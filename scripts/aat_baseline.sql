-- AAT refresh baseline / verification report.
--
-- Run before the refresh to capture a baseline, and again afterwards to diff:
--     psql -d arches_lingo -f scripts/aat_baseline.sql > aat_baseline_before.txt
--     psql -d arches_lingo -f scripts/aat_baseline.sql > aat_baseline_after.txt
--     diff aat_baseline_before.txt aat_baseline_after.txt
--
-- Counts are expected to drift with the upstream vocabulary. What must NOT change
-- is the shape: cross-scheme relations stay 0, the other 15 schemes keep their
-- concept counts, every concept keeps a URI + identifier + type, and the AAT
-- scheme stays absent from concept_identifier_counters.

\pset footer off

\set aat_scheme '''ea43bfa0-5eda-5666-884d-2885976a28d3'''
\set ng_part_of_scheme '''bf73e60a-4888-11ee-8a8d-11afefc4bff7'''
\set ng_uri '''bf73e598-4888-11ee-8a8d-11afefc4bff7'''
\set node_uri '''bf73e64a-4888-11ee-8a8d-11afefc4bff7'''
\set ng_label '''ab9fee9c-0eb6-11ef-93db-0a58a9feac02'''
\set ng_note '''bf73e5d7-4888-11ee-8a8d-11afefc4bff7'''
\set ng_type '''74d4d2cc-0f5d-11ef-9493-0a58a9feac02'''

CREATE TEMP TABLE aat_concept AS
SELECT resourceinstanceid AS cid
FROM tiles
WHERE nodegroupid = :ng_part_of_scheme::uuid
  AND tiledata -> :ng_part_of_scheme ->> 0 IS NOT NULL
  AND (tiledata -> :ng_part_of_scheme -> 0 ->> 'resourceId') = :aat_scheme;
CREATE INDEX ON aat_concept (cid);

CREATE TEMP TABLE aat_uri AS
SELECT t.resourceinstanceid AS cid, t.tiledata ->> :node_uri AS uri
FROM tiles t JOIN aat_concept a ON a.cid = t.resourceinstanceid
WHERE t.nodegroupid = :ng_uri::uuid;
CREATE INDEX ON aat_uri (cid);

\echo '== 1. AAT concept count =='
SELECT count(*) AS aat_concepts FROM aat_concept;

\echo '== 2. Concepts per scheme (non-AAT counts must be unchanged) =='
SELECT tiledata -> :ng_part_of_scheme -> 0 ->> 'resourceId' AS scheme_id,
       count(DISTINCT resourceinstanceid) AS concepts
FROM tiles WHERE nodegroupid = :ng_part_of_scheme::uuid
GROUP BY 1 ORDER BY 2 DESC;

\echo '== 3. Tiles per nodegroup on AAT concepts =='
SELECT n.name AS nodegroup, count(*) AS tiles,
       count(DISTINCT t.resourceinstanceid) AS concepts
FROM tiles t JOIN aat_concept a ON a.cid = t.resourceinstanceid
JOIN nodes n ON n.nodeid = t.nodegroupid
GROUP BY 1 ORDER BY 2 DESC;

\echo '== 4. Attribution fill rates (timespans expected 0) =='
SELECT 'labels' AS tile_kind, count(*) AS total,
  count(*) FILTER (WHERE jsonb_typeof(t.tiledata->'df980c50-0eb8-11ef-93db-0a58a9feac02')='array'
    AND jsonb_array_length(t.tiledata->'df980c50-0eb8-11ef-93db-0a58a9feac02')>0) AS with_sources,
  count(*) FILTER (WHERE jsonb_typeof(t.tiledata->'0acd2982-0eb9-11ef-93db-0a58a9feac02')='array'
    AND jsonb_array_length(t.tiledata->'0acd2982-0eb9-11ef-93db-0a58a9feac02')>0) AS with_contributors,
  count(*) FILTER (WHERE t.tiledata->>'93544d18-0eb8-11ef-93db-0a58a9feac02' IS NOT NULL) AS with_timespan
