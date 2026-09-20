"""Version-controlled capabilities. Database URL/method strings are not policy.

Only the resources and actions below are registered. Adding a router or an
@action never implicitly grants access; coverage tests require a policy decision.
"""
from dataclasses import dataclass
from enum import Enum


class Policy(str, Enum):
    PUBLIC = 'PUBLIC'
    SELF_SERVICE = 'SELF_SERVICE'
    FIXED_SUPERUSER = 'FIXED_SUPERUSER'
    ROLE_GRANTABLE = 'ROLE_GRANTABLE'
    B1_SHUTDOWN = 'B1_SHUTDOWN'


@dataclass(frozen=True)
class Action:
    resource: str
    name: str
    policy: Policy
    methods: tuple
    shutdown_guard: str = 'active'

    @property
    def code(self):
        return f'{self.resource}.{self.name}'


# Exact class identities, not a component name, URL regex, basename heuristic,
# or a model-derived fallback. Explicit as_view aliases use these same classes.
RESOURCES = {
    'menu': ('menu', 'MenuViewSet'),
    'menu_button': ('menu_button', 'MenuButtonViewSet'),
    'role': ('role', 'RoleViewSet'),
    'dept': ('dept', 'DeptViewSet'),
    'user': ('user', 'UserViewSet'),
    'operation_log': ('operation_log', 'OperationLogViewSet'),
    'dictionary': ('dictionary', 'DictionaryViewSet'),
    'area': ('area', 'AreaViewSet'),
    'file': ('file_list', 'FileViewSet'),
    'managed_file': ('managed_file', 'ManagedFileViewSet'),
    'api_white_list': ('api_white_list', 'ApiWhiteListViewSet'),
    'system_config': ('system_config', 'SystemConfigViewSet'),
    'message_center': ('message_center', 'MessageCenterViewSet'),
    'role_menu_button_permission': ('role_menu_button_permission', 'RoleMenuButtonPermissionViewSet'),
    'role_menu_permission': ('role_menu', 'RoleMenuPermissionViewSet'),
    'column': ('menu_field', 'MenuFieldViewSet'),
    'login_log': ('login_log', 'LoginLogViewSet'),
    'download_center': ('download_center', 'DownloadCenterViewSet'),
}
CLASS_RESOURCES = {
    (f'coreadmin.system.views.{module}', cls): resource
    for resource, (module, cls) in RESOURCES.items()
}
AUTH_RESOURCES = frozenset({
    'role', 'role_menu_permission', 'role_menu_button_permission',
    'menu_button', 'column', 'api_white_list',
})
READ_ONLY = frozenset({'file', 'download_center', 'operation_log', 'login_log'})
REGISTRY = {}


def register(resource, names, policy, methods, shutdown_guard='active'):
    for name in names.split():
        for method in methods.split():
            key = (resource, name, method)
            if key in REGISTRY:
                raise ValueError(f'Duplicate action policy: {key}')
            REGISTRY[key] = Action(resource, name, policy, tuple(methods.split()), shutdown_guard)


R, S, O, X = (Policy.ROLE_GRANTABLE, Policy.FIXED_SUPERUSER,
               Policy.SELF_SERVICE, Policy.B1_SHUTDOWN)
