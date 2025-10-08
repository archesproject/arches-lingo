import uuid
from collections import defaultdict
from django.db.models import Q
from rdflib import Literal, Namespace, RDF
from rdflib.namespace import SKOS, DCTERMS
from rdflib.graph import Graph
from arches.app.models.models import (
    DValueType,
    Graph as ArchesGraphModel,
    Language,
    ResourceInstance,
    ResourceInstanceLifecycleState,
)
from arches.app.models.system_settings import settings
from arches_querysets.models import ResourceTileTree

from arches_controlled_lists.utils.skos import SKOSReader, SKOSWriter

# define the ARCHES namespace
ARCHES = Namespace(settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT)


class SKOSReader(SKOSReader):
    """
    Extends the SKOSReader class from Arches Controlled Lists to import RDF graphs as Lingo resources.

    """

    def save_lingo_resources_from_skos(self, graph, overwrite_options="overwrite"):
        baseuuid = uuid.uuid4()
        allowed_languages = {}
        for lang in Language.objects.all():
            allowed_languages[lang.code] = lang
        default_lang = allowed_languages[settings.LANGUAGE_CODE]

        # scheme_model = ArchesGraphModel.objects.get(slug="scheme")
        if isinstance(graph, Graph):

            # Create lookups for valuetypes used during Concept processing
            value_types = DValueType.objects.all()
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
                    "tile_data": defaultdict(list),
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
                            for lang in Language.objects.all():
                                allowed_languages[lang.code] = lang

                        value_type = dcterms_value_types.get(valuetype=predicate_str)
                        val = self.unwrapJsonLiteral(object)
                        mock_tile = {
                            "id": val["value_id"],
                            "value": val["value"],
                            "language": object.language or default_lang,
                            "value_type": value_type,
                        }
                        new_scheme["tile_data"][predicate].append(mock_tile)

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

                if len(new_scheme["tile_data"][DCTERMS.identifier]) == 0:
                    identifier = self.unwrapJsonLiteral(str(scheme))
                    mock_tile = {
                        "id": identifier["value_id"],
                        "value": identifier["value"],
                        "language": default_lang,
                        "type": "identifier",
                        "category": "identifiers",
                    }
                    new_scheme["tile_data"][DCTERMS.identifier].append(mock_tile)

                self.nodes.append(new_scheme)

                ### Concepts ###
                for concept, v, o in graph.triples((None, SKOS.inScheme, scheme)):
                    concept_pk = self.generate_uuidv5_from_subject(baseuuid, concept)
                    new_concept = {
                        "resourceinstanceid": concept_pk,
                        "legacyid": str(concept),
                        "type": "Concept",
                        "tile_data": defaultdict(list),
                    }

                    new_concept["tile_data"][SKOS.inScheme].append(
                        {
                            "id": scheme_pk,
                            "value": scheme_pk,
                            "value_type": skos_value_types.get("inScheme"),
                        }
                    )

                    for predicate, object in graph.predicate_objects(concept):
                        predicate_str = (
                            predicate.replace(ARCHES, "")
                            .replace(SKOS, "")
                            .replace(DCTERMS, "")
                        )

                        if str(SKOS) in predicate or str(ARCHES) in predicate:
                            if not self.language_exists(object, allowed_languages):
                                for lang in Language.objects.all():
                                    allowed_languages[lang.code] = lang

                            if predicate_str in skos_value_types:
                                value_type = skos_value_types.get(predicate_str)
                                val = self.unwrapJsonLiteral(object)
                                mock_tile = {
                                    "id": val["value_id"],
                                    "value": val["value"],
                                    "language": object.language or default_lang,
                                    "value_type": value_type,
                                }
                                new_concept["tile_data"][predicate].append(mock_tile)

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

                    if len(new_concept["tile_data"][DCTERMS.identifier]) == 0:
                        identifier = self.unwrapJsonLiteral(str(scheme))
                        mock_tile = {
                            "id": identifier["value_id"],
                            "value": identifier["value"],
                            "language": default_lang,
                            "type": "identifier",
                            "category": "identifiers",
                        }
                        new_concept["tile_data"][DCTERMS.identifier].append(mock_tile)

                    self.nodes.append(new_concept)
        self.save_nodes_and_relations(overwrite_options=overwrite_options)
