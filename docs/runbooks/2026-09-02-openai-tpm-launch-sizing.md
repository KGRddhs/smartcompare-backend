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
| gpt-4o (verdict) TPM | 30,000 ÷ ~4,500 tokens/verdict | **~6.6 verdicts/min** — **CORRECTED 2026-09-07 (m22 load review, LS-CONCURRENCY-LIMITS-06): the real `build_verdict_prompt` tokenises to 5,498–5,942 prompt tokens over the recorded fixtures (measured twice, independently), and `extraction_service.py:2447` passes `max_tokens=1000`, which OpenAI charges to TPM at admission → 6,500–6,800 TPM per verdict → 4.4–4.6 verdicts/min (5.2/min if the reservation premise is discarded). Also `verdict_chain_max_attempts()` resolves to 6 in prod (both retry knobs unset), not the 3 this runbook documents as the launch setting.** |
| RPM (either model) | 500 ÷ per-compare calls | not binding |

So the restored product's deployment-wide ceiling is **~4.4–5.2 compares per
minute on the gpt-4o verdict leg (CORRECTED 2026-09-07; was published as ~6.6–10; MODELLED, conditional on Tier 1)** — a tokens-per-minute wall, not a
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
| `OPENAI_MAX_RETRIES` | `2` (== SDK default) | SDK retry ceiling for all five AsyncOpenAI constructions (`openai_service.py` module client + both per-project clients, `extraction_service.get_client`, `url_extraction_service.get_client` — the last added by #265, session 70) |
| `OPENAI_FALLBACK_MAX_RETRIES` | inherits `OPENAI_MAX_RETRIES` | Ceiling for the verdict chain's 429 fallback onto the standard model (`extraction_service`, applied per call via `with_options`) |

The explicit worst-case attempt count is
`model_config.verdict_chain_max_attempts()` =
`(1 + OPENAI_MAX_RETRIES) + (1 + OPENAI_FALLBACK_MAX_RETRIES)`.

**Launch settings (set in Railway together with re-funding):**

```
OPENAI_MAX_RETRIES=1            # 2 attempts per call — one genuine retry for the verdict
OPENAI_FALLBACK_MAX_RETRIES=0   # the fallback never retries into a saturated mini budget
```

⇒ worst-case chain = **3 attempts** (down from 6). Note that
`OPENAI_MAX_RETRIES` is read when each client is BUILT, never per call: the
module-level `openai_service.client` reads it at import, and the lazily-built
clients (`openai_service`'s per-project clients, `extraction_service.get_client`
and `url_extraction_service.get_client`) read it once, at first construction,
and cache it for the life of the process. A Railway change therefore reaches
all five on the next restart or redeploy (corrected in session 71; this
sentence used to say the lazily-built clients pick it up without one). Only the
per-call fallback ceiling (`OPENAI_FALLBACK_MAX_RETRIES`, or the
`OPENAI_MAX_RETRIES` it inherits when unset, applied via `with_options`) is
re-read on every fallback call. The SDK honours a 429's `Retry-After` header on
the retries it does make; capping retries does not change that.

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

## 6. Daily gpt-4o cap (`DAILY_4O_CAP`, #268)

**Status:** the env read ships with the session-70 OAI_OBS unit. Unset in
production = today's routing (the class constant, 1,000,000). Choosing a value
is **Ahmed's decision and his env action**; this unit sets nothing on Railway.
Every number in this section is **MODELLED** unless it says otherwise.

**How the router uses it.** `ModelRouterService.get_model(priority="high")`
reads `DAILY_4O_CAP` on every call (`daily_4o_cap()`; no restart needed) and
routes the verdict to the standard model once today's counter reaches
`SWITCH_THRESHOLD` (0.80) of the cap. Each such decision logs one INFO line,
and the response carries `metadata.model_downgraded: true`.

**What the counter counts.**
- `response.usage.total_tokens` of each verdict API call that RETURNED a
  response on the configured verdict model: `record_usage` filters on
  `model_config.verdict_model()` (`model_router_service.record_usage`, called
  from `extraction_service.generate_comparison`).
- "Returned" is the bar, not "parsed": `record_usage` runs before the JSON
  parse, so a response that later fails to parse is still counted.
- It does NOT count the Tier-3 spec synthesis call. That call is routed by the
  same `get_model("high")` (`structured_comparison_service`, `_synth_call`;
  `max_tokens` 300 in `openai_service.extract_specs_synthesized`; up to 2 per
  compare) and runs on gpt-4o below the threshold, but it is never recorded.
  **The cap bounds verdict tokens, not total gpt-4o tokens** — real gpt-4o
  spend is higher than the counter.
- Keys roll over at 00:00 UTC (`openai:4o:tokens:<UTC date>`).

**Per-verdict tokens (MODELLED).** Prompt 5,498–5,942 tokens (the offline
count in the §2 correction); completion bounded by `max_tokens=1000`, real
size UNMEASURED. That is roughly **5.5k–6.9k counted tokens per verdict**
(MODELLED).

**Shipped default (MODELLED).** `1,000,000 × 0.80 = 800,000` counted tokens,
reached at about **116–145 verdicts per UTC day** (MODELLED; matches the
session-69 decision memo's R-C14).

**~200 verdicts/day (MODELLED).** `200 × ~6.9k ≈ 1.38M` tokens needs
`cap ≥ 1.38M / 0.80 ≈ 1.73M`. Suggested setting: `DAILY_4O_CAP=2000000`,
which puts the threshold at 1.6M — about **232–290 verdicts per day**
(MODELLED). If `ENABLE_SELF_CRITIQUE` is ever turned on, a regenerated
verdict spends a second verdict-model call; size the cap for it.

**Read before choosing a value (decision inputs, UNMEASURED for this org).**
- The router's own purpose is to "never fall off the data-sharing free tier
  mid-day" (module docstring). OpenAI's complimentary gpt-4o allowance under
  data sharing is **tier-dependent: 250K tokens/day on usage Tiers 1–2, 1M
  tokens/day on Tiers 3–5**, shared across the large-model group and across
  the organisation's projects; overage bills at list price; it resets at
  00:00 UTC. **This org's usage tier and whether it is enrolled in data
  sharing at all are UNMEASURED** — Ahmed reads both in the OpenAI dashboard
  before choosing. Do not assume 1M.
- Paid tokens above the allowance: the shipped default already lets up to
  800K counted verdict tokens through per UTC day, which is above a 250K
  (Tier 1–2) allowance. `DAILY_4O_CAP=2000000` lets up to 1.6M through, which
  is above even a 1M allowance, so the excess bills at list price (MODELLED).
- The daily dollar cost of the chosen cap must be read from OpenAI's pricing
  page when the value is set. It is not stated here.

**Operator trap — write digits only.** `DAILY_4O_CAP=2000000`. `2e6` and
`2_000_000` are also accepted (Python `float()` accepts them; measured).
`2,000,000` (commas), hex (`0x…`), a blank value, `inf`, `nan` and anything
below 1 are rejected and **silently fall back to 1,000,000**. After setting the
value, verify it: `GET /api/v1/admin/costs/gauges` → `openai_4o_today.cap`
(the gauge reports the cap the router uses), or the `cap=` field of the INFO
line below.

**Limits.**
- Overshoot: the counter is incremented after each call returns, so
  concurrent in-flight verdicts can overshoot the threshold by about
  (concurrency × ~6.9k) tokens (MODELLED).
- TPM-blind: the cap is a daily spend guard. It does not protect the
  per-minute wall (§2).
- Redis down: a failed counter read counts as 0, so every verdict runs on the
  verdict model and cap protection is lost until Redis returns; the increment
  is best-effort too.

**Observability.**
- The INFO line in the Railway logs, one per downgrade decision:
  `[MODEL_ROUTER] 4o cap reached: routing verdict to <standard model> (used=<n> cap=<n> threshold=0.80)`.
  It also fires for the Tier-3 synthesis `get_model("high")` call, whose line
  also says "routing verdict", so **line counts overstate downgraded
  verdicts**.
- Count `metadata.model_downgraded: true` on responses instead. The key is a
  bare boolean, present only when true, on the full sync body and the SSE
  `settle_complete` / `complete` events (never on a partial response or on
  `/api/v1/url/compare`). It is set for BOTH the cap downgrade and the
  existing 429/rate/quota fallback onto the standard model; the two are told
  apart only in the logs (the INFO line above vs the WARNING
  `[model_router] … rate-limited mid-call; falling back to …`).
- Stated limit: the fallback trigger is a substring test on `'429'` / `'rate'`
  / `'quota'`, and `'rate'` also matches words such as "generate", so the
  marker can mark a verdict that fell back after a non-429 failure.
  Pre-existing; not changed here.
