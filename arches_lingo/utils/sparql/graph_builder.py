"""Graph builder for SPARQL evaluation.

Materializes Lingo concept and scheme data as an rdflib Graph
by reusing the exporter's triple-extraction pipeline. The graph
can then be queried by the SPARQL evaluator.

Supports building a graph for:
  - All concepts across all schemes
  - A single scheme and its concepts
"""

import logging
from collections import defaultdict

from django.core.cache import cache
from rdflib import Graph

from arches_querysets.models import ResourceTileTree

from arches_lingo.etl_modules.lingo_resource_exporter import (
    TILE_TREE_TO_TRIPLE_MAPPING,
    LingoResourceExporter,
)
from arches_lingo.utils.skos import SKOSWriter

logger = logging.getLogger(__name__)

GRAPH_CACHE_TIMEOUT = 600
GRAPH_CACHE_KEY_PREFIX = "sparql_graph"


def build_graph_for_scheme(scheme_id):
    """Build an rdflib Graph for a single scheme and its concepts.

    Uses Django cache to avoid re-materializing on every query.
    """
    cache_key = f"{GRAPH_CACHE_KEY_PREFIX}:{scheme_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    graph = _materialize_scheme_graph(scheme_id)
    cache.set(cache_key, graph, GRAPH_CACHE_TIMEOUT)
    return graph


def build_graph_for_all():
    """Build an rdflib Graph for all schemes and concepts.

    Uses Django cache with a fixed key.
    """
    cache_key = f"{GRAPH_CACHE_KEY_PREFIX}:all"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    graph = _materialize_all_graphs()
    cache.set(cache_key, graph, GRAPH_CACHE_TIMEOUT)
    return graph


def invalidate_graph_cache(scheme_id=None):
    """Invalidate cached graphs. Call when concept/scheme data changes."""
    cache.delete(f"{GRAPH_CACHE_KEY_PREFIX}:all")
    if scheme_id:
        cache.delete(f"{GRAPH_CACHE_KEY_PREFIX}:{scheme_id}")


def _materialize_scheme_graph(scheme_id):
    """Build an rdflib Graph for a single scheme."""
    schemes = ResourceTileTree.get_tiles(
        graph_slug="scheme", resource_ids=[str(scheme_id)]
    )
    concepts = ResourceTileTree.get_tiles(graph_slug="concept").filter(
        part_of_scheme__id=str(scheme_id)
    )

    return _build_graph_from_tile_trees(schemes, concepts)


def _materialize_all_graphs():
    """Build an rdflib Graph for all schemes and concepts."""
    schemes = ResourceTileTree.get_tiles(graph_slug="scheme")
    concepts = ResourceTileTree.get_tiles(graph_slug="concept")

    return _build_graph_from_tile_trees(schemes, concepts)


def _build_graph_from_tile_trees(schemes, concepts):
    """Extract triples from aliased tile trees and build an rdflib Graph."""
    exporter = LingoResourceExporter()

    scheme_triples = defaultdict(list)
    for scheme in schemes:
        for nodegroup_alias, tile_trees in scheme.aliased_data._items():
            if tile_trees:
                scheme_triples[scheme.resourceinstanceid].extend(
                    exporter.extract_triples_from_aliased_tiles(
                        nodegroup_alias, tile_trees
                    )
                )

    concept_triples = defaultdict(list)
    for concept in concepts:
        for nodegroup_alias, tile_trees in concept.aliased_data._items():
            if tile_trees:
                concept_triples[concept.resourceinstanceid].extend(
                    exporter.extract_triples_from_aliased_tiles(
                        nodegroup_alias, tile_trees
                    )
                )

    writer = SKOSWriter()
    return writer.write_skos_from_triples(scheme_triples, concept_triples)
