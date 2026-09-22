"""Tests for concept match detection.

The engine's job is to suggest pairs an editor has not already settled, once
each, scoped to what was asked for. These cover that logic rather than the SQL
that implements it, so the signals stay replaceable.
"""

import json
from http import HTTPStatus
from io import StringIO

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.core.management import call_command
from django.core.management.base import CommandError

from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPTS_GRAPH_ID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    EXACT_MATCH_LIST_ITEM_ID,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    SCHEMES_GRAPH_ID,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.models import (
    ConceptMatchCandidate,
    ConceptMatchRun,
    ConceptMatchRun,
    ConceptMerge,
    ConceptSet,
    ConceptSetMember,
)
from arches_lingo.utils.concept_lifecycle import (
    EDITING_STATE_ID,
    PUBLISHED_STATE_ID,
)
from arches_lingo.utils.concept_merge import get_list_item_tile_value
from arches_lingo.utils.concept_matching_service import (
    MAX_LINK_BATCH,
    ConceptMatchRequestError,
    link_candidates_with_exact_match,
    serialize_candidate_page,
    serialize_run,
    set_candidate_status,
    start_detection,
)
from unittest.mock import patch

from arches_lingo.utils.concept_matching import (
    ALL_SIGNALS,
    DEFAULT_SIMILARITY_THRESHOLD,
    EXACT_SIGNALS,
    SIGNAL_TRIGRAM,
    find_similar_label_pairs,
    SIGNAL_EXACT_LABEL,
    SIGNAL_SHARED_IDENTIFIER,
    ConceptMatchError,
    MatchScope,
    collect_candidates,
    find_decided_pairs,
    find_exact_label_pairs,
    find_shared_uri_pairs,
    mark_pairs_settled,
    run_detection,
)
from tests.tests import ViewTests

# These tests can be run from the command line via:
# python manage.py test tests.test_concept_matching --settings="tests.test_settings"


class ConceptMatchingTestCase(ViewTests):
    """Two concepts in the shared scheme, plus helpers to give them values."""

    def setUp(self):
        super().setUp()
        self.first_concept = self.concepts[1]
        self.second_concept = self.concepts[2]
        ResourceInstance.objects.filter(
            pk__in=[self.first_concept.pk, self.second_concept.pk]
        ).update(resource_instance_lifecycle_state_id=EDITING_STATE_ID)

    def add_label(self, concept, content, language="en"):
        return TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: content,
                CONCEPT_NAME_LANGUAGE_NODE: language,
            },
        )

    def clear_labels(self, concept):
        """Drop the fixture's own labels from a concept.

        ViewTests names its concepts "Concept 1" ... "Concept 5", which are
        highly similar to each other -- fine for the exact signals, but it means
        a fuzzy test would measure the fixture rather than the code.
        """
        TileModel.objects.filter(
            resourceinstance=concept, nodegroup_id=CONCEPT_NAME_NODEGROUP
        ).delete()

    def add_uri(self, concept, uri):
        return TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=URI_NODEGROUP,
            data={URI_CONTENT_NODE: uri},
        )

    def add_exact_match(self, concept, matched_uri):
        return TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=MATCH_STATUS_NODEGROUP,
            data={
                MATCH_STATUS_RELATION_NODE: [
                    get_list_item_tile_value(EXACT_MATCH_LIST_ITEM_ID)
                ],
                MATCH_STATUS_COMPARATE_NODE: matched_uri,
            },
        )

    def make_concept_in_other_scheme(self, name="Outsider"):
        other_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Other Scheme"
        )
        outsider = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID,
            name=name,
            resource_instance_lifecycle_state_id=EDITING_STATE_ID,
        )
        TileModel.objects.create(
            resourceinstance=outsider,
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {"resourceId": str(other_scheme.pk)}
                ]
            },
        )
        return other_scheme, outsider

    def pairs_of(self, found):
        return {
            (concept_a, concept_b) for concept_a, concept_b, _evidence, _score in found
        }

    def expected_pair(self, first_concept, second_concept):
        return ConceptMatchCandidate.order_concept_ids(
            first_concept.pk, second_concept.pk
        )


