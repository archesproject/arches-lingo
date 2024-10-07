import json
from http import HTTPStatus

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

# these tests can be run from the command line via
# python manage.py test tests.tests --settings="tests.test_settings"

from arches.app.models.models import (
    Concept,
    GraphModel,
    Node,
    NodeGroup,
    Relation,
    ResourceInstance,
    TileModel,
    Value,
)

from arches_lingo.const import (
    ENGLISH_VALUE_ID,
    CONCEPTS_GRAPH_ID,
    LANGUAGE_CONCEPT_ID,
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
    PREF_LABEL_VALUE_ID,
)


def setUpModule():
    """Bootstrap just a few nodes as an alternative to loading the entire package."""
    if not GraphModel.objects.filter(pk=SCHEMES_GRAPH_ID).exists():
        GraphModel.objects.create(pk=SCHEMES_GRAPH_ID, isresource=True)
        GraphModel.objects.create(pk=CONCEPTS_GRAPH_ID, isresource=True)

        for nodegroup_id, node_id, node_name, datatype in [
            (
                TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                "top_concept_of",
                "concept-list",
            ),
            (
                CLASSIFICATION_STATUS_NODEGROUP,
                CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
                "classification_status_ascribed_classification",
                "concept-list",
            ),
            (
                SCHEME_NAME_NODEGROUP,
                SCHEME_NAME_CONTENT_NODE,
                "appellative_status_ascribed_name_content",
                "concept-list",
            ),
            (
                SCHEME_NAME_NODEGROUP,
                SCHEME_NAME_LANGUAGE_NODE,
                "appellative_status_ascribed_name_language",
                "string",
            ),
            (
                CONCEPT_NAME_NODEGROUP,
                CONCEPT_NAME_CONTENT_NODE,
                "appellative_status_ascribed_name_content",
                "concept-list",
            ),
            (
                CONCEPT_NAME_NODEGROUP,
                CONCEPT_NAME_LANGUAGE_NODE,
                "appellative_status_ascribed_name_language",
                "string",
            ),
        ]:
            NodeGroup.objects.update_or_create(
                pk=nodegroup_id, defaults={"cardinality": "n"}
            )
            Node.objects.create(
                pk=node_id,
                graph_id=CONCEPTS_GRAPH_ID,
                nodegroup_id=nodegroup_id,
                name=node_name,
                istopnode=False,
                datatype=datatype,
                isrequired=datatype == "string",
            )

    Concept.objects.get_or_create(
        conceptid=LANGUAGE_CONCEPT_ID,
        nodetype_id="Concept",
    )
    Value.objects.get_or_create(
        concept_id=LANGUAGE_CONCEPT_ID,
        valueid=ENGLISH_VALUE_ID,
        valuetype_id="prefLabel",
        value="en",
    )
    Relation.objects.get_or_create(
        conceptfrom_id=LANGUAGE_CONCEPT_ID,
        conceptto_id=LANGUAGE_CONCEPT_ID,
        relationtype_id="narrower",
    )


def localized_string(text, language="en", direction="ltr"):
    return {language: {"value": text, "direction": direction}}


class ViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(username="admin")

        # Create a scheme with five concepts, each one narrower than the last,
        # and each concept after the top concept also narrower than the top.
        cls.scheme = ResourceInstance.objects.create(graph_id=SCHEMES_GRAPH_ID)
        TileModel.objects.create(
            resourceinstance=cls.scheme,
            nodegroup_id=SCHEME_NAME_NODEGROUP,
            data={
                SCHEME_NAME_CONTENT_NODE: localized_string("Test Scheme"),
                SCHEME_NAME_TYPE_NODE: PREF_LABEL_VALUE_ID,
                SCHEME_NAME_LANGUAGE_NODE: [ENGLISH_VALUE_ID],
            },
        )

        MAX_DEPTH = 5
        CONCEPT_COUNT = 5
        cls.concepts = [
            ResourceInstance(graph_id=CONCEPTS_GRAPH_ID) for _ in range(CONCEPT_COUNT)
        ]
        for concept in cls.concepts:
            concept.save()

        for i, concept in enumerate(cls.concepts):
            # Create label tile
            TileModel.objects.create(
                resourceinstance=concept,
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data={
                    CONCEPT_NAME_CONTENT_NODE: localized_string(f"Concept {i + 1}"),
                    CONCEPT_NAME_TYPE_NODE: PREF_LABEL_VALUE_ID,
                    CONCEPT_NAME_LANGUAGE_NODE: [ENGLISH_VALUE_ID],
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
            # 3: select relations (to find languages)
            # 4: select broader tiles, subquery for labels
            # 5: select top concept tiles, subquery for labels
            # 6: select schemes, subquery for labels
            response = self.client.get(reverse("api-concepts"))

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        scheme = result["schemes"][0]

        self.assertEqual(scheme["labels"][0]["value"], "Test Scheme")
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
