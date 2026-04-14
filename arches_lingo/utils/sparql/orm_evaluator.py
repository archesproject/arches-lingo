"""ORM-based SPARQL evaluator for Lingo.

Translates common SKOS triple patterns directly to Django ORM queries
against TileModel, avoiding the expensive step of materializing an
entire rdflib Graph.  For patterns that cannot be mapped to ORM queries,
falls back to the graph-based evaluator.

Strategy
--------
1. Analyse parsed triple patterns to identify recognisable SKOS patterns
   (rdf:type, prefLabel, altLabel, broader, inScheme, etc.).
2. Execute each pattern as a targeted TileModel / ResourceInstance query
   returning lightweight binding dicts (strings, not rdflib terms).
3. Join, filter, aggregate, and paginate in Python — same as the
   graph-based evaluator but operating on far less data.

All returned binding values are rdflib URIRef / Literal instances so
that the existing evaluator's formatting and filter logic works
unchanged.
"""

import logging

from django.db.models import Q
from django.db.models.expressions import RawSQL

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS

from arches.app.models.models import ResourceInstance, TileModel
from arches.app.models.system_settings import settings

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    SCHEMES_GRAPH_ID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_TYPE_NODE,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    RELATION_STATUS_NODEGROUP,
    RELATION_STATUS_ASCRIBED_COMPARATE_NODEID,
    STATEMENT_NODEGROUP,
    STATEMENT_CONTENT_NODE,
    STATEMENT_LANGUAGE_NODE,
    STATEMENT_TYPE_NODE,
    URI_NODEGROUP,
    URI_CONTENT_NODE,
)
from arches_lingo.utils.sparql.evaluator import (
    MAX_RESULTS,
    SparqlEvaluationError,
    _apply_filter,
    _apply_aggregation,
    _apply_order_by,
    _distinct_bindings,
    _left_join_bindings,
)
from arches_lingo.utils.sparql.parser import (
    SparqlParseError,
    resolve_prefixed_name,
)

logger = logging.getLogger(__name__)

ARCHES_NS = Namespace(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT)

SKOS_LABEL_PREDICATES = {
    str(SKOS.prefLabel),
    str(SKOS.altLabel),
    str(SKOS.hiddenLabel),
}

SKOS_NOTE_PREDICATES = {
    str(SKOS.scopeNote),
    str(SKOS.definition),
    str(SKOS.example),
    str(SKOS.historyNote),
    str(SKOS.editorialNote),
    str(SKOS.changeNote),
    str(SKOS.note),
}


def can_evaluate_via_orm(parsed_query):
    """Return True if every triple pattern in the query can be handled by the ORM evaluator."""
    prefixes = {**parsed_query.prefixes}

    all_patterns = list(parsed_query.triple_patterns)
    for optional_block in parsed_query.optional_blocks:
        all_patterns.extend(optional_block.patterns)

    for pattern in all_patterns:
        if not _can_handle_pattern(pattern, prefixes):
            return False
    return True


def evaluate_query_via_orm(parsed_query, scheme_id=None):
    """Evaluate a parsed SPARQL query using direct ORM queries.

    Returns the same dict shape as the graph-based evaluator:
    {"variables": [...], "bindings": [...]}.
    """
    prefixes = {**parsed_query.prefixes}

    bindings = [{}]
    for pattern in parsed_query.triple_patterns:
        pattern_bindings = _execute_pattern_via_orm(pattern, prefixes, scheme_id)
        bindings = _join_bindings_fast(bindings, pattern_bindings)

    for optional_block in parsed_query.optional_blocks:
        optional_bindings = [{}]
        for pattern in optional_block.patterns:
            pattern_results = _execute_pattern_via_orm(pattern, prefixes, scheme_id)
            optional_bindings = _join_bindings_fast(optional_bindings, pattern_results)
        for filter_expr in optional_block.filters:
            optional_bindings = _apply_filter(optional_bindings, filter_expr, prefixes)
        bindings = _left_join_bindings(bindings, optional_bindings)

    for filter_expr in parsed_query.filters:
        bindings = _apply_filter(bindings, filter_expr, prefixes)

    if parsed_query.group_by and parsed_query.aggregates:
        bindings = _apply_aggregation(
            bindings, parsed_query.group_by, parsed_query.aggregates
        )

    if parsed_query.distinct:
        bindings = _distinct_bindings(bindings)

    if parsed_query.order_by:
        bindings = _apply_order_by(bindings, parsed_query.order_by)

    if parsed_query.offset:
        bindings = bindings[parsed_query.offset :]

    effective_limit = parsed_query.limit or MAX_RESULTS
    bindings = bindings[:effective_limit]

    variables = parsed_query.select_variables
    if variables == ["*"]:
        all_vars = set()
        for binding in bindings:
            all_vars.update(binding.keys())
        variables = sorted(all_vars)

    output_bindings = []
    for binding in bindings:
        output_bindings.append({var: binding.get(var) for var in variables})

    return {"variables": variables, "bindings": output_bindings}


