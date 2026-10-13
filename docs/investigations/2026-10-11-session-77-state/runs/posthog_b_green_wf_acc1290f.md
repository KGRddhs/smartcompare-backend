# GREEN report

Report file not written: the harness refused to write `report.md` ("Subagents should return findings as text"), so the full report is below.

**Result:** GREEN for S77 POSTHOG part B. The RED set passes 139/139, the comm gate shows no branch-only failures, and the legal machinery is byte-identical. One target is missed and needs a ruling: the PG11 loop-cost p99 on this Windows box is 5.688 ms against the < 2 ms target (G5 and deviation 1). Nothing is committed. Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s77-posthog`, base 18121839.

## Files (final sha256)
Every edited file is still CRLF, no non-ASCII byte was added, and `git diff --stat` shows 15 files changed, 201 insertions, 15 deletions, with no whole-file diff.

| file | sha256 |
|---|---|
| app/services/product_analytics_service.py (new, ASCII, CRLF) | 32674adb42b785e7fdc56ca6cf2049ec3507755b3f500da4bbe229727116d11e |
| app/services/feedback_service.py | 0253245ea0bc41c53abe1b61b41b63a2cfb3d5f47180b10548d9a7ce3c05b20c |
| app/services/database_service.py | ea8fe241b7fbd8b05c6109edeb255e4f72f80ad8c50d6b24f0d4c49c3ab064bb |
| app/api/text_routes.py | 99eb77fe334560b601ab76cce16524e88d9f391792fd819deb66fe530c7e2ee5 |
| app/api/auth_routes.py | 347001a70a8a86a7b13846e9d6ab7afafc3cb980eacd4cd25f8c96f7d9b78ac7 |
| app/main.py | 6773d13f623ffdb75cf85ef7bbd18b3f789cecc3a88943efd267267d97f50a16 |
| requirements.in (BOM kept) | 519d8328023234e35b88a511767f71b5ddca2770ce97667a22b99d2159053cd8 |
| requirements.txt (uv output, converted to CRLF) | 055e8118533756293b23fab5192ce441f938bb042fa22441648bb5f5c31478d8 |
| requirements-dev.txt | unchanged, 4ad0abac9536824191e5524d59840e7184586b28e61f013751684abc46df5629 |
| tests/_env_safety.py | 1315807d87f7dd5b4549f7fd5d362624c0bc0042e1ed766d41223bf55e94c7e5 |
| tests/test_conftest_env_safety.py (the PG7 pin) | 287552ea35aeece5172ec7a82ac064642d1039cb6a0960eea565e6a3d7e5aeb7 |
| scripts/fill_in_legal.py | 8921307fa7a19315a2c7e2a47f95a2a3f6bfaa6b66f56417620f3f053a13e8dd |
| tests/test_legal_docs_u8.py | 2a25a599182977d779c95401d6a47b01859fe8570a22002730b823c026139746 |
| tests/fixtures/legal_fill_in_u8.json | 0d640447c4de1f6a2a9e77c5c8f715980ede3cf6a8af2ef007e56a9b647a9c29 |
| app/legal/processors.json | 5070803aedc0bd0dc3915cadc5e2bbddc029d909557f63181f3a616f8bf575b0 |
| CLAUDE.md (two flag rows plus a header line) | f2df4b04e35fb46df3ebbea69de5ddf976009a915671c4946aba382f5d9297fe |
| tests/test_s77_posthog_server.py (RED, untouched) | 488e75a6784a3f90ff0837280418fe463a09caa8ef87e3fbd15f474435816b9b |
| tests/test_shutdown_drain.py (RED, untouched) | 91ad84ae81662e42d0999dbd1c9c9694020c917e29b1aa36adb8f4e9c2a935b0 |

## Gates
**G1 (RED set): 139/139 pass.**
- `[pyt] tag=ph-g1b elapsed=10s status=OK rc=0`: 139 passed.
- The final run with the legal and env-safety files: `[pyt] tag=ph-g1-final elapsed=27s status=OK rc=0`, 343 passed, 1 skipped, 2 deselected.

**G2 (legal machinery): byte-identical.**
- Snapshot of 26 legal files: app/legal/*, landing/**/*.html, the prefill fixtures, legal_variants_u8.json, legal_fill_in_u8.json and legal_d3c_u8.json.
- `python scripts/fill_in_legal.py --dry-run` returned rc 0 with no "would write" line. The real run returned rc 0 with no "wrote" and no "rendered" line.
- All 26 files have the same sha256 before and after.
- `render_legal_landing.py --check` returned rc 0.
- `[pyt] tag=ph-g2-legal elapsed=13s status=OK rc=0`: 180 passed across u8, u8_d3c, u8_polish, legal_disclosure_s77 and legal_routes.

**G3 (comm gate): branch-only-NEW is empty.**
- The set has 149 files in 6 chunks of at most 25:
  - 145 found by the reference grep;
  - the 12 source-scanning pins;
  - the drainingSeconds pins;
  - the 2 RED files.
- The base was a detached worktree of 18121839 under notes/phgreen/base, run without the RED server file. It was removed afterwards with `git worktree remove --force` (rc 0; it had no node_modules).

| chunk | base | head |
|---|---|---|
| 0 | 29s, FAIL rc=1 (2 failed, 959 passed) | 22s, FAIL rc=1 (2 failed, 959 passed) |
| 1 | 46s, FAIL (3 failed, 494 passed) | 39s, FAIL (3 failed, 494 passed) |
| 2 | 84s, OK (495) | 58s, OK (495) |
| 3 | 60s, OK (576) | 27s, OK (576) |
| 4 | 138s, OK (1373) | 124s, OK (1491) |
| 5 | 63s, OK (831) | 61s, OK (832) |

- The 5 failures are identical on both sides:
  - test_auth_interceptor.py::test_sign_in_with_social_exception
  - test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
  - test_camera_vision.py::TestIdentifyProductsMocked::test_empty_product_fields_normalized
  - test_camera_vision.py::TestIdentifyProductsMocked::test_malformed_response_returns_error
  - test_camera_vision.py::TestIdentifyProductsMocked::test_successful_identification
- `comm -13` and `comm -23` are both empty.
- Head passes 119 more nodes than base: the 118 RED server nodes plus the 1 new drain node.
- The netguard counts are identical per chunk on both sides.

**G4 (flag-OFF identity): no client and no new call.**
- The RED flag-OFF pins are green.
- The measurement script runs in conftest order (neutralize_credentials, the dotenv guard, the netguard). After `import app.main` there are no posthog modules in sys.modules.
- After a flag-OFF `capture_compare_completed` plus `capture_compare_failed` there are still no posthog modules, the client is None and the preference cache holds 0 entries.

**G5 (PG11 measurement): target missed on this box.**
- Setup: the real posthog 7.60.1 client with sync_mode=False. The consumer's `batch_post` and `_send_v1_batch` were monkeypatched to no-ops, `requests.Session.send` refuses, and the netguard was on. There were 0 HTTP attempts and 0 netguard blocks, and sends never ran on the loop thread.
- Run 1, capture on the loop: p50 30.23 ms, p99 51.36 ms. cProfile puts 100% of the time in `posthog.utils.system_context()`, which calls `platform.win32_ver()` and runs a WMI query on every capture (Windows only). This triggered the spec 4.3 fallback, so `client.capture` now runs in `asyncio.to_thread`.
- Run 3, the shipped code on the real Windows path: the longest loop stall per capture is p50 0.237 ms, **p99 5.688 ms**, max 39.7 ms. The idle baseline p99 is 0.003 ms, and the property build on the loop is p99 0.013 ms. Wall time per capture is p50 36.7 ms. The 5.7 ms p99 matches the 5 ms GIL switch interval while the worker thread runs the WMI read.
- Run 4, supplementary and not the shipped environment: with `win32_ver` memoised as a stand-in for Linux's cached `distro` read, the loop stall is p50 0.101 ms, p99 0.366 ms, max 1.02 ms. A bare on-loop capture there is p99 0.143 ms.
- The first client build (import plus constructor), run in to_thread: 78.6 to 88.7 ms. `flush(timeout_seconds=)` exists on 7.60.1 (signature measured). The posthog logger level after build is CRITICAL (50).

**G6 (lint, syntax, lock): clean, and the lock reproduces.**
- ruff `--select E9,F63,F7,F82` reports "All checks passed!" on all 10 changed .py files, and py_compile returns rc 0.
- `uv pip compile requirements.in -o requirements.txt --universal --python-version 3.12` was run twice. The second output is byte-identical to the first.
- The dev lock compile was also run twice; its content is identical to the committed dev lock, so it is unchanged.
- New lock lines:
  - posthog==7.60.1
  - backoff==2.2.1 (via posthog)
  - distro==1.9.0 (via posthog)
  - posthog added to the via blocks of requests and typing-extensions
- pip-audit was not run.

## The PG3 case that applied
Not threaded. At 18121839 the route's preferences object is only set when `success and preferences_completed` (text_routes.py:603, :820, :1005), and it can be cohort-seeded.
- The three direct callers pass only `input_type`.
- `track_after_persist` has no `preferences` argument.
- The capture reads users.preferences through asyncio.to_thread plus the 300 s cache.

## Ruling deviations and questions (should be none; these need a decision)
1. **Executor for the capture.** The spec says to use the "default executor, NOT the adapter executor". In this app the loop's default executor is the qaren-worker adapter pool (app/utils/executor.py:62-64), so the captures and the PR5 preference read run there. I did not add a dedicated executor without a ruling.
2. **PG11 target.** p99 < 2 ms holds only in the Linux stand-in (0.366 ms). It is missed on the Windows box (5.688 ms). Linux itself could not be measured here.
3. **PG5 path.** I used `POST /api/projects/{id}/persons/bulk_delete` without a trailing slash, as the docs show it. Source: context7 /posthog/posthog.com, docs/privacy/data-storage.mdx (returns 202, `events_queued_for_deletion` is a boolean, `deletion_errors` is an array). The docs do not say whether the arguments go in the body or the query; I followed the RED pin (JSON body). Not verified live.
4. **PG7 pin location.** The two names were added to `_CONTRACT_UNSET` in tests/test_conftest_env_safety.py, a file outside the expected list.
5. **PG2 count pins.** No numeric pin counting seven exists. Instead:
   - The "seven" texts now say "eight" (the test schema docstring, the gate_flag message, the fill_in docstring).
   - The fixture gained one comment key, `_s77_posthog_comment`, because its main comment says flags are recorded from production by the orchestrator.
6. **Network use outside pytest.**
   - The uv compile read PyPI. An offline compile failed ("posthog was not found in the cache"), and the compile was assigned as CLAUDE.md shows it.
   - Two context7 documentation queries were made for PG5.
7. **Extra constructor knobs.** The constructor also passes the spec 4.3 values max_queue_size=1000, flush_at=50, flush_interval=5.0, timeout=5 and max_retries=2. They are not pinned.

## Stated limits
- The real client adds server-environment `$` properties to every event: lib/version, `$geoip_disable`, `$is_server`, python version and OS. They carry no user data; `before_send` drops only `$ip`.
- The preference cache and the deleted-user set are per process and in memory. Another process can capture for up to 300 s after a user turns analytics off.
- A user whose erase fails stays marked deleted in that process until a restart (fail-closed).
- A construction failure is retried on every capture, with one warning each time.
- With ENABLE_SEARCH_LOG_TRUTH OFF, stream failure terminals, abandoned streams and Link-mode failures send no `server_compare_failed` (PR4).
- The shutdown bound only frees the loop; the flush thread can run until interpreter exit. A SIGKILL or OOM loses the queue.
- A key or host change needs a restart.
- The G5 numbers come from Windows only.
- Production was not probed, Railway was not read, and no .env file was read.

## pr_body_notes
**What changes**
- **New module.** `app/services/product_analytics_service.py`:
  - a lazy posthog 7.60.1 client built in to_thread (sync_mode=False, geoip and exception autocapture off, `$ip` dropped, errors logged by type only, the posthog logger set to CRITICAL);
  - `capture_compare_completed` and `capture_compare_failed`, with the capture call itself in to_thread;
  - a fail-closed preference read in to_thread with a 300 s / 2048-entry cache;
  - B2 `request_person_deletion`: flush an existing client, POST bulk_delete, log counts only.
- **Capture call sites.**
  - `track_after_persist(input_type=)` captures before its falsy-id return, for `success True` only.
  - The composite and the 3 direct text callers pass input_type ("text", "text", "text_stream").
  - `log_search` captures signed-in failure rows.
- **Routes and shutdown.**
  - The toggles route accepts `analytics_enabled` alone, invalidates the cache entry, and echoes the key only when it was sent.
  - DELETE /account marks the user before the erase and fires the person deletion after it.
  - main.py adds `POSTHOG_SHUTDOWN_FLUSH_TIMEOUT = 1.0` and `_flush_product_analytics`, registered after the drain.
- **Legal and dependencies.**
  - ENABLE_POSTHOG_SERVER_CAPTURE is the eighth fill-in flag, set "off", and the PostHog row in processors.json is gated on it.
  - The fill-in re-run is byte-identical.
  - posthog is pinned in the locks, and _env_safety neutralises the two PostHog keys.

**Flags and activation order**
All flags default OFF and are read per call. The exception is POSTHOG_PROJECT_API_KEY and POSTHOG_HOST, which apply at first construction and need a restart to change.
1. Unit L is live: the fill-in value is "on" and the PostHog text is published.
2. The owner's PostHog EU project: "Discard client IP data" ON, exception autocapture OFF, DPA signed, and either the free plan or changed retention text.
3. ENABLE_SEARCH_LOG_TRUTH=true is confirmed on web.
4. Turn on ENABLE_POSTHOG_PERSON_DELETE, POSTHOG_PERSONAL_API_KEY and POSTHOG_PROJECT_ID (POSTHOG_API_HOST optional).
5. Set the project key, then turn on ENABLE_POSTHOG_SERVER_CAPTURE. Canary: one own-account compare shows one server_compare_completed with no `$ip` or `$geoip_*` property.
6. Then the client OTA.

Rollback: unset the flag.

**Stated limits**
As listed above.

Working notes and evidence are in `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/b66a80d9-2bd6-44b5-bde6-1370a9fa1121/scratchpad/notes/phgreen/`, including notes.md, comm/, g5_run1-4 JSON, legal_sha_before/after.json and g4_g5_measure.py.

# ADVERSARY report

**Verdict: NOT READY.** There is one MAJOR privacy defect (F1): the analytics opt-out is wiped by two other routes that write `users.preferences`. The fix is small and sits in a file the unit already edits. Everything else is MINOR.

**Gates I re-measured on the GREEN tree**
- RED set before probing: `[pyt] tag=phadv-base elapsed=9s status=OK rc=0`, 139 passed.
- RED set after every mutant was restored: `[pyt] tag=phadv-post elapsed=9s status=OK rc=0`, 139 passed.
- Toggles (w314) and Sentry (u8d) pins: `[pyt] tag=phadv-adj elapsed=11s status=OK rc=0`, 159 passed.
- Legal T7 baseline: `[pyt] tag=phadv-legal-base elapsed=4s status=OK rc=0`.
- `scripts/fill_in_legal.py --dry-run` returned rc 0 with no "would write" line, and `render_legal_landing.py --check` returned rc 0. The fill-in round trip is byte-identical.
- ruff E9/F63/F7/F82 and py_compile are clean. The new module is ASCII with CRLF line endings.
- Real posthog 7.60.1 adds only `$geoip_disable $is_server $lib $lib_version $os $os_version $python_runtime $python_version` to an event. It adds no `$ip`, no hostname and no person data.
- Lock file: `requirements.txt` entries for backoff, distro and requests match posthog's Requires-Dist. I did not run `uv pip compile` (that needs the network).
- Neither key reaches logs or Sentry: the constructor logs no key, the logger is set to CRITICAL, `on_error` and B2 log the type or counts only, and the Bearer key travels only in the request header.

## Findings
**F1 MAJOR — the analytics opt-out does not survive the other writers of `users.preferences` (reproduced).**
- `PUT /api/v1/auth/preferences` (`save_preferences`, auth_routes.py:1266, :1276, :1292) saves `body.model_dump()` as the whole preferences object.
  - `UserPreferencesRequest` (auth_routes.py:218-232) has no `analytics_enabled` field.
  - So a stored `analytics_enabled: False` is erased on every Edit-Preferences save, even when the client sends the key.
  - Capture then resumes, because the default is ON (`_allowed_by` returns True).
  - Probe P4 confirmed it. The saved keys were `[_sources, ai_sharing_enabled, brand_attitude, budget, lifestyle, notification_types, notifications_enabled, priorities]`.
- The cohort seed path does the same (auth_routes.py:1606-1609). `should_seed({"analytics_enabled": False})` returns True (P5), and the seed replaces the whole object.
- Fix: carry `analytics_enabled` over from the existing preferences in both writers, and make `should_seed` ignore toggle-only keys. Add a pin for each.

**F2 MINOR — the preference cache can go stale in the same process (P1).**
- A read that is in flight when the toggles route writes False and calls `invalidate_analytics_preference` stores its stale True after the invalidation (product_analytics_service.py:233-239).
- Later compares in the same process are then captured for up to 300 s. The stated limit only names "another process".
- Fix: a per-user generation counter that invalidation bumps; the read stores its result only if the counter is unchanged.

**F3 MINOR — the deleted-user check runs before the awaits (:368, :390) (P2).**
- A capture whose preference read is in flight when the deletion route marks the user is still sent.
- This contradicts the CLAUDE.md row's "even one racing the erase".
- Fix: re-check `_deleted_users` in `_send`, right before `client.capture`.

**F4 MINOR — B2 builds a new `httpx.AsyncClient` on the event loop for every deletion (:428).**
- Measured on this box over 30 runs: minimum 179 ms, p50 181 ms, maximum 266 ms of blocking (SSL context and certificate load).
- Spec 4.5 said to use the existing async client. Build it once, or build it in `to_thread`.

**F5 MINOR — PH9 gap: links without a scheme keep their query string (:250-255).**
- `_SAFE_EXC_URL_RE` only matches `scheme://`. The query `www.noon.com/p/x?...&token=SECRETVALUE vs ...` passes through unchanged (P6).

