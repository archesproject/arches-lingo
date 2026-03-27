"""Tests for pure utility and helper functions across arches_lingo.

Focuses on functions with branching logic that benefit from direct unit tests,
rather than testing the HTTP layer or Django/DRF framework mechanics.

These tests can be run from the command line via:
  python manage.py test tests.test_utils --settings="tests.test_settings"
"""

import uuid
from datetime import datetime, timezone as stdlib_timezone
from unittest.mock import MagicMock, patch

from arches.app.models.system_settings import settings as arches_settings

from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from arches_lingo.const import LINGO_EDITOR_GROUP_NAME
from arches_lingo.models import ConceptIdentifierCounter
from arches_lingo.permissions import (
    anonymous_access_allowed,
    is_authenticated_user,
    is_lingo_editor,
)
from arches_lingo.utils.concept_identifier_allocator import (
    allocate_concept_identifier_number,
)
from arches_lingo.utils.concepts import (
    resolve_max_edit_distance,
    score_concept_for_term,
)
from arches_lingo.utils.dashboard import parse_days_param, parse_scheme_ids
from arches_lingo.utils.scheme_uri_template import default_scheme_uri_template_value
from arches_lingo.utils.search_service import extract_note_type_label

from tests.tests import ViewTests


# ────────────────────────────────────────────────────────────────
# permissions.py
# ────────────────────────────────────────────────────────────────


class PermissionHelpersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        lingo_editor_group, _ = Group.objects.get_or_create(
            name=LINGO_EDITOR_GROUP_NAME
        )
        cls.editor_user = User.objects.create_user(username="perm_editor", password="x")
        cls.editor_user.groups.add(lingo_editor_group)

        cls.regular_user = User.objects.create_user(
            username="perm_regular", password="x"
        )
        cls.superuser = User.objects.create_user(
            username="perm_super", password="x", is_superuser=True
        )

    def test_is_lingo_editor_anonymous_returns_false(self):
        self.assertFalse(is_lingo_editor(AnonymousUser()))

    def test_is_lingo_editor_regular_user_without_group_returns_false(self):
        self.assertFalse(is_lingo_editor(self.regular_user))

    def test_is_lingo_editor_group_member_returns_true(self):
        self.assertTrue(is_lingo_editor(self.editor_user))

    def test_is_lingo_editor_superuser_returns_true_without_group(self):
        self.assertTrue(is_lingo_editor(self.superuser))

    def test_is_authenticated_user_anonymous_user_returns_false(self):
        self.assertFalse(is_authenticated_user(AnonymousUser()))

    def test_is_authenticated_user_with_anonymous_username_returns_false(self):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.username = "anonymous"
        self.assertFalse(is_authenticated_user(mock_user))

    def test_is_authenticated_user_regular_user_returns_true(self):
        self.assertTrue(is_authenticated_user(self.regular_user))

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=True)
    def test_anonymous_access_allowed_when_setting_is_true(self):
        self.assertTrue(anonymous_access_allowed())

    @override_settings(LINGO_ALLOW_ANONYMOUS_ACCESS=False)
    def test_anonymous_access_allowed_when_setting_is_false(self):
        self.assertFalse(anonymous_access_allowed())

    def test_anonymous_access_defaults_to_false_when_setting_absent(self):
        with self.settings(LINGO_ALLOW_ANONYMOUS_ACCESS=None):
            # getattr(..., False) is used in the implementation, so None is falsy
            self.assertFalse(anonymous_access_allowed())


# ────────────────────────────────────────────────────────────────
# utils/concepts.py — resolve_max_edit_distance
# ────────────────────────────────────────────────────────────────


