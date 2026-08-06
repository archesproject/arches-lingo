"""Reconcile the arches `languages` table with the language codes that actually
appear in resource data.

Resource data reaches an arches-lingo install through SKOS/RDF imports and other
migrations that carry arbitrary BCP-47 language tags (`nl`, `zh-latn-wadegile`,
`grc-latn-x-liturgic`, ...). The `languages` table, by contrast, is seeded only
from `settings.LANGUAGES`, so most of those codes have no row. A
language-datatype value whose code has no row cannot be resolved by
`LanguageDataType.get_display_value`, which is why the Language dropdown widget
renders a blank instead of a language name.

This module finds the codes in use and derives the best available display name
and text direction for each, in this order of preference:

1. Django's `LANG_INFO`, which is where arches itself gets language names when
   it seeds the table, so codes shared with `settings.LANGUAGES` keep the exact
   names arches would have given them.
2. The IANA Language Subtag Registry, the authoritative BCP-47 source. Each
   subtag of a compound tag is described separately and then recombined, which
   is what turns `zh-latn-wadegile` into
   "Chinese (Latin, Wade-Giles romanization)".
3. The raw tag, for private-use codes (`x-local`, `qqq-002`) that have no
   registered meaning to look up. The tag itself is the only honest label, and
   it at least stays traceable back to the data.

Derived names and directions are a starting point, not an authority: they are
what a generic standards lookup can say about a tag, and a vocabulary editor may
well want to refine them afterwards.
"""

import urllib.request
from collections import defaultdict
from dataclasses import dataclass

from django.conf.locale import LANG_INFO
from django.db import connection

from arches.app.models.models import Language

IANA_SUBTAG_REGISTRY_URL = (
    "https://www.iana.org/assignments/language-subtag-registry/"
    "language-subtag-registry"
)

# Language codes reach tile data two ways: as the value of a language-datatype
# node, and as the keys of an i18n string. Both need a `languages` row -- the
# first so the Language widget can resolve a name to display, the second so the
# string widget offers the language as a translation to edit. Pass NULL for
# `graph_ids` to scan every graph, or a uuid[] to scope the scan.
LANGUAGE_CODES_IN_RESOURCE_DATA_SQL = """
    SELECT DISTINCT code
    FROM (
        SELECT jsonb_extract_path_text(tiles.tiledata, nodes.nodeid::text) AS code
        FROM tiles
        JOIN nodes ON nodes.nodegroupid = tiles.nodegroupid
        WHERE nodes.datatype = 'language'
          AND (
            %(graph_ids)s::uuid[] IS NULL
            OR tiles.resourceinstanceid IN (
                SELECT resourceinstanceid FROM resource_instances
                WHERE graphid = ANY(%(graph_ids)s::uuid[])
            )
          )
        UNION
        SELECT jsonb_object_keys(
            jsonb_extract_path(tiles.tiledata, nodes.nodeid::text)
        ) AS code
        FROM tiles
        JOIN nodes ON nodes.nodegroupid = tiles.nodegroupid
        WHERE nodes.datatype = 'string'
          AND jsonb_typeof(
            jsonb_extract_path(tiles.tiledata, nodes.nodeid::text)
          ) = 'object'
          AND (
            %(graph_ids)s::uuid[] IS NULL
            OR tiles.resourceinstanceid IN (
                SELECT resourceinstanceid FROM resource_instances
                WHERE graphid = ANY(%(graph_ids)s::uuid[])
            )
          )
    ) collected_codes
    WHERE code IS NOT NULL AND code <> ''
"""

# Scripts written right to left, by IANA script subtag. Used both for an
# explicit script subtag in a tag and for the script a language is normally
# written in.
# fmt: off
RIGHT_TO_LEFT_SCRIPT_SUBTAGS = frozenset(
    {
        "adlm", "arab", "aran", "armi", "avst", "chrs", "cprt", "elym", "hatr",
        "hebr", "hung", "khar", "lydi", "mand", "mani", "merc", "mero", "narb",
        "nbat", "nkoo", "orkh", "palm", "phli", "phlp", "phnx", "prti", "samr",
        "sarb", "sogd", "sogo", "syrc", "syre", "syrj", "syrn", "thaa", "yezi"
    }
)
# fmt: on

