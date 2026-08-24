import uuid
from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from arches_lingo.const import LINGO_ADMIN_GROUP_NAME, LINGO_EDITOR_GROUP_NAME
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.utils.concept_lifecycle import (
    EDITING_STATE_ID,
    LOCKED_STATE_ID,
    RETIRED_STATE_ID,
)
from arches_lingo.utils.scheme_lock import is_concept_in_locked_scheme, is_scheme_locked
from tests.tests import ViewTests

# These tests can be run from the command line via:
# python manage.py test tests.test_scheme_lock --settings="tests.test_settings"


def _make_editor():
    user = User.objects.create_user(
        username=f"editor_{uuid.uuid4().hex[:8]}", password="x"
    )
    user.groups.add(Group.objects.get(name=LINGO_EDITOR_GROUP_NAME))
    return user


def _make_lingo_admin():
    user = User.objects.create_user(
        username=f"admin_{uuid.uuid4().hex[:8]}", password="x"
    )
    user.groups.add(Group.objects.get(name=LINGO_ADMIN_GROUP_NAME))
    return user


class IsLingoAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.regular_user = User.objects.create_user(
            username="regular_ila", password="x"
        )
        cls.editor_user = _make_editor()
        cls.admin_user = _make_lingo_admin()
        cls.superuser = User.objects.get(username="admin")

    def test_superuser_is_admin(self):
        self.assertTrue(is_lingo_admin(self.superuser))

    def test_lingo_admin_group_member_is_admin(self):
        self.assertTrue(is_lingo_admin(self.admin_user))

    def test_lingo_editor_is_not_admin(self):
        self.assertFalse(is_lingo_admin(self.editor_user))

    def test_regular_user_is_not_admin(self):
        self.assertFalse(is_lingo_admin(self.regular_user))

    def test_anonymous_user_is_not_admin(self):
        self.assertFalse(is_lingo_admin(AnonymousUser()))


class IsSchemeLockedTests(SimpleTestCase):
    @patch("arches_lingo.utils.scheme_lock.ResourceInstance")
    def test_returns_true_when_lifecycle_state_is_locked(self, MockRI):
        MockRI.objects.filter.return_value.exists.return_value = True
        self.assertTrue(is_scheme_locked(uuid.uuid4()))

    @patch("arches_lingo.utils.scheme_lock.ResourceInstance")
    def test_returns_false_when_lifecycle_state_is_not_locked(self, MockRI):
        MockRI.objects.filter.return_value.exists.return_value = False
        self.assertFalse(is_scheme_locked(uuid.uuid4()))


class IsConceptInLockedSchemeTests(SimpleTestCase):
    @patch("arches_lingo.utils.scheme_lock.is_scheme_locked", return_value=True)
    @patch(
        "arches_lingo.utils.scheme_lock.get_scheme_id_for_concept",
        return_value=str(uuid.uuid4()),
    )
    def test_returns_true_when_scheme_is_locked(self, _mock_get, _mock_locked):
        self.assertTrue(is_concept_in_locked_scheme(str(uuid.uuid4())))

    @patch("arches_lingo.utils.scheme_lock.is_scheme_locked", return_value=False)
    @patch(
        "arches_lingo.utils.scheme_lock.get_scheme_id_for_concept",
        return_value=str(uuid.uuid4()),
    )
    def test_returns_false_when_scheme_is_not_locked(self, _mock_get, _mock_locked):
        self.assertFalse(is_concept_in_locked_scheme(str(uuid.uuid4())))

    @patch(
        "arches_lingo.utils.scheme_lock.get_scheme_id_for_concept",
        return_value=None,
    )
    def test_returns_false_when_concept_has_no_scheme_tile(self, _mock_get):
        self.assertFalse(is_concept_in_locked_scheme(str(uuid.uuid4())))


class _LockUsersTestMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.editor_user = _make_editor()
        cls.lingo_admin = _make_lingo_admin()

    def setUp(self):
        super().setUp()
        self.scheme.resource_instance_lifecycle_state_id = EDITING_STATE_ID
        self.scheme.save(update_fields=["resource_instance_lifecycle_state"])


