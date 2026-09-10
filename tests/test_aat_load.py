"""Tests for the Getty AAT load.

Covers the conversion logic that turns the Getty export into SKOS, since that is
where the export's shape is interpreted, plus the scoping rule that decides what
a reload removes. The import itself is arches machinery already covered by
tests/test_import_export.py, except for the direct tile-load path that replaces
it under --bypass-staging, which tests/test_aat_direct_load.py covers.
"""

import datetime
import io
import json
import os
import tempfile
import xml.etree.ElementTree as ElementTree
import zipfile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from arches_lingo.utils.aat.attribution_extraction import (
    extract_attribution_from_archive,
)
from arches_lingo.etl_modules.migrate_to_lingo import LingoResourceImporter
from arches_lingo.utils.aat.languages import resolve_language_metadata
from arches_lingo.utils.aat.progress import (
    iterate_with_progress,
    stream_lines_with_progress,
)
from arches_lingo.utils.aat.attribution_statement import (
    build_aat_attribution,
    format_extraction_date,
)
from arches_lingo.utils.aat.skos_conversion import (
    AATConversionError,
    GVP_NS,
    break_hierarchy_cycles,
    convert_archive_to_skos,
    find_hierarchy_cycles,
    validate_output,
    read_archive_extraction_date,
    SKOS_BROADER,
)


# A miniature stand-in for the Getty "explicit" export: small enough to assert
# on exactly, but carrying the shapes that matter -- GVP subject typing, skos-xl
# label nodes, direct hierarchy predicates, a scope note node, a retired
# subject, and source/contributor links.
SAMPLE_ARCHIVE_MEMBERS = {
    "AATOut_1Subjects.nt": """\
<http://vocab.getty.edu/aat/300000001> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vocab.getty.edu/ontology#Concept> .
<http://vocab.getty.edu/aat/300000001> <http://www.w3.org/2004/02/skos/core#inScheme> <http://vocab.getty.edu/aat/> .
<http://vocab.getty.edu/aat/300000001> <http://purl.org/dc/elements/1.1/identifier> "300000001" .
<http://vocab.getty.edu/aat/300000002> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vocab.getty.edu/ontology#Facet> .
<http://vocab.getty.edu/aat/300000002> <http://www.w3.org/2004/02/skos/core#inScheme> <http://vocab.getty.edu/aat/> .
<http://vocab.getty.edu/aat/300000002> <http://purl.org/dc/elements/1.1/identifier> "300000002" .
<http://vocab.getty.edu/aat/300000009> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vocab.getty.edu/ontology#Concept> .
<http://vocab.getty.edu/aat/300000009> <http://www.w3.org/2004/02/skos/core#inScheme> <http://vocab.getty.edu/aat/> .
<http://vocab.getty.edu/aat/300000009> <http://purl.org/dc/elements/1.1/identifier> "300000009" .
""",
    "AATOut_2Terms.nt": """\
<http://vocab.getty.edu/aat/300000001> <http://www.w3.org/2008/05/skos-xl#prefLabel> <http://vocab.getty.edu/aat/term/1000000001-en> .
<http://vocab.getty.edu/aat/300000001> <http://www.w3.org/2008/05/skos-xl#altLabel> <http://vocab.getty.edu/aat/term/1000000001-alt> .
<http://vocab.getty.edu/aat/300000002> <http://www.w3.org/2008/05/skos-xl#prefLabel> <http://vocab.getty.edu/aat/term/1000000002-en> .
<http://vocab.getty.edu/aat/300000009> <http://www.w3.org/2008/05/skos-xl#prefLabel> <http://vocab.getty.edu/aat/term/1000000009-en> .
<http://vocab.getty.edu/aat/term/1000000001-en> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2008/05/skos-xl#Label> .
<http://vocab.getty.edu/aat/term/1000000001-alt> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2008/05/skos-xl#Label> .
<http://vocab.getty.edu/aat/term/1000000002-en> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2008/05/skos-xl#Label> .
<http://vocab.getty.edu/aat/term/1000000009-en> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2008/05/skos-xl#Label> .
<http://vocab.getty.edu/aat/term/1000000001-en> <http://www.w3.org/2008/05/skos-xl#literalForm> "trumpets"@en .
<http://vocab.getty.edu/aat/term/1000000001-alt> <http://www.w3.org/2008/05/skos-xl#literalForm> "trompettes"@fr .
<http://vocab.getty.edu/aat/term/1000000002-en> <http://www.w3.org/2008/05/skos-xl#literalForm> "Objects Facet"@en .
<http://vocab.getty.edu/aat/term/1000000009-en> <http://www.w3.org/2008/05/skos-xl#literalForm> "retired thing"@en .
""",
    "AATOut_ScopeNotes.nt": """\
<http://vocab.getty.edu/aat/300000001> <http://www.w3.org/2004/02/skos/core#scopeNote> <http://vocab.getty.edu/aat/scopeNote/11> .
<http://vocab.getty.edu/aat/scopeNote/11> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vocab.getty.edu/ontology#ScopeNote> .
<http://vocab.getty.edu/aat/scopeNote/11> <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> "Brass instruments."@en .
""",
    "AATOut_HierarchicalRels.nt": """\
<http://vocab.getty.edu/aat/300000001> <http://vocab.getty.edu/ontology#broaderPreferred> <http://vocab.getty.edu/aat/300000002> .
""",
    "AATOut_AssociativeRels.nt": """\
<http://vocab.getty.edu/aat/300000001> <http://vocab.getty.edu/ontology#aat2000_related_to> <http://vocab.getty.edu/aat/300000002> .
""",
    "AATOut_Notations.nt": "",
    "AATOut_ObsoleteSubjects.nt": """\
<http://vocab.getty.edu/aat/300000009> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vocab.getty.edu/ontology#ObsoleteSubject> .
""",
    "AATOut_Sources.nt": """\
<http://vocab.getty.edu/aat/source/2000000001> <http://purl.org/dc/terms/title> "A Source (1999)" .
""",
    "AATOut_Contribs.nt": """\
<http://vocab.getty.edu/aat/contrib/1000000001> <http://xmlns.com/foaf/0.1/name> "Example Contributor" .
""",
    "AATOut_SourceRels.nt": """\
<http://vocab.getty.edu/aat/term/1000000001-en> <http://purl.org/dc/terms/source> <http://vocab.getty.edu/aat/source/2000000001> .
""",
    "AATOut_ContribRels.nt": """\
<http://vocab.getty.edu/aat/term/1000000001-en> <http://purl.org/dc/terms/contributor> <http://vocab.getty.edu/aat/contrib/1000000001> .
""",
}


