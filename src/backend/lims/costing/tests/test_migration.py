"""Real PostgreSQL upgrade/empty-schema evidence in owned disposable databases."""
import copy
import uuid
import unittest
from contextlib import contextmanager
from decimal import Decimal
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from psycopg2 import sql


@contextmanager
def disposable():
    source = connections['default']
    assert source.vendor == 'postgresql'
    assert 'complims_test_' in source.settings_dict['NAME']
    name = 'complims_test_cost_upgrade_' + uuid.uuid4().hex[:8]
    alias = name
    with source._nodb_cursor() as cursor:
        cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    config = copy.deepcopy(source.settings_dict)
    config['NAME'] = name
    connections.databases[alias] = config
    connection = connections[alias]
    try:
        yield connection, alias
    finally:
        connection.close()
        del connections[alias]
        del connections.databases[alias]
        with source._nodb_cursor() as cursor:
            cursor.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))


class CostingMigrationTests(unittest.TestCase):
    def test_empty_database(self):
        with disposable() as (connection, alias):
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            executor.migrate(targets)
            apps = executor.loader.project_state(targets).apps
            self.assertEqual(apps.get_model('costing', 'CostType').objects.using(alias).count(), 7)
            kind = apps.get_model('costing', 'CostType').objects.using(alias).get(number='LABOR')
            item = apps.get_model('costing', 'CostItem').objects.using(alias).create(
                number='SMOKE', name='Smoke', cost_type_id=kind.pk, unit='u', unit_cost=Decimal('1.20'))
            self.assertEqual(apps.get_model('costing', 'CostItem').objects.using(alias).get(pk=item.pk).unit_cost, Decimal('1.20'))

    def test_baseline_upgrade_preserves_identity_relations_and_m2(self):
        with disposable() as (connection, alias):
            executor = MigrationExecutor(connection)
            final = executor.loader.graph.leaf_nodes()
            baseline = [('costing', '0001_initial') if app == 'costing' else (app, name) for app, name in final]
            executor.migrate(baseline)
            apps = executor.loader.project_state(baseline).apps
            def model(app, name): return apps.get_model(app, name)
            def create(app, model_name, **fields): return model(app, model_name).objects.using(alias).create(**fields)
            labels = {'LABOR':'人工', 'EQUIPMENT':'设备', 'CONSUMABLE':'耗材', 'CERTIFICATION':'认证',
                      'MAINTENANCE':'维护', 'REPAIR':'维修', 'OPERATION':'运营'}
            actor = create('system', 'Users', username='upgrade-actor')
            costs = ['1.234567','1.235000','0.005000','0.000000','999.999999','1.000000','2.500000']
            expected = ['1.23','1.24','0.01','0.00','1000.00','1.00','2.50']
            items = [create('costing','CostItem',number='OLD-'+kind,name=kind,type=kind,unit='hour',
                unit_cost=Decimal(cost), basis_data={'original':kind},enabled=False,description='preserve',
                creator_id=actor.pk,modifier=str(actor.pk),dept_belong_id='42') for kind,cost in zip(labels,costs)]
            package = create('costing','CostPackage',number='PK',name='Package',unit='u')
            for item in items: create('costing','CostPackageItem',package_id=package.pk,item_id=item.pk,quantity=Decimal('0.123456'))
            service = create('catalog','Service',number='S',name='Service')
            product = create('catalog','Product',number='P',name='Product',service_id=service.pk,unit='u',reference_price=Decimal('12.34'))
            create('catalog','ProductCostPackage',product_id=product.pk,package_id=package.pk,quantity=Decimal('0.123456'))
            scheme = create('catalog','Scheme',number='SC',name='Scheme')
            create('catalog','SchemeItem',scheme_id=scheme.pk,product_id=product.pk,sequence=10)
            customer = create('customer','Customer',number='CU',name='Customer')
            create('customer','CustomerContact',customer_id=customer.pk,name='Contact',is_default=True)
            for doc, date_field, group, parent, row, row_parent in (
                ('Quotation','quotation_date','QuotationScheme','quotation_id','QuotationSchemeItem','quotation_scheme_id'),
                ('Contract','contract_date','ContractScheme','contract_id','ContractSchemeItem','contract_scheme_id')):
                document = create('commercial',doc,number=doc,customer_id=customer.pk,customer_name_snapshot='Snapshot',
                    subtotal=Decimal('1.24'),adjustment_amount=Decimal('-0.01'),total_amount=Decimal('1.23'),**{date_field:'2026-09-21'})
                g = create('commercial',group,source_scheme_id=scheme.pk,sequence=10,name_snapshot='Snapshot',**{parent:document.pk})
                create('commercial',row,source_product_id=product.pk,sequence=10,name_snapshot='Product snapshot',
                    unit_snapshot='u',quantity=Decimal('1'),unit_price=Decimal('1.24'),line_amount=Decimal('1.24'),**{row_parent:g.pk})
            preserved = [('costing','CostPackage'),('costing','CostPackageItem'),('catalog','Service'),('catalog','Product'),
                ('catalog','ProductCostPackage'),('catalog','Scheme'),('catalog','SchemeItem'),('customer','Customer'),
                ('customer','CustomerContact'),('commercial','Quotation'),('commercial','QuotationScheme'),
                ('commercial','QuotationSchemeItem'),('commercial','Contract'),('commercial','ContractScheme'),('commercial','ContractSchemeItem')]
            snapshots = {(app,name):list(model(app,name).objects.using(alias).order_by('pk').values()) for app,name in preserved}
            old_items = list(model('costing','CostItem').objects.using(alias).order_by('pk').values())
            executor = MigrationExecutor(connection)
            executor.migrate(final)
            apps = executor.loader.project_state(final).apps
            self.assertEqual(dict(model('costing','CostType').objects.using(alias).values_list('number','name')), labels)
            for (app,name), before in snapshots.items():
                self.assertEqual(list(model(app,name).objects.using(alias).order_by('pk').values()), before, (app,name))
            new_items = list(model('costing','CostItem').objects.using(alias).order_by('pk').values())
            types = dict(model('costing','CostType').objects.using(alias).values_list('number','pk'))
            for old,new,rounded in zip(old_items,new_items,expected):
                self.assertEqual(new.pop('cost_type_id'), types[old.pop('type')])
                self.assertEqual(new.pop('unit_cost'), Decimal(rounded))
                old.pop('unit_cost')
                self.assertEqual(new,old)
            table = model('costing','CostItem')._meta.db_table
            with connection.cursor() as cursor:
                columns = connection.introspection.get_table_description(cursor,table)
                self.assertNotIn('type', {column.name for column in columns})
                self.assertNotIn('lims_item_type_valid', connection.introspection.get_constraints(cursor,table))
                cursor.execute('SELECT numeric_scale FROM information_schema.columns WHERE table_name=%s AND column_name=%s',(table,'unit_cost'))
                self.assertEqual(cursor.fetchone()[0], 2)
                self.assertFalse(next(column for column in columns if column.name=='cost_type_id').null_ok)
