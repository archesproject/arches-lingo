from collections import defaultdict

from django.db import connection
from django.db.models import F
from django.utils.translation import gettext as _

from arches.app.models.models import Node, ResourceInstance, TileModel

from arches_lingo.const import CONCEPTS_GRAPH_ID, SCHEMES_GRAPH_ID

OVERWRITE = "overwrite"
IGNORE = "ignore"

LINGO_GRAPH_IDS = [SCHEMES_GRAPH_ID, CONCEPTS_GRAPH_ID]

# The nodegroups a SKOS file fully describes, so an overwrite replaces them.
# The rest (concept type, URIs, identifiers, images, sources) are only filled
# in where empty: SKOS cannot carry them, or the import writes a placeholder
# (every concept arrives typed "concept") that would undo an editor's choice.
SKOS_SOURCED_NODEGROUP_ALIASES = frozenset(
    {
        "appellative_status",
        "statement",
        "match_status",
        "classification_status",
        "relation_status",
        "part_of_scheme",
        "top_concept_of",
    }
)

UNEDITABLE_RESOURCES_SHOWN_IN_ERROR = 10
SUBJECT_URI_LOOKUP_BATCH_SIZE = 5000


class ReimportBlockedError(Exception):
    pass


def normalize_overwrite_option(overwrite_option):
    return IGNORE if overwrite_option == IGNORE else OVERWRITE


def find_resource_ids_by_subject_uri(subject_uris):
    """Map subject URIs to the resources an earlier import loaded from them.

    Batched because a full vocabulary such as AAT has far too many subjects
    for a single IN clause.
    """
    subject_uris = list(subject_uris)
    resource_ids_by_subject_uri = {}
    for batch_start in range(0, len(subject_uris), SUBJECT_URI_LOOKUP_BATCH_SIZE):
        resource_ids_by_subject_uri.update(
            ResourceInstance.objects.filter(
                graph_id__in=LINGO_GRAPH_IDS,
                legacyid__in=subject_uris[
                    batch_start : batch_start + SUBJECT_URI_LOOKUP_BATCH_SIZE
                ],
            ).values_list("legacyid", "resourceinstanceid")
        )
    return resource_ids_by_subject_uri


def prepare_resources_for_reimport(resources, overwrite_option):
    """Return the resources to load and the ids of existing ones being replaced.

    Ignore drops every resource that already exists. Overwrite keeps them but
    refuses resources whose lifecycle state does not allow editing, and drops
    incoming tiles outside the SKOS-sourced nodegroups wherever the resource
    already has a tile in that nodegroup.
    """
    existing_resource_ids = set(
        ResourceInstance.objects.filter(
            graph_id__in=LINGO_GRAPH_IDS,
            resourceinstanceid__in=[
                resource["resourceinstanceid"] for resource in resources
            ],
        ).values_list("resourceinstanceid", flat=True)
    )
    if not existing_resource_ids:
        return resources, set()

    if normalize_overwrite_option(overwrite_option) == IGNORE:
        resources_to_load = [
            resource
            for resource in resources
            if resource["resourceinstanceid"] not in existing_resource_ids
        ]
        return resources_to_load, set()

    raise_if_any_resource_is_uneditable(existing_resource_ids)

    existing_nodegroup_aliases = find_nodegroup_aliases_with_tiles(
        existing_resource_ids
    )
    for resource in resources:
        resource_id = resource["resourceinstanceid"]
        if resource_id not in existing_resource_ids:
            continue
        resource["tile_data"] = [
            mock_tile
            for mock_tile in resource["tile_data"]
            if next(iter(mock_tile)) in SKOS_SOURCED_NODEGROUP_ALIASES
            or next(iter(mock_tile)) not in existing_nodegroup_aliases[resource_id]
        ]
    return resources, existing_resource_ids


def raise_if_any_resource_is_uneditable(resource_ids):
    uneditable_resources = list(
        ResourceInstance.objects.filter(
            resourceinstanceid__in=resource_ids,
            resource_instance_lifecycle_state__can_edit_resource_instances=False,
        ).values_list("legacyid", "resourceinstanceid")
    )
    if not uneditable_resources:
        return
    shown_resources = ", ".join(
        str(legacyid or resource_id)
        for legacyid, resource_id in uneditable_resources[
            :UNEDITABLE_RESOURCES_SHOWN_IN_ERROR
        ]
    )
    raise ReimportBlockedError(
        _(
            "{count} existing Schemes or Concepts cannot be overwritten because "
            "their lifecycle state does not allow editing: {resources}"
        ).format(count=len(uneditable_resources), resources=shown_resources)
    )


def find_nodegroup_aliases_with_tiles(resource_ids):
    alias_by_nodegroup_id = find_nodegroup_aliases_by_id()
    aliases_by_resource_id = defaultdict(set)
    for resource_id, nodegroup_id in (
        TileModel.objects.filter(resourceinstance_id__in=resource_ids)
        .values_list("resourceinstance_id", "nodegroup_id")
        .distinct()
    ):
        aliases_by_resource_id[resource_id].add(alias_by_nodegroup_id.get(nodegroup_id))
    return aliases_by_resource_id


def find_nodegroup_aliases_by_id():
    return dict(
        Node.objects.filter(
            graph_id__in=LINGO_GRAPH_IDS, nodeid=F("nodegroup_id")
        ).values_list("nodegroup_id", "alias")
    )


def delete_skos_sourced_tiles(resource_ids):
    """Remove the tiles an overwrite replaces.

    Deleting through the ORM also removes the resource relationships those
    tiles hold, which a raw delete would leave behind. The deferred foreign key
    checks the delete queues are run straight away, because the save that
    follows alters the tiles table, which Postgres refuses while trigger
    events are pending.
    """
    if not resource_ids:
        return
    skos_sourced_nodegroup_ids = [
        nodegroup_id
        for nodegroup_id, alias in find_nodegroup_aliases_by_id().items()
        if alias in SKOS_SOURCED_NODEGROUP_ALIASES
    ]
    TileModel.objects.filter(
        resourceinstance_id__in=resource_ids,
        nodegroup_id__in=skos_sourced_nodegroup_ids,
    ).delete()
    connection.check_constraints()
