import json
import uuid

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.client import Client
from django.urls import reverse

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import ResourceIdentifier, ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    EXACT_MATCH_LIST_ITEM_ID,
    IDENTIFIER_CONTENT_NODE,
    IDENTIFIER_NODEGROUP,
    LABEL_LIST_ID,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_TYPE_NODE,
    SCHEMES_GRAPH_ID,
    STATEMENT_CONTENT_NODE,
    STATEMENT_LANGUAGE_NODE,
    STATEMENT_NODEGROUP,
    STATEMENT_TYPE_NODE,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.checks import check_reconciliation_rate_limit
from arches_lingo.models import ConceptMerge
from arches_lingo.utils.concept_merge.tiles import get_list_item_tile_value
from arches_lingo.utils.concept_lifecycle import (
    DRAFT_STATE_ID,
    LOCKED_STATE_ID,
    PUBLISHED_STATE_ID,
    RETIRED_STATE_ID,
)
from arches_lingo.utils.reconciliation.candidates import (
    MAX_CANDIDATE_LIMIT,
    MAX_QUERIES_PER_REQUEST,
    ScoredCandidate,
    parse_reconciliation_queries,
)
from arches_lingo.utils.reconciliation.manifest import (
    SUGGEST_KINDS,
    build_service_manifest,
    list_reconcilable_schemes,
)
from arches_lingo.utils.reconciliation.suggest import SUGGEST_SERVICES
from arches_lingo.utils.reconciliation.scoring import (
    adjust_score_for_properties,
    decide_automatic_match,
    score_match,
)
from arches_lingo.utils.reconciliation.visibility import resolve_merge_survivors
from arches_lingo.utils.search_service import extract_note_type_label
from arches_lingo.utils.skos import ARCHES
from tests.tests import SchemeWithConceptsTestCase


def set_lifecycle_state(resource, state_id):
    ResourceInstance.objects.filter(pk=resource.pk).update(
        resource_instance_lifecycle_state_id=state_id
    )


