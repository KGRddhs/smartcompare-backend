# B3 unit spec (measured): VISION-IDENTITY-V2 -- camera identification behind `ENABLE_VISION_IDENTITY_V2`

- Unit: B3 (backend, one PR, dark flag `ENABLE_VISION_IDENTITY_V2`, default OFF, read per call). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s80-b3`, branch `feature/s80-vision-identity-v2`, base `81df2b641454e0301cca51a3ba01bf8ef3d7e649` (`git rev-parse HEAD`, detached; `git status --short` empty at the start and after every probe below; the only file written in the worktree is this one, under the gitignored `.qa-s80/`, `.gitignore:72`).
- Evidence pointers: PLAN_S80.md section 0 (the build-3 contract), section 1 (R-A1..R-A15), section 3 unit B3; RULINGS_R0.md R0-4 (camera forwards `user_id` and `user_preferences`), R0-6 B3-PROMPT-PINS (V2 is a SECOND prompt string and a second normaliser; flag OFF byte-identical; no W4-11 fixture regeneration; the four clear-lists; M1), R0-7; DEFECT_LEDGER.md rows MYEZ-001, MYEZ-004 (vision half), MYEZ-015 (vision bound), OWNER-CAMERA, OWNER-OPENAI (vision half); research digests `runs/research/openai_flows_provider.json` findings 0/4/5/10/11/13 and `runs/research/eval_regression.json` findings 2/6/10/22 (the tester fixtures), `runs/research/contract_freeze.json` findings (3), (4), (5a); the tester scenarios V01 (OSMIA / AL IBDAA), V04 (Sefiki / Violin), V07 (GUESS / GUESS).
- Sister units and contracts: B1 RESULT-STATUS (reads nothing from B3; stamps `metadata.*` in `response_builder`), B2 RESULT-GATE (CONSUMER of this unit: the camera pre-compare refusal reads the per-product identity fields B3 carries on `vision_products` and on the orchestrator's identity dicts; the DECISION to refuse on low confidence, same identity or category conflict belongs to B2 and is out of scope here), B5 CATEGORY-TRUTH (the vision-category tie-break in `_resolve_pair_category` is B5's, not B3's), B7 IMAGE-PIPELINE-V2 (image selection, out of scope), B8 (any `lang` on `/image/identify` and the T23 re-record are B8's only), B10 (typed errors / provider seam). B3 declares NO new route parameter or body field (R0-6 T23-RERECORD).
- Personal-data rule: no real name, email, phone, Apple id, device id, address or account id appears in this file or in anything the unit writes. Test identities are the tester's PRODUCT strings from the audit (brand / product names, not people) and synthetic user ids built at run time. No credential-shaped literal anywhere (the `sk-` sentinel the existing camera test needs is built by concatenation).
- Measurement location: `<scratchpad>/B3/` (`probe_usage_fix.py` and its output in this file's section 1.4/1.7, `comm_set.py` + `comm_base.txt`, `base_camera_vision.log`, `base_model_config_enforced.log`, `base_paid_route_metering.log`, the digest extracts `digest_vision.txt`, `eval_fixtures.txt`, `openai_flows_vision.txt`, `notes.md`). Every pytest went through the bounded runner, one process at a time; three runs in all (the brief's cap), their `[pyt]` lines in 1.10.

## 0. What the unit does (one paragraph)

Behind `ENABLE_VISION_IDENTITY_V2` (default OFF, read per call inside `identify_products` and once per request in the camera route): the vision call sends a SECOND prompt (`VISION_PROMPT_V2`: the exact-label OCR rule kept, the guess-from-shape rule replaced by "no readable text means confidence low", an Arabic-script transliteration rule, the nine-key category enumeration shared with the text path, an `image_index` per candidate) with `response_format` = a strict `json_schema` for the object `{products:[{image_index, brand, name, category, product_type, size_or_count, visible_price, distinguishing_features, is_product, confidence}]}`, under `asyncio.wait_for(VISION_TIMEOUT_SECONDS, default 20.0)`; a SECOND normaliser accepts the object or a bare array, keeps ONE best candidate per `image_index` (is_product true, then highest confidence, then first), keeps the five public keys the route and the client already see (`brand, name, size_or_count, visible_price, confidence`) and carries the fields B2 needs as underscore-prefixed internal keys (`_image_index, _category, _product_type, _distinguishing_features, _is_product`) that the route strips from every wire body; a None / refused reply raises `LLMUnavailableError` (the route's existing branch ships the coded 503 `LLM_UNAVAILABLE`, never a 500), a `finish_reason == "length"` reply is a logged parse failure (the route's existing `action: "error"` exit), a timeout is a `TimeoutError` (the same existing 503 branch); the orchestrator's vision identity dicts (REST and stream twins) carry `_vision_confidence`, `_vision_category`, `_vision_distinguishing_features`, `_vision_is_product` when the vision products are V2-shaped; the camera route forwards `user_id` and, when `preferences_completed`, `user_preferences` as CONDITIONAL kwargs into `compare_from_text` under the flag. Alongside, a reviewed test-side fix: the three `tests/test_camera_vision.py::TestIdentifyProductsMocked` baseline nodes use a `types.SimpleNamespace` usage object, the three rows leave `tests/.pre_impl_failures.txt` with pass proof, the mirror is regenerated (11 -> 8). Flag OFF: the prompt text, message layout, kwargs, normaliser and route call are byte-identical to base, pinned.

## 1. Base state (measured at 81df2b64)

### 1.1 The vision service (`app/services/openai_service.py`, 479 lines)

| what | where | measured fact |
|---|---|---|
| imports | `:4-22` | `json, base64, logging, typing, httpx, AsyncOpenAI, provider_base_url, model_config (openai_max_retries, sampling_kwargs, standard_model, token_limit_kwargs, verdict_model, vision_model), api_budget_service as _llm_breaker, sanitize_prompt_input`. No `asyncio`, no `os`, no `math` import today. |
| module client | `:33-37` | `client = AsyncOpenAI(base_url=provider_base_url(), timeout=httpx.Timeout(120.0, connect=30.0), max_retries=openai_max_retries())` built at import; `identify_products` dispatches through THIS object (`:187`), not `get_client()` (`:45-61`, used by the three text helpers). Tests patch `app.services.openai_service.client` (test_camera_vision.py:62, test_image_identify_llm_unavailable_s69.py docstring). |
| cache telemetry | `:64-82` | `_log_cache_telemetry(response, label)`: `usage = getattr(response, "usage", None)`; `cached_tokens = getattr(usage, "prompt_tokens_cached", None)`; on a `MagicMock` usage that is a truthy MagicMock, `cached_tokens or 0` keeps it and `:81 if cached_tokens > 0` raises `TypeError` (the ledger's "openai_service.py:83" and CLAUDE.md:502's ":109" are both stale; it is `:81` at this sha). Called at `:195` BEFORE the JSON parse, so all three baseline nodes die there. |
| prompt text (flag OFF, frozen) | `:135-162` | the one `{"type": "text", "text": """..."""}` block; 2,119 characters, 2 non-ASCII characters (the em dashes at `:147` and `:162`); sha256 of the text as sent = `bb737687c40969abb4dea936f522d5be4a0693bcd5e2f7b09e28a78204462ae3` (probe, fake client recorder). Lines `:152` ("Identify products even WITHOUT packaging ... confidence=low") and `:156` ("Return ONLY a valid JSON array") are the two rules V2 changes; `:137`/`:147` are the OCR rules V2 keeps. |
| message layout | `:166-189` | ONE user message; `content[0]` the text block, then one `{"type": "image_url", "image_url": {"url": "data:<mime>;base64,<b64>", "detail": "auto"}}` per input image in order (`:177-183`); bytes input `mime_type` from the dict, default `image/jpeg`. |
| the call | `:186-194` | `_vision_model = vision_model()`; `await _llm_breaker.guarded_llm_create(client, model=_vision_model, messages=[...], **token_limit_kwargs(_vision_model, 500), **sampling_kwargs(_vision_model, 0))`. Measured kwargs at the fake client: keys exactly `{max_tokens, messages, model, store, temperature}`, `model == "gpt-4o-mini"`, `max_tokens == 500`, `temperature == 0`, `store is False` (added by the chokepoint), NO `response_format`, NO `wait_for`. |
| parse + normaliser (flag OFF, frozen) | `:198-222` | `raw_content = response.choices[0].message.content`; `clean_json_response(raw_content)` (`:96-108`, `.strip()` first: a None content raises `AttributeError` outside the try -> the route 500s, measured); `json.loads` -> on `JSONDecodeError` the dict `{"products": [], "error": "Failed to parse response: <e>", "raw_response": raw_content, "tokens_used": <usage.total_tokens or 0>, "cost": 0}` (`:205-211`); a non-list (e.g. `{"products": [...]}`) is silently dropped to `[]` (`:215`); each dict -> exactly five keys `brand` ("Unknown" default), `name` ("Unknown Product"), `size_or_count`, `visible_price`, `confidence` ("medium" default) (`:216-222`); a non-dict element raises `AttributeError` at `:217`. |
| cost | `:224-235` | mini list price over `usage.prompt_tokens` / `completion_tokens` regardless of the model id (digest finding 11); `usage is None` raises at `:227`. Return `{"products", "tokens_used", "cost"}`. |
| the digest fixture | `tests/w4_11_prompt_digest_recorder.py`, `tests/test_prompt_fence.py` | `grep -n -i identify_products|vision` over both: EMPTY. The vision prompt has no digest pin and no literal pin (R0-6 confirmed); the fixture is NOT regenerated by this unit. |

### 1.2 The camera route (`app/api/image_routes.py`, 634 lines)

| what | where | measured fact |
|---|---|---|
| imports | `:19` `identify_products`; `:27-30` `LLM_UNAVAILABLE_FRIENDLY_MESSAGE, StructuredComparisonService`; `:31-34` `LLMUnavailableError, _openai_failure_is_transient` from `api_budget_service`; `:35` `get_optional_user`; `:51-59` the text_routes helpers. | No import of `auth_service.get_user_preferences` (text_routes.py:23 has it). |
| route | `:160-168` | `@router.post("/identify", dependencies=[Depends(require_paid_route_user)])`, `@limiter.limit("10/minute")`, params `images: List[UploadFile]`, `region: str = Query("bahrain")`, `nocache: bool = Query(False)`, `user = Depends(get_optional_user)`. NO `selected_category`, NO `lang` (T23 fixture freezes this). |
| anon gate, validation | `:180-208`, `:211-237` | unchanged by this unit. |
| refund latches | `:249-286` | `_refund_reserved_credit(label)` (once per request, only when `usage_consumed`), `_refund_anon_credit(label)`. |
| metering gate | `:288-302` | `consume_comparison_credit` under `paid_route_metering_enabled()`. |
| vision call | `:304-310` | `vision_ledger = start_openai_ledger()`; `vision_result = await identify_products(image_data_list)` -- NO `wait_for` (digest finding 13). |
| vision exception exit (exit 1) | `:311-329` | `logger.error(f"[IMAGE] Vision call failed: {e}")` (inside the except arm), both refunds, then `if isinstance(e, LLMUnavailableError) or _openai_failure_is_transient(e): raise HTTPException(503, {"code": "LLM_UNAVAILABLE", "error": LLM_UNAVAILABLE_FRIENDLY_MESSAGE})` else `HTTPException(500, "Image analysis failed. Please try again.")`. `_openai_failure_is_transient` (`api_budget_service.py:907-931`) returns True for `TimeoutError` (`:913`; `asyncio.TimeoutError is TimeoutError` on 3.12), `RateLimitError`, `APIConnectionError`, `InternalServerError`, any `APIStatusError >= 500`; False for `AttributeError`, `IndexError`, `BadRequestError`. So at base a None content -> `AttributeError` -> 500; a wait_for expiry or an `LLMUnavailableError` raised inside `identify_products` -> 503 `LLM_UNAVAILABLE` with NO route change. |
| parse-error exit (exit 2) | `:331-345` | `if vision_result.get("error")`: `logger.error("[IMAGE] Vision parse error")` (constant), raw at DEBUG, both refunds, body `{"success": False, "action": "error", "error": "Could not identify products in the image. Please try a clearer photo.", "vision_cost": ...}`. |
| moderation | `:353-396` | `moderate_vision_output(vision_result)` reads `products[].brand/name/size_or_count` only (`content_safety_service.py:265-277`); blocked -> `need_second_product` + `CONTENT_UNAVAILABLE`. Unaffected by underscore keys. |
| products, size enrichment | `:398-409` | `products = vision_result.get("products", [])`; `size_or_count` appended to `name` when not already in it (`:403-406`); `product_names` from brand/name. |
| 0 / 1 products (exits 4, 5) | `:411-421`, `:423-437` | `action: "error"` / `action: "need_second_product"` with `"products": products` (`:433`) and `message: f"Identified: {brand} {name}. ..."`. |
| 2+ products | `:439-450` | `p1, p2 = products[0], products[1]`; `query = f"{p1['brand']} {p1['name']} vs {p2['brand']} {p2['name']}"`; `:450 result = await service.compare_from_text(query, region=region, vision_products=products, nocache=nocache)` -- NO `user_id`, NO `user_preferences`, NO `selected_category` (R0-4). |
| metadata injection | `:476-496` | `result["metadata"]["identified_products"] = products` (`:488`; `:493` on the no-metadata branch): the SAME list objects that went into `compare_from_text`; no key filtering. |
| unsuccessful / envelope / except | `:503-534`, `:575-579`, `:582-634` | `_camera_failure_envelope(result, request, products, vision_cost)` (`:109-129`) and the `comparison_failed` body (`:625-634`) both ship `"products": products` verbatim. |
| the top-level `result` key | contract_freeze (5a): `ResultsScreen.tsx:321-331 setResult(data.result ?? data)` | ADDING a top-level `result` key to the camera 200 body would make build 3 render that key. This unit adds no top-level key in either flag state. |

### 1.3 The orchestrator (`app/services/structured_comparison_service.py`, 9,701 lines)

| what | where | measured fact |
|---|---|---|
| entry | `:3959-3973` | `compare_from_text(self, query, region="bahrain", include_specs=True, include_reviews=True, include_pros_cons=True, nocache=False, selected_category=None, vision_products=None, user_preferences=None, user_id=None, explicit_pair=None, output_lang=None)`; `:4008-4024` forwards every kwarg to `_compare_from_text_impl` under `wait_for(STREAM_HARD_CAP_SECONDS)`, `output_lang` as a conditional kwarg (the W4-14a 28b pattern, `:4021`). |
| vision identity dicts, REST twin | `:4210-4225` | `if vision_products and len(vision_products) >= 2: for vp in vision_products[:2]: brand = vp.get("brand", "Unknown"); vname = vp.get("name", "Unknown Product"); full = f"{brand} {vname}".strip(); category = classify_category_from_text(full); products.append({"brand": brand, "name": vname, "variant": vp.get("size_or_count"), "category": category, "search_query": full, "_vision": True}); parsed = {}`. Exactly SIX keys; `confidence` dropped (digest finding 6). |
| stream twin | `:4848-4863` | byte-for-byte the same block (A3/A4 "lockstep" comment). |
| where the identity dicts go | `:4277` `_resolve_pair_category(products, selected_category, parser_path=_parser_path)` (reads `search_query`/`name`/`category`, `:454-456`); `:4295-4296` the category write-back; `:4316-4317` `_fetch_product_data(products[i], ...)`. | `_fetch_product_data` builds a FRESH result dict `{"brand", "name": display_name, "full_name", "variant", "category", "query"}` (`:5687-5700`) and reads `_vision` only to choose the display identity (`:5689-5694`, `_product_display_identity` `:1327-1343`: vision -> `dedup_brand_name(brand, name) or search_query`). The identity dicts themselves never reach `product_data`, `build_comparison_response` or the wire: `grep -l '"_vision"' tests/fixtures/lane1/*.json tests/fixtures/*.json` is EMPTY and `response_builder.py` never reads `_vision` (grep empty). So an underscore key added to these dicts is invisible on the wire by construction (the wire ships `product_data`, `response_builder.py:2213 result["products"] = product_data`, whose dicts are built at `:5697`). |
| knob idiom | `:1777-1787` `_float_knob(name, default)`: unset/blank -> default; `float()` ValueError/TypeError -> default; non-finite or `<= 0` -> default. `text_routes.py:104-140` is the same rule with a WARNING per rejected value. | The new knob copies the text_routes form (WARNING on garbage / non-positive / non-finite, names only). |
| the friendly copies | `:1696` `TIMEOUT_FRIENDLY_MESSAGE`, `:1701` `LLM_UNAVAILABLE_FRIENDLY_MESSAGE` (imported by image_routes `:28`). | |
| category enumeration (text path) | `extraction_service.py:113` `"category": "electronics|grocery|supplements|makeup|skincare|haircare|fragrances|fashion|other"` (the parser prompt), `:1357-1358` `"electronics, grocery, supplements, makeup, skincare, haircare, fragrances, fashion, other"` (the A2b classifier prompt), `:1160 _CANONICAL_CATEGORIES = frozenset(CATEGORY_SPEC_SCHEMAS.keys())`, `:1217-1250 canonicalize_category(raw)` (non-str / empty / unknown -> "other"). | V2 re-uses the same nine keys in the same order as `:1357`. |

### 1.4 The text route's rules B3 copies (`app/api/text_routes.py`)

- Preferences rule `:599-604`: `user_prefs = None; if user: prefs_result = await get_user_preferences(user["id"]); if prefs_result.get("success") and prefs_result.get("preferences_completed"): user_prefs = prefs_result.get("preferences")`. `get_user_preferences` (`auth_service.py:917-931`) returns `{"success": True, "preferences", "preferences_completed"}` on a row, and runs through `run_db` (one blocking Supabase round trip, inline while `ENABLE_SYNC_DB_OFFLOAD` is OFF; CLAUDE.md measured 285 ms p50 for an insert of the same client class).
- The service call `:636-647`: `user_preferences=user_prefs, user_id=user.get("id") if user else None` as plain kwargs on the text route; the camera route under the flag uses CONDITIONAL kwargs instead (no kwarg when absent), so the flag-OFF call stays the base three-kwarg call (2.6).
- The 503 mapping `:521-551` (`_surface_comparison_failure`): `TIMEOUT` / `LLM_UNAVAILABLE` -> 503 with a coded detail (never a bare 503: `error_handler.py:34` stamps a code-less 503 FEATURE_DISABLED, PLAN section 0.3).

### 1.5 The LLM chokepoint and the cost recorder

- `api_budget_service.guarded_llm_create(client, **kwargs)` (`:954-1035`): forces `kwargs["store"] = False` (`:980-983`); breaker OFF (`llm_preflight_breaker_enabled()` False at base, probe) -> `await client.chat.completions.create(**kwargs)` then `record_openai_response(kwargs.get("model"), response)` (`:984-987`); breaker ON: a `CancelledError` records nothing and re-raises (`:995-1011`, W1-3a) -- so an outer `asyncio.wait_for` that cancels the call never trips the breaker; a transient exception records a failure (`:1012-1014`). Every kwarg is passed through untouched, so a `response_format` reaches the SDK.
- `openai_pricing.record_openai_response` (`:121-154`): `getattr(usage, "prompt_tokens", None)` etc. through `_tok`; never raises. With a `types.SimpleNamespace(total_tokens=, prompt_tokens=, completion_tokens=)` usage it records a priced call (probe: the three fixed nodes return products / cost 2.4e-05).
- `LLMUnavailableError(RuntimeError)` (`:702-709`): its message must avoid "429" / "rate" / "quota" (the verdict fallback matcher).

### 1.6 Libraries on the pinned venv (measured in-process, `-I`)

- `openai == 3.3.1`, `pydantic == 2.13.4`. `ChatCompletionMessage.content: Optional[str]`, `.refusal: Optional[str]`; `Choice.finish_reason: Literal['stop', 'length', 'tool_calls', 'content_filter', 'function_call']`. A completion with `content: null, refusal: "..."` validates (`content None, refusal "I cannot help", finish stop`); `finish_reason: "length"` with a truncated string validates.
- `openai.types.shared_params.ResponseFormatJSONSchema = {"type": "json_schema", "json_schema": JSONSchema}` with `JSONSchema = {"name": str (required), "description": str, "schema": Dict[str, object], "strict": Optional[bool]}`; `completion_create_params.CompletionCreateParamsBase.response_format: ResponseFormat` (the union that includes it). The SDK accepts a plain dict of that shape (digest finding 4: `completion_create_params.py:474`).
- Python 3.12 (`runtime.txt`): `asyncio.TimeoutError is TimeoutError`, so `_openai_failure_is_transient(asyncio.TimeoutError())` is True (`:913`).
- No new dependency; `requirements*.txt` untouched.

### 1.7 Base behaviour measured with a fake client (`probe_usage_fix.py`, real `identify_products`, real `guarded_llm_create`, credentials popped, `OPENAI_API_KEY` set to a concatenated dummy in the probe process only)

| input | base result |
|---|---|
| MagicMock usage (the three baseline nodes' fixture) | `TypeError: '>' not supported between instances of 'MagicMock' and 'int'` from `:81`, all three contents |
| `types.SimpleNamespace(total_tokens=100, prompt_tokens=80, completion_tokens=20)` usage | `'[{"name": "Something"}]'` -> `{"products": [{"brand": "Unknown", "name": "Something", "size_or_count": None, "visible_price": None, "confidence": "medium"}], "tokens_used": 100, "cost": 2.4e-05}`; `'I can see an iPhone in the image'` -> the parse-failure dict (`error` "Failed to parse response: Expecting value: ...", `tokens_used` 100, `cost` 0); the Apple array -> one product, `cost` 2.4e-05 > 0. So the SimpleNamespace fixture makes all three nodes pass with NO production change. |
| `content = None` | `AttributeError: 'NoneType' object has no attribute 'strip'` (propagates; the route 500s) |
| `'[]'`, two images | `{"products": [], "tokens_used": 100, "cost": 2.4e-05}`; the recorded kwargs keys `['max_tokens', 'messages', 'model', 'store', 'temperature']`, one user message, content types `['text', 'image_url', 'image_url']`, data URL prefix `data:image/jpeg;base64,`, detail `auto`; prompt sha256 `bb737687c40969abb4dea936f522d5be4a0693bcd5e2f7b09e28a78204462ae3`, 2,119 chars, 2 non-ASCII |

### 1.8 Guards the new code must not trip

- `tests/test_model_config_enforced.py::test_no_call_site_passes_raw_sampling_kwargs` (`:134-143`, M1): AST over `app/**/*.py`, callee ending `completions.create` or `guarded_llm_create` minus the wrapper's two pass-throughs (`:112-114`): `>= 15` sites (base 15) and NO literal `temperature=` / `max_tokens=` keyword. The V2 call keeps `**token_limit_kwargs(...)` / `**sampling_kwargs(...)`; a literal `response_format=` is allowed (R0-6). `::test_image_tier3_dispatches_through_the_breaker_chokepoint` (`:146-169`): no direct `completions.create` outside the wrapper -- the V2 call goes through `guarded_llm_create`. Autouse `_clean_env` `:98-107` deletes `OPENAI_MODEL_*` and five flags (`:103-105`); the new flag joins that tuple.
- `tests/test_model_config.py` (the stray-model-literal pin, source-scanning): no model id literal in new code (`vision_model()` only).
- `tests/test_sentry_channels_u8d_unit.py` R8 (`:773-918`): an ERROR / exception / critical log OUTSIDE an except arm may take only constants / type names. Every new log line is INFO or WARNING, arguments constants, ints, bools or the `finish_reason` literal; no `exc_info`; never a product string.
- `tests/test_logger_no_query_leak.py`, `tests/test_openai_key_log_hygiene_s69.py`: no query text, no key tail in any new line.
- `tests/test_prompt_fence.py`: the vision prompt interpolates NO untrusted text (images only), so no `<SEARCH_RESULTS>` region or guard sentence applies; `_W411_FLAGS` (`:46-52`) is deleted per node at `:119` -- the new flag joins it. `tests/w4_11_prompt_digest_recorder.py` FLAGS (`:41-45`, popped at `:93`) joins the same way; the fixture bytes do not move (no vision render is digested).
- `tests/test_s71_u13_compare_auth_required.py` CLEAN_ENV (`:76-83`, every env name a route reads per call): the new flag joins it; the T23 OpenAPI fixture `tests/fixtures/s71_u13_flag_off_baseline.json` is untouched because no route parameter changes.
- `tests/test_ci_gates.py::test_baseline_count_is_rederivable_from_the_committed_file` (`:823-850`) re-derives the id set and the `<!-- BASELINE_COUNT: N -->` marker of `tests/PRE_IMPL_FAILURE_BASELINE.md` from `tests/.pre_impl_failures.txt`; `::test_backend_tests_derives_deselect_from_the_committed_baseline` (`:875-`) and `::test_baseline_node_ids_are_shell_safe_for_deselect` (`:900-`) read the file. `scripts/gen_baseline_mirror.py` renders the mirror (`python -m scripts.gen_baseline_mirror`, `--check`).
- The pre-commit hook: no `sk-` + 20 chars literal, no JWT shape, no PEM header in any new file (the camera test's dummy key at `tests/test_camera_vision.py:13` is a pre-existing literal `"sk-REDACTED"`; it is NOT touched by this unit -- the hook checks ADDED lines only -- and the new test file builds its own by concatenation).
- `tests/_env_safety.CREDENTIALS_UNSET`: no new credential-bearing name (a flag and a float knob only) -- nothing to add.

### 1.9 Line endings

Every existing file this unit edits is `i/lf w/crlf` (`git ls-files --eol`): `app/services/openai_service.py`, `app/api/image_routes.py`, `app/services/structured_comparison_service.py`, `tests/test_camera_vision.py`, `tests/.pre_impl_failures.txt`, `tests/test_model_config_enforced.py`, `tests/w4_11_prompt_digest_recorder.py`, `tests/test_prompt_fence.py`, `tests/test_s71_u13_compare_auth_required.py`, `CLAUDE.md` (and `tests/PRE_IMPL_FAILURE_BASELINE.md`, regenerated by the script). Use the Edit tool on existing files; the new test file is written with CRLF like its neighbours; `git diff --stat` must show content lines only.

### 1.10 Base pass state (bounded runner, one process at a time, flag unset; the three runs the brief allows)

```
tests/test_camera_vision.py
  3 failed, 22 passed, 1 deselected (TestVisionLive, live_unit), 11 warnings in 4.20s
  FAILED tests/test_camera_vision.py::TestIdentifyProductsMocked::test_malformed_response_returns_error
  FAILED tests/test_camera_vision.py::TestIdentifyProductsMocked::test_successful_identification
  FAILED tests/test_camera_vision.py::TestIdentifyProductsMocked::test_empty_product_fields_normalized
    (rows 81-83 of tests/.pre_impl_failures.txt; TypeError at openai_service.py:81, section 1.7)
  [hermeticity] sentinel checked 25 test(s)   [netguard] blocked 0 attempt(s) from 0 node(s)
  [pyt] tag=b3-base-camera-vision start=2026-10-19 23:27:33 end=2026-10-19 23:27:39 elapsed=5s bound=600s status=FAIL rc=1

