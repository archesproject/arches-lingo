import uuid
from collections import Counter

from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models import models
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
    LABEL_LIST_ID,
    SCHEMES_GRAPH_ID,
)
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.views.api.edit_log import EDIT_TYPE_LABELS

PREF_LABEL_URI = "http://www.w3.org/2004/02/skos/core#prefLabel"


def _get_label_stats(concept_resource_ids):
    """Return label_count, labels_by_type, and labels_by_language.

    labels_by_type uses the controlled list at LABEL_LIST_ID for human labels.
    labels_by_language uses Language.code → Language.name for display.
    """
    tiles = models.TileModel.objects.filter(
        nodegroup_id=CONCEPT_NAME_NODEGROUP,
        resourceinstance_id__in=concept_resource_ids,
    ).values_list("data", flat=True)

    type_counter = Counter()
    lang_counter = Counter()
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

    # Build URI → label map from the label controlled list
    label_items = ListItem.objects.filter(list_id=LABEL_LIST_ID)
    uri_label_map = {}
    for item in label_items:
        pref = (
            ListItemValue.objects.filter(list_item=item, valuetype_id="prefLabel")
            .order_by("language_id")
            .first()
        )
        uri_label_map[item.uri] = pref.value if pref else str(item.id)

    labels_by_type = [
        {"label": uri_label_map.get(uri, uri), "uri": uri, "count": count}
        for uri, count in type_counter.items()
    ]
    labels_by_type.sort(key=lambda x: x["label"])

    # Build language code → display name map
    lang_codes = list(lang_counter.keys())
    lang_name_map = {}
    if lang_codes:
        for lang_obj in models.Language.objects.filter(code__in=lang_codes):
            lang_name_map[lang_obj.code] = lang_obj.name or lang_obj.code

    labels_by_language = [
        {"language": lang_name_map.get(code, code), "code": code, "count": count}
        for code, count in lang_counter.items()
    ]
    labels_by_language.sort(key=lambda x: -x["count"])

    return total, labels_by_type, labels_by_language