class SchemeLockViewTests(_LockUsersTestMixin, ViewTests):
    """Tests for POST /api/lingo/scheme/<pk>/lock."""

    def test_non_admin_editor_cannot_lock(self):
        self.client.force_login(self.editor_user)
        response = self.client.post(
            reverse("api-scheme-lock", kwargs={"pk": self.scheme.pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_lock_nonexistent_scheme_returns_404(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-scheme-lock", kwargs={"pk": uuid.uuid4()})
            )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_cannot_lock_retired_scheme(self):
        self.scheme.resource_instance_lifecycle_state_id = RETIRED_STATE_ID
        self.scheme.save(update_fields=["resource_instance_lifecycle_state"])
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-scheme-lock", kwargs={"pk": self.scheme.pk})
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_lock_sets_scheme_to_locked_state(self):
        response = self.client.post(
            reverse("api-scheme-lock", kwargs={"pk": self.scheme.pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.scheme.refresh_from_db()
        self.assertEqual(
            self.scheme.resource_instance_lifecycle_state_id, LOCKED_STATE_ID
        )

    def test_lock_cascades_to_non_retired_concepts(self):
        concept = self.concepts[0]
        concept.resource_instance_lifecycle_state_id = EDITING_STATE_ID
        concept.save(update_fields=["resource_instance_lifecycle_state"])

        self.client.post(reverse("api-scheme-lock", kwargs={"pk": self.scheme.pk}))

        concept.refresh_from_db()
        self.assertEqual(concept.resource_instance_lifecycle_state_id, LOCKED_STATE_ID)

    def test_lock_does_not_affect_retired_concepts(self):
        retired_concept = self.concepts[0]
        retired_concept.resource_instance_lifecycle_state_id = RETIRED_STATE_ID
        retired_concept.save(update_fields=["resource_instance_lifecycle_state"])

        self.client.post(reverse("api-scheme-lock", kwargs={"pk": self.scheme.pk}))

        retired_concept.refresh_from_db()
        self.assertEqual(
            retired_concept.resource_instance_lifecycle_state_id, RETIRED_STATE_ID
        )


class SchemeUnlockViewTests(_LockUsersTestMixin, ViewTests):
    """Tests for POST /api/lingo/scheme/<pk>/unlock."""

    def _lock_scheme(self):
        self.scheme.resource_instance_lifecycle_state_id = LOCKED_STATE_ID
        self.scheme.save(update_fields=["resource_instance_lifecycle_state"])

    def test_non_admin_editor_cannot_unlock(self):
        self._lock_scheme()
        self.client.force_login(self.editor_user)
        response = self.client.post(
            reverse("api-scheme-unlock", kwargs={"pk": self.scheme.pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_unlock_nonexistent_scheme_returns_404(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-scheme-unlock", kwargs={"pk": uuid.uuid4()})
            )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_cannot_unlock_non_locked_scheme(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-scheme-unlock", kwargs={"pk": self.scheme.pk})
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_unlock_sets_scheme_to_editing_state(self):
        self._lock_scheme()
        response = self.client.post(
            reverse("api-scheme-unlock", kwargs={"pk": self.scheme.pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.scheme.refresh_from_db()
        self.assertEqual(
            self.scheme.resource_instance_lifecycle_state_id, EDITING_STATE_ID
        )

    def test_unlock_cascades_locked_concepts_to_editing(self):
        concept = self.concepts[0]
        concept.resource_instance_lifecycle_state_id = LOCKED_STATE_ID
        concept.save(update_fields=["resource_instance_lifecycle_state"])
        self._lock_scheme()

        self.client.post(reverse("api-scheme-unlock", kwargs={"pk": self.scheme.pk}))

        concept.refresh_from_db()
        self.assertEqual(concept.resource_instance_lifecycle_state_id, EDITING_STATE_ID)

    def test_unlock_does_not_change_retired_concepts(self):
        self._lock_scheme()
        retired_concept = self.concepts[0]
        retired_concept.resource_instance_lifecycle_state_id = RETIRED_STATE_ID
        retired_concept.save(update_fields=["resource_instance_lifecycle_state"])

        self.client.post(reverse("api-scheme-unlock", kwargs={"pk": self.scheme.pk}))

        retired_concept.refresh_from_db()
        self.assertEqual(
            retired_concept.resource_instance_lifecycle_state_id, RETIRED_STATE_ID
        )


class LockedSchemeViewGuardTests(_LockUsersTestMixin, ViewTests):
    """Verifies the inline lock guards in each write view."""

    def setUp(self):
        super().setUp()
        self.scheme.resource_instance_lifecycle_state_id = LOCKED_STATE_ID
        self.scheme.save(update_fields=["resource_instance_lifecycle_state"])
        self.client.force_login(self.editor_user)

    def test_retire_concept_blocked_when_scheme_locked(self):
        response = self.client.post(
            reverse("api-concept-retire", kwargs={"pk": self.concepts[0].pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.LOCKED)

    @patch("arches_lingo.views.api.concept_lifecycle.retire_concept")
    @patch(
        "arches_lingo.views.api.concept_lifecycle.get_narrower_ids",
        return_value=set(),
    )
    def test_retire_concept_allowed_for_admin_when_locked(
        self, _mock_narrower, _mock_retire
    ):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("api-concept-retire", kwargs={"pk": self.concepts[0].pk})
        )
        self.assertNotEqual(response.status_code, HTTPStatus.LOCKED)

    def test_unretire_concept_blocked_when_scheme_locked(self):
        response = self.client.post(
            reverse("api-concept-unretire", kwargs={"pk": self.concepts[0].pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.LOCKED)

    @patch("arches_lingo.views.api.concept_lifecycle.unretire_concept")
    def test_unretire_concept_allowed_for_admin_when_locked(self, _mock_unretire):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("api-concept-unretire", kwargs={"pk": self.concepts[0].pk})
        )
        self.assertNotEqual(response.status_code, HTTPStatus.LOCKED)

    def test_delete_concept_blocked_when_scheme_locked(self):
        response = self.client.delete(
            reverse("api-concept-delete", kwargs={"pk": self.concepts[0].pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.LOCKED)

    @patch("arches_lingo.views.api.concepts.delete_concept")
    @patch(
        "arches_lingo.views.api.concepts.get_narrower_ids",
        return_value=set(),
    )
    def test_delete_concept_allowed_for_admin_when_locked(
        self, _mock_narrower, _mock_delete
    ):
        self.client.force_login(self.admin)
        # Concept must be in DRAFT for delete to proceed past the state check
        self.concepts[0].resource_instance_lifecycle_state_id = EDITING_STATE_ID
        self.concepts[0].save(update_fields=["resource_instance_lifecycle_state"])
        response = self.client.delete(
            reverse("api-concept-delete", kwargs={"pk": self.concepts[0].pk})
        )
        self.assertNotEqual(response.status_code, HTTPStatus.LOCKED)

    def test_unretire_scheme_concepts_blocked_when_locked(self):
        response = self.client.post(
            reverse("api-scheme-unretire-concepts", kwargs={"pk": self.scheme.pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.LOCKED)

    def test_unretire_scheme_concepts_allowed_for_admin_when_locked(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("api-scheme-unretire-concepts", kwargs={"pk": self.scheme.pk})
        )
        self.assertNotEqual(response.status_code, HTTPStatus.LOCKED)

    def test_set_scheme_identifier_blocked_when_locked(self):
        response = self.client.post(
            reverse(
                "api-scheme-identifier",
                kwargs={"scheme_resource_instance_id": self.scheme.pk},
            ),
            data={"identifier": "test-id"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.LOCKED)

    def test_set_scheme_identifier_allowed_for_admin_when_locked(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse(
                "api-scheme-identifier",
                kwargs={"scheme_resource_instance_id": self.scheme.pk},
            ),
            data={"identifier": "test-id"},
            content_type="application/json",
        )
        self.assertNotEqual(response.status_code, HTTPStatus.LOCKED)

    def test_set_scheme_uri_template_blocked_when_locked(self):
        response = self.client.post(
            reverse(
                "api-scheme-url-template",
                kwargs={"scheme_resource_instance_id": self.scheme.pk},
            ),
            data={
                "url_template": "http://example.com/<scheme_identifier>/<concept_identifier>"
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.LOCKED)

    def test_set_scheme_uri_template_allowed_for_admin_when_locked(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse(
                "api-scheme-url-template",
                kwargs={"scheme_resource_instance_id": self.scheme.pk},
            ),
            data={
                "url_template": "http://example.com/<scheme_identifier>/<concept_identifier>"
            },
            content_type="application/json",
        )
        self.assertNotEqual(response.status_code, HTTPStatus.LOCKED)
