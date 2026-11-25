import datetime
import uuid

from django.urls import reverse

from arches.app.models.models import (
    EditLog,
    ResourceInstance,
    ResourceXResource,
    TileModel,
)

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,
    RELATION_STATUS_NODEGROUP,
)
from arches_lingo.utils.concept_lifecycle import DRAFT_STATE_ID, PUBLISHED_STATE_ID
from arches_lingo.utils.scheme_deletion import SchemeDeletionError, delete_scheme
from tests.tests import SchemeWithConceptsTestCase

# These tests can be run from the command line via:
# python manage.py test tests.test_scheme_deletion --settings="tests.test_settings"


class SchemeDeletionTests(SchemeWithConceptsTestCase):
    def setUp(self):
        super().setUp()
        ResourceInstance.objects.filter(
            pk__in=[self.scheme.pk, *[concept.pk for concept in self.concepts]]
        ).update(resource_instance_lifecycle_state_id=DRAFT_STATE_ID)
        self.scheme.refresh_from_db()

    def create_outside_concept_related_to(self, related_concept):
        outside_concept = ResourceInstance.objects.create(
            graph_id=CONCEPTS_GRAPH_ID, name="Outside Concept"
        )
        relation_tile = TileModel.objects.create(
            resourceinstance=outside_concept,
            nodegroup_id=RELATION_STATUS_NODEGROUP,
            data={},
        )
        relationship = ResourceXResource.objects.create(
            from_resource=outside_concept,
            to_resource=related_concept,
            tile=relation_tile,
            node_id=RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        relation_tile.data = {
            RELATION_STATUS_ASCRIBED_COMPARATE_NODEID: [
                {
                    "resourceId": str(related_concept.pk),
                    "resourceXresourceId": str(relationship.pk),
                }
            ]
        }
        relation_tile.save()
        return outside_concept, relation_tile

    def test_deletes_scheme_with_its_concepts_and_references_to_them(self):
        outside_concept, relation_tile = self.create_outside_concept_related_to(
            self.concepts[0]
        )
        deleted_resource_ids = {self.scheme.pk, *[c.pk for c in self.concepts]}

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(
                reverse("api-lingo-scheme-delete", kwargs={"pk": self.scheme.pk})
            )

        self.assertEqual(response.json(), {"deleted_concept_count": len(self.concepts)})
        self.assertFalse(
            ResourceInstance.objects.filter(pk__in=deleted_resource_ids).exists()
        )
        self.assertTrue(ResourceInstance.objects.filter(pk=outside_concept.pk).exists())
        relation_tile.refresh_from_db()
        self.assertEqual(
            relation_tile.data[RELATION_STATUS_ASCRIBED_COMPARATE_NODEID], []
        )
        self.assertEqual(
            set(
                EditLog.objects.filter(edittype="delete").values_list(
                    "resourceinstanceid", flat=True
                )
            ),
            {str(resource_id) for resource_id in deleted_resource_ids},
        )

    def test_refuses_a_scheme_that_is_not_in_draft(self):
        ResourceInstance.objects.filter(pk=self.scheme.pk).update(
            resource_instance_lifecycle_state_id=PUBLISHED_STATE_ID
        )

        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.delete(
                reverse("api-lingo-scheme-delete", kwargs={"pk": self.scheme.pk})
            )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(ResourceInstance.objects.filter(pk=self.scheme.pk).exists())

    def test_refuses_a_scheme_with_a_concept_that_is_not_in_draft(self):
        ResourceInstance.objects.filter(pk=self.concepts[-1].pk).update(
            resource_instance_lifecycle_state_id=PUBLISHED_STATE_ID
        )

        with self.assertRaises(SchemeDeletionError):
            delete_scheme(self.scheme, self.admin)

        self.assertEqual(
            ResourceInstance.objects.filter(
                pk__in=[c.pk for c in self.concepts]
            ).count(),
            len(self.concepts),
        )

    def test_endpoint_reports_concept_count_and_only_deletes_schemes(self):
        response = self.client.get(
            reverse("api-lingo-scheme-delete", kwargs={"pk": self.scheme.pk})
        )
        self.assertEqual(response.json(), {"concept_count": len(self.concepts)})

        for resource_id in (self.concepts[0].pk, uuid.uuid4()):
            with self.assertLogs("django.request", level="WARNING"):
                response = self.client.delete(
                    reverse("api-lingo-scheme-delete", kwargs={"pk": resource_id})
                )
            self.assertEqual(response.status_code, 404)
        self.assertTrue(
            ResourceInstance.objects.filter(pk=self.concepts[0].pk).exists()
        )
