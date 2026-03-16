import json
import uuid
import datetime
from http import HTTPStatus
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Group, User
from django.core import management
from django.test import TestCase, override_settings
from django.test.utils import captured_stdout
from django.urls import reverse

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import ResourceInstance, ResourceXResource, TileModel
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.data_management.resource_graphs.importer import (
    import_graph as ResourceGraphImporter,
)

from arches_controlled_lists.management.commands.packages import (
    Command as ControlledListsPackageCommand,
)

from arches_lingo.permissions import (
    is_lingo_editor,
)
from arches_lingo.const import (
    LINGO_EDITOR_GROUP_NAME,
    CONCEPTS_GRAPH_ID,
    SCHEMES_GRAPH_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CONCEPT_TYPE_NODEGROUP,
    CONCEPT_TYPE_NODEID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    GUIDE_TERM_URI,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_TYPE_NODE,
    LABEL_LIST_ID,
)
from arches_lingo.utils.concept_builder import ConceptBuilder

# these tests can be run from the command line via
# python manage.py test tests.tests --settings="tests.test_settings"


class ViewTests(TestCase):
    graph_fixtures = ["Scheme.json", "Concept.json"]

    @classmethod
    def load_ontology(cls):
        path = Path(settings.APP_ROOT) / "pkg" / "ontologies" / "takin"
        management.call_command("load_ontology", source=path, verbosity=0)

    @classmethod
    def load_graphs(cls):
        path = Path(settings.APP_ROOT) / "pkg" / "graphs" / "resource_models"
        for file_path in cls.graph_fixtures:
            with captured_stdout(), open(path / file_path, "r") as graph_file:
                archesfile = JSONDeserializer().deserialize(graph_file)
                ResourceGraphImporter(archesfile["graph"], overwrite_graphs=True)

    @classmethod
    def load_controlled_lists(cls):
        cmd = ControlledListsPackageCommand()
        package_dir = Path(settings.APP_ROOT) / "pkg"
        cmd.load_concepts(package_dir, "overwrite", "keep", True)

    @classmethod
    def setUpTestData(cls):
        cls.load_controlled_lists()
        cls.load_ontology()
        cls.load_graphs()
        cls.admin = User.objects.get(username="admin")

        # Create a scheme with five concepts, each one narrower than the last,
        # and each concept after the top concept also narrower than the top.
        cls.scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Test Scheme"
        )

        reference = DataTypeFactory().get_instance("reference")
        label_config = {"controlledList": LABEL_LIST_ID}
        prefLabel_reference_dt = reference.transform_value_for_tile(
            "prefLabel", **label_config
        )

        TileModel.objects.create(
            resourceinstance=cls.scheme,
            nodegroup_id=SCHEME_NAME_NODEGROUP,
            data={
                SCHEME_NAME_CONTENT_NODE: "Test Scheme",
                SCHEME_NAME_TYPE_NODE: prefLabel_reference_dt,
                SCHEME_NAME_LANGUAGE_NODE: "en",
            },
        )

        MAX_DEPTH = 5
        CONCEPT_COUNT = 5
        cls.concepts = [
            ResourceInstance(graph_id=CONCEPTS_GRAPH_ID, name=f"Concept {num + 1}")
            for num in range(CONCEPT_COUNT)
        ]
        for concept in cls.concepts:
            concept.save()

        concept_tiles = []
        resource_x_resource_records = []
        for index, concept in enumerate(cls.concepts):
            # Create label tile
            concept_tiles.append(
                TileModel(
                    resourceinstance=concept,
                    nodegroup_id=CONCEPT_NAME_NODEGROUP,
                    data={
                        CONCEPT_NAME_CONTENT_NODE: f"Concept {index + 1}",
                        CONCEPT_NAME_TYPE_NODE: prefLabel_reference_dt,
                        CONCEPT_NAME_LANGUAGE_NODE: "en",
                    },
                )
            )
            # Create part of scheme tile
            part_of_scheme_rxr = ResourceXResource(
                from_resource=concept,
                from_resource_graph_id=CONCEPTS_GRAPH_ID,
                to_resource=cls.scheme,
                to_resource_graph_id=SCHEMES_GRAPH_ID,
                created=datetime.datetime.now(),
                modified=datetime.datetime.now(),
            )
            resource_x_resource_records.append(part_of_scheme_rxr)
            concept_tiles.append(
                TileModel(
                    resourceinstance=concept,
                    nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                    data={
                        CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                            {
                                "resourceId": str(cls.scheme.pk),
                                "resourceXresourceId": str(part_of_scheme_rxr.pk),
                            },
                        ],
                    },
                )
            )
            # Create top concept/narrower tile
            if index == 0:
                top_concept_rxr = ResourceXResource(
                    from_resource=concept,
                    from_resource_graph_id=CONCEPTS_GRAPH_ID,
                    to_resource=cls.scheme,
                    to_resource_graph_id=SCHEMES_GRAPH_ID,
                    created=datetime.datetime.now(),
                    modified=datetime.datetime.now(),
                )
                resource_x_resource_records.append(top_concept_rxr)
                concept_tiles.append(
                    TileModel(
                        resourceinstance=concept,
                        nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                        data={
                            TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [
                                {
                                    "resourceId": str(cls.scheme.pk),
                                    "resourceXresourceId": str(top_concept_rxr.pk),
                                },
                            ],
                        },
                    )
                )
            elif index < MAX_DEPTH:
                narrower_hierarchy_rxr = ResourceXResource(
                    from_resource=concept,
                    from_resource_graph_id=CONCEPTS_GRAPH_ID,
                    to_resource=cls.concepts[index - 1],
                    to_resource_graph_id=CONCEPTS_GRAPH_ID,
                    created=datetime.datetime.now(),
                    modified=datetime.datetime.now(),
                )
                broader_hierarchy_rxr = ResourceXResource(
                    from_resource=concept,
                    from_resource_graph_id=CONCEPTS_GRAPH_ID,
                    to_resource=cls.concepts[0],
                    to_resource_graph_id=CONCEPTS_GRAPH_ID,
                    created=datetime.datetime.now(),
                    modified=datetime.datetime.now(),
                )
                resource_x_resource_records.append(narrower_hierarchy_rxr)
                resource_x_resource_records.append(broader_hierarchy_rxr)
                concept_tiles.append(
                    TileModel(
                        resourceinstance=concept,
                        nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                        data={
                            CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                                # Previous concept
                                {
                                    "resourceId": str(cls.concepts[index - 1].pk),
                                    "resourceXresourceId": str(
                                        narrower_hierarchy_rxr.pk
                                    ),
                                },
                                # Also add top concept
                                {
                                    "resourceId": str(cls.concepts[0].pk),
                                    "resourceXresourceId": str(
                                        broader_hierarchy_rxr.pk
                                    ),
                                },
                            ],
                        },
                    )
                )
            else:
                broader_hierarchy_rxr = ResourceXResource(
                    from_resource=concept,
                    from_resource_graph_id=CONCEPTS_GRAPH_ID,
                    to_resource=cls.concepts[0],
                    to_resource_graph_id=CONCEPTS_GRAPH_ID,
                    created=datetime.datetime.now(),
                    modified=datetime.datetime.now(),
                )
                resource_x_resource_records.append(broader_hierarchy_rxr)
                concept_tiles.append(
                    TileModel(
                        resourceinstance=concept,
                        nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                        data={
                            CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                                # Top concept only
                                {
                                    "resourceId": str(cls.concepts[0].pk),
                                    "resourceXresourceId": str(
                                        broader_hierarchy_rxr.pk
                                    ),
                                },
                            ],
                        },
                    )
                )
        TileModel.objects.bulk_create(concept_tiles)
        ResourceXResource.objects.bulk_create(resource_x_resource_records)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_get_concept_trees(self):
        with self.assertNumQueries(8):
            # 1: session
            # 2: auth
            # 3: select broader tiles, subquery for labels
            # 4: select top concept tiles, subquery for labels
            # 5: select guide term concept type tiles
            # 6: select schemes, subquery for labels
            # 7: languages
            # 8: resource_instance_lifecycle_state
            response = self.client.get(reverse("api-concepts"))

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        scheme = result["schemes"][0]

        self.assertEqual(scheme["labels"][0]["value"], "Test Scheme")
        self.assertEqual(scheme["labels"][0]["valuetype_id"], "prefLabel")
        self.assertEqual(len(scheme["top_concepts"]), 1)
        top = scheme["top_concepts"][0]
        self.assertEqual(top["labels"][0]["value"], "Concept 1")
        self.assertEqual(len(top["narrower"]), 4)
        self.assertEqual(
            {n["labels"][0]["value"] for n in top["narrower"]},
            {"Concept 2", "Concept 3", "Concept 4", "Concept 5"},
        )
        concept_2 = [
            concept
            for concept in top["narrower"]
            if concept["labels"][0]["value"] == "Concept 2"
        ][0]
        self.assertEqual(
            {n["labels"][0]["value"] for n in concept_2["narrower"]},
            {"Concept 3"},
        )
        self.assertEqual(
            {n["labels"][0]["valuetype_id"] for n in concept_2["narrower"]},
            {"prefLabel"},
        )

    def test_search(self):
        cases = (
            # Fuzzy match: finds all 5 concepts
            ["term=Concept 1", 5],
            ["term=Concept 1&maxEditDistance=0", 1],
            ["term=Concept 1&exact=true", 1],
            ["term=Concept 0&exact=true", 0],
            ["term=Concept 1&items=4", 4],
            ["term=Concept 1&items=4&page=2", 1],
            # Containment
            ["term=Con", 5],
            ["term=Con&maxEditDistance=0", 5],
            ["term=Con&exact=True", 0],
        )
        for query, expected_result_count in cases:
            with self.subTest(query=query):
                response = self.client.get(reverse("api-search"), QUERY_STRING=query)
                result = json.loads(response.content)
                self.assertEqual(len(result["data"]), expected_result_count, result)

    def test_lineage(self):
        # Supplement the test data with a tile that makes Concept 5
        # also a top concept of the scheme (in addition to Concept 1).
        TileModel.objects.create(
            resourceinstance=self.concepts[4],
            nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
            data={
                TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [
                    {"resourceId": str(self.scheme.pk)},
                ],
            },
        )

        response = self.client.get(
            reverse("api-search"), QUERY_STRING="term=Concept 5&maxEditDistance=0"
        )
        result = json.loads(response.content)

        self.assertIs(result["data"][0]["polyhierarchical"], True)
        # Since each concept was also created with a broader concept tile for
        # the top concept (Concept 1), Concept 5 has 4 paths back to root, plus
        # another path directly to the Scheme from the extra tile created above.
        self.assertEqual(
            sorted(
                [concept["labels"][0]["value"] for concept in path]
                for path in result["data"][0]["parents"]
            ),
            [
                [
                    "Test Scheme",
                    "Concept 1",
                    "Concept 2",
                    "Concept 3",
                    "Concept 4",
                    "Concept 5",
                ],
                ["Test Scheme", "Concept 1", "Concept 3", "Concept 4", "Concept 5"],
                ["Test Scheme", "Concept 1", "Concept 4", "Concept 5"],
                ["Test Scheme", "Concept 1", "Concept 5"],
                ["Test Scheme", "Concept 5"],
            ],
        )

    def test_invalid_search_term(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(
                reverse("api-search"), QUERY_STRING="term=" + ("!" * 256)
            )
        self.assertContains(
            response,
            "Fuzzy search terms cannot exceed 255 characters.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_invalid_edit_distance(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(
                reverse("api-search"), QUERY_STRING="term=test&maxEditDistance=?"
            )
        self.assertContains(
            response,
            "Edit distance could not be converted to an integer.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_get_scheme_without_top_concepts(self):
        response = self.client.get(
            reverse("api-lingo-scheme", kwargs={"pk": self.scheme.pk})
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["labels"][0]["value"], "Test Scheme")
        self.assertNotIn("top_concepts", result)

    def test_get_scheme_with_top_concepts(self):
        response = self.client.get(
            reverse("api-lingo-scheme", kwargs={"pk": self.scheme.pk}),
            {"include_top_concepts": "true"},
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["labels"][0]["value"], "Test Scheme")
        self.assertIn("top_concepts", result)
        self.assertEqual(len(result["top_concepts"]), 1)
        top = result["top_concepts"][0]
        self.assertEqual(top["labels"][0]["value"], "Concept 1")
        self.assertEqual(top["narrower"], [])

    def test_get_scheme_not_found(self):
        nonexistent_id = uuid.uuid4()
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(
                reverse("api-lingo-scheme", kwargs={"pk": nonexistent_id})
            )
        self.assertEqual(response.status_code, 404)

    def test_scheme_label_counts(self):
        """The existing test data has 5 concepts each with one English label."""
        response = self.client.get(
            reverse("api-lingo-scheme-label-counts", kwargs={"pk": self.scheme.pk})
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["code"], "en")
        self.assertEqual(result[0]["count"], 5)
        self.assertEqual(result[0]["language"], "English")

    def test_scheme_label_counts_multiple_languages(self):
        """Add German labels to some concepts and verify counts."""
        # Add German labels to the first two concepts
        for concept in self.concepts[:2]:
            TileModel.objects.create(
                resourceinstance=concept,
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data={
                    CONCEPT_NAME_CONTENT_NODE: f"{concept.name} (de)",
                    CONCEPT_NAME_TYPE_NODE: None,
                    CONCEPT_NAME_LANGUAGE_NODE: "de",
                },
            )

        response = self.client.get(
            reverse("api-lingo-scheme-label-counts", kwargs={"pk": self.scheme.pk})
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)

        counts_by_code = {entry["code"]: entry["count"] for entry in result}
        self.assertEqual(counts_by_code["en"], 5)
        self.assertEqual(counts_by_code["de"], 2)
        # Results sorted by count descending
        self.assertEqual(result[0]["code"], "en")
        self.assertEqual(result[1]["code"], "de")

    def test_scheme_label_counts_empty_scheme(self):
        """A scheme with no concepts should return an empty list."""
        empty_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Empty Scheme"
        )
        response = self.client.get(
            reverse("api-lingo-scheme-label-counts", kwargs={"pk": empty_scheme.pk})
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result, [])

    def test_scheme_label_counts_unauthenticated(self):
        """Anonymous users should be able to read scheme label counts when allowed."""
        self.client.logout()
        with self.settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True):
            response = self.client.get(
                reverse(
                    "api-lingo-scheme-label-counts",
                    kwargs={"pk": self.scheme.pk},
                )
            )
        self.assertEqual(response.status_code, 200)

    def test_scheme_label_counts_unauthenticated_denied(self):
        """Anonymous users should be denied when anonymous access is disabled."""
        self.client.logout()
        with self.settings(LINGO_ALLOW_ANONYMOUS_ACCESS=False):
            response = self.client.get(
                reverse(
                    "api-lingo-scheme-label-counts",
                    kwargs={"pk": self.scheme.pk},
                )
            )
        self.assertEqual(response.status_code, 403)

    def test_guide_term_flag_in_concept_tree(self):
        """Concepts with guide term concept type should be flagged."""
        guide_concept = self.concepts[1]  # Concept 2

        # Add a type tile with guide term type
        TileModel.objects.create(
            resourceinstance=guide_concept,
            nodegroup_id=CONCEPT_TYPE_NODEGROUP,
            data={
                CONCEPT_TYPE_NODEID: [
                    {
                        "uri": GUIDE_TERM_URI,
                        "labels": [{"value": "guide term", "language_id": "en"}],
                    }
                ],
            },
        )

        response = self.client.get(reverse("api-concepts"))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        scheme = result["schemes"][0]
        top = scheme["top_concepts"][0]

        # The top concept (Concept 1) should NOT be a guide term
        self.assertFalse(top["guide_term"])

        # Find Concept 2 in narrower list -- it should be flagged as guide term
        concept_2 = next(
            narrower_concept
            for narrower_concept in top["narrower"]
            if narrower_concept["labels"][0]["value"] == "Concept 2"
        )
        self.assertTrue(concept_2["guide_term"])

        # Other narrower concepts should not be guide terms
        for narrower_concept in top["narrower"]:
            if narrower_concept["labels"][0]["value"] != "Concept 2":
                self.assertFalse(narrower_concept["guide_term"])

    def test_guide_term_flag_in_search(self):
        """Guide term flag should appear in search results."""
        guide_concept = self.concepts[2]  # Concept 3

        TileModel.objects.create(
            resourceinstance=guide_concept,
            nodegroup_id=CONCEPT_TYPE_NODEGROUP,
            data={
                CONCEPT_TYPE_NODEID: [
                    {
                        "uri": GUIDE_TERM_URI,
                        "labels": [{"value": "guide term", "language_id": "en"}],
                    }
                ],
            },
        )

        response = self.client.get(
            reverse("api-search"),
            QUERY_STRING="term=Concept 3&maxEditDistance=0",
        )
        result = json.loads(response.content)
        self.assertEqual(len(result["data"]), 1)
        self.assertTrue(result["data"][0]["guide_term"])

        # Non-guide-term concept should be False
        response = self.client.get(
            reverse("api-search"),
            QUERY_STRING="term=Concept 1&maxEditDistance=0",
        )
        result = json.loads(response.content)
        self.assertEqual(len(result["data"]), 1)
        self.assertFalse(result["data"][0]["guide_term"])

    def test_guide_term_flag_default_false(self):
        """Concepts without guide term type should have guide_term=False."""
        response = self.client.get(reverse("api-concepts"))
        result = json.loads(response.content)
        scheme = result["schemes"][0]
        top = scheme["top_concepts"][0]

        self.assertFalse(top["guide_term"])
        for narrower_concept in top["narrower"]:
            self.assertFalse(narrower_concept["guide_term"])

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True)
    def test_anonymous_can_read_concept_trees(self):
        """Anonymous users should be able to read the concept tree when allowed."""
        self.client.logout()
        response = self.client.get(reverse("api-concepts"))
        self.assertEqual(response.status_code, 200)

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True)
    def test_anonymous_can_search(self):
        """Anonymous users should be able to search when allowed."""
        self.client.logout()
        response = self.client.get(reverse("api-search"), QUERY_STRING="term=Concept")
        self.assertEqual(response.status_code, 200)

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True)
    def test_anonymous_can_read_edit_log(self):
        """Anonymous users should be able to GET the edit log when allowed."""
        self.client.logout()
        response = self.client.get(
            reverse(
                "api-lingo-edit-log",
                kwargs={"resourceid": self.concepts[0].pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True)
    def test_anonymous_cannot_post_edit_log(self):
        """Anonymous users should not be able to revert resources."""
        self.client.logout()
        response = self.client.post(
            reverse(
                "api-lingo-edit-log",
                kwargs={"resourceid": self.concepts[0].pk},
            ),
            content_type="application/json",
            data=json.dumps({"timestamp": "2024-01-01T00:00:00Z"}),
        )
        self.assertEqual(response.status_code, 403)

    def test_non_editor_cannot_post_edit_log(self):
        """Authenticated non-editors should not be able to revert resources."""
        non_editor = User.objects.create_user(username="noeditor", password="test")
        self.client.force_login(non_editor)
        response = self.client.post(
            reverse(
                "api-lingo-edit-log",
                kwargs={"resourceid": self.concepts[0].pk},
            ),
            content_type="application/json",
            data=json.dumps({"timestamp": "2024-01-01T00:00:00Z"}),
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=False)
    def test_anonymous_denied_when_setting_disabled(self):
        """Anonymous users should be denied read access when anonymous access is disabled."""
        self.client.logout()
        response = self.client.get(reverse("api-concepts"))
        self.assertEqual(response.status_code, 403)

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=False)
    def test_anonymous_search_denied_when_setting_disabled(self):
        """Anonymous users should be denied search access when anonymous access is disabled."""
        self.client.logout()
        response = self.client.get(reverse("api-search"), QUERY_STRING="term=Concept")
        self.assertEqual(response.status_code, 403)


class IsGuideTermTileTests(TestCase):
    """Unit tests for ConceptBuilder.is_guide_term_tile static method."""

    def test_guide_term_tile_detected(self):
        tile_data = {
            CONCEPT_TYPE_NODEID: [
                {
                    "uri": GUIDE_TERM_URI,
                    "labels": [{"value": "guide term", "language_id": "en"}],
                }
            ]
        }
        self.assertTrue(ConceptBuilder.is_guide_term_tile(tile_data))

    def test_non_guide_term_tile(self):
        tile_data = {
            CONCEPT_TYPE_NODEID: [
                {
                    "uri": "http://example.com/some-other-type",
                    "labels": [{"value": "other", "language_id": "en"}],
                }
            ]
        }
        self.assertFalse(ConceptBuilder.is_guide_term_tile(tile_data))

    def test_empty_type_data(self):
        self.assertFalse(ConceptBuilder.is_guide_term_tile({}))
        self.assertFalse(ConceptBuilder.is_guide_term_tile({CONCEPT_TYPE_NODEID: None}))
        self.assertFalse(ConceptBuilder.is_guide_term_tile({CONCEPT_TYPE_NODEID: []}))


class PermissionTests(TestCase):
    """Tests for the Lingo Editor permission utilities and LingoUserView."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(username="admin")
        cls.regular_user = User.objects.create_user(
            username="regular", password="testpass"
        )
        cls.editor_user = User.objects.create_user(
            username="editor", password="testpass"
        )
        editor_group = Group.objects.get(name=LINGO_EDITOR_GROUP_NAME)
        cls.editor_user.groups.add(editor_group)

    def test_is_lingo_editor_anonymous_user(self):
        anonymous = AnonymousUser()
        self.assertFalse(is_lingo_editor(anonymous))

    def test_is_lingo_editor_regular_user(self):
        self.assertFalse(is_lingo_editor(self.regular_user))

    def test_is_lingo_editor_editor_user(self):
        self.assertTrue(is_lingo_editor(self.editor_user))

    def test_is_lingo_editor_superuser(self):
        self.assertTrue(is_lingo_editor(self.admin))

    def test_lingo_user_view_anonymous(self):
        response = self.client.get(reverse("api-lingo-user"))
        result = json.loads(response.content)
        self.assertTrue(result["is_anonymous"])
        self.assertFalse(result["is_lingo_editor"])
        self.assertNotIn("allow_anonymous_access", result)

    def test_lingo_user_view_regular_user(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("api-lingo-user"))
        result = json.loads(response.content)
        self.assertFalse(result["is_anonymous"])
        self.assertFalse(result["is_lingo_editor"])
        self.assertEqual(result["username"], "regular")

    def test_lingo_user_view_editor(self):
        self.client.force_login(self.editor_user)
        response = self.client.get(reverse("api-lingo-user"))
        result = json.loads(response.content)
        self.assertFalse(result["is_anonymous"])
        self.assertTrue(result["is_lingo_editor"])
        self.assertEqual(result["username"], "editor")

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True)
    def test_app_settings_view_anonymous_access_enabled(self):
        response = self.client.get(reverse("api-lingo-settings"))
        result = json.loads(response.content)
        self.assertTrue(result["allow_anonymous_access"])

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=False)
    def test_app_settings_view_anonymous_access_disabled(self):
        response = self.client.get(reverse("api-lingo-settings"))
        result = json.loads(response.content)
        self.assertFalse(result["allow_anonymous_access"])
