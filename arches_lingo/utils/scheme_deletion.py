import datetime
import logging
import uuid

from django.db import transaction
from django.utils.translation import gettext as _

from arches.app.models.models import (
    EditLog,
    ResourceInstance,
    ResourceXResource,
    TileModel,
)
from arches.app.models.resource import Resource
from arches.app.models.system_settings import settings
from arches.app.utils import import_class_from_string
from arches.app.utils.index_database import index_resources_using_singleprocessing

from arches_lingo.const import CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID
from arches_lingo.utils.aat.deferred_indexing import remove_resources_from_index
from arches_lingo.utils.concept_lifecycle import DRAFT_STATE_ID

logger = logging.getLogger(__name__)


class SchemeDeletionError(Exception):
    pass


def get_concept_ids_in_scheme(scheme_id):
    return set(
        TileModel.objects.filter(
            nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
            **{
                f"data__{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}__contains": [
                    {"resourceId": str(scheme_id)}
                ]
            },
        ).values_list("resourceinstance_id", flat=True)
    )


def delete_scheme(scheme, user):
    """Delete a Draft scheme together with every concept in it.

    Does in bulk what Resource.delete() does one resource at a time: references
    held by resources outside the scheme are removed from their tiles, each
    deletion is recorded in the edit log, and the search index is cleaned up
    once the deletion commits. Returns the number of concepts deleted.
    """
    if scheme.resource_instance_lifecycle_state_id != DRAFT_STATE_ID:
        raise SchemeDeletionError(_("Only schemes in Draft can be deleted."))

    concept_ids = get_concept_ids_in_scheme(scheme.pk)
    if (
        ResourceInstance.objects.filter(pk__in=concept_ids)
        .exclude(resource_instance_lifecycle_state_id=DRAFT_STATE_ID)
        .exists()
    ):
        raise SchemeDeletionError(
            _("The scheme has concepts that are not in Draft, so it cannot be deleted.")
        )

    deleted_resource_ids = {scheme.pk, *concept_ids}
    referencing_resource_ids = set()
    with transaction.atomic():
        for relationship in ResourceXResource.objects.filter(
            to_resource_id__in=deleted_resource_ids
        ).exclude(from_resource_id__in=deleted_resource_ids):
            referencing_resource_ids.add(relationship.from_resource_id)
            relationship.delete(deletedResourceId=relationship.to_resource_id)

        record_deletions_in_edit_log(deleted_resource_ids, user)
        ResourceInstance.objects.filter(pk__in=deleted_resource_ids).delete()

        transaction.on_commit(
            lambda: update_search_index_after_deletion(
                deleted_resource_ids, referencing_resource_ids
            )
        )
    return len(concept_ids)


def record_deletions_in_edit_log(resource_ids, user):
    edit_transaction_id = uuid.uuid4()
    timestamp = datetime.datetime.now()
    EditLog.objects.bulk_create(
        EditLog(
            resourceclassid=resource.graph_id,
            resourceinstanceid=resource.pk,
            edittype="delete",
            note=str(resource.name),
            timestamp=timestamp,
            transactionid=edit_transaction_id,
            userid=getattr(user, "id", ""),
            user_email=getattr(user, "email", ""),
            user_firstname=getattr(user, "first_name", ""),
            user_lastname=getattr(user, "last_name", ""),
            user_username=getattr(user, "username", ""),
        )
        for resource in ResourceInstance.objects.filter(pk__in=resource_ids).only(
            "graph_id", "name"
        )
    )


def update_search_index_after_deletion(deleted_resource_ids, referencing_resource_ids):
    remove_resources_from_index(deleted_resource_ids, log=logger.info)
    deleted_resources = [
        ResourceInstance(pk=resource_id) for resource_id in deleted_resource_ids
    ]
    for custom_index in settings.ELASTICSEARCH_CUSTOM_INDEXES:
        import_class_from_string(custom_index["module"])(
            custom_index["name"]
        ).delete_resources(resources=deleted_resources)
    if referencing_resource_ids:
        index_resources_using_singleprocessing(
            resources=Resource.objects.filter(pk__in=referencing_resource_ids),
            quiet=True,
        )
