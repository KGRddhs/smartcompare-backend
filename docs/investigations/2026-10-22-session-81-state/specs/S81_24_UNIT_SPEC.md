# S81-24 UNIT SPEC: AUTH-THROTTLE-V2 phase 1 + MS4 HOP-PROBE echo line

- Unit: S81-24 AUTH-THROTTLE-V2 phase 1 (PLAN_S81 :150) + the MS4 HOP-PROBE dark echo line (PLAN_S81 :105 / :150). Class FOCUS (LC-1: auth routes, Redis Lua, the 429 contract build 3 renders, a privacy TTL statement); R-S24-18 stands: the measured footprint holds NO migration and NO client file, so the spec does not stop.
- Flags: `ENABLE_AUTH_THROTTLE_V2` (NEW, default OFF, read per call) and `ENABLE_HOP_PROBE_LOG` (NEW, default OFF, read per call). New names, so unset in production by construction (Railway not read). Knobs: section 2.2. New credential-bearing name: `AUTH_THROTTLE_PEPPER` (joins `tests/_env_safety.CREDENTIALS_UNSET`).
- Worktree: `C:/Users/SynAckITPC/Documents/AI/sc-s81-s24`, detached at base `daf86d32d222a885c42dc537e83c25483527a83b` (`git rev-parse HEAD` measured equal); `git status --short` EMPTY before and after every probe of this spec (the spec file lives under the gitignored `.qa-s80/`).
- Branch for RED / GREEN: `feature/s81-s24-auth-throttle-v2` (the brief's name; the RED re-points to the then-main after the G8 FOLLOWUPS merge).
- Measurement location: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/8723f7aa-4b51-496c-9ed1-d602ed517c8b/scratchpad/s81-24/` (base_core.log, probe_bodies.py + probe_bodies.json, scripts_frozen.py, comm_set_daf86d32.txt).
- Evidence pointers: the unit brief `specs/S81_24_BRIEF.md` (R-S24-1..R-S24-18, binding); PLAN_S81 :105 (research finding) and :150 (unit text); PLAN_S80 section 0 (contract freeze, items 2-5) and `runs/research/contract_freeze.json` (RULE 4: RATE_LIMITED is a code build 3 maps); R-A1 / R-A13 (PLAN_S80 section 1); the session-81 ledger (newest line on proxy-aware: ENABLE_PROXY_AWARE_RATELIMIT OFF on web, the 2026-11-06 20:35 names-only read).
- Sister units and contracts: S81-05 (the HMAC idiom `app/utils/request_context.py:298-312`, `CREDENTIALS_UNSET`); S81-04 (the Upstash EVAL two-shape `_eval` `app/services/llm_spend_breaker.py:970-977`, the timeout knob + dedicated pool `:126-127`, `:833-866`); S81-09 (the Lua-in-a-constant form `app/services/usage_service.py:300-353`, the Asia/Riyadh fixed +03:00 day `:166`); S81-12 HELD (the dormant throttle text; no edit here); W1-9 / W1-9b (the 429 contract `app/middleware/error_handler.py:96-128`, `:146-160`, `:163-249`, `:309-334`; the lockout `app/services/auth_service.py:1294-1373`); M13-01 / M13-02 (the limiter `app/middleware/rate_limiter.py:24-70`); S81-24b (phase 2, after the probe: per-IP / per-device keys, the m13_02 leftmost pin, #299, the GoTrue secret-key client, SMTP); S81-24c (the test-only retirement of the string-presence tests). Known union with the G8 lane: CLAUDE.md only (the block goes after the newest block at the final round).
- Personal-data rule: no personal value anywhere. Every email in tests is synthetic and built at run time (`"user-a" + "@example.com"`); every IP is a documentation (TEST-NET / RFC 1918 / CGNAT) or a public-resolver address; the pepper is built at run time (`"s24-pepper-" + "q" * 8`); no user id other than a run-time `uuid.UUID(int=n)`.

## 0. What the unit does

Adds Upstash-backed, per-email and per-account throttles in front of six auth routes, dark behind `ENABLE_AUTH_THROTTLE_V2`, and a dark header-echo log line on two cheap GET paths behind `ENABLE_HOP_PROBE_LOG`. With both flags OFF every auth response, header set, log line and Redis command sequence is byte-identical to base.

ON, each gated route makes ONE Lua EVAL decision through a NEW leaf `app/services/auth_throttle.py` BEFORE any GoTrue / Supabase call of its body and before the W1-9b lockout calls:
- `POST /api/v1/auth/login`: exponential backoff per email: after the n-th consecutive credential failure the next attempt waits min(2^(n-1), cap) seconds (1, 2, 4, 8 ... cap); a success clears it; only a wrong-password / unknown-user result counts (never an unconfirmed email, a transient provider error or a 5xx).
- `POST /api/v1/auth/register`: one attempt per email per interval (60 s).
- `POST /api/v1/auth/password-reset` and `POST /api/v1/auth/resend-verification`: one per email per interval (60 s) and at most 5 per email per Asia/Riyadh day, each endpoint on its own keys; the login backoff never blocks the reset.
- `PUT /api/v1/auth/password` and `PUT /api/v1/auth/email`: at most 5 attempts per authenticated account (the user id) per 600 s window.

A throttled request gets the SAME unified 429 envelope the slowapi handler emits (`code` RATE_LIMITED, `Retry-After` header = `retry_after_seconds` field), which build 3 already renders. Keys are `auth_throttle:<endpoint>:<kind>:<digest>` with digest = HMAC-SHA256(`AUTH_THROTTLE_PEPPER`, the identifier)[:32]; every key expires 6 h (the privacy section 8 figure) after its last write, the per-day counter 24 h after its first increment. Every Redis error, timeout, unset client, unset pepper or malformed reply fails OPEN with one constant WARNING; the per-IP slowapi floor and the W1-9b lockout are untouched in both states.

MS4: under `ENABLE_HOP_PROBE_LOG`, ONE INFO line per `GET /health` and `GET /api/v1/app/version` request, emitted from `RequestIDMiddleware.dispatch`, carrying only counts and booleans about X-Forwarded-For / X-Real-IP / Forwarded / CF-Connecting-IP versus the TCP peer, never an IP, a hash or a header value. The spoof probe itself is an ops step after the deploy (section 8).

Closes nothing directly: it drafts the session-81 DEFECT_LEDGER row S81-24 (names only, section 8.3); #299 (the request.state limiter key) stays open for S81-24b.

## 1. Base state (MEASURED at daf86d32)

### 1.1 The auth route surface (`app/api/auth_routes.py`, 1,763 lines, CRLF working copy, LF index)

The AST of the file (measured with `ast.parse`, module-level functions carrying a `@router.<method>` decorator) gives FIFTEEN routes with exactly one `@limiter.limit("<rate>")` decorator each (no keyword arguments on any), placed directly below the router decorator, plus the expired-logout budget literal. The brief's "sixteen" = these fifteen + the budget (recorded, not a defect).

| # | function | method path | limiter line | rate | V2 gate |
|---|---|---|---|---|---|
| 1 | register | POST /register | :688 | 3/minute | YES per email (interval) |
| 2 | login | POST /login | :800 | 5/minute | YES per email (backoff) |
| 3 | refresh | POST /refresh | :864 | 10/minute | no |
| 4 | password_reset | POST /password-reset | :1127 | 3/minute | YES per email (interval + day) |
| 5 | password_recovery | POST /password-recovery | :1142 | 5/minute | no (completing a reset is never blocked) |
| 6 | update_email | PUT /email | :1208 | 5/minute | YES per account |
| 7 | change_password | PUT /password | :1242 | 5/minute | YES per account |
| 8 | social_login | POST /social-login | :1272 | 10/minute | no |
| 9 | delete_account | DELETE /account | :1301 | 1/minute | no |
| 10 | resend_verification | POST /resend-verification | :1320 | 3/minute | YES per email (interval + day) |
| 11 | update_push_token | PUT /push-token | :1430 | 10/minute | no |
| 12 | update_reengagement_subs | PUT /reengagement-subs | :1498 | 10/minute | no |
| 13 | update_preference_toggles | PUT /preference-toggles | :1572 | 10/minute | no |
| 14 | save_demographics | PUT /demographics | :1655 | 5/minute | no |
| 15 | save_attribution | POST /attribution | :1744 | 30/minute | no |

Undecorated routes (router decorator, no limiter): get_me GET /me :1089, verify_auth GET /verify :1162, update_profile PUT /profile :1175, get_preferences GET /preferences :1336, save_preferences PUT /preferences :1383, get_cohort_profile GET /cohort-profile :1721. `logout` (:1049) is registered through a custom route class (:1040-1046 return `logout_route_handler`), not a `@router` decorator. Budget: `_EXPIRED_LOGOUT_BUDGET = parse_rate_limit("10/minute")` at :967, used by `_expired_logout_within_budget` :971-981 (`limiter.limiter.hit`, fails CLOSED on a storage error). Imports: `limiter, audit_client_ip, _rate_limit_key` from rate_limiter at :18; the auth_service names incl. `check_account_locked, track_failed_login, clear_failed_logins` at :37-59.

Request models: `RegisterRequest.email: EmailStr` :95-96, `LoginRequest.email: EmailStr` :124-125, `PasswordResetRequest.email: EmailStr` :143-144 (also the resend body), `UpdateEmailRequest.new_email` :162-163, `ChangePasswordRequest` :167.

### 1.2 The gated route bodies and their GoTrue error branches

- `register` :689-796: consent decided first (:706-708, `consent_from_fields` then `consent_rejection()` when REQUIRED; no await), then `await register_user(...)` :710 (the first await), 400 with `result["error"]` on failure :712-716. `auth_service.register_user` :389-438: `sign_up`; `user` -> users insert -> success; no user -> "Registration failed"; exception -> `_categorize_auth_error(e, "register")` :276-319: "user already registered" -> "An account with this email already exists"; transient terms (:213-216) -> `UPSTREAM_UNAVAILABLE` result; else "Something went wrong. Please try again later." MEASURED wire body for an existing email (route-level mock): `400 {"success":false,"error":"An account with this email already exists","code":"BAD_REQUEST","request_id":"<rid>"}`. Register is therefore NOT enumeration-safe at base (Q7); V2 changes neither body.
- `login` :801-852: `await check_account_locked(body.email)` :808 FIRST (the first await); locked -> audit `brute_force_lockout` + 429 ACCOUNT_LOCKED with `retry_after` :809-826; `await login_user(...)` :828; failure -> `await track_failed_login(body.email)` :831, audit `login_failed`, 401 `result.get("error")` :842-845; success -> `await clear_failed_logins(body.email)` :848, audit `login_success`. `auth_service.login_user` :441-489: success; no user/session -> "Login failed"; exception -> `_categorize_auth_error(e, "login")`: "invalid login credentials" (GoTrue's text for BOTH a wrong password and an unknown user) -> "Invalid email or password"; "email not confirmed" -> "Please verify your email before logging in"; transient -> `{"error": "Connection failed. Please try again.", "code": "UPSTREAM_UNAVAILABLE"}` (:219-224); else "Something went wrong. Please try again later.". The V2 backoff counts ONLY `result.get("error") == "Invalid email or password"` (the wrong-password / unknown-user class, R-S24-3); a GoTrue 429 / 5xx lands in the generic or transient branch and never counts.
- `password_reset` :1128-1138: `await request_password_reset(body.email)` :1132, result ignored, always `200 {"success":true,"message":"If an account with that email exists, a reset link has been sent."}` (measured identical for a success and a failure mock). `request_password_reset` :1159-1180 catches every exception into `_categorize_auth_error(e, "password_reset")`.
- `resend_verification` :1321-1330: `await resend_verification_email(body.email)` inside try; success and exception both `200 {"success":true,"message":"Verification email sent if account exists"}` (measured); the except arm logs `logger.error(f"Resend verification error: {e}")` (base line, untouched).
- `update_email` :1209-1238: `Depends(get_current_user)` (a GoTrue verify through `verify_token`, before the body; unavoidable, Q11); `email = current_user.get("email") or ""`; `await check_account_locked(email)` :1222 (the first await of the body); `_account_locked_response` :1185-1204; `await update_user_email(...)` :1226; `"password" in error` -> `track_failed_login`; 400 / 500; success -> `clear_failed_logins`. Service :887-902: "invalid login credentials" -> "Current password is incorrect", else `_categorize_auth_error(e, "update_email")`.
- `change_password` :1243-1268: same shape; `check_account_locked(email)` :1253 first await; `change_user_password` :1257; error text containing password / incorrect / credentials -> `track_failed_login`; 400; success -> `clear_failed_logins`. Service :869-884.

### 1.3 The W1-9b lockout (`app/services/auth_service.py:1290-1373`, untouched in both states)

`LOCKOUT_THRESHOLD = 5` :47, `LOCKOUT_WINDOW_SECONDS = 900` :48; `redis_client` bound at import from cache_service :28. `_login_attempt_key(email)` :1294-1297 = `failed_login:<sha256(email.lower())[:16]>` (UNSALTED). `check_account_locked` :1300-1330: `get(key)`; locked -> `ttl(key)`, a non-positive TTL re-arms with `expire(key, 900)`; fails OPEN `{"locked": False, "retry_after": 0}`. `track_failed_login` :1333-1363: `set(key, 0, nx=True, ex=900)`, `incr(key)`, `expire(key, 900, nx=True)` in its own try; fails OPEN. `clear_failed_logins` :1366-1373: `delete(key)`. Hence the base Redis command sequence (recorder, key absent, unlocked): login failure = `get, set(nx, ex=900), incr, expire(900, nx=True)`; login success = `get, delete`; change_password / update_email the same around their service call; register / password_reset / resend_verification = NO Redis command (slowapi storage is in-memory, measured: no `storage_uri`).

### 1.4 The limiter and the 429 contract

- `app/middleware/rate_limiter.py` (185 lines): `_proxy_aware_enabled` :24-30 (`ENABLE_PROXY_AWARE_RATELIMIT`, OFF in production per the ledger); `_leftmost_xff_ip` :33-48; `_rate_limit_key` :51-58 (TCP peer unless proxy-aware); `audit_client_ip` :61-69. Untouched.
- `app/middleware/error_handler.py` (368 lines): `STATUS_CODE_MAP[429] = "RATE_LIMITED"` :32; `_build_error_response` :101-128 (content order success, error, code, request_id, then `retry_after_seconds` + `Retry-After` when given); `_detail_retry_after` :146-160 (a positive non-bool int `retry_after` only); `http_exception_handler` :163-249 (a structured detail's `error` and `code` lifted; a 429 with a usable `retry_after` gets `retry_after_seconds` + `Retry-After`; the S81-09 / S81-10 / S81-20 / B4 blocks fire only for their own codes); `_retry_after_seconds` :270-306 (slowapi's `int(1 + reset_time - now)`, bounded at window + 1); `rate_limit_handler` :309-334 (message "Rate limit exceeded. Please try again later."; never a 500). Untouched.
- MEASURED wire bytes (probe_bodies.json; route-level mocks; `<rid>` = the request id): the slowapi 429 (4th `POST /password-reset` in a minute) = `{"success":false,"error":"Rate limit exceeded. Please try again later.","code":"RATE_LIMITED","request_id":"<rid>","retry_after_seconds":60}` with header names `content-length, content-security-policy, content-type, permissions-policy, referrer-policy, retry-after, strict-transport-security, x-content-type-options, x-frame-options, x-request-id, x-xss-protection`; the ACCOUNT_LOCKED 429 = `{"success":false,"error":"Account temporarily locked due to too many failed attempts","code":"ACCOUNT_LOCKED","request_id":"<rid>","retry_after_seconds":120}` with the same eleven header names. An `HTTPException(429, detail={"error": "Rate limit exceeded. Please try again later.", "code": "RATE_LIMITED", "retry_after": n})` therefore yields the slowapi 429's exact key order, types, header-name set and `Retry-After: n` through `http_exception_handler` with NO error_handler edit. Login 401 = `{"success":false,"error":"Invalid email or password","code":"AUTH_REQUIRED","request_id":"<rid>"}` (ten header names, no retry-after).
- Build 3 (read-only, `git show 683f56c0:SmartCompareApp/src/services/authErrorCopy.ts:13-15, :46-49`): login / register map `RATE_LIMITED` (and any 429) to `common.errors.rateLimited`; contract_freeze records the settings surfaces mapping RATE_LIMITED / ACCOUNT_LOCKED else the caller fallback. No client change is needed (Q6 answered by measurement).

### 1.5 The Upstash client and the EVAL forms

- `app/services/cache_service.py`: `redis_client = _build_redis_client()` :166 (upstash_redis REST client, or the `redis://` fallback, or None; built at import; the W0-3 bounded transport under its own flag :76-126). Hermetic tests: `UPSTASH_REDIS_URL` / `_TOKEN` are in CREDENTIALS_UNSET, so `redis_client` is None unless a test patches it.
- `llm_spend_breaker._client()` :275-281 reads `_cache_service.redis_client` per call (never a by-name import: the #183 reload hazard). `_eval` :970-977: upstash-redis 1.7.0 `eval(script, keys=, args=)` versus redis-py 8.1.0 `eval(script, numkeys, *keys_and_args)`, chosen by `type(client).__module__.split(".")[0] == "upstash_redis"`. MEASURED signatures on the pinned venv: `Redis.eval(self, script, keys=None, args=None)` (upstash_redis) and `Redis.eval(self, script, numkeys, *keys_and_args)` (redis 8.1.0). Timeout: `LLM_SPEND_REDIS_TIMEOUT_SECONDS` default 0.5 :126-127 (the measured TLS GET 163-203 ms); `_run_bounded_async` :860-866 = `asyncio.wait_for(asyncio.wrap_future(pool.submit(...)), timeout)` on a dedicated lazily built 4-thread pool :833-845.
- `usage_service` S81-09: the scripts are module constants (:300-320), run through `llm_spend_breaker._eval` imported inside the arm (:338-353) with no timeout of its own; `RIYADH_UTC_OFFSET_HOURS = 3` :166 (fixed +03:00, no DST, owner decision 5); `llm_spend_breaker.riyadh_day` :337-351 is the day helper. No Lua runtime on the venv (pip list: no lupa, no fakeredis): the S81-09 RED models each script in Python keyed on the exact script text (`tests/test_s81_s09_device_quota.py:283-285`, FakeRedis :290-385). This unit follows that form.

### 1.6 The HMAC idiom and the env-safety list

- `app/utils/request_context.py:298-312` `device_key(fp)`: pepper read per call, unset / blank / non-UTF-8-encodable -> None + ONE constant WARNING per process (`_warn_pepper_once` :279-288, latch + lock, test seam `_reset_pepper_warning` :291-295); `hmac.new(pepper.strip().encode("utf-8"), msg, hashlib.sha256).hexdigest()`. MEASURED: `hmac.new(b"p", b"user-a@example.com", sha256).hexdigest()[:32]` = `65ca3d58efea5842e3360dc1d24aea2a` (a fixture sanity value).
- `tests/_env_safety.py:110-143` `CREDENTIALS_UNSET` (CRLF working copy): `DEVICE_KEY_PEPPER` :136 with its comment :135; readers: tests/test_conftest_env_safety.py (:292 superset of a contract list; :361-381 no overlap with placeholders), test_s81_s05_request_context.py :1283, test_s81_s04_spend_breaker.py :1943-1948 (no LLM_SPEND name), test_s81_s06_anthropic_router.py :2435-2438, test_s79_b3b_apple_revoke.py :1473-1477; adding one name breaks none of them.

### 1.7 The request-id middleware and the middleware order

- `app/middleware/request_id.py` (15 lines, ASCII, CRLF): `RequestIDMiddleware(BaseHTTPMiddleware).dispatch` :10-15: `request.headers.get("X-Request-ID", str(uuid.uuid4()))`, `request.state.request_id`, `await call_next`, response header. No logger, no os import.
- `app/main.py`: registration order :123 RequestContext, :124 CORS, :159-160 SlowAPIASGI (flag), :176 ErrorHandler, :179 SecurityHeaders, :182 RequestID (outermost). Pinned by tests/test_s81_s05_request_context.py :103 / :110, tests/test_retro_w1_9.py :274, tests/test_retro_w1_1.py :211 (the middleware class list). A NEW middleware class would redden all three, so the echo line lives INSIDE `RequestIDMiddleware.dispatch` (measured reason for the seat, R-S24-11 option one; Q5).
- Paths: `@app.get("/health")` :626 `health_check`; the version route is `GET /api/v1/app/version` (`version_routes.py:9` prefix `/api/v1/app`, `:49` `/version`); the brief's "/app/version" is that path. Body keys (probe): /health `adapter_executor, loop_lag_max_60s_ms, loop_lag_max_ms, loop_lag_ms, message, status`; /api/v1/app/version `force_update, latest_version, min_version, update_url_android, update_url_ios`.
- Starlette `TestClient(app, client=("<host>", <port>))` sets the TCP peer (measured signature on starlette 1.6.0). `ipaddress.ip_address("203.0.113.7").is_global` = False, `"100.64.0.1"` False, `"8.8.8.8"` True (measured): a TEST-NET forged XFF reads `xff_leftmost_public=false`.

### 1.8 Libraries (pinned venv `.venv-qaren`, measured with pip list)

fastapi 0.141.1, starlette 1.6.0, slowapi 0.1.10, limits 5.8.0, upstash-redis 1.7.0, redis 8.1.0, httpx 0.28.1, pytest 9.1.1, pytest-asyncio 1.4.0, pytest-timeout 2.4.0. No new dependency.

### 1.9 Guards the new code must not trip

- G1 `tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app` (:1371-1400) walks app/ and scripts/: any file containing `request_context`, or (case-insensitive) `device_key_pepper`, `x-ai-consent-version`, `x-compare-request-id`, `header_state` must be allowlisted. Neither `auth_throttle.py` nor the edited `request_id.py` may contain those strings (no "never reuse DEVICE_KEY_PEPPER" comment in app/).
- G2 The middleware-order pins (1.7): no new middleware class, no registration change in main.py.
- G3 The source-window string tests (4.2): every `@limiter.limit(...)` line and its position relative to `async def` stays byte-identical; V2 lines go inside the bodies only. `tests/test_password_reset_deep_link.py:322-329` reads the three lines above `async def password_recovery(` (untouched route); `tests/test_attribution_endpoint.py:98-105` a 250-char window around `"/attribution"` (untouched route); `tests/test_security_regression.py:425-439` substring presence.
- G4 gitleaks keyword rule: no constant named with access / auth / api / credential / creds / key / password / secret / token beside a 64-hex literal (the RED's sha pins: `FROZEN_SCRIPT_SHA256`, never `..._KEY_...`; note `AUTH_THROTTLE_PEPPER` is an env NAME string, never assigned a hex literal).
- G5 The credential-shape hook: the pepper and any sentinel built at run time by concatenation.
- G6 `tests/test_429_contract.py` drives `POST /password-reset` 4 times with ONE email (:56, :71-83): green in both states because the hermetic `redis_client` is None (V2 fails open); a V2 row that installs a fake client must never leak it to other tests (monkeypatch only).
- G7 Line endings: the four edited files are CRLF in the working copy (`git ls-files --eol`: i/lf w/crlf for auth_routes.py, request_id.py, tests/_env_safety.py, CLAUDE.md); the Edit tool preserves them; a whole-file diff is a defect. NEW files (auth_throttle.py, the RED and gate-rows files) are pure ASCII LF.

### 1.10 Base pass state (bounded runner, base daf86d32)

One run over the files this unit edits or pins (17 files):
`tests/test_429_contract.py tests/test_retro_w1_9_429.py tests/test_brute_force.py tests/test_retro_r_auth_fixer_pins.py tests/test_security_regression.py tests/test_password_reset_deep_link.py tests/test_attribution_endpoint.py tests/test_auth_demographics.py tests/test_m13_01_slowapi_middleware.py tests/test_m13_02_proxy_aware_ratelimit.py tests/test_security_middleware.py tests/test_observability.py tests/test_retro_w1_9.py tests/test_s81_s05_request_context.py tests/test_conftest_env_safety.py tests/test_limiter_endpoint_key.py tests/test_auth_interceptor.py`

```
[hermeticity] sentinel checked 668 test(s)
[netguard] blocked 18 attempt(s) from 11 node(s)
==== 2 failed, 665 passed, 1 skipped, 2 deselected, 321 warnings in 44.69s ====
[pyt] tag=s24-spec-base-core start=2026-11-07 07:36:28 end=2026-11-07 07:37:15 elapsed=47s bound=1200s status=FAIL rc=1
```

The two FAILED nodes are the baselined red-by-choice pair `tests/test_auth_interceptor.py::test_sign_in_with_social_exception` and `::test_social_login_user_insert_fails_gracefully` (`tests/.pre_impl_failures.txt:88-89`; the [B4-BE-DIAG] social_login branch, auth_service.py:313-317), also in the stored 05ccaed2 record. Everything else is green at base. The netguard blocks are the `neutralized.supabase.invalid` sentinel (a fail-fast placeholder host), not real network.

## 2. Contract

### 2.1 Flags (house idiom, read per call)

- `auth_throttle.auth_throttle_v2_enabled()` = `os.getenv("ENABLE_AUTH_THROTTLE_V2", "false").strip().lower() in ("true", "1", "yes", "on")`. At every gated route the FIRST statement of the new predicate is this call: the route block is `if auth_throttle.auth_throttle_v2_enabled():` followed by the awaited V2 call. `gate()` and the two record functions do NOT re-read the flag (a single gate per site, so a "not gated" mutant is killable by the OFF rows).
- `request_id.hop_probe_log_enabled()` = the same idiom over `ENABLE_HOP_PROBE_LOG`, the first statement of the echo predicate in `dispatch`.

### 2.2 Knobs (read per call, parsed defensively: strip, `int(raw, 10)` for the int knobs, `float(raw)` for the timeout; unset / blank / garbage / non-integer text / inf / nan / out of range -> the DEFAULT, never a clamp to the bound)

| name | default | valid range | used by |
|---|---|---|---|
| AUTH_THROTTLE_LOGIN_CAP_SECONDS | 60 | 8..3600 | the login backoff ceiling |
| AUTH_THROTTLE_REGISTER_INTERVAL_SECONDS | 60 | 10..3600 | register |
| AUTH_THROTTLE_RESET_INTERVAL_SECONDS | 60 | 10..3600 | password_reset, resend_verification |
| AUTH_THROTTLE_RESET_PER_DAY | 5 | 1..100 | password_reset, resend_verification (each its own counter) |
| AUTH_THROTTLE_ACCOUNT_PER_WINDOW | 5 | 1..100 | change_password, update_email |
| AUTH_THROTTLE_ACCOUNT_WINDOW_SECONDS | 600 | 60..86400 | change_password, update_email |
| AUTH_THROTTLE_TTL_SECONDS | 21600 | 60..86400 | every backoff / interval / account key (6 h = privacy section 8) |
| AUTH_THROTTLE_REDIS_TIMEOUT_SECONDS | 0.5 | 0.05..5.0 (finite float) | `asyncio.wait_for` per EVAL |

The effective TTL of a key = max(TTL knob, the window the key enforces in seconds) so a key never expires before its own window (only reachable when an operator sets a TTL below a window). Constants (no knob): `DAY_KEY_TTL_SECONDS = 86400`; `RIYADH_UTC_OFFSET_HOURS = 3`; `POOL_WORKERS = 4`, thread prefix `auth-throttle`; `DIGEST_HEX_CHARS = 32`; `THROTTLED_MESSAGE = "Rate limit exceeded. Please try again later."` (pinned equal to error_handler's rate_limit_handler literal). No knob is added beyond R-S24-1.

### 2.3 Identifiers, keys and the pepper

- `PEPPER_ENV = "AUTH_THROTTLE_PEPPER"`, read per call. `digest(ident) -> Optional[str]`: `ident` a str; pepper unset / blank / not UTF-8-encodable -> None and ONE WARNING per process `[AUTH_THROTTLE] pepper unset` (a latch under a lock; test seam `_reset_pepper_warning()`); else `hmac.new(pepper.strip().encode("utf-8"), ident.encode("utf-8"), hashlib.sha256).hexdigest()[:32]`.
- `email_ident(raw)`: a str -> `raw.strip().lower()`; empty or not a str -> None. `account_ident(raw)`: a non-empty str (the user id, `str(...)` of a UUID str) -> `raw.strip()`; else None. A None ident = allow, no Redis call, no log line.
- `throttle_key(endpoint, kind, digest) = "auth_throttle:%s:%s:%s" % (endpoint, kind, digest)`. Endpoints (`ENDPOINTS`, a tuple): `login`, `register`, `password_reset`, `resend_verification`, `change_password`, `update_email`. Kinds: `backoff` (login), `interval` (register, password_reset, resend_verification), `day<YYYYMMDD>` (the Asia/Riyadh day, password_reset and resend_verification), `account` (change_password, update_email). Example shapes: `auth_throttle:login:backoff:<32 hex>`, `auth_throttle:password_reset:day20261107:<32 hex>`.
- `riyadh_day_compact(now_epoch_s)`: the UTC instant + 3 h, as `YYYYMMDD` (equal to the date of `llm_spend_breaker.riyadh_day(...)[0]` without dashes); `seconds_to_riyadh_midnight(now)`: whole seconds to the next 00:00 +03:00, at least 1.
- No key, digest, email, local part, user id or pepper appears in any log line (R-S24-5, R-S24-9).

### 2.4 The six Lua scripts (module constants; each the LF join of the listed lines, no trailing LF; frozen by RED sha rows)

Every reply is a Lua table `{allowed, retry_after_seconds, count}` (ints; Redis truncates Lua numbers to integers in replies) except FAIL (an int) and CLEAR (an int). `now` = ARGV milliseconds since the epoch from the web process clock (`_now_ms()`, the test seam).

`LOGIN_GATE_SCRIPT` (KEYS[1] = the backoff hash; ARGV = [now_ms, cap_ms, ttl_s]); sha256 `ae12bf55585cfafe79dc9ff3ba55f2ec5a9bd76027ebb3ca5af693cd2617d34d`:
```
local c = tonumber(redis.call('HGET', KEYS[1], 'c') or '0')
local u = tonumber(redis.call('HGET', KEYS[1], 'u') or '0')
local now = tonumber(ARGV[1])
if now < u then return {0, math.ceil((u - now) / 1000), c} end
local w = 1000
for i = 1, math.min(c, 22) do w = w * 2 end
if w > tonumber(ARGV[2]) then w = tonumber(ARGV[2]) end
redis.call('HSET', KEYS[1], 'u', now + w)
redis.call('EXPIRE', KEYS[1], ARGV[3])
return {1, 0, c}
```
`LOGIN_FAIL_SCRIPT` (KEYS[1]; ARGV = [ttl_s]); sha256 `df42ae18aed6a692c4ced0575765c71c0e83e9db83bbd645dd5f0cb5a1d5112a`:
```
local c = redis.call('HINCRBY', KEYS[1], 'c', 1)
redis.call('EXPIRE', KEYS[1], ARGV[1])
return c
```
`LOGIN_CLEAR_SCRIPT` (KEYS[1]; no ARGV); sha256 `d5c2157a7f09aca2b3faee49953d80b5905a98c0afadb442553830b3952e58a1`:
```
return redis.call('DEL', KEYS[1])
```
`INTERVAL_SCRIPT` (KEYS[1] = the interval key; ARGV = [now_ms, interval_ms, ttl_s]); sha256 `8d04ebbfe5236d3a9a9090e71dfd8e5fb76530ab0f32bcb22aead3b0843d4251`:
```
local now = tonumber(ARGV[1])
local u = tonumber(redis.call('GET', KEYS[1]) or '0')
if now < u then return {0, math.ceil((u - now) / 1000), 1} end
redis.call('SET', KEYS[1], now + tonumber(ARGV[2]), 'EX', ARGV[3])
return {1, 0, 1}
```
`RESET_SCRIPT` (KEYS[1] = the interval key, KEYS[2] = the day key; ARGV = [now_ms, interval_ms, per_day, ttl_s, day_ttl_s, seconds_to_riyadh_midnight]); sha256 `963aab4312555db335dc98ec5c8958559f480356841f06eb88cff122497460ff`:
```
local now = tonumber(ARGV[1])
local u = tonumber(redis.call('GET', KEYS[1]) or '0')
local d = tonumber(redis.call('GET', KEYS[2]) or '0')
if now < u then return {0, math.ceil((u - now) / 1000), d} end
if d >= tonumber(ARGV[3]) then return {0, tonumber(ARGV[6]), d} end
redis.call('SET', KEYS[1], now + tonumber(ARGV[2]), 'EX', ARGV[4])
d = redis.call('INCR', KEYS[2])
if d == 1 then redis.call('EXPIRE', KEYS[2], ARGV[5]) end
return {1, 0, d}
```
`ACCOUNT_SCRIPT` (KEYS[1] = the account hash; ARGV = [now_ms, per_window, window_ms, ttl_s]); sha256 `8e3153ec40ac995ccf49506763518a4fc5a1af7c0047be40ccdd8114ea85085d`:
```
local now = tonumber(ARGV[1])
local w = tonumber(ARGV[3])
local s = tonumber(redis.call('HGET', KEYS[1], 's') or '0')
local c = tonumber(redis.call('HGET', KEYS[1], 'c') or '0')
if now - s >= w then
  s = now
  c = 0
end
if c >= tonumber(ARGV[2]) then return {0, math.ceil((s + w - now) / 1000), c} end
c = c + 1
redis.call('HSET', KEYS[1], 's', s, 'c', c)
redis.call('EXPIRE', KEYS[1], ARGV[4])
return {1, 0, c}
```

Semantics (what the RED's Python model of each script implements, keyed on the exact text):
- Login: the gate PRE-ARMS the window the attempt would earn on failure (`u = now + min(1000 * 2^c, cap)`), so concurrent attempts on one email admit exactly ONE and the others get 429 with the remaining wait; a counted failure only increments `c`; a success deletes the hash. Sequence for consecutive failures spaced at their windows: waits 1, 2, 4, 8, 16, 32, then the cap (60 by default). A non-counted result (unconfirmed email, transient, generic, "Login failed") leaves `c` unchanged; its pre-armed window (at most 2^c s) stands. The reset routes never read a login key.
- Register / reset / resend: an attempt arms the interval whatever the GoTrue outcome (existence never changes the throttle path, R-S24-9). Reset / resend: a refused attempt does not increment the day counter; the day cap's retry = the seconds to the next Riyadh midnight (the next day uses a new key).
- Account: a fixed window from the first attempt; the attempt that would exceed `per_window` is refused with retry = the window's remainder; a refused attempt does not count.
- Every decision is ONE EVAL (no pipeline, no read-then-write, no second round trip, R-S24-4); the login request makes at most two EVALs (the gate decision, then exactly one of FAIL / CLEAR, or none on a non-counted result).

### 2.5 Python API of `app/services/auth_throttle.py` (a NEW stdlib leaf; imports only stdlib, `fastapi.HTTPException` and `from app.services import cache_service as _cache_service`)

- `async def gate(endpoint: str, ident: object) -> None`: returns None to ALLOW; raises `HTTPException(status_code=429, detail={"error": THROTTLED_MESSAGE, "code": "RATE_LIMITED", "retry_after": <int >= 1>})` to REFUSE; never raises anything else (an unknown endpoint, a None ident, every Redis-side failure = allow). It computes the keys, runs the endpoint's script once, parses the reply, logs, decides.
- `async def record_login_failure(email: object, result: object) -> None`: runs LOGIN_FAIL only when `isinstance(result, dict) and result.get("error") == "Invalid email or password"`; never raises.
- `async def record_login_success(email: object) -> None`: runs LOGIN_CLEAR; never raises.
- `_eval(client, script, keys, args)`: the S81-04 two-shape dispatch (a local copy of `llm_spend_breaker._eval` :970-977, so the leaf imports no service; a RED row pins identical dispatch on both fakes).
- `async def _run(script, keys, args)`: `client = _cache_service.redis_client` read per call (None -> `RedisUnconfigured`); `asyncio.wait_for(asyncio.wrap_future(_pool().submit(_eval, client, script, keys, args)), redis_timeout_seconds())`; the loop thread never runs the command.
- `_parse_reply(raw) -> Tuple[bool, int, int]`: a list / tuple of exactly three non-bool ints with allowed in {0, 1}; else `ValueError`. `retry = max(1, retry)` on a refusal; a refusal never carries 0.
- `_now_ms()` = `int(time.time() * 1000)` (test seam); `_pool()` lazily builds the `auth-throttle` pool under a lock; `_reset_pepper_warning()` test seam.

### 2.6 The route insertions (`app/api/auth_routes.py`; one import + eight insertion sites; nothing else moves)

- Import (after the consent_service import block :19-24): `from app.services import auth_throttle  # S81-24 ENABLE_AUTH_THROTTLE_V2 (dark)`.
- `login`: first statement after the docstring (before `lockout = await check_account_locked(...)` :808):
  `if auth_throttle.auth_throttle_v2_enabled():` / `    await auth_throttle.gate("login", body.email)`.
  After `await track_failed_login(body.email)` :831: `if auth_throttle.auth_throttle_v2_enabled():` / `    await auth_throttle.record_login_failure(body.email, result)`.
  After `await clear_failed_logins(body.email)` :848: `if auth_throttle.auth_throttle_v2_enabled():` / `    await auth_throttle.record_login_success(body.email)`.
- `register`: after the consent block (:706-708), before `result = await register_user(...)` :710: the block with `gate("register", body.email)` (a consent-refused request arms nothing).
- `password_reset`: first statement after the docstring: `gate("password_reset", body.email)`.
- `resend_verification`: first statement after the docstring, OUTSIDE the try: `gate("resend_verification", body.email)` (inside the try the `except Exception` arm would swallow the 429 into a 200).
- `change_password`: first statement after the docstring: `gate("change_password", current_user["id"])`.
- `update_email`: first statement after the docstring: `gate("update_email", current_user["id"])`.
In every gated route the V2 `If` precedes the first `Await` of the body (AST order). The W1-9b calls, the audit events, the decorators, the docstrings and every other line are unchanged.

### 2.7 Log templates (constants, ints and type names only)

- WARNING once per process: `[AUTH_THROTTLE] pepper unset`.
- WARNING per fail-open decision or record: `[AUTH_THROTTLE] skipped endpoint=%s type=%s` with `endpoint` in ENDPOINTS or `login_fail` / `login_clear`, and `type` the exception type name (`RedisUnconfigured`, `TimeoutError`, `ConnectionError`, `ValueError`, ...). Not rate-limited (Q9).
- INFO per refusal: `[AUTH_THROTTLE] throttled endpoint=%s count=%d retry_after=%d`.
- INFO per echo request: `[HOP_PROBE] xff_entries=%d xff_leftmost_is_peer=%s xff_rightmost_is_peer=%s xff_leftmost_public=%s x_real_ip_present=%s x_real_ip_is_peer=%s x_real_ip_public=%s forwarded_present=%s cf_present=%s peer_public=%s` with each `%s` exactly `true` or `false`.
No other new log line. ERROR is never used.

### 2.8 The MS4 echo line (`app/middleware/request_id.py`)

- `HOP_PROBE_PATHS = ("/health", "/api/v1/app/version")`. In `dispatch`, after `request.state.request_id = request_id` and before `await call_next`: `if hop_probe_log_enabled() and request.method == "GET" and request.url.path in HOP_PROBE_PATHS: _log_hop_probe(request)`.
- `_log_hop_probe(request)` never raises (a bare `except Exception: pass`; a failure logs nothing). Peer = `request.client.host` when present. A value "parses" when `ipaddress.ip_address(v.strip())` succeeds; `is_peer` = both parse and are equal; `public` = parses and `.is_global`. `xff_entries` = the count of non-empty stripped entries of `X-Forwarded-For` split on commas (0 when absent); leftmost / rightmost = the first / last such entry. `x_real_ip_*` from `X-Real-IP`; `forwarded_present` = a `Forwarded` header is present; `cf_present` = a `CF-Connecting-IP` header is present; `peer_public` from the peer.
- OFF: one `os.getenv` per request, nothing else; no `[HOP_PROBE]` line on any path. ON: one line per GET to the two paths only (HEAD, POST and every other path: none). The response is unchanged in both states.

### 2.9 Failure table (every row: allow, the per-IP floor and W1-9b unchanged, never a 500)

| condition (flag ON) | gate result | Redis calls | log |
|---|---|---|---|
| pepper unset / blank / not encodable | allow | 0 | `pepper unset` once per process |
| ident None / not a str / blank | allow | 0 | none |
| `cache_service.redis_client` None | allow | 0 | `skipped endpoint=<e> type=RedisUnconfigured` |
| EVAL raises (ConnectionError, any Exception) | allow | 1 | `skipped ... type=<Type>` |
| EVAL slower than the timeout knob | allow | 1 (left running on the pool) | `skipped ... type=TimeoutError` |
| malformed reply (None, short, non-int, bool) | allow | 1 | `skipped ... type=ValueError` |
| garbage knob | the default | as configured | none |
| concurrent EVALs on one key | Redis serialises scripts (atomic); login admits exactly one per pre-armed window | n | n-1 `throttled` lines |
| FAIL / CLEAR raise or time out | the route's own response unchanged | 1 | `skipped endpoint=login_fail|login_clear type=<Type>` |
| ENABLE_HOP_PROBE_LOG ON, garbage headers | the line with false booleans and the true count | 0 | one `[HOP_PROBE]` line |

### 2.10 The flag-OFF identity invariant (the main invariant, R-S24-14)

With `ENABLE_AUTH_THROTTLE_V2` unset / `""` / `"false"` / `"0"` / `"off"` / `" FALSE "` and the FULL companion configuration (the pepper and every knob in 2.2 set to synthetic in-range NON-default values, `ENABLE_HOP_PROBE_LOG` OFF): every auth response (status, body fields, header-name set, Retry-After), every `app.*` log record (logger, level, message), the W1-9b and the V2 Redis command sequence on ONE recorder installed as BOTH `auth_service.redis_client` and `cache_service.redis_client`, and the service-mock call order are byte-identical to the base literals; the `auth-throttle` pool is never built; no EVAL is issued. With `ENABLE_HOP_PROBE_LOG` OFF no `[HOP_PROBE]` line appears on any path. The 429 contract (tests/test_429_contract.py) is green in both states.

### 2.11 Test seams (production values in brackets)

`auth_throttle._now_ms` [wall clock ms]; `auth_throttle._cache_service.redis_client` via `monkeypatch.setattr(cache_service, "redis_client", fake)` [the import-time client]; `auth_throttle._pool` / `POOL_WORKERS` [4]; `auth_throttle._reset_pepper_warning()`; the knobs by env [2.2 defaults]; `auth_routes.login_user` / `register_user` / `request_password_reset` / `resend_verification_email` / `change_user_password` / `update_user_email` / `check_account_locked` / `track_failed_login` / `clear_failed_logins` / `log_audit_event` by monkeypatch; `app.dependency_overrides[get_current_user]` [the GoTrue verify]; `TestClient(app, client=(host, port))` [the Railway edge peer].

## 3. Change list (in the order GREEN applies it)

0. Byte copies (shutil.copyfile) of `app/api/auth_routes.py`, `app/middleware/request_id.py`, `tests/_env_safety.py`, `CLAUDE.md` into the GREEN notes folder; sha256 recorded.
1. NEW `app/services/auth_throttle.py` (pure ASCII, LF): sections 2.1-2.7; the six scripts as module constants named exactly `LOGIN_GATE_SCRIPT`, `LOGIN_FAIL_SCRIPT`, `LOGIN_CLEAR_SCRIPT`, `INTERVAL_SCRIPT`, `RESET_SCRIPT`, `ACCOUNT_SCRIPT`; no string listed in G1; no by-name import of `redis_client`.
2. EDIT `app/api/auth_routes.py` (CRLF preserved): the import line and the eight insertion sites of 2.6; nothing else.
3. EDIT `app/middleware/request_id.py` (CRLF preserved): `import ipaddress`, `import logging`, `import os`; `logger = logging.getLogger(__name__)`; `HOP_PROBE_PATHS`; `hop_probe_log_enabled()`; `_log_hop_probe(request)`; the one guarded call in `dispatch` (2.8).
4. EDIT `tests/_env_safety.py` (CRLF preserved): after `"DEVICE_KEY_PEPPER",` (:136) add the comment `# Auth-throttle key HMAC pepper (S81-24); absence = the V2 throttle inactive (fail open).` and `"AUTH_THROTTLE_PEPPER",`.
5. The frozen RED file `tests/test_s81_s24_auth_throttle.py` (written by the RED agent, unedited at GREEN) and the GREEN gate-rows file `tests/test_s81_s24_gate_rows.py` (house practice: the comm-set hygiene rows, the CRLF / whole-file-diff row, the pure-ASCII row over the new files, the CLAUDE.md row presence).
6. EDIT `CLAUDE.md` (CRLF preserved): the S81-24 block (section 8.1) after the newest block at the final round (at daf86d32: after the S81-22 owner-steps bullet :608, before the blank line and `## Tests`), plus one clause in the `:341` Feature Flags pointer sentence naming the block, in merge order.
No other file: no app/legal, no migration, no SmartCompareApp file, no rate_limiter / error_handler / main.py edit, no .github edit, no requirements change, no processors.json row (Upstash is an existing processor; no new host).

## 4. Existing pins

### 4.1 Pins that change deliberately

None expected. The eighteen `limiter.limit` referencing test files are NOT edited (R-S24-10). A GREEN red in any existing pin is an E-row named with its anchor and fixed by a ruled pin-fix, never by weakening.

### 4.2 Pins that must stay green and unedited

The eighteen files that reference `limiter.limit` by string, with what each asserts:
- tests/conftest.py :236 (comment; the autouse `_reset_rate_limiter` fixture resets the in-memory storage per test).
- tests/test_429_contract.py :17-51, :202-245, :388-403 (the slowapi 429 envelope, Retry-After <= window + 1, window-read failure degrades, no X-RateLimit headers on a 200).
- tests/test_account_deletion.py :33, :47 (patch `limiter.enabled` False).
- tests/test_account_deletion_u8b.py :118 (patch), :257 (the `@limiter.limit("1/minute")` directly above `async def delete_account`).
- tests/test_account_deletion_u8b_fix_pins.py :210 (patch).
- tests/test_account_deletion_u8c_sentry_chain.py :239 (patch).
- tests/test_attribution_endpoint.py :91-106 (`@limiter.limit` within the window around `"/attribution"`).
- tests/test_auth_demographics.py :387-397 (`limiter.limit` in the route source).
- tests/test_limiter_endpoint_key.py :24-88, :195, :467, :496 (the registered limits per route under the endpoint key style).
- tests/test_m13_01_slowapi_middleware.py :82 (an undecorated route under the default limit) and the lockout rows for PUT /password and PUT /email.
- tests/test_paid_route_metering.py :35 (comment; the paid-route limit).
- tests/test_password_reset_deep_link.py :322-329 (`@limiter.limit("5/minute")` within the three lines above `async def password_recovery(`).
- tests/test_retro_r_auth_fixer_pins.py :63 (`REFRESH_BUDGET = 10` for POST /auth/refresh).
- tests/test_retro_w1_9.py :343 (the attribution route's own 30/minute) and :274 (the middleware order).
- tests/test_security_middleware.py :104, :147 (a private test app's limiter).
- tests/test_security_regression.py :42-50 (admin source), :425-439 (`@limiter.limit("5/minute")`, `("3/minute")`, `("1/minute")` substrings in auth_routes.py), :660-668 (demographics), :1510-1524 (text_compare).
- tests/test_sentry_channels_u8d.py :436 (patch).
- tests/test_streaming.py :460 (patch).
Plus: tests/test_brute_force.py and tests/test_retro_w1_9_429.py (the W1-9b lockout, its command order and windows: unchanged ON and OFF because V2 adds beside it); tests/test_m13_02_proxy_aware_ratelimit.py :51-57 (the leftmost-XFF pin; S81-24b updates it, not this unit); tests/test_observability.py :179-183, tests/test_retro_w1_1.py :211, tests/test_s81_s05_request_context.py :103 / :110 / :1283 / :1371-1400 (middleware order, the pepper list, the needle walker); tests/test_conftest_env_safety.py :292, :361-381; tests/test_auth_interceptor.py (the two baselined nodes stay red identically).

## 5. RED tests

File `tests/test_s81_s24_auth_throttle.py` (hermetic; free tier; `import app.main` FIRST in an autouse fixture, then monkeypatch.setenv, the DOTENV GUARD rule). Every RED row fails at base on an AssertionError only: the module and its names are read through a `_need(module_name, attr)` helper (`importlib.util.find_spec` then `getattr` with an assert), never a bare import. Every PIN row is green at base and runs with the FULL configuration (2.10) and the recorders. Fixtures:
- `FULL_CONFIG`: `AUTH_THROTTLE_PEPPER = "s24-pepper-" + "q" * 8`, CAP 30, REGISTER 20, RESET 15, PER_DAY 3, ACCOUNT_PER_WINDOW 2, ACCOUNT_WINDOW 120, TTL 7200, REDIS_TIMEOUT 0.25; `ENABLE_HOP_PROBE_LOG` unset.
- `FakeRedis` (upstash shape: `type(fake).__module__ = "upstash_redis.s24fake"`, `eval(script, keys=, args=)`) and `FakeRedisPy` (redis-py shape `eval(script, numkeys, *keys_and_args)`): a dict store with TTLs on a fake clock; `get / set(nx, ex) / incr / expire(nx) / ttl / delete / hget / hset / hincrby`; `eval` dispatches on `script == getattr(auth_throttle, NAME)` to a Python model of that script (2.4 semantics) under a `threading.Lock` (one script at a time, as Redis does), any other text -> AssertionError; every call appended to `fake.calls` as `(name, args, sorted kwargs)`; `fake.fail_with` / `fake.delay` / `fake.reply_override` knobs for the failure rows.
- The recorder is installed as BOTH `app.services.auth_service.redis_client` and `app.services.cache_service.redis_client` (monkeypatch) in every route row.
- Route rows use `TestClient(app)` with the service functions mocked at `app.api.auth_routes.<name>` and `app.dependency_overrides[get_current_user] = lambda: {"id": <uuid str>, "email": <synthetic>, "access_token": "t"}` for the account routes; `_now_ms` advanced by monkeypatch.
- Base literals (recorded at RED from 1.2-1.4 and probe_bodies.json) for bodies, header-name sets, Redis sequences and log records.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R01 | test_r01_module_surface | auth_throttle exists with FLAG, PEPPER_ENV, ENDPOINTS (the six, in order), the eight knob names and defaults, the six script constants, gate, record_login_failure, record_login_success, digest, email_ident, account_ident, throttle_key, riyadh_day_compact, seconds_to_riyadh_midnight, THROTTLED_MESSAGE | RED (find_spec None) | step 1 |
| R02 | test_r02_flag_idiom_per_call | truth table: unset / "" / "false" / "0" / "off" / "no" / "garbage" -> False; "true" / "1" / "yes" / "on" / " TRUE " / "On" -> True; setenv between two calls flips the result | RED | 2.1 |
| R03 | test_r03_knobs_defensive_per_call | per knob: unset, "", "abc", "inf", "nan", "-5", "0", "60.5" (int knobs), below and above the range -> the default; an in-range value -> that value; the timeout knob accepts "0.25", refuses "0", "10", "nan" | RED | 2.2 |
| R04 | test_r04_scripts_frozen | each constant == the LF join of the 2.4 lines and its sha256 == FROZEN_SCRIPT_SHA256[name] (the six digests of 2.4); pure ASCII | RED | 2.4 |
| R05 | test_r05_key_grammar_and_digest | `throttle_key("login","backoff",d) == "auth_throttle:login:backoff:" + d`; digest == the HMAC-SHA256 of 2.3 truncated to 32 lower hex; " User-A@Example.COM " and "user-a@example.com" share a digest; another pepper differs; the key holds no "@", no local part, no pepper; account digest = digest of the user id, never of the email | RED | 2.3 |
| R06 | test_r06_pepper_unset_fail_open_once | flag ON, pepper unset then "   ": three login gate calls -> allowed, zero fake calls, exactly ONE WARNING `[AUTH_THROTTLE] pepper unset` (after `_reset_pepper_warning()`) | RED | 2.3, 2.9 |
| R07 | test_r07_riyadh_day | 2026-11-06T20:59:59Z -> "20261106"; 21:00:00Z -> "20261107"; equals `llm_spend_breaker.riyadh_day` date without dashes; seconds_to_riyadh_midnight(21:00:00Z) == 86400 and (20:59:59Z) == 1 | RED | 2.3 |
| R10 | test_r10_login_backoff_sequence | ON + FULL_CONFIG (cap 30): eight consecutive wrong-password logins, each sent when the previous window has passed: all 401 (base body); an immediate retry after the n-th failure -> 429 with retry_after_seconds = min(2^(n-1), 30) for n = 1..8 (1, 2, 4, 8, 16, 30, 30, 30); the fake's EVAL list per allowed login = [LOGIN_GATE, LOGIN_FAIL] | RED | 2.4, 2.6 |
| R11 | test_r11_success_clears | after three failures, a success past the window -> 200 and LOGIN_CLEAR issued; the next wrong attempt is allowed and its retry is 1 again | RED | 2.6 |
| R12 | test_r12_only_credential_failures_count | results "Please verify your email before logging in", {"error": "Connection failed. Please try again.", "code": "UPSTREAM_UNAVAILABLE"}, "Something went wrong. Please try again later.", "Login failed": LOGIN_GATE issued per request, LOGIN_FAIL never; the hash `c` stays 0 | RED | 2.5 |
| R13 | test_r13_default_cap | the cap knob unset: after ten counted failures the retry never exceeds 60 and reaches 60 | RED | 2.2 |
| R14 | test_r14_login_placement_order | the gate EVAL precedes the first W1-9b `get` on the recorder and precedes `login_user`; a refused login calls neither `check_account_locked`, nor `login_user`, nor `log_audit_event` | RED | 2.6 |
| R15 | test_r15_w19b_untouched_on | ON: a counted failure's recorder sequence == [eval LOGIN_GATE, get, set(nx, ex=900), incr, expire(900, nx), eval LOGIN_FAIL]; a success == [eval LOGIN_GATE, get, delete, eval LOGIN_CLEAR] | RED | 2.6 |
| R16 | test_r16_concurrent_login_one_admitted | asyncio.gather of five gate("login", E) on a fresh key -> exactly one allowed, four HTTPException 429 with retry 1 | RED | 2.4 |
| R20 | test_r20_register_interval | ON (interval 20): register E -> 200 (mock success), INTERVAL issued; immediately E again -> 429 retry 20 and register_user called once; F -> 200; E after 20 s -> 200 | RED | 2.6 |
| R21 | test_r21_register_existence_blind | E (mock: the "already exists" 400) and F (mock: success): the first responses equal the base literals (400 and 200 fields); the second responses within the interval are both 429 with field-equal bodies (request_id aside) and equal header-name sets | RED | 2.4 |
| R22 | test_r22_register_gate_after_consent | consent required (monkeypatch `consent_required_enabled` True) and no consent -> the base consent refusal and ZERO EVAL; with consent fields -> one INTERVAL EVAL | RED | 2.6 |
| R30 | test_r30_reset_interval_and_day | ON (interval 15, per_day 3): reset E -> 200 (base body); immediately -> 429 retry 15; three allowed resets spaced 15 s -> the fourth -> 429 retry = seconds_to_riyadh_midnight(now); after 21:00Z -> 200 on a new day key | RED | 2.4 |
| R31 | test_r31_resend_own_keys | resend E after reset E (same instant) -> 200 (separate endpoint keys); resend's own interval and day cap as R30 | RED | 2.3 |
| R32 | test_r32_reset_existence_blind | reset for E (mock success) and F (mock failure dict): identical 200 bodies; identical throttle replies and identical 429 bodies (request_id aside) | RED | 2.4 |
| R33 | test_r33_reset_never_blocked_by_login | E's login driven to a 30 s backoff, then reset E -> 200 with exactly one RESET EVAL whose KEYS are `auth_throttle:password_reset:*` only; `POST /password-recovery` -> no EVAL | RED | 2.6 |
| R34 | test_r34_ttls | interval key SET EX = TTL knob (7200); day key EXPIRE 86400 on the first increment only; backoff / account hash EXPIRE 7200 on every write; effective TTL = max(TTL, window) when TTL 60 and window 120 | RED | 2.2, 2.4 |
| R40 | test_r40_change_password_account_window | ON (2 per 120 s): two attempts -> the service's result; the third -> 429 with 1 <= retry <= 120 and change_user_password not called; the key digest is of the user id; no `auth_throttle:login:*` key touched | RED | 2.6 |
| R41 | test_r41_update_email_account_window | the same for PUT /email on its own key | RED | 2.6 |
| R42 | test_r42_account_routes_keep_w19b | ON: the W1-9b get precedes the service call and track / clear follow it, after the ACCOUNT EVAL | RED | 2.6 |
| R50 | test_r50_v2_429_equals_slowapi_429 | the slowapi 429 (4th reset, V2 OFF) vs the V2 429: status 429; `list(body)` == ["success", "error", "code", "request_id", "retry_after_seconds"] in both; error, code and the value types equal; header-name sets equal; `Retry-After` == str(retry_after_seconds) | RED | 2.5 |
| R51 | test_r51_retry_after_at_least_one | a refusal reply with retry 0 or -3 -> the 429 carries 1 | RED | 2.5 |
| R60 | test_r60_no_client_fail_open | ON, redis_client None: login / register / reset / resend / change_password / update_email -> the base responses; one WARNING `[AUTH_THROTTLE] skipped endpoint=<e> type=RedisUnconfigured` per request | RED | 2.9 |
| R61 | test_r61_eval_raises_fail_open | `fail_with = ConnectionError` -> allow, WARNING `type=ConnectionError`, never 500 | RED | 2.9 |
| R62 | test_r62_eval_timeout_fail_open | timeout knob 0.05, the fake sleeps 0.5 s -> allow within 0.4 s, WARNING `type=TimeoutError` | RED | 2.5 |
| R63 | test_r63_malformed_reply_fail_open | replies None, [1], ["1", "0", "0"], {}, [True, 0, 0], [2, 0, 0] -> allow, WARNING `type=ValueError` | RED | 2.5 |
| R64 | test_r64_record_failures_harmless | LOGIN_FAIL / LOGIN_CLEAR raising -> the 401 / 200 unchanged; WARNING endpoint=login_fail / login_clear | RED | 2.9 |
| R65 | test_r65_log_hygiene | over R10-R64 every `[AUTH_THROTTLE]` record full-matches one of the three 2.7 templates; no record contains the email, its local part, a 32- or 64-hex run, the pepper, the user id or "auth_throttle:" | RED (no record exists: asserted non-empty) | 2.7 |
| R66 | test_r66_bad_ident_allows | gate("login", None / 123 / b"x" / "" / "   ") -> allow, zero EVAL, no record; gate("login", "user-a@example.com") -> one EVAL | RED | 2.3 |
| R82 | test_r82_v2_placement_ast | for the six gated routes: an `If` whose test is `auth_throttle.auth_throttle_v2_enabled()` and whose body is one `Await` of `auth_throttle.gate("<endpoint>", <ident>)` (ident `body.email` or `current_user["id"]`), preceding the first other `Await` of the body; login / password_reset / resend_verification / change_password / update_email: the first statement after the docstring; register: after the consent `If`; resend: not inside a `Try`; non-gated routes (refresh, password_recovery, social_login, delete_account, the profile routes, logout): no `auth_throttle` name | RED | 2.6 |
| R83 | test_r83_login_record_placement_ast | inside `if not result["success"]:` the guarded `record_login_failure(body.email, result)` follows `await track_failed_login(body.email)`; the guarded `record_login_success(body.email)` follows `await clear_failed_logins(body.email)` | RED | 2.6 |
| R90 | test_r90_pepper_in_credentials_unset | "AUTH_THROTTLE_PEPPER" in `_env_safety.CREDENTIALS_UNSET`; auth_throttle reads no `DEVICE_KEY_PEPPER` (AST: no getenv of it) | RED | step 4 |
| R91 | test_r91_leaf_imports | auth_throttle imports only stdlib, fastapi and `from app.services import cache_service as _cache_service`; no `from app.services.cache_service import redis_client`; no import of auth_service / llm_spend_breaker / usage_service / request_context; `_eval` dispatch equal on FakeRedis and FakeRedisPy | RED | 2.5 |
| R92 | test_r92_hygiene | auth_throttle.py and request_id.py are pure ASCII; neither contains a G1 needle; no module constant whose name carries a gitleaks keyword is a 64-hex literal | RED (auth_throttle.py absent: asserted present) | 1.9 |
| R100 | test_r100_hop_probe_health_line | ON, `TestClient(app, client=("100.64.0.1", 50000))`, GET /health with `X-Forwarded-For: 8.8.8.8, 100.64.0.1` -> exactly one INFO record == `[HOP_PROBE] xff_entries=2 xff_leftmost_is_peer=false xff_rightmost_is_peer=true xff_leftmost_public=true x_real_ip_present=false x_real_ip_is_peer=false x_real_ip_public=false forwarded_present=false cf_present=false peer_public=false` | RED | 2.8 |
| R101 | test_r101_hop_probe_version_headers | ON, GET /api/v1/app/version with `X-Real-IP: 100.64.0.1`, `Forwarded: for=192.0.2.1`, `CF-Connecting-IP: 192.0.2.1`, no XFF -> `xff_entries=0 ... x_real_ip_present=true x_real_ip_is_peer=true x_real_ip_public=false forwarded_present=true cf_present=true peer_public=false` | RED | 2.8 |
| R102 | test_r102_hop_probe_paths_only | ON: POST /api/v1/auth/login, GET /, GET /api/v1/usage/status, HEAD /health -> no `[HOP_PROBE]` record; GET /health -> one | RED | 2.8 |
| R103 | test_r103_hop_probe_no_values | every `[HOP_PROBE]` record over R100-R104 full-matches the 2.7 template; none contains an injected header value or IP string | RED | 2.8 |
| R104 | test_r104_hop_probe_garbage | ON: XFF "not-an-ip, , 300.1.1.1", a 200-entry XFF, a non-ASCII value -> one line each with the non-empty count and false booleans; response bodies and status equal OFF | RED | 2.8 |
| R105 | test_r105_hop_probe_flag_idiom | the 2.1 truth table for ENABLE_HOP_PROBE_LOG, read per request | RED | 2.8 |
| P70 | test_p70_off_identity_login | FULL_CONFIG, the six OFF spellings: login failure / success / locked -> status, body fields, header-name sets, Retry-After, the recorder sequence (1.3), the mock call order and the `app.*` records == the base literals; no EVAL; the pool unbuilt (when the module exists) | PIN | 2.10 |
| P71 | test_p71_off_identity_other_routes | the same for register (success and "already exists"), password_reset (success and failure), resend (ok and raise), change_password (ok, wrong password, locked), update_email (ok, wrong password, locked) | PIN | 2.10 |
| P72 | test_p72_off_no_throttle_records | over P70-P71 no `[AUTH_THROTTLE]` record, no fake.eval call | PIN | 2.10 |
| P73 | test_p73_hop_probe_off_silent | ENABLE_HOP_PROBE_LOG OFF (six spellings), ENABLE_AUTH_THROTTLE_V2 ON or OFF: forged headers on GET /health and /api/v1/app/version -> no `[HOP_PROBE]` record; body keys and header-name sets equal the base | PIN | 2.8 |
| P74 | test_p74_429_contract_both_states | V2 OFF and ON with redis_client None: the 4th reset in a minute -> the base slowapi 429 literal (fields, header names, 1 <= Retry-After <= 61) | PIN | 2.9 |
| P80 | test_p80_decorator_table_ast | the 15-row table of 1.1 (function, method, path, rate) parsed from the AST equals the literal; the six undecorated routes carry no limiter; no limiter keyword arguments; `_EXPIRED_LOGOUT_BUDGET` is `parse_rate_limit("10/minute")` | PIN | 1.1 |
| P81 | test_p81_decorator_order_ast | in every decorated route the limiter decorator is the one directly after the router decorator, exactly one each | PIN | 1.1 |
| P106 | test_p106_probe_paths_unchanged_on | ENABLE_HOP_PROBE_LOG ON vs OFF: /health and /api/v1/app/version status, body key sets and header-name sets equal | PIN | 2.8 |

Counts: 45 RED rows (R01-R07, R10-R16, R20-R22, R30-R34, R40-R42, R50-R51, R60-R66, R82-R83, R90-R92, R100-R105), 8 PIN rows (P70-P74, P80, P81, P106). Satisfiability: the RED agent proves every row green on an in-place prototype of steps 1-4 (byte copies, restored and sha-checked) before freezing the file. The session-80 eval_regression.json scenarios do not apply (no compare path); the fixtures come from the brief and 1.2-1.4.

## 6. Mutation table (each mutant on a byte copy, an exact-string edit matching once, the killing rows via pyt.py -k with bound 600, restored, sha256 compared)

| # | file | mutant | killed by |
|---|---|---|---|
| M01 | auth_routes.py | login gate `if auth_throttle.auth_throttle_v2_enabled():` -> `if True:` | P70, P72 |
| M02 | auth_routes.py | reset gate guard -> `if True:` | P71 |
| M03 | auth_throttle.py | flag truthy set drops "on" | R02 |
| M04 | auth_throttle.py | a knob range check removed (cap accepts 1) | R03 |
| M05 | auth_throttle.py | LOGIN_GATE `now < u` -> `now <= u` | R04 |
| M06 | auth_throttle.py | digest without the pepper (sha256 of the ident) | R05 |
| M07 | auth_throttle.py | email_ident drops `.lower()` | R05 |
| M08 | auth_throttle.py | digest `[:32]` -> full 64 | R05 |
| M09 | auth_throttle.py | pepper unset -> refuse (raise 429) | R06 |
| M10 | auth_throttle.py | the pepper warning latch removed | R06 |
| M11 | auth_throttle.py | RIYADH_UTC_OFFSET_HOURS 3 -> 0 | R07, R30 |
| M12 | auth_throttle.py | record_login_failure counts every failure | R12 |
| M13 | auth_routes.py | the record_login_success line deleted | R11, R83 |
| M14 | auth_routes.py | login gate moved after `login_user` | R14, R82 |
| M15 | auth_routes.py | `await track_failed_login(body.email)` deleted | R15, P70 |
| M16 | auth_throttle.py | the cap ARGV passed in seconds, not ms | R10, R13 |
| M17 | auth_throttle.py | RESET per_day ARGV = knob + 1 | R30 |
| M18 | auth_throttle.py | the day-cap retry ARGV = the interval | R30 |
| M19 | auth_routes.py | change_password ident `current_user["id"]` -> `current_user.get("email")` | R40, R82 |
| M20 | auth_throttle.py | 429 code "RATE_LIMITED" -> "THROTTLED" | R50 |
| M21 | auth_throttle.py | `max(1, retry)` removed | R51 |
| M22 | auth_throttle.py | the fail-open except narrowed to ConnectionError | R62, R63 |
| M23 | auth_throttle.py | _parse_reply accepts bool | R63 |
| M24 | auth_throttle.py | the throttled line adds `key=%s` | R65 |
| M25 | auth_throttle.py | the day key TTL ARGV = TTL knob | R34 |
| M26 | auth_routes.py | resend gate moved inside the try | R82 (and R31: the 429 becomes a 200) |
| M27 | auth_routes.py | reset gate endpoint literal "password_reset" -> "login" | R33 |
| M28 | request_id.py | the echo flag check removed | P73 |
| M29 | request_id.py | "/" added to HOP_PROBE_PATHS | R102 |
| M30 | request_id.py | the line adds the leftmost value | R103 |
| M31 | request_id.py | leftmost / rightmost swapped | R100 |
| M32 | request_id.py | peer_public = `not is_private` | R100 (100.64.0.1 is neither private nor global) |
| M33 | tests/_env_safety.py | the AUTH_THROTTLE_PEPPER entry removed | R90 |
| M34 | auth_throttle.py | `from app.services.cache_service import redis_client` | R91, R60 |
| M35 | auth_routes.py | login `@limiter.limit("5/minute")` -> `("6/minute")` | P80 |
| M36 | auth_throttle.py | register gate uses INTERVAL with interval_ms = interval seconds | R20 |

Equivalent survivors are reported for a ruling; none are expected (the gate does not re-read the flag, by design, so M01 / M02 are killable).

## 7. Comm set and gates for GREEN (cheapest first)

1. `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` over the four edited / new app and test files; pure-ASCII byte check of auth_throttle.py, the RED and gate-rows files; `git diff --stat` shows no whole-file diff (CRLF preserved in the four edited files).
2. The RED file at base (scratch detached worktree, no junction): every R row FAILED on AssertionError only, every P row passed (bound 600); at head: all 53 green (bound 600). The gate-rows file at head.
3. The mutation table (section 6), one mutant at a time, bound 600 each, under the MUTATION LOCK.
4. The touched-and-pinned set of 1.10 at head (17 files, bound 1200): only the two baselined auth_interceptor nodes red.
5. The comm set: `comm_set_daf86d32.txt` (364 files, sha256 `a9a3f4b3568ce39f3a9108bae21cb38c5f669d9d6cb91ab73bbdd600fc6ea0e7`) = the module and symbol reference grep (auth_routes, auth_service, rate_limiter, error_handler, request_id, auth_throttle, _env_safety, the /api/v1/auth, /api/v1/app/version and /health path strings; 147 files) UNION the app.main importers (132; the whole route surface, R-S24-15) UNION the source-scanning walkers (Path("app ..., "app/", rglob, glob, inspect.getsource, ast.parse, os.listdir, scandir; 258) UNION the CLAUDE.md readers (38 by string, incl. test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire) UNION the SmartCompareApp-scanning backend tests (27) UNION the named pins (test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command*, test_sentry_channels_u8d_unit) MINUS the four tests/test_precommit_hook*.py (NOT RUN: no .githooks change) PLUS, at GREEN, the RED and gate-rows files. Chunks of at most 25 files, bound 1200, one pytest at a time; `comm -13` of the sorted FAILED ids base vs head EMPTY; a branch-only failure re-run against base once.
6. Base record (LC-6 / GC-9): 355 of the 364 members are in the stored 05ccaed2 record `48158306...` (729 files, 22 environmental FAILED ids); reuse PER FILE for a member that references none of compare_runs / cron_compare_judge / text_routes / image_routes / url_routes / CLAUDE.md / the three S81-22-edited test files, is not a glob walker and whose bytes are unchanged 05ccaed2 -> the RED base; re-run the rest (incl. the 9 members not in the record) at the RED base in a junction-free detached scratch worktree; prefer a stored record at the RED base sha if the G8 RED stores one first (R-S24-15).
7. The fourteen client fences (brand/inAppMark.u4c, clientTruth/{medicalNote,privacyManifest,shareTruth}.s74, clipboardFallbackService, config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService(+.edges), ResultsScreen.timeout) + b3a/nativeStrings by path through the orchestrator's junction at GREEN (an app/ edit); the accepted base failures are the 4 nativeBundle.w37 drift nodes. The FULL jest suite once, in the final round (LC-7).
8. The corpus gate is NOT required (no price-pipeline module).

## 8. CLAUDE.md row and owner steps

### 8.1 The block (after the newest block at the final round)

**SESSION 81 flags (S81-24 AUTH-THROTTLE-V2 phase 1 + MS4 HOP-PROBE, 2026-11-07; TWO new flags, default OFF, read PER CALL; new names, so unset in production by construction (Railway not read); FOCUS; no migration, no client file, no legal file):**
- `ENABLE_AUTH_THROTTLE_V2` (`app/services/auth_throttle.py::auth_throttle_v2_enabled`, a stdlib leaf over `cache_service.redis_client` read per call; the flag is the first statement of the guard at each of the six gated routes in `app/api/auth_routes.py`). **Effect ON:** per-email throttles on login (backoff 1, 2, 4, 8 ... s up to `AUTH_THROTTLE_LOGIN_CAP_SECONDS` 60 after consecutive wrong-password / unknown-user results; a success clears it; the password reset and recovery are never blocked by it), register (one per email per `AUTH_THROTTLE_REGISTER_INTERVAL_SECONDS` 60), password reset and resend verification (one per email per `AUTH_THROTTLE_RESET_INTERVAL_SECONDS` 60 and `AUTH_THROTTLE_RESET_PER_DAY` 5 per Asia/Riyadh day, each on its own keys), and per-account throttles on PUT /auth/password and PUT /auth/email (`AUTH_THROTTLE_ACCOUNT_PER_WINDOW` 5 per `AUTH_THROTTLE_ACCOUNT_WINDOW_SECONDS` 600); ONE Lua EVAL per decision (six frozen scripts) on a dedicated 4-thread `auth-throttle` pool under `AUTH_THROTTLE_REDIS_TIMEOUT_SECONDS` 0.5; keys `auth_throttle:<endpoint>:<kind>:<HMAC-SHA256(AUTH_THROTTLE_PEPPER, the lower-cased email or the user id)[:32]>`, expiring `AUTH_THROTTLE_TTL_SECONDS` 21600 (6 h) after the last write, the per-day counter 24 h after its first increment; a refusal is the SAME 429 envelope as the slowapi limit (`code` RATE_LIMITED, `Retry-After` = `retry_after_seconds`), which build 3 renders as its rate-limit copy; every Redis error, timeout, unset client or unset pepper fails OPEN with one `[AUTH_THROTTLE] skipped endpoint=<e> type=<T>` (or once per process `[AUTH_THROTTLE] pepper unset`) WARNING; refusals log `[AUTH_THROTTLE] throttled endpoint=<e> count=<n> retry_after=<s>`. The per-IP `@limiter.limit` floor and the W1-9b lockout are untouched in both states. **Flag OFF:** byte-identical (responses, headers, log lines, the Redis command sequence; pinned by the frozen RED `tests/test_s81_s24_auth_throttle.py`). `AUTH_THROTTLE_PEPPER` joins `tests/_env_safety.CREDENTIALS_UNSET`.
- `ENABLE_HOP_PROBE_LOG` (`app/middleware/request_id.py::hop_probe_log_enabled`, read per request inside `RequestIDMiddleware.dispatch`). **Effect ON:** one INFO `[HOP_PROBE] xff_entries=<n> xff_leftmost_is_peer=<b> ... peer_public=<b>` line per GET /health and GET /api/v1/app/version (counts and booleans only; never an IP, a hash or a header value). ON only for the probe window, then unset.
- **Stated limits:** section 9 of the unit spec (the Python model of the Lua in hermetic tests; the process clock; fail-open leaves only the per-IP floor during an Upstash outage; the per-IP floor still keys on the edge peer; the 24 h day key versus the live privacy section 8 "within 6 hours" until S81-12; a known email can be held at most one cap window per attempt; register stays enumerable as at base).
- **Owner steps (names only; a dated ledger line per step):** none to merge. Flip preconditions for `ENABLE_AUTH_THROTTLE_V2` (each a dated ledger line): (1) `AUTH_THROTTLE_PEPPER` set on `web` (the owner generates the value; never in a transcript; never `DEVICE_KEY_PEPPER` reused); (2) owner item 8 (the Supabase dashboard sign-up and token limits) done; (3) the S81-12 window live (the throttle retention text "up to 24 hours"); (4) the owner's explicit yes, then a canary window reading the `[AUTH_THROTTLE] throttled` count per endpoint and the `skipped` count. Rollback: unset the variable (per call, immediate; keys expire within 24 h). The probe: (a) `ENABLE_HOP_PROBE_LOG` ON on `web`; (b) from one public IP, one plain GET /health and one GET /health with a forged `X-Forwarded-For` of a single TEST-NET entry; (c) the two `[HOP_PROBE]` lines (booleans only) land as a dated ledger line; (d) unset the flag; S81-24b picks the hop from that line.

### 8.2 The Feature Flags pointer clause (:341)

One clause naming the S81-24 block, after the S81-22 clause (merge order).

### 8.3 The DEFECT_LEDGER row (drafted for the orchestrator, names only)

`S81-24 | AUTH-THROTTLE-V2 phase 1 + MS4 echo | auth routes had only per-IP slowapi limits keyed on the shared edge peer (proxy-aware OFF) plus the 5-in-15-min W1-9b lockout; no per-email backoff, no register / reset / resend per-email interval or day cap, no per-account limit on PUT /auth/password and /auth/email; the Railway hop is unmeasured | ENABLE_AUTH_THROTTLE_V2, ENABLE_HOP_PROBE_LOG | tests/test_s81_s24_auth_throttle.py R01-R105, P70-P106 | precondition: AUTH_THROTTLE_PEPPER, owner item 8, S81-12 live, canary | #299 stays open (S81-24b)`.

## 9. Stated limits

- L1 Lua atomicity rests on Redis script semantics and the sha-frozen texts; the hermetic tests run a Python model of each script keyed on its exact text (no Lua runtime on the pinned venv, the S81-09 form). The adversaries read the Lua and the model side by side.
- L2 `now` is the web process wall clock passed as ARGV (the S81-04 EXPIREAT form); two replicas with skewed clocks see windows off by the skew; a clock step backwards lengthens a live window by the step.
- L3 Lua 5.1 formats numbers with %.14g: millisecond epochs stay exact below 1e14 (beyond year 5000).
- L4 Fail-open: during an Upstash outage V2 is inactive and the W1-9b lockout (Redis too, fail-open too) is also inactive, so only the in-memory per-process slowapi floor remains (as at base).
- L5 The per-IP floor keeps keying on the Railway edge peer (ENABLE_PROXY_AWARE_RATELIMIT OFF): one shared bucket per route stays as at base; per-IP / per-device keys are S81-24b.
- L6 The per-day counter lives 24 h, beyond the live privacy section 8 "expire within 6 hours" sentence (app/legal/privacy_policy.md:110) until S81-12 records "up to 24 hours"; hence flip precondition (3). Under flag OFF nothing is written.
- L7 Backoff abuse: anyone who knows an email can hold its login at most one cap window (60 s) per wrong attempt; a correct password after the window clears it; the reset and recovery routes stay open (R-S24-3). The W1-9b 15-minute lockout already allowed a stronger hold at base.
- L8 The keys are pseudonymous personal data (HMAC with a server pepper); a pepper rotation orphans the live keys (they expire within 24 h) and resets every throttle once.
- L9 The pre-arm: a first login attempt arms a 1 s window, so a double submit inside 1 s gets one 429 (build 3 renders its rate-limit copy).
- L10 Register is enumerable at base (400 "An account with this email already exists" vs 200) and stays so in both states; V2 only guarantees the throttle path itself is existence-blind (Q7).
- L11 With `ENABLE_UPSTASH_BOUNDED_TRANSPORT` OFF a stalled REST call parks an `auth-throttle` pool thread with no SDK timeout; the `wait_for` bound returns fail-open on time, and with four parked threads every later decision queues and fails open (the S81-04 pool behaviour).
- L12 The skipped WARNING is per decision, not rate-limited: an Upstash outage with the flag ON logs one line per gated request.
- L13 The echo line counts XFF entries only; a 200-entry forged header logs one line with the count; INFO volume = one line per probe-path GET while the flag is ON.
- L14 `auth_throttle.py` is not added to `.github/black-clean-paths.txt` (no .github edit in this unit).
- L15 The account routes' `Depends(get_current_user)` GoTrue verify runs before the V2 gate (FastAPI resolves dependencies before the body).

## 10. Out of scope

Per-IP and per-device keys; the tests/test_m13_02_proxy_aware_ratelimit.py:51-57 leftmost pin update; the request.state limiter key (#299); the secret-key GoTrue client and Sb-Forwarded-For; custom SMTP and its processors.json row; the retirement of the W1-9b lockout and of the eighteen string-presence tests (S81-24c); any client copy or file; any legal text (S81-12 HELD carries it); any migration; making register enumeration-safe; the Supabase dashboard limits (owner item 8); a throttled-login audit event; the spoof probe run itself (ops, names only).

## 11. Open questions for the orchestrator

- Q1 The login cap default: 60 s (R-S24-1) versus a longer ceiling (the W1-9b window is 900 s). The spec keeps 60.
- Q2 The pre-arm (2.4): it makes concurrent attempts on one email admit exactly one and costs a 1 s window on a first attempt (L9). The alternative (count-only, no pre-arm) lets a parallel burst through up to the per-IP floor. The spec picks the pre-arm.
- Q3 The per-account window: 5 per 600 s (R-S24-1) next to the 5/minute floor and the W1-9b lockout on the same routes. Kept.
- Q4 Interval keys live 6 h (R-S24-6) although they enforce 60 s; expiring them at the interval would hold less data. The spec follows the ruling.
- Q5 The echo-line seat: INSIDE `RequestIDMiddleware.dispatch` (measured: a new middleware class reddens three middleware-order pins, 1.7). Confirm.
- Q6 Build 3 and the 429 on login: ANSWERED by measurement (authErrorCopy.ts:13-15, :46-49 at 683f56c0: RATE_LIMITED -> common.errors.rateLimited); no client change.
- Q7 R-S24-9's premise does not hold for register: the base bodies differ by existence (1.2). V2 keeps them; a fix is a client-visible copy change for a later unit. Rule whether to record it as a DEFECT_LEDGER row.
- Q8 The brief's "sixteen" decorators = fifteen routes + the expired-logout budget (1.1); P80 pins the measured fifteen.
- Q9 Rate-limit the `skipped` WARNING (L12)?
- Q10 The version path is `/api/v1/app/version`, not `/app/version` (1.7).
- Q11 The register gate sits after the consent block (a consent-refused request arms nothing); every other gated route has it first. Confirm.

Not done in this spec: no RED file, no app edit, no mutation run, no comm-set run beyond 1.10, no CLAUDE.md edit, no DEFECT_LEDGER edit (the row is drafted in 8.3).
