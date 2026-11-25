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

# Subtag glosses used to build a distinct name for a tag the override table and
# Django between them only know the base language of. Without these, every
# romanisation of a language would be offered under the base language's name.
SCRIPT_SUBTAG_NAMES = {
    "latn": "Latin transliteration",
    "cyrl": "Cyrillic",
    "arab": "Arabic script",
    "hebr": "Hebrew script",
    "grek": "Greek script",
    "hang": "Hangul",
    "hani": "Han characters",
    "kana": "Katakana",
    "hira": "Hiragana",
    "hant": "Traditional",
    "hans": "Simplified",
    "deva": "Devanagari",
    "thai": "Thai script",
    "cans": "Canadian Aboriginal syllabics",
}

VARIANT_SUBTAG_NAMES = {
    "pinyin": "Pinyin",
    "wadegile": "Wade-Giles",
    "hanyu": "Hanyu",
    "notone": "no tones",
    "tongyong": "Tongyong",
    "std": "standard",
    "local": "local",
}

# A script subtag means the text is written in that script, so direction
# follows the script rather than the base language.
LTR_SCRIPT_SUBTAGS = {"latn", "cyrl", "grek", "hang", "hani", "kana", "hira"}

# Base languages Django's table does not carry, so a tag built on them would
# otherwise be named after the raw subtag.
BASE_LANGUAGE_NAMES = {
    "zh": "Chinese",
    "sa": "Sanskrit",
    "akk": "Akkadian",
    "arc": "Aramaic",
    "ber": "Berber",
    "pal": "Middle Persian",
    "pra": "Prakrit",
    "sux": "Sumerian",
    "syc": "Syriac",
    "xcl": "Classical Armenian",
    "peo": "Old Persian",
    "egy": "Egyptian",
    "grc": "Ancient Greek",
    "ang": "Old English",
    "aeb": "Tunisian Arabic",
    "acw": "Hijazi Arabic",
}


def _describe_subtags(subtags):
    """Gloss the subtags after the base language, for use in a display name."""
    described = []
    for subtag in subtags:
        lowered = subtag.lower()
        if lowered in SCRIPT_SUBTAG_NAMES:
            described.append(SCRIPT_SUBTAG_NAMES[lowered])
        elif lowered in VARIANT_SUBTAG_NAMES:
            described.append(VARIANT_SUBTAG_NAMES[lowered])
        elif lowered == "x":
            continue  # private-use marker, carries no meaning by itself
        elif len(subtag) == 2 and subtag.isalpha():
            described.append(subtag.upper())  # region, e.g. es-MX -> MX
        else:
            described.append(subtag)
    return described


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
    # Tags are matched case-insensitively: BCP 47 case is conventional, not
    # significant, and AAT writes them as "ar-Latn" where the table is keyed
    # "ar-latn".
    override = LANGUAGE_OVERRIDES.get(code.lower())
    if override:
        return {
            "name": override["name"],
            "default_direction": override["direction"],
        }

    subtags = code.split("-")
    base_tag = subtags[0].lower()
    trailing_subtags = subtags[1:]

    # "x" is the private-use singleton, not a language: "x-highgerm" has no
    # base language to name, so the tag stands on its own.
    if base_tag == "x":
        return {"name": code, "default_direction": "ltr"}

    if base_tag in BASE_LANGUAGE_NAMES:
        base_name = BASE_LANGUAGE_NAMES[base_tag]
        direction = "rtl" if base_tag in RTL_CODES else "ltr"
    else:
        try:
            base_info = get_language_info(base_tag)
            base_name = base_info["name"]
            direction = "rtl" if base_info["bidi"] else "ltr"
        except KeyError:
            base_name = base_tag
            direction = "rtl" if base_tag in RTL_CODES else "ltr"

    if not trailing_subtags:
        return {"name": base_name, "default_direction": direction}

    # Text written in another script reads in that script's direction.
    if any(subtag.lower() in LTR_SCRIPT_SUBTAGS for subtag in trailing_subtags):
        direction = "ltr"

    described = _describe_subtags(trailing_subtags)
    name = f"{base_name} ({', '.join(described)})" if described else base_name
    return {"name": name, "default_direction": direction}


def repair_colliding_language_names(dry_run=False, log=print):
    """Give a distinct name to every language code that shares one.

    Rows predating the naming fix can still share a name -- "Korean" for `ko`,
    `ko-Hang`, `ko-Hani` and `ko-Latn` alike. Only the more specific tags are
    renamed; a bare language tag keeps whatever name it has, so a name someone
    set deliberately on a base language is left alone.
    """
    all_languages = list(Language.objects.order_by("code"))
    languages_by_name = {}
    for language in all_languages:
        languages_by_name.setdefault(language.name, []).append(language)

    claimed_names = set(languages_by_name)
    languages_to_rename = []

    # Rows whose name is just the tag are a legacy of the derivation failing;
    # they read badly in a picker even though they are technically distinct.
    for language in all_languages:
        if language.name != language.code:
            continue
        candidate = resolve_language_metadata(language.code)["name"]
        if candidate == language.code or candidate in claimed_names:
            continue
        claimed_names.discard(language.name)
        claimed_names.add(candidate)
        log(f"  {language.code}: {language.name!r} -> {candidate!r}")
        language.name = candidate
        languages_to_rename.append(language)

    for name, languages in languages_by_name.items():
        if len(languages) < 2:
            continue
        # Keep the bare tag on the shared name; re-derive the variants.
        for language in sorted(languages, key=lambda item: len(item.code))[1:]:
            candidate = resolve_language_metadata(language.code)["name"]
            if candidate in claimed_names:
                candidate = f"{candidate} [{language.code}]"
            claimed_names.add(candidate)
            log(f"  {language.code}: {language.name!r} -> {candidate!r}")
            language.name = candidate
            languages_to_rename.append(language)

    if languages_to_rename and not dry_run:
        Language.objects.bulk_update(languages_to_rename, ["name"], batch_size=200)

    log(f"Renamed {len(languages_to_rename)} language(s) to remove name collisions")
    return languages_to_rename


def ensure_languages(xml_path, dry_run=False, log=print):
    """Insert a Language row for every xml:lang code the SKOS file uses.

    Codes already present are left untouched. Returns the Language objects
    created (or that would be created, when dry_run is set).
    """
    language_codes = collect_language_codes_from_xml(xml_path)
    existing_languages = {
        code: name for code, name in Language.objects.values_list("code", "name")
    }

    # Names, not codes, are what a language picker shows, so two codes sharing
    # a name are indistinguishable to the user -- and any lookup that resolves
    # by name resolves them arbitrarily. Uniqueness is enforced here rather
    # than left to the correctness of every derived name.
    claimed_names = set(existing_languages.values())

    languages_to_create = []
    for code in sorted(language_codes):
        if code in existing_languages:
            continue
        metadata = resolve_language_metadata(code)
        name = metadata["name"]
        if name in claimed_names:
            name = f"{name} [{code}]"
        claimed_names.add(name)
        languages_to_create.append(
            Language(
                code=code,
                name=name,
                default_direction=metadata["default_direction"],
                scope=Language.DATA_SCOPE,
                isdefault=False,
            )
        )

    log(
        f"{len(language_codes)} language code(s) in use; "
        f"{len(language_codes) - len(languages_to_create)} already present, "
        f"{len(languages_to_create)} to insert"
    )

    if languages_to_create and not dry_run:
        Language.objects.bulk_create(languages_to_create)
        log(f"Inserted {len(languages_to_create)} language record(s)")

    return languages_to_create
