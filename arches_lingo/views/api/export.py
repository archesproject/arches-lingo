from django.views.generic import View

from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.etl_modules.lingo_resource_exporter import LingoResourceExporter
from arches_lingo.mixins.permissions import LingoExportMixin


class ThesaurusExportView(LingoExportMixin, View):
    """Start a thesaurus export for users with export permission.

    Exports are also reachable through the core Arches ETL manager, but that view
    requires membership in the Resource Editor group. This endpoint lets Lingo
    editors/admins, members of the Lingo Exporter group, and (if configured)
    anonymous users export without also needing a core Arches group.
    """

    def post(self, request):
        exporter = LingoResourceExporter(request=request)
        response = exporter.start(request)

        if response["success"]:
            return JSONResponse({"result": response["data"]})
        return JSONErrorResponse(content=response)
