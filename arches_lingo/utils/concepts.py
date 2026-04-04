from django.db import connection
from django.utils.translation import gettext as _

from arches.app.models.system_settings import settings
from arches_lingo.const import (
    ALT_LABEL_URI,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    PREF_LABEL_URI,
)


ORDER_MODE_ALPHABETICAL = "alphabetical"
ORDER_MODE_REVERSE_ALPHABETICAL = "reverse-alphabetical"
ORDER_MODE_UNSORTED = "unsorted"


def resolve_max_edit_distance(term):
    elastic_prefix_length = settings.SEARCH_TERM_SENSITIVITY

    if elastic_prefix_length <= 0:
        base_max_edit_distance = 5
    elif elastic_prefix_length >= 5:
        base_max_edit_distance = 0
    else:
        base_max_edit_distance = int(5 - elastic_prefix_length)

    if not term:
        return base_max_edit_distance

    term_length = len(term)

    if term_length <= 3:
        return 0

    if term_length <= 5:
        return min(base_max_edit_distance, 1)

    return min(base_max_edit_distance, 2)


def build_search_queryset(
    labels_queryset,
    term,
    max_edit_distance,
    order_mode,
    active_language=None,
    system_language=None,
):
    """Return a SearchResultSet of concept IDs matching a search term.

    Uses raw SQL with ILIKE and pg_trgm similarity to leverage the GIN
    trigram index on label content, avoiding the sequential scan that the
    ORM's UPPER()/LIKE pattern would cause on large datasets.
    """
    if len(term) > 255:
        raise ValueError(_("Fuzzy search terms cannot exceed 255 characters."))

    try:
        max_edit_distance = int(max_edit_distance)
    except (ValueError, TypeError):
        raise ValueError(_("Edit distance could not be converted to an integer."))

    use_fuzzy = max_edit_distance > 0
    similarity_threshold = _edit_distance_to_similarity_threshold(
        max_edit_distance, len(term)
    )

    return SearchResultSet(
        term=term,
        use_fuzzy=use_fuzzy,
        similarity_threshold=similarity_threshold,
        order_mode=order_mode,
        active_language=active_language or "",
        system_language=system_language or "",
    )


def _edit_distance_to_similarity_threshold(max_edit_distance, term_length):
    """Convert a max edit distance to an approximate pg_trgm similarity threshold."""
    if max_edit_distance == 0 or term_length == 0:
        return 1.0
    ratio = max_edit_distance / max(term_length, 1)
    return max(0.1, round(1.0 - ratio, 2))


def build_concept_ids_for_non_fuzzy(labels_queryset, order_mode):
    """Return a SearchResultSet for browsing (no search term)."""
    return SearchResultSet(
        term=None,
        use_fuzzy=False,
        similarity_threshold=1.0,
        order_mode=order_mode,
        active_language="",
        system_language="",
    )


