import uuid
from collections import Counter
from datetime import timedelta

from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models import models
from arches.app.models.card import Card
from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_controlled_lists.models import ListItem, ListItemValue
from arches_querysets.models import ResourceTileTree

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    CONCEPT_TYPE_NODE,
    CONCEPT_TYPE_NODEGROUP,
    EDIT_TYPE_LABELS,
    LABEL_LIST_ID,
    PREF_LABEL_URI,
    SCHEMES_GRAPH_ID,
    TILE_EDIT_TYPE_LABEL_TEMPLATES,
)
from arches_lingo.utils.concept_builder import ConceptBuilder


def _build_uri_label_map(list_id: str) -> dict:
    """Return a URI → display-label dict for all items in a controlled list.

    Uses two queries (fetch items, fetch pref labels in bulk) rather than
    one query per item, avoiding an N+1 pattern.
    """
    items = list(ListItem.objects.filter(list_id=list_id))
    pref_values = (
        ListItemValue.objects.filter(list_item__in=items, valuetype_id="prefLabel")
        .order_by("language_id")
        .values("list_item_id", "value")
    )
    # Build item_id → first pref label value
    pref_map: dict = {}
    for pref_value in pref_values:
        pref_map.setdefault(pref_value["list_item_id"], pref_value["value"])
    return {item.uri: pref_map.get(item.id, str(item.id)) for item in items}


def _parse_scheme_ids(request) -> tuple:
    """Parse and validate ``scheme`` query params as UUID strings.

    Returns ``(scheme_ids, None)`` on success or ``([], error_response)``
    when any value is not a valid UUID.
    """
    scheme_ids = []
    for param in request.GET.getlist("scheme"):
        try:
            scheme_ids.append(str(uuid.UUID(param)))
        except ValueError:
            return [], JSONErrorResponse(
                title=_("Invalid scheme"),
                message=_("scheme must be a valid UUID"),
                status=400,
            )
    return scheme_ids, None


def _get_label_stats(concept_resource_ids: list) -> tuple:
    """Return ``(label_count, labels_by_type, labels_by_language)`` for a
    set of concept resource IDs.
    """
    tiles = models.TileModel.objects.filter(
        nodegroup_id=CONCEPT_NAME_NODEGROUP,
        resourceinstance_id__in=concept_resource_ids,
    ).values_list("data", flat=True)

    type_counter: Counter = Counter()
    lang_counter: Counter = Counter()
    total = 0

    for data in tiles:
        total += 1
        lang = data.get(CONCEPT_NAME_LANGUAGE_NODE)
        if lang:
            lang_counter[lang] += 1
        ref_values = data.get(CONCEPT_NAME_TYPE_NODE)
        if ref_values and isinstance(ref_values, list):
            for ref in ref_values:
                uri = ref.get("uri")
                if uri:
                    type_counter[uri] += 1

    uri_label_map = _build_uri_label_map(LABEL_LIST_ID)

    labels_by_type = [
        {"label": uri_label_map.get(uri, uri), "uri": uri, "count": count}
        for uri, count in type_counter.items()
    ]
    labels_by_type.sort(key=lambda entry: entry["label"])

    lang_codes = list(lang_counter.keys())
    lang_name_map: dict = {}
    if lang_codes:
        for lang_obj in models.Language.objects.filter(code__in=lang_codes):
            lang_name_map[lang_obj.code] = lang_obj.name or lang_obj.code

    labels_by_language = [
        {"language": lang_name_map.get(code, code), "code": code, "count": count}
        for code, count in lang_counter.items()
    ]
    labels_by_language.sort(key=lambda entry: -entry["count"])

    return total, labels_by_type, labels_by_language


def _get_concept_type_breakdown(concept_resource_ids: list) -> list:
    """Return a list of ``{label, uri, count}`` dicts for each concept type.

    Concepts with no type tile are counted under an "Untyped" bucket.
    """
    type_node = models.Node.objects.get(nodeid=CONCEPT_TYPE_NODE)
    controlled_list_id = type_node.config.get("controlledList")
    if not controlled_list_id:
        return []

    uri_label_map = _build_uri_label_map(controlled_list_id)

    uri_counter: Counter = Counter()
    typed_resource_ids: set = set()

    type_tiles = models.TileModel.objects.filter(
        nodegroup_id=CONCEPT_TYPE_NODEGROUP,
        resourceinstance_id__in=concept_resource_ids,
    ).values_list("resourceinstance_id", "data")

    for resource_id, data in type_tiles:
        ref_values = data.get(CONCEPT_TYPE_NODE) if data else None
        if ref_values and isinstance(ref_values, list):
            for ref in ref_values:
                uri = ref.get("uri")
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


def _get_concept_ids(scheme_ids: list) -> tuple:
    """Return ``(concept_count, concept_ids_as_strings)`` for the given
    scheme filter.  When *scheme_ids* is empty, all concepts are returned.
    """
    if scheme_ids:
        concept_qs = ResourceTileTree.get_tiles("concept").filter(
            part_of_scheme__id__in=scheme_ids,
        )
        concept_count = concept_qs.count()
        concept_ids_list = [str(pk) for pk in concept_qs.values_list("pk", flat=True)]
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


def _get_all_scheme_ids() -> list:
    """Return all scheme resource IDs as strings."""
    return [
        str(pk)
        for pk in models.ResourceInstance.objects.filter(
            graph_id=SCHEMES_GRAPH_ID
        ).values_list("pk", flat=True)
    ]


