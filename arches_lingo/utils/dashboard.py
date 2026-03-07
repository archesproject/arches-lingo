"""Service-layer helpers for the Lingo dashboard and missing-translations APIs."""

import uuid
from collections import Counter
from datetime import timedelta

from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.translation import gettext as _

from arches.app.models import models
from arches.app.models.card import Card

from arches_controlled_lists.models import ListItem, ListItemValue
from arches_querysets.models import ResourceTileTree

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    CONCEPT_TYPE_NODEID,
    CONCEPT_TYPE_NODEGROUP,
    EDIT_TYPE_LABELS,
    LABEL_LIST_ID,
    PREF_LABEL_URI,
    SCHEMES_GRAPH_ID,
    TILE_EDIT_TYPE_LABEL_TEMPLATES,
)
from arches_lingo.utils.concept_builder import ConceptBuilder


def build_uri_label_map(list_id: str) -> dict:
    """Return a URI -> display-label mapping for all items in a controlled list."""
    items = list(ListItem.objects.filter(list_id=list_id))
    preferred_values = (
        ListItemValue.objects.filter(list_item__in=items, valuetype_id="prefLabel")
        .order_by("language_id")
        .values("list_item_id", "value")
    )
    preferred_label_map: dict = {}
    for preferred_value in preferred_values:
        preferred_label_map.setdefault(
            preferred_value["list_item_id"], preferred_value["value"]
        )
    return {item.uri: preferred_label_map.get(item.id, str(item.id)) for item in items}


def parse_scheme_ids(request) -> list:
    """Parse and validate ``scheme`` query params as UUID strings."""
    scheme_ids = []
    for param in request.GET.getlist("scheme"):
        try:
            scheme_ids.append(str(uuid.UUID(param)))
        except ValueError:
            raise ValueError(_("scheme must be a valid UUID"))
    return scheme_ids


def parse_days_param(request):
    """Parse the optional ``days`` query param into a cutoff datetime."""
    days_param = request.GET.get("days")
    if days_param is None:
        return None
    try:
        days_int = int(days_param)
    except ValueError:
        raise ValueError(_("days must be an integer"))
    if days_int > 0:
        return timezone.now() - timedelta(days=days_int)
    return None


def get_concept_ids(scheme_ids: list) -> tuple:
    """Return ``(concept_count, concept_id_strings)`` for the given scheme filter."""
    if scheme_ids:
        concept_queryset = ResourceTileTree.get_tiles("concept").filter(
            part_of_scheme__id__in=scheme_ids,
        )
        concept_count = concept_queryset.count()
        concept_ids_list = [
            str(pk) for pk in concept_queryset.values_list("pk", flat=True)
        ]
    else:
        concept_count = models.ResourceInstance.objects.filter(
            graph_id=CONCEPTS_GRAPH_ID
        ).count()
        concept_ids_list = [
            str(pk)
            for pk in models.ResourceInstance.objects.filter(
                graph_id=CONCEPTS_GRAPH_ID
            ).values_list("pk", flat=True)
        ]
    return concept_count, concept_ids_list


def get_all_scheme_ids() -> list:
    """Return all scheme resource IDs as strings."""
    return [
        str(pk)
        for pk in models.ResourceInstance.objects.filter(
            graph_id=SCHEMES_GRAPH_ID
        ).values_list("pk", flat=True)
    ]


