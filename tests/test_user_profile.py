import json
from http import HTTPStatus

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from arches.app.models.models import UserProfile


# These tests can be run from the command line via:
# python manage.py test tests.test_user_profile --settings="tests.test_settings"


class UserProfileAPIViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testprofileuser",
            password="testpassword123!",
            first_name="Test",
            last_name="User",
            email="test@example.com",
        )

    def setUp(self):
        self.client.force_login(self.user)
        # Ensure a clean UserProfile state per-test (created lazily by some views)
        UserProfile.objects.filter(user=self.user).delete()

    # --- GET tests ---

    def test_get_profile_authenticated(self):
        response = self.client.get(reverse("api-lingo-user-profile"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertEqual(data["username"], "testprofileuser")
        self.assertEqual(data["first_name"], "Test")
        self.assertEqual(data["last_name"], "User")
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["phone"], "")

    def test_get_profile_with_phone(self):
        UserProfile.objects.create(user=self.user, phone="555-1234")
        response = self.client.get(reverse("api-lingo-user-profile"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertEqual(data["phone"], "555-1234")

    def test_get_profile_phone_defaults_to_empty_string_when_no_userprofile(self):
        # No UserProfile exists — phone should default to ""
        UserProfile.objects.filter(user=self.user).delete()
        response = self.client.get(reverse("api-lingo-user-profile"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertEqual(data["phone"], "")

    def test_get_profile_unauthenticated(self):
        self.client.logout()
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(reverse("api-lingo-user-profile"))
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    # --- PUT tests ---

    def test_put_profile_updates_fields(self):
        payload = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
            "phone": "555-9999",
        }
        response = self.client.put(
            reverse("api-lingo-user-profile"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertEqual(data["first_name"], "Updated")
        self.assertEqual(data["last_name"], "Name")
        self.assertEqual(data["email"], "updated@example.com")
        self.assertEqual(data["phone"], "555-9999")
        self.assertEqual(data["username"], "testprofileuser")

        # Verify DB was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(self.user.userprofile.phone, "555-9999")

    def test_put_profile_creates_userprofile_if_missing(self):
        UserProfile.objects.filter(user=self.user).delete()
        payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone": "555-0000",
        }
        response = self.client.put(
            reverse("api-lingo-user-profile"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())
        self.user.refresh_from_db()
        self.assertEqual(self.user.userprofile.phone, "555-0000")

    def test_put_profile_phone_defaults_to_empty_string(self):
        payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
        }
        response = self.client.put(
            reverse("api-lingo-user-profile"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertEqual(data["phone"], "")

    def test_put_profile_unauthenticated(self):
        self.client.logout()
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.put(
                reverse("api-lingo-user-profile"),
                data=json.dumps(
                    {"first_name": "X", "last_name": "Y", "email": "x@y.com"}
                ),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_put_profile_invalid_json(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.put(
                reverse("api-lingo-user-profile"),
                data="not valid json",
                content_type="application/json",
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_put_profile_missing_first_name(self):
        payload = {"first_name": "", "last_name": "User", "email": "test@example.com"}
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.put(
                reverse("api-lingo-user-profile"),
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_put_profile_missing_last_name(self):
        payload = {"first_name": "Test", "last_name": "", "email": "test@example.com"}
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.put(
                reverse("api-lingo-user-profile"),
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_put_profile_missing_email(self):
        payload = {"first_name": "Test", "last_name": "User", "email": ""}
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.put(
                reverse("api-lingo-user-profile"),
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)


class ChangePasswordAPIViewTests(TestCase):
    PASSWORD = "OldSecurePass1!"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testpassworduser",
            password=cls.PASSWORD,
            first_name="Pass",
            last_name="Word",
            email="pass@example.com",
        )

    def setUp(self):
        # Re-set the password each test since some tests change it
        self.user.set_password(self.PASSWORD)
        self.user.save()
        self.client.force_login(self.user)

    def _post(self, payload):
        return self.client.post(
            reverse("api-lingo-change-password"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    # --- POST tests ---

    def test_change_password_success(self):
        new_password = "NewSecurePass2!"
        response = self._post(
            {
                "old_password": self.PASSWORD,
                "new_password": new_password,
                "new_password2": new_password,
            }
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertIn("success", data)

        # Verify the password actually changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_change_password_unauthenticated(self):
        self.client.logout()
        with self.assertLogs("django.request", level="WARNING"):
            response = self._post(
                {
                    "old_password": self.PASSWORD,
                    "new_password": "NewSecurePass2!",
                    "new_password2": "NewSecurePass2!",
                }
            )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_change_password_invalid_json(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("api-lingo-change-password"),
                data="not valid json",
                content_type="application/json",
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_change_password_wrong_old_password(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self._post(
                {
                    "old_password": "WrongPassword!",
                    "new_password": "NewSecurePass2!",
                    "new_password2": "NewSecurePass2!",
                }
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = json.loads(response.content)
        self.assertIn("incorrect", data["message"].lower())

    def test_change_password_mismatch(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self._post(
                {
                    "old_password": self.PASSWORD,
                    "new_password": "NewSecurePass2!",
                    "new_password2": "DifferentPass3!",
                }
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = json.loads(response.content)
        self.assertIn("match", data["message"].lower())

    def test_change_password_fails_validation(self):
        # Django's default validators reject passwords that are too short or too common
        with self.assertLogs("django.request", level="WARNING"):
            response = self._post(
                {
                    "old_password": self.PASSWORD,
                    "new_password": "short",
                    "new_password2": "short",
                }
            )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = json.loads(response.content)
        self.assertIn("validation", data["title"].lower())
