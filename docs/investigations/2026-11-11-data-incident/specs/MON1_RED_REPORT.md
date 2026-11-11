# MON1 RED REPORT (LLM-CREDENTIAL-HEALTH; Opus 5.5 RED agent; 2026-11-11)

Base a74caba7e3ff66b12e94178c912197c845ccbd14; worktree sc-inc-mon1 (HEAD == base). Merged is NOT proven: this report is suites and gates, never the production proof (H6); PROOF ON THE PHONE stays PP1-PP5 of the spec, rewritten by R-MON1-22/24.

## Files written (the ONLY files added to the real worktree)
- tests/test_inc_mon1_credential_health.py sha256 10061c0a64da034588602258d5020c015f97e95f7020e9eb0251a2c94bf56c71 (52629 B, ASCII, LF, black-clean at default 88)
- tests/test_inc_mon1_probe.py sha256 2950c33e70d30a3dd69361a9726ce1421b778c4a9a00354067b213a530845880 (17106 B, ASCII, LF, black-clean); it imports the helpers and the two fixtures from the first file

## Every [pyt] line
```
[pyt] tag=inc-mon1-base-direct start=2026-11-11 19:56:47 end=2026-11-11 19:57:45 elapsed=58s bound=1200s status=OK rc=0   (1193 passed)
[pyt] tag=inc-mon1-base-health start=2026-11-11 19:57:56 end=2026-11-11 19:59:02 elapsed=66s bound=1200s status=FAIL rc=1   (2 failed, 1274 passed: test_s81_s24_auth_throttle.py::test_r92_hygiene + ::test_p83_red_file_setenv_hygiene, CRLF working-copy bytes, environmental; carried in the S81-04c base record too)
[pyt] tag=inc-mon1-base-serper waited=2s; start=2026-11-11 19:59:05 end=2026-11-11 19:59:41 elapsed=36s bound=1200s status=OK rc=0   (543 passed)
[pyt] tag=inc-mon1-base-scan start=2026-11-11 19:59:49 end=2026-11-11 20:00:10 elapsed=21s bound=1200s status=OK rc=0   (598 passed)
[pyt] tag=inc-mon1-red-base waited=42s; start=2026-11-11 20:08:49 end=2026-11-11 20:09:27 elapsed=37s bound=600s status=FAIL rc=1   (122 failed, 7 passed; first RED draft)
[pyt] tag=inc-mon1-red-base2 start=2026-11-11 20:34:57 end=2026-11-11 20:35:34 elapsed=37s bound=600s status=FAIL rc=1   (123 failed, 7 passed = 130 nodes; FROZEN bytes; [hermeticity] sentinel checked 130 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
[pyt] tag=inc-mon1-proto-on waited=348s; start=2026-11-11 20:19:55 end=2026-11-11 20:20:40 elapsed=45s bound=600s status=FAIL rc=1   (1 failed se04, before the scope recipe)
[pyt] tag=inc-mon1-proto-se04 start=2026-11-11 20:23:10 end=2026-11-11 20:23:39 elapsed=30s bound=600s status=OK rc=0   (5 passed)
[pyt] tag=inc-mon1-proto-on2 start=2026-11-11 20:23:47 end=2026-11-11 20:24:17 elapsed=30s bound=600s status=OK rc=0   (129 passed)
[pyt] tag=inc-mon1-proto-off start=2026-11-11 20:24:18 end=2026-11-11 20:24:47 elapsed=29s bound=600s status=OK rc=0   (129 passed)
[pyt] tag=inc-mon1-proto-on3 start=2026-11-11 20:35:36 end=2026-11-11 20:36:08 elapsed=32s bound=600s status=OK rc=0   (130 passed; FROZEN bytes, ENABLE_LLM_CREDENTIAL_PROBE=true)
[pyt] tag=inc-mon1-proto-off3 start=2026-11-11 20:36:09 end=2026-11-11 20:36:45 elapsed=36s bound=600s status=OK rc=0   (130 passed; FROZEN bytes, ENABLE_LLM_CREDENTIAL_PROBE=false)
[pyt] tag=inc-mon1-proto-pins start=2026-11-11 20:32:54 end=2026-11-11 20:34:45 elapsed=111s bound=1200s status=FAIL rc=1   (2 failed, 2149 passed on the PROTOTYPE: K1 = E1 as specified; test_s81_s04_spend_breaker.py::test_p05_flag_off_health_has_no_spend_key = NEW E2)
[pyt] tag=inc-mon1-mut-mu24 start=2026-11-11 20:31:29 end=2026-11-11 20:32:00 elapsed=31s bound=600s status=FAIL rc=1   (15 failed, 634 passed)
[pyt] tag=inc-mon1-mu24-ctrl start=2026-11-11 20:32:03 end=2026-11-11 20:32:33 elapsed=30s bound=600s status=FAIL rc=1   (1 failed = E2, 648 passed)
[pyt] tag=inc-mon1-comm-01 elapsed=28s status=OK rc=0 (400 passed, 3 skipped)
[pyt] tag=inc-mon1-comm-02 elapsed=22s status=OK rc=0 (444 passed, 30 deselected; netguard blocked 17 attempts from 4 nodes)
[pyt] tag=inc-mon1-comm-03 elapsed=40s status=OK rc=0 (858 passed, 1 xfailed)
[pyt] tag=inc-mon1-comm-04 elapsed=13s status=OK rc=0 (417 passed)
[pyt] tag=inc-mon1-comm-05 elapsed=21s status=OK rc=0 (456 passed)
[pyt] tag=inc-mon1-comm-06 elapsed=22s status=OK rc=0 (1312 passed, 1 xfailed)
[pyt] tag=inc-mon1-comm-07 elapsed=28s status=OK rc=0 (172 passed)
[pyt] tag=inc-mon1-comm-08 elapsed=17s status=OK rc=0 (419 passed)
[pyt] tag=inc-mon1-comm-09 elapsed=25s status=FAIL rc=1 (4 failed, 589 passed)
[pyt] tag=inc-mon1-comm-09-rerun elapsed=5s status=FAIL rc=1 (4 failed, 17 passed: deterministic, all 4 in tests/.pre_impl_failures.txt)
[pyt] tag=inc-mon1-comm-10 elapsed=23s status=OK rc=0 (317 passed)
[pyt] tag=inc-mon1-comm-11 elapsed=51s status=OK rc=0 (354 passed)
[pyt] tag=inc-mon1-comm-12 elapsed=15s status=OK rc=0 (577 passed)
[pyt] tag=inc-mon1-comm-13 elapsed=45s status=OK rc=0 (711 passed, 1 skipped)
[pyt] tag=inc-mon1-comm-14 elapsed=29s status=OK rc=0 (289 passed)
[pyt] tag=inc-mon1-comm-15 elapsed=23s status=OK rc=0 (745 passed, 9 skipped)
[pyt] tag=inc-mon1-comm-16 elapsed=14s status=OK rc=0 (208 passed)
(full comm [pyt] lines with start/end: <SP>/harness/base_records/a74caba7.../23f5330f....pyt.log)
```