def _build_resource_type_map(resource_ids: list) -> dict:
    """Return a ``{resource_id_str: "scheme"|"concept"}`` mapping."""
    type_map: dict = {}
    for resource in models.ResourceInstance.objects.filter(
        resourceinstanceid__in=resource_ids
    ):
        type_map[str(resource.resourceinstanceid)] = (
            "scheme" if str(resource.graph_id) == str(SCHEMES_GRAPH_ID) else "concept"
        )
    return type_map


def _build_recent_activity(
    all_resource_ids: list,
    type_map: dict,
    since,
    *,
    max_items: int = 20,
    fetch_limit: int = 100,
) -> list:
    """Return the *max_items* most recent edits, deduplicated by transaction.

    Each entry is a dict ready for JSON serialisation.
    """
    edit_qs = models.EditLog.objects.filter(
        resourceinstanceid__in=all_resource_ids,
    ).order_by("-timestamp")
    if since:
        edit_qs = edit_qs.filter(timestamp__gte=since)
    edits = edit_qs[:fetch_limit]

    # Build nodegroup ID → card name map for action labels
    nodegroup_ids = {edit.nodegroupid for edit in edits if edit.nodegroupid}
    card_lookup: dict = {}
    if nodegroup_ids:
        for card in Card.objects.filter(nodegroup_id__in=nodegroup_ids):
            card_lookup[str(card.nodegroup_id)] = card.name

    seen_transactions: set = set()
    activity: list = []
    for edit in edits:
        dedup_key = (
            str(edit.transactionid) if edit.transactionid else str(edit.editlogid)
        )
        if dedup_key in seen_transactions:
            continue
        seen_transactions.add(dedup_key)

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


def _attach_activity_labels(activity: list) -> None:
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


def _parse_days_param(request):
    """Parse the optional ``days`` query param.

    Returns ``(since_datetime_or_None, None)`` on success or
    ``(None, error_response)`` on invalid input.
    """
    days_param = request.GET.get("days")
    if days_param is None:
        return None, None
    try:
        days_int = int(days_param)
    except ValueError:
        return None, JSONErrorResponse(
            title=_("Invalid parameter"),
            message=_("days must be an integer"),
            status=400,
        )
    if days_int > 0:
        return timezone.now() - timedelta(days=days_int), None
    return None, None


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class DashboardStatsView(View):
    def get(self, request):
        scheme_ids, error = _parse_scheme_ids(request)
        if error:
            return error

        user = request.user
        user_display_name = (
            user.first_name or user.username if user.is_authenticated else ""
        )

        total_scheme_count = models.ResourceInstance.objects.filter(
            graph_id=SCHEMES_GRAPH_ID
        ).count()
        scheme_count = len(scheme_ids) if scheme_ids else total_scheme_count

        concept_count, concept_ids_list = _get_concept_ids(scheme_ids)

        resolved_scheme_ids = scheme_ids or _get_all_scheme_ids()
        all_resource_ids = concept_ids_list + resolved_scheme_ids

        type_map = _build_resource_type_map(all_resource_ids)

        since, error = _parse_days_param(request)
        if error:
            return error

        activity = _build_recent_activity(all_resource_ids, type_map, since)
        _attach_activity_labels(activity)

        concept_uuids = [uuid.UUID(rid) for rid in concept_ids_list]
        concepts_by_type = _get_concept_type_breakdown(concept_uuids)
        label_count, labels_by_type, labels_by_language = _get_label_stats(
            concept_uuids
        )

        labels_per_concept = (
            round(label_count / concept_count, 1) if concept_count else 0
        )

        return JSONResponse(
            {
                "user_display_name": user_display_name,
                "scheme_count": scheme_count,
                "concept_count": concept_count,
                "concepts_by_type": concepts_by_type,
                "label_count": label_count,
                "labels_per_concept": labels_per_concept,
                "labels_by_type": labels_by_type,
                "labels_by_language": labels_by_language,
                "recent_activity": activity,
            }
        )


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class MissingTranslationsView(View):
    def get(self, request):
        language_code = request.GET.get("language")
        if not language_code:
            return JSONErrorResponse(
                title=_("Missing parameter"),
                message=_("language parameter is required"),
                status=400,
            )

        scheme_ids, error = _parse_scheme_ids(request)
        if error:
            return error

        page_number = int(request.GET.get("page", 1))
        items_per_page = int(request.GET.get("items", 25))

        concepts_with_pref_ids = set(
            models.TileModel.objects.filter(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data__contains={
                    CONCEPT_NAME_LANGUAGE_NODE: language_code,
                    CONCEPT_NAME_TYPE_NODE: [{"uri": PREF_LABEL_URI}],
                },
            ).values_list("resourceinstance_id", flat=True)
        )

        _concept_count, all_concept_id_strings = _get_concept_ids(scheme_ids)
        all_concept_ids = [uuid.UUID(pk) for pk in all_concept_id_strings]

        missing_ids = [
            str(pk) for pk in all_concept_ids if pk not in concepts_with_pref_ids
        ]
        missing_ids.sort()

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

        return JSONResponse(
            {
                "current_page": page.number,
                "total_pages": paginator.num_pages,
                "results_per_page": paginator.per_page,
                "total_results": total_results,
                "data": data,
            }
        )
