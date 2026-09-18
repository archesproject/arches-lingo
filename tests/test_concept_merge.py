import json
import uuid
from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase
from django.urls import reverse

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import EditLog, ResourceInstance, TileModel

from arches_lingo.const import (
    ALT_LABEL_URI,
    PREF_LABEL_URI,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CLASSIFICATION_STATUS_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    CONCEPT_TYPE_NODEGROUP,
    CONCEPT_TYPE_NODEID,
    CONCEPTS_GRAPH_ID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    LABEL_LIST_ID,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    SCHEMES_GRAPH_ID,
    STATEMENT_CONTENT_NODE,
    STATEMENT_LANGUAGE_NODE,
    STATEMENT_NODEGROUP,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.models import ConceptMerge
from arches_lingo.utils.concept_lifecycle import (
    DRAFT_STATE_ID,
    EDITING_STATE_ID,
    RETIRED_STATE_ID,
    STRATEGY_REPARENT_TO_SURVIVOR,
    get_broader_ids,
)
from arches_lingo.utils.concept_merge import (
    ConceptMergeError,
    build_tile_identity_key,
    copy_tiles_to_survivor,
    get_concept_merge_history,
    get_list_item_tile_value,
    merge_concepts,
    normalize_node_value,
    validate_merge,
    write_reciprocal_exact_match_tiles,
)
from tests.tests import ViewTests

# statement_data_assignment_statement: the only child nodegroup beneath a
# nodegroup an editor can select, so it is what proves child tiles are copied.
STATEMENT_CHILD_NODEGROUP = "bf73e59b-4888-11ee-8a8d-11afefc4bff7"
STATEMENT_CHILD_CONTENT_NODE = "bf73e66a-4888-11ee-8a8d-11afefc4bff7"

# "guide term" in the term_types list backing the concept type node.
GUIDE_TERM_LIST_ITEM_ID = "45fab276-7818-4c83-8dd8-43e4e862904c"

# These tests can be run from the command line via:
# python manage.py test tests.test_concept_merge --settings="tests.test_settings"


class NormalizeNodeValueTests(SimpleTestCase):
    def test_resource_instance_entries_reduce_to_resource_ids(self):
        node_value = [
            {"resourceId": "abc", "resourceXresourceId": "ignored"},
            {"resourceId": "def", "resourceXresourceId": "also-ignored"},
        ]
        self.assertEqual(normalize_node_value(node_value), ("abc", "def"))

    def test_reference_entries_reduce_to_uris(self):
        node_value = [{"uri": ALT_LABEL_URI, "labels": [{"value": "altLabel"}]}]
        self.assertEqual(normalize_node_value(node_value), (ALT_LABEL_URI,))

    def test_scalars_pass_through(self):
        self.assertEqual(normalize_node_value("Tapestry"), "Tapestry")
        self.assertIsNone(normalize_node_value(None))


class BuildTileIdentityKeyTests(SimpleTestCase):
    def test_unmapped_nodegroup_has_no_identity(self):
        self.assertIsNone(build_tile_identity_key(CONCEPT_TYPE_NODEGROUP, {}))

    def test_equivalent_tiles_share_a_key_despite_bookkeeping(self):
        first_key = build_tile_identity_key(
            CLASSIFICATION_STATUS_NODEGROUP,
            {
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                    {"resourceId": "parent-id", "resourceXresourceId": "one"}
                ]
            },
        )
        second_key = build_tile_identity_key(
            CLASSIFICATION_STATUS_NODEGROUP,
            {
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                    {"resourceId": "parent-id", "resourceXresourceId": "two"}
                ]
            },
        )
        self.assertEqual(first_key, second_key)


