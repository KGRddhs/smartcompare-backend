# B2 unit spec (measured): RESULT-GATE (refuse unsupported verdicts as non-deliveries)

Unit B2 of PLAN_S80.md section 3 (batch 1), bound by rulings R-A3 (an abstain is a non-delivery),
R-A4 (status vocabulary, minimum evidence to crown), R-A5 (placeholder and same-identity rules),
R-A6 (camera copy during review) and RULINGS_R0 R0-1 / R0-4 / R0-5, RULINGS_BATCH1 B3-R6(11) and
B4-R6 (B2 threads `consumed_keys` for every abstain exit it adds). Flag `ENABLE_RESULT_GATE` (new; default
OFF; read per call; the FIRST statement / first operand of every gated predicate, so OFF reads no state).
Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s80-b2`, branch `feature/s80-result-gate`, base
`95cf6f864b4e70980ca191daa064c0118e223c13` (origin/main = B1 #364 + B3 #365; HEAD == base, detached;
`git status --short` empty at 19:36 AST on 2026-10-20 and again after every probe in this spec; nothing was
written to the worktree except this file under the gitignored `.qa-s80/`; the offline tally imported the
worktree's pure `result_gate` with `python -B`, so no `__pycache__` was written). Every `file:line` below
was read at the base sha in this run (2026-10-20 19:36-20:30 AST); resolve by symbol if a line moves.
Measurement location: `<scratchpad>/b2/` (notes.md, base_r1..r3.log, b2_tally.py, b2_tally_out.json,
b2_tally_stdout.txt, comm_set.txt). Evidence pointers: PLAN_S80.md sections 0, 1 (R-A3..R-A6), 3 (B2);
RULINGS_R0.md R0-1, R0-4, R0-5, R0-6; RULINGS_BATCH1.md B3-R6(11), B4-R5, B4-R6; DEFECT_LEDGER.md rows
MYEZ-001 (category-conflict half), 002, 003, 004, 007 (partial), 011, 012, 027;
`runs/research/contract_freeze.json` (findings 1-3 and RULES 3, 4, 9); `runs/research/eval_regression.json`
(T01, T03, T04, T05, T10, the V01-V10 map); `runs/research/identity_winner.json` (CAMERA-SPOT fix item (3)
= the plan's "F3": a placeholder, `is_product` false or a LOW confidence returns the camera `action:'error'`
body before the compare; extra finding 4 = Rule 1 dead); `runs/r0/abstain_tally.json`.
Sister units and contracts: B1 RESULT-STATUS (#364, merged; `app/services/result_gate.py` primitives, the
`metadata.product_categories` stamp under its own flag, the `comparison_result_status` message); B3
VISION-IDENTITY-V2 (#365, merged; V2 vision products carry `confidence` in {high, medium, low},
`_category`, `_distinguishing_features`, `_image_index`, `_is_product`; `public_vision_products`); B4
URL-MODE-V2 (`feature/s80-b4-url-mode-v2`, NOT merged, fix round 2 running; owns the URL pre-gate, the typed
URL codes and `url_extraction_service.py`; B2's URL hunk is the smallest post-compare check, seams in 2.7);
C1 (client, three result states) consumes `reason` later; build 3 ignores it (1.7).
Personal-data rule: no real name, email, phone, Apple id, device id, address or account id in any file,
test, fixture or log line; synthetic values built at run time where a shape matters (user ids like
`b2-<node>`); the added-line sweep (@gmail, +973, 8-digit runs, key shapes) runs over the GREEN diff. Pure
ASCII and LF in every file this unit writes (this spec: 0 bytes > 127, checked after the write).

---------------------------------------------------------------------------------------------------

## 0. What the unit does (one paragraph)

Under a new dark flag, a comparison that B1's assessment says is NOT a supported result is refused as a
non-delivery instead of being crowned, through envelopes build 3 already renders: on the text routes (POST
and GET `/api/v1/text/compare`) and the URL route (POST and GET `/api/v1/url/compare`) as HTTP 400 with
`code: INSUFFICIENT_DATA` raised through `_surface_comparison_failure`, carrying an ADDITIVE `reason` in
{placeholder_identity, same_identity, category_conflict, no_evidence}; on the stream as its existing
INSUFFICIENT_DATA terminal event shape plus `reason`; on the camera route BEFORE the paid compare as the
existing `action:'error'` body (or the existing `need_second_product` body when exactly one of the pair is a
placeholder) carrying `reason` in {placeholder_identity, low_confidence, same_identity, category_conflict},
never `comparison_failed`. Every refusal refunds the reserved credit (and the anonymous one where it was
debited) with the gate's `consumed_keys` BEFORE any raise, never bumps the lifetime counter, never writes a
history row, and writes exactly one `search_logs` row with `success=False` and the constant message
`result_gate:<reason>`. The gate computes the assessment itself (`assess_result` / B1's predicates) with
the per-product categories the builder stamps under EITHER flag, so no flip order leaves it inert. Flag OFF
the unit is byte-identical on every response, SSE frame, stored row, log row and refund call.

---------------------------------------------------------------------------------------------------

## 1. Base state (measured at 95cf6f86)

### 1.1 The delivery exits and where each gate goes

| Exit | Where (base) | Measured fact | B2 seam |
|---|---|---|---|
| text POST | `app/api/text_routes.py:578` `text_compare`; gate consume `:617-630` (`usage_check` dict carries `consumed_keys`, `:630` keeps only `consumed`); compare `:638-649`; `_truth` `:653`, `_syn` `:654`; failure branch `:655-698` (log OFF arm `:658-667`, refund `:675-679` WITHOUT keys, log ON arm `:680-691`, `_surface_comparison_failure` `:696`); delivery `:700-771` (log `:709-718`, save `:719-762`, lifetime `:765-768`, `capture_result_status` `:770`) | a `success:True` body is delivered and billed whatever B1 says | insert after `:654`, before `:655` |
| text GET | `:774` `text_compare_get`; consume `:832-847`; compare `:849-861`; `_truth` `:865`, `_syn` `:866`; failure branch `:867-905` (refund `:883-887`); delivery `:907-955` | same shape as POST | insert after `:866`, before `:867` |
| stream | `:958` `text_compare_stream`; consume `:1021-1034` (`usage_consumed` captured by the closure); `event_generator` `:1064`; terminal capture `:1121-1170` (first terminal latches `complete_after_client_gone`; W3-2 persist `:1148-1163` under `ENABLE_COMPARISON_ID_ECHO`); yield `:1219`; `finally` `:1220-1372`: `if complete_response and not had_error and not complete_after_client_gone:` `:1224` | 1.4: a `success:False` terminal takes the DELIVERY branch today: no refund, `save_comparison_and_track_cohort` attempted, `record_lifetime_comparison` called (W4-13b) | intercept at `:1121`; new first branch of the `finally` chain at `:1224` |
| camera | `app/api/image_routes.py:192` `identify_and_compare`; anon gate `:217-240` (`anon_consumed_keys`); `_refund_reserved_credit(label)` `:285-298` (calls `refund_comparison_credit(usage_user_id)` WITHOUT keys, latched); `_refund_anon_credit(label)` `:302-318` (passes `anon_consumed_keys`, latched); authed gate `:320-334`; vision `:341-363`; non-delivery exits 2-5 `:365-473` (exit 4 `action:'error'` body `:452-457`, exit 5 `need_second_product` body `:466-473`); the 2+ branch `:475-483` (`p1, p2 = products[0], products[1]`, `query`, `_truth` `:482`, `_syn` `:483`); `try:` `:484`; paid compare `:501-503`; unsuccessful arm `:511-595`; delivery `:597-647` | no pre-compare identity, confidence or category check: any two products auto-compare (eval_regression T01/T05) | insert after `:483`, before `:484` (before ANY paid call; `_camera_user_preferences` at `:497` is inside the try) |
| URL | `app/api/url_routes.py:122` `_compare_urls_metered`; reserve `:144` via `_reserve_comparison_credit(user) -> bool` `:59-88` (returns `bool(usage_check.get("consumed", False))` at `:88`; the keys are dropped); compare `:160-171`; failure `:173-200` (refund `:177-181` without keys; rows only under W4-13 flag 1); delivery: save + lifetime under metering `:202-214`, success row under `_truth` `:216-220`, `capture_result_status` `:223` | the envelope (`url_extraction_service.py:681-690`) has NO `metadata`, NO `scoring_v2`, price dicts WITHOUT `source_method`, the rating under `products[i].reviews.rating` | insert after `:200` (end of the failure block), before `:202` |

The three orchestrator callers of `build_comparison_response` pass `product_categories` (scs `:3848` partial
builder `ctx.get("product_categories")`, `:4628` REST, `:5472` stream; captured BEFORE the pair write-back at
`:4312` REST and `:4945` stream). Every stream terminal yields ONE object twice (`settle_complete` then
`complete`): scs `:4800-4801`, `:4818-4819`, `:5025-5026`, `:5049-5050`, `:5072-5073` (H6
INSUFFICIENT_DATA), `:5555-5556` (L3 moderation), `:5564-5565` (the full result).

### 1.2 The B1 primitives B2 reuses (app/services/result_gate.py, 659 lines)

`assess_result(result, *, product_categories=None, vision_confidences=None)` `:504-548` returns
`{status, reasons, identity_confidence, data_coverage, data_coverage_literal, section_status,
unknown_product_count, same_identity, coherent, facts, facts_literal}`; `reasons` in `REASONS` order
(`:35-42`: not_success, placeholder_identity, same_identity, unsupported_category, category_conflict,
no_evidence); status = the first reason's status (`_STATUS_BY_REASON` `:43-50`), `supported_result` when
none applies (R-A4's minimum evidence). Building blocks: `product_is_placeholder` `:136-141` (identity text
via `dedup_brand_name` OR the name alone), `same_identity(p0, p1)` `:171-183` (normalised identities equal,
or equal brands with name Jaccard >= 0.9; vetoed when BOTH carry a different `variant`/`size_or_count` or
`distinguishing_features` -- note the key has NO underscore; a V2 vision product carries
`_distinguishing_features`), `identity_coherence(product_categories, category_used)` `:193-205` (False only
when both are canonical, not `other` and differ), `price_is_showable` `:210-221` (requires a non-empty
`source_method` != estimated), `rating_is_real` `:236-239` (reads `product["rating"]`), `real_spec_rows`
`:258-272`, `stamped_product_categories(result)` `:553-561` (the ONE reader of `metadata.product_categories`).
`result_status_metadata_enabled()` `:83-85` is the house idiom. B1's builder stamp
(`app/services/response_builder.py:2264-2295`, inside `if result_status_metadata_enabled():` `:2273`, a
try/except that logs `[RESULT_STATUS] assess failed` by type) writes `metadata.product_categories`
(`:2286-2287`) ONLY under B1's flag; `_strip_inference_markers(result)` is `:2303`. B1's telemetry
(`sentry_service.capture_result_status` `:671`) runs at every delivery exit (text `:770`, `:954`, stream
`:1307`, camera `:646`, URL `:223`) and re-assesses with the stamped categories.

### 1.3 The cross-category rule is dead today (Rule 1), measured

`detect_comparison_quality` (scs `:985-1035`) Rule 1 `:1006-1009` compares `_product_category(p)` (`:193-194`,
`category_used or category`) per product; every live path writes the pair category onto BOTH products before
the products reach it: scs `:4326-4327` (REST write-back loop), `:4946-4947` (stream), and
`url_extraction_service.py:641-642` (URL). The detector runs on `product_data` built from those dicts
(`response_builder._safe_detect_comparison_quality` `:480-483`, used at `:1343` and `:2090`; the verdict
prompt reads it via `verdict_comparison_quality` scs `:1038-1060` under ENABLE_COMPARISON_QUALITY_V2). So
Rule 1 can never fire on the vision, typed-pair, parser or URL path (identity_winner extra finding 4,
re-measured). B1's `identity_coherence` over the pre-write-back categories IS the revived rule; B1 measures it
(`category_conflict` -> `unsupported_category`), B2 enforces it (2.1 decision D3).

### 1.4 The stream bills a success:False terminal today (measured, W4-13b)

In the `finally` (`text_routes.py:1224-1307`) a terminal with `success: False` that the client received
takes the first branch: W4-13 flag 1 ON logs a failure row (`:1225-1245`), then `if user_id:` (`:1264`,
OUTSIDE the success/failure split) schedules `save_comparison_and_track_cohort` (refused later by
`_validate_renderable`, which needs `metadata.query`) and `record_lifetime_comparison` (`:1298-1301`), and
NO refund fires. So re-using the INSUFFICIENT_DATA terminal shape alone would BILL every stream refusal
(R-A3 violated); B2 adds its own first branch (2.5). The phones never open the stream (contract_freeze
finding 2: `ENABLE_EXPO_FETCH_SSE_DEFAULT=false`), so this is a correctness rule for the dormant path.

### 1.5 Refund primitives and consumed_keys per route

`usage_service.refund_comparison_credit(user_id, consumed_keys=None)` `:488-505`; with keys it credits
exactly the debited windows, without them the legacy floor-at-zero + previous-window fallback
(`_refund_credit_sync` `:472-485`). `consume_comparison_credit` returns `consumed_keys` (`:364-371`).
`refund_anon_comparison_credit(fp, consumed_keys)` `:129-135`. No existing text/URL/camera-reserved refund
passes keys (text `:677`, `:885`, `:1323`, `:1354`; URL `:165`, `:179`; camera `:298`); the camera anon refund
does (`:317`). B2 passes keys on every exit it adds and leaves every existing call shape untouched (B4-R6).

### 1.6 The error envelope at base, and B4's passthrough on its branch

`app/middleware/error_handler.py:113-143` `http_exception_handler`: a structured detail (`_is_structured_detail`
`:74-91`) is unwrapped to `{success, error, code, request_id}` (+ `retry_after_seconds` on a 429 only); every
other detail key is DROPPED, so `reason` cannot reach the wire without a handler change. B4 (branch head
`96676f1f`, measured with `git diff 81df2b64 96676f1f -- app/middleware/error_handler.py`) adds `import os`,
a local reader `_url_mode_v2_keys_enabled()` (the middleware never imports a service), a tuple
`_URL_V2_PASSTHROUGH_CODES` and ONE block after the `content = {...}` dict that copies str `field`/`reason`
for its three codes when its flag is ON. B2 adds a parallel, independently scoped block (2.8).

### 1.7 Build 3 rendering (client at the base sha, measured)

- `SmartCompareApp/src/services/api.ts:1049-1127` `parseApiError`: `code = data.code || data.detail.code`;
  reads `error`/`detail` and `retry_after_seconds` (`withRetryAfter` `:1038-1047`) only; any other key
  (`reason`) is ignored. `src/services/errorCopy.ts:72-95` `friendlyErrorKey`: `INSUFFICIENT_DATA` ->
  `home.errors.insufficientData` (`src/i18n/en.json:119`: "Thin data on that pair -- swap in two products
  with brand and model."; the AR twin exists, contract_freeze finding 3). The text compare (HomeScreen
  `:481` parse, `:519` copy) and the URL compare (`:613`, `:637`) both render by code.
- Camera: `src/screens/ResultsScreen.tsx:296-355`: `action:'error'` (the final else) -> `vision_failed`
  (en.json:854 "Snap each product in its own photo and we'll line them up side by side."),
  `need_second_product` -> `need_more_photos` (en.json:853), `comparison_failed` -> the timeout state
  (tap-to-retry, re-sends the photos: why B2 never uses it); `src/services/failureClassification.ts:104-109`
  `isCameraEngineOutageResponse` fires only on the outage codes, so B2's code-less camera body cannot be
  routed there. Build 3 never opens `/text/compare/stream`.

### 1.8 The flag-reader idiom; production state

House idiom (`result_gate.result_status_metadata_enabled` `:83-85`, `openai_service.vision_identity_v2_enabled`
`:256-263`): `os.getenv("ENABLE_RESULT_GATE", "false").strip().lower() in ("true", "1", "yes", "on")`, read
per call, never cached. B2 has NO numeric knob. Production (newest dated ledger lines; the session-80
`ledger.md` carries no flag-state line for these names, so the brief's permitted facts apply):
ENABLE_PAID_ROUTE_METERING, ENABLE_CAMERA_FAILURE_ENVELOPE and ENABLE_COMPARE_AUTH_REQUIRED ON since
2026-10-03; ENABLE_RESULT_STATUS_METADATA, ENABLE_VISION_IDENTITY_V2, ENABLE_URL_MODE_V2 and
ENABLE_RESULT_GATE are new names (unset by construction). UNKNOWN (designed for both states):
ENABLE_SEARCH_LOG_TRUTH / _SYNTHETIC_MARKER (W4-13), ENABLE_COMPARISON_ID_ECHO (R-A15),
ENABLE_ANON_USAGE_GATE, ENABLE_STRICT_OPTIONAL_AUTH.

### 1.9 Libraries and guards the new code must not trip

- Pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren` (fastapi/starlette per the lock; no new
  dependency). `extraction_service.classify_category_from_text` `:1307-1340` is pure and $0 (it reads
  ENABLE_CATEGORY_TOKEN_FIX per call) and is the stub the vision path uses (scs `:4236-4250`).
