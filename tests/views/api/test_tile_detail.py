import uuid
from http import HTTPStatus

from django.contrib.auth.models import Group, User
from django.urls import reverse

from arches.app.models.models import TileModel

from arches_lingo.const import CONCEPT_NAME_NODEGROUP, LINGO_EDITOR_GROUP_NAME
from arches_lingo.utils.concept_lifecycle import EDITING_STATE_ID, PUBLISHED_STATE_ID
from tests.tests import SchemeWithConceptsTestCase

# These tests can be run from the command line via:
# python manage.py test tests.views.api.test_tile_detail --settings="tests.test_settings"


class LingoTileDeleteTests(SchemeWithConceptsTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.editor = User.objects.create_user(
            username=f"editor_{uuid.uuid4().hex[:8]}", password="x"
        )
        # Without Resource Reviewer, arches records edits and deletes as provisional.
        cls.editor.groups.add(
            *Group.objects.filter(
                name__in=[LINGO_EDITOR_GROUP_NAME, "Resource Reviewer"]
            )
        )

    def setUp(self):
        super().setUp()
        self.client.force_login(self.editor)
        self.concept = self.concepts[0]
        self.label_tile = TileModel.objects.get(
            resourceinstance=self.concept, nodegroup_id=CONCEPT_NAME_NODEGROUP
        )

    def delete_label_tile(self, lifecycle_state_id):
        self.concept.resource_instance_lifecycle_state_id = lifecycle_state_id
        self.concept.save(update_fields=["resource_instance_lifecycle_state"])
        return self.client.delete(
            reverse(
                "api-lingo-tile",
                kwargs={
                    "graph": "concept",
                    "nodegroup_alias": "appellative_status",
                    "pk": self.label_tile.pk,
                },
            )
        )

    def test_editor_can_delete_tile_of_concept_being_edited(self):
        response = self.delete_label_tile(EDITING_STATE_ID)

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(TileModel.objects.filter(pk=self.label_tile.pk).exists())

    def test_editor_cannot_delete_tile_of_published_concept(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.delete_label_tile(PUBLISHED_STATE_ID)

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTrue(TileModel.objects.filter(pk=self.label_tile.pk).exists())
