## tests: process-wide network guard (netguard 04c + curl_cffi), teardown hermeticity sentinel, and the #183 / #185 / #186 leaks fixed at the source

Closes #183, #184, #185, #186.

Test infrastructure only. `git diff --stat -- app/` is EMPTY. There is no feature flag: the guard is always on in the default tier, and `LIVE=1` leaves it uninstalled.

### Defects
- **#184.** Before this PR the free tier had no process-wide network guard. Per-file socket guards miss `curl_cffi`, because native libcurl never calls Python's `socket`. Measured at base 61585c58 under a reference guard, over the full free tier (18,922 nodes in 17 chunks): **681 blocked attempts in total: 680 from 196 nodes in 52 files, plus 1 at collection time**. Four nodes FAILED only because they needed live DNS (the SSRF "valid URL" tests resolving example.com / amazon.ae).
- **#183.** `tests/test_hotfix_shopping_query_clean.py::TestSearchProductPricesIntegration` (3 tests) did `setenv("SERPER_API_KEY", "test-key")` + `importlib.reload(serper_service)`. That left `serper_service.SERPER_API_KEY == "test-key"` for the rest of the process. Probe: `None -> 'test-key'`, same module object.
- **#185.** `tests/test_platform_router.py::test_does_not_import_price_service` deleted `app.services.price_service` from `sys.modules` and reloaded the router. Every by-name binding of price_service was orphaned (probe: collection id != sys.modules id; `fetch_shopify_price.__globals__` no longer the live dict). In CI order, `tests/test_shopify_discovery_l13.py::TestFetchShopifyPrice::test_fetch_uses_catalog_and_matches` then made a REAL curl_cffi GET to shopalmoayyed.com. It failed under a guard and passed in CI only because the live store answered.
- **#186 (root-caused; the issue's hypothesis was half right).** Four W4-3 nodes route through `_run_sync` in `tests/test_prescoring_showable_guard.py`. That helper did `monkeypatch.setattr(real_service, "compute_scores", spy)` on the scoring SINGLETON. Here is the mechanism in pytest 9.1.1 (`_pytest/monkeypatch.py:240`): `setattr` on an INSTANCE snapshots `getattr(target, name)`, which is the class method bound to the instance. `undo()` then SETS that bound method into the instance `__dict__`, where it shadows `ScoringService.compute_scores` for the rest of the process. W4-4's class-level spy was never called: 3 failed / 139 passed in W4-3-then-W4-4 order, 142 passed in reverse. A `__func__` identity check cannot see this, because the shadow's `__func__` IS the original.

### Design
- **`tests/_netguard.py` (new), installed by `tests/conftest.py` at import time.** It runs after the credential neutralisation and before any `app.*` import. It is idempotent and also registered as a pytest plugin.
  - Every non-loopback attempt raises `NetworkBlocked(OSError)`, so fail-open code takes its offline branch, and is recorded.
  - Patch points: `socket.socket.connect` / `connect_ex`, `socket.getaddrinfo`, `socket.create_connection`, Windows `IocpProactor.connect` (recorded as `socket.connect`), and the four curl_cffi points `requests.Session.request`, `AsyncSession.request`, `Curl.perform`, `AsyncCurl.add_handle`.
- **Rules:**
  - **Loopback** is allowed: `localhost`, numeric 127/8, `::1`, `::`, `0.0.0.0`, `''`, `None`, `testserver`, AF_UNIX, plus `QAREN_NETGUARD_ALLOW` extras. A loopback curl `Session.request` may `perform` through a ContextVar hand-off. It is blocked when a call- or session-level proxy is non-loopback. A bare `Curl.perform` is allowed when the handle's `EFFECTIVE_URL` is loopback; this covers the `stream=True` executor path.
  - **IP literals (R6):** `getaddrinfo` is allowed when `ipaddress.ip_address` parses the host (no DNS). Connecting to a non-loopback literal stays blocked. As a result, the SSRF private/link-local literal tests now exercise their real rule; 7 of them no longer attempt at all. Measured: mutating `url_validator`'s private-IP rule to `if False:` turns `test_blocks_private_ip_10_x` and `test_blocks_private_ip_192_168` red (a one-off measurement, restored and sha-verified).
  - **Marker:** `allow_network` (registered in pyproject) lifts the guard for one test. The live-tier markers `live_unit`, `live_db`, `integration`, `bench` and `live_prod` imply it.
  - **LIVE:** under `LIVE=1` nothing is patched, and the summary prints `[netguard] not installed (LIVE=1 opt-in ...)`.
