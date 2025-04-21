import json
from http import HTTPStatus

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

# these tests can be run from the command line via
# python manage.py test tests.tests --settings="tests.test_settings"

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import (
    GraphModel,
    Node,
    NodeGroup,
    ResourceInstance,
    TileModel,
)

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    SCHEMES_GRAPH_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_TYPE_NODE,
    LANGUAGES_LIST_ID,
    LABEL_LIST_ID,
)


class ViewTests(TestCase):
    @classmethod
    def mock_concept_and_scheme_graphs(cls):
        """Bootstrap just a few nodes as an alternative to loading the entire package."""

        GraphModel.objects.create(pk=SCHEMES_GRAPH_ID, isresource=True)
        GraphModel.objects.create(pk=CONCEPTS_GRAPH_ID, isresource=True)

        for nodegroup_id, node_id, node_name, datatype, config in [
            (
                TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                "top_concept_of",
                "resource-instance",
                {
                    "graphs": [{"graphid": SCHEMES_GRAPH_ID, "name": "Scheme"}],
                    "searchDsl": "",
                    "searchString": "",
                },
            ),
            (
                CLASSIFICATION_STATUS_NODEGROUP,
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
                "classification_status_ascribed_classification",
                "resource-instance",
                {
                    "graphs": [{"graphid": CONCEPTS_GRAPH_ID, "name": "Concept"}],
                    "searchDsl": "",
                    "searchString": "",
                },
            ),
            (
                SCHEME_NAME_NODEGROUP,
                SCHEME_NAME_CONTENT_NODE,
                "appellative_status_ascribed_name_content",
                "non-localized-string",
                {},
            ),
            (
                SCHEME_NAME_NODEGROUP,
                SCHEME_NAME_LANGUAGE_NODE,
                "appellative_status_ascribed_name_language",
                "reference",
                {"controlledList": LANGUAGES_LIST_ID, "multiValue": True},
            ),
            (
                CONCEPT_NAME_NODEGROUP,
                CONCEPT_NAME_CONTENT_NODE,
                "appellative_status_ascribed_name_content",
                "non-localized-string",
                {},
            ),
            (
                CONCEPT_NAME_NODEGROUP,
                CONCEPT_NAME_LANGUAGE_NODE,
                "appellative_status_ascribed_name_language",
                "reference",
                {"controlledList": LANGUAGES_LIST_ID, "multiValue": True},
            ),
        ]:
            NodeGroup.objects.update_or_create(
                pk=nodegroup_id,
                defaults={"cardinality": "1" if node_name == "top_concept_of" else "n"},
            )
            Node.objects.create(
                pk=node_id,
                graph_id=CONCEPTS_GRAPH_ID,
                nodegroup_id=nodegroup_id,
                name=node_name,
                istopnode=False,
                datatype=datatype,
                config=config,
                isrequired=False,
            )

    @classmethod
    def setUpTestData(cls):
        cls.mock_concept_and_scheme_graphs()
        cls.admin = User.objects.get(username="admin")

        # Create a scheme with five concepts, each one narrower than the last,
        # and each concept after the top concept also narrower than the top.
        cls.scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Test Scheme"
        )

        reference = DataTypeFactory().get_instance("reference")
        language_config = {"controlledList": LANGUAGES_LIST_ID}
        label_config = {"controlledList": LABEL_LIST_ID}
        prefLabel_reference_dt = reference.transform_value_for_tile(
            "prefLabel", **label_config
        )
        en_reference_dt = reference.transform_value_for_tile(
            "English", **language_config
        )

        TileModel.objects.create(
            resourceinstance=cls.scheme,
            nodegroup_id=SCHEME_NAME_NODEGROUP,
            data={
                SCHEME_NAME_CONTENT_NODE: "Test Scheme",
                SCHEME_NAME_TYPE_NODE: prefLabel_reference_dt,
                SCHEME_NAME_LANGUAGE_NODE: en_reference_dt,
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

        for i, concept in enumerate(cls.concepts):
            # Create label tile
            TileModel.objects.create(
                resourceinstance=concept,
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data={
                    CONCEPT_NAME_CONTENT_NODE: f"Concept {i + 1}",
                    CONCEPT_NAME_TYPE_NODE: prefLabel_reference_dt,
                    CONCEPT_NAME_LANGUAGE_NODE: en_reference_dt,
                },
            )
            # Create top concept/narrower tile
            if i == 0:
                TileModel.objects.create(
                    resourceinstance=concept,
                    nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                    data={
                        TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [
                            {"resourceId": str(cls.scheme.pk)},
                        ],
                    },
                )
            elif i < MAX_DEPTH:
                TileModel.objects.create(
                    resourceinstance=concept,
                    nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                    data={
                        CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                            # Previous concept
                            {"resourceId": str(cls.concepts[i - 1].pk)},
                            # Also add top concept
                            {"resourceId": str(cls.concepts[0].pk)},
                        ],
                    },
                )
            else:
                TileModel.objects.create(
                    resourceinstance=concept,
                    nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                    data={
                        CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                            # Top concept only
                            {"resourceId": str(cls.concepts[0].pk)},
                        ],
                    },
                )

    def test_get_concept_trees(self):
        self.client.force_login(self.admin)
        with self.assertNumQueries(6):
            # 1: session
            # 2: auth
            # 3: select broader tiles, subquery for labels
            # 4: select top concept tiles, subquery for labels
            # 5: select schemes, subquery for labels
            # 6: languages
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
            c for c in top["narrower"] if c["labels"][0]["value"] == "Concept 2"
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
        self.client.force_login(self.admin)

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

    def test_invalid_search_term(self):
        self.client.force_login(self.admin)
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
        self.client.force_login(self.admin)
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(
                reverse("api-search"), QUERY_STRING="term=test&maxEditDistance=?"
            )
        self.assertContains(
            response,
            "Edit distance could not be converted to an integer.",
            status_code=HTTPStatus.BAD_REQUEST,
        )