# Right-to-left languages the registry cannot settle on its own, because it
# records no `Suppress-Script` for them and they belong to no macrolanguage that
# has one. Mostly historic Semitic languages plus a few Arabic-script languages
# whose registry entry stays script-neutral.
# fmt: off
RIGHT_TO_LEFT_LANGUAGE_SUBTAGS = frozenset(
    {
        "arc", "ckb", "hbo", "jpa", "ks", "ku", "pal", "phn", "sam", "sd",
        "syc", "syr", "tmr", "xpr"
    }
)
# fmt: on

# ISO 639-2 codes are absent from the IANA registry whenever the language also
# has a two-letter ISO 639-1 code, since the shorter code is the canonical
# subtag. Data that spells a language `ind` or `gla` therefore needs to be
# resolved through `id` and `gd` to find a name at all. Derived from the Library
# of Congress ISO 639-2 code list; both the bibliographic and terminologic
# spellings are included.
# fmt: off
ISO_639_2_TO_ISO_639_1 = {
    "aar": "aa", "abk": "ab", "afr": "af", "aka": "ak", "alb": "sq",
    "amh": "am", "ara": "ar", "arg": "an", "arm": "hy", "asm": "as",
    "ava": "av", "ave": "ae", "aym": "ay", "aze": "az", "bak": "ba",
    "bam": "bm", "baq": "eu", "bel": "be", "ben": "bn", "bis": "bi",
    "bod": "bo", "bos": "bs", "bre": "br", "bul": "bg", "bur": "my",
    "cat": "ca", "ces": "cs", "cha": "ch", "che": "ce", "chi": "zh",
    "chu": "cu", "chv": "cv", "cor": "kw", "cos": "co", "cre": "cr",
    "cym": "cy", "cze": "cs", "dan": "da", "deu": "de", "div": "dv",
    "dut": "nl", "dzo": "dz", "ell": "el", "eng": "en", "epo": "eo",
    "est": "et", "eus": "eu", "ewe": "ee", "fao": "fo", "fas": "fa",
    "fij": "fj", "fin": "fi", "fra": "fr", "fre": "fr", "fry": "fy",
    "ful": "ff", "geo": "ka", "ger": "de", "gla": "gd", "gle": "ga",
    "glg": "gl", "glv": "gv", "gre": "el", "grn": "gn", "guj": "gu",
    "hat": "ht", "hau": "ha", "heb": "he", "her": "hz", "hin": "hi",
    "hmo": "ho", "hrv": "hr", "hun": "hu", "hye": "hy", "ibo": "ig",
    "ice": "is", "ido": "io", "iii": "ii", "iku": "iu", "ile": "ie",
    "ina": "ia", "ind": "id", "ipk": "ik", "isl": "is", "ita": "it",
    "jav": "jv", "jpn": "ja", "kal": "kl", "kan": "kn", "kas": "ks",
    "kat": "ka", "kau": "kr", "kaz": "kk", "khm": "km", "kik": "ki",
    "kin": "rw", "kir": "ky", "kom": "kv", "kon": "kg", "kor": "ko",
    "kua": "kj", "kur": "ku", "lao": "lo", "lat": "la", "lav": "lv",
    "lim": "li", "lin": "ln", "lit": "lt", "ltz": "lb", "lub": "lu",
    "lug": "lg", "mac": "mk", "mah": "mh", "mal": "ml", "mao": "mi",
    "mar": "mr", "may": "ms", "mkd": "mk", "mlg": "mg", "mlt": "mt",
    "mon": "mn", "mri": "mi", "msa": "ms", "mya": "my", "nau": "na",
    "nav": "nv", "nbl": "nr", "nde": "nd", "ndo": "ng", "nep": "ne",
    "nld": "nl", "nno": "nn", "nob": "nb", "nor": "no", "nya": "ny",
    "oci": "oc", "oji": "oj", "ori": "or", "orm": "om", "oss": "os",
    "pan": "pa", "per": "fa", "pli": "pi", "pol": "pl", "por": "pt",
    "pus": "ps", "que": "qu", "roh": "rm", "ron": "ro", "rum": "ro",
    "run": "rn", "rus": "ru", "sag": "sg", "san": "sa", "sin": "si",
    "slk": "sk", "slo": "sk", "slv": "sl", "sme": "se", "smo": "sm",
    "sna": "sn", "snd": "sd", "som": "so", "sot": "st", "spa": "es",
    "sqi": "sq", "srd": "sc", "srp": "sr", "ssw": "ss", "sun": "su",
    "swa": "sw", "swe": "sv", "tah": "ty", "tam": "ta", "tat": "tt",
    "tel": "te", "tgk": "tg", "tgl": "tl", "tha": "th", "tib": "bo",
    "tir": "ti", "ton": "to", "tsn": "tn", "tso": "ts", "tuk": "tk",
    "tur": "tr", "twi": "tw", "uig": "ug", "ukr": "uk", "urd": "ur",
    "uzb": "uz", "ven": "ve", "vie": "vi", "vol": "vo", "wel": "cy",
    "wln": "wa", "wol": "wo", "xho": "xh", "yid": "yi", "yor": "yo",
    "zha": "za", "zho": "zh", "zul": "zu",
}
# fmt: on


