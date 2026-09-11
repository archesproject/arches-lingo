"""Tests for the direct tile-load path used by `load_aat`.

`--bypass-staging` replaces arches' `__arches_staging_to_tile` with COPY and
set-based SQL, so the rows that function would have written -- resources,
tiles, and the `resource_x_resource` entries derived from them -- are this
module's responsibility rather than core's.
"""

import uuid
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.db import connection
from django.test import TestCase

from arches.app.models.models import ResourceInstance, ResourceXResource, TileModel

from arches_lingo import const
from arches_lingo.etl_modules.migrate_to_lingo import LingoResourceImporter
from arches_lingo.utils.aat.direct_tile_load import (
    TileValidationError,
    build_tiledata,
    load_resources_and_tiles,
    merge_into_tiledata,
    tiledata_for_copy,
)
from arches_lingo.utils.concept_lifecycle import DRAFT_STATE_ID, LOCKED_STATE_ID

from tests.tests import ViewTests


def silent(message):
    """Stand in for the `log` callable the loaders print through."""


def register_migrate_to_lingo_etl_module():
    """`LingoResourceImporter` looks its ETLModule row up by slug on init."""
    from arches.management.commands.etl_module import Command as ETLModuleCommand

    ETLModuleCommand().register(
        source=str(Path(settings.APP_ROOT) / "etl_modules" / "migrate_to_lingo.py")
    )


class TiledataBuildTests(TestCase):
    def test_resource_references_get_a_cross_reference_id(self):
        """resource_x_resource is keyed on resourceXresourceId, so a reference
        written without one cannot be related back to its tile."""
        tiledata = build_tiledata(
            {
                "node-a": {
                    "value": [{"resourceId": "r1", "resourceXresourceId": ""}],
                    "datatype": "resource-instance-list",
                },
                "node-b": {"value": "plain", "datatype": "string"},
            }
        )
        self.assertNotEqual(tiledata["node-a"][0]["resourceXresourceId"], "")
        self.assertEqual(tiledata["node-b"], "plain")


class DirectWriteTestCase(TestCase):
    """Shared graph setup: the loaders write real tiles against real nodes."""

    @classmethod
    def setUpTestData(cls):
        ViewTests.load_controlled_lists()
        ViewTests.load_ontology()
        ViewTests.load_graphs()
        register_migrate_to_lingo_etl_module()

    def make_resource_row(self, resource_id, graph_id, lifecycle_state_id):
        return (
            str(resource_id),
            graph_id,
            str(resource_id),
            str(lifecycle_state_id),
        )

    def make_tile_row(self, resource_id, nodegroup_id, tiledata, sortorder=0):
        return (
            str(uuid.uuid4()),
            str(resource_id),
            nodegroup_id,
            sortorder,
            tiledata_for_copy(tiledata),
        )

    def part_of_scheme_reference(self, scheme_id, cross_reference_id):
        return {
            const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                {
                    "resourceId": str(scheme_id),
                    "ontologyProperty": const.TOP_CONCEPT_OF_ONTOLOGY_PROPERTY,
                    "inverseOntologyProperty": "",
                    "resourceXresourceId": str(cross_reference_id),
                }
            ]
        }


