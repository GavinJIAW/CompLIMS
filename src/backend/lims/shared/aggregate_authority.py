"""M2 children inherit exactly the grants contributing to the aggregate parent."""
from types import SimpleNamespace
from rest_framework.exceptions import PermissionDenied, ValidationError
from coreadmin.system.models import FieldPermission
from coreadmin.access.context import AccessContext
from coreadmin.access.registry import REGISTRY
from coreadmin.access.fields import FieldPolicy
from lims.shared.m2_contract import CHILD_READ, CHILD_CREATE, CHILD_UPDATE


def proposed(context):
    values = context.create_attribution()
    return SimpleNamespace(pk=None, creator_id=values['creator'].pk, dept_belong_id=values['dept_belong_id'])


def child_fields(context, parent, model, mode):
    name = model if isinstance(model, str) else model.__name__
    ceiling = set({'read': CHILD_READ, 'create': CHILD_CREATE, 'update': CHILD_UPDATE}[mode][name].split())
    if context.admin:
        return ceiling
    flag = {'read': 'is_query', 'create': 'is_create', 'update': 'is_update'}[mode]
    result = {'id'} if mode == 'read' else set()
    for grant in context.contributing(parent):
        result.update(FieldPermission.objects.filter(role_id=grant.role_id, field__menu_id=grant.menu_id, field__model=name, **{flag: True}).values_list('field__field_name', flat=True))
    return result & ceiling


def check_child(context, parent, model, data, existing=None):
    allowed = child_fields(context, parent, model, 'update' if existing else 'create')
    rejected = set(data) - allowed - {'id'}
    if rejected:
        raise ValidationError({key: 'Child field is not writable for this parent.' for key in sorted(rejected)})


def source(context, resource, model, pk, fields=()):
    """Both object reference and source field reads are required for snapshotting."""
    from django.shortcuts import get_object_or_404
    if type(pk) is not int or pk <= 0:
        raise ValidationError({resource: 'A positive source ID is required.'})
    read = AccessContext(context.user, REGISTRY[resource, 'retrieve', 'GET'])
    if not read.allowed():
        raise PermissionDenied('Source reference permission is required.')
    obj = get_object_or_404(read.scope(model.objects.all()), pk=pk)
    from django.db import connection
    if connection.in_atomic_block:
        # Scope uses DISTINCT, so lock the already-authorized row separately and
        # resolve scope again against the current row before snapshotting it.
        get_object_or_404(model.objects.select_for_update(), pk=obj.pk)
        read.__dict__.pop('grants', None)
        read.__dict__.pop('child_depts', None)
        obj = get_object_or_404(read.scope(model.objects.all()), pk=pk)
    if not obj.enabled:
        raise ValidationError({resource: 'Disabled sources cannot establish new relationships.'})
    if not set(fields) <= FieldPolicy(read, model).allowed(obj):
        raise PermissionDenied('Source snapshot fields are not readable.')
    return obj
