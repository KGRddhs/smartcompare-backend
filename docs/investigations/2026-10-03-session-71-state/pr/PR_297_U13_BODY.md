## U13 - the paid routes require a caller (`ENABLE_COMPARE_AUTH_REQUIRED`, default OFF)

Spec: `docs/investigations/2026-10-03-session-71-state/U13_COMPARE_AUTH_SPEC.md` (body + Review corrections C1-C11 + Orchestrator rulings UR1-UR15 + RED gate UG1-UG6). Base `eb86075e`.

**Why.** On 2026-10-02 production served 322 anonymous `/api/v1/text/compare` calls in 27 active minutes from 155 rotating addresses (`python-httpx` / `python-requests`), peak 51/min, zero 429. It cost nothing only because OpenAI is unfunded. The owner ruled that the paid routes must require a caller BEFORE OpenAI is funded. The repo is public; the app is login-gated, so real users always hold a session.

### Flag

| Flag | Default | Read | Effect ON | Rollback |
|---|---|---|---|---|
| `ENABLE_COMPARE_AUTH_REQUIRED` | OFF | per call, `text_routes.compare_auth_required_enabled()` (`1/true/yes/on`, trimmed, case-insensitive) | U1-U6 (POST/GET `/api/v1/text/compare`, GET `/api/v1/text/compare/stream`, POST/GET `/api/v1/url/compare`, POST `/api/v1/image/identify`) need a signed-in user OR a valid `X-Admin-Key`; A1-A4 (POST `/text/quick`, GET `/text/prices/{product}`, POST/GET `/url/extract`, no app caller, unmetered for users) need a valid `X-Admin-Key`. Anonymous -> 401 `{"success":false,"error":"Sign in to continue.","code":"AUTH_REQUIRED","request_id":...}` before ANY work (usage gate, prefs, anon gate, DNS/SSRF, `log_search`, every provider leg, schema/query 422s and the slowapi bucket). A present, wrong `X-Admin-Key` -> 403 `FORBIDDEN` "Invalid admin key". SSE refusal is a JSON 401, never a stream. | unset the variable (per call, immediate) |
| `HARNESS_SEND_ADMIN_KEY` (script env, not a server flag) | unset | per call in each harness script | the script sends `X-Admin-Key: $ADMIN_API_KEY` only when this is truthy AND `ADMIN_API_KEY` is non-empty | unset |