@dataclass(frozen=True)
class RegisteredSubtag:
    """One subtag's entry in the IANA Language Subtag Registry."""

    description: str
    preferred_value: str | None = None
    macrolanguage: str | None = None
    suppress_script: str | None = None


@dataclass(frozen=True)
class ResolvedLanguage:
    """A language code paired with the name and direction derived for it."""

    code: str
    name: str
    default_direction: str


class SubtagRegistry:
    """The IANA Language Subtag Registry, parsed for lookup by subtag type.

    The registry is a record-jar file: `Field: value` lines, records separated
    by `%%`, and values continued on following indented lines. A subtag can
    carry several `Description` fields when it has alternate names; only the
    first is kept, because it is the one intended as the primary name.
    """

    def __init__(self, registry_text):
        self._subtags = {}
        # Blocks of unassigned subtags reserved for private use are registered
        # as a range ("qaa..qtz") rather than one record each.
        self._private_use_ranges = []

        for record in self._parse_records(registry_text):
            subtag_values = record.get("Subtag") or record.get("Tag")
            if not subtag_values or "Type" not in record:
                continue
            subtag_type = record["Type"][0].lower()
            subtag_value = subtag_values[0].lower()

            if ".." in subtag_value:
                range_start, _, range_end = subtag_value.partition("..")
                self._private_use_ranges.append((subtag_type, range_start, range_end))
                continue

            self._subtags[subtag_type, subtag_value] = RegisteredSubtag(
                description=record.get("Description", [subtag_value])[0],
                preferred_value=self._first(record, "Preferred-Value"),
                macrolanguage=self._first(record, "Macrolanguage"),
                suppress_script=self._first(record, "Suppress-Script"),
            )

    @staticmethod
    def _first(record, field_name):
        values = record.get(field_name)
        return values[0] if values else None

    @staticmethod
    def _parse_records(registry_text):
        for block in registry_text.split("\n%%"):
            values_by_field = defaultdict(list)
            current_field = None
            for line in block.splitlines():
                if line[:1] in (" ", "\t") and current_field:
                    values_by_field[current_field][-1] += " " + line.strip()
                    continue
                current_field, separator, value = line.partition(":")
                if not separator:
                    current_field = None
                    continue
                values_by_field[current_field].append(value.strip())
            if values_by_field:
                yield values_by_field

    def find(self, subtag_type, subtag_value):
        return self._subtags.get((subtag_type, subtag_value.lower()))

    def is_private_use(self, subtag_type, subtag_value):
        subtag_value = subtag_value.lower()
        return any(
            registered_type == subtag_type
            and len(subtag_value) == len(range_start)
            and range_start <= subtag_value <= range_end
            for registered_type, range_start, range_end in self._private_use_ranges
        )


