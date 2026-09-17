"""Real-router mutation matrix, with legacy grants and whitelist deliberately present."""
from django.apps import apps
from django.test import TestCase
from rest_framework.test import APIClient
from coreadmin.system.models import (Users, Role, Dept, Menu, MenuButton, MenuField,
    RoleMenuPermission, RoleMenuButtonPermission, ApiWhiteList)


def database_snapshot():
    # Include auto-created through tables. Compare without printing sensitive rows.
    return {model._meta.label: list(model.objects.order_by('pk').values())
            for model in apps.get_app_config('system').get_models(include_auto_created=True)}


class GrantManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Dept.objects.create(name='Test department', key='test-dept')
        cls.role = Role.objects.create(name='Target role', key='target-role')
        cls.normal = Users.objects.create(username='normal', name='Normal', password='!', dept=cls.dept)
        cls.inactive = Users.objects.create(username='inactive', name='Inactive', password='!', is_superuser=True, is_active=False)
        cls.admin = Users.objects.create(username='admin', name='Admin', password='!', is_superuser=True)
        cls.member = Users.objects.create(username='member', name='Member', password='!')
        cls.member.role.add(cls.role)
        cls.menu = Menu.objects.create(name='Target menu', component_name='test_menu')
        cls.button = MenuButton.objects.create(menu=cls.menu, name='Target button', value='target', api='/target/', method=0)
        cls.field = MenuField.objects.create(menu=cls.menu, model='Users', field_name='name', title='Name')
        cls.menu_grant = RoleMenuPermission.objects.create(role=cls.role, menu=cls.menu)
        cls.button_grant = RoleMenuButtonPermission.objects.create(role=cls.role, menu_button=cls.button)
        cls.button_grant.dept.add(cls.dept)
        cls.white = ApiWhiteList.objects.create(url='/target/', method=0)
        legacy = Role.objects.create(name='Legacy administrator', key='legacy-admin')
        cls.normal.role.add(legacy)
        for method in (0, 1, 2, 3, 5):
            button = MenuButton.objects.create(menu=cls.menu, name='Legacy bypass', value='legacy-' + str(method), api='/api/system/.*', method=method)
            RoleMenuButtonPermission.objects.create(role=legacy, menu_button=button, data_range=3)
            ApiWhiteList.objects.create(url='/api/system/.*', method=method, enable_datasource=False)

    def case(self, resource, action):
        fixtures = {
            'role': (self.role.pk, {'name': 'New role', 'key': 'new-role'}),
            'role_menu_permission': (self.menu_grant.pk, {'role': self.role.pk, 'menu': self.menu.pk}),
            'role_menu_button_permission': (self.button_grant.pk, {'role': self.role.pk, 'menu_button': self.button.pk, 'data_range': 3}),
            'menu_button': (self.button.pk, {'menu': self.menu.pk, 'name': 'New button', 'value': 'new-button', 'api': '/new/', 'method': 1}),
            'column': (self.field.pk, {'menu': self.menu.pk, 'model': 'Users', 'field_name': 'email', 'title': 'Email'}),
            'api_white_list': (self.white.pk, {'url': '/new/', 'method': 1}),
        }
        pk, payload = fixtures[resource]
        base = '/api/system/' + resource + '/'
        if action == 'create': return 'post', base, payload
        if action == 'update': return 'put', base + str(pk) + '/', payload
        if action == 'partial_update': return 'patch', base + str(pk) + '/', payload
        if action == 'destroy': return 'delete', base + str(pk) + '/', {}
        if action == 'multiple_delete': return 'delete', base + action + '/', {'keys': [pk]}
        custom = {
            'set_role_users': ('put', str(self.role.pk) + '/', {'direction': 'right', 'movedKeys': [self.normal.pk]}),
            'add_role_users': ('post', str(self.role.pk) + '/', {'users_id': [self.normal.pk]}),
            'remove_role_user': ('delete', str(self.role.pk) + '/', {'user_id': [self.member.pk]}),
            'save_auth': ('post', '', {'role': self.role.pk, 'menu': []}),
            'set_role_menu': ('put', '', {'roleId': self.role.pk, 'menuId': self.menu.pk, 'isCheck': False}),
            'set_role_menu_field': ('put', str(self.role.pk) + '/', [{'id': self.field.pk, 'is_query': True, 'is_create': False, 'is_update': False}]),
            'set_role_menu_btn': ('put', '', {'roleId': self.role.pk, 'btnId': self.button.pk, 'isCheck': False}),
            'set_role_menu_btn_data_range': ('put', '', {'role_menu_btn_perm_id': self.button_grant.pk, 'data_range': 4, 'dept': []}),
            'batch_create': ('post', '', {'menu': self.menu.pk}),
            'auto_match_fields': ('post', '', {'menu': self.menu.pk, 'model': 'Users'}),
        }
        method, detail, payload = custom[action]
        return method, base + detail + action + '/', payload

    def test_normal_read_permissions_are_preserved(self):
        from coreadmin.foundation_tests.access_fixtures import grant
        from coreadmin.access.fields import READ
        aliases = {'role': ('role:Search', 'Role'), 'role_menu_permission': ('role_menu_permission:Search', 'RoleMenuPermission'),
                   'role_menu_button_permission': ('role_menu_button_permission:Search', 'RoleMenuButtonPermission'),
                   'menu_button': ('btn:Search', 'MenuButton'), 'column': ('column:Search', 'MenuField'),
                   'api_white_list': ('api_white_list:Search', 'ApiWhiteList')}
        for resource, (alias, model) in aliases.items():
            grant(self.normal, alias, model, fields=READ[resource])
        client = APIClient()
        client.force_authenticate(self.normal)
        for resource in MUTATIONS:
            with self.subTest(resource=resource):
                response = client.get('/api/system/' + resource + '/', {'menu': self.menu.pk} if resource == 'column' else {})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['code'], 2000)



def mutation_test(actor, resource, action):
    def test(self):
        client = APIClient()
        if actor != 'anonymous':
            client.force_authenticate(getattr(self, actor))
        method, path, payload = self.case(resource, action)
        before = database_snapshot()
        response = getattr(client, method)(path, payload, format='json')
        after = database_snapshot()
        if actor == 'admin':
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['code'], 2000)
            self.assertTrue(before != after, 'Allowed mutation must perform a real write')
        else:
            self.assertIn(response.status_code, (401, 403) if actor == 'anonymous' else (403,))
            self.assertTrue(before == after, 'Rejected mutation changed database or M2M state')
    return test


MUTATIONS = {
    'role': ('set_role_users', 'add_role_users', 'remove_role_user'),
    'role_menu_permission': ('save_auth',),
    'role_menu_button_permission': ('set_role_menu', 'set_role_menu_field', 'set_role_menu_btn', 'set_role_menu_btn_data_range'),
    'menu_button': ('batch_create',),
    'column': ('auto_match_fields',),
    'api_white_list': (),
}
for resource, custom in MUTATIONS.items():
    for action in ('create', 'update', 'partial_update', 'destroy', 'multiple_delete') + custom:
        for actor in ('anonymous', 'normal', 'inactive', 'admin'):
            setattr(GrantManagementTests, 'test_' + '_'.join((actor, resource, action)), mutation_test(actor, resource, action))
