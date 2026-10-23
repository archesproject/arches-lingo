from django.views.generic import View

from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.etl_modules.lingo_resource_exporter import LingoResourceExporter
from arches_lingo.mixins.permissions import LingoEditorMixin


class ThesaurusExportView(LingoEditorMixin, View):
    """Start a thesaurus export for Lingo editors.

    Exports are also reachable through the core Arches ETL manager, but that view
    requires membership in the Resource Editor group. This endpoint lets the Lingo
    Editor group export without also needing a core Arches group.
    """

    def post(self, request):
        exporter = LingoResourceExporter(request=request)
        response = exporter.start(request)

        if response["success"]:
            return JSONResponse({"result": response["data"]})
        return JSONErrorResponse(content=response)
