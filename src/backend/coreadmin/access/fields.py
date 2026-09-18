"""Instance-level field and query policy over the same contributing grant tuples."""
import re
from functools import cached_property
from types import SimpleNamespace

from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework.exceptions import PermissionDenied, ValidationError

from coreadmin.access.registry import Policy, REGISTRY
from coreadmin.access.context import AccessContext
from coreadmin.system.models import FieldPermission


AUDIT_READ = 'id description creator modifier dept_belong_id create_datetime update_datetime creator_name modifier_name'
# These are reviewed output ceilings, not introspected model-field fallbacks.
READ = {key: frozenset((AUDIT_READ + ' ' + fields).split()) for key, fields in {
    'menu': 'icon name title path sort is_link link_url is_catalog web_path component component_name status cache visible is_iframe is_affix parent menuPermission hasChild',
    'menu_button': 'name value api method menu sort canonical_action mapping_status',
    'role': 'name key sort status users',
    'dept': 'name key sort owner phone email status parent parent_name status_label has_children hasChild dept_user_count dept_name dept_user gender sub_dept_map',
    'user': 'username name email mobile avatar gender user_type is_active dept role post dept_name dept_name_all role_info last_login date_joined',
    'operation_log': 'request_modular request_path request_body request_target request_method request_msg request_ip request_browser response_code request_os json_result status',
    'dictionary': 'label value type color is_value status sort remark parent',
    'area': 'name code level pinyin initials enable pcode pcode_count hasChild pcode_info',
    'file': 'name file_url engine mime_type size md5sum upload_method file_type url',
    'api_white_list': 'url method enable_datasource',
    'system_config': 'title key value sort status data_options form_item_type rule placeholder setting parent children form_item_type_label',
    'message_center': 'title content target_type target_user target_dept target_role role_info user_info dept_info is_read',
    'role_menu_button_permission': 'role menu_button data_range dept menu_button__name menu_button__value',
    'role_menu_permission': 'role menu',
    'column': 'model field_name title menu',
    'login_log': 'username ip agent browser os continent country province city district isp area_code country_english country_code longitude latitude login_type',
    'download_center': 'task_name task_status file_name size md5sum url',
}.items()}
WRITE = {key: frozenset(fields.split()) for key, fields in {
    'menu': 'description icon name sort is_link link_url is_catalog web_path component component_name status cache visible is_iframe is_affix parent',
    'menu_button': 'name value api method menu sort description',
    'role': 'name key sort status description',
    'dept': 'name key sort owner phone email status parent description',
    'user': 'username name email mobile avatar gender user_type is_active',
    'dictionary': 'label value type color is_value status sort remark parent description',
    'area': 'name code enable pcode description',
    'api_white_list': 'url method enable_datasource description',
    'system_config': 'title key value sort status data_options form_item_type rule placeholder setting parent description',
    'message_center': 'title content target_type target_user target_dept target_role description',
    'role_menu_button_permission': 'role menu_button data_range dept description',
    'role_menu_permission': 'role menu description',
    'column': 'model field_name title menu description',
}.items()}
IDENTITY = {
    'menu': {'id'}, 'menu_button': {'id'}, 'role': {'id'}, 'dept': {'id'},
    'user': {'id'}, 'operation_log': {'id'}, 'dictionary': {'id'}, 'area': {'id'},
    'file': {'id'}, 'api_white_list': {'id'}, 'system_config': {'id'},
    'message_center': {'id'}, 'role_menu_button_permission': {'id'},
    'role_menu_permission': {'id'}, 'column': {'id'}, 'login_log': {'id'},
    'download_center': {'id'},
}
# Explicitly reviewed create contexts: attribution is entirely server-owned.
CREATE_ADAPTERS = frozenset({'user', 'dictionary', 'menu', 'area'})
SELF_READ = {
    'user.update_user_info': frozenset({'name', 'email', 'mobile', 'avatar', 'gender'}),
    'menu.web_router': frozenset('id parent icon sort path name title is_link link_url is_catalog web_path component component_name cache visible is_iframe is_affix status'.split()),
    'menu.get_all_menu': frozenset('id parent icon sort path name title is_link link_url is_catalog web_path component component_name cache visible is_iframe is_affix status'.split()),
    'message_center.get_self_receive': frozenset({'id', 'title', 'content', 'is_read', 'create_datetime'}),
    'message_center.get_newest_msg': frozenset({'id', 'title', 'content', 'is_read', 'create_datetime'}),
    'download_center.list': READ['download_center'],
    'download_center.retrieve': READ['download_center'],
}
# Relations have an explicit target resource/action. A parent's field grant
# never authorizes a child's fields or objects.
RELATIONS = {
    'area': {'pcode_info': ('area', 'pcode')},
    'role': {'users': ('user', 'users_set')},
    'user': {'role_info': ('role', 'role'), 'role': ('role', 'role'), 'dept': ('dept', 'dept')},
    'message_center': {'role_info': ('role', 'target_role'), 'user_info': ('user', 'target_user'),
                       'dept_info': ('dept', 'target_dept'), 'target_role': ('role', 'target_role'),
                       'target_user': ('user', 'target_user'), 'target_dept': ('dept', 'target_dept')},
    'system_config': {'children': ('system_config', 'children')},
    'menu': {'menuPermission': ('menu_button', 'menuPermission')},
}
# Area's parent summary belongs to the current Area action. Its FK uses code,
# not the primary key; keep the existing name/code response shape.
CURRENT_ACTION_RELATIONS = frozenset({('area', 'pcode_info')})
RELATION_IDENTIFIERS = {('area', 'pcode_info'): 'code'}
# Only explicitly named scalar relationship lookups may be queried. No arbitrary
# '__' traversal is admitted by django-filter/RESTQL on behalf of a caller.
QUERY_RELATIONS = {'user': {'dept__name': 'dept_name', 'role__name': 'role_info'}}
# Exact scalar lookup registrations, not permission for arbitrary traversal.
QUERY_LOOKUPS = {'system_config': {'parent__isnull': ('parent', frozenset({'true', 'false'}))}}
QUERY_CONTROLS = frozenset({'page', 'limit', 'page_size', 'format', 'search', 'ordering', 'query'})
BUSINESS_QUERIES = {
    'user.list': {'show_all': None},
    'dept.dept_info': {'dept_id': 'id', 'show_all': None},
    'system_config.get_relation_info': {'varName': 'key', 'table': 'setting', 'relationIds': 'value'},
}


