# U13 - paid routes require a caller (ENABLE_COMPARE_AUTH_REQUIRED)

Session 71, MYEZ (formerly Qaren) Apple launch lane. Spec writer: read-and-measure only (no source edited).
Written 2026-10-03 (`date` 07:54 to 08:28 +03). Owner ruling (Ahmed, 2026-10-03): build this unit FIRST, then fund OpenAI.

Precedence: "Orchestrator rulings (BINDING)" at the end overrides "Review corrections (BINDING)", which overrides this body. Agents never edit this spec.

---

## 0. Base SHA (rev-parse proof)

```
$ git -C C:/Users/SynAckITPC/Documents/AI/sc-s71-u13 rev-parse HEAD
4bd5a09f1216ee3891cd4c1ea908ebbef284604e
$ git rev-parse origin/main
4bd5a09f1216ee3891cd4c1ea908ebbef284604e
$ git branch --show-current
feature/s71-u13-compare-auth-required
$ git log --oneline -3
4bd5a09f Merge pull request #277 from KGRddhs/docs/session-70-checkpoint
5c854d51 Merge remote-tracking branch 'origin/main' into docs/session-70-checkpoint
5ed4f459 Merge pull request #278 from KGRddhs/fix/s71-pyjwt-2.14
```

The local `main` ref in this clone is STALE (`git rev-parse main` = `94c097cd`). Use `origin/main` / `4bd5a09f`. Every `file:line` below is at `4bd5a09f`. Pinned stack measured in `.venv-qaren`: fastapi 0.141.1, starlette 1.6.0, slowapi 0.1.10, limits 5.8.0, uvicorn 0.52.4, pyjwt 2.15.1, supabase 2.31.0.

## 1. Why

`TRAFFIC_FINDING_2026-10-02.md` (sc-docs-70, session-71 state): 322 anonymous calls to `/api/v1/text/compare` in 27 active minutes from 155 rotating datacenter IPs (`python-httpx/0.28.1` 242, `python-requests/2.34.2` 80; those are exactly the clients `scripts/eval_runner.py` / `bias_matrix_probe.py` (httpx) and `run_validation_matrix.py` (requests) use), peak 51/min, zero 429. It cost nothing only because OpenAI is out of credits; funded, a modelled $0.023-0.031 per compare plus search credits, about $70-95/hour at the measured peak. The repo is public. The app is login-gated (section 2.5), so real users always hold a session.

---

## 2. Measured facts

Every command below was run at `4bd5a09f` with `PYTHONIOENCODING=utf-8` and the pinned venv. Scratch scripts (not committed) live in the spec writer's scratchpad `u13/`: `route_inventory.py`, `openapi_params.py`, `order_probe.py`, `envelope_probe.py`; each imports `tests._env_safety.neutralize_credentials` + `tests._netguard.install()` before `app.main` (conftest's order), so nothing reached the network.

### 2.1 Route inventory (walked with `tests/_route_introspection.walk_routes`, not `app.routes`)

Command: `python u13/route_inventory.py` (walk_routes + `route.dependant` recursion + `limiter._route_limits[module.func]`). Output head: `TOTAL_ROWS 88` (HEAD verbs dropped; 19 rows under `/api/v1/admin/*`, ALL with `admin_routes.verify_admin_key`; one `Mount /admin` static app behind HTTP Basic, `app/main.py:465-482`). `/docs`, `/redoc` and `/openapi.json` are registered only when `RAILWAY_ENVIRONMENT` is unset (`app/main.py:62-68,91-92`), i.e. absent in production.

Paid reach traced by reading the handler and its callee (grep of `guarded_llm_create|AsyncOpenAI|serper|brightdata|firecrawl|scrapedo|identify_products` over `app/services` and `app/api`).

**IN SCOPE - PAID and reachable by an anonymous caller today (10 method+path rows):**

| # | Method path | Handler (file:line) | Auth dep today | Limit | Paid leg (measured) |
|---|---|---|---|---|---|
| U1 | POST /api/v1/text/compare | `text_routes.py:447-449` text_compare | get_optional_user | 10/min | `service.compare_from_text` :501 (OpenAI parse + verdict, Serper/BD/Firecrawl/Scrape.do price cascade) |
| U2 | GET /api/v1/text/compare | `text_routes.py:642-656` text_compare_get | get_optional_user | 10/min | same service call |
| U3 | GET /api/v1/text/compare/stream | `text_routes.py:825-839` text_compare_stream | get_optional_user | 10/min | `get_comparison_service()` + streaming generator |
| U4 | POST /api/v1/url/compare | `url_routes.py:329-334` compare_urls | get_optional_user | 10/min | `compare_from_urls` :156 (AI extraction + `generate_comparison`) |
| U5 | GET /api/v1/url/compare | `url_routes.py:366-376` compare_urls_get | get_optional_user | 10/min | same |
| U6 | POST /api/v1/image/identify | `image_routes.py:151-158` identify_and_compare | get_optional_user | 10/min | `identify_products` :297 (vision) + a full compare |
| A1 | POST /api/v1/text/quick | `text_routes.py:1246-1248` quick_compare | none | 10/min | `service.compare_from_text` |
| A2 | GET /api/v1/text/prices/{product} | `text_routes.py:1346-1419` get_gcc_prices | none (X-Admin-Key in-handler ONLY when `ENABLE_PAID_ROUTE_METERING`, :1392-1393) | 20/min (url-keyed; shared scope under metering) | `get_regional_prices` :1412 (Serper + GPT + render tiers) |
| A3 | POST /api/v1/url/extract | `url_routes.py:271-273` extract_product | none | 10/min | `extract_from_url` :297 -> `extract_with_ai` (`url_extraction_service.py:383-454`, `guarded_llm_create`) when structured data is thin; plus an outbound fetch of the caller's URL |
| A4 | GET /api/v1/url/extract | `url_routes.py:308-313` extract_product_get | none | 10/min | same |

U-rows are the six routes the APP calls (section 2.5); A-rows have ZERO app callers (`grep` over `SmartCompareApp/src` returns nothing for `/text/quick`, `/url/extract`, `/text/prices`) and zero harness callers in `scripts/*.py`.

**PAID but admin-only already** (`Depends(verify_admin_key)`): GET /text/parse (`text_routes.py:1844-1847`, `parse_product_query` = LLM), GET /text/price-kpi (`:1422-1429`, parse + price cascade), DELETE /text/cache (`:1676-1680`, calls `parse_product_query` at :1735). All 19 `/api/v1/admin/*` routes are admin-only reads (stats/costs; no provider call found).

**PAID but already auth-required**: none. (`get_current_user` routes are all DB/Redis reads/writes.)

**FREE (stay anonymous, out of scope):**

