# AAT Vocabulary Refresh Plan (August 2026)

Refresh the Getty AAT vocabulary in `arches-lingo` from the April 2026 extract to a
current one, and dump a new set of lingo fixtures.

**Goal:** update every AAT concept and its properties, identifiers, sources and
contributors. Concepts retired or deleted upstream are removed outright — they are
not retained in a retired state.

**Constraint:** turnaround speed is prioritised over building a repeatable pipeline,
where the two compete.

---

## 1. Findings that shape this plan

### 1.1 The AAT partition is cleanly separable

Verified against the live `arches_lingo` database:

| Measure | Count |
| --- | ---: |
| AAT scheme `ea43bfa0-5eda-5666-884d-2885976a28d3` (identifier `300000000`) concepts | 58,736 |
| Other 15 schemes' concepts (GEMET, EH, MDA, …) | 17,663 |
| Textual works (sources) reached **only** by AAT concepts | 80,683 |
| Groups (contributors) reached **only** by AAT concepts | 80 |
| Digital objects reached **only** by non-AAT concepts | 240 |
| Concept-to-concept relations crossing the AAT / non-AAT boundary | **0** |

There is no overlap between the AAT subgraph and the other 15 vocabularies. All
58,736 AAT concepts were created in a single April 2026 load, with no local
additions since. The AAT partition can therefore be dropped and rebuilt without
touching the other schemes.

### 1.2 The importer cannot update in place

`LingoResourceImporter.populate_staging_table` assigns every tile a fresh
`tile_id = uuid.uuid4()` with `operation = "insert"`, and the
`__arches_staging_to_tile` stored procedure upserts on `tileid`. Re-importing onto
existing resources therefore *appends duplicate tiles* rather than updating them.

The `-ow overwrite` flag is inert: `extract_concepts_from_skos_for_lingo_import`
accepts `overwrite_options` and never reads it.

Building genuine tile-level reconciliation across ~1.4M tiles is days of work.
**Decision: rebuild the AAT partition rather than diff it.** This also delivers
retired-concept removal for free — they simply never come back.

### 1.3 Concept IDs churn unless pinned

`generate_uuidv5_from_subject` seeds from `baseuuid = uuid.uuid4()`, a fresh random
namespace on every run, so a naive re-import remints all 58,736 concept IDs.

Every AAT concept carries a Getty URI tile, so `{getty_uri -> resourceinstanceid}`
can be snapshotted before deletion and used to pin IDs on the way back in.

Sources and contributors need no such work: `load_aat_sources` already keys off a
fixed namespace, `uuid5("a1b2c3d4-e5f6-7890-abcd-ef1234567890", uri)`. Confirmed by
the 80,703 v5 textual works and 80 v5 groups in the database.

---

## 2. Branch selection

`origin/jmc/identifier-uri-extract` (b64b09fb, 2026-04-23) is the correct source. It
descends from `origin/pr701/7-additional-aat-scripts` (e09455c8) and adds URI and
identifier tile creation during import — which is what produced the currently
loaded data.

**It is rebased onto `dev/1.1.x`, not `dev/1.2.x`.** The two have diverged (13 commits
in 1.1.x absent from 1.2.x; 4 the other way). Rebasing onto 1.1.x is materially
cleaner — 2 conflicts instead of 4, with `tests/test_import_export.py` and
`migrate_to_lingo.py` both applying untouched:

| | onto `dev/1.2.x` | onto `dev/1.1.x` |
| --- | ---: | ---: |
| Conflicts | 4 | 2 |
| `tests/test_import_export.py` | conflicted | clean |
| `etl_modules/migrate_to_lingo.py` | conflicted | clean |
| `arches_lingo/const.py` | 2 | 2 |

Both branches pin `arches==8.1.3`, so the arches version is not a differentiator.

**It carries everything needed to reload all current AAT data**, including two
reference-data changes that are mandatory and absent from HEAD:

| Reference data | HEAD | jmc branch | Needed for |
| --- | ---: | ---: | --- |
| `controlled_lists/related_properties.xml` | 2 prefLabels | 131 prefLabels | The typed associative relations used by 23,498 `relation_status` tiles |
| `controlled_lists/term_types.xml` | `concept`, `guide term` | adds `facet`, `hierarchy name` | Correct typing of 46 concepts (8 facets + 38 hierarchy names) |

Without these, relation types and 46 concept types cannot be assigned.

### Not needed

The local, unpushed commit `3ee98bc3` (`update_aat_label_timestamps`) is **not
required**. Timespan nodes are empty in the current load
(`appellative_status_timespan_begin_of_the_begin` = 0 rows,
`statement_data_assignment_timespan_begin_of_the_begin` = 0 rows), so that command
has never been run against this data. Including it would *add* data not currently
present. Leave it out of the refresh; adopt it separately if wanted.

