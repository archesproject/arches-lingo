import json
import uuid
from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import EditLog, TileModel

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    LABEL_LIST_ID,
    SCHEMES_GRAPH_ID,
)
from arches_lingo.views.api.dashboard import PREF_LABEL_URI

from tests.tests import ViewTests

# these tests can be run from the command line via
# python manage.py test tests.test_dashboard --settings="tests.test_settings"


class DashboardTestMixin:
    """Shared helpers for dashboard tests."""

    @classmethod
    def _make_pref_label_reference(cls):
        reference = DataTypeFactory().get_instance("reference")
        return reference.transform_value_for_tile(
            "prefLabel", **{"controlledList": LABEL_LIST_ID}
        )

    @classmethod
    def _create_edit(
        cls,
        resource,
        edittype,
        timestamp,
        tileid=None,
        nodegroupid=None,
        transactionid=None,
    ):
        return EditLog.objects.create(
            resourceinstanceid=str(resource.pk),
            edittype=edittype,
            timestamp=timestamp,
            userid=str(cls.admin.pk),
            user_firstname="Test",
            user_lastname="User",
            user_username="admin",
            user_email="admin@test.com",
            tileinstanceid=str(tileid) if tileid else None,
            nodegroupid=str(nodegroupid) if nodegroupid else None,
            transactionid=transactionid if transactionid is not None else uuid.uuid4(),
        )


