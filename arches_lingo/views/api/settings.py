from django.conf import settings
from django.utils.translation import gettext as _

from arches.app.utils.response import JSONResponse
from arches.app.views.api import APIBase


class PublicServerAddressView(APIBase):
    def get(self, request):
        public_server_address = getattr(settings, "PUBLIC_SERVER_ADDRESS", None)

        return JSONResponse(
            {
                "PUBLIC_SERVER_ADDRESS": public_server_address,
            }
        )
