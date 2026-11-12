import json
from django.views.generic import View

from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.const import (
    EXPORT_STATUS_QUEUED,
    EXPORT_STATUS_COMPLETE,
    DELEGATED_TO_CELERY,
)
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

        if not response["success"]:
            return JSONErrorResponse(content=response)

        if response["data"] == DELEGATED_TO_CELERY:
            return JSONResponse(
                {"result": response["data"], "status": EXPORT_STATUS_QUEUED}
            )

        return JSONResponse(
            {
                "result": response["data"],
                "status": EXPORT_STATUS_COMPLETE,
                "file": self._get_exported_file_details(exporter),
            }
        )

    @staticmethod
    def _get_exported_file_details(exporter):
        load_event = getattr(exporter, "load_event", None)
        if load_event is None or not load_event.load_details:
            return None
        return json.loads(load_event.load_details).get("file")
