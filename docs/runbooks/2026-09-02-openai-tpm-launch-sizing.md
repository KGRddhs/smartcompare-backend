# OpenAI re-funding launch: TPM sizing + retry-amplification runbook (#117)

**Status:** OpenAI is DEFERRED (429, no credits). Nothing in this document was
measured against a live OpenAI account. Every throughput figure below is
**MODELLED** from source-derived token profiles and vendor-published limits;
each is labelled. The account's real tier is **UNKNOWN** — verifying it is a
hard launch gate, not an optional step.

Filed from the M18 review (`docs/investigations/2026-09-01-m18-product-app-load-review.md`,
finding LS-capacity-math-03).

---

## 1. Launch gate — verify the tier FIRST (Ahmed's step)

Read the account's actual rate limits from the OpenAI dashboard
(Settings → Limits) **before** re-funding and record them in this file:

| Field | Value (fill in on verification) |
|---|---|
| Account tier | _unverified_ |
| gpt-4o TPM / RPM | _unverified_ |
| gpt-4o-mini TPM / RPM | _unverified_ |
| Verified on / by | _unverified_ |

**Do not re-fund and launch on the Tier-1 numbers.** If the account is Tier 1,
the honest options are (in order of preference): raise the tier before any
real traffic; move the verdict onto mini (lifts the binding wall from
~6.6/min to ~10/min, MODELLED); or add a verdict cache keyed on the
normalised product pair (repeated pairs are common in a comparison product —
a dedupe lifts the 4o wall without spending anything).

## 2. The sizing arithmetic (MODELLED — re-derive from data once live)

Token profile per compare (**estimates from the prompt/response shapes, not
instrumented measurements**): cold ≈ 19–25k mini tokens + ~4.5k gpt-4o
(verdict); warm ≈ 5.2k. Latency anchors from the M18 review (MODELLED from
source at the lanes' declared RTTs): warm compare ~2.2–2.4s, cold ~6–7s, on a
**single uvicorn worker**.

Against OpenAI's published **Tier-1** limits (vendor documentation, not
measured here: 200K TPM gpt-4o-mini, 30K TPM gpt-4o, 500 RPM each):

| Binding limit | Arithmetic | Ceiling (MODELLED) |
|---|---|---|
| gpt-4o-mini TPM | 200,000 ÷ ~20,000 tokens/cold compare | **~10 cold compares/min** |
| gpt-4o (verdict) TPM | 30,000 ÷ ~4,500 tokens/verdict | **~6.6 verdicts/min** |
| RPM (either model) | 500 ÷ per-compare calls | not binding |

So the restored product's deployment-wide ceiling is **~6.6–10 compares per
minute (MODELLED, conditional on Tier 1)** — a tokens-per-minute wall, not a
requests-per-minute one. The only breaker in the code watches a **daily**
counter (`model_router_service.DAILY_4O_CAP`), which is structurally blind to
TPM: it cannot fire before a mid-minute wall is hit.

**Interaction with the `[ratelimit]` issue (#114):** the mis-keyed
deployment-wide 10 compares/min limiter bucket happens to sit at almost
exactly this ceiling today. Fixing the limiter key without this sizing work
moves the wall from a clean front-door 429 to a mid-compare OpenAI 429 with a
retry storm behind it — a strictly worse failure mode. **#114 lands after the
M24 offloads and after this runbook's knobs are set.**

## 3. Retry amplification — knobs shipped by #117

Without an override the SDK defaults to 2 retries = **3 attempts per call**,
and the verdict chain's second-model fallback multiplied that again: worst
case **6 upstream attempts for one verdict** during a 429 storm — the storm
makes the saturation worse, not better.

Knobs (resolved through `model_config`, never `app/config.py`; defaults are
byte-identical to the pre-#117 behaviour):

| Env | Default | Meaning |
|---|---|---|
| `OPENAI_MAX_RETRIES` | `2` (== SDK default) | SDK retry ceiling for all four AsyncOpenAI constructions (`openai_service.py` module client + both per-project clients, `extraction_service.get_client`) |
| `OPENAI_FALLBACK_MAX_RETRIES` | inherits `OPENAI_MAX_RETRIES` | Ceiling for the verdict chain's 429 fallback onto the standard model (`extraction_service`, applied per call via `with_options`) |

The explicit worst-case attempt count is
`model_config.verdict_chain_max_attempts()` =
`(1 + OPENAI_MAX_RETRIES) + (1 + OPENAI_FALLBACK_MAX_RETRIES)`.

**Launch settings (set in Railway together with re-funding):**

```
OPENAI_MAX_RETRIES=1            # 2 attempts per call — one genuine retry for the verdict
OPENAI_FALLBACK_MAX_RETRIES=0   # the fallback never retries into a saturated mini budget
```

⇒ worst-case chain = **3 attempts** (down from 6). Note the module-level
`openai_service.client` reads the knob at import — a Railway change reaches it
on the next restart; the lazily-built clients and the per-call fallback pick
it up without one. The SDK honours a 429's `Retry-After` header on the
retries it does make; capping retries does not change that.

## 4. Activation preconditions (pair with re-funding — no new code)

- **`ENABLE_FULL_STREAM_DEADLINE=true` is a hard pairing with OpenAI
  re-funding.** With it OFF (the shipped default), the streaming verdict +
  self-critique are awaited OUTSIDE the 30s cap: under degradation a single
  tail call can hold an SSE connection for ~3×120s + backoff ≈ 6.5 minutes
  (worst chain ≈ 13 minutes, MODELLED from the timeout/retry shapes) — and
  M13-35's drain-not-abandon keeps abandoned streams burning server-side.
  With the flag ON the tail caps at the residual budget and yields a PARTIAL.
- `ENABLE_PREVERDICT_DISCONNECT_ABORT=true` is complementary (stops paying
  the OpenAI tail for a client that already left); see the M18
  CD-interactions-01 entry in CLAUDE.md.
- The M24 offload wave (#115/#116) should be canaried per its own
  preconditions; it is independent of these knobs.

## 5. What this unit deliberately did NOT do

- **No TPM-aware router** (`ENABLE_TPM_AWARE_ROUTING`, the per-minute token
  counter downshifting `get_model("high")`): deferred — the M24 wave scoped
  #117 to bounding the amplification + writing this arithmetic down. File it
  against the router when the tier is known, because the correct threshold is
  a function of the verified TPM, and build it on the atomic INCRBY idiom
  `tests/test_model_router.py::test_record_usage_uses_atomic_incrby` pins.
- **No per-compare token instrumentation** yet — until it lands, the table in
  §2 cannot be re-derived from data; treat every number above as MODELLED.
- **No live call and no load test.** A staged load test needs an isolated
  environment with its own Upstash, its own Supabase, its own OpenAI project
  and budget, and Ahmed's explicit GO — the point of this arithmetic is to
  avoid discovering the ceiling by paying for it.
