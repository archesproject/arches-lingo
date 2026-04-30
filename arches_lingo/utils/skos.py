import uuid
import logging
from collections import defaultdict
from django.db.models import Q
from rdflib import Literal, Namespace, RDF, URIRef
from rdflib.namespace import SKOS, DCTERMS
from rdflib.graph import Graph
from arches.app.models import models
from arches.app.models.system_settings import settings

from arches_controlled_lists.utils.skos import SKOSReader
from arches_controlled_lists.models import List, ListItem, ListItemValue

from arches_lingo.etl_modules.migrate_to_lingo import LingoResourceImporter
import arches_lingo.const as const

# define the ARCHES namespace
ARCHES = Namespace(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT)

logger = logging.getLogger(__name__)

# GVP typed associative relation predicates use this prefix followed by a
# numeric relation code and descriptive label, e.g.:
#   http://vocab.getty.edu/ontology#aat2285_practiced-studied_by
# The arches-lingo controlled list «related properties» stores these URIs as
# the identifier of each list item so they can be looked up and stored as the
# relation_status_ascribed_relation reference value during import.
GVP_TYPED_RELATION_PREFIX = "http://vocab.getty.edu/ontology#aat"


class SKOSReader(SKOSReader):
    """
    Extends the SKOSReader class from Arches Controlled Lists to import RDF graphs as Lingo resources.
    """

    def __init__(self):
        super().__init__()
        self.schemes = []
        self.concepts = []
        self.relations = defaultdict(list)
        self.prefLabel_valuetype = models.DValueType.objects.get(valuetype="prefLabel")
        self._gvp_relation_type_lookup = None

    def _get_gvp_relation_type_lookup(self):
        """Return a {gvp_predicate_uri: list_item_id_str} mapping built from
        the related_properties controlled list.  The lookup is built lazily on
        first call and cached; an empty dict is returned when the controlled
        list is not yet loaded so the import still succeeds without type data."""
        if self._gvp_relation_type_lookup is not None:
            return self._gvp_relation_type_lookup
        try:
            self._gvp_relation_type_lookup = {
                item.uri: str(item.id)
                for item in ListItem.objects.filter(
                    list_id=const.RELATED_PROPERTIES_LIST_ID,
                    uri__startswith=GVP_TYPED_RELATION_PREFIX,
                )
            }
        except Exception:
            logger.warning(
                "Could not load related_properties controlled list; "
                "typed GVP relation types will not be set on import."
            )
            self._gvp_relation_type_lookup = {}
        return self._gvp_relation_type_lookup

    def extract_concepts_from_skos_for_lingo_import(
        self, graph, overwrite_options="overwrite", import_identifiers=False
    ):
        baseuuid = uuid.uuid4()
        self.import_identifiers = import_identifiers
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

                    if predicate_str in DCTERMS.identifier and str(scheme_pk) in str(
                        object
                    ):
                        # Don't import RDM default identifiers
                        continue

                    if (
                        predicate_str in self.dcterms_value_types
                        or predicate_str in self.skos_note_and_label_types
                    ):
                        mock_tile = self.map_predicate_object_to_mock_tile(
                            object, predicate_str, isScheme
                        )
                        if isinstance(mock_tile, list):
                            new_scheme["tile_data"].extend(mock_tile)
                        elif mock_tile:
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

                self._add_label_and_identifier_fallbacks(new_scheme, scheme, isScheme)
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
                        new_concept["is_top_concept"] = True

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
                        if predicate == DCTERMS.description:
                            # Cast dcterms:description to scopeNote (same behavior in RDM)
                            predicate_str = "scopeNote"
                        else:
                            predicate_str = (
                                predicate.replace(ARCHES, "")
                                .replace(SKOS, "")
                                .replace(DCTERMS, "")
                            )

                        if predicate_str in DCTERMS.identifier and str(
                            concept_pk
                        ) in str(object):
                            # Don't import RDM default identifiers
                            continue

                        if predicate == SKOS.topConceptOf and not new_concept.get(
                            "is_top_concept"
                        ):
                            # SKOS.topConceptOf is the inverse of SKOS.hasTopConcept.
                            # Some thesauri (e.g. Getty AAT) only declare this on the
                            # concept side rather than using hasTopConcept on the scheme.
                            # Guard against thesauri that declare both hasTopConcept on
                            # the scheme and topConceptOf on the concept, which would
                            # cause cardinality issues.
                            scheme_of_top_concept_pk = (
                                self.generate_uuidv5_from_subject(baseuuid, object)
                            )
                            top_concept_mock_tile = LingoResourceImporter.create_mock_tile_from_relationship(
                                {
                                    "resourceId": scheme_of_top_concept_pk,
                                    "node_alias": "top_concept_of",
                                    "nodegroup_alias": "top_concept_of",
                                    "resourceinstanceid": concept_pk,
                                }
                            )
                            new_concept["tile_data"].append(top_concept_mock_tile)
                            new_concept["is_top_concept"] = True
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
                        elif str(predicate).startswith(GVP_TYPED_RELATION_PREFIX):
                            # Typed GVP associative relation predicate — carries both
                            # the comparate (the other concept) and the relation type
                            # (encoded in the predicate URI local name).  The tile is
                            # placed on the object concept so that viewing it shows the
                            # comparate (subject) with its semantic relation type.
                            related_concept_id = self.generate_uuidv5_from_subject(
                                baseuuid, object
                            )
                            relation_type_id = self._get_gvp_relation_type_lookup().get(
                                str(predicate)
                            )
                            typed_relation_mock_tile = {
                                "relation_status": {
                                    "relation_status_ascribed_comparate": {
                                        "resourceId": str(concept_pk),
                                        "ontologyProperty": const.RELATION_STATUS_ASCRIBED_COMPARATE_ONTOLOGY_PROPERTY,
                                        "resourceXresourceId": "",
                                        "inverseOntologyProperty": "",
                                    }
                                }
                            }
                            if relation_type_id:
                                typed_relation_mock_tile["relation_status"][
                                    "relation_status_ascribed_relation"
                                ] = relation_type_id
                            else:
                                logger.debug(
                                    "No list item found for GVP relation predicate %s;"
                                    " relation_status_ascribed_relation will be null.",
                                    predicate,
                                )
                            self.relations[related_concept_id].append(
                                typed_relation_mock_tile
                            )
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
                                if isinstance(mock_tile, list):
                                    new_concept["tile_data"].extend(mock_tile)
                                elif mock_tile:
                                    new_concept["tile_data"].append(mock_tile)
                        else:
                            mock_tile = self.map_predicate_object_to_mock_tile(
                                object, predicate_str, isScheme
                            )
                            if isinstance(mock_tile, list):
                                new_concept["tile_data"].extend(mock_tile)
                            elif mock_tile:
                                new_concept["tile_data"].append(mock_tile)

                    type_tile = {
                        "type": {"type": "concept", "type_metatype": "classification"}
                    }
                    new_concept["tile_data"].append(type_tile)
                    self._add_label_and_identifier_fallbacks(
                        new_concept, concept, isScheme
                    )
                    self.concepts.append(new_concept)

            # Map relationships to their respective concept resources
            for concept in self.concepts:
                if self.relations.get(concept["resourceinstanceid"]):
                    concept["tile_data"].extend(
                        self.relations.get(concept["resourceinstanceid"])
                    )

            return self.schemes, self.concepts

    def language_exists(self, rdf_tag, allowed_languages):
        """
        Override the parent implementation to fix two issues with extended BCP-47
        language tags (e.g. zh-latn-pinyin-x-notone):

        1. Case mismatch: arches core's capitalize_region() uppercases only the
           second subtag ('zh-latn-...' → 'zh-LATN-...'), but Language records
           stored from ensure_aat_languages.py use fully lower-case codes.  A
           case-insensitive pre-check avoids calling get_language_info when the
           language is already in the database under a differently-cased key.

        2. Unknown BCP-47 tags: Django's get_language_info() raises KeyError for
           any tag it does not recognise.  When the parent would raise, we create
           a minimal Language record and return False so the caller refreshes its
           allowed_languages cache.
        """
        if not (
            hasattr(rdf_tag, "language")
            and rdf_tag.language is not None
            and rdf_tag.language.strip() != ""
        ):
            return True

        lower_code = rdf_tag.language.lower()
        if any(code.lower() == lower_code for code in allowed_languages):
            return True

        try:
            return super().language_exists(rdf_tag, allowed_languages)
        except KeyError:
            from arches.app.utils.i18n import capitalize_region

            newlang = models.Language()
            newlang.code = capitalize_region(rdf_tag.language)
            newlang.name = rdf_tag.language
            newlang.default_direction = "ltr"
            newlang.isdefault = False
            newlang.save()
            return False

    def map_predicate_object_to_mock_tile(
        self,
        object: str | dict,
        predicate: str,
        isScheme: bool = False,
    ) -> dict | list | None:
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
        elif isinstance(object, Literal) and object.language:
            # rdflib Literal carries the language tag directly; extract it here
            # so the mock tile receives the correct language rather than falling
            # back to self.default_lang (which would assign English to every label).
            if not self.language_exists(object, self.allowed_languages):
                for lang in models.Language.objects.all():
                    self.allowed_languages[lang.code] = lang
            # Resolve to the key actually present in allowed_languages (the DB-stored
            # code may differ in case from the rdflib tag, e.g. 'zh-latn-...' vs
            # 'zh-LATN-...').  Fall back to the raw tag if not matched.
            lower_code = object.language.lower()
            object_lang = next(
                (code for code in self.allowed_languages if code.lower() == lower_code),
                object.language,
            )

        val = self.unwrapJsonLiteral(object)
        mock_tile = {
            "id": val["value_id"],
            "value": val["value"],
            "language_id": object_lang or self.default_lang,
            "valuetype_id": predicate,
        }
        mock_tile = LingoResourceImporter.create_mock_tile_from_value(
            mock_tile,
            isScheme=isScheme,
            import_identifiers=self.import_identifiers,
            lang_lookup=self.allowed_languages,
        )
        return mock_tile

    def _add_label_and_identifier_fallbacks(self, resource, rdf_node, isScheme):
        """
        If a scheme or concept has not been imported with a prefLabel and/or identifier (in the case of `import_identifiers=True`),
        map those properties from the rdf:about value
        """
        tile_aliases = [
            alias
            for tile_entry in resource["tile_data"]
            for tile in (tile_entry if isinstance(tile_entry, list) else [tile_entry])
            for alias in tile.keys()
        ]
        if "appellative_status" not in tile_aliases:
            mock_tile = self.map_predicate_object_to_mock_tile(
                str(rdf_node), "prefLabel", isScheme
            )
            if mock_tile:
                resource["tile_data"].append(mock_tile)
        if self.import_identifiers and "identifier" not in tile_aliases:
            mock_tile = self.map_predicate_object_to_mock_tile(
                str(rdf_node), "identifier", isScheme
            )
            if isinstance(mock_tile, list):
                resource["tile_data"].extend(mock_tile)
            elif mock_tile:
                resource["tile_data"].append(mock_tile)


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
            object = Literal(object, lang=object_language)
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
