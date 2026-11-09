# S81-G10 UNIT SPEC: G10 FOLLOWUPS = D-S22-J1 JUDGE-JSONB-FILTER + S81-22b SELF-CRITIQUE-RETIRE + S81-22c KB-PRODUCT-IDS + S81-04d SPEND-DURABLE-RETRIEVE

- Group: S81-G10 FOLLOWUPS, the tenth SAFE group under LC-9; orchestrator Opus 5.5 by the owner's ruling of 2026-11-07; spec agent Opus 5.5 (session 89, 2026-11-09 16:47-18:1x AST).
- Brief: docs/investigations/2026-10-22-session-81-state/specs/S81_G10_BRIEF.md (read in full); common brief scripts/s81-common.txt (LC-1..LC-9, the MOVING MAIN line of 90d4ed74); PLAN_S81 (Standing constraints, VERIFY corrections, the S81-22 unit text: "the inline ENABLE_SELF_CRITIQUE regeneration retired"); PLAN_S80 R-A1..R-A15; DEFECT_LEDGER; the S81-22 rulings (R-S22-12, R-S22-14, R-S22-26 / L-KBID in specs/RULINGS_S81_22.md and specs/S81_22_BRIEF.md).
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-g10, detached at the base 90d4ed74bdd16f62130dc9f7a4727620f8a1cea2; `git status --short` EMPTY before and after every probe (re-checked after the last probe). Branch to create at RED/GREEN: feature/s81-g10-followups.
- Measurement location: <scratchpad>/S81-G10/ (notes.md, the probes j1_render_probe.py, j1_e2e_probe.py, s04d_leak_probe.py, g8golden_probe.py, comm.py, proto_apply.py, proto_22b.py, every pyt log, comm/ = closure.txt, comm_set.txt, members.tsv, reuse_plan.tsv, excluded.txt, summary.json). <scratchpad> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/07cedb96-2752-480a-aa62-62e55837e125/scratchpad.
- Prototype: a DETACHED scratch worktree <scratchpad>/S81-G10/proto at 90d4ed74 (no junction) held all four units' code edits plus the minimal E-row edits named below; it is removed at the end of this spec run (`git worktree remove --force`, verified with `git worktree list`). Every number labelled "prototype" was measured there.
- Personal data: none anywhere (synthetic ids such as 00000000-0000-4000-8000-000000000001, msgbatch_probe, probe.invalid); no secret value read or printed; production flag state only from the dated ledger lines cited.
- Every file:line below was read at 90d4ed74 in this run.

## 0 THE GROUP

0.1 One branch `feature/s81-g10-followups` from origin/main 90d4ed74; one RED round (one agent writes the four RED files), one GREEN, one adversary (correctness with the data, privacy, asyncio and legal-manifest checks folded in), fix rounds as needed, one final round (the FULL jest once, LC-7), one PR (body <= 25,600 bytes, one short section per unit).

0.2 The units, their flags, their footprint:

| Unit | Flag (none new) | Production state (newest ledger lines) | App / scripts / data footprint | Test footprint (RED + E-rows) |
|---|---|---|---|---|
| D-S22-J1 JUDGE-JSONB-FILTER | rides ENABLE_BATCH_JUDGE (unset/false OFF before any read; truthy DRY; `apply` WRITE) | judge service exists, ENABLE_BATCH_JUDGE=true (DRY), ENABLE_LLM_SPEND_BREAKER=true, NO schedule (ledger 2026-11-07 12:40) | scripts/cron_compare_judge.py (1 line, :502) | NEW tests/test_s81_s22j1_judge_jsonb_filter.py; EJ1 tests/test_s81_s22_judge.py (the fake's contains branch); EJ2 tests/test_s81_s22d_ledger_pins.py (S22_LF_SHA re-pin) |
| S81-22b SELF-CRITIQUE-RETIRE | none (unflagged deletion of code reachable only under ENABLE_SELF_CRITIQUE) | ENABLE_SELF_CRITIQUE UNSET on web (ledger 2026-11-06 20:35, line 299; 2026-11-07 06:24, line 316) | DELETE app/services/verdict_critique_service.py; EDIT app/services/structured_comparison_service.py, app/services/feedback_service.py, app/services/llm_router.py, app/services/model_config.py, app/services/api_budget_service.py (comment), scripts/cron_learning.py (comment), app/legal/processors.json (one module path) | NEW tests/test_s81_s22b_self_critique_retire.py; DELETE tests/test_verdict_critique_service.py, tests/test_self_critique_orchestration.py; E-rows EB1-EB13 (section 22b.4) |
| S81-22c KB-PRODUCT-IDS | rides ENABLE_KB_FIRST_SERVE (the key) + ENABLE_COMPARE_RUN_LEDGER (the row) | both UNSET on web (ledger 2026-11-07 06:24 "every S81 flag ... UNSET"; 09:05 not flipped) | app/services/structured_comparison_service.py (_stamp_unit_metadata, +8 lines), app/services/compare_runs.py (the row field + the D-S22-K1 widening) | NEW tests/test_s81_s22c_kb_product_ids.py; EC1 tests/test_s81_s11b_result_aggregates.py, EC2 tests/test_s81_s18b_store_label.py (the G8 golden P1 rows) |
| S81-04d SPEND-DURABLE-RETRIEVE | rides ENABLE_LLM_SPEND_BREAKER (log-only, R-A1 b) | UNSET on web; =true on the judge service (sync path only) | app/services/llm_spend_breaker.py (+10 lines) | NEW tests/test_s81_s04d_durable_retrieve.py; no E-row (measured) |

Plus CLAUDE.md (GREEN, last): ONE G10 block after the S81-G9 block (before `## Tests`, :630), the :341 pointer clause, the ENABLE_SELF_CRITIQUE row rewritten as retired, the self-critique sentences made false by S81-22b rewritten in place, and the rows that lag after the first production OTA rewritten in place (section 12.6).

0.3 Files two units share and the order GREEN applies them:
- app/services/structured_comparison_service.py: S81-22b deletes six regions (:3402, :4690-4706, :4789-4794, :5582-5608, :5713-5718, :9879-9999 at base); S81-22c inserts 8 lines after :3997 (inside `_stamp_unit_metadata`, before every 22b region except :3402). ORDER: apply S81-22c's insertion FIRST against base line numbers (anchor: the two lines `if kb_marks:` / `metadata["kb_hit"] = list(kb_marks)` at :3996-3997), THEN S81-22b's deletions by ANCHOR TEXT (never by stale line numbers: after the 22c insertion every 22b region below :3997 shifts by +8; the prototype measured exactly this shift and an anchor-checked deletion).
- CLAUDE.md: every unit's row inside ONE G10 block, written LAST.
- No other file is shared between units (compare_runs.py is S81-22c only; cron_compare_judge.py J1 only; llm_spend_breaker.py 04d only).

0.4 Group facts measured once:
- Corpus gate at base (scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_SELF_CRITIQUE,ENABLE_KB_FIRST_SERVE,ENABLE_COMPARE_RUN_LEDGER,ENABLE_BATCH_JUDGE,ENABLE_LLM_SPEND_BREAKER,ENABLE_SCRAPEDO_SUPER,ENABLE_KB_BRANDS,ENABLE_KB_COVERAGE_ROLLUP, the pinned venv, alone, 16:53:55-17:03:26): `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656`, `OVERALL SHA256 387fa35c600f6ea9f049d38a84966f435b9827ed2ed636c0144b7b56f1d09181` (<scratchpad>/S81-G10/corpus_base.{txt,json}). The value differs from G9's cce256e1... only because the flag list is part of the payload (the G10 list has eight names). Prototype HEAD (all four units applied): see 12.4. The corpus gate exercises price_service.extract_price_from_html only; it proves no collateral damage to the extraction spine; the S81-22b / S81-22c flag-OFF identity rests on the save-path and SSE PIN rows (22b.5, 22c.5).
- Line endings: every working-copy file G10 edits is CRLF (counted: processors.json 274/274, legal_s78.json 509/509, CLAUDE.md 1092/1092, feedback_service.py 373/373, model_config.py 263/263, llm_router.py 1228/1228, api_budget_service.py 1361/1361, test_s81_s06_anthropic_router.py 2751/2751, test_s81_s06_router_gate_rows.py 981/981, test_comparison_id_echo.py 1337/1337, s81_g8_flag_off_golden.json 8235/8235; `file` reports CRLF for cron_compare_judge.py, llm_spend_breaker.py, structured_comparison_service.py, compare_runs.py, 048); core.autocrlf=true, index LF, no .gitattributes rule for these paths. The Edit tool keeps CRLF; `git diff --stat` must show hunks only (the prototype's did: 14 files, +31 / -1350 with the two deleted test files).
- Known environmental base failures on this box (CRLF working copy; also in the stored f4461556 base record): tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first, tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf, tests/test_s81_s18b_store_label.py::test_r2_table_shape; plus the stored-record entries test_prompt_truth (2 ERROR, cold tiktoken cache) and test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content.

## Unit D-S22-J1 JUDGE-JSONB-FILTER

### J1.1 Base state (measured at 90d4ed74)

| # | Where | Measured |
|---|---|---|
| 1.1 | scripts/cron_compare_judge.py:496-547 `_resume` | step 0 (R-S22-33): `rows = _paged(lambda: client.table(JUDGEMENTS_TABLE).select("run_id,batch_id,model,flags").eq("judge", "haiku").contains("flags", ["batch_pending"]), 100000)` at :501-502; groups by batch_id; `ac is None` -> resume.still_pending (:511-513); retrieve -> lost (404/410) marker rows `batch_lost` in apply (:514-523); ended -> `_read_results` (:528-531), apply: ONE ledger row + breaker record (sync) + upsert + judged_at + batch delete (:533-547) |
| 1.2 | :349-359 `_paged` | `build().order("id").range(start, start + 499).execute()`; rendered as `order=id.asc&offset=0&limit=500` (probe) |
| 1.3 | :812-850 `main` | `judge_mode()` FIRST (:813-816: OFF -> `_say` + return 0 before any read, client build or other env read); `_resume` is the first read (:843); any exception from steps 0-2 is caught at :847-850 (`[COMPARE_JUDGE] read failed (<type>)`, `_err`, `_finish(..., 0)`), so a 400 at step 0 ends the run with nothing judged |
| 1.4 | :34 | `import json` already at module top (stdlib; the docstring rule "Only the standard library and kb_seed_common at module top" holds) |
| 1.5 | migrations/048_compare_runs.sql:155-167 | compare_judgements: `id uuid PRIMARY KEY` (:156), `run_id uuid NOT NULL REFERENCES compare_runs ON DELETE CASCADE` (:157), `judge text CHECK IN (programmatic, haiku, sonnet)` (:158), `model` (:159), `batch_id text` (:160), `verdicts jsonb NOT NULL CHECK object` (:161), `flags jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(flags) = 'array')` (:162), `note`, `cost_usd`, `created_at`, `UNIQUE (run_id, judge)` (:166). 048 APPLIED in production 2026-11-07 (ledger 12:05) |
| 1.6 | pinned client (venv: postgrest 2.31.0, httpx 0.28.1, Python 3.12.9) base_request_builder.py | `contains(col, value)`: a str -> `filter(col, "cs", value)` verbatim; a non-dict Iterable -> `"{" + ",".join(value) + "}"` (the PostgreSQL array literal); a dict -> `json.dumps(value)`. `filter(col, op, criteria)` -> param `col=op.criteria`. `cs()` / `cd()` / `ov()` / `contained_by()` with a list all render `{...}` |
| 1.7 | the rendering probe (<scratchpad>/S81-G10/j1_render_probe.py -> j1_render.json; a real SyncPostgrestClient(http_client=httpx.Client(transport=httpx.MockTransport(recorder))), synthetic host probe.invalid) | base call: `GET /rest/v1/compare_judgements?select=run_id%2Cbatch_id%2Cmodel%2Cflags&judge=eq.haiku&flags=cs.%7Bbatch_pending%7D&order=id.asc&offset=0&limit=500`, decoded param `flags=cs.{batch_pending}` (exactly the production 400 URL of the ledger 12:40 line). Fix candidates: `.contains("flags", json.dumps(["batch_pending"]))` and `.filter("flags", "cs", json.dumps(["batch_pending"]))` BOTH render `flags=cs.["batch_pending"]` (raw `flags=cs.%5B%22batch_pending%22%5D`); a two-element json.dumps renders `cs.["a", "b"]` (a space, valid JSON), the compact form `cs.["a","b"]` |
| 1.8 | the end-to-end probe (j1_e2e_probe.py: `main(["--report", f], client=<real postgrest client over MockTransport>)`, ENABLE_BATCH_JUDGE=true, no ANTHROPIC_API_KEY, a fake PostgREST answering 400 (22P02) to `cs.{batch_pending}` and 200 with one pending marker to `cs.["batch_pending"]`) | base: rc 0, `errors {"APIError": 1}`, `runs_read 0`, `resume.batches 0` = the production DRY totals of 2026-11-07 12:40. Prototype (the one-line fix): rc 0, `errors {}`, `resume {"batches": 1, "still_pending": 1, ...}` |
| 1.9 | sweep: every PostgREST containment / overlap filter over app/ and scripts/ (`git grep` of `.contains(`, `.contained_by(`, `.overlaps(`, `.ov(`, `.cs(`, `.cd(`, `"cs"`/`"ov"`/`"cd"`, `cs.{`, `cs.[`, `ov.{`, `text_search(`, `.filter(`) | ONE hit: scripts/cron_compare_judge.py:502. Non-PostgREST look-alikes: scripts/check_channel_freshness.py:282 `ancestry.contains(sha)` (a set of commit hashes), app/services/drug_database_service.py:31 `.text_search(` (FTS, not containment), app/static/admin/costs.html:157 (JS). No other jsonb column is read with a list operand anywhere in app/ or scripts/: nothing to record as a follow-up |
| 1.10 | every other judge PostgREST call vs the schemas | `_recompare` :554-555 compare_runs select id,created_at,query_hmac,device_key,recompare + gte created_at; update recompare in_ id (:573); `_window` :581-582 SELECT_COLUMNS (:63-64, all 13 names exist in 048 :116-153) + gte created_at + is_ judged_at null + gte consent_version (smallint); head count :592-594 (select id, count exact, head, lt, is_); `_prior_judgements` :603-604 select run_id,judge,verdicts,flags in_ run_id; `_user_wrong` :616-617 comparison_feedback select comparison_id,winner_correct (027 :28 winner_correct text) in_ comparison_id; `_escalate` :650-651 head count eq judge sonnet + gte created_at; upserts :449 / :465 on_conflict run_id,judge (= the 048 UNIQUE :166); `_set_judged` :479; rpc compare_runs_prune(p_days) (048 :184) and kb_prune_feedback(p_days) (045 :406); DRY head counts on compare_runs / kb_feedback created_at (045 :308). NO other mismatch |
| 1.11 | the frozen fake tests/test_s81_s22_judge.py:130-191 (`_Q`, `FakeClient`) | the `contains` branch (:183-184) filters `all(x in (r.get(col) or []) for x in a[1])`: a str operand iterates its CHARACTERS, so the JSON form filters every pending row out; tests/test_s81_s22_gate_rows.py reuses `tj.FakeClient` (:192, :222, :293) |
| 1.12 | tests/test_s81_s22d_ledger_pins.py:27-31, :123-126 | `S22_LF_SHA` pins the LF sha256 of the three frozen S81-22 files; p2 asserts each equals (an EJ1 edit to test_s81_s22_judge.py turns p2 red) |
| 1.13 | production reachability | the judge runs only when started by hand (no schedule); DRY reads only; 048 is applied but the judge never wrote a marker (DRY), so no `batch_pending` row exists: the fix changes no production read RESULT until a first apply run creates markers |

1.14 Base pass state (bounded runner, base worktree): `tests/test_s81_s22_judge.py tests/test_s81_s22_compare_runs.py tests/test_s81_s22_gate_rows.py tests/test_s81_s22d_ledger_pins.py`: 2 failed, 220 passed (the failures = j01 + b02, the CRLF environment, both in the f4461556 base record). `[pyt] tag=g10spec-baseA start=2026-11-09 17:03:53 end=2026-11-09 17:04:14 elapsed=21s bound=600s status=FAIL rc=1`; `[hermeticity] sentinel checked 222 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.

### J1.2 Contract

- Flag: none new. ENABLE_BATCH_JUDGE through `kb_seed_common.run_mode` (unchanged): unset / blank / garbage / false -> OFF (return 0 FIRST, zero requests); truthy -> DRY; `apply` -> WRITE. ENABLE_JUDGE_WEB_SEARCH stays inert.
- The change: `_resume` sends the JSON operand for the jsonb `flags` column. The request param MUST be exactly `flags=cs.["batch_pending"]` (raw `flags=cs.%5B%22batch_pending%22%5D`); every other param of that request unchanged (`select=run_id,batch_id,model,flags`, `judge=eq.haiku`, `order=id.asc`, `offset`, `limit`). Recommended form: `.contains("flags", json.dumps(["batch_pending"]))` (keeps the verb `contains`, which the frozen fake already knows; `.filter(...)` would hit the fake's "unexpected PostgREST verb" AssertionError). A module constant (e.g. `PENDING_FLAG_OPERAND = json.dumps(["batch_pending"])`) is allowed; its name carries no gitleaks keyword (E-G4-1).
- Failure table: a PostgREST error on the resume read for any other reason -> unchanged (caught at :847-850, counted in `errors.<Type>`, rc 0); an empty answer -> no batch; a pending marker with no batch_id -> skipped (:505); everything after the read unchanged.
- Flag-OFF identity (the main invariant): OFF makes no request at all (unchanged code path, pinned with a transport recorder). DRY and apply: every request other than the resume read is byte-identical (pinned by the full request list under DRY with no pending rows); DRY writes nothing (GR4 + the new rows).
- Seams: `main(argv, client=, anthropic_factory=)`; the real `postgrest.SyncPostgrestClient(base_url=..., http_client=httpx.Client(base_url=..., transport=httpx.MockTransport(handler)))` (the house SDK seam of D17c applied to the PostgREST session); the frozen FakeClient for logic rows.

### J1.3 Change list

1. Byte copies first (the GREEN's own snapshot under its notes folder).
2. scripts/cron_compare_judge.py:502: `.contains("flags", ["batch_pending"])` -> `.contains("flags", json.dumps(["batch_pending"]))` (optionally through a named constant defined beside `_PENDING_FLAGS` :68). CRLF kept. The docstring may gain one clause "(the jsonb operand, D-S22-J1)" (optional).
3. tests/test_s81_s22_judge.py (EJ1): in `_Q.execute`, the `contains` branch decodes a str operand: `vals = json.loads(a[1]) if isinstance(a[1], str) else a[1]` then filters with `vals` (the fake now emulates PostgREST's jsonb containment; `json` is already imported at :29). Measured on the prototype: without EJ1 five frozen nodes go red (`test_j14c_resume_first[ended]`, `[running]`, `[lost]` StopIteration, `test_jf1_3a_resume_maps_by_hashed_id` AssertionError, tests/test_s81_s22_gate_rows.py::`test_g22_gr4_dry_resume_writes_nothing`); with EJ1: 70 passed + the env j01 (`[pyt] tag=g10spec-protoA2 start=2026-11-09 17:11:41 end=2026-11-09 17:11:51 elapsed=10s bound=600s status=FAIL rc=1`).
4. tests/test_s81_s22d_ledger_pins.py (EJ2): `S22_LF_SHA["tests/test_s81_s22_judge.py"]` re-pinned to the post-EJ1 LF sha256 (the other two entries unchanged). Measured: the prototype's EJ1 turned `test_p2_s22_frozen_files_unchanged` red.
5. NEW tests/test_s81_s22j1_judge_jsonb_filter.py (the RED, LF, ASCII).
6. No other file.

### J1.4 Existing pins

4.1 Deliberate changes: EJ1 (the fake's contains semantics; reason: the frozen fake pinned the rejected array-literal operand: "a frozen row pinning a rejected API parameter is a ruled pin-fix", the S86 lesson) and EJ2 (the frozen-file sha table follows EJ1). No assertion is weakened: list operands behave exactly as before; a wrong JSON operand still filters to nothing.
4.2 Must stay green: every other node of tests/test_s81_s22_judge.py, test_s81_s22_compare_runs.py, test_s81_s22_gate_rows.py (G22-GR1..GR7), test_s81_s22d_ledger_pins.py, test_s81_kb_schema.py (P02_ALLOWED names the judge's write lines; unchanged), the scripts/ walkers.

### J1.5 RED tests: tests/test_s81_s22j1_judge_jsonb_filter.py

Hermetic: `import app.main` first (the dotenv guard); every judge knob set to synthetic values in the PIN rows (JUDGE_MAX_USD, JUDGE_MAX_RUNS, JUDGE_WINDOW_DAYS, JUDGE_SAMPLE_PCT, JUDGE_ESCALATION_MAX_PER_DAY, JUDGE_ESCALATION_MAX_USD, RECOMPARE_WINDOW_DAYS, ENABLE_JUDGE_WEB_SEARCH both states, ENABLE_LLM_SPEND_BREAKER both states with a fake breaker recorder); no network (MockTransport only); `ANTHROPIC_API_KEY` absent or a run-time synthetic value with an injected `anthropic_factory`.

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R1 | the resume operand | DRY `main` over a real SyncPostgrestClient + MockTransport recorder: the compare_judgements request carries `flags == 'cs.["batch_pending"]'` (decoded param) | RED (AssertionError: `cs.{batch_pending}`) | the :502 fix |
| R2 | the raw query | the same request's raw query contains `flags=cs.%5B%22batch_pending%22%5D` and NOT `cs.%7B` | RED | fix |
| R3 | DRY end to end, provider absent | fake PostgREST (400 to the array literal, 200 + one pending marker to the JSON form): report `errors == {}`, `resume.batches == 1`, `resume.still_pending == 1`, rc 0 | RED (`errors.APIError == 1`, batches 0) | fix |
| R4 | DRY end to end, batch ended | an injected anthropic_factory whose retrieve answers `ended` and whose results yield one succeeded item for the marker's custom id: `resume.filled == 1`; the recorder holds NO POST/PATCH/DELETE request and no ledger insert (DRY writes nothing) | RED (the read 400s first) | fix |
| R5 | apply end to end, batch ended | ENABLE_BATCH_JUDGE=apply: exactly ONE llm_spend_ledger POST, ONE compare_judgements upsert request (a POST whose params name on_conflict run_id,judge; the RED records the exact rendering on the pinned client) carrying the haiku row with `flags == []`, ONE compare_runs PATCH judged_at for a clean answer, ONE batches.delete | RED | fix |
| R6 | apply, batch lost | retrieve raises a 404-shaped error: ONE upsert of the marker row with `flags == ["batch_lost"]`; resume.lost == 1 | RED | fix |
| P1 | OFF identity (FULL config) | unset / "" / "false" / "0" / "off" / " FALSE ": rc 0 and ZERO requests on the transport recorder, the client factory never called | PIN green | unchanged |
| P2 | the other requests unchanged | DRY with no pending rows: the ordered list of (method, table, params minus the resume flags param) equals a literal recorded at base (recompare, window, expired head count, prior judgements, feedback, escalation head count, the two DRY prune head counts) | PIN green (at base the run stops at the 400; the literal is recorded with a transport that answers 200 [] to both operand forms) | unchanged |
| P3 | the containment sweep | an AST scan of app/**/*.py and scripts/**/*.py: exactly one `.contains(` call on a PostgREST builder (in `_resume`) and no `.overlaps(` / `.ov(` / `.cs(` / `.cd(` / `.contained_by(` call; no string literal starting `cs.{` / `ov.{` / `cd.{` | PIN green | unchanged |
| P4 | the column type | migrations/048_compare_runs.sql declares `flags jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(flags) = 'array')` | PIN green | unchanged |

(R4-R6 may build their bodies with the frozen helpers of tests/test_s81_s22_judge.py: `custom_id`, `_haiku_prior`; importing that module makes the new file a test-support importer: name it in the comm set.)

### J1.6 Mutation table (byte copies, exact-string edits, killing rows via pyt -k, restore, sha256 compare)

| M | Edit (scripts/cron_compare_judge.py unless said) | Killed by |
|---|---|---|
| J-M1 | revert to `.contains("flags", ["batch_pending"])` | R1, R2, R3, R4, R5, R6 |
| J-M2 | `json.dumps(["batch_lost"])` | R3 (batches 0), R4-R6 |
| J-M3 | `.filter("flags", "cs", "{batch_pending}")` | R1, R2, R3 |
| J-M4 | drop `.eq("judge", "haiku")` from the resume read | P2 / R1 (the param list) |
| J-M5 | EJ1 reverted (fake iterates characters) | the five frozen nodes of J1.3 step 3 |
| J-M6 | `json.dumps(["batch_pending"], separators=(",", ":"))` | EQUIVALENT for one element (identical bytes): reported for a ruling, no row |

### J1.7 Comm set: within the group set (section 12): the importers of scripts.cron_compare_judge (tests/test_s81_s22_judge.py, test_s81_s22_gate_rows.py, test_s81_s22d_ledger_pins.py through the frozen-sha table, the scripts/ walkers), the CLAUDE.md readers, the source-scanning pins. No client fence reads the script.

### J1.8 CLAUDE.md row (inside the G10 block) and owner steps

Row text (GREEN may tighten): "D-S22-J1 JUDGE-JSONB-FILTER (no new flag; rides `ENABLE_BATCH_JUDGE`): `scripts/cron_compare_judge.py` `_resume` (step 0) filters the jsonb `compare_judgements.flags` with the JSON operand (`flags=cs.["batch_pending"]`, measured on the pinned postgrest 2.31.0); the array-literal form `cs.{batch_pending}` answered PostgREST 400 in the 2026-11-07 DRY run (errors.APIError=1, runs_read=0). DRY / apply otherwise unchanged; OFF makes no request. RED tests/test_s81_s22j1_judge_jsonb_filter.py; E-rows EJ1 (the frozen judge fake decodes a JSON operand) and EJ2 (the S81-22d frozen-file sha)."
Owner steps (names only): after the merge, ONE judge DRY run (the judge service redeploy or a railway run with the service's own variables): step 0 shows no `errors.APIError`; a DATED ledger line. The `ENABLE_BATCH_JUDGE=apply` flip keeps its S81-22 preconditions (ENABLE_COMPARE_RUN_LEDGER after App Review approval and the 50-run read); this fix is one more of them, now met at merge.

### J1.9 Stated limits

- L-J1-1: the proof drives the pinned client against a FAKE PostgREST (MockTransport); that PostgREST parses `cs.["..."]` on a jsonb column as JSON containment is the documented JSON form and is re-read live only by the owner's DRY run (owner step).
- L-J1-2: no `batch_pending` row exists in production (the judge has only run DRY), so the fix changes no production read result until an apply run writes markers.
- L-J1-3: the gate rows exercise the fake; the real-client rows exercise only the requests the fake PostgREST answers (unknown routes answer 200 []).

### J1.10 Out of scope: the apply flip; any other judge logic or knob; the escalation lane; S81-22e (refusal rows) and S81-22f (camera / URL link) (section 10 of S81-22c).

### J1.11 Open questions: Q-J1-1 the named constant vs the inline `json.dumps` (either renders the same bytes; the RED pins the request, not the source form).

## Unit S81-22b SELF-CRITIQUE-RETIRE

### 22b.1 Base state (measured at 90d4ed74)

1.1 Production state: ENABLE_SELF_CRITIQUE is UNSET on web (ledger 2026-11-06 20:35, line 299: "Also UNSET on web: ... ENABLE_SELF_CRITIQUE (= default OFF; closes the UNKNOWN ...)"; 2026-11-07 06:24, line 316: "every S81 flag and ENABLE_LEGACY_FINGERPRINT_READER / ENABLE_SELF_CRITIQUE UNSET"). No dated line ever records it ON. PLAN_S81 S81-22 text: "the inline ENABLE_SELF_CRITIQUE regeneration retired"; R-S22-12: "OFF -> the corpus-gate deletion like the G7 varhint retire".

1.2 The module app/services/verdict_critique_service.py (391 lines): imports api_budget_service, llm_router, database_service.get_admin_supabase_client, model_config (critic_model, sampling_kwargs, token_limit_kwargs), openai_service.get_client (:36-40; no load_dotenv, no import-time side effect beyond those modules, all already loaded by the orchestrator); `CRITIQUE_THRESHOLD = 7` (:56); the critique call routes through `_llm_router.route("critique", ...)` (the 16th routed site).

1.3 Reachability with the flag OFF (production): `_apply_self_critique` (structured_comparison_service.py:9879-9980) sets `self._verdict_critique_outcome = None` (:9906) and `self._regen_model_downgraded = False` (:9909), then returns `comparison` at :9910 (`if not _vcs.is_self_critique_enabled()`), with no `await` before that return; `_verdict_critique_metadata` (:9982-9998) returns None, so no `_verdict_critique` key is written (:4792-4794 sync, :5716-5718 stream); feedback_service `_without_verdict_critique` returns the SAME object when the key is absent (:62-63); `track_after_persist` skips the persist (`isinstance(_crit, dict)` False, :134); llm_router `_self_critique_on()` (:540-545) is evaluated only when `any_role_enabled()` (every S81-06 role flag unset on web) and returns False on ModuleNotFoundError (:544). Stream path with ENABLE_FULL_STREAM_DEADLINE ON: base awaits `asyncio.wait_for(_critique_coro, timeout=_tail_residual())` (:5600-5606), `_tail_residual()` floors at 0.05 s (:5017-5020); on CPython 3.12.9 a positive-timeout `wait_for` runs the never-suspending OFF coroutine inline, so no TimeoutError and no partial: deleting the block is unobservable with the flag OFF (pinned by R9b).

1.4 The deletion map (every reference outside the module; `git grep` of the retired identifiers over app/, scripts/, data/, railway*.json, at base):

| File:line | What | Fate |
|---|---|---|
| structured_comparison_service.py:3402 | `self._regen_model_downgraded: bool = False` in `__init__` (read only by the regen closure :9938 / :9979) | delete |
| :4690-4706 | sync path: the `_apply_self_critique(...)` call and its comment (I3.1) | delete |
| :4789-4794 | sync path: `_crit_meta = self._verdict_critique_metadata()` -> `_metadata_override["_verdict_critique"]` (I3.2) | delete |
| :5582-5608 | stream path: `_critique_coro = self._apply_self_critique(...)` + the M13-04 `wait_for` / else-await block | delete (the deadline still bounds verdict + moderation) |
| :5713-5718 | stream path I3.2 metadata threading | delete |
| :9879-9999 | `_apply_self_critique`, `_verdict_critique_metadata` (+ the trailing blank) | delete |
| prose :1716, :1727, :5001 ("verdict/critique/moderation") | comments | optional reword (not a retired identifier) |
| feedback_service.py:15 | `from app.services.model_config import critic_model` | delete |
| :43-70 | `_without_verdict_critique` | delete |
| :89 | `full_response=_without_verdict_critique(full_response)` | -> `full_response=full_response` |
| :106 docstring, :116 `_crit = metadata.get("_verdict_critique")`, :129-135 the I3.2 persist block | track_after_persist | delete (docstring: three follow-ups) |
| :182-210 | `_persist_verdict_critique` | delete |
| llm_router.py:540-545 | `_self_critique_on()` | delete |
| :552 docstring clause, :560-561 | the critic leg of `active_provider_preflight_allows` | delete (the clause reworded) |
| llm_router.py:53-59 ROLE_FLAGS ("critic"), :81 `_ENTRY_ROLES`, :227 `SITES["critique"]`, :425-444 the consent gates | the S81-06 role / site tables and the consent gate | KEEP byte-identical (22b.2, Q-22b-1) |
| model_config.py:52-53 | the OpenAI `"critic": "gpt-4o-mini"` role default (with its comment) | delete |
| :92-94 | `critic_model()` | delete |
| :224-230 `_ANTHROPIC_ROLE_DEFAULTS["critic"]` (:228) | the Claude critic model = the judge's Haiku selector (scripts/cron_compare_judge.py:833 `mc.anthropic_model("critic")`; frozen row tests/test_s81_s22_judge.py:638) | KEEP |
| api_budget_service.py:947 | the comment line `verdict_critique_service critique_verdict (wired by this rework)` | delete |
| scripts/cron_learning.py:100 | comment `# mirrors verdict_critique_service.CRITIQUE_THRESHOLD (PIN P5)` | reword (the module is retired; the constant 7 stays; the job still reads the kept table) |
| app/legal/processors.json:67 | `"app/services/verdict_critique_service.py",` in the openai row's module list | delete the one line |
| migrations/030_verdict_critiques.sql + rollback, the `verdict_critiques` table, scripts/cron_learning.py :17 / :66 / :84 (the D22 job reads the table) | the table and its readers | KEEP (a table drop is a migration: FOCUS; follow-up) |
| scripts/cron_compare_judge.py:67 `VERDICT_ROLES = ("verdict", "critic")` | the judge's self-produced rule over stored llm_calls | KEEP |

1.5 The test map (18 test-side files = 17 tests/test_*.py + tests/fixtures/legal_s78.json reference the retired names at base (git grep of verdict_critique|ENABLE_SELF_CRITIQUE|_verdict_critique|self_critique|critique_verdict|CritiqueResult|persist_critique|is_self_critique_enabled); the prototype adds tests/test_u3c_store_false_pin.py (a site-count floor, no name); fates measured on the prototype; `[pyt] tag=g10spec-protoC2 start=2026-11-09 17:14:26 end=2026-11-09 17:15:37 elapsed=71s bound=600s status=FAIL rc=1` = 35 failed / 1364 passed / 22 errors over 23 files after the five minimal import edits; `[hermeticity] sentinel checked 1421 test(s)`; `[netguard] blocked 149 attempt(s) from 15 node(s)`):

| File | Base reference | Fate |
|---|---|---|
| tests/test_verdict_critique_service.py | the module's own suite (25 tests) | DELETED with the module |
| tests/test_self_critique_orchestration.py | `_apply_self_critique` only (6 tests) | DELETED |
| tests/test_arabic_verdict_output_w414.py | recorder on `_apply_self_critique` (:432-449), rows 29 / 29b / 29c (:512-557), 33 (:698-758); env list :40 | EB1 |
| tests/test_comparison_quality_v2.py | module import :32; TestCritiqueHedgingExemption :224-280 | EB2 |
| tests/test_feedback_service.py | :26 setattr `_persist_verdict_critique` | EB3 |
| tests/test_model_config.py (named source pin) | "critic" rows :28 / :36 / :44 (module-level dict -> collection AttributeError at HEAD) | EB4 |
| tests/test_model_config_enforced.py (named source pin) | import :29; site branch :225-227; kwargs row :248; floor :148; resolved_models :278-282 | EB5 |
| tests/test_openai_breaker.py | import :81; test_verdict_critique_dispatch_feeds_the_breaker :896-916 | EB6 (also repairs the collection chain of tests/test_cost_meter_s74.py :78, tests/test_s81_s03_llm_ledger_v2.py :75, tests/test_retro_w1_3.py :62, tests/test_s81_s22d_ledger_pins.py :20, all of which import it transitively) |
| tests/test_s70_model_router_downgrade.py | R2.6 rows :574-640; env list :87; docstring :21 | EB7 |
| tests/test_s81_d22_nightly_learning.py | p5 :1546-1550 reads the module file by path | EB8 |
| tests/test_s81_s06_anthropic_router.py | import :51; REPLIES / BASE_KW critique :534 / :555; run_site branch :630-632; p10 :2245-2249; SITE_FUNCS :2527; p07 :2688-2689; p13 :2749 | EB9 |
| tests/test_s81_s06_router_gate_rows.py | G05 :255-305 (cell3); G13 :790-857 | EB10 |
| tests/test_u3c_store_false_pin.py (named source pin) | census floor `sites >= 16` (:214) | EB11 (found by the prototype run g10spec-protoE) |
| tests/test_comparison_id_echo.py | fixture recorder :215-224; `_base_result` :120-140; order pins :953 / :980 / :1023; 8c :1129-1170 | EB12 |
| tests/fixtures/legal_s78.json | `manifest_base.openai.module` :283 | EB13 |
| tests/test_cost_meter_s74.py :197-199, tests/test_s81_s03_llm_ledger_v2.py :113 / :119, tests/test_w49_extraction_catch_redaction.py :94, tests/test_s81_s22_judge.py :589-638 | env-name lists / the Claude critic model | untouched (green on the prototype once EB6 lands) |
| tests/test_migration_030_verdict_critiques.py | reads migration 030 only | untouched (green) |

1.6 processors.json readers and what each renders (the SAFE condition): tests/test_legal_docs_u8.py (MANIFEST :187; schema :75 "module: list of repo-relative FILE paths that exist"; required keys :803; module walks :883 / :980), tests/test_legal_s78.py R22 (:898-919, every row's kind / module / hosts / gate_flag / personal_data equal `manifest_base` of tests/fixtures/legal_s78.json), tests/test_legal_docs_u8_polish.py (:50, the _comment :290), tests/test_legal_disclosure_s77.py (:54, D7 the gmail row :617-622), tests/test_s79_b3b_apple_revoke.py (:1428, the apple row), tests/test_s81_s06_anthropic_router.py R36 (:2441-2445, the anthropic row); app/services/llm_router.py:69 is a comment. NOTHING renders the module list: processors.json :2 says "Internal: no route or page serves it (LR3)"; scripts/render_legal_landing.py does not read it (no scripts/ reference); docs/privacy-data-inventory.md lists no module. The six legal markdown files and the landing legal pages are NOT edited. The openai row keeps id, names, kind, personal_data, hosts, gate_flag, categories and public_name: the edit changes NO rendered legal or privacy text and NO processor. The unit stays SAFE on this surface.

1.7 The S81-12 held branch feature/s81-legal-v3 (e8c8c1dc, merge-base 6c14ac95; read with `git diff` from this worktree, no sibling path named): it shares app/legal/processors.json (its hunks: the `_comment` :2 and the anthropic row `public_name` :271), tests/fixtures/legal_s78.json (its hunks: `_comment`, `s5_carveout_ar`, `tos_s8_openai_ar`, the two section-title lists), tests/test_s81_s06_anthropic_router.py (its hunk: the R36 docstring :2441-2444) and CLAUDE.md. Every G10 hunk in those files is disjoint (:67; :283; :51 / :534 / :555 / :630-632 / :2248 / :2527 / :2688 / :2749): the S81-12 rebase unions them by hand.

1.8 Base pass state: `[pyt] tag=g10spec-baseC start=2026-11-09 17:05:19 end=2026-11-09 17:05:46 elapsed=27s bound=600s status=OK rc=0` (14 files: the two module suites, EB1-EB8 files, test_legal_s78, test_legal_docs_u8, test_migration_030: 586 passed; `[netguard] blocked 121 attempt(s) from 6 node(s)` = the test_openai_breaker preflight rows' neutralized supabase.invalid); `[pyt] tag=g10spec-baseD start=2026-11-09 17:05:52 end=2026-11-09 17:06:21 elapsed=29s bound=600s status=OK rc=0` (test_s81_s06_anthropic_router, test_s81_s06_router_gate_rows, test_legal_docs_u8_polish, test_legal_disclosure_s77: 522 passed; netguard 0).

1.9 Prototype completeness: with all four units + EB4 / EB5-import / EB6-import / EB9-import / EB2-import + EB13 + EJ1 applied, the source-scanning and orchestrator chunk (test_prompt_fence, test_u3c_store_false_pin, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_start_command, test_s81_kb_schema, test_s81_s05_request_context, test_ci_gates, test_w4_13_flag_off_ledger, test_structured_comparison_service, test_streaming, test_text_routes_sse_contract, test_m13_04_full_stream_deadline, test_retro_w2_1, test_s81_s20_result_gate, test_s81_s17_kb_ingest, test_s81_s10_fragrance_gate, test_s75_fanout_identity, test_s71_u13_compare_auth_required, test_prompt_truth, test_s81_d14_live_robots, test_comparison_quality_detector, test_cost_tracking): 2 failed / 1892 passed / 2 skipped / 1 xfailed / 2 errors = EB11 (`test_u3c_03`, "saw 15") + the base-record r06 + the two base-record test_prompt_truth ERRORs. `[pyt] tag=g10spec-protoE start=2026-11-09 17:16:16 end=2026-11-09 17:17:44 elapsed=87s bound=600s status=FAIL rc=1`; `[hermeticity] sentinel checked 1897 test(s)`; `[netguard] blocked 64 attempt(s) from 25 node(s)`. ruff --select E9,F63,F7,F82 on every edited app/scripts file: "All checks passed!".

### 22b.2 Contract

- No flag. After the merge nothing reads ENABLE_SELF_CRITIQUE (an inert retired name: setting it changes nothing; stated limit L-22b-1).
- Main invariant (flag-OFF identity, R-A1 (c) "proven byte-identical"): for every compare path (REST POST / GET, the SSE stream incl. ENABLE_FULL_STREAM_DEADLINE ON) the response body, the SSE event sequence and terminal payloads, the persisted comparisons payload (save_comparison's `full_response` argument) and the follow-up calls are byte-identical to base with ENABLE_SELF_CRITIQUE unset; AND with ENABLE_SELF_CRITIQUE set to true they equal that same base-unset output (inertness), with ZERO dispatch of the `critique` site.
- Kept byte-identical: llm_router ROLE_FLAGS, `_ENTRY_ROLES`, `SITES` (incl. `"critique": SiteSpec("critic", 512, None, True)`), `compare_refuses_for_consent`, `camera_refuses_for_consent`, `any_role_enabled`, `bind_request_scope`; model_config `_ANTHROPIC_ROLE_DEFAULTS`, `anthropic_model`, `resolved_anthropic_models`; migration 030 + rollback; the judge.
- Changed by design: `active_provider_preflight_allows` with a role flag ON and ENABLE_SELF_CRITIQUE true no longer adds the critic's provider (the critic has no dispatch left); `model_config.resolved_models()` loses `critic` (the startup `[models]` INFO line of app/main.py:52-54 loses `critic=gpt-4o-mini`); the persisted comparisons row is the response body verbatim (no stripper: no producer of `_verdict_critique` remains); `track_after_persist` runs three follow-ups (cache bust, track_event, Loop 2).
- Contract freeze (re-read: PLAN_S80 section 0 item 4; contract_freeze.json finding 1 lists `metadata.partial` as the only metadata path build 3 reads): `metadata._verdict_critique` is not a client-read path and was never produced in production (the flag never ON); nothing a client reads is removed, renamed or retyped; no 503 path changes.
- Failure table: none new (code is removed; no new exception path).
- Seams: the orchestrator harness of the house rows (tests/test_arabic_verdict_output_w414.py `_sync_harness`, the S81-18 `_compare` helper, the comparison-id echo `follow_ups` fixture); a recorder on `app.services.llm_router.route` records every routed site key.

### 22b.3 Change list (GREEN applies S81-22c's scs insertion FIRST, then these deletions by anchor text)

1. Byte copies first. 2. `git rm app/services/verdict_critique_service.py tests/test_verdict_critique_service.py tests/test_self_critique_orchestration.py` (the GREEN's own branch). 3. structured_comparison_service.py: the six regions of 1.4 (anchors: `self._regen_model_downgraded: bool = False`; `# I3.1 -- optional self-critique pass` (sync, with its call to the closing parenthesis); `# I3.2 -- thread the self-critique outcome` (sync, 6 lines); `# I3.1 -- optional self-critique pass (flag-gated OFF; no-op in prod).` (stream: through `comparison = await _critique_coro`); `# I3.2` (stream, 6 lines); `async def _apply_self_critique(` through the end of `_verdict_critique_metadata` and one blank line); the prototype applied exactly these six ranges (+8 shift after 22c) with anchor checks. 4. feedback_service.py per 1.4. 5. llm_router.py: `_self_critique_on` and the two-line critic leg + the docstring clause; `importlib` stays used (:175, :280, :851). 6. model_config.py: the OpenAI critic default (2 lines) and `critic_model()` (+ its trailing blank lines). 7. api_budget_service.py:947 (one comment line). 8. scripts/cron_learning.py:100 (the comment reworded, e.g. `# the retired self-critique pass's threshold (S81-22b); PIN P5 holds the literal`). 9. app/legal/processors.json:67 (one line; CRLF kept; json.loads clean). 10. The E-rows EB1-EB13. 11. NEW tests/test_s81_s22b_self_critique_retire.py. 12. No other file.

### 22b.4 Existing pins

4.1 Deliberate changes (each measured red at the prototype without it):
- EB1 tests/test_arabic_verdict_output_w414.py: `_install_recorders` stops the run with a raising recorder on the first call after the verdict on both paths (the GREEN measures which: e.g. `trust_validation_service.validate_verdict`, imported at call time) instead of `_apply_self_critique`; the `regen_args` assertions of test_29 / 29b / 29c are dropped (the `gen` assertions that output_lang reaches generate_comparison stay); test_33 deleted (it pins the retired regen). Red without it: 29, 29b, 29c[sync], 29c[stream], 33.
- EB2 tests/test_comparison_quality_v2.py: the module import :32 and TestCritiqueHedgingExemption (:224-280) deleted. Red: its 3 nodes (collection error for the whole file without the import removal).
- EB3 tests/test_feedback_service.py:26: the `_persist_verdict_critique` setattr removed. Red: test_successful_save_busts_home_savings_cache.
- EB4 tests/test_model_config.py: the three "critic" rows (:28, :36, :44) removed (collection AttributeError otherwise).
- EB5 tests/test_model_config_enforced.py: import :29 removed; the critique_verdict branch (:225-227) and row (:248) removed; floor `>= 16` -> `>= 15` (:148); `test_resolved_models_unchanged` drops "critic" (:282). Red: test_no_call_site_passes_raw_sampling_kwargs, test_gpt5_ids_emit_no_rejected_kwargs[critique_verdict], test_shipped_ids_kwargs_unchanged[critique_verdict], test_resolved_models_unchanged.
- EB6 tests/test_openai_breaker.py: import :81 removed; test_verdict_critique_dispatch_feeds_the_breaker deleted. Red: that node + the collection of four importer files (1.5).
- EB7 tests/test_s70_model_router_downgrade.py: the R2.6 block (test_self_critique_regen_marker x5) deleted; the docstring line :21 reworded.
- EB8 tests/test_s81_d22_nightly_learning.py p5: re-pointed to `scripts/cron_learning.CRITIQUE_THRESHOLD == 7` (literal) and to `bias_score` / `missing_citation_score` being `integer NULL` columns of migrations/030_verdict_critiques.sql (:45, :48), the kept table the job reads (cron_learning :84).
- EB9 tests/test_s81_s06_anthropic_router.py: per 1.5 (12 nodes red otherwise: r04[critique], p01[critique-x6], r14[critique], p10, r39, p07, p13); p07 / p13 re-pointed to another real site (the GREEN picks one whose base kwargs the row already holds).
- EB10 tests/test_s81_s06_router_gate_rows.py: G05 cell `(({"text", "verdict"}, True, False, True), True)` -> `False` (the inertness of ENABLE_SELF_CRITIQUE in the preflight; the other six cells unchanged); G13 `G13_SITE_KEYS` minus "critique", `len(...) == 15`, the docstring's 16 -> 15.
- EB11 tests/test_u3c_store_false_pin.py: `assert sites >= 16` -> `>= 15` (:214) with the message "since S81-22b".
- EB12 tests/test_comparison_id_echo.py: per 1.5 (22 ERROR nodes otherwise: the fixture setattr of a deleted attribute).
- EB13 tests/fixtures/legal_s78.json: the one module line of `manifest_base.openai.module` (:283).
4.2 Must stay green: every other node of those files; test_migration_030_verdict_critiques.py; the legal manifest readers (1.6); tests/test_s81_s22_judge.py (:638 the Claude critic model); the S81-04 / S81-18 / S81-22 files; the source-scanning pins; the SSE contract files (test_streaming.py, test_text_routes_sse_contract.py, test_m13_04_full_stream_deadline.py, test_settle_window_orchestration.py, test_sse_settle_window.py).

### 22b.5 RED tests: tests/test_s81_s22b_self_critique_retire.py

Missing symbols are read with getattr / importlib.util.find_spec helpers (AssertionError-only at base). Every flag-OFF / inertness row runs with the FULL companion configuration (ENABLE_FULL_STREAM_DEADLINE both states, ENABLE_ARABIC_VERDICT_OUTPUT with output_lang ar, ENABLE_COMPARISON_ID_ECHO ON, ENABLE_COMPARE_RUN_LEDGER ON with an insert recorder, ENABLE_LLM_LEDGER_V2 ON, every S81-06 role flag OFF and, in R6, ON) plus a recorder on `llm_router.route` (site keys) and on `database_service.save_comparison` (the persisted payload).

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R1 | module absent | `importlib.util.find_spec("app.services.verdict_critique_service") is None` | RED | the deletion |
| R2 | no reference left | a text scan of app/**/*.py, scripts/**/*.py, data/**/*.json, railway*.json, app/legal/processors.json finds none of: verdict_critique_service, ENABLE_SELF_CRITIQUE, _apply_self_critique, _verdict_critique_metadata, _verdict_critique_outcome, _persist_verdict_critique, _without_verdict_critique, critique_verdict, critique_and_maybe_regenerate, CritiqueResult, persist_critique, is_self_critique_enabled, _self_critique_on, critic_model, _regen_model_downgraded, the quoted key "_verdict_critique" (the table name verdict_critiques is allowed) | RED (54 line hits outside the module, 1.4) | 3-9 |
| R3 | orchestrator surface | `StructuredComparisonService` has no `_apply_self_critique` / `_verdict_critique_metadata`; a fresh instance has no `_regen_model_downgraded` attribute | RED | 3 |
| R4 | save-path surface | feedback_service has no `_persist_verdict_critique`, `_without_verdict_critique`, `critic_model` attributes | RED | 4 |
| R5 | model config | `model_config` has no `critic_model`; `resolved_models()` with every OPENAI_MODEL_* unset == {"moderation": "omni-moderation-latest", "standard": "gpt-4o-mini", "verdict": "gpt-4o", "vision": "gpt-4o-mini"} (literal) | RED (a critic key) | 6 |
| R6 | preflight inertness | role flags text + verdict ON, consent 3, openai breaker OPEN, anthropic CLOSED, ENABLE_SELF_CRITIQUE=true: `scs._llm_preflight_short_circuits()` is False (the G05 harness) | RED (True) | 5 |
| R7 | manifest | processors.json openai row `module` == the base list minus the one path (literal, 6 entries); every other row and every other openai field equal a base literal; json.loads clean | RED (7 entries) | 9 |
| R8 | REST inertness | compare_from_text through the house harness (generate_comparison faked; a fake critique answer available at the `critique` site) with ENABLE_SELF_CRITIQUE=true: the routed site keys contain no "critique"; the normalized body has no `_verdict_critique`; the body equals the same harness's unset body | RED (the critique runs: "critique" in the keys, `_verdict_critique` in metadata) | 3 |
| R9 | SSE inertness | the stream path, same as R8 on the `complete` payload and the event sequence; R9b the same with ENABLE_FULL_STREAM_DEADLINE ON | RED | 3 |
| R10 | persisted payload | through `persist_comparison` with a body carrying NO `_verdict_critique`: save_comparison receives the SAME object (identity) and track_after_persist's follow-ups are [cache_bust, track_event, loop2] | PIN green at base (no key -> same object; the persist call skipped) | unchanged behaviour |
| P1 | OFF identity (FULL config) | unset / "" / false / 0 / off / " FALSE ": REST + SSE bodies, the event list and the persisted payload equal literals recorded at base by the RED agent (the golden tests/fixtures/s81_s22b_flag_off_golden.json, ASCII, LF) | PIN green | 3-4 |
| P2 | tables kept | llm_router ROLE_FLAGS, `_ENTRY_ROLES`, sorted SITES keys and each SiteSpec, and model_config `_ANTHROPIC_ROLE_DEFAULTS` equal base literals; `mc.anthropic_model("critic") == "claude-haiku-5-5"` | PIN green | the KEEP rows of 1.4 |
| P3 | the table kept | migrations/030_verdict_critiques.sql and its rollback LF sha256 equal the base values; no migration added (the migrations/ listing equals the base listing) | PIN green | no migration |

### 22b.6 Mutation table (re-introductions on the HEAD byte copies)

| M | Edit | Killed by |
|---|---|---|
| B-M1 | restore verdict_critique_service.py | R1, R2 |
| B-M2 | restore a no-op `_apply_self_critique` and its sync call | R3, R2 |
| B-M3 | restore `_without_verdict_critique` (identity body) | R4, R2 |
| B-M4 | restore `"critic": "gpt-4o-mini"` in `_ROLE_DEFAULTS` | R5 |
| B-M5 | restore the preflight critic leg reading `os.getenv("ENABLE_SELF_CRITIQUE")` | R6 |
| B-M6 | restore the processors.json line | R7 |
| B-M7 | over-delete `_ANTHROPIC_ROLE_DEFAULTS["critic"]` | P2 (and tests/test_s81_s22_judge.py:638) |
| B-M8 | over-delete `SITES["critique"]` | P2 (and the EB9-kept escalation rows) |
| B-M9 | remove "critic" from ROLE_FLAGS | P2 |
| B-M10 | thread `metadata["_verdict_critique"] = {}` on the sync path when the env var is true | R8 |

### 22b.7 Comm set: within the group set (section 12); plus the manifest readers (1.6) and the importers of the four affected test modules (1.5).

### 22b.8 CLAUDE.md row and owner steps

Row text: "S81-22b SELF-CRITIQUE-RETIRE (no flag; unflagged deletion under R-A1 (c)): the verdict self-critique pass is deleted (`app/services/verdict_critique_service.py`, the orchestrator's I3.1 / I3.2 sites on both paths, `feedback_service` `_without_verdict_critique` / `_persist_verdict_critique`, `model_config.critic_model` and the OpenAI critic role, the router's preflight critic leg, the processors.json module path); `ENABLE_SELF_CRITIQUE` was unset in production (ledger 2026-11-06) and is now an INERT retired name (setting it does nothing). KEPT: migration 030 and the `verdict_critiques` table (read by the D22 learning job; a drop is a later migration unit), the router's `critic` role / `critique` site / `ENABLE_ANTHROPIC_CRITIC` (the S81-06 consent gate) and the Claude critic model (the judge's Haiku). RED tests/test_s81_s22b_self_critique_retire.py; E-rows EB1-EB13."
In-place rewrites (principle 5): :341 the Feature Flags entry `ENABLE_SELF_CRITIQUE` (OFF -- verdict self-critique pass) -> retired by S81-22b (2026-11-xx), inert; :337 and :394 "verdict/critique/moderation tail" -> "verdict/moderation tail"; :387 "verdict + self-critique + moderation each run under" -> "verdict + moderation each run under"; :508 the S81-06 row's routed-site list (16 sites incl. verdict_critique_service and critique -> 15; the `critique` SiteSpec stays without a caller); :780 "The self-critique regen keeps the directive." deleted; :839 the `metadata._verdict_critique` pre-existing leak sentence -> closed (no producer since S81-22b); :846 the W1-3 wired-site list loses verdict_critique_service. Keep :860 (`never --branch production`, pinned by tests/test_ci_gates.py).
Owner steps: none (nothing to flip); optionally remove the name ENABLE_SELF_CRITIQUE from any service (absent on web today).

### 22b.9 Stated limits

- L-22b-1: ENABLE_SELF_CRITIQUE becomes inert; a service that sets it after the merge gets no critique and no log line.
- L-22b-2: the `verdict_critiques` table and migration 030 stay (no writer remains; the D22 learning job reads an empty table); the drop is a migration (FOCUS), follow-up S81-22h.
- L-22b-3: `resolved_models()` and the startup `[models]` log line lose `critic=...` (a log-line change, no response change).
- L-22b-4: the router keeps the `critic` role, the `critique` site and ENABLE_ANTHROPIC_CRITIC (the consent gate counts the critic role when that dark flag is ON); retiring them is a consent-path unit (FOCUS), follow-up S81-22i.
- L-22b-5: with no stripper, a comparisons row would carry `metadata._verdict_critique` only if a body produced before the merge with the flag ON were persisted after it; the flag was never ON in production by any dated line, so no such body exists.
- L-22b-6: the corpus gate cannot see the orchestrator; the identity proof is P1 / R8 / R9 / R10.

### 22b.10 Out of scope: the table drop (migration); the router critic role / site / flag; the verdict prompt; S81-22e / S81-22f.

### 22b.11 Open questions

- Q-22b-1 (DEVIATION from the brief, measured): the brief asks "the router's role table ... without the critic". The role table feeds the S81-06 consent gate (`_ENTRY_ROLES` -> `compare_refuses_for_consent`; ROLE_FLAGS -> `camera_refuses_for_consent`), a FOCUS surface; removing "critic" changes the gate's decision whenever ENABLE_ANTHROPIC_CRITIC is ON and would turn S81-22b FOCUS. The spec KEEPS the role table, the `critique` SiteSpec and the Claude critic model (the judge's Haiku selector, frozen row s22_judge :638) and removes only `_self_critique_on` + the preflight leg. Ruling asked: keep (recommended) or split the router retirement into S81-22i for a Fable session.
- Q-22b-2: EB1's new stop point (the GREEN measures the first post-verdict call on both paths).
- Q-22b-3: the follow-up ids S81-22h (table drop) and S81-22i (router critic retirement) for the DEFECT_LEDGER.

## Unit S81-22c KB-PRODUCT-IDS

### 22c.1 Base state (measured at 90d4ed74)

| # | Where | Measured |
|---|---|---|
| 1.1 | app/services/kb_serve.py:245-342 `classify` | the per-slot view: `_miss()` (:210-213) = {"hit": "miss", "pid": None, ...}; `out["pid"] = product.get("id") if isinstance(product.get("id"), str) else None` (:254); `out["hit"] = "full" if full else "partial"` (:341). The card's product id is `kb_products.id`, TEXT (045 :304 `product_id text REFERENCES public.kb_products (id)`), minted by `kb_service.kb_product_id` (:239-262) = the spine key minus ml: "fragrance|<brand>|<sorted identity tokens>|<concentration>" (spec_spine_service.spine_key :210-240) |
| 1.2 | structured_comparison_service.py:4528-4532 (sync) / :5249-5253 (stream) | under `kb_serve.kb_first_serve_enabled()` (read once per compare) the card task starts and `self._kb_hit_marks = ["miss", "miss"]`, `self._kb_views = [None, None]`; flag OFF sets neither |
| 1.3 | :6106-6123 (`_fetch_product_data`, partial_slot 0 / 1) | `_kb = kb_serve.classify(...)`; on a view: `self._kb_hit_marks[slot] = _kb["hit"]` (:6122), `self._kb_views[slot] = _kb` (:6123) |
| 1.4 | :3968 `_stamp_unit_metadata`, :3992-3997 | `kb_marks = getattr(self, "_kb_hit_marks", None)`; `if kb_marks: metadata["kb_hit"] = list(kb_marks)` (S81-18 H7). Callers: :3928, :4832 (sync), :5759 (stream complete) |
| 1.5 | kb_serve.py:444 (log_verdict_key) | the house predicate for "a slot holds a card id": `isinstance(view, dict) and view.get("hit") in ("full", "partial") and view.get("pid")` |
| 1.6 | app/services/compare_runs.py:440-466 `build_run_row` | `"kb_product_ids": None` (:454) by R-S22-26 (L-KBID); `RUN_COLUMNS` (:53) holds the name; 048 :130-132 `kb_product_ids jsonb NULL CHECK (kb_product_ids IS NULL OR jsonb_typeof(kb_product_ids) = 'array')`; compare_runs imports no kb_service / kb_serve (the P01 fence of tests/test_s81_kb_schema.py) |
| 1.7 | compare_runs.py:192-202 `_sources_used` (MEASURED DEFECT D-S22-K1) | accepts `metadata.kb_hit` only when `all(m in ("hit", "miss") for m in marks)`; the producer writes "full" / "partial" / "miss" (1.1, pinned by tests/test_s81_s18_kb_first_serve.py:785 `["full", "full"]`, :817 `["partial", "miss"]`, :894 `["miss", "miss"]`), so every real KB hit is recorded as `sources_used.kb_hit = None` once both flags are ON; only ["miss", "miss"] survives. The frozen S81-22 rows use the synthetic ["hit", "miss"] (tests/test_s81_s22_compare_runs.py:649-678) |
| 1.8 | the de-identification evidence | the run row already stores product identity text: the evidence snapshot's winner name (compare_runs.py:379) and per-product entries (:394); a KB product id (brand + identity tokens + concentration of a catalogue juice) is catalogue data, not personal data, and adds no new category to the row (no user id, query text, device id or profile) |
| 1.9 | key-set pins under ENABLE_KB_FIRST_SERVE ON | tests/test_s81_s18_kb_first_serve.py R10 / R11 / R12 assert `kb_hit` values only; R20 (:885-897, both slots miss) pops `kb_hit` then asserts `on == off` (stays green when the new key is ABSENT on a both-miss compare); tests/test_s81_g4_gate_rows.py:79 asserts kb_hit only; the shared G8 golden tests/fixtures/s81_g8_flag_off_golden.json records full payloads with ENABLE_KB_FIRST_SERVE ON and kb_hit ["full", "full"] in 10 scenario payloads (truth_true / truth_unset x camera_full / rest_ar / rest_full / stream_full x2; g8golden_probe.py), compared whole by tests/test_s81_s11b_result_aggregates.py::test_p1_flag_off_golden_full_config (:340-355) and tests/test_s81_s18b_store_label.py::test_p1_flag_off_golden_full_config (:427-441) |
| 1.10 | client readers | none: no SmartCompareApp/src or __tests__ file reads `kb_hit` / `kb_product*` or enumerates `metadata` keys (`git grep`); the client v2 response fixtures are static recordings |
| 1.11 | camera / URL exits | the camera compare runs through the same orchestrator, so it carries the key under the flag exactly like kb_hit; the URL compare is not a KB-first path; the comparison-id link of those exits is S81-22f (split out) |
| 1.12 | history / share | the key rides `full_response.metadata` into the saved comparisons row under the flag (as kb_hit does today); the public share strips personalization only (stated limit) |

1.13 Prototype: the 8-line insertion + the row helper (proto_apply.py, `22c`) turned exactly two frozen nodes red: tests/test_s81_s11b_result_aggregates.py::test_p1_flag_off_golden_full_config and tests/test_s81_s18b_store_label.py::test_p1_flag_off_golden_full_config (`[pyt] tag=g10spec-protoA start=2026-11-09 17:10:53 end=2026-11-09 17:11:23 elapsed=30s bound=600s status=FAIL rc=1`, 10 failed / 564 passed over the S81-22 / S81-04 / S81-18 / G4 / G8 files: the 5 J1 nodes before EJ1, the 2 G8 P1 nodes, the 3 environmental CRLF nodes); test_s81_s18 R20 stayed green (the key absent on both-miss).

1.14 Base pass state: `[pyt] tag=g10spec-baseB start=2026-11-09 17:04:29 end=2026-11-09 17:05:02 elapsed=33s bound=600s status=FAIL rc=1` (test_s81_s04_spend_breaker, test_s81_s18_kb_first_serve, test_s81_g4_gate_rows, test_s81_s11b_result_aggregates, test_s81_s18b_store_label, test_s81_g8_gate_rows, test_s77_redis_offloop: 517 passed / 1 failed = s18b r2 CRLF environment); `[hermeticity] sentinel checked 518 test(s)`; `[netguard] blocked 24 attempt(s) from 2 node(s)` (s04 r42 / p08: neutralized supabase.invalid).

### 22c.2 Contract

- Flags: none new. The key rides ENABLE_KB_FIRST_SERVE (through `_kb_hit_marks`, set only when the flag started the card task: the flag is not re-read); the row field rides ENABLE_COMPARE_RUN_LEDGER (`record_compare_run`'s first statement).
- NEW additive key `metadata.kb_product_ids`: a list of EXACTLY two elements; element i = slot i's KB card product id (a non-empty str, the view's `pid`) when that slot's view hit is "full" or "partial", else null. Written in `_stamp_unit_metadata` right after the kb_hit stamp, ONLY when `kb_marks` is truthy AND at least one element is a str; absent otherwise (both-miss compares carry no key, so R20 and every both-miss pin stay byte-identical). `kb_hit` is never reshaped.
- compare_runs: `build_run_row` writes `kb_product_ids` = `_kb_product_ids(meta)`: the metadata list when it is a list of length 2; each element kept only when a str of length 1..256, else null; NULL when no element survives or the shape is wrong. No kb_service / kb_serve import (P01).
- D-S22-K1 (in scope, Q-22c-1): `_sources_used` accepts the producer vocabulary: a mark is valid when in ("full", "partial", "miss", "hit") ("hit" kept so the frozen synthetic rows stay green; an allowlist widening, R-A1 (a)); any other mark or length -> None as today.
- Flag-OFF identity: ENABLE_KB_FIRST_SERVE OFF -> no `_kb_hit_marks` -> no key: REST / SSE bodies byte-identical (the S81-18 OFF pins, P1); ENABLE_COMPARE_RUN_LEDGER OFF -> no row, no insert, no build (the S81-22 OFF pins).
- Failure table: a malformed view (no dict, no pid, a non-str pid, an empty pid) -> null for that slot; both null -> no key; `_kb_views` absent or short -> padded with null; `build_run_row` never raises on the key (a wrong shape -> NULL).
- Contract freeze (re-read: PLAN_S80 section 0 item 4; runs/research/contract_freeze.json finding 1, whose only metadata path build 3 reads is `metadata.partial`): the key is ADDITIVE, under a dark flag, read by no client; no error path or 503 is added or changed.
- Seams: the S81-18 harness (`_compare(monkeypatch, "rest"|"stream")`, `_on(monkeypatch, cards)`, `_card`, `_full_config`), the S81-22 row builder (`build_run_row(result, input_type, ...)`).

### 22c.3 Change list

1. Byte copies first. 2. structured_comparison_service.py `_stamp_unit_metadata`, inside `if kb_marks:` after :3997 (the prototype's 8 lines): build the two-element list from `getattr(self, "_kb_views", None)` padded to 2 with the 1.5 predicate; `if any(ids): metadata["kb_product_ids"] = ids`. Applied FIRST (0.3). 3. compare_runs.py: the `_kb_product_ids(meta)` helper (beside `_cache_hits`), :454 -> `_kb_product_ids(meta)`, :194 the widened mark set. 4. EC1 tests/test_s81_s11b_result_aggregates.py and EC2 tests/test_s81_s18b_store_label.py: the P1 rows drop `metadata.kb_product_ids` from every scenario payload before the comparison AND assert its value where present (`[P0_ID, P1_ID]` for the full/full scenarios), so the rows keep pinning the G8 flags' OFF identity; the golden file is NOT re-recorded (Q-22c-2). 5. NEW tests/test_s81_s22c_kb_product_ids.py. 6. No other file.

### 22c.4 Existing pins

4.1 Deliberate: EC1, EC2 (above; measured red on the prototype). No other frozen row moves: R20 (both miss) by design; tests/test_s81_s22_compare_runs.py:682 (`kb_product_ids is None` for a body without the key) stays green; :649-678 (synthetic ["hit", "miss"]) stays green under the widened set.
4.2 Must stay green: tests/test_s81_s18_kb_first_serve.py, test_s81_g4_gate_rows.py, test_s81_g8_gate_rows.py, test_s81_s22_compare_runs.py, test_s81_s22_gate_rows.py, test_s81_kb_schema.py (P01), the G8 flag-OFF rows other than P1.

### 22c.5 RED tests: tests/test_s81_s22c_kb_product_ids.py

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R1 | REST full/full | KB ON, both cards full: `metadata.kb_product_ids == [P0_ID, P1_ID]` (the cards' `product.id`) and `metadata.kb_hit == ["full", "full"]` unchanged | RED (absent) | 2 |
| R2 | stream full/full | the `complete` payload carries the same list | RED | 2 |
| R3 | partial / miss | `[P0_ID, None]` with kb_hit ["partial", "miss"] | RED | 2 |
| R4 | camera path | the camera compare (vision products) carries the key like kb_hit | RED | 2 |
| R5 | row from the key | `build_run_row` over a body with `metadata.kb_product_ids == [id, None]` -> row `kb_product_ids == [id, None]` | RED (None) | 3 |
| R6 | D-S22-K1 | a body with kb_hit ["full", "miss"] -> `sources_used.kb_hit == ["full", "miss"]`; ["partial", "partial"] kept | RED (None) | 3 |
| R7 | end to end | ENABLE_KB_FIRST_SERVE + ENABLE_COMPARE_RUN_LEDGER ON, a full/miss compare through text POST: the insert recorder's row `kb_product_ids == [P0_ID, None]` and `sources_used.kb_hit == ["full", "miss"]` | RED | 2 + 3 |
| P1 | KB OFF identity (FULL config) | ENABLE_KB_FIRST_SERVE unset / "" / false / 0 / off / " FALSE " with ENABLE_COMPARE_RUN_LEDGER both states, ENABLE_RESULT_AGGREGATES / ENABLE_STORE_LABEL both states: no `kb_product_ids` anywhere in REST / SSE bodies; the bodies equal the S81-18 OFF golden (tests/fixtures/s81_s18_flag_off_golden.json through the S81-18 `_golden_snapshot` helper) | PIN green | unchanged |
| P2 | both miss | KB ON, both cards absent (and the raising-RPC case of R20): no key; kb_hit ["miss", "miss"] | PIN green | design |
| P3 | shapes | `_kb_product_ids`-equivalent outcomes through `build_run_row`: absent key / non-list / length 3 / [None, None] / ["", None] / [1, None] / a 257-char str -> NULL or the element nulled; never raises | PIN green at base (NULL always) | 3 |
| P4 | P01 | compare_runs.py imports no kb_service / kb_serve (top level or lazy) | PIN green | 3 |
| P5 | ledger OFF | ENABLE_COMPARE_RUN_LEDGER OFF with KB ON: zero insert, zero build | PIN green | unchanged |

### 22c.6 Mutation table

| M | Edit | Killed by |
|---|---|---|
| C-M1 | drop the stamp | R1-R4, R7 |
| C-M2 | stamp also when both null | P2 (and test_s81_s18 R20) |
| C-M3 | accept "miss" views' pid | R3 (a miss view has pid None; use a card whose classify misses with a product id present: the RED builds it) |
| C-M4 | reshape kb_hit to ids | R1 (kb_hit asserted unchanged) |
| C-M5 | `build_run_row` keeps None | R5, R7 |
| C-M6 | widening reverted | R6, R7 |
| C-M7 | widen to any str | P3-style row on kb_hit ["bogus", "miss"] -> None (add it to R6) |
| C-M8 | stamp outside `if kb_marks:` (flag OFF) | P1 |

### 22c.7 Comm set: within the group set; the S81-18 / G4 / G8 / S81-22 files; the camera route importers.

### 22c.8 CLAUDE.md row and owner steps

Row text: "S81-22c KB-PRODUCT-IDS (no new flag): under `ENABLE_KB_FIRST_SERVE` the compare body gains the additive `metadata.kb_product_ids` = [the KB card product id of slot 0 or null, of slot 1 or null] for a compare where at least one slot served a full or partial card (absent otherwise; `kb_hit` unchanged); under `ENABLE_COMPARE_RUN_LEDGER` `compare_runs.kb_product_ids` is written from it (NULL when absent; no kb_service import, P01) and `sources_used.kb_hit` now records the producer marks full / partial / miss (D-S22-K1: the run row dropped every real hit). Both flags unset: byte-identical. RED tests/test_s81_s22c_kb_product_ids.py; E-rows EC1 / EC2 (the G8 golden P1 rows set the new key aside)."
Owner steps: none to merge; the key appears only after the ENABLE_KB_FIRST_SERVE flip, the row field only after ENABLE_COMPARE_RUN_LEDGER (their own preconditions unchanged).

### 22c.9 Stated limits

- L-22c-1: under ENABLE_KB_FIRST_SERVE the ids are stored with the saved comparison (history, public share) like kb_hit; they are catalogue ids, not personal data.
- L-22c-2: a both-miss compare writes no key, so the run row's NULL means "no KB card id" (the miss marks stay in sources_used.kb_hit).
- L-22c-3: the camera and URL exits are unchanged here (S81-22f links them).
- L-22c-4: rows written before the merge keep `sources_used.kb_hit` NULL for hits (no backfill; the ledger flag is OFF, so no such row exists).

### 22c.10 Out of scope (SPLIT OUT, new ids)

- S81-22e REFUSAL-ROWS: compare_runs rows with `refusal_reason` at the refusal exits (R-S22-14); precondition "after the canary says it matters" unmet (ENABLE_COMPARE_RUN_LEDGER not flipped); the refusal exits refund with consumed_keys (the quota path): FOCUS by surface.
- S81-22f CAMERA-URL-LINK: the comparison id on the camera / URL exits once ENABLE_COMPARISON_ID_ECHO covers them (the L-LINK half of R-S22-26); it widens a response contract on the quota-path exits and the account link of stored runs: classified at its own brief by a Fable session.

### 22c.11 Open questions

- Q-22c-1: D-S22-K1 in S81-22c (recommended: one line, dark, the same row builder) or split to its own id.
- Q-22c-2: EC1 / EC2 as the narrow "set the key aside and assert it" edits (recommended) or re-record the shared G8 golden.
- Q-22c-3: the key name `kb_product_ids` (mirrors the 048 column and PLAN_S81) instead of the brief's example `kb_card_ids`.

## Unit S81-04d SPEND-DURABLE-RETRIEVE

### 04d.1 Base state (measured at 90d4ed74)

| # | Where | Measured |
|---|---|---|
| 1.1 | app/services/llm_spend_breaker.py:862-868 `_run_bounded_async` | `future = asyncio.wrap_future(_get_llm_spend_pool().submit(fn, *args))`; `awaitable = asyncio.shield(future) if durable else future`; `return await asyncio.wait_for(awaitable, redis_timeout_seconds())` |
| 1.2 | callers | only `_record_task` (:1135-1149, `durable=True`) <- `record_soon` (:1152-1179, a `fire_and_forget` task registered for the W1-6 drain) <- `record_openai_response_soon` (:1287-1303, the guarded_llm_create chokepoint, only with ENABLE_LLM_SPEND_BREAKER ON) and llm_router.py:1025 (the Anthropic dispatch, role flags ON and a bound); `settle` (:1224-1258) and `record` (:1102-1132) use `_run_bounded_sync` |
| 1.3 | `_record_job` :1001-1016 | a failed EVAL calls `_record_finished(flight, type(exc).__name__)` then re-raises; `_record_finished` (:785-807) reports a late failure through `_record_failed` (:645-660: the fail-open count once per window + the rate-limited WARNING) and a late success through ONE INFO line `[SPEND] late record landed -- recorded after its bound expired` |
| 1.4 | the pinned interpreter: CPython 3.12.9 (C:/Users/SynAckITPC/AppData/Local/Programs/Python/Python312/Lib/asyncio/tasks.py) | `shield` :898-925: `_inner_done_callback` would retrieve `inner.exception()` when the outer is cancelled (:906-910), but `_outer_done_callback` REMOVES that callback when the outer finishes first (:922-924); a `wait_for` timeout or a task cancel finishes the outer first, so a later failure of the inner (wrapped) future is never retrieved |
| 1.5 | the leak probe (<scratchpad>/S81-G10/s04d_leak_probe.py, the real `_run_bounded_async`, LLM_SPEND_REDIS_TIMEOUT_SECONDS=0.05, a pool job sleeping 0.3 s, a loop exception-handler recorder, gc.collect) at BASE | late raise after the bound: TimeoutError to the awaiter and the handler receives `Future exception was never retrieved`; awaiter cancelled + late raise: the same message; late success: none; an in-bound raise: propagates (RuntimeError), none. PROTOTYPE (the 04d edit): none in all four cases |
| 1.6 | the shield sweep over app/ and scripts/ | app/utils/redis_offloop.py:115 and :140 retrieve (`fut.add_done_callback(_retrieve_quietly)` :114 / :139; `_retrieve_quietly` :96-100); app/services/auth_throttle.py:366 retrieves (`job.add_done_callback(_durable_done(...))` :364; `_done` :335-345 always calls `fut.exception()`, S81-24 F1-1); llm_spend_breaker.py:867 does NOT (fixed here). The durable=True callers algolia_service :240 / :291, price_service :15333 / :15371, review_service :712 go through redis_offloop (retrieved); auth_throttle :479 / :492 through its own `_run`. The breaker's read path (`_follow` :896-920) copies into a follower that wait_for cancels; `_copy` returns when the follower is done (:904-905): no unretrieved exception. Nothing to record by name |
| 1.7 | the leaf import rule tests/test_s81_s04_spend_breaker.py:612-643 (R01) | top-level app imports limited to cache_service, llm_pricing, openai_pricing, async_utils: a top-level `from app.utils import redis_offloop` would turn R01 red; hence a LOCAL twin of `_retrieve_quietly` (no import) |
| 1.8 | production reachability | ENABLE_LLM_SPEND_BREAKER unset on web (no async record at all); the judge service runs it =true but only through the sync calls: `_resume` -> `br.record` (:539), `_haiku_batch` -> `br.reserve` / `br.settle` / `br.record` (:731-780), `_escalate` -> `br.reserve` / `br.settle` / `br.record` (:676-696): all `_run_bounded_sync` (a `concurrent.futures` wait, no event loop), never `_run_bounded_async` |

1.9 Base pass state: tests/test_s81_s04_spend_breaker.py is inside g10spec-baseB (22c.1.14: green). Prototype: the same chunk green for the s04 file (g10spec-protoA), R01 green (no new import).

### 04d.2 Contract

- No new flag (rides ENABLE_LLM_SPEND_BREAKER through its callers). Log-only under R-A1 (b).
- The change: a module-level `_retrieve_quietly(fut)` in llm_spend_breaker.py, the house body of app/utils/redis_offloop.py:96-100 (`if not fut.cancelled(): fut.exception()`), attached with `future.add_done_callback(_retrieve_quietly)` ONLY when `durable` and BEFORE `asyncio.shield(future)`.
- Invariants (byte-identical): every admit / record / refuse / reserve / settle decision, every counter (`late_records`, `fail_open`, the in-flight sums), the late-record INFO line, the fail-open WARNING lines, the W1-6 drain registration, the shield (a durable write still lands after the outer cancel), the non-durable path, the pool, the keys, the Lua script and EXPIREAT. NO new log line (a late failure is already reported once by `_record_finished` -> `_record_failed`).
- Failure table: late failure -> no 'never retrieved' ERROR, the existing fail-open accounting; late success -> the existing INFO line once; a cancelled inner future -> the callback returns without touching it (never `.exception()` on it); an in-bound failure -> propagates to `_record_task` as before.
- Seams: the real `_run_bounded_async` / `record_soon` with a fake Redis client (the S81-04 file's fakes), `LLM_SPEND_REDIS_TIMEOUT_SECONDS` small, a loop exception-handler recorder, caplog, and `_get_llm_spend_pool` monkeypatched to an executor whose `submit` returns a test-controlled `concurrent.futures.Future` (for the cancelled case).

### 04d.3 Change list

1. Byte copies first. 2. app/services/llm_spend_breaker.py: `_retrieve_quietly` defined immediately before `_run_bounded_async` (the prototype's 7 lines incl. a docstring naming the house form); `_run_bounded_async` gains `if durable: future.add_done_callback(_retrieve_quietly)` (+2 lines). CRLF kept. 3. NEW tests/test_s81_s04d_durable_retrieve.py. 4. No other file (no E-row: measured, the S81-04 file stays green incl. R01).

### 04d.4 Existing pins: 4.1 none. 4.2 tests/test_s81_s04_spend_breaker.py entire (R01 import rule, the F1-4a late-record rows :2235-2258, the drain rows), test_s77_redis_offloop.py, test_shutdown_drain.py, tests/test_s81_s24_auth_throttle.py (the F1-1 twin), tests/test_s81_s06_anthropic_router.py (record_soon after a Claude dispatch).

### 04d.5 RED tests: tests/test_s81_s04d_durable_retrieve.py

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R1 | late failure after the bound | `_run_bounded_async(job, durable=True)` with a job that raises after the bound: the awaiter gets TimeoutError; after the job ends + gc.collect, the loop exception handler recorded NO 'Future exception was never retrieved' | RED (one record) | 2 |
| R2 | awaiter cancelled, late failure | the same with the awaiting task cancelled | RED | 2 |
| R3 | through record_soon | `record_soon("live", 0.2)` with a fake Redis whose EVAL raises after the bound: no 'never retrieved' record; `llm_spend_fail_open` +1 exactly once; caplog holds no line beyond the base set (literal) | RED (the handler record) | 2 |
| R4 | the twin | `ast.dump` of llm_spend_breaker `_retrieve_quietly`'s body equals redis_offloop `_retrieve_quietly`'s body; `_run_bounded_async` attaches it inside `if durable` before the shield (AST) | RED (no function) | 2 |
| P1 | late success | a job landing after the bound: the record lands (fake store value), ONE `[SPEND] late record landed` INFO line, `late_records` +1, no handler record | PIN green | unchanged |
| P2 | cancelled inner | `_get_llm_spend_pool` patched to an executor returning a controlled concurrent Future, cancelled before it runs: no handler record, no exception from the callback | PIN green (no callback at base) | the cancelled guard |
| P3 | in-bound failure | propagates to the caller exactly as base (the exception type), no handler record | PIN green | unchanged |
| P4 | non-durable | `durable=False` path: no callback attached (the wrapped future's callbacks unchanged), wait_for timeout behaviour unchanged | PIN green | design |
| P5 | the import rule | R01's rule holds (no new top-level import) | PIN green | local twin |

### 04d.6 Mutation table

| M | Edit | Killed by |
|---|---|---|
| D-M1 | no attach | R1, R2, R3 |
| D-M2 | the twin without the cancelled guard | P2 (`.exception()` on a cancelled future raises CancelledError inside the callback: 'Exception in callback') |
| D-M3 | attach only when not durable | R1, R2, R4 |
| D-M4 | the callback logs a WARNING | R3 (no new line) |
| D-M5 | attach for both branches | EQUIVALENT (a non-durable future is either awaited directly or cancelled by wait_for): reported for a ruling; R4's AST clause pins the `if durable` form |

### 04d.7 Comm set: within the group set (llm_spend_breaker importers: api_budget_service, llm_router, the scripts with offclock lanes, the S81-04 / S81-06 / S81-22 / S81-16 files).

### 04d.8 CLAUDE.md row and owner steps

Row text: "S81-04d SPEND-DURABLE-RETRIEVE (no new flag; rides `ENABLE_LLM_SPEND_BREAKER`; log-only under R-A1 (b)): `llm_spend_breaker._run_bounded_async(durable=True)` attaches the house quiet retrieval (`_retrieve_quietly`, the `app/utils/redis_offloop.py` form) to the shielded pool job, so a record EVAL that fails after its awaiter's bound (or cancel) no longer logs `Future exception was never retrieved` (CPython 3.12 `asyncio.shield` drops its inner callback once the outer is cancelled); the late failure is still counted once as a fail-open; every decision, counter and line is unchanged. RED tests/test_s81_s04d_durable_retrieve.py. ID NOTE: the S88 follow-up called 'S81-04b (the spend breaker's durable write)' is S81-04d; S81-04b stays the /url/compare entry check (FOCUS)."
Owner steps: none.

### 04d.9 Stated limits

- L-04d-1: production web never takes this path (the breaker is OFF); the judge uses the sync path; the fix matters from the breaker flip on.
- L-04d-2: the local twin duplicates three lines of redis_offloop (the leaf import rule forbids the import); R4 pins the two bodies equal.

### 04d.10 Out of scope: S81-04b (the /url/compare entry check, FOCUS), S81-04c (the exc_info ERROR downgrades).

### 04d.11 Open questions: Q-04d-1 the local twin (recommended) vs a lazy in-function import of `redis_offloop._retrieve_quietly` (R01-compatible, imports a private name on every durable call).

## 12 THE GROUP

### 12.1 The comm set (the union rule; derived by <scratchpad>/S81-G10/comm.py, read-only, AST + text, at 90d4ed74)

- Seeds (edited or deleted modules): app.services.structured_comparison_service, app.services.llm_router, app.services.feedback_service, app.services.model_config, app.services.api_budget_service (comment), app.services.llm_spend_breaker, app.services.compare_runs, scripts.cron_compare_judge, app.services.verdict_critique_service (deleted); scripts/cron_learning.py (comment) and app/legal/processors.json join through their readers below.
- (a) The transitive importer closure over app/ and scripts/ to a FIXPOINT (every `import x`, `from pkg import mod` resolved to the submodule, `from . import`, and every string literal naming an app./scripts. module = the importlib form): 108 modules incl. app.main and every app/api router (closure.txt). (b) Every tests/test_*.py importing or naming a closure module, (c) every app.main / TestClient user, (d) the symbol references (the retired identifiers of 22b.1.4, kb_hit, kb_product_ids, _kb_views, _stamp_unit_metadata, build_run_row, record_compare_run, _sources_used, _run_bounded_async, record_soon, _record_task, _record_job, _retrieve_quietly, cron_compare_judge, batch_pending, compare_judgements, ENABLE_BATCH_JUDGE, processors.json, verdict_critiques, ENABLE_ANTHROPIC_CRITIC, resolved_models, active_provider_preflight_allows), (e) the named source-scanning pins (tests/test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py, test_start_command.py), (f) every module-path / glob / path-segment / ast.parse / getsource / os.listdir / scandir reader, (g) the CLAUDE.md readers by the import graph (tests/test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py; 38 files mention CLAUDE.md, all in the set), (h) the manifest readers (22b.1.6), (i) the SmartCompareApp-scanning backend tests (the additive response key), (j) every test importing a member test module (the importer chains of 22b.1.5 included). MINUS the four tests/test_precommit_hook*.py.
- RESULT: 726 members of the 764 tests/test_*.py at base; set sha256 `f963d6dc3e690e244bf1a54242ba4a34514f33cd6682f2054ff8ea7c9293d8de` over the LF, Python-sorted list (<scratchpad>/S81-G10/comm/comm_set.txt). Excluded (38): the four precommit-hook files + tests/test_abuse_detection.py, test_abuse_detection_internals.py, test_attribution_service.py, test_attribution_service_edges.py, test_audit_logging.py, test_bundle_e_integration.py, test_cohort_service.py, test_cohort_snapshots.py, test_confidence_service.py, test_d2_spec_parity_per_category.py, test_database_service.py, test_db_improvements.py, test_demographics_rls.py, test_drug_database_service.py, test_feature_bucket.py, test_history.py, test_integration.py, test_lane2_integration.py, test_m13_02_proxy_aware_ratelimit.py, test_m13_05_sync_db_offload.py, test_migration_023.py, test_pain_workflow_loader_edges.py, test_personality_edge_cases.py, test_probe_truth_freshness_match.py, test_product_type_router.py, test_quality_ranker.py, test_retro_w0_1.py, test_scoring_v2_models.py, test_sentry_503_suppression.py, test_sentry_service.py, test_spec_parity.py, test_subtype_spec_reconciliation.py, test_verdict_builder.py, test_verdict_exemplar_loader.py (none imports, names or path-reads a seed, the closure or a G10 symbol). The GREEN re-derives the set at HEAD: the base set minus the two deleted suites plus the four RED files (and any file a RED imports).
- The fourteen backend-scanning client fences + b3a: none reads a file G10 edits (measured: brand/inAppMark.u4c reads app.json / docs/brand / scripts/render_myez_icons.py; clientTruth/privacyManifest.s74 reads docs/privacy-data-inventory.md; clientTruth/shareTruth.s74 reads app/services/referral_service.py; landing.domain.s76 reads landing/ + app/services/robots_eval.py + sitemap_discovery_service.py; config/nativeBundle.w37 reads app.json / assets / eas.json / babel / locales; ResultsScreen.timeout, honestCounts.s69, onboarding/step05Trust.s69, medicalNote.s74, navigation/linking.w315 read SmartCompareApp/src only; DimensionBars.perCategory, clipboardFallbackService(+.edges), playInstallReferrerService(+.edges) name backend files in comments only). They still run BY PATH through the orchestrator's junction at GREEN and at every rebase (app/ and scripts/ are edited), expected green and unchanged.

### 12.2 The base record at 90d4ed74 (LC-6, GC-9 per-file reuse; the PLAN, built by the RED round as its LAST step)

- Reuse (330 members, reuse_plan.tsv): 317 from f4461556/e18102fb... (708 members; unchanged f4461556 -> 90d4ed74; naming none of scrapedo_service / source_router / structured_comparison_service / seed_kb_brands_wikidata / cron_kb_coverage / ab_render_providers / auth_routes / request_id / auth_throttle / _env_safety / CLAUDE.md / docs/policies / the WDQS ruling; no app.main / TestClient user; no glob / dir walker) + 13 from 39ac80ba (fe55771e... 673 / 99bacbe8... 382) under the same rule plus the S81-24 module exclusion; their FAILED node ids copied from the stored .txt files.
- Run at 90d4ed74 (396 members): reasons (overlapping) = names a 90d4ed74 / f4461556-touched module or CLAUDE.md (346), app.main / TestClient user (148), glob / dir walker (45), not in a stored record or changed since it (8), names an S81-24 module (1). 16 chunks of <= 25 files, bound 1200, one pytest at a time, in a detached junction-free scratch worktree at 90d4ed74, removed afterwards; stored at <scratchpad>/harness/base_records/90d4ed74bdd16f62130dc9f7a4727620f8a1cea2/f963d6dc3e690e244bf1a54242ba4a34514f33cd6682f2054ff8ea7c9293d8de.{files,txt,header.txt,pyt.log} with the [pyt] lines and the reused-vs-run split.
- Expected base FAILED entries already known: the three CRLF-environment nodes (22c.1.14 / J1.1.14), test_prompt_truth x2 ERROR, test_s81_s10_fragrance_gate r06, the stored f4461556 list (27 ids) where reused.
- GREEN: the HEAD set in the same chunks; `comm -13` of the sorted FAILED sets EMPTY; a branch-only-new failure is re-run against base once to tell a flake.

### 12.3 The CI-order set (ONE pyt call, bound 1200, files in CI's alphabetical order)

tests/test_arabic_verdict_output_w414.py, test_comparison_id_echo.py, test_comparison_quality_v2.py, test_cost_meter_s74.py, test_feedback_service.py, test_health_loop_lag.py (a lifespan user ahead of every RED file, the S88 P73 lesson), test_legal_docs_u8.py, test_legal_s78.py, test_migration_030_verdict_critiques.py, test_model_config.py, test_model_config_enforced.py, test_openai_breaker.py, test_retro_w1_3.py, test_s70_model_router_downgrade.py, test_s81_d22_nightly_learning.py, test_s81_g8_gate_rows.py, test_s81_s03_llm_ledger_v2.py, test_s81_s04_spend_breaker.py, test_s81_s04d_durable_retrieve.py, test_s81_s06_anthropic_router.py, test_s81_s06_router_gate_rows.py, test_s81_s11b_result_aggregates.py, test_s81_s18_kb_first_serve.py, test_s81_s18b_store_label.py, test_s81_s20_result_gate.py, test_s81_s22_compare_runs.py, test_s81_s22_gate_rows.py, test_s81_s22_judge.py, test_s81_s22b_self_critique_retire.py, test_s81_s22c_kb_product_ids.py, test_s81_s22d_ledger_pins.py, test_s81_s22j1_judge_jsonb_filter.py, test_u3c_store_false_pin.py (33 files: <= 25 per chunk does not apply to the CI-order set; if the bound is at risk the GREEN splits it in TWO calls at test_s81_s04d, keeping the lifespan user first in each). Run once at base (the RED round; the new RED files RED, everything else as the base record) and at HEAD (GREEN).

### 12.4 The combined footprint (the prototype's `git diff --stat` of the code edits: 14 files, +31 / -1350 incl. the two deleted suites)

| File | Unit | Kind |
|---|---|---|
| scripts/cron_compare_judge.py | J1 | 1 line |
| app/services/verdict_critique_service.py | 22b | DELETED (391 lines) |
| app/services/structured_comparison_service.py | 22b + 22c | -186 / +8 |
| app/services/feedback_service.py | 22b | about -68 |
| app/services/llm_router.py | 22b | -10 |
| app/services/model_config.py | 22b | -7 |
| app/services/api_budget_service.py | 22b | -1 (comment) |
| scripts/cron_learning.py | 22b | 1 comment line |
| app/legal/processors.json | 22b | -1 |
| app/services/compare_runs.py | 22c | about +10 / -2 |
| app/services/llm_spend_breaker.py | 04d | +10 |
| tests (RED x4 NEW; DELETED x2; E-rows EJ1, EJ2, EB1-EB13, EC1, EC2) | all | test-only |
| CLAUDE.md | all | the G10 block + in-place rewrites (12.6) |

Corpus gate at the prototype HEAD (all four units' code edits applied; the same eight-name flag list; alone; 17:17:59-17:25:40): `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656`, `OVERALL SHA256 387fa35c600f6ea9f049d38a84966f435b9827ed2ed636c0144b7b56f1d09181` = EQUAL to base. GREEN re-runs it at HEAD (EQUAL expected).

### 12.5 The shared-file plan (GREEN order)

1. scripts/cron_compare_judge.py (J1) and the J1 RED + EJ1 + EJ2. 2. app/services/llm_spend_breaker.py (04d) + its RED. 3. structured_comparison_service.py: S81-22c's insertion FIRST, then S81-22b's six deletions by anchor (0.3). 4. compare_runs.py (22c) + EC1 / EC2 + the 22c RED. 5. The 22b deletions in feedback_service / llm_router / model_config / api_budget_service / cron_learning / processors.json + the module + the two suites + EB1-EB13 + the 22b RED. 6. CLAUDE.md LAST. Each step CRLF-preserving; `git diff --stat` hunks only; ruff --select E9,F63,F7,F82 + py_compile on every edited Python file; json.loads on processors.json and legal_s78.json; bytes > 127 == 0 in every NEW file; no 64-hex literal beside a gitleaks-keyword name (S22_LF_SHA is keyword-free).

### 12.6 CLAUDE.md (GREEN, last)

- The G10 block after the S81-G9 block (the G9 block ends at :629, `## Tests` at :630), one blank line before its heading: "**SESSION 81 units (S81-G10 FOLLOWUPS: D-S22-J1 JUDGE-JSONB-FILTER + S81-22b SELF-CRITIQUE-RETIRE + S81-22c KB-PRODUCT-IDS + S81-04d SPEND-DURABLE-RETRIEVE, 2026-11-xx; NO new flag; the tenth SAFE group under LC-9; orchestrator Opus 5.5 by the owner's ruling of 2026-11-07; spec .qa-s80/S81-G10_UNIT_SPEC.md, rulings specs/RULINGS_S81_G10.md, gate specs/GATE_S81_G10.md):**" then the four rows of J1.8, 22b.8, 22c.8, 04d.8 and one owner-steps bullet (J1's DRY re-read; nothing to flip).
- :341 the pointer clause gains, after the S81-G9 sentence: "S81-G10 FOLLOWUPS adds no flag (D-S22-J1 rides `ENABLE_BATCH_JUDGE`, S81-22c rides `ENABLE_KB_FIRST_SERVE` / `ENABLE_COMPARE_RUN_LEDGER`, S81-04d rides `ENABLE_LLM_SPEND_BREAKER`; S81-22b retires `ENABLE_SELF_CRITIQUE`): the rows of the **SESSION 81 units (S81-G10 FOLLOWUPS, ...)** block."; the same line's `ENABLE_SELF_CRITIQUE` (OFF -- verdict self-critique pass) entry rewritten as retired (22b.8).
- The 22b in-place rewrites of 22b.8 (:337, :387, :394, :508, :780, :839, :846).
- The rows that LAG after the first production OTA (ledger 2026-11-07 16:10 / 16:11: published from main f1e20c39, update group 08de6433-3883-4c4d-bada-fb450ba29100, branch production, runtime 1.0.0; the bundle = S81-08 + S81-11 + D20 + CL2 + the SF1 line + S81-11e; consent v3 / S81-12 NOT in it), each rewritten in place with that dated truth: :255 "the `production` channel had never received an update as of session 69"; :298 "the `production` channel, which has never received an update -- every OTA so far went to `preview`"; :522 S81-08 "it SHIPS only in the first post-approval OTA, after LEGAL-V3 is live ..." (it shipped 2026-11-07 16:10 before LEGAL-V3); :564 the S81-G6 block "it SHIPS only in the OTA with the first KB-first canary, after the first review-safe OTA (S81-08 + S81-11 + consent v3; UB-R4)" and its owner step (1) (CL2 shipped early in the first OTA, the relay's stated deviation); :576 / :581 S81-11 "SHIPS only in the FIRST post-approval OTA together with S81-08 and the consent v3 copy" and owner step (1); :583 S81-11e "first post-approval OTA waits on this unit". Keep :860 (`never --branch production`, pinned by tests/test_ci_gates.py:1390-1395) and every literal the CLAUDE.md readers pin (test_s81_s04 R38's S81-04 row tokens; test_s81_s23's forbidden phrases).

### 12.7 The PR plan

ONE PR from feature/s81-g10-followups, body <= 25,600 bytes (measured with python): the summary; one short section per unit (what, the flag it rides, the RED file + counts, the E-rows); the E-rows table (EJ1, EJ2, EB1-EB13, EC1, EC2); the stated limits by id; the sentence "orchestrator Opus 5.5 by the owner's ruling of 2026-11-07"; the rename note ONCE ("the S88 follow-up 'S81-04b (the spend breaker's durable write)' ships as S81-04d; S81-04b stays the /url/compare entry check"); the owner steps names-only (D-S22-J1: one judge DRY run after the merge re-reads step 0, errors.APIError absent; S81-22c rides two dark flags; S81-04d rides the breaker flag; S81-22b is inert; the verdict_critiques table drop is a later migration unit); mutation tables and per-row evidence go to specs/ files by name.

### 12.8 The SAFE check (LC-1; the FOCUS surfaces, per unit, measured)

| Surface | D-S22-J1 | S81-22b | S81-22c | S81-04d |
|---|---|---|---|---|
| auth / tokens / sessions | no | no | no | no |
| quota / billing / refunds | no (the judge's spend calls untouched) | no (`track_after_persist` keeps cache bust / track_event / Loop 2; no consume / refund code) | no | no (every admit / record / refuse / reserve / settle decision byte-identical) |
| legal or privacy TEXT | no | no rendered text: processors.json is an internal manifest ("no route or page serves it"); one module path removed; ids, names, categories, hosts, public_name unchanged; no legal markdown or landing file edited (22b.1.6) | no | no |
| the consent path | no | no: the S81-06 consent gate (`_ENTRY_ROLES`, ROLE_FLAGS, compare/camera_refuses_for_consent) KEPT byte-identical (Q-22b-1) | no | no |
| security middleware | no | no | no | no |
| migrations | no | no (030 + the table kept) | no (048's existing column) | no |
| Redis key / TTL / Lua | no | no | no | no (RECORD_SCRIPT, keys, EXPIREAT untouched) |
| App-Review-visible client surface | no | no (no client file; the response loses nothing the client reads: `_verdict_critique` was never produced in production) | no (an additive key under a dark flag; no client reader) | no |
| secrets / key handling | no | no | no | no |

RESULT: every unit is SAFE; no unit leaves the group. The near miss is recorded: the brief's "router role table without the critic" would touch the consent gate (FOCUS) and is NOT done (Q-22b-1).

### 12.9 DEFECT_LEDGER rows (drafts, names only; the orchestrator files them)

- D-S22-J1 | JUDGE-JSONB-FILTER: the judge's resume read sent the PostgreSQL array literal `cs.{batch_pending}` for the jsonb flags column (PostgREST 400; the 2026-11-07 DRY run errors.APIError=1, runs_read=0); now the JSON operand `cs.["batch_pending"]` | rides ENABLE_BATCH_JUDGE | tests/test_s81_s22j1_judge_jsonb_filter.py | feature/s81-g10-followups | SPEC (G10) |
- S81-22b | SELF-CRITIQUE-RETIRE: the verdict self-critique pass deleted; ENABLE_SELF_CRITIQUE inert; migration 030 / the table kept | none (R-A1 (c)) | tests/test_s81_s22b_self_critique_retire.py | same | SPEC (G10) |
- S81-22c | KB-PRODUCT-IDS: metadata.kb_product_ids under ENABLE_KB_FIRST_SERVE; compare_runs.kb_product_ids from it; D-S22-K1 the kb_hit vocabulary of sources_used | rides ENABLE_KB_FIRST_SERVE + ENABLE_COMPARE_RUN_LEDGER | tests/test_s81_s22c_kb_product_ids.py | same | SPEC (G10) |
- S81-04d | SPEND-DURABLE-RETRIEVE: the quiet retrieval on the breaker's shielded durable record (renamed from the S88 'S81-04b durable write') | rides ENABLE_LLM_SPEND_BREAKER (log-only) | tests/test_s81_s04d_durable_retrieve.py | same | SPEC (G10) |
- S81-22e REFUSAL-ROWS (split out; FOCUS by surface), S81-22f CAMERA-URL-LINK (split out; a Fable brief), S81-22h VERDICT-CRITIQUES-DROP (a migration; FOCUS), S81-22i ROUTER-CRITIC-RETIRE (the consent-gate role / site / ENABLE_ANTHROPIC_CRITIC; FOCUS) | PLANNED / OPENED.

## Not done in this spec

- The base record at 90d4ed74 for the 396 RUN members (the plan is 12.2; the RED round builds it as its LAST step); no comm chunk was run (only the touched files: g10spec-baseA..D at base, g10spec-protoA / A2 / C2 / E on the prototype).
- The RED files, the golden of 22b.5 P1 and the E-row edits (the prototype applied only the minimal E-edits that measured the red sets; it is removed).
- The full jest suite and the fourteen fences + b3a (GREEN / the final round, through the junction).
- The CLAUDE.md wording (GREEN) and the DEFECT_LEDGER / PLAN_STATUS filing (the orchestrator).
- No production read of any kind; the owner's DRY re-read of the judge is an owner step.