def get_label_stats(concept_resource_ids: list) -> tuple:
    """Return ``(label_count, labels_by_type, labels_by_language)`` for the given concepts."""
    tiles = models.TileModel.objects.filter(
        nodegroup_id=CONCEPT_NAME_NODEGROUP,
        resourceinstance_id__in=concept_resource_ids,
    ).values_list("data", flat=True)

    type_counter: Counter = Counter()
    language_counter: Counter = Counter()
    total = 0

    for data in tiles:
        total += 1
        language_code = data.get(CONCEPT_NAME_LANGUAGE_NODE)
        if language_code:
            language_counter[language_code] += 1
        reference_values = data.get(CONCEPT_NAME_TYPE_NODE)
        if reference_values and isinstance(reference_values, list):
            for reference_value in reference_values:
                uri = reference_value.get("uri")
                if uri:
                    type_counter[uri] += 1

    uri_label_map = build_uri_label_map(LABEL_LIST_ID)

    labels_by_type = [
        {"label": uri_label_map.get(uri, uri), "uri": uri, "count": count}
        for uri, count in type_counter.items()
    ]
    labels_by_type.sort(key=lambda entry: entry["label"])

    language_codes = list(language_counter.keys())
    language_name_map: dict = {}
    if language_codes:
        for language in models.Language.objects.filter(code__in=language_codes):
            language_name_map[language.code] = language.name or language.code

    labels_by_language = [
        {
            "language": language_name_map.get(code, code),
            "code": code,
            "count": count,
        }
        for code, count in language_counter.items()
    ]
    labels_by_language.sort(key=lambda entry: -entry["count"])

    return total, labels_by_type, labels_by_language


def get_concept_type_breakdown(concept_resource_ids: list) -> list:
    """Return a ``{label, uri, count}`` breakdown for each concept type."""
    type_node = models.Node.objects.get(nodeid=CONCEPT_TYPE_NODEID)
    controlled_list_id = type_node.config.get("controlledList")
    if not controlled_list_id:
        return []

    uri_label_map = build_uri_label_map(controlled_list_id)

    uri_counter: Counter = Counter()
    typed_resource_ids: set = set()

    type_tiles = models.TileModel.objects.filter(
        nodegroup_id=CONCEPT_TYPE_NODEGROUP,
        resourceinstance_id__in=concept_resource_ids,
    ).values_list("resourceinstance_id", "data")

    for resource_id, data in type_tiles:
        reference_values = data.get(CONCEPT_TYPE_NODEID) if data else None
        if reference_values and isinstance(reference_values, list):
            for reference_value in reference_values:
                uri = reference_value.get("uri")
                if uri:
                    uri_counter[uri] += 1
            typed_resource_ids.add(resource_id)

    untyped_count = len(concept_resource_ids) - len(typed_resource_ids)

    breakdown = [
        {"label": label, "uri": uri, "count": uri_counter.get(uri, 0)}
        for uri, label in uri_label_map.items()
    ]
    breakdown.sort(key=lambda entry: entry["label"])

    if untyped_count > 0:
        breakdown.append({"label": _("Untyped"), "uri": None, "count": untyped_count})

    return breakdown


def build_resource_type_map(resource_ids: list) -> dict:
    """Return a ``{resource_id_str: "scheme"|"concept"}`` mapping."""
    type_map: dict = {}
    for resource in models.ResourceInstance.objects.filter(
        resourceinstanceid__in=resource_ids
    ):
        type_map[str(resource.resourceinstanceid)] = (
            "scheme" if str(resource.graph_id) == str(SCHEMES_GRAPH_ID) else "concept"
        )
    return type_map


