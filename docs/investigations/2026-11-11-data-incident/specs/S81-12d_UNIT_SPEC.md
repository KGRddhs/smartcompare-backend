# S81-12d unit spec: OPENAI-EGRESS-STOP (a dark flag under which no OpenAI call leaves the process)

- Unit: S81-12d OPENAI-EGRESS-STOP (the main lane's "S81-12d OPENAI-DISPATCH-OFF", RB2-14 and RULINGS_ITEM26_S81_12 IT26-7; incident fact F3: the code still sends every compare and scan to OpenAI, which refuses it). Class FOCUS (R-12D-10): the privacy text will rest on it; the camera / compare credit and refund exits; the consent router.
- Flag ruling (R-12D-1): ONE new DARK flag `ENABLE_OPENAI_EGRESS_STOP` (the proposed name kept: it says what it stops, and no name in app/, scripts/, tests/ or CLAUDE.md at the base contains EGRESS_STOP, measured by `git grep`). Default OFF; read PER CALL with the house idiom `os.getenv("ENABLE_OPENAI_EGRESS_STOP", "false").strip().lower() in ("true", "1", "yes", "on")` as the ONLY statement of its predicate; any other value is OFF. Flag OFF byte-identical in every response, log line and recorder, pinned with the FULL configuration and call recorders (B1 rule). Nothing ships unflagged. Only the relay sets it, on the owner's yes, in its own window.
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-12d (detached, read-only for this round). Branch GREEN creates: fix/s81-12d-openai-egress-stop. RED files: tests/test_s81_s12d_openai_egress_stop.py and tests/test_s81_s12d_no_byte_e2e.py. Runner tags start with inc-12d-.
- Base sha 6b909e0a92067d6b3562eee325e4956c116441f7 (origin/main after #399 S81-04c; HEAD == base, measured 2026-11-12). `git status --short` EMPTY before every probe and after (this file is under the gitignored .qa-s80/; `git check-ignore -v` = .gitignore:72 `.qa-*/`).
- This round is READ-ONLY (H5 c): no pytest, jest, tsc or eslint ran; no scratch worktree. Every run is listed with its command and marked DEFERRED TO RED. Measurement location: <SP>/S81-12d/spec (base blobs via `git show`, one `git archive` copy of app/ tests/ scripts/ for the importer-closure count; all deleted at the end).
- Evidence: record/inc/S81_12D_BRIEF.md (R-12D-1..12, Q1..Q8); record/inc/S93_RULINGS_ITEM26_2026-11-12.md (IT26-1..9); record/inc/MON1_UNIT_SPEC.md (the dispatch census one merge earlier; re-measured here); record/inc/RULINGS_INC_R0.md; record/incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md (sections 1, 2, 4; "7, 10 and 6 calls per comparison, plus one moderation call"); record/s81/PLAN_S81.md; record/s80/PLAN_S80.md section 0 + contract_freeze.json (never a codeless 503); record/s81/ledger.md line 316 (the 2026-11-07 flag read of web and price-warmer).
- Sister units and contracts: MON1 (this lane, another branch, not on the base) hooks the same chokepoints: section 2.9 writes the contract for both merge orders. S81-04c (#399, merged into the base) owns the log statements of the eight LLMUnavailableError arms: this unit touches none of them and relies on them (Q4). S81-12 (#378, the legal branch) consumes the flag's ON date under path B (IT26-7); this unit edits no legal text and no processor row (R-12D-9). CL3 (client) disjoint.
- Personal-data rule: no personal value, no real credential shape, no key-value literal in any file; every synthetic credential is built at run time by concatenation; a digest constant's NAME avoids access/auth/api/credential/creds/key/password/secret/token; digests recorded as base64. Pure ASCII and LF in this file.
- Line references `file:N` are at 6b909e0a (`git show 6b909e0a:<file>`); resolve by symbol if they move.

## 0. What the unit does

Production calls OpenAI only (no ENABLE_ANTHROPIC_* role flag on web, H2), and OpenAI answers every call with HTTP 401 (the credential is revoked). So every text comparison (7 to 10 chat calls plus one moderation call), every camera scan and every link comparison still SENDS the user's content to a service that refuses it. This unit adds one dark flag. With it ON:

1. The ONE OpenAI chat chokepoint `api_budget_service.guarded_llm_create` raises a new typed refusal `OpenAIEgressStoppedError` (a subclass of the existing `LLMUnavailableError`) right after its local privacy prologue and BEFORE the spend admit, the breaker admission, the SDK call, the usage ledger and every record. All 15 routed sites reach OpenAI only through it.
2. The OpenAI moderation call in `content_safety_service.moderate_output` raises the same class inside its existing try, after the Claude branch and before the client is fetched; the existing arm fails OPEN exactly as it does today on the 401.
3. The two operator scripts that dispatch to OpenAI directly (scripts/seed_spec_spine.py, scripts/shadow_experiments.py) stop the same way (part B; open question OQ-1 may drop it).
4. One WARNING line per process per surface says the stop is active; nothing logs at ERROR and nothing raises a Sentry event because of a stop.

Every entry answers what it answers today with the rejected credential (measured in 1.6 / Q2): the text comparison and its stream deliver the same deterministic result; the link comparison the same coded 503 LLM_UNAVAILABLE; the camera, the ONE ruled exception (R-12D-3), the existing coded 503 LLM_UNAVAILABLE instead of today's 500 SERVER_ERROR, with the same two refunds. With the flag OFF nothing changes (one extra getenv per dispatch). A Claude-routed call is untouched.

Nothing in this file says a production problem is fixed. A merged S81-12d is "merged, NOT yet proven" until section 8b is run on production by the relay with the owner; the ON date is the date a legal text may carry (IT26-7).

## 1. Base state (measured at 6b909e0a)

### 1.1 The chat chokepoint (app/services/api_budget_service.py, 1360 lines, i/lf w/crlf)

| What | Where | Measured fact |
|---|---|---|
| Module imports | :6-21 | stdlib + cache_service + openai_pricing.record_openai_response (:17) + `llm_spend_breaker as _llm_spend_breaker` (:21); `logger` :23. |
| `_LLM_PREFLIGHT_FLAG` | :696 | "ENABLE_LLM_PREFLIGHT_BREAKER"; NOT in the ON list of the 2026-11-07 web read (ledger line 316): production runs the flag-OFF branch. |
| `LLMUnavailableError(RuntimeError)` | :706-713 | docstring: the message avoids the substrings "429" / "rate" / "quota" that `generate_comparison` keys its fallback on. Subclasses at the base: llm_router.py:235-269 (ConsentUpdateRequiredError, AnthropicNotConfiguredError, AnthropicShapeError, AnthropicDispatchError, AnthropicRefusalError, AnthropicBreakerOpenError). |
| `llm_preflight_breaker_enabled` | :716-721 | the reader idiom (default "" there; the house idiom with "false" is llm_router._on :312-313). |
| Census comment | :938-956 | 13 wired dispatches; content_safety moderation named NOT WIRED to the breaker. |
| `guarded_llm_create(client, **kwargs)` | :957-1056 | docstring :958-990; privacy prologue :991 `kwargs["store"] = False`, :992 `eb = kwargs.get("extra_body")`, :993-994 the extra_body scrub; :995 `spend_ticket = None`; :996-1000 spend admit under `_llm_spend_breaker.spend_breaker_enabled()`; :1001 `if not llm_preflight_breaker_enabled():` :1002 `response = await client.chat.completions.create(**kwargs)` (no try), :1003 record_openai_response, :1004-1005 spend record, :1006 return; flag ON :1007-1011 admission (a denial raises LLMUnavailableError), :1012-1013 try/create, :1014-1050 the three arms, :1051-1056 the success tail. |
| Where the stop goes | between :994 and :995 | after the prologue (U3c requires `kwargs["store"] = False` as statement 1: test_u3c_store_false_pin.py:298-312) and before the spend admit (R-12D-5). The prologue writes only the local kwargs dict: no I/O. |

### 1.2 The router (app/services/llm_router.py, 1217 lines) - NOT edited

| What | Where | Measured fact |
|---|---|---|
| ROLE_FLAGS / PRE_V3_FLAG | :53-59, :61 | none set on web (H2). |
| `decide(role)` | :345-357 | role OFF -> "openai" (the only read); ON: consent >= 3 -> "anthropic"; else "openai" while ENABLE_OPENAI_PRE_V3 is ON, else "refuse". |
| `route(site, dispatch, client, **kwargs)` | :1086-1123 | role OFF -> `return await dispatch(client, **kwargs)` :1089-1090 (dispatch = guarded_llm_create at all 15 sites); decision "openai" -> the same :1092-1093; "refuse" -> ConsentUpdateRequiredError :1094-1100; else Claude through `_dispatch_claude`, escalation only to Claude (:1101-1123). NO path falls back from Anthropic to OpenAI (every except arm in route re-raises or returns a Claude result). |
| `decide_moderation` / `moderate_with_claude` | :1129-1135, :1184-1217 | Claude moderation through guarded_anthropic_create (:1144); fails CLOSED. |

### 1.3 The moderation arm (app/services/content_safety_service.py, 295 lines, i/lf w/crlf; module top imports stdlib only, :12-18)

`moderate_output` :234-270: empty text -> allowed :244-245; QA sentinel :246; `try:` :247; `from app.services import llm_router as _llm_router` :251; `if _llm_router.decide_moderation() == "anthropic":` :252-254 (Claude, returns); inline imports :255-257 (`moderation_model`, `openai_service.get_client`); `client = get_client()` :258; `resp = await client.moderations.create(model=moderation_model(), input=text)` :259; flagged branch :260-267; `except Exception as e:` :268 -> `logger.warning("[content_safety] L3 moderation API failed (fail-open): %s", e)` :269; `return SafetyResult(allowed=True)` :270. The stop goes between :254 and :255. Callers: structured_comparison_service.py:4860 (sync L3), :5762 (stream L3), image_routes.py:457 through moderate_vision_output :272-284 (L4).

### 1.4 THE EGRESS CENSUS (Q1): every statement in app/ and scripts/ that can send a request to an OpenAI host

Method: `git grep` at the base over app/ and scripts/ for `chat.completions`, `moderations.`, `embeddings.`, `.responses.`, `.images.`, `.files.`, `.batches.`, `.audio.`, `models.retrieve`, `models.list`, `AsyncOpenAI`, `OpenAI(`, `api.openai.com`, the `/v1/<surface>` paths and `base_url`; then the import closure of every script a Railway service starts (railway*.json startCommand).

| # | Statement | Where | Process | Reached through | Gating | Production today |
|---|---|---|---|---|---|---|
| C1 | `await client.chat.completions.create(**kwargs)` | api_budget_service.py:1002 | web; price-warmer; in-process scripts | the 15 routed sites (1.5) | ENABLE_LLM_PREFLIGHT_BREAKER OFF branch | YES (every compare, scan, link) |
| C2 | the same | api_budget_service.py:1013 | same | same | the ON branch | no (flag OFF on web) |
| C3 | `await client.moderations.create(...)` | content_safety_service.py:259 | web; price-warmer | L3 sync / stream, L4 camera | role moderation OFF | YES (one per text compare; L4 only after a successful vision call) |
| C4 | `await get_client().chat.completions.create(...)` | scripts/seed_spec_spine.py:381 (`extract_spine_specs` :362, its try :380, the create :381) | operator-run only (no railway*.json starts it) | direct, NOT through C1 | `--dry-run` / no key | no service |
| C5 | `await client.chat.completions.create(**kwargs)` | scripts/shadow_experiments.py:999 (`_create_with_retry` :989-1015, retries only on 429 / "rate limit") | operator-run only | direct, NOT through C1 | none | no service |

Clients (construction only, no network): openai 3.3.1 `AsyncOpenAI.__init__` (`openai/_client.py:836-1012`) reads env and builds an httpx2 client; workload identity only when passed. Constructions: openai_service.py:38 (module singleton at import) and :50-65 `get_client`; extraction_service.py:67-90; url_extraction_service.py:34-47. `client.with_options(...)` (extraction_service.py:2739) only re-wraps a client handed to C1. No embeddings, files, responses, images, audio, batches or models call reaches OpenAI anywhere: the `messages.batches.*` calls of scripts/cron_compare_judge.py and scripts/seed_kb_batch.py and `messages.create` at cron_compare_judge.py:684 are the anthropic SDK with `lr.ANTHROPIC_BASE_URL` (cron_compare_judge.py:28 "never calls OpenAI"). No raw HTTP to an OpenAI host: the only literals are llm_provider.py:73 (STOCK_OPENAI_BASE_URL, passed as base_url), processors.json:70 and sentry_service.py:198 (a scrub list).

`OPENAI_BASE_URL` (llm_provider.py:69-190): every client takes `base_url=provider_base_url()`, so an operator could point the SDK at another OpenAI-compatible host. The stop applies to C1 / C3 whatever the base URL (stated limit L5; OQ-3).

Railway services and whether their process can reach C1 / C3:

| Config | startCommand | Reaches C1 / C3? | How measured |
|---|---|---|---|
| railway.json (web) | uvicorn app.main:app | YES | the routes of 1.6 |
| railway.warmer.json (price-warmer) | python -m scripts.cron_warm_price_cache | YES once ENABLE_PRICE_CACHE_WARMER is ON (`_warm_one` :218-257 awaits `compare_from_text`) | ledger line 316: ENABLE_PRICE_CACHE_WARMER=false on price-warmer, and `main()` :260-266 returns before any work: no OpenAI traffic today |
| railway.judge.json, railway.kbseed.json | cron_compare_judge, seed_kb_batch | NO: anthropic SDK only; api_budget_service is imported for LLMUnavailableError only | read |
| railway.feedwalker.json, railway.pdpdiscovery.json, railway.kbenrich.json | cron_feed_walker, cron_pdp_discovery, cron_kb_enrich | NO: pure helpers only (feed walker: parse_money, extract_size_ml_any, ...; pdp: normalize_words + sitemap helpers; kb_enrich: price_service.extract_price_from_html, a SYNC function :13927-14286 whose calls are BeautifulSoup / JSON-LD parsers) | the AST call list of extract_price_from_html; the `ps.` / `ws.` / `sds.` names each script uses |
| railway.robots.json, railway.kbcoverage.json, railway.learning.json | robots registry, kb coverage, learning | NO (no OpenAI-reaching import) | grep |

Operator-run scripts reaching C1 in process (no service): measure_warmed_kpi.py:34, warm_kpi_truth.py:44, seed_zyte_luxury.py:164 (parse_product_query), shadow_experiments.py:1376 / :1574 (get_client, then C5), seed_spec_spine.py:376 (C4). eval_runner.py, review_warmup.py, verify_after_credits.py, bias_matrix_probe.py and bundle_d_prod_smoke.py call the backend over HTTP (their OpenAI traffic is the web process's).

### 1.5 The 15 routed sites (all `_llm_router.route(<key>, _llm_breaker.guarded_llm_create, client, ...)`; G13_SITE_KEYS, test_s81_s06_router_gate_rows.py:787-803)

| Key | Where | The arm that catches a dispatch error (role flags OFF) | Returned / logged today on the 401 |
|---|---|---|---|
| classify | extraction_service.py:1404 | :1417-1420 | "other"; WARNING with the exception text |
| parse | :1544 | :1570-1581 (S81-04c) | {"products": [], "error": PARSE_PRODUCT_QUERY_ERROR}; ERROR + exc_info for a non-class exception |
| specs | :1611 | :1742-1747 (S81-04c) | {"brand","model","error": str(e)}; ERROR exc_summary |
| price | :1773 | :1797-1802 (S81-04c) | {"amount": None, "currency", "error": str(e)}; ERROR |
| price_training | :1825 | :1855-1860 (S81-04c) | the same shape; ERROR |
| reviews | :1890 | :1915-1920 (S81-04c) | {"average_rating": None, "error": REVIEWS_EXTRACTION_ERROR}; ERROR + exc_info |
| verdict / verdict_fallback | :2696 / :2738 | the fallback test :2714-2752 (fires only on "429" / "rate" / "quota" in str(e)); outer arm :2827-2840 (S81-04c) | {"winner_index": 0, "error": COMPARISON_GENERATION_ERROR}; ERROR + exc_info |
| image_tier3 | image_service.py:187 | :195-197 | None; WARNING %r |
| vision_v1 / vision_v2 | openai_service.py:649 / :477 | none: propagates to image_routes.py:390-417 | see 1.6 E3 |
| specs_targeted / specs_synthesized | openai_service.py:768 / :843 | :787-789 / :860-862 | {}; WARNING with text |
| disambiguate | openai_service.py:905 (caller price_service.py:9173) | :954-956 | {"distinct_product": "unknown", "confidence": "low", "cost": 0.0}; WARNING with text |
| url_extract | url_extraction_service.py:960 | :983-998 (S81-04c) | {"error": str(e)}; ERROR by type |

Role flags OFF, every arm returns the SAME value for an AuthenticationError and for an LLMUnavailableError subclass except where the value embeds str(e) (specs, price, price_training, url_extract); the S81-04c arms differ only in the log record (WARNING by type for the class vs ERROR for any other exception).

### 1.6 THE DELIVERY TABLE (Q2; role flags OFF = production; (a) today's AuthenticationError 401, (b) an LLMUnavailableError subclass raised at the chokepoint)

| Entry | (a) today, the 401 | (b) the stop class | Pinned today by |
|---|---|---|---|
| E1 POST / GET /api/v1/text/compare (text_routes.py:673 / :891) | every site arm swallows (1.5); moderation fails open (1.3); 200 success with the deterministic scores, no AI text (incident section 1); credit consumed, no refund; history row + share as for any success; the arms log ERROR (parse, specs, price x2, reviews, verdict) = Sentry events | the SAME body except the text of the str(e)-carrying error values; the S81-04c arms log ONE WARNING by type, so no Sentry event | tests/test_w49_extraction_catch_redaction.py r2c / r2e rows (:334-545: every OpenAI call failing on the phone path; extract_specs / extract_price did NOT surface in the body, measured there at b63a8368); test_s81_s04c_refusal_log_hygiene.py P2 (:736-756) |
| E2 GET /api/v1/text/compare/stream (:1097) | the same arms; the same events (build 3 and the OTA use REST only, contract_freeze) | the same | test_w49 r2c SSE rows (:411) |
| E3 POST /api/v1/image/identify (image_routes.py:205) | identify_products (v1 :571-705; v2 :459-570 when ENABLE_VISION_IDENTITY_V2, OFF on web) does not catch it; arm :390-417: `logger.error(f"[IMAGE] Vision call failed: {e}")`, `_refund_reserved_credit("usage_refund.image.vision_exception")` + `_refund_anon_credit(...)`, then NOT transient (401) -> HTTPException(500, "Image analysis failed. Please try again.") -> error_handler.py:172-250 = {success: false, error: <that literal>, code: "SERVER_ERROR", request_id}; a Sentry event (5xx minus 503) | arm :395-398 logs WARNING "[IMAGE] Vision call failed: <TypeName>"; the SAME two refund calls; :412 `isinstance(e, LLMUnavailableError)` -> HTTPException(503, {code: "LLM_UNAVAILABLE", error: LLM_UNAVAILABLE_FRIENDLY_MESSAGE}) = the existing coded refusal (THE RULED EXCEPTION, R-12D-3); no Sentry event (503 excluded, no ERROR record) | test_s81_s04c P4 (:795-811: one consume, one refund, label vision_exception; 503 LLM_UNAVAILABLE for the class, 500 + the literal for a RuntimeError), P5 (:814-827 anon refund); test_image_identify_llm_unavailable_s69.py:233; test_paid_route_metering.py vision_raised_500; test_security_regression.py:235-240 (source literal) |
| E4 POST / GET /api/v1/url/compare (url_routes.py:508 / :561) | extract_with_ai (only when structured data is short) returns {"error": str(e)} merged into raw_data (normalize_product_data copies no "error" key); generate_comparison returns the failure dict; url_extraction_service.py:1487-1495 returns {success: false, code: "LLM_UNAVAILABLE", error: <friendly>}; the route raises the coded 503 and refunds once (incident: "POST /url/compare 503 on 11-09 / 11-10") | the SAME | test_s80_url_mode_v2.py LLM_UNAVAILABLE rows; test_s81_s04c P2 (url_extract arm) |
| E5 POST /text/quick, GET /text/prices/{product} (admin key), GET /text/price-kpi, GET /text/parse (admin) | the same arms; /parse returns {"query", "parsed": {"products": [], "error": PARSE_PRODUCT_QUERY_ERROR}} | the SAME | test_w49 04 rows (parse constant) |
| E6 price-warmer `_warm_one` | compare_from_text as E1; NOT RUN today (flag false) | the SAME tally | tests/test_cron_warm_price_cache.py (by name; which rows NOT VERIFIED) |
| E7 scripts C4 / C5 | C4: WARNING "seed extraction failed ..." and {} per fragrance; C5: AuthenticationError re-raised (not a rate error) | C4: the SAME ({}); C5: the class re-raised, no retry, no sleep | test_spec_spine_d2.py, test_shadow_experiments.py (fakes only) |

Cache: every cache / L2 write in the compare path keys on the TRUTHINESS of an "error" value (e.g. structured_comparison_service.py:6905 specs cache + save_specs only when `not specs.get("error")`), so (a) and (b) take the same branch. Credit / refund: no exit distinguishes the two classes except the camera (:412). Moderation: allowed=True in both. NOT VERIFIED in this round (DEFERRED TO RED, rows E01-E07): the full body equality per entry; the RED pair rows measure it with the error texts normalised.

### 1.7 Libraries on the pinned venv (C:/Users/SynAckITPC/Documents/AI/.venv-qaren; read, not run)

- openai 3.3.1 (openai-3.3.1.dist-info), transport httpx2 2.12.0: `AsyncAPIClient._send_request` ends in `return await self._client.send(request, stream=stream, **kwargs)` (openai/_base_client.py:1624-1631); `self._client` is `AsyncHttpxClientWrapper` (:1517) <- `_DefaultAsyncHttpxClient(httpx2.AsyncClient)` (:1470), neither overrides `send`, so a class-level patch of `httpx2.AsyncClient.send` (httpx2/_client.py:1787) sees EVERY OpenAI SDK request (the transport recorder of section 5). A 401 response makes the SDK raise `openai.AuthenticationError` with no retry (`_should_retry` :825 retries 408 / 409 / 429 / 5xx only, read). The U3c test already drives the pinned SDK through `httpx2.MockTransport` (test_u3c_store_false_pin.py:610-640): the precedent.
- anthropic 1.12.1, httpx 0.28.1, sentry-sdk 2.68.1: unchanged, not imported by the new code.
- No new dependency. The new code is stdlib (os, logging) inside existing modules.

### 1.8 Guards the new code must not trip (each read at the base)

| Guard | Where | Rule the new code follows |
|---|---|---|
| U3c statement 1 | test_u3c_store_false_pin.py:298-312 | `kwargs["store"] = False` stays the FIRST statement; exactly one store write; the stop comes AFTER the prologue. |
| U3c kwargs discipline | :315-347, :350-377 | the stop call takes a string literal only; it never names `kwargs`; exactly two `create(**kwargs)` dispatches remain. |
| U3c no dispatch outside the chokepoint / scripts store | :380-421, :461-517 | no new create call; the script stops sit AFTER each function's store write (C5) or inside the try before the call (C4: store=False stays a keyword). |
| K1 AST digest | test_s81_s03_llm_ledger_v2.py:193, :2484-2492 | MOVES deliberately: E1 (4.1). |
| S81-04 R37 | test_s81_s04_spend_breaker.py:1619-1650 | exactly one spend_breaker_enabled call, one admit, two record_openai_response_soon, admit before `_openai_dispatch_admission`: unchanged (the stop calls none of them). |
| S81-06 G13 / R38 / R39b | test_s81_s06_router_gate_rows.py:747-840; test_s81_s06_anthropic_router.py:2476-2553 | no new guarded_llm_create call, no router edit; `decide_moderation()` stays before `moderations.create` in moderate_output (the stop sits between them). |
| Model-id literal ban / M1 | test_model_config.py:125-150; test_model_config_enforced.py:116-160 | no model literal; no new chat site. |
| U8d R8 ERROR-line AST | test_sentry_channels_u8d_unit.py:773-919 | WARNING only; no logger.error / exception / critical. |
| Legal service scanner | test_legal_docs_u8.py:819-857 | no URL literal, no client constructor added under app/services. |
| processors.json OpenAI row | app/legal/processors.json:56-72; tests/fixtures/legal_s78.json:283; test_s81_s22b_self_critique_retire.py:93 | untouched (gate_flag stays null, module list unchanged): R-12D-9. |
| S81-04c arm shape | test_s81_s04c_refusal_log_hygiene.py P1-P6 | the arms are not edited; a subclass prints its own name (R3 :543). |
| Verdict fallback matcher | extraction_service.py:2718-2722 | the stop message contains none of "429", "rate", "quota" (lower-cased), nor "rate limit" / "ratelimit" (shadow_experiments.py:1003-1004). |
| Line endings | `git ls-files --eol`: api_budget_service.py, content_safety_service.py, seed_spec_spine.py, shadow_experiments.py, CLAUDE.md all `i/lf w/crlf` | the Edit tool keeps CRLF; a whole-file diff is a defect; new test files LF in the index. |

### 1.9 Production flag state used here (ledger line 316, the 2026-11-07 read; H2)

No ENABLE_ANTHROPIC_* role flag, no ENABLE_OPENAI_PRE_V3, no ENABLE_LLM_PREFLIGHT_BREAKER, no ENABLE_LLM_SPEND_BREAKER, no ENABLE_VISION_IDENTITY_V2, no ENABLE_URL_MODE_V2 on web; ENABLE_CAMERA_FAILURE_ENVELOPE, ENABLE_PAID_ROUTE_METERING and ENABLE_COMPARE_AUTH_REQUIRED ON; ENABLE_LLM_LEDGER_V2 ON since 2026-11-11 (H2); price-warmer ENABLE_PRICE_CACHE_WARMER=false. The design holds for every state of these flags (section 2.6 failure table); the hermetic rows run the production state AND the full configuration.

### 1.10 Base pass state of the touched files (ALL DEFERRED TO RED: this round ran no test)

Runner prefix (P): `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound <s> --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-12d --log <SP>/S81-12d/red/<tag>.log --tag <tag> --`

| Gate | Command | State |
|---|---|---|
| B1 the chokepoint + moderation readers | P --bound 1200 --tag inc-12d-base-direct -- tests/test_api_budget_service.py tests/test_openai_breaker.py tests/test_retro_w1_3.py tests/test_m13_31_half_open_probe.py tests/test_s81_s04_spend_breaker.py tests/test_s81_s03_llm_ledger_v2.py tests/test_u3c_store_false_pin.py tests/test_content_safety_service.py tests/test_cost_meter_s74.py tests/test_model_config_enforced.py | DEFERRED TO RED |
| B2 router, S81-04c, camera, text, url | P --bound 1200 --tag inc-12d-base-route -- tests/test_s81_s06_anthropic_router.py tests/test_s81_s06_router_gate_rows.py tests/test_s81_s04c_refusal_log_hygiene.py tests/test_image_identify_llm_unavailable_s69.py tests/test_m13_26_image_error_envelope.py tests/test_paid_route_metering.py tests/test_w49_extraction_catch_redaction.py tests/test_text_error_envelope_no_raw_exception.py tests/test_s80_url_mode_v2.py tests/test_s80_b3_vision_identity_v2.py | DEFERRED TO RED |
| B3 scripts + scanners | P --bound 1200 --tag inc-12d-base-scan -- tests/test_spec_spine_d2.py tests/test_shadow_experiments.py tests/test_tradeoffs_dedup_parity.py tests/test_cron_warm_price_cache.py tests/test_model_config.py tests/test_prompt_fence.py tests/test_migration_index_predicate_immutability.py tests/test_openai_key_log_hygiene_s69.py tests/test_sentry_channels_u8d_unit.py tests/test_legal_docs_u8.py tests/test_security_regression.py tests/test_start_command.py | DEFERRED TO RED |
| B4 the CLAUDE.md readers (by the import graph) | P --bound 1200 --tag inc-12d-base-claude -- tests/test_ci_gates.py tests/test_behavior_dimension_translation.py tests/test_s81_s04_spend_breaker.py tests/test_s81_s08b_legacy_fingerprint.py tests/test_s81_s08b_gate_rows.py tests/test_s81_s23_bypass_retire.py | DEFERRED TO RED |
| B5 the RED files at base (must fail on AssertionError only; PIN rows green) | P --bound 600 --tag inc-12d-red-base -- tests/test_s81_s12d_openai_egress_stop.py tests/test_s81_s12d_no_byte_e2e.py | DEFERRED TO RED |
| B6 the comm-set base record (7.2) | chunks of <= 25 files, bound 1200, tags inc-12d-base-cNN | DEFERRED TO RED |

No stored base record exists for 6b909e0a (harness/base_records/ holds a74caba7 and older). The a74caba7 record 0a224f48... is NOT reusable for app.main / TestClient users or for the importers of extraction_service / image_routes / url_extraction_service (#399 edited them); per-file reuse (GC-9) only for members that reference none of those and are no glob walkers. Known base noise: tests/test_prompt_truth.py two ERROR nodes (cold tiktoken); tests/test_s80_url_mode_v2.py::test_deadline_yields_timeout_503[POST] a wall-clock flake under load.

## 2. Contract

### 2.1 Flags and knobs

| Name | Type | Default | Reader | Read when |
|---|---|---|---|---|
| ENABLE_OPENAI_EGRESS_STOP | bool flag (house idiom) | OFF (unset, "", "false", "0", "no", "off", any other value) | `api_budget_service.openai_egress_stop_enabled()` | per call, as the first statement of `stop_openai_egress_if_enabled`, at every C1 / C2 / C3 / C4 / C5 dispatch attempt; never at import |

No knob. No new credential name (CREDENTIALS_UNSET unchanged). The flag is not read by the router, the routes, /health or any client.

### 2.2 New symbols in app/services/api_budget_service.py (placed after `llm_preflight_breaker_enabled`, :716-721)

```python
# S81-12d OPENAI-EGRESS-STOP (ENABLE_OPENAI_EGRESS_STOP, default OFF, read per call).
_OPENAI_EGRESS_STOP_FLAG = "ENABLE_OPENAI_EGRESS_STOP"
OPENAI_EGRESS_STOP_MESSAGE = "openai dispatch stopped locally (ENABLE_OPENAI_EGRESS_STOP)"
OPENAI_EGRESS_STOP_LOG = "[OPENAI_EGRESS] dispatch stopped locally surface=%s (logged once per process per surface)"
OPENAI_EGRESS_SURFACES = ("chat_completions", "moderations", "script")
_openai_egress_stop_logged: set = set()


class OpenAIEgressStoppedError(LLMUnavailableError):
    """S81-12d: raised INSTEAD of an OpenAI dispatch while ENABLE_OPENAI_EGRESS_STOP is
    ON, before any network activity, spend admit, breaker admission or record. An
    LLMUnavailableError, so every arm that already distinguishes the class (the
    camera's coded 503, the S81-04c WARNING-by-type arms, the S81-06 role-ON
    non-deliveries) treats it as a typed refusal. The message carries none of the
    words the verdict fallback matcher keys on ("429" / "rate" / "quota")."""


def openai_egress_stop_enabled() -> bool:
    return os.getenv(_OPENAI_EGRESS_STOP_FLAG, "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def stop_openai_egress_if_enabled(surface: str) -> None:
    """Flag OFF: one getenv, returns None (nothing else read, logged or raised).
    Flag ON: one WARNING per process per surface, then OpenAIEgressStoppedError."""
    if not openai_egress_stop_enabled():
        return
    if surface not in _openai_egress_stop_logged:
        _openai_egress_stop_logged.add(surface)
        logger.warning(OPENAI_EGRESS_STOP_LOG, surface)
    raise OpenAIEgressStoppedError(OPENAI_EGRESS_STOP_MESSAGE)


def _reset_openai_egress_stop_state() -> None:
    """Test seam: forget the once-per-process log latch."""
    _openai_egress_stop_logged.clear()
```

Checks on these literals (made by reading): the message lower-cased contains no "429", "rate", "quota", "rate limit", "ratelimit"; no name contains a gitleaks keyword; ASCII only. The latch is a plain set: two threads racing the first stop may each log once (at most one extra line per surface per process; stated limit L3); the raise is unconditional.

### 2.3 The hooks (exact statements GREEN inserts; nothing else in the functions changes)

H1 `guarded_llm_create` (api_budget_service.py), between :994 and :995, at the function's top level:
```python
    # S81-12d (ENABLE_OPENAI_EGRESS_STOP, read per call): ON, the call stops HERE,
    # after the local privacy prologue and before the spend admit, the W1-3
    # admission, the dispatch and every record (R-12D-5). OFF: one getenv.
    stop_openai_egress_if_enabled("chat_completions")
```
H2 `ContentSafetyService.moderate_output` (content_safety_service.py), inside the try, between :254 and :255:
```python
            # S81-12d: ON, the OpenAI moderation call is not made; the arm below fails
            # OPEN exactly as on today's 401. The Claude branch above is untouched.
            from app.services import api_budget_service as _abs
            _abs.stop_openai_egress_if_enabled("moderations")
```
H3 (part B) scripts/seed_spec_spine.py `extract_spine_specs`, inside the try (:380), before :381 (the existing `except Exception as exc` :397 logs WARNING and returns {}):
```python
        from app.services import api_budget_service as _abs
        _abs.stop_openai_egress_if_enabled("script")
```
H4 (part B) scripts/shadow_experiments.py `_create_with_retry`, after `kwargs["store"] = False` (:994) and before `delay = 2.0`:
```python
    from app.services import api_budget_service as _abs
    _abs.stop_openai_egress_if_enabled("script")
```

Order inside H1 (R-12D-5, proven by rows S12D-03 / S12D-04): prologue (local dict writes) -> STOP -> [never reached while ON: `spend_breaker_enabled()` read, `admit_openai_dispatch`, `llm_preflight_breaker_enabled()` read, `_openai_dispatch_admission`, the create, `record_openai_response`, `record_openai_response_soon`, `openai_record_failure` / `openai_record_success` / `openai_release_half_open_probe`]. No retry is possible: the SDK is never called; the verdict fallback (:2718-2722) does not fire because the message carries none of its words, and if it did its route call would stop again at H1 (row S12D-15 pins exactly ONE stop per verdict call).

Order inside H2: the QA sentinel and the empty-text exits unchanged -> `decide_moderation()` (a role-ON "refuse" raises ConsentUpdateRequiredError as at base; "anthropic" returns through Claude as at base) -> STOP -> [never reached while ON: `moderation_model()`, `get_client()`, `moderations.create`].

### 2.4 Log lines and events

| Line | Level | Where | When | Fields |
|---|---|---|---|---|
| `[OPENAI_EGRESS] dispatch stopped locally surface=%s (logged once per process per surface)` | WARNING | api_budget_service logger | the first stop of each surface in a process (closed set chat_completions / moderations / script) | the surface literal only |
| `<prefix>: OpenAIEgressStoppedError` (the eight S81-04c arms: "Product parsing error", "Specs extraction error", "Price extraction error", "Price fallback error", "Reviews extraction error", "Comparison generation error", "[IMAGE] Vision call failed", "AI extraction error") | WARNING | unchanged statements | every stopped call that reaches them (Q4) | the type name only |
| the other arms (classify :1420, [EXTRACT_TARGETED] / [EXTRACT_SYNTH] / [VARHINT], [image] Tier 3 %r, [content_safety] L3 ... (fail-open): %s, the seed / shadow lines) | WARNING (unchanged) | unchanged statements | every stopped call that reaches them | the exception text = OPENAI_EGRESS_STOP_MESSAGE (a constant: no user content, no key, no URL) |

No ERROR record and no Sentry event is caused by a stop (R-12D-7): the new line is WARNING; LoggingIntegration(level=logging.ERROR) (sentry_service.py:738) makes no event or breadcrumb from WARNING; the camera's 503 is excluded from failed_request_status_codes (sentry_service.py:724-733). No new /health key, no new response key, no new error code, no new copy, no new event type.

### 2.5 Contract freeze (PLAN_S80 section 0, contract_freeze.json)

Additive only: no response key is added, removed, renamed or retyped in any state. The one status change under the flag (camera 500 SERVER_ERROR -> 503 LLM_UNAVAILABLE) uses an envelope both live bundles already render (failureClassification.ts:79-94 at 683f56c0 and f1e20c39: CAMERA_ENGINE_OUTAGE_CODES = {LLM_UNAVAILABLE, INTERNAL_ERROR, SERVER_ERROR}), carries an explicit code (never a bare 503: the error-handler mapping would otherwise turn it into FEATURE_DISABLED, error_handler.py:34) and keeps the existing refunds. No client change.

### 2.6 Failure table (flag ON unless said)

| Situation | Outcome |
|---|---|
| Every role flag OFF (production) | every C1 / C3 attempt stops; each entry answers as in 1.6 column (b); zero OpenAI requests. |
| A role flag ON, consent >= 3 (decision anthropic) | untouched: guarded_anthropic_create runs; H1 is never reached for that site (route returns the Claude result); no stop line for it. |
| A role flag ON, consent < 3, ENABLE_OPENAI_PRE_V3 ON (decision openai) | H1 stops; the class is an LLMUnavailableError, so the S81-06 role-ON arms treat it as their typed non-delivery: the verdict re-raises -> the text compare answers the coded LLM_UNAVAILABLE envelope (refund on the existing path), url_extract re-raises -> the coded URL result, the camera the coded 503. This DIFFERS from that configuration with a working-but-401 OpenAI (an AuthenticationError is swallowed into a deterministic result): stated limit L1; it matches what ENABLE_OPENAI_PRE_V3 OFF delivers for such a client, but mid-pipeline instead of at the entry (no entry refusal is added: R-12D-3). |
| A role flag ON, consent < 3, ENABLE_OPENAI_PRE_V3 OFF | unchanged: the router refuses before any dispatch (ConsentUpdateRequiredError); H1 not reached. |
| Moderation role ON (Claude) | untouched (H2 sits after the Claude branch). |
| ENABLE_LLM_PREFLIGHT_BREAKER ON | H1 precedes the branch: no admission, no probe slot taken, no record; a stop can never trip or close the breaker. |
| ENABLE_LLM_SPEND_BREAKER ON | H1 precedes the admit: no reservation, no record, no Redis command. |
| ENABLE_LLM_LEDGER_V2 ON (production) | record_openai_response is never called for a stopped call: the saved rows show zero OpenAI calls and zero cost, as they do today (a raising create records nothing). |
| OPENAI_API_KEY unset or blank | not this unit's lever (R-12D-4). The sites still call get_client() before route(); extraction_service.get_client passes api_key=None and the SDK raises OpenAIError at construction BEFORE H1 (an OpenAIError is not the class: today's arms take it as a non-class exception). Stated limit L4. |
| OPENAI_BASE_URL set to another OpenAI-compatible host | the stop still applies (H1 / H2 are host-blind). Stated limit L5. |
| Flag value garbage / padded / upper case | per the idiom: " TRUE " and "On" are ON; "truthy", "2", "enabled" are OFF. |
| Two concurrent first stops on one surface | the latch may log twice; behaviour identical (L3). |

### 2.7 The flag-OFF identity and the EXACT deploy-visible delta (the main invariant)

Flag OFF (unset or any non-ON value), with every other flag in any state: every response body, status, header, SSE event, saved row, cache write, credit / refund call, breaker / spend / ledger record, outbound request (count, order, host, path, body) and log record is byte-identical to the base. The ONLY runtime difference is one `os.getenv` per C1 / C2 / C3 attempt (and per C4 / C5 call in the scripts). Pinned by S12D-12, S12D-13, S12D-19, E08 under the FULL configuration with the call and transport recorders.

Deploy-visible delta with every flag at its default (the merge itself): NOTHING a user, the client, /health, Sentry or the deploy log can see. Code-level: the K1 AST digest of guarded_llm_create changes (E1); the CLAUDE.md block is added; two operator scripts gain a no-op-when-OFF call. Production changes only when the relay sets the flag (section 8).

### 2.8 Test seams (production values in brackets)

- `api_budget_service._reset_openai_egress_stop_state()` [never called in production]: clears the latch; the RED files call it in an autouse fixture (no conftest edit).
- The transport recorder: a class-level monkeypatch of `httpx2.AsyncClient.send` (and, belt and braces, `httpx2.Client.send`, `httpx.AsyncClient.send`, `socket.getaddrinfo` / `socket.socket.connect` for the host api.openai.com) [the real network]. Flag OFF it answers an OpenAI request with `httpx2.Response(401, json={"error": {"message": <synthetic constant>, "type": "invalid_request_error", "code": "invalid_api_key"}}, request=request)` so the pinned SDK raises the same AuthenticationError production sees; flag ON any OpenAI request FAILS the test.
- Synthetic credentials [the owner's variables]: OPENAI_API_KEY is the conftest placeholder (tests/_env_safety.py:156, CREDENTIAL_PLACEHOLDERS) or a value built at run time ("test" + "-" + "z" * 24); ANTHROPIC_API_KEY (in CREDENTIALS_UNSET, :142) is built at run time and set with monkeypatch AFTER importing app.main (the DOTENV GUARD HAZARD). No credential shape is written into a file.
- The clients: the real `openai_service.get_client` / `extraction_service.get_client` / `url_extraction_service.get_client` memo slots are reset per test (monkeypatch of `_client_cache`, `_client`) and `openai_service.client` is replaced by a fresh real AsyncOpenAI built under the synthetic key [the production singletons].

### 2.9 The MON1 contract (R-12D-6; MON1 is on another branch and NOT on the base; this unit is correct without it)

What MON1's final round must honour (its spec: record/inc/MON1_UNIT_SPEC.md 2.3 hooks H1-H8, 2.9 the active check, 2.6 the monitor path):
- M-1 A stopped dispatch records NEITHER `rejected` NOR `ok`. Structurally true at H1 / H2 of this unit: the stop raises BEFORE MON1's H1-H4 (inside / after the create) and before MON1's H7 (after moderations.create). MON1's H8 (the moderation except arm :268) DOES see the stop exception: its classifier must return None for it (it does by construction, OpenAIEgressStoppedError is no SDK class) and a MON1 row pins `classify(OpenAIEgressStoppedError()) is None`.
- M-2 The active check never calls OpenAI while the stop is ON: the first statement of MON1's openai probe leg is `if api_budget_service.openai_egress_stop_enabled(): <skip, no models.retrieve, no record>`; a MON1 row with the transport recorder pins zero OpenAI requests per tick with the stop ON.
- M-3 OpenAI is not "in use" while the stop is ON: MON1's in-use predicate for openai is `not api_budget_service.openai_egress_stop_enabled() and <its base predicate>`, so /health/llm is not degraded by a stale openai `rejected` state once the stop is ON.

Merge orders:
- S81-12d FIRST (expected): MON1's final round replays onto main and adds M-1 (the row), M-2 and M-3 in its own files; it reads the predicate by module attribute (`api_budget_service.openai_egress_stop_enabled`), never copies the name. This unit's files do not change.
- MON1 FIRST: this unit's final round replays onto main and carries M-2 and M-3 in MON1's modules (app/services/llm_credential_probe.py and the in-use predicate in app/services/llm_credential_health.py, per the MON1 spec names; re-measured at that main) with one RED-style row each, plus the M-1 row; H1 stays after the prologue and BEFORE MON1's chokepoint hooks (MON1 places its hooks around the create, so the order is unaffected). The comm set then gains MON1's files and tests.

### 2.10 What the stop does NOT do

It never reads or changes OPENAI_API_KEY, ENABLE_OPENAI_PRE_V3, a role flag, the consent decision or the router; it never touches guarded_anthropic_create, the judge or the KB seed; it adds no entry refusal; it changes nothing in what a working credential does with the flag OFF (R-12D-4, R-12D-9).

## 3. Change list (the order GREEN applies it)

3.0 Byte copies first (Python shutil.copyfile + sha256 into <SP>/S81-12d/green/base_copies/) of app/services/api_budget_service.py, app/services/content_safety_service.py, scripts/seed_spec_spine.py, scripts/shadow_experiments.py, tests/test_s81_s03_llm_ledger_v2.py, CLAUDE.md. Never `git checkout --` a file.
3.1 app/services/api_budget_service.py: the 2.2 block after `llm_preflight_breaker_enabled` (:716-721); H1 between :994 and :995; one sentence appended to the guarded_llm_create docstring ("S81-12d (ENABLE_OPENAI_EGRESS_STOP, read per call): ON, the call raises OpenAIEgressStoppedError after the privacy prologue and before the spend admit; nothing is dispatched, admitted or recorded."); the census comment :938-956 gains one line naming the stop at H1 and H2. Edit tool only (CRLF kept).
3.2 app/services/content_safety_service.py: H2 between :254 and :255. No module-top import (the module stays stdlib-only at top).
3.3 scripts/seed_spec_spine.py: H3 (part B; dropped if OQ-1 rules so).
3.4 scripts/shadow_experiments.py: H4 (part B; same).
3.5 tests/test_s81_s03_llm_ledger_v2.py: E1 only (the K1 digest constant, built by concatenation as today, re-measured on CPython 3.12 from the GREEN bytes).
3.6 CLAUDE.md: the section 8 block after the S81-04c block (:637-639) and before `## Tests` (:641), one blank line before and after; the :341 Feature Flags pointer clause gains one sentence naming ENABLE_OPENAI_EGRESS_STOP in merge order (after the newest sentence at the then-main).
3.7 The two frozen RED files (section 5) arrive from the RED round unchanged (sha256 recorded in the gate file).
No other file. (No router, route, client, migration, processors.json, legal text, conftest, _env_safety, .github or SmartCompareApp change.)

## 4. Existing pins

### 4.1 Pins that change deliberately (E-rows)

| E | File:line | Today | After | Reason |
|---|---|---|---|---|
| E1 | tests/test_s81_s03_llm_ledger_v2.py:193 (K1_GUARDED_AST_SHA, read by :2484-2492) | sha256 of ast.dump(guarded_llm_create) at the base | the same measurement on the GREEN bytes, written by concatenation (the sweep's digit rule) | H1 adds one statement to the function by design (R-12D-2); the row's purpose (detect an unreviewed chokepoint edit) is served by re-pinning to the reviewed bytes |

No other E-row is expected (measured: no other digest, source substring or statement count over guarded_llm_create, moderate_output, extract_spine_specs or _create_with_retry; the U3c / S81-04 R37 / S81-06 G13 / R39b / M1 AST pins stay green by the rules of 1.8). A new red at GREEN is a finding, never a silent edit.

### 4.2 Pins that must stay green and unedited (named; the whole comm set 7.2 is the arbiter)

tests/test_u3c_store_false_pin.py (01, 01b, 01c, 02, 04, 05-22: store=False on both branches, scripts store discipline); tests/test_s81_s04_spend_breaker.py R37 + the chokepoint rows; tests/test_s81_s03_llm_ledger_v2.py (all but the K1 constant); tests/test_openai_breaker.py, test_retro_w1_3.py, test_m13_31_half_open_probe.py (the W1-3 arms); tests/test_cost_meter_s74.py cm03 / cm04 (record on both branches); tests/test_content_safety_service.py (fail-open rows :379-400, :474); tests/test_s81_s06_anthropic_router.py (R38, R39b, :2525-2547) and test_s81_s06_router_gate_rows.py (G13, the moderation rows); tests/test_s81_s04c_refusal_log_hygiene.py (P1-P6, R1-R7); tests/test_image_identify_llm_unavailable_s69.py; tests/test_paid_route_metering.py (vision_raised_500); tests/test_security_regression.py:222-246; tests/test_w49_extraction_catch_redaction.py; tests/test_model_config_enforced.py (M1, M5); tests/test_sentry_channels_u8d_unit.py (R8); tests/test_legal_docs_u8.py; tests/test_spec_spine_d2.py; tests/test_shadow_experiments.py; tests/test_tradeoffs_dedup_parity.py; the CLAUDE.md readers (B4).

## 5. RED tests (hermetic; two files; each RED row fails at base on an AssertionError ONLY: a missing symbol is read with getattr / importlib.util.find_spec helpers and asserted, never imported bare; each PIN row is green at base and runs with the FULL configuration and the recorders)

FULL configuration (B1 rule; every row unless it says otherwise): ENABLE_OPENAI_EGRESS_STOP per the row; the synthetic OPENAI_API_KEY / ANTHROPIC_API_KEY (2.8); ENABLE_LLM_SPEND_BREAKER=true, ENABLE_LLM_LEDGER_V2=true, ENABLE_PAID_ROUTE_METERING=true, ENABLE_COMPARE_AUTH_REQUIRED=true, ENABLE_CAMERA_FAILURE_ENVELOPE=true; ENABLE_LLM_PREFLIGHT_BREAKER parametrised OFF / ON; role flags OFF (production) unless the row says otherwise; OPENAI_BASE_URL unset. Recorders: the transport recorder (2.8) counting (host, path) per request; call recorders on `_llm_spend_breaker.spend_breaker_enabled`, `admit_openai_dispatch`, `record_openai_response_soon`, `llm_preflight_breaker_enabled`, `_openai_dispatch_admission`, `openai_record_failure` / `openai_record_success` / `openai_release_half_open_probe`, `record_openai_response`, the refund / consume calls, `save_comparison`, `fire_and_forget` labels, `sentry_sdk.capture_message` / `capture_exception`; a caplog handler at DEBUG on the root logger. Autouse: `_reset_openai_egress_stop_state` (via getattr; a no-op at base), router state reset (`llm_router._reset_router_state`), the client memo slots.

File A: tests/test_s81_s12d_openai_egress_stop.py

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| S12D-01 | reader | `openai_egress_stop_enabled` exists; ON for "true", "1", "yes", "on", " TRUE ", "On\n"; OFF for unset, "", "false", "0", "no", "off", "truthy", "2"; set / unset between two calls flips the answer (read per call) | RED (getattr None) | 2.2 |
| S12D-02 | the class and the message | `OpenAIEgressStoppedError` exists, `issubclass(..., LLMUnavailableError)`; `str(OpenAIEgressStoppedError(OPENAI_EGRESS_STOP_MESSAGE))` == the constant; lower-cased it contains none of "429", "rate", "quota", "rate limit", "ratelimit"; OPENAI_EGRESS_SURFACES == ("chat_completions", "moderations", "script"); every new constant is ASCII | RED | 2.2 |
| S12D-03 | chokepoint ON, no byte (x preflight OFF / ON) | `guarded_llm_create(<real AsyncOpenAI>, model=..., messages=[...], max_tokens=5)` raises exactly OpenAIEgressStoppedError; the transport recorder saw ZERO requests; every recorder of R-12D-5 saw ZERO calls (spend read, admit, preflight read, admission, the three W1-3 records, both response records) | RED (one 401 request recorded, AuthenticationError) | H1 |
| S12D-04 | the order | ON: the stop line is emitted and `spend_breaker_enabled` is NOT read (the stop precedes the spend admit); the caller's kwargs show store False and an extra_body store False (the prologue ran first) | RED | H1 placement |
| S12D-05 | AST placement | in guarded_llm_create: statement 1 is still the store write; exactly one call `stop_openai_egress_if_enabled("chat_completions")`, a top-level statement whose index is after the extra_body `if` and before `spend_ticket = None`; it names no `kwargs` | RED | H1 |
| S12D-06 | moderation ON | `moderate_output("synthetic shopping text")` -> allowed True, reason None; ZERO requests; `openai_service.get_client` and `model_config.moderation_model` recorders ZERO calls; one WARNING "[content_safety] L3 moderation API failed (fail-open): " + the constant; no ERROR record | RED | H2 |
| S12D-07 | Claude moderation untouched (PIN) | ENABLE_ANTHROPIC_MODERATION ON, consent 3, ANTHROPIC key set, stop ON: `moderate_with_claude` (stubbed to (True, None)) called once; ZERO OpenAI requests; no [OPENAI_EGRESS] line | PIN (green at base: the stub answers) | H2 after the Claude branch |
| S12D-08 | Anthropic-routed site untouched (PIN) | ENABLE_ANTHROPIC_TEXT ON, consent 3, stop ON: `route("parse", guarded_llm_create, <client>, ...)` returns the stubbed `_dispatch_claude` result; guarded_llm_create recorder ZERO; ZERO OpenAI requests; no stop line | PIN | the router is not edited |
| S12D-09 | pre-v3 lands on the stop | ENABLE_ANTHROPIC_TEXT ON, consent absent, ENABLE_OPENAI_PRE_V3 ON, stop ON: `route("parse", ...)` raises OpenAIEgressStoppedError; ZERO requests | RED | H1 |
| S12D-10 | once per process per surface | three chat stops + two moderation stops -> exactly two [OPENAI_EGRESS] records, WARNING, args == ("chat_completions",) and ("moderations",); after `_reset_openai_egress_stop_state()` one more chat stop logs again | RED | 2.2 latch |
| S12D-11 | no Sentry, no ERROR | across S12D-03 / -06 flows: capture_message / capture_exception ZERO calls; no record >= ERROR from any logger; AND the stop happened (ZERO requests) | RED | 2.4 |
| S12D-12 | chokepoint flag-OFF identity (PIN; x stop unset / "false" / "garbage" x preflight OFF / ON) | the recorder answers 401 -> AuthenticationError (the SDK class) propagates; exactly ONE request, path /v1/chat/completions, body `store` false; the spend read + admit ONE each (spend ON); the preflight-ON arms record as at base (a 401 = server answered: no failure record); no [OPENAI_EGRESS] record | PIN | the base bytes |
| S12D-13 | moderation flag-OFF identity (PIN) | ONE request to /v1/moderations; allowed True; the WARNING carries the SDK's text | PIN | the base bytes |

| S12D-14 | THE PER-SITE PAIR (x the 15 G13 site keys + moderation; the real site function, the real route, the real chokepoint, the site's own client from a reset memo) | flag OFF (401 recorder): N_off requests to the site's path and the site's return value V_off; flag ON: ZERO requests, the stop raised exactly N_off times (a stop counter = a wrapper on `stop_openai_egress_if_enabled` that forwards), and the return value V_on equals V_off after replacing str(AuthenticationError) and OPENAI_EGRESS_STOP_MESSAGE by one token (vision: both raise; the raised class differs by design, asserted per class) | RED (ON half: requests > 0) | H1 / H2 |
| S12D-15 | the verdict fallback is not attempted | verdict model != standard model, stop ON: `generate_comparison(...)` calls the stop exactly ONCE and the router never sees the "verdict_fallback" key; the result is the base failure dict | RED | the message rule |
| S12D-16 | the eight S81-04c arms (x parse, specs, price, price_fallback, reviews, verdict, camera, url_extract) | stop ON, role flags OFF: each logs exactly ONE WARNING "<prefix>: OpenAIEgressStoppedError" and no ERROR; the delivered value equals the base failure value of that arm (S81-04c W13_DELIVERY shapes, error text normalised) | RED | the subclass |
| S12D-17 | per-call read in one process | stop ON then the env var deleted between two `guarded_llm_create` calls: the first raises with ZERO requests, the second sends ONE request (401) | RED | the per-call reader |
| S12D-18 | scripts ON (part B) | `seed_spec_spine.extract_spine_specs(...)` returns {} with ZERO requests and its WARNING carrying the constant; `shadow_experiments._create_with_retry(<real client>, model=..., messages=[...])` raises OpenAIEgressStoppedError with ZERO requests and ZERO `asyncio.sleep` calls | RED | H3 / H4 |
| S12D-19 | scripts flag-OFF identity (PIN) | the same calls OFF: ONE request each (C4 body store false; C5 body store false), C4 returns {} after the 401, C5 re-raises AuthenticationError with no retry | PIN | the base bytes |
| S12D-20 | THE CENSUS (AST over app/**/*.py and scripts/**/*.py) | the set of OpenAI SDK dispatch calls (callee ending chat.completions.create / moderations.create / embeddings.create / responses.create / images.generate / files.create / batches.create / audio.*.create / models.list / models.retrieve, excluding anthropic clients named `ac` / `_anthropic*` and the strings in docstrings) is EXACTLY {api_budget_service.guarded_llm_create x2, content_safety_service.moderate_output, seed_spec_spine.extract_spine_specs, shadow_experiments._create_with_retry} and in each such function a `stop_openai_egress_if_enabled(<literal in OPENAI_EGRESS_SURFACES>)` statement precedes the dispatch in source order inside the same try / body; no other function calls it; no URL literal with host api.openai.com outside llm_provider.py, processors.json and sentry_service.py | RED | H1-H4 |

File B: tests/test_s81_s12d_no_byte_e2e.py (Q6: the transport proof across the entries; the harness of tests/test_w49_extraction_catch_redaction.py quota_outage (:458-486) and tests/test_s81_s04c_refusal_log_hygiene.py run_camera, with moderation NOT stubbed and the OpenAI calls answered by the transport recorder instead of a raising fake)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| E01 | text compare GET /api/v1/text/compare (explicit pair, authed, metering ON) | OFF: N_off OpenAI requests (chat + one moderation), status S_off, body B_off; ON: ZERO requests, the same status, the same body after normalisation (request_id, comparison_id, timings, the two error texts), the same consume / refund calls, the same save_comparison payload (normalised), stops per surface == requests per path at OFF | RED (ON: requests > 0) | H1 / H2 |
| E02 | text compare POST /api/v1/text/compare (product_a / product_b) | as E01 | RED | H1 / H2 |
| E03 | stream GET /api/v1/text/compare/stream | the same event-name sequence; the terminal event bodies equal after normalisation; ZERO requests ON | RED | H1 / H2 |
| E04 | camera POST /api/v1/image/identify (authed, two synthetic images) | OFF: ONE request (vision), 500, code SERVER_ERROR, error == the 500 literal; ON: ZERO requests, 503, code LLM_UNAVAILABLE, error == LLM_UNAVAILABLE_FRIENDLY_MESSAGE, success False; in BOTH: one consume, one refund, label usage_refund.image.vision_exception, no moderation request; ON no capture_* call | RED (ON half) | H1 + image_routes.py:412 |
| E05 | link compare POST /api/v1/url/compare (the page fetch stubbed to an HTML page without structured price, so extract_with_ai runs) | OFF and ON: 503, code LLM_UNAVAILABLE, the same refund; ON ZERO requests; stops == OFF requests | RED | H1 |
| E06 | the other entries: POST /text/quick and GET /text/parse (admin key), GET /text/price-kpi | ON: ZERO requests; status and body equal OFF after normalisation | RED | H1 |
| E07 | price-warmer `_warm_one(<gold record>)` | ON: ZERO requests; the tally equals OFF | RED | H1 / H2 |
| E08 | flag-OFF e2e identity (PIN; x stop unset / "false" / " garbage ") | for E01-E07: the request count per path equals the count recorded at base and frozen in the file as literals by the RED agent; the bodies equal the base bodies recorded as literals (normalised) | PIN | the base bytes |
| E09 | a mixed configuration | ENABLE_ANTHROPIC_TEXT + _VERDICT ON, consent 3 (the Claude text path stubbed at `_dispatch_claude`), moderation and vision roles OFF, stop ON: text compare -> ZERO OpenAI requests (the moderation call is the one that would have gone to OpenAI), the Claude stub called | RED (the moderation request at base) | H2 |

Counts: 23 RED rows (S12D-01..06, -09, -10, -11, -14..18, -20; E01..E07, E09) and 6 PIN rows (S12D-07, -08, -12, -13, -19; E08); parametrised ids multiply the nodes. RED satisfiability: every RED row is satisfied by the 2.2 / 2.3 bytes alone (no other production change is needed); the RED agent proves it IN PLACE on byte copies of the four files, restored and sha-checked (no scratch worktree).

## 6. Mutation table (on the GREEN bytes; each mutant: a byte copy, ONE exact-string edit that matches once, the killing rows via `P --bound 600 --tag inc-12d-mut-<id> -- <file> -k "<rows>"`, restore from the copy, sha256 compare; the mutation lock .qa-mutation.lock; KILLED = an assertion failure)

| Id | Mutant (file: edit) | Killed by |
|---|---|---|
| M01 | api_budget_service: delete the H1 call | S12D-03, -14, E01 |
| M02 | api_budget_service: move H1 below the spend admit (after :1000) | S12D-03 (admit recorder), -04, -05 |
| M03 | api_budget_service: move H1 inside `if not llm_preflight_breaker_enabled():` | S12D-03 [preflight ON], -05 |
| M04 | api_budget_service: H1 before the store write (statement 1) | S12D-04, -05 (and the U3c 01 pin) |
| M05 | reader default "true" (`os.getenv(..., "true")`) | S12D-01 (unset), -12, -13, -19, E08 |
| M06 | reader without `.strip()` | S12D-01 (" TRUE ") |
| M07 | reader set ("true", "1") only | S12D-01 ("yes", "on") |
| M08 | reader cached at import (a module-level bool) | S12D-17, -01 (per call) |
| M09 | the class derives from RuntimeError, not LLMUnavailableError | S12D-02, E04 (500 instead of 503), -16 |
| M10 | the helper raises plain LLMUnavailableError | S12D-02, -16 (type name) |
| M11 | the message gains " (rate stop)" | S12D-02, -15 (a fallback attempt = two stops) |
| M12 | the log line at ERROR | S12D-10, -11 |
| M13 | the latch removed (logs every stop) | S12D-10 |
| M14 | the latch shared across surfaces (a bool) | S12D-10 |
| M15 | the log line carries `kwargs.get("model")` | S12D-10 (args), -05 (names kwargs) |
| M16 | content_safety: delete H2 | S12D-06, -14 [moderation], E01, E09 |
| M17 | content_safety: H2 before `decide_moderation()` | S12D-07 (Claude moderation stopped) |
| M18 | content_safety: H2 after `client = get_client()` | S12D-06 (get_client recorder) |
| M19 | content_safety: H2 outside the try (raises to the caller) | S12D-06 (raises instead of allowed), E01 |
| M20 | seed_spec_spine: delete H3 | S12D-18, -20 |
| M21 | shadow_experiments: H4 inside the retry loop after the create | S12D-18 (one request), -20 (order) |
| M22 | api_budget_service: H1 passes "moderations" | S12D-10 (args), -20 (literal per function) |
| M23 | the helper returns instead of raising when ON | S12D-03 (no exception), -14 |
| M24 | the helper inverted (`if openai_egress_stop_enabled(): return`) | S12D-03, -12 (OFF raises) |

Equivalent survivors are reported to the gate for a ruling, never deleted.

## 7. Comm set and gates for GREEN (cheapest first)

### 7.1 Gates

1. `git diff --stat` = the section 3 files only; no whole-file diff (CRLF kept); bytes > 127 added: none (the existing em dash at api_budget_service.py:1010 is untouched); the added-line sweep (credential shapes, 8-digit runs, @gmail, +973) clean; no gitleaks keyword in a new constant name.
2. `<venv python> -m py_compile` and `-m ruff check --select E9,F63,F7,F82 --no-cache` on the four edited files and the two RED files.
3. The RED files: P --bound 600 --tag inc-12d-green-red -- tests/test_s81_s12d_openai_egress_stop.py tests/test_s81_s12d_no_byte_e2e.py (all green; PIN rows also green at base, B5).
4. The direct readers (B1, B2, B3 of 1.10) at head; each red node re-run at base.
5. The mutation table (section 6).
6. The CI-order set (7.3).
7. The comm set (7.2), base and head, `comm -13` of the sorted FAILED node-id sets EMPTY.
8. The fourteen backend-scanning client jest fences BY PATH (the unit touches app/ and scripts/; no fence reads a literal it moves, so they are expected green): from SmartCompareApp through the orchestrator's junction, the H5 jest probe first; `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/brand/inAppMark.u4c.test.ts __tests__/clientTruth/medicalNote.s74.test.tsx __tests__/clientTruth/privacyManifest.s74.test.ts __tests__/clientTruth/shareTruth.s74.test.tsx __tests__/clipboardFallbackService.test.ts __tests__/config/nativeBundle.w37.test.ts __tests__/DimensionBars.perCategory.test.tsx __tests__/honestCounts.s69.test.tsx __tests__/landing.domain.s76.test.ts __tests__/navigation/linking.w315.test.ts __tests__/onboarding/step05Trust.s69.test.tsx __tests__/playInstallReferrerService.test.ts __tests__/playInstallReferrerService.edges.test.ts __tests__/ResultsScreen.timeout.test.tsx` (the fourteen of the common brief, paths measured with `git ls-files`; the accepted base failures are the four nativeBundle.w37 drift nodes). The FULL jest suite runs ONCE in the last round before the PR (LC-7).
9. The CLAUDE.md readers (B4) at head after the block lands.

### 7.2 The comm set (the union rule of the common brief)

Measured at the base (an AST import graph over a `git archive` copy of app/, scripts/ and tests/, iterated to a fixpoint from the four edited modules): 105 app / scripts modules import an edited module directly or transitively, app.main among them; 668 of the 766 parseable tests/test_*.py files are in that importer closure (tests/test_subtype_spec_reconciliation.py does not parse with ast because of a BOM and is counted in by rule). The remaining members by rule are the source-scanning pins (tests/test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py, test_legal_docs_u8.py, test_security_regression.py, test_s81_s06_router_gate_rows.py, test_s81_s06_anthropic_router.py, test_s81_s04_spend_breaker.py, test_s81_s03_llm_ledger_v2.py, test_s81_s22b_self_critique_retire.py, test_legal_s78.py), the app/ and scripts/ glob / path-segment walkers, the CLAUDE.md readers by the import graph (B4) and the SmartCompareApp-scanning backend tests. Because the closure already holds 87 percent of the suite and the remainder is mostly scanners and walkers, the comm set is ruled the WHOLE free tier: every tests/test_*.py at the base (767) minus the four test_precommit_hook*.py files = 763 files, in chunks of at most 25 files (31 chunks), bound 1200, base and head. No stored record exists for 6b909e0a: the RED agent records it once (LC-6) under harness/base_records/6b909e0a.../<set-sha256>.txt.

### 7.3 CI-order set (one process, alphabetical as CI runs; bound 1200; a lifespan user BEFORE the RED files, the P73 lesson)

P --bound 1200 --tag inc-12d-ci-order -- tests/test_api_budget_service.py tests/test_content_safety_service.py tests/test_cost_meter_s74.py tests/test_image_identify_llm_unavailable_s69.py tests/test_model_config_enforced.py tests/test_openai_breaker.py tests/test_s81_s03_llm_ledger_v2.py tests/test_s81_s04_spend_breaker.py tests/test_s81_s04c_refusal_log_hygiene.py tests/test_s81_s06_anthropic_router.py tests/test_s81_s06_router_gate_rows.py tests/test_s81_s12d_no_byte_e2e.py tests/test_s81_s12d_openai_egress_stop.py tests/test_s81_s20_result_gate.py tests/test_u3c_store_false_pin.py tests/test_w49_extraction_catch_redaction.py

(test_s81_s20_result_gate.py sorts after the RED files alphabetically; the gate therefore ALSO runs a second ordering with it first: `-- tests/test_s81_s20_result_gate.py tests/test_s81_s12d_no_byte_e2e.py tests/test_s81_s12d_openai_egress_stop.py`, so a process-state leak in either order is seen.)

## 8. CLAUDE.md block, anchor and owner steps (Q7)

### 8.1 Anchor

After the S81-04c block (CLAUDE.md:637-639 at the base: the heading line `**SESSION 81 unit (S81-04c REFUSAL-LOG-HYGIENE, ...` and its two bullets), one blank line, then this block, one blank line, then `## Tests` (:641). If MON1 or another unit lands a block at the same anchor first, the final round unions this block AFTER the newest one in merge order. The :341 Feature Flags pointer clause gains the sentence "ENABLE_OPENAI_EGRESS_STOP (S81-12d): see the S81-12d block." after its newest sentence.

### 8.2 Block text (GREEN writes it; ASCII; the dates filled at the merge)

```
**INCIDENT LANE unit (S81-12d OPENAI-EGRESS-STOP, 2026-11-<dd>; ONE new flag, default OFF, read PER CALL; FOCUS, two adversaries; spec .qa-s80/S81-12d_UNIT_SPEC.md):**
- `ENABLE_OPENAI_EGRESS_STOP` (`app/services/api_budget_service.py::openai_egress_stop_enabled`, the house idiom, read per call as the first statement of `stop_openai_egress_if_enabled(surface)`): ON, every call that would go to OpenAI fails LOCALLY before any network activity with `OpenAIEgressStoppedError` (an `LLMUnavailableError`): in `guarded_llm_create` after the store=False prologue and BEFORE the spend admit, the W1-3 admission, the dispatch and every record (all 15 routed sites); in `content_safety_service.moderate_output` after the Claude branch (the arm fails OPEN as on a 401); in `scripts/seed_spec_spine.py` and `scripts/shadow_experiments.py`. Claude-routed calls are untouched; the router, the consent decision, ENABLE_OPENAI_PRE_V3 and OPENAI_API_KEY are not read or changed. One WARNING `[OPENAI_EGRESS] dispatch stopped locally surface=<chat_completions|moderations|script>` per process per surface; never ERROR, never a Sentry event. Delivery with ON = today's with the rejected key, except the camera: the existing coded 503 `LLM_UNAVAILABLE` (both refunds) instead of the 500 `SERVER_ERROR` (both live bundles show the same engine-unavailable state for either). OFF: byte-identical (one getenv per dispatch).
- Stated limits: L1 role ON + pre-v3 client: the coded LLM_UNAVAILABLE mid-pipeline; L4 the key must stay set (an unset key fails at client construction before the stop); L5 the stop is host-blind (applies to an OPENAI_BASE_URL override too); processors.json and the legal texts are unchanged (S81-12 / S81-12b own them).
- **Owner steps (names only; a dated ledger line per step):** none to merge. (1) The relay sets `ENABLE_OPENAI_EGRESS_STOP=true` on web on the owner's yes, in its own window (under legal path B: the FIRST step of the legal window); (2) the same on price-warmer before any `ENABLE_PRICE_CACHE_WARMER` flip (recommended in the same window, so the date covers every service that can reach OpenAI); (3) the relay files the dated line: that date is the one a legal text may carry. Proof: the spec's section 8b.
```

### 8.3 Owner steps (names only; nobody but the owner decides; nobody reads a value)

1. ENABLE_OPENAI_EGRESS_STOP=true on the web service: set by the relay on the owner's yes, ONE window (a variable change redeploys web: the window keeps no other proof running). Under path B of IT26-5 it is the first step of the legal window and its date is the "stopped sending data to OpenAI on <date>" of the texts.
2. ENABLE_OPENAI_EGRESS_STOP=true on the price-warmer service (no traffic there today: ENABLE_PRICE_CACHE_WARMER=false; required before any warmer flip).
3. No other service: the census (1.4) shows no other Railway process reaching OpenAI.
4. The relay files the dated ledger line (service names, the time, "ON"); no value other than this flag is read.

## 8b. PROOF ON THE PHONE (header H6; R0-1; the brief's section 4)

After the merge the unit is "merged, NOT yet proven". The proof runs AFTER the flip (8.3 step 1), by the relay with the owner, and needs no AI text:

| Step | The owner does | Must be visible (Q8, plain words) | Backing check (the relay) |
|---|---|---|---|
| P1 | one text comparison of a golden pair (e.g. Aventus vs Layton) | the result looks as it did before the flip: scores, prices and the grey "explanation not available" note, no AI text | the deploy log for those minutes: ZERO request lines to the OpenAI host (today each of the 7 to 10 chat calls and the moderation call leaves a 401 request line) and ONE `[OPENAI_EGRESS] ... surface=chat_completions` and ONE `... surface=moderations` line (the first stops since the redeploy); the arms log `<prefix>: OpenAIEgressStoppedError` at WARNING; Sentry: no new "Specs extraction error" / "Comparison generation error" events for those minutes |
| P2 | one camera scan of two bottles | the engine-unavailable screen (the copy and the back button) | the request line of POST /api/v1/image/identify answers 503 (today 500); the WARNING `[IMAGE] Vision call failed: OpenAIEgressStoppedError` (today an ERROR with the 401 text); the credit is refunded (the usage screen / quota shows the scan was not charged); no new Sentry event |
| P3 | one link comparison of two product links | the same AI-engine-unavailable message as before the flip | POST /api/v1/url/compare answers 503 LLM_UNAVAILABLE as before; ZERO OpenAI request lines; the refund as before |
| P4 | - | - | the saved rows of P1 keep zero OpenAI calls and zero cost (metadata openai ledger), as today |
| P5 | - | - | the relay files the dated line; that date is the one a legal text may carry |

A MEASURED BEFORE / AFTER, stated plainly: by code reading at the base AND at both live bundles (683f56c0, f1e20c39: failureClassification.ts:79-94 and ResultsScreen.tsx:377 / :400), today's camera 500 SERVER_ERROR ALREADY routes to the engine-unavailable state, so P2's SCREEN does not change with the flip; the change is in the status line, the log level and Sentry. The brief's expectation that "the camera shows the engine-unavailable message instead of 'Image analysis failed'" does not hold by this reading (the literal is never rendered); this is NOT verified on a device (answer to Q8 and OQ-4).

What is NOT provable in production: (a) the absence of packets: the deploy log shows the absence of SDK request lines, not of network bytes (the hermetic transport rows S12D-03 / -14 / E01-E09 are the only per-byte measure and are necessary, never the proof); (b) OpenAI's side: a revoked key's refused requests may not appear in the organisation's usage page either way; (c) that no operator runs a script without the flag in its shell (C4 / C5 stop only where the flag is set). The hermetic suites and gates are never presented as the production proof.

## 9. Stated limits

- L1 Role ON + a consent-below-3 client + ENABLE_OPENAI_PRE_V3 ON + the stop ON: the OpenAI-bound sites refuse with the class, so the S81-06 role-ON arms answer the coded LLM_UNAVAILABLE envelope mid-pipeline (after the scraping), where today's 401 in that configuration is swallowed into a deterministic result. Not a production state today (no role flag on); it equals the pre-v3-OFF delivery minus the entry refusal.
- L2 The str(e) carried in four internal failure values (specs, price, price_training, url_extract) changes text under ON (the SDK's 401 message -> the constant). By the W4-9 measurement none reaches the response body on the phone path; the pair rows (S12D-14, E01-E07) normalise exactly these texts and fail on any other difference.
- L3 The once-per-process latch is not locked: two concurrent first stops may each log (at most one extra line per surface per process).
- L4 OPENAI_API_KEY must stay set for the delivery to be today's: unset, the clients fail at construction before the stop (the owner keeps the variable; R-12D-4 forbids that lever anyway).
- L5 Host-blind: an OPENAI_BASE_URL pointing elsewhere is stopped too (the flag means "no request through the OpenAI SDK").
- L6 Not stopped: Claude traffic (by design), the judge and KB-seed batch services (anthropic SDK), and every non-LLM outbound call.
- L7 Operator scripts outside the chokepoint (C4, C5) stop only when the flag is in the shell that runs them (part B); the operator scripts that run through C1 (measure_warmed_kpi, warm_kpi_truth, seed_zyte_luxury) stop the same way.
- L8 The MON1 contract (2.9) is enforced only once MON1 lands; until then nothing reports the stop on /health.

## 10. Out of scope (R-12D-9)

Every legal text and processors.json row (the main lane's S81-12 / S81-12b); removing the OpenAI SDK or its client code; retiring the credential (window 22); any client change; any change to what a working credential does with the flag OFF; MON1's files; an entry refusal for text compares; a /health key for the stop; the camera / text copy.

## 11. Answers to the brief's questions and open questions for the orchestrator

### 11.1 Answers (by measurement at 6b909e0a)

- Q1 THE CENSUS: exactly five SDK dispatch statements can reach an OpenAI host from app/ and scripts/: C1 api_budget_service.py:1002 and C2 :1013 (the 15 routed sites; web + price-warmer + in-process scripts), C3 content_safety_service.py:259 (moderation; web + price-warmer), C4 scripts/seed_spec_spine.py:381 and C5 scripts/shadow_experiments.py:999 (operator-run only, no service). No embeddings / files / responses / images / audio / batches / models call, no raw HTTP to an OpenAI host, no Anthropic-to-OpenAI fallback; the base-URL override is host-blind under the stop. Production reaches C1 and C3 today on web only (price-warmer flag false). The stop goes at H1 (after :994), H2 (after :254), H3 (before :381, in the try), H4 (after :994 of shadow_experiments). Section 1.4.
- Q2 THE DELIVERY TABLE: section 1.6. Role flags OFF, every entry answers the same for today's AuthenticationError and for the stop class, except the camera (500 SERVER_ERROR -> 503 LLM_UNAVAILABLE, the same two refunds: the ruled exception) and the text of four internal str(e) values (L2). Pins: test_s81_s04c P2 / P4 / P5, test_image_identify_llm_unavailable_s69.py:233, test_paid_route_metering vision_raised_500, test_w49 r2c / r2e, test_s80_url_mode_v2, test_content_safety_service fail-open rows. The class chosen at EVERY site is OpenAIEgressStoppedError (an LLMUnavailableError): neither another class nor a per-site class is needed (an AuthenticationError look-alike would keep the camera's codeless 500, against R-12D-3).
- Q3 THE ORDER: prologue -> stop -> (never reached) spend read / admit, preflight read / admission, create, both response records, the W1-3 records. Recorders in S12D-03 / -04 (zero calls of each) and S12D-05 (AST position); moderation: decide_moderation -> stop -> (never) moderation_model / get_client / create (S12D-06, -07).
- Q4 The class is OpenAIEgressStoppedError everywhere. The eight arms PR #399 edited (parse :1570, specs :1742, price :1797, price_fallback :1855, reviews :1915, verdict :2827, camera image_routes.py:390, url_extract url_extraction_service.py:983) each log ONE WARNING `<prefix>: OpenAIEgressStoppedError` (by type, no text; the role-ON elif twins are not reached with roles OFF); the other arms log their existing WARNING with the constant message (2.4). Row S12D-16.
- Q5 THE E-ROWS: one, E1 (the K1 digest, test_s81_s03_llm_ledger_v2.py:193). Measured and staying green: the U3c chokepoint rows (statement 1, kwargs discipline, two dispatches, scripts store), S81-04 R37, S81-06 G13 / R38 / R39b / the site census, M1 / M5, the model-literal ban, U8d R8, the legal scanner, the S81-04c rows, test_security_regression:222-246. Section 4.
- Q6 THE NO-BYTE PROOF: a class-level recorder on httpx2.AsyncClient.send (the pinned SDK's only send path, openai/_base_client.py:1631) plus socket / httpx belts, held across the chokepoint (S12D-03), every site (S12D-14), the scripts (S12D-18) and each entry end to end (E01-E07, E09) with the flag ON and the FULL configuration; the flag-OFF identity rows (S12D-12, -13, -19, E08) use the same recorder answering 401 to COUNT the calls that do happen, frozen as base literals.
- Q7 The CLAUDE.md block, its anchor (after the S81-04c block :637-639, before `## Tests` :641) and the owner steps by name: section 8.
- Q8 What the owner sees with the flag ON: the text comparison looks exactly as today; the link comparison shows the same AI-engine-unavailable message as today; the camera shows the engine-unavailable screen, which (by code reading of both live bundles) it ALREADY shows today for the 500, so no screen changes anywhere; the visible change is in the deploy log (no OpenAI request lines, the stop lines, 503 instead of 500 on the camera) and in Sentry (no new events). Section 8b.

### 11.2 Open questions for the orchestrator (each with the assumption this spec takes and why)

- OQ-1 Part B (the two operator scripts C4 / C5): IN by this spec, because R-12D-2 and the privacy-and-egress adversary read "no code path of this repository", the cost is two statements and two RED rows, and the flag-OFF identity is pinned. The alternative (OUT, a stated limit) is defensible because neither is a production process and neither sends user content (seed snippets, gold queries). A ruling either way changes only 3.3 / 3.4, S12D-18 / -19 / -20 and M20 / M21.
- OQ-2 The class: a NEW subclass (OpenAIEgressStoppedError) rather than the bare LLMUnavailableError, so the deploy-log proof can tell a stop from a W1-3 / spend denial by type name and MON1 can pin it; every isinstance arm behaves the same either way (measured: no `type(e) is` check on the class exists in app/; the only `type(e).__name__ ==` compare is auth_service.py:266, unrelated).
- OQ-3 Host-blind stop (L5): assumed, because a host check would add a variable read and a URL parse to every dispatch and the flag's purpose (no request through the OpenAI SDK) is simpler to state in a legal text; if an OpenAI-compatible provider is ever configured through OPENAI_BASE_URL, the flag must stay OFF or a new unit scopes it.
- OQ-4 The proof step P2: the brief expects a visible camera change; this spec measured none (both live bundles render the 500 and the 503 the same way). The orchestrator may keep P2 as "the screen stays the engine-unavailable state" with the status / log check as the proof, or ask the relay for one device read of today's camera failure before the flip (a before / after pair on the phone).
- OQ-5 The role-ON + pre-v3 behaviour (L1): the spec takes "the stop behaves like a typed refusal" because the camera ruling needs the class and a role-dependent class would be a second branch to pin; if the main lane wants pre-v3 clients served deterministically under the stop, the smallest change is to raise a non-LLMUnavailableError class when `_llm_router.any_role_enabled()` is True at the chokepoint, which this spec does NOT recommend (it reintroduces a codeless camera 500 in that configuration).
- OQ-6 Whether the K1 re-pin (E1) is filed as an E-row of this unit's PR body or as a GREEN-time measurement only: assumed an E-row with the digest measured on the GREEN bytes (the S81-04 precedent).

## Not done in this spec

No test, gate, mutant or jest run (READ-ONLY round, H5 c): every run of 1.10, 5, 6 and 7 is DEFERRED TO RED / GREEN with its command. Not measured: the full per-entry body equality (rows E01-E07 measure it), the exact count of OpenAI requests per entry on the hermetic harness (E08 freezes it), which rows of tests/test_cron_warm_price_cache.py pin `_warm_one`, the device rendering of the camera failure (OQ-4), production flag state beyond the dated ledger line 316 and H2, and anything on MON1's branch. No file outside .qa-s80/ was written in the worktree; the scratch copies under <SP>/S81-12d/spec were deleted.
