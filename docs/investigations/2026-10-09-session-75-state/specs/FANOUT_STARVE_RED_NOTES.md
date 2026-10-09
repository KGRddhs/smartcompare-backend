# FANOUT-STARVE RED notes (session 75, 2026-10-09)

Clock start (first tool call): 2026-10-09T14:46:59Z. Budget 90 min -> hard stop 16:17Z.
Worktree C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b, HEAD 4c0f3c99c786f93e3d0fed5ffc94d54f19ea74d5,
branch feature/s75-fanout-starve, `git status --short` EMPTY at 14:47Z. No production file, script,
runbook or docs file touched; no git write.

## Reads (facts re-anchored at main 4c0f3c99)
- executor.py:30 `_DEFAULT_MAX_WORKERS = 40`; :33-40 default_executor_size (int(env or "0") > 0 wins;
  ValueError -> 40); :43-57 install_default_executor, log line :56
  "[executor] default ThreadPoolExecutor installed: max_workers=%d".
- main.py:179-182 startup `_install_default_executor`; /health :535-553 spreads loop_lag_snapshot +
  price_parse_pool_snapshot; no `[loop]` line anywhere.
- railway.json:7 startCommand and Procfile:1 web: both `exec uvicorn app.main:app --host 0.0.0.0 --port
  $PORT --timeout-graceful-shutdown 20 --limit-concurrency "${UVICORN_LIMIT_CONCURRENCY:-512}"`.
- test_shutdown_drain.py:851-856 test_both_start_commands_begin_with_exec: startswith("exec ") and
  split()[1] == "uvicorn" (FS-R6 target).
- test_retro_w0_4_efg.py:1495-1502 test_w04g_health_has_no_price_parse_pool_key_before_the_pool_exists:
  exact key set (FS-R7 target). SECOND exact key-set pin at :1553 (test where price_parse_pool_stats
  raises) -- OUTSIDE my allowed scope, reported.
- test_serper_fail_fast.py:127 `assert t.connect == 3.0`; serper_service.py:397 connect default 3.0.
- brightdata_service.py:129-134 non-200 WARNING "[brightdata] HTTP %s for %r: %s" with query[:60] and
  resp.text[:200]; no ERROR, no _AUTH_ERROR_SEEN, no snapshot.
- scs: compare_from_text :3591 (cap wait_for :3640-3655 reads module STREAM_HARD_CAP_SECONDS per call);
  impl :3760-3812 seeds ctx + `_early_specs_buffer = [None, None]`, L1 prefilter in-proc; Step 1
  :3829-3848; `_parser_path = not (vision_products or explicit_pair)` :3866; gather :3909-3912;
  stream parse :4462 after the "Parsing query..." status :4428; `_stream_deadline = time.monotonic()
  + STREAM_HARD_CAP_SECONDS` :4325 (the clock T18 mirrors); _fetch_product_data :5241, unified search
  :5393-5395 bare await, specs launched with search_results=unified_search :5433, Phase 2 :5652-5740
  (_get_verified_rating under _PHASE2_RATING_TIMEOUT, _smart_fallback_extract), tier2/tier3 after.
- url_validator.py:526-537 _validate_url_offloop_or_sync; both validators getaddrinfo any host incl. IP
  literals (no literal short-circuit) -> "127.0.0.9" is a valid T19 host.
- Line endings: all five existing target files i/lf w/crlf -> Edit tool / CRLF-preserving append.
- netguard: IP literals allowed for getaddrinfo; loopback connects allowed; MockTransport never connects.
- test_be_harness.py: _drive/_routes/_by_pair/_degraded harness; _kind() classifies q vs pair by params;
  last node BH44 + BH23b -> new nodes BH45..BH52.

## Files written (all in the worktree; sha256 in the final report)
- tests/test_s75_fanout_starve.py NEW (ASCII, LF, 46900 bytes): T1(+pin), T2, T3(+pin), T4 PIN, T5 PIN,
  T6, T11(+pin), T12, T13, T14 x4 (OFF, ON fallback, ON no-vs, knob hygiene x8), T15 x2, T16 x3
  (OFF guard, ON, knob hygiene x8), T17 x5 (helper ON, helper fall-through x3, REST driver, stream
  driver), T18 x2 (guard param x3, knob hygiene x8), T19 PIN x2.