- **Report:** attempts are attributed per node by a `pytest_runtest_protocol` hookwrapper, with `<collection>` for import- or session-time attempts. The hookwrapper's `finally` resets two things, and both resets are pinned.
  - It resets the current node, so an attempt made after the last test (a session-finish hook, atexit) is charged to `<collection>`, never to the last test (R16).
  - It resets `lifted` (R18). An earlier round of this PR called this reset an equivalent mutant (N8), on the grounds that the next runtest protocol sets `lifted` again. That was wrong: after the LAST test no protocol runs again. If the last test carries `allow_network` or a live-tier marker, an attempt from a session-finish hook would go through unblocked and unrecorded without this reset. `test_an_attempt_after_a_lifted_last_test_is_still_blocked` pins it with a synthetic run: the last test is marked `allow_network` and the conftest makes a `getaddrinfo` in `pytest_sessionfinish`. The attempt must raise `NetworkBlocked` and be charged to `<collection>`.
  - Each host is classified `sentinel` (`*.invalid` / `neutralized.*`), `ip_literal` or `egress`, and bytes hosts are decoded. The summary line is `[netguard] blocked N attempt(s) from M node(s)`, where N counts every blocked attempt including `<collection>` ones and M counts real test nodes only. `QAREN_NETGUARD_REPORT=<path>` writes `{blocked, nodes, classes}`.
- **Ratchet:** `scripts/netguard_ratchet.py REPORT [BASELINE] [--write]`.
  - The baseline `tests/.network_attempt_baseline.txt` holds generated `<nodeid> <classes>` lines.
  - Exit 1 on a NEW node whose classes INCLUDE `egress`. Mixed `sentinel,egress` new nodes fail, and that is pinned.
  - A new sentinel-only or ip-literal-only node is a WARNING with exit 0. A baseline node that gains a class is also a WARNING.
  - `<collection>` never fails the ratchet. Exit 2 means the report is unreadable.
  - CI: `QAREN_NETGUARD_REPORT: ${{ runner.temp }}/netguard_report.json` on "Run unit tests", plus a plain following step, "Network-attempt ratchet", running `python scripts/netguard_ratchet.py "$RUNNER_TEMP/netguard_report.json" tests/.network_attempt_baseline.txt`.
  - `test_ci_runs_the_network_attempt_ratchet` parses ci.yml and pins the coupling (R16, R19). It checks exactly these things:
    - the test step's `QAREN_NETGUARD_REPORT` path and the ratchet's report argument name the same file, `netguard_report.json`;
    - both paths sit under the runner temp directory. `${{ runner.temp }}`, `$RUNNER_TEMP` and `${RUNNER_TEMP}` count as that directory; any other directory fails;
    - the ratchet's report argument is not single-quoted, because `'$RUNNER_TEMP/...'` never expands;
    - the ratchet step has no `if:`, `env:`, `shell:` or `continue-on-error`, and the `backend-tests` job has no `continue-on-error`;
    - the ratchet's `run` is one command whose argv is exactly `python scripts/netguard_ratchet.py <report> tests/.network_attempt_baseline.txt`, with no `|| true`, no second command and no extra argument;
    - the ratchet step comes after "Run unit tests".
    Anything else about the runner (a job- or workflow-level override, for example) is not checked here. CI's own exit 2 on an unreadable report remains the arbiter for it.
