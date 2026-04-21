import uuid
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from arches_lingo.functions.update_concept_lifecycle_states_for_scheme import (
    CHUNK_SIZE,
    UpdateConceptLifecycleStatesForScheme,
)

# These tests can be run from the command line via:
# python manage.py test tests.test_update_concept_lifecycle_states_for_scheme --settings="tests.test_settings"

MODULE = "arches_lingo.functions.update_concept_lifecycle_states_for_scheme"

CONCEPT_GRAPH_ID = uuid.uuid4()
SCHEME_ID = uuid.uuid4()

URI_NODEGROUP_ID = uuid.uuid4()
URI_CONTENT_NODE_ID = uuid.uuid4()
URI_CONTENT_NODE_ID_STR = str(URI_CONTENT_NODE_ID)

IDENTIFIER_NODEGROUP_ID = uuid.uuid4()
IDENTIFIER_CONTENT_NODE_ID = uuid.uuid4()
IDENTIFIER_TYPE_NODE_ID = uuid.uuid4()
IDENTIFIER_CONTENT_NODE_ID_STR = str(IDENTIFIER_CONTENT_NODE_ID)
IDENTIFIER_TYPE_NODE_ID_STR = str(IDENTIFIER_TYPE_NODE_ID)

URL_TEMPLATE = "http://example.org/<scheme_identifier>/<concept_counter>"
SCHEME_IDENTIFIER = "my-scheme"


def _make_uri_nodes():
    uri_node = MagicMock()
    uri_node.alias = "uri"
    uri_node.nodegroup_id = URI_NODEGROUP_ID

    uri_content_node = MagicMock()
    uri_content_node.alias = "uri_content"
    uri_content_node.nodeid = URI_CONTENT_NODE_ID

    return [uri_node, uri_content_node]


def _make_identifier_nodes():
    identifier_node = MagicMock()
    identifier_node.alias = "identifier"
    identifier_node.nodegroup_id = IDENTIFIER_NODEGROUP_ID

    identifier_content_node = MagicMock()
    identifier_content_node.alias = "identifier_content"
    identifier_content_node.nodeid = IDENTIFIER_CONTENT_NODE_ID

    identifier_type_node = MagicMock()
    identifier_type_node.alias = "identifier_type"
    identifier_type_node.nodeid = IDENTIFIER_TYPE_NODE_ID

    return [identifier_node, identifier_content_node, identifier_type_node]


