from arches.app.models.models import ResourceIdentifier, TileModel

from arches_lingo.const import (
    CONCEPTS_GRAPH_ID,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    SCHEMES_GRAPH_ID,
    IDENTIFIER_SOURCE,
)


def resolve_scheme_identifier(scheme_identifier):
    return (
        ResourceIdentifier.objects.filter(
            identifier=scheme_identifier,
            source=IDENTIFIER_SOURCE,
            resourceid__graph_id=SCHEMES_GRAPH_ID,
        )
        .values_list("resourceid", flat=True)
        .first()
    )


def resolve_concept_identifier(scheme_identifier, concept_identifier):
    """Concept identifiers are numbered per scheme, so the same identifier
    exists in every scheme; only a concept in the named scheme matches."""
    scheme_resource_instance_id = resolve_scheme_identifier(scheme_identifier)
    if scheme_resource_instance_id is None:
        return None

    concepts_in_scheme = TileModel.objects.filter(
        nodegroup_id=CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
        **{
            f"data__{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}__contains": [
                {"resourceId": str(scheme_resource_instance_id)}
            ]
        },
    ).values("resourceinstance_id")

    return (
        ResourceIdentifier.objects.filter(
            identifier=concept_identifier,
            source=IDENTIFIER_SOURCE,
            resourceid__graph_id=CONCEPTS_GRAPH_ID,
            resourceid__in=concepts_in_scheme,
        )
        .values_list("resourceid", flat=True)
        .first()
    )


def resolve_identifier_route(scheme_identifier, concept_identifier=None):
    if concept_identifier:
        return resolve_concept_identifier(scheme_identifier, concept_identifier)
    return resolve_scheme_identifier(scheme_identifier)
