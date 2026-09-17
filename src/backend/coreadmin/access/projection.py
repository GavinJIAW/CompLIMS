"""UI hints derived from canonical policy; never an authorization cache."""
from coreadmin.access.registry import ALIASES, REGISTRY, Policy
from coreadmin.access.context import AccessContext
from coreadmin.access.fields import FieldPolicy, READ


def alias_diagnostic(value):
    code = ALIASES.get(value)
    actions = [action for action in REGISTRY.values() if action.code == code]
    policy = actions[0].policy.value if actions else 'UNREGISTERED'
    return {'canonical_action': code, 'mapping_status': policy,
            'grantable': policy == Policy.ROLE_GRANTABLE.value}


def button_aliases(user):
    actions = {action.code: action for action in REGISTRY.values() if action.policy != Policy.B1_SHUTDOWN}
    allowed = {code for code, action in actions.items() if AccessContext(user, action).allowed()}
    return sorted(alias for alias, code in ALIASES.items() if code in allowed)


def field_metadata(user, resource, model):
    result = {name: {'is_query': False, 'is_create': False, 'is_update': False} for name in READ[resource]}
    for action, method, mode, flag in [('list', 'GET', 'read', 'is_query'),
                                       ('create', 'POST', 'create', 'is_create'),
                                       ('update', 'PUT', 'update', 'is_update')]:
        context = AccessContext(user, REGISTRY[resource, action, method])
        if not context.allowed() or context.action.policy == Policy.B1_SHUTDOWN:
            continue
        policy = FieldPolicy(context, model)
        fields = policy.ceiling(mode) if context.admin else policy.for_grants(context.grants, mode)
        for name in fields:
            result.setdefault(name, {'is_query': False, 'is_create': False, 'is_update': False})[flag] = True
    return result