for resource in RESOURCES:
    if resource == 'managed_file':
        continue  # B5 has a fixed multipart/read contract, no inherited workbook actions.
    read_policy = S if resource in {'file', 'operation_log', 'login_log'} else (
        O if resource == 'download_center' else R)
    register(resource, 'list retrieve', read_policy, 'GET HEAD')
    write_policy = X if resource in READ_ONLY else (
        S if resource in AUTH_RESOURCES | {'system_config', 'message_center'} else R)
    guard = 'superuser' if resource in {'file', 'operation_log', 'login_log'} else 'active'
    register(resource, 'create', write_policy, 'POST', guard)
    register(resource, 'update', write_policy, 'PUT PATCH', guard)
    register(resource, 'destroy', write_policy, 'DELETE', guard)
    register(resource, 'multiple_delete', S if resource in AUTH_RESOURCES else X, 'DELETE', guard)
    # Only the existing Dept blank template is retained. User and log imports
    # remain closed, including HEAD. No path-based importer is re-enabled.
    template = S if resource == 'dept' else X
    import_guard = 'public' if resource == 'user' else guard
    register(resource, 'import_data', template, 'GET', import_guard)
    register(resource, 'import_data', X, 'POST HEAD', import_guard)
    register(resource, 'update_template', R if resource in {'dept', 'user'} else X, 'GET HEAD', guard)
    register(resource, 'export_data', R if resource == 'user' else X, 'GET HEAD', guard)
    # Safe metadata is a separate policy: identity only, no serializer discovery.
    register(resource, 'metadata', O, 'OPTIONS')
register('user', 'export_data', R, 'POST')
register('managed_file', 'list retrieve download', O, 'GET HEAD')
register('managed_file', 'create', O, 'POST')
register('managed_file', 'metadata', O, 'OPTIONS')
register('managed_file', 'update', X, 'PUT PATCH')
register('managed_file', 'destroy multiple_delete', X, 'DELETE')


register('menu', 'web_router get_all_menu', O, 'GET HEAD')
register('menu', 'move_up move_down', S, 'POST')
register('dept', 'all_dept dept_info', R, 'GET HEAD')
register('dept', 'move_up move_down', S, 'POST')
register('user', 'user_info', O, 'GET HEAD')
register('user', 'update_user_info change_password', O, 'PUT')
register('user', 'login_change_password', O, 'POST')
register('user', 'reset_password reset_to_default_password', S, 'PUT')
register('role', 'set_role_users', S, 'PUT')
register('role', 'get_role_users', S, 'GET HEAD')
register('role', 'add_role_users', S, 'POST')
register('role', 'remove_role_user', S, 'DELETE')
register('role', 'init_crud field_permission', O, 'GET HEAD')
register('area', 'field_permission', O, 'GET HEAD')
register('login_log', 'field_permission', X, 'GET HEAD', 'superuser')
register('role_menu_permission', 'save_auth', S, 'POST')
register('role_menu_button_permission', 'get_role_menu get_role_menu_btn_field role_to_dept_all', S, 'GET HEAD')
register('role_menu_button_permission', 'set_role_menu set_role_menu_field set_role_menu_btn set_role_menu_btn_data_range', S, 'PUT')
register('menu_button', 'menu_button_all_permission', O, 'GET HEAD')
register('menu_button', 'batch_create', S, 'POST')
register('column', 'get_models', S, 'GET HEAD')
register('column', 'auto_match_fields', S, 'POST')
register('file', 'get_all', S, 'GET HEAD')
register('message_center', 'get_self_receive get_newest_msg', O, 'GET HEAD')
register('system_config', 'save_content', S, 'PUT')
register('system_config', 'get_association_table', S, 'GET HEAD')
register('system_config', 'get_table_data', X, 'GET HEAD', 'public')
register('system_config', 'get_relation_info', R, 'GET HEAD')

# Existing non-ViewSet entrypoints, with no wildcard/prefix public allowance.
ENTRYPOINTS = {
    ('/api/login/', 'POST'): ('login.create', Policy.PUBLIC),
    ('/api/captcha/', 'GET'): ('captcha.retrieve', Policy.PUBLIC),
    ('/api/token/refresh/', 'POST'): ('token.refresh', Policy.PUBLIC),
    ('/api/init/settings/', 'GET'): ('init_settings.retrieve', Policy.PUBLIC),
    ('/healthz', 'GET'): ('health.retrieve', Policy.PUBLIC),
    ('/readiness', 'GET'): ('readiness.retrieve', Policy.PUBLIC),
    ('/api/init/dictionary/', 'GET'): ('init_dictionary.retrieve', O),
    ('/api/logout/', 'POST'): ('logout.create', O),
}