**F6 MINOR — a failed preference read is not cached, and its thread is unbounded (:233-237).**
- Every capture re-reads after a failure (P7: 3 captures produced 3 reads).
- The read has no timeout of its own, so it can wait as long as the Supabase client allows: 120 s when `ENABLE_SUPABASE_CLIENT_REUSE` is OFF (prod state not verified).
- It runs on the default executor, which in production is the `qaren-worker` adapter pool (app/utils/executor.py:64). Spec 4.3 said "NOT the adapter executor".
- During a Supabase brownout, every capture parks one adapter-pool thread.

**F7 MINOR — the capture now delays existing work (feedback_service.py:106 vs :121).**
- `track_after_persist` awaits the capture (preference read, plus the first client build) before its four existing follow-ups: the home:savings cache bust, the user_events row, the critique write and Referral Loop 2.
- P8 measured a 0.39 s delay for a 0.4 s read. The worst case is the Supabase timeout, and the 8 s shutdown drain can then abandon the follow-ups.
- Fix: capture after the follow-ups, or run it as its own fire-and-forget task.

**F8 MINOR — URL-compare events carry almost nothing.**
- `compare_from_urls` returns `category_used`, a top-level `products` list and `winner_index`, with no `overview`, `metadata` or `query` (url_extraction_service.py:680-689).
- Its `server_compare_completed` event therefore has null category, products, prices and winner.

