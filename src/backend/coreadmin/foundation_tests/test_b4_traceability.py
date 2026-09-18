"""B4 operational traceability on disposable PostgreSQL, not an AuditTrail."""
import json
from unittest.mock import patch

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from coreadmin.system.models import (Users, Role, Menu, MenuButton, Dept, MenuField,
    RoleMenuButtonPermission, SystemConfig, OperationLog)
from coreadmin.utils.log_sanitization import (MAX_LOG_SERIALIZED_SIZE, REDACTED,
    TRUNCATED, sanitize_log_value, serialize_log_value)


@override_settings(API_LOG_ENABLE=True, API_LOG_METHODS=['POST', 'PUT', 'DELETE'])
class TargetTests(TestCase):
    def setUp(self):
        self.admin = Users.objects.create(username='b4-admin', is_superuser=True, pwd_change_count=1)
        self.user = Users.objects.create(username='b4-user', pwd_change_count=1)
        self.role = Role.objects.create(name='role', key='role')
        self.menu = Menu.objects.create(name='menu', sort=1)
        self.button = MenuButton.objects.create(menu=self.menu, name='button', value='user:Search', api='/')
        self.dept = Dept.objects.create(name='dept', sort=1)
        self.field = MenuField.objects.create(menu=self.menu, model='Users', field_name='name', title='Name')
        self.root = SystemConfig.objects.create(title='root', key='b4_root')
        self.config = SystemConfig.objects.create(title='sample', key='sample', parent=self.root, value='old')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def send(self, method, url, payload, expected=200):
        before = OperationLog.objects.count()
        response = getattr(self.client, method)(url, payload, format='json')
        self.assertEqual(response.status_code, expected, response.data)
        self.assertEqual(OperationLog.objects.count(), before + 1)
        log = OperationLog.objects.latest('id')
        self.assertEqual(log.creator_id, self.client.handler._force_user.pk)
        self.assertTrue(log.create_datetime)
        self.assertEqual(log.request_path, url)
        self.assertEqual(log.request_method, method.upper())
        self.assertEqual(json.loads(log.json_result)['http_status'], expected)
        self.assertEqual(log.status, expected == 200)
        return response, log

    def target(self, log, expected):
        self.assertEqual(json.loads(log.request_target), expected)

    def config_row(self, obj, value='new'):
        return dict(id=str(obj.pk), title=obj.title, key=obj.key, parent=self.root.pk, value=value)

    def test_detail_put_patch_destroy(self):
        url = f'/api/system/role/{self.role.pk}/'
        for method in ('put', 'patch', 'delete'):
            payload = {'name': 'changed', 'key': 'role'} if method != 'delete' else {}
            _, log = self.send(method, url, payload)
            self.target(log, {'role': [self.role.pk]})

    def test_create_and_batch_create_capture_saved_ids(self):
        for payload in ({'name': 'created', 'key': 'created'},
                        [{'name': 'a', 'key': 'a'}, {'name': 'b', 'key': 'b'}]):
            response, log = self.send('post', '/api/system/role/', payload)
            data = response.data['data']
            rows = data if isinstance(data, list) else [data]
            self.target(log, {'role': sorted(row['id'] for row in rows)})

    def test_role_user_actions_and_client_target_spoof(self):
        old = OperationLog.objects.create(request_target='{"role":[999]}', request_body='historical')
        before = OperationLog.objects.filter(pk=old.pk).values().get()
        for method, action, payload in (
            ('put', 'set_role_users', {'direction': 'right', 'movedKeys': [str(self.user.pk), self.user.pk]}),
            ('post', 'add_role_users', {'users_id': [self.user.pk]}),
            ('delete', 'remove_role_user', {'user_id': [self.user.pk]})):
            payload.update(log_id=old.pk, request_target={'role': [999]}, id=old.pk)
            _, log = self.send(method, f'/api/system/role/{self.role.pk}/{action}/', payload)
            self.target(log, {'role': [self.role.pk], 'users': [self.user.pk]})
        self.assertEqual(before, OperationLog.objects.filter(pk=old.pk).values().get())

    def test_menu_grant_actions(self):
        _, log = self.send('post', '/api/system/role_menu_permission/save_auth/',
                           {'role': str(self.role.pk), 'menu': [self.menu.pk]})
        self.target(log, {'role': [self.role.pk], 'menu': [self.menu.pk]})
        _, log = self.send('put', '/api/system/role_menu_button_permission/set_role_menu/',
                           {'roleId': self.role.pk, 'menuId': self.menu.pk, 'isCheck': False})
        self.target(log, {'role': [self.role.pk], 'menu': [self.menu.pk]})

    def test_button_and_custom_department_targets(self):
        _, log = self.send('put', '/api/system/role_menu_button_permission/set_role_menu_btn/',
            {'roleId': self.role.pk, 'btnId': self.button.pk, 'isCheck': True, 'data_range': 4, 'dept': [self.dept.pk]})
        self.target(log, {'role': [self.role.pk], 'menubutton': [self.button.pk], 'dept': [self.dept.pk]})
        grant = RoleMenuButtonPermission.objects.get(role=self.role, menu_button=self.button)
        _, log = self.send('put', '/api/system/role_menu_button_permission/set_role_menu_btn_data_range/',
            {'role_menu_btn_perm_id': grant.pk, 'data_range': 4, 'dept': [self.dept.pk]})
        self.target(log, {'rolemenubuttonpermission': [grant.pk], 'dept': [self.dept.pk]})

    def test_field_permission_targets(self):
        _, log = self.send('put', f'/api/system/role_menu_button_permission/{self.role.pk}/set_role_menu_field/',
            [{'id': self.field.pk, 'is_query': True, 'is_create': False, 'is_update': False}])
        self.target(log, {'role': [self.role.pk], 'menufield': [self.field.pk]})

    def test_normal_config_targets(self):
        _, log = self.send('put', '/api/system/system_config/save_content/', [self.config_row(self.config)])
        self.target(log, {'systemconfig': [self.config.pk]})
        self.config.refresh_from_db()
        self.assertEqual(self.config.value, 'new')

    def test_large_config_body_retains_every_target_beyond_50_items(self):
        rows = SystemConfig.objects.bulk_create([
            SystemConfig(title=str(i), key=str(i), parent=self.root, value='old') for i in range(55)])
        payload = [self.config_row(row, 'x' * 700) for row in reversed(rows)]
        self.assertGreater(len(json.dumps(payload)), MAX_LOG_SERIALIZED_SIZE)
        _, log = self.send('put', '/api/system/system_config/save_content/', payload)
        self.assertEqual(json.loads(log.request_body)['body'], TRUNCATED)
        self.target(log, {'systemconfig': sorted(row.pk for row in rows)})
        self.assertEqual(SystemConfig.objects.filter(pk__in=[r.pk for r in rows], value='x' * 700).count(), 55)
        response = self.client.get(f'/api/system/operation_log/{log.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['request_target'], log.request_target)

    def test_bulk_full_set_normalization_and_failed_full_set(self):
        other = Role.objects.create(name='other', key='other')
        expected = sorted([self.role.pk, other.pk])
        _, log = self.send('delete', '/api/system/role/multiple_delete/',
                           {'keys': [other.pk, str(self.role.pk), self.role.pk]})
        self.target(log, {'role': expected})
        self.assertFalse(Role.objects.filter(pk__in=expected).exists())
        survivor = Role.objects.create(name='survivor', key='survivor')
        _, log = self.send('delete', '/api/system/role/multiple_delete/', {'keys': [survivor.pk, 999999]}, 404)
        self.assertIsNone(log.request_target)
        self.assertTrue(Role.objects.filter(pk=survivor.pk).exists())

    def test_malformed_missing_unauthorized_and_field_failure_unchanged(self):
        url = '/api/system/system_config/save_content/'
        for identity, status in [('abc', 400), (999999, 404)]:
            payload = self.config_row(self.config); payload['id'] = identity
            _, log = self.send('put', url, [payload], status)
            self.assertIsNone(log.request_target)
        payload = self.config_row(self.config); payload['creator'] = self.admin.pk
        _, log = self.send('put', url, [payload], 400)
        self.assertIsNone(log.request_target)
        self.client.force_authenticate(self.user)
        _, log = self.send('put', url, [self.config_row(self.config)], 403)
        self.assertIsNone(log.request_target)
        self.config.refresh_from_db()
        self.assertEqual(self.config.value, 'old')

    def test_password_reset_target_and_redaction(self):
        value = 'B4-Only-Synthetic-Password-2026!'
        _, log = self.send('put', f'/api/system/user/{self.user.pk}/reset_password/',
                           {'newPassword': value, 'newPassword2': value})
        self.target(log, {'users': [self.user.pk]})
        self.assertNotIn(value, log.request_body)

    def test_menu_and_dept_move_targets(self):
        for resource, obj in [('menu', self.menu), ('dept', self.dept)]:
            for action in ('move_up', 'move_down'):
                _, log = self.send('post', f'/api/system/{resource}/{action}/', {resource + '_id': obj.pk})
                self.target(log, {resource: [obj.pk]})

    def test_metadata_failure_does_not_change_mutation(self):
        with patch('coreadmin.utils.log_targets.json') as encoder:
            encoder.dumps.side_effect = RuntimeError('synthetic metadata failure')
            response = self.client.patch(f'/api/system/role/{self.role.pk}/', {'name': 'metadata survived'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.role.refresh_from_db()
        self.assertEqual(self.role.name, 'metadata survived')

    def test_persistence_failure_does_not_change_mutation(self):
        before = OperationLog.objects.count()
        with patch.object(OperationLog.objects, 'create', side_effect=RuntimeError('synthetic log failure')):
            response = self.client.patch(f'/api/system/role/{self.role.pk}/', {'name': 'log survived'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.role.refresh_from_db()
        self.assertEqual(self.role.name, 'log survived')
        self.assertEqual(OperationLog.objects.count(), before)

    def test_persisted_sensitive_representations_and_normal_config(self):
        marker = 'B4_SYNTHETIC_SENTINEL'
        cases = [(key, {'items': [{key: marker}]}) for key in
                 ('password', 'access', 'refresh', 'secret', 'jwt', 'jwt_token', 'idJWT')]
        cases += [('encoded', json.dumps({'items': [{'password': marker, 'token': marker, 'jwt': marker}]})),
                  ('storage_secret', marker), ('default_password', marker)]
        for key, value in cases:
            with self.subTest(key=key):
                payload = self.config_row(self.config, value); payload['key'] = key
                _, log = self.send('put', '/api/system/system_config/save_content/', [payload])
                self.assertNotIn(marker, log.request_body)
                self.assertIn(REDACTED, log.request_body)
        payload = self.config_row(self.config, 'CompLIMS'); payload['key'] = 'site_name'
        _, log = self.send('put', '/api/system/system_config/save_content/', [payload])
        self.assertEqual(json.loads(log.request_body)['body'][0]['value'], 'CompLIMS')


class StructuredStringTests(TestCase):
    def test_json_representation_and_input_unchanged(self):
        value = json.dumps({'jwt': 'synthetic', 'ok': [7, 8]})
        encoded = sanitize_log_value({'nested': value})['nested']
        self.assertEqual(json.loads(encoded), {'jwt': REDACTED, 'ok': [7, 8]})
        self.assertIn('synthetic', value)
        for ordinary in ('plain text', '{not json', '[malformed'):
            self.assertEqual(sanitize_log_value(ordinary), ordinary)

    def test_json_array_pair_and_shared_limits(self):
        value = json.dumps([{'key': 'default_password', 'value': 'synthetic'}])
        self.assertEqual(json.loads(sanitize_log_value(value))[0]['value'], REDACTED)
        deep = {'password': 'synthetic'}
        for _ in range(10): deep = {'nested': deep}
        self.assertNotIn('synthetic', serialize_log_value(json.dumps(deep)))
        wide = json.dumps([{'jwt': 'synthetic'} for _ in range(100)])
        result = serialize_log_value(wide)
        self.assertNotIn('synthetic', result)
        self.assertIn(TRUNCATED, result)
        huge = '{"password":"' + 'x' * MAX_LOG_SERIALIZED_SIZE + '"}'
        self.assertEqual(sanitize_log_value(huge), TRUNCATED)
        expanded = {'rows': [json.dumps({'items': list(range(50))}) for _ in range(50)]}
        self.assertLessEqual(len(serialize_log_value(expanded)), MAX_LOG_SERIALIZED_SIZE)


class MigrationTests(TransactionTestCase):
    def test_b3_upgrade_preserves_existing_rows_and_nullable_target(self):
        old = [('system', '0002_b3_integrity_auth')]
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(old)
            apps = executor.loader.project_state(old).apps
            user = apps.get_model('system', 'Users').objects.create(username='historical-b4', password='')
            apps.get_model('system', 'Role').objects.create(name='preserved', key='preserved')
            log = apps.get_model('system', 'OperationLog').objects.create(
                creator_id=user.pk, request_body='historical untouched', request_path='/historical/')
            def snapshot(registry):
                return {model._meta.label: list(model.objects.order_by('pk').values_list(
                    *[field.attname for field in model._meta.local_fields if field.name != 'request_target']))
                    for model in registry.get_app_config('system').get_models(include_auto_created=True)}
            before = snapshot(apps)
            MigrationExecutor(connection).migrate(latest)
            current = MigrationExecutor(connection).loader.project_state(latest).apps
            self.assertEqual(before, snapshot(current))
            self.assertIsNone(OperationLog.objects.get(pk=log.pk).request_target)
            with connection.cursor() as cursor:
                cursor.execute("SELECT is_nullable FROM information_schema.columns WHERE table_name=%s AND column_name='request_target'",
                               [OperationLog._meta.db_table])
                self.assertEqual(cursor.fetchone(), ('YES',))
        finally:
            MigrationExecutor(connection).migrate(latest)