- **B1 P11 purity pin** (`tests/test_s80_b1.py:1146-1157`): `result_gate.py` stays pure ASCII, imports only
  {os, re, typing, __future__, app.services.text_sanitize}, has no `async def`, and must NOT contain the
  SUBSTRINGS `sentry_sdk`, `structured_comparison_service`, `response_builder`, `price_service`,
  `extraction_service`, `httpx`, `asyncio`, `socket`, `logging` -- in code, comments or docstrings. B2's
  additions obey it (the em dash of the refusal sentence is built with `chr(0x2014)`; the camera category
  stub is computed in `image_routes`, never in `result_gate`; the INFO lines live in the routes).
- `tests/test_s75_fanout_identity.py:60-64` `UNIT_ENV` (FY25 nine digests pop these names per scenario).
- `tests/test_w4_13_flag_off_ledger.py`: the fire_and_forget LABEL sequence and `log_search` kwargs at every
  existing exit with W4-13 flags unset -- B2 OFF adds no label and no kwarg.
- `tests/test_s71_u13_compare_auth_required.py` T17/T23: no new route parameter or body field (R0-6);
  `CLEAN_ENV` `:76-84`. `tests/test_retro_w2_1.py:173-176` autouse `_clean_flags`.
- `tests/test_text_routes_error_mapping.py`, `tests/test_http_400_cap_cut_mapping.py`,
  `tests/test_text_error_envelope_no_raw_exception.py`: the 400 INSUFFICIENT_DATA detail is exactly
  `{code, error}` and the envelope exactly `{success, error, code, request_id}` flag OFF.
- U8d log-hygiene AST pins (`tests/test_sentry_channels_u8d_unit.py`, `tests/test_auth_error_log_hygiene.py`
  os.walk over `app/`): new log templates carry constants and closed-set enums only; nothing at ERROR.
- `tests/_netguard`: nothing here resolves a host. The pre-commit hook: no credential shapes.

### 1.10 Base pass state (bounded runner, one process at a time, every unit flag unset)

```
run 1  tests/test_text_routes_error_mapping.py tests/test_http_400_cap_cut_mapping.py
       tests/test_text_error_envelope_no_raw_exception.py tests/test_m13_37_freemium_atomic_consume.py
       tests/test_paid_route_metering.py tests/test_retro_w2_1.py tests/test_m13_26_image_error_envelope.py
       tests/test_image_identify_llm_unavailable_s69.py tests/test_error_middleware.py tests/test_429_contract.py
       tests/test_m18_usage_symmetry.py
       collected 226 items; 226 passed, 13 warnings in 7.45s
       [hermeticity] sentinel checked 226 test(s); [netguard] blocked 25 attempt(s) from 25 node(s)
       (the ratchet baseline's sentinel class: neutralized.supabase.invalid:443)
       [pyt] tag=b2-base-r1 start=2026-10-20 19:59:17 end=2026-10-20 19:59:28 elapsed=11s bound=600s status=OK rc=0
run 2  tests/test_s75_fanout_identity.py tests/test_w4_13_flag_off_ledger.py tests/test_w4_13_measurement_truth.py
       tests/test_s80_b1.py tests/test_s80_b3_vision_identity_v2.py tests/test_comparison_id_echo.py tests/test_streaming.py
       collected 601 items; 601 passed, 12 warnings in 35.58s
       [hermeticity] sentinel checked 601 test(s); [netguard] blocked 40 attempt(s) from 16 node(s)
       (test_streaming.py egress api.openai.com:443 -- existing baseline behaviour, blocked)
       [pyt] tag=b2-base-r2 start=2026-10-20 19:59:40 end=2026-10-20 20:00:17 elapsed=38s bound=600s status=OK rc=0
run 3  tests/test_auth_error_log_hygiene.py tests/test_events_allowlist_superset.py
       tests/test_sentry_channels_u8d_unit.py tests/test_s71_u13_compare_auth_required.py
       tests/test_compare_timeout_graceful.py tests/test_timeout_partial_integration.py tests/test_openai_breaker.py
       tests/test_camera_vision.py tests/test_b2_strict_optional_auth.py
       collected 454 items / 1 deselected / 453 selected; 453 passed, 1 deselected, 13 warnings in 24.67s
       [hermeticity] sentinel checked 453 test(s); [netguard] blocked 132 attempt(s) from 13 node(s)
       [pyt] tag=b2-base-r3 start=2026-10-20 20:00:34 end=2026-10-20 20:01:01 elapsed=27s bound=600s status=OK rc=0
```

