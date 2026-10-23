# S81-05 unit spec (measured): REQUEST-CONTEXT, three request headers into ContextVars + the HMAC device-key helper

- Unit: S81-05 REQUEST-CONTEXT (backend, lane B, one PR, dark flag `ENABLE_REQUEST_CONTEXT_HEADERS`). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s81-s05`, branch `feature/s81-request-context`, base main `84c861f6` (`git rev-parse HEAD` = `84c861f68ba3b23606c69ce2d1f78597e2f3037b` = origin/main with #366 B4, #367 certifi, #368 D03; `git status --short` empty at the start and after every probe below; this file lives under the gitignored `.qa-s80/`).
- Evidence: PLAN_S81 M1 unit text (`PLAN_S81.md:137`), the VERIFY "Quota, auth, refusal" bullets (`PLAN_S81.md:102-103`), Fable rulings F1-F4 (`PLAN_S81.md:123`), owner decisions 2 and 5 (`PLAN_S81.md:193`, `:201`), the orchestrator brief `specs/S81_05_BRIEF.md`, research `runs/research/A7.json` and `R5.json` (session-81 state folder), RULINGS_R0 R0-6 (no new route parameter; T23 not re-recorded), PLAN_S80 section 0 + `runs/research/contract_freeze.json` (session-80 state folder).
- Sister units and contracts: consumers to come, none in this unit: S81-06 ANTHROPIC-ROUTER reads `consent_version()` (`PLAN_S81.md:143`); S81-09 DEVICE-QUOTA-RIYADH reads `device_fingerprint()` and calls `device_key()` (`PLAN_S81.md:148`); S81-22 COMPARE-RUNS reads `compare_request_id()` and the peppered device hash (`PLAN_S81.md:168`); S81-08 CLIENT-FIRST-OTA sends the three headers on every metered request (`PLAN_S81.md:173`). In flight on branches: S81-03 LEDGER-V2 and ST1 share no file with this unit (they edit `app/services/*`, `CLAUDE.md`); the only shared hunk is the CLAUDE.md flag-row anchor (a known rebase: union, chronological order).
- Personal-data rule: no real name, email, phone, device id, account id or address appears in this file or in anything the unit writes. Every fingerprint, uuid and pepper in the tests is synthetic and built at run time (`"ab" * 32`, `str(uuid.uuid4())`, a pepper concatenated from short words); no 8-digit run, no key shape, no JWT, no `sk-` literal is written into any file.
- Measurement location: `<scratchpad>/S81-05/` (probe `probe_ctx.py` with its two `.out` files, `comm_files.txt`, the runner logs). Nothing in the worktree was written except this file.

## 0. What the unit does (one paragraph)

Behind `ENABLE_REQUEST_CONTEXT_HEADERS` (default OFF, read once per HTTP request as the middleware's first statement): a new pure-ASGI middleware `RequestContextMiddleware`, registered unconditionally as the INNERMOST user middleware in `app/main.py`, reads `X-AI-Consent-Version` (decimal int 0..999), `X-Device-Fingerprint` (the existing `^[a-f0-9]{64}$` shape) and `X-Compare-Request-Id` (canonical lowercase uuid4) from the raw ASGI scope into three ContextVars of a new stdlib-only leaf `app/utils/request_context.py`, and resets them when the request finishes. A missing or malformed header is `None`: never a 400, never a log line, never a changed byte. The leaf also carries the device-key helper `device_key(fp) = HMAC-SHA256(DEVICE_KEY_PEPPER, fp)` (fail closed: `None` and one WARNING per process when the pepper is unset or blank) and the dual-hash transition map `device_lookup_keys(fp)` = the HMAC key plus the legacy lookup key in the shape `users.device_fingerprint_hash` stores today. No route, response key, schema or envelope changes; nothing reads the ContextVars yet (PIN-proven); with the flag OFF the only new work per request is one `os.getenv`.

## 1. Base state (measured at 84c861f6)

### 1.1 The middleware stack (`app/main.py`)

| line | what |
|---|---|
| `:11` | `load_dotenv(override=True)` at import (the DOTENV hazard, 1.8) |
| `:33-39` | middleware imports (`RequestIDMiddleware` `:34`, `SecurityHeadersMiddleware` `:35`, `ErrorHandlerMiddleware` `:36`, `limiter, _default_rate_limits_enabled` `:37`, `SlowAPIASGIMiddleware` `:39`) |
| `:95` | comment `# -- Middleware (order matters: outermost added last) --` |
| `:113-119` | `app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["GET","POST","PUT","DELETE","OPTIONS"], allow_headers=["Authorization","Content-Type","X-Admin-Key","X-Request-ID"])`: the FIRST registration, so the innermost user middleware at base |
| `:121-147` | the M13-01 / W1-9c comment block (SlowAPIASGIMiddleware, measured limits) |
| `:148-149` | `if _default_rate_limits_enabled(): app.add_middleware(SlowAPIASGIMiddleware)` (conditional, between ErrorHandler and CORS when ON) |
| `:151-163` | `app.state.limiter`, the three exception handlers (`HTTPException`, `RequestValidationError`, `RateLimitExceeded`): these run in Starlette's ExceptionMiddleware, INSIDE every user middleware |
| `:165` / `:168` / `:171` | `ErrorHandlerMiddleware`, `SecurityHeadersMiddleware`, `RequestIDMiddleware` (last added = outermost) |

Starlette `add_middleware` inserts at index 0 of `user_middleware`, so `[m.cls.__name__ for m in app.user_middleware]` is outermost first. Measured at base (pinned by `tests/test_retro_w1_9.py:273-290`, `TestW19cFlagOffIdentity.EXPECTED_STACK`): `["RequestIDMiddleware", "SecurityHeadersMiddleware", "ErrorHandlerMiddleware", "CORSMiddleware"]`; with `ENABLE_DEFAULT_RATE_LIMITS` on, `SlowAPIASGIMiddleware` sits between `ErrorHandlerMiddleware` and `CORSMiddleware`. CLAUDE.md:112 states the order as "RequestID -> SecurityHeaders -> ErrorHandler -> CORS -> slowapi", which is wrong at base (slowapi is OUTSIDE CORS); GREEN rewrites that sentence in place (section 3 step 8).

### 1.2 The `request_id.py` pattern is NOT pure ASGI (correction to the brief)

`app/middleware/request_id.py:7-15`: `class RequestIDMiddleware(BaseHTTPMiddleware)`, `dispatch` reads `request.headers.get("X-Request-ID", str(uuid.uuid4()))`, stores it on `request.state.request_id` (= `scope["state"]`), awaits `call_next`, echoes `X-Request-ID`. `security.py:6-37` and `error_handler.py:255-286` are `BaseHTTPMiddleware` too. The request id reaches the envelope through `error_handler._get_request_id` (`:53-55`, `getattr(request.state, "request_id", "unknown")`). The repo's only hand-written pure-ASGI `__call__(self, scope, receive, send)` is `app/main.py:476` (`_AdminAuthenticatedStaticFiles`). So the new middleware follows the pure-ASGI shape (as the brief requires: no extra task, no body re-framing, streaming-safe), not the `request_id.py` class shape; it does not touch `request.state`.

### 1.3 ContextVar propagation through the real middleware classes (probe, measured)

`<scratchpad>/S81-05/probe_ctx.py` builds a scratch FastAPI app with the REAL `RequestIDMiddleware`, `SecurityHeadersMiddleware`, `ErrorHandlerMiddleware`, `CORSMiddleware` (the `main.py` kwargs) and a pure-ASGI ContextVar setter in two positions (innermost; directly inside RequestID). Both positions gave identical results (`probe_ctx_innermost.out`, `probe_ctx_inside_request_id.out`):

| reader | sees the value |
|---|---|
| async route, sync dependency, async dependency | yes |
| sync `def` route (threadpool) | yes |
| `asyncio.to_thread` | yes |
| `StreamingResponse` over an async generator (both chunks) and over a sync generator | yes |
| a task created with `loop.create_task` inside the route, read 50 ms after the response | yes (the task's context is a copy taken at creation) |
| the registered `HTTPException` handler | yes |
| `loop.run_in_executor(None, fn)` | NO (`None`: executor jobs do not copy the context; a stated limit for consumers) |
| 5 concurrent requests with different values (httpx ASGITransport, gather) | each saw its own |
| after the middleware's `finally` reset | `None` in the middleware's own context |
| unhandled exception in the route | 500 envelope `{code, error, request_id, success}`, `X-Request-ID` and `nosniff` present (the setter inside ErrorHandler does not disturb the envelope) |
| CORS preflight `OPTIONS` | answered 200 by CORSMiddleware; the INNERMOST setter never runs for it (inside-RequestID it does) |

### 1.4 Existing header readers (unchanged by this unit)

| site | what | gate |
|---|---|---|
| `app/api/auth_routes.py:29-35` | comment (`:30` carries a non-ASCII dash) + `_DEVICE_FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")` | none (regex constant) |
| `app/api/auth_routes.py:478-495` | `_read_valid_device_fingerprint(request)`: `fp = request.headers.get("X-Device-Fingerprint")`; `if fp and not _DEVICE_FINGERPRINT_RE.match(fp)`: INFO `device-fp header rejected: invalid format (expected 64-char hex), len=%d` and `None`; else returns `fp` (so `""` returns `""`, and because `.match` with `$` accepts a trailing `\n`, `"<64 hex>\n"` is accepted; neither is reachable over HTTP, h11 strips OWS and refuses LF) | used by `/register` (`:624`) and `/social-login` (`:553`, under `ENABLE_SOCIAL_DEVICE_FINGERPRINT`, `:1172`) |
| `app/api/auth_routes.py:499-537` | `_inherit_device_counter`: `.eq("device_fingerprint_hash", fp)` (`:523`) and writes `"device_fingerprint_hash": fp` (`:534`): the RAW header value is stored, no server-side hash | - |
| `app/services/usage_service.py:20-41` | a second copy `_DEVICE_FINGERPRINT_RE` (`:22`) + `valid_device_fingerprint(value)` (`:36-41`, `if value and RE.match(value)`, else `None`) | - |
| `app/api/image_routes.py:224-225` | `device_fp = valid_device_fingerprint(request.headers.get("x-device-fingerprint"))` in `identify_and_compare` (`:192`) | `ENABLE_ANON_USAGE_GATE` and no user (`:224`) |
| `app/api/text_routes.py:1404-1405` | the same in `quick_compare` (POST `/text/quick`, `:1385-1387`, admin-only) | `ENABLE_ANON_USAGE_GATE` (`:1404`) |
| `app/api/referral_routes.py:117-119` | pydantic body field `device_fingerprint_hash`, `pattern=r"^[a-f0-9]{64}$"` | `ENABLE_REFERRAL_SYSTEM` |
| `app/services/referral_service.py:322`, `:791-802`; `abuse_detection_service.py:137-147`, `:249` | store and compare the raw value (`referral_invites.device_fingerprint_hash`, the SAME_DEVICE check) | - |

`grep -rn` over `app/` and `scripts/` at base for `request_context`, `consent_version`, `compare_request_id`, `DEVICE_KEY_PEPPER`, `device_key`, `legacy_hash`, `X-AI-Consent`, `X-Compare-Request`: empty (every new name is new). `X-AI-Consent-Version` and `X-Compare-Request-Id` are read nowhere today.

### 1.5 The legacy hash shape (correction to the brief)

Migration 021 (`migrations/021_device_fingerprint_users.sql`): `users.device_fingerprint_hash TEXT`, comment "SHA-256 hash of expo-application bundle id + expo-device osBuildId + SecureStore-pinned nonce": the hash is computed by the CLIENT (`deviceFingerprint.ts`, A7 finding 5) and the server stores the header value verbatim (`auth_routes.py:534`, `referral_service.py:322`). A server-side `sha256(fp).hexdigest()` (the brief's `legacy_hash`) would match NO stored row. This spec therefore defines `legacy_hash(fp)` as the validated header value itself (the 021 stored shape) and asks for a ruling (Q1).

### 1.6 Flag-reader idiom and leaf precedents

- House idiom, exact: `app/middleware/error_handler.py:43-50` `_url_mode_v2_keys_enabled()`: `return os.getenv("ENABLE_URL_MODE_V2", "false").strip().lower() in ("true", "1", "yes", "on",)`, kept local so "the middleware never imports a service".
- Stdlib ContextVar leaf precedent: `app/services/openai_pricing.py:1-28` ("Stdlib only, no app imports: this is a LEAF ...") and `:48-50` (`_LEDGER: ContextVar[...] = ContextVar("openai_usage_ledger", default=None)`). `app/utils/__init__.py` is empty (0 bytes), so importing `app.utils.request_context` imports nothing else; `app/middleware/__init__.py` (450 bytes) imports request_id, security, error_handler and rate_limiter, all already imported by `app.main`.

### 1.7 Libraries (pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren`, installed == `requirements.txt`)

python 3.12.9, starlette 1.6.0 (`requirements.txt:151`), fastapi 0.141.1 (`:48`), anyio 4.14.2 (`:7`), uvicorn 0.52.4 (`:193`), httpx 0.28.1 (`:67`), sentry-sdk 2.68.1 (`:143`), slowapi 0.1.10 (`:145`). Measured: `uuid.UUID(s, version=4)` FORCES the version/variant bits, so `str(uuid.UUID(s, version=4)) == s` is True only for a canonical lowercase v4 string with the RFC variant (a v1 string, a variant-c string, upper case, braces, `urn:uuid:` and the 32-hex form all False); `int(chr(0x663)) == 3` and `chr(0x663).isdigit()` is True (Arabic-Indic digits), so the consent parser must use an ASCII `[0-9]` class, never `int()` on the raw string or `str.isdigit()`. Sentry's `StarletteIntegration(middleware_spans=False)` is the 2.68.1 default (`sentry_sdk/integrations/starlette.py:117`), so the new class adds no span. No new dependency.

### 1.8 Guards the new code must not trip

- DOTENV GUARD HAZARD: `tests/_env_safety.py:110-135` `CREDENTIALS_UNSET` (last entry `"APPLE_SIWA_PRIVATE_KEY"` at `:134`, comment `:133`, closing `)` `:135`); `install_dotenv_guard` (`:243-280`) re-runs `neutralize_credentials` after every `load_dotenv`, and `app.main:11` plus the extraction services call `load_dotenv(override=True)` at import. `DEVICE_KEY_PEPPER` is a new credential-bearing name: it joins `CREDENTIALS_UNSET` in this unit; a test that needs it set imports `app.main` FIRST (autouse fixture), then `monkeypatch.setenv`. `tests/test_conftest_env_safety.py:290-295` (`test_helper_covers_the_whole_contract`) only checks a superset, so adding is green.
- The "netguard credential list" named in the brief does not exist: `tests/_netguard.py` (388 lines) carries no credential names (grep for CREDENTIAL / KEY / TOKEN / SECRET: only its own allow-list env `QAREN_NETGUARD_ALLOW` `:66` and report path `:382`). The precedent `APPLE_SIWA_PRIVATE_KEY` is registered only in `_env_safety` (grep). So the pepper joins `CREDENTIALS_UNSET` only (Q4).
- `tests/test_sentry_channels_u8d_unit.py:773-918` (R8 AST pin over `app/**/*.py`): an ERROR / exception / critical log call outside an except arm may only take constants, type names or allow-listed names. The unit's one log line is a WARNING with a constant string (2.7); the middleware logs nothing.
- The pre-commit hook and secret scanner (`\bsk-[A-Za-z0-9_-]{20,}`, JWT shape, PEM header, 8-digit runs in the added-line sweep): every synthetic value is built at run time.
- `tests/test_retro_w1_9.py:436-451` walks `app.middleware_stack` via `.app` to `SlowAPIASGIMiddleware`: an innermost middleware sits below it and is never walked; the class still stores `self.app`.
- `tests/test_security_regression.py:403-407` reads `app/main.py` source for `CORS_ORIGINS` / `CORSMiddleware`: unchanged.
- No OpenAPI change: the middleware reads raw scope headers, outside FastAPI's dependency system, so `tests/test_s71_u13_compare_auth_required.py:983` (`test_T23_openapi_unchanged`, 10 routes, fixture `tests/fixtures/s71_u13_flag_off_baseline.json`) is not re-recorded (R0-6).

### 1.9 Line endings and bytes

Every existing file the unit edits is `i/lf w/crlf` (`git ls-files --eol`; measured CRLF counts: `app/main.py` 624/624 lines, `app/api/auth_routes.py` 1650/1650, `tests/_env_safety.py` 289/289, `tests/test_retro_w1_9.py` 532/532, `CLAUDE.md` 946/946). Non-ASCII bytes already present: `main.py` 36, `auth_routes.py` 175, `_env_safety.py` 63, `CLAUDE.md` 3961; `test_retro_w1_9.py` 0. Use the Edit tool on existing files (it keeps CRLF); write the three new files with CRLF like their neighbours and PURE ASCII (count bytes > 127 = 0 after every write); `git diff --stat` must show content lines only.

### 1.10 Base pass state (bounded runner, one process at a time, flag unset)

The pin files this unit names in section 4, one runner call:

```
tests/test_retro_w1_9.py tests/test_m13_01_slowapi_middleware.py tests/test_security_middleware.py
tests/test_observability.py tests/test_conftest_env_safety.py tests/test_auth_routes_invite_fingerprint.py
tests/test_social_login_device_fingerprint.py tests/test_s71_u13_compare_auth_required.py
tests/test_s75_fanout_identity.py tests/test_w4_13_flag_off_ledger.py tests/test_security_regression.py
tests/test_behavior_dimension_translation.py tests/test_sentry_channels_u8d_unit.py
  558 passed, 1 skipped, 2 deselected, 263 warnings in 145.06s
  [hermeticity] sentinel checked 559 test(s)
  [netguard] blocked 16 attempt(s) from 10 node(s)   (all baseline nodes: test_m13_01 x2, test_auth_routes_invite_fingerprint x2,
                                                      test_security_regression x6; sentinel neutralized.supabase.invalid / api.openai.com)
  [pyt] tag=s05-base-pins start=2026-10-23 06:46:57 end=2026-10-23 06:49:26 elapsed=149s bound=600s status=OK rc=0
