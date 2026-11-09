## S81-G10 FOLLOWUPS: D-S22-J1 + S81-22b + S81-22c (with D-S22-K1) + S81-04d

The tenth SAFE group under LC-9 (one spec, one RED, one GREEN, one adversary); orchestrator Opus 5.5 by the owner's ruling of 2026-11-07. **No new flag.** Every riding flag stays unset in production, so nothing changes in production at the merge: S81-22b deletes code reachable only under `ENABLE_SELF_CRITIQUE` (unset on web, ledger 2026-11-06), which becomes an inert retired name.

Spec `specs/S81_G10_UNIT_SPEC.md` (53ebfa69...), rulings `specs/RULINGS_S81_G10.md` (R-G10-1..16), gate `specs/GATE_S81_G10.md` (GC-1..10), the RED report `specs/S81_G10_RED_REPORT.md` (mutation tables, per-row evidence), the GREEN report (filed by the orchestrator beside them: every [pyt] line, the file table with shas).

**ID note:** the S88 follow-up called 'S81-04b (the spend breaker's durable write)' ships here as **S81-04d**; the DEFECT_LEDGER S81-04b stays the /url/compare spend-breaker entry check (FOCUS, untouched).

### D-S22-J1 JUDGE-JSONB-FILTER (rides `ENABLE_BATCH_JUDGE`)
`scripts/cron_compare_judge.py` `_resume` (step 0) now sends the JSON operand for the jsonb `compare_judgements.flags` column: `.contains("flags", json.dumps(["batch_pending"]))` renders `flags=cs.["batch_pending"]` on the pinned postgrest 2.31.0 (one comment line names the rule). The list form rendered the PostgreSQL array literal `cs.{batch_pending}`, which PostgREST answered 400 in the 2026-11-07 DRY run (errors.APIError=1, runs_read=0). OFF (unset / false) still exits before any request; DRY and apply are otherwise byte-identical (the other judge requests pinned by P2). RED `tests/test_s81_s22j1_judge_jsonb_filter.py` (6 RED / 16 PIN).

### S81-22b SELF-CRITIQUE-RETIRE (no flag; R-A1 (c))
Deleted: `app/services/verdict_critique_service.py` + its two suites; the orchestrator's six regions (the `_regen_model_downgraded` init, the I3.1 / I3.2 sites on both paths, `_apply_self_critique`, `_verdict_critique_metadata`); `feedback_service` `_without_verdict_critique` / `_persist_verdict_critique` (the insert receives the body itself; `track_after_persist` runs cache bust, cohort event, Loop 2); `model_config.critic_model` + the OpenAI critic default; `llm_router._self_critique_on` + the preflight critic leg + its docstring clause; the `api_budget_service` WIRED comment line (count 14 -> 13); the `scripts/cron_learning.py` threshold comment; ONE module path in `app/legal/processors.json` (an internal manifest: no route or page serves it; no rendered legal or privacy text and no processor changes). KEPT byte-identical (R-G10-2): `ROLE_FLAGS`, `_ENTRY_ROLES`, `SITES` incl. `critique`, the consent gates, `ENABLE_ANTHROPIC_CRITIC`, the Claude critic model (the judge's Haiku), migration 030 + the `verdict_critiques` table. Inertness: REST, SSE (both `ENABLE_FULL_STREAM_DEADLINE` states), the persisted payload, the follow-ups and the compare_runs row equal the base golden with `ENABLE_SELF_CRITIQUE` unset AND set to true, with zero `critique` dispatch. RED `tests/test_s81_s22b_self_critique_retire.py` (10 RED / 9 PIN) + the P1 golden `tests/fixtures/s81_s22b_flag_off_golden.json`.

### S81-22c KB-PRODUCT-IDS + D-S22-K1 (rides `ENABLE_KB_FIRST_SERVE` / `ENABLE_COMPARE_RUN_LEDGER`)
`_stamp_unit_metadata` writes the additive `metadata.kb_product_ids` = [slot 0's KB card id or null, slot 1's or null] right after the kb_hit stamp, only when at least one slot served a full or partial card (an id only for a full / partial view with a non-empty str pid; a both-miss compare carries no key; `kb_hit` untouched). `compare_runs.build_run_row` writes `kb_product_ids` from it (each element a str of 1..256 chars or null; NULL when absent / malformed / empty; no kb_service / kb_serve import, P01). D-S22-K1: `_sources_used` accepts the producer marks full / partial / miss (and the frozen synthetic `hit`): the run row dropped every real hit. RED `tests/test_s81_s22c_kb_product_ids.py` (7 RED / 17 PIN).