class LoadResourcesAndTilesTests(DirectWriteTestCase):
    def test_resources_and_tiles_are_written_with_the_requested_state(self):
        scheme_id = uuid.uuid4()
        concept_id = uuid.uuid4()

        counts = load_resources_and_tiles(
            [
                self.make_resource_row(
                    scheme_id, const.SCHEMES_GRAPH_ID, LOCKED_STATE_ID
                ),
                self.make_resource_row(
                    concept_id, const.CONCEPTS_GRAPH_ID, LOCKED_STATE_ID
                ),
            ],
            [
                self.make_tile_row(
                    concept_id,
                    const.URI_NODEGROUP,
                    {const.URI_CONTENT_NODE: "http://vocab.getty.edu/aat/300000001"},
                )
            ],
            [const.SCHEMES_GRAPH_ID, const.CONCEPTS_GRAPH_ID],
            log=silent,
        )

        self.assertEqual(counts, {"resources": 2, "tiles": 1})
        concept = ResourceInstance.objects.get(pk=concept_id)
        self.assertEqual(concept.graph_id, uuid.UUID(const.CONCEPTS_GRAPH_ID))
        self.assertEqual(concept.resource_instance_lifecycle_state_id, LOCKED_STATE_ID)
        self.assertIsNotNone(concept.createdtime)
        tile = TileModel.objects.get(resourceinstance_id=concept_id)
        self.assertEqual(
            tile.data[const.URI_CONTENT_NODE],
            "http://vocab.getty.edu/aat/300000001",
        )

    def test_resource_references_become_relationships_keyed_on_the_tile(self):
        """`__arches_refresh_tile_resource_relationships` is not called on this
        path, so the rows it would have derived are built here instead."""
        scheme_id = uuid.uuid4()
        concept_id = uuid.uuid4()
        cross_reference_id = uuid.uuid4()

        load_resources_and_tiles(
            [
                self.make_resource_row(
                    scheme_id, const.SCHEMES_GRAPH_ID, LOCKED_STATE_ID
                ),
                self.make_resource_row(
                    concept_id, const.CONCEPTS_GRAPH_ID, LOCKED_STATE_ID
                ),
            ],
            [
                self.make_tile_row(
                    concept_id,
                    const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                    self.part_of_scheme_reference(scheme_id, cross_reference_id),
                )
            ],
            [const.SCHEMES_GRAPH_ID, const.CONCEPTS_GRAPH_ID],
            log=silent,
        )

        relationship = ResourceXResource.objects.get(resourcexid=cross_reference_id)
        self.assertEqual(relationship.from_resource_id, concept_id)
        self.assertEqual(relationship.to_resource_id, scheme_id)
        self.assertEqual(
            relationship.relationshiptype, const.TOP_CONCEPT_OF_ONTOLOGY_PROPERTY
        )
        # __arches_update_resource_x_resource_with_graphids is likewise skipped.
        self.assertEqual(
            relationship.from_resource_graph_id,
            uuid.UUID(const.CONCEPTS_GRAPH_ID),
        )
        self.assertEqual(
            relationship.to_resource_graph_id,
            uuid.UUID(const.SCHEMES_GRAPH_ID),
        )

    def test_a_reference_without_a_cross_reference_id_still_relates(self):
        """Values that reach the loader unprepared must not be dropped."""
        scheme_id = uuid.uuid4()
        concept_id = uuid.uuid4()

        load_resources_and_tiles(
            [
                self.make_resource_row(
                    scheme_id, const.SCHEMES_GRAPH_ID, LOCKED_STATE_ID
                ),
                self.make_resource_row(
                    concept_id, const.CONCEPTS_GRAPH_ID, LOCKED_STATE_ID
                ),
            ],
            [
                self.make_tile_row(
                    concept_id,
                    const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                    self.part_of_scheme_reference(scheme_id, ""),
                )
            ],
            [const.SCHEMES_GRAPH_ID, const.CONCEPTS_GRAPH_ID],
            log=silent,
        )

        self.assertEqual(
            ResourceXResource.objects.filter(from_resource_id=concept_id).count(),
            1,
        )

    def test_rerunning_over_existing_ids_neither_fails_nor_duplicates(self):
        """A resumed load resends resources it already wrote."""
        concept_id = uuid.uuid4()
        resource_rows = [
            self.make_resource_row(concept_id, const.CONCEPTS_GRAPH_ID, LOCKED_STATE_ID)
        ]

        load_resources_and_tiles(
            resource_rows, [], [const.CONCEPTS_GRAPH_ID], log=silent
        )
        load_resources_and_tiles(
            resource_rows, [], [const.CONCEPTS_GRAPH_ID], log=silent
        )

        self.assertEqual(ResourceInstance.objects.filter(pk=concept_id).count(), 1)

    def test_tiles_on_graphs_outside_the_load_are_left_unrelated(self):
        """The relationship pass reads every tile on the nodegroup, so it is
        scoped to the graphs this load wrote."""
        scheme_id = uuid.uuid4()
        concept_id = uuid.uuid4()

        load_resources_and_tiles(
            [
                self.make_resource_row(
                    scheme_id, const.SCHEMES_GRAPH_ID, LOCKED_STATE_ID
                ),
                self.make_resource_row(
                    concept_id, const.CONCEPTS_GRAPH_ID, LOCKED_STATE_ID
                ),
            ],
            [
                self.make_tile_row(
                    concept_id,
                    const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                    self.part_of_scheme_reference(scheme_id, uuid.uuid4()),
                )
            ],
            [const.SCHEMES_GRAPH_ID],
            log=silent,
        )

        self.assertFalse(
            ResourceXResource.objects.filter(from_resource_id=concept_id).exists()
        )


