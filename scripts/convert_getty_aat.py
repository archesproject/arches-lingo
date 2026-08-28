#!/usr/bin/env python3
"""
Getty AAT to SKOS Converter for arches-lingo
=============================================

Downloads the Getty Art & Architecture Thesaurus (AAT) full bulk export and
converts it to standard SKOS RDF/XML format compatible with arches-lingo's
import mechanism.

Usage
-----
Step 1 — convert (downloads ~172 MB, processes without full decompression):

    python scripts/convert_getty_aat.py [--output getty_aat_skos.xml]

    Options:
      --output / -o    Output file path (default: getty_aat_skos.xml)
      --skip-download  Reuse an existing full.zip in the current directory

Step 2 — import into arches-lingo:

    python manage.py packages \\
        -o import_lingo_resources \\
        -s /path/to/getty_aat_skos.xml \\
        -ow overwrite

Background
----------
The AAT is published using the Getty Vocabulary Program (GVP) ontology, which
differs from plain SKOS in ways arches-lingo's importer cannot handle directly:

  - Labels via skosxl:Label nodes rather than plain skos:prefLabel literals.
    The full.zip includes pre-computed skos:prefLabel inference, so those
    plain literals are already present and need no extra work.

  - Scope notes as linked gvp:ScopeNote nodes (skos:scopeNote -> node ->
    rdf:value "text"@lang). This script inlines the literal text.

  - The AATOut_Full.nt file does NOT contain a rdf:type skos:ConceptScheme
    triple for http://vocab.getty.edu/aat/ -- the scheme is synthesised from
    the skos:inScheme values found on the concepts.

  - Getty facets (top-level hierarchy nodes) use skos:topConceptOf pointing
    up to the scheme, not skos:hasTopConcept pointing down from the scheme.
    The script preserves these triples; arches-lingo's SKOS reader handles
    the inverse property.

  - Output format: SKOS RDF/XML (the format arches-lingo's importer parses).

The AAT contains ~38 000 concepts. Expect the import step to run for 30-90
minutes on a development machine.

Data licence
------------
Getty AAT is released under the Open Data Commons Attribution Licence (ODC-By).
Required attribution:
  "This dataset contains information from Art & Architecture Thesaurus (AAT)(r)
   which is made available under the ODC Attribution License."
"""

import argparse
import collections
import itertools
import os
import re
import sys
import tempfile
import urllib.request
import zipfile
from xml.sax.saxutils import escape


# ---------------------------------------------------------------------------
# Download URL
# ---------------------------------------------------------------------------

# The full export has not been updated since 2025-01-13 and appears to be
# frozen in place; the explicit export is current. Both layouts are supported.
GETTY_AAT_FULL_ZIP_URL = "http://aatdownloads.getty.edu/VocabData/full.zip"
GETTY_AAT_EXPLICIT_ZIP_URL = "http://aatdownloads.getty.edu/VocabData/explicit.zip"
DEFAULT_LOCAL_ARCHIVE = "explicit.zip"

# The synthesised AAT scheme has no identifier of its own in the export. Its
# canonical Getty subject number is used so the scheme gets the same URI and
# identifier tiles it had previously ("300000000").
DEFAULT_SCHEME_IDENTIFIER_URI = "http://vocab.getty.edu/aat/300000000"

# Label given to the synthesised scheme when the export declares none of its own.
DEFAULT_SCHEME_PREF_LABEL = "Getty Art & Architecture Thesaurus (AAT)"


# ---------------------------------------------------------------------------
# RDF / SKOS predicate URI constants
# ---------------------------------------------------------------------------

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDF_VALUE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#value"

SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
SKOS_CONCEPT = SKOS_NS + "Concept"
SKOS_CONCEPT_SCHEME = SKOS_NS + "ConceptScheme"
SKOS_IN_SCHEME = SKOS_NS + "inScheme"
SKOS_PREF_LABEL = SKOS_NS + "prefLabel"
SKOS_ALT_LABEL = SKOS_NS + "altLabel"
SKOS_BROADER = SKOS_NS + "broader"
SKOS_SCOPE_NOTE = SKOS_NS + "scopeNote"
SKOS_RELATED = SKOS_NS + "related"
SKOS_EXACT_MATCH = SKOS_NS + "exactMatch"
SKOS_HAS_TOP_CONCEPT = SKOS_NS + "hasTopConcept"
SKOS_TOP_CONCEPT_OF = SKOS_NS + "topConceptOf"

DCTERMS_IDENTIFIER = "http://purl.org/dc/terms/identifier"

# GVP ontology broader predicates -- these carry the same hierarchy meaning as
# skos:broader but are the primary predicates used in the AAT bulk NTriples.
# The full.zip includes skos:broader as an inferred alias for some triples, but
# most hierarchy is expressed only via these GVP predicates.
GVP_NS = "http://vocab.getty.edu/ontology#"
GVP_BROADER_GENERIC = GVP_NS + "broaderGeneric"
GVP_BROADER_PARTITIV = GVP_NS + "broaderPartitive"
GVP_BROADER_INSTANTI = GVP_NS + "broaderInstantial"

# GVP typed associative relation predicates encode the semantic relation type
# in the predicate URI local name (e.g. aat2285_practiced-studied_by). These
# are subproperties of skos:related and carry richer meaning than plain
# skos:related.  The prefix below is used to detect them during streaming;
# they are collected in subject_data and output using the gvp: namespace.
GVP_TYPED_RELATION_PREFIX = "http://vocab.getty.edu/ontology#aat"

