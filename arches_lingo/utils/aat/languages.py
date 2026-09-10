"""Ensure Language records exist for every xml:lang code in a SKOS XML file.

A label whose language has no Language row is silently filed under the default
language on import, so this runs before the AAT resources are loaded.
"""

import mmap
import re

from django.utils.translation import get_language_info

from arches.app.models.models import Language


# Language metadata overrides for codes that Django does not recognise or
# for which custom names / directions are preferable (e.g. romanised scripts
# that are always read left-to-right).

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


def ensure_languages(xml_path, dry_run=False, log=print):
    """Insert a Language row for every xml:lang code the SKOS file uses.

    Codes already present are left untouched. Returns the Language objects
    created (or that would be created, when dry_run is set).
    """
    language_codes = collect_language_codes_from_xml(xml_path)
    existing_codes = set(Language.objects.values_list("code", flat=True))

    languages_to_create = [
        Language(
            code=code,
            name=resolve_language_metadata(code)["name"],
            default_direction=resolve_language_metadata(code)["default_direction"],
            scope=Language.DATA_SCOPE,
            isdefault=False,
        )
        for code in language_codes
        if code not in existing_codes
    ]

    log(
        f"{len(language_codes)} language code(s) in use; "
        f"{len(language_codes) - len(languages_to_create)} already present, "
        f"{len(languages_to_create)} to insert"
    )

    if languages_to_create and not dry_run:
        Language.objects.bulk_create(languages_to_create)
        log(f"Inserted {len(languages_to_create)} language record(s)")

    return languages_to_create