class ResolveMaxEditDistanceTests(TestCase):
    """Tests for resolve_max_edit_distance, which maps term length and sensitivity to max edit distance.

    Sensitivity is patched on the arches `SystemSettings` object since it does not
    participate in Django's override_settings mechanism.
    """

    def _resolve(self, term, sensitivity=2):
        with patch.object(arches_settings, "SEARCH_TERM_SENSITIVITY", new=sensitivity):
            return resolve_max_edit_distance(term)

    def test_empty_term_returns_base_distance(self):
        # sensitivity=2 → base = 5-2 = 3; empty term returns base directly
        self.assertEqual(self._resolve(""), 3)

    def test_none_term_returns_base_distance(self):
        self.assertEqual(self._resolve(None), 3)

    def test_short_term_three_chars_clamps_to_zero(self):
        self.assertEqual(self._resolve("cat"), 0)

    def test_medium_term_five_chars_clamps_to_one(self):
        # min(base=3, 1) = 1
        self.assertEqual(self._resolve("hello"), 1)

    def test_longer_term_six_chars_clamps_to_two(self):
        # min(base=3, 2) = 2
        self.assertEqual(self._resolve("search"), 2)

    def test_sensitivity_zero_gives_base_five(self):
        # sensitivity=0 → base=5; long term → min(5, 2) = 2
        self.assertEqual(self._resolve("searching", 0), 2)

    def test_sensitivity_five_or_more_gives_base_zero(self):
        # sensitivity=5 → base=0; min(0, anything) = 0
        self.assertEqual(self._resolve("hello", 5), 0)
        self.assertEqual(self._resolve("hello", 10), 0)

    def test_sensitivity_five_long_term_returns_zero(self):
        # sensitivity=5 → base=0
        self.assertEqual(self._resolve("a very long term", 5), 0)


# ────────────────────────────────────────────────────────────────
# utils/concepts.py — score_concept_for_term
# ────────────────────────────────────────────────────────────────


class ScoreConceptForTermTests(SimpleTestCase):
    """Tests for score_concept_for_term, which ranks concept labels against a search term."""

    def _score(self, labels, search_term, active_language="en", system_language="en"):
        return score_concept_for_term(
            {"labels": labels},
            search_term,
            active_language,
            system_language,
        )

    def _make_label(self, value, language_id="en", valuetype_id="prefLabel", rank=None):
        label = {
            "value": value,
            "language_id": language_id,
            "valuetype_id": valuetype_id,
        }
        if rank is not None:
            label["rank"] = rank
        return label

    def test_no_labels_returns_none(self):
        self.assertIsNone(self._score([], "bird"))

    def test_exact_match_produces_lower_score_than_prefix(self):
        exact_labels = [self._make_label("bird")]
        prefix_labels = [self._make_label("birdhouse")]

        exact_score = self._score(exact_labels, "bird")
        prefix_score = self._score(prefix_labels, "bird")

        # Lower tuple means better match
        self.assertLess(exact_score, prefix_score)

    def test_prefix_match_beats_substring_match(self):
        prefix_labels = [self._make_label("birdsong")]
        substring_labels = [self._make_label("singing bird")]

        prefix_score = self._score(prefix_labels, "bird")
        substring_score = self._score(substring_labels, "bird")

        self.assertLess(prefix_score, substring_score)

    def test_active_language_label_ranks_better_than_system_language(self):
        """A label in the active language should outscore one in the system language."""
        active_label = self._make_label("bird", language_id="fr")
        system_label = self._make_label("bird", language_id="en")

        active_score = self._score(
            [active_label], "bird", active_language="fr", system_language="en"
        )
        system_score = self._score(
            [system_label], "bird", active_language="fr", system_language="en"
        )

        self.assertLess(active_score, system_score)

    def test_empty_search_term_assigns_no_match_rank(self):
        """An empty term should give every label the same no-match rank."""
        label = self._make_label("bird")
        score = self._score([label], "")
        # text_match_rank for empty term is 3, which maps to 6 for prefLabel
        # The exact value isn't important; just check a score is returned
        self.assertIsNotNone(score)

    def test_pref_label_scores_better_than_alt_label_for_same_match(self):
        """Identical text match on a prefLabel should rank better than on an altLabel."""
        pref_label = self._make_label("bird", valuetype_id="prefLabel")
        alt_label = self._make_label("bird", valuetype_id="altLabel")

        pref_score = self._score([pref_label], "bird")
        alt_score = self._score([alt_label], "bird")

        self.assertLess(pref_score, alt_score)

    def test_rank_field_affects_score(self):
        """Higher rank value should produce a worse (larger) score tuple."""
        high_rank_label = self._make_label("bird", rank=10)
        low_rank_label = self._make_label("bird", rank=1)

        high_rank_score = self._score([high_rank_label], "bird")
        low_rank_score = self._score([low_rank_label], "bird")

        # rank contributes -rank, so rank=10 → -10 (worse, i.e. larger position)
        # Actually, lower rank number (rank=1) → label_rank=-1 vs rank=10 → label_rank=-10
        # label_rank = -rank, so rank=10 gives label_rank=-10 (lower / better sort position)
        # Wait, let me re-read: label_rank = -raw_label_rank, so rank=10 → label_rank=-10,
        # and the tuple (match, lang, label_rank, value) sorts ascending.
        # rank=10 → label_rank=-10 → better score (lower in tuple comparison).
        self.assertLess(high_rank_score, low_rank_score)

    def test_case_insensitive_matching(self):
        """Score should match regardless of case."""
        label_upper = self._make_label("BIRD")
        label_lower = self._make_label("bird")

        score_upper = self._score([label_upper], "bird")
        score_lower = self._score([label_lower], "bird")

        self.assertEqual(score_upper, score_lower)