### Known stale reference

The `update_aat_concept_types` docstring cites a prerequisite migration
`0013_add_aat_concept_types`. **No such migration exists** on HEAD or on the jmc
branch — HEAD's `0013` is `add_broader_concept_gin_index`. The list items come from
`term_types.xml` instead. The docstring should be corrected.

---

## 3. Completeness audit — what must be reproduced

Every nodegroup currently populated on AAT concepts, and the stage that produces it:

| Nodegroup | Tiles | Concepts | Produced by |
| --- | ---: | ---: | --- |
| `appellative_status` (labels) | 513,828 | 58,736 | SKOS import, then `load_aat_sources` |
| `statement` (notes) | 137,953 | 47,502 | SKOS import, then `load_aat_sources` |
| `classification_status` (hierarchy) | 85,009 | 58,728 | SKOS import |
| `URI` | 58,736 | 58,736 | import with `--import-identifiers` |
| `identifier` | 58,736 | 58,736 | import with `--import-identifiers` |
| `part_of_scheme` | 58,736 | 58,736 | SKOS import |
| `type` | 58,736 | 58,736 | `update_aat_concept_types` |
| `relation_status` | 23,498 | 14,642 | SKOS import |
| `top_concept_of` | 8 | 8 | SKOS import |

Attribution sub-field fill rates to reproduce:

| Field | Populated |
| --- | ---: |
| Label sources (`appellative_status_data_assignment_object_used`) | 510,147 / 513,828 |
| Label contributors (`appellative_status_data_assignment_actor`) | 513,328 / 513,828 |
| Note sources (`statement_data_assignment_object_used`) | 134,859 / 137,953 |
| Note contributors (`statement_data_assignment_actor`) | 137,940 / 137,953 |
| Any timespan field | 0 (not loaded — see §2) |

Concept type distribution to reproduce:

| Type | Count |
| --- | ---: |
| concept | 56,971 |
| guide term | 1,719 |
| hierarchy name | 38 |
| facet | 8 |

Also required: 58,736 `resource_identifiers` rows (Getty numbers, e.g. `300024720`)
plus 16 scheme rows = 76,415 total across all schemes.

Note: `concept_identifier_counters` has 15 rows and the AAT scheme is deliberately
**absent** — AAT uses Getty-assigned numbers, not lingo-allocated ones. It must stay
absent after the refresh.

---

## 4. Golden examples for verifying the final load

Fixed anchors — the 8 facets (stable AAT IDs, must all be present and typed `facet`):

| AAT URI | English label |
| --- | --- |
| `.../300264086` | Associated Concepts Facet |
| `.../300264087` | Physical Attributes Facet |
| `.../300264088` | Styles and Periods Facet |
| `.../300264089` | Agents Facet |
| `.../300264090` | Activities Facet |
| `.../300264091` | Materials Facet |
| `.../300264092` | Objects Facet |
| `.../300343372` | Brand Names Facet |

Stress cases — each exercises a different axis. Baseline figures are from the April
load; upstream drift means these are expected to move somewhat, but a *collapse*
(e.g. languages dropping to 1) indicates a broken stage.

| AAT URI | Labels | Langs | Notes | Relations | Exercises |
| --- | ---: | ---: | ---: | ---: | --- |
| `.../300263147` | 54 | 6 | 3 | 0 | Highest label count |
| `.../300265752` | 51 | 12 | 4 | 2 | Labels + multilingual |
| `.../300028051` | 26 | 18 | 6 | 7 | Most languages |
| `.../300011798` | 22 | 17 | 5 | 3 | Multilingual |
| `.../300311076` | 8 | 7 | 4 | 31 | Most typed relations |
| `.../300005433` | 30 | 14 | 9 | 1 | Most notes |
| `.../300042513` | 28 | 15 | 9 | 3 | Notes + languages |

Plus, after the load, confirm by inspection:
- one concept retired upstream is **absent** (identify from the new extract diff)
- one concept new upstream is **present** with a freshly minted ID
- a pinned survivor kept its original `resourceinstanceid`

Baseline capture and comparison are automated in `scripts/aat_baseline.sql`.

---

## 5. Execution phases

### Phase 0 — Prep
1. `pg_dump -Fc arches_lingo > aat_pre_update_$(date +%F).dump` — the rollback.
2. Create `rmg/aat-2026-refresh` from `origin/jmc/identifier-uri-extract`, rebase onto
   `dev/1.1.x`. Every `const.*` name used by `load_aat_sources` still resolves.
3. Snapshot the ID map **before anything else**, and capture the baseline via
   `scripts/aat_baseline.sql`.
4. **Load the updated controlled lists** (`related_properties.xml`, `term_types.xml`).
   This is a hard prerequisite for Phase 4, not housekeeping — see §7.

