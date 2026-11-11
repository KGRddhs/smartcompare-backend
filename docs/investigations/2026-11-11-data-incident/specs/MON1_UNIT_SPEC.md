# MON1 unit spec: LLM-CREDENTIAL-HEALTH (the operator signal for a dead LLM credential + the Serper key state)

- Unit: MON1 LLM-CREDENTIAL-HEALTH (incident root cause 2 "no alarm"; incident fix S7; session-81 DEFECT_LEDGER row 68). Class FOCUS (R-MON1-13).
- Flag ruling (R-MON1-1, a SPLIT): the PASSIVE part (the recorder leaf, the hooks at the dispatch chokepoints, the alert event, the two /health entries, the monitor path /health/llm, the Serper key state) ships UNFLAGGED as a production bug fix. The ACTIVE check is DARK behind ENABLE_LLM_CREDENTIAL_PROBE (default OFF, read per tick, house idiom) with the knob LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS (default 900, floor 300).
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-mon1 (detached, read-only for this round). Branch GREEN creates: fix/inc-mon1-llm-credential-health.
- Base sha a74caba7e3ff66b12e94178c912197c845ccbd14 (HEAD == base, measured 2026-11-11). `git status --short` EMPTY before every probe and after (this file is under the gitignored .qa-s80/).
- This round is READ-ONLY (H5 c): no pytest, jest, tsc or eslint ran. Every run is listed with its command and marked DEFERRED TO RED. Measurement location: <SP>/MON1/spec (scratch copies of base blobs only; deleted at the end).
- Evidence: record/incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md (root cause 2 row, S7 row, the proof rule); record/inc/MON1_BRIEF.md (R-MON1-1..15, Q1..Q10); record/inc/RULINGS_INC_R0.md; record/s81/PLAN_S81.md; record/s80/PLAN_S80.md section 0 and the contract-freeze rules (RULE 4: never a codeless 503); record/s81/ledger.md line 316 (the 2026-11-07 flag read of web) and the 2026-11-11 lines.
- Sister units and contracts: S81-04c (other session, in flight) edits ONLY the log statements of the LLMUnavailableError arms in app/services/extraction_service.py, app/api/image_routes.py, app/services/url_extraction_service.py: MON1 touches none of those files. S81-04c adds a CLAUDE.md block at the same anchor (after the S81-G10 block): the final round unions in merge order. CL3 (client) is disjoint. Consumed contracts: S81-06 guarded_anthropic_create / route / _classify (unchanged), W1-3b breaker classification (unchanged), S81-04 spend breaker (unchanged), the /health additive rule (main.py:628-638), the B1 capture_message precedent (sentry_service.py:671-698).
- Personal-data rule: no personal value, no real credential shape, no key-value literal in any file; every credential sentinel is built at run time by concatenation; digest constant NAMES avoid access/auth/api/credential/creds/key/password/secret/token (record digests as base64 or build at run time). Pure ASCII and LF in this file.
- Line references `file:N` are at a74caba7 (`git show a74caba7:<file>`); resolve by symbol if they move.

## 0. What the unit does

Production's OpenAI credential has been rejected (HTTP 401) for 8+ days and nothing told the owner (incident row 2). Three causes, all measured below: (1) the chokepoint records nothing an operator sees for a 401 (correct for GATING, wrong for ALERTING); (2) /health carries no LLM and no Serper state; (3) the per-call ERROR records became 48 Sentry events with no single, low-volume, clearly-named event to hang an alert rule on.

MON1 adds, without changing gating, responses or timings:
1. A stdlib-only RECORDER leaf `app/services/llm_credential_health.py`: per provider (openai, anthropic) the credential state ok / rejected / quota, classified by exception CLASS, status_code and the SDK's structured error attribute (never message text).
2. HOOKS (exception-transparent, no await, no I/O) at every provider dispatch of the web process: both branches and both success tails of `guarded_llm_create`, the except arm and success tail of `guarded_anthropic_create`, and the OpenAI moderation call in `content_safety_service.moderate_output`.
3. ONE alert-grade Sentry event per (provider, new state) per process on entering rejected / quota and one on the recovery to ok (a capture_message with a constant message, a fixed fingerprint and the tag alert=llm_credential), plus ONE event when the last healthy Serper key is found exhausted (tag alert=serper_keys).
4. Two additive /health entries (`llm_credential`, `serper_keys`), present only once this process holds an outcome, read through the `_module_snapshot` idiom (no import, no I/O, never raises).
5. A monitor path GET /health/llm: 200 while no in-use provider is rejected / quota, else 503 with an explicit code (never a bare 503).
6. A DARK active check: a lifespan task that, with ENABLE_LLM_CREDENTIAL_PROBE ON, makes ONE metadata call per in-use provider per interval (models.retrieve; no tokens) so a dead credential shows with no user traffic.

Nothing in this file says the incident is fixed. A merged MON1 is "merged, NOT yet proven" until section 8b is run on production by the relay with the owner.

## 1. Base state (measured at a74caba7)

### 1.1 The OpenAI chat chokepoint (app/services/api_budget_service.py, 1360 lines, CRLF working copy)

| What | Where | Measured fact |
|---|---|---|
| `_openai_server_answered` | :894-908 | True for any `openai.APIStatusError` with 400 <= status < 500 and != 429 (so 401 / 403 = "server answered"). |
| `_openai_failure_is_transient` | :911-935 | True for TimeoutError, RateLimitError, APIConnectionError, InternalServerError, status >= 500. False for 401 / 403. |
| Census comment | :938-956 | 13 wired dispatches; moderation (content_safety) and image Tier-3 named NOT WIRED to the BREAKER (image Tier-3 is now routed through route -> guarded_llm_create, see 1.3). |
| `guarded_llm_create` | :957-1056 | store=False prologue :991-994; spend admit :995-1000 (flag ENABLE_LLM_SPEND_BREAKER). |
| Flag-OFF branch (PRODUCTION) | :1001-1006 | `if not llm_preflight_breaker_enabled():` bare `response = await client.chat.completions.create(**kwargs)` (:1002, NO try), `record_openai_response` :1003, spend record :1004-1005, return :1006. ENABLE_LLM_PREFLIGHT_BREAKER is NOT in the ON list of the 2026-11-07 web read (ledger line 316): production runs THIS branch. |
| Flag-ON branch | :1007-1056 | admission :1007-1011; `try: create` :1012-1013; CancelledError arm :1014-1030; `except Exception as e` :1031-1043 (transient -> record_failure; probe + server answered -> record_success; probe else release); BaseException arm :1044-1050; success tail :1051-1056. |
| Module imports | :6-21 | stdlib + cache_service + openai_pricing + llm_spend_breaker (as `_llm_spend_breaker`). |

### 1.2 The Anthropic chokepoint and the router (app/services/llm_router.py, 1217 lines)

| What | Where | Measured fact |
|---|---|---|
| ROLE_FLAGS | :53-59 | ENABLE_ANTHROPIC_{TEXT,VISION,VERDICT,CRITIC,MODERATION}. None set on web (ledger line 316: every S81 flag unset). |
| Flag reader | :312-313 | `_on(name)`: `os.getenv(name, "false").strip().lower() in ("true", "1", "yes", "on")` (the house idiom). `any_role_enabled()` :329-332. |
| Key reader | :367-371 | `_anthropic_api_key()`: None when unset / blank. |
| Client memo | :279-280, :879-887 | `_anthropic_client_factory` (importlib, never a module-top import); `_client_for(key)` memoises on (sha256(key), retries). |
| `_classify` | :855-876 | (transient, status) by class + status_code. |
| `guarded_anthropic_create` | :921-1022 | key check :939-942; spend admit :943; breaker admission :944; the ONE `client.messages.create` :969 under wait_for; `except Exception as exc` :984-1001 (`transient, status = _classify(exc)` :987; logs `[ROUTER] anthropic dispatch failed site=%s class=%s status=%s transient=%s` WARNING; raises AnthropicDispatchError(type name, status, transient) from None); success tail :1002-1022. |
| `route` | :1086-1123 | role flag OFF -> `return await dispatch(client, **kwargs)` (:1089-1090). |
| SITES | :211-228 | 16 keys; "critique" has no caller since S81-G10 (15 routed call sites, below). |
| Moderation on Claude | :1138-1217 | `_moderate_once` -> guarded_anthropic_create(site="moderation") :1144; fails CLOSED. |

### 1.3 The dispatch census (Q1): every provider SDK call in the web process

`git grep` at a74caba7 over app/ for chat.completions.create, moderations.create, messages.create, embeddings, responses, images, models, files, batches, count_tokens, audio: exactly THREE SDK call statements in app/.

| # | Call | Where | Reached through | Hook |
|---|---|---|---|---|
| D1 | `client.chat.completions.create` | api_budget_service.py:1002 (flag OFF) | 15 route sites: extraction_service.py:1404 classify, :1544 parse, :1607 specs, :1766 price, :1815 price_training, :1877 reviews, :2680 verdict, :2722 verdict_fallback (`client.with_options(...)` passed in); image_service.py:187 image_tier3; openai_service.py:477 vision_v2, :649 vision_v1, :768 specs_targeted, :843 specs_synthesized, :905 disambiguate; url_extraction_service.py:960 url_extract | H1 (except) + H2 (success) |
| D2 | same | api_budget_service.py:1013 (flag ON) | same 15 sites | H3 (inside the existing except arm, first statement) + H4 (success tail) |
| D3 | `client.messages.create` | llm_router.py:969 | route (role flag ON, consent >= 3) and `_moderate_once` | H5 (except arm) + H6 (success) |
| D4 | `client.moderations.create` | content_safety_service.py:259 | `moderate_output` (L3) and `moderate_vision_output` (L4) | H7 (success after :259) + H8 (except arm :268) |

Not in the web process (out of scope, R-MON1-12): scripts/cron_compare_judge.py (messages.batches.*, messages.create :684), scripts/seed_kb_batch.py (batches), scripts/seed_spec_spine.py:381, scripts/shadow_experiments.py:999. No embeddings, files, responses or audio call exists. No raw HTTP to api.openai.com / api.anthropic.com in app/ (only llm_provider.py constants, llm_router.ANTHROPIC_BASE_URL, processors.json rows).

### 1.4 The moderation arm (app/services/content_safety_service.py, 295 lines)

`moderate_output` :234-270: try :247; router decision :251-254; inline imports of `moderation_model` and `openai_service.get_client` :256-257; `resp = await client.moderations.create(model=moderation_model(), input=text)` :259; flagged branch :260-267; `except Exception as e:` :268 -> WARNING `[content_safety] L3 moderation API failed (fail-open): %s` (:269; exception TEXT, WARNING so no Sentry event); return allowed :270. Module imports :12-18 stdlib only.

### 1.5 /health and the lifespan (app/main.py, 654 lines)