class MergeIntoTiledataTests(DirectWriteTestCase):
    """Attribution adds two nodes to tiles that already exist, so the merge
    must leave the rest of `tiledata` alone."""

    def setUp(self):
        self.scheme = ResourceInstance.objects.create(
            graph_id=const.SCHEMES_GRAPH_ID, name="Merge Test Scheme"
        )
        self.concept = ResourceInstance.objects.create(
            graph_id=const.CONCEPTS_GRAPH_ID, name="Merge Test Concept"
        )
        self.label_tile = TileModel.objects.create(
            resourceinstance=self.concept,
            nodegroup_id=const.CONCEPT_NAME_NODEGROUP,
            data={
                const.CONCEPT_NAME_CONTENT_NODE: "trumpets",
                const.CONCEPT_NAME_LANGUAGE_NODE: "en",
            },
        )

    def source_reference(self, resource_id):
        return [
            {
                "resourceId": str(resource_id),
                "ontologyProperty": "",
                "inverseOntologyProperty": "",
                "resourceXresourceId": "",
            }
        ]

    def test_added_nodes_do_not_displace_the_nodes_already_on_the_tile(self):
        merged = merge_into_tiledata(
            [
                (
                    self.label_tile.pk,
                    {
                        const.CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE: self.source_reference(
                            self.scheme.pk
                        )
                    },
                )
            ],
            log=silent,
        )

        self.assertEqual(merged, 1)
        self.label_tile.refresh_from_db()
        self.assertEqual(
            self.label_tile.data[const.CONCEPT_NAME_CONTENT_NODE], "trumpets"
        )
        self.assertEqual(self.label_tile.data[const.CONCEPT_NAME_LANGUAGE_NODE], "en")
        self.assertEqual(
            self.label_tile.data[const.CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE][0][
                "resourceId"
            ],
            str(self.scheme.pk),
        )

    def test_references_are_given_a_cross_reference_id_and_a_relationship(self):
        merge_into_tiledata(
            [
                (
                    self.label_tile.pk,
                    {
                        const.CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE: self.source_reference(
                            self.scheme.pk
                        )
                    },
                )
            ],
            log=silent,
        )

        self.label_tile.refresh_from_db()
        cross_reference_id = self.label_tile.data[
            const.CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE
        ][0]["resourceXresourceId"]
        self.assertNotEqual(cross_reference_id, "")
        relationship = ResourceXResource.objects.get(resourcexid=cross_reference_id)
        self.assertEqual(relationship.tile_id, self.label_tile.pk)
        self.assertEqual(relationship.to_resource_id, self.scheme.pk)

    def test_several_additions_for_one_tile_are_combined_into_a_single_row(self):
        """Two attribution entries can resolve to the same tile when they share
        a literal form and language; sending both as rows violates the temp
        table's primary key."""
        other_scheme = ResourceInstance.objects.create(
            graph_id=const.SCHEMES_GRAPH_ID, name="Second Source"
        )

        merged = merge_into_tiledata(
            [
                (
                    self.label_tile.pk,
                    {
                        const.CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE: self.source_reference(
                            self.scheme.pk
                        )
                    },
                ),
                (
                    self.label_tile.pk,
                    {
                        const.CONCEPT_NAME_DATA_ASSIGNMENT_ACTOR_NODE: self.source_reference(
                            other_scheme.pk
                        )
                    },
                ),
            ],
            log=silent,
        )

        self.assertEqual(merged, 1)
        self.label_tile.refresh_from_db()
        self.assertIn(
            const.CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE, self.label_tile.data
        )
        self.assertIn(
            const.CONCEPT_NAME_DATA_ASSIGNMENT_ACTOR_NODE, self.label_tile.data
        )

    def test_merging_twice_replaces_the_relationships_it_wrote(self):
        """The merge deletes and rebuilds relationships for the tiles it
        touches, so a rerun must not leave the first pass's rows behind."""
        addition = [
            (
                self.label_tile.pk,
                {
                    const.CONCEPT_NAME_DATA_ASSIGNMENT_OBJ_USED_NODE: self.source_reference(
                        self.scheme.pk
                    )
                },
            )
        ]

        merge_into_tiledata(addition, log=silent)
        merge_into_tiledata(addition, log=silent)

        self.assertEqual(
            ResourceXResource.objects.filter(tile_id=self.label_tile.pk).count(), 1
        )

    def test_no_additions_touches_nothing(self):
        self.assertEqual(merge_into_tiledata([], log=silent), 0)


