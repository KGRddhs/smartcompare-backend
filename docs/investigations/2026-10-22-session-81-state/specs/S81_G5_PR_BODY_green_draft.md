# S81-G5 LEARN-SEARCH: D22 NIGHTLY-LEARNING (dark, scripts only)

Base `ec747b49` (origin/main after #386). HEAD `53b7b66e` on `feature/s81-g5-learn-search`. The fifth SAFE group under LC-9 (one unit, D22; RULINGS_S81_G5 R-G5-1 SAFE: one adversary). No app/, migrations/, SmartCompareApp/, data/, requirements*, .github/, .githooks/ or app/legal/ file. Production is byte-identical: the flag is a new name (unset), no Railway service runs the script until the owner creates it, nothing imports it, and the deleted rotation cron had no importer, an unset fail-closed flag and no service.

## D22 NIGHTLY-LEARNING

**Flag and mode.** `ENABLE_LEARNING_JOB` is read per call as the FIRST statement of `main` through `kb_seed_common.run_mode`: unset / blank / garbage / false / 0 / no / off / dry = OFF (one INFO line `[LEARNING] mode=off ENABLE_LEARNING_JOB not set; skipping run`, exit 0, before argparse, before any client, before `kb_leaf`, no file); true / 1 / yes / on = DRY (reads + report, zero writes); the exact word `apply` = WRITE; `--dry-run` downgrades apply. Knobs through `int_knob` per call: `LEARNING_WINDOW_DAYS` (7, 1..30), `LEARNING_MIN_CASES` (3, 1..100), `LEARNING_MIN_DEVICES` (2, 1..10), `LEARNING_MAX_ROWS` (5000 per table, 100..50000), `LEARNING_EXEMPLARS_PER_CATEGORY` (5, 3..5); unset / garbage / inf / nan / negative / 0 fall back to the default.

**Reads (DB only; no LLM, no Serper, no Redis, no network).** The window `[previous UTC midnight - window_days, previous UTC midnight)` (`--day` moves both edges) of comparison_feedback, verdict_critiques, user_events (`in_` on the six ABANDON / CONFIRM event types), search_logs, kb_gaps (on `last_seen`) and kb_feedback, each `.gte/.lt` + `.order("id")` + `.range` pages of 500 until a short page or the cap (status `capped`, `learning.capped.<table>`); then comparisons by the sorted de-duplicated comparison ids (PostgREST JSON paths only: the category at `full_response->>category_used`, the per-product price `source_method` / amount / currency, the BC `comparison` verdict fields; never `query`, never the bare `full_response`) and kb_specs by the product ids of the kb spec_wrong cases. The SELECT strings are the spec 2.2 constants exactly (no query, change_suggestion, mattered_most, event_data, error_message, products_found). Module top imports stdlib + `scripts.kb_seed_common` only; the leaf comes through `common.kb_leaf()`.

**Buckets.** identity_wrong (kb_feedback field `identity` + wrong, R-G5-5; no writer yet); price_wrong (comparison_feedback `price_correct` wrong, source = the shared `source_method` / `mixed` / `unknown`; kb_feedback `price` wrong, source `kb`); spec_missing (open / queued / needs_operator kb_gaps whose field does not start `pdp_`, source `kb_gap`, demand summed, no actor); spec_wrong (`specs_correct` wrong, source `specs`; kb_feedback other fields, source `kb`); verdict_unsupported (verdict_critiques `missing_citation_score` or `bias_score` an int below 7, actor the joined comparisons.user_id); verdict_wrong (`winner_correct` wrong). search_logs and user_events feed only the context metrics.

**The systematic rule.** Cluster = (category, source, field, bucket); `cases` = distinct case keys; `actors` = the distinct actors over EVERY report that maps to the cluster's cases (GC-2: one comparison reported wrong by two users = 1 case, 2 actors); systematic = cases >= LEARNING_MIN_CASES and actors >= LEARNING_MIN_DEVICES. user_id is a PROXY for a device outside kb_feedback (device_key there); anonymous rows add a case and no actor. Every systematic cluster gets one proposal `{bucket, category, source, field, cases, distinct_actors, judge_state: "pending", grounding, proposed_action}` from the closed action map (price estimated -> drop_source_for_field; price on another source_method -> recheck_source; price mixed / unknown / kb -> needs_operator; spec_wrong with a cited kb_specs grounding -> recheck_source, else needs_operator; identity_wrong / spec_missing -> needs_operator; the verdict buckets -> no_action). NOTHING is applied: no write to kb_specs / kb_offers / kb_products / kb_gaps / data/.

**De-identification.** A structural screen (uuid / 64-hex / at sign / the Bahrain dialling prefix / 8-digit shapes, unanchored, so a shape inside a longer token counts) on every string of every exemplar candidate, eval candidate and grounding entry; a failing one is dropped and counted (`learning.dropped.deidentify`). The screen runs BEFORE the per-category cut (GC-3: a dropped candidate frees its slot). An eval candidate is kept when only its comparison's winner_reason is unclean (GC-4: the eval shape carries no winner_reason). Only product names, field / category / source names, verdict text (report only) and counts reach the outputs; user ids, device keys, request ids, comparison ids, row ids, query text, comments and event data never do.

**Outputs.** `--report` JSON through `common.write_report` (ASCII, LF, sorted keys: schema `learning-report/1`, day, mode, window_days, window_start, window_end, thresholds, judge_state, actor_basis, tables, buckets, clusters, proposals, exemplar_candidates (per category: version `<day>.<16 base32 chars of sha256>`, count, exemplars), eval_candidates, context, dropped_deidentify, metrics); `--report-md` (metric / cluster / proposal tables + exemplar names, no verdict text); the log (the header first, one `table=` line per READ_TABLES entry, cluster / proposal / exemplar / eval lines, one `metric=` line per metric, the totals line last; counts and names only). APPLY: exactly ONE `client.table("kb_coverage_daily").upsert(rows, on_conflict="day,metric").execute()`, every row from `kb.build_coverage_row(day=, metric=, value=, n=)` (D17's call shape). The closed list: 16 always-emitted (`learning.cases.<bucket>` x 6, `learning.clusters.total`, `.clusters.systematic`, `.proposals`, `.exemplar_candidates`, `.eval_candidates`, `.actors`, `.events.abandon`, `.events.confirm`, `.searches.failed`, `.dropped.deidentify`) + the conditional `learning.skipped.<table>` / `learning.capped.<table>`.

**Failure table.** A table whose error `.code` is 42P01 / PGRST205 (a kb_* table before 045) = status `absent`, one WARNING with the type name, a counted skip; any other one-table error = status `error`, isolated; a client construction failure or None = one ERROR line with the type name only, exit 1 (R-G5-2); a bad `--day` = WARNING, exit 0, no client; an unwritable report = WARNING, the log stands; a raising upsert = WARNING, exit 0.

**RED rows -> the flag -> the flip preconditions.** D22 -> tests/test_s81_d22_nightly_learning.py (R1-R29 + P1-P7, 50 nodes) + tests/test_s81_g5_gate_rows.py (G5-GR1 / G5-GR2) -> `ENABLE_LEARNING_JOB` -> 045 applied (the kb_* reads and the coverage upsert), the `learning` service created, ONE DRY run read by the owner (owner steps below).

## Deliberate pin changes (GC-6)

| E | file | change | reason |
|---|---|---|---|
| E1 | tests/test_s81_kb_schema.py | P02_ALLOWED + the two rows `("scripts/cron_learning.py", 'KB_COVERAGE_TABLE = "kb_coverage_daily"')` / `('KB_FEEDBACK_TABLE = "kb_feedback"')` with the comment `#: S81-G5 E1: the D22 job's two relation constants.`; P01 unchanged | the G2 / G4 row form for the job's two relation constants |
| E2 | scripts/cron_few_shot_rotation.py | DELETED | R-G5-8 option (i): the only code path writing user-derived exemplars (with a comparison uuid) under data/; no importer; flag unset; never registered (the G1 judgeme precedent) |
| E3 | tests/test_cron_few_shot_rotation.py | DELETED | the deleted script's test file (12 nodes, green at base, so `comm -23` stays empty) |
| E4 | tests/test_exemplar_contamination.py | RULED OUT (R-G5-4): byte-identical | R26 scans import statements only |

No other pin moved.

## Counts

- RED file: 50 nodes (43 RED at base on AssertionError only + 7 PIN), 50 / 50 at HEAD in three runner calls (flag unset; `ENABLE_LEARNING_JOB=true`; `=apply`, each exported in the runner environment only):
  - `[pyt] tag=g5green-red-off start=2026-11-05 04:33:09 end=2026-11-05 04:33:23 elapsed=15s bound=600s status=OK rc=0`
  - `[pyt] tag=g5green-red-true start=2026-11-05 04:33:32 end=2026-11-05 04:33:46 elapsed=14s bound=600s status=OK rc=0`
  - `[pyt] tag=g5green-red-apply start=2026-11-05 04:33:49 end=2026-11-05 04:34:01 elapsed=12s bound=600s status=OK rc=0`
  - each 50 passed; `[hermeticity] sentinel checked 50 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`
- 15 mutants M1-M15 killed at the RED gate (specs/S81_G5_RED_REPORT.md section 4); the adversary re-runs at least ten on the GREEN bytes.
- Two GREEN gate rows: `[pyt] tag=g5green-gr start=2026-11-05 04:34:51 end=2026-11-05 04:34:54 elapsed=3s bound=600s status=OK rc=0` (2 passed); each proven RED by its inverse edit on a byte copy of scripts/cron_learning.py (restored, sha256 verified): GR1-inv (an actor recorded on a case's first report only) fails G5-GR1 (actors 1 != 2); GR2-inv (cut first, screen after) fails G5-GR2 (4 != 5). Table: specs/S81_G5_GREEN_MUTATIONS.md.
- Pins (E1 + the scripts-scanning pins the RED ran): `[pyt] tag=g5green-pins start=2026-11-05 04:35:43 end=2026-11-05 04:36:17 elapsed=34s bound=1200s status=FAIL rc=1` = 1 failed / 1052 passed; the 1 = the known d17 r9 CRLF baseline.
- CI-order set (spec 12.1): `[pyt] tag=g5green-ciorder start=2026-11-05 04:38:03 end=2026-11-05 04:39:17 elapsed=74s bound=1200s status=FAIL rc=1` = 1 failed (d17 r9) / 835 passed (base: 44 failed = the 43 RED nodes + d17 r9 / 792 passed).
- Comm set: the RED's 46 files minus tests/test_cron_few_shot_rotation.py plus the RED file and the gate-rows file = 47 (no other importer newly referenced), at HEAD in 2 chunks + the secret scan ALONE, vs the STORED base record `base_records/ec747b49.../c636b9d5...` (REUSED, LC-6):
  - `[pyt] tag=g5green-comm-head-00 start=2026-11-05 04:39:46 end=2026-11-05 04:41:25 elapsed=99s bound=1200s status=FAIL rc=1` (2 failed, 1096 passed, 1 skipped)
  - `[pyt] tag=g5green-comm-head-01 start=2026-11-05 04:41:34 end=2026-11-05 04:43:13 elapsed=99s bound=1200s status=FAIL rc=1` (6 failed, 2089 passed)
  - `[pyt] tag=g5green-comm-head-secretscan start=2026-11-05 04:43:15 end=2026-11-05 04:43:34 elapsed=19s bound=600s status=OK rc=0` (31 passed)
  - HEAD failed = the 8 fresh-checkout CRLF hygiene nodes, identical to base (GC-5); `comm -13` EMPTY; `comm -23` EMPTY. The netguard lines name only the known passing pins (test_hermeticity_pins' probes; two s04 rows on the neutralized sentinel).
- The fourteen backend-scanning client jest fences by path through the junction (node v24.11.1, jest 29.7.0): `[jest] tag=g5green-fences start=2026-11-05 04:44:22 end=2026-11-05 04:44:45 rc=1` = 13 / 14 suites, 4 failed / 236 passed: exactly the four config/nativeBundle.w37 drift nodes (d5, k2, k4, k5).
- Not run: the corpus gate (no price_service edit); the pre-commit hook test files (no .githooks change); the FULL jest suite (LC-7: the final round).
- Gate logs: specs/S81_G5_GREEN_GATES.md.

## Stated limits (spec L1-L12, R-G5-9 as L13, GC-10)

- L1 The judge is absent (compare_judgements = S81-22): every proposal is judge_state pending; D22b adds the join.
- L2 `user_id` is a PROXY for a device on comparison_feedback / user_events / search_logs / verdict_critiques; anonymous rows add cases, no actor.
- L3 identity_wrong has only the kb_feedback `identity` input, which nothing writes yet.
- L4 The report file is ephemeral on Railway; the log is the durable copy (names and counts, never the exemplar verdict text).
- L5 kb_gaps / kb_feedback / kb_specs / kb_coverage_daily exist only after 045: before it the kb reads are counted skips and APPLY's upsert fails with one WARNING (rows logged).
- L6 The specs source axis is the constant `specs`; price clusters use source_method (no host), so a host-level proposal needs the operator.
- L7 kb_gaps carries no actor: spec_missing clusters never become systematic; they carry their demand.
- L8 No $0 DB-only replay exists (shadow_experiments' replay calls OpenAI); the offline proof is D22b.
- L9 The window edges are whole UTC days ending at the previous midnight; a capped table is counted and its tail unread (ordered by id: deterministic, not the newest rows).
- L10 A conditional `learning.skipped.*` / `learning.capped.*` row of an earlier same-day run is not removed by a later same-day run that does not hit the condition.
- L11 Category comes from `full_response.category_used` (no column): a row whose JSON lacks it is `unknown`.
- L12 The legal fill-in flag list still names `ENABLE_FEWSHOT_ROTATION` (recorded off); the U8 machinery is not touched (FOCUS).
- L13 (R-G5-9) No client sends the per-axis correctness fields today, so price_wrong / spec_wrong / verdict_wrong read 0 in production until CL3 / SF1; the live value at the flip = verdict_unsupported (only while ENABLE_SELF_CRITIQUE has run), spec_missing (kb_gaps demand after the G3 flip) and the context metrics; the seeded fixture proves the bucket logic. The PostgREST JSON-path selects are unprobed: the owner's ONE DRY run is their proof (R-G5-7).
- GC-10: the two-actor rule (GC-2) and the screen-before-cut order (GC-3) are pinned by G5-GR1 / G5-GR2.

## Owner steps (names only; a dated ledger line per step)

1. Apply 045 then 047 (owner item 29) then 052.
2. Create the `learning` Railway service from `railway.learning.json` with `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`, and a nightly cron schedule at a DIFFERENT hour from `kb-coverage`.
3. Set `ENABLE_LEARNING_JOB=true` and make ONE DRY run; read the report in the run log. Canary items: FIRST, `learning.cases.*` with category `unknown` or source `unknown` dominating = a JSON path returned null: report it before the schedule is set; then `learning.cases.*` per bucket, `learning.clusters.systematic`, the proposals, the exemplar candidates, the eval candidates, the skipped tables.
4. Then `apply`. Eval cases are ratified by hand into data/validation_gold_truth.json only through a reviewed PR. Rollback: unset the variable.

## [NATIVE READ]

EMPTY (no client copy, no Arabic string).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
