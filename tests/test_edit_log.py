import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from arches.app.models.models import EditLog, NodeGroup
from arches.app.models.tile import Tile as RealTile

from django.contrib.auth.models import User
from django.urls import reverse

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    SCHEME_NAME_NODEGROUP,
)
from arches_lingo.utils.edit_log import revert_resource_to_timestamp
from tests.tests import ViewTests


class EditLogTestMixin:
    """Shared helpers for edit log tests."""

    @classmethod
    def _create_edit(
        cls,
        resource,
        edittype,
        timestamp,
        *,
        tileid=None,
        nodegroupid=None,
        newvalue=None,
        oldvalue=None,
        note=None,
    ):
        return EditLog.objects.create(
            resourceinstanceid=str(resource.pk),
            edittype=edittype,
            timestamp=timestamp,
            userid=str(cls.admin.pk),
            user_firstname="admin",
            user_lastname="admin",
            user_username="admin",
            user_email="admin@test.com",
            tileinstanceid=str(tileid) if tileid else None,
            nodegroupid=str(nodegroupid) if nodegroupid else None,
            newvalue=newvalue,
            oldvalue=oldvalue,
            note=note,
        )


class EditLogGetViewTests(EditLogTestMixin, ViewTests):
    """HTTP-level tests for GET /api/lingo/resource/<id>/edit-log."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        cls._create_edit(cls.scheme, "create", cls.base_time, note="Created resource")
        cls._create_edit(
            cls.scheme,
            "tile create",
            cls.base_time + timedelta(minutes=5),
            nodegroupid=SCHEME_NAME_NODEGROUP,
            tileid=uuid.uuid4(),
        )

    def _get_edit_log(self):
        return json.loads(
            self.client.get(
                reverse("api-lingo-edit-log", args=[self.scheme.pk])
            ).content
        )

    def test_returns_200_with_edit_list(self):
        response = self.client.get(reverse("api-lingo-edit-log", args=[self.scheme.pk]))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["resourceid"], str(self.scheme.pk))
        self.assertIsInstance(data["edits"], list)
        self.assertGreaterEqual(len(data["edits"]), 2)

    def test_edits_ordered_ascending_by_timestamp(self):
        data = self._get_edit_log()
        timestamps = [entry["timestamp"] for entry in data["edits"]]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_edit_fields_are_serialized(self):
        data = self._get_edit_log()
        resource_create_edit = next(
            entry for entry in data["edits"] if entry["edittype"] == "create"
        )

        self.assertEqual(resource_create_edit["edittype_label"], "Resource Created")
        self.assertEqual(resource_create_edit["user_username"], "admin")
        self.assertIsNotNone(resource_create_edit["timestamp"])
        self.assertIsNotNone(resource_create_edit["editlogid"])
        self.assertEqual(resource_create_edit["note"], "Created resource")
        self.assertIsNone(resource_create_edit["nodegroupid"])
        self.assertIsNone(resource_create_edit["card_name"])

    def test_tile_edit_includes_card_name_field(self):
        data = self._get_edit_log()
        tile_create_edit = next(
            entry for entry in data["edits"] if entry["edittype"] == "tile create"
        )

        self.assertEqual(tile_create_edit["nodegroupid"], SCHEME_NAME_NODEGROUP)
        self.assertIn("card_name", tile_create_edit)

    def test_known_edit_types_have_human_readable_labels(self):
        data = self._get_edit_log()
        edits_by_type = {entry["edittype"]: entry for entry in data["edits"]}

        self.assertEqual(edits_by_type["create"]["edittype_label"], "Resource Created")
        self.assertEqual(edits_by_type["tile create"]["edittype_label"], "Tile Created")

    def test_returns_404_for_unknown_resource(self):
        url = reverse("api-lingo-edit-log", args=[uuid.uuid4()])
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_is_denied(self):
        self.client.logout()
        response = self.client.get(reverse("api-lingo-edit-log", args=[self.scheme.pk]))

        self.assertIn(response.status_code, [403, 302])

    def test_non_editor_authenticated_user_can_read_edit_log(self):
        self.client.force_login(
            User.objects.create_user(username="viewer", password="test123")
        )
        response = self.client.get(reverse("api-lingo-edit-log", args=[self.scheme.pk]))

        self.assertEqual(response.status_code, 200)


class EditLogPostViewTests(EditLogTestMixin, ViewTests):
    """HTTP-level tests for POST /api/lingo/resource/<id>/edit-log (auth, request parsing)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.base_time = datetime(2025, 6, 1, 12, 0, 0)

    def _post_revert(self, resource, timestamp=None):
        target_timestamp = (timestamp or self.base_time).isoformat()
        url = reverse("api-lingo-edit-log", args=[resource.pk])
        return self.client.post(
            url,
            data=json.dumps({"timestamp": target_timestamp}),
            content_type="application/json",
        )

    def test_returns_200_on_valid_request(self):
        self.assertEqual(self._post_revert(self.scheme).status_code, 200)

    def test_returns_400_for_invalid_json(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-lingo-edit-log", args=[self.scheme.pk]),
                data="not json",
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)

    def test_returns_400_when_timestamp_missing(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-lingo-edit-log", args=[self.scheme.pk]),
                data=json.dumps({"other_key": "value"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)

    def test_returns_400_for_invalid_timestamp_format(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-lingo-edit-log", args=[self.scheme.pk]),
                data=json.dumps({"timestamp": "not-a-timestamp"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)

    def test_returns_404_for_unknown_resource(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self._post_revert(MagicMock(pk=uuid.uuid4()))
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_is_denied(self):
        self.client.logout()
        self.assertIn(self._post_revert(self.scheme).status_code, [403, 302])

    def test_non_admin_user_is_denied(self):
        self.client.force_login(
            User.objects.create_user(username="viewer2", password="test123")
        )
        self.assertIn(self._post_revert(self.scheme).status_code, [403, 302])


class EditLogRevertUtilTests(EditLogTestMixin, ViewTests):
    """Tests for the revert_resource_to_timestamp utility function."""

    TILE_PATCH_TARGET = "arches_lingo.utils.edit_log.Tile"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.base_time = datetime(2025, 6, 1, 12, 0, 0)  # naive — USE_TZ=False

    def _revert(self, resource, timestamp=None):
        return revert_resource_to_timestamp(
            str(resource.pk),
            timestamp or self.base_time,
            MagicMock(),
        )

    @contextmanager
    def _patch_tile(self, *, return_value=None, side_effect=None):
        with patch(self.TILE_PATCH_TARGET) as MockTile:
            MockTile.DoesNotExist = RealTile.DoesNotExist
            if side_effect is not None:
                MockTile.objects.get.side_effect = side_effect
            elif return_value is not None:
                MockTile.objects.get.return_value = return_value
            yield MockTile

    def test_deletes_tile_created_after_target(self):
        """Tiles created after target timestamp should be deleted."""
        concept = self.concepts[0]
        mock_tile = MagicMock()

        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=uuid.uuid4(),
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Extra label"},
        )

        with self._patch_tile(return_value=mock_tile):
            errors = self._revert(concept)

        self.assertEqual(errors, [])
        mock_tile.delete.assert_called_once()

    def test_restores_tile_to_earlier_state(self):
        """Tiles edited after target timestamp should be reverted to their earlier data."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()
        original_data = {
            CONCEPT_NAME_CONTENT_NODE: "Original label",
            CONCEPT_NAME_LANGUAGE_NODE: "en",
        }
        modified_data = {
            CONCEPT_NAME_CONTENT_NODE: "Modified label",
            CONCEPT_NAME_LANGUAGE_NODE: "en",
        }

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue=original_data,
        )
        self._create_edit(
            concept,
            "tile edit",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue=modified_data,
            oldvalue=original_data,
        )

        mock_tile = MagicMock()
        mock_tile.data = modified_data.copy()
        with self._patch_tile(return_value=mock_tile):
            errors = self._revert(concept)

        self.assertEqual(errors, [])
        self.assertEqual(mock_tile.data, original_data)
        mock_tile.save.assert_called_once()

    def test_deletes_tile_recreated_after_earlier_deletion(self):
        """If a tile was deleted before target and recreated after, delete it on revert."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()
        mock_tile = MagicMock()

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=2),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Tmp"},
        )
        self._create_edit(
            concept,
            "tile delete",
            self.base_time - timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
        )
        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Re-created"},
        )

        with self._patch_tile(return_value=mock_tile):
            errors = self._revert(concept)

        self.assertEqual(errors, [])
        mock_tile.delete.assert_called_once()

    def test_no_op_when_no_edits_after_target(self):
        """When no tile edits exist after target timestamp, revert is a no-op."""
        concept = self.concepts[0]

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=1),
            tileid=uuid.uuid4(),
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Old"},
        )

        self.assertEqual(self._revert(concept), [])

    def test_naive_target_timestamp_is_treated_as_utc(self):
        """A naive datetime passed to the service is interpreted as UTC."""
        concept = self.concepts[0]
        mock_tile = MagicMock()

        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=uuid.uuid4(),
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "After"},
        )

        with self._patch_tile(return_value=mock_tile):
            errors = revert_resource_to_timestamp(
                str(concept.pk), self.base_time, MagicMock()
            )

        self.assertEqual(errors, [])
        mock_tile.delete.assert_called_once()

    def test_resource_level_edits_without_tile_id_are_ignored(self):
        """Edits without a tileinstanceid (e.g. resource create) do not cause errors."""
        concept = self.concepts[0]

        self._create_edit(concept, "create", self.base_time + timedelta(hours=1))

        self.assertEqual(self._revert(concept), [])

    def test_silently_ignores_tile_already_gone_at_deletion_time(self):
        """Tile.DoesNotExist during deletion is silently caught — not an error."""
        concept = self.concepts[0]

        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=uuid.uuid4(),
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Ghost"},
        )

        with self._patch_tile(side_effect=RealTile.DoesNotExist):
            errors = self._revert(concept)

        self.assertEqual(errors, [])

    def test_captures_error_when_tile_deletion_raises(self):
        """An unexpected exception from tile.delete() is captured in the error list."""
        concept = self.concepts[0]
        mock_tile = MagicMock()
        mock_tile.delete.side_effect = Exception("delete failed")

        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=uuid.uuid4(),
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "data"},
        )

        with self._patch_tile(return_value=mock_tile):
            errors = self._revert(concept)

        self.assertEqual(len(errors), 1)
        self.assertIn("delete failed", errors[0])

    def test_silently_ignores_already_gone_tile_when_target_state_was_deleted(self):
        """Tile.DoesNotExist when the target state is also a deletion is silently caught."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=2),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Tmp"},
        )
        self._create_edit(
            concept,
            "tile delete",
            self.base_time - timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
        )
        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Re-created"},
        )

        with self._patch_tile(side_effect=RealTile.DoesNotExist):
            errors = self._revert(concept)

        self.assertEqual(errors, [])

    def test_captures_error_when_deletion_raises_for_previously_deleted_tile(self):
        """An exception from tile.delete() for a tile in a deleted target state is captured."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()
        mock_tile = MagicMock()
        mock_tile.delete.side_effect = Exception("cannot delete")

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=2),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Tmp"},
        )
        self._create_edit(
            concept,
            "tile delete",
            self.base_time - timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
        )
        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Re-created"},
        )

        with self._patch_tile(return_value=mock_tile):
            errors = self._revert(concept)

        self.assertEqual(len(errors), 1)
        self.assertIn("cannot delete", errors[0])

    def test_skips_tile_with_no_recorded_state_at_target(self):
        """If the last edit before target has no newvalue, the tile is left unchanged."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue=None,
        )
        self._create_edit(
            concept,
            "tile edit",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Updated"},
        )

        self.assertEqual(self._revert(concept), [])

    def test_recreates_top_level_tile_deleted_after_target(self):
        """A top-level tile deleted after target timestamp should be recreated."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()
        target_data = {CONCEPT_NAME_CONTENT_NODE: "Original data"}
        mock_new_tile = MagicMock()

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue=target_data,
        )
        self._create_edit(
            concept,
            "tile delete",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
        )

        with self._patch_tile(side_effect=RealTile.DoesNotExist) as MockTile:
            MockTile.return_value = mock_new_tile
            errors = self._revert(concept)

        self.assertEqual(errors, [])
        mock_new_tile.save.assert_called_once()

    def test_captures_error_when_tile_save_raises_during_revert(self):
        """An exception from tile.save() during a data revert is captured."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()
        mock_tile = MagicMock()
        mock_tile.save.side_effect = Exception("save failed")

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Original"},
        )
        self._create_edit(
            concept,
            "tile edit",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Modified"},
        )

        with self._patch_tile(return_value=mock_tile):
            errors = self._revert(concept)

        self.assertEqual(len(errors), 1)
        self.assertIn("Failed to update tile", errors[0])

    def test_captures_error_when_tile_save_raises_during_recreation(self):
        """An exception from tile.save() during tile recreation is captured."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()
        mock_new_tile = MagicMock()
        mock_new_tile.save.side_effect = Exception("restore failed")

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Data"},
        )
        self._create_edit(
            concept,
            "tile delete",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
        )

        with self._patch_tile(side_effect=RealTile.DoesNotExist) as MockTile:
            MockTile.return_value = mock_new_tile
            errors = self._revert(concept)

        self.assertEqual(len(errors), 1)
        self.assertIn("Failed to restore tile", errors[0])

    def test_reports_error_when_nested_tile_needs_recreation(self):
        """Recreating a nested tile reports an error since parent context is unavailable."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        nested_nodegroup = NodeGroup.objects.filter(
            parentnodegroup__isnull=False
        ).first()
        if not nested_nodegroup:
            self.skipTest("No nested nodegroup available in test data")

        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=2),
            tileid=tileid,
            nodegroupid=str(nested_nodegroup.pk),
            newvalue={"some_node": "data"},
        )
        self._create_edit(
            concept,
            "tile delete",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=str(nested_nodegroup.pk),
        )

        with self._patch_tile(side_effect=RealTile.DoesNotExist):
            errors = self._revert(concept)

        self.assertEqual(len(errors), 1)
        self.assertIn("Cannot restore nested tile", errors[0])