@override_settings(
    LINGO_RECONCILIATION_ENABLED=True,
    LINGO_RECONCILIATION_SERVICE_NAME="Test Lingo",
    PUBLIC_SERVER_ADDRESS="https://lingo.example.org/",
)
class ReconciliationManifestTests(SchemeWithConceptsTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        set_lifecycle_state(cls.scheme, PUBLISHED_STATE_ID)
        ResourceIdentifier.objects.create(
            resourceid=cls.scheme, identifier="test-scheme", source="arches-lingo"
        )

        cls.locked_scheme = cls.create_scheme_with_labels(
            [("Alpha Scheme", "altLabel", "en"), ("Schéma Alpha", "prefLabel", "fr")]
        )
        set_lifecycle_state(cls.locked_scheme, LOCKED_STATE_ID)

        cls.unlabelled_scheme = cls.create_scheme_with_labels([])
        set_lifecycle_state(cls.unlabelled_scheme, PUBLISHED_STATE_ID)

        cls.hidden_schemes = [
            cls.create_scheme_with_labels([(f"Hidden {state_id}", "prefLabel", "en")])
            for state_id in (DRAFT_STATE_ID, RETIRED_STATE_ID)
        ]
        for hidden_scheme, state_id in zip(
            cls.hidden_schemes, (DRAFT_STATE_ID, RETIRED_STATE_ID)
        ):
            set_lifecycle_state(hidden_scheme, state_id)
        ResourceIdentifier.objects.create(
            resourceid=cls.hidden_schemes[0],
            identifier="draft-scheme",
            source="arches-lingo",
        )

    @classmethod
    def create_scheme_with_labels(cls, labels):
        scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Unlabelled Scheme"
        )
        reference = DataTypeFactory().get_instance("reference")
        for value, label_type, language in labels:
            TileModel.objects.create(
                resourceinstance=scheme,
                nodegroup_id=SCHEME_NAME_NODEGROUP,
                data={
                    SCHEME_NAME_CONTENT_NODE: value,
                    SCHEME_NAME_TYPE_NODE: reference.transform_value_for_tile(
                        label_type, controlledList=LABEL_LIST_ID
                    ),
                    SCHEME_NAME_LANGUAGE_NODE: language,
                },
            )
        return scheme

    def setUp(self):
        self.client.logout()

    def test_lists_only_published_and_locked_schemes_by_display_name(self):
        self.assertEqual(
            list_reconcilable_schemes(),
            [
                # The English altLabel outranks the French prefLabel in English.
                {"id": str(self.locked_scheme.pk), "name": "Alpha Scheme"},
                {"id": str(self.scheme.pk), "name": "Test Scheme"},
                {"id": str(self.unlabelled_scheme.pk), "name": "Unlabelled Scheme"},
            ],
        )

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=False)
    def test_anonymous_cross_origin_global_manifest(self):
        response = self.client.get(reverse("api-lingo-reconcile"))
        manifest = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertEqual(manifest["name"], "Test Lingo")
        self.assertEqual(manifest["versions"], ["0.1", "0.2"])
        self.assertEqual(
            manifest["identifierSpace"], "https://lingo.example.org/concept/"
        )
        self.assertEqual(
            manifest["view"]["url"], "https://lingo.example.org/concept/{{id}}"
        )
        self.assertEqual(
            manifest["schemaSpace"], "http://www.w3.org/2004/02/skos/core#"
        )
        self.assertEqual(len(manifest["defaultTypes"]), 3)
        self.assertEqual(
            manifest["preview"]["url"],
            "https://lingo.example.org/api/lingo/reconcile/preview?id={{id}}",
        )
        self.assertEqual(
            manifest["suggest"]["entity"],
            {
                "service_url": "https://lingo.example.org/api/lingo/reconcile",
                "service_path": "/suggest/entity",
            },
        )
        self.assertEqual(set(SUGGEST_KINDS), set(SUGGEST_SERVICES))
        self.assertEqual(
            manifest["extend"]["propose_properties"]["service_path"], "/properties"
        )
        self.assertEqual(manifest["extend"]["property_settings"][0]["name"], "lang")

    def test_scheme_service_is_scoped_named_and_only_for_reconcilable_schemes(self):
        def scheme_manifest_response(scheme_identifier):
            return self.client.get(
                reverse(
                    "api-lingo-scheme-reconcile",
                    kwargs={"scheme_identifier": scheme_identifier},
                )
            )

        manifest = scheme_manifest_response("test-scheme").json()

        self.assertEqual(manifest["name"], "Test Lingo — Test Scheme")
        self.assertEqual(
            manifest["defaultTypes"],
            [{"id": str(self.scheme.pk), "name": "Test Scheme"}],
        )
        self.assertEqual(
            manifest["suggest"]["entity"]["service_url"],
            "https://lingo.example.org/api/lingo/schemes/test-scheme/reconcile",
        )
        self.assertEqual(
            manifest["extend"]["propose_properties"]["service_url"],
            "https://lingo.example.org/api/lingo/reconcile",
        )
        for hidden_identifier in ["draft-scheme", "no-such-scheme"]:
            self.assertEqual(
                scheme_manifest_response(hidden_identifier).status_code, 404
            )

    @override_settings(LINGO_RECONCILIATION_ENABLED=False)
    def test_disabled_service_is_absent(self):
        response = self.client.get(reverse("api-lingo-reconcile"))

        self.assertEqual(response.status_code, 404)

    def test_app_settings_advertise_the_service_only_while_enabled(self):
        enabled = self.client.get(reverse("api-lingo-settings")).json()
        with override_settings(LINGO_RECONCILIATION_ENABLED=False):
            disabled = self.client.get(reverse("api-lingo-settings")).json()

        self.assertTrue(enabled["reconciliation_enabled"])
        self.assertEqual(
            enabled["reconciliation_service_url"],
            "https://lingo.example.org/api/lingo/reconcile",
        )
        self.assertEqual(
            enabled["scheme_reconciliation_service_url_template"],
            "https://lingo.example.org/api/lingo/schemes/{scheme_identifier}/reconcile",
        )
        self.assertFalse(disabled["reconciliation_enabled"])
        self.assertIsNone(disabled["reconciliation_service_url"])

    @override_settings(
        LINGO_RECONCILIATION_RATE_LIMIT="2/h",
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "reconciliation-rate-limit",
            }
        },
    )
    def test_callers_over_the_rate_limit_are_told_to_wait(self):
        responses = [
            self.client.get(reverse("api-lingo-reconcile")) for _request in range(3)
        ]

        self.assertEqual(
            [response.status_code for response in responses], [200, 200, 429]
        )
        self.assertEqual(responses[2]["Access-Control-Allow-Origin"], "*")
        self.assertGreater(int(responses[2]["Retry-After"]), 0)

    @override_settings(LINGO_RECONCILIATION_RATE_LIMIT="1/h")
    def test_rate_limit_never_blocks_without_a_cache_that_stores(self):
        # The test settings' default cache is a DummyCache.
        for _request in range(2):
            response = self.client.get(reverse("api-lingo-reconcile"))
            self.assertEqual(response.status_code, 200)

    def test_system_check_rejects_malformed_rate_limits(self):
        for rate_limit, is_valid in [
            (None, True),
            ("120/m", True),
            ("5/10s", True),
            ("1000/d", True),
            ("0/m", False),
            ("many/m", False),
            ("5/0m", False),
            ("5", False),
            (120, False),
        ]:
            with self.subTest(rate_limit=rate_limit):
                with override_settings(LINGO_RECONCILIATION_RATE_LIMIT=rate_limit):
                    errors = check_reconciliation_rate_limit(None)
                self.assertEqual(
                    [error.id for error in errors],
                    [] if is_valid else ["arches_lingo.E001"],
                )

    def test_service_name_defaults_when_the_setting_is_absent(self):
        with override_settings():
            del settings.LINGO_RECONCILIATION_SERVICE_NAME
            self.assertEqual(build_service_manifest()["name"], "Arches Lingo")


class ReconciliationScoringTests(SimpleTestCase):
    def test_exact_labels_score_by_tier_and_fuzzy_matches_by_similarity(self):
        self.assertEqual(score_match(best_rank=0, best_similarity=0.2), 100)
        self.assertEqual(score_match(best_rank=1002, best_similarity=0.2), 90)
        self.assertEqual(score_match(best_rank=3000, best_similarity=0.9), 72)
        self.assertEqual(score_match(best_rank=3000, best_similarity=0.1), 60)
        self.assertEqual(score_match(best_rank=7000, best_similarity=0.2), 16)
        self.assertEqual(score_match(best_rank=7000, best_similarity=None), 0)

    def test_only_an_unambiguous_direct_pref_label_match_is_automatic(self):
        exact = ScoredCandidate(concept_id="exact", tier=0, score=100)
        other_exact = ScoredCandidate(concept_id="other", tier=0, score=100)
        alt_label = ScoredCandidate(concept_id="alt", tier=1, score=90)
        substitute = ScoredCandidate(
            concept_id="survivor", tier=0, score=100, substitutes_for_concept_id="old"
        )

        self.assertIs(decide_automatic_match([exact, alt_label]), exact)
        self.assertIsNone(decide_automatic_match([exact, other_exact]))
        self.assertIsNone(decide_automatic_match([alt_label]))
        self.assertIsNone(decide_automatic_match([substitute]))

    def test_properties_boost_penalize_and_settle_matches(self):
        exact = ScoredCandidate(concept_id="exact", tier=0, score=100)
        contradicted_exact = ScoredCandidate(
            concept_id="homograph", tier=0, score=70, is_contradicted=True
        )
        identified = ScoredCandidate(
            concept_id="identified", tier=8, score=100, is_identified=True
        )
        retired_exact = ScoredCandidate(
            concept_id="retired", tier=0, score=100, is_retired=True
        )

        self.assertEqual(adjust_score_for_properties(95, 2, False), 100)
        self.assertEqual(adjust_score_for_properties(20, 0, True), 0)
        self.assertEqual(adjust_score_for_properties(60, 1, True), 40)
        self.assertIs(decide_automatic_match([exact, contradicted_exact]), exact)
        self.assertIs(decide_automatic_match([exact, identified]), identified)
        self.assertIsNone(decide_automatic_match([retired_exact]))


