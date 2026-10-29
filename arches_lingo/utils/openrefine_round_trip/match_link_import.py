"""Writing exactMatch/closeMatch/relatedMatch links from an uploaded CSV.

The import only ever adds links: it never deletes or overwrites, and a link a
concept already records is skipped, so uploading the same file twice is harmless.
"""

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from arches.app.models.models import EditLog, ResourceInstance
from arches.app.tasks import notify_completion

from arches_lingo.const import (
    LINKABLE_MATCH_TYPES,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
)
from arches_lingo.models import MatchLinkImport
from arches_lingo.utils.concept_lifecycle import index_concepts_in_transaction
from arches_lingo.utils.concept_merge.tiles import (
    create_tile_on_concept,
    get_list_item_tile_value,
    load_concept_resources,
)
from arches_lingo.utils.openrefine_round_trip.match_link_validation import (
    OUTCOME_ADD,
    canonical_concept_id,
    count_outcomes,
    validate_match_links,
)

logger = logging.getLogger(__name__)


def claim_match_link_import(match_link_import):
    """Move a pending import to running; False if it was already taken or
    given up on, so a late or repeated worker never applies it a second time."""
    is_claimed = MatchLinkImport.objects.filter(
        pk=match_link_import.pk, status=MatchLinkImport.STATUS_PENDING
    ).update(status=MatchLinkImport.STATUS_RUNNING, started=timezone.now())
    match_link_import.refresh_from_db()
    return bool(is_claimed)


def lock_concepts_of_links(match_links):
    """Two imports running at once must not both decide the same link is new."""
    concept_ids = {
        canonical_concept_id(match_link.get("concept_id")) for match_link in match_links
    }
    list(
        ResourceInstance.objects.select_for_update()
        .filter(pk__in=concept_ids - {None})
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def attribute_edits_to_user(edit_transaction_id, user):
    """create_tile_on_concept saves tiles without a user to keep them out of
    provisional edits, so the importer is named on the edit log afterwards."""
    if user is None:
        return
    EditLog.objects.filter(transactionid=edit_transaction_id).update(
        userid=str(user.pk),
        user_email=user.email,
        user_firstname=user.first_name,
        user_lastname=user.last_name,
        user_username=user.username,
    )


def apply_match_link_import(match_link_import):
    """Validate the stored links again (state may have changed since the
    preview) and write them in one edit transaction.

    The record is saved as soon as the links commit, so its
    ``edit_transaction_id`` survives a failure while indexing them.
    """
    if not claim_match_link_import(match_link_import):
        logger.warning(
            "Match link import %s is %s, not pending; not applying it.",
            match_link_import.pk,
            match_link_import.status,
        )
        return match_link_import
    edit_transaction_id = uuid.uuid4()
    links_to_add = []
    try:
        relation_tile_value_by_match_type = {
            match_type: get_list_item_tile_value(list_item_id)
            for match_type, list_item_id in LINKABLE_MATCH_TYPES.items()
        }
        with transaction.atomic():
            lock_concepts_of_links(match_link_import.links)
            validated_links = validate_match_links(
                match_link_import.links,
                match_link_import.user,
                match_link_import.scheme_id,
            )
            links_to_add = [
                validated_link
                for validated_link in validated_links
                if validated_link["outcome"] == OUTCOME_ADD
            ]
            resource_by_concept_id = load_concept_resources(
                *{link_to_add["concept_id"] for link_to_add in links_to_add}
            )
            for link_to_add in links_to_add:
                create_tile_on_concept(
                    link_to_add["concept_id"],
                    MATCH_STATUS_NODEGROUP,
                    {
                        MATCH_STATUS_RELATION_NODE: [
                            relation_tile_value_by_match_type[link_to_add["match_type"]]
                        ],
                        MATCH_STATUS_COMPARATE_NODE: link_to_add["match_uri"],
                    },
                    None,
                    edit_transaction_id,
                    resource_by_concept_id[link_to_add["concept_id"]],
                )
            attribute_edits_to_user(edit_transaction_id, match_link_import.user)
        if links_to_add:
            match_link_import.edit_transaction_id = edit_transaction_id
        match_link_import.outcome_counts = count_outcomes(validated_links)
        match_link_import.status = MatchLinkImport.STATUS_COMPLETE
    except Exception:
        logger.exception("Match link import %s failed", match_link_import.pk)
        match_link_import.status = MatchLinkImport.STATUS_FAILED
        match_link_import.error_code = MatchLinkImport.ERROR_APPLY_FAILED
    match_link_import.finished = timezone.now()
    match_link_import.save()

    if match_link_import.status == MatchLinkImport.STATUS_COMPLETE and links_to_add:
        try:
            index_concepts_in_transaction(edit_transaction_id)
        except Exception:
            logger.exception(
                "Match link import %s could not index its concepts",
                match_link_import.pk,
            )
            match_link_import.error_code = MatchLinkImport.ERROR_INDEXING_FAILED
            match_link_import.save(update_fields=["error_code"])

    notify_requester(match_link_import)
    return match_link_import


def notify_requester(match_link_import):
    """The requester may have closed the dialog while the import ran."""
    if not match_link_import.user:
        return
    with translation.override(match_link_import.language or settings.LANGUAGE_CODE):
        if match_link_import.status == MatchLinkImport.STATUS_COMPLETE:
            added_count = match_link_import.outcome_counts.get(OUTCOME_ADD, 0)
            message = ngettext(
                "Match link import finished: %(count)s link added",
                "Match link import finished: %(count)s links added",
                added_count,
            ) % {"count": added_count}
        else:
            message = _("Match link import failed")
    notify_completion(message, match_link_import.user)