tests/test_model_config_enforced.py
  27 passed, 1 warning in 9.96s
  [hermeticity] sentinel checked 27 test(s)   [netguard] blocked 0 attempt(s) from 0 node(s)
  [pyt] tag=b3-base-model-config-enforced start=2026-10-19 23:27:39 end=2026-10-19 23:27:51 elapsed=12s bound=600s status=OK rc=0

tests/test_paid_route_metering.py   (the image_routes metering file, W2-1)
  21 passed, 13 warnings in 6.82s
  [hermeticity] sentinel checked 21 test(s)
  [netguard] blocked 2 attempt(s) from 2 node(s)   (test_camera_success_consumes_once_and_never_refunds,
    test_url_compare_saves_history_with_input_type_url: [sentinel] socket.create_connection
    neutralized.supabase.invalid:443 -- the existing ratchet baseline, no egress)
  [pyt] tag=b3-base-paid-route-metering start=2026-10-19 23:30:53 end=2026-10-19 23:31:04 elapsed=11s bound=600s status=OK rc=0
```

NOT MEASURED at spec time (the three-run cap): the rest of the comm set (section 7). The last two specs at this code line (S78-F8 at e0f3e475, B3-B at b965c63b) recorded the same base failure classes the comm set will show: the `.pre_impl_failures.txt` rows that fall into the set and the two `tests/test_prompt_truth.py` tiktoken ERRORs on this box (cold cache, environmental, identical both sides). GREEN measures base -> head -> base.

## 2. Contract

### 2.1 Flag, knob, constants (all in `app/services/openai_service.py`)

- `vision_identity_v2_enabled() -> bool`: `os.getenv("ENABLE_VISION_IDENTITY_V2", "false").strip().lower() in ("true", "1", "yes", "on")`, read per call, never cached. Read at exactly two places: the FIRST statement of the V2 branch in `identify_products` (before any V2 state is touched) and once per request in the camera route at the compare site (2.6). No other module reads it (the orchestrator is presence-gated, 2.5).
- `vision_timeout_seconds() -> float`: `VISION_TIMEOUT_SECONDS`, default `_VISION_TIMEOUT_DEFAULT = 20.0`; `raw = os.getenv(...,"").strip()`; blank -> default; `float()` ValueError -> default with `logger.warning("VISION_TIMEOUT_SECONDS=%r is not a number; using the %.1fs default", raw, default)`; `<= 0` or not `math.isfinite` -> default with `"... is not a positive finite number; ..."` (the text_routes.py:104-140 form). Read per call, only inside the V2 branch (flag OFF never reads it).
- `VISION_CATEGORY_KEYS = ("electronics", "grocery", "supplements", "makeup", "skincare", "haircare", "fragrances", "fashion", "other")` -- the nine canonical keys in the `extraction_service.py:1357` order (pinned equal to `extraction_service._CANONICAL_CATEGORIES` as a set and to that string's order).
- `_VISION_V2_MAX_TOKENS = 1000` (V1 keeps 500; the V2 object carries ten fields per product incl. a list, up to 4 products; Q4).
- `VISION_PROMPT_V2` (pure ASCII module constant; GREEN writes it verbatim from 2.2).
- `VISION_RESPONSE_FORMAT_V2` (2.3), `VISION_V2_PUBLIC_KEYS = ("brand", "name", "size_or_count", "visible_price", "confidence")`, `VISION_V2_INTERNAL_KEYS = ("_image_index", "_category", "_product_type", "_distinguishing_features", "_is_product")`.
- `public_vision_products(products) -> list`: `[{k: v for k, v in p.items() if not str(k).startswith("_")} if isinstance(p, dict) else p for p in (products or [])]` -- a NEW list of NEW dicts; unconditional (no flag read): a V1 product has no underscore key, so OFF the copy equals the original byte for byte (Q6).

### 2.2 `VISION_PROMPT_V2` (the second prompt string; `:135-162` stays byte-identical)

The text, line by line (GREEN copies it as one triple-quoted ASCII string; the RED rows pin substrings, not a V2 sha):

```
You are a product identification expert with OCR skills. The images are numbered from 0 in the order they are given (image_index 0 is the first image). Identify every distinct retail product visible in each image.

