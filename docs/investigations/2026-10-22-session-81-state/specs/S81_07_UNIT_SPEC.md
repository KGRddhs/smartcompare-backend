# S81-07 MEAS-CLAUDE-GATE unit spec (measured at 6b909e0a): ONE script `scripts/meas_claude_gate.py` (the Claude go / no-go measurement harness, run ONLY by the ops lane under the owner's 15 USD cap with the owner's TEST key), its fixtures under `tests/fixtures/s81_s07/`, its tests `tests/test_s81_s07_meas_harness.py`; NO flag, NO byte under app/

- Unit: S81-07 MEAS-CLAUDE-GATE. FOCUS (LC-1: a credential path and a spend path; R-S07-11). Chain: this spec -> Opus adversarial spec review -> RULINGS_S81_07 -> RED -> gate -> GREEN -> TWO adversaries (correctness; security-and-spend) -> fix rounds -> final round. The merge waits for the end of the merge freeze on main (#378's rebase round, RULINGS_CLAUDE_PATH "Slots and merges"); the ops lane may run the harness from the reviewed branch before the merge (R-S07-11).
- Flag: NONE. No `ENABLE_*`, no knob, no migration, no client file, no requirements change (R-S07-1). The invariant that replaces flag-OFF identity (section 2.13): no byte under `app/`, `migrations/`, `SmartCompareApp/`, `requirements*.in|txt`, `.github/`, `.githooks/` moves; every existing test result is unchanged; the script opens no socket in `--dry-run` and in every test (netguard).
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-s07`, detached at base `6b909e0a92067d6b3562eee325e4956c116441f7` (`git rev-parse HEAD`), `git status --short` EMPTY at the start and after every probe of this run (this file sits under the gitignored `.qa-s80/`, `.gitignore:72 .qa-*/`). Branch for GREEN: `feature/s81-s07-meas-claude-gate`.
- Evidence: the unit brief `S81_07_BRIEF.md` (R-S07-1..R-S07-12 binding, Q1-Q8 answered in section 11 / inline); PLAN_S81.md:144 (the unit text), :86 (the VERIFY flip-gate text: "a 20-call latency/token spike per setting, count_tokens on 20 saved fragrance compares, a smoke20 regression plus the WINNER_INDEX_MISMATCH rate ..., and the refusal rate on fragrance names"), :184 (flip order), :187 ("spike budget [<= $15]"); RULINGS_S81_06 R-S06-1 / R-S06-7 / R-S06-8 / R-S06-13 / R-S06-15 and GATE_S81_06 GC-6 (S81-07 measures acceptance and values before each flip); RULINGS_S81_03 R-S03-4 (the pricing re-verification); RULINGS_S81_04 R-S04-3 / R-S04-9; RULINGS_CLAUDE_PATH step 6; the common brief (R-A1 / R-A13 / R-A14 / R-A15, LC-1..LC-9, the MOVING MAIN line 2026-11-11 20:30 = 6b909e0a, the two-lanes-one-box rule); production flag state from the newest dated ledger line (the session-81 ledger copy: every `ENABLE_ANTHROPIC_*` unset; the S81-07 sweep "run by the ops lane ... under the ruled cap of 15 USD, with the key only in that one run's environment").
- Sister units and contracts (consumed READ-ONLY, never edited): S81-06 ANTHROPIC-ROUTER (#374; `SITES`, `to_claude_request`, `_escalation_request`, `ANTHROPIC_BASE_URL`, `MODERATION_*`, `moderate_with_claude`, `ClaudeChatResult`, the exception classes); S81-03 (`llm_pricing.price_call`, `anthropic_usage_record`, the Anthropic rows, `HAIKU_LONG_CONTEXT`, `WEB_SEARCH_USD_PER_REQUEST`); S81-04 (`llm_spend_breaker.prompt_token_upper_bound`, `upper_bound_usd`, `conservative_bound_usd`: pure functions, no Redis); `model_config.anthropic_model` / `anthropic_escalation_model`. Known rebases: CLAUDE.md (the block after the newest block before `## Tests`; S81-12 #378 lands first in the freeze), `tests/_env_safety.py` (E1, a one-line append to `CREDENTIALS_UNSET`; any unit appending there unions by hand). Consumers of this unit's OUTPUT: every `ENABLE_ANTHROPIC_*` / `ENABLE_SONNET_ESCALATION` flip (CLAUDE.md:508 "S81-07 go per role"), S81-21 (the web-search design input), RULINGS_S81_07 (the pass bars).
- Personal-data rule: no real names, emails, phone numbers, device ids, account ids or keys in this file or anything the unit writes. Product names in fixtures are PUBLIC fragrance product names (brands and lines), never a person; synthetic snippets and texts only (R-S07-6); the test canary is built at run time by concatenation and is not a credential shape; no constant whose NAME contains access / auth / api / credential / creds / key / password / secret / token holds a high-entropy literal (the gitleaks keyword rule).
- Measurement location: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/458aba65-975c-438f-b716-170c7d51b119/scratchpad/s07/spec/` (`probe_sdk.py` + `probe_sdk.json` (the pinned SDK surface through `httpx2.MockTransport`, no socket), `probe_capture.py` + `probe_capture.json` (the twelve prompt builders driven offline through a capture seam, 0 sockets), `base_pins.log`, `comm.py` + `comm_union.txt`). Nothing in the worktree was written except this file.

## 0. What the unit does

A read-only, offline-testable measurement harness that answers the go / no-go of every Claude role before its flip:

1. `scripts/meas_claude_gate.py` NEW (a leaf; nothing under `app/` imports it; ASCII, LF). Sub-commands = stages, each with its own cap, ledger and report, run by the ops lane in the order A -> M -> V -> W, which may stop after any (R-S07-2): `text` (stage A, the critical path: TEXT / VERDICT / CRITIC / SONNET_ESCALATION), `moderation` (stage M: the 100-case parity set, window 14), `vision` (stage V: owner-written photos only, else NOT RUNNABLE), `web_search` (stage W: OFF unless the owner's dated line is passed), `report` (renders `<out>/REPORT.md` from the stage results, $0, no network). Every stage has `--dry-run` (builds every request, prices every worst case, opens no socket, reads no key).
2. Every TEXT request is built by the APP'S OWN prompt builders (the twelve dispatch functions, driven offline through a capture seam on `llm_router.route`) and converted by the router's own `to_claude_request` (R-S07-8); the moderation request by the router's own `moderate_with_claude` with its chokepoint replaced by the harness dispatcher; the Sonnet shape by `_escalation_request`. The harness calls the SDK directly with its own client (no `guarded_anthropic_create`: no breaker, no ledger row, no Redis).
3. Key handling (FOCUS, R-S07-3): ONE variable read by NAME (`MEAS_ANTHROPIC_TEST_KEY`), the client built with the key passed explicitly, a names-only refusal of every `ANTHROPIC_*` name and of the import-time production names, the value never in argv / logs / outputs / reprs / exception text.
4. Spend (FOCUS, R-S07-4 / R-S07-5): a hard per-stage ceiling in code, a 15.00 USD unit ceiling across every stage ledger, a worst-case-before-each-call check, a JSONL ledger appended and fsynced per call with resume, the stop conditions, SDK retries OFF.
5. Fixtures `tests/fixtures/s81_s07/` (synthetic, public names only) and `tests/test_s81_s07_meas_harness.py` (fake client, netguard); E1: `MEAS_ANTHROPIC_TEST_KEY` joins `tests/_env_safety.CREDENTIALS_UNSET` (the DOTENV GUARD rule for a new credential name).
6. The CLAUDE.md unit block (names only; the run command, the stop conditions, the pass bars by reference to RULINGS_S81_07).

No agent ever runs it against the network, sets the variable or reads it (R-S07-10). The OpenAI arms of PLAN :144 (gpt-4o verdict, gpt-4o-mini vision) are NOT built (R-S07-9).

## 1. Base state (measured at 6b909e0a in this run)

### 1.1 The router contract the harness consumes (`app/services/llm_router.py`, 1,217 lines)
| what | file:line | measured |
|---|---|---|
| `ANTHROPIC_BASE_URL = "https://api.anthropic.com"` | :70 | the explicit destination (R-S06-7) |
| `ANTHROPIC_IMAGE_MAX_BYTES = 5_000_000`, `IMAGE_LONG_EDGE_PX = 2576` | :72-:73 | S81-07 confirms the published cap (R-S06-8): a stage-V finding |
| `CALL_DEADLINE_DEFAULT_SECONDS = 25.0` | :77 | the inner deadline knob default (`ANTHROPIC_CALL_DEADLINE_SECONDS`) |
| `_ACCEPTED_KWARGS` | :83-:93 | model, messages, max_tokens, max_completion_tokens, temperature, response_format, store |
| `JSON_ONLY_INSTRUCTION`, `_FENCE_RE` | :96-:97 | the R-S06-1 (b) no-format sites |
| closed schemas `IMAGE_TIER3_SCHEMA` / `DISAMBIGUATE_SCHEMA` / `VISION_V1_SCHEMA` / `MODERATION_SCHEMA` | :103-:158 | every object `additionalProperties: false` |
| `MODERATION_SYSTEM_PROMPT`, `MODERATION_MAX_TOKENS = 64` | :160-:168 | |
| `class SiteSpec` | :179-:205 | role, claude_max_tokens, output_schema, expects_json |
| `SITES` | :211-:228 | 16 keys: classify 32 / parse 768 / specs 1536 / price 512 / price_training 384 / reviews 1024 / verdict 1536 / verdict_fallback 1536 / image_tier3 256 (schema) / vision_v2 1536 (B3 V2 schema) / vision_v1 768 (schema) / specs_targeted 384 / specs_synthesized 512 / disambiguate 256 (schema) / url_extract 1200 / critique 512 (critic) |
| exception classes (messages avoid SDK text) | :235-:273 | |
| `_anthropic_client_factory` | :279-:280 | `importlib.import_module("anthropic").AsyncAnthropic(**kw)` |
| `_anthropic_api_key()` reads `ANTHROPIC_API_KEY` | :367-:371 | the PRODUCTION name: the harness never calls it (R-S07-3 (e)) |
| `classify_timeout(base)` / `vision_timeout()` / `tail_reserve_seconds_for_request()` | :399-:414 | ANTHROPIC_CLASSIFY_LLM_TIMEOUT 4.0, ANTHROPIC_VISION_TIMEOUT_SECONDS 20.0, ANTHROPIC_TAIL_RESERVE_SECONDS 6.5 (`_float_knob` :382-:392) |
| `to_claude_request(site, kwargs)` | :718-:755 | model = `_model_config.anthropic_model(spec.role)`; system joined; image parts -> blocks; `thinking {"type": "disabled"}`; `output_config {"effort": "low"}` (+ `format` when the site has a schema); `max_tokens` = SITES cap; NO temperature, NO `cache_control`; unknown kwarg -> `AnthropicShapeError` |
| `ClaudeChatResult.from_message` | :827-:842 | finish "length" on max_tokens / model_context_window_exceeded |
| `_classify(exc)` | :855-:876 | by class and status_code, never message |
| `_client_for(key)` | :879-:887 | factory(api_key=key, max_retries=`anthropic_max_retries()` (default 2), base_url=ANTHROPIC_BASE_URL) |
| `guarded_anthropic_create` | :921-:1022 | `client.messages.create(model, system or NOT_GIVEN, messages, max_tokens, thinking, output_config, timeout=deadline)` at :968-:977: NON-streaming; refusal = `stop_reason == "refusal"` -> `AnthropicRefusalError` :1019-:1021 |
| `_normalise` (fence strip, v1 unwrap) | :1028-:1046 | |
| `_escalation_request` | :1066-:1072 | model = `anthropic_escalation_model()`, `thinking {"type": "between_tools"}` (the shape S81-07 confirms, R-S06-15) |
| `_schema_failure` | :1075-:1083 | finish length or `json.loads` failure |
| `route` | :1086-:1123 | flag first; the capture seam replaces this module attribute |
| `_moderate_once` / `_moderate_step` / `moderate_with_claude` | :1138-:1217 | `_moderate_once` calls the module-global `guarded_anthropic_create` at :1144 (patchable by attribute); body fenced in `<USER_INPUT>` with `neutralize_prompt_tags`; fails CLOSED (refusal / unavailable / malformed) |

The fifteen live call sites (the census; `critique` has NO caller since S81-22b): `extraction_service.py` :1404 classify (`classify_category_llm` :1387, wrapped by `asyncio.wait_for(..., timeout=_llm_router.classify_timeout(_CLASSIFY_LLM_TIMEOUT))` :1413; `_CLASSIFY_LLM_TIMEOUT` = env `CLASSIFY_LLM_TIMEOUT` 4.0 at :1384), :1544 parse (`parse_product_query` :1531), :1611 specs (`extract_specs` :1584), :1773 price (`extract_price` :1750; search context sliced `[:2000]` at :1771), :1825 price_training (`extract_price_from_training_data` :1805), :1890 reviews (`extract_reviews` :1863), :2696 verdict and :2738 verdict_fallback (`generate_comparison` :2552); `image_service.py` :187 image_tier3 (`extract_image_via_gpt` :154); `openai_service.py` :477 vision_v2 (`_identify_products_v2` :459, timeout `_llm_router.vision_timeout()` :473), :649 vision_v1 (`identify_products` :571), :768 specs_targeted (:730), :843 specs_synthesized (:792), :905 disambiguate (:865); `url_extraction_service.py` :960 url_extract (`extract_with_ai` :915; page text sliced `[:4000]` at :939). `structured_comparison_service.py` :1905 `tail_reserve_seconds_for_request()`; the leg bounds the LLM call runs inside: `_PHASE1_TIMEOUTS` :6026 specs 8.0 / price `_PRICE_RACE_TIMEOUT` 15.0 (:1779) / reviews 10.0 / image_url 5.0; `STREAM_HARD_CAP_SECONDS` default 25.0 at :1722 (30.0 in production per CLAUDE.md).

### 1.2 The offline capture of the prompt builders (Q2; `probe_capture.json`)
Measured in a fresh `-I` process: every `ANTHROPIC_* / OPENAI_* / UPSTASH_* / SUPABASE_* / SERPER_* / ENABLE_*` name removed; `socket.socket.connect` and `socket.getaddrinfo` guarded (loopback allowed for the proactor self-pipe); `dotenv.load_dotenv` and `dotenv.main.load_dotenv` replaced by a counting no-op BEFORE any app import; `llm_router.route` replaced by a coroutine that records `(site, kwargs)` and raises; `get_client` of the four modules replaced by `lambda: object()`; an in-process placeholder (not a key shape) in `OPENAI_API_KEY` because `openai_service.py:38` builds `client = AsyncOpenAI(...)` AT IMPORT and raises `OpenAIError` with no key (measured: the first run crashed there). Result: ALL TWELVE text sites captured (classify, parse, specs, price, price_training, reviews, verdict, image_tier3, specs_targeted, specs_synthesized, disambiguate, url_extract); 0 blocked sockets; 2 load_dotenv calls intercepted (extraction_service.py:5 and url_extraction_service.py:6 call `load_dotenv(override=True)` at import: an unguarded harness would load a `.env` from the checkout into its own environment); every capture converted by `to_claude_request` with keys {max_tokens, messages, model, output_config, system?, thinking}, model `claude-haiku-5-5`, caps equal to SITES; `has_format` True only for image_tier3 and disambiguate. Prompt characters at the probe's synthetic inputs (12 snippets per context): classify 392, parse 2,822, specs 12,302, price 3,608, price_training 1,133, reviews 4,744, verdict 12,222, image_tier3 884 (no system part), specs_targeted 2,031, specs_synthesized 695, disambiguate 402, url_extract 1,344. verdict_fallback is reached only when the first verdict dispatch fails; the harness captures it by making the capture seam raise a non-LLM exception on `verdict` (GREEN measures the branch; if unreachable offline the setting is NOT RUNNABLE, stated).

Importing `app.services.llm_router` alone (measured): 0.81 s, 11 app modules (`api_budget_service`, `cache_service`, `llm_pricing`, `llm_router`, `llm_spend_breaker`, `model_config`, `openai_pricing`, `app.utils.async_utils`, `app.utils.request_context`, packages), no `anthropic` / `openai` / `supabase` / `upstash_redis` import, 0 dotenv calls. `cache_service.py:16-17` reads `UPSTASH_REDIS_URL` / `UPSTASH_REDIS_TOKEN` at import and `:166 redis_client = _build_redis_client()` builds an Upstash client when both are set: the harness refuses both names (2.3).

### 1.3 The pinned SDK (Q1; `anthropic==1.12.1` on `.venv-qaren` AND `.venv-s81-06`, Python 3.12.9; transport package `httpx2` 2.12.0, NOT `httpx` 0.28.1; measured through `httpx2.MockTransport`, `probe_sdk.json`)
| item | measured |
|---|---|
| `AsyncAnthropic.__init__` params | api_key, auth_token, credentials, config, profile, webhook_key, base_url, timeout, max_retries, default_headers, default_query, http_client, middleware, _strict_response_validation, _token_cache |
| env reads (`anthropic/_client.py` :656-:690) | an explicit `api_key` disables the `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` env reads (`has_explicit_credential`) and the profile / federation discovery (`ANTHROPIC_PROFILE`, `ANTHROPIC_IDENTITY_TOKEN[_FILE]`, `ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_ORGANIZATION_ID`); an explicit `base_url` wins over `ANTHROPIC_BASE_URL`; `ANTHROPIC_CUSTOM_HEADERS` is ALWAYS read and merged into the default headers (measured: a planted `X-Decoy: 1` was SENT with an explicit key and base_url); `ANTHROPIC_WEBHOOK_SIGNING_KEY` read when `webhook_key` is None; `ANTHROPIC_LOG` (`_utils/_logs.py:17`) = debug / info turns on the `anthropic` and `httpx2` loggers |
| `max_retries=0` | honoured: exactly 1 request on 400 / 401 / 403 / 404 / 413 / 429 / 500 / 503 / 529 (`n_requests` 1 each); SDK defaults `DEFAULT_MAX_RETRIES = 2`, `DEFAULT_TIMEOUT = Timeout(600, connect=5.0)` (`_constants.py:9-:11`) |
| request | `POST https://api.anthropic.com/v1/messages`, header `x-api-key` = the key, no `authorization`; 18 header names incl. `anthropic-version`, `x-stainless-*` |
| exceptions (class, MRO) | 400 BadRequestError, 401 AuthenticationError, 403 PermissionDeniedError, 404 NotFoundError, 413 RequestTooLargeError, 429 RateLimitError, 500 / 503 InternalServerError, 529 OverloadedError (all `APIStatusError` -> `APIError` -> `AnthropicError`); transport failure -> `APIConnectionError` ("Connection error.") |
| key echo | `str` / `repr` / `traceback.format_exception` / `repr(vars(exc))` of every class: canary ABSENT; BUT `exc.response.request.headers` HOLDS the key (any code that serialises `exc.response` or its request leaks it), and `str(exc)` CARRIES THE RESPONSE BODY (a planted body marker was in `str(exc)` for every status): the harness records TYPE + status only, never `str(exc)` |
| client / response repr | canary absent from `repr(client)`, `str(client)`, `repr(resp)`; `client.api_key` holds it (never serialised) |
| debug logging | 103 DEBUG lines at level DEBUG over the probe, canary absent (the auth headers are not in the logged options) but the synthetic request bodies are; the harness pins the `anthropic`, `httpx2`, `httpx`, `httpcore` loggers at WARNING and refuses `ANTHROPIC_LOG` (by the prefix rule) |
| proxies (Q7) | `anthropic.DefaultAsyncHttpxClient()` mounts the environment proxy (`get_environment_proxies()` -> `urllib.getproxies()`, which on Windows also reads the REGISTRY) EVEN with `trust_env=False` (1 mount in both cases); a plain `httpx2.AsyncClient(trust_env=False)` (with or without an explicit `httpx2.AsyncHTTPTransport()`) has 0 mounts; `trust_env=True` has 2 |
| `messages.create` params | max_tokens, messages, model, cache_control, container, diagnostics, inference_geo, metadata, output_config, service_tier, stop_sequences, stream, system, thinking, tool_choice, tools, user_profile_id, workspace_id, extra_*, timeout; `thinking {"type": "disabled"}` and `output_config {"effort": "low"}` accepted by the client-side types (the server's acceptance is a stage-A finding) |
| streaming (TTFT) | `create(stream=True, **same)` sends the same body plus `"stream": true`; events message_start, content_block_start, content_block_delta, content_block_stop, message_delta, message_stop |
| `messages.count_tokens` | params messages, model, cache_control, output_config, output_format, system, thinking, tool_choice, tools, ... (NO max_tokens); `POST /v1/messages/count_tokens` -> `.input_tokens` |
| `models.retrieve(model_id)` | `GET /v1/models/<id>` -> fields capabilities, created_at, deprecated_at, display_name, id, lifecycle, line, max_input_tokens, max_tokens, retires_at, type |
| `Usage` fields | cache_creation, cache_creation_input_tokens, cache_read_input_tokens, inference_geo, input_tokens, output_tokens, output_tokens_details, server_tool_use (web_search_requests, web_fetch_requests), service_tier |
| web search tool types | `web_search_20250305`, `web_search_20260209`, `web_search_20260318` (params incl. allowed_domains, blocked_domains, max_uses, user_location) |

### 1.4 Pricing and bounds (`app/services/llm_pricing.py`, `llm_spend_breaker.py`)
`ANTHROPIC_PRICE_TABLE_AS_OF = "2026-10-22"` :38; `ANTHROPIC_PRICE_USD_PER_1M` :39-:48 (haiku input 0.10 / output 0.50 / cache_read 0.01 / write_5m 0.125 / write_1h 0.20; sonnet 2.00 / 10.00 / 0.10 / 2.50 / 4.00); `HAIKU_LONG_CONTEXT` :59-:67 (threshold 100,000 prompt tokens; 0.50 / 2.50 / 0.05 / 0.625 / 1.00); `LONG_CONTEXT_THRESHOLD_PROMPT_TOKENS` :73-:76 (sonnet 200,000 -> unpriced above); `WEB_SEARCH_USD_PER_REQUEST = 0.01` :80; `price_call(...)` :173-:214 (None, never 0, when unpriceable); `anthropic_usage_record(model, usage, ...)` :385-:437 (never raises; reads the cache_creation breakdown and `server_tool_use.web_search_requests`). `llm_spend_breaker.prompt_token_upper_bound(messages, response_format, tools, provider, model)` :448 (an UPPER bound: 16 + per message 4 + the UTF-8 bytes; images at the provider bound), `upper_bound_usd(provider, model, prompt_tokens, max_tokens, web_search_max_uses)` :496, `conservative_bound_usd(...)` :531 (the Sonnet row for an unpriced Anthropic call): pure, no Redis, never raise.

### 1.5 Models (`app/services/model_config.py`)
`_ANTHROPIC_ROLE_DEFAULTS` :217-:223 (every role `claude-haiku-5-5`), `_ANTHROPIC_ESCALATION_DEFAULT = "claude-sonnet-5-5"` :224, `anthropic_model(role)` :227-:234 (env `ANTHROPIC_MODEL_<ROLE>`), `anthropic_escalation_model()` :237-:243, `anthropic_max_retries()` :246-:249 (production default 2: the harness uses 0 deliberately, R-S07-5). With every `ANTHROPIC_*` name refused (2.3) the harness measures exactly the default ids.

### 1.6 The existing offline eval harness (Q6; `scripts/shadow_experiments.py`, 1,744 lines)
It reconstructs verdict inputs from the L2 `product_*` tables (Supabase reads: `_fetch_l2_rows_for_category` :659, `_load_all_l2_rows` :681; docstring :19-:28) and grades with `scripts.eval_runner` functions (`grade_arm_verdict` :484 imports `extract_winner_index`); arms are OpenAI only (`arm_baseline_4o` :1054 ...); `_compute_scores_summary_offline` :754-:776 runs the real `scoring_service` offline and builds the summary through `text_sanitize.dedup_brand_name` (it avoids importing the orchestrator because that builds AsyncOpenAI at import). Gold set `data/validation_gold_truth.json` (200 queries; 18 fragrances; keys category, expected_prices, expected_specs, expected_winner_index, expected_winner_rationale, forbidden_facts, id, max_wall_seconds, query, region): its winner labels were made against REAL product data the harness may not read (R-S07-6). Ruling proposed (Q6): the verdict eval does NOT reuse shadow_experiments' input path (a database read) nor its OpenAI arms (R-S07-9); it reuses ONLY the pattern of `_compute_scores_summary_offline` (scoring_service + dedup_brand_name, $0) to label a SYNTHETIC 60-case fragrance gold set at fixture-build time (2.9).

### 1.7 Sets in the repo (Q3)
| set | in repo | this unit |
|---|---|---|
| fragrance gold set (60) | no (18 fragrance queries in `data/validation_gold_truth.json`, labels tied to real data) | writes `verdict_gold.json` SYNTHETIC (60 pairs, labels = the offline deterministic winner) |
| fragrance names for the refusal rate | `data/fragrance_lexicon.json` (category words, not product names) | writes `fragrance_names.json` (100 public names: 50 EN, 30 Arabic-script, 20 names that look sensitive out of context, e.g. "Opium", "Poison", "Obsession") |
| 20 saved compares for count_tokens | no (saved compares are user rows: forbidden) | `compare_pairs.json` (20 synthetic compares; the verdict request built from each) |
| moderation parity set (100) | no | writes `moderation_parity.json` SYNTHETIC (80 benign shopping texts incl. 25 Arabic; 20 flag-worthy texts limited to mild harassment / violence / illicit phrasing); the sexual, sexual/minors and self-harm categories are NOT synthesised in a public repo (stated limit L6; owner-written additions through `--set`) |
| packaging photos (100, 30% Arabic labels) | no | owner-written ONLY; stage V is NOT RUNNABLE without `--set <dir>` and lists what the owner supplies (2.8) |
| web-search allowed domains | the registry is a DB table (forbidden) | `web_search_domains.json` (three public retailer hosts as a stand-in; the owner may pass his list) |

### 1.8 Guards the new code must not trip (measured)
- `tests/test_model_config.py:118-:153` `TestNoStrayModelLiterals` scans `app/services/*.py` only (pattern :135-:136 `gpt-* | omni-moderation-* | claude-*` in quotes); the harness, though under scripts/, carries NO model literal either (R-S07-8; RED R32 reuses the exact regex).
- `tests/test_model_config_enforced.py:123` rglob over `app/` only.
- `tests/test_s81_kb_schema.py` P01 / P02 (`:331` / `:341`): scripts importing `kb_service` or naming kb_* table literals; the harness does neither.
- `tests/test_s81_s05_request_context.py` `_ALLOWED_CTX_FILES` (:1316): files naming the request_context module; the harness never names it (it reaches the router only).
- `tests/test_hermeticity_pins.py` (:1506, :1581 rglob over tests/): no raw tiktoken loader, no import-time tokenizer call; `tests/test_ci_gates.py` (:760, :779): `live_prod` markers on live tests (the RED file has no live test).
- `.githooks/pre-commit`: the secret scan and gitleaks keyword rule (no credential shape, no keyword-named high-entropy constant; the canary built by concatenation); black runs only on `.github/black-clean-paths.txt` (63 lines, 3 scripts entries): the new files are NOT added (no `.github` byte, R-S07-1).
- `tests/_netguard.py` (:10-:17): blocks `socket.connect` / `connect_ex` / `create_connection`, a NAME `getaddrinfo`, the proactor `ConnectEx`, curl_cffi; it guards httpx2 too (socket level). `pyt.py` loads it as the `qaren_netguard` plugin.
- `tests/_env_safety.CREDENTIALS_UNSET` (:110-:145) holds `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL` (not `ANTHROPIC_CUSTOM_HEADERS`); pinned by membership only (`test_conftest_env_safety.py:292-:381`, `test_s81_s06_anthropic_router.py:2428-:2431`, ...).

### 1.9 Idiom, libraries, line endings
No flag: the house flag idiom does not apply; parse helpers follow `_float_knob` (`llm_router.py:382-:392`: unset / blank / garbage / inf / nan / <= 0 -> default) for the CLI numbers. Libraries on the pinned venv: stdlib, `anthropic` 1.12.1, `httpx2` 2.12.0, `dotenv`; no new dependency. Line endings: the repo is `core.autocrlf=true` (`git ls-files --eol`: CLAUDE.md, tests/_env_safety.py, scripts/cron_compare_judge.py are `i/lf w/crlf`); the three NEW files are written LF (a new blob is LF in the index either way); the two EDITED files keep CRLF in the working copy through the Edit tool (a whole-file diff is a defect).

### 1.10 Base pass state (bounded runner, at 6b909e0a, every flag unset)
- `tests/test_conftest_env_safety.py tests/test_hermeticity_pins.py tests/test_model_config.py tests/test_model_config_enforced.py tests/test_shadow_experiments.py`: 264 passed, 1 skipped, 2 deselected.
  `[pyt] tag=s07-spec-base start=2026-11-11 21:42:40 end=2026-11-11 21:44:05 elapsed=85s bound=600s status=OK rc=0 log=...\scratchpad\s07\spec\base_pins.log`
  `[netguard]` lines: only the hermeticity self-tests' deliberate blocks (192.0.2.1 literals, example.com:80); no `[hermeticity]` line.
- The new files do not exist at base (`scripts/meas_claude_gate.py`, `tests/fixtures/s81_s07/`, `tests/test_s81_s07_meas_harness.py`: absent).

## 2. Contract

### 2.1 Constants (module level of `scripts/meas_claude_gate.py`; no knob, no flag)
| name | value | note |
|---|---|---|
| `ENV_VAR_NAME` | `"MEAS_ANTHROPIC_TEST_KEY"` | the ONE source of the key (R-S07-3 (a)); the constant name avoids the gitleaks keywords |
| `REFUSED_ENV_PREFIXES` | `("ANTHROPIC_",)` | every `ANTHROPIC_*` name refuses the start: the four of R-S07-3 (b) plus `ANTHROPIC_LOG`, `ANTHROPIC_PROFILE`, the federation trio, `ANTHROPIC_WEBHOOK_SIGNING_KEY`, `ANTHROPIC_MODEL_*` (which would change the measured ids) |
| `REFUSED_ENV_NAMES` | `("UPSTASH_REDIS_URL", "UPSTASH_REDIS_TOKEN", "OPENAI_API_KEY")` | the import-time production names (1.2): a Redis client at `cache_service.py:166`, an OpenAI client at `openai_service.py:38` |
| `OPENAI_IMPORT_PLACEHOLDER` | a fixed non-key word (e.g. `"meas-import-placeholder"`) | set in-process ONLY after `OPENAI_API_KEY` was refused-absent, so `openai_service` imports; never sent anywhere (the capture seam replaces every dispatch) |
| `UNIT_CEILING_USD` | `15.00` | the owner's cap (ledger 2026-11-06 17:53; PLAN :187) |
| `STAGE_DEFAULTS` | `text`: max_usd 4.00, max_calls 700, max_minutes 90; `moderation`: 2.00, 250, 20; `vision`: 5.00, 450, 60; `web_search`: 3.00, 60, 20 | `--max-usd` / `--max-calls` / `--max-minutes` may LOWER, never raise (a higher value = exit 2) |
| `CONSECUTIVE_TRANSIENT_STOP` | `3` | 5xx / 529 / APIConnectionError / timeout in a row |
| `RATE_LIMIT_RETRIES` | `3` | per call id; then the setting stops |
| `RETRY_AFTER_DEFAULT_S` / `RETRY_AFTER_MAX_S` | `5` / `60` | a missing or unparsable `retry-after` -> 5; clamp 1..60 |
| `CALL_TIMEOUT_S` | `ANTHROPIC_CALL_DEADLINE` mirror = `llm_router.CALL_DEADLINE_DEFAULT_SECONDS` (25.0), read from the router constant | per call `timeout=` and the http_client timeout (connect 5.0) |
| `ROUND_SPACING_S` | `30.0` | the gap between two synthetic compares in stage A (2.6; open question OQ-3) |
| `WEB_SEARCH_RESULT_TOKENS_BOUND` | `60000` | the pre-call input bound added per allowed search (the server injects results the harness cannot pre-count; stated limit L8) |
| `GO_THRESHOLDS` | section 2.11 | proposed here, ruled in RULINGS_S81_07 |
| exit codes | `EXIT_OK 0`, `EXIT_REFUSED 2`, `EXIT_CRASH 3`, `EXIT_UNIT_CEILING 4`, `EXIT_AUTH 5`, `EXIT_STOPPED 6`, `EXIT_INTERRUPTED 130` | a NOT RUNNABLE stage is EXIT_OK with the result row |

### 2.2 CLI
`python -m scripts.meas_claude_gate <stage> --out <dir> [--dry-run] [--max-usd X] [--max-calls N] [--max-minutes M] [--set <path>] [--reps N] [--owner-line "<YYYY-MM-DD HH:MM>"] [--settings a,b,...]` with `<stage>` in {text, moderation, vision, web_search, report}. `--out` is REQUIRED and must resolve OUTSIDE the repository root (`Path(__file__).resolve().parents[1]`; inside -> exit 2). The key is never an argument. `main(argv=None) -> int` is the entry; `if __name__ == "__main__": sys.exit(main())`.

### 2.3 Start sequence (in this order; every refusal = one stderr line `meas_claude_gate: refused: <reason> names=<sorted NAMES>` (names only), exit 2, NO client built, NO app module imported, NO file written under --out)
1. parse argv (the numeric parsers reject non-finite / <= 0; a value above the stage default refuses);
2. `--out` outside the repo (created if missing, mode default);
3. the environment scan: every name with a `REFUSED_ENV_PREFIXES` prefix and every `REFUSED_ENV_NAMES` member PRESENT (even empty) -> refuse, listing the names;
4. live mode only (not `--dry-run`, not `report`, not a NOT RUNNABLE stage): `_read_key()` = `os.environ.get(ENV_VAR_NAME)`; None, empty or whitespace -> refuse naming `ENV_VAR_NAME`; the value is held in ONE local passed to `_build_client` and nowhere else (never a module global, never logged, never in a dict that is serialised);
5. logging hygiene: `logging.getLogger(n).setLevel(logging.WARNING)` for `anthropic`, `httpx2`, `httpx`, `httpcore` (the SDK's `setup_logging` reads `ANTHROPIC_LOG`, already refused);
6. dotenv neutralised: `dotenv.load_dotenv` and `dotenv.main.load_dotenv` replaced by a counting no-op BEFORE the first app import (a module-level seam `_install_dotenv_guard()`);
7. the placeholder `OPENAI_API_KEY = OPENAI_IMPORT_PLACEHOLDER` set in-process, then `_import_app_modules()` (llm_router, model_config, llm_pricing, llm_spend_breaker, extraction_service, openai_service, image_service, url_extraction_service, scoring_service, text_sanitize, prompt_sanitizer);
8. the environment scan AGAIN (step 3) after the imports, ignoring only the harness's own placeholder: any new refused name (a `.env` load that slipped through) -> refuse;
9. the unit ceiling: the sum of `usd` over every `<out>/*/spend.jsonl` + this stage's max_usd > `UNIT_CEILING_USD` -> exit 4 (names-only line `refused: unit ceiling`), nothing sent;
10. live mode: `_build_client(value)` = `_client_factory(api_key=value, base_url=llm_router.ANTHROPIC_BASE_URL, max_retries=0, timeout=CALL_TIMEOUT_S, http_client=httpx2.AsyncClient(trust_env=False, follow_redirects=False, timeout=httpx2.Timeout(CALL_TIMEOUT_S, connect=5.0)))`; `_client_factory(**kw)` = `importlib.import_module("anthropic").AsyncAnthropic(**kw)` (the test seam). The names of any proxy variable present (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, any case) are recorded in results.json `proxy_env_ignored` (names only): `trust_env=False` makes them inert (1.3), the registry proxy included.

### 2.4 The capture seam (R-S07-8)
`capture_request(site, builder_call) -> dict`: sets `llm_router.route` to a recorder for the duration of ONE builder call (restored in `finally`), awaits the builder with the fixture's synthetic arguments, and returns `llm_router.to_claude_request(site, captured_kwargs)`. The `get_client` attributes of the four site modules are replaced by `lambda: object()` for the capture only. A builder that reaches no `route` call (returns early) -> the setting is NOT RUNNABLE with reason `builder_did_not_dispatch`. The harness NEVER writes a request dict by hand for a router site; the one exception is stage W (no router shape exists: S81-21 designs it), whose request is built from `to_claude_request` of the nearest site plus `tools` (2.10).

### 2.5 The dispatcher and the record of one call
`async _send(client, request, *, setting, site, call_id, stream=False) -> dict`: in order: (a) the worst case `worst_usd` = `llm_spend_breaker.upper_bound_usd("anthropic", request["model"], llm_spend_breaker.prompt_token_upper_bound(<system as a message> + request["messages"], response_format=request["output_config"].get("format"), tools=request.get("tools"), provider="anthropic", model=request["model"]), request["max_tokens"], web_search_max_uses)` (+ `WEB_SEARCH_RESULT_TOKENS_BOUND` at the input rate per allowed search), else `conservative_bound_usd(...)` when unpriced; (b) stop with `budget` when `stage_spent + worst_usd > max_usd` OR `unit_spent + worst_usd > UNIT_CEILING_USD`; `max_calls` / `max_minutes` likewise; (c) `client.messages.create(**request, timeout=CALL_TIMEOUT_S)` (stream: `create(stream=True, ...)` iterated, `ttft_ms` at the first `content_block_delta`); (d) the record (2.7) priced by `llm_pricing.anthropic_usage_record(model, resp.usage, role=..., latency_ms=..., stop_reason=...)["cost_usd"]`; an unpriced usage (None) books `worst_usd` (the R-S04-3 rule); (e) append + flush + `os.fsync` the ledger line; (f) write `raw/<call_id>.json` = {content blocks as dicts, stop_reason, usage dict, model} (never a header, never `resp._request_id` beyond the plain id string). An exception books `usd 0.0`, `error_class = type(exc).__name__`, `status = exc.status_code` (int) or None, and NO message text.

`call_id` = the first 16 hex of `sha256("<stage>|<setting>|<site>|<case_id>|<rep>")` (the name avoids the keyword rule; no user value enters it).

### 2.6 Stage A `text` (settings in this order; `--settings` may select a subset; R-S07-2)
| setting | calls | built by | what is recorded |
|---|---|---|---|
| `A0_capabilities` | 2 (`models.retrieve` for `anthropic_model("text")` and `anthropic_escalation_model()`; the distinct ids of the five roles) | SDK | max_input_tokens, max_tokens, capabilities, lifecycle, retires_at; $0 |
| `A1_sites` | 20 rounds; one round = one synthetic compare in the code's order: classify -> parse -> {specs x2, price x2} concurrently -> {reviews x2, image_tier3 x2} concurrently -> verdict; then price_training, specs_targeted, specs_synthesized, disambiguate, url_extract, verdict_fallback once each; `ROUND_SPACING_S` between rounds | capture seam + `to_claude_request` | per call: latency_ms, usage, cache_read share, stop_reason, refusal, JSON validity after the router's own `_normalise` (fence strip), schema acceptance (no 400 on a format site), `max_tokens` hits |
| `A2_ttft` | 20 verdict + 20 specs requests with `stream=True` (the body otherwise equal to A1's) | as A1 | ttft_ms, latency_ms |
| `A3_sonnet_between_tools` | 20 | `llm_router._escalation_request(<A1 verdict request>)` | acceptance (no 400), latency, usage, JSON validity |
| `A4_refusal_names` | 100 (`parse` builder over "<name> vs <name>" pairs from `fragrance_names.json`, every name twice across the set) | capture seam | stop_reason `refusal` count by language (en / ar / sensitive-looking) |
| `A5_count_tokens` | 20 (`messages.count_tokens(model, system, messages, output_config, thinking)` of the verdict request of each `compare_pairs.json` compare) | capture seam | input_tokens; $0 |
| `A6_verdict_eval` | 60 cases x `--reps` (default 2) = 120 | capture seam over `generate_comparison` with each `verdict_gold.json` product pair + its offline `scores_summary` | winner_index parsed from the JSON; `winner_mismatch` = model winner_index != the case's gold (deterministic) winner (the response_builder WINNER_INDEX_MISMATCH rule); rep agreement |

The CRITIC role has NO live dispatch site at this base (SITES `critique` has no caller since S81-22b): the report's CRITIC row reads `NOT RUNNABLE: no builder` (stated; the orchestrator rules whether `ENABLE_ANTHROPIC_CRITIC` keeps a place in window 13, OQ-6). Vision sites are stage V.

### 2.7 The ledger line (`<out>/<stage>/spend.jsonl`; one JSON object per line, sorted keys, closed key set)
`call_id, stage, setting, site, case_id, rep, model, kind ("create" | "stream" | "count_tokens" | "models_retrieve"), ok (bool), usd (float), worst_usd (float), input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, web_search_requests, stop_reason, error_class, status, latency_ms, ttft_ms, retry (int), ts (UTC ISO seconds)`. A line is COMPLETED when `ok` is true or `error_class` is a non-transient class (400 / 401 / 403 / 404 / 413 or a local `AnthropicShapeError`); a re-run skips every completed `call_id` (RESUME) and never re-sends it; a transient line (429 / 5xx / 529 / connection / timeout) is retried on resume. `stage_spent` and `unit_spent` are the sums of `usd` read back from disk at start and kept in memory after.

### 2.8 Stage M `moderation` and stage V `vision`
- M: `moderation_parity.json` (or `--set <file>` of the same shape: `{id, text, lang, expected_flagged, category}`): for each case `llm_router.moderate_with_claude(text)` runs with `llm_router.guarded_anthropic_create` replaced (module attribute, restored in `finally`) by the harness dispatcher (2.5), which returns `llm_router.ClaudeChatResult.from_message(resp, model, record)` and raises `llm_router.AnthropicRefusalError` on `stop_reason == "refusal"`; `llm_router.consume_escalation` replaced by a once-per-case True (the per-compare cap of 1), so the PRODUCTION decision path (fail-closed reasons, the uncertain -> Sonnet re-run) is what is measured. Recorded: allowed / reason per case; false-positive rate on `expected_flagged false`, recall on true, fail-closed rate (refusal + unavailable + malformed), Haiku-only and with-escalation figures, latency p50 / p95.
- V: without `--set <dir>` -> NOT RUNNABLE: results + REPORT list the owner's inputs: 100 owner-taken packaging photos (about 30 with Arabic labels), a `manifest.json` `[{file, label_lang ("ar" | "en" | "mixed"), expected_brand, expected_name}]`, no faces, no people, no receipts, no screens with personal data, JPEG / PNG / WebP / GIF, each under `ANTHROPIC_IMAGE_MAX_BYTES`. With a set: each photo through the capture seam of `openai_service._identify_products_v2` / `identify_products` (vision_v2 and vision_v1 requests) on Haiku (`to_claude_request`) and on Sonnet (`_escalation_request`); recorded: identity hit (brand and name match, case-insensitive token rule), latency p50 / p95 / p99 (the vision timeout proposal), usage, the image-block acceptance and the 5,000,000-byte cap confirmation (R-S06-8).

### 2.9 Fixtures (`tests/fixtures/s81_s07/`, UTF-8 JSON, LF; Arabic only inside JSON strings; public product names only; no id, cohort, profile, email, phone, device or account field)
`fragrance_names.json` (100), `compare_pairs.json` (20 compares: two products, ten synthetic snippets per product of at most 250 characters each (the production slices: price `[:2000]`, url page `[:4000]`), a synthetic product_data pair for the verdict builder), `verdict_gold.json` (60 cases: a product_data pair + `gold_winner_index` computed at build time by `scoring_service.get_scoring_service().compute_scores(...)` and `build_scores_summary(...)` with `dedup_brand_name` names, the pattern of `shadow_experiments.py:754-:776`; a PIN row recomputes every label offline), `moderation_parity.json` (100, 1.7), `web_search_domains.json` (3). A generator `tests/fixtures/s81_s07/_gen_fixtures.py` (the `_gen_*_golden.py` precedent in tests/fixtures) regenerates them deterministically.

### 2.10 Stage W `web_search`
Without `--owner-line` -> NOT RUNNABLE ("the organisation web-search switch is OFF by the owner's setting; the owner's dated ledger line is required", R-S07-2). With it: `W1_one_turn` 20 calls: the A1 `price` request plus `tools=[{"type": "web_search_20260318", "name": "web_search", "max_uses": 1, "allowed_domains": <fixture or --set list>}]`; `W2_with_format` 20 calls: the same plus `output_config.format` = the closed `IMAGE_TIER3_SCHEMA`-style object schema `{"price": number|null, "currency": string|null, "source_url": string|null}` (additionalProperties false). Recorded: acceptance of the combination (the 400 class and status, PLAN :74 "one paid call settles it"), `web_search_requests`, citations count, latency, usage. The owner line string is copied into results.json as given (a date-time, no personal value).

### 2.11 Results, REPORT.md and the proposed GO thresholds (Q5; R-S07-7; every bar ruled in RULINGS_S81_07)
`<out>/<stage>/results.json` (sorted keys: stage, settings{name: {calls, ok, usd, p50_ms, p95_ms, p99_ms, ttft_p50_ms, ttft_p95_ms, json_valid_rate, schema_accept_rate, refusal_rate, max_tokens_rate, cache_read_share, error_classes{class: n}}}, stop_reason, spent_usd, unit_spent_usd, env_var_name (= `ENV_VAR_NAME`, the NAME only), proxy_env_ignored, redactions, base_sha, price_table_as_of, not_runnable[]); `<out>/<stage>/REPORT.md` and `<out>/REPORT.md` (the `report` stage) carry the go / no-go table per role with each bar, its source, the measured value and GO / NO-GO / NOT RUN, and the three timeout proposals. Never a prefix, suffix, length or hash of the key (R-S07-3 (d)).

| role | proposed GO bar | source |
|---|---|---|
| TEXT (ENABLE_ANTHROPIC_TEXT) | per JSON site json_valid_rate >= 0.98; schema_accept_rate = 1.00 at image_tier3 / disambiguate; refusal_rate on A4 <= 0.01 overall and 0 on the 30 Arabic names' pairs above 1 refusal = NO-GO; max_tokens_rate <= 0.02 per site; latency p95: classify <= 4.0 s, specs <= 4.0 s, reviews <= 5.0 s, price <= 7.5 s, image_tier3 <= 2.5 s, every site p99 < 25.0 s | CLAUDE.md:508 criteria; `_CLASSIFY_LLM_TIMEOUT` 4.0 (extraction_service.py:1384); half of each leg bound (`_PHASE1_TIMEOUTS` specs 8.0 / reviews 10.0 / image_url 5.0, `_PRICE_RACE_TIMEOUT` 15.0) because the LLM call shares the leg with search; `CALL_DEADLINE_DEFAULT_SECONDS` 25.0 (llm_router.py:77); Haiku has no server fallback on refusal (RULINGS_S81_06 stated limits) |
| VERDICT (ENABLE_ANTHROPIC_VERDICT) | json_valid_rate >= 0.98 on verdict and verdict_fallback; A6 winner_mismatch_rate <= 0.10 and rep agreement >= 0.90; verdict p95 <= the tail proposal <= 6.5 s x 1.5 | PLAN :86 (WINNER_INDEX_MISMATCH); `ANTHROPIC_TAIL_RESERVE_SECONDS` 6.5 (llm_router.py:412-:414); the OpenAI temperature-0 baseline is NOT measurable (R-S07-9), so the bar is absolute (owner ruling) |
| SONNET_ESCALATION | A3 20 / 20 accepted with `between_tools` (no 400); json_valid_rate >= 0.95 | R-S06-15 |
| CRITIC | NOT RUNNABLE (no builder) | 2.6 |
| MODERATION (window 14) | false-positive rate on benign <= 0.01 (a fail-closed false positive blocks a delivery); recall on flag-worthy >= 0.90; fail-closed rate <= 0.01; p95 <= 3.0 s | R-S06-6 (fail closed); CLAUDE.md:508 "the 100-case moderation parity set before ENABLE_ANTHROPIC_MODERATION" |
| VISION (window 21, with NT1) | identity hit rate Haiku >= Sonnet - 0.05 and >= 0.80; p99 <= 20.0 s | `ANTHROPIC_VISION_TIMEOUT_SECONDS` 20.0 (llm_router.py:407-:409) |
| WEB_SEARCH (S81-21 input) | a design input, no flip bar: W2 accepted yes / no, p95 | F2 (PLAN :123) |
| per-compare cost | A1 p95 USD per synthetic compare <= 0.01 | CLAUDE.md "Target $0.01/comparison"; the breaker live cap 3 USD / Riyadh day (RULINGS_S81_04 item 13 defaults) / that cost = compares per day, printed |

Timeout proposals (rounded UP to 0.5 s, margin x1.25 over the measured percentile): classify = p99(classify) x 1.25; vision = p99(vision_v2) x 1.25 (stage V only); tail = p95(verdict) x 1.25; each printed beside the current knob value (4.0 / 20.0 / 6.5) and the knob NAME (`ANTHROPIC_CLASSIFY_LLM_TIMEOUT`, `ANTHROPIC_VISION_TIMEOUT_SECONDS`, `ANTHROPIC_TAIL_RESERVE_SECONDS`).

### 2.12 Output and secret hygiene
Every string the harness writes (stdout, stderr, ledger, raw, results, reports) passes `_scrub(text)`, which replaces any occurrence of the held key value with `[redacted]` and increments `redactions`; on every path the expected count is 0 (a non-zero count in results.json is itself a NO-GO line for the security review). `main` wraps the stage in `try`: `KeyboardInterrupt` -> flush, write the PARTIAL report, exit 130; any other exception -> one stderr line `meas_claude_gate: crashed class=<Type>`, a crash record in results.json (type only), exit 3; no traceback is printed (the exception object is never formatted).

### 2.13 The main invariant (replaces flag-OFF identity)
(a) `git diff --name-only 6b909e0a..HEAD` = exactly `scripts/meas_claude_gate.py`, `tests/test_s81_s07_meas_harness.py`, `tests/fixtures/s81_s07/*` (six files), `tests/_env_safety.py` (E1), `CLAUDE.md`; (b) the comm set (7.1) has no branch-only-new failure; (c) nothing under `app/` names `meas_claude_gate` (PIN P01); (d) the RED file opens no non-loopback socket (netguard lines empty for it), and `--dry-run` builds no client (R13).

### 2.14 Failure table
| condition | behaviour | exit |
|---|---|---|
| a refused name present (before or after app imports) | names-only line, nothing built or written | 2 |
| key missing / empty in live mode | names-only line naming `ENV_VAR_NAME` | 2 |
| `--out` inside the repo / bad number / above the stage default | one line | 2 |
| unit ceiling would be passed | one line, nothing sent | 4 |
| worst case does not fit / max_calls / max_minutes | the stage stops, ledger flushed, PARTIAL report | 6 |
| 401 / 403 | stop at once, never retried, report | 5 |
| 3 consecutive transient | the stage stops | 6 |
| 429 | sleep `retry-after` (clamped) up to 3 times per call id, then the setting stops; the next setting runs | 0 or 6 |
| a 400 at one call | recorded (class + status), counts against acceptance, the setting continues | 0 |
| KeyboardInterrupt | flush, PARTIAL report | 130 |
| any other exception | type-only line and record | 3 |
| V without `--set`, W without `--owner-line`, CRITIC | NOT RUNNABLE row | 0 |

### 2.15 Test seams (production values in brackets)
`_client_factory` [anthropic.AsyncAnthropic], `_read_key` [os.environ.get(ENV_VAR_NAME)], `_sleep` [asyncio.sleep], `_monotonic` [time.monotonic], `_fsync` [os.fsync], `_import_app_modules` [the eleven imports], `_install_dotenv_guard` [the no-op install], `REPO_ROOT` [Path(__file__).resolve().parents[1]].

## 3. Change list (GREEN, in this order; byte-copy every EXISTING file first into `<scratchpad>/S81-07_green_before/` with sha256)
1. NEW `tests/fixtures/s81_s07/_gen_fixtures.py` + the five JSON fixtures (2.9), generated once, committed.
2. NEW `scripts/meas_claude_gate.py` (sections 2.1-2.12; ASCII, LF; no model literal; imports at module top: stdlib + nothing from app/ (app modules only through `_import_app_modules` after the start checks)).
3. `tests/_env_safety.py`: E1, one entry `"MEAS_ANTHROPIC_TEST_KEY",` appended to `CREDENTIALS_UNSET` after `"ANTHROPIC_BASE_URL",` (:144) with a one-line comment (CRLF kept).
4. CLAUDE.md: the unit block (section 8) after the S81-04c block (:637-:640) with one blank line before `## Tests` (:641); one clause in the :341 pointer paragraph ("S81-07 MEAS-CLAUDE-GATE adds no flag: the **SESSION 81 unit (S81-07 MEAS-CLAUDE-GATE, ...)** block").
5. The frozen RED file `tests/test_s81_s07_meas_harness.py` is NOT edited by GREEN.
No other file.

## 4. Existing pins
### 4.1 Pins that change deliberately
| id | file | change | reason |
|---|---|---|---|
| E1 | `tests/_env_safety.py:110-:145` | `CREDENTIALS_UNSET` gains `MEAS_ANTHROPIC_TEST_KEY` | the DOTENV GUARD rule (common brief: a new credential-bearing name joins CREDENTIALS_UNSET in the same unit, with a pin row = R38); membership-only pins stay green (1.8) |
No other pin changes.

### 4.2 Pins that must stay green and unedited
`tests/test_conftest_env_safety.py` (the contract unset set, the overlap rule), `tests/test_hermeticity_pins.py`, `tests/test_model_config.py` (`TestNoStrayModelLiterals`), `tests/test_model_config_enforced.py`, `tests/test_shadow_experiments.py`, `tests/test_s81_s06_anthropic_router.py` (R35 membership), `tests/test_s81_s06_router_gate_rows.py`, `tests/test_s81_kb_schema.py` (P01 / P02 scripts allowlists), `tests/test_s81_s05_request_context.py` (the ctx-file allowlist walks scripts/), `tests/test_s81_s22_judge.py` / `test_s81_s22_gate_rows.py` / `test_s81_d22_nightly_learning.py` (scripts readers), the CLAUDE.md readers (`test_ci_gates.py`, `test_behavior_dimension_translation.py`, `test_s81_s04_spend_breaker.py`, `test_s81_s08b_legacy_fingerprint.py`, `test_s81_s08b_gate_rows.py`, `test_s81_s23_bypass_retire.py` and every grep reader in 7.1), the named source-scanning pins.

## 5. RED tests (ONE file `tests/test_s81_s07_meas_harness.py`, pure ASCII, LF, hermetic; every R row fails at base on an AssertionError ONLY (the module read through `importlib.util.find_spec("scripts.meas_claude_gate")` asserted not None, then imported; fixtures through `Path.exists` asserts); every P row is green at base and runs with the FULL configuration (every `ENABLE_ANTHROPIC_*` set ON, `ENABLE_SONNET_ESCALATION` ON, synthetic `ANTHROPIC_MODEL_*` absent) plus call recorders)

Fakes: `FakeAsyncAnthropic(**kw)` records its kwargs and exposes `messages.create` (scripted: a Message-like object with `content` text blocks, `stop_reason`, `usage` (an `anthropic.types.Usage`), or a raised exception), `messages.count_tokens`, `models.retrieve`; real SDK exceptions are constructed from `httpx2.Response(status, json=body, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages", headers={"x-api-key": CANARY}))` so that the request object carries the canary exactly as measured (1.3). CANARY = `"CANARY" + "VAL-" + "s07" + "q" * 12` built at run time. Every test passes `--out tmp_path/out` (outside the repo) and patches `_client_factory`, `_sleep`, `_monotonic`, `_fsync`. The `main(argv)` return is the exit code; stdout / stderr through `capsys`.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R01 | test_r01_module_and_entry | find_spec not None; `main`, `ENV_VAR_NAME`, `UNIT_CEILING_USD`, `STAGE_DEFAULTS`, the exit codes exist | RED | 3.2 |
| R02 | test_r02_env_var_name | `ENV_VAR_NAME == "MEAS_ANTHROPIC_TEST_KEY"`; `UNIT_CEILING_USD == 15.0`; `STAGE_DEFAULTS` max_usd 4.0 / 2.0 / 5.0 / 3.0 and their sum <= 15.0 | RED | 2.1 |
| R03 | test_r03_refuses_each_anthropic_name (parametrized: API_KEY, AUTH_TOKEN, BASE_URL, CUSTOM_HEADERS, LOG, PROFILE, MODEL_TEXT; value "" and "x") | exit 2; stderr names exactly that NAME and no value; factory 0 calls; `_import_app_modules` recorder 0 calls; `--out` empty | RED | 2.3 step 3 |
| R04 | test_r04_refuses_import_time_names (UPSTASH_REDIS_URL, UPSTASH_REDIS_TOKEN, OPENAI_API_KEY) | as R03 | RED | 2.3 step 3 |
| R05 | test_r05_key_missing_empty_blank | live `text` with the variable unset / "" / "  " -> exit 2, stderr names `MEAS_ANTHROPIC_TEST_KEY`, factory 0 calls | RED | 2.3 step 4 |
| R06 | test_r06_out_inside_repo_refused | `--out <repo>/tmp_s07` -> exit 2, nothing created | RED | 2.2 |
| R07 | test_r07_client_built_explicitly | factory kwargs: api_key == CANARY, base_url == `llm_router.ANTHROPIC_BASE_URL`, max_retries == 0; `http_client` is an `httpx2.AsyncClient` with `trust_env` False, `follow_redirects` False, 0 mounts even with `HTTPS_PROXY` set; results `proxy_env_ignored == ["HTTPS_PROXY"]` | RED | 2.3 step 10 |
| R08 | test_r08_canary_absent_success_path | CANARY in the variable; `text --settings A1_sites --max-calls 3`; CANARY absent from stdout, stderr and every byte of every file under `--out`; results `redactions == 0`; no 6+ character substring of CANARY in any output | RED | 2.3-2.12 |
| R09 | test_r09_canary_absent_sdk_error_path | the fake raises `BadRequestError` whose body message CONTAINS the canary and whose request headers hold it; same absence asserts; the ledger line has `error_class "BadRequestError"`, `status 400` and no message field | RED | 2.5, 2.12 |
| R10 | test_r10_canary_absent_crash_path | the fake raises `RuntimeError(CANARY)`; exit 3; stderr == `meas_claude_gate: crashed class=RuntimeError\n`; absence asserts | RED | 2.12 |
| R11 | test_r11_no_read_of_production_key | AST of the script: every `os.getenv(X)` / `os.environ.get(X)` / `os.environ[X]` has X = the Name `ENV_VAR_NAME`; no string literal `ANTHROPIC_API_KEY`; the script never references `llm_router._anthropic_api_key` / `_client_for` / `guarded_anthropic_create` except the moderation patch assignment; dynamic: with an `os.environ` recorder (a `MutableMapping` wrapper monkeypatched as `os.environ` for the run) the key `ANTHROPIC_API_KEY` is never read by `get`/`__getitem__` | RED | 2.3 |
| R12 | test_r12_sdk_loggers_pinned | after a run with the root logger at DEBUG: `anthropic`, `httpx2`, `httpx`, `httpcore` levels >= WARNING; caplog holds no record from those loggers | RED | 2.3 step 5 |
| R13 | test_r13_dry_run_no_socket_no_key | `text --dry-run` (and moderation / vision with a 1-photo tmp set / web_search with an owner line) with CANARY in the variable: exit 0; factory 0 calls; `_read_key` recorder 0 calls; `plan.json` lists every setting with calls and worst_usd; total worst_usd per stage <= its max_usd; CANARY absent | RED | 2.2, 2.5 |
| R14 | test_r14_request_equals_router (parametrized over the twelve text sites) | the kwargs the fake `messages.create` receives minus `timeout` == `llm_router.to_claude_request(site, <kwargs captured from the same builder with the same fixture args>)`; model == `model_config.anthropic_model(SITES[site].role)` | RED | 2.4 |
| R15 | test_r15_sonnet_request | A3 request == `llm_router._escalation_request(<A1 verdict request>)`; thinking `{"type": "between_tools"}`; model == `anthropic_escalation_model()` | RED | 2.6 |
| R16 | test_r16_pricing_from_usage | a usage of (1000 in, 200 out, 300 cache read) books usd == `llm_pricing.price_call("anthropic", "claude-haiku-5-5", input_tokens=1000, output_tokens=200, cache_read_tokens=300)`; a 120,000-token prompt books the long-context tier; a web search usage adds 0.01 per search; an unpriced usage books its worst_usd | RED | 2.5 (d) |
| R17 | test_r17_worst_case_stop | `--max-usd` set to one cent below the first call's worst case: 0 `messages.create` calls, exit 6, results stop_reason `budget`; a request whose input bound fits but whose `max_tokens` x output rate does not -> stopped (kills the output-term mutant) | RED | 2.5 (a)-(b) |
| R18 | test_r18_unit_ceiling | a pre-written `<out>/moderation/spend.jsonl` summing 11.50: `text` (4.00) -> exit 4, 0 factory calls; 10.99 -> starts | RED | 2.3 step 9 |
| R19 | test_r19_max_usd_lower_only | `--max-usd 4.01` on text -> exit 2; `--max-usd 0.5` accepted; nan / inf / -1 / "x" -> exit 2 | RED | 2.2 |
| R20 | test_r20_ledger_per_call | after 5 fake calls: 5 lines, each the closed key set of 2.7, `_fsync` recorder 5 calls, each line flushed before the next create (an order recorder) | RED | 2.5 (e) |
| R21 | test_r21_resume | run 1 `--max-calls 5`, run 2: the first five call_ids are never sent again; total completed ids unique; a transient line from run 1 IS re-sent | RED | 2.7 |
| R22 | test_r22_max_calls | `--max-calls 7` -> exactly 7 creates, exit 6 | RED | 2.5 (b) |
| R23 | test_r23_auth_stops_at_once (401, 403) | exactly 1 create, exit 5, no retry, report written | RED | 2.14 |
| R24 | test_r24_three_consecutive_transient | 500, 529, APIConnectionError -> stop after exactly 3 creates, exit 6; 500, 500, ok, 500, 500, ok -> no stop | RED | 2.14 |
| R25 | test_r25_rate_limit_retry_after | 429 with `retry-after: 2` x4 on one call id: `_sleep` called with 2, 2, 2; 4 creates for that id; the setting stops; the next setting's first create happens; missing header -> sleep 5; `retry-after: 999` -> 60 | RED | 2.14 |
| R26 | test_r26_wall_clock | `_monotonic` advanced past `--max-minutes 1` after call 2 -> exit 6, 2 creates, PARTIAL report | RED | 2.5 (b) |
| R27 | test_r27_interrupt | the fake raises KeyboardInterrupt on call 3 -> exit 130; 2 ledger lines; REPORT.md contains `PARTIAL` | RED | 2.12 |
| R28 | test_r28_not_runnable_stages | `vision` without `--set` and `web_search` without `--owner-line`: exit 0, factory 0 calls, results `not_runnable` names the reason; the vision REPORT lists the owner inputs (100 photos, about 30 Arabic, the manifest keys) | RED | 2.8, 2.10 |
| R29 | test_r29_report_table | `report` over fixture results: REPORT.md has one row per role (TEXT, VERDICT, SONNET_ESCALATION, CRITIC, MODERATION, VISION, WEB_SEARCH) with the GO_THRESHOLDS values, the knob NAMES and the three proposals computed as ceil-to-0.5(percentile x 1.25); contains `MEAS_ANTHROPIC_TEST_KEY` and no value | RED | 2.11 |
| R30 | test_r30_raw_without_headers | raw/<id>.json keys == {content, stop_reason, usage, model}; no `x-api-key`, `authorization`, `anthropic-version` substring | RED | 2.5 (f) |
| R31 | test_r31_no_model_literal | the script text has no match of the `test_model_config.py:136` regex | RED | 2.1 |
| R32 | test_r32_moderation_production_path | stage M with the fake returning `{"flagged": true, ...}` for case 1, malformed text for case 2, a refusal for case 3: recorded allowed False / reasons category / malformed / refusal; the request seen by the fake has system == `MODERATION_SYSTEM_PROMPT`, max_tokens == `MODERATION_MAX_TOKENS`, format schema == `MODERATION_SCHEMA`; `llm_router.guarded_anthropic_create` and `consume_escalation` are restored after the stage | RED | 2.8 |
| R33 | test_r33_verdict_eval_plan | dry-run plan: A6 = 60 x 2 = 120 calls; a fake verdict JSON with winner_index != gold counts one mismatch | RED | 2.6 |
| R34 | test_r34_count_tokens_and_capabilities | A5 calls `messages.count_tokens` 20 times with no `max_tokens` kwarg, usd 0; A0 calls `models.retrieve` for the distinct model_config ids | RED | 2.6 |
| R35 | test_r35_fixtures | the five fixtures exist and parse; counts 100 / 20 / 60 / 100 / 3; 30 names with Arabic script; no key named id-like person field (email, phone, user, device, cohort, profile); the moderation set has no case in the sexual, minors or self-harm categories | RED | 2.9 |
| R36 | test_r36_dotenv_guard_and_recheck | `_import_app_modules` seam that sets `ANTHROPIC_DECOY=1` -> exit 2 after the imports (the re-scan); `dotenv.load_dotenv` is the harness no-op during the imports | RED | 2.3 steps 6-8 |
| R37 | test_r37_env_safety_lists_the_name | `"MEAS_ANTHROPIC_TEST_KEY" in tests._env_safety.CREDENTIALS_UNSET` | RED | E1 |
| R38 | test_r38_stream_ttft | A2: create called with `stream=True`; ttft_ms recorded from the first content_block_delta; the body otherwise equals A1's | RED | 2.6 |
| P01 | test_p01_app_never_imports_the_harness | no file under app/ contains `meas_claude_gate` (AST import scan + text) | PIN | 2.13 (c) |
| P02 | test_p02_router_sites_contract | SITES keys == the 16 names; role / claude_max_tokens per site as in 1.1; `to_claude_request` output keys for a classify capture == {model, messages, max_tokens, thinking, output_config, system} | PIN | base |
| P03 | test_p03_builders_capture_offline | with the FULL configuration (every ENABLE_ANTHROPIC_* ON), `llm_router.route` monkeypatched to a recorder, `get_client` patched: the twelve builders each reach `route` with their site name and 0 non-loopback sockets (the netguard) | PIN | base (1.2) |
| P04 | test_p04_price_rows | the Anthropic rows, HAIKU_LONG_CONTEXT, WEB_SEARCH_USD_PER_REQUEST and ANTHROPIC_PRICE_TABLE_AS_OF equal the 1.4 values | PIN | base |
| P05 | test_p05_sdk_hazards | through `httpx2.MockTransport`: an explicit key + base_url sends `x-api-key` to `https://api.anthropic.com/v1/messages`; `max_retries=0` -> 1 request on 529; `ANTHROPIC_CUSTOM_HEADERS` (set via monkeypatch) IS sent (the hazard behind R03); `str(BadRequestError)` carries the body (the hazard behind R09) | PIN | base (1.3) |
| P06 | test_p06_gold_labels_recompute | every `verdict_gold.json` label equals the offline scoring winner recomputed now (skipped-as-RED at base: the fixture is absent, so this row is R-class at base and P after GREEN; listed here for the gate) | RED at base | 2.9 |

Counts: 38 R rows (R03 / R04 / R14 / R23 / R24 parametrized) + P06 (RED at base) = 39 RED rows; 5 PIN rows (P01-P05).

## 6. Mutation table (each on a byte copy of `scripts/meas_claude_gate.py` under the mutation lock; an exact-string edit that matches once; the killing rows via `pyt.py -k`, bound 600; restore; sha256 compare)
| # | mutant | killed by |
|---|---|---|
| M01 | `REFUSED_ENV_PREFIXES = ("ANTHROPIC_API",)` (CUSTOM_HEADERS / LOG slip through) | R03 |
| M02 | the env scan moved after `_build_client` | R03 (factory calls) |
| M03 | `"OPENAI_API_KEY"` dropped from `REFUSED_ENV_NAMES` | R04 |
| M04 | key check `if value is None` only (blank accepted) | R05 |
| M05 | `--out` repo check removed | R06 |
| M06 | `max_retries=0` -> `max_retries=_model_config.anthropic_max_retries()` | R07 |
| M07 | `trust_env=False` -> `True` | R07 |
| M08 | `follow_redirects=False` -> `True` | R07 |
| M09 | the ledger records `"message": str(exc)` | R09 |
| M10 | the crash line prints `repr(exc)` | R10 |
| M11 | key read `os.environ.get(ENV_VAR_NAME) or os.environ.get("ANTHROPIC" + "_API_KEY")` | R11 |
| M12 | the logger pin loop removed | R12 |
| M13 | dry-run builds the client | R13 |
| M14 | the capture result used without `to_claude_request` (kwargs sent as OpenAI-shaped) | R14 |
| M15 | `_escalation_request` replaced by a model swap only (thinking kept disabled) | R15 |
| M16 | `cache_read_tokens` not passed to pricing | R16 |
| M17 | an unpriced usage books 0.0 | R16 |
| M18 | the worst-case check removed | R17 |
| M19 | the worst case ignores `max_tokens` (output term 0) | R17 |
| M20 | `UNIT_CEILING_USD = 150.00` | R18 |
| M21 | `--max-usd` above the default accepted | R19 |
| M22 | `_fsync` call removed | R20 |
| M23 | resume ignores completed ids | R21 |
| M24 | resume skips transient lines too | R21 |
| M25 | `--max-calls` off by one (`>` for `>=`) | R22 |
| M26 | 401 classed transient (retried) | R23 |
| M27 | the consecutive counter not reset on success | R24 |
| M28 | `CONSECUTIVE_TRANSIENT_STOP = 4` | R24 |
| M29 | `RATE_LIMIT_RETRIES = 4` | R25 |
| M30 | `retry-after` ignored (always 5) | R25 |
| M31 | the 60 s clamp removed | R25 |
| M32 | the wall-clock check removed | R26 |
| M33 | `except KeyboardInterrupt` removed | R27 |
| M34 | vision runs without `--set` | R28 |
| M35 | web_search runs without `--owner-line` | R28 |
| M36 | the tail proposal uses x1.0 | R29 |
| M37 | the report prints `len(value)` beside the name | R29 / R08 |
| M38 | raw response stored with `resp.model_dump()` of the http response headers | R30 |
| M39 | moderation request built by a harness copy with `max_tokens=128` | R32 |
| M40 | `guarded_anthropic_create` not restored after stage M | R32 |
| M41 | `_install_dotenv_guard` call removed | R36 |
| M42 | the post-import env re-scan removed | R36 |
| M43 | stream=True dropped in A2 | R38 |
| M44 | `_scrub` not applied to stdout | R08 (redactions path) / R10 |
Expected: 44 / 44 KILLED; an equivalent survivor is reported for a ruling.

## 7. Comm set and gates for GREEN
### 7.1 The comm set (union rule; measured by `comm.py` over tests/ at 6b909e0a)
`_env_safety` importers (23, E1) UNION CLAUDE.md readers by grep (38; the import-graph six included) UNION scripts/ readers and walkers (83) UNION router / pricing / model_config / spend-breaker / shadow_experiments importers (31) UNION the named source-scanning pins (12 incl. `test_start_command*`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`) UNION tests/ walkers (31) MINUS the four `test_precommit_hook*.py` = 156 files (`comm_union.txt`, sha256 prefix 6e69d75cf0f4f6b6) + the RED file at HEAD = 157. No SmartCompareApp-scanning test is required (no client-visible change); the fourteen client fences read no scripts/ or CLAUDE.md literal this unit moves, but the common brief requires them for a backend unit touching scripts/ (the orchestrator's junction): run BY PATH at GREEN. Base record: LC-6 at 6b909e0a (the a74caba7 record is reusable per file for members whose bytes are unchanged and that read none of CLAUDE.md / extraction_service / image_routes / url_extraction_service; the CLAUDE.md readers and the _env_safety importers re-run at base).

### 7.2 Gates for GREEN (cheapest first; ONE pytest at a time across both lanes (the foreign-process probe first); every [pyt] line pasted)
1. `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on the script, the generator and the RED file; bytes > 127 = 0 in the script and the RED file; the fixtures UTF-8 JSON (`json.loads`), LF.
2. The secret sweep on the added lines (no `sk-` shape, no 8-digit run, no `@gmail`, no `+973`, no keyword-named high-entropy constant).
3. The RED file alone (bound 600): all R and P rows green; the netguard lines EMPTY for it.
4. `python -m scripts.meas_claude_gate text --dry-run --out <scratchpad>/s07_dry` (and moderation, vision with no set, web_search with no line, report) under a process-wide socket guard: exit 0 each; `plan.json` worst totals printed; NO variable set.
5. The mutation table (44).
6. The comm set in chunks of at most 25 (bound 1200), HEAD vs the base record: branch-only-new EMPTY.
7. The pre-commit hook on the staged files (the commit by the GREEN agent per its gate note).

### 7.3 Adversary checks (R-S07-11, the security-and-spend lens)
Every path from the variable to an output (stdout, stderr, files, exceptions, reprs, the SDK's own logs); the SDK hazards of 1.3 (CUSTOM_HEADERS, the body in `str(exc)`, the key in `exc.response.request.headers`, the env proxy and the Windows registry proxy, redirects); the worst-case arithmetic against `llm_pricing` (long context, web search, unpriced); resume double-spend; the 15.00 unit ceiling across stages; the dry-run socket proof; the moderation patch restore; the fidelity rows.

## 8. CLAUDE.md block, owner steps
### 8.1 The block (after the S81-04c block :637-:640, one blank line before `## Tests` :641; CRLF; names only)
"**SESSION 81 unit (S81-07 MEAS-CLAUDE-GATE, 2026-11-1x; NO flag: a scripts/ leaf nothing under app/ imports; FOCUS, two adversaries; spec .qa-s80/S81-07_UNIT_SPEC.md, rulings specs/RULINGS_S81_07.md, gate specs/GATE_S81_07.md):**
- `scripts/meas_claude_gate.py` measures the Claude go / no-go per role BEFORE each `ENABLE_ANTHROPIC_*` / `ENABLE_SONNET_ESCALATION` flip (the CLAUDE.md:508 precondition "S81-07 go per role"): stage `text` (the twelve text sites built by the app's own prompt builders and `llm_router.to_claude_request`, 20 synthetic compares, the TTFT twin, the Sonnet `between_tools` shape, the refusal rate on 100 public fragrance names incl. Arabic, `count_tokens` on 20 synthetic compares, the 60-case synthetic verdict eval at 2 reps with the WINNER_INDEX_MISMATCH rate), `moderation` (the 100-case parity set through `moderate_with_claude`), `vision` (owner-written photos only, else NOT RUNNABLE), `web_search` (only with the owner's dated line), `report`. Inputs synthetic or owner-written only; no database, Redis, Supabase, Railway or production row; the only host is api.anthropic.com.
- WHO RUNS IT: the ops lane only, under the owner's 15 USD cap, with the owner's TEST key in the variable `MEAS_ANTHROPIC_TEST_KEY` in that one run's environment (names only; never `ANTHROPIC_API_KEY`: any `ANTHROPIC_*` name, `UPSTASH_REDIS_URL` / `UPSTASH_REDIS_TOKEN` or `OPENAI_API_KEY` present refuses the start). No agent sets the variable or runs it against the network; agents run the tests and `--dry-run` (no socket, no key read).
- Spend: per-stage ceilings in code (text 4.00, moderation 2.00, vision 5.00, web_search 3.00 USD; `--max-usd` may only lower them), a 15.00 USD unit ceiling across every stage ledger in `--out`, a worst-case check before each call, a JSONL ledger fsynced per call (a re-run resumes), `--max-calls`, `--max-minutes`; SDK retries off; 401 / 403 stop at once; three consecutive 5xx / 529 / connection errors stop; a 429 is honoured by retry-after at most three times. Output under `--out` (outside the repo): spend.jsonl, raw/, results.json, REPORT.md. The GO bars and the three timeout proposals (`ANTHROPIC_CLASSIFY_LLM_TIMEOUT`, `ANTHROPIC_VISION_TIMEOUT_SECONDS`, `ANTHROPIC_TAIL_RESERVE_SECONDS`) are ruled in RULINGS_S81_07; a knob value changes only by the owner's dated line.
- Owner steps (names only): (1) create a TEST key in a dedicated Console workspace with a spend limit at or under 15 USD; (2) give the ops lane the run window; (3) read the REPORT.md go / no-go table; (4) for stage W only: the dated line enabling web search for that workspace; for stage V only: the photo set and manifest."

### 8.2 The relay message at READY (R-S07-12; the orchestrator sends it)
Per stage: the exact command `python -m scripts.meas_claude_gate <stage> --out <abs dir outside the repo>`; the variable NAME `MEAS_ANTHROPIC_TEST_KEY`; the expected spend (9 below); the stop conditions (2.14); where REPORT.md lands.

## 9. Stated limits
- L1 (Q4, expected spend at list prices; worst-case bounds use UTF-8 bytes as tokens, so the real spend is roughly a third of the bound): stage A bound about 1.50 USD (A1 20 compares x about 0.016 = 0.31; A2 0.08; A3 20 Sonnet verdicts x 0.040 = 0.80; A4 100 parses 0.07; A5 0; A6 120 verdicts 0.24); stage M about 0.28 (Haiku 0.013 + a worst-case Sonnet re-run of every case 0.26); stage V about 3.04 for 100 photos on both models; stage W about 0.64 (40 turns x 0.016 incl. one 0.01 search each, at the 60,000-token result bound). The ruled defaults (4 / 2 / 5 / 3, sum 14 <= 15) hold every stage with headroom; no default change proposed.
- L2 no site streams at this base (`guarded_anthropic_create` uses a non-streaming `create`, llm_router.py:968-:977): TTFT is measured by the A2 twin (`stream=True`, otherwise the same body), not by a production path.
- L3 "the real spacing of one compare": the harness replays the code's call ORDER and concurrency per compare, not the search legs between them (Serper and the scrapers are not called); `ROUND_SPACING_S` 30 s between compares is an assumption (OQ-3); the cache_read share is measured with no `cache_control` (the router sends none, llm_router.py:746-:752), so it measures automatic caching only.
- L4 the verdict eval's labels are the offline deterministic winners of SYNTHETIC pairs, not owner gold; the OpenAI temperature-0 baseline and the gpt-4o / gpt-4o-mini arms are not run (R-S07-9); the mismatch bar is absolute.
- L5 CRITIC has no builder (no live site since S81-22b): NOT RUNNABLE.
- L6 the moderation set is synthetic and omits the sexual, sexual/minors and self-harm categories (a public repo); parity is against labels, not against today's OpenAI moderation (no credential); the owner may add a private set through `--set` (never committed).
- L7 the harness imports `llm_spend_breaker` for its pure bound functions (not in R-S07-1's list; OQ-2) and sets an in-process placeholder in `OPENAI_API_KEY` for `openai_service`'s import-time client (never sent: every dispatch is captured).
- L8 a web-search turn's injected result tokens are bounded by a constant (60,000), not counted.
- L9 the pricing rows are the S81-03 data read 2026-10-22; the R-S03-4 re-verification of the Anthropic rows is a documentation read for the relay before the first flip, not something the harness can do.
- L10 the harness cannot see a key in the box's shell history or the ops session transcript: the ops brief must set the variable from the owner's paste in that one process only.

## 10. Out of scope
Any app/ change (the knob values themselves, cache_control, prompt caching, streaming, web search on the live path, the CRITIC site); a router fix found by the measurement (a follow-up unit); the gpt-4o / gpt-4o-mini arms; the owner's photo set; adding `ANTHROPIC_CUSTOM_HEADERS` to `CREDENTIALS_UNSET` (OQ-5); Batch API measurement; the price-warmer.

## 11. Open questions for the orchestrator
- OQ-1 E1 touches `tests/_env_safety.py`, a test-support file outside R-S07-1's three paths; the common brief's DOTENV GUARD rule asks for it. Accept E1 (and its 23 importers in the comm set), or drop it?
- OQ-2 The worst-case bound reuses `llm_spend_breaker.prompt_token_upper_bound` / `upper_bound_usd` (pure, no Redis) instead of a `count_tokens` call before every call (the brief's "counted input"); the bound is >= the count, so the check is stricter and costs no request. Accept, or require a count per call (a free but rate-limited request)?
- OQ-3 The compare spacing: 30 s between synthetic compares, the phases chained with no gap. Rule a value (or a measured production inter-phase gap from the stage timings, if the relay has one).
- OQ-4 The proposed GO bars of 2.11 (notably the absolute 0.10 winner-mismatch bar and the half-leg latency bars) go to the owner through the relay as pass bars: confirm or amend.
- OQ-5 `ANTHROPIC_CUSTOM_HEADERS` is read by the SDK even with an explicit key (measured) and is absent from `CREDENTIALS_UNSET`; it matters for production too (R-S06-17 lists only BASE_URL / AUTH_TOKEN as inert). Record a follow-up for the router (an explicit refusal or the CREDENTIALS_UNSET entry)?
- OQ-6 CRITIC: with no live site, does `ENABLE_ANTHROPIC_CRITIC` keep its place in window 13?
- OQ-7 The contract freeze (PLAN_S80 section 0 and runs/research/contract_freeze.json on the docs checkout) was NOT re-read in this run: opening sc-docs-70 costs a CLAUDE.md injection and this unit moves no response byte, envelope or key (2.13). Confirm that the freeze is vacuous here.
- OQ-8 The ops lane's Python: the harness needs `anthropic==1.12.1` (on `.venv-qaren` since #374); the ops command should name that interpreter.

Not done in this spec: the RED file, the fixtures, the script, the mutation runs, the comm-set base record at 6b909e0a, the client fences, the base re-run of the CLAUDE.md readers.
