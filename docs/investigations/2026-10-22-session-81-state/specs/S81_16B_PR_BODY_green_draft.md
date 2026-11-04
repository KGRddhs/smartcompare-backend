## S81-16b KB-BRANDS: migration 052 `kb_brands` (WRITTEN, NOT APPLIED) + the Wikidata brand import under `ENABLE_KB_BRANDS`

**MERGING THIS CHANGES NOTHING IN PRODUCTION**: 052 is written, not applied; no request path reads or writes `kb_brands`; the brand script runs only as a one-off command with `ENABLE_KB_BRANDS` set. **L6 (stated beside it):** the merge edits `scripts/kb_seed_common.py`, which all three G2 `railway.*.json` watch, so it re-deploys (= re-runs) the kbseed, feedwalker and pdpdiscovery jobs in whatever mode their flags hold: confirm `ENABLE_KB_SEED`, `ENABLE_FEED_WALKER`, `ENABLE_PDP_DISCOVERY` unset (or `false`) on their services BEFORE the merge (owner step 0).

Base `0b19de5b` (origin/main), HEAD `28eec42b2055920604acb1e4ef9765fe74126625` (branch `feature/s81-s16b-kb-brands`, one commit, 9 files). FOCUS unit (a migration): GREEN, then two adversaries (correctness; schema-and-data).

