from django.test import TestCase, SimpleTestCase
from rest_framework.test import APIClient
from coreadmin.system.models import Users, FieldPermission, MenuField
from coreadmin.foundation_tests.access_fixtures import grant
from coreadmin.access.registry import resolve
from lims.shared.contract import READ, WRITE, ROW_FIELDS
from lims.costing.models import CostType, CostItem, CostPackage, CostPackageItem
from lims.catalog.models import Service, Product, ProductCostPackage, Scheme, SchemeItem
from lims.catalog.tests import test_models

MODEL_NAMES = {'cost_type': 'CostType', 'service': 'Service', 'cost_item': 'CostItem', 'cost_package': 'CostPackage', 'product': 'Product', 'scheme': 'Scheme'}

MODEL_CLASSES = {'cost_type': CostType, 'service': Service, 'cost_item': CostItem, 'cost_package': CostPackage, 'product': Product, 'scheme': Scheme}


class RouteTests(SimpleTestCase):
    def test_every_route_method(self):
        from lims.urls import urlpatterns
        for pattern in urlpatterns:
            view = pattern.callback.cls()
            for method, action in pattern.callback.actions.items():
                view.action = action
                self.assertIsNotNone(resolve(view, method.upper()), (str(pattern.pattern), method))
                if method == 'get':
                    self.assertIsNotNone(resolve(view, 'HEAD'))
            self.assertIsNotNone(resolve(view, 'OPTIONS'))