class FieldPolicy:
    def __init__(self, context, model):
        self.context, self.model = context, model
        self.resource = context.action.resource

    @cached_property
    def configured(self):
        conditions = Q(pk__in=[])
        for grant in self.context.grants:
            conditions |= Q(role_id=grant.role_id, field__menu_id=grant.menu_id)
        rows = FieldPermission.objects.filter(conditions, field__model=self.model.__name__).select_related('field')
        result = {}
        for row in rows:
            key = (row.role_id, row.field.menu_id)
            entry = result.setdefault(key, {'read': set(), 'create': set(), 'update': set()})
            for mode, enabled in [('read', row.is_query), ('create', row.is_create), ('update', row.is_update)]:
                if enabled:
                    entry[mode].add(row.field.field_name)
        return result

    def ceiling(self, mode):
        if mode == 'read':
            return READ.get(self.resource, frozenset())
        ceiling = WRITE.get(self.resource, frozenset())
        if self.resource == 'user' and mode == 'create':
            ceiling |= {'password'}
        return ceiling

    def for_grants(self, grants, mode):
        fields = set(IDENTITY.get(self.resource, ())) if mode == 'read' else set()
        for grant in grants:
            fields |= self.configured.get((grant.role_id, grant.menu_id), {}).get(mode, set())
        return fields & self.ceiling(mode)

    def allowed(self, instance, mode='read'):
        if self.context.admin:
            return self.ceiling(mode)
        if self.context.action.policy == Policy.SELF_SERVICE:
            return SELF_READ.get(self.context.action.code, frozenset()) if mode == 'read' else frozenset()
        return self.for_grants(self.context.contributing(instance), mode)

    def query_fields(self):
        if self.context.admin:
            return self.ceiling('read')
        if self.context.action.policy == Policy.SELF_SERVICE:
            return SELF_READ.get(self.context.action.code, frozenset())
        # Conservative intersection prevents a filter on Role A's hidden field
        # from revealing membership/count/order of objects visible only via B.
        sets = [self.for_grants((grant,), 'read') for grant in self.context.grants]
        return set.intersection(*sets) if sets else set()

    def validate_write(self, data, instance=None):
        mode = 'update' if instance is not None else 'create'
        if instance is None:
            if not self.context.admin and self.resource not in CREATE_ADAPTERS:
                raise PermissionDenied('No approved create scope adapter.')
            attribution = self.context.create_attribution()
            instance = SimpleNamespace(pk=None, creator_id=attribution['creator'].pk,
                                       dept_belong_id=attribution['dept_belong_id'])
            if not self.context.admin and not self.context.contributing(instance):
                raise PermissionDenied('Create target is outside authorized scope.')
        allowed = self.allowed(instance, mode)
        if not isinstance(data, dict):
            raise ValidationError('Expected an object.')
        rejected = set(data) - allowed
        if rejected:
            raise ValidationError({key: 'Field is not writable for this action and object.' for key in sorted(rejected)})
        if not allowed and not self.context.admin:
            raise PermissionDenied('No writable fields for this action and target.')

    def validate_query(self, request, view):
        readable = self.query_fields()
        controls = dict(BUSINESS_QUERIES.get(self.context.action.code, {}))
        aliases = QUERY_RELATIONS.get(self.resource, {})
        lookups = QUERY_LOOKUPS.get(self.resource, {})
        rejected = set()
        for key in request.query_params:
            if key in QUERY_CONTROLS:
                continue
            if key in lookups:
                field, values = lookups[key]
                if field not in readable or any(value.lower() not in values for value in request.query_params.getlist(key)):
                    rejected.add(key)
                continue
            if key in controls:
                field = controls[key]
                if field and field not in readable:
                    rejected.add(key)
                continue
            field = aliases.get(key, key)
            for suffix in ('_after', '_before'):
                if field.endswith(suffix):
                    field = field[:-len(suffix)]
            if field not in readable or ('__' in key and key not in aliases):
                rejected.add(key)
        if request.query_params.get('search'):
            fields = {aliases.get(field.lstrip('^=$@'), field.lstrip('^=$@')) for field in view.search_fields}
            if not fields or not fields <= readable:
                rejected.add('search')
        relation_keys = set(request.query_params) & set(aliases)
        if request.query_params.get('search'):
            relation_keys |= set(view.search_fields) & set(aliases)
        if relation_keys and not self.context.admin:
            from coreadmin.system.models import Role, Dept
            for key in relation_keys:
                resource, model = ('role', Role) if key == 'role__name' else ('dept', Dept)
                child = AccessContext(self.context.user, REGISTRY[resource, 'retrieve', 'GET'])
                if (not child.allowed() or not any(grant.scope == 3 for grant in child.grants)
                        or 'name' not in FieldPolicy(child, model).query_fields()):
                    rejected.add(key)
        if request.query_params.get('ordering'):
            fields = {item.lstrip('-') for item in request.query_params['ordering'].split(',')}
            if not fields <= readable:
                rejected.add('ordering')
        query = request.query_params.get('query')
        if query:
            # Nested RESTQL is deliberately not an implicit relation registry.
            # Flat selection is accepted only for readable fields; aliases,
            # arguments and nested traversal require a separately reviewed API.
            if not re.fullmatch(r'\s*\{\s*[\w\s,]*\}\s*', query):
                rejected.add('query')
            elif not set(re.findall(r'\w+', query)) <= readable:
                rejected.add('query')
        if rejected:
            raise ValidationError({key: 'Query field is not readable.' for key in sorted(rejected)})