### What it does
- `migrations/052_kb_brands.sql` + `migrations/rollback/052_kb_brands.sql`: ONE table `public.kb_brands (qid PK, label_en, label_ar, official_host, source, created_at, updated_at)`; the qid CHECK `^Q[1-9][0-9]{0,11}$`; both labels 1..128 and `= btrim(...)`; the 045 host belts on `official_host` (host regex, deny-label `!~`, top-label constraint); `source` wikidata | operator; a partial NON-unique index on `official_host`; the 045 trigger function reused (`BEFORE UPDATE`); a DO guard refusing to run without 045; RLS on with no policy, `REVOKE ALL ... FROM PUBLIC, anon, authenticated, service_role` then `GRANT SELECT, INSERT, UPDATE, DELETE ... TO service_role` (the 045 pattern, the 037 both-readings rule). Rollback = `DROP TABLE IF EXISTS public.kb_brands` (the function is 045's and is kept); roll 052 back BEFORE any rollback of 045.
- `app/services/kb_service.py` (the leaf; no request path imports it): `kb_brands` LAST in `KB_TABLES` / `KB_COLUMNS` (hence `KB_BUILDER_KEYS`), `KB_QID_REGEX`, `KB_BRAND_SOURCES`, `KB_BRAND_UPSERT_SET`, and the pure `build_brand_row` mirroring every 052 CHECK (plus the deny RULE `kb_source_allowed` and a Python `strip()` refusal, stricter than btrim); None on any refusal, never raises. `kb_ingest` keys its writes by its own table constants and `KB_OFFER_UPSERT_SET` / `KB_OFFER_OBSERVATION_KEY` through kb_leaf, so the new census entry changes nothing for it (R-S16B-13).
- `scripts/kb_seed_common.py`: `KB_BRANDS_TABLE` + `KbWriter.brands` (insert-ignore on qid; one update of `KB_BRAND_UPSERT_SET` filtered on `qid` AND `source = 'wikidata'` per row the insert did not return; no delete, no select). The existing writer methods are byte-unchanged.
- `scripts/seed_kb_brands_wikidata.py`: its OWN flag `ENABLE_KB_BRANDS` (unset / blank / garbage / false / 0 / no / off / dry -> OFF; true / 1 / yes / on -> DRY; apply -> WRITE; `--dry-run` downgrades) read per call as the FIRST statement of `main`; OFF = one INFO line naming both flags, rc 0, before argv / client / any I/O, whatever `ENABLE_KB_SEED` holds. Knob `KB_BRANDS_MAX` (300, 1..5000). The SPARQL gains exact-language OPTIONAL labels (en, mul, ar), `FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 . }` and `ORDER BY xsd:integer(STRAFTER(STR(?brand), "/entity/Q")) ?site LIMIT 2000`. DRY: robots + ONE SPARQL GET + the unchanged host derivation + the brand rows and counts to `--report`, no write. APPLY: the same + `KbWriter.brands` (a failure = one WARNING with the type name, `write_failed=1`, the writer counters added in a `finally`). `derive_hosts`, `_site_host`, `sparql_url`, `_parse_args` byte-unchanged. `ENABLE_KB_SEED` never runs this script.
- Source: Wikidata (CC0 public-domain dedication), `query.wikidata.org` (already the G2 script's host), one GET per run. No new dependency, no new external host, no new credential name; no personal data (humans excluded, no user column, the 043 fence sees 052 with no gap).

### Defects -> RED nodes -> flag
| id | what | RED rows (tests/test_s81_s16b_kb_brands.py, 129 nodes) | flag / precondition |
|---|---|---|---|
| S16 L7 / R-G2-3 | brand labels not stored (no table) | B01-B12 (migration), K01-K06 (leaf), S01-S12 (script) | `ENABLE_KB_BRANDS=apply` after 052 is applied |
| R-S16B-1 | 052, never 051 | B01, B10 (no '051' text) | - |
| R-S16B-6 / 8 / 9 | the strip rule, the mul fallback, the numeric ORDER BY | K03, S03, S06, S07 | - |
| PIN-1..6 | batch seeder flag, host derivation literal, 045 census, app/ names nothing new, no service runs the script, 045 bytes | PIN rows (green at base and head) | - |

### Deliberate pin changes (spec 4.1)
| id | file | change | nodes |
|---|---|---|---|
| EK0 | tests/test_s81_s16_kb_seed.py `_env` | the autouse also deletes `ENABLE_KB_BRANDS`, `KB_BRANDS_MAX` | all (hermeticity) |
| EK1 | same, `_brand_bindings` + R23 | bindings carry `label_en`, qids from Q1; R23 sets `ENABLE_KB_BRANDS=<mode>` + `ENABLE_KB_SEED=apply`; DRY = no write, APPLY = `kb_brands` upsert / update only | 2 |
| EK2 | same, R24 | `ENABLE_KB_BRANDS=true` in place of `_dry` | 3 |
| E1 | tests/test_s81_kb_schema.py R27 | `KB_TABLES == KB_TABLE_NAMES + ("kb_brands",)` | 10 |
No other existing pin moved (R02 unedited: the OFF line names both flags).

### Gates (GREEN)
- G1 py_compile OK on the edited .py files + the RED file; ruff --select E9,F63,F7,F82 --no-cache: All checks passed (full ruff on the three app/scripts files also clean); the hook passed on commit.
- G2 new files ASCII + LF (0 bytes > 127); edited files keep CRLF; `git diff --stat` hunks only (CLAUDE.md 2+/2-); added-line sweep (@gmail, +973, 8-digit runs, key shapes) empty.
- G3 `sqlfluff lint --config .sqlfluff` 052 + rollback: All Finished!, rc 0 (and the three APPLY_052 files).
- G4 RED file 129/129 flags unset `[pyt] tag=s16b-green-red-off elapsed=6s status=OK rc=0`; 129/129 with ENABLE_KB_BRANDS=apply KB_BRANDS_MAX=1 ENABLE_KB_SEED=apply for that one call `[pyt] tag=s16b-green-red-on elapsed=10s status=OK rc=0`; netguard 0.
- G5 E-row files 673 passed / 5 failed = exactly the environmental G2 R27 CRLF nodes (as at base; R27 re-checked on the LF bytes: clean) `[pyt] tag=s16b-green-g5 elapsed=14s status=FAIL rc=1`.
- G6 seven migration readers 168 passed `[pyt] tag=s16b-green-g6 elapsed=25s status=OK rc=0`.
- G7 comm set 303 files (the RED 302, sha c5734182..., + the RED file; HEAD set sha fcceee0b...) in 13 chunks + test_secret_scan_static.py alone: 19,140 passed, 6 failed, 2 errors = the 8 base-record nodes; `comm -13` vs the STORED base record (LC-6, reused, not re-run) EMPTY, `comm -23` EMPTY.
- G8 33/33 mutants KILLED on AssertionError (M01-M30 + M31 / M32 / M33), byte copies restored and sha-verified, the lock removed.
- G9 throwaway PostgreSQL 18.1 (port 55432): 045 applied; PRECHECK all true; 052 applied; POSTCHECK grid exactly as stated (check_count 6, host_index_unique f, every anon / authenticated privilege f, sr_truncate f); re-apply clean; 16 negative inserts refused (15 x 23514, NULL label 23502); the trigger moved updated_at; anon / authenticated SELECT and UPDATE refused; ON CONFLICT DO NOTHING RETURNING: 1 row then 0; the 045 rollback first failed 2BP01 and changed nothing; rollback 052 then 045 clean; cluster stopped, data directory left.
- G10 CLAUDE.md readers 481 passed `[pyt] tag=s16b-green-g10 elapsed=20s status=OK rc=0`.
- Client fences: the fourteen by path through the junction (node v24.11.1, jest 29.7.0): 13/14 suites, 236 passed / 4 failed = exactly the four config/nativeBundle.w37 drift nodes. The hook test files NOT run (no .githooks change); the FULL jest NOT run (LC-7: the last round).

The mutation table, the comm logs and the G9 transcript are separate files (filed by the orchestrator): `S81-16b_green/mutants/results.json`, `S81-16b_green/comm_progress.txt`, `S81-16b_green/g9/g9_transcript.txt`, the gate logs under `S81-16b_green/logs/`.

### Stated limits (R-S16B-16)
- L1 the Wikidata ids (P1056, Q131746, P856, P31, Q5) and the `rdfs:` prefix are offline-unverified; the DRY counts are the check.
- L2 labels are `en` (else `mul`) and exact `ar`; an item with neither `en` nor `mul` is skipped (`no_label_en`); regional codes are not matched.
- L3 the human exclusion also removes human items' official sites from the G2 DRY host list (deliberate).
- L4 a brand that loses its en label keeps its last stored row; a brand gone from Wikidata is never deleted.
- L5 rollback order: 052 before 045 (the 045 rollback fails 2BP01 while kb_brands exists and changes nothing; measured in G9).
- L6 the merge re-deploys the three G2 jobs (kb_seed_common is in their watch patterns); harmless while their flags are unset (owner step 0).
- L7 the PostgREST insert-ignore return shape (inserted rows only) is unmeasured offline; the SQL half (`ON CONFLICT DO NOTHING RETURNING` returns 0 rows on the second run) is measured in G9; the canary (step 6) reads the rest.
- L8 the SPARQL answer is truncated at 2,000 (brand, site) pairs; the numeric ORDER BY makes the truncation deterministic by qid, not complete (`sparql_limit_hit`).
- L9 G2 R27 stays environmentally red on a Windows CRLF checkout (5 nodes, as at base); green on the LF blobs in CI.
- L10 one update per existing row per run (up to `KB_BRANDS_MAX` round trips), even when nothing changed.
- L11 `official_host` NULL means no usable official site; the reasons are counted, not stored.
- L12 a brand with several official sites keeps the smallest host string, not a preferred apex.
- L13 `brand_updates` counts the update calls made (attempts that returned), not rows changed.

### Owner steps (names only; one dated ledger line each; R-S16B-11)
0. Before the merge: `ENABLE_KB_SEED` unset or `false` on kbseed (and `ENABLE_FEED_WALKER`, `ENABLE_PDP_DISCOVERY` unset on their services): one names-only count line (L6).
1. Apply 045, then 047 (owner item 29), if not yet applied.
2. Apply 052 with `APPLY_052_1_PRECHECK.sql` (grid as stated), `APPLY_052_2_ONE_PASTE.sql`, `APPLY_052_3_POSTCHECK.sql` (grid as stated, check_count 6).
3. The DRY run as a ONE-OFF command on kbseed carrying `ENABLE_KB_BRANDS=true` in its own environment, never a service variable (a variable change redeploys kbseed, whose startCommand is the paid batch seeder): `python -m scripts.seed_kb_brands_wikidata --report <file>`; record the totals line.
4. If the counts look right (bindings > 0, with_label_en near the distinct brands): the same one-off command with `ENABLE_KB_BRANDS=apply` (optionally `KB_BRANDS_MAX`), ONCE; record `kb_brands_sent`, `brand_updates`, `write_failed`.
5. Nothing to unset (no service variable was set).
6. Canary (read-only SQL): `SELECT count(*), count(label_ar), count(official_host) FROM public.kb_brands`; after a second apply run, `count(*) FILTER (WHERE updated_at > created_at)` > 0 confirms the update path (L7).

Wikidata structured data: CC0. Source host: query.wikidata.org, one GET per run.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
