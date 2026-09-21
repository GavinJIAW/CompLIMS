from django.test import TestCase
from rest_framework.test import APIClient
from coreadmin.system.models import Users
from coreadmin.foundation_tests.access_fixtures import grant
from lims.access_registry import READ
from lims.customer.models import Customer


class CustomerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Users.objects.create(username='admin', is_superuser=True, pwd_change_count=1)
        self.client.force_authenticate(self.admin)

    def test_contacts_default_lifecycle_and_rollback(self):
        # The accepted standalone adjustment deliberately rejects the old aggregate DTO.
        response = self.client.post('/api/lims/customer/', {'number':'C1','name':'客户','contacts':[{'name':'A'}]}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Customer.objects.exists())
        response = self.client.post('/api/lims/customer/', {'number':'C1','name':'客户'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        data=response.data['data']; self.assertNotIn('contacts', data)
        url=f"/api/lims/customer/{data['id']}/"
        self.assertEqual(self.client.patch(url, {'contacts':[],'name':'BAD'}, format='json').status_code, 400)
        self.assertEqual(Customer.objects.get(pk=data['id']).name, '客户')
        self.assertEqual(self.client.patch(url, {'number':'X'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'name':'Updated'}, format='json').status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 200)

    def test_shared_all_nonall_denied(self):
        actor = Users.objects.create(username='normal', pwd_change_count=1)
        permission = grant(actor, 'customer:Search', 'Customer', fields=READ['customer'].split(), scope=0)
        self.client.force_authenticate(actor)
        self.assertEqual(self.client.get('/api/lims/customer/').status_code, 403)
        permission.data_range = 3; permission.save()
        self.assertEqual(self.client.get('/api/lims/customer/').status_code, 200)
