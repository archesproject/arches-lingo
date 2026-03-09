import json
import uuid
from datetime import datetime, timedelta, timezone

from django.urls import reverse

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import (
    EditLog,
    ResourceInstance,
    ResourceXResource,
    TileModel,
)

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    CONCEPTS_GRAPH_ID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    LABEL_LIST_ID,
    PREF_LABEL_URI,
    SCHEMES_GRAPH_ID,
)

from tests.tests import ViewTests


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

    def test_concept_count_all_schemes(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        self.assertEqual(data["concept_count"], 5)
        self.assertEqual(data["scheme_count"], 1)

    def test_concept_count_filtered_by_unknown_scheme(self):
        other_scheme_id = str(uuid.uuid4())
        response = self.client.get(
            reverse("api-lingo-dashboard"), {"scheme": other_scheme_id}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["concept_count"], 0)

    def test_recent_activity_includes_concept_edits(self):
        edit_timestamp = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.concepts[0], "tile create", edit_timestamp)

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        resource_ids = [item["resource_id"] for item in data["recent_activity"]]
        self.assertIn(str(self.concepts[0].pk), resource_ids)

    def test_recent_activity_deduplicates_by_transaction(self):
        edit_timestamp = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        transaction_id = uuid.uuid4()
        self._create_edit(
            self.concepts[0],
            "tile create",
            edit_timestamp,
            transactionid=transaction_id,
        )
        self._create_edit(
            self.concepts[0],
            "tile create",
            edit_timestamp,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            transactionid=transaction_id,
        )

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        # Both edits share the same transaction ID; only one entry should appear
        txn_entries = [
            item
            for item in data["recent_activity"]
            if item["resource_id"] == str(self.concepts[0].pk)
        ]
        # At most one entry per transaction
        self.assertLessEqual(len(txn_entries), 1)

    def test_recent_activity_capped_at_20(self):
        base_timestamp = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
        for edit_num in range(25):
            self._create_edit(
                self.concepts[edit_num % 5],
                "tile edit",
                base_timestamp + timedelta(minutes=edit_num),
            )

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        self.assertLessEqual(len(data["recent_activity"]), 20)

    def test_recent_activity_scheme_resource_type(self):
        edit_timestamp = datetime(2025, 6, 1, 14, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.scheme, "create", edit_timestamp)

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
        in_scheme_timestamp = datetime(2025, 6, 1, 15, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.concepts[0], "tile edit", in_scheme_timestamp)

        # Edit for a concept NOT in the test scheme
        other_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Other Concept"
        )
        out_of_scheme_timestamp = datetime(2025, 6, 1, 16, 0, 0, tzinfo=timezone.utc)
        self._create_edit(other_concept, "tile create", out_of_scheme_timestamp)

        response = self.client.get(
            reverse("api-lingo-dashboard"), {"scheme": str(self.scheme.pk)}
        )
        data = json.loads(response.content)

        resource_ids = {item["resource_id"] for item in data["recent_activity"]}
        # The other concept (not in this scheme) should not appear
        self.assertNotIn(str(other_concept.pk), resource_ids)

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

    def test_labels_by_language_count_correct(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        en_entries = [
            entry for entry in data["labels_by_language"] if entry["code"] == "en"
        ]
        self.assertEqual(len(en_entries), 1)
        # 5 concepts × 1 EN label each
        self.assertEqual(en_entries[0]["count"], 5)

    def test_labels_by_type_contains_pref_label(self):
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        uris = [entry["uri"] for entry in data["labels_by_type"]]
        self.assertIn(PREF_LABEL_URI, uris)

    def test_labels_per_concept(self):
        # 5 concepts × 1 label each → 1.0
        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        self.assertIn("labels_per_concept", data)
        self.assertEqual(data["labels_per_concept"], 1.0)

    def test_days_filter_restricts_activity(self):
        old_timestamp = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        recent_timestamp = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        self._create_edit(self.concepts[0], "tile create", old_timestamp)
        self._create_edit(self.concepts[1], "tile create", recent_timestamp)

        # With days=1, only the recent edit should appear
        response = self.client.get(reverse("api-lingo-dashboard"), {"days": "1"})
        data = json.loads(response.content)
        resource_ids = {item["resource_id"] for item in data["recent_activity"]}
        self.assertIn(str(self.concepts[1].pk), resource_ids)
        self.assertNotIn(str(self.concepts[0].pk), resource_ids)

    def test_days_zero_shows_all_activity(self):
        old_timestamp = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self._create_edit(self.concepts[0], "tile create", old_timestamp)

        response = self.client.get(reverse("api-lingo-dashboard"), {"days": "0"})
        data = json.loads(response.content)
        resource_ids = {item["resource_id"] for item in data["recent_activity"]}
        self.assertIn(str(self.concepts[0].pk), resource_ids)

    def test_invalid_days_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(reverse("api-lingo-dashboard"), {"days": "abc"})
        self.assertEqual(response.status_code, 400)

    def test_multi_scheme_filter(self):
        # Create a second scheme with its own concept
        second_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Second Scheme"
        )
        extra_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Extra Concept"
        )
        resource_relationship = ResourceXResource(
            from_resource=extra_concept,
            from_resource_graph_id=CONCEPTS_GRAPH_ID,
            to_resource=second_scheme,
            to_resource_graph_id=SCHEMES_GRAPH_ID,
            created=datetime.now(),
            modified=datetime.now(),
        )
        resource_relationship.save()
        TileModel.objects.create(
            resourceinstance=extra_concept,
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {
                        "resourceId": str(second_scheme.pk),
                        "resourceXresourceId": str(resource_relationship.pk),
                    }
                ]
            },
        )

        # Filter by both schemes — should include concepts from both
        response = self.client.get(
            reverse("api-lingo-dashboard"),
            {"scheme": [str(self.scheme.pk), str(second_scheme.pk)]},
        )
        data = json.loads(response.content)
        # 5 from the first scheme + 1 from the second
        self.assertEqual(data["concept_count"], 6)
        self.assertEqual(data["scheme_count"], 2)

    def test_nodegroup_name_in_activity_label(self):
        edit_timestamp = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
        self._create_edit(
            self.concepts[0],
            "tile create",
            edit_timestamp,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
        )

        response = self.client.get(reverse("api-lingo-dashboard"))
        data = json.loads(response.content)

        matching = [
            item
            for item in data["recent_activity"]
            if item["resource_id"] == str(self.concepts[0].pk)
        ]
        self.assertTrue(len(matching) > 0)
        label = matching[0]["edittype_label"]
        # Should use the nodegroup name instead of "Tile"
        self.assertNotIn("Tile", label)

    def test_invalid_scheme_uuid_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(
                reverse("api-lingo-dashboard"), {"scheme": "not-a-uuid"}
            )
        self.assertEqual(response.status_code, 400)


