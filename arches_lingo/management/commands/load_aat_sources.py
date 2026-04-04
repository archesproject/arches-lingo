"""
Management command: load_aat_sources
======================================

Loads Getty AAT source and contributor attribution data into Lingo.

Prerequisites:
  1. The AAT SKOS data has already been imported via the normal Lingo import
     (``python manage.py packages -o import_lingo_resources -s getty_aat_skos.xml``)
  2. The extraction script has been run to produce aat_sources.json:
     ``python scripts/extract_getty_aat_sources.py``

What this command does:
  - Phase 1: Creates ``textual_work`` resources for each unique source.
  - Phase 2: Creates ``group`` resources for each unique contributor.
  - Phase 3: Updates existing concept/scheme label tiles (``appellative_status``)
    and note tiles (``statement``) to reference the source/contributor resources
    via their ``data_assignment_object_used`` and ``data_assignment_actor`` fields.

Usage:
    python manage.py load_aat_sources --source aat_sources.json
"""

import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime

from django.core.management.base import BaseCommand

from arches.app.etl_modules.save import save_to_tiles
from arches.app.models.models import (
    LoadEvent,
    LoadStaging,
    ETLModule,
    Node,
    NodeGroup,
    TileModel,
    ResourceInstance,
)
from arches.app.models import models

import arches_lingo.const as const

logger = logging.getLogger(__name__)

# --- Graph IDs ---
TEXTUAL_WORK_GRAPH_ID = "6dad61aa-b4b5-11ea-84f7-3af9d3b32b71"
PERSON_GRAPH_ID = "9ffb6fcc-b4b4-11ea-84f7-3af9d3b32b71"
GROUP_GRAPH_ID = "d6774bfc-b4b4-11ea-84f7-3af9d3b32b71"

# --- Textual Work name nodes ---
TEXTUAL_WORK_NAME_NODEGROUP = "42fd96f4-11e6-11ef-9493-0a58a9feac02"
TEXTUAL_WORK_NAME_CONTENT_NODE = "42fd9a5a-11e6-11ef-9493-0a58a9feac02"

# --- Person name nodes ---
PERSON_NAME_NODEGROUP = "4952a70a-bb15-11ea-85a6-3af9d3b32b71"
PERSON_NAME_CONTENT_NODE = "4952a9ee-bb15-11ea-85a6-3af9d3b32b71"

# --- Group name nodes ---
GROUP_NAME_NODEGROUP = "de76dbdc-11e5-11ef-9493-0a58a9feac02"
GROUP_NAME_CONTENT_NODE = "de76df10-11e5-11ef-9493-0a58a9feac02"

# --- Concept appellative_status data assignment nodes ---
CONCEPT_APPSTATUS_DA_ACTOR_NODE = "0acd2982-0eb9-11ef-93db-0a58a9feac02"
CONCEPT_APPSTATUS_DA_OBJ_USED_NODE = "df980c50-0eb8-11ef-93db-0a58a9feac02"

# --- Concept statement data assignment nodes ---
CONCEPT_STMT_DA_ACTOR_NODE = "bf73e650-4888-11ee-8a8d-11afefc4bff7"
CONCEPT_STMT_DA_OBJ_USED_NODE = "bf73e652-4888-11ee-8a8d-11afefc4bff7"

# --- Scheme appellative_status data assignment nodes ---
SCHEME_APPSTATUS_DA_ACTOR_NODE = "ef87b1d2-11de-11ef-9493-0a58a9feac02"
SCHEME_APPSTATUS_DA_OBJ_USED_NODE = "ef87b4de-11de-11ef-9493-0a58a9feac02"

# --- Scheme statement data assignment nodes ---
SCHEME_STMT_NODEGROUP = "7131bc72-11e0-11ef-9493-0a58a9feac02"
SCHEME_STMT_DA_ACTOR_NODE = "7131c83e-11e0-11ef-9493-0a58a9feac02"
SCHEME_STMT_DA_OBJ_USED_NODE = "7131c8ca-11e0-11ef-9493-0a58a9feac02"

# AAT URI patterns
AAT_CONCEPT_PREFIX = "http://vocab.getty.edu/aat/"

# Deterministic UUID namespace for AAT source/contributor resources.
# Using a fixed namespace means the same URI always produces the same resource ID,
# making the load command idempotent across reruns.
_AAT_RESOURCE_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# Batch size for bulk_create
BATCH_SIZE = 2000


