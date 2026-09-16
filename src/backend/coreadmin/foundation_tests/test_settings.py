"""Credential-free regression checks in fresh, network/file-write-blocked processes.

These tests never run database setup. Placeholder values only exercise config
validation and SimpleTestCase startup; they are not PostgreSQL credentials.
"""
import os
from pathlib import Path
import subprocess
import sys
import unittest


# Block local env reads, all file writes and socket connections before Django
# imports. Patch the C-extension driver too (it bypasses Python socket hooks).
GUARDS = r"""
import builtins
import os
import sys
violations = []
def forbidden(message):
    violations.append(message)
    raise AssertionError(message)
_original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name == 'conf.env' or (name == 'conf' and 'env' in (kwargs.get('fromlist') or ((args[2] or ()) if len(args) > 2 else ()))):
        forbidden('Development env import attempted')
    return _original_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
def audit(event, args):
    if event == 'open':
        path, mode, flags = args
        if path == os.devnull:
            return  # OS null device is not a filesystem artifact.
        if isinstance(path, (str, bytes)) and os.fsdecode(path).replace(chr(92), '/').endswith('/conf/env.py'):
            forbidden('Development env read attempted')
        if (mode and any(flag in mode for flag in 'wax+')) or (flags and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
            forbidden('File write attempted')
    if event in ('socket.connect', 'socket.getaddrinfo', 'os.mkdir', 'os.remove', 'os.rename', 'os.rmdir'):
        forbidden('External or filesystem side effect attempted: ' + event)
sys.addaudithook(audit)
import psycopg2
def no_database(*args, **kwargs):
    forbidden('Database connection attempted')
psycopg2.connect = no_database
"""


class SettingsIsolationTests(unittest.TestCase):
    def run_probe(self, code, overrides=None):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith('COMPLIMS_TEST_DB_')}
        env.update({
            'DJANGO_SETTINGS_MODULE': 'application.settings_test',
            'PYTHONDONTWRITEBYTECODE': '1',
            'COMPLIMS_TEST_DB_NAME': 'complims_test_config_probe',
            'COMPLIMS_TEST_DB_USER': 'unusable_test_probe',
            'COMPLIMS_TEST_DB_PASSWORD': 'unusable_test_probe',
            'COMPLIMS_TEST_DB_HOST': 'invalid.example',
            'COMPLIMS_TEST_DB_PORT': '5432',
        })
        for key, value in (overrides or {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        result = subprocess.run([sys.executable, '-B', '-c', GUARDS + code + '\nassert not violations, violations'],
                                cwd=Path(__file__).resolve().parents[2],
                                env=env, capture_output=True, text=True, timeout=60)
        # Never echo subprocess output/settings/credentials on failure.
        self.assertEqual(result.returncode, 0, 'Isolated startup probe failed (output withheld)')

    def test_missing_each_required_parameter_fails_closed(self):
        for key in ('NAME', 'USER', 'PASSWORD', 'HOST', 'PORT'):
            with self.subTest(parameter=key):
                self.run_probe("""
from django.core.exceptions import ImproperlyConfigured
try:
    import application.settings_test
except ImproperlyConfigured:
    assert 'conf.env' not in sys.modules
else:
    raise AssertionError('Missing configuration accepted')
""", {'COMPLIMS_TEST_DB_' + key: None})

    def test_unsafe_database_names_and_ports_fail_closed(self):
        for name in ('complims', 'postgres', 'template0', 'template1', 'test_complims',
                     'complims_test_', 'complims_test_../dev'):
            with self.subTest(name=name):
                self.run_probe("""
from django.core.exceptions import ImproperlyConfigured
try:
    import application.settings_test
except ImproperlyConfigured:
    pass
else:
    raise AssertionError('Unsafe database target accepted')
""", {'COMPLIMS_TEST_DB_NAME': name})
        self.run_probe("""
from django.core.exceptions import ImproperlyConfigured
try:
    import application.settings_test
except ImproperlyConfigured:
    pass
else:
    raise AssertionError('Invalid port accepted')
""", {'COMPLIMS_TEST_DB_PORT': '0'})

    def test_startup_and_targeted_no_database_suite(self):
        self.run_probe("""
import django
django.setup()
from django.conf import settings
assert settings.SECRET_KEY != os.environ['DJANGO_SECRET_KEY']
assert 'conf.env' not in sys.modules
from django.test.runner import DiscoverRunner
failures = DiscoverRunner(verbosity=0).run_tests([
    'coreadmin.foundation_tests.test_environment.EnvironmentTests'
])
assert failures == 0
""", {'DJANGO_SECRET_KEY': 'deployment-secret-sentinel-never-use'})

    def test_development_configuration_contract_without_local_env(self):
        self.run_probe("""
from types import ModuleType
from unittest.mock import patch
stub = ModuleType('conf.env')
for key, value in {
    'DATABASE_ENGINE': 'django.db.backends.postgresql',
    'DATABASE_NAME': 'development_stub', 'DATABASE_USER': 'stub',
    'DATABASE_PASSWORD': 'stub', 'DATABASE_HOST': 'invalid.example',
    'DATABASE_PORT': '5432', 'DJANGO_SECRET_KEY': 'local-stub',
    'DEBUG': True, 'ALLOWED_HOSTS': ['localhost'],
}.items():
    setattr(stub, key, value)
def stub_import(name, *args, **kwargs):
    return stub if name == 'conf.env' else guarded_import(name, *args, **kwargs)
# Exercise the development branch with an in-memory substitute, never the real
# ignored file, DB connection or filesystem. Do not configure Django logging.
with patch('builtins.__import__', stub_import), patch('os.makedirs') as mkdir, patch('os.path.exists', return_value=False):
    import application.settings as development
    mkdir.assert_called_once_with(os.path.join(development.BASE_DIR, 'logs'))
assert development.DATABASES['default']['NAME'] == 'development_stub'
assert development.SECRET_KEY == 'environment-stub'
assert development.DEBUG is True
assert development.LOGGING['handlers']['file']['class'] == 'logging.handlers.RotatingFileHandler'
assert getattr(development, 'INITIALIZE_ON_URL_IMPORT', True) is True
""", {'DJANGO_SETTINGS_MODULE': 'application.settings',
      'DJANGO_SECRET_KEY': 'environment-stub'})