class ReconciliationQueryParsingTests(SimpleTestCase):
    def test_property_values_are_normalized(self):
        query = parse_reconciliation_queries(
            json.dumps(
                {
                    "q0": {
                        "query": "crane",
                        "properties": [
                            {"pid": "broader", "v": [" birds ", {"id": "abc"}]},
                            {"pid": "broader", "v": None},
                            {"pid": "includeRetired", "v": True},
                            {"pid": "lang", "v": "fr"},
                            {"pid": "notation", "v": 300},
                        ],
                    }
                }
            )
        )["q0"]

        self.assertEqual(query.values_for("broader"), ("birds", "abc"))
        self.assertEqual(query.values_for("notation"), ("300",))
        self.assertEqual(query.values_for("altLabel"), ())
        self.assertEqual(query.language, "fr")
        self.assertTrue(query.include_retired)

    def test_defaults_capping_and_single_item_type_lists(self):
        queries = parse_reconciliation_queries(
            json.dumps(
                {
                    "q0": {"query": "  crane  "},
                    "q1": {"query": "crane", "type": ["scheme-a"], "limit": 500},
                    "q2": {"query": "crane", "type": "scheme-b", "limit": 3},
                    "q3": {"query": "crane", "type": None},
                }
            ),
            default_scheme_id="default-scheme",
        )

        self.assertEqual(queries["q0"].text, "crane")
        self.assertEqual(queries["q0"].scheme_id, "default-scheme")
        self.assertEqual(queries["q0"].limit, 10)
        self.assertEqual(queries["q1"].scheme_id, "scheme-a")
        self.assertEqual(queries["q1"].limit, MAX_CANDIDATE_LIMIT)
        self.assertEqual(queries["q2"].scheme_id, "scheme-b")
        self.assertEqual(queries["q2"].limit, 3)
        # A scheme's service treats an explicit null type as its own scheme.
        self.assertEqual(queries["q3"].scheme_id, "default-scheme")

    def test_malformed_batches_are_rejected(self):
        too_many_queries = {
            f"q{index}": {"query": "crane"}
            for index in range(MAX_QUERIES_PER_REQUEST + 1)
        }
        malformed_batches = [
            "not json",
            json.dumps(["crane"]),
            json.dumps(too_many_queries),
            json.dumps({"q0": "crane"}),
            json.dumps({"q0": {"query": "   "}}),
            json.dumps({"q0": {"query": "c" * 256}}),
            json.dumps({"q0": {"query": "crane", "type": ["a", "b"]}}),
            json.dumps({"q0": {"query": "crane", "limit": 0}}),
            json.dumps({"q0": {"query": "crane", "limit": True}}),
            json.dumps({"q0": {"query": "crane", "properties": {"pid": "broader"}}}),
            json.dumps({"q0": {"query": "crane", "properties": [{"v": "birds"}]}}),
            json.dumps({"q0": {"query": "crane", "properties": [{"pid": "colour"}]}}),
        ]
        for malformed_batch in malformed_batches:
            with self.subTest(malformed_batch=malformed_batch[:40]):
                with self.assertRaises(ValueError):
                    parse_reconciliation_queries(malformed_batch)


class MergeSurvivorResolutionTests(TestCase):
    def test_follows_chains_and_stops_at_loops(self):
        first, second, third, looping, untouched = (str(uuid.uuid4()) for _ in range(5))
        for absorbed_id, survivor_id in [
            (first, second),
            (second, third),
            (looping, first),
            (third, looping),
        ]:
            ConceptMerge.objects.create(
                absorbed_concept_id=absorbed_id, survivor_concept_id=survivor_id
            )

        self.assertEqual(resolve_merge_survivors([untouched]), {})
        # first → second → third → looping → (first, already visited)
        self.assertEqual(resolve_merge_survivors([first]), {first: looping})


