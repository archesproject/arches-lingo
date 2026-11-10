from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import Error, Warning

from arches_lingo.permissions import reconciliation_enabled
from arches_lingo.utils.reconciliation.rate_limit import is_valid_rate_limit

LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


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


def check_reconciliation_is_rate_limited(app_configs, **kwargs):
    if not reconciliation_enabled():
        return []
    if getattr(settings, "LINGO_RECONCILIATION_RATE_LIMIT", None) is not None:
        return []
    return [
        Warning(
            "The reconciliation service is enabled without a request rate limit, "
            "and it answers anonymous callers.",
            hint='Set LINGO_RECONCILIATION_RATE_LIMIT, such as "120/m". If a reverse '
            "proxy already limits request rates, add arches_lingo.W002 to "
            "SILENCED_SYSTEM_CHECKS.",
            id="arches_lingo.W002",
        )
    ]


def check_reconciliation_public_server_address(app_configs, **kwargs):
    if not reconciliation_enabled():
        return []
    public_server_address = getattr(settings, "PUBLIC_SERVER_ADDRESS", "") or ""
    hostname = urlsplit(public_server_address).hostname
    if hostname and hostname not in LOCAL_HOSTNAMES:
        return []
    return [
        Warning(
            "The reconciliation service is enabled, but PUBLIC_SERVER_ADDRESS is "
            "empty or a local address: %r" % (public_server_address,),
            hint="Set PUBLIC_SERVER_ADDRESS to the address OpenRefine users reach, "
            "since the service's links and URLs are built from it.",
            id="arches_lingo.W001",
        )
    ]
