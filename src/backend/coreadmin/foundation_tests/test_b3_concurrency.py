"""Concurrent commands use independent PostgreSQL connections and a common start."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import AuthenticationFailed
from coreadmin.system.models import Users, Role, Menu, MenuButton, Dept, RoleMenuPermission, RoleMenuButtonPermission, SystemConfig, AuthSession
from coreadmin.system.services.auth import AuthService
from coreadmin.system.services.config import ConfigService

PASSWORD = 'Concurrent-valid-password-2026!'


class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.admin=Users.objects.create(username='admin',is_superuser=True,pwd_change_count=1)
        self.admin.set_password(PASSWORD);self.admin.save()
        self.role=Role.objects.create(name='role',key='role')
        self.menu=Menu.objects.create(name='menu')
        self.other=Menu.objects.create(name='other')
        self.dept=Dept.objects.create(name='a')
        self.second=Dept.objects.create(name='b')

    def race(self, *commands):
        barrier=Barrier(len(commands))
        def run(command):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return command()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(commands)) as pool:
            futures=[pool.submit(run,c) for c in commands]
            return [f.result(timeout=30) for f in futures]

    def request(self, method, path, data):
        client=APIClient();client.force_authenticate(Users.objects.get(pk=self.admin.pk))
        response=getattr(client,method)(path,data,format='json')
        return response.status_code

    def test_grant_replacement_is_one_complete_set(self):
        path='/api/system/role_menu_permission/save_auth/'
        results=self.race(
            lambda:self.request('post',path,{'role':self.role.pk,'menu':[self.menu.pk]}),
            lambda:self.request('post',path,{'role':self.role.pk,'menu':[self.other.pk]}))
        self.assertEqual(results,[200,200])
        final=set(RoleMenuPermission.objects.filter(role=self.role).values_list('menu_id',flat=True))
        self.assertIn(final,[{self.menu.pk},{self.other.pk}])

    def test_custom_scope_and_departments_are_one_command(self):
        button=MenuButton.objects.create(menu=self.menu,name='button',value='button',api='/')
        grant=RoleMenuButtonPermission.objects.create(role=self.role,menu_button=button,data_range=4)
        path='/api/system/role_menu_button_permission/set_role_menu_btn_data_range/'
        results=self.race(
            lambda:self.request('put',path,{'role_menu_btn_perm_id':grant.pk,'data_range':4,'dept':[self.dept.pk]}),
            lambda:self.request('put',path,{'role_menu_btn_perm_id':grant.pk,'data_range':3,'dept':[]}))
        self.assertEqual(results,[200,200]);grant.refresh_from_db()
        self.assertIn((grant.data_range,tuple(grant.dept.values_list('pk',flat=True))),[(4,(self.dept.pk,)),(3,())])

    def test_config_batches_do_not_interleave(self):
        root=SystemConfig.objects.create(title='root',key='root')
        rows=[SystemConfig.objects.create(title=k,key=k,parent=root,value='old') for k in ('a','b')]
        def save(value):
            ConfigService.save_batch([dict(id=o.pk,title=o.title,key=o.key,parent=root.pk,value=value) for o in rows])
        self.race(lambda:save('first'),lambda:save('second'))
        values=set(SystemConfig.objects.filter(pk__in=[o.pk for o in rows]).values_list('value',flat=True))
        self.assertIn(values,[{'first'},{'second'}])

    def test_refresh_exactly_one_winner(self):
        pair=AuthService.issue(self.admin)
        def refresh():
            try:return (200,AuthService.refresh(pair['refresh']))
            except AuthenticationFailed:return (401,None)
        results=self.race(refresh,refresh)
        self.assertEqual(sorted(r[0] for r in results),[200,401])
        winner=next(r[1] for r in results if r[0]==200)
        client=APIClient();client.credentials(HTTP_AUTHORIZATION='JWT '+winner['access'])
        self.assertEqual(client.get('/api/system/user/user_info/').status_code,200)
        self.assertIn('access',AuthService.refresh(winner['refresh']))

    def test_password_reset_vs_refresh_leaves_no_old_session(self):
        pair=AuthService.issue(self.admin)
        def refresh():
            try:return AuthService.refresh(pair['refresh'])
            except AuthenticationFailed:return None
        results=self.race(refresh,lambda:AuthService.reset_password(self.admin.pk,PASSWORD+'new',PASSWORD+'new'))
        self.assertFalse(AuthSession.objects.filter(user=self.admin,revoked_at__isnull=True).exists())
        client=APIClient()
        for tokens in [pair,results[0]]:
            if tokens:
                client.credentials(HTTP_AUTHORIZATION='JWT '+tokens['access'])
                self.assertEqual(client.get('/api/system/user/user_info/').status_code,401)
