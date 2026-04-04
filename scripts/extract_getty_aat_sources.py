#!/usr/bin/env python3
"""
Getty AAT Source & Contributor Extractor
=========================================

Streams the Getty AAT NTriples bulk export and extracts source/contributor
attribution data that is not captured by the SKOS conversion script
(convert_getty_aat.py).

For each skos-xl:Label and gvp:ScopeNote in the AAT, this script collects:
  - dct:source references (the bibliographic sources that support the data)
  - dct:contributor references (the organizations that contributed the data)
  - gvp:sourcePreferred / gvp:sourceNonPreferred
  - gvp:contributorPreferred / gvp:contributorNonPreferred

It also collects contributor metadata (foaf:name, foaf:nick) and source
metadata (dcterms:title, bibo:shortTitle) so that the downstream loader can
create Lingo resources for sources and contributors.

Usage
-----
    python scripts/extract_getty_aat_sources.py [--output aat_sources.json]
    python scripts/extract_getty_aat_sources.py --skip-download

The output is a JSON file with this structure:

    {
      "sources": {
        "<source-uri>": {
          "title": "...",
          "short_title": "..."
        }
      },
      "contributors": {
        "<contributor-uri>": {
          "name": "...",
          "nick": "..."
        }
      },
      "labels": {
        "<concept-uri>": [
          {
            "literal_form": "...",
            "language": "en",
            "label_type": "prefLabel|altLabel",
            "sources": ["<source-uri>", ...],
            "contributors": ["<contributor-uri>", ...]
          }
        ]
      },
      "notes": {
        "<concept-uri>": [
          {
            "value": "...",
            "language": "en",
            "sources": ["<source-uri>", ...],
            "contributors": ["<contributor-uri>", ...]
          }
        ]
      }
    }

This file is consumed by the load_aat_sources ETL module to create
textual_work, person, and group resources and link them to existing
concept/scheme tiles.
"""

import argparse
import collections
import json
import os
import re
import sys
import tempfile
import urllib.request
import zipfile


# ---------------------------------------------------------------------------
# Download URL (same as convert_getty_aat.py)
# ---------------------------------------------------------------------------

GETTY_AAT_FULL_ZIP_URL = "http://aatdownloads.getty.edu/VocabData/full.zip"


# ---------------------------------------------------------------------------
# RDF / SKOS / GVP predicate URI constants
# ---------------------------------------------------------------------------

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDF_VALUE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#value"

SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
SKOS_CONCEPT = SKOS_NS + "Concept"
SKOS_PREF_LABEL = SKOS_NS + "prefLabel"
SKOS_ALT_LABEL = SKOS_NS + "altLabel"
SKOS_SCOPE_NOTE = SKOS_NS + "scopeNote"

SKOSXL_NS = "http://www.w3.org/2008/05/skos-xl#"
SKOSXL_LABEL = SKOSXL_NS + "Label"
SKOSXL_PREF_LABEL = SKOSXL_NS + "prefLabel"
SKOSXL_ALT_LABEL = SKOSXL_NS + "altLabel"
SKOSXL_LITERAL_FORM = SKOSXL_NS + "literalForm"

GVP_NS = "http://vocab.getty.edu/ontology#"
GVP_SCOPE_NOTE = GVP_NS + "ScopeNote"
GVP_SOURCE_PREFERRED = GVP_NS + "sourcePreferred"
GVP_SOURCE_NON_PREFERRED = GVP_NS + "sourceNonPreferred"
GVP_CONTRIBUTOR_PREFERRED = GVP_NS + "contributorPreferred"
GVP_CONTRIBUTOR_NON_PREFERRED = GVP_NS + "contributorNonPreferred"

DCT_NS = "http://purl.org/dc/terms/"
DCT_SOURCE = DCT_NS + "source"
DCT_CONTRIBUTOR = DCT_NS + "contributor"
DCT_TITLE = DCT_NS + "title"
DCT_LANGUAGE = DCT_NS + "language"

FOAF_NS = "http://xmlns.com/foaf/0.1/"
FOAF_AGENT = FOAF_NS + "Agent"
FOAF_NAME = FOAF_NS + "name"
FOAF_NICK = FOAF_NS + "nick"

BIBO_NS = "http://purl.org/ontology/bibo/"
BIBO_DOCUMENT = BIBO_NS + "Document"
BIBO_SHORT_TITLE = BIBO_NS + "shortTitle"

