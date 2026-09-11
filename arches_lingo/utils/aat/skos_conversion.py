"""Convert a Getty AAT bulk export into SKOS RDF/XML that Lingo can import.

Getty publishes the AAT using the Getty Vocabulary Program (GVP) ontology, which
departs from plain SKOS in ways the Lingo importer cannot read directly. This
module reconciles the two, and supports both archives Getty distributes:

  explicit.zip  Current, and the default. Data is split across many files and
                carries no inference: subjects are typed with GVP classes rather
                than skos:Concept, labels exist only as skos-xl Label nodes, and
                identifiers use dc: rather than dcterms:.
  full.zip      A single pre-inferred file. Frozen since 2025-01-13, so it is
                supported for archived copies rather than fresh downloads.

In both, scope notes hang off linked gvp:ScopeNote nodes and are inlined here,
no ConceptScheme is declared so the scheme is synthesised from skos:inScheme,
and facets carry skos:topConceptOf rather than the scheme carrying
skos:hasTopConcept.

Getty AAT is released under the Open Data Commons Attribution Licence (ODC-By);
see utils.aat.attribution_statement for the statement recorded on load.
"""

import collections
import datetime
import itertools
import os
import re
import sys
import tempfile
import urllib.request
import zipfile
from xml.sax.saxutils import escape

from arches_lingo.utils.aat.progress import (
    progress_reporting_is_useful,
    stream_lines_with_progress,
)


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

# Explicit-export (explicit.zip) support

# All four become SKOS concepts on output; update_aat_concept_types assigns the
# distinction afterwards.
GVP_CONCEPT = GVP_NS + "Concept"
GVP_GUIDE_TERM = GVP_NS + "GuideTerm"
GVP_HIERARCHY = GVP_NS + "Hierarchy"
GVP_FACET = GVP_NS + "Facet"
GVP_SUBJECT_TYPES = frozenset([GVP_CONCEPT, GVP_GUIDE_TERM, GVP_HIERARCHY, GVP_FACET])

# Two further hierarchy predicates appear only in the explicit export.
GVP_BROADER_PREFERRED = GVP_NS + "broaderPreferred"
GVP_BROADER_NON_PREFERRED = GVP_NS + "broaderNonPreferred"

# <concept> xl:prefLabel <term>, with the text on <term> xl:literalForm.
SKOSXL_NS = "http://www.w3.org/2008/05/skos-xl#"
SKOSXL_PREF_LABEL = SKOSXL_NS + "prefLabel"
SKOSXL_ALT_LABEL = SKOSXL_NS + "altLabel"
SKOSXL_LITERAL_FORM = SKOSXL_NS + "literalForm"

DC_IDENTIFIER = "http://purl.org/dc/elements/1.1/identifier"

# Retired concepts, typed gvp:ObsoleteSubject in AATOut_ObsoleteSubjects.nt.
GVP_OBSOLETE_SUBJECT = GVP_NS + "ObsoleteSubject"

# Streamed in this order. The archive's other members are either irrelevant to
# the SKOS output or handled by attribution_extraction.
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
            # The importer only creates a URI tile when the identifier is a
            # URL, taking the identifier itself from the last path segment. The
            # export's bare number would therefore yield no URI tile, which the
            # attribution loader and concept typing both need.
            predicate_uri = DCTERMS_IDENTIFIER
            raw_object = f'"{subject_uri}"'

        # Duplicates arise where the full export asserts both skos:broader and
        # a GVP equivalent for the same pair; the write step deduplicates.
        if predicate_uri in (
            GVP_BROADER_GENERIC,
            GVP_BROADER_PARTITIV,
            GVP_BROADER_INSTANTI,
            GVP_BROADER_PREFERRED,
            GVP_BROADER_NON_PREFERRED,
        ):
            predicate_uri = SKOS_BROADER

        subject_data[subject_uri][predicate_uri].append(raw_object)

    return (
        concepts,
        explicit_schemes,
        scope_note_literals,
        subject_data,
        xl_label_literals,
    )


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