- tests/test_shutdown_drain.py: FS-R6 amendment (tokens[0]=="exec"; "uvicorn" in tokens; between =
  env|NAME=value; PLUS the D2 presence of `env UV_THREADPOOL_SIZE=` so the node is RED at main).
- tests/test_retro_w0_4_efg.py: FS-R7 superset amendment at :1495 (installs a pool on a throwaway loop
  so adapter_executor must be present; five keys subset; extras <= {adapter_executor, brightdata_auth};
  brightdata_auth absent).
- tests/test_serper_fail_fast.py:127 3.0 -> 8.0 (one line).
- tests/test_be_harness.py: appended BH45-BH52 (T22 x7 + T23), CRLF preserved via a byte append.

## Measurements
- 15:05Z RED-A `tests/test_s75_fanout_starve.py` alone: 50 failed / 10 passed in 8.34 s (bound 600).
  [pyt] tag=fs-red-a start=2026-10-09 18:05:26 end=2026-10-09 18:05:35 elapsed=9s bound=600s status=FAIL rc=1
  Passed = T1 pin, T3 pin, T4 PIN, T5 PIN, T11 pin, T16 OFF guard, T18[runs], T18[off] (guard rows),
  T19 x2 PIN. Every RED failed on an AttributeError or the pinned-defect message (see report).
- 15:07Z RED-B three amended files: 4 failed / 155 passed in 7.75 s (bound 1200).
  [pyt] tag=fs-red-b start=2026-10-09 18:07:43 end=2026-10-09 18:07:51 elapsed=8s bound=1200s status=FAIL rc=1
  The 4 = the amended nodes (2 param rows of shutdown-drain + the w04g pin + the serper split).
- 15:08Z probe_t17_main.py (NOT pytest, no network): at main the T17 REST driver reaches the partial
  path in 0.5 s (success True, metadata.partial True, partial_stage gather, parser_path True, one LLM
  call); the stream driver records the resolver after two status events in 0.02 s. The T17 harness is
  sound; GREEN only has to add the pre-split.
- 15:09Z RED-C `tests/test_be_harness.py`: 9 failed / 191 passed in 3.66 s (bound 1200).
  [pyt] tag=fs-red-c start=2026-10-09 18:09:21 end=2026-10-09 18:09:25 elapsed=4s bound=1200s status=FAIL rc=1
  The 9 = BH45..BH52 (BH46 x2); every existing node green.
- gitleaks 8.30.1 `dir <file> --config .gitleaks.toml --redact`: no leaks, 0 ERR lines, all five files.
- ruff E9,F63,F7,F82 clean + py_compile OK on all five; `git diff --stat` == `--ignore-cr-at-eol`
  (182/27/2/31 lines, no whole-file diff); new file 0 bytes > 127, 0 CR.

## Decisions / questions for the orchestrator (also in the report)
1. FS-R5 default `--form both` reddens BH07, BH07b, BH18, BH24, BH28 (append-only protected): my
   BH45-BH52 pass --form explicitly and do NOT pin the default. Needs a ruling (amend those nodes, or
   default q + run_canary.sh/runbook pass --form both).
2. The shutdown-drain amendment ADDS the D2 presence condition (env + UV_THREADPOOL_SIZE= between exec
   and uvicorn) so it is RED at main as step (5) demands; FS-R6's three conditions alone are green at
   main. Drop the fourth assert if the pure superset form was intended.
3. test_retro_w0_4_efg.py:1553 (test_w04g ... stats error escape) is a second exact key-set pin that
   reddens under GREEN; outside my scope -- needs the same superset amendment.
4. Contract names fixed by the tests (GREEN must follow or ask): _parse_with_budget (the single Step-1
   seam, returns (parsed, usage), marks _parse_presplit/_parse_fallback, emits the [STAGE] line),
   _parse_timeout_seconds, _unified_search_timeout_seconds, _phase2_min_residual_seconds,
   svc._compare_deadline (time.monotonic instant), brightdata _AUTH_ERROR_SEEN / _AUTH_LAST or
   _reset_brightdata_auth_state(), /health adapter_executor {workers, queued}, brightdata_auth
   {last_status, at}; metadata.phase2_skipped written by _build_partial_response.
5. T18 uses a real-clock deadline with wide margins (2 s vs 8 s knob; 100 s) instead of a fake clock
   (patching time.monotonic would break asyncio's loop clock).