class LoadDirectlyTests(DirectWriteTestCase):
    """`load_directly` turns the SKOS reader's mock tiles into the rows the
    loaders above write, and is where validation happens."""

    def setUp(self):
        self.importer = LingoResourceImporter(
            loadid=str(uuid.uuid4()), bypass_staging=True
        )
        self.importer.log = silent
        self.nodegroup_lookup, nodes = self.importer.get_graph_tree(
            const.CONCEPTS_GRAPH_ID
        )
        self.node_lookup = self.importer.get_node_lookup(nodes)

    def make_concept(self, resource_id, *label_values):
        return {
            "resourceinstanceid": resource_id,
            "type": "Concept",
            "legacyid": str(resource_id),
            "tile_data": [
                LingoResourceImporter.create_mock_tile_from_value(
                    {
                        "value": label_value,
                        "valuetype_id": "prefLabel",
                        "language_id": "en",
                    },
                    lang_lookup={},
                )
                for label_value in label_values
            ],
        }

    def test_mock_tiles_become_resources_and_tiles(self):
        resource_id = uuid.uuid4()

        with connection.cursor() as cursor:
            counts = self.importer.load_directly(
                cursor,
                [self.make_concept(resource_id, "trumpets")],
                self.nodegroup_lookup,
                self.node_lookup,
            )

        self.assertEqual(counts["resources"], 1)
        self.assertEqual(counts["tiles"], 1)
        tile = TileModel.objects.get(resourceinstance_id=resource_id)
        self.assertEqual(tile.data[const.CONCEPT_NAME_CONTENT_NODE], "trumpets")

    def test_tiles_sharing_a_nodegroup_get_increasing_sortorder(self):
        """The descriptor for a concept is read from its first tile by
        sortorder, so the order the reader produced has to survive the load."""
        resource_id = uuid.uuid4()

        with connection.cursor() as cursor:
            self.importer.load_directly(
                cursor,
                [self.make_concept(resource_id, "trumpets", "clarions")],
                self.nodegroup_lookup,
                self.node_lookup,
            )

        sortorders = list(
            TileModel.objects.filter(
                resourceinstance_id=resource_id,
                nodegroup_id=const.CONCEPT_NAME_NODEGROUP,
            )
            .order_by("sortorder")
            .values_list("sortorder", flat=True)
        )
        self.assertEqual(sortorders, [0, 1])

    def test_resources_take_the_graphs_initial_lifecycle_state(self):
        """`_post_import_identifier_setup` moves them to the requested state
        afterwards; until then they hold what the graph starts them in."""
        resource_id = uuid.uuid4()

        with connection.cursor() as cursor:
            self.importer.load_directly(
                cursor,
                [self.make_concept(resource_id, "trumpets")],
                self.nodegroup_lookup,
                self.node_lookup,
            )

        concept = ResourceInstance.objects.get(pk=resource_id)
        self.assertEqual(concept.resource_instance_lifecycle_state_id, DRAFT_STATE_ID)

    def test_an_invalid_tile_stops_the_load_before_anything_is_written(self):
        """Staging records a bad value as a load error after the fact, against
        rows already written. Off that path the load has to fail first instead,
        so `create_tile_value` reporting a tile invalid must abort everything --
        including the resources of concepts that validated."""
        good_concept = self.make_concept(uuid.uuid4(), "trumpets")
        bad_concept = self.make_concept(uuid.uuid4(), "clarions")

        def reject_the_second_concept(cursor, mock_tile, *args, **kwargs):
            passes = mock_tile["appellative_status"] is not bad_tile
            return {}, passes

        bad_tile = bad_concept["tile_data"][0]["appellative_status"]
        with patch.object(
            self.importer, "create_tile_value", side_effect=reject_the_second_concept
        ):
            with connection.cursor() as cursor:
                with self.assertRaises(TileValidationError) as raised:
                    self.importer.load_directly(
                        cursor,
                        [good_concept, bad_concept],
                        self.nodegroup_lookup,
                        self.node_lookup,
                    )

        self.assertIn("1 value(s) failed validation", str(raised.exception))
        self.assertFalse(
            ResourceInstance.objects.filter(
                pk=good_concept["resourceinstanceid"]
            ).exists()
        )

    def test_nothing_to_load_is_not_an_error(self):
        with connection.cursor() as cursor:
            counts = self.importer.load_directly(
                cursor, [], self.nodegroup_lookup, self.node_lookup
            )

        self.assertEqual(counts, {"resources": 0, "tiles": 0})
