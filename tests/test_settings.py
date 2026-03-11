import os

from arches_lingo.settings import *

PACKAGE_NAME = "arches_lingo"

PROJECT_TEST_ROOT = os.path.dirname(__file__)
MEDIA_ROOT = os.path.join(PROJECT_TEST_ROOT, "data")

BUSINESS_DATA_FILES = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

DATABASES = {
    "default": {
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "HOST": "localhost",
        "NAME": "arches_lingo",
        "OPTIONS": {
            "options": "-c cursor_tuple_fraction=1",
        },
        "PASSWORD": "postgis",
        "PORT": "5432",
        "POSTGIS_TEMPLATE": "template_postgis",
        "TEST": {"CHARSET": None, "COLLATION": None, "MIRROR": None, "NAME": None},
        "TIME_ZONE": None,
        "USER": "postgres",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
    "lingo": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "user_permission": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        "LOCATION": "user_permission_cache",
    },
}

LOGGING["loggers"]["arches"]["level"] = "ERROR"

ELASTICSEARCH_PREFIX = "test"

TEST_RUNNER = "arches.test.runner.ArchesTestRunner"
SILENCED_SYSTEM_CHECKS.append(
    "arches.W001",  # Cache backend does not support rate-limiting
)
SILENCED_SYSTEM_CHECKS.append(
    "arches.E001",  # Cache backend does not support rate-limiting (error level)
)
SILENCED_SYSTEM_CHECKS.append(
    "arches.E003",  # Incompatible arches requirement
)

ELASTICSEARCH_HOSTS = [
    {"scheme": "http", "host": "localhost", "port": ELASTICSEARCH_HTTP_PORT}
]
