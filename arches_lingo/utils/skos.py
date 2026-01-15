import uuid
from collections import defaultdict
from django.db import transaction
from django.db.models import Max, Q
from django.utils import translation
from rdflib import Literal, Namespace, RDF, URIRef
from rdflib.namespace import SKOS, DCTERMS
from rdflib.graph import Graph
from arches.app.models import models
from arches.app.models.system_settings import settings

from arches_controlled_lists.utils.skos import SKOSReader
from arches_controlled_lists.models import List, ListItem, ListItemValue

from arches_lingo.etl_modules.migrate_to_lingo import LingoResourceImporter

# define the ARCHES namespace
ARCHES = Namespace(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT)


class SKOSReader(SKOSReader):
    """
    Extends the SKOSReader class from Arches Controlled Lists to import RDF graphs as Lingo resources.
    """

    def __init__(self):
        super().__init__()
        self.schemes = []
        self.concepts = []
        self.relations = defaultdict(list)
        self.languages_controlled_list = List.objects.get(name="Languages")
        self.prefLabel_valuetype = models.DValueType.objects.get(valuetype="prefLabel")

    def extract_concepts_from_skos_for_lingo_import(
        self, graph, overwrite_options="overwrite"
    ):
        baseuuid = uuid.uuid4()
        self.allowed_languages = {}
        for lang in models.Language.objects.all():
            self.allowed_languages[lang.code] = lang
        self.default_lang = settings.LANGUAGE_CODE

        if isinstance(graph, Graph):

            # Create lookups for valuetypes used during Concept processing
            value_types = models.DValueType.objects.all()
            skos_value_types = value_types.filter(
                Q(namespace="skos") | Q(namespace="arches")
            )
            skos_note_and_label_types = skos_value_types.filter(
                Q(category="note") | Q(category="label")
            )
            self.skos_value_types = skos_value_types.values_list("valuetype", flat=True)
            self.skos_note_and_label_types = skos_note_and_label_types.values_list(
                "valuetype", flat=True
            )
            self.dcterms_value_types = value_types.filter(
                namespace="dcterms"
            ).values_list("valuetype", flat=True)
            self.match_types = models.DRelationType.objects.filter(
                category="Mapping Properties"
            ).values_list("relationtype", flat=True)

            ### Schemes ###
            top_concept_mock_tiles = {}
            isScheme = True
            for scheme, v, o in graph.triples((None, RDF.type, SKOS.ConceptScheme)):
                scheme_pk = self.generate_uuidv5_from_subject(baseuuid, scheme)

                new_scheme = {
                    "resourceinstanceid": scheme_pk,
                    "legacyid": str(scheme),
                    "type": "Scheme",
                    "tile_data": [],
                }

                for predicate, object in graph.predicate_objects(scheme):
                    predicate_str = (
                        predicate.replace(ARCHES, "")
                        .replace(SKOS, "")
                        .replace(DCTERMS, "")
                    )

                    if (
                        predicate_str in self.dcterms_value_types
                        or predicate_str in self.skos_note_and_label_types
                    ):
                        mock_tile = self.map_predicate_object_to_mock_tile(
                            object, predicate_str, isScheme
                        )
                        if mock_tile:
                            new_scheme["tile_data"].append(mock_tile)

                    elif predicate == SKOS.hasTopConcept:
                        top_concept_id = self.generate_uuidv5_from_subject(
                            baseuuid, object
                        )
                        top_concept_mock_tile = (
                            LingoResourceImporter.create_mock_tile_from_relationship(
                                {
                                    "resourceId": scheme_pk,
                                    "node_alias": "top_concept_of",
                                    "nodegroup_alias": "top_concept_of",
                                    "resourceinstanceid": top_concept_id,
                                }
                            )
                        )
                        top_concept_mock_tiles[top_concept_id] = top_concept_mock_tile

                if "identifier" not in [
                    key for val in new_scheme["tile_data"] for key in val.keys()
                ]:
                    mock_tile = self.map_predicate_object_to_mock_tile(
                        str(scheme), "identifier", isScheme
                    )
                    if mock_tile:
                        new_scheme["tile_data"].append(mock_tile)

                self.schemes.append(new_scheme)

                ### Concepts ###
                isScheme = False
                for concept, v, o in graph.triples((None, SKOS.inScheme, scheme)):
                    concept_pk = self.generate_uuidv5_from_subject(baseuuid, concept)
                    new_concept = {
                        "resourceinstanceid": concept_pk,
                        "legacyid": str(concept),
                        "type": "Concept",
                        "tile_data": [],
                    }

                    if top_concept_mock_tiles.get(concept_pk):
                        new_concept["tile_data"].append(
                            top_concept_mock_tiles.get(concept_pk)
                        )

                    mock_tile = (
                        LingoResourceImporter.create_mock_tile_from_relationship(
                            {
                                "resourceId": scheme_pk,
                                "node_alias": "part_of_scheme",
                                "nodegroup_alias": "part_of_scheme",
                                "resourceinstanceid": concept_pk,
                            }
                        )
                    )
                    if mock_tile:
                        new_concept["tile_data"].append(mock_tile)

                    for predicate, object in graph.predicate_objects(concept):
                        # Cast dcterms:description to scopeNote (same behavior in RDM)
                        if predicate == DCTERMS.description:
                            predicate_str = "scopeNote"

                        predicate_str = (
                            predicate.replace(ARCHES, "")
                            .replace(SKOS, "")
                            .replace(DCTERMS, "")
                        )

                        if predicate in [
                            SKOS.broader,
                            SKOS.narrower,
                            SKOS.related,
                        ]:
                            related_concept_id = self.generate_uuidv5_from_subject(
                                baseuuid, object
                            )
                            if predicate == SKOS.broader:
                                relationship = {
                                    "resourceId": related_concept_id,
                                    "node_alias": "classification_status_ascribed_classification",
                                    "nodegroup_alias": "classification_status",
                                }
                                resourceinstanceid = concept_pk
                            elif predicate == SKOS.narrower:
                                relationship = {
                                    "resourceId": concept_pk,
                                    "node_alias": "classification_status_ascribed_classification",
                                    "nodegroup_alias": "classification_status",
                                }
                                resourceinstanceid = related_concept_id
                            elif predicate == SKOS.related:
                                relationship = {
                                    "resourceId": concept_pk,
                                    "node_alias": "relation_status_ascribed_comparate",
                                    "nodegroup_alias": "relation_status",
                                }
                                resourceinstanceid = related_concept_id
                            mock_tile = LingoResourceImporter.create_mock_tile_from_relationship(
                                relationship
                            )
                            self.relations[resourceinstanceid].append(mock_tile)
                        elif predicate in [
                            SKOS.broadMatch,
                            SKOS.closeMatch,
                            SKOS.exactMatch,
                            SKOS.inverseOf,
                            SKOS.mappingRelation,
                            SKOS.narrowMatch,
                            SKOS.relatedMatch,
                        ]:
                            matched_URI = None
                            for (
                                matched_predicate,
                                matched_object,
                            ) in graph.predicate_objects(object):
                                if matched_predicate == DCTERMS.identifier:
                                    matched_URI = matched_object
                                    break
                            if matched_URI:
                                mock_tile = self.map_predicate_object_to_mock_tile(
                                    matched_URI, predicate_str, isScheme
                                )
                                new_concept["tile_data"].append(mock_tile)
                        else:
                            mock_tile = self.map_predicate_object_to_mock_tile(
                                object, predicate_str, isScheme
                            )
                            if isinstance(mock_tile, list):
                                new_concept["tile_data"].extend(mock_tile)
                            elif mock_tile:
                                new_concept["tile_data"].append(mock_tile)

                    if "identifier" not in [
                        key for val in new_concept["tile_data"] for key in val.keys()
                    ]:
                        mock_tile = self.map_predicate_object_to_mock_tile(
                            str(concept), "identifier", isScheme
                        )
                        if isinstance(mock_tile, list):
                            new_concept["tile_data"].extend(mock_tile)
                        elif mock_tile:
                            new_concept["tile_data"].append(mock_tile)

                    self.concepts.append(new_concept)

            # Map relationships to their respective concept resources
            for concept in self.concepts:
                if self.relations.get(concept["resourceinstanceid"]):
                    concept["tile_data"].extend(
                        self.relations.get(concept["resourceinstanceid"])
                    )

            return self.schemes, self.concepts

    def map_predicate_object_to_mock_tile(
        self, object: str | dict, predicate: str, isScheme: bool = False
    ) -> dict:
        if (
            predicate not in self.dcterms_value_types
            and predicate not in self.skos_value_types
            and predicate not in self.match_types
        ):
            return None

        object_lang = None
        if isinstance(object, dict):
            object_lang = object.get("language")
            if object_lang and not self.language_exists(object, self.allowed_languages):
                for lang in models.Language.objects.all():
                    self.allowed_languages[lang.code] = lang

        val = self.unwrapJsonLiteral(object)
        mock_tile = {
            "id": val["value_id"],
            "value": val["value"],
            "language_id": object_lang or self.default_lang,
            "valuetype_id": predicate,
        }
        mock_tile = LingoResourceImporter.create_mock_tile_from_value(
            mock_tile, isScheme=isScheme, lang_lookup=self.allowed_languages
        )
        return mock_tile

    def language_exists(self, rdf_tag):
        # TODO: When creating new Language datatype, remove this logic to add new list items
        # re. https://github.com/archesproject/arches-lingo/issues/472
        with transaction.atomic():
            lang_exists = super().language_exists(rdf_tag, self.allowed_languages)
            default_lang = self.allowed_languages[settings.LANGUAGE_CODE]
            if not lang_exists:
                lang_list_items = ListItem.objects.filter(
                    list=self.languages_controlled_list
                )
                lang_code = rdf_tag.language
                lang_name = translation.get_language_info(lang_code)
                new_list_item = ListItem.objects.create(
                    list=self.languages_controlled_list,
                    parent=None,
                    guide=False,
                    sortorder=lang_list_items.aggregate(Max("sortorder"))[
                        "sortorder__max"
                    ]
                    + 1,
                )
                new_list_item.clean()  # force generation of URI
                ListItemValue.objects.create(
                    list_item=new_list_item,
                    valuetype=self.prefLabel_valuetype,
                    language=default_lang,
                    value=lang_name or lang_code,
                )
                # Re-sort of list items after addition
                sorted = new_list_item.sort_siblings(root_siblings=lang_list_items)
                ListItem.objects.bulk_update(sorted, ["sortorder"])
            return lang_exists


