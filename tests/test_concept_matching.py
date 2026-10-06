"""Tests for concept match detection and review."""

import datetime
import json
import threading
import uuid
from http import HTTPStatus
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from django.core.management.base import CommandError

from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import (
    LINGO_ADMIN_GROUP_NAME,
    LINGO_EDITOR_GROUP_NAME,
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
    ConceptMerge,
    ConceptSet,
    ConceptSetMember,
)
from arches_lingo.tasks import detect_concept_matches_task
from arches_lingo.utils.concept_lifecycle import (
    EDITING_STATE_ID,
    LOCKED_STATE_ID,
    PUBLISHED_STATE_ID,
    RETIRED_STATE_ID,
    STRATEGY_REPARENT_TO_SURVIVOR,
)
from arches_lingo.utils.concept_merge.service import merge_concepts
from arches_lingo.utils.concept_merge.tiles import get_list_item_tile_value
from arches_lingo.utils.concept_matching_service import (
    MAX_LINK_BATCH,
    STALE_RUN_SECONDS,
    ConceptMatchRequestError,
    delete_run,
    link_candidates_with_exact_match,
    reap_stale_runs,
    serialize_candidate_page,
    serialize_run,
    set_candidate_status,
    set_status_for_all,
    start_detection,
)
from arches_lingo.utils.concept_matching import (
    ALL_SIGNALS,
    DEFAULT_SIMILARITY_THRESHOLD,
    EXACT_SIGNALS,
    SIGNAL_EXACT_LABEL,
    SIGNAL_SHARED_IDENTIFIER,
    SIGNAL_TRIGRAM,
    ConceptMatchError,
    MatchScope,
    mark_pairs_settled,
    run_detection,
)
from tests.tests import SchemeWithConceptsTestCase

# These tests can be run from the command line via:
# python manage.py test tests.test_concept_matching --settings="tests.test_settings"


class ConceptMatchingTestCase(SchemeWithConceptsTestCase):

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
        """The fixture's "Concept 1" ... "Concept 5" labels are too similar for
        fuzzy tests."""
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

    def detect(self, scope=None, signals=EXACT_SIGNALS, **options):
        """Store a run and return {pair: (signal, evidence, score)} from it."""
        run = run_detection(
            scope or MatchScope(), signals=signals, log=lambda message: None, **options
        )
        return {
            (str(candidate.concept_a_id), str(candidate.concept_b_id)): (
                candidate.signal,
                candidate.evidence,
                candidate.score,
            )
            for candidate in run.candidates.all()
        }

    def detect_exact_labels(self, scope=None, same_language_only=True):
        return self.detect(
            scope, signals=(SIGNAL_EXACT_LABEL,), same_language_only=same_language_only
        )

    def detect_shared_uris(self, scope=None):
        return self.detect(scope, signals=(SIGNAL_SHARED_IDENTIFIER,))

    def detect_similar_labels(self, similarity_threshold):
        return self.detect(
            signals=(SIGNAL_TRIGRAM,), similarity_threshold=similarity_threshold
        )

    def expected_pair(self, first_concept, second_concept):
        return ConceptMatchCandidate.order_concept_ids(
            first_concept.pk, second_concept.pk
        )