def find_hierarchy_cycles(concepts, subject_data):
    """Return the skos:broader edges that close a cycle, as (child, parent).

    Getty's data contains a small number of concept pairs that each declare the
    other a parent. Those assertions are in the source vocabulary and are legal
    SKOS, so they are loaded as they stand; this only reports them, so a load
    that introduces a new one is visible in the log.
    """
    parents_by_child = {}
    for concept_uri in sorted(concepts):
        parent_uris = []
        for raw_object in subject_data.get(concept_uri, {}).get(SKOS_BROADER, []):
            parent_uri = _parse_uri_object(raw_object)
            if parent_uri and parent_uri in concepts and parent_uri not in parent_uris:
                parent_uris.append(parent_uri)
        if parent_uris:
            parents_by_child[concept_uri] = parent_uris

    cycle_edges = []
    UNVISITED, IN_PROGRESS, DONE = 0, 1, 2
    visit_state = collections.defaultdict(int)

    # Iterative depth-first search; an edge reaching a node already on the
    # current path closes a cycle. The edge is recorded and not followed, so
    # the walk terminates without the hierarchy having to be acyclic.
    for start_uri in parents_by_child:
        if visit_state[start_uri] != UNVISITED:
            continue
        stack = [(start_uri, iter(parents_by_child.get(start_uri, [])))]
        visit_state[start_uri] = IN_PROGRESS
        while stack:
            current_uri, parent_iterator = stack[-1]
            next_parent = next(parent_iterator, None)
            if next_parent is None:
                visit_state[current_uri] = DONE
                stack.pop()
                continue
            if visit_state[next_parent] == IN_PROGRESS:
                cycle_edges.append((current_uri, next_parent))
            elif visit_state[next_parent] == UNVISITED:
                visit_state[next_parent] = IN_PROGRESS
                stack.append((next_parent, iter(parents_by_child.get(next_parent, []))))
    return cycle_edges


def report_hierarchy_cycles(concepts, subject_data, log=print):
    """Log the cyclic broader edges the export contains, keeping them all."""
    cycle_edges = find_hierarchy_cycles(concepts, subject_data)
    if cycle_edges:
        log(
            f"{len(cycle_edges)} broader edge(s) close a cycle and are loaded "
            f"as the source asserts them:"
        )
        for child_uri, parent_uri in cycle_edges:
            log(f"  {child_uri} -> {parent_uri}")
    return cycle_edges


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


def validate_output(concepts, schemes, subject_data, log=print):
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


def read_archive_extraction_date(archive_path):
    """Return the date Getty built the export, from its newest data member.

    Getty stamps each member as it is written, so the newest of the members we
    actually read is the build date. Members are considered selectively because
    the archive also carries files Getty forwards unchanged from earlier builds
    (their Wikidata alignment is years older), which would otherwise drag the
    answer backwards.
    """
    considered_filenames = set(EXPLICIT_EXPORT_FILES) | {OBSOLETE_SUBJECTS_FILE}
    with zipfile.ZipFile(archive_path, "r") as archive:
        member_dates = [
            datetime.date(*member.date_time[:3])
            for member in archive.infolist()
            if member.filename in considered_filenames
        ]
        if not member_dates:
            member_dates = [
                datetime.date(*member.date_time[:3]) for member in archive.infolist()
            ]
    return max(member_dates) if member_dates else None


class AATConversionError(Exception):
    """Raised when a Getty archive cannot be converted."""


def download_archive(destination_path, url=GETTY_AAT_EXPLICIT_ZIP_URL, log=print):
    """Download a Getty AAT archive to destination_path."""
    log(f"Downloading {url} ...")
    try:
        download_with_progress(url, destination_path)
    except Exception as download_error:
        if os.path.exists(destination_path):
            os.unlink(destination_path)
        raise AATConversionError(
            f"Download failed: {download_error}"
        ) from download_error
    return destination_path


