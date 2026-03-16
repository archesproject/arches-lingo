from django.conf import settings
from django.views.generic import View

from arches.app.utils.response import JSONResponse

from arches_lingo.permissions import anonymous_access_allowed


class AppSettingsView(View):
    """Returns application-level settings."""

    def get(self, request):
        return JSONResponse(
            {
                "allow_anonymous_access": anonymous_access_allowed(),
                "public_server_address": getattr(
                    settings, "PUBLIC_SERVER_ADDRESS", None
                ),
            }
        )
