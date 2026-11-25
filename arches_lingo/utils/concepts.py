import json
from functools import cached_property

from django.db import connection
from django.utils.translation import gettext as _

from arches.app.models.system_settings import settings
from arches_lingo.const import (
    ALT_LABEL_URI,
    CONCEPT_NAME_CONTENT_NODE,
    CONCEPT_NAME_LANGUAGE_NODE,
    CONCEPT_NAME_NODEGROUP,
    CONCEPT_NAME_TYPE_NODE,
    CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID,
    PREF_LABEL_URI,
)


ORDER_MODE_ALPHABETICAL = "alphabetical"
ORDER_MODE_REVERSE_ALPHABETICAL = "reverse-alphabetical"
ORDER_MODE_UNSORTED = "unsorted"
# pg_trgm cannot index a "contains" pattern shorter than this, but a prefix
# pattern of any length can still use the trigram index.
MIN_INDEXED_CONTAINS_LENGTH = 3
# Defined by migration 0022, which indexes label content through it.
UNACCENT_FUNCTION = "__arches_lingo_immutable_unaccent"


def escape_like_pattern(term):
    """Escape LIKE wildcards so a term containing ``%`` or ``_`` matches literally."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
    excluded_ids=None,
    scheme_ids=None,
    lifecycle_state_ids=None,
    prefix_only=False,
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
        excluded_ids=excluded_ids,
        scheme_ids=scheme_ids,
        lifecycle_state_ids=lifecycle_state_ids,
        prefix_only=prefix_only,
    )


def _edit_distance_to_similarity_threshold(max_edit_distance, term_length):
    """Convert a max edit distance to an approximate pg_trgm similarity threshold."""
    if max_edit_distance == 0 or term_length == 0:
        return 1.0
    ratio = max_edit_distance / max(term_length, 1)
    return max(0.1, round(1.0 - ratio, 2))


def build_concept_ids_for_non_fuzzy(
    labels_queryset, order_mode, scheme_ids=None, excluded_ids=None
):
    """Return a SearchResultSet for browsing (no search term)."""
    return SearchResultSet(
        term=None,
        use_fuzzy=False,
        similarity_threshold=1.0,
        order_mode=order_mode,
        active_language="",
        system_language="",
        scheme_ids=scheme_ids,
        excluded_ids=excluded_ids,
    )


class SearchResultSet:
    """Paginator-compatible object backed by raw SQL against the GIN trigram index.

    Supports .count() and slice access (__getitem__) as required by
    Django's Paginator.  All SQL uses ``tiledata ->> 'node_id'`` directly
    so PostgreSQL can use the GIN trigram index for fast filtering.
    """

    CONTENT_COL = f"(tiledata ->> '{CONCEPT_NAME_CONTENT_NODE}')"
    # Label content without diacritics, written exactly as the index on it.
    SEARCH_COL = f"{UNACCENT_FUNCTION}({CONTENT_COL})"
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
        excluded_ids=None,
        scheme_ids=None,
        lifecycle_state_ids=None,
        prefix_only=False,
    ):
        self.term = term
        self.like_term = None if term is None else escape_like_pattern(term)
        self.use_fuzzy = use_fuzzy
        self.similarity_threshold = similarity_threshold
        self.order_mode = order_mode
        self.active_language = active_language
        self.system_language = system_language
        self.exact_match = exact_match
        self.excluded_ids = excluded_ids or []
        # None leaves results unfiltered; an empty collection matches nothing.
        self.scheme_ids = scheme_ids
        self.lifecycle_state_ids = lifecycle_state_ids
        self.prefix_only = prefix_only
        self._count_cache = None

    @cached_property
    def folded_terms(self):
        """Return (term, like_term) without diacritics, so "apa" matches "apă".

        Folded here rather than in each pattern's SQL so the patterns reach
        PostgreSQL as constants the trigram index can be planned against.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {UNACCENT_FUNCTION}(%s), {UNACCENT_FUNCTION}(%s)",
                [self.term, self.like_term],
            )
            return cursor.fetchone()

    def _filtered_labels_cte(self):
        """Return (sql, params) for a WITH clause defining ``filtered_labels``.

        ``filtered_labels`` has one row per matching label, with columns
        ``resourceinstanceid``, ``label_content``, ``label_type`` and
        ``label_language``.

        PostgreSQL overestimates how many labels a one- or two-character term
        matches. When such a term is limited by scheme or lifecycle state, it
        would start from every concept in scope and test each label in turn,
        never using the trigram index, so those label matches are materialized
        first. Longer terms are left to the planner, which estimates them well
        and can then run the query in parallel.
        """
        term_sql, term_params = self._term_filter()
        concept_sql, concept_params = self._concept_filter()
        has_concept_scope = (
            self.scheme_ids is not None or self.lifecycle_state_ids is not None
        )
        has_short_term = (
            self.term is not None and len(self.term) < MIN_INDEXED_CONTAINS_LENGTH
        )
        materialization = "MATERIALIZED" if has_concept_scope and has_short_term else ""

        sql = f"""
            WITH matching_labels AS {materialization} (
                SELECT
                    resourceinstanceid,
                    {self.CONTENT_COL} AS label_content,
                    {self.SEARCH_COL} AS search_content,
                    {self.TYPE_COL} AS label_type,
                    {self.LANG_COL} AS label_language
                FROM tiles
                WHERE {self.NODEGROUP_FILTER}{term_sql}
            ),
            filtered_labels AS (
                SELECT *
                FROM matching_labels
                WHERE TRUE{concept_sql}
            )
        """
        return sql, term_params + concept_params

    def _term_filter(self):
        """Return (sql_fragment, params) matching label content against the term."""
        where_sql = ""
        params = []

        if self.term is not None:
            if self.exact_match:
                where_sql += f" AND {self.CONTENT_COL} = %s"
                params.append(self.term)
            else:
                folded_term, folded_like_term = self.folded_terms
                if self.prefix_only:
                    where_sql += f" AND {self.SEARCH_COL} ILIKE %s"
                    params.append(f"{folded_like_term}%")
                elif self.use_fuzzy:
                    # ILIKE uses the GIN trigram index; %% is the pg_trgm
                    # similarity operator (escaped for cursor.execute).
                    where_sql += (
                        f" AND ({self.SEARCH_COL} ILIKE %s"
                        f" OR {self.SEARCH_COL} %% %s)"
                    )
                    params.extend([f"%{folded_like_term}%", folded_term])
                else:
                    where_sql += f" AND {self.SEARCH_COL} ILIKE %s"
                    params.append(f"%{folded_like_term}%")

        return where_sql, params

    def _concept_filter(self):
        """Return (sql_fragment, params) limiting labels by their concept."""
        where_sql = ""
        params = []

        if self.scheme_ids is not None:
            where_sql += (
                f" AND resourceinstanceid IN ("
                f"SELECT resourceinstanceid FROM tiles"
                f" WHERE nodegroupid = '{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'"
                f" AND tiledata -> '{CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'"
                f" @> ANY(%s::jsonb[]))"
            )
            params.append(
                [
                    json.dumps([{"resourceId": str(scheme_id)}])
                    for scheme_id in self.scheme_ids
                ]
            )

        if self.lifecycle_state_ids is not None:
            where_sql += (
                " AND resourceinstanceid IN ("
                "SELECT resourceinstanceid FROM resource_instances"
                " WHERE resource_instance_lifecycle_state_id = ANY(%s::uuid[]))"
            )
            params.append([str(state_id) for state_id in self.lifecycle_state_ids])

        if self.excluded_ids:
            placeholders = ", ".join(["%s"] * len(self.excluded_ids))
            where_sql += f" AND resourceinstanceid NOT IN ({placeholders})"
            params.extend(str(excluded_id) for excluded_id in self.excluded_ids)

        return where_sql, params

    def _build_base_sql(self):
        """Build the core query that filters, ranks, and deduplicates."""
        if self.term is None:
            return self._build_browse_sql()

        return self._build_search_sql()

    def _build_browse_sql(self):
        """SQL for browsing without a search term."""
        if self.order_mode == ORDER_MODE_ALPHABETICAL:
            order_clause = "ORDER BY sort_label ASC, resourceinstanceid"
        elif self.order_mode == ORDER_MODE_REVERSE_ALPHABETICAL:
            order_clause = "ORDER BY sort_label DESC, resourceinstanceid"
        else:
            order_clause = "ORDER BY resourceinstanceid"

        with_sql, with_params = self._filtered_labels_cte()
        sql = f"""
            {with_sql}
            SELECT resourceinstanceid
            FROM (
                SELECT
                    resourceinstanceid,
                    MIN(LOWER(label_content)) AS sort_label
                FROM filtered_labels
                GROUP BY resourceinstanceid
            ) grouped
            {order_clause}
        """
        return sql, with_params

    def _build_search_sql(self, include_scores=False):
        """SQL for term search with ranking.

        ``include_scores`` also selects ``best_rank`` and the best trigram
        ``best_similarity`` of any matching label, for callers that score matches.
        """
        if include_scores:
            selected_columns = "resourceinstanceid, best_rank, best_similarity"
            similarity_column = (
                "MAX(similarity(LOWER(search_content), LOWER(%s)))"
                " AS best_similarity,"
            )
            similarity_params = [self.folded_terms[0]]
        else:
            selected_columns = "resourceinstanceid"
            similarity_column = ""
            similarity_params = []

        if self.order_mode == ORDER_MODE_UNSORTED:
            order_clause = "ORDER BY best_rank, sort_label"
        elif self.order_mode == ORDER_MODE_ALPHABETICAL:
            order_clause = "ORDER BY sort_label ASC, resourceinstanceid"
        else:
            order_clause = "ORDER BY sort_label DESC, resourceinstanceid"

        with_sql, with_params = self._filtered_labels_cte()
        sql = f"""
            {with_sql}
            SELECT {selected_columns}
            FROM (
                SELECT
                    resourceinstanceid,
                    MIN(
                        (CASE
                            WHEN label_type = %s
                                 AND search_content ILIKE %s
                            THEN 0
                            WHEN label_type = %s
                                 AND search_content ILIKE %s
                            THEN 1
                            WHEN label_type = %s
                                 AND search_content ILIKE %s
                            THEN 2
                            WHEN label_type = %s
                                 AND search_content ILIKE %s
                            THEN 3
                            WHEN label_type = %s
                                 AND search_content ILIKE %s
                            THEN 4
                            WHEN search_content ILIKE %s
                            THEN 4
                            WHEN label_type = %s
                                 AND search_content ILIKE %s
                            THEN 5
                            WHEN search_content ILIKE %s
                            THEN 5
                            WHEN search_content ILIKE %s
                            THEN 6
                            ELSE 7
                        END) * 1000
                        + (CASE
                            WHEN label_language = %s THEN 0
                            WHEN label_language = %s THEN 1
                            ELSE 2
                        END)
                    ) AS best_rank,
                    {similarity_column}
                    MIN(LOWER(label_content)) AS sort_label
                FROM filtered_labels
                GROUP BY resourceinstanceid
            ) ranked
            {order_clause}
        """

        like_term = self.folded_terms[1]
        rank_params = [
            PREF_LABEL_URI,
            like_term,  # prefLabel exact
            ALT_LABEL_URI,
            like_term,  # altLabel exact
            PREF_LABEL_URI,
            f"{like_term}%",  # prefLabel prefix
            PREF_LABEL_URI,
            f"%{like_term}%",  # prefLabel contains
            ALT_LABEL_URI,
            f"{like_term}%",  # altLabel prefix
            like_term,  # any exact
            ALT_LABEL_URI,
            f"%{like_term}%",  # altLabel contains
            f"{like_term}%",  # any prefix
            f"%{like_term}%",  # any contains
            self.active_language,
            self.system_language,
        ]

        params = with_params + rank_params + similarity_params
        return sql, params

    def scored_slice(self, limit):
        """Return ``[(concept_id, best_rank, best_similarity)]`` for the best matches."""
        sql, params = self._build_search_sql(include_scores=True)
        with connection.cursor() as cursor:
            cursor.execute(f"{sql} LIMIT %s", params + [limit])
            return [
                (str(concept_id), best_rank, best_similarity)
                for concept_id, best_rank, best_similarity in cursor.fetchall()
            ]

    def count(self):
        if self._count_cache is not None:
            return self._count_cache

        with_sql, with_params = self._filtered_labels_cte()
        sql = f"""
            {with_sql}
            SELECT COUNT(DISTINCT resourceinstanceid)
            FROM filtered_labels
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, with_params)
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
