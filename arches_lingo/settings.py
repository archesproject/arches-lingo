"""
Django settings for arches_lingo project.
"""

import json
import os
import sys
import arches
import inspect
import semantic_version
from datetime import datetime, timedelta
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string

try:
    from arches.settings import *
except ImportError:
    pass


def get_env_variable(var_name):
    msg = "Set the %s environment variable"
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = msg % var_name
        raise ImproperlyConfigured(error_msg)


def get_optional_env_variable(var_name, default=None) -> str:
    try:
        return os.environ[var_name]
    except KeyError:
        return default


APP_NAME = "arches_lingo"
SECRETS_MODE = get_optional_env_variable("ARCHES_SECRETS_MODE", "ENV")

APP_ROOT = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
DB_NAME = get_optional_env_variable("ARCHES_DB_NAME", APP_NAME)
DB_USER = get_optional_env_variable("ARCHES_PGUSERNAME", "postgres")
DB_PASSWORD = get_optional_env_variable("ARCHES_PGPASSWORD", "postgis")
DB_HOST = get_optional_env_variable("ARCHES_PGHOST", "localhost")
DB_PORT = get_optional_env_variable("ARCHES_PGPORT", "5432")
ES_USER = get_optional_env_variable("ARCHES_ESUSER", "elastic")
ES_PASSWORD = get_optional_env_variable("ARCHES_ESPASSWORD", "E1asticSearchforArche5")
ES_HOST = get_optional_env_variable("ARCHES_ESHOST", "localhost")
ES_PORT = int(get_optional_env_variable("ARCHES_ESPORT", "9200"))
WEBPACK_DEVELOPMENT_SERVER_PORT = int(
    get_optional_env_variable("ARCHES_WEBPACKDEVELOPMENTSERVERPORT", "8022")
)
ES_PROTOCOL = get_optional_env_variable("ARCHES_ESPROTOCOL", "http")
ES_VALIDATE_CERT = get_optional_env_variable("ARCHES_ESVALIDATE", "True") == "True"
DEBUG = bool(get_optional_env_variable("ARCHES_DJANGO_DEBUG", False))
KIBANA_URL = get_optional_env_variable("ARCHES_KIBANA_URL", "http://localhost:5601/")
KIBANA_CONFIG_BASEPATH = get_optional_env_variable(
    "ARCHES_KIBANACONFIGBASEPATH", "kibana"
)
RESOURCE_IMPORT_LOG = get_optional_env_variable(
    "ARCHES_RESOURCEIMPORTLOG", os.path.join(APP_ROOT, "logs", "resource_import.log")
)
ARCHES_LOG_PATH = get_optional_env_variable(
    "ARCHES_LOGPATH", os.path.join(ROOT_DIR, "arches.log")
)

STORAGE_BACKEND = get_optional_env_variable(
    "ARCHES_STORAGEBACKEND", "django.core.files.storage.FileSystemStorage"
)

if STORAGE_BACKEND == "storages.backends.s3.S3Storage":
    import psutil

    STORAGE_OPTIONS = {
        "bucket_name": get_env_variable("ARCHES_S3BUCKETNAME"),
        "file_overwrite": get_optional_env_variable("ARCHES_S3FILEOVERWRITE", "True")
        == "True",
        "signature_version": get_optional_env_variable(
            "ARCHES_S3SIGNATUREVERSION", "s3v4"
        ),
        "region": get_optional_env_variable("ARCHES_S3REGION", "us-west-1"),
        "max_memory_size": get_optional_env_variable(
            "ARCHES_S3MAXMEMORY", str(psutil.virtual_memory().available * 0.5)
        ),
    }
else:
    STORAGE_OPTIONS = {}

