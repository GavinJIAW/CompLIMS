from django.test import TestCase
from rest_framework.test import APIClient
from coreadmin.system.models import Users
from coreadmin.foundation_tests.access_fixtures import grant
from lims.shared.m2_contract import READ
from lims.customer.models import Customer


class CustomerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Users.objects.create(username='admin', is_superuser=True, pwd_change_count=1)
        self.client.force_authenticate(self.admin)

    def test_contacts_default_lifecycle_and_rollback(self):
        response = self.client.post('/api/lims/customer/', {'number': 'C1', 'name': '客户', 'contacts': [{'name': 'A', 'is_default': True}, {'name': 'B', 'is_default': True, 'enabled': False}]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data['data']; a, b = data['contacts']
        url = f"/api/lims/customer/{data['id']}/"
        response = self.client.patch(url, {'name': 'BAD', 'contacts': [{'id': a['id']}, {'id': b['id'], 'enabled': True}]}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Customer.objects.get(pk=data['id']).name, '客户')
        response = self.client.patch(url, {'contacts': [{'id': a['id'], 'is_default': False}, {'id': b['id'], 'enabled': True}]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([x['id'] for x in response.data['data']['contacts']], [a['id'], b['id']])
        self.assertEqual(self.client.patch(url, {'number': 'X'}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 200)

    def test_shared_all_nonall_denied(self):
        actor = Users.objects.create(username='normal', pwd_change_count=1)
        permission = grant(actor, 'customer:Search', 'Customer', fields=READ['customer'].split(), scope=0)
        self.client.force_authenticate(actor)
        self.assertEqual(self.client.get('/api/lims/customer/').status_code, 403)
        permission.data_range = 3; permission.save()
        self.assertEqual(self.client.get('/api/lims/customer/').status_code, 200)
