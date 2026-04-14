"""Tests for the SPARQL parser and evaluator modules."""

import json
import unittest.mock

from django.test import SimpleTestCase
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS

from arches_lingo.utils.sparql.evaluator import evaluate_query, format_binding_value
from arches_lingo.utils.sparql.orm_evaluator import (
    can_evaluate_via_orm,
    _join_bindings_fast,
)
from arches_lingo.utils.sparql.parser import (
    SparqlParseError,
    SparqlUnsupportedError,
    parse_sparql,
    resolve_prefixed_name,
)

ARCHES = Namespace("http://example.org/arches/")


def _build_test_graph():
    """Build a small SKOS graph for testing."""
    graph = Graph()
    graph.bind("skos", SKOS)
    graph.bind("arches", ARCHES)

    scheme = ARCHES["scheme-1"]
    concept_a = ARCHES["concept-a"]
    concept_b = ARCHES["concept-b"]
    concept_c = ARCHES["concept-c"]

    graph.add((scheme, RDF.type, SKOS.ConceptScheme))
    graph.add((scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
    graph.add((scheme, SKOS.prefLabel, Literal("Schema de test", lang="fr")))
    graph.add((scheme, SKOS.hasTopConcept, concept_a))

    graph.add((concept_a, RDF.type, SKOS.Concept))
    graph.add((concept_a, SKOS.prefLabel, Literal("Architecture", lang="en")))
    graph.add((concept_a, SKOS.altLabel, Literal("Building design", lang="en")))
    graph.add((concept_a, SKOS.inScheme, scheme))
    graph.add((concept_a, SKOS.scopeNote, Literal("The art of building", lang="en")))

    graph.add((concept_b, RDF.type, SKOS.Concept))
    graph.add((concept_b, SKOS.prefLabel, Literal("Archaeology", lang="en")))
    graph.add((concept_b, SKOS.prefLabel, Literal("Archéologie", lang="fr")))
    graph.add((concept_b, SKOS.inScheme, scheme))
    graph.add((concept_b, SKOS.broader, concept_a))

    graph.add((concept_c, RDF.type, SKOS.Concept))
    graph.add((concept_c, SKOS.prefLabel, Literal("Ceramics", lang="en")))
    graph.add((concept_c, SKOS.inScheme, scheme))
    graph.add((concept_c, SKOS.related, concept_b))

    return graph


class SparqlParserTests(SimpleTestCase):
    def test_parse_basic_select(self):
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?s ?label
        WHERE {
            ?s a skos:Concept ;
               skos:prefLabel ?label .
        }
        """
        parsed = parse_sparql(query)
        self.assertEqual(len(parsed.prefixes), 1)
        self.assertIn("skos", parsed.prefixes)
        self.assertEqual(parsed.select_variables, ["?s", "?label"])
        self.assertEqual(len(parsed.triple_patterns), 2)

    def test_parse_select_star(self):
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT * WHERE { ?s skos:prefLabel ?o . }
        """
        parsed = parse_sparql(query)
        self.assertEqual(parsed.select_variables, ["*"])

    def test_parse_distinct(self):
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT DISTINCT ?s WHERE { ?s a skos:Concept . }
        """
        parsed = parse_sparql(query)
        self.assertTrue(parsed.distinct)

    def test_parse_filter(self):
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?s ?label WHERE {
            ?s skos:prefLabel ?label .
            FILTER(lang(?label) = "en")
        }
        """
        parsed = parse_sparql(query)
        self.assertEqual(len(parsed.filters), 1)
        self.assertIn("lang", parsed.filters[0].raw)

    def test_parse_optional(self):
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?s ?label ?note WHERE {
            ?s skos:prefLabel ?label .
            OPTIONAL { ?s skos:scopeNote ?note . }
        }
        """
        parsed = parse_sparql(query)
        self.assertEqual(len(parsed.optional_blocks), 1)
        self.assertEqual(len(parsed.optional_blocks[0].patterns), 1)

    def test_parse_limit_offset(self):
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?s WHERE { ?s a skos:Concept . }
        LIMIT 10 OFFSET 5
        """
        parsed = parse_sparql(query)
        self.assertEqual(parsed.limit, 10)
        self.assertEqual(parsed.offset, 5)

    def test_parse_order_by(self):
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?s ?label WHERE { ?s skos:prefLabel ?label . }
        ORDER BY DESC(?label)
        """
        parsed = parse_sparql(query)
        self.assertEqual(len(parsed.order_by), 1)
        self.assertEqual(parsed.order_by[0].variable, "?label")
        self.assertFalse(parsed.order_by[0].ascending)

    def test_parse_group_by_count(self):
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?scheme (COUNT(?concept) AS ?count)
        WHERE { ?concept skos:inScheme ?scheme . }
        GROUP BY ?scheme
        """
        parsed = parse_sparql(query)
        self.assertEqual(parsed.group_by, ["?scheme"])
        self.assertEqual(len(parsed.aggregates), 1)
        self.assertEqual(parsed.aggregates[0].function, "COUNT")
        self.assertEqual(parsed.aggregates[0].alias, "?count")

    def test_reject_construct(self):
        with self.assertRaises(SparqlUnsupportedError):
            parse_sparql(
                "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> "
                "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
            )

    def test_reject_update(self):
        with self.assertRaises(SparqlUnsupportedError):
            parse_sparql("INSERT DATA { <x> <y> <z> }")

    def test_parse_error_invalid(self):
        with self.assertRaises(SparqlParseError):
            parse_sparql("not a sparql query at all")

    def test_resolve_prefixed_name_well_known(self):
        uri = resolve_prefixed_name("skos:Concept", {})
        self.assertEqual(uri, "http://www.w3.org/2004/02/skos/core#Concept")

    def test_resolve_full_uri(self):
        uri = resolve_prefixed_name("<http://example.org/test>", {})
        self.assertEqual(uri, "http://example.org/test")

    def test_resolve_custom_prefix(self):
        uri = resolve_prefixed_name("ex:thing", {"ex": "http://example.org/"})
        self.assertEqual(uri, "http://example.org/thing")

    def test_resolve_unknown_prefix_raises(self):
        with self.assertRaises(SparqlParseError):
            resolve_prefixed_name("unknown:thing", {})

    def test_comment_stripping(self):
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        # This is a comment
        SELECT ?s WHERE {
            ?s a skos:Concept . # inline comment
        }
        """
        parsed = parse_sparql(query)
        self.assertEqual(len(parsed.triple_patterns), 1)


class SparqlEvaluatorTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.graph = _build_test_graph()

    def _execute(self, query_string):
        parsed = parse_sparql(query_string)
        return evaluate_query(parsed, self.graph)

    def test_select_all_concepts(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept WHERE { ?concept a skos:Concept . }
            """
        )
        self.assertEqual(len(results["bindings"]), 3)

    def test_select_with_prefLabel(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?label WHERE {
                ?concept a skos:Concept ;
                         skos:prefLabel ?label .
                FILTER(lang(?label) = "en")
            }
            """
        )
        labels = {str(binding["?label"]) for binding in results["bindings"]}
        self.assertIn("Architecture", labels)
        self.assertIn("Archaeology", labels)
        self.assertIn("Ceramics", labels)

    def test_filter_regex(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?label WHERE {
                ?concept skos:prefLabel ?label .
                FILTER(regex(str(?label), "^arch", "i"))
            }
            """
        )
        labels = {str(binding["?label"]) for binding in results["bindings"]}
        self.assertIn("Architecture", labels)
        self.assertIn("Archaeology", labels)
        self.assertNotIn("Ceramics", labels)

    def test_broader_relationship(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?child ?parent WHERE {
                ?child skos:broader ?parent .
            }
            """
        )
        self.assertEqual(len(results["bindings"]), 1)
        binding = results["bindings"][0]
        self.assertTrue(str(binding["?child"]).endswith("concept-b"))
        self.assertTrue(str(binding["?parent"]).endswith("concept-a"))

    def test_optional_scope_note(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?label ?note WHERE {
                ?concept a skos:Concept ;
                         skos:prefLabel ?label .
                FILTER(lang(?label) = "en")
                OPTIONAL { ?concept skos:scopeNote ?note . }
            }
            """
        )
        notes_found = [
            binding
            for binding in results["bindings"]
            if binding.get("?note") is not None
        ]
        notes_missing = [
            binding for binding in results["bindings"] if binding.get("?note") is None
        ]
        self.assertTrue(len(notes_found) > 0)
        self.assertTrue(len(notes_missing) > 0)

    def test_limit(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?s WHERE { ?s a skos:Concept . }
            LIMIT 2
            """
        )
        self.assertEqual(len(results["bindings"]), 2)

    def test_offset(self):
        results_all = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?s WHERE { ?s a skos:Concept . }
            """
        )
        results_offset = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?s WHERE { ?s a skos:Concept . }
            OFFSET 1
            """
        )
        self.assertEqual(
            len(results_offset["bindings"]),
            len(results_all["bindings"]) - 1,
        )

    def test_distinct(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT ?type WHERE { ?s a ?type . }
            """
        )
        types = {str(binding["?type"]) for binding in results["bindings"]}
        self.assertIn(str(SKOS.Concept), types)
        self.assertIn(str(SKOS.ConceptScheme), types)

    def test_count_group_by(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?scheme (COUNT(?concept) AS ?count)
            WHERE { ?concept skos:inScheme ?scheme . }
            GROUP BY ?scheme
            """
        )
        self.assertEqual(len(results["bindings"]), 1)
        count = int(str(results["bindings"][0]["?count"]))
        self.assertEqual(count, 3)

    def test_top_concepts(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?scheme ?concept WHERE {
                ?scheme skos:hasTopConcept ?concept .
            }
            """
        )
        self.assertEqual(len(results["bindings"]), 1)
        self.assertTrue(str(results["bindings"][0]["?concept"]).endswith("concept-a"))

    def test_related_concepts(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?a ?b WHERE { ?a skos:related ?b . }
            """
        )
        self.assertEqual(len(results["bindings"]), 1)

    def test_scheme_query(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?scheme ?label WHERE {
                ?scheme a skos:ConceptScheme ;
                        skos:prefLabel ?label .
                FILTER(lang(?label) = "en")
            }
            """
        )
        self.assertEqual(len(results["bindings"]), 1)
        self.assertEqual(str(results["bindings"][0]["?label"]), "Test Scheme")

    def test_select_star(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT * WHERE { ?s skos:related ?o . }
            """
        )
        self.assertIn("?s", results["variables"])
        self.assertIn("?o", results["variables"])

    def test_filter_equality(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?label WHERE {
                ?concept skos:prefLabel ?label .
                FILTER(str(?label) = "Architecture")
            }
            """
        )
        self.assertEqual(len(results["bindings"]), 1)

    def test_filter_negation(self):
        results = self._execute(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?label WHERE {
                ?concept a skos:Concept ;
                         skos:prefLabel ?label .
                FILTER(lang(?label) = "en")
                FILTER(!bound(?concept))
            }
            """
        )
        self.assertEqual(len(results["bindings"]), 0)

    def test_format_binding_value_uri(self):
        result = format_binding_value(URIRef("http://example.org/concept"))
        self.assertEqual(result["type"], "uri")
        self.assertEqual(result["value"], "http://example.org/concept")

    def test_format_binding_value_literal(self):
        result = format_binding_value(Literal("test", lang="en"))
        self.assertEqual(result["type"], "literal")
        self.assertEqual(result["value"], "test")
        self.assertEqual(result["xml:lang"], "en")

    def test_format_binding_value_none(self):
        self.assertIsNone(format_binding_value(None))


class SparqlViewTests(SimpleTestCase):
    """Tests for the SPARQL API view request/response handling."""

    def setUp(self):
        self.patcher = unittest.mock.patch(
            "arches_lingo.mixins.permissions.anonymous_access_allowed",
            return_value=True,
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_get_without_query_returns_400(self):
        response = self.client.get("/api/lingo/sparql")
        self.assertEqual(response.status_code, 400)

    def test_post_invalid_json_returns_400(self):
        response = self.client.post(
            "/api/lingo/sparql",
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_post_empty_query_returns_400(self):
        response = self.client.post(
            "/api/lingo/sparql",
            data=json.dumps({"query": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_post_unsupported_query_returns_400(self):
        response = self.client.post(
            "/api/lingo/sparql",
            data=json.dumps({"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_examples_endpoint(self):
        response = self.client.get("/api/lingo/sparql/examples")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)
        self.assertIn("title", data[0])
        self.assertIn("query", data[0])


class OrmEvaluatorCanHandleTests(SimpleTestCase):
    """Tests for can_evaluate_via_orm — determines ORM vs graph fallback."""

    def test_basic_concept_query_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?label WHERE {
                ?concept a skos:Concept ;
                         skos:prefLabel ?label .
                FILTER(lang(?label) = "en")
            }
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_broader_query_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?child ?parent WHERE {
                ?child skos:broader ?parent .
            }
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_in_scheme_query_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?scheme WHERE {
                ?concept skos:inScheme ?scheme .
            }
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_top_concept_query_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?scheme ?concept WHERE {
                ?scheme skos:hasTopConcept ?concept .
            }
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_related_query_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?a ?b WHERE {
                ?a skos:related ?b .
            }
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_scope_note_query_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?note WHERE {
                ?concept a skos:Concept ;
                         skos:scopeNote ?note .
            }
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_optional_note_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?label ?note WHERE {
                ?concept a skos:Concept ;
                         skos:prefLabel ?label .
                OPTIONAL { ?concept skos:scopeNote ?note . }
            }
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_variable_predicate_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?concept ?labelType ?label WHERE {
                ?concept a skos:Concept ;
                         ?labelType ?label .
            }
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_scheme_query_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?scheme ?label WHERE {
                ?scheme a skos:ConceptScheme ;
                        skos:prefLabel ?label .
            }
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_count_group_by_is_orm_capable(self):
        parsed = parse_sparql(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?scheme (COUNT(?concept) AS ?count)
            WHERE { ?concept skos:inScheme ?scheme . }
            GROUP BY ?scheme
            """
        )
        self.assertTrue(can_evaluate_via_orm(parsed))

    def test_all_example_queries_are_orm_capable(self):
        from arches_lingo.utils.sparql.examples import EXAMPLE_QUERIES

        for example in EXAMPLE_QUERIES:
            parsed = parse_sparql(example["query"])
            self.assertTrue(
                can_evaluate_via_orm(parsed),
                f"Example query not ORM-capable: {example['title']}",
            )


