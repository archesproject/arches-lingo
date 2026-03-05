"""Tests for advanced search: query evaluator and API views."""

import datetime
import json
import uuid
from http import HTTPStatus
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core import management
from django.test import TestCase
from django.test.utils import captured_stdout
from django.urls import reverse

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import (
    ResourceInstance,
    ResourceXResource,
    TileModel,
)
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.data_management.resource_graphs.importer import (
    import_graph as ResourceGraphImporter,
)

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    SCHEMES_GRAPH_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_TYPE_NODE,
    RELATION_STATUS_NODEGROUP,
    RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,
    LABEL_LIST_ID,
    STATEMENT_NODEGROUP,
    STATEMENT_CONTENT_NODE,
    STATEMENT_LANGUAGE_NODE,
    STATEMENT_TYPE_NODE,
    URI_NODEGROUP,
    URI_CONTENT_NODE,
    IDENTIFIER_NODEGROUP,
    IDENTIFIER_CONTENT_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_COMPARATE_NODE,
    CONCEPT_TYPE_NODE,
    STATUS_NODEGROUP,
)
from arches_lingo.models import ConceptSet, ConceptSetMember, SavedSearch
from arches_lingo.utils.advanced_search import AdvancedSearchEvaluator


# ────────────────────────────────────────────────────────────────
# Evaluator tests  (require graph fixtures + tile data)
# ────────────────────────────────────────────────────────────────


