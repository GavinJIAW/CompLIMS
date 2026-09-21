"""One request's active grant tuples, shared by action, scope and field policy."""
from dataclasses import dataclass
from functools import cached_property

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from coreadmin.access.registry import Policy, RESOURCES, aliases_for, resolve
from coreadmin.system.models import Dept, RoleMenuButtonPermission


@dataclass(frozen=True)
class Grant:
    id: int
    role_id: int
    menu_id: int
    scope: int
    dept_ids: frozenset


def descendants(dept_id):
    """Finite even when historical parent data contains a cycle."""
    if dept_id is None:
        return frozenset()
    seen, pending = set(), {int(dept_id)}
    while pending:
        seen.update(pending)
        pending = set(Dept.objects.filter(parent_id__in=pending).values_list('id', flat=True)) - seen
    return frozenset(seen)


# Every current resource uses its CoreModel attribution, except Dept itself,
# whose department scope is its primary key. New resources have no fallback.
SCOPE_PROVIDERS = {
    'menu': 'attribution', 'menu_button': 'attribution', 'role': 'attribution',
    'dept': 'department', 'user': 'attribution', 'operation_log': 'attribution',
    'dictionary': 'attribution', 'area': 'attribution', 'file': 'attribution',
    'api_white_list': 'attribution', 'system_config': 'attribution',
    'message_center': 'attribution', 'role_menu_button_permission': 'attribution',
    'role_menu_permission': 'attribution', 'column': 'attribution',
    'login_log': 'attribution', 'download_center': 'attribution',
}
from lims.access_registry import SCOPES as LIMS_SCOPES
SCOPE_PROVIDERS.update(LIMS_SCOPES)


class AccessContext:
    def __init__(self, user, action):
        self.user = user
        self.action = action

    @property
    def active(self):
        return bool(self.user.is_authenticated and self.user.is_active)

    @property
    def admin(self):
        return bool(self.active and self.user.is_superuser)

    def create_attribution(self):
        # User's B1 serializer has no department attribution input/default.
        # The other approved create adapters retain CoreModel's actor dept.
        return {'creator': self.user, 'modifier': str(self.user.pk),
                'dept_belong_id': None if self.action.resource == 'user' or SCOPE_PROVIDERS.get(self.action.resource) == 'shared_all' else self.user.dept_id}

    @cached_property
    def grants(self):
        if not self.active or not self.action or self.action.policy != Policy.ROLE_GRANTABLE:
            return ()
        rows = RoleMenuButtonPermission.objects.filter(
            role__in=self.user.role.filter(status=True),
            menu_button__value__in=aliases_for(self.action.code),
            data_range__in=(0, 1, 2, 3, 4),
        ).select_related('menu_button').prefetch_related('dept').order_by('id')
        if SCOPE_PROVIDERS.get(self.action.resource) == 'shared_all':
            rows = rows.filter(data_range=3)
        return tuple(Grant(row.id, row.role_id, row.menu_button.menu_id, row.data_range,
                           frozenset(dept.id for dept in row.dept.all())) for row in rows)

    def allowed(self):
        if not self.action:
            return False
        if self.action.policy == Policy.PUBLIC:
            return True
        if self.action.policy == Policy.B1_SHUTDOWN:
            return (self.action.shutdown_guard == 'public' or
                    (self.admin if self.action.shutdown_guard == 'superuser' else self.active))
        if not self.active:
            return False
        if self.admin:
            return True
        if self.action.policy == Policy.SELF_SERVICE:
            return True
        return self.action.policy == Policy.ROLE_GRANTABLE and bool(self.grants)

    @cached_property
    def child_depts(self):
        return descendants(self.user.dept_id)

    def grant_depts(self, grant):
        if grant.scope == 4:
            return grant.dept_ids
        if grant.scope == 1:
            return self.child_depts
        if grant.scope == 2 and self.user.dept_id is not None:
            return frozenset({self.user.dept_id})
        return frozenset()

    def predicate(self, grant):
        if grant.scope == 3:
            return Q()
        if grant.scope == 0:
            return Q(creator_id=self.user.id)
        key = 'id__in' if SCOPE_PROVIDERS.get(self.action.resource) == 'department' else 'dept_belong_id__in'
        return Q(**{key: self.grant_depts(grant)})

    def scope(self, queryset):
        if not self.allowed():
            raise PermissionDenied()
        if self.admin or self.action.policy != Policy.ROLE_GRANTABLE:
            return queryset
        if self.action.resource not in SCOPE_PROVIDERS:
            return queryset.none()
        if not any(grant.scope == 3 for grant in self.grants):
            combined = Q(pk__in=[])
            for grant in self.grants:
                combined |= self.predicate(grant)
            queryset = queryset.filter(combined)
        if self.action.resource == 'message_center':
            queryset = queryset.filter(Q(creator_id=self.user.id) | Q(target_user__id=self.user.id))
        return queryset.distinct()

    def contributing(self, instance):
        """Evaluate the same predicates against an object or proposed create DTO."""
        if self.action.resource not in SCOPE_PROVIDERS:
            return ()
        result = []
        for grant in self.grants:
            if grant.scope == 3 or (grant.scope == 0 and instance.creator_id == self.user.id):
                result.append(grant)
            elif grant.scope in (1, 2, 4):
                value = instance.pk if SCOPE_PROVIDERS[self.action.resource] == 'department' else instance.dept_belong_id
                if value is not None and str(value) in {str(pk) for pk in self.grant_depts(grant)}:
                    result.append(grant)
        return tuple(result)


def context_for(request, view):
    context = getattr(view, 'access_context', None)
    if context is None:
        context = view.access_context = AccessContext(request.user, resolve(view, request.method))
    return context