# --- Explicit-export (explicit.zip) support -------------------------------
# The "full" export is a single pre-inferred AATOut_Full.nt. The explicit
# export splits the data across many files and omits all inference, so the
# shapes below have to be handled directly rather than read off inferred
# triples.

# Subjects are typed with GVP classes, not rdf:type skos:Concept. All four
# become SKOS concepts on output; the distinction is carried by the concept
# type assigned later by the update_aat_concept_types command.
GVP_CONCEPT = GVP_NS + "Concept"
GVP_GUIDE_TERM = GVP_NS + "GuideTerm"
GVP_HIERARCHY = GVP_NS + "Hierarchy"
GVP_FACET = GVP_NS + "Facet"
GVP_SUBJECT_TYPES = frozenset([GVP_CONCEPT, GVP_GUIDE_TERM, GVP_HIERARCHY, GVP_FACET])

# Two further hierarchy predicates appear only in the explicit export.
GVP_BROADER_PREFERRED = GVP_NS + "broaderPreferred"
GVP_BROADER_NON_PREFERRED = GVP_NS + "broaderNonPreferred"

# Labels are skos-xl Label nodes: <concept> xl:prefLabel <term>, and the text
# hangs off the term as <term> xl:literalForm "text"@lang.
SKOSXL_NS = "http://www.w3.org/2008/05/skos-xl#"
SKOSXL_PREF_LABEL = SKOSXL_NS + "prefLabel"
SKOSXL_ALT_LABEL = SKOSXL_NS + "altLabel"
SKOSXL_LITERAL_FORM = SKOSXL_NS + "literalForm"

# The explicit export uses dc:identifier where the full export used
# dcterms:identifier.
DC_IDENTIFIER = "http://purl.org/dc/elements/1.1/identifier"

# Retired concepts, typed gvp:ObsoleteSubject in AATOut_ObsoleteSubjects.nt.
GVP_OBSOLETE_SUBJECT = GVP_NS + "ObsoleteSubject"

# Files from the explicit export that carry data this converter needs, in the
# order they are streamed. Everything else in the archive (revision history,
# source/contributor detail, alignments, ordered collections) is either
# irrelevant here or handled by extract_getty_aat_sources.py.
EXPLICIT_EXPORT_FILES = (
    "AATOut_1Subjects.nt",
    "AATOut_2Terms.nt",
    "AATOut_ScopeNotes.nt",
    "AATOut_HierarchicalRels.nt",
    "AATOut_AssociativeRels.nt",
    "AATOut_Notations.nt",
)
OBSOLETE_SUBJECTS_FILE = "AATOut_ObsoleteSubjects.nt"

# Only predicates in this set are retained; everything else is discarded
# immediately to keep memory usage low.
COLLECT_PREDICATES = frozenset(
    [
        RDF_TYPE,
        RDF_VALUE,
        SKOS_IN_SCHEME,
        SKOS_PREF_LABEL,
        SKOS_ALT_LABEL,
        SKOS_BROADER,
        SKOS_SCOPE_NOTE,
        SKOS_RELATED,
        SKOS_EXACT_MATCH,
        SKOS_HAS_TOP_CONCEPT,
        SKOS_TOP_CONCEPT_OF,
        DCTERMS_IDENTIFIER,
        GVP_BROADER_GENERIC,
        GVP_BROADER_PARTITIV,
        GVP_BROADER_INSTANTI,
        GVP_BROADER_PREFERRED,
        GVP_BROADER_NON_PREFERRED,
        SKOSXL_PREF_LABEL,
        SKOSXL_ALT_LABEL,
        SKOSXL_LITERAL_FORM,
        DC_IDENTIFIER,
    ]
)

# Maps predicate URI -> (xml-namespace-prefix, local-name, value-kind)
PREDICATE_ELEMENT_MAP = {
    SKOS_IN_SCHEME: ("skos", "inScheme", "uri"),
    SKOS_PREF_LABEL: ("skos", "prefLabel", "literal"),
    SKOS_ALT_LABEL: ("skos", "altLabel", "literal"),
    SKOS_BROADER: ("skos", "broader", "uri"),
    SKOS_SCOPE_NOTE: ("skos", "scopeNote", "literal"),
    SKOS_RELATED: ("skos", "related", "uri"),
    SKOS_EXACT_MATCH: ("skos", "exactMatch", "uri"),
    SKOS_HAS_TOP_CONCEPT: ("skos", "hasTopConcept", "uri"),
    SKOS_TOP_CONCEPT_OF: ("skos", "topConceptOf", "uri"),
    DCTERMS_IDENTIFIER: ("dcterms", "identifier", "literal"),
}


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------


def download_with_progress(url, destination_path):
    def reporthook(block_num, block_size, total_size):
        downloaded_mb = block_num * block_size / 1_048_576
        if total_size > 0:
            pct = min(100.0, block_num * block_size * 100.0 / total_size)
            sys.stdout.write(
                f"\r  Downloading: {downloaded_mb:.1f} / "
                f"{total_size / 1_048_576:.1f} MB  ({pct:.0f}%)"
            )
        else:
            sys.stdout.write(f"\r  Downloading: {downloaded_mb:.1f} MB")
        sys.stdout.flush()

    print(f"Fetching {url}")
    urllib.request.urlretrieve(url, destination_path, reporthook)
    print()


