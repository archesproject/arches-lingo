import json
import uuid
from http import HTTPStatus

from django.contrib.auth.models import Group, User
from django.urls import reverse

from arches_lingo.const import LINGO_ADMIN_GROUP_NAME, LINGO_EDITOR_GROUP_NAME
from arches_lingo.models import SchemeAttribution
from tests.tests import ViewTests

# These tests can be run from the command line via:
# python manage.py test tests.views.api.test_scheme_attribution --settings="tests.test_settings"


class SchemeAttributionViewTests(ViewTests):
    """Tests for GET/POST /api/lingo/scheme/<scheme_resource_instance_id>/attribution."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.editor_user = User.objects.create_user(
            username=f"editor_{uuid.uuid4().hex[:8]}", password="x"
        )
        cls.editor_user.groups.add(Group.objects.get(name=LINGO_EDITOR_GROUP_NAME))
        cls.lingo_admin = User.objects.create_user(
            username=f"admin_{uuid.uuid4().hex[:8]}", password="x"
        )
        cls.lingo_admin.groups.add(Group.objects.get(name=LINGO_ADMIN_GROUP_NAME))

    def attribution_url(self):
        return reverse(
            "api-scheme-attribution",
            kwargs={"scheme_resource_instance_id": self.scheme.pk},
        )

    def post_attribution(self, attribution):
        return self.client.post(
            self.attribution_url(),
            data=json.dumps({"attribution": attribution}),
            content_type="application/json",
        )

    def test_non_admin_editor_cannot_create_attribution(self):
        self.client.force_login(self.editor_user)
        response = self.post_attribution("Attributed to an editor")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertFalse(
            SchemeAttribution.objects.filter(scheme_id=self.scheme.pk).exists()
        )

    def test_non_admin_editor_cannot_edit_or_delete_attribution(self):
        SchemeAttribution.objects.create(
            scheme_id=self.scheme.pk, attribution="Original attribution"
        )
        self.client.force_login(self.editor_user)

        for attempted_attribution in ("Edited attribution", ""):
            with self.subTest(attribution=attempted_attribution):
                response = self.post_attribution(attempted_attribution)

                self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
                self.assertEqual(
                    SchemeAttribution.objects.get(scheme_id=self.scheme.pk).attribution,
                    "Original attribution",
                )

    def test_non_admin_editor_can_read_attribution(self):
        SchemeAttribution.objects.create(
            scheme_id=self.scheme.pk, attribution="Original attribution"
        )
        self.client.force_login(self.editor_user)

        response = self.client.get(self.attribution_url())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            json.loads(response.content)["attribution"], "Original attribution"
        )

    def test_lingo_admin_can_create_edit_and_delete_attribution(self):
        self.client.force_login(self.lingo_admin)

        create_response = self.post_attribution("Attributed to an admin")
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        self.assertEqual(
            SchemeAttribution.objects.get(scheme_id=self.scheme.pk).attribution,
            "Attributed to an admin",
        )

        edit_response = self.post_attribution("Edited by an admin")
        self.assertEqual(edit_response.status_code, HTTPStatus.OK)
        self.assertEqual(
            SchemeAttribution.objects.get(scheme_id=self.scheme.pk).attribution,
            "Edited by an admin",
        )

        delete_response = self.post_attribution("")
        self.assertEqual(delete_response.status_code, HTTPStatus.OK)
        self.assertEqual(
            SchemeAttribution.objects.get(scheme_id=self.scheme.pk).attribution, ""
        )