STORAGES = {
    "default": {
        "BACKEND": STORAGE_BACKEND,
        "OPTIONS": STORAGE_OPTIONS,
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

if SECRETS_MODE == "AWS":
    try:
        import boto3
        import json

        AWS_REGION = get_optional_env_variable("ARCHES_AWS_REGION", "us-west-1")
        ES_SECRET_ID = get_env_variable("ARCHES_ES_SECRET_ID")
        DB_SECRET_ID = get_env_variable("ARCHES_DB_SECRET_ID")
        client = boto3.client("secretsmanager", region_name=AWS_REGION)
        es_secret = json.loads(
            client.get_secret_value(SecretId=ES_SECRET_ID)["SecretString"]
        )
        db_secret = json.loads(
            client.get_secret_value(SecretId=DB_SECRET_ID)["SecretString"]
        )
        DB_NAME = APP_NAME
        DB_USER = db_secret["username"]
        DB_PASSWORD = db_secret["password"]
        DB_HOST = db_secret["host"]
        DB_PORT = db_secret["port"]
        ES_USER = es_secret["user"]
        ES_PASSWORD = es_secret["password"]
        ES_HOST = es_secret["host"]
    except (ModuleNotFoundError, ImportError):
        pass


APP_VERSION = semantic_version.Version(major=0, minor=0, patch=0)


WEBPACK_LOADER = {
    "DEFAULT": {
        "STATS_FILE": os.path.join(APP_ROOT, "..", "webpack/webpack-stats.json"),
    },
}

DATATYPE_LOCATIONS.append("arches_lingo.datatypes")
FUNCTION_LOCATIONS.append("arches_lingo.functions")
ETL_MODULE_LOCATIONS.append("arches_lingo.etl_modules")
SEARCH_COMPONENT_LOCATIONS.append("arches_lingo.search_components")

LOCALE_PATHS.insert(0, os.path.join(APP_ROOT, "locale"))

FILE_TYPE_CHECKING = "lenient"
FILE_TYPES = [
    "bmp",
    "gif",
    "jpg",
    "jpeg",
    "pdf",
    "png",
    "psd",
    "rtf",
    "tif",
    "tiff",
    "xlsx",
    "csv",
    "zip",
]
FILENAME_GENERATOR = "arches.app.utils.storage_filename_generator.generate_filename"
UPLOADED_FILES_DIR = "uploadedfiles"

chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_optional_env_variable(
    "ARCHES_SECRET_KEY", "django-insecure-" + get_random_string(50, chars)
)

ROOT_URLCONF = "arches_lingo.urls"

ELASTICSEARCH_HOSTS = [{"scheme": ES_PROTOCOL, "host": ES_HOST, "port": ES_PORT}]
# Modify this line as needed for your project to connect to elasticsearch with a password that you generate
ELASTICSEARCH_CONNECTION_OPTIONS = {
    "request_timeout": 30,
    "verify_certs": ES_VALIDATE_CERT,
    "basic_auth": (ES_USER, ES_PASSWORD),
}

# If you need to connect to Elasticsearch via an API key instead of username/password, use the syntax below:
# ELASTICSEARCH_CONNECTION_OPTIONS = {"timeout": 30, "verify_certs": False, "api_key": "<ENCODED_API_KEY>"}
# ELASTICSEARCH_CONNECTION_OPTIONS = {"timeout": 30, "verify_certs": False, "api_key": ("<ID>", "<API_KEY>")}

# Your Elasticsearch instance needs to be configured with xpack.security.enabled=true to use API keys - update elasticsearch.yml or .env file and restart.

# Set the ELASTIC_PASSWORD environment variable in either the docker-compose.yml or .env file to the password you set for the elastic user,
# otherwise a random password will be generated.

# API keys can be generated via the Elasticsearch API: https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html
# Or Kibana: https://www.elastic.co/guide/en/kibana/current/api-keys.html

# a prefix to append to all elasticsearch indexes, note: must be lower case
ELASTICSEARCH_PREFIX = get_optional_env_variable("ARCHES_ES_INDEX_PREFIX", APP_NAME)

ELASTICSEARCH_CUSTOM_INDEXES = []

LOAD_DEFAULT_ONTOLOGY = False
LOAD_PACKAGE_ONTOLOGIES = True

# This is the namespace to use for export of data (for RDF/XML for example)
# It must point to the url where you host your site
# Make sure to use a trailing slash
PUBLIC_SERVER_ADDRESS = get_optional_env_variable(
    "ARCHES_PUBLIC_SERVER_ADDRESS", "http://localhost:8000/"
)
ARCHES_NAMESPACE_FOR_DATA_EXPORT = get_optional_env_variable(
    "ARCHES_NAMESPACE_FOR_DATA_EXPORT", PUBLIC_SERVER_ADDRESS
)

DATABASES = {
    "default": {
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "OPTIONS": {
            "options": "-c cursor_tuple_fraction=1",
        },
        "HOST": DB_HOST,
        "NAME": DB_NAME,
        "PASSWORD": DB_PASSWORD,
        "PORT": DB_PORT,
        "POSTGIS_TEMPLATE": "template_postgis",
        "TEST": {"CHARSET": None, "COLLATION": None, "MIRROR": None, "NAME": None},
        "TIME_ZONE": None,
        "USER": DB_USER,
    }
}

SEARCH_THUMBNAILS = False

INSTALLED_APPS = (
    "arches_lingo",
    "webpack_loader",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django_hosts",
    "arches_vue_utils",
    "arches",
    "arches.app.models",
    "arches.management",
    "guardian",
    "captcha",
    "revproxy",
    "corsheaders",
    "oauth2_provider",
    "django_celery_results",
    "arches_references",
    # "silk",
)

INSTALLED_APPS += ("arches.app",)

ROOT_HOSTCONF = "arches_lingo.hosts"
DEFAULT_HOST = "arches_lingo"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    #'arches.app.utils.middleware.TokenMiddleware',
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "arches.app.utils.middleware.ModifyAuthorizationHeader",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "arches.app.utils.middleware.SetAnonymousUser",
    # "silk.middleware.SilkyMiddleware",
]

MIDDLEWARE.insert(
    0, "django_hosts.middleware.HostsRequestMiddleware"
)  # this must resolve to first MIDDLEWARE entry

MIDDLEWARE.append(
    "django_hosts.middleware.HostsResponseMiddleware"
)  # this must resolve last MIDDLEWARE entry

STATICFILES_DIRS = build_staticfiles_dirs(app_root=APP_ROOT)

TEMPLATES = build_templates_config(
    debug=DEBUG,
    app_root=APP_ROOT,
)

ALLOWED_HOSTS = get_optional_env_variable("ARCHES_ALLOWED_HOSTS", "*").split(",")

SYSTEM_SETTINGS_LOCAL_PATH = os.path.join(
    APP_ROOT, "system_settings", "System_Settings.json"
)
WSGI_APPLICATION = "arches_lingo.wsgi.application"

# URL that handles the media served from MEDIA_ROOT, used for managing stored files.
# It must end in a slash if set to a non-empty value.
MEDIA_URL = "/files/"

# Absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = os.path.join(APP_ROOT)

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = "/static/"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(APP_ROOT, "staticfiles")

# when hosting Arches under a sub path set this value to the sub path eg : "/{sub_path}/"
FORCE_SCRIPT_NAME = None

RESOURCE_IMPORT_LOG = os.path.join(APP_ROOT, "logs", "resource_import.log")
DEFAULT_RESOURCE_IMPORT_USER = {"username": "admin", "userid": 1}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        },
    },
    "handlers": {
        "file": {
            "level": "WARNING",  # DEBUG, INFO, WARNING, ERROR
            "class": "logging.FileHandler",
            "filename": os.path.join(APP_ROOT, "arches.log"),
            "formatter": "console",
        },
        "console": {
            "level": "WARNING",
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "loggers": {
        "arches": {
            "handlers": ["file", "console"],
            "level": "WARNING",
            "propagate": True,
        }
    },
}

# Rate limit for authentication views
# See options (including None or python callables):
# https://django-ratelimit.readthedocs.io/en/stable/rates.html#rates-chapter
RATE_LIMIT = "5/m"

# Sets default max upload size to 15MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 15728640

# Unique session cookie ensures that logins are treated separately for each app
SESSION_COOKIE_NAME = "arches_lingo"

# For more info on configuring your cache: https://docs.djangoproject.com/en/2.2/topics/cache/
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "lingo": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "user_permission": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "user_permission_cache",
    },
}

