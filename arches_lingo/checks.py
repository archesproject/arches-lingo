from django.conf import settings
from django.core.checks import Error

from arches_lingo.utils.reconciliation.rate_limit import is_valid_rate_limit


def check_reconciliation_rate_limit(app_configs, **kwargs):
    rate_limit = getattr(settings, "LINGO_RECONCILIATION_RATE_LIMIT", None)
    if rate_limit is None or is_valid_rate_limit(rate_limit):
        return []
    return [
        Error(
            "LINGO_RECONCILIATION_RATE_LIMIT is not a valid rate: %r" % (rate_limit,),
            hint='Use a positive number of requests per s, m, h or d, such as "120/m", '
            "or None for no limit.",
            id="arches_lingo.E001",
        )
    ]