def write_sample_archive(archive_path):
    with zipfile.ZipFile(archive_path, "w") as archive:
        for member_name, member_content in SAMPLE_ARCHIVE_MEMBERS.items():
            archive.writestr(member_name, member_content)
    return archive_path


SKOS_NAMESPACE = "http://www.w3.org/2004/02/skos/core#"
DCTERMS_NAMESPACE = "http://purl.org/dc/terms/"


def concept_elements_by_aat_number(skos_path):
    root = ElementTree.parse(skos_path).getroot()
    concepts = {}
    for concept_element in root.findall(f"{{{SKOS_NAMESPACE}}}Concept"):
        about = concept_element.get(
            "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"
        )
        concepts[about.rsplit("/", 1)[-1]] = concept_element
    return concepts


def element_texts(concept_element, namespace, local_name):
    return [
        child.text for child in concept_element.findall(f"{{{namespace}}}{local_name}")
    ]


class GettyExportConversionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.archive_path = write_sample_archive(
            os.path.join(cls.temporary_directory.name, "explicit.zip")
        )
        cls.skos_path = os.path.join(cls.temporary_directory.name, "aat.xml")
        cls.concept_count = convert_archive_to_skos(
            cls.archive_path, cls.skos_path, log=lambda message: None
        )
        cls.concepts = concept_elements_by_aat_number(cls.skos_path)

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()
        super().tearDownClass()

    def test_gvp_typed_subjects_become_concepts(self):
        """Subjects are typed gvp:Concept/gvp:Facet, never rdf:type skos:Concept."""
        self.assertEqual(self.concept_count, 2)
        self.assertEqual(set(self.concepts), {"300000001", "300000002"})

    def test_retired_subjects_are_excluded(self):
        self.assertNotIn("300000009", self.concepts)

    def test_skos_xl_labels_are_inlined_with_language(self):
        """Labels exist only as skos-xl nodes and must be resolved to literals."""
        trumpets = self.concepts["300000001"]
        self.assertEqual(
            element_texts(trumpets, SKOS_NAMESPACE, "prefLabel"), ["trumpets"]
        )
        self.assertEqual(
            element_texts(trumpets, SKOS_NAMESPACE, "altLabel"), ["trompettes"]
        )
        pref_label_element = trumpets.find(f"{{{SKOS_NAMESPACE}}}prefLabel")
        self.assertEqual(
            pref_label_element.get("{http://www.w3.org/XML/1998/namespace}lang"), "en"
        )

    def test_identifier_is_emitted_as_a_uri(self):
        """A bare dc:identifier yields no URI tile on import, so emit the URI."""
        self.assertEqual(
            element_texts(self.concepts["300000001"], DCTERMS_NAMESPACE, "identifier"),
            ["http://vocab.getty.edu/aat/300000001"],
        )

    def test_direct_gvp_hierarchy_becomes_skos_broader(self):
        broader_element = self.concepts["300000001"].find(
            f"{{{SKOS_NAMESPACE}}}broader"
        )
        self.assertEqual(
            broader_element.get(
                "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
            ),
            "http://vocab.getty.edu/aat/300000002",
        )

    def test_scope_note_text_is_inlined(self):
        self.assertEqual(
            element_texts(self.concepts["300000001"], SKOS_NAMESPACE, "scopeNote"),
            ["Brass instruments."],
        )

    def test_scheme_receives_label_and_identifier(self):
        root = ElementTree.parse(self.skos_path).getroot()
        scheme_element = root.find(f"{{{SKOS_NAMESPACE}}}ConceptScheme")
        self.assertEqual(
            element_texts(scheme_element, SKOS_NAMESPACE, "prefLabel"),
            ["Getty Art & Architecture Thesaurus (AAT)"],
        )
        self.assertEqual(
            element_texts(scheme_element, DCTERMS_NAMESPACE, "identifier"),
            ["http://vocab.getty.edu/aat/300000000"],
        )

    def test_missing_archive_raises(self):
        with self.assertRaises(AATConversionError):
            convert_archive_to_skos(
                os.path.join(self.temporary_directory.name, "absent.zip"),
                self.skos_path,
                log=lambda message: None,
            )


