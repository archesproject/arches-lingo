import uuid
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase, TestCase

from arches_lingo.const import (
    RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,
    RELATION_STATUS_ASCRIBED_RELATION_NODEID,
    RELATION_STATUS_DATA_ASSIGNMENT_ACTOR_NODEID,
    RELATION_STATUS_DATA_ASSIGNMENT_OBJECT_USED_NODEID,
    RELATION_STATUS_DATA_ASSIGNMENT_TYPE_NODEID,
    RELATION_STATUS_NODEGROUP,
    RELATION_STATUS_STATUS_METATYPE_NODEID,
    RELATION_STATUS_STATUS_NODEID,
    RELATION_STATUS_TIMESPAN_BEGIN_OF_THE_BEGIN_NODEID,
    RELATION_STATUS_TIMESPAN_END_OF_THE_END_NODEID,
)
from arches_lingo.functions.reciprocal_relationship import (
    RECIPROCAL_SYNC_CONTEXT,
    ReciprocalRelationshipFunction,
    _thread_local,
)

# These tests can be run from the command line via:
# python manage.py test tests.test_reciprocal_relationship --settings="tests.test_settings"

RESOURCE_A = str(uuid.uuid4())
RESOURCE_B = str(uuid.uuid4())


def _make_tile(
    resource_id=RESOURCE_A, nodegroup_id=RELATION_STATUS_NODEGROUP, data=None
):
    """Build a minimal mock Tile for use in function tests."""
    tile = MagicMock()
    tile.tileid = uuid.uuid4()
    tile.resourceinstance_id = resource_id
    tile.nodegroup_id = nodegroup_id
    tile.data = data or {}
    return tile


def _comparate(resource_id):
    """Build a list-format comparate value pointing to resource_id."""
    return [
        {
            "resourceId": resource_id,
            "ontologyProperty": "",
            "inverseOntologyProperty": "",
        }
    ]


class GetRelatedResourceIdTests(SimpleTestCase):
    """Unit tests for _get_related_resource_id — no DB required."""

    def setUp(self):
        self.fn = ReciprocalRelationshipFunction()

    def test_list_format_returns_resource_id(self):
        data = [{"resourceId": RESOURCE_B}]
        self.assertEqual(self.fn._get_related_resource_id(data), RESOURCE_B)

    def test_dict_format_returns_resource_id(self):
        data = {"resourceId": RESOURCE_B}
        self.assertEqual(self.fn._get_related_resource_id(data), RESOURCE_B)

    def test_empty_list_returns_none(self):
        self.assertIsNone(self.fn._get_related_resource_id([]))

    def test_list_with_non_dict_items_returns_none(self):
        self.assertIsNone(self.fn._get_related_resource_id(["not-a-dict"]))

    def test_dict_with_empty_resource_id_returns_none(self):
        self.assertIsNone(self.fn._get_related_resource_id({"resourceId": ""}))

    def test_dict_missing_resource_id_returns_none(self):
        self.assertIsNone(self.fn._get_related_resource_id({}))

    def test_none_returns_none(self):
        self.assertIsNone(self.fn._get_related_resource_id(None))

    def test_non_list_non_dict_returns_none(self):
        self.assertIsNone(self.fn._get_related_resource_id("just-a-string"))

    def test_resource_id_coerced_to_string(self):
        uid = uuid.uuid4()
        result = self.fn._get_related_resource_id([{"resourceId": uid}])
        self.assertEqual(result, str(uid))


