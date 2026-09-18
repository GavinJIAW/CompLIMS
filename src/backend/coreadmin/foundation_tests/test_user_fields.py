"""User input ceilings are enforced through the real POST/PUT/PATCH routes."""
from django.test import TestCase, SimpleTestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import (ValidationError, PermissionDenied, NotFound, NotAuthenticated, AuthenticationFailed)
from coreadmin.utils.exception import CustomExceptionHandler
from coreadmin.system.models import Users, Role, Dept, Post
from coreadmin.system.views.user import UserViewSet, UserUpdateSerializer
from .test_grant_management import database_snapshot


class UserFieldsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Users.objects.create(username='admin', name='Admin', password='!', is_superuser=True, pwd_change_count=1)
        cls.dept = Dept.objects.create(name='Department', key='department')
        cls.role = Role.objects.create(name='Role', key='role')
        cls.post = Post.objects.create(name='Post', code='post')
        cls.target = Users.objects.create(username='target', name='Target', password='!stored-test-marker', dept=cls.dept, dept_belong_id=str(cls.dept.pk), login_error_count=4, pwd_change_count=1)
        cls.target.role.add(cls.role)
        cls.target.post.add(cls.post)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_patch_selects_hardened_serializer(self):
        view = UserViewSet()
        view.action = 'partial_update'
        self.assertIs(view.get_serializer_class(), UserUpdateSerializer)

    def test_safe_create_and_all_responses_hide_password(self):
        response = self.client.post('/api/system/user/', {'username': 'safe', 'name': 'Safe', 'password': 'test-only-password'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 2000)
        user = Users.objects.get(username='safe')
        self.assertTrue(bool(user.password))
        self.assertIsNone(user.dept_id)
        self.assertFalse(user.role.exists())
        self.assertFalse(user.post.exists())
        responses = [response, self.client.get('/api/system/user/'), self.client.get(f'/api/system/user/{user.pk}/')]
        for method in ('put', 'patch'):
            responses.append(getattr(self.client, method)(f'/api/system/user/{user.pk}/', {'username': 'safe', 'name': 'Updated'}, format='json'))
        for result in responses:
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.data['code'], 2000)
            self.assertTrue('"password"' not in result.content.decode(), "Password field leaked")
            self.assertTrue(user.password not in result.content.decode(), "Password hash leaked")
            self.assertTrue('test-only-password' not in result.content.decode(), 'Password value leaked')

    def test_safe_update_preserves_memberships_and_server_resets_counter(self):
        for method in ('put', 'patch'):
            response = getattr(self.client, method)(f'/api/system/user/{self.target.pk}/', {'username': 'target', 'name': 'Updated', 'is_active': True}, format='json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['code'], 2000)
            self.target.refresh_from_db()
            self.assertEqual(self.target.name, 'Updated')
            self.assertEqual(self.target.login_error_count, 0)
            self.assertEqual(list(self.target.role.values_list('pk', flat=True)), [self.role.pk])
            self.assertEqual(list(self.target.post.values_list('pk', flat=True)), [self.post.pk])
            self.assertEqual(self.target.dept_id, self.dept.pk)
            self.assertEqual(str(self.target.dept_belong_id), str(self.dept.pk))

    def test_bulk_mixed_create_rejected_before_any_save(self):
        before = database_snapshot()
        response = self.client.post('/api/system/user/', [{'username': 'safe-bulk', 'name': 'Safe'}, {'username': 'unsafe-bulk', 'name': 'Unsafe', 'is_superuser': True}], format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(before == database_snapshot(), 'Mixed bulk input partially saved')

    def test_import_aliases_disabled_for_all_actors(self):
        for actor in (None, self.admin, self.target):
            self.client.force_authenticate(actor)
            for path in ('/api/system/user/import/', '/api/system/user/import_data/'):
                for method in ('get', 'post'):
                    with self.subTest(actor=actor and actor.username, path=path, method=method):
                        before = database_snapshot()
                        response = getattr(self.client, method)(path, {}, format='json')
                        self.assertEqual(response.status_code, 405)
                        self.assertTrue(before == database_snapshot())

    def test_safe_bulk_create(self):
        response = self.client.post('/api/system/user/', [
            {'username': 'bulk-one', 'name': 'One', 'password': 'Valid-test-password-2026!'},
            {'username': 'bulk-two', 'name': 'Two', 'password': 'Valid-test-password-2026!'},
        ], format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 2000)
        self.assertEqual(Users.objects.filter(username__in=['bulk-one', 'bulk-two']).count(), 2)

    def test_dynamic_query_cannot_expand_input_ceiling(self):
        before = database_snapshot()
        response = self.client.patch(f'/api/system/user/{self.target.pk}/?query={{username,name}}',
                                     {'name': 'Attempt', 'is_superuser': True}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(before == database_snapshot())

    def test_normal_authorized_user_has_same_write_ceiling(self):
        from coreadmin.system.models import ApiWhiteList
        from coreadmin.foundation_tests.access_fixtures import grant
        grant(self.target, 'user:Create', 'Users', create=['username', 'name'])
        grant(self.target, 'user:Update', 'Users', update=['username', 'name'])
        self.client.force_authenticate(self.target)
        for method in (1, 2, 5):
            ApiWhiteList.objects.create(url='/api/system/user/.*', method=method, enable_datasource=False)
        for method in ('post', 'put', 'patch'):
            with self.subTest(method=method):
                before = database_snapshot()
                path = '/api/system/user/' if method == 'post' else f'/api/system/user/{self.target.pk}/'
                response = getattr(self.client, method)(path, {'username': 'new' if method == 'post' else 'target',
                    'name': 'Attempt', 'role': []}, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertTrue(before == database_snapshot())



FORBIDDEN = {'id': 99999, 'is_superuser': True, 'is_staff': True, 'groups': [],
    'user_permissions': [], 'role': [], 'post': [], 'dept': None, 'creator': None,
    'modifier': '99999', 'dept_belong_id': '99999', 'pwd_change_count': 9,
    'login_error_count': 0, 'last_login': None, 'date_joined': '2020-01-01T00:00:00',
    'unknown_field': 'ignored-before', 'creator_name': 'spoof', 'create_datetime': None}


def forbidden_test(method, field, value):
    def test(self):
        payload = {'username': 'new' if method == 'post' else 'target', 'name': 'Attempted change', field: value}
        path = '/api/system/user/' if method == 'post' else f'/api/system/user/{self.target.pk}/'
        before = database_snapshot()
        response = getattr(self.client, method)(path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(before == database_snapshot(), 'Rejected input changed DB/M2M')
    return test


for method in ('post', 'put', 'patch'):
    for field, value in FORBIDDEN.items():
        setattr(UserFieldsTests, f'test_{method}_rejects_{field}', forbidden_test(method, field, value))
    if method != 'post':
        setattr(UserFieldsTests, f'test_{method}_rejects_password', forbidden_test(method, 'password', 'test-only-new-password'))


class SecurityHTTPTests(SimpleTestCase):
    def test_drf_status_and_envelope(self):
        for exception, status in ((ValidationError({'name': ['Invalid']}), 400), (PermissionDenied(), 403),
                                  (NotFound(), 404), (NotAuthenticated(), 401), (AuthenticationFailed(), 401)):
            with self.subTest(status=status, exception=type(exception).__name__):
                response = CustomExceptionHandler(exception, {})
                self.assertEqual(response.status_code, status)
                self.assertEqual(set(response.data), {'code', 'msg', 'data'})
