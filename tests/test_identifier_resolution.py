import json
from http import HTTPStatus

from django.urls import reverse

from arches.app.models.models import ResourceIdentifier, ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    SCHEMES_GRAPH_ID,
    IDENTIFIER_SOURCE,
)

from tests.tests import SchemeWithConceptsTestCase


class IdentifierResolveViewTests(SchemeWithConceptsTestCase):
    """Two schemes whose concepts share identifier "1", as the per-scheme
    concept identifier counter produces."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.first_concept = cls.concepts[0]
        cls.other_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Other Scheme"
        )
        cls.other_scheme_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Other Scheme Concept"
        )
        TileModel.objects.create(
            resourceinstance=cls.other_scheme_concept,
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {"resourceId": str(cls.other_scheme.pk)}
                ]
            },
        )

        for resource, identifier in [
            (cls.scheme, "test-scheme"),
            (cls.other_scheme, "other-scheme"),
            (cls.first_concept, "1"),
            (cls.other_scheme_concept, "1"),
            (cls.concepts[1], "2"),
        ]:
            ResourceIdentifier.objects.create(
                resourceid=resource,
                identifier=identifier,
                source=IDENTIFIER_SOURCE,
            )

    def setUp(self):
        self.client.force_login(self.admin)

    def resolve_concept(self, scheme_identifier, concept_identifier):
        return self.client.get(
            reverse(
                "api-lingo-concept-resolve",
                kwargs={
                    "scheme_identifier": scheme_identifier,
                    "concept_identifier": concept_identifier,
                },
            )
        )

    def resolve_scheme(self, scheme_identifier):
        return self.client.get(
            reverse(
                "api-lingo-scheme-resolve",
                kwargs={"scheme_identifier": scheme_identifier},
            )
        )

    def assert_resolves_to(self, response, resource):
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            json.loads(response.content)["resourceinstanceid"], str(resource.pk)
        )

    def test_shared_concept_identifier_resolves_within_each_scheme(self):
        self.assert_resolves_to(
            self.resolve_concept("test-scheme", "1"), self.first_concept
        )
        self.assert_resolves_to(
            self.resolve_concept("other-scheme", "1"), self.other_scheme_concept
        )

    def test_concept_from_another_scheme_is_not_found(self):
        response = self.resolve_concept("other-scheme", "2")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_unknown_scheme_is_not_found(self):
        response = self.resolve_concept("missing-scheme", "1")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_scheme_route_resolves_scheme(self):
        self.assert_resolves_to(self.resolve_scheme("test-scheme"), self.scheme)

    def test_scheme_route_ignores_concept_identifiers(self):
        response = self.resolve_scheme("2")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_concept_route_ignores_scheme_identifiers(self):
        response = self.resolve_concept("test-scheme", "other-scheme")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_dereference_serializes_the_concept_in_the_named_scheme(self):
        response = self.client.get(
            reverse(
                "concept-by-identifier",
                kwargs={
                    "scheme_identifier": "other-scheme",
                    "concept_identifier": "1",
                },
            ),
            HTTP_ACCEPT="text/turtle",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        serialized_concept = response.content.decode()
        self.assertIn(str(self.other_scheme_concept.pk), serialized_concept)
        self.assertNotIn(str(self.first_concept.pk), serialized_concept)
