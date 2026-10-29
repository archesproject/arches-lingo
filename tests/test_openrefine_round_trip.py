import csv
import datetime
import io
import json
import uuid
from contextlib import nullcontext
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from arches.app.models.models import EditLog, ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_NODEGROUP,
    EXACT_MATCH_LIST_ITEM_ID,
    LINGO_ADMIN_GROUP_NAME,
    LINGO_EDITOR_GROUP_NAME,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.models import ConceptSet, ConceptSetMember, MatchLinkImport
from arches_lingo.tasks import apply_match_link_import_task
from arches_lingo.utils.concept_lifecycle import (
    DRAFT_STATE_ID,
    LOCKED_STATE_ID,
    PUBLISHED_STATE_ID,
    RETIRED_STATE_ID,
)
from arches_lingo.utils.concept_merge.tiles import get_list_item_tile_value
from arches_lingo.utils.openrefine_round_trip.match_link_import import (
    apply_match_link_import,
    parse_match_link_csv,
)
from tests.tests import SchemeWithConceptsTestCase

CELERY_CHECK = (
    "arches_lingo.utils.openrefine_round_trip.match_link_import_service"
    ".task_management.check_if_celery_available"
)
NOTIFY_COMPLETION = (
    "arches_lingo.utils.openrefine_round_trip.match_link_import.notify_completion"
)


def set_lifecycle_state(resource, state_id):
    ResourceInstance.objects.filter(pk=resource.pk).update(
        resource_instance_lifecycle_state_id=state_id
    )


def csv_upload(rows, header=("concept_id", "match_uri", "match_type")):
    text = io.StringIO()
    writer = csv.writer(text)
    writer.writerow(header)
    writer.writerows(rows)
    return SimpleUploadedFile(
        "matches.csv", text.getvalue().encode("utf-8"), content_type="text/csv"
    )


