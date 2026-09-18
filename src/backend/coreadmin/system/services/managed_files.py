"""One-shot private local upload, with compensation for normal write failures."""
import hashlib
import logging
import ntpath
import re
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from rest_framework.exceptions import APIException, NotFound, ValidationError

from coreadmin.system.models import ManagedFile

logger = logging.getLogger(__name__)


class FileTooLarge(APIException):
    status_code = 413
    default_detail = 'File exceeds the configured size limit.'


def validate_name(name):
    if (not isinstance(name, str) or not name.strip() or len(name) > 255
            or name in {'.', '..'} or any(c in name for c in ('/', '\\', '\x00', '\r', '\n'))
            or ntpath.basename(name) != name or ntpath.isabs(name)):
        raise ValidationError({'file': 'A basename without path components is required.'})
    return name


def private_root():
    root = Path(settings.MANAGED_FILE_ROOT).resolve()
    media = Path(settings.MEDIA_ROOT).resolve()
    if root == media or media in root.parents or root in media.parents:
        raise ImproperlyConfigured('MANAGED_FILE_ROOT and MEDIA_ROOT must not overlap.')
    return root


def visible_files(context):
    """Same owner envelope for metadata and bytes; action authority is B2."""
    if not context.allowed():
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied()
    rows = ManagedFile.objects.all()
    return rows if context.admin else rows.filter(uploader_id=context.user.pk)


def upload(uploaded, user):
    name = validate_name(uploaded.name)
    root = private_root()
    directory = root / 'managed'
    directory.mkdir(parents=True, exist_ok=True)
    if directory.resolve().parent != root:
        raise ImproperlyConfigured('Managed storage directory must not escape private root.')
    key = 'managed/' + uuid.uuid4().hex
    path = root / key
    created = False
    try:
        # Exclusive creation: collision never overwrites or removes an older file.
        with path.open('xb') as output:
            created = True
            digest = hashlib.sha256()
            size = 0
            for chunk in uploaded.chunks():
                size += len(chunk)
                if size > settings.MANAGED_FILE_MAX_SIZE_BYTES:
                    raise FileTooLarge()
                output.write(chunk)
                digest.update(chunk)
            if not size:
                raise ValidationError({'file': 'Empty files are not allowed.'})
        content_type = getattr(uploaded, 'content_type', None) or 'application/octet-stream'
        if len(content_type) > 255 or '\r' in content_type or '\n' in content_type:
            content_type = 'application/octet-stream'
        with transaction.atomic():
            return ManagedFile.objects.create(original_name=name, storage_key=key,
                size=size, sha256=digest.hexdigest(), content_type=content_type, uploader=user)
    except Exception:
        if created:
            path.unlink(missing_ok=True)
        raise


def open_authorized(context, pk):
    from rest_framework.generics import get_object_or_404
    obj = get_object_or_404(visible_files(context), pk=pk)
    root = private_root()
    if not re.fullmatch(r'managed/[0-9a-f]{32}', obj.storage_key):
        logger.error('Invalid managed file key for record %s', obj.pk)
        raise NotFound('File unavailable.')
    path = root / obj.storage_key
    if root not in path.resolve().parents:
        logger.error('Managed file outside private root for record %s', obj.pk)
        raise NotFound('File unavailable.')
    try:
        stream = path.open('rb')
    except FileNotFoundError:
        logger.error('Missing backing file for managed record %s', obj.pk)
        raise NotFound('File unavailable.')
    return obj, stream
