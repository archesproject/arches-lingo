import uuid
from collections import defaultdict
from django.db import transaction
from django.db.models import Max, Q
from django.utils import translation
from rdflib import Literal, Namespace, RDF
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
        allowed_languages = {}
        for lang in models.Language.objects.all():
            allowed_languages[lang.code] = lang
        default_lang = settings.LANGUAGE_CODE

        if isinstance(graph, Graph):

            # Create lookups for valuetypes used during Concept processing
            value_types = models.DValueType.objects.all()
            skos_value_types = value_types.filter(
                Q(namespace="skos") | Q(namespace="arches")
            )
            skos_note_and_label_types = skos_value_types.filter(
                Q(category="note") | Q(category="label")
            )
            skos_value_types = {
                valuetype.valuetype: valuetype for valuetype in skos_value_types
            }
            skos_note_and_label_types = {
                valuetype.valuetype: valuetype
                for valuetype in skos_note_and_label_types
            }
            dcterms_value_types = value_types.filter(namespace="dcterms")

            ### Schemes ###
            top_concept_mock_tiles = {}
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

                    if str(
                        DCTERMS
                    ) in predicate and predicate_str in dcterms_value_types.values_list(
                        "valuetype", flat=True
                    ):
                        if not self.language_exists(object, allowed_languages):
                            for lang in models.Language.objects.all():
                                allowed_languages[lang.code] = lang

                        val = self.unwrapJsonLiteral(object)
                        mock_tile = {
                            "id": val["value_id"],
                            "value": val["value"],
                            "language_id": object.language or default_lang,
                            "valuetype_id": predicate_str,
                        }
                        mock_tile = LingoResourceImporter.create_mock_tile_from_value(
                            mock_tile, isScheme=True, lang_lookup=allowed_languages
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
                    identifier = self.unwrapJsonLiteral(str(scheme))
                    mock_tile = {
                        "id": identifier["value_id"],
                        "value": identifier["value"],
                        "language_id": default_lang,
                        "valuetype_id": "identifier",
                    }
                    mock_tile = LingoResourceImporter.create_mock_tile_from_value(
                        mock_tile, lang_lookup=allowed_languages
                    )
                    if mock_tile:
                        new_scheme["tile_data"].append(mock_tile)

                self.schemes.append(new_scheme)

                ### Concepts ###
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
                        predicate_str = (
                            predicate.replace(ARCHES, "")
                            .replace(SKOS, "")
                            .replace(DCTERMS, "")
                        )

                        if str(SKOS) in predicate or str(ARCHES) in predicate:
                            if not self.language_exists(object, allowed_languages):
                                for lang in models.Language.objects.all():
                                    allowed_languages[lang.code] = lang

                            if predicate_str in skos_value_types:
                                val = self.unwrapJsonLiteral(object)
                                mock_tile = {
                                    "id": val["value_id"],
                                    "value": val["value"],
                                    "language_id": object.language or default_lang,
                                    "valuetype_id": predicate_str,
                                }
                                mock_tile = (
                                    LingoResourceImporter.create_mock_tile_from_value(
                                        mock_tile, lang_lookup=allowed_languages
                                    )
                                )
                                if mock_tile:
                                    new_concept["tile_data"].append(mock_tile)

                            elif predicate in [
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

                    if "identifier" not in [
                        key for val in new_concept["tile_data"] for key in val.keys()
                    ]:
                        identifier = self.unwrapJsonLiteral(str(scheme))
                        mock_tile = {
                            "id": identifier["value_id"],
                            "value": identifier["value"],
                            "language_id": default_lang,
                            "valuetype_id": "identifier",
                        }
                        mock_tile = LingoResourceImporter.create_mock_tile_from_value(
                            mock_tile, lang_lookup=allowed_languages
                        )
                        if mock_tile:
                            new_concept["tile_data"].append(mock_tile)

                    self.concepts.append(new_concept)

            # Map relationships to their respective concept resources
            for concept in self.concepts:
                if self.relations.get(concept["resourceinstanceid"]):
                    concept["tile_data"].extend(
                        self.relations.get(concept["resourceinstanceid"])
                    )

            return self.schemes, self.concepts

    def language_exists(self, rdf_tag, allowed_languages):
        # TODO: When creating new Language datatype, remove this logic to add new list items
        # re. https://github.com/archesproject/arches-lingo/issues/472
        with transaction.atomic():
            lang_exists = super().language_exists(rdf_tag, allowed_languages)
            default_lang = allowed_languages[settings.LANGUAGE_CODE]
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
