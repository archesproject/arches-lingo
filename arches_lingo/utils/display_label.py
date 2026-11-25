from arches.app.models.models import TileModel
from arches.app.utils.i18n import rank_label

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_TYPE_NODE,
)
from arches_lingo.utils.concept_builder import ConceptBuilder

LABEL_NODES_BY_NODEGROUP = {
    SCHEME_NAME_NODEGROUP: (
        SCHEME_NAME_CONTENT_NODE,
        SCHEME_NAME_LANGUAGE_NODE,
        SCHEME_NAME_TYPE_NODE,
    ),
    CONCEPT_NAME_NODEGROUP: (
        CONCEPT_NAME_CONTENT_NODE,
        CONCEPT_NAME_LANGUAGE_NODE,
        CONCEPT_NAME_TYPE_NODE,
    ),
}


def get_display_label(resource_id, language_code=None):
    """The scheme or concept label the client would show, ranked as getItemLabel
    ranks it: preferred over alternate, the user's language over the system
    language. Unlike the stored resource name, this follows the labels as edited.
    """
    candidate_labels = []
    for nodegroup_id, tile_data in TileModel.objects.filter(
        resourceinstance_id=resource_id,
        nodegroup_id__in=list(LABEL_NODES_BY_NODEGROUP),
    ).values_list("nodegroup_id", "data"):
        content_node, language_node, type_node = LABEL_NODES_BY_NODEGROUP[
            str(nodegroup_id)
        ]
        value = tile_data.get(content_node)
        label_types = tile_data.get(type_node) or []
        if not value or not label_types:
            continue
        candidate_labels.append(
            {
                "value": value,
                "language_id": tile_data.get(language_node) or "",
                "valuetype_id": ConceptBuilder.find_valuetype_id_from_uri(
                    label_types[0].get("uri")
                ),
            }
        )

    if not candidate_labels:
        return ""

    best_label = max(
        candidate_labels,
        key=lambda label: rank_label(
            kind=label["valuetype_id"],
            source_lang=label["language_id"],
            target_lang=language_code,
        ),
    )
    return best_label["value"]
