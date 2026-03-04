import copy
import logging
import threading
import uuid

from arches.app.functions.base import BaseFunction
from arches.app.models.tile import Tile

from arches_lingo.const import (
    RELATION_STATUS_NODEGROUP,
    RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,
    RELATION_STATUS_ASCRIBED_RELATION_NODEID,
    RELATION_STATUS_STATUS_NODEID,
    RELATION_STATUS_STATUS_METATYPE_NODEID,
    RELATION_STATUS_TIMESPAN_BEGIN_OF_THE_BEGIN_NODEID,
    RELATION_STATUS_TIMESPAN_END_OF_THE_END_NODEID,
    RELATION_STATUS_DATA_ASSIGNMENT_ACTOR_NODEID,
    RELATION_STATUS_DATA_ASSIGNMENT_OBJECT_USED_NODEID,
    RELATION_STATUS_DATA_ASSIGNMENT_TYPE_NODEID,
)

logger = logging.getLogger(__name__)

RECIPROCAL_SYNC_CONTEXT = "reciprocal_sync"

# Thread-local storage to guard against infinite recursion during
# save and delete operations. Both guards are needed because:
# - save uses both context= and thread-local (belt and suspenders)
# - delete has no context param, so thread-local is the only guard
_thread_local = threading.local()

details = {
    "functionid": "dc0a3a78-f8a3-4472-b77d-7301d6718a36",
    "name": "Reciprocal Relationship",
    "type": "node",
    "description": "Ensures reciprocal relationship tiles exist between related Concepts",
    "defaultconfig": {"triggering_nodegroups": [RELATION_STATUS_NODEGROUP]},
    "classname": "ReciprocalRelationshipFunction",
    "component": "",
}