```

The comm set (section 7, 150 files, six chunks of 25) at base, flag unset, one runner call per chunk:

```
c00  2 failed, 972 passed, 25 deselected   [pyt] tag=s05-base-c00 start=2026-10-23 06:59:36 end=2026-10-23 07:00:14 elapsed=38s bound=1200s status=FAIL rc=1
     FAILED tests/test_auth_interceptor.py::test_sign_in_with_social_exception
     FAILED tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
       (both listed in tests/.pre_impl_failures.txt:88-89: known reds CI deselects)
     [hermeticity] sentinel checked 974 test(s)   [netguard] blocked 6 attempt(s) from 5 node(s)
c01  526 passed, 1 skipped, 22 deselected      [pyt] tag=s05-base-c01 start=2026-10-23 07:00:26 end=2026-10-23 07:03:23 elapsed=177s bound=1200s status=OK rc=0
     [hermeticity] sentinel checked 527 test(s)   [netguard] blocked 61 attempt(s) from 38 node(s)
c02  375 passed, 19 deselected                 [pyt] tag=s05-base-c02 start=2026-10-23 07:03:54 end=2026-10-23 07:05:57 elapsed=123s bound=1200s status=OK rc=0
     [hermeticity] sentinel checked 375 test(s)   [netguard] blocked 10 attempt(s) from 10 node(s)