| Method path | Auth dep | Why free (measured) |
|---|---|---|
| GET /api/v1/referrals/invite/{share_token} | `_require_referral_enabled` + get_optional_user, 20/min | `referral_service.resolve_invite`: Supabase reads; the module imports no LLM/search service (`referral_service.py:18-24`) |
| POST /api/v1/referrals/invite/{share_token}/quiz | same, 10/min | `run_invitee_quiz` (`referral_service.py:463-506`): one `comparisons` select by share_token, deterministic re-tag, "zero LLM cost" |
| GET/POST /api/v1/url/detect | none, 20/min | `detect_retailer` is a pure string match (`url_extraction_service.py:58`); the SSRF guard resolves DNS (free) |
| GET /api/v1/url/retailers | none, no limit | static dict |
| GET /api/v1/share/{token} | none, 30/min | `get_shared_comparison` DB read |
| GET /api/v1/home/trending | get_optional_user, 60/min | Redis/DB only (home_routes imports no paid service) |
| POST /api/v1/feedback, POST /api/v1/events | get_optional_user, 30/min, 60/min | `feedback_service` DB writes |
| GET /api/v1/legal/* (4 paths), GET /api/v1/app/version, GET /health, GET /, GET /favicon.ico | none | static/config |
| /auth/login, /register, /refresh, /password-recovery, /password-reset, /resend-verification, /social-login | none, 3-10/min | Supabase auth (not a provider in this unit's scope) |
| every other /auth, /comparisons, /home/savings, /home/smart-pick, /profile, /referrals/share, /referrals/status, POST /share/{comparison_id}, /usage/status | get_current_user | DB/Redis |

### 2.2 How auth works today

`app/api/auth_routes.py`:
- `get_current_user` (:319-347): no header -> 401 "Authorization header missing"; not `Bearer <x>` -> 401 "Invalid authorization header format. Use: Bearer <token>"; `verify_token` returns None -> 401 "Invalid or expired token".
- `get_optional_user` (:425-461): no header -> `None` in BOTH modes; malformed / rejected -> `_reject_or_anonymous` (:409-422): `None` with `ENABLE_STRICT_OPTIONAL_AUTH` off, `HTTPException(401, {"code":"AUTH_REQUIRED","error":...})` with it on; `except HTTPException: raise` then `except Exception` -> same decision.
- `strict_optional_auth_enabled()` (:350-381) reads `ENABLE_STRICT_OPTIONAL_AUTH` per call, truthy `true/1/yes/on`.
- `app/services/auth_service.py:543-576 verify_token`: revocation check (`_is_token_revoked_async`) then `client.auth.get_user(token)` via `run_db`; `except Exception: ... return None`. So EXPIRED JWT, BAD SIGNATURE, REVOKED (logout blacklist) and a SUPABASE OUTAGE all return `None` - indistinguishable to every caller.

| Case | get_optional_user (strict OFF / ON) | get_current_user |
|---|---|---|
| no header | None / None | 401 "Authorization header missing" |
| malformed header | None / 401 AUTH_REQUIRED | 401 "Invalid authorization header format..." |
| expired JWT | None / 401 | 401 "Invalid or expired token" |
| invalid signature | None / 401 | 401 |
| revoked (logout blacklist) | None / 401 | 401 |
| Supabase outage | None / 401 | 401 |

`ENABLE_STRICT_OPTIONAL_AUTH` recorded preconditions (`CLAUDE.md:430`, status `CLAUDE.md:638`): (1) `/auth/refresh` 503 on upstream failure - MET by #139; (2) the camera `/image/identify` raw fetch has no 401 -> refresh -> retry - OPEN (re-measured below, still true); (3) the M23 OTA on phones - recorded OPEN. The flag is dark in production per the record.

Envelopes, measured on the REAL app (`u13/envelope_probe.py`, TestClient, `verify_token` patched, no network):
```
usage/status no header: 401 {"success": false, "error": "Authorization header missing", "code": "AUTH_REQUIRED", "request_id": "7f83d0ba-..."} ct= application/json www-auth= None
strict ON rejected bearer POST compare: 401 {"success": false, "error": "Invalid or expired token", "code": "AUTH_REQUIRED", "request_id": "cae958b0-..."} svc_called= False
strict ON rejected bearer SSE: 401 application/json {"success":false,"error":"Invalid or expired token","code":"AUTH_REQUIRED","request_id":"6851eb7b-... svc_called= False
parse wrong admin key: 403 {"success": false, "error": "Invalid admin key", "code": "FORBIDDEN", "request_id": "7924d1ee-..."}
parse no admin key: 403 {"success": false, "error": "Invalid admin key", "code": "FORBIDDEN", "request_id": "3dbd0ebf-..."}
```
- `app/middleware/error_handler.py:23-34` maps 401 -> `AUTH_REQUIRED`, 403 -> `FORBIDDEN`; `http_exception_handler` (:113-143) unwraps a structured `{"code","error"}` detail and DROPS `exc.headers` (no `WWW-Authenticate` reaches the wire). `request_id` comes from `RequestIDMiddleware` (`app/middleware/request_id.py:10-15`, honours an inbound `X-Request-ID`).
- The SSE route answers an auth failure as a plain 401 JSON response BEFORE any stream byte (content-type `application/json`, the streaming service never called) because the raise happens during dependency resolution, before `StreamingResponse` exists.
- `admin_routes.verify_admin_key` (:34-59): `hmac.compare_digest` over `utf-8`/`surrogateescape` BYTES; empty `ADMIN_API_KEY` -> 403; absent header -> 403. W2-1 already calls it as a plain function on `request.headers.get("x-admin-key", "")` (`text_routes.py:1392-1393`).
- Precedent for a secret header with emptiness guards: `database_service._is_synthetic_request` (:729-744) - "ruling C2: `compare_digest(b'', b'')` is True, so the emptiness guards run BEFORE the compare".

### 2.3 Framework order on the pinned stack (decides where the check can sit)

- `fastapi/routing.py:425-466` (0.141.1): the request body is read and JSON-DECODED (a decode error raises `RequestValidationError` type `json_invalid` -> 422) and a multipart/form body is PARSED, BEFORE `solve_dependencies` (:481).
- `fastapi/dependencies/utils.py:619-708`: sub-dependencies are solved FIRST (a raising dependency propagates immediately), THEN path/query/header params, THEN body field validation.
- `slowapi/extension.py:713-736`: the `@limiter.limit` check runs INSIDE the decorated endpoint wrapper, i.e. after every dependency.
- Toy-app probe on the pinned libs (`u13/order_probe.py`; guard = a dependency that 401s when its `Depends(get_optional_user)` returns None):
```
versions fastapi 0.141.1 starlette 1.6.0 slowapi ?
anon + schema-invalid body: 401 {"detail":{"code":"AUTH_REQUIRED","error":"sign in"}}
anon + malformed json: 422 {"detail":[{"type":"json_invalid","loc":["body",1],"msg":"JSON decode error",...
anon + too-long query param: 401 {"detail":{"code":"AUTH_REQUIRED","error":"sign in"}}
anon + multipart: 401 {"detail":{"code":"AUTH_REQUIRED","error":"sign in"}}
authed ok: 200 {"ok":true}
calls after ONE authed request: {'optional': 1, 'guard': 1, 'endpoint': 1}
anon flood 0..3: 401 401 401 401
authed after anon flood (limit 2/min, 1 authed used before): 200 429
```
Read: a dependency guard precedes schema/query 422s and the usage gate; only JSON-decode and multipart parsing precede it; the FastAPI dependency cache resolves `get_optional_user` ONCE when both the guard and the route parameter depend on it; anonymous 401s raised in a dependency do NOT consume the slowapi bucket.
- `fastapi/routing.py:836` sets `scope["route"]` in `APIRoute.matches`, so a dependency can read the route TEMPLATE (`request.scope["route"].path`, e.g. `/api/v1/text/prices/{product}`) - never the concrete URL.

### 2.4 OpenAPI parameters of the in-scope routes at base (`u13/openapi_params.py`)

```
POST /api/v1/text/compare        params [header:authorization]                         body yes
GET  /api/v1/text/compare        params [header:authorization, query:lang, query:nocache, query:product_a, query:product_b, query:pros_cons, query:q, query:region, query:reviews, query:selected_category, query:specs]
GET  /api/v1/text/compare/stream params (same 11 as GET /text/compare)
POST /api/v1/text/quick          params []                                             body yes
GET  /api/v1/text/prices/{product} params [path:product, query:variant]
POST /api/v1/url/compare         params [header:authorization]                         body yes
GET  /api/v1/url/compare         params [header:authorization, query:region, query:selected_category, query:url1, query:url2]
POST /api/v1/url/extract         params []                                             body yes
GET  /api/v1/url/extract         params [query:url]
POST /api/v1/image/identify      params [header:authorization, query:nocache, query:region] body yes
```
A guard that takes `request: Request` (+ `Depends(get_optional_user)` only where `authorization` is already declared) adds nothing to these sets; a `Header(...)` parameter or a new `Depends(get_optional_user)` on an A-row would add `header:x-admin-key` / `header:authorization` (the W2-1 comment at `text_routes.py:1380-1388` records the issue-#55 trap of a declared parameter turning a missing header into a 422).

### 2.5 The client (SmartCompareApp at 4bd5a09f)

- Base URL `api.ts:20`. Axios request interceptor `api.ts:51-65`: attaches `Authorization: Bearer <token>` to EVERY axios request when `getToken()` returns one.
- Axios response interceptor `api.ts:204-245`: keys on `error.response.status === 401` ONLY (not on `code`), skips the auth-flow endpoints, sets `_retry`, calls the coalesced `getOrStartRefresh()` (:173-178) and re-drives the original request ONCE with the new token. `performRefresh` (:112-157): on `sessionInvalid` -> `clearSession()` + `emitSessionInvalid()` (back to Auth); a transient refresh failure (e.g. `/auth/refresh` 503 `REFRESH_UPSTREAM_UNAVAILABLE`) leaves the session and rejects the original error.
- Call sites of in-scope routes:
  - Text compare: `streamComparison` (`api.ts:582`). With `features.ENABLE_EXPO_FETCH_SSE_DEFAULT = false` (`src/config/features.ts:52`) it never streams: `runRestCompare` (`api.ts:613-664`) = axios `GET /api/v1/text/compare` -> interceptor refresh+retry on 401. With the stream flag on, the SSE `expo/fetch` (`api.ts:766-783`) attaches the bearer; a non-ok response throws (:784) and the catch (:863-879) falls back ONCE to `runRestCompare` (axios, refresh-capable) unless a terminal event already arrived.
  - `compareTextPair` (`api.ts:897-910`): axios POST /text/compare; no screen calls it (grep).
  - URL compare: `HomeScreen.tsx:556-568` axios `api.post('/api/v1/url/compare')` -> interceptor.
  - Camera: `identifyFromImages` (`api.ts:252-375`) is a RAW `fetch` (multipart). It attaches the bearer if present (:279-285) but has NO 401 branch: a 401 becomes an axios-shaped `Error('Server error 401')` (:345-354); `ResultsScreen.tsx:362-384` -> `isCameraEngineOutage` false for 401 (`failureClassification.ts:82-95`) -> `classifyLoadFailure` -> `'auth'` (`failureClassification.ts:55`) -> `setLoadError(kind === 'timeout' ? 'timeout' : 'generic')` = the GENERIC empty state. No refresh, no logout. Same as `ENABLE_STRICT_OPTIONAL_AUTH` precondition (2).
  - Invitee quiz / referral landing: `referralService.ts:131-163` (axios GET invite, POST quiz) - FREE routes, out of scope.
- Signed-out reachability: `App.tsx:365-458` renders the `Main` stack (Home, Results, ScanCamera, Paywall...) only when `isAuthenticated`; signed out shows only `Auth` plus the hoisted `ReferralLanding`, `InviteeQuiz` (`App.tsx:478-481`) and the legal screen. `InviteeQuizScreen.tsx:38-41` and `ReferralLandingScreen.tsx:38-42` import only `submitInviteeQuiz` / `resolveInvite`. No guest mode (grep `guest|skipLogin|continue without`: none). So NO client screen reaches an in-scope route signed out.
- Boot: `App.tsx:210-235` - `initializeAuth` resolves from the CACHED user and refreshes in the background, so a compare fired right after launch can carry an expired token; the axios path coalesces onto the same refresh (correct). No `AppState` foreground refresh exists (grep: only `onboardingDraft.ts:288`), so a phone resumed past the JWT lifetime keeps the stale token until some axios call 401s.
- Client copy: `AUTH_REQUIRED` has no case in `errorCopy.friendlyErrorKey` (`errorCopy.ts:70-...`), so it renders the generic copy; the backend's English `error` string is never rendered.

**What breaks or degrades with the flag ON, signed-in user whose token expired:**
- Text compare (REST, the shipped default), URL compare: 401 -> refresh -> retry -> works (metered + persisted once). Refresh fails definitively -> back to Auth (correct). Supabase auth outage -> refresh 503 -> generic error, NO logout.
- Text compare over SSE (only if `ENABLE_EXPO_FETCH_SSE` were on): 401 -> REST fallback -> refresh -> works.
- Camera: 401 -> generic error state, no refresh. Today (flag OFF, strict OFF) the same request runs an anonymous, unmetered compare and returns 200. This is a DEGRADE, recoverable only after another axios call refreshes the token. JS-only fix, deliverable by OTA (open question Q4).

### 2.6 Harness scripts that call production over HTTP

| Script | Routes | Client | Headers today | Needs with flag ON |
|---|---|---|---|---|
| `scripts/eval_runner.py` `run_query` (:994-1021) via `run_eval` (:1220-1245) | GET /text/compare (`nocache=true` unless `--read-cache`) | httpx.AsyncClient(base_url) | `X-Qaren-Synthetic` only when `SEARCH_LOG_SYNTHETIC_TOKEN` set (:1210-1217) | a credential |
| `scripts/eval_runner.py` price-KPI path (:1299-1338) | GET /text/price-kpi | httpx | `X-Admin-Key` from `ADMIN_API_KEY` when set (:1316-1321) | unchanged (already admin) |
| `scripts/cron_eval_nightly.py` (:70-85) | via `run_eval` | - | as run_eval | as run_eval; cron NOT registered (docstring :19-26) |
| `scripts/run_validation_matrix.py` `run_query` (:177-187) | GET /text/compare `nocache=true` | `requests.get(url, params, timeout)` | none | a credential |
| `scripts/bias_matrix_probe.py` `_run_one` (:108-125), client built in `_main_async` (:146, `httpx.AsyncClient()` at :156) | GET /text/compare `nocache=true` | `httpx.AsyncClient()` | none | a credential |
| `scripts/bundle_d_prod_smoke.py` `run_probes` (:155-171), probe 12 (:452-470) | GET /text/compare (cached) | httpx.Client | none on the compare probe; it REGISTERS + LOGS IN a throwaway user (:295-340) and keeps `derived_token` for other probes | send `derived_token` on probe 12 |
| `docs/investigations/2026-09-29-session-69-state/verify_after_credits.py` (:18-20, :37-39, :49) | GET /text/compare + GET /text/compare/stream (`nocache=true`) | httpx.Client(timeout=150) | none | a credential |
| `docs/investigations/2026-09-30-session-70-state/scripts/probe_providers.py` | calls OpenAI / Serper / Firecrawl / Scrape.do DIRECTLY, no app route | urllib | provider keys | UNAFFECTED |
| `tests/integration/bundle-e-smoke.sh` (:100-140) | probe 2 GET /text/compare (accepts `200,429,401,400`), probe 4 SSE | curl | optional `AUTH_ARG_1/2` bearer | SSE probe needs `AUTH_ARG`; not changed by this unit |
| CLAUDE.md:51-52 curl example; CLAUDE.md:197 Serper liveness probe `GET /api/v1/text/prices/<product>` | - | curl | none | the probe returns 401 with the flag ON (not a dead key) - doc row for the orchestrator |

`scripts/*.py` are standalone (stdlib + httpx/requests; no cross-imports; tests load them with `importlib.util.spec_from_file_location`, e.g. `tests/test_validation_matrix_runner.py:17-26`), except `cron_eval_nightly` which imports `scripts.eval_runner`.

### 2.7 Why the limiter did not 429 at 51/min (code measured; Railway topology NOT MEASURED)

- Key: `rate_limiter._rate_limit_key` (:52-59) = `get_remote_address(request)` = `request.client.host` (slowapi `util.py:20-27`) while `ENABLE_PROXY_AWARE_RATELIMIT` is unset (`CLAUDE.md:359`: unset in prod).
- `request.client.host`: uvicorn 0.52.4 runs `ProxyHeadersMiddleware` (`proxy_headers=True` default, `config.py:220,526-527`) with `trusted_hosts = FORWARDED_ALLOW_IPS or "127.0.0.1"` (`config.py:355-357`); the start command (`Procfile:1`, `railway.json` startCommand) passes no proxy flags. So `X-Forwarded-For` is honoured only if the TCP peer is 127.0.0.1; otherwise `client.host` = the TCP peer = a Railway edge address.
- Storage `memory://` (`rate_limiter.py:149-156`), per process, reset on every restart/deploy; one uvicorn process (no `--workers`).
- Bucket: `key_style="url"` default (`ENABLE_LIMITER_ENDPOINT_KEY` unset): `request["path"]` (`slowapi/extension.py:564-570`) - the query string is not part of it, so GET /text/compare is ONE bucket per client key.
- Decorators: 10/minute on U1-U6 and A1, A3, A4; 20/minute on A2 (`limits=` column in 2.1). slowapi `enabled` is read from `RATELIMIT_ENABLED` via its env config (`extension.py:235`).
- Mechanism: with ONE shared peer address, 51 requests in a minute must produce 41 429s. Zero 429s is consistent only with (a) the TCP peer address varying across those requests (several Railway edge addresses), or (b) more than one serving process/replica each with its own memory store, or (c) `FORWARDED_ALLOW_IPS` set on Railway so the 155 rotating client IPs became 155 keys, or (d) `RATELIMIT_ENABLED` set false. Which holds is NOT MEASURED (orchestrator can check variable NAMES and the replica count; no value is needed).
- This unit does NOT fix the limiter (stated limit L2; follow-up named there). With the flag ON, anonymous refusals never reach the limiter (2.3), so the limiter gap no longer matters for anonymous traffic.

### 2.8 Existing tests that pin anonymous access, and a collision

53 files under `tests/` reference an in-scope route path or handler name (`grep -rlE` over the ten paths and `text_compare|text_compare_get|text_compare_stream|quick_compare|compare_urls|extract_product|identify_and_compare|get_gcc_prices`): 49 `test_*.py` plus 4 helpers/fixtures. 48 of the 49 are inside the G4 comm set; the 49th, `tests/test_noon_adapter.py`, is a false positive (`_extract_product_jsonld`). The ones that matter for this unit:
- `tests/test_security_regression.py::TestQueryMaxLength` (:266-281): anonymous GET /text/compare q=501 chars -> 422; normal length != 422. Flag OFF unchanged. Flag ON: the guard precedes query validation, so anonymous -> 401 (pinned as RED T18b).
- `TestReferralQuizNoAuthAndNoPII` (:953-982): POST quiz anonymously must not be 401/403. Out of scope -> stays green in both states (pinned again flag ON as T22).
- `TestBundleBContentSafety` (:1289, :1327, :1496): anonymous POST /text/compare and /image/identify. Flag OFF unchanged.
- `TestBundleBRateLimitSmoke` (:1515-1524): regex `@limiter\.limit\([^)]+\)\s*\n\s*async def text_compare\(` - the guard must NOT be inserted between the limiter decorator and the `def`; attaching it via the ROUTER decorator's `dependencies=[...]` keeps the regex true.
- `TestImageEndpointSanitization` (:225-244) and `TestAuthSecurityBaseline` (:419-443) read `image_routes.py` / `auth_routes.py` with `read_text()` (locale encoding on Windows): additions to those files must be ASCII.
- `tests/test_b2_strict_optional_auth.py`: strict flag matrix incl. "absent header still serves an anonymous compare" with strict ON (:357). U13 OFF keeps it green.
- `tests/test_m13_03_paid_work_gating.py`, `tests/test_paid_route_metering.py`, `tests/test_retro_w2_1.py`: anonymous /text/quick, /image/identify, /url/compare, /text/prices behaviour under their own flags; flag OFF unchanged.
- `tests/test_w4_13_flag_off_ledger.py` + `tests/fixtures/w4_13_flag_off_ledger.json` (45 committed flag-OFF records, anonymous AND authed, over U1-U6 and A1, plus `eval_headers`) - the byte-identity ledger this unit must keep green.
- **COLLISION (derived from code, not executed):** `tests/test_w4_13_measurement_truth.py:1816` pins `HEAD_EVAL_HEADERS = {"accept","accept-encoding","connection","host","user-agent"}` and `test_eval_runner_no_header_without_token` (:1839-1845) asserts `run_eval`'s request header set equals it exactly; the ledger's last record `eval_headers` stores the same five headers. Nine test files set `ADMIN_API_KEY` at MODULE import (`os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")`: test_b2_strict_optional_auth.py:31, test_explicit_pair_integration_mocked.py:46, test_http_400_cap_cut_mapping.py:34, test_partial_specs_stash_on_price_timeout.py:30, test_password_reset_deep_link.py:66, test_text_error_envelope_no_raw_exception.py:44, test_text_routes_error_mapping.py:16, test_timeout_partial_integration.py:34, test_w49_extraction_catch_redaction.py:50; plus `test_retro_w1_1.py:392` assigns it at module level; `test_analytics.py:243,295` reassigns it INSIDE tests without restoring), and conftest never re-strips per test. pytest imports every collected module before running any test, so in CI's single process `ADMIN_API_KEY` is non-empty for practically every test. Therefore a harness that sends `X-Admin-Key` "whenever `ADMIN_API_KEY` is set" turns both W4-13 pins RED in CI while passing in a single-file run. The harness credential MUST be an explicit opt-in (D9).

### 2.9 Metering facts that shape the design

- Tiers (`usage_service.py:138-149`): free = 3 lifetime-free, 3/day, 10/month; premium = 10/day, 70/month. A signed-in test account therefore cannot run a 30-50-query eval (it hits 429 `USAGE_LIMIT` after 3 or 10 per day).
- Users are metered on U1-U3 always (`consume_comparison_credit`, `text_routes.py:487-497` for U1, same gate in U2/U3); on U4-U6 ONLY under `ENABLE_PAID_ROUTE_METERING` (`url_routes.py:54-84`, `image_routes.py:279-292`); on A1-A4 NEVER (no user dependency at all).
- So "any signed-in user" on A1-A4 would be unmetered paid work for any farmed account. A1-A4 have no app caller. This is why the design makes A1-A4 admin-only under the flag (D2).

### 2.10 Baseline runs at base (bounded runner)

Pin set, one process, CI order:
```
pyt.py --bound 1200 --tag u13-base-pins -- tests/test_b2_strict_optional_auth.py tests/test_bias_matrix_probe.py tests/test_eval_runner.py tests/test_m13_03_paid_work_gating.py tests/test_paid_route_metering.py tests/test_route_introspection.py tests/test_security_regression.py tests/test_w4_13_flag_off_ledger.py tests/test_w4_13_measurement_truth.py -q
469 passed, 11 warnings in 16.95s
[netguard] blocked 14 attempt(s) from 8 node(s)   (all baseline nodes, e.g. TestQueryMaxLength::test_normal_length_query_accepted -> api.openai.com)
[pyt] tag=u13-base-pins start=2026-10-03 08:07:20 end=2026-10-03 08:07:38 elapsed=18s bound=1200s status=OK rc=0
```
Module-reference comm set at base (131 files; build command in G4), run in the worktree while HEAD == base, chunks of 25:
```
[pyt] tag=u13-comm-base-00 elapsed=17s status=FAIL rc=1   5 failed, 710 passed, 3 skipped, 31 deselected
[pyt] tag=u13-comm-base-01 elapsed=28s status=OK rc=0     650 passed, 1 skipped, 17 deselected
[pyt] tag=u13-comm-base-02 elapsed=33s status=OK rc=0     441 passed, 19 deselected
[pyt] tag=u13-comm-base-03 elapsed=100s status=OK rc=0    503 passed, 1 skipped, 1 deselected
[pyt] tag=u13-comm-base-04 elapsed=64s status=OK rc=0     791 passed, 7 deselected
[pyt] tag=u13-comm-base-05 elapsed=13s status=OK rc=0     395 passed
```
Base FAILED ids (all five are in `tests/.pre_impl_failures.txt:79-89`, the known 11): `test_auth_interceptor.py::test_sign_in_with_social_exception`, `::test_social_login_user_insert_fails_gracefully`, `test_camera_vision.py::TestIdentifyProductsMocked::{test_malformed_response_returns_error, test_successful_identification, test_empty_product_fields_normalized}`. Base ERROR ids: none. Logs: scratchpad `u13/comm_base_0{0..5}.log`.

---

## 3. Design (each choice with its measured alternative)

**D1 - Enforcement point: a FastAPI dependency attached with the ROUTER decorator's `dependencies=[Depends(...)]`.**
- Runs before the usage gate, the preferences fetch, the anon-fingerprint gate, the DNS/SSRF resolve, `log_search` and every provider leg (all live in handler bodies), and before schema/query 422s (2.3). It does NOT precede JSON-decode 422 or multipart parsing: fastapi 0.141.1 does those before `solve_dependencies` (`routing.py:425-481`); no paid work, metering or `search_logs` write happens there (stated limit L5).
- Handler signatures and bodies stay byte-identical; `user` keeps coming from the existing `Depends(get_optional_user)` (cached, one `verify_token`).
- Anonymous refusals do not consume the slowapi bucket (measured, 2.3), so an anonymous flood can no longer 429 real users who share a limiter key.
- Rejected alternatives: (a) per-route inline checks inside the handler (the W2-1 `/text/prices` pattern, `text_routes.py:1376-1393`) - run after body validation and after the limiter (anonymous floods would burn the shared bucket) and duplicate the check 10 times; (b) an ASGI middleware - needs its own method+path table copied from the routers, cannot share the dependency cache (a second `verify_token` = a second Redis GET + Supabase `/user` round trip per compare), and sits outside FastAPI's exception handlers (hand-built envelope); (c) replacing `Depends(get_optional_user)` in the handler parameter - works, but edits 6 handler signatures for no gain.

**D2 - Two guard variants, one module.**
- `require_paid_route_user` on U1-U6 (the app's routes): `async def require_paid_route_user(request: Request, user: Optional[Dict] = Depends(get_optional_user)) -> Optional[Dict]`. Flag ON: a truthy `user` passes; else a valid admin credential passes; else 401. Because the six routes already declare `Depends(get_optional_user)`, the dependency cache keeps it to ONE `verify_token` and the OpenAPI parameter sets do not change.
- `require_paid_route_admin` on A1-A4 (no app caller): `async def require_paid_route_admin(request: Request) -> None`. Flag ON: a valid admin credential passes; no/empty `X-Admin-Key` -> 401; a wrong one -> 403. It never resolves a bearer (no Supabase call; a bearer-only caller gets 401). Measured reasons: A1-A4 are unmetered for users (2.9), have zero app and zero harness callers, and A2 is already admin-only under `ENABLE_PAID_ROUTE_METERING`. Giving A1-A4 `Depends(get_optional_user)` instead would (i) add `header:authorization` to their OpenAPI params, (ii) make flag-OFF requests that carry a bearer call `verify_token` (a Supabase round trip that does not happen today) and 401 under `ENABLE_STRICT_OPTIONAL_AUTH` - NOT byte-identical. Alternative (signed-in users allowed on A1-A4) is open question Q3.
- Placement: both guards, the flag reader and the refusal helper live in `app/api/text_routes.py`, which already imports `get_optional_user` (:21) and `verify_admin_key` (:22) and is the single-definition hub that `url_routes` (:30-41) and `image_routes` (:44-50) already import from (`paid_route_metering_enabled` idiom). `auth_routes.py`, `admin_routes.py`, `error_handler.py`, `rate_limiter.py`, `main.py` are NOT edited (no new import edge, no source-scan risk on `auth_routes.py`).

**D3 - The admin credential (harness path).** Recommended over a signed-in test account (Q1).
- Header `X-Admin-Key` (already in CORS `allow_headers`, `main.py:118`), compared by calling `verify_admin_key(header)` verbatim: bytes, `surrogateescape`, `hmac.compare_digest`, empty `ADMIN_API_KEY` -> 403.
- Read off `request.headers` (never a declared `Header(...)` parameter - 2.4). An ABSENT or EMPTY header is "no admin attempt" (guard before any compare, the `_is_synthetic_request` C2 rule); a PRESENT non-empty header that fails -> 403 `FORBIDDEN` "Invalid admin key" (the existing envelope), never a fall-through to anonymous. A present header with `ADMIN_API_KEY` unset -> 403.
- On U1-U6 the admin header is consulted ONLY when `user` is falsy (the app never sends it; a valid bearer wins without touching the key).
- An admin pass runs the route exactly as an anonymous caller does today (no user -> no usage consumption, no history row).
- Never logged, never echoed.
- Why not a test account (measured): free tier 3/day and premium 10/day (2.9) cannot carry a 30-50-query eval; JWTs expire (the scripts would need login + refresh); each run writes history/cohort rows; the account password becomes a second secret to distribute. Why the admin key is acceptable: the same key already unlocks paid `/text/parse`, `/text/price-kpi`, `DELETE /text/cache` and (under metering) `/text/prices`, so its blast radius grows only by the compare routes.

**D4 - The 401 detail.** `HTTPException(401, detail={"code": "AUTH_REQUIRED", "error": "Sign in to continue."})` - the `_reject_or_anonymous` shape; on the wire `{"success": false, "error": "Sign in to continue.", "code": "AUTH_REQUIRED", "request_id": "<id>"}`. The client keys on STATUS 401 only (`api.ts:222`, `failureClassification.ts:55`); `code` is `AUTH_REQUIRED` either way (`STATUS_CODE_MAP`); the English string is never rendered by the app (2.5). ASCII only.

**D5 - Expired / invalid bearer.** Flag ON never downgrades silently: strict OFF -> `get_optional_user` returns None -> the guard raises the D4 401; strict ON -> `get_optional_user` itself raises its 401 (`"Invalid or expired token"`) before the guard body runs. Both are 401 `AUTH_REQUIRED`, which the axios interceptor refreshes and retries once. U13 does not require, flip or change `ENABLE_STRICT_OPTIONAL_AUTH`; for U1-U6 it subsumes it.

**D6 - Flag reader.** `compare_auth_required_enabled()` in `text_routes.py`: `os.getenv("ENABLE_COMPARE_AUTH_REQUIRED", "").strip().lower() in ("1", "true", "yes", "on")`, read per call, never cached, default OFF. Flag OFF: `require_paid_route_user` returns `user` and `require_paid_route_admin` returns None immediately - no header read, no log, no call.

**D7 - Logging.** Exactly one `logger.info` (the `text_routes` logger) per refusal: `"[paid-auth] refused route=%s reason=%s"` with `route` = `"<METHOD> <route template>"` from `request.scope["route"].path` (e.g. `GET /api/v1/text/prices/{product}` - never the concrete path, which carries the product string) and `reason` in `NO_CREDENTIAL` (no Authorization and no admin header), `BEARER_REJECTED` (an Authorization header was present but resolved to no user; only reachable with strict OFF), `ADMIN_KEY_INVALID` (present, wrong), `ADMIN_REQUIRED` (A-routes: an Authorization header but no admin header). One INFO per admin pass: `"[paid-auth] admin credential accepted route=%s"`. NEVER the token, any header value, the client IP/host, the query/body or the concrete path. (INFO does not create Sentry events; `sentry_service` configures no log forwarding.)

**D8 - Out of scope, stays anonymous:** the referral invitee routes (DB-only, 2.1), `/url/detect` (string match + DNS), `/url/retailers` (static), `/share/{token}`, `/home/trending`, `/feedback`, `/events`, `/legal/*`, `/app/version`, `/health`. Q2 asks the orchestrator to confirm.

**D9 - Harness credential is OPT-IN.** Each script sends `X-Admin-Key: <ADMIN_API_KEY>` only when `HARNESS_SEND_ADMIN_KEY` is truthy (`1/true/yes/on`) AND `ADMIN_API_KEY` is non-empty; otherwise its requests are byte-identical to today. Measured reason: 2.8 collision. `bundle_d_prod_smoke` instead sends `Authorization: Bearer <derived_token>` on probe 12 whenever its own login probe produced a token (the real user path, as the app does), falling back to the opt-in admin header. Each standalone script carries its own 6-line `_harness_auth_headers()` (they share no imports); `eval_runner` exposes `harness_auth_headers()` used by `run_eval` (and so by `cron_eval_nightly`). The operator runs them as `railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 python <script>` so the key is injected, never typed or printed.

---

## 4. Flags

| Flag | Default | Read | This unit |
|---|---|---|---|
| `ENABLE_COMPARE_AUTH_REQUIRED` (NEW) | OFF | per call, `text_routes.compare_auth_required_enabled()` | ON: U1-U6 need a signed-in user or the admin credential; A1-A4 need the admin credential; anonymous -> 401 `AUTH_REQUIRED` before any work |
| `ENABLE_STRICT_OPTIONAL_AUTH` | OFF (dark) | per call | not changed; composes (D5) |
| `ENABLE_PAID_ROUTE_METERING` | OFF | per call | not changed; A2's in-handler admin check stays; users on U4-U6 stay unmetered until it is ON (Q5) |
| `ENABLE_ANON_USAGE_GATE` | OFF | per call | not changed; with U13 ON no anonymous caller reaches it on A1/U6 |
| `ENABLE_PROXY_AWARE_RATELIMIT`, `ENABLE_DEFAULT_RATE_LIMITS`, `ENABLE_LIMITER_ENDPOINT_KEY` | OFF | - | not changed (L2) |
| `HARNESS_SEND_ADMIN_KEY` (script env, not a server flag) | unset | per call in each script | opt-in for D9 |

CLAUDE.md flag row, curl examples and the Serper-probe note are written by the ORCHESTRATOR at merge (R14). Nothing flips without Ahmed.

---

## 5. Requirements

- **R1** `app/api/text_routes.py`: add `compare_auth_required_enabled()` (D6) next to the other readers (near :54-212).
- **R2** `app/api/text_routes.py`: add the module constants `_PAID_AUTH_DETAIL = {"code": "AUTH_REQUIRED", "error": "Sign in to continue."}`, the reason strings of D7, a `_paid_route_label(request) -> str` (method + `scope["route"].path`, `"?"` fallback), and `_refuse_paid_route(request, reason)` that logs (D7) and raises `HTTPException(401, detail=dict(_PAID_AUTH_DETAIL))`.
- **R3** `app/api/text_routes.py`: `require_paid_route_user(request, user=Depends(get_optional_user))` per D2/D3/D5/D6/D7.
- **R4** `app/api/text_routes.py`: `require_paid_route_admin(request)` per D2/D3/D6/D7.
- **R5** Attach `dependencies=[Depends(require_paid_route_user)]` to the ROUTER decorators of U1 `text_routes.py:447`, U2 `:642`, U3 `:825`, U4 `url_routes.py:329`, U5 `:366`, U6 `image_routes.py:151`. Nothing between `@limiter.limit(...)` and `async def`; handler signatures and bodies unchanged.
- **R6** Attach `dependencies=[Depends(require_paid_route_admin)]` to A1 `text_routes.py:1246`, A2 `:1346`, A3 `url_routes.py:271`, A4 `:308`. A2's in-handler W2-1 check (:1392-1393) stays.
- **R7** `url_routes.py` and `image_routes.py` import the guards from `app.api.text_routes` (no second definition, no re-parse of the env).
- **R8** Flag OFF is byte-identical per route for anonymous, valid-bearer and rejected-bearer callers (status, body, side-effect calls, `verify_token` call count); OpenAPI parameter sets equal 2.4; the W4-13 ledger stays green.
- **R9** Do NOT edit `auth_routes.py`, `admin_routes.py`, `error_handler.py`, `rate_limiter.py`, `main.py`, anything under `backend/app/` or `SmartCompareApp/`, `requirements*.txt`, `tests/.pre_impl_failures.txt`, any existing test or fixture.
- **R10** Harness (D9), each edit minimal and opt-in:
  - `scripts/eval_runner.py`: `harness_auth_headers() -> Dict[str, str]`; `run_eval` merges `{**synthetic_traffic_headers(), **harness_auth_headers()}` and sets `client_kwargs["headers"]` only when the merge is non-empty (today's `if _synthetic:` shape). The price-KPI path (:1316-1321) is unchanged.
  - `scripts/run_validation_matrix.py` `run_query`: pass `headers=` to `requests.get` ONLY when the helper returns a non-empty dict (else the call's kwargs are exactly today's).
  - `scripts/bias_matrix_probe.py` `_main_async`: `httpx.AsyncClient(headers=h) if h else httpx.AsyncClient()`.
  - `scripts/bundle_d_prod_smoke.py` probe 12: `headers={"Authorization": f"Bearer {derived_token}"}` when `derived_token` is not None, else the opt-in admin header when present, else none. Probe order is unchanged (probe 6 login precedes probe 12).
  - `docs/investigations/2026-09-29-session-69-state/verify_after_credits.py` `main`: `httpx.Client(timeout=150, headers=h)` when the inline helper returns non-empty (Q7).
  - `scripts/cron_eval_nightly.py`: no edit (inherits via `run_eval`).
  - No script prints or logs the key or the opt-in decision's value.
- **R11** Tests: `tests/test_s71_u13_compare_auth_required.py` (routes) and `tests/test_s71_u13_harness_auth.py` (scripts) - section 6. Module docstrings name this spec and the T/H ids.
- **R12** ASCII-only additions in every touched file (2.8: locale-encoded `read_text()` scans).
- **R13** CRLF working copies (`core.autocrlf=true`, `i/lf w/crlf` measured with `git ls-files --eol` for all 8 touched files): use the Edit tool; a whole-file diff in `git diff --stat` is a defect.
- **R14** (orchestrator, at merge) CLAUDE.md: the flag row (effect, activation order, rollback = unset); the curl example at :51-52 gains `-H "X-Admin-Key: ..."` guidance (never a literal key); the Serper liveness note at :197 ("with `ENABLE_COMPARE_AUTH_REQUIRED` ON an unauthenticated `/text/prices` probe returns 401, which is NOT a dead key"); the PR body carries a Flag row and the Activation gate of section 9.

---

## 6. RED table

Conventions for both files: hermetic (patch `auth_routes.verify_token` with an `AsyncMock` returning a user for the sentinel `u13.valid.jwt` and None for `u13.expired.jwt`; patch every provider/usage/DB/DNS leg at the ROUTE module's import name: `text_routes.get_comparison_service`, `get_regional_prices`, `consume_comparison_credit`, `refund_comparison_credit`, `record_lifetime_comparison`, `get_user_preferences`, `check_anon_usage_allowed`, `log_search`, `fire_and_forget`, `save_comparison_and_track_cohort`; `url_routes._validate_url_offloop_or_sync`, `compare_from_urls`, `extract_from_url`, `consume_comparison_credit`, `log_search`, `fire_and_forget`; `image_routes.identify_products`, `check_anon_usage_allowed`, `consume_comparison_credit`, `log_search`, `fire_and_forget`); `monkeypatch.setenv/delenv` for every flag a test depends on (`ENABLE_COMPARE_AUTH_REQUIRED`, `ENABLE_STRICT_OPTIONAL_AUTH`, `ENABLE_PAID_ROUTE_METERING`, `ENABLE_ANON_USAGE_GATE`, `ADMIN_API_KEY`, `HARNESS_SEND_ADMIN_KEY`, `SEARCH_LOG_SYNTHETIC_TOKEN`) - `ADMIN_API_KEY` is set by other modules at collection (2.8), so a test needing it UNSET must `delenv`; an autouse `limiter.reset()` fixture (the `test_b2_strict_optional_auth.py:62-73` pattern); a fixed `X-Request-ID` header where a body is compared; names the unit creates are imported INSIDE test bodies (or matched by `__name__` string) so the file collects at base; pytest-asyncio strict (`@pytest.mark.asyncio`); sentinels never `sk-`-shaped (admin key sentinel `u13-admin-sentinel-key`); no `[netguard]` line may name a new node. Route lists: USER = U1-U6, ADMIN = A1-A4, ALL = 10.

### File 1: `tests/test_s71_u13_compare_auth_required.py`

| ID | Name | Assertion | Why RED at base | RED / PIN nodes |
|---|---|---|---|---|
| T01 | flag default off | unset, "", "false", "0", "no", "off", "garbage" -> `compare_auth_required_enabled()` is False | reader absent (ImportError inside body) | 7 RED |
| T02 | flag truthy set | "1", "true", "yes", "on", " TRUE ", "On" -> True | absent | 6 RED |
| T03 | read per call | set -> True, delenv -> False in one test | absent | 1 RED |
| T04 | inventory: guards declared | for each of ALL (walk_routes + find_route), the dependant tree contains exactly one call named `require_paid_route_user` (USER) / `require_paid_route_admin` (ADMIN) | names absent | 10 RED |
| T05 | inventory: out of scope untouched | `assert_route_table_visible`; no route outside ALL (incl. referral invite GET/quiz POST, /url/detect x2, /url/retailers, /share/{token} GET, /home/*, /feedback, /events, /legal/*, /app/version, /health, /text/parse, /text/price-kpi, DELETE /text/cache, /api/v1/admin/*) has a dependency named `require_paid_route_*` | string match, green at base | 1 PIN |
| T06 | anonymous refused (flag ON) | per ALL: 401; body keys exactly {success, error, code, request_id}; success False; code "AUTH_REQUIRED"; ZERO calls to every patched provider/usage/prefs/anon-gate/log_search/fire_and_forget/DNS stub (A1 and U6 run with `ENABLE_ANON_USAGE_GATE=true` + a valid `X-Device-Fingerprint` so the anon gate is armed) | base serves the request (stubs called) | 10 RED |
| T07 | SSE refusal shape | anon flag ON GET /text/compare/stream: 401, content-type application/json, body parses as the envelope, no `event:` / `data:` bytes, `get_comparison_service` not called | base streams | 1 RED |
| T08 | valid bearer passes (USER) | flag ON + `Bearer u13.valid.jwt`: status not 401/403; the route's provider stub called once; `verify_token` awaited EXACTLY once | green at base (no guard) | 6 PIN |
| T09 | bearer is not enough on ADMIN routes | flag ON + valid bearer, no admin header, per ADMIN: 401 AUTH_REQUIRED; `verify_token` NOT awaited; zero provider calls | base serves | 4 RED |
| T10 | admin credential passes | flag ON, `ADMIN_API_KEY=u13-admin-sentinel-key`, matching `X-Admin-Key`, no bearer, per ALL: not 401/403, provider stub called once, `verify_token` not awaited | green at base (anon passes) | 10 PIN |
| T11 | wrong admin key | flag ON, key set, `X-Admin-Key: wrong`, per ALL: 403, code "FORBIDDEN", zero provider calls | base serves | 10 RED |
| T12 | admin header but ADMIN_API_KEY unset | `delenv ADMIN_API_KEY`; POST /text/compare with `X-Admin-Key: anything`: 403, zero provider calls | base serves | 1 RED |
| T13 | empty admin header = absent | `X-Admin-Key: ""`, no bearer, POST /text/compare: 401 AUTH_REQUIRED (not 403) | base serves | 1 RED |
| T14 | non-ASCII admin header | `X-Admin-Key` carrying byte 0xE9, POST /text/compare: 403, never 500. Pass the value as BYTES (`b"\xe9u13"`): measured, httpx raises `UnicodeEncodeError` on a non-ASCII `str` header value and sends bytes as-is | base serves | 1 RED |
| T15 | rejected bearer, strict OFF | flag ON, `Bearer u13.expired.jwt`, per USER: 401 AUTH_REQUIRED; zero provider/usage calls | base downgrades to anonymous 200 | 6 RED |
| T16 | rejected bearer, strict ON | flag ON + `ENABLE_STRICT_OPTIONAL_AUTH=true`, per USER: 401 AUTH_REQUIRED | green at base (strict already 401s) | 6 PIN |
| T17 | flag OFF byte-identity | flag unset, strict unset, metering unset; per ALL x {anonymous, valid bearer, rejected bearer}: status + JSON body (fixed `X-Request-ID`; for U3 the joined SSE chunks) equal literals RECORDED AT BASE (the RED author runs these scenarios in a detached scratch worktree at `4bd5a09f` and hardcodes the results), stub call counts equal base, `verify_token` count equal base (USER: 1 per bearer request; ADMIN: 0) | literals from base | 30 PIN |
| T18 | ordering | a) flag ON anon POST /text/compare body `{}` -> 401 (base 422); b) flag ON anon GET /text/compare q of 501 chars -> 401 (base 422); c) flag ON anon POST /text/compare malformed JSON -> 422 `json_invalid`, zero stub calls (framework order, L5) | a, b: base 422 | 2 RED + 1 PIN |
| T19 | refusals do not burn the bucket | `limiter.reset()`; flag ON; 12 anonymous POST /text/compare (all 401) then one valid-bearer POST -> not 429, provider stub called | base: anon calls consume 10/min, the bearer call 429s | 1 RED |
| T20 | refusal log line | caplog INFO on the text_routes logger, flag ON: anon -> exactly one record containing `POST /api/v1/text/compare` and `NO_CREDENTIAL`; rejected bearer -> `BEARER_REJECTED`; wrong admin key -> `ADMIN_KEY_INVALID`; valid admin -> one `admin credential accepted` record; GET /text/prices/IPHONE-U13-SENTINEL -> template `/api/v1/text/prices/{product}` (5 scenarios) | no such records | 5 RED |
| T21 | nothing secret logged | across T20's scenarios, at DEBUG on all loggers: at least one `[paid-auth]` record exists (non-vacuity) and NO record contains the bearer sentinel, the admin sentinel, the query sentinel, `IPHONE-U13-SENTINEL` or `testclient` | non-vacuity fails | 1 RED |
| T22 | out-of-scope stays anonymous (flag ON) | invitee quiz POST (referral service stubbed) not 401/403; GET /url/detect (validator stubbed) not 401 | green at base | 2 PIN |
| T23 | OpenAPI unchanged | `app.openapi_schema = None; app.openapi()` (restore after); per ALL the sorted `in:name` params and requestBody presence equal 2.4 | green at base | 10 PIN |
| T24 | prices composition | flag ON + `ENABLE_PAID_ROUTE_METERING=true`: anon -> 401 (not 403); valid admin -> 200 with `get_regional_prices` called once | base: anon 403 | 1 RED |

File 1 totals: **68 RED, 66 PIN** (134 nodes).

### File 2: `tests/test_s71_u13_harness_auth.py`

| ID | Name | Assertion | Why RED at base | RED / PIN |
|---|---|---|---|---|
| H01 | run_eval sends the key when opted in | `HARNESS_SEND_ADMIN_KEY=1`, `ADMIN_API_KEY=u13-admin-sentinel-key`, MockTransport (the `_eval_headers` pattern, `test_w4_13_measurement_truth.py:1819-1826`): every request carries `x-admin-key` == sentinel | not sent | 1 RED |
| H02 | run_eval byte-identical without opt-in | `ADMIN_API_KEY` SET, opt-in unset, token unset: header set == {"accept","accept-encoding","connection","host","user-agent"} | green at base | 1 PIN |
| H03 | opt-in without a key | opt-in set, `ADMIN_API_KEY` deleted: no `x-admin-key` | green | 1 PIN |
| H04 | both harness headers | opt-in + key + `SEARCH_LOG_SYNTHETIC_TOKEN`: both headers present | admin header missing | 1 RED |
| H05 | validation matrix sends when opted in | monkeypatch the loaded module's `requests.get` to capture kwargs; `run_query(...)` -> `headers == {"X-Admin-Key": sentinel}` | not sent | 1 RED |
| H06 | validation matrix unchanged otherwise | key set, opt-in unset: captured kwargs have NO `headers` key (exactly today's call) | green | 1 PIN |
| H07 | each script's helper | per script in {eval_runner, run_validation_matrix, bias_matrix_probe, bundle_d_prod_smoke, verify_after_credits} loaded by path: helper returns `{"X-Admin-Key": sentinel}` when opted in, `{}` when not (2 states each) | helper absent (both states fail at base) | 10 RED |
| H08 | bias probe client headers | monkeypatch the module's `httpx.AsyncClient` with a recorder; `_main_async` on a 1-query matrix fixture (MockTransport): client constructed with the admin header when opted in, with no `headers` kwarg otherwise | not sent | 1 RED + 1 PIN |
| H09 | smoke compare probe carries the user token | module `httpx.Client` wrapped to inject a MockTransport whose `/auth/login` returns `{"success":true,"session":{"access_token":"u13.smoke.jwt"}}`: the `/api/v1/text/compare` request carries `Authorization: Bearer u13.smoke.jwt`; with login failing and the opt-in set it carries the admin header instead | anonymous at base | 2 RED |
| H10 | verify_after_credits client | module loaded by path; `httpx.Client` recorder: built with the admin header when opted in, without `headers` otherwise | not sent | 1 RED + 1 PIN |

File 2 totals: **17 RED, 5 PIN** (22 nodes). Grand total: **85 RED, 71 PIN** (156 nodes). The RED agent reports actual counts; a difference is explained, not hidden.

### Mutation spot-checks (green agent; each restored from a Python byte copy, sha256 compared)

| Mutant | Must redden |
|---|---|
| X1 `require_paid_route_user` returns None instead of raising when no user/admin | T06 (USER), T15 |
| X2 flag read once at import into a module constant | T03 |
| X3 the user guard resolves the user with a direct `await get_optional_user(request.headers.get("authorization"))` instead of `Depends` | T08 (verify_token awaited twice) |
| X4 drop the "empty header = absent" guard (call `verify_admin_key("")`) | T13 |
| X5 move the check into the handler after the usage/anon gate | T06 (anon gate stub called on A1/U6), T18a/b, T19 |
| X6 flag-OFF path of `require_paid_route_admin` resolves a bearer / reads headers | T17 (ADMIN `verify_token` count) |
| X7 the refusal log line includes the Authorization header value | T21 |
| X8 `run_eval` sends `X-Admin-Key` whenever `ADMIN_API_KEY` is set (no opt-in) | H02 (and the W4-13 pins in CI order) |
| X9 smoke probe 12 stays anonymous | H09 |
| X10 guard attached to text routes only (url/image forgotten) | T04, T06 for U4-U6 |

---

## 7. Gates (cheapest first; every pytest through the bounded runner; paste each `[pyt]` line)

- **G0 versions**: print `python -c "import fastapi,starlette,slowapi,uvicorn,jwt,httpx,requests; ..."` versions; base values in section 0 (httpx 0.28.1 is what the scripts' MockTransport tests use).
- **G1 syntax + ruff tier** over every changed file: `<venv> -m py_compile <files>`; `<venv> -m ruff check --select E9,F63,F7,F82 --no-cache <files>`. No changed file is on `.github/black-clean-paths.txt`; new test files are not added to it (s69/s70 precedent) unless ruled.
- **G2 RED files at HEAD**: `pyt.py --bound 600 --tag u13-red -- tests/test_s71_u13_compare_auth_required.py tests/test_s71_u13_harness_auth.py -q` -> all pass; no `[netguard]` line names a node of either file.
- **G3 pin set, one process, CI order** (the 2.10 set + the two new files + every module-level `ADMIN_API_KEY` setter so the collision is exercised): `pyt.py --bound 1200 --tag u13-pins -- tests/test_analytics.py tests/test_b2_strict_optional_auth.py tests/test_bias_matrix_probe.py tests/test_eval_runner.py tests/test_explicit_pair_integration_mocked.py tests/test_http_400_cap_cut_mapping.py tests/test_m13_03_paid_work_gating.py tests/test_paid_route_metering.py tests/test_partial_specs_stash_on_price_timeout.py tests/test_password_reset_deep_link.py tests/test_retro_w1_1.py tests/test_route_introspection.py tests/test_s71_u13_compare_auth_required.py tests/test_s71_u13_harness_auth.py tests/test_security_regression.py tests/test_text_error_envelope_no_raw_exception.py tests/test_text_routes_error_mapping.py tests/test_timeout_partial_integration.py tests/test_validation_matrix_runner.py tests/test_w49_extraction_catch_redaction.py tests/test_w4_13_flag_off_ledger.py tests/test_w4_13_measurement_truth.py -q` -> 0 failed, 0 errors.
- **G4 MODULE-REFERENCE comm gate** at BASE (detached scratch worktree `git worktree add --detach <scratchpad>/u13-base 4bd5a09f`, no node_modules needed) and at HEAD, chunks of at most 25, `--bound 1200` each, `-q -rfE`. Set = union of
  - `grep -rlE "text_routes|url_routes|image_routes|auth_routes|referral_routes|admin_routes|eval_runner|run_validation_matrix|bias_matrix_probe|bundle_d_prod_smoke|cron_eval_nightly|verify_after_credits" tests/ --include=test_*.py`
  - `grep -rlE "/api/v1/(text/(compare|quick|prices)|url/(compare|extract|detect)|image/identify|referrals/invite)" tests/ --include=test_*.py`
  - every file that sets `ADMIN_API_KEY` at module import (2.8 list) and the hand-added `tests/test_w4_13_flag_off_ledger.py`, `tests/test_m13_21_openapi_gated.py`, `tests/test_conftest_env_safety.py`
  - the two new test files (HEAD only).
  At base this is 131 files (measured 2.10: 5 known FAILED, 0 ERROR). `comm -13 <(sort base FAILED+ERROR ids) <(sort head FAILED+ERROR ids)` MUST be empty. (Not `scripts/regression_gate_diff.py`: it cannot see ERRORs.)
- **G5** `pyt.py --bound 600 --tag u13-secreg -- tests/test_security_regression.py -q` alone -> green.
- **G6 netguard**: no `[netguard]` line in G2-G5 names a node absent from the base logs.
- **G7 hygiene**: `git diff --stat` shows only the R5/R6/R10/R11 files with line-level (not whole-file) diffs; `git diff | grep -nP '[^\x00-\x7F]'` on the touched app files is empty (R12); no `sk-`-shaped string anywhere in the diff.
- **G8 mutation spot-checks** X1-X10 (each: byte copy -> mutate -> run the named test(s) with `--bound 600` -> must FAIL -> restore -> sha256 equal).
- **Client gates**: none - this unit changes no `SmartCompareApp` file. If a ruling adds the camera refresh fix (Q4), that is a separate client unit with its own spec (jest by path, tsc, eslint, FULL jest, plus the backend tests that read the app).

---

## 8. Stated limits

- **L1 Account farming.** `/auth/register` is open (3/min per limiter key, which is the shared edge address); each account carries 3 lifetime-free, 3/day, 10/month credits on U1-U3 and is UNMETERED on U4-U6 until `ENABLE_PAID_ROUTE_METERING` is ON (Q5). `scripts/bundle_d_prod_smoke.py:162-163` registers throwaway accounts `bundle-d-smoke-<unix-ts>@qaren.app` with a password that is public in the repo; how many exist in production is NOT MEASURED (follow-up: delete or rotate them).
- **L2 The limiter gap is not fixed** (mechanism 2.7). Follow-up: measure the Railway edge peer addresses / replica count / `FORWARDED_ALLOW_IPS` / `RATELIMIT_ENABLED` names, then a per-user limiter key on authenticated routes (the user id is available after auth) - this would bound a farmed account's burst regardless of IPs.
- **L3 Public repo history.** The production URL, every route, the harness defaults, the example query pairs and the smoke password stay readable in git history whatever the visibility decision. The admin key is not in the repo; rotating `ADMIN_API_KEY` after the harness starts carrying it is an Ahmed decision (the memory records an owed rotation).
- **L4 Supabase-auth outage = compare outage** for signed-in users (today such users silently fall back to anonymous compares). The client does not log anyone out on it (`/auth/refresh` 503 path).
- **L5 Pre-guard framework work**: JSON decode (422 `json_invalid`) and multipart parsing (`/image/identify` uploads are fully parsed) happen before the guard on fastapi 0.141.1. Free, but an anonymous upload still costs parse CPU/memory.
- **L6 Admin-key guessing is not rate-limited** on these routes (a dependency precedes the slowapi wrapper). Pre-existing on the 19 `/api/v1/admin/*` routes, `/text/parse` and `DELETE /text/cache`; this unit adds the same class to 10 more routes.
- **L7 Garbage-bearer floods** still cost one Redis GET + one Supabase `/user` call each on U1-U6 (pre-existing on every `get_optional_user` / `get_current_user` route).
- **L8 Camera degrade** with an expired token (2.5); recoverable after another axios call refreshes. Q4.
- **L9 Harness operators** must run the scripts with `HARNESS_SEND_ADMIN_KEY=1` and `ADMIN_API_KEY` injected (`railway run -s web -- ...`). A future `cron_eval_nightly` service needs both variables in its own environment. `tests/integration/bundle-e-smoke.sh` probe 4 needs `AUTH_ARG` with the flag ON.
- **L10 Pre-existing raw logging** of the compare query and URLs at INFO (`text_routes.py:465`, `url_routes.py:292,353`) is untouched; with the flag ON anonymous callers no longer reach those lines. Follow-up.
- **L11** `ENABLE_STRICT_OPTIONAL_AUTH` stays dark; its other optional routes (`/feedback`, `/events`, `/home/trending`, referral invite) keep the silent downgrade.

---

## 9. Activation runbook (Ahmed; agents never flip flags)

1. Merge the PR (all five required checks green). Railway auto-deploys `web`; confirm `/health` 200 and the deployment's commit is the merge.
2. Flag still OFF: anonymous `GET /api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24` behaves exactly as before (today the 400 parse-failure copy while OpenAI is unfunded).
3. Smoke the credentials BEFORE the flip (no LLM spend while unfunded):
   - signed-in: the demo/test account's bearer on `GET /text/compare` -> NOT 401 (expect today's 400 copy);
   - admin: `railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 python docs/investigations/2026-09-29-session-69-state/verify_after_credits.py --pairs "iPhone 15 vs Galaxy S24"` -> compare http != 401/403 (the run itself FAILs while unfunded; only the status matters here).
4. Ahmed sets `ENABLE_COMPARE_AUTH_REQUIRED=true` on `web` (read per call; a Railway variable change redeploys anyway).
5. Re-probe anonymously (free): `GET /text/compare`, `GET /text/compare/stream` (expect a JSON 401, not a stream), `POST /text/quick`, `GET /text/prices/x`, `GET /url/extract?url=https://example.com`, `GET /url/compare?url1=...&url2=...`, `POST /image/identify` (any small multipart) -> each 401 `AUTH_REQUIRED`. `GET /url/detect`, `GET /url/retailers`, `/health`, `/legal/privacy` -> unchanged. Repeat step 3 -> still not 401.
6. Watch 24 h: Railway HTTP logs for 401s on the ten routes (expect the scanners), the `[paid-auth]` reason histogram, and any mobile-UA 401 not followed by a `/auth/refresh` + successful retry.
7. ONLY THEN fund OpenAI (prepaid, low project budget, no auto-recharge - D8 of the traffic finding). Then run step 3's admin command with the default pairs to verify end to end.
8. Rollback: unset `ENABLE_COMPARE_AUTH_REQUIRED` (per call, immediate). Rolling back reopens anonymous paid compares - do it only with OpenAI spend capped.

---

## 10. Stop conditions (any one: stop, write what was measured, report)

- S1 G4 finds a branch-only-new FAILED or ERROR id.
- S2 a flag-OFF pin (T17, T23, H02, the W4-13 ledger, `test_eval_runner_no_header_without_token`) is red at HEAD.
- S3 a `[netguard]` line names a new node.
- S4 the implementation needs any R9 file (auth_routes, admin_routes, error_handler, rate_limiter, main, backend/app, SmartCompareApp, requirements, an existing test/fixture).
- S5 the measured order in 2.3 does not reproduce on the real app (e.g. a schema 422 precedes the guard's 401): the D1 premise changed.
- S6 a test would need a real secret, the real `ADMIN_API_KEY`, network, Supabase, Railway or OpenAI.
- S7 a gate TIMEOUTs twice: report NOT MEASURED with both `[pyt]` lines.
- S8 `git diff --stat` shows a whole-file diff (line endings), or a non-ASCII byte lands in a touched app file.
- S9 origin/main moved past `4bd5a09f` before the build: rebase, re-anchor every file:line, re-run G4 at the new base.

---

## 11. Open questions for the orchestrator

- **Q1 Credential choice.** Recommended: the existing `X-Admin-Key` (D3), opt-in per script (D9). Alternative: a signed-in test account (needs a premium/unmetered tier for evals, login + refresh in four scripts, a second secret). Rule one.
- **Q2 Scope confirmation.** `/url/detect`, `/url/retailers` and both referral invitee routes start NO paid work (2.1) -> recommended OUT of scope, pinned anonymous (T05, T22). Confirm.
- **Q3 The four no-app-caller paid routes (A1-A4).** Recommended admin-only under the flag (D2: users are unmetered there; no caller). Alternative: user-or-admin like U1-U6 (needs a direct user resolution on those routes; flag-OFF identity must still hold: resolve ONLY when the flag is ON).
- **Q4 Client change.** The camera raw fetch has no 401 refresh (2.5): with the flag ON an expired token gives the generic error instead of today's anonymous success. Not required for the flip (recoverable, and zero tester sessions were seen since the OTA), but recommended as a separate small client unit (on a 401 from `/image/identify`, `await getOrStartRefresh()` and retry once). It is JS-only: ships by `eas update` to preview and is in the first store binary only if merged before U10's build. Does it gate the flip, and must it be in the store binary?
- **Q5** Flip `ENABLE_PAID_ROUTE_METERING` with or right after U13 so signed-in users are metered on the camera and URL compare (its anon-half precondition #128 is moot once anonymous callers are refused)?
- **Q6** Log admin passes at INFO (recommended, D7) or not at all?
- **Q7** Edit `verify_after_credits.py` in place (recommended: it is a runnable tool, not a SESSION record) or add a `scripts/` copy?
- **Q8** Names: `ENABLE_COMPARE_AUTH_REQUIRED`, `HARNESS_SEND_ADMIN_KEY`, `require_paid_route_user` / `require_paid_route_admin`, 401 text "Sign in to continue." - accept or rename.

---

## Review corrections (BINDING - supersede the body)

Adversarial review, 2026-10-03 08:27-08:55 +03, read-and-measure only, at `4bd5a09f` (re-proven: `git -C sc-s71-u13 rev-parse HEAD` = `4bd5a09f1216ee3891cd4c1ea908ebbef284604e`; the only worktree change is this untracked folder; spec sha256 before this section `9160d94a47002ac1d06483d8640ef3d0bf812011916ff0737c41822b6bcda72c`). Probes in scratchpad `u13/` (conftest import order, netguard installed, no network): `adv_probe1.py` (the real app, `dependency_overrides` on `get_optional_user`), `adv_probe2.py` / `adv_probe3.py` (the 10 REAL endpoint functions re-registered on fresh FastAPI apps with and without guards written exactly per D2/D3/D6, plus `error_handler.http_exception_handler`), `adv_commset.py`; notes `adv_notes.txt`. Result: the D1 premise and the paid-route inventory survive; the corrections are one missing activation precondition (C1), two gate/test designs that cannot pass as written (C2, C3), pin additions (C4, C5, C6), one overclaim (C7), the credential precondition (C8, C9) and stated-limit omissions (C10, C11).

### Re-measured and HOLDS (no change)

- **Inventory.** Every LLM/provider call site in `app/` (`guarded_llm_create` / `chat.completions` / `moderations` / `responses`: extraction_service x8, openai_service x5, image_service, url_extraction_service, verdict_critique_service, content_safety_service.moderate_output, serper_service.search_images, llm_provider) traced back to callers: reachable only from the text/url/image routers (the 10 rows) and the three admin-gated text routes (`text_routes.py:1429,1680,1847` `Depends(verify_admin_key)`). `referral_service.py` imports no paid module (its imports are abuse_detection/audit/database/db_offload) and `run_invitee_quiz` is a select + deterministic re-score; home/profile/history/share/feedback/usage/auth/legal/version routers import no paid module; admin_routes reads Redis/DB only (`get_burn_status`, gauges). No missed paid route, no fire-and-forget or background paid path outside the 10 rows.
- **Bypass hunt** (adv_probe1, real app): the 10 rows register exactly the verbs of 2.1 (walk_routes: no HEAD row, no extra verb); `HEAD /api/v1/text/compare` -> 405, handler not called; `OPTIONS` -> 405 without CORS headers / 400 for a foreign-origin preflight, handler not called; `/api/v1/text/compare/` and `/api/v1/text/compare/stream/` -> 307 to the guarded route; upper-case and `//` paths -> 404; each router is included exactly once (`main.py:373-386`). A route-decorator dependency covers every reachable variant.
- **Route template.** `request.scope["route"].path` on the real app is the full template (`'/api/v1/text/compare'`, `'/api/v1/referrals/invite/{share_token}'`): fastapi 0.141.1 `_IncludedRouter._handle_selected` sets `scope["route"] = original_route` (`routing.py:1799`) and every in-scope router carries its prefix at `APIRouter(prefix=...)`.
- **Order on the REAL endpoints with the guard** (adv_probe3, flag ON): GET q of 501 chars -> 401; POST `{}` -> 401; malformed JSON -> 422 `json_invalid`; SSE -> 401 `application/json` envelope; multipart `/image/identify` -> 401; wrong `X-Admin-Key` on `/text/prices` -> 403 FORBIDDEN; 12 anonymous POST /text/compare -> twelve 401s, then a valid bearer reached the service (no 429); `log_search` awaited 0 times.
- **Dependency cache** (adv_probe2): `verify_token` awaited exactly once per request in both flag states, with and without the guard; flag OFF the guard app and the no-guard app gave the same status and service-call counts for valid, expired and absent bearers.
- **OpenAPI** (adv_probe2): the FULL operation object of all 10 routes is identical with and without the guards (0 diffs; `components` equal; the re-registered no-guard app equals the real app on 10/10 operations).
- **Client** claims of 2.5 as stated (api.ts:51-65, 204-245, 252-375, 766-783, 863-879; HomeScreen.tsx:557). `getToken` (authService.ts:603-610) is a bare SecureStore read with no expiry check. Only HomeScreen and ResultsScreen (Main stack, signed-in) call the compare APIs.
- **Collision 2.8** reproduced: 9 `setdefault` + `test_retro_w1_1.py:392`; `tests/_env_safety.py:129` neutralises `ADMIN_API_KEY` at conftest time only. **G4** union reproduced at 131 files, identical to the writer's `comm_final.txt`. **RED/PIN** arithmetic 68/66 and 17/5 correct.
- **Baseline** (the G3 list plus the three files of C6, base, one process): `720 passed, 10 warnings in 45.25s` / `[pyt] tag=u13-adv-g3base start=2026-10-03 08:37:24 end=2026-10-03 08:38:10 elapsed=47s bound=1200s status=OK rc=0` (the netguard lines name baseline nodes such as `test_timeout_partial_integration.py`).

### Corrections

**C1 (BLOCKING activation precondition; answers Q5).** U13 alone does not stop paid spend: any self-registered account gets UNMETERED paid work on U4-U6. Measured: `url_routes.py:67` `_reserve_comparison_credit` returns False while `paid_route_metering_enabled()` is off; `image_routes.py:279` meters only under the same flag; `/auth/register` is public (`auth_routes.py:572`, 3/minute per limiter key) and the repo's own smoke registers and then logs in with a 200 + session (`bundle_d_prod_smoke.py:295-341`), so an account is one POST away (whether Supabase "Confirm email" is on in production is NOT MEASURED). With OpenAI funded, one account = unbounded `/url/compare` (two AI extractions + the gpt-4o verdict) and `/image/identify` (vision + a full compare), bounded only by the 10/minute decorator that measurably did not bite on 2026-10-02 (2.7). Binding: `ENABLE_PAID_ROUTE_METERING=true` is set in the SAME window as `ENABLE_COMPARE_AUTH_REQUIRED` (runbook step 4) and BEFORE funding (step 7), together with `ENABLE_CAMERA_FAILURE_ENVELOPE=true` (its CLAUDE.md row: "FLIP BOTH TOGETHER"). The client already routes 429 `USAGE_LIMIT` on both routes (HomeScreen.tsx:613 `isUsageLimitError` -> Paywall; api.ts:316 camera 429 tagged `USAGE_LIMIT`), and phones carry it (OTA `e2bde9c9` from `94c097cd`). L1 is rewritten: with both flags ON a farmed account is bounded by the free tier (3 lifetime-free, 3/day, 10/month across every metered route, `usage_service.py:137-148`); the device-fingerprint inheritance applies only when the header is sent.

**C2 (T21 cannot go green as written).** The valid-admin-pass scenario reaches the handler, and the handler logs the raw query at INFO: `text_routes.py:465` `logger.info(f"Text comparison request: {body.query}")` (observed in adv_probe1's output as `Text comparison request: A vs B`); `url_routes.py:292,353` log the URLs (L10). "NO record contains the query sentinel" over all records therefore fails at HEAD for a pre-existing reason. Binding rewrite: (a) across ALL records, DEBUG on all loggers: no record contains the bearer sentinel or the admin-key sentinel; (b) across the records whose message contains `[paid-auth]`: none contains the query sentinel, `IPHONE-U13-SENTINEL`, `testclient` or any header value; (c) non-vacuity: at least one `[paid-auth]` record in each of T20's five scenarios. Still 1 RED.

**C3 (G7 is broken on this box and would false-fail).** `grep -P` errors here (`grep: -P supports only unibyte and UTF-8 locales`, measured), and `git diff` CONTEXT lines carry pre-existing non-ASCII (lines with a byte > 127 at base: text_routes.py 80, image_routes.py 7, eval_runner.py 96, bundle_d_prod_smoke.py 42, bias_matrix_probe.py 10, run_validation_matrix.py 9; url_routes.py and verify_after_credits.py 0). Binding G7: a Python check over ADDED lines only - `git diff -U0 -- <touched files>`, every line that starts with `+` and not `+++` must be pure ASCII (all bytes < 128) - over the app files, the scripts and both new test files (R12).

**C4 (T23 strengthened, same count).** Compare the full operation JSON (`json.dumps(op, sort_keys=True)`) of each of the 10 routes, plus `components`, against base literals - not only the sorted `in:name` params and requestBody presence. Measured identical with the proposed guards (above), so it costs nothing and also catches a security/response/tag/summary drift. Still 10 PIN.

**C5 (composition pins, +3 PIN).** Define and pin as T16b: (a) a USER route, flag ON, valid bearer + `X-Admin-Key: wrong` -> passes as the user (not 403: the admin header is consulted only when no user resolved; base: passes -> PIN); (b) strict OFF, flag ON, rejected bearer + VALID admin key -> admin pass (base: anonymous pass -> PIN); (c) strict ON, flag ON, rejected bearer + valid admin key -> 401 `AUTH_REQUIRED` raised by `get_optional_user` before the guard body (the admin key cannot rescue a rejected bearer under strict; base: strict 401 -> PIN). File 1 becomes 68 RED / 69 PIN. No harness sends both headers (bundle_d sends one or the other - keep it so).

**C6 (G3 additions).** Add `tests/test_price_kpi_endpoint.py` (pins eval_runner's existing admin-header price-KPI client, which R10 keeps unchanged), `tests/test_health_brand_s69.py` (loads `scripts/bundle_d_prod_smoke.py` by path, :26-40; R10 edits that file) and `tests/test_cron_eval_nightly.py` (cron_eval_nightly imports `eval_runner.run_eval`, which R10 edits). Green at base in one process with the G3 list (720 passed, above). All three are already in the G4 set.

**C7 (R10/D9 overclaim: probe 12 is NOT opt-in).** Sending `Authorization: Bearer <derived_token>` whenever the smoke's login produced a token changes the smoke even with U13 OFF and nothing opted in: probe 12 (`bundle_d_prod_smoke.py:452-470`, `nocache=false`) becomes a signed-in compare that consumes one credit of the throwaway account and writes a comparisons/history row, cohort tracking and a user-keyed `search_logs` row on every run. Recommended ruling: keep the bearer (the app's own path, no secret), and R10 plus the PR body state it as the ONE non-opt-in harness change with those side effects (the smoke already creates one production user per run, #267). H09 unchanged.

**C8 (Q1 resolved, with a precondition).** X-Admin-Key (D3) is the safer option against both a test account and a new dedicated harness key, on this evidence: (i) capability - the same key already buys paid work (`/text/parse` = an LLM parse, `/text/price-kpi` = parse + the Serper/Bright Data cascade, `DELETE /text/cache` = an LLM parse; `text_routes.py:1429,1680,1847`), so U13 raises the per-call cost a key holder can spend, not the class; (ii) distribution - the planned operator path `railway run -s web -- ...` injects every `web` variable (`OPENAI_API_KEY`, `SUPABASE_SERVICE_KEY`, `ADMIN_API_KEY`, ...) into the script process, so the harness process already holds strictly more privilege than the admin key; a dedicated key adds a second secret without removing a holder; (iii) handling - the comparison is the existing bytes/`surrogateescape`/`compare_digest` code (`admin_routes.py:34-59`), Sentry scrubs `x-admin-key` (`sentry_service.py:150`) and ships no frame locals (`include_local_variables=False`, `:325`). **Binding precondition: rotate `ADMIN_API_KEY` to a fresh value of at least 32 random bytes BEFORE runbook step 3.** The rotation is recorded as owed since the 2026-09-07 transcript exposure (CLAUDE.md Operating Principle 10; the session-68 close lists "the leaked-key + `ADMIN_API_KEY` rotation still owed"), and with U13 ON the key becomes the only account-free way to buy paid compares while guesses are not rate-limited on these routes (L6: the guard runs before the slowapi wrapper; 12 refusals produced no 429 in adv_probe3). When `cron_eval_nightly` becomes a Railway service (L9), give that service its own credential, not `ADMIN_API_KEY` (a later unit).

**C9 (runbook, section 9, binding edits).** Insert "2b. Ahmed rotates `ADMIN_API_KEY` (C8); `railway run -s web` picks up the new value." Step 4 sets `ENABLE_COMPARE_AUTH_REQUIRED=true`, `ENABLE_PAID_ROUTE_METERING=true` and `ENABLE_CAMERA_FAILURE_ENVELOPE=true` (C1). Step 5 adds: a signed-in, exhausted free account now gets 429 `USAGE_LIMIT` on `/url/compare` and `/image/identify`. Step 7 (funding) only after steps 4-6 hold. Add a check for Ahmed: Supabase Auth "Confirm email" (NOT MEASURED) - if it is off, an account costs one POST per 10 compares a month.

**C10 (L9 incomplete).** Besides the 2.6 scripts, these LIVE/integration files call production in-scope routes anonymously and will get 401 with the flag ON: `tests/test_integration.py`, `test_two_input_shape.py` (TestLiveRailwaySmoke), `test_d2_spec_parity_per_category.py`, `test_spec_parity.py`, `test_unified_search.py` (TestCostTrackingLive), `test_cohort_personalization_load.py`, `test_bundle_c_integration.py`, `test_bundle_e_integration.py`, `test_lane2_integration.py`, `test_scoring_v2_all_nine_categories.py`, `tests/perf/test_latency_bench.py`, plus the manual `tests/post_deploy/bundle_c_acceptance.md`. None runs in CI; the weekly live suite selects `live_unit and not live_prod` (`.github/workflows/live-suite.yml:46,146`). Not edited by this unit; add them to L9 as a follow-up (they need the opt-in admin header or a bearer).

**C11 (D7 wording).** "INFO does not create Sentry events" is right, but `sentry_sdk.init` keeps its default integrations (`sentry_service.py:299-329` passes no `default_integrations=False`), so INFO lines ride as breadcrumbs on later error events. Harmless only because the line carries just the route template and the reason; D7's never-log-a-value rule is therefore load-bearing for Sentry too.

### Answers to the writer's open questions (recommendations; the orchestrator rules)

- **Q1** X-Admin-Key, opt-in per script (D9), `verify_admin_key` reused verbatim - with C8's rotation before runbook step 3. Not a test account (free 3/day and premium 10/day cannot carry a 30-50-query eval; 1 h JWTs; history/cohort writes; a second secret).
- **Q2** Confirm out of scope: `/url/detect` = SSRF validation + the `detect_retailer` string match (`url_routes.py:386-422`), `/url/retailers` static, invitee GET/quiz = DB + a deterministic re-score (`referral_service.py:463-506`). No change, noted: `/url/detect` still resolves attacker-chosen hostnames (on the loop unless `ENABLE_OFFLOOP_DNS_RESOLVE`) - a free DoS surface, not spend.
- **Q3** Admin-only (D2). Zero client callers (SmartCompareApp/src calls only `/text/compare`, `/text/compare/stream`, `/url/compare`, `/image/identify`), zero script callers, and no user dependency today (users are unmetered there).
- **Q4** Does NOT gate the flip (testers only today; recoverable - Home's focus effect calls `/referrals/status` through axios, which refreshes; the Results retry re-sends the same stale token, so the user must leave the screen). It MUST merge before U10's production store build (the production channel has never received an OTA). A separate small client unit.
- **Q5** Flip `ENABLE_PAID_ROUTE_METERING` in the same window as U13 and before funding - binding through C1.
- **Q6** INFO, route template + "admin credential accepted", never the value (D7): an audit trail of key use after C8's rotation.
- **Q7** Edit in place (the session-69 runbook and NEXT_SESSION_PROMPT reference that path; no test loads it today; H07/H10 will).
- **Q8** Accept `ENABLE_COMPARE_AUTH_REQUIRED` (the owner's brief and the traffic finding use it), `HARNESS_SEND_ADMIN_KEY`, `require_paid_route_user` / `require_paid_route_admin`, and "Sign in to continue." (ASCII; never rendered by the client).

Totals after these corrections: file 1 **68 RED / 69 PIN** (137 nodes), file 2 **17 RED / 5 PIN** (22); grand total **85 RED / 74 PIN** (159 nodes).

## Orchestrator rulings (BINDING)

(none yet)

---

## Orchestrator rulings (BINDING - supersede the review corrections and the body)

Fable orchestrator, session 71, 2026-10-03 08:51 +03. The spec body (sha256 `9160d94a...` as written) and the review section (file sha256 `1cf1095a...` after the reviewer's append) were read in full. Verdict on the spec: ACCEPTED with the rulings below. RED may start.

- **UR1 (Q1, C8) - harness credential.** `X-Admin-Key`, checked by calling `verify_admin_key` verbatim, sent by each script only under the opt-in `HARNESS_SEND_ADMIN_KEY` (D3, D9). A signed-in test account is rejected for the measured reasons in D3. Rotating `ADMIN_API_KEY` (at least 32 random bytes) is an ACTIVATION precondition for Ahmed (runbook step 2b), not a code change.
- **UR2 (Q2) - out of scope confirmed.** `/url/detect`, `/url/retailers`, both referral invitee routes and the rest of D8 stay anonymous; T05 and T22 pin it.
- **UR3 (Q3) - A1-A4 are admin-only under the flag.** No `Depends(get_optional_user)` is added to them (it would change their OpenAPI parameters and their flag-OFF behaviour under a bearer).
- **UR4 (Q4, L8) - the camera 401 refresh-and-retry is a SEPARATE client unit (U13c).** It does not gate the flag flip. It must merge before the U10 production build. The orchestrator files the issue at merge; this unit edits no `SmartCompareApp` file.
- **UR5 (Q5, C1, C9) - activation is THREE flags in one window, all Ahmed's:** `ENABLE_COMPARE_AUTH_REQUIRED`, `ENABLE_PAID_ROUTE_METERING` and `ENABLE_CAMERA_FAILURE_ENVELOPE`, flipped together BEFORE OpenAI is funded. Reason (C1, measured): with U13 alone any self-registered account has unmetered paid `/url/compare` and `/image/identify`. This unit changes NO code of the two existing flags; section 9 as corrected by C9 is the runbook, and the PR body carries it. The #128 precondition recorded for `ENABLE_PAID_ROUTE_METERING` concerns anonymous callers, who no longer reach these routes with U13 ON.
- **UR6 (Q6, C11) - logging.** One INFO line per refusal and one per admin pass, exactly as D7. No header value, token, IP, host, query, body or concrete path in any `[paid-auth]` record. INFO lines ride along as Sentry breadcrumbs, which is why the rule is absolute.
- **UR7 (Q7) - `verify_after_credits.py` is edited in place.**
- **UR8 (Q8) - names accepted verbatim:** `ENABLE_COMPARE_AUTH_REQUIRED`, `HARNESS_SEND_ADMIN_KEY`, `compare_auth_required_enabled`, `require_paid_route_user`, `require_paid_route_admin`, the 401 text `Sign in to continue.`, the reason codes of D7.
- **UR9 - review corrections C2, C3, C4, C5, C6, C7, C10 and C11 are ACCEPTED as written** and are binding: the T21 rewrite (C2); G7 as a Python check that only ADDED lines of `git diff -U0` are ASCII (C3); T23 compares the full operation JSON plus components (C4); the three composition pins T16b (C5; file 1 = 68 RED / 69 PIN, grand total 85 RED / 74 PIN); the three extra G3 files (C6); the smoke probe-12 bearer is the ONE non-opt-in harness change and is stated in R10 and the PR body (C7); the live/integration files that will 401 with the flag ON become one follow-up issue (C10).
- **UR10 - the base moved.** Main is `eb86075e` (PR #279, U4b). Measured: between `4bd5a09f` and `eb86075e` nothing under `app/`, `tests/` or the harness scripts changed (the only file under `scripts/` is the new `render_myez_icons.py`), so every anchor in this spec holds. The orchestrator fast-forwards this worktree to `eb86075e` before RED. BASE for T17's recorded literals and for the G4 comm gate is `eb86075e`.
- **UR11 - T17's flag-OFF records live in ONE committed fixture**, `tests/fixtures/s71_u13_flag_off_baseline.json`, written by a recorder function in the test module (a documented `python -m` or pytest-free command, run by the RED author in a DETACHED scratch worktree at `eb86075e`), compared record by record. Every normalised field (a timestamp, a duration) is named in the recorder with its reason; nothing else is normalised. Hand-typed literals in the test body are not accepted for these 30 records.
- **UR12 - roles.** Every agent is Opus. The RED agent writes ONLY `tests/test_s71_u13_compare_auth_required.py`, `tests/test_s71_u13_harness_auth.py` and the UR11 fixture; it edits no file under `app/` or `scripts/`. The RED files are frozen after the orchestrator's gate; GREEN is a separate launch.
- **UR13 - the limiter cause, narrowed by measurement (orchestrator, Railway CLI, names and manifest only, 2026-10-03 08:50):** `FORWARDED_ALLOW_IPS` absent, `RATELIMIT_ENABLED` absent, `ENABLE_PROXY_AWARE_RATELIMIT` absent, `WEB_CONCURRENCY` absent, one replica (`numReplicas: 1`, region `asia-southeast1`). That eliminates causes (b), (c) and (d) of section 2.7. What remains is (a): the TCP peer address varies across requests, so the per-IP limiter spreads one client over many edge keys. Not measured directly. Consequences: the limiter is not a spend control on any route, and the CLAUDE.md sentence that calls the proxy-IP key "one deployment-wide bucket" is wrong; both go into the follow-up issue of L2 (a per-user limiter key on authenticated routes). This unit still does not change the limiter.
- **UR14 - residual after activation, stated for the PR body and for Ahmed:** registration is public, so the remaining exposure is the free-tier credits of each self-registered account (3 lifetime-free, 3 per day, 10 per month, per the tier table), bounded on every paid route only once UR5's three flags are on. The prepaid, low-cap, no-auto-recharge OpenAI budget stays the backstop. Whether Supabase "Confirm email" can be turned on without breaking the app's register flow is NOT measured; it is a follow-up question, not part of this unit.
- **UR15 - also recorded for the docs, not for this unit:** the service runs in `asia-southeast1` (Singapore). The traffic finding's "Sentry geolocates the caller to Singapore" most likely reflects the server's own location, because the backend SDK reports no client IP; the caller evidence is the 155 source addresses in the Railway HTTP log.

---

## Orchestrator gate on the RED tests (BINDING - supersedes everything above where they differ)

Fable orchestrator, session 71, 2026-10-03 09:20 +03. Verdict: **PASS with one change (UG1)**. GREEN may start.

Reviewed: `tests/test_s71_u13_compare_auth_required.py` (sha256 `1849dbfef701cceb...`, 994 lines), `tests/test_s71_u13_harness_auth.py` (`eb33a12da8fb5017...`, 391 lines), `tests/fixtures/s71_u13_flag_off_baseline.json` (`fa72e28fc4b0cd00...`, recorded twice at `eb86075e`, byte-identical, no normalised field). Measured by the RED agent at base and at HEAD: 85 failed / 74 passed over 159 nodes, 0 collection errors, 0 network attempts from either file; every RED fails for its stated reason (the proving line per id is in the RED report); the G3 neighbours pass without the new files (720) and with them only the 85 REDs fail; one mutated fixture record reddens exactly its T17 node. The orchestrator read the env fixture, the recorder, T17, T19, T20/T21 and T23 in the file.

- **UG1 - T23 compares only what the ten routes use.** As written T23 pins the WHOLE application's OpenAPI `components`, so any later unit that adds or changes any model anywhere would redden ten nodes and force a re-record of the fixture that also holds the 30 flag-OFF records; a re-record is exactly how an accidental flag-OFF change would get absorbed. Change: T23 keeps the full-operation comparison per route, and compares `components` restricted to the transitive closure of the `$ref`s reachable from the ten operations, computed the same way on both sides at compare time. The fixture is NOT re-recorded and its bytes do not change. The GREEN agent makes this edit FIRST (only `test_T23_openapi_unchanged` and one small helper), confirms T23 = 10 PIN green before touching `app/`, and reports the new file sha.
- **UG2 - the RED agent's deviations are accepted:** T18c asserts the envelope text `JSON decode error` (the unified envelope carries no pydantic type string); the two extra deterministic fields in the T17 records; the wider stub set; the vision-stub exit on U6; `ENABLE_REFERRAL_SYSTEM` set in T22a; the stricter assertions.
- **UG3 - apart from UG1 the three RED files are FROZEN.** A test edit needs a test defect proven by measurement and is reported as a deviation.
- **UG4 - the fixture is immutable in GREEN.** A GREEN that needs to re-record `s71_u13_flag_off_baseline.json` has changed flag-OFF behaviour and is wrong by definition (R8).
- **UG5 - the PR text carries:** the flag row; the activation runbook of section 9 as corrected by C9 and UR5 (rotate `ADMIN_API_KEY`, three flags in one window, the anonymous re-probe, then funding); the one non-opt-in harness change (C7); the stated limits L1-L11 with UR13 and UR14; the follow-ups (the camera 401 refresh-and-retry client unit; a per-user limiter key; the live/integration files that will 401; raw query logging at INFO; multipart parsing before the guard; the smoke accounts and their public password).
- **UG6 - `CLAUDE.md` is the orchestrator's at merge** (R14). No agent edits it.

## Orchestrator rulings after the adversaries (BINDING, 2026-10-03 11:15, supersede everything above)

Both adversaries returned SOUND (0 defects). The orchestrator re-hashed the twelve files, read the full diff of the three route files and the five harness scripts, fast-forwarded the worktree to main ca604e0a (PR #285; no overlap with the unit files) and re-ran the 25-file pin set there: 879 passed.

- **UF1 (ratified).** scripts/run_validation_matrix.py passes allow_redirects=False inside the opted-in branch only. This goes one keyword beyond R10 and is accepted: requests 2.34.2 forwards X-Admin-Key across a cross-host redirect (measured by the security adversary and by the fix agent). The not-opted-in call keeps exactly {params, timeout}.
- **UF2 (supplementary pins, a NEW file).** The RED files stay frozen (UG3) and the fixture immutable (UG4). The four test-strength gaps the adversaries measured are closed in this unit by ONE new file, tests/test_s71_u13_pins.py (LF, pure ASCII, hermetic, same stub and flag conventions as RED file 1, nothing imported from app.* at module top). Each pin names the mutant it kills and the pins agent proves the kill (byte copy, mutate, run, must FAIL, restore, sha256 equal):
  - **P1 exact admin key (kills MF and MA).** Flag ON, ADMIN_API_KEY set to the sentinel. On one USER route (POST /api/v1/text/compare) and one ADMIN route (GET /api/v1/text/prices/{product}): X-Admin-Key equal to the sentinel minus its last character, its first character alone, the sentinel with one character case-flipped, and the sentinel plus one extra character each get 403 with code FORBIDDEN and zero stub calls; the exact sentinel passes. Plus: app.api.text_routes.verify_admin_key IS app.api.admin_routes.verify_admin_key (identity), and a spy shows the guard hands the supplied header value to it exactly once.
  - **P2 flag OFF never consults the admin header (kills XA and XB).** Flag unset and flag set to "false": with text_routes._admin_credential_passes replaced by a spy that records calls, a request carrying a valid and a request carrying a wrong X-Admin-Key on one USER route and on one ADMIN route records zero spy calls, and status and body equal those of the same request without the header (all other flags unset).
  - **P3 refusal reasons and the label fallback.** Flag ON: a bearer-only caller on an ADMIN route gets 401 AUTH_REQUIRED, verify_token awaited zero times, exactly one [paid-auth] record with reason=ADMIN_REQUIRED; an Authorization header with the Basic scheme on a USER route gets 401 with reason=BEARER_REJECTED; _paid_route_label returns "<METHOD> ?" when scope carries no route and when the route template is empty; no record carries the header value.
  - **P4 the redirect keyword.** run_validation_matrix.run_query, opted in: the captured requests.get keywords are exactly params, timeout, headers and allow_redirects False. (The not-opted-in shape is already pinned by H06.)
  Gates for the new file: alone; together with the two RED files (159 + the new nodes, netguard 0 attempts); the 25-file pin set plus the new file in CI order; py_compile and ruff; the ASCII and LF checks; the mutants MF, MA, XA, XB, a reason swap (ADMIN_REQUIRED logged as NO_CREDENTIAL), a label-fallback change and the removal of allow_redirects, each KILLED by at least one node of the new file.
- **UF3 (out of scope, follow-up issue).** A whitespace-only ADMIN_API_KEY counts as a configured key in admin_routes.verify_admin_key (an R9 file, pre-existing, every admin route). Own unit.
- **UF4 (by design, documented).** With ENABLE_STRICT_OPTIONAL_AUTH on, a rejected bearer on U1-U6 is refused by get_optional_user before the guard body and logs no [paid-auth] line. Strict stays dark; the activation runbook says the reason histogram undercounts under strict.
- **UF5 (PR text).** With an operator-supplied --auth-token, bundle_d_prod_smoke probe 12 sends that token: one credit and one history row in the operator account per run. No code change (R10 literal).
- **UF6.** Unmeasured by design and stated in the PR: real uvicorn / h11 header handling, the Railway edge and production log shipping. The owner activation runbook carries the anonymous re-probe that measures the first two.