class ConceptMergeTestCase(ViewTests):
    """Shared fixture: two editable concepts in the scheme built by ViewTests."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.pref_label_value = (
            DataTypeFactory()
            .get_instance("reference")
            .transform_value_for_tile("prefLabel", controlledList=LABEL_LIST_ID)
        )

    def setUp(self):
        super().setUp()
        self.survivor = self.concepts[1]
        self.absorbed = self.concepts[2]
        ResourceInstance.objects.filter(
            pk__in=[self.survivor.pk, self.absorbed.pk]
        ).update(resource_instance_lifecycle_state_id=EDITING_STATE_ID)
        self.survivor.refresh_from_db()
        self.absorbed.refresh_from_db()

    def add_uri_tile(self, concept, uri):
        return TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=URI_NODEGROUP,
            data={URI_CONTENT_NODE: uri},
        )

    def add_label_tile(self, concept, content, label_type_value, language="en"):
        return TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: content,
                CONCEPT_NAME_TYPE_NODE: label_type_value,
                CONCEPT_NAME_LANGUAGE_NODE: language,
            },
        )

    def add_statement_tile(self, concept, content, language="en"):
        return TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=STATEMENT_NODEGROUP,
            data={
                STATEMENT_CONTENT_NODE: content,
                STATEMENT_LANGUAGE_NODE: language,
            },
        )

    def make_child_of(self, child, *parents):
        TileModel.objects.filter(
            resourceinstance=child, nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP
        ).delete()
        return TileModel.objects.create(
            resourceinstance=child,
            nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
            data={
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                    {"resourceId": str(parent.pk)} for parent in parents
                ]
            },
        )

    def survivor_tiles(self, nodegroup_id):
        return TileModel.objects.filter(
            resourceinstance=self.survivor, nodegroup_id=nodegroup_id
        )

    def assertMergeRejected(self, survivor, absorbed, status=None, **selections):
        with self.assertRaises(ConceptMergeError) as raised:
            validate_merge(survivor, absorbed, selections, False)
        if status is not None:
            self.assertEqual(raised.exception.status, status)
        return raised.exception


class CopyTilesToSurvivorTests(ConceptMergeTestCase):
    def test_cardinality_n_tile_is_copied_under_a_new_tileid(self):
        source_tile = self.add_statement_tile(self.absorbed, "A scope note.")

        copy_tiles_to_survivor(
            self.survivor, self.absorbed, [str(source_tile.tileid)], set(), uuid.uuid4()
        )

        copied_tiles = self.survivor_tiles(STATEMENT_NODEGROUP)
        self.assertEqual(copied_tiles.count(), 1)
        self.assertNotEqual(copied_tiles.first().tileid, source_tile.tileid)
        self.assertEqual(
            copied_tiles.first().data[STATEMENT_CONTENT_NODE], "A scope note."
        )
        self.assertTrue(TileModel.objects.filter(pk=source_tile.tileid).exists())

    def test_tile_the_survivor_already_holds_is_not_duplicated(self):
        self.add_statement_tile(self.survivor, "Shared note.")
        source_tile = self.add_statement_tile(self.absorbed, "Shared note.")

        copy_tiles_to_survivor(
            self.survivor, self.absorbed, [str(source_tile.tileid)], set(), uuid.uuid4()
        )

        self.assertEqual(self.survivor_tiles(STATEMENT_NODEGROUP).count(), 1)

    def test_cardinality_one_tile_overwrites_in_place(self):
        existing_tile = TileModel.objects.create(
            resourceinstance=self.survivor,
            nodegroup_id=CONCEPT_TYPE_NODEGROUP,
            data={CONCEPT_TYPE_NODEID: None},
        )
        guide_term_value = [get_list_item_tile_value(GUIDE_TERM_LIST_ITEM_ID)]
        source_tile = TileModel.objects.create(
            resourceinstance=self.absorbed,
            nodegroup_id=CONCEPT_TYPE_NODEGROUP,
            data={CONCEPT_TYPE_NODEID: guide_term_value},
        )

        copy_tiles_to_survivor(
            self.survivor, self.absorbed, [str(source_tile.tileid)], set(), uuid.uuid4()
        )

        survivor_type_tiles = self.survivor_tiles(CONCEPT_TYPE_NODEGROUP)
        self.assertEqual(survivor_type_tiles.count(), 1)
        self.assertEqual(survivor_type_tiles.first().tileid, existing_tile.tileid)
        self.assertEqual(
            normalize_node_value(survivor_type_tiles.first().data[CONCEPT_TYPE_NODEID]),
            normalize_node_value(guide_term_value),
        )

    def test_pref_label_is_demoted_to_alt_label_when_selected_for_demotion(self):
        source_tile = self.add_label_tile(
            self.absorbed, "Woven hanging", self.pref_label_value
        )

        copy_tiles_to_survivor(
            self.survivor,
            self.absorbed,
            [str(source_tile.tileid)],
            {str(source_tile.tileid)},
            uuid.uuid4(),
        )

        copied_tile = self.survivor_tiles(CONCEPT_NAME_NODEGROUP).get(
            data__contains={CONCEPT_NAME_CONTENT_NODE: "Woven hanging"}
        )
        self.assertEqual(
            normalize_node_value(copied_tile.data[CONCEPT_NAME_TYPE_NODE]),
            (ALT_LABEL_URI,),
        )

    def test_broader_tile_naming_only_the_survivor_is_not_copied(self):
        """Merging a child into its parent must not leave the survivor its own parent."""
        broader_tile = self.make_child_of(self.absorbed, self.survivor)

        copied_tiles = copy_tiles_to_survivor(
            self.survivor,
            self.absorbed,
            [str(broader_tile.tileid)],
            set(),
            uuid.uuid4(),
        )

        self.assertEqual(copied_tiles, [])
        self.assertNotIn(str(self.survivor.pk), get_broader_ids(str(self.survivor.pk)))

    def test_broader_tile_keeps_its_other_parents_when_the_survivor_is_stripped(self):
        other_parent = self.concepts[3]
        broader_tile = self.make_child_of(self.absorbed, self.survivor, other_parent)

        copy_tiles_to_survivor(
            self.survivor,
            self.absorbed,
            [str(broader_tile.tileid)],
            set(),
            uuid.uuid4(),
        )

        survivor_parents = get_broader_ids(str(self.survivor.pk))
        self.assertIn(str(other_parent.pk), survivor_parents)
        self.assertNotIn(str(self.survivor.pk), survivor_parents)

    def test_child_tiles_follow_their_parent(self):
        parent_tile = self.add_statement_tile(self.absorbed, "Note with assignment.")
        TileModel.objects.create(
            resourceinstance=self.absorbed,
            nodegroup_id=STATEMENT_CHILD_NODEGROUP,
            parenttile_id=parent_tile.tileid,
            data={STATEMENT_CHILD_CONTENT_NODE: "Assignment detail."},
        )

        copy_tiles_to_survivor(
            self.survivor, self.absorbed, [str(parent_tile.tileid)], set(), uuid.uuid4()
        )

        copied_parent = self.survivor_tiles(STATEMENT_NODEGROUP).get()
        copied_child = TileModel.objects.get(parenttile_id=copied_parent.tileid)
        self.assertEqual(copied_child.resourceinstance_id, self.survivor.pk)
        self.assertEqual(
            copied_child.data[STATEMENT_CHILD_CONTENT_NODE], "Assignment detail."
        )


class WriteReciprocalExactMatchTilesTests(ConceptMergeTestCase):
    def test_exact_match_is_recorded_on_both_concepts(self):
        self.add_uri_tile(self.survivor, "https://example.org/concepts/survivor")
        self.add_uri_tile(self.absorbed, "https://example.org/concepts/absorbed")

        write_reciprocal_exact_match_tiles(self.survivor, self.absorbed, uuid.uuid4())

        survivor_match = TileModel.objects.get(
            resourceinstance=self.survivor, nodegroup_id=MATCH_STATUS_NODEGROUP
        )
        absorbed_match = TileModel.objects.get(
            resourceinstance=self.absorbed, nodegroup_id=MATCH_STATUS_NODEGROUP
        )
        self.assertEqual(
            survivor_match.data[MATCH_STATUS_COMPARATE_NODE],
            "https://example.org/concepts/absorbed",
        )
        self.assertEqual(
            absorbed_match.data[MATCH_STATUS_COMPARATE_NODE],
            "https://example.org/concepts/survivor",
        )

    def test_nothing_is_written_when_a_concept_has_no_uri(self):
        self.add_uri_tile(self.survivor, "https://example.org/concepts/survivor")

        written_tiles = write_reciprocal_exact_match_tiles(
            self.survivor, self.absorbed, uuid.uuid4()
        )

        self.assertEqual(written_tiles, [])
        self.assertFalse(
            TileModel.objects.filter(nodegroup_id=MATCH_STATUS_NODEGROUP).exists()
        )

    def test_existing_exact_match_is_not_duplicated(self):
        self.add_uri_tile(self.survivor, "https://example.org/concepts/survivor")
        self.add_uri_tile(self.absorbed, "https://example.org/concepts/absorbed")
        edit_transaction_id = uuid.uuid4()

        write_reciprocal_exact_match_tiles(
            self.survivor, self.absorbed, edit_transaction_id
        )
        write_reciprocal_exact_match_tiles(
            self.survivor, self.absorbed, edit_transaction_id
        )

        self.assertEqual(
            TileModel.objects.filter(nodegroup_id=MATCH_STATUS_NODEGROUP).count(), 2
        )


class ValidateMergeTests(ConceptMergeTestCase):
    def test_concept_cannot_be_merged_into_itself(self):
        self.assertMergeRejected(self.survivor, self.survivor)

    def test_concepts_in_different_schemes_are_rejected(self):
        other_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Other Scheme"
        )
        outsider = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID,
            name="Outsider",
            resource_instance_lifecycle_state_id=EDITING_STATE_ID,
        )
        TileModel.objects.create(
            resourceinstance=outsider,
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {"resourceId": str(other_scheme.pk)}
                ]
            },
        )

        self.assertMergeRejected(self.survivor, outsider)

    def test_absorbed_concept_must_be_in_editing_state(self):
        ResourceInstance.objects.filter(pk=self.absorbed.pk).update(
            resource_instance_lifecycle_state_id=DRAFT_STATE_ID
        )
        self.absorbed.refresh_from_db()

        self.assertMergeRejected(
            self.survivor, self.absorbed, status=HTTPStatus.CONFLICT
        )

    def test_excluded_nodegroups_cannot_be_selected(self):
        uri_tile = self.add_uri_tile(
            self.absorbed, "https://example.org/concepts/absorbed"
        )

        error = self.assertMergeRejected(
            self.survivor, self.absorbed, tile_selections=[str(uri_tile.tileid)]
        )
        self.assertIn("uri", error.message)

    def test_tiles_belonging_to_another_concept_are_rejected(self):
        foreign_tile = self.add_statement_tile(self.concepts[3], "Elsewhere.")

        self.assertMergeRejected(
            self.survivor, self.absorbed, tile_selections=[str(foreign_tile.tileid)]
        )

    def test_survivor_label_demotions_must_belong_to_the_survivor(self):
        absorbed_label = self.add_label_tile(
            self.absorbed, "Theirs", self.pref_label_value
        )

        self.assertMergeRejected(
            self.survivor,
            self.absorbed,
            survivor_pref_label_demotions=[str(absorbed_label.tileid)],
        )

    def test_absorbed_label_demotions_must_belong_to_the_absorbed_concept(self):
        survivor_label = self.add_label_tile(
            self.survivor, "Mine", self.pref_label_value
        )

        self.assertMergeRejected(
            self.survivor,
            self.absorbed,
            pref_label_demotions=[str(survivor_label.tileid)],
        )

    def test_valid_merge_passes(self):
        source_tile = self.add_statement_tile(self.absorbed, "Copy me.")
        survivor_label = self.add_label_tile(
            self.survivor, "Mine", self.pref_label_value
        )
        validate_merge(
            self.survivor,
            self.absorbed,
            {
                "tile_selections": [str(source_tile.tileid)],
                "survivor_pref_label_demotions": [str(survivor_label.tileid)],
            },
            False,
        )


class MergeConceptsTests(ConceptMergeTestCase):
    def test_merge_records_its_selections_and_groups_its_edits(self):
        source_tile = self.add_statement_tile(self.absorbed, "Merged note.")
        selections = {
            "absorbed_concept_id": str(self.absorbed.pk),
            "tile_selections": [str(source_tile.tileid)],
            "create_exact_match_tiles": False,
        }

        concept_merge = merge_concepts(
            self.survivor, self.absorbed, selections, self.admin
        )

        self.assertEqual(concept_merge.survivor_concept_id, self.survivor.pk)
        self.assertEqual(concept_merge.absorbed_concept_id, self.absorbed.pk)
        self.assertEqual(concept_merge.user, self.admin)
        self.assertEqual(concept_merge.selections, selections)
        self.assertTrue(
            EditLog.objects.filter(
                transactionid=concept_merge.edit_transaction_id
            ).exists()
        )

    def test_exact_match_tiles_are_skipped_when_not_requested(self):
        merge_concepts(
            self.survivor,
            self.absorbed,
            {
                "absorbed_concept_id": str(self.absorbed.pk),
                "create_exact_match_tiles": False,
            },
            self.admin,
        )
        self.assertFalse(
            TileModel.objects.filter(nodegroup_id=MATCH_STATUS_NODEGROUP).exists()
        )


class DemoteSurvivorPrefLabelTests(ConceptMergeTestCase):
    def test_survivor_pref_label_steps_down_before_the_absorbed_one_arrives(self):
        survivor_label = self.add_label_tile(
            self.survivor, "Kept spelling", self.pref_label_value
        )
        absorbed_label = self.add_label_tile(
            self.absorbed, "Preferred spelling", self.pref_label_value
        )

        merge_concepts(
            self.survivor,
            self.absorbed,
            {
                "absorbed_concept_id": str(self.absorbed.pk),
                "tile_selections": [str(absorbed_label.tileid)],
                "survivor_pref_label_demotions": [str(survivor_label.tileid)],
                "create_exact_match_tiles": False,
            },
            self.admin,
        )

        survivor_label.refresh_from_db()
        self.assertEqual(
            normalize_node_value(survivor_label.data[CONCEPT_NAME_TYPE_NODE]),
            (ALT_LABEL_URI,),
        )
        copied_label = self.survivor_tiles(CONCEPT_NAME_NODEGROUP).get(
            data__contains={CONCEPT_NAME_CONTENT_NODE: "Preferred spelling"}
        )
        self.assertEqual(
            normalize_node_value(copied_label.data[CONCEPT_NAME_TYPE_NODE]),
            (PREF_LABEL_URI,),
        )


class ConceptMergeHistoryTests(ConceptMergeTestCase):
    def test_history_reads_from_both_sides_of_a_merge(self):
        merge_concepts(
            self.survivor,
            self.absorbed,
            {
                "absorbed_concept_id": str(self.absorbed.pk),
                "create_exact_match_tiles": False,
            },
            self.admin,
        )

        survivor_history = get_concept_merge_history(self.survivor.pk)
        absorbed_history = get_concept_merge_history(self.absorbed.pk)

        self.assertEqual(survivor_history[0]["direction"], "absorbed")
        self.assertEqual(
            survivor_history[0]["counterpart_concept_id"], str(self.absorbed.pk)
        )
        self.assertEqual(absorbed_history[0]["direction"], "merged_into")
        self.assertEqual(
            absorbed_history[0]["counterpart_concept_id"], str(self.survivor.pk)
        )

    def test_history_carries_labels_rather_than_the_resource_descriptor(self):
        merge_concepts(
            self.survivor,
            self.absorbed,
            {
                "absorbed_concept_id": str(self.absorbed.pk),
                "create_exact_match_tiles": False,
            },
            self.admin,
        )

        [entry] = get_concept_merge_history(self.survivor.pk)

        self.assertTrue(entry["counterpart_concept_labels"])
        label = entry["counterpart_concept_labels"][0]
        self.assertEqual(label["value"], "Concept 3")
        self.assertEqual(label["language_id"], "en")
        self.assertEqual(label["valuetype_id"], "prefLabel")

    def test_concept_never_merged_has_no_history(self):
        self.assertEqual(get_concept_merge_history(self.concepts[3].pk), [])


class MergeRetirementTests(ConceptMergeTestCase):
    """Retirement is part of the merge transaction, not a follow-up request."""

    def give_absorbed_a_child(self):
        child = self.concepts[3]
        self.make_child_of(child, self.absorbed)
        return child

    def test_merge_retires_and_hands_children_to_the_survivor(self):
        child = self.give_absorbed_a_child()
        source_tile = self.add_statement_tile(self.absorbed, "Carried over.")

        merge_concepts(
            self.survivor,
            self.absorbed,
            {
                "absorbed_concept_id": str(self.absorbed.pk),
                "tile_selections": [str(source_tile.tileid)],
                "create_exact_match_tiles": False,
                "retire_absorbed_concept": True,
                "retirement_strategy": STRATEGY_REPARENT_TO_SURVIVOR,
            },
            self.admin,
        )

        self.assertEqual(get_broader_ids(str(child.pk)), {str(self.survivor.pk)})
        self.absorbed.refresh_from_db()
        self.assertEqual(
            self.absorbed.resource_instance_lifecycle_state_id, RETIRED_STATE_ID
        )
        self.assertEqual(self.survivor_tiles(STATEMENT_NODEGROUP).count(), 1)

    def test_reparenting_to_the_survivor_never_makes_it_its_own_parent(self):
        self.make_child_of(self.survivor, self.absorbed)
        sibling = self.concepts[3]
        self.make_child_of(sibling, self.absorbed)

        merge_concepts(
            self.survivor,
            self.absorbed,
            {
                "absorbed_concept_id": str(self.absorbed.pk),
                "create_exact_match_tiles": False,
                "retire_absorbed_concept": True,
                "retirement_strategy": STRATEGY_REPARENT_TO_SURVIVOR,
            },
            self.admin,
        )

        self.assertNotIn(str(self.survivor.pk), get_broader_ids(str(self.survivor.pk)))
        self.assertEqual(get_broader_ids(str(sibling.pk)), {str(self.survivor.pk)})

    def test_absorbed_concept_stays_active_when_retirement_is_declined(self):
        merge_concepts(
            self.survivor,
            self.absorbed,
            {
                "absorbed_concept_id": str(self.absorbed.pk),
                "create_exact_match_tiles": False,
                "retire_absorbed_concept": False,
            },
            self.admin,
        )

        self.absorbed.refresh_from_db()
        self.assertEqual(
            self.absorbed.resource_instance_lifecycle_state_id, EDITING_STATE_ID
        )

    def test_retiring_a_parent_concept_requires_a_strategy(self):
        self.give_absorbed_a_child()

        self.assertMergeRejected(
            self.survivor,
            self.absorbed,
            retire_absorbed_concept=True,
        )

    def test_a_failed_retirement_rolls_the_whole_merge_back(self):
        source_tile = self.add_statement_tile(self.absorbed, "Should not survive.")

        with patch(
            "arches_lingo.utils.concept_merge.retire_concept",
            side_effect=RuntimeError("retirement blew up"),
        ):
            with self.assertRaises(RuntimeError):
                merge_concepts(
                    self.survivor,
                    self.absorbed,
                    {
                        "absorbed_concept_id": str(self.absorbed.pk),
                        "tile_selections": [str(source_tile.tileid)],
                        "create_exact_match_tiles": False,
                        "retire_absorbed_concept": True,
                    },
                    self.admin,
                )

        self.assertEqual(self.survivor_tiles(STATEMENT_NODEGROUP).count(), 0)
        self.assertFalse(ConceptMerge.objects.exists())


class ConceptMergeViewTests(ConceptMergeTestCase):
    """Tests for POST /api/lingo/concept/<pk>/merge."""

    def post_merge(self, survivor_pk, payload):
        return self.client.post(
            reverse("api-concept-merge", kwargs={"pk": survivor_pk}),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_unknown_concept_returns_404(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.post_merge(
                uuid.uuid4(), {"absorbed_concept_id": str(self.absorbed.pk)}
            )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_missing_absorbed_concept_id_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.post_merge(self.survivor.pk, {})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_non_editor_is_forbidden(self):
        self.client.force_login(
            User.objects.create_user(username="not-an-editor", password="x")
        )
        response = self.post_merge(
            self.survivor.pk, {"absorbed_concept_id": str(self.absorbed.pk)}
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_successful_merge_returns_the_audit_record(self):
        source_tile = self.add_statement_tile(self.absorbed, "Via the API.")

        response = self.post_merge(
            self.survivor.pk,
            {
                "absorbed_concept_id": str(self.absorbed.pk),
                "tile_selections": [str(source_tile.tileid)],
                "create_exact_match_tiles": False,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        body = json.loads(response.content)
        self.assertTrue(body["merged"])
        self.assertTrue(
            ConceptMerge.objects.filter(pk=body["concept_merge_id"]).exists()
        )
        self.assertEqual(self.survivor_tiles(STATEMENT_NODEGROUP).count(), 1)
