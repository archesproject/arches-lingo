#!/usr/bin/env python3
"""
Ensure Language records exist for all xml:lang codes in getty_aat_skos.xml
=========================================================================

Scans the converted SKOS XML file for every xml:lang attribute value, then
inserts a Language row for any code not already present in the database.
Existing records are left untouched.

Usage
-----
    python scripts/ensure_aat_languages.py [--xml getty_aat_skos.xml]

    Options:
      --xml / -x    Path to the SKOS XML file (default: getty_aat_skos.xml)
      --dry-run     Print what would be inserted without writing to the database
"""

import argparse
import mmap
import os
import re
import sys

# ---------------------------------------------------------------------------
# Django setup -- must happen before any model imports
# ---------------------------------------------------------------------------

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "arches_lingo.settings")

import django  # noqa: E402

django.setup()

from django.utils.translation import get_language_info  # noqa: E402
from arches.app.models.models import Language  # noqa: E402


# ---------------------------------------------------------------------------
# Language metadata overrides for codes that Django does not recognise or
# for which custom names / directions are preferable (e.g. romanised scripts
# that are always read left-to-right).
# ---------------------------------------------------------------------------

LANGUAGE_OVERRIDES = {
    # Extended Chinese script / romanisation tags
    "zh-hant": {"name": "Chinese (Traditional)", "direction": "ltr"},
    "zh-hans": {"name": "Chinese (Simplified)", "direction": "ltr"},
    "zh-latn": {"name": "Chinese (Latin transliteration)", "direction": "ltr"},
    "zh-latn-wadegile": {"name": "Chinese (Wade-Giles)", "direction": "ltr"},
    "zh-latn-pinyin": {"name": "Chinese (Pinyin)", "direction": "ltr"},
    "zh-latn-pinyin-x-hanyu": {"name": "Chinese (Hanyu Pinyin)", "direction": "ltr"},
    "zh-latn-pinyin-x-notone": {
        "name": "Chinese (Pinyin, no tones)",
        "direction": "ltr",
    },
    # English regional variants
    "en-us": {"name": "English (US)", "direction": "ltr"},
    "en-gb": {"name": "English (UK)", "direction": "ltr"},
    # Romanised Arabic / Hebrew (Latin script → always ltr)
    "ar-latn": {"name": "Arabic (Latin transliteration)", "direction": "ltr"},
    "he-latn": {"name": "Hebrew (Latin transliteration)", "direction": "ltr"},
    # Romanised Japanese / Greek
    "ja-latn": {"name": "Japanese (Latin transliteration)", "direction": "ltr"},
    "el-latn": {"name": "Greek (Latin transliteration)", "direction": "ltr"},
    # Sanskrit in Latin script
    "sa-latn": {"name": "Sanskrit (Latin transliteration)", "direction": "ltr"},
    # Classical / indigenous languages Django may not know
    "la": {"name": "Latin", "direction": "ltr"},
    "nci": {"name": "Classical Nahuatl", "direction": "ltr"},
    "nhe": {"name": "Eastern Huasteca Nahuatl", "direction": "ltr"},
    "nah": {"name": "Nahuatl", "direction": "ltr"},
    "mi": {"name": "Māori", "direction": "ltr"},
    "sr": {"name": "Serbian", "direction": "ltr"},
    "nb": {"name": "Norwegian Bokmål", "direction": "ltr"},
    "nn": {"name": "Norwegian Nynorsk", "direction": "ltr"},
    # Pseudo / internal codes used by Getty — inserted with descriptive names
    # so they do not block import, but flagged clearly
    "und": {"name": "Undetermined language", "direction": "ltr"},
    "qqq-002": {"name": "Internal Getty code (qqq-002)", "direction": "ltr"},
    "x-local": {"name": "Local language (unspecified)", "direction": "ltr"},
}

# Language codes that are right-to-left when written in their native script.
# This supplements Django's bidi detection for codes it may not recognise.
RTL_CODES = {"ar", "he", "fa", "ur", "yi", "ps", "sd"}


def collect_language_codes_from_xml(xml_path):
    """
    Return a sorted list of unique BCP 47 language tag strings found in
    xml:lang attributes inside the given file.  Uses memory-mapped I/O so
    the multi-hundred-MB file is not loaded into RAM all at once.
    """
    pattern = re.compile(rb'xml:lang="([^"]+)"')
    language_codes = set()
    with open(xml_path, "rb") as file_handle:
        with mmap.mmap(file_handle.fileno(), 0, access=mmap.ACCESS_READ) as mapped_file:
            for match in pattern.finditer(mapped_file):
                language_codes.add(match.group(1).decode("utf-8"))
    return sorted(language_codes)


def resolve_language_metadata(code):
    """
    Return a dict with keys  name, default_direction  for the given BCP 47
    language tag.  Checks LANGUAGE_OVERRIDES first, then Django's
    get_language_info(), then falls back to sensible defaults.
    """
    if code in LANGUAGE_OVERRIDES:
        override = LANGUAGE_OVERRIDES[code]
        return {
            "name": override["name"],
            "default_direction": override["direction"],
        }

    try:
        info = get_language_info(code)
        return {
            "name": info["name"],
            "default_direction": "rtl" if info["bidi"] else "ltr",
        }
    except KeyError:
        pass

    # Derive direction from the base subtag (e.g. "ar" in "ar-latn" would
    # normally be RTL but that is handled above; this catches remaining cases).
    base_tag = code.split("-")[0].lower()
    direction = "rtl" if base_tag in RTL_CODES else "ltr"
    return {
        "name": code,  # use the code itself when name is unknown
        "default_direction": direction,
    }


def ensure_languages(xml_path, dry_run=False):
    language_codes = collect_language_codes_from_xml(xml_path)
    print(f"Found {len(language_codes)} unique language code(s) in {xml_path}.\n")

    existing_codes = set(Language.objects.values_list("code", flat=True))

    languages_to_create = []
    already_present = []

    for code in language_codes:
        if code in existing_codes:
            already_present.append(code)
            continue
        metadata = resolve_language_metadata(code)
        languages_to_create.append(
            Language(
                code=code,
                name=metadata["name"],
                default_direction=metadata["default_direction"],
                scope=Language.DATA_SCOPE,
                isdefault=False,
            )
        )

    print(f"  Already in database : {len(already_present)}")
    print(f"  Will be inserted    : {len(languages_to_create)}\n")

    if languages_to_create:
        print("Languages to insert:")
        for language in languages_to_create:
            print(
                f"  {language.code:<35}  {language.name:<45}  "
                f"{language.default_direction}"
            )

    if not dry_run and languages_to_create:
        Language.objects.bulk_create(languages_to_create)
        print(f"\nInserted {len(languages_to_create)} language record(s).")
    elif dry_run and languages_to_create:
        print("\n(Dry run — no records written.)")
    else:
        print("Nothing to insert.")

    return languages_to_create


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Insert Language records for all xml:lang codes found in a Getty "
            "AAT SKOS XML file, skipping codes already in the database."
        )
    )
    parser.add_argument(
        "--xml",
        "-x",
        default="getty_aat_skos.xml",
        help="Path to the SKOS XML file (default: getty_aat_skos.xml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be inserted without writing to the database.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.xml):
        print(f"Error: '{args.xml}' not found.", file=sys.stderr)
        sys.exit(1)

    ensure_languages(args.xml, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
