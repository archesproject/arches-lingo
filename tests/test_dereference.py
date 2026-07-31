import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from pyld import jsonld
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, SKOS

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import ResourceIdentifier, ResourceInstance, TileModel

from arches_lingo.const import (
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.utils.concept_lifecycle import (
    DRAFT_STATE_ID,
    PUBLISHED_STATE_ID,
)
from arches_lingo.utils.skos import ARCHES
from arches_lingo.utils.skos_serializer import (
    NOT_ACCEPTABLE,
    negotiate_rdf_format,
    serialize_resource,
)
from tests.tests import ViewTests

# Controlled list backing match_status_ascribed_relation (SKOS mapping properties).
MAPPING_PROPERTIES_LIST_ID = "769fa072-6247-4e23-b638-4e801f8c50dc"


def _graph_from_jsonld(content):
    """Parse a JSON-LD document into an rdflib Graph via pyld.

    rdflib 4.2.2 has no JSON-LD parser, so bridge through N-Quads like the
    serializer does in the other direction.
    """
    nquads = jsonld.to_rdf(json.loads(content), {"format": "application/nquads"})
    return Graph().parse(data=nquads, format="nquads")


class NegotiateRdfFormatTests(SimpleTestCase):
    """Content negotiation is pure logic; exercise it directly without the DB."""

    def test_explicit_format_tokens(self):
        for token, expected in [
            ("jsonld", "jsonld"),
            ("xml", "xml"),
            ("turtle", "turtle"),
            ("nt", "nt"),
        ]:
            self.assertEqual(negotiate_rdf_format("", explicit_format=token), expected)

    def test_explicit_format_aliases(self):
        for token, expected in [
            ("json-ld", "jsonld"),
            ("ttl", "turtle"),
            ("rdf", "xml"),
            ("n-triples", "nt"),
        ]:
            self.assertEqual(negotiate_rdf_format("", explicit_format=token), expected)

    def test_explicit_html_is_the_spa(self):
        self.assertIsNone(negotiate_rdf_format("", explicit_format="html"))

    def test_explicit_unsupported_format_is_not_acceptable(self):
        self.assertIs(negotiate_rdf_format("", explicit_format="csv"), NOT_ACCEPTABLE)

    def test_accept_header_maps_to_format(self):
        for accept, expected in [
            ("application/ld+json", "jsonld"),
            ("application/rdf+xml", "xml"),
            ("text/turtle", "turtle"),
            ("application/n-triples", "nt"),
        ]:
            self.assertEqual(negotiate_rdf_format(accept), expected)

    def test_browser_accept_headers_get_the_spa(self):
        self.assertIsNone(negotiate_rdf_format("text/html,application/xhtml+xml,*/*"))
        self.assertIsNone(negotiate_rdf_format("*/*"))
        self.assertIsNone(negotiate_rdf_format(""))

    def test_quality_values_decide_the_winner(self):
        # HTML preferred over RDF -> serve the SPA.
        self.assertIsNone(
            negotiate_rdf_format("application/ld+json;q=0.2, text/html;q=0.9")
        )
        # RDF preferred over HTML -> serve RDF.
        self.assertEqual(
            negotiate_rdf_format("text/html;q=0.5, application/ld+json;q=0.9"),
            "jsonld",
        )

    def test_explicit_format_beats_accept_header(self):
        self.assertEqual(
            negotiate_rdf_format("text/html", explicit_format="turtle"), "turtle"
        )


class _LingoResourceTestCase(TestCase):
    """Reuses the ViewTests fixture (a scheme with five hierarchical concepts)."""

    @classmethod
    def setUpTestData(cls):
        ViewTests.setUpTestData()
        cls.scheme = ResourceInstance.objects.get(name="Test Scheme")
        cls.concept_1 = ResourceInstance.objects.get(name="Concept 1")  # top concept
        cls.concept_2 = ResourceInstance.objects.get(name="Concept 2")  # narrower

    @staticmethod
    def _add_uri_tile(resource, uri):
        TileModel.objects.create(
            resourceinstance=resource,
            nodegroup_id=URI_NODEGROUP,
            data={URI_CONTENT_NODE: uri},
        )


class SkosSerializerTests(_LingoResourceTestCase):
    def test_serialize_concept_emits_skos_concept_with_relations(self):
        body, content_type = serialize_resource(self.concept_2.pk, "concept", "xml")
        self.assertEqual(content_type, "application/rdf+xml")

        graph = Graph().parse(data=body, format="xml")
        subject = ARCHES[str(self.concept_2.pk)]

        self.assertIn((subject, RDF.type, SKOS.Concept), graph)
        self.assertIn((subject, SKOS.prefLabel, Literal("Concept 2", lang="en")), graph)
        # Concept 2 is narrower than Concept 1 and in the scheme.
        self.assertIn((subject, SKOS.broader, ARCHES[str(self.concept_1.pk)]), graph)
        self.assertIn((subject, SKOS.inScheme, ARCHES[str(self.scheme.pk)]), graph)

    def test_serialize_scheme_emits_concept_scheme(self):
        body, _content_type = serialize_resource(self.scheme.pk, "scheme", "xml")
        graph = Graph().parse(data=body, format="xml")
        subject = ARCHES[str(self.scheme.pk)]

        self.assertIn((subject, RDF.type, SKOS.ConceptScheme), graph)
        self.assertIn(
            (subject, SKOS.prefLabel, Literal("Test Scheme", lang="en")), graph
        )

    def test_serialize_scheme_enumerates_top_concepts(self):
        # Concept 1 is the top concept of the scheme in the fixture data.
        body, _content_type = serialize_resource(self.scheme.pk, "scheme", "xml")
        graph = Graph().parse(data=body, format="xml")
        self.assertIn(
            (
                ARCHES[str(self.scheme.pk)],
                SKOS.hasTopConcept,
                ARCHES[str(self.concept_1.pk)],
            ),
            graph,
        )

    def test_serialize_concept_emits_match_as_uri_reference(self):
        external_uri = "http://vocab.getty.edu/aat/300000000"
        exact_match_reference = (
            DataTypeFactory()
            .get_instance("reference")
            .transform_value_for_tile(
                "exactMatch", controlledList=MAPPING_PROPERTIES_LIST_ID
            )
        )
        TileModel.objects.create(
            resourceinstance=self.concept_2,
            nodegroup_id=MATCH_STATUS_NODEGROUP,
            data={
                MATCH_STATUS_RELATION_NODE: exact_match_reference,
                MATCH_STATUS_COMPARATE_NODE: external_uri,
            },
        )

        body, _content_type = serialize_resource(self.concept_2.pk, "concept", "xml")
        graph = Graph().parse(data=body, format="xml")
        subject = ARCHES[str(self.concept_2.pk)]

        # The match target is a URI reference (not a string literal), under a SKOS
        # mapping predicate.
        match_objects = set(graph.objects(subject, SKOS.exactMatch))
        self.assertIn(URIRef(external_uri), match_objects)

    def test_every_rdf_format_round_trips(self):
        for rdf_format, parse_format, expected_type in [
            ("jsonld", None, "application/ld+json"),
            ("xml", "xml", "application/rdf+xml"),
            ("turtle", "turtle", "text/turtle; charset=utf-8"),
            ("nt", "nt", "application/n-triples"),
        ]:
            with self.subTest(rdf_format=rdf_format):
                body, content_type = serialize_resource(
                    self.concept_2.pk, "concept", rdf_format
                )
                self.assertEqual(content_type, expected_type)
                if rdf_format == "jsonld":
                    graph = _graph_from_jsonld(body)
                else:
                    graph = Graph().parse(data=body, format=parse_format)
                self.assertIn(
                    (ARCHES[str(self.concept_2.pk)], RDF.type, SKOS.Concept), graph
                )

    def test_public_uri_becomes_subject_and_links_use_it(self):
        concept_2_uri = "https://vocab.example.org/schemes/test/concepts/c2"
        concept_1_uri = "https://vocab.example.org/schemes/test/concepts/c1"
        self._add_uri_tile(self.concept_2, concept_2_uri)
        self._add_uri_tile(self.concept_1, concept_1_uri)

        body, _content_type = serialize_resource(self.concept_2.pk, "concept", "xml")
        graph = Graph().parse(data=body, format="xml")

        subject = URIRef(concept_2_uri)
        # The public URI is the subject, and the UUID form is retained via owl:sameAs.
        self.assertIn((subject, RDF.type, SKOS.Concept), graph)
        self.assertIn((subject, OWL.sameAs, ARCHES[str(self.concept_2.pk)]), graph)
        # A link to another resource uses that resource's public URI, not its UUID.
        self.assertIn((subject, SKOS.broader, URIRef(concept_1_uri)), graph)

    def test_retired_resource_is_marked_deprecated(self):
        body, _content_type = serialize_resource(
            self.concept_2.pk, "concept", "xml", mark_deprecated=True
        )
        graph = Graph().parse(data=body, format="xml")
        self.assertIn(
            (ARCHES[str(self.concept_2.pk)], OWL.deprecated, Literal(True)), graph
        )

    def test_missing_resource_returns_none(self):
        body, content_type = serialize_resource(
            "00000000-0000-0000-0000-000000000000", "concept", "xml"
        )
        self.assertIsNone(body)
        self.assertIsNone(content_type)


class DereferenceViewTests(_LingoResourceTestCase):
    def setUp(self):
        self.admin = User.objects.get(username="admin")

    def _set_state(self, resource, state_id):
        ResourceInstance.objects.filter(pk=resource.pk).update(
            resource_instance_lifecycle_state_id=state_id
        )

    @patch("arches_lingo.views.api.dereference.LingoRootView")
    def test_browser_request_delegates_to_spa(self, mock_root_view):
        mock_root_view.as_view.return_value = lambda request, *a, **k: HttpResponse(
            "SPA-HTML"
        )
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("concept", kwargs={"id": self.concept_2.pk}),
            HTTP_ACCEPT="text/html,application/xhtml+xml,*/*",
        )
        self.assertEqual(response.content, b"SPA-HTML")

    def test_accept_ldjson_returns_negotiated_skos(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("concept", kwargs={"id": self.concept_2.pk}),
            HTTP_ACCEPT="application/ld+json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/ld+json")
        self.assertIn("Accept", response["Vary"])
        graph = _graph_from_jsonld(response.content)
        self.assertIn((ARCHES[str(self.concept_2.pk)], RDF.type, SKOS.Concept), graph)

    def test_format_query_overrides_accept(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("concept", kwargs={"id": self.concept_2.pk}),
            {"format": "turtle"},
            HTTP_ACCEPT="text/html",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/turtle; charset=utf-8")

    def test_unsupported_format_returns_406(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("concept", kwargs={"id": self.concept_2.pk}),
            {"format": "csv"},
        )
        self.assertEqual(response.status_code, 406)

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True)
    def test_anonymous_can_dereference_published_resource(self):
        self._set_state(self.concept_2, PUBLISHED_STATE_ID)
        response = self.client.get(
            reverse("concept", kwargs={"id": self.concept_2.pk}),
            HTTP_ACCEPT="application/ld+json",
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True)
    def test_anonymous_cannot_dereference_draft_resource(self):
        self._set_state(self.concept_2, DRAFT_STATE_ID)
        response = self.client.get(
            reverse("concept", kwargs={"id": self.concept_2.pk}),
            HTTP_ACCEPT="application/ld+json",
        )
        self.assertEqual(response.status_code, 404)

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=False)
    def test_anonymous_denied_when_setting_disabled(self):
        self._set_state(self.concept_2, PUBLISHED_STATE_ID)
        response = self.client.get(
            reverse("concept", kwargs={"id": self.concept_2.pk}),
            HTTP_ACCEPT="application/ld+json",
        )
        self.assertEqual(response.status_code, 404)

    def test_authenticated_user_can_preview_draft(self):
        self._set_state(self.concept_2, DRAFT_STATE_ID)
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("concept", kwargs={"id": self.concept_2.pk}),
            HTTP_ACCEPT="application/ld+json",
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True)
    def test_slug_route_resolves_and_serializes(self):
        self._set_state(self.scheme, PUBLISHED_STATE_ID)
        ResourceIdentifier.objects.create(
            resourceid=self.scheme,
            identifier="test-scheme",
            source="arches-lingo",
        )
        response = self.client.get(
            reverse(
                "scheme-by-identifier", kwargs={"scheme_identifier": "test-scheme"}
            ),
            HTTP_ACCEPT="text/turtle",
        )
        self.assertEqual(response.status_code, 200)
        graph = Graph().parse(data=response.content, format="turtle")
        self.assertIn(
            (ARCHES[str(self.scheme.pk)], RDF.type, SKOS.ConceptScheme), graph
        )