def _select_source_filenames(archive, log):
    """Return the NTriples members to stream, supporting both export layouts."""
    available_filenames = archive.namelist()

    full_export_filename = next(
        (
            name
            for name in available_filenames
            if "Full" in name and name.endswith(".nt")
        ),
        None,
    )
    if full_export_filename:
        return [full_export_filename]

    source_filenames = [
        name for name in EXPLICIT_EXPORT_FILES if name in available_filenames
    ]
    missing_filenames = [
        name for name in EXPLICIT_EXPORT_FILES if name not in available_filenames
    ]
    if missing_filenames:
        log(
            f"Warning: expected files absent from archive: {', '.join(missing_filenames)}"
        )
    if not source_filenames:
        raise AATConversionError(
            f"Cannot identify NTriples data files in archive. "
            f"Available: {available_filenames}"
        )
    return source_filenames


def convert_archive_to_skos(
    archive_path,
    output_path,
    scheme_identifier_uri=DEFAULT_SCHEME_IDENTIFIER_URI,
    scheme_pref_label=DEFAULT_SCHEME_PREF_LABEL,
    show_progress=None,
    log=print,
):
    """Convert a Getty AAT archive into SKOS RDF/XML written to output_path.

    Handles both Getty export layouts: the single pre-inferred "full" export and
    the multi-file "explicit" export, which carries no inference and expresses
    labels as skos-xl nodes. Concepts Getty has retired are excluded.

    Returns the number of concepts written.
    """
    if not os.path.exists(archive_path):
        raise AATConversionError(f"Archive not found: {archive_path}")

    with zipfile.ZipFile(archive_path, "r") as archive:
        source_filenames = _select_source_filenames(archive, log)
        total_uncompressed_bytes = sum(
            archive.getinfo(name).file_size for name in source_filenames
        )
        log(
            f"Reading {len(source_filenames)} file(s), "
            f"{total_uncompressed_bytes / 1_048_576:,.0f} MB uncompressed"
        )

        obsolete_uris = set()
        if OBSOLETE_SUBJECTS_FILE in archive.namelist():
            with archive.open(OBSOLETE_SUBJECTS_FILE) as obsolete_stream:
                obsolete_uris = collect_obsolete_subjects(obsolete_stream)
            log(f"{len(obsolete_uris):,} retired subjects will be excluded")

        if show_progress is None:
            show_progress = progress_reporting_is_useful()

        open_streams = [archive.open(name) for name in source_filenames]
        try:
            (
                concepts,
                explicit_schemes,
                scope_note_literals,
                subject_data,
                xl_label_literals,
            ) = collect_aat_data(
                stream_lines_with_progress(
                    open_streams,
                    total_uncompressed_bytes,
                    title="Reading concepts, labels and hierarchy",
                    show_progress=show_progress,
                )
            )
        finally:
            for stream in open_streams:
                stream.close()

    if obsolete_uris:
        retired_concepts = concepts & obsolete_uris
        concepts -= obsolete_uris
        for retired_uri in retired_concepts:
            subject_data.pop(retired_uri, None)
        log(f"Excluded {len(retired_concepts):,} retired concepts")

    if xl_label_literals:
        inlined_label_count = resolve_xl_labels(subject_data, xl_label_literals)
        log(f"Inlined {inlined_label_count:,} skos-xl label literals")

    schemes = derive_schemes(explicit_schemes, concepts, subject_data)
    resolve_scope_notes(subject_data, scope_note_literals)
    promote_all_broader_targets_transitively(concepts, subject_data)
    report_hierarchy_cycles(concepts, subject_data, log=log)
    synthesize_top_concepts(concepts, schemes, subject_data)
    validate_output(concepts, schemes, subject_data, log=log)

    concepts_written = write_skos_xml(
        output_path,
        concepts,
        schemes,
        subject_data,
        scheme_identifier_uri,
        scheme_pref_label,
    )
    log(f"Wrote {concepts_written:,} concepts to {output_path}")
    return concepts_written
