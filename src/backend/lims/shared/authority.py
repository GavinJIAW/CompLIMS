"""Explicit cross-master references and aggregate child field grants."""
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from coreadmin.access.context import AccessContext
from coreadmin.access.registry import REGISTRY
from coreadmin.access.fields import FieldPolicy
from coreadmin.system.models import FieldPermission


def read_context(actor, resource):
    return AccessContext(actor, REGISTRY[resource, 'retrieve', 'GET'])


def reference(actor, resource, obj, existing=False):
    context = read_context(actor, resource)
    if not context.allowed():
        raise PermissionDenied('Target resource cannot be referenced.')
    if not context.scope(type(obj).objects.all()).filter(pk=obj.pk).exists():
        raise NotFound()
    if not existing and not obj.enabled:
        raise ValidationError({'reference': 'Disabled masters cannot be added to a new relationship.'})


def readable(actor, resource, obj, fields):
    context = read_context(actor, resource)
    return context.allowed() and set(fields) <= FieldPolicy(context, type(obj)).allowed(obj)


def row_fields(context, model, mode, fields):
    ceiling = set(fields.split())
    if context.admin:
        return ceiling
    result = {'id'} if mode == 'read' else set()
    flag = {'read': 'is_query', 'create': 'is_create', 'update': 'is_update'}[mode]
    for grant in context.grants:
        result.update(FieldPermission.objects.filter(role_id=grant.role_id, field__menu_id=grant.menu_id,
            field__model=model.__name__, **{flag: True}).values_list('field__field_name', flat=True))
    return result & ceiling
