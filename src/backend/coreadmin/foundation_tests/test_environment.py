"""No-database startup checks plus one real PostgreSQL ORM smoke test."""
import importlib
import logging
import sys
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache, caches
from django.core.cache.backends.locmem import LocMemCache
from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage, default_storage
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.runner import DiscoverRunner


class EnvironmentTests(SimpleTestCase):
    def test_selected_settings_and_database(self):
        self.assertEqual(settings.SETTINGS_MODULE, "application.settings_test")
        self.assertNotIn("conf.env", sys.modules)
        database = settings.DATABASES["default"]
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        # The runner changes NAME to TEST.NAME while the ORM suite is running.
        self.assertRegex(database["NAME"], r"^(test_)?complims_test_[a-z0-9_]{1,40}$")
        self.assertRegex(database["TEST"]["NAME"], r"^test_complims_test_[a-z0-9_]{1,40}$")

    def test_local_cache_and_storage(self):
        self.assertIsInstance(caches["default"], LocMemCache)
        cache.set("foundation-isolation", "local")
        self.assertEqual(cache.get("foundation-isolation"), "local")
        cache.delete("foundation-isolation")
        self.assertIsInstance(default_storage, InMemoryStorage)
        name = default_storage.save("foundation.txt", ContentFile(b"test only"))
        self.assertEqual(default_storage.open(name).read(), b"test only")
        default_storage.delete(name)
        self.assertEqual(settings.DISPATCH_DB_TYPE, "memory")

    def test_no_file_logging(self):
        self.assertFalse(settings.API_LOG_ENABLE)
        loggers = [logging.getLogger()] + [
            item for item in logging.Logger.manager.loggerDict.values()
            if isinstance(item, logging.Logger)
        ]
        self.assertFalse(any(isinstance(handler, logging.FileHandler)
                             for logger in loggers for handler in logger.handlers))
        self.assertTrue(all(handler["class"] == "logging.NullHandler"
                            for handler in settings.LOGGING["handlers"].values()))

    def test_url_import_never_initializes_business_data(self):
        from application import dispatch
        self.assertFalse(settings.INITIALIZE_ON_URL_IMPORT)
        with patch.object(dispatch, "init_system_config") as config, \
                patch.object(dispatch, "init_dictionary") as dictionary:
            # Always execute the module body, even if Django system checks imported it.
            module = importlib.import_module(settings.ROOT_URLCONF)
            module = importlib.reload(module)
            self.assertTrue(module.urlpatterns)
        config.assert_not_called()
        dictionary.assert_not_called()

    def test_targeted_discovery_excludes_legacy_script(self):
        suite = DiscoverRunner(verbosity=0).build_suite(["coreadmin.foundation_tests"])
        def ids(tests):
            for test in tests:
                if hasattr(test, "id"):
                    yield test.id()
                else:
                    yield from ids(test)
        discovered = list(ids(suite))
        self.assertTrue(discovered)
        self.assertTrue(all(name.startswith("coreadmin.foundation_tests.") for name in discovered))
        self.assertIn(
            "coreadmin.foundation_tests.test_environment.PostgreSQLSmokeTests.test_migrated_database_supports_orm",
            discovered,
        )
        self.assertNotIn("coreadmin.system.tests", sys.modules)


class PostgreSQLSmokeTests(TestCase):
    def test_migrated_database_supports_orm(self):
        from coreadmin.system.models import Role
        self.assertEqual(connection.vendor, "postgresql")
        self.assertEqual(connection.settings_dict["NAME"],
                         settings.DATABASES["default"]["TEST"]["NAME"])
        role = Role.objects.create(name="Foundation test", key="foundation_test")
        self.assertEqual(Role.objects.get(pk=role.pk).key, "foundation_test")