| What | Where | Measured fact |
|---|---|---|
| Middleware order | :123-182 | RequestContext (innermost), CORS, SlowAPIASGI only when `_default_rate_limits_enabled()` (flag OFF in prod), ErrorHandler, SecurityHeaders, RequestID (outermost). |
| `_module_snapshot` | :313-323 | `getattr(sys.modules.get(module_name), fn_name, None)`; `fn() or {}`; any exception -> {}. Never imports. |
| Precedent | :333-337 + brightdata_service.py:50-95 | `brightdata_auth` {last_status, at} present only after a 401/403 in this process; `_reset_brightdata_auth_state` test seam; UTC `%Y-%m-%dT%H:%M:%SZ`. |
| `health_check` | :626-649 | `{"status": "healthy", "message": "MYEZ API is running", **loop_lag_snapshot(), **price_parse_pool_snapshot(), **redis_offloop_pool_snapshot(), **adapter_executor_snapshot(), **brightdata_auth_health_snapshot(), **llm_spend_health_snapshot(), **anthropic_breaker_health_snapshot()}`. Docstring: additive only; Railway's deploy healthcheck (railway.json:8-9, healthcheckPath /health, timeout 30). |
| Heartbeat | :357-390 | `_loop_lag_heartbeat` (no exception handler, CancelledError propagates); startup `_start_loop_lag_heartbeat` :372-375; shutdown `_stop_loop_lag_heartbeat` :378-390. |
| Drain | :393-460 | 30 > 20 + 8 arithmetic comment :403-416; registered AFTER the heartbeat stop on purpose :418-419; `_drain_background_tasks` :427-460 drains only `async_utils._BACKGROUND_TASKS`. |
| Startup handlers | :190, :203, :372 | `_install_default_executor`, `_log_loop_truth`, `_start_loop_lag_heartbeat` (definition order = registration order). |
| App-level routes | :578, :586, :626 | /favicon.ico (include_in_schema=False), /, /health. |
| Client reader | SmartCompareApp/src/services/api.ts:531-534 | `healthCheck()` reads only `response.data.status === 'healthy'`. |

### 1.6 Serper key state (app/services/serper_service.py, 1397 lines)

| What | Where | Measured fact |
|---|---|---|
| Key list | :102-126 | `_resolve_serper_keys()`: SERPER_API_KEYS (comma list, trimmed, de-duplicated) else the module attr SERPER_API_KEY. Variable NAMES only here. |
| Exhaustion flag | :82, :88 | Redis `serper:exhausted:<prefix8>`, TTL 6 h. |
| In-process latch | :92, :234-241 | `_serper_exhausted_logged` (a set of prefix8, never cleared) + WARNING `SERPER_KEY_EXHAUSTED key=%s... marked exhausted (ttl=%ss); rotating to next key` (logs the 8-char PREFIX). |
| Memo | :129-215 | ENABLE_SERPER_KEY_STATE_MEMO (unset on web); `_reset_serper_key_state_memo` called per test by conftest :200. |
| `_active_serper_key` | :244-270 | 0/1 key: return it, NO exhaustion read (single-key inert). >=2 keys: first key not in `exclude` and not exhausted (one Redis read per key via `_is_serper_key_exhausted`), else None. |
| Rotation loop | :573-671 | single-key short-circuit :580-589; loop :606-665 calls `_active_serper_key(exclude=timed_out)` :626; `if not key: break` :627-630; exhaustion mark + rotate :662-664. `timed_out` is non-empty only under ENABLE_SERPER_FAIL_FAST (ON on web, ledger line 316). |
| Entry guards | :732, :948, :1061, :1174, :1206, :1251 | `if not _active_serper_key():` before each search. |

Q7 answer: production is MULTI-key (the incident log line SERPER_KEY_EXHAUSTED at 15:02:46Z is emitted only by the >=2-key branch). "No healthy key left" is observable with NO extra Redis command at the `return None` of `_active_serper_key`'s multi-key branch (:270): every key was already read there. It means "all exhausted" only when no key was skipped by `exclude`.

### 1.7 Sentry (app/services/sentry_service.py, 803 lines; sentry-sdk 2.68.1 pinned and installed)

- `init_sentry` :703-803: no DSN -> INFO and return (the SDK stays a non-recording client). `LoggingIntegration(level=logging.ERROR)` :738 (breadcrumbs and events from ERROR records only; WARNING records make neither). FastApi/Starlette `failed_request_status_codes` = 5xx minus 503 :724-733. `before_send=_before_send` :794.
- `_before_send` :510-590: drops an event whose `contexts.response.status_code == 503` :524-529; scrubs `extra`, `contexts`, `logentry`, `tags`, `user` through `_scrub_dict` :566-569 (key fragments api_key/apikey/token/secret/password redact the value; values through `_SENSITIVE_PATTERNS` :27-33: JWT, sk-proj-, fc-, 32+ hex, Bearer). Tag names alert/provider/state/status and their closed-set values pass unchanged (no fragment, no pattern match).
- Precedent `capture_result_status` :671-700: `import sentry_sdk` inside; `sentry_sdk.capture_message(_RESULT_STATUS_MESSAGE, level="info", tags=tags)`; except arm logs type name only.
- Pinned SDK (venv .venv-qaren, sentry_sdk/api.py:167-173 + scope.py:1993-2017): `capture_message(message, level=None, scope=None, **scope_kwargs)` with scope kwargs user/level/extras/contexts/tags/fingerprint/attributes. Response status context is set only on the TRANSACTION (`tracing.py:1144 set_context("response", ...)`), so a capture_message raised mid-request is not dropped by the 503 branch (LIKELY by reading; RED row SE01 measures it).

### 1.8 The pinned SDK truth (Q2; requirements.txt pins openai==3.3.1, anthropic==1.12.1; the same versions are installed in .venv-qaren)