class ExactLabelSignalTests(ConceptMatchingTestCase):
    def test_concepts_sharing_a_label_are_suggested_once(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")

        found = self.detect_exact_labels()

        self.assertEqual(
            list(found), [self.expected_pair(self.first_concept, self.second_concept)]
        )

    def test_case_and_surrounding_whitespace_are_not_a_difference(self):
        self.add_label(self.first_concept, "Trumpets")
        self.add_label(self.second_concept, "  trumpets ")

        self.assertEqual(len(self.detect_exact_labels()), 1)

    def test_a_concept_is_never_paired_with_itself(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.first_concept, "trumpets", language="fr")

        self.assertEqual(self.detect_exact_labels(same_language_only=False), {})

    def test_languages_differ_by_default(self):
        self.add_label(self.first_concept, "chien", language="fr")
        self.add_label(self.second_concept, "chien", language="en")

        self.assertEqual(self.detect_exact_labels(), {})
        self.assertEqual(len(self.detect_exact_labels(same_language_only=False)), 1)

    def test_blank_labels_are_not_a_match(self):
        self.add_label(self.first_concept, "   ")
        self.add_label(self.second_concept, "")

        self.assertEqual(self.detect_exact_labels(), {})


class SharedUriSignalTests(ConceptMatchingTestCase):
    def test_concepts_sharing_a_uri_are_suggested(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/1")

        found = self.detect_shared_uris()

        self.assertEqual(
            list(found), [self.expected_pair(self.first_concept, self.second_concept)]
        )

    def test_different_uris_are_not_a_match(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")

        self.assertEqual(self.detect_shared_uris(), {})


class ScopeTests(ConceptMatchingTestCase):
    def label_three_concepts(self):
        self.third_concept = self.concepts[3]
        for concept in (self.first_concept, self.second_concept, self.third_concept):
            self.add_label(concept, "trumpets")

    def test_an_unscoped_run_pairs_every_combination(self):
        self.label_three_concepts()
        self.assertEqual(len(self.detect_exact_labels()), 3)

    def test_scoping_to_a_concept_keeps_only_its_pairs(self):
        self.label_three_concepts()
        scope = MatchScope(source_concept_ids=[str(self.first_concept.pk)])

        found = self.detect_exact_labels(scope)

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

        found = self.detect_exact_labels(scope)

        self.assertEqual(len(found), 2)

    def test_cross_scheme_only_discards_pairs_inside_one_scheme(self):
        self.label_three_concepts()
        _, outsider = self.make_concept_in_other_scheme()
        self.add_label(outsider, "trumpets")

        found = self.detect_exact_labels(MatchScope(cross_scheme_only=True))

        self.assertEqual(len(found), 3)
        for pair in found:
            self.assertIn(str(outsider.pk), pair)

    def test_scoping_to_a_scheme_confines_the_run_to_it(self):
        self.label_three_concepts()
        _, outsider = self.make_concept_in_other_scheme()
        self.add_label(outsider, "trumpets")
        scope = MatchScope(scheme_ids=[str(self.scheme.pk)])

        found = self.detect_exact_labels(scope)

        self.assertEqual(len(found), 3)
        for pair in found:
            self.assertNotIn(str(outsider.pk), pair)

    def test_scoping_to_several_schemes_keeps_what_spans_them(self):
        self.label_three_concepts()
        other_scheme, outsider = self.make_concept_in_other_scheme()
        self.add_label(outsider, "trumpets")
        scope = MatchScope(scheme_ids=[str(self.scheme.pk), str(other_scheme.pk)])

        found = self.detect_exact_labels(scope)

        self.assertEqual(len(found), 6)

    def test_a_scheme_outside_the_scope_contributes_nothing(self):
        self.label_three_concepts()
        other_scheme, outsider = self.make_concept_in_other_scheme()
        self.add_label(outsider, "trumpets")
        scope = MatchScope(scheme_ids=[str(other_scheme.pk)])

        found = self.detect_exact_labels(scope)

        self.assertEqual(found, {})


class TrigramSignalTests(ConceptMatchingTestCase):
    def setUp(self):
        super().setUp()
        for concept in self.concepts:
            self.clear_labels(concept)

    def test_near_duplicate_labels_are_suggested_with_their_similarity(self):
        self.add_label(self.first_concept, "engatillado en metales")
        self.add_label(self.second_concept, "engatillados en metales")

        found = self.detect_similar_labels(0.7)

        self.assertEqual(
            list(found), [self.expected_pair(self.first_concept, self.second_concept)]
        )
        _signal, evidence, score = found[
            self.expected_pair(self.first_concept, self.second_concept)
        ]
        self.assertGreater(score, 0.7)
        self.assertLess(score, 1.0)
        self.assertIn("engatillado en metales", evidence)

    def test_the_threshold_decides_what_counts_as_similar(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpeters")

        self.assertEqual(self.detect_similar_labels(0.95), {})
        self.assertEqual(len(self.detect_similar_labels(0.4)), 1)

    def test_identical_labels_are_left_to_the_exact_signal(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")

        self.assertEqual(self.detect_similar_labels(0.5), {})

    def test_an_exact_match_is_never_downgraded_to_a_fuzzy_one(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.first_concept, "trumpeters", language="fr")
        self.add_label(self.second_concept, "trumpets")
        self.add_label(self.second_concept, "trumpeter", language="fr")

        candidates = self.detect(signals=ALL_SIGNALS)

        self.assertEqual(len(candidates), 1)
        signal, _evidence, score = next(iter(candidates.values()))
        self.assertEqual(signal, SIGNAL_EXACT_LABEL)
        self.assertEqual(score, 1.0)

    def test_a_fuzzy_run_records_the_similarity_as_the_score(self):
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
    @patch("arches_lingo.utils.concept_matching_service.detect_concept_matches_task")
    @patch(
        "arches_lingo.utils.concept_matching_service.task_management"
        ".check_if_celery_available",
        return_value=True,
    )
    def test_every_run_is_handed_to_a_worker(self, _celery_available, mock_task):
        run = start_detection(
            MatchScope(), EXACT_SIGNALS, True, DEFAULT_SIMILARITY_THRESHOLD, None
        )

        self.assertEqual(run.status, ConceptMatchRun.STATUS_PENDING)
        mock_task.apply_async.assert_called_once()
        queued_run_id = mock_task.apply_async.call_args.kwargs["args"][0]
        self.assertEqual(queued_run_id, run.pk)
        self.assertNotIn("queue", mock_task.apply_async.call_args.kwargs)

    @patch(
        "arches_lingo.utils.concept_matching_service.MATCH_TASK_QUEUE",
        "lingo_matching",
    )
    @patch("arches_lingo.utils.concept_matching_service.detect_concept_matches_task")
    @patch(
        "arches_lingo.utils.concept_matching_service.task_management"
        ".check_if_celery_available",
        return_value=True,
    )
    def test_a_configured_queue_is_used(self, _celery_available, mock_task):
        start_detection(
            MatchScope(), EXACT_SIGNALS, True, DEFAULT_SIMILARITY_THRESHOLD, None
        )

        self.assertEqual(
            mock_task.apply_async.call_args.kwargs["queue"], "lingo_matching"
        )

    @patch(
        "arches_lingo.utils.concept_matching_service.task_management"
        ".check_if_celery_available",
        return_value=False,
    )
    def test_no_worker_is_an_actionable_error(self, _celery_available):
        with self.assertRaises(ConceptMatchRequestError) as raised:
            start_detection(MatchScope(), (SIGNAL_TRIGRAM,), True, 0.7, None)

        self.assertIn("detect_concept_matches", raised.exception.message)

    @patch("arches_lingo.utils.concept_matching_service.detect_concept_matches_task")
    @patch(
        "arches_lingo.utils.concept_matching_service.task_management"
        ".check_if_celery_available",
        return_value=False,
    )
    def test_a_worker_busy_with_another_search_still_counts_as_available(
        self, _celery_available, mock_task
    ):
        ConceptMatchRun.objects.create(
            user=None,
            status=ConceptMatchRun.STATUS_RUNNING,
            last_progress=timezone.now(),
            parameters={"signals": [SIGNAL_TRIGRAM]},
        )

        run = start_detection(MatchScope(), (SIGNAL_TRIGRAM,), True, 0.7, None)

        self.assertEqual(run.status, ConceptMatchRun.STATUS_PENDING)
        mock_task.apply_async.assert_called_once()

    @patch(
        "arches_lingo.utils.concept_matching_service.task_management"
        ".check_if_celery_available",
        return_value=False,
    )
    def test_a_run_that_stopped_reporting_is_not_evidence_of_a_worker(
        self, _celery_available
    ):
        stranded = ConceptMatchRun.objects.create(
            user=None,
            status=ConceptMatchRun.STATUS_RUNNING,
            parameters={"signals": [SIGNAL_TRIGRAM]},
        )
        ConceptMatchRun.objects.filter(pk=stranded.pk).update(
            last_progress=timezone.now()
            - datetime.timedelta(seconds=STALE_RUN_SECONDS * 2)
        )

        with self.assertRaises(ConceptMatchRequestError):
            start_detection(MatchScope(), (SIGNAL_TRIGRAM,), True, 0.7, None)


class DecidedPairTests(ConceptMatchingTestCase):
    def test_a_merged_pair_is_not_suggested_again(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        ConceptMerge.objects.create(
            survivor_concept_id=self.first_concept.pk,
            absorbed_concept_id=self.second_concept.pk,
        )

        self.assertEqual(self.detect(), {})

    def test_an_exact_match_tile_settles_the_pair(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        self.add_exact_match(self.first_concept, "https://example.org/concepts/2")

        self.assertEqual(self.detect(), {})

    def test_a_match_other_than_exact_leaves_the_pair_open(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        TileModel.objects.create(
            resourceinstance=self.first_concept,
            nodegroup_id=MATCH_STATUS_NODEGROUP,
            data={
                MATCH_STATUS_RELATION_NODE: [
                    {"uri": "http://www.w3.org/2004/02/skos/core#closeMatch"}
                ],
                MATCH_STATUS_COMPARATE_NODE: "https://example.org/concepts/2",
            },
        )

        self.assertEqual(len(self.detect()), 1)

    def test_a_retired_concept_is_not_suggested(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        ResourceInstance.objects.filter(pk=self.second_concept.pk).update(
            resource_instance_lifecycle_state_id=RETIRED_STATE_ID
        )

        self.assertEqual(self.detect(), {})

    def test_an_unrelated_match_tile_settles_nothing(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        self.add_exact_match(self.first_concept, "https://example.org/elsewhere")

        self.assertEqual(len(self.detect()), 1)


class SignalPrecedenceTests(ConceptMatchingTestCase):
    def test_a_pair_found_by_two_signals_keeps_the_stronger_reason(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        self.add_uri(self.first_concept, "https://example.org/concepts/shared")
        self.add_uri(self.second_concept, "https://example.org/concepts/shared")

        candidates = self.detect()

        self.assertEqual(len(candidates), 1)
        signal, evidence, _score = next(iter(candidates.values()))
        self.assertEqual(signal, SIGNAL_SHARED_IDENTIFIER)
        self.assertEqual(evidence, "https://example.org/concepts/shared")

    def test_a_signal_can_be_left_out(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")

        self.assertEqual(self.detect_shared_uris(), {})

    def test_an_unsupported_signal_is_rejected(self):
        with self.assertRaises(ConceptMatchError):
            self.detect(signals=("phonetic",))


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
        with patch(
            "arches_lingo.utils.concept_matching._store_pairs",
            side_effect=RuntimeError("label query failed"),
        ):
            with self.assertRaises(RuntimeError):
                run_detection(MatchScope(), log=lambda message: None)

        run = ConceptMatchRun.objects.get()
        self.assertEqual(run.status, ConceptMatchRun.STATUS_FAILED)
        self.assertIn("label query failed", run.error_message)

    def test_unusable_options_are_refused_before_a_run_is_recorded(self):
        for signals, similarity_threshold in (
            (("phonetic",), DEFAULT_SIMILARITY_THRESHOLD),
            ((SIGNAL_TRIGRAM,), 0.05),
            ((SIGNAL_TRIGRAM,), 1.5),
        ):
            with self.subTest(signals=signals, threshold=similarity_threshold):
                with self.assertRaises(ConceptMatchError):
                    run_detection(
                        MatchScope(),
                        signals=signals,
                        similarity_threshold=similarity_threshold,
                        log=lambda message: None,
                    )

        self.assertFalse(ConceptMatchRun.objects.exists())


class CandidateReviewTests(ConceptMatchingTestCase):
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

    def test_a_concept_deleted_since_the_run_is_reported_missing(self):
        run = self.make_run_with_one_candidate()
        run.candidates.update(concept_b_id=uuid.uuid4())

        [row] = serialize_candidate_page(run)["data"]

        self.assertIsNotNone(row["concept_a"])
        self.assertIsNone(row["concept_b"])

    def test_a_pair_spanning_two_schemes_is_marked_as_such(self):
        _, outsider = self.make_concept_in_other_scheme()
        self.add_label(self.first_concept, "trumpets")
        self.add_label(outsider, "trumpets")
        run = run_detection(MatchScope(), log=lambda message: None)

        candidate = serialize_candidate_page(run)["data"][0]

        self.assertTrue(candidate["is_cross_scheme"])

    def test_a_concept_that_can_be_merged_into_says_so(self):
        run = self.make_run_with_one_candidate()

        candidate = serialize_candidate_page(run)["data"][0]

        for side in ("concept_a", "concept_b"):
            self.assertTrue(candidate[side]["can_receive_data"])
            self.assertIsNone(candidate[side]["cannot_receive_reason"])

    def test_a_published_concept_cannot_be_merged_into(self):
        run = self.make_run_with_one_candidate()
        ResourceInstance.objects.filter(pk=self.second_concept.pk).update(
            resource_instance_lifecycle_state_id=PUBLISHED_STATE_ID
        )

        candidate = serialize_candidate_page(run)["data"][0]
        by_id = {
            candidate["concept_a"]["id"]: candidate["concept_a"],
            candidate["concept_b"]["id"]: candidate["concept_b"],
        }

        self.assertTrue(by_id[str(self.first_concept.pk)]["can_receive_data"])
        published = by_id[str(self.second_concept.pk)]
        self.assertFalse(published["can_receive_data"])
        self.assertEqual(published["cannot_receive_reason"], "not_editable")

    def test_a_locked_scheme_stops_its_concepts_being_merged_into(self):
        run = self.make_run_with_one_candidate()
        ResourceInstance.objects.filter(pk=self.scheme.pk).update(
            resource_instance_lifecycle_state_id=LOCKED_STATE_ID
        )

        candidate = serialize_candidate_page(run)["data"][0]

        for side in ("concept_a", "concept_b"):
            self.assertFalse(candidate[side]["can_receive_data"])
            self.assertEqual(candidate[side]["cannot_receive_reason"], "scheme_locked")

    def test_a_lingo_admin_is_not_stopped_by_a_locked_scheme(self):
        run = self.make_run_with_one_candidate()
        ResourceInstance.objects.filter(pk=self.scheme.pk).update(
            resource_instance_lifecycle_state_id=LOCKED_STATE_ID
        )

        candidate = serialize_candidate_page(run, user_is_lingo_admin=True)["data"][0]

        for side in ("concept_a", "concept_b"):
            self.assertTrue(candidate[side]["can_receive_data"])

    def test_a_run_counts_its_pairs_by_what_was_decided(self):
        run = self.make_run_with_one_candidate()
        run.candidates.update(status=ConceptMatchCandidate.STATUS_MERGED)

        serialized = serialize_run(run)

        self.assertEqual(
            serialized["counts_by_status"],
            {"pending": 0, "dismissed": 0, "linked": 0, "merged": 1},
        )
        self.assertEqual(serialized["pending_count"], 0)

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
        run = self.make_run_with_one_candidate()

        for status in (
            ConceptMatchCandidate.STATUS_LINKED,
            ConceptMatchCandidate.STATUS_MERGED,
        ):
            with self.assertRaises(ConceptMatchRequestError):
                set_candidate_status(run, [run.candidates.get().pk], status, None)

    def test_a_linked_or_merged_pair_cannot_be_dismissed_or_restored(self):
        run = self.make_run_with_one_candidate()
        candidate = run.candidates.get()

        for decided_status in (
            ConceptMatchCandidate.STATUS_LINKED,
            ConceptMatchCandidate.STATUS_MERGED,
        ):
            run.candidates.update(status=decided_status)
            for requested_status in (
                ConceptMatchCandidate.STATUS_DISMISSED,
                ConceptMatchCandidate.STATUS_PENDING,
            ):
                with self.subTest(decided=decided_status, requested=requested_status):
                    result = set_candidate_status(
                        run, [candidate.pk], requested_status, None
                    )
                    self.assertEqual(result["updated"], 0)
                    candidate.refresh_from_db()
                    self.assertEqual(candidate.status, decided_status)

    def test_a_dismissed_pair_can_be_restored(self):
        run = self.make_run_with_one_candidate()
        candidate_ids = [run.candidates.get().pk]
        set_candidate_status(
            run, candidate_ids, ConceptMatchCandidate.STATUS_DISMISSED, None
        )

        result = set_candidate_status(
            run, candidate_ids, ConceptMatchCandidate.STATUS_PENDING, None
        )

        self.assertEqual(result["updated"], 1)


class BulkLinkTests(ConceptMatchingTestCase):
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

    def test_a_pair_that_cannot_be_written_is_skipped_with_its_reason(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        run = self.make_run_for(self.first_concept, self.second_concept)
        candidate = run.candidates.get()

        ResourceInstance.objects.filter(
            pk__in=[self.first_concept.pk, self.second_concept.pk]
        ).update(resource_instance_lifecycle_state_id=PUBLISHED_STATE_ID)
        neither_editable = link_candidates_with_exact_match(run, [candidate.pk], None)

        run.candidates.update(concept_b_id=uuid.uuid4())
        concept_deleted = link_candidates_with_exact_match(run, [candidate.pk], None)

        self.assertEqual(neither_editable["skipped"], {"not_editable": 1})
        self.assertEqual(concept_deleted["skipped"], {"missing_concept": 1})
        self.assertFalse(
            TileModel.objects.filter(nodegroup_id=MATCH_STATUS_NODEGROUP).exists()
        )

    def test_a_concept_without_a_uri_is_skipped_not_failed(self):
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
        second_attempt = link_candidates_with_exact_match(run, [candidate_id], None)

        self.assertEqual(second_attempt["linked"], 0)
        self.assertEqual(second_attempt["skipped"], {"already_decided": 1})
        self.assertEqual(
            TileModel.objects.filter(nodegroup_id=MATCH_STATUS_NODEGROUP).count(), 2
        )

    def test_a_dismissed_pair_is_not_linked(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        run = self.make_run_for(self.first_concept, self.second_concept)
        run.candidates.update(status=ConceptMatchCandidate.STATUS_DISMISSED)

        result = link_candidates_with_exact_match(run, [run.candidates.get().pk], None)

        self.assertEqual(result["skipped"], {"already_decided": 1})
        self.assertFalse(
            TileModel.objects.filter(nodegroup_id=MATCH_STATUS_NODEGROUP).exists()
        )

    def test_a_linked_pair_is_not_suggested_by_a_later_run(self):
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

    def test_a_merge_outranks_a_dismissal_and_nothing_outranks_a_merge(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        run = run_detection(MatchScope(), log=lambda message: None)
        set_candidate_status(
            run,
            [run.candidates.get().pk],
            ConceptMatchCandidate.STATUS_DISMISSED,
            None,
        )
        pair = [(self.first_concept.pk, self.second_concept.pk)]

        mark_pairs_settled(pair, ConceptMatchCandidate.STATUS_MERGED)
        mark_pairs_settled(pair, ConceptMatchCandidate.STATUS_LINKED)

        self.assertEqual(
            run.candidates.get().status, ConceptMatchCandidate.STATUS_MERGED
        )

    def test_retiring_the_absorbed_concept_hands_its_pairs_to_the_survivor(self):
        third_concept = self.concepts[3]
        ResourceInstance.objects.filter(pk=third_concept.pk).update(
            resource_instance_lifecycle_state_id=EDITING_STATE_ID
        )
        fourth_concept = self.concepts[4]
        for concept in (self.first_concept, self.second_concept, third_concept):
            self.add_label(concept, "chairs")
        self.add_label(fourth_concept, "stools")
        self.add_label(self.first_concept, "stools")
        run = run_detection(MatchScope(), log=lambda message: None)
        survivor, absorbed = self.second_concept, self.first_concept

        merge_concepts(
            survivor,
            absorbed,
            {
                "absorbed_concept_id": str(absorbed.pk),
                "tile_selections": [],
                "create_exact_match_tiles": False,
                "retire_absorbed_concept": True,
                "retirement_strategy": STRATEGY_REPARENT_TO_SURVIVOR,
            },
            User.objects.get(username="admin"),
        )

        pending_pairs = set(
            run.candidates.filter(
                status=ConceptMatchCandidate.STATUS_PENDING
            ).values_list("concept_a_id", "concept_b_id")
        )
        pending_pairs = {
            ConceptMatchCandidate.order_concept_ids(*pair) for pair in pending_pairs
        }
        # A ~ C was already asked as B ~ C, so it is dropped; A ~ D had no
        # counterpart, so it becomes B ~ D.
        self.assertEqual(
            pending_pairs,
            {
                self.expected_pair(survivor, third_concept),
                self.expected_pair(survivor, fourth_concept),
            },
        )


class ConceptMatchApiTests(ConceptMatchingTestCase):

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.admin = User.objects.get(username="admin")
        self.client.force_login(self.admin)
        for patcher in (
            patch(
                "arches_lingo.utils.concept_matching_service.task_management"
                ".check_if_celery_available",
                return_value=True,
            ),
            patch(
                "arches_lingo.utils.concept_matching_service"
                ".detect_concept_matches_task.apply_async",
                side_effect=lambda args, **options: detect_concept_matches_task(*args),
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def post_json(self, url, payload):
        return self.client.post(
            url, data=json.dumps(payload), content_type="application/json"
        )

    def create_run_with_one_pair(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        created = self.post_json(reverse("api-concept-match-runs"), {}).json()
        return self.client.get(
            reverse("api-concept-match-run-detail", args=[created["id"]])
        ).json()

    def test_a_run_is_created_and_listed(self):
        created = self.create_run_with_one_pair()

        self.assertEqual(created["status"], ConceptMatchRun.STATUS_COMPLETE)
        self.assertEqual(created["candidate_count"], 1)
        listed = self.client.get(reverse("api-concept-match-runs")).json()
        self.assertEqual([run["id"] for run in listed["data"]], [created["id"]])

    def test_a_run_records_the_name_and_schemes_it_was_given(self):
        for body, expected_name, expected_scheme_ids in (
            (
                {"name": "  Brass sweep  ", "scheme_ids": [str(self.scheme.pk)]},
                "Brass sweep",
                [str(self.scheme.pk)],
            ),
            ({}, "", []),
        ):
            with self.subTest(body=body):
                created = self.post_json(reverse("api-concept-match-runs"), body).json()
                self.assertEqual(created["name"], expected_name)
                self.assertEqual(
                    created["parameters"]["scheme_ids"], expected_scheme_ids
                )

    def make_editor(self, username, is_admin=False):
        editor = User.objects.create_user(username=username, password="x")
        editor.groups.add(Group.objects.get(name=LINGO_EDITOR_GROUP_NAME))
        if is_admin:
            editor.groups.add(Group.objects.get(name=LINGO_ADMIN_GROUP_NAME))
        return editor

    def test_every_editor_sees_every_run_and_who_started_it(self):
        created = self.create_run_with_one_pair()
        self.client.force_login(self.make_editor("someone"))

        listed = self.client.get(reverse("api-concept-match-runs")).json()["data"]

        self.assertEqual([run["id"] for run in listed], [created["id"]])
        self.assertEqual(listed[0]["created_by"], self.admin.username)
        self.assertFalse(listed[0]["started_by_viewer"])
        self.assertFalse(listed[0]["can_delete"])

    def test_only_the_creator_or_an_admin_can_delete_a_run(self):
        creator = self.make_editor("creator")
        lingo_admin = self.make_editor("lingo-admin", is_admin=True)
        self.client.force_login(creator)
        created_runs = [self.create_run_with_one_pair() for _attempt in range(2)]
        detail_urls = [
            reverse("api-concept-match-run-detail", args=[run["id"]])
            for run in created_runs
        ]

        self.client.force_login(self.make_editor("someone"))
        self.assertEqual(
            self.client.delete(detail_urls[0]).status_code, HTTPStatus.FORBIDDEN
        )

        for deleting_user, detail_url in zip((creator, lingo_admin), detail_urls):
            with self.subTest(deleting_user=deleting_user.username):
                self.client.force_login(deleting_user)
                self.assertTrue(self.client.get(detail_url).json()["can_delete"])
                self.assertTrue(self.client.delete(detail_url).json()["deleted"])
        self.assertFalse(ConceptMatchRun.objects.exists())

    def test_malformed_run_requests_are_bad_requests(self):
        for raw_body in ("not json", "[]"):
            with self.subTest(raw_body=raw_body):
                response = self.client.post(
                    reverse("api-concept-match-runs"),
                    data=raw_body,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        for body in (
            {"signals": ["phonetic"]},
            {"similarity_threshold": "high"},
            {"similarity_threshold": 0.05},
            {"same_language_only": "no"},
            {"scheme_ids": ["not-a-uuid"]},
            {"source_concept_ids": "not-a-list"},
            {"source_concept_set_id": "7"},
        ):
            with self.subTest(body=body):
                response = self.post_json(reverse("api-concept-match-runs"), body)
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertFalse(ConceptMatchRun.objects.exists())

    def test_malformed_review_requests_are_bad_requests(self):
        created = self.create_run_with_one_pair()
        candidates_url = reverse("api-concept-match-candidates", args=[created["id"]])
        link_url = reverse("api-concept-match-link", args=[created["id"]])
        candidate_id = self.client.get(candidates_url).json()["data"][0]["id"]

        for query in ({"page": "two"}, {"items": "0"}, {"status": "maybe"}):
            with self.subTest(query=query):
                response = self.client.get(candidates_url, query)
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        for body in (
            {"status": ConceptMatchCandidate.STATUS_DISMISSED},
            {"candidate_ids": ["1"], "status": ConceptMatchCandidate.STATUS_DISMISSED},
            {
                "candidate_ids": [candidate_id],
                "status": ConceptMatchCandidate.STATUS_MERGED,
            },
            {"all": True, "status": ConceptMatchCandidate.STATUS_LINKED},
        ):
            with self.subTest(body=body):
                response = self.client.patch(
                    candidates_url,
                    data=json.dumps(body),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertEqual(
            self.post_json(link_url, {}).status_code, HTTPStatus.BAD_REQUEST
        )

    def test_candidates_are_paged_and_can_be_dismissed(self):
        created = self.create_run_with_one_pair()
        candidates_url = reverse("api-concept-match-candidates", args=[created["id"]])

        page = self.client.get(candidates_url).json()
        self.assertEqual(page["total_results"], 1)

        dismissed = self.client.patch(
            candidates_url,
            data=json.dumps(
                {
                    "candidate_ids": [page["data"][0]["id"]],
                    "status": ConceptMatchCandidate.STATUS_DISMISSED,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(dismissed.json()["updated"], 1)
        self.assertEqual(
            self.client.get(
                reverse("api-concept-match-run-detail", args=[created["id"]])
            ).json()["pending_count"],
            0,
        )

    def test_selected_pairs_can_be_linked(self):
        self.add_uri(self.first_concept, "https://example.org/concepts/1")
        self.add_uri(self.second_concept, "https://example.org/concepts/2")
        created = self.create_run_with_one_pair()
        page = self.client.get(
            reverse("api-concept-match-candidates", args=[created["id"]])
        ).json()

        linked = self.post_json(
            reverse("api-concept-match-link", args=[created["id"]]),
            {"candidate_ids": [page["data"][0]["id"]]},
        )

        self.assertEqual(linked.json()["linked"], 1)
        self.assertEqual(
            TileModel.objects.filter(nodegroup_id=MATCH_STATUS_NODEGROUP).count(), 2
        )

    def test_another_editor_can_review_a_run(self):
        created = self.create_run_with_one_pair()
        self.client.force_login(self.make_editor("other-editor"))

        response = self.client.patch(
            reverse("api-concept-match-candidates", args=[created["id"]]),
            data=json.dumps(
                {"all": True, "status": ConceptMatchCandidate.STATUS_DISMISSED}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.json()["updated"], 1)

    def test_an_unknown_run_is_not_found(self):
        response = self.client.get(
            reverse("api-concept-match-run-detail", args=[999999])
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_an_editor_is_required(self):
        self.client.force_login(
            User.objects.create_user(username="viewer", password="x")
        )

        response = self.client.get(reverse("api-concept-match-runs"))

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)


class DetectConceptMatchesTaskTests(ConceptMatchingTestCase):
    def make_pending_run(self, signals):
        return ConceptMatchRun.objects.create(
            user=User.objects.get(username="admin"),
            status=ConceptMatchRun.STATUS_PENDING,
            parameters={"signals": list(signals)},
        )

    def test_the_task_fills_in_the_run_it_was_given(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        run = self.make_pending_run([SIGNAL_EXACT_LABEL])

        detect_concept_matches_task(
            run.pk,
            MatchScope().as_parameters(),
            [SIGNAL_EXACT_LABEL],
            {"same_language_only": True, "similarity_threshold": 0.7},
        )

        run.refresh_from_db()
        self.assertEqual(run.status, ConceptMatchRun.STATUS_COMPLETE)
        self.assertEqual(run.candidate_count, 1)

    def test_a_failure_leaves_the_run_saying_why(self):
        run = self.make_pending_run(["phonetic"])

        detect_concept_matches_task(
            run.pk,
            MatchScope().as_parameters(),
            ["phonetic"],
            {"same_language_only": True, "similarity_threshold": 0.7},
        )

        run.refresh_from_db()
        self.assertEqual(run.status, ConceptMatchRun.STATUS_FAILED)
        self.assertIn("phonetic", run.error_message)


class DetectConceptMatchesCommandTests(ConceptMatchingTestCase):
    def test_the_command_stores_a_reviewable_run(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        stdout = StringIO()

        call_command("detect_concept_matches", stdout=stdout)

        run = ConceptMatchRun.objects.get()
        self.assertEqual(run.candidate_count, 1)
        self.assertIn("1 candidate pair", stdout.getvalue())

    def test_the_command_can_search_for_similar_labels(self):
        for concept in self.concepts:
            self.clear_labels(concept)
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpet")

        call_command(
            "detect_concept_matches",
            signals=[SIGNAL_TRIGRAM],
            similarity_threshold=0.5,
            stdout=StringIO(),
        )

        run = ConceptMatchRun.objects.get()
        self.assertEqual(run.parameters["similarity_threshold"], 0.5)
        self.assertEqual(run.candidates.get().signal, SIGNAL_TRIGRAM)

    def test_an_out_of_range_threshold_is_an_actionable_error(self):
        with self.assertRaises(CommandError):
            call_command(
                "detect_concept_matches",
                signals=[SIGNAL_TRIGRAM],
                similarity_threshold=0.05,
                stdout=StringIO(),
            )
        self.assertFalse(ConceptMatchRun.objects.exists())

    def test_a_run_cancelled_from_the_interface_ends_the_command_quietly(self):
        stdout = StringIO()

        with patch(
            "arches_lingo.management.commands.detect_concept_matches.run_detection",
            return_value=None,
        ):
            call_command("detect_concept_matches", stdout=stdout)

        self.assertIn("cancelled", stdout.getvalue())

    def test_an_unknown_user_is_an_actionable_error(self):
        with self.assertRaises(CommandError):
            call_command("detect_concept_matches", user="nobody", stdout=StringIO())


class RunReportingTests(ConceptMatchingTestCase):

    def make_run(self, status, age_seconds, heartbeat_age_seconds=None):
        run = ConceptMatchRun.objects.create(
            user=User.objects.get(username="admin"),
            status=status,
            parameters={"signals": [SIGNAL_EXACT_LABEL]},
        )
        # created is auto_now_add, so it is moved afterwards rather than passed.
        ConceptMatchRun.objects.filter(pk=run.pk).update(
            created=timezone.now() - datetime.timedelta(seconds=age_seconds),
            last_progress=(
                None
                if heartbeat_age_seconds is None
                else timezone.now() - datetime.timedelta(seconds=heartbeat_age_seconds)
            ),
        )
        run.refresh_from_db()
        return run

    def test_a_run_that_stopped_reporting_is_failed(self):
        run = self.make_run(
            ConceptMatchRun.STATUS_RUNNING,
            age_seconds=STALE_RUN_SECONDS * 3,
            heartbeat_age_seconds=STALE_RUN_SECONDS * 2,
        )

        self.assertEqual(reap_stale_runs(), 1)

        run.refresh_from_db()
        self.assertEqual(run.status, ConceptMatchRun.STATUS_FAILED)
        self.assertIn("interrupted", run.error_message)
        self.assertIsNotNone(run.finished)

    def test_a_run_still_reporting_is_left_alone(self):
        run = self.make_run(
            ConceptMatchRun.STATUS_RUNNING,
            age_seconds=STALE_RUN_SECONDS * 10,
            heartbeat_age_seconds=1,
        )

        self.assertEqual(reap_stale_runs(), 0)

        run.refresh_from_db()
        self.assertEqual(run.status, ConceptMatchRun.STATUS_RUNNING)

    def test_a_run_that_never_reported_falls_back_to_when_it_started(self):
        fresh = self.make_run(ConceptMatchRun.STATUS_PENDING, age_seconds=1)
        stranded = self.make_run(
            ConceptMatchRun.STATUS_PENDING, age_seconds=STALE_RUN_SECONDS * 2
        )

        self.assertEqual(reap_stale_runs(), 1)

        fresh.refresh_from_db()
        stranded.refresh_from_db()
        self.assertEqual(fresh.status, ConceptMatchRun.STATUS_PENDING)
        self.assertEqual(stranded.status, ConceptMatchRun.STATUS_FAILED)

    def test_a_finished_run_is_never_reopened(self):
        run = self.make_run(
            ConceptMatchRun.STATUS_COMPLETE, age_seconds=STALE_RUN_SECONDS * 10
        )

        self.assertEqual(reap_stale_runs(), 0)

        run.refresh_from_db()
        self.assertEqual(run.status, ConceptMatchRun.STATUS_COMPLETE)

    def test_progress_is_recorded_as_each_query_is_stored(self):
        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")
        run = ConceptMatchRun.objects.create(
            user=None,
            status=ConceptMatchRun.STATUS_RUNNING,
            parameters={"signals": [SIGNAL_EXACT_LABEL]},
        )
        recorded_progress = []

        def record_progress(message):
            recorded_progress.append(
                ConceptMatchRun.objects.values_list(
                    "candidate_count", "last_progress"
                ).get(pk=run.pk)
            )

        run_detection(
            MatchScope(),
            signals=(SIGNAL_SHARED_IDENTIFIER, SIGNAL_EXACT_LABEL),
            run=run,
            log=record_progress,
        )

        after_uris, after_labels = recorded_progress[:2]
        self.assertEqual(after_uris[0], 0)
        self.assertEqual(after_labels[0], 1)
        self.assertGreaterEqual(after_labels[1], after_uris[1])

    def test_a_run_reports_from_a_thread_of_its_own(self):
        run = ConceptMatchRun.objects.create(
            user=None, status=ConceptMatchRun.STATUS_RUNNING, parameters={}
        )
        heartbeat_thread_name = f"lingo-match-run-{run.pk}"
        heartbeat_alive_during_work = []

        def running_thread_names():
            return [thread.name for thread in threading.enumerate()]

        def note_heartbeat(message):
            heartbeat_alive_during_work.append(
                heartbeat_thread_name in running_thread_names()
            )

        run_detection(
            MatchScope(), signals=(SIGNAL_EXACT_LABEL,), run=run, log=note_heartbeat
        )

        self.assertTrue(heartbeat_alive_during_work[0])
        self.assertNotIn(heartbeat_thread_name, running_thread_names())

    def test_timestamps_carry_their_offset(self):
        run = ConceptMatchRun.objects.create(
            user=None,
            status=ConceptMatchRun.STATUS_COMPLETE,
            finished=timezone.now(),
            parameters={},
        )

        serialized = serialize_run(run)

        for timestamp in (serialized["created"], serialized["finished"]):
            self.assertIsNotNone(datetime.datetime.fromisoformat(timestamp).tzinfo)

    def test_elapsed_time_is_measured_on_the_server(self):
        run = ConceptMatchRun.objects.create(
            user=User.objects.get(username="admin"),
            status=ConceptMatchRun.STATUS_RUNNING,
            parameters={"signals": [SIGNAL_EXACT_LABEL]},
        )
        ConceptMatchRun.objects.filter(pk=run.pk).update(
            created=timezone.now() - datetime.timedelta(seconds=90)
        )
        run.refresh_from_db()

        self.assertAlmostEqual(serialize_run(run)["elapsed_seconds"], 90, delta=5)

    def test_a_finished_run_stops_counting(self):
        run = ConceptMatchRun.objects.create(
            user=User.objects.get(username="admin"),
            status=ConceptMatchRun.STATUS_COMPLETE,
            parameters={"signals": [SIGNAL_EXACT_LABEL]},
        )
        ConceptMatchRun.objects.filter(pk=run.pk).update(
            created=timezone.now() - datetime.timedelta(seconds=300),
            finished=timezone.now() - datetime.timedelta(seconds=240),
        )
        run.refresh_from_db()

        self.assertEqual(serialize_run(run)["elapsed_seconds"], 60)


class RunDisposalTests(ConceptMatchingTestCase):
    def make_run_with_candidates(self, statuses):
        run = ConceptMatchRun.objects.create(
            user=User.objects.get(username="admin"),
            status=ConceptMatchRun.STATUS_COMPLETE,
            parameters={"signals": [SIGNAL_EXACT_LABEL]},
        )
        for index, status in enumerate(statuses):
            ConceptMatchCandidate.objects.create(
                run=run,
                concept_a_id=uuid.uuid4(),
                concept_b_id=uuid.uuid4(),
                score=1.0,
                signal=SIGNAL_EXACT_LABEL,
                evidence=f"pair {index}",
                status=status,
            )
        return run

    def test_every_pending_pair_is_dismissed_at_once(self):
        run = self.make_run_with_candidates([ConceptMatchCandidate.STATUS_PENDING] * 3)

        result = set_status_for_all(
            run,
            ConceptMatchCandidate.STATUS_DISMISSED,
            User.objects.get(username="admin"),
        )

        self.assertEqual(result["updated"], 3)
        self.assertEqual(
            run.candidates.filter(
                status=ConceptMatchCandidate.STATUS_DISMISSED
            ).count(),
            3,
        )

    def test_pairs_already_decided_are_left_as_they_are(self):
        run = self.make_run_with_candidates(
            [
                ConceptMatchCandidate.STATUS_PENDING,
                ConceptMatchCandidate.STATUS_LINKED,
                ConceptMatchCandidate.STATUS_MERGED,
            ]
        )

        result = set_status_for_all(
            run,
            ConceptMatchCandidate.STATUS_DISMISSED,
            User.objects.get(username="admin"),
        )

        self.assertEqual(result["updated"], 1)
        self.assertEqual(
            run.candidates.filter(status=ConceptMatchCandidate.STATUS_LINKED).count(),
            1,
        )
        self.assertEqual(
            run.candidates.filter(status=ConceptMatchCandidate.STATUS_MERGED).count(),
            1,
        )

    def test_every_dismissed_pair_is_restored_at_once(self):
        run = self.make_run_with_candidates(
            [
                ConceptMatchCandidate.STATUS_DISMISSED,
                ConceptMatchCandidate.STATUS_DISMISSED,
                ConceptMatchCandidate.STATUS_LINKED,
            ]
        )

        result = set_status_for_all(
            run,
            ConceptMatchCandidate.STATUS_PENDING,
            User.objects.get(username="admin"),
        )

        self.assertEqual(result["updated"], 2)
        self.assertEqual(result["skipped"], {})
        self.assertEqual(
            run.candidates.filter(status=ConceptMatchCandidate.STATUS_LINKED).count(),
            1,
        )

    def test_a_pair_decided_since_it_was_dismissed_stays_dismissed(self):
        concept_a_id, concept_b_id = self.expected_pair(
            self.first_concept, self.second_concept
        )
        run = self.make_run_with_candidates([])
        candidate = ConceptMatchCandidate.objects.create(
            run=run,
            concept_a_id=concept_a_id,
            concept_b_id=concept_b_id,
            score=1.0,
            signal=SIGNAL_EXACT_LABEL,
            status=ConceptMatchCandidate.STATUS_DISMISSED,
        )
        ConceptMerge.objects.create(
            survivor_concept_id=self.first_concept.pk,
            absorbed_concept_id=self.second_concept.pk,
        )

        for restore in (
            lambda: set_status_for_all(run, ConceptMatchCandidate.STATUS_PENDING, None),
            lambda: set_candidate_status(
                run, [candidate.pk], ConceptMatchCandidate.STATUS_PENDING, None
            ),
        ):
            with self.subTest(restore=restore):
                result = restore()
                self.assertEqual(result["updated"], 0)
                self.assertEqual(result["skipped"], {"already_decided": 1})
                candidate.refresh_from_db()
                self.assertEqual(
                    candidate.status, ConceptMatchCandidate.STATUS_DISMISSED
                )

    def test_another_runs_pairs_are_untouched(self):
        run = self.make_run_with_candidates([ConceptMatchCandidate.STATUS_PENDING])
        other_run = self.make_run_with_candidates(
            [ConceptMatchCandidate.STATUS_PENDING]
        )

        set_status_for_all(
            run,
            ConceptMatchCandidate.STATUS_DISMISSED,
            User.objects.get(username="admin"),
        )

        self.assertEqual(
            other_run.candidates.get().status, ConceptMatchCandidate.STATUS_PENDING
        )

    def test_a_run_deleted_while_working_stops_without_failing(self):
        run = ConceptMatchRun.objects.create(
            user=User.objects.get(username="admin"),
            status=ConceptMatchRun.STATUS_RUNNING,
            parameters={"signals": [SIGNAL_EXACT_LABEL]},
        )

        self.add_label(self.first_concept, "trumpets")
        self.add_label(self.second_concept, "trumpets")

        def delete_after_the_first_query(message):
            ConceptMatchRun.objects.filter(pk=run.pk).delete()

        result = run_detection(
            MatchScope(),
            signals=(SIGNAL_SHARED_IDENTIFIER, SIGNAL_EXACT_LABEL),
            run=run,
            log=delete_after_the_first_query,
        )

        self.assertIsNone(result)
        self.assertFalse(ConceptMatchRun.objects.filter(pk=run.pk).exists())
        self.assertEqual(ConceptMatchCandidate.objects.filter(run_id=run.pk).count(), 0)

    def test_a_query_failing_because_its_run_was_deleted_is_a_cancellation(self):
        run = ConceptMatchRun.objects.create(
            user=None, status=ConceptMatchRun.STATUS_RUNNING, parameters={}
        )

        def delete_run_and_fail(*args, **kwargs):
            ConceptMatchRun.objects.filter(pk=run.pk).delete()
            raise IntegrityError("violates foreign key constraint")

        with patch(
            "arches_lingo.utils.concept_matching._store_pairs",
            side_effect=delete_run_and_fail,
        ):
            result = run_detection(MatchScope(), run=run, log=lambda message: None)

        self.assertIsNone(result)

    def test_a_delete_racing_a_committing_query_is_retried(self):
        run = ConceptMatchRun.objects.create(
            user=None, status=ConceptMatchRun.STATUS_RUNNING, parameters={}
        )

        with patch.object(
            ConceptMatchRun, "delete", side_effect=[IntegrityError, None]
        ) as mock_delete:
            delete_run(run, None, user_is_lingo_admin=True)

        self.assertEqual(mock_delete.call_count, 2)
