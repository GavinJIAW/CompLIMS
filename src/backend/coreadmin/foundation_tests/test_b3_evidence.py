"""B3 review closure: real PostgreSQL writes and authentication entrypoints."""
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.password_validation import get_default_password_validators
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.cache import cache
from django.db import connection, IntegrityError, transaction
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from coreadmin.system.models import (Users, Role, Dept, Menu, MenuButton,
    RoleMenuButtonPermission, SystemConfig, Dictionary, MessageCenter,
    MessageCenterTargetUser, AuthSession)
from coreadmin.system.services.auth import AuthService
from coreadmin.system.services.config import ConfigService

PASSWORD = 'Evidence-valid-password-2026!'


class ConfigIdentityTests(TransactionTestCase):
    def setUp(self):
        self.admin = Users.objects.create(username='admin', is_superuser=True, pwd_change_count=1)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.root = SystemConfig.objects.create(title='Root', key='root')
        self.rows = [SystemConfig.objects.create(title=k, key=k, parent=self.root, value='old')
                     for k in ('a', 'b')]
        self.url = '/api/system/system_config/save_content/'

    def row(self, obj, identity=None):
        return dict(id=obj.pk if identity is None else identity, title=obj.title,
                    key=obj.key, parent=self.root.pk, value='new')

    def unchanged(self):
        self.assertEqual(list(SystemConfig.objects.filter(pk__in=[o.pk for o in self.rows])
                             .values_list('value', flat=True)), ['old', 'old'])

    def test_integer_and_string_service_identity_equivalent(self):
        obj = self.rows[0]
        for identity in (obj.pk, str(obj.pk)):
            with self.subTest(identity_type=type(identity).__name__):
                obj.value = 'old'
                obj.save()
                ConfigService.save_batch([self.row(obj, identity)])
                obj.refresh_from_db()
                self.assertEqual(obj.value, 'new')

    def test_mixed_batch_uses_stable_pk_lock_order(self):
        with CaptureQueriesContext(connection) as queries:
            ConfigService.save_batch([self.row(self.rows[1], str(self.rows[1].pk)), self.row(self.rows[0])])
        self.assertEqual(set(SystemConfig.objects.filter(parent=self.root).values_list('value', flat=True)), {'new'})
        locks = [q['sql'] for q in queries if 'FOR UPDATE' in q['sql']]
        self.assertEqual(len(locks), 1)
        self.assertIn('ORDER BY', locks[0])
        self.assertIn('"id" ASC', locks[0])

    def test_endpoint_integer_and_string_equivalent(self):
        for obj, identity in zip(self.rows, (self.rows[0].pk, str(self.rows[1].pk))):
            response = self.client.put(self.url, [self.row(obj, identity)], format='json')
            self.assertEqual(response.status_code, 200, response.data)
            obj.refresh_from_db()
            self.assertEqual(obj.value, 'new')

    def test_string_first_nth_write_failure_rolls_back(self):
        original = SystemConfig.save
        def fail(obj, *args, **kwargs):
            if obj.pk == self.rows[1].pk:
                raise RuntimeError('injected second write failure')
            return original(obj, *args, **kwargs)
        with patch.object(SystemConfig, 'save', fail):
            response = self.client.put(self.url, [self.row(o, str(o.pk)) for o in self.rows], format='json')
        self.assertEqual(response.status_code, 500)
        self.unchanged()
        self.assertEqual(settings.SYSTEM_CONFIG['root.a'], 'old')

    def test_invalid_second_item_never_commits_first(self):
        bad = self.row(self.rows[1])
        bad['title'] = ''
        response = self.client.put(self.url, [self.row(self.rows[0], str(self.rows[0].pk)), bad], format='json')
        self.assertEqual(response.status_code, 400)
        self.unchanged()

    def test_target_and_field_errors_preserve_batch(self):
        for extra, expected in [({'id': '999999'}, 404), ({'id': 'abc'}, 400),
                                ({'children': []}, 400), ({'creator': self.admin.pk}, 400)]:
            with self.subTest(extra=extra):
                bad = dict(self.row(self.rows[1]), **extra)
                response = self.client.put(self.url, [self.row(self.rows[0], str(self.rows[0].pk)), bad], format='json')
                self.assertEqual(response.status_code, expected)
                self.unchanged()

    def test_normal_and_inactive_cannot_save(self):
        normal = Users.objects.create(username='normal', pwd_change_count=1)
        inactive = Users.objects.create(username='inactive', is_superuser=True, is_active=False, pwd_change_count=1)
        for actor in (normal, inactive):
            self.client.force_authenticate(actor)
            self.assertEqual(self.client.put(self.url, [self.row(self.rows[0], str(self.rows[0].pk))], format='json').status_code, 403)
            self.unchanged()