# Hide nodes and cards in a report that have no data
HIDE_EMPTY_NODES_IN_REPORT = False

BYPASS_UNIQUE_CONSTRAINT_TILE_VALIDATION = False
BYPASS_REQUIRED_VALUE_TILE_VALIDATION = False

DATE_IMPORT_EXPORT_FORMAT = (
    "%Y-%m-%d"  # Custom date format for dates imported from and exported to csv
)

# This is used to indicate whether the data in the CSV and SHP exports should be
# ordered as seen in the resource cards or not.
EXPORT_DATA_FIELDS_IN_CARD_ORDER = False

# Identify the usernames and duration (seconds) for which you want to cache the time wheel
CACHE_BY_USER = {"default": 3600 * 24, "anonymous": 3600 * 24}  # 24hrs  # 24hrs

TILE_CACHE_TIMEOUT = 600  # seconds
CLUSTER_DISTANCE_MAX = 5000  # meters
GRAPH_MODEL_CACHE_TIMEOUT = None

OAUTH_CLIENT_ID = ""  #'9JCibwrWQ4hwuGn5fu2u1oRZSs9V6gK8Vu8hpRC4'

APP_TITLE = "Arches | Heritage Data Management"
COPYRIGHT_TEXT = "All Rights Reserved."
COPYRIGHT_YEAR = "2019"

