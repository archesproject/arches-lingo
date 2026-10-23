import math
import time

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

PERIOD_SECONDS_BY_UNIT = {"s": 1, "m": 60, "h": 3600}


def parse_rate_limit(rate_limit):
    """Parse a rate such as ``"120/m"`` into ``(request_limit, period_seconds)``."""
    request_limit_text, _separator, period_unit = str(rate_limit).partition("/")
    try:
        request_limit = int(request_limit_text)
    except ValueError:
        request_limit = 0
    if request_limit < 1 or period_unit not in PERIOD_SECONDS_BY_UNIT:
        raise ImproperlyConfigured(
            "LINGO_RECONCILIATION_RATE_LIMIT must be a positive number of requests "
            'per second, minute or hour, such as "120/m".'
        )
    return request_limit, PERIOD_SECONDS_BY_UNIT[period_unit]


def seconds_until_allowed(client_address):
    """Count a request from ``client_address``; return how many seconds it must
    wait, or 0 while it is within ``LINGO_RECONCILIATION_RATE_LIMIT``.

    Requests are counted per fixed window in the default cache, which every
    server process must share for the limit to hold across them.
    """
    rate_limit = getattr(settings, "LINGO_RECONCILIATION_RATE_LIMIT", None)
    if not rate_limit:
        return 0
    request_limit, period_seconds = parse_rate_limit(rate_limit)

    current_time = time.time()
    window_index = int(current_time // period_seconds)
    cache_key = f"lingo-reconciliation-requests:{client_address}:{window_index}"
    cache.add(cache_key, 0, timeout=period_seconds)
    try:
        request_count = cache.incr(cache_key)
    except ValueError:
        # The counter expired since it was added, or the cache stores nothing.
        cache.set(cache_key, 1, timeout=period_seconds)
        request_count = 1
    if request_count <= request_limit:
        return 0
    return math.ceil((window_index + 1) * period_seconds - current_time)
