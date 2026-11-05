# S81-G5 LEARN-SEARCH: D22 NIGHTLY-LEARNING (dark, scripts only)

Base `00e4120d` (origin/main after #387 S81-G6 CLIENT-PERF). HEAD `50e3f3a59721bb2e5323708a5f66b0e9d74b12cf` on `feature/s81-g5-learn-search` = two commits: GREEN `d5c86546` (the GREEN `53b7b66e` replayed onto `00e4120d`, no conflict, every G5 blob byte-identical) + the final-round commit `50e3f3a5` (tests + docs only: G5-GR3..GR7 and the CLAUDE.md S81-G5 block amended in place; RULINGS_REBASE_S81_G5 RB-G5-9). The fifth SAFE group under LC-9 (one unit, D22; one adversary). No app/, migrations/, SmartCompareApp/, data/, requirements*, .github/, .githooks/ or app/legal/ file. Production is byte-identical: the flag is a new name (unset), no Railway service runs the script until the owner creates it, nothing imports it, and the deleted rotation cron had no importer, an unset fail-closed flag and no service.

Reports (session-81 state folder, specs/): S81_G5_RED_REPORT.md, GATE_S81_G5.md, RULINGS_S81_G5.md, S81_G5_GREEN_REPORT.md, S81_G5_GREEN_GATES.md, S81_G5_GREEN_MUTATIONS.md, S81_G5_ADV1_correctness.md, RULINGS_REBASE_S81_G5.md and this round's S81_G5_REBASE_REPORT.md.

## D22 NIGHTLY-LEARNING

**Flag and mode.** `ENABLE_LEARNING_JOB` is read per call as the FIRST statement of `main` through `kb_seed_common.run_mode`: unset / blank / garbage / false / 0 / no / off / dry = OFF (one INFO line `[LEARNING] mode=off ENABLE_LEARNING_JOB not set; skipping run`, exit 0, before argparse, before any client, before `kb_leaf`, no file); true / 1 / yes / on = DRY (reads + report, zero writes); the exact word `apply` = WRITE; `--dry-run` downgrades apply. Knobs through `int_knob` per call: `LEARNING_WINDOW_DAYS` (7, 1..30), `LEARNING_MIN_CASES` (3, 1..100), `LEARNING_MIN_DEVICES` (2, 1..10), `LEARNING_MAX_ROWS` (5000 per table, 100..50000), `LEARNING_EXEMPLARS_PER_CATEGORY` (5, 3..5); unset / garbage / inf / nan / negative / 0 fall back to the default.

**Reads (DB only; no LLM, no Serper, no Redis, no network).** The window `[previous UTC midnight - window_days, previous UTC midnight)` (`--day` moves both edges) of comparison_feedback, verdict_critiques, user_events (`in_` on the six ABANDON / CONFIRM event types), search_logs, kb_gaps (on `last_seen`) and kb_feedback, each `.gte/.lt` + `.order("id")` + `.range` pages of 500 until a short page or the cap (status `capped`, `learning.capped.<table>`); then comparisons by the sorted de-duplicated comparison ids (PostgREST JSON paths only: the category at `full_response->>category_used`, the per-product price `source_method` / amount / currency, the BC `comparison` verdict fields; never `query`, never the bare `full_response`) and kb_specs by the product ids of the kb spec_wrong cases. The SELECT strings are the spec 2.2 constants exactly (no query, change_suggestion, mattered_most, event_data, error_message, products_found). Module top imports stdlib + `scripts.kb_seed_common` only; the leaf comes through `common.kb_leaf()`.

**Buckets.** identity_wrong (kb_feedback field `identity` + wrong, R-G5-5; no writer yet); price_wrong (comparison_feedback `price_correct` wrong, source = the shared `source_method` / `mixed` / `unknown`; kb_feedback `price` wrong, source `kb`); spec_missing (open / queued / needs_operator kb_gaps whose field does not start `pdp_`, source `kb_gap`, demand summed, no actor); spec_wrong (`specs_correct` wrong, source `specs`; kb_feedback other fields, source `kb`); verdict_unsupported (verdict_critiques `missing_citation_score` or `bias_score` an int below 7, actor the joined comparisons.user_id); verdict_wrong (`winner_correct` wrong). search_logs and user_events feed only the context metrics.

**The systematic rule.** Cluster = (category, source, field, bucket); `cases` = distinct case keys; `actors` = the distinct actors over EVERY report that maps to the cluster's cases (GC-2: one comparison reported wrong by two users = 1 case, 2 actors); systematic = cases >= LEARNING_MIN_CASES and actors >= LEARNING_MIN_DEVICES. user_id is a PROXY for a device outside kb_feedback (device_key there); anonymous rows add a case and no actor. Every systematic cluster gets one proposal `{bucket, category, source, field, cases, distinct_actors, judge_state: "pending", grounding, proposed_action}` from the closed action map (price estimated -> drop_source_for_field; price on another source_method -> recheck_source; price mixed / unknown / kb -> needs_operator; spec_wrong with a cited kb_specs grounding -> recheck_source, else needs_operator; identity_wrong / spec_missing -> needs_operator; the verdict buckets -> no_action). NOTHING is applied: no write to kb_specs / kb_offers / kb_products / kb_gaps / data/.

**De-identification.** A structural screen (uuid / 64-hex / at sign / the Bahrain dialling prefix / 8-digit shapes, unanchored, so a shape inside a longer token counts) on every string of every exemplar candidate, eval candidate and grounding entry; a failing one is dropped and counted (`learning.dropped.deidentify`). The screen runs BEFORE the per-category cut (GC-3: a dropped candidate frees its slot). An eval candidate is kept when only its comparison's winner_reason is unclean (GC-4: the eval shape carries no winner_reason). The outputs carry product names, field / category / source names, the verdict text fields (report only), counts and the grounding entries' kb product_id + source_url (all screened; spec 2.5), plus version strings and exception type names; never a user id, device key, query text, free-text comment, compare_request_id, comparison id, row id or event data (RB-G5-6). An unclean kb_feedback field name maps to the field `other` (it never reaches a cluster, a grounding or an output; G5-GR6).

**Outputs.** `--report` JSON through `common.write_report` (ASCII, LF, sorted keys: schema `learning-report/1`, day, mode, window_days, window_start, window_end, thresholds, judge_state, actor_basis, tables, buckets, clusters, proposals, exemplar_candidates (per category: version `<day>.<16 base32 chars of sha256>`, count, exemplars), eval_candidates, context, dropped_deidentify, metrics); `--report-md` (metric / cluster / proposal tables + exemplar names, no verdict text); the log (the header first, one `table=` line per READ_TABLES entry, cluster / proposal / exemplar / eval lines, one `metric=` line per metric, the totals line last; counts and names only). APPLY: exactly ONE `client.table("kb_coverage_daily").upsert(rows, on_conflict="day,metric").execute()`, every row from `kb.build_coverage_row(day=, metric=, value=, n=)` (D17's call shape). The closed list: 16 always-emitted (`learning.cases.<bucket>` x 6, `learning.clusters.total`, `.clusters.systematic`, `.proposals`, `.exemplar_candidates`, `.eval_candidates`, `.actors`, `.events.abandon`, `.events.confirm`, `.searches.failed`, `.dropped.deidentify`) + the conditional `learning.skipped.<table>` / `learning.capped.<table>`.

**Failure table.** A table whose error `.code` is 42P01 / PGRST205 (a kb_* table before 045) = status `absent`, one WARNING with the type name, a counted skip; any other one-table error = status `error`, isolated; a client construction failure or None = one ERROR line with the type name only, exit 1 (R-G5-2); a bad `--day` = WARNING, exit 0, no client; an unwritable report = WARNING, the log stands; a raising upsert = WARNING, exit 0.

**RED rows -> the flag -> the flip preconditions.** D22 -> tests/test_s81_d22_nightly_learning.py (R1-R29 + P1-P7, 50 nodes) + tests/test_s81_g5_gate_rows.py (G5-GR1..GR7) -> `ENABLE_LEARNING_JOB` -> 045 applied (the kb_* reads and the coverage upsert), the `learning` service created, ONE DRY run read by the owner BEFORE any schedule (owner steps below).

## Deliberate pin changes (GC-6)

| E | file | change | reason |
|---|---|---|---|
| E1 | tests/test_s81_kb_schema.py | P02_ALLOWED + the two rows `("scripts/cron_learning.py", 'KB_COVERAGE_TABLE = "kb_coverage_daily"')` / `('KB_FEEDBACK_TABLE = "kb_feedback"')` with the comment `#: S81-G5 E1: the D22 job's two relation constants.`; P01 unchanged | the G2 / G4 row form for the job's two relation constants |
| E2 | scripts/cron_few_shot_rotation.py | DELETED | R-G5-8 option (i): the only code path writing user-derived exemplars (with a comparison uuid) under data/; no importer; flag unset; never registered (the G1 judgeme precedent) |
| E3 | tests/test_cron_few_shot_rotation.py | DELETED | the deleted script's test file (12 nodes, green at base, so `comm -23` stays empty) |
| E4 | tests/test_exemplar_contamination.py | RULED OUT (R-G5-4): byte-identical | R26 scans import statements only |

No other pin moved.

## Counts

- RED file (frozen, blob sha256 98b2bafced383455edc4d6cc9c8690d1bea5c3193a042a0d760ddf0eb5d08656, unchanged by the replay and the round commit): 50 nodes (43 RED at base on AssertionError only + 7 PIN), 50 / 50 at HEAD in three runner calls (flag unset; `ENABLE_LEARNING_JOB=true`; `=apply`, each exported in the runner environment only):
  - `[pyt] tag=g5fin-red-off start=2026-11-05 06:35:17 end=2026-11-05 06:35:25 elapsed=9s bound=600s status=OK rc=0`
  - `[pyt] tag=g5fin-red-true start=2026-11-05 06:35:27 end=2026-11-05 06:35:36 elapsed=10s bound=600s status=OK rc=0`
  - `[pyt] tag=g5fin-red-apply start=2026-11-05 06:35:38 end=2026-11-05 06:35:47 elapsed=9s bound=600s status=OK rc=0`
  - each 50 passed; `[hermeticity] sentinel checked 50 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`
- Gate rows tests/test_s81_g5_gate_rows.py (blob sha256 40762b235921e4e078b74e690520d3e1e7658fb460990d8ac8b4e750aa46d8b3): 7 / 7 = G5-GR1 (GC-2 two actors), G5-GR2 (GC-3 screen before the cut), G5-GR3 (64-hex inside a longer token in a winner_reason), G5-GR4 (the Bahrain dialling prefix in a winner_reason + an 8-digit run in a product name), G5-GR5 (a uuid shape with no 8-digit run), G5-GR6 (unclean kb_feedback field names map to `other`, never ground, never reach an output), G5-GR7 (m0 != m1 both in SOURCE_METHODS cluster under `mixed`): `[pyt] tag=g5fin-gr-head start=2026-11-05 06:35:48 end=2026-11-05 06:35:51 elapsed=3s bound=600s status=OK rc=0`.
- Mutants: the spec's 15 (M1-M15) killed at the RED gate; GREEN's two inverse edits killed by GR1 / GR2; the adversary's 39 on the GREEN bytes: 32 killed by the RED + gate rows, A1-A4 / A11 / A12 survived there (MIN-2) and are NOW KILLED by GR3-GR7 on sha-verified byte copies of scripts/cron_learning.py under `.qa-mutation.lock` (restored, sha256 compared; each failure an AssertionError):
  - A4-anchored (64-hex regex anchored) -> G5-GR3 FAIL; A1-no8digit and A2-no973 -> G5-GR4 FAIL; A3-nouuid -> G5-GR5 FAIL; A11-fieldname-noscreen -> G5-GR6 FAIL; A12-mixed-unknown -> G5-GR7 FAIL
  - A18 (the per-comparison de-dup in `_confirmed` removed) is NEAR-EQUIVALENT by ruling RB-G5-4: an unclean confirmed comparison counts twice in learning.dropped.deidentify (one exemplar + one eval candidate), which is the metric's definition.
- Pins (E1 + the scripts-scanning pins): `[pyt] tag=g5fin-pins start=2026-11-05 06:36:04 end=2026-11-05 06:36:30 elapsed=26s bound=1200s status=FAIL rc=1` = 1 failed / 1052 passed; the 1 = the known d17 r9 CRLF baseline.
- CI-order set (spec 12.1, 7 files): `[pyt] tag=g5fin-ciorder2 start=2026-11-05 06:36:52 end=2026-11-05 06:37:19 elapsed=27s bound=1200s status=FAIL rc=1` = 1 failed (d17 r9) / 835 passed.
- Comm set (RB-G5-1): GREEN's 47 + tests/test_s81_s08b_gate_rows.py (a CLAUDE.md reader through the `CLAUDE_MD` it imports from test_s81_s08b_legacy_fingerprint.py; the adversary's MAJ-1) = 48 at HEAD, in 2 chunks (25 + 22) + tests/test_secret_scan_static.py ALONE:
  - `[pyt] tag=g5fin-comm-head-00 start=2026-11-05 06:40:38 end=2026-11-05 06:42:09 elapsed=92s bound=1200s status=FAIL rc=1` (2 failed, 1096 passed, 1 skipped)
  - `[pyt] tag=g5fin-comm-head-01 start=2026-11-05 06:42:23 end=2026-11-05 06:43:29 elapsed=66s bound=1200s status=FAIL rc=1` (6 failed, 2123 passed)
  - `[pyt] tag=g5fin-comm-head-secretscan start=2026-11-05 06:43:30 end=2026-11-05 06:43:51 elapsed=21s bound=600s status=OK rc=0` (31 passed)
  - vs the base record at `00e4120d` `base_records/00e4120d.../9a85c0b03c896d76e22fa40a18090e99dea29e76553f0486166d68e29f65c91d` (47 files: the 46 of the stored ec747b49 record c636b9d5... + the s08b gate rows), built by PER-FILE REUSE (GC-9): 23 members reused (their text names neither SmartCompareApp nor CLAUDE.md, no glob walker, no import of a CLAUDE.md reader; no tests/ file changed in #387), 24 RUN in a detached scratch worktree of origin/main (removed afterwards): `[pyt] tag=g5fin-comm-base-00 start=2026-11-05 06:44:15 end=2026-11-05 06:46:18 elapsed=123s bound=1200s status=FAIL rc=1` (23 files: 5 failed / 2395 passed) + `[pyt] tag=g5fin-comm-base-secretscan start=2026-11-05 06:46:20 end=2026-11-05 06:46:40 elapsed=20s bound=600s status=OK rc=0` (31 passed).
  - HEAD failed = base failed = the 8 fresh-checkout CRLF hygiene nodes (d16 r10, d17 r9, the five s16 r27, s19 r15); `comm -13` EMPTY; `comm -23` EMPTY.
- The fourteen backend-scanning client jest fences by path through the junction (node v24.11.1, jest 29.7.0): `[jest] tag=g5fin-fences start=2026-11-05 06:48:06 end=2026-11-05 06:48:23 rc=1` = 13 / 14 suites, 4 failed / 236 passed: exactly the four config/nativeBundle.w37 drift nodes (d5, k2, k4, k5).
- FULL jest suite once (LC-7, the rebased tree carries G6's client files): `[jest] tag=g5fin-full start=2026-11-05 06:48:38 end=2026-11-05 06:49:01 rc=1` = suites 398 passed / 1 failed / 3 skipped of 402; tests 3,852 passed / 4 failed (the four w37 drift nodes) / 13 skipped / 13 todo; snapshots 42 / 42; 20.9 s; no .snap change (exit read from the JSON result: success false, numFailedTests 4).
- ruff --select E9,F63,F7,F82 --no-cache + py_compile on the touched python files: All checks passed.
- Not run: the pre-commit hook test files (no .githooks change); the corpus gate (no price_service edit); the R8 sentry pair and tests/test_paid_route_metering.py (no app/ file; RB-G5-10).

## Stated limits (spec L1-L12, R-G5-9 as L13, RB-G5-3 / RB-G5-7 as L14 / L15, GC-10)

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
- L14 (RB-G5-3, MIN-1) The kb_specs grounding read takes ONE range of 800 rows per 100-id chunk with no paging and reports status ok: a product with more cited spec rows loses its grounding and the proposal falls to needs_operator. Dark, nothing applied; the paged form is the follow-up D22d.
- L15 (RB-G5-7, MIN-6) Product names are logged unescaped and the shape screen does not reject control characters, so a newline inside a stored product name can split a log record (rendering, never a value leak); escaping on render = D22d.
- GC-10: the two-actor rule (GC-2) and the screen-before-cut order (GC-3) are pinned by G5-GR1 / G5-GR2.
- MIN-7 (RB-G5-8, informational): `capped` at exactly max_rows rows conforms to spec 2.3; no change.

## Adversary (correctness, one, LC-1)

NOT_READY on the GREEN bytes: 0 blocking, 1 MAJOR, 7 minors. MAJ-1 (tests/test_s81_s08b_gate_rows.py missing from the comm set; green at HEAD) CLOSED by RB-G5-1: the file is in the 48-file set at HEAD and in the base record at 00e4120d (above). MIN-1 -> L14; MIN-2 -> G5-GR3..GR7 (A1-A4 / A11 / A12 killed); MIN-3 -> A18 near-equivalent (RB-G5-4); MIN-4 -> the owner steps re-ordered (below and in CLAUDE.md); MIN-5 -> the outputs sentence (RB-G5-6, above and in CLAUDE.md); MIN-6 -> L15; MIN-7 informational (RB-G5-8). No fix round and no re-verifier (LC-2 / LC-4).

## Owner steps (names only; a dated ledger line per step)

1. Apply 045 then 047 (owner item 29) then 052.
2. Create the `learning` Railway service from `railway.learning.json` with the service-role names `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` and NO schedule.
3. Set `ENABLE_LEARNING_JOB=true` and make ONE DRY run; read the report in the run log. The FIRST canary item: `learning.cases.*` with category `unknown` or source `unknown` dominating = a PostgREST JSON path returned null: report it. Then `learning.cases.*` per bucket, `learning.clusters.systematic`, the proposals, the exemplar candidates, the eval candidates, the skipped tables.
4. Only after step 3 reads clean, set the nightly cron schedule at a DIFFERENT hour from `kb-coverage`.
5. Then `apply`. Eval cases are ratified by hand into data/validation_gold_truth.json only through a reviewed PR. Rollback: unset the variable.

## [NATIVE READ]

EMPTY (no client copy, no Arabic string).