- **`tests/_hermeticity.py` (new, conftest plugin): a teardown sentinel.** Its session-root autouse fixture is set up first and torn down last, so a leak ERRORs the LEAKING test with `hermeticity: <test> leaked <item>: <before> -> <after>`. The summary line is `[hermeticity] sentinel checked N test(s)`. It checks four items:
  1. price_service is missing from `sys.modules`, or its identity or its package-attribute identity changed;
  2. `serper_service.SERPER_API_KEY` changed;
  3. the scoring singleton's identity changed, or `vars(singleton).get('compute_scores')` changed (NOT `__func__`). The singleton is built lazily (`_scoring_service = None` until the first `get_scoring_service()`). So a singleton that was `None` at setup and EXISTS at teardown must carry no instance-level `compute_scores` either (R15). If it does, the test that created it left the #186 shadow at its source; without this check every later test would snapshot the shadow as its baseline and the failure would land on a victim;
  4. an `app.*` `sys.modules` key was deleted.
- **Fixes at the source:**
  - #183: `monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")` replaces setenv + reload. This is measured sufficient: `_resolve_serper_keys` reads the module attribute, and `_shopping_primary_countries` reads the env per call.
  - #185: the cycle proof runs in a SUBPROCESS, and an in-process pin checks that the identity of the `sys.modules` entry and of the package attribute is unchanged. `_price_service_globals` in `tests/test_w49_extraction_catch_redaction.py` is left as is; it can be simplified later.
  - #186: `_run_sync` uses a PRIVATE `ScoringService()` (`scs.get_scoring_service` is already patched to return it), so the singleton is never touched.
  - SSRF (R5): a test-side resolver stub answers `93.184.216.34` for example.com / amazon.ae, at `socket.getaddrinfo` looked up at call time by both validators. Every other host still goes to the guarded resolver. It never uses allow_network.
  - `test_conftest_env_safety.py::test_sentinel_hosts_really_do_not_resolve_here` gets `@pytest.mark.allow_network`, because resolving the reserved name is its point.

### Flag row
None. The guard has no flag: it is default ON in every non-LIVE run and not installed under `LIVE=1`. Knobs: `QAREN_NETGUARD_REPORT` (report path) and `QAREN_NETGUARD_ALLOW` (extra allowed hosts). Identity proof for the unflagged change: the full free tier's pass/fail set under the guard equals base's set minus the 4 fixed SSRF nodes. Base had 4 failed; now there are 0 failed and 0 errors over the same 18,922 nodes.

### Gates (all under the CONFTEST guard, no `-p qaren_netguard`, `LIVE` and `PYTHONPATH` unset, `--timeout=60` as in CI)
The final fix round was test-only. It edited one pin file and one comment line, and the sentinel did not widen, so (a) through (c) were re-measured on the final bytes. (d) and (e) come from the full-tier run on the same guard code, which this round did not change.
- (a) Unit files in ONE process (`tests/test_hermeticity_pins.py` plus the 10 neighbour and fixed files): **668 passed, 4 skipped, 3 deselected, 0 failed**, `[netguard] blocked 112 attempt(s) from 35 node(s)`, `[hermeticity] sentinel checked 669 test(s)`, ratchet `OK: 35 attempting node(s), baseline 205`.
  - The pin file alone: **80 passed**, `[netguard] blocked 22 attempt(s) from 21 node(s)`, `[hermeticity] sentinel checked 80 test(s)`, ratchet OK 21 vs 205.
  - The pin file has 80 nodes: the 43 drafted at red plus pins added in the fix rounds. Four of the added pins are for R15/R16/R18: two in-process compare pins for the lazy singleton (created with and without a shadow), one synthetic run proving that a session-finish attempt is charged to `<collection>`, and one synthetic run proving that the same attempt after an `allow_network` LAST test is still blocked.