CRITICAL: READ the EXACT text printed on each product's packaging, label or screen. Do NOT guess from memory or training data. Only report what you can actually SEE in the image.

For EACH product found, give:
- image_index: the 0-based number of the image the product appears in.
- brand: the manufacturer or brand name as printed on the label, logo or packaging; null when no brand text is readable.
- name: the FULL product name exactly as printed, including model numbers, variants and edition text ("Vitamin D-3 5000 IU", "iPhone 16 Pro Max 256GB"); null when no name text is readable.
- category: one of electronics, grocery, supplements, makeup, skincare, haircare, fragrances, fashion, other -- or null when you cannot tell. This is the same category list the rest of the service uses.
- product_type: a short noun for what the object is ("perfume bottle", "wrist watch", "shirt", "vitamin bottle", "violin").
- size_or_count: the quantity, count, weight, volume or storage size printed on the package ("360 Softgels", "1000mg", "128GB", "500ml"); null if not visible.
- visible_price: any price shown in the image (shelf tag, screen, label) with its currency symbol; null if not visible.
- distinguishing_features: short phrases that tell this item from a similar one (colour, pattern, material, edition text, cap shape, bottle shape, printed slogan). Empty list if none.
- is_product: true when the object is a retail product someone could buy; false for a person, an animal, furniture, a background object or a part of the room.
- confidence: "high" (brand and name text clearly readable), "medium" (partially readable, some inference), "low" (little or no readable text).

RULES:
- READ the label text character by character -- exact numbers and units matter.
- One image may contain MULTIPLE products: list each of them with the same image_index (up to 4 products in total across all images).
- If a product has NO readable brand or name text, do NOT invent one from its shape, colour or design. Report what you can see, set the unreadable fields to null and set confidence to "low".
- If the label is written in Arabic script, keep any Latin brand text as printed and transliterate the Arabic product name into Latin letters.
- For supplements and vitamins read the EXACT count from the front label; for electronics the EXACT model and storage; for food and grocery the weight, volume or count.
- For screenshots of retailer pages, extract the product name exactly as shown.
- If a price tag sits next to a product, associate it with that product.
- Return ONLY the JSON object described below, nothing else.

Return a JSON object: {"products": [ { "image_index": 0, "brand": "NOW", "name": "Vitamin D-3 5000 IU", "category": "supplements", "product_type": "vitamin bottle", "size_or_count": "360 Softgels", "visible_price": "BHD 8.50", "distinguishing_features": ["orange cap", "white bottle"], "is_product": true, "confidence": "high" } ]}
```

What changed against `:135-162`: the "Identify products even WITHOUT packaging ... (confidence=low)" rule (`:152`) is REPLACED by the no-invention rule (brand/name null, confidence low); the "Return ONLY a valid JSON array" rule (`:156`) and the array example (`:158-162`) are replaced by the object; `image_index`, `category`, `product_type`, `distinguishing_features`, `is_product` are new; the Arabic-script rule is new; every OCR rule is kept in substance. The message LAYOUT is the same as V1 (one user message, the text block first, one `image_url` part per image, `detail: "auto"`).

### 2.3 `VISION_RESPONSE_FORMAT_V2`

```
{"type": "json_schema",
 "json_schema": {"name": "vision_products_v2", "strict": True,
   "schema": {"type": "object", "additionalProperties": False, "required": ["products"],
     "properties": {"products": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["image_index", "brand", "name", "category", "product_type", "size_or_count",
                     "visible_price", "distinguishing_features", "is_product", "confidence"],
        "properties": {
          "image_index": {"type": "integer"},
          "brand": {"type": ["string", "null"]},
          "name": {"type": ["string", "null"]},
          "category": {"type": ["string", "null"], "enum": [*VISION_CATEGORY_KEYS, None]},
          "product_type": {"type": ["string", "null"]},
          "size_or_count": {"type": ["string", "null"]},
          "visible_price": {"type": ["string", "null"]},
          "distinguishing_features": {"type": "array", "items": {"type": "string"}},
          "is_product": {"type": "boolean"},
          "confidence": {"type": "string", "enum": ["high", "medium", "low"]}}}}}}}