# All predicates we need to collect
COLLECT_PREDICATES = frozenset(
    [
        RDF_TYPE,
        RDF_VALUE,
        # Label structure
        SKOSXL_PREF_LABEL,
        SKOSXL_ALT_LABEL,
        SKOSXL_LITERAL_FORM,
        # Note structure
        SKOS_SCOPE_NOTE,
        # Source/contributor on labels and notes
        DCT_SOURCE,
        DCT_CONTRIBUTOR,
        GVP_SOURCE_PREFERRED,
        GVP_SOURCE_NON_PREFERRED,
        GVP_CONTRIBUTOR_PREFERRED,
        GVP_CONTRIBUTOR_NON_PREFERRED,
        # Contributor metadata
        FOAF_NAME,
        FOAF_NICK,
        # Source metadata
        DCT_TITLE,
        BIBO_SHORT_TITLE,
        # Language on scope notes
        DCT_LANGUAGE,
    ]
)

SOURCE_PREDICATES = frozenset(
    [
        DCT_SOURCE,
        GVP_SOURCE_PREFERRED,
        GVP_SOURCE_NON_PREFERRED,
    ]
)

CONTRIBUTOR_PREDICATES = frozenset(
    [
        DCT_CONTRIBUTOR,
        GVP_CONTRIBUTOR_PREFERRED,
        GVP_CONTRIBUTOR_NON_PREFERRED,
    ]
)

AAT_CONTRIB_PREFIX = "http://vocab.getty.edu/aat/contrib/"
AAT_SOURCE_PREFIX = "http://vocab.getty.edu/aat/source/"


# ---------------------------------------------------------------------------
# Download helper (same as convert_getty_aat.py)
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
# NTriples parser (same as convert_getty_aat.py)
# ---------------------------------------------------------------------------


def _parse_nt_triple(line):
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
    value = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), value)
    value = re.sub(r"\\U([0-9a-fA-F]{8})", lambda m: chr(int(m.group(1), 16)), value)
    return value


def _parse_literal(raw_object):
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
# Streaming collection
# ---------------------------------------------------------------------------


def collect_source_data(nt_stream):
    """
    Stream NTriples and collect source/contributor attribution data.

    We collect:
    1. Which URIs are skos:Concepts (to filter scope notes and labels to concepts)
    2. skos-xl:Label nodes: literal form, language, and their source/contributor links
    3. gvp:ScopeNote nodes: rdf:value text and their source/contributor links
    4. concept -> label mappings (skosxl:prefLabel, skosxl:altLabel)
    5. concept -> scope note mappings (skos:scopeNote)
    6. Contributor metadata (foaf:name, foaf:nick)
    7. Source metadata (dcterms:title, bibo:shortTitle)
    """
    concepts = set()

    # Label node data: {label_uri: {predicate: [raw_object, ...]}}
    label_data = collections.defaultdict(lambda: collections.defaultdict(list))
    label_types = {}  # {label_uri: rdf:type}

    # Scope note data: {note_uri: {predicate: [raw_object, ...]}}
    note_data = collections.defaultdict(lambda: collections.defaultdict(list))

    # Concept -> label/note links
    concept_labels = collections.defaultdict(
        list
    )  # {concept_uri: [(label_uri, pref/alt)]}
    concept_notes = collections.defaultdict(list)  # {concept_uri: [note_uri]}

    # Contributor/source metadata
    contributor_names = {}  # {uri: name}
    contributor_nicks = {}  # {uri: nick}
    source_titles = {}  # {uri: title}
    source_short_titles = {}  # {uri: short_title}

    # Track types
    label_uris = set()
    note_uris = set()

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
                f" | {len(label_uris):>6,} labels"
                f" | {len(note_uris):>6,} notes",
                flush=True,
            )

        parsed = _parse_nt_triple(line)
        if parsed is None:
            continue
        subject_uri, predicate_uri, raw_object = parsed

        if predicate_uri not in COLLECT_PREDICATES:
            continue

        # --- rdf:type ---
        if predicate_uri == RDF_TYPE:
            obj_uri = _parse_uri_object(raw_object)
            if obj_uri == SKOS_CONCEPT:
                concepts.add(subject_uri)
            elif obj_uri == SKOSXL_LABEL:
                label_uris.add(subject_uri)
            elif obj_uri == GVP_SCOPE_NOTE:
                note_uris.add(subject_uri)
            continue

        # --- Concept -> label links ---
        if predicate_uri == SKOSXL_PREF_LABEL:
            label_uri = _parse_uri_object(raw_object)
            if label_uri:
                concept_labels[subject_uri].append((label_uri, "prefLabel"))
            continue

        if predicate_uri == SKOSXL_ALT_LABEL:
            label_uri = _parse_uri_object(raw_object)
            if label_uri:
                concept_labels[subject_uri].append((label_uri, "altLabel"))
            continue

        # --- Concept -> note links ---
        if predicate_uri == SKOS_SCOPE_NOTE:
            note_uri = _parse_uri_object(raw_object)
            if note_uri:
                concept_notes[subject_uri].append(note_uri)
            continue

        # --- Label literal form ---
        if predicate_uri == SKOSXL_LITERAL_FORM:
            label_data[subject_uri]["literal_form"].append(raw_object)
            continue

        # --- Note rdf:value ---
        if predicate_uri == RDF_VALUE:
            note_data[subject_uri]["value"].append(raw_object)
            continue

        # --- Source/contributor on labels and notes ---
        if predicate_uri in SOURCE_PREDICATES:
            obj_uri = _parse_uri_object(raw_object)
            if obj_uri:
                label_data[subject_uri]["sources"].append(obj_uri)
                note_data[subject_uri]["sources"].append(obj_uri)
            continue

        if predicate_uri in CONTRIBUTOR_PREDICATES:
            obj_uri = _parse_uri_object(raw_object)
            if obj_uri:
                label_data[subject_uri]["contributors"].append(obj_uri)
                note_data[subject_uri]["contributors"].append(obj_uri)
            continue

        # --- Contributor metadata ---
        if predicate_uri == FOAF_NAME:
            value, _ = _parse_literal(raw_object)
            if value:
                contributor_names[subject_uri] = value
            continue

        if predicate_uri == FOAF_NICK:
            value, _ = _parse_literal(raw_object)
            if value:
                contributor_nicks[subject_uri] = value
            continue

        # --- Source metadata ---
        if predicate_uri == DCT_TITLE:
            value, _ = _parse_literal(raw_object)
            if value:
                source_titles[subject_uri] = value
            continue

        if predicate_uri == BIBO_SHORT_TITLE:
            value, _ = _parse_literal(raw_object)
            if value:
                source_short_titles[subject_uri] = value
            continue

        # --- Language on notes ---
        if predicate_uri == DCT_LANGUAGE:
            note_data[subject_uri]["language"].append(raw_object)
            continue

    print(
        f"  {line_count:>10,} lines | {len(concepts):>6,} concepts"
        f" | {len(label_uris):>6,} labels"
        f" | {len(note_uris):>6,} notes",
        flush=True,
    )

    return {
        "concepts": concepts,
        "label_uris": label_uris,
        "note_uris": note_uris,
        "label_data": label_data,
        "note_data": note_data,
        "concept_labels": concept_labels,
        "concept_notes": concept_notes,
        "contributor_names": contributor_names,
        "contributor_nicks": contributor_nicks,
        "source_titles": source_titles,
        "source_short_titles": source_short_titles,
    }


