## W4-9: stop shipping `str(e)`; failures get the unified `INTERNAL_ERROR` envelope (PO-RECORDED-MEASURED-05)

### What was wrong
Two `except Exception` catches in the comparison orchestrator put the raw Python exception text on the wire. These are the sync `_compare_from_text_impl` catch and the stream `compare_from_text_streaming` catch, both in `structured_comparison_service`. Three more catches one layer down in `extraction_service` did the same. The leaked text includes Supabase hostnames, table names, SQLSTATE codes and OpenAI quota errors with the org id (`insufficient_quota`, `org-…`). It reached:

- the sync `/text/compare` 400 body (POST and GET), `/text/quick` and the camera `/image/identify` `return result` arm;
- the SSE `error` event, which had no code and no request_id;
- the parser exits' nested `parsed.error`, from the `parse_product_query` catch;
- **SUCCESS payloads**, at `$.comparison.error` (from the `generate_comparison` catch) and `$.products[i].reviews.error` (from the `extract_reviews` catch). These were on the sync 200 body, on the SSE `verdict`, `settle_complete` and `complete` events, in the row `save_comparison` persists, and on the **unauthenticated** `GET /api/v1/share/{token}`.

**What this is NOT (R1):** the phones run bundle `97b5f15` with `ENABLE_EXPO_FETCH_SSE_DEFAULT=false`. A text compare there is sync `GET /api/v1/text/compare`, and the pre-OTA Alert shows the axios string "Request failed with status code 400" **before and after** this change. HEAD's `friendlyErrorKey` maps `BAD_REQUEST` and `INTERNAL_ERROR` to the same `home.errors.comparison` key. **This PR's value is wire disclosure to direct API callers, plus what gets persisted and publicly shared. It is not a UI change.**

### The six surfaces closed
1. **Sync catch** (scs `_compare_from_text_impl`): returns `{success:false, error: INTERNAL_ERROR_FRIENDLY_MESSAGE, code:"INTERNAL_ERROR", total_cost}`. `logger.error(..., exc_info=True)` is unchanged.
2. **Stream catch** (scs `compare_from_text_streaming`): yields the same envelope as its terminal `error` event.
3. **Parser catch + `parsed`**: the `extraction_service.parse_product_query` catch stores a constant and logs with `exc_info=True`. Both parser exits now emit `parsed` with ONLY `products`, so neither layer can leak on its own (pinned separately: `test_04c` covers the catch, `test_04` the stripping).
4. **`generate_comparison` catch**: stores the constant "verdict generation unavailable" and logs with `exc_info`. The comparison still succeeds (pinned), so no result fork is introduced.
5. **`extract_reviews` catch**: stores the constant "reviews extraction unavailable" and logs with `exc_info`.
6. **Route floors** in `text_routes`:
   - The sync `_surface_comparison_failure` has an ALLOWLIST (`_is_codeless_safe_message`). A codeless message that is not `"Comparison failed"` or the parser sentence becomes `{code:"INTERNAL_ERROR", error:<constant>}`.
   - The SSE floor does the same for a codeless `error` event, symmetric with the sync floor.
   - Both floors fail CLOSED on a non-str `error` value. Before, a list or dict raised TypeError, and on SSE the stream died with an empty 200 body.
   - The floor log line never interpolates the message.
   - Coded exits pass through unchanged (by design: honest limit 2).

New constants `INTERNAL_ERROR_FRIENDLY_MESSAGE` and `PRODUCT_PARSE_FAILURE_MESSAGE` are exported from `structured_comparison_service` and imported by `text_routes`. The copy is inside the Build-Principle-#4 fence (no "couldn't", "try again" or "Failed to"; pinned by a copy fence test).

