import json
import uuid
from datetime import datetime, timezone

from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models import models
from arches.app.models.card import Card
from arches.app.models.tile import Tile
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse


EDIT_TYPE_LABELS = {
    "create": "Resource Created",
    "delete": "Resource Deleted",
    "tile delete": "Tile Deleted",
    "tile create": "Tile Created",
    "tile edit": "Tile Updated",
    "bulk_create": "Resource Created",
    "update_resource_instance_lifecycle_state": "Resource Lifecycle State Updated",
}


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class ResourceEditLogAPIView(View):
    def get(self, request, resourceid):
        """Return the edit log for a resource as JSON."""
        try:
            resource_instance = models.ResourceInstance.objects.get(pk=resourceid)
        except models.ResourceInstance.DoesNotExist:
            return JSONErrorResponse(
                title="Not found",
                message=f"Resource {resourceid} not found",
                status=404,
            )

        edits = models.EditLog.objects.filter(
            resourceinstanceid=str(resourceid)
        ).order_by("-timestamp")

        # Build nodegroup → card name lookup (all cards for the graph)
        cards = Card.objects.filter(graph=resource_instance.graph)
        card_lookup = {str(c.nodegroup_id): c.name for c in cards}

        # Check permissions per nodegroup
        nodegroup_ids = [
            uuid.UUID(e.nodegroupid) if e.nodegroupid else None for e in edits
        ]
        nodegroups_lookup = models.NodeGroup.objects.filter(
            pk__in=[ng for ng in nodegroup_ids if ng is not None]
        ).in_bulk()

        permitted_edits = []
        for edit in edits:
            if edit.nodegroupid:
                ng = nodegroups_lookup.get(uuid.UUID(edit.nodegroupid))
                if ng and not request.user.has_perm("read_nodegroup", ng):
                    continue

            permitted_edits.append(
                {
                    "editlogid": str(edit.editlogid),
                    "transactionid": (
                        str(edit.transactionid) if edit.transactionid else None
                    ),
                    "edittype": edit.edittype,
                    "edittype_label": _(
                        EDIT_TYPE_LABELS.get(edit.edittype, edit.edittype)
                    ),
                    "timestamp": (
                        edit.timestamp.isoformat() if edit.timestamp else None
                    ),
                    "userid": edit.userid,
                    "user_firstname": edit.user_firstname,
                    "user_lastname": edit.user_lastname,
                    "user_username": edit.user_username,
                    "user_email": edit.user_email,
                    "nodegroupid": edit.nodegroupid,
                    "tileinstanceid": edit.tileinstanceid,
                    "card_name": (
                        card_lookup.get(edit.nodegroupid) if edit.nodegroupid else None
                    ),
                    "note": edit.note,
                }
            )

        return JSONResponse(
            {
                "resourceid": str(resourceid),
                "edits": permitted_edits,
            }
        )

    def post(self, request, resourceid):
        """Revert a resource to a specific point in time."""
        try:
            body = json.loads(request.body)
            target_timestamp_str = body["timestamp"]
            target_timestamp = datetime.fromisoformat(target_timestamp_str)
            # Ensure timezone-aware for comparison
            if target_timestamp.tzinfo is None:
                target_timestamp = target_timestamp.replace(tzinfo=timezone.utc)
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            return JSONErrorResponse(
                title="Invalid request",
                message=f"Invalid request body: {str(e)}",
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

        # Get all tile-level edits for this resource ordered by timestamp
        all_tile_edits = list(
            models.EditLog.objects.filter(
                resourceinstanceid=str(resourceid),
                tileinstanceid__isnull=False,
            )
            .exclude(tileinstanceid="")
            .order_by("timestamp")
        )

        # Find tiles with edits after the target timestamp
        edits_after = [
            e
            for e in all_tile_edits
            if e.timestamp is not None and _make_aware(e.timestamp) > target_timestamp
        ]
        affected_tileids = {e.tileinstanceid for e in edits_after}

        errors = []
        for tileid in affected_tileids:
            # Find the state of this tile at target_timestamp
            tile_edits_at_or_before = [
                e
                for e in all_tile_edits
                if e.tileinstanceid == tileid
                and e.timestamp is not None
                and _make_aware(e.timestamp) <= target_timestamp
            ]

            if not tile_edits_at_or_before:
                # Tile was created after target timestamp — delete it
                try:
                    tile = Tile.objects.get(pk=tileid)
                    tile.delete(request=request)
                except Tile.DoesNotExist:
                    pass
                except Exception as e:
                    errors.append(str(e))
            else:
                last_edit = tile_edits_at_or_before[-1]

                if last_edit.edittype == "tile delete":
                    # Tile was deleted at or before target — it should not exist now
                    try:
                        tile = Tile.objects.get(pk=tileid)
                        tile.delete(request=request)
                    except Tile.DoesNotExist:
                        pass
                    except Exception as e:
                        errors.append(str(e))
                else:
                    # Tile should exist with the data from last_edit.newvalue
                    target_data = last_edit.newvalue
                    if not target_data:
                        continue

                    try:
                        tile = Tile.objects.get(pk=tileid)
                        tile.data = target_data
                        tile.save(request=request)
                    except Tile.DoesNotExist:
                        # Tile was deleted after the target — recreate it
                        try:
                            nodegroup = models.NodeGroup.objects.get(
                                pk=last_edit.nodegroupid
                            )
                            if nodegroup.parentnodegroup_id is not None:
                                errors.append(
                                    _(
                                        "Cannot restore nested tile %(tileid)s: "
                                        "parent tile information is not available "
                                        "in the edit log."
                                    )
                                    % {"tileid": tileid}
                                )
                                continue

                            tile = Tile()
                            tile.tileid = uuid.UUID(tileid)
                            tile.resourceinstance_id = str(resourceid)
                            tile.nodegroup_id = last_edit.nodegroupid
                            tile.data = target_data
                            tile.save(request=request)
                        except Exception as e:
                            errors.append(
                                _("Failed to restore tile %(tileid)s: %(error)s")
                                % {"tileid": tileid, "error": str(e)}
                            )
                    except Exception as e:
                        errors.append(
                            _("Failed to update tile %(tileid)s: %(error)s")
                            % {"tileid": tileid, "error": str(e)}
                        )

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
            {
                "status": "ok",
                "message": _("Resource reverted successfully."),
            }
        )


def _make_aware(dt):
    """Ensure a datetime is timezone-aware (UTC if naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
