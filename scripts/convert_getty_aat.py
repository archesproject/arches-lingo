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
import os
import sys
import tempfile
import urllib.request
import zipfile
from xml.sax.saxutils import escape


# ---------------------------------------------------------------------------
# Download URL
# ---------------------------------------------------------------------------

GETTY_AAT_FULL_ZIP_URL = "http://aatdownloads.getty.edu/VocabData/full.zip"


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
    """
    concepts = set()
    explicit_schemes = set()
    scope_note_literals = collections.defaultdict(list)
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
            continue

        if predicate_uri == RDF_TYPE:
            obj_uri = _parse_uri_object(raw_object)
            if obj_uri == SKOS_CONCEPT:
                concepts.add(subject_uri)
            elif obj_uri == SKOS_CONCEPT_SCHEME:
                explicit_schemes.add(subject_uri)
            continue

        if predicate_uri == RDF_VALUE:
            value, lang = _parse_literal(raw_object)
            if value is not None:
                scope_note_literals[subject_uri].append((value, lang))
            continue

        # Map all GVP broader predicates to skos:broader so the output uses a
        # single standard hierarchy predicate.  Duplicates arise because the
        # full NTriples sometimes asserts both skos:broader (as an inferred
        # alias) and gvp:broaderGeneric for the same subject/object pair;
        # deduplication happens in the write step.
        if predicate_uri in (
            GVP_BROADER_GENERIC,
            GVP_BROADER_PARTITIV,
            GVP_BROADER_INSTANTI,
        ):
            predicate_uri = SKOS_BROADER

        subject_data[subject_uri][predicate_uri].append(raw_object)

    print(
        f"  {line_count:>10,} lines | {len(concepts):>6,} concepts"
        f" | {len(scope_note_literals):>6,} scope notes",
        flush=True,
    )
    return concepts, explicit_schemes, scope_note_literals, subject_data


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


def write_skos_xml(output_path, concepts, schemes, subject_data):
    """Write the collected AAT data as SKOS RDF/XML."""
    print(f"Writing output to {output_path} ...", flush=True)
    with open(output_path, "w", encoding="utf-8") as out:
        out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        out.write("<rdf:RDF\n")
        out.write('  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n')
        out.write('  xmlns:skos="http://www.w3.org/2004/02/skos/core#"\n')
        out.write('  xmlns:dcterms="http://purl.org/dc/terms/"\n')
        out.write(">\n\n")

        # --- ConceptScheme(s) ---
        for scheme_uri in sorted(schemes):
            out.write(f'  <skos:ConceptScheme rdf:about="{escape(scheme_uri)}">\n')
            scheme_data = subject_data.get(scheme_uri, {})
            for pred_uri, raw_objects in scheme_data.items():
                if pred_uri in (RDF_TYPE, SKOS_IN_SCHEME):
                    continue
                _write_predicate_elements(out, pred_uri, raw_objects)
            if SKOS_PREF_LABEL not in scheme_data:
                out.write(
                    '    <skos:prefLabel xml:lang="en">'
                    "Art &amp; Architecture Thesaurus (AAT)"
                    "</skos:prefLabel>\n"
                )
            out.write("  </skos:ConceptScheme>\n\n")

        # --- Concepts ---
        written_count = 0
        for concept_uri in sorted(concepts):
            out.write(f'  <skos:Concept rdf:about="{escape(concept_uri)}">\n')
            concept_data = subject_data.get(concept_uri, {})
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
        help="Skip downloading and use an existing 'full.zip' in the current directory.",
    )
    args = parser.parse_args()

    # Step 1: obtain the zip
    if args.skip_download:
        zip_path = "full.zip"
        if not os.path.exists(zip_path):
            print(
                "Error: --skip-download set but 'full.zip' not found.", file=sys.stderr
            )
            sys.exit(1)
        cleanup_zip = False
        print(f"Using existing {zip_path}")
    else:
        tmp_fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix="getty_aat_", dir=".")
        os.close(tmp_fd)
        cleanup_zip = True
        try:
            download_with_progress(GETTY_AAT_FULL_ZIP_URL, zip_path)
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

            subjects_filename = next(
                (n for n in available if "Full" in n and n.endswith(".nt")), None
            )
            if not subjects_filename:
                subjects_filename = next(
                    (n for n in available if "Subject" in n and n.endswith(".nt")), None
                )
            if not subjects_filename:
                print(
                    f"Error: cannot identify subjects NTriples file. "
                    f"Available: {available}",
                    file=sys.stderr,
                )
                sys.exit(1)

            fi = zf.getinfo(subjects_filename)
            print(
                f"Processing {subjects_filename}"
                f" ({fi.compress_size / 1_048_576:.0f} MB compressed,"
                f" {fi.file_size / 1_048_576:.0f} MB uncompressed)"
            )

            # Step 3: stream NTriples
            print("\nStreaming NTriples data (this will take several minutes) ...")
            with zf.open(subjects_filename) as nt_stream:
                concepts, explicit_schemes, scope_note_literals, subject_data = (
                    collect_aat_data(nt_stream)
                )

    finally:
        if cleanup_zip and os.path.exists(zip_path):
            os.unlink(zip_path)
            print("\nTemporary download file removed.")

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
    written = write_skos_xml(args.output, concepts, schemes, subject_data)

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
