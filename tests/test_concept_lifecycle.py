import json
import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase
from django.urls import reverse

from arches_lingo.const import (
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
)
from arches_lingo.utils.concept_lifecycle import (
    DRAFT_STATE_ID,
    RETIRED_STATE_ID,
    delete_concept,
    get_all_descendant_ids,
    get_broader_ids,
    get_scheme_id_if_top_concept,
    orphan_children,
    reparent_children,
    retire_concept,
)
from tests.tests import ViewTests

# These tests can be run from the command line via:
# python manage.py test tests.test_concept_lifecycle --settings="tests.test_settings"

CONCEPT_A = str(uuid.uuid4())
CONCEPT_B = str(uuid.uuid4())
CONCEPT_C = str(uuid.uuid4())
SCHEME_S = str(uuid.uuid4())


def _mock_tile(resource_id=CONCEPT_A, broader_ids=None):
    tile = MagicMock()
    tile.resourceinstance_id = resource_id
    if broader_ids:
        broader_references = [{"resourceId": broader_id} for broader_id in broader_ids]
    else:
        broader_references = []
    tile.data = {
        CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: broader_references
    }
    return tile


class GetBroaderIdsTests(SimpleTestCase):
    @patch("arches_lingo.utils.concept_lifecycle.TileModel")
    def test_returns_broader_ids_from_tile_data(self, MockTileModel):
        MockTileModel.objects.filter.return_value = [
            _mock_tile(broader_ids=[CONCEPT_B, CONCEPT_C])
        ]
        self.assertEqual(get_broader_ids(CONCEPT_A), {CONCEPT_B, CONCEPT_C})

    @patch("arches_lingo.utils.concept_lifecycle.TileModel")
    def test_skips_entries_with_no_resource_id(self, MockTileModel):
        tile = _mock_tile()
        tile.data[CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID] = [
            {"resourceId": CONCEPT_B},
            {"resourceId": ""},
            {},
        ]
        MockTileModel.objects.filter.return_value = [tile]
        self.assertEqual(get_broader_ids(CONCEPT_A), {CONCEPT_B})

    @patch("arches_lingo.utils.concept_lifecycle.TileModel")
    def test_returns_empty_set_when_no_tiles(self, MockTileModel):
        MockTileModel.objects.filter.return_value = []
        self.assertEqual(get_broader_ids(CONCEPT_A), set())


class GetSchemeIdIfTopConceptTests(SimpleTestCase):
    @patch("arches_lingo.utils.concept_lifecycle.TileModel")
    def test_returns_scheme_id_for_top_concept(self, MockTileModel):
        tile = MagicMock()
        tile.data = {TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [{"resourceId": SCHEME_S}]}
        MockTileModel.objects.filter.return_value.first.return_value = tile
        self.assertEqual(get_scheme_id_if_top_concept(CONCEPT_A), SCHEME_S)

    @patch("arches_lingo.utils.concept_lifecycle.TileModel")
    def test_returns_none_when_not_a_top_concept(self, MockTileModel):
        MockTileModel.objects.filter.return_value.first.return_value = None
        self.assertIsNone(get_scheme_id_if_top_concept(CONCEPT_A))

    @patch("arches_lingo.utils.concept_lifecycle.TileModel")
    def test_returns_none_when_top_concept_tile_has_no_references(self, MockTileModel):
        tile = MagicMock()
        tile.data = {TOP_CONCEPT_OF_NODE_AND_NODEGROUP: []}
        MockTileModel.objects.filter.return_value.first.return_value = tile
        self.assertIsNone(get_scheme_id_if_top_concept(CONCEPT_A))


class GetAllDescendantIdsTests(SimpleTestCase):
    def test_returns_empty_for_leaf(self):
        with patch(
            "arches_lingo.utils.concept_lifecycle.get_narrower_ids", return_value=set()
        ):
            self.assertEqual(get_all_descendant_ids(CONCEPT_A), set())

    def test_traverses_multiple_levels(self):
        narrower_map = {CONCEPT_A: {CONCEPT_B}, CONCEPT_B: {CONCEPT_C}}
        with patch(
            "arches_lingo.utils.concept_lifecycle.get_narrower_ids",
            side_effect=lambda cid: narrower_map.get(cid, set()),
        ):
            self.assertEqual(get_all_descendant_ids(CONCEPT_A), {CONCEPT_B, CONCEPT_C})

    def test_handles_diamond_without_duplicates(self):
        concept_d = str(uuid.uuid4())
        narrower_map = {
            CONCEPT_A: {CONCEPT_B, CONCEPT_C},
            CONCEPT_B: {concept_d},
            CONCEPT_C: {concept_d},
        }
        with patch(
            "arches_lingo.utils.concept_lifecycle.get_narrower_ids",
            side_effect=lambda cid: narrower_map.get(cid, set()),
        ):
            self.assertEqual(
                get_all_descendant_ids(CONCEPT_A), {CONCEPT_B, CONCEPT_C, concept_d}
            )

    def test_terminates_on_cycle(self):
        narrower_map = {CONCEPT_A: {CONCEPT_B}, CONCEPT_B: {CONCEPT_A}}
        with patch(
            "arches_lingo.utils.concept_lifecycle.get_narrower_ids",
            side_effect=lambda cid: narrower_map.get(cid, set()),
        ):
            self.assertEqual(get_all_descendant_ids(CONCEPT_A), {CONCEPT_B})


