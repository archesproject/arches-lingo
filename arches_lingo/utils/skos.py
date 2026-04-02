import uuid
import xml.etree.ElementTree as ET
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

                if "appellative_status" not in [
                    key for val in new_scheme["tile_data"] for key in val.keys()
                ]:
                    mock_tile = self.map_predicate_object_to_mock_tile(
                        str(scheme), "prefLabel", isScheme
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
                        if predicate == DCTERMS.description:
                            # Cast dcterms:description to scopeNote (same behavior in RDM)
                            predicate_str = "scopeNote"
                        else:
                            predicate_str = (
                                predicate.replace(ARCHES, "")
                                .replace(SKOS, "")
                                .replace(DCTERMS, "")
                            )

                        if predicate == SKOS.topConceptOf:
                            # SKOS.topConceptOf is the inverse of SKOS.hasTopConcept.
                            # Some thesauri (e.g. Getty AAT) only declare this on the
                            # concept side rather than using hasTopConcept on the scheme.
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
                                if mock_tile:
                                    new_concept["tile_data"].append(mock_tile)
                        else:
                            mock_tile = self.map_predicate_object_to_mock_tile(
                                object, predicate_str, isScheme
                            )
                            if mock_tile:
                                new_concept["tile_data"].append(mock_tile)

                    type_tile = {
                        "type": {"type": "concept", "type_metatype": "classification"}
                    }
                    new_concept["tile_data"].append(type_tile)

                    self.concepts.append(new_concept)

            # Map relationships to their respective concept resources
            for concept in self.concepts:
                if self.relations.get(concept["resourceinstanceid"]):
                    concept["tile_data"].extend(
                        self.relations.get(concept["resourceinstanceid"])
                    )

            return self.schemes, self.concepts

    def extract_from_skos_xml_file(self, file, overwrite_options="overwrite"):
        """
        Streaming replacement for read_file() + extract_concepts_from_skos_for_lingo_import()
        for SKOS RDF/XML files in the standard serialisation format (one <skos:Concept>
        element per concept at the document root level).

        Uses xml.etree.ElementTree.iterparse() instead of rdflib.  rdflib parses the
        whole XML into an in-memory triple store before any concept is processed; the
        per-triple Python overhead makes it very slow for large files (e.g. 90 MB AAT
        with 58k+ concepts takes 30+ minutes under rdflib).  ET streams element-by-element,
        builds mock tiles as it goes, and discards parsed XML immediately — reducing the
        parse-and-extract phase from ~30 minutes to ~2 minutes.
        """
        baseuuid = uuid.uuid4()
        self.allowed_languages = {}
        for lang in models.Language.objects.all():
            self.allowed_languages[lang.code] = lang
        self.default_lang = settings.LANGUAGE_CODE

        value_types = models.DValueType.objects.all()
        skos_value_types = value_types.filter(
            Q(namespace="skos") | Q(namespace="arches")
        )
        self.skos_value_types = set(
            skos_value_types.values_list("valuetype", flat=True)
        )
        self.skos_note_and_label_types = set(
            skos_value_types.filter(
                Q(category="note") | Q(category="label")
            ).values_list("valuetype", flat=True)
        )
        self.dcterms_value_types = set(
            value_types.filter(namespace="dcterms").values_list("valuetype", flat=True)
        )
        self.match_types = set(
            models.DRelationType.objects.filter(
                category="Mapping Properties"
            ).values_list("relationtype", flat=True)
        )

        # XML namespace URIs used by SKOS RDF/XML files.
        RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
        DCTERMS_NS = "http://purl.org/dc/terms/"
        XML_NS = "http://www.w3.org/XML/1998/namespace"

        ATTR_ABOUT = f"{{{RDF_NS}}}about"
        ATTR_RESOURCE = f"{{{RDF_NS}}}resource"
        ATTR_LANG = f"{{{XML_NS}}}lang"

        TAG_CONCEPT_SCHEME = f"{{{SKOS_NS}}}ConceptScheme"
        TAG_CONCEPT = f"{{{SKOS_NS}}}Concept"
        TAG_PREF_LABEL = f"{{{SKOS_NS}}}prefLabel"
        TAG_ALT_LABEL = f"{{{SKOS_NS}}}altLabel"
        TAG_HIDDEN_LABEL = f"{{{SKOS_NS}}}hiddenLabel"
        TAG_SCOPE_NOTE = f"{{{SKOS_NS}}}scopeNote"
        TAG_NOTE = f"{{{SKOS_NS}}}note"
        TAG_BROADER = f"{{{SKOS_NS}}}broader"
        TAG_NARROWER = f"{{{SKOS_NS}}}narrower"
        TAG_RELATED = f"{{{SKOS_NS}}}related"
        TAG_IN_SCHEME = f"{{{SKOS_NS}}}inScheme"
        TAG_TOP_CONCEPT_OF = f"{{{SKOS_NS}}}topConceptOf"
        TAG_HAS_TOP_CONCEPT = f"{{{SKOS_NS}}}hasTopConcept"
        TAG_IDENTIFIER = f"{{{DCTERMS_NS}}}identifier"
        TAG_EXACT_MATCH = f"{{{SKOS_NS}}}exactMatch"
        TAG_CLOSE_MATCH = f"{{{SKOS_NS}}}closeMatch"
        TAG_BROAD_MATCH = f"{{{SKOS_NS}}}broadMatch"
        TAG_NARROW_MATCH = f"{{{SKOS_NS}}}narrowMatch"
        TAG_RELATED_MATCH = f"{{{SKOS_NS}}}relatedMatch"

        LABEL_TAGS = {
            TAG_PREF_LABEL: "prefLabel",
            TAG_ALT_LABEL: "altLabel",
            TAG_HIDDEN_LABEL: "hiddenLabel",
        }
        NOTE_TAGS = {
            TAG_SCOPE_NOTE: "scopeNote",
            TAG_NOTE: "note",
        }
        MATCH_TAGS = {
            TAG_EXACT_MATCH: "exactMatch",
            TAG_CLOSE_MATCH: "closeMatch",
            TAG_BROAD_MATCH: "broadMatch",
            TAG_NARROW_MATCH: "narrowMatch",
            TAG_RELATED_MATCH: "relatedMatch",
        }

        self.schemes = []
        self.concepts = []
        self.relations = defaultdict(list)

        # Accumulated from skos:hasTopConcept on the scheme element; applied when
        # the corresponding concept element is reached.
        top_concept_mock_tiles = {}

        # Shared across all concepts since it carries only constant values.
        concept_type_tile = {
            "type": {"type": "concept", "type_metatype": "classification"}
        }

        if hasattr(file, "seek"):
            file.seek(0)

        for _event, elem in ET.iterparse(file, events=("end",)):
            tag = elem.tag

            if tag == TAG_CONCEPT_SCHEME:
                uri = elem.get(ATTR_ABOUT)
                if not uri:
                    elem.clear()
                    continue

                scheme_pk = self.generate_uuidv5_from_subject(baseuuid, uri)
                tile_data = []
                has_pref_label = False

                for child in elem:
                    child_tag = child.tag
                    if child_tag in LABEL_TAGS:
                        lang_name = self._language_display_name(child.get(ATTR_LANG))
                        tile_data.append(
                            {
                                "appellative_status": {
                                    "appellative_status_ascribed_name_content": child.text
                                    or "",
                                    "appellative_status_ascribed_name_language": lang_name,
                                    "appellative_status_ascribed_relation": LABEL_TAGS[
                                        child_tag
                                    ],
                                }
                            }
                        )
                        if child_tag == TAG_PREF_LABEL:
                            has_pref_label = True
                    elif child_tag == TAG_HAS_TOP_CONCEPT:
                        top_concept_uri = child.get(ATTR_RESOURCE)
                        if top_concept_uri:
                            top_concept_id = self.generate_uuidv5_from_subject(
                                baseuuid, top_concept_uri
                            )
                            top_concept_mock_tiles[top_concept_id] = (
                                LingoResourceImporter.create_mock_tile_from_relationship(
                                    {
                                        "resourceId": scheme_pk,
                                        "node_alias": "top_concept_of",
                                        "nodegroup_alias": "top_concept_of",
                                        "resourceinstanceid": top_concept_id,
                                    }
                                )
                            )

                if not has_pref_label:
                    tile_data.append(
                        {
                            "appellative_status": {
                                "appellative_status_ascribed_name_content": uri,
                                "appellative_status_ascribed_name_language": self._language_display_name(
                                    None
                                ),
                                "appellative_status_ascribed_relation": "prefLabel",
                            }
                        }
                    )

                self.schemes.append(
                    {
                        "resourceinstanceid": scheme_pk,
                        "legacyid": uri,
                        "type": "Scheme",
                        "tile_data": tile_data,
                    }
                )
                elem.clear()

            elif tag == TAG_CONCEPT:
                uri = elem.get(ATTR_ABOUT)
                if not uri:
                    elem.clear()
                    continue

                concept_pk = self.generate_uuidv5_from_subject(baseuuid, uri)
                tile_data = [concept_type_tile]
                scheme_pk = None

                for child in elem:
                    child_tag = child.tag

                    if child_tag == TAG_IN_SCHEME:
                        scheme_uri = child.get(ATTR_RESOURCE)
                        if scheme_uri:
                            scheme_pk = self.generate_uuidv5_from_subject(
                                baseuuid, scheme_uri
                            )

                    elif child_tag == TAG_TOP_CONCEPT_OF:
                        scheme_uri = child.get(ATTR_RESOURCE)
                        if scheme_uri:
                            scheme_of_top_pk = self.generate_uuidv5_from_subject(
                                baseuuid, scheme_uri
                            )
                            tile_data.append(
                                LingoResourceImporter.create_mock_tile_from_relationship(
                                    {
                                        "resourceId": scheme_of_top_pk,
                                        "node_alias": "top_concept_of",
                                        "nodegroup_alias": "top_concept_of",
                                        "resourceinstanceid": concept_pk,
                                    }
                                )
                            )

                    elif child_tag in LABEL_TAGS:
                        lang_name = self._language_display_name(child.get(ATTR_LANG))
                        tile_data.append(
                            {
                                "appellative_status": {
                                    "appellative_status_ascribed_name_content": child.text
                                    or "",
                                    "appellative_status_ascribed_name_language": lang_name,
                                    "appellative_status_ascribed_relation": LABEL_TAGS[
                                        child_tag
                                    ],
                                }
                            }
                        )

                    elif child_tag in NOTE_TAGS:
                        lang_name = self._language_display_name(child.get(ATTR_LANG))
                        tile_data.append(
                            {
                                "statement": {
                                    "statement_content": child.text or "",
                                    "statement_type": NOTE_TAGS[child_tag],
                                    "statement_language": lang_name,
                                }
                            }
                        )

                    elif child_tag == TAG_BROADER:
                        broader_uri = child.get(ATTR_RESOURCE)
                        if broader_uri:
                            broader_pk = self.generate_uuidv5_from_subject(
                                baseuuid, broader_uri
                            )
                            self.relations[concept_pk].append(
                                LingoResourceImporter.create_mock_tile_from_relationship(
                                    {
                                        "resourceId": broader_pk,
                                        "node_alias": "classification_status_ascribed_classification",
                                        "nodegroup_alias": "classification_status",
                                        "resourceinstanceid": concept_pk,
                                    }
                                )
                            )

                    elif child_tag == TAG_NARROWER:
                        narrower_uri = child.get(ATTR_RESOURCE)
                        if narrower_uri:
                            narrower_pk = self.generate_uuidv5_from_subject(
                                baseuuid, narrower_uri
                            )
                            self.relations[narrower_pk].append(
                                LingoResourceImporter.create_mock_tile_from_relationship(
                                    {
                                        "resourceId": concept_pk,
                                        "node_alias": "classification_status_ascribed_classification",
                                        "nodegroup_alias": "classification_status",
                                        "resourceinstanceid": narrower_pk,
                                    }
                                )
                            )

                    elif child_tag == TAG_RELATED:
                        related_uri = child.get(ATTR_RESOURCE)
                        if related_uri:
                            related_pk = self.generate_uuidv5_from_subject(
                                baseuuid, related_uri
                            )
                            self.relations[related_pk].append(
                                LingoResourceImporter.create_mock_tile_from_relationship(
                                    {
                                        "resourceId": concept_pk,
                                        "node_alias": "relation_status_ascribed_comparate",
                                        "nodegroup_alias": "relation_status",
                                        "resourceinstanceid": related_pk,
                                    }
                                )
                            )

                    elif child_tag == TAG_IDENTIFIER:
                        identifier_text = child.text
                        if identifier_text:
                            tile_data.append(
                                {
                                    "match_status": {
                                        "match_status_ascribed_comparate": identifier_text,
                                        "match_status_ascribed_relation": "exactMatch",
                                    }
                                }
                            )

                    elif child_tag in MATCH_TAGS:
                        match_uri = child.get(ATTR_RESOURCE)
                        if match_uri:
                            tile_data.append(
                                {
                                    "match_status": {
                                        "match_status_ascribed_comparate": match_uri,
                                        "match_status_ascribed_relation": MATCH_TAGS[
                                            child_tag
                                        ],
                                    }
                                }
                            )

                if top_concept_mock_tiles.get(concept_pk):
                    tile_data.append(top_concept_mock_tiles[concept_pk])

                if scheme_pk:
                    tile_data.append(
                        LingoResourceImporter.create_mock_tile_from_relationship(
                            {
                                "resourceId": scheme_pk,
                                "node_alias": "part_of_scheme",
                                "nodegroup_alias": "part_of_scheme",
                                "resourceinstanceid": concept_pk,
                            }
                        )
                    )

                self.concepts.append(
                    {
                        "resourceinstanceid": concept_pk,
                        "legacyid": uri,
                        "type": "Concept",
                        "tile_data": tile_data,
                    }
                )
                elem.clear()

        for concept in self.concepts:
            concept_relations = self.relations.get(concept["resourceinstanceid"])
            if concept_relations:
                concept["tile_data"].extend(concept_relations)

        return self.schemes, self.concepts

    def _resolve_language_code(self, lang_code):
        """
        Return the key for lang_code as it is stored in self.allowed_languages,
        creating a Language DB record for unknown BCP-47 tags.  Returns
        self.default_lang when lang_code is absent or blank.
        """
        if not lang_code or not lang_code.strip():
            return self.default_lang
        lower_code = lang_code.lower()
        match = next(
            (code for code in self.allowed_languages if code.lower() == lower_code),
            None,
        )
        if match:
            return match
        # Refresh cache — another worker or earlier call may have added this language.
        for lang in models.Language.objects.all():
            self.allowed_languages[lang.code] = lang
        match = next(
            (code for code in self.allowed_languages if code.lower() == lower_code),
            None,
        )
        if match:
            return match
        # Truly unknown tag — create a minimal Language record so the import does
        # not silently drop labels in that language.
        from arches.app.utils.i18n import capitalize_region

        new_lang = models.Language(
            code=capitalize_region(lang_code),
            name=lang_code,
            default_direction="ltr",
            isdefault=False,
        )
        new_lang.save()
        self.allowed_languages[new_lang.code] = new_lang
        return new_lang.code

    def _language_display_name(self, lang_code):
        """
        Return the display name string (e.g. "English") for a language code,
        creating a Language DB record for unknown BCP-47 tags if necessary.
        This is the value expected by the appellative_status and statement node
        aliases in populate_staging_table → create_tile_value.
        """
        resolved_code = self._resolve_language_code(lang_code)
        lang = self.allowed_languages.get(resolved_code)
        if isinstance(lang, models.Language):
            return lang.name
        return resolved_code
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
            mock_tile, isScheme=isScheme, lang_lookup=self.allowed_languages
        )
        return mock_tile


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