## RED at base (inc-mon1-red-base2, frozen bytes)
130 nodes: 123 failed (every one AssertionError: 105 parsed failure sections plus the grep count 123 'E ... AssertionError' lines; zero ImportError / AttributeError / setup errors), 7 passed = exactly the PIN rows G01, G02, G03, HE02, S04, S05, T01. Failed ids: <SP>/MON1/red/failed_base2.txt; collected: <SP>/MON1/red/collected.txt (129 at draft 1; 130 after the P13 probe_quota param).

## Prototype (scratch worktree, thrown away)
ON (ENABLE_LLM_CREDENTIAL_PROBE=true): 130 passed. OFF: 130 passed. The rows set or delete every flag themselves, so the ambient flag cannot move a row (by design). The prototype implemented spec 3.1-3.9 plus rulings 16-22 and 26 in about 450 lines; the measured points GREEN needs:
- R-MON1-20 recipe (measured on sentry-sdk 2.68.1): Scope.clear() does NOT drop event processors, so the Starlette request processor survives a plain isolation_scope()+clear(). Working recipe (SE04 green, MU28 killed): `with sentry_sdk.isolation_scope() as iso: iso.clear(); iso._event_processors.clear(); with sentry_sdk.new_scope() as cur: cur.clear(); cur._event_processors.clear(); sentry_sdk.capture_message(...)` (a private attribute of the pinned version; 6 lines).
- R-MON1-18 lives in classify(provider, exc, source): for source probe a 401/403 rejects only with openai code invalid_api_key / anthropic type authentication_error; else the probe outcome is inconclusive.
- R-MON1-17 lives in note_success: source probe never clears quota and never clears a rejected state unless that state is probe-sourced or carried 401.

