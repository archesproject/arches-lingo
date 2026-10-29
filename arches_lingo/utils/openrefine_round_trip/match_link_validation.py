"""Deciding what an import would do with each match link, without writing."""

import uuid
from collections import Counter, defaultdict
from urllib.parse import urlsplit, urlunsplit

from arches.app.models.models import ResourceInstance, TileModel

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    LINKABLE_MATCH_TYPES,
    MATCH_STATUS_COMPARATE_NODE,
    MATCH_STATUS_NODEGROUP,
    MATCH_STATUS_RELATION_NODE,
    URI_CONTENT_NODE,
    URI_NODEGROUP,
)
from arches_lingo.permissions import is_lingo_admin
from arches_lingo.utils.concept_lifecycle import reasons_concepts_cannot_receive_data
from arches_lingo.utils.concept_matching import get_scheme_ids_for_concepts
from arches_lingo.utils.concept_merge.tiles import get_list_item_tile_value

OUTCOME_ADD = "add"
OUTCOME_ALREADY_LINKED = "already_linked"
# The concept and URI are already paired by another match type. SKOS makes some
# of these pairs contradictory (exactMatch and relatedMatch are disjoint), so an
# editor changes the type deliberately rather than the import adding a second.
OUTCOME_CONFLICTING_LINK = "conflicting_link"
OUTCOME_DUPLICATE_IN_FILE = "duplicate_in_file"
OUTCOME_UNKNOWN_CONCEPT = "unknown_concept"
OUTCOME_OUTSIDE_SCHEME = "outside_scheme"
OUTCOME_INVALID_MATCH_TYPE = "invalid_match_type"
OUTCOME_INVALID_URI = "invalid_uri"
OUTCOME_SELF_MATCH = "self_match"
# Outcomes that say nothing about the link itself, so a later link to the same
# URI in the file is judged on its own.
OUTCOMES_NOT_RECORDED_AS_SEEN = {
    OUTCOME_UNKNOWN_CONCEPT,
    OUTCOME_OUTSIDE_SCHEME,
    OUTCOME_INVALID_URI,
    OUTCOME_SELF_MATCH,
}


def canonical_concept_id(raw_concept_id):
    try:
        return str(uuid.UUID(raw_concept_id))
    except (TypeError, ValueError):
        return None


def is_absolute_web_uri(uri):
    parsed_uri = urlsplit(uri)
    return (
        parsed_uri.scheme in ("http", "https")
        and bool(parsed_uri.netloc)
        and not any(character.isspace() for character in uri)
    )


def comparable_uri(uri):
    """Reduce a URI to what identifies its target, so http/https, host case and
    a trailing slash do not make the same link look new."""
    parsed_uri = urlsplit((uri or "").strip())
    return urlunsplit(
        (
            "",
            parsed_uri.netloc.casefold(),
            parsed_uri.path.rstrip("/"),
            parsed_uri.query,
            parsed_uri.fragment,
        )
    )


def stored_uri_variants(uri):
    """Mixed-case hosts other than the one given are not enumerated."""
    parsed_uri = urlsplit(uri)
    path = parsed_uri.path.rstrip("/")
    return {
        urlunsplit(
            (
                scheme,
                host,
                path_variant,
                parsed_uri.query,
                parsed_uri.fragment,
            )
        )
        for scheme in ("http", "https")
        for host in (parsed_uri.netloc, parsed_uri.netloc.casefold())
        for path_variant in (path, f"{path}/")
    }


def uri_node_value_as_text(uri_node_value):
    """Older data may hold a URI as a url datatype value rather than a string."""
    if isinstance(uri_node_value, dict):
        return uri_node_value.get("url") or ""
    return uri_node_value if isinstance(uri_node_value, str) else ""


def get_own_uris(concept_ids):
    own_uris_by_concept_id = defaultdict(set)
    for concept_id, uri_node_value in TileModel.objects.filter(
        nodegroup_id=URI_NODEGROUP, resourceinstance_id__in=concept_ids
    ).values_list("resourceinstance_id", f"data__{URI_CONTENT_NODE}"):
        uri = uri_node_value_as_text(uri_node_value)
        if uri:
            own_uris_by_concept_id[str(concept_id)].add(comparable_uri(uri))
    return own_uris_by_concept_id


def get_existing_links(concept_ids):
    """Return ``{(concept_id, comparable matched uri): {relation_uri, …}}``."""
    relation_uris_by_link = defaultdict(set)
    for concept_id, tile_data in TileModel.objects.filter(
        nodegroup_id=MATCH_STATUS_NODEGROUP, resourceinstance_id__in=concept_ids
    ).values_list("resourceinstance_id", "data"):
        relation_values = tile_data.get(MATCH_STATUS_RELATION_NODE) or []
        if relation_values:
            relation_uris_by_link[
                (
                    str(concept_id),
                    comparable_uri(tile_data.get(MATCH_STATUS_COMPARATE_NODE)),
                )
            ].add(relation_values[0].get("uri"))
    return relation_uris_by_link


