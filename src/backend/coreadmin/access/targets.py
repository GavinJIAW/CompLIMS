"""Explicit target bindings for legacy custom management actions.

All IDs are resolved before the handler writes anything. This is authorization
validation, not a replacement for the later transaction/concurrency work.
"""
from rest_framework.exceptions import NotFound, ValidationError

from coreadmin.system import models


def ids(value):
    values = value if isinstance(value, list) else [value]
    try:
        if any(isinstance(item, bool) or not isinstance(item, (int, str))
               or not str(item).isdigit() for item in values):
            raise ValueError()
        return {int(item) for item in values}
    except (TypeError, ValueError):
        raise ValidationError('Expected valid target IDs.')


def resolve_ids(queryset, value):
    requested = ids(value)
    if set(queryset.filter(pk__in=requested).values_list('pk', flat=True)) != requested:
        raise NotFound()
    return requested


def dept_info_selection(params):
    """An explicit empty UI selection is not a missing or concrete target."""
    if 'dept_id' not in params:
        raise ValidationError({'dept_id': 'Target parameter is required.'})
    show_all = params.get('show_all', '0')
    if show_all not in ('0', '1', ''):
        raise ValidationError({'show_all': 'Expected 0 or 1.'})
    value = params.get('dept_id')
    if value == '':
        if show_all == '1':
            raise ValidationError({'dept_id': 'Recursive statistics require a department.'})
        return None, False
    return next(iter(ids(value))), show_all == '1'


# (source, parameter, model). These are admin controls, never role-delegated.
ADMIN_TARGETS = {
    'menu.move_up': [('body', 'menu_id', 'Menu')],
    'menu.move_down': [('body', 'menu_id', 'Menu')],
    'dept.move_up': [('body', 'dept_id', 'Dept')],
    'dept.move_down': [('body', 'dept_id', 'Dept')],
    'role.set_role_users': [('path', 'pk', 'Role'), ('body', 'movedKeys', 'Users')],
    'role.add_role_users': [('path', 'pk', 'Role'), ('body', 'users_id', 'Users')],
    'role.remove_role_user': [('path', 'pk', 'Role'), ('body', 'user_id', 'Users')],
    'role.get_role_users': [('query', 'role_id', 'Role')],
    'role_menu_permission.save_auth': [('body', 'role', 'Role'), ('body', 'menu', 'Menu')],
    'role_menu_button_permission.set_role_menu': [('body', 'roleId', 'Role'), ('body', 'menuId', 'Menu')],
    'role_menu_button_permission.set_role_menu_btn': [('body', 'roleId', 'Role'), ('body', 'btnId', 'MenuButton')],
    'role_menu_button_permission.set_role_menu_field': [('path', 'pk', 'Role')],
    'role_menu_button_permission.set_role_menu_btn_data_range': [('body', 'role_menu_btn_perm_id', 'RoleMenuButtonPermission')],
    'menu_button.batch_create': [('body', 'menu', 'Menu')],
    'column.auto_match_fields': [('body', 'menu', 'Menu')],
    'user.reset_password': [('path', 'pk', 'Users')],
    'user.reset_to_default_password': [('path', 'pk', 'Users')],
}
OPTIONAL_ADMIN_TARGETS = {
    'role.get_role_users': [('query', 'dept', 'Dept')],
    'role_menu_button_permission.get_role_menu': [('query', 'roleId', 'Role')],
    'role_menu_button_permission.get_role_menu_btn_field': [('query', 'roleId', 'Role'), ('query', 'menuId', 'Menu')],
    'role_menu_button_permission.role_to_dept_all': [('query', 'menu_button', 'MenuButton')],
    'role_menu_button_permission.set_role_menu_btn': [('body', 'dept', 'Dept')],
    'role_menu_button_permission.set_role_menu_btn_data_range': [('body', 'dept', 'Dept')],
}


def validate_targets(view, request, context):
    code = context.action.code
    sources = {'body': request.data, 'query': request.query_params, 'path': view.kwargs}
    for required, bindings in ((True, ADMIN_TARGETS.get(code, [])),
                               (False, OPTIONAL_ADMIN_TARGETS.get(code, []))):
        for source, key, model_name in bindings:
            if not isinstance(sources[source], dict):
                raise ValidationError('Expected target parameters.')
            value = sources[source].get(key)
            if value is None or value == '':
                if required:
                    raise ValidationError({key: 'Target is required.'})
                continue
            queryset = getattr(models, model_name).objects.all()
            if model_name == 'Users':
                queryset = queryset.exclude(is_superuser=True)
            resolve_ids(queryset, value)
    if code == 'role_menu_button_permission.set_role_menu_field':
        if not isinstance(request.data, list):
            raise ValidationError('Expected field grants.')
        resolve_ids(models.MenuField.objects.all(), [item.get('id') for item in request.data])
    if code in {'role_menu_button_permission.set_role_menu_btn', 'role_menu_button_permission.set_role_menu_btn_data_range'}:
        if request.data.get('data_range', 0) not in (0, 1, 2, 3, 4):
            raise ValidationError({'data_range': 'Invalid scope.'})
    if code == 'system_config.save_content':
        if not isinstance(request.data, list):
            raise ValidationError('Expected configuration items.')
        resolve_ids(models.SystemConfig.objects.all(), [row.get('id') for row in request.data])
        from coreadmin.access.fields import FieldPolicy
        policy = FieldPolicy(context, models.SystemConfig)
        for row in request.data:
            policy.validate_write({key: value for key, value in row.items() if key != 'id'},
                                  models.SystemConfig.objects.get(pk=row['id']))
    if code == 'dept.dept_info':
        dept_id, _ = dept_info_selection(request.query_params)
        if dept_id is not None:
            resolve_ids(context.scope(view.get_queryset()), dept_id)


def validate_write_relations(context, data):
    bindings = {'menu': ('parent', models.Menu), 'dept': ('parent', models.Dept),
                'dictionary': ('parent', models.Dictionary), 'area': ('pcode', models.Area)}
    binding = bindings.get(context.action.resource)
    if binding and data.get(binding[0]) not in (None, ''):
        resolve_ids(context.scope(binding[1].objects.all()), data[binding[0]])