c03  790 passed, 1 skipped, 1 deselected       [pyt] tag=s05-base-c03 start=2026-10-23 07:06:22 end=2026-10-23 07:08:29 elapsed=127s bound=1200s status=OK rc=0
     [hermeticity] sentinel checked 790 test(s)   [netguard] blocked 115 attempt(s) from 20 node(s)
c04  2341 passed                               [pyt] tag=s05-base-c04 start=2026-10-23 07:08:54 end=2026-10-23 07:12:11 elapsed=197s bound=1200s status=OK rc=0
     [hermeticity] sentinel checked 2341 test(s)  [netguard] blocked 17 attempt(s) from 9 node(s)
c05  1053 passed, 2 deselected                 [pyt] tag=s05-base-c05 start=2026-10-23 07:12:28 end=2026-10-23 07:14:52 elapsed=144s bound=1200s status=OK rc=0
     [hermeticity] sentinel checked 1053 test(s)  [netguard] blocked 139 attempt(s) from 67 node(s)
total: 6,057 passed, 2 skipped, 69 deselected, 2 failed (both baseline); base FAILED set = the two auth_interceptor nodes
```

## 2. Contract

### 2.1 Flag and knob

- `ENABLE_REQUEST_CONTEXT_HEADERS` (default OFF): reader `app.utils.request_context.request_context_headers_enabled()` = `os.getenv("ENABLE_REQUEST_CONTEXT_HEADERS", "false").strip().lower() in ("true", "1", "yes", "on")`, read once per ASGI call as the FIRST statement of `RequestContextMiddleware.__call__` (so OFF reads no scope key and no header). A new name: unset in production by construction (no ledger line names it).
- `DEVICE_KEY_PEPPER` (credential, NAME only; the owner sets it on `web` before the flag flips): read PER CALL inside `device_key()` with `os.getenv("DEVICE_KEY_PEPPER")`; `None`, `""` or whitespace-only (after `.strip()`) = unset; the HMAC key is `pepper.strip().encode("utf-8")`. No minimum length is enforced (owner step: 32+ random bytes). No other knob.

### 2.2 New module `app/utils/request_context.py` (stdlib only: `contextvars`, `hashlib`, `hmac`, `logging`, `os`, `re`, `threading`, `typing`, `uuid`; no `app.*` import)

Constants: `FLAG_ENV = "ENABLE_REQUEST_CONTEXT_HEADERS"`, `PEPPER_ENV = "DEVICE_KEY_PEPPER"`, `HEADER_CONSENT_VERSION = b"x-ai-consent-version"`, `HEADER_DEVICE_FINGERPRINT = b"x-device-fingerprint"`, `HEADER_COMPARE_REQUEST_ID = b"x-compare-request-id"`, `DEVICE_FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")` (the canonical object; `auth_routes` re-imports it, 3 step 2), `_CONSENT_RE = re.compile(r"[0-9]{1,3}")`.

ContextVars (module level, `default=None`): `_CONSENT_VERSION: ContextVar[Optional[int]]` name `"s81_consent_version"`, `_DEVICE_FINGERPRINT: ContextVar[Optional[str]]` `"s81_device_fingerprint"`, `_COMPARE_REQUEST_ID: ContextVar[Optional[str]]` `"s81_compare_request_id"`.

| function | signature | rule |
|---|---|---|
| `request_context_headers_enabled` | `() -> bool` | 2.1 |
| `parse_consent_version` | `(raw: object) -> Optional[int]` | `str` only; `_CONSENT_RE.fullmatch(raw)` (no strip, no sign, ASCII digits only, 1-3 digits, leading zeros allowed) -> `int(raw)`; anything else (non-str, empty, `"1000"`, `"-1"`, `"+3"`, `" 3"`, `"3.0"`, Arabic-Indic or fullwidth digits, a trailing `\n`) -> `None`; never raises |
| `parse_device_fingerprint` | `(raw: object) -> Optional[str]` | `str` only; `DEVICE_FINGERPRINT_RE.fullmatch(raw)` -> `raw`; else `None` (`fullmatch` rejects the trailing-`\n` form `auth_routes` `.match` accepts, unreachable over HTTP, 1.4); never raises |
| `parse_compare_request_id` | `(raw: object) -> Optional[str]` | `str` only; `len(raw) == 36`; `str(uuid.UUID(raw, version=4)) == raw` (canonical lowercase hyphenated v4 with the RFC variant) -> `raw`; `ValueError`/anything -> `None`; never raises |
| `consent_version` / `device_fingerprint` / `compare_request_id` | `() -> Optional[int]` / `Optional[str]` / `Optional[str]` | the ContextVar `.get()`; `None` outside a bound request |
| `bind_from_headers` | `(headers: object) -> tuple` | TOTAL: iterates `headers` (the ASGI `scope["headers"]` list of `(bytes, bytes)`) once; for each of the three LOWERCASE names takes the FIRST occurrence only (Starlette `Headers.get` semantics; a later duplicate never replaces a malformed first one); decodes `latin-1`; parses; sets all three ContextVars (to `None` when absent or malformed); returns the three tokens. Any exception while reading or parsing (non-iterable headers, non-tuple items, non-bytes values) -> all three bound to `None`. Never raises, never logs |
| `reset_request_context` | `(tokens: tuple) -> None` | resets the three tokens in reverse order |
| `device_key` | `(fp: object) -> Optional[str]` | (1) `parsed = parse_device_fingerprint(fp)`; `None` -> return `None` (no env read, no log); (2) pepper per 2.1; unset -> the once-per-process WARNING (2.7) and `None` (fail closed: never a device key without a pepper, never a fallback to `fp` or `sha256(fp)`); (3) `hmac.new(pepper.strip().encode("utf-8"), parsed.encode("ascii"), hashlib.sha256).hexdigest()` (64 lowercase hex) |
| `legacy_hash` | `(fp: object) -> Optional[str]` | `parse_device_fingerprint(fp)`: the value as `users.device_fingerprint_hash` / `referral_invites.device_fingerprint_hash` store it today (1.5; Q1) |
| `device_lookup_keys` | `(fp: object) -> Dict[str, Optional[str]]` | the dual-hash transition map: exactly `{"device_key": device_key(fp), "legacy_hash": legacy_hash(fp)}` |
| `_reset_pepper_warning` | `() -> None` | test seam: clears the once-per-process latch |

### 2.3 New module `app/middleware/request_context.py`

```
from app.utils.request_context import (
    bind_from_headers, request_context_headers_enabled, reset_request_context,
)

class RequestContextMiddleware:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if not request_context_headers_enabled() or scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        tokens = bind_from_headers(scope.get("headers"))
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_context(tokens)
```

Exact semantics GREEN must keep: the flag read is the first evaluated call; the SAME `scope`, `receive`, `send` objects go downstream in both flag states (no wrapper, no copied scope, so no response byte can change); lifespan and websocket scopes pass through unbound; the module imports no `logging` and has no `print` (it never logs). `bind_from_headers` / `reset_request_context` are called through the names imported into this module (the RED call recorders patch `app.middleware.request_context.bind_from_headers`).

### 2.4 Registration (`app/main.py`) and why the innermost position

`app.add_middleware(RequestContextMiddleware)` immediately BEFORE the CORS `app.add_middleware(` at `:113` (first registration = innermost), unconditional (no flag at import; the flag is read per request). Resulting stack, outermost first: flag OFF or ON: `["RequestIDMiddleware", "SecurityHeadersMiddleware", "ErrorHandlerMiddleware", "CORSMiddleware", "RequestContextMiddleware"]`; with `ENABLE_DEFAULT_RATE_LIMITS` on: `[..., "ErrorHandlerMiddleware", "SlowAPIASGIMiddleware", "CORSMiddleware", "RequestContextMiddleware"]`. Why innermost (measured, 1.3):
1. The request id exists first: `RequestIDMiddleware` (outermost) has set `request.state.request_id` before this runs.
2. SlowAPIASGIMiddleware (default limits), ErrorHandlerMiddleware, SecurityHeaders and CORS all run OUTSIDE the ContextVar scope, so none of them can observe a value: they cannot come to depend on it, and their behaviour is the same in both flag states. The decorator limits (`@limiter.limit`), the exception handlers, dependencies and routes run inside it.
3. Any defect that raised inside the new middleware would still be turned into the standard 500 envelope with `request_id` and the security headers by ErrorHandlerMiddleware (it sits inside ErrorHandler; outside it, a raise would escape as a bare 500).
4. A CORS preflight never reaches it (CORSMiddleware answers it), and preflights carry no metered work.
5. The `test_retro_w1_9.py:436-451` stack walker reaches SlowAPIASGIMiddleware before it.

### 2.5 New keys and types

No response key, no header added to any response, no new route parameter, no OpenAPI change, no DB or Redis key, no new log line on a request path. The only new values are the three ContextVars (`int 0..999 | None`, `str 64 lowercase hex | None`, `str 36-char canonical lowercase uuid4 | None`) and the helper outputs (`device_key`: `str 64 lowercase hex | None`; `legacy_hash`: `str | None`; `device_lookup_keys`: a dict with exactly the keys `device_key`, `legacy_hash`).

