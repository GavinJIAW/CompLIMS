from copy import deepcopy
from decimal import Decimal
from django.test import TestCase, override_settings
from django.core.management import call_command
from rest_framework.test import APIClient
from coreadmin.system.models import Users, Dept, MenuField, FieldPermission, RoleMenuButtonPermission, Menu, MenuButton, OperationLog
from coreadmin.foundation_tests.access_fixtures import grant
from lims.customer.models import Customer
from lims.catalog.models import Service, Product, Scheme, SchemeItem
from lims.shared.m2_contract import READ, WRITE, CHILDREN, CHILD_READ, CHILD_CREATE, CHILD_UPDATE
from lims.shared.contract import READ as M1_READ
from lims.commercial.models import Quotation, Contract


class WorkflowTests(TestCase):
    def setUp(self):
        self.admin = Users.objects.create(username='m2admin', is_superuser=True, pwd_change_count=1)
        self.dept = Dept.objects.create(name='Sales')
        self.actor = Users.objects.create(username='m2actor', dept=self.dept, pwd_change_count=1)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.customer = Customer.objects.create(number='C1', name='Original customer')
        self.schema = [{'key': 'count', 'label': '数量', 'type': 'integer', 'required': True}, {'key': 'mode', 'label': '条件', 'type': 'select', 'required': False, 'options': [{'value': 'A', 'label': 'A'}]}]
        self.service = Service.objects.create(number='S1', name='Service', requirement_template=self.schema)
        self.product = Product.objects.create(number='P1', name='Original product', unit='test', service=self.service, reference_price='0.01', requirement_defaults={'mode': 'A'})
        self.scheme = Scheme.objects.create(number='SC1', name='Original scheme')
        SchemeItem.objects.create(scheme=self.scheme, product=self.product, sequence=10, requirement_override={'count': 6})

    def api(self, method, resource, data=None, pk=None, action=None, status=200):
        url = f'/api/lims/{resource}/' + (f'{pk}/' if pk else '') + (f'{action}/' if action else '')
        response = getattr(self.client, method)(url, data=data, format='json')
        self.assertEqual(response.status_code, status, response.data)
        return response.data.get('data')

    def create(self, resource='quotation', number='Q1', **extra):
        body = {'number': number, 'customer': self.customer.pk, resource + '_date': '2026-09-20', 'schemes': [{'source_scheme': self.scheme.pk, 'sequence': 10}]}
        body.update(extra)
        return self.api('post', resource, body)

    def permit(self, resource, suffix, scope=3, user=None):
        names = {'customer': 'Customer', 'quotation': 'Quotation', 'contract': 'Contract'}
        permission = grant(user or self.actor, f'{resource}:{suffix}', names[resource], fields=READ[resource].split(), create=WRITE[resource].split(), update=WRITE[resource].split(), scope=scope)
        for child in CHILDREN[resource]:
            for key in CHILD_READ[child].split():
                field, _ = MenuField.objects.get_or_create(menu=permission.menu_button.menu, model=child, field_name=key, defaults={'title': key})
                FieldPermission.objects.update_or_create(role=permission.role, field=field, defaults={'is_query': True, 'is_create': key in CHILD_CREATE[child].split(), 'is_update': key in CHILD_UPDATE[child].split()})
        return permission

    def permit_sources(self):
        self.permit('customer', 'Retrieve')
        for resource, model in [('service', 'Service'), ('product', 'Product'), ('scheme', 'Scheme')]:
            permission = grant(self.actor, f'{resource}:Retrieve', model, fields=M1_READ[resource].split(), scope=3)
            if resource == 'scheme':
                for key in ('id', 'product', 'sequence', 'requirement_override', 'remark'):
                    field, _ = MenuField.objects.get_or_create(menu=permission.menu_button.menu, model='SchemeItem', field_name=key)
                    FieldPermission.objects.create(role=permission.role, field=field, is_query=True)

    def test_full_scheme_to_contract_workflow(self):
        q = self.create()
        self.assertEqual(q['subtotal'], '0.01')
        self.assertEqual(q['schemes'][0]['items'][0]['requirement_data'], {'mode': 'A', 'count': 6})
        for action in ('send', 'accept'):
            self.api('post', 'quotation', {}, q['id'], action)
        c = self.api('post', 'quotation', {'number': 'C001', 'contract_date': '2026-09-20'}, q['id'], 'create_contract')
        contract = Contract.objects.get(pk=c['id'])
        self.assertEqual(contract.source_quotation_id, q['id'])
        self.api('post', 'contract', {}, c['id'], 'sign')
        contract.refresh_from_db()
        self.assertEqual(contract.status, 'SIGNED')
        self.assertEqual(contract.signed_by_id, self.admin.pk)
        self.assertIsNotNone(contract.signed_at)

    def test_snapshot_independence_and_source_delete(self):
        q = self.create()
        self.customer.name = 'Changed'; self.customer.save()
        self.product.name = 'Changed'; self.product.save()
        self.service.requirement_template = []; self.service.save()
        self.scheme.delete()
        self.product.delete()
        actual = self.api('get', 'quotation', pk=q['id'])
        self.assertEqual(actual['customer_name_snapshot'], 'Original customer')
        item = actual['schemes'][0]['items'][0]
        self.assertEqual(item['name_snapshot'], 'Original product')
        self.assertEqual(item['requirement_schema'], self.schema)
        self.assertIsNone(item['source_product'])
        self.assertIsNone(actual['schemes'][0]['source_scheme'])

    def test_direct_product_partial_requirements_and_half_up(self):
        q = self.create(schemes=[{'sequence': 1, 'name_snapshot': 'Custom', 'items': [{'sequence': 1, 'source_product': self.product.pk, 'quantity': '1.500000'}]}])
        self.assertEqual(q['subtotal'], '0.02')
        self.assertNotIn('count', q['schemes'][0]['items'][0]['requirement_data'])
        self.api('post', 'quotation', {}, q['id'], 'send')

    def test_retained_identity_reorder_and_omission(self):
        q = self.create(schemes=[{'sequence': 1, 'name_snapshot': 'Custom', 'items': [{'sequence': 1, 'source_product': self.product.pk}, {'sequence': 2, 'source_product': self.product.pk}]}])
        group = q['schemes'][0]; first, second = group['items']
        updated = self.api('patch', 'quotation', {'schemes': [{'id': group['id'], 'items': [{'id': first['id'], 'sequence': 2}, {'id': second['id'], 'sequence': 1}]}]}, q['id'])
        self.assertEqual([r['id'] for r in updated['schemes'][0]['items']], [second['id'], first['id']])
        updated = self.api('patch', 'quotation', {'remark': 'header'}, q['id'])
        self.assertEqual(len(updated['schemes'][0]['items']), 2)
        updated = self.api('patch', 'quotation', {'schemes': [{'id': group['id'], 'items': []}]}, q['id'])
        self.assertEqual(updated['subtotal'], '0.00')

    def test_deep_failure_rolls_back_header_and_children(self):
        q = self.create(); group = q['schemes'][0]
        self.api('patch', 'quotation', {'remark': 'MUST ROLLBACK', 'schemes': [{'id': group['id'], 'items': [{'source_product': self.product.pk, 'sequence': 1}, {'source_product': self.product.pk, 'sequence': 2, 'quantity': '0'}]}]}, q['id'], status=400)
        obj = Quotation.objects.get(pk=q['id'])
        self.assertEqual(obj.remark, '')
        self.assertEqual(obj.schemes.get().items.count(), 1)

    def test_foreign_child_id_rejected(self):
        first = self.create(); second = self.create(number='Q2')
        self.api('patch', 'quotation', {'schemes': [{'id': second['schemes'][0]['id']}]}, first['id'], status=400)

    def test_locked_body_and_delete(self):
        q = self.create()
        self.api('post', 'quotation', {}, q['id'], 'send')
        self.api('patch', 'quotation', {'remark': 'bad'}, q['id'], status=409)
        self.api('delete', 'quotation', pk=q['id'], status=409)
        self.api('post', 'quotation', {}, q['id'], 'send', status=409)

    def test_all_terminal_quotation_transitions(self):
        for action, expected in [('accept', 'ACCEPTED'), ('reject', 'REJECTED'), ('void', 'VOID')]:
            q = self.create(number=action)
            self.api('post', 'quotation', {}, q['id'], action, status=409)
            self.api('post', 'quotation', {}, q['id'], 'send')
            self.api('post', 'quotation', {}, q['id'], action)
            self.assertEqual(Quotation.objects.get(pk=q['id']).status, expected)

    def test_readonly_number_state_schema_amounts(self):
        q = self.create()
        for body in [{'number': 'OTHER'}, {'status': 'SENT'}, {'subtotal': '1'}, {'sent_by': self.admin.pk}]:
            self.api('patch', 'quotation', body, q['id'], status=400)
        row = q['schemes'][0]['items'][0]
        for key, value in [('source_product', self.product.pk), ('requirement_schema', []), ('product_number_snapshot', 'X'), ('line_amount', '5')]:
            self.api('patch', 'quotation', {'schemes': [{'id': q['schemes'][0]['id'], 'items': [{'id': row['id'], key: value}]}]}, q['id'], status=400)

    def test_requirements_invalid_values(self):
        q = self.create(); group = q['schemes'][0]; row = group['items'][0]
        for values in [{'unknown': 1}, {'count': 'bad'}, {'mode': 'INVALID'}]:
            self.api('patch', 'quotation', {'schemes': [{'id': group['id'], 'items': [{'id': row['id'], 'requirement_data': values}]}]}, q['id'], status=400)

    def test_adjustments_zero_price_and_overflow(self):
        q = self.create()
        self.assertEqual(self.api('patch', 'quotation', {'adjustment_amount': '-0.01'}, q['id'])['total_amount'], '0.00')
        self.api('patch', 'quotation', {'adjustment_amount': '-0.02'}, q['id'], status=400)
        self.assertEqual(self.api('patch', 'quotation', {'adjustment_amount': '1.00'}, q['id'])['total_amount'], '1.01')
        self.create(number='FREE', schemes=[{'sequence': 1, 'name_snapshot': 'Free', 'items': [{'sequence': 1, 'source_product': self.product.pk, 'unit_price': '0'}]}])
        self.api('post', 'quotation', {'number': 'BIG', 'customer': self.customer.pk, 'quotation_date': '2026-09-20', 'schemes': [{'sequence': 1, 'name_snapshot': 'Big', 'items': [{'sequence': 1, 'source_product': self.product.pk, 'unit_price': '999999999999999999.99', 'quantity': '2'}]}]}, status=400)

    def test_disabled_existing_snapshot_allowed_new_rejected(self):
        q = self.create()
        for obj in (self.customer, self.product, self.scheme):
            obj.enabled = False; obj.save()
        self.api('patch', 'quotation', {'remark': 'still valid'}, q['id'])
        self.api('post', 'quotation', {}, q['id'], 'send')
        self.api('post', 'quotation', {}, q['id'], 'accept')
        self.api('post', 'quotation', {'number': 'NO', 'contract_date': '2026-09-20'}, q['id'], 'create_contract', status=400)

    def test_conversion_once_and_current_actor(self):
        q = self.create()
        for action in ('send', 'accept'): self.api('post', 'quotation', {}, q['id'], action)
        self.permit('quotation', 'CreateContract'); self.permit('contract', 'Create', 0); self.permit('customer', 'Retrieve')
        self.client.force_authenticate(self.actor)
        data = self.api('post', 'quotation', {'number': 'CONV', 'contract_date': '2026-09-20'}, q['id'], 'create_contract')
        contract = Contract.objects.get(pk=data['id'])
        self.assertEqual(contract.creator_id, self.actor.pk)
        self.assertEqual(str(contract.dept_belong_id), str(self.dept.pk))
        self.assertEqual(contract.subtotal, Decimal('0.01'))
        self.api('post', 'quotation', {'number': 'CONV2', 'contract_date': '2026-09-20'}, q['id'], 'create_contract', status=409)

    def test_direct_contract_lock_void_and_delete(self):
        c = self.create('contract', 'C001')
        self.api('post', 'contract', {}, c['id'], 'sign')
        self.api('patch', 'contract', {'remark': 'bad'}, c['id'], status=409)
        self.api('delete', 'contract', pk=c['id'], status=409)
        self.api('post', 'contract', {}, c['id'], 'void')
        self.api('post', 'contract', {}, c['id'], 'void', status=409)
        draft = self.create('contract', 'C002')
        self.api('delete', 'contract', pk=draft['id'])

    def test_unauthorized_actions_and_detail(self):
        q = self.create(); self.client.force_authenticate(self.actor)
        for resource in ('customer', 'quotation', 'contract'):
            self.api('get', resource, status=403)
        self.api('get', 'quotation', pk=q['id'], status=403)
        self.api('post', 'quotation', {}, q['id'], 'send', status=403)

    def test_normal_actor_create_and_relation_permission(self):
        self.permit('quotation', 'Create', 0)
        self.client.force_authenticate(self.actor)
        body = {'number': 'NORMAL', 'customer': self.customer.pk, 'quotation_date': '2026-09-20'}
        self.api('post', 'quotation', body, status=403)
        self.permit_sources()
        self.api('post', 'quotation', body)

    def test_scope_variants_and_out_of_scope(self):
        q = self.create(); obj = Quotation.objects.get(pk=q['id'])
        child = Dept.objects.create(name='Child', parent=self.dept)
        for scope in (0, 1, 2, 3, 4):
            permission = self.permit('quotation', 'Retrieve', scope)
            if scope == 4: permission.dept.add(child)
            obj.creator = self.actor if scope == 0 else self.admin
            obj.dept_belong_id = child.pk if scope in (1, 4) else self.dept.pk
            obj.save()
            self.client.force_authenticate(self.actor)
            self.api('get', 'quotation', pk=q['id'])
            if scope != 3:
                obj.creator = self.admin; obj.dept_belong_id = None; obj.save()
                self.api('get', 'quotation', pk=q['id'], status=404)
            permission.delete()

    def test_field_query_and_nested_scope_grants(self):
        q = self.create(); obj = Quotation.objects.get(pk=q['id']); obj.dept_belong_id = self.dept.pk; obj.save()
        permitted = self.permit('quotation', 'Retrieve', 2)
        noncontributing = self.permit('quotation', 'Retrieve', 0)
        FieldPermission.objects.filter(role=permitted.role, field__model='QuotationSchemeItem', field__field_name='unit_price').update(is_query=False)
        self.client.force_authenticate(self.actor)
        result = self.api('get', 'quotation', pk=q['id'])
        self.assertNotIn('unit_price', result['schemes'][0]['items'][0])
        self.assertNotIn('line_amount', result['schemes'][0]['items'][0])
        self.assertNotIn('subtotal', result)
        self.assertNotIn('total_amount', result)
        listing = self.permit('quotation', 'Search', 3)
        FieldPermission.objects.filter(role=listing.role, field__model='Quotation', field__field_name='customer_name_snapshot').update(is_query=False)
        for query in ('customer_name_snapshot=X', 'search=X', 'ordering=customer_name_snapshot'):
            response = self.client.get('/api/lims/quotation/?' + query)
            self.assertEqual(response.status_code, 400)

    @override_settings(API_LOG_ENABLE=True, API_LOG_METHODS=['POST', 'PUT', 'DELETE'])
    def test_action_audit_trusted_targets(self):
        q = self.create()
        self.api('post', 'quotation', {'id': 999999}, q['id'], 'send', status=400)
        self.api('post', 'quotation', {}, q['id'], 'send')
        log = OperationLog.objects.filter(request_path__contains='/send/').latest('id')
        self.assertIn(str(q['id']), log.request_target)
        self.assertNotIn('999999', log.request_target)

    @override_settings(API_LOG_ENABLE=True, API_LOG_METHODS=['POST', 'PUT', 'DELETE'])
    def test_conversion_audit_records_both_resolved_targets(self):
        import json
        q = self.create()
        for action in ('send', 'accept'):
            self.api('post', 'quotation', {}, q['id'], action)
        contract = self.api('post', 'quotation', {
            'number': 'AUDIT-C', 'contract_date': '2026-09-20',
        }, q['id'], 'create_contract')
        log = OperationLog.objects.filter(request_path__contains='/create_contract/').latest('id')
        targets = json.loads(log.request_target)
        self.assertEqual(targets['quotation'], [q['id']])
        self.assertEqual(targets['contract'], [contract['id']])

    def test_menu_idempotent_no_m2_role_grants(self):
        call_command('init_lims', verbosity=0)
        counts = (Menu.objects.count(), MenuButton.objects.count(), MenuField.objects.count(), RoleMenuButtonPermission.objects.count())
        call_command('init_lims', verbosity=0)
        self.assertEqual(counts, (Menu.objects.count(), MenuButton.objects.count(), MenuField.objects.count(), RoleMenuButtonPermission.objects.count()))
        root = Menu.objects.get(component_name='lims_customer_root')
        page = Menu.objects.get(component_name='lims_customer')
        self.assertNotEqual(root.web_path, page.web_path)