class ForeignKeyEdgeTests(TransactionTestCase):
    def setUp(self):
        self.user = Users.objects.create(username='edge')
        self.role = Role.objects.create(name='edge', key='edge')
        self.dept = Dept.objects.create(name='edge')
        menu = Menu.objects.create(name='edge')
        button = MenuButton.objects.create(menu=menu, name='edge', value='edge', api='/')
        self.grant = RoleMenuButtonPermission.objects.create(role=self.role, menu_button=button)

    def rejects(self, owner, relation, left, right, invalid_side):
        through = owner._meta.get_field(relation).remote_field.through
        fields = {f.remote_field.model: f.attname for f in through._meta.fields if f.many_to_one}
        values = {fields[type(left)]: left.pk, fields[type(right)]: right.pk}
        values[fields[type((left, right)[invalid_side])]] = 999999
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                through.objects.create(**values)
                connection.check_constraints()
        self.assertFalse(through.objects.exists())

    def test_users_role_left_fk(self):
        self.rejects(Users, 'role', self.user, self.role, 0)

    def test_users_role_right_fk(self):
        self.rejects(Users, 'role', self.user, self.role, 1)

    def test_grant_dept_left_fk(self):
        self.rejects(RoleMenuButtonPermission, 'dept', self.grant, self.dept, 0)

    def test_grant_dept_right_fk(self):
        self.rejects(RoleMenuButtonPermission, 'dept', self.grant, self.dept, 1)


class CacheRollbackTests(TransactionTestCase):
    def test_dictionary_real_save_and_delete_do_not_publish_rollback(self):
        root = Dictionary.objects.create(label='Root', value='evidence', is_value=False)
        row = Dictionary.objects.create(label='Old', value='one', parent=root, is_value=True)
        before = settings.DICTIONARY_CONFIG.copy()
        for operation in ('save', 'delete'):
            with self.subTest(operation=operation):
                with self.assertRaises(RuntimeError):
                    with transaction.atomic():
                        obj = Dictionary.objects.get(pk=row.pk)
                        if operation == 'save':
                            obj.label = 'Uncommitted'
                            obj.save()
                        else:
                            obj.delete()
                        self.assertEqual(settings.DICTIONARY_CONFIG, before)
                        raise RuntimeError('rollback')
                self.assertEqual(Dictionary.objects.get(pk=row.pk).label, 'Old')
                self.assertEqual(settings.DICTIONARY_CONFIG, before)
        row.label = 'Committed'
        row.save()
        self.assertEqual(settings.DICTIONARY_CONFIG['evidence']['children'][0]['label'], 'Committed')

    def test_message_recipient_real_signals_wait_for_commit(self):
        user = Users.objects.create(username='cache')
        message = MessageCenter.objects.create(title='cache', content='text')
        relation = MessageCenterTargetUser.objects.create(users=user, messagecenter=message)
        for operation in ('save', 'delete'):
            cache.set('last_db_change_time', 'committed-marker', timeout=None)
            with self.subTest(operation=operation):
                with self.assertRaises(RuntimeError):
                    with transaction.atomic():
                        obj = MessageCenterTargetUser.objects.get(pk=relation.pk)
                        if operation == 'save':
                            obj.is_read = True
                            obj.save(update_fields=['is_read'])
                        else:
                            obj.delete()
                        self.assertEqual(cache.get('last_db_change_time'), 'committed-marker')
                        raise RuntimeError('rollback')
                self.assertFalse(MessageCenterTargetUser.objects.get(pk=relation.pk).is_read)
                self.assertEqual(cache.get('last_db_change_time'), 'committed-marker')
        relation.is_read = True
        relation.save()
        self.assertNotEqual(cache.get('last_db_change_time'), 'committed-marker')


