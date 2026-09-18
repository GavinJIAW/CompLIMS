from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from coreadmin.foundation_tests.access_fixtures import grant
from coreadmin.system.models import Dept, Users


class DeptEmptyStateTests(TestCase):
    url = '/api/system/dept/dept_info/'
    empty = {'dept_name': None, 'dept_user': 0, 'owner': None, 'description': None,
             'gender': {'male': 0, 'female': 0, 'unknown': 0}, 'sub_dept_map': []}

    def setUp(self):
        self.actor = Users.objects.create(username='dept-uat', pwd_change_count=1)
        self.dept = Dept.objects.create(name='REAL_DEPARTMENT', owner='REAL_OWNER')
        self.other = Dept.objects.create(name='OTHER_DEPARTMENT')
        Users.objects.create(username='real-user', dept=self.dept, gender=1, pwd_change_count=1)
        grant(self.actor, 'dept:HeaderInfo', 'Dept', fields=['name'], scope=4, departments=[self.dept])
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def test_exact_url_empty_without_business_queries_or_object_policy(self):
        with patch('coreadmin.access.context.AccessContext.scope', side_effect=AssertionError('No scope for empty state')), patch(
                'coreadmin.access.fields.FieldPolicy.allowed', side_effect=AssertionError('No object fields')), CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url + '?dept_id=&show_all=0')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data'], self.empty)
        for query in queries:
            # Active Action grants load their configured department relations.
            # Keep that authorization check; forbid business target/subtree and
            # user-statistics queries after it.
            if 'INNER JOIN "role_menu_button_permission_dept"' in query['sql']:
                continue
            for model in (Dept, Users):
                self.assertNotIn('"' + model._meta.db_table + '"', query['sql'])

    def test_empty_blank_show_all_matches_zero(self):
        response = self.client.get(self.url, {'dept_id': '', 'show_all': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data'], self.empty)

    def test_empty_recursive_rejected(self):
        self.assertEqual(self.client.get(self.url, {'dept_id': '', 'show_all': '1'}).status_code, 400)

    def test_missing_parameter_rejected(self):
        self.assertEqual(self.client.get(self.url, {'show_all': '0'}).status_code, 400)

    def test_malformed_parameter_rejected(self):
        self.assertEqual(self.client.get(self.url, {'dept_id': 'abc', 'show_all': '0'}).status_code, 400)

    def test_invalid_show_all_rejected_for_empty_and_concrete(self):
        for dept in ('', str(self.dept.pk)):
            for value in ('2', 'true', '-1'):
                self.assertEqual(self.client.get(self.url, {'dept_id': dept, 'show_all': value}).status_code, 400)

    def test_authorized_concrete_preserves_field_policy(self):
        response = self.client.get(self.url, {'dept_id': self.dept.pk, 'show_all': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data'], {'dept_name': self.dept.name})

    def test_out_of_scope_and_missing_concrete_are_404(self):
        for value in (self.other.pk, 99999999):
            self.assertEqual(self.client.get(self.url, {'dept_id': value, 'show_all': '0'}).status_code, 404)

    def test_empty_selection_does_not_bypass_action(self):
        inactive = Users.objects.create(username='inactive-dept', is_active=False, is_superuser=True, pwd_change_count=1)
        no_action = Users.objects.create(username='no-dept-action', pwd_change_count=1)
        for actor in (None, inactive, no_action):
            self.client.force_authenticate(actor)
            self.assertIn(self.client.get(self.url + '?dept_id=&show_all=0').status_code, (401, 403))

    def test_superuser_empty_selection_positive(self):
        admin = Users.objects.create(username='dept-admin', is_superuser=True, pwd_change_count=1)
        self.client.force_authenticate(admin)
        response = self.client.get(self.url + '?dept_id=&show_all=0')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data'], self.empty)