def _resource_uri(resource_id):
    """Build the ARCHES namespace URI for a resource instance."""
    return URIRef(str(ARCHES_NS) + str(resource_id))


def _resolve_uri(term, prefixes):
    """Resolve a SPARQL term to a URI string, or None if it's a variable."""
    if term.startswith("?"):
        return None
    if term.startswith("<") and term.endswith(">"):
        return term[1:-1]
    if term == "a" or term == "rdf:type":
        return str(RDF.type)
    try:
        return resolve_prefixed_name(term, prefixes)
    except SparqlParseError:
        return None


def _can_handle_pattern(pattern, prefixes):
    """Check whether a single triple pattern is ORM-translatable."""
    predicate_uri = _resolve_uri(pattern.predicate, prefixes)

    if predicate_uri == str(RDF.type):
        object_uri = _resolve_uri(pattern.obj, prefixes)
        return object_uri in (str(SKOS.Concept), str(SKOS.ConceptScheme)) or (
            pattern.obj.startswith("?")
        )

    if predicate_uri is None and pattern.predicate.startswith("?"):
        return True

    if predicate_uri in SKOS_LABEL_PREDICATES:
        return True
    if predicate_uri in SKOS_NOTE_PREDICATES:
        return True
    if predicate_uri in (
        str(SKOS.broader),
        str(SKOS.inScheme),
        str(SKOS.hasTopConcept),
        str(SKOS.related),
    ):
        return True

    return False


def _execute_pattern_via_orm(pattern, prefixes, scheme_id=None):
    """Execute a single triple pattern via ORM and return binding dicts."""
    predicate_uri = _resolve_uri(pattern.predicate, prefixes)

    if predicate_uri == str(RDF.type):
        return _pattern_rdf_type(pattern, prefixes, scheme_id)

    if predicate_uri in SKOS_LABEL_PREDICATES:
        return _pattern_label(pattern, prefixes, predicate_uri, scheme_id)

    if predicate_uri in SKOS_NOTE_PREDICATES:
        return _pattern_note(pattern, prefixes, predicate_uri, scheme_id)

    if predicate_uri == str(SKOS.broader):
        return _pattern_broader(pattern, prefixes, scheme_id)

    if predicate_uri == str(SKOS.inScheme):
        return _pattern_in_scheme(pattern, prefixes, scheme_id)

    if predicate_uri == str(SKOS.hasTopConcept):
        return _pattern_has_top_concept(pattern, prefixes, scheme_id)

    if predicate_uri == str(SKOS.related):
        return _pattern_related(pattern, prefixes, scheme_id)

    if predicate_uri is None and pattern.predicate.startswith("?"):
        return _pattern_variable_predicate(pattern, prefixes, scheme_id)

    raise SparqlEvaluationError(
        f"Cannot translate predicate to ORM query: {pattern.predicate}"
    )


