# D2 Error / Partial Contract (genuine-bh-latency-warmer bundle)

**Status:** LOCKED + IMPLEMENTED. Owner: be-core. Consumers: fe (WS6), qa, test.
**As-shipped commits:** WS1 `6bfe830` (+ `33645e3` spec-named tests), route mapping in
`app/api/text_routes.py`, fe consumption `0fe1cba` + `5981493` (AR copy).

This is the BE↔FE wire contract for what `/api/v1/text/compare`
(GET + POST + SSE stream) returns when a comparison hits the hard cap or runs
out of usable data. It replaces the old behaviour where ANY hard-cap timeout on
a valid query collapsed to **HTTP 400 `BAD_REQUEST`** with scary copy
("We couldn't finish… Try again.") — the Tom Ford "couldn't load" surface.

The FE i18n-substitutes by **code**, never by the backend `error` string.

---

## 1. HTTP 200 — best-available PARTIAL (the common degrade)

Body: a normal success response **plus** `metadata.partial: true`.

```json
{
  "success": true,
  "overview": { ... }, "specs": { ... }, "reviews": { ... }, "scoring": { ... },
  "metadata": { ..., "partial": true }
}
```

- Prices carry an **honest** `source_method`, priority
  **genuine** (`local_bhd` / `page_scrape_jsonld` / `shopify_json`) **>**
  `converted_usd` **>** `estimated` (last resort).
- A product with no price at all may have `price: null` — the FE renders its
  placeholder; the response is NOT a failure.
- `metadata.partial` **absent or false** = a complete result (today's happy path,
  unchanged).

**Backend:** `compare_from_text` stashes each stage onto `self` as it lands
(product_data after Phase 1, scoring/names after scoring, comparison after the
verdict). On `asyncio.TimeoutError` at the hard cap, if ≥1 product has usable
data it returns `_build_partial_response()` (reuses
`response_builder.build_comparison_response`, which defaults every missing
stage) with `success:true` + `metadata.partial:true`.

**FE:** when `metadata.partial === true`, render normally (it is a real result).

## 2. HTTP 503 — true TIMEOUT failure (no usable data at all)

```json
{ "success": false, "error": "<friendly>", "code": "TIMEOUT", "request_id": "<uuid>" }
```

- Status **503** (transient / retryable), code the literal string **`TIMEOUT`** —
  NOT `BAD_REQUEST`, NOT the 503-default `FEATURE_DISABLED`.
- **Mechanism (verified):** the route raises
  `HTTPException(503, detail={"code": "TIMEOUT", "error": <friendly>})`.
  `app/middleware/error_handler.py::http_exception_handler` recognises the
  structured detail (`_is_structured_detail`) and **overrides** the
  `STATUS_CODE_MAP[503]="FEATURE_DISABLED"` default with the explicit code
  (L84-88). No `JSONResponse` fallback needed.

**FE:** `parseApiError` maps code `TIMEOUT`/`STREAM_TIMEOUT` OR status 503 →
`{ message: '', code: 'TIMEOUT' }` (empty message so the backend string can
never reach the UI) → soft tap-to-retry state.

## 3. SSE stream

On the streaming hard cap the orchestrator emits **both** a `settle_complete`
and a `complete` event:

```json
{ "success": false, "code": "STREAM_TIMEOUT", "partial": true, ... }
```

- `STREAM_TIMEOUT` is a distinct code by existing design; the FE SSE error
  branch handles **both** `TIMEOUT` and `STREAM_TIMEOUT`.
- Already-streamed partial specs/prices remain rendered; prefer them.

## 4. INSUFFICIENT_DATA — both products zero usable data (unchanged)

```json
{ "success": false, "code": "INSUFFICIENT_DATA",
  "error": "Comparison data was incomplete — choose different products." }
```

- HTTP **400** (non-stream); `settle_complete` + `complete` (stream).
- Distinct from TIMEOUT (which is 503). The route preserves the code.

## 5. Route mapping (`text_routes._surface_comparison_failure`)

| service result `code` | wire surface |
|---|---|
| (success / partial) | 200 body (never reaches the failure map) |
| `CONTENT_UNAVAILABLE` | 200 structured body (FE reads body, not status) |
| `TIMEOUT` | **503** `{code:"TIMEOUT", error}` |
| `INSUFFICIENT_DATA` | 400, code preserved |
| any other / no code | 400 |

## 6. Copy contract (no-scary, per `SmartCompareApp/src/i18n/.copy-policy.json`)

Forbidden EN: `couldn't`, `try again`, `Failed to`. Forbidden AR: `تعذر`, `فشل`,
`تقدير`, `مُقدَّر`.

- Backend `TIMEOUT_FRIENDLY_MESSAGE` (API-level fallback, FE i18n's by code):
  **EN** `"Still gathering prices — give it another tap in a moment."`
- **AR** (blessed by fe, matches the established `home.limit.rate_body`
  "أمهلها لحظة" voice): `"ما زلنا نجمع الأسعار — أمهلها لحظة ثم اضغط مجددًا."`

## 7. Tests pinning this contract

- `tests/test_compare_timeout_graceful.py` — service partial / insufficient /
  timeout matrix + forbidden-vocab.
- `tests/test_text_routes_error_mapping.py` — `_surface_comparison_failure` +
  the error_handler 503/TIMEOUT unwrap + route e2e.
- `tests/test_http_400_cap_cut_mapping.py` — rewritten to pin TIMEOUT→**503**
  (was the old TIMEOUT→400 bug).
- FE: `SmartCompareApp/__tests__/ResultsScreen.timeout.test.tsx` (23 tests).