class LanguageTagResolver:
    """Derives a display name and text direction for a BCP-47 language tag."""

    def __init__(self, subtag_registry):
        self.subtag_registry = subtag_registry

    def resolve(self, code):
        return ResolvedLanguage(
            code=code,
            name=self._resolve_name(code),
            default_direction=self._resolve_direction(code),
        )

    def _resolve_name(self, code):
        name_from_django = self._django_name(code)
        if name_from_django:
            return name_from_django

        primary_subtag, qualifying_subtags, private_use_subtags = _split_tag(code)
        if primary_subtag is None:
            return f"{code} (private use)"

        qualifiers = [
            self._qualifier_name(subtag_value) for subtag_value in qualifying_subtags
        ]
        if private_use_subtags:
            qualifiers.append("private use: " + "-".join(private_use_subtags))

        name = self._primary_language_name(primary_subtag)
        if qualifiers:
            name += f" ({', '.join(qualifiers)})"
        return name

    def _language_subtag(self, primary_subtag):
        """Look up a primary language subtag, resolving the two spellings that
        do not appear in the registry under the code the data uses: an ISO 639-2
        code is looked up under its two-letter equivalent, and a deprecated
        subtag under the replacement it names. Returns the code actually
        resolved along with its registry entry, if it has one."""

        subtag_value = ISO_639_2_TO_ISO_639_1.get(primary_subtag, primary_subtag)
        subtag = self.subtag_registry.find("language", subtag_value)
        if subtag and subtag.preferred_value:
            preferred_subtag = self.subtag_registry.find(
                "language", subtag.preferred_value
            )
            if preferred_subtag:
                subtag_value, subtag = subtag.preferred_value, preferred_subtag
        return subtag_value, subtag

    def _primary_language_name(self, primary_subtag):
        subtag_value, subtag = self._language_subtag(primary_subtag)
        if subtag:
            return subtag.description
        return self._django_name(subtag_value) or primary_subtag

    def _qualifier_name(self, subtag_value):
        for subtag_type in _candidate_subtag_types(subtag_value):
            subtag = self.subtag_registry.find(subtag_type, subtag_value)
            if subtag:
                return subtag.description
        return subtag_value

    def _resolve_direction(self, code):
        primary_subtag, qualifying_subtags, _ = _split_tag(code)

        # An explicit script subtag settles direction by itself: `he-latn` is
        # romanized Hebrew, and reads left to right.
        for subtag_value in qualifying_subtags:
            if _is_script_subtag(subtag_value):
                return _direction_for_script(subtag_value)

        if primary_subtag is None:
            return Language.LEFT_TO_RIGHT

        django_info = LANG_INFO.get(code.lower()) or LANG_INFO.get(primary_subtag)
        if django_info and "bidi" in django_info:
            return (
                Language.RIGHT_TO_LEFT
                if django_info["bidi"]
                else Language.LEFT_TO_RIGHT
            )

        return self._registry_direction(primary_subtag)

    def _registry_direction(self, primary_subtag):
        subtag_value, subtag = self._language_subtag(primary_subtag)
        if subtag_value in RIGHT_TO_LEFT_LANGUAGE_SUBTAGS:
            return Language.RIGHT_TO_LEFT

        # A language with no script of its own is written in the script of its
        # macrolanguage: `acw` (Hijazi Arabic) resolves through `ar`.
        if subtag and not subtag.suppress_script and subtag.macrolanguage:
            if subtag.macrolanguage in RIGHT_TO_LEFT_LANGUAGE_SUBTAGS:
                return Language.RIGHT_TO_LEFT
            subtag = (
                self.subtag_registry.find("language", subtag.macrolanguage) or subtag
            )

        if subtag and subtag.suppress_script:
            return _direction_for_script(subtag.suppress_script)
        return Language.LEFT_TO_RIGHT

    @staticmethod
    def _django_name(code):
        django_info = LANG_INFO.get(code.lower())
        return django_info.get("name") if django_info else None