```

Built once at import from `VISION_CATEGORY_KEYS`; passed as `response_format=VISION_RESPONSE_FORMAT_V2` (a literal keyword, allowed by M1).

### 2.4 `identify_products(image_data_list)` under the flag (the V2 branch; the V1 branch `:131-235` is byte-identical)

1. `if vision_identity_v2_enabled():` is the FIRST statement after the docstring; OFF falls into the unchanged V1 body (no knob read, no V2 constant touched).
2. `content = [{"type": "text", "text": VISION_PROMPT_V2}]` + the same image parts as V1 (the image encoding loop is shared code or duplicated verbatim; either way V1's bytes do not move).
3. `_vision_model = vision_model()`; `response = await asyncio.wait_for(_llm_breaker.guarded_llm_create(client, model=_vision_model, messages=[{"role": "user", "content": content}], response_format=VISION_RESPONSE_FORMAT_V2, **token_limit_kwargs(_vision_model, _VISION_V2_MAX_TOKENS), **sampling_kwargs(_vision_model, 0)), timeout=vision_timeout_seconds())`. The `TimeoutError` propagates unchanged (the route's existing 503 branch, 1.2); one `logger.warning("[VISION_V2] vision call timed out after %.1fs", bound)` is logged inside the `except asyncio.TimeoutError: ... raise` arm.
4. `_log_cache_telemetry(response, "identify_products")` (unchanged helper).
5. Reply triage, in this order: `choices = getattr(response, "choices", None) or []`; no choice -> treated as None content. `choice = choices[0]`; `finish_reason = getattr(choice, "finish_reason", None)`; `message = getattr(choice, "message", None)`; `content = getattr(message, "content", None)`; `refusal = getattr(message, "refusal", None)`.
   - `refusal` truthy OR `content` not a `str`: `logger.warning("[VISION_V2] no content: finish_reason=%s refused=%s", finish_reason, bool(refusal))` then `raise _llm_breaker.LLMUnavailableError("vision returned no content")` (the message carries none of "429", "rate", "quota"; the route maps it to the coded 503 `LLM_UNAVAILABLE`, 1.2).
   - `finish_reason == "length"`: `logger.warning("[VISION_V2] finish_reason=length; treating the reply as a parse failure")` and return the V1-shaped parse-failure dict `{"products": [], "error": "Failed to parse response: finish_reason=length", "raw_response": content, "tokens_used": <usage.total_tokens if usage else 0>, "cost": 0}` (the route's exit 2).
   - else `clean_json_response(content)` -> `json.loads`; `JSONDecodeError` -> the V1 parse-failure dict (same keys, `error` "Failed to parse response: <e>").
6. Shape: a `dict` with a list under `"products"` -> that list; a bare `list` -> itself; anything else -> the parse-failure dict with `error` "Failed to parse response: unexpected shape <type name>". Non-dict items are dropped and counted.
7. `_normalize_vision_products_v2(items, n_images)` per dict item: `image_index` = the int when `isinstance(x, int) and not isinstance(x, bool) and 0 <= x < n_images`, else the item is DROPPED and counted (`out_of_range`); `brand` = the stripped str or `"Unknown"`; `name` = the stripped str or `"Unknown Product"` (the V1 defaults, so the route's f-strings and the moderation join are unchanged in shape); `size_or_count`, `visible_price`, `product_type` = the stripped str or `None`; `confidence` = `.strip().lower()` when in `("high", "medium", "low")` else `"low"` (V2's honest default; V1 keeps "medium"); `category` = `canonicalize_category(raw)` when `raw` is a non-empty str (lazy import of `extraction_service.canonicalize_category`, the `:276` pattern) else `None`; `distinguishing_features` = the list's non-empty `str` items, each stripped and cut at 80 chars, at most 8, else `[]`; `is_product` = the value when it is a `bool`, else `True` (a V1-shaped array that lacks the key is treated as products, so a lenient reply does not vanish).
8. Selection: group by `image_index`, iterate indices ascending; within a group keep only `is_product` True candidates (the others are counted `not_product`); choose the highest confidence (high 3 > medium 2 > low 1), ties -> the earlier candidate; an index with no `is_product` candidate yields nothing. Result order = ascending `image_index`.
9. Each kept product is the dict `{"brand", "name", "size_or_count", "visible_price", "confidence", "_image_index", "_category", "_product_type", "_distinguishing_features", "_is_product"}` (the five public keys first, then the five internal keys; `_is_product` is always True after step 8 and is the V2 marker the orchestrator keys on, 2.5).
10. One `logger.info("[VISION_V2] candidates=%d kept=%d dropped_not_product=%d dropped_out_of_range=%d dropped_non_dict=%d images=%d finish_reason=%s", ...)` per call -- ints and the finish_reason literal only, never a product string.
11. Cost: the V1 formula over `usage.prompt_tokens` / `completion_tokens`, tolerant of `usage is None` (`tokens_used` 0, `cost` 0.0); return `{"products": kept, "tokens_used", "cost"}` (the same three keys as V1).

### 2.5 The orchestrator twins (`structured_comparison_service.py:4220-4224` and `:4858-4862`)

Module helper, next to `_product_display_identity` (`:1327`):

```
def _vision_identity_fields(vp) -> dict:
    """B3: the B2 fields a V2-shaped vision product carries into the identity dict.
    Presence-gated on the V2 marker `_is_product`: a V1 product (five public keys)
    returns {} and the dict stays the base six keys byte for byte."""
    if not isinstance(vp, dict) or "_is_product" not in vp:
        return {}
    feats = vp.get("_distinguishing_features")
    return {
        "_vision_confidence": vp.get("confidence"),
        "_vision_category": vp.get("_category"),
        "_vision_distinguishing_features": list(feats) if isinstance(feats, (list, tuple)) else [],
        "_vision_is_product": bool(vp.get("_is_product")),
    }
```

Both twins become `products.append({"brand": brand, "name": vname, "variant": vp.get("size_or_count"), "category": category, "search_query": full, "_vision": True, **_vision_identity_fields(vp)})` -- one splat per twin, nothing else in either block moves. No flag read here (Q5): the identity dicts follow the shape the vision call produced, so a mid-request flip cannot split one request, and flag OFF is byte-identical because V1 never emits `_is_product`. These dicts never reach `product_data` or the wire (1.3). B2 reads them from `product_info` inside `_fetch_product_data` or wherever it rules; B3 adds no reader.

### 2.6 The camera route under the flag (`image_routes.py`)

- Imports: `from app.services.openai_service import identify_products, public_vision_products, vision_identity_v2_enabled` (`:19` widened) and `from app.services.auth_service import get_user_preferences` (new line, the text_routes.py:23 import).
- Wire hygiene (unconditional, no flag read, a no-op for V1 products): `"products": public_vision_products(products)` at the `need_second_product` body (`:433`), `result["metadata"]["identified_products"] = public_vision_products(products)` (`:488` and `:493`), `_camera_failure_envelope(result, request, public_vision_products(products), vision_cost)` (`:533`, `:579`) and `"products": public_vision_products(products)` in the `comparison_failed` body (`:631`). The list passed INTO `compare_from_text` (`:450`) stays the un-stripped `products` (the orchestrator reads the internal keys). `product_names`, the moderation join and the size enrichment read public keys only and are untouched.
- Forwarding (the ONE route-level flag read, immediately before `:450`):

```
_extra = {}
if vision_identity_v2_enabled():
    _uid = user.get("id") if user else None
    if _uid:
        _extra["user_id"] = _uid
        _prefs = await _camera_user_preferences(_uid)
        if _prefs:
            _extra["user_preferences"] = _prefs
