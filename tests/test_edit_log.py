import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from arches.app.models.tile import Tile as RealTile

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from arches.app.models.models import (
    EditLog,
    NodeGroup,
)

from arches_lingo.const import (
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    SCHEME_NAME_NODEGROUP,
)
from arches_lingo.views.api.edit_log import _make_aware

from tests.tests import ViewTests


class EditLogTestMixin:
    """Shared helpers for edit log tests."""

    def _create_edit(
        self,
        resource,
        edittype,
        timestamp,
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
            userid=str(self.admin.pk),
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


class EditLogGetTests(EditLogTestMixin, ViewTests):
    """Tests for the GET endpoint of the edit log API."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        cls.edit1 = cls._create_edit_cls(
            cls.scheme,
            "create",
            cls.base_time,
            note="Created resource",
        )
        cls.edit2 = cls._create_edit_cls(
            cls.scheme,
            "tile create",
            cls.base_time + timedelta(minutes=5),
            nodegroupid=SCHEME_NAME_NODEGROUP,
            tileid=uuid.uuid4(),
        )

    @classmethod
    def _create_edit_cls(
        cls,
        resource,
        edittype,
        timestamp,
        tileid=None,
        nodegroupid=None,
        newvalue=None,
        oldvalue=None,
        note=None,
    ):
        """classmethod variant of _create_edit for use in setUpTestData."""
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

    def test_get_edit_log(self):
        url = reverse("api-lingo-edit-log", args=[self.scheme.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data["resourceid"], str(self.scheme.pk))
        self.assertIsInstance(data["edits"], list)
        self.assertGreaterEqual(len(data["edits"]), 2)

        # Verify edits are ordered by timestamp descending
        # (the tile create at +5min should come first)
        edit_types = [e["edittype"] for e in data["edits"]]
        tile_create_idx = edit_types.index("tile create")
        create_idx = edit_types.index("create")
        self.assertLess(tile_create_idx, create_idx)

    def test_get_edit_log_fields(self):
        url = reverse("api-lingo-edit-log", args=[self.scheme.pk])
        response = self.client.get(url)
        data = json.loads(response.content)

        # Find the "create" edit
        create_edit = next(e for e in data["edits"] if e["edittype"] == "create")
        self.assertEqual(create_edit["edittype_label"], "Resource Created")
        self.assertEqual(create_edit["user_username"], "admin")
        self.assertIsNotNone(create_edit["timestamp"])
        self.assertIsNotNone(create_edit["editlogid"])
        self.assertEqual(create_edit["note"], "Created resource")
        self.assertIsNone(create_edit["nodegroupid"])
        self.assertIsNone(create_edit["card_name"])

    def test_get_edit_log_tile_edit_has_card_name(self):
        url = reverse("api-lingo-edit-log", args=[self.scheme.pk])
        response = self.client.get(url)
        data = json.loads(response.content)

        tile_edit = next(e for e in data["edits"] if e["edittype"] == "tile create")
        self.assertEqual(tile_edit["nodegroupid"], SCHEME_NAME_NODEGROUP)
        # Card name should be resolved from card_lookup
        # (may be None if the nodegroup doesn't have a card, but field must exist)
        self.assertIn("card_name", tile_edit)

    def test_get_edit_log_edit_type_labels(self):
        """Test that known edit types get human-readable labels."""
        url = reverse("api-lingo-edit-log", args=[self.scheme.pk])
        response = self.client.get(url)
        data = json.loads(response.content)

        create_edit = next(e for e in data["edits"] if e["edittype"] == "create")
        self.assertEqual(create_edit["edittype_label"], "Resource Created")

        tile_create_edit = next(
            e for e in data["edits"] if e["edittype"] == "tile create"
        )
        self.assertEqual(tile_create_edit["edittype_label"], "Tile Created")

    def test_get_edit_log_resource_not_found(self):
        fake_id = uuid.uuid4()
        url = reverse("api-lingo-edit-log", args=[fake_id])
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_get_edit_log_unauthenticated(self):
        self.client.logout()
        url = reverse("api-lingo-edit-log", args=[self.scheme.pk])
        response = self.client.get(url)

        self.assertIn(response.status_code, [403, 302])

    def test_get_edit_log_non_admin_user(self):
        non_admin = User.objects.create_user(username="viewer", password="test123")
        self.client.force_login(non_admin)
        url = reverse("api-lingo-edit-log", args=[self.scheme.pk])
        response = self.client.get(url)

        self.assertIn(response.status_code, [403, 302])


class EditLogPostTests(EditLogTestMixin, ViewTests):
    """Tests for the POST (revert) endpoint of the edit log API."""

    TILE_PATCH_TARGET = "arches_lingo.views.api.edit_log.Tile"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.base_time = datetime(2025, 6, 1, 12, 0, 0)

    def _post_revert(self, resource, timestamp=None):
        """POST a revert request and return the response."""
        ts = (timestamp or self.base_time).isoformat()
        url = reverse("api-lingo-edit-log", args=[resource.pk])
        return self.client.post(
            url,
            data=json.dumps({"timestamp": ts}),
            content_type="application/json",
        )

    def _patch_tile(self, *, return_value=None, side_effect=None):
        """Return a context manager that patches the Tile class.

        Usage::

            with self._patch_tile(return_value=mock_tile) as MockTile:
                ...
        """
        p = patch(self.TILE_PATCH_TARGET)

        class _PatchContext:
            def __enter__(self_ctx):
                MockTile = p.__enter__()
                MockTile.DoesNotExist = RealTile.DoesNotExist
                if side_effect is not None:
                    MockTile.objects.get.side_effect = side_effect
                elif return_value is not None:
                    MockTile.objects.get.return_value = return_value
                self_ctx.MockTile = MockTile
                return MockTile

            def __exit__(self_ctx, *args):
                return p.__exit__(*args)

        return _PatchContext()

    def test_revert_deletes_tile_created_after_target(self):
        """Tiles created after target timestamp should be deleted on revert."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Extra label"},
        )

        mock_tile = MagicMock()
        with self._patch_tile(return_value=mock_tile):
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")
        mock_tile.delete.assert_called_once()

    def test_revert_restores_tile_to_earlier_state(self):
        """Tiles edited after target timestamp should be reverted to earlier data."""
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

        # Edit log: created before target, edited after target
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
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(mock_tile.data, original_data)
        mock_tile.save.assert_called_once()

    def test_revert_handles_tile_deleted_before_target(self):
        """If a tile was deleted at or before target timestamp, it should not
        exist after revert (delete if present)."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        # Edit log shows: tile created, then deleted, both before base_time.
        # Then a tile create after base_time (e.g., it was re-created).
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

        mock_tile = MagicMock()
        with self._patch_tile(return_value=mock_tile):
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")
        mock_tile.delete.assert_called_once()

    def test_revert_no_changes_needed(self):
        """If no edits exist after the target timestamp, revert is a no-op."""
        concept = self.concepts[0]

        # Only an edit before base_time
        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=1),
            tileid=uuid.uuid4(),
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Old"},
        )

        response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")

    def test_revert_invalid_json(self):
        url = reverse("api-lingo-edit-log", args=[self.scheme.pk])
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                url,
                data="not json",
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)

    def test_revert_missing_timestamp(self):
        url = reverse("api-lingo-edit-log", args=[self.scheme.pk])
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                url,
                data=json.dumps({"other_key": "value"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)

    def test_revert_invalid_timestamp(self):
        url = reverse("api-lingo-edit-log", args=[self.scheme.pk])
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                url,
                data=json.dumps({"timestamp": "not-a-timestamp"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)

    def test_revert_resource_not_found(self):
        fake_resource = MagicMock(pk=uuid.uuid4())
        with self.assertLogs("django.request", level="WARNING"):
            response = self._post_revert(fake_resource)

        self.assertEqual(response.status_code, 404)

    def test_revert_unauthenticated(self):
        self.client.logout()
        response = self._post_revert(self.scheme)

        self.assertIn(response.status_code, [403, 302])

    def test_revert_non_admin_user(self):
        non_admin = User.objects.create_user(username="viewer2", password="test123")
        self.client.force_login(non_admin)
        response = self._post_revert(self.scheme)

        self.assertIn(response.status_code, [403, 302])

    def test_revert_naive_timestamp_treated_as_utc(self):
        """A naive timestamp (no timezone info) in the request body should
        be interpreted as UTC."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        # Create after base_time (UTC)
        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "After"},
        )

        mock_tile = MagicMock()
        naive_ts = self.base_time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._patch_tile(return_value=mock_tile):
            url = reverse("api-lingo-edit-log", args=[concept.pk])
            response = self.client.post(
                url,
                data=json.dumps({"timestamp": naive_ts}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")
        mock_tile.delete.assert_called_once()

    def test_revert_partial_success_with_nested_tile(self):
        """Reverting should report partial_success when a nested tile
        cannot be recreated."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        # Find a nodegroup that has a parent (nested).
        nested_ng = NodeGroup.objects.filter(parentnodegroup__isnull=False).first()

        if not nested_ng:
            self.skipTest("No nested nodegroup available in test data")

        # Tile was created before target (so it should exist at target time),
        # then deleted after target.
        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=2),
            tileid=tileid,
            nodegroupid=str(nested_ng.pk),
            newvalue={"some_node": "data"},
        )
        self._create_edit(
            concept,
            "tile delete",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=str(nested_ng.pk),
        )

        # The tile doesn't exist now (it was deleted after target).
        # When reverting, the code tries Tile.objects.get → DoesNotExist,
        # then finds that the nodegroup is nested → reports error.
        with self._patch_tile(side_effect=RealTile.DoesNotExist):
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "partial_success")
        self.assertTrue(len(data["errors"]) > 0)
        self.assertIn("Cannot restore nested tile", data["errors"][0])

    def test_revert_skips_edits_without_tileinstanceid(self):
        """Edits without tileinstanceid (e.g., resource create) should be
        ignored during revert, no error should occur."""
        concept = self.concepts[0]

        # Only a resource-level edit, no tile edits
        self._create_edit(
            concept,
            "create",
            self.base_time + timedelta(hours=1),
        )

        response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")

    def test_revert_tile_already_deleted(self):
        """Reverting when target tile no longer exists (already deleted)
        should not raise errors — Tile.DoesNotExist is silently caught."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        # Tile was created after base_time, but doesn't actually exist
        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Ghost"},
        )

        with self._patch_tile(side_effect=RealTile.DoesNotExist):
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")

    def test_revert_tile_delete_raises_exception(self):
        """When tile.delete() raises an unexpected exception during revert
        of a tile created after target, the error is captured."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "data"},
        )

        mock_tile = MagicMock()
        mock_tile.delete.side_effect = Exception("delete failed")
        with self._patch_tile(return_value=mock_tile):
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "partial_success")
        self.assertIn("delete failed", data["errors"][0])

    def test_revert_tile_delete_before_target_not_found(self):
        """When a tile was deleted before target and doesn't currently exist,
        Tile.DoesNotExist is silently caught (no error)."""
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
        # A later edit triggers the tile to be in the affected set
        self._create_edit(
            concept,
            "tile create",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Re-created"},
        )

        with self._patch_tile(side_effect=RealTile.DoesNotExist):
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")

    def test_revert_tile_delete_before_target_raises_exception(self):
        """When tile.delete() raises an exception during revert of a tile
        that was deleted before target, the error is captured."""
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

        mock_tile = MagicMock()
        mock_tile.delete.side_effect = Exception("cannot delete")
        with self._patch_tile(return_value=mock_tile):
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "partial_success")
        self.assertIn("cannot delete", data["errors"][0])

    def test_revert_skips_tile_with_no_target_data(self):
        """If the last edit before target has no newvalue (target_data is None),
        the tile should be skipped (continue)."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

        # Tile was created before target with no newvalue
        self._create_edit(
            concept,
            "tile create",
            self.base_time - timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue=None,
        )
        # Tile was edited after target (triggers the tile to be affected)
        self._create_edit(
            concept,
            "tile edit",
            self.base_time + timedelta(hours=1),
            tileid=tileid,
            nodegroupid=CONCEPT_NAME_NODEGROUP,
            newvalue={CONCEPT_NAME_CONTENT_NODE: "Updated"},
        )

        response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")

    def test_revert_recreates_tile_for_top_level_nodegroup(self):
        """When a tile was deleted after target and its nodegroup is top-level,
        the tile should be recreated."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()
        target_data = {CONCEPT_NAME_CONTENT_NODE: "Original data"}

        # Tile existed before target, deleted after target
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

        mock_new_tile = MagicMock()
        with self._patch_tile(side_effect=RealTile.DoesNotExist) as MockTile:
            MockTile.return_value = mock_new_tile
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")
        mock_new_tile.save.assert_called_once()

    def test_revert_tile_save_raises_exception(self):
        """When tile.save() raises an exception, the error is captured."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()

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

        mock_tile = MagicMock()
        mock_tile.save.side_effect = Exception("save failed")
        with self._patch_tile(return_value=mock_tile):
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "partial_success")
        self.assertIn("Failed to update tile", data["errors"][0])

    def test_revert_restore_tile_save_fails(self):
        """When recreating a tile (top-level nodegroup) and tile.save() fails,
        the error is captured."""
        concept = self.concepts[0]
        tileid = uuid.uuid4()
        target_data = {CONCEPT_NAME_CONTENT_NODE: "Data"}

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

        mock_new_tile = MagicMock()
        mock_new_tile.save.side_effect = Exception("restore failed")
        with self._patch_tile(side_effect=RealTile.DoesNotExist) as MockTile:
            MockTile.return_value = mock_new_tile
            response = self._post_revert(concept)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "partial_success")
        self.assertIn("Failed to restore tile", data["errors"][0])


class MakeAwareTests(TestCase):
    """Tests for the _make_aware utility function."""

    def test_naive_datetime_gets_utc(self):
        naive = datetime(2025, 1, 1, 12, 0, 0)
        result = _make_aware(naive)
        self.assertEqual(result.tzinfo, timezone.utc)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.hour, 12)

    def test_aware_datetime_unchanged(self):
        aware = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _make_aware(aware)
        self.assertIs(result.tzinfo, timezone.utc)
        self.assertEqual(result, aware)

    def test_non_utc_aware_datetime_preserved(self):
        from datetime import timezone as tz

        eastern = tz(timedelta(hours=-5))
        aware = datetime(2025, 1, 1, 12, 0, 0, tzinfo=eastern)
        result = _make_aware(aware)
        self.assertEqual(result.tzinfo, eastern)
        self.assertEqual(result, aware)
