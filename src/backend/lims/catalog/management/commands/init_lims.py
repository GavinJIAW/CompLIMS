"""Explicit, idempotent menu setup; never runs during import or migration."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from coreadmin.system.fixtures.initSerializer import MenuInitSerializer
from coreadmin.system.models import Menu, MenuField, Role, RoleMenuPermission, RoleMenuButtonPermission, FieldPermission
from lims.shared.contract import READ, WRITE, ROW_FIELDS

RESOURCES = [('service', 'Service', '技术服务'), ('cost_item', 'CostItem', '成本项'),
             ('cost_package', 'CostPackage', '成本包'), ('product', 'Product', '产品'), ('scheme', 'Scheme', '技术方案')]
ROWS = {'cost_package': 'CostPackageItem', 'product': 'ProductCostPackage', 'scheme': 'SchemeItem'}
GROUPS = {'costing': '成本管理', 'catalog': '服务目录'}
PAGES = {'cost_item': ('costing', 'costItem'), 'cost_package': ('costing', 'costPackage'),
         'service': ('catalog', 'service'), 'product': ('catalog', 'product'), 'scheme': ('catalog', 'scheme')}


class Command(BaseCommand):
    help = 'Create M1 menus/fields; optionally grant an explicitly named existing role ALL-scope M1 management.'

    def add_arguments(self, parser):
        parser.add_argument('--role-key', help='Optional existing role to grant; no role/user is created.')

    @transaction.atomic
    def handle(self, *args, **options):
        role = None
        if options['role_key']:
            role = Role.objects.select_for_update().filter(key=options['role_key'], status=True).first()
            if role is None:
                raise CommandError('An active existing role is required.')
        roots = {}
        for index, (key, title) in enumerate(GROUPS.items()):
            roots[key], _ = Menu.objects.update_or_create(component_name=f'lims_{key}', defaults={
                'name': title, 'web_path': f'/lims/{key}', 'is_catalog': True, 'sort': 20 + index, 'status': True})
            if role:
                RoleMenuPermission.objects.get_or_create(role=role, menu=roots[key])
        for index, (resource, model, title) in enumerate(RESOURCES):
            buttons = [{'name': label, 'value': f'{resource}:{suffix}', 'api': f'/api/lims/{resource}/', 'method': method}
                       for suffix, label, method in [('Search', '查询', 0), ('Retrieve', '详情', 0),
                           ('Create', '新增', 1), ('Update', '修改', 2), ('Delete', '删除', 3)]]
            fields = [{'model': model, 'field_name': key, 'title': key} for key in READ[resource].split()]
            if resource in ROWS:
                fields += [{'model': ROWS[resource], 'field_name': key, 'title': key} for key in ROW_FIELDS[ROWS[resource]].split()]
            group, page = PAGES[resource]
            data = dict(name='方案' if resource == 'scheme' else title, parent=roots[group].pk, web_path=f'/lims/{resource}', component=f'lims/{group}/{page}/index',
                        component_name=f'lims_{resource}', sort=index * 10, is_catalog=False, status=True,
                        menu_button=buttons, menu_field=fields)
            existing = Menu.objects.filter(component_name=data['component_name']).first()
            serializer = MenuInitSerializer(existing, data=data)
            serializer.is_valid(raise_exception=True)
            menu = serializer.save()
            if role:
                RoleMenuPermission.objects.get_or_create(role=role, menu=menu)
                for button in menu.menuPermission.all():
                    grant, _ = RoleMenuButtonPermission.objects.update_or_create(role=role, menu_button=button, defaults={'data_range': 3})
                    grant.dept.clear()
                for field in MenuField.objects.filter(menu=menu):
                    writable = field.field_name in (WRITE[resource].split() if field.model == model else ROW_FIELDS[field.model].split())
                    FieldPermission.objects.update_or_create(role=role, field=field, defaults={
                        'is_query': True, 'is_create': writable and field.field_name != 'id',
                        'is_update': writable and field.field_name not in ('id', 'number')})
        self.stdout.write(self.style.SUCCESS('M1 menu configuration ready; role grants applied only if explicitly requested.'))
        from lims.shared.m2_menus import initialize_m2
        initialize_m2()
        self.stdout.write(self.style.SUCCESS('M2 metadata ready; no M2 role grants applied.'))
