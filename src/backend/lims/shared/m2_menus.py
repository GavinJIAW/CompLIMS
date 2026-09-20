"""Idempotent M2 metadata only: deliberately never expands existing role grants."""
from coreadmin.system.models import Menu
from coreadmin.system.fixtures.initSerializer import MenuInitSerializer
from .m2_contract import READ, CHILD_READ, CHILDREN, ACTIONS


def initialize_m2():
    roots = {}
    for index, (name, title) in enumerate([('customer', '客户管理'), ('commercial', '商务管理')]):
        root_path = '/lims/customer-management' if name == 'customer' else '/lims/commercial'
        roots[name], _ = Menu.objects.update_or_create(component_name=f'lims_{name}_root', defaults={'name': title, 'web_path': root_path, 'is_catalog': True, 'sort': 22 + index, 'status': True})
    for resource, model, title in [('customer', 'Customer', '客户'), ('quotation', 'Quotation', '报价'), ('contract', 'Contract', '合同')]:
        group = 'customer' if resource == 'customer' else 'commercial'
        buttons = [{'name': label, 'value': f'{resource}:{suffix}', 'api': f'/api/lims/{resource}/', 'method': method} for suffix, label, method in [('Search', '查询', 0), ('Retrieve', '详情', 0), ('Create', '新增', 1), ('Update', '修改', 2), ('Delete', '删除', 3)]]
        labels = {'Send': '发送', 'Accept': '接受', 'Reject': '拒绝', 'Void': '作废', 'Sign': '签署', 'CreateContract': '创建合同'}
        buttons += [{'name': labels[suffix], 'value': f'{resource}:{suffix}', 'api': f'/api/lims/{resource}/{{id}}/{action}/', 'method': 1} for suffix, action in ACTIONS[resource].items()]
        fields = [{'model': model, 'field_name': key, 'title': key} for key in READ[resource].split()]
        for child in CHILDREN[resource]:
            fields += [{'model': child, 'field_name': key, 'title': key} for key in CHILD_READ[child].split()]
        data = dict(name=title, parent=roots[group].pk, web_path=f'/lims/{resource}', component=f'lims/{group}/{resource}/index', component_name=f'lims_{resource}', is_catalog=False, status=True, menu_button=buttons, menu_field=fields)
        serializer = MenuInitSerializer(Menu.objects.filter(component_name=data['component_name']).first(), data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