def outcome_for_known_link(relation_uri, recorded_relation_uris, same_type_outcome):
    if relation_uri in recorded_relation_uris:
        return same_type_outcome
    return OUTCOME_CONFLICTING_LINK


def get_internal_concept_uris(match_uris):
    return {
        comparable_uri(uri_node_value_as_text(internal_uri))
        for internal_uri in TileModel.objects.filter(
            nodegroup_id=URI_NODEGROUP,
            **{
                f"data__{URI_CONTENT_NODE}__in": [
                    uri_variant
                    for match_uri in match_uris
                    for uri_variant in stored_uri_variants(match_uri)
                ]
            },
        ).values_list(f"data__{URI_CONTENT_NODE}", flat=True)
    }


def validate_match_links(match_links, user, scheme_id=None):
    """Give each link an ``outcome``, in a fixed number of queries.

    Writability uses the same rule as the concept matching "link" action. A
    match URI that belongs to another concept here is still added (one way
    only) and flagged ``is_internal_concept``: a two-way link between Lingo
    concepts belongs to the concept matches workflow.
    """
    concept_ids = [
        canonical_concept_id(match_link["concept_id"]) for match_link in match_links
    ]
    existing_concept_ids = {
        str(concept_id)
        for concept_id in ResourceInstance.objects.filter(
            pk__in={concept_id for concept_id in concept_ids if concept_id},
            graph_id=CONCEPTS_GRAPH_ID,
        ).values_list("pk", flat=True)
    }
    scheme_id_by_concept_id = get_scheme_ids_for_concepts(existing_concept_ids)
    cannot_receive_reason_by_concept_id = reasons_concepts_cannot_receive_data(
        existing_concept_ids,
        scheme_id_by_concept_id,
        user is not None and is_lingo_admin(user),
    )
    own_uris_by_concept_id = get_own_uris(existing_concept_ids)
    existing_relation_uris_by_link = get_existing_links(existing_concept_ids)
    relation_uri_by_match_type = {
        match_type: get_list_item_tile_value(list_item_id)["uri"]
        for match_type, list_item_id in LINKABLE_MATCH_TYPES.items()
    }
    internal_concept_uris = get_internal_concept_uris(
        {
            match_link["match_uri"]
            for match_link in match_links
            if is_absolute_web_uri(match_link["match_uri"])
        }
    )

    relation_uris_by_link_seen_in_file = defaultdict(set)
    validated_links = []
    for match_link, concept_id in zip(match_links, concept_ids):
        match_uri = comparable_uri(match_link["match_uri"])
        link = (concept_id, match_uri)
        relation_uri = relation_uri_by_match_type.get(match_link["match_type"])
        if concept_id not in existing_concept_ids:
            outcome = OUTCOME_UNKNOWN_CONCEPT
        elif scheme_id and scheme_id_by_concept_id.get(concept_id) != str(scheme_id):
            outcome = OUTCOME_OUTSIDE_SCHEME
        elif match_link["match_type"] not in LINKABLE_MATCH_TYPES:
            outcome = OUTCOME_INVALID_MATCH_TYPE
        elif not is_absolute_web_uri(match_link["match_uri"]):
            outcome = OUTCOME_INVALID_URI
        elif match_uri in own_uris_by_concept_id.get(concept_id, set()):
            outcome = OUTCOME_SELF_MATCH
        elif link in relation_uris_by_link_seen_in_file:
            outcome = outcome_for_known_link(
                relation_uri,
                relation_uris_by_link_seen_in_file[link],
                OUTCOME_DUPLICATE_IN_FILE,
            )
        elif concept_id in cannot_receive_reason_by_concept_id:
            outcome = cannot_receive_reason_by_concept_id[concept_id]
        elif link in existing_relation_uris_by_link:
            outcome = outcome_for_known_link(
                relation_uri,
                existing_relation_uris_by_link[link],
                OUTCOME_ALREADY_LINKED,
            )
        else:
            outcome = OUTCOME_ADD
        if relation_uri and outcome not in OUTCOMES_NOT_RECORDED_AS_SEEN:
            relation_uris_by_link_seen_in_file[link].add(relation_uri)
        validated_links.append(
            {
                **match_link,
                "concept_id": concept_id or match_link["concept_id"],
                "outcome": outcome,
                "is_internal_concept": match_uri in internal_concept_uris,
            }
        )
    return validated_links


def count_outcomes(validated_links):
    return dict(
        Counter(validated_link["outcome"] for validated_link in validated_links)
    )