### S81-04d SPEND-DURABLE-RETRIEVE (rides `ENABLE_LLM_SPEND_BREAKER`; R-A1 (b))
`llm_spend_breaker._retrieve_quietly` (a local twin of `app/utils/redis_offloop.py`'s, the leaf import rule) is attached with `future.add_done_callback(...)` inside `if durable:` before the shield in `_run_bounded_async`, so a record EVAL failing after its awaiter's bound or cancel no longer reaches the loop's 'Future exception was never retrieved' ERROR (CPython 3.12 `shield` drops its inner callback once the outer is cancelled). No new line; every decision, counter, the late-record INFO and the fail-open accounting unchanged; a cancelled inner future is left alone. RED `tests/test_s81_s04d_durable_retrieve.py` (4 RED / 6 PIN).

### Ids -> RED nodes -> flag -> precondition
| id | RED nodes (file) | flag | activation precondition |
|---|---|---|---|
| D-S22-J1 | r1-r6 (`test_s81_s22j1_judge_jsonb_filter.py`) | `ENABLE_BATCH_JUDGE` | none to merge; one DRY run re-reads step 0; a flip precondition of `apply` |
| S81-22b | r1-r9b (`test_s81_s22b_self_critique_retire.py`) | none (inert `ENABLE_SELF_CRITIQUE`) | none |
| S81-22c | r1-r5, r7 (`test_s81_s22c_kb_product_ids.py`) | `ENABLE_KB_FIRST_SERVE` + `ENABLE_COMPARE_RUN_LEDGER` | their own (unchanged) |
| D-S22-K1 | r6 (same file) | `ENABLE_COMPARE_RUN_LEDGER` | its own (unchanged) |
| S81-04d | r1-r4 (`test_s81_s04d_durable_retrieve.py`) | `ENABLE_LLM_SPEND_BREAKER` | its own (unchanged) |

### E-rows (deliberate pin changes)
| id | file | change | reason | LF blob base -> new |
|---|---|---|---|---|
| EJ1 | `tests/test_s81_s22_judge.py` | `_Q.execute` `contains` branch decodes a JSON str operand (`json.loads`) before filtering | the frozen fake pinned the rejected array-literal operand (a str iterated its characters): 5 frozen nodes red without it (J-M5) | `df14911370` -> `0ca60a4fcd` |
| EJ2 | `tests/test_s81_s22d_ledger_pins.py` | `S22_LF_SHA[tests/test_s81_s22_judge.py]` re-pinned to the post-EJ1 LF sha `86614fb4...` (max digit run 5) | p2 frozen-file pin follows EJ1 (GC-4 Q2) | `115fd3c6e3` -> `055d489521` |
| EB1 | `tests/test_arabic_verdict_output_w414.py` | stop point = a raising recorder on `trust_validation_service.validate_verdict` (measured: the first call after the verdict on BOTH paths); 29 / 29b / 29c keep the `gen` asserts and assert `stopped == ['validate_verdict']`; test_33 deleted; the env-list name removed | R-G10-3 / D11: the regen_args asserts and test_33 pinned the retired regen | `fecf8b992b` -> `f75b8a2625` |
| EB2 | `tests/test_comparison_quality_v2.py` | vcs import + `_critique` + TestCritiqueHedgingExemption (3 nodes) deleted; one docstring clause | the module is gone (collection error) | `5aa58b75d2` -> `30093dd166` |
| EB3 | `tests/test_feedback_service.py` | the `_persist_verdict_critique` setattr removed | AttributeError on a deleted attribute | `cf273e6fc7` -> `7fe054eac3` |
| EB4 | `tests/test_model_config.py` | the three `critic` rows (LEGACY_DEFAULTS / RESOLVERS / ENV_VARS) removed | `critic_model` deleted (collection AttributeError) | `716e79931c` -> `863968b73c` |
| EB5 | `tests/test_model_config_enforced.py` | vcs import, the `critique_verdict` branch and SHIPPED row removed; floor `>= 16` -> `>= 15`; `resolved_models()` literal without `critic`; count-free docstrings | the 16th dispatch site is deleted | `93bbc64e07` -> `d626289a94` |
| EB6 | `tests/test_openai_breaker.py` | vc_mod import + `test_verdict_critique_dispatch_feeds_the_breaker` deleted | the module is gone (also repairs 4 importers' collection) | `97ab601835` -> `d87a3275aa` |
| EB7 | `tests/test_s70_model_router_downgrade.py` | the R2.6 block (5 nodes) deleted; docstring line reworded; the now-unused `import asyncio` removed | it drove `_apply_self_critique` | `a1f48782f1` -> `341e888e7e` |
| EB8 | `tests/test_s81_d22_nightly_learning.py` | p5 re-pointed: `scripts/cron_learning.CRITIQUE_THRESHOLD == 7` and its CRITIQUE_COLUMNS `*_score` columns == [bias_score, missing_citation_score], each `integer NULL` in migration 030 | the module file it read is gone; the job reads the kept table | `f206bf810e` -> `f15c1c7103` |
| EB9 | `tests/test_s81_s06_anthropic_router.py` | vcs import, REPLIES['critique'], run_site's critique branch, r14's critique case, p10's `critic`, the SITE_FUNCS row removed; p07 -> `disambiguate`, p13 -> `classify`; BASE_KW['critique'] KEPT (the kept SiteSpec rows dispatch with it) | the dispatch site is deleted; SITE_ROLES / SITE_CAPS / every `_route('critique')` row kept | `bba81f56cb` -> `bf89418b8d` |
| EB10 | `tests/test_s81_s06_router_gate_rows.py` | G05 cell 4 `True` -> `False` (ENABLE_SELF_CRITIQUE inert); G13 keys minus `critique`, `== 15` | the preflight critic leg and the routed key are retired | `9f9b6763f1` -> `846309e888` |
| EB11 + EB11b | `tests/test_u3c_store_false_pin.py` | census floors `sites >= 15`, `spreads >= 31` (15 + 15 + 1) | each floor minus exactly the one deleted dispatch site | `5819022853` -> `e1b0433ac0` |
| EB12 + EB12b | `tests/test_comparison_id_echo.py` | `_verdict_critique` fixture key and the `_persist_critique` recorder removed; order pins = [cache_bust, track_event, loop2]; `Insert.snapshots` (call-time json snapshot) read by 8c, which now asserts row metadata == response metadata | 22 ERROR nodes otherwise; with no sanitizing copy the route's later echo mutates the recorded object | `453fd6aa72` -> `1b9a8f1edb` |
| EB13 | `tests/fixtures/legal_s78.json` | the one module path removed from `manifest_base.openai.module` | R22 equality with processors.json | `b77ba27347` -> `99350d05d6` |
| EC1 | `tests/test_s81_s11b_result_aggregates.py` | P1 sets `metadata.kb_product_ids` aside and asserts its value (each full / partial slot's id, else null; at least one full/full payload) | R-G10-6; the G8 golden NOT re-recorded | `e4a51eafc2` -> `65bdc8764f` |
| EC2 | `tests/test_s81_s18b_store_label.py` | the same helper on its P1 row | R-G10-6 | `f7d9359b23` -> `dde8d244ed` |

No other frozen row moved: the S81-18 R20 both-miss row, `test_s81_s22_compare_runs.py:682` (NULL without the key) and the synthetic `hit` rows stay green; every E-row floor change equals exactly the one deleted dispatch site.

### Evidence (every [pyt] line is in the GREEN report)
- Frozen files (GC-1): the five re-hashed first and last from the LF bytes: equal.
- RED files: 75 / 75 in every run (the last two at the committed tree), flags unset and with every riding flag exported ON:
```
[pyt] tag=g10green-red-off1 start=2026-11-09 19:03:56 end=2026-11-09 19:04:09 elapsed=12s bound=600s status=OK rc=0
[pyt] tag=g10green-red-on start=2026-11-09 19:14:28 end=2026-11-09 19:14:40 elapsed=12s bound=600s status=OK rc=0
[pyt] tag=g10green-red-final-off start=2026-11-09 19:40:39 end=2026-11-09 19:40:51 elapsed=12s bound=600s status=OK rc=0
[pyt] tag=g10green-red-final-on start=2026-11-09 19:40:51 end=2026-11-09 19:41:04 elapsed=12s bound=600s status=OK rc=0
```
- Counts: 75 nodes = 27 RED (J1 6 / 22b 10 / 22c 7 / 04d 4) + 48 PIN; 30 mutants on the RED prototype, all KILLED except J-M6 and C-M8 (equivalent: L-J1-4, L-22c-5); D-M5 KILLED structurally (GC-3).
- CI-order set (spec 12.3, 33 files, a lifespan user first; the second run at the committed tree): 3 failed = the 3 CRLF-environment nodes of the base record / 2099 passed (base: 30 failed = 27 RED by design + the same 3 / 2095 passed; the 23 fewer nodes are the deleted critique rows):
```
[pyt] tag=g10green-ciorder start=2026-11-09 19:12:43 end=2026-11-09 19:14:07 elapsed=84s bound=1200s status=FAIL rc=1
[pyt] tag=g10green-ciorder-final start=2026-11-09 19:41:09 end=2026-11-09 19:42:33 elapsed=84s bound=1200s status=FAIL rc=1
```
- Comm set of record: 729 members at HEAD (`3fa62c6b...`, re-derived: no addition) in 30 chunks of <= 25 vs the stored base record 90d4ed74 / `1f35353b...` (727 members, 27 FAILED ids, all environmental): HEAD FAILED 27, **comm -13 = EMPTY**; not measured: none.
```
[pyt] tag=g10green-head-c01 start=2026-11-09 19:21:14 end=2026-11-09 19:21:47 elapsed=33s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c02 start=2026-11-09 19:21:47 end=2026-11-09 19:22:14 elapsed=26s bound=1200s status=FAIL rc=1
[pyt] tag=g10green-head-c03 start=2026-11-09 19:22:14 end=2026-11-09 19:22:39 elapsed=25s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c04 start=2026-11-09 19:22:39 end=2026-11-09 19:23:39 elapsed=60s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c05 start=2026-11-09 19:23:39 end=2026-11-09 19:23:55 elapsed=16s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c06 start=2026-11-09 19:23:55 end=2026-11-09 19:24:08 elapsed=13s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c07 start=2026-11-09 19:24:08 end=2026-11-09 19:24:24 elapsed=16s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c08 start=2026-11-09 19:24:25 end=2026-11-09 19:24:56 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c09 start=2026-11-09 19:24:56 end=2026-11-09 19:26:15 elapsed=79s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c10 start=2026-11-09 19:26:15 end=2026-11-09 19:26:29 elapsed=14s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c11 start=2026-11-09 19:26:29 end=2026-11-09 19:27:08 elapsed=39s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c12 start=2026-11-09 19:27:08 end=2026-11-09 19:27:20 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c13 start=2026-11-09 19:27:20 end=2026-11-09 19:27:32 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c14 start=2026-11-09 19:27:32 end=2026-11-09 19:28:02 elapsed=30s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c15 start=2026-11-09 19:28:02 end=2026-11-09 19:28:36 elapsed=34s bound=1200s status=FAIL rc=1
[pyt] tag=g10green-head-c16 start=2026-11-09 19:28:36 end=2026-11-09 19:28:59 elapsed=23s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c17 start=2026-11-09 19:28:59 end=2026-11-09 19:29:18 elapsed=19s bound=1200s status=FAIL rc=1
[pyt] tag=g10green-head-c18 start=2026-11-09 19:29:18 end=2026-11-09 19:29:39 elapsed=21s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c19 start=2026-11-09 19:29:39 end=2026-11-09 19:32:20 elapsed=161s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c20 start=2026-11-09 19:32:20 end=2026-11-09 19:33:57 elapsed=97s bound=1200s status=FAIL rc=1
[pyt] tag=g10green-head-c21 start=2026-11-09 19:33:57 end=2026-11-09 19:35:04 elapsed=67s bound=1200s status=FAIL rc=1
[pyt] tag=g10green-head-c22 start=2026-11-09 19:35:04 end=2026-11-09 19:35:56 elapsed=52s bound=1200s status=FAIL rc=1
[pyt] tag=g10green-head-c23 start=2026-11-09 19:35:56 end=2026-11-09 19:36:33 elapsed=37s bound=1200s status=FAIL rc=1
[pyt] tag=g10green-head-c24 start=2026-11-09 19:36:33 end=2026-11-09 19:37:35 elapsed=62s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c25 start=2026-11-09 19:37:35 end=2026-11-09 19:37:54 elapsed=19s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c26 start=2026-11-09 19:37:54 end=2026-11-09 19:38:46 elapsed=51s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c27 start=2026-11-09 19:38:46 end=2026-11-09 19:39:33 elapsed=47s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c28 start=2026-11-09 19:39:33 end=2026-11-09 19:40:01 elapsed=28s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c29 start=2026-11-09 19:40:01 end=2026-11-09 19:40:26 elapsed=25s bound=1200s status=OK rc=0
[pyt] tag=g10green-head-c30 start=2026-11-09 19:40:26 end=2026-11-09 19:40:30 elapsed=4s bound=1200s status=OK rc=0
```
- `tests/test_secret_scan_static.py`: [pyt] tag=g10green-secretscan start=2026-11-09 19:42:33 end=2026-11-09 19:42:38 elapsed=5s bound=600s status=OK rc=0   # [hermeticity] sentinel checked 31 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 31 passed, 1 warning in 4.23s
- Corpus gate (`scripts/verify_flag_byte_identity.py`, the eight-flag list, alone): `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656`, OVERALL SHA256 `387fa35c600f6ea9f049d38a84966f435b9827ed2ed636c0144b7b56f1d09181` (EQUAL to the base value `387fa35c...`).
- Client fences by path through the junction (the fourteen + clipboard edges + the seven b3a suites incl. nativeStrings): 22 suites: 21 passed, 1 failed = config/nativeBundle.w37 with exactly its 4 known drift nodes (d5, k2, k4, k5; the accepted base failures); 337 passed / 4 failed. `[jest] tag=g10green-fences start=2026-11-09 19:21:40 end=2026-11-09 19:21:49 rc=1`
- ruff E9,F63,F7,F82 + py_compile clean on every edited Python file; json.loads clean (processors.json, legal_s78.json); black --check clean on the three allowlisted files (llm_spend_breaker.py, llm_router.py, test_s81_s06_router_gate_rows.py); bytes > 127 = 0 in the five new files; `git diff --stat` hunks only (CRLF kept).
- CLAUDE.md: the G10 block after the S81-G9 block, the :341 pointer sentence, `ENABLE_SELF_CRITIQUE` retired in place, the self-critique sentences of the 22b list rewritten in place, and the rows that lagged after the first production OTA (2026-11-07 16:10 AST, update group `08de6433-3883-4c4d-bada-fb450ba29100`, runtime 1.0.0, from main `f1e20c39`) rewritten in place (principle 5).

### Stated limits
- L-J1-1 the proof drives the pinned client against a fake PostgREST; the live jsonb parse is re-read only by the owner's DRY run. L-J1-2 no `batch_pending` row exists in production (DRY only): no production read result changes until an apply run writes markers. L-J1-3 the real-client rows exercise only the requests the fake answers. L-J1-4 the compact-separator operand is byte-identical for one element (J-M6, equivalent).
- L-22b-1 `ENABLE_SELF_CRITIQUE` is inert: setting it does nothing and logs nothing. L-22b-2 migration 030 and the `verdict_critiques` table stay with no writer (the D22 job reads an empty table); the drop is S81-22h. L-22b-3 `resolved_models()` and the startup `[models]` line lose `critic` (log only). L-22b-4 the router keeps the critic role, the `critique` SiteSpec and `ENABLE_ANTHROPIC_CRITIC` (the consent gate counts the critic role when that dark flag is ON): S81-22i. L-22b-5 a comparisons row carries `metadata._verdict_critique` only if a body produced before the merge with the flag ON were persisted after it (never ON in production). L-22b-6 the corpus gate cannot see the orchestrator: the identity proof is P1 / R8 / R9 / R9b / R10.
- L-22c-1 the ids ride the saved comparison (history, public share) like kb_hit: catalogue ids, not personal data. L-22c-2 a NULL row value means no KB card id (the miss marks stay in sources_used). L-22c-3 the camera / URL comparison link is S81-22f. L-22c-4 rows written before the merge keep a NULL kb_hit for hits (none exist). L-22c-5 the stamp sits inside the kb_hit guard (C-M8 equivalent: views and marks are set together).
- L-04d-1 production web never takes this path (the breaker is OFF; the judge uses the sync path). L-04d-2 the twin duplicates three lines of redis_offloop (pinned equal by AST).

### Follow-ups (PLANNED, outside G10; R-G10-4)
S81-22e REFUSAL-ROWS (FOCUS by the quota-path exits; after the ledger canary), S81-22f CAMERA-URL-LINK (a Fable brief), S81-22h VERDICT-CRITIQUES-DROP (a migration: FOCUS), S81-22i ROUTER-CRITIC-RETIRE (the consent-gate role / site / flag: FOCUS).

### Owner steps (names only)
Nothing to flip. After the merge, ONE judge DRY run (the service exists, no schedule) re-reads step 0: `errors.APIError` absent, the resume read 200; a dated ledger line. The S81-12 rebase unions `app/legal/processors.json`, `tests/fixtures/legal_s78.json`, `tests/test_s81_s06_anthropic_router.py` and CLAUDE.md (hunks disjoint). The `verdict_critiques` drop waits for S81-22h.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
