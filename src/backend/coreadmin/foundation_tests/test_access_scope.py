from types import SimpleNamespace

from django.test import TestCase
from unittest.mock import patch

from coreadmin.access.context import AccessContext, SCOPE_PROVIDERS
from coreadmin.access.registry import REGISTRY
from coreadmin.system.models import Dept, Menu, MenuButton, Role, RoleMenuButtonPermission, Users


class ScopePolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = Dept.objects.create(name='A')
        cls.b = Dept.objects.create(name='B')
        cls.child = Dept.objects.create(name='A child', parent=cls.a)
        cls.actor = Users.objects.create(username='actor', dept=cls.a)
        cls.other = Users.objects.create(username='other')
        cls.own = Users.objects.create(username='own', creator=cls.actor, dept_belong_id=cls.b.id)
        cls.same = Users.objects.create(username='same', creator=cls.other, dept_belong_id=cls.a.id)
        cls.sub = Users.objects.create(username='sub', creator=cls.other, dept_belong_id=cls.child.id)
        cls.remote = Users.objects.create(username='remote', creator=cls.other, dept_belong_id=cls.b.id)
        cls.protected = Users.objects.create(username='protected', is_superuser=True)
        cls.menu = Menu.objects.create(name='Users')
        cls.button = MenuButton.objects.create(menu=cls.menu, name='List', value='user:Search', api='/WRONG/', method=3)
        cls.other_button = MenuButton.objects.create(menu=cls.menu, name='Update', value='user:Update', api='/WRONG/', method=0)

    def grant(self, scope, dept=None, button=None, active=True):
        role = Role.objects.create(name='role', key='role-' + str(Role.objects.count()), status=active)
        self.actor.role.add(role)
        grant = RoleMenuButtonPermission.objects.create(role=role, menu_button=button or self.button, data_range=scope)
        if dept:
            grant.dept.add(dept)
        return grant

    def context(self):
        return AccessContext(self.actor, REGISTRY['user', 'list', 'GET'])

    def visible(self):
        return set(self.context().scope(Users.objects.exclude(is_superuser=True)).values_list('id', flat=True))

    def test_self_survives_department_change(self):
        self.grant(0)
        self.assertEqual(self.visible(), {self.own.id})

    def test_department_and_children(self):
        self.grant(1)
        self.assertEqual(self.visible(), {self.same.id, self.sub.id})

    def test_department_only(self):
        self.grant(2)
        self.assertEqual(self.visible(), {self.same.id})

    def test_self_and_department_union(self):
        self.grant(0)
        self.grant(2)
        self.assertEqual(self.visible(), {self.own.id, self.same.id})

    def test_all_union_does_not_expand_envelope(self):
        self.grant(0)
        self.grant(3)
        self.assertEqual(self.visible(), set(Users.objects.exclude(is_superuser=True).values_list('id', flat=True)))
        self.assertNotIn(self.protected.id, self.visible())

    def test_custom_does_not_borrow_other_action_departments(self):
        self.grant(4, self.a)
        self.grant(4, self.b, button=self.other_button)
        self.assertEqual(self.visible(), {self.same.id})

    def test_disabled_role_stops_contributing_on_next_context(self):
        grant = self.grant(3)
        self.assertTrue(self.context().allowed())
        Role.objects.filter(pk=grant.role_id).update(status=False)
        self.assertFalse(self.context().allowed())

    def test_missing_scope_provider_is_empty(self):
        self.grant(3)
        with patch.dict(SCOPE_PROVIDERS, {}, clear=True):
            self.assertEqual(self.visible(), set())

    def test_tuple_contributors_are_object_specific(self):
        a = self.grant(2)
        b = self.grant(4, self.b)
        context = self.context()
        self.assertEqual([g.id for g in context.contributing(self.same)], [a.id])
        self.assertEqual([g.id for g in context.contributing(self.remote)], [b.id])

    def test_no_department_all_five_scopes(self):
        self.actor.dept = None
        for scope, expected in [(0, {self.own.id}), (1, set()), (2, set()),
                                (3, set(Users.objects.exclude(is_superuser=True).values_list('id', flat=True))),
                                (4, {self.own.id, self.remote.id})]:
            with self.subTest(scope=scope):
                self.actor.role.clear()
                self.grant(scope, self.b if scope == 4 else None)
                self.assertEqual(self.visible(), expected)

    def test_role_order_does_not_change_union(self):
        a, b = self.grant(0), self.grant(2)
        before = self.visible()
        Role.objects.filter(pk=a.role_id).update(sort=99)
        Role.objects.filter(pk=b.role_id).update(sort=-1)
        self.assertEqual(self.visible(), before)
