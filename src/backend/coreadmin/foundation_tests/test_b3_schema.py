"""PostgreSQL constraints and historical preflight, without repair."""
from django.apps import apps
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from coreadmin.system.models import (Users, Role, Dept, Menu, MenuButton,
    RoleMenuPermission, RoleMenuButtonPermission, MenuField, FieldPermission,
    MessageCenter, MessageCenterTargetUser, SystemConfig, AuthSession)
from coreadmin.system.migrations._b3_preflight import inspect_data
from django.utils import timezone


class ConstraintTests(TransactionTestCase):
    def setUp(self):
        self.role = Role.objects.create(name='role', key='role')
        self.menu = Menu.objects.create(name='menu')
        self.button = MenuButton.objects.create(menu=self.menu, name='button', value='button', api='/')
        self.field = MenuField.objects.create(menu=self.menu, model='Users', field_name='name', title='name')
        self.user = Users.objects.create(username='user')
        self.message = MessageCenter.objects.create(title='message', content='text')

    def rejected(self, write):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                write()
                connection.check_constraints()

    def test_duplicate_grants(self):
        for cls, values in [
            (RoleMenuPermission, dict(role=self.role, menu=self.menu)),
            (RoleMenuButtonPermission, dict(role=self.role, menu_button=self.button)),
            (FieldPermission, dict(role=self.role, field=self.field)),
            (MenuField, dict(menu=self.menu, model='Users', field_name='name', title='name')),
            (MessageCenterTargetUser, dict(messagecenter=self.message, users=self.user)),
        ]:
            with self.subTest(model=cls.__name__):
                if cls != MenuField:
                    cls.objects.create(**values)
                self.rejected(lambda: cls.objects.create(**values))

    def test_scope_and_required_button(self):
        self.rejected(lambda: RoleMenuButtonPermission.objects.create(role=self.role))
        self.rejected(lambda: RoleMenuButtonPermission.objects.create(role=self.role, menu_button=self.button, data_range=9))

    def test_root_unique_and_dept_self_parent(self):
        SystemConfig.objects.create(title='root', key='root')
        self.rejected(lambda: SystemConfig.objects.create(title='root2', key='root'))
        dept = Dept.objects.create(name='dept')
        self.rejected(lambda: Dept.objects.filter(pk=dept.pk).update(parent_id=dept.pk))

    def test_all_critical_foreign_keys(self):
        bindings = [(RoleMenuPermission, 'role'), (RoleMenuPermission, 'menu'),
            (RoleMenuButtonPermission, 'role'), (RoleMenuButtonPermission, 'menu_button'),
            (FieldPermission, 'role'), (FieldPermission, 'field'), (MenuField, 'menu'),
            (MenuButton, 'menu'), (Users, 'dept'), (Dept, 'parent'),
            (MessageCenterTargetUser, 'users'), (MessageCenterTargetUser, 'messagecenter'),
            (SystemConfig, 'parent'), (AuthSession, 'user')]
        RoleMenuPermission.objects.create(role=self.role, menu=self.menu)
        RoleMenuButtonPermission.objects.create(role=self.role, menu_button=self.button)
        FieldPermission.objects.create(role=self.role, field=self.field)
        Dept.objects.create(name='dept')
        SystemConfig.objects.create(title='config', key='config')
        MessageCenterTargetUser.objects.create(users=self.user, messagecenter=self.message)
        AuthSession.objects.create(user=self.user, current_refresh_jti='test', expires_at=timezone.now())
        for cls, name in bindings:
            with self.subTest(model=cls.__name__, field=name):
                self.rejected(lambda: cls.objects.update(**{name + '_id': 999999}))
        for owner, name in [(Users, 'role'), (RoleMenuButtonPermission, 'dept')]:
            through = owner._meta.get_field(name).remote_field.through
            fields = [f.attname for f in through._meta.fields if f.many_to_one]
            self.rejected(lambda: through.objects.create(**{f: 999999 for f in fields}))

    def test_preflight_clean(self):
        self.assertEqual(inspect_data(apps, 'default'), {})


class MigrationTests(TransactionTestCase):
    """Exercise the actual historical graph in the disposable test database."""
    def setUp(self):
        self.old = [('system', '0001_initial')]
        self.new = [('system', '0002_b3_integrity_auth')]
        executor = MigrationExecutor(connection)
        executor.migrate(self.old)
        self.old_apps = executor.loader.project_state(self.old).apps

    def tearDown(self):
        # Tests remove their deliberately dirty records before upgrading.
        MigrationExecutor(connection).migrate(self.new)
        super().tearDown()

    def test_clean_old_data_upgrade_preserves_unknown_credentials(self):
        user = self.old_apps.get_model('system', 'Users').objects.create(username='historical', password='')
        MigrationExecutor(connection).migrate(self.new)
        self.assertEqual(Users.objects.get(pk=user.pk).credential_version, 'LEGACY_UNKNOWN')
        self.assertEqual(Users.objects.get(pk=user.pk).password, '')

    def test_dirty_old_data_fails_without_deleting_or_guessing(self):
        RoleOld = self.old_apps.get_model('system', 'Role')
        GrantOld = self.old_apps.get_model('system', 'RoleMenuButtonPermission')
        role = RoleOld.objects.create(name='dirty', key='dirty')
        row = GrantOld.objects.create(role=role, menu_button_id=None)
        try:
            with self.assertRaisesRegex(RuntimeError, 'Data Cleanup Task'):
                MigrationExecutor(connection).migrate(self.new)
            self.assertTrue(GrantOld.objects.filter(pk=row.pk, menu_button_id=None).exists())
        finally:
            GrantOld.objects.filter(pk=row.pk).delete()