- (b) The four subprocess pins over real files (R9: #183 hotfix->w49, #185 platform_router->l13->w49, #186 in both orders) are inside the pin file and green.
  - Each carries `@pytest.mark.timeout(300)` (R20). Each one runs a whole pytest child over real files. The r4 adversary measured them at 38-56 s on a loaded box (#183 55.51 s, #185 40.62 s, #186[w43_first] 38.51 s), and at CI's `--timeout=60` one of them hit `+++ Timeout +++`. pytest-timeout's per-test marker overrides the CLI value for these four nodes only.
  - This round measured 9-29 s for the four.
  - Marker proof, from a byte snapshot with a sha-verified restore: the #183 pin at `--timeout=5` passed with the marker (1 passed in 22.07 s) and hit `+++ Timeout +++` with the marker removed.
- (c) CI-order set (`.qa-s68/ci_order_set.txt`, 76 files) in ONE process at `--timeout=60`, the value CI passes: **5,808 passed, 42 skipped, 9 deselected, 0 failed**, `[netguard] blocked 46 attempt(s) from 45 node(s)`, `[hermeticity] sentinel checked 5826 test(s)`, ratchet `OK: 45 attempting node(s), baseline 205`. Base 61585c58 had 4 failed / 5,724 passed: the 3 SSRF DNS nodes plus l13 #185. The run used no `--cov`, and the job's other flags are as in CI.
- (d) FULL free tier in the red's 17 chunks. This was re-run in the round that implemented R15, because R15 widened sentinel item 3; it was not re-run in the final round (R18-R21 are test-only): **18,922 run = 18,834 passed / 0 failed / 0 errors / 51 skipped / 37 xfailed**, 127 deselected (base: 18,830 passed / 4 failed, the 4 SSRF live-DNS nodes). **0 `hermeticity:` errors under the widened item 3** (sentinel checked 18,892), so no real test creates the lazy scoring singleton with a shadow on it and no leaker needed fixing. Attempts: **665 blocked in total = 664 from 183 nodes + 1 at `<collection>`** (`socket.create_connection neutralized.supabase.invalid:443`). Base was 681 in total = 680 from 196 nodes + 1 at collection. Node delta vs base: 13 GONE, 0 NEW. That is the 12 nodes this PR fixes (listed under Follow-up campaign) plus one timing-dependent node, explained next.
  - The timing-dependent node is `tests/test_genuine_price_priority.py::TestFlagOffByteIdentity::test_flag_off_timeout_returns_parked_converted`. It made no attempt in that run's chunk 06. Measured elsewhere it does attempt: 3 attempts in the previous full-tier run on the same guard code, in 5 of 5 runs of its file alone, and 2 attempts in a re-run of chunk 06 (`.qa-s68/fix3_chunk_06_rerun.out.txt`). Its lookup races the test's own timeout, so this is the order/timing-dependent attribution named under Stated limits. One other node's attempt COUNT moved (`test_comparison_response_image_url.py::...::test_organic_results_passed_to_image_service`, 3 -> 2); its class did not change.
  - Ratchet over the merged chunks + pins report (`.qa-s68/fix3_netguard_merged_all.json`): `OK: 204 attempting node(s), baseline 205`, exit 0, with the shrink line for that one node. `--write` into `.qa-s68/fix3_regen_baseline.txt` reproduces the committed baseline below the header except for that single line.
  - **The committed baseline KEEPS `tests/test_genuine_price_priority.py::TestFlagOffByteIdentity::test_flag_off_timeout_returns_parked_converted` (R21, accepted in writing).** That one `--write` run omits it, but the node does attempt in other runs. It made 3 attempts in each of 5 file-alone runs (5 of 5; re-read from the saved `flaky_1..5.json` reports this round) and 2 attempts in the chunk 06 re-run. Dropping it would make CI's ratchet fail intermittently on a spurious NEW egress node. When the node does not attempt, the ratchet's `shrink: ... no longer attempts the network` line followed by `OK` and exit 0 is the EXPECTED output, not a regression. Anyone regenerating the baseline with `--write` from a run where it did not attempt must add it back. The full-tier run before that one (same guard code) regenerated the committed baseline byte-identically: 669 in total = 668 from 184 nodes + 1 at `<collection>`, ratchet OK 205 vs 205.
- (e) #185 single-process exposure run (platform_router + every later price_service file): **2,774 passed, 19 skipped, 1 deselected, 0 failed**, `[netguard] blocked 25 attempt(s) from 15 node(s)`, **0 attempts from test_shopify_discovery_l13** (base: 1 failed, 3 l13 nodes doing real curl_cffi GETs), ratchet OK 15 vs 205.
- (f) Mutation from byte snapshots, with every restore sha256-verified.
  - The 56-row table ran on the fix-round-4 bytes: 55 rows red, plus N8, which was then wrongly accepted as equivalent.
  - This round re-ran 14 rows on the final bytes, all red (`.qa-s68/fix5_mutations.jsonl`):
    - N8 (the `lifted` reset dropped) reddens `test_an_attempt_after_a_lifted_last_test_is_still_blocked` (1 failed, 79 passed).
    - A4 (the node reset dropped) reddens both session-finish pins (2 failed, 78 passed).
    - AD1 (single-quoted report path), AD2 (`env: RUNNER_TEMP` override on the ratchet step) and AD5 (`shell:` override on the ratchet step) each redden `test_ci_runs_the_network_attempt_ratchet`.
    - So do the nine earlier CI-coupling rows: MY1, MY1b, MY2, MY3, MY3b, MY4, MY5, CI1 and CI2.
  - The rows of the full table cover:
    - each guard patch point (getaddrinfo, connect, connect_ex, create_connection, Session.request, AsyncSession.request, perform, add_handle, the proactor connect);
    - the IP-literal allowance; the marker lift and the live-tier lift markers; the LIVE lift; the EFFECTIVE_URL allowance; per-node attribution; the private ip_address ref; the proxy check; the 127.-name rule; the sentinel prefixes; the `allow_network` lift on `AsyncCurl.add_handle`;
    - each sentinel item, plus the teardown fail and the arming;
    - R15: removing the created-singleton branch reddens the created-with-shadow pin (1 failed). Widening it to flag every created singleton reddens the created-without-shadow pin and more (5 failed, 1 error). On the real code, reverting #186 and selecting only the two W4-3 sync nodes, so that they are the FIRST to build the singleton, now ERRORs the leaking node at teardown. Before R15 that run was 2 passed with 0 errors;
    - R16: removing the node reset reddens the session-finish pin (1 failed; 2 failed now that the R18 pin also observes it);
    - R18: removing the `lifted` reset reddens the lifted-last-test pin (N8, 1 failed);
    - the CI coupling, each reddening `test_ci_runs_the_network_attempt_ratchet`: a different report file in the ratchet step or in the test step; a different directory in either step (`$GITHUB_WORKSPACE` in the ratchet step, `${{ github.workspace }}` in the test step); `if: always()` on the ratchet step; `continue-on-error: true` on the ratchet step and on the `backend-tests` job; `|| true` after the command; `set +e` ... `true` around it; and (R19) a single-quoted report path, an `env:` RUNNER_TEMP override and a `shell:` override on the ratchet step;
    - the ratchet class rule, a mixed `sentinel,egress` new node, the `<collection>` ignore and class escalation;
    - the three fix reverts and the four SSRF stub reverts.
- (g) ruff `E9,F63,F7,F82` clean and py_compile clean on every edited .py. ci.yml passes `yaml.safe_load`. CRLF hygiene holds: no whole-file diffs. `git diff --stat -- app/` is EMPTY.

### Stated limits
- **Attribution is by the process-wide "current test", not by thread.** An attempt from a thread that outlives the test that started it lands on whichever test is running when it fires. This was measured with a synthetic pair: a daemon thread started in test_p6 looked up a name 0.5 s later, and the attempt was reported under the NEXT test as `[egress]`. In CI's single-process order, a late thread could therefore turn up as a spurious NEW egress node naming an innocent test. None exists today: a single-process full-tree run gave ratchet OK, 204 attempting nodes vs baseline 205. If it ever fires, fix the test that started the thread (join it or mock it), not the named test. Thread-origin attribution was considered and not built. Stamping threads at start would mis-attribute every legitimate attempt from a long-lived pool worker (a module-level ThreadPoolExecutor) to the test that first started it, and that would HIDE new egress behind an old baseline node. The limit is written into the `tests/_netguard.py` docstring.
- **A baseline node that does not attempt only shrinks the set.** When a node in the baseline makes no attempt in a given order or run, the ratchet prints a shrink line and exits 0. This was measured twice: one node in single-process order, and one timing-dependent node in the last full-tier run's chunk 06 (see Gates (d)). The reverse case is not harmless. A node that attempts only in some orders or timings, and is ABSENT from the baseline, appears as a NEW node and fails the ratchet when its attempt is egress. That is the ratchet doing its job, and it is why the baseline keeps the timing-dependent node (see Gates (d)).
- **Per-file guards under-count the report (R10(2), documented, no change).** The guards in the w49 file (`socket_guard`), W4-4 (`_no_network`) and test_retro_w0_4 (`_zero_network`) install over ours with monkeypatch and restore ours. Attempts they catch never reach our report or the ratchet. The w49 file still shows 8 attempts via `socket.create_connection`, which its own guard does not patch.
- **libcurl environment proxies are not seen.** Proxies that libcurl reads from the environment are invisible to the curl proxy check.
- **The Windows proactor connect patch is exercised locally only.** CI runs on Linux with the selector loop, so there the patch is installed but never reached.
- `NetworkBlocked` is raised into the code under test; it does not fail the test. Making an attempt a failure is the follow-up campaign.

### Follow-up campaign (the baseline, by class)
The red measured 196 attempting nodes at base, by target class: 69 api.openai.com, 106 `*.invalid` sentinels (95 exclusively), 28 curl_cffi retailer fetches (noon, Shopify `products.json`, algolia, unbxd, footlocker, sharafdg), 8 SSRF literals and 6 example.com. This PR removes 12 of them: the 4 SSRF live-DNS nodes, the 7 private/link-local literal nodes now allowed by R6, and the allow_network sentinel test. It adds 0. The committed baseline has 205 lines: 184 chunk nodes plus the 21 pin nodes. The class mix of the 184 is egress 79, sentinel 94, sentinel+egress 11, so **90 baseline nodes carry egress; these are the follow-up campaign**. Top files: test_two_input_shape 20, test_streaming 16, test_text_error_envelope_no_raw_exception 14, test_personalization 10, test_flush_live_price_key 9, test_w49_extraction_catch_redaction 8, test_category_selection 7, test_http_400_cap_cut_mapping 7.

### #186 instance-setattr hazard list (AST scan of tests/: `monkeypatch.setattr(<get_*() result or a local bound from one>, ...)`)
The #186 site (`_run_sync`'s scoring singleton) is fixed. The other 8 hits all target `scs.get_comparison_service()`, which returns a NEW instance per call, so none of them shadows a shared object. They are listed and not fixed:
tests/test_algolia_tier2_wiring.py:65 `_get_serper_shopping_price`; tests/test_m13_30_get_price_finally.py:32 `_save_price_to_db`; tests/test_noon_adapter.py:773 `_save_price_to_db`; tests/test_prescoring_showable_guard.py:766 `_fetch_product_data`; tests/test_price_latency_budget.py:125 and :178 `_save_price_to_db`, :185 `_estimate_price_with_gpt`; tests/test_retro_w1_8.py:344 `_save_price_to_db`. The hazard applies to ANY `monkeypatch.setattr(<shared instance>, ...)`. Patch the class or use a private instance instead. For the scoring singleton the sentinel now catches the leaker whether or not the singleton existed before the test (R15).

### #183 reload audit (strong-reference vars() diff before setup / after teardown, one process per file)
Only 7 of the 13 files the spec listed call `importlib.reload`. The other 6 mention it in comments or docstrings only, and were measured clean.

| file | fixture/test | module reloaded | globals changed after teardown | verdict |
|---|---|---|---|---|
| test_hotfix_shopping_query_clean.py | TestSearchProductPricesIntegration (3 tests, inline reload) | serper_service | VALUE SERPER_API_KEY None -> 'test-key' + 41 rebound objects | LEAKS -> FIXED here (monkeypatch.setattr) |
| test_platform_router.py | test_does_not_import_price_service | platform_router (reload) + price_service (del sys.modules) | price_service REMOVED; 16 router objects rebound | LEAKS (#185) -> FIXED here (subprocess) |
| test_backend_cleanup.py | TestLegacyRoutesRemoved::test_main_imports_cleanly | app.main | 21 rebound incl. a NEW FastAPI `app` | LEAKS identity (follow-up) |
| test_fan_out_budget_env.py | 6 reload tests (finally-reload) | firecrawl_service, scrapedo_service | 14 + 11 rebound; values restored | LEAKS identity (follow-up) |
| test_m18_openai_tpm_sizing.py | 2 max_retries tests (+ _restore fixture reload) | openai_service | 14 rebound incl. `client`; value restored | LEAKS identity (follow-up) |
| test_observability.py | 4 sentry init tests (inline reload) | sentry_service | 13 rebound (_before_send, init_sentry ...) | LEAKS identity (follow-up) |
| test_supplement_branch_genuine.py | 2 cde2 tests | source_router | 39 rebound incl. the `Source` dataclass, SOURCE_REGISTRY | LEAKS identity (follow-up) |
| test_cache_service_bounded_transport / test_limiter_endpoint_key / test_nasser_adapter / test_password_reset_deep_link / test_retro_w1_1 / test_w49_extraction_catch_redaction | - | - | none | harmless |

**Issue to file after merge (R4):**
> **tests: five importlib.reload sites leak module IDENTITY (the reload audit of session 68)**
> The session-68 reload audit (strong-reference `vars()` diff before setup / after teardown) found five test files whose `importlib.reload` leaves the module's objects REBOUND for the rest of the process. The values are restored, but the identity is not. Any module that bound a name at collection time then holds a stale object. None trips the #183/#185/#186 sentinel today and none moves a value, but each is the same class of hazard that produced #185:
> - `tests/test_backend_cleanup.py::TestLegacyRoutesRemoved::test_main_imports_cleanly` reloads `app.main` (a NEW FastAPI `app`; 49 test files bind `from app.main import app` at module level)
> - `tests/test_fan_out_budget_env.py` (6 tests) reloads `firecrawl_service` + `scrapedo_service` (`source_router` binds `scrapedo_service._super_enabled` lazily)
> - `tests/test_m18_openai_tpm_sizing.py` (2 tests + fixture) reloads `openai_service` (new `client`; `image_routes` binds `identify_products`, 3 modules bind `get_client`)
> - `tests/test_observability.py` (4 tests) reloads `sentry_service` (`app.main` binds `init_sentry`)
> - `tests/test_supplement_branch_genuine.py` (2 tests) reloads `source_router` (the `Source` dataclass is replaced, so an isinstance check against the old class fails)
> Fix per file: build a PRIVATE module instance via `importlib.util.spec_from_file_location` + `module_from_spec` under the real dotted name (the W0-3 pattern in `tests/test_cache_service_bounded_transport.py`), never touching `sys.modules`. `monkeypatch.setattr` does not apply where the test exercises import-time construction. Add each module to `tests/_hermeticity.py` only if a value-level item is needed.

### #185 exposure measurement
At base, one process ran `tests/test_platform_router.py` plus every later-alphabetical test file that mentions price_service. Result: 1 failed (l13 `test_fetch_uses_catalog_and_matches`), 2,773 passed, and 3 TestFetchShopifyPrice nodes made real curl_cffi GETs to shopalmoayyed.com. After this PR: 0 failed, 2,774 passed, and 0 network attempts from any test_shopify_discovery_l13 node (15 attempting nodes in that run, all in the baseline).

### Follow-ups
- The R4 issue above.
- The attempting-node campaign by class (the 90 egress-class baseline nodes, api.openai.com first).
- Simplifying `_price_service_globals` in the w49 file.
- Per-file guards delegating to `NetworkBlocked` so the report counts them.
- A child pytest process in the CI-order set inherits `QAREN_NETGUARD_REPORT` and overwrites the report mid-run; the parent rewrites it at session end, so the final report is correct. The child should drop the variable.
- Optionally, thread-origin attribution for the late-thread limit (see Stated limits).

### CLAUDE.md corrections for the docs PR
- The "Next" line of the SESSION 67 block ("the repo-wide netguard 04c (with curl_cffi, issue #184)") is DONE by this PR. The "Until 04c lands: every new test file carries its own guard AND the unit set is run in CI order" rule is replaced: the conftest guard is process-wide, and the ratchet fails a NEW egress node.
- #183/#185/#186 in the SESSION 67 "Four latent hazards" bullet are CLOSED. #186's mechanism is the pytest instance-setattr pin-on-undo, not a second singleton.
- The Tests section: `allow_network` marker, `QAREN_NETGUARD_REPORT`, `tests/.network_attempt_baseline.txt` (regenerate with `python scripts/netguard_ratchet.py <report> --write`, never hand-edit), and `[netguard]` / `[hermeticity]` summary lines on every run.
- "`test_rate_limiting_complete.py` does a real GET" (Known RED-by-design paragraph) is stale. Its only live dependency was DNS for amazon.ae, now stubbed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

### Corrections applied at ship time (Fable, after the round-5 adversary)
- The CI pin's "runner temp directory" sentence above is broader than the pin: GitHub Actions does not shell-expand `env:` values, so on the TEST step only `${{ runner.temp }}` is a valid spelling; `$RUNNER_TEMP` there would make netguard write to a literal relative path, print `[netguard] report write failed`, and the ratchet would exit 2 (loud, never a silent pass). The pin accepts the `$RUNNER_TEMP` spellings on the test step; rejecting them there is a one-line tightening recorded as a nit, not a defect.
- "An attempt after the last test (a session-finish hook, atexit) is charged to `<collection>`": an `atexit` attempt is still BLOCKED (the lifted and node resets hold) but it fires after `pytest_terminal_summary` has written the report, so it is charged to `<collection>` in memory only and never reaches the report or the ratchet. Session-finish-hook attempts are both charged and reported, which is what the R16/R18 pins prove.

---
Session 68 unit. Pipeline: red (43-node draft, full-tier measurement 18,922 nodes / 681 attempts) -> Fable gate R1-R14 -> green -> adversary r0/r1/r2 with two fix rounds -> Fable R15-R17 (first-creator #186 shadow; node-reset pin) -> fix r3 + full tier re-run under the widened sentinel -> adversary r3 -> fix r4 (CI pin yaml-parsed) -> adversary r4 -> Fable R18-R21 (the lifted reset is NOT equivalent, pinned; env/shell/quoting checks on the ratchet step; 300 s marker on the four subprocess pins; the kept baseline node accepted in writing) -> fix r5 -> adversary r5 SOUND. Rebased onto current main; ship checks recorded in the PR comments.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
