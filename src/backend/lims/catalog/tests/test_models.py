from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from lims.costing.models import CostType, CostItem, CostPackage, CostPackageItem
from lims.catalog.models import Service, Product, ProductCostPackage, Scheme, SchemeItem



class ModelTests(TestCase):
    def setUp(self):
        self.cost_type, _ = CostType.objects.get_or_create(number='LABOR', defaults={'name': '人工'})
        self.service = Service.objects.create(number='S', name='Service')
        self.item = CostItem.objects.create(number='I', name='Item', cost_type=self.cost_type, unit='hour', unit_cost='0.42')
        self.package = CostPackage.objects.create(number='C', name='Package', unit='hour')
        self.product = Product.objects.create(number='P', name='Product', service=self.service, unit='test', reference_price='1.00')
        self.scheme = Scheme.objects.create(number='SC', name='Scheme')

    def rejected(self, callback):
        with self.assertRaises(IntegrityError), transaction.atomic():
            callback()
            connection.check_constraints()

    def test_master_numbers_unique_and_immutable(self):
        for obj in (self.service, self.item, self.package, self.product, self.scheme):
            with self.subTest(model=type(obj).__name__):
                data = {field.name: getattr(obj, field.name) for field in obj._meta.fields if not field.primary_key}
                self.rejected(lambda: type(obj).objects.create(**data))
                obj.number += '-changed'
                with self.assertRaises(ValidationError):
                    obj.save()

    def test_package_constraints(self):
        CostPackageItem.objects.create(package=self.package, item=self.item, quantity=1)
        self.rejected(lambda: CostPackageItem.objects.create(package=self.package, item=self.item, quantity=1))
        self.rejected(lambda: CostPackageItem.objects.create(package=self.package, item_id=99999, quantity=1))
        self.rejected(lambda: CostPackageItem.objects.create(package=self.package, quantity=1))
        self.rejected(lambda: CostPackageItem.objects.filter(package=self.package).update(quantity=0))

    def test_product_constraints(self):
        ProductCostPackage.objects.create(product=self.product, package=self.package, quantity=1)
        self.rejected(lambda: ProductCostPackage.objects.create(product=self.product, package=self.package, quantity=1))
        self.rejected(lambda: ProductCostPackage.objects.filter(product=self.product).update(quantity=-1))
        self.rejected(lambda: ProductCostPackage.objects.filter(product=self.product).update(package_id=99999))

    def test_scheme_allows_repeated_product_but_not_sequence(self):
        for sequence in (10, 20):
            SchemeItem.objects.create(scheme=self.scheme, product=self.product, sequence=sequence)
        self.assertEqual(self.scheme.items.count(), 2)
        self.rejected(lambda: SchemeItem.objects.create(scheme=self.scheme, product=self.product, sequence=10))

    def test_protect_and_cascade(self):
        CostPackageItem.objects.create(package=self.package, item=self.item, quantity=1)
        ProductCostPackage.objects.create(product=self.product, package=self.package, quantity=1)
        SchemeItem.objects.create(scheme=self.scheme, product=self.product, sequence=10)
        for obj in (self.service, self.item, self.package, self.product):
            with self.assertRaises(ProtectedError):
                obj.delete()
        self.scheme.delete()
        self.assertFalse(SchemeItem.objects.exists())
        self.product.delete()
        self.assertFalse(ProductCostPackage.objects.exists())
        self.package.delete()
        self.assertFalse(CostPackageItem.objects.exists())
        self.item.delete()
        self.service.delete()

    def test_cost_and_price_constraints(self):
        self.rejected(lambda: CostItem.objects.filter(pk=self.item.pk).update(unit_cost=-1))
        self.rejected(lambda: CostItem.objects.filter(pk=self.item.pk).update(cost_type_id=999999))
        self.rejected(lambda: Product.objects.filter(pk=self.product.pk).update(reference_price=-1))
        self.item.refresh_from_db()
        self.assertEqual(self.item.unit_cost, Decimal('0.42'))

    def test_business_foreign_keys_are_required_and_constrained(self):
        for model, names in ((CostItem, ['cost_type']), (Product, ['service']), (CostPackageItem, ['package', 'item']),
                             (ProductCostPackage, ['product', 'package']), (SchemeItem, ['scheme', 'product'])):
            for name in names:
                field = model._meta.get_field(name)
                self.assertFalse(field.null)
                self.assertTrue(field.db_constraint)

    def test_mutable_json_defaults_are_independent(self):
        first, second = Service(), Service()
        first.requirement_template.append({'key': 'a'})
        self.assertEqual(second.requirement_template, [])
