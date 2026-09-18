import hashlib
from unittest.mock import patch
from django.contrib.auth.hashers import make_password, check_password
from django.test import TransactionTestCase
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from coreadmin.system.models import Users, Role, AuthSession, Menu, MenuButton, RoleMenuButtonPermission
from coreadmin.system.services.auth import AuthService

PASSWORD = 'A-valid-probe-password-2026!'
NEW = 'Another-valid-password-2026!'


class AuthTests(TransactionTestCase):
    def setUp(self):
        self.user = Users.objects.create(username='actor', is_active=True, pwd_change_count=1)
        self.user.set_password(PASSWORD); self.user.save()
        self.admin = Users.objects.create(username='admin', is_superuser=True, pwd_change_count=1)
        self.admin.set_password(PASSWORD); self.admin.save()

    def login(self, user=None, password=PASSWORD):
        return APIClient().post('/api/login/', {'username': (user or self.user).username, 'password': password}, format='json')

    def authenticated_client(self, tokens):
        c=APIClient();c.credentials(HTTP_AUTHORIZATION='JWT '+tokens['access']);return c

    def refresh(self, tokens):
        return APIClient().post('/api/token/refresh/', {'refresh':tokens['refresh']}, format='json')

    def pair(self, user=None):
        return self.login(user).data['data']

    def assert_revoked(self, tokens):
        self.assertEqual(self.authenticated_client(tokens).get('/api/system/user/user_info/').status_code,401)
        self.assertEqual(self.refresh(tokens).status_code,401)

    def test_native_login_sid_and_legacy_token_denied(self):
        tokens=self.pair()
        self.assertEqual(AccessToken(tokens['access'])['sid'],RefreshToken(tokens['refresh'])['sid'])
        self.assertEqual(self.authenticated_client(tokens).get('/api/system/user/user_info/').status_code,200)
        legacy={'access':str(RefreshToken.for_user(self.user).access_token),'refresh':str(RefreshToken.for_user(self.user))}
        self.assert_revoked(legacy)

    def test_single_and_double_legacy_upgrade(self):
        for rounds in [1,2]:
            raw=PASSWORD
            for _ in range(rounds):raw=hashlib.md5(raw.encode()).hexdigest()
            self.user.password=make_password(raw);self.user.credential_version='LEGACY_UNKNOWN';self.user.save()
            response=self.login()
            self.assertEqual(response.status_code,200)
            self.user.refresh_from_db()
            self.assertEqual(self.user.credential_version,'DJANGO_NATIVE')
            self.assertTrue(check_password(PASSWORD,self.user.password))

    def test_ambiguous_and_empty_require_reset_without_tokens(self):
        for encoded in [make_password(PASSWORD),'']:
            self.user.password=encoded;self.user.credential_version='LEGACY_UNKNOWN';self.user.save()
            before=AuthSession.objects.count()
            response=self.login()
            self.assertEqual(response.status_code,401)
            self.assertIn('RESET REQUIRED',str(response.data))
            self.assertEqual(AuthSession.objects.count(),before)

    def test_native_digest_is_not_accepted(self):
        self.assertEqual(self.login(password=hashlib.md5(PASSWORD.encode()).hexdigest()).status_code,401)

    def test_logout_only_current_session(self):
        first,second=self.pair(),self.pair()
        self.assertEqual(self.authenticated_client(first).post('/api/logout/',{},format='json').status_code,200)
        self.assert_revoked(first)
        self.assertEqual(self.authenticated_client(second).get('/api/system/user/user_info/').status_code,200)

    def test_refresh_single_use_and_successor(self):
        tokens=self.pair()
        first=self.refresh(tokens);second=self.refresh(tokens)
        self.assertEqual(first.status_code,200);self.assertEqual(second.status_code,401)
        self.assertEqual(self.authenticated_client(first.data).get('/api/system/user/user_info/').status_code,200)
        self.assertEqual(self.refresh(first.data).status_code,200)

    def test_change_revokes_all_sessions(self):
        tokens,other=self.pair(),self.pair()
        response=self.authenticated_client(tokens).put('/api/system/user/change_password/',
            {'oldPassword':PASSWORD,'newPassword':NEW,'newPassword2':NEW},format='json')
        self.assertEqual(response.status_code,200)
        self.assert_revoked(tokens);self.assert_revoked(other)
        self.assertEqual(self.login(password=NEW).status_code,200)

    def test_admin_reset_and_shared_default_shutdown(self):
        tokens=self.pair();admin=self.authenticated_client(self.pair(self.admin))
        response=admin.put(f'/api/system/user/{self.user.pk}/reset_password/',
            {'newPassword':NEW,'newPassword2':NEW},format='json')
        self.assertEqual(response.status_code,200);self.assert_revoked(tokens)
        self.user.refresh_from_db();self.assertEqual(self.user.pwd_change_count,0)
        self.assertEqual(admin.put(f'/api/system/user/{self.user.pk}/reset_to_default_password/',{},format='json').status_code,405)

    def test_disable_service_and_direct_gate(self):
        tokens=self.pair()
        admin=self.authenticated_client(self.pair(self.admin))
        self.assertEqual(admin.patch(f'/api/system/user/{self.user.pk}/',{'is_active':False},format='json').status_code,200)
        self.assert_revoked(tokens)
        self.assertTrue(AuthSession.objects.filter(user=self.user,revoked_at__isnull=False).exists())
        self.user.is_active=True;self.user.save()
        fresh=self.pair()
        Users.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assert_revoked(fresh)

    def test_must_change_allowlist(self):
        self.user.pwd_change_count=0;self.user.save()
        tokens=self.pair();client=self.authenticated_client(tokens)
        self.assertEqual(client.get('/api/system/user/user_info/').status_code,200)
        for path in ['/api/system/user/','/api/system/message_center/get_self_receive/',
                     '/api/system/menu/web_router/','/api/init/dictionary/']:
            self.assertEqual(client.get(path).status_code,403,path)
        successor=self.refresh(tokens)
        self.assertEqual(successor.status_code,200)
        self.assertEqual(self.authenticated_client(successor.data).get('/api/system/menu/web_router/').status_code,403)
        self.assertEqual(client.put('/api/system/user/change_password/',
            {'oldPassword':PASSWORD,'newPassword':NEW,'newPassword2':NEW},format='json').status_code,200)

    def test_role_disable_and_revoke_preserve_authentication(self):
        role=Role.objects.create(name='role',key='role');self.user.role.add(role)
        menu=Menu.objects.create(name='menu')
        button=MenuButton.objects.create(menu=menu,name='read',value='dept:Search',api='/')
        grant=RoleMenuButtonPermission.objects.create(role=role,menu_button=button,data_range=3)
        tokens=self.pair();client=self.authenticated_client(tokens)
        self.assertEqual(client.get('/api/system/dept/').status_code,200)
        role.status=False;role.save()
        self.assertEqual(client.get('/api/system/dept/').status_code,403)
        self.assertEqual(client.get('/api/system/user/user_info/').status_code,200)
        role.status=True;role.save();grant.delete()
        self.assertEqual(client.get('/api/system/dept/').status_code,403)
        self.assertEqual(self.refresh(tokens).status_code,200)

    def test_password_policy_and_required_create(self):
        admin=self.authenticated_client(self.pair(self.admin))
        self.assertEqual(admin.post('/api/system/user/',{'username':'new'},format='json').status_code,400)
        for password in ['short','123456789012345']:
            response=admin.post('/api/system/user/',{'username':'new','password':password},format='json')
            self.assertEqual(response.status_code,400)
        response=admin.post('/api/system/user/',{'username':'new','name':'New User','password':NEW},format='json')
        self.assertEqual(response.status_code,200,response.data)
        user=Users.objects.get(username='new')
        self.assertEqual(user.pwd_change_count,0);self.assertEqual(user.credential_version,'DJANGO_NATIVE')
        self.assertTrue(check_password(NEW,user.password))

    def test_operational_log_failure_does_not_fail_login_or_increment(self):
        self.user.login_error_count=3;self.user.save()
        with patch('coreadmin.system.views.login.save_login_log',side_effect=RuntimeError('log failed')):
            response=self.login()
        self.assertEqual(response.status_code,200)
        self.user.refresh_from_db();self.assertEqual(self.user.login_error_count,0)
        self.assertTrue(self.user.is_active)

    def test_only_credential_failure_increments(self):
        self.assertEqual(self.login(password='wrong').status_code,401)
        self.user.refresh_from_db();self.assertEqual(self.user.login_error_count,1)
        with patch('coreadmin.system.views.login.captcha_enabled',return_value=True):
            self.assertEqual(self.login().status_code,400)
        self.user.refresh_from_db();self.assertEqual(self.user.login_error_count,1)
        with patch('coreadmin.system.services.auth.verify_credential',side_effect=RuntimeError('internal')):
            self.assertEqual(self.login().status_code,500)
        self.user.refresh_from_db();self.assertEqual(self.user.login_error_count,1)

    def test_session_owner_expiry_and_missing(self):
        tokens=self.pair()
        session=AuthSession.objects.get(sid=AccessToken(tokens['access'])['sid'])
        session.user=self.admin;session.save();self.assert_revoked(tokens)
        session.user=self.user;session.expires_at=timezone.now()-timedelta(seconds=1);session.save()
        self.assert_revoked(tokens)
        session.delete();self.assert_revoked(tokens)

    def test_superuser_role_failure_rolls_back_user(self):
        Role.objects.create(name='管理员',key='required')
        with patch.object(type(self.user.role),'add',side_effect=RuntimeError('role failure')):
            with self.assertRaises(RuntimeError):
                Users.objects.create_superuser('newadmin',password=PASSWORD)
        self.assertFalse(Users.objects.filter(username='newadmin').exists())

    def test_form_blank_captcha_key_without_captcha_requirement(self):
        response=APIClient().post('/api/login/',{'username':self.user.username,'password':PASSWORD,'captchaKey':'','captcha':''},format='json')
        self.assertEqual(response.status_code,200)

    def test_wrong_old_password_no_changes(self):
        tokens=self.pair()
        before=self.user.password
        response=self.authenticated_client(tokens).put('/api/system/user/change_password/',
            {'oldPassword':'wrong','newPassword':NEW,'newPassword2':NEW},format='json')
        self.assertEqual(response.status_code,400)
        self.user.refresh_from_db();self.assertEqual(self.user.password,before)
        self.assertEqual(self.refresh(tokens).status_code,200)

    def test_revocation_failure_rolls_back_password(self):
        tokens=self.pair();before=self.user.password
        with patch.object(AuthService,'revoke_all_locked',side_effect=RuntimeError('injected')):
            with self.assertRaises(RuntimeError):
                AuthService.reset_password(self.user.pk,NEW,NEW)
        self.user.refresh_from_db();self.assertEqual(self.user.password,before)
        self.assertEqual(self.refresh(tokens).status_code,200)

    def test_must_change_logout_and_options(self):
        self.user.pwd_change_count=0;self.user.save()
        tokens=self.pair();client=self.authenticated_client(tokens)
        self.assertEqual(client.options('/api/system/dept/').status_code,403)
        self.assertEqual(client.options('/api/init/dictionary/').status_code,403)
        self.assertEqual(client.post('/api/logout/',{},format='json').status_code,200)
        self.assert_revoked(tokens)