def _pattern_rdf_type(pattern, prefixes, scheme_id):
    """Handle ?s a skos:Concept / ?s a skos:ConceptScheme / ?s a ?type."""
    object_uri = _resolve_uri(pattern.obj, prefixes)
    results = []

    if pattern.obj.startswith("?"):
        for resource_id in _concept_ids(scheme_id):
            binding = {}
            if pattern.subject.startswith("?"):
                binding[pattern.subject] = _resource_uri(resource_id)
            binding[pattern.obj] = URIRef(str(SKOS.Concept))
            results.append(binding)
        for resource_id in _scheme_ids(scheme_id):
            binding = {}
            if pattern.subject.startswith("?"):
                binding[pattern.subject] = _resource_uri(resource_id)
            binding[pattern.obj] = URIRef(str(SKOS.ConceptScheme))
            results.append(binding)
        return results

    if object_uri == str(SKOS.Concept):
        for resource_id in _concept_ids(scheme_id):
            binding = {}
            if pattern.subject.startswith("?"):
                binding[pattern.subject] = _resource_uri(resource_id)
            results.append(binding)
    elif object_uri == str(SKOS.ConceptScheme):
        for resource_id in _scheme_ids(scheme_id):
            binding = {}
            if pattern.subject.startswith("?"):
                binding[pattern.subject] = _resource_uri(resource_id)
            results.append(binding)

    return results


def _pattern_label(pattern, prefixes, predicate_uri, scheme_id):
    """Handle ?s skos:prefLabel/altLabel/hiddenLabel ?label patterns for both concepts and schemes."""
    results = []

    skos_label_name = predicate_uri.replace(str(SKOS), "")

    concept_label_tiles = _query_label_tiles(
        CONCEPT_NAME_NODEGROUP,
        CONCEPT_NAME_CONTENT_NODE,
        CONCEPT_NAME_LANGUAGE_NODE,
        CONCEPT_NAME_TYPE_NODE,
        skos_label_name,
        scheme_id,
        CONCEPTS_GRAPH_ID,
    )
    for tile in concept_label_tiles:
        binding = _build_label_binding(pattern, tile)
        if binding is not None:
            results.append(binding)

    scheme_label_tiles = _query_label_tiles(
        SCHEME_NAME_NODEGROUP,
        SCHEME_NAME_CONTENT_NODE,
        SCHEME_NAME_LANGUAGE_NODE,
        SCHEME_NAME_TYPE_NODE,
        skos_label_name,
        scheme_id,
        SCHEMES_GRAPH_ID,
    )
    for tile in scheme_label_tiles:
        binding = _build_label_binding(pattern, tile)
        if binding is not None:
            results.append(binding)

    return results


def _query_label_tiles(
    nodegroup_id,
    content_node,
    language_node,
    type_node,
    skos_label_name,
    scheme_id,
    graph_id,
):
    """Query label tiles, optionally filtering by label type (prefLabel, altLabel, etc.)."""
    filters = Q(nodegroup_id=nodegroup_id)

    if scheme_id and graph_id == CONCEPTS_GRAPH_ID:
        concept_ids_in_scheme = _concept_ids_in_scheme(scheme_id)
        filters &= Q(resourceinstance_id__in=concept_ids_in_scheme)
    elif scheme_id and graph_id == SCHEMES_GRAPH_ID:
        filters &= Q(resourceinstance_id=scheme_id)

    skos_uri_fragment = f"http://www.w3.org/2004/02/skos/core#{skos_label_name}"
    filters &= Q(**{f"data__{type_node}__contains": [{"uri": skos_uri_fragment}]})

    return TileModel.objects.filter(filters).values(
        "resourceinstance_id",
        resource_label=RawSQL(
            f"tiledata->>%s",
            [content_node],
        ),
        resource_language=RawSQL(
            f"tiledata->>%s",
            [language_node],
        ),
        label_type_json=RawSQL(
            f"tiledata->%s",
            [type_node],
        ),
    )


def _build_label_binding(pattern, tile_row):
    """Build a binding dict from a label tile query result."""
    label_text = tile_row.get("resource_label")
    if not label_text:
        return None

    language = tile_row.get("resource_language") or None
    resource_id = tile_row["resourceinstance_id"]

    if language:
        label_value = Literal(label_text, lang=language)
    else:
        label_value = Literal(label_text)

    binding = {}
    if pattern.subject.startswith("?"):
        binding[pattern.subject] = _resource_uri(resource_id)
    if pattern.obj.startswith("?"):
        binding[pattern.obj] = label_value
    return binding