openai 3.3.1 (`openai/_exceptions.py`, `_client.py:768-799` and :1464-1495):
- `APIStatusError(APIError)` sets `status_code = response.status_code`; `APIError.__init__` sets `code`, `param`, `type` from the body dict (`code = body.get("code")`), and `_make_status_error` passes `data = body.get("error", body)`, so `exc.code` is the structured `error.code`.
- 401 -> `AuthenticationError` (subclass `OAuthError`), 403 -> `PermissionDeniedError`, 429 -> `RateLimitError`, >= 500 -> `InternalServerError`, 400/404/409/422 their classes, else the generic `APIStatusError`. `APIConnectionError` / `APITimeoutError` carry no status. The SDK uses httpx2 (`httpx2.Response`, `httpx2.Request`) for the test doubles.
- Out of credit: OpenAI answers 429 with `error.code == "insufficient_quota"` (the code string is the server's; it is NOT a constant in the SDK: `grep -r insufficient_quota openai/` is empty). So quota = `RateLimitError` AND `getattr(exc, "code", None) == "insufficient_quota"`.

anthropic 1.12.1 (`anthropic/_exceptions.py`, `_client.py:557-586`):
- `APIStatusError` sets `status_code`, `request_id`, `workspace_id`, and `type` from `body["error"]["type"]` (`ErrorType` literal, `types/shared/error_type.py`: invalid_request_error, authentication_error, permission_error, not_found_error, rate_limit_error, timeout_error, overloaded_error, api_error, billing_error).
- 401 -> `AuthenticationError`, 403 -> `PermissionDeniedError`, 429 -> `RateLimitError`, 529 -> `OverloadedError`, >= 500 -> `InternalServerError`; NO 402 class, so a 402 is the generic `APIStatusError`.
- Out of credit: `type == "billing_error"` (the shared `BillingError` model). So quota = `APIStatusError` AND `getattr(exc, "type", None) == "billing_error"`. (A user-set spend LIMIT answers 400 invalid_request_error and the tier spend CAP answers 429 rate_limit_error with details.error_code enforced_spend_limit_reached, per the official rate-limits page, 8b/Q8; neither is classified by MON1: a stated limit, 9.)

The classification table the leaf implements (R-MON1-4):

| Provider | Exception | State |
|---|---|---|
| openai | `AuthenticationError` (401) or `PermissionDeniedError` (403), or any `APIStatusError` with status_code 401 / 403 | rejected |
| openai | `RateLimitError` with `.code == "insufficient_quota"` | quota |
| anthropic | `AuthenticationError` / `PermissionDeniedError`, or any `APIStatusError` with status_code 401 / 403 | rejected |
| anthropic | `APIStatusError` with `.type == "billing_error"` | quota |
| either | everything else (timeout, connection error, 5xx, plain 429, 400, 404, 409, 413, 422, a non-SDK exception, CancelledError never reaches the hook) | None: the state is left alone |

The leaf reaches the SDK classes with `importlib.import_module` at call time inside try (the `_sdk()` precedent, llm_router.py:848-852), so it stays stdlib-only at module top and a missing SDK classifies nothing. The s06 tests install a fake `anthropic` hierarchy (tests/test_s81_s06_anthropic_router.py:203-229); the getattr-based lookup works with it.

### 1.9 Guards the new code must not trip (each read at a74caba7)

| Guard | Where | Rule the new code follows |
|---|---|---|
| K1 AST digest of `guarded_llm_create` | tests/test_s81_s03_llm_ledger_v2.py:193, :2484-2492 | MOVES deliberately (E1, 4.1). |
| U3c chokepoint shape | tests/test_u3c_store_false_pin.py:298-377 | exactly 2 `chat.completions.create(**kwargs)` dispatches stay; `kwargs` read only via get / subscript / dispatch: the hooks never touch `kwargs`. |
| U3c SDK surface | test_u3c_store_false_pin.py:36-43, :380-421 | `.create/.parse/.stream` on chat.completions/responses/batches/wrappers, REST paths, getattr names are flagged; `client.models.retrieve` and `with_options(...)` (not followed by chat.completions) are NOT; no `client.messages` bound to a name outside llm_router, no "/v1/messages" string. |
| S81-06 R38 | test_s81_s06_anthropic_router.py:2476-2502 | exactly one `messages.create` in llm_router, inside guarded_anthropic_create; no store/temperature/metadata/extra_body keyword anywhere in llm_router. |
| S81-06 no module-top anthropic import | test_s81_s06_anthropic_router.py:693-699 | the router gains only `from app.services import llm_credential_health as _cred_health`. |
| R39b | test_s81_s06_anthropic_router.py:2547-2553 | `decide_moderation()` stays before `moderations.create` in moderate_output. |
| Model-id literal ban | tests/test_model_config.py:125-150 (app/services/*.py except model_config / openai_pricing / llm_pricing) | no `gpt-`, `claude-`, `omni-moderation-` literal: the probe reads ids from model_config. |
| U8d R8 ERROR-line AST | tests/test_sentry_channels_u8d_unit.py:773-919 (rglob app/) | the unit adds NO logger.error / exception / critical call anywhere (WARNING / INFO only). |
| Legal service scanner | tests/test_legal_docs_u8.py:820-857 | no URL literal and no client constructor (AsyncOpenAI / AsyncAnthropic / ...) in the new modules: the probe reuses `openai_service.get_client()` and `llm_router._client_for(key)`. |
| Default-limiter census | tests/test_retro_w1_9.py:382-480 | on RAILWAY_ENVIRONMENT the default limiter reaches exactly {/health, /, /favicon.ico}: the new route is decorated `@limiter.exempt` (slowapi extension.py:869-875; `_should_exempt` middleware.py:98-106). |
| Shutdown order | tests/test_shutdown_drain.py:690-743 | `_drain_background_tasks` stays AFTER `_stop_loop_lag_heartbeat`; the new stop handler sits between them. |
| /health purity | tests/test_health_loop_lag.py:190-212 | no "await ", "asyncio.sleep", "requests.", "httpx.", "get_cached", "execute(" in the handler body. |
| /health key supersets | test_retro_w0_4_efg.py:1526-1529; test_s77_redis_offloop.py:2210-2213, :2253-2256, :2274, :2287; test_s81_s04_spend_breaker.py:120-121, :1507 | these pin "no OTHER key" in the same test: both new keys are ABSENT unless this process recorded an outcome IN THAT TEST, and conftest resets the state per test (3.5). No E-row. |
| No top-level "code" in /health | tests/test_error_middleware.py:93-101 | the entries are nested dicts; /health keeps no top-level code. |
| U13 route inventory | tests/test_s71_u13_compare_auth_required.py:562-599 + its OpenAPI snapshot :448-460 (ten operations + components) | the route carries no require_paid_route_* dependency and `include_in_schema=False`. |
| loop_lag namespace | tests/test_retro_w1_7_w1_10.py:115 | no new main.py global starts with `_loop_lag`. |
| Black ratchet | .github/black-clean-paths.txt; test_s81_s05_request_context.py:1291-1303 precedent | the two new app modules and the RED files join the ratchet (3.10). |

Libraries: stdlib only in the leaf; the probe uses the installed openai / anthropic SDKs through the existing clients; no new dependency. Line endings: every touched tracked file is `i/lf w/crlf` (`git ls-files --eol`); the Edit tool keeps CRLF; new files are written LF in the index (autocrlf) and a whole-file diff is a defect.

### 1.10 Base pass state of the touched files (ALL DEFERRED TO RED: this round ran no test)

Runner prefix (P): `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound <s> --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-mon1 --log <SP>/MON1/red/<tag>.log --tag <tag> --`

| Gate | Command | State |
|---|---|---|
| B1 the direct readers of the edited modules | P --bound 1200 --tag inc-mon1-base-direct -- tests/test_api_budget_service.py tests/test_openai_breaker.py tests/test_retro_w1_3.py tests/test_m13_31_half_open_probe.py tests/test_s81_s04_spend_breaker.py tests/test_s81_s03_llm_ledger_v2.py tests/test_u3c_store_false_pin.py tests/test_s81_s06_anthropic_router.py tests/test_s81_s06_router_gate_rows.py tests/test_content_safety_service.py | DEFERRED TO RED |
| B2 /health, lifespan, limiter, shutdown | P --bound 1200 --tag inc-mon1-base-health -- tests/test_health_loop_lag.py tests/test_health_brand_s69.py tests/test_retro_w1_7_w1_10.py tests/test_retro_w1_9.py tests/test_retro_w0_4_efg.py tests/test_s77_redis_offloop.py tests/test_s75_fanout_starve.py tests/test_error_middleware.py tests/test_security_hardening.py tests/test_shutdown_drain.py tests/test_s81_s24_auth_throttle.py tests/test_s81_s24_gate_rows.py tests/test_s81_st1_usage_path_offloop.py | DEFERRED TO RED |
| B3 Serper + Sentry | P --bound 1200 --tag inc-mon1-base-serper -- tests/test_serper_multikey_failover.py tests/test_s78_serper_key_memo.py tests/test_serper_fail_fast.py tests/test_serper_budget_gate.py tests/test_sentry_channels_u8d_unit.py tests/test_admin_key_and_sentry_scrub.py tests/test_retro_w1_1.py tests/test_security_regression.py tests/test_auth_error_log_hygiene.py | DEFERRED TO RED |
| B4 the source scanners | P --bound 1200 --tag inc-mon1-base-scan -- tests/test_model_config.py tests/test_model_config_enforced.py tests/test_prompt_fence.py tests/test_migration_index_predicate_immutability.py tests/test_openai_key_log_hygiene_s69.py tests/test_legal_docs_u8.py tests/test_s71_u13_compare_auth_required.py tests/test_route_introspection.py tests/test_s81_s05_request_context.py tests/test_ci_gates.py | DEFERRED TO RED |
| B5 the RED files at base (must fail on AssertionError only) | P --bound 600 --tag inc-mon1-red-base -- tests/test_inc_mon1_credential_health.py tests/test_inc_mon1_probe.py | DEFERRED TO RED |

The stored base record harness/base_records/a74caba7.../0a224f48... (375 members, the S81-04c set) is reusable PER FILE (LC-6 / GC-9) for its members; the rest of the comm set (7.2) is run at a74caba7 by the RED agent. Known base noise: tests/test_prompt_truth.py two ERROR nodes (cold tiktoken); tests/test_s80_url_mode_v2.py::test_deadline_yields_timeout_503[POST] a wall-clock flake under load (observed in that record).

## 2. Contract

### 2.1 Flags and knobs (all read per call / per tick; nothing at import)

| Name | Type | Default | Read where | Parse |
|---|---|---|---|---|
| ENABLE_LLM_CREDENTIAL_PROBE | flag | OFF | the FIRST statement of every probe tick (`probe_enabled()`) | `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")` |
| LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS | float knob | 900.0 | after each tick, to sleep | unset / unparsable / inf / nan / <= 0 -> 900.0; 0 < v < 300 -> 300.0 (floor); else v |

No other variable is added. The passive part has NO flag (R-MON1-1 a). No credential-bearing name is added (the probe reuses OPENAI_API_KEY via `openai_service.get_client()` and ANTHROPIC_API_KEY via `llm_router._anthropic_api_key()`), so tests/_env_safety.py is unchanged (R-MON1-14; measured at :110-157: ANTHROPIC_API_KEY is in CREDENTIALS_UNSET (S81-06 R35) and OPENAI_API_KEY is in CREDENTIAL_PLACEHOLDERS with an unusable placeholder, so in every test OPENAI_API_KEY is PRESENT and `providers_in_use()` includes openai; RED row Y01 pins the env names the two new modules read).

### 2.2 The leaf `app/services/llm_credential_health.py` (NEW; stdlib only: logging, threading, importlib, sys, os, datetime; no `app.` import)

Constants: `PROVIDERS = ("openai", "anthropic")`; `STATES = ("ok", "rejected", "quota")`; `SOURCES = ("dispatch", "probe", "moderation")`; `ALERT_LLM = "llm_credential"`; `ALERT_SERPER = "serper_keys"`; `_LOCK = threading.Lock()`; `_STATE: dict` provider -> record; `_ALERTED: set` of (kind, provider, state).

| Function | Signature | Contract |
|---|---|---|
| `classify` | `(provider: str, exc: BaseException) -> Optional[Tuple[str, Optional[int]]]` | the 1.8 table; returns (state, status) or None; reads only `type(exc)`, `status_code`, `code` (openai), `type` (anthropic) through getattr; never `str(exc)`, `exc.args`, `exc.message`, `exc.body`; never raises. |
| `note_failure` | `(provider: str, exc: BaseException, source: str) -> None` | classify; None -> no-op; else `_transition(provider, state, status, source)`. Unknown provider / source -> no-op. Never raises (one try around the body; the except arm does nothing but `pass`). |
| `note_success` | `(provider: str, source: str) -> None` | `_transition(provider, "ok", None, source)`. Never raises. |
| `_transition` | internal | under `_LOCK`: prev = record state or None; record = {"state", "last_status" (int or None), "at" (UTC `%Y-%m-%dT%H:%M:%SZ`), "source", "count" (prev count + 1 when the state repeats, else 1)}; outside the lock: when prev != new, ONE WARNING (2.4 L1); and the event decision (2.5). |
| `health_snapshot` | `() -> dict` | `{}` while `_STATE` is empty, else `{"llm_credential": {provider: dict(record) ...}}` (copies; providers in PROVIDERS order). Pure read. |
| `providers_in_use` | `() -> Tuple[str, ...]` | "openai" when OPENAI_API_KEY is set and non-blank (presence only; the value is never stored, compared or logged); "anthropic" when ANTHROPIC_API_KEY is set and non-blank AND `any_role_enabled()` of `sys.modules["app.services.llm_router"]` is True (read through getattr on sys.modules; module absent or raising -> not in use). Env reads only. |
| `monitor_view` | `() -> Tuple[int, dict]` | 2.6. Pure: env reads + a dict read. |
| `emit_alert` | `(kind: str, provider: str, state: str, status: Optional[int]) -> None` | once per (kind, provider, state) per process (`_ALERTED` latch under `_LOCK`); calls `getattr(sys.modules.get("app.services.sentry_service"), "capture_credential_alert", None)` when present; any exception swallowed. Used by the leaf and by serper_service. |
| `_reset_credential_health_state` | `() -> None` | test seam: clears `_STATE` and `_ALERTED` (conftest calls it per test, 3.5). |

### 2.3 The hooks (exact statements; each is exception-transparent: the same exception object propagates, no added await, no added I/O, the same return value)

- H1 api_budget_service.py flag-OFF branch: `response = await client.chat.completions.create(**kwargs)` (:1002) becomes `try: <same statement>` / `except Exception as e:  # noqa: BLE001 -- MON1: note, re-raise unchanged` / `_cred_health.note_failure("openai", e, "dispatch")` / `raise`. CancelledError and other BaseException are not caught (no change).
- H2 directly after that try (before `record_openai_response`, :1003): `_cred_health.note_success("openai", "dispatch")`.
- H3 flag-ON `except Exception as e:` arm (:1031): a NEW first statement `_cred_health.note_failure("openai", e, "dispatch")`; the existing classification lines :1032-1043 stay byte-identical below it.
- H4 flag-ON success tail: `_cred_health.note_success("openai", "dispatch")` directly after the try statement (before `record_openai_response`, :1051).
- Import: `from app.services import llm_credential_health as _cred_health` beside the `_llm_spend_breaker` import (:21).
- H5 llm_router.py except arm (:984-1001): after `transient, status = _classify(exc)` (:987) a new statement `_cred_health.note_failure("anthropic", exc, "moderation" if site == "moderation" else "dispatch")`. The breaker writes, the WARNING and the `raise AnthropicDispatchError(...) from None` stay byte-identical.
- H6 llm_router.py success: directly after the `try/except` statement (before `latency_ms = ...`, :1002): `_cred_health.note_success("anthropic", "moderation" if site == "moderation" else "dispatch")`. Import beside :45-49.
- H7 content_safety_service.py: directly after :259 `resp = await client.moderations.create(...)`: `_cred_health.note_success("openai", "moderation")`.
- H8 content_safety_service.py except arm :268: a new first statement `_cred_health.note_failure("openai", e, "moderation")` before the existing WARNING (:269, unchanged). The fail-open return is unchanged. An exception from the Claude branch or the router reaches this arm too; it is not an openai SDK class, so classify returns None (no state change). Import at module top (:12-18 block).
- H9 serper_service.py `_active_serper_key` multi-key branch (:265-270): the loop tracks `skipped = True` when a key is skipped by `exclude`; before `return key` (:269) `_note_serper_selection(len(keys), keys, False)`; before `return None` (:270) `_note_serper_selection(len(keys), keys, not skipped)`. The 0/1-key branch (:262-264) is untouched (single-key inert). No Redis command is added (the Redis reads are the existing `_is_serper_key_exhausted` calls).

NOT touched: `_openai_server_answered`, `_openai_failure_is_transient`, the breaker functions, `_openai_dispatch_admission`, `llm_router._classify`, `route`, `_moderate_*`, `moderate_with_claude`, every route site, extraction_service.py, image_routes.py, url_extraction_service.py (the S81-04c footprint).

### 2.4 Log lines (constants, closed-set names and ints only; WARNING / INFO only; never an exception text, header, URL, key, prefix or model output)

| Id | Level | Template | When |
|---|---|---|---|
| L1 | WARNING | `[LLM_CREDENTIAL] provider=%s state=%s status=%s source=%s` (status an int or the word none) | every state CHANGE of a provider (not on repeats) |
| L2 | WARNING | `[SERPER_KEYS] no healthy key left configured=%d` | the transition of `none_left` False -> True |
| L3 | INFO | `[SERPER_KEYS] a healthy key is available again configured=%d` | the transition True -> False |
| L4 | INFO | `[LLM_PROBE] provider=%s outcome=%s class=%s ms=%d` (outcome in ok / rejected / quota / inconclusive / unavailable; class a type name or the word none) | one per provider per ON tick |
| L5 | WARNING | `[LLM_PROBE] tick failed class=%s` | an unexpected exception inside a tick (the task survives) |
| L6 | WARNING | `[LLM_CREDENTIAL] alert skipped: %s` (type name) | inside `capture_credential_alert` when the SDK call raises |

An L1 WARNING is NOT a Sentry event and not a breadcrumb (LoggingIntegration level ERROR, 1.7), so the alert event is never doubled (R-MON1-6).

### 2.5 The alert event (sentry_service.capture_credential_alert, NEW, beside capture_result_status)

`capture_credential_alert(kind: str, provider: str, state: str, status: Optional[int]) -> None`: `import sentry_sdk` inside; `sentry_sdk.capture_message(_CREDENTIAL_ALERT_MESSAGE, level=("info" if state == "ok" else "error"), tags={"alert": kind, "provider": provider, "state": state, "status": str(status) if isinstance(status, int) else "none"}, fingerprint=[kind, provider, state])`; except -> L6. `_CREDENTIAL_ALERT_MESSAGE = "credential_state"` (a constant; the tags carry everything). No exception text, no request data, no extras.

Emission rules (in the leaf, `emit_alert`, latched per process): kind llm_credential: on a transition INTO rejected or quota (once per (provider, state)), and on a transition from rejected / quota INTO ok (once per provider: the recovery event). A first-ever ok (no prior failure) emits nothing. kind serper_keys: once, on the none_left False -> True transition, provider "serper", state "exhausted", status None. With SENTRY_DSN unset the call is a no-op (the non-recording client) and the L1 / L2 line remains. The 503 drop in `_before_send` does not apply (the event carries no response context, 1.7). Level error is what an owner-side "issue alert" filtered on the tag alert matches by default; the recovery event is info.

### 2.6 The monitor path GET /health/llm (R-MON1-8; owner ruling O2 pending, default IN)

Registered in app/main.py right after `health_check`: `@app.get("/health/llm", include_in_schema=False)` over `@limiter.exempt` over `async def llm_credential_health():`. The handler body: `status_code, body = _llm_credential_monitor_view()` and `return JSONResponse(status_code=status_code, content=body)` where `_llm_credential_monitor_view()` reads `sys.modules.get("app.services.llm_credential_health").monitor_view` with a try (module absent or raising -> (200, {"status": "ok", "providers": {}})). No await, no I/O, no HTTPException.

| Condition (in-use providers only, 2.2) | HTTP | Body |
|---|---|---|
| no in-use provider is rejected or quota | 200 | `{"status": "ok", "providers": {"<p>": "ok" or "unknown"}}` (unknown = in use, no outcome yet in this process) |
| any in-use provider is rejected or quota | 503 | `{"status": "degraded", "code": "LLM_CREDENTIAL_UNUSABLE", "providers": {"<p>": "<state>"}}` |

The 503 is a returned JSONResponse with an explicit `code`, so the ErrorHandler STATUS_CODE_MAP (error_handler.py:24-34, codeless 503 -> FEATURE_DISABLED) never applies. No client bundle reads this path (contract RULE 4 is about client-read codes; `LLM_CREDENTIAL_UNUSABLE` is read only by an uptime monitor). A 503 from it is not a Sentry event (the integrations exclude 503 and `_before_send` drops it). Middleware met (Q5): RequestID (generates an id; the HOP probe line is only for HOP_PROBE_PATHS = ("/health", "/api/v1/app/version"), request_id.py:14/:80, exact match), SecurityHeaders (adds headers; its /admin/ branch does not match), ErrorHandler (not entered: no exception), CORS, RequestContext (flag-gated per call). SlowAPIASGI is absent in production and the route is `limiter.exempt` anyway. No auth dependency: the path is public like /health and carries only closed-set words. GET only (a HEAD answers 405: 9 L-7).

### 2.7 The /health entries (R-MON1-7)

`health_check` gains, at the END of its dict, `**llm_credential_health_snapshot(), **serper_keys_health_snapshot()`, two new module functions beside `anthropic_breaker_health_snapshot`:
- `llm_credential_health_snapshot()` -> `_module_snapshot("app.services.llm_credential_health", "health_snapshot")` -> `{"llm_credential": {"openai": {"state": "rejected", "last_status": 401, "at": "2026-11-11T15:02:57Z", "source": "dispatch", "count": 23}}}` (example values) or {}.
- `serper_keys_health_snapshot()` -> `_module_snapshot("app.services.serper_service", "serper_keys_snapshot")` -> `{"serper_keys": {"configured": 2, "marked_exhausted": 1, "none_left": false, "at": "..."}}` or {}.
`status`, `message`, the 200 and every existing entry are byte-identical. A process that has made no LLM call and no multi-key Serper selection shows neither key (Q10, 11).

### 2.8 Serper key state (serper_service.py, H9)

Module state `_serper_keys_state: Optional[dict] = None` and `_serper_keys_lock = threading.Lock()`. `_note_serper_selection(configured: int, keys: list, none_left: bool)`: under the lock writes `{"configured": configured, "marked_exhausted": <count of keys whose prefix8 is in _serper_exhausted_logged>, "none_left": none_left, "at": <UTC Z>}`; outside the lock L2 + `_cred_health.emit_alert("serper_keys", "serper", "exhausted", None)` on False -> True, L3 on True -> False; never raises. `serper_keys_snapshot()` -> `{"serper_keys": dict(state)}` or {}. `_reset_serper_keys_state()` test seam. The snapshot holds COUNTS only: never a key, a prefix or an index. `marked_exhausted` counts marks made by THIS process since start (`_serper_exhausted_logged` never decays, while the Redis flag lives 6 h): named as such in the CLAUDE.md row (9 L-5).

### 2.9 The active check (DARK; R-MON1-9 / R-MON1-10) - NEW module `app/services/llm_credential_probe.py`

Top-level imports: stdlib (asyncio, logging, math, os, time) + `from app.services import llm_credential_health as _cred_health`. Provider modules are imported INSIDE functions (openai_service, llm_router, model_config), never at top. Constants: `FLAG = "ENABLE_LLM_CREDENTIAL_PROBE"`, `INTERVAL_ENV = "LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS"`, `DEFAULT_INTERVAL_SECONDS = 900.0`, `MIN_INTERVAL_SECONDS = 300.0`, `FIRST_DELAY_SECONDS = 20.0` (<= 30, R-MON1-9), `CALL_TIMEOUT_SECONDS = 5.0`.

| Function | Contract |
|---|---|
| `probe_enabled()` | the house idiom on FLAG. |
| `probe_interval()` | 2.1 parse. |
| `async probe_once()` | for each provider in `_cred_health.providers_in_use()`: one call (below) under `asyncio.wait_for(..., CALL_TIMEOUT_SECONDS)`, never retried; 2xx -> `note_success(p, "probe")`; an exception -> `note_failure(p, exc, "probe")` (transient classes change nothing); one L4 line per provider. Returns {provider: outcome}. |
| openai call | `openai_service.get_client().with_options(max_retries=0, timeout=CALL_TIMEOUT_SECONDS).models.retrieve(model_config.standard_model())` (GET /v1/models/{model}; the SDK's own path; `with_options` copies the client and shares its HTTP pool). A client construction error (no key) -> outcome unavailable, no state change. |
| anthropic call | `key = llm_router._anthropic_api_key()`; None -> skip; `llm_router._client_for(key).with_options(max_retries=0, timeout=CALL_TIMEOUT_SECONDS).models.retrieve(model_config.anthropic_model("text"))` (GET /v1/models/{model_id}). |
| `async run_forever()` | `await asyncio.sleep(FIRST_DELAY_SECONDS)`; loop: `if probe_enabled(): try: await probe_once() except asyncio.CancelledError: raise except Exception as exc: L5`; `await asyncio.sleep(probe_interval())`. CancelledError always propagates. |

Lifespan in app/main.py: `_llm_probe_task = None`; `@app.on_event("startup") async def _start_llm_credential_probe()` defined directly after `_start_loop_lag_heartbeat` (imports the probe module inside, `asyncio.create_task(_probe.run_forever(), name="llm_credential_probe")`); `@app.on_event("shutdown") async def _stop_llm_credential_probe()` defined directly after `_stop_loop_lag_heartbeat` and before `_drain_background_tasks` (cancel, await, suppress CancelledError at the canceller, set None). The task is NOT a fire_and_forget registry task, so the drain never waits on it.

Q6 drain arithmetic: unchanged. The new stop handler cancels a task that is either sleeping or inside one `wait_for(..., 5 s)`: cancellation ends it within one loop turn, so it adds ~0 s before the 8 s DRAIN_TIMEOUT; 30 > 20 + 8 holds. Not in any cron / script process (only app.main registers it). No spend admit, no usage-ledger record, no breaker admission (it is not a completion); no user data in the request (a model id only); no new host (api.openai.com and api.anthropic.com are processors of record: processors.json:70 and :266, so processors.json and the R22 row-set fixture are unchanged). With `OPENAI_BASE_URL` pointing at a non-OpenAI gateway the retrieve may be unsupported: outcome inconclusive, no state change (9 L-8).

### 2.10 Failure table

| Failure | Behaviour |
|---|---|
| The leaf raises inside a hook (a bug) | impossible by contract: note_* wrap their body in try/except Exception: pass; the caller's exception / return value is untouched (RED rows L07, H01). |
| SDK not importable | classify returns None: no state change. |
| An exception whose `status_code` / `code` / `type` getattr raises | caught inside classify: None. |
| /health snapshot function raises or the module is absent | `_module_snapshot` -> {} (the key is absent, /health stays 200). |
| /health/llm view raises | 200 {"status": "ok", "providers": {}} (fail-open: a monitor bug must not page the owner; stated limit 9 L-9). |
| SENTRY_DSN unset | capture is a no-op; L1/L2 lines remain. |
| sentry capture_message raises | L6 WARNING with the type name; the hook returns normally. |
| Probe: provider key absent | the provider is not in use (openai) or skipped (anthropic): no call. |
| Probe: retrieve times out (5 s) / connection error / 5xx / 429 / 404 | outcome inconclusive, no state change, never retried in the tick. |
| Probe: 401 / 403 / quota | state rejected / quota with source probe; the event rules of 2.5 apply. |
| Probe: anything else raises inside a tick | L5, the task keeps running. |
| Shutdown during a probe call | the task is cancelled; CancelledError propagates; the stop handler suppresses it at the canceller. |
| Flapping 401 / ok (e.g. a model-specific 403) | the state follows the last outcome; L1 logs each change; the event latch bounds events to 3 per provider per process (9 L-3). |

### 2.11 The flag-OFF identity and the EXACT deploy-visible delta (the main invariant)

With ENABLE_LLM_CREDENTIAL_PROBE at its default (OFF) and every other flag as in production, deploying MON1 changes EXACTLY this, and nothing else:
1. /health gains `llm_credential` once the process has seen one OpenAI / Anthropic outcome (the first compare after the deploy), and `serper_keys` once it has made one multi-key Serper selection. Every existing key, `status`, `message` and the 200 are unchanged.
2. A new unauthenticated GET /health/llm (200 or 503 JSON; not in the OpenAPI schema; not rate-limited).
3. Sentry: one error-level event `credential_state` tagged alert=llm_credential provider=openai state=rejected status=401 the first time an OpenAI call is rejected in a process (with today's dead credential: on the first compare after each deploy / restart), one info-level recovery event when a call succeeds after that, one more per (provider, state) at most per process; one error-level event tagged alert=serper_keys when every Serper key is found exhausted (once per process).
4. Logs: one WARNING L1 per credential state change; L2 / L3 on the Serper none-left transitions.
5. One idle asyncio task in the web process (created at startup, cancelled at shutdown) that wakes 20 s after startup and then every 900 s and reads two environment variables; with the flag OFF it builds no client and makes no I/O.
6. On the hot path: per LLM call outcome one lock + one small dict write (microseconds); one more try frame around the production create; per multi-key Serper selection one lock + one dict write. No added await, Redis command or network call.
The compare / camera / URL responses, the gating (breakers, admissions, spend breaker), the timings beyond those microseconds, the stream frames and every client-read key are byte-identical. PIN rows G01-G03, H01-H02, S04-S05 measure this with the FULL configuration (B1 rule).

With ENABLE_LLM_CREDENTIAL_PROBE ON (its own canary window, O3): per in-use provider one GET /v1/models/{model} every interval (96 a day per provider at 900 s), plus the first one 20 s after each start.

### 2.12 Test seams (production values in brackets)

`llm_credential_health._reset_credential_health_state()`; `llm_credential_health._LOCK` / `_STATE` / `_ALERTED` [module globals]; `sentry_service.capture_credential_alert` [looked up through sys.modules at call time, so a test monkeypatches the attribute]; `serper_service._reset_serper_keys_state()`; `llm_credential_probe.FIRST_DELAY_SECONDS` [20.0], `CALL_TIMEOUT_SECONDS` [5.0], `DEFAULT_INTERVAL_SECONDS` [900.0], `MIN_INTERVAL_SECONDS` [300.0] read as module globals at call time; `llm_credential_probe.probe_once` [the real one] patchable from run_forever; `openai_service.get_client` and `llm_router._client_for` / `_anthropic_api_key` [the real factories] patched with fakes whose `with_options(...)` returns an object whose `models.retrieve` records (model, options) and returns / raises; `app.main._llm_probe_task` [None before startup].

## 3. Change list (the order GREEN applies it)

3.0 Byte copies first: shutil.copyfile of every file in 3.1-3.11 that exists at base into <SP>/MON1/green/base_copies/ with sha256 recorded; `git status --short` empty before; the RED files are frozen (sha256 from the RED gate) and never edited by GREEN.
3.1 NEW app/services/llm_credential_health.py (2.2, 2.4 L1, 2.5 rules). Stdlib-only top-level imports; no URL, no model-id literal, no client constructor, no logger.error.
3.2 EDIT app/services/sentry_service.py: `_CREDENTIAL_ALERT_MESSAGE = "credential_state"` and `capture_credential_alert(...)` directly after `capture_result_status` (:671-700). Nothing else in the file.
3.3 EDIT app/services/api_budget_service.py: the import (:21 block) and H1-H4 (2.3). Optionally one line appended to the census comment (:938-956) naming MON1's observer hooks (comment only; no AST effect outside guarded_llm_create). Nothing else.
3.4 EDIT app/services/llm_router.py: the import (:45-49 block), H5, H6. Nothing else.
3.5 EDIT tests/conftest.py: one NEW autouse fixture `_reset_credential_health_state` after `_reset_serper_budget_gate_memo` (:183-201), import-guarded like it, calling `llm_credential_health._reset_credential_health_state()` and `serper_service._reset_serper_keys_state()` before each test. (Needed: an earlier test that raises a real AuthenticationError through a chokepoint would otherwise leave `llm_credential` on every later /health body and redden the three superset pins of 1.9.)
3.6 EDIT app/services/content_safety_service.py: the import, H7, H8. Nothing else.
3.7 EDIT app/services/serper_service.py: the import of the leaf, the state + lock + `_note_serper_selection` + `serper_keys_snapshot` + `_reset_serper_keys_state` (after `_mark_serper_key_exhausted`, :218-241), H9 in `_active_serper_key` (:265-270). The 0/1-key branch, `_serper_post_impl`, `_mark_serper_key_exhausted` and the entry guards are untouched.
3.8 NEW app/services/llm_credential_probe.py (2.9).
3.9 EDIT app/main.py: `from fastapi.responses import JSONResponse` (beside the existing fastapi import, :6); the two snapshot functions after `anthropic_breaker_health_snapshot` (:349-354); `_llm_probe_task` + `_start_llm_credential_probe` after `_start_loop_lag_heartbeat` (:372-375); `_stop_llm_credential_probe` after `_stop_loop_lag_heartbeat` (:378-390), BEFORE the DRAIN comment block (:393); the two `**...()` entries at the END of the `health_check` dict (:648); the monitor route + `_llm_credential_monitor_view` after `health_check` (:649). The `health_check` docstring gains one sentence naming the two entries (additive).
3.10 EDIT .github/black-clean-paths.txt: append app/services/llm_credential_health.py, app/services/llm_credential_probe.py, tests/test_inc_mon1_credential_health.py, tests/test_inc_mon1_probe.py (the D03 F1-7 / S81-05 R-S05-8 precedent; the files are black-clean when written).
3.11 EDIT tests/test_s81_s03_llm_ledger_v2.py: E1 only (4.1).
3.12 EDIT CLAUDE.md: the MON1 block after the S81-G10 block (before `## Tests`, CLAUDE_md_a74caba7.txt:630-637) and one sentence appended to the :341 Feature Flags pointer clause (8.1).
No other file. In particular: no client file, no migration, no processors.json, no requirements file, no extraction_service.py / image_routes.py / url_extraction_service.py (S81-04c), no tests/_env_safety.py, no RED file.

## 4. Existing pins

### 4.1 Pins that change deliberately (E-rows)

| E | File:line | Change | Reason |
|---|---|---|---|
| E1 | tests/test_s81_s03_llm_ledger_v2.py:193 `K1_GUARDED_AST_SHA` (+ the docstring of test_k1 :2485-2486) | re-record the sha256 of `ast.dump(guarded_llm_create, include_attributes=False)` on CPython 3.12 at the GREEN bytes, written as the same two-piece concatenation; the docstring gains "re-recorded by MON1 for the credential-health hooks H1-H4 (the S81-04 precedent)". | H1-H4 edit the function body by ruling (R-MON1-5). The constant's NAME has no scanner keyword (K1_GUARDED_AST_SHA): unchanged. |

No other pin moves by design. If the RED or GREEN gate finds another red pin, it is an E-row for the orchestrator's ruling, never a weakened pin.

### 4.2 Pins that must stay green and unedited (named; the whole comm set 7.2 is the arbiter)

- Gating: tests/test_retro_w1_3.py (W1-3a/b: a 401 records no failure; half-open probe closes on a 4xx), tests/test_openai_breaker.py, tests/test_m13_31_half_open_probe.py, tests/test_api_budget_service.py, tests/test_s81_s04_spend_breaker.py (r37 wiring: one admit, two `record_openai_response_soon`, admit before the W1-3 admission), tests/test_s81_s06_anthropic_router.py (R16f/R16g classification, R38, R39, R39b, the no-module-top-anthropic rule), tests/test_s81_s06_router_gate_rows.py (G04 anthropic_breaker presence; the direct-guarded-call walker).
- Chokepoint shape: tests/test_u3c_store_false_pin.py (u3c_01, 01b, 01c, 02, 03, 04, 05-22).
- /health: tests/test_health_loop_lag.py (additive pin :173-187, purity pin :190-212, lifespan :313-350), tests/test_health_brand_s69.py, tests/test_retro_w1_7_w1_10.py, tests/test_retro_w0_4_efg.py:1495-1533, tests/test_s77_redis_offloop.py RO18 rows, tests/test_s75_fanout_starve.py:512-542, tests/test_s81_s04_spend_breaker.py R33-R36, tests/test_s81_st1_usage_path_offloop.py R26, tests/test_error_middleware.py:93-101, tests/test_security_hardening.py:201-236, tests/test_s81_s24_auth_throttle.py /health rows.
- Routes / limiter / schema: tests/test_retro_w1_9.py (the three-route census :473-480), tests/test_s71_u13_compare_auth_required.py (T05 inventory, the OpenAPI snapshot fixture), tests/test_m13_21_openapi_gated.py, tests/test_route_introspection.py.
- Shutdown: tests/test_shutdown_drain.py (order :718-743, the 30 > 20 + 8 arithmetic).
- Serper: tests/test_serper_multikey_failover.py, tests/test_s78_serper_key_memo.py, tests/test_serper_fail_fast.py, tests/test_serper_budget_gate.py.
- Sentry / secrets: tests/test_sentry_channels_u8d_unit.py (R8 AST: no new ERROR line), tests/test_admin_key_and_sentry_scrub.py, tests/test_retro_w1_1.py, tests/test_security_regression.py, tests/test_auth_error_log_hygiene.py, tests/test_openai_key_log_hygiene_s69.py.
- Source scanners: tests/test_model_config.py, tests/test_model_config_enforced.py, tests/test_prompt_fence.py, tests/test_migration_index_predicate_immutability.py, tests/test_legal_docs_u8.py, tests/test_s81_s05_request_context.py (the ctx-reader allowlist: the new modules read no request_context), tests/test_s81_kb_schema.py (IDENTITY_NODES: tests/test_s75_fanout_identity.py and its fixture stay byte-identical; MON1 adds no UNIT_ENV entry, see 11 OQ-4).
- CLAUDE.md readers by the import graph: tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py, tests/test_s81_s04_spend_breaker.py, tests/test_s81_s08b_legacy_fingerprint.py (R11: one Feature Flags paragraph), tests/test_s81_s08b_gate_rows.py, tests/test_s81_s23_bypass_retire.py.

## 5. RED tests (hermetic; two files; each RED row fails at base on an AssertionError ONLY: a missing module or symbol is read with importlib.util.find_spec / getattr helpers and asserted, never imported bare)

Files: tests/test_inc_mon1_credential_health.py (rows L, H, G, HE, S, M, SE, Y) and tests/test_inc_mon1_probe.py (rows P). Every credential-shaped sentinel is built at run time by concatenation; a test that sets a credential variable imports app.main first (autouse fixture), then monkeypatch.setenv (the dotenv guard). Real SDK exception objects are built from the pinned classes with `httpx2.Request("GET", "https://example.invalid/v1/x")` / `httpx2.Response(<status>, request=..., json=<body>)`; the message string carries an SDK_SENTINEL built at run time. FULL configuration (the B1 rule) = ENABLE_LLM_PREFLIGHT_BREAKER and ENABLE_LLM_SPEND_BREAKER in the row's state, every LLM_SPEND_* knob set to a synthetic value, ENABLE_ANTHROPIC_TEXT / _MODERATION ON for the anthropic rows with consent 3, ANTHROPIC_API_KEY and SERPER_API_KEYS sentinels, ENABLE_LLM_CREDENTIAL_PROBE OFF and LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS set, plus call / order recorders on openai_record_failure / openai_record_success / openai_release_half_open_probe / record_openai_response / record_openai_response_soon / abs_.record_failure / abs_.record_success / capture_credential_alert.

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| L01 | leaf exists, import rule | find_spec("app.services.llm_credential_health") not None; AST: top-level imports stdlib only, no `app.` import, no URL / model-id literal, no logger.error | RED (spec None) | 3.1 |
| L02 | openai classify (real classes) | 401 / 403 / generic APIStatusError 401 -> rejected; RateLimitError code insufficient_quota -> quota; plain RateLimitError, BadRequestError whose MESSAGE says "invalid_api_key 401", NotFoundError, InternalServerError, APITimeoutError, APIConnectionError, asyncio.TimeoutError, ValueError -> None | RED | 3.1 |
| L03 | anthropic classify (real classes) | Authentication / PermissionDenied -> rejected; APIStatusError 402 type billing_error -> quota; RateLimitError, OverloadedError, BadRequestError with message "credit balance is too low" -> None | RED | 3.1 |
| L04 | record shape | after note_failure: snapshot == {"llm_credential": {"openai": {state, last_status 401, at ISO-Z regex, source dispatch, count 1}}}; a repeat -> count 2; a change -> count 1 | RED | 3.1 |
| L05 | recovery | rejected then note_success -> state ok, last_status None | RED | 3.1 |
| L06 | empty / reset | snapshot {} before any outcome and after `_reset_credential_health_state()` | RED | 3.1 |
| L07 | never raises | an exception object whose getattr of status_code raises; provider "x"; source "y"; a leaf whose emit path raises -> each call returns None, state unchanged where invalid | RED | 3.1 |
| L08 | the event latch (recorder on sentry_service.capture_credential_alert) | sequence: 3 x 401, ok, 401, quota, ok -> calls exactly [(llm_credential, openai, rejected, 401), (llm_credential, openai, ok, None), (llm_credential, openai, quota, 429)] (the second ok is latched: no fourth call) | RED | 3.1 + 3.2 |
| L09 | no event on a first ok | note_success first -> zero calls | RED (symbol missing) | 3.1 |
| L10 | L1 line | caplog: exactly one WARNING per change, full-match the 2.4 L1 template as a full-match regex (provider, state, status, source each from its closed set; status three digits or none); no record (message + repr(args)) contains SDK_SENTINEL or the key sentinel | RED | 3.1 |

| H01 | flag OFF 401 (FULL config, preflight OFF, spend OFF and ON as two params) | `guarded_llm_create(fake_client, **kw)` raises the SAME AuthenticationError object (`is`); state openai rejected 401 dispatch; breaker recorders all zero; record_openai_response zero; record_openai_response_soon zero | RED | 3.3 H1 |
| H02 | flag OFF success | returns the exact fake response object; state ok; record_openai_response once AFTER the create; spend ON: record_openai_response_soon once; no breaker call | RED (no state) | 3.3 H2 |
| H03 | flag ON 401 (preflight ON, the Redis fake; non-probe and half-open-probe params) | same exception object; state rejected; non-probe: zero record_failure / record_success / release; probe: record_success exactly once (W1-3b unchanged) | RED | 3.3 H3 |
| H04 | flag ON success | state ok; record_success once iff outcome_matters (both params) | RED | 3.3 H4 |
| H05 | transient (plain RateLimitError, APITimeoutError, InternalServerError), flag OFF and ON | snapshot {} (asserted through the API, which must exist); flag ON: record_failure exactly once (unchanged) | RED (API missing) | 3.3 |
| H06 | CancelledError, flag OFF and ON | CancelledError propagates; snapshot {}; probe param: release once | RED (API missing) | 3.3 |
| H07 | guarded_anthropic_create 401 (role flag ON, consent 3, key sentinel, fake client raising the REAL anthropic.AuthenticationError) | AnthropicDispatchError with error_class AuthenticationError, status 401, transient False (as at base); state anthropic rejected dispatch; abs_.record_failure zero | RED | 3.4 H5 |
| H08 | moderation site 403, then success | source moderation; then ok | RED | 3.4 H5/H6 |
| H09 | anthropic APIStatusError 402 billing_error | state quota, last_status 402 | RED | 3.4 |
| H10 | content_safety moderate_output, role flags OFF, get_client patched to a fake raising the real openai.AuthenticationError, then returning a not-flagged result | SafetyResult(allowed=True) (fail-open unchanged), state openai rejected moderation; then ok moderation | RED | 3.6 |
| G01 | gating code untouched | sha256 of ast.dump(include_attributes=False) of `_openai_server_answered`, `_openai_failure_is_transient`, `openai_record_failure`, `openai_record_success`, `openai_release_half_open_probe`, `_openai_dispatch_admission`, `llm_router._classify`, `llm_router.route`, `llm_router._moderate_step`, `llm_router.moderate_with_claude` equal the digests recorded AT BASE by the RED agent (stored base64; a name like GATING_AST_B64) | PIN (green at base) | nothing (must stay) |
| G02 | a 401 never gates (preflight ON, spend ON, FULL config) | 10 consecutive 401 dispatches: each admitted; the breaker never OPEN; failure count 0 | PIN | nothing |
| G03 | /health status / message / 200 with every state set | after a rejected openai and a none-left Serper selection: status healthy, message unchanged, HTTP 200 | PIN (asserts only those three) | nothing |
| HE01 | /health entry | after note_failure: body["llm_credential"] equals the leaf snapshot value; `set(body) - BASE == {"llm_credential"}` | RED | 3.9 |
| HE02 | absence after reset | the reset seams (when present) first, then /health carries neither key | PIN | 3.5 keeps it green |
| HE03 | raising snapshot | leaf.health_snapshot patched to raise -> 200, key absent; `_need(app.main, "llm_credential_health_snapshot")` | RED | 3.9 |
| HE04 | purity | Redis-fake and openai-fake recorders: zero calls during /health; getsource(health_check) contains both snapshot calls and no "await " | RED | 3.9 |
| HE05 | Serper counts only | SERPER_API_KEYS = two runtime sentinels, one marked through the Redis fake; `_active_serper_key()`; /health serper_keys == {configured 2, marked_exhausted 1, none_left False, at ISO-Z}; the body TEXT holds neither key nor either first-8 prefix | RED | 3.7 + 3.9 |
| S01 | all exhausted | both exhausted, exclude None -> None (unchanged); none_left True; one alert call (serper_keys, serper, exhausted, None); a second None -> no second call; L2 once | RED | 3.7 |
| S02 | exclude is not exhaustion | exclude={k1}, k2 exhausted -> None; none_left False; zero alert calls | RED | 3.7 |
| S03 | single key inert | one key: returned, zero Redis reads, `serper_keys_snapshot()` == {} | RED (`_need`) | 3.7 |
| S04 | Redis command count unchanged | two keys, first healthy: 1 GET; first exhausted: 2 GETs (literals measured at base) | PIN | nothing |
| S05 | SERPER_KEY_EXHAUSTED unchanged | two marks of one key -> one WARNING, the base template | PIN | nothing |
| M01 | monitor ok / unknown | OPENAI_API_KEY placeholder present, role flags OFF, no outcome -> 200 `{"status": "ok", "providers": {"openai": "unknown"}}` | RED (404 at base) | 3.9 |
| M02 | monitor rejected | after an openai 401 -> 503; status degraded; code LLM_CREDENTIAL_UNUSABLE (not FEATURE_DISABLED); providers {"openai": "rejected"}; application/json | RED | 3.9 |
| M03 | monitor quota | -> 503, providers {"openai": "quota"} | RED | 3.9 |
| M04 | not in use | anthropic rejected with every role flag OFF -> 200; "anthropic" not in providers | RED | 3.1 + 3.9 |
| M05 | route properties | "GET /health/llm" mounted (route_method_paths); absent from app.openapi()["paths"]; under RAILWAY_ENVIRONMENT the default-limiter reachable set (the test_retro_w1_9 helper logic) is still the three base paths; no "await " in the handler | RED | 3.9 |
| M06 | no Sentry event on the 503 | capture recorder: zero calls over 5 GETs in the rejected state (after the one transition call made by the setup, counted separately) | RED (asserts 503 first) | 3.9 |
| SE01 | one tagged event (a subprocess child, the S81-06 r34 pattern: SENTRY_DSN a synthetic https://public@example.invalid/1, init_sentry(), the client transport replaced by an in-memory recorder; no network) | `capture_credential_alert("llm_credential", "openai", "rejected", 401)` -> exactly one event: message credential_state, level error, tags exactly {alert llm_credential, provider openai, state rejected, status "401"}, fingerprint [llm_credential, openai, rejected], no exception, no request | RED | 3.2 |
| SE02 | no DSN | returns None, raises nothing | RED (`_need`) | 3.2 |
| SE03 | one event, not two (child as SE01) | `note_failure("openai", <real AuthenticationError>, "dispatch")` -> exactly ONE event (the message); the L1 WARNING makes none | RED | 3.1 + 3.2 |
| Y01 | env names | AST of both new modules: every os.getenv / os.environ.get name is in {ENABLE_LLM_CREDENTIAL_PROBE, LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS, OPENAI_API_KEY, ANTHROPIC_API_KEY}; no secret-shaped literal; tests/_env_safety.CREDENTIALS_UNSET equal to its base tuple | RED (module missing) | 3.1 + 3.8 |
| P01 | flag OFF, FULL config (keys, role flags ON, interval set) | one `probe_once`-guarded tick through the tick helper: zero get_client / _client_for / retrieve calls; snapshot {} | RED (module missing) | 3.8 |
| P02 | flag reader | "true", "1", "yes", "on", " TRUE " -> ON; unset, "", "false", "0", "off", "maybe" -> OFF | RED | 3.8 |
| P03 | interval knob | unset 900; "600" 600; "60" 300; "0", "-5", "inf", "nan", "abc" 900 | RED | 3.8 |
| P04 | ON, openai only | one retrieve with model == model_config.standard_model() and options max_retries 0, timeout 5.0; success -> ok source probe | RED | 3.8 |
| P05 | ON, real AuthenticationError | state rejected probe; nothing escapes the tick | RED | 3.8 |
| P06 | ON, retrieve hangs (CALL_TIMEOUT patched to 0.05) | tick returns; exactly one call; snapshot {} | RED | 3.8 |
| P07 | ON, anthropic in use / not in use | in use (role flag + key): one anthropic retrieve with anthropic_model("text"); not in use: none | RED | 3.8 |
| P08 | no spend / ledger | recorders on llm_spend_breaker admit / record, llm_pricing.record_llm_call, openai_pricing.record_openai_response, api_budget admissions: zero across an ON tick | RED | 3.8 |
| P09 | run_forever timing and cancel | sleep recorder: first FIRST_DELAY_SECONDS (<= 30), then probe_interval(); task.cancel() -> CancelledError propagates (task.cancelled()) | RED | 3.8 |
| P10 | lifespan | inside `with TestClient(app)`: app.main._llm_probe_task is a Task; after exit None; shutdown names: `_stop_loop_lag_heartbeat` < `_stop_llm_credential_probe` < `_drain_background_tasks` | RED | 3.9 |
| P11 | L4 line | per provider one INFO full-matching the 2.4 L4 regex; no key or SDK sentinel in any record | RED | 3.8 |
| P12 | probe module hygiene | AST: no URL literal, no model-id literal, no AsyncOpenAI / AsyncAnthropic / OpenAI / Anthropic constructor, no `.create(` / `.messages` attribute, no logger.error; provider modules imported inside functions only | RED | 3.8 |

Counts: 55 rows = 49 RED + 6 PIN (G01, G02, G03, HE02, S04, S05). Parametrised rows count once here; the RED agent reports node counts.

## 6. Mutation table (on the GREEN bytes; each mutant: byte copy, one exact-string edit matching once, the killing rows via `P --bound 600 --tag inc-mon1-mut-<id> -- <file> -k "<rows>"`, restore from the copy, sha256 compare; the mutation lock .qa-mutation.lock; KILLED = an assertion failure)

| Id | Mutant | Killed by |
|---|---|---|
| MU01 | drop H1's note_failure (flag-OFF except arm) | H01, M02 |
| MU02 | drop H3's note_failure (flag-ON except arm) | H03 |
| MU03 | drop H2 (flag-OFF success) | H02 |
| MU04 | H1 swallows instead of `raise` | H01 (identity) |
| MU05 | classify maps BadRequestError (400) to rejected | L02 |
| MU06 | classify reads str(exc) for "invalid_api_key" | L02 (the 400 whose message names it) |
| MU07 | openai quota branch removed | L02, M03 |
| MU08 | anthropic billing_error branch removed | L03, H09 |
| MU09 | the event latch removed (emit on every transition) | L08 |
| MU10 | the recovery event removed | L08 |
| MU11 | H3 also calls openai_record_failure on a 401 (gating changed) | H03, G02 |
| MU12 | /health line `**llm_credential_health_snapshot()` deleted | HE01 |
| MU13 | monitor raises HTTPException(503) without a code | M02 (code FEATURE_DISABLED) |
| MU14 | monitor ignores providers_in_use | M04 |
| MU15 | probe flag gate removed | P01 |
| MU16 | interval floor removed | P03 |
| MU17 | probe built without max_retries=0 | P04 |
| MU18 | Serper none_left set even when a key was skipped by exclude | S02 |
| MU19 | Serper latch removed | S01 |
| MU20 | `_stop_llm_credential_probe` defined after `_drain_background_tasks` | P10 |
| MU21 | capture_credential_alert also logs logger.error | SE03 |
| MU22 | serper snapshot carries the key prefix list | HE05 |
| MU23 | note_success omits its try (a raising _transition escapes) | L07 |
| MU24 | conftest reset fixture removed | HE02 run after H01 in one process (the RED agent proves the order dependence with an order-preserving pair) |

24 mutants. An equivalent survivor is reported for a ruling, never silently dropped.

## 7. Comm set and gates for GREEN (cheapest first)

### 7.1 Gates

1. Hygiene: bytes > 127 = 0 in every new or edited file; `git diff --stat` shows no whole-file diff; the added-line sweep (no 8-digit run, no key shape, no @gmail / +973); no digest constant name with a scanner keyword; gitleaks-safe (no key-value literal).
2. `<venv python> -m py_compile` and `-m ruff check --select E9,F63,F7,F82 --no-cache` on the six app files, conftest and the two RED files; `black --check` on the four ratchet files (3.10).
3. The RED files at GREEN: P --bound 600 --tag inc-mon1-green-red -- tests/test_inc_mon1_credential_health.py tests/test_inc_mon1_probe.py (all 55 rows green).
4. The named pins of 4.2 in one run (bound 1200).
5. The comm set 7.2 base vs head (chunks <= 25 files, bound 1200, `comm -13` of the sorted FAILED node ids EMPTY).
6. The CI-order set (7.3).
7. The mutation run (section 6).
8. The fourteen backend-scanning CLIENT jest fences by path (the footprint touches app/ and .github/): run at the final round through the orchestrator's junction, after the H5 jest probe; and the FULL jest suite ONCE in the last round (LC-7). No client literal moves, so a red fence is unexpected (an E-row, never weakened).

### 7.2 The comm set (union rule)

- conftest.py is EDITED (3.5): an autouse fixture runs for every test, so EVERY backend test file imports it. The comm set is therefore the WHOLE backend test tree: 767 tests/**/test_*.py at base MINUS the four tests/test_precommit_hook*.py = 763 files, PLUS the two RED files. This union already contains every class the rule names (the module and symbol references of the six edited app modules; the source-scanning pins incl. test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command*.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py; the rglob / glob / path-segment / bare-ast / os.walk / listdir walkers of 1.9; every app.main / TestClient user; the importers of the edited test file test_s81_s03_llm_ledger_v2.py; the CLAUDE.md readers by the import graph; the .github readers for black-clean-paths.txt (test_ci_gates.py and the S81-05 R28 precedent)).
- Base records (LC-6 / GC-9): reuse harness/base_records/a74caba7.../0a224f48... per file for its 375 members (same sha, unchanged bytes); the remaining ~390 files run at a74caba7 once and are stored as a new record (set sha256 over the sorted file list) for the later units of this lane.
- 32 chunks of <= 25 files, bound 1200, base and head; a branch-only failure is re-run alone at base to separate a flake (the known url_mode_v2 wall-clock node) from a regression.

### 7.3 CI-order set (one process, alphabetical as CI runs; bound 1200)

tests/test_error_middleware.py, tests/test_health_brand_s69.py, tests/test_health_loop_lag.py, tests/test_inc_mon1_credential_health.py, tests/test_inc_mon1_probe.py, tests/test_retro_w0_4_efg.py, tests/test_retro_w1_3.py, tests/test_retro_w1_7_w1_10.py, tests/test_retro_w1_9.py, tests/test_s75_fanout_starve.py, tests/test_s77_redis_offloop.py, tests/test_s81_s04_spend_breaker.py, tests/test_s81_s06_router_gate_rows.py, tests/test_s81_s20_result_gate.py (a lifespan user BEFORE the RED files is required by the P73 lesson: it sorts after them alphabetically, so the CI-order set is run TWICE: once sorted, and once with tests/test_s81_s20_result_gate.py placed first), tests/test_s81_s24_auth_throttle.py, tests/test_security_hardening.py, tests/test_shutdown_drain.py, tests/test_u3c_store_false_pin.py.

## 8. CLAUDE.md block, anchor and owner steps

### 8.1 Anchor (Q9)

A new block AFTER the S81-G10 block (CLAUDE_md_a74caba7.txt:630, the last block before `## Tests` at :637), one blank line before its heading; S81-04c adds a block at the same anchor: the final round unions them in MERGE ORDER. One sentence appended to the :341 Feature Flags pointer clause after the S81-G10 sentence: "`ENABLE_LLM_CREDENTIAL_PROBE` and the knob `LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS` (MON1 LLM-CREDENTIAL-HEALTH, default OFF; the passive credential-health signal ships unflagged): the rows of the **INCIDENT unit (MON1 LLM-CREDENTIAL-HEALTH, ...)** block." The CLAUDE.md readers (7.2) run at GREEN; test_s81_s08b R11 (one Feature Flags paragraph) stays green because the clause is edited in place.

### 8.2 Block text (GREEN writes it; ASCII; dates filled at the merge)

**INCIDENT unit (MON1 LLM-CREDENTIAL-HEALTH, 2026-11-xx, the 2026-11-11 incident lane; the passive part UNFLAGGED as a production bug fix of root cause 2 "no alarm", the active check DARK; spec .qa-s80/MON1_UNIT_SPEC.md):**
- Recorder `app/services/llm_credential_health.py` (stdlib leaf): per provider openai / anthropic the state ok / rejected / quota, by exception class + status_code + the SDK's structured `code` (openai insufficient_quota) / `type` (anthropic billing_error), never message text. Hooks: both branches and both success tails of `api_budget_service.guarded_llm_create`, the except arm and success tail of `llm_router.guarded_anthropic_create`, and `content_safety_service.moderate_output`'s OpenAI moderation call. Gating is unchanged: a 401 / 403 still never trips a breaker or denies an admission (W1-3b).
- Alert: `sentry_service.capture_credential_alert` sends ONE Sentry message `credential_state` (level error; info for a recovery) tagged `alert=llm_credential`, `provider`, `state`, `status` per (provider, state) per process, and `alert=serper_keys` once when every Serper key is found exhausted. An owner-side Sentry alert rule on the tag `alert` is what reaches the phone.
- `/health` gains `llm_credential` {provider: {state, last_status, at, source, count}} after the first outcome in the process and `serper_keys` {configured, marked_exhausted (marks by this process since start), none_left, at} after the first multi-key selection (counts only, never a key or prefix). `GET /health/llm` (public, not in the schema, not rate-limited): 200 `{"status": "ok", ...}` or 503 `{"status": "degraded", "code": "LLM_CREDENTIAL_UNUSABLE", ...}` while an in-use provider is rejected / quota: the uptime-monitor path.
- `ENABLE_LLM_CREDENTIAL_PROBE` (default OFF, read per tick) + `LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS` (default 900, floor 300): a lifespan task in the web process only; ON: one `models.retrieve` (GET /v1/models/{model}, no tokens, 5 s timeout, no retry) per in-use provider per interval, first 20 s after start; no spend admit, no ledger record. Flip in its own canary window, after the OpenAI credential works.
- Owner steps (names only): (1) a Sentry issue alert rule on tag `alert` (values llm_credential, serper_keys) with a phone notification; (2) one uptime monitor on GET /health/llm (GET, not HEAD); (3) the ENABLE_LLM_CREDENTIAL_PROBE flip on web in its own window; (4) optional, no code: a Sentry metric alert on the existing error events for a failure-rate threshold.
- Merged is NOT proven: the PROOF ON THE PHONE of the spec's 8b decides.

### 8.3 Owner steps (names only; nobody but the owner enters any credential)

1. A Sentry alert rule on the tag `alert` (values `llm_credential`, `serper_keys`), action: notify the owner's phone; the owner sends its test notification (who receives it: ruling O2).
2. One uptime monitor on GET /health/llm (expect 200; alert on non-200) (ruling O2).
3. The flip of ENABLE_LLM_CREDENTIAL_PROBE on web in its own canary window, set by the relay on the owner's yes, only after N1 (the working OpenAI credential) is proven (ruling O3). LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS stays unset (900).
4. Optional: a Sentry metric alert on the existing ERROR events for a failure-rate threshold (no code).

## 8b. PROOF ON THE PHONE (header H6; R0-1; the brief's section 4; the incident S7 row)

Nothing here is called fixed on green suites. After the merge the unit is reported "merged, NOT yet proven". The relay runs these with the owner and files the dated result; only then does DEFECT_LEDGER_INCIDENT say PROVEN. The hermetic rows (a fake client raising the real SDK classes) are necessary and are NOT this proof.

| # | Repeat | What must be visible | Backing check | Not provable here |
|---|---|---|---|---|
| PP1 | After the deploy, ONE comparison on the phone (any golden pair, e.g. Creed Aventus EDP vs Parfums de Marly Layton EDP), then one GET of production /health | `llm_credential.openai.state` = `ok` if the owner's new credential (N1) is in place, `rejected` with last_status 401 if not; `serper_keys` with `configured` >= 2 and its counts | the deploy log has exactly ONE `[LLM_CREDENTIAL] provider=openai state=... source=dispatch` line for that comparison's first outcome; if rejected, Sentry shows ONE `credential_state` event tagged alert=llm_credential provider=openai state=rejected status=401 | nothing on the phone screen itself changes (by design: the unit is an operator signal) |
| PP2 | The owner's Sentry alert rule (8.3 step 1) sends its test notification | the notification arrives on the owner's phone | the rule exists in Sentry naming tag alert | that a REAL event pages him, unless PP3 runs |
| PP3 | Only if the merge lands BEFORE N1 (the relay decides; N1 is never delayed for it): the next comparison | the alert notification itself arrives on the phone; GET /health/llm answers 503 with code LLM_CREDENTIAL_UNUSABLE; after N1 and one more comparison: the recovery event (info), /health llm_credential.openai.state ok, /health/llm 200 | deploy log L1 lines for both transitions; the two Sentry events | if N1 lands first, the rejected path is proven only hermetically (SE01 / H01 / M02) |
| PP4 | After the probe's flip window (8.3 step 3): a redeploy, NO comparison, wait 60 s, GET /health | `llm_credential.openai` present with `source` = `probe` and state ok | the log shows one `[LLM_PROBE] provider=openai outcome=ok` line per interval and zero `[LLM_PROBE] tick failed`; the OpenAI console shows no added token spend for the probe (a GET of model metadata) | that the endpoint is unbilled is stated by the vendor docs only by omission (11 Q8) |
| PP5 | The uptime monitor (8.3 step 2) | it shows the path up (200) while the credential works | the monitor's own history | a monitor alert on a real outage needs PP3 or a real outage |

Measured before (the incident, 2026-11-11): production /health carries neither key (main.py:639-649); the 401 lines are WARNING / ERROR per call with no tagged event (48 untagged events since 2026-10-31, SENTRY_READ); no monitor path. The after is PP1-PP5 on production; a hermetic measurement is not the production proof.

## 9. Stated limits

- L-1 Per-process state: a Railway restart forgets it; the first outcome after each start re-emits the event (bounded: at most one event per (provider, state) per process). With the probe OFF and no traffic, /health shows nothing and /health/llm says unknown (production traffic is about two comparisons a week): the probe is the answer, in its own window.
- L-2 A single uvicorn worker is assumed (railway start command); with more workers each has its own state and its own events.
- L-3 A model-specific 403 (a project without access to one model) marks the credential rejected while other calls succeed; the state flaps, L1 logs each change, the latch bounds the events to three per provider per process.
- L-4 Anthropic spend LIMIT (400 invalid_request_error) and the tier spend CAP (429 rate_limit_error with details.error_code enforced_spend_limit_reached, per the official rate-limits page) are NOT classified as quota: the first needs message text (forbidden), the second a body field the SDK does not surface as an attribute. OpenAI's org-level hard limit is assumed to surface as insufficient_quota (not measured against a live account).
- L-5 `serper_keys.marked_exhausted` counts this process's marks since start (`_serper_exhausted_logged` never decays) while the Redis flag lives 6 h; `none_left` is the truth of the last multi-key selection. A single-key configuration has no exhaustion machinery and shows no `serper_keys` entry (single-key inert, unchanged).
- L-6 The moderation except arm keeps logging the exception TEXT at WARNING (content_safety_service.py:269, base behaviour; not an event): out of scope here, a hygiene follow-up.
- L-7 GET /health/llm answers HEAD with 405: the monitor must use GET.
- L-8 With OPENAI_BASE_URL pointing at a non-OpenAI gateway the probe's models.retrieve may be unsupported: inconclusive, no state change.
- L-9 /health/llm fails OPEN (200) if its own view raises: a monitor bug never pages the owner, and the /health entry and the event still carry the truth.
- L-10 The recorder takes a threading lock per LLM outcome (microseconds); the probe adds outbound GETs only while its flag is ON.
- L-11 The unit cannot prove in production that a REAL dead credential pages the phone unless PP3's order is available (no staging environment on the record; nobody enters a key for a test).

## 10. Out of scope (R-MON1-12)

Any gating or refusal change (an honest refusal while the credential is known dead is a page-unit question); a failure-rate threshold alert (owner-side Sentry metric alert, no code); any notifier besides Sentry; a cron service; the cron and script processes (judge, kbseed, warmer and the others); the S81-04c log statements in extraction_service.py, image_routes.py, url_extraction_service.py; any client change; the moderation WARNING text hygiene (L-6); Bright Data / Firecrawl / Scrape.do health (the existing brightdata_auth entry stays as is); counting Serper credits.

## 11. Answers to the brief's questions and open questions for the orchestrator

### 11.1 Answers (by measurement)

- Q1 Census: three SDK call statements in the web process (1.3): chat create at api_budget_service.py:1002 (flag OFF, production) and :1013 (flag ON), reached by 15 routed sites (SITES has 16 keys; "critique" has no caller since S81-G10); Anthropic messages.create at llm_router.py:969 (route + moderation); OpenAI moderations.create at content_safety_service.py:259. No embeddings / files / responses / audio; no raw provider HTTP. Hook statements: 2.3 H1-H8. Source-scanning readers of these: K1 AST digest (tests/test_s81_s03_llm_ledger_v2.py:193/:2484, MOVES: E1), U3c shape and surface (test_u3c_store_false_pin.py, stays), S81-06 R38 / R39 / R39b / module-top import (stays), S81-04 r37 wiring (stays), the model-id literal scan (stays), U8d R8 (stays: no ERROR line added), test_health_loop_lag purity (stays), test_s81_s04 R36 `llm_spend_health_snapshot()` in getsource(health_check) (stays). One E-row only.
- Q2 SDK truth: 1.8 (openai 3.3.1: Authentication 401 / PermissionDenied 403 classes, `code` from error.code, quota = RateLimitError + code insufficient_quota; anthropic 1.12.1: same two classes, `type` from error.type, quota = generic APIStatusError 402 + type billing_error).
- Q3 sentry-sdk 2.68.1: one event = one `capture_message(..., level, tags=, fingerprint=)` (scope kwargs measured at scope.py:1993-2017); the L1 line is WARNING, below LoggingIntegration(level=ERROR), so no second event and no breadcrumb; level error for the alert (info for recovery); `_before_send` passes the closed-set tags unchanged (no key fragment, no pattern) and the 503 drop does not apply to a message event (response context is set on the transaction only, tracing.py:1144; RED SE01 measures it); no DSN -> a no-op client, the log line remains.
- Q4 /health readers in tests/ (1.9 + 4.2): test_error_middleware.py:96 (status + no top-level code), test_health_brand_s69.py:31 (status / message), test_health_loop_lag.py:121 / :350 (keys present, purity), test_retro_w0_4_efg.py:1486-1533 (SUPERSET pin: `set(body) - five <= {adapter_executor, brightdata_auth}`), test_retro_w1_7_w1_10.py:145, test_retro_w1_9.py:303 / :319 (200 / limiter), test_s75_fanout_starve.py:520-542 (brightdata_auth absent then present), test_s77_redis_offloop.py:2223-2287 (SUPERSET: `set(body) <= _BASE_HEALTH_KEYS`), test_s81_s04_spend_breaker.py:1493-1555 (SUPERSET + getsource), test_s81_s06_router_gate_rows.py:243-251 (anthropic_breaker), test_s81_s24_auth_throttle.py:1677-2134 and test_s81_s24_gate_rows.py:132 (HOP probe), test_s81_st1_usage_path_offloop.py:2080 (redis_offloop_pool), test_security_hardening.py:201-236 (headers). Three rows pin the ABSENCE of other keys in the same test (w0_4_efg, s77, s04); none produces an LLM outcome or a multi-key Serper selection inside that test, and the conftest reset (3.5) clears earlier tests' state, so all stay green with no E-row. No row pins the whole body byte-for-byte.
- Q5 Monitor-path table: 2.6 (RequestID, SecurityHeaders, ErrorHandler, CORS, RequestContext; SlowAPIASGI absent in prod and the route exempt; no auth dependency; HOP probe exact-match list unaffected). Pins that would move without the design choices: test_retro_w1_9.py:473-480 (avoided by `@limiter.exempt`), the U13 OpenAPI snapshot (avoided by include_in_schema=False and because it covers only ten operations), test_s71_u13 T05 (no require_paid dependency). None moves.
- Q6 Startup / shutdown: startup handlers by definition order (:190, :203, :372) + the new one after :372; shutdown `_stop_loop_lag_heartbeat` -> NEW `_stop_llm_credential_probe` -> `_drain_background_tasks`; pinned by test_shutdown_drain.py:718-743 (index order, stays green) and test_health_loop_lag.py lifespan rows. The drain arithmetic 30 > 20 + 8 is unchanged (the cancel adds ~0 s; the task is not in `_BACKGROUND_TASKS`).
- Q7 Serper: 1.6 (names SERPER_API_KEYS / SERPER_API_KEY; the in-process set `_serper_exhausted_logged`; "no healthy key left" = the multi-key `return None` of `_active_serper_key` with no exclude-skip, observable with no extra Redis command).
- Q8 Official documentation (read 2026-11-11; no project value sent): Anthropic Models API (https://platform.claude.com/docs/en/api/models, redirected from docs.anthropic.com/en/api/models): GET /v1/models and GET /v1/models/{model_id} return model metadata; no price or token use is stated. Anthropic pricing (https://platform.claude.com/docs/en/about-claude/pricing): billing is per input / output / cache token and per tool use; the Models API is not listed. Anthropic rate limits (https://platform.claude.com/docs/en/api/rate-limits): RPM / ITPM / OTPM are stated for the Messages API, separate limits for Message Batches, Managed Agents and Files; NO limit is stated for the Models API. OpenAI retrieve model (https://developers.openai.com/api/reference/resources/models/methods/retrieve; platform.openai.com answered 403 to the fetch): returns id, created, object, owned_by; billing and rate limit not stated. OpenAI pricing (https://developers.openai.com/api/docs/pricing): units per token / minute / call / GB-day / session; no price for the models endpoint. OpenAI rate limits guide (https://developers.openai.com/api/docs/guides/rate-limits): limits by model; GET /v1/models mentioned only as a way to check model access; no limit stated for it. CONCLUSION: the metadata endpoints are not billed as far as both vendors' official pages state (by omission: neither page says "free" in words), and no tight limit applies; 96 calls a day per provider (about 0.07 per minute) is far below any stated limit. No completion call is used (R-MON1-10 holds). LIKELY, not ESTABLISHED: PP4 checks the console for zero added spend.
- Q9 CLAUDE.md: 8.1-8.2; readers by the import graph in 4.2 / 7.2.
- Q10 After a deploy and before the first LLM call, with the probe OFF: /health shows NO `llm_credential` entry (absent, the brightdata_auth precedent). An explicit `unknown` on /health would put the key on EVERY body and redden the three superset pins (w0_4_efg :1528, s77 :2255/:2274/:2287, s04 :1507) as three E-rows; instead the monitor path reports `unknown` per in-use provider (M01). Recommended: keep /health absent-until-outcome (no E-row) and read /health/llm for the unknown state. The probe ON fills /health within 20 s of start.

### 11.2 Open questions for the orchestrator (each with the assumption this spec takes and why)

- OQ-1 (O2) The monitor path is IN with the path `/health/llm` and code `LLM_CREDENTIAL_UNUSABLE` (one code for rejected and quota; the providers map carries the detail). Assumption: one code keeps an uptime rule simple. Alternative: two codes.
- OQ-2 Serper recovery: this spec emits NO Sentry event when a healthy key returns (an INFO line L3 only), per R-MON1-11's "ONE alert-grade event". Rule whether a recovery event is wanted for symmetry with the LLM recovery event.
- OQ-3 403 counts as rejected per R-MON1-4; a model-specific 403 flaps (L-3). Alternative: 403 only from the probe (a metadata call cannot be model-access-denied). The spec keeps the brief's rule.
- OQ-4 ENABLE_LLM_CREDENTIAL_PROBE is NOT added to the FY25 UNIT_ENV list of tests/test_s75_fanout_identity.py (an identity node whose digest tests/test_s81_kb_schema.py pins): the probe is not on the compare path and the flag is read only by the lifespan task. Adding it would move the FY25 digest (two E-rows, the S81-06 E10 / S81-20 E8 precedent). Rule it.
- OQ-5 The conftest edit (3.5) makes the comm set the whole backend tree (763 + 2 files). Alternative: no conftest edit and a reset only in the RED files; rejected because any later test raising a real 401 through a chokepoint would leave the key on /health for the rest of the process and redden the superset pins order-dependently (the P73 class).
- OQ-6 `marked_exhausted` uses the never-decaying in-process set (L-5). Alternative: read the Redis flags at /health time (forbidden by R-MON1-7: no Redis command).
- OQ-7 The probe's OpenAI model id is `model_config.standard_model()` and the Anthropic one `anthropic_model("text")`. A retrieve of an unknown id answers 404 after authenticating; the spec treats 404 as inconclusive (no state change), so a renamed model never flips the state.
- OQ-8 The recovery event is level info; an owner rule filtered on level error will not page on recovery (intended). Rule whether the owner wants the recovery notification too (then the rule matches the tag only).
- OQ-9 FOCUS chain (R-MON1-13): two adversaries (correctness; observability-and-secrets) at GREEN. The spec review (Opus) precedes RED.

## Not done in this spec

- No pytest, jest, tsc or eslint ran (READ-ONLY round, H5 c): section 1.10's base runs, the RED-at-base proof, every gate of 7.1 and the mutation run are DEFERRED TO RED / GREEN with their commands.
- The K1 re-pin value (E1), the G01 base digests and the S04 Redis-count literals are measured by the RED agent at base (they need the interpreter).
- SE01's claim that a capture_message inside a request scope keeps no response context is by reading sentry-sdk 2.68.1 source only; SE01 measures it.
- The OpenAI insufficient_quota and Anthropic billing_error shapes were read from the SDK sources and the vendors' documentation, never from a live account.
- Q8 billing of the metadata endpoints is stated by the vendors only by omission; PP4 is the production check.
- No file other than this spec was written in the worktree; the scratch copies under <SP>/MON1/spec were deleted.
