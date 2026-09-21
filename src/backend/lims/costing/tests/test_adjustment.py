"""CostType authority, lifecycle and canonical monetary boundaries."""
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from coreadmin.system.models import Users, FieldPermission
from coreadmin.foundation_tests.access_fixtures import grant
from lims.access_registry import READ, WRITE
from lims.costing.models import CostType, CostItem, CostPackage, CostPackageItem
from lims.catalog.models import Service, Product, ProductCostPackage, Scheme, SchemeItem
from lims.costing.services import package_cost
from lims.catalog.services import product_cost, scheme_totals


class AdjustmentTests(TestCase):
    def setUp(self):
        self.admin = Users.objects.create(username='adjust-admin', is_superuser=True, pwd_change_count=1)
        self.actor = Users.objects.create(username='adjust-user', pwd_change_count=1)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.kind = CostType.objects.create(number='CUSTOM', name='Custom type')
        self.other = CostType.objects.create(number='OTHER', name='Other type')
        self.item = CostItem.objects.create(number='I', name='Item', cost_type=self.kind, unit='hour', unit_cost=Decimal('1.23'))

    def url(self, resource, obj=None):
        return '/api/lims/' + resource + '/' + (str(obj.pk) + '/' if obj else '')

    def permit(self, resource, suffix, scope=3):
        return grant(self.actor, resource + ':' + suffix,
            {'cost_type': 'CostType', 'cost_item': 'CostItem'}[resource],
            fields=READ[resource].split(), create=WRITE[resource].split(),
            update=WRITE[resource].split(), scope=scope)

    def post_item(self, number='NEW', target=None, cost='1.20'):
        return self.client.post(self.url('cost_item'), dict(number=number, name=number,
            cost_type=(target or self.kind).pk, unit='hour', unit_cost=cost), format='json')

    def test_cost_type_crud_and_number_immutable(self):
        response = self.client.post(self.url('cost_type'), dict(number='NEW', name='新类型'), format='json')
        self.assertEqual(response.status_code, 200, response.data)
        obj = CostType.objects.get(number='NEW')
        self.assertTrue(obj.enabled)
        self.assertEqual(self.client.get(self.url('cost_type', obj)).status_code, 200)
        self.assertEqual(self.client.patch(self.url('cost_type', obj), {'name': 'Changed'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(self.url('cost_type', obj), {'number': 'CHANGE'}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(self.url('cost_type', obj)).status_code, 200)

    def test_referenced_delete_protected(self):
        self.assertEqual(self.client.delete(self.url('cost_type', self.kind)).status_code, 409)
        self.assertTrue(CostType.objects.filter(pk=self.kind.pk).exists())

    def test_disabled_lifecycle(self):
        CostType.objects.filter(pk__in=[self.kind.pk, self.other.pk]).update(enabled=False)
        self.assertEqual(self.post_item().status_code, 400)
        self.assertEqual(self.client.get(self.url('cost_item', self.item)).status_code, 200)
        self.assertEqual(self.client.patch(self.url('cost_item', self.item), {'name': 'Allowed'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(self.url('cost_item', self.item), {'cost_type': self.kind.pk}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(self.url('cost_item', self.item), {'cost_type': self.other.pk}, format='json').status_code, 400)
        CostType.objects.filter(pk=self.other.pk).update(enabled=True)
        self.assertEqual(self.client.patch(self.url('cost_item', self.item), {'cost_type': self.other.pk}, format='json').status_code, 200)

    def test_shared_all_and_unauthorized(self):
        self.client.force_authenticate(self.actor)
        self.assertEqual(self.client.get(self.url('cost_type')).status_code, 403)
        permission = self.permit('cost_type', 'Search', scope=0)
        for scope in (0, 1, 2, 4):
            permission.data_range = scope
            permission.save()
            self.assertEqual(self.client.get(self.url('cost_type')).status_code, 403)
        permission.data_range = 3
        permission.save()
        self.assertEqual(self.client.get(self.url('cost_type')).status_code, 200)

    def test_normal_user_crud(self):
        for suffix in ('Search', 'Retrieve', 'Create', 'Update', 'Delete'):
            self.permit('cost_type', suffix)
        self.client.force_authenticate(self.actor)
        self.test_cost_type_crud_and_number_immutable()

    def test_field_permission_read_write_and_query(self):
        self.client.force_authenticate(self.actor)
        permission = grant(self.actor, 'cost_type:Retrieve', 'CostType', fields=['number', 'name'])
        data = self.client.get(self.url('cost_type', self.kind)).data['data']
        self.assertNotIn('description', data)
        grant(self.actor, 'cost_type:Create', 'CostType', create=['number', 'name'])
        self.assertEqual(self.client.post(self.url('cost_type'), {'number':'X', 'name':'X', 'description':'forbidden'}, format='json').status_code, 400)
        grant(self.actor, 'cost_type:Update', 'CostType', update=['name'])
        self.assertEqual(self.client.patch(self.url('cost_type', self.kind), {'enabled':False}, format='json').status_code, 400)
        grant(self.actor, 'cost_type:Search', 'CostType', fields=['number'])
        self.assertEqual(self.client.get(self.url('cost_type'), {'name':'Custom type'}).status_code, 400)

    def test_relation_authority_create_update(self):
        self.permit('cost_item', 'Create')
        self.permit('cost_item', 'Update')
        self.client.force_authenticate(self.actor)
        self.assertEqual(self.post_item().status_code, 403)
        self.assertEqual(self.client.patch(self.url('cost_item', self.item), {'cost_type':self.other.pk}, format='json').status_code, 403)
        self.permit('cost_type', 'Retrieve')
        self.assertEqual(self.post_item().status_code, 200)
        self.assertEqual(self.client.patch(self.url('cost_item', self.item), {'cost_type':self.other.pk}, format='json').status_code, 200)

    def test_relation_write_field_permission(self):
        self.permit('cost_type', 'Retrieve')
        grant(self.actor, 'cost_item:Update', 'CostItem', update=['name'])
        self.client.force_authenticate(self.actor)
        self.assertEqual(self.client.patch(self.url('cost_item', self.item), {'cost_type':self.other.pk}, format='json').status_code, 400)

    def test_exact_filter_and_unreadable_filter(self):
        second = CostItem.objects.create(number='II', name='Second', cost_type=self.other, unit='u', unit_cost=1)
        self.other.enabled = False
        self.other.save()
        response = self.client.get(self.url('cost_item'), {'cost_type':self.other.pk})
        self.assertEqual([row['id'] for row in response.data['data']], [second.pk])
        self.client.force_authenticate(self.actor)
        self.permit('cost_item', 'Search')
        self.permit('cost_type', 'Retrieve')
        self.assertEqual(self.client.get(self.url('cost_item'), {'cost_type':self.kind.pk}).status_code, 200)
        FieldPermission.objects.filter(field__model='CostItem', field__field_name='cost_type').update(is_query=False)
        self.assertEqual(self.client.get(self.url('cost_item'), {'cost_type':self.kind.pk}).status_code, 400)
        self.assertEqual(self.client.get(self.url('cost_item'), {'cost_type__name':'Custom type'}).status_code, 400)

    def test_two_decimal_input_and_legacy_field_rejected(self):
        self.assertEqual(self.post_item(cost='1.235').status_code, 400)
        self.assertEqual(self.post_item(cost='1.2').data['data']['unit_cost'], '1.20')
        self.assertEqual(self.client.patch(self.url('cost_item', self.item), {'type':'LABOR'}, format='json').status_code, 400)

    def test_rounded_rows_sum_at_each_layer_and_api_strings(self):
        package = CostPackage.objects.create(number='PK', name='Package', unit='u')
        CostPackageItem.objects.create(package=package, item=self.item, quantity=Decimal('0.5'))
        self.assertEqual(package_cost(package), Decimal('0.62'))
        other_item = CostItem.objects.create(number='I2', name='Item2', cost_type=self.kind, unit='u', unit_cost=Decimal('1.23'))
        CostPackageItem.objects.create(package=package, item=other_item, quantity=Decimal('0.5'))
        self.assertEqual(package_cost(package), Decimal('1.24'))
        service = Service.objects.create(number='S', name='Service')
        product = Product.objects.create(number='P', name='Product', service=service, unit='u', reference_price=Decimal('1.20'))
        ProductCostPackage.objects.create(product=product, package=package, quantity=Decimal('0.5'))
        self.assertEqual(product_cost(product), Decimal('0.62'))
        scheme = Scheme.objects.create(number='SC', name='Scheme')
        for sequence in (10,20):
            SchemeItem.objects.create(scheme=scheme, product=product, sequence=sequence)
        self.assertEqual(scheme_totals(scheme), (Decimal('1.24'),Decimal('2.40')))
        data=self.client.get(self.url('cost_package', package)).data['data']
        self.assertEqual(data['current_cost'], '1.24')
        self.assertEqual([row['line_cost'] for row in data['items']], ['0.62','0.62'])
        data=self.client.get(self.url('product', product)).data['data']
        self.assertEqual(data['standard_cost'], '0.62')
        self.assertEqual(data['packages'][0]['line_cost'], '0.62')
        data=self.client.get(self.url('scheme', scheme)).data['data']
        self.assertEqual((data['standard_cost'],data['reference_price']), ('1.24','2.40'))

    def test_product_sums_rounded_package_lines_not_raw_products(self):
        service = Service.objects.create(number='S', name='Service')
        product = Product.objects.create(number='P', name='Product', service=service, unit='u', reference_price=0)
        self.item.unit_cost = Decimal('0.01')
        self.item.save()
        for number in ('A', 'B'):
            package = CostPackage.objects.create(number=number, name=number, unit='u')
            CostPackageItem.objects.create(package=package, item=self.item, quantity=Decimal('1'))
            ProductCostPackage.objects.create(product=product, package=package, quantity=Decimal('0.5'))
        self.assertEqual(product_cost(product), Decimal('0.02'))
        data = self.client.get(self.url('product', product)).data['data']
        self.assertEqual([row['line_cost'] for row in data['packages']], ['0.01', '0.01'])
        self.assertEqual(data['standard_cost'], '0.02')
