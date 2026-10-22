from django.conf import settings
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from arches_lingo.utils.concepts import (
    MIN_INDEXED_CONTAINS_LENGTH,
    ORDER_MODE_UNSORTED,
    build_search_queryset,
)
from arches_lingo.utils.reconciliation.candidates import MAX_QUERY_LENGTH
from arches_lingo.utils.reconciliation.concept_summaries import summarize_concepts
from arches_lingo.utils.reconciliation.manifest import list_reconcilable_schemes
from arches_lingo.utils.reconciliation.query_properties import QUERY_PROPERTY_NAMES
from arches_lingo.utils.reconciliation.visibility import (
    RECONCILABLE_LIFECYCLE_STATE_IDS,
    reconcilable_scheme_ids,
)

SUGGEST_PAGE_SIZE = 10


def parse_cursor(raw_cursor):
    if raw_cursor in (None, ""):
        return 0
    try:
        cursor = int(raw_cursor)
    except ValueError:
        raise ValueError(_("The cursor must be a non-negative integer."))
    if cursor < 0:
        raise ValueError(_("The cursor must be a non-negative integer."))
    return cursor


def page_of(items, cursor):
    return {"result": items[cursor : cursor + SUGGEST_PAGE_SIZE]}


def suggest_entities(prefix, raw_cursor=None, scheme_id=None):
    """Autocomplete reconcilable concepts by label, prefix matches first."""
    cursor = parse_cursor(raw_cursor)
    prefix = (prefix or "").strip()
    if not prefix:
        return {"result": []}
    if len(prefix) > MAX_QUERY_LENGTH:
        raise ValueError(
            _("Suggest prefixes cannot exceed %(limit)s characters.")
            % {"limit": MAX_QUERY_LENGTH}
        )

    searchable_scheme_ids = reconcilable_scheme_ids()
    if scheme_id:
        searchable_scheme_ids &= {scheme_id}

    search = build_search_queryset(
        None,
        prefix,
        0,
        ORDER_MODE_UNSORTED,
        get_language() or settings.LANGUAGE_CODE,
        settings.LANGUAGE_CODE,
        scheme_ids=searchable_scheme_ids,
        lifecycle_state_ids=RECONCILABLE_LIFECYCLE_STATE_IDS,
        prefix_only=len(prefix) < MIN_INDEXED_CONTAINS_LENGTH,
    )
    concept_ids = [
        str(concept_id) for concept_id in search[cursor : cursor + SUGGEST_PAGE_SIZE]
    ]
    summaries = summarize_concepts(concept_ids)
    return {
        "result": [
            {
                "id": concept_id,
                "name": summaries[concept_id]["name"],
                "description": summaries[concept_id]["description"],
            }
            for concept_id in concept_ids
            if concept_id in summaries
        ]
    }


def suggest_types(prefix, raw_cursor=None):
    cursor = parse_cursor(raw_cursor)
    folded_prefix = (prefix or "").strip().casefold()
    matching_types = [
        reconciliation_type
        for reconciliation_type in list_reconcilable_schemes()
        if folded_prefix in reconciliation_type["name"].casefold()
    ]
    return page_of(matching_types, cursor)


def suggest_properties(prefix, raw_cursor=None):
    cursor = parse_cursor(raw_cursor)
    folded_prefix = (prefix or "").strip().casefold()
    matching_properties = [
        {"id": property_id, "name": str(property_name)}
        for property_id, property_name in QUERY_PROPERTY_NAMES.items()
        if folded_prefix in property_id.casefold()
        or folded_prefix in str(property_name).casefold()
    ]
    return page_of(matching_properties, cursor)


SUGGEST_SERVICES = {
    "entity": suggest_entities,
    "type": suggest_types,
    "property": suggest_properties,
}