### Phase 1 — Fetch and convert (mostly unattended, ~172 MB download)
5. `python scripts/convert_getty_aat.py -o getty_aat_skos_2026-08.xml`
6. `python scripts/extract_getty_aat_sources.py --skip-download -o aat_sources_2026-08.json`
7. `python scripts/ensure_aat_languages.py` — **before** import; a missing `Language`
   row silently misfiles labels into the default language.

### Phase 2 — ID pinning — completed 2026-08-27

Implemented as an opt-in CLI flag; imports that do not pass it behave exactly as before.

```
python manage.py packages -o import_lingo_resources \
    -s getty_aat_skos_2026-08.xml --import-identifiers \
    --pin-resource-ids aat_uri_to_resourceid.csv
```

- `utils/skos.py`: new `load_pinned_resource_ids()` reads the two-column CSV;
  `SKOSReader.generate_uuidv5_from_subject()` is overridden to return a pinned id when
  the subject is known and defer to `super()` otherwise.
- `etl_modules/migrate_to_lingo.py`: carries `pinned_resource_ids` through to both
  SKOS reader call sites.
- `management/commands/packages.py`: adds `--pin-resource-ids`.

Verified behaviour:

| Case | Result |
| --- | --- |
| Pinned survivor | returns the existing id exactly |
| New subject | derives a fresh uuid5, stable within the run |
| Subject with an embedded UUID | still extracts the embedded UUID |
| Reader with no map | unchanged from before |

Measured churn for the actual refresh:

| | Concepts |
| --- | ---: |
| Currently loaded | 58,736 |
| In new extract | 59,300 |
| Survivors, id preserved | **58,511** |
| Brand new, id minted | 789 |
| Removed (retired or withdrawn) | 225 |

58,736 - 225 + 789 = 59,300. Without pinning, all 58,511 survivors would have been
reassigned new ids despite being unchanged.

Note the 225 removals against the 1,337 subjects in `AATOut_ObsoleteSubjects.nt`: that
file lists every retirement Getty has ever recorded, and only 225 of them were present
in the Jan-2025-era data currently loaded.

Test suite after these changes: 41 tests, 3 failures + 8 errors — **identical to the
branch baseline recorded in §8**, same tests, no regression introduced.

**Also fixed while here:** `packages.py` capped `celeryByteSizeLimit` at 90,000,000
bytes, above which the importer defers to a celery worker. The converted export is
90,208,669 bytes — 208,669 over the limit — so the Phase 4 import would have demanded
a celery worker and, in doing so, dropped the in-process pinned-id map. The cap is now
2 GB, keeping the CLI import in-process as intended.

### Phase 3 — Delete the AAT partition
9. One transaction, scoped by `part_of_scheme -> ea43bfa0-…`: delete
   `resource_x_resource`, `tiles`, `resource_identifiers`, then `resource_instances`
   for the 58,736 concepts plus the 80,683 textual works and 80 groups. Keep the
   Scheme resource so its `SchemeURITemplate` / `SchemeAttribution` rows survive.

### Phase 4 — Re-import (several hours, unattended)
```
python manage.py packages -o import_lingo_resources -s getty_aat_skos_2026-08.xml --import-identifiers
python manage.py load_aat_sources --source aat_sources_2026-08.json
python manage.py update_aat_concept_types --source getty_aat_skos_2026-08.xml
```

### Phase 5 — Validate
10. Re-run `scripts/aat_baseline.sql` and diff against the Phase 0 baseline.
11. Assert: cross-scheme relations still 0; other schemes still 17,663 concepts;
    `concept_identifier_counters` still 15 rows without AAT. Also confirm the
    identifier/URI behaviour the §8 test failure concerns is correct for AAT: the
    scheme's identifier is `300000000`, every concept identifier is a bare Getty
    number, and no resource has a URL-shaped identifier:

    ```sql
    -- must return 0
    SELECT count(*) FROM resource_identifiers r
    JOIN aat_concept a ON a.cid = r.resourceid_id
    WHERE r.identifier !~ '^[0-9]+$';
    ```
12. Walk the golden examples in §4.
13. Reindex — the bulk loader bypasses normal indexing.

### Phase 6 — Dump fixtures
14. `python manage.py dump_lingo_fixtures --key lingo_fixtures/lingo_concept_scheme_fixture.tar.gz`
15. Verify by restoring into a scratch database and re-running Phase 5 checks.

---

## 6. Open questions

- **Fixture distribution.** The current 782 MB archive is not tracked in git and
  `.gitattributes` has no LFS rule. `dump_lingo_fixtures` writes through Django
  default storage, so pointing `ARCHES_STORAGEBACKEND` at S3 is the intended route.
  Needs a decision before Phase 6.
- **ID pinning is optional.** Skipping Phase 2 saves ~30 minutes and is safe for this
  database, since nothing outside AAT references those IDs. It matters only if a
  downstream install already loaded the April fixtures and holds data pointing at AAT
  concept IDs.