class SKOSWriter:
    def write_skos_from_triples(self, schemes_triples, concepts_triples):
        rdf_graph = Graph()
        rdf_graph.bind("skos", SKOS)
        rdf_graph.bind("dcterms", DCTERMS)
        rdf_graph.bind("arches", ARCHES)

        self.language_lookup = {
            lang.name: lang.code for lang in models.Language.objects.all()
        }

        for scheme_id, triples in schemes_triples.items():
            rdf_scheme_id = ARCHES[str(scheme_id)]
            rdf_graph.add((rdf_scheme_id, RDF.type, SKOS.ConceptScheme))
            for triple in triples:
                predicates, object = self.extract_predicate_object(triple)
                for predicate in predicates:
                    rdf_graph.add((rdf_scheme_id, predicate, object))

        for concept_id, triples in concepts_triples.items():
            rdf_concept_id = ARCHES[str(concept_id)]
            rdf_graph.add((rdf_concept_id, RDF.type, SKOS.Concept))
            for triple in triples:
                predicates, object = self.extract_predicate_object(triple)
                for predicate in predicates:
                    if predicate == SKOS.hasTopConcept:
                        rdf_graph.add((object, SKOS.hasTopConcept, rdf_concept_id))
                    else:
                        rdf_graph.add((rdf_concept_id, predicate, object))

        return rdf_graph

    def extract_predicate_object(self, triple):
        # Some predicates are multivalue reference datatype fields, so process all predicates
        # as lists for ease of handling
        predicates = self.transform_predicate_values(triple.get("predicate"))

        object = triple.get("object")
        object_language = triple.get("object_language")
        if object_language:
            object = Literal(
                object, lang=self.get_language_code_from_references(object_language)
            )
        if isinstance(object, models.ResourceInstance):
            object = ARCHES[str(object.resourceinstanceid)]
        if not isinstance(object, Literal) and not isinstance(object, URIRef):
            object = Literal(object)

        return predicates, object

    def transform_predicate_values(self, predicate_references):
        if isinstance(predicate_references, str):
            return [SKOS[predicate_references]]
        elif isinstance(predicate_references, list):
            predicates = []
            for predicate in predicate_references:
                predicate = self.reformat_predicate_based_on_namespace(predicate)
                predicates.append(predicate)
            return predicates

    def reformat_predicate_based_on_namespace(self, predicate):
        uri = predicate.uri
        if not (SKOS in uri or ARCHES in uri or DCTERMS in uri):
            predicate_label = [
                label.value
                for label in predicate.labels
                if label.valuetype_id == "prefLabel"
            ][0]
            if predicate_label == "identifier":
                predicate = DCTERMS.identifier
            else:
                predicate = SKOS[predicate_label]
        else:
            predicate = URIRef(uri)
        return predicate

    # TODO: remove when implementing language datatype
    # re. https://github.com/archesproject/arches-lingo/issues/472
    def get_language_code_from_references(self, language_references):
        for language_reference in language_references:
            language_name = (
                [
                    lang.value
                    for lang in language_reference.labels
                    if lang.valuetype_id == "prefLabel"
                ]
            )[0]
            language_code = self.language_lookup.get(language_name)
            if language_code:
                return language_code
        return None