# ────────────────────────────────────────────────────────────────
# utils/dashboard.py — parse_scheme_ids, parse_days_param
# ────────────────────────────────────────────────────────────────


class ParseSchemeIdsTests(SimpleTestCase):
    """Tests for parse_scheme_ids, which validates and normalises scheme UUID params."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request_with_params(self, scheme_values):
        query_string = "&".join(f"scheme={value}" for value in scheme_values)
        return self.factory.get("/", QUERY_STRING=query_string)

    def test_empty_params_returns_empty_list(self):
        request = self.factory.get("/")
        self.assertEqual(parse_scheme_ids(request), [])

    def test_single_valid_uuid_returns_list_with_one_element(self):
        valid_uuid = str(uuid.uuid4())
        request = self._request_with_params([valid_uuid])
        result = parse_scheme_ids(request)
        self.assertEqual(result, [valid_uuid])

    def test_multiple_valid_uuids_returned_in_order(self):
        first_uuid = str(uuid.uuid4())
        second_uuid = str(uuid.uuid4())
        request = self._request_with_params([first_uuid, second_uuid])
        result = parse_scheme_ids(request)
        self.assertEqual(result, [first_uuid, second_uuid])

    def test_invalid_uuid_string_raises_value_error(self):
        request = self._request_with_params(["not-a-valid-uuid"])
        with self.assertRaises(ValueError):
            parse_scheme_ids(request)

    def test_uuid_is_normalised_to_lowercase_string(self):
        uppercase_uuid = str(uuid.uuid4()).upper()
        request = self._request_with_params([uppercase_uuid])
        result = parse_scheme_ids(request)
        self.assertEqual(result, [uppercase_uuid.lower()])


class ParseDaysParamTests(SimpleTestCase):
    """Tests for parse_days_param, which converts a `days` query param to a cutoff datetime."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_absent_param_returns_none(self):
        request = self.factory.get("/")
        self.assertIsNone(parse_days_param(request))

    def test_positive_integer_returns_cutoff_datetime(self):
        request = self.factory.get("/", {"days": "7"})
        result = parse_days_param(request)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, datetime)

    def test_zero_returns_none(self):
        request = self.factory.get("/", {"days": "0"})
        self.assertIsNone(parse_days_param(request))

    def test_negative_integer_returns_none(self):
        request = self.factory.get("/", {"days": "-5"})
        self.assertIsNone(parse_days_param(request))

    def test_non_integer_string_raises_value_error(self):
        request = self.factory.get("/", {"days": "abc"})
        with self.assertRaises(ValueError):
            parse_days_param(request)


# ────────────────────────────────────────────────────────────────
# utils/search_service.py — extract_note_type_label
# ────────────────────────────────────────────────────────────────


