"""Service functions for advanced search views.

Handles search execution, result enrichment, serialization, and
search options assembly. The view layer delegates to these functions.
"""

from django.core.paginator import Paginator

from arches.app.models.models import (
    Language,
    ResourceInstance,
    ResourceInstanceLifecycleState,
    TileModel,
)

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    IDENTIFIER_CONTENT_NODE,
    IDENTIFIER_NODEGROUP,
    STATEMENT_CONTENT_NODE,
    STATEMENT_LANGUAGE_NODE,
    STATEMENT_NODEGROUP,
    STATEMENT_TYPE_NODE,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.models import ConceptSetMember
from arches_lingo.utils.advanced_search import AdvancedSearchEvaluator
from arches_lingo.utils.concept_builder import ConceptBuilder


# ── Search execution ────────────────────────────────────────────


def execute_search(query, user, page_number=1, items_per_page=25):
    """Execute an advanced search and return paginated, enriched results."""
    evaluator = AdvancedSearchEvaluator(user=user)
    concept_ids = evaluator.evaluate(query)

    paginator = Paginator(concept_ids, items_per_page)
    page = paginator.get_page(page_number)

    data = []
    if paginator.count:
        page_ids = [str(concept_id) for concept_id in page]
        builder = ConceptBuilder(page_ids, include_parents=True)
        data = [enrich_search_result(builder, concept_id) for concept_id in page_ids]

    return {
        "current_page": page.number,
        "total_pages": paginator.num_pages,
        "results_per_page": paginator.per_page,
        "total_results": paginator.count,
        "data": data,
    }


# ── Result enrichment ──────────────────────────────────────────


def enrich_search_result(builder, concept_id):
    """Serialize a concept with extra fields for advanced search results."""
    result = builder.serialize_concept(concept_id, parents=True, children=False)
    result["uri"] = get_first_uri_for_concept(concept_id)
    result["identifier"] = get_first_identifier_for_concept(concept_id)
    result["notes"] = get_notes_for_concept(concept_id)
    result["lifecycle_state"] = get_lifecycle_state_for_concept(concept_id)
    return result


def get_first_uri_for_concept(concept_id):
    """Extract the first URI value from URI tiles for a concept."""
    tile = TileModel.objects.filter(
        resourceinstance_id=concept_id,
        nodegroup_id=URI_NODEGROUP,
    ).first()
    if not tile:
        return None
    uri_data = tile.data.get(URI_CONTENT_NODE)
    if isinstance(uri_data, dict):
        return uri_data.get("url")
    if isinstance(uri_data, str):
        return uri_data
    return None


def get_first_identifier_for_concept(concept_id):
    """Extract the first identifier value from identifier tiles for a concept."""
    tile = TileModel.objects.filter(
        resourceinstance_id=concept_id,
        nodegroup_id=IDENTIFIER_NODEGROUP,
    ).first()
    if not tile:
        return None
    return tile.data.get(IDENTIFIER_CONTENT_NODE)


def get_notes_for_concept(concept_id, limit=3):
    """Extract note summaries from statement tiles for a concept."""
    note_tiles = TileModel.objects.filter(
        resourceinstance_id=concept_id,
        nodegroup_id=STATEMENT_NODEGROUP,
    )[:limit]

    notes = []
    for tile in note_tiles:
        content = tile.data.get(STATEMENT_CONTENT_NODE, "")
        language = tile.data.get(STATEMENT_LANGUAGE_NODE, "")
        note_type = extract_note_type_label(tile.data.get(STATEMENT_TYPE_NODE, []))
        notes.append(
            {
                "content": content or "",
                "language": language or "",
                "type": note_type,
            }
        )
    return notes


def extract_note_type_label(note_type_data):
    """Extract a human-readable label from reference-data note type JSON.

    Prefers English; falls back to the first available label.
    """
    if not note_type_data or not isinstance(note_type_data, list):
        return ""
    labels = note_type_data[0].get("labels", [])
    for label in labels:
        if label.get("language_id") == "en":
            return label.get("value", "")
    if labels:
        return labels[0].get("value", "")
    return ""


def get_lifecycle_state_for_concept(concept_id):
    """Get the lifecycle state name for a concept."""
    try:
        resource = ResourceInstance.objects.get(pk=concept_id)
        state = resource.resource_instance_lifecycle_state
        return state.name if state else None
    except ResourceInstance.DoesNotExist:
        return None


# ── Search options ──────────────────────────────────────────────


def fetch_search_options():
    """Return filter option data for the advanced search UI."""
    languages = list(
        Language.objects.filter(isdefault=True)
        .union(Language.objects.filter(scope="system"))
        .values("code", "name")
        .order_by("name")
    )
    if not languages:
        languages = list(Language.objects.all().values("code", "name").order_by("name"))

    scheme_builder = ConceptBuilder()
    scheme_options = []
    for scheme in scheme_builder.schemes:
        serialized = scheme_builder.serialize_scheme(scheme, children=False)
        scheme_options.append(
            {
                "id": serialized["id"],
                "labels": serialized.get("labels", []),
            }
        )

    lifecycle_states = list(
        ResourceInstanceLifecycleState.objects.filter(
            resource_instance_lifecycle__graphs__graphid=CONCEPTS_GRAPH_ID
        )
        .values("id", "name")
        .distinct()
        .order_by("name")
    )

    return {
        "languages": languages,
        "schemes": scheme_options,
        "lifecycle_states": lifecycle_states,
    }


# ── Serialization ──────────────────────────────────────────────


def serialize_saved_search(saved_search):
    """Serialize a SavedSearch instance to a dict."""
    return {
        "id": saved_search.pk,
        "name": saved_search.name,
        "query": saved_search.query,
        "created": saved_search.created.isoformat(),
        "updated": saved_search.updated.isoformat(),
    }


def serialize_concept_set(concept_set):
    """Serialize a ConceptSet instance to a dict with member count."""
    return {
        "id": concept_set.pk,
        "name": concept_set.name,
        "description": concept_set.description,
        "member_count": concept_set.members.count(),
        "created": concept_set.created.isoformat(),
        "updated": concept_set.updated.isoformat(),
    }


def serialize_concept_set_with_members(concept_set):
    """Serialize a concept set including its members."""
    member_ids = list(concept_set.members.values_list("concept_id", flat=True))

    members = []
    if member_ids:
        string_ids = [str(member_id) for member_id in member_ids]
        builder = ConceptBuilder(string_ids, include_parents=True)
        members = [
            builder.serialize_concept(concept_id, parents=True, children=False)
            for concept_id in string_ids
        ]

    return {
        "id": concept_set.pk,
        "name": concept_set.name,
        "description": concept_set.description,
        "members": members,
        "created": concept_set.created.isoformat(),
        "updated": concept_set.updated.isoformat(),
    }


# ── Concept set member operations ──────────────────────────────


def add_members_to_concept_set(concept_set, concept_ids):
    """Add concept IDs to a concept set.

    Returns a dict with the count of newly added members and total member count.
    """
    added_count = 0
    for concept_id in concept_ids:
        _, created = ConceptSetMember.objects.get_or_create(
            concept_set=concept_set,
            concept_id=concept_id,
        )
        if created:
            added_count += 1

    return {
        "added": added_count,
        "member_count": concept_set.members.count(),
    }


def remove_members_from_concept_set(concept_set, concept_ids):
    """Remove concept IDs from a concept set.

    Returns a dict with the updated member count.
    """
    if concept_ids:
        concept_set.members.filter(concept_id__in=concept_ids).delete()

    return {
        "member_count": concept_set.members.count(),
    }
