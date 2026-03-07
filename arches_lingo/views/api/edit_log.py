import json
from datetime import datetime, timezone

from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models import models
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.permissions import (
    anonymous_access_allowed,
    is_authenticated_user,
    is_lingo_editor,
)
from arches_lingo.utils.edit_log import (
    build_permitted_edit_log,
    revert_resource_to_timestamp,
)


class ResourceEditLogAPIView(View):
    def get(self, request, resourceid):
        if not anonymous_access_allowed() and not is_authenticated_user(request.user):
            return JsonResponse(
                {"message": _("Authentication required.")},
                status=403,
            )

        try:
            resource_instance = models.ResourceInstance.objects.get(pk=resourceid)
        except models.ResourceInstance.DoesNotExist:
            return JSONErrorResponse(
                title="Not found",
                message=f"Resource {resourceid} not found",
                status=404,
            )

        permitted_edits = build_permitted_edit_log(resource_instance, request.user)
        return JSONResponse({"resourceid": str(resourceid), "edits": permitted_edits})

    def post(self, request, resourceid):
        if not is_lingo_editor(request.user):
            return JsonResponse(
                {"message": _("Permission denied.")},
                status=403,
            )

        try:
            body = json.loads(request.body)
            target_timestamp = datetime.fromisoformat(body["timestamp"])
            if target_timestamp.tzinfo is None:
                target_timestamp = target_timestamp.replace(tzinfo=timezone.utc)
        except (KeyError, ValueError, json.JSONDecodeError) as parse_error:
            return JSONErrorResponse(
                title="Invalid request",
                message=f"Invalid request body: {str(parse_error)}",
                status=400,
            )

        try:
            models.ResourceInstance.objects.get(pk=resourceid)
        except models.ResourceInstance.DoesNotExist:
            return JSONErrorResponse(
                title="Not found",
                message=f"Resource {resourceid} not found",
                status=404,
            )

        errors = revert_resource_to_timestamp(resourceid, target_timestamp, request)

        if errors:
            return JSONResponse(
                {
                    "status": "partial_success",
                    "message": _(
                        "Resource was partially reverted; some changes could not be applied."
                    ),
                    "errors": errors,
                }
            )

        return JSONResponse(
            {"status": "ok", "message": _("Resource reverted successfully.")}
        )
