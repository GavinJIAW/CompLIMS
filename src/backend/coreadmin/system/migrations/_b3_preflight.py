"""Frozen preflight shared by migration 0002 and the read-only command.

Never repairs data or prints credentials. Historical models only.
"""
from django.db.models import Count, F


def inspect_data(apps, alias):
    problems = {}
    def model(name):
        return apps.get_model('system', name)
    keys = {'RoleMenuPermission': ('role', 'menu'),
            'RoleMenuButtonPermission': ('role', 'menu_button'),
            'FieldPermission': ('role', 'field'),
            'MenuField': ('menu', 'model', 'field_name'),
            'MessageCenterTargetUser': ('messagecenter', 'users')}
    for name, fields in keys.items():
        count = model(name).objects.using(alias).values(*fields).annotate(n=Count('pk')).filter(n__gt=1).count()
        if count: problems[name + '.duplicates'] = count
    bindings = {'RoleMenuPermission': ('role', 'menu'),
                'RoleMenuButtonPermission': ('role', 'menu_button'),
                'FieldPermission': ('role', 'field'), 'MenuField': ('menu',),
                'MenuButton': ('menu',), 'Users': ('dept',), 'Dept': ('parent',),
                'MessageCenterTargetUser': ('messagecenter', 'users'), 'SystemConfig': ('parent',)}
    for name, fields in bindings.items():
        cls = model(name)
        for field in fields:
            f = cls._meta.get_field(field)
            count = cls.objects.using(alias).filter(**{field + '__isnull': False}).exclude(
                **{f.attname + '__in': f.remote_field.model.objects.using(alias).values(f.target_field.name)}).count()
            if count: problems[name + '.' + field + '.orphan'] = count
    for name, field in [('Users', 'role'), ('RoleMenuButtonPermission', 'dept')]:
        through = model(name)._meta.get_field(field).remote_field.through
        for f in through._meta.fields:
            if f.many_to_one:
                count = through.objects.using(alias).exclude(**{f.attname + '__in':
                    f.remote_field.model.objects.using(alias).values(f.target_field.name)}).count()
                if count: problems[through._meta.db_table + '.' + f.name] = count
    grants = model('RoleMenuButtonPermission').objects.using(alias)
    for label, count in [('null_button', grants.filter(menu_button__isnull=True).count()),
                         ('invalid_scope', grants.exclude(data_range__in=[0, 1, 2, 3, 4]).count())]:
        if count: problems[label] = count
    roots = model('SystemConfig').objects.using(alias).filter(parent__isnull=True)
    count = roots.values('key').annotate(n=Count('pk')).filter(n__gt=1).count()
    if count: problems['root_config_duplicates'] = count
    edges = dict(model('Dept').objects.using(alias).values_list('pk', 'parent_id'))
    cycles = set()
    for node in edges:
        seen = []
        while node in edges and node is not None:
            if node in seen:
                cycles.add(tuple(sorted(seen[seen.index(node):])))
                break
            seen.append(node)
            node = edges[node]
    if cycles: problems['dept_cycles'] = len(cycles)
    # Empty/legacy passwords intentionally remain RESET REQUIRED, never repaired.
    return problems


def require_clean(apps, schema_editor):
    problems = inspect_data(apps, schema_editor.connection.alias)
    if problems:
        raise RuntimeError('B3 preflight failed; Data Cleanup Task required: ' + str(problems))