# Explicit finite compatibility vocabulary. No database URL or method is read.
ALIASES = {}
for prefix, resource in {
    'menu': 'menu', 'btn': 'menu_button', 'column': 'column', 'dept': 'dept',
    'role': 'role', 'user': 'user', 'messageCenter': 'message_center',
    'api_white_list': 'api_white_list', 'downloadCenter': 'download_center',
    'system_config': 'system_config', 'dictionary': 'dictionary', 'area': 'area',
    'file': 'file', 'login_log': 'login_log', 'operation_log': 'operation_log',
    'role_menu_permission': 'role_menu_permission',
    'role_menu_button_permission': 'role_menu_button_permission',
}.items():
    for suffix, action in {'Search': 'list', 'Retrieve': 'retrieve', 'Create': 'create',
                           'Update': 'update', 'Delete': 'destroy'}.items():
        ALIASES[f'{prefix}:{suffix}'] = f'{resource}.{action}'
ALIASES.update({
    'menu:SearchAll': 'menu.get_all_menu', 'menu:router': 'menu.web_router',
    'menu:MoveUp': 'menu.move_up', 'menu:MoveDown': 'menu.move_down',
    'dept:SearchAll': 'dept.all_dept', 'dept:HeaderInfo': 'dept.dept_info',
    'dept:MoveUp': 'dept.move_up', 'dept:MoveDown': 'dept.move_down',
    'column:Match': 'column.auto_match_fields', 'role:Save': 'role.update',
    # Permission editor is an admin operation, not a second role detail grant.
    'role:Permission': 'role_menu_button_permission.get_role_menu',
    'role:AuthorizedAdd': 'role.add_role_users',
    'role:AuthorizedSearch': 'role.get_role_users',
    'role:AuthorizedDel': 'role.remove_role_user',
    'user:ResetPassword': 'user.reset_password',
    'user:DefaultPassword': 'user.reset_to_default_password',
    'user:Export': 'user.export_data',
    'system_config:RelationInfo': 'system_config.get_relation_info',
    'user:UpdateTemplate': 'user.update_template',
    'dept:UpdateTemplate': 'dept.update_template',
})


# M1 is a separate app, with exact class identities and the same policies.
from apps.lims.contract import CLASSES as LIMS_CLASSES
for resource, cls in LIMS_CLASSES.items():
    CLASS_RESOURCES[('apps.lims.views', cls)] = resource
    register(resource, 'list retrieve', R, 'GET HEAD')
    register(resource, 'create', R, 'POST')
    register(resource, 'update', R, 'PUT PATCH')
    register(resource, 'destroy', R, 'DELETE')
    register(resource, 'metadata', O, 'OPTIONS')
    register(resource, 'field_permission', O, 'GET HEAD')
    register(resource, 'multiple_delete', X, 'DELETE')
    register(resource, 'import_data', X, 'GET HEAD POST')
    register(resource, 'export_data update_template', X, 'GET HEAD')
    for suffix, name in {'Search': 'list', 'Retrieve': 'retrieve', 'Create': 'create',
                         'Update': 'update', 'Delete': 'destroy'}.items():
        ALIASES[f'{resource}:{suffix}'] = f'{resource}.{name}'


def resource_for(view):
    cls = type(view)
    return CLASS_RESOURCES.get((cls.__module__, cls.__name__))


def resolve(view, method):
    resource = resource_for(view)
    if method == 'OPTIONS':
        name = 'metadata'
    else:
        name = getattr(view, 'action', None)
        if not name:
            name = getattr(view, 'action_map', {}).get(method.lower())
        if name == 'partial_update':
            name = 'update'
    return REGISTRY.get((resource, name, method))


def aliases_for(code):
    return frozenset(alias for alias, target in ALIASES.items() if target == code)
