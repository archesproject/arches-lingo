"""Sizes above which an import or export is handed to a Celery worker.

Anything smaller runs inside the web request, so these must stay within the
time the web server allows a request to take.
"""

from django.conf import settings
from django.utils.translation import gettext as _

from arches_lingo.const import (
    DEFAULT_CELERY_CONCEPT_COUNT_THRESHOLD,
    DEFAULT_IMPORT_CELERY_BYTE_SIZE_LIMIT,
)

IMPORT_BYTE_SIZE_LIMIT_SETTING = "LINGO_IMPORT_CELERY_BYTE_SIZE_LIMIT"
CONCEPT_COUNT_THRESHOLD_SETTING = "LINGO_CELERY_CONCEPT_COUNT_THRESHOLD"


def get_import_celery_byte_size_limit():
    return getattr(
        settings, IMPORT_BYTE_SIZE_LIMIT_SETTING, DEFAULT_IMPORT_CELERY_BYTE_SIZE_LIMIT
    )


def get_celery_concept_count_threshold():
    return getattr(
        settings,
        CONCEPT_COUNT_THRESHOLD_SETTING,
        DEFAULT_CELERY_CONCEPT_COUNT_THRESHOLD,
    )


def celery_unavailable_message(threshold_setting):
    return _(
        "This thesaurus is too large to process without Celery, and no Celery "
        "worker is available. Ask your system administrator to start a worker, "
        "or to raise {setting} so it can be processed without one."
    ).format(setting=threshold_setting)
