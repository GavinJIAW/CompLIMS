"""Fixed B5 file DTO and canonical SELF_SERVICE actions."""
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.http import FileResponse
from django.http.multipartparser import MultiPartParser as DjangoMultiPartParser, MultiPartParserError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ParseError, ValidationError
from rest_framework.parsers import MultiPartParser, DataAndFiles
from rest_framework.viewsets import GenericViewSet

from coreadmin.access.context import context_for
from coreadmin.access.registry import Policy
from coreadmin.system.models import ManagedFile
from coreadmin.system.services import managed_files as service
from coreadmin.utils.authentication import must_change_gate
from coreadmin.utils.json_response import DetailResponse, ErrorResponse
from coreadmin.utils.log_targets import record_targets
from coreadmin.utils.pagination import CustomPagination
from coreadmin.utils.permission import CustomPermission


class StrictFilenameParser(DjangoMultiPartParser):
    def sanitize_file_name(self, file_name):
        # Inspect the multipart name BEFORE Django strips directory components.
        return service.validate_name(file_name)


class ManagedMultipartParser(MultiPartParser):
    def parse(self, stream, media_type=None, parser_context=None):
        request = parser_context['request']
        meta = request.META.copy()
        meta['CONTENT_TYPE'] = media_type
        # A provided stream can be chunked/lengthless. Never use this hint as the
        # file size authority; the service enforces the actual byte count.
        meta.setdefault('CONTENT_LENGTH', '1')
        try:
            data, files = StrictFilenameParser(meta, stream, request.upload_handlers,
                parser_context.get('encoding', 'utf-8')).parse()
        except MultiPartParserError as exc:
            raise ParseError('Invalid multipart upload.') from exc
        return DataAndFiles(data, files)


class ManagedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagedFile
        fields = ('id', 'original_name', 'size', 'sha256', 'content_type', 'uploader', 'created_at')
        read_only_fields = fields


class ManagedFileViewSet(GenericViewSet):
    queryset = ManagedFile.objects.all()
    serializer_class = ManagedFileSerializer
    permission_classes = [CustomPermission]
    parser_classes = [ManagedMultipartParser]
    pagination_class = CustomPagination
    filter_backends = []

    def initialize_request(self, request, *args, **kwargs):
        # Spool multipart bytes to OS temporary storage, including lengthless
        # ASGI streams. Do not let a missing/small length hint buffer 100 MiB.
        request.upload_handlers = [TemporaryFileUploadHandler(request)]
        result = super().initialize_request(request, *args, **kwargs)
        if 'CONTENT_LENGTH' not in request.META and not request._read_started:
            result._stream = request
        return result

    def check_permissions(self, request):
        super().check_permissions(request)
        context = context_for(request, self)
        if context.action.policy == Policy.B1_SHUTDOWN:
            raise MethodNotAllowed(request.method)
        must_change_gate(request.user, context.action.code, False)

    def handle_exception(self, exc):
        if isinstance(exc, (MethodNotAllowed, service.FileTooLarge)):
            return ErrorResponse(msg=str(exc.detail), status=exc.status_code)
        return super().handle_exception(exc)

    def get_queryset(self):
        return service.visible_files(context_for(self.request, self))

    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def retrieve(self, request, pk=None):
        return DetailResponse(data=self.get_serializer(self.get_object()).data)

    def create(self, request):
        if set(request.data) != {'file'} or len(request.FILES.getlist('file')) != 1:
            raise ValidationError({'file': 'Exactly one file and no other fields are accepted.'})
        obj = service.upload(request.FILES['file'], request.user)
        record_targets(request, {'managedfile': [obj.pk]})
        return DetailResponse(data=self.get_serializer(obj).data, msg='File uploaded.')

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        obj, stream = service.open_authorized(context_for(request, self), pk)
        return FileResponse(stream, as_attachment=True, filename=obj.original_name,
            content_type=obj.content_type or 'application/octet-stream')

    def update(self, request, pk=None):
        raise MethodNotAllowed(request.method)

    partial_update = update
    destroy = update

    @action(detail=False, methods=['delete'])
    def multiple_delete(self, request):
        raise MethodNotAllowed(request.method)

    def options(self, request, *args, **kwargs):
        return DetailResponse(data={})
