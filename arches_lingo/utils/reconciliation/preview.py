import uuid

from django.conf import settings
from django.utils.translation import get_language

from arches.app.models.models import TileModel

from arches_lingo.const import (
    ALT_LABEL_URI,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
)
from arches_lingo.utils.concept_lifecycle import RETIRED_STATE_ID
from arches_lingo.utils.reconciliation.concept_summaries import (
    get_lifecycle_state_ids,
    summarize_concepts,
)
from arches_lingo.utils.reconciliation.labels import (
    choose_display_label_tile,
    is_same_base_language,
    join_labels,
)
from arches_lingo.utils.reconciliation.manifest import concept_identifier_space
from arches_lingo.utils.reconciliation.visibility import (
    SEARCHED_LIFECYCLE_STATE_IDS,
)
from arches_lingo.utils.search_service import (
    get_notes_for_concepts,
    get_uris_for_concepts,
)

# Kept short so the card fits OpenRefine's preview iframe.
MAX_PREVIEW_ALTERNATE_LABELS = 3
# Enough notes to usually find one in the active language.
MAX_PREVIEW_NOTE_CANDIDATES = 20


def choose_alternate_labels(label_tiles, display_language):
    alternate_labels = sorted(
        label_tile[CONCEPT_NAME_CONTENT_NODE]
        for label_tile in label_tiles
        if label_tile.get(CONCEPT_NAME_CONTENT_NODE)
        and (label_tile.get(CONCEPT_NAME_TYPE_NODE) or [{}])[0].get("uri")
        == ALT_LABEL_URI
        and is_same_base_language(
            label_tile.get(CONCEPT_NAME_LANGUAGE_NODE), display_language
        )
    )
    return join_labels(alternate_labels[:MAX_PREVIEW_ALTERNATE_LABELS])


def choose_preview_note(concept_id, display_language):
    notes = get_notes_for_concepts(
        [concept_id],
        limit_per_concept=MAX_PREVIEW_NOTE_CANDIDATES,
        label_language=display_language,
    ).get(concept_id, [])
    notes_with_content = [note for note in notes if note["content"]]
    for note in notes_with_content:
        if is_same_base_language(note["language"], display_language):
            return note
    return notes_with_content[0] if notes_with_content else None


def build_concept_preview(raw_concept_id):
    """Return the preview card context for a public concept, or None.

    Unknown and non-public ids both return None, so the preview cannot be used
    to discover whether a draft exists.
    """
    try:
        concept_id = str(uuid.UUID(str(raw_concept_id)))
    except ValueError:
        return None

    lifecycle_state_id = get_lifecycle_state_ids([concept_id]).get(concept_id)
    if lifecycle_state_id not in SEARCHED_LIFECYCLE_STATE_IDS:
        return None
    display_language = get_language() or settings.LANGUAGE_CODE
    summary = summarize_concepts([concept_id], display_language).get(concept_id)
    if summary is None:
        return None

    label_tiles = list(
        TileModel.objects.filter(
            nodegroup_id=CONCEPT_NAME_NODEGROUP, resourceinstance_id=concept_id
        ).values_list("data", flat=True)
    )
    # The name may fall back to another language, which the card marks up.
    name_tile = choose_display_label_tile(
        label_tiles,
        CONCEPT_NAME_CONTENT_NODE,
        CONCEPT_NAME_TYPE_NODE,
        CONCEPT_NAME_LANGUAGE_NODE,
        display_language,
    )
    return {
        "name": summary["name"],
        "name_language": (name_tile or {}).get(CONCEPT_NAME_LANGUAGE_NODE),
        "description": summary["description"],
        "alternate_labels": choose_alternate_labels(label_tiles, display_language),
        "note": choose_preview_note(concept_id, display_language),
        "uri": get_uris_for_concepts([concept_id]).get(concept_id),
        "view_url": f"{concept_identifier_space()}{concept_id}",
        "is_retired": lifecycle_state_id == RETIRED_STATE_ID,
    }