class JoinBindingsFastTests(SimpleTestCase):
    """Tests for the hash-based join used in ORM evaluation."""

    def test_join_with_empty_seed(self):
        right = [{"?x": URIRef("http://a")}, {"?x": URIRef("http://b")}]
        result = _join_bindings_fast([{}], right)
        self.assertEqual(len(result), 2)

    def test_join_on_shared_variable(self):
        left = [
            {"?s": URIRef("http://a")},
            {"?s": URIRef("http://b")},
        ]
        right = [
            {"?s": URIRef("http://a"), "?label": Literal("Alpha")},
            {"?s": URIRef("http://b"), "?label": Literal("Beta")},
            {"?s": URIRef("http://c"), "?label": Literal("Gamma")},
        ]
        result = _join_bindings_fast(left, right)
        self.assertEqual(len(result), 2)
        labels = {str(binding["?label"]) for binding in result}
        self.assertEqual(labels, {"Alpha", "Beta"})

    def test_cross_join_no_shared_variables(self):
        left = [{"?a": Literal("1")}, {"?a": Literal("2")}]
        right = [{"?b": Literal("x")}, {"?b": Literal("y")}]
        result = _join_bindings_fast(left, right)
        self.assertEqual(len(result), 4)

    def test_empty_right_returns_empty(self):
        left = [{"?s": URIRef("http://a")}]
        result = _join_bindings_fast(left, [])
        self.assertEqual(result, [])