## Mutation table (prototype bytes; byte copy, exact edit matching once, -k killing rows, restore, sha256 verified; lock <scratch>/.qa-mutation.lock)
| id | mutant | -k | verdict | killing rows |
|---|---|---|---|---|
| MU01 | drop H1 note_failure (flag-OFF except) | h01 | KILLED | test_h01_flag_off_401[False], test_h01_flag_off_401[True] |
| MU02 | drop H3 note_failure (flag-ON except) | h03 | KILLED | test_h03_flag_on_401[False], test_h03_flag_on_401[True] |
| MU03 | drop H2 (flag-OFF success) | h02 | KILLED | test_h02_flag_off_success[False], test_h02_flag_off_success[True] |
| MU04 | H1 swallows instead of raise | h01 | KILLED | test_h01_flag_off_401[False], test_h01_flag_off_401[True] |
| MU05 | classify maps 400 to rejected | l02 | KILLED | test_l02_openai_classify_real_classes[BadRequestError-400-None-invalid_api_key |
| MU06 | classify reads str(exc) for invalid_api_key | l02 | KILLED | test_l02_openai_classify_real_classes[BadRequestError-400-None-invalid_api_key |
| MU07 | openai quota code branch removed | l02 or m03 | KILLED | test_l02_openai_quota_codes[credit_balance_exhausted], test_l02_openai_quota_codes[insufficient_quota], test_l02_openai_quota_codes[organization_spend_limit_exceeded], test_l02_openai_quota_codes[project_spend_limit_exceeded], test_l02_openai_quota_codes[organization_usage_limit_exceeded] |
| MU08 | anthropic billing_error branch removed | l03 or h09 | KILLED | test_l03_anthropic_classify[APIStatusError-402-billing_error-None-expected2], test_h09_anthropic_billing_quota |
| MU09 | cool-down removed (emit on every transition) | l08 or l12 | KILLED | test_l08_event_rule_same_instant, test_l12_inside_the_cooldown_one_event_and_one_warning |
| MU10 | recovery event removed | l08 | KILLED | test_l08_event_rule_same_instant |
| MU11 | H3 also records a breaker failure on a 401 | h03 or g02 | KILLED | test_h03_flag_on_401[False], test_h03_flag_on_401[True], test_g02_a_401_never_gates |
| MU12 | /health llm_credential line deleted | he01 | KILLED | test_he01_health_entry |
| MU13 | monitor raises a codeless HTTPException(503) | m02 | KILLED | test_m02_monitor_rejected |
| MU14 | monitor ignores providers_in_use | m04 | KILLED | test_m04_not_in_use |
| MU15 | tick() first statement (flag read) deleted | p01 | KILLED | test_p01_flag_off_full_config_tick_makes_no_call |
| MU16 | interval floor removed | p03 | KILLED | test_p03_interval_knob[60-300.0] |
| MU17 | probe without max_retries=0 | p04 | KILLED | test_p04_on_openai_only |
| MU18 | Serper none_left set even when a key was skipped | s02 | KILLED | test_s02_exclude_is_not_exhaustion |
| MU19 | Serper transition latch removed | s01 | KILLED | test_s01_all_exhausted |
| MU20 | _stop_llm_credential_probe defined after _drain_background_tasks | p10 | KILLED | test_p10_lifespan |
| MU21 | capture_credential_alert also logs logger.error | se03 | KILLED | test_se03_one_event_not_two |
| MU22 | serper snapshot carries the key prefixes | he05 | KILLED | test_he05_serper_counts_only |
| MU23 | note_success loses its catch-all | l07 | KILLED | test_l07_never_raises |
| MU25 | openai quota by structured type ignored | l02 | KILLED | test_l02_openai_quota_type_only |
| MU26 | probe success clears quota | p13 | KILLED | test_p13_probe_success_never_clears_quota_or_dispatch_403[probe_quota] |
| MU27 | probe 401/403 without the structured signal rejects | p15 | KILLED | test_p15_probe_unstructured_401_403_is_inconclusive[oa401-nocode], test_p15_probe_unstructured_401_403_is_inconclusive[oa401-othercode], test_p15_probe_unstructured_401_403_is_inconclusive[oa403] |
| MU28 | alert scope keeps the request event processors | se04 | KILLED | test_se04_no_request_region_inside_a_request |
| MU29 | monitor UNKNOWN 503 removed | m07 | KILLED | test_m07_unknown_with_the_probe_on[true-200.0-503-LLM_CREDENTIAL_UNKNOWN] |
| MU30 | drop H5 (anthropic except note) | h07 or h08 or h09 | KILLED | test_h07_anthropic_401, test_h08_moderation_site_403_then_success, test_h09_anthropic_billing_quota |
| MU31 | drop H8 (moderation except note) | h10 | KILLED | test_h10_content_safety_moderation |
| MU32 | once-per-process latch instead of a cool-down | l11 | KILLED | test_l11_second_outage_after_the_cooldown_emits_again |
| MU33 | probe success clears a dispatch 403 | p13 | KILLED | test_p13_probe_success_never_clears_quota_or_dispatch_403[dispatch403] |
| MU34 | drop H6 (anthropic success note) | h08 | KILLED | test_h08_moderation_site_403_then_success |
| MU35 | drop H7 (moderation success note) | h10 | KILLED | test_h10_content_safety_moderation |
| MU36 | /health serper_keys line deleted | he05 or he04 | KILLED | test_he04_health_purity, test_he05_serper_counts_only |
| MU24 | conftest reset fixture removed | order pair tests/test_retro_w1_3.py, test_openai_breaker.py, test_retro_w0_4_efg.py, test_s77_redis_offloop.py, test_s81_s04_spend_breaker.py | KILLED | 15 failed (test_retro_w0_4_efg w04g superset rows and others) vs control 1 failed (the E2 row) |

36 mutants (MU01-MU36): 36 KILLED, 0 SURVIVED at the final bytes. History: MU23 first died on an escaping RuntimeError (not an assertion) -> L07 now wraps calls in _no_raise (AssertionError); MU26 first SURVIVED (the prototype's second guard covered a dispatch quota) -> P13 gained the probe_quota param; both re-run KILLED. New mutants beyond spec 6: MU25 (quota by type, R-MON1-16), MU26/MU33 (R-MON1-17), MU27 (R-MON1-18), MU28 (R-MON1-20), MU29 (R-MON1-22), MU30/MU31/MU34/MU35 (H5-H8 each), MU32 (R-MON1-21 once-per-process latch), MU36 (serper /health line). MU15 is re-pointed to tick()'s first statement (R-MON1-19). Results TSV: <SP>/MON1/red/mutation_results.tsv; logs inc-mon1-mut-*.log.

## Comm set at base (step 7; R-MON1-29)
- List: <SP>/MON1/red/comm_all.txt (763 = every tracked tests/**/test_*.py minus the four test_precommit_hook*.py; whole tree because 3.5 edits conftest.py); reasons TSV <SP>/MON1/red/comm_reasons.tsv; set sha256 23f5330fd840af67f65ed8e7b3cb70ce176ea71eb15ccffbdc7b2aa18cf1ae58. No NETWORK_FLAKY_EXCLUDE list exists in the lane record (searched harness/, wf/, record/): none excluded.
- Reused per file at the SAME sha: 374 members of 0a224f48... + the 38 of 07867773... (36 overlap) = 376 files, 24 FAILED ids copied. Run: the 387-file remainder in 16 chunks (comm-01..16), 4 FAILED: test_page_scraping.py x2 and test_personalization_bundle_c.py x2, deterministic alone (comm-09-rerun) and all four in tests/.pre_impl_failures.txt (CI-deselected known set).
- Stored: <SP>/harness/base_records/a74caba7e3ff66b12e94178c912197c845ccbd14/23f5330f....{txt,files,header.txt,pyt.log}: 28 FAILED/ERROR ids (complete, not PARTIAL). The RED files are not in the record (they run separately: red-base2).

## Deviations (spec rows changed by the rulings, and spec claims refuted)
1. NEW E-ROW E2 (spec 4.1 says no other pin moves; 11.1 Q4 says no superset row produces an LLM outcome in-test: REFUTED): tests/test_s81_s04_spend_breaker.py:1924-1932 test_p05_flag_off_health_has_no_spend_key runs a SUCCESSFUL guarded_llm_create and then asserts set(/health body) <= BASE_HEALTH_KEYS; H2 records openai ok, so llm_credential appears. Measured red on the prototype (proto-pins, mu24-ctrl). Needs an orchestrator ruling (re-pin BASE_HEALTH_KEYS to allow llm_credential, or reset inside the test) before GREEN.
2. Seam names frozen by the RED file where the rulings name only behaviour: llm_credential_health.ALERT_COOLDOWN_SECONDS (900.0, R-MON1-21), llm_credential_health._monotonic (the cool-down / uptime clock), llm_credential_health._STARTED_AT (R-MON1-22 uptime mark). classify gains an optional third arg source (default dispatch) in the prototype; the RED rows call classify(provider, exc) only and drive R-MON1-18 through tick().
3. L08 re-pinned to R-MON1-21 (same-instant sequence yields [rejected 401, ok, quota 429]); L11 / L12 added (after / inside the cool-down; inside logs one extra WARNING). M07 added (R-MON1-22 LLM_CREDENTIAL_UNKNOWN). P13 / P14 (R-MON1-17), P15 / P16 (R-MON1-18), SE04 (R-MON1-20), SE05 + T01 PIN (R-MON1-26) added. L02 gained one case per R-MON1-16 code + the type-only case. Serper rows mark through _mark_serper_key_exhausted with run-time-unique prefixes (R-MON1-23). P10 uses the duck-typed shutdown reader (R-MON1-23).
4. H03 / H04 / H05 / H06 patch api_budget_service._openai_dispatch_admission to a fixed (admitted, outcome_matters, probe) triple instead of the Redis fake (hermetic and exact for the hook rows); G02 uses the real admission with the test_openai_breaker dict Redis (B1 rule).
5. SE rows run in a child process with init_sentry() (via app.main import) and an in-memory Transport; SE02 runs in-process with no DSN.
6. P01 is a flag-OFF row but RED at base (module absent), not a PIN; with tick() it is killable (MU15).
7. Base gate B2: two pre-existing failures (s24 CRLF hygiene rows) are environmental on this autocrlf checkout, not MON1.

## Open questions for the gate
- E2 ruling (deviation 1).
- R-MON1-20 recipe uses the private Scope._event_processors of sentry-sdk 2.68.1: accept (with SE04 as the pin), or the ruling's fallback wording.
- The suppression WARNING template for a cooled transition is unnamed (L12 counts WARNING records of the leaf logger: three L1 lines + one); GREEN may pick the text.

## Restore check
Real worktree: git status --short = only the two new RED files; git diff --quiet (no tracked change); HEAD a74caba7. Scratch worktree removed (git worktree remove --force; git worktree list shows sc-inc-mon1 only for this unit); mutation lock gone; no orphan pytest (only the orchestrator's stall monitors run).