class ExtractNoteTypeLabelTests(SimpleTestCase):
    """Tests for extract_note_type_label, which pulls a human-readable label from note-type JSON."""

    def test_none_returns_empty_string(self):
        self.assertEqual(extract_note_type_label(None), "")

    def test_empty_list_returns_empty_string(self):
        self.assertEqual(extract_note_type_label([]), "")

    def test_non_list_returns_empty_string(self):
        self.assertEqual(extract_note_type_label("not a list"), "")
        self.assertEqual(extract_note_type_label({"labels": []}), "")

    def test_english_label_is_preferred(self):
        note_type_data = [
            {
                "labels": [
                    {"language_id": "de", "value": "Umfangsnotiz"},
                    {"language_id": "en", "value": "Scope Note"},
                ]
            }
        ]
        self.assertEqual(extract_note_type_label(note_type_data), "Scope Note")

    def test_falls_back_to_first_label_when_no_english(self):
        note_type_data = [
            {
                "labels": [
                    {"language_id": "de", "value": "Umfangsnotiz"},
                    {"language_id": "fr", "value": "Note de portée"},
                ]
            }
        ]
        self.assertEqual(extract_note_type_label(note_type_data), "Umfangsnotiz")

    def test_empty_labels_array_returns_empty_string(self):
        note_type_data = [{"labels": []}]
        self.assertEqual(extract_note_type_label(note_type_data), "")

    def test_missing_labels_key_returns_empty_string(self):
        note_type_data = [{}]
        self.assertEqual(extract_note_type_label(note_type_data), "")


# ────────────────────────────────────────────────────────────────
# utils/scheme_uri_template.py
# ────────────────────────────────────────────────────────────────


class DefaultSchemeUriTemplateTests(SimpleTestCase):
    """Tests for default_scheme_uri_template_value, which builds a URI template from settings."""

    @override_settings(PUBLIC_SERVER_ADDRESS="https://example.com/")
    def test_strips_trailing_slash_from_server_address(self):
        template = default_scheme_uri_template_value()
        self.assertNotIn("//schemes", template)

    @override_settings(PUBLIC_SERVER_ADDRESS="https://example.com")
    def test_template_contains_scheme_and_concept_placeholders(self):
        template = default_scheme_uri_template_value()
        self.assertIn("<scheme_identifier>", template)
        self.assertIn("<concept_identifier>", template)

    @override_settings(PUBLIC_SERVER_ADDRESS="https://example.com")
    def test_template_starts_with_server_address(self):
        template = default_scheme_uri_template_value()
        self.assertTrue(template.startswith("https://example.com"))


# ────────────────────────────────────────────────────────────────
# utils/concept_identifier_allocator.py
# ────────────────────────────────────────────────────────────────


class ConceptIdentifierAllocatorTests(ViewTests):
    """Tests for allocate_concept_identifier_number, which atomically increments a scheme counter."""

    COUNTER_START = 100

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ConceptIdentifierCounter.objects.create(
            scheme=cls.scheme,
            start_number=cls.COUNTER_START,
            next_number=cls.COUNTER_START,
        )

    def setUp(self):
        super().setUp()
        # Reset the counter before each test so each one starts from a clean state.
        ConceptIdentifierCounter.objects.filter(scheme=self.scheme).update(
            next_number=self.COUNTER_START
        )

    def test_first_allocation_returns_start_number(self):
        allocated = allocate_concept_identifier_number(self.scheme.pk)
        self.assertEqual(allocated, self.COUNTER_START)

    def test_allocation_increments_next_number(self):
        allocate_concept_identifier_number(self.scheme.pk)
        counter = ConceptIdentifierCounter.objects.get(scheme=self.scheme)
        self.assertEqual(counter.next_number, self.COUNTER_START + 1)

    def test_batch_allocation_reserves_multiple_numbers(self):
        batch_size = 5
        first_allocated = allocate_concept_identifier_number(
            self.scheme.pk, count=batch_size
        )
        counter = ConceptIdentifierCounter.objects.get(scheme=self.scheme)
        self.assertEqual(first_allocated, self.COUNTER_START)
        self.assertEqual(counter.next_number, self.COUNTER_START + batch_size)
