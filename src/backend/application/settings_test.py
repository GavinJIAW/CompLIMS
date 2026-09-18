"""Isolated PostgreSQL settings. Select with --settings=application.settings_test.

Required environment variables (no defaults): COMPLIMS_TEST_DB_NAME, _USER,
_PASSWORD, _HOST, _PORT (each uses the full COMPLIMS_TEST_DB_ prefix).
NAME must match complims_test_[a-z0-9_]{1,40}. Provision a dedicated PostgreSQL
role/connection database, isolated from development/production. Django creates
and destroys test_<NAME>; the role needs test-database creation permissions.
The PostgreSQL backend may connect to its postgres maintenance database for
CREATE DATABASE; neither that database nor NAME is the migration/test target.
Never grant this role access to development/production data.

Run from src/backend in dvadmin3_env, after explicitly providing credentials:
  python -B manage.py test coreadmin.foundation_tests --settings=application.settings_test
No-database bootstrap checks (no credentials needed):
  python -B -m unittest coreadmin.foundation_tests.test_settings
Use the targeted package, not unlabelled discovery of legacy system/tests.py.
"""
import os

from django.core.exceptions import ImproperlyConfigured

# Prevent accidental direct import from silently loading development settings.
if os.environ.get("DJANGO_SETTINGS_MODULE") != "application.settings_test":
    raise ImproperlyConfigured("Select application.settings_test as DJANGO_SETTINGS_MODULE")

from application.settings import *  # noqa: F403,E402 - guarded before conf.env import
from application.settings import _ISOLATED_TEST

if not _ISOLATED_TEST:
    raise ImproperlyConfigured("Development settings were already loaded; start a fresh test process")

DATABASES["default"]["TEST"] = {"NAME": "test_" + DATABASES["default"]["NAME"]}
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
INITIALIZE_ON_URL_IMPORT = False
DISPATCH_DB_TYPE = "memory"
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "complims-foundation-tests",
}}
# In-memory storage avoids project files and external storage credentials.
DEFAULT_FILE_STORAGE = "django.core.files.storage.InMemoryStorage"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
API_LOG_ENABLE = False
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
    "loggers": {"django": {"handlers": ["null"], "propagate": False}},
}


# Reserve an isolated temporary path without I/O during settings import.
# The service creates it on first upload; startup-only tests remain side-effect free.
import atexit
import shutil
import uuid
MANAGED_FILE_ROOT = str(Path(os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp')
    / ('complims-managed-test-' + uuid.uuid4().hex))
MANAGED_FILE_MAX_SIZE_BYTES = 104857600


def _cleanup_managed_test_storage(root=MANAGED_FILE_ROOT):
    if Path(root).is_dir():
        shutil.rmtree(root)


atexit.register(_cleanup_managed_test_storage)