# ---------------------------------------------------------------------------
# NTriples streaming parser (no external dependencies)
# ---------------------------------------------------------------------------


def _parse_nt_triple(line):
    """
    Parse one NTriples line.  Returns (subject_uri, predicate_uri, raw_object)
    or None for blank/comment lines and blank-node subjects.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.endswith(" ."):
        line = line[:-2]
    elif line.endswith("."):
        line = line[:-1]
    line = line.rstrip()

    if not line.startswith("<"):
        return None
    try:
        s_end = line.index(">")
    except ValueError:
        return None
    subject_uri = line[1:s_end]
    rest = line[s_end + 1 :].lstrip()

    if not rest.startswith("<"):
        return None
    try:
        p_end = rest.index(">")
    except ValueError:
        return None
    predicate_uri = rest[1:p_end]
    raw_object = rest[p_end + 1 :].lstrip()
    return subject_uri, predicate_uri, raw_object


def _decode_nt_unicode_escapes(value):
    """Decode N-Triples \\uXXXX and \\UXXXXXXXX Unicode escape sequences."""
    value = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), value)
    value = re.sub(r"\\U([0-9a-fA-F]{8})", lambda m: chr(int(m.group(1), 16)), value)
    return value


def _parse_literal(raw_object):
    """Return (value_str, lang_or_None) from a raw NTriples literal token."""
    if not raw_object.startswith('"'):
        return None, None
    pos = 1
    while pos < len(raw_object):
        ch = raw_object[pos]
        if ch == "\\":
            pos += 2
            continue
        if ch == '"':
            break
        pos += 1
    else:
        return None, None
    raw_value = raw_object[1:pos]
    value = (
        raw_value.replace('\\"', '"')
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace("\\\\", "\\")
    )
    value = _decode_nt_unicode_escapes(value)
    suffix = raw_object[pos + 1 :].lstrip()
    if suffix.startswith("@"):
        lang_tag = suffix[1:].split()[0] if suffix[1:].split() else ""
        return value, lang_tag
    return value, None


def _parse_uri_object(raw_object):
    raw = raw_object.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    return None


# ---------------------------------------------------------------------------
# Single-pass streaming collection
# ---------------------------------------------------------------------------


def collect_obsolete_subjects(nt_stream):
    """Return the set of subject URIs typed gvp:ObsoleteSubject.

    These are concepts Getty has retired. They are dropped rather than marked,
    so they simply do not appear in the converted output.
    """
    obsolete = set()
    for raw_line in nt_stream:
        line = (
            raw_line.decode("utf-8", "replace")
            if isinstance(raw_line, bytes)
            else raw_line
        )
        parsed = _parse_nt_triple(line)
        if parsed is None:
            continue
        subject_uri, predicate_uri, raw_object = parsed
        if (
            predicate_uri == RDF_TYPE
            and _parse_uri_object(raw_object) == GVP_OBSOLETE_SUBJECT
        ):
            obsolete.add(subject_uri)
    return obsolete


def collect_aat_data(nt_stream):
    """
    Stream NTriples and collect only what is needed for the SKOS output.

    Returns:
      concepts            - set of concept URI strings
      explicit_schemes    - set of ConceptScheme URIs declared via
                             rdf:type skos:ConceptScheme (may be empty for
                             the AAT full.zip which omits this triple)
      scope_note_literals - {scope_note_uri: [(value, lang), ...]}
      subject_data        - {uri: {predicate_uri: [raw_object, ...]}}
      xl_label_literals   - {term_uri: [(value, lang), ...]} for the explicit
                             export, where labels are skos-xl Label nodes
    """
    concepts = set()
    explicit_schemes = set()
    scope_note_literals = collections.defaultdict(list)
    xl_label_literals = collections.defaultdict(list)
    subject_data = collections.defaultdict(lambda: collections.defaultdict(list))

    line_count = 0
    for raw_line in nt_stream:
        if isinstance(raw_line, bytes):
            try:
                line = raw_line.decode("utf-8")
            except UnicodeDecodeError:
                line = raw_line.decode("latin-1")
        else:
            line = raw_line

        line_count += 1
        if line_count % 500_000 == 0:
            print(
                f"  {line_count:>10,} lines | {len(concepts):>6,} concepts"
                f" | {len(scope_note_literals):>6,} scope notes",
                flush=True,
            )

        parsed = _parse_nt_triple(line)
        if parsed is None:
            continue
        subject_uri, predicate_uri, raw_object = parsed

        if predicate_uri not in COLLECT_PREDICATES:
            # Collect GVP typed associative relation predicates alongside the
            # standard SKOS predicates.  Identifying triples look like:
            #   <concept> <http://vocab.getty.edu/ontology#aat2285_practiced-studied_by> <concept>
            # The full.zip also emits inferred skos:related for these; the
            # write step deduplicates so the XML carries only the typed form.
            if (
                predicate_uri.startswith(GVP_TYPED_RELATION_PREFIX)
                and len(predicate_uri) > len(GVP_TYPED_RELATION_PREFIX)
                and predicate_uri[len(GVP_TYPED_RELATION_PREFIX)].isdigit()
            ):
                target_uri = _parse_uri_object(raw_object)
                if target_uri:
                    subject_data[subject_uri][predicate_uri].append(raw_object)
            continue

        if predicate_uri == RDF_TYPE:
            obj_uri = _parse_uri_object(raw_object)
            # The full export types concepts as skos:Concept; the explicit
            # export uses the GVP subject classes instead. Guide terms,
            # hierarchy names and facets are all concepts for our purposes --
            # they carry labels and participate in the hierarchy.
            if obj_uri == SKOS_CONCEPT or obj_uri in GVP_SUBJECT_TYPES:
                concepts.add(subject_uri)
            elif obj_uri == SKOS_CONCEPT_SCHEME:
                explicit_schemes.add(subject_uri)
            continue

        if predicate_uri == RDF_VALUE:
            value, lang = _parse_literal(raw_object)
            if value is not None:
                scope_note_literals[subject_uri].append((value, lang))
            continue

        # skos-xl Label node text. Collected against the term URI so the
        # concept -> term references can be inlined afterwards.
        if predicate_uri == SKOSXL_LITERAL_FORM:
            value, lang = _parse_literal(raw_object)
            if value is not None:
                xl_label_literals[subject_uri].append((value, lang))
            continue

        # Record skos-xl label references under the plain SKOS predicate; they
        # are still term URIs at this point and get resolved to literals by
        # resolve_xl_labels().
        if predicate_uri == SKOSXL_PREF_LABEL:
            predicate_uri = SKOS_PREF_LABEL
        elif predicate_uri == SKOSXL_ALT_LABEL:
            predicate_uri = SKOS_ALT_LABEL
        elif predicate_uri == DC_IDENTIFIER:
            # The explicit export uses dc:identifier, carrying the bare number
            # ("300000201"). Normalise to dcterms:identifier AND emit the
            # concept's own URI as the value: arches-lingo's importer creates a
            # URI tile only when the identifier value is a URL, deriving the
            # identifier tile from its last path segment. Emitting the bare
            # number yields an identifier tile but no URI tile, which the
            # attribution loader and concept-type command both depend on.
            predicate_uri = DCTERMS_IDENTIFIER
            raw_object = f'"{subject_uri}"'

        # Map all GVP broader predicates to skos:broader so the output uses a
        # single standard hierarchy predicate.  Duplicates arise because the
        # full NTriples sometimes asserts both skos:broader (as an inferred
        # alias) and gvp:broaderGeneric for the same subject/object pair;
        # deduplication happens in the write step.
        if predicate_uri in (
            GVP_BROADER_GENERIC,
            GVP_BROADER_PARTITIV,
            GVP_BROADER_INSTANTI,
            GVP_BROADER_PREFERRED,
            GVP_BROADER_NON_PREFERRED,
        ):
            predicate_uri = SKOS_BROADER

        subject_data[subject_uri][predicate_uri].append(raw_object)

    print(
        f"  {line_count:>10,} lines | {len(concepts):>6,} concepts"
        f" | {len(scope_note_literals):>6,} scope notes",
        flush=True,
    )
    return (
        concepts,
        explicit_schemes,
        scope_note_literals,
        subject_data,
        xl_label_literals,
    )


# ---------------------------------------------------------------------------
# Scheme synthesis
# ---------------------------------------------------------------------------


def derive_schemes(explicit_schemes, concepts, subject_data):
    """
    Return the set of scheme URIs to write.

    AATOut_Full.nt does not include a rdf:type skos:ConceptScheme triple for
    http://vocab.getty.edu/aat/, so explicit_schemes is typically empty. In
    that case the scheme is inferred from skos:inScheme values on concepts.
    """
    if explicit_schemes:
        return set(explicit_schemes)

    print(
        "  No explicit skos:ConceptScheme declarations found.\n"
        "  Synthesising scheme(s) from skos:inScheme values on concepts ...",
        flush=True,
    )
    inferred_schemes = set()
    for concept_uri in concepts:
        for raw_object in subject_data.get(concept_uri, {}).get(SKOS_IN_SCHEME, []):
            scheme_uri = _parse_uri_object(raw_object)
            if scheme_uri:
                inferred_schemes.add(scheme_uri)

    if not inferred_schemes:
        inferred_schemes.add("http://vocab.getty.edu/aat/")
        print(
            "  No skos:inScheme values found; using fallback "
            "http://vocab.getty.edu/aat/",
            flush=True,
        )
    else:
        print(f"  Synthesised {len(inferred_schemes)} scheme(s).", flush=True)
    return inferred_schemes


# ---------------------------------------------------------------------------
# Top-concept detection
# ---------------------------------------------------------------------------


def promote_all_broader_targets_transitively(concepts, subject_data):
    """
    Iteratively promote all URIs that appear as skos:broader targets of
    concepts in the set but are not yet in the set themselves.

    The AAT hierarchy contains many intermediate nodes typed as
    skos:Collection or gvp:GuideTerm (not skos:Concept) that sit between the
    8 top-level facets and actual leaf concepts.  Without promoting them,
    those intermediate nodes are absent from the concept set and their
    children appear to have no in-set broader, causing those children to be
    incorrectly marked as top concepts.

    The promotion runs in rounds until the concept set is stable (no new
    broader targets found outside the set).  Any skos:broader references that
    point to URIs not present in subject_data at all (truly unresolvable
    targets) are removed from the child concept so they do not leave dangling
    references in the output XML — without broader, those concepts will be
    classified by synthesize_top_concepts() according to whatever higher-level
    broader they may have.

    Modifies both concepts and subject_data in place.
    Returns the total count of promoted URIs.
    """
    total_promoted = 0
    round_number = 0

    while True:
        newly_promoted = set()
        for concept_uri in list(concepts):
            for raw_object in subject_data.get(concept_uri, {}).get(SKOS_BROADER, []):
                target_uri = _parse_uri_object(raw_object)
                if (
                    target_uri
                    and target_uri not in concepts
                    and target_uri in subject_data
                ):
                    newly_promoted.add(target_uri)

        if not newly_promoted:
            break

        concepts.update(newly_promoted)
        total_promoted += len(newly_promoted)
        round_number += 1
        print(
            f"  Round {round_number}: promoted {len(newly_promoted):,} intermediate nodes"
            f" (running total: {total_promoted:,})",
            flush=True,
        )

    # Strip broader references to URIs that are neither in the concept set
    # nor in subject_data — these are truly unresolvable and would produce
    # dangling ResourceXResource records on import.
    stripped_count = 0
    for concept_uri in concepts:
        broader_list = subject_data.get(concept_uri, {}).get(SKOS_BROADER, [])
        if not broader_list:
            continue
        filtered = [
            raw
            for raw in broader_list
            if _parse_uri_object(raw) is None or _parse_uri_object(raw) in concepts
        ]
        if len(filtered) < len(broader_list):
            subject_data[concept_uri][SKOS_BROADER] = filtered
            stripped_count += len(broader_list) - len(filtered)

    if stripped_count:
        print(
            f"  Stripped {stripped_count:,} broader references to unresolvable targets.",
            flush=True,
        )

    print(
        f"  Promotion complete: {total_promoted:,} intermediate nodes added to concept set.",
        flush=True,
    )
    return total_promoted


def synthesize_top_concepts(concepts, schemes, subject_data):
    """
    Add skos:topConceptOf to concepts that have neither a skos:broader pointing
    to another concept within the imported set nor an existing topConceptOf.

    After promote_top_concept_collections() has run, the AAT facets are in the
    concept set and carry their own topConceptOf triples already.  This
    function then only marks genuinely orphaned concepts (no in-set broader
    and no existing topConceptOf) — which should be zero or very few.

    Modifies subject_data in place.  Returns the count of top concepts added.
    """
    scheme_uri = sorted(schemes)[0]
    scheme_raw_object = f"<{scheme_uri}>"

    top_concept_count = 0
    for concept_uri in concepts:
        # Skip if the concept already has topConceptOf (e.g. the promoted facets).
        if subject_data.get(concept_uri, {}).get(SKOS_TOP_CONCEPT_OF):
            continue
        broader_values = subject_data.get(concept_uri, {}).get(SKOS_BROADER, [])
        has_broader_in_concept_set = any(
            _parse_uri_object(raw) in concepts for raw in broader_values
        )
        if not has_broader_in_concept_set:
            subject_data[concept_uri][SKOS_TOP_CONCEPT_OF].append(scheme_raw_object)
            top_concept_count += 1

    if top_concept_count:
        print(
            f"  Synthesised topConceptOf for {top_concept_count:,} orphan concept(s) "
            f"with no broader within the concept set.",
            flush=True,
        )
    return top_concept_count


# ---------------------------------------------------------------------------
# Scope note resolution
# ---------------------------------------------------------------------------


def _as_nt_literal(value, lang):
    """Render a python string back into an NTriples literal, since the write
    step re-parses the raw object strings it is handed."""
    escaped_value = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped_value}"@{lang}' if lang else f'"{escaped_value}"'


def resolve_xl_labels(subject_data, xl_label_literals):
    """
    Replace skos-xl label references with inline literal objects.

    The explicit export carries no inferred plain-literal labels: a concept
    points at a skos-xl Label node (<concept> xl:prefLabel <term>) and the text
    hangs off that node as xl:literalForm. arches-lingo expects plain
    skos:prefLabel / skos:altLabel literals, so the term references are inlined
    here. Objects that are already literals (the full export) are passed
    through untouched, which keeps both export formats working.

    Modifies subject_data in place and returns the number of labels resolved.
    """
    resolved_count = 0
    for predicates in subject_data.values():
        for label_predicate in (SKOS_PREF_LABEL, SKOS_ALT_LABEL):
            if label_predicate not in predicates:
                continue
            resolved = []
            for raw_object in predicates[label_predicate]:
                term_uri = _parse_uri_object(raw_object)
                if term_uri is None:
                    resolved.append(raw_object)  # already a literal
                    continue
                for value, lang in xl_label_literals.get(term_uri, ()):
                    resolved.append(_as_nt_literal(value, lang))
                    resolved_count += 1
            predicates[label_predicate] = resolved
    return resolved_count


def resolve_scope_notes(subject_data, scope_note_literals):
    """
    Replace skos:scopeNote URI references with inline literal objects.

    GVP represents scope notes as linked gvp:ScopeNote nodes carrying text via
    rdf:value. arches-lingo expects plain skos:scopeNote literals. Modifies
    subject_data in place.
    """
    for subject_uri, predicates in subject_data.items():
        if SKOS_SCOPE_NOTE not in predicates:
            continue
        resolved = []
        for raw_object in predicates[SKOS_SCOPE_NOTE]:
            scope_note_uri = _parse_uri_object(raw_object)
            if scope_note_uri and scope_note_uri in scope_note_literals:
                for value, lang in scope_note_literals[scope_note_uri]:
                    escaped_value = (
                        value.replace("\\", "\\\\")
                        .replace('"', '\\"')
                        .replace("\n", "\\n")
                        .replace("\r", "\\r")
                    )
                    if lang:
                        resolved.append(f'"{escaped_value}"@{lang}')
                    else:
                        resolved.append(f'"{escaped_value}"')
            elif not scope_note_uri:
                resolved.append(raw_object)  # already a literal
        predicates[SKOS_SCOPE_NOTE] = resolved


# ---------------------------------------------------------------------------
# SKOS RDF/XML output
# ---------------------------------------------------------------------------


def _write_predicate_elements(out, predicate_uri, raw_objects):
    mapping = PREDICATE_ELEMENT_MAP.get(predicate_uri)
    if not mapping:
        return
    ns_prefix, local_name, _ = mapping
    element = f"{ns_prefix}:{local_name}"
    for raw_object in raw_objects:
        raw = raw_object.strip()
        if raw.startswith('"'):
            value, lang = _parse_literal(raw)
            if value is None:
                continue
            safe_value = escape(value)
            if lang:
                out.write(
                    f'    <{element} xml:lang="{escape(lang)}">'
                    f"{safe_value}</{element}>\n"
                )
            else:
                out.write(f"    <{element}>{safe_value}</{element}>\n")
        else:
            uri = _parse_uri_object(raw)
            if uri:
                out.write(f'    <{element} rdf:resource="{escape(uri)}"/>\n')


def write_skos_xml(
    output_path,
    concepts,
    schemes,
    subject_data,
    scheme_identifier_uri=None,
    scheme_pref_label=DEFAULT_SCHEME_PREF_LABEL,
):
    """Write the collected AAT data as SKOS RDF/XML."""
    print(f"Writing output to {output_path} ...", flush=True)
    with open(output_path, "w", encoding="utf-8") as out:
        out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        out.write("<rdf:RDF\n")
        out.write('  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n')
        out.write('  xmlns:skos="http://www.w3.org/2004/02/skos/core#"\n')
        out.write('  xmlns:dcterms="http://purl.org/dc/terms/"\n')
        out.write('  xmlns:gvp="http://vocab.getty.edu/ontology#"\n')
        out.write(">\n\n")

        # --- ConceptScheme(s) ---
        for scheme_uri in sorted(schemes):
            out.write(f'  <skos:ConceptScheme rdf:about="{escape(scheme_uri)}">\n')
            if scheme_identifier_uri:
                out.write(
                    f"    <dcterms:identifier>{escape(scheme_identifier_uri)}"
                    f"</dcterms:identifier>\n"
                )
            scheme_data = subject_data.get(scheme_uri, {})
            for pred_uri, raw_objects in scheme_data.items():
                if pred_uri in (RDF_TYPE, SKOS_IN_SCHEME):
                    continue
                _write_predicate_elements(out, pred_uri, raw_objects)
            if SKOS_PREF_LABEL not in scheme_data:
                out.write(
                    '    <skos:prefLabel xml:lang="en">'
                    f"{escape(scheme_pref_label)}"
                    "</skos:prefLabel>\n"
                )
            out.write("  </skos:ConceptScheme>\n\n")

        # --- Concepts ---
        written_count = 0
        gvp_ns_len = len("http://vocab.getty.edu/ontology#")
        for concept_uri in sorted(concepts):
            out.write(f'  <skos:Concept rdf:about="{escape(concept_uri)}">\n')
            concept_data = subject_data.get(concept_uri, {})

            # Build the set of target URIs covered by typed GVP relation
            # predicates for this concept, so plain skos:related triples that
            # duplicate a typed predicate can be omitted from the output.
            typed_relation_targets = set()
            for pred_uri, raw_objects in concept_data.items():
                if (
                    pred_uri.startswith(GVP_TYPED_RELATION_PREFIX)
                    and len(pred_uri) > len(GVP_TYPED_RELATION_PREFIX)
                    and pred_uri[len(GVP_TYPED_RELATION_PREFIX)].isdigit()
                ):
                    for raw in raw_objects:
                        target = _parse_uri_object(raw)
                        if target:
                            typed_relation_targets.add(target)

            for pred_uri, raw_objects in concept_data.items():
                if pred_uri == RDF_TYPE:
                    continue

                # Deduplicate skos:broader: the NTriples may contain both
                # gvp:broaderGeneric (remapped) and skos:broader for the same
                # subject/object pair.  Use seen set to emit each once.
                if pred_uri == SKOS_BROADER:
                    seen_broader_uris = set()
                    deduped = []
                    for raw in raw_objects:
                        uri = _parse_uri_object(raw)
                        if uri and uri not in seen_broader_uris:
                            seen_broader_uris.add(uri)
                            deduped.append(raw)
                    _write_predicate_elements(out, pred_uri, deduped)

                # Suppress plain skos:related for targets already expressed via
                # a typed GVP predicate to avoid duplicate relation_status tiles
                # on import.  Any remaining (untyped) related targets are kept.
                elif pred_uri == SKOS_RELATED:
                    untyped_objects = [
                        raw
                        for raw in raw_objects
                        if _parse_uri_object(raw) not in typed_relation_targets
                    ]
                    if untyped_objects:
                        _write_predicate_elements(out, pred_uri, untyped_objects)

                # Output typed GVP associative relation predicates using the
                # gvp: namespace so the arches-lingo SKOS reader can preserve
                # the semantic relation type.
                elif (
                    pred_uri.startswith(GVP_TYPED_RELATION_PREFIX)
                    and len(pred_uri) > len(GVP_TYPED_RELATION_PREFIX)
                    and pred_uri[len(GVP_TYPED_RELATION_PREFIX)].isdigit()
                ):
                    local_name = pred_uri[gvp_ns_len:]
                    for raw in raw_objects:
                        target = _parse_uri_object(raw)
                        if target:
                            out.write(
                                f'    <gvp:{escape(local_name)} rdf:resource="{escape(target)}"/>\n'
                            )

                else:
                    _write_predicate_elements(out, pred_uri, raw_objects)

            out.write("  </skos:Concept>\n\n")

            written_count += 1
            if written_count % 5_000 == 0:
                print(f"  Written {written_count:,} concepts ...", flush=True)

        out.write("</rdf:RDF>\n")

    output_size_mb = os.path.getsize(output_path) / 1_048_576
    print(
        f"Done: {written_count:,} concepts written to {output_path}"
        f" ({output_size_mb:.1f} MB)",
        flush=True,
    )
    return written_count


# ---------------------------------------------------------------------------
# Validation diagnostics
# ---------------------------------------------------------------------------


def validate_output(concepts, schemes, subject_data):
    concepts_with_pref_label = sum(
        1 for uri in concepts if SKOS_PREF_LABEL in subject_data.get(uri, {})
    )
    concepts_with_broader = sum(
        1 for uri in concepts if SKOS_BROADER in subject_data.get(uri, {})
    )
    concepts_with_scope_note = sum(
        1 for uri in concepts if subject_data.get(uri, {}).get(SKOS_SCOPE_NOTE)
    )
    concepts_with_typed_relations = sum(
        1
        for uri in concepts
        if any(
            pred.startswith(GVP_TYPED_RELATION_PREFIX)
            and len(pred) > len(GVP_TYPED_RELATION_PREFIX)
            and pred[len(GVP_TYPED_RELATION_PREFIX)].isdigit()
            for pred in subject_data.get(uri, {})
        )
    )
    top_concept_count = sum(
        1 for uri in concepts if SKOS_TOP_CONCEPT_OF in subject_data.get(uri, {})
    )
    # Of the broader relationships, count those pointing within the concept set
    concepts_with_inset_broader = sum(
        1
        for uri in concepts
        if any(
            _parse_uri_object(raw) in concepts
            for raw in subject_data.get(uri, {}).get(SKOS_BROADER, [])
        )
    )
    print("\nConversion summary:")
    print(f"  Schemes:                             {len(schemes):>7,}")
    print(f"  Total concepts:                      {len(concepts):>7,}")
    print(f"  Concepts with prefLabel:             {concepts_with_pref_label:>7,}")
    print(f"  Concepts with broader (any):         {concepts_with_broader:>7,}")
    print(f"  Concepts with broader (in-set):      {concepts_with_inset_broader:>7,}")
    print(f"  Concepts with scope note:            {concepts_with_scope_note:>7,}")
    print(f"  Concepts with typed relations:       {concepts_with_typed_relations:>7,}")
    print(f"  Top concepts (topConceptOf):         {top_concept_count:>7,}")
    if not schemes:
        print("\n  ERROR: No scheme produced -- the output XML will not import.")
    if top_concept_count == 0:
        print(
            "\n  WARNING: No skos:topConceptOf triples found. "
            "The hierarchy view will not work after import."
        )
    if concepts_with_pref_label == 0:
        print(
            "\n  WARNING: No skos:prefLabel literals found. Concepts will "
            "import without labels."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Download the Getty AAT full export and convert to SKOS RDF/XML "
            "for arches-lingo import."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        "-o",
        default="getty_aat_skos.xml",
        help="Output file path (default: getty_aat_skos.xml)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help=(
            "Skip downloading and use an existing archive on disk "
            f"(default: {DEFAULT_LOCAL_ARCHIVE}; override with --archive)."
        ),
    )
    parser.add_argument(
        "--archive",
        default=DEFAULT_LOCAL_ARCHIVE,
        help=(
            "Path to an existing Getty archive to read with --skip-download "
            f"(default: {DEFAULT_LOCAL_ARCHIVE})."
        ),
    )
    parser.add_argument(
        "--scheme-pref-label",
        default=DEFAULT_SCHEME_PREF_LABEL,
        help=(
            "English prefLabel for the synthesised scheme "
            f"(default: {DEFAULT_SCHEME_PREF_LABEL!r})."
        ),
    )
    parser.add_argument(
        "--scheme-identifier",
        default=DEFAULT_SCHEME_IDENTIFIER_URI,
        help=(
            "URL-valued dcterms:identifier to give the synthesised scheme "
            f"(default: {DEFAULT_SCHEME_IDENTIFIER_URI}). Pass an empty string "
            "to omit it."
        ),
    )
    parser.add_argument(
        "--url",
        default=GETTY_AAT_EXPLICIT_ZIP_URL,
        help=(
            "Archive URL to download. Defaults to the explicit export, which "
            "Getty still updates; the full export has been frozen since "
            "January 2025."
        ),
    )
    args = parser.parse_args()

    # Step 1: obtain the zip
    if args.skip_download:
        zip_path = args.archive
        if not os.path.exists(zip_path):
            print(
                f"Error: --skip-download set but {zip_path!r} not found.",
                file=sys.stderr,
            )
            sys.exit(1)
        cleanup_zip = False
        print(f"Using existing {zip_path}")
    else:
        tmp_fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix="getty_aat_", dir=".")
        os.close(tmp_fd)
        cleanup_zip = True
        try:
            download_with_progress(args.url, zip_path)
        except Exception as exc:
            print(f"\nDownload failed: {exc}", file=sys.stderr)
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            sys.exit(1)

    try:
        # Step 2: identify the subjects NTriples file
        print(f"\nOpening {zip_path} ...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            available = zf.namelist()
            print(f"Files in archive: {', '.join(available)}")

            full_export_filename = next(
                (n for n in available if "Full" in n and n.endswith(".nt")), None
            )
            if full_export_filename:
                # "full" export: one pre-inferred file carries everything.
                source_filenames = [full_export_filename]
            else:
                # "explicit" export: data is split across files and carries no
                # inference, so every file holding data we need is streamed.
                source_filenames = [n for n in EXPLICIT_EXPORT_FILES if n in available]
                missing = [n for n in EXPLICIT_EXPORT_FILES if n not in available]
                if missing:
                    print(
                        f"Warning: expected files absent from archive: "
                        f"{', '.join(missing)}",
                        file=sys.stderr,
                    )

            if not source_filenames:
                print(
                    f"Error: cannot identify NTriples data files. "
                    f"Available: {available}",
                    file=sys.stderr,
                )
                sys.exit(1)

            total_uncompressed = sum(zf.getinfo(n).file_size for n in source_filenames)
            print(
                f"Processing {len(source_filenames)} file(s), "
                f"{total_uncompressed / 1_048_576:,.0f} MB uncompressed:"
            )
            for n in source_filenames:
                print(f"  {n} ({zf.getinfo(n).file_size / 1_048_576:,.0f} MB)")

            # Retired concepts are listed in their own file and must not be
            # emitted. Collected first so they can be dropped up front.
            obsolete_uris = set()
            if OBSOLETE_SUBJECTS_FILE in available:
                with zf.open(OBSOLETE_SUBJECTS_FILE) as obsolete_stream:
                    obsolete_uris = collect_obsolete_subjects(obsolete_stream)
                print(
                    f"\n{len(obsolete_uris):,} obsolete (retired) subjects will be "
                    f"excluded."
                )

            # Step 3: stream NTriples across every source file as one sequence.
            print("\nStreaming NTriples data (this will take several minutes) ...")
            open_streams = [zf.open(n) for n in source_filenames]
            try:
                (
                    concepts,
                    explicit_schemes,
                    scope_note_literals,
                    subject_data,
                    xl_label_literals,
                ) = collect_aat_data(itertools.chain(*open_streams))
            finally:
                for stream in open_streams:
                    stream.close()

    finally:
        if cleanup_zip and os.path.exists(zip_path):
            os.unlink(zip_path)
            print("\nTemporary download file removed.")

    # Drop anything Getty has retired before it can reach the output.
    if obsolete_uris:
        removed = concepts & obsolete_uris
        concepts -= obsolete_uris
        for uri in removed:
            subject_data.pop(uri, None)
        print(f"Excluded {len(removed):,} retired concepts.")

    # Step 3b: inline skos-xl label text (no-op for the full export)
    if xl_label_literals:
        print(f"Resolving {len(xl_label_literals):,} skos-xl label nodes ...")
        resolved = resolve_xl_labels(subject_data, xl_label_literals)
        print(f"  inlined {resolved:,} label literals")

    # Step 4: determine scheme(s)
    print()
    schemes = derive_schemes(explicit_schemes, concepts, subject_data)

    # Step 5: inline scope note literal text
    print(f"Resolving {len(scope_note_literals):,} scope note nodes ...")
    resolve_scope_notes(subject_data, scope_note_literals)

    # Step 6: promote all intermediate hierarchy nodes (guide terms, facets,
    #          collections) so every skos:broader reference resolves within
    #          the concept set, then synthesise topConceptOf only for the true
    #          top nodes (the 8 AAT facets).
    print("Promoting intermediate hierarchy nodes transitively ...")
    promote_all_broader_targets_transitively(concepts, subject_data)
    print("Synthesising top concepts for any remaining orphans ...")
    synthesize_top_concepts(concepts, schemes, subject_data)

    validate_output(concepts, schemes, subject_data)

    # Step 7: write SKOS RDF/XML
    print()
    written = write_skos_xml(
        args.output,
        concepts,
        schemes,
        subject_data,
        args.scheme_identifier,
        args.scheme_pref_label,
    )

    output_abs = os.path.abspath(args.output)
    print(
        f"\n{'=' * 64}\n"
        f"Conversion complete!\n"
        f"Output file : {output_abs}\n"
        f"Concepts    : {written:,}\n"
        f"\nTo import into arches-lingo, run from the arches-lingo directory:\n"
        f"\n  python manage.py packages \\\n"
        f"      -o import_lingo_resources \\\n"
        f"      -s {output_abs} \\\n"
        f"      -ow overwrite\n"
        f"\nNOTE: Importing {written:,} concepts may take 30-90 minutes.\n"
        f"      The management command runs synchronously (no Celery needed).\n"
        f"\nRequired attribution for the Getty AAT data:\n"
        f'  "This dataset contains information from Art & Architecture\n'
        f"   Thesaurus (AAT)(r) which is made available under the ODC\n"
        f'   Attribution License."\n'
    )


if __name__ == "__main__":
    main()
