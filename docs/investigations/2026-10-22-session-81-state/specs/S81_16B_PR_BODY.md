## S81-16b KB-BRANDS: migration 052 `kb_brands` (WRITTEN, NOT APPLIED) + the Wikidata brand import under `ENABLE_KB_BRANDS`

**MERGING THIS CHANGES NOTHING IN PRODUCTION**: 052 is written, not applied; no request-path code reads or writes `kb_brands`; the brand script runs only as a one-off command with `ENABLE_KB_BRANDS` set. **L6 (stated beside it):** the merge edits `scripts/kb_seed_common.py`, which all three G2 `railway.*.json` watch, so it re-deploys (= re-runs) the kbseed, feedwalker and pdpdiscovery jobs in whatever mode their flags hold: confirm `ENABLE_KB_SEED`, `ENABLE_FEED_WALKER`, `ENABLE_PDP_DISCOVERY` unset (or `false`) on their services BEFORE the merge (owner step 0).

Base `e1491c97` (origin/main after #385 S81-G4 KB-SERVE), HEAD `afaaa4af6e8daa466c7cdd9329bf29c57a9d4ac8` (branch `feature/s81-s16b-kb-brands`, ONE commit: the GREEN commit `28eec42b` replayed onto e1491c97 with no conflict and no edit; 9 files). FOCUS unit (a migration): GREEN, then two adversaries (correctness; schema-and-data), both SOUND; no fix round. The frozen RED file `tests/test_s81_s16b_kb_brands.py` blob sha256 `cd67db3b...` (unchanged; no pin rows this round); 052 blob `fef8ec19...`, rollback `766cff1c...` (unchanged since GREEN).

### What it does
- `migrations/052_kb_brands.sql` + `migrations/rollback/052_kb_brands.sql`: ONE table `public.kb_brands (qid PK, label_en, label_ar, official_host, source, created_at, updated_at)`; the qid CHECK `^Q[1-9][0-9]{0,11}$`; both labels 1..128 and `= btrim(...)`; the 045 host belts on `official_host` (host regex, deny-label `!~`, top-label constraint); `source` wikidata | operator; a partial NON-unique index on `official_host`; the 045 trigger function reused (`BEFORE UPDATE`); a DO guard refusing to run without 045; RLS on with no policy, `REVOKE ALL ... FROM PUBLIC, anon, authenticated, service_role` then `GRANT SELECT, INSERT, UPDATE, DELETE ... TO service_role` (the 045 pattern, the 037 both-readings rule). Rollback = `DROP TABLE IF EXISTS public.kb_brands` (the function is 045's and is kept); roll 052 back BEFORE any rollback of 045.
- `app/services/kb_service.py` (the leaf; kb_ingest and merchant_registry import it lazily and no request-path code reads the new names): `kb_brands` LAST in `KB_TABLES` / `KB_COLUMNS` (hence `KB_BUILDER_KEYS`), `KB_QID_REGEX`, `KB_BRAND_SOURCES`, `KB_BRAND_UPSERT_SET`, and the pure `build_brand_row` mirroring every 052 CHECK (plus the deny RULE `kb_source_allowed` and a Python `strip()` refusal, stricter than btrim); None on any refusal, never raises. `kb_ingest` keys its writes by its own table constants and `KB_OFFER_UPSERT_SET` / `KB_OFFER_OBSERVATION_KEY` through kb_leaf, so the new census entry changes nothing for it (R-S16B-13).
- `scripts/kb_seed_common.py`: `KB_BRANDS_TABLE` + `KbWriter.brands` (insert-ignore on qid; one update of `KB_BRAND_UPSERT_SET` filtered on `qid` AND `source = 'wikidata'` per row the insert did not return; no delete, no select). The existing writer methods are byte-unchanged.
- `scripts/seed_kb_brands_wikidata.py`: its OWN flag `ENABLE_KB_BRANDS` (unset / blank / garbage / false / 0 / no / off / dry -> OFF; true / 1 / yes / on -> DRY; apply -> WRITE; `--dry-run` downgrades) read per call as the FIRST statement of `main`; OFF = one INFO line naming both flags, rc 0, before argv / client / any I/O, whatever `ENABLE_KB_SEED` holds. Knob `KB_BRANDS_MAX` (300, 1..5000). The SPARQL gains exact-language OPTIONAL labels (en, mul, ar), `FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 . }` and `ORDER BY xsd:integer(STRAFTER(STR(?brand), "/entity/Q")) ?site LIMIT 2000`. DRY: robots + ONE SPARQL GET + the unchanged host derivation + the brand rows and counts to `--report`, no write. APPLY: the same + `KbWriter.brands` (a failure = one WARNING with the type name, `write_failed=1`, the writer counters added in a `finally`). `derive_hosts`, `_site_host`, `sparql_url`, `_parse_args` byte-unchanged. `ENABLE_KB_SEED` never runs this script.
- Source: Wikidata (CC0 public-domain dedication), `query.wikidata.org` (already the G2 script's host), one GET per run. No new dependency, no new external host, no new credential name; no personal data (humans excluded, no user column, the 043 fence sees 052 with no gap).
- `CLAUDE.md`: the S81-G2 block edited IN PLACE (spec 8.1; three edits, 052 in the sentences); the G4 block from main untouched.

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
| E1 | tests/test_s81_kb_schema.py R27 | `KB_TABLES == KB_TABLE_NAMES + ("kb_brands",)` (one line; G4's P01 / P02 hunks at 332-361 sit beside it, no overlap) | 10 |
No other existing pin moved (R02 unedited: the OFF line names both flags).

### Gates (this round, on the rebased bytes)
- Replay: `git merge-tree --write-tree` origin/main HEAD = the orchestrator's clean tree `fdfa6e62...`; `git rebase origin/main` replayed 1/1 with no conflict; the per-file patch of every one of the 9 files against its base is identical to GREEN's (`git diff 28eec42b HEAD` empty for the 7 files main did not touch; for CLAUDE.md and tests/test_s81_kb_schema.py the +/- lines of `git diff e1491c97 HEAD` equal those of `git diff 0b19de5b 28eec42b`); `git diff --check` clean; no conflict markers; no whole-file diff.
- ruff --select E9,F63,F7,F82 --no-cache: All checks passed; py_compile OK (the three edited .py files + the two edited test files + the RED file); `sqlfluff lint --config .sqlfluff` 052 + rollback: All Finished!, rc 0; neither file contains '051'.
- RED file 129 / 129 flags unset `[pyt] tag=s16bF-red-off elapsed=10s status=OK rc=0`; 129 / 129 with ENABLE_KB_BRANDS=apply KB_BRANDS_MAX=1 ENABLE_KB_SEED=apply for that one call `[pyt] tag=s16bF-red-on elapsed=6s status=OK rc=0`; netguard 0.
- G5 (kb_schema + s16_kb_seed + g2_gate_rows): 673 passed / 5 failed = exactly the environmental G2 R27 CRLF nodes (the G4 P01 / P02 rows green beside E1) `[pyt] tag=s16bF-g5 elapsed=13s status=FAIL rc=1`.
- G6 seven migration readers 168 passed `[pyt] tag=s16bF-g6 elapsed=17s status=OK rc=0`. G10 CLAUDE.md readers 481 passed `[pyt] tag=s16bF-g10 elapsed=17s status=OK rc=0`.
- The R8 pair (test_sentry_channels_u8d_unit + test_sentry_channels_u8d) 273 passed `[pyt] tag=s16bF-r8 elapsed=19s status=OK rc=0`; test_paid_route_metering 21 passed without and with ENABLE_KB_BRANDS=apply exported `[pyt] tag=s16bF-prm-off elapsed=4s status=OK rc=0` / `[pyt] tag=s16bF-prm-on elapsed=4s status=OK rc=0`.
- Comm set (RB-16B-2): 308 files at HEAD = the RED's 302 + the RED file + 5 G4 files joined by the union rule at e1491c97 (tests/test_s81_d16_operator_ingest.py ref kb_service + app-source scan; tests/test_s81_d17_coverage.py ref kb_service / kb_seed_common / scripts; tests/test_s81_g4_gate_rows.py ref scripts; tests/test_s81_s18_kb_first_serve.py ref kb_service / kb_ingest; tests/test_s81_s19_gap_queue.py ref kb_service / kb_seed_common / kb_ingest / scripts), 0 dropped. Base record at e1491c97 (307 files, the RED file absent at base; set sha256 4b65c5db...): 154 members REUSED per file from the stored 0b19de5b record, 153 RUN at e1491c97 in a junction-free detached scratch worktree (126 reference a #385 module or CLAUDE.md, 22 of them CLAUDE.md only; 20 glob walkers; 5 new G4 files; 1 changed at #385; the secret scan) in 7 chunks + tests/test_secret_scan_static.py alone; 11 baseline nodes (the two tiktoken test_prompt_truth nodes, s10 r06, the five s16 r27 CRLF nodes, and the three G4 CRLF hygiene nodes d16 r10 / d17 r9 / s19 r15). HEAD: 13 chunks of <= 25 + the secret scan alone, every chunk inside its bound, 19,256 passed, 9 failed, 2 errors = the same 11 nodes; comm -13 EMPTY, comm -23 EMPTY.
- Client fences: the fourteen backend-scanning suites by path through the junction (node v24.11.1, jest 29.7.0): 13 / 14 suites, 236 passed / 4 failed = exactly the four config/nativeBundle.w37 drift nodes (d5, k2, k4, k5) `[jest] tag=s16bfinal-fences rc=1`.
- Full jest suite once (LC-7): 385 suites passed, 1 failed, 3 skipped; 3,794 passed, 4 failed (the same four nativeBundle.w37 drift nodes), 13 skipped, 13 todo; 42 snapshots passed, no .snap written, no -u `[jest] tag=s16bfinal-full rc=1`.
- G9 (throwaway PostgreSQL 18.1) NOT re-run: the 052 / rollback bytes are unchanged since GREEN measured them and the schema lens re-measured them on its own cluster. The corpus gate NOT run (no price_service change). The hook test files `tests/test_precommit_hook*.py` NOT run (the unit touches no .githooks file; RB-16B-3 (i)).

### Adversaries (both SOUND, no fix round)
- Correctness lens (`specs/S81_16B_ADV1_correctness.md`): SOUND, 7 minors (m1-m7), 20 mutants killed.
- Schema-and-data lens (`specs/S81_16B_ADV2_schemaanddata.md`): SOUND, 6 minors (m1-m6), 15 mutants + the 10-case K03 matrix measured on PostgreSQL 18.1.
- The RED / GREEN mutation table: 33 / 33 spec mutants killed. All thirteen minors are stated limits or wording below (LC-4, RB-16B-4).

The mutation tables, the comm logs and the G9 transcript are separate files (filed by the orchestrator): `S81-16b_green/mutants/results.json`, `S81-16b_green/g9/g9_transcript.txt`, `S81-16b_final/REBASE_REPORT.md` (every [pyt] / [jest] line of this round), the e1491c97 base record `harness/base_records/e1491c97.../4b65c5db...`.

### Stated limits (R-S16B-16 as amended by RB-16B-4)
- L1 the Wikidata ids (P1056, Q131746, P856, P31, Q5) and the `rdfs:` prefix are offline-unverified; the DRY counts are the check.
- L2 labels are `en` (else `mul`) and exact `ar`; an item with neither `en` nor `mul` is skipped (`no_label_en`); regional codes are not matched.
- L3 the human exclusion also removes human items' official sites from the G2 DRY host list (deliberate).
- L4 a brand that loses its en label keeps its last stored row; a brand gone from Wikidata is never deleted; a Wikidata item merge leaves the old qid row beside the surviving qid until an operator removes one (schema m2).
- L5 rollback order: 052 before 045 (the 045 rollback fails 2BP01 while kb_brands exists and changes nothing; measured in G9).
- L6 the merge re-deploys the three G2 jobs (kb_seed_common is in their watch patterns); harmless while their flags are unset (owner step 0).
- L7 the PostgREST insert-ignore return shape (inserted rows only) is unmeasured offline; the SQL half (`ON CONFLICT DO NOTHING RETURNING` returns 0 rows on the second run) is measured in G9; the canary (step 6) reads the rest.
- L8 the SPARQL answer is truncated at 2,000 (brand, site) pairs; the numeric ORDER BY makes the truncation deterministic by qid, not complete (`sparql_limit_hit`).
- L9 G2 R27 stays environmentally red on a Windows CRLF checkout (5 nodes, as at base; the G4 hygiene rows d16 r10 / d17 r9 / s19 r15 are the same class on this box); green on the LF blobs in CI.
- L10 one update per existing row per run (up to `KB_BRANDS_MAX` round trips), even when nothing changed.
- L11 `official_host` NULL means no usable official site; the reasons are counted, not stored.
- L12 a brand with several official sites keeps the smallest host string, not a preferred apex.
- L13 `brand_updates` counts the update calls made (attempts that returned), not rows changed.
- L14 the 052 header's 'never a person's name' means 'never the label of a human item' (P31 Q5 excluded); a brand may carry its founder's trade name (schema m1).
- L15 a refused en label never falls back to mul: correct by probe but unpinned (correctness m1).
- L16 the in-Python `source != 'wikidata'` skip is unpinned; the `.eq('source', 'wikidata')` filter is the pinned guard (correctness m2).
- L17 `brand_rows` on an empty SPARQL answer is unpinned (correctness m3).
- L18 a whitespace-only en label is stripped to None before the builder and falls back to mul, counting `label_en_from_mul` (correctness m4; never seen with real Wikidata labels).
- L19 interior control characters in a label pass the CHECK and the builder; they are escaped on render (schema m4).
- L20 the R02 `seed_kb_brands_wikidata` parametrisation is vacuous for the brand flag; S02's 24 nodes are the OFF row (correctness m7).
- L21 POSTCHECK counts the six CHECK constraints without comparing their text (PRECHECK's `kb_brands_absent` guards a stale table) and lists no REFERENCES / TRIGGER / MAINTAIN columns (measured false; schema m5 / m6).

### Owner steps (names only; one dated ledger line each; R-S16B-11)
0. Before the merge: `ENABLE_KB_SEED` unset or `false` on kbseed (and `ENABLE_FEED_WALKER`, `ENABLE_PDP_DISCOVERY` unset on their services): one names-only count line (L6).
1. Apply 045, then 047 (owner item 29), if not yet applied.
2. Then apply 052 with the APPLY_052 files filed under the session-81 state folder's specs/: `APPLY_052_1_PRECHECK.sql` (grid as stated), `APPLY_052_2_ONE_PASTE.sql`, `APPLY_052_3_POSTCHECK.sql` (grid as stated, check_count 6).
3. The DRY run as a ONE-OFF command on kbseed carrying `ENABLE_KB_BRANDS=true` in its own environment, never a service variable (a variable change redeploys kbseed, whose startCommand is the paid batch seeder): `python -m scripts.seed_kb_brands_wikidata --report <file>`; record the totals line.
4. If the counts look right (bindings > 0, with_label_en near the distinct brands): ONE apply run, the same one-off command carrying `ENABLE_KB_BRANDS=apply` (optionally `KB_BRANDS_MAX`), never a service variable; record `kb_brands_sent`, `brand_updates`, `write_failed`.
5. Nothing to unset (no service variable was set).
6. Canary (read-only SQL): `SELECT count(*), count(label_ar), count(official_host) FROM public.kb_brands`; after a second apply run (its report showing `brand_updates` > 0 and no `write_failed`), `select count(*) from kb_brands where updated_at > '<the second run's start, UTC>'` > 0 confirms the update path (L7; created_at is the database clock, updated_at the host clock, so never compare the two columns).

Wikidata structured data: CC0. Source host: query.wikidata.org, one GET per run.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