class ExactLabelSignalTests(ConceptMatchingTestCase):
    def test_concepts_sharing_a_label_are_suggested_once(self):
        """The pair is stored lowest id first, so it cannot appear twice under
        opposite names."""
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")

        found = list(find_exact_label_pairs(MatchScope()))

        self.assertEqual(len(found), 1)
        self.assertEqual(
            found[0][:2],
            self.expected_pair(self.first_concept, self.second_concept),
        )

    def test_case_and_surrounding_whitespace_are_not_a_difference(self):
        self.add_label(self.first_concept, "Trumpets")
        self.add_label(self.second_concept, "  trumpets ")

        self.assertEqual(len(list(find_exact_label_pairs(MatchScope()))), 1)

    def test_a_concept_is_never_paired_with_itself(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.first_concept, "trumpets", language="fr")

        self.assertEqual(list(find_exact_label_pairs(MatchScope(), False)), [])

    def test_languages_differ_by_default(self):
        """The same spelling in two languages is more often a coincidence than
        a duplicate, so it takes asking for."""
        self.add_label(self.first_concept, "chien", language="fr")
        self.add_label(self.second_concept, "chien", language="en")

        self.assertEqual(list(find_exact_label_pairs(MatchScope())), [])
        self.assertEqual(len(list(find_exact_label_pairs(MatchScope(), False))), 1)

    def test_blank_labels_are_not_a_match(self):
        self.add_label(self.first_concept, "   ")
        self.add_label(self.second_concept, "")

        self.assertEqual(list(find_exact_label_pairs(MatchScope())), [])


