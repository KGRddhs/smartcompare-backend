# S81-06 unit spec: ANTHROPIC-ROUTER, the consent-gated Claude brain above guarded_llm_create

| Field | Value |
|---|---|
| Unit | S81-06 ANTHROPIC-ROUTER (lane A; PLAN_S81 M2) |
| Flags (all NEW, default OFF, read PER CALL, house idiom) | `ENABLE_ANTHROPIC_TEXT`, `ENABLE_ANTHROPIC_VISION`, `ENABLE_ANTHROPIC_VERDICT`, `ENABLE_ANTHROPIC_CRITIC`, `ENABLE_ANTHROPIC_MODERATION`, `ENABLE_SONNET_ESCALATION`, `ENABLE_OPENAI_PRE_V3`. New names: unset in production by construction (no ledger line names them; session-81 ledger.md read 2026-10-23 15:45). |
| Worktree | `C:/Users/SynAckITPC/Documents/AI/sc-s81-s06` (detached at base; read-only for the spec agent) |
| Branch | `feature/s81-s06-anthropic-router` |
| Base sha | `dfc6502f791cdccbf0a620041f66888a734015d3` (= 84c861f6 D03 + #369 S81-03 LLM-LEDGER-V2) |
| git status --short | empty before and after every probe (only `.qa-s80/` is written, gitignored) |
| Evidence | measurement location `<scratchpad>/S81-06/` (notes.md, census.json, keys.json, base_a.log, base_b.log, base_c.log, base_envsafety.log, comm_files.txt, comm_tests.txt, scripts/census.py, scripts/keys.py); PLAN_S81 (Standing constraints, VERIFY "Provider adapter" + "Haiku 5.5 facts", F1-F4, M2 S81-06 text, owner decisions 6/9/10); S81_06_BRIEF.md; RULINGS_R0 R0-8 + runs/r0/anthropic_prereqs.json (anthropic 1.11.0 surface, measured in a scratch venv on 2026-10-19); PLAN_S80 section 0 + runs/research/contract_freeze.json; PyPI release RSS of `anthropic` read 2026-10-23 ~12:20 UTC (read-only, as the brief allows). |
| Sister units / contracts | DEPENDENCY S81-03 (merged, #369): `app/services/llm_pricing.py` `start_llm_ledger`, `record_llm_call`, `anthropic_usage_record`, `price_call`, `provider_of`; rulings R-S03-7 (llm ledger = NON-OpenAI providers only), R-S03-9 (no PROVIDER_CONFIGS `llm`), F1-9 (bind the llm ledger BEFORE any tracked call and in the PARENT task). DEPENDENCY S81-04 SPEND-BREAKER (RED; spec copy specs/S81_04_UNIT_SPEC.md + RULINGS_S81_04): `app/services/llm_spend_breaker.py` `spend_breaker_enabled`, `admit_async(lane, ub)`, `upper_bound_usd(provider, model, prompt_tokens, max_tokens, web_search_max_uses)`, `prompt_token_upper_bound(messages)`, `record_soon(lane, actual)`, lanes `live` / `escalation` (contract 2.8; R-S04-3 unpriced rule; R-S04-9 Anthropic image bound). DEPENDENCY S81-05 REQUEST-CONTEXT (GREEN; spec copy specs/S81_05_UNIT_SPEC.md + RULINGS_S81_05 + GATE_S81_05): `app.utils.request_context.consent_version() -> Optional[int]` (0..999) and `header_state(name) -> "absent"|"malformed"|"ok"` (R-S05-3, GC-1/GC-2); the S81-05 P1 pin (`test_s05_p01_no_consumer_in_app`) is this unit's deliberate pin change (R-S05-10). GREEN starts only after S81-04 and S81-05 merge; this spec is measured at dfc6502f. Known rebases: S81-04 edits `api_budget_service.guarded_llm_create` + the two scs compare entries (this unit's consent gate sits beside its entry check) + app/main.py; S81-05 edits `tests/_env_safety.CREDENTIALS_UNSET` (DEVICE_KEY_PEPPER beside this unit's ANTHROPIC_* names) + app/main.py; ST1 (READY_FOR_PR at 8e663581) edits usage_service / review_service / redis_offloop (no shared hunk); S81-12 LEGAL-V3 owns the policy text, SEVEN_FLAGS and T7a-c consent pins (this unit adds NO policy text); S81-08 CLIENT-FIRST-OTA sends `X-AI-Consent-Version`. CLAUDE.md anchor shared with every S81 row (union at rebase). |
| Personal-data rule | No personal values anywhere (repo public): synthetic product names, synthetic keys built at run time by concatenation (never an `sk-`-shaped or `sk-ant-`-shaped literal), no real ids, emails or phone numbers, no 8-digit runs; variable NAMES only; no `.env` read; no provider call. |

## 0. What the unit does

It adds `app/services/llm_router.py`, a routing wrapper ABOVE `api_budget_service.guarded_llm_create` that every one of the 16 chat dispatch sites calls with a site key, the caller's own `_llm_breaker.guarded_llm_create` and the unchanged OpenAI kwargs. With every role flag OFF the router's first statement reads that site's role flag and returns `await dispatch(client, **kwargs)`: the exact base call. With the role flag ON it reads the request's AI-consent version (S81-05): `>= 3` sends the call to Claude Haiku 5.5 through a new chokepoint `guarded_anthropic_create` (official `anthropic` SDK Messages API only, its own `anthropic` circuit breaker, typed-exception classification, capped retries, an inner deadline, the S81-04 spend admit/record, the S81-03 llm-ledger record, refusal -> `LLMUnavailableError` recorded first) and returns an OpenAI-shaped result object so the 29 measured result readers stay untouched; `< 3` or absent goes to OpenAI while `ENABLE_OPENAI_PRE_V3` is ON, else raises `ConsentUpdateRequiredError` (a subclass of `LLMUnavailableError`). The two compare entries refuse such a request BEFORE any provider work with the existing `LLM_UNAVAILABLE` envelope (build 3 renders it; refund per R-A3). A capped (1 per compare) Sonnet 5.5 escalation on refusal or schema failure rides `ENABLE_SONNET_ESCALATION` under the `escalation` spend lane; the moderation call in `content_safety_service` gains a Haiku classifier role that stays dark until S81-07's 100-case parity set passes. The same PR pins the `anthropic` SDK in `requirements.in` (the orchestrator recompiles the locks and installs it), adds `AnthropicIntegration(include_prompts=False)`, adds the ANTHROPIC_* names to `CREDENTIALS_UNSET`, adds the `anthropic` processor-manifest row, and rewrites the named pins. Nothing flips until S81-07 and S81-12 (section 8).

## 1. Base state (MEASURED at dfc6502f)

### 1.1 The chokepoint and breaker (`app/services/api_budget_service.py`, CRLF)

| file:line | What |
|---|---|
| :37-95 | `PROVIDER_CONFIGS` (firecrawl, scrapedo, brightdata, serper, openai (inert budget row, comment :63-77), youtube). Iterated by the admin surfaces at :1099 and :1118 (`get_usage_summary` / `get_provider_burn`), so a new row changes admin output in both flag states. |
| :513-519 | `_half_open_probe_key(provider, state)` |
| :522-585 | `is_circuit_closed(provider)` (fail-open; half-open atomic INCR admission) |
| :588-609 / :612-626 | `record_failure(provider)` / `record_success(provider)`; the key is `_circuit_key(provider)`, which never consults PROVIDER_CONFIGS (comment :68-71; `unbxd_service.py:53` is a provider label with no PROVIDER_CONFIGS entry) |
| :692-699 | `_LLM_PREFLIGHT_FLAG`, `LLM_BREAKER_CACHE_TTL` (default 60.0), `OPENAI_PROVIDER = "openai"`, the memo tuple |
| :702-709 | `class LLMUnavailableError(RuntimeError)`; its message avoids the `429` / `rate` / `quota` substrings of the verdict fallback |
| :712-717 | `llm_preflight_breaker_enabled()` (house idiom, default ""); :720-730 TTL knob |
| :750-773 | `_openai_breaker_snapshot()` (read-only, memoised); :776-792 `openai_preflight_allows_compare()`; :795-823 `_openai_dispatch_admission()` -> (admitted, outcome_matters, probe); :826-887 record / release helpers (no-op unless the preflight flag is ON); :890-904 `_openai_server_answered`; :907-931 `_openai_failure_is_transient` |
| :934-953 | the caller census comment (says 14; stale, 16 measured below) |
| :954-1035 | `guarded_llm_create(client, **kwargs)`: `kwargs["store"] = False` (:980, body[0]), extra_body scrub (:981-983), flag-OFF `create(**kwargs)` + `record_openai_response` (:985-987), flag-ON admission + `create(**kwargs)` (:994) + outcome recording + `record_openai_response` (:1032). Exactly two `create(**kwargs)`. NOT edited by this unit (U3c 01/01b/01c, S81-03 K1; S81-04 re-records K1 for its own hunk). |

### 1.2 The 16 dispatch sites + the moderation call (AST census, scripts/census.py -> census.json)

Every site module imports `from app.services import api_budget_service as _llm_breaker` (extraction_service.py:30, image_service.py:40, openai_service.py:24, url_extraction_service.py:23, verdict_critique_service.py:36). Site key = the router key this unit introduces.

| # | Site key | file:line (call) | function (span) | Role | base cap | base temperature | base response_format | JSON parse at |
|---|---|---|---|---|---|---|---|---|
| 1 | `classify` | extraction_service.py:1385 | classify_category_llm (1368-1402) | text | 10 | 0.0 | none (plain word) | none; wrapped in wait_for `timeout=_CLASSIFY_LLM_TIMEOUT` (:1394; the knob read ONCE at import :1365, default 4.0) |
| 2 | `parse` | extraction_service.py:1525 | parse_product_query (1512-1553) | text | 500 | 0.1 | none | :1549 |
| 3 | `specs` | extraction_service.py:1583 | extract_specs (1556-1716) | text | 1000 | 0.1 | none | :1599 |
| 4 | `price` | extraction_service.py:1742 | extract_price (1719-1768) | text | 300 | 0.1 | none | :1764 |
| 5 | `price_training` | extraction_service.py:1791 | extract_price_from_training_data (1771-1823) | text | 200 | 0 or 0.2 | `**_json_mode` | :1812 |
| 6 | `reviews` | extraction_service.py:1847 | extract_reviews (1826-1874) | text | 600 | 0.2 | none | :1863 |
| 7 | `verdict` | extraction_service.py:2643 | generate_comparison (2499-2773) | verdict | 1000 | 0 | json_object | :2712 |
| 8 | `verdict_fallback` | extraction_service.py:2685 | generate_comparison (the 429 fallback) | verdict | 1000 | 0 | json_object | :2712 |
| 9 | `image_tier3` | image_service.py:186 | extract_image_via_gpt (153-214) | text | 120 | 0.1 | none | :206 (key `image_url`) |
| 10 | `vision_v2` | openai_service.py:474 | _identify_products_v2 (458-561) | vision | `_VISION_V2_MAX_TOKENS` 1000 (:125) | 0 | `VISION_RESPONSE_FORMAT_V2` (:208, strict json_schema) | :521; wait_for bound `VISION_TIMEOUT_SECONDS` (per call :268-290, default 20.0 :124) at :473 |
| 11 | `vision_v1` | openai_service.py:642 | identify_products (564-695) | vision | 500 | 0 | none | :657 |
| 12 | `specs_targeted` | openai_service.py:758 | extract_specs_targeted (720-779) | text | 200 | 0.1 | json_object | :770 |
| 13 | `specs_synthesized` | openai_service.py:833 | extract_specs_synthesized (782-852) | text | 300 | 0.1 | json_object | :845 |
| 14 | `disambiguate` | openai_service.py:895 | disambiguate_variant_line (855-943) | text | 60 | 0 | json_object | :907 (keys distinct_product, confidence) |
| 15 | `url_extract` | url_extraction_service.py:945 | extract_with_ai (900-972) | text | 800 | 0.1 | none | :966 |
| 16 | `critique` | verdict_critique_service.py:174 | critique_verdict (148-235) | critic | 150 | 0.0 | json_object | :191 |
| M | `moderation` | content_safety_service.py:252 | moderate_output (234-263) | moderation | n/a | n/a | `client.moderations.create(model=moderation_model(), input=text)`; fail-open `except Exception` :261-262 | n/a |

Every site passes `**token_limit_kwargs(...)` and `**sampling_kwargs(...)` (site 5 also `**_json_mode`); the M3 shipped kwargs are pinned at tests/test_model_config_enforced.py:228-241. Site 8 passes `client.with_options(max_retries=openai_fallback_max_retries())` as the client (:2686-2688).

### 1.3 Result readers (29 attribute reads, census.json "readers")

`.choices[0].message.content`: extraction_service x8, openai_service x4, image_service x1, url_extraction_service x1, verdict_critique_service x1. `usage.prompt_tokens` / `completion_tokens`: extraction_service x6 each (e.g. :1546-1547, :1709-1710, :2757-2758), openai_service :687-688. `usage.total_tokens`: extraction_service :2703 (`getattr(usage, "total_tokens", 0)`, fed to `model_router.record_usage(verdict_model, tokens_used)` :2704), openai_service :664, :693. Cost formulas priced by the REQUESTED OpenAI id: openai_service.py:551-559 (v2) and :681-689 (v1) (`_llm_pricing.openai_usage_cost_usd(_vision_model, usage)` under LEDGER_V2, else gpt-4o-mini literals). `record_openai_response(kwargs.get("model"), response)` is inside guarded_llm_create only.

### 1.4 The verdict substring fallback (extraction_service.py:2661-2699)

`err_msg = str(primary_err).lower()`; fallback to `standard_model()` iff `verdict_model != _fallback_model and ("429" in err_msg or "rate" in err_msg or "quota" in err_msg)` (:2665-2670). Measured hazard: the type name `RateLimitError` lower-cased contains `rate`, and English words such as `generate`, `separate`, `moderate`, `accurate` contain `rate`; so no Anthropic-path exception text may carry an SDK message, a type name or such a word.

### 1.5 model_config (`app/services/model_config.py`, 205 lines)

`_ROLE_DEFAULTS` :44-56 (verdict gpt-4o, standard/vision/critic gpt-4o-mini, moderation omni-moderation-latest); `_resolve` :64-74 (`OPENAI_MODEL_<ROLE>`, blank -> default); `sampling_kwargs` :107-123 (drops temperature only for the GPT-5 family); `token_limit_kwargs` :126-140; `resolved_models` :143-145; `_resolve_retries` :172-181; `openai_max_retries` :184-189 (default 2). No claude handling.

### 1.6 Compare entries, preflight, ledger bind (`app/services/structured_comparison_service.py`)

`LLM_UNAVAILABLE_FRIENDLY_MESSAGE` :1732-1734; `_llm_preflight_short_circuits()` :1755-1768 (`llm_preflight_breaker_enabled() and not openai_preflight_allows_compare()`); `_tail_reserve_seconds()` :1836-1841 (`TAIL_RESERVE_SECONDS`, 6.5); `_TIER2_WALL_SECONDS` :613, `_TIER3_WALL_SECONDS` :836; `_llm_unavailable_envelope()` :3972-3990 (success False, error, code LLM_UNAVAILABLE, elapsed_seconds 0.0, total_cost, api_calls); `compare_from_text` :3992, W1-3 preflight :4032-4038, `_t0` :4039; `_compare_from_text_impl` binds `self._openai_ledger = start_openai_ledger()` at :4153; `compare_from_text_streaming` :4724, ledger bind :4747, W1-3 preflight :4762-4769 (`yield ("error", envelope); return`). `app/api/image_routes.py:342` `vision_ledger = start_openai_ledger()` (S81-03 R-S03-7 names these three as S81-06's llm-ledger bind sites).

### 1.7 Refusal envelopes build 3 renders (measured on the 683f56c0 bytes with `git show`)

`SmartCompareApp/src/services/api.ts` parseApiError :1049-1110: a 503 is normalised to TIMEOUT only when it has NO code; an explicit code survives. `SmartCompareApp/src/services/errorCopy.ts`: `ENGINE_UNAVAILABLE_CODES` :15-20 = {LLM_UNAVAILABLE, INTERNAL_ERROR, SERVER_ERROR, GATEWAY_UNAVAILABLE} -> `home.errors.engineUnavailable.*`; `friendlyErrorKey` :70-93: ANY other code (an unknown `CONSENT_UPDATE_REQUIRED` included) -> `home.errors.comparison` = the "try with brand or model" retype nudge, which blames the user's input. text_routes `_surface_comparison_failure` maps `LLM_UNAVAILABLE` to a coded 503 (`detail={"code", "error"}`, :530-545); the camera vision exit maps `LLMUnavailableError` to the coded 503 LLM_UNAVAILABLE after its refunds (#258 U7 R4). PLAN_S80 section 0 point 3 lists the codes build 3 maps. Conclusion: the consent non-delivery travels as code `LLM_UNAVAILABLE` (2.6).

### 1.8 Sentry, env safety, netguard, manifest

- `app/services/sentry_service.py` `init_sentry` :701-786: explicit integrations FastApi/Starlette/Logging(ERROR) + `OpenAIIntegration(include_prompts=False)` in its own try (:743-748); `sentry_sdk.init` :749-781 with `send_default_pii=False`, no `disabled_integrations`, so the SDK auto-enable set applies. sentry-sdk 2.68.1 auto-enables `AnthropicIntegration` (default `include_prompts=True`, capture gated by `should_send_default_pii()`; anthropic_prereqs.json evidence 15-16) the moment `anthropic` is importable.
- `tests/test_sentry_channels_u8d.py` `BASE_INTEGRATIONS` :192-197 (14 names, derived from the EFFECTIVE client, so auto-enabled integrations are listed); child probe INIT :279-292 (`openai_include_prompts`); `test_u8d_red_options_effective` :800-820; SR8 `test_u8d_pin_integration_list_unchanged` :968-971. HAZARD: installing `anthropic` into the shared venv adds `AnthropicIntegration` to the effective list and reddens SR8 in EVERY worktree on this box that runs this file until it rebases onto this unit (question Q3).
- `tests/_env_safety.py` `CREDENTIALS_UNSET` :110-135 (SENTRY_DSN ... APPLE_SIWA_PRIVATE_KEY); no ANTHROPIC name. anthropic 1.x reads `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL` from the environment and otherwise an `ant auth login` profile (anthropic_prereqs.json evidence 5).
- `tests/_netguard.py` (388 lines): NO host list; it blocks every non-loopback connect / getaddrinfo / create_connection / proactor connect and curl_cffi request (:184-260). `api.anthropic.com` is therefore already blocked; the brief's "blocked-host list gains api.anthropic.com" has nothing to edit (also measured by S81-05, R-S05-6). This unit adds a PIN row instead.
- `app/legal/processors.json`: 18 rows; the `openai` row (module list of 7 files, hosts api.openai.com, gate_flag null, category_en "OpenAI", public_name true). `tests/test_legal_docs_u8.py`: T7b scanner `CLIENT_CONSTRUCTORS = {AsyncOpenAI, OpenAI, create_client, Redis, StrictRedis}` :763 (no `AsyncAnthropic`: R0-8 named the gap), `_scan_source` :823-843, T7a :996-1036 (a personal-data row's category must appear in the policy; a non-public name must appear in NO legal source), T7b :1039-1058, gate_flag must be one of `SEVEN_FLAGS` :233-241 (S81-12 owns that list). `tests/test_legal_s78.py::test_s78_r22_manifest_categories` :900-921 freezes the row ids against `tests/fixtures/legal_s78.json` `manifest_base` (18 ids). The phrase "third-party AI service" is present at app/legal/privacy_policy.md:57 and :67; "Anthropic" / "claude" occur in no legal source (R0-8).

### 1.9 Libraries (pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren`)

`anthropic` NOT installed (find_spec None); `docstring_parser` absent (a new transitive of anthropic 1.x); openai 3.3.1, sentry-sdk 2.68.1 (`sentry_sdk.integrations.anthropic` present), httpx 0.28.1, httpx2 2.12.0 (lock :76), pydantic 2.13.4, jiter 0.16.0, anyio 4.14.2, sniffio 1.3.1. PyPI release RSS (read 2026-10-23 ~12:20 UTC): 2.1.0 (10-21), 2.0.0 (10-21), 1.17.0 (10-20), 1.16.0 (10-20), 1.15.0 (10-15), 1.14.0 (10-14), 1.13.0 (2026-10-09T15:29:08Z), 1.12.1 (2026-10-08T03:41:58Z), 1.12.0 (10-07), 1.11.0 (2026-09-30T22:58:21Z). Newest release at least 14 days old at spec time = **1.12.1**; 1.13.0 qualifies from 2026-10-23T15:29:08Z. The only MEASURED surface is 1.11.0 (R0-8): exception classes (BadRequest 400, Authentication 401, PermissionDenied 403, NotFound 404, Conflict 409, RequestTooLarge 413, UnprocessableEntity 422, RateLimit 429, Overloaded 529, InternalServer >= 500; APIConnectionError > APITimeoutError; 402 = bare APIStatusError with type billing_error); DEFAULT_MAX_RETRIES 2, DEFAULT_TIMEOUT 600 s / connect 5 s, retry-after honoured unbounded; `messages.create` keys max_tokens, messages, model, output_config, system, thinking, stop_sequences, metadata, ... and NO temperature / top_p / top_k / store; `output_config={"effort": low|medium|high|xhigh|max, "format": {"type": "json_schema", "schema": dict}}`; image source media types exactly image/jpeg, image/png, image/gif, image/webp; thinking types adaptive / enabled / disabled / between_tools; Usage fields input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, cache_creation, server_tool_use; stop_reason end_turn|max_tokens|stop_sequence|tool_use|pause_turn|refusal|model_context_window_exceeded; `claude-haiku-5-5` is not in the Model literal (sent through the str arm).

### 1.10 Base pass state of the files this unit touches (bounded runner, one process at a time, flags unset)

- `[pyt] tag=s06-base-a start=2026-10-23 15:26:21 end=2026-10-23 15:35:22 elapsed=541s bound=1200s status=FAIL rc=1` over tests/test_model_config.py, test_model_config_enforced.py, test_u3c_store_false_pin.py, test_legal_docs_u8.py, test_legal_s78.py, test_s81_s03_llm_ledger_v2.py, test_openai_breaker.py, test_content_safety_service.py, test_version_routes.py, test_conftest_env_safety.py: 1 failed, 508 passed, 1 skipped, 2 deselected; `[hermeticity] sentinel checked 510 test(s)`; `[netguard] blocked 121 attempt(s) from 6 node(s)` (test_openai_breaker sentinel `neutralized.supabase.invalid`, baseline class). The one failure, `tests/test_conftest_env_safety.py::test_live_opt_in_restores_the_environment_end_to_end`, is its child pytest timing out while importing openai types under load (log :75-95).
- `[pyt] tag=s06-base-envsafety start=2026-10-23 15:36:39 end=2026-10-23 15:37:38 elapsed=59s bound=600s status=OK rc=0`: test_conftest_env_safety.py alone 24 passed, 1 skipped, 2 deselected; `[netguard] blocked 0 attempt(s) from 0 node(s)`. The set failure is load timing, not a base failure; GREEN runs this file alone at base and head.
- `[pyt] tag=s06-base-b start=2026-10-23 15:38:22 end=2026-10-23 15:39:43 elapsed=81s bound=1200s status=OK rc=0` over test_sentry_channels_u8d.py, test_sentry_channels_u8d_unit.py, test_cost_meter_s74.py, test_image_identify_llm_unavailable_s69.py, test_verdict_critique_service.py, test_s80_b3_vision_identity_v2.py, test_w4_13_flag_off_ledger.py, test_s75_fanout_identity.py, test_prompt_fence.py, test_retro_w1_3.py: 588 passed; `[hermeticity] sentinel checked 588 test(s)`; `[netguard] blocked 20 attempt(s) from 1 node(s)` (test_retro_w1_3 `test_pin_flag_off_both_compare_entries_never_read_the_openai_breaker`, curl_cffi egress, baseline class).
- `[pyt] tag=s06-base-c start=2026-10-23 15:40:16 end=2026-10-23 15:43:06 elapsed=170s bound=1200s status=OK rc=0` over test_retro_w0_4.py, test_retro_w0_4_efg.py, test_s70_exc_summary_logs.py, test_s70_model_router_downgrade.py, test_w49_extraction_catch_redaction.py, test_camera_vision.py, test_url_extraction.py, test_sentry_service.py, test_s81_d03_deny_and_guards.py: 741 passed, 1 deselected; `[hermeticity] sentinel checked 741 test(s)`; `[netguard] blocked 8 attempt(s) from 8 node(s)` (w49 sentinel class).
- The tiktoken pair of test_prompt_fence did NOT error on this run (warm cache); GREEN records it identically at base and head either way.

### 1.11 Flag idiom, guards, line endings

House idiom `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")` (llm_pricing.py:153-155 is the newest example). Guards the new code must not trip: the U3c rules (no OpenAI SDK surface outside guarded_llm_create; no denied keyword at a call site; allowlisted spreads only), test_model_config.py:121-151 (no model literal in app/services outside the allowlist), the model_config_enforced M1 (no literal temperature= / max_tokens= at a dispatch site), the prompt-fence digests (no prompt text edited), the W4-9 codeless-message floor, the copy policy (no `couldn't` / `try again` / `Failed to`). Backend files are CRLF in the working copy, LF in the index (`core.autocrlf=true`); the new module and test file are written LF + pure ASCII (the S81-03 leaf precedent) or CRLF consistently, and `git diff --stat` must show no whole-file diff of an edited file.

## 2. Contract

### 2.1 Flags and knobs (every one read PER CALL, never at import)

| Name | Type / default | Reader | Meaning |
|---|---|---|---|
| `ENABLE_ANTHROPIC_TEXT` | flag, OFF | `llm_router.role_enabled("text")` | sites 1-6, 9, 12-15 |
| `ENABLE_ANTHROPIC_VISION` | flag, OFF | `role_enabled("vision")` | sites 10-11 |
| `ENABLE_ANTHROPIC_VERDICT` | flag, OFF | `role_enabled("verdict")` | sites 7-8 |
| `ENABLE_ANTHROPIC_CRITIC` | flag, OFF | `role_enabled("critic")` | site 16 |
| `ENABLE_ANTHROPIC_MODERATION` | flag, OFF | `role_enabled("moderation")` | site M |
| `ENABLE_SONNET_ESCALATION` | flag, OFF | `escalation_enabled()` | the one Sonnet retry per compare |
| `ENABLE_OPENAI_PRE_V3` | flag, OFF | `openai_pre_v3_enabled()` | consent None / < 3 on an ON role -> the exact OpenAI call |
| `ANTHROPIC_API_KEY` | credential NAME only | `_anthropic_api_key()` per call; None / blank = unset | passed explicitly as `api_key=` (never left to the SDK's env/profile discovery) |
| `ANTHROPIC_MAX_RETRIES` | int, default 2 | `model_config.anthropic_max_retries()` = `_resolve_retries("ANTHROPIC_MAX_RETRIES", 2)` | read at client construction (memoised per value; a change applies to the next construction) |
| `ANTHROPIC_MODEL_TEXT` / `_VISION` / `_VERDICT` / `_CRITIC` / `_MODERATION` | str, default `claude-haiku-5-5` | `model_config.anthropic_model(role)` (`_resolve` rule: blank -> default) | the Haiku id per role |
| `ANTHROPIC_MODEL_ESCALATION` | str, default `claude-sonnet-5-5` | `model_config.anthropic_escalation_model()` | |
| `ANTHROPIC_CALL_DEADLINE_SECONDS` | float, default 25.0 | `_call_deadline()`; unset / blank / garbage / inf / nan / <= 0 -> 25.0 | the total `asyncio.wait_for` around one SDK call (retries included; the SDK honours retry-after unbounded) and the SDK `timeout=` float |
| `ANTHROPIC_CLASSIFY_LLM_TIMEOUT` | float, default 4.0 (= today's `CLASSIFY_LLM_TIMEOUT`) | per call, same defensive parse | the classify site's wait_for when site 1 routes to Anthropic |
| `ANTHROPIC_VISION_TIMEOUT_SECONDS` | float, default 20.0 (= `VISION_TIMEOUT_SECONDS` default) | per call | site 10's wait_for when it routes to Anthropic |
| `ANTHROPIC_TAIL_RESERVE_SECONDS` | float, default 6.5 (= `TAIL_RESERVE_SECONDS` default) | per call | `_tail_reserve_seconds()` when the verdict role routes to Anthropic for the request |

The three timeout knobs are read only after the routing decision for that site says `anthropic`; any other decision reads the base knob exactly as at base (S81-07 re-measures all three). No PROVIDER_CONFIGS row is added (1.1: admin output would change in both flag states; the breaker needs none; question Q4).

### 2.2 New module `app/services/llm_router.py` (LF, pure ASCII; imports: stdlib `asyncio`, `base64`, `binascii`, `json`, `logging`, `math`, `os`, `re`, `time`, `contextvars`, `importlib`, `typing`; `from app.services import api_budget_service as _abs`, `llm_pricing as _llm_pricing`, `llm_spend_breaker as _llm_spend_breaker`, `model_config as _model_config`; `from app.utils import request_context as _request_context`; never `import anthropic` at module top)

| Symbol | Contract |
|---|---|
| `ROLE_FLAGS` | `{"text": "ENABLE_ANTHROPIC_TEXT", "vision": "ENABLE_ANTHROPIC_VISION", "verdict": "ENABLE_ANTHROPIC_VERDICT", "critic": "ENABLE_ANTHROPIC_CRITIC", "moderation": "ENABLE_ANTHROPIC_MODERATION"}` |
| `ESCALATION_FLAG`, `PRE_V3_FLAG` | `"ENABLE_SONNET_ESCALATION"`, `"ENABLE_OPENAI_PRE_V3"` |
| `MIN_CONSENT_VERSION` | `3` |
| `ESCALATION_CAP_PER_COMPARE` | `1` (a constant, not a knob) |
| `PROVIDER` | `"anthropic"` (the breaker key `circuit:anthropic` via `_abs._circuit_key`) |
| `SITES` | dict site key -> `SiteSpec(role, claude_max_tokens, output_schema)` for the 16 keys of 1.2, exact values: classify (text, 32, None), parse (text, 768, OPEN), specs (text, 1536, OPEN), price (text, 512, OPEN), price_training (text, 384, OPEN), reviews (text, 1024, OPEN), verdict (verdict, 1536, OPEN), verdict_fallback (verdict, 1536, OPEN), image_tier3 (text, 256, IMAGE_TIER3_SCHEMA), vision_v2 (vision, 1536, `openai_service.VISION_RESPONSE_FORMAT_V2["json_schema"]["schema"]` read lazily), vision_v1 (vision, 768, OPEN), specs_targeted (text, 384, OPEN), specs_synthesized (text, 512, OPEN), disambiguate (text, 256, DISAMBIGUATE_SCHEMA), url_extract (text, 1200, OPEN), critique (critic, 512, OPEN). The caps are constants S81-07 re-measures (a data PR). |
| `OPEN_OBJECT_SCHEMA` | `{"type": "object"}` (acceptance by Haiku 5.5 structured outputs is UNMEASURED: S81-07 row; if rejected, a data PR sets those sites' schema to None = no format, the base parsers already strip code fences) |
| `IMAGE_TIER3_SCHEMA` | `{"type": "object", "properties": {"image_url": {"type": ["string", "null"]}}, "required": ["image_url"], "additionalProperties": False}` |
| `DISAMBIGUATE_SCHEMA` | `{"type": "object", "properties": {"distinct_product": {"type": "boolean"}, "confidence": {"type": "string"}}, "required": ["distinct_product", "confidence"], "additionalProperties": False}` |
| `MODERATION_SCHEMA` | `{"type": "object", "properties": {"flagged": {"type": "boolean"}, "category": {"type": "string"}, "uncertain": {"type": "boolean"}}, "required": ["flagged", "category", "uncertain"], "additionalProperties": False}` |
| `MODERATION_SYSTEM_PROMPT` | a new constant (synthetic, owner-reviewable; names the categories the base `omni-moderation-latest` reports; no exemplar carrying any id, cohort or profile field) |
| `class ConsentUpdateRequiredError(_abs.LLMUnavailableError)` | message exactly `"ai consent version below 3; dispatch suppressed"` |
| `class AnthropicNotConfiguredError(_abs.LLMUnavailableError)` | `"anthropic key unset; dispatch suppressed"` |
| `class AnthropicShapeError(_abs.LLMUnavailableError)` | `"anthropic request shape unsupported; dispatch suppressed"`; attr `detail` = a constant reason code (`unknown_kwarg`, `image_media_type`, `image_data_url`, `content_part`) |
| `class AnthropicDispatchError(_abs.LLMUnavailableError)` | `"anthropic dispatch suppressed"`; attrs `error_class: str` (type name, NEVER in str()), `status: Optional[int]`, `transient: bool`; raised `from None` |
| `class AnthropicRefusalError(_abs.LLMUnavailableError)` | `"anthropic declined; dispatch suppressed"` |
| `class AnthropicBreakerOpenError(_abs.LLMUnavailableError)` | `"anthropic circuit breaker denied admission; dispatch suppressed"` |
| `role_enabled(role) -> bool` | house idiom on `ROLE_FLAGS[role]`; `KeyError` for an unknown role (programming error) |
| `escalation_enabled()`, `openai_pre_v3_enabled()` | house idiom |
| `decide(role) -> str` | `"openai"` if not `role_enabled(role)` (the ONLY read when OFF); else `consent = _request_context.consent_version()`; `"anthropic"` if `isinstance(consent, int) and consent >= 3`; else `"openai"` if `openai_pre_v3_enabled()`; else `"refuse"`. Never raises. |
| `async route(site, dispatch, client, **kwargs)` | FIRST statement: `spec = SITES[site]` then `if not role_enabled(spec.role): return await dispatch(client, **kwargs)` (the base call). Else `d = decide(spec.role)`: `"openai"` -> `return await dispatch(client, **kwargs)`; `"refuse"` -> one INFO `[ROUTER] consent update required site=%s consent_state=%s` (state = `header_state` constant) then `raise ConsentUpdateRequiredError(...)`; `"anthropic"` -> `request = to_claude_request(site, kwargs)`; `result = await _dispatch_claude(site, spec, request, lane="live")`; escalation per 2.7; returns the result object (2.5). `dispatch` is never called on the anthropic or refuse paths. |
| `to_claude_request(site, kwargs) -> dict` | pure translation (2.3); raises `AnthropicShapeError` before any I/O |
| `async guarded_anthropic_create(*, site, role, lane, model, system, messages, max_tokens, thinking, output_config)` | the ONE Anthropic chokepoint (2.4) |
| `compare_refuses_for_consent() -> bool` | entry gate (2.6): False after reading the five role flags when all are OFF (no consent read); else True iff any ON role decides `"refuse"` |
| `bind_request_scope() -> Optional[dict]` | reads the five role flags; all OFF -> returns None and binds NOTHING; else `_llm_pricing.start_llm_ledger()` and binds `_SCOPE` (`ContextVar("s81_router_scope", default=None)`) to a fresh `{"escalations": 0}`; returns it |
| `escalation_allowed() -> bool` / `consume_escalation() -> bool` | public hooks for later units (identity confidence, result gate): allowed iff `escalation_enabled()` and a scope is bound and `scope["escalations"] < ESCALATION_CAP_PER_COMPARE`; consume increments BEFORE the call and returns whether it was allowed |
| `active_provider_preflight_allows() -> bool` | 2.8 |
| `async moderate_with_claude(text) -> SafetyResult-shaped tuple (allowed, reason)` | 2.9 |
| `classify_timeout() / vision_timeout() / tail_reserve_seconds_for_request()` | 2.1 knob readers (each reads the routing decision first) |
| test seams | `_anthropic_client_factory` [prod: `lambda **kw: importlib.import_module("anthropic").AsyncAnthropic(**kw)`], `_monotonic` [`time.monotonic`], `_reset_router_state()` (client memo, warn latches, breaker memo) |

### 2.3 Claude request shape (`to_claude_request`, sites 1-16)

Accepted kwargs: `model`, `messages`, `max_tokens`, `max_completion_tokens`, `temperature`, `response_format`, `store`. Any other key (e.g. `tools`, `extra_body`, `metadata`, `user`, `stream`, `timeout`) -> `AnthropicShapeError("unknown_kwarg")`. Translation:
- `model` = `_model_config.anthropic_model(spec.role)` (the OpenAI id passed by the site is ignored).
- `system` = the `content` strings of every `role == "system"` message in order, joined with `"\n\n"`; omitted when there is none. `messages` = the remaining messages in order, roles kept; `content` str kept; a list content maps per part: `{"type": "text", "text": t}` -> same; `{"type": "image_url", "image_url": {"url": u, ...}}` with `u` = `data:<mime>;base64,<b64>` -> `{"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}}` (mime must be one of image/jpeg, image/png, image/gif, image/webp, else `AnthropicShapeError("image_media_type")`; a malformed data URL -> `"image_data_url"`); an http(s) URL -> `{"type": "image", "source": {"type": "url", "url": u}}`; any other part -> `"content_part"`. The `detail` hint is dropped. Images above 2,576 px on the long edge are downscaled by the API (4,784-token cap per image, ceil(w/28) x ceil(h/28); VERIFY Haiku 5.5 facts); the camera already refuses HEIC (image_routes.py:132-149).
- `max_tokens` = `spec.claude_max_tokens` (the OpenAI cap is ignored; `max_tokens` 0 is never sent: the 0-pre-warm 400).
- `temperature`, `top_p`, `top_k`, `store`, `response_format` are never sent (a non-default temperature is a 400 on Haiku / Sonnet 5.5; the pinned SDK has no such parameter).
- `thinking` = `{"type": "disabled"}` for the Haiku role model; `output_config` = `{"effort": "low"}` plus `"format": {"type": "json_schema", "schema": spec.output_schema}` when the schema is not None.
- Escalation (2.7): model = `anthropic_escalation_model()`, `thinking` = `{"type": "between_tools"}` (Sonnet 5.5 rejects disabled: inferred from the bundled docs, R0-8 evidence 20; S81-07 measures), same `output_config`.

### 2.4 `guarded_anthropic_create` (the Anthropic chokepoint)

In order:
1. Spend admit (S81-04 contract 2.8): `if _llm_spend_breaker.spend_breaker_enabled(): await _llm_spend_breaker.admit_async(lane, _llm_spend_breaker.upper_bound_usd("anthropic", model, _llm_spend_breaker.prompt_token_upper_bound(([{"role": "system", "content": system}] if system else []) + list(messages)), max_tokens))`. A refusal propagates as the S81-04 `LLMUnavailableError` before any client is built.
2. Breaker admission on `circuit:anthropic`: `_anthropic_dispatch_admission()` = the W1-3 algorithm (`_abs._openai_dispatch_admission` shape) over its own memo (`_anthropic_breaker_snapshot`, one GET of `_abs._circuit_key("anthropic")` per `LLM_BREAKER_CACHE_TTL` window, fail-open): CLOSED -> admitted, outcome matters iff failures > 0; OPEN inside `CB_RECOVERY_TIMEOUT` -> `AnthropicBreakerOpenError` without dispatch; otherwise `_abs.is_circuit_closed("anthropic")` (the atomic half-open probe). The breaker is active on every Anthropic dispatch (the path itself is behind the role flags); it never reads or writes `circuit:openai`.
3. Key: `_anthropic_api_key()` None -> `AnthropicNotConfiguredError` (one WARNING per process `[ROUTER] ANTHROPIC_API_KEY unset; anthropic roles unavailable (fail closed)`), no client built, a held half-open probe released.
4. Client: memoised `_anthropic_client_factory(api_key=key, max_retries=_model_config.anthropic_max_retries())` (no `base_url`, no httpx object: the SDK is built on httpx2).
5. Call: `t0 = _monotonic()`; `resp = await asyncio.wait_for(client.messages.create(model=model, system=system, messages=messages, max_tokens=max_tokens, thinking=thinking, output_config=output_config, timeout=_call_deadline()), _call_deadline())` (`system=` omitted when None). Exactly ONE `messages.create` in the module, keywords a subset of {model, system, messages, max_tokens, thinking, output_config, timeout}.
6. Exceptions (classified by class and `status_code`, never by message text): `asyncio.CancelledError` -> release a held probe, re-raise untouched, record nothing; transient (`RateLimitError`, `OverloadedError`, `InternalServerError`, any `APIStatusError` with status >= 500, `APIConnectionError` incl. `APITimeoutError`, a builtin `TimeoutError` from wait_for) -> `_abs.record_failure("anthropic")` + memo reset, raise `AnthropicDispatchError(transient=True) from None`; terminal (400, 401, 403, 404, 409, 413, 422, the 402 billing `APIStatusError`) -> no failure recorded (a held probe records success: the server answered), raise `AnthropicDispatchError(transient=False) from None`; any other exception -> release a held probe, raise `AnthropicDispatchError(transient=False) from None`. One WARNING `[ROUTER] anthropic dispatch failed site=%s class=%s status=%s transient=%s` (type name and int only).
7. Served response: `latency_ms = int((_monotonic() - t0) * 1000)`; `record = _llm_pricing.anthropic_usage_record(model, resp.usage, role=role, latency_ms=latency_ms, stop_reason=resp.stop_reason)`; `_llm_pricing.record_llm_call(record)` (a no-op when no llm ledger is bound); if the spend flag is ON: `_llm_spend_breaker.record_soon(lane, record["cost_usd"])` (the S81-04 R-S04-3 rule handles a None cost); success recorded on the breaker when the outcome matters. All of this happens BEFORE any refusal raise.
8. `resp.stop_reason == "refusal"` -> INFO `[ROUTER] anthropic refusal site=%s` and `raise AnthropicRefusalError(...)`; else return `ClaudeChatResult.from_message(resp, model, record)`.

### 2.5 The OpenAI-shaped result (`ClaudeChatResult`, plain classes, no pydantic)

`.choices = [Choice(index=0, message=Message(role="assistant", content=<the text blocks of resp.content joined in order, "" when none>), finish_reason=<"stop" for end_turn / stop_sequence, "length" for max_tokens and model_context_window_exceeded, "stop" otherwise>)]`; `.usage = Usage(prompt_tokens=record["prompt_tokens"], completion_tokens=record["completion_tokens"], total_tokens=prompt + completion, prompt_tokens_details=Details(cached_tokens=record["cache_read_tokens"]))` (None-safe: an unpriced record gives 0 counts); `.model` = the Claude id; `.provider = "anthropic"`; `.cost_usd` = `record["cost_usd"]`; `.stop_reason` = the raw stop reason. Every reader of 1.3 works unchanged. Two readers would mis-account a Claude result and are made provider-aware, each guarded by `getattr(response, "provider", None) == "anthropic"` (False for every OpenAI object, so flag OFF is identical): extraction_service.py:2702-2704 skips `model_router.record_usage(verdict_model, ...)` (a Claude verdict must not consume the gpt-4o daily counter), and openai_service.py:551-559 / :681-689 take `response.cost_usd` (0.0 when None) instead of pricing Claude tokens at the requested OpenAI id.

### 2.6 Consent gate and the non-delivery envelope (R-A3, contract freeze)

- Compare entries (`structured_comparison_service.py`): in `compare_from_text` after the W1-3 block (:4038) and after S81-04's entry check, before `_t0` (:4039): `if _llm_router.compare_refuses_for_consent(): logger.info("[ROUTER] consent update required at compare entry"); return self._llm_unavailable_envelope()`. In `compare_from_text_streaming` after the W1-3 block (:4769) and S81-04's: `yield ("error", self._llm_unavailable_envelope()); return`. Flag OFF: the gate returns False after five getenv reads and no coroutine, no consent read, no log.
- The envelope is the EXISTING `LLM_UNAVAILABLE` body (1.6); text_routes maps it to the coded 503 and refunds with consumed_keys, no lifetime bump, no history row, `log_search` as today (the W1-3 precedent). Build 3 renders `home.errors.engineUnavailable.*` (1.7). No new response key, no new code on the wire, never a bare 503. `CONSENT_UPDATE_REQUIRED` is the internal reason (exception class name, log line). The owner's lever that closes the window for old clients is `APP_MIN_VERSION` (+ `APP_FORCE_UPDATE`), version_routes.py:8-13.
- Dispatch-level backstop (any route): `route()` raises `ConsentUpdateRequiredError`, which every site already treats as an `LLMUnavailableError`; the camera vision exit turns it into the coded 503 LLM_UNAVAILABLE after its refunds; the URL compare surfaces it through `compare_from_urls`' existing LLM_UNAVAILABLE mapping (an entry gate for /url/compare is follow-up S81-06b, the S81-04b lane); moderation fails open (2.9).

### 2.7 Sonnet escalation (ENABLE_SONNET_ESCALATION)

Inside `route` on the anthropic path only. Triggers: (a) `AnthropicRefusalError` from the Haiku call; (b) schema failure on a site whose schema is not None: `finish_reason == "length"` or `json.loads(content)` raising. If `consume_escalation()` is True: INFO `[ROUTER] escalation site=%s trigger=refusal|schema`, one `guarded_anthropic_create` call with the escalation model, lane `"escalation"`, the same request. Outcome: success -> its result; a refusal or any `LLMUnavailableError` on the escalation -> for trigger (a) raise `AnthropicRefusalError`, for trigger (b) return the original Haiku result unchanged (the site degrades as it does on a malformed OpenAI answer today). No scope bound (no compare) -> no escalation. Low identity confidence and result-gate escalation are hooks only (`escalation_allowed` / `consume_escalation`), wired by the B3 follow-up and B2 (section 10).

### 2.8 Ledger, scope and the preflight of the active provider

- `bind_request_scope()` is called at `_compare_from_text_impl` right after `start_openai_ledger()` (:4153), at `compare_from_text_streaming` right after :4747, and at `image_routes.py` right after :342: the parent task, before any tracked call (F1-9). All role flags OFF: nothing bound (`current_llm_records()` stays None, byte-identical).
- `_llm_preflight_short_circuits()` (scs:1755) becomes `return llm_preflight_breaker_enabled() and not _llm_router.active_provider_preflight_allows()`; `active_provider_preflight_allows()` returns `openai_preflight_allows_compare()` unless `decide("verdict") == "anthropic"` or `decide("text") == "anthropic"`, in which case it returns the read-only Anthropic preflight (False only for an `anthropic` breaker OPEN inside its cooldown). Preflight flag OFF: the first operand short-circuits, nothing read.
- Timeouts: extraction_service site 1's `wait_for(timeout=...)` uses `_llm_router.classify_timeout()` (base `_CLASSIFY_LLM_TIMEOUT` unless site 1 decides anthropic, then `ANTHROPIC_CLASSIFY_LLM_TIMEOUT`); openai_service site 10's bound uses `_llm_router.vision_timeout()` (base `_vision_timeout()` unless anthropic); scs `_tail_reserve_seconds()` returns `_llm_router.tail_reserve_seconds_for_request()` only when the verdict role decides anthropic, else the base read.

### 2.9 Moderation role (dark until parity)

`moderate_output` (content_safety_service.py:247-263): inside the existing `try`, before the base two lines (:249-252), `if _llm_router.decide_moderation() == "anthropic": allowed, reason = await _llm_router.moderate_with_claude(text); return SafetyResult(allowed=allowed, reason=reason) if not allowed else SafetyResult(allowed=True)`. `decide_moderation()` = `decide("moderation")` with `"refuse"` raised as `ConsentUpdateRequiredError` (caught by the existing fail-open `except`, logged by the existing WARNING whose `%s` now carries only the constant message). `moderate_with_claude`: one `guarded_anthropic_create` (role moderation, lane live, max_tokens 64, `MODERATION_SYSTEM_PROMPT`, user content = the text, `MODERATION_SCHEMA`); `flagged` -> (False, category or "unspecified"); `uncertain` and `consume_escalation()` -> one Sonnet re-run under lane escalation, its answer wins; malformed JSON -> fail open (True, None). The OpenAI `moderations.create` is not called on this path. Flip precondition: the S81-07 100-case labelled parity set passes (row text).

### 2.10 Same-PR configuration changes

- `requirements.in`: `anthropic==1.12.1` (the newest release at least 14 days old at spec time; if the orchestrator installs at or after 2026-10-23T15:29:08Z it may choose 1.13.0, question Q1) with a comment naming S81-06 and the 14-day rule. The orchestrator runs `uv pip compile` for both locks (new transitive `docstring-parser`), `pip-audit -r requirements.txt --strict`, and installs into the venv BEFORE GREEN; agents never run package managers.
- `sentry_service.init_sentry`: after the OpenAI block (:743-748), its own try: `from sentry_sdk.integrations.anthropic import AnthropicIntegration; integrations.append(AnthropicIntegration(include_prompts=False))` (DidNotEnable when the SDK cannot load must not disable Sentry, the FIX B4 rule). Nothing else changes in `sentry_sdk.init`.
- `tests/_env_safety.CREDENTIALS_UNSET` gains `"ANTHROPIC_API_KEY"`, `"ANTHROPIC_AUTH_TOKEN"`, `"ANTHROPIC_BASE_URL"` (comment: the SDK reads all three from the environment; a test sets them only AFTER `import app.main`, the DOTENV GUARD rule).
- `app/legal/processors.json` gains row `anthropic`: `{"id": "anthropic", "name_en": "Anthropic", "name_ar": "Anthropic", "kind": "processor", "personal_data": true, "module": ["app/services/llm_router.py"], "hosts": ["api.anthropic.com"], "gate_flag": null, "category_en": "third-party AI service", "category_ar": <the Arabic twin of that phrase as it occurs at app/legal/privacy_policy_ar.md:57, extracted by GREEN with Python and verified by T7a's `_name_in`>, "public_name": false}`. With `public_name` false, T7a requires "Anthropic" in NO legal source (true at base) and the category in both policies (measured EN; AR verified by GREEN). S81-12 flips `public_name` and names the processor (question Q5).
- `.github/black-clean-paths.txt` gains `app/services/llm_router.py` and `tests/test_s81_s06_anthropic_router.py` (the D03 / S81-05 precedent).

### 2.11 Log templates (constants, ints, type names only; never a prompt, a product name, a key, an SDK message or a header value)

`[ROUTER] consent update required site=%s consent_state=%s` (INFO); `[ROUTER] consent update required at compare entry` (INFO); `[ROUTER] ANTHROPIC_API_KEY unset; anthropic roles unavailable (fail closed)` (WARNING, once per process); `[ROUTER] anthropic dispatch failed site=%s class=%s status=%s transient=%s` (WARNING); `[ROUTER] anthropic refusal site=%s` (INFO); `[ROUTER] escalation site=%s trigger=%s` (INFO); `[CIRCUIT] anthropic breaker read failed (%s) -- failing open` (WARNING, type name). ERROR only inside except arms (none added).

### 2.12 Every new key and its type

No response key of any route is added, removed, renamed or retyped; no new request field, header or route parameter (the T23 OpenAPI fixture is unchanged). New values: the result object fields of 2.5 (internal); llm-ledger records with provider `anthropic` (S81-03 shape) which reach `metadata.llm` only under `ENABLE_LLM_LEDGER_V2` (already additive, S81-03); spend keys `llm_spend:live|escalation:<day>` (S81-04 shape); Redis `circuit:anthropic` (+ its half-open side key) JSON blob, `_CB_TTL`.

### 2.13 Failure table

| Situation | flags OFF | role ON, consent >= 3 | role ON, consent None/<3, PRE_V3 ON | role ON, consent None/<3, PRE_V3 OFF |
|---|---|---|---|---|
| normal | base OpenAI call | Haiku via guarded_anthropic_create, OpenAI-shaped result | base OpenAI call | compare entry: LLM_UNAVAILABLE envelope, coded 503, refund; dispatch: ConsentUpdateRequiredError |
| ANTHROPIC_API_KEY unset | n/a | AnthropicNotConfiguredError (fail closed; never OpenAI) | base OpenAI | refusal |
| request-context flag OFF (consent always None) | n/a | n/a | base OpenAI | refusal (flip precondition: S81-05 ON first) |
| 429 / 529 / 5xx / connect / timeout | n/a | AnthropicDispatchError transient, `circuit:anthropic` failure recorded; site degrades via its except path; the verdict fallback is NOT triggered | | |
| 400 / 401 / 403 / 404 / 413 / 422 / 402 | n/a | AnthropicDispatchError terminal, no failure recorded | | |
| breaker OPEN | n/a | AnthropicBreakerOpenError, no call; preflight ON refuses the compare at entry | | |
| stop_reason refusal | n/a | usage recorded, then AnthropicRefusalError; escalation once if ON | | |
| schema failure | n/a | escalation once if ON, else the Haiku result returned | | |
| spend cap reached (S81-04 ON) | n/a | S81-04 LLMUnavailableError before the client | | |
| unknown kwarg / unsupported image | n/a | AnthropicShapeError, no call | | |
| cancellation | n/a | re-raised, probe released, nothing recorded | | |
| moderation path error | base fail-open | fail-open (allowed) | base | fail-open (allowed) after the compare-entry refusal already fired |
| off-clock script / warmer (no request context) | base | consent None -> PRE_V3 decides | base | refusal: the warmer service must not set role flags (owner step) |

### 2.14 Flag-OFF identity (the main invariant)

With all seven flags unset / `""` / `false` / `0` / `off` / ` FALSE ` and the FULL configuration present (synthetic `ANTHROPIC_API_KEY`, every ANTHROPIC_* knob set, a valid `X-AI-Consent-Version: 3` header with `ENABLE_REQUEST_CONTEXT_HEADERS` ON, a fake `anthropic` module in `sys.modules`): every one of the 16 sites hands the OpenAI fake exactly the base kwargs (the M3 SHIPPED literals + `store: False`), the moderation call is exactly `moderations.create(model=..., input=...)`, the anthropic fake records zero constructions and zero calls, no llm ledger is bound, `circuit:anthropic` is never read, the consent accessor is never called, no new log line is emitted, every compare / camera / url response body is field-equal to base (the FY25 nine digests, the W4-13 flag-OFF ledger, the T23 OpenAPI fixture, the U13 baseline unchanged). The only structural differences: the 16 sites' callee (pin changes 4.1) and one getenv per site per call. `ENABLE_OPENAI_PRE_V3` or `ENABLE_SONNET_ESCALATION` ON alone (role flags OFF) is byte-identical too.

### 2.15 Contract freeze (PLAN_S80 section 0, contract_freeze.json)

Additive only: the refusal reuses `LLM_UNAVAILABLE` (a build-3 code); the camera keeps its U7 R4 outage state; no `action`, `result`, `status` or `winner` key is introduced; the success payloads keep every key and type (the result readers see the same shapes).

## 3. Change list (the order GREEN applies it; byte copies of every edited file first, sha256 recorded)

1. Byte copies of every file below under `<scratchpad>/S81-06/green_base/`; `.qa-mutation.lock` rules for any later mutation run.
2. `requirements.in`: the `anthropic==` line (2.10). The orchestrator recompiles, audits and installs; GREEN verifies `find_spec("anthropic")` and records the installed version, then re-measures the 1.9 surface on the pin (exception classes, `messages.create` parameters incl. `output_config` and `thinking`, Usage fields) and reports any difference before writing code.
3. `app/services/model_config.py`: `_ANTHROPIC_ROLE_DEFAULTS` (five roles -> `claude-haiku-5-5`), `_ANTHROPIC_ESCALATION_DEFAULT = "claude-sonnet-5-5"`, `anthropic_model(role)`, `anthropic_escalation_model()`, `anthropic_max_retries()`, `resolved_anthropic_models()`; `sampling_kwargs` returns `{}` for ids starting `claude-` (`_CLAUDE_FAMILY` regex, IGNORECASE); `token_limit_kwargs` keeps `max_tokens` for them. `resolved_models()` unchanged.
4. New `app/services/llm_router.py` (2.2-2.9).
5. The 16 sites: `_llm_breaker.guarded_llm_create(client, <same kwargs>)` -> `_llm_router.route("<key>", _llm_breaker.guarded_llm_create, client, <same kwargs>)` with `from app.services import llm_router as _llm_router` beside the `_llm_breaker` import in each of the five files; site 1's `timeout=` and site 10's bound per 2.8; extraction_service :2702-2704 and openai_service :551-559 / :681-689 per 2.5. No prompt text, no kwarg value, no other line.
6. `app/services/content_safety_service.py` `moderate_output` per 2.9.
7. `app/services/structured_comparison_service.py`: import; `bind_request_scope()` at :4153 and :4747; the consent gate at both entries (2.6); `_llm_preflight_short_circuits` and `_tail_reserve_seconds` per 2.8.
8. `app/api/image_routes.py`: `bind_request_scope()` after :342.
9. `app/services/sentry_service.py` (2.10).
10. `tests/_env_safety.py`, `app/legal/processors.json`, `.github/black-clean-paths.txt` (2.10).
11. The pin rewrites of 4.1 (E1-E9) and `tests/fixtures/legal_s78.json` `manifest_base.anthropic` (E7).
12. The RED file stays as frozen by the RED gate; CLAUDE.md row (section 8).

No other file. (Not edited: `api_budget_service.py`, `llm_pricing.py`, `openai_pricing.py`, `llm_spend_breaker.py`, `request_context.py`, any prompt constant, any client file.)

## 4. Existing pins

### 4.1 Pins that change deliberately

| # | Pin | Change | Reason |
|---|---|---|---|
| E1 | `tests/test_model_config_enforced.py::_chat_sites` (:118-131) + `test_no_call_site_passes_raw_sampling_kwargs` (:134-143) | the callee match also accepts `llm_router.route` (`callee.endswith("llm_router.route")`), floor `>= 16`; the router's internal `dispatch(client, **kwargs)` is not a site | the 16 sites now call the router; without the widening M1 sees 0 sites and fails `>= 15` |
| E2 | `tests/test_model_config_enforced.py::_clean_env` (:98-107) | the seven new flag names join the cleared list | a developer `.env` must not flip the M2/M3 rows |
| E3 | `tests/test_u3c_store_false_pin.py::test_u3c_03_call_sites_pass_no_store_or_extra_body` (:333-361) | the census counts `route(...)` calls whose second positional is `*.guarded_llm_create` (the denied-keyword and spread rules apply to them unchanged); floors `sites >= 16`, `spreads >= 33` (16 + 16 + 1, GREEN measures); docstring names S81-06 | same reason as E1 |
| E4 | `tests/test_u3c_store_false_pin.py::test_u3c_02_no_chat_dispatch_outside_the_chokepoint_under_app` (:313-330) + `DISPATCH_METHODS` / `SDK_OBJECTS` | the attribute rule also flags `.create` / `.stream` / `.parse` / `.count_tokens` on `.messages` / `.messages.batches` / `.beta.messages`; allowed only inside `llm_router.guarded_anthropic_create`; two BYPASS shapes added (`client.messages.create(...)`, `client.messages.batches.create(...)`) and one LEGIT shape (`self.messages.append(x)`) | the new chokepoint beside the old: no Anthropic dispatch may bypass the ledger / breaker / spend admit. U3c 01 / 01b / 01c target `guarded_llm_create`, which is untouched, so they stay green UNEDITED (4.2); their twins for the new chokepoint are RED rows R38-R39 of this unit's file (stated deviation from the brief's "01 / 01b / 01c / 02"). |
| E5 | `tests/test_model_config.py::TestNoStrayModelLiterals` (:121-151) | regex `["\'](gpt-[0-9a-zA-Z.\-]+|omni-moderation-[a-z]+|claude-[0-9a-zA-Z.\-]+)["\']`; `ALLOWED` gains `llm_pricing.py` (a list-price table names models by definition, the openai_pricing reasoning in the comment) | Claude ids live only in model_config (and the price table) |
| E6 | `tests/test_legal_docs_u8.py` `CLIENT_CONSTRUCTORS` (:763) | gains `"AsyncAnthropic"`, `"Anthropic"`; the T7 positive-control row gains a probe for `AsyncAnthropic(` | T7b must see the new recipient (R0-8 gap) |
| E7 | `tests/fixtures/legal_s78.json` `manifest_base` + (unchanged) `test_s78_r22_manifest_categories` | `manifest_base.anthropic` = the frozen kind / module / hosts / gate_flag / personal_data of the new row; `PUBLIC_NAME_IDS` unchanged | the R22 frozen row set is re-recorded deliberately |
| E8 | `tests/test_sentry_channels_u8d.py` `BASE_INTEGRATIONS` (:192-197), the child INIT dict (:279-292), `test_u8d_red_options_effective` params (:802-810) | `"AnthropicIntegration"` joins the list (sorted position); INIT gains `"anthropic_include_prompts"`; a param row `("anthropic_include_prompts", False)`; SR8 docstring names S81-06 | the explicit integration with prompts off (the auto-enabled one would carry include_prompts True) |
| E9 | S81-05 `tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app` (on the merged main) | allowlist gains `app/services/llm_router.py` with ImportFrom/attribute names exactly {`consent_version`, `header_state`} | R-S05-10: S81-06 is the first consumer |
| E10 (conditional) | `tests/test_s75_fanout_identity.py` FY25 env list, the w4_11 recorder FLAGS (:41-45), `tests/test_prompt_fence.py` `_W411_FLAGS` (:50-56), the U13 CLEAN_ENV | the seven names join each clear-list that already carries `ENABLE_URL_MODE_V2` / `ENABLE_VISION_IDENTITY_V2` (R0-6 precedent); GREEN measures which lists exist at head | a developer `.env` must not leak a flag into a digest pin |

### 4.2 Pins that must stay green and UNEDITED (green at base, 1.10)

`tests/test_u3c_store_false_pin.py` (01, 01b, 01c, 04-09, 18, 19, 22), `tests/test_model_config_enforced.py` M2, M3 (twelve SHIPPED kwargs), M4 (`resolved_models`), M5 (spy on `api_budget_service.guarded_llm_create`: the image site passes `_llm_breaker.guarded_llm_create` evaluated at call time, so the patched attribute is the dispatch), `tests/test_s81_s03_llm_ledger_v2.py` (K1 untouched by this unit; R-S03-7 PIN), `tests/test_openai_breaker.py`, `tests/test_retro_w1_3.py`, `tests/test_cost_meter_s74.py`, `tests/test_retro_w0_4.py:507, :1443` and `tests/test_retro_w0_4_efg.py:1796` (they replace `ues._llm_breaker` with a SimpleNamespace: the router receives that namespace's function as `dispatch`), `tests/test_s70_exc_summary_logs.py:326`, `tests/test_s70_model_router_downgrade.py:220`, `tests/test_w49_extraction_catch_redaction.py:199`, `tests/test_s81_d03_deny_and_guards.py:1427` (all patch `<module>._llm_breaker.guarded_llm_create`), `tests/test_image_identify_llm_unavailable_s69.py`, `tests/test_s80_b3_vision_identity_v2.py`, `tests/test_camera_vision.py`, `tests/test_url_extraction.py`, `tests/test_verdict_critique_service.py`, `tests/test_content_safety_service.py`, `tests/test_sentry_service.py`, `tests/test_sentry_channels_u8d_unit.py`, `tests/test_w4_13_flag_off_ledger.py`, `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main`, `tests/test_prompt_fence.py` (digests: no prompt text changes), `tests/test_legal_docs_u8.py` T7a / T7c / schema, `tests/test_version_routes.py`, `tests/test_conftest_env_safety.py` (run alone), `tests/fixtures/s71_u13_flag_off_baseline.json` (T23).

## 5. RED tests: `tests/test_s81_s06_anthropic_router.py` (new; pure ASCII; hermetic: the house socket / DNS / curl_cffi guard, a fake `anthropic` module installed in `sys.modules` by an autouse fixture (`AsyncAnthropic` recording constructions and `messages.create` kwargs, scripted responses, synthetic exception classes mirroring the 1.9 hierarchy for the rows that do not need the real SDK), a fake OpenAI client recording kwargs, a dict-backed Redis fake for `circuit:anthropic`, `import app.main` before any `setenv`; every RED fails at base on an AssertionError only: the router module and new symbols are read with `importlib.util.find_spec` / `getattr` helpers and asserted; rows that need the REAL SDK assert `find_spec("anthropic")` first)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R01 | `test_r01_router_module_and_symbols` | find_spec(`app.services.llm_router`) and every 2.2 symbol present; ROLE_FLAGS / ESCALATION_FLAG / PRE_V3_FLAG / MIN_CONSENT_VERSION / ESCALATION_CAP_PER_COMPARE exact | module absent -> AssertionError | 3.4 |
| R02 | `test_r02_sites_table_exact` | SITES keys == the 16 keys; each (role, claude_max_tokens, schema identity) exact | absent | 3.4 |
| R03 | `test_r03_flag_readers[...]` (parametrized x7 names x 12 values) | ON for true/1/yes/on/" TRUE "/"On"; OFF for unset/""/false/0/off/no/garbage | absent | 3.4 |
| R04 | `test_r04_site_routes_to_claude_on_consent_3[site]` x16 (through the REAL site function with the M3 `_call` harness shape) | role ON + consent 3: the anthropic fake receives exactly {model claude-haiku-5-5, system, messages (no system role), max_tokens = SITES cap, thinking disabled, output_config {effort low[, format]}, timeout} and NO temperature / top_p / store / response_format / metadata / user; the OpenAI fake receives nothing | absent -> AssertionError (anthropic fake 0 calls) | 3.4-3.5 |
| R05 | `test_r05_consent_threshold[consent]` (None, 0, 2, 3, 999, malformed header) | 3 and 999 -> anthropic; None / 0 / 2 / malformed -> PRE_V3 ON: the exact base OpenAI kwargs | absent | 3.4 |
| R06 | `test_r06_pre_v3_off_refuses_at_dispatch` | role ON, consent 2, PRE_V3 OFF: `ConsentUpdateRequiredError`, isinstance `LLMUnavailableError`, str has none of 429 / rate / quota, both fakes 0 calls, one INFO with consent_state constant | absent | 3.4 |
| R07 | `test_r07_rest_entry_refusal_envelope` | `compare_from_text` (TEXT ON, consent None, PRE_V3 OFF): returns the envelope fields (success False, code LLM_UNAVAILABLE, error == LLM_UNAVAILABLE_FRIENDLY_MESSAGE, elapsed_seconds 0.0); Serper / OpenAI / anthropic recorders 0 | proceeds (no gate) -> AssertionError | 3.7 |
| R08 | `test_r08_stream_entry_refusal_event` | first and only event ("error", envelope) | proceeds | 3.7 |
| R09 | `test_r09_route_503_refund_no_history` | POST /api/v1/text/compare via TestClient (auth + usage fakes): 503, envelope code LLM_UNAVAILABLE (field), the refund called once with the consumed keys, `record_lifetime_comparison` 0 calls, `save_comparison` 0 calls (R-A3) | 200 path -> AssertionError | 3.7 |
| R10 | `test_r10_entry_gate_admits_consent_3` | TEXT ON + consent 3: the compare reaches the anthropic fake | gate absent -> anthropic fake 0 | 3.7 |
| R11 | `test_r11_image_blocks[mime]` | jpeg/png/gif/webp data URL -> base64 source with that media_type and data; https URL -> url source; image/heic -> AnthropicShapeError("image_media_type"), 0 calls; malformed data URL -> "image_data_url" | absent | 3.4 |
| R12 | `test_r12_unknown_kwarg_fails_closed` | `tools=` or `extra_body=` -> AnthropicShapeError("unknown_kwarg"), 0 calls | absent | 3.4 |
| R13 | `test_r13_openai_shaped_result` | choices[0].message.content = joined text blocks; finish_reason map; usage.prompt_tokens = input + cache_read + cache_creation; completion; total; prompt_tokens_details.cached_tokens = cache_read; .model claude id; .provider "anthropic"; .cost_usd = price_call | absent | 3.4 |
| R14 | `test_r14_real_readers_parse_claude_result[site]` (classify, parse, verdict, critique, disambiguate, image_tier3, vision_v2) | the site's own parser returns the expected value from the fake Claude JSON / text | anthropic not reached | 3.5 |
| R15 | `test_r15_refusal_recorded_then_raised` | stop_reason refusal (escalation OFF): AnthropicRefusalError; the bound llm ledger holds exactly one record with stop_reason "refusal" and provider anthropic, appended before the raise | absent | 3.4 |
| R16 | `test_r16_error_classification[cls]` (real SDK; asserts find_spec("anthropic") first) | transient classes -> `record_failure("anthropic")` once; terminal classes incl. a 402 APIStatusError -> none; every raise is AnthropicDispatchError whose str() is the constant, contains no SDK message sentinel, no type name, none of 429 / rate / quota; `__cause__` None and `__suppress_context__` True | absent / SDK absent | 3.4 |
| R17 | `test_r17_verdict_fallback_not_triggered` | generate_comparison with VERDICT ON + consent 3 and a fake RateLimitError (sentinel message carries "rate limit 429 quota"): one anthropic call, zero OpenAI calls, the LLMUnavailableError propagates | absent | 3.4-3.5 |
| R18 | `test_r18_client_construction` | factory called with api_key = the synthetic key and max_retries per ANTHROPIC_MAX_RETRIES (unset 2, "0" 0, "-1" 0, "x" 2); no base_url kwarg; memoised (one construction for two calls) | absent | 3.3-3.4 |
| R19 | `test_r19_key_unset_fails_closed` | role ON + consent 3 + key unset/blank: AnthropicNotConfiguredError, factory 0 calls, OpenAI 0 calls, one WARNING per process | absent | 3.4 |
| R20 | `test_r20_anthropic_breaker` | OPEN within cooldown -> AnthropicBreakerOpenError, 0 calls; half-open -> `is_circuit_closed("anthropic")` once; success after a streak -> `record_success("anthropic")`; `circuit:openai` never read on this path | absent | 3.4 |
| R21 | `test_r21_cancel_releases_probe` | CancelledError re-raised unchanged, no record_failure, half-open probe counter reset | absent | 3.4 |
| R22 | `test_r22_deadline` | ANTHROPIC_CALL_DEADLINE_SECONDS 0.05 + a sleeping fake: transient failure recorded, AnthropicDispatchError; knob garbage / inf / nan / <= 0 -> 25.0 | absent | 3.4 |
| R23 | `test_r23_ledger_record_and_metadata_llm` | one anthropic_usage_record per served call (role, latency_ms int, stop_reason); OpenAI calls never on the llm ledger; with ENABLE_LLM_LEDGER_V2 ON `build_llm_metadata` includes `by_provider.anthropic` with the record cost | absent | 3.4, 3.7 |
| R24 | `test_r24_scope_bound_in_parent_before_dispatch` | role ON: `current_llm_records()` is a list inside the first dispatch of `_compare_from_text_impl`, the stream and the camera route; all OFF: None | absent | 3.7-3.8 |
| R25 | `test_r25_spend_admit_record` (asserts find_spec(`app.services.llm_spend_breaker`) first) | spend flag ON: `admit_async("live", ub)` with ub = `upper_bound_usd("anthropic", model, prompt_ub, cap)` BEFORE the fake; `record_soon("live", cost)` after; an admit refusal -> 0 calls; escalation uses "escalation" | S81-04 absent at dfc6502f -> AssertionError | 3.4 |
| R26 | `test_r26_refusal_escalates_once` | ESCALATION ON: Haiku refusal -> one Sonnet call (model claude-sonnet-5-5, thinking between_tools, lane escalation) and its result; a second refusal in the same compare -> AnthropicRefusalError with no second Sonnet call; ESCALATION OFF -> no Sonnet call | absent | 3.4 |
| R27 | `test_r27_schema_failure_escalates_or_returns_haiku` | non-JSON / finish length on a format site -> one Sonnet call; Sonnet also invalid -> the Haiku result returned unchanged | absent | 3.4 |
| R28 | `test_r28_no_scope_no_escalation` | no bound scope -> no Sonnet call | absent | 3.4 |
| R29 | `test_r29_moderation_claude[case]` | MODERATION ON + consent 3: flagged -> SafetyResult(False, category); clean -> allowed; uncertain + ESCALATION -> Sonnet decides; any exception -> allowed (fail-open); `moderations.create` 0 calls | absent | 3.6 |
| R30 | `test_r30_moderation_pre_v3_openai` | MODERATION ON + consent 2 + PRE_V3 ON: exactly the base `moderations.create(model, input)` | absent (no decision) -> passes? no: the row also asserts the router decision recorder fired once -> AssertionError at base | 3.6 |
| R31 | `test_r31_model_config_anthropic` | anthropic_model(role) defaults + env override (blank -> default); anthropic_escalation_model(); anthropic_max_retries(); sampling_kwargs("claude-haiku-5-5", 0) == {} (and "CLAUDE-x" upper); token_limit_kwargs("claude-haiku-5-5", 10) == {"max_tokens": 10} | functions absent; sampling returns {"temperature": 0} | 3.3 |
| R32 | `test_r32_timeout_knobs[knob]` | classify / vision / tail-reserve: base value unless the site decides anthropic; then the ANTHROPIC_* knob with the defensive parse (4.0 / 20.0 / 6.5 defaults) | absent | 3.5, 3.7 |
| R33 | `test_r33_preflight_reads_active_provider` | preflight flag ON + TEXT ON + consent 3: anthropic breaker OPEN -> the compare short-circuits (envelope); openai OPEN + anthropic CLOSED -> proceeds | openai breaker decides -> AssertionError | 3.7 |
| R34 | `test_r34_sentry_anthropic_include_prompts_false` (child probe like u8d; asserts find_spec("anthropic") first) | effective integrations include AnthropicIntegration with include_prompts False | SDK absent or auto-enabled True | 3.9 |
| R35 | `test_r35_credentials_unset_names` | the three ANTHROPIC_* names in CREDENTIALS_UNSET | absent | 3.10 |
| R36 | `test_r36_manifest_row` | processors.json `anthropic` row field-equal to 2.10 (category_ar checked with T7a's `_name_in` against privacy_policy_ar.md); a test-local T7b scan with AsyncAnthropic maps llm_router.py to it | absent | 3.10 |
| R37 | `test_r37_requirements_pin` | requirements.in has exactly one `anthropic==X.Y.Z` line; the version's PyPI date is recorded in the comment | absent | 3.2 |
| R38 | `test_r38_anthropic_chokepoint_ast` | exactly one `messages.create(...)` in llm_router.py, inside guarded_anthropic_create, keywords subset of {model, system, messages, max_tokens, thinking, output_config, timeout}; no `store` / `temperature` / `top_p` / `top_k` / `metadata` / `user` / `extra_body` / `extra_headers` keyword or subscript write anywhere in the module; no `import anthropic` at module top | absent | 3.4 |
| R39 | `test_r39_sites_call_route_with_their_key` (AST) | each of the 16 calls is `_llm_router.route("<key>", _llm_breaker.guarded_llm_create, client-expr, ...)` with the 1.2 key for its file:function; no `guarded_llm_create(` call left in the five files | base calls guarded_llm_create | 3.5 |
| R40 | `test_r40_claude_cost_and_4o_counter` | a Claude-served verdict: `model_router.record_usage` 0 calls; a Claude-served vision v1 / v2: returned cost == result.cost_usd | absent | 3.5 |
| R41 | `test_r41_log_hygiene` | prompt sentinel, synthetic key, SDK message sentinel, header value: absent from every caplog record across R04-R29 scenarios | absent | 3.4 |
| P01 | `test_p01_flag_off_sites_byte_identical[site][off_value]` x16 x7 | FULL config (synthetic key, knobs, consent 3, fake anthropic in sys.modules): the OpenAI fake gets the M3 SHIPPED kwargs + store False; anthropic fake 0 constructions / 0 calls; consent accessor recorder 0 calls (installed with `raising=False`) | green | stays green |
| P02 | `test_p02_flag_off_entries_identical` | REST + stream with FULL config: no envelope, provider recorder counts equal to base literals, no `[ROUTER]` line | green | stays green |
| P03 | `test_p03_flag_off_moderation_identical` | exactly `moderations.create(model="omni-moderation-latest", input=text)`; anthropic 0 | green | stays green |
| P04 | `test_p04_flag_off_no_llm_ledger` | `current_llm_records()` None inside a dispatch with FULL config | green | stays green |
| P05 | `test_p05_flag_off_preflight_reads_only_openai` | preflight flag ON, role flags OFF: Redis GET recorder sees `circuit:openai` and never `circuit:anthropic` | green | stays green |
| P06 | `test_p06_flag_off_verdict_fallback_identical` | an OpenAI 429 on the primary: two OpenAI dispatches, the second on standard_model() with `with_options(max_retries=...)`, as at base | green | stays green |
| P07 | `test_p07_pre_v3_or_escalation_alone_identical` | ENABLE_OPENAI_PRE_V3 ON alone, ENABLE_SONNET_ESCALATION ON alone: P01 / P02 assertions hold | green | stays green |
| P08 | `test_p08_camera_identify_flag_off_body` | /image/identify with fakes, FULL config: body fields equal to the base literal | green | stays green |
| P09 | `test_p09_netguard_blocks_anthropic_host` | a socket connect / getaddrinfo to api.anthropic.com raises NetworkBlocked under the conftest guard | green | stays green |
| P10 | `test_p10_resolved_models_unchanged` | `resolved_models()` == the base five-key dict; `sampling_kwargs` gpt rows unchanged | green | stays green |
| P11 | `test_p11_refusal_messages_avoid_fallback_substrings` (run at head over every new exception class; at base over `LLMUnavailableError`'s own message) | none of 429 / rate / quota | green | stays green |

Counts: 41 RED rows (R01-R41, before parametrisation) and 11 PIN rows (P01-P11). The RED agent may split a row; every split stays AssertionError-only at base.

## 6. Mutation table (GREEN bytes; byte copy -> exact-string edit matching once -> killing rows via `pyt.py -k`, bound 600 -> restore -> sha256 compare; `.qa-mutation.lock`)

| # | Mutant | Killed by |
|---|---|---|
| M01 | `route` skips the role-flag check (always decides) | P01, P07 |
| M02 | `role_enabled` without `.strip().lower()` | R03 |
| M03 | `MIN_CONSENT_VERSION` 2 | R05 |
| M04 | `>= 3` -> `> 3` | R05 |
| M05 | PRE_V3 branch inverted | R05, R06 |
| M06 | refuse path calls `dispatch` (silent OpenAI) | R06 |
| M07 | compare entry gate removed (REST) | R07, R09 |
| M08 | compare entry gate removed (stream) | R08 |
| M09 | entry gate reads consent before the flags | P02 (consent recorder) |
| M10 | `temperature` forwarded | R04, R38 |
| M11 | `thinking` omitted | R04 |
| M12 | `output_config.format` dropped at a schema site | R04 |
| M13 | system message left inside `messages` | R04 |
| M14 | image media_type check removed | R11 |
| M15 | unknown kwarg silently dropped | R12 |
| M16 | `prompt_tokens` = input only | R13 |
| M17 | refusal raised before the ledger record | R15 |
| M18 | SDK message included in the wrapper str | R16, R17 |
| M19 | transient classification misses OverloadedError (529) | R16 |
| M20 | terminal 400 records a failure | R16 |
| M21 | `max_retries` hard-coded 2 | R18 |
| M22 | key unset falls back to OpenAI | R19 |
| M23 | breaker OPEN not checked | R20 |
| M24 | CancelledError records a failure | R21 |
| M25 | `wait_for` removed | R22 |
| M26 | `bind_request_scope` binds when all flags OFF | P04 |
| M27 | `bind_request_scope` moved inside a gather child (after the first tracked call) | R24 |
| M28 | spend admit after the call | R25 |
| M29 | escalation cap 2 | R26 |
| M30 | escalation lane "live" | R25, R26 |
| M31 | moderation path still calls `moderations.create` | R29 |
| M32 | `sampling_kwargs` keeps temperature for claude ids | R31 |
| M33 | preflight reads only the openai breaker | R33 |
| M34 | `include_prompts=True` | R34 |
| M35 | 4o counter recorded for a Claude verdict | R40 |
| M36 | a site passes `api_budget_service.guarded_llm_create` instead of its own `_llm_breaker` attribute | R39 and tests/test_retro_w0_4.py:507 |
| M37 | a log line carries the prompt | R41 |

Equivalent survivors, if any, are reported for a ruling.

## 7. Comm set and gates for GREEN (cheapest first; every pytest through `pyt.py`, one process at a time)

1. ruff `E9,F63,F7,F82` + `py_compile` on every edited / new .py; `json.loads` on processors.json and legal_s78.json; bytes > 127 = 0 in the new files; `git diff --stat` shows no whole-file diff.
2. The unit file ON and OFF (rows set flags themselves), bound 600; then the mutation table (section 6) on GREEN's bytes.
3. The E1-E10 pin files at head (green with the rewrites) and at base (the rewrites red only where 4.1 says), bound 600 each; `tests/test_conftest_env_safety.py` alone.
4. The FY25 nine-digest node, the W4-13 flag-OFF ledger, the T23 / U13 baseline OFF; `scripts/verify_flag_byte_identity.py` is NOT required (the price path is not touched).
5. CLAUDE.md readers `tests/test_ci_gates.py`, `tests/test_behavior_dimension_translation.py`; `tests/test_ci_gates.py::test_black_allowlist_entries_are_actually_clean` and `tests/test_precommit_hook.py -k black` in their own runner call.
6. Comm set (zero-regression): the module and symbol reference grep over tests/ of every edited file (extraction_service, openai_service, image_service, url_extraction_service, verdict_critique_service, content_safety_service, structured_comparison_service, model_config, sentry_service, image_routes, text_routes as the refusal route, api_budget_service as the chokepoint module, llm_pricing, guarded_llm_create, processors.json, requirements.in / .txt) UNION the edited test-support module `tests/_env_safety.py`'s importers UNION every source-scanning class of the common brief (string paths, `Path(<module>.__file__)`, `inspect.getsource`, `ast.parse` over app source, glob / rglob walkers over app/, "app" path joins, .github readers, conftest source readers) UNION the CLAUDE.md readers UNION the manifest / legal readers UNION the SmartCompareApp-scanning backend tests (no client file is edited; included because the refusal contract is client-visible) MINUS the four `test_precommit_hook*.py`. Approximate size at base: 400 test files (`<scratchpad>/S81-06/comm_tests.txt`, derived 2026-10-23 with the narrower string-grep; GREEN re-derives the union with the full class list at head and adds every new importer). Chunks of at most 25 files, bound 1200, at base and head; `comm -13` of the sorted FAILED node ids EMPTY beyond the recorded base noise (the env-safety child timeout class, the tiktoken pair); a branch-only failure is re-run against base before it is called a regression.

## 8. CLAUDE.md flag row (GREEN writes it after the SESSION 81 S81-03 row, CLAUDE.md:485-486, before `## Tests` :488; anchor shared with the other S81 rows: union at rebase) and owner steps

Row text (content binding, wording may tighten): **SESSION 81 flags (S81-06 ANTHROPIC-ROUTER, 2026-10-2x; default OFF, read PER CALL; new names, unset in production by construction):** `ENABLE_ANTHROPIC_TEXT` / `_VISION` / `_VERDICT` / `_CRITIC` / `_MODERATION` + `ENABLE_SONNET_ESCALATION` + `ENABLE_OPENAI_PRE_V3` (`app/services/llm_router.py`): a role whose flag is ON goes to Claude Haiku 5.5 (`claude-haiku-5-5`, `ANTHROPIC_MODEL_<ROLE>`) through `guarded_anthropic_create` only when the request's `X-AI-Consent-Version` is >= 3 (S81-05); consent absent or < 3 goes to the exact OpenAI call while `ENABLE_OPENAI_PRE_V3` is ON, else the compare is refused at entry with the existing `LLM_UNAVAILABLE` envelope (coded 503, refund, no history row; build 3 shows the engine-unavailable copy; `APP_MIN_VERSION` force-update closes the window). Flag OFF byte-identical (16 sites + moderation; pins named). Knobs `ANTHROPIC_MAX_RETRIES` (2), `ANTHROPIC_CALL_DEADLINE_SECONDS` (25), `ANTHROPIC_CLASSIFY_LLM_TIMEOUT` (4.0), `ANTHROPIC_VISION_TIMEOUT_SECONDS` (20.0), `ANTHROPIC_TAIL_RESERVE_SECONDS` (6.5); credential `ANTHROPIC_API_KEY` (NAME only; unset = fail closed, never a silent OpenAI fallback). Sonnet 5.5 (`ANTHROPIC_MODEL_ESCALATION`) only as ONE escalation per compare on refusal or schema failure under the S81-04 `escalation` lane. Moderation on Claude stays dark until the S81-07 100-case parity set passes. **Flip preconditions (all):** S81-12 LEGAL-V3 merged and live with the landing; the consent v3 OTA (S81-08) propagated; `ENABLE_REQUEST_CONTEXT_HEADERS` ON first (else every request reads consent None); `ENABLE_LLM_LEDGER_V2` ON (cost truth); S81-04 `ENABLE_LLM_SPEND_BREAKER` ON before `ENABLE_ANTHROPIC_VERDICT` (R-S03-9); S81-07 go per role (latency, refusal rate on fragrance names, structured-output acceptance incl. the open `{"type": "object"}` schema and the format + image-block combination before the vision flip, the timeout knob values); the owner's `ANTHROPIC_API_KEY` on `web`. **Flip order:** text roles -> verdict -> critic -> moderation after parity -> camera (vision) with the permission-string risk accepted or 1.0.1 live (build 3's Info.plist strings say photos go to OpenAI, app.json:220,228; the consent sheet v3 and the policy are the disclosures). **Stated limits:** see section 9; never set these flags in a local `.env`.

Owner steps (names only, in order): (1) Console: MYEZ workspace, web search disabled, spend limit; create `ANTHROPIC_API_KEY` on `web` by name (not on `price-warmer`); (2) after S81-12 + the OTA: `ENABLE_REQUEST_CONTEXT_HEADERS`, `ENABLE_LLM_LEDGER_V2`, `ENABLE_LLM_SPEND_BREAKER` ON (their own windows); (3) the pre-v3 window: `ENABLE_OPENAI_PRE_V3=true` for the window the owner chooses (default 7 days), then unset and raise `APP_MIN_VERSION`; (4) one role flag per canary window on fresh never-compared fragrance pairs written into the ledger first; watch `metadata.llm` cost and cache_read share, the `[ROUTER]` lines, the LLM_UNAVAILABLE count, the refusal rate, `/health` loop lag; rollback = unset the variable (per call, immediate); (5) never set any role flag on `price-warmer` (it has no request context: consent None).

## 9. Stated limits

1. The consent version is the CLIENT's claim (a header); the server cannot verify the sheet was shown.
2. Haiku has no server-side fallback on refusal; Sonnet escalation (capped at one per compare) is the only fallback; a refusal past the cap is an `LLMUnavailableError` non-delivery.
3. The moderation classifier is dark until parity; until then OpenAI moderation runs whenever the moderation flag is OFF, i.e. OpenAI cannot be fully OFF before parity.
4. The OpenAI free daily allowance (organisation data sharing) ends with the switch: Claude calls are billed from the first token (cost table, PLAN_S81).
5. No web search here (S81-21), no streaming, no Batch (S81-16 / S81-22), no prompt caching (`cache_control` is not sent: enable only after S81-07 measures the read share).
6. `OPEN_OBJECT_SCHEMA` acceptance and the structured-output + image-block combination are unmeasured; S81-07 settles both before the respective flips.
7. The SDK surface is measured on 1.11.0 only; the pinned 1.12.1 (or 1.13.0) is re-measured by GREEN step 2 before code.
8. `CB_RECOVERY_TIMEOUT` / threshold of the generic breaker apply to `anthropic` unchanged.
9. A mid-request flip of a role flag: the scope is bound at entry, so a flag turned ON after entry records its Claude calls nowhere (cost missing for that request only); a flag turned OFF mid-request sends the rest to OpenAI.
10. Off-clock scripts and the warmer have no request context: with a role flag ON they route by `ENABLE_OPENAI_PRE_V3` (consent None).
11. The URL compare has no consent entry gate (dispatch-level backstop only; follow-up S81-06b); the camera refuses at its vision call (the camera's first paid call, after its refunds).
12. The escalation hooks for low identity confidence and result-gate failure exist but are unwired.
13. `metadata.total_cost` counts a Claude call only when its caller tracks a usage dict with normalised tokens (F1-9 second half); the vision cost and the 4o counter are corrected here, other `_track_gpt_cost` sites rely on the LEDGER_V2 claims match.
14. Sentry: installing the SDK changes the effective integration list; the explicit `include_prompts=False` keeps prompts out even if `send_default_pii` is ever turned on.

## 10. Out of scope

Web search (S81-21); KB-first serving (S81-17); Batch submitters and crons (S81-16 / S81-22); the legal text, consent v3 copy, SEVEN_FLAGS and T7a-c consent pins (S81-12); the client header (S81-08); device quota (S81-09); the /url/compare consent entry gate (S81-06b); escalation on identity confidence (B3 follow-up) and result gate (B2); prompt caching and the warm-up timer; any change to `guarded_llm_create`, `llm_pricing`, `llm_spend_breaker`, `request_context`; Sonnet as a default verdict model; the 1.0.1 native permission strings.

## 11. Open questions for the orchestrator

- Q1 SDK pin: 1.12.1 (newest >= 14 days at spec time) vs 1.13.0 (qualifies from 2026-10-23T15:29:08Z) vs 1.11.0 (the only measured surface). Default 1.12.1, re-measured by GREEN step 2.
- Q2 Envelope: the consent refusal reuses `LLM_UNAVAILABLE` (build 3's engine-unavailable copy) with no new key; an additive `reason: "CONSENT_UPDATE_REQUIRED"` would need a text_routes detail change and has no reader before the OTA. Default: no new key.
- Q3 Venv install timing: installing `anthropic` into the shared venv reddens SR8 (`test_u8d_pin_integration_list_unchanged`, `BASE_INTEGRATIONS`) in every sibling worktree on this box until they rebase onto this unit; CI is consistent (lock + code in one PR). Install just before GREEN and tell sibling lanes, or install into a separate venv for this unit.
- Q4 PROVIDER_CONFIGS: the brief asks for an `anthropic` entry; it would change `/admin` usage output in both flag states and the breaker does not need it. Default: no entry (the unbxd precedent).
- Q5 Manifest row: `public_name: false` with category "third-party AI service" (present in both policies at :57) keeps T7a green until S81-12 names Anthropic; alternative = a gated row, which needs an eighth Q10 flag (S81-12's SEVEN_FLAGS). Default: the public_name false row.
- Q6 Raised caps and the open schema: the per-site Claude caps in `SITES` are inferred (x1.3 tokenizer, JSON wrapping); S81-07 measures and a data PR adjusts. Accept as constants (not env knobs)?
- Q7 Sonnet thinking: `between_tools` is inferred from the bundled docs (R0-8 evidence 20); S81-07 to confirm before `ENABLE_SONNET_ESCALATION`.
- Q8 Moderation on a pre-v3 refusal is fail-open (the base contract) because the compare entry has already refused; confirm, or make the Claude moderation path fail closed.
- Q9 The S81-05 P1 pin edit (E9) lands in this unit's PR against the merged S81-05 file; confirm the allowlist names {consent_version, header_state}.

Not done in this spec: no RED file, no prototype, no mutation run, no comm-set run at base (GREEN runs base and head), no measurement of the pinned SDK surface (not installed), no live or provider call.
