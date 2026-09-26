# W0-4e / W0-4f / W0-4g UNIT SPEC (session 68, written by Fable 2026-09-26)

Base SHA: `61585c58` (= origin/main, the session-67 close). Worktree `C:/Users/SynAckITPC/Documents/AI/sc-w0-4efg`, branch `retro/w0-4efg-followups`.
Flag: the EXISTING `ENABLE_PRICE_PARSE_OFFLOAD` (default OFF, read PER CALL by `price_service.price_parse_offload_enabled()`, `structured_comparison_service._price_parse_offload_enabled()` and `url_extraction_service._price_parse_offload_enabled()`; the three readers accept true/1/yes/on, case- and space-insensitive — pinned by `test_w04_the_three_flag_readers_agree`). NO new flag. The knob `PRICE_PARSE_MAX_WORKERS` is unchanged.
Sources (read them): `docs/investigations/2026-09-24-session-67-state/prbody_R-W04.md` ("Stated limits / follow-ups" paragraph and the "## Follow-ups" list), `retro_adv_R-W04_r1.json` (`tests_that_prove_nothing`, five rows), `retro_rulings_R-W04.txt` (rulings 5, 8, 9, 11), CLAUDE.md's W0-4 row (~line 405) and W0 ACTIVATION ORDER step (2) (~line 407). Line numbers below were measured at `61585c58` — re-locate every anchor by symbol.

## 0. Invariants (binding for red, green, adversary)

1. **Flag OFF is byte-identical to `61585c58`:** every OFF path executes the exact base statements (the same soups, the same inline calls, the whole body, the pool never built, `/health` the same keys). Corpus gate OFF must reproduce OVERALL `9504e5a94a218969764c8cbfdb43243da7bfcd8e0950bb5fb9148b9a9258ce99` and results `a1b3460c28579fab605287e1b5a05dd9cb8a3b07782573dfb5aac005104c59d8`; ON `--compare` against OFF must be equal with 0 differing records (the harness calls `extract_price_from_html` directly, so it observes neither the cap nor the new sites — stated limit, carried forward).
2. Every new fork sits under a per-call flag read. Module globals are resolved at CALL time, never aliased at import, so a monkeypatched `scs.curl_fetch_html`, `ues.extract_generic_data`, `ps.run_parse_offloaded` is what runs on either branch.
3. Hunks are function-local; no refactors; no new module-level state beyond the pool counters in §3. CRLF hygiene (the working copy is CRLF, the index LF; `git diff --stat` shows only the intended lines).
4. The existing pins stay green in both flag states: `tests/test_retro_w0_4.py` (185 nodes), `tests/test_price_parse_offload.py`, `tests/test_verify_flag_byte_identity.py`, `tests/test_lazy_bh_pdp_backfill.py`, `tests/test_health_loop_lag.py` (incl. `test_health_handler_is_a_pure_dict_read`: NO `await` and none of `asyncio.sleep`, `requests.`, `httpx.`, `get_cached`, `execute(` in the handler body).

## 1. W0-4e — the lazy-backfill search-page scan (`structured_comparison_service._lazy_bh_pdp_backfill`, ~scs:2863)

Defect (R-W04 ruling 5, disclosed): under the flag `curl_fetch_html` caps EVERY caller at `PRICE_FETCH_MAX_BYTES` = 3,000,000 chars, so the backfill's `re.findall(href=... /product/ ...)` over a curled retailer SEARCH page no longer sees an href past 3,000,000 chars. The base pin `test_w04b_lazy_backfill_caller_flag_off_scans_the_whole_search_page` covers OFF only.