class ReciprocalRelationshipFunction(BaseFunction):
    """
    An Arches graph function that maintains reciprocal relationship tiles
    between Concept resources.

    Bidirectional sync: editing or deleting EITHER side of a relationship
    pair will propagate the change to the counterpart tile, regardless
    of which tile was the "original" and which was auto-created.
    """

    # Node IDs that should be mirrored from one tile to its counterpart.
    MIRRORED_NODES = [
        RELATION_STATUS_ASCRIBED_RELATION_NODEID,
        RELATION_STATUS_STATUS_NODEID,
        RELATION_STATUS_STATUS_METATYPE_NODEID,
        RELATION_STATUS_TIMESPAN_BEGIN_OF_THE_BEGIN_NODEID,
        RELATION_STATUS_TIMESPAN_END_OF_THE_END_NODEID,
        RELATION_STATUS_DATA_ASSIGNMENT_ACTOR_NODEID,
        RELATION_STATUS_DATA_ASSIGNMENT_OBJECT_USED_NODEID,
        RELATION_STATUS_DATA_ASSIGNMENT_TYPE_NODEID,
    ]

    def save(self, tile, request, context=None):
        raise NotImplementedError

    def post_save(self, tile, request, context=None):
        """Create or update a counterpart relationship tile on the related resource.

        Works bidirectionally: fires for both user-created tiles and
        auto-created counterpart tiles (unless suppressed by the
        recursion guard).
        """
        if context == RECIPROCAL_SYNC_CONTEXT:
            return
        if getattr(_thread_local, "syncing_save", False):
            return

        if str(tile.nodegroup_id) != RELATION_STATUS_NODEGROUP:
            return

        comparate_data = tile.data.get(RELATION_STATUS_ASCRIBED_COMPARATE_NODEID)
        if not comparate_data:
            logger.debug(
                "Reciprocal sync: tile %s has no comparate data, skipping.",
                tile.tileid,
            )
            return

        related_resource_id = self._get_related_resource_id(comparate_data)
        if not related_resource_id:
            logger.debug(
                "Reciprocal sync: could not extract resource ID from "
                "comparate data on tile %s, skipping.",
                tile.tileid,
            )
            return

        source_resource_id = str(tile.resourceinstance_id)
        if related_resource_id == source_resource_id:
            logger.debug(
                "Reciprocal sync: tile %s points to its own resource, skipping.",
                tile.tileid,
            )
            return

        counterpart_tile = self._find_counterpart_tile(
            related_resource_id, source_resource_id
        )

        try:
            _thread_local.syncing_save = True
            if counterpart_tile:
                self._update_counterpart_tile(
                    tile, counterpart_tile, source_resource_id
                )
            else:
                self._create_counterpart_tile(
                    tile, related_resource_id, source_resource_id
                )
        finally:
            _thread_local.syncing_save = False

    def delete(self, tile, request):
        """Delete the counterpart relationship tile when either side is deleted.

        Works bidirectionally: fires for both user-created tiles and
        auto-created counterpart tiles (unless suppressed by the
        recursion guard).
        """
        if getattr(_thread_local, "syncing_delete", False):
            return

        if str(tile.nodegroup_id) != RELATION_STATUS_NODEGROUP:
            return

        comparate_data = tile.data.get(RELATION_STATUS_ASCRIBED_COMPARATE_NODEID)
        if not comparate_data:
            logger.debug(
                "Reciprocal sync: tile %s has no comparate data on delete, skipping.",
                tile.tileid,
            )
            return

        related_resource_id = self._get_related_resource_id(comparate_data)
        if not related_resource_id:
            logger.debug(
                "Reciprocal sync: could not extract resource ID from "
                "comparate data on tile %s during delete, skipping.",
                tile.tileid,
            )
            return

        source_resource_id = str(tile.resourceinstance_id)
        if related_resource_id == source_resource_id:
            return

        counterpart_tile = self._find_counterpart_tile(
            related_resource_id, source_resource_id
        )

        if counterpart_tile:
            try:
                _thread_local.syncing_delete = True
                counterpart_tile.delete(request=request)
                logger.info(
                    "Deleted counterpart relationship tile %s on resource %s "
                    "(triggered by tile %s on resource %s)",
                    counterpart_tile.tileid,
                    related_resource_id,
                    tile.tileid,
                    source_resource_id,
                )
            except Exception:
                logger.exception(
                    "Failed to delete counterpart relationship tile %s "
                    "on resource %s",
                    counterpart_tile.tileid,
                    related_resource_id,
                )
            finally:
                _thread_local.syncing_delete = False
        else:
            logger.debug(
                "Reciprocal sync: no counterpart tile found on resource %s "
                "pointing back to resource %s (tile %s being deleted).",
                related_resource_id,
                source_resource_id,
                tile.tileid,
            )

    def on_import(self, tile):
        raise NotImplementedError

    def get(self):
        raise NotImplementedError

    def after_function_save(self, tile, request):
        raise NotImplementedError

    def _get_related_resource_id(self, comparate_data):
        """Extract the resource ID from a resource-instance value.

        Handles both single dict and list-of-dicts formats.
        """
        if isinstance(comparate_data, list):
            if len(comparate_data) > 0 and isinstance(comparate_data[0], dict):
                resource_id = comparate_data[0].get("resourceId", "")
                return str(resource_id) if resource_id else None
            return None
        elif isinstance(comparate_data, dict):
            resource_id = comparate_data.get("resourceId", "")
            return str(resource_id) if resource_id else None
        return None

    def _find_counterpart_tile(self, target_resource_id, pointing_to_resource_id):
        """Find an existing tile on target_resource_id whose comparate
        points back to pointing_to_resource_id."""
        tiles = Tile.objects.filter(
            resourceinstance_id=target_resource_id,
            nodegroup_id=RELATION_STATUS_NODEGROUP,
        )
        for candidate in tiles:
            candidate_comparate = candidate.data.get(
                RELATION_STATUS_ASCRIBED_COMPARATE_NODEID
            )
            candidate_related_id = self._get_related_resource_id(candidate_comparate)
            if candidate_related_id and candidate_related_id == pointing_to_resource_id:
                return candidate
        return None

    def _build_comparate_value(self, resource_id):
        """Build a resource-instance value pointing to the given resource."""
        return [
            {
                "resourceId": str(resource_id),
                "ontologyProperty": "",
                "inverseOntologyProperty": "",
                "resourceXresourceId": str(uuid.uuid4()),
            }
        ]

    def _build_counterpart_data(self, source_tile, pointing_back_to_resource_id):
        """Build tile data for the counterpart tile, mirroring all values
        from the source tile except the comparate which points back."""
        data = {}

        # Copy all mirrored node values
        for node_id in self.MIRRORED_NODES:
            value = source_tile.data.get(node_id)
            if value is not None:
                data[node_id] = copy.deepcopy(value)
            else:
                data[node_id] = None

        # Set the comparate to point back to the source resource
        data[RELATION_STATUS_ASCRIBED_COMPARATE_NODEID] = self._build_comparate_value(
            pointing_back_to_resource_id
        )

        return data

    def _create_counterpart_tile(
        self, source_tile, related_resource_id, source_resource_id
    ):
        """Create a new counterpart tile on the related resource."""
        try:
            counterpart_data = self._build_counterpart_data(
                source_tile, source_resource_id
            )
            counterpart_tile = Tile(
                tileid=uuid.uuid4(),
                resourceinstance_id=related_resource_id,
                nodegroup_id=RELATION_STATUS_NODEGROUP,
                data=counterpart_data,
            )
            counterpart_tile.save(request=None, context=RECIPROCAL_SYNC_CONTEXT)
            logger.info(
                "Created counterpart relationship tile %s on resource %s "
                "(source tile: %s on resource %s)",
                counterpart_tile.tileid,
                related_resource_id,
                source_tile.tileid,
                source_resource_id,
            )
        except Exception:
            logger.exception(
                "Failed to create counterpart relationship tile on resource %s "
                "(source tile: %s on resource %s)",
                related_resource_id,
                source_tile.tileid,
                source_resource_id,
            )

    def _update_counterpart_tile(
        self, source_tile, counterpart_tile, source_resource_id
    ):
        """Update an existing counterpart tile to stay in sync with the source."""
        try:
            counterpart_data = self._build_counterpart_data(
                source_tile, source_resource_id
            )
            counterpart_tile.data = counterpart_data
            counterpart_tile.save(request=None, context=RECIPROCAL_SYNC_CONTEXT)
            logger.info(
                "Updated counterpart relationship tile %s on resource %s "
                "(source tile: %s on resource %s)",
                counterpart_tile.tileid,
                counterpart_tile.resourceinstance_id,
                source_tile.tileid,
                source_resource_id,
            )
        except Exception:
            logger.exception(
                "Failed to update counterpart relationship tile %s on resource %s",
                counterpart_tile.tileid,
                counterpart_tile.resourceinstance_id,
            )
