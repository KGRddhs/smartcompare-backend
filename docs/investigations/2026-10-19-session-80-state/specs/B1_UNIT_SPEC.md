# B1 unit spec (measured): RESULT-STATUS + TELEMETRY (measure before enforce)

Unit B1 of PLAN_S80.md section 3 (batch 1), as amended by RULINGS_R0.md R0-1, R0-2, R0-4, R0-5, R0-6
(B1-TIMINGS), R0-7. Flag `ENABLE_RESULT_STATUS_METADATA` (default OFF, read per call, the first statement
of every new predicate). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s80-b1`, branch
`feature/s80-result-status-metadata`, base `81df2b641454e0301cca51a3ba01bf8ef3d7e649` (HEAD == base ==
origin/main; `git status --short` empty at 23:19 AST on 2026-10-19 and again after every probe in this
spec; nothing was written to the worktree except this file under the gitignored `.qa-s80/`). Every
`file:line` below was read at the base sha in this run (2026-10-19 23:19-23:45 AST); resolve by symbol
if a line moves. Measurement location: `<scratchpad>/B1/` (notes.md, base_r1..r3.log, the pretty-printed
digests). Evidence pointers: PLAN_S80.md sections 0, 1, 3 (B1), RULINGS_R0.md, DEFECT_LEDGER.md rows
MYEZ-002/003/004/011/012/015/022/023/027, `runs/research/contract_freeze.json` (findings 1, 3, 4, 5a,
5b), `runs/research/eval_regression.json` (T03, T04, T05, T10, the V09 and V07 shapes),
`runs/research/identity_winner.json`, `runs/r0/abstain_tally.json` (the AUDITABLE vs LITERAL tally and
the quoted predicates), `runs/r0/openapi_pins_and_timings.json` (B1-TIMINGS), `runs/r0/url_history_camera_rows.json`
(R0-1), `runs/r0/feedback_and_allowlists.json` (R0-2). Sister units and contracts: B2 RESULT-GATE
(ENABLE_RESULT_GATE) consumes `assess_result` and `metadata.product_categories`; B3 VISION-IDENTITY-V2
threads the vision confidence into `assess_result(vision_confidences=...)` (accepted, unused here); B4
URL-MODE-V2 keeps the URL envelope WITHOUT `metadata` (R0-1), so B1 never stamps it; C1/C6/C7 are the
client halves (status UI, feedback chips, scan events) and C7 fires the event names this unit allowlists.
Personal-data rule: no real name, email, phone, Apple id, device id, address or account id in any file,
test, fixture or log line; synthetic values built at run time where a shape matters; the added-line sweep
(@gmail, +973, 8-digit runs, key shapes) runs over the GREEN diff. Pure ASCII and LF in every file this
unit writes (this spec: 0 bytes > 127).

---------------------------------------------------------------------------------------------------

## 0. What the unit does (one paragraph)

Under a new dark flag, every text and camera comparison body built by `build_comparison_response`
carries an honest machine-readable verdict about itself: `metadata.result_status` (R-A4 vocabulary),
`identity_confidence`, `data_coverage` (the AUDITABLE count of discriminating facts, R0-5) and
`data_coverage_literal` (the literal count, so production sizes the gap), `product_categories` (the
per-product categories captured BEFORE the pair-category write-back, so B2's cross-category rule can
fire again), `section_status` (specs / reviews / pros_cons / price each available | partial |
unavailable, MYEZ-022), `overview.winner.supported` (bool), and `metadata.winner_index = None` on every
non-supported body (B1 is the first writer of that key, so the stored row and the History list stop
presenting an unsupported result as a decision, MYEZ-027); `home_routes` skips stamped non-supported rows
from the savings aggregate (never via `winner_index`). The same flag emits ONE PII-free Sentry info
message per delivery exit (text POST, text GET, stream complete, camera success, URL success) carrying
enum/int tags only, writes `vision_ms` / `vision_moderation_ms` / `compare_ms` into an EXISTING
`metadata.stage_timings_ms` dict on the camera body (R0-6 B1-TIMINGS), and installs a `traces_sampler`
that samples the compare routes at 1.0 (everything else keeps today's 0.1 / parent decision). Nothing
abstains (B2); nothing changes for build 3 (every new key is additive and ignored, contract_freeze 5b);
flag OFF is byte-identical on every body and stored row. Unflagged per R-A1(a) and R0-2: the two
allowlists widen (six `scan_*` / `image_load_failed` event types, six `mattered_most` values) and
`FeedbackRequest` gains the three optional 027 columns written only when sent. The pure module
`app/services/result_gate.py` holds every predicate, so B2 enforces exactly what B1 measured.

---------------------------------------------------------------------------------------------------

## 1. Base state (measured at 81df2b64)

### 1.1 The one stamping site and its callers

| What | Where | Measured fact |
|---|---|---|
| Builder | `app/services/response_builder.py:1451` `build_comparison_response(*, product_data, products, comparison, scoring_result, product_names, tradeoffs, confidence, verdict_validation, user_preferences, from_cache, query, region, category_used, category_switched, original_category, total_cost, api_calls, gpt_calls, serper_calls, elapsed_seconds, metadata, cohort_summary, openai_usage, _single_margin)` | keyword-only; every kwarg defaulted (:1452-1476). 2,262 lines. |
| `metadata.query` | `:2060-2061` | the ONLY writer of `metadata.query` (R0-1); `_validate_renderable` (`database_service.py:303-321`) requires it, so every persisted text/camera row passed through this function. |
| Caller override | `:2109-2112` | `if openai_usage is not None: result["metadata"]["openai"] = ...`; `if metadata: result["metadata"].update(metadata)` -- the caller's keys win. |
| Post-override additive keys | `:2115-2116` (`verdict_scrubbed`), `:2119-2120` (margin) | the precedent for flag-ON-only additive keys written after the merge. |
| `overview.winner` | `:1897-1904` | keys `product_index, name, declaration, reason, key_tradeoff, margin`; no `supported`. |
| Alias loop / exit | `:2160-2231` products alias, `comparison` alias, `recommendation`, `key_differences`, `result["winner_index"] = winner_index` (:2231), `category_used`, `personalized`, `tier_context`; `_strip_inference_markers(result)` + `return result` (:2259-2262) | the B1 stamp block goes between `tier_context` and `_strip_inference_markers` (section 3 step 3), so `_field_confidence` (tier-3 markers) is still readable and every alias is already in place. |
| Three callers | `structured_comparison_service.py` (scs) `:3783` (`_build_partial_response`, def :3701), `:4571` (REST, `_compare_from_text_impl` def :4092), `:5411` (stream, `compare_from_text_streaming` def :4685) | all three pass `query=`, `category_used=`, `metadata=` (the partial passes `{"partial": True, "partial_stage": ..., "category_used": ...}` :3812-3816). Each is followed by `attach_data_freshness_notice` and `self._stamp_unit_metadata(result)` (:3826-3827, :4604-4605, :5444-5445) and, when `orchestrator_timings is not None`, `result.setdefault("metadata", {})["stage_timings_ms"] = orchestrator_timings` (:4612 REST, :5452 stream). |
| Pair category write-back | scs `:4276-4297` (REST), `:4908-4912` (stream) | `category_used, category_switched, original_category = await _resolve_pair_category(products, selected_category, parser_path=_parser_path)`; then `for _p in products: _p["category"] = category_used` (:4295-4296 REST, :4911-4912 stream). After this the per-product category is lost; `_fetch_product_data`'s `result` dict copies it (six identity keys). `_partial_build_ctx.update({...category...})` at :4284-4288 / :4923-4927. |
| Per-product category before the write-back | vision path scs `:4210-4224`: `category = classify_category_from_text(f"{brand} {vname}")` per product (the deterministic stub; `vp.get("confidence")` is NOT copied -- `identity_winner.json`: "the vision confidence is dropped"); explicit pair: the same stub per half; parser path: the LLM's per-product `category`. `_resolve_pair_category` :430-494 (R0-4). | `canonicalize_category` / `classify_category_from_text` are imported in scs at :27-28. |
| Camera post-build stamping | `app/api/image_routes.py:482-495` | `result["metadata"]["input_method"] = "camera"`, `vision_cost`, `total_cost` += vision_cost, `identified_products`; the else-branch (:490-494) creates a metadata dict WITHOUT `query` (failure envelopes only). `result["action"] = "comparison"` :498. |

### 1.2 Delivery exits and what each body carries

| Exit | Where | Facts |
|---|---|---|
| text POST | `text_routes.py:576` route; `_surface_comparison_failure` :694-696 (a `success:False` result is raised or returned here); `log_search` :708-716; save :718-760 (ENABLE_COMPARISON_ID_ECHO arms); lifetime :762-766; `return result` :768 | `input_type="text"` in `log_search`; `result["metadata"]["elapsed_ms"]` present (builder :2063). |
| text GET | `:771`; the same shape; `return result` :951 | `input_type="text"`. |
| stream complete | `:954`; `finally` :1217; gate `if complete_response and not had_error and not complete_after_client_gone:` :1220; W4-13 T3 failure row for `success is False` :1221-1241; success row :1250-1259 (`input_type="text_stream"`); save :1270-1294; lifetime :1296-1299 | a terminal whose client left before it (`complete_after_client_gone`) is NOT a delivery (M18 CD-interactions-01). |
| camera success | `image_routes.py:160-162` route; `start_time = time.time()` :178; `identify_products` :310; moderation :368; `vision_cost` :399; compare :450; `unsuccessful_not_billed` :467-469; the unsuccessful branch :503-534 returns before the save; success `log_search` :540-551 (`input_type="camera"`); save :553-560 (NOT behind metering, R0-1); lifetime :565-569; `return result` :579 | `metadata.stage_timings_ms` exists on the body only when scs created it (DEBUG_STAGE_TIMINGS memo true at :1066-1075). |
| URL success | `url_routes.py:118` `_compare_urls_metered`; `compare_from_urls` :158; save behind metering :199-206; lifetime :207-211; success row :213-218 (`input_type="url"`); `return result` :219 | the envelope has NO `metadata` and NO `scoring_v2` (`url_extraction_service.py:681-690`, R0-1): keys `success, products, comparison, winner_index, recommendation, key_differences, category_used, source_urls`. B4 keeps it so; B1 reads it for telemetry only and never writes to it. |

### 1.3 Readers of a stored row's winner

| Reader | Where | Fact |
|---|---|---|
| History list | `history_routes.py:33-43` `_extract_winner_index`: `metadata.winner_index` when the key is PRESENT (:38-39, `in` check, value may be None), else `comparison.winner_index` (:41-42), else None; list item :109-121; images `_extract_winner_runner_up_image_urls(full, winner_index)` :73-74 returns `(None, None)` when the index is not 0/1 | no code writes `metadata.winner_index` today (grep app/: the reader only). Pinned at `tests/test_history_routes.py:314-440` (metadata path, comparison fallback, null when neither, null when `full_response` None). The present-with-None case is NOT pinned (section 5, P7). |
| Home savings | `home_routes.py:151-176` `_extract_winner_loser_prices(full_response)`: top-level `full_response["winner_index"]` (:163) must be 0/1, both prices BHD; select :253, call :267; the #116 RPC branch (:949+, `ENABLE_HOME_SAVINGS_AGGREGATE`, migration 036 unapplied) bypasses Python | pinned `tests/test_home_routes.py:147-270` (`_comparison_row` fixture :87-135 builds `{winner_index, products, scoring}`). |
| Home smart pick | `home_routes.py:520-610` `_select_smart_pick`: `winner_idx = full.get("winner_index")` :542 (eligibility) and :596 | pinned `tests/test_home_routes.py:271-860`. |
| Profile recent decisions | `profile_routes.py:75, :97, :141` top-level `winner_index` | NOT touched by B1 (section 9 L13, question Q7). |
| Save gate | `database_service.py:303-321` `_validate_renderable` (two named products + `metadata.query`); `save_comparison` :413, refuse :431-447 | B1's keys do not touch it. |

### 1.4 Telemetry surfaces at base

- `comparison_wall_time` exists ONLY on the client: `SmartCompareApp/src/lib/performance/wallTimeInstrumentation.ts:92-114` `Sentry.captureMessage('comparison_wall_time', {level: 'info', tags})` with `wall_time.<stage>_ms` string tags; `ResultsScreen.tsx:489`. The backend has no `capture_message` on any compare path (grep app/: `api_budget_service.py:469` is the only call, a budget warning). `feedback_routes.py:56` and `tests/test_events_allowlist_superset.py:116-121` pin that `comparison_wall_time` is NOT an `/events` type.
- Sentry init: `sentry_service.py:616` `init_sentry()`, `sentry_sdk.init(...)` :664-684 with `traces_sample_rate=0.1` (:667), `send_default_pii=False`, `include_local_variables=False`, `max_request_body_size="never"`, `trace_propagation_targets=[]`, the three hooks. No `traces_sampler`. Module-level: stdlib only (`os, re, sys, copy, logging, urlsplit`); `sentry_sdk` is imported inside `init_sentry`.
- Camera traces: R0-7 -- zero of a 10 % sample in 30 days; the only camera latency evidence is the client message. This unit is what makes it observable.

### 1.5 The flag-reader idiom and the knob rules

House idiom (s80-common, scs `_flag_on` :1760-1761 in the S78-F8 spec; `apple_siwa_service.apple_token_revocation_enabled` in B3-B):
`os.getenv("ENABLE_RESULT_STATUS_METADATA", "false").strip().lower() in ("true", "1", "yes", "on")`, read per call, never cached, the FIRST statement of every new predicate so OFF reads no state. B1 has no numeric knob. `DEBUG_STAGE_TIMINGS` (scs `_debug_timings_enabled` :1068-1075) is PROCESS-CACHED in `_DEBUG_STAGE_TIMINGS` (:1066; `== "true"` only, no strip/lower); tests reset `scs._DEBUG_STAGE_TIMINGS = None` (`tests/test_stage_timings.py:20, :108`). Production runs `DEBUG_STAGE_TIMINGS=true` (CLAUDE.md "Optional" env vars, "true since Sprint A"; R0-6), so a presence-only timing rule would change production camera bytes at merge: the write is gated on the flag AND the key's presence (B1-TIMINGS).

### 1.6 Libraries on the pinned venv (measured)

- `sentry-sdk==2.68.1` (requirements.txt:142; installed 2.68.1). `sentry_sdk.capture_message(message, level=None, scope=None, **scope_kwargs)`; `Scope.update_from_kwargs(user, level, extras, contexts, tags, fingerprint, attributes)` -- `tags=` is accepted. `traces_sampler` is a `ClientConstructor` option. Sampling precedence (`sentry_sdk/tracing.py:1176-1250` `_set_initial_sampling_decision`): a forced `sampled` first; else `traces_sampler(sampling_context)` when callable (a raising sampler falls back to `parent_sampled` else `traces_sample_rate`); else `parent_sampled` when not None; else `traces_sample_rate`. The ASGI middleware (`integrations/asgi.py:224` `span_streaming = has_span_streaming_enabled(client.options)`, false unless `trace_lifecycle == "stream"` -- not set by `init_sentry`) takes the legacy branch: `start_transaction(transaction, custom_sampling_context={"asgi_scope": scope})` (:321-328) and `scope.py:1182-1186` builds `sampling_context = {"transaction_context": transaction.to_json(), "parent_sampled": transaction.parent_sampled, **custom_sampling_context}`. So the sampler sees `sampling_context["asgi_scope"]["path"]` (the raw request path; the `endpoint` name is resolved later by Starlette, `asgi.py:462-479`).
- `pydantic 2.13.4` (R0-2): `FeedbackRequest` has no `model_config`, extra keys are ignored (route-level pin `tests/test_feedback.py:356-365`); `Optional[Literal[...]] = None` 422s an off-enum value.
- `text_sanitize.dedup_brand_name` (:24-60): measured outputs -- `("Unknown", "Unknown Product") -> "Unknown Product"`, `("", "Unknown Product") -> "Unknown Product"`, `("Unknown", "") -> "Unknown"`, `("Unknown", "Unknown") -> "Unknown"`, `("GUESS", "GUESS!") -> "GUESS GUESS!"`, `("Manama Pickles", "Manama Pickles Achbara Sauce") -> "Manama Pickles Achbara Sauce"`, `("", "Iphone 17") -> "Iphone 17"`.
- `price_service.is_price_showable(product_name, price, category=None, *, enforce_correctness=False)` (:1801-1905): False when not a dict, amount not a positive number, `source_method` not in `_showable_source_methods()` (= `_GENUINE_BH_SOURCE_METHODS | {"converted_usd"}`, :1763-1764; `estimated` is excluded), the fragrance/haircare/high-value guards, sample/decant; with `enforce_correctness` also `in_stock False`, listing URL, no identity+url, device accessory (stamps `price["guard_rejected"]`, a MUTATION). The builder's chokepoint (:1700-1756) pends every non-showable price to `make_pending_price(...)` (amount None, `unavailable True`) BEFORE the stamp site, so at the stamp a price is showable iff it still has a positive amount and is not `unavailable` -- the pure structural predicate of 2.3 (a) equals the chokepoint verdict by position; no second `is_price_showable` call is needed (no re-mutation).
- `scoring_service`: `MISSING_SCORE = 50` (:297); `_NEUTRAL_DISPLAY_SCORE = 75` (:3168); `_CALIBRATION_FLOOR = 60`, `_CEILING = 95` (:3122-3123); `_dim_price` / `_dim_reviews` / `_dim_value` (:3240-3416) emit `confidence` in {high, medium, low} and `caption_key: "limited_data"` on the missing-data path with 75/75; `_dim_from_category_lookup` (:3511-3560) reads RAW `scores.product_i.breakdown[<dim>_score]` (the 50 sentinel is visible there: w412 row 24 `review 50/90.0`); `build_dimensions_v2` (:3848) = 3 core + up to 5 category dims; `scores.product_i.missing_data` lists the sentinel dims (:1543). `response_builder` imports `MISSING_SCORE, build_dimensions_v2, calibrate_score, compute_confidence, confidence_single_computation_enabled, count_missing_dim_cells` (:11-18) and `has_score_internals, strip_score_internals, scrub_review_summary` (:19).
- `response_builder._SPEC_INTERNAL_FIELDS = {"_field_confidence", "_internal", "_extraction_metadata"}` (:617-621), `_SPEC_NA_TOKENS = {"n/a", "na", "none", "unknown", "-", ""}` (:625); `_build_specs_rows` (:725-762) emits one row per field BOTH products populate, skipping only `None`/`""` -- an `"N/A" vs "N/A"` row IS emitted (R0-5 surprise; w412 rows 12-19 and 22-25 carry 7/7 `"N/A"` specs). `_strip_inference_markers` (:1417-1445) drops `inference_source*` keys and `"model_knowledge"` values at the exit. Tier-3 marker: `specs["_field_confidence"][field] == "tier3_synthesis"` (scs :827, :859, :3403-3445, :6308).
- `extraction_service.CATEGORY_SPEC_SCHEMAS` (:142) keys = the nine categories; `_CANONICAL_CATEGORIES = frozenset(CATEGORY_SPEC_SCHEMAS.keys())` (:1160); `canonicalize_category` :1217; `classify_category_from_text` :1307. R0-4: all nine are supported; `unsupported_category` means "not one of the nine".

### 1.7 Guards the new code must not trip

- `tests/test_sentry_channels_u8d_unit.py::TestOptions::test_u8d_pin_options_init_kwargs_kept` (:644-656) asserts `kw["traces_sample_rate"] == 0.1`, the three hook names and the 503 exclusion -- B1 KEEPS `traces_sample_rate=0.1` and ADDS `traces_sampler=`; `test_observability.py:272` and `test_retro_w1_1.py:242` assert the same 0.1. `test_u8d_red_r8_*` (R8): no ERROR-level log outside an except arm with user content; B1 logs nothing new at ERROR (one WARNING by type in the emitter's except arm).
- `tests/test_sentry_channels_u8d_unit.py` AST pins over `app/`: every log template with constants/ints/type names only. B1's two lines (2.8) comply.
- `tests/test_events_allowlist_superset.py:97-121`: the seven names stay, `comparison_wall_time` stays out, `hacker_event` still 422 (`test_feedback.py:235-240`); `tests/test_feedback_allowlist_superset.py:126-184`: the seven original values stay, `bogus` still 422.
- `tests/test_w4_13_flag_off_ledger.py`: records the fire_and_forget LABEL sequence and `log_search` kwargs at every exit with every W4-13 flag unset -- B1 adds NO `fire_and_forget` call and NO `log_search` kwarg on any exit in either flag state (the emitter is a direct, synchronous `capture_message` inside try/except).
- `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main` (:270-277): nine normalised digests (REST/stream full, pair, partial-at-gather, parse-failure, private marks); `VOLATILE` drops only clock fields and `stage_timings_ms` (:66-68) -- any new metadata key with the flag OFF moves a digest. `UNIT_ENV` (:60-63) is popped per scenario; B1 adds `ENABLE_RESULT_STATUS_METADATA` to that tuple (section 4.1 E1).
- `tests/test_s71_u13_compare_auth_required.py` T17/T23 (UR11 fixture): no new route parameter or body field on the ten paid operations (ruling T23); `FeedbackRequest` is outside the ten-operation `$ref` closure (R0-2), so the three optional fields do not touch T23. `tests/test_paid_route_metering.py` camera pins stub `StructuredComparisonService` (`_stub_camera` :256-310, body `{success, products, metadata: {total_cost: 0.01}}`) and assert `action` / `success` / `metadata.input_method` / ledger calls only.
- `tests/test_stage_timings.py:85-99` asserts the expected `stage_timings_ms` keys as SUBSETS (extra keys pass) and `:163-164` asserts the key's ABSENCE with the memo off; `tests/_env_safety.CREDENTIALS_UNSET` strips `SENTRY_DSN` (:110-112), so no Sentry client exists in any test process: the emitter is observed by patching `sentry_sdk.capture_message` (the harness of 5.1).
- `tests/_netguard`: `result_gate` imports nothing that resolves a host; `sentry_sdk.capture_message` without a client is a no-op.
- The pre-commit hook: no `sk-` + 20 chars, no JWT shapes, no credentialed URLs in any new file; every sentinel built at run time.
- Backend files are CRLF in the working copy, LF in the index (`git ls-files --eol`: `i/lf w/crlf` for every file in section 3); the Edit tool preserves CRLF; a whole-file diff is a defect. The two NEW files (`result_gate.py`, the tests) are written LF (the index form) -- `core.autocrlf=true` normalises on add.

### 1.8 Fixtures measured for RED

- `tests/fixtures/w412_corpus_min.json`: 27 rows `{row, created_at, input_type, schema_version, product_names, full_response}` (camera 16 / text 7 / text_stream 4). Rows 12-14 (Manama Pickles, camera): `products[]` both `price {amount 2.25, source_method "estimated", estimated True}`, `rating 3.8` with `rating_derived True` at `products[]` (the `overview.products[]` mirror shows `rating_derived None` because the stored overview projection predates the A5 null), `review_count None`, `image_url None`, `specs` 7/7 `"N/A"`, `pros` 3-4 / `cons` 2-3, `reviews.review_summary` present; `scoring_v2.dimensions` `[('price',85,85,'high',None), ('reviews',84,84,'high',None), ('value',88,88,'medium',None)]` (all ties); `scoring.scores` 57.3 / 57.3 with `missing_data ["review_score", "feature_match_score"]`; `winner_index 0`, `overview.winner.margin 0.0`, `comparison.specs_comparison` prose lists present; `metadata` keys `comparison_quality, partial` only (no `query` in the minimised corpus). Row 24 (partial, `metadata.partial True`): prices None, one derived rating, three `limited_data` core dims at 75/75 plus legacy category dims `function 65.0/50, review 50/90.0, reliability 65.0/90.0, feature_match 50/100`. Row 26 (partial): `character 55.9/74.1, longevity 55.9/74.1` on smart_fallback / tier3 specs. Rows 15-19 (text_stream, June 2026): brand `""` on both products with full coverage (`price local_bhd`, `rating 4.4` real, `review_count 24000`, `image_url` str).
- `tests/fixtures/lane1/*_response.json` (9): full response shape (`products, overview, specs, reviews, scoring, scoring_v2, comparison, metadata` with `query`); `grocery`: `Bertolli` vs `Carbonell` both named `Extra Virgin Olive Oil` (local_bhd 1.26 / 3.56, ratings 4.9 / 4.8 real, 13 specs each, dims price 85/75 high, reviews 90/89 high, value 88/76 medium); `now_vs_solgar`: `NOW Foods` vs `Solgar` both `Vitamin D3` (converted_usd 3.35 / 5.597); `tomford_vs_creed` (local_bhd 20.68 / 86.48, 10-11 specs); `iphone15_vs_galaxys24` (4 dims incl. popularity 77/88).
- `runs/r0/abstain_tally.json` (script `r_a4_tally.py`, predicates quoted there): AUDITABLE coverage 0 on w412 rows 6, 12, 13, 14 (4/27 = 14.8 %; camera 3/16), lane1 all 3-4; LITERAL coverage 0 on row 6 only; placeholder on brand alone would wrongly fire on rows 15-19; name-only same_identity would wrongly refuse `grocery` and `now_vs_solgar` (Jaccard 1.0 on the name); the highest in-corpus Jaccard is 0.714 (row 26 `OUD VOYAGER` vs `OUD WOOD`).
- Tester shapes (eval_regression T03/T04/T05): V09 = two products named `Unknown Product` (brand `""` or `Unknown`) with `winner_index 0`; V07 = vision `[{"brand": "GUESS", "name": "GUESS!", "size_or_count": None, "confidence": "medium"}] * 2`; V10/T04 = `('Hyper X MIC', 'Hyper X2 MIC')`, specs `{}` / all-dash, prices None, ratings None, `factual_verdict.line1 "... edges ahead on the overall picture."`.
- The FY25 harness `tests/test_s75_fanout_identity.py::_install` (:130-230) runs the REAL `compare_from_text` / streaming with every leaf faked (parse, verdict, search, specs, price, reviews, rating, refill tiers, image, moderation) and real scoring; `_scenario(kind, query, *, cap, explicit_pair, slow, parse_extra, env)` (:233-268) pops `UNIT_ENV` and applies `env`; its specs/price/rating fakes produce a supported result (local_bhd 120.0 both, rating 4.5 both, 3 specs each). RED reuses it for the route-free orchestrator rows and the FY25-style digest PINs.

### 1.9 Line endings

Every file in section 3 is `i/lf w/crlf` (`git ls-files --eol`). New files are written LF. `git diff --stat` after GREEN must show content lines only.

### 1.10 Base pass state (bounded runner, one process at a time, every unit flag unset)

Three runs at base (the files B1 pins or whose readers it edits), logs in `<scratchpad>/B1/`:

```
run 1  tests/test_feedback.py tests/test_events_allowlist_superset.py tests/test_feedback_allowlist_superset.py
       tests/test_history_routes.py tests/test_home_routes.py
       collected 119 items; 119 passed, 10 warnings in 10.25s
       [hermeticity] sentinel checked 119 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
       [pyt] tag=b1-base-r1 start=2026-10-19 23:30:58 end=2026-10-19 23:31:11 elapsed=13s bound=600s status=OK rc=0
run 2  tests/test_s75_fanout_identity.py tests/test_stage_timings.py tests/test_w4_13_flag_off_ledger.py
       collected 7 items; 7 passed, 10 warnings in 11.06s
       [hermeticity] sentinel checked 7 test(s); [netguard] blocked 18 attempt(s) from 2 node(s)
         (tests/test_stage_timings.py::test_stage_timings_present_when_flag_on and ::_absent_when_flag_off,
          [egress] socket.getaddrinfo api.openai.com:443 -- their existing baseline behaviour, blocked)
       [pyt] tag=b1-base-r2 start=2026-10-19 23:31:44 end=2026-10-19 23:31:59 elapsed=15s bound=600s status=OK rc=0
run 3  tests/test_sentry_channels_u8d_unit.py tests/test_observability.py tests/test_retro_w1_1.py
       tests/test_paid_route_metering.py
       collected 225 items; 225 passed, 13 warnings in 15.06s
       [hermeticity] sentinel checked 225 test(s); [netguard] blocked 2 attempt(s) from 2 node(s)
         (test_paid_route_metering.py::test_camera_success_consumes_once_and_never_refunds and
          ::test_url_compare_saves_history_with_input_type_url, [sentinel] neutralized.supabase.invalid:443 --
          the ratchet baseline's `sentinel` class, tests/.network_attempt_baseline.txt:93)
       [pyt] tag=b1-base-r3 start=2026-10-19 23:32:30 end=2026-10-19 23:32:46 elapsed=16s bound=600s status=OK rc=0
```

The runner prints no per-file progress lines, so the per-file split is: run 1 = test_feedback (the route + service nodes), the two allowlist superset files, test_history_routes (incl. the four winner_index nodes :371-436), test_home_routes (savings 4 + smart-pick + images + #116); run 2 = the three FY25 nodes, the two stage-timings nodes, the two ledger nodes; run 3 = the 141 U8d unit nodes (per the B3-B 1.10 table) + observability + retro W1-1 + metering. Zero failures, zero errors at base in the files this unit touches or pins. NOT MEASURED at spec time (RED's first job): `tests/test_s71_u13_compare_auth_required.py` (T17/T23), `tests/test_w4_13_measurement_truth.py`, `tests/test_comparison_id_echo.py`, `tests/test_camera_vision.py` (3 pre-impl reds), `tests/test_image_routes*.py`, `tests/test_url_*`, `tests/test_sentry_channels_u8d.py` (child-process half) -- all in the comm set of section 7.

---------------------------------------------------------------------------------------------------

## 2. Contract

### 2.1 Flag

`ENABLE_RESULT_STATUS_METADATA` (new; default OFF; the 1.5 idiom; the single reader
`app/services/result_gate.py::result_status_metadata_enabled()`, imported by `response_builder`,
`image_routes`, `text_routes`, `url_routes`, `sentry_service`). No knob. Read per call at every site; a
mid-request flip can produce a stamped body without a message or the reverse for one request (L12).

### 2.2 `app/services/result_gate.py` (new, pure)

Imports: stdlib (`re`, `typing`) and `from app.services.text_sanitize import dedup_brand_name` (a
regex-only module already imported by `response_builder`). Never imports `structured_comparison_service`,
`response_builder`, `price_service`, `extraction_service`, `sentry_sdk`, nothing that does I/O. Constants:

- `STATUS_SUPPORTED = "supported_result"`, `STATUS_PARTIAL = "partial_no_winner"`, `STATUS_NEEDS_ID = "needs_identification"`, `STATUS_UNSUPPORTED = "unsupported_category"`, `STATUS_FAILED = "failed"`; `STATUSES` = the five (R-A4).
- `CONFIDENCE_LEVELS = ("high", "medium", "low", "unresolved")`.
- `REASONS = ("not_success", "placeholder_identity", "same_identity", "unsupported_category", "category_conflict", "no_evidence")` (emission order).
- `CANONICAL_CATEGORIES = frozenset({"electronics", "grocery", "supplements", "makeup", "skincare", "haircare", "fragrances", "fashion", "other"})` -- a literal copy of `CATEGORY_SPEC_SCHEMAS.keys()`; PIN P12 asserts equality so drift is caught without importing `extraction_service` here.
- `PLACEHOLDERS = frozenset({"", "unknown", "unknown product", "n/a", "product", "this product"})` (R-A5; the site-title case is B4's: `is_placeholder_identity(text, site_title=None)` also returns True when `norm(text) == norm(site_title)` and `site_title` is non-empty).
- `NA_VALUES = frozenset({"", "n/a", "na", "none", "unknown", "-"})` (a superset of `response_builder._SPEC_NA_TOKENS`; PIN P12).
- `DIM_FLAGGED = frozenset({"missing", "limited_data", "tier3"})`, `DIM_MARGIN = 3.0`, `SENTINEL_SCORE = 50`.
- `SECTION_KEYS = ("specs", "reviews", "pros_cons", "price")`, `SECTION_STATES = ("available", "partial", "unavailable")`.

Functions (all total: a malformed input yields the conservative answer, never raises; every predicate
receives plain dicts/lists):

- `norm(text) -> str`: casefold, every run of characters outside `[0-9a-z\u0600-\u06ff]` becomes one space, collapsed, stripped (R0's `norm`).
- `identity_text(brand, name) -> str`: `dedup_brand_name(brand, name)` (R0-5: the identity, never the brand alone).
- `is_placeholder_identity(text, site_title=None) -> bool`: `norm(text) in PLACEHOLDERS` or (site_title and `norm(text) == norm(site_title)`).
- `product_is_placeholder(product) -> bool`: `is_placeholder_identity(identity_text(brand, name)) or is_placeholder_identity(name)` (name alone covered: brand "Unknown" + a real name is NOT a placeholder; brand "" + "Unknown Product" IS).
- `token_jaccard(a, b) -> float`: over `set(norm(x).split())`; both empty -> 1.0.
- `same_identity(p0, p1) -> bool` (R-A5 with the brand condition, R0-5): `norm(identity_text(b0, n0)) == norm(identity_text(b1, n1))` OR (`norm(b0) == norm(b1)` AND `token_jaccard(n0, n1) >= 0.9` AND no differing `variant` / `size` / `distinguishing_features` -- compare `norm(p.get("variant") or p.get("size_or_count") or "")` and `norm(" ".join(p.get("distinguishing_features") or []))`: when both products carry a non-empty value for the same axis and the values differ, NOT the same identity). Two placeholders are the same identity (and placeholder wins in the status order).
- `identity_coherence(product_categories, category_used) -> bool`: True unless BOTH per-product categories are non-empty strings, canonical (in `CANONICAL_CATEGORIES`), not `"other"`, and differ from each other (casefold/strip compare). `category_used` is accepted for the signature B2 needs but never makes a pair incoherent by itself ("other" never conflicts; a stub `other` beside a real category is coherent, R0-4's V06 walk). `None` / non-list input -> True.
- `price_is_showable(price) -> bool`: dict, `amount` is int/float (not bool) and > 0, `unavailable is not True`, `estimated is not True`, `source_method` is a non-empty str and != `"estimated"` (R0's `price_strict`; equals the chokepoint verdict by position, 1.6).
- `price_is_present_literal(price) -> bool`: R0's `price_task` (amount not None, not unavailable, source_method != "estimated", estimated not True; an EMPTY source_method passes).
- `rating_is_real(product) -> bool`: `rating` int/float (not bool) and `rating_derived is not True`.
- `real_spec_rows(specs0, specs1) -> int`: fields present in both dicts, key not starting with `_`, neither value `None`/`""`, neither value a str whose `norm()` is in `NA_VALUES`, and neither side's `_field_confidence.get(field) == "tier3_synthesis"` (R-A4: tier-3 is not evidence). Non-dict specs -> 0.
- `literal_spec_items(specs_comparison) -> int`: `len(product_0_advantages) + len(product_1_advantages) + len(similar)` over list values of a dict (R0's literal fact (c); the `rows` key is NOT counted, matching the tally).
- `dim_is_discriminating(dim, missing_data_keys, *, strict) -> bool`: `score_a` and `score_b` numeric (not bool); `caption_key` and `confidence` not in `DIM_FLAGGED`; `abs(a - b) >= DIM_MARGIN`; and when `strict`: `confidence != "low"`, neither score == `SENTINEL_SCORE`, and neither `key` nor `key + "_score"` is in `missing_data_keys` (the union of both products' `scores.product_i.missing_data`).
- `evidence_facts(result) -> dict`: `{"price": a_strict, "ratings": b, "specs": c_real, "dims": d_strict}` and `evidence_facts_literal(result) -> {"price": a_literal, "ratings": b, "specs": c_literal, "dims": d_literal}` from the BUILT body: products = `result["overview"]["products"]` else `result["products"]` (two needed, else every fact False); specs from `result["specs"]["products"][i]["specs"]` else `products[i]["specs"]`; dims from `result["scoring_v2"]["dimensions"]` when `scoring_v2` is a dict (None / {} -> no dims); `missing_data` from `result["scoring"]["scores"]`; prose lists from `result["comparison"]["specs_comparison"]` else `result["specs"]["specs_comparison"]`.
- `evidence_coverage(result) -> (int, int)`: `(sum(facts), sum(facts_literal))` -- `data_coverage` (AUDITABLE, R0-5 ruling) and `data_coverage_literal`.
- `section_status(result) -> dict`: per product i: specs_i = `real_spec_rows_one_side(specs_i) >= 1` (a field whose own value is not None/""/NA, `_`-keys skipped); reviews_i = non-empty `reviews.review_summary.consensus` str OR non-empty `reviews.retailer_quotes` list OR non-empty `review_praise` str OR (`rating_is_real` and `review_count` int > 0); pros_cons_i = `pros` or `cons` a non-empty list (on `overview.products[i]`, post-scrub); price_i = `price_is_showable(price)`. Each section: both True -> `available`; exactly one -> `partial`; none -> `unavailable`.
- `identity_confidence(products, *, same, coherent, vision_confidences=None, facts_per_product) -> str`: `unresolved` if any product is a placeholder; else `low` if `same` or not `coherent` or any provided vision confidence (casefold) == `"low"`; else `medium` if any `norm(brand) == ""`, or any vision confidence == `"medium"`, or any product has NO corroboration (not showable price AND no real rating AND no real spec on its side); else `high`. `vision_confidences` is `None` at base (dropped at scs:4210-4224); B3 threads it (Q2).
- `assess_result(result, *, product_categories=None, vision_confidences=None) -> dict`: returns `{"status", "reasons", "identity_confidence", "data_coverage", "data_coverage_literal", "section_status", "unknown_product_count", "same_identity", "coherent", "facts", "facts_literal"}`. Status precedence: `result.get("success") is not True` -> `failed` (`not_success`); any placeholder -> `needs_identification` (`placeholder_identity`); `same_identity` -> `needs_identification` (`same_identity`); `category_used` (= `result["category_used"]` or `result["category"]`) a non-empty str not in `CANONICAL_CATEGORIES` -> `unsupported_category` (`unsupported_category`); `identity_coherence` False -> `unsupported_category` (`category_conflict`); `data_coverage == 0` -> `partial_no_winner` (`no_evidence`); else `supported_result`. `reasons` lists EVERY applicable reason in `REASONS` order (telemetry), the status is the first in that order. `supported_result` is exactly R-A4's minimum evidence: coverage >= 1, confidence != unresolved, not same_identity, no category conflict (a partial crowns only on coverage >= 1).
- `telemetry_tags(result, input_type, *, assessment=None, vision_ms=None, compare_ms=None) -> dict[str, str]`: the 2.5 tag set, every value a short enum/int string.
- `stamp_camera_stage_timings(result, *, vision_ms, vision_moderation_ms, compare_ms) -> bool` (pure on the dict): flag read FIRST; then only when `result["metadata"]["stage_timings_ms"]` already exists and is a dict, write the three keys as ints (`None` skipped); returns whether it wrote. Never creates `metadata` or the dict (B1-TIMINGS).
- `result_status_metadata_enabled() -> bool` (2.1).

### 2.3 Stamping in `build_comparison_response` (flag ON only)

New keyword `product_categories: Optional[List[Optional[str]]] = None` (additive; ignored OFF). The block
sits after `result["tier_context"] = {...}` and before `_strip_inference_markers(result)`:

```python
# B1 (ENABLE_RESULT_STATUS_METADATA, default OFF, read per call): the honest status of this body.
if result_status_metadata_enabled():
    _rs = assess_result(result, product_categories=product_categories)
    _md = result["metadata"]
    _md["result_status"] = _rs["status"]
    _md["identity_confidence"] = _rs["identity_confidence"]
    _md["data_coverage"] = _rs["data_coverage"]
    _md["data_coverage_literal"] = _rs["data_coverage_literal"]
    _md["section_status"] = _rs["section_status"]
    if isinstance(product_categories, list) and len(product_categories) == 2:
        _md["product_categories"] = [c if isinstance(c, str) else None for c in product_categories]
    result["overview"]["winner"]["supported"] = _rs["status"] == STATUS_SUPPORTED
    if _rs["status"] != STATUS_SUPPORTED:
        _md["winner_index"] = None
```

Key types: `result_status` str in `STATUSES`; `identity_confidence` str in `CONFIDENCE_LEVELS`;
`data_coverage`, `data_coverage_literal` int 0..4; `section_status` dict of the four `SECTION_KEYS` ->
`SECTION_STATES`; `product_categories` list of two (str | None), present only when the caller passed a
2-list; `overview.winner.supported` bool; `metadata.winner_index` None, present only on a non-supported
body (absent on a supported one, so History keeps today's `comparison.winner_index` fallback). The
top-level `winner_index`, `overview.winner.product_index`, `scoring_v2.overall_score` and
`comparison.winner_index` are UNCHANGED in both states (build 3 crowns from them; B2 decides refusals).
The camera route's `identified_products` / `input_method` stamping (:482-495) runs after the build and
is untouched. `_strip_inference_markers` runs after the stamp (no new key carries the marker).

Per-product categories: scs captures `product_categories = [canonicalize_category(_p.get("category")) for _p in products]`
immediately BEFORE the write-back loops (:4295-4296 REST, :4911-4912 stream), stores it on
`self._partial_build_ctx["product_categories"]` beside `category_used` (:4284-4288 / :4923-4927) and
passes `product_categories=product_categories` to the REST (:4571) and stream (:5411) builds; the partial
build passes `product_categories=ctx.get("product_categories")` (:3783). The kwarg is passed in BOTH flag
states (byte-identical: unused OFF).

### 2.4 Readers: History and Home (unflagged readers keyed on the stamp; byte-identical on unstamped rows)

- `history_routes._extract_winner_index` is NOT edited: present-with-None already yields None (:38-39). PIN P7 freezes that the list item carries `winner_index: None` and `winner_image_url: None, runner_up_image_url: None` for a row stamped `metadata.winner_index: None` even when `comparison.winner_index` is 0 (the null-neutral render; the build-3 HistoryScreen then shows no winner highlight and the placeholder glyph on both tiles, contract_freeze 5b -- L6).
- `home_routes`: a module helper `_result_status_supported(full_response) -> bool` = `metadata.result_status` is absent OR == `"supported_result"` (a non-dict metadata counts as absent). `_extract_winner_loser_prices` returns `(None, None)` when it is False (before the `winner_index` read, :163, with a comment "never via winner_index"); `_select_smart_pick` `continue`s on it (before :542). The savings and smart-pick RPC/legacy selects are unchanged. The helper reads NO flag: a stamped row stays skipped after a rollback (it is still not a supported result), an unstamped row (every row written before the flip) counts exactly as today (PIN P8).

### 2.5 Telemetry: `sentry_service.capture_result_status(result, input_type, *, vision_ms=None, compare_ms=None) -> None`

Flag read FIRST (returns at once OFF). Then, inside ONE try/except: `assessment = assess_result(result)`
(URL bodies and stamped bodies alike -- the tags are recomputed from the body, never read from metadata);
`compare_ms = compare_ms if compare_ms is not None else metadata.elapsed_ms` (int when numeric);
`tags = telemetry_tags(result, input_type, assessment=assessment, vision_ms=vision_ms, compare_ms=compare_ms)`;
`import sentry_sdk; sentry_sdk.capture_message("comparison_result_status", level="info", tags=tags)`.
A no-op without a client (the SDK's own rule). The except arm logs ONE WARNING
`"[RESULT_STATUS] telemetry skipped: %s", type(exc).__name__` and returns. Never `fire_and_forget` (the
W4-13 ledger records label sequences; the call is synchronous and cheap), never raises, never awaits.

Tags (every value a str; a tag is OMITTED when its source is unknown, never `"None"`):

| tag | value |
|---|---|
| `input_type` | `text` / `text_stream` / `camera` / `url` (the `log_search` input_type of the exit) |
| `result_status` | the five statuses |
| `identity_confidence` | the four levels |
| `reasons` | the applicable reasons joined by `,`, or `none` |
| `unknown_product_count` | `0` / `1` / `2` (placeholders among the two products) |
| `winner_emitted` | `true` when status == supported_result (= `overview.winner.supported`), else `false` |
| `image_present_a`, `image_present_b` | `true` when `overview.products[i].image_url` (else `products[i].image_url`) is a non-empty str starting with `http://` or `https://` |
| `price_showable_a`, `price_showable_b` | `true` / `false` per `price_is_showable` |
| `partial_stage` | `metadata.partial_stage` when `metadata.partial is True` (gather / post_gather / scoring / verdict), else `none` |
| `data_coverage`, `data_coverage_literal` | `0`..`4` |
| `vision_ms`, `compare_ms` | `str(int)` when known (camera passes both; text passes `metadata.elapsed_ms`; URL passes the route's wall); omitted when unknown |

No product name, brand, query, URL, host, user id, request id, amount, or free text ever enters a tag or
the message (RED R16 asserts the key set and the value grammar `^[a-z0-9_,]+$` over every emitted tag).
The message text is the constant `comparison_result_status` (the `comparison_wall_time` pattern: a
constant name, tags only, level info). No `extras`, no `user`, no `fingerprint`.

Call sites (all delivery exits, each ONE call, after the metering/save block and immediately before the
`return`): `text_routes.py` POST :768 (`input_type="text"`), GET :951 (`"text"`), the stream `finally`
success branch after the lifetime block (:1299, inside `if complete_response and not had_error and not
complete_after_client_gone:` and only when `complete_response.get("success") is True`; `"text_stream"`),
`image_routes.py` :579 (`"camera"`, `vision_ms=`, `compare_ms=` the route's measured walls; NOT on the
`comparison_unsuccessful` paths, which are non-deliveries), `url_routes.py` :219 (`"url"`,
`compare_ms=int((time.time() - _start) * 1000)`). A `success:False` body never reaches these points
(text: `_surface_comparison_failure` :694-696 returns/raises; camera: the unsuccessful branch returns
:532-534 / the envelope :575-578 is excluded by `comparison_unsuccessful`; URL: :170-193).

### 2.6 Camera timings (B1-TIMINGS)

`image_routes.py` measures three walls with `time.perf_counter()` unconditionally (reads of a clock, no
state): `vision_ms` around `await identify_products(image_data_list)` (:310), `vision_moderation_ms`
around `await _safety.moderate_vision_output(vision_result)` (:368), `compare_ms` around
`await service.compare_from_text(...)` (:450). After the metadata stamping (:495) and before
`result["action"] = "comparison"` (:498): `stamp_camera_stage_timings(result, vision_ms=..., vision_moderation_ms=..., compare_ms=...)`
-- flag first, then ONLY into an existing `result["metadata"]["stage_timings_ms"]` dict (the dict scs
creates at :4612 when `DEBUG_STAGE_TIMINGS` is true), as ints. Flag OFF or dict absent: no write, no
new key, no new dict (R0-6: production runs `DEBUG_STAGE_TIMINGS=true`, so a presence-only rule would
change production camera bytes at merge). RED/PIN rows set or delete BOTH `ENABLE_RESULT_STATUS_METADATA`
and `DEBUG_STAGE_TIMINGS` explicitly and reset `scs._DEBUG_STAGE_TIMINGS = None`.

### 2.7 Traces sampler (`sentry_service.compare_traces_sampler`)

```python
_TRACES_SAMPLE_RATE = 0.1
_COMPARE_PATHS = frozenset({"/api/v1/text/compare", "/api/v1/text/compare/stream",
                            "/api/v1/image/identify", "/api/v1/url/compare"})

def compare_traces_sampler(sampling_context):
    try:
        if result_status_metadata_enabled():
            scope = sampling_context.get("asgi_scope") if isinstance(sampling_context, dict) else None
            path = scope.get("path") if isinstance(scope, dict) else None
            if path in _COMPARE_PATHS:
                return 1.0
        parent = sampling_context.get("parent_sampled") if isinstance(sampling_context, dict) else None
        return parent if parent is not None else _TRACES_SAMPLE_RATE
    except Exception:  # noqa: BLE001 -- a sampler must never raise
        return _TRACES_SAMPLE_RATE
```

`sentry_sdk.init(..., traces_sample_rate=0.1, traces_sampler=compare_traces_sampler, ...)` -- the rate
stays (the U8d / observability / retro pins read it) and the sampler returns exactly the SDK's rules 3/4
when the flag is OFF (`parent_sampled` else 0.1), so the sampling decisions are identical OFF. The
"three compare routes" = text (REST + its stream), camera, URL = the four paths above (Q4). A path is
matched on the raw ASGI `path` (no query string, no trailing-slash variant: a `/compare/` request is
the 307 redirect, not the compare).

### 2.8 Logging rules

Two templates only, both constants: WARNING `[RESULT_STATUS] telemetry skipped: <TypeName>` (the emitter's
except arm) and INFO `[RESULT_STATUS] camera timings written: vision_ms=%d moderation_ms=%d compare_ms=%d`
is NOT emitted (no new INFO line; the timings are in the body). No ERROR level. No value, name, URL or id
in any line.

### 2.9 Unflagged (R-A1(a), R0-2): allowlists and the three feedback fields

- `feedback_routes.VALID_MATTERED_MOST` (:44-48) gains, after `"fast"`, with the comment `# S80 C6 reason chips (MYEZ-023); a tap sends mattered_most: [chipKey]`: `"wrong_product", "missing_info", "unclear_reasons", "slow", "wrong_winner", "unsure"` (R0-2 decision: the third answer state ships as `mattered_most: ["unsure"]`).
- `feedback_routes.VALID_EVENT_TYPES` (:58-94) gains a new group with the comment `# S80 C7 camera loader stages + cancel (MYEZ-015) and the image failure signal`: `"scan_start", "scan_identity_resolved", "scan_comparison_ready", "scan_failed", "scan_cancelled", "image_load_failed"`. Append-only; nothing removed or renamed; `comparison_wall_time` stays out.
- `FeedbackRequest` (:97-118) gains `winner_correct: Optional[Literal["correct", "wrong", "unsure"]] = None`, `price_correct: ...`, `specs_correct: ...` (the live 027 columns' CHECK). `submit_feedback` (:174-183) passes `winner_correct=body.winner_correct, price_correct=..., specs_correct=...`; `feedback_service.save_feedback` (:194-240) gains the three `Optional[str] = None` kwargs and adds each to `record` ONLY when `is not None` (:223-232 pattern), so a 4-field body's stored row is byte-identical. `mattered_most: []` stays accepted. The response stays the constant `{"success": True, "message": "Feedback received"}`. An off-enum value (`"maybe"`) 422s at the model (never a silent DB CHECK drop at WARNING). T23 is untouched (`FeedbackRequest` is outside the ten-operation closure, R0-2).

### 2.10 Test seams (production values in brackets)

`result_gate.result_status_metadata_enabled` [env read]; `sentry_service.compare_traces_sampler`
[installed by `init_sentry`]; `sentry_sdk.capture_message` [the SDK, a no-op with no client]
patched by the tests at `sentry_sdk.capture_message` (the emitter imports the module inside the
function and calls `sentry_sdk.capture_message`, so a `monkeypatch.setattr(sentry_sdk, "capture_message", rec)`
records it); `scs._DEBUG_STAGE_TIMINGS` [None -> memo]; `image_routes.identify_products`,
`image_routes.StructuredComparisonService`, `content_safety_service.get_content_safety_service`,
`image_routes.log_search`, `image_routes.save_comparison_and_track_cohort` [the `_stub_camera` set];
`text_routes.get_comparison_service` [a real service with the FY25 `_install` leaves]; the FY25
`_Patcher` / `_install` / `_scenario` helpers (imported from `tests.test_s75_fanout_identity`);
`home_routes` / `history_routes` through `TestClient(app)` with the `test_home_routes.py:40-135`
supabase stub and the `test_history_routes.py:314-370` list patches.

### 2.11 Flag-OFF identity (the unit's main invariant)

With `ENABLE_RESULT_STATUS_METADATA` unset / `false` / `0` / `""` / `off`, and with the FULL
configuration otherwise present (`DEBUG_STAGE_TIMINGS=true` with the memo reset, a `capture_message`
recorder installed, `product_categories` passed on every build, a Sentry init recorder):
- every text and camera body built by `build_comparison_response` is byte-identical (no `result_status`, `identity_confidence`, `data_coverage*`, `section_status`, `product_categories`, `winner_index` key in `metadata`; no `supported` in `overview.winner`): the nine FY25 digests (E1 adds the flag to `UNIT_ENV`), PIN P1 (lane1 + w412 bodies through the builder, key-set and JSON equality against the base body recorded as a literal by RED), the UR11 T17 records, the metering camera bodies, the W4-13 ledger;
- `metadata.stage_timings_ms` on a camera body carries exactly scs's keys (no `vision_ms` / `vision_moderation_ms` / `compare_ms`), PIN P3;
- `capture_message` is called zero times on every exit, PIN P4; no new `fire_and_forget` label at any exit (the ledger);
- the sampler returns `parent_sampled` when not None else 0.1 for every path, PIN P5; `sentry_sdk.init` kwargs keep `traces_sample_rate == 0.1` and the three hooks (the U8d pin);
- every stored row (text, camera) is byte-identical (the builder is the only writer of the new keys);
- the only OFF-state work is the env read of the flag at each site, the three `perf_counter` reads on the camera route, and the per-product category capture in scs (a list of two canonical strings on `self._partial_build_ctx`, never serialised OFF).
The unflagged allowlist widening and the three feedback fields change no response byte and no stored
row for build 3 (which never sends them): P9, P10, P11.

### 2.12 Failure table (flag ON)

| failure | effect | log |
|---|---|---|
| `assess_result` raises inside the builder | the builder's block is wrapped: `except Exception` -> no stamp, body as flag OFF, ONE WARNING `[RESULT_STATUS] assess failed: <TypeName>` | WARNING |
| `capture_message` raises / no client | swallowed; body unchanged | WARNING (raise only) |
| sampler raises | 0.1 (and the SDK's own fallback) | none |
| `product_categories` not a 2-list | key omitted; coherence True | none |
| a malformed `scoring_v2` (None, {}, non-list dims) | dims fact False | none |
| a malformed product (non-dict) | that product's facts False, identity placeholder | none |
| `stage_timings_ms` absent / not a dict | no timing write | none |
| URL body (no metadata) | telemetry only; no stamp | none |
| off-enum `winner_correct` | 422 at the model (`VALIDATION_ERROR` envelope, as every 422) | none |

---------------------------------------------------------------------------------------------------

## 3. Change list, in the order GREEN applies it

Before the first edit: byte-copy (`shutil.copyfile`) every existing file below into
`<scratchpad>/b1_green_before/` with its sha256; restore only from those copies; CRLF preserved by the
Edit tool; `git diff --stat` content lines only.

1. NEW `app/services/result_gate.py` (2.2): constants, `norm`, `identity_text`, `is_placeholder_identity`, `product_is_placeholder`, `token_jaccard`, `same_identity`, `identity_coherence`, `price_is_showable`, `price_is_present_literal`, `rating_is_real`, `real_spec_rows`, `literal_spec_items`, `dim_is_discriminating`, `evidence_facts`, `evidence_facts_literal`, `evidence_coverage`, `section_status`, `identity_confidence`, `assess_result`, `telemetry_tags`, `stamp_camera_stage_timings`, `result_status_metadata_enabled`. Imports: `os`, `re`, `typing`, `from app.services.text_sanitize import dedup_brand_name`. Module docstring names R-A4 / R-A5 / R0-5 and the AUDITABLE reading.
2. `app/services/response_builder.py`: import `from app.services.result_gate import STATUS_SUPPORTED, assess_result, result_status_metadata_enabled` at the module top (:11-19 block); the new kwarg `product_categories: Optional[List[Optional[str]]] = None` after `_single_margin` (:1476); the docstring paragraph "B1 (S80) -- `product_categories` ..."; the stamp block of 2.3 between `result["tier_context"]` and `_strip_inference_markers(result)` (:2241-2259), wrapped in `try/except Exception` with the one WARNING (2.12).
3. `app/services/structured_comparison_service.py`: the capture `product_categories = [canonicalize_category(_p.get("category")) for _p in products]` immediately before `for _p in products: _p["category"] = category_used` at :4295 (REST) and :4911 (stream); `"product_categories": product_categories` added to the two `_partial_build_ctx.update({...})` dicts (:4284-4288, :4923-4927); `product_categories=product_categories` on the REST build (:4571-4597) and the stream build (:5411-5437); `product_categories=ctx.get("product_categories")` on the partial build (:3783-3824). Four insertions, no other line.
4. `app/services/sentry_service.py`: `from app.services.result_gate import result_status_metadata_enabled, telemetry_tags, assess_result` (module top; result_gate is stdlib + text_sanitize); `_TRACES_SAMPLE_RATE`, `_COMPARE_PATHS`, `compare_traces_sampler` (2.7) before `init_sentry`; `traces_sampler=compare_traces_sampler` added to the `sentry_sdk.init` kwargs after `traces_sample_rate=0.1` (:667); `capture_result_status` (2.5) after `init_sentry`.
5. `app/api/image_routes.py`: `from app.services.result_gate import stamp_camera_stage_timings` and `from app.services.sentry_service import capture_result_status`; the three `perf_counter` walls (2.6) around :310, :368, :450; `stamp_camera_stage_timings(...)` after :495; `capture_result_status(result, "camera", vision_ms=vision_ms, compare_ms=compare_ms)` immediately before `return result` at :579 (after the `comparison_unsuccessful and camera_failure_envelope_enabled()` return, so a non-delivery never emits).
6. `app/api/text_routes.py`: `from app.services.sentry_service import capture_result_status`; `capture_result_status(result, "text")` before `return result` at :768 and :951; `capture_result_status(complete_response, "text_stream")` at the end of the success branch (after the lifetime block :1296-1299, still inside the :1220 gate and only when `complete_response.get("success") is True`).
7. `app/api/url_routes.py`: the import; `capture_result_status(result, "url", compare_ms=int((time.time() - _start) * 1000))` before `return result` at :219.
8. `app/api/home_routes.py`: `_result_status_supported(full_response)` helper (2.4) next to `_safe_float` (:140); the early return in `_extract_winner_loser_prices` before :163; the `continue` in `_select_smart_pick` before :542 (Q5 may strike the smart-pick half).
9. `app/api/feedback_routes.py`: the two allowlist groups (2.9); `Literal` import; the three optional fields on `FeedbackRequest`; the three kwargs on the `save_feedback(...)` call (:174-183).
10. `app/services/feedback_service.py`: the three `Optional[str] = None` kwargs on `save_feedback` (:194-200) and the three `if x is not None: record[...] = x` lines after `change_suggestion` (:231-232).
11. NEW tests `tests/test_s80_b1.py` (section 5.1) and `tests/test_s80_b1_feedback.py` (5.2), written by RED, frozen for GREEN; E1 (one tuple entry in `tests/test_s75_fanout_identity.py`).
12. `CLAUDE.md`: the flag row (8.1) as a new `**SESSION 80 flag (B1, ...)**` block after the B3-B block (:471-472, before `## Tests` :474); the `/feedback` line (:105) rewritten IN PLACE (8.1); the event/feedback sentence in the "Feedback and event tracking" pattern if it lists the fields.

No other file. No `requirements*`, no migration (the 027 columns are live, R0-2), no `processors.json`
(no new host), no client file, no `.githooks`, no `tests/.pre_impl_failures.txt`, no fixture
regeneration (the FY25 digests do not move: flag OFF is byte-identical; the W4-11 recorder is never run).

---------------------------------------------------------------------------------------------------

## 4. Existing pins

### 4.1 Pins that change (deliberately), one row each

| # | test node | asserts today | new assertion | reason |
|---|---|---|---|---|
| E1 | `tests/test_s75_fanout_identity.py` `UNIT_ENV` tuple (:60-63), read by every node of the file | the FANOUT flags + `DEBUG_STAGE_TIMINGS` + `ENABLE_FULL_STREAM_DEADLINE` are popped per scenario | the tuple gains `"ENABLE_RESULT_STATUS_METADATA"`; the nine digests are UNCHANGED (no re-record) | a developer `.env` carrying the new flag would otherwise move the flag-OFF digests; one line, no assertion changes |

No other existing assertion changes. `test_u8d_pin_options_init_kwargs_kept`, `test_observability.py:272`,
`test_retro_w1_1.py:242` keep `traces_sample_rate == 0.1` (kept). `test_feedback.py::test_save_feedback_success`
(:19-42) asserts `insert_arg["mattered_most"]` and the keys it names -- the record is unchanged for a
4-field call.

### 4.2 Pins that must stay green and unedited (all green at base, 1.10 and the comm set)

`tests/test_s75_fanout_identity.py` (the nine FY25 digests, flag-ON stamps), `tests/test_w4_13_flag_off_ledger.py`
(45 scenarios: labels + kwargs), `tests/test_w4_13_measurement_truth.py`, `tests/test_s71_u13_compare_auth_required.py`
(T17 bodies, T23 OpenAPI, UR11), `tests/test_paid_route_metering.py` (camera + URL bodies, the ledger),
`tests/test_camera_failure_envelope*.py` / `tests/test_image_routes*.py` (camera envelopes), `tests/test_stage_timings.py`
(subset keys ON, absence OFF), `tests/test_history_routes.py` (:371-436 winner_index shapes),
`tests/test_home_routes.py` (savings 4, smart-pick, images, #116), `tests/test_events_allowlist_superset.py`
(:97-121), `tests/test_feedback_allowlist_superset.py` (:126-184), `tests/test_feedback.py` (incl. :356-365
extra fields ignored, :182-188 invalid item 422, :190-196 empty list ok), `tests/test_sentry_channels_u8d_unit.py`
(R8 AST pins, the init kwargs), `tests/test_sentry_channels_u8d.py`, `tests/test_observability.py`,
`tests/test_retro_w1_1.py`, `tests/test_comparison_id_echo.py`, `tests/test_response_builder*.py`,
`tests/test_winner_truth*.py` / `tests/test_m20_*` (reconcile + scrub), `tests/test_s78_*.py`
(TG / F8 metadata stamps), `tests/test_model_config.py`, `test_model_config_enforced.py`, `test_prompt_fence.py`,
`test_u3c_store_false_pin.py`, `test_start_command*.py`, `test_migration_index_predicate_immutability.py`,
`test_openai_key_log_hygiene_s69.py` (source-scanning), `tests/test_ci_gates.py`, `tests/test_behavior_dimension_translation.py`
(CLAUDE.md readers), `tests/test_security_regression.py`, `tests/test_conftest_env_safety.py`,
`tests/test_hermeticity_pins.py`, and the rest of the comm set.

---------------------------------------------------------------------------------------------------

## 5. RED tests

### 5.1 `tests/test_s80_b1.py` (new; pure ASCII, LF; hermetic)

Harness rules: nothing the unit creates is imported at module top (`importlib.util.find_spec("app.services.result_gate")`
/ `getattr(module, name, None)` inside each body, asserted, so every RED row fails on an AssertionError
or an assertion on a missing symbol, never an ImportError at collection). An autouse fixture `delenv`s
`ENABLE_RESULT_STATUS_METADATA`, `DEBUG_STAGE_TIMINGS`, `ENABLE_HONEST_PARTIAL_SCORING`,
`ENABLE_SINGLE_VERDICT_MARGIN`, `ENABLE_CONFIDENCE_SINGLE_COMPUTATION`, `ENABLE_PRESCORING_SHOWABLE_GUARD`,
`ENABLE_REGION_CURRENCY_GUARD`, `ENABLE_COMPARISON_ID_ECHO`, `ENABLE_SEARCH_LOG_TRUTH` (and the other
W4-13 names), resets `scs._DEBUG_STAGE_TIMINGS = None` before and after, installs a `capture_message`
recorder (`monkeypatch.setattr(sentry_sdk, "capture_message", rec)` where `rec(message, level=None, **kw)`
appends `(message, level, dict(kw.get("tags") or {}))`), disables the slowapi limiter (the
`test_social_login_device_fingerprint.py:65-72` copy) and restores `app.dependency_overrides`. Bodies
are built three ways: (a) the BUILDER directly (`build_comparison_response(product_data=deepcopy(row.products), comparison=deepcopy(row.comparison), scoring_result=deepcopy(row.scoring), product_names=[...], query="a vs b", category_used=<row category>, product_categories=[c, c])`
from w412 rows 12-14, 15, 24, 26 and the lane1 `grocery`, `now_vs_solgar`, `tomford_vs_creed`,
`iphone15_vs_galaxys24` files; `scoring_result` from `full_response["scoring"]` plus `winner_index` from
the row; the chokepoint and the scrubs run for real); (b) the ORCHESTRATOR through the FY25 `_install`
with its fakes swapped per row (`_specs` returning `{}` / an all-dash dict, `_price` returning None or an
`estimated` dict, `_rating` returning None, the vision pair via `compare_from_text(vision_products=...)`,
the explicit pair via `explicit_pair=`); (c) the ROUTES through `TestClient(app)`: `text_routes.get_comparison_service`
patched to a FY25-installed service for POST/GET/stream; `image_routes` through the `_stub_camera` set
with a `_Service` whose `compare_from_text` returns a REAL builder body (built in the test with (a)) and,
for the timing rows, a body whose `metadata["stage_timings_ms"]` is `{"total_ms": 1.0}` or absent;
`url_routes` through `_stub_url_leaves`; `home_routes` through the `test_home_routes.py:40-135` stub;
`history_routes` through the :314-370 list patches. Every flag-ON row exports the flag with
`monkeypatch.setenv`; every PIN row runs with the FULL configuration (flag OFF but `DEBUG_STAGE_TIMINGS=true`
+ memo reset, the recorder installed, `product_categories` passed) so a "not gated" mutant is killed.
Base bodies for P1 are recorded as literals by RED (sorted-key JSON, the clock fields dropped as FY25's
`VOLATILE`). Sentinels are plain words built at run time.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_b1_r1_flag_reader_per_call` (param: unset, `""`, `false`, `0`, `no`, `off`, `true`, `1`, `yes`, `on`, ` TRUE `) | `result_gate.result_status_metadata_enabled()` True exactly for the truthy four (strip/casefold); flipping the env after import flips the result | RED: module absent (`find_spec` None asserted) | 2.1, step 1 |
| R2 | `test_b1_r2_placeholder_identity` (param: `("Unknown","Unknown Product")`, `("","Unknown Product")`, `("Unknown","")`, `("Unknown","Unknown")`, `("","")`, `("", "n/a")`, `("Acme","This product")`, `("", "PRODUCT")`, `("Rasasi", "Hawas")`, `("", "Iphone 17")`, `("Unknown", "Hawas")`) | `product_is_placeholder` True for the first eight, False for the last three (brand "Unknown" with a real name is not a placeholder; brand "" with a real name is not); `is_placeholder_identity("Store Title", site_title="store title")` True | RED: module absent | 2.2 |
| R3 | `test_b1_r3_same_identity` (param: GUESS/GUESS! x2 -> True; `Guess`/`GUESS !` -> True; `GUESS Logo Tee` vs `GUESS Denim Shirt` -> False; Bertolli vs Carbonell `Extra Virgin Olive Oil` -> False; NOW Foods vs Solgar `Vitamin D3` -> False; `TOM FORD OUD VOYAGER 100 ML` vs `TOM FORD OUD WOOD 100 ML` -> False (0.714); same brand+name with variants `100ml` vs `50ml` -> False; same brand+name, one variant None -> True) | the listed truth table | RED: module absent | 2.2 (R-A5, R0-5) |
| R4 | `test_b1_r4_identity_coherence` (param: `["electronics","fragrances"]` -> False; `["other","fragrances"]` -> True; `["electronics","electronics"]` -> True; `[None,"grocery"]` -> True; `["Electronics ","electronics"]` -> True; `None` -> True; `["beauty","fragrances"]` (non-canonical) -> True) | the table | RED: module absent | 2.2 (R0-4) |
| R5 | `test_b1_r5_price_facts` (param over price dicts: `{amount 2.25, source_method estimated, estimated True}` -> showable False, literal False; `{amount 1.26, source_method local_bhd}` -> True/True; `{amount 2.07, source_method None}` -> False/True (R0 row 0); `{amount None, unavailable True}` -> False/False; `{amount True}` -> False/False; `None` -> False/False) | `price_is_showable` / `price_is_present_literal` | RED: module absent | 2.2 |
| R6 | `test_b1_r6_real_spec_rows_excludes_na_and_tier3` | 7/7 `"N/A"` vs `"N/A"` -> 0 (the Manama specs); `{"color": "red", "_field_confidence": {"color": "tier3_synthesis"}}` vs `{"color": "blue"}` -> 0; `{"color": "red", "weight": "N/A"}` vs `{"color": "blue", "weight": "1 kg"}` -> 1; `literal_spec_items({"product_0_advantages": ["x"], "similar": []})` -> 1; `response_builder._build_specs_rows(manama_products)` returns 7 rows (the base behaviour this fact deliberately does not follow, documented) | RED: module absent | 2.2 (R0-5) |
| R7 | `test_b1_r7_dim_facts` (param: `(85,85,high,None)` -> False both; `(85,75,high,None)` -> True both; `(75,75,low,limited_data)` -> False both; `(65.0,50,medium,None)` -> literal True, strict False (sentinel); `(88,82,low,None)` -> literal True, strict False; `(88,84,high,None)` with `review_score` in `missing_data` and key `review` -> strict False) | `dim_is_discriminating(dim, keys, strict=...)` | RED: module absent | 2.2 |
| R8 | `test_b1_r8_builder_stamps_manama_partial_no_winner` (param rows 12, 13, 14; flag ON) | `metadata.result_status == "partial_no_winner"`, `reasons` contains `no_evidence`, `data_coverage == 0`, `data_coverage_literal >= 1` (the GPT prose rescues the literal count), `identity_confidence == "medium"` (brand present, no corroboration), `section_status == {"specs": "unavailable", "reviews": "available", "pros_cons": "available", "price": "unavailable"}`, `overview.winner.supported is False`, `metadata.winner_index is None`, top-level `winner_index == 0` and `overview.winner.product_index == 0` unchanged, `metadata.product_categories == ["grocery", "grocery"]` | RED: no `result_status` key | 2.3 (MYEZ-003/011) |
| R9 | `test_b1_r9_builder_stamps_lane1_supported` (param: grocery, now_vs_solgar, tomford_vs_creed, iphone15; flag ON) | `result_status == "supported_result"`, `reasons == []`, `data_coverage >= 3`, `identity_confidence == "high"`, `overview.winner.supported is True`, `"winner_index" not in metadata`, `section_status` all `available` (grocery/now: specs available, reviews available, pros_cons available, price available) | RED: no key | 2.3 |
| R10 | `test_b1_r10_builder_unknown_product_pair_needs_identification` (param: brands `("","")` and `("Unknown","Unknown")`, names `Unknown Product` x2; flag ON; a scoring_result with real-looking dims) | `result_status == "needs_identification"`, `reasons[0] == "placeholder_identity"`, `identity_confidence == "unresolved"`, `metadata.winner_index is None`, `overview.winner.supported is False`; the top-level `winner_index` still 0 (B1 does not refuse) | RED: no key | 2.3 (MYEZ-002, V09) |
| R11 | `test_b1_r11_builder_same_identity_pair` (GUESS/GUESS! twice, flag ON, lane1-shaped data) | `result_status == "needs_identification"`, `reasons == ["same_identity", ...]`, `identity_confidence == "low"` | RED | 2.3 (MYEZ-004, V07) |
| R12 | `test_b1_r12_builder_category_conflict` (flag ON; `product_categories=["electronics","fragrances"]`, otherwise lane1 data) | `result_status == "unsupported_category"`, `reasons == ["category_conflict"]`, `identity_confidence == "low"`; with `["other","fragrances"]` -> `supported_result` | RED | 2.3 (R0-4) |
| R13 | `test_b1_r13_builder_june_rows_brand_empty_supported` (w412 rows 15-19 through the builder; flag ON) | `result_status == "supported_result"`, `identity_confidence == "medium"` (brand empty), `data_coverage >= 3` | RED | 2.3 (R0-5: never brand alone) |
| R14 | `test_b1_r14_builder_partial_rows` (w412 rows 24 and 26, `metadata={"partial": True, "partial_stage": "post_gather"}`; flag ON) | row 24: `data_coverage == 1` (the legacy dims), status `supported_result`, `supported True`; row 26: `data_coverage >= 1`; `partial_stage` survives in `metadata`; tag `partial_stage == "post_gather"` on a telemetry call built from the body | RED | 2.3 (R0-5 open item recorded) |
| R15 | `test_b1_r15_orchestrator_rest_and_stream_stamp` (FY25 `_install`, flag ON; REST `rest_q_full`, REST `rest_pair_full`, stream `complete`, REST partial at gather with `cap=0.5, slow=True`) | REST and stream `complete` bodies: `metadata.result_status == "supported_result"`, `data_coverage == 4` (local_bhd 120 both, rating 4.5 both, 3 real specs, dims), `metadata.product_categories == ["electronics","electronics"]`, `overview.winner.supported is True`; the gather partial: `metadata.partial is True`, `result_status == "partial_no_winner"` (the slow fetch stashes specs `{"display": "6.1 in"}` with price None, ratings None -> coverage 0... RED measures; if the stash's one real spec row on BOTH sides yields coverage 1 the expected status is `supported_result` and the row records the measured value), `metadata.winner_index is None` iff not supported | RED: no key | 2.3, step 3 |
| R16 | `test_b1_r16_orchestrator_vision_pair_product_categories` (FY25 `_install`, flag ON, `compare_from_text(query, vision_products=[{brand "Casio", name "G-Shock watch"}, {brand "Dior", name "Sauvage eau de parfum"}])`) | `metadata.product_categories == ["electronics", "fragrances"]` (captured BEFORE the write-back; `products[i].category` both == `category_used` as today), `result_status == "unsupported_category"`, `reasons == ["category_conflict"]` | RED: no key | step 3 (R0-4, MYEZ-001 measurement half) |
| R17 | `test_b1_r17_telemetry_text_post_get_stream` (route, flag ON, FY25-installed service) | exactly ONE recorder entry per exit: message `comparison_result_status`, level `info`, tags: `input_type` in {text, text, text_stream}, `result_status == "supported_result"`, `winner_emitted == "true"`, `unknown_product_count == "0"`, `image_present_a == "false"` (the FY25 image fake returns None), `price_showable_a == "true"`, `partial_stage == "none"`, `data_coverage == "4"`, `compare_ms` a digit string, no `vision_ms`; the key set is exactly the 2.5 table minus `vision_ms`; every value matches `^[a-z0-9_,]+$`; no value contains any product token (`iphone`, `galaxy`, `apple`, `samsung`) or the query | RED: zero entries | 2.5, steps 4, 6 |
| R18 | `test_b1_r18_telemetry_camera_and_url` (route; camera via `_stub_camera` with a REAL builder body; URL via `_stub_url_leaves`; flag ON) | camera: one entry, `input_type == "camera"`, `vision_ms` and `compare_ms` digit strings; URL: one entry, `input_type == "url"`, `result_status` in the five, `price_showable_a == "false"`, no `vision_ms`, `compare_ms` present; the camera unsuccessful path (`_Service` returning `success False` + `code`, metering ON) emits ZERO entries | RED: zero entries | 2.5, steps 5, 7 |
| R19 | `test_b1_r19_telemetry_stream_client_gone_emits_nothing` (the stream route with a client that disconnects before `complete`, the M18 CD-interactions-01 harness idiom from `tests/test_w4_13_measurement_truth.py`; flag ON) | zero recorder entries | PIN-shaped but RED-relevant: at base zero entries too -> this row is a PIN (green at base) kept for the mutant "emit outside the gate" | kept |
| R20 | `test_b1_r20_camera_timings_written_only_into_existing_dict` (route via `_stub_camera`; flag ON; param: body with `metadata.stage_timings_ms == {"total_ms": 1.0}` / body without the key / body with `stage_timings_ms` not a dict) | first: `stage_timings_ms` keys == `{"total_ms", "vision_ms", "vision_moderation_ms", "compare_ms"}`, the three ints >= 0, `total_ms` untouched; second and third: no `stage_timings_ms` key / unchanged value, no new `metadata` key | RED: no `vision_ms` | 2.6, step 5 |
| R21 | `test_b1_r21_sampler_flag_on_compare_paths` (param: the four paths, `/api/v1/health`, `/api/v1/comparisons/history`; `parent_sampled` None / True / False) | `compare_traces_sampler({"transaction_context": {...}, "parent_sampled": ps, "asgi_scope": {"path": p, "method": "GET"}})` == 1.0 for the four compare paths regardless of `parent_sampled`; == `ps` when not None else 0.1 for the others; a context without `asgi_scope` -> `ps`/0.1; `init_sentry()` against a recording `sentry_sdk.init` passes `traces_sampler` with `__name__ == "compare_traces_sampler"` AND `traces_sample_rate == 0.1` | RED: attribute absent | 2.7, step 4 |
| R22 | `test_b1_r22_home_savings_skips_stamped_non_supported_rows` (the `_comparison_row` fixture with `full["metadata"] = {"result_status": "partial_no_winner"}` on two of four rows, `winner_index 0`, BHD prices cheaper winner; flag unset -- the reader is unflagged) | `savings_bhd` equals the two supported rows' sum, `decisions_count == 2`; a row stamped `supported_result` counts; a row with `metadata.winner_index None` but no `result_status` counts (never via winner_index: the base helper already skips a non-0/1 top-level index, so this row carries top-level 0) | RED: all four counted | 2.4, step 8 |
| R23 | `test_b1_r23_home_smart_pick_skips_stamped_non_supported_rows` (the most recent row stamped `partial_no_winner`, an older supported row) | the smart pick is the older row | RED: the newest row is picked | step 8 (Q5) |
| P1 | `test_b1_p1_flag_off_builder_bodies_identical` (param: unset, `false`, `0`, `""`, `off`; bodies: w412 rows 12, 15, 24 and lane1 grocery; `product_categories` passed; `DEBUG_STAGE_TIMINGS=true` + memo reset; recorder installed) | the built body, sorted-key JSON with FY25's `VOLATILE` keys dropped, equals the literal recorded at base; `metadata` key set equals the base key set (no `result_status`, `identity_confidence`, `data_coverage`, `data_coverage_literal`, `section_status`, `product_categories`, `winner_index`); `overview.winner` key set == `{product_index, name, declaration, reason, key_tradeoff, margin}`; zero recorder entries | PIN (green at base) | 2.11 |
| P2 | `test_b1_p2_flag_off_orchestrator_digests_unchanged` | with `ENABLE_RESULT_STATUS_METADATA` unset AND set to `false`, the nine FY25 scenario digests equal `tests/fixtures/s75_fanout_identity_digests.json` (the file's own assertion, re-driven here with the flag explicitly `false` as the full-config variant) | PIN | 2.11, E1 |
| P3 | `test_b1_p3_flag_off_camera_timings_untouched` (route; `DEBUG_STAGE_TIMINGS=true`, memo reset, body with `stage_timings_ms {"total_ms": 1.0}`; flag unset / `false`) | `stage_timings_ms == {"total_ms": 1.0}` exactly; `metadata` key set == the stub's + `input_method, vision_cost, total_cost, identified_products`; zero recorder entries | PIN | 2.6, 2.11 |
| P4 | `test_b1_p4_flag_off_no_message_on_any_exit` (text POST, GET, stream, camera, URL; recorder installed; flag unset / `0`) | zero recorder entries on every exit; the response bodies equal the same requests' bodies with the recorder absent | PIN | 2.11 |
| P5 | `test_b1_p5_flag_off_sampler_is_the_sdk_rule` (param the six paths x `parent_sampled` None/True/False) | sampler == `ps` when not None else 0.1; `init_sentry()` kwargs keep `traces_sample_rate == 0.1`, `send_default_pii False`, `include_local_variables False`, the three hooks (the U8d assertion repeated here) | PIN (RED half: the attribute does not exist at base -> this row is split: P5a asserts the init kwargs (green at base), R21 asserts the sampler) | 2.7 |
| P6 | `test_b1_p6_builder_flag_on_does_not_move_the_crown` (rows of R8-R12, flag ON) | top-level `winner_index`, `overview.winner.product_index`, `overview.winner.name/declaration/reason/key_tradeoff/margin`, `scoring_v2.overall_score`, `comparison.winner_index`, `recommendation`, `products[i].price` (public view), `specs`, `reviews` byte-equal to the same build with the flag OFF (every key outside the seven stamped ones) | PIN-shaped at base (trivially equal), kept against the mutant "the stamp edits the crown" | 2.3 |
| P7 | `test_b1_p7_history_list_null_neutral_for_stamped_row` (list patch: a row with `full_response = {"metadata": {"winner_index": None, "result_status": "partial_no_winner"}, "comparison": {"winner_index": 0}, "products": [{"name": "a", "image_url": "https://x.invalid/a.jpg"}, {"name": "b", "image_url": "https://x.invalid/b.jpg"}]}`) | the list item has `winner_index None`, `winner_image_url None`, `runner_up_image_url None`; a sibling row with `metadata {}` and `comparison.winner_index 0` has `winner_index 0` and both image urls | PIN (green at base: the `in` check at :38) | 1.3, L6 |
| P8 | `test_b1_p8_home_savings_unstamped_rows_count_as_today` (the base `test_home_routes` fixtures: no `metadata`, or `metadata` without `result_status`, or `metadata` a non-dict) | `savings_bhd` and `decisions_count` equal the base values (`175.0 / 4` for the four-winning-rows case) | PIN | 2.4 |
| P9 | (feedback file 5.2) | | | |
| P10 | `test_b1_p10_canonical_categories_and_na_tokens_match_the_sources` | `result_gate.CANONICAL_CATEGORIES == set(extraction_service.CATEGORY_SPEC_SCHEMAS.keys())`; `response_builder._SPEC_NA_TOKENS <= result_gate.NA_VALUES`; `result_gate.SENTINEL_SCORE == scoring_service.MISSING_SCORE` | RED (module absent) -- listed under P for its role | 2.2 |
| P11 | `test_b1_p11_result_gate_is_pure` | `result_gate`'s module source (read as text) imports only `os`, `re`, `typing` and `app.services.text_sanitize`; no `import sentry_sdk`, `structured_comparison_service`, `response_builder`, `price_service`, `extraction_service`, `httpx`, `asyncio`, `socket`; no `def ` is `async`; no `logging` call | RED (module absent) | 2.2 |
| P12 | `test_b1_p12_url_body_never_stamped` (URL route, flag ON, `_stub_url_leaves`) | the response body has no `metadata` key (R0-1 / B4) while one telemetry entry was recorded | RED half (the entry); the body half is green at base | 2.5 |
| P13 | `test_b1_p13_stamp_failure_degrades_to_flag_off` (flag ON; `result_gate.assess_result` patched to raise) | the body equals the flag-OFF body; one WARNING `[RESULT_STATUS] assess failed: ValueError` (type only) | RED | 2.12 |

### 5.2 `tests/test_s80_b1_feedback.py` (new; the unflagged half; the W3-1 pattern)

| # | test | assertion | at base |
|---|---|---|---|
| F1 | `test_b1_f1_new_mattered_most_values_accepted` (param the six values) | `POST /api/v1/feedback {"useful": false, "mattered_most": [v]}` -> 200 with `get_supabase_client` patched | RED: 422 |
| F2 | `test_b1_f2_new_event_types_accepted` (param the six names) | `POST /api/v1/events {"events": [{"event_type": n, "event_data": {}}]}` -> 200 | RED: 422 |
| F3 | `test_b1_f3_correctness_fields_accepted_and_written` (param each of the three fields x `correct|wrong|unsure`) | 200; the `save_feedback` recorder (patched at `feedback_routes.save_feedback`) received the kwarg; through the REAL `save_feedback` with a recording client, `record[field] == value` | RED: the kwarg is absent / `TypeError` guarded by `getattr` -> AssertionError |
| F4 | `test_b1_f4_off_enum_value_422s` (param `"maybe"`, `1`, `true`) | 422 `VALIDATION_ERROR`, zero `save_feedback` calls | RED: 200 (the field is ignored as extra today) |
| F5 (PIN) | `test_b1_f5_four_field_body_record_identical` | the REAL `save_feedback` with a 4-field body builds `record == {"useful": True, "mattered_most": ["price"], "comparison_id": <uuid>, "change_suggestion": "x"}` exactly (no None keys) | PIN |
| F6 (PIN) | `test_b1_f6_existing_pins_hold` | the seven original values and `accurate/detailed/fast` still 200; `bogus` 422; `hacker_event` 422; `comparison_wall_time` not in `VALID_EVENT_TYPES`; `mattered_most: []` 200; the seven dark-era event names present | PIN |
| F7 (PIN) | `test_b1_f7_allowlists_append_only` | `VALID_MATTERED_MOST[:10]` == the base ten in order; `VALID_EVENT_TYPES[:27]` == the base list in order (recorded literals) | PIN (fails if GREEN reorders) |

RED rows fail at base on an AssertionError only (the 422/200 status or the missing-symbol assertion).
PIN rows are green at base with the full configuration. RED records the P1 literals and proves
satisfiability on a byte-copy prototype of section 3 inside the worktree (restored and sha-checked,
the mutation lock `.qa-mutation.lock` held), or in a detached scratch worktree under its notes folder
(no node_modules).

---------------------------------------------------------------------------------------------------

## 6. Mutation table (each mutant on a byte copy, exact-string edit matching once, the killing rows via `pyt.py -k`, bound 600, restored and sha256-compared)

| id | mutant | killed by |
|---|---|---|
| X1 | flag default `"true"` | P1, P2, P3, P4 |
| X2 | flag read once at import (module constant) | R1 (flip after import) |
| X3 | reader drops `"on"` / adds `"enabled"` | R1 |
| X4 | placeholder test on the brand alone | R13 (rows 15-19 would be `needs_identification`), R2 |
| X5 | `same_identity` ignores the brand (name Jaccard only) | R3 (Bertolli/Carbonell, NOW/Solgar), R9 |
| X6 | Jaccard threshold 0.5 | R3 (OUD VOYAGER vs OUD WOOD) |
| X7 | `identity_coherence` treats `"other"` as a conflict | R4, R12 |
| X8 | `price_is_showable` accepts `estimated` | R5, R8 (coverage 1 -> supported) |
| X9 | `rating_is_real` ignores `rating_derived` | R8 (ratings fact True -> coverage 1) |
| X10 | `real_spec_rows` counts `"N/A"` rows | R6, R8 |
| X11 | `real_spec_rows` ignores `tier3_synthesis` | R6 |
| X12 | `dim_is_discriminating` drops the margin test | R7, R8 (ties count) |
| X13 | strict reading drops the sentinel / low checks | R7 |
| X14 | status `supported_result` when coverage 0 | R8 |
| X15 | `winner_index = None` written on every body | R9 (`"winner_index" not in metadata`), P1 |
| X16 | `overview.winner.supported` always True | R8, R10 |
| X17 | `section_status` reports `available` on one side | R8 (`specs` would read `available`? no: both N/A) -> R-one-sided fixture inside R6/R8: a lane1 row with one product's specs emptied expects `partial` (add to R9's param) |
| X18 | `product_categories` captured AFTER the write-back | R16 (`["fragrances","fragrances"]`), R12 unaffected |
| X19 | stamp block placed before the chokepoint (reads raw prices) | R8 (Manama estimated 2.25 would be showable) |
| X20 | telemetry emitted with the flag OFF | P4 |
| X21 | telemetry tags carry `query` / a product name | R17 (grammar + token checks) |
| X22 | telemetry on the camera unsuccessful path | R18 |
| X23 | telemetry outside the stream gate (client gone) | R19 |
| X24 | camera timings written when the flag is OFF | P3 |
| X25 | camera timings create the dict when absent | R20 |
| X26 | sampler returns 1.0 with the flag OFF | P5 |
| X27 | sampler path set lacks `/text/compare/stream` | R21 |
| X28 | sampler ignores `parent_sampled` OFF (returns 0.1 always) | P5 |
| X29 | `init_sentry` drops `traces_sample_rate` | P5a / the U8d pin |
| X30 | home skip keyed on `winner_index is None` | R22 (the stamped row carries 0) |
| X31 | home skip when `result_status` is ABSENT | P8 |
| X32 | `FeedbackRequest` field typed `Optional[str]` | F4 |
| X33 | `save_feedback` writes the three keys when None | F5 |
| X34 | one allowlist name missing / misspelled | F1 / F2 |
| X35 | `assess_result` raise not caught in the builder | P13 |

Equivalent survivors expected: none; any survivor is reported for a ruling.

---------------------------------------------------------------------------------------------------

## 7. Comm set and gates for GREEN (cheapest first; every pytest through the bounded runner, one process at a time)

1. Syntax / lint on every changed `.py`: `<venv python> -m py_compile` and `-m ruff check --select E9,F63,F7,F82 --no-cache`. Byte check (`> 127`) on the new files. `git diff --stat` content lines only (CRLF kept; new files LF).
2. Unit: `tests/test_s80_b1.py`, then `tests/test_s80_b1_feedback.py` (bound 600 each) -> all pass; then the 1.10 files again (runs 1-3, bound 600 each) -> same counts.
3. Identity nodes alone (bound 600): `tests/test_s75_fanout_identity.py` (E1 applied, digests unchanged), `tests/test_w4_13_flag_off_ledger.py`, `tests/test_stage_timings.py`, `tests/test_s71_u13_compare_auth_required.py` (T17/T23), `tests/test_paid_route_metering.py`, `tests/test_sentry_channels_u8d_unit.py`, `tests/test_observability.py`, `tests/test_retro_w1_1.py`.
4. Flag-ON smoke (information, not a gate): the 1.10 files once with `ENABLE_RESULT_STATUS_METADATA=true` exported in the runner call only; expected green except nodes that pin an exact metadata key set on a built body (report any by node id; `test_stage_timings` subset assertions pass; the FY25 flag-OFF node is expected RED under this export by construction -- its `UNIT_ENV` pop makes it green again after E1, verify).
5. Comm set, base vs head, `comm -13` of the sorted FAILED node ids EMPTY. The set = the module-reference grep for `structured_comparison_service`, `response_builder`, `result_gate`, `image_routes`, `text_routes`, `url_routes`, `home_routes`, `history_routes`, `feedback_routes`, `feedback_service`, `sentry_service` (268 files at base by `grep -rlE` over `tests/*.py`; scs alone pulls most of them) UNION the source-scanning pins (`test_model_config.py`, `test_model_config_enforced.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`, `test_start_command*.py`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py`, every test that walks or reads `app/` by path) UNION the CLAUDE.md readers (`tests/test_ci_gates.py`, `tests/test_behavior_dimension_translation.py`; CLAUDE.md changes in step 12) UNION the SmartCompareApp-scanning tests (`grep -rl SmartCompareApp tests/*.py` = 25 files at base; the allowlists are the client-visible contract) MINUS the four `test_precommit_hook*.py` files (no `.githooks` change). About 290 files: chunks of at most 25 files, bound 1200 each, base then head (then base again for any branch-only-new failure, to tell a flake from a regression); GREEN computes the exact list with `scripts/comm_set.py` at HEAD and adds the two new test files; expected base noise: the two `test_prompt_truth.py` ERRORs (cold tiktoken cache) identical on both sides and the `.pre_impl_failures.txt` nodes.
6. Mutation run (section 6) on the GREEN bytes, byte copies, sha-verified restore, the `.qa-mutation.lock` protocol.
7. Personal-data and secret sweep of `git diff 81df2b64` (Python, in memory, counts only): no added line matches the hook patterns, `@gmail`, `+973`, an 8-digit run; no real name.
8. Full-suite CI is the final arbiter (one new module import in five route/service files).

---------------------------------------------------------------------------------------------------

## 8. CLAUDE.md row and owner steps

### 8.1 The flag row (GREEN writes it; wording may be tightened, content may not)

New block after the B3-B block (CLAUDE.md:471-472, before `## Tests`):

**SESSION 80 flag (B1, 2026-10-20; default OFF, read PER CALL; a new name, so unset in production by construction (Railway not read); PLAN_S80 unit B1 as amended by RULINGS_R0 R0-1/R0-4/R0-5/R0-6; spec `.qa-s80/B1_UNIT_SPEC.md` of the unit worktree):**
- `ENABLE_RESULT_STATUS_METADATA` (B1, `app/services/result_gate.py::result_status_metadata_enabled`; the pure module holds `is_placeholder_identity`, `same_identity` (R-A5 with the brand condition), `identity_coherence`, `evidence_coverage` under the AUDITABLE and the LITERAL readings, `assess_result`). **Effect ON:** every text and camera body built by `build_comparison_response` carries `metadata.result_status` {supported_result, partial_no_winner, needs_identification, unsupported_category, failed}, `identity_confidence` {high, medium, low, unresolved}, `data_coverage` (0-4, the AUDITABLE count: both prices showable and not estimated; both ratings real; a real two-sided spec row that is not tier-3; a non-sentinel, non-low dimension with margin >= 3) and `data_coverage_literal` (the literal count, so production sizes the gap R0-5 measured as 1/27 vs 4/27), `product_categories` (the per-product categories captured BEFORE the pair write-back), `section_status` {specs, reviews, pros_cons, price: available | partial | unavailable}, `overview.winner.supported` (bool), and `metadata.winner_index = None` on every non-supported body (the first writer of that key: History renders such a row with no winner highlight and placeholder tiles; `/home/savings` and `/home/smart-pick` skip stamped non-supported rows by `result_status`, never by `winner_index`). One PII-free Sentry info message `comparison_result_status` per delivery exit (text POST/GET, stream complete, camera success, URL success) with enum/int tags only (input_type, result_status, identity_confidence, reasons, unknown_product_count, winner_emitted, image_present_a/b, price_showable_a/b, partial_stage, data_coverage, data_coverage_literal, vision_ms, compare_ms). `vision_ms` / `vision_moderation_ms` / `compare_ms` are written into an EXISTING camera `metadata.stage_timings_ms` dict only. A `traces_sampler` samples `/api/v1/text/compare`, `/text/compare/stream`, `/image/identify`, `/url/compare` at 1.0; every other transaction keeps the parent decision else 0.1. Nothing abstains (B2); build 3 ignores every new key; the crown (`winner_index`, `overview.winner.product_index`, `scoring_v2.overall_score`) is unchanged. **Flag OFF:** byte-identical on every body and stored row, no message, the SDK's own sampling rule (pinned by the nine FY25 digests, `tests/test_s80_b1.py` P1-P8, the W4-13 ledger, the UR11 bodies, the metering pins). **UNFLAGGED alongside it (R-A1(a), R0-2):** `VALID_EVENT_TYPES` += scan_start, scan_identity_resolved, scan_comparison_ready, scan_failed, scan_cancelled, image_load_failed (C7); `VALID_MATTERED_MOST` += wrong_product, missing_info, unclear_reasons, slow, wrong_winner, unsure (C6); `FeedbackRequest` gains optional `winner_correct` / `price_correct` / `specs_correct` (Literal correct | wrong | unsure, default None) written to the live 027 columns only when sent; `mattered_most: []` stays accepted. **Stated limits:** the identity confidence has no vision signal until B3 threads it; `unsupported_category` is reachable only through a per-product category conflict today (every `category_used` is one of the nine); the URL envelope is never stamped (R0-1, B4) and its telemetry reads a body without prices or scoring; the stream emits no message when the client left before `complete` (not a delivery); a stamped non-supported History row shows placeholder tiles until C1; the compare-route transaction volume rises to 100 % of compare requests under the flag (Sentry quota is the owner's reading). **Precondition:** none; this is the FIRST flag to flip after approval (R-A2 order): it measures the abstain rate before ENABLE_RESULT_GATE abstains. **Canary:** the `comparison_result_status` messages grouped by `result_status` x `input_type` over one canary window (expected from the fixtures: about 15 % `partial_no_winner`, camera-heavy; `needs_identification` on Unknown Product / identical pairs), `data_coverage` vs `data_coverage_literal` distributions, the camera `vision_ms` / `compare_ms` tags, `/home/savings` counts unchanged for pre-flip rows. **Rollback:** unset the variable (per call, immediate); rows stamped during the window stay stamped (they stay non-supported) and keep being skipped by Home.

Also IN PLACE (principle 5): CLAUDE.md:105 `FeedbackRequest: 4 fields only (...)` -> "`FeedbackRequest`: `useful, comparison_id, mattered_most, change_suggestion` + the three optional 027 fields `winner_correct / price_correct / specs_correct` (B1, S80, written only when sent); ContactUsScreen prefixes `[Bug] Subject\n\nBody` for grep."

### 8.2 Owner steps (names only)

1. Nothing before merge; nothing before approval (UB-R4; no OTA).
2. After approval, the FIRST flip of the R-A2 order: set `ENABLE_RESULT_STATUS_METADATA=true` on `web`; read the canary of 8.1 for one window in Sentry (Issues -> the `comparison_result_status` message, group by the `result_status` and `input_type` tags; Performance -> the four compare transactions now at 100 % sampling) and the Railway log for `[RESULT_STATUS]` WARNING lines (expected none).
3. Check the Sentry plan's transaction quota against the compare request rate before the flip (names only; the sampler raises compare transactions from 10 % to 100 %).
4. The allowlist widening is live at merge (unflagged) and must be deployed BEFORE any client bundle fires the six event names or the six chip values (C6/C7 OTAs after approval).

---------------------------------------------------------------------------------------------------

## 9. Stated limits

- L1 `identity_confidence` uses no vision confidence at base (dropped at scs:4210-4224); `assess_result(vision_confidences=...)` is accepted and ignored until B3 passes it; `medium` therefore means "brand empty or no corroborating data", never "the model was unsure".
- L2 `unsupported_category` via `category_used` is unreachable at base (every `category_used` is one of the nine incl. `other`); it is reachable through a per-product conflict (two different canonical non-other categories) on every path, since the per-product stubs are name-keyword classifications (a watch beside a perfume).
- L3 Fact (c) excludes tier-3 fields through `specs._field_confidence[field] == "tier3_synthesis"`, which `_clean_specs` lifts at scs:3443 and which survives to the stamp; stored rows carry the marker on 3 of 52 corpus products only, so B2 must honour the STAMPED status, not recompute it on old rows.
- L4 The strict dims reading treats a score of exactly 50 on either side as the MISSING_SCORE sentinel; a genuine calibrated 50 (raw 10) on a core dim is excluded too (conservative).
- L5 The literal fact (c) counts the GPT prose lists (`product_0_advantages`, `product_1_advantages`, `similar`), matching R0's tally; the `rows` list `_build_specs_rows` emits still contains `"N/A" vs "N/A"` rows (a C1/B5 display item, not fixed here).
- L6 A stamped non-supported History row ships `winner_index None` and both image urls None (history_routes:73-74); build 3 then shows no winner highlight and placeholder tiles on both cards (contract_freeze 5b) until C1 renders the three states.
- L7 The Sentry message is subject to the SDK event `sample_rate` (default 1.0) and the project's event quota; the sampler raises compare transactions to 100 %.
- L8 The stream emits no message for a terminal the client never received (`complete_after_client_gone`), by design (it is refunded, not delivered), so stream telemetry counts deliveries only.
- L9 URL bodies: telemetry only; no prices are showable (no `source_method`), no `scoring_v2` -> `data_coverage` is 0 or 1 (ratings only) and the status is mostly `partial_no_winner`; the body is unchanged (B4 owns the URL envelope; B12 unifies it later).
- L10 `metadata.winner_index` is written only on non-supported bodies; a supported body keeps the key absent so the History fallback to `comparison.winner_index` is unchanged.
- L11 The Home readers key on the stored stamp and read no flag: rows written before the flip keep counting; rows stamped during a window stay skipped after a rollback (they stay non-supported).
- L12 The flag is read per call at six sites; a mid-request flip can yield a stamped body without a message (or the reverse) for at most one in-flight request.
- L13 `profile_routes.py:75/:97/:141` (recent decisions) still read the top-level `winner_index` and will present a stamped non-supported row as a decision until Q7 is ruled or C1 lands.
- L14 `DEBUG_STAGE_TIMINGS` is process-cached (scs:1066-1075): a camera body gets the three timing keys only in processes where the memo was true at first read; tests reset the memo.
- L15 Offline sizing (R0-5): 4/27 corpus rows abstain under the AUDITABLE reading (3/16 camera); the identity half (placeholder, same identity) has 0 corpus hits -- its production rate is what this flag measures.
- L16 `same_identity`'s variant/size/distinguishing_features condition compares the fields present on the product dicts (`variant`, `size_or_count`, `distinguishing_features`); at base the orchestrator's product dict carries `variant` (from `size_or_count` on the vision path) and no `distinguishing_features` (B3 adds it), so two same-named products at two sizes are "not the same identity" only when both sizes were read.
- L17 Camera `vision_ms` excludes the multipart read and JPEG transcoding before :310 and the per-image validation; `compare_ms` is the `compare_from_text` wall only (the route's own `duration_ms` at :500 is the full wall).

## 10. Out of scope

Any refusal or abstain (B2: the `action:'error'` camera refusal, the INSUFFICIENT_DATA `reason`, the R-A3 non-delivery accounting); vision prompt or confidence changes (B3); the URL envelope, `metadata.query` on it, the URL pre-gate and codes (B4); the `N/A vs N/A` spec rows and `limited_data` captions (B5/C1); client rendering of the status (C1), the feedback card (C6), the scan events firing (C7); `profile_routes` recent decisions (Q7); the `/home/savings` SQL aggregate (#116, migration 036) -- the Python legacy path only; any change to `scoring_v2.confidence_legs`, `winner_index`, `overview.winner.product_index` or `scoring_v2.overall_score`; a migration (none needed); `processors.json` (no new host).

## 11. Open questions for the orchestrator

- Q1 (status mapping, binding before RED): a per-product category conflict maps to `unsupported_category` with reason `category_conflict` (recommended: the pair is not one supported category) or to `needs_identification` (the user mis-paired the inputs)?
- Q2 (identity_confidence rule): accept the four-level rule of 2.2 (`unresolved` placeholder; `low` same identity / conflict / vision low; `medium` brand empty / vision medium / no corroborating data; `high` else), or collapse to three levels until B3 threads the vision signal?
- Q3 (fact (c) reading, R0-5 open item): confirm the AUDITABLE reading for `data_coverage` = real two-sided spec rows minus tier-3 fields (as spec'd), with the literal count beside it; and confirm that `data_coverage` on a partial (row 24: legacy category dims only) counts those dims (as spec'd: 1).
- Q4 (sampler path set): the "three compare routes" = `/api/v1/text/compare`, `/api/v1/text/compare/stream`, `/api/v1/image/identify`, `/api/v1/url/compare` (recommended) or without the stream?
- Q5 (Home smart pick): skip stamped non-supported rows in `_select_smart_pick` too (recommended, step 8; MYEZ-027: a non-supported row would otherwise be crowned on Home) or limit to the savings aggregate as the brief says?
- Q6 (telemetry tags): the brief's tag list plus `identity_confidence` and `reasons` (recommended: both are enums) or the brief's list exactly?
- Q7 (profile recent decisions): apply the same `result_status` skip in `profile_routes.py:75/:97/:141` in this unit (one more reader, same rule) or defer to C1?
- Q8 (telemetry message name): `comparison_result_status` (recommended, the `comparison_wall_time` naming pattern) or a name the owner prefers for the Sentry search?
- Q9 (the `estimated` corner of fact (a)): the structural predicate equals the chokepoint verdict by position; confirm no second `is_price_showable` call is wanted at the stamp (it would re-stamp `guard_rejected` on the public view).

Not done in this spec: no production, Railway, Supabase, Sentry or network access; no app code executed beyond `dedup_brand_name` on the identity cases of 1.6; the per-file split of the three base runs (the runner prints totals); the comm set was sized by grep (268 + 25 + the pins), not computed with `comm_set.py`; the FY25 gather-partial expectation of R15 is left for RED to measure (the fake stash carries one real spec on both sides).