Design (binding):
- `price_service.curl_fetch_html(url: str, *, cap: bool = True)`: keyword-only. Under the flag: `resp.text[:PRICE_FETCH_MAX_BYTES]` when `cap` is true, the WHOLE `resp.text` when `cap` is false. Flag OFF: the whole body, `cap` never read (the base statements). Every other caller keeps the default (`cap=True`), including `StructuredComparisonService._curl_fetch_html` (~scs:3277) and `fetch_page_price`.
- `_lazy_bh_pdp_backfill` calls `curl_fetch_html(sp, cap=False)` (the ONLY `cap=False` site in `app/`), and moves the pure-sync `re.findall(...)` over the body into ONE nested block `_w04_scan_block()` returning the match list; under the flag the block runs on the price-parse pool via `price_service.run_parse_offloaded(_w04_scan_block)` (resolved at call time, `from app.services import price_service as _w04_ps` inside the branch exactly as `_extract_price_from_html_maybe_offloaded` does), flag OFF the identical block runs inline. The per-match `_accept(...)` loop stays on the event loop in BOTH states (it calls `validate_scrape_url` / `score_source` and appends in order; ordering and acceptance are byte-identical).
- Nothing else in the backfill moves (Serper fan-out, `_accept` gates, the INFO line).

## 2. W0-4f — `url_extraction_service.extract_from_url`'s three inline soups (~ues:448)

Defect (R-W04 ruling 8, disclosed): `extract_from_url` calls `extract_amazon_data` / `extract_noon_data` / `extract_generic_data` (each builds one or more `BeautifulSoup`; generic builds two via `extract_json_ld` + `extract_meta_tags`) INLINE on the event loop in both flag states; the transitive AST guard allowlists `("url_extraction_service.py", "extract_from_url")` for that reason.