### 2.6 Test seams (production values in brackets)

`request_context._reset_pepper_warning()` [never called in production], the module-level latch `_PEPPER_WARNED` [False until the first unset-pepper call] guarded by `_PEPPER_LOCK` (`threading.Lock`), the env names `FLAG_ENV` / `PEPPER_ENV` [`ENABLE_REQUEST_CONTEXT_HEADERS` / `DEVICE_KEY_PEPPER`], the header constants of 2.2. Tests set env with `monkeypatch.setenv` / `delenv` AFTER `import app.main` (1.8), patch `app.middleware.request_context.bind_from_headers` / `request_context_headers_enabled` for call recorders, and drive the middleware either directly (`asyncio.run(mw(scope, receive, send))` with a recording downstream app) or through a fresh exec of `app/main.py` (the `tests/test_retro_w1_9.py:122-148` `_fresh_main` pattern, dotenv / logging / sentry no-op'd) with probe routes added by `add_api_route`, never by editing the shared `app_main.app`.

### 2.7 Logging rules

The middleware logs nothing. The leaf logs exactly one line, on logger `app.utils.request_context`, WARNING, at most once per process (latch), only inside `device_key` when a VALID fingerprint meets an unset/blank pepper: `logger.warning("[REQUEST-CONTEXT] DEVICE_KEY_PEPPER unset or blank; device keys disabled (fail closed)")` (one constant argument). Never logged anywhere: any header value, the pepper (set or not), any device key, any parse failure reason, the request id.

### 2.8 Flag-OFF identity (the unit's main invariant)

With `ENABLE_REQUEST_CONTEXT_HEADERS` unset / `""` / `false` / `0` / `no` / `off` / ` FALSE ` and the FULL configuration present (pepper set, all three headers valid on the request): per HTTP request the middleware makes exactly one `os.getenv` call (`ENABLE_REQUEST_CONTEXT_HEADERS`), reads no scope key, calls neither `bind_from_headers` nor `reset_request_context`, passes the identical `scope` / `receive` / `send` objects downstream, and every accessor reads `None` inside the request; every response (status, headers except `date`, body bytes) is byte-identical to base for the same request (the base literals of P4). The only structural difference from base is one more entry at the end of `app.user_middleware` (pin change E1). With the flag ON nothing downstream reads the ContextVars yet (P1), so responses are byte-identical in that state too (P4 rows c/d).

### 2.9 Failure table

| input | flag OFF | flag ON | log |
|---|---|---|---|
| header absent | all `None` | that var `None` | none |
| malformed value (any of 2.2's rejects) | all `None` | that var `None`; the request proceeds; never 400 | none |
| duplicate header | n/a | the FIRST occurrence decides | none |
| non-UTF-8 / high bytes | n/a | latin-1 decode, then the parser rejects -> `None` | none |
| `scope["headers"]` missing / not a list / bad items | n/a | all `None` (bind is total) | none |
| parser raises (defect) | n/a | all `None`, request proceeds | none |
| lifespan / websocket scope | pass-through | pass-through, unbound | none |
| downstream raises | pass-through | vars reset in `finally`, the same exception propagates (ErrorHandler then builds the 500 envelope) | existing ErrorHandler line |
| `device_key` with pepper unset/blank | n/a (no consumer) | `None` | one WARNING per process |
| `device_key` with an invalid fp | n/a | `None`, no env read | none |
| `loop.run_in_executor` reader in a consumer | n/a | `None` (contextvars are not copied; use `asyncio.to_thread` or `copy_context().run`) | none |

### 2.10 Contract freeze (PLAN_S80 section 0, contract_freeze.json)

Additive only and invisible to build 3: no response path the client reads is added, removed, renamed or retyped; no refusal is introduced (the unit never refuses: malformed = `None`), so no new envelope, no new code and never a bare 503.

## 3. Change list, in the order GREEN applies it

Before the first edit: byte-copy (Python `shutil.copyfile`) every existing file below into `<scratchpad>/S81-05/green_before/` with its sha256; restore only from those copies.

1. NEW `app/utils/request_context.py` (2.1, 2.2, 2.6, 2.7): module docstring (purpose, stdlib-leaf rule, the None rule, the dual-hash note citing `auth_routes.py:534`, the `run_in_executor` limit), CRLF, pure ASCII.
2. `app/api/auth_routes.py:35`: replace `_DEVICE_FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")` with `from app.utils.request_context import DEVICE_FINGERPRINT_RE as _DEVICE_FINGERPRINT_RE  # S81-05: one compiled object, same pattern` (the comment block `:29-34` kept byte for byte; `re` stays imported, it is used elsewhere in the file). Nothing else in the file. `usage_service.py:22` and `referral_routes.py:118` are NOT edited (parity pin P6).
3. NEW `app/middleware/request_context.py` (2.3), CRLF, pure ASCII, no logging import.
4. `app/main.py`: add `from app.middleware.request_context import RequestContextMiddleware` after `:36` (inside the "# Import middleware" block); insert immediately before the CORS `app.add_middleware(` at `:113` a comment + `app.add_middleware(RequestContextMiddleware)`, comment text: "S81-05 (ENABLE_REQUEST_CONTEXT_HEADERS, read per request inside the class): registered FIRST so it is the innermost user middleware; RequestID has set request.state.request_id, and SlowAPI / ErrorHandler / SecurityHeaders / CORS run outside the ContextVar scope and cannot depend on it. Registration is unconditional; flag OFF = one os.getenv per request." Nothing else in the file.
5. `tests/_env_safety.py` `CREDENTIALS_UNSET`: after `:134` add the comment `# Device-key HMAC pepper (S81-05); absence = device keys disabled (fail closed).` and `"DEVICE_KEY_PEPPER",`.
6. `tests/test_retro_w1_9.py:273-278` `EXPECTED_STACK`: append `"RequestContextMiddleware",` after `"CORSMiddleware",` with a one-line comment `# S81-05: innermost, unconditional (pin change E1)`. Nothing else in the file.
7. NEW `tests/test_s81_s05_request_context.py` (section 5; written by RED, frozen for GREEN).
8. `CLAUDE.md`: (a) the flag row (section 8.1) as a new "SESSION 81 flag (S81-05 REQUEST-CONTEXT ...)" block after the D03 block (`CLAUDE.md:482-483`), before `## Tests` (`:485`); (b) `DEVICE_KEY_PEPPER` added to the **Optional** env list (`:337`, after the `APPLE_SIWA_*` names); (c) rewrite `:112` in place to "**Middleware stack** (outermost -> innermost): RequestID -> SecurityHeaders (HSTS, CSP, X-Frame-Options) -> ErrorHandler -> SlowAPIASGI (only under `ENABLE_DEFAULT_RATE_LIMITS`) -> CORS -> RequestContext (S81-05)" (keeping the file's existing arrow characters); (d) `:184` gains "request_context (S81-05, the three request headers into ContextVars)".

No other file: no requirements change, no client file, no migration, no `.githooks` change, no edit to `tests/.pre_impl_failures.txt`, `app/middleware/__init__.py`, `usage_service.py`, `referral_routes.py`, `image_routes.py`, `text_routes.py`, `processors.json` or legal text.

## 4. Existing pins

### 4.1 Pins that change (deliberately), one row each

| # | test node | asserts today | new assertion | reason |
|---|---|---|---|---|
| E1 | `tests/test_retro_w1_9.py::TestW19cFlagOffIdentity::test_imported_app_has_no_rate_limit_middleware`, `::test_fresh_exec_flag_off_matches_the_imported_app`, `::test_falsy_flag_values_register_nothing[ , 0, false, off, no]` (7 nodes, via `EXPECTED_STACK` `:273-278`) | the stack is exactly the four base classes | the four + `"RequestContextMiddleware"` last | the new middleware is registered unconditionally and innermost (2.4); the class name list still proves "no rate-limit middleware" when the flag is OFF |

No other existing node changes. `tests/test_m13_01_slowapi_middleware.py:45` checks `SlowAPIMiddleware not in classes` (membership: unaffected); the flag-ON w1_9 nodes check membership (unaffected).

### 4.2 Pins that must stay green and unedited (green at base, 1.10)

`tests/test_retro_w1_9.py` (every node except E1's 7, incl. the flag-ON stack, the 429 contract `_assert_contract_429` that the 429 still carries `x-request-id` + `nosniff`, and the `_messages_into_slowapi` single-chunk nodes), `test_m13_01_slowapi_middleware.py`, `test_security_middleware.py`, `test_observability.py` (request-id and error-handler behaviour), `test_conftest_env_safety.py` (superset contract), `test_auth_routes_invite_fingerprint.py`, `test_social_login_device_fingerprint.py` (the `_DEVICE_FINGERPRINT_RE` social pin `:256-260`: the re-imported object is the same pattern), `test_s71_u13_compare_auth_required.py` (T23 OpenAPI, 10 nodes, NOT re-recorded), `test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main` (the nine digests), `test_w4_13_flag_off_ledger.py` (the 45-scenario flag-OFF ledger), `test_security_regression.py` (CORS source pins `:400-407`), `test_sentry_channels_u8d_unit.py` (R8 AST), `test_ci_gates.py` and `test_behavior_dimension_translation.py` (the CLAUDE.md readers), the source-scanning pins of section 7. FY25 and W4-13 additionally run once with the flag ON (gate G6).

## 5. RED tests

### 5.1 `tests/test_s81_s05_request_context.py` (new; pure ASCII; CRLF; hermetic)

Harness rules: nothing the unit creates is imported at module top; helpers `_leaf()` / `_mw()` do `spec = importlib.util.find_spec("app.utils.request_context")` (resp. `app.middleware.request_context`), `assert spec is not None, "S81-05 leaf missing"`, then `importlib.import_module`, so every RED row fails at base on that AssertionError (never an ImportError or setup error). An autouse fixture imports `app.main` FIRST (DOTENV hazard), `delenv`s `ENABLE_REQUEST_CONTEXT_HEADERS` and `DEVICE_KEY_PEPPER`, and calls `_leaf()._reset_pepper_warning()` only when the leaf exists (`getattr` guard, so the fixture itself never errors at base). Synthetic values at run time: `FP_A = "ab" * 32`, `FP_B = "cd" * 32`, `UID_A = str(uuid.uuid4())`, `PEPPER = "s05" + "-pepper-" + "synthetic"`; malformed sentinels concatenated from short words; the nil uuid as `str(uuid.UUID(int=0))`; a v1-shaped string `"abcdefab-cdef-1abc-8def-abcdefabcdef"`, a variant-c string `"abcdefab-cdef-4abc-cdef-abcdefabcdef"`. `_full_config(monkeypatch, flag)` = the flag value (or delenv for "unset") + `DEVICE_KEY_PEPPER=PEPPER` + a scope carrying all three valid headers (`b"3"`, `FP_A`, `UID_A`). Direct-call helpers: `_scope(headers, type_="http")`, a `_Recorder` downstream ASGI app that captures `(scope, receive, send)` identities and the three accessor values (and optionally awaits an event or raises), a `_ScopeSpy(dict)` that records every key read (`__getitem__`, `get`, `__contains__`), an `os.getenv` recorder installed with `monkeypatch.setattr(os, "getenv", ...)` only around the direct call.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_s05_r01_flag_reader_per_call` (param: unset, `""`, `false`, `0`, `no`, `off`, `true`, `1`, `yes`, `on`, ` TRUE `, `On`) | `request_context_headers_enabled()` is True exactly for the six truthy spellings after strip/lower; setting the env after import flips the result | RED (leaf missing) | 2.1 |
| R2 | `test_s05_r02_consent_valid` (param `"0"->0`, `"3"->3`, `"03"->3`, `"007"->7`, `"999"->999`) | `parse_consent_version` returns the int | RED | 2.2 |
| R3 | `test_s05_r03_consent_invalid` (param: None, `""`, `"1000"`, `"-1"`, `"+3"`, `" 3"`, `"3 "`, `"3.0"`, `"1e2"`, `"0x3"`, `chr(0x663)`, `chr(0xFF13)`, `"3\n"`, `"abc"`, `b"3"`, `3`, `3.0`, `True`) | `None`, no exception | RED | 2.2 (ASCII class, str only) |
| R4 | `test_s05_r04_fp_valid` (param `"ab"*32`, `"0f"*32`, `"e"*64`) | `parse_device_fingerprint(x) == x` | RED | 2.2 |
| R5 | `test_s05_r05_fp_invalid` (param: None, `""`, `"AB"*32`, 63 chars, 65 chars, `"ab"*32 + "\n"`, `" " + "ab"*32`, `"g"*64`, 64 chars with one `-`, `int`, `bytes`) | `None` | RED | 2.2 (`fullmatch`, case-sensitive) |
| R6 | `test_s05_r06_request_id_valid` (3 runtime uuid4 strings) | returned unchanged | RED | 2.2 |
| R7 | `test_s05_r07_request_id_invalid` (param: None, `""`, `UID_A.upper()`, `"{"+UID_A+"}"`, `UID_A.replace("-","")`, `"urn:uuid:"+UID_A`, the v1-shaped string, the variant-c string, the nil uuid, `UID_A + " "`, 36 non-hex chars, `uuid.UUID(UID_A)` object) | `None` | RED | 2.2 (`version=4` round trip, length 36, str only) |
| R8 | `test_s05_r08_one_regex_object` | `auth_routes._DEVICE_FINGERPRINT_RE is leaf.DEVICE_FINGERPRINT_RE`; `.pattern == r"^[a-f0-9]{64}$"`; `.flags` == the base `re.compile(r"^[a-f0-9]{64}$").flags` | RED | 3 step 2 |
| R9 | `test_s05_r09_device_key_hmac` (param pepper: `PEPPER`, `"  " + PEPPER + "\t"`) | `device_key(FP_A) == hmac.new(PEPPER.encode("utf-8"), FP_A.encode("ascii"), hashlib.sha256).hexdigest()` (computed in the test); 64 lowercase hex; `!= FP_A`; `!= hashlib.sha256(FP_A.encode()).hexdigest()`; `device_key(FP_B) != device_key(FP_A)`; deterministic over 3 calls; changing the env pepper between calls changes the key (read per call) | RED | 2.2 |
| R10 | `test_s05_r10_device_key_fail_closed` (param pepper: unset, `""`, `"   "`, `"\t"`) | `device_key(FP_A) is None` on 3 calls; caplog (DEBUG, logger `app.utils.request_context`) holds EXACTLY ONE record, level WARNING, message == the 2.7 constant, `FP_A` not in `caplog.text`; after `_reset_pepper_warning()` the next call logs one more | RED | 2.2 (3), 2.7 latch |
| R11 | `test_s05_r11_device_key_invalid_fp` (pepper set; param: R5's invalid list) | `None`; zero log records; `os.getenv` recorder shows no `DEVICE_KEY_PEPPER` read | RED | 2.2 (1) |
| R12 | `test_s05_r12_pepper_never_leaks` | with the pepper set, `device_key`, `legacy_hash`, `device_lookup_keys` on FP_A and on an invalid fp: no return value equals or contains `PEPPER`; `repr()` of the map does not contain it; caplog at DEBUG over the root logger does not contain it | RED | 2.7 |
| R13 | `test_s05_r13_dual_hash_map` | `legacy_hash(FP_A) == FP_A` (the 021 stored shape, `auth_routes.py:534`); `legacy_hash(invalid) is None`; `device_lookup_keys(FP_A) == {"device_key": <R9 value>, "legacy_hash": FP_A}`; pepper unset -> `{"device_key": None, "legacy_hash": FP_A}`; the key set is exactly the two names | RED | 2.2 (Q1) |
| R14 | `test_s05_r14_accessors_default_none` | run inside `contextvars.Context().run(...)`: the three accessors return `None` | RED | 2.2 |
| R15 | `test_s05_r15_flag_on_binds_inside` (param: consent only, fp only, request id only, all three) | flag `true`, direct call: the downstream recorder sees the parsed values for the headers present and `None` for the others; it received the identical `scope`, `receive`, `send` objects (`is`) | RED | 2.3 |
| R16 | `test_s05_r16_flag_on_malformed_is_none` (param: each header with each of 3 malformed values, incl. a high-byte value `b"\xff" * 64`) | downstream called once; that accessor `None`; no exception; zero log records from `app.middleware.request_context` / `app.utils.request_context`; no sentinel in `caplog.text` (DEBUG, root) | RED | 2.2, 2.7 |
| R17 | `test_s05_r17_reset_on_return_and_raise` (param: downstream returns / raises `RuntimeError`) | inside ONE `async def` body (so the read shares the middleware's context; `asyncio.run` gives the whole body one task): `await mw(scope, receive, send)` (wrapped in `pytest.raises` for the raise case), then the accessors read `None` again in that same coroutine; in the raise case the SAME exception object propagates; nested: an outer direct call (headers A) whose downstream awaits an inner call (headers B) reads A again after the inner call returns | RED | 2.3 `finally`, tokens |
| R18 | `test_s05_r18_first_occurrence_wins` | headers `[(fp, FP_A), (fp, FP_B)]` -> `FP_A`; `[(fp, "zz"), (fp, FP_A)]` -> `None`; same two shapes for consent and request id | RED | 2.2 `bind_from_headers` |
| R19 | `test_s05_r19_non_http_scopes_pass_through` (param: `lifespan` without headers, `websocket` with the three valid headers) | flag `true`: downstream sees `None` x3 and the identical objects; the `bind_from_headers` recorder (patched in the middleware namespace) is called 0 times | RED | 2.3 |
| R20 | `test_s05_r20_bind_is_total` (param: `scope["headers"]` missing, `None`, `"junk"`, `[b"x"]`, `[(b"x-ai-consent-version", 3)]`; plus a variant with `leaf.parse_device_fingerprint` monkeypatched to raise) | flag `true`: downstream called once with `None` x3; no exception escapes | RED | 2.2 totality |
| R21 | `test_s05_r21_concurrent_isolation` | two concurrent direct calls (`asyncio.gather`) with different headers, each downstream awaiting a shared `asyncio.Event` set only after both entered, then reading the accessors: each sees its own three values (a module-global store would show the second request's values in both) | RED | ContextVars, not module globals |
| R22 | `test_s05_r22_flag_off_reads_nothing` (param flag: unset, `""`, `false`, `0`, `no`, `off`, ` FALSE `; FULL configuration) | direct call with a `_ScopeSpy`: zero scope keys read by the middleware; the `os.getenv` recorder (installed inside the test coroutine immediately before `await mw(...)` and removed right after, so asyncio's own setup is outside it; the downstream recorder calls no getenv) saw exactly one call, name `ENABLE_REQUEST_CONTEXT_HEADERS`; the `bind_from_headers` and `reset_request_context` recorders 0 calls; downstream got the identical objects and sees `None` x3 | RED | 2.8 |
| R23 | `test_s05_r23_flag_on_reads_flag_once` | flag `true`, FULL configuration: `os.getenv` recorder names == `["ENABLE_REQUEST_CONTEXT_HEADERS"]` (the middleware never reads the pepper); scope keys read are a subset of `{"type", "headers"}`; bind and reset called once each | RED | 2.3 |
| R24 | `test_s05_r24_sources_never_log` (AST) | `app/middleware/request_context.py`: no `import logging`, no name `logger` / `logging` / `print` / `warnings`; `app/utils/request_context.py`: exactly one call whose func is an attribute `warning` on a name `logger`, with exactly one `ast.Constant` str argument and no keywords, and no other `logger.*` / `logging.*` / `print` call; neither file imports a module under `app.` except the middleware importing `app.utils.request_context` | RED (files missing -> assertion) | 2.3, 2.7 |
| R25 | `test_s05_r25_stack_registration` (param: imported `app_main.app`; fresh exec flag unset; fresh exec flag `true`; fresh exec with `ENABLE_DEFAULT_RATE_LIMITS=true`) | class names == the 2.4 lists (flag state does not change registration) | RED (list equality fails) | 3 step 4 |
| R26 | `test_s05_r26_end_to_end_through_main` (fresh exec of `app/main.py` with probe routes added by `add_api_route`: an async route returning the three accessors + `device_key(device_fingerprint())`, a sync `def` route, a sync and an async dependency, an `asyncio.to_thread` read, a `StreamingResponse` async generator, a task created in the route and read 50 ms later, a `run_in_executor` read; param flag `true` / unset) | flag `true` + pepper + valid headers: every reader except `run_in_executor` sees `3`, `FP_A`, `UID_A`, and the HMAC of R9; `run_in_executor` sees `None`; flag unset: every reader `None` (device key `None`) | RED | 2.3, 2.4, 1.3 |
| R27 | `test_s05_r27_pepper_is_a_sanitized_credential` | `"DEVICE_KEY_PEPPER" in _env_safety.CREDENTIALS_UNSET`; `neutralize_credentials(env)` on a plain dict holding a synthetic pepper pops it and reports it in the returned map | RED (absent from the tuple) | 3 step 5 |

### 5.2 PIN rows (same file; green at base; run with the FULL configuration and call recorders where a gated mutant exists)

| # | test | assertion | why green at base |
|---|---|---|---|
| P1 | `test_s05_p01_no_consumer_in_app` (AST + text over `app/**/*.py` and `scripts/**/*.py`) | the substring `request_context` appears only in `app/utils/request_context.py`, `app/middleware/request_context.py`, `app/main.py`, `app/api/auth_routes.py`; ImportFrom of `app.utils.request_context` only in the middleware (names a subset of {`bind_from_headers`, `request_context_headers_enabled`, `reset_request_context`}) and in `auth_routes` (names == {`DEVICE_FINGERPRINT_RE`}); ImportFrom of `app.middleware.request_context` only in `app/main.py` (names == {`RequestContextMiddleware`}); `DEVICE_KEY_PEPPER`, `x-ai-consent-version`, `x-compare-request-id` (case-insensitive) only in the leaf (and the middleware docstring); no `importlib` / `__import__` string naming either module | no occurrence at base (1.4) |
| P2 | `test_s05_p02_openapi_declares_no_context_header` | no operation in `app_main.app.openapi()` declares a header/query/body field named (case-insensitive) `x-ai-consent-version`, `x-device-fingerprint`, `x-compare-request-id` | none at base |
| P3 | `test_s05_p03_cors_config_literal` | the `CORSMiddleware` entry of `app_main.app.user_middleware` has kwargs == `{allow_origins: app_main.ALLOWED_ORIGINS, allow_credentials: True, allow_methods: ["GET","POST","PUT","DELETE","OPTIONS"], allow_headers: ["Authorization","Content-Type","X-Admin-Key","X-Request-ID"]}` (no header added, Q3) | base kwargs |
| P4 | `test_s05_p04_response_bytes_literal` (3 requests x 4 env states = 12 nodes) | requests through `TestClient(app_main.app)` (no lifespan), each with `X-Request-ID: s05-fixed-request-id`: `GET /api/v1/app/version`, `GET /api/v1/usage/status` (no bearer), `GET /api/v1/s05-no-such-route`; env states: (a) flag unset, (b) flag `false` + pepper + valid headers, (c) flag `true` + pepper + valid headers, (d) flag `true` + malformed headers; `(status, body bytes, sorted response headers minus date)` == the literal RED records at base in state (a) (record twice byte-identical; paste as literals; if any of the three requests trips the netguard or is not deterministic at base, RED swaps it for `GET /api/v1/legal/terms` and records the swap in its report) | base has no middleware; all four states equal (a) |
| P5 | `test_s05_p05_no_header_value_logged` (param flag unset / `true`) | through `app_main.app`, pepper set, the three headers carrying runtime sentinels (valid `FP_A`, a malformed consent `"zz" + "9"`, a valid `UID_A`) on `GET /api/v1/app/version`; caplog at DEBUG (root): none of the sentinels and not the pepper appear in `caplog.text` | nothing logs them at base |
| P6 | `test_s05_p06_fp_readers_unchanged` | `auth_routes._read_valid_device_fingerprint` over a stub with `.headers.get` for inputs (`FP_A`, `"AB"*32`, 63 chars, `""`, None, `FP_A + "\n"`) == literals (`FP_A`, None, None, `""`, None, `FP_A + "\n"`): the base behaviour incl. the two quirks; `usage_service.valid_device_fingerprint` over the same == (`FP_A`, None, None, None, None, `FP_A + "\n"`); `usage_service._DEVICE_FINGERPRINT_RE.pattern` and the `referral_routes` field pattern == `r"^[a-f0-9]{64}$"` | measured at base (1.4) |
| P7 | `test_s05_p07_route_header_reads_untouched` | `app/api/image_routes.py` and `app/api/text_routes.py` each contain `valid_device_fingerprint(request.headers.get("x-device-fingerprint"))` exactly once, and `app/api/auth_routes.py` contains `request.headers.get("X-Device-Fingerprint")` exactly once (no route change) | base text |

Counts: 27 RED rows (about 150 nodes with the parametrizations), 7 PIN rows (about 22 nodes). RED gate: every RED node fails at base on an AssertionError only (`pyt.py`, bound 600; the log shows no ImportError / collection error); every PIN node is green at base.

## 6. Mutation table (each mutant applied to a byte copy, run through the bounded runner with `-k`, restored and sha-checked; `.qa-mutation.lock` per the house rule; KILLED = an assertion failure)

| id | file | exact edit (matches once) | killed by |
|---|---|---|---|
| X1 | leaf | `.strip().lower() in` -> `.lower() in` (flag reader) | R1[ TRUE ] |
| X2 | leaf | flag default `"false"` -> `"true"` | R1[unset], R22[unset] |
| X3 | middleware | `if not request_context_headers_enabled() or scope.get("type") != "http":` -> `if scope.get("type") != "http" or not request_context_headers_enabled():` | R22 (scope key read with flag OFF) |
| X4 | middleware | the flag check removed (always bind) | R22, R26[unset] |
| X5 | middleware | `reset_request_context(tokens)` removed from `finally` | R17 |
| X6 | middleware | reset moved after the `try` (not in `finally`) | R17[raise] |
| X7 | middleware | `scope.get("type") != "http"` check removed | R19[websocket] |
| X8 | middleware | downstream given a wrapped `send` (a pass-through closure) | R15 / R22 identity (`is`) |
| X9 | leaf | `_CONSENT_RE` -> `re.compile(r"\d{1,3}")` | R3[chr(0x663)], R3[chr(0xFF13)] |
| X10 | leaf | `{1,3}` -> `{1,4}` | R3["1000"] |
| X11 | leaf | consent parse via `int(raw)` inside try (no regex) | R3["+3"], R3[" 3"], R3["-1"] |
| X12 | leaf | `DEVICE_FINGERPRINT_RE.fullmatch(raw)` -> `.match(raw)` | R5[trailing newline] |
| X13 | leaf | fingerprint pattern compiled with `re.I` | R5["AB"*32], R8 flags |
| X14 | leaf | `uuid.UUID(raw, version=4)` -> `uuid.UUID(raw)` | R7[v1-shaped], R7[variant-c] |
| X15 | leaf | round-trip compare `== raw` -> `== raw.lower()` | R7[upper] |
| X16 | leaf | `len(raw) == 36` check removed | expected EQUIVALENT (the round trip already implies 36 canonical characters; the check is a work bound before `uuid.UUID` on a long header), reported for a ruling |
| X17 | leaf | `bind_from_headers` keeps the LAST occurrence (dict over the list) | R18 |
| X18 | leaf | the try/except in `bind_from_headers` removed | R20 |
| X19 | leaf | ContextVars replaced by module globals (one `_STATE` dict) | R21, R17[nested] |
| X20 | leaf | pepper unset -> `return hashlib.sha256(parsed.encode()).hexdigest()` (fail open) | R10 |
| X21 | leaf | `device_key` skips `parse_device_fingerprint` (HMACs any str) | R11 |
| X22 | leaf | `if not pepper:` without `.strip()` | R10["   "], R10["\t"], R9[padded] |
| X23 | leaf | latch removed (WARNING on every call) | R10 (exactly one record) |
| X24 | leaf | WARNING text gains `%s` with the fingerprint | R10 (`FP_A` not in text), R24 |
| X25 | leaf | `hashlib.sha256` -> `hashlib.sha1` / key and message swapped | R9 |
| X26 | leaf | `legacy_hash` returns `hashlib.sha256(fp.encode()).hexdigest()` | R13 |
| X27 | leaf | `device_lookup_keys` gains a third key | R13 |
| X28 | `app/main.py` | registration wrapped in `if request_context_headers_enabled():` | R25[unset], E1 |
| X29 | `app/main.py` | registration moved after `RequestIDMiddleware` (outermost) | R25 |
| X30 | middleware | `logger.info("ctx %s", fp)` added (with `import logging`) | R24, R16, P5[true] |
| X31 | `app/services/usage_service.py` (planted consumer) | `from app.utils.request_context import device_fingerprint` added | P1 |
| X32 | `tests/_env_safety.py` | the `"DEVICE_KEY_PEPPER",` line removed | R27 |
| X33 | `app/api/auth_routes.py` | the re-import replaced by the old local `re.compile` line | R8 |
| X34 | middleware | flag ON: `scope = dict(scope)` before downstream | R15 identity |
| X35 | `app/main.py` | `allow_headers` gains `"X-Device-Fingerprint"` | P3 |
| X36 | leaf | the flag read once at import into a module constant | R1 (the env set after import must flip the result) |
| X37 | middleware | the middleware also computes `device_key(fp)` per request (reads the pepper) | R23 (getenv names gain `DEVICE_KEY_PEPPER`) |

Equivalent survivors are reported for a ruling; one is expected (X16).

## 7. Comm set and gates for GREEN (cheapest first; every pytest through the bounded runner, one process at a time)

### 7.1 The comm set (150 files, `<scratchpad>/S81-05/comm_files.txt`, MINUS the four `test_precommit_hook*.py`)

Union of: (a) module-reference grep over `tests/*.py` for every edited or new module: `app.main` (99 files), `app.middleware` (49), `auth_routes` (64), the edited test-support module `tests/_env_safety.py` (21 importers; session-80 addendum), plus the edited `tests/test_retro_w1_9.py`; (b) the source-scanning pins: `test_model_config.py`, `test_model_config_enforced.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`, `test_start_command.py`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py`, every test that walks `app/` by path (`rglob` / `os.walk` / `glob("app` / `iterdir`: 26 files incl. `test_ci_gates.py`, `test_u3b_sharing_branch_removed.py`, `test_w4_13_measurement_truth.py`, `test_s81_d03_deny_and_guards.py`), every test that reads `app/main.py` by path (15) or `app/middleware/*` / `app/utils/*` by path (40); (c) the CLAUDE.md readers `test_ci_gates.py`, `test_behavior_dimension_translation.py` (measured: the only two that open the file); (d) T23 `test_s71_u13_compare_auth_required.py`, FY25 `test_s75_fanout_identity.py`, W4-13 `test_w4_13_flag_off_ledger.py`. Not included: the SmartCompareApp-scanning tests (the unit touches no client file and no client-visible contract; 2.5) and migration/manifest readers (no migration, no `processors.json` or legal change). The head run adds the new `tests/test_s81_s05_request_context.py`. Chunks of at most 25 files (6 chunks), bound 1200 each, base (a detached scratch worktree at `84c861f6` under the notes folder, no node_modules) and head; `comm -13` of the sorted FAILED node-id sets must be EMPTY (E1's 7 nodes are green on both sides: the base run uses the base test file, the head run the edited one). Base pass state: section 1.10 (base FAILED set = the two `test_auth_interceptor.py` baseline nodes); the file list per chunk is 7.3.

### 7.2 Gates, in order

| # | gate | command / pass rule |
|---|---|---|
| G1 | bytes | the three new files: bytes > 127 = 0; CRLF; `git diff --stat` content lines only (no whole-file diff) |
| G2 | syntax / lint | `<venv python> -m py_compile` and `-m ruff check --select E9,F63,F7,F82 --no-cache` on the 7 Python files touched |
| G3 | unit file | `pyt.py --bound 600 --tag s05-head-unit -- tests/test_s81_s05_request_context.py`: all green |
| G4 | pins | the 1.10 pin set at head: green (E1's 7 nodes green against the new `EXPECTED_STACK`) |
| G5 | mutation | section 6 on byte copies, each KILLED by its named row |
| G6 | flag ON identity | ONE runner call with `ENABLE_REQUEST_CONTEXT_HEADERS=true` exported in that call's env only: `tests/test_s75_fanout_identity.py tests/test_w4_13_flag_off_ledger.py tests/test_s71_u13_compare_auth_required.py tests/test_retro_w1_9.py tests/test_observability.py tests/test_security_middleware.py`: green (nothing reads the vars, so ON is byte-identical too) |
| G7 | comm | 7.1 base vs head, `comm -13` empty |
| G8 | hook | the commit through `.githooks/pre-commit` (no `--no-verify`); the hook test files are not run (no `.githooks` change) |

### 7.3 The comm set file list (all under `tests/`, the base chunks of 1.10; GREEN re-derives the union at head and adds any new importer)

```
chunk 00: test_429_contract.py test_account_deletion.py test_account_deletion_u8b.py test_account_deletion_u8b_fix_pins.py test_account_deletion_u8c_sentry_chain.py test_admin_key_and_sentry_scrub.py test_admin_referral_endpoints.py test_arabic_verdict_output_w414.py test_attribution_endpoint.py test_attribution_service.py test_attribution_service_edges.py test_auth_ai_sharing_toggle.py test_auth_demographics.py test_auth_error_log_hygiene.py test_auth_interceptor.py test_auth_preference_toggles_w314.py test_auth_refresh_and_revocation.py test_auth_routes_invite_fingerprint.py test_b2_strict_optional_auth.py test_backend_cleanup.py test_be_harness.py test_behavior_dimension_translation.py test_budget_value_literal.py test_bundle_c_feature_flag.py test_bundle_c_integration.py
chunk 01: test_bundle_e_integration.py test_camera_vision.py test_category_selection.py test_ci_gates.py test_cohort_personalization_load.py test_cohort_profile_governorate.py test_cohort_summary_orchestrator.py test_comparison_id_echo.py test_conftest_env_safety.py test_consent_capture_w3_16.py test_cost_dashboard.py test_cost_meter_s74.py test_demographics_rls.py test_domain_s76.py test_drug_database_service.py test_endpoint_shapes_vs_jsx.py test_error_middleware.py test_events_allowlist_superset.py test_feedback.py test_feedback_allowlist_superset.py test_flush_live_price_key.py test_health_brand_s69.py test_health_loop_lag.py test_hermeticity_pins.py test_history_routes.py
chunk 02: test_home_routes.py test_http_400_cap_cut_mapping.py test_image_identify_llm_unavailable_s69.py test_invitee_quiz.py test_lane2_integration.py test_legal_disclosure_s77.py test_legal_docs_u8.py test_legal_routes.py test_legal_s78.py test_limiter_endpoint_key.py test_m13_01_slowapi_middleware.py test_m13_02_proxy_aware_ratelimit.py test_m13_03_paid_work_gating.py test_m13_21_openapi_gated.py test_m13_25_compare_body_maxlength.py test_m13_26_image_error_envelope.py test_m13_28_referral_hardening.py test_m13_29_feedback_uuid.py test_m13_35_sse_disconnect_finally.py test_m18_preverdict_disconnect_refund.py test_migration_023.py test_migration_028_pain_workflow_events.py test_migration_032_b1_pre_hardening.py test_migration_037_security_definer_grants.py test_migration_043_delete_user_cascade.py
chunk 03: test_migration_index_predicate_immutability.py test_model_config.py test_model_config_enforced.py test_observability.py test_openai_key_log_hygiene_s69.py test_paid_route_metering.py test_password_reset_deep_link.py test_personalization.py test_price_kpi_endpoint.py test_profile_routes.py test_prompt_fence.py test_push_token_endpoint.py test_rate_limiting_complete.py test_referral_e2e.py test_referral_feature_flag.py test_referral_must_fixes.py test_referral_routes.py test_referral_share_privacy.py test_register_invite_linking.py test_retro_r_auth_fixer_pins.py test_retro_w0_4.py test_retro_w0_4_efg.py test_retro_w1_1.py test_retro_w1_2b.py test_retro_w1_2d.py
chunk 04: test_retro_w1_4_logout_expired.py test_retro_w1_4_server.py test_retro_w1_7_w1_10.py test_retro_w1_9.py test_retro_w1_9_429.py test_retro_w2_1.py test_route_introspection.py test_s70_model_router_downgrade.py test_s71_u13_compare_auth_required.py test_s71_u13_pins.py test_s75_fanout_identity.py test_s75_fanout_starve.py test_s77_redis_offloop.py test_s78_all_timeout_cap_as_timeout.py test_s78_tier_fill_residual_guard.py test_s79_b3b_apple_revoke.py test_s80_b1.py test_s80_b1_feedback.py test_s80_b3_vision_identity_v2.py test_s80_url_mode_v2.py test_s81_d03_deny_and_guards.py test_scraping_mode.py test_security_hardening.py test_security_middleware.py test_security_regression.py
chunk 05: test_sentry_channels_u8d.py test_sentry_channels_u8d_unit.py test_share_routes.py test_shopify_pdp_json.py test_shutdown_drain.py test_social_login_device_fingerprint.py test_social_login_smoke.py test_start_command.py test_streaming.py test_supabase_client_reuse.py test_text_error_envelope_no_raw_exception.py test_text_routes_error_mapping.py test_tier_detection.py test_timeout_partial_integration.py test_two_input_shape.py test_u13e_url_detect_guard.py test_u3b_sharing_branch_removed.py test_u3c_store_false_pin.py test_url_validator_offloop.py test_usage_device_inheritance.py test_version_routes.py test_w49_extraction_catch_redaction.py test_w4_12_display_contract.py test_w4_13_flag_off_ledger.py test_w4_13_measurement_truth.py
head adds: test_s81_s05_request_context.py (and, per the union rule, any file that newly imports app.utils.request_context / app.middleware.request_context; at head that is only the new test file)
```

## 8. CLAUDE.md row and owner steps

### 8.1 The flag row (GREEN writes it after the D03 block, before `## Tests`; wording may be tightened, content may not)

**SESSION 81 flag (S81-05 REQUEST-CONTEXT, 2026-10-23; default OFF, read PER CALL; a new name, so unset in production by construction (Railway not read); PLAN_S81 unit S81-05 (M1, lane B); spec `.qa-s80/S81-05_UNIT_SPEC.md` of the unit worktree with its review and rulings in the session-81 state folder `specs/`):**
- `ENABLE_REQUEST_CONTEXT_HEADERS` (S81-05, `app/utils/request_context.py::request_context_headers_enabled`, read once per HTTP request as the first statement of `app/middleware/request_context.py::RequestContextMiddleware`, a pure-ASGI class registered unconditionally as the INNERMOST user middleware in `app/main.py`, inside RequestID / SecurityHeaders / ErrorHandler / SlowAPIASGI / CORS, so none of them can observe the values) + credential NAME `DEVICE_KEY_PEPPER` (read per call by `device_key`; in `tests/_env_safety.CREDENTIALS_UNSET`, so a test sets it only after importing `app.main`). **Effect ON:** three request headers are parsed into ContextVars for the request scope and reset when it ends: `X-AI-Consent-Version` -> `consent_version()` (a decimal int 0..999, ASCII digits only), `X-Device-Fingerprint` -> `device_fingerprint()` (the existing `^[a-f0-9]{64}$`, full match; the compiled object now lives in the leaf and `auth_routes` re-imports it under its old name), `X-Compare-Request-Id` -> `compare_request_id()` (a canonical lowercase uuid4); a missing, duplicate-later, malformed or non-ASCII value is `None`: never a 400, never logged, never a changed byte. `device_key(fp)` = HMAC-SHA256(pepper, fp) (fail closed: `None` plus ONE WARNING per process `[REQUEST-CONTEXT] DEVICE_KEY_PEPPER unset or blank; device keys disabled (fail closed)` when the pepper is unset or blank, never a fallback key); `device_lookup_keys(fp)` = {`device_key`, `legacy_hash`}, the dual-hash transition map, where `legacy_hash` is the value as `users.device_fingerprint_hash` (migration 021) and `referral_invites` store it today (the client's own SHA-256, stored verbatim; per the ruling on Q1). **No consumer yet** (pinned): S81-06 consent routing, S81-09 device quota and S81-22 compare runs read them later; until then the flag is inert. **Flag OFF:** one `os.getenv` per request, no scope read, the identical scope/receive/send downstream, every accessor `None`; responses byte-identical (pinned against base literals); the only structural change is one more `app.user_middleware` entry (`tests/test_retro_w1_9.py` EXPECTED_STACK). **Stated limits:** build 3 sends `X-Device-Fingerprint` only on register / social sign-in / share and never the other two headers, so every accessor reads `None` on compares until the S81-08 OTA; the consent version is the CLIENT's claim (S81-06 treats it as a claim, not proof); the fingerprint is client-generated and only format-checked (a script can send a fresh value per request; the device cap protects honest clients only); `loop.run_in_executor` readers see `None` (use `asyncio.to_thread`); a task spawned inside the request keeps the request's values after it ends; CORS `allow_headers` is unchanged (native clients do not preflight; Expo web would need it); no DB change (`users.device_fingerprint_hash` keeps the client's hash until S81-09 decides); the privacy text for device counters moves in S81-12 LEGAL-V3, not here. **Owner steps (names only):** set `DEVICE_KEY_PEPPER` on `web` (32+ random bytes, never in the repo or chat) BEFORE the flag flips; flip `ENABLE_REQUEST_CONTEXT_HEADERS` in the post-approval window "ledger, breaker, request context ON" (PLAN_S81 flip order), after the S81-08 OTA has propagated; canary: none needed for bytes (inert); watch the single WARNING line (it means the pepper is missing). **Rollback:** unset the variable (per request, immediate).

### 8.2 Owner steps (in this order)

1. Create a random pepper of at least 32 bytes on a trusted machine and set it as `DEVICE_KEY_PEPPER` on Railway `web` (name only in any message; never in the repo, chat or a ledger). Rotating it later changes every device key (S81-09 counters restart for the day).
2. After approval and after the S81-08 OTA has propagated: set `ENABLE_REQUEST_CONTEXT_HEADERS=true` on `web` in its own canary window (no visible effect until a consumer flips).
3. Record both as dated ledger lines (names only).

## 9. Stated limits

1. Build 3 sends `X-Device-Fingerprint` only on `/register`, social sign-in and share (A7 finding 5, `authService.ts`), never `X-AI-Consent-Version` or `X-Compare-Request-Id`: every accessor reads `None` on compare, camera and usage requests until the S81-08 OTA.
2. The consent version is client-asserted; S81-06 must treat it as the client's claim (the server cannot verify what the user saw).
3. The fingerprint is client-generated and only format-checked (A7 finding 7, R5): a script can send a fresh value per request; a device cap built on it stops honest multi-account use only. The current composition hashes `osBuildId` (R5), so it likely changes on an OS update until S81-08 moves it to a Keychain UUID.
4. `legacy_hash` is the identity on a valid value (1.5; Q1). Whether social-login users carry a stored hash depends on `ENABLE_SOCIAL_DEVICE_FINGERPRINT`, whose production state is UNKNOWN (R-A15) until the owner's names-only answer.
5. ContextVar semantics consumers inherit: `loop.run_in_executor` sees `None`; a task created in the request keeps the request's values after it ends (a snapshot; S81-22's fire-and-forget insert relies on it); a value set inside a downstream task is not visible upstream.
6. The innermost position means a CORS preflight never binds (irrelevant: no metered work) and the default-limit 429 from SlowAPIASGIMiddleware is produced outside the scope (so a future device-keyed limiter must be a decorator or a consumer inside the route, not a slowapi key_func reading these vars).
7. CORS `allow_headers` (`main.py:118`) does not list the three headers (nor `X-Device-Fingerprint` at base): native clients do not preflight; an Expo web build would be refused (Q3).
8. One `os.getenv` per HTTP request in both flag states (measured cost negligible; not timed).
9. No minimum pepper length is enforced; a rotated pepper changes every device key.
10. `fullmatch` in the leaf rejects the trailing-newline fingerprint that `auth_routes` / `usage_service` `.match` accept; unreachable over HTTP (h11 refuses LF in header values), so the two readers agree on every value a real request can carry.
11. No DB change; the privacy policy (s3.4 "Device identifier", `privacy_policy.md:42`; s8 / s9) is unchanged here: device counters and their retention move in S81-12 LEGAL-V3.

## 10. Out of scope

Any consumer of the ContextVars (S81-06 routing, S81-09 quota and the device key in `consumed_keys`, S81-22 compare runs); `X-Client-Capabilities: price_asof` (sent by S81-08 for the as-of price unit); sending the headers from the client (S81-08); moving `usage_service.py:22` or `referral_routes.py:118` onto the leaf; changing the `/register` / social device binding or the anon gate; the stored-hash migration; CORS changes; Sentry tags or log fields carrying the request id or compare request id; legal text.

## 11. Open questions for the orchestrator

- Q1 (blocking for R13 / X26): the brief defines `legacy_hash(fp) = sha256(fp).hexdigest()` "(the users.device_fingerprint_hash shape, migration 021)". Measured: the server stores the header value verbatim (`auth_routes.py:523`, `:534`; `referral_service.py:322`; `abuse_detection_service.py:249`); the SHA-256 is the client's. A server `sha256(fp)` matches no stored row. Proposed ruling: `legacy_hash` = the validated header value (identity), as specified here. If the ruling keeps `sha256`, R13 and X26 flip and the CLAUDE.md row must say the map matches no existing row.
- Q2: the brief cites `request_id.py` as "the pure ASGI pattern"; it is a `BaseHTTPMiddleware` (1.2). This spec keeps the brief's PURE-ASGI requirement and the class shape of 2.3. Confirm.
- Q3: CORS `allow_headers` stays unchanged (P3 pins it). Should S81-08 or this unit add the three headers for Expo web? Default: no (native only; web is not a shipped target).
- Q4: the brief names a "netguard credential list"; none exists (1.8). The pepper joins `CREDENTIALS_UNSET` only, as `APPLE_SIWA_PRIVATE_KEY` did. Confirm.
- Q5: position: innermost (2.4) versus "directly inside RequestID" (the probe shows identical propagation; inside-RequestID would also bind CORS preflights and put SlowAPI / ErrorHandler inside the scope). Default: innermost.
- Q6: duplicate headers: first occurrence decides (Starlette `Headers.get`), a malformed first value is not rescued by a later valid one. Alternative: any duplicate = `None`. Default: first occurrence.

Not done in this spec: no source, test or CLAUDE.md edit; no mutation run (section 6 is GREEN's); the P4 literals are recorded by RED at base; the comm-set base run IS done (1.10) and the head run is GREEN's.
