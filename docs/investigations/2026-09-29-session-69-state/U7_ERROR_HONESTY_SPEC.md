# U7 — error honesty when the engine is down — unit spec (client + one backend seam)
**SESSION 69 CORRECTION (2026-09-29):** Status: SHIPPED — PR #258, main 3c5e4ff4 (follow-ups #259, #260, #261).

**Session 69, audit findings RT-1 (copy blames the user), BP-04 / A-C14 (LLM_UNAVAILABLE copy), A-C19 (degraded HTTP 200 shown as a normal result), RT-1 camera loop.** Owner: Claude. JavaScript except one optional backend seam.

## 1. Measured base (main `89f2dc6a`)

- With OpenAI down the explicit-pair compare (`src/services/api.ts:630-641` → `GET /api/v1/text/compare?product_a&product_b`) runs Phase-1 scraping and then fails at the verdict; the backend returns `{success:false, code:'INTERNAL_ERROR'}` (`app/services/structured_comparison_service.py:4261-4272`) or `INSUFFICIENT_DATA` when Phase-1 also failed; with `ENABLE_LLM_PREFLIGHT_BREAKER` ON it returns `{success:false, code:'LLM_UNAVAILABLE'}` → HTTP 503 (`app/api/text_routes.py:399`).
- The client maps every code other than TIMEOUT / RATE_LIMITED to one alert: title "Hold on — give it another tap." body "Sharper match coming up — try with brand or model." (`src/utils/errorCopy.ts`, `src/services/api.ts:1011-1015`, `src/utils/failureClassification.ts:57`); `INSUFFICIENT_DATA` → "Thin data on that pair — swap in two products with brand and model." That tells the reviewer their input was wrong.
- A verdict failure AFTER Phase-1 can also come back as HTTP 200 `success:true` with `comparison.error = "verdict generation unavailable"`, a template winner reason and empty pros/cons (`app/services/extraction_service.py:2754-2756`, `app/services/response_builder.py:1892,2219`); the client renders it as a normal result.
- Camera: `identify_products` does not catch the 429 → `/image/identify` returns HTTP 500 "Image analysis failed…" (`app/api/image_routes.py`); the client maps that 5xx to the "Still gathering prices / Tap to retry" loop (`src/utils/failureClassification.ts`, `ResultsScreen.tsx` around :274-317).

## 2. Target

R1 **Outage copy.** `errorCopy.ts` gets an `engine_unavailable` family (EN + native MSA AR): title "Qaren is catching its breath" / body "Our comparison engine is unavailable for a moment. Your comparison was not counted; please come back shortly." (no "failed", no "try again" — copy policy). It is used for backend codes `LLM_UNAVAILABLE`, `INTERNAL_ERROR`, HTTP 503 and 502/504 from the compare, stream and URL-compare paths. `INSUFFICIENT_DATA` keeps its own copy (it IS about the pair). `TIMEOUT` / `RATE_LIMITED` unchanged.
R2 **Degraded result is shown as degraded.** When a 200 payload carries `comparison.error` (or the BC alias the response builder sets), the results screen shows a visible "partial result" notice at the top (copy: "We could not generate the full verdict this time; scores and prices below are real, the written verdict is not.") and hides the template winner reason / empty pros-cons blocks instead of rendering them as if real. History keeps the row but marks it partial. (No banner elsewhere — the no-info-banners rule applies to informational banners, not to a truth notice about the result itself; ruling R-B.)
R3 **Camera.** A 5xx or `LLM_UNAVAILABLE` from `/image/identify` is classified as `engine_unavailable`, not as the price-gathering retry loop; the reviewer sees the R1 copy with a way back.
R4 **Backend seam (optional, flag-free, small):** `image_routes` returns the same `{success:false, code:'LLM_UNAVAILABLE'}` 503 envelope as the text routes when `identify_products` raises an OpenAI `RateLimitError` / connection error (instead of a bare 500), so R3 has a stable code to key on. Covered by a pytest through the bounded runner; no change to the 200 path.
R5 Nothing else: no flag flips, no copy changes to unrelated alerts.

## 3. Tests (RED at base)

T1 `__tests__/errorCopy.engineUnavailable.s69.test.ts`: the classification maps `LLM_UNAVAILABLE`, `INTERNAL_ERROR`, 503, 502, 504 → `engine_unavailable`; `INSUFFICIENT_DATA` unchanged; both catalogs carry the keys; the old "try with brand or model" copy is NOT used for those codes.
T2 `__tests__/screens/ResultsScreen.degraded.s69.test.tsx`: a payload with `comparison.error` renders the partial notice and no template winner reason; a payload without it renders as today.
T3 `__tests__/screens/camera.engineUnavailable.s69.test.tsx`: a 503 `LLM_UNAVAILABLE` (and a bare 500) from identify shows the R1 copy and does not enter the "still gathering prices" loop.
T4 backend `tests/test_image_identify_llm_unavailable_s69.py`: with the OpenAI client raising `RateLimitError`, `/api/v1/image/identify` returns 503 `{success:false, code:'LLM_UNAVAILABLE'}` and refunds the credit like the text route.

## 4. Gates

- Client: jest by path `'\.s69\.test|Results|errorCopy|failureClassification|camera'`, FULL suite (orchestrator), tsc, eslint by path.
- Backend: the new test + `tests/test_openai_breaker.py` + the image-route tests through `pyt.py` (bound 900); ruff count unchanged; py_compile.

## 5. Rulings

- R-A: the outage copy never mentions OpenAI by name (the consent sheet, U3, does).
- R-B: the partial-result notice is a truth notice, allowed by the no-info-banners rule.
- R-C: no flag; both halves are unconditional.
- R-D: never `git checkout --`; junction rules; bounded runner for every pytest.
