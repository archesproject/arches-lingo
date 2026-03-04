import uuid
from datetime import timezone

from django.utils.translation import gettext as _

from arches.app.models import models
from arches.app.models.card import Card
from arches.app.models.tile import Tile


EDIT_TYPE_LABELS = {
    "create": "Resource Created",
    "delete": "Resource Deleted",
    "tile delete": "Tile Deleted",
    "tile create": "Tile Created",
    "tile edit": "Tile Updated",
    "bulk_create": "Resource Created",
    "update_resource_instance_lifecycle_state": "Resource Lifecycle State Updated",
}


def build_permitted_edit_log(resource_instance, user):
    """Return a list of serialized edit dicts for resource_instance, filtered by user permissions."""
    edits = models.EditLog.objects.filter(
        resourceinstanceid=str(resource_instance.pk)
    ).order_by("timestamp")

    card_name_by_nodegroup_id = {
        str(card.nodegroup_id): card.name
        for card in Card.objects.filter(graph=resource_instance.graph)
    }

    nodegroups_by_id = models.NodeGroup.objects.filter(
        pk__in=[uuid.UUID(edit.nodegroupid) for edit in edits if edit.nodegroupid]
    ).in_bulk()

    permitted_edits = []
    for edit in edits:
        if edit.nodegroupid:
            nodegroup = nodegroups_by_id.get(uuid.UUID(edit.nodegroupid))
            if nodegroup and not user.has_perm("read_nodegroup", nodegroup):
                continue

        permitted_edits.append(
            {
                "editlogid": str(edit.editlogid),
                "transactionid": (
                    str(edit.transactionid) if edit.transactionid else None
                ),
                "edittype": edit.edittype,
                "edittype_label": EDIT_TYPE_LABELS.get(edit.edittype, edit.edittype),
                "timestamp": edit.timestamp.isoformat() if edit.timestamp else None,
                "userid": edit.userid,
                "user_firstname": edit.user_firstname,
                "user_lastname": edit.user_lastname,
                "user_username": edit.user_username,
                "user_email": edit.user_email,
                "nodegroupid": edit.nodegroupid,
                "tileinstanceid": edit.tileinstanceid,
                "card_name": (
                    card_name_by_nodegroup_id.get(edit.nodegroupid)
                    if edit.nodegroupid
                    else None
                ),
                "note": edit.note,
            }
        )

    return permitted_edits


def revert_resource_to_timestamp(resourceid, target_timestamp, request):
    """Revert all tiles for resourceid to their state at target_timestamp.

    target_timestamp may be naive (interpreted as UTC) or timezone-aware.
    Returns a list of error strings. An empty list means full success.
    """
    if target_timestamp.tzinfo is None:
        target_timestamp = target_timestamp.replace(tzinfo=timezone.utc)

    all_tile_edits_chronological = list(
        models.EditLog.objects.filter(
            resourceinstanceid=str(resourceid),
            tileinstanceid__isnull=False,
        )
        .exclude(tileinstanceid="")
        .order_by("timestamp")
    )

    affected_tile_ids = {
        edit.tileinstanceid
        for edit in all_tile_edits_chronological
        if edit.timestamp is not None
        and edit.timestamp.replace(tzinfo=edit.timestamp.tzinfo or timezone.utc)
        > target_timestamp
    }

    errors = []
    for tileid in affected_tile_ids:
        tile_edits_at_or_before_target = [
            edit
            for edit in all_tile_edits_chronological
            if edit.tileinstanceid == tileid
            and edit.timestamp is not None
            and edit.timestamp.replace(tzinfo=edit.timestamp.tzinfo or timezone.utc)
            <= target_timestamp
        ]

        last_edit_before_target = (
            tile_edits_at_or_before_target[-1]
            if tile_edits_at_or_before_target
            else None
        )

        if (
            last_edit_before_target is None
            or last_edit_before_target.edittype == "tile delete"
        ):
            # Tile either didn't exist yet or was already deleted at the target time.
            error = _delete_tile_by_id(tileid, request)
        else:
            error = _revert_tile_to_state_at_edit(
                tileid, last_edit_before_target, resourceid, request
            )

        if error:
            errors.append(error)

    return errors


def _delete_tile_by_id(tileid, request):
    """Delete a tile. Silently ignores DoesNotExist. Returns an error string on unexpected failure."""
    try:
        Tile.objects.get(pk=tileid).delete(request=request)
    except Tile.DoesNotExist:
        pass
    except Exception as deletion_error:
        return str(deletion_error)
    return None


def _revert_tile_to_state_at_edit(tileid, last_edit_before_target, resourceid, request):
    """Revert a tile to the state captured in last_edit_before_target.

    If the tile no longer exists (deleted after the target timestamp), recreates it.
    Returns an error string on failure, or None on success.
    """
    if not last_edit_before_target.newvalue:
        return None

    try:
        tile = Tile.objects.get(pk=tileid)
        tile.data = last_edit_before_target.newvalue
        tile.save(request=request)
    except Tile.DoesNotExist:
        return _recreate_deleted_tile_from_edit_log_entry(
            tileid, last_edit_before_target, resourceid, request
        )
    except Exception as update_error:
        return _("Failed to update tile %(tileid)s: %(error)s") % {
            "tileid": tileid,
            "error": str(update_error),
        }
    return None


def _recreate_deleted_tile_from_edit_log_entry(
    tileid, last_edit_before_target, resourceid, request
):
    """Recreate a tile that was deleted after the target timestamp.

    Returns an error string on failure, or None on success.
    """
    try:
        nodegroup = models.NodeGroup.objects.get(pk=last_edit_before_target.nodegroupid)
        if nodegroup.parentnodegroup_id is not None:
            return _(
                "Cannot restore nested tile %(tileid)s: "
                "parent tile information is not available "
                "in the edit log."
            ) % {"tileid": tileid}

        tile = Tile()
        tile.tileid = uuid.UUID(tileid)
        tile.resourceinstance_id = str(resourceid)
        tile.nodegroup_id = last_edit_before_target.nodegroupid
        tile.data = last_edit_before_target.newvalue
        tile.save(request=request)
    except Exception as creation_error:
        return _("Failed to restore tile %(tileid)s: %(error)s") % {
            "tileid": tileid,
            "error": str(creation_error),
        }
    return None
