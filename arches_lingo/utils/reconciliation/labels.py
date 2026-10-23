from django.utils.translation import pgettext

from arches.app.utils.i18n import rank_label

from arches_lingo.const import (
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_TYPE_NODE,
)
from arches_lingo.utils.concept_builder import ConceptBuilder


def choose_display_label_tile(
    label_tiles, content_node, type_node, language_node, target_language=None
):
    """Pick the label tile best suited to ``target_language`` (default: the
    active language), prefLabels first. A tile missing its type or language
    ranks last rather than failing the whole request."""
    named_label_tiles = [
        label_tile for label_tile in label_tiles if label_tile.get(content_node)
    ]
    if not named_label_tiles:
        return None
    return max(
        named_label_tiles,
        key=lambda label_tile: rank_label(
            kind=ConceptBuilder.find_valuetype_id_from_uri(
                (label_tile.get(type_node) or [{}])[0].get("uri")
            ),
            source_lang=label_tile.get(language_node) or "",
            target_lang=target_language or "",
        ),
    )


def choose_display_label(
    label_tiles, content_node, type_node, language_node, target_language=None
):
    best_label_tile = choose_display_label_tile(
        label_tiles, content_node, type_node, language_node, target_language
    )
    return None if best_label_tile is None else best_label_tile[content_node]


def join_labels(labels):
    return pgettext("separator between items in a list", ", ").join(labels)


def get_scheme_display_names(schemes, target_language=None):
    """Return ``{scheme_id: name}`` for a scheme queryset, in one query."""
    return {
        str(scheme.pk): choose_display_label(
            scheme.labels,
            SCHEME_NAME_CONTENT_NODE,
            SCHEME_NAME_TYPE_NODE,
            SCHEME_NAME_LANGUAGE_NODE,
            target_language,
        )
        or str(scheme.name)
        or str(scheme.pk)
        for scheme in schemes.annotate(
            labels=ConceptBuilder.labels_subquery(SCHEME_NAME_NODEGROUP)
        )
    }


def is_same_base_language(language_code, other_language_code):
    return (language_code or "").split("-")[0].casefold() == (
        other_language_code or ""
    ).split("-")[0].casefold()
