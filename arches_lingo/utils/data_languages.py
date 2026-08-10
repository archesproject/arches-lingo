"""Reconcile the arches `languages` table with the language codes that actually
appear in resource data.

Resource data reaches an arches-lingo install through SKOS/RDF imports and other
migrations that carry arbitrary BCP-47 language tags (`nl`, `zh-latn-wadegile`,
`grc-latn-x-liturgic`, ...). The `languages` table, by contrast, is seeded only
from `settings.LANGUAGES`, so most of those codes have no row. A
language-datatype value whose code has no row cannot be resolved by
`LanguageDataType.get_display_value`, which is why the Language dropdown widget
renders a blank instead of a language name.

This module finds the codes in use and derives display names and text direction
using the langcodes library, which provides access to the IANA Language Subtag
Registry and handles BCP-47 parsing, deprecated code resolution, and display
name generation. For codes that cannot be resolved (private-use tags like
`x-local`), the raw tag is used as the name.

Derived names and directions are a starting point, not an authority: they are
what a generic standards lookup can say about a tag, and a vocabulary editor may
well want to refine them afterwards.
"""

from dataclasses import dataclass

import langcodes
from django.db import connection

from arches.app.models.models import Language

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


@dataclass(frozen=True)
class ResolvedLanguage:
    """A language code paired with the name and direction derived for it."""

    code: str
    name: str
    default_direction: str


class LanguageTagResolver:
    """Derives a display name and text direction for a BCP-47 language tag."""

    def resolve(self, code):
        return ResolvedLanguage(
            code=code,
            name=self._resolve_name(code),
            default_direction=self._resolve_direction(code),
        )

    def _resolve_name(self, code):
        try:
            lang = langcodes.Language.get(code)
            if not lang.is_valid():
                return code
            return lang.display_name()
        except (langcodes.LanguageTagError, ValueError):
            return code

    def _resolve_direction(self, code):
        try:
            lang = langcodes.Language.get(code)
        except (langcodes.LanguageTagError, ValueError):
            return Language.LEFT_TO_RIGHT

        if lang.script:
            return _direction_for_script(lang.script)

        primary_subtag = str(lang.language) if lang.language else None
        if not primary_subtag:
            return Language.LEFT_TO_RIGHT

        if primary_subtag in RIGHT_TO_LEFT_LANGUAGE_SUBTAGS:
            return Language.RIGHT_TO_LEFT

        lang_with_script = lang.assume_script() if lang.is_valid() else lang
        if lang_with_script.script:
            return _direction_for_script(lang_with_script.script)

        return Language.LEFT_TO_RIGHT


def _direction_for_script(script_subtag):
    if script_subtag.lower() in RIGHT_TO_LEFT_SCRIPT_SUBTAGS:
        return Language.RIGHT_TO_LEFT
    return Language.LEFT_TO_RIGHT


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

    resolver = LanguageTagResolver()
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