class AdvancedSearchEvaluatorTests(TestCase):
    """Tests for AdvancedSearchEvaluator — facet evaluation logic."""

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
    def setUpTestData(cls):
        cls.load_ontology()
        cls.load_graphs()
        cls.admin = User.objects.get(username="admin")

        reference = DataTypeFactory().get_instance("reference")
        label_config = {"controlledList": LABEL_LIST_ID}
        cls.prefLabel_ref = reference.transform_value_for_tile(
            "prefLabel", **label_config
        )

        cls.scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Evaluator Scheme"
        )
        TileModel.objects.create(
            resourceinstance=cls.scheme,
            nodegroup_id=SCHEME_NAME_NODEGROUP,
            data={
                SCHEME_NAME_CONTENT_NODE: "Evaluator Scheme",
                SCHEME_NAME_TYPE_NODE: cls.prefLabel_ref,
                SCHEME_NAME_LANGUAGE_NODE: "en",
            },
        )

        # Create three concepts with different data to exercise facets.
        cls.concept_a = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Alpha Concept"
        )
        cls.concept_b = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Beta Concept"
        )
        cls.concept_c = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Gamma Concept"
        )

        now = datetime.datetime.now()

        # ── Labels ──
        TileModel.objects.create(
            resourceinstance=cls.concept_a,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "Alpha Concept",
                CONCEPT_NAME_TYPE_NODE: cls.prefLabel_ref,
                CONCEPT_NAME_LANGUAGE_NODE: "en",
            },
        )
        TileModel.objects.create(
            resourceinstance=cls.concept_b,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "Beta Concept",
                CONCEPT_NAME_TYPE_NODE: cls.prefLabel_ref,
                CONCEPT_NAME_LANGUAGE_NODE: "en",
            },
        )
        TileModel.objects.create(
            resourceinstance=cls.concept_b,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "Beta Konzept",
                CONCEPT_NAME_TYPE_NODE: cls.prefLabel_ref,
                CONCEPT_NAME_LANGUAGE_NODE: "de",
            },
        )
        TileModel.objects.create(
            resourceinstance=cls.concept_c,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "Gamma Concept",
                CONCEPT_NAME_TYPE_NODE: cls.prefLabel_ref,
                CONCEPT_NAME_LANGUAGE_NODE: "en",
            },
        )

        # ── Notes (statement) ──
        TileModel.objects.create(
            resourceinstance=cls.concept_a,
            nodegroup_id=STATEMENT_NODEGROUP,
            data={
                STATEMENT_CONTENT_NODE: "Alpha definition note",
                STATEMENT_LANGUAGE_NODE: "en",
                STATEMENT_TYPE_NODE: [],
            },
        )
        TileModel.objects.create(
            resourceinstance=cls.concept_c,
            nodegroup_id=STATEMENT_NODEGROUP,
            data={
                STATEMENT_CONTENT_NODE: "Gamma scope note about sculpture",
                STATEMENT_LANGUAGE_NODE: "en",
                STATEMENT_TYPE_NODE: [],
            },
        )

        # ── URI ──
        TileModel.objects.create(
            resourceinstance=cls.concept_a,
            nodegroup_id=URI_NODEGROUP,
            data={
                URI_CONTENT_NODE: {
                    "url": "http://example.com/alpha",
                    "url_label": "Alpha URI",
                },
            },
        )

        # ── Identifier ──
        TileModel.objects.create(
            resourceinstance=cls.concept_b,
            nodegroup_id=IDENTIFIER_NODEGROUP,
            data={
                IDENTIFIER_CONTENT_NODE: "ID-BETA-001",
            },
        )

        # ── Match status ──
        TileModel.objects.create(
            resourceinstance=cls.concept_a,
            nodegroup_id=MATCH_STATUS_NODEGROUP,
            data={
                MATCH_STATUS_COMPARATE_NODE: "http://vocab.getty.edu/aat/12345",
            },
        )

        # ── Part of scheme ──
        for concept in [cls.concept_a, cls.concept_b, cls.concept_c]:
            rxr = ResourceXResource.objects.create(
                from_resource=concept,
                from_resource_graph_id=CONCEPTS_GRAPH_ID,
                to_resource=cls.scheme,
                to_resource_graph_id=SCHEMES_GRAPH_ID,
                created=now,
                modified=now,
            )
            TileModel.objects.create(
                resourceinstance=concept,
                nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                data={
                    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                        {
                            "resourceId": str(cls.scheme.pk),
                            "resourceXresourceId": str(rxr.pk),
                        },
                    ],
                },
            )

        # ── Top concept of ──
        top_rxr = ResourceXResource.objects.create(
            from_resource=cls.concept_a,
            from_resource_graph_id=CONCEPTS_GRAPH_ID,
            to_resource=cls.scheme,
            to_resource_graph_id=SCHEMES_GRAPH_ID,
            created=now,
            modified=now,
        )
        TileModel.objects.create(
            resourceinstance=cls.concept_a,
            nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
            data={
                TOP_CONCEPT_OF_NODE_AND_NODEGROUP: [
                    {
                        "resourceId": str(cls.scheme.pk),
                        "resourceXresourceId": str(top_rxr.pk),
                    },
                ],
            },
        )

        # ── Hierarchy: B broader A, C broader A ──
        for child in [cls.concept_b, cls.concept_c]:
            hier_rxr = ResourceXResource.objects.create(
                from_resource=child,
                from_resource_graph_id=CONCEPTS_GRAPH_ID,
                to_resource=cls.concept_a,
                to_resource_graph_id=CONCEPTS_GRAPH_ID,
                created=now,
                modified=now,
            )
            TileModel.objects.create(
                resourceinstance=child,
                nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP,
                data={
                    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID: [
                        {
                            "resourceId": str(cls.concept_a.pk),
                            "resourceXresourceId": str(hier_rxr.pk),
                        },
                    ],
                },
            )

        # ── Association: A ↔ C ──
        assoc_rxr = ResourceXResource.objects.create(
            from_resource=cls.concept_a,
            from_resource_graph_id=CONCEPTS_GRAPH_ID,
            to_resource=cls.concept_c,
            to_resource_graph_id=CONCEPTS_GRAPH_ID,
            created=now,
            modified=now,
        )
        TileModel.objects.create(
            resourceinstance=cls.concept_a,
            nodegroup_id=RELATION_STATUS_NODEGROUP,
            data={
                RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: [
                    {
                        "resourceId": str(cls.concept_c.pk),
                        "resourceXresourceId": str(assoc_rxr.pk),
                    },
                ],
            },
        )

    def setUp(self):
        self.evaluator = AdvancedSearchEvaluator(user=self.admin)

    # ── evaluate() core behaviour ───────────────────────────────

    def test_empty_query_returns_all(self):
        """An empty dict should return all concept IDs."""
        result = self.evaluator.evaluate({})
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    def test_invalid_facet_returns_empty(self):
        result = self.evaluator.evaluate({"facet": "nonexistent", "value": "x"})
        self.assertEqual(result, [])

    def test_group_no_conditions_returns_all(self):
        result = self.evaluator.evaluate({"operator": "and", "conditions": []})
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    # ── Label facet ─────────────────────────────────────────────

    def test_facet_label_text_match(self):
        result = self.evaluator.evaluate({"facet": "label", "value": "Alpha"})
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertNotIn(self.concept_b.pk, ids)

    def test_facet_label_case_insensitive(self):
        result = self.evaluator.evaluate({"facet": "label", "value": "alpha"})
        self.assertIn(self.concept_a.pk, set(result))

    def test_facet_label_language_filter(self):
        result = self.evaluator.evaluate(
            {"facet": "label", "value": "Konzept", "language": "de"}
        )
        ids = set(result)
        self.assertIn(self.concept_b.pk, ids)
        self.assertNotIn(self.concept_a.pk, ids)

    def test_facet_label_empty_value_returns_all_with_labels(self):
        result = self.evaluator.evaluate({"facet": "label", "value": ""})
        # All three concepts have labels
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_c.pk, ids)

    # ── Note facet ──────────────────────────────────────────────

    def test_facet_note_text_match(self):
        result = self.evaluator.evaluate({"facet": "note", "value": "sculpture"})
        ids = set(result)
        self.assertIn(self.concept_c.pk, ids)
        self.assertNotIn(self.concept_b.pk, ids)

    def test_facet_note_alpha_match(self):
        result = self.evaluator.evaluate({"facet": "note", "value": "definition"})
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)

    def test_facet_note_no_match(self):
        result = self.evaluator.evaluate({"facet": "note", "value": "zzz_nonexistent"})
        self.assertEqual(len(result), 0)

    # ── Language facet ──────────────────────────────────────────

    def test_facet_language_english(self):
        result = self.evaluator.evaluate({"facet": "language", "value": "en"})
        ids = set(result)
        # All three have English labels, plus A and C have English notes
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_c.pk, ids)

    def test_facet_language_german(self):
        result = self.evaluator.evaluate({"facet": "language", "value": "de"})
        ids = set(result)
        self.assertIn(self.concept_b.pk, ids)
        self.assertNotIn(self.concept_a.pk, ids)
        self.assertNotIn(self.concept_c.pk, ids)

    def test_facet_language_empty_returns_all(self):
        result = self.evaluator.evaluate({"facet": "language", "value": ""})
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    # ── URI facet ───────────────────────────────────────────────

    def test_facet_uri_match(self):
        result = self.evaluator.evaluate({"facet": "uri", "value": "alpha"})
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertNotIn(self.concept_b.pk, ids)

    def test_facet_uri_empty_returns_all(self):
        result = self.evaluator.evaluate({"facet": "uri", "value": ""})
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    # ── Identifier facet ────────────────────────────────────────

    def test_facet_identifier_match(self):
        result = self.evaluator.evaluate({"facet": "identifier", "value": "BETA"})
        ids = set(result)
        self.assertIn(self.concept_b.pk, ids)
        self.assertNotIn(self.concept_a.pk, ids)

    def test_facet_identifier_empty_returns_all(self):
        result = self.evaluator.evaluate({"facet": "identifier", "value": ""})
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    # ── Match URI facet ─────────────────────────────────────────

    def test_facet_match_uri(self):
        result = self.evaluator.evaluate({"facet": "match_uri", "value": "getty"})
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertNotIn(self.concept_b.pk, ids)

    def test_facet_match_uri_empty_returns_all(self):
        result = self.evaluator.evaluate({"facet": "match_uri", "value": ""})
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    # ── Scheme facet ────────────────────────────────────────────

    def test_facet_scheme_finds_members(self):
        result = self.evaluator.evaluate(
            {"facet": "scheme", "value": str(self.scheme.pk)}
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_c.pk, ids)

    def test_facet_scheme_empty_returns_all(self):
        result = self.evaluator.evaluate({"facet": "scheme", "value": ""})
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    # ── Hierarchical relationship facet ─────────────────────────

    def test_facet_relationship_hierarchical_broader(self):
        """B and C both have A as broader."""
        result = self.evaluator.evaluate(
            {
                "facet": "relationship_hierarchical",
                "value": str(self.concept_a.pk),
                "direction": "broader",
            }
        )
        ids = set(result)
        self.assertIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_c.pk, ids)
        self.assertNotIn(self.concept_a.pk, ids)

    def test_facet_relationship_hierarchical_narrower(self):
        """A is the broader concept of B — asking narrower of B should yield A."""
        result = self.evaluator.evaluate(
            {
                "facet": "relationship_hierarchical",
                "value": str(self.concept_b.pk),
                "direction": "narrower",
            }
        )
        # narrower handler returns string IDs from tile data JSON
        ids = set(str(resource_id) for resource_id in result)
        self.assertIn(str(self.concept_a.pk), ids)

    def test_facet_relationship_hierarchical_empty_returns_all(self):
        result = self.evaluator.evaluate(
            {
                "facet": "relationship_hierarchical",
                "value": "",
            }
        )
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    # ── Associated relationship facet ───────────────────────────

    def test_facet_relationship_associated_forward(self):
        """A has C as an associated concept."""
        result = self.evaluator.evaluate(
            {
                "facet": "relationship_associated",
                "value": str(self.concept_c.pk),
            }
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)

    def test_facet_relationship_associated_reverse(self):
        """C is associated with A (reverse direction)."""
        result = self.evaluator.evaluate(
            {
                "facet": "relationship_associated",
                "value": str(self.concept_a.pk),
            }
        )
        # reverse handler returns string IDs from tile data JSON
        ids = set(str(resource_id) for resource_id in result)
        # A's tiles list C, so querying for A finds concepts whose tiles
        # reference A — that's the reverse direction. C should be found via
        # the tile on A that references C.
        self.assertIn(str(self.concept_c.pk), ids)

    def test_facet_relationship_associated_empty_returns_all(self):
        result = self.evaluator.evaluate(
            {
                "facet": "relationship_associated",
                "value": "",
            }
        )
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    # ── Concept set facet ───────────────────────────────────────

    def test_facet_concept_set(self):
        concept_set = ConceptSet.objects.create(user=self.admin, name="Eval Set")
        ConceptSetMember.objects.create(
            concept_set=concept_set, concept_id=self.concept_a.pk
        )
        ConceptSetMember.objects.create(
            concept_set=concept_set, concept_id=self.concept_c.pk
        )
        result = self.evaluator.evaluate(
            {
                "facet": "concept_set",
                "value": str(concept_set.pk),
            }
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_c.pk, ids)
        self.assertNotIn(self.concept_b.pk, ids)

    def test_facet_concept_set_empty_returns_empty(self):
        result = self.evaluator.evaluate({"facet": "concept_set", "value": ""})
        self.assertEqual(result, [])

    def test_facet_concept_set_nonexistent_returns_empty(self):
        result = self.evaluator.evaluate({"facet": "concept_set", "value": "99999"})
        self.assertEqual(result, [])

    # ── Boolean group logic ─────────────────────────────────────

    def test_and_group_intersection(self):
        """AND of label=Alpha + note=definition → only concept A."""
        query = {
            "operator": "and",
            "conditions": [
                {"facet": "label", "value": "Alpha"},
                {"facet": "note", "value": "definition"},
            ],
        }
        result = self.evaluator.evaluate(query)
        ids = set(result)
        self.assertEqual(ids, {self.concept_a.pk})

    def test_or_group_union(self):
        """OR of label=Alpha + label=Beta → A and B."""
        query = {
            "operator": "or",
            "conditions": [
                {"facet": "label", "value": "Alpha"},
                {"facet": "label", "value": "Beta"},
            ],
        }
        result = self.evaluator.evaluate(query)
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_b.pk, ids)
        self.assertNotIn(self.concept_c.pk, ids)

    def test_and_contradictory_returns_empty(self):
        """AND of label=Alpha + label=Gamma → empty (no concept has both)."""
        query = {
            "operator": "and",
            "conditions": [
                {"facet": "label", "value": "Alpha"},
                {"facet": "label", "value": "Gamma"},
            ],
        }
        result = self.evaluator.evaluate(query)
        self.assertEqual(len(result), 0)

    def test_nested_groups(self):
        """Nested group: (label=Alpha OR label=Beta) AND note=definition → A."""
        query = {
            "operator": "and",
            "conditions": [
                {
                    "operator": "or",
                    "conditions": [
                        {"facet": "label", "value": "Alpha"},
                        {"facet": "label", "value": "Beta"},
                    ],
                },
                {"facet": "note", "value": "definition"},
            ],
        }
        result = self.evaluator.evaluate(query)
        ids = set(result)
        self.assertEqual(ids, {self.concept_a.pk})

    # ── Lifecycle state facet (no data, tests the empty path) ──

    def test_facet_lifecycle_state_empty_returns_all(self):
        result = self.evaluator.evaluate({"facet": "lifecycle_state", "value": ""})
        all_concepts = {self.concept_a.pk, self.concept_b.pk, self.concept_c.pk}
        self.assertTrue(all_concepts.issubset(set(result)))

    # ── Match mode tests ────────────────────────────────────────

    def test_match_mode_contains(self):
        """Default 'contains' match finds partial text."""
        result = self.evaluator.evaluate(
            {"facet": "label", "value": "Alph", "match_mode": "contains"}
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertNotIn(self.concept_b.pk, ids)

    def test_match_mode_exact(self):
        """Exact match only returns concepts with that exact label."""
        result = self.evaluator.evaluate(
            {"facet": "label", "value": "Alpha Concept", "match_mode": "exact"}
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertNotIn(self.concept_b.pk, ids)

    def test_match_mode_exact_no_partial(self):
        """Exact match does not find partial text."""
        result = self.evaluator.evaluate(
            {"facet": "label", "value": "Alpha", "match_mode": "exact"}
        )
        self.assertEqual(len(result), 0)

    def test_match_mode_starts_with(self):
        """starts_with finds labels starting with the given text."""
        result = self.evaluator.evaluate(
            {"facet": "label", "value": "Beta", "match_mode": "starts_with"}
        )
        ids = set(result)
        self.assertIn(self.concept_b.pk, ids)
        self.assertNotIn(self.concept_a.pk, ids)

    def test_match_mode_ends_with(self):
        """ends_with finds labels ending with the given text."""
        result = self.evaluator.evaluate(
            {"facet": "label", "value": "Concept", "match_mode": "ends_with"}
        )
        ids = set(result)
        # All three concepts have labels ending in "Concept"
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_c.pk, ids)

    def test_match_mode_exists_label(self):
        """'exists' match returns concepts that have any label."""
        result = self.evaluator.evaluate(
            {"facet": "label", "value": "", "match_mode": "exists"}
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_c.pk, ids)

    def test_match_mode_exists_note(self):
        """'exists' note match returns only concepts with notes."""
        result = self.evaluator.evaluate(
            {"facet": "note", "value": "", "match_mode": "exists"}
        )
        ids = set(result)
        # Only A and C have notes
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_c.pk, ids)
        self.assertNotIn(self.concept_b.pk, ids)

    def test_match_mode_exists_identifier(self):
        """'exists' identifier match returns only concepts with identifiers."""
        result = self.evaluator.evaluate(
            {"facet": "identifier", "value": "", "match_mode": "exists"}
        )
        ids = set(result)
        # Only B has an identifier
        self.assertIn(self.concept_b.pk, ids)
        self.assertNotIn(self.concept_a.pk, ids)

    def test_match_mode_note_starts_with(self):
        """starts_with works on notes too."""
        result = self.evaluator.evaluate(
            {"facet": "note", "value": "Alpha", "match_mode": "starts_with"}
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)
        self.assertNotIn(self.concept_c.pk, ids)

    def test_match_mode_identifier_exact(self):
        """Exact match on identifier."""
        result = self.evaluator.evaluate(
            {"facet": "identifier", "value": "ID-BETA-001", "match_mode": "exact"}
        )
        ids = set(result)
        self.assertIn(self.concept_b.pk, ids)

    def test_match_mode_identifier_partial_no_exact(self):
        """Exact match does not find partial identifier."""
        result = self.evaluator.evaluate(
            {"facet": "identifier", "value": "BETA", "match_mode": "exact"}
        )
        self.assertEqual(len(result), 0)

    def test_match_mode_uri_starts_with(self):
        """starts_with on URI content."""
        result = self.evaluator.evaluate(
            {"facet": "uri", "value": "http://example", "match_mode": "starts_with"}
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)

    def test_match_mode_uri_exists(self):
        """'exists' on URI returns only concepts with a URI."""
        result = self.evaluator.evaluate(
            {"facet": "uri", "value": "", "match_mode": "exists"}
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)

    def test_match_mode_match_uri_exact(self):
        """Exact match on match_uri (Getty URI)."""
        result = self.evaluator.evaluate(
            {
                "facet": "match_uri",
                "value": "http://vocab.getty.edu/aat/12345",
                "match_mode": "exact",
            }
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)

    def test_match_mode_match_uri_exists(self):
        """'exists' on match_uri returns concepts with any match URI."""
        result = self.evaluator.evaluate(
            {"facet": "match_uri", "value": "", "match_mode": "exists"}
        )
        ids = set(result)
        self.assertIn(self.concept_a.pk, ids)

    # ── Negation tests ──────────────────────────────────────────

    def test_negation_excludes_matched(self):
        """Negated label=Alpha returns everything except Alpha."""
        result = self.evaluator.evaluate(
            {"facet": "label", "value": "Alpha", "negated": True}
        )
        ids = set(result)
        self.assertNotIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_c.pk, ids)

    def test_negation_note(self):
        """Negated note=definition excludes A (which has it)."""
        result = self.evaluator.evaluate(
            {"facet": "note", "value": "definition", "negated": True}
        )
        ids = set(result)
        self.assertNotIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_c.pk, ids)

    def test_negation_with_match_mode(self):
        """Negation combined with match mode: NOT starts_with Beta → no B."""
        result = self.evaluator.evaluate(
            {
                "facet": "label",
                "value": "Beta",
                "match_mode": "starts_with",
                "negated": True,
            }
        )
        ids = set(result)
        self.assertNotIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_c.pk, ids)

    def test_negation_exists_note(self):
        """NOT exists on notes → concepts WITHOUT any notes."""
        result = self.evaluator.evaluate(
            {"facet": "note", "value": "", "match_mode": "exists", "negated": True}
        )
        ids = set(result)
        # B has no notes
        self.assertIn(self.concept_b.pk, ids)
        # A and C have notes
        self.assertNotIn(self.concept_a.pk, ids)
        self.assertNotIn(self.concept_c.pk, ids)

    def test_negation_identifier(self):
        """Negated identifier filter excludes B."""
        result = self.evaluator.evaluate(
            {"facet": "identifier", "value": "BETA", "negated": True}
        )
        ids = set(result)
        self.assertNotIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_c.pk, ids)

    def test_negation_scheme(self):
        """Negated scheme filter excludes all members of the scheme."""
        result = self.evaluator.evaluate(
            {"facet": "scheme", "value": str(self.scheme.pk), "negated": True}
        )
        ids = set(result)
        # All three concepts are in this scheme, so none should appear
        self.assertNotIn(self.concept_a.pk, ids)
        self.assertNotIn(self.concept_b.pk, ids)
        self.assertNotIn(self.concept_c.pk, ids)

    def test_negation_in_group(self):
        """Negated condition within an AND group works correctly."""
        query = {
            "operator": "and",
            "conditions": [
                {"facet": "label", "value": "Concept"},
                {"facet": "note", "value": "definition", "negated": True},
            ],
        }
        result = self.evaluator.evaluate(query)
        ids = set(result)
        # All have labels with "Concept", but A has "definition" note → excluded
        self.assertNotIn(self.concept_a.pk, ids)
        self.assertIn(self.concept_b.pk, ids)
        self.assertIn(self.concept_c.pk, ids)