Design (binding):
- Select the extractor first (module global read at call time): `_extractor = extract_amazon_data` if `"amazon" in retailer["key"]`, `extract_noon_data` if `"noon"`, else `extract_generic_data`.
- Under the flag (`_price_parse_offload_enabled()`, the module-local reader so the OFF path never imports `price_service`): `from app.services.price_service import PRICE_FETCH_MAX_BYTES, run_parse_offloaded`; `html = html[:PRICE_FETCH_MAX_BYTES]` (ONE truncation, right after the fetch; the SAME capped `html` then reaches `extract_with_ai` — mirroring the render legs: the parse input is bounded, the fetch is not); `raw_data = await run_parse_offloaded(_extractor, html, url)`. Flag OFF: `raw_data = _extractor(html, url)` inline, whole body, exactly the base behaviour.
- The AST guard's `_TRANSITIVE_ALLOWLIST` in `tests/test_retro_w0_4.py` becomes `frozenset()` (EMPTY) — that edit is the RED for this part and the ONLY edit to that file.
- `fetch_page` (httpx) stays uncapped in both states (stated limit). `extract_with_ai` is otherwise unchanged (its own offload from R-W04 stays).
- An exception raised inside the extractor propagates out of `extract_from_url` with the same type in both states (`run_parse_offloaded` re-raises the worker's exception; pin it).

## 3. W0-4g — pool instrumentation (the canary watch item) + the r1 test-hardening notes

### 3a. Instrumentation (CLAUDE.md activation step (2) says "watch the price-parse pool's queue depth" — nothing exposes it; prbody line "not instrumented yet; follow-up W0-4g")
- `price_service._PRICE_PARSE_STATS = {"jobs_total": 0, "waiting": 0, "running": 0, "peak_waiting": 0, "peak_running": 0}` (module dict, mutated only inside `run_parse_offloaded` on the event-loop thread; approximate under several loops is acceptable and stated).
- `run_parse_offloaded`: `waiting += 1` (and `peak_waiting`) BEFORE `await sem.acquire()`, `waiting -= 1` in a `finally` around the acquire (a cancelled waiter never leaks a count and never releases a slot it did not take); `running += 1`, `jobs_total += 1` (and `peak_running`) after the acquire; `running -= 1` and `sem.release()` in the `finally` around the executor await. The cancel/slot pins of R-W04 (`test_w04d_cancelled_awaits_*`, `test_w04d_semaphore_bounds_jobs_submitted_to_the_parse_pool`, the 9x2 ContextVar pins) must stay green — `async with sem` and acquire/release-in-finally are the same contract.
- `price_service.price_parse_pool_stats() -> Optional[Dict[str, int]]`: `None` while `_PRICE_PARSE_POOL is None`; else `{"workers": pool._max_workers, "queued": pool._work_queue.qsize(), **_PRICE_PARSE_STATS}` (a pure read; `queued` is the executor's own queue depth, which the submission semaphore keeps at 0 — its value on `/health` is the proof the semaphore is doing its job).
- `_get_price_parse_pool`: when it BUILDS the pool, ONE grep-stable line `logger.info("[PRICE-PARSE] pool built workers=%d", n)` (R-W18 style; once per process).
- `app/main.py`: `def price_parse_pool_snapshot() -> dict` next to `loop_lag_snapshot`: `mod = sys.modules.get("app.services.price_service")` (NEVER an import statement — the handler must not be able to trigger an import), `fn = getattr(mod, "price_parse_pool_stats", None)`, call it inside `try/except Exception: return {}`; return `{"price_parse_pool": stats}` when stats is truthy else `{}`. `health_check` returns `{"status": ..., "message": ..., **loop_lag_snapshot(), **price_parse_pool_snapshot()}` — no await, no I/O, none of the forbidden substrings in the handler body. Flag OFF: the pool is never built, so the key is ABSENT and `/health` is byte-identical.

### 3b. The r1 adversary's four test-side gaps (each pin must KILL its named mutant; the red report proves the kill from a byte snapshot with a sha256-verified restore)
1. `N_curl_cap_flag_true_only_literal` — the curl cap and BOTH render-leg caps are exercised under every accepted flag value ('1', 'yes', 'on', ' TRUE '), not only 'true'.
2. `N_ues_text_trunc_on` — the `extract_with_ai` prompt-identity pin (ON vs OFF) uses a fixture page whose visible text EXCEEDS 4,000 chars, so the 4,000-char truncation is inside the pinned region.
3. `N_harness_compare_intersection_only` — `scripts/verify_flag_byte_identity.py --compare` counts records missing on EITHER side: other payload with one record fewer -> `DIFFERING RECORDS 1 of N`; other payload with one EXTRA record -> counted too; exit 1 both times.
4. `N_harness_compare_whole_payload_not_results` — `--compare` against a JSON WITHOUT a `results` key (e.g. `{"foo": 1}`) reports `equal=False` and exits 1 (never compares this run against itself).
5. The two production-equivalent survivors (`N_sem_size_check_removed`, `N_pool_size_read_every_call`) are recorded as equivalent in pr_text; no pin.
No harness CODE change is expected for 3 and 4 (the base code already behaves so — the mutants changed it); if a pin cannot be written without a code change, STOP and report.

## 4. Tests — the red list (new file `tests/test_retro_w0_4_efg.py`; the ONLY edit to `tests/test_retro_w0_4.py` is the allowlist -> `frozenset()`)

The new file carries its own autouse fixtures copied from `tests/test_retro_w0_4.py`'s pattern: the zero-network guard (socket + `curl_cffi.requests.get`), `_fresh_parse_pool` (reset the pool and semaphore BY TYPE between tests, shut the old pool down) and the flag reset. Fixture pages are synthetic (no corpus files). RED = fails at `61585c58` for the stated reason; PIN = green at base and must stay green; KILL = a pin whose proof is the named mutant going red.

W0-4e
- E1 RED `test_w04e_flag_on_backfill_scan_sees_an_href_past_3mb` — flag ON, search page with the only in-domain /product/ href after 3,500,000 chars (the base OFF pin's body) -> `extra == [href]`.
- E2 RED `test_w04e_flag_on_backfill_scan_runs_on_the_price_parse_pool` — spy `re.findall` via a wrapped `_w04_scan_block`? No: patch `scs.re.findall` is too broad; instead stub `price_service.run_parse_offloaded` with a recorder that runs the block on a thread named like the pool and asserts the block was submitted exactly once and that the thread name of the block's execution starts with `price-parse` when the REAL pool runs it (two tests or one parametrized: recorder + real pool).
- E3 PIN `test_w04e_flag_off_backfill_scan_inline_whole_page_no_pool` — flag OFF (and unset): `extra == [href]`, the scan ran on MainThread, `price_service._PRICE_PARSE_POOL is None` afterwards.
- E4 RED `test_w04e_curl_fetch_html_cap_kwarg[flag x size x cap]` — sizes 2,999,999 / 3,000,000 / 3,000,001 / 3,500,000; ON+cap=True -> `min(len, 3,000,000)`; ON+cap=False -> whole; OFF either -> whole; today `cap=False` is a `TypeError` (the red).
- E5 RED `test_w04e_exactly_one_caller_exempts_itself_from_the_cap` — AST over `app/**/*.py`: the set of `(file, enclosing def)` passing `cap=False` to `curl_fetch_html` == `{("structured_comparison_service.py", "_lazy_bh_pdp_backfill")}` (today: empty set -> red; a second exemption later -> red).
- E6 PIN/RED `test_w04e_backfill_result_identical_flag_on_vs_off[small page, page past 3mb]` — the same `extra` list in both states (red today for the large page).
- E7 PIN `test_w04e_backfill_accept_loop_stays_on_the_loop` — `_accept`'s helpers (`validate_scrape_url`, `score_source`) are called on MainThread in both states (a monkeypatched `score_source` records `threading.current_thread().name`).

W0-4f
- F1 RED (edit) `test_w04c_no_async_def_reaches_a_soup_helper_inline` with `_TRANSITIVE_ALLOWLIST = frozenset()` — reports `extract_from_url` today.
- F2 RED `test_w04f_extract_from_url_extractor_runs_on_the_price_parse_pool[amazon|noon|generic x true|1|yes|on]` — `fetch_page` stubbed to a fixture PDP (structured data complete so `extract_with_ai` is not reached), the extractor's thread name recorded via a monkeypatched wrapper on the module global: starts with `price-parse` ON.
- F3 PIN `test_w04f_extract_from_url_flag_off_extractor_inline_on_main_thread[3]` and the pool stays unbuilt.
- F4 PIN `test_w04f_extract_from_url_result_identical_flag_on_vs_off[3 branches x structured|needs_ai]` — `json.dumps(result, sort_keys=True)` equal; `extract_with_ai` stubbed to a deterministic dict in the needs_ai arm.
- F5 RED `test_w04f_extract_from_url_caps_the_parse_input_under_the_flag[2,999,999|3,000,000|3,000,001|3,500,000]` — the extractor stub records `len(html)`: ON -> `min(len, 3,000,000)`; F5b PIN OFF -> whole.
- F6 RED `test_w04f_extract_with_ai_receives_capped_html_on_and_whole_body_off` — a page needing AI, `extract_with_ai` stubbed to record `len(html)`.
- F7 PIN `test_w04f_extract_from_url_honours_a_monkeypatched_extractor_in_both_flag_states` — `monkeypatch.setattr(ues, "extract_generic_data", fake)` is what runs ON and OFF (kills an import-time alias).
- F8 PIN `test_w04f_extractor_exception_propagates_with_the_same_type_in_both_flag_states` — a `ValueError` from the extractor surfaces as `ValueError` from `extract_from_url` ON and OFF.
- F9 PIN `test_w04f_flag_off_never_reaches_run_parse_offloaded_from_extract_from_url` — a spy on `price_service.run_parse_offloaded` records zero calls OFF (kills an unconditional offload).
- F10 PIN `test_w04f_extract_from_url_offloads_under_every_accepted_flag_value` (folded into F2's parametrization).

W0-4g
- G1 RED `test_w04g_pool_stats_is_none_until_the_pool_is_built`.
- G2 RED `test_w04g_pool_stats_after_one_flagged_parse` — `{"workers": <PRICE_PARSE_MAX_WORKERS>, "queued": 0, "jobs_total": 1, "waiting": 0, "running": 0, "peak_waiting": 0 or 1, "peak_running": 1}` (state exactly what the design yields).
- G3 RED `test_w04g_pool_stats_peak_waiting_and_running_under_a_saturating_burst` — pool size 1 (env), three concurrent parses blocked on a `threading.Event`: while held `running == 1`, `waiting == 2`, `queued == 0`; after release `jobs_total == 3`, `peak_waiting == 2`, `peak_running == 1`, `waiting == running == 0`.
- G4 RED `test_w04g_cancelled_waiter_never_leaks_a_waiting_count` — cancel a waiter blocked on the semaphore: `waiting` returns to 0, the slot is not released twice (the existing R-W04 cancel pins stay green).
- G5 PIN `test_w04g_health_has_no_price_parse_pool_key_before_the_pool_exists` (TestClient GET /health, fresh pool state).
- G6 RED `test_w04g_health_carries_price_parse_pool_after_a_flagged_parse` — the key is present with the dict shape of G2.
- G7 PIN `test_w04g_health_handler_stays_a_pure_dict_read` — the same source inspection as `tests/test_health_loop_lag.py::test_health_handler_is_a_pure_dict_read`, plus `"import " not in body` (no import statement inside the handler).
- G8 RED `test_w04g_pool_build_logs_one_grep_stable_info_line` — caplog: exactly one `[PRICE-PARSE] pool built workers=N` INFO record per process build; a second parse logs nothing.
- G9 PIN `test_w04g_flag_off_health_body_byte_identical_after_off_path_parses` — run the OFF path through `_extract_price_from_html_maybe_offloaded` and `extract_from_url`; `/health` JSON (minus the lag numbers) unchanged and without the key.
- H1 KILL `test_w04g_curl_cap_and_render_caps_fire_under_every_accepted_flag_value[curl|firecrawl|scrapedo x 1|yes|on| TRUE ]`.
- H2 KILL `test_w04g_extract_with_ai_prompt_identical_on_vs_off_past_the_4000_char_truncation` — visible text >= 6,000 chars; the captured prompts byte-equal; assert the content slot is exactly 4,000 chars in both.
- H3 KILL `test_w04g_harness_compare_counts_records_missing_on_either_side[fewer|extra]`.
- H4 KILL `test_w04g_harness_compare_against_a_non_payload_json_is_unequal_and_exits_1`.

## 5. Gates (green; all through the process-wide guard plugin — see the workflow prompt)
(a) Unit files green with the flag UNSET and with `=true`: `tests/test_retro_w0_4.py`, `tests/test_retro_w0_4_efg.py`, `tests/test_price_parse_offload.py`, `tests/test_verify_flag_byte_identity.py`, `tests/test_lazy_bh_pdp_backfill.py`, `tests/test_health_loop_lag.py`.
(b) Mutation: every RED/KILL row from byte snapshots (sha256-verified restores) — the four r1 mutants, plus at least: cap kwarg ignored under the flag; `cap=False` at a second caller; the backfill scan left inline under the flag; the `_accept` loop moved into the block; the extractor aliased at import; the cap applied OFF; the cap skipped for `extract_with_ai`'s html; `waiting` decremented after the executor instead of after acquire; stats returning a dict before the pool exists; the `/health` key emitted unconditionally; the INFO line logged per parse.
(c) Comm HEAD over the recorded set (`.qa-s68/comm_set.txt`, derived at red time = every `tests/*.py` referencing `price_service`, `structured_comparison_service`, `url_extraction_service`, `verify_flag_byte_identity`, or `app.main`/`main`), same runner and deselects as CI (`tests/.pre_impl_failures.txt`), `--timeout=60`, chunked; every failure not in that file is re-run in isolation AND at base (a detached scratch worktree at `61585c58`, that file only, removed afterwards) before it counts; a hung node is re-run in isolation before it counts.
(d) Corpus gate over the READ-ONLY root `C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof`: OFF (`--flags ENABLE_PRICE_PARSE_OFFLOAD`) must print OVERALL `9504e5a9...` and results `a1b3460c...`; ON via `--flags-on ENABLE_PRICE_PARSE_OFFLOAD --compare <off.json>` -> `equal=True`, `DIFFERING RECORDS 0 of 1656`; record both digests and wall times. Never run `_proof/sweep2.py`.
(e) `ruff check --select E9,F63,F7,F82 --no-cache` + `py_compile` on every edited module; CRLF hygiene.
(f) The CI-order set (`.qa-s68/ci_order_set.txt`, sorted alphabetically = CI's order) green in ONE process: the six unit files plus every file that pins the touched functions — at base these are `tests/test_bh_registry_curl_timeout.py tests/test_bolo_adapter.py tests/test_cascade_hardening.py tests/test_cascade_parallel.py tests/test_error_middleware.py tests/test_health_loop_lag.py tests/test_js_rendering.py tests/test_jsonld_hardening_i58.py tests/test_lazy_bh_pdp_backfill.py tests/test_llm_provider_base_url.py tests/test_m13_01_slowapi_middleware.py tests/test_openai_breaker.py tests/test_page_scraping.py tests/test_paid_route_metering.py tests/test_price_parse_offload.py tests/test_retro_w0_4.py tests/test_retro_w0_4_efg.py tests/test_retro_w1_1.py tests/test_retro_w1_7_w1_10.py tests/test_retro_w1_9.py tests/test_retro_w2_1.py tests/test_security_hardening.py tests/test_sentry_service.py tests/test_showable_name_identity.py tests/test_sitemap_discovery.py tests/test_ssrf_redirect_hardening.py tests/test_url_compare_category.py tests/test_url_validator_offloop_hops.py tests/test_verify_flag_byte_identity.py` (the red agent re-derives the list by grep and records it).

## 6. Out of scope / stated limits (pr_text must carry them)
- `fetch_page` (httpx, ues) has no size cap in either state; the corpus harness observes neither the cap nor the W0-4c/e/f sites; the five over-cap corpus files unresolved by the manifest; `PRICE_PARSE_MAX_WORKERS` read once (restart); the stats counters are approximate under several event loops in one process (tests only); the two production-equivalent mutants.
- CLAUDE.md corrections for the docs PR (not edited here): the W0-4 row gains W0-4e (backfill exempt + offloaded scan), W0-4f (the three ues extractors on the pool, ues parse input capped), W0-4g (`/health.price_parse_pool`, the `[PRICE-PARSE] pool built` line); activation step (2) points the queue-depth watch at `/health.price_parse_pool.queued|waiting|peak_waiting`.

## 7. Assumptions (and why each beats the alternative)
- Exempting the backfill via a keyword on `curl_fetch_html` beats a second fetch function: one code path, the cap stays the default, the exemption is greppable and pinned to one site.
- Offloading the backfill's regex scan (not only exempting it) beats exempt-only: an uncapped multi-MB `re.findall` on the loop is exactly the class the unit exists for; the cost is one nested block.
- Capping the ues parse input under the flag mirrors the ruled render-leg shape (bounded parse input, unbounded fetch); leaving it uncapped would make W0-4f the only offloaded site with unbounded input.
- Exposing pool stats on `/health` only once the pool exists keeps OFF byte-identical without a flag read in the handler; a `sys.modules.get` read keeps the handler import-free and pure.
- Counters maintained by `run_parse_offloaded` beat reading `asyncio.Semaphore._waiters`: no private asyncio attribute, and `peak_*` gives the canary a value between polls.

## 8. Report contents (red): every file written with its sha256; the red/pin/kill table with verbatim summary lines; each KILL row's mutant diff and red node names; `.qa-s68/comm_set.txt` and `.qa-s68/ci_order_set.txt` written; the satisfiability prototype's result (see the prompt); spec disagreements with measurements; `git status --short` verbatim; scratch worktrees removed (`git worktree list`).
