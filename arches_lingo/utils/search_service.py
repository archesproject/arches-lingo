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
        # Pre-fetch URI, identifier, and notes for the whole page in 3 queries
        # instead of 3-per-result (N×3 queries avoided).
        uri_map = get_uris_for_concepts(page_ids)
        identifier_map = get_identifiers_for_concepts(page_ids)
        notes_map = get_notes_for_concepts(page_ids)
        data = [
            enrich_search_result(
                builder, concept_id, uri_map, identifier_map, notes_map
            )
            for concept_id in page_ids
        ]

    return {
        "current_page": page.number,
        "total_pages": paginator.num_pages,
        "results_per_page": paginator.per_page,
        "total_results": paginator.count,
        "data": data,
    }


def enrich_search_result(builder, concept_id, uri_map, identifier_map, notes_map):
    """Serialize a concept with extra fields for advanced search results."""
    result = builder.serialize_concept(concept_id, parents=True, children=False)
    result["uri"] = uri_map.get(concept_id)
    result["identifier"] = identifier_map.get(concept_id)
    result["notes"] = notes_map.get(concept_id, [])
    return result


def get_uris_for_concepts(concept_ids):
    """Return ``{concept_id: url_string}`` for a batch of concepts (1 query)."""
    tiles = TileModel.objects.filter(
        resourceinstance_id__in=concept_ids,
        nodegroup_id=URI_NODEGROUP,
    ).values("resourceinstance_id", "data")

    result = {}
    for tile in tiles:
        concept_id = str(tile["resourceinstance_id"])
        if concept_id in result:
            continue
        uri_data = tile["data"].get(URI_CONTENT_NODE)
        if isinstance(uri_data, dict):
            result[concept_id] = uri_data.get("url")
        elif isinstance(uri_data, str):
            result[concept_id] = uri_data
    return result


def get_identifiers_for_concepts(concept_ids):
    """Return ``{concept_id: identifier_string}`` for a batch of concepts (1 query)."""
    tiles = TileModel.objects.filter(
        resourceinstance_id__in=concept_ids,
        nodegroup_id=IDENTIFIER_NODEGROUP,
    ).values("resourceinstance_id", "data")

    result = {}
    for tile in tiles:
        concept_id = str(tile["resourceinstance_id"])
        if concept_id in result:
            continue
        result[concept_id] = tile["data"].get(IDENTIFIER_CONTENT_NODE)
    return result


def get_notes_for_concepts(concept_ids, limit_per_concept=3):
    """Return ``{concept_id: [note, ...]}`` for a batch of concepts (1 query)."""
    tiles = TileModel.objects.filter(
        resourceinstance_id__in=concept_ids,
        nodegroup_id=STATEMENT_NODEGROUP,
    ).values("resourceinstance_id", "data")

    result: dict = {}
    counts: dict = {}
    for tile in tiles:
        concept_id = str(tile["resourceinstance_id"])
        if counts.get(concept_id, 0) >= limit_per_concept:
            continue
        content = tile["data"].get(STATEMENT_CONTENT_NODE, "")
        language = tile["data"].get(STATEMENT_LANGUAGE_NODE, "")
        note_type = extract_note_type_label(tile["data"].get(STATEMENT_TYPE_NODE, []))
        result.setdefault(concept_id, []).append(
            {"content": content or "", "language": language or "", "type": note_type}
        )
        counts[concept_id] = counts.get(concept_id, 0) + 1
    return result


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


def fetch_search_options():
    """Return filter option data for the advanced search UI."""
    languages = list(Language.objects.all().values("code", "name").order_by("name"))

    # Use a lightweight builder that only populates scheme labels — avoids
    # loading all broader/top-concept tiles (which is expensive at AAT scale).
    scheme_builder = ConceptBuilder(concept_ids=[])
    scheme_builder.populate_schemes()
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
