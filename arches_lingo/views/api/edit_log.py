import json
from datetime import datetime, timezone

from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models import models
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.utils.edit_log import (
    build_permitted_edit_log,
    revert_resource_to_timestamp,
)


def _get_resource_or_404(resourceid):
    """Look up a resource instance, returning it or None + error response."""
    try:
        return models.ResourceInstance.objects.get(pk=resourceid), None
    except models.ResourceInstance.DoesNotExist:
        return None, JSONErrorResponse(
            title="Not found",
            message=f"Resource {resourceid} not found",
            status=404,
        )


def _delete_tile(tileid, request):
    """Delete a tile by id, silently ignoring DoesNotExist.

    Returns an error string on unexpected failure, or None on success.
    """
    try:
        tile = Tile.objects.get(pk=tileid)
        tile.delete(request=request)
    except Tile.DoesNotExist:
        pass
    except Exception as e:
        return str(e)
    return None


def _revert_tile(tileid, last_edit, resourceid, request):
    """Revert a single tile to the state described by *last_edit*.

    Returns an error string on failure, or None on success.
    """
    target_data = last_edit.newvalue
    if not target_data:
        return None

    try:
        tile = Tile.objects.get(pk=tileid)
        tile.data = target_data
        tile.save(request=request)
    except Tile.DoesNotExist:
        return _recreate_tile(tileid, last_edit, resourceid, request)
    except Exception as e:
        return _("Failed to update tile %(tileid)s: %(error)s") % {
            "tileid": tileid,
            "error": str(e),
        }
    return None


def _recreate_tile(tileid, last_edit, resourceid, request):
    """Recreate a tile that was deleted after the target timestamp.

    Returns an error string on failure, or None on success.
    """
    try:
        nodegroup = models.NodeGroup.objects.get(pk=last_edit.nodegroupid)
        if nodegroup.parentnodegroup_id is not None:
            return _(
                "Cannot restore nested tile %(tileid)s: "
                "parent tile information is not available "
                "in the edit log."
            ) % {"tileid": tileid}

        tile = Tile()
        tile.tileid = uuid.UUID(tileid)
        tile.resourceinstance_id = str(resourceid)
        tile.nodegroup_id = last_edit.nodegroupid
        tile.data = last_edit.newvalue
        tile.save(request=request)
    except Exception as e:
        return _("Failed to restore tile %(tileid)s: %(error)s") % {
            "tileid": tileid,
            "error": str(e),
        }
    return None


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ResourceEditLogAPIView(View):
    def get(self, request, resourceid):
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

        _, error_response = _get_resource_or_404(resourceid)
        if error_response:
            return error_response

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
