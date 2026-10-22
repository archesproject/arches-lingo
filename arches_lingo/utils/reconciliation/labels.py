from arches.app.utils.i18n import rank_label

from arches_lingo.utils.concept_builder import ConceptBuilder


def choose_display_label(
    label_tiles, content_node, type_node, language_node, target_language=None
):
    """Pick the label best suited to ``target_language`` (default: the active
    language), prefLabels first."""
    named_label_tiles = [
        label_tile for label_tile in label_tiles if label_tile.get(content_node)
    ]
    if not named_label_tiles:
        return None
    best_label_tile = max(
        named_label_tiles,
        key=lambda label_tile: rank_label(
            kind=ConceptBuilder.find_valuetype_id_from_uri(
                label_tile[type_node][0]["uri"]
            ),
            source_lang=label_tile[language_node],
            target_lang=target_language or "",
        ),
    )
    return best_label_tile[content_node]


def is_same_base_language(language_code, other_language_code):
    return (language_code or "").split("-")[0].casefold() == (
        other_language_code or ""
    ).split("-")[0].casefold()