class SearchResultSet:
    """Paginator-compatible object backed by raw SQL against the GIN trigram index.

    Supports .count() and slice access (__getitem__) as required by
    Django's Paginator.  All SQL uses ``tiledata ->> 'node_id'`` directly
    so PostgreSQL can use the GIN trigram index for fast filtering.
    """

    CONTENT_COL = f"(tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}')"
    TYPE_COL = f"(tiledata -> '{CONCEPT_NAME_TYPE_NODE}' -> 0 ->> 'uri')"
    LANG_COL = f"(tiledata ->> '{CONCEPT_NAME_LANGUAGE_NODE}')"
    NODEGROUP_FILTER = f"nodegroupid = '{CONCEPT_NAME_NODEGROUP}'"

    def __init__(
        self,
        term,
        use_fuzzy,
        similarity_threshold,
        order_mode,
        active_language,
        system_language,
        exact_match=False,
    ):
        self.term = term
        self.use_fuzzy = use_fuzzy
        self.similarity_threshold = similarity_threshold
        self.order_mode = order_mode
        self.active_language = active_language
        self.system_language = system_language
        self.exact_match = exact_match
        self._count_cache = None

    def _where_clause(self):
        """Return (sql_fragment, params) for the WHERE filter."""
        base = self.NODEGROUP_FILTER

        if self.term is None:
            return base, []

        if self.exact_match:
            return f"{base} AND {self.CONTENT_COL} = %s", [self.term]

        if self.use_fuzzy:
            # ILIKE uses the GIN trigram index; %% is the pg_trgm similarity
            # operator (escaped for cursor.execute parameter substitution).
            return (
                f"{base} AND ({self.CONTENT_COL} ILIKE %s"
                f" OR {self.CONTENT_COL} %% %s)",
                [f"%{self.term}%", self.term],
            )

        return f"{base} AND {self.CONTENT_COL} ILIKE %s", [f"%{self.term}%"]

    def _build_base_sql(self):
        """Build the core query that filters, ranks, and deduplicates."""
        where_sql, where_params = self._where_clause()

        if self.term is None:
            return self._build_browse_sql(where_sql, where_params)

        return self._build_search_sql(where_sql, where_params)

    def _build_browse_sql(self, where_sql, where_params):
        """SQL for browsing without a search term."""
        if self.order_mode == ORDER_MODE_ALPHABETICAL:
            order_clause = "ORDER BY sort_label ASC, resourceinstanceid"
        elif self.order_mode == ORDER_MODE_REVERSE_ALPHABETICAL:
            order_clause = "ORDER BY sort_label DESC, resourceinstanceid"
        else:
            order_clause = "ORDER BY resourceinstanceid"

        sql = f"""
            SELECT resourceinstanceid
            FROM (
                SELECT
                    resourceinstanceid,
                    MIN(LOWER({self.CONTENT_COL})) AS sort_label
                FROM tiles
                WHERE {where_sql}
                GROUP BY resourceinstanceid
            ) grouped
            {order_clause}
        """
        return sql, where_params

    def _build_search_sql(self, where_sql, where_params):
        """SQL for term search with ranking."""
        if self.order_mode == ORDER_MODE_UNSORTED:
            order_clause = "ORDER BY best_rank, sort_label"
        elif self.order_mode == ORDER_MODE_ALPHABETICAL:
            order_clause = "ORDER BY sort_label ASC, resourceinstanceid"
        else:
            order_clause = "ORDER BY sort_label DESC, resourceinstanceid"

        sql = f"""
            SELECT resourceinstanceid
            FROM (
                SELECT
                    resourceinstanceid,
                    MIN(
                        (CASE
                            WHEN ({self.TYPE_COL}) = %s
                                 AND ({self.CONTENT_COL}) ILIKE %s
                            THEN 0
                            WHEN ({self.TYPE_COL}) = %s
                                 AND ({self.CONTENT_COL}) ILIKE %s
                            THEN 1
                            WHEN ({self.TYPE_COL}) = %s
                                 AND ({self.CONTENT_COL}) ILIKE %s
                            THEN 2
                            WHEN ({self.TYPE_COL}) = %s
                                 AND ({self.CONTENT_COL}) ILIKE %s
                            THEN 3
                            WHEN ({self.TYPE_COL}) = %s
                                 AND ({self.CONTENT_COL}) ILIKE %s
                            THEN 4
                            WHEN ({self.CONTENT_COL}) ILIKE %s
                            THEN 4
                            WHEN ({self.TYPE_COL}) = %s
                                 AND ({self.CONTENT_COL}) ILIKE %s
                            THEN 5
                            WHEN ({self.CONTENT_COL}) ILIKE %s
                            THEN 5
                            WHEN ({self.CONTENT_COL}) ILIKE %s
                            THEN 6
                            ELSE 7
                        END) * 1000
                        + (CASE
                            WHEN ({self.LANG_COL}) = %s THEN 0
                            WHEN ({self.LANG_COL}) = %s THEN 1
                            ELSE 2
                        END)
                    ) AS best_rank,
                    MIN(LOWER({self.CONTENT_COL})) AS sort_label
                FROM tiles
                WHERE {where_sql}
                GROUP BY resourceinstanceid
            ) ranked
            {order_clause}
        """

        rank_params = [
            PREF_LABEL_URI,
            self.term,  # prefLabel exact
            ALT_LABEL_URI,
            self.term,  # altLabel exact
            PREF_LABEL_URI,
            f"{self.term}%",  # prefLabel prefix
            PREF_LABEL_URI,
            f"%{self.term}%",  # prefLabel contains
            ALT_LABEL_URI,
            f"{self.term}%",  # altLabel prefix
            self.term,  # any exact
            ALT_LABEL_URI,
            f"%{self.term}%",  # altLabel contains
            f"{self.term}%",  # any prefix
            f"%{self.term}%",  # any contains
            self.active_language,
            self.system_language,
        ]

        params = rank_params + where_params
        return sql, params

    def count(self):
        if self._count_cache is not None:
            return self._count_cache

        where_sql, where_params = self._where_clause()
        sql = f"""
            SELECT COUNT(DISTINCT resourceinstanceid)
            FROM tiles
            WHERE {where_sql}
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, where_params)
            self._count_cache = cursor.fetchone()[0]
        return self._count_cache

    def __getitem__(self, key):
        if isinstance(key, slice):
            offset = key.start or 0
            limit = (key.stop or offset) - offset
            if limit <= 0:
                return []

            base_sql, base_params = self._build_base_sql()
            sql = f"{base_sql} LIMIT %s OFFSET %s"
            params = base_params + [limit, offset]

            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return [row[0] for row in cursor.fetchall()]

        raise TypeError("SearchResultSet only supports slice indexing.")