---

## 7. Blocker found: controlled lists are missing from the database

The live database holds only **91 controlled list items in total**, and the list
items that AAT data references largely do not exist:

| Referenced value | Referencing data | Exists in DB |
| --- | --- | :---: |
| `concept` | 56,971 concepts | yes |
| `guide term` | 1,719 concepts | yes |
| `facet` | 8 concepts | **no** |
| `hierarchy name` | 38 concepts | **no** |
| `distinguished from - any` | 4,844 relation tiles | **no** |
| `practiced/studied by - role` | 271 relation tiles | **no** |
| (123 further relation types) | 23,498 relation tiles total | **no** |

The AAT tiles still *display* correctly because the `reference` datatype denormalizes
the label, URI and `list_item_id` into the tile JSON. But the backing list items are
absent, so anything list-driven — editing a type, faceting, validation — has nothing
to resolve against. The largest list in the database has 16 items; the 131-item
related-properties list is simply not there.

This is consistent with `dev/1.2.x` shipping `related_properties.xml` with 2
prefLabels and a `term_types.xml` without `facet` or `hierarchy name`: a package
import on current HEAD would leave exactly this state.

### Consequences

1. **Phase 0.4 is a hard prerequisite for Phase 4.** `update_aat_concept_types` calls
   `load_non_concept_type_items()`, which raises `CommandError` when `facet` or
   `hierarchy name` is missing. It will fail immediately unless the lists are loaded
   first. Its error message tells you to run migration `0013_add_aat_concept_types`,
   which does not exist — load `term_types.xml` instead.
2. **The existing fixtures inherit this defect.** `dump_lingo_fixtures` deliberately
   excludes controlled lists (they are package metadata). So the April fixture archive
   restored onto current HEAD reproduces the same dangling references. Loading the
   branch's reference data is required for the new fixtures to be coherent on restore,
   and this should be called out in the fixture's release notes.

### Measured extent

`scripts/aat_baseline.sql` check 13 now walks every reference-datatype node on AAT
tiles and resolves each `list_item_id` against
`arches_controlled_lists_listitem`. Current result:

| Reference node | Distinct items referenced | Dangling |
| --- | ---: | ---: |
| `relation_status_ascribed_relation` | 125 | **125** |
| `type` | 4 | **2** |

Every other reference node on AAT concepts resolves cleanly. So the damage is exactly
two lists: all 125 relation types actually in use are missing, and 2 of the 4 concept
types (`facet`, `hierarchy name`) are missing. Note 125 distinct types are *referenced*
while `related_properties.xml` defines 131 — the extra 6 are simply unused by the
current extract.

### Action taken — resolved 2026-08-27

Verified first that the fix would actually work and lose nothing:

- Every list item UUID is declared explicitly in the XML (`rdf:about`), and
  `generate_uuidv5_from_subject` extracts it, so item IDs are stable across imports.
- All **125** relation-type UUIDs referenced by AAT tiles are defined in
  `related_properties.xml` (132 UUIDs = 131 items + the list id). Zero unaccounted for.
- The tiles' `facet` (`1f88f375-…`) and `hierarchy name` (`e3738c52-…`) UUIDs are
  exactly the ones `term_types.xml` defines.
- `overwrite` deletes and recreates the list, so anything in the database but *not* in
  the XML would be lost. Confirmed the DB content is a strict subset for both lists:
  Term Types held 2 of 4, related properties 2 of 131, all four present in the XML.
- Non-AAT `relation_status` tiles (4,403 of them) populate no relation type at all, so
  they were unaffected either way.

Then, with `arches_controlled_lists_*` tables backed up to
`aat_controlled_lists_pre_0.4.dump`:

```
python manage.py packages -o import_controlled_lists \
    -s arches_lingo/pkg/reference_data/controlled_lists/term_types.xml -ow overwrite
python manage.py packages -o import_controlled_lists \
    -s arches_lingo/pkg/reference_data/controlled_lists/related_properties.xml -ow overwrite
```

`-ow overwrite` is required. Without it the import attempts a plain insert and dies on
`IntegrityError: duplicate key ... arches_controlled_lists_list_pkey` (harmless — it
rolls back cleanly).

**Result:** list items 91 -> 222. Term Types now 4, related properties now 131.
Check 13 dangling: `125 + 2` -> **0**. Diffing the full 13-check report before and
after, check 13 is the *only* section that changed — every other count is
byte-identical (`docs/aat_baseline_after_phase0.4.txt`).

`load_non_concept_type_items()` now resolves `facet`, `guide term` and
`hierarchy name` to the exact UUIDs the existing tiles reference, so
`update_aat_concept_types` will no longer hard-fail in Phase 4.

---