# ────────────────────────────────────────────────────────────────
# API view tests  (require graph fixtures + tile data)
# ────────────────────────────────────────────────────────────────


class AdvancedSearchViewTests(TestCase):
    """Tests for the advanced search API endpoints."""

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
    def setUpTestData(cls):
        cls.load_ontology()
        cls.load_graphs()
        cls.admin = User.objects.get(username="admin")
        # Ensure admin is in RDM Administrator group
        rdm_group, _ = Group.objects.get_or_create(name="RDM Administrator")
        cls.admin.groups.add(rdm_group)

        cls.non_admin = User.objects.create_user(
            username="non_admin_advsearch",
            password="pass",
        )

        reference = DataTypeFactory().get_instance("reference")
        label_config = {"controlledList": LABEL_LIST_ID}
        cls.prefLabel_ref = reference.transform_value_for_tile(
            "prefLabel", **label_config
        )

        # Scheme
        cls.scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="API Test Scheme"
        )
        TileModel.objects.create(
            resourceinstance=cls.scheme,
            nodegroup_id=SCHEME_NAME_NODEGROUP,
            data={
                SCHEME_NAME_CONTENT_NODE: "API Test Scheme",
                SCHEME_NAME_TYPE_NODE: cls.prefLabel_ref,
                SCHEME_NAME_LANGUAGE_NODE: "en",
            },
        )

        # Concept
        cls.concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="API Concept"
        )
        TileModel.objects.create(
            resourceinstance=cls.concept,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "API Concept",
                CONCEPT_NAME_TYPE_NODE: cls.prefLabel_ref,
                CONCEPT_NAME_LANGUAGE_NODE: "en",
            },
        )
        rxr = ResourceXResource.objects.create(
            from_resource=cls.concept,
            from_resource_graph_id=CONCEPTS_GRAPH_ID,
            to_resource=cls.scheme,
            to_resource_graph_id=SCHEMES_GRAPH_ID,
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        TileModel.objects.create(
            resourceinstance=cls.concept,
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {
                        "resourceId": str(cls.scheme.pk),
                        "resourceXresourceId": str(rxr.pk),
                    },
                ],
            },
        )

    def setUp(self):
        self.client.force_login(self.admin)

    # ── AdvancedSearchView ──────────────────────────────────────

    def test_search_basic(self):
        response = self.client.post(
            reverse("api-advanced-search"),
            data=json.dumps(
                {
                    "query": {
                        "operator": "and",
                        "conditions": [
                            {"facet": "label", "value": "API Concept"},
                        ],
                    },
                    "page": 1,
                    "items": 25,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        result = json.loads(response.content)
        self.assertIn("data", result)
        self.assertIn("total_results", result)
        self.assertGreaterEqual(result["total_results"], 1)
        # Verify our concept appears
        ids = {item["id"] for item in result["data"]}
        self.assertIn(str(self.concept.pk), ids)

    def test_search_returns_enriched_fields(self):
        """Enriched results should include notes, uri, identifier, lifecycle_state."""
        response = self.client.post(
            reverse("api-advanced-search"),
            data=json.dumps(
                {
                    "query": {
                        "operator": "and",
                        "conditions": [
                            {"facet": "label", "value": "API Concept"},
                        ],
                    },
                }
            ),
            content_type="application/json",
        )
        result = json.loads(response.content)
        self.assertGreaterEqual(len(result["data"]), 1)
        item = result["data"][0]
        # These fields should exist even if null/empty
        self.assertIn("uri", item)
        self.assertIn("identifier", item)
        self.assertIn("notes", item)
        self.assertIn("lifecycle_state", item)

    def test_search_invalid_json(self):
        response = self.client.post(
            reverse("api-advanced-search"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_search_requires_authentication(self):
        self.client.logout()
        response = self.client.post(
            reverse("api-advanced-search"),
            data=json.dumps({"query": {}}),
            content_type="application/json",
        )
        self.assertNotEqual(response.status_code, HTTPStatus.OK)

    # ── AdvancedSearchOptionsView ───────────────────────────────

    def test_get_search_options(self):
        response = self.client.get(reverse("api-advanced-search-options"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        result = json.loads(response.content)
        self.assertIn("languages", result)
        self.assertIn("schemes", result)
        self.assertIn("lifecycle_states", result)
        self.assertIsInstance(result["languages"], list)
        self.assertIsInstance(result["schemes"], list)


class SavedSearchViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="ss_admin", password="pass")
        rdm_group, _ = Group.objects.get_or_create(name="RDM Administrator")
        cls.admin.groups.add(rdm_group)

        cls.other_user = User.objects.create_user(username="ss_other", password="pass")
        rdm_group.user_set.add(cls.other_user)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_create_saved_search(self):
        response = self.client.post(
            reverse("api-saved-searches"),
            data=json.dumps(
                {
                    "name": "New Search",
                    "query": {"operator": "and", "conditions": []},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        result = json.loads(response.content)
        self.assertEqual(result["name"], "New Search")
        self.assertIn("id", result)

    def test_delete_other_users_search_returns_404(self):
        saved_search = SavedSearch.objects.create(
            user=self.other_user, name="Not Mine", query={}
        )
        response = self.client.delete(
            reverse("api-saved-search-detail", args=[saved_search.pk])
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_create_saved_search_with_invalid_json(self):
        response = self.client.post(
            reverse("api-saved-searches"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_list_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("api-saved-searches"))
        self.assertNotEqual(response.status_code, HTTPStatus.OK)


class ConceptSetViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="cs_admin", password="pass")
        rdm_group, _ = Group.objects.get_or_create(name="RDM Administrator")
        cls.admin.groups.add(rdm_group)

        cls.other_user = User.objects.create_user(username="cs_other", password="pass")
        rdm_group.user_set.add(cls.other_user)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_create_concept_set(self):
        response = self.client.post(
            reverse("api-concept-sets"),
            data=json.dumps(
                {
                    "name": "New Set",
                    "description": "A test set",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        result = json.loads(response.content)
        self.assertEqual(result["name"], "New Set")
        self.assertEqual(result["description"], "A test set")
        self.assertEqual(result["member_count"], 0)

    def test_list_includes_member_count(self):
        concept_set = ConceptSet.objects.create(user=self.admin, name="Counted Set")
        ConceptSetMember.objects.create(
            concept_set=concept_set, concept_id=uuid.uuid4()
        )
        ConceptSetMember.objects.create(
            concept_set=concept_set, concept_id=uuid.uuid4()
        )
        response = self.client.get(reverse("api-concept-sets"))
        result = json.loads(response.content)
        self.assertEqual(result["data"][0]["member_count"], 2)

    def test_patch_other_users_set_returns_404(self):
        concept_set = ConceptSet.objects.create(user=self.other_user, name="Not Mine")
        response = self.client.patch(
            reverse("api-concept-set-detail", args=[concept_set.pk]),
            data=json.dumps({"name": "Hacked"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_list_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("api-concept-sets"))
        self.assertNotEqual(response.status_code, HTTPStatus.OK)


class ConceptSetMembersViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="csm_admin", password="pass")
        rdm_group, _ = Group.objects.get_or_create(name="RDM Administrator")
        cls.admin.groups.add(rdm_group)

        cls.other_user = User.objects.create_user(username="csm_other", password="pass")
        rdm_group.user_set.add(cls.other_user)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_add_members(self):
        concept_set = ConceptSet.objects.create(user=self.admin, name="Members Set")
        cid1, cid2 = str(uuid.uuid4()), str(uuid.uuid4())
        response = self.client.post(
            reverse("api-concept-set-members", args=[concept_set.pk]),
            data=json.dumps({"concept_ids": [cid1, cid2]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        result = json.loads(response.content)
        self.assertEqual(result["added"], 2)
        self.assertEqual(result["member_count"], 2)

    def test_add_duplicate_members_is_idempotent(self):
        concept_set = ConceptSet.objects.create(user=self.admin, name="Dedup Set")
        cid = str(uuid.uuid4())
        ConceptSetMember.objects.create(concept_set=concept_set, concept_id=cid)

        response = self.client.post(
            reverse("api-concept-set-members", args=[concept_set.pk]),
            data=json.dumps({"concept_ids": [cid]}),
            content_type="application/json",
        )
        result = json.loads(response.content)
        self.assertEqual(result["added"], 0)
        self.assertEqual(result["member_count"], 1)

    def test_remove_members(self):
        concept_set = ConceptSet.objects.create(user=self.admin, name="Remove Set")
        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()
        ConceptSetMember.objects.create(concept_set=concept_set, concept_id=cid1)
        ConceptSetMember.objects.create(concept_set=concept_set, concept_id=cid2)

        response = self.client.delete(
            reverse("api-concept-set-members", args=[concept_set.pk]),
            data=json.dumps({"concept_ids": [str(cid1)]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        result = json.loads(response.content)
        self.assertEqual(result["member_count"], 1)

    def test_add_members_to_other_users_set_returns_404(self):
        concept_set = ConceptSet.objects.create(
            user=self.other_user, name="Private Set"
        )
        response = self.client.post(
            reverse("api-concept-set-members", args=[concept_set.pk]),
            data=json.dumps({"concept_ids": [str(uuid.uuid4())]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