class AttributionExtractionTests(TestCase):
    def test_sources_and_contributors_are_linked_to_labels(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = write_sample_archive(
                os.path.join(temporary_directory, "explicit.zip")
            )
            attribution_path = os.path.join(temporary_directory, "attribution.json")
            extract_attribution_from_archive(
                archive_path, attribution_path, log=lambda message: None
            )

            with open(attribution_path, encoding="utf-8") as attribution_file:
                attribution = json.load(attribution_file)

        self.assertIn(
            "http://vocab.getty.edu/aat/source/2000000001", attribution["sources"]
        )
        self.assertIn(
            "http://vocab.getty.edu/aat/contrib/1000000001",
            attribution["contributors"],
        )
        labels_for_concept = attribution["labels"][
            "http://vocab.getty.edu/aat/300000001"
        ]
        self.assertEqual(
            labels_for_concept[0]["sources"],
            ["http://vocab.getty.edu/aat/source/2000000001"],
        )


class ExtractionDateTests(TestCase):
    def test_extraction_date_comes_from_the_newest_data_member(self):
        """Getty stamps each member as it writes it, so the newest is the build date."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = os.path.join(temporary_directory, "explicit.zip")
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    zipfile.ZipInfo("AATOut_1Subjects.nt", (2026, 8, 1, 6, 33, 20)), ""
                )
                archive.writestr(
                    zipfile.ZipInfo("AATOut_2Terms.nt", (2026, 8, 1, 8, 24, 22)), ""
                )
            self.assertEqual(
                read_archive_extraction_date(archive_path),
                datetime.date(2026, 8, 1),
            )

    def test_files_getty_carries_forward_do_not_drag_the_date_back(self):
        """The archive ships an alignment file years older than the build."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = os.path.join(temporary_directory, "explicit.zip")
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    zipfile.ZipInfo("AATOut_1Subjects.nt", (2026, 8, 1, 6, 33, 20)), ""
                )
                archive.writestr(
                    zipfile.ZipInfo(
                        "AATOut_WikidataAlignment.nt", (2024, 11, 14, 8, 39, 48)
                    ),
                    "",
                )
            self.assertEqual(
                read_archive_extraction_date(archive_path),
                datetime.date(2026, 8, 1),
            )