class _SimpleObject:
    """Stand-in for ORM model instances.

    When a mocked model class is called as a constructor, returning a
    MagicMock means attribute access (tile.data, identifier.identifier)
    returns mocks rather than the real values passed in. This class
    accepts constructor keyword arguments and stores them as real
    attributes so tests can inspect them normally.
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _make_non_retired_queryset(concept_ids):
    queryset = MagicMock()
    queryset.values_list.return_value = concept_ids
    return queryset


def _make_draft_concepts_queryset(draft_concept_ids):
    queryset = MagicMock()
    (
        queryset.filter.return_value.select_for_update.return_value.order_by.return_value.values_list.return_value
    ) = draft_concept_ids
    return queryset


# ---------------------------------------------------------------------------
# _recalculate_non_retired_concept_uris — functional tests
# ---------------------------------------------------------------------------


class RecalculateNonRetiredConceptUrisTests(SimpleTestCase):

    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_returns_early_when_scheme_identifier_is_falsy(
        self, MockTileModel, MockResourceIdentifier, MockNode
    ):
        func = UpdateConceptLifecycleStatesForScheme()
        func._recalculate_non_retired_concept_uris(
            url_template=URL_TEMPLATE,
            scheme_identifier_value=None,
            concept_graph_id=CONCEPT_GRAPH_ID,
            related_non_retired_concepts_queryset=MagicMock(),
        )

        MockNode.objects.filter.assert_not_called()
        MockResourceIdentifier.objects.filter.assert_not_called()
        MockTileModel.objects.bulk_create.assert_not_called()

    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_creates_new_uri_tile_when_none_exists(
        self, MockTileModel, MockResourceIdentifier, MockNode
    ):
        concept_id = uuid.uuid4()

        MockNode.objects.filter.return_value = _make_uri_nodes()
        MockResourceIdentifier.objects.filter.return_value.values_list.return_value = [
            (concept_id, "42")
        ]
        MockTileModel.objects.filter.return_value.only.return_value = []
        MockTileModel.side_effect = _SimpleObject

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func,
            "_get_nodegroup_data_with_widget_defaults",
            return_value={URI_CONTENT_NODE_ID_STR: None},
        ):
            func._recalculate_non_retired_concept_uris(
                url_template=URL_TEMPLATE,
                scheme_identifier_value=SCHEME_IDENTIFIER,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_non_retired_queryset(
                    [concept_id]
                ),
            )

        MockTileModel.objects.bulk_create.assert_called_once()
        created_tiles = MockTileModel.objects.bulk_create.call_args.args[0]
        self.assertEqual(len(created_tiles), 1)
        expected_uri = f"http://example.org/{SCHEME_IDENTIFIER}/42"
        self.assertEqual(created_tiles[0].data[URI_CONTENT_NODE_ID_STR], expected_uri)

    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_updates_existing_tile_when_uri_has_changed(
        self, MockTileModel, MockResourceIdentifier, MockNode
    ):
        concept_id = uuid.uuid4()

        MockNode.objects.filter.return_value = _make_uri_nodes()
        MockResourceIdentifier.objects.filter.return_value.values_list.return_value = [
            (concept_id, "42")
        ]

        existing_tile = MagicMock()
        existing_tile.resourceinstance_id = concept_id
        existing_tile.data = {URI_CONTENT_NODE_ID_STR: "http://example.org/old/1"}
        MockTileModel.objects.filter.return_value.only.return_value = [existing_tile]

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func,
            "_get_nodegroup_data_with_widget_defaults",
            return_value={URI_CONTENT_NODE_ID_STR: None},
        ):
            func._recalculate_non_retired_concept_uris(
                url_template=URL_TEMPLATE,
                scheme_identifier_value=SCHEME_IDENTIFIER,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_non_retired_queryset(
                    [concept_id]
                ),
            )

        expected_uri = f"http://example.org/{SCHEME_IDENTIFIER}/42"
        self.assertEqual(existing_tile.data[URI_CONTENT_NODE_ID_STR], expected_uri)
        MockTileModel.objects.bulk_update.assert_called_once()
        updated_tiles = MockTileModel.objects.bulk_update.call_args.args[0]
        self.assertIn(existing_tile, updated_tiles)

    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_skips_tile_when_uri_is_already_correct(
        self, MockTileModel, MockResourceIdentifier, MockNode
    ):
        concept_id = uuid.uuid4()
        expected_uri = f"http://example.org/{SCHEME_IDENTIFIER}/42"

        MockNode.objects.filter.return_value = _make_uri_nodes()
        MockResourceIdentifier.objects.filter.return_value.values_list.return_value = [
            (concept_id, "42")
        ]

        existing_tile = MagicMock()
        existing_tile.resourceinstance_id = concept_id
        existing_tile.data = {URI_CONTENT_NODE_ID_STR: expected_uri}
        MockTileModel.objects.filter.return_value.only.return_value = [existing_tile]

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func,
            "_get_nodegroup_data_with_widget_defaults",
            return_value={URI_CONTENT_NODE_ID_STR: None},
        ):
            func._recalculate_non_retired_concept_uris(
                url_template=URL_TEMPLATE,
                scheme_identifier_value=SCHEME_IDENTIFIER,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_non_retired_queryset(
                    [concept_id]
                ),
            )

        MockTileModel.objects.bulk_create.assert_not_called()
        MockTileModel.objects.bulk_update.assert_not_called()

    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_skips_concept_with_no_identifier(
        self, MockTileModel, MockResourceIdentifier, MockNode
    ):
        concept_id = uuid.uuid4()

        MockNode.objects.filter.return_value = _make_uri_nodes()
        MockResourceIdentifier.objects.filter.return_value.values_list.return_value = []
        MockTileModel.objects.filter.return_value.only.return_value = []

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func,
            "_get_nodegroup_data_with_widget_defaults",
            return_value={URI_CONTENT_NODE_ID_STR: None},
        ):
            func._recalculate_non_retired_concept_uris(
                url_template=URL_TEMPLATE,
                scheme_identifier_value=SCHEME_IDENTIFIER,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_non_retired_queryset(
                    [concept_id]
                ),
            )

        MockTileModel.objects.bulk_create.assert_not_called()
        MockTileModel.objects.bulk_update.assert_not_called()


# ---------------------------------------------------------------------------
# _recalculate_non_retired_concept_uris — chunking regression tests
# ---------------------------------------------------------------------------


class RecalculateNonRetiredConceptUrisChunkingTests(SimpleTestCase):

    def _run_with_concept_count(
        self, concept_count, MockTileModel, MockResourceIdentifier, MockNode
    ):
        concept_ids = [uuid.uuid4() for _ in range(concept_count)]

        MockNode.objects.filter.return_value = _make_uri_nodes()
        MockResourceIdentifier.objects.filter.return_value.values_list.return_value = []
        MockTileModel.objects.filter.return_value.only.return_value = []

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func,
            "_get_nodegroup_data_with_widget_defaults",
            return_value={URI_CONTENT_NODE_ID_STR: None},
        ):
            func._recalculate_non_retired_concept_uris(
                url_template=URL_TEMPLATE,
                scheme_identifier_value=SCHEME_IDENTIFIER,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_non_retired_queryset(
                    concept_ids
                ),
            )

        return concept_ids

    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_identifier_query_is_issued_once_per_chunk(
        self, MockTileModel, MockResourceIdentifier, MockNode
    ):
        concept_count = CHUNK_SIZE * 2 + 1  # forces 3 chunks
        self._run_with_concept_count(
            concept_count, MockTileModel, MockResourceIdentifier, MockNode
        )

        self.assertEqual(MockResourceIdentifier.objects.filter.call_count, 3)
        for filter_call in MockResourceIdentifier.objects.filter.call_args_list:
            queried_ids = filter_call.kwargs["resourceid_id__in"]
            self.assertLessEqual(len(queried_ids), CHUNK_SIZE)

    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_existing_tile_query_is_issued_once_per_chunk(
        self, MockTileModel, MockResourceIdentifier, MockNode
    ):
        concept_count = CHUNK_SIZE * 2 + 1  # forces 3 chunks
        self._run_with_concept_count(
            concept_count, MockTileModel, MockResourceIdentifier, MockNode
        )

        self.assertEqual(MockTileModel.objects.filter.call_count, 3)
        for filter_call in MockTileModel.objects.filter.call_args_list:
            queried_ids = filter_call.kwargs["resourceinstance_id__in"]
            self.assertLessEqual(len(queried_ids), CHUNK_SIZE)

    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_bulk_create_is_called_per_chunk_and_never_exceeds_chunk_size(
        self, MockTileModel, MockResourceIdentifier, MockNode
    ):
        concept_count = CHUNK_SIZE * 2 + 1  # 3 chunks
        concept_ids = [uuid.uuid4() for _ in range(concept_count)]

        MockNode.objects.filter.return_value = _make_uri_nodes()
        # Every concept has an identifier so every concept produces a tile to create
        MockResourceIdentifier.objects.filter.return_value.values_list.return_value = [
            (concept_id, str(index + 1)) for index, concept_id in enumerate(concept_ids)
        ]
        MockTileModel.objects.filter.return_value.only.return_value = []

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func,
            "_get_nodegroup_data_with_widget_defaults",
            return_value={URI_CONTENT_NODE_ID_STR: None},
        ):
            func._recalculate_non_retired_concept_uris(
                url_template=URL_TEMPLATE,
                scheme_identifier_value=SCHEME_IDENTIFIER,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_non_retired_queryset(
                    concept_ids
                ),
            )

        self.assertEqual(MockTileModel.objects.bulk_create.call_count, 3)
        for create_call in MockTileModel.objects.bulk_create.call_args_list:
            self.assertLessEqual(len(create_call.args[0]), CHUNK_SIZE)


# ---------------------------------------------------------------------------
# _handle_draft_concepts_promoted_to_active — functional tests
# ---------------------------------------------------------------------------


class HandleDraftConceptsPromotedToActiveTests(SimpleTestCase):

    @patch(f"{MODULE}.ListItem")
    @patch(f"{MODULE}.allocate_concept_identifier_number")
    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_returns_early_when_no_draft_concepts(
        self,
        MockTileModel,
        MockResourceIdentifier,
        MockNode,
        MockAllocate,
        MockListItem,
    ):
        func = UpdateConceptLifecycleStatesForScheme()
        func._handle_draft_concepts_promoted_to_active(
            scheme_resource_instance_id=SCHEME_ID,
            concept_graph_id=CONCEPT_GRAPH_ID,
            related_non_retired_concepts_queryset=_make_draft_concepts_queryset([]),
            request=None,
        )

        MockAllocate.assert_not_called()
        MockTileModel.objects.bulk_create.assert_not_called()
        MockResourceIdentifier.objects.bulk_create.assert_not_called()

    @patch(f"{MODULE}.ListItem")
    @patch(f"{MODULE}.allocate_concept_identifier_number")
    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_creates_one_resource_identifier_and_tile_per_draft_concept(
        self,
        MockTileModel,
        MockResourceIdentifier,
        MockNode,
        MockAllocate,
        MockListItem,
    ):
        concept_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        MockNode.objects.filter.return_value = _make_identifier_nodes()
        MockAllocate.return_value = 10
        MockListItem.objects.get.return_value.build_tile_value.return_value = {}

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func, "_get_nodegroup_data_with_widget_defaults", return_value={}
        ):
            func._handle_draft_concepts_promoted_to_active(
                scheme_resource_instance_id=SCHEME_ID,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_draft_concepts_queryset(
                    concept_ids
                ),
                request=None,
            )

        MockTileModel.objects.bulk_create.assert_called_once()
        created_tiles = MockTileModel.objects.bulk_create.call_args.args[0]
        self.assertEqual(len(created_tiles), 3)

        MockResourceIdentifier.objects.bulk_create.assert_called_once()
        created_identifiers = MockResourceIdentifier.objects.bulk_create.call_args.args[
            0
        ]
        self.assertEqual(len(created_identifiers), 3)

    @patch(f"{MODULE}.ListItem")
    @patch(f"{MODULE}.allocate_concept_identifier_number")
    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_identifier_values_are_sequential_from_allocated_start(
        self,
        MockTileModel,
        MockResourceIdentifier,
        MockNode,
        MockAllocate,
        MockListItem,
    ):
        concept_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        MockNode.objects.filter.return_value = _make_identifier_nodes()
        MockAllocate.return_value = 10
        MockListItem.objects.get.return_value.build_tile_value.return_value = {}
        MockResourceIdentifier.side_effect = _SimpleObject

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func, "_get_nodegroup_data_with_widget_defaults", return_value={}
        ):
            func._handle_draft_concepts_promoted_to_active(
                scheme_resource_instance_id=SCHEME_ID,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_draft_concepts_queryset(
                    concept_ids
                ),
                request=None,
            )

        created_identifiers = MockResourceIdentifier.objects.bulk_create.call_args.args[
            0
        ]
        for index, identifier in enumerate(created_identifiers):
            self.assertEqual(identifier.identifier, str(10 + index))

    @patch(f"{MODULE}.ListItem")
    @patch(f"{MODULE}.allocate_concept_identifier_number")
    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_tile_data_contains_identifier_value_and_type(
        self,
        MockTileModel,
        MockResourceIdentifier,
        MockNode,
        MockAllocate,
        MockListItem,
    ):
        concept_ids = [uuid.uuid4()]
        MockNode.objects.filter.return_value = _make_identifier_nodes()
        MockAllocate.return_value = 5
        type_tile_value = {"id": "some-type-id"}
        MockListItem.objects.get.return_value.build_tile_value.return_value = (
            type_tile_value
        )
        MockTileModel.side_effect = _SimpleObject
        MockResourceIdentifier.side_effect = _SimpleObject

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func,
            "_get_nodegroup_data_with_widget_defaults",
            return_value={
                IDENTIFIER_CONTENT_NODE_ID_STR: None,
                IDENTIFIER_TYPE_NODE_ID_STR: None,
            },
        ):
            func._handle_draft_concepts_promoted_to_active(
                scheme_resource_instance_id=SCHEME_ID,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_draft_concepts_queryset(
                    concept_ids
                ),
                request=None,
            )

        created_tiles = MockTileModel.objects.bulk_create.call_args.args[0]
        tile_data = created_tiles[0].data
        self.assertEqual(tile_data[IDENTIFIER_CONTENT_NODE_ID_STR], "5")
        self.assertEqual(tile_data[IDENTIFIER_TYPE_NODE_ID_STR], [type_tile_value])


# ---------------------------------------------------------------------------
# _handle_draft_concepts_promoted_to_active — chunking regression tests
# ---------------------------------------------------------------------------


class HandleDraftConceptsPromotedToActiveChunkingTests(SimpleTestCase):

    def _run_with_concept_count(
        self,
        concept_count,
        MockTileModel,
        MockResourceIdentifier,
        MockNode,
        MockAllocate,
        MockListItem,
    ):
        concept_ids = [uuid.uuid4() for _ in range(concept_count)]
        MockNode.objects.filter.return_value = _make_identifier_nodes()
        MockAllocate.return_value = 1
        MockListItem.objects.get.return_value.build_tile_value.return_value = {}

        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func, "_get_nodegroup_data_with_widget_defaults", return_value={}
        ):
            func._handle_draft_concepts_promoted_to_active(
                scheme_resource_instance_id=SCHEME_ID,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_draft_concepts_queryset(
                    concept_ids
                ),
                request=None,
            )

        return concept_ids

    @patch(f"{MODULE}.ListItem")
    @patch(f"{MODULE}.allocate_concept_identifier_number")
    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_identifier_allocation_called_exactly_once_regardless_of_chunk_count(
        self,
        MockTileModel,
        MockResourceIdentifier,
        MockNode,
        MockAllocate,
        MockListItem,
    ):
        concept_count = CHUNK_SIZE * 2 + 1  # 3 chunks
        self._run_with_concept_count(
            concept_count,
            MockTileModel,
            MockResourceIdentifier,
            MockNode,
            MockAllocate,
            MockListItem,
        )

        MockAllocate.assert_called_once_with(
            scheme_resource_instance_id=SCHEME_ID,
            count=concept_count,
        )

    @patch(f"{MODULE}.ListItem")
    @patch(f"{MODULE}.allocate_concept_identifier_number")
    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_resource_identifier_bulk_create_called_per_chunk(
        self,
        MockTileModel,
        MockResourceIdentifier,
        MockNode,
        MockAllocate,
        MockListItem,
    ):
        concept_count = CHUNK_SIZE * 2 + 1  # 3 chunks
        self._run_with_concept_count(
            concept_count,
            MockTileModel,
            MockResourceIdentifier,
            MockNode,
            MockAllocate,
            MockListItem,
        )

        self.assertEqual(MockResourceIdentifier.objects.bulk_create.call_count, 3)
        for create_call in MockResourceIdentifier.objects.bulk_create.call_args_list:
            self.assertLessEqual(len(create_call.args[0]), CHUNK_SIZE)

    @patch(f"{MODULE}.ListItem")
    @patch(f"{MODULE}.allocate_concept_identifier_number")
    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_tile_bulk_create_called_per_chunk(
        self,
        MockTileModel,
        MockResourceIdentifier,
        MockNode,
        MockAllocate,
        MockListItem,
    ):
        concept_count = CHUNK_SIZE * 2 + 1  # 3 chunks
        self._run_with_concept_count(
            concept_count,
            MockTileModel,
            MockResourceIdentifier,
            MockNode,
            MockAllocate,
            MockListItem,
        )

        self.assertEqual(MockTileModel.objects.bulk_create.call_count, 3)
        for create_call in MockTileModel.objects.bulk_create.call_args_list:
            self.assertLessEqual(len(create_call.args[0]), CHUNK_SIZE)

    @patch(f"{MODULE}.ListItem")
    @patch(f"{MODULE}.allocate_concept_identifier_number")
    @patch(f"{MODULE}.Node")
    @patch(f"{MODULE}.ResourceIdentifier")
    @patch(f"{MODULE}.TileModel")
    def test_identifier_values_are_sequential_across_chunk_boundary(
        self,
        MockTileModel,
        MockResourceIdentifier,
        MockNode,
        MockAllocate,
        MockListItem,
    ):
        concept_count = CHUNK_SIZE + 5  # 2 chunks: one full, one partial
        MockNode.objects.filter.return_value = _make_identifier_nodes()
        MockAllocate.return_value = 100
        MockListItem.objects.get.return_value.build_tile_value.return_value = {}
        MockResourceIdentifier.side_effect = _SimpleObject

        concept_ids = [uuid.uuid4() for _ in range(concept_count)]
        func = UpdateConceptLifecycleStatesForScheme()
        with patch.object(
            func, "_get_nodegroup_data_with_widget_defaults", return_value={}
        ):
            func._handle_draft_concepts_promoted_to_active(
                scheme_resource_instance_id=SCHEME_ID,
                concept_graph_id=CONCEPT_GRAPH_ID,
                related_non_retired_concepts_queryset=_make_draft_concepts_queryset(
                    concept_ids
                ),
                request=None,
            )

        all_created_identifiers = []
        for create_call in MockResourceIdentifier.objects.bulk_create.call_args_list:
            all_created_identifiers.extend(create_call.args[0])

        self.assertEqual(len(all_created_identifiers), concept_count)
        for index, identifier in enumerate(all_created_identifiers):
            self.assertEqual(identifier.identifier, str(100 + index))
