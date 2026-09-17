"""Explicit canonical grants for isolated tests; no URL/whitelist authorization."""
from coreadmin.system.models import Menu, MenuButton, Role, RoleMenuButtonPermission, MenuField, FieldPermission


def grant(user, alias, model, fields=(), scope=3, departments=(), role=None, menu=None,
          create=(), update=()):
    role = role or Role.objects.create(name='Access fixture', key=f'access-{Role.objects.count()}')
    user.role.add(role)
    menu = menu or Menu.objects.create(name='Access fixture')
    button, _ = MenuButton.objects.get_or_create(value=alias, defaults={
        'name': alias, 'menu': menu, 'api': '/deliberately-not-authority/', 'method': 3})
    menu = button.menu
    permission = RoleMenuButtonPermission.objects.create(role=role, menu_button=button, data_range=scope)
    permission.dept.set(departments)
    for name in set(fields) | set(create) | set(update):
        field, _ = MenuField.objects.get_or_create(menu=menu, model=model, field_name=name, defaults={'title': name})
        FieldPermission.objects.update_or_create(role=role, field=field, defaults={
            'is_query': name in fields, 'is_create': name in create, 'is_update': name in update})
    return permission