def _make_ri_list_value(resource_ids):
    """Build a resource-instance-list value (list of dicts)."""
    return [
        {
            "resourceId": str(rid),
            "ontologyProperty": "",
            "inverseOntologyProperty": "",
            "resourceXresourceId": "",
        }
        for rid in resource_ids
    ]


def _make_staging_value(node_id, value, datatype):
    """Build a staging value envelope for a single node."""
    return {
        node_id: {
            "value": value,
            "valid": True,
            "source": "",
            "notes": "",
            "datatype": datatype,
        }
    }


class Command(BaseCommand):
    help = "Load AAT source/contributor attribution data into Lingo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            "-s",
            required=True,
            help="Path to aat_sources.json file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print statistics without loading data",
        )

    def handle(self, *args, **options):
        source_path = options["source"]
        dry_run = options["dry_run"]

        self.stdout.write(f"Loading source data from {source_path} ...")
        with open(source_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        sources = data["sources"]
        contributors = data["contributors"]
        labels = data["labels"]
        notes = data["notes"]

        self.stdout.write(
            f"  {len(sources)} sources, {len(contributors)} contributors\n"
            f"  {len(labels)} concepts with label attribution\n"
            f"  {len(notes)} concepts with note attribution"
        )

        if dry_run:
            self.stdout.write("Dry run — exiting.")
            return

        admin_user = models.User.objects.get(username="admin")

        # Phase 1: Create textual_work resources for sources
        self.stdout.write("\n=== Phase 1: Creating source (textual_work) resources ===")
        source_resource_map = self._create_source_resources(sources, admin_user)

        # Phase 2: Create group resources for contributors
        self.stdout.write("\n=== Phase 2: Creating contributor (group) resources ===")
        contributor_resource_map = self._create_contributor_resources(
            contributors, admin_user
        )

        # Phase 3: Update existing tiles with source/contributor references
        self.stdout.write(
            "\n=== Phase 3: Updating label/note tiles with attribution ==="
        )
        self._update_attribution_tiles(
            labels, notes, source_resource_map, contributor_resource_map, admin_user
        )

        self.stdout.write("\nDone!")

    def _create_source_resources(self, sources, user):
        """Create textual_work resources for each source. Returns {source_uri: resource_id}."""
        load_id = str(uuid.uuid4())
        etl_module = ETLModule.objects.get(slug="migrate-to-lingo")

        load_event = LoadEvent.objects.create(
            loadid=load_id,
            user=user,
            etl_module=etl_module,
            status="running",
            load_details=json.dumps({"operation": "AAT Source Resources"}),
            load_start_time=datetime.now(),
            complete=False,
        )

        source_resource_map = {}
        staging_rows = []
        name_nodegroup = NodeGroup.objects.get(nodegroupid=TEXTUAL_WORK_NAME_NODEGROUP)

        # Build blank tile template for the name nodegroup
        blank_tile = self._get_blank_tile(TEXTUAL_WORK_NAME_NODEGROUP)

        # Compute deterministic resource IDs first, then check which already exist
        for source_uri in sources:
            source_resource_map[source_uri] = uuid.uuid5(
                _AAT_RESOURCE_NAMESPACE, source_uri
            )

        existing_ids = set(
            ResourceInstance.objects.filter(
                resourceinstanceid__in=source_resource_map.values()
            ).values_list("resourceinstanceid", flat=True)
        )
        new_count = len(source_resource_map) - len(existing_ids)
        self.stdout.write(
            f"  {len(existing_ids)} already exist, creating {new_count} new ..."
        )

        for source_uri, meta in sources.items():
            resource_id = source_resource_map[source_uri]
            if resource_id in existing_ids:
                continue

            # Use short_title if available, otherwise full title, otherwise URI
            name = meta.get("short_title") or meta.get("title") or source_uri

            tile_value = dict(blank_tile)
            tile_value[TEXTUAL_WORK_NAME_CONTENT_NODE] = {
                "value": name,
                "valid": True,
                "source": name,
                "notes": "",
                "datatype": "non-localized-string",
            }

            staging_rows.append(
                LoadStaging(
                    load_event=load_event,
                    nodegroup=name_nodegroup,
                    resourceid=resource_id,
                    tileid=uuid.uuid4(),
                    parenttileid=None,
                    value=tile_value,
                    passes_validation=True,
                    nodegroup_depth=0,
                    source_description=f"Source: {source_uri}",
                    operation="insert",
                    sortorder=0,
                )
            )

        if staging_rows:
            # Get lifecycle state for textual_work graph
            lifecycle_state = self._get_default_lifecycle_state(TEXTUAL_WORK_GRAPH_ID)

            resource_instances = [
                ResourceInstance(
                    resourceinstanceid=source_resource_map[uri],
                    graph_id=TEXTUAL_WORK_GRAPH_ID,
                    resource_instance_lifecycle_state=lifecycle_state,
                )
                for uri in sources
                if source_resource_map[uri] not in existing_ids
            ]

            # Bulk create in batches
            for i in range(0, len(resource_instances), BATCH_SIZE):
                ResourceInstance.objects.bulk_create(
                    resource_instances[i : i + BATCH_SIZE], ignore_conflicts=True
                )
            for i in range(0, len(staging_rows), BATCH_SIZE):
                LoadStaging.objects.bulk_create(staging_rows[i : i + BATCH_SIZE])

            self.stdout.write(f"  Saving tiles ...")
            save_to_tiles(user.pk, load_id)
        else:
            self.stdout.write("  All source resources already exist, skipping.")
            load_event.status = "completed"
            load_event.complete = True
            load_event.successful = True
            load_event.load_end_time = datetime.now()
            load_event.save()
        self.stdout.write(
            f"  Done: {len(source_resource_map)} source resources created."
        )
        return source_resource_map

    def _create_contributor_resources(self, contributors, user):
        """Create group resources for each contributor. Returns {contributor_uri: resource_id}."""
        load_id = str(uuid.uuid4())
        etl_module = ETLModule.objects.get(slug="migrate-to-lingo")

        load_event = LoadEvent.objects.create(
            loadid=load_id,
            user=user,
            etl_module=etl_module,
            status="running",
            load_details=json.dumps({"operation": "AAT Contributor Resources"}),
            load_start_time=datetime.now(),
            complete=False,
        )

        contributor_resource_map = {}
        staging_rows = []
        name_nodegroup = NodeGroup.objects.get(nodegroupid=GROUP_NAME_NODEGROUP)

        blank_tile = self._get_blank_tile(GROUP_NAME_NODEGROUP)

        # Compute deterministic resource IDs, then check which already exist
        for contrib_uri in contributors:
            contributor_resource_map[contrib_uri] = uuid.uuid5(
                _AAT_RESOURCE_NAMESPACE, contrib_uri
            )

        existing_ids = set(
            ResourceInstance.objects.filter(
                resourceinstanceid__in=contributor_resource_map.values()
            ).values_list("resourceinstanceid", flat=True)
        )
        new_count = len(contributor_resource_map) - len(existing_ids)
        self.stdout.write(
            f"  {len(existing_ids)} already exist, creating {new_count} new ..."
        )

        for contrib_uri, meta in contributors.items():
            resource_id = contributor_resource_map[contrib_uri]
            if resource_id in existing_ids:
                continue

            name = meta.get("name") or meta.get("nick") or contrib_uri

            tile_value = dict(blank_tile)
            tile_value[GROUP_NAME_CONTENT_NODE] = {
                "value": name,
                "valid": True,
                "source": name,
                "notes": "",
                "datatype": "non-localized-string",
            }

            staging_rows.append(
                LoadStaging(
                    load_event=load_event,
                    nodegroup=name_nodegroup,
                    resourceid=resource_id,
                    tileid=uuid.uuid4(),
                    parenttileid=None,
                    value=tile_value,
                    passes_validation=True,
                    nodegroup_depth=0,
                    source_description=f"Contributor: {contrib_uri}",
                    operation="insert",
                    sortorder=0,
                )
            )

        if staging_rows:
            lifecycle_state = self._get_default_lifecycle_state(GROUP_GRAPH_ID)

            resource_instances = [
                ResourceInstance(
                    resourceinstanceid=contributor_resource_map[uri],
                    graph_id=GROUP_GRAPH_ID,
                    resource_instance_lifecycle_state=lifecycle_state,
                )
                for uri in contributors
                if contributor_resource_map[uri] not in existing_ids
            ]

            for i in range(0, len(resource_instances), BATCH_SIZE):
                ResourceInstance.objects.bulk_create(
                    resource_instances[i : i + BATCH_SIZE], ignore_conflicts=True
                )
            for i in range(0, len(staging_rows), BATCH_SIZE):
                LoadStaging.objects.bulk_create(staging_rows[i : i + BATCH_SIZE])

            self.stdout.write(f"  Saving tiles ...")
            save_to_tiles(user.pk, load_id)
        else:
            self.stdout.write("  All contributor resources already exist, skipping.")
            load_event.status = "completed"
            load_event.complete = True
            load_event.successful = True
            load_event.load_end_time = datetime.now()
            load_event.save()
        self.stdout.write(
            f"  Done: {len(contributor_resource_map)} contributor resources created."
        )
        return contributor_resource_map

    def _update_attribution_tiles(
        self, labels, notes, source_resource_map, contributor_resource_map, user
    ):
        """Update existing label and note tiles with source/contributor references."""
        load_id = str(uuid.uuid4())
        etl_module = ETLModule.objects.get(slug="migrate-to-lingo")

        load_event = LoadEvent.objects.create(
            loadid=load_id,
            user=user,
            etl_module=etl_module,
            status="running",
            load_details=json.dumps({"operation": "AAT Attribution Updates"}),
            load_start_time=datetime.now(),
            complete=False,
        )

        # Pre-populate node datatype cache for all relevant nodegroups
        self._preload_node_datatypes(
            [
                const.CONCEPT_NAME_NODEGROUP,
                const.SCHEME_NAME_NODEGROUP,
                const.STATEMENT_NODEGROUP,
                SCHEME_STMT_NODEGROUP,
            ]
        )

        # Build a lookup of concept URI -> resource instance ID
        # AAT concept URIs look like http://vocab.getty.edu/aat/300011021
        # Resource instances have their AAT URI stored in the uri tile
        self.stdout.write("  Building concept URI -> resource ID lookup ...")
        concept_uri_to_resource = self._build_concept_uri_lookup(
            labels=labels, notes=notes
        )

        self.stdout.write("  Building tile lookup for labels and notes ...")
        label_tile_lookup = self._build_label_tile_lookup(concept_uri_to_resource)
        note_tile_lookup = self._build_note_tile_lookup(concept_uri_to_resource)

        staging_rows = []
        updated_labels = 0
        updated_notes = 0
        skipped_labels = 0
        skipped_notes = 0

        # Process label attributions
        for concept_uri, label_list in labels.items():
            resource_id = concept_uri_to_resource.get(concept_uri)
            if not resource_id:
                skipped_labels += len(label_list)
                continue

            tiles = label_tile_lookup.get(str(resource_id), {})
            for label_info in label_list:
                tile_key = self._make_label_key(
                    label_info["literal_form"],
                    label_info["language"],
                )
                tile_info = tiles.get(tile_key)
                if not tile_info:
                    skipped_labels += 1
                    continue

                tile_id = tile_info["tileid"]
                existing_data = tile_info["data"]
                graph_id = tile_info["graph_id"]

                # Determine which node IDs to use based on the graph
                if str(graph_id) == const.CONCEPTS_GRAPH_ID:
                    actor_node = CONCEPT_APPSTATUS_DA_ACTOR_NODE
                    obj_node = CONCEPT_APPSTATUS_DA_OBJ_USED_NODE
                    nodegroup_id = const.CONCEPT_NAME_NODEGROUP
                elif str(graph_id) == const.SCHEMES_GRAPH_ID:
                    actor_node = SCHEME_APPSTATUS_DA_ACTOR_NODE
                    obj_node = SCHEME_APPSTATUS_DA_OBJ_USED_NODE
                    nodegroup_id = const.SCHEME_NAME_NODEGROUP
                else:
                    skipped_labels += 1
                    continue

                # Build the update value — include ALL existing data plus new fields
                tile_value = {}
                for node_id, node_val in existing_data.items():
                    tile_value[node_id] = {
                        "value": node_val,
                        "valid": True,
                        "source": "",
                        "notes": "",
                        "datatype": self._get_node_datatype(node_id),
                    }

                # Add source references
                source_rids = [
                    source_resource_map[s]
                    for s in label_info.get("sources", [])
                    if s in source_resource_map
                ]
                if source_rids:
                    tile_value[obj_node] = {
                        "value": _make_ri_list_value(source_rids),
                        "valid": True,
                        "source": "",
                        "notes": "",
                        "datatype": "resource-instance-list",
                    }

                # Add contributor references
                contrib_rids = [
                    contributor_resource_map[c]
                    for c in label_info.get("contributors", [])
                    if c in contributor_resource_map
                ]
                if contrib_rids:
                    tile_value[actor_node] = {
                        "value": _make_ri_list_value(contrib_rids),
                        "valid": True,
                        "source": "",
                        "notes": "",
                        "datatype": "resource-instance-list",
                    }

                if not source_rids and not contrib_rids:
                    skipped_labels += 1
                    continue

                staging_rows.append(
                    LoadStaging(
                        load_event=load_event,
                        nodegroup=NodeGroup(nodegroup_id),
                        resourceid=resource_id,
                        tileid=tile_id,
                        parenttileid=None,
                        value=tile_value,
                        passes_validation=True,
                        nodegroup_depth=0,
                        source_description=f"Label attribution: {concept_uri}",
                        operation="update",
                        sortorder=0,
                    )
                )
                updated_labels += 1

        # Process note attributions
        for concept_uri, note_list in notes.items():
            resource_id = concept_uri_to_resource.get(concept_uri)
            if not resource_id:
                skipped_notes += len(note_list)
                continue

            tiles = note_tile_lookup.get(str(resource_id), {})
            for note_info in note_list:
                tile_key = self._make_note_key(
                    note_info["value"],
                    note_info["language"],
                )
                tile_info = tiles.get(tile_key)
                if not tile_info:
                    skipped_notes += 1
                    continue

                tile_id = tile_info["tileid"]
                existing_data = tile_info["data"]
                graph_id = tile_info["graph_id"]

                if str(graph_id) == const.CONCEPTS_GRAPH_ID:
                    actor_node = CONCEPT_STMT_DA_ACTOR_NODE
                    obj_node = CONCEPT_STMT_DA_OBJ_USED_NODE
                    nodegroup_id = const.STATEMENT_NODEGROUP
                elif str(graph_id) == const.SCHEMES_GRAPH_ID:
                    actor_node = SCHEME_STMT_DA_ACTOR_NODE
                    obj_node = SCHEME_STMT_DA_OBJ_USED_NODE
                    nodegroup_id = SCHEME_STMT_NODEGROUP
                else:
                    skipped_notes += 1
                    continue

                tile_value = {}
                for node_id, node_val in existing_data.items():
                    tile_value[node_id] = {
                        "value": node_val,
                        "valid": True,
                        "source": "",
                        "notes": "",
                        "datatype": self._get_node_datatype(node_id),
                    }

                source_rids = [
                    source_resource_map[s]
                    for s in note_info.get("sources", [])
                    if s in source_resource_map
                ]
                if source_rids:
                    tile_value[obj_node] = {
                        "value": _make_ri_list_value(source_rids),
                        "valid": True,
                        "source": "",
                        "notes": "",
                        "datatype": "resource-instance-list",
                    }

                contrib_rids = [
                    contributor_resource_map[c]
                    for c in note_info.get("contributors", [])
                    if c in contributor_resource_map
                ]
                if contrib_rids:
                    tile_value[actor_node] = {
                        "value": _make_ri_list_value(contrib_rids),
                        "valid": True,
                        "source": "",
                        "notes": "",
                        "datatype": "resource-instance-list",
                    }

                if not source_rids and not contrib_rids:
                    skipped_notes += 1
                    continue

                staging_rows.append(
                    LoadStaging(
                        load_event=load_event,
                        nodegroup=NodeGroup(nodegroup_id),
                        resourceid=resource_id,
                        tileid=tile_id,
                        parenttileid=None,
                        value=tile_value,
                        passes_validation=True,
                        nodegroup_depth=0,
                        source_description=f"Note attribution: {concept_uri}",
                        operation="update",
                        sortorder=0,
                    )
                )
                updated_notes += 1

        self.stdout.write(
            f"  Labels to update: {updated_labels}, skipped: {skipped_labels}\n"
            f"  Notes to update:  {updated_notes}, skipped: {skipped_notes}"
        )

        if staging_rows:
            self.stdout.write(f"  Staging {len(staging_rows)} tile updates ...")
            for i in range(0, len(staging_rows), BATCH_SIZE):
                LoadStaging.objects.bulk_create(staging_rows[i : i + BATCH_SIZE])

            self.stdout.write(f"  Saving tiles ...")
            save_to_tiles(user.pk, load_id)
            self.stdout.write(f"  Done.")
        else:
            self.stdout.write("  No tiles to update.")
            load_event.status = "completed"
            load_event.complete = True
            load_event.successful = True
            load_event.load_end_time = datetime.now()
            load_event.save()

    def _build_concept_uri_lookup(self, labels=None, notes=None):
        """Build {concept_uri: resource_instance_id} from existing URI tiles.

        If no URI tiles exist, falls back to matching English prefLabels from
        the provenance data against label tiles in the database, then creates
        URI tiles for matched resources so that future runs can use them.
        """
        # Scheme URI nodegroup/node IDs (different from concept)
        SCHEME_URI_NODEGROUP = "7fdc87bb-6ef9-4a74-8e84-4bde69557eef"
        SCHEME_URI_CONTENT_NODE = "1bd0f20b-b945-4231-b872-cba02cc4bc25"

        # Query both concept and scheme URI tiles
        uri_tiles = TileModel.objects.filter(
            nodegroup_id__in=[const.URI_NODEGROUP, SCHEME_URI_NODEGROUP],
        ).values_list("resourceinstance_id", "nodegroup_id", "data")

        lookup = {}
        for resource_id, nodegroup_id, data in uri_tiles:
            if not data:
                continue
            # Determine which content node to read based on nodegroup
            uri_node = (
                SCHEME_URI_CONTENT_NODE
                if str(nodegroup_id) == SCHEME_URI_NODEGROUP
                else const.URI_CONTENT_NODE
            )
            uri_value = data.get(uri_node)
            if isinstance(uri_value, str) and uri_value.startswith(AAT_CONCEPT_PREFIX):
                lookup[uri_value] = resource_id

        if lookup:
            self.stdout.write(f"  Found {len(lookup)} resources with AAT URIs")
            return lookup

        # --- Fallback: No URI tiles exist. Build mapping from label matching. ---
        self.stdout.write(
            "  No URI tiles found. Building mapping from English prefLabels ..."
        )

        if not labels and not notes:
            self.stdout.write("  WARNING: No provenance data provided for fallback.")
            return {}

        # Collect the first English prefLabel for each concept URI from the JSON
        uri_to_en_label = {}
        all_uris = set()
        if labels:
            all_uris.update(labels.keys())
        if notes:
            all_uris.update(notes.keys())

        if labels:
            for concept_uri, label_list in labels.items():
                for lbl in label_list:
                    if (
                        lbl.get("language", "").lower().startswith("en")
                        and lbl.get("label_type") == "prefLabel"
                        and lbl.get("literal_form")
                    ):
                        uri_to_en_label[concept_uri] = lbl["literal_form"]
                        break

        # Build a reverse lookup: label text -> set of resource_ids
        # by querying all concept/scheme label tiles
        label_to_resources = defaultdict(set)
        label_nodegroups = [
            const.CONCEPT_NAME_NODEGROUP,
            const.SCHEME_NAME_NODEGROUP,
        ]
        content_nodes = [
            const.CONCEPT_NAME_CONTENT_NODE,
            const.SCHEME_NAME_CONTENT_NODE,
        ]
        label_tiles = TileModel.objects.filter(
            nodegroup_id__in=label_nodegroups,
            resourceinstance__graph_id__in=[
                const.CONCEPTS_GRAPH_ID,
                const.SCHEMES_GRAPH_ID,
            ],
        ).values_list("resourceinstance_id", "data")

        for resource_id, data in label_tiles.iterator():
            if not data:
                continue
            for cn in content_nodes:
                content = data.get(cn)
                if isinstance(content, str) and content:
                    label_to_resources[content].add(resource_id)
                    break

        # Match: concept_uri -> en_label -> resource_id
        # Only use unambiguous matches (label maps to exactly one resource)
        ambiguous = 0
        for concept_uri, en_label in uri_to_en_label.items():
            resource_ids = label_to_resources.get(en_label)
            if resource_ids and len(resource_ids) == 1:
                lookup[concept_uri] = next(iter(resource_ids))
            elif resource_ids and len(resource_ids) > 1:
                ambiguous += 1

        # For concept URIs that have notes but no labels, try the scheme
        # (the AAT scheme URI is http://vocab.getty.edu/aat/)
        scheme_uri = "http://vocab.getty.edu/aat/"
        if scheme_uri not in lookup and notes and scheme_uri in notes:
            # Try to find the scheme resource by its prefLabel
            scheme_rids = label_to_resources.get("Art & Architecture Thesaurus (AAT)")
            if scheme_rids and len(scheme_rids) == 1:
                lookup[scheme_uri] = next(iter(scheme_rids))

        self.stdout.write(
            f"  Matched {len(lookup)} of {len(all_uris)} concept URIs via labels"
            f" ({ambiguous} ambiguous, skipped)"
        )

        # Create URI tiles for matched resources so future runs can use them
        if lookup:
            self._create_uri_tiles(lookup)

        return lookup

    def _create_uri_tiles(self, concept_uri_to_resource):
        """Create URI tiles for concepts/schemes that don't have them yet."""
        self.stdout.write(
            f"  Creating URI tiles for {len(concept_uri_to_resource)} resources ..."
        )

        concept_ng = NodeGroup.objects.get(nodegroupid=const.URI_NODEGROUP)
        SCHEME_URI_NODEGROUP = "7fdc87bb-6ef9-4a74-8e84-4bde69557eef"
        SCHEME_URI_CONTENT_NODE = "1bd0f20b-b945-4231-b872-cba02cc4bc25"
        scheme_ng = NodeGroup.objects.get(nodegroupid=SCHEME_URI_NODEGROUP)

        # Check which resources already have URI tiles
        existing = set(
            TileModel.objects.filter(
                nodegroup_id__in=[const.URI_NODEGROUP, SCHEME_URI_NODEGROUP],
                resourceinstance_id__in=concept_uri_to_resource.values(),
            ).values_list("resourceinstance_id", flat=True)
        )

        # Determine graph for each resource so we use the right nodegroup
        resource_graphs = dict(
            ResourceInstance.objects.filter(
                resourceinstanceid__in=concept_uri_to_resource.values(),
            ).values_list("resourceinstanceid", "graph_id")
        )

        tiles_to_create = []
        for concept_uri, resource_id in concept_uri_to_resource.items():
            if resource_id in existing:
                continue
            graph_id = str(resource_graphs.get(resource_id, ""))
            if graph_id == const.SCHEMES_GRAPH_ID:
                nodegroup = scheme_ng
                content_node = SCHEME_URI_CONTENT_NODE
            else:
                nodegroup = concept_ng
                content_node = const.URI_CONTENT_NODE

            tiles_to_create.append(
                TileModel(
                    tileid=uuid.uuid4(),
                    nodegroup=nodegroup,
                    resourceinstance_id=resource_id,
                    data={content_node: concept_uri},
                    sortorder=0,
                )
            )

        if tiles_to_create:
            for i in range(0, len(tiles_to_create), BATCH_SIZE):
                TileModel.objects.bulk_create(tiles_to_create[i : i + BATCH_SIZE])
            self.stdout.write(f"  Created {len(tiles_to_create)} URI tiles")

    def _build_label_tile_lookup(self, concept_uri_to_resource):
        """
        Build {resource_id_str: {label_key: {tileid, data, graph_id}}} for label tiles.
        """
        resource_ids = set(concept_uri_to_resource.values())
        if not resource_ids:
            return {}

        # Query label tiles for both concept and scheme graphs
        label_nodegroups = [
            const.CONCEPT_NAME_NODEGROUP,
            const.SCHEME_NAME_NODEGROUP,
        ]
        # When we have many resources, filter by graph instead of individual IDs
        label_tiles = (
            TileModel.objects.filter(
                nodegroup_id__in=label_nodegroups,
                resourceinstance__graph_id__in=[
                    const.CONCEPTS_GRAPH_ID,
                    const.SCHEMES_GRAPH_ID,
                ],
            )
            .select_related("resourceinstance")
            .values_list(
                "tileid",
                "resourceinstance_id",
                "resourceinstance__graph_id",
                "data",
            )
        )

        lookup = defaultdict(dict)
        content_nodes = [
            const.CONCEPT_NAME_CONTENT_NODE,
            const.SCHEME_NAME_CONTENT_NODE,
        ]
        lang_nodes = [const.CONCEPT_NAME_LANGUAGE_NODE, const.SCHEME_NAME_LANGUAGE_NODE]

        for tile_id, resource_id, graph_id, data in label_tiles.iterator():
            if not data:
                continue
            if resource_id not in resource_ids:
                continue
            # Find content and language values
            content = None
            language = None
            for cn in content_nodes:
                if cn in data and data[cn]:
                    content = data[cn]
                    break
            for ln in lang_nodes:
                if ln in data and data[ln]:
                    lang_val = data[ln]
                    if isinstance(lang_val, str):
                        language = lang_val
                    elif isinstance(lang_val, dict):
                        language = lang_val.get("code") or lang_val.get("value")
                    break

            if content:
                key = self._make_label_key(content, language)
                lookup[str(resource_id)][key] = {
                    "tileid": tile_id,
                    "data": data,
                    "graph_id": graph_id,
                }

        self.stdout.write(f"  Found label tiles for {len(lookup)} resources")
        return lookup

    def _build_note_tile_lookup(self, concept_uri_to_resource):
        """
        Build {resource_id_str: {note_key: {tileid, data, graph_id}}} for note tiles.
        """
        resource_ids = set(concept_uri_to_resource.values())
        if not resource_ids:
            return {}

        note_nodegroups = [
            const.STATEMENT_NODEGROUP,
            SCHEME_STMT_NODEGROUP,
        ]
        note_tiles = (
            TileModel.objects.filter(
                nodegroup_id__in=note_nodegroups,
                resourceinstance__graph_id__in=[
                    const.CONCEPTS_GRAPH_ID,
                    const.SCHEMES_GRAPH_ID,
                ],
            )
            .select_related("resourceinstance")
            .values_list(
                "tileid",
                "resourceinstance_id",
                "resourceinstance__graph_id",
                "data",
            )
        )

        lookup = defaultdict(dict)
        content_node = const.STATEMENT_CONTENT_NODE
        lang_node = const.STATEMENT_LANGUAGE_NODE
        # Scheme statement nodes may differ — check both
        scheme_content_nodes = self._get_scheme_statement_content_nodes()

        for tile_id, resource_id, graph_id, data in note_tiles.iterator():
            if not data:
                continue
            if resource_id not in resource_ids:
                continue
            content = None
            language = None

            # Try concept statement nodes first
            if content_node in data and data[content_node]:
                content_val = data[content_node]
                if isinstance(content_val, dict):
                    content = (
                        content_val.get(next(iter(content_val)))
                        if len(content_val) == 1
                        else str(content_val)
                    )
                else:
                    content = str(content_val) if content_val else None
            # Try scheme statement nodes
            if not content:
                for cn in scheme_content_nodes:
                    if cn in data and data[cn]:
                        content = str(data[cn]) if data[cn] else None
                        break

            if lang_node in data and data[lang_node]:
                lang_val = data[lang_node]
                if isinstance(lang_val, str):
                    language = lang_val
                elif isinstance(lang_val, dict):
                    language = lang_val.get("code") or lang_val.get("value")

            if content:
                # Truncate content for the key to handle minor differences
                key = self._make_note_key(content, language)
                lookup[str(resource_id)][key] = {
                    "tileid": tile_id,
                    "data": data,
                    "graph_id": graph_id,
                }

        self.stdout.write(f"  Found note tiles for {len(lookup)} resources")
        return lookup

    def _get_scheme_statement_content_nodes(self):
        """Get content node IDs for scheme statement nodegroup."""
        nodes = Node.objects.filter(
            nodegroup_id=SCHEME_STMT_NODEGROUP,
            alias__contains="content",
        ).values_list("nodeid", flat=True)
        return [str(n) for n in nodes]

    @staticmethod
    def _make_label_key(content, language):
        """Create a matching key for a label tile."""
        # Normalize: strip whitespace, lowercase for matching
        c = (content or "").strip()[:200]
        l = (language or "").strip().lower()
        return f"{c}||{l}"

    @staticmethod
    def _make_note_key(content, language):
        """Create a matching key for a note tile."""
        # Use first 200 chars to match (notes can be very long)
        c = (content or "").strip()[:200]
        l = (language or "").strip().lower()
        return f"{c}||{l}"

    def _get_node_datatype(self, node_id):
        """Get the datatype for a node by its ID."""
        if not hasattr(self, "_node_datatype_cache"):
            self._node_datatype_cache = {}
        if node_id not in self._node_datatype_cache:
            try:
                node = Node.objects.get(nodeid=node_id)
                self._node_datatype_cache[node_id] = node.datatype
            except Node.DoesNotExist:
                self._node_datatype_cache[node_id] = "string"
        return self._node_datatype_cache[node_id]

    def _preload_node_datatypes(self, nodegroup_ids):
        """Bulk-load node datatypes for all nodes in the given nodegroups."""
        if not hasattr(self, "_node_datatype_cache"):
            self._node_datatype_cache = {}
        nodes = Node.objects.filter(
            nodegroup_id__in=nodegroup_ids,
        ).values_list("nodeid", "datatype")
        for nodeid, datatype in nodes:
            self._node_datatype_cache[str(nodeid)] = datatype

    def _get_blank_tile(self, nodegroup_id):
        """Build a blank tile value dict for a nodegroup."""
        nodes = Node.objects.filter(nodegroup_id=nodegroup_id).exclude(
            datatype="semantic"
        )

        blank = {}
        for node in nodes:
            blank[str(node.nodeid)] = {
                "value": None,
                "valid": True,
                "source": "",
                "notes": "",
                "datatype": node.datatype,
            }
        return blank

    def _get_default_lifecycle_state(self, graph_id):
        """Get the default lifecycle state for a graph."""
        from arches.app.models.models import (
            GraphModel,
            ResourceInstanceLifecycleState,
        )

        try:
            graph = GraphModel.objects.get(graphid=graph_id)
            if graph.resource_instance_lifecycle is None:
                return None
            return ResourceInstanceLifecycleState.objects.filter(
                resource_instance_lifecycle=graph.resource_instance_lifecycle,
                is_initial_state=True,
            ).first()
        except GraphModel.DoesNotExist:
            return None