def _pattern_note(pattern, prefixes, predicate_uri, scheme_id):
    """Handle ?s skos:scopeNote/definition/... ?note patterns."""
    skos_note_name = predicate_uri.replace(str(SKOS), "")
    results = []

    filters = Q(nodegroup_id=STATEMENT_NODEGROUP)

    if scheme_id:
        concept_ids_in_scheme = _concept_ids_in_scheme(scheme_id)
        filters &= Q(resourceinstance_id__in=concept_ids_in_scheme)

    skos_uri_fragment = f"http://www.w3.org/2004/02/skos/core#{skos_note_name}"
    filters &= Q(
        **{f"data__{STATEMENT_TYPE_NODE}__contains": [{"uri": skos_uri_fragment}]}
    )

    tiles = TileModel.objects.filter(filters).values(
        "resourceinstance_id",
        note_content=RawSQL(f"tiledata->>%s", [STATEMENT_CONTENT_NODE]),
        note_language=RawSQL(f"tiledata->>%s", [STATEMENT_LANGUAGE_NODE]),
    )

    for tile in tiles:
        note_text = tile.get("note_content")
        if not note_text:
            continue

        language = tile.get("note_language") or None
        resource_id = tile["resourceinstance_id"]

        if language:
            note_value = Literal(note_text, lang=language)
        else:
            note_value = Literal(note_text)

        binding = {}
        if pattern.subject.startswith("?"):
            binding[pattern.subject] = _resource_uri(resource_id)
        if pattern.obj.startswith("?"):
            binding[pattern.obj] = note_value
        results.append(binding)

    return results


def _pattern_broader(pattern, prefixes, scheme_id):
    """Handle ?child skos:broader ?parent."""
    results = []

    filters = Q(nodegroup_id=CLASSIFICATION_STATUS_NODEGROUP)
    if scheme_id:
        concept_ids_in_scheme = _concept_ids_in_scheme(scheme_id)
        filters &= Q(resourceinstance_id__in=concept_ids_in_scheme)

    tiles = (
        TileModel.objects.filter(filters)
        .annotate(
            broader_id=RawSQL(
                "(jsonb_array_elements(tiledata->%s) ->> 'resourceId')::uuid",
                [CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID],
            )
        )
        .values("resourceinstance_id", "broader_id")
    )

    for tile in tiles:
        broader_id = tile.get("broader_id")
        if not broader_id:
            continue
        binding = {}
        if pattern.subject.startswith("?"):
            binding[pattern.subject] = _resource_uri(tile["resourceinstance_id"])
        if pattern.obj.startswith("?"):
            binding[pattern.obj] = _resource_uri(broader_id)
        results.append(binding)

    return results


def _pattern_in_scheme(pattern, prefixes, scheme_id):
    """Handle ?concept skos:inScheme ?scheme."""
    results = []

    filters = Q(nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID)
    if scheme_id:
        filters &= Q(
            **{
                f"data__{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}__contains": [
                    {"resourceId": str(scheme_id)}
                ]
            }
        )

    tiles = (
        TileModel.objects.filter(filters)
        .annotate(
            scheme_resource_id=RawSQL(
                "(jsonb_array_elements(tiledata->%s) ->> 'resourceId')::uuid",
                [CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID],
            )
        )
        .values("resourceinstance_id", "scheme_resource_id")
    )

    for tile in tiles:
        target_scheme_id = tile.get("scheme_resource_id")
        if not target_scheme_id:
            continue
        binding = {}
        if pattern.subject.startswith("?"):
            binding[pattern.subject] = _resource_uri(tile["resourceinstance_id"])
        if pattern.obj.startswith("?"):
            binding[pattern.obj] = _resource_uri(target_scheme_id)
        results.append(binding)

    return results