Zero failures, zero errors at base in the files this unit touches or pins (the 3 camera_vision baseline nodes
pass since B3). NOT MEASURED at spec time (RED's first job, run ALONE, G-3): `tests/test_sentry_channels_u8d.py`
(child process), `tests/test_history_routes.py`, `tests/test_home_routes.py`, `tests/test_s71_u13_pins.py`,
`tests/test_shutdown_drain.py`, `tests/test_m13_04_full_stream_deadline.py` -- all in the comm set.

### 1.11 Line endings

Every backend file in section 3 is `i/lf w/crlf` (`git ls-files --eol`, measured for result_gate.py,
response_builder.py, text_routes.py, image_routes.py, url_routes.py, structured_comparison_service.py;
error_handler.py measured the same). New files are written LF. `git diff --stat` after GREEN must show
content lines only.

### 1.12 Gate sizing: the R0 tally re-run with this spec's exact predicates (measured)

`<scratchpad>/b2/b2_tally.py` imports the REAL merged `result_gate` (python -B) and applies the text
predicate of 2.2 (`gate_reason` = the first `assess_result` reason mapped into GATE_REASONS, on a
`success:True` body, with `stamped_product_categories`) to `tests/fixtures/w412_corpus_min.json` (27
production rows, stamped `success: True` because the minimised corpus omits it) and
`tests/fixtures/lane1/*_response.json` (9):

| Set | Refused by the text predicate | Which and why |
|---|---|---|
| w412 text + text_stream rows (11) | 1 | row 6 (text): the schema-v1 junk row whose `full_response` is `{metadata}` only -> no products -> `placeholder_identity` (also same_identity, no_evidence). Not a body a live exit can produce today. |
| w412 camera rows (16) | 3 by the predicate, 0 by B2 | rows 12, 13, 14 (Manama Pickles: both prices `estimated`, ratings derived, specs 7/7 `N/A`, dims tied) -> `no_evidence` (coverage 0, literal 1). B2 does NOT gate the camera after the compare (D5), so 0 camera rows are refused post-compare; the pre-compare checks find no placeholder and no same identity on any camera row (reasons list empty except 12-14), and confidence / vision categories are not stored -> NOT MEASURABLE offline. |
| w412 partials (rows 24, 26) | 0 | coverage 1 and 2 -> supported -> delivered and billed as today (2.14). |
| lane1 (9) | 0 | coverage 3-4 on every file. |

Total: 1 of 36 bodies refused by the wired text predicate (a junk row), 0 of the 26 real deliveries and
0 of 9 lane1. Tester shapes (2.2 predicates): V09 URL `Unknown Product` x2 -> `placeholder_identity`;
V07 GUESS/GUESS! x2 -> `same_identity` (with V2 features `polyurethane` vs `cotton` -> NOT same); V04
(two LOW confidences) -> `low_confidence`; one `Unknown Product` + one high -> placeholder on exactly one.
**URL finding:** `assess_result` on a URL envelope with two real page prices and no overlapping specs
(V03-like) returns `partial_no_winner` / `no_evidence` (coverage 0, literal 1) because the URL price dict has
no `source_method` and the rating lives under `reviews.rating`; the literal predicate would refuse every
priced URL pair without spec overlap. B2 therefore uses a URL reading (2.2 `url_gate_reason`, decision D4),
and B1's URL telemetry (`capture_result_status(result, "url")`) over-reports `partial_no_winner` for the
same reason (open question Q3). The production canary for text/stream/camera is B1's
`metadata.result_status` distribution before any B2 flip; for URL it is NOT (Q3).

---------------------------------------------------------------------------------------------------

## 2. Contract

### 2.1 Flag and the coupling decisions

`ENABLE_RESULT_GATE` (new; default OFF; the 1.8 idiom; single reader `result_gate.result_gate_enabled()`;
`error_handler.py` keeps a local one-line twin, the B4 precedent, pinned equal). No knob.

- **D1 Coupling (the gate computes the assessment itself).** Every gate decision calls B1's pure
  predicates directly (never reads `metadata.result_status`), and the builder stamps
  `metadata.product_categories` when EITHER `ENABLE_RESULT_STATUS_METADATA` OR `ENABLE_RESULT_GATE` is on
  (2.3), so `category_conflict` fires in every flip order. Alternative rejected: reading B1's stamp (the
  W4-6a R5 / W4-7 R2 coupling precedent) would leave the gate inert whenever B2 is flipped before B1 or B1
  is rolled back; with the self-computing gate the two flags are independent and, when both are ON, B2
  refuses exactly the bodies B1 stamps non-supported (R8 row pins the equivalence).
- **D2 Gate location = the delivery exits (routes), not the orchestrator.** The routes own the credit, the
  refund, the history write and the log row (R-A3), they already hold `consumed_keys`, and B1's telemetry
  already assesses at the same five exits, so B1's production distribution sizes B2 one to one. The
  orchestrator is not edited (no new branch in an 8,000-line file; the camera path, which also calls
  `compare_from_text`, must never get an INSUFFICIENT_DATA failure that the ON envelope turns into
  `comparison_failed`). Cost accepted: on text/URL the refusal happens after the paid fan-out (L4).