### What changes with the flag OFF: nothing (measured)
- Both guards return before reading any header when the flag is off (no log, no call).
- T17: 30 flag-OFF records (10 routes x anonymous / valid bearer / rejected bearer: status, body, SSE text, stub call counts, `verify_token` count) recorded at base `eb86075e` into `tests/fixtures/s71_u13_flag_off_baseline.json` and compared record by record - green, fixture never re-recorded.
- T23: the full OpenAPI operation of all 10 routes plus the `$ref` closure they use is unchanged (the guards read `request.headers`, never a declared `Header(...)`; U1-U6 reuse the handlers' own `Depends(get_optional_user)`, so the dependency cache keeps ONE `verify_token` per request).
- Adversarial flag matrix (20 env configs x 10 routes x 8 caller shapes = 1,760 records, incl. strict/metering/anon-gate combinations and admin-header callers) and a 320-request edge probe: base == head, 0 diffs; the app's JSON log stream identical, 0 `[paid-auth]` lines with the flag off.

### Implementation
- `app/api/text_routes.py`: `compare_auth_required_enabled()`, `_PAID_AUTH_DETAIL`, the four D7 reason constants, `_paid_route_label` (method + route TEMPLATE, `?` fallback), `_refuse_paid_route`, `_admin_credential_passes` (absent/empty header = no attempt; otherwise `admin_routes.verify_admin_key` verbatim: bytes, surrogateescape, `hmac.compare_digest`), `require_paid_route_user` (flag ON: a resolved user passes without consulting the admin header; else a valid admin credential passes and the route runs as today's anonymous caller - no usage consumption, no history row; else 401 `BEARER_REJECTED` / `NO_CREDENTIAL`), `require_paid_route_admin` (never resolves a bearer; 401 `ADMIN_REQUIRED` / `NO_CREDENTIAL`, 403 on a wrong key).
- Attached with the ROUTER decorator `dependencies=[Depends(...)]` on the ten routes; handler signatures and bodies unchanged; nothing between `@limiter.limit` and `async def`. `url_routes` / `image_routes` import the guards from `text_routes` (one definition).
- Logging (D7/UR6): exactly one INFO `[paid-auth] refused route=<METHOD> <template> reason=<CODE>` per refusal and one `[paid-auth] admin credential accepted route=...` per admin pass. Never a token, header value, IP/host, query, body or concrete path (INFO lines ride as Sentry breadcrumbs).
- Not edited: `auth_routes.py`, `admin_routes.py`, `error_handler.py`, `rate_limiter.py`, `main.py`, `backend/app/`, `SmartCompareApp/`, requirements, `tests/.pre_impl_failures.txt`, any existing test or fixture, `CLAUDE.md`.

### Harness (D9, opt-in)
- `scripts/eval_runner.py` `harness_auth_headers()`, merged with `synthetic_traffic_headers()` in `run_eval` (so `cron_eval_nightly` inherits); the price-KPI admin path unchanged.
- `scripts/run_validation_matrix.py`, `scripts/bias_matrix_probe.py`, `docs/investigations/2026-09-29-session-69-state/verify_after_credits.py`: an inline `_harness_auth_headers()`; without the opt-in every request is byte-identical to today (pinned: H02/H03/H06/H08/H10 and the W4-13 ledger in CI order - `ADMIN_API_KEY` alone is never enough, because test modules set it at import).
- `run_validation_matrix` also passes `allow_redirects=False` when the admin header is attached: requests 2.34.2 strips only `Authorization` on a cross-host redirect and was measured forwarding `X-Admin-Key` to the redirect target. The httpx-based scripts do not follow redirects.
- **The ONE non-opt-in harness change (C7):** `scripts/bundle_d_prod_smoke.py` probe 12 (`GET /text/compare`, cached) now sends `Authorization: Bearer <derived_token>` whenever the smoke has a token, falling back to the opt-in admin header, else none. Side effects even with U13 OFF: probe 12 becomes a signed-in compare that consumes one credit and writes a comparisons/history row, cohort tracking and a user-keyed `search_logs` row on every run. Normally the token is the throwaway account the smoke's own login probe created; **when the operator passes `--auth-token`, that token is used instead, so the credit and the history row land in the OPERATOR's own account** (the same pattern the smoke's other authed probes already use).
- Operators run harnesses as `railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 python <script>` so the key is injected, never typed or printed.

### Activation runbook (Ahmed; agents never flip flags) - section 9 as corrected by C9 + UR5
1. Merge (all five required checks green). Railway auto-deploys `web`; confirm `/health` 200 and the deployment's commit is the merge.
2. Flag still OFF: anonymous `GET /api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24` behaves exactly as before (today the 400 parse-failure copy while OpenAI is unfunded).
2b. **Rotate `ADMIN_API_KEY`** to a fresh value of at least 32 random bytes (owed since the 2026-09-07 exposure; with U13 ON it is the only account-free way to buy paid compares, and guesses are not rate-limited on these routes, L6). `railway run -s web` picks up the new value.
3. Smoke the credentials BEFORE the flip (no LLM spend while unfunded): the demo/test account's bearer on `GET /text/compare` -> NOT 401; `railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 python docs/investigations/2026-09-29-session-69-state/verify_after_credits.py --pairs "iPhone 15 vs Galaxy S24"` -> compare http != 401/403 (the run itself fails while unfunded; only the status matters).
4. **Set THREE flags in ONE window on `web`:** `ENABLE_COMPARE_AUTH_REQUIRED=true`, `ENABLE_PAID_ROUTE_METERING=true`, `ENABLE_CAMERA_FAILURE_ENVELOPE=true` (C1/UR5: with U13 alone any self-registered account gets UNMETERED paid `/url/compare` and `/image/identify`; the camera-envelope flag must flip with metering). This unit changes no code of the two existing flags.
5. Re-probe anonymously (free): `GET /text/compare`, `GET /text/compare/stream` (a JSON 401, not a stream), `POST /text/quick`, `GET /text/prices/x`, `GET /url/extract?url=https://example.com`, `GET /url/compare?url1=...&url2=...`, `POST /image/identify` (any small multipart) -> each 401 `AUTH_REQUIRED`. `GET /url/detect`, `GET /url/retailers`, `/health`, `/legal/privacy` -> unchanged. A signed-in, exhausted free account now gets 429 `USAGE_LIMIT` on `/url/compare` and `/image/identify`. Repeat step 3 -> still not 401.
6. Watch 24 h: Railway HTTP 401s on the ten routes (expect the scanners), the `[paid-auth]` reason histogram, and any mobile-UA 401 not followed by `/auth/refresh` + a successful retry. Caveat: if `ENABLE_STRICT_OPTIONAL_AUTH` is ever ON, a rejected bearer on U1-U6 is refused by `get_optional_user` before the guard and logs NO `[paid-auth]` line, so the histogram undercounts (strict is dark today).
7. ONLY THEN fund OpenAI (prepaid, low project budget, no auto-recharge). Then run step 3's admin command with the default pairs to verify end to end.
8. Rollback: unset `ENABLE_COMPARE_AUTH_REQUIRED` (per call, immediate). Rolling back reopens anonymous paid compares - only with OpenAI spend capped.
- Also for Ahmed: check Supabase Auth "Confirm email" (NOT measured); if it is off, an account costs one POST per 10 compares a month.

### Stated limits
- L1 Account farming: `/auth/register` is public; with the three flags ON a farmed account is bounded by the free tier (3 lifetime-free, 3/day, 10/month across every metered route). UR14: the remaining exposure after activation is those free-tier credits per self-registered account; the prepaid, low-cap OpenAI budget stays the backstop. The smoke's throwaway accounts use a password that is public in the repo; how many exist in production is not measured.
- L2 / UR13 The limiter is not a spend control: Railway shows `FORWARDED_ALLOW_IPS`, `RATELIMIT_ENABLED`, `ENABLE_PROXY_AWARE_RATELIMIT`, `WEB_CONCURRENCY` absent and one replica, so the remaining cause of zero 429s is (a) the TCP peer address varying across requests (not measured directly). The CLAUDE.md sentence that calls the proxy-IP key "one deployment-wide bucket" is wrong. Anonymous refusals never reach the limiter with the flag ON. Not fixed here.
- L3 Public repo history keeps the URL, routes, harness defaults and smoke password readable.
- L4 A Supabase-auth outage becomes a compare outage for signed-in users (no forced logout; `/auth/refresh` 503 path).
- L5 JSON decode (422 `json_invalid`) and multipart parsing (full `/image/identify` uploads) happen before the guard on fastapi 0.141.1 - free, but an anonymous upload still costs parse CPU/memory.
- L6 Admin-key guessing is not rate-limited on these routes (a dependency runs before the slowapi wrapper) - same class as the existing admin routes.
- L7 Garbage-bearer floods still cost one Redis GET + one Supabase `/user` call each on U1-U6 (pre-existing).
- L8 Camera degrade: the camera raw fetch has no 401 refresh, so an expired token gives the generic error instead of today's anonymous success (recoverable after another axios call refreshes).
- L9 Harness operators need `HARNESS_SEND_ADMIN_KEY=1` + `ADMIN_API_KEY`; a future `cron_eval_nightly` service needs its own credential (C8); `tests/integration/bundle-e-smoke.sh` probe 4 needs `AUTH_ARG`.
- L10 Pre-existing raw query/URL logging at INFO (`text_routes`, `url_routes`) is untouched; with the flag ON anonymous callers no longer reach it.
- L11 `ENABLE_STRICT_OPTIONAL_AUTH` stays dark; its other optional routes keep the silent downgrade.
- Pre-existing, outside this unit: `admin_routes.verify_admin_key` treats a whitespace-only `ADMIN_API_KEY` as configured (measured under TestClient; h11 would strip a whitespace header value).

### Follow-ups (to file)
1. U13c (client): the camera `/image/identify` 401 -> refresh -> retry once. Does not gate the flip; must merge before the U10 production store build.
2. Per-user limiter key on authenticated routes (L2/UR13), plus the CLAUDE.md "one deployment-wide bucket" correction.
3. The live/integration files that will 401 with the flag ON (C10): `tests/test_integration.py`, `test_two_input_shape.py` (TestLiveRailwaySmoke), `test_d2_spec_parity_per_category.py`, `test_spec_parity.py`, `test_unified_search.py` (TestCostTrackingLive), `test_cohort_personalization_load.py`, `test_bundle_c_integration.py`, `test_bundle_e_integration.py`, `test_lane2_integration.py`, `test_scoring_v2_all_nine_categories.py`, `tests/perf/test_latency_bench.py`, `tests/post_deploy/bundle_c_acceptance.md` - they need the opt-in admin header or a bearer.
4. Raw query/URL logging at INFO (L10).
5. Multipart parsing before the guard (L5).
6. The smoke's production accounts and their public password (L1): delete or rotate.
7. DONE in this PR (ruling UF2): `tests/test_s71_u13_pins.py` pins the exact-match admin key (near-miss, padded and case variants, the identity with `admin_routes.verify_admin_key`, an unconfigured key never admitting an empty header), flag OFF never consulting the admin header, the `ADMIN_REQUIRED` / Basic-header reasons at DEBUG on all loggers, the `?` label fallback and the opted-in `allow_redirects=False`; 44 nodes, ten mutants killed.
8. `admin_routes.verify_admin_key`: treat a whitespace-only configured key as unset (its own unit; R9 file here).

### Gates (bounded runner, one pytest at a time)
- G1 py_compile 10 files OK; ruff 0.16.5 `E9,F63,F7,F82` all passed. G7: 234 added lines, 0 non-ASCII; 0 `sk-`-shaped strings; fixture unchanged; line-level diffs on CRLF working copies.
- G2 the two new files: 159 passed, netguard 0 - `[pyt] tag=u13-fix-g2 elapsed=14s status=OK rc=0`.
- G3 pin set (25 files, CI order, incl. every module-level `ADMIN_API_KEY` setter and the C6 files): 879 passed - `[pyt] tag=u13-fix-g3 elapsed=59s status=OK rc=0`.
- G5 `tests/test_security_regression.py` alone: 104 passed - `[pyt] tag=u13-fix-secreg elapsed=9s status=OK rc=0`.
- G4 module-reference comm gate (131 files at base `eb86075e`, 133 at head, chunks of <= 25): FAILED+ERROR base 5 == head 5 (all five are known rows of `tests/.pre_impl_failures.txt`), `comm -13` empty, netguard node sets equal (135/135).
- G8 mutation spot-checks X1-X10 (GREEN and the regression adversary, each restored and sha-verified): all killed.
- Two adversarial reviews (security, regression): SOUND, no serious defect; their minors are applied (redirect hardening, PR text) or listed above.

### Owed by the orchestrator at merge (R14, UG6)
CLAUDE.md: the flag row (effect, activation order = the three flags in one window after the `ADMIN_API_KEY` rotation, rollback = unset); the curl example gains `-H "X-Admin-Key: ..."` guidance (never a literal key); the Serper liveness note: with `ENABLE_COMPARE_AUTH_REQUIRED` ON an unauthenticated `/text/prices` probe returns 401, which is NOT a dead key.

## Orchestrator review (session 71)
- Process: Opus spec, Opus adversarial spec review (C1-C11), orchestrator rulings UR1-UR15, Opus RED gated PASS (UG1-UG6), Opus GREEN, two Opus adversaries (security: 46 + 6 bypass probes, the paid-route inventory rebuilt from the import graph; regression: the module-reference comm gate re-run with a different chunk layout, a 1,760-record flag-OFF matrix identical base vs head), both SOUND with 0 defects; the fix round hardened `run_validation_matrix` (UF1); rulings UF1-UF6; then a pins workflow (one Opus author, one Opus adversary, fix) added the supplementary pin file, every pin proven by a mutant.
- The orchestrator re-hashed the thirteen files, read the full diff of the three route files and the five harness scripts, fast-forwarded the branch to main `0a7446b4` and re-ran the 26-file CI-order set there (923 passed); it then mutated the admin check to a case-insensitive prefix match itself and watched seven pin nodes fail before restoring the file (sha equal).
- Nothing is flipped by merging. The activation runbook above is the owner's; the orchestrator hands it over separately with the follow-up issue numbers.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
