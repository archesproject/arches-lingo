import os
import json
import logging
import uuid
import zipfile
from io import BytesIO
from collections import defaultdict
from datetime import datetime
from slugify import slugify

from django.utils.translation import gettext as _

from arches.app.models.system_settings import settings
from arches.app.models.models import (
    ETLModule,
    LoadEvent,
    ResourceInstance,
    TempFile,
    User,
)
from arches_querysets.models import ResourceTileTree

from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.utils.skos import SKOSWriter

logger = logging.getLogger(__name__)

details = {
    "etlmoduleid": "4302e334-33ed-4e85-99f2-fdac7c7c32fa",
    "name": "Lingo Thesaurus Exporter",
    "description": "Export Arches Lingo schemes and concepts to a linked data file",
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
Mapping dict consists of nodegroup aliases as top level key. Their values are dicts where
the key indicates the component of a triple and the value are node aliases which are used
to extract data from Arches Queryset TileTrees. There is also an option to define a 
default predicate if a predicate is not found in the tile tree.
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
        format = request.POST.get("format", "xml") if request else "xml"

        load_details = {
            "operation": "Export Lingo Resources",
            "scheme_resourceid": self.resourceid,
        }
        load_event = LoadEvent.objects.create(
            loadid=self.loadid,
            user=User.objects.get(id=self.userid),
            etl_module=ETLModule.objects.get(pk=self.moduleid),
            status="validated",
            load_details=json.dumps(load_details),
            load_start_time=datetime.now(),
            complete=False,
        )
        self.load_event = load_event

        try:
            response = self.run_export_task(self.resourceid, filename, format)
            return response
        except:
            error = _("An unexpected error occurred during export.")
            self.handle_error(error)
            raise

    def run_export_task(self, resourceid, filename=None, format="xml"):
        schemes, concepts = self.gather_hierarchy_for_export(resourceid)
        self.schemes = schemes
        self.concepts = concepts

        self.scheme_triples = defaultdict(list)
        for scheme in self.schemes:
            for nodegroup_alias, tile_trees in scheme.aliased_data._items():
                if tile_trees:
                    self.scheme_triples[scheme.resourceinstanceid].extend(
                        self.extract_triples_from_aliased_tiles(
                            nodegroup_alias, tile_trees
                        )
                    )

        self.concept_triples = defaultdict(list)
        for concept in self.concepts:
            for nodegroup_alias, tile_trees in concept.aliased_data._items():
                if tile_trees:
                    self.concept_triples[concept.resourceinstanceid].extend(
                        self.extract_triples_from_aliased_tiles(
                            nodegroup_alias, tile_trees
                        )
                    )

        if len(self.scheme_triples) == 0 and len(self.concept_triples) == 0:
            error = _("The thesaurus could not be mapped to triples for export.")
            return self.handle_error(error)

        if format == "xml":
            writer = SKOSWriter()
            rdf_graph = writer.write_skos_from_triples(
                self.scheme_triples, self.concept_triples
            )
            serialized_rdf = rdf_graph.serialize(format="pretty-xml")
        # TODO: support other linked data formats
        else:
            error = _("The requested export format is not supported.")
            return self.handle_error(error)

        file = self.save_file(serialized_rdf, filename, format)
        if file:
            filename = os.path.basename(file.path.name)
            file_url = os.path.join(settings.MEDIA_URL, filename)
            existing_details = json.loads(self.load_event.load_details)
            file_details = {
                "name": filename,
                "url": file_url,
                "fileid": str(file.fileid),
            }
            load_details = {
                **existing_details,
                "file": file_details,
                # TODO: support multiple schemes export to individual files
                "scheme_name": self.scheme_name,
            }
            self.load_event.complete = True
            self.load_event.status = (
                "indexed"  # in BDM UI, 'indexed' maps to 'completed'
            )
            self.load_event.load_details = json.dumps(load_details)
            self.load_event.save()

            return {
                "success": True,
                "data": {
                    "message": "success",
                    "load_details": json.dumps(self.load_event.load_details),
                },
            }
        else:
            error = _("File could not be saved.")
            return self.handle_error(error)

    def gather_hierarchy_for_export(self, resourceid):
        """
        Depending on whether the resourceid provided is a scheme or a concept,
        we're either exporting a full hierarchy or a partial hierarchy.
        If we're exporting a partial hierarchy, we need to map the root concept to
        `SKOS:ConceptScheme` and its children as `SKOS:HasTopConcept`'s
        """
        schemes = ResourceTileTree.get_tiles(
            graph_slug="scheme", resource_ids=[resourceid]
        )
        #  Full Hierarchy Export
        if len(schemes) > 0:
            concepts = ResourceTileTree.get_tiles(graph_slug="concept").filter(
                part_of_scheme__id=resourceid
            )
            self.scheme_name = schemes.first().name[settings.LANGUAGE_CODE]
        # Partial Hierarchy Export
        else:
            root_concept = ResourceTileTree.get_tiles(
                graph_slug="concept", resource_ids=[resourceid]
            ).first()
            part_of_scheme = root_concept.aliased_data.part_of_scheme
            if not part_of_scheme:
                error = _(
                    "The selected concept is not part of a Scheme and cannot be exported."
                )
                return self.handle_error(error)
            else:
                scheme_id = part_of_scheme.aliased_data.part_of_scheme.pk

            self.scheme_name = root_concept.name[settings.LANGUAGE_CODE]

            # use ConceptBuilder to identify correct hierarchy to export
            concept_builder = ConceptBuilder()
            direct_descendants = set()
            indirect_descendants = set()
            # concepts can only be part of one scheme, so we can filter by scheme here
            potential_descendants = ResourceTileTree.get_tiles(
                graph_slug="concept"
            ).filter(part_of_scheme__id=str(scheme_id))
            for concept in potential_descendants:
                # direct descendants will need to be marked as top concepts
                parents_of_potential_descendants = (
                    concept.aliased_data.classification_status
                )
                for parent in parents_of_potential_descendants:
                    if (
                        root_concept.pk
                        == parent.aliased_data.classification_status_ascribed_classification.pk
                    ):
                        direct_descendants.add(concept)
                # indirect descendants do not need to mapped before export
                if concept not in direct_descendants:
                    paths = concept_builder.find_paths_to_root([], str(concept.pk))
                    for path in paths:
                        if resourceid in path:
                            indirect_descendants.add(concept)
                            break

            # CAUTION: below are only temporary modifications to the in-memory objects
            # for the purpose of export. These changes are NOT saved to the database.

            # Remove relationships held by root concept that do not apply to ConceptScheme
            del root_concept.aliased_data.part_of_scheme
            del root_concept.aliased_data.top_concept_of
            del root_concept.aliased_data.classification_status
            del root_concept.aliased_data.relation_status
            schemes = [root_concept]
            root_concept_instance = ResourceInstance.objects.get(pk=root_concept.pk)

            concepts = []
            for concept in direct_descendants:
                # mark direct descendants as top concepts & remove their parentage
                concept.aliased_data.part_of_scheme = root_concept_instance
                concept.aliased_data.top_concept_of = root_concept_instance
                concept.aliased_data.classification_status = []
                concepts.append(concept)
            for concept in indirect_descendants:
                # indirect descendants only need their scheme relationship set
                concept.aliased_data.part_of_scheme = root_concept_instance
                concepts.append(concept)

        return schemes, concepts

    def extract_triples_from_aliased_tiles(self, nodegroup_alias, tile_trees):
        triples = []
        mapping = TILE_TREE_TO_TRIPLE_MAPPING.get(nodegroup_alias)
        if mapping is None:
            logger.error(f"No mapping found for nodegroup alias: {nodegroup_alias}")
            return None
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
                    try:
                        predicate = getattr(tile_tree.aliased_data, node_alias)
                    except AttributeError:
                        # Expected when we've directly mapped a relationship
                        # that won't be wrapped as AliasedData as returned from a queryset
                        # (e.g. top_concept_of and part_of_scheme during partial hierarchy export)
                        predicate = tile_tree
                    triple[triple_component] = predicate
            triples.append(triple)
        return triples

    def save_file(self, serialized_rdf, filename, format):
        # TODO: support multiple schemes export to individual files
        if filename:
            filename = filename.replace(" ", "_")
            if not filename.endswith(f".{format}"):
                filename = f"{filename}.{format}"
        else:
            filename = (
                f"{slugify(self.scheme_name, separator='_', lowercase=False)}.{format}"
            )
        zip_name = filename.replace(
            f".{format}", f"_{slugify(str(datetime.now()))}.zip"
        )

        # TODO: support saving associated files (e.g. images) in zip archive
        data_stream = BytesIO(serialized_rdf)
        zip_stream = BytesIO()
        with zipfile.ZipFile(zip_stream, "w") as zip:
            zip.writestr(filename, data_stream.read())
        zip_file = TempFile(source="lingo_resource_exporter")
        zip_file.path.save(zip_name, zip_stream)

        return zip_file

    def handle_error(self, error):
        self.load_event.status = "failed"
        self.load_event.error_message = str(error)
        self.load_event.save()
        logger.error(error)
        return {"success": False, "data": {"message": error}}