- **D3 Rule 1.** The cross-category rule is revived as the gate's `category_conflict` refusal over the
  pre-write-back categories (B1's `identity_coherence`), on text (REST + stream) and camera (pre-compare).
  `detect_comparison_quality` Rule 1 is NOT edited: under B2 every pair it would label `weird` is refused
  before delivery, and reviving it inside the detector would only re-frame the verdict prompt of a pair the
  gate then refuses (spend without delivery). URL cannot carry it (L2).
- **D4 URL reading.** The URL gate does NOT use `assess_result` literally (1.12 finding): it applies the same
  placeholder and same-identity rules and a URL evidence reading (page price on both sides, a numeric
  rating on both sides, or one real two-sided spec row), no category conflict.
- **D5 Camera.** Refusals only BEFORE the paid compare (placeholder, low confidence, same identity, category
  conflict); a camera body that turns out thin after the compare is delivered as today (L1, Q1).

### 2.2 `app/services/result_gate.py` additions (pure; appended after `:659`; obeys 1.9 P11)

Constants (exact values):
- `GATE_REASONS = ("placeholder_identity", "same_identity", "category_conflict", "no_evidence")`
- `CAMERA_GATE_REASONS = ("placeholder_identity", "low_confidence", "same_identity", "category_conflict")`
- `GATE_CODE = "INSUFFICIENT_DATA"`
- `GATE_REFUSAL_MESSAGE = "Comparison data was incomplete " + chr(0x2014) + " choose different products."`
  (byte-equal to the H6 sentence at scs `:4373` / `:5066`; PIN R2 asserts equality with a literal built the
  same way in the test).
- `CAMERA_GATE_MESSAGE = "Could not confirm two different products. Photograph each product in its own photo."`
- `GATE_LOG_PREFIX = "result_gate:"`
- `_GATE_REASON_BY_ASSESS = {"placeholder_identity": "placeholder_identity", "same_identity": "same_identity",
  "unsupported_category": "category_conflict", "category_conflict": "category_conflict",
  "no_evidence": "no_evidence"}` (`not_success` never maps).

Functions (all total: a malformed input yields None or the conservative refusal, never raises):
- `result_gate_enabled() -> bool`: the idiom over `ENABLE_RESULT_GATE`.
- `gate_reason(result, *, product_categories=None) -> Optional[str]`: no flag read. None unless `result`
  is a dict with `success is True`; else `a = assess_result(result, product_categories=product_categories)`
  and the first reason in `a["reasons"]` that maps through `_GATE_REASON_BY_ASSESS`, else None. Invariant
  (R8): for every `success:True` body, `gate_reason(...) is None` iff `a["status"] == STATUS_SUPPORTED`.
- `url_gate_reason(result) -> Optional[str]`: no flag read. None unless a dict with `success is True` and a
  `products` list of >= 2 dicts; p0, p1 = the first two. In order: `product_is_placeholder` on either ->
  `placeholder_identity`; `same_identity(p0, p1)` -> `same_identity`; else coverage = `_url_price(p0) and
  _url_price(p1)` (price dict, `_num(amount)` and amount > 0 and `unavailable is not True` and
  `estimated is not True`) + `_url_rating(p0) and _url_rating(p1)` (`_num(p["reviews"]["rating"])` or
  `rating_is_real(p)`) + `real_spec_rows(p0.get("specs"), p1.get("specs")) >= 1`; coverage 0 ->
  `no_evidence`; else None.
- `camera_gate_reason(p0, p1, *, categories=None) -> Optional[str]`: no flag read; the pair the route would
  compare. A non-dict side counts as a placeholder. Views: `v_i = dict(p_i)` plus
  `v_i["distinguishing_features"] = p_i.get("_distinguishing_features")` when the V2 key is a list and the
  plain key is absent (so `same_identity` sees the V2 features). In order: either side
  `product_is_placeholder` -> `placeholder_identity`; either side `confidence` a str whose
  `.strip().casefold() == "low"` -> `low_confidence` (ANY low, eval_regression T01); `same_identity(v0, v1)`
  -> `same_identity`; `identity_coherence(categories)` False -> `category_conflict`; else None.
- `camera_placeholder_sides(p0, p1) -> Tuple[bool, bool]`: `(product_is_placeholder(p0), product_is_placeholder(p1))`.
- `gate_refusal_body(result, reason) -> Dict`: keys IN THIS ORDER `success` False, `error`
  GATE_REFUSAL_MESSAGE, `code` GATE_CODE, `elapsed_seconds` (metadata `elapsed_seconds` when `_finite` and
  >= 0 else 0.0), `total_cost` (metadata `total_cost` when `_finite` and >= 0 else 0.0), `api_calls`
  (metadata `api_calls` when an int >= 0 and not bool else 0), `reason` (the given reason). The key order
  prefix equals the H6 failure dict (scs `:4371-4377`); `reason` is last (additive).
- `result_gate_refusal(result, *, url_mode=False) -> Optional[Dict]`: `if not result_gate_enabled(): return
  None` is the FIRST statement; then None unless a dict with `success is True`; `reason = url_gate_reason(result)`
  when `url_mode` else `gate_reason(result, product_categories=stamped_product_categories(result))`; None ->
  None; else `gate_refusal_body(result, reason)`. The calls go through the module globals (`gate_reason`,
  `url_gate_reason`) so a test recorder patched on the module sees them (the M1 killer); the call is wrapped
  in `try/except Exception` returning None (2.13).
- `gate_log_message(reason) -> str`: `GATE_LOG_PREFIX + reason` when `reason` is in `GATE_REASONS +
  CAMERA_GATE_REASONS` (tuple membership, no hashing), else `GATE_LOG_PREFIX + "unknown"`.
- The module docstring line "nothing that reads a flag except ..." gains `result_gate_enabled` and
  `result_gate_refusal` (wording free; P11 substrings forbidden).

### 2.3 The builder stamp (response_builder.py; additive; after `:2295`, before the M18 comment at `:2297`)

```python
    # B2 (S80, ENABLE_RESULT_GATE; default OFF, read per call -- the FIRST operand, so OFF reads
    # nothing more): the gate's category input. The route-level gate re-assesses this body with
    # the stamped categories, so the per-product pair must be on the body even when
    # ENABLE_RESULT_STATUS_METADATA is OFF (no flip order leaves category_conflict inert).
    # setdefault: under B1 the same value is already there. Additive key only.
    if result_gate_enabled() and isinstance(product_categories, list) and len(product_categories) == 2:
        result["metadata"].setdefault(
            "product_categories", [c if isinstance(c, str) else None for c in product_categories])
```
Import at `:21`: add `result_gate_enabled` to the existing `from app.services.result_gate import ...`
line. Nothing else in the builder moves (no crown change, no B1 key under B2 alone).

### 2.4 Text POST and GET (text_routes.py)

- Import (after `:49`): `from app.services.result_gate import GATE_CODE, GATE_REASONS, gate_log_message, result_gate_enabled, result_gate_refusal`.
- Keys: POST adds `usage_consumed_keys = None` beside `usage_consumed = False` (`:617`) and
  `usage_consumed_keys = usage_check.get("consumed_keys")` after `:630`; GET the same at `:832` / after `:847`.
- One module helper, defined after `_surface_comparison_failure`:

```python
def _result_gate_exit(refusal, *, query, input_type, user_id, usage_consumed,
                      consumed_keys, duration_ms, syn, where):
    """B2 (ENABLE_RESULT_GATE): the abstain exit (R-A3). Refund FIRST (the M13-37
    lesson), then ONE failure row, then the 400 through the shared mapping, which
    raises. Never a save, never a lifetime bump."""
    if usage_consumed and user_id:
        fire_and_forget(refund_comparison_credit(user_id, consumed_keys),
                        label=f"usage_refund.{where}.result_gate")
    fire_and_forget(
        log_search(query=query, input_type=input_type, user_id=user_id, success=False,
                   error_message=gate_log_message(refusal.get("reason")),
                   cost=_failure_log_cost(refusal), duration_ms=duration_ms, **syn),
        label=f"log_search.{where}.result_gate",
    )
    logger.info("[RESULT_GATE] refused input=%s reason=%s", input_type, refusal.get("reason"))
    _surface_comparison_failure(refusal)
```
- Call sites (POST after `:654`, GET after `:866`; `where` = `text.post` / `text.get`):

```python
    # B2 (S80): flag read inside, FIRST; None OFF or on a supported / failed body.
    _refusal = result_gate_refusal(result)
    if _refusal is not None:
        _result_gate_exit(_refusal, query=<body.query | q>, input_type="text",
                          user_id=user.get("id") if user else None,
                          usage_consumed=usage_consumed, consumed_keys=usage_consumed_keys,
                          duration_ms=duration_ms, syn=_syn, where="text.post")
```
  `_result_gate_exit` always raises (HTTPException 400); the W3-2 echo, the save, the lifetime write and
  `capture_result_status` are below it and unreachable for a refusal. An anonymous caller (no consume):
  no refund, one row.

### 2.5 The stream (text_routes.py `text_compare_stream`)

- Keys: `usage_consumed_keys = None` beside `:1021`, set after `:1034` (closure-captured).
- `event_generator` local `_b2_refusal = None` beside `:1065-1075`.
- At the top of `if event_type in ("complete", "settle_complete"):` (`:1121`), before the latch:

```python
                    # B2 (S80): the FIRST terminal decides; the duplicate terminal reuses it.
                    if _b2_refusal is None and complete_response is None:
                        _b2_refusal = result_gate_refusal(data)
                    if _b2_refusal is not None:
                        data = _b2_refusal
```
- The W3-2 persist condition (`:1148-1151`) gains `and _b2_refusal is None` (a refusal is never persisted
  and carries no `comparison_id`; flag OFF `_b2_refusal` is always None -> identical).
- The `finally` chain gains a FIRST branch; the existing `if` at `:1224` becomes `elif` (text unchanged):

```python
            if (_b2_refusal is not None and complete_response is _b2_refusal
                    and not had_error and not complete_after_client_gone):
                # B2 (R-A3): refund with the gate's keys, ONE failure row; no save, no lifetime,
                # no status message (the W4-13b billing of success:False terminals does not apply).
                if usage_consumed and user_id:
                    fire_and_forget(refund_comparison_credit(user_id, usage_consumed_keys),
                                    label="usage_refund.text_stream.result_gate")
                fire_and_forget(log_search(query=q, input_type="text_stream", user_id=user_id,
                                           success=False,
                                           error_message=gate_log_message(_b2_refusal.get("reason")),
                                           cost=_failure_log_cost(_b2_refusal),
                                           duration_ms=duration_ms, **_syn),
                                label="log_search.text_stream.result_gate")
                logger.info("[RESULT_GATE] refused input=%s reason=%s", "text_stream",
                            _b2_refusal.get("reason"))
            elif complete_response and not had_error and not complete_after_client_gone:
                ...   # unchanged
```
  A client that left before the refusal terminal takes the existing `else` (incomplete refund without keys,
  the W4-13 T5 row): unchanged base behaviour for a non-delivery. Wire shape of both terminal frames:
  `{"success": false, "error": GATE_REFUSAL_MESSAGE, "code": "INSUFFICIENT_DATA", "elapsed_seconds", "total_cost",
  "api_calls", "reason"}` (the existing H6 terminal shape + `reason`).

### 2.6 The camera (image_routes.py; before ANY paid call)

- Imports: `from app.services.result_gate import CAMERA_GATE_MESSAGE, camera_gate_reason,
  camera_placeholder_sides, gate_log_message, result_gate_enabled`; `from app.services.extraction_service
  import classify_category_from_text` (P11 forbids it inside result_gate).
- `usage_consumed_keys = None` beside `:282`, set after `:334` from `usage_check.get("consumed_keys")`.
- `_refund_reserved_credit(label, consumed_keys=None)`: when `consumed_keys is None` the body is byte-equal to
  base (`refund_comparison_credit(usage_user_id)`); else `refund_comparison_credit(usage_user_id,
  consumed_keys)`. Same latch. Every existing call keeps its one-argument form.
- Module helper `_camera_gate_categories(p0, p1) -> list`: per side, the V2 `_category` when it is a str in
  the nine canonical keys, else `classify_category_from_text(f"{brand} {name}".strip())` with base defaults
  `brand "Unknown"`, `name "Unknown Product"` (the exact stub scs `:4238-4245` computes, so B1's camera stamp
  sees the same categories when V2 is OFF).
- Inserted after `:483`, before `try:` `:484`:

```python
    # B2 (S80, ENABLE_RESULT_GATE): the camera refusal is decided BEFORE the paid compare (R-A6,
    # CAMERA-SPOT fix 3); build 3 renders action 'error' as vision_failed and
    # need_second_product as need_more_photos; never comparison_failed.
    if result_gate_enabled():
        _gate = camera_gate_reason(p1, p2, categories=_camera_gate_categories(p1, p2))
        if _gate is not None:
            _refund_reserved_credit("usage_refund.image.result_gate", consumed_keys=usage_consumed_keys)
            _refund_anon_credit("usage_refund.image.anon.result_gate")
            fire_and_forget(
                log_search(query=query, input_type="camera",
                           user_id=user.get("id") if user else None,
                           products_found=product_names, success=False,
                           error_message=gate_log_message(_gate),
                           cost=round(_log_cost_value(vision_cost) or 0.0, 6),
                           duration_ms=int((time.time() - start_time) * 1000), **_syn),
                label="log_search.camera.result_gate",
            )
            logger.info("[RESULT_GATE] refused input=%s reason=%s", "camera", _gate)
            _ph0, _ph1 = camera_placeholder_sides(p1, p2)
            _other = p2 if _ph0 else p1
            if _gate == "placeholder_identity" and (_ph0 != _ph1) and not _is_low(_other):
                return {"success": True, "action": "need_second_product",
                        "products": public_vision_products([_other]),
                        "message": f"Identified: {_other.get('brand', '')} {_other.get('name', '')}. "
                                   f"Take another photo or type a product to compare with.",
                        "vision_cost": vision_cost, "reason": _gate}
            return {"success": False, "action": "error", "error": CAMERA_GATE_MESSAGE,
                    "vision_cost": vision_cost, "reason": _gate}
```
  `_is_low(p)` = `isinstance(p.get("confidence"), str) and p["confidence"].strip().casefold() == "low"`
  (module helper). Precedence: exactly one placeholder with a non-low other side -> the existing
  `need_second_product` shape (+ `reason`), every other refusal -> the existing `action:'error'` shape
  (+ `reason`); no `code` key on either (1.7: `isCameraEngineOutageResponse` would route an outage code).
  Products beyond index 1 are not considered (base compares only the first two).

### 2.7 URL (url_routes.py) and the B4 rebase seam

- `_reserve_comparison_credit(user, keys_out=None)` (signature `:59`); before `return bool(...)` at `:88`
  insert `if isinstance(keys_out, dict) and isinstance(usage_check.get("consumed_keys"), dict):
  keys_out.update(usage_check["consumed_keys"])`. Call site `:144`: `_b2_keys = {}` then
  `usage_consumed = await _reserve_comparison_credit(user, keys_out=_b2_keys)`.
- Imports: `from app.services.result_gate import gate_log_message, result_gate_refusal`.
- Inserted after `:200` (the end of the `if not result.get("success"):` block), before `:202`:

```python
    # B2 (S80, ENABLE_RESULT_GATE): the URL reading (D4); a non-delivery like the failure exit above.
    _refusal = result_gate_refusal(result, url_mode=True)
    if _refusal is not None:
        if usage_consumed and user_id:
            fire_and_forget(refund_comparison_credit(user_id, _b2_keys or None),
                            label="usage_refund.url.compare.result_gate")
        _url_row("log_search.url.result_gate", success=False,
                 error_message=gate_log_message(_refusal.get("reason")))
        logger.info("[RESULT_GATE] refused input=%s reason=%s", "url", _refusal.get("reason"))
        surfaced = _surface_comparison_failure(_refusal)
        if surfaced is not None:
            return surfaced
```
- **Seam with B4 (either merge order).** B4 edits `url_routes.py` imports (adds `asyncio` and a
  url_extraction_service block after `:26`), adds helpers after `_reserve_comparison_credit` (its hunk's
  leading context is the `return bool(...)` line and two blank lines), the `_compare_urls_metered`
  docstring and signature (`url_mode_v2`), the compare call `:161` and a three-line block INSIDE the
  failure branch before `if result.get("code"):`. B2's changes touch the signature line `:59`, one line
  BEFORE `:88`, the call line `:144` and a block AFTER the failure branch: no B2 change region is adjacent to
  a B4 change region (two or more unchanged lines between each pair), so `git merge`/`rebase` is expected to
  apply cleanly; the import blocks may conflict textually (resolution: keep both). `error_handler.py`: both
  add `import os` and a block after the `content` dict -> a conflict in that hunk is EXPECTED; resolution
  = keep B4's block, then B2's block, one `import os`. CLAUDE.md: rows after B4's row if B4 merges first
  (G-2). Tests: if B4 is on main first, `ENABLE_RESULT_GATE` joins B4's `_CLEAN_ENV` in
  `tests/test_paid_route_metering.py` (E4). B2's URL gate runs on B4's V2 envelope unchanged (B4 adds no
  `metadata`, measured `git diff 81df2b64 96676f1f -- app/services/url_extraction_service.py`), AFTER B4's
  typed failures (they are `success:False` and leave through the failure branch first).

### 2.8 `_surface_comparison_failure` and the error envelope

- `text_routes._surface_comparison_failure` coded arm (`:549-553`) becomes:

```python
    if code:
        detail = {"code": code, "error": error_msg}
        # B2 (flag read FIRST): an INSUFFICIENT_DATA gate refusal keeps its additive reason.
        if (result_gate_enabled() and code == GATE_CODE
                and result.get("reason") in GATE_REASONS):
            detail["reason"] = result["reason"]
        raise HTTPException(status_code=400, detail=detail)
```
  Flag OFF the detail is the same two-key dict (no H6 / hard-cap / parser failure carries a gate reason
  anyway). `in GATE_REASONS` is a tuple test (an unhashable value cannot raise).
- `error_handler.py`: `import os`; `_RESULT_GATE_REASONS = ("placeholder_identity", "same_identity",
  "category_conflict", "no_evidence")` (pinned equal to `result_gate.GATE_REASONS`, R62);
  `_result_gate_keys_enabled()` = the idiom over `ENABLE_RESULT_GATE` (pinned equal to
  `result_gate.result_gate_enabled` over the truthy/falsy table, R62); after the `content` dict (`:133-138`):

```python
    # B2 (S80, flag read FIRST): an INSUFFICIENT_DATA gate refusal keeps its additive `reason`.
    if (_result_gate_keys_enabled() and _is_structured_detail(detail)
            and detail.get("code") == "INSUFFICIENT_DATA"
            and detail.get("reason") in _RESULT_GATE_REASONS):
        content["reason"] = detail["reason"]
```
  Wire body of a text/URL refusal: `{"success": false, "error": "...", "code": "INSUFFICIENT_DATA",
  "request_id": "<uuid>", "reason": "<one of four>"}`, HTTP 400. Never a 503; never a new code.

### 2.9 New keys and types

| Surface | Key | Type / values | When |
|---|---|---|---|
| text/URL 400 envelope | `reason` | str in GATE_REASONS | flag ON, gate refusal only |
| stream terminal frames | `reason` (+ the H6 keys) | str in GATE_REASONS | flag ON, gate refusal only |
| camera `action:'error'` / `need_second_product` body | `reason` | str in CAMERA_GATE_REASONS | flag ON, camera refusal only |
| delivered text/stream/camera body | `metadata.product_categories` | list of two (str or None) | flag ON (or B1 ON, today) and the caller passed a 2-list |
| search_logs row | `error_message` | `result_gate:<reason>` | every refusal |

### 2.10 Logging rules

One INFO line per refusal, `[RESULT_GATE] refused input=%s reason=%s`, both arguments constants / closed-set
enums (never a query, a name, a URL or an id). Nothing at ERROR. No new line under OFF. The builder stamp
logs nothing.

### 2.11 Test seams (production values in brackets)

`result_gate.gate_reason`, `url_gate_reason`, `camera_gate_reason` module globals (recorders patch them);
`text_routes.get_comparison_service` [per-request service]; `image_routes.identify_products`,
`image_routes.StructuredComparisonService`, `image_routes.log_search`,
`image_routes.save_comparison_and_track_cohort`; `url_routes.compare_from_urls`; the Ledger recorders of
`tests/test_retro_w2_1.py` (`consume`, `refund` with `consumed_keys`, lifetime, history, log rows, labels);
`fire_and_forget` label recorder; companion flags [PROD: ENABLE_PAID_ROUTE_METERING=true,
ENABLE_CAMERA_FAILURE_ENVELOPE=true, ENABLE_COMPARE_AUTH_REQUIRED=true]; `ENABLE_RESULT_STATUS_METADATA`,
`ENABLE_VISION_IDENTITY_V2`, `ENABLE_COMPARISON_ID_ECHO`, `ENABLE_SEARCH_LOG_TRUTH` [unset / UNKNOWN] set per
row explicitly.

### 2.12 Flag-OFF identity (the unit's main invariant)

With `ENABLE_RESULT_GATE` unset / blank / `false` / `0` / `off` / `no`, under the FULL companion
configuration (metering ON, envelope ON, B1 ON, V2 ON, echo ON, W4-13 both states): every response body,
status, SSE frame, `search_logs` kwarg set, fire_and_forget label sequence, refund call (args), save and
lifetime call is byte-identical to base; `gate_reason`, `url_gate_reason` and `camera_gate_reason` are
called ZERO times (recorders); the builder writes `metadata.product_categories` only under B1 (as base); the
error envelope never carries `reason`. Pinned by P1-P8 (5.1), the unedited 4.2 files (incl. the FY25 nine
digests and the W4-13 flag-OFF ledger) and the comm set.

### 2.13 Failure table (flag ON)

| Situation | Behaviour |
|---|---|
| text/URL body supported (coverage >= 1, identity resolved, distinct, coherent) | delivered exactly as OFF plus `metadata.product_categories` on text bodies |
| text/stream body with a placeholder product | 400 / terminal INSUFFICIENT_DATA reason placeholder_identity; refund (keys); one row; no save; no lifetime |
| same identity | reason same_identity |
| per-product categories canonical, not other, different (or `category_used` not canonical) | reason category_conflict |
| AUDITABLE coverage 0 (incl. a hard-cap partial with coverage 0) | reason no_evidence |
| a `success:False` result (H6, TIMEOUT, LLM_UNAVAILABLE, CONTENT_UNAVAILABLE, parser) | untouched (its own exit) |
| `assess_result` raising (it is total; defensive) | `result_gate_refusal` wraps the `gate_reason` / `url_gate_reason` call in `try/except Exception` returning None (deliver as OFF); no log line inside `result_gate` (P11 forbids the logging module there) |
| camera: placeholder on exactly one side, other not low | `need_second_product` (existing shape + reason), refunds, one row, no compare |
| camera: both placeholders / any low / same identity / category conflict | `action:'error'` (+ reason), refunds, one row, no compare |
| camera after the compare | as OFF (D5) |
| URL: placeholder / same identity / URL coverage 0 | 400 INSUFFICIENT_DATA + reason; refund (keys); one row |
| client gone before the stream refusal terminal | existing incomplete-refund arm (no keys) |
| mid-request flip | each read is per call: a refusal built ON and surfaced OFF loses `reason` on the wire (still INSUFFICIENT_DATA, still refunded through B2's exit, which does not re-read the flag); a body built OFF and gated ON lacks `product_categories` (category_conflict cannot fire for that one request) |

### 2.14 Delivered partials (stated, per the plan)

R-A4: "A partial (hard-cap) result may crown only if coverage >= 1." So a partial (`metadata.partial`
True) with AUDITABLE coverage >= 1 and a resolved, distinct, coherent pair is delivered and billed exactly as
today (R-A3: billing of DELIVERED partials unchanged); a partial with coverage 0, or with an identity reason,
is refused like any other body. Measured: w412 partial rows 24 and 26 have coverage 1 and 2 -> delivered.

---------------------------------------------------------------------------------------------------

## 3. Change list, in the order GREEN applies it

0. Byte copies of every file below into the notes folder (sha256 recorded); mutation lock rules apply.
1. `app/services/result_gate.py`: append the 2.2 constants and functions (+ `_url_price`, `_url_rating`
   private helpers); docstring line. Pure ASCII; P11-clean.
2. `app/services/response_builder.py`: import `result_gate_enabled` at `:21`; the 2.3 block after `:2295`.
3. `app/middleware/error_handler.py`: `import os`; `_RESULT_GATE_REASONS`; `_result_gate_keys_enabled()`;
   the 2.8 block after `:138`.
4. `app/api/text_routes.py`: import (2.4); `_surface_comparison_failure` coded arm (2.8);
   `_result_gate_exit` helper; POST keys + gate; GET keys + gate; stream keys, `_b2_refusal`, terminal
   intercept, persist condition, `finally` first branch (2.5).
5. `app/api/image_routes.py`: imports; `usage_consumed_keys`; `_refund_reserved_credit(label,
   consumed_keys=None)`; `_camera_gate_categories`, `_is_low`; the 2.6 block.
6. `app/api/url_routes.py`: imports; `_reserve_comparison_credit(user, keys_out=None)`; the call site; the
   2.7 block.
7. Tests: `tests/test_s80_b2_result_gate.py` (the RED file, frozen at the gate; GREEN adds nothing to it);
   E1-E3 (4.1); E4 only when B4 is already on main.
8. `CLAUDE.md`: the section 8 row after the B3 row (`:477`), before `## Tests` (`:479`); the other context
   files the orchestrator names ("also update context files": DEFECT_LEDGER rows, the session ledger) are the
   orchestrator's, not GREEN's.
No other file. (`structured_comparison_service.py`, `url_extraction_service.py`, `openai_service.py`,
`sentry_service.py`, `usage_service.py` and every client file are NOT edited.)

---------------------------------------------------------------------------------------------------

## 4. Existing pins

### 4.1 Pins that change deliberately (one row each)

| # | File | Edit | Reason |
|---|---|---|---|
| E1 | `tests/test_s75_fanout_identity.py:60-64` `UNIT_ENV` | append `"ENABLE_RESULT_GATE"` | the B2 stamp adds `metadata.product_categories` under the flag; a developer `.env` must not move the nine digests (the B1 E1 precedent) |
| E2 | `tests/test_retro_w2_1.py:173-176` autouse `_clean_flags` | add `"ENABLE_RESULT_GATE"` | its URL/text stub bodies are thin; with the flag exported locally the gate would refuse them |
| E3 | `tests/test_s71_u13_compare_auth_required.py:76-84` `CLEAN_ENV` | add `"ENABLE_RESULT_GATE"` | the recorded flag-OFF responses include delivered compares (route-affecting flags are listed there, e.g. COMPARISON_ID_ECHO, CAMERA_FAILURE_ENVELOPE) |
| E4 | `tests/test_paid_route_metering.py` `_CLEAN_ENV` (exists only after B4 merges) | add `"ENABLE_RESULT_GATE"` | same as E2; conditional on merge order |

Each is a test-only one-name edit; no assertion changes. GREEN proves each file green with AND without
the flag exported (the B4 F4-3 / E6 precedent).

### 4.2 Pins that must stay green and unedited (all green at base, 1.10)

`tests/test_text_routes_error_mapping.py`, `tests/test_http_400_cap_cut_mapping.py`,
`tests/test_text_error_envelope_no_raw_exception.py` (400 detail `{code, error}`, envelope four keys),
`tests/test_m13_37_freemium_atomic_consume.py`, `tests/test_m18_usage_symmetry.py`,
`tests/test_paid_route_metering.py` (camera/URL metering, `_stub_camera` vision `B<i>/N<i>` without
confidence passes the camera gate by construction), `tests/test_retro_w2_1.py` (rows),
`tests/test_m13_26_image_error_envelope.py`, `tests/test_image_identify_llm_unavailable_s69.py`,
`tests/test_error_middleware.py`, `tests/test_429_contract.py`, `tests/test_s75_fanout_identity.py` (nine
digests), `tests/test_w4_13_flag_off_ledger.py`, `tests/test_w4_13_measurement_truth.py`,
`tests/test_s80_b1.py` (incl. P11 purity, P12 URL never stamped), `tests/test_s80_b3_vision_identity_v2.py`,
`tests/test_comparison_id_echo.py`, `tests/test_streaming.py`, `tests/test_auth_error_log_hygiene.py`,
`tests/test_events_allowlist_superset.py`, `tests/test_sentry_channels_u8d_unit.py`,
`tests/test_sentry_channels_u8d.py`, `tests/test_s71_u13_compare_auth_required.py` (T17/T23 apart from E3),
`tests/test_compare_timeout_graceful.py`, `tests/test_timeout_partial_integration.py`,
`tests/test_openai_breaker.py`, `tests/test_camera_vision.py`, `tests/test_b2_strict_optional_auth.py` (an
older, unrelated "B2"), `tests/test_history_routes.py`, `tests/test_home_routes.py`, `tests/test_ci_gates.py`,
`tests/test_behavior_dimension_translation.py`.

---------------------------------------------------------------------------------------------------

## 5. RED tests

### 5.1 `tests/test_s80_b2_result_gate.py` (new; pure ASCII, LF; hermetic)

Harness: imports `app.main` first (autouse; the dotenv guard), then `monkeypatch.setenv`. Reuses
`tests.test_s75_fanout_identity as fy` (`_Patcher`, `_new_state`, `_install`, `QUERY`) for real-orchestrator
rows (the B1 `fy_text` pattern, `tests/test_s80_b1.py:269-284`), `tests.test_retro_w2_1`'s `Ledger`
(records `consumed_keys`, lifetime, history, log rows, labels) and its camera stub pattern with an added
compare-call counter, the lane1 fixtures, and the tester shapes of eval_regression T01/T03/T04/T05/T10.
Missing symbols are read with `getattr(rg, name, None)` + `assert callable(...)` so every RED fails on an
AssertionError at base. Every ON row sets the PROD companions (metering ON, envelope ON, auth required with
an `authed` override) explicitly; every OFF PIN sets the FULL configuration (B1 ON, V2 ON, echo ON, W4-13
flag 1 in both states via param, metering ON, envelope ON) plus the three decision recorders.
Fixtures (built at run time): BODY_SUP = lane1 `tomford_vs_creed_response.json` (coverage 4);
BODY_V09 = BODY_SUP with both products' `brand ""`, `name "Unknown Product"` (overview mirror too);
BODY_V07 = BODY_SUP with both `GUESS` / `GUESS!`; BODY_V10 = BODY_SUP with prices pended (`amount None,
unavailable True`), `rating_derived True`, specs all `N/A`, dims tied (coverage 0); BODY_CAT = BODY_SUP with
`metadata.product_categories ["electronics", "fragrances"]`; URL_V09 / URL_V03 / URL_NOEV / URL_SAME = the
1.12 URL envelopes; VISION_V07 = GUESS/GUESS! x2 `medium`; VISION_V04 = Sefiki/Violin `low` x2;
VISION_ONE_PH = (`Unknown`/`Unknown Product` low) + (`Lattafa`/`Asad` high); VISION_CAT_V2 = two V2 dicts
with `_category` electronics / fragrances; VISION_CAT_V1 = "Samsung"/"Galaxy S24 phone" + "Dior"/"Sauvage
eau de parfum" (no `_category`); VISION_FEAT = GUESS/GUESS! with `_distinguishing_features`
[polyurethane] / [cotton].

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_flag_reader_table` (param unset, "", false, 0, off, no, " TRUE ", true, 1, yes, On) | `rg.result_gate_enabled()` equals the idiom | AssertionError (absent) | 2.2 |
| R2 | `test_r2_constants` | GATE_REASONS, CAMERA_GATE_REASONS, GATE_CODE exact; GATE_REFUSAL_MESSAGE == "Comparison data was incomplete " + chr(0x2014) + " choose different products."; CAMERA_GATE_MESSAGE exact | absent | 2.2 |
| R3 | `test_r3_gate_reason_lane1_supported` (9 files) | `gate_reason(body) is None` | absent | 2.2 |
| R4 | `test_r4_gate_reason_v09_placeholder` | BODY_V09 -> "placeholder_identity" | absent | 2.2 |
| R5 | `test_r5_gate_reason_same_identity` | BODY_V07 -> "same_identity"; GUESS Logo Tee vs GUESS Denim Shirt -> None | absent | 2.2 |
| R6 | `test_r6_gate_reason_category` | BODY_SUP + cats [electronics, fragrances] -> "category_conflict"; [other, fragrances] -> None; `category_used "toys"` -> "category_conflict" | absent | 2.2 |
| R7 | `test_r7_gate_reason_corpus` | w412 rows 12, 13, 14 (success True) -> "no_evidence"; rows 24, 26 (partials) -> None; row 6 -> "placeholder_identity" | absent | 2.2, 2.14 |
| R8 | `test_r8_gate_equals_b1_status` (36 bodies + the 5 synthetic) | `(gate_reason(b, product_categories=c) is None) == (assess_result(b, product_categories=c)["status"] == "supported_result")` | absent | D1 |
| R9 | `test_r9_gate_reason_total` | success False / non-dict / products missing -> None for gate_reason; non-dict -> None for url_gate_reason | absent | 2.2 |
| R10 | `test_r10_url_gate_reason` | URL_V09 -> placeholder_identity; URL_SAME -> same_identity; URL_NOEV -> no_evidence; URL_V03 (two page prices, no specs) -> None | absent | D4 |
| R11 | `test_r11_camera_gate_reason` | VISION_V07 -> same_identity; VISION_V04 -> low_confidence; ("LOW ", high) -> low_confidence (any low); VISION_ONE_PH -> placeholder_identity; cats [electronics, fragrances] -> category_conflict; VISION_FEAT -> None; distinct high pair, [other, other] -> None | absent | 2.2 |
| R12 | `test_r12_refusal_body_shape` | `list(gate_refusal_body(BODY_SUP, "no_evidence"))` == [success, error, code, elapsed_seconds, total_cost, api_calls, reason]; values from metadata; inf / nan / bool -> 0 | absent | 2.2 |
| R13 | `test_r13_refusal_flag_first` (OFF and ON) | OFF: `result_gate_refusal(BODY_V09)` is None and recorders on `gate_reason` / `url_gate_reason` saw 0 calls; ON: one call, a body with reason placeholder_identity | absent | 2.2 (kills M1) |
| R14 | `test_r14_log_message` | gate_log_message("no_evidence") == "result_gate:no_evidence"; ("x") -> "result_gate:unknown"; ([]) -> "result_gate:unknown" | absent | 2.2 |
| R20 | `test_r20_text_post_v09_refused` (W4-13 flag 1 param both) | service returns BODY_V09: 400; json code INSUFFICIENT_DATA, reason placeholder_identity, keys == {success, error, code, request_id, reason}; ledger refunds == [uid] with refund_keys == [the consumed keys]; history == []; lifetime == []; exactly one log row success False error "result_gate:placeholder_identity" with cost == metadata.total_cost; the refund label precedes the log label | 200 delivered | 2.4, 2.8 |
| R21 | `test_r21_text_get_v07_refused` | GET with BODY_V07: 400 reason same_identity; same ledger shape | 200 | 2.4 |
| R22 | `test_r22_text_post_v10_no_evidence` | BODY_V10: 400 reason no_evidence; ledger shape | 200 | 2.4 |
| R23 | `test_r23_category_conflict_b2_alone_real_orchestrator` | B1 OFF, B2 ON; fy_text explicit pair CONFLICT_PAIR ("Samsung Galaxy S24 phone", "Dior Sauvage eau de parfum"): 400 reason category_conflict | 200 | 2.3 (kills M12) |
| R24 | `test_r24_category_conflict_both_flags` | B1 ON + B2 ON, same pair: 400 reason category_conflict | 200 | D1 |
| R25 | `test_r25_supported_real_orchestrator_stamp` | B2 ON, B1 OFF, fy_text default pair: 200 delivered; `metadata.product_categories` == [electronics, electronics] (the FY25 pair); refunds []; history 1; lifetime 1 | stamp absent -> AssertionError | 2.3 |
| R26 | `test_r26_anonymous_text_refusal` | no user: 400 refusal; refunds == []; one log row (user_id None) | 200 | 2.4 |
| R27 | `test_r27_hard_cap_partial_coverage_1_delivered` | B2 ON, fy `_scenario` REST cap 0.5 slow: 200, `metadata.partial` True; the same body with coverage forced 0 (BODY_V10 marked partial via the stub) -> 400 no_evidence | the second half 200 | 2.14 |
| R30 | `test_r30_stream_refusal_frames_and_accounting` (W4-13 both) | stub stream yields status, verdict, settle_complete(BODY_V09), complete(BODY_V09): both terminal frames parse to the 2.5 shape with reason placeholder_identity; refunds == [uid] with keys; history == []; lifetime == []; exactly one log row "result_gate:placeholder_identity"; no `log_search.text_stream.terminal_failure` / `.success` label | billed (lifetime 1, no refund) | 2.5 (kills M3, M15, M17, M18) |
| R31 | `test_r31_stream_refusal_not_persisted_under_echo` | ENABLE_COMPARISON_ID_ECHO ON: persist recorder 0 calls; frames carry no `comparison_id` | persist called | 2.5 |
| R40 | `test_r40_camera_same_identity` | VISION_V07, metering + envelope ON, authed: compare calls 0; body == {success False, action "error", error CAMERA_GATE_MESSAGE, vision_cost 0.003, reason "same_identity"}; refunds == [uid] keys == consumed keys; history []; lifetime []; one log row "result_gate:same_identity" cost 0.003 | compare called, action comparison | 2.6 (kills M5) |
| R41 | `test_r41_camera_low_confidence` (param both-low, one-low) | reason low_confidence; compare 0 | compare called | 2.6 (kills M9) |
| R42 | `test_r42_camera_one_placeholder_need_second_product` | VISION_ONE_PH with the other side high: success True, action need_second_product, products == [the Lattafa public dict], reason placeholder_identity; compare 0; refund 1 | compare called | 2.6 (kills M11) |
| R43 | `test_r43_camera_two_placeholders_error` | both Unknown: action error reason placeholder_identity | compare called | 2.6 |
| R44 | `test_r44_camera_category_conflict` (param V2 `_category`, V1 stub) | action error reason category_conflict; compare 0 | compare called | 2.6 |
| R46 | `test_r46_camera_anon_refund_keys` | ENABLE_ANON_USAGE_GATE ON + metering ON + fp header, VISION_V07: anon_refunds == [fp] with the anon keys | compare called, no refund | 2.6 |
| R50 | `test_r50_url_v09_refused` (W4-13 both) | 400 INSUFFICIENT_DATA reason placeholder_identity; refunds == [uid] keys; history []; lifetime []; one row "result_gate:placeholder_identity" | 200, history, lifetime | 2.7 |
| R52 | `test_r52_url_no_evidence` | URL_NOEV: 400 reason no_evidence | 200 | 2.7 |
| R60 | `test_r60_envelope_reason_passthrough` | flag ON: HTTPException(400, {code INSUFFICIENT_DATA, error, reason "no_evidence"}) through `http_exception_handler` -> body.reason == "no_evidence"; reason "hacked" -> no key; code TIMEOUT (503) with reason -> no key | no key -> AssertionError | 2.8 (kills M4b, M14) |
| R62 | `test_r62_reader_and_vocab_parity` | `error_handler._result_gate_keys_enabled()` == `rg.result_gate_enabled()` over the R1 table; `error_handler._RESULT_GATE_REASONS == rg.GATE_REASONS` | absent | 2.8 |
| R70 | `test_r70_builder_stamp_b2_alone` | B2 ON, B1 OFF: `build_comparison_response(..., product_categories=["electronics", "fragrances"])` -> `metadata.product_categories` present; `result_status` absent | absent | 2.3 |

PIN rows (green at base; run with the FULL configuration and the recorders):

| # | test | assertion |
|---|---|---|
| P1 | `test_p1_off_text_post_v09_delivered` (W4-13 both) | B2 unset, B1/V2/echo/metering/envelope ON: 200; body == the service body (+ the base-produced additions) recorded as a literal at base; refunds []; history/lifetime as base; gate recorders 0 calls |
| P2 | `test_p2_off_text_get_v07_delivered` | GET twin |
| P3 | `test_p3_off_stream_v09_billed_as_base` | base billing exactly (lifetime 1, no refund, the W4-13 labels per state); frames byte-equal to base literals |
| P4 | `test_p4_off_camera_v07_compares` | compare called once; action comparison; camera recorder 0 calls |
| P5 | `test_p5_off_url_v09_delivered` | 200, history + lifetime as base |
| P6 | `test_p6_off_h6_envelope_four_keys` | the H6 INSUFFICIENT_DATA failure: 400, envelope keys exactly {success, error, code, request_id} (also with B2 ON: no reason on a non-gate failure) |
| P7 | `test_p7_off_handler_drops_reason` | flag OFF: a detail carrying reason "no_evidence" -> no reason key |
| P8 | `test_p8_off_builder_no_categories` | B1 OFF, B2 OFF: no `metadata.product_categories` |
| P9 | `test_p9_on_v2_features_pair_compares` (= R45) | VISION_FEAT under ON: compare once, action comparison (kills M10) |
| P10 | `test_p10_on_supported_text_delivered` | B2 ON, BODY_SUP: 200, refunds [], history 1, lifetime 1, no gate row (kills M6) |
| P11 | `test_p11_on_url_v03_priced_pair_delivered` | URL_V03 under ON: 200 delivered (kills M13) |
| P12 | `test_p12_on_stream_supported_delivered` | supported stream under ON: base billing, frames carry no reason |
| P13 | `test_p13_on_lane1_all_delivered` (9 files via the text route) | 200 each (kills M6) |

RED count 35 rows (counted per test function: R1-R14, R20-R27, R30-R31, R40-R44, R46, R50, R52, R60, R62,
R70; parametrisations expand the node count); PIN 13 (P1-P13). The RED agent reports node counts.

### 5.2 Satisfiability notes for the RED agent

- R22/R27: assert the synthetic BODY_V10 is `no_evidence` through the real `assess_result` first (a helper
  row); if the real-orchestrator V10 (T04 leaves: specs all-dash, price None, rating None) is added, measure
  its base `assess_result` status first and keep it only if `partial_no_winner`.
- R23-R25 reuse the B1 harness verbatim (`fy._install` via `text_routes.get_comparison_service`); CONFLICT_PAIR
  is measured by B1 R16 as [electronics, fragrances].
- R30: the stub generator must yield the SAME dict object for both terminals (the orchestrator does,
  1.1); parse SSE frames by splitting on blank lines and the last `data:` line.
- P1-P5 record the base bodies / frames as literals at RED time (assert on fields, not on substrings of
  bodies carrying a random request id).

---------------------------------------------------------------------------------------------------

## 6. Mutation table (each mutant on a byte copy, an exact-string edit that matches once, the killing rows
via `pyt.py -k`, bound 600, restored and sha256-compared; KILLED = an assertion failure)

| # | Mutant | File | Killing rows |
|---|---|---|---|
| M1 | flag read moved after the assessment (compute `gate_reason(...)` before `if not result_gate_enabled(): return None`) | result_gate.py | R13, P1, P2 (recorder 0 calls) |
| M2 | the refund after the surface call (move the refund `fire_and_forget` below `_surface_comparison_failure(refusal)` in `_result_gate_exit`) | text_routes.py | R20, R21, R22 (refunds == 1) |
| M3 | a refusal that still writes a history row (stream: the B2 branch condition forced False, so the refusal falls to the delivery arm) | text_routes.py | R30 (history [], lifetime [], refunds 1) |
| M3b | text: `_result_gate_exit` schedules `save_comparison_and_track_cohort(full_response=refusal, ...)` before raising | text_routes.py | R20 (history []) |
| M4 | the reason key dropped (`detail["reason"] = ...` deleted in `_surface_comparison_failure`) | text_routes.py | R20, R21, R50 |
| M4b | the handler passthrough block deleted | error_handler.py | R60, R20 |
| M5 | the camera refusal moved after the paid compare (the 2.6 block placed after `compare_ms = ...`) | image_routes.py | R40-R44 (compare calls 0) |
| M6 | a delivered supported result refused (`gate_reason` returns "no_evidence" when no reason maps) | result_gate.py | R3, P10, P13, R25 |
| M7 | consumed_keys dropped (`refund_comparison_credit(user_id)` in `_result_gate_exit`) | text_routes.py | R20 (refund_keys) |
| M8 | the log row removed from `_result_gate_exit` | text_routes.py | R20 |
| M9 | any-low -> both-low in `camera_gate_reason` | result_gate.py | R11, R41 (one-low param) |
| M10 | the V2 features view removed (`same_identity(p0, p1)` on the raw dicts) | result_gate.py | P9, R11 |
| M11 | one placeholder returns `action:'error'` (the need_second_product branch deleted) | image_routes.py | R42 |
| M12 | the builder stamp gated on B1 only (`result_gate_enabled()` replaced by `result_status_metadata_enabled()`) | response_builder.py | R23, R70 |
| M13 | URL gate uses the strict reading (`gate_reason` instead of `url_gate_reason`) | result_gate.py | P11, R10 |
| M14 | the handler vocabulary check removed (any str reason passes) | error_handler.py | R60 ("hacked") |
| M15 | stream: the refusal applied to the first terminal only (`data = _b2_refusal` guarded by `complete_response is None`) | text_routes.py | R30 (second frame) |
| M16 | stream: refund in the B2 branch without keys | text_routes.py | R30 |
| M17 | stream: B2 branch also calls `record_lifetime_comparison` | text_routes.py | R30 |
| M18 | stream: the existing `elif` restored to `if` (both arms run) | text_routes.py | R30 (refunds 1, history []) |
| M19 | `_GATE_REASON_BY_ASSESS` drops `unsupported_category` | result_gate.py | R6 ("toys") |
| M20 | casefold/strip removed from the low test (`== "low"`) | result_gate.py | R11 ("LOW ") |
| M21 | `result_gate_refusal` ignores `success` (refuses a success:False body too) | result_gate.py | R9, P6 |
| M22 | URL refund placed after `_surface_comparison_failure` | url_routes.py | R50 |
| M23 | the camera log row removed | image_routes.py | R40 |

---------------------------------------------------------------------------------------------------

## 7. Comm set and gates for GREEN (cheapest first; every pytest through the bounded runner, one process at
a time)

1. `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on the six edited app files and the test
   file; bytes > 127 count = 0 on result_gate.py and the test file; `git diff --stat` content-only.
2. The unit file alone, flag unset and with `ENABLE_RESULT_GATE=true` exported for that one call (bound 600).
3. The 4.1 / 4.2 files (1.10 runs 1-3 plus the NOT MEASURED list), flag unset; then the 4.1 files with the
   flag exported (each must stay green: the E1-E3 proof).
4. The local-.env hazard sweep: the route-heavy comm chunk (text_routes / image_routes / url_routes
   referencers) with the flag exported; every red file either joins an existing clean list (a 4.1 row added
   by the gate, never silently) or is named in the CLAUDE.md row as "never set in a local .env".
5. CI-order set: `tests/test_s80_b2_result_gate.py` + E1-E3 files + the 4.2 list, flag unset (bound 1200).
6. **Comm set = 182 files** (`<scratchpad>/b2/comm_set.txt`, measured at base): the module/symbol reference
   grep (138 files matching `result_gate|response_builder|text_routes|image_routes|url_routes|error_handler|
   build_comparison_response|_surface_comparison_failure|http_exception_handler|identify_and_compare|
   /text/compare|/image/identify|/url/compare|ENABLE_RESULT_STATUS_METADATA|ENABLE_RESULT_GATE`) UNION every
   source-scanning pin (tests that `os.walk` / `rglob` / `glob` or `read_text` / `open` paths under `app/`:
   incl. `tests/test_auth_error_log_hygiene.py`, `tests/test_events_allowlist_superset.py`,
   `tests/test_model_config.py`, `tests/test_model_config_enforced.py`, `tests/test_prompt_fence.py`,
   `tests/test_u3c_store_false_pin.py`, `tests/test_start_command*.py`,
   `tests/test_migration_index_predicate_immutability.py`, `tests/test_openai_key_log_hygiene_s69.py`,
   `tests/test_sentry_channels_u8d_unit.py`) UNION the CLAUDE.md readers (`tests/test_ci_gates.py`,
   `tests/test_behavior_dimension_translation.py`) UNION the SmartCompareApp-scanning backend tests (25
   files; the client-visible contract gains `reason`) MINUS the four `test_precommit_hook*.py`. No
   test-support module (`tests/_*.py`, conftest) is edited, so no importer union applies; if GREEN edits one,
   every importer joins the set (a missing file is a MAJOR). Eight chunks of <= 25 files, bound 1200, base
   -> head -> base, `comm -13` of the sorted FAILED node ids EMPTY; the cold-tiktoken pair recorded
   identically at base and head.
7. The mutation table (lock, byte copies, sha256 restore).
8. Secret / personal-value sweep over the added lines; `git status --short` shows only the intended files.

---------------------------------------------------------------------------------------------------

## 8. CLAUDE.md row and owner steps

### 8.1 The flag row (GREEN writes it after the B3 row; wording may be tightened, content may not)

**SESSION 80 flag (B2 RESULT-GATE, 2026-10-20; default OFF, read PER CALL; a new name, so unset in
production by construction (Railway not read); spec `.qa-s80/B2_UNIT_SPEC.md` of the unit worktree with its
review and rulings):**
- `ENABLE_RESULT_GATE` (B2, `app/services/result_gate.py::result_gate_enabled`, read per call as the FIRST
  statement of `result_gate_refusal` and of the camera block in `image_routes.identify_and_compare`, the
  first operand of the builder stamp, of `_surface_comparison_failure`'s reason arm and of the error
  handler's local twin). **Effect ON:** a comparison B1's assessment (`assess_result`, R-A4 / R-A5 / R0-5,
  computed by the gate itself, never read from `metadata.result_status`) does not support is NOT delivered:
  text POST/GET and URL compares answer HTTP 400 `code INSUFFICIENT_DATA` (build 3: "Thin data on that
  pair") with an additive `reason` in {placeholder_identity, same_identity, category_conflict, no_evidence};
  the stream's terminal pair is the existing INSUFFICIENT_DATA shape plus `reason`; the camera refuses
  BEFORE the paid compare with the existing `action:'error'` body (build 3: "Snap each product in its own
  photo") or, when exactly one of the pair is a placeholder and the other is not low-confidence, the
  existing `need_second_product` body, each with `reason` in {placeholder_identity, low_confidence (ANY
  low vision confidence), same_identity, category_conflict}; never `comparison_failed`, never a new code,
  never a 503. Every refusal refunds the reserved credit with the gate's `consumed_keys` (and the anonymous
  credit where debited) BEFORE the raise, never calls `record_lifetime_comparison`, writes no history row
  and writes ONE `search_logs` row `success=False`, `error_message="result_gate:<reason>"` (both W4-13
  states), plus one INFO `[RESULT_GATE] refused input=<type> reason=<reason>`. The builder stamps
  `metadata.product_categories` under this flag too, so `category_conflict` fires in every flip order (the
  revived cross-category rule; `detect_comparison_quality` Rule 1 stays dead). URL uses its own reading
  (page price on both sides, a numeric rating on both, or one real two-sided spec row; no category check).
  Delivered partials with coverage >= 1 are delivered and billed as today. **Flag OFF:** byte-identical
  (pinned by `tests/test_s80_b2_result_gate.py` P1-P8, the FY25 nine digests and the W4-13 flag-OFF
  ledger). **Sizing (offline, real predicate):** 1 of 36 corpus bodies refused (a schema-v1 junk row),
  0 of 26 real deliveries, 0 of 9 lane1; 3 of 16 camera rows are no_evidence but camera bodies are not gated
  after the compare. **Activation precondition:** App Store approval of build 3 (R-A2 order: after
  ENABLE_RESULT_STATUS_METADATA has measured the production `metadata.result_status` distribution for one
  canary window, and after VISION_IDENTITY_V2 / IMAGE_PIPELINE_V2 / CATEGORY_TRUTH / CLAIMS_PROVENANCE /
  URL_MODE_V2); the owner's explicit yes. **Canary:** the `[RESULT_GATE] refused` count per input and reason
  vs B1's non-supported share (text/stream/camera; not URL, Q3), the 400 INSUFFICIENT_DATA rate on
  /text/compare and /url/compare, the camera `action:'error'` rate, refunds == refusals, no history rows for
  refused queries. **Stated limits:** camera bodies thin after the compare are delivered (3/16 corpus rows);
  text/URL refusals come after the paid fan-out; the stream emits its intermediate events before the refusal
  terminal (build 3 never opens it); URL has no category check and does not catch a storefront-title name
  (B4's domain); B1's message counts deliveries only after the flip; never set the flag in a local `.env`
  (route tests with thin stub bodies go red; E1-E3 clean lists). **Rollback:** unset the variable (per call,
  immediate).

### 8.2 Owner steps (names only)

None to merge. After approval and the R-A2 predecessors: read B1's `comparison_result_status` messages
(text, text_stream, camera) for one window; flip `ENABLE_RESULT_GATE` on `web` with the owner's yes; watch
the canary items; rollback = unset.

---------------------------------------------------------------------------------------------------

## 9. Stated limits

- L1 Camera bodies that are thin AFTER the compare (no_evidence) are delivered as today (3 of 16 corpus
  camera rows); refusing them needs a copy that build 3 does not have (Q1).
- L2 URL: no `category_conflict` (per-product categories are overwritten at `url_extraction_service.py:641-642`
  and the envelope has no `metadata`); a name equal to the storefront title is not a placeholder here (no
  site title in the envelope; B4's UNRESOLVED_PRODUCT covers it under URL_MODE_V2); the URL reading counts a
  page price as evidence.
- L3 Stream: `scores`/`verdict` frames precede the refusal terminal; the terminal decides. Build 3 never
  opens the stream.
- L4 Text and URL refusals happen after the paid fan-out (spend is not saved); a pre-fetch identity check on
  the text path is a follow-up (Q4). The orchestrator's post-build fire-and-forget behaviour-profile update
  (scs `:4694-4699`, `:5499-5504`) still runs for a refused compare.
- L5 B1's `comparison_result_status` message fires on delivery exits only, so after the B2 flip refused
  compares are counted by the `[RESULT_GATE]` lines and the `result_gate:<reason>` rows, not by B1 (Q5).
- L6 The B2 row is written in both W4-13 states, so on the URL route it is the one row written while W4-13
  flag 1 is OFF (Q6).
- L7 Existing non-B2 exits keep the legacy refund without keys (B4-R6 scope).
- L8 Camera category: V2 `_category` when present, else the name stub; B1's camera stamp uses the stub only,
  so with V2 ON the B1 canary and the B2 camera decision can differ on a pair the vision labels differently
  (Q7).
- L9 The gate inherits B1's predicate limits (the stub recognises generic category words only; the tier-3
  exclusion; the AUDITABLE reading).
- L10 `/text/quick` (admin-only, no app caller) is not gated.
- L11 A mid-request flip can split one request (2.13 last row).
- L12 Never set the flag in a local `.env` (4.1, 7.4).
- L13 History keeps no trace of a refused compare (intended, MYEZ-027).
- L14 MYEZ-007 (typed input never resolves a model) is closed only in its refusal half; the candidates route
  is a follow-up after approval.

## 10. Out of scope

The orchestrator (no edit), `detect_comparison_quality` Rule 1, `url_extraction_service.py` and the URL
pre-gate / typed codes (B4), any client file and the C1 copy for `reason`, the vision prompt (B3), B1's
emitter and its URL calibration (Q3), `/text/quick`, the refund keys of the existing exits, a pre-fetch text
refusal, any OpenAPI change (R0-6: none).

## 11. Open questions for the orchestrator

- Q1 Camera thin-after-compare: deliver (this spec) or refuse with `action:'error'` (copy says "Snap each
  product in its own photo", misleading for a data gap)? Recommendation: deliver until C1.
- Q2 One placeholder on the camera: `need_second_product` (this spec, "We spotted one product") or always
  `action:'error'`?
- Q3 B1's URL telemetry over-reports `partial_no_winner` for priced URL pairs (1.12); a B1 follow-up to use
  the URL reading in `capture_result_status(result, "url")`?
- Q4 A pre-fetch identity refusal on the text path (B2b) to save the fan-out spend?
- Q5 Should the B2 exits also emit B1's message (canary continuity) under B1's flag?
- Q6 The URL refusal row in both W4-13 states (this spec) or only under W4-13 flag 1?
- Q7 Camera category source: vision first (this spec) or the stub only (equal to B1's stamp)?

Not done in this spec: no code, no test file, no CLAUDE.md edit; the RED file, the GREEN change, the
adversaries, the comm-set runs and the mutation table are later phases. The NOT MEASURED files of 1.10 are
RED's first job.
