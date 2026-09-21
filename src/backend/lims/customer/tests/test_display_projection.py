"""Contact display projections must not grant target read or write authority."""
from io import StringIO
from pathlib import Path
from django.core.management import call_command
from django.test import TestCase, SimpleTestCase
from rest_framework.test import APIClient
from coreadmin.foundation_tests.access_fixtures import grant
from coreadmin.system.models import Users, FieldPermission, MenuField
from lims.customer.access_contract import READ, WRITE
from lims.customer.models import Customer, CustomerContact
from lims.customer.views import ContactViewSet


class ContactProjectionTests(TestCase):
    def setUp(self):
        self.admin = Users.objects.create(username='admin', is_superuser=True, pwd_change_count=1)
        self.actor = Users.objects.create(username='actor', pwd_change_count=1)
        self.customer = Customer.objects.create(number='C', name='Customer name')
        self.supervisor = CustomerContact.objects.create(customer=self.customer, name='Supervisor name')
        self.contact = CustomerContact.objects.create(customer=self.customer, name='Contact', direct_supervisor=self.supervisor)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def permit(self, resource, action, scope=3):
        model = {'customer': 'Customer', 'contact': 'CustomerContact'}[resource]
        return grant(self.actor, resource + ':' + action, model, fields=READ[resource].split(),
                     create=WRITE[resource].split(), update=WRITE[resource].split(), scope=scope)

    def normal(self, retrieve=True):
        self.permit('contact', 'Search')
        if retrieve:
            self.permit('contact', 'Retrieve')
        self.permit('customer', 'Retrieve')
        self.client.force_authenticate(self.actor)

    def rows(self):
        detail = self.client.get(f'/api/lims/contact/{self.contact.pk}/')
        listing = self.client.get('/api/lims/contact/')
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(listing.status_code, 200, listing.data)
        return [detail.data['data'], next(row for row in listing.data['data'] if row['id'] == self.contact.pk)]

    def test_list_and_retrieve_names(self):
        self.normal()
        for row in self.rows():
            self.assertEqual(row['customer_name'], self.customer.name)
            self.assertEqual(row['direct_supervisor_name'], self.supervisor.name)
            self.assertEqual(row['customer'], self.customer.pk)
            self.assertEqual(row['direct_supervisor'], self.supervisor.pk)
        self.assertIsNone(self.client.get(f'/api/lims/contact/{self.supervisor.pk}/').data['data']['direct_supervisor_name'])

    def test_customer_target_field_denied(self):
        self.normal()
        FieldPermission.objects.filter(field__model='Customer', field__field_name='name').update(is_query=False)
        for row in self.rows():
            self.assertIsNone(row['customer_name'])
            self.assertEqual(row['direct_supervisor_name'], self.supervisor.name)

    def test_supervisor_target_field_denied(self):
        self.normal()
        FieldPermission.objects.filter(field__model='CustomerContact', field__field_name='name').update(is_query=False)
        for row in self.rows():
            self.assertIsNone(row['direct_supervisor_name'])
            self.assertEqual(row['customer_name'], self.customer.name)

    def test_own_projection_fields_denied(self):
        self.normal()
        FieldPermission.objects.filter(field__model='CustomerContact', field__field_name__in=['customer_name', 'direct_supervisor_name']).update(is_query=False)
        for row in self.rows():
            self.assertNotIn('customer_name', row)
            self.assertNotIn('direct_supervisor_name', row)

    def test_customer_retrieve_authority_denied(self):
        self.permit('contact', 'Search')
        self.permit('contact', 'Retrieve')
        self.client.force_authenticate(self.actor)
        for row in self.rows():
            self.assertIsNone(row['customer_name'])

    def test_supervisor_retrieve_authority_denied_on_list(self):
        self.normal(retrieve=False)
        response = self.client.get('/api/lims/contact/')
        self.assertEqual(response.status_code, 200)
        for row in response.data['data']:
            self.assertIsNone(row['direct_supervisor_name'])

    def test_nonall_target_scope_denied(self):
        self.permit('contact', 'Search')
        self.permit('contact', 'Retrieve')
        self.permit('customer', 'Retrieve', scope=0)
        self.client.force_authenticate(self.actor)
        for row in self.rows():
            self.assertIsNone(row['customer_name'])

    def test_projection_writes_rejected_even_for_admin(self):
        for field in ('customer_name', 'direct_supervisor_name'):
            response = self.client.post('/api/lims/contact/', {'name': 'New', 'customer': self.customer.pk, field: 'Forged'}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
            response = self.client.patch(f'/api/lims/contact/{self.contact.pk}/', {field: 'Forged'}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(CustomerContact.objects.count(), 2)

    def test_metadata_and_configured_write_grants_cannot_expand_ceiling(self):
        call_command('init_lims', stdout=StringIO())
        self.normal()
        self.permit('contact', 'Create')
        self.permit('contact', 'Update')
        FieldPermission.objects.filter(field__model='CustomerContact', field__field_name__in=['customer_name', 'direct_supervisor_name']).update(is_create=True, is_update=True)
        metadata = self.client.get('/api/lims/contact/field_permission/').data['data']
        for field in ('customer_name', 'direct_supervisor_name'):
            self.assertEqual(metadata[field], {'is_query': True, 'is_create': False, 'is_update': False})
            self.assertEqual(self.client.post('/api/lims/contact/', {'name': 'New', 'customer': self.customer.pk, field: 'Forged'}, format='json').status_code, 400)
            self.assertEqual(self.client.patch(f'/api/lims/contact/{self.contact.pk}/', {field: 'Forged'}, format='json').status_code, 400)
        for field in ('customer_name', 'direct_supervisor_name'):
            self.assertTrue(MenuField.objects.filter(menu__component_name='lims_contact', model='CustomerContact', field_name=field).exists())
            self.assertNotIn(field, ContactViewSet.filter_fields)
            self.assertNotIn(field, ContactViewSet.ordering_fields)
        self.assertEqual(self.client.get('/api/lims/contact/', {'customer__name': 'Customer name'}).status_code, 400)

    def test_disabled_existing_supervisor_is_readable_and_retained(self):
        self.supervisor.enabled = False
        self.supervisor.save()
        for row in self.rows():
            self.assertEqual(row['direct_supervisor_name'], self.supervisor.name)
        response = self.client.get('/api/lims/contact/', {'enabled': True, 'customer': self.customer.pk})
        self.assertNotIn(self.supervisor.pk, [row['id'] for row in response.data['data']])
        self.assertEqual(self.client.get(f'/api/lims/contact/{self.supervisor.pk}/').status_code, 200)
        self.assertEqual(self.client.patch(f'/api/lims/contact/{self.contact.pk}/', {'title': 'Updated', 'direct_supervisor': self.supervisor.pk}, format='json').status_code, 200)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.direct_supervisor_id, self.supervisor.pk)
        self.assertEqual(self.client.post('/api/lims/contact/', {'name': 'New', 'customer': self.customer.pk, 'direct_supervisor': self.supervisor.pk}, format='json').status_code, 400)


class ContactProjectionFrontendTests(SimpleTestCase):
    root = Path(__file__).resolve().parents[5] / 'src/web/src/views/lims'

    def test_contact_labels_names_and_pk_bindings(self):
        text = (self.root / 'customer/contact/crud.tsx').read_text(encoding='utf-8')
        self.assertIn("title: '姓名'", text)
        self.assertIn("title: '启用状态'", text)
        self.assertIn("title: '是否默认联系人'", text)
        self.assertIn("message: '请填写姓名'", text)
        for relation in ('customer', 'direct_supervisor'):
            self.assertIn(f"formatter: ({{ row }}: any) => row.{relation}_name ?? '—'", text)
            self.assertIn(f'permissions.{relation}_name?.is_query', text)
            self.assertIn(f'modelValue: scope.form.{relation}', text)
        customer = text.split('        customer: {', 1)[1].split('        direct_supervisor: {', 1)[0]
        self.assertIn('search: {', customer)
        self.assertIn('scope.form.customer = value', customer)
        api = (self.root / 'customer/contact/api.ts').read_text(encoding='utf-8')
        self.assertNotIn('customer_name', api)
        self.assertNotIn('direct_supervisor_name', api)

    def test_supervisor_enabled_options_and_existing_selected_retention(self):
        text = (self.root / 'customer/contact/crud.tsx').read_text(encoding='utf-8')
        supervisor = text.split('        direct_supervisor: {', 1)[1].split('        title: {', 1)[0]
        self.assertNotIn('includeDisabled: true', supervisor)
        self.assertIn('loadOne: contactApi.retrieve', supervisor)
        self.assertIn('params: { customer: scope.form.customer }', supervisor)
        selector = (self.root / 'shared/MasterSelect.vue').read_text(encoding='utf-8')
        self.assertIn('props.includeDisabled ? {} : { enabled: true }', selector)
        self.assertIn('await props.loadOne(props.modelValue)', selector)
        self.assertIn('options.value.unshift(res.data)', selector)
        self.assertIn('options.value.unshift(selected)', selector)
        self.assertIn('row.enabled === false && row.id !== modelValue', selector)