class MissingTranslationsViewTests(DashboardTestMixin, ViewTests):
    """Tests for GET /api/lingo/concepts/missing-translations."""

    def test_missing_language_param_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(reverse("api-lingo-missing-translations"))
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
        preferred_label_reference_value = self._make_pref_label_reference()
        TileModel.objects.create(
            resourceinstance=self.concepts[0],
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "Konzept 1",
                CONCEPT_NAME_TYPE_NODE: preferred_label_reference_value,
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
        alt_label_reference_value = reference.transform_value_for_tile(
            "altLabel", **{"controlledList": LABEL_LIST_ID}
        )
        TileModel.objects.create(
            resourceinstance=self.concepts[1],
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data={
                CONCEPT_NAME_CONTENT_NODE: "Konzept alt",
                CONCEPT_NAME_TYPE_NODE: alt_label_reference_value,
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

    def test_scheme_filter_excludes_other_scheme_concepts(self):
        # Create a second scheme with one concept
        second_scheme = ResourceInstance.objects.create(
            graph_id=SCHEMES_GRAPH_ID, name="Second Scheme"
        )
        other_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Other Concept"
        )
        resource_relationship = ResourceXResource(
            from_resource=other_concept,
            from_resource_graph_id=CONCEPTS_GRAPH_ID,
            to_resource=second_scheme,
            to_resource_graph_id=SCHEMES_GRAPH_ID,
            created=datetime.now(),
            modified=datetime.now(),
        )
        resource_relationship.save()
        TileModel.objects.create(
            resourceinstance=other_concept,
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            data={
                CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID: [
                    {
                        "resourceId": str(second_scheme.pk),
                        "resourceXresourceId": str(resource_relationship.pk),
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
