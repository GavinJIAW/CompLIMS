"""Copy to env.py (ignored), then supply local environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_ENGINE = "django.db.backends.postgresql"
DATABASE_NAME = os.environ.get("DATABASE_NAME", "complims")
DATABASE_HOST = os.environ.get("DATABASE_HOST", "127.0.0.1")
DATABASE_PORT = int(os.environ.get("DATABASE_PORT", "5432"))
DATABASE_USER = os.environ.get("DATABASE_USER", "")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "")
DJANGO_SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
# Independent key is recommended even for development; production requires it.
JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY", "")
TABLE_PREFIX = ""
REDIS_DB = 1
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379")
# settings.py strictly parses DJANGO_DEBUG. Missing configuration defaults False.
# For local development explicitly set DJANGO_DEBUG=true (or DEBUG=True here).
# Production: DJANGO_DEBUG=false and DJANGO_ALLOWED_HOSTS must be configured.
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(',')
# Same-origin is the default. Development may explicitly enable allow-all;
# production rejects it. Prefer exact origins in both environments.
CORS_ALLOW_ALL_ORIGINS = os.environ.get("DJANGO_CORS_ALLOW_ALL_ORIGINS", "false")
CORS_ALLOWED_ORIGINS = os.environ.get("DJANGO_CORS_ALLOWED_ORIGINS", "").split(',')
CSRF_TRUSTED_ORIGINS = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(',')
ENABLE_LOGIN_ANALYSIS_LOG = False
LOGIN_NO_CAPTCHA_AUTH = False
COLUMN_EXCLUDE_APPS = []