def _get_concept_type_breakdown(concept_resource_ids):
    """Return a list of {label, uri, count} dicts for each concept type list item.

    Concepts that have no type tile are counted under an "Untyped" bucket.
    The controlled list is discovered dynamically from the type node's config.
    """
    type_node = models.Node.objects.get(nodeid=CONCEPT_TYPE_NODE)
    controlled_list_id = type_node.config.get("controlledList")
    if not controlled_list_id:
        return []

    # Build a map of URI → label from the controlled list
    items = ListItem.objects.filter(list_id=controlled_list_id)
    uri_label_map = {}
    for item in items:
        pref = (
            ListItemValue.objects.filter(list_item=item, valuetype_id="prefLabel")
            .order_by("language_id")
            .first()
        )
        label = pref.value if pref else str(item.id)
        uri_label_map[item.uri] = label

    # Count concepts by the URI stored in their type tile
    uri_counter = Counter()
    typed_resource_ids = set()

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

    breakdown = []
    for uri, label in uri_label_map.items():
        breakdown.append({"label": label, "uri": uri, "count": uri_counter.get(uri, 0)})
    # Sort by label for consistent ordering
    breakdown.sort(key=lambda x: x["label"])

    if untyped_count > 0:
        breakdown.append({"label": _("Untyped"), "uri": None, "count": untyped_count})

    return breakdown


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class DashboardStatsView(View):
    def get(self, request):
        scheme_params = request.GET.getlist("scheme")
        scheme_ids = []
        for param in scheme_params:
            try:
                scheme_ids.append(str(uuid.UUID(param)))
            except ValueError:
                return JSONErrorResponse(
                    title=_("Invalid scheme"),
                    message=_("scheme must be a valid UUID"),
                    status=400,
                )

        # --- User greeting ---
        user = request.user
        user_display_name = (
            user.first_name or user.username if user.is_authenticated else ""
        )

        # --- Scheme count ---
        total_scheme_count = models.ResourceInstance.objects.filter(
            graph_id=SCHEMES_GRAPH_ID
        ).count()
        scheme_count = len(scheme_ids) if scheme_ids else total_scheme_count

        # --- Concept count ---
        Concept = ResourceTileTree.get_tiles("concept")
        if scheme_ids:
            concept_count = Concept.filter(part_of_scheme__id__in=scheme_ids).count()
        else:
            concept_count = models.ResourceInstance.objects.filter(
                graph_id=CONCEPTS_GRAPH_ID
            ).count()

        # --- Resource IDs for activity query ---
        if scheme_ids:
            concept_ids_list = [
                str(pk)
                for pk in Concept.filter(part_of_scheme__id__in=scheme_ids).values_list(
                    "pk", flat=True
                )
            ]
            all_resource_ids = concept_ids_list + scheme_ids
        else:
            concept_ids_list = [
                str(pk)
                for pk in models.ResourceInstance.objects.filter(
                    graph_id=CONCEPTS_GRAPH_ID
                ).values_list("pk", flat=True)
            ]
            all_scheme_ids = [
                str(pk)
                for pk in models.ResourceInstance.objects.filter(
                    graph_id=SCHEMES_GRAPH_ID
                ).values_list("pk", flat=True)
            ]
            all_resource_ids = concept_ids_list + all_scheme_ids

        # --- Build resource name and type lookup ---
        resource_instances = models.ResourceInstance.objects.filter(
            resourceinstanceid__in=all_resource_ids
        )
        name_map = {}
        type_map = {}
        for ri in resource_instances:
            descriptors = ri.descriptors or {}
            name_map[str(ri.resourceinstanceid)] = next(
                (v.get("name", "") for v in descriptors.values() if v.get("name")),
                "",
            )
            type_map[str(ri.resourceinstanceid)] = (
                "scheme" if str(ri.graph_id) == str(SCHEMES_GRAPH_ID) else "concept"
            )

        # --- Recent activity: 20 most recent edits, deduplicated by transaction ---
        edits = models.EditLog.objects.filter(
            resourceinstanceid__in=all_resource_ids
        ).order_by("-timestamp")[:100]

        # Build nodegroup ID → display name map for action labels
        nodegroup_ids = {edit.nodegroupid for edit in edits if edit.nodegroupid}
        nodegroup_name_map = {}
        if nodegroup_ids:
            for node in models.Node.objects.filter(nodeid__in=nodegroup_ids):
                # Convert snake_case alias to Title Case
                nodegroup_name_map[str(node.nodeid)] = node.name.replace(
                    "_", " "
                ).title()

        seen_transactions = set()
        activity = []
        for edit in edits:
            key = str(edit.transactionid) if edit.transactionid else str(edit.editlogid)
            if key not in seen_transactions:
                seen_transactions.add(key)
                # Build action label: replace "Tile" with nodegroup name
                raw_label = EDIT_TYPE_LABELS.get(edit.edittype, edit.edittype)
                if edit.nodegroupid and edit.nodegroupid in nodegroup_name_map:
                    ng_name = nodegroup_name_map[edit.nodegroupid]
                    edittype_label = _(raw_label.replace("Tile", ng_name))
                else:
                    edittype_label = _(raw_label)
                activity.append(
                    {
                        "editlogid": str(edit.editlogid),
                        "edittype_label": edittype_label,
                        "timestamp": (
                            edit.timestamp.isoformat() if edit.timestamp else None
                        ),
                        "user_username": edit.user_username,
                        "user_firstname": edit.user_firstname,
                        "user_lastname": edit.user_lastname,
                        "resource_id": edit.resourceinstanceid,
                        "resource_name": name_map.get(edit.resourceinstanceid, ""),
                        "resource_type": type_map.get(
                            edit.resourceinstanceid, "concept"
                        ),
                    }
                )
            if len(activity) >= 20:
                break

        # --- Concepts by type ---
        concepts_by_type = _get_concept_type_breakdown(
            [uuid.UUID(rid) for rid in concept_ids_list]
        )

        # --- Label stats ---
        label_count, labels_by_type, labels_by_language = _get_label_stats(
            [uuid.UUID(rid) for rid in concept_ids_list]
        )

        return JSONResponse(
            {
                "user_display_name": user_display_name,
                "scheme_count": scheme_count,
                "concept_count": concept_count,
                "concepts_by_type": concepts_by_type,
                "label_count": label_count,
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

        scheme_params = request.GET.getlist("scheme")
        scheme_ids = []
        for param in scheme_params:
            try:
                scheme_ids.append(str(uuid.UUID(param)))
            except ValueError:
                return JSONErrorResponse(
                    title=_("Invalid scheme"),
                    message=_("scheme must be a valid UUID"),
                    status=400,
                )

        page_number = int(request.GET.get("page", 1))
        items_per_page = int(request.GET.get("items", 25))

        # Find concept IDs that have a preferred label in the given language
        concepts_with_pref_ids = set(
            models.TileModel.objects.filter(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data__contains={
                    CONCEPT_NAME_LANGUAGE_NODE: language_code,
                    CONCEPT_NAME_TYPE_NODE: [{"uri": PREF_LABEL_URI}],
                },
            ).values_list("resourceinstance_id", flat=True)
        )

        # All concept IDs, optionally filtered by scheme(s)
        Concept = ResourceTileTree.get_tiles("concept")
        if scheme_ids:
            all_concept_ids = list(
                Concept.filter(part_of_scheme__id__in=scheme_ids).values_list(
                    "pk", flat=True
                )
            )
        else:
            all_concept_ids = list(
                models.ResourceInstance.objects.filter(
                    graph_id=CONCEPTS_GRAPH_ID
                ).values_list("resourceinstanceid", flat=True)
            )

        # Concepts missing preferred label in given language
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
