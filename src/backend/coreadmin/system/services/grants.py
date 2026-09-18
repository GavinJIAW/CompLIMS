"""Role-serialized authorization commands. B2 remains the policy authority."""
from contextlib import contextmanager
from functools import wraps
from django.db import transaction
from coreadmin.system.models import Role, Users, Dept, RoleMenuButtonPermission


class GrantService:
    @staticmethod
    @contextmanager
    def command(role_ids, user_ids=(), dept_ids=()):
        with transaction.atomic():
            list(Role.objects.select_for_update().filter(pk__in=set(role_ids)).order_by('pk'))
            list(RoleMenuButtonPermission.objects.select_for_update().filter(role_id__in=set(role_ids)).order_by('pk'))
            list(Users.objects.select_for_update().filter(pk__in=set(user_ids)).order_by('pk'))
            list(Dept.objects.select_for_update().filter(pk__in=set(dept_ids)).order_by('pk'))
            yield


def grant_command(method):
    @wraps(method)
    def wrapped(view, request, *args, **kwargs):
        data = request.data
        roles, users = set(), []
        if isinstance(data, dict):
            roles.update(int(data[k]) for k in ('role', 'roleId') if data.get(k) is not None)
            users = data.get('movedKeys', data.get('users_id', data.get('user_id', []))) or []
            if data.get('role_menu_btn_perm_id'):
                roles.update(RoleMenuButtonPermission.objects.filter(pk=data['role_menu_btn_perm_id']).values_list('role_id', flat=True))
        if kwargs.get('pk') is not None:
            roles.add(int(kwargs['pk']))
        with GrantService.command(roles, users, data.get('dept', []) if isinstance(data, dict) else []):
            from coreadmin.access.targets import validate_targets
            validate_targets(view, request, view.access_context)
            return method(view, request, *args, **kwargs)
    return wrapped