def _pattern_has_top_concept(pattern, prefixes, scheme_id):
    """Handle ?scheme skos:hasTopConcept ?concept."""
    results = []

    filters = Q(nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP)
    if scheme_id:
        filters &= Q(
            **{
                f"data__{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}__contains": [
                    {"resourceId": str(scheme_id)}
                ]
            }
        )

    tiles = (
        TileModel.objects.filter(filters)
        .annotate(
            target_scheme_id=RawSQL(
                "(jsonb_array_elements(tiledata->%s) ->> 'resourceId')::uuid",
                [TOP_CONCEPT_OF_NODE_AND_NODEGROUP],
            )
        )
        .values("resourceinstance_id", "target_scheme_id")
    )

    for tile in tiles:
        target_scheme = tile.get("target_scheme_id")
        if not target_scheme:
            continue
        binding = {}
        if pattern.subject.startswith("?"):
            binding[pattern.subject] = _resource_uri(target_scheme)
        if pattern.obj.startswith("?"):
            binding[pattern.obj] = _resource_uri(tile["resourceinstance_id"])
        results.append(binding)

    return results


def _pattern_related(pattern, prefixes, scheme_id):
    """Handle ?a skos:related ?b."""
    results = []

    filters = Q(nodegroup_id=RELATION_STATUS_NODEGROUP)
    if scheme_id:
        concept_ids_in_scheme = _concept_ids_in_scheme(scheme_id)
        filters &= Q(resourceinstance_id__in=concept_ids_in_scheme)

    tiles = (
        TileModel.objects.filter(filters)
        .annotate(
            related_id=RawSQL(
                "(jsonb_array_elements(tiledata->%s) ->> 'resourceId')::uuid",
                [RELATION_STATUS_ASCRIBED_COMPARATE_NODEID],
            )
        )
        .values("resourceinstance_id", "related_id")
    )

    for tile in tiles:
        related_id = tile.get("related_id")
        if not related_id:
            continue
        binding = {}
        if pattern.subject.startswith("?"):
            binding[pattern.subject] = _resource_uri(tile["resourceinstance_id"])
        if pattern.obj.startswith("?"):
            binding[pattern.obj] = _resource_uri(related_id)
        results.append(binding)

    return results


def _pattern_variable_predicate(pattern, prefixes, scheme_id):
    """Handle patterns with a variable predicate (e.g., ?s ?p ?o).

    This is common in queries like:
        ?concept ?labelType ?label .
        FILTER(?labelType = skos:prefLabel || ?labelType = skos:altLabel)

    We return bindings for all supported label-type predicates.
    """
    results = []

    for predicate_uri in sorted(SKOS_LABEL_PREDICATES):
        skos_label_name = predicate_uri.replace(str(SKOS), "")
        concept_tiles = _query_label_tiles(
            CONCEPT_NAME_NODEGROUP,
            CONCEPT_NAME_CONTENT_NODE,
            CONCEPT_NAME_LANGUAGE_NODE,
            CONCEPT_NAME_TYPE_NODE,
            skos_label_name,
            scheme_id,
            CONCEPTS_GRAPH_ID,
        )
        for tile in concept_tiles:
            binding = _build_label_binding(pattern, tile)
            if binding is not None:
                if pattern.predicate.startswith("?"):
                    binding[pattern.predicate] = URIRef(predicate_uri)
                results.append(binding)

        scheme_tiles = _query_label_tiles(
            SCHEME_NAME_NODEGROUP,
            SCHEME_NAME_CONTENT_NODE,
            SCHEME_NAME_LANGUAGE_NODE,
            SCHEME_NAME_TYPE_NODE,
            skos_label_name,
            scheme_id,
            SCHEMES_GRAPH_ID,
        )
        for tile in scheme_tiles:
            binding = _build_label_binding(pattern, tile)
            if binding is not None:
                if pattern.predicate.startswith("?"):
                    binding[pattern.predicate] = URIRef(predicate_uri)
                results.append(binding)

    for predicate_uri in sorted(SKOS_NOTE_PREDICATES):
        skos_note_name = predicate_uri.replace(str(SKOS), "")
        note_filters = Q(nodegroup_id=STATEMENT_NODEGROUP)
        if scheme_id:
            concept_ids_in_scheme = _concept_ids_in_scheme(scheme_id)
            note_filters &= Q(resourceinstance_id__in=concept_ids_in_scheme)
        skos_uri_fragment = f"http://www.w3.org/2004/02/skos/core#{skos_note_name}"
        note_filters &= Q(
            **{f"data__{STATEMENT_TYPE_NODE}__contains": [{"uri": skos_uri_fragment}]}
        )
        tiles = TileModel.objects.filter(note_filters).values(
            "resourceinstance_id",
            note_content=RawSQL(f"tiledata->>%s", [STATEMENT_CONTENT_NODE]),
            note_language=RawSQL(f"tiledata->>%s", [STATEMENT_LANGUAGE_NODE]),
        )
        for tile in tiles:
            note_text = tile.get("note_content")
            if not note_text:
                continue
            language = tile.get("note_language") or None
            if language:
                note_value = Literal(note_text, lang=language)
            else:
                note_value = Literal(note_text)
            binding = {}
            if pattern.subject.startswith("?"):
                binding[pattern.subject] = _resource_uri(tile["resourceinstance_id"])
            if pattern.obj.startswith("?"):
                binding[pattern.obj] = note_value
            if pattern.predicate.startswith("?"):
                binding[pattern.predicate] = URIRef(predicate_uri)
            results.append(binding)

    return results


