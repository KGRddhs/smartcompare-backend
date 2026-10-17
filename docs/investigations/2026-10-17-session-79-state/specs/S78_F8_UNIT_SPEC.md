# S78-F8 unit spec: report an all-timeout hard cap as TIMEOUT, not INSUFFICIENT_DATA

Unit S78-F8 = fix 8 of `COMPARE_QUALITY_PLAN_S78.md` (docs branch), orchestrator brief
`scratchpad/f8/F8_BRIEF.md` (provisional rulings D1-D10, tests F1-F15, questions Q1-Q6). House rules:
`RULINGS_S78_TG_SM.md` + `RULINGS_S78_TG_SM_SPEC_REVIEW.md` (the TG pattern: flag idiom, tests, comm
set, byte identity). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s78-alltimeout`, branch
`feature/s78-all-timeout-cap-as-timeout`, base main `e0f3e475` (HEAD == base == origin/main
`e0f3e4759052b07a24717384a7a4d462ddadaf21`, tree clean, measured 2026-10-17 05:09 AST).
`scs` = `app/services/structured_comparison_service.py` (9,474 lines at base, CRLF working copy,
`core.autocrlf=true`). Every line number is at `e0f3e475` (worktree file == `git show e0f3e475:` file);
resolve by symbol if it moves. Pure ASCII in this file: the em dash of the product strings is written
`U+2014`.

---------------------------------------------------------------------------------------------------

## 1. Base state (measured)

### 1.1 The REST hard-cap handler (the unit's site)

| What | Where | Measured fact |
|---|---|---|
| Entry | scs:3787 `compare_from_text` | LLM preflight short-circuit 3827-3833; `_t0 = time.time()` 3834. |
| The cap | scs:3836-3852 | `asyncio.wait_for(self._compare_from_text_impl(...), timeout=STREAM_HARD_CAP_SECONDS)`. |
| Cap value | scs:1632 | `STREAM_HARD_CAP_SECONDS = float(os.getenv("STREAM_HARD_CAP_SECONDS", "25.0"))`, import-time; tests patch `scs.STREAM_HARD_CAP_SECONDS`. |
| Handler | scs:3853-3900 | `except asyncio.TimeoutError:` 3853; `elapsed = time.time() - _t0` 3854. |
| Partial branch | scs:3856-3864 | `if self._partial_has_usable_data():` build + WARNING `[L2.7] compare_from_text hard-cap %.1fs hit for query=%r <U+2014> returning best-available PARTIAL (success:true)` (3859-3863). |
| Partial build failure | scs:3865-3871 | `except Exception` -> **ERROR** `[L2.7] partial build failed after hard-cap for query length=%d: %s` (U8d, query length only), then FALLS THROUGH to the no-data branches with usable data present. |
| No-usable WARNING | scs:3875-3879 | `[L2.7] compare_from_text hard-cap %.1fs hit for query=%r <U+2014> no usable partial; returning graceful timeout` -- logged ONCE, BEFORE the INSUFFICIENT_DATA / TIMEOUT decision, on both remaining branches. |
| INSUFFICIENT_DATA branch | scs:3885-3893 | `if self._partial_product_data or self._early_specs_buffer_list():` -> six keys: `success` False, `error` "Comparison data was incomplete U+2014 choose different products.", `code` "INSUFFICIENT_DATA", `elapsed_seconds` `round(elapsed, 2)`, `total_cost`, `api_calls`. |
| TIMEOUT body | scs:3894-3900 | five keys: `success` False, `error` `TIMEOUT_FRIENDLY_MESSAGE`, `code` "TIMEOUT", `elapsed_seconds` `round(elapsed, 2)`, `total_cost`. NO `api_calls`. |
| `TIMEOUT_FRIENDLY_MESSAGE` | scs:1696 | "Still gathering prices U+2014 give it another tap in a moment." |
| House flag reader | scs:1760-1761 | `_flag_on(name)`: `os.getenv(name, "").strip().lower() in ("true", "1", "yes", "on")`. |

### 1.2 The stash state the handler reads

| What | Where | Measured fact |
|---|---|---|
| Post-gather stash attr | scs:3239 (`__init__`) | `self._partial_product_data: Optional[List[Dict[str, Any]]] = None`. |
| Per-run attr precedent | scs:3247-3248 | `_compare_deadline`, `_phase2_skipped` (reset at both entries 3940-3941 / 4548-4549). |
| Early buffer attr | scs:3256-3265 | `self._early_specs_buffer: Optional[List[Optional[Dict[str, Any]]]] = None`. |
| `_early_specs_buffer_list()` | scs:3519-3525 | `[pd for pd in (self._early_specs_buffer or []) if isinstance(pd, dict)]` -- compacts, LOSES the slot index. |
| `_partial_has_usable_data()` | scs:3527-3547 | `pd_list = self._partial_product_data or self._early_specs_buffer_list()`; True iff some dict has `specs is not None` or `price is not None`. |
| `_phase1_completely_failed(pd)` | scs:416-427 | `pd.get("specs") is None and pd.get("price") is None`. |
| `_build_partial_response` | def scs:3565 | (scs:3549 is `_partial_stage`). |
| REST impl | def scs:3902 | resets: `_compare_deadline` 3940, `_phase2_skipped` 3941, `_source_trace = {}` 3950, `_parked_price = {}` 3952, `_price_candidates = {}` 3953, `_partial_product_data = None` 3983 ... `_early_specs_buffer = [None, None]` 3991. |
| REST pair gather | scs:4123-4126 | `_fetch_product_data(products[i], ..., partial_slot=i)` for i = 0, 1. |
| Post-gather stash | scs:4133 | `self._partial_product_data = product_data`. |
| REST H6 guard | scs:4141-4155 | both products `_phase1_completely_failed` -> returns INSUFFICIENT_DATA (six keys, `elapsed_seconds` NOT rounded) synchronously. No await between 4133 and 4141, so a post-gather all-None pair never reaches the cap handler. OUT OF SCOPE (D1). |
| Stream entry | def scs:4493 | resets 4548-4549, 4603-4606, 4619-4625 (`_early_specs_buffer = [None, None]` at 4625). |
| Stream Phase-1 cap | scs:4759-4821 | `wait_for(gather(...), STREAM_HARD_CAP_SECONDS)` 4760-4766; handler 4767-4821: partial when usable, else `STREAM_TIMEOUT` body 4810-4818 (carries `partial: True` and `api_calls`). Never INSUFFICIENT_DATA. Untouched. |
| Stream H6 | scs:4827-4844 | INSUFFICIENT_DATA settle_complete + complete. OUT OF SCOPE. |

### 1.3 `_fetch_product_data`: registration, races, done-callbacks, the loop

| What | Where | Measured fact |
|---|---|---|
| Signature | scs:5474-5477 | `(self, product_info, region, include_specs, include_reviews, nocache=False, partial_slot=None)`. Only callers: scs:4124-4125 (REST) and scs:4762-4763 (stream), always `partial_slot=0/1` (TG spec 1.1). |
| `result` dict | scs:5503-5506 | six identity keys: brand, name, full_name, variant, category, query. Never rebound (only assignment 5503; `return result` 6221), so `_partial_product_data[i] is _early_specs_buffer[i]`. |
| Early registration | scs:5517-5524 | `_stash_early` = stash flag ON and `partial_slot is not None` and buffer is a list and slot in range; then `self._early_specs_buffer[partial_slot] = result` BY REFERENCE. |
| `_PHASE1_TIMEOUTS` | scs:5538-5555 | LOCAL dict literal: specs 8.0, price `_PRICE_RACE_TIMEOUT` (scs:1689, env `PRICE_RACE_TIMEOUT` default 15.0, import-time), reviews 10.0, image_url 5.0. Not patchable except the price constant. |
| Price task | scs:5565-5568 | `ensure_future(wait_for(_timed_task("price", self._get_price(...)), timeout=...))`, started BEFORE the unified search. |
| **Price done-callback** | **scs:5578-5584** | `_stash_price_cb`: `_res["price"] = _t.result()` on a COMPLETED price race (any value, None included); TimeoutError / CancelledError / Exception -> writes nothing. |
| Specs task + done-callback | scs:5689-5705 | `_specs_task` 5689-5692; `_stash_specs_cb` 5693-5705, the same rule for `result["specs"]`. |
| Race order | scs:5664-5752 | `phase1_keys`: `specs` (5706-5707, if include_specs), `price` (5713-5714, always), `reviews` (5716-5729, if include_reviews), `image_url` (5739-5752, always). |
| Gather | scs:5755 | `asyncio.gather(*phase1_tasks, return_exceptions=True)`, inside `try`; `except BaseException` 5756-5772 drains the price / specs tasks and re-raises (a cancel never reaches the loop). |
| THE LOOP (record site) | scs:5780-5798 | `isinstance(r, asyncio.TimeoutError)` -> WARNING `[L2.6] Phase 1 race timeout for %s (limit %.1fs)` + `result[key] = self._price_fallback_on_miss(...)`; `isinstance(r, Exception)` -> ERROR `Error fetching %s: %s` (type name) + the same fallback; else `result[key] = r` (a `CancelledError` instance, BaseException-not-Exception, lands here as a VALUE). |
| After the loop | scs:5800-5861 | S3 L1.5 price-outcome record 5800-5824; L2.9 `_source_trace` 5826-5861 (`sources_returned_value` from result presence; no timeout signal; `product_key` by append order, not slot). `grep -n "_source_trace\[" scs` -> 0 hits. No per-race outcome record exists. |
| `_price_fallback_on_miss` | def scs:6376 | price: a completed genuine candidate (6395-6437, under `_genuine_priority_enabled()`), else the parked price `self._parked_price.get(full_name)` with an amount (6438-6444), else None; every other key -> None. |
| `_timed_task` | scs:1346-1357 | try/finally only; never catches. |
| Phase 2 rating cap | scs:5956-5970 | `wait_for(_get_verified_rating, _PHASE2_RATING_TIMEOUT)`; `_PHASE2_RATING_TIMEOUT = 4.0` (scs:1931). |

Every write of `result["specs"]` / `result["price"]` / `result[key]` inside `_fetch_product_data`
(Q2, `awk` over scs:5474-6222): 5581 (price callback, pre-loop), 5702 (specs callback, pre-loop),
5791 / 5796 / 5798 (the loop), 5906 (`_clean_specs`), 6038 (smart-fallback merge), 6064 (Tier 2),
6088 (Tier 3) -- the last four are post-loop and specs-only.

### 1.4 The route, the KPI row, the camera, the client

| What | Where | Measured fact |
|---|---|---|
| Wire mapping | app/api/text_routes.py:521-551 | `_surface_comparison_failure`: CONTENT_UNAVAILABLE -> body (524-527); TIMEOUT / LLM_UNAVAILABLE -> `HTTPException(503, {code, error})` (528-543); any other code -> 400 (547-551). |
| Refund | text_routes.py:666-677 | fires for EVERY failure before the surface call (694). Unchanged by the unit. |
| Failure row, W4-13 OFF | text_routes.py:656-665 | `error_message=result.get("error")`. |
| Failure row, W4-13 ON | text_routes.py:678-689 | `_failure_log_message` (457-468: a coded result logs `error` unchanged) + `_failure_log_cost` (443-454: reads `total_cost`, never `api_calls`). |
| `api_calls` readers | `grep -n api_calls app/api/text_routes.py app/api/image_routes.py` | 0 hits: no route reads it. |
| KPI bucket | app/services/analytics_service.py:136 `get_error_stats`; 154-155 | `Counter(r.get("error_message", "Unknown") for r in errors)` -- buckets by exact text. |
| Camera | app/api/image_routes.py:450 | `service.compare_from_text(query, region=region, vision_products=products, nocache=nocache)` -> the SAME handler. Failure row `error_message=result.get("code") or ...` (526). Envelope `_camera_failure_envelope` 109-129 carries the result's own `code` (121); applied at 532-533 and 575 under `camera_failure_envelope_enabled()` (89-107, default OFF in code; ON in prod since 2026-10-03 per CLAUDE.md). |
| Client, text | SmartCompareApp/src/services/errorCopy.ts:75-92 | `INSUFFICIENT_DATA` -> `home.errors.insufficientData` (76-79); `TIMEOUT` / `STREAM_TIMEOUT` -> `home.errors.timeout` (85-89). |
| Client, camera | SmartCompareApp/src/services/failureClassification.ts:119-126 | TIMEOUT / STREAM_TIMEOUT -> `'timeout'` (123); anything else incl. INSUFFICIENT_DATA -> `'generic'` (125). |

### 1.5 The probe (Q1, Q2, Q4, F2/F3/F6/F7/F12 at base, F13 cost, F15 harness)

Probe file `tests/test_zz_s78f8_probe.py` (a copy kept at
`scratchpad/f8/spec_agent/test_zz_s78f8_probe.py.copy`), run with `-s` through the bounded runner, then
deleted (`git status --short` empty afterwards):

```
13 passed, 12 warnings in 27.58s
[hermeticity] sentinel checked 13 test(s)
[netguard] blocked 2 attempt(s) from 1 node(s)
[netguard]   tests/test_zz_s78f8_probe.py::test_f15_route_end_to_end [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=f8-probe start=2026-10-17 05:24:46 end=2026-10-17 05:25:19 elapsed=33s bound=600s status=OK rc=0
```

The real-entry harness the probe used (and the RED file reuses, section 4): the REAL
`compare_from_text` -> REAL `_compare_from_text_impl` -> REAL `_fetch_product_data` x2, with
`scs.parse_product_query` / `scs._resolve_pair_category` / `scs.search_web` / tier2 / tier3 /
`collect_retailer_ratings` / `get_product_image_url` / `find_matching_drugs` and the instance leaves
`_get_specs` / `_get_price` / `_get_reviews` / `_smart_fallback_extract` / `_track_serper_cost` stubbed;
`_get_verified_rating` HANGS (sleep 60) so the cap (`STREAM_HARD_CAP_SECONDS = 1.0`) fires in Phase 2,
after both products' loops ran -- the capture-3 shape. Leaves "raise" = `raise asyncio.TimeoutError()`.

Measured lines (condensed from `[probe]` JSON):

| Probe | Result at base |
|---|---|
| Q1 | python 3.12.9; `asyncio.TimeoutError is TimeoutError` True; gather(return_exceptions=True) over [wait_for(raise asyncio.TimeoutError), wait_for(raise TimeoutError), wait_for(sleep 5, 0.05), ok None, RuntimeError, a cancelled task] -> types [TimeoutError, TimeoutError, TimeoutError, NoneType, RuntimeError, CancelledError]; isinstance asyncio.TimeoutError [T, T, T, F, F, F]; isinstance Exception [T, T, T, F, T, **F**]; inner and cap results the same class; wall 0.05 s. The `_stash_price_cb` shape writes NO key on an inner timeout and writes `price: None` on a completed None. |
| F2 all four leaves raise | `INSUFFICIENT_DATA`, keys [api_calls, code, elapsed_seconds, error, success, total_cost], error == the incomplete sentence; 8 `[L2.6] Phase 1 race timeout` lines (4 per product); one `[L2.7] ... no usable partial` WARNING; `_partial_product_data` None; buffer both slots: extra keys {image_url, price, reviews, specs}, specs None, price None; wall 1.002 s. The same with the whey pair parsed as supplements (wall 1.005 s). |
| F3b reviews returns a value | INSUFFICIENT_DATA; 6 race-timeout lines (no reviews line); buffer reviews set on both. |
| F3 specs returns None | INSUFFICIENT_DATA; 6 lines (no specs line). |
| F6 specs raises RuntimeError | INSUFFICIENT_DATA; two ERROR `Error fetching specs: RuntimeError`; 6 timeout lines. |
| F7 price stub parks a price then raises TimeoutError | `success` True, `metadata.partial` True, WARNING `... returning best-available PARTIAL`; buffer price not None. |
| F12 `include_specs=False` | INSUFFICIENT_DATA; buffer has NO `specs` key (extra keys {image_url, price, reviews}). |
| Q2 mid-gather (specs + price hang, reviews / image return) | INSUFFICIENT_DATA; buffer both slots extra keys `[]` (IDENTITY ONLY); 0 race-timeout lines; wall 1.003 s. |
| Q2 mid-gather, price completes None, specs hangs | INSUFFICIENT_DATA; buffer extra keys `["price"]`, price None -- the price callback wrote the key. |
| Q4 `_scenario("rest"/"stream", QUERY, cap=0.5, slow=True)` | REST: success True, partial True, no code; stream: [status, status, settle_complete, complete], complete success True, partial True. |
| F13 cost `asyncio.run(_all_digests())` | 9 digests, moved [] vs the fixture, wall 1.313 s. |
| F15 TestClient GET + POST `/api/v1/text/compare`, real svc with an F1-shape hang impl, cap 0.2 | 400 / 400, envelope code INSUFFICIENT_DATA, keys [code, error, request_id, success]; netguard: 2 SENTINEL attempts (`neutralized.supabase.invalid`), no egress. |

### 1.6 Every existing test that pins this region (Q5)

`grep -rln "Comparison data was incomplete" tests/` -> 6 files; `grep -rl STREAM_HARD_CAP_SECONDS tests/ | xargs grep -l INSUFFICIENT_DATA` -> 6 files. Classified:

| File | What it pins | Sees the unit? |
|---|---|---|
| tests/test_compare_timeout_graceful.py | the handler via a hanging `_compare_from_text_impl` that seeds `_partial_product_data` (never the buffer): partial (65-99, 102-140), INSUFFICIENT_DATA code only (144-165, specs None + price None dicts), TIMEOUT when nothing stashed (169-183), no scary vocab (187-205), fast pass-through (209-220) | flag OFF only (no node sets the flag); under the flag ON 144-165 stays INSUFFICIENT_DATA (buffer None -> F9) |
| tests/test_compare_from_text_hard_cap.py | TIMEOUT on a slow impl with nothing stashed (19-50), pass-through, no swallow, stream no double cap | no (nothing resolved -> TIMEOUT branch) |
| tests/test_partial_specs_stash_on_price_timeout.py | the early buffer (`_mock_phase1` 45-, real `_fetch_product_data`, `explicit_pair`): specs land -> partial, price lands -> partial, **both hang -> INSUFFICIENT_DATA "NOT a bare TIMEOUT" (182-193)**, stash OFF -> TIMEOUT (195-) | flag OFF only; 182-193 is exactly the F1b shape and FLIPS under the flag ON by design (stated limit 15) |
| tests/test_timeout_partial_integration.py | `test_wrapper_insufficient_data_when_no_product_stash` accepts `code in (INSUFFICIENT_DATA, TIMEOUT)` (400-418); route nodes with mocked results | no |
| tests/test_http_400_cap_cut_mapping.py | route mapping with a MOCKED service (`TIMEOUT_RESULT` 65-70, `INSUFFICIENT_RESULT` 72-77): TIMEOUT -> 503 GET/POST (81-108), INSUFFICIENT_DATA -> 400 (125-136) | no (mocked body) |
| tests/test_text_routes_error_mapping.py | `_surface_comparison_failure` with literal dicts | no |
| tests/test_retro_w2_1.py | a literal INSUFFICIENT_DATA dict (377-379) | no |
| tests/test_text_error_envelope_no_raw_exception.py | a literal dict (355-356) | no |
| tests/test_w4_13_measurement_truth.py + tests/test_w4_13_flag_off_ledger.py + fixtures | a FAKE `_Svc` (318-323) returning `FAIL_ID` (263-265, with an ASCII hyphen, not U+2014) | no (route level, mocked service) |
| tests/test_be_harness.py | the BE harness classifier over recorded envelopes (`INCOMPLETE` 258) | no |
| tests/test_phase1_per_race_timeouts.py | the loop's `[L2.6]` family; nodes at :28 and :128 are `live_unit` (deselected) | the loop is not edited |
| tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main | 9 digests incl. `rest_q_partial_gather` / `stream_q_partial_gather` (a `_slow_fetch` that seeds specs, 175-181) | flag OFF; F13 re-runs it ON |
| tests/test_lane2_integration.py | accepts TIMEOUT / INSUFFICIENT_DATA | `integration` marker (35), never run |

Q5 answer: no existing test reads the cap handler's INSUFFICIENT_DATA body from the REAL service by exact
bytes; the W4-13 ledger is route-level over a fake service and cannot see the unit.

### 1.7 The brief's open questions, answered by measurement

- **Q1 (inner TimeoutError vs the cap's).** Yes, identical: on 3.12.9 `asyncio.TimeoutError is TimeoutError`, a `wait_for` re-raises a coroutine's own TimeoutError unchanged, and `gather(return_exceptions=True)` returns that instance (probe Q1); through the real entry all four stubbed-raise leaves produce the 8 base `[L2.6] Phase 1 race timeout` lines in 1.0 s (probe F2). F2 stubs the leaves; no 8-15 s waits.
- **Q2 (a pre-loop `price` writer).** YES: `_stash_price_cb` (scs:5578-5584) writes `result["price"]` on any COMPLETED price race, None included (probe Q2 price-none: key present, value None); on timeout / cancel / error it writes nothing (probe Q1 + Q2 mid-gather: identity keys only). D4's mid-gather rule ("neither `specs` nor `price` is a key") is therefore correct, and it relies on BOTH callbacks, not only the specs one.
- **Q3 (the whey capture under D4).** Capture 3: both products logged their per-race timeouts (A at 03:59:33, B at 03:59:38), so both loops ran and, under the flag, both slots carry a recorded dict: A = {specs: timeout, price: timeout, reviews: timeout, image_url: timeout}; B = {specs: timeout, price: timeout, reviews: ok, image_url: timeout}. The cap fired at 03:59:46 in the post-loop stages (Phase 2 / tiers), `_partial_product_data` None, `_partial_has_usable_data()` False (the handler returned INSUFFICIENT_DATA, so price was None on both: `_price_fallback_on_miss` found nothing). Predicate: buffer slots 0, 1 populated; slot 0 recorded, price timeout, specs timeout -> all-timeout; slot 1 recorded, price timeout, specs timeout (reviews ok ignored) -> all-timeout -> True -> TIMEOUT -> 503. Reproduced by F3b (probe F3b: base INSUFFICIENT_DATA on that shape).
- **Q4 (the `_scenario` partial shapes).** `_slow_fetch` (test_s75_fanout_identity.py:175-181) seeds `specs: {"display": "6.1 in"}` -> `_partial_has_usable_data()` True -> the PARTIAL branch on REST and the stream partial (probe Q4: both success True, partial True). The new code sits inside the INSUFFICIENT_DATA branch, so neither partial-gather digest can move in either flag state; and `_slow_fetch` REPLACES `_fetch_product_data`, so the record block never runs in those two scenarios. FY25 is unaffected OFF (probe F13: 9/9 at base).
- **Q5.** Section 1.6.
- **Q6 (`__new__`-built instances).** `grep -rnE "StructuredComparisonService\.__new__|__new__\(\s*(scs\.)?StructuredComparisonService" tests/` -> 7 sites in 6 files: test_cascade_hardening.py:11, test_js_rendering.py:43 and :101, test_luxury_price_tiers.py:10, test_page_scraping.py:132, test_prompt_fence.py:337, test_retro_w0_4.py:526. Every new attribute read (the record block, the predicate, the log-count helper) is a `getattr(self, name, None)` with an `isinstance` check; F18 row 12 pins it.

---------------------------------------------------------------------------------------------------

## 2. The exact change (code sketch per site)

All edits are in `scs` (Edit tool only, CRLF preserved; `git diff` shows added lines only, no changed or
removed line; a whole-file diff is a defect). Callers of `_fetch_product_data` re-grepped over `app/` and
`scripts/`: scs:4124-4125 and scs:4762-4763 only. No new import (`asyncio`, `Tuple`, `Dict`, `logger` are module-level: `from typing import
Optional, List, Dict, Any, Tuple, Callable, Awaitable` scs:21). The base loop (5780-5798), the
done-callbacks, `_partial_has_usable_data`, `_early_specs_buffer_list`, both bodies' existing bytes and
the stream handlers are NOT edited.

### 2.1 Module helper (after `_flag_on` / the FANOUT knob readers, scs:~1790)

```python
def _phase1_race_outcome(res: Any) -> str:
    """S78-F8 (D3): classify one Phase-1 gather result the way the post-gather loop
    does (scs:5781 / :5792): an asyncio.TimeoutError instance (the per-race wait_for
    cap OR a TimeoutError raised inside the race -- one class since 3.11) ->
    "timeout"; any other BaseException instance (CancelledError included, which the
    loop stores as a value) -> "error"; anything else (None included) -> "ok". Pure."""
    if isinstance(res, asyncio.TimeoutError):
        return "timeout"
    if isinstance(res, BaseException):
        return "error"
    return "ok"
```

### 2.2 Instance state (`__init__`, after scs:3265)

```python
        # S78-F8 (D3) -- per-run Phase-1 race outcomes, slot -> {race key ->
        # "timeout" | "error" | "ok"}, written after the post-gather loop under
        # ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT only, read only by the REST hard-cap
        # handler's INSUFFICIENT_DATA branch under the same flag. Reset per run.
        self._phase1_race_outcomes: Dict[int, Dict[str, str]] = {}
```

### 2.3 Per-run reset at both entries (unconditional, the `_phase2_skipped` precedent)

- scs:3991 (REST impl), after `self._early_specs_buffer = [None, None]`: `self._phase1_race_outcomes = {}`
- scs:4625 (stream), after `self._early_specs_buffer = [None, None]`: `self._phase1_race_outcomes = {}`

### 2.4 The record block (after the loop, between scs:5798 and the S3 L1.5 block at scs:5800)

```python
        # S78-F8 (D3) -- record each Phase-1 race's outcome for the REST hard-cap
        # handler (ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT, read per call). Additive: the
        # loop above is unchanged; flag OFF (or partial_slot None) writes nothing.
        if partial_slot is not None and _flag_on("ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT"):
            _outcomes = getattr(self, "_phase1_race_outcomes", None)
            if not isinstance(_outcomes, dict):
                _outcomes = {}
                self._phase1_race_outcomes = _outcomes
            _outcomes[partial_slot] = {
                key: _phase1_race_outcome(phase1_results[i])
                for i, key in enumerate(phase1_keys)
            }
```

Key order is `phase1_keys` order (specs, price, reviews, image_url, each only when it ran). The block
runs on the stream path too (shared function); nothing consumes it there.

### 2.5 The predicate and the log-count helper (on the class, after `_partial_has_usable_data`, scs:~3548)

```python
    def _cap_all_data_races_timed_out(self) -> bool:
        """S78-F8 (D4) -- ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT (default OFF, read per
        call): True when every product the early buffer registered ran out of time
        on every Phase-1 DATA race (specs when it ran, price always) and completed
        none. reviews / image_url never count (capture 3). Fail-closed: any missing
        or contrary evidence -> False (the base INSUFFICIENT_DATA body). Flag OFF:
        returns False before any state is read."""
        if not _flag_on("ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT"):
            return False
        buffer = getattr(self, "_early_specs_buffer", None)
        if not isinstance(buffer, list):
            return False
        outcomes = getattr(self, "_phase1_race_outcomes", None)
        if not isinstance(outcomes, dict):
            outcomes = {}
        populated = 0
        for slot, pd in enumerate(buffer):          # the slot index, never the compacted list
            if not isinstance(pd, dict):
                continue
            populated += 1
            recorded = outcomes.get(slot)
            if isinstance(recorded, dict):          # this product's loop ran under the flag
                if recorded.get("price") != "timeout":
                    return False
                if "specs" in recorded and recorded["specs"] != "timeout":
                    return False
            elif "specs" in pd or "price" in pd:    # mid-gather: a landed key = a completed race
                return False
        return populated > 0

    def _cap_timeout_log_counts(self) -> Tuple[int, int, int, int]:
        """S78-F8 (D5, amended 7.1): (products, data races timed out, data races
        recorded, products cut mid-gather) for the one WARNING line. Called only
        after _cap_all_data_races_timed_out() returned True. Pure."""
        buffer = getattr(self, "_early_specs_buffer", None)
        outcomes = getattr(self, "_phase1_race_outcomes", None)
        if not isinstance(outcomes, dict):
            outcomes = {}
        products = timed_out = recorded = cut = 0
        for slot, pd in enumerate(buffer if isinstance(buffer, list) else []):
            if not isinstance(pd, dict):
                continue
            products += 1
            rec = outcomes.get(slot)
            if isinstance(rec, dict):
                for key in ("specs", "price"):
                    if key in rec:
                        recorded += 1
                        if rec[key] == "timeout":
                            timed_out += 1
            else:
                cut += 1
        return products, timed_out, recorded, cut
```

### 2.6 The handler branch (an INSERTION at the top of the INSUFFICIENT_DATA branch, between scs:3885 and 3886)

```python
            if self._partial_product_data or self._early_specs_buffer_list():      # scs:3885, unchanged
                if self._cap_all_data_races_timed_out():                          # NEW
                    _p, _to, _rec, _cut = self._cap_timeout_log_counts()          # NEW
                    logger.warning(                                               # NEW (D5)
                        "[L2.7] hard-cap: every Phase-1 data race timed out "
                        "(products=%d, races timed out=%d/%d, cut mid-gather=%d) "
                        "for query=%r -- reporting TIMEOUT, not INSUFFICIENT_DATA",
                        _p, _to, _rec, _cut, query,
                    )
                    return {                                                      # NEW: the base TIMEOUT body, same five keys
                        "success": False,
                        "error": TIMEOUT_FRIENDLY_MESSAGE,
                        "code": "TIMEOUT",
                        "elapsed_seconds": round(elapsed, 2),
                        "total_cost": self.total_cost,
                    }
                return {                                                          # scs:3886-3893, unchanged bytes
                    ...
```

The predicate is consulted ONLY inside that branch: after `_partial_has_usable_data()` was False (or the
partial build raised) and after the base "no usable partial" WARNING (3875-3879), which therefore still
fires exactly once. No new body key; the copy is the base TIMEOUT copy. ASCII `--` in the new line (the
two base `[L2.7]` WARNINGs keep their U+2014).

Log regex (logger `app.services.structured_comparison_service`, level WARNING):
`^\[L2\.7\] hard-cap: every Phase-1 data race timed out \(products=(\d+), races timed out=(\d+)/(\d+), cut mid-gather=(\d+)\) for query='.*' -- reporting TIMEOUT, not INSUFFICIENT_DATA$`

### 2.7 Docs (D10, GREEN)

One CLAUDE.md paragraph under **Environment Variables -> Feature Flags**:
"**SESSION 79 flag (S78-F8, 2026-10-17; default OFF, read per call):** `ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT`
..." (effect ON, flag-OFF identity, the limits of section 6, canary = a unit test plus log review of the
next natural occurrence of the D5 line, rollback = unset). Two tests read CLAUDE.md
(`tests/test_ci_gates.py:1392` asserts "never `--branch production`" is present;
`tests/test_behavior_dimension_translation.py:226-233` reads the `scoring_method` enum lines) -- both are
in the comm set; an additive paragraph moves neither. The TG row (#355) and SM row (#356) insert at the
same anchor; the PR body states the merge order (#354, #355, #356, then this unit, rebased).

---------------------------------------------------------------------------------------------------

## 3. Flag-OFF identity argument

With `ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT` unset (or any value outside `{"true","1","yes","on"}` after
`.strip().lower()`):

1. The handler's partial branch, the build-failure ERROR and the "no usable partial" WARNING run exactly as at base; the new code is reached only inside the INSUFFICIENT_DATA branch.
2. There, `_cap_all_data_races_timed_out()` executes one statement with an effect, `os.getenv("ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT", "")`, and returns False: it reads neither `_early_specs_buffer` nor `_phase1_race_outcomes` (F4c with raising class properties), logs nothing, and `_cap_timeout_log_counts` is never called. The base `return {...}` (3886-3893) follows with the same expressions, so the body is byte-identical (six keys, the U+2014 sentence, `api_calls`).
3. The TIMEOUT branch (nothing resolved) is not touched.
4. The record block: `partial_slot is not None and _flag_on(...)` -> False -> nothing written; `self._phase1_race_outcomes` stays `{}` from `__init__` and both resets (F4b). With `partial_slot` None no env read happens at all.
5. `_phase1_race_outcome` and both new methods are defined but never called OFF; defining them executes nothing at import.
6. The loop, the done-callbacks, `phase1_results`, `result`, the `[L2.6]` lines, `_source_trace` and every downstream call are the base sequence: the record block only READS `phase1_results` / `phase1_keys`.
7. The only flag-OFF delta: one extra `os.getenv` per orchestrator product, one extra `os.getenv` per INSUFFICIENT_DATA cap, one dict attribute (never serialised) and two dict resets.
8. Flag ON on any path that is not "INSUFFICIENT_DATA branch + all data races timed out": the predicate returns False (or is never consulted) and the base body ships; the record block writes an attribute nothing else reads. So "flag ON, success / partial / stream / H6" is also byte-identical (F13: the 9 FY25 digests with the flag ON).

Proof obligations in the gate: F4a/F4b/F4c, F5-off, F7, F8a, F9, F13, F14 (FY25 unchanged, existing
node), the existing handler pins of 1.6 green at HEAD, and the comm set `branch-only-NEW == []`.

---------------------------------------------------------------------------------------------------

## 4. RED test list

New file `tests/test_s78_all_timeout_cap_as_timeout.py` (pure ASCII, LF, no credential shape -- any
sentinel built by concatenation; bounded runner only; the worktree's conftest wires `tests/_netguard.py`,
so run bare; no edit to any existing test file or fixture). Harness:

- `import app.main` (configure_logging) and `import app.services.structured_comparison_service as scs`; `SCS_LOGGER = "app.services.structured_comparison_service"`; F13 imports `_all_digests` / `FIXTURE` from `tests.test_s75_fanout_identity` (TG-A7: helpers only, never a `test_*` name).
- `UNIT_ENV = ("ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT", "ENABLE_EARLY_SPECS_STASH", "ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET", "ENABLE_UNIFIED_SEARCH_BOUND", "ENABLE_PHASE2_RESIDUAL_GUARD", "ENABLE_TIER_FILL_RESIDUAL_GUARD", "DEBUG_STAGE_TIMINGS")`; an autouse fixture `delenv`s all of them first and sets `scs._DEBUG_STAGE_TIMINGS = False` via monkeypatch (TG-A1).
- `TIMEOUT_KEYS = {"success", "error", "code", "elapsed_seconds", "total_cost"}`; `INSUFF_KEYS = TIMEOUT_KEYS | {"api_calls"}`; `INCOMPLETE = "Comparison data was incomplete " + chr(0x2014) + " choose different products."`.
- `CAP_RE` = the regex of 2.6; `_cap_lines(caplog)` = WARNING records of `SCS_LOGGER` starting `[L2.7] hard-cap: every`; `_no_usable_lines(caplog)` = records containing `no usable partial`.
- `IDENT(name)` = `{"brand": "", "name": name, "full_name": name, "variant": None, "category": "supplements", "query": name}` (the six identity keys of scs:5503-5506).
- `_NoReadDict(dict)`: `__getitem__`, `get`, `__contains__`, `__iter__`, `__len__`, `__bool__`, `keys`, `items`, `values` raise `AssertionError("S78-F8: the flag-OFF path read _phase1_race_outcomes")`. `_boom_property()` = `property(lambda self: (_ for _ in ()).throw(AssertionError(...)))`-style raising getter, installed on the CLASS after construction with `monkeypatch.setattr(scs.StructuredComparisonService, name, prop, raising=False)` (a data descriptor wins over the instance dict, so ANY read raises, `getattr(..., default)` included).
- `_hang_impl(svc, seed)`: the test_compare_timeout_graceful pattern (`_impl(*a, **k)`: `seed(svc)`; `await asyncio.sleep(60)`) installed with `monkeypatch.setattr(svc, "_compare_from_text_impl", _impl)`; `STREAM_HARD_CAP_SECONDS = 0.2`.
- `_install_real(svc, monkeypatch, *, specs, price, reviews, image, rating=_hang, parsed=PAIR, cap=1.0)`: the section 1.5 real-entry harness (copied from the probe). Leaves: `_raise_t` (`raise asyncio.TimeoutError()`), `_raise_rt` (`raise RuntimeError(...)`), `_hang` (sleep 60), per-product stubs keyed on `name` where a row needs one product different. Measured base wall about 1.0 s per compare.
- `_fetch_direct(svc, *, partial_slot, include_specs=True, include_reviews=True, leaves=...)`: the TG `_fetch` idiom (`_tier_mocks` leaves, `asyncio.wait_for(svc._fetch_product_data(dict(P), "bahrain", include_specs, include_reviews, nocache=True, partial_slot=slot), 20.0)`), Phase 2 not hung.
- PIN rows read the record with `getattr(svc, "_phase1_race_outcomes", {})` (TG-A4), never a direct attribute read.

RED = fails at base `e0f3e475` ON AN AssertionError (the TG idiom: a missing helper is read with
`getattr(scs, name, None)` / `getattr(svc, name, None)` and asserted callable or equal, never an
AttributeError; or the base INSUFFICIENT_DATA body / missing line where TIMEOUT is wanted) and passes
after GREEN. PIN = passes at base and must stay green.

| ID | Kind | Setup | Assertions | Why it fails at base | How it passes |
|---|---|---|---|---|---|
| F1 | RED | flag `true`; `_hang_impl` seeds `svc._early_specs_buffer = [IDENT("A"), IDENT("B")]`; `_phase1_race_outcomes` untouched (`{}` from `__init__`) | `code == "TIMEOUT"`; `set(body) == TIMEOUT_KEYS`; `error == scs.TIMEOUT_FRIENDLY_MESSAGE`; `elapsed_seconds` a float; exactly ONE `CAP_RE` line, groups (2, 0, 0, 2); exactly ONE "no usable partial" line (the base WARNING kept) | base returns INSUFFICIENT_DATA with `api_calls` (probe F15 measured the same seed through the route: 400 INSUFFICIENT_DATA) | mid-gather arm: no record, no `specs`/`price` key in either dict -> True |
| F1b | RED | flag `true`; `_install_real` with `specs=_hang, price=_hang`, reviews / image return, rating left at the default hang (never reached: the cap fires mid-gather) | TIMEOUT; one line, groups (2, 0, 0, 2); `svc._early_specs_buffer` dicts carry only the six identity keys; `getattr(svc, "_phase1_race_outcomes", {}) == {}` (no loop ran) | probe Q2: base INSUFFICIENT_DATA, identity-only buffer | the done-callbacks write nothing on a cancel; mid-gather arm |
| F2 | RED | flag `true`; `_install_real` with all four leaves `_raise_t`, rating hangs | `getattr(svc, "_phase1_race_outcomes", None) == {0: {"specs": "timeout", "price": "timeout", "reviews": "timeout", "image_url": "timeout"}, 1: <same>}`; TIMEOUT, `TIMEOUT_KEYS`; one line, groups (2, 4, 4, 0); the 8 base `[L2.6] Phase 1 race timeout` lines still logged | probe F2: base INSUFFICIENT_DATA; no attribute (the getattr reads None) | record block + recorded arm |
| F3 | PIN | flag `true`; (a) `_install_real` with `_get_specs` returning None for product A only, `_raise_t` for B, other leaves `_raise_t`; (b) `_hang_impl` seeds `buffer = [IDENT("A"), dict(IDENT("B"), specs=None)]` and `svc._phase1_race_outcomes = {0: {"specs": "timeout", "price": "timeout"}}`; (c) `_install_real` with `specs=_hang`, price returns None (probe Q2 price-none) | (a) INSUFFICIENT_DATA, `INSUFF_KEYS`, `error == INCOMPLETE`, record slot of A has `specs == "ok"`; (b) and (c) INSUFFICIENT_DATA; no `CAP_RE` line in any | (passes: probe F3 / Q2 price-none measured INSUFFICIENT_DATA) | a completed data race keeps the base verdict (recorded arm specs ok; mid-gather landed `specs` key; landed `price` key) |
| F3b | RED | flag `true`; `_install_real`, all leaves `_raise_t` except `_get_reviews` returns `{"summary": "ok"}` (capture 3) | TIMEOUT; record `reviews == "ok"` on both slots; one line, groups (2, 4, 4, 0) | probe F3b: base INSUFFICIENT_DATA | reviews never counts |
| F4a | PIN | flag UNSET; F1 seed plus `svc._phase1_race_outcomes = _NoReadDict()` inside the seed | INSUFFICIENT_DATA; `set(body) == INSUFF_KEYS`; `error == INCOMPLETE`; `api_calls` present; no `CAP_RE` line; the stand-in never raised | (passes: base never reads the attribute) | flag OFF returns before any state read |
| F4b | PIN | flag UNSET; F2 setup (real `_fetch_product_data`) | INSUFFICIENT_DATA; `getattr(svc, "_phase1_race_outcomes", {}) == {}` | (passes: no attribute -> default `{}`) | the record block writes nothing OFF |
| F4c | RED | flag UNSET; `svc = StructuredComparisonService()`; then raising CLASS properties for `_early_specs_buffer` and `_phase1_race_outcomes`; call `svc._cap_all_data_races_timed_out()` | returns False; no AssertionError | the method is missing (getattr None -> the callable assert fails) | the flag is the first statement |
| F5-on | RED | flag value in `["true", "TRUE", " true ", "1", "yes", "ON", "on"]`, F1 seed | TIMEOUT, one line | INSUFFICIENT_DATA | `_flag_on` (strip + lower + the house set) |
| F5-off | PIN | flag value in `[None, "", "false", "0", "no", "off", "garbage", "tru e"]`, F4a seed (`_NoReadDict`) | INSUFFICIENT_DATA, `INSUFF_KEYS`, no line, stand-in never raised | (passes) | not truthy -> no read |
| F6 | PIN | flag `true`; `_install_real` with `specs=_raise_rt`, other leaves `_raise_t` | INSUFFICIENT_DATA, `INSUFF_KEYS`; record `specs == "error"`, `price == "timeout"` on both; two ERROR `Error fetching specs: RuntimeError` lines (base); no `CAP_RE` line | (passes: probe F6) | only "timeout" flips; an error keeps the base verdict (D7) |
| F7 | PIN | both flag states (parametrised); `_install_real` with a `_get_price` stub that parks `{"amount": 9.5, "currency": "BHD", "source_method": "converted_usd", ...}` under `scs._product_display_identity(brand, name, variant, search_query, False)[0]` then raises TimeoutError | `success is True`; `metadata.partial is True`; no `CAP_RE` line; under ON the record has `price == "timeout"` | (passes: probe F7) | `_price_fallback_on_miss` returns the parked price -> usable -> PARTIAL; the predicate is never consulted |
| F8a | PIN | flag `true`; REAL `_compare_from_text_impl` with `scs.parse_product_query` / `scs._resolve_pair_category` stubbed (the TG R12 `_install_presplit_pipeline` pattern) and `svc._fetch_product_data` replaced by a hang that registers `dict(IDENT(name), specs=None)` in its slot; BEFORE the call `svc._phase1_race_outcomes = {0: {"specs": "timeout", "price": "timeout"}, 1: <same>}` (stale) | INSUFFICIENT_DATA; no `CAP_RE` line | (passes: base never reads) | the REST entry reset (3991) drops the stale all-timeout record, so the mid-gather arm sees the landed `specs` key |
| F8b | RED | as F8a for REST (`stale = {9: {"price": "timeout"}}`), and separately the stream entry driven to its partial (TG R12 `_stream_to_complete` with a hang that seeds specs) | after each entry `getattr(svc, "_phase1_race_outcomes", None) == {}` | the stale seed survives (nothing resets at base) | both entry resets |
| F9 | PIN | flag `true`; the test_compare_timeout_graceful 144-165 seed: `_partial_product_data = [specs None / price None dicts]`, buffer untouched (None), no outcomes | INSUFFICIENT_DATA, `INSUFF_KEYS`, no line | (passes) | buffer not a list -> False (fail-closed to base) |
| F10 | RED | `scs._phase1_race_outcome(x)` table | `asyncio.TimeoutError()` -> "timeout"; `TimeoutError()` -> "timeout"; `RuntimeError()` -> "error"; `asyncio.CancelledError()` -> "error"; `KeyboardInterrupt()` -> "error"; `None`, `{}`, `{"amount": 1.0}`, `0`, `False`, `"x"` -> "ok" | the helper is missing (getattr None -> the callable assert fails) | 2.1 |
| F11 | RED | flag `true`; `_fetch_direct` with specs returning a dict, price `_raise_t`, reviews `_raise_rt`, image returning None; slots 0, 1 and None; plus `include_reviews=False` and `include_specs=False` runs | read with `rec = getattr(svc, "_phase1_race_outcomes", None)`: slot 0 -> `{0: {"specs": "ok", "price": "timeout", "reviews": "error", "image_url": "ok"}}` with `list(rec[0]) == ["specs", "price", "reviews", "image_url"]`; slot 1 -> key 1; slot None -> `{}` (fresh instance per run); include_reviews False -> keys `["specs", "price", "image_url"]`; include_specs False -> keys `["price", "reviews", "image_url"]` | no record (`rec` is None) | 2.4 |
| F12 | RED | flag `true`; (a) `_install_real` all `_raise_t`, `compare_from_text(..., include_specs=False)`; (b) the same with `include_reviews=False` too | TIMEOUT; records have no `specs` key; one line, groups (2, 2, 2, 0) | probe F12: base INSUFFICIENT_DATA | price alone decides; reviews irrelevant |
| F13 | PIN | `monkeypatch.setenv("ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT", "true")`; `asyncio.run(_all_digests())` (the 9 FY25 scenarios; `_scenario` pops only its own UNIT_ENV, so the flag survives) | the 9 digests equal `FIXTURE["digests"]` | (passes: probe F13, 9/9 at base, 1.3 s) | flag ON moves no byte on REST full / REST partial / stream full (the record block runs, nothing consumes it) / stream partial / parse-fail / private marks |
| F14 | PIN | existing node `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main` | unchanged | (passes) | flag OFF moves no byte |
| F15 | RED | `fastapi.testclient.TestClient(app)`; `limiter.reset()`; `patch("app.api.text_routes.get_comparison_service", lambda: svc)` with a real svc carrying the F1 hang; cap 0.2; parametrise ON / OFF; GET `/api/v1/text/compare?q=A One vs B Two&nocache=true` and POST `{"query": ...}` | ON: 503, `json()["code"] == "TIMEOUT"`; OFF: 400, `"INSUFFICIENT_DATA"` | ON half: probe F15 measured 400 at base | the handler + the existing 503 mapping. Netguard: 2 SENTINEL attempts per node (route fire-and-forget), no egress; the ratchet fails only on a new EGRESS node |
| F18 | RED | flag `true`; direct `svc._cap_all_data_races_timed_out()` on seeded state (rows below) | each row's expected bool | the method is missing (getattr None -> the callable assert fails) | 2.5 |

F18 rows (buffer, outcomes -> expected): (1) None, {} -> False; (2) `[None, None]`, all-timeout for 0 and 1 -> **False** (empty buffer); (3) `[IDENT, IDENT]`, {} -> True; (4) `[dict(IDENT, specs=None), IDENT]`, {} -> False; (5) `[dict(IDENT, price=None), IDENT]`, {} -> False; (6) `[IDENT, IDENT]`, `{0: {"specs": "timeout", "price": "timeout"}, 1: {"specs": "error", "price": "timeout"}}` -> False; (7) `{.., 1: {"specs": "timeout", "price": "ok"}}` -> False; (8) both `{"specs": "timeout", "price": "timeout", "reviews": "ok", "image_url": "ok"}` -> True; (9) both `{"price": "timeout"}` (no specs race) -> True; (10) both `{"specs": "timeout"}` (no price key) -> False; (11) **slot index**: buffer `[None, IDENT]`, outcomes `{0: {"price": "ok"}, 1: {"specs": "timeout", "price": "timeout"}}` -> True (the compacted list would read slot 0's record and return False); (12) a `__new__`-built instance (`scs.StructuredComparisonService.__new__(...)`) with only `_early_specs_buffer = [IDENT, IDENT]` set (no `_phase1_race_outcomes` attribute) -> True, no AttributeError; (13) recorded slot 0 all-timeout, slot 1 mid-gather identity-only -> True (mixed arms); (14) outcomes not a dict (`svc._phase1_race_outcomes = None`) with `[IDENT, IDENT]` -> True.

Rulings tables in the tests: F5-on / F5-off is the TG1 flag-reader table; F10 the D3 classifier table; F18
the D4 decision table.

### 4.1 Mutation table (applied to the GREEN bytes; byte-copy restore + sha256 compare; `--bound 600` per mutant)

| # | Mutant | Killed by |
|---|---|---|
| M1 | flag check removed from the predicate (always ON) | F4a, F4c, F5-off |
| M2 | reader `os.getenv("ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT") == "true"` (no strip / lower / set) | F5-on (`TRUE`, `" true "`, `1`, `yes`, `ON`) |
| M3 | flag read moved after the buffer / outcomes reads | F4c |
| M4 | reviews counted as a data race | F3b, F18 (8) |
| M5 | image_url counted as a data race | F18 (8), F2 vs F3b groups |
| M6 | "error" counted as timeout (outcome) or `isinstance(res, Exception)` -> "timeout" | F6, F18 (6) |
| M7 | `_phase1_race_outcome` tests `Exception` instead of `BaseException` (CancelledError -> "ok") | F10 (CancelledError, KeyboardInterrupt) |
| M8 | slot index lost (`enumerate(self._early_specs_buffer_list())`) | F18 (11) |
| M9 | recorded arm ignores the specs outcome (price only) | F6, F3 (a), F18 (6) |
| M10 | recorded arm ignores a missing price key (`.get("price", "timeout")`) | F18 (10) |
| M11 | mid-gather arm ignores a landed `specs` key | F3 (b), F18 (4) |
| M12 | mid-gather arm ignores a landed `price` key | F3 (c), F18 (5) |
| M13 | predicate returns True on an empty buffer (`return True` / `populated >= 0`) | F18 (2) |
| M14 | TIMEOUT body gains `api_calls` (or any key) | F1, F2, F3b, F12 (`TIMEOUT_KEYS`) |
| M15 | TIMEOUT body uses the INSUFFICIENT_DATA copy or another code | F1 (`error`, `code`), F15 |
| M16 | the D5 line removed, or its format / counts changed | F1, F2, F3b, F12 (regex + groups) |
| M17 | the base "no usable partial" WARNING moved after / dropped for the new branch | F1 (count == 1) |
| M18 | REST entry reset removed | F8a, F8b (REST half) |
| M19 | stream entry reset removed | F8b (stream half) |
| M20 | record block writes under flag OFF | F4b |
| M21 | record block also for `partial_slot` None (key None or 0) | F11 (slot None row) |
| M22 | record block placed before the loop or mutating `result` / `phase1_results` | F2 (8 `[L2.6]` lines), F13 |
| M23 | predicate consulted before the partial branch (or in place of `_partial_has_usable_data`) | F7 (ON: must stay PARTIAL) |
| M24 | `getattr` default dropped (`self._phase1_race_outcomes`) | F18 (12) |
| M25 | `isinstance(outcomes, dict)` check dropped | F18 (14) |

---------------------------------------------------------------------------------------------------

## 5. Gates

### 5.1 Unit file, lint, syntax

- `tests/test_s78_all_timeout_cap_as_timeout.py` green at HEAD (the flag is set per node; also run once with the flag exported ON in the runner env, every node green), RED-count at base = the RED rows above (AssertionError only, never an AttributeError, an ImportError or a collection error).
- `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache app/services/structured_comparison_service.py tests/test_s78_all_timeout_cap_as_timeout.py`; `-m py_compile` on both.

### 5.2 Comm set

Rule (memory feedback 2026-10-09 + TG5): the module-reference set
`grep -rlE "structured_comparison_service" tests/ --include=*.py` (**182 files** at e0f3e475) UNION the
source-scanning pins (the CLAUDE.md list -- test_model_config.py, test_model_config_enforced.py,
test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command*.py,
test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py,
test_sentry_channels_u8d_unit.py -- plus every `test_*.py` that combines
`rglob|.glob(|os.walk|iterdir|listdir|scandir|ast.parse|read_text|read_bytes|open(` with an `app` path
literal) UNION the CLAUDE.md readers (D10 edits CLAUDE.md: `tests/test_ci_gates.py`, already in, and
`tests/test_behavior_dimension_translation.py`, added). Script
`scratchpad/f8/spec_agent/comm_set.py` (read-only): `modref 182 srcscan 61 added_by_srcscan 37 union 219`.
The 37 source-scan additions = the TG spec's 27 (TG 5, all present) + 10 from the wider regex
(test_attribution_endpoint, test_auth_demographics, test_cohort_service, test_legal_docs_u8_d3c,
test_legal_docs_u8_polish, test_occ_adapter, test_password_reset_deep_link, test_precommit_hook,
test_s71_u13_compare_auth_required, test_secret_scan_static -- kept as a harmless superset). Excluded,
with reasons: `tests/test_precommit_hook_phase_b.py` (TG Q7 ruling stands: synthetic temp repo, never
reads the real `app/`, 20-30 s per node) and `tests/test_precommit_hook.py` (the same class: a temp repo
per scenario reading only `.githooks/pre-commit`, which the unit does not touch). Result: **218 files,
9 chunks (8 x 25 + 18)**, list sha256
`1063f1884189a3ba9dc12132d0efb311e09468f3c823cdbd628b8b50325c0806` (`comm_final.txt`). GREEN adds
the new unit file to the HEAD run and re-greps at HEAD.

Base results (worktree at e0f3e475, bounded runner, conftest netguard; chunks run ALONE, `--bound 1200`):

```
chunk 00: 1371 passed, 12 warnings in 122.19s
[pyt] tag=f8-base-comm00 start=2026-10-17 05:28:25 end=2026-10-17 05:30:33 elapsed=128s bound=1200s status=OK rc=0
chunk 01: 489 passed, 11 warnings in 84.78s
[pyt] tag=f8-base-comm01 start=2026-10-17 05:30:36 end=2026-10-17 05:32:04 elapsed=88s bound=1200s status=OK rc=0
chunk 02: 2107 passed, 1 skipped, 5 deselected, 16 warnings in 226.41s
[pyt] tag=f8-base-comm02 start=2026-10-17 05:32:14 end=2026-10-17 05:36:08 elapsed=233s bound=1200s status=OK rc=0
chunk 03: 546 passed, 13 warnings in 91.09s
[pyt] tag=f8-base-comm03 start=2026-10-17 05:36:11 end=2026-10-17 05:37:53 elapsed=102s bound=1200s status=OK rc=0
chunk 04: 2 failed, 649 passed, 3 deselected, 17 warnings in 108.40s
FAILED tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
FAILED tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
[pyt] tag=f8-base-comm04 start=2026-10-17 05:46:01 end=2026-10-17 05:47:56 elapsed=114s bound=1200s status=FAIL rc=1
chunk 05: 859 passed, 2 skipped, 3 deselected, 1 xfailed, 11 warnings, 2 errors in 151.00s
ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
[pyt] tag=f8-base-comm05 start=2026-10-17 05:47:59 end=2026-10-17 05:50:33 elapsed=154s bound=1200s status=FAIL rc=1
chunk 06: 1405 passed, 1 skipped, 2 deselected, 16 warnings in 321.77s
[pyt] tag=f8-base-comm06 start=2026-10-17 05:50:45 end=2026-10-17 05:56:13 elapsed=328s bound=1200s status=OK rc=0
chunk 07: 451 passed, 1 skipped, 12 deselected, 13 warnings in 146.10s
[pyt] tag=f8-base-comm07 start=2026-10-17 05:56:19 end=2026-10-17 05:58:52 elapsed=152s bound=1200s status=OK rc=0
chunk 08: 997 passed, 4 deselected, 13 warnings in 104.64s
[pyt] tag=f8-base-comm08 start=2026-10-17 05:59:12 end=2026-10-17 06:01:11 elapsed=119s bound=1200s status=OK rc=0
```

Base failure set (4 nodes, all pre-existing, the same 4 the TG spec recorded at this base, TG 5.1):
- `tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest` and `::TestFetchPagePriceOpenGraph::test_og_meta_extraction`: rows 85-86 of `tests/.pre_impl_failures.txt` (CI deselects them).
- `tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable` and `::test_render_digests_match_base_except_the_fence`: ERROR at setup, `AssertionError: test attempted network access: [('getaddrinfo', "'openaipublic.blob.core.windows.net'")]` (test_prompt_truth.py:139) -- this box's tiktoken cache is cold, CI warms it (R22). Environmental, identical on both sides.

Total base wall: 1,418 s of `[pyt]` elapsed for the 9 chunks (the TG measurement at this base: 543 s for its 208 files; budget the HEAD run accordingly). The HEAD gate: the same 9 chunks plus the unit file; `comm -13 <base FAILED+ERROR ids> <head FAILED+ERROR ids>` must be empty.

Chunk lists (sorted; chunk NN = lines 25*NN+1 .. 25*NN+25 of `comm_final.txt`):

```
00: test_account_deletion_u8b test_adapter_drop_visibility test_adapter_prefetch_hook test_algolia_tier2_wiring
    test_arabic_verdict_output_w414 test_async_redis_offload test_async_utils test_attribution_endpoint
    test_auth_demographics test_auth_error_log_hygiene test_be_harness test_behavior_dimension_translation
    test_behavior_integration test_bh_gcc_cascade_wiring test_bh_locale_filter test_bh_pdp_sitelink_harvest
    test_cache_first_render_gate test_cascade_hardening test_cascade_order_regression_qa test_cascade_parallel
    test_category_aware_discovery_i55 test_category_token_fix test_ci_gates test_citation_cleanup
    test_cohort_orchestrator_wire_v2
01: test_cohort_service test_cohort_summary_orchestrator test_compare_from_text_hard_cap
    test_compare_timeout_graceful test_comparison_id_echo test_comparison_quality_detector
    test_comparison_quality_v2 test_comparison_response_image_url test_consent_capture_w3_16
    test_converted_price_before_estimate_t1 test_converted_provenance_fanout test_converted_tier1_parks_for_bh
    test_correctness_consume_and_fairness test_cost_meter_s74 test_cost_tracking test_counterfeit_filter
    test_critical_schema_fields_split test_cron_warm_price_cache test_curl_before_render_budget
    test_decomposed_services test_discovery_window_i54 test_domain_s76 test_error_paths
    test_explicit_pair_category test_explicit_pair_integration_mocked
02: test_extraction_prompt test_extraction_prompt_bundle_c test_fact_checking test_fallback_improvements
    test_fan_out_budget_env test_fan_out_integration test_fire_and_forget_wrap test_flush_live_price_key
    test_fragrance_content_quality test_genuine_beats_converted_selection test_genuine_predicate_parity
    test_genuine_price_clobber_guard test_genuine_price_priority test_genuine_reach_cascade
    test_global_tier_never_genuine test_guidance_insights test_hermeticity_pins test_hostile_jsonld
    test_iherb_rating test_iherb_scraping test_image_identify_llm_unavailable_s69 test_input_validation
    test_js_rendering test_jsonld_shape_ladder test_kpi_session_fixes
03: test_l2_promotion_remaining_ttl test_landing_fallback_pages_s69 test_latency_stack_i56
    test_lazy_bh_pdp_backfill test_legal_disclosure_s77 test_legal_docs_u8 test_legal_docs_u8_d3c
    test_legal_docs_u8_polish test_legal_s78 test_lever1_orphan_cancel_i56 test_logger_no_query_leak
    test_lulu_locale_rewrite test_luxury_brands test_luxury_price_tiers test_m13_04_full_stream_deadline
    test_m13_06_async_redis_offload_writes test_m13_30_get_price_finally test_m13_34_adapter_timeouts
    test_m13_shortcircuit_stash_parse test_m18_factcheck_honest test_m18_offload_sweep_residual
    test_m18_region_guard_prescoring test_m21_brand_dedup_and_verdict_copy test_m21_currency_parity
    test_migration_043_delete_user_cascade
04: test_migration_index_predicate_immutability test_model_config test_model_config_enforced
    test_multiplicity_discriminator_policy test_negative_cache_structural_gap test_negcache_genuine_invalidation
    test_negcache_outage_and_converted_fallback test_no_luxury_gate_in_tier3 test_noon_adapter test_occ_adapter
    test_openai_breaker test_openai_key_log_hygiene_s69 test_organic_pdp_harvest test_page_scraping
    test_paid_route_metering test_parallel_race_escalation test_park_listing_url_tier1
    test_partial_response_no_fabricated_scores test_partial_specs_stash_on_price_timeout
    test_password_reset_deep_link test_personalization test_personalization_e2e test_pharmacy_jsonld
    test_phase1_includes_reviews test_phase1_per_race_timeouts
05: test_prescoring_showable_guard test_price_cache_bust_probe test_price_fallback test_price_in_stock_persistence
    test_price_latency_budget test_price_parse_offload test_price_priority test_price_timeout_returns_parked
    test_prompt_fence test_prompt_truth test_rating_provenance test_rating_tiers test_regional_prices_category
    test_register_benefits_parity_s69 test_render_wave_domain_cap test_resolve_category
    test_response_builder_phase1_none_guard test_retro_w0_4 test_retro_w0_4_efg test_retro_w1_2b
    test_retro_w1_3 test_retro_w1_8 test_retro_w2_1 test_review_cleanup test_s70_exc_summary_logs
06: test_s70_fix_followups test_s70_model_router_downgrade test_s70_prefetch_gather_retrieved
    test_s71_u13_compare_auth_required test_s75_fanout_identity test_s75_fanout_starve test_s77_redis_offloop
    test_scoring_calibration_bundle_c test_secret_scan_static test_security_regression
    test_self_critique_orchestration test_sentry_channels_u8d test_sentry_channels_u8d_unit
    test_serper_budget_gate test_serper_fail_fast test_settle_window_orchestration
    test_shopify_cascade_wiring_l13 test_shopify_pdp_json test_shopping_currency_truth
    test_shopping_price_not_self_pending test_shutdown_drain test_singleton_state test_smart_fallback
    test_spec_confidence_cache test_spec_spine_d2
07: test_spec_verification_strict test_specs_no_fabrication_guard test_specs_refill_no_fabrication
    test_sse_settle_window test_stage_timings test_start_command test_streaming
    test_structured_comparison_service test_supplement_branch_genuine test_supplement_detector_precision
    test_text_error_envelope_no_raw_exception test_text_routes_sse_contract test_tier15_bahrain_discovery
    test_tier15_hit_rate_metric test_tier15_registry_gate test_tier15_route_trace test_tier15_timing
    test_tier2_spec_fallback test_tier3_synth test_timeout_partial_integration test_tradeoffs_dedup_parity
    test_transient_negcache test_two_input_shape test_u3b_sharing_branch_removed test_u3c_store_false_pin
08: test_unified_search test_url_extraction test_url_quality test_value_badge_category_dims
    test_variant_descriptor_backstop_axes test_w49_extraction_catch_redaction test_w4_12_display_contract
    test_w4_13_measurement_truth test_w4_7_confidence_single_computation test_w4_7_factcheck_shopping_key
    test_wall_caps_i57 test_wave_c_fence_bounds test_wave_d_cv_polish test_wide_signal_text
    test_winner_prose_reconciliation test_wrong_cheap_price_guard test_youtube_flag_and_cache test_zyte_service
```

(every name is `tests/<name>.py`).

### 5.3 CI-order set (one process, sorted = CI's alphabetical order, `--bound 1200`)

The unit file plus every file of 1.6 that runs in the free tier, plus the two files whose harness the
unit file imports or copies:

```
tests/test_be_harness.py tests/test_compare_from_text_hard_cap.py tests/test_compare_timeout_graceful.py
tests/test_http_400_cap_cut_mapping.py tests/test_partial_specs_stash_on_price_timeout.py
tests/test_phase1_per_race_timeouts.py tests/test_retro_w2_1.py tests/test_s75_fanout_identity.py
tests/test_s75_fanout_starve.py tests/test_s78_all_timeout_cap_as_timeout.py
tests/test_text_error_envelope_no_raw_exception.py tests/test_text_routes_error_mapping.py
tests/test_timeout_partial_integration.py tests/test_w4_13_flag_off_ledger.py tests/test_w4_13_measurement_truth.py
```

(`tests/test_lane2_integration.py` is `integration`-marked and excluded.) The point is cross-file leakage in
CI order (issue #186 class): the unit file sorts after the stash and identity files and before the route
files. Base run of the same set WITHOUT the unit file (it does not exist yet):

```
733 passed, 2 deselected, 13 warnings in 114.84s
[pyt] tag=f8-base-ciorder start=2026-10-17 06:01:15 end=2026-10-17 06:03:18 elapsed=124s bound=1200s status=OK rc=0
```

### 5.4 Identity nodes

F4a, F4b, F4c, F5-off, F7 (OFF half), F8a, F9, F13, F14 (`test_FY25_flag_off_compare_identity_matches_main`,
unchanged fixture) + every node of tests/test_compare_timeout_graceful.py,
tests/test_partial_specs_stash_on_price_timeout.py, tests/test_compare_from_text_hard_cap.py,
tests/test_timeout_partial_integration.py, tests/test_http_400_cap_cut_mapping.py green at HEAD unchanged.

### 5.5 Mutation run

M1-M25 on the GREEN bytes, each through the runner (`--bound 600`), the unit file plus F14; each mutant
must turn at least one named node red; restore from a byte copy and sha256-compare after each.

---------------------------------------------------------------------------------------------------

## 6. Stated limits

1. **H6 out of scope (D1), and it is probably the MORE common all-timeout path.** With the four per-race caps (specs 8, price 15, reviews 10, image 5 s) a product's loop ends at ~15 s plus the unified search; if both products finish their post-loop stages under the 30 s cap, the pair gather completes and the REST H6 guard (scs:4141-4155) returns INSUFFICIENT_DATA (400) synchronously -- the cap handler never runs. Capture 3 reached the cap only because both products were still in Phase 2 / the tier fills at 30 s. The stream H6 (4827-4844) likewise. Follow-up unit S78-F8b (the same record + predicate at both H6 sites).
2. **KPI bucket move.** Text route: the `search_logs.error_message` of these failures moves from the INSUFFICIENT_DATA sentence to `TIMEOUT_FRIENDLY_MESSAGE` in both W4-13 states (text_routes.py:661 / :684 via 465-466); `get_error_stats` buckets by exact text (analytics_service.py:154-155). Camera route: `error_message` moves from "INSUFFICIENT_DATA" to "TIMEOUT" (image_routes.py:526). The INSUFFICIENT_DATA count falls and the TIMEOUT count rises by the same rows; read the canary with that in mind.
3. **HTTP status 400 -> 503** on `/text/compare` (GET + POST) for these rows (text_routes.py:528-543): the Railway 5xx rate rises by the same count; any alert keyed on 5xx sees it.
4. **The stream is untouched.** Its Phase-1 cap already yields STREAM_TIMEOUT when nothing is usable (4810-4818); the record block runs on the stream path and nothing consumes it (F13). Phones drive REST only (TG-A5).
5. **Mid-request flip (D8)** fails closed to base: ON at record / OFF at the handler -> the flag-first predicate returns False; OFF at record / ON at the handler -> no record, the loop-written `specs` / `price` keys make the mid-gather arm return False.
6. **A parked or genuine price on a price-race timeout** (`_price_fallback_on_miss`, scs:6376) makes the compare a PARTIAL; it never reaches this branch (D7, F7).
7. **reviews / image_url never count** (capture 3, F3b). A product whose reviews landed but whose specs and price timed out reports TIMEOUT.
8. **The partial-build-failure path** (scs:3865-3871) reaches the INSUFFICIENT_DATA branch WITH usable data present. Under D4 as written, a recorded all-timeout pair whose price came from the fallback (or whose specs a post-loop refill filled) then reports TIMEOUT instead of INSUFFICIENT_DATA after a partial build crash (7.2).
9. **The body loses `api_calls`** on these rows (the TIMEOUT body never carried it); no route reads it (0 hits).
10. **Camera:** under `ENABLE_CAMERA_FAILURE_ENVELOPE` (ON in prod) the envelope carries `code: TIMEOUT`, so the client classifies the row `'timeout'` (tap-to-retry, failureClassification.ts:123) instead of `'generic'`; with the envelope OFF the camera route returns the TIMEOUT body itself.
11. **Refund and metering unchanged:** the M13-37 refund fires for every failure code before the surface call (text_routes.py:666-677).
12. **`include_specs=False`** is a request field (text_routes.py:373 POST body default True, passed at :639; the GET `specs` parameter at :849 / :1100); `grep -rn "include_specs=False" app/` -> 0 hits. With it False the price race alone decides (F12).
13. **`ENABLE_EARLY_SPECS_STASH` OFF:** the buffer is never populated, `_early_specs_buffer_list()` is empty, the handler already returns the base TIMEOUT body; the unit is inert there (the record block still writes, unread).
14. **Retry amplification / copy:** TIMEOUT says "give it another tap"; a pair whose sources are slow on every attempt will time out again, where the old copy steered the user to a different pair. Canary reading: the repeat-query rate after a D5 line.
15. **An existing pin encodes the old product rule:** `tests/test_partial_specs_stash_on_price_timeout.py::...::test_both_hang_falls_through_to_insufficient_data` (182-193, "NOT a bare TIMEOUT") is exactly the F1b shape; it stays green flag OFF and is reversed by design under the flag. Not edited (RED writes one new file).
16. **The D5 counts are per product, not per race, for the mid-gather arm:** the buffer dict does not record which races ran (probe Q2: identity keys only; probe F12: no `specs` key when it did not run), so a product cut mid-gather is counted in `cut mid-gather`, not in `races timed out`.
17. **One-slot window:** a buffer with one populated slot (the other `_fetch_product_data` not yet started; both register before their first await, so the window is a single loop tick) is judged on that slot alone.

---------------------------------------------------------------------------------------------------

## 7. Open questions for Fable (only what measurement could not settle)

- **7.1 (D5 log format, amended).** D5's `races timed out=%d/%d` is not computable for the mid-gather arm: measured, the buffer dict carries identity keys only when the cap fires mid-gather (probe Q2) and carries no `specs` key when the specs race never ran (probe F12), so "how many data races" is unknown for an unrecorded product. This spec keeps D5's field over RECORDED slots and adds `cut mid-gather=%d` (section 2.6, `_cap_timeout_log_counts`), which also tells the two arms apart in the canary. Confirm, or rule a different well-defined count.
- **7.2 (D4 hardening for the partial-build-failure path).** Measured reachable: `_partial_has_usable_data()` True -> `_build_partial_response` raises -> fall-through (scs:3865-3879) -> the predicate. With the recorded arm as written, a pair with a fallback price (probe F7 shape) whose partial build crashed reports TIMEOUT. Proposed: in the recorded arm also require `pd.get("specs") is None and pd.get("price") is None` (the plan's "identities only"; implied anyway on the normal path because `_partial_has_usable_data()` read the same dicts). Cost: two dict reads; adds an F18 row and a mutant. Not implemented here (D4 as written); rule it in or out.
- **7.3 (F8 split).** The brief's F8 PIN asked to prove "the attribute is reset on entry"; that assertion cannot pass at base (no reset exists), so it is F8b (RED) and the body half is F8a (PIN). Confirm.
- **7.4 (F13 replaced).** The brief's F13 (stream with the flag ON on `stream_q_partial_gather`) cannot exercise the record block: that scenario replaces `_fetch_product_data` with `_slow_fetch` (test_s75_fanout_identity.py:175-187). This spec runs all 9 FY25 scenarios with the flag ON (1.3 s measured), which covers `stream_q_full` (record block runs on the stream) and both partial shapes. Confirm.
- **7.5 (F15 keep or drop).** The existing route nodes pin the 503 mapping for a mocked TIMEOUT body; F15 adds the real-service link in both flag states (each node logs 2 sentinel netguard attempts, no egress). Keep (this spec) or drop as duplicate.
- **7.6 (comm-set extras).** The wider source-scan regex added 10 files beyond the TG's 27 (listed in 5.2); kept as a harmless superset. The two precommit-hook files are excluded with the TG Q7 reason. Confirm both.
- **7.7 (H6 follow-up priority).** Stated limit 1: with the 30 s cap the H6 path is likely where most all-timeout pairs land, so plan fix 8 alone may move few rows. Should S78-F8b be scheduled with this unit's canary, or should the canary first count `INSUFFICIENT_DATA: both products' Phase 1 fetches returned None` lines (scs:4142-4146) against D5 lines?
- **7.8 (copy, product call).** Stated limit 14: "give it another tap" for a pair whose sources are slow every time. Owner's call before the flip.

### 7.9 Not done in this spec

- No GREEN / HEAD comm run (no GREEN yet); M1-M25 are targets.
- No live capture: capture 3 was read by the orchestrator, not re-read here (no access from this agent); Q3 relies on the brief's reading of the log timestamps.
