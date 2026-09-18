from django.test import TestCase
from rest_framework.test import APIClient
from coreadmin.foundation_tests.access_fixtures import grant
from coreadmin.system.models import Users, Role, Menu, MenuButton, RoleMenuPermission


class ProjectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create(username='projection', pwd_change_count=1)
        cls.admin = Users.objects.create(username='projection-admin', is_superuser=True, pwd_change_count=1)

    def client_for(self, actor):
        client = APIClient(); client.force_authenticate(actor)
        return client

    def test_missing_database_aliases_are_projected_for_admin(self):
        response = self.client_for(self.admin).get('/api/system/menu_button/menu_button_all_permission/')
        self.assertEqual(response.status_code, 200)
        for alias in ('role:AuthorizedAdd', 'role:AuthorizedSearch', 'role:AuthorizedDel', 'user:Export'):
            self.assertIn(alias, response.data['data'])
        self.assertEqual(MenuButton.objects.count(), 0)
        self.assertNotIn('file:Update', response.data['data'])

    def test_normal_projection_only_effective_aliases(self):
        permission = grant(self.user, 'user:Retrieve', 'Users', fields=['name'])
        grant(self.user, 'unknown-value', 'Users')
        grant(self.user, 'role:Create', 'Role')
        client = self.client_for(self.user)
        url = '/api/system/menu_button/menu_button_all_permission/'
        response = client.get(url)
        self.assertIn('user:Retrieve', response.data['data'])
        self.assertNotIn('unknown-value', response.data['data'])
        self.assertNotIn('role:Create', response.data['data'])
        Role.objects.filter(pk=permission.role_id).update(status=False)
        self.assertNotIn('user:Retrieve', client.get(url).data['data'])

    def test_navigation_does_not_grant_action_and_filters_disabled_roles(self):
        role = Role.objects.create(name='Navigation', key='navigation')
        self.user.role.add(role)
        menu = Menu.objects.create(name='Navigation', status=True)
        RoleMenuPermission.objects.create(role=role, menu=menu)
        client = self.client_for(self.user)
        response = client.get('/api/system/menu/web_router/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data['data']], [menu.id])
        self.assertEqual(client.get('/api/system/user/').status_code, 403)
        Role.objects.filter(pk=role.pk).update(status=False)
        self.assertEqual(client.get('/api/system/menu/web_router/').data['data'], [])

    def test_unknown_alias_diagnostics_do_not_change_historical_mapping(self):
        menu = Menu.objects.create(name='Metadata')
        button = MenuButton.objects.create(menu=menu, name='Unknown', value='unknown', api='/old/', method=1)
        response = self.client_for(self.admin).get(f'/api/system/menu_button/{button.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['mapping_status'], 'UNREGISTERED')
        button.refresh_from_db(); self.assertEqual(button.api, '/old/')

    def test_non_viewset_options_and_self_service_identity(self):
        client = self.client_for(self.user)
        self.assertEqual(client.options('/api/login/').data['data'], {})
        from coreadmin.system.services.auth import AuthService
        from rest_framework_simplejwt.tokens import AccessToken
        client.force_authenticate(self.user, token=AccessToken(AuthService.issue(self.user)['access']))
        self.assertEqual(client.post('/api/logout/').status_code, 200)
        self.user.is_active = False
        self.assertEqual(client.post('/api/logout/').status_code, 403)
        self.assertEqual(APIClient().options('/api/login/').status_code, 403)

    def test_admin_scope_editor_replaces_custom_departments_and_keeps_identity(self):
        from coreadmin.system.models import Dept, RoleMenuButtonPermission
        first = Dept.objects.create(name='First')
        second = Dept.objects.create(name='Second')
        permission = grant(self.user, 'user:Retrieve', 'Users', fields=['name'], scope=4, departments=[first])
        client = self.client_for(self.admin)
        url = '/api/system/role_menu_button_permission/set_role_menu_btn_data_range/'
        response = client.put(url, {'role_menu_btn_perm_id': permission.id, 'data_range': 4, 'dept': [second.id]}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['id'], permission.menu_button_id)
        self.assertEqual(response.data['data']['role_menu_btn_perm_id'], permission.id)
        self.assertEqual(response.json()['data']['dept'], [second.id])
        response = client.put(url, {'role_menu_btn_perm_id': permission.id, 'data_range': 3, 'dept': [second.id]}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(permission.dept.exists())