FROM tiles t JOIN aat_concept a ON a.cid = t.resourceinstanceid
WHERE t.nodegroupid = :ng_label::uuid
UNION ALL
SELECT 'notes', count(*),
  count(*) FILTER (WHERE jsonb_typeof(t.tiledata->'bf73e652-4888-11ee-8a8d-11afefc4bff7')='array'
    AND jsonb_array_length(t.tiledata->'bf73e652-4888-11ee-8a8d-11afefc4bff7')>0),
  count(*) FILTER (WHERE jsonb_typeof(t.tiledata->'bf73e650-4888-11ee-8a8d-11afefc4bff7')='array'
    AND jsonb_array_length(t.tiledata->'bf73e650-4888-11ee-8a8d-11afefc4bff7')>0),
  count(*) FILTER (WHERE t.tiledata->>'de191d08-0f60-11ef-9493-0a58a9feac02' IS NOT NULL)
FROM tiles t JOIN aat_concept a ON a.cid = t.resourceinstanceid
WHERE t.nodegroupid = :ng_note::uuid;

\echo '== 5. Concept type distribution =='
SELECT t.tiledata -> :ng_type -> 0 -> 'labels' -> 0 ->> 'value' AS concept_type, count(*)
FROM tiles t JOIN aat_concept a ON a.cid = t.resourceinstanceid
WHERE t.nodegroupid = :ng_type::uuid GROUP BY 1 ORDER BY 2 DESC;

\echo '== 6. Top relation types in use =='
SELECT t.tiledata->'799ba8ce-0ed3-11ef-9493-0a58a9feac02'->0->'labels'->0->>'value' AS relation_type,
       count(*)
FROM tiles t JOIN aat_concept a ON a.cid = t.resourceinstanceid
WHERE t.nodegroupid = '807ef412-0ebe-11ef-9493-0a58a9feac02'::uuid
GROUP BY 1 ORDER BY 2 DESC LIMIT 20;

\echo '== 7. Coverage gaps: AAT concepts missing URI / identifier / type (must be 0) =='
SELECT
 (SELECT count(*) FROM aat_concept a WHERE NOT EXISTS
   (SELECT 1 FROM tiles t WHERE t.resourceinstanceid=a.cid AND t.nodegroupid=:ng_uri::uuid)) AS missing_uri,
 (SELECT count(*) FROM aat_concept a WHERE NOT EXISTS
   (SELECT 1 FROM tiles t WHERE t.resourceinstanceid=a.cid
      AND t.nodegroupid='bf73e5d1-4888-11ee-8a8d-11afefc4bff7'::uuid)) AS missing_identifier_tile,
 (SELECT count(*) FROM aat_concept a WHERE NOT EXISTS
   (SELECT 1 FROM tiles t WHERE t.resourceinstanceid=a.cid AND t.nodegroupid=:ng_type::uuid)) AS missing_type,
 (SELECT count(*) FROM aat_concept a WHERE NOT EXISTS
   (SELECT 1 FROM resource_identifiers r WHERE r.resourceid_id=a.cid)) AS missing_resource_identifier;

\echo '== 8. Cross-scheme concept relations (must be 0) =='
WITH cs AS (
  SELECT resourceinstanceid AS cid,
         (tiledata -> :ng_part_of_scheme -> 0 ->> 'resourceId') AS scheme
  FROM tiles WHERE nodegroupid = :ng_part_of_scheme::uuid
)
SELECT count(*) AS cross_scheme_relations
FROM resource_x_resource r
JOIN cs f ON f.cid = r.resourceinstanceidfrom
JOIN cs t ON t.cid = r.resourceinstanceidto
WHERE (f.scheme = :aat_scheme) <> (t.scheme = :aat_scheme);