result = await service.compare_from_text(query, region=region, vision_products=products, nocache=nocache, **_extra)
```

`_camera_user_preferences(user_id)` (module helper): `try: r = await get_user_preferences(user_id)` -> `r.get("preferences") if r.get("success") and r.get("preferences_completed") else None`; any exception -> `logger.warning("[IMAGE] preferences read failed: %s", type(e).__name__)` and `None` (a scan never dies on a preferences read; the text route has no such guard and that is its own matter). Flag OFF: `_extra == {}` and the call is the base call `compare_from_text(query, region=region, vision_products=products, nocache=nocache)` -- one positional, three kwargs, nothing else (pinned with a recorder, 5 P6). `selected_category` is NOT forwarded: the route has no such input and T23 forbids adding one (R0-6); a chip reaches the camera path only when B8/T23 re-records (stated in 9).

### 2.7 Test seams (production values in brackets)

`openai_service.client` [the module AsyncOpenAI] -- tests patch it with a fake whose `chat.completions.create` is a recorder; `openai_service.vision_timeout_seconds` [the env reader] -- a raising stand-in proves the OFF path never reads it; `openai_service._VISION_V2_MAX_TOKENS` [1000]; `image_routes.identify_products`, `image_routes.StructuredComparisonService`, `image_routes.get_user_preferences` [the real functions] -- the `tests/test_retro_w2_1.py:330-363` `_stub_camera` / `_post_identify` harness plus a spy service recording `compare_from_text` args/kwargs; `content_safety_service.get_content_safety_service` [the singleton] -- the `_Safety` stub; `scs.classify_category_llm` [the A2b LLM] -- `AsyncMock(return_value="other")` so a vision pair whose names are blind never dispatches; `scs.StructuredComparisonService._fetch_product_data` -- a recorder raising a sentinel so the REST entry returns the generic failure after the identity dicts are built. Env via `monkeypatch.setenv` / `delenv` only; never a `.env`.

### 2.8 Flag-OFF identity (the unit's main invariant)

With `ENABLE_VISION_IDENTITY_V2` unset / "false" / "0" / "off" / "" and EVERY other knob of the unit present (`VISION_TIMEOUT_SECONDS` set, `OPENAI_MODEL_VISION` unset or set), for every input the base accepted:
- `identify_products` sends the same single user message with the text sha `bb737687c40969abb4dea936f522d5be4a0693bcd5e2f7b09e28a78204462ae3` and the same image parts, with kwargs exactly `{model, messages, max_tokens 500, temperature 0, store False}` (no `response_format`), with no `asyncio.wait_for`, reads no knob, and returns the V1 dicts (five keys, "Unknown" / "Unknown Product" / "medium" defaults) or the V1 parse-failure dict; a None content still raises `AttributeError` (the base 500 -- it is not repaired OFF, by R-A1);
- the orchestrator's identity dicts are the base six keys (`_vision_identity_fields` returns `{}` on a V1 product);
- the camera route calls `compare_from_text(query, region=region, vision_products=products, nocache=nocache)` with no other kwarg, never calls `get_user_preferences`, and every body (`need_second_product`, `comparison`, `comparison_failed`, the envelope, `metadata.identified_products`) equals the base body byte for byte (`public_vision_products` of a V1 list is an equal list);
- the three fixed `test_camera_vision.py` nodes change the TEST fixture only (the production bytes they exercise are the V1 path above);
- the only new work OFF is the two env reads of the flag (service + route) and the copy made by `public_vision_products`.

### 2.9 Failure table (flag ON)

| failure | `identify_products` | route result | log |
|---|---|---|---|
| wait_for expiry (slow vision) | raises `TimeoutError` | 503 `{"code": "LLM_UNAVAILABLE", "error": LLM_UNAVAILABLE_FRIENDLY_MESSAGE}`; both refunds (exit 1) | `[VISION_V2] vision call timed out after <x.x>s` + the route's existing `[IMAGE] Vision call failed: ...` |
| content None / refusal / no choice | raises `LLMUnavailableError` | the same 503, both refunds | `[VISION_V2] no content: finish_reason=<lit> refused=<bool>` |
| `finish_reason == "length"` | the parse-failure dict (`error` names `finish_reason=length`) | 200 `action: "error"` ("Could not identify products..."), both refunds (exit 2) | `[VISION_V2] finish_reason=length; ...` + the route's constant `[IMAGE] Vision parse error` |
| invalid JSON / unexpected shape | the parse-failure dict | 200 `action: "error"`, refunds | the route's constant line |
| every candidate `is_product` false or out of range | `products == []` | 200 `action: "error"` ("No products could be identified..."), refunds (exit 4) | the `[VISION_V2] candidates=... kept=0 ...` counts |
| exactly one photo yields a product | one product | 200 `action: "need_second_product"` (exit 5), refunds | counts |
| OpenAI 400 on `response_format` (an id that rejects structured outputs) | `openai.BadRequestError` propagates | 500 "Image analysis failed. Please try again." (today's non-transient branch; rollback = unset the flag) | the route's line; a canary item (9) |
| OpenAI 429 / 5xx / connection | the SDK exception propagates (as today) | 503 `LLM_UNAVAILABLE` (today's branch) | as today |
| `get_user_preferences` raises | n/a | the compare runs without `user_preferences` (with `user_id`) | `[IMAGE] preferences read failed: <Type>` |
| `usage` None on the reply | `tokens_used` 0, `cost` 0.0 | as the products decide | none |

## 3. Change list, in the order GREEN applies it

Before the first edit: byte-copy (Python `shutil.copyfile`) every existing file below into `<scratchpad>/b3_green_before/` with its sha256; restore only from those copies.

1. `app/services/openai_service.py`: `import asyncio`, `import math`, `import os` added to the import block (`:4-7`); after `clean_json_response` (`:108`) the constants `_VISION_TIMEOUT_DEFAULT`, `_VISION_V2_MAX_TOKENS`, `VISION_CATEGORY_KEYS`, `VISION_V2_PUBLIC_KEYS`, `VISION_V2_INTERNAL_KEYS`, `VISION_PROMPT_V2`, `VISION_RESPONSE_FORMAT_V2`, the readers `vision_identity_v2_enabled`, `vision_timeout_seconds`, the helpers `public_vision_products`, `_normalize_vision_products_v2`, `_select_best_per_image`, `_identify_products_v2(image_data_list)` (2.4 steps 2-11); `identify_products` gains `if vision_identity_v2_enabled(): return await _identify_products_v2(image_data_list)` as its first statement after the docstring; lines `:131-235` otherwise unchanged (the V1 body).
2. `app/services/structured_comparison_service.py`: `_vision_identity_fields` after `_product_display_identity` (`:1343`); the one-splat edit in BOTH twins (`:4223` and `:4861`, the `"_vision": True,` lines gain `**_vision_identity_fields(vp),`).
3. `app/api/image_routes.py`: the two imports (2.6); `_camera_user_preferences`; the six `public_vision_products(...)` wire sites; the `_extra` block before `:450` and `**_extra` on the call.
4. `tests/test_camera_vision.py:50-53, 72-75, 96-99`: `mock_usage = MagicMock(); ...` -> `mock_usage = types.SimpleNamespace(total_tokens=..., prompt_tokens=..., completion_tokens=...)` (`import types` added at `:15`); nothing else in the file.
5. `tests/.pre_impl_failures.txt`: delete rows `:81-83` (the three camera_vision ids); in the header, replace the "test_camera_vision x3 -- fixture bug ..." bullet (`:54-56`) with a dated PRUNED paragraph: "PRUNED <date> (B3, session 80): the three test_camera_vision.py::TestIdentifyProductsMocked rows -- the fixture bug (MagicMock usage; TypeError at openai_service.py:81) fixed in the test with types.SimpleNamespace; proof: tests/test_camera_vision.py 25 passed / 0 failed / 1 deselected through the bounded runner at <HEAD sha>, [pyt] line in the PR body"; "Effective baseline count = 11" (`:65`) -> 8. No other row moves.
6. `python -m scripts.gen_baseline_mirror` -> `tests/PRE_IMPL_FAILURE_BASELINE.md` regenerated (`BASELINE_COUNT: 8`, rows 3-5 gone, renumbered); `python -m scripts.gen_baseline_mirror --check` exit 0.
7. The four clear-lists: `tests/test_model_config_enforced.py:103-105` tuple gains `"ENABLE_VISION_IDENTITY_V2"`; `tests/w4_11_prompt_digest_recorder.py:41-45` FLAGS gains it; `tests/test_prompt_fence.py:46-52` `_W411_FLAGS` gains it; `tests/test_s71_u13_compare_auth_required.py:76-83` CLEAN_ENV gains it. The W4-11 fixture is NOT regenerated.
8. NEW `tests/test_s80_b3_vision_identity_v2.py` (section 5), written by RED, frozen for GREEN.
9. `CLAUDE.md`: the flag row (8.1) as a new "SESSION 80 flag (B3)" block after the SESSION 79 B3-B block (`CLAUDE.md:471-472`); `:502` rewritten in place: "skips those 11 nodes" -> 8, the camera_vision sentence replaced by "the three test_camera_vision.py::TestIdentifyProductsMocked nodes were fixed in B3 (session 80; a SimpleNamespace usage fixture) and run in CI again", "Fixing the 11 is #89" -> "Fixing the remaining 8 is #89", "green with 11 known nodes deselected (the 11 node-id rows ..., recounted 2026-10-03)" -> 8 and the new date; the Tests bullet `:501` "then CLEANED to **11** ... (`tests/.pre_impl_failures.txt`)" gains "then **8** (B3, session 80)"; `VISION_TIMEOUT_SECONDS` under Optional env vars. NOTE: H0 (PR #363, sc-s80-h0) rewrites `:502`'s ":109" at the same time -- GREEN rebases onto main after #363 merges and re-applies this edit on the merged sentence (Q7).

No other file. No `requirements*` change, no client file, no `.githooks` change, no migration, no `processors.json` change (no new host), no `tests/_env_safety.py` change.

## 4. Existing pins

### 4.1 Pins that change (deliberately), one row each

| # | test node / file | today | after | reason |
|---|---|---|---|---|
| E1 | `tests/test_camera_vision.py::TestIdentifyProductsMocked::test_malformed_response_returns_error` | FAILED at base (TypeError at `openai_service.py:81`), deselected in CI via `.pre_impl_failures.txt:82` | PASSES (SimpleNamespace usage, measured 1.7); assertions unchanged | a FIXTURE defect, not a product bug (R-A14; `.pre_impl_failures.txt:54-56`); the test-side fix is a reviewed change of this unit (brief item 6) |
| E2 | `::test_successful_identification` (row `:83`) | FAILED (same) | PASSES, assertions unchanged | same |
| E3 | `::test_empty_product_fields_normalized` (row `:81`) | FAILED (same) | PASSES, assertions unchanged | same |
| E4 | `tests/.pre_impl_failures.txt` rows `:81-83` + header `:54-56`, `:65`; `tests/PRE_IMPL_FAILURE_BASELINE.md` (`BASELINE_COUNT: 11`, rows 3-5) | 11 ids | 8 ids; mirror regenerated by the script | the per-row prune with pass proof the header prescribes (`:25-27`); `test_ci_gates.py::test_baseline_count_is_rederivable_from_the_committed_file` re-derives both |
| E5 | `tests/test_model_config_enforced.py:103-105` `_clean_env`, `tests/w4_11_prompt_digest_recorder.py:41-45` FLAGS, `tests/test_prompt_fence.py:46-52` `_W411_FLAGS`, `tests/test_s71_u13_compare_auth_required.py:76-83` CLEAN_ENV | five / ten / ten / seventeen names | each plus `ENABLE_VISION_IDENTITY_V2` | R0-6: a developer env carrying the flag must not leak into the digest, fence, M1 or T23 nodes; the fixtures' bytes do not move |
| E6 | `tests/test_model_config_enforced.py::test_no_call_site_passes_raw_sampling_kwargs` (`:134-143`) | 15 sites | 16 sites (the V2 call), still `>= 15`, still zero raw `temperature=` / `max_tokens=`; the assertion itself is unedited | a count the pin tolerates by design |
| E7 | `CLAUDE.md:501-502` (the "11 known nodes" sentences) | 11 | 8, dated | principle 5 (edit in place) |

### 4.2 Pins that must stay green and unedited (green at base; 1.10 for the three measured files)

`tests/test_image_identify_llm_unavailable_s69.py` (the 503 `LLM_UNAVAILABLE` branch for `RateLimitError`, `APIConnectionError`, `LLMUnavailableError`; the 500 literal for anything else -- the V2 None-content raise rides the first branch, the OFF path keeps the 500), `tests/test_retro_w2_1.py` (the camera body base pins `:484-560`: `identified_products == _vision(2)["products"]`, the delivery body, the unsuccessful bodies in all four flag states, the envelope helper, the anon refunds; every one runs with the new flag unset and asserts body EQUALITY, so they ARE the flag-OFF wire pins for `public_vision_products`), `tests/test_paid_route_metering.py` (the camera consume/refund rows incl. `vision_raised_500`), `tests/test_m13_26_image_error_envelope.py` (the `comparison_failed` body), `tests/test_cost_meter_s74.py` (the camera ledger merge), `tests/test_w4_13_measurement_truth.py` + `tests/test_w4_13_flag_off_ledger.py` (the camera `log_search` kwargs -- untouched), `tests/test_s71_u13_compare_auth_required.py` (T23: no new route parameter; the fixture untouched), `tests/test_m13_03_paid_work_gating.py`, `tests/test_b2_strict_optional_auth.py`, `tests/test_comparison_id_echo.py`, `tests/test_security_regression.py`, `tests/test_text_error_envelope_no_raw_exception.py`, `tests/test_logger_no_query_leak.py`, `tests/test_sentry_channels_u8d_unit.py` (R8), `tests/test_openai_key_log_hygiene_s69.py`, `tests/test_model_config.py`, `tests/test_u3c_store_false_pin.py` (the V2 call still goes through the chokepoint that forces `store=False`), `tests/test_prompt_fence.py` (every row other than the list edit), `tests/w4_11_prompt_digest_recorder.py` + `tests/fixtures/w4_11_prompt_render_digests.json` (NOT regenerated), `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main` (text-path digests; the vision twins' splat is a no-op on non-vision runs), `tests/test_explicit_pair_category.py` and every `_resolve_pair_category` pin (unchanged reader), `tests/test_ci_gates.py` (every node other than the mirror re-derivation, which stays green because the mirror is regenerated), and the rest of the comm set (section 7).

## 5. RED tests

New file `tests/test_s80_b3_vision_identity_v2.py` (pure ASCII, CRLF like its neighbours, hermetic under the conftest netguard; no edit to any existing test except E1-E5). Harness:

- `import app.main` first (configure_logging), `from app.services import openai_service as osvc, api_budget_service, structured_comparison_service as scs`, `from app.api import image_routes`.
- `UNIT_ENV = ("ENABLE_VISION_IDENTITY_V2", "VISION_TIMEOUT_SECONDS", "OPENAI_MODEL_VISION", "ENABLE_LLM_PREFLIGHT_BREAKER", "ENABLE_PAID_ROUTE_METERING", "ENABLE_CAMERA_FAILURE_ENVELOPE", "ENABLE_ANON_USAGE_GATE", "ENABLE_SEARCH_LOG_TRUTH")`; an autouse fixture `delenv`s all of them, disables the limiter (`limiter.enabled = False`), and sets `OPENAI_API_KEY` to `"sk-" + "b3-unit-dummy-key"` only if unset (the camera test's import-time need; built by concatenation).
- `FULL_CONFIG(monkeypatch, flag)`: `setenv("VISION_TIMEOUT_SECONDS", "7.5")`, `setenv("ENABLE_VISION_IDENTITY_V2", flag)` or `delenv` for `None` (B1 rule: every OFF row runs with the knob present).
- `_FakeClient(replies)`: `chat.completions.create(**kwargs)` records `kwargs` (deep-copied) into `calls`, awaits an optional `delay`, returns the next reply; `_reply(content, finish_reason="stop", refusal=None, usage="simple")` builds a `types.SimpleNamespace` response tree (`choices=[SimpleNamespace(finish_reason=..., message=SimpleNamespace(content=..., refusal=...))], usage=SimpleNamespace(total_tokens=100, prompt_tokens=80, completion_tokens=20)`), `usage=None` for the usage-None row. Installed with `monkeypatch.setattr(osvc, "client", fake)`.
- `IMG(n)` = `n` dicts `{"bytes": b"\xff\xd8" + bytes([i]) * 8, "mime_type": "image/jpeg"}`; `run(coro)` = `asyncio.run`.
- Fixtures (JSON strings, pure ASCII): `V04_OBJECT` = `{"products": [{"image_index": 0, "brand": "Sefiki", "name": "Limited Edition", "category": null, "product_type": "wrist watch", "size_or_count": null, "visible_price": null, "distinguishing_features": ["gold case"], "is_product": true, "confidence": "low"}, {"image_index": 1, "brand": "Violin", "name": "SHAHRAZAD L'INTENSE", "category": "other", "product_type": "violin", "size_or_count": null, "visible_price": null, "distinguishing_features": [], "is_product": true, "confidence": "low"}]}`; `V07_ARRAY` = a bare array of two `GUESS` / `GUESS!` candidates at `image_index` 0 and 1, `category` "fashion", `confidence` "medium", `distinguishing_features` `["white logo tee"]` and `["denim shirt", "polyurethane label"]`; `V01_OBJECT` = `OSMIA` / `Woody F` (`size_or_count` null) at 0 and `AL IBDAA` / `EAU DE PARFUM` (`size_or_count` "100ml") at 1, both `fragrances`, `high`; `TWO_IN_ONE` = three candidates: index 0 `high` A, index 0 `medium` B, index 1 `low` C; `NON_PRODUCT` = index 0 `is_product` false only, index 1 true; `BAD_INDEX` = indices 7, -1, true (a bool), "0" (a str) plus one valid; `COERCE` = `confidence` `"HIGH "`, `"certain"`; `category` `"Fragrance"`, `""`, null; `distinguishing_features` `"not a list"`, `[1, "ok", ""]`; `is_product` missing.
- Route harness: the `tests/test_retro_w2_1.py` idiom re-implemented locally (not imported: a `test_*` module is never imported): `_stub_camera(monkeypatch, vision=..., compare=...)` patches `image_routes.identify_products`, `content_safety_service.get_content_safety_service` (allowed), `audit_service.log_content_blocked`, `image_routes.log_search`, `image_routes.save_comparison_and_track_cohort`, the usage functions (a `Ledger` recording consume/refund/lifetime), and `image_routes.StructuredComparisonService` with a `_Spy` whose `compare_from_text(self, *a, **kw)` appends `(a, dict(kw))` to `SPY_CALLS` and returns a deep copy of `DELIVERED` (the W2-1 shape); `_post_identify(client, n_images=2)`; `authed` overrides `get_optional_user` with `{"id": "b3-" + node name, "email": "b3@example.test", "access_token": "b3-token"}`; `image_routes.get_user_preferences` patched per row (`raising=False` so the OFF row's recorder is installable at base, where the name does not exist yet). For the end-to-end rows the REAL `identify_products` runs with `_FakeClient` (the `test_image_identify_llm_unavailable_s69.py` pattern) and only the compare side is stubbed.
- Orchestrator harness: `svc = scs.StructuredComparisonService()`; `monkeypatch.setattr(scs, "classify_category_llm", AsyncMock(return_value="other"))`; `monkeypatch.setattr(svc, "_fetch_product_data", _rec)` where `_rec(product_info, *a, **k)` appends `dict(product_info)` to `SEEN` and raises `RuntimeError("b3 stop")` (the generic except returns `success False`; no network, no LLM); `STREAM_HARD_CAP_SECONDS` left alone (the run ends in milliseconds).
- RED = fails at base `81df2b64` on an AssertionError only (a missing symbol is read with `getattr(module, name, None)` and asserted callable / not None, never attribute-accessed); PIN = green at base, run with the FULL configuration and a recorder.

| ID | Kind | Setup | Assertions | Why it fails at base | Satisfied by |
|---|---|---|---|---|---|
| P1 | PIN | FULL_CONFIG flag `None`, then parametrised over `[None, "", "false", "0", "no", "off", "garbage"]`; `_FakeClient([_reply("[]")])`; `IMG(2)`; `monkeypatch.setattr(osvc, "vision_timeout_seconds", _raise, raising=False)` | `sha256(calls[0]["messages"][0]["content"][0]["text"]) == "bb737687c40969abb4dea936f522d5be4a0693bcd5e2f7b09e28a78204462ae3"` (VISION_PROMPT_SHA_OFF); one message, role user, content types `["text", "image_url", "image_url"]`, each image part `detail == "auto"` and url startswith `data:image/jpeg;base64,`; the raising stand-in never ran | (passes: 1.7) | the flag-first branch; `:131-194` untouched |
| P2 | PIN | as P1 | `set(calls[0]) == {"model", "messages", "max_tokens", "temperature", "store"}`; `model == "gpt-4o-mini"`; `max_tokens == 500`; `temperature == 0`; `store is False`; `"response_format" not in calls[0]` (VISION_KWARGS_OFF); result `== {"products": [], "tokens_used": 100, "cost": 2.4e-05}` | (passes: 1.7) | same |
| P3 | PIN | FULL_CONFIG flag "false"; reply = `V04_OBJECT` (an object) and separately a bare array whose items carry `category` / `image_index` / `is_product` extras and one item `{"name": "Something"}` | the object -> `products == []` (the base drop); the array -> each product has EXACTLY the five V1 keys, `brand == "Unknown"` and `confidence == "medium"` on the sparse item, no key starts with `_`; no `[VISION_V2]` record in caplog | (passes: `:213-222`) | the V1 normaliser untouched |
| R1 | RED | FULL_CONFIG "true"; `_FakeClient([_reply(V04_OBJECT)])`; `IMG(2)` | `len(products) == 2`; `set(products[0]) == set(VISION_V2_PUBLIC_KEYS) | set(VISION_V2_INTERNAL_KEYS)` (read with `getattr(osvc, name, None)` first, asserted not None); products[0] `brand "Sefiki"`, `name "Limited Edition"`, `confidence "low"`, `_image_index 0`, `_category None`, `_product_type "wrist watch"`, `_distinguishing_features ["gold case"]`, `_is_product True`; products[1] `_category == "other"`, `_image_index 1`; `tokens_used == 100`; `cost == 2.4e-05` | the object is dropped -> `products == []` | 2.4 steps 6-9 |
| R2 | RED | "true"; reply `V07_ARRAY` (bare array) | two products in index order; `_distinguishing_features` carried verbatim (`["white logo tee"]`, `["denim shirt", "polyurethane label"]`); `_category == "fashion"` both; public keys unchanged | V1 keeps five keys -> `_category` missing | step 6 (bare array), 7 |
| R3 | RED | "true"; reply `"[]"`; `IMG(2)` | `calls[0]["response_format"]` deep-equals the 2.3 object (`strict is True`, name `vision_products_v2`, the enum = the nine keys + None, every required list); `max_tokens == getattr(osvc, "_VISION_V2_MAX_TOKENS")` (1000); `temperature == 0`; `store is False`; the text contains `"image_index"`, `"electronics, grocery, supplements, makeup, skincare, haircare, fragrances, fashion, other"`, `"Arabic script"`, `"is_product"`, does NOT contain `"WITHOUT packaging"`, and its sha differs from the OFF sha; layout still `["text", "image_url", "image_url"]` | no `response_format` key | 2.2, 2.3, 2.4 step 3 |
| R4 | RED | "true"; reply `_reply(None, refusal="I cannot help with that")`; also `_reply(None)` (no refusal) and a reply with `choices=[]` | `with pytest.raises(Exception) as ei: run(identify_products(IMG(1)))`; `assert isinstance(ei.value, api_budget_service.LLMUnavailableError)`; the message contains none of `"429"`, `"rate"`, `"quota"`; one WARNING record starting `[VISION_V2] no content` whose message contains `refused=True` / `refused=False` and never the refusal text | base raises `AttributeError` (asserted type -> AssertionError) | 2.4 step 5 |
| R4b | RED | route: `_stub_camera` with `identify_products` REAL + `_FakeClient([_reply(None, refusal="x")])`, `authed`, `setenv(ENABLE_PAID_ROUTE_METERING, "true")`, FULL_CONFIG "true" | `resp.status_code == 503`; `body["code"] == "LLM_UNAVAILABLE"`; `body["error"] == LLM_UNAVAILABLE_FRIENDLY_MESSAGE`; `ledger.refunds == ledger.consumes` (one each); `SPY_CALLS == []` | base: 500 | the raise rides `image_routes.py:324-328` |
| R5 | RED | "true"; reply `_reply('[{"brand"', finish_reason="length")` | `result["products"] == []`; `"finish_reason=length" in result["error"]`; `result["raw_response"] == '[{"brand"'`; `result["tokens_used"] == 100`; `result["cost"] == 0`; one WARNING `[VISION_V2] finish_reason=length` | base: `error` is "Failed to parse response: Expecting ..." (no "length") and no record | 2.4 step 5 |
| R5b | RED | route: REAL identify + the R5 reply, `authed`, metering ON | 200; `body["action"] == "error"`; `body["error"] == "Could not identify products in the image. Please try a clearer photo."`; `body["vision_cost"] == 0`; refunds == consumes; `SPY_CALLS == []` | base: same body (the parse-failure path) -- so this row asserts the WARNING record too, which is absent at base | exit 2 unchanged + the log |
| R6 | RED | "true"; reply `TWO_IN_ONE` (object); `IMG(2)` | `[p["name"] for p in products] == ["A", "C"]`; `[p["_image_index"] for p in products] == [0, 1]`; the INFO line reports `candidates=3 kept=2 dropped_not_product=0 dropped_out_of_range=0` | base: three products | step 8 |
| R6b | RED | "true"; `TWO_IN_ONE` with `IMG(1)` (one photo, two candidates at index 0, the third at index 1 is now out of range) | `len(products) == 1`; the line reports `dropped_out_of_range=1` | base: three products | step 7-8 (Q2 records the product consequence) |
| R7 | RED | "true"; reply `NON_PRODUCT`; `IMG(2)` | `len(products) == 1`; `products[0]["_image_index"] == 1`; the line reports `dropped_not_product=1` | base: two products | step 8 |
| R7b | RED | route: REAL identify + `NON_PRODUCT`, `authed`, metering ON | 200 `action == "need_second_product"`; `body["products"]` has one dict with NO `_`-prefixed key and `set(...) == set(VISION_V2_PUBLIC_KEYS)`; `message` starts `"Identified: "`; refunds == consumes | base: two products -> `action == "comparison"` | step 8 + `public_vision_products` at `:433` |
| R8 | RED | "true"; reply `BAD_INDEX`; `IMG(2)` | exactly one product kept (the valid one); `dropped_out_of_range=4`; no exception | base: five products (the bool / str indices are ignored) | step 7 |
| R9 | RED | "true"; reply `COERCE` | `confidence` values `["high", "low"]`; `_category` values `["fragrances", None, None]`; `_distinguishing_features` `[]` for the string and `["ok"]` for the mixed list; `_is_product True` when the key is missing | base: `confidence` passes through raw ("HIGH ") | step 7 |
| R10 | RED | "true"; `setenv("VISION_TIMEOUT_SECONDS", "0.05")`; `_FakeClient` with `delay=2.0`; a recorder on `osvc.vision_timeout_seconds` (wrapping the real one when present) | `pytest.raises(TimeoutError)`; wall `< 1.5 s`; the knob recorder was called once; one WARNING `[VISION_V2] vision call timed out after 0.1s` (format `%.1f`) | base: no `wait_for` -> the fake returns after 2 s, no raise | step 3 |
| R10b | RED | route: REAL identify + the R10 fake, FULL "true", `authed`, metering ON | 503 `LLM_UNAVAILABLE`; refunds == consumes; `SPY_CALLS == []` | base: 200 after the delay | `image_routes.py:324-328` via `_openai_failure_is_transient(TimeoutError)` |
| R11 | RED | `fn = getattr(osvc, "vision_timeout_seconds", None)`; parametrised env `[unset, "", "   ", "garbage", "inf", "nan", "0", "-3", "1e400", " 12.5 ", "20"]` | `callable(fn)`; results `20.0` for every row except `" 12.5 " -> 12.5` and `"20" -> 20.0`; a WARNING naming `VISION_TIMEOUT_SECONDS` (never the value's meaning beyond `%r`) for garbage / inf / nan / 0 / -3 / 1e400 and none for the others | the helper is missing | 2.1 |
| R12 | RED | `fn = getattr(osvc, "vision_identity_v2_enabled", None)`; values `["true", "TRUE", " true ", "1", "yes", "ON", "on"]` -> True; `[None, "", "false", "0", "no", "off", "garbage", "tru e"]` -> False | as listed | the helper is missing | 2.1 (the house idiom, `.strip().lower()`) |
| R13 | RED | `fn = getattr(scs, "_vision_identity_fields", None)` table: a V2-shaped vp (five public + five internal keys) -> the four `_vision_*` keys with the given values (`_vision_distinguishing_features` a NEW list equal to the input); a V1 vp (five keys) -> `{}`; a vp with `_is_product` but `_distinguishing_features` `None` -> `[]`; a non-dict -> `{}` | as listed | the helper is missing | 2.5 |
| R14 | RED | orchestrator harness; `run(svc.compare_from_text("Sefiki Limited Edition vs Violin SHAHRAZAD L'INTENSE", vision_products=[v2a, v2b]))` with the V2-shaped dicts of R1 | `result["success"] is False` (the sentinel path); `len(SEEN) == 2`; `set(SEEN[0]) == {"brand", "name", "variant", "category", "search_query", "_vision", "_vision_confidence", "_vision_category", "_vision_distinguishing_features", "_vision_is_product"}`; `SEEN[0]["_vision_confidence"] == "low"`, `SEEN[1]["_vision_category"] == "other"`, `SEEN[0]["_vision_category"] is None`, `SEEN[0]["_vision_is_product"] is True`; the base six values unchanged (`search_query == "Sefiki Limited Edition"`, `_vision is True`) | the identity dicts have six keys | 2.5 (REST twin) |
| P4 | PIN | the R14 harness with V1-shaped vps (five public keys) and `ENABLE_VISION_IDENTITY_V2=true` in the env (full config, flag ON, V1 shape) | `set(SEEN[0]) == {"brand", "name", "variant", "category", "search_query", "_vision"}` exactly; values as base | (passes) | presence-gating: a "copy always" mutant adds None-valued keys |
| P5 | PIN | as P4 with the flag unset / "false" | the same six keys | (passes) | flag-OFF identity of the twins |
| R15 | RED | source pin: `src = Path(scs.__file__).read_text()`; `src.count("**_vision_identity_fields(vp)") == 2` and both occurrences sit on a line that also contains `"_vision": True` | as stated | count 0 | both twins (the stream twin has no cheap runtime harness; this pins lockstep) |
| R16 | RED | route forwarding: `_stub_camera` (vision stub = two V1-shaped products), `authed`, FULL "true", `image_routes.get_user_preferences` -> `{"success": True, "preferences_completed": True, "preferences": {"budget": "mid", "priorities": ["value"]}}` | `len(SPY_CALLS) == 1`; `args == ("B0 N0 vs B1 N1",)`; `kwargs == {"region": "bahrain", "vision_products": <the two dicts>, "nocache": False, "user_id": authed["id"], "user_preferences": {"budget": "mid", "priorities": ["value"]}}`; the prefs stub was called once with `authed["id"]`; 200 `action == "comparison"` | kwargs lack `user_id` | 2.6 |
| R16b | RED | as R16 with prefs `{"success": True, "preferences_completed": False, "preferences": {...}}`; then `{"success": False}`; then a raising stub | `"user_preferences" not in kwargs` and `kwargs["user_id"] == authed["id"]` in all three; the raising row logs one WARNING `[IMAGE] preferences read failed: RuntimeError` and still returns 200 | kwargs lack `user_id` | 2.6 (conditional kwargs; fail-soft) |
| R16c | RED | as R16 with `anonymous` (no user override), metering OFF | `kwargs == {"region": "bahrain", "vision_products": ..., "nocache": False}` and the prefs stub NOT called -- wait: this is identical to the base call, so the row is a PIN-ON (green at base); recorded as such | (passes) | no user -> no kwarg |
| P6 | PIN | as R16 but FULL_CONFIG flag `None` and separately `"false"`, with the prefs RECORDER installed (`raising=False`) | `kwargs == {"region": "bahrain", "vision_products": <two dicts>, "nocache": False}`; `args == (query,)`; the prefs recorder NEVER called; body `==` the W2-1 delivery body with `metadata.identified_products == vision["products"]` | (passes) | flag-OFF route identity; kills "not gated" |
| R17 | RED | wire hygiene: `_stub_camera` with a V2-shaped vision stub (the R1 dicts, all ten keys), `authed`, each of: (a) flag ON delivery; (b) flag OFF delivery; (c) one-product stub -> `need_second_product`; (d) compare raises -> `comparison_failed`; (e) metering ON + envelope ON + an unsuccessful result -> the envelope | in every body, every dict under `metadata.identified_products` / `products` has no key starting with `_` and equals `{k: v for k, v in stub if not k.startswith("_")}`; the spy received the UN-stripped dicts (`"_category" in SPY_CALLS[0][1]["vision_products"][0]`) | base ships the stub dicts verbatim (`_category` on the wire) | `public_vision_products` at the six sites |
| P7 | PIN | R17 with V1-shaped stubs (`_vision(2)` of the W2-1 harness) in both flag states | bodies equal the base pins' expected literals (`identified_products == vision["products"]`, the W2-1 `expected` dict) | (passes) | the copy of a V1 list is equal |
| R18 | RED | end to end V04: REAL identify + `_FakeClient([_reply(V04_OBJECT)])`, moderation allowed, `_Spy` compare, `authed`, metering ON, FULL "true" | `SPY_CALLS[0][0] == ("Sefiki Limited Edition vs Violin SHAHRAZAD L'INTENSE",)`; the two `vision_products` carry `confidence "low"`, `_category None / "other"`, `_is_product True`; 200 `action == "comparison"`; `metadata.identified_products` has no `_` key and `confidence == "low"` on both; `ledger.lifetime == [authed["id"]]`, no refund (a delivery: B2 decides the refusal, not B3) | base: the object is dropped -> 0 products -> `action == "error"` | the whole V2 path |
| R19 | RED | end to end V07: REAL identify + `V07_ARRAY`, as R18 | `SPY_CALLS[0][0] == ("GUESS GUESS! vs GUESS GUESS!",)`; `vision_products[0]["_distinguishing_features"] == ["white logo tee"]`, `[1] == ["denim shirt", "polyurethane label"]`; the orchestrator-side carry is R14's job | base: the array has no `_` keys -> AssertionError | step 7 |
| R20 | RED | end to end V01: REAL identify + `V01_OBJECT`, as R18 | `SPY_CALLS[0][0] == ("OSMIA Woody F vs AL IBDAA EAU DE PARFUM 100ml",)` (the route's size enrichment `:403-406` still appends "100ml"); both `_category == "fragrances"`, `confidence == "high"`; `identified_products[1]["name"] == "EAU DE PARFUM 100ml"` and no `_` key | base: no `_category` | the public shape is V1's; the enrichment is untouched |
| R21 | RED | `keys = getattr(osvc, "VISION_CATEGORY_KEYS", None)` | `keys is not None`; `set(keys) == extraction_service._CANONICAL_CATEGORIES`; `", ".join(keys) + "\n"` equals the `extraction_service.py:1357-1358` string (read from the module source around `classify_category_llm`) -- i.e. the same nine keys in the same order as the text path | missing | 2.1 |
| P8 | PIN | log hygiene: for every ON row above, `caplog` records of the `app.services.openai_service` and `app.api.image_routes` loggers contain none of `"Sefiki"`, `"Violin"`, `"GUESS"`, `"OSMIA"`, `"I cannot help"` and no `ERROR`-level record outside the route's existing `[IMAGE] Vision call failed` / `[IMAGE] Vision parse error` lines | (passes vacuously at base: no `[VISION_V2]` lines; non-vacuous on the GREEN bytes) | 2.4 steps 5, 10 (ints, bools, the finish_reason literal) |
| P9 | PIN | the existing M1 node `tests/test_model_config_enforced.py::test_no_call_site_passes_raw_sampling_kwargs` and `::test_image_tier3_dispatches_through_the_breaker_chokepoint` | unchanged | (passes) | the V2 call uses the two kwargs helpers and the chokepoint |
| P10 | PIN | usage None: "true"; `_reply("[]", usage=None)` | `{"products": [], "tokens_used": 0, "cost": 0.0}`; OFF with the same reply raises `AttributeError` (asserted with `pytest.raises(AttributeError)`, the base behaviour kept OFF) | (passes: the OFF half is base; the ON half is the only new assertion -- so this row is RED on its ON half) | 2.4 step 11 |

Counts: RED rows R1-R21 incl. the b/c variants = 27 node groups (R1, R2, R3, R4, R4b, R5, R5b, R6, R6b, R7, R7b, R8, R9, R10, R10b, R11 (table), R12 (table), R13 (table), R14, R15, R16, R16b, R17 (five arms), R18, R19, R20, R21 + P10's ON half = 28); PIN rows P1-P9 + R16c = 10 node groups. The three fixed camera_vision nodes are E1-E3 (4.1), not new rows.

## 6. Mutation table (each mutant applied to a byte copy of the GREEN file, run through the bounded runner with `-k`, restored and sha256-checked; KILLED = an assertion failure)

| # | Mutant | Killed by |
|---|---|---|
| M1 | flag check removed from `identify_products` (always V2) | P1 (sha), P2 (`response_format` present), P3 (object no longer dropped) |
| M2 | reader `os.getenv("ENABLE_VISION_IDENTITY_V2") == "true"` (no strip/lower/set) | R12 (`TRUE`, `" true "`, `1`, `yes`, `ON`) |
| M3 | `vision_timeout_seconds()` read before the flag check | P1 (the raising stand-in) |
| M4 | `wait_for` removed (or `timeout=None`) | R10 (no raise within 1.5 s), R10b |
| M5 | knob parse accepts `inf` / `nan` / `<= 0` (plain `float()`) | R11 |
| M6 | `response_format` dropped, or `strict` False, or the enum missing `None`, or a required key missing | R3 (deep equality) |
| M7 | V2 prompt still contains "WITHOUT packaging" / lacks the enumeration / lacks "image_index" | R3 |
| M8 | None content handled as a parse failure (returns the dict) instead of raising | R4 (`isinstance` LLMUnavailableError), R4b (503 vs 200) |
| M9 | the raise is a bare `RuntimeError` (not `LLMUnavailableError`) | R4, R4b (500 at the route) |
| M10 | `finish_reason == "length"` parsed anyway (no warning, generic error text) | R5 (`"finish_reason=length" in error`, the WARNING) |
| M11 | the object shape rejected (bare array only) or the array rejected (object only) | R1 / R2 |
| M12 | dedupe per `image_index` removed (every candidate kept) | R6 (`["A", "C"]`), R6b |
| M13 | best-candidate picks the LAST or the lowest confidence | R6 (A over B) |
| M14 | `is_product` False candidates kept | R7, R7b |
| M15 | `image_index` range check dropped / bool accepted / str accepted | R8 |
| M16 | `confidence` not lower-stripped, or unknown -> "medium" | R9 |
| M17 | `category` not canonicalised, or "" -> "other" instead of None | R9 |
| M18 | `is_product` missing -> False | R9 (`_is_product True` when missing) |
| M19 | public keys renamed / an internal key without the underscore (e.g. `category`) | R1 (`set(products[0])`), R17 (a non-underscore key would reach the wire) |
| M20 | `public_vision_products` removed at one of the six sites | R17 arms (a) delivery, (c) need_second_product, (d) comparison_failed, (e) envelope |
| M21 | `public_vision_products` strips from the list passed INTO `compare_from_text` | R17 (`"_category" in SPY_CALLS[...]`), R18 |
| M22 | the route forwards `user_id=None` / `user_preferences=None` as explicit kwargs | R16b (`"user_preferences" not in kwargs`), P6 (OFF kwargs exact), R16c |
| M23 | the route reads the prefs regardless of the flag | P6 (recorder never called) |
| M24 | `user_preferences` forwarded when `preferences_completed` is False | R16b |
| M25 | a raising `get_user_preferences` propagates (route 500) | R16b (200 + the WARNING) |
| M26 | `_vision_identity_fields` copies on every vp (no `_is_product` gate) | P4, P5 |
| M27 | `_vision_identity_fields` drops one of the four keys or copies the list by reference | R13 (`is not` the input list), R14 |
| M28 | the stream twin left without the splat | R15 |
| M29 | `VISION_CATEGORY_KEYS` reordered / a key misspelt | R21 |
| M30 | a `[VISION_V2]` line logs a brand / name / the refusal text | P8 |
| M31 | `_VISION_V2_MAX_TOKENS` passed as a literal `max_tokens=1000` | P9 (M1) |
| M32 | the V2 call bypasses `guarded_llm_create` (direct `client.chat.completions.create`) | P9 (`test_image_tier3_dispatches_through_the_breaker_chokepoint`), `test_u3c_store_false_pin` |
| M33 | `usage None` crashes the V2 path | P10 |
| M34 | the three camera_vision fixtures left as MagicMock | E1-E3 red again (the file's own three nodes) |
| M35 | `.pre_impl_failures.txt` rows removed without the mirror regenerated | `test_ci_gates.py::test_baseline_count_is_rederivable_from_the_committed_file` |

Equivalent survivors expected (report for a ruling, do not fix): stripping the wire bodies conditionally on the flag instead of unconditionally (OFF bytes identical either way; R17 arm (b) kills it only because the stub is V2-shaped under OFF, which production never produces -- so it is a design choice, Q6, not a defect).

## 7. Comm set and gates for GREEN (cheapest first; every pytest through the bounded runner, one process at a time)

1. Unit file alone: `tests/test_s80_b3_vision_identity_v2.py` (`--bound 600`), then once more with `ENABLE_VISION_IDENTITY_V2=true` exported in the runner env only (every node still green: the rows set or delete the flag themselves).
2. The three fixed nodes + the file: `tests/test_camera_vision.py` 25 passed / 0 failed / 1 deselected (the pass proof for 3.5; paste the `[pyt]` line into the header paragraph and the PR body); `python -m scripts.gen_baseline_mirror --check` exit 0.
3. Lint / syntax: `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache app/services/openai_service.py app/api/image_routes.py app/services/structured_comparison_service.py tests/test_s80_b3_vision_identity_v2.py tests/test_camera_vision.py` and `-m py_compile` on each. Byte check: `git diff --stat` content lines only; the new test file pure ASCII.
4. CI-order set (one process, sorted, `--bound 1200`): `tests/test_b2_strict_optional_auth.py tests/test_camera_vision.py tests/test_ci_gates.py tests/test_comparison_id_echo.py tests/test_cost_meter_s74.py tests/test_image_identify_llm_unavailable_s69.py tests/test_logger_no_query_leak.py tests/test_m13_03_paid_work_gating.py tests/test_m13_26_image_error_envelope.py tests/test_model_config.py tests/test_model_config_enforced.py tests/test_paid_route_metering.py tests/test_prompt_fence.py tests/test_retro_w2_1.py tests/test_s71_u13_compare_auth_required.py tests/test_s80_b3_vision_identity_v2.py tests/test_security_regression.py tests/test_sentry_channels_u8d_unit.py tests/test_shutdown_drain.py tests/test_text_error_envelope_no_raw_exception.py tests/test_u3c_store_false_pin.py tests/test_w4_13_flag_off_ledger.py tests/test_w4_13_measurement_truth.py` (the camera-route files = `grep -rl 'identify_and_compare|/image/identify|image_routes' tests/` at base, plus the source-scanning and CLAUDE.md-reader files the unit edits or that read its edits).
5. Comm set, base -> head -> base, `comm -13` of the sorted FAILED+ERROR id sets EMPTY. Rule: `grep -rlE "openai_service|image_routes|identify_products|structured_comparison_service|pre_impl_failures|PRE_IMPL_FAILURE_BASELINE|gen_baseline_mirror|regression_gate_diff" tests/test_*.py` (**204 files** at base) UNION the source-scanning pins (the CLAUDE.md list + every `test_*.py` combining `rglob|.glob(|os.walk|iterdir|listdir|scandir|ast.parse|read_text|read_bytes|open(` with an `app` path literal, + `test_start_command*.py`; 16 files, 9 not already in: `test_account_deletion_u8b test_behavior_dimension_translation test_migration_043_delete_user_cascade test_migration_index_predicate_immutability test_model_config test_openai_key_log_hygiene_s69 test_s79_b3b_apple_revoke test_start_command test_u3c_store_false_pin`) UNION the CLAUDE.md readers (`test_ci_gates`, `test_behavior_dimension_translation`; both already in) MINUS `test_precommit_hook*.py` (not in the union anyway). Result: **213 files, 9 chunks (8 x 25 + 13)**, list `<scratchpad>/B3/comm_base.txt`, sha256 `3a927dfae67a2165def77be29d518f8db0d37e8c6757336a4969432e195e7abe` (script `comm_set.py`). GREEN adds the new unit file at HEAD and re-greps at HEAD. The SmartCompareApp-scanning tests (25 files, 16 not in the union) are NOT required: no client file and no client-visible key set changes (the five public vision keys and every body shape are the base ones) -- the orchestrator may add that chunk if it wants the belt (one chunk, about 3 min at the F8 rates). Expected base noise: the `.pre_impl_failures.txt` rows inside the set (after this unit: 8) and the two `tests/test_prompt_truth.py` tiktoken ERRORs on this box; identical both sides. Budget: the F8 run of 218 files took 1,418 s of `[pyt]` elapsed at this code line.
6. Mutation run: section 6 rows via `-k`, `--bound 600` per mutant, byte-copy / restore / sha256.
7. Flag-ON smoke of the unit file (step 1) is the only ON run; nothing else in the suite reads the flag (the four clear-lists delete it).

## 8. CLAUDE.md row and owner steps

### 8.1 The flag row (GREEN writes it; wording may be tightened, content may not)

**SESSION 80 flag (B3, 2026-10-20; default OFF, read PER CALL; a new name, so unset in production by construction (Railway not read); spec `.qa-s80/B3_UNIT_SPEC.md` of the unit worktree):**
- `ENABLE_VISION_IDENTITY_V2` (B3, `app/services/openai_service.py::vision_identity_v2_enabled`, read per call at the vision call and once per camera request) + knob `VISION_TIMEOUT_SECONDS` (default 20.0 s; unset / blank / garbage / inf / nan / <= 0 -> 20.0, one WARNING naming the variable; read per call only under the flag). **Effect ON:** `identify_products` sends `VISION_PROMPT_V2` (exact-label OCR kept; no brand/name invented from shape -- unreadable fields null and confidence low; Arabic-script labels transliterated with the Latin brand kept; the nine canonical categories; a 0-based `image_index`) with `response_format` = the strict json_schema `vision_products_v2` (object `{products:[{image_index, brand, name, category, product_type, size_or_count, visible_price, distinguishing_features, is_product, confidence}]}`), under `asyncio.wait_for(VISION_TIMEOUT_SECONDS)`; the reply may be the object or a bare array; ONE best candidate per `image_index` (is_product true, highest confidence, first) so photo 1 is paired with photo 2; each product keeps the five public keys (`brand, name, size_or_count, visible_price, confidence`) and carries `_image_index, _category, _product_type, _distinguishing_features, _is_product` internally -- the route strips every underscore key from `metadata.identified_products`, the `need_second_product` / `comparison_failed` / envelope `products`; the orchestrator's vision identity dicts (REST and stream twins) carry `_vision_confidence`, `_vision_category`, `_vision_distinguishing_features`, `_vision_is_product` for B2 (never on the wire); a None / refused reply raises `LLMUnavailableError` and a timeout raises `TimeoutError`, both served by the route's EXISTING coded 503 `LLM_UNAVAILABLE` (never a 500), `finish_reason=length` is a logged parse failure (the existing `action: "error"` exit, refund); the camera route forwards `user_id` and, only when `preferences_completed`, `user_preferences` as conditional kwargs into `compare_from_text` (scans get the same personalisation as text; no `selected_category`, the route has none and T23 forbids adding one). Log lines `[VISION_V2] candidates= kept= dropped_not_product= dropped_out_of_range= dropped_non_dict= images= finish_reason=`, `[VISION_V2] no content: finish_reason= refused=`, `[VISION_V2] finish_reason=length; ...`, `[VISION_V2] vision call timed out after <s>`, `[IMAGE] preferences read failed: <Type>` (INFO / WARNING, ints, bools, literals and type names only). **Flag OFF:** byte-identical: the base prompt (sha256 `bb737687...` pinned through the real function with a fake client), the base kwargs `{model, messages, max_tokens 500, temperature 0, store False}` (no response_format, no wait_for, no knob read), the base five-key normaliser, the base six-key identity dicts, the base three-kwarg camera call and the base bodies (`tests/test_s80_b3_vision_identity_v2.py` P1-P7 + the W2-1 camera body pins). **Alongside, test-side (R-A14):** the three `tests/test_camera_vision.py::TestIdentifyProductsMocked` nodes use a `types.SimpleNamespace` usage and run in CI again; `tests/.pre_impl_failures.txt` is 8 rows (per-row prune with pass proof), the mirror regenerated. **Stated limits:** section 9 of the spec (structured outputs on the live vision model are unmeasured offline; a 400 on `response_format` is today's 500 until the flag is unset; a 1-based `image_index` reply drops every candidate; one photo holding two products yields ONE product under V2; V2 alone does not refuse a low-confidence or same-identity pair -- that is B2; the breaker records nothing on our own timeout; the preference read adds one Supabase round trip for signed-in scans). **Activation:** after `ENABLE_RESULT_STATUS_METADATA` per R-A2, one canary window: `OPENAI_MODEL_VISION` smoke-tested first by the owner (names only), then flip, then two never-compared photo pairs (a labelled pair and a label-less pair) watching the `[VISION_V2]` counts, the 503 `LLM_UNAVAILABLE` rate on `/image/identify`, the `action: "error"` rate, p50 vision latency against the 20 s knob and the Railway log for `BadRequestError`. **Rollback:** unset the variable (per call, immediate).

### 8.2 Owner steps (names only)

1. Before the flip: smoke-test the vision model id on a real key with ONE labelled photo through the deployed route (the owner's own gpt-4o test is independent; `OPENAI_MODEL_VISION` stays an env knob, default gpt-4o-mini); confirm the structured-output reply arrives (the `[VISION_V2] candidates=` line) and no `BadRequestError`.
2. Set `VISION_TIMEOUT_SECONDS` only if 20 s is wrong for the chosen model (names only; a value is never typed into chat).
3. Flip `ENABLE_VISION_IDENTITY_V2` on `web` in its R-A2 window (after STATUS_METADATA, before IMAGE_PIPELINE_V2); canary as in 8.1; one dated ledger line.
4. B2 (RESULT_GATE) is where the V04 / V07 refusals land; until it flips, V2 ON changes what is identified and carried, not what is refused.

## 9. Stated limits

1. Whether the live vision model honours `strict` structured outputs together with image input is unmeasured offline (openai 3.3.1 accepts the parameter; the model's behaviour is the canary). A `BadRequestError` on `response_format` is non-transient and takes today's 500 branch until the flag is unset; no message-substring fallback is attempted (R0-8's rule against text classification).
2. `image_index` is 0-based by prompt and schema description; a reply that numbers from 1 drops every candidate for the last image and the first image's products are mis-paired (index 1 = the second photo) -- for a two-photo request every candidate at index 2 is dropped (`dropped_out_of_range`), the canary counter.
3. One photo that shows two products yields ONE product under V2 (one best per `image_index`), so a single-photo two-product upload ends in `need_second_product` where V1 compared them; build 3's camera flow sends two photos (api.ts:256-280 posts every URI it is given; the two-slot ScanCamera and the M13-13 gallery fallback require two picks per CLAUDE.md, not re-measured here). Q2.
4. Candidates with `is_product` false are DROPPED, not carried; B2 therefore never sees a non-product candidate, only its absence (the photo yields nothing). Q3.
5. V2 ON alone still compares a low-confidence pair (V04) and a same-identity pair (V07): the fields are carried, the decision is B2's (R-A6). The V04 crown does not change until B2 flips.
6. The `asyncio.wait_for` cancels the awaiting coroutine; the HTTP request already sent to OpenAI may complete server-side and be billed. The breaker records nothing on a cancellation (W1-3a), so a wedged OpenAI shows as 503s on the camera route, not as a breaker trip; the SDK's own `OPENAI_MAX_RETRIES` attempts are all inside the one bound.
7. The cost formula stays the mini list price whatever `OPENAI_MODEL_VISION` resolves to (digest finding 11; `metadata.openai` from the ledger is the priced figure).
8. Under ON, a signed-in scan adds one `get_user_preferences` round trip (inline on the loop while `ENABLE_SYNC_DB_OFFLOAD` is OFF, about 0.3 s p50 by the CLAUDE.md measurement of that client class) before the compare; a raise costs the personalisation, never the scan.
9. The stream twin is pinned by source text (R15), not by a runtime row; the camera route is REST-only.
10. `confidence` stays a PUBLIC key with the V1 vocabulary; V2's default for a missing / unknown value is "low" (V1: "medium"), a visible change only under the flag and only in `metadata.identified_products`.
11. `public_vision_products` copies the list, so `metadata.identified_products` is no longer the same list object as the `vision_products` argument (equal by value; no reader relies on identity; the W2-1 pins assert equality).
12. No `selected_category` reaches the camera compare in either state (no input; T23); the "when present" clause of the brief is therefore vacuous at B3.
13. Arabic transliteration quality, and whether the model keeps a Latin brand as printed, are unmeasured offline.
14. `OPENAI_MODEL_VISION` is UNKNOWN on `web` (R-A15): the V2 call shape is the same for every id (`token_limit_kwargs` chooses `max_tokens` / `max_completion_tokens`); structured outputs on a GPT-5 id are untested here.
15. The three fixed `test_camera_vision.py` nodes run in CI from this merge on; a later regression in the V1 path shows there instead of being deselected. `#89` drops from 11 to 8.
16. The route's exit-2 `error` copy for a `finish_reason=length` reply blames the photo ("try a clearer photo") for a token cap; the client copy is C1's.

## 10. Out of scope

Refusals and the camera pre-compare decision (B2: placeholder, same identity, category conflict, low confidence; the `action: "error"` refusal copy R-A6); the vision-category tie-break in `_resolve_pair_category` (B5); image selection, the KG identity check and `image_url` gating on identity confidence (B7 -- PLAN's "image_url for a camera product gated on identity confidence" is B7's, not in the orchestrator's B3 brief); `lang` on `/image/identify` and the T23 re-record (B8); the typed error classification and the provider seam (B10); any change to the V1 prompt, normaliser or kwargs; a `.env` or Railway change; the client; `metadata.result_status` (B1).

## 11. Open questions for the orchestrator

- Q1 (envelope on expiry): the spec maps a vision timeout to the EXISTING 503 `LLM_UNAVAILABLE` branch (build 3 renders the outage copy with a back button; no re-send of photos). The brief says "TIMEOUT / LLM_UNAVAILABLE": should the expiry instead raise a coded 503 `TIMEOUT` (build 3's camera then renders the tap-to-retry state, which re-sends the photos and re-spends a credit, the harm PLAN 0.2 names)? Default: LLM_UNAVAILABLE.
- Q2 (one photo, two products): follow the brief literally (one best per `image_index`, R6b) or keep both products when the request carries exactly ONE image? Default: literal; measured consequence in 9.3.
- Q3 (`is_product` false): drop (default, the brief's "a photo with no product candidate gives the existing ... shapes") or carry the best non-product candidate with `_is_product False` so B2 can refuse with `needs_identification` instead of the generic `need_second_product`?
- Q4 `_VISION_V2_MAX_TOKENS = 1000` (V1 500): accept, or another figure?
- Q5 (orchestrator gating): the twins are presence-gated on the V2 marker (`_is_product`), no second flag read; accept, or require a flag read in `structured_comparison_service` too (a mid-request flip could then split one request)?
- Q6 (wire hygiene): `public_vision_products` is unconditional (a no-op OFF, byte-identical; the W4-7 R5 `pop` precedent) -- accept, or gate it on the flag (then a mid-request flip can leak an internal key)?
- Q7 (CLAUDE.md conflict): H0 (#363) rewrites `CLAUDE.md:502` concurrently; GREEN applies its `:501-502` edits after rebasing onto a main that contains #363 -- confirm the order.
- Q8 should the identity dicts also carry `_vision_image_index` (pairing evidence for B2)? Default: the four named fields only.
- Q9 the `.pre_impl_failures.txt` header paragraph wording (3.5) and whether the PR body must quote the `[pyt]` pass line verbatim (default yes).
- Q10 should the per-call `[VISION_V2] candidates=...` INFO line stay once B1's per-compare telemetry line lands, or fold into it? Default: stay (it is the only vision-side counter).

Not done in this spec: the comm set was not run at base (the three-run cap; 1.10 names what was measured and 7.5 what GREEN runs base -> head -> base); the stream twin has no runtime row (R15 source pin only); the live model's structured-output behaviour, the Arabic transliteration and the 1-based `image_index` risk are canary items, not measurements; no scratch worktree was created and no file outside `.qa-s80/` was written in the worktree.
