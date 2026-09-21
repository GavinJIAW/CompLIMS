import unittest
from decimal import Decimal
from django.db.migrations.executor import MigrationExecutor
from lims.costing.tests.test_migration import disposable


class ContactMigrationTests(unittest.TestCase):
    def test_empty_database_contact_orm(self):
        with disposable() as (connection,alias):
            ex=MigrationExecutor(connection);targets=ex.loader.graph.leaf_nodes();ex.migrate(targets)
            apps=ex.loader.project_state(targets).apps
            customer=apps.get_model('customer','Customer').objects.using(alias).create(number='C',name='Customer')
            contact=apps.get_model('customer','CustomerContact').objects.using(alias).create(customer=customer,name='Contact',gender=2,mobile='123')
            self.assertEqual(contact.gender,2)
            self.assertIsNone(contact.direct_supervisor_id)

    def test_exact_main_upgrade_cleans_only_contacts_and_renames_snapshot(self):
        with disposable() as (connection,alias):
            ex=MigrationExecutor(connection);final=ex.loader.graph.leaf_nodes()
            baseline=[(app,'0001_initial') if app in ('customer','commercial') else (app,name) for app,name in final]
            ex.migrate(baseline);apps=ex.loader.project_state(baseline).apps
            def model(app,name):return apps.get_model(app,name)
            def create(app,model_name,**data):return model(app,model_name).objects.using(alias).create(**data)
            customer=create('customer','Customer',number='C',name='Customer')
            create('customer','CustomerContact',customer=customer,name='Old contact',department='Old',phone='123',remark='Legacy')
            kind=model('costing','CostType').objects.using(alias).get(number='LABOR')
            create('costing','CostItem',number='I',name='Cost',cost_type=kind,unit_cost=Decimal('1.23'),unit='hour')
            create('catalog','Service',number='S',name='Service')
            for name,date in [('Quotation','quotation_date'),('Contract','contract_date')]:
                create('commercial',name,number=name,customer=customer,contact_name_snapshot='Historical',contact_phone_snapshot='555',contact_email_snapshot='a@example.com',subtotal=Decimal('123.45'),adjustment_amount=Decimal('-1.00'),total_amount=Decimal('122.45'),**{date:'2026-09-21'})
            preserved=[('customer','Customer'),('costing','CostItem'),('catalog','Service'),('commercial','Quotation'),('commercial','Contract')]
            before={(app,name):list(model(app,name).objects.using(alias).values()) for app,name in preserved}
            ex=MigrationExecutor(connection);ex.migrate(final);apps=ex.loader.project_state(final).apps
            self.assertEqual(model('customer','CustomerContact').objects.using(alias).count(),0)
            for (app,name),rows in before.items():
                if app=='commercial':
                    for row in rows:row['contact_mobile_snapshot']=row.pop('contact_phone_snapshot')
                self.assertEqual(list(model(app,name).objects.using(alias).values()),rows)
            with connection.cursor() as c:
                for app,name,absent in [('customer','CustomerContact',{'phone','department','remark'}),('commercial','Quotation',{'contact_phone_snapshot'}),('commercial','Contract',{'contact_phone_snapshot'})]:
                    columns={f.name for f in connection.introspection.get_table_description(c,model(app,name)._meta.db_table)}
                    self.assertFalse(columns & absent)