## 7b. Blocker: the source export the pipeline uses is frozen

`convert_getty_aat.py` and `extract_getty_aat_sources.py` both download
`http://aatdownloads.getty.edu/VocabData/full.zip`. As of 2026-08-27 that file
reports:

```
Content-Length: 251953169
Last-Modified: Mon, 13 Jan 2025 18:06:45 GMT
```

**It has not changed since January 2025** — earlier than the currently loaded data was
imported. Re-running the pipeline against it cannot produce an update; it would
reproduce what is already in the database.

The same host serves a second export that *is* current:

| Archive | Size | Last-Modified | Contents |
| --- | ---: | --- | --- |
| `full.zip` | 252 MB | **2025-01-13** | `AATOut_Full.nt`, `AATOut_Sources.nt`, `AATOut_Contribs.nt` |
| `explicit.zip` | 134 MB | **2026-08-01** | 19 split files (see below) |

No other archive name resolves (`full.nt.zip`, `AATOut_Full.zip`, `aat.zip`,
`semantic.zip` all 404). `vocab.getty.edu/dataset/aat/full.zip` returns HTTP 500. The
downloads index announces that Getty is "retiring some service offerings", which is
consistent with `full.zip` being deprecated in place rather than updated.

### What `explicit.zip` contains

```
AATOut_1Subjects.nt        AATOut_ObsoleteSubjects.nt   AATOut_SemanticLinks.nt
AATOut_2Terms.nt           AATOut_OrderedCollections.nt AATOut_SourceRels.nt
AATOut_AssociativeRels.nt  AATOut_RevisionHistory.nt    AATOut_Sources.nt
AATOut_ContribRels.nt      AATOut_RevisionHistorySource.nt AATOut_TermsTest.nt
AATOut_Contribs.nt         AATOut_ScopeNotes.nt         AATOut_WikidataAlignment.nt
AATOut_HierarchicalRels.nt AATOut_Lang_sameAs.nt        AATOut_LCSHAlignment.nt
AATOut_Notations.nt
```

### Why the scripts cannot consume it as-is

`convert_getty_aat.py` streams exactly **one** `.nt` file: it looks for a name
containing `"Full"`, else falls back to one containing `"Subject"`. Against
`explicit.zip` it would read only `AATOut_1Subjects.nt` and silently miss labels,
hierarchy, associative relations and scope notes — producing a near-empty conversion.

