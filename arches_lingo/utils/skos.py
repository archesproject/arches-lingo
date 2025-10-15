import uuid
from collections import defaultdict
from django.db.models import Q
from rdflib import Literal, Namespace, RDF
from rdflib.namespace import SKOS, DCTERMS
from rdflib.graph import Graph
from arches.app.models import models
from arches.app.models.system_settings import settings
from arches_querysets.models import ResourceTileTree

from arches_controlled_lists.utils.skos import SKOSReader, SKOSWriter

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

    def extract_concepts_from_skos_for_lingo_import(
        self, graph, overwrite_options="overwrite"
    ):
        baseuuid = uuid.uuid4()
        allowed_languages = {}
        for lang in models.Language.objects.all():
            allowed_languages[lang.code] = lang
        default_lang = settings.LANGUAGE_CODE
        self.language_lookup = {
            lang.code: lang.name for lang in models.Language.objects.all()
        }

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
                        # TODO: This should check if the language is in the Languages controlled list, not in models.Language
                        # re. https://github.com/archesproject/arches-lingo/issues/472
                        # if not self.language_exists(object, allowed_languages):
                        #     for lang in models.Language.objects.all():
                        #         allowed_languages[lang.code] = lang

                        val = self.unwrapJsonLiteral(object)
                        mock_tile = {
                            "id": val["value_id"],
                            "value": val["value"],
                            "language_id": object.language or default_lang,
                            "valuetype_id": predicate_str,
                        }
                        mock_tile = LingoResourceImporter.create_mock_tile_from_value(
                            mock_tile, lang_lookup=self.language_lookup
                        )
                        new_scheme["tile_data"].append(mock_tile)

                    elif predicate == SKOS.hasTopConcept:
                        top_concept_id = self.generate_uuidv5_from_subject(
                            baseuuid, object
                        )
                        self.relations[scheme_pk].append(
                            {
                                "source": scheme_pk,
                                "type": "hasTopConcept",
                                "target": top_concept_id,
                            }
                        )

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
                        mock_tile, lang_lookup=self.language_lookup
                    )
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

                    # new_concept["tile_data"][SKOS.inScheme].append(
                    #     {
                    #         "id": scheme_pk,
                    #         "value": scheme_pk,
                    #         "valuetype_id": skos_value_types.get("inScheme"),
                    #     }
                    # )

                    for predicate, object in graph.predicate_objects(concept):
                        predicate_str = (
                            predicate.replace(ARCHES, "")
                            .replace(SKOS, "")
                            .replace(DCTERMS, "")
                        )

                        if str(SKOS) in predicate or str(ARCHES) in predicate:
                            # TODO: This should check if the language is in the Languages controlled list, not in models.Language
                            # re. https://github.com/archesproject/arches-lingo/issues/472
                            # if not self.language_exists(object, allowed_languages):
                            #     for lang in models.Language.objects.all():
                            #         allowed_languages[lang.code] = lang

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
                                        mock_tile, lang_lookup=self.language_lookup
                                    )
                                )
                                new_concept["tile_data"].append(mock_tile)

                            elif predicate == SKOS.broader:
                                broader_concept_id = self.generate_uuidv5_from_subject(
                                    baseuuid, object
                                )
                                self.relations[broader_concept_id].append(
                                    {
                                        "source": broader_concept_id,
                                        "type": "narrower",
                                        "target": concept_pk,
                                    }
                                )
                            elif predicate == SKOS.narrower:
                                self.relations[concept_pk].append(
                                    {
                                        "source": concept_pk,
                                        "type": "narrower",
                                        "target": self.generate_uuidv5_from_subject(
                                            baseuuid, object
                                        ),
                                    }
                                )
                            elif predicate == SKOS.related:
                                self.relations[concept_pk].append(
                                    {
                                        "source": concept_pk,
                                        "type": "related",
                                        "target": self.generate_uuidv5_from_subject(
                                            baseuuid, object
                                        ),
                                    }
                                )

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
                            mock_tile, lang_lookup=self.language_lookup
                        )
                        new_concept["tile_data"].append(mock_tile)

                    self.concepts.append(new_concept)

    def orchestrate_bulk_import_from_skos(self, graph, overwrite_options):
        self.loadid = str(uuid.uuid4())
        bulk_loader = LingoResourceImporter(
            loadid=self.loadid,
            userid=models.User.objects.get(username="admin").pk,
            mode="cli",
        )

        # TODO: BDM error handling
        start_request = bulk_loader.start(request=None)
        self.extract_concepts_from_skos_for_lingo_import(
            graph, overwrite_options=overwrite_options
        )
        write_request = bulk_loader.write(
            request=None,
            schemes=self.schemes,
            concepts=self.concepts,
            relations=self.relations,
        )