class OpenRefineRoundTripTestCase(SchemeWithConceptsTestCase):
    """Concepts 1–5 are drafts (editable) unless a test says otherwise."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.editor = User.objects.create_user(username="round-trip-editor")
        cls.editor.groups.add(Group.objects.get(name=LINGO_EDITOR_GROUP_NAME))
        cls.other_editor = User.objects.create_user(username="other-editor")
        cls.other_editor.groups.add(Group.objects.get(name=LINGO_EDITOR_GROUP_NAME))
        cls.other_editor.groups.add(Group.objects.get(name=LINGO_ADMIN_GROUP_NAME))
        set_lifecycle_state(cls.scheme, DRAFT_STATE_ID)
        for concept in cls.concepts:
            set_lifecycle_state(concept, DRAFT_STATE_ID)
        TileModel.objects.create(
            resourceinstance=cls.concepts[0],
            nodegroup_id=URI_NODEGROUP,
            data={URI_CONTENT_NODE: "https://lingo.example/c1"},
        )

    def setUp(self):
        self.client.force_login(self.editor)

    def add_exact_match(self, concept, uri):
        TileModel.objects.create(
            resourceinstance=concept,
            nodegroup_id=MATCH_STATUS_NODEGROUP,
            data={
                MATCH_STATUS_RELATION_NODE: [
                    get_list_item_tile_value(EXACT_MATCH_LIST_ITEM_ID)
                ],
                MATCH_STATUS_COMPARATE_NODE: uri,
            },
        )


class ReconciliationWorksheetTests(OpenRefineRoundTripTestCase):
    def export(self, scope, language="en"):
        response = self.client.post(
            reverse("api-lingo-reconciliation-worksheet"),
            json.dumps({"scope": scope, "language": language}),
            content_type="application/json",
        )
        return response

    def rows_of(self, response):
        return list(csv.DictReader(io.StringIO(response.content.decode())))

    @patch(
        "arches_lingo.utils.openrefine_round_trip.worksheet_export"
        ".WORKSHEET_BATCH_SIZE",
        2,
    )
    def test_scheme_worksheet_describes_each_non_retired_concept(self):
        set_lifecycle_state(self.concepts[1], PUBLISHED_STATE_ID)
        set_lifecycle_state(self.concepts[4], RETIRED_STATE_ID)
        self.add_exact_match(self.concepts[2], "http://example.org/third")

        response = self.export({"scheme_id": str(self.scheme.pk)})
        rows_by_label = {row["pref_label"]: row for row in self.rows_of(response)}

        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(
            set(rows_by_label), {"Concept 1", "Concept 2", "Concept 3", "Concept 4"}
        )
        self.assertEqual(rows_by_label["Concept 1"]["uri"], "https://lingo.example/c1")
        self.assertEqual(
            rows_by_label["Concept 3"]["broader_labels"], "Concept 1|Concept 2"
        )
        self.assertEqual(
            rows_by_label["Concept 3"]["exact_matches"], "http://example.org/third"
        )
        self.assertEqual(rows_by_label["Concept 3"]["scheme"], "Test Scheme")
        self.assertEqual(rows_by_label["Concept 3"]["lifecycle_state"], "Draft")
        self.assertEqual(rows_by_label["Concept 3"]["editable"], "true")
        self.assertEqual(rows_by_label["Concept 2"]["editable"], "false")
        self.assertEqual(rows_by_label["Concept 3"]["match_uri"], "")
        self.assertEqual(rows_by_label["Concept 3"]["match_type"], "")

    def test_concept_set_and_search_scopes(self):
        concept_set = ConceptSet.objects.create(user=self.editor, name="Set")
        ConceptSetMember.objects.create(
            concept_set=concept_set, concept_id=self.concepts[3].pk
        )

        set_rows = self.rows_of(self.export({"concept_set_id": concept_set.pk}))
        search_rows = self.rows_of(
            self.export(
                {
                    "query": {
                        "operator": "and",
                        "conditions": [{"facet": "label", "value": "Concept"}],
                    }
                }
            )
        )

        self.assertEqual([row["pref_label"] for row in set_rows], ["Concept 4"])
        self.assertEqual(len(search_rows), 5)

        self.client.force_login(self.other_editor)
        self.assertEqual(
            self.export({"concept_set_id": concept_set.pk}).status_code, 400
        )

    def test_scope_must_be_exactly_one_kind(self):
        for scope in [
            {},
            {"scheme_id": str(self.scheme.pk), "query": {}},
            {"query": "not an object"},
            {"query": {}},
            {"query": {"operator": "and", "conditions": []}},
            {"scheme_id": "not-a-uuid"},
            {"concept_set_id": {"not": "an id"}},
        ]:
            with self.subTest(scope=scope):
                self.assertEqual(self.export(scope).status_code, 400)
        self.assertEqual(
            self.client.post(
                reverse("api-lingo-reconciliation-worksheet"),
                "[]",
                content_type="application/json",
            ).status_code,
            400,
        )

    @patch(
        "arches_lingo.utils.openrefine_round_trip.worksheet_export"
        ".MAX_WORKSHEET_CONCEPTS",
        4,
    )
    def test_scopes_over_the_limit_are_refused(self):
        response = self.export({"scheme_id": str(self.scheme.pk)})

        self.assertEqual(response.status_code, 400)
        self.assertIn("at most 4 concepts", response.json()["message"])

    def test_free_text_that_would_run_as_a_formula_is_neutralized(self):
        for concept, label in [
            (self.concepts[0], '=HYPERLINK("http://evil.example")'),
            (self.concepts[1], "@SUM(1)"),
            (self.concepts[2], "-ism"),
        ]:
            label_tile = TileModel.objects.get(
                resourceinstance=concept, nodegroup_id=CONCEPT_NAME_NODEGROUP
            )
            label_tile.data[CONCEPT_NAME_CONTENT_NODE] = label
            label_tile.save()
        self.add_exact_match(self.concepts[3], "=1+1")

        rows = self.rows_of(self.export({"scheme_id": str(self.scheme.pk)}))

        self.assertTrue(
            {'\'=HYPERLINK("http://evil.example")', "'@SUM(1)", "-ism"}
            <= {row["pref_label"] for row in rows}
        )
        self.assertIn("'=1+1", {row["exact_matches"] for row in rows})

    def test_unknown_languages_fall_back_to_the_active_one(self):
        for language in ["zz-not-a-language", {"not": "a string"}]:
            with self.subTest(language=language):
                response = self.export(
                    {"scheme_id": str(self.scheme.pk)}, language=language
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    "Concept 1", {row["pref_label"] for row in self.rows_of(response)}
                )


class MatchLinkImportTests(OpenRefineRoundTripTestCase):
    def preview(self, upload):
        return self.client.post(
            reverse("api-lingo-match-link-import-preview"), {"file": upload}
        )

    def outcomes_of(self, preview_response):
        return {
            row["row_number"]: row["outcome"] for row in preview_response.json()["rows"]
        }

    def test_every_row_gets_an_outcome(self):
        set_lifecycle_state(self.concepts[1], PUBLISHED_STATE_ID)
        self.add_exact_match(self.concepts[3], "http://example.org/already")
        concept_ids = [str(concept.pk) for concept in self.concepts]
        upload = csv_upload(
            [
                [concept_ids[2], "http://example.org/new", ""],
                [concept_ids[2], "http://example.org/new", "exactMatch"],
                ["not-a-uuid", "http://example.org/x", ""],
                [concept_ids[2], "http://example.org/x", "broadMatch"],
                [concept_ids[2], "ftp://example.org/x", ""],
                [concept_ids[0], "https://lingo.example/c1", ""],
                [concept_ids[1], "http://example.org/x", ""],
                [concept_ids[3], "http://example.org/already", ""],
                [concept_ids[4], "https://lingo.example/c1", "closeMatch"],
                [concept_ids[3], "http://example.org/already", "relatedMatch"],
                [concept_ids[2], "http://example.org/new", "closeMatch"],
            ]
        )

        preview = self.preview(upload)
        rows = preview.json()["rows"]

        self.assertEqual(
            self.outcomes_of(preview),
            {
                2: "add",
                3: "duplicate_in_file",
                4: "unknown_concept",
                5: "invalid_match_type",
                6: "invalid_uri",
                7: "self_match",
                8: "not_editable",
                9: "already_linked",
                10: "add",
                11: "conflicting_link",
                12: "conflicting_link",
            },
        )
        self.assertEqual(preview.json()["counts_by_outcome"]["add"], 2)
        self.assertEqual(rows[0]["concept_label"], "Concept 3")
        # Row 10 links to Concept 1's own URI: added one way, and flagged.
        self.assertTrue(rows[8]["is_internal_concept"])
        self.assertFalse(rows[0]["is_internal_concept"])

    def test_cells_are_split_aliased_and_compared_loosely(self):
        self.add_exact_match(self.concepts[3], "http://example.org/already")
        concept_ids = [str(concept.pk) for concept in self.concepts]
        upload = csv_upload(
            [
                [
                    concept_ids[2],
                    "http://example.org/a|https://example.org/b/",
                    "SKOS:closeMatch",
                ],
                [
                    concept_ids[2],
                    "https://EXAMPLE.org/a/",
                    "http://www.w3.org/2004/02/skos/core#closeMatch",
                ],
                [concept_ids[3], "https://example.org/already/", "exactmatch"],
                [concept_ids[4], "http://lingo.example/c1/", ""],
            ]
        )

        rows = self.preview(upload).json()["rows"]

        self.assertEqual(
            [(row["row_number"], row["match_type"], row["outcome"]) for row in rows],
            [
                (2, "closeMatch", "add"),
                (2, "closeMatch", "add"),
                (3, "closeMatch", "duplicate_in_file"),
                (4, "exactMatch", "already_linked"),
                (5, "exactMatch", "add"),
            ],
        )
        self.assertTrue(rows[4]["is_internal_concept"])

    def test_scheme_scope_leaves_other_schemes_alone(self):
        upload_rows = [[str(self.concepts[2].pk), "http://example.org/x", ""]]

        in_scheme = self.client.post(
            reverse("api-lingo-match-link-import-preview"),
            {"file": csv_upload(upload_rows), "scheme_id": str(self.scheme.pk)},
        )
        other_scheme = self.client.post(
            reverse("api-lingo-match-link-import-preview"),
            {"file": csv_upload(upload_rows), "scheme_id": str(uuid.uuid4())},
        )
        invalid_scheme = self.client.post(
            reverse("api-lingo-match-link-import-preview"),
            {"file": csv_upload(upload_rows), "scheme_id": "not-a-uuid"},
        )

        self.assertEqual(self.outcomes_of(in_scheme), {2: "add"})
        self.assertEqual(self.outcomes_of(other_scheme), {2: "outside_scheme"})
        self.assertEqual(invalid_scheme.status_code, 400)

    def test_imports_left_waiting_or_running_are_failed_when_read(self):
        a_day_ago = timezone.now() - datetime.timedelta(days=1)
        stale_running_import = MatchLinkImport.objects.create(
            user=self.editor,
            status=MatchLinkImport.STATUS_RUNNING,
            started=a_day_ago,
        )
        stale_pending_import = MatchLinkImport.objects.create(user=self.editor)
        MatchLinkImport.objects.filter(pk=stale_pending_import.pk).update(
            created=a_day_ago
        )
        # Queued for a day, but only just picked up by a worker.
        fresh_running_import = MatchLinkImport.objects.create(
            user=self.editor,
            status=MatchLinkImport.STATUS_RUNNING,
            started=timezone.now(),
        )
        MatchLinkImport.objects.filter(pk=fresh_running_import.pk).update(
            created=a_day_ago
        )
        # Queued for an hour: a backed-up queue, not a lost worker.
        queued_pending_import = MatchLinkImport.objects.create(user=self.editor)
        MatchLinkImport.objects.filter(pk=queued_pending_import.pk).update(
            created=timezone.now() - datetime.timedelta(hours=1)
        )

        imports_by_id = {
            match_link_import.pk: self.client.get(
                reverse(
                    "api-lingo-match-link-import", kwargs={"pk": match_link_import.pk}
                )
            ).json()
            for match_link_import in [
                stale_running_import,
                stale_pending_import,
                fresh_running_import,
                queued_pending_import,
            ]
        }

        self.assertEqual(
            {
                import_id: read_import["status"]
                for import_id, read_import in imports_by_id.items()
            },
            {
                stale_running_import.pk: "failed",
                stale_pending_import.pk: "failed",
                fresh_running_import.pk: "running",
                queued_pending_import.pk: "pending",
            },
        )
        self.assertIn(
            "stopped before it finished",
            imports_by_id[stale_pending_import.pk]["error_message"],
        )

    @patch(NOTIFY_COMPLETION)
    def test_an_import_given_up_on_is_never_applied_late(self, notify_completion):
        given_up_import = MatchLinkImport.objects.create(
            user=self.editor,
            status=MatchLinkImport.STATUS_FAILED,
            error_code=MatchLinkImport.ERROR_INTERRUPTED,
            rows=[
                {
                    "row_number": 2,
                    "concept_id": str(self.concepts[2].pk),
                    "match_uri": "http://example.org/late",
                    "match_type": "exactMatch",
                }
            ],
        )

        apply_match_link_import_task(given_up_import.pk)
        apply_match_link_import(given_up_import)

        given_up_import.refresh_from_db()
        self.assertEqual(given_up_import.status, MatchLinkImport.STATUS_FAILED)
        self.assertFalse(
            TileModel.objects.filter(
                nodegroup_id=MATCH_STATUS_NODEGROUP,
                resourceinstance_id=self.concepts[2].pk,
            ).exists()
        )
        notify_completion.assert_not_called()

    @patch(
        "arches_lingo.utils.openrefine_round_trip.match_link_import"
        ".index_concepts_in_transaction",
        side_effect=RuntimeError("Elasticsearch is down"),
    )
    def test_indexing_failure_keeps_the_written_links_on_record(self, _index):
        match_link_import = MatchLinkImport.objects.create(
            user=self.editor,
            rows=[
                {
                    "row_number": 2,
                    "concept_id": str(self.concepts[2].pk),
                    "match_uri": "http://example.org/a",
                    "match_type": "exactMatch",
                }
            ],
        )

        apply_match_link_import(match_link_import)
        match_link_import.refresh_from_db()

        self.assertEqual(match_link_import.status, MatchLinkImport.STATUS_COMPLETE)
        self.assertIsNotNone(match_link_import.edit_transaction_id)
        self.assertEqual(match_link_import.outcome_counts, {"add": 1})
        self.assertEqual(
            match_link_import.error_code, MatchLinkImport.ERROR_INDEXING_FAILED
        )

    def test_locked_scheme_blocks_editors_but_not_lingo_admins(self):
        set_lifecycle_state(self.scheme, LOCKED_STATE_ID)
        upload_rows = [[str(self.concepts[2].pk), "http://example.org/x", ""]]

        editor_preview = self.preview(csv_upload(upload_rows))
        self.client.force_login(self.other_editor)
        admin_preview = self.preview(csv_upload(upload_rows))

        self.assertEqual(self.outcomes_of(editor_preview), {2: "scheme_locked"})
        self.assertEqual(self.outcomes_of(admin_preview), {2: "add"})

    @patch(NOTIFY_COMPLETION)
    @patch(CELERY_CHECK, return_value=False)
    def test_apply_writes_links_once_in_one_edit_transaction(
        self, _celery_check, notify_completion
    ):
        upload_rows = [
            [str(self.concepts[2].pk), "http://example.org/a", ""],
            [str(self.concepts[3].pk), "http://example.org/b", "closeMatch"],
            ["not-a-uuid", "http://example.org/c", ""],
        ]

        response = self.client.post(
            reverse("api-lingo-match-link-imports"), {"file": csv_upload(upload_rows)}
        )
        match_link_import = MatchLinkImport.objects.get(pk=response.json()["id"])
        repeat_preview = self.preview(csv_upload(upload_rows))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(match_link_import.status, MatchLinkImport.STATUS_COMPLETE)
        self.assertEqual(
            match_link_import.outcome_counts, {"add": 2, "unknown_concept": 1}
        )
        self.assertIsNotNone(match_link_import.edit_transaction_id)
        self.assertEqual(
            set(
                EditLog.objects.filter(
                    transactionid=match_link_import.edit_transaction_id
                ).values_list("userid", "user_username")
            ),
            {(str(self.editor.pk), self.editor.username)},
        )
        notify_completion.assert_called_once_with(
            "Match link import finished: 2 links added", self.editor
        )
        self.assertEqual(
            TileModel.objects.filter(
                nodegroup_id=MATCH_STATUS_NODEGROUP,
                resourceinstance_id__in=[self.concepts[2].pk, self.concepts[3].pk],
            ).count(),
            2,
        )
        self.assertEqual(
            self.outcomes_of(repeat_preview),
            {2: "already_linked", 3: "already_linked", 4: "unknown_concept"},
        )

        detail_url = reverse(
            "api-lingo-match-link-import", kwargs={"pk": match_link_import.pk}
        )
        self.assertEqual(self.client.get(detail_url).json()["status"], "complete")
        stranger = User.objects.create_user(username="stranger")
        stranger.groups.add(Group.objects.get(name=LINGO_EDITOR_GROUP_NAME))
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(detail_url).status_code, 404)

    @patch(CELERY_CHECK, return_value=True)
    @patch("arches_lingo.tasks.apply_match_link_import_task.apply_async")
    def test_apply_is_handed_to_a_worker_when_one_is_available(
        self, apply_async, _celery_check
    ):
        response = self.client.post(
            reverse("api-lingo-match-link-imports"),
            {"file": csv_upload([[str(self.concepts[2].pk), "http://e.org/a", ""]])},
        )

        self.assertEqual(response.status_code, 202)
        apply_async.assert_called_once_with(args=[response.json()["id"]])
        self.assertEqual(response.json()["status"], "pending")

    @patch(NOTIFY_COMPLETION)
    def test_worker_task_applies_and_notifies(self, notify_completion):
        match_link_import = MatchLinkImport.objects.create(
            user=self.editor,
            rows=[
                {
                    "row_number": 2,
                    "concept_id": str(self.concepts[2].pk),
                    "match_uri": "http://example.org/a",
                    "match_type": "exactMatch",
                }
            ],
        )
        failing_import = MatchLinkImport.objects.create(user=self.editor, rows=[{}])

        apply_match_link_import_task(match_link_import.pk)
        apply_match_link_import_task(failing_import.pk)
        apply_match_link_import_task(-1)
        apply_match_link_import_task(match_link_import.pk)

        match_link_import.refresh_from_db()
        failing_import.refresh_from_db()
        self.assertEqual(match_link_import.status, MatchLinkImport.STATUS_COMPLETE)
        self.assertEqual(failing_import.status, MatchLinkImport.STATUS_FAILED)
        self.assertEqual(failing_import.error_code, MatchLinkImport.ERROR_APPLY_FAILED)
        self.assertEqual(
            [call.args[0] for call in notify_completion.call_args_list],
            [
                "Match link import finished: 1 link added",
                "Match link import failed",
            ],
        )

    def test_unreadable_files_are_rejected(self):
        oversized = csv_upload([[str(self.concepts[2].pk), "http://e.org/a", ""]])
        for upload, patches in [
            (None, {}),
            (csv_upload([], header=("concept_id", "note")), {}),
            (SimpleUploadedFile("empty.csv", b""), {}),
            (SimpleUploadedFile("latin.csv", "é".encode("latin-1")), {}),
            (
                SimpleUploadedFile(
                    "huge-cell.csv",
                    b"concept_id,match_uri\n" + b"x" * (csv.field_size_limit() + 1),
                ),
                {},
            ),
            (oversized, {"MAX_IMPORT_BYTES": 10}),
            (
                csv_upload([["a", "b", ""], ["c", "d", ""]]),
                {"MAX_IMPORT_ROWS": 1},
            ),
        ]:
            with self.subTest(patches=patches, upload=getattr(upload, "name", None)):
                with (
                    patch.multiple(
                        "arches_lingo.utils.openrefine_round_trip.match_link_import",
                        **patches,
                    )
                    if patches
                    else nullcontext()
                ):
                    response = self.client.post(
                        reverse("api-lingo-match-link-import-preview"),
                        {} if upload is None else {"file": upload},
                    )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.client.post(reverse("api-lingo-match-link-imports")).status_code, 400
        )

    def test_worksheet_columns_are_ignored_and_headers_normalized(self):
        upload = SimpleUploadedFile(
            "worksheet.csv",
            (
                "﻿Concept ID,pref_label,Match-URI\n"
                f"{self.concepts[2].pk},Concept 3,http://example.org/a\n"
                f"{self.concepts[3].pk},Concept 4,\n"
                ",,\n"
            ).encode("utf-8"),
        )

        rows = parse_match_link_csv(upload)

        self.assertEqual(
            rows,
            [
                {
                    "row_number": 2,
                    "concept_id": str(self.concepts[2].pk),
                    "match_uri": "http://example.org/a",
                    "match_type": "exactMatch",
                }
            ],
        )