class OrphanChildrenTests(SimpleTestCase):
    def test_removes_concept_from_broader_refs(self):
        tile = _mock_tile(resource_id=CONCEPT_B, broader_ids=[CONCEPT_A, CONCEPT_C])
        fetched = MagicMock(data={})

        with (
            patch("arches_lingo.utils.concept_lifecycle.TileModel") as MockTileModel,
            patch("arches_lingo.utils.concept_lifecycle.Tile") as MockTile,
        ):
            MockTileModel.objects.filter.return_value = [tile]
            MockTile.objects.get.return_value = fetched
            orphan_children(CONCEPT_A)

        MockTile.objects.get.assert_called_once_with(tileid=tile.tileid)
        saved_refs = fetched.data[CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID]
        self.assertEqual([r["resourceId"] for r in saved_refs], [CONCEPT_C])
        fetched.save.assert_called_once_with(request=None)

    def test_deletes_tile_when_no_broader_refs_remain(self):
        tile = _mock_tile(resource_id=CONCEPT_B, broader_ids=[CONCEPT_A])

        with (
            patch("arches_lingo.utils.concept_lifecycle.TileModel") as MockTileModel,
            patch("arches_lingo.utils.concept_lifecycle.Tile") as MockTile,
        ):
            MockTileModel.objects.filter.return_value = [tile]
            orphan_children(CONCEPT_A)

        tile.delete.assert_called_once()
        MockTile.objects.get.assert_not_called()


class ReparentChildrenTests(SimpleTestCase):
    def test_swaps_removed_concept_for_new_parent(self):
        tile = _mock_tile(resource_id=CONCEPT_C, broader_ids=[CONCEPT_A])
        fetched = MagicMock(data={})

        with (
            patch("arches_lingo.utils.concept_lifecycle.TileModel") as MockTileModel,
            patch("arches_lingo.utils.concept_lifecycle.Tile") as MockTile,
        ):
            MockTileModel.objects.filter.return_value = [tile]
            MockTile.objects.get.return_value = fetched
            reparent_children(CONCEPT_A, {CONCEPT_B}, scheme_id=None)

        MockTile.objects.get.assert_called_once_with(tileid=tile.tileid)
        saved_refs = fetched.data[CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID]
        self.assertEqual([r["resourceId"] for r in saved_refs], [CONCEPT_B])
        fetched.save.assert_called_once_with(request=None)

    def test_does_not_duplicate_parent_already_present(self):
        tile = _mock_tile(resource_id=CONCEPT_C, broader_ids=[CONCEPT_A, CONCEPT_B])
        fetched = MagicMock(data={})

        with (
            patch("arches_lingo.utils.concept_lifecycle.TileModel") as MockTileModel,
            patch("arches_lingo.utils.concept_lifecycle.Tile") as MockTile,
        ):
            MockTileModel.objects.filter.return_value = [tile]
            MockTile.objects.get.return_value = fetched
            reparent_children(CONCEPT_A, {CONCEPT_B}, scheme_id=None)

        saved_refs = fetched.data[CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID]
        self.assertEqual(
            len([r for r in saved_refs if r["resourceId"] == CONCEPT_B]), 1
        )

    def test_promotes_to_top_concept_when_no_parents_remain(self):
        tile = _mock_tile(resource_id=CONCEPT_B, broader_ids=[CONCEPT_A])

        with (
            patch("arches_lingo.utils.concept_lifecycle.TileModel") as MockTileModel,
            patch("arches_lingo.utils.concept_lifecycle.Tile") as MockTile,
        ):
            MockTileModel.objects.filter.return_value = [tile]
            reparent_children(CONCEPT_A, set(), scheme_id=SCHEME_S)

        tile.delete.assert_called_once()
        MockTile.assert_called_once_with(
            resourceinstance_id=CONCEPT_B,
            nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
            data={TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [{"resourceId": SCHEME_S}]},
        )
        MockTile.return_value.save.assert_called_once_with(request=None)

    def test_just_deletes_tile_when_no_parents_remain_and_no_scheme(self):
        tile = _mock_tile(resource_id=CONCEPT_B, broader_ids=[CONCEPT_A])

        with (
            patch("arches_lingo.utils.concept_lifecycle.TileModel") as MockTileModel,
            patch("arches_lingo.utils.concept_lifecycle.Tile") as MockTile,
        ):
            MockTileModel.objects.filter.return_value = [tile]
            reparent_children(CONCEPT_A, set(), scheme_id=None)

        tile.delete.assert_called_once()
        MockTile.assert_not_called()


