"""Domain boundaries and metadata consumed by the existing Foundation."""
from importlib import import_module
from io import StringIO
from django.apps import apps
from django.core.management import call_command
from django.db import models
from django.test import SimpleTestCase, TestCase
from coreadmin.system.models import (
    Menu, MenuButton, MenuField, Users, Role, RoleMenuPermission,
    RoleMenuButtonPermission, FieldPermission,
)
from lims.costing.models import CostItem, CostPackage, CostPackageItem
from lims.catalog.models import Service, Product, ProductCostPackage, Scheme, SchemeItem


class DomainStructureTests(SimpleTestCase):
    def test_app_ownership_and_namespace(self):
        self.assertFalse(apps.is_installed('apps.lims'))
        self.assertNotIn('lims', apps.app_configs)
        for label, module, expected in (
            ('costing', 'lims.costing', {CostItem, CostPackage, CostPackageItem}),
            ('catalog', 'lims.catalog', {Service, Product, ProductCostPackage, Scheme, SchemeItem}),
        ):
            config = apps.get_app_config(label)
            self.assertEqual(config.name, module)
            self.assertEqual(set(config.get_models()), expected)

    def test_business_metadata(self):
        audit = {'id', 'creator', 'modifier', 'dept_belong_id', 'create_datetime', 'update_datetime', 'description'}
        for model in (CostItem, CostPackage, CostPackageItem, Service, Product, ProductCostPackage, Scheme, SchemeItem):
            self.assertRegex(model._meta.verbose_name, '[\u4e00-\u9fff]')
            self.assertEqual(model._meta.verbose_name_plural, model._meta.verbose_name)
            for field in model._meta.fields:
                if field.name in audit - {'description'}:
                    continue
                self.assertRegex(field.verbose_name, '[\u4e00-\u9fff]')
                self.assertRegex(field.help_text, '[\u4e00-\u9fff]')
                self.assertNotEqual(field.help_text, field.verbose_name)

    def test_cross_app_fk_and_migration_dependency(self):
        field = ProductCostPackage._meta.get_field('package')
        self.assertIs(field.related_model, CostPackage)
        self.assertTrue(field.db_constraint)
        self.assertIs(field.remote_field.on_delete, models.PROTECT)
        self.assertIs(Product._meta.get_field('service').related_model, Service)
        migration = import_module('lims.catalog.migrations.0001_initial').Migration
        self.assertIn(('costing', '0001_initial'), migration.dependencies)


class MenuStructureTests(TestCase):
    def test_hierarchy_model_mapping_and_no_implicit_grants(self):
        protected = (Users, Role, RoleMenuPermission, RoleMenuButtonPermission, FieldPermission)
        before = [model.objects.count() for model in protected]
        call_command('init_lims', stdout=StringIO())
        counts = [model.objects.count() for model in (Menu, MenuButton, MenuField)]
        call_command('init_lims', stdout=StringIO())
        self.assertEqual(counts, [model.objects.count() for model in (Menu, MenuButton, MenuField)])
        self.assertEqual(before, [model.objects.count() for model in protected])
        self.assertFalse(Menu.objects.filter(component_name='lims_master').exists())
        for group, title, pages in (
            ('costing', '成本管理', [('cost_item', 'costItem', CostItem), ('cost_package', 'costPackage', CostPackage)]),
            ('catalog', '服务目录', [('service', 'service', Service), ('product', 'product', Product), ('scheme', 'scheme', Scheme)]),
        ):
            parent = Menu.objects.get(component_name=f'lims_{group}')
            self.assertEqual(parent.name, title)
            self.assertIsNone(parent.parent_id)
            for resource, page, model in pages:
                menu = Menu.objects.get(component_name=f'lims_{resource}')
                self.assertEqual(menu.parent_id, parent.pk)
                self.assertEqual(menu.component, f'lims/{group}/{page}/index')
                self.assertTrue(MenuField.objects.filter(menu=menu, model=model.__name__, field_name='number').exists())
