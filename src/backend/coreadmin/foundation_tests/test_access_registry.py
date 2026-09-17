"""The route inventory must not silently enlarge the permission vocabulary."""
from types import SimpleNamespace

from django.test import SimpleTestCase

from coreadmin.access.registry import (
    ALIASES, AUTH_RESOURCES, Policy, REGISTRY, aliases_for, resolve,
)


class ActionRegistryTests(SimpleTestCase):
    def test_non_viewset_production_routes_have_entry_policies(self):
        from django.urls import get_resolver, URLResolver
        from coreadmin.access.entrypoints import CanonicalEntryMixin
        from coreadmin.access.registry import ENTRYPOINTS
        def walk(patterns, prefix=''):
            for pattern in patterns:
                path = prefix + str(pattern.pattern)
                if isinstance(pattern, URLResolver):
                    yield from walk(pattern.url_patterns, path)
                else:
                    yield path, pattern.callback
        found = set()
        for path, callback in walk(get_resolver().url_patterns):
            if hasattr(callback, 'actions'):
                continue
            cls = getattr(callback, 'cls', None)
            self.assertIsNotNone(cls, path)
            self.assertTrue(issubclass(cls, CanonicalEntryMixin), path)
            for method in ('get', 'post', 'put', 'patch', 'delete'):
                if hasattr(cls, method):
                    self.assertIn(('/' + path, method.upper()), ENTRYPOINTS)
                    found.add('/' + path)
        self.assertEqual(found, {'/api/login/', '/api/logout/', '/api/token/refresh/',
                                 '/api/captcha/', '/api/init/dictionary/', '/api/init/settings/'})

    def test_every_registered_system_route_method_has_an_explicit_policy(self):
        from coreadmin.system.urls import urlpatterns
        for pattern in urlpatterns:
            callback = pattern.callback
            view = callback.cls()
            for method, action in callback.actions.items():
                view.action = action
                with self.subTest(route=str(pattern.pattern), method=method, action=action):
                    self.assertIsNotNone(resolve(view, method.upper()))
                    if method == 'get':
                        self.assertIsNotNone(resolve(view, 'HEAD'))
            self.assertEqual(resolve(view, 'OPTIONS').name, 'metadata')

    def test_unregistered_resource_and_action_do_not_have_policy(self):
        from coreadmin.system.views.user import UserViewSet
        self.assertIsNone(resolve(SimpleNamespace(action='list'), 'GET'))
        view = UserViewSet()
        view.action = 'unreviewed_action'
        self.assertIsNone(resolve(view, 'GET'))
        view.action = 'list'
        self.assertIsNone(resolve(view, 'TRACE'))

    def test_patch_and_head_share_canonical_capabilities_without_mutating_method(self):
        from coreadmin.system.views.user import UserViewSet
        view = UserViewSet()
        view.action = 'partial_update'
        self.assertEqual(resolve(view, 'PATCH').code, 'user.update')
        view.action = 'retrieve'
        self.assertEqual(resolve(view, 'HEAD').code, 'user.retrieve')

    def test_aliases_have_registered_targets_and_never_use_url_metadata(self):
        codes = {action.code for action in REGISTRY.values()}
        self.assertTrue(set(ALIASES.values()) <= codes)
        self.assertNotIn('/api/system/user/.*', ALIASES)
        self.assertNotIn('VIEWSETNAME:Create', ALIASES)
        self.assertEqual(ALIASES['messageCenter:Delete'], 'message_center.destroy')
        self.assertEqual(ALIASES['menu:MoveUp'], 'menu.move_up')
        self.assertEqual(ALIASES['downloadCenter:Search'], 'download_center.list')
        self.assertNotEqual(ALIASES['role:Permission'], ALIASES['role:Retrieve'])
        self.assertIn('user:Export', aliases_for('user.export_data'))

    def test_b1_shutdown_and_six_bulk_opt_ins_remain_explicit(self):
        for (resource, name, method), action in REGISTRY.items():
            with self.subTest(resource=resource, name=name, method=method):
                if name == 'multiple_delete':
                    self.assertEqual(action.policy, Policy.FIXED_SUPERUSER
                                     if resource in AUTH_RESOURCES else Policy.B1_SHUTDOWN)
                if name == 'import_data' and method in {'POST', 'HEAD'}:
                    self.assertEqual(action.policy, Policy.B1_SHUTDOWN)
                if resource in {'file', 'operation_log', 'login_log', 'download_center'} and name in {'create', 'update', 'destroy'}:
                    self.assertEqual(action.policy, Policy.B1_SHUTDOWN)

    def test_export_alias_has_one_capability(self):
        self.assertEqual(REGISTRY['user', 'export_data', 'GET'].code,
                         REGISTRY['user', 'export_data', 'POST'].code)
