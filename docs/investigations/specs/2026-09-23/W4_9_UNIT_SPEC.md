# W4-9 — the comparison service's generic catch ships `str(e)` to the client; return the unified envelope instead

Finding `PO-RECORDED-MEASURED-05`. **Backend only** (the CLIENT copy half is the other
session's A11, already merged at `74d041cb` and NOT on phones yet). **UNFLAGGED — only
stricter / regression fix:** the change removes a raw Python exception string from four
response surfaces and replaces it with a constant sentence plus the `code` +
`request_id` envelope every other failure exit already carries; a flag would leave the
disclosure live in its OFF state, which is the state prod runs. *No legitimate client
copy depends on the raw string — MEASURED below: the pre-OTA client renders it verbatim
in an `Alert`, and the post-OTA (A11) client never renders the backend message at all,
only `code`.*

Worktree `C:/Users/SynAckITPC/Documents/AI/sc-w4-9`, branch
`feature/s65-w4-9-error-envelope`, base `b63a8368` (the `origin/main` this worktree was
cut from; `origin/main` has since advanced to `19ec866a` — **docs-only**, `git diff
--stat b63a8368..19ec866a` over every file this unit touches is EMPTY, so every anchor
below holds against current main too). Every line anchor is verified at `b63a8368`; the
review's anchors are from `76ace90` and have drifted — per-anchor table in the last
section. Every "today" claim has a probe under `.qa-w4/W4-9-w49_probe*_out.txt`, run
with the conftest-equivalent env (`load_dotenv(override=True)`, `neutralize_credentials()`,
`install_dotenv_guard()`, `PYTHONIOENCODING=utf-8`, no `LIVE`, no network reached).

---

## 1. The defect, measured

### 1.1 The two producers

`app/services/structured_comparison_service.py` — the generic `except Exception` at the
bottom of each orchestrator:

```
:3922    except Exception as e:
:3923        logger.error(f"Comparison error: {e}", exc_info=True)
:3926        await _cancel_profile_task(_profile_task)
:3927        return {"success": False, "error": str(e), "total_cost": self.total_cost}
```

```
:4713    except Exception as e:
:4714        logger.error(f"Streaming comparison error: {e}", exc_info=True)
:4717        await _cancel_profile_task(_profile_task)
:4718        yield ("error", {
:4719            "success": False, "error": str(e), "total_cost": self.total_cost,
:4720        })
```

Enclosing functions resolved by walking back to the nearest `def` (measured, not
inferred): `:3927` is in `_compare_from_text_impl` (`:3397`), `:4719` is in
`compare_from_text_streaming` (`:3929`).

**Every other failure exit in the file already carries a `code`.** All 15
`"success": False` exits, classified by reading each:

| line | function | `code` | `error` is |
|---|---|---|---|
| `:3278` | `_llm_unavailable_envelope` | `LLM_UNAVAILABLE` | `LLM_UNAVAILABLE_FRIENDLY_MESSAGE` (`:1515`) |
| `:3382` | `compare_from_text` | `INSUFFICIENT_DATA` | constant user copy |
| `:3390` | `compare_from_text` | `TIMEOUT` | `TIMEOUT_FRIENDLY_MESSAGE` (`:1510`) |
| `:3494` | `_compare_from_text_impl` | `CONTENT_UNAVAILABLE` | constant user copy |
| **`:3542`** (copy at `:3543`) | `_compare_from_text_impl` | **none** | **"Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'" — LEGITIMATE user copy** |
| `:3621` | `_compare_from_text_impl` | `INSUFFICIENT_DATA` | constant user copy |
| `:3906` | `_compare_from_text_impl` | `CONTENT_UNAVAILABLE` | constant user copy |
| **`:3927`** | `_compare_from_text_impl` | **none** | **`str(e)` — THE DEFECT** |
| `:4013` | `compare_from_text_streaming` | `STREAM_TIMEOUT` | `TIMEOUT_FRIENDLY_MESSAGE` |
| `:4070` | `compare_from_text_streaming` | `CONTENT_UNAVAILABLE` | constant user copy |
| **`:4118`** (copy at `:4119`) | `compare_from_text_streaming` | **none** | **the same parser-failure user copy as `:3543`** |
| `:4229` | `compare_from_text_streaming` | `STREAM_TIMEOUT` | `TIMEOUT_FRIENDLY_MESSAGE` |
| `:4253` | `compare_from_text_streaming` | `INSUFFICIENT_DATA` | constant user copy |
| `:4696` | `compare_from_text_streaming` | `CONTENT_UNAVAILABLE` | constant user copy |
| **`:4719`** | `compare_from_text_streaming` | **none** | **`str(e)` — THE DEFECT** |

So the codeless arm has **exactly two producers per path**: one legitimate user sentence
and one raw exception. That single fact decides the whole design (§ 2.4).

### 1.2 The four consumers that put it on the wire

| consumer | HEAD anchor | what it does with the service's `error` |
|---|---|---|
| `_surface_comparison_failure` generic arm | `app/api/text_routes.py:305` `raise HTTPException(status_code=400, detail=error_msg)` | plain-string detail → `error_handler.http_exception_handler` (`app/middleware/error_handler.py:128` `message = str(detail)`) → body `error` = the raw string, `code` = `BAD_REQUEST` (`STATUS_CODE_MAP[400]`, `:24`) |
| POST `/api/v1/text/compare` | `text_routes.py:415` calls that helper | same |
| GET `/api/v1/text/compare` | `text_routes.py:603` calls that helper | same |
| GET `/api/v1/text/compare/stream` | `text_routes.py:887` `yield f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"` | **no mapping at all** — the orchestrator's `error` payload is serialized verbatim |
| POST `/api/v1/text/quick` | `text_routes.py:1035-1038` `raise HTTPException(400, detail=result.get("error", "Comparison failed"))` | same as the helper's generic arm (this route does not use the helper) |
| POST `/api/v1/image/identify` | `app/api/image_routes.py:360` `return result` | **returns `compare_from_text`'s dict VERBATIM at HTTP 200** — the M13-26 envelope at `:381-396` covers only the `except Exception` arm, not an already-caught `success:false` return |

`text_routes.py:276` is the read (`error_msg = result.get("error", "Comparison failed")`),
`:275` the code read, `:305` the leak.

### 1.3 RED reproduction — real output

`.qa-w4/W4-9-w49_probe2_out.txt` (scratchpad `w49_probe2.py`; `TestClient(app)`,
`get_comparison_service` patched to return the review's exact result
`{'success': False, 'error': 'relation "comparisons" does not exist', 'total_cost': 0.0}`,
limiter reset between calls):

```
A POST /text/compare status                  400
A   body.error == the raw service string?    True
A   body.code                                'BAD_REQUEST'
A   request_id present?                      True
A GET /text/compare status                   400
A   body.error == the raw service string?    True
A   body.code                                'BAD_REQUEST'
A   request_id present?                      True
A2 infra string reaches body verbatim?       True
A2   body.error                              'connection to server at "db.abcdefgh.supabase.co" (10.0.0.5), port 5432 failed; SQLSTATE 42P01'
C stream status                              200
C   error-event payload                      {"success": false, "error": "relation \"comparisons\" does not exist", "total_cost": 0.0}
C   error event error == raw string?         True
C   error event has code?                    False
C   error event has request_id?              False
D /text/quick body.error == raw?             True
D   body.code                                'BAD_REQUEST'
H /image/identify status                     200
H   leaks raw?                               False
H   body.error                               'Products identified — comparing them is unavailable right now.'
H   body.code                                'INTERNAL_ERROR'
H   request_id present?                      True
```

(`H` is the M13-26 model the fix copies — the `except Exception` arm of `/image/identify`,
which does NOT leak. The `return result` arm does; see `A4` below.)

**Through the REAL generic catch**, not a stub — `.qa-w4/W4-9-w49_probe5_out.txt`
(`parse_product_query` patched to raise inside each `try:`, so `:3927` / `:4719` actually
execute):

```
sync result                                      {"success": false, "error": "relation \"comparisons\" does not exist", "total_cost": 0.0}
sync   error == raw?                             True
sync   has code?                                 False
stream event types                               ['status', 'error']
stream last payload                              {"success": false, "error": "relation \"comparisons\" does not exist", "total_cost": 0.0}
stream   error == raw?                           True
stream   has code?                               False
parser-fail result                               {"success": false, "error": "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'", "parsed": {"products": []}}
parser-fail   has code?                          False
```

**The camera route leak the review did not name** — `.qa-w4/W4-9-w49_probe4_out.txt`
(`StructuredComparisonService.compare_from_text` stubbed to RETURN the codeless raw
result, i.e. what `:3927` produces, not to raise):

```
camera status                                        200
camera body.error == the raw service string?         True
camera body.success                                  False
camera body.code                                     None
camera body keys                                     ['action', 'error', 'metadata', 'success', 'total_cost']
```

`image_routes.py:302-360` never checks `result.get("success")`; it stamps
`metadata.input_method`, sets `result["action"] = "comparison"` and returns the dict.
Fixing the SOURCE closes this for free; no `image_routes` edit is needed (and none is
made — see § 2.5).

### 1.4 What the client does with it — MEASURED, both client generations

**Pre-OTA (the bundle on phones today, `97b5f15`; the A11 fix `74d041cb` landed
2026-09-07, AFTER the 2026-09-02 OTA, and `git merge-base --is-ancestor 1df95b02
97b5f15` → NOT an ancestor):**

* `api.ts` SSE dispatch at `97b5f15:api.ts:570-572`:
  `case 'error': callbacks.onError?.(new Error(parsed.error || 'Stream error'))` — a bare
  `Error`, **no `response` object**. `parseApiError` (`97b5f15:api.ts:675`) therefore
  falls through to `if (error?.message) return { message: error.message, code: rawCode }`
  with `rawCode = null`.
* `HomeScreen.tsx:388` (`97b5f15`):
  `Alert.alert(t('common.error'), error.message || t('home.errors.comparison'))`.
* **⇒ the Python exception text is rendered verbatim in a modal on the phone.** This is
  the live user-facing harm, and it is on the SSE path — the mobile client's primary
  compare path (`handleTextCompare` is streaming-only; `97b5f15:HomeScreen.tsx:276`).
* Adding a `code` alone would NOT fix the pre-OTA client — its `case 'error'` reads only
  `parsed.error`. **The STRING must change.** That is why the fix is at the source.
* The pre-OTA sync `/text/compare` body is not rendered by the pre-OTA client (there is
  no non-stream text caller in `97b5f15:HomeScreen.tsx`); the fallback GET in `api.ts`
  wraps `response.data.error` into a synthetic error whose `code` is forwarded.

**Post-OTA (HEAD client, ships on the next `eas update --branch preview`):**

* `SmartCompareApp/src/services/errorCopy.ts:33` `friendlyErrorKey(code)` is TOTAL and
  the message is NEVER render input (`errorCopy.ts:5-8`). `friendlyErrorKey('INTERNAL_ERROR')`
  → `default` → `'home.errors.comparison'`, which exists in BOTH catalogs (measured:
  `home.errors.{comparison,insufficientData,rateLimited,timeout}` present in `en.json`
  and `ar.json`).
* `api.ts:788-808` wraps the SSE `error` event as a synthetic **status 503** carrying
  `code: parsed.code ?? null`. `parseApiError` (`api.ts:944-950`, M18 MB-contract-09)
  collapses a 503 to `TIMEOUT` **only when there is no code**. So today's codeless error
  event is shown to the post-OTA user as the *timeout* copy; after this fix, `code:
  'INTERNAL_ERROR'` survives and the user gets the correct generic comparison copy.
  **Strictly better on the future client too.**

### 1.5 The recorded production evidence (from the review, not re-measured here)

`search_logs` carries exactly two rows with `error_message = "'NoneType' object has no
attribute 'get'"` (2026-06-08T22:43:55 / 22:45:22, `input_type=text`, 20,251 ms /
19,944 ms, `products_found=[]`, cost 0.0). I did **not** re-query Supabase (read-only DB
access is out of this unit's env; no `LIVE`, no network). Taken as-is from the verifier
ledger, `docs/investigations/2026-09-06-full-review-state/FABLE_REVIEW_NOTES.md:80`.

---

## 2. The design — redact at the source, floor at the route

### 2.1 Two constants, in the file that already has this idiom

`app/services/structured_comparison_service.py`, immediately after
`LLM_UNAVAILABLE_FRIENDLY_MESSAGE` (`:1515-1517`), copying its register and its comment
shape verbatim:

```python
# W4-9 (PO-RECORDED-MEASURED-05) — the generic catch's user-facing copy. str(e)
# on this path carries Supabase hostnames, table names, Postgres SQLSTATE codes
# and upstream URLs; the raw text stays in the logger.error(..., exc_info=True)
# above and in Sentry, never in a response. Same register as
# TIMEOUT_FRIENDLY_MESSAGE and inside the Build-Principle-#4 copy contract
# (SmartCompareApp/src/i18n/.copy-policy.json scary_vocab_en: no "couldn't",
# no "try again", no "Failed to"). The FE i18n-substitutes by CODE
# ("INTERNAL_ERROR" -> home.errors.comparison), so this string is the API-level
# fallback for the pre-OTA client, not the rendered copy on a current build.
INTERNAL_ERROR_FRIENDLY_MESSAGE = (
    "Something went wrong on our side — give it another tap in a moment."
)

# The ONLY other codeless failure copy the orchestrators produce (:3543 sync,
# :4119 stream). Named so text_routes' floor can tell a legitimate codeless
# sentence from a leaked exception without a substring heuristic.
PRODUCT_PARSE_FAILURE_MESSAGE = (
    "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'"
)
```

Copy-policy check, measured (`.qa-w4/W4-9-w49_probe3_out.txt`):
`proposed constant forbidden tokens   NONE`.

### 2.2 The two service exits

`:3927` becomes:

```python
            return {
                "success": False,
                "error": INTERNAL_ERROR_FRIENDLY_MESSAGE,
                "code": "INTERNAL_ERROR",
                "total_cost": self.total_cost,
            }
```

`:4718-4720` becomes:

```python
            yield ("error", {
                "success": False,
                "error": INTERNAL_ERROR_FRIENDLY_MESSAGE,
                "code": "INTERNAL_ERROR",
                "total_cost": self.total_cost,
            })
```

`logger.error(..., exc_info=True)` at `:3923` / `:4714` is **unchanged** — that is where
the raw text must keep going.

The duplicated literal at `:3543` and `:4119` is swapped for `PRODUCT_PARSE_FAILURE_MESSAGE`.
Byte-identical strings; this is a de-duplication so the floor's allowlist cannot drift
from the copy.

### 2.3 The SSE `request_id` stamp — in the ROUTE, the only place with the `Request`

`app/api/text_routes.py:863-864` today:

```python
                if event_type == "error":
                    had_error = True
```

becomes:

```python
                if event_type == "error":
                    had_error = True
                    # W4-9: the orchestrator has no Request, so the ROUTE stamps
                    # the correlation id onto the terminal error payload — the
                    # same additive contract every HTTPException envelope gets
                    # from error_handler (`_get_request_id`). Only `error`
                    # events, only when absent, and BEFORE the yield at :887.
                    if isinstance(data, dict) and "request_id" not in data:
                        data["request_id"] = getattr(
                            request.state, "request_id", "unknown"
                        )
```

`getattr(request.state, "request_id", "unknown")` is the exact idiom at
`image_routes.py:387` and `error_handler.py:39`. Mutating `data` in place is the idiom
already used two branches up (`data["comparison_id"] = comparison_id`, `:857`).

### 2.4 The route floor — an ALLOWLIST, because the codeless arm is NOT all garbage

The review asks for "a defensive floor in `_surface_comparison_failure:144`: when `code`
is absent, raise the constant instead of `error_msg`". **An unconditional floor destroys
a legitimate user sentence**, measured (`.qa-w4/W4-9-w49_probe3_out.txt`):

```
scs:3542 parser copy (LEGIT user copy)   HTTP 400 detail="Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'"
scs:3927 str(e)      (RAW LEAK)          HTTP 400 detail='relation "comparisons" does not exist'
parser-copy body today                   {"success": false, "error": "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'", "code": "BAD_REQUEST", "request_id": "..."}
```

…and it would redden `tests/test_text_routes_error_mapping.py::test_no_code_raises_400_plain`
(`:73-78`, `assert exc.value.detail == "Comparison failed"`).

So the floor keys on a **named allowlist of the two sentences the codeless arm can
legitimately carry**, in `text_routes.py` just above `_surface_comparison_failure`:

```python
from app.services.structured_comparison_service import (
    get_comparison_service,
    get_regional_prices,
    INTERNAL_ERROR_FRIENDLY_MESSAGE,
    PRODUCT_PARSE_FAILURE_MESSAGE,
)
...
_DEFAULT_FAILURE_MESSAGE = "Comparison failed"

# W4-9 — the ONLY strings the orchestrators emit on the codeless arm
# (structured_comparison_service:3543 / :4119, plus this module's own `.get`
# default). Anything ELSE arriving without a `code` did not come from a
# reviewed exit and is treated as a leaked exception: redacted to the unified
# envelope. An allowlist, not a heuristic — a substring check on "relation"
# or "Traceback" would pass the next unfamiliar message straight through.
_CODELESS_SAFE_MESSAGES = frozenset({
    _DEFAULT_FAILURE_MESSAGE,
    PRODUCT_PARSE_FAILURE_MESSAGE,
})
```

and `:276` / `:305` become:

```python
    error_msg = result.get("error", _DEFAULT_FAILURE_MESSAGE)
    ...
    if error_msg not in _CODELESS_SAFE_MESSAGES:
        logger.error(
            "[W4-9] codeless comparison failure with an unrecognized message; "
            "redacting to the INTERNAL_ERROR envelope"
        )
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INTERNAL_ERROR",
                "error": INTERNAL_ERROR_FRIENDLY_MESSAGE,
            },
        )
    raise HTTPException(status_code=400, detail=error_msg)
```

The log line deliberately does NOT interpolate `error_msg` — it would re-create the
disclosure in a lower-trust log sink, and the underlying exception is already logged
with `exc_info` at `structured_comparison_service:3923`.

**`/text/quick` (`:1035-1038`) gets the same floor** by routing it through
`_surface_comparison_failure`? **NO** — see must-NOT-touch item 7 and Honest limit 3.
It is left alone in this unit and covered by the source fix only.

### 2.5 Exactly which lines change

| file | line(s) at `b63a8368` | change |
|---|---|---|
| `app/services/structured_comparison_service.py` | after `:1517` | +2 constants |
| " | `:3543` | literal → `PRODUCT_PARSE_FAILURE_MESSAGE` |
| " | `:3927` | raw dict → envelope (constant + `code`) |
| " | `:4119` | literal → `PRODUCT_PARSE_FAILURE_MESSAGE` |
| " | `:4718-4720` | raw dict → envelope (constant + `code`) |
| `app/api/text_routes.py` | `:15-18` (the `structured_comparison_service` import) | + the 2 constants |
| " | above `:274` | + `_DEFAULT_FAILURE_MESSAGE`, `_CODELESS_SAFE_MESSAGES` |
| " | `:276` | `"Comparison failed"` → `_DEFAULT_FAILURE_MESSAGE` (same value) |
| " | `:305` | + the allowlist branch |
| " | `:863-864` | + the `request_id` stamp on `error` events |
| `tests/test_text_error_envelope_no_raw_exception.py` | new | § 5 |

### 2.6 MUST NOT TOUCH

1. **`app/services/price_service.py`** — not involved; the corpus byte-identity harness
   is therefore N/A (§ 6).
2. **`app/middleware/error_handler.py`** — the W1-9 envelope (`_is_structured_detail`
   `:74`, the `str(detail)` fall-through `:128`, `_detail_retry_after` `:94`, the 429
   header/field pair) is the contract this unit RELIES on. Zero edits.
3. **The 4xx/5xx mappings that intentionally pass user copy** —
   `_surface_comparison_failure:277-281` (`CONTENT_UNAVAILABLE` → the structured body at
   HTTP 200), `:282-296` (`TIMEOUT` / `LLM_UNAVAILABLE` → 503 with the code preserved),
   `:299-304` (any other `code` → 400 with the code preserved). Measured today
   (`.qa-w4/W4-9-w49_probe_out.txt` E2–E6) and unchanged. **In particular `E6` — an
   unrecognized code WITH a raw message (`{"code": "WEIRD", "error": <raw>}`) still ships
   the raw message.** That is deliberate: a coded exit is a reviewed exit, and no
   orchestrator exit produces one; see Honest limit 2.
4. **The other 13 `success: False` exits** in § 1.1. Their copy is product copy.
5. **`app/api/image_routes.py`** — the M13-26 block (`:381-396`) is the model, not a
   target. Its `return result` leak (§ 1.3 `A4`) is closed by the source fix; editing
   `image_routes` as well would be a second, redundant redaction on the same value.
6. **`app/api/url_routes.py`** — `:117`, `:219`, `:240` have the identical
   `detail=result.get("error", …)` shape and WOULD ship a raw string, but measured: no
   producer feeds them one. `compare_from_urls`'s only failure exit is
   `url_extraction_service.py:577` `"Could not extract both products"` (a constant; the
   per-URL `str(result)` texts go into `details`, which `:117` never reads), and
   `extract_from_url`'s only failure exit is `:444` `"Failed to fetch URL"` (constant;
   `extract_with_ai`'s `{"error": str(e)}` at `:422` is merged into `raw_data` and then
   dropped by `normalize_product_data`, which builds a fixed key set). **Ruled OUT of the
   change set, IN as a follow-up row** — the channel is symmetric and the pre-OTA client
   renders `parsed.message` on that path verbatim (`97b5f15:HomeScreen.tsx:453`).
7. **`/text/quick` (`text_routes.py:1035-1038`)** — the source fix stamps a `code` on the
   result, so the raw string is gone; but this route does NOT use
   `_surface_comparison_failure`, so it keeps its plain-string `detail` and its
   `BAD_REQUEST` code. Wiring it into the helper changes its status mapping for
   `CONTENT_UNAVAILABLE` and `TIMEOUT` — a route contract change with its own blast
   radius. Out.
8. **`text_routes.py:1371`** (`entry["error"] = str(e)[:300]` in `DELETE /text/cache`) —
   admin-only (`Depends(verify_admin_key)`), an operator surface. Out.
9. **`app/api/referral_routes.py:228`** (`detail={"code": "VALIDATION_ERROR", "error":
   str(exc)}`) — a narrow `except ValueError` whose message is deliberate validation
   copy, and it is coded. Out.
10. **`app/services/auth_service.py:196-201`** — the `[B4-BE-DIAG] supabase_error=
    {str(e)[:300]}` escape hatch for `social_login`. Same defect class, explicitly
    labelled temporary, different module, different reviewer. Out; follow-up row.
11. **`SmartCompareApp/**`** — read-only in this unit. A11 owns the client half.
12. **The `log_search` call sites** (`:394`, `:586`, `:951`) and the M13-37 refund
    ordering. Untouched — see Honest limit 1 for the observability consequence.

### 2.7 Why this design beats the alternatives

* **Route-only (redact at `text_routes:305`)** — would miss the SSE path entirely (no
  mapping there, `:887` serializes the payload as-is), miss `/text/quick`, and miss the
  camera route's `return result`. Measured: 3 of the 4 leaking surfaces survive.
* **Source-only (no floor)** — closes all four surfaces today but leaves
  `_surface_comparison_failure`'s codeless arm as an open pipe for the next producer.
  The floor is 6 lines and is the last gate before the wire.
* **Unconditional floor** — destroys `PRODUCT_PARSE_FAILURE_MESSAGE` and reddens an
  existing pin (§ 2.4).
* **Substring heuristic** (`"Traceback" in msg`, `"relation" in msg`) — passes the next
  unfamiliar exception straight through. An allowlist fails closed.
* **Giving `:3542`/`:4118` a code (e.g. `PARSE_FAILED`) so the floor can be
  unconditional** — cleaner in principle, but it changes the wire `code` for that failure
  from `BAD_REQUEST` to a new value, which is a client-contract decision (the A11 map has
  no case for it and would fall to the generic key, and the pre-OTA client's `case
  'error'` would be unaffected). **Open ruling 1.**
* **A private `_internal_error` key on the result so `log_search` keeps the raw text** —
  MEASURED UNSAFE: `image_routes.py:360` returns `compare_from_text`'s dict verbatim to
  the client (§ 1.3 `A4`), so any private key leaks on the camera route. Rejected.
* **Flagging it** — the OFF state is the disclosure. The repo precedent for an unflagged
  narrowing is M13-26 itself (`image_routes.py:381`, unflagged) and W1-8.

---

## 3. Preserve — existing tests on the touched paths, RUN at HEAD

| suite | what it pins | result at `b63a8368` |
|---|---|---|
| `tests/test_text_routes_error_mapping.py` + `tests/test_http_400_cap_cut_mapping.py` + `tests/test_m13_26_image_error_envelope.py` | the whole D2 code→surface map, the `error_handler` unwrap, the M13-26 envelope | **17 passed**, 13 warnings, 67.99s |
| `tests/test_openai_breaker.py` + `tests/test_compare_timeout_graceful.py` | `LLM_UNAVAILABLE` → 503, the generic arm fall-through, the hard-cap PARTIAL / `INSUFFICIENT_DATA` / `TIMEOUT` triad | **24 passed**, 5 warnings, 89.54s |
| `tests/test_streaming.py` + `tests/test_comparison_id_echo.py` + `tests/test_compare_from_text_hard_cap.py` + `tests/test_m18_preverdict_disconnect_refund.py` + `tests/test_timeout_partial_integration.py` | the SSE event loop, the W3-2 insert gate, `had_error`, the M13-37/M18 refund arms | **84 passed**, 13 warnings, 47.88s |

Command shape: `python -m pytest <files> -q -p no:cacheprovider --timeout=<n>
-m "not (live_unit or live_db or integration)"`.

Specific nodes that MUST stay green and why they are safe:

* `test_text_routes_error_mapping.py::test_no_code_raises_400_plain` (`:73-78`) asserts
  `detail == "Comparison failed"`. `"Comparison failed"` IS in `_CODELESS_SAFE_MESSAGES`
  (it is this module's own `.get` default), so the floor does not fire. **This node is
  the single most important pin in the unit** — it is what rules out the unconditional
  floor.
* `test_compare_from_text_hard_cap.py:89` `assert result.get("error") == "boom"` — it
  patches `_compare_from_text_impl` to *return* `{"success": False, "error": "boom"}`.
  That value passes through `compare_from_text`'s `wait_for` untouched (the generic catch
  lives INSIDE the impl, which is replaced). Green.
* `test_comparison_id_echo.py:1092` yields `("error", {"error": …, "code": "TIMEOUT"})`
  from a stub and asserts only on the TERMINAL events' keys. The `request_id` stamp adds
  a key to the *error* event only. Green.
* `test_m18_preverdict_disconnect_refund.py:173` yields `("error", {"message": "boom"})`
  — a dict, so the stamp applies and adds `request_id`; the test asserts on refund
  labels, not payload keys. Green.
* `test_m13_26_image_error_envelope.py` drives the `except Exception` arm
  (`side_effect=Exception`), not the `return result` arm. Untouched by this unit. Green.

Nothing in `tests/.pre_impl_failures.txt` (89 lines) references `text_routes`,
`structured_comparison_service`, `streaming` or `error_mapping` — measured `grep -c` = 0,
so the deselect list has no interaction with this unit.

---

## 4. Red tests — `tests/test_text_error_envelope_no_raw_exception.py`

Module-level `os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")` /
`("ADMIN_API_KEY", "test-admin-key")` and the `_reset_rate_limiter` autouse fixture,
copied from `tests/test_text_routes_error_mapping.py:15-40` (the `/text/compare` limiter
is 10/min per IP and this file makes >10 `TestClient` calls).

Two module constants:
```python
_SECRET = 'relation "comparisons" does not exist'
_INFRA = ('connection to server at "db.abcdefgh.supabase.co" (10.0.0.5), '
          'port 5432 failed; SQLSTATE 42P01')
```
Leak assertions unescape before searching, because `json.dumps` escapes the inner quotes
and a naive `in resp.text` gives a FALSE NEGATIVE (this bit probe v1 — recorded in
`.qa-w4/W4-9-w49_probe_out.txt`, where every `raw string in body?` reads `False` while
the body visibly contains the string):
```python
def _leaks(resp, needle):
    return needle in resp.text.replace('\\"', '"')
```

### Class A — the service exits (the source fix)

Injection: `patch("app.services.structured_comparison_service.parse_product_query",
AsyncMock(side_effect=Exception(_SECRET)))` — that call sits inside BOTH `try:` blocks
(`:3537` sync, `:4113` stream), so the real `:3927` / `:4719` execute. Verified by probe 5.

1. **RED** — `await StructuredComparisonService().compare_from_text("alpha vs beta")`
   returns a dict whose `error` is `INTERNAL_ERROR_FRIENDLY_MESSAGE`, whose `code` is
   `"INTERNAL_ERROR"`, and `_SECRET not in json.dumps(result, default=str)`.
   *RED today: `error == _SECRET`, no `code` key (probe 5).*
2. **RED** — the stream twin: collect
   `[(t, d) async for t, d in svc.compare_from_text_streaming("alpha vs beta")]`; the
   last event is `("error", …)` with the same three assertions.
   *RED today (probe 5).*
3. **PIN** — the raw text still reaches the log. `caplog.at_level(logging.ERROR)` around
   test 1; assert `_SECRET` appears in the captured records and that one record has
   `exc_info`. Green today; reddens if the fix deletes the `logger.error` line.
4. **PIN** — parametrised over `("sync", "stream")`: with `parse_product_query` returning
   `({"products": []}, {})`, the result is `PRODUCT_PARSE_FAILURE_MESSAGE` and carries
   **no** `code` key. Green today (probe 5, `parser-fail has code? False`); reddens if
   `:3542`/`:4118` are given a code or their copy is changed.

### Class B — the sync wire (POST + GET, parametrised over the verb)

`patch("app.api.text_routes.get_comparison_service")` with
`compare_from_text = AsyncMock(return_value=<codeless raw result>)` — this exercises the
ROUTE FLOOR (the service is stubbed, so the source fix is bypassed by construction; that
separation is the point).

5. **RED**, parametrised over `verb in ("post", "get")` × `needle in (_SECRET, _INFRA)`:
   status 400; `not _leaks(resp, needle)`; `resp.json()["code"] == "INTERNAL_ERROR"`;
   `resp.json()["error"] == INTERNAL_ERROR_FRIENDLY_MESSAGE`;
   `resp.json()["request_id"]` truthy. **This is the review's RED, verbatim.**
   *RED today: `error == needle`, `code == 'BAD_REQUEST'` (probe 2 A/A2).*
6. **PIN** — the parser-failure sentence survives the floor: service returns
   `{"success": False, "error": PRODUCT_PARSE_FAILURE_MESSAGE, "parsed": {}}` → body
   `error == PRODUCT_PARSE_FAILURE_MESSAGE`, `code == "BAD_REQUEST"`. Green today (probe
   3); **reddens under an unconditional floor.**
7. **PIN** — the helper directly: `_surface_comparison_failure({"success": False})`
   (no `error` key at all) raises `HTTPException(400)` with `detail == "Comparison
   failed"` — the plain-string shape `test_text_routes_error_mapping.py:73` pins, restated
   here so this file fails loudly if someone widens the floor later. Green today.
8. **PIN** — the preserved 4xx/5xx map, parametrised over the four coded results
   measured in probe 1 (`CONTENT_UNAVAILABLE` → returned dict; `TIMEOUT` → 503 +
   `code`; `LLM_UNAVAILABLE` → 503 + `code`; `INSUFFICIENT_DATA` → 400 + `code`), each
   asserting the `error` sentence is passed through UNCHANGED. Green today; reddens if
   the floor is hoisted above the `if code:` branch.

### Class C — the SSE wire

Stub `compare_from_text_streaming` with an async generator yielding
`("status", {...})` then `("error", {"success": False, "error": _SECRET, "total_cost": 0.0})`,
parse the SSE body into `(event, payload)` pairs.

9. **RED** — the terminal `error` payload: `payload["code"] == "INTERNAL_ERROR"`,
   `payload["error"] == INTERNAL_ERROR_FRIENDLY_MESSAGE`, `payload["request_id"]` truthy,
   and `not _leaks(resp, _SECRET)`.
   *RED today on all four: probe 2 C (`code` absent, `request_id` absent, `error` raw).*
   **Note the split:** `code` + `error` come from the SERVICE fix, `request_id` from the
   ROUTE stamp — this stub bypasses the service fix, so with only the route stamp
   implemented this test is half-green. Implement both; the mutation table pins each.
10. **PIN** — the stamp is scoped: a stub yielding
    `("status", {...}), ("prices", {...}), ("complete", <payload>)` produces NO
    `request_id` on any non-`error` event. Green today; reddens if the stamp is hoisted
    out of the `if event_type == "error"` branch.
11. **PIN** — the stamp is idempotent/non-clobbering: a stub yielding
    `("error", {"error": "x", "code": "CONTENT_UNAVAILABLE", "request_id": "caller-supplied"})`
    keeps `request_id == "caller-supplied"` and keeps `code == "CONTENT_UNAVAILABLE"`
    (the stamp must not rewrite a coded error event). Green today.
12. **PIN** — a non-dict `error` payload does not crash the route: stub yields
    `("error", "boom")`; the response is still 200 and the event is serialized. Green
    today; reddens if the stamp drops the `isinstance(data, dict)` guard.

### Class D — the two surfaces the source fix closes for free

13. **RED** — `/api/v1/text/quick`: `POST {"product1": "A", "product2": "B"}` with
    `compare_from_text` stubbed to return the codeless raw result → `not _leaks(...)`.
    **Marked as depending on the SOURCE fix only** (this route has no floor), so the stub
    must be the *post-fix* service envelope for the green assertion, and the RED variant
    asserts today's leak. Implement as: stub raises inside the real service
    (`parse_product_query` injection, Class-A style) and drive the route, so the source
    fix is what turns it green. *RED today: probe 2 D.*
14. **RED** — `/api/v1/image/identify`: two JPEG parts, `identify_products` stubbed to 2
    products, content safety allowed, and the comparison driven to the real generic catch
    (same `parse_product_query` injection). Body must not leak; `body["code"] ==
    "INTERNAL_ERROR"`. *RED today: probe 4 (`error == _SECRET`, `code == None`).*
    **This is the review row's missing surface** — see § 9 disagreement 3.

### Class E — the copy contract

15. **PIN** — `INTERNAL_ERROR_FRIENDLY_MESSAGE` contains none of
    `SmartCompareApp/src/i18n/.copy-policy.json` `scary_vocab_en`
    (`["couldn't", "try again", "Failed to"]`), loaded from the file, case-insensitive —
    the same fence `tests/test_http_400_cap_cut_mapping.py::test_timeout_copy_has_no_forbidden_vocab`
    applies to the TIMEOUT copy. Green by construction (measured: `NONE`).

No flag-state parametrisation: the unit is unflagged, so there is no OFF arm to pin.
The rollback proof is the Preserve suite plus pins 6, 7, 8, 10, 11, 12.

---

## 5. Gates

1. **TDD red-first.** Write the file, run it alone before any source edit:
   `python -m pytest tests/test_text_error_envelope_no_raw_exception.py -q
   -p no:cacheprovider --timeout=200 -m "not (live_unit or live_db or integration)"`.
   Record `.qa-w4/W4-9-RED.txt` showing tests **1, 2, 5, 9, 13, 14 RED** and
   **3, 4, 6, 7, 8, 10, 11, 12, 15 GREEN**.
2. **Comm gate.** Touched modules: `app/api/text_routes.py`,
   `app/services/structured_comparison_service.py`. The union
   ```
   grep -rlE "text_routes|structured_comparison_service|_surface_comparison_failure|compare_from_text|error_handler|text/compare" tests --include=test_*.py
   ```
   is **189 files** — recorded verbatim in `.qa-w4/comm-set-W4-9.txt`. Per-pattern:
   `structured_comparison_service` 152, `compare_from_text` 37, `text/compare` 30,
   `text_routes` 26, `error_handler` 10, `_surface_comparison_failure` 5. Base run
   BEFORE the edit (this worktree IS `b63a8368`, working tree clean), head run after
   green WITH this unit's own file appended; same shape as
   `sc-w0-load/.qa-w0/run_comm_head_w04.py`:
   `-m "not (live_unit or live_db or integration)" --timeout=200 -q -p no:cacheprovider`
   plus `--deselect` for each of the 89 ids in `tests/.pre_impl_failures.txt`, split in
   halves. `comm -13 <(sort comm-base) <(sort comm-head)` must be empty.
   **SmartCompareApp scanners are NOT part of this gate**: no file under
   `SmartCompareApp/` is touched, so its jest suite has nothing to regress. The wire
   contract DOES change and is analysed in § 10 instead; the two RN files that name the
   shape (`__tests__/errorCopy.a11.test.ts`, `__tests__/HomeScreen.errorCopy.a11.test.tsx`)
   assert on `code`→key, never on a backend string, and `grep -rn "BAD_REQUEST"` over
   `SmartCompareApp/src` + `__tests__` returns zero hits.
3. **Byte-identity gate: N/A — `app/services/price_service.py` is NOT touched.** The
   `scripts/verify_flag_byte_identity.py` harness exercises `extract_price_from_html`
   over the frozen `_proof` corpus and never enters `text_routes`, the orchestrators'
   error arms, or `error_handler`; running it would prove nothing about this change and
   the unit declares no flag for `--flags`. Do NOT run `_proof/sweep2.py`. The rollback
   proof for this unit is gate 2 plus pins 6/7/8/10/11/12.
4. **Ruff + py_compile.**
   `python -m ruff check --select E9,F63,F7,F82 --no-cache app/api/text_routes.py
   app/services/structured_comparison_service.py tests/test_text_error_envelope_no_raw_exception.py`
   (clean at HEAD on the two source files — measured `All checks passed!`), then
   `python -m py_compile` on all three.
5. **Full free-tier suite** before merge, same marker + deselect shape as gate 2; failing
   only on ids already in `tests/.pre_impl_failures.txt` / the recorded comm base.
6. **Fable review before commit. Agents never commit.** CLAUDE.md carries no flag row for
   this unit (unflagged); the PR body must state the wire-contract delta of § 10 and that
   the pre-OTA client is IMPROVED, not merely unharmed.

---

## 6. Mutation checks

Record each in `.qa-w4/W4-9-MUTATIONS.txt`; restore after every one.

| mutation | tests that must redden |
|---|---|
| Revert `scs:3927` to `{"success": False, "error": str(e), "total_cost": …}` | 1, 13, 14 |
| Revert `scs:4719` to the same | 2, 9 (its `code`/`error` half) |
| Drop `"code": "INTERNAL_ERROR"` from `scs:3927`, keep the constant | 1, 13, 14 (code assertion) |
| Drop `"code": "INTERNAL_ERROR"` from `scs:4719`, keep the constant | 2, 9 |
| Delete `logger.error(..., exc_info=True)` at `scs:3923` | 3 |
| Give `scs:3542` / `:4118` a `code` | 4 |
| Change `PRODUCT_PARSE_FAILURE_MESSAGE`'s text without updating `:3542`/`:4118` | 4, 6 (the floor fires on the now-unlisted sentence) |
| Remove the `request_id` stamp at `text_routes:864` | 9 |
| Hoist the stamp out of `if event_type == "error"` | 10 |
| Make the stamp unconditional (`data["request_id"] = …`, no `not in` guard) | 11 |
| Drop the `isinstance(data, dict)` guard from the stamp | 12 |
| Make the floor unconditional (`if True:` / drop the allowlist test) | 6, 7 |
| Remove the floor entirely | 5 (both verbs × both needles) |
| Move the floor ABOVE the `if code:` branch at `:301` | 8 |
| Replace the allowlist with `if "Traceback" in error_msg:` | 5 (neither `_SECRET` nor `_INFRA` contains it) |
| Interpolate `error_msg` into the floor's `logger.error` | — no test target; assert by reading the diff, and say so in the report |
| Put `"couldn't"` / `"try again"` / `"Failed to"` in `INTERNAL_ERROR_FRIENDLY_MESSAGE` | 15 |

Test 3 is the only guard against the fix throwing the diagnostic away; tests 7 and 8 are
the only guards against the floor over-reaching. Say so in the report.

---

## 7. Honest limits

1. **`search_logs.error_message` loses fidelity on the sync text path.** `text_routes.py:394`
   (POST) and `:586` (GET) log `error_message=result.get("error")`; after the fix that is
   the constant, so the forensic column that produced the two 2026-06-08 rows the finding
   cites will read `"Something went wrong on our side …"` for this class. The exception
   itself survives in the Railway log + Sentry (`scs:3923`, `exc_info=True`). The obvious
   remedy — a private `_internal_error` key on the result dict for the route to log — is
   **MEASURED UNSAFE**: `image_routes.py:360` returns `compare_from_text`'s dict verbatim
   to the client (§ 1.3 `A4`), so a private key leaks on the camera route. The streaming
   path loses nothing: `text_routes.py:951` already logs the constant
   `"Streaming comparison failed"`. **Open ruling 2.**
2. **A coded exit with a raw message is still passed through.** `_surface_comparison_failure`
   preserves `{"code": X, "error": <anything>}` verbatim (measured, probe 1 `E6`:
   `{"code": "WEIRD", "error": <raw>}` → `HTTP 400 detail={'code': 'WEIRD', 'error':
   <raw>}`). No orchestrator exit produces one today (§ 1.1 table: every coded exit's
   `error` is a constant), so this is a latent hole, not a live leak. Closing it would
   require redacting messages on coded exits, which would destroy the `INSUFFICIENT_DATA`
   / `TIMEOUT` / `CONTENT_UNAVAILABLE` copy. Left open by design.
3. **`/text/quick` keeps its own mapping.** After the fix its body is
   `{"success": false, "error": <constant>, "code": "BAD_REQUEST", "request_id": …}` —
   the constant is right but the `code` is `BAD_REQUEST`, not `INTERNAL_ERROR`, because
   the route raises a plain-string detail (`:1037`) and does not use the helper. Test 13
   asserts only that the raw string is gone. Wiring it to the helper is must-NOT-touch 7.
4. **`url_routes`' three `detail=result.get("error", …)` sites are unchanged.** Measured
   safe today (must-NOT-touch 6) but structurally identical; a future
   `url_extraction_service` exit that returns `str(e)` would leak, and the pre-OTA client
   renders that path's message verbatim. Follow-up row, not this unit.
5. **HTTP status stays 400 for a server-side crash.** `code: "INTERNAL_ERROR"` inside a
   `BAD_REQUEST`-shaped 400 is semantically odd; 500 would be truthful. Changing it moves
   the response into `parseApiError`'s non-503 arm on both client generations and into
   the mobile `failureClassification` buckets. Out of scope. **Open ruling 3.**
6. **`request_id` is caller-supplied when the caller wants it to be.**
   `app/middleware/request_id.py:11` is `request.headers.get("X-Request-ID",
   str(uuid.uuid4()))`. The SSE stamp therefore echoes an attacker-chosen id exactly as
   every existing error envelope already does. Pre-existing, unchanged, noted.
7. **English-only.** The constant is an English sentence. The Arabic user gets correct
   copy only through the A11 `code`→i18n map, i.e. only after the next
   `eas update --branch preview`. Until then the pre-OTA Arabic user sees an English
   sentence where they previously saw an English Python traceback fragment — better, not
   fixed. That is A11's half.
8. **Not re-measured: the two production `search_logs` rows.** Taken from the verifier
   ledger; no DB access in this unit.

---

## 8. Spec disagreements with the review

1. **Anchor drift — every review anchor re-resolved at `b63a8368`** (all four verified at
   `76ace90` first with `git show 76ace90:<file> | sed -n '<n>p'`):

   | review anchor (`76ace90`) | content there | HEAD anchor | drift |
   |---|---|---|---|
   | `scs.py:3659` | `return {"success": False, "error": str(e), "total_cost": self.total_cost}` | **`:3927`** | +268 |
   | `scs.py:4429` | `"success": False, "error": str(e), "total_cost": self.total_cost,` | **`:4719`** | +290 |
   | `text_routes.py:144` (tables doc) | `raise HTTPException(status_code=400, detail=error_msg)` | **`:305`** | +161 |
   | `text_routes.py:123` | `error_msg = result.get("error", "Comparison failed")` | **`:276`** | +153 |
   | `text_routes.py:146` (wave-plan row) | **blank line** | — | the wave-plan row is off by 2; the tables doc's `:144` is the exact one |
   | `image_routes.py:294` | the M13-26 comment | **`:381`** | +87 |

2. **The review's proposed floor is WRONG as written.** "when `code` is absent, raise the
   constant instead of `error_msg`" would delete the one legitimate codeless user
   sentence (`scs:3542`/`:4118`, measured in probe 3) and redden
   `test_text_routes_error_mapping.py::test_no_code_raises_400_plain`. The spec replaces
   it with an allowlist (§ 2.4). This is the single substantive design change against the
   review.

3. **The review under-counts the surfaces: there are FOUR, not two.** Beyond POST/GET and
   the SSE event it names:
   * `POST /api/v1/text/quick` (`text_routes.py:1035-1038`) leaks identically — measured
     (probe 2 D).
   * `POST /api/v1/image/identify` leaks the SAME value through `image_routes.py:360`
     `return result` — measured (probe 4). The review says "the M13-26 fix landed on the
     camera route only"; measured, M13-26 covers only the camera route's `except
     Exception` arm and leaves its `return result` arm leaking the very string this unit
     redacts. Both are closed by the source fix; no extra edit.

4. **"text_routes:123 `error_msg = result.get(...)` … str(e) reaches the wire verbatim"
   — CONFIRMED, with one precision.** It reaches the wire as the envelope's `error`
   field, not as a bare detail: `error_handler.http_exception_handler:128`
   (`message = str(detail)`) wraps it into `{success, error, code: "BAD_REQUEST",
   request_id}`. So a `request_id` is ALREADY present on the sync path today (probe 2);
   the review's RED phrasing "`code: 'INTERNAL_ERROR'` + `request_id` present" is RED only
   on the `code` half there. On the SSE path BOTH halves are RED (no `code`, no
   `request_id`).

5. **"Truncate `str(e)` to 200 chars in `log_search`'s `error_message`" — NOT DONE, and
   the reason is measured.** After the fix `log_search` receives the constant, so there is
   nothing left to truncate; keeping the raw text for the log would need a private key on
   the result dict, which `image_routes.py:360` would publish. Honest limit 1 + open
   ruling 2.

6. **Product decisions I am NOT making:** the wording of
   `INTERNAL_ERROR_FRIENDLY_MESSAGE` beyond the copy-policy fence; whether the parser
   failure gets a `code` (ruling 1); whether the status becomes 500 (ruling 3); whether
   `search_logs` keeps exception fidelity (ruling 2); anything about the client copy or
   the i18n catalogs (A11); whether `url_routes` / `auth_service:196` get the same
   treatment (follow-up rows).

### Open rulings for Fable

1. **Give `scs:3542` / `:4118` a `code` (e.g. `PARSE_FAILED`) and make the floor
   unconditional?** Cleaner invariant ("every orchestrator exit is coded"), but it
   changes that failure's wire `code` from `BAD_REQUEST` to a new value. *Recommendation:
   NO for W4-9 — keep the allowlist; log it as a follow-up so the codeless arm can be
   retired later in a client-contract-aware unit.*
2. **Preserve `search_logs.error_message` fidelity?** Only safe route is a private key
   plus a `pop` on every surface that returns the dict (`image_routes:360` today).
   *Recommendation: NO — accept the loss; `logger.error(exc_info=True)` + Sentry carry
   the diagnostic, and the private-key convention is one refactor away from re-leaking.*
3. **Status 400 → 500 for `INTERNAL_ERROR`?** *Recommendation: NO in this unit — separate
   row, it moves the response across `parseApiError`'s 503/non-503 boundary and the
   mobile failure-classification buckets.*
4. **Scope confirmation:** `url_routes` (measured safe today) and `auth_service:196-201`
   (`[B4-BE-DIAG] supabase_error=…`) OUT, as follow-up rows. Confirm.

---

## 9. Blast radius

**`structured_comparison_service.compare_from_text`** — 4 non-test callers
(`grep -rn "compare_from_text\b" app/ scripts/ --include=*.py`, excluding the defs):
`app/api/text_routes.py:373` (POST), `:565` (GET), `:1026` (`/text/quick`),
`app/api/image_routes.py:304` (camera), plus `scripts/cron_warm_price_cache.py:225`
(offline warmer, no wire). All four route callers are analysed above; the warmer only
reads `result.get("success")`.

**`compare_from_text_streaming`** — 1 non-test caller: `app/api/text_routes.py:794`.

**`_surface_comparison_failure`** — 2 call sites (`text_routes.py:415`, `:603`) and 5
test files naming it (`test_text_routes_error_mapping.py`, `test_http_400_cap_cut_mapping.py`,
`test_openai_breaker.py`, `test_m13_26_image_error_envelope.py` (comment only),
`app/api/image_routes.py:386` (comment only)).

**Comm-gate blast surface:** 189 test files (§ 5 gate 2), set in
`.qa-w4/comm-set-W4-9.txt`.

**Wire-contract delta (what a client sees change):**

| surface | before | after |
|---|---|---|
| POST/GET `/text/compare`, generic failure | `{error: <raw str(e)>, code: "BAD_REQUEST", request_id}` | `{error: <constant>, code: "INTERNAL_ERROR", request_id}` |
| POST/GET `/text/compare`, parser failure | `{error: <parser copy>, code: "BAD_REQUEST", request_id}` | **unchanged** |
| POST/GET `/text/compare`, coded failures | unchanged | **unchanged** |
| SSE `error` event, generic failure | `{success:false, error: <raw>, total_cost}` | `{success:false, error: <constant>, code:"INTERNAL_ERROR", total_cost, request_id}` |
| SSE `error` event, coded failures (`CONTENT_UNAVAILABLE`, parser) | as today | **+ `request_id` only** |
| SSE non-error events | unchanged | **unchanged** |
| POST `/text/quick`, generic failure | `{error: <raw>, code:"BAD_REQUEST", request_id}` | `{error: <constant>, code:"BAD_REQUEST", request_id}` |
| POST `/image/identify`, `return result` arm | `{success:false, error: <raw>, action:"comparison", metadata}` | `{success:false, error: <constant>, code:"INTERNAL_ERROR", action:"comparison", metadata}` |

**Client impact — the phones run the PRE-OTA bundle (`97b5f15`), so this is the binding
case:**

* **SSE `error` (the primary compare path): IMPROVED.** `97b5f15:api.ts:570` →
  `new Error(parsed.error)` → `97b5f15:HomeScreen.tsx:388`
  `Alert.alert(t('common.error'), error.message || …)`. Today that modal shows the Python
  exception text; after the fix it shows the constant English sentence. The added `code`
  and `request_id` keys are ignored by that branch — **no pre-OTA code path reads them**,
  so nothing can break.
* **`/image/identify`: IMPROVED and shape-compatible.** The added `code` key is additive;
  `action` and `metadata` are unchanged, so the camera result handling is unaffected.
* **`/text/quick`, sync `/text/compare`: no pre-OTA caller** (`handleTextCompare` is
  SSE-only; the `api.ts` GET fallback forwards `code` and `error` into a synthetic error
  whose `code` the M18 branch already tolerates).
* **Post-OTA (HEAD client): IMPROVED.** `errorCopy.friendlyErrorKey('INTERNAL_ERROR')` →
  `home.errors.comparison` (key present in `en.json` and `ar.json`). And `api.ts:944-950`
  stops collapsing this error event into `TIMEOUT`, because a code is now present — the
  user gets the correct generic copy instead of "still gathering prices".
* **No `SmartCompareApp/` file is modified by this unit.**

**Final state of this worktree:** `git status --short` is EMPTY. `.qa-w4/` does not appear
as `?? .qa-w4/` because `.gitignore:72` ignores `.qa-*/`; the spec and the probe outputs
live there and are untracked-and-ignored by design. No file under `app/`, `tests/`,
`scripts/`, `SmartCompareApp/` or `docs/` was written.

---

# FABLE REVIEW RULINGS (binding, 2026-09-23) — W4-9 error envelope, not `str(e)` (PO-RECORDED-MEASURED-05)

Reviewer verdict DEFECTIVE (Opus 5.5 adversarial spec review, read-only, at `b63a8368`). The two orchestrator catches, every HEAD anchor, `image_routes.py:360`'s verbatim return, the allowlist safety and the request_id stamp all hold. The spec's client-impact narrative, its disclosure inventory and four of its tests do not. This unit stays UNFLAGGED. Everything below overrides the spec body where they conflict; the red phase runs against this overlay, no separate rewrite round.

## R1 (BLOCKING) — the client-impact section is rewritten; the "pre-OTA IMPROVED" claim is deleted
`ENABLE_EXPO_FETCH_SSE_DEFAULT` is `false` at 97b5f15 AND at HEAD (`features.ts:52`), so the phones never open `/compare/stream`: a text compare is sync `GET /api/v1/text/compare`, and the pre-OTA Alert shows the axios string "Request failed with status code 400" both today and after the fix (measured with real axios + the 97b5f15 `parseApiError`). HEAD's `friendlyErrorKey` maps BAD_REQUEST and any new code to the same `home.errors.comparison`. **The unit's value is wire disclosure to direct API callers plus what gets PERSISTED and SHARED — not UI.** The PR body says exactly that.

## R2 (BLOCKING) — scope: the leak class lives one layer down; three more sites are IN
(a) The two orchestrator generic catches (`scs:~3927` sync, `:~4718` stream) as specced. (b) **`extraction_service.parse_product_query:~1392`** — its catch returns `{'products': [], 'error': str(e)}`, and the parser exits (`:3542` / `:4118`) ship that dict as the nested `parsed` key of the SSE error event (measured on the wire: an OpenAI-429 string with `insufficient_quota` and an org id). The frozen-exit ruling is overturned to this extent: the catch stores a constant + `logger.error(..., exc_info=True)`, and the parser exits emit `parsed` with ONLY `products` (or drop it). (c) **`extraction_service.generate_comparison:~2549`** — its catch's `error: str(e)` rides SUCCESS payloads (`comparison.error` on sync 200, SSE `verdict` / `settle_complete` / `complete`, `/url/compare`), passes `_validate_renderable`, is persisted by `save_comparison` and served on unauthenticated `GET /api/v1/share/{token}`: constant + log. (d) **SSE route floor** at `text_routes:~887`: a codeless error payload gets `code: INTERNAL_ERROR` and the constant before serialisation, symmetric with the sync floor — this is what lets test 9 go green. (e) Enumerate every other `return {... str(e) ...}` / `f"{e}"`-in-a-dict site under `app/services` and `app/api` (grep, then read): any that reaches a response body, a persisted row or an SSE event through the orchestrator is IN; the rest (e.g. `extract_specs:~1555`, `extract_price`, `auth_service:196-201`, `url_extraction_service` — already constants at `:444/:577`) are listed in the PR as `PO-RECORDED-MEASURED-05c` with their measured reachability.

## R3 — tests
Test 4 drives the REAL `parse_product_query` with `guarded_llm_create` raising an OpenAI-429-shaped string carrying a fake org id, and asserts the raw string is absent from the SSE error event (`parsed` sanitised) AND the log carries it with `exc_info`. Test 14 (camera) injects at `_resolve_pair_category` (which runs on the vision path; `parse_product_query` is skipped there — measured call_count 0) under a socket guard that blocks non-loopback connects and DNS. Add a test for the phones' real shape (`GET /text/compare?product_a=&product_b=` ⇒ `explicit_pair`), injecting at `_resolve_pair_category`, asserting the sync body carries the constant + `INTERNAL_ERROR` + `request_id` and never the raw string. New pin for R2(c): with `generate_comparison` failing, the raw string is absent from the sync 200 body, every SSE event, the persisted row and the share payload. Tests 4 and 6 compare against the LITERAL user sentence when they guard copy (the imported-constant comparison cannot redden the "change the constant" mutation). Test 7 is dropped (verbatim duplicate of `test_no_code_raises_400_plain`); test 15 stays, labelled a copy fence.

## R4 — status code
400 stays for this unit (diff size), with the measurement recorded that 500 is client-neutral on both generations (`parseApiError` collapses only 503; no 5xx retry) and would make Railway 5xx monitoring truthful — follow-up `05d`.

## R5 — honest limits and follow-ups
Add: the admin `get_error_stats.common_errors` KPI (`analytics_service.py:119-150`, served by `admin_routes.py`) collapses sync text failures to one constant row (the stream path already logs a constant — parity). The unflagged SSE `request_id` stamp changes EVERY error event's shape (CONTENT_UNAVAILABLE, LLM_UNAVAILABLE, the parser exit), harmless as measured — the wire-delta table says so. Follow-up `05b`: the camera return-result arm treats `success:false` as a delivery (credit kept, `log_search success=True`, `action='comparison'`, the pre-OTA client renders an empty result) — its own unit, not this one.

## R6 — gates and merge order
Preserve suite (17 passed) plus the 189-file comm set (204 if the new files are added), `comm -13` empty; unflagged, so no byte-identity gate; ruff + py_compile. Merge after W4-1 (every scs anchor from `:1515` shifts +5). `search_logs.error_message` fidelity loss accepted (ruling 2 stands).