class SharedUriSignalTests(ConceptMatchingTestCase):
    def test_concepts_sharing_a_uri_are_suggested(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/1")

        found = list(find_shared_uri_pairs(MatchScope()))

        self.assertEqual(len(found), 1)
        self.assertEqual(
            found[0][:2],
            self.expected_pair(self.first_concept, self.second_concept),
        )

    def test_different_uris_are_not_a_match(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")

        self.assertEqual(list(find_shared_uri_pairs(MatchScope())), [])


class ScopeTests(ConceptMatchingTestCase):
    """Labels are added per test rather than in setUp: this class inherits
    ViewTests' own tests, and some of them count a concept's labels."""

    def label_three_concepts(self):
        self.third_concept = self.concepts[3]
        for concept in (self.first_concept, self.second_concept, self.third_concept):
            self.add_label(concept, "trumpets")

    def test_an_unscoped_run_pairs_every_combination(self):
        self.label_three_concepts()
        self.assertEqual(len(list(find_exact_label_pairs(MatchScope()))), 3)

    def test_scoping_to_a_concept_keeps_only_its_pairs(self):
        """Either side may be the scoped concept, since a pair has no
        direction once it is stored."""
        self.label_three_concepts()
        scope = MatchScope(source_concept_ids=[str(self.first_concept.pk)])

        found = self.pairs_of(find_exact_label_pairs(scope))

        self.assertEqual(len(found), 2)
        for pair in found:
            self.assertIn(str(self.first_concept.pk), pair)

    def test_scoping_to_a_concept_set_keeps_only_its_members(self):
        self.label_three_concepts()
        concept_set = ConceptSet.objects.create(
            user=User.objects.get(username="admin"), name="Review batch"
        )
        ConceptSetMember.objects.create(
            concept_set=concept_set, concept_id=self.first_concept.pk
        )
        scope = MatchScope(source_concept_set_id=concept_set.pk)

        found = self.pairs_of(find_exact_label_pairs(scope))

        self.assertEqual(len(found), 2)

    def test_cross_scheme_only_discards_pairs_inside_one_scheme(self):
        self.label_three_concepts()
        _, outsider = self.make_concept_in_other_scheme()
        self.add_label(outsider, "trumpets")

        found = self.pairs_of(
            find_exact_label_pairs(MatchScope(cross_scheme_only=True))
        )

        self.assertEqual(len(found), 3)
        for pair in found:
            self.assertIn(str(outsider.pk), pair)

    def test_scoping_to_a_scheme_keeps_pairs_touching_it(self):
        self.label_three_concepts()
        _, outsider = self.make_concept_in_other_scheme()
        self.add_label(outsider, "trumpets")
        scope = MatchScope(source_scheme_id=str(self.scheme.pk))

        found = self.pairs_of(find_exact_label_pairs(scope))

        # Every pair has at least one concept in the original scheme; only the
        # pair made of two outsiders would be excluded, and there is one outsider.
        self.assertEqual(len(found), 6)


class TrigramSignalTests(ConceptMatchingTestCase):
    """The fuzzy signal, and the threshold that decides what it calls a match."""

    def start_from_a_clean_corpus(self):
        """Called per test rather than in setUp: this class inherits ViewTests'
        own tests, and clearing labels would break the ones that count them."""
        for concept in self.concepts:
            self.clear_labels(concept)

    def test_near_duplicate_labels_are_suggested_with_their_similarity(self):
        self.start_from_a_clean_corpus()
        self.add_label(self.first_concept, "engatillado en metales")
        self.add_label(self.second_concept, "engatillados en metales")

        found = list(find_similar_label_pairs(MatchScope(), 0.7))

        self.assertEqual(len(found), 1)
        concept_a, concept_b, evidence, score = found[0]
        self.assertEqual(
            (concept_a, concept_b),
            self.expected_pair(self.first_concept, self.second_concept),
        )
        self.assertGreater(score, 0.7)
        self.assertLess(score, 1.0)
        self.assertIn("engatillado en metales", evidence)

    def test_the_threshold_decides_what_counts_as_similar(self):
        """Postgres defaults this to 0.3, which is far too loose to be useful."""
        self.start_from_a_clean_corpus()
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpeters")

        self.assertEqual(list(find_similar_label_pairs(MatchScope(), 0.95)), [])
        self.assertEqual(len(list(find_similar_label_pairs(MatchScope(), 0.4))), 1)

    def test_identical_labels_are_left_to_the_exact_signal(self):
        self.start_from_a_clean_corpus()
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")

        self.assertEqual(list(find_similar_label_pairs(MatchScope(), 0.5)), [])

    def test_an_exact_match_is_never_downgraded_to_a_fuzzy_one(self):
        """The pair is reported once, by its strongest signal."""
        self.start_from_a_clean_corpus()
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.first_concept, "trumpeters", language="fr")
        self.add_label(self.second_concept, "trumpets")
        self.add_label(self.second_concept, "trumpeter", language="fr")

        candidates = collect_candidates(MatchScope(), signals=ALL_SIGNALS)

        self.assertEqual(len(candidates), 1)
        signal, _evidence, score = next(iter(candidates.values()))
        self.assertEqual(signal, SIGNAL_EXACT_LABEL)
        self.assertEqual(score, 1.0)

    def test_a_fuzzy_run_records_the_similarity_as_the_score(self):
        self.start_from_a_clean_corpus()
        self.add_label(self.first_concept, "engatillado en metales")
        self.add_label(self.second_concept, "engatillados en metales")

        run = run_detection(
            MatchScope(),
            signals=(SIGNAL_TRIGRAM,),
            similarity_threshold=0.7,
            log=lambda message: None,
        )

        candidate = run.candidates.get()
        self.assertEqual(candidate.signal, SIGNAL_TRIGRAM)
        self.assertGreater(candidate.score, 0.7)
        self.assertLess(candidate.score, 1.0)


class StartDetectionTests(ConceptMatchingTestCase):
    """Exact signals answer inside the request; the fuzzy one goes to a worker."""

    def test_exact_signals_run_in_the_foreground(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")

        run = start_detection(
            MatchScope(), EXACT_SIGNALS, True, DEFAULT_SIMILARITY_THRESHOLD, None
        )

        self.assertEqual(run.status, ConceptMatchRun.STATUS_COMPLETE)
        self.assertEqual(run.candidate_count, 1)

    @patch("arches_lingo.utils.concept_matching_service.detect_concept_matches_task")
    @patch(
        "arches_lingo.utils.concept_matching_service.task_management"
        ".check_if_celery_available",
        return_value=True,
    )
    def test_the_fuzzy_signal_is_handed_to_a_worker(self, _celery_available, mock_task):
        """Comparing every label against every other takes minutes, which is
        far too long to hold a request open."""
        run = start_detection(MatchScope(), (SIGNAL_TRIGRAM,), True, 0.7, None)

        self.assertEqual(run.status, ConceptMatchRun.STATUS_PENDING)
        mock_task.apply_async.assert_called_once()
        queued_run_id = mock_task.apply_async.call_args.kwargs["args"][0]
        self.assertEqual(queued_run_id, run.pk)

    @patch(
        "arches_lingo.utils.concept_matching_service.task_management"
        ".check_if_celery_available",
        return_value=False,
    )
    def test_no_worker_is_an_actionable_error(self, _celery_available):
        with self.assertRaises(ConceptMatchRequestError) as raised:
            start_detection(MatchScope(), (SIGNAL_TRIGRAM,), True, 0.7, None)

        self.assertIn("detect_concept_matches", raised.exception.message)


class DecidedPairTests(ConceptMatchingTestCase):
    def test_a_merged_pair_is_not_suggested_again(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        ConceptMerge.objects.create(
            survivor_concept_id=self.first_concept.pk,
            absorbed_concept_id=self.second_concept.pk,
        )

        self.assertIn(
            self.expected_pair(self.first_concept, self.second_concept),
            find_decided_pairs(),
        )
        self.assertEqual(collect_candidates(MatchScope()), {})

    def test_an_exact_match_tile_settles_the_pair(self):
        """The tile names the other concept by URI, so the link is resolved
        back through the URI tiles."""
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        self.add_exact_match(self.first_concept, "https://example.org/concepts/2")

        self.assertEqual(collect_candidates(MatchScope()), {})

    def test_an_unrelated_match_tile_settles_nothing(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        self.add_exact_match(self.first_concept, "https://example.org/elsewhere")

        self.assertEqual(len(collect_candidates(MatchScope())), 1)


class CollectCandidateTests(ConceptMatchingTestCase):
    def test_a_pair_found_by_two_signals_keeps_the_stronger_reason(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        self.add_uri(self.first_concept, "https://example.org/concepts/shared")
        self.add_uri(self.second_concept, "https://example.org/concepts/shared")

        candidates = collect_candidates(MatchScope())

        self.assertEqual(len(candidates), 1)
        signal, evidence, _score = next(iter(candidates.values()))
        self.assertEqual(signal, SIGNAL_SHARED_IDENTIFIER)
        self.assertEqual(evidence, "https://example.org/concepts/shared")

    def test_a_signal_can_be_left_out(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")

        self.assertEqual(
            collect_candidates(MatchScope(), signals=(SIGNAL_SHARED_IDENTIFIER,)), {}
        )

    def test_an_unsupported_signal_is_rejected(self):
        with self.assertRaises(ConceptMatchError):
            collect_candidates(MatchScope(), signals=("phonetic",))


class RunDetectionTests(ConceptMatchingTestCase):
    def test_a_run_records_its_candidates_and_parameters(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")

        run = run_detection(MatchScope(), log=lambda message: None)

        self.assertEqual(run.status, ConceptMatchRun.STATUS_COMPLETE)
        self.assertEqual(run.candidate_count, 1)
        self.assertIsNotNone(run.finished)
        self.assertEqual(run.parameters["same_language_only"], True)

        candidate = run.candidates.get()
        self.assertEqual(candidate.signal, SIGNAL_EXACT_LABEL)
        self.assertEqual(candidate.score, 1.0)
        self.assertEqual(candidate.evidence, "trumpets")
        self.assertEqual(candidate.status, ConceptMatchCandidate.STATUS_PENDING)

    def test_a_failed_run_is_recorded_rather_than_lost(self):
        with self.assertRaises(ConceptMatchError):
            run_detection(MatchScope(), signals=("phonetic",), log=lambda message: None)

        run = ConceptMatchRun.objects.get()
        self.assertEqual(run.status, ConceptMatchRun.STATUS_FAILED)
        self.assertIn("phonetic", run.error_message)


class CandidateReviewTests(ConceptMatchingTestCase):
    """What the review interface reads and writes, via the service layer."""

    def make_run_with_one_candidate(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        return run_detection(MatchScope(), log=lambda message: None)

    def test_a_page_of_candidates_names_both_concepts_and_their_schemes(self):
        run = self.make_run_with_one_candidate()

        page = serialize_candidate_page(run)

        self.assertEqual(page["total_results"], 1)
        candidate = page["data"][0]
        self.assertEqual(candidate["evidence"], "trumpets")
        for side in ("concept_a", "concept_b"):
            self.assertTrue(candidate[side]["labels"])
            self.assertEqual(candidate[side]["scheme_id"], str(self.scheme.pk))
        self.assertFalse(candidate["is_cross_scheme"])

    def test_a_pair_spanning_two_schemes_is_marked_as_such(self):
        _, outsider = self.make_concept_in_other_scheme()
        self.add_label(self.first_concept, "trumpets")
        self.add_label(outsider, "trumpets")
        run = run_detection(MatchScope(), log=lambda message: None)

        candidate = serialize_candidate_page(run)["data"][0]

        self.assertTrue(candidate["is_cross_scheme"])

    def test_candidates_can_be_filtered_by_status(self):
        run = self.make_run_with_one_candidate()
        candidate_id = run.candidates.get().pk
        set_candidate_status(
            run,
            [candidate_id],
            ConceptMatchCandidate.STATUS_DISMISSED,
            User.objects.get(username="admin"),
        )

        pending = serialize_candidate_page(
            run, status=ConceptMatchCandidate.STATUS_PENDING
        )
        dismissed = serialize_candidate_page(
            run, status=ConceptMatchCandidate.STATUS_DISMISSED
        )

        self.assertEqual(pending["total_results"], 0)
        self.assertEqual(dismissed["total_results"], 1)

    def test_dismissing_records_who_decided_and_when(self):
        run = self.make_run_with_one_candidate()
        admin = User.objects.get(username="admin")

        set_candidate_status(
            run,
            [run.candidates.get().pk],
            ConceptMatchCandidate.STATUS_DISMISSED,
            admin,
        )

        candidate = run.candidates.get()
        self.assertEqual(candidate.status, ConceptMatchCandidate.STATUS_DISMISSED)
        self.assertEqual(candidate.reviewed_by, admin)
        self.assertIsNotNone(candidate.reviewed_at)

    def test_linked_and_merged_are_not_settable_by_hand(self):
        """Those are consequences of doing the work, recorded by the code that
        does it, not decisions a reviewer types in."""
        run = self.make_run_with_one_candidate()

        for status in (
            ConceptMatchCandidate.STATUS_LINKED,
            ConceptMatchCandidate.STATUS_MERGED,
        ):
            with self.assertRaises(ConceptMatchRequestError):
                set_candidate_status(run, [run.candidates.get().pk], status, None)

    def test_a_run_reports_how_much_is_left_to_review(self):
        run = self.make_run_with_one_candidate()

        self.assertEqual(serialize_run(run)["pending_count"], 1)

        set_candidate_status(
            run,
            [run.candidates.get().pk],
            ConceptMatchCandidate.STATUS_DISMISSED,
            None,
        )
        self.assertEqual(serialize_run(run)["pending_count"], 0)


class BulkLinkTests(ConceptMatchingTestCase):
    """Linking says two concepts mean the same thing and leaves both in place."""

    def make_run_for(self, concept_a, concept_b):
        self.add_label(concept_a, "trumpets")
        self.add_label(concept_b, "trumpets")
        return run_detection(MatchScope(), log=lambda message: None)

    def match_uris_on(self, concept):
        return {
            tile.data[MATCH_STATUS_COMPARATE_NODE]
            for tile in TileModel.objects.filter(
                resourceinstance=concept, nodegroup_id=MATCH_STATUS_NODEGROUP
            )
        }

    def test_both_concepts_point_at_each_other(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        run = self.make_run_for(self.first_concept, self.second_concept)

        result = link_candidates_with_exact_match(run, [run.candidates.get().pk], None)

        self.assertEqual(result["linked"], 1)
        self.assertEqual(result["linked_one_way"], 0)
        self.assertEqual(
            self.match_uris_on(self.first_concept),
            {"https://example.org/concepts/2"},
        )
        self.assertEqual(
            self.match_uris_on(self.second_concept),
            {"https://example.org/concepts/1"},
        )
        self.assertEqual(
            run.candidates.get().status, ConceptMatchCandidate.STATUS_LINKED
        )

    def test_a_published_concept_is_linked_one_way(self):
        """It cannot be written to, but the half that can is still worth having."""
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        _, outsider = self.make_concept_in_other_scheme()
        self.add_uri(outsider, "https://example.org/concepts/outsider")
        run = self.make_run_for(self.first_concept, outsider)
        ResourceInstance.objects.filter(pk=outsider.pk).update(
            resource_instance_lifecycle_state_id=PUBLISHED_STATE_ID
        )

        result = link_candidates_with_exact_match(run, [run.candidates.get().pk], None)

        self.assertEqual(result["linked"], 1)
        self.assertEqual(result["linked_one_way"], 1)
        self.assertEqual(
            self.match_uris_on(self.first_concept),
            {"https://example.org/concepts/outsider"},
        )
        self.assertEqual(self.match_uris_on(outsider), set())

    def test_a_concept_without_a_uri_is_skipped_not_failed(self):
        """An exactMatch names the other concept by URI, so there is nothing to
        point at -- but one awkward pair must not cost the rest."""
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        run = self.make_run_for(self.first_concept, self.second_concept)

        result = link_candidates_with_exact_match(run, [run.candidates.get().pk], None)

        self.assertEqual(result["linked"], 0)
        self.assertEqual(result["skipped"], {"missing_uri": 1})
        self.assertEqual(
            run.candidates.get().status, ConceptMatchCandidate.STATUS_PENDING
        )

    def test_linking_twice_does_not_duplicate_the_tile(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        run = self.make_run_for(self.first_concept, self.second_concept)
        candidate_id = run.candidates.get().pk

        link_candidates_with_exact_match(run, [candidate_id], None)
        link_candidates_with_exact_match(run, [candidate_id], None)

        self.assertEqual(
            TileModel.objects.filter(nodegroup_id=MATCH_STATUS_NODEGROUP).count(), 2
        )

    def test_a_linked_pair_is_not_suggested_by_a_later_run(self):
        """Linking settles the pair, so the next run leaves it alone."""
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        run = self.make_run_for(self.first_concept, self.second_concept)
        link_candidates_with_exact_match(run, [run.candidates.get().pk], None)

        later_run = run_detection(MatchScope(), log=lambda message: None)

        self.assertEqual(later_run.candidate_count, 0)

    def test_an_oversized_batch_is_refused(self):
        run = self.make_run_for(self.first_concept, self.second_concept)

        with self.assertRaises(ConceptMatchRequestError):
            link_candidates_with_exact_match(run, list(range(MAX_LINK_BATCH + 1)), None)


class PairSettlementTests(ConceptMatchingTestCase):
    """A decision made in one place settles the pair everywhere it is queued."""

    def test_a_merge_settles_the_pair_in_every_run(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        first_run = run_detection(MatchScope(), log=lambda message: None)
        second_run = run_detection(MatchScope(), log=lambda message: None)

        client = Client()
        client.force_login(User.objects.get(username="admin"))
        response = client.post(
            reverse("api-concept-merge", kwargs={"pk": str(self.first_concept.pk)}),
            data=json.dumps(
                {
                    "absorbed_concept_id": str(self.second_concept.pk),
                    "tile_selections": [],
                    "create_exact_match_tiles": False,
                    "retire_absorbed_concept": False,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        for run in (first_run, second_run):
            self.assertEqual(
                run.candidates.get().status, ConceptMatchCandidate.STATUS_MERGED
            )

    def test_linking_settles_the_pair_in_a_run_it_was_not_reviewed_in(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        reviewed_run = run_detection(MatchScope(), log=lambda message: None)
        other_run = run_detection(MatchScope(), log=lambda message: None)

        link_candidates_with_exact_match(
            reviewed_run, [reviewed_run.candidates.get().pk], None
        )

        self.assertEqual(
            other_run.candidates.get().status,
            ConceptMatchCandidate.STATUS_LINKED,
        )

    def test_a_decision_already_recorded_is_not_overwritten(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        run = run_detection(MatchScope(), log=lambda message: None)
        set_candidate_status(
            run,
            [run.candidates.get().pk],
            ConceptMatchCandidate.STATUS_DISMISSED,
            None,
        )

        mark_pairs_settled(
            [(self.first_concept.pk, self.second_concept.pk)],
            ConceptMatchCandidate.STATUS_MERGED,
        )

        self.assertEqual(
            run.candidates.get().status, ConceptMatchCandidate.STATUS_DISMISSED
        )


class DetectConceptMatchesCommandTests(ConceptMatchingTestCase):
    def test_the_command_stores_a_reviewable_run(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        stdout = StringIO()

        call_command("detect_concept_matches", stdout=stdout)

        run = ConceptMatchRun.objects.get()
        self.assertEqual(run.candidate_count, 1)
        self.assertIn("1 candidate pair", stdout.getvalue())

    def test_an_unknown_user_is_an_actionable_error(self):
        with self.assertRaises(CommandError):
            call_command("detect_concept_matches", user="nobody", stdout=StringIO())