class SessionGateTests(TransactionTestCase):
    @override_settings(DEBUG=True)
    def test_debug_session_must_change_denies_protected_api(self):
        user = Users.objects.create(username='session', is_superuser=True, pwd_change_count=0)
        user.set_password(PASSWORD)
        user.save()
        client = APIClient()
        self.assertTrue(client.login(username=user.username, password=PASSWORD))
        response = client.get('/api/system/dept/')
        self.assertEqual(response.status_code, 403)
        self.assertIn('Password change required', str(response.data))
        self.assertEqual(response.wsgi_request.user.pk, user.pk)
        self.assertFalse(AuthSession.objects.exists())
        self.assertEqual(client.get('/api/system/user/user_info/').status_code, 200)
        Users.objects.filter(pk=user.pk).update(pwd_change_count=1)
        self.assertEqual(client.get('/api/system/dept/').status_code, 200)


class PasswordPolicyMatrixTests(TransactionTestCase):
    def setUp(self):
        self.admin = Users.objects.create(username='policy-admin', is_superuser=True, pwd_change_count=1)
        self.admin.set_password(PASSWORD)
        self.admin.save()
        self.user = Users.objects.create(username='UniqueAttributeExample2026', pwd_change_count=1)
        self.user.set_password(PASSWORD)
        self.user.save()
        self.tokens = AuthService.issue(self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def snapshot(self):
        self.user.refresh_from_db()
        return (self.user.password, self.user.credential_version, self.user.pwd_change_count,
                list(AuthSession.objects.filter(user=self.user).values('sid', 'current_refresh_jti', 'revoked_at', 'expires_at')))

    def matrix(self, operation):
        cases = [('Tiny!9', 'too_short'), ('password1234', 'too_common'),
                 ('92746183058274619305', 'entirely_numeric'),
                 (self.user.username, 'too_similar')]
        for password, code in cases:
            with self.subTest(operation=operation, validator=code):
                validators = dict(zip(('too_similar', 'too_short', 'too_common', 'entirely_numeric'), get_default_password_validators()))
                with self.assertRaises(DjangoValidationError) as expected:
                    validators[code].validate(password, self.user)
                before = self.snapshot()
                if operation == 'create':
                    response = self.client.post('/api/system/user/', {'username': self.user.username + 'x', 'name': 'New policy user', 'password': password}, format='json')
                elif operation == 'reset':
                    response = self.client.put(f'/api/system/user/{self.user.pk}/reset_password/', {'newPassword': password, 'newPassword2': password}, format='json')
                else:
                    client = APIClient()
                    client.credentials(HTTP_AUTHORIZATION='JWT ' + self.tokens['access'])
                    response = client.put('/api/system/user/change_password/', {'oldPassword': PASSWORD, 'newPassword': password, 'newPassword2': password}, format='json')
                self.assertEqual(response.status_code, 400, response.data)
                self.assertTrue(any(message in str(response.data) for message in expected.exception.messages), response.data)
                self.assertEqual(self.snapshot(), before)
                self.assertFalse(Users.objects.filter(username=self.user.username + 'x').exists())
                client = APIClient()
                client.credentials(HTTP_AUTHORIZATION='JWT ' + self.tokens['access'])
                self.assertEqual(client.get('/api/system/user/user_info/').status_code, 200)

    def test_create_validator_matrix(self):
        self.matrix('create')

    def test_admin_reset_validator_matrix(self):
        self.matrix('reset')

    def test_self_change_validator_matrix(self):
        self.matrix('change')