class BuildComparateValueTests(SimpleTestCase):
    """Unit tests for _build_comparate_value — no DB required."""

    def setUp(self):
        self.fn = ReciprocalRelationshipFunction()

    def test_returns_list_with_one_entry(self):
        result = self.fn._build_comparate_value(RESOURCE_B)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    def test_resource_id_set_correctly(self):
        result = self.fn._build_comparate_value(RESOURCE_B)
        self.assertEqual(result[0]["resourceId"], RESOURCE_B)

    def test_contains_required_keys(self):
        result = self.fn._build_comparate_value(RESOURCE_B)
        entry = result[0]
        self.assertIn("ontologyProperty", entry)
        self.assertIn("inverseOntologyProperty", entry)
        self.assertIn("resourceXresourceId", entry)

    def test_resource_x_resource_id_is_valid_uuid(self):
        result = self.fn._build_comparate_value(RESOURCE_B)
        # Should not raise
        uuid.UUID(result[0]["resourceXresourceId"])


class BuildCounterpartDataTests(SimpleTestCase):
    """Unit tests for _build_counterpart_data — no DB required."""

    def setUp(self):
        self.fn = ReciprocalRelationshipFunction()
        self.source_tile = _make_tile(
            resource_id=RESOURCE_A,
            data={
                RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_B),
                RELATION_STATUS_ASCRIBED_RELATION_NODEID: "related",
                RELATION_STATUS_STATUS_NODEID: "active",
                RELATION_STATUS_STATUS_METATYPE_NODEID: None,
                RELATION_STATUS_TIMESPAN_BEGIN_OF_THE_BEGIN_NODEID: "2020-01-01",
                RELATION_STATUS_TIMESPAN_END_OF_THE_END_NODEID: None,
                RELATION_STATUS_DATA_ASSIGNMENT_ACTOR_NODEID: None,
                RELATION_STATUS_DATA_ASSIGNMENT_OBJECT_USED_NODEID: None,
                RELATION_STATUS_DATA_ASSIGNMENT_TYPE_NODEID: None,
            },
        )

    def test_comparate_points_back_to_source(self):
        data = self.fn._build_counterpart_data(self.source_tile, RESOURCE_A)
        comparate = data[RELATION_STATUS_ASCRIBED_COMPARATE_NODEID]
        self.assertEqual(comparate[0]["resourceId"], RESOURCE_A)

    def test_mirrored_nodes_are_copied(self):
        data = self.fn._build_counterpart_data(self.source_tile, RESOURCE_A)
        self.assertEqual(data[RELATION_STATUS_ASCRIBED_RELATION_NODEID], "related")
        self.assertEqual(data[RELATION_STATUS_STATUS_NODEID], "active")
        self.assertEqual(
            data[RELATION_STATUS_TIMESPAN_BEGIN_OF_THE_BEGIN_NODEID], "2020-01-01"
        )

    def test_absent_mirrored_nodes_set_to_none(self):
        # Source tile has no data for STATUS_METATYPE — should be None in output
        data = self.fn._build_counterpart_data(self.source_tile, RESOURCE_A)
        self.assertIsNone(data[RELATION_STATUS_STATUS_METATYPE_NODEID])

    def test_mirrored_node_values_are_deep_copied(self):
        mutable_value = {"key": "original"}
        self.source_tile.data[RELATION_STATUS_ASCRIBED_RELATION_NODEID] = mutable_value

        data = self.fn._build_counterpart_data(self.source_tile, RESOURCE_A)

        # Mutating the original should not affect the copy
        mutable_value["key"] = "mutated"
        self.assertEqual(
            data[RELATION_STATUS_ASCRIBED_RELATION_NODEID]["key"], "original"
        )

    def test_all_mirrored_node_ids_present_in_output(self):
        data = self.fn._build_counterpart_data(self.source_tile, RESOURCE_A)
        for node_id in self.fn.MIRRORED_NODES:
            self.assertIn(node_id, data)


