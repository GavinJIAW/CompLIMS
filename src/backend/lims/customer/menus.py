from coreadmin.system.models import Menu, MenuField
from coreadmin.system.fixtures.initSerializer import MenuInitSerializer
from .access_contract import READ


def initialize_customer():
    root, _ = Menu.objects.update_or_create(component_name='lims_customer_root', defaults=dict(name='客户管理', web_path='/lims/customer-management', is_catalog=True, sort=22, status=True))
    for resource, model, title in [('customer', 'Customer', '客户管理'), ('contact', 'CustomerContact', '联系人管理')]:
        existing = Menu.objects.filter(component_name=f'lims_{resource}').first()
        if resource == 'customer' and existing:
            MenuField.objects.filter(menu=existing, model='CustomerContact').delete()
            MenuField.objects.filter(menu=existing, model='Customer', field_name='contacts').delete()
        buttons = [dict(name=label, value=f'{resource}:{suffix}', api=f'/api/lims/{resource}/', method=method)
                   for suffix, label, method in [('Search', '查询', 0), ('Retrieve', '详情', 0), ('Create', '新增', 1), ('Update', '修改', 2), ('Delete', '删除', 3)]]
        fields = [dict(model=model, field_name=key, title=key) for key in READ[resource].split()]
        serializer = MenuInitSerializer(existing, data=dict(name=title, parent=root.pk, web_path=f'/lims/{resource}', component=f'lims/customer/{resource}/index', component_name=f'lims_{resource}', is_catalog=False, status=True, menu_button=buttons, menu_field=fields))
        serializer.is_valid(raise_exception=True)
        serializer.save()