ENABLE_CAPTCHA = False
# RECAPTCHA_PUBLIC_KEY = ''
# RECAPTCHA_PRIVATE_KEY = ''
# RECAPTCHA_USE_SSL = False
NOCAPTCHA = True
# RECAPTCHA_PROXY = 'http://127.0.0.1:8000'
if DEBUG is True:
    SILENCED_SYSTEM_CHECKS += ["captcha.recaptcha_test_key_error"]


# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  #<-- Only need to uncomment this for testing without an actual email server
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = "xxxx@xxx.com"
# EMAIL_HOST_PASSWORD = 'xxxxxxx'
# EMAIL_PORT = 587

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

CELERY_BROKER_URL = ""  # RabbitMQ --> "amqp://guest:guest@localhost",  Redis --> "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_BACKEND = (
    "django-db"  # Use 'django-cache' if you want to use your cache as your backend
)
CELERY_TASK_SERIALIZER = "json"


CELERY_SEARCH_EXPORT_EXPIRES = 24 * 3600  # seconds
CELERY_SEARCH_EXPORT_CHECK = 3600  # seconds

CELERY_BEAT_SCHEDULE = {
    "delete-expired-search-export": {
        "task": "arches.app.tasks.delete_file",
        "schedule": CELERY_SEARCH_EXPORT_CHECK,
    },
    "notification": {
        "task": "arches.app.tasks.message",
        "schedule": CELERY_SEARCH_EXPORT_CHECK,
        "args": ("Celery Beat is Running",),
    },
}

# Set to True if you want to send celery tasks to the broker without being able to detect celery.
# This might be necessary if the worker pool is regulary fully active, with no idle workers, or if
# you need to run the celery task using solo pool (e.g. on Windows). You may need to provide another
# way of monitoring celery so you can detect the background task not being available.
CELERY_CHECK_ONLY_INSPECT_BROKER = False