**F9 MINOR — the shutdown arithmetic leaves out posthog's own exit flush.**
- posthog registers its own flush at interpreter exit for `sync_mode=False` (client.py:1068), bounded at 1.0 s (`_ATEXIT_FLUSH_TIMEOUT_SECONDS`, client.py:139).
- It runs after lifespan shutdown whenever the shutdown flush ran out of budget. Worst case: 20 + 8 + 1.25 + 1.0 = 30.25 s, against a 30 s window.
- The shutdown flush can also queue behind a saturated `qaren-worker` pool and then run again at exit.

**F10 MINOR — test gaps.** Five mutants survived (table below). Nothing pins the PG6 invalidation, the PG9 response key, the deleted-user check on the failure event, the `price_found`/`unavailable` rule, or the capture running off the loop.

**F11 MINOR — documentation.**
- The B2 flag row does not state the "unit L live first" precondition, yet B2 sends user ids to eu.posthog.com. The PostHog `processors.json` row is gated only on `ENABLE_POSTHOG_SERVER_CAPTURE`.
- The fixture's `_comment` still says "seven flags".

**Lens 4 and lens 5 (no defect):**
- Flag OFF is byte-identical on every surface checked: the RED pins are green, and mutant M19 is equivalent.
- The T7 legal gate passes for the right reason; no exemption was added. Removing the PostHog row breaks T7b ("unmapped eu.i.posthog.com, eu.posthog.com"). Setting the gate flag to null, or recording the flag "on", breaks T7a ("does not name PostHog"). Narrowing the row's host breaks T7b.