# ---------------------------------------------------------------------------
# Build output
# ---------------------------------------------------------------------------


def _normalize_source_uri(uri):
    """Strip page-specific suffixes like -subject-300011021 or -term-12345."""
    # Source URIs can be like:
    #   http://vocab.getty.edu/aat/source/2000051089
    #   http://vocab.getty.edu/aat/source/2000051089-subject-300011021
    #   http://vocab.getty.edu/aat/source/2000051089-term-12345
    # We want the base source URI.
    if not uri.startswith(AAT_SOURCE_PREFIX):
        return uri
    local = uri[len(AAT_SOURCE_PREFIX) :]
    # Strip -subject-NNN or -term-NNN suffixes
    base = re.sub(r"-(subject|term)-\d+$", "", local)
    return AAT_SOURCE_PREFIX + base


def build_output(collected):
    concepts = collected["concepts"]
    label_uris = collected["label_uris"]
    note_uris = collected["note_uris"]
    label_data = collected["label_data"]
    note_data = collected["note_data"]
    concept_labels = collected["concept_labels"]
    concept_notes = collected["concept_notes"]

    # Collect all referenced sources and contributors
    all_sources = set()
    all_contributors = set()

    # Build labels output: {concept_uri: [label_info, ...]}
    # Iterate over all URIs that have label links, not just skos:Concept-typed ones.
    # Facets, guide terms, and hierarchy names in AAT use rdf:type gvp:Facet /
    # skos:Collection rather than skos:Concept, so they would be missed if we
    # only iterated over `concepts`.
    labels_out = collections.defaultdict(list)
    for concept_uri in concept_labels:
        for label_uri, label_type in concept_labels[concept_uri]:
            if label_uri not in label_uris:
                continue
            ldata = label_data.get(label_uri, {})

            # Get literal form
            literal_form = None
            language = None
            for raw in ldata.get("literal_form", []):
                value, lang = _parse_literal(raw)
                if value:
                    literal_form = value
                    language = lang
                    break

            if not literal_form:
                continue

            # Get sources (deduplicate and normalize)
            sources = sorted(
                set(_normalize_source_uri(uri) for uri in ldata.get("sources", []))
            )
            # Get contributors (deduplicate)
            contributors = sorted(set(ldata.get("contributors", [])))

            if not sources and not contributors:
                continue

            all_sources.update(sources)
            all_contributors.update(contributors)

            labels_out[concept_uri].append(
                {
                    "literal_form": literal_form,
                    "language": language,
                    "label_type": label_type,
                    "sources": sources,
                    "contributors": contributors,
                }
            )

    # Build notes output: {concept_uri: [note_info, ...]}
    # Same reasoning as labels: iterate concept_notes directly rather than
    # filtering through the skos:Concept-only `concepts` set.
    notes_out = collections.defaultdict(list)
    for concept_uri in concept_notes:
        for note_uri in concept_notes[concept_uri]:
            if note_uri not in note_uris:
                continue
            ndata = note_data.get(note_uri, {})

            # Get note text
            note_value = None
            note_language = None
            for raw in ndata.get("value", []):
                value, lang = _parse_literal(raw)
                if value:
                    note_value = value
                    note_language = lang
                    break

            if not note_value:
                continue

            # Get sources (deduplicate and normalize)
            sources = sorted(
                set(_normalize_source_uri(uri) for uri in ndata.get("sources", []))
            )
            # Get contributors (deduplicate)
            contributors = sorted(set(ndata.get("contributors", [])))

            if not sources and not contributors:
                continue

            all_sources.update(sources)
            all_contributors.update(contributors)

            notes_out[concept_uri].append(
                {
                    "value": note_value,
                    "language": note_language,
                    "sources": sources,
                    "contributors": contributors,
                }
            )

    # Build source metadata
    sources_meta = {}
    for uri in sorted(all_sources):
        sources_meta[uri] = {
            "title": collected["source_titles"].get(uri, ""),
            "short_title": collected["source_short_titles"].get(uri, ""),
        }

    # Build contributor metadata
    contributors_meta = {}
    for uri in sorted(all_contributors):
        contributors_meta[uri] = {
            "name": collected["contributor_names"].get(uri, ""),
            "nick": collected["contributor_nicks"].get(uri, ""),
        }

    return {
        "sources": sources_meta,
        "contributors": contributors_meta,
        "labels": dict(labels_out),
        "notes": dict(notes_out),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract source/contributor attribution data from the Getty AAT "
            "NTriples export."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        default="aat_sources.json",
        help="Output JSON file path (default: aat_sources.json)",
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
                "Error: --skip-download set but 'full.zip' not found.",
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
            download_with_progress(GETTY_AAT_FULL_ZIP_URL, zip_path)
        except Exception as exc:
            print(f"\nDownload failed: {exc}", file=sys.stderr)
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            sys.exit(1)

    try:
        print(f"\nOpening {zip_path} ...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            available = zf.namelist()
            print(f"Files in archive: {', '.join(available)}")

            subjects_filename = next(
                (n for n in available if "Full" in n and n.endswith(".nt")), None
            )
            if not subjects_filename:
                subjects_filename = next(
                    (n for n in available if "Subject" in n and n.endswith(".nt")),
                    None,
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

            # Step 2: stream NTriples
            print("\nStreaming NTriples data (this will take several minutes) ...")
            with zf.open(subjects_filename) as nt_stream:
                collected = collect_source_data(nt_stream)
    finally:
        if cleanup_zip and os.path.exists(zip_path):
            os.unlink(zip_path)
            print("\nTemporary download file removed.")

    # Step 3: build output
    print("\nBuilding output ...")
    output = build_output(collected)

    print(f"\nSummary:")
    print(f"  Unique sources:      {len(output['sources']):>7,}")
    print(f"  Unique contributors: {len(output['contributors']):>7,}")
    print(f"  Concepts with label attribution: " f"{len(output['labels']):>7,}")
    print(f"  Concepts with note attribution:  " f"{len(output['notes']):>7,}")
    total_labels = sum(len(v) for v in output["labels"].values())
    total_notes = sum(len(v) for v in output["notes"].values())
    print(f"  Total label attributions:        {total_labels:>7,}")
    print(f"  Total note attributions:         {total_notes:>7,}")

    # Check for sources/contributors with missing metadata
    missing_source_titles = sum(1 for s in output["sources"].values() if not s["title"])
    missing_contrib_names = sum(
        1 for c in output["contributors"].values() if not c["name"]
    )
    if missing_source_titles:
        print(
            f"\n  WARNING: {missing_source_titles} source(s) have no title. "
            f"These may need to be fetched from the Getty SPARQL endpoint."
        )
    if missing_contrib_names:
        print(
            f"\n  WARNING: {missing_contrib_names} contributor(s) have no name. "
            f"These may need to be fetched from the Getty SPARQL endpoint."
        )

    # Step 4: write output
    print(f"\nWriting {args.output} ...")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    output_size_mb = os.path.getsize(args.output) / 1_048_576
    print(f"Done: {args.output} ({output_size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