def serializer_policy(serializer):
    request = serializer.request
    view = getattr(request, '_canonical_access_view', None) if request else None
    if view is None or serializer.Meta.model is not view.queryset.model:
        return None
    policy = getattr(view, 'field_policy', None)
    if policy is None:
        policy = view.field_policy = FieldPolicy(view.access_context, serializer.Meta.model)
    return policy


def project_relations(policy, instance, data, depth=0):
    if depth > 4:
        return {}
    from coreadmin.system import models
    model_names = {'user': 'Users', 'role': 'Role', 'dept': 'Dept',
                   'system_config': 'SystemConfig', 'menu_button': 'MenuButton', 'area': 'Area'}
    for field, (resource, _) in RELATIONS.get(policy.resource, {}).items():
        if field not in data or data[field] is None:
            continue
        binding = (policy.resource, field)
        child_context = (policy.context if binding in CURRENT_ACTION_RELATIONS else
                         AccessContext(policy.context.user, REGISTRY[resource, 'retrieve', 'GET']))
        multiple = isinstance(data[field], (list, tuple, QuerySet))
        if not child_context.allowed():
            data[field] = [] if multiple else None
            continue
        values = list(data[field]) if multiple else [data[field]]
        identifier = RELATION_IDENTIFIERS.get(binding, 'id')
        identifiers = [value.get(identifier) if isinstance(value, dict) else value for value in values]
        model = getattr(models, model_names[resource])
        queryset = model.objects.all()
        if resource == 'user':
            queryset = queryset.exclude(is_superuser=True)
        objects = {getattr(obj, identifier): obj for obj in
                   child_context.scope(queryset).filter(**{identifier + '__in': identifiers})}
        child_policy = FieldPolicy(child_context, model)
        result = []
        for value, pk in zip(values, identifiers):
            obj = objects.get(pk)
            if obj is None:
                continue
            if isinstance(value, dict):
                value = {key: content for key, content in value.items() if key in child_policy.allowed(obj)}
                value = project_relations(child_policy, obj, value, depth + 1)
            result.append(value)
        data[field] = result if multiple else (result[0] if result else None)
    return data