class FindCounterpartTileTests(SimpleTestCase):
    """Unit tests for _find_counterpart_tile, mocking Tile.objects."""

    def setUp(self):
        self.fn = ReciprocalRelationshipFunction()

    def _make_db_tile(self, comparate_resource_id):
        tile = MagicMock()
        tile.data = {
            RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(comparate_resource_id)
        }
        return tile

    @patch("arches_lingo.functions.reciprocal_relationship.Tile")
    def test_returns_matching_tile(self, MockTile):
        matching = self._make_db_tile(RESOURCE_A)
        MockTile.objects.filter.return_value = [matching]

        result = self.fn._find_counterpart_tile(RESOURCE_B, RESOURCE_A)

        self.assertIs(result, matching)
        MockTile.objects.filter.assert_called_once_with(
            resourceinstance_id=RESOURCE_B,
            nodegroup_id=RELATION_STATUS_NODEGROUP,
        )

    @patch("arches_lingo.functions.reciprocal_relationship.Tile")
    def test_returns_none_when_no_tiles_exist(self, MockTile):
        MockTile.objects.filter.return_value = []
        result = self.fn._find_counterpart_tile(RESOURCE_B, RESOURCE_A)
        self.assertIsNone(result)

    @patch("arches_lingo.functions.reciprocal_relationship.Tile")
    def test_returns_none_when_no_tile_points_back(self, MockTile):
        # Tile exists but comparate points elsewhere, not back to RESOURCE_A
        other = self._make_db_tile(str(uuid.uuid4()))
        MockTile.objects.filter.return_value = [other]

        result = self.fn._find_counterpart_tile(RESOURCE_B, RESOURCE_A)
        self.assertIsNone(result)

    @patch("arches_lingo.functions.reciprocal_relationship.Tile")
    def test_returns_first_matching_tile_among_many(self, MockTile):
        non_match = self._make_db_tile(str(uuid.uuid4()))
        matching = self._make_db_tile(RESOURCE_A)
        MockTile.objects.filter.return_value = [non_match, matching]

        result = self.fn._find_counterpart_tile(RESOURCE_B, RESOURCE_A)
        self.assertIs(result, matching)


class PostSaveTests(SimpleTestCase):
    """Unit tests for post_save, mocking Tile operations."""

    def setUp(self):
        self.fn = ReciprocalRelationshipFunction()
        # Ensure thread-local guards are clean before each test
        _thread_local.syncing_save = False

    def _source_tile(
        self, resource_id=RESOURCE_A, nodegroup_id=RELATION_STATUS_NODEGROUP
    ):
        return _make_tile(
            resource_id=resource_id,
            nodegroup_id=nodegroup_id,
            data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_B)},
        )

    def test_skips_when_context_is_reciprocal_sync(self):
        tile = self._source_tile()
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.post_save(tile, request=None, context=RECIPROCAL_SYNC_CONTEXT)
            mock_find.assert_not_called()

    def test_skips_when_thread_local_syncing(self):
        _thread_local.syncing_save = True
        tile = self._source_tile()
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.post_save(tile, request=None)
            mock_find.assert_not_called()
        _thread_local.syncing_save = False

    def test_skips_when_wrong_nodegroup(self):
        tile = self._source_tile(nodegroup_id="different-nodegroup")
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.post_save(tile, request=None)
            mock_find.assert_not_called()

    def test_skips_when_no_comparate_data(self):
        tile = _make_tile(data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: None})
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.post_save(tile, request=None)
            mock_find.assert_not_called()

    def test_skips_when_comparate_is_empty_list(self):
        tile = _make_tile(data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: []})
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.post_save(tile, request=None)
            mock_find.assert_not_called()

    def test_skips_when_self_referential(self):
        # comparate points to the same resource as the tile's resource
        tile = _make_tile(
            resource_id=RESOURCE_A,
            data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_A)},
        )
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.post_save(tile, request=None)
            mock_find.assert_not_called()

    def test_creates_counterpart_when_none_exists(self):
        tile = self._source_tile()
        with (
            patch.object(
                self.fn, "_find_counterpart_tile", return_value=None
            ) as mock_find,
            patch.object(self.fn, "_create_counterpart_tile") as mock_create,
            patch.object(self.fn, "_update_counterpart_tile") as mock_update,
        ):
            self.fn.post_save(tile, request=None)
            mock_find.assert_called_once_with(RESOURCE_B, RESOURCE_A)
            mock_create.assert_called_once_with(tile, RESOURCE_B, RESOURCE_A)
            mock_update.assert_not_called()

    def test_updates_existing_counterpart(self):
        tile = self._source_tile()
        existing = _make_tile(resource_id=RESOURCE_B)
        with (
            patch.object(self.fn, "_find_counterpart_tile", return_value=existing),
            patch.object(self.fn, "_create_counterpart_tile") as mock_create,
            patch.object(self.fn, "_update_counterpart_tile") as mock_update,
        ):
            self.fn.post_save(tile, request=None)
            mock_update.assert_called_once_with(tile, existing, RESOURCE_A)
            mock_create.assert_not_called()

    def test_thread_local_guard_released_after_success(self):
        tile = self._source_tile()
        with (
            patch.object(self.fn, "_find_counterpart_tile", return_value=None),
            patch.object(self.fn, "_create_counterpart_tile"),
        ):
            self.fn.post_save(tile, request=None)
        self.assertFalse(getattr(_thread_local, "syncing_save", False))

    def test_thread_local_guard_released_after_exception(self):
        tile = self._source_tile()
        with (
            patch.object(self.fn, "_find_counterpart_tile", return_value=None),
            patch.object(self.fn, "_create_counterpart_tile", side_effect=RuntimeError),
        ):
            with self.assertRaises(RuntimeError):
                self.fn.post_save(tile, request=None)
        self.assertFalse(getattr(_thread_local, "syncing_save", False))