@override_settings(LINGO_RECONCILIATION_ENABLED=True)
class ReconciliationQueryTestCase(SchemeWithConceptsTestCase):
    """Concept 1 is the top concept; each later concept is narrower than the one
    before it and than Concept 1."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        set_lifecycle_state(cls.scheme, PUBLISHED_STATE_ID)
        for concept in cls.concepts:
            set_lifecycle_state(concept, PUBLISHED_STATE_ID)
        ResourceIdentifier.objects.create(
            resourceid=cls.scheme, identifier="test-scheme", source="arches-lingo"
        )

    def setUp(self):
        self.client.logout()

    def reconcile(self, queries, url=None):
        response = self.client.post(
            url or reverse("api-lingo-reconcile"), {"queries": json.dumps(queries)}
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def result_ids(self, results):
        return [result["id"] for result in results]

    def add_label(self, concept, value, label_type="prefLabel", language="en"):
        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: value,
                CONCEPT_NAME_TYPE_NODE: DataTypeFactory()
                .get_instance("reference")
                .transform_value_for_tile(label_type, controlledList=LABEL_LIST_ID),
                CONCEPT_NAME_LANGUAGE_NODE: language,
            },
        )


class ReconciliationQueryTests(ReconciliationQueryTestCase):
    def test_exact_pref_label_is_an_automatic_match_with_context(self):
        # A label tile missing its type and language must not break the batch.
        TileModel.objects.create(
            resourceinstance=self.concepts[2],
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={CONCEPT_NAME_CONTENT_NODE: "Concept 3 (untyped)"},
        )

        results = self.reconcile({"q0": {"query": "concept 3"}})["q0"]["result"]

        self.assertEqual(
            results[0],
            {
                "id": str(self.concepts[2].pk),
                "name": "Concept 3",
                "description": "Concept 1, Concept 2 · Test Scheme",
                "type": [{"id": str(self.scheme.pk), "name": "Test Scheme"}],
                "score": 100,
                "match": True,
            },
        )
        self.assertFalse(any(result["match"] for result in results[1:]))

    def test_short_terms_match_by_label_prefix_not_anywhere_in_it(self):
        # Every fixture label contains "on" ("Concept 1" …), none starts with it.
        anywhere_in_label = self.reconcile({"q0": {"query": "on"}})["q0"]["result"]
        label_prefix = self.reconcile({"q0": {"query": "co"}})["q0"]["result"]

        self.assertEqual(anywhere_in_label, [])
        self.assertEqual(len(label_prefix), 5)

    def test_shared_pref_label_is_never_automatic(self):
        self.add_label(self.concepts[4], "Concept 4")

        results = self.reconcile({"q0": {"query": "Concept 4"}})["q0"]["result"]

        self.assertEqual(
            set(self.result_ids(results[:2])),
            {str(self.concepts[3].pk), str(self.concepts[4].pk)},
        )
        self.assertFalse(any(result["match"] for result in results))

    def test_drafts_and_unmerged_retired_concepts_are_not_offered(self):
        set_lifecycle_state(self.concepts[3], DRAFT_STATE_ID)
        set_lifecycle_state(self.concepts[4], RETIRED_STATE_ID)

        batch = self.reconcile(
            {"q0": {"query": "Concept 4"}, "q1": {"query": "Concept 5"}}
        )

        returned_ids = self.result_ids(batch["q0"]["result"]) + self.result_ids(
            batch["q1"]["result"]
        )
        self.assertNotIn(str(self.concepts[3].pk), returned_ids)
        self.assertNotIn(str(self.concepts[4].pk), returned_ids)

    def test_merged_concept_leads_to_its_survivor_without_automatic_match(self):
        set_lifecycle_state(self.concepts[4], RETIRED_STATE_ID)
        ConceptMerge.objects.create(
            absorbed_concept_id=self.concepts[4].pk,
            survivor_concept_id=self.concepts[1].pk,
        )

        results = self.reconcile({"q0": {"query": "Concept 5"}})["q0"]["result"]

        self.assertEqual(results[0]["id"], str(self.concepts[1].pk))
        self.assertEqual(results[0]["score"], 100)
        self.assertFalse(results[0]["match"])
        self.assertNotIn(str(self.concepts[4].pk), self.result_ids(results))

    def test_cross_scheme_survivor_respects_scheme_scope_and_visibility(self):
        other_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Other Scheme"
        )
        survivor = ResourceInstance.objects.create(
            graph_id=self.concepts[0].graph_id, name="Survivor"
        )
        TileModel.objects.create(
            resourceinstance=survivor,
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {"resourceId": str(other_scheme.pk)}
                ]
            },
        )
        set_lifecycle_state(survivor, PUBLISHED_STATE_ID)
        set_lifecycle_state(other_scheme, PUBLISHED_STATE_ID)
        set_lifecycle_state(self.concepts[4], RETIRED_STATE_ID)
        ConceptMerge.objects.create(
            absorbed_concept_id=self.concepts[4].pk, survivor_concept_id=survivor.pk
        )
        queries = {
            "any_scheme": {"query": "Concept 5"},
            "absorbed_concepts_scheme": {
                "query": "Concept 5",
                "type": str(self.scheme.pk),
            },
        }

        TileModel.objects.create(
            resourceinstance=self.concepts[4],
            nodegroup_id=IDENTIFIER_NODEGROUP,
            data={IDENTIFIER_CONTENT_NODE: "C-5"},
        )
        by_identifier = {
            "q0": {
                "query": "no such label",
                "properties": [{"pid": "notation", "v": "C-5"}],
            }
        }

        visible_batch = self.reconcile(queries)
        # Found by identifier, an absorbed concept in a hidden scheme must not
        # reveal what it was merged into.
        set_lifecycle_state(self.scheme, DRAFT_STATE_ID)
        hidden_absorbed_batch = self.reconcile(by_identifier)
        set_lifecycle_state(self.scheme, PUBLISHED_STATE_ID)
        set_lifecycle_state(other_scheme, DRAFT_STATE_ID)
        hidden_survivor_batch = self.reconcile(queries)

        self.assertIn(
            str(survivor.pk), self.result_ids(visible_batch["any_scheme"]["result"])
        )
        for results in [
            visible_batch["absorbed_concepts_scheme"]["result"],
            hidden_absorbed_batch["q0"]["result"],
            hidden_survivor_batch["any_scheme"]["result"],
        ]:
            self.assertNotIn(str(survivor.pk), self.result_ids(results))

    def test_type_scoping(self):
        batch = self.reconcile(
            {
                "in_scheme": {"query": "Concept 3", "type": str(self.scheme.pk)},
                "unknown_scheme": {"query": "Concept 3", "type": str(uuid.uuid4())},
            }
        )

        self.assertEqual(
            batch["in_scheme"]["result"][0]["id"], str(self.concepts[2].pk)
        )
        self.assertEqual(batch["unknown_scheme"]["result"], [])
        self.assertEqual(
            self.reconcile({"q0": {"query": "Concept 3", "type": "no-such-scheme"}}),
            {"q0": {"result": []}},
        )

    def test_scheme_service_defaults_queries_to_its_scheme(self):
        set_lifecycle_state(self.scheme, DRAFT_STATE_ID)
        hidden_scheme_url = reverse(
            "api-lingo-scheme-reconcile", kwargs={"scheme_identifier": "test-scheme"}
        )
        self.assertEqual(
            self.client.post(hidden_scheme_url, {"queries": "{}"}).status_code, 404
        )

        set_lifecycle_state(self.scheme, PUBLISHED_STATE_ID)
        results = self.reconcile({"q0": {"query": "Concept 3"}}, url=hidden_scheme_url)[
            "q0"
        ]["result"]
        self.assertEqual(results[0]["id"], str(self.concepts[2].pk))

    def test_scheme_service_never_searches_another_scheme(self):
        other_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Other Scheme"
        )
        elsewhere = ResourceInstance.objects.create(
            graph_id=self.concepts[0].graph_id, name="Elsewhere"
        )
        TileModel.objects.create(
            resourceinstance=elsewhere,
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {"resourceId": str(other_scheme.pk)}
                ]
            },
        )
        self.add_label(elsewhere, "Concept 3")
        TileModel.objects.create(
            resourceinstance=elsewhere,
            nodegroup_id=IDENTIFIER_NODEGROUP,
            data={IDENTIFIER_CONTENT_NODE: "E-1"},
        )
        set_lifecycle_state(elsewhere, PUBLISHED_STATE_ID)
        set_lifecycle_state(other_scheme, PUBLISHED_STATE_ID)
        queries = {
            "typed_elsewhere": {"query": "Concept 3", "type": str(other_scheme.pk)},
            "identified_with_null_type": {
                "query": "no such label",
                "type": None,
                "properties": [{"pid": "notation", "v": "E-1"}],
            },
        }
        scheme_url = reverse(
            "api-lingo-scheme-reconcile", kwargs={"scheme_identifier": "test-scheme"}
        )
        extension_request = {
            "extend": json.dumps(
                {"ids": [str(elsewhere.pk)], "properties": [{"id": "prefLabel"}]}
            )
        }

        global_batch = self.reconcile(queries)
        scheme_batch = self.reconcile(queries, url=scheme_url)
        global_extension = self.client.post(
            reverse("api-lingo-reconcile"), extension_request
        ).json()
        scheme_extension = self.client.post(scheme_url, extension_request).json()

        for query_key in queries:
            self.assertEqual(
                self.result_ids(global_batch[query_key]["result"]),
                [str(elsewhere.pk)],
            )
            self.assertEqual(scheme_batch[query_key]["result"], [])
        self.assertEqual(
            global_extension["rows"][str(elsewhere.pk)]["prefLabel"],
            [{"str": "Concept 3"}],
        )
        self.assertEqual(scheme_extension["rows"][str(elsewhere.pk)]["prefLabel"], [])

    def test_non_public_broader_concepts_are_never_revealed(self):
        set_lifecycle_state(self.concepts[1], DRAFT_STATE_ID)

        results = self.reconcile({"q0": {"query": "concept 3"}})["q0"]["result"]
        by_draft_broader_label = self.reconcile(
            {
                "q0": {
                    "query": "concept 3",
                    "properties": [{"pid": "broader", "v": "concept 2"}],
                }
            }
        )["q0"]["result"]

        self.assertEqual(results[0]["description"], "Concept 1 · Test Scheme")
        self.assertFalse(any(result["match"] for result in by_draft_broader_label))

    def test_version_0_1_clients_and_csrf_free_posts_are_served(self):
        queries = json.dumps({"q0": {"query": "Concept 3", "limit": 1}})
        get_response = self.client.get(
            reverse("api-lingo-reconcile"), {"queries": queries}
        )
        csrf_enforcing_post = Client(enforce_csrf_checks=True).post(
            reverse("api-lingo-reconcile"), {"queries": queries}
        )

        self.assertEqual(get_response.json(), csrf_enforcing_post.json())
        self.assertEqual(len(get_response.json()["q0"]["result"]), 1)

    def test_malformed_requests_are_bad_requests(self):
        missing_queries = self.client.post(reverse("api-lingo-reconcile"))
        malformed_queries = self.client.post(
            reverse("api-lingo-reconcile"), {"queries": "not json"}
        )

        self.assertEqual(missing_queries.status_code, 400)
        self.assertEqual(malformed_queries.status_code, 400)


class ReconciliationQueryPropertyTests(ReconciliationQueryTestCase):
    """Concept 4 and Concept 5 share the prefLabel "Concept 4" here: Concept 4 is
    narrower than Concept 3, Concept 5 narrower than Concept 4."""

    def setUp(self):
        super().setUp()
        self.add_label(self.concepts[4], "Concept 4")

    def reconcile_one(self, query_text, properties):
        return self.reconcile({"q0": {"query": query_text, "properties": properties}})[
            "q0"
        ]["result"]

    def matched_id(self, results):
        matched_ids = [result["id"] for result in results if result["match"]]
        return matched_ids[0] if matched_ids else None

    def add_tile(self, concept, nodegroup_id, data):
        TileModel.objects.create(
            resourceinstance=concept, nodegroup_id=nodegroup_id, data=data
        )

    def test_broader_term_settles_a_homograph_by_label_or_id(self):
        by_label = self.reconcile_one(
            "Concept 4", [{"pid": "broader", "v": "concept 3"}]
        )
        by_id = self.reconcile_one(
            "Concept 4", [{"pid": "broader", "v": {"id": str(self.concepts[3].pk)}}]
        )

        self.assertEqual(self.matched_id(by_label), str(self.concepts[3].pk))
        self.assertEqual(by_label[0]["score"], 100)
        self.assertEqual(by_label[1]["score"], 70)
        self.assertEqual(self.matched_id(by_id), str(self.concepts[4].pk))

    def test_alternate_label_boosts_its_concept(self):
        self.add_label(self.concepts[2], "Third", label_type="altLabel")

        results = self.reconcile_one("Concept", [{"pid": "altLabel", "v": "THIRD"}])

        self.assertEqual(results[0]["id"], str(self.concepts[2].pk))
        self.assertEqual(results[0]["score"], results[1]["score"] + 10)

    def test_notation_identifies_a_concept_and_contradicts_the_rest(self):
        self.add_tile(
            self.concepts[1], IDENTIFIER_NODEGROUP, {IDENTIFIER_CONTENT_NODE: "C-2"}
        )

        unlabelled = self.reconcile_one(
            "no such label", [{"pid": "notation", "v": "C-2"}]
        )
        overruled = self.reconcile_one("Concept 3", [{"pid": "notation", "v": "C-2"}])

        self.assertEqual(self.matched_id(unlabelled), str(self.concepts[1].pk))
        self.assertEqual(self.matched_id(overruled), str(self.concepts[1].pk))

        set_lifecycle_state(self.concepts[1], DRAFT_STATE_ID)
        hidden = self.reconcile_one("no such label", [{"pid": "notation", "v": "C-2"}])
        self.assertEqual(hidden, [])

    def test_exact_match_uri_identifies_linked_and_own_uris(self):
        self.add_tile(
            self.concepts[2],
            MATCH_STATUS_NODEGROUP,
            {
                MATCH_STATUS_RELATION_NODE: [
                    get_list_item_tile_value(EXACT_MATCH_LIST_ITEM_ID)
                ],
                MATCH_STATUS_COMPARATE_NODE: "http://example.org/third",
            },
        )
        self.add_tile(
            self.concepts[0], URI_NODEGROUP, {URI_CONTENT_NODE: "https://lingo/c1"}
        )

        linked = self.reconcile_one(
            "no such label",
            [{"pid": "exactMatch", "v": "HTTP://EXAMPLE.ORG/third"}],
        )
        own = self.reconcile_one(
            "no such label", [{"pid": "exactMatch", "v": "https://lingo/c1"}]
        )

        self.assertEqual(self.matched_id(linked), str(self.concepts[2].pk))
        self.assertEqual(self.matched_id(own), str(self.concepts[0].pk))

    def test_language_chooses_the_returned_name(self):
        self.add_label(self.concepts[2], "Concept trois", language="fr")
        self.add_label(
            self.concepts[2], "Concept 3", label_type="altLabel", language="fr"
        )

        results = self.reconcile_one("Concept 3", [{"pid": "lang", "v": "fr"}])
        in_regional_language = self.reconcile_one(
            "concept trois", [{"pid": "lang", "v": "fr-CA"}]
        )

        self.assertEqual(results[0]["name"], "Concept trois")
        # The exact prefLabel is English (the French label is only an altLabel),
        # so a French query is not matched automatically.
        self.assertFalse(results[0]["match"])
        self.assertTrue(in_regional_language[0]["match"])

    def test_include_retired_flags_retired_concepts(self):
        set_lifecycle_state(self.concepts[2], RETIRED_STATE_ID)

        default = self.reconcile_one("Concept 3", [])
        opted_in = self.reconcile_one(
            "Concept 3", [{"pid": "includeRetired", "v": "true"}]
        )

        self.assertNotIn(str(self.concepts[2].pk), self.result_ids(default))
        self.assertEqual(opted_in[0]["id"], str(self.concepts[2].pk))
        self.assertTrue(opted_in[0]["description"].endswith("(retired)"))
        self.assertFalse(opted_in[0]["match"])


class ReconciliationSuggestTests(ReconciliationQueryTestCase):
    def suggest(self, suggest_kind, **parameters):
        return self.client.get(
            reverse(
                "api-lingo-reconcile-suggest", kwargs={"suggest_kind": suggest_kind}
            ),
            parameters,
        )

    def test_entity_suggest_lists_public_concepts_with_paging(self):
        set_lifecycle_state(self.concepts[4], DRAFT_STATE_ID)

        first_page = self.suggest("entity", prefix="concept").json()["result"]
        later_page = self.suggest("entity", prefix="concept", cursor=2).json()
        scoped_elsewhere = self.suggest(
            "entity", prefix="concept", type=str(uuid.uuid4())
        ).json()

        self.assertEqual(
            [suggestion["name"] for suggestion in first_page],
            ["Concept 1", "Concept 2", "Concept 3", "Concept 4"],
        )
        # The fixture's Concept 2 names Concept 1 twice in one tile.
        self.assertEqual(first_page[1]["description"], "Concept 1 · Test Scheme")
        self.assertEqual(
            first_page[2]["description"], "Concept 1, Concept 2 · Test Scheme"
        )
        self.assertEqual(len(later_page["result"]), 2)
        self.assertEqual(scoped_elsewhere["result"], [])
        self.assertEqual(self.suggest("entity", prefix=" ").json()["result"], [])

    def test_type_and_property_suggest_filter_by_prefix(self):
        self.assertEqual(
            self.suggest("type", prefix="TEST").json()["result"],
            [{"id": str(self.scheme.pk), "name": "Test Scheme"}],
        )
        self.assertEqual(self.suggest("type", prefix="zzz").json()["result"], [])
        self.assertEqual(
            self.suggest("property", prefix="broad").json()["result"],
            [{"id": "broader", "name": "Broader concept (label or id)"}],
        )
        self.assertEqual(len(self.suggest("property").json()["result"]), 6)

    def test_scheme_service_suggestions_stay_in_the_scheme(self):
        other_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Test Other"
        )
        set_lifecycle_state(other_scheme, PUBLISHED_STATE_ID)

        def scheme_suggest(suggest_kind, **parameters):
            return self.client.get(
                reverse(
                    "api-lingo-scheme-reconcile-suggest",
                    kwargs={
                        "scheme_identifier": "test-scheme",
                        "suggest_kind": suggest_kind,
                    },
                ),
                parameters,
            ).json()["result"]

        self.assertEqual(len(self.suggest("type", prefix="test").json()["result"]), 2)
        self.assertEqual(
            scheme_suggest("type", prefix="test"),
            [{"id": str(self.scheme.pk), "name": "Test Scheme"}],
        )
        self.assertEqual(len(scheme_suggest("entity", prefix="concept")), 5)
        self.assertEqual(
            scheme_suggest("entity", prefix="concept", type=str(other_scheme.pk)), []
        )
        self.assertEqual(len(scheme_suggest("property", prefix="broad")), 1)

    def test_invalid_suggest_requests(self):
        unknown_kind = self.suggest("colour", prefix="x")
        self.assertEqual(unknown_kind.status_code, 404)
        self.assertEqual(unknown_kind["Access-Control-Allow-Origin"], "*")
        self.assertEqual(self.suggest("type", cursor="-1").status_code, 400)
        self.assertEqual(self.suggest("type", cursor="first").status_code, 400)
        self.assertEqual(self.suggest("entity", prefix="c" * 256).status_code, 400)


class ReconciliationPreviewTests(ReconciliationQueryTestCase):
    def preview(self, concept_id):
        return self.client.get(
            reverse("api-lingo-reconcile-preview"), {"id": str(concept_id)}
        )

    def add_note(self, concept, content, language):
        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=STATEMENT_NODEGROUP,
            data={
                STATEMENT_CONTENT_NODE: content,
                STATEMENT_LANGUAGE_NODE: language,
                STATEMENT_TYPE_NODE: [
                    {"labels": [{"language_id": "en", "value": "Scope note"}]}
                ],
            },
        )

    def test_preview_card_shows_labels_note_and_uri_in_the_active_language(self):
        self.add_label(self.concepts[2], "Third", label_type="altLabel")
        self.add_label(
            self.concepts[2], "Troisième", label_type="altLabel", language="fr"
        )
        self.add_note(self.concepts[2], "Une note.", "fr")
        self.add_note(self.concepts[2], "An English note.", "en")
        TileModel.objects.create(
            resourceinstance=self.concepts[2],
            nodegroup_id=URI_NODEGROUP,
            data={URI_CONTENT_NODE: "https://lingo.example/c3"},
        )

        response = self.preview(self.concepts[2].pk)
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Frame-Options", response)
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        for expected_text in [
            "Concept 3",
            "Concept 1, Concept 2 · Test Scheme",
            "Third",
            "Scope note",
            "An English note.",
            "https://lingo.example/c3",
        ]:
            self.assertIn(expected_text, content)
        self.assertNotIn("Troisième", content)
        self.assertNotIn("Une note.", content)

    def test_preview_falls_back_to_a_note_in_another_language(self):
        self.add_note(self.concepts[1], "Une note.", "fr")

        self.assertIn(
            '<dd lang="fr">Une note.</dd>',
            self.preview(self.concepts[1].pk).content.decode(),
        )

    def test_note_type_is_named_in_the_display_language(self):
        note_type = [
            {
                "labels": [
                    {"language_id": "en", "value": "Scope note"},
                    {"language_id": "fr", "value": "Note d'application"},
                ]
            }
        ]

        self.assertEqual(
            extract_note_type_label(note_type, "fr-CA"), "Note d'application"
        )
        self.assertEqual(extract_note_type_label(note_type, "de"), "Scope note")

    def test_retired_concepts_are_flagged(self):
        set_lifecycle_state(self.concepts[2], RETIRED_STATE_ID)

        self.assertIn("Retired", self.preview(self.concepts[2].pk).content.decode())

    def test_preview_never_reveals_non_public_concepts(self):
        set_lifecycle_state(self.concepts[1], DRAFT_STATE_ID)
        self.assertEqual(self.preview(self.concepts[1].pk).status_code, 404)
        self.assertEqual(self.preview("not-a-uuid").status_code, 404)

        set_lifecycle_state(self.scheme, DRAFT_STATE_ID)
        self.assertEqual(self.preview(self.concepts[2].pk).status_code, 404)


# Controlled list backing match_status_ascribed_relation (SKOS mapping properties).
MAPPING_PROPERTIES_LIST_ID = "769fa072-6247-4e23-b638-4e801f8c50dc"


class ReconciliationExtensionTests(ReconciliationQueryTestCase):
    def extend(self, ids, properties, method="post"):
        extension_request = {
            "extend": json.dumps(
                {
                    "ids": [str(concept_id) for concept_id in ids],
                    "properties": properties,
                }
            )
        }
        return getattr(self.client, method)(
            reverse("api-lingo-reconcile"), extension_request
        )

    def test_columns_come_from_the_concepts_published_skos(self):
        concept_3 = self.concepts[2]
        TileModel.objects.create(
            resourceinstance=concept_3,
            nodegroup_id=URI_NODEGROUP,
            data={URI_CONTENT_NODE: "https://lingo.example/c3"},
        )
        TileModel.objects.create(
            resourceinstance=self.concepts[0],
            nodegroup_id=URI_NODEGROUP,
            data={URI_CONTENT_NODE: "https://lingo.example/c1"},
        )
        TileModel.objects.create(
            resourceinstance=concept_3,
            nodegroup_id=MATCH_STATUS_NODEGROUP,
            data={
                MATCH_STATUS_RELATION_NODE: DataTypeFactory()
                .get_instance("reference")
                .transform_value_for_tile(
                    "exactMatch", controlledList=MAPPING_PROPERTIES_LIST_ID
                ),
                MATCH_STATUS_COMPARATE_NODE: "http://example.org/third",
            },
        )
        self.add_label(concept_3, "Concept trois", language="fr")
        self.add_label(self.concepts[0], "Concept un", language="fr")

        response = self.extend(
            [concept_3.pk],
            [
                {"id": "uri"},
                {"id": "prefLabel"},
                {"id": "inScheme"},
                {"id": "exactMatch"},
            ],
        ).json()
        # Concept 2's only broader concept, Concept 1, has a minted URI.
        broader_by_minted_uri = self.extend(
            [self.concepts[1].pk], [{"id": "broader", "settings": {"lang": "fr"}}]
        ).json()
        all_languages = self.extend(
            [concept_3.pk], [{"id": "prefLabel", "settings": {"lang": "*"}}]
        ).json()

        self.assertEqual(
            [column["id"] for column in response["meta"]],
            ["uri", "prefLabel", "inScheme", "exactMatch"],
        )
        self.assertEqual(
            response["rows"][str(concept_3.pk)],
            {
                "uri": [{"str": "https://lingo.example/c3"}],
                "prefLabel": [{"str": "Concept 3"}],
                "inScheme": [{"str": "Test Scheme"}],
                "exactMatch": [{"str": "http://example.org/third"}],
            },
        )
        self.assertEqual(
            broader_by_minted_uri["rows"][str(self.concepts[1].pk)]["broader"],
            [{"id": str(self.concepts[0].pk), "name": "Concept un"}],
        )
        self.assertEqual(
            all_languages["rows"][str(concept_3.pk)]["prefLabel"],
            [{"str": "Concept 3"}, {"str": "Concept trois"}],
        )

    def test_non_public_concepts_get_empty_rows(self):
        set_lifecycle_state(self.concepts[0], DRAFT_STATE_ID)
        set_lifecycle_state(self.concepts[1], DRAFT_STATE_ID)
        requested_ids = [self.concepts[2].pk, self.concepts[1].pk, "not-a-uuid"]

        rows = self.extend(requested_ids, [{"id": "broader"}], method="get").json()[
            "rows"
        ]

        self.assertEqual(rows[str(self.concepts[1].pk)], {"broader": []})
        self.assertEqual(rows["not-a-uuid"], {"broader": []})
        # The draft broader concepts are not revealed either.
        self.assertEqual(rows[str(self.concepts[2].pk)], {"broader": []})

        set_lifecycle_state(self.scheme, DRAFT_STATE_ID)
        hidden_scheme_rows = self.extend(
            [self.concepts[3].pk], [{"id": "prefLabel"}]
        ).json()["rows"]
        self.assertEqual(
            hidden_scheme_rows, {str(self.concepts[3].pk): {"prefLabel": []}}
        )

    def test_match_columns_reveal_only_public_local_resources(self):
        draft_concept = self.concepts[4]
        set_lifecycle_state(draft_concept, DRAFT_STATE_ID)
        TileModel.objects.create(
            resourceinstance=draft_concept,
            nodegroup_id=URI_NODEGROUP,
            data={URI_CONTENT_NODE: "https://lingo.example/c5"},
        )
        public_uris = [
            str(ARCHES[str(self.concepts[0].pk)]),
            str(ARCHES[str(self.scheme.pk)]),
            str(ARCHES["not-a-resource"]),
        ]
        for comparate in [
            str(ARCHES[str(draft_concept.pk)]),
            "https://lingo.example/c5",
            *public_uris,
        ]:
            TileModel.objects.create(
                resourceinstance=self.concepts[2],
                nodegroup_id=MATCH_STATUS_NODEGROUP,
                data={
                    MATCH_STATUS_RELATION_NODE: DataTypeFactory()
                    .get_instance("reference")
                    .transform_value_for_tile(
                        "exactMatch", controlledList=MAPPING_PROPERTIES_LIST_ID
                    ),
                    MATCH_STATUS_COMPARATE_NODE: comparate,
                },
            )

        rows = self.extend([self.concepts[2].pk], [{"id": "exactMatch"}]).json()["rows"]

        self.assertEqual(
            rows[str(self.concepts[2].pk)]["exactMatch"],
            [{"str": uri} for uri in sorted(public_uris)],
        )

    def test_malformed_extension_requests_are_rejected(self):
        too_many_ids = [str(uuid.uuid4()) for _ in range(MAX_QUERIES_PER_REQUEST + 1)]
        for raw_extension_request in [
            "not json",
            json.dumps(["ids"]),
            json.dumps({"ids": "abc", "properties": []}),
            json.dumps({"ids": too_many_ids, "properties": []}),
            json.dumps({"ids": [], "properties": "uri"}),
            json.dumps({"ids": [], "properties": [{"id": "colour"}]}),
            json.dumps({"ids": [], "properties": [{"id": "uri"}, {"id": "uri"}]}),
            json.dumps({"ids": [], "properties": [{"id": "uri", "settings": "fr"}]}),
            json.dumps(
                {"ids": [], "properties": [{"id": "uri", "settings": {"lang": 3}}]}
            ),
        ]:
            with self.subTest(raw_extension_request=raw_extension_request[:40]):
                response = self.client.post(
                    reverse("api-lingo-reconcile"), {"extend": raw_extension_request}
                )
                self.assertEqual(response.status_code, 400)

    def test_property_proposals(self):
        proposals_url = reverse("api-lingo-reconcile-properties")

        all_proposals = self.client.get(proposals_url, {"type": "scheme"}).json()
        limited = self.client.get(proposals_url, {"limit": "2"}).json()

        self.assertEqual(all_proposals["type"], "scheme")
        self.assertEqual(len(all_proposals["properties"]), 10)
        self.assertEqual(
            limited["properties"],
            [{"id": "uri", "name": "URI"}, {"id": "notation", "name": "Identifier"}],
        )
        for bad_limit in ["0", "two"]:
            self.assertEqual(
                self.client.get(proposals_url, {"limit": bad_limit}).status_code, 400
            )