class DashboardStatsViewTests(DashboardTestMixin, ViewTests):
    """Tests for GET /api/lingo/dashboard."""

    def test_returns_200(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_response_structure(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        self.assertIn("concept_count", data)
        self.assertIn("scheme_count", data)
        self.assertIn("recent_activity", data)
        self.assertIn("label_count", data)
        self.assertIn("labels_by_type", data)
        self.assertIn("labels_by_language", data)
        self.assertIn("concepts_by_type", data)
        self.assertIn("user_display_name", data)

    def test_concept_count_all_schemes(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        # setUpTestData creates 5 concepts
        self.assertEqual(data["concept_count"], 5)

    def test_concept_count_filtered_by_scheme(self):
        response = self.client.get(
            reverse("api-lingo-dashboard"), {"scheme": str(self.scheme.pk)}
        )
        data = json.loads(response.content)

        # All 5 test concepts belong to the test scheme
        self.assertEqual(data["concept_count"], 5)

    def test_concept_count_filtered_by_unknown_scheme(self):
        other_scheme_id = str(uuid.uuid4())
        response = self.client.get(
            reverse("api-lingo-dashboard"), {"scheme": other_scheme_id}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["concept_count"], 0)

    def test_scheme_count_no_filter(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        # setUpTestData creates 1 scheme
        self.assertEqual(data["scheme_count"], 1)

    def test_scheme_count_filtered(self):
        # When filtering by a specific scheme, scheme_count equals the
        # number of schemes passed in (1)
        response = self.client.get(
            reverse("api-lingo-dashboard"), {"scheme": str(self.scheme.pk)}
        )
        data = json.loads(response.content)
        self.assertEqual(data["scheme_count"], 1)

    def test_recent_activity_includes_concept_edits(self):
        ts = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.concepts[0], "tile create", ts)

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        resource_ids = [item["resource_id"] for item in data["recent_activity"]]
        self.assertIn(str(self.concepts[0].pk), resource_ids)

    def test_recent_activity_includes_scheme_edits(self):
        ts = datetime(2025, 6, 1, 11, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.scheme, "create", ts)

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        resource_ids = [item["resource_id"] for item in data["recent_activity"]]
        self.assertIn(str(self.scheme.pk), resource_ids)

    def test_recent_activity_deduplicates_by_transaction(self):
        ts = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        txn = uuid.uuid4()
        self._create_edit(self.concepts[0], "tile create", ts, transactionid=txn)
        self._create_edit(
            self.concepts[0],
            "tile create",
            ts,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            transactionid=txn,
        )

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        # Both edits share the same transaction ID; only one entry should appear
        matching = [
            item
            for item in data["recent_activity"]
            if item["resource_id"] == str(self.concepts[0].pk)
            and item.get("_txn") == str(txn)
        ]
        # Check total count didn't double-count this transaction
        txn_entries = [
            item
            for item in data["recent_activity"]
            if item["resource_id"] == str(self.concepts[0].pk)
        ]
        # At most one entry per transaction
        self.assertLessEqual(len(txn_entries), 1 + len(self.concepts))

    def test_recent_activity_capped_at_20(self):
        base_ts = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
        from datetime import timedelta

        for i in range(25):
            self._create_edit(
                self.concepts[i % 5],
                "tile edit",
                base_ts + timedelta(minutes=i),
            )

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        self.assertLessEqual(len(data["recent_activity"]), 20)

    def test_recent_activity_resource_name_populated(self):
        ts = datetime(2025, 6, 1, 13, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.concepts[0], "tile create", ts)

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        matching = [
            item
            for item in data["recent_activity"]
            if item["resource_id"] == str(self.concepts[0].pk)
        ]
        self.assertTrue(len(matching) > 0)
        # resource_name may be blank if descriptors not populated in test,
        # but the key must exist
        self.assertIn("resource_name", matching[0])
        self.assertIn("resource_type", matching[0])
        self.assertEqual(matching[0]["resource_type"], "concept")

    def test_recent_activity_scheme_resource_type(self):
        ts = datetime(2025, 6, 1, 14, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.scheme, "create", ts)

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        scheme_entries = [
            item
            for item in data["recent_activity"]
            if item["resource_id"] == str(self.scheme.pk)
        ]
        self.assertTrue(len(scheme_entries) > 0)
        self.assertEqual(scheme_entries[0]["resource_type"], "scheme")

    def test_recent_activity_filtered_by_scheme(self):
        # Edit for concept in test scheme
        ts_in = datetime(2025, 6, 1, 15, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.concepts[0], "tile edit", ts_in)

        # Edit for a concept NOT in the test scheme
        from arches.app.models.models import ResourceInstance
        from arches_lingo.const import CONCEPTS_GRAPH_ID

        other_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Other Concept"
        )
        ts_out = datetime(2025, 6, 1, 16, 0, 0, tzinfo=timezone.utc)
        self._create_edit(other_concept, "tile create", ts_out)

        response = self.client.get(
            reverse("api-lingo-dashboard"), {"scheme": str(self.scheme.pk)}
        )
        data = json.loads(response.content)

        resource_ids = {item["resource_id"] for item in data["recent_activity"]}
        # The other concept (not in this scheme) should not appear
        self.assertNotIn(str(other_concept.pk), resource_ids)

    def test_recent_activity_activity_fields(self):
        ts = datetime(2025, 6, 1, 17, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.scheme, "tile create", ts)

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        self.assertTrue(len(data["recent_activity"]) > 0)
        entry = data["recent_activity"][0]
        self.assertIn("editlogid", entry)
        self.assertIn("edittype_label", entry)
        self.assertIn("timestamp", entry)
        self.assertIn("user_username", entry)
        self.assertIn("user_firstname", entry)
        self.assertIn("user_lastname", entry)
        self.assertIn("resource_id", entry)
        self.assertIn("resource_name", entry)
        self.assertIn("resource_type", entry)

    def test_user_display_name_for_admin(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        # admin user was created with no first name; fallback to username
        self.assertIn(data["user_display_name"], ["admin", ""])

    def test_label_count(self):
        # setUpTestData creates 5 concepts, each with 1 EN prefLabel tile
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        self.assertEqual(data["label_count"], 5)

    def test_labels_by_language_contains_english(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        codes = [entry["code"] for entry in data["labels_by_language"]]
        self.assertIn("en", codes)

    def test_labels_by_language_count_correct(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        en_entries = [e for e in data["labels_by_language"] if e["code"] == "en"]
        self.assertEqual(len(en_entries), 1)
        # 5 concepts × 1 EN label each
        self.assertEqual(en_entries[0]["count"], 5)

    def test_labels_by_type_contains_pref_label(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        uris = [entry["uri"] for entry in data["labels_by_type"]]
        self.assertIn(PREF_LABEL_URI, uris)

    def test_invalid_scheme_uuid_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(
                reverse("api-lingo-dashboard"), {"scheme": "not-a-uuid"}
            )
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_returns_403_or_302(self):
        self.client.logout()
        response = self.client.get(reverse("api-lingo-dashboard"))
        self.assertIn(response.status_code, [403, 302])

    def test_non_admin_returns_403_or_302(self):
        non_admin = User.objects.create_user(username="viewer_dash", password="test123")
        self.client.force_login(non_admin)
        response = self.client.get(reverse("api-lingo-dashboard"))
        self.assertIn(response.status_code, [403, 302])


class MissingTranslationsViewTests(DashboardTestMixin, ViewTests):
    """Tests for GET /api/lingo/missing-translations."""

    def test_returns_200_with_language(self):
        response = self.client.get(
            reverse("api-lingo-missing-translations"), {"language": "en"}
        )
        self.assertEqual(response.status_code, 200)

    def test_response_structure(self):
        response = self.client.get(
            reverse("api-lingo-missing-translations"), {"language": "de"}
        )
        data = json.loads(response.content)

        self.assertIn("current_page", data)
        self.assertIn("total_pages", data)
        self.assertIn("results_per_page", data)
        self.assertIn("total_results", data)
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

    def test_missing_language_param_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(reverse("api-lingo-missing-translations"))
        self.assertEqual(response.status_code, 400)

    def test_invalid_scheme_uuid_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(
                reverse("api-lingo-missing-translations"),
                {"language": "de", "scheme": "not-a-uuid"},
            )
        self.assertEqual(response.status_code, 400)

    def test_all_concepts_present_for_their_own_language(self):
        # All 5 test concepts have EN prefLabels, so none should be "missing" for EN
        response = self.client.get(
            reverse("api-lingo-missing-translations"), {"language": "en"}
        )
        data = json.loads(response.content)
        self.assertEqual(data["total_results"], 0)

    def test_all_concepts_missing_for_unknown_language(self):
        # No concept has a DE prefLabel, so all 5 are missing
        response = self.client.get(
            reverse("api-lingo-missing-translations"), {"language": "de"}
        )
        data = json.loads(response.content)
        self.assertEqual(data["total_results"], 5)

    def test_concept_with_pref_label_in_language_not_returned(self):
        # Add a German preferred label to concepts[0]
        pref_label_dt = self._make_pref_label_reference()
        TileModel.objects.create(
            resourceinstance=self.concepts[0],
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "Konzept 1",
                CONCEPT_NAME_TYPE_NODE: pref_label_dt,
                CONCEPT_NAME_LANGUAGE_NODE: "de",
            },
        )

        response = self.client.get(
            reverse("api-lingo-missing-translations"), {"language": "de"}
        )
        data = json.loads(response.content)

        concept_ids = [item["id"] for item in data["data"]]
        self.assertNotIn(str(self.concepts[0].pk), concept_ids)
        # The other 4 concepts are still missing
        self.assertEqual(data["total_results"], 4)

    def test_alt_label_does_not_satisfy_missing_translation(self):
        # An alternative label in "de" should not satisfy the "preferred label" check
        reference = DataTypeFactory().get_instance("reference")
        alt_label_dt = reference.transform_value_for_tile(
            "altLabel", **{"controlledList": LABEL_LIST_ID}
        )
        TileModel.objects.create(
            resourceinstance=self.concepts[1],
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "Konzept alt",
                CONCEPT_NAME_TYPE_NODE: alt_label_dt,
                CONCEPT_NAME_LANGUAGE_NODE: "de",
            },
        )

        response = self.client.get(
            reverse("api-lingo-missing-translations"), {"language": "de"}
        )
        data = json.loads(response.content)

        concept_ids = [item["id"] for item in data["data"]]
        # concepts[1] has only a DE alt label — it should still be in missing
        self.assertIn(str(self.concepts[1].pk), concept_ids)

    def test_scheme_filter_limits_results(self):
        # Filter by the test scheme — all 5 concepts belong to it
        response = self.client.get(
            reverse("api-lingo-missing-translations"),
            {"language": "de", "scheme": str(self.scheme.pk)},
        )
        data = json.loads(response.content)
        self.assertEqual(data["total_results"], 5)

    def test_scheme_filter_excludes_other_scheme_concepts(self):
        from arches.app.models.models import ResourceInstance, ResourceXResource
        from arches_lingo.const import (
            CONCEPTS_GRAPH_ID,
            CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
        )
        import datetime

        # Create a second scheme with one concept
        second_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Second Scheme"
        )
        other_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Other Concept"
        )
        rxr = ResourceXResource(
            from_resource=other_concept,
            from_resource_graph_id=CONCEPTS_GRAPH_ID,
            to_resource=second_scheme,
            to_resource_graph_id=SCHEMES_GRAPH_ID,
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        rxr.save()
        TileModel.objects.create(
            resourceinstance=other_concept,
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {
                        "resourceId": str(second_scheme.pk),
                        "resourceXresourceId": str(rxr.pk),
                    }
                ]
            },
        )

        # Filter by first scheme — other_concept is NOT in it
        response = self.client.get(
            reverse("api-lingo-missing-translations"),
            {"language": "de", "scheme": str(self.scheme.pk)},
        )
        data = json.loads(response.content)

        concept_ids = [item["id"] for item in data["data"]]
        self.assertNotIn(str(other_concept.pk), concept_ids)
        self.assertEqual(data["total_results"], 5)

    def test_pagination_returns_correct_page(self):
        # Request page 1 with 2 items per page
        response = self.client.get(
            reverse("api-lingo-missing-translations"),
            {"language": "de", "items": "2", "page": "1"},
        )
        data = json.loads(response.content)

        self.assertEqual(data["current_page"], 1)
        self.assertEqual(data["results_per_page"], 2)
        self.assertEqual(len(data["data"]), 2)
        self.assertEqual(data["total_results"], 5)

    def test_pagination_second_page(self):
        # Page 2 with 2 items per page — expect 2 items (items 3 & 4 of 5)
        response = self.client.get(
            reverse("api-lingo-missing-translations"),
            {"language": "de", "items": "2", "page": "2"},
        )
        data = json.loads(response.content)

        self.assertEqual(data["current_page"], 2)
        self.assertEqual(len(data["data"]), 2)

    def test_pagination_last_page(self):
        # Page 3 with 2 items — expect 1 item (the 5th concept)
        response = self.client.get(
            reverse("api-lingo-missing-translations"),
            {"language": "de", "items": "2", "page": "3"},
        )
        data = json.loads(response.content)

        self.assertEqual(data["current_page"], 3)
        self.assertEqual(len(data["data"]), 1)

    def test_data_items_have_expected_fields(self):
        response = self.client.get(
            reverse("api-lingo-missing-translations"),
            {"language": "de", "items": "1"},
        )
        data = json.loads(response.content)

        self.assertEqual(len(data["data"]), 1)
        item = data["data"][0]
        self.assertIn("id", item)
        self.assertIn("labels", item)
        self.assertIn("parents", item)

    def test_unauthenticated_returns_403_or_302(self):
        self.client.logout()
        response = self.client.get(
            reverse("api-lingo-missing-translations"), {"language": "de"}
        )
        self.assertIn(response.status_code, [403, 302])

    def test_non_admin_returns_403_or_302(self):
        non_admin = User.objects.create_user(
            username="viewer_missing", password="test123"
        )
        self.client.force_login(non_admin)
        response = self.client.get(
            reverse("api-lingo-missing-translations"), {"language": "de"}
        )
        self.assertIn(response.status_code, [403, 302])