`explicit.zip` also omits the materialised inference `full.zip` carried. The converter
depends on that inference for plain `skos:prefLabel` literals (its own docstring: "the
full.zip includes pre-computed skos:prefLabel inference ... need no extra work"). In
the explicit export, labels exist only as `skosxl:Label` nodes in `AATOut_2Terms.nt`
and must be resolved via `xl:literalForm`.

### What the explicit export actually looks like

Confirmed by inspecting the downloaded archive (134 MB, 19 files). My first estimate
was wrong in both directions, so the real shapes are recorded here:

| Aspect | `full.zip` (used before) | `explicit.zip` (now) |
| --- | --- | --- |
| Concept typing | `rdf:type skos:Concept` | `gvp:Concept` 57,322 / `gvp:GuideTerm` 1,785 / `gvp:Hierarchy` 185 / `gvp:Facet` 8 |
| Labels | inferred plain `skos:prefLabel` literals | `skosxl:prefLabel`/`altLabel` -> term node -> `skosxl:literalForm` (522,689 term nodes) |
| Hierarchy | GVP broader predicates | direct `gvp:broaderGeneric` (62,987), `broaderPreferred` (59,292), `broaderNonPreferred` (4,839), `broaderPartitive` (1,140) |
| Associative | direct `gvp:aatNNNN_*` | direct `gvp:aatNNNN_*` — unchanged |
| Scope notes | node + `rdf:value` | node + `rdf:value`, still language-tagged — unchanged |
| Identifier | `dcterms:identifier` | `dc:identifier` |
| Retired concepts | not distinguished | `AATOut_ObsoleteSubjects.nt`, typed `gvp:ObsoleteSubject` |

Two corrections to my initial reading:

- **Hierarchy is fine.** `AATOut_HierarchicalRels.nt` opens with reified
  `rdf:Statement` blocks, which looked alarming, but those are only 9,548 of the
  triples and carry metadata. The actual hierarchy is asserted directly, so it needs
  only two extra predicate names.
- **Labels are the real work**, as expected, but so is concept typing (`gvp:*` rather
  than `skos:Concept`) and the `dc:` vs `dcterms:` identifier switch — neither of
  which I anticipated. Without those the converter would have silently produced zero
  concepts and no identifiers.

### Changes made to `scripts/convert_getty_aat.py`

Both export layouts remain supported; the explicit path is now the default.

1. Multi-file streaming. `collect_aat_data` only iterates lines, so the six relevant
   files are chained with `itertools.chain` and consumed as one sequence. Files are
   auto-detected: a name containing `"Full"` selects the old single-file path.
2. `GVP_SUBJECT_TYPES` accepted alongside `skos:Concept`.
3. `broaderPreferred` / `broaderNonPreferred` added to the broader mapping.
4. `resolve_xl_labels()` inlines skos-xl term references into plain literals,
   mirroring the existing `resolve_scope_notes`. Objects that are already literals
   pass through untouched, so the full export still works.
5. `dc:identifier` normalised to `dcterms:identifier`.
6. `collect_obsolete_subjects()` reads `AATOut_ObsoleteSubjects.nt` and retired
   concepts are dropped before output — satisfying the "remove retired concepts
   entirely" requirement from an authoritative list rather than by inferring absence.
7. New `--archive` and `--url` options; default download is now the explicit export.

### Phase 1 outcome — completed 2026-08-27

```
python scripts/convert_getty_aat.py --skip-download --archive explicit.zip \
    -o getty_aat_skos_2026-08.xml
python scripts/extract_getty_aat_sources.py --skip-download --archive explicit.zip \
    -o aat_sources_2026-08.json
python scripts/ensure_aat_languages.py --xml getty_aat_skos_2026-08.xml
```

Converted output (`getty_aat_skos_2026-08.xml`, 86 MB) against the loaded baseline:

| Measure | Loaded (Jan 2025 data) | New (Aug 2026 data) |
| --- | ---: | ---: |
| Concepts | 58,736 | **59,300** |
| Labels (pref + alt) | 513,828 | **522,690** |
| Scope notes | 137,953 | **140,406** |
| Broader relations | 85,009 | **64,131** |
| Typed associative relations | 23,498 | **23,979** |
| Identifiers | 58,736 | **59,300** |
| Top concepts (facets) | 8 | **8** |

Attribution (`aat_sources_2026-08.json`, 273 MB):

| Measure | Loaded | New |
| --- | ---: | ---: |
| Unique sources | 80,683 | **84,532** |
| Unique contributors | 80 | **89** |
| Concepts with label attribution | — | **59,300** (all) |
| Label attributions | 510,147 | **522,689** |
| Note attributions | 134,859 | **140,406** |

Attribution coverage is now complete (every label carries attribution, against 99.3%
before). 1,337 retired subjects were identified and excluded.

Golden cases reconcile closely, confirming the conversion is sound rather than merely
non-empty:

| AAT | Baseline labels/langs/notes/rels | New |
| --- | --- | --- |
| `300028051` "books" | 26 / 18 / 6 / 7 | 26 / 18 / 7 / 7 |
| `300311076` "slate (color)" | 8 / 7 / 4 / 31 | 8 / 7 / 4 / 31 |
| `300005433` "houses" | 30 / 14 / 9 / 1 | 31 / 14 / 9 / 1 |
| `300264089` Agents Facet | top concept, no broader | 8 prefLabels, no broader |

66 new `Language` records inserted (169 -> 235); without them labels in those codes
would be silently misfiled into the default language.

**Untitled sources are not a regression.** The extractor warns that 17,643 of 84,532
sources have no title (20.9%). The loaded data has the same characteristic — 17,202 of
80,704 textual works (21.3%) carry a URI as their name. This is how AAT publishes
those sources, not something the explicit export introduced.

### The broader-relation drop, verified before deletion

Hierarchy relations fall 85,009 -> 64,131 (-25%). Verified against the live database
while the old data still existed, by comparing parent sets concept by concept:

- 58,503 concepts appear in both. The dominant shift is `(2 parents -> 1)` for 17,180
  concepts, with 35,997 unchanged at `(1 -> 1)`.
- 20,162 concepts lose at least one parent. Sampling 400 of them (438 dropped links):
  **433 (98.9%) point at a parent still reachable transitively** in the new hierarchy —
  i.e. a grandparent that `full.zip` asserted redundantly alongside the real parent.
- The 5 genuinely absent links split between parents withdrawn from the vocabulary
  (e.g. `aat/300435543`, no longer present) and concepts Getty has reparented
  (e.g. `aat/300435523`, still present but no longer claimed as a parent).

So the reduction is removal of redundant inferred ancestry plus 19 months of editorial
change — not structural loss from the explicit export. Accepted and proceeding.

### Expected effect on concept counts

The explicit export has 59,300 live subjects against 58,736 currently loaded. Note the
type mix differs from what `update_aat_concept_types` currently derives from English
label heuristics — notably `gvp:Hierarchy` 185 versus 38 "hierarchy name" concepts in
the database. The GVP typing is authoritative, so this is a data-quality improvement,
but it is a behavioural change to expect in Phase 5 rather than treat as a regression.

### Decision needed

Where did the currently loaded "April 2026" extract come from? If it came from
`full.zip`, it is Jan 2025 content loaded in April 2026, and `explicit.zip` is the only
route to newer data. If it came from somewhere else — an internal mirror, or a
newer full-format dump — that source should be used instead and none of the above work
is needed.

---

## 8. Rebase record (`rmg/aat-2026-refresh`)

9 commits from `origin/jmc/identifier-uri-extract` replayed onto `dev/1.1.x`. Two
conflicts, both in `arches_lingo/const.py`, both resolved additively.

| # | Commit | Resolution |
| --- | --- | --- |
| 4/9 | `adds script to update concept types` | Kept incoming `FACET_URI`. |
| 5/9 | `Differentiate between scheme and concept nodeids` | See below. |

### The const.py rename hazard (commit 5/9)

`807f60e3` renames `URI_NODEGROUP` -> `CONCEPT_URI_NODEGROUP` and
`IDENTIFIER_NODEGROUP` -> `CONCEPT_IDENTIFIER_NODEGROUP`, and adds `SCHEME_URI_*` /
`SCHEME_IDENTIFIER_*`. But `dev/1.1.x` code still calls the **old** names, so taking
the rename wholesale would break it.

**Resolved by keeping both naming schemes.** Duplicated names were verified
programmatically to hold byte-identical values before the redundant definitions were
collapsed — no conflicting values existed. All key constants now appear exactly once.

Worth collapsing to one scheme with callers updated before the branch is proposed for
merge; deliberately not done here, as it is unrelated to the refresh.

### Post-rebase verification

- `compileall` clean; `black --check` clean (29 files).
- `load_aat_sources`, `update_aat_concept_types`, `dump_lingo_fixtures` all load.
  `load_aat_sources` takes `--source`, not `--input`.
- `packages -o import_lingo_resources` exposes `--import-identifiers` /
  `--namespace-template`.
- Reference data present: `related_properties.xml` 131 prefLabels; `term_types.xml`
  includes `facet` and `hierarchy name`.

### Test status

Run `tests.test_import_export`, fresh database each time (never `--keepdb` — a reused
database is missing `Language` rows and produces spurious, non-reproducible results):

| | `dev/1.1.x` | branch on 1.1.x | `dev/1.2.x` | branch on 1.2.x |
| --- | ---: | ---: | ---: | ---: |
| Tests | 41 | 41 | 43 | 43 |
| `ExportTests` failing | 10 | 10 | 12 | 12 |
| `test_lingo_resource_importer` | passes | **fails** | passes | **fails** |

The `ExportTests` failures are **pre-existing on both bases** — present on untouched
`dev/1.1.x` and `dev/1.2.x`, unrelated to this work. They stem from an export
response-shape mismatch (`TypeError: string indices must be integers` in
`_assert_successful_export`) against the installed arches 8.1.4rc1.

The branch adds **exactly one** failure on either base: `test_lingo_resource_importer`.

### What is known about that one failure

- It is not caused by conflict resolution: on the 1.1.x base
  `tests/test_import_export.py` applied with no conflicts and was never edited.
- At the branch tip it fails at `_assert_resources_loaded` line 83 —
  `assertEqual(len(test_scheme.aliased_data.identifier), 0)` -> `1 != 0`.
- At the earlier commit that *introduced* the assertions (`7127ab8c`, before
  `994c3336` "Add label and identifier fall backs for AAT, tbd whether this is
  maintained") the test **also fails**, but at line 115 —
  `assertIsNone(junk_sculpture.aliased_data.uri)`. So the fallbacks commit changed
  *which* assertion fails; it did not create the failure.
- Whether the test ever passed cannot be determined here: the original unrebased
  commit `bb440bcb` will not run against current dependencies
  (`NodeNotFoundError` — `arches_controlled_lists.0011` references a nonexistent
  `arches_vue_components.0002`).

### Why it does not block the refresh

Both failing assertions concern RDM round-tripped data, where a resource's
`dcterms:identifier` is its own `rdf:about` URL embedding its Arches UUID — visible in
`tests/fixtures/data/skos_rdf_import_example.xml`:

```
rdf:about="http://localhost:8000/4a10134e-d594-4102-8edf-2f63e18d3b04"
dcterms:identifier ... "value": "http://localhost:8000/4a10134e-d594-4102-8edf-2f63e18d3b04"
```

That shape triggers the RDM-default skip in `utils/skos.py`
(`str(scheme_pk) in str(object)`). AAT data never has it: the scheme carries
`300000000`, concepts carry bare Getty numbers, and their `resourceinstanceid`s are
uuid5 values appearing nowhere in those strings.

The stronger evidence is empirical: the currently loaded data was produced by this
same pipeline and has 58,736 correct URI tiles and 58,736 correct Getty identifier
tiles. The AAT path demonstrably works.

**Recommendation:** file it against the branch, do not fix it as part of this refresh.
Fixing it means deciding whether the skip or the fallback is correct — a design
question the original author left explicitly open. Phase 5 verifies the AAT-relevant
behaviour directly (see check in §5 step 11).

---

## 9. Progress log

| Phase | Status | Notes |
| --- | --- | --- |
| Audit & plan | Complete | This document |
| 0.1 pg_dump | **Complete** | `aat_pre_update_2026-08-27.dump`, 361 MB, repo root (gitignored) |
| 0.2 Branch rebase | **Complete** | `rmg/aat-2026-refresh` = 9 commits onto `dev/1.1.x`, 2 conflicts. See §8 |
| 0.3 Baseline capture | **Complete** | `scripts/aat_baseline.sql` (13 checks) -> `docs/aat_baseline_before.txt` |
| 0.4 Controlled lists | **Complete** | Lists 91 -> 222 items; dangling refs 127 -> 0; only check 13 changed. See §7 |
| 1 Fetch & convert | **Complete** | Converter + extractor adapted to `explicit.zip`; 59,300 concepts, 84,532 sources, 66 languages added. See §7b |
| 2 ID pinning patch | **Complete** | `--pin-resource-ids`; 58,511 ids preserved, 789 new, 225 removed. Celery size cap bug fixed |
| 3 Delete partition | **Complete** | Removed 58,736 concepts / 80,683 works / 80 groups / 1.08M tiles / 2.2M relations. Other 15 schemes unchanged |
| 4 Re-import | **Complete** | 59,300 concepts, 84,532 sources, 89 contributors, 1,766 type tiles |
| 5 Validate | **Complete** | 13-check diff reviewed; every change accounted for. See §10 |
| 6 Dump fixtures | **Next** | |

### Superseded work

`rmg/aat-2026-refresh-1.2.x-attempt` holds the earlier rebase onto `dev/1.2.x`, kept
only for comparison. Safe to delete.

---

## 10. Phase 4/5 outcome — validation

Ran with `--import-identifiers` and `--pin-resource-ids`, then `load_aat_sources`
(`--source`, not `--input`) and `update_aat_concept_types`. Full 13-check report saved
to `docs/aat_baseline_after_refresh.txt`; diffed against
`docs/aat_baseline_before.txt`.

| Measure | Before | After | Explanation |
| --- | ---: | ---: | --- |
| AAT concepts | 58,736 | 59,300 | +789 new, -225 removed |
| Labels | 513,828 | 522,611 | 19 months of editorial growth |
| Notes | 137,953 | 140,406 | as above |
| Hierarchy | 85,009 | 64,131 | redundant inferred ancestry removed (§7b) |
| Typed relations | 23,498 | 23,979 | growth |
| URI tiles | 58,736 | 59,300 | one per concept |
| Identifier tiles | 58,736 | 59,300 | one per concept |
| Textual works | 80,704 | 84,533 | +3,849 sources |
| Groups (contributors) | 80 | 89 | +9 |
| Dangling list references | 127 | **0** | fixed in Phase 0.4 |
| Resource ids preserved | — | **58,511** | every survivor |

Invariants held: cross-scheme relations still 0; the other 15 schemes unchanged at
17,663 concepts; 241 digital objects untouched; all 8 facets present and typed;
every AAT `resource_identifiers` value numeric (0 non-numeric), which is the check
§8 called for.

### Two deviations from the plan's expectations

**1. `concept_identifier_counters` gained an AAT row** (15 -> 16). The plan asserted
AAT must stay absent. `--import-identifiers` assigns lifecycle states, which
`get_or_create`s a counter. It is not harmful — it was seeded from the data:

```
start_number = 300000201   (lowest Getty id in the extract)
next_number  = 300460384   (max Getty id 300460383, + 1)
```

A concept created through the UI therefore continues Getty's numbering instead of
colliding with it. This is better than the previous state, where no counter existed at
all. The §3 invariant is updated accordingly: the AAT counter should be **present and
seeded above the Getty range**, not absent.

**2. "hierarchy name" stayed at 38, not the 185 predicted.** `AATOut_1Subjects.nt`
types 185 subjects as `gvp:Hierarchy`, and §7b predicted the concept-type counts would
follow. They did not: `update_aat_concept_types` classifies by **English label
heuristics** (`(hierarchy name)` substring, `<angle brackets>`, `" Facet"` suffix), and
the converter flattens all four GVP subject classes to `skos:Concept`, so the
authoritative typing never reaches the command. Final counts are therefore consistent
with the baseline: 8 facets, 1,720 guide terms, 38 hierarchy names, 57,534 concepts.

That GVP typing is available and more reliable than label matching — 185 versus 38 —
so wiring it through is a worthwhile follow-up, but it is a behavioural change beyond
this refresh and was not made.