class DeleteConceptTests(SimpleTestCase):
    def setUp(self):
        self.concept = MagicMock()
        self.concept.pk = uuid.uuid4()

    @patch("arches_lingo.utils.concept_lifecycle.ResourceInstance")
    def test_delete_children_deletes_descendants(self, MockResourceInstance):
        MockResourceInstance.objects.filter.return_value.exclude.return_value.exists.return_value = (
            False
        )
        with patch(
            "arches_lingo.utils.concept_lifecycle.get_all_descendant_ids",
            return_value={"child-id"},
        ):
            delete_concept(self.concept, "delete_children")
        MockResourceInstance.objects.filter.return_value.delete.assert_called_once()
        self.concept.delete.assert_called_once()

    @patch("arches_lingo.utils.concept_lifecycle.ResourceInstance")
    def test_delete_children_raises_when_published_descendants_exist(
        self, MockResourceInstance
    ):
        MockResourceInstance.objects.filter.return_value.exclude.return_value.exists.return_value = (
            True
        )
        with patch(
            "arches_lingo.utils.concept_lifecycle.get_all_descendant_ids",
            return_value={"child-id"},
        ):
            with self.assertRaises(ValueError):
                delete_concept(self.concept, "delete_children")
        self.concept.delete.assert_not_called()

    @patch("arches_lingo.utils.concept_lifecycle.reparent_children")
    def test_reparent_calls_reparent_children(self, mock_reparent):
        with (
            patch(
                "arches_lingo.utils.concept_lifecycle.get_broader_ids",
                return_value={CONCEPT_B},
            ),
            patch(
                "arches_lingo.utils.concept_lifecycle.get_scheme_id_if_top_concept",
                return_value=SCHEME_S,
            ),
        ):
            delete_concept(self.concept, "reparent")
        mock_reparent.assert_called_once_with(
            str(self.concept.pk), {CONCEPT_B}, SCHEME_S
        )
        self.concept.delete.assert_called_once()

    @patch("arches_lingo.utils.concept_lifecycle.orphan_children")
    def test_orphan_calls_orphan_children(self, mock_orphan):
        delete_concept(self.concept, "orphan")
        mock_orphan.assert_called_once_with(str(self.concept.pk))
        self.concept.delete.assert_called_once()


class RetireConceptTests(SimpleTestCase):
    def setUp(self):
        self.concept = MagicMock()
        self.concept.pk = uuid.uuid4()

    @patch("arches_lingo.utils.concept_lifecycle.ResourceInstance")
    def test_delete_children_retires_descendants(self, MockResourceInstance):
        with patch(
            "arches_lingo.utils.concept_lifecycle.get_all_descendant_ids",
            return_value={"child-id"},
        ):
            retire_concept(self.concept, "delete_children")
        MockResourceInstance.objects.filter.return_value.update.assert_called_once_with(
            resource_instance_lifecycle_state_id=RETIRED_STATE_ID
        )

    @patch("arches_lingo.utils.concept_lifecycle.reparent_children")
    def test_reparent_calls_reparent_children(self, mock_reparent):
        with (
            patch(
                "arches_lingo.utils.concept_lifecycle.get_broader_ids",
                return_value={CONCEPT_B},
            ),
            patch(
                "arches_lingo.utils.concept_lifecycle.get_scheme_id_if_top_concept",
                return_value=None,
            ),
        ):
            retire_concept(self.concept, "reparent")
        mock_reparent.assert_called_once_with(str(self.concept.pk), {CONCEPT_B}, None)

    @patch("arches_lingo.utils.concept_lifecycle.orphan_children")
    def test_orphan_calls_orphan_children(self, mock_orphan):
        retire_concept(self.concept, "orphan")
        mock_orphan.assert_called_once_with(str(self.concept.pk))

    def test_concept_is_marked_retired_after_strategy(self):
        with patch("arches_lingo.utils.concept_lifecycle.orphan_children"):
            retire_concept(self.concept, "orphan")
        self.assertEqual(
            self.concept.resource_instance_lifecycle_state_id, RETIRED_STATE_ID
        )
        self.concept.save.assert_called_once_with(
            update_fields=["resource_instance_lifecycle_state"]
        )