class DeleteTests(SimpleTestCase):
    """Unit tests for delete, mocking Tile operations."""

    def setUp(self):
        self.fn = ReciprocalRelationshipFunction()
        _thread_local.syncing_delete = False

    def _source_tile(
        self, resource_id=RESOURCE_A, nodegroup_id=RELATION_STATUS_NODEGROUP
    ):
        return _make_tile(
            resource_id=resource_id,
            nodegroup_id=nodegroup_id,
            data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_B)},
        )

    def test_skips_when_thread_local_syncing(self):
        _thread_local.syncing_delete = True
        tile = self._source_tile()
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.delete(tile, request=None)
            mock_find.assert_not_called()
        _thread_local.syncing_delete = False

    def test_skips_when_wrong_nodegroup(self):
        tile = self._source_tile(nodegroup_id="other-nodegroup")
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.delete(tile, request=None)
            mock_find.assert_not_called()

    def test_skips_when_no_comparate_data(self):
        tile = _make_tile(data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: None})
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.delete(tile, request=None)
            mock_find.assert_not_called()

    def test_skips_when_self_referential(self):
        tile = _make_tile(
            resource_id=RESOURCE_A,
            data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_A)},
        )
        with patch.object(self.fn, "_find_counterpart_tile") as mock_find:
            self.fn.delete(tile, request=None)
            mock_find.assert_not_called()

    def test_skips_when_no_counterpart_tile(self):
        tile = self._source_tile()
        with patch.object(self.fn, "_find_counterpart_tile", return_value=None):
            counterpart = MagicMock()
            # Should not call delete on the (nonexistent) counterpart
            self.fn.delete(tile, request=None)
            counterpart.delete.assert_not_called()

    def test_deletes_counterpart_tile(self):
        tile = self._source_tile()
        counterpart = _make_tile(resource_id=RESOURCE_B)
        request = MagicMock()
        with patch.object(self.fn, "_find_counterpart_tile", return_value=counterpart):
            self.fn.delete(tile, request=request)
            counterpart.delete.assert_called_once_with(request=request)

    def test_thread_local_guard_released_after_successful_delete(self):
        tile = self._source_tile()
        counterpart = _make_tile(resource_id=RESOURCE_B)
        with patch.object(self.fn, "_find_counterpart_tile", return_value=counterpart):
            self.fn.delete(tile, request=None)
        self.assertFalse(getattr(_thread_local, "syncing_delete", False))

    def test_thread_local_guard_released_after_delete_exception(self):
        tile = self._source_tile()
        counterpart = _make_tile(resource_id=RESOURCE_B)
        counterpart.delete.side_effect = RuntimeError("DB error")
        with patch.object(self.fn, "_find_counterpart_tile", return_value=counterpart):
            # Exception is caught internally, so it should not propagate
            self.fn.delete(tile, request=None)
        self.assertFalse(getattr(_thread_local, "syncing_delete", False))