### Flag row
- **UNFLAGGED.** A flag's OFF state would be the disclosure, and OFF is what prod runs. Precedent: M13-26 and W1-8.
- **Effect:** the wire deltas below.
- **Composition:** independent of every ENABLE_* flag. The `ENABLE_FULL_STREAM_DEADLINE` fork is tested in both states.
- **Activation order:** deploy-effective on merge. Merged AFTER W4-1 (#173): W4-1's scs hunk at ~:1214 shifted every scs anchor from ~:1515 by +5; resolved by symbol, no textual overlap (the rebase was clean).

### Wire delta
| surface | before | after |
|---|---|---|
| POST/GET `/text/compare`, generic failure | `{error:<raw>, code:BAD_REQUEST, request_id}` 400 | `{error:<constant>, code:INTERNAL_ERROR, request_id}` 400 |
| POST/GET `/text/compare`, parser failure | parser sentence, BAD_REQUEST | unchanged |
| SSE `error`, generic failure | `{success:false, error:<raw>, total_cost}` | `+code:INTERNAL_ERROR`, constant error, `+request_id` |
| SSE `error`, parser exit | `parsed` carried the parser's `error` (raw 429 text) | `parsed:{products:[…]}` only, `+request_id` |
| **every** SSE `error` event (CONTENT_UNAVAILABLE, LLM_UNAVAILABLE, STREAM_TIMEOUT, parser exit, …) | no request_id | **`+request_id`** (stamped by the route, only when absent, error events only; unflagged; additive; no pre-OTA or HEAD client reads it) |
| SSE non-error events | — | unchanged |
| sync 200 / SSE verdict, settle_complete, complete / persisted row / share page, verdict LLM failed | `comparison.error: <raw OpenAI text>` | `comparison.error: "verdict generation unavailable"` |
| same surfaces, reviews LLM failed | `products[i].reviews.error: <raw>` | `"reviews extraction unavailable"` |
| POST `/text/quick`, generic failure | raw error, BAD_REQUEST | constant error, still BAD_REQUEST (no floor there: must-NOT-touch 7) |
| POST `/image/identify`, `return result` arm | raw error, no code, 200 | constant error, `code:INTERNAL_ERROR`, 200 |

### KPI / canary
- **Admin `get_error_stats.common_errors`** (`analytics_service.py:119-150`, served by `admin_routes`) collapses every sync text failure of this class into ONE constant row. The stream path already logged a constant, so the two paths are now at parity.
- **`search_logs.error_message`** loses exception fidelity on the sync text path (ruling 2: accepted). The raw text lives in the Railway log and in Sentry via `exc_info=True` at each catch.
- **Canary line:** `[W4-9] codeless comparison failure with an unrecognized message; redacting to the INTERNAL_ERROR envelope`. Any occurrence means a NEW unreviewed codeless producer reached the sync floor; it should be zero on today's exits. Also watch the count of `code:INTERNAL_ERROR` on `/text/compare` 400s.

### Honest limits
1. Status stays 400 for a server-side failure (R4). 500 would be client-neutral on both client generations (`parseApiError` collapses only 503; no 5xx retry) and would make Railway 5xx monitoring truthful. That is follow-up 05d.
2. A CODED exit with a raw message still passes through. No orchestrator exit produces one today.
3. `/text/quick` keeps `BAD_REQUEST`.
4. A codeless SSE error payload with no `error` key gets INTERNAL_ERROR, while the sync helper uses its own default "Comparison failed" / BAD_REQUEST. This is deliberate: the SSE route has no reviewed default sentence.
5. The constant is English-only. The Arabic copy comes via the A11 `code`→i18n map, which reaches phones only after the next `eas update`.
6. `request_id` echoes a caller-supplied `X-Request-ID`, as every envelope already does.
7. The two 2026-06-08 production `search_logs` rows are taken from the ledger, not re-measured.
8. The verdict catch's error marker is not pinned for TRUTHINESS: a mutation that stores `error: ""` in `generate_comparison`'s catch leaves both unit files green (the reviews catch has that pin; the verdict catch does not). Every consumer tests the key for truthiness, so a non-empty constant is what preserves each branch. Recorded as follow-up 05e.
9. The first green agent's mutation driver died mid-table and left the sync floor as `if True:` on disk; the fix round restored the allowlist condition from its recorded body (never `git checkout`), re-ran every gate on the final bytes, and the re-adversary verified the on-disk shas before reviewing.

### Follow-ups
- **05b:** the camera `return result` arm treats `success:false` as a delivery: the credit is kept, `log_search success=True`, `action='comparison'`, and the pre-OTA client renders an empty result. It needs its own unit.
- **05c:** the remaining `str(e)` sites, with reachability measured at b63a8368:
  - (a) `auth_service.py:201` `[B4-BE-DIAG] supabase_error={str(e)[:300]}` **reaches the wire** on `/auth/social` failure. It is a deliberate, temporary diagnostic and the highest priority.
  - (b) `extraction_service.extract_specs` (~:1565 at head) and `extract_price` (~:1617 / ~:1660) return `error: str(e)`. On the phone `explicit_pair` path with every OpenAI call failing, the whole-body marker scan (`test_r2e`, green at head with these sites untouched) finds nothing on the sync or SSE wire. Not proven unreachable on every path.
  - (c) `openai_service.py:236` vision parse error. `image_routes.py:193` replaces it with constant copy and logs `raw_response` at debug only. Not on the wire.
  - (d) `serper_service.py:669/1017/1097/1142/1174` `{…, error: str(e)}`. Consumed internally (counted as discovery errors at scs ~:7044). Not traced to the wire, not measured.
  - (e) `url_extraction_service.py:422`. Merged into `raw_data`, then dropped by `normalize_product_data`. Not on the wire, but `url_routes` `detail=result.get("error")` remains a structural pipe.
  - (f) `feedback_service.py:240/275/308`. `save_feedback` and `track_events_batch` run under `fire_and_forget`, so their return values are discarded; `track_event` is internal. Not on the wire.
  - (g) `database_service.health_check:800` has zero callers (dead; `/health` does not call it).
  - (h) `auth_service.py:499` is log-only, with both tokens redacted.
  - (i) `text_routes` `DELETE /text/cache` `entry["error"]=str(e)[:300]` is admin-only.
  - (j) `referral_routes.py:228` is coded `VALIDATION_ERROR` validation copy, deliberate.
  - (k) `cache_service.py:914` `"message": f"Redis error: {str(e)}"` in `health_check()`; a git grep at HEAD finds no caller, so the function is dead and cannot reach the wire.
- **05d:** 400 → 500 for INTERNAL_ERROR.
- **05e:** pin the verdict catch's error-marker truthiness (see honest limit 8).

### Gates
- **Unit files:** `test_text_error_envelope_no_raw_exception.py` + `test_w49_extraction_catch_redaction.py`, 46 passed, with an autouse socket guard (zero non-loopback egress). The base row (the three source files reverted to b63a8368, current tests kept) gives 30 failed / 17 passed: the 25 original reds plus the 5 pins the fix round added or strengthened.
- **Preserve suite:** 17 passed (`test_text_routes_error_mapping`, `test_http_400_cap_cut_mapping`, `test_m13_26_image_error_envelope`).
- **Mutation table:** 33 rows plus a combination row, all killed. Every row restored from byte snapshots and sha-verified. Rows include the exc_info drops on the reviews and verdict catches (unpinned before this round) and the floors' str guard.
- **Comm gate:** at HEAD over the 191-file set (spec 189 + the 2 unit files) and the 49-file `extraction_service` supplement, run against their b63a8368 bases: `comm -13` empty on both, 0 failed at HEAD (HALF 00 2670 passed, HALF 01 1872 passed; supplement 372 passed / 35 xfailed). Base failures were exactly this unit's own 25 red tests (none from pre-existing tests; the ruling's "stop if not baseline" clause was read against that fact).
- **Lint:** ruff E9, F63, F7, F82 clean (0.16.5); py_compile OK.
- **Byte identity:** not applicable (unflagged; `price_service` untouched).
- **Toolchain:** the fix round ran on the global interpreter (fastapi 0.115.0 / starlette 0.38.6 / pydantic 2.7.0, which drift from the lock); the tests assert codes and shapes only. **Post-rebase verification on the pinned venv** (fastapi 0.141.1 / pydantic 2.13.4 / pytest 9.1.1, the CI pins) on the rebased tree: both unit files 46 passed; Preserve + the SSE contract, pre-verdict disconnect refund and W4-1 shopping-currency neighbours 195 passed; ruff + py_compile clean.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