CANTALOUPE_DIR = os.path.join(ROOT_DIR, UPLOADED_FILES_DIR)
CANTALOUPE_HTTP_ENDPOINT = "http://localhost:8182/"

ACCESSIBILITY_MODE = False

RENDERERS = [
    {
        "name": "imagereader",
        "title": "Image Reader",
        "description": "Displays most image file types",
        "id": "5e05aa2e-5db0-4922-8938-b4d2b7919733",
        "iconclass": "fa fa-camera",
        "component": "views/components/cards/file-renderers/imagereader",
        "ext": "",
        "type": "image/*",
        "exclude": "tif,tiff,psd",
    },
    {
        "name": "pdfreader",
        "title": "PDF Reader",
        "description": "Displays pdf files",
        "id": "09dec059-1ee8-4fbd-85dd-c0ab0428aa94",
        "iconclass": "fa fa-file",
        "component": "views/components/cards/file-renderers/pdfreader",
        "ext": "pdf",
        "type": "application/pdf",
        "exclude": "tif,tiff,psd",
    },
]

# By setting RESTRICT_MEDIA_ACCESS to True, media file requests outside of Arches will checked against nodegroup permissions.
RESTRICT_MEDIA_ACCESS = False

# By setting RESTRICT_CELERY_EXPORT_FOR_ANONYMOUS_USER to True, if the user is attempting
# to export search results above the SEARCH_EXPORT_IMMEDIATE_DOWNLOAD_THRESHOLD
# value and is not signed in with a user account then the request will not be allowed.
RESTRICT_CELERY_EXPORT_FOR_ANONYMOUS_USER = False

# Dictionary containing any additional context items for customising email templates
EXTRA_EMAIL_CONTEXT = {
    "salutation": _("Hi"),
    "expiration": (
        datetime.now() + timedelta(seconds=CELERY_SEARCH_EXPORT_EXPIRES)
    ).strftime("%A, %d %B %Y"),
}

# see https://docs.djangoproject.com/en/1.9/topics/i18n/translation/#how-django-discovers-language-preference
# to see how LocaleMiddleware tries to determine the user's language preference
# (make sure to check your accept headers as they will override the LANGUAGE_CODE setting!)
# also see get_language_from_request in django.utils.translation.trans_real.py
# to see how the language code is derived in the actual code

####### TO GENERATE .PO FILES DO THE FOLLOWING ########
# run the following commands
# language codes used in the command should be in the form (which is slightly different
# form the form used in the LANGUAGE_CODE and LANGUAGES settings below):
# --local={countrycode}_{REGIONCODE} <-- countrycode is lowercase, regioncode is uppercase, also notice the underscore instead of hyphen
# commands to run (to generate files for "British English, German, and Spanish"):
# django-admin.py makemessages --ignore=env/* --local=de --local=en --local=en_GB --local=es  --extension=htm,py
# django-admin.py compilemessages


# default language of the application
# language code needs to be all lower case with the form:
# {langcode}-{regioncode} eg: en, en-gb ....
# a list of language codes can be found here http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en"

# list of languages to display in the language switcher,
# if left empty or with a single entry then the switch won't be displayed
# language codes need to be all lower case with the form:
# {langcode}-{regioncode} eg: en, en-gb ....
# a list of language codes can be found here http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGES = [
    #   ('de', _('German')),
    ("en", _("English")),
    #   ('en-gb', _('British English')),
    #   ('es', _('Spanish')),
]

# override this to permenantly display/hide the language switcher
SHOW_LANGUAGE_SWITCH = len(LANGUAGES) > 1

# TODO: remove when finalizing release
SILENCED_SYSTEM_CHECKS += ["arches.E002"]

try:
    from .package_settings import *
except ImportError:
    try:
        from package_settings import *
    except ImportError as e:
        pass

try:
    from .settings_local import *
except ImportError as e:
    try:
        from settings_local import *
    except ImportError as e:
        pass
