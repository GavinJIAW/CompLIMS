"""B1C real-router shutdown boundaries; no real storage input is opened."""
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from coreadmin.system.models import Users, Dept, Menu, Role, RoleMenuPermission, FileList, DownloadCenter, SystemConfig, ApiWhiteList
from coreadmin.system.views.file_list import FileViewSet
from coreadmin.system.urls import system_url
from coreadmin.foundation_tests.test_grant_management import database_snapshot


PUBLIC_KEYS = {
    'login.site_title', 'login.site_name', 'login.site_logo', 'login.login_background',
    'base.web_title', 'base.web_favicon', 'base.captcha_state',
}
ACTORS = ('anonymous', 'normal', 'inactive', 'admin')


class DangerousEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.normal = Users.objects.create(username='b1c-normal', password='!')
        cls.other = Users.objects.create(username='b1c-other', password='!')
        cls.inactive = Users.objects.create(username='b1c-inactive', password='!', is_active=False, is_superuser=True)
        cls.admin = Users.objects.create(username='b1c-admin', password='!', is_superuser=True)
        cls.dept = Dept.objects.create(name='One', key='one', sort=1)
        cls.dept2 = Dept.objects.create(name='Two', key='two', sort=2)
        cls.menu = Menu.objects.create(name='One', sort=1)
        cls.menu2 = Menu.objects.create(name='Two', sort=2)
        role = Role.objects.create(name='Read one menu', key='b1c-read')
        cls.normal.role.add(role)
        RoleMenuPermission.objects.create(role=role, menu=cls.menu)
        cls.file = FileList.objects.create(name='Metadata only', url='never-open.txt', md5sum='test', size='1')
        cls.download = DownloadCenter.objects.create(creator=cls.normal, task_name='Own')
        cls.other_download = DownloadCenter.objects.create(creator=cls.other, task_name='Other')
        cls.parent = SystemConfig.objects.create(title='Test', key='test')
        cls.config = SystemConfig.objects.create(title='Child', key='child', parent=cls.parent, value='old', setting={'table': 'Users'})
        # A legacy whitelist must not bypass the new boundaries.
        for method in (0, 1, 2, 3, 5):
            ApiWhiteList.objects.create(url='/api/system/.*', method=method, enable_datasource=False)

    def client_for(self, actor):
        client = APIClient()
        if actor != 'anonymous':
            client.force_authenticate(getattr(self, actor))
        return client

    def unchanged(self, before):
        self.assertTrue(before == database_snapshot(), 'Rejected request changed database/M2M state')

    def test_download_own_scope(self):
        for actor, expected in (('normal', {self.download.pk}), ('admin', {self.download.pk, self.other_download.pk})):
            client = self.client_for(actor)
            response = client.get('/api/system/download_center/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual({row['id'] for row in response.data['data']}, expected)
            own = client.get(f'/api/system/download_center/{self.download.pk}/')
            self.assertEqual(own.status_code, 200)
        self.assertEqual(self.client_for('normal').get(f'/api/system/download_center/{self.other_download.pk}/').status_code, 404)

    def test_inactive_normal_download(self):
        self.normal.is_active = False
        self.normal.save()
        self.assertEqual(self.client_for('normal').get('/api/system/download_center/').status_code, 403)

    def test_real_multipart_upload_never_enters_serializer_or_storage_selection(self):
        for actor in ACTORS:
            with self.subTest(actor=actor), patch.object(FileViewSet, 'get_serializer') as serializer, patch('application.dispatch.get_system_config_values') as engine, patch('django.core.files.storage.default_storage.save') as storage:
                before = database_snapshot()
                response = self.client_for(actor).post('/api/system/file/', {
                    'file': SimpleUploadedFile('b1c.txt', b'TEST ONLY', content_type='text/plain'),
                }, format='multipart')
                self.assertIn(response.status_code, (405,) if actor == 'admin' else (401, 403))
                serializer.assert_not_called()
                # OSS/COS/local storage branches all follow this engine lookup.
                engine.assert_not_called()
                storage.assert_not_called()
                self.unchanged(before)

    def test_all_registered_post_imports_stop_before_file_processing(self):
        client = self.client_for('admin')
        for prefix, view, _ in system_url.registry:
            if not hasattr(view, 'import_data'):
                continue
            with self.subTest(prefix=prefix), patch('coreadmin.utils.import_export_mixin.import_to_data') as importer, patch('openpyxl.load_workbook') as workbook:
                before = database_snapshot()
                response = client.post(f'/api/system/{prefix}/import_data/', {'url': '../../forbidden.xlsx'}, format='json')
                self.assertEqual(response.status_code, 405)
                importer.assert_not_called()
                workbook.assert_not_called()
                self.unchanged(before)

    def test_dept_import_rejects_paths_before_open(self):
        client = self.client_for('admin')
        # URLConf is already imported. Only the request is guarded, not test setup.
        for path in ('/absolute.xlsx', '../outside.xlsx', r'C:\outside.xlsx', r'\\server\share\file.xlsx', 'symlink.xlsx'):
            with self.subTest(path=path), patch('builtins.open', side_effect=AssertionError('Unexpected file open')) as opened, patch('openpyxl.load_workbook') as workbook:
                response = client.post('/api/system/dept/import_data/', {'url': path}, format='json')
                self.assertEqual(response.status_code, 405)
                opened.assert_not_called()
                workbook.assert_not_called()

    def test_dept_get_template_preserved(self):
        response = self.client_for('admin').get('/api/system/dept/import_data/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'PK'))

    def test_head_cannot_enter_legacy_non_get_import_branch(self):
        with patch('coreadmin.utils.import_export_mixin.import_to_data') as importer, patch('openpyxl.load_workbook') as workbook:
            response = self.client_for('admin').head('/api/system/dept/import_data/', {'url': '../outside.xlsx'})
            self.assertEqual(response.status_code, 405)
            importer.assert_not_called()
            workbook.assert_not_called()

    def test_generic_bulk_disabled_before_queryset(self):
        preserved = {'role', 'role_menu_permission', 'role_menu_button_permission', 'menu_button', 'column', 'api_white_list'}
        for prefix, view, _ in system_url.registry:
            if prefix in preserved or not hasattr(view, 'multiple_delete'):
                continue
            with self.subTest(prefix=prefix), patch.object(view, 'get_queryset', side_effect=AssertionError('Queryset evaluated')):
                before = database_snapshot()
                response = self.client_for('admin').delete(f'/api/system/{prefix}/multiple_delete/', {'keys': [self.dept.pk]}, format='json')
                self.assertEqual(response.status_code, 405)
                self.unchanged(before)

    def test_public_settings_exact_allowlist(self):
        values = {key: 'UI test value' for key in PUBLIC_KEYS}
        values.update({key: 'TEST ONLY sentinel' for key in ('base.default_password', 'base.secret', 'file_storage.token', 'login.site_title.secret', 'database.password', 'unused.public')})
        queries = ({}, {'key': ''}, {'key': 'base'}, {'key': 'unknown'}, {'key': 'base.default_password'}, {'key': 'base.web_title|base.default_password'}, {'key': 'login.site_title'})
        for query in queries:
            with self.subTest(query=query), patch('application.dispatch.get_system_config', return_value=values):
                response = APIClient().get('/api/init/settings/', query)
                self.assertEqual(response.status_code, 200)
                expected = PUBLIC_KEYS if not query.get('key') else PUBLIC_KEYS.intersection(query['key'].split('|'))
                self.assertEqual(set(response.data['data']), expected)

    def test_disabled_public_setting_is_not_returned(self):
        parent = SystemConfig.objects.create(title='Login', key='login')
        SystemConfig.objects.create(parent=parent, title='Title', key='site_title', status=False)
        with patch('application.dispatch.get_system_config', return_value={'login.site_title': 'Title'}):
            self.assertEqual(APIClient().get('/api/init/settings/').data['data'], {})


def metadata_test(actor, resource, action):
    def test(self):
        pk = self.file.pk if resource == 'file' else self.download.pk
        suffix = f'{pk}/' if action == 'retrieve' else ('get_all/' if action == 'get_all' else '')
        response = self.client_for(actor).get(f'/api/system/{resource}/{suffix}')
        allowed = actor == 'admin' or (resource == 'download_center' and actor == 'normal')
        self.assertIn(response.status_code, (200,) if allowed else ((401, 403) if actor == 'anonymous' else (403,)))
        if allowed:
            self.assertEqual(response.data['code'], 2000)
    return test


def readonly_test(actor, resource, action):
    def test(self):
        pk = self.file.pk if resource == 'file' else self.download.pk
        method, suffix = {'create': ('post', ''), 'update': ('put', f'{pk}/'), 'patch': ('patch', f'{pk}/'), 'delete': ('delete', f'{pk}/'), 'bulk': ('delete', 'multiple_delete/')}[action]
        before = database_snapshot()
        with patch('coreadmin.system.views.file_list.FileSerializer.create', side_effect=AssertionError('Upload serializer entered')) as upload, patch('django.core.files.storage.base.Storage.save', side_effect=AssertionError('Storage save entered')) as storage:
            response = getattr(self.client_for(actor), method)(f'/api/system/{resource}/{suffix}', {'name': 'Changed', 'keys': [pk]}, format='json')
            self.assertIn(response.status_code, (405,) if actor == 'admin' or (resource == 'download_center' and actor == 'normal') else (401, 403, 405))
            upload.assert_not_called()
            storage.assert_not_called()
        self.unchanged(before)
    return test


def config_test(actor, action):
    def test(self):
        base = '/api/system/system_config/'
        payload = {'title': 'Changed', 'key': 'new-child', 'parent': self.parent.pk}
        method, suffix = {'create': ('post', ''), 'update': ('put', f'{self.config.pk}/'), 'patch': ('patch', f'{self.config.pk}/'), 'delete': ('delete', f'{self.config.pk}/'), 'save_content': ('put', 'save_content/'), 'metadata': ('get', 'get_association_table/'), 'lookup': ('get', f'get_table_data/{self.config.pk}/')}[action]
        if action == 'save_content':
            payload = [{'id': self.config.pk, **payload}]
        before = database_snapshot()
        if action == 'lookup':
            with patch('coreadmin.system.views.system_config.get_all_models_objects', side_effect=AssertionError('Dynamic lookup entered')) as lookup:
                response = self.client_for(actor).get(base + suffix)
                self.assertEqual(response.status_code, 405)
                lookup.assert_not_called()
            self.unchanged(before)
            return
        response = getattr(self.client_for(actor), method)(base + suffix, payload if method != 'get' else {}, format='json')
        if actor == 'admin':
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['code'], 2000)
            if action != 'metadata':
                self.assertTrue(before != database_snapshot())
        else:
            self.assertIn(response.status_code, (401, 403) if actor == 'anonymous' else (403,))
            self.unchanged(before)
    return test


def custom_test(actor, resource, action):
    def test(self):
        obj = self.menu if resource == 'menu' else self.dept
        obj2 = self.menu2 if resource == 'menu' else self.dept2
        before = database_snapshot()
        client = self.client_for(actor)
        if action == 'read':
            suffix = 'get_all_menu' if resource == 'menu' else 'dept_info'
            response = client.get(f'/api/system/{resource}/{suffix}/', {'dept_id': obj.pk})
            allowed = actor in ('admin', 'normal')
        else:
            response = client.post(f'/api/system/{resource}/{action}/', {resource + '_id': obj2.pk if action == 'move_up' else obj.pk}, format='json')
            allowed = actor == 'admin'
        self.assertIn(response.status_code, (200,) if allowed else ((401, 403) if actor == 'anonymous' else (403,)))
        if allowed:
            self.assertEqual(response.data['code'], 2000)
            if resource == 'menu' and action == 'read' and actor == 'normal':
                self.assertEqual({row['id'] for row in response.data['data']}, {self.menu.pk})
            if action != 'read':
                obj.refresh_from_db()
                obj2.refresh_from_db()
                self.assertEqual((obj.sort, obj2.sort), (2, 1))
        else:
            self.unchanged(before)
    return test


for actor in ACTORS:
    for resource in ('file', 'download_center'):
        for action in ('list', 'retrieve') + (('get_all',) if resource == 'file' else ()):
            setattr(DangerousEndpointTests, f'test_{actor}_{resource}_{action}', metadata_test(actor, resource, action))
        for action in ('create', 'update', 'patch', 'delete', 'bulk'):
            setattr(DangerousEndpointTests, f'test_{actor}_{resource}_{action}', readonly_test(actor, resource, action))
    for action in ('create', 'update', 'patch', 'delete', 'save_content', 'metadata', 'lookup'):
        setattr(DangerousEndpointTests, f'test_{actor}_config_{action}', config_test(actor, action))
    for resource in ('menu', 'dept'):
        for action in ('read', 'move_up', 'move_down'):
            setattr(DangerousEndpointTests, f'test_{actor}_{resource}_{action}', custom_test(actor, resource, action))