\echo '== 9. Attribution resources by graph =='
SELECT g.name->>'en' AS model, count(*)
FROM resource_instances ri JOIN graphs g ON g.graphid = ri.graphid
GROUP BY 1 ORDER BY 2 DESC;

\echo '== 10. concept_identifier_counters (AAT scheme must be ABSENT) =='
SELECT count(*) AS counter_rows,
       count(*) FILTER (WHERE scheme_resource_instance_id::text = :aat_scheme) AS aat_rows
FROM concept_identifier_counters;

\echo '== 11. The 8 facets (all must be present, typed facet) =='
SELECT u.uri,
       ty.tiledata -> :ng_type -> 0 -> 'labels' -> 0 ->> 'value' AS concept_type
FROM aat_uri u
JOIN tiles ty ON ty.resourceinstanceid = u.cid AND ty.nodegroupid = :ng_type::uuid
WHERE u.uri IN (
  'http://vocab.getty.edu/aat/300264086','http://vocab.getty.edu/aat/300264087',
  'http://vocab.getty.edu/aat/300264088','http://vocab.getty.edu/aat/300264089',
  'http://vocab.getty.edu/aat/300264090','http://vocab.getty.edu/aat/300264091',
  'http://vocab.getty.edu/aat/300264092','http://vocab.getty.edu/aat/300343372')
ORDER BY u.uri;

\echo '== 12. Golden stress cases (shape must hold; counts may drift) =='
SELECT u.uri,
 (SELECT count(*) FROM tiles t WHERE t.resourceinstanceid=u.cid AND t.nodegroupid=:ng_label::uuid) AS labels,
 (SELECT count(DISTINCT t.tiledata->>'a8ecaf54-0eb7-11ef-93db-0a58a9feac02')
    FROM tiles t WHERE t.resourceinstanceid=u.cid AND t.nodegroupid=:ng_label::uuid) AS langs,
 (SELECT count(*) FROM tiles t WHERE t.resourceinstanceid=u.cid AND t.nodegroupid=:ng_note::uuid) AS notes,
 (SELECT count(*) FROM tiles t WHERE t.resourceinstanceid=u.cid
    AND t.nodegroupid='807ef412-0ebe-11ef-9493-0a58a9feac02'::uuid) AS relations
FROM aat_uri u
WHERE u.uri IN (
  'http://vocab.getty.edu/aat/300263147','http://vocab.getty.edu/aat/300265752',
  'http://vocab.getty.edu/aat/300028051','http://vocab.getty.edu/aat/300011798',
  'http://vocab.getty.edu/aat/300311076','http://vocab.getty.edu/aat/300005433',
  'http://vocab.getty.edu/aat/300042513')
ORDER BY u.uri;

\echo '== 13. Controlled-list referential integrity (dangling must be 0) =='
-- The `reference` datatype denormalizes labels into tile JSON, so tiles render
-- correctly even when the backing list item no longer exists. This check reads
-- every reference-datatype node on AAT tiles and confirms each referenced
-- list_item_id resolves to a real row.
SELECT n.name AS ref_node,
       count(DISTINCT lab ->> 'list_item_id') AS distinct_items,
       count(DISTINCT lab ->> 'list_item_id') FILTER (WHERE li.id IS NULL) AS dangling
FROM tiles t
JOIN aat_concept a ON a.cid = t.resourceinstanceid
JOIN nodes n ON n.nodegroupid = t.nodegroupid AND n.datatype = 'reference'
CROSS JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(t.tiledata -> n.nodeid::text) = 'array'
       THEN t.tiledata -> n.nodeid::text ELSE '[]'::jsonb END) ref
CROSS JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(ref -> 'labels') = 'array'
       THEN ref -> 'labels' ELSE '[]'::jsonb END) lab
LEFT JOIN arches_controlled_lists_listitem li ON li.id::text = lab ->> 'list_item_id'
GROUP BY 1
HAVING count(DISTINCT lab ->> 'list_item_id') FILTER (WHERE li.id IS NULL) > 0
ORDER BY 3 DESC;