class ConceptDeleteViewTests(ViewTests):
    """Tests for DELETE /api/lingo/concept/<pk>/delete."""

    def test_unknown_concept_returns_404(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.delete(
                reverse("api-concept-delete", kwargs={"pk": uuid.uuid4()})
            )
        self.assertEqual(response.status_code, 404)

    def test_non_draft_concept_cannot_be_deleted(self):
        # Concepts in setUpTestData have no lifecycle state (None ≠ DRAFT_STATE_ID).
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.delete(
                reverse("api-concept-delete", kwargs={"pk": self.concepts[0].pk})
            )
        self.assertEqual(response.status_code, 400)

    def test_non_editor_cannot_delete(self):
        self.client.force_login(
            User.objects.create_user(username="rando", password="x")
        )
        response = self.client.delete(
            reverse("api-concept-delete", kwargs={"pk": self.concepts[0].pk})
        )
        self.assertEqual(response.status_code, 403)

    @patch("arches_lingo.views.api.concepts.delete_concept")
    @patch("arches_lingo.views.api.concepts.ResourceInstance.objects.get")
    def test_draft_concept_with_children_requires_strategy(self, mock_get, mock_delete):
        mock_get.return_value = MagicMock(
            resource_instance_lifecycle_state_id=DRAFT_STATE_ID
        )
        with patch(
            "arches_lingo.views.api.concepts.get_narrower_ids",
            return_value={"some-child"},
        ):
            with self.assertLogs("django.request", level="WARNING"):
                response = self.client.delete(
                    reverse("api-concept-delete", kwargs={"pk": uuid.uuid4()})
                )
        self.assertEqual(response.status_code, 400)
        mock_delete.assert_not_called()

    @patch("arches_lingo.views.api.concepts.delete_concept")
    @patch("arches_lingo.views.api.concepts.ResourceInstance.objects.get")
    def test_draft_leaf_concept_deleted(self, mock_get, mock_delete):
        mock_concept = MagicMock(resource_instance_lifecycle_state_id=DRAFT_STATE_ID)
        mock_get.return_value = mock_concept
        with patch(
            "arches_lingo.views.api.concepts.get_narrower_ids", return_value=set()
        ):
            response = self.client.delete(
                reverse("api-concept-delete", kwargs={"pk": uuid.uuid4()})
            )
        self.assertEqual(response.status_code, 200)
        mock_delete.assert_called_once_with(mock_concept, None)

    @patch("arches_lingo.views.api.concepts.ResourceInstance.objects.get")
    def test_delete_children_with_published_descendants_returns_400(self, mock_get):
        mock_get.return_value = MagicMock(
            resource_instance_lifecycle_state_id=DRAFT_STATE_ID
        )
        with (
            patch(
                "arches_lingo.views.api.concepts.get_narrower_ids",
                return_value={"some-child"},
            ),
            patch(
                "arches_lingo.views.api.concepts.delete_concept",
                side_effect=ValueError("published descendants"),
            ),
        ):
            with self.assertLogs("django.request", level="WARNING"):
                response = self.client.delete(
                    reverse("api-concept-delete", kwargs={"pk": uuid.uuid4()}),
                    QUERY_STRING="strategy=delete_children",
                )
        self.assertEqual(response.status_code, 400)


class ConceptRetireViewTests(ViewTests):
    """Tests for POST /api/lingo/concept/<pk>/retire."""

    def test_unknown_concept_returns_404(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-concept-retire", kwargs={"pk": uuid.uuid4()})
            )
        self.assertEqual(response.status_code, 404)

    def test_concept_with_children_requires_strategy(self):
        # concepts[0] has children in the test data.
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-concept-retire", kwargs={"pk": self.concepts[0].pk})
            )
        self.assertEqual(response.status_code, 400)

    def test_invalid_strategy_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-concept-retire", kwargs={"pk": self.concepts[0].pk}),
                QUERY_STRING="strategy=bogus",
            )
        self.assertEqual(response.status_code, 400)

    def test_non_editor_cannot_retire(self):
        self.client.force_login(
            User.objects.create_user(username="rando2", password="x")
        )
        response = self.client.post(
            reverse("api-concept-retire", kwargs={"pk": self.concepts[0].pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_leaf_concept_can_be_retired_without_strategy(self):
        with (
            patch(
                "arches_lingo.views.api.concept_lifecycle.get_narrower_ids",
                return_value=set(),
            ),
            patch("arches_lingo.views.api.concept_lifecycle.retire_concept"),
        ):
            response = self.client.post(
                reverse("api-concept-retire", kwargs={"pk": self.concepts[0].pk})
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)["retired"])

    @patch("arches_lingo.views.api.concept_lifecycle.retire_concept")
    def test_each_valid_strategy_is_accepted(self, mock_retire):
        for strategy in ("orphan", "reparent", "delete_children"):
            with self.subTest(strategy=strategy):
                response = self.client.post(
                    reverse("api-concept-retire", kwargs={"pk": self.concepts[0].pk}),
                    QUERY_STRING=f"strategy={strategy}",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(mock_retire.call_args.args[1], strategy)