def _split_tag(code):
    """Split a language tag into its primary language subtag, its qualifying
    script/region/variant subtags, and its private-use subtags. The primary
    subtag is None for a tag that is nothing but private use, such as
    `x-local`."""

    subtags = code.lower().split("-")
    if subtags[0] == "x":
        return None, [], subtags[1:]

    qualifying_subtags = subtags[1:]
    private_use_subtags = []
    if "x" in qualifying_subtags:
        singleton_index = qualifying_subtags.index("x")
        private_use_subtags = qualifying_subtags[singleton_index + 1 :]
        qualifying_subtags = qualifying_subtags[:singleton_index]
    return subtags[0], qualifying_subtags, private_use_subtags


def _candidate_subtag_types(subtag_value):
    """The subtag types a qualifying subtag could be, given its shape. BCP-47
    makes most of these unambiguous by position and length: four letters is
    always a script, two letters or three digits always a region."""

    if _is_script_subtag(subtag_value):
        return ("script",)
    if (len(subtag_value) == 2 and subtag_value.isalpha()) or (
        len(subtag_value) == 3 and subtag_value.isdigit()
    ):
        return ("region",)
    if len(subtag_value) == 3 and subtag_value.isalpha():
        return ("extlang", "variant")
    return ("variant",)


def _is_script_subtag(subtag_value):
    return len(subtag_value) == 4 and subtag_value.isalpha()


def _direction_for_script(script_subtag):
    if script_subtag.lower() in RIGHT_TO_LEFT_SCRIPT_SUBTAGS:
        return Language.RIGHT_TO_LEFT
    return Language.LEFT_TO_RIGHT


def read_subtag_registry(local_path=None):
    """Return the text of the IANA Language Subtag Registry, read from
    `local_path` if given and downloaded from IANA otherwise."""

    if local_path:
        with open(local_path, encoding="utf-8") as registry_file:
            return registry_file.read()
    with urllib.request.urlopen(IANA_SUBTAG_REGISTRY_URL, timeout=60) as response:
        return response.read().decode("utf-8")


def get_language_codes_in_resource_data(graph_ids=None):
    """The set of language codes appearing in tile data, across every graph or
    only the given graphs."""

    with connection.cursor() as cursor:
        cursor.execute(
            LANGUAGE_CODES_IN_RESOURCE_DATA_SQL,
            {"graph_ids": None if graph_ids is None else [str(id) for id in graph_ids]},
        )
        return {row[0] for row in cursor.fetchall()}


def get_missing_language_codes(graph_ids=None):
    """The language codes used by resource data that have no `languages` row.

    Codes are compared exactly, the same way `LanguageDataType.lookup_language`
    resolves them, so a differently-cased near-match still counts as missing --
    it would not resolve for display either.
    """

    existing_codes = set(Language.objects.values_list("code", flat=True))
    return get_language_codes_in_resource_data(graph_ids) - existing_codes


def add_missing_languages(
    graph_ids=None,
    subtag_registry_path=None,
    scope=Language.DATA_SCOPE,
    dry_run=False,
):
    """Add a `languages` row for every language code used by resource data that
    does not have one yet, and return what was resolved for each, ordered by
    code.

    Rows are added with the given scope -- `data` by default, since these are
    languages the vocabulary is recorded in rather than languages the interface
    is translated into -- and never as the default language.
    """

    missing_codes = sorted(get_missing_language_codes(graph_ids))
    if not missing_codes:
        return []

    resolver = LanguageTagResolver(
        SubtagRegistry(read_subtag_registry(subtag_registry_path))
    )
    resolved_languages = [resolver.resolve(code) for code in missing_codes]

    if not dry_run:
        Language.objects.bulk_create(
            Language(
                code=resolved.code,
                name=resolved.name,
                default_direction=resolved.default_direction,
                scope=scope,
                isdefault=False,
            )
            for resolved in resolved_languages
        )

    return resolved_languages