class CreateCounterpartTileTests(SimpleTestCase):
    """Unit tests for _create_counterpart_tile, mocking Tile construction."""

    def setUp(self):
        self.fn = ReciprocalRelationshipFunction()

    @patch("arches_lingo.functions.reciprocal_relationship.Tile")
    def test_creates_tile_with_correct_resource_and_nodegroup(self, MockTile):
        source_tile = _make_tile(
            resource_id=RESOURCE_A,
            data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_B)},
        )
        mock_instance = MagicMock()
        MockTile.return_value = mock_instance

        self.fn._create_counterpart_tile(source_tile, RESOURCE_B, RESOURCE_A)

        _, kwargs = MockTile.call_args
        self.assertEqual(str(kwargs["resourceinstance_id"]), RESOURCE_B)
        self.assertEqual(str(kwargs["nodegroup_id"]), RELATION_STATUS_NODEGROUP)

    @patch("arches_lingo.functions.reciprocal_relationship.Tile")
    def test_saves_with_reciprocal_sync_context(self, MockTile):
        source_tile = _make_tile(
            resource_id=RESOURCE_A,
            data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_B)},
        )
        mock_instance = MagicMock()
        MockTile.return_value = mock_instance

        self.fn._create_counterpart_tile(source_tile, RESOURCE_B, RESOURCE_A)

        mock_instance.save.assert_called_once_with(
            request=None, context=RECIPROCAL_SYNC_CONTEXT
        )

    @patch("arches_lingo.functions.reciprocal_relationship.Tile")
    def test_exception_is_caught_and_logged(self, MockTile):
        source_tile = _make_tile(
            resource_id=RESOURCE_A,
            data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_B)},
        )
        MockTile.side_effect = Exception("DB error")

        # Should not raise
        with self.assertLogs(
            "arches_lingo.functions.reciprocal_relationship", level="ERROR"
        ):
            self.fn._create_counterpart_tile(source_tile, RESOURCE_B, RESOURCE_A)


class UpdateCounterpartTileTests(SimpleTestCase):
    """Unit tests for _update_counterpart_tile, mocking Tile.save."""

    def setUp(self):
        self.fn = ReciprocalRelationshipFunction()

    def test_updates_tile_data_and_saves(self):
        source_tile = _make_tile(
            resource_id=RESOURCE_A,
            data={
                RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_B),
                RELATION_STATUS_STATUS_NODEID: "active",
            },
        )
        counterpart = _make_tile(resource_id=RESOURCE_B)

        self.fn._update_counterpart_tile(source_tile, counterpart, RESOURCE_A)

        # Counterpart's data should have been replaced
        self.assertEqual(
            counterpart.data[RELATION_STATUS_ASCRIBED_COMPARATE_NODEID][0][
                "resourceId"
            ],
            RESOURCE_A,
        )
        counterpart.save.assert_called_once_with(
            request=None, context=RECIPROCAL_SYNC_CONTEXT
        )

    def test_exception_is_caught_and_logged(self):
        source_tile = _make_tile(
            resource_id=RESOURCE_A,
            data={RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: _comparate(RESOURCE_B)},
        )
        counterpart = _make_tile(resource_id=RESOURCE_B)
        counterpart.save.side_effect = Exception("DB error")

        with self.assertLogs(
            "arches_lingo.functions.reciprocal_relationship", level="ERROR"
        ):
            self.fn._update_counterpart_tile(source_tile, counterpart, RESOURCE_A)