def build_recent_activity(
    all_resource_ids: list,
    type_map: dict,
    since,
    *,
    max_items: int = 20,
    fetch_limit: int = 100,
) -> list:
    """Return the *max_items* most recent edits, deduplicated by transaction."""
    edit_queryset = models.EditLog.objects.filter(
        resourceinstanceid__in=all_resource_ids,
    ).order_by("-timestamp")
    if since:
        edit_queryset = edit_queryset.filter(timestamp__gte=since)
    edits = edit_queryset[:fetch_limit]

    nodegroup_ids = {edit.nodegroupid for edit in edits if edit.nodegroupid}
    card_lookup: dict = {}
    if nodegroup_ids:
        for card in Card.objects.filter(nodegroup_id__in=nodegroup_ids):
            card_lookup[str(card.nodegroup_id)] = card.name

    seen_transactions: set = set()
    activity: list = []
    for edit in edits:
        deduplication_key = (
            str(edit.transactionid) if edit.transactionid else str(edit.editlogid)
        )
        if deduplication_key in seen_transactions:
            continue
        seen_transactions.add(deduplication_key)

        card_name = card_lookup.get(edit.nodegroupid) if edit.nodegroupid else None
        template = TILE_EDIT_TYPE_LABEL_TEMPLATES.get(edit.edittype)
        if card_name and template:
            edittype_label = str(template % {"name": card_name})
        else:
            edittype_label = str(EDIT_TYPE_LABELS.get(edit.edittype, edit.edittype))

        activity.append(
            {
                "editlogid": str(edit.editlogid),
                "edittype": edit.edittype,
                "edittype_label": edittype_label,
                "timestamp": (edit.timestamp.isoformat() if edit.timestamp else None),
                "user_username": edit.user_username,
                "user_firstname": edit.user_firstname,
                "user_lastname": edit.user_lastname,
                "resource_id": edit.resourceinstanceid,
                "resource_type": type_map.get(edit.resourceinstanceid, "concept"),
            }
        )
        if len(activity) >= max_items:
            break

    return activity


def attach_activity_labels(activity: list) -> None:
    """Mutate *activity* items in-place, adding a ``labels`` list to each."""
    concept_ids = list(
        {item["resource_id"] for item in activity if item["resource_type"] == "concept"}
    )
    scheme_ids = list(
        {item["resource_id"] for item in activity if item["resource_type"] == "scheme"}
    )

    labels_map: dict = {}
    if concept_ids or scheme_ids:
        builder = ConceptBuilder(concept_ids or [])
        if scheme_ids:
            builder.populate_schemes(scheme_ids)

        for concept_id in concept_ids:
            labels_map[concept_id] = [
                builder.serialize_concept_label(label_data)
                for label_data in builder.labels.get(concept_id, [])
            ]
        for scheme in builder.schemes:
            scheme_id = str(scheme.pk)
            labels_map[scheme_id] = [
                builder.serialize_scheme_label(label_tile)
                for label_tile in scheme.labels
            ]

    for item in activity:
        item["labels"] = labels_map.get(item["resource_id"], [])


def get_missing_translation_ids(
    language_code: str,
    scheme_ids: list,
) -> list:
    """Return sorted concept ID strings that lack a preferred label in *language_code*."""
    concepts_with_pref_ids = set(
        models.TileModel.objects.filter(
            nodegroup_id=CONCEPT_NAME_NODEGROUP,
            data__contains={
                CONCEPT_NAME_LANGUAGE_NODE: language_code,
                CONCEPT_NAME_TYPE_NODE: [{"uri": PREF_LABEL_URI}],
            },
        ).values_list("resourceinstance_id", flat=True)
    )

    _concept_count, all_concept_id_strings = get_concept_ids(scheme_ids)
    all_concept_ids = [uuid.UUID(pk) for pk in all_concept_id_strings]

    missing_ids = [
        str(pk) for pk in all_concept_ids if pk not in concepts_with_pref_ids
    ]
    missing_ids.sort()
    return missing_ids


def paginate_missing_translations(
    missing_ids: list,
    page_number: int,
    items_per_page: int,
) -> dict:
    """Paginate *missing_ids* and serialise the current page."""
    paginator = Paginator(missing_ids, items_per_page)
    page = paginator.get_page(page_number)
    total_results = paginator.count

    data = []
    if total_results:
        page_ids = list(page.object_list)
        builder = ConceptBuilder(page_ids, include_parents=True)
        data = [
            builder.serialize_concept(concept_id, parents=True, children=False)
            for concept_id in page_ids
        ]

    return {
        "current_page": page.number,
        "total_pages": paginator.num_pages,
        "results_per_page": paginator.per_page,
        "total_results": total_results,
        "data": data,
    }