class ApiTests(TestCase):
    def setUp(self):
        test_models.ModelTests.setUp(self)
        self.admin = Users.objects.create(username='admin', is_superuser=True, pwd_change_count=1)
        self.actor = Users.objects.create(username='actor', pwd_change_count=1)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def url(self, resource, obj=None):
        return f'/api/lims/{resource}/' + (f'{obj.pk}/' if obj else '')

    def grant_all(self, resource, suffix='Retrieve', scope=3):
        permission = grant(self.actor, f'{resource}:{suffix}', MODEL_NAMES[resource], fields=READ[resource].split(),
            create=WRITE[resource].split(), update=WRITE[resource].split(), scope=scope)
        row_models = {'cost_package': 'CostPackageItem', 'product': 'ProductCostPackage', 'scheme': 'SchemeItem'}
        if resource in row_models:
            name = row_models[resource]
            for key in ROW_FIELDS[name].split():
                field, _ = MenuField.objects.get_or_create(menu=permission.menu_button.menu, model=name, field_name=key, defaults={'title': key})
                FieldPermission.objects.create(role=permission.role, field=field)
        return permission

    def test_full_master_crud(self):
        for resource, payload in [
            ('cost_type', {}),
            ('service', {'service_type': 'Mechanical'}),
            ('cost_item', {'cost_type': self.cost_type.pk, 'unit': 'hour', 'unit_cost': '0.42'}),
            ('cost_package', {'unit': 'hour', 'items': []}),
            ('product', {'service': self.service.pk, 'unit': 'test', 'reference_price': '12.00', 'packages': []}),
            ('scheme', {'items': []}),
        ]:
            with self.subTest(resource=resource):
                payload.update(number='NEW', name='New')
                response = self.client.post(self.url(resource), payload, format='json')
                self.assertEqual(response.status_code, 200, response.data)
                obj = MODEL_CLASSES[resource].objects.get(number='NEW')
                self.assertIsNone(obj.dept_belong_id)
                self.assertEqual(self.client.get(self.url(resource, obj)).status_code, 200)
                self.assertEqual(self.client.patch(self.url(resource, obj), {'name': 'Changed'}, format='json').status_code, 200)
                self.assertEqual(self.client.put(self.url(resource, obj), payload, format='json').status_code, 200)
                self.assertEqual(self.client.patch(self.url(resource, obj), {'number': 'OTHER'}, format='json').status_code, 400)
                self.assertEqual(self.client.delete(self.url(resource, obj)).status_code, 200)

    def test_action_scope_and_object(self):
        self.client.force_authenticate(self.actor)
        self.assertEqual(self.client.get(self.url('service')).status_code, 403)
        self.grant_all('service', 'Search', scope=0)
        self.assertEqual(self.client.get(self.url('service')).status_code, 403)
        permission = self.grant_all('service', 'Retrieve')
        self.assertEqual(self.client.get(self.url('service', self.service)).status_code, 200)
        self.assertEqual(self.client.get('/api/lims/service/99999/').status_code, 404)
        permission.role.status = False
        permission.role.save()
        self.assertEqual(self.client.get(self.url('service', self.service)).status_code, 403)

    def test_field_query_and_hard_ceiling(self):
        self.client.force_authenticate(self.actor)
        grant(self.actor, 'service:Search', 'Service', fields=['name'])
        result = self.client.get(self.url('service'))
        self.assertEqual(set(result.data['data'][0]), {'id', 'name'})
        for params in ({'number': 'S'}, {'ordering': 'number'}, {'search': 'Service'}, {'requirement_template__x': 'y'}):
            self.assertEqual(self.client.get(self.url('service'), params).status_code, 400)
        grant(self.actor, 'service:Update', 'Service', update=['name', 'creator'])
        self.assertEqual(self.client.patch(self.url('service', self.service), {'creator': self.actor.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(self.url('service', self.service), {'name': 'Allowed'}, format='json').status_code, 200)

    def test_role_create_and_target_reference_authority(self):
        self.client.force_authenticate(self.actor)
        self.grant_all('product', 'Create')
        payload = {'number': 'P2', 'name': 'Product', 'service': self.service.pk, 'unit': 'test', 'reference_price': '1.00'}
        self.assertEqual(self.client.post(self.url('product'), payload, format='json').status_code, 403)
        self.grant_all('service')
        response = self.client.post(self.url('product'), payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)

    def test_all_composition_reference_permissions(self):
        for resource, obj, field, target, target_obj, row in [
            ('cost_package', self.package, 'items', 'cost_item', self.item, {'item': self.item.pk, 'quantity': '1', 'sequence': 10}),
            ('product', self.product, 'packages', 'cost_package', self.package, {'package': self.package.pk, 'quantity': '1', 'sequence': 10}),
            ('scheme', self.scheme, 'items', 'product', self.product, {'product': self.product.pk, 'sequence': 10}),
        ]:
            self.client.force_authenticate(self.actor)
            self.grant_all(resource, 'Update')
            self.assertEqual(self.client.patch(self.url(resource, obj), {field: [row]}, format='json').status_code, 403)
            self.grant_all(target)
            result = self.client.patch(self.url(resource, obj), {field: [row]}, format='json')
            self.assertEqual(result.status_code, 200, result.data)

    def test_template_mutation_rejects_invalidation(self):
        template = [{'key': 'n', 'label': 'Count', 'type': 'integer', 'required': True}]
        self.client.patch(self.url('service', self.service), {'requirement_template': template}, format='json')
        response = self.client.patch(self.url('product', self.product), {'requirement_defaults': {'n': 3}}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.patch(self.url('service', self.service), {'requirement_template': []}, format='json')
        self.assertEqual(response.status_code, 400)
        self.service.refresh_from_db()
        self.assertEqual(self.service.requirement_template, template)

    def test_invalid_product_defaults_and_scheme_override(self):
        for resource, obj, payload in [('product', self.product, {'requirement_defaults': {'unknown': 1}}),
            ('scheme', self.scheme, {'items': [{'product': self.product.pk, 'sequence': 10, 'requirement_override': {'unknown': 1}}]})]:
            response = self.client.patch(self.url(resource, obj), payload, format='json')
            self.assertEqual(response.status_code, 400, response.data)

    def test_repeated_product_and_reorder_identity(self):
        rows = [{'product': self.product.pk, 'sequence': i} for i in (10, 20)]
        response = self.client.patch(self.url('scheme', self.scheme), {'items': rows}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        saved = list(self.scheme.items.values('id', 'product', 'sequence', 'remark', 'requirement_override'))
        saved[0]['sequence'], saved[1]['sequence'] = 20, 10
        response = self.client.patch(self.url('scheme', self.scheme), {'items': saved}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row['sequence'] for row in response.data['data']['items']], [10, 20])

    def test_disabled_targets_and_existing_relationship(self):
        row = CostPackageItem.objects.create(package=self.package, item=self.item, quantity=1)
        self.item.enabled = False
        self.item.save()
        payload = {'items': [{'item': self.item.pk, 'quantity': '2', 'sequence': 10}]}
        self.assertEqual(self.client.patch(self.url('cost_package', self.package), payload, format='json').status_code, 400)
        payload['items'][0]['id'] = row.pk
        response = self.client.patch(self.url('cost_package', self.package), payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNotNone(response.data['data']['current_cost'])

    def test_atomic_invalid_batch_and_parent_id_injection(self):
        for rows in ([{'item': self.item.pk, 'quantity': '1', 'sequence': 10}, {'item': self.item.pk, 'quantity': '1', 'sequence': 20}],
                     [{'item': self.item.pk, 'quantity': '1', 'sequence': 10, 'id': 999}],
                     [{'item': self.item.pk, 'quantity': '1', 'sequence': 10, 'package': 999}]):
            response = self.client.patch(self.url('cost_package', self.package), {'name': 'Changed', 'items': rows}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
            self.package.refresh_from_db()
            self.assertEqual(self.package.name, 'Package')
            self.assertEqual(self.package.items.count(), 0)

    def test_protected_delete_returns_conflict(self):
        self.assertEqual(self.client.delete(self.url('service', self.service)).status_code, 409)

    def test_hidden_costs_do_not_leak_through_aggregate(self):
        CostPackageItem.objects.create(package=self.package, item=self.item, quantity=1)
        ProductCostPackage.objects.create(product=self.product, package=self.package, quantity=1)
        self.client.force_authenticate(self.actor)
        self.grant_all('product')
        response = self.client.get(self.url('product', self.product))
        self.assertIsNone(response.data['data']['standard_cost'])
        self.assertNotIn('unit_cost', response.data['data']['packages'][0])

    def test_nested_field_permission(self):
        SchemeItem.objects.create(scheme=self.scheme, product=self.product, sequence=10, remark='private')
        self.client.force_authenticate(self.actor)
        grant(self.actor, 'scheme:Retrieve', 'Scheme', fields=['items'])
        self.assertEqual(self.client.get(self.url('scheme', self.scheme)).data['data']['items'], [{'id': self.scheme.items.get().id}])

    def test_inherited_unapproved_actions_closed(self):
        for endpoint, method in [('import_data', 'post'), ('export_data', 'get'), ('multiple_delete', 'delete')]:
            response = getattr(self.client, method)(self.url('service') + endpoint + '/')
            self.assertIn(response.status_code, [403, 405])

    def test_scheme_derived_totals_and_dependency_field_authority(self):
        CostPackageItem.objects.create(package=self.package, item=self.item, quantity=3)
        ProductCostPackage.objects.create(product=self.product, package=self.package, quantity=2)
        self.product.reference_price = '120.00'
        self.product.save()
        for sequence in (10, 20):
            SchemeItem.objects.create(scheme=self.scheme, product=self.product, sequence=sequence)
        response = self.client.get(self.url('scheme', self.scheme)).data['data']
        from lims.catalog.services import product_cost
        self.assertEqual(response['standard_cost'], str(product_cost(self.product) * 2))
        self.assertEqual(response['reference_price'], '240.00')
        self.client.force_authenticate(self.actor)
        self.grant_all('scheme')
        response = self.client.get(self.url('scheme', self.scheme)).data['data']
        self.assertIsNone(response['standard_cost'])
        self.assertIsNone(response['reference_price'])

    def test_disabled_service_package_product_reference_boundaries(self):
        self.service.enabled = self.package.enabled = self.product.enabled = False
        self.service.save()
        self.package.save()
        self.product.save()
        self.assertEqual(self.client.post(self.url('product'), {
            'number': 'DISABLED', 'name': 'No', 'service': self.service.pk,
            'unit': 'test', 'reference_price': '1.00'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(self.url('product', self.product), {
            'packages': [{'package': self.package.pk, 'quantity': '1', 'sequence': 10}]}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(self.url('scheme', self.scheme), {
            'items': [{'product': self.product.pk, 'sequence': 10}]}, format='json').status_code, 400)
        row = SchemeItem.objects.create(scheme=self.scheme, product=self.product, sequence=10)
        self.assertEqual(self.client.patch(self.url('scheme', self.scheme), {'items': [
            {'id': row.pk, 'product': self.product.pk, 'sequence': 20}]}, format='json').status_code, 200)

    def test_menu_initializer_is_explicit_and_idempotent(self):
        from django.core.management import call_command
        from coreadmin.system.models import Menu, MenuButton, Role
        from io import StringIO
        call_command('init_lims', stdout=StringIO())
        counts = (Menu.objects.count(), MenuButton.objects.count(), MenuField.objects.count(), Role.objects.count())
        call_command('init_lims', stdout=StringIO())
        self.assertEqual(counts, (Menu.objects.count(), MenuButton.objects.count(), MenuField.objects.count(), Role.objects.count()))
