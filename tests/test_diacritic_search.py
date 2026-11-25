from django.db import connection, transaction

from arches.app.models.models import TileModel

from arches_lingo.const import (
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_NODEGROUP,
    STATEMENT_CONTENT_NODE,
    STATEMENT_NODEGROUP,
)
from arches_lingo.utils.advanced_search import AdvancedSearchEvaluator
from arches_lingo.utils.concepts import ORDER_MODE_UNSORTED, build_search_queryset
from tests.tests import SchemeWithConceptsTestCase

# These tests can be run from the command line via:
# python manage.py test tests.test_diacritic_search --settings="tests.test_settings"


INDEX_TEST_FILLER_LABEL_COUNT = 1000


class DiacriticInsensitiveSearchTests(SchemeWithConceptsTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Romanian writes ș and ț with a comma below, but older text uses the
        # cedilla forms ş and ţ; both should be found by either, or by neither.
        cls.water, cls.comma_below_science, cls.cedilla_science = cls.concepts[:3]
        for concept, label in (
            (cls.water, "apă"),
            (cls.comma_below_science, "știință"),
            (cls.cedilla_science, "ştiinţă"),
        ):
            TileModel.objects.create(
                resourceinstance=concept,
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data={CONCEPT_NAME_CONTENT_NODE: label},
            )
        TileModel.objects.create(
            resourceinstance=cls.water,
            nodegroup_id=STATEMENT_NODEGROUP,
            data={STATEMENT_CONTENT_NODE: "Apă dulce sau sărată."},
        )

    def search(self, term):
        results = build_search_queryset(None, term, 0, ORDER_MODE_UNSORTED)
        return set(results[0 : results.count()])

    def test_concept_search_ignores_diacritics(self):
        science_ids = {self.comma_below_science.pk, self.cedilla_science.pk}
        for term, expected_ids in (
            ("apa", {self.water.pk}),
            ("APĂ", {self.water.pk}),
            ("stiinta", science_ids),
            ("știință", science_ids),
            ("ştiinţă", science_ids),
        ):
            with self.subTest(term=term):
                self.assertEqual(self.search(term), expected_ids)

    def test_advanced_search_labels_and_notes_ignore_diacritics(self):
        evaluator = AdvancedSearchEvaluator(user=self.admin)
        for facet, value in (("label", "apa"), ("note", "sarata")):
            with self.subTest(facet=facet):
                self.assertEqual(
                    set(evaluator.evaluate({"facet": facet, "value": value})),
                    {self.water.pk},
                )

    def test_search_can_use_the_unaccented_label_index(self):
        """The search expression must match the index's expression exactly,
        or the index is silently never used. Enough other labels are added
        that scanning every label costs more than using the index."""
        TileModel.objects.bulk_create(
            TileModel(
                resourceinstance=self.concepts[-1],
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                data={CONCEPT_NAME_CONTENT_NODE: f"filler label {number}"},
            )
            for number in range(INDEX_TEST_FILLER_LABEL_COUNT)
        )
        sql, params = build_search_queryset(
            None, "stiinta", 0, ORDER_MODE_UNSORTED
        )._build_base_sql()
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("ANALYZE tiles")
            cursor.execute("SET LOCAL enable_seqscan = off")
            cursor.execute(f"EXPLAIN {sql}", params)
            plan = "\n".join(row[0] for row in cursor.fetchall())
        self.assertIn("tiles_unaccented_label_content_trgm", plan)