class AttributionStatementTests(TestCase):
    def test_extraction_date_is_rendered_without_a_leading_zero(self):
        self.assertEqual(
            format_extraction_date(datetime.date(2026, 8, 1)), "August 1, 2026"
        )

    def test_attribution_names_the_extraction_date(self):
        attribution = build_aat_attribution(datetime.date(2026, 8, 1))
        self.assertIn("This copy was extracted on August 1, 2026", attribution)
        self.assertIn("Open Data Commons Attribution License (ODC-By) 1.0", attribution)
        self.assertIn(
            "https://www.getty.edu/research/tools/vocabularies/aat/", attribution
        )


class StreamProgressTests(TestCase):
    """The progress wrapper sits in front of every line the load parses."""

    def test_every_line_is_yielded_unchanged(self):
        first_stream = [b"line one\n", b"line two\n"]
        second_stream = [b"line three\n"]
        total_bytes = sum(len(line) for line in first_stream + second_stream)

        yielded = list(
            stream_lines_with_progress(
                [first_stream, second_stream],
                total_bytes,
                title="test",
                show_progress=False,
            )
        )

        self.assertEqual(yielded, first_stream + second_stream)

    def test_lines_are_yielded_when_the_total_is_unknown(self):
        lines = [b"a\n", b"b\n"]
        self.assertEqual(
            list(
                stream_lines_with_progress([lines], 0, title="test", show_progress=True)
            ),
            lines,
        )


class BatchProgressTests(TestCase):
    def test_every_batch_is_yielded_with_a_partial_final_batch(self):
        """The last batch is short, which is where a fixed step overshoots."""
        batch_size = 5000
        total = 84532
        batches = list(
            iterate_with_progress(
                range(0, total, batch_size),
                total,
                title="test",
                show_progress=False,
                step=batch_size,
            )
        )
        self.assertEqual(batches, list(range(0, total, batch_size)))
        self.assertEqual(len(batches), 17)


class HierarchyCycleTests(TestCase):
    """Cycles are legal SKOS, and AAT contains a few, so the load must survive
    them rather than reject the vocabulary."""

    @staticmethod
    def build_mutual_pair():
        first = "http://vocab.getty.edu/aat/300212545"
        second = "http://vocab.getty.edu/aat/300036794"
        outside = "http://vocab.getty.edu/aat/300205385"
        concepts = {first, second, outside}
        subject_data = {
            first: {SKOS_BROADER: [f"<{second}>", f"<{outside}>"]},
            second: {SKOS_BROADER: [f"<{first}>"]},
            outside: {},
        }
        return concepts, subject_data, first, second, outside

    def test_cycle_is_broken_without_dropping_a_preferred_parent(self):
        concepts, subject_data, first, second, outside = self.build_mutual_pair()
        # Each concept's preferred parent is the one outside the cycle.
        preferred_parents = {first: {outside}, second: {first}}

        removed = break_hierarchy_cycles(
            concepts, subject_data, preferred_parents, log=lambda message: None
        )

        self.assertEqual(removed, [(first, second)])
        self.assertEqual(find_hierarchy_cycles(concepts, subject_data), [])
        # The concept keeps its preferred parent rather than being orphaned.
        self.assertIn(f"<{outside}>", subject_data[first][SKOS_BROADER])

    def test_all_preferred_cycle_warns_loudly_and_still_breaks(self):
        concepts, subject_data, first, second, _outside = self.build_mutual_pair()
        # Nothing to prefer: both directions are the preferred parent.
        preferred_parents = {first: {second}, second: {first}}

        logged = []
        removed = break_hierarchy_cycles(
            concepts, subject_data, preferred_parents, log=logged.append
        )

        self.assertEqual(len(removed), 1)
        self.assertEqual(find_hierarchy_cycles(concepts, subject_data), [])
        self.assertTrue(
            any("consisted entirely of preferred parents" in line for line in logged),
            logged,
        )

    def test_validation_reports_a_surviving_cycle_without_raising(self):
        concepts, subject_data, *_ = self.build_mutual_pair()
        logged = []

        validate_output(concepts, [], subject_data, log=logged.append)

        self.assertTrue(
            any("survived cycle breaking" in line for line in logged), logged
        )


