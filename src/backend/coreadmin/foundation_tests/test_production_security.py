"""Fresh-process configuration probes: stub credentials, no network or file writes."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

from coreadmin.foundation_tests.test_settings import GUARDS


BOOTSTRAP = r'''
from types import ModuleType
from unittest.mock import patch
stub = ModuleType('conf.env')
values = {
    'DATABASE_ENGINE': 'django.db.backends.postgresql',
    'DATABASE_NAME': 'unusable_probe', 'DATABASE_USER': 'probe',
    'DATABASE_PASSWORD': 'probe', 'DATABASE_HOST': 'invalid.example', 'DATABASE_PORT': '5432',
    'DJANGO_SECRET_KEY': 'TEST-ONLY-Django-probe-' * 4,
    'JWT_SIGNING_KEY': 'TEST-ONLY-JWT-independent-' * 4,
    'ALLOWED_HOSTS': ['app.example.test'], 'INITIALIZE_ON_URL_IMPORT': False,
}
values.update(OVERRIDES)
for key, value in values.items():
    if value is not None:
        setattr(stub, key, value)
def stub_import(name, *args, **kwargs):
    return stub if name == 'conf.env' else guarded_import(name, *args, **kwargs)
from django.core.exceptions import ImproperlyConfigured
with patch('builtins.__import__', stub_import), patch('os.makedirs'):
    try:
        import application.settings as configuration
    except ImproperlyConfigured:
        assert EXPECT_FAILURE
    else:
        assert not EXPECT_FAILURE, 'Unsafe configuration accepted'
        configuration.LOGGING_CONFIG = None
        import django
        django.setup()
        from django.conf import settings
        BODY
assert not violations, violations
'''


class ProductionSecurityTests(unittest.TestCase):
    def probe(self, body='pass', overrides=None, environment=None, fails=False):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('DJANGO_', 'COMPLIMS_TEST_DB_', 'JWT_', 'CORS_', 'CSRF_'))}
        env.update(DJANGO_SETTINGS_MODULE='application.settings', PYTHONDONTWRITEBYTECODE='1')
        env.update(environment or {})
        code = GUARDS + '\nOVERRIDES = ' + repr(overrides or {}) + '\nEXPECT_FAILURE = ' + repr(fails) + '\n'
        code += BOOTSTRAP.replace('        BODY', '\n'.join('        ' + line for line in body.splitlines()))
        result = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                                cwd=Path(__file__).resolve().parents[2], capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, 'Production probe failed (output withheld)')
        return result.stdout.decode('utf-8')

    def test_debug_defaults_to_false(self):
        self.probe('assert settings.DEBUG is False')

    def test_debug_strict_environment_parsing(self):
        for value in ('maybe', 'debug', '2', ''):
            with self.subTest(value=value):
                self.probe(environment={'DJANGO_DEBUG': value}, fails=True)
        for value in ('1', 'TRUE', 'yes', 'On', '0', 'FALSE', 'no', 'off'):
            with self.subTest(value=value):
                expected = value.lower() in ('1', 'true', 'yes', 'on')
                self.probe(f'assert settings.DEBUG is {expected}', environment={'DJANGO_DEBUG': value})

    def test_production_rejects_missing_or_wildcard_hosts(self):
        for value in (None, [], ['*']):
            with self.subTest(value=value):
                self.probe(overrides={'DEBUG': False, 'ALLOWED_HOSTS': value}, fails=True)

    def test_production_rejects_cors_allow_all_aliases_and_wildcards(self):
        for overrides in ({'CORS_ALLOW_ALL_ORIGINS': True}, {'CORS_ORIGIN_ALLOW_ALL': True},
                          {'CORS_ALLOW_ALL_ORIGINS': False, 'CORS_ORIGIN_ALLOW_ALL': True},
                          {'CORS_ALLOWED_ORIGINS': ['*']}, {'CORS_ORIGIN_WHITELIST': ['*']},
                          {'CSRF_TRUSTED_ORIGINS': ['*']}):
            with self.subTest(keys=list(overrides)):
                self.probe(overrides={'DEBUG': False, **overrides}, fails=True)

    def test_production_effective_cors_and_cookies(self):
        self.probe('''
from corsheaders.conf import conf
from corsheaders.middleware import CorsMiddleware
from django.test import RequestFactory
from django.http import HttpResponse
assert conf.CORS_ALLOW_ALL_ORIGINS is False
assert list(conf.CORS_ALLOWED_ORIGINS) == ['https://ui.example.test']
assert settings.ALLOWED_HOSTS == ['app.example.test', 'api.example.test']
assert settings.CSRF_TRUSTED_ORIGINS == ['https://ui.example.test']
assert settings.SESSION_COOKIE_SECURE is True and settings.CSRF_COOKIE_SECURE is True
middleware = CorsMiddleware(lambda request: HttpResponse('ok'))
for origin, allowed in [('https://ui.example.test', True), ('https://evil.example.test', False)]:
    response = middleware(RequestFactory().get('/', HTTP_ORIGIN=origin))
    assert ('Access-Control-Allow-Origin' in response) is allowed
''', overrides={'DEBUG': False, 'CORS_ALLOW_CREDENTIALS': True}, environment={
            'DJANGO_ALLOWED_HOSTS': 'app.example.test,api.example.test',
            'DJANGO_CORS_ALLOWED_ORIGINS': 'https://ui.example.test',
            'DJANGO_CSRF_TRUSTED_ORIGINS': 'https://ui.example.test'})

    def test_production_same_origin_defaults(self):
        self.probe('''
from corsheaders.conf import conf
assert not conf.CORS_ALLOW_ALL_ORIGINS
assert not conf.CORS_ALLOWED_ORIGINS
assert settings.CSRF_TRUSTED_ORIGINS == []
''', overrides={'DEBUG': False})

    def test_production_jwt_rejects_missing_short_or_coupled_keys(self):
        for key in (None, '', 'short', 'TEST-ONLY-Django-probe-' * 4):
            self.probe(overrides={'DEBUG': False, 'JWT_SIGNING_KEY': key}, fails=True)

    def test_jwt_cryptographic_separation_and_environment_priority(self):
        self.probe('''
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenBackendError
key = settings.SIMPLE_JWT['SIGNING_KEY']
assert key == os.environ['JWT_SIGNING_KEY']
backend = TokenBackend(algorithm='HS256', signing_key=key)
token = backend.encode({'probe': 'test only'})
assert backend.decode(token)['probe'] == 'test only'
try:
    TokenBackend(algorithm='HS256', signing_key=settings.SECRET_KEY).decode(token)
except TokenBackendError:
    pass
else:
    raise AssertionError('Django key verified JWT')
''', overrides={'DEBUG': False}, environment={'JWT_SIGNING_KEY': 'TEST-ONLY-environment-JWT-' * 4})

    def test_development_fallback_only(self):
        self.probe('''
assert settings.SIMPLE_JWT['SIGNING_KEY'] == settings.SECRET_KEY
assert settings.CORS_ALLOW_ALL_ORIGINS is True
assert settings.SESSION_COOKIE_SECURE is False
''', overrides={'DEBUG': True, 'JWT_SIGNING_KEY': None})

    def test_origin_and_environment_guards(self):
        for environment in ({'DJANGO_ALLOWED_HOSTS': ''}, {'DJANGO_ALLOWED_HOSTS': '*'},
                            {'DJANGO_CORS_ALLOW_ALL_ORIGINS': 'true'},
                            {'DJANGO_CORS_ALLOWED_ORIGINS': '*'},
                            {'DJANGO_CSRF_TRUSTED_ORIGINS': '*'}, {'JWT_SIGNING_KEY': ''}):
            with self.subTest(keys=list(environment)):
                self.probe(overrides={'DEBUG': False}, environment=environment, fails=True)
        for value in ('https://*.example.test', 'https://example.test/path', 'not-an-origin'):
            self.probe(overrides={'DEBUG': False, 'CORS_ALLOWED_ORIGINS': [value]}, fails=True)
        self.probe(overrides={'DEBUG': False, 'CORS_ORIGIN_REGEX_WHITELIST': ['.*']}, fails=True)

    def test_legacy_exact_origin_configuration_is_effective(self):
        self.probe('''
from corsheaders.conf import conf
assert list(conf.CORS_ALLOWED_ORIGINS) == ['https://legacy.example.test']
assert not conf.CORS_ALLOW_ALL_ORIGINS
''', overrides={'DEBUG': False, 'CORS_ORIGIN_WHITELIST': ['https://legacy.example.test']})

    def test_missing_django_secret_still_fails(self):
        self.probe('pass', overrides={'DEBUG': False, 'DJANGO_SECRET_KEY': None}, fails=True)

    def test_urls_in_fresh_production_and_development_processes(self):
        for debug in (False, True):
            with self.subTest(debug=debug):
                self.probe('''
from django.urls import resolve, Resolver404
for path in ('/api/swagger.json', '/api/swagger.yaml', '/api/swagger/', '/api/redoc/', '/api/api-auth/login/', '/apiLogin/'):
    try:
        resolve(path)
    except Resolver404:
        assert not settings.DEBUG
    else:
        assert settings.DEBUG
for path in ('/api/login/', '/api/captcha/', '/api/token/refresh/', '/api/init/settings/'):
    resolve(path)
''', overrides={'DEBUG': debug})

    def test_isolated_jwt_ignores_deployment_environment(self):
        # Reuse the original B1A guards without a stub: real conf.env import is forbidden.
        from coreadmin.foundation_tests.test_settings import SettingsIsolationTests
        SettingsIsolationTests().run_probe('''
import django
django.setup()
from django.conf import settings
assert settings.SIMPLE_JWT['SIGNING_KEY'] != os.environ['JWT_SIGNING_KEY']
assert settings.SIMPLE_JWT['SIGNING_KEY'] != settings.SECRET_KEY
assert 'conf.env' not in sys.modules
''', {'JWT_SIGNING_KEY': 'TEST-ONLY-deployment-key-' * 4, 'DJANGO_DEBUG': 'maybe'})
