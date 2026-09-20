from decimal import Decimal
from types import SimpleNamespace
from django.test import TestCase
from apps.lims.tests import test_models
from apps.lims.models import CostPackageItem, ProductCostPackage
from apps.lims.costs import package_cost, product_cost
from apps.lims.services import master_command, save_aggregate


class CostTests(TestCase):
    def setUp(self):
        test_models.ModelTests.setUp(self)

    def test_exact_chain_no_intermediate_rounding(self):
        CostPackageItem.objects.create(package=self.package, item=self.item, quantity=3)
        ProductCostPackage.objects.create(product=self.product, package=self.package, quantity=2)
        self.assertEqual(package_cost(self.package), Decimal('1.250001'))
        self.assertEqual(product_cost(self.product), Decimal('2.50'))

    def test_half_up(self):
        self.item.unit_cost = Decimal('0.005')
        self.item.save()
        CostPackageItem.objects.create(package=self.package, item=self.item, quantity=1)
        ProductCostPackage.objects.create(product=self.product, package=self.package, quantity=1)
        self.assertEqual(product_cost(self.product), Decimal('0.01'))

    def test_empty_and_disabled_existing_cost(self):
        self.assertEqual(product_cost(self.product), Decimal('0.00'))
        self.item.enabled = False
        self.item.save()
        CostPackageItem.objects.create(package=self.package, item=self.item, quantity=1)
        self.assertEqual(package_cost(self.package), Decimal('0.416667'))

    def test_aggregate_rolls_back(self):
        row = CostPackageItem.objects.create(package=self.package, item=self.item, quantity=1)
        serializer = SimpleNamespace(instance=self.package, row_name='items',
            validated_data={'name': 'Changed', 'items': [{'item': self.item, 'quantity': Decimal(2), 'sequence': 10}]})
        with self.assertRaises(RuntimeError):
            with master_command():
                save_aggregate(serializer)
                raise RuntimeError('simulate failure')
        self.package.refresh_from_db()
        self.assertEqual(self.package.name, 'Package')
        self.assertEqual(self.package.items.get().pk, row.pk)