def _join_bindings_fast(left_bindings, right_bindings):
    """Join two sets of bindings, using hash-based join when possible."""
    if not left_bindings:
        return right_bindings
    if not right_bindings:
        return []

    if left_bindings == [{}]:
        return right_bindings
    if right_bindings == [{}]:
        return left_bindings

    left_keys = set()
    for binding in left_bindings:
        left_keys.update(binding.keys())
    right_keys = set()
    for binding in right_bindings:
        right_keys.update(binding.keys())

    shared_keys = left_keys & right_keys

    if shared_keys:
        right_index = {}
        for right_binding in right_bindings:
            join_key = tuple(
                (key, right_binding.get(key)) for key in sorted(shared_keys)
            )
            if join_key not in right_index:
                right_index[join_key] = []
            right_index[join_key].append(right_binding)

        results = []
        for left_binding in left_bindings:
            join_key = tuple(
                (key, left_binding.get(key)) for key in sorted(shared_keys)
            )
            matching_right = right_index.get(join_key, [])
            for right_binding in matching_right:
                merged = {**left_binding, **right_binding}
                results.append(merged)
        return results
    else:
        results = []
        for left_binding in left_bindings:
            for right_binding in right_bindings:
                merged = {**left_binding, **right_binding}
                results.append(merged)
        return results


def _concept_ids(scheme_id=None):
    """Return concept resource instance IDs, optionally scoped to a scheme."""
    if scheme_id:
        return _concept_ids_in_scheme(scheme_id)
    return ResourceInstance.objects.filter(graph_id=CONCEPTS_GRAPH_ID).values_list(
        "resourceinstanceid", flat=True
    )


def _scheme_ids(scheme_id=None):
    """Return scheme resource instance IDs."""
    if scheme_id:
        return ResourceInstance.objects.filter(
            graph_id=SCHEMES_GRAPH_ID, resourceinstanceid=scheme_id
        ).values_list("resourceinstanceid", flat=True)
    return ResourceInstance.objects.filter(graph_id=SCHEMES_GRAPH_ID).values_list(
        "resourceinstanceid", flat=True
    )


def _concept_ids_in_scheme(scheme_id):
    """Return concept IDs belonging to a specific scheme."""
    return (
        TileModel.objects.filter(
            Q(
                nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
                **{
                    f"data__{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}__contains": [
                        {"resourceId": str(scheme_id)}
                    ]
                },
            )
            | Q(
                nodegroup_id=TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
                **{
                    f"data__{TOP_CONCEPT_OF_NODE_AND_NODEGROUP}__contains": [
                        {"resourceId": str(scheme_id)}
                    ]
                },
            )
        )
        .values_list("resourceinstance_id", flat=True)
        .distinct()
    )
