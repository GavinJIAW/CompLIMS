"""Real routes, real JWT authentication and legacy permission regression."""
from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken
from coreadmin.system.models import Users, Role, Menu, MenuButton, RoleMenuButtonPermission, ApiWhiteList
from coreadmin.utils.permission import CustomPermission
from coreadmin.system.views.system_config import InitSettingsViewSet


class PublicEntrypointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.normal = Users.objects.create(username='b1e-normal', password='!')
        cls.inactive = Users.objects.create(username='b1e-inactive', password='!', is_active=False)
        cls.admin = Users.objects.create(username='b1e-admin', password='!', is_superuser=True)
        cls.inactive_admin = Users.objects.create(username='b1e-inactive-admin', password='!', is_superuser=True, is_active=False)
        role = Role.objects.create(name='Legacy', key='b1e-legacy')
        menu = Menu.objects.create(name='Legacy menu')
        button = MenuButton.objects.create(menu=menu, name='Read', value='b1e-read', api='/api/system/dictionary/', method=0)
        RoleMenuButtonPermission.objects.create(role=role, menu_button=button)
        cls.normal.role.add(role)
        cls.inactive.role.add(role)
        cls.inactive_admin.role.add(role)
        from coreadmin.foundation_tests.access_fixtures import grant
        grant(cls.normal, 'dictionary:Search', 'Dictionary', fields=['label', 'value'], role=role)

    def test_dictionary_and_real_role_init_crud_actor_matrix(self):
        for actor in (None, self.normal, self.inactive, self.admin, self.inactive_admin):
            client = APIClient()
            client.force_authenticate(actor)
            for path in ('/api/init/dictionary/?dictionary_key=all', '/api/init/dictionary/?dictionary_key=gender', '/api/system/role/init_crud/'):
                with self.subTest(actor='anonymous' if actor is None else actor.username, path=path):
                    with patch('application.dispatch.get_dictionary_config', return_value={'gender': []}):
                        response = client.get(path)
                    self.assertIn(response.status_code, (401, 403) if actor is None else ((200,) if actor.is_active else (403,)))

    def test_legacy_gate_precedes_whitelist_and_grants(self):
        for whitelist in (False, True):
            if whitelist:
                ApiWhiteList.objects.create(url='/api/system/dictionary/', method=0)
            for actor in (self.normal, self.inactive, self.admin, self.inactive_admin):
                with self.subTest(whitelist=whitelist, actor=actor.username):
                    request = APIRequestFactory().get('/api/system/dictionary/')
                    request.user = actor
                    from coreadmin.system.views.dictionary import DictionaryViewSet
                    view = DictionaryViewSet()
                    view.action = 'list'
                    self.assertEqual(bool(CustomPermission().has_permission(request, view)), actor.is_active)
                    client = APIClient()
                    client.force_authenticate(actor)
                    self.assertEqual(client.get('/api/system/dictionary/').status_code, 200 if actor.is_active else 403)

    def test_old_jwt_rejected_after_deactivation(self):
        token = str(RefreshToken.for_user(self.normal).access_token)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='JWT ' + token)
        self.assertEqual(client.get('/api/init/dictionary/?dictionary_key=gender').status_code, 200)
        self.normal.is_active = False
        self.normal.save(update_fields=['is_active'])
        self.assertIn(client.get('/api/init/dictionary/?dictionary_key=gender').status_code, (401, 403))

    def test_public_init_settings_remains_exact(self):
        values = {key: 'UI-safe' for key in InitSettingsViewSet.PUBLIC_KEYS}
        values.update({'base.default_password': 'HIDDEN', 'secret': 'HIDDEN', 'token': 'HIDDEN', 'credential': 'HIDDEN', 'database.password': 'HIDDEN'})
        client = APIClient()
        with patch('application.dispatch.get_system_config', return_value=values):
            response = client.get('/api/init/settings/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(set(response.data['data']), InitSettingsViewSet.PUBLIC_KEYS)

    def test_standard_login_captcha_and_refresh_remain_public(self):
        client = APIClient()
        with patch('application.dispatch.get_system_config_values', return_value=False):
            self.assertEqual(client.get('/api/captcha/').status_code, 200)
        # Missing credentials must reach validation, not an authentication gate.
        self.assertEqual(client.post('/api/login/', {}, format='json').status_code, 400)
        refresh = str(RefreshToken.for_user(self.normal))
        self.assertEqual(client.post('/api/token/refresh/', {'refresh': refresh}, format='json').status_code, 200)

    def test_health_endpoints_remain_public(self):
        client = APIClient()
        for path in ('/healthz', '/readiness'):
            self.assertEqual(client.get(path).status_code, 200)

    def test_registered_anonymous_permissions_have_explicit_inventory(self):
        from django.contrib.auth.models import AnonymousUser
        from django.urls import get_resolver, URLResolver
        allowed = set()

        def walk(patterns):
            for pattern in patterns:
                if isinstance(pattern, URLResolver):
                    yield from walk(pattern.url_patterns)
                else:
                    yield pattern.callback

        with self.assertNumQueries(0):
            for callback in walk(get_resolver().url_patterns):
                view_class = getattr(callback, 'cls', None)
                self.assertIsNotNone(view_class, 'Unclassified non-DRF production route')
                actions = getattr(callback, 'actions', {})
                for method in actions or ('get', 'post'):
                    if not actions and not hasattr(view_class, method):
                        continue
                    view = view_class(**callback.initkwargs)
                    view.action = actions.get(method)
                    request = APIRequestFactory().generic(method.upper(), '/inventory/')
                    request.user = AnonymousUser()
                    view.request = request
                    if all(permission.has_permission(request, view) for permission in view.get_permissions()):
                        allowed.add((view_class.__name__, view.action or method))
        self.assertEqual(allowed, {
            ('LoginView', 'post'), ('CaptchaView', 'get'), ('CanonicalTokenRefreshView', 'post'),
            ('InitSettingsViewSet', 'get'),
            # B1C shutdown route intentionally returns 405 before model lookup.
            ('SystemConfigViewSet', 'get_table_data'),
            # B1B similarly rejects every User import actor with a stable 405.
            ('UserViewSet', 'import_data'),
        })
