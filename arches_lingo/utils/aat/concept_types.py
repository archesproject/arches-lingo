"""Assign AAT concept types to concepts that are already loaded.

The SKOS import gives every AAT concept the type "concept". Getty's export
distinguishes three further kinds, none of which it states as data: they are
recognisable only from the shape of the English preferred label and, for the
facets, the presence of ``skos:topConceptOf``.

  - **facet** -- the 8 top-level organisational facets (e.g. "Agents Facet").
  - **hierarchy name** -- the ~39 hierarchical group nodes directly beneath a
    facet (e.g. "Built Complexes and Districts (hierarchy name)").
  - **guide term** -- the ~1,800 non-indexable organisational terms displayed
    with angle brackets (e.g. ``<complexes by function>``).

All other concepts keep the default "concept" type. The three items above must
be present in the term types controlled list, which ships in
``pkg/reference_data/controlled_lists/term_types.xml``.
"""

import json
import xml.etree.ElementTree as ET

from django.db import connection

from arches_controlled_lists.models import ListItem

from arches_lingo import const

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
XML_NS = "http://www.w3.org/XML/1998/namespace"

SKOS_CONCEPT_TAG = f"{{{SKOS_NS}}}Concept"
SKOS_PREF_LABEL_TAG = f"{{{SKOS_NS}}}prefLabel"
SKOS_TOP_CONCEPT_OF_TAG = f"{{{SKOS_NS}}}topConceptOf"
RDF_ABOUT_ATTR = f"{{{RDF_NS}}}about"
XML_LANG_ATTR = f"{{{XML_NS}}}lang"

# Concept type label strings as stored in the term types controlled list.
CONCEPT_TYPE_CONCEPT = "concept"
CONCEPT_TYPE_GUIDE_TERM = "guide term"
CONCEPT_TYPE_HIERARCHY_NAME = "hierarchy name"
CONCEPT_TYPE_FACET = "facet"

NON_CONCEPT_TYPES = (
    CONCEPT_TYPE_GUIDE_TERM,
    CONCEPT_TYPE_HIERARCHY_NAME,
    CONCEPT_TYPE_FACET,
)


class MissingConceptTypeItemsError(Exception):
    """Raised when the term types controlled list lacks the AAT concept types."""

    def __init__(self, missing_labels):
        self.missing_labels = sorted(missing_labels)
        super().__init__(
            "The following concept type list items are missing from the "
            f"database: {self.missing_labels}. Load "
            "pkg/reference_data/controlled_lists/term_types.xml to add them."
        )


def classify_aat_concept(english_label, has_top_concept_of):
    """
    Return the concept type label for an AAT concept based on its English
    preferred label and whether it has a ``skos:topConceptOf`` triple.

    Classification rules (applied in priority order):
      1. ``skos:topConceptOf`` present **and** label ends with " Facet" → "facet"
      2. "(hierarchy name)" in the label → "hierarchy name"
      3. Label starts with "<" and ends with ">" → "guide term"
      4. Otherwise → "concept"
    """
    if not english_label:
        return CONCEPT_TYPE_CONCEPT
    if has_top_concept_of and english_label.endswith(" Facet"):
        return CONCEPT_TYPE_FACET
    if "(hierarchy name)" in english_label:
        return CONCEPT_TYPE_HIERARCHY_NAME
    if english_label.startswith("<") and english_label.endswith(">"):
        return CONCEPT_TYPE_GUIDE_TERM
    return CONCEPT_TYPE_CONCEPT


def parse_aat_concept_types(skos_path):
    """
    Stream-parse the AAT SKOS XML file and return a dict mapping each AAT
    concept URI to its concept type label.

    Only concepts whose type differs from "concept" are included in the result
    to keep memory usage proportional to the number of non-standard types.

    Uses paired ``start``/``end`` events so that child elements (prefLabel,
    topConceptOf) can be cleared individually as they close, without waiting
    for the parent Concept element to accumulate all children in memory.
    """
    non_concept_type_map = {}

    current_concept_uri = None
    current_english_label = None
    current_has_top_concept_of = False

    for event, elem in ET.iterparse(skos_path, events=("start", "end")):
        tag = elem.tag

        if event == "start":
            if tag == SKOS_CONCEPT_TAG:
                current_concept_uri = elem.get(RDF_ABOUT_ATTR)
                current_english_label = None
                current_has_top_concept_of = False

        elif event == "end":
            if tag == SKOS_PREF_LABEL_TAG and elem.get(XML_LANG_ATTR) == "en":
                if current_english_label is None:
                    current_english_label = elem.text or ""
                elem.clear()
            elif tag == SKOS_TOP_CONCEPT_OF_TAG:
                current_has_top_concept_of = True
                elem.clear()
            elif tag == SKOS_CONCEPT_TAG:
                if current_concept_uri:
                    concept_type = classify_aat_concept(
                        current_english_label, current_has_top_concept_of
                    )
                    if concept_type != CONCEPT_TYPE_CONCEPT:
                        non_concept_type_map[current_concept_uri] = concept_type
                elem.clear()
                current_concept_uri = None

    return non_concept_type_map


def load_non_concept_type_items():
    """
    Return a dict mapping concept type label → ``ListItem`` for all non-concept
    type items in the term types controlled list.

    Raises ``MissingConceptTypeItemsError`` if any expected type is missing,
    which means the term types controlled list has not been loaded.
    """
    items_by_label = {}
    for item in ListItem.objects.filter(
        list_id=const.CONCEPT_TYPE_LIST_ID
    ).prefetch_related("list_item_values"):
        for value in item.list_item_values.filter(
            valuetype_id="prefLabel", language_id="en"
        ):
            if value.value in NON_CONCEPT_TYPES:
                items_by_label[value.value] = item

    missing = set(NON_CONCEPT_TYPES) - set(items_by_label)
    if missing:
        raise MissingConceptTypeItemsError(missing)
    return items_by_label


def update_concept_type_tiles(uris_by_type, type_items_by_label, dry_run=False):
    """
    Update the concept type tiles for all resources whose AAT URI appears in
    ``uris_by_type``.

    Performs one SQL UPDATE per concept type so that all resources of the same
    type are updated in a single round-trip.  The URI lookup joins on the
    ``URI_NODEGROUP`` tile, which stores each concept's canonical AAT URI.

    Returns a dict mapping concept type label → number of tiles updated.
    """
    updated_counts = {}

    for type_label, aat_uris in sorted(uris_by_type.items()):
        list_item = type_items_by_label[type_label]
        new_type_json = json.dumps([list_item.build_tile_value()])

        if dry_run:
            updated_counts[type_label] = len(aat_uris)
            continue

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE tiles AS type_tile
                SET tiledata = jsonb_set(
                    type_tile.tiledata,
                    ARRAY[%s::text],
                    %s::jsonb
                )
                FROM tiles AS uri_tile
                WHERE uri_tile.nodegroupid = %s::uuid
                  AND uri_tile.tiledata ->> %s = ANY(%s::text[])
                  AND type_tile.nodegroupid = %s::uuid
                  AND type_tile.resourceinstanceid = uri_tile.resourceinstanceid
                """,
                [
                    str(const.CONCEPT_TYPE_NODEID),
                    new_type_json,
                    str(const.URI_NODEGROUP),
                    str(const.URI_CONTENT_NODE),
                    aat_uris,
                    str(const.CONCEPT_TYPE_NODEGROUP),
                ],
            )
            updated_counts[type_label] = cursor.rowcount

    return updated_counts
