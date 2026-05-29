import json
from http import HTTPStatus

from django.urls import reverse

from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import CONCEPTS_GRAPH_ID, URI_CONTENT_NODE, URI_NODEGROUP

from tests.tests import ViewTests


class ConceptURILookupViewTests(ViewTests):
    TEST_URI = "http://example.com/test-concept-uri-lookup"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.uri_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="URI Lookup Test Concept"
        )
        TileModel.objects.create(
            resourceinstance=cls.uri_concept,
            nodegroup_id=URI_NODEGROUP,
            data={URI_CONTENT_NODE: cls.TEST_URI},
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_returns_resource_instance_id_for_matching_uri(self):
        response = self.client.get(
            reverse("api-lingo-concept-uri-resolve"),
            {"uri": self.TEST_URI},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertEqual(data["resourceinstanceid"], str(self.uri_concept.pk))

    def test_returns_404_for_unknown_uri(self):
        response = self.client.get(
            reverse("api-lingo-concept-uri-resolve"),
            {"uri": "http://example.com/nonexistent"},
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_returns_404_when_uri_param_is_missing(self):
        response = self.client.get(reverse("api-lingo-concept-uri-resolve"))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
