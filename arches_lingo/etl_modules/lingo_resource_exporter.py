import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from django.utils.translation import gettext as _

from arches.app.models.models import ETLModule, LoadEvent, User
from arches_querysets.models import ResourceTileTree

from arches_lingo.utils.skos import SKOSWriter

from arches_lingo.const import (
    SCHEMES_GRAPH_ID,
    TOP_CONCEPT_OF_NODE_AND_NODEGROUP,
    CLASSIFICATION_STATUS_NODEGROUP,
    CLASSIFICATION_STATUS_ASCRIBED_CLASSIFICATION_NODEID,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_TYPE_NODE,
    ALT_LABEL_VALUE,
    HIDDEN_LABEL_VALUE,
    PREF_LABEL_VALUE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_TYPE_NODE,
)

logger = logging.getLogger(__name__)

details = {
    "etlmoduleid": "4302e334-33ed-4e85-99f2-fdac7c7c32fa",
    "name": "Lingo SKOS Exporter",
    "description": "Export Arches Lingo schemes and concepts to SKOS RDF",
    "etl_type": "export",
    "component": "views/components/etl_modules/export-lingo-resources",
    "componentname": "export-lingo-resources",
    "modulename": "lingo_resource_exporter.py",
    "classname": "LingoResourceExporter",
    "config": {"bgColor": "#ffa564", "circleColor": "#ffd2b1", "show": True},
    "icon": "fa fa-usb",
    "slug": "export-lingo-resources",
    "helpsortorder": 0,
    "helptemplate": "export-lingo-resources-help",
}

"""
Mapping dict consists of nodegroup aliases as top level key that matches a nodegroup alias
the key/value pairs of the subdict map node aliases to their role in the triple, with 
option to define a default predicate if a predicate is not found in the tile tree.
Some predicates are hardcoded SKOS predicates for specific relationships.

nodegroup_alias: {
    "predicate": "<predicate_node_alias>" | "<skos_predicate_value>",
    "object": "<object_node_alias>",
    "object_language": "<object_language_node_alias>" (optional)
    "default_predicate": "<default_predicate_value>" (optional)
}
"""
TILE_TREE_TO_TRIPLE_MAPPING = {
    # Scheme and Concept Mappings:
    "appellative_status": {
        "predicate": "appellative_status_ascribed_relation",
        "object": "appellative_status_ascribed_name_content",
        "object_language": "appellative_status_ascribed_name_language",
    },
    "identifier": {
        "predicate": "identifier_type",
        "object": "identifier_content",
    },
    "statement": {
        "predicate": "statement_type",
        "object": "statement_content",
        "object_language": "statement_language",
    },
    # Concept Mappings:
    "top_concept_of": {
        "predicate": "hasTopConcept",  # hardcoded SKOS predicate
        "object": "top_concept_of",
    },
    "part_of_scheme": {
        "predicate": "inScheme",  # hardcoded SKOS predicate
        "object": "part_of_scheme",
    },
    # Hierarchy
    "classification_status": {
        "predicate": "classification_status_ascribed_relation",
        "object": "classification_status_ascribed_classification",
        "default_predicate": "broader",
    },
    # Associated Concepts
    "relation_status": {
        "predicate": "relation_status_ascribed_relation",
        "object": "relation_status_ascribed_comparate",
        "default_predicate": "related",
    },
}


class LingoResourceExporter:
    def __init__(self, request=None):
        self.request = request

    def start(self, request, **kwargs):
        self.userid = request.user.id if request else None
        self.moduleid = request.POST.get("module")
        if self.moduleid is None:
            self.moduleid = ETLModule.objects.get(slug="export-lingo-resources").pk

        self.loadid = request.POST.get("load_id")
        if self.loadid is None and self.loadid is None:
            # Mints a loadid if one was not minted by frontend
            loadid = str(uuid.uuid4())

        self.resourceid = (
            request.POST.get("resourceid")
            if request
            else kwargs.get("resourceid", None)
        )
        filename = request.POST.get("filename") if request else None

        load_details = {
            "operation": "Export Lingo Resources",
            "resourceid": self.resourceid,
            "filename": filename,
        }
        load_event = LoadEvent.objects.create(
            loadid=self.loadid,
            user=User.objects.get(id=self.userid),
            etl_module=ETLModule.objects.get(pk=self.moduleid),
            status="running",
            load_details=json.dumps(load_details),
            load_start_time=datetime.now(),
            complete=False,
        )
        self.load_event = load_event

        self.run_export_task(self.resourceid, filename=filename)

    def run_export_task(self, resourceid, format="pretty-xml", filename=None):
        schemes = ResourceTileTree.get_tiles(
            graph_slug="scheme", resource_ids=[resourceid]
        )
        concepts = ResourceTileTree.get_tiles(graph_slug="concept").filter(
            part_of_scheme__id=resourceid
        )

        scheme_triples = defaultdict(list)
        for scheme in schemes:
            for nodegroup_alias, tile_trees in scheme.aliased_data:
                if tile_trees:
                    scheme_triples[scheme.resourceinstanceid].extend(
                        self.extract_triples_from_aliased_tiles(
                            nodegroup_alias, tile_trees
                        )
                    )

        concept_triples = defaultdict(list)
        for concept in concepts:
            for nodegroup_alias, tile_trees in concept.aliased_data:
                if tile_trees:
                    concept_triples[concept.resourceinstanceid].extend(
                        self.extract_triples_from_aliased_tiles(
                            nodegroup_alias, tile_trees
                        )
                    )

        writer = SKOSWriter()
        writer.write_skos_from_triples(scheme_triples, concept_triples, format=format)

    def extract_triples_from_aliased_tiles(self, nodegroup_alias, tile_trees):
        triples = []
        mapping = TILE_TREE_TO_TRIPLE_MAPPING.get(nodegroup_alias)
        if mapping is None:
            logger.error(f"No mapping found for nodegroup alias: {nodegroup_alias}")
            return triples
        if type(tile_trees) is not list:
            tile_trees = [tile_trees]
        for tile_tree in tile_trees:
            triple = defaultdict(str)
            for triple_component, node_alias in mapping.items():
                if node_alias in ["inScheme", "hasTopConcept"]:
                    # Predicate for concept -> scheme relationship are not stored as a node value
                    # but instead derived from the relationship itself
                    triple[triple_component] = node_alias
                elif (
                    triple_component == "default_predicate"
                    and triple["predicate"] is None
                ):
                    # Fall back on default predicates for relationships if none was found
                    triple["predicate"] = node_alias
                elif triple_component != "default_predicate":
                    predicate = getattr(tile_tree.aliased_data, node_alias)
                    triple[triple_component] = predicate
            triples.append(triple)
        return triples