class CommandSmokeTests(TestCase):
    """`--help` does not execute handle(), so an unimported name used inside it
    reaches a real run undetected. These enter handle() far enough to catch it."""

    def test_load_aat_sources_handle_runs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            attribution_path = os.path.join(temporary_directory, "attribution.json")
            with open(attribution_path, "w", encoding="utf-8") as attribution_file:
                json.dump(
                    {"sources": {}, "contributors": {}, "labels": {}, "notes": {}},
                    attribution_file,
                )

            captured_output = io.StringIO()
            call_command(
                "load_aat_sources",
                source=attribution_path,
                dry_run=True,
                stdout=captured_output,
            )

        self.assertIn("Dry run", captured_output.getvalue())

    def test_update_aat_concept_types_handle_runs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = write_sample_archive(
                os.path.join(temporary_directory, "explicit.zip")
            )
            skos_path = os.path.join(temporary_directory, "aat.xml")
            convert_archive_to_skos(archive_path, skos_path, log=lambda message: None)

            # Reaching the missing-list-items check means handle() ran; the
            # term types controlled list is not loaded in the test database.
            with self.assertRaises(CommandError) as raised:
                call_command(
                    "update_aat_concept_types",
                    source=skos_path,
                    dry_run=True,
                    stdout=io.StringIO(),
                )

        self.assertIn("term_types.xml", str(raised.exception))


class LabelLanguageTests(TestCase):
    """AAT tags many labels with romanised variants (ar-Latn, ko-Hang,
    zh-Latn-wadegile). The language datatype resolves a value against both code
    and name and takes the first match, so passing a name that several codes
    share silently files the label under the wrong one."""

    def test_language_code_is_passed_through_not_the_name(self):
        mock_tile = LingoResourceImporter.create_mock_tile_from_value(
            {
                "value": "kutub",
                "valuetype_id": "prefLabel",
                "language_id": "ar-Latn",
            },
            lang_lookup={},
        )
        self.assertEqual(
            mock_tile["appellative_status"][
                "appellative_status_ascribed_name_language"
            ],
            "ar-Latn",
        )

    def test_note_language_code_is_passed_through(self):
        mock_tile = LingoResourceImporter.create_mock_tile_from_value(
            {
                "value": "a scope note",
                "valuetype_id": "scopeNote",
                "language_id": "zh-Latn-wadegile",
            },
            lang_lookup={},
        )
        self.assertEqual(
            mock_tile["statement"]["statement_language"], "zh-Latn-wadegile"
        )


class LanguageNamingTests(TestCase):
    """Language pickers show the name, so two codes sharing one are
    indistinguishable to the user and ambiguous to any lookup by name."""

    def test_script_and_region_variants_get_distinct_names(self):
        variant_codes = [
            "ar",
            "ar-Latn",
            "ko",
            "ko-Latn",
            "ko-Hang",
            "ko-Hani",
            "en",
            "en-GB",
            "en-US",
            "zh-Hant",
            "zh-Latn-wadegile",
            "zh-Latn-pinyin-x-hanyu",
        ]
        names = [resolve_language_metadata(code)["name"] for code in variant_codes]
        self.assertEqual(len(names), len(set(names)), names)

    def test_tags_are_matched_case_insensitively(self):
        """AAT writes "ar-Latn"; the override table is keyed "ar-latn"."""
        self.assertEqual(
            resolve_language_metadata("ar-Latn")["name"],
            "Arabic (Latin transliteration)",
        )

    def test_romanised_text_reads_left_to_right(self):
        self.assertEqual(resolve_language_metadata("ar")["default_direction"], "rtl")
        self.assertEqual(
            resolve_language_metadata("ar-Latn")["default_direction"], "ltr"
        )