**B2 order** is mark → erase → (fire-and-forget) flush → bulk_delete. That satisfies PR2 (flush before bulk_delete) and spec 4.5 (after the erase). The lens shorthand "mark → flush → erase" is not what PR2 says.

**Not verified** (no network grant): the `persons/bulk_delete` path and its trailing slash, `uv pip compile` currency, prod `ENABLE_SUPABASE_CLIENT_REUSE`. I did not re-measure PG11; GREEN's own missed p99 target stands.

## Mutation probes (34 total: 30 against the RED files, 4 against the legal T7 tests)
| Result | Mutants |
|---|---|
| Killed | M01 `$ip` drop · M02 deleted check (completed) · M04 `_allowed_by` · M05 missing row fail-open · M06 read error fail-open · M07 cache TTL · M08 partial · M09 link reduction · M11 B2 flush · M12 logger CRITICAL · M13 explicit `enable_exception_autocapture` · M14 error_class · M17 mark after erase · M18 log_search success rows · M20 outer bound +30 · M21 inner flush timeout · M22 PR3 success check · M24 read on loop · M25 query cap · M26 name cap · M27 build on loop · M28 route-preferences path · M29 reset hook · M30 composite input_type · L01–L04 legal |
| **Survived** | **M03** (`capture_compare_failed` deleted check removed, :390) · **M10** (`price_found` ignores `unavailable`, :310) · **M15** (`invalidate_analytics_preference` removed, auth_routes.py:1518) · **M16** (response `analytics_enabled` key removed, :1519) · **M23** (`client.capture` on the loop thread, :348) |
| Equivalent | **M19** (`if True:` in place of the flag check, feedback_service.py:106): `capture_compare_completed` re-checks the flag itself, so behaviour is unchanged |

Each mutant was applied from my byte snapshot and restored from it, with a sha check after every restore. The mutation lock was created and then removed. A temporary probe file (`tests/test_zz_phadv_probe.py`) was copied in and deleted.

**pre.sha == post.sha: IDENTICAL (17 files)**

I wrote nothing in the worktree. Files are in `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/b66a80d9-2bd6-44b5-bde6-1370a9fa1121/scratchpad/notes/phadv/`:
- pre.sha
- post.sha
- notes.md
- test_zz_phadv_probe.py
- mut.py
- mut_results.jsonl
- mut_*.log
- probe.log
- asyncclient_cost.py
- real_props.py
