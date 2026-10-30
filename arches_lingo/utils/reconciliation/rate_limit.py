import re

from django.conf import settings
from django_ratelimit.core import get_usage

RATE_LIMIT_GROUP = "arches_lingo.reconciliation"
# The subset of django-ratelimit's rate syntax that cannot fail at request time:
# a positive count per optional multiple of s, m, h or d, such as "120/m".
VALID_RATE_LIMIT_PATTERN = re.compile(r"[1-9]\d*/(?:[1-9]\d*)?[smhd]")


def is_valid_rate_limit(rate_limit):
    return isinstance(rate_limit, str) and bool(
        VALID_RATE_LIMIT_PATTERN.fullmatch(rate_limit)
    )


def seconds_until_allowed(request):
    """Count a request against ``LINGO_RECONCILIATION_RATE_LIMIT``; return how
    many seconds the caller must wait, or 0 while it is within the limit.

    Requests are counted per client address (see django-ratelimit's
    ``RATELIMIT_IP_META_KEY``) in ``RATELIMIT_USE_CACHE``, which every server
    process must share for the limit to hold across them.
    """
    usage = get_usage(
        request,
        group=RATE_LIMIT_GROUP,
        key="ip",
        rate=getattr(settings, "LINGO_RECONCILIATION_RATE_LIMIT", None),
        increment=True,
    )
    if usage is None or not usage["should_limit"]:
        return 0
    return max(1, usage["time_left"])
