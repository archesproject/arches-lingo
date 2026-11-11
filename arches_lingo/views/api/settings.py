from django.conf import settings
from django.views.generic import View

import arches
import arches_lingo
from arches.app.utils.response import JSONResponse

from arches_lingo.permissions import anonymous_access_allowed, reconciliation_enabled
from arches_lingo.utils.reconciliation.manifest import (
    reconciliation_service_url,
    scheme_reconciliation_service_url_template,
)


class AppSettingsView(View):
    """Returns application-level settings."""

    def get(self, request):
        is_reconciliation_enabled = reconciliation_enabled()
        return JSONResponse(
            {
                "allow_anonymous_access": anonymous_access_allowed(),
                "reconciliation_enabled": is_reconciliation_enabled,
                "reconciliation_service_url": (
                    reconciliation_service_url() if is_reconciliation_enabled else None
                ),
                "scheme_reconciliation_service_url_template": (
                    scheme_reconciliation_service_url_template()
                    if is_reconciliation_enabled
                    else None
                ),
                "public_server_address": getattr(
                    settings, "PUBLIC_SERVER_ADDRESS", None
                ),
                "arches_version": arches.__version__,
                "lingo_version": arches_lingo.__version__,
            }
        )
