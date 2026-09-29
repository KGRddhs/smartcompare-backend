> Orchestrator's note (Fable, 2026-09-30): produced by workflow `wf_2cedaf09-66d` (89 Opus 5.5 agents: call-site inventory, cost model, four option lenses, 82 claim refuters, synthesis). Two things to read with care: (1) `STREAM_HARD_CAP_SECONDS` is SET on Railway `web` (CLAUDE.md records 30.0 since 2026-06-09; the memo's "default 25 s" is the code default), so the `ENABLE_FULL_STREAM_DEADLINE` canary in §3.4 is optional for the review window, not required; (2) every dollar figure is modelled from fetched list prices and the runbook token profile, not measured on a live account — the Usage page after the first 50 compares is the real number.

# Decision memo: OpenAI credits or Anthropic for the App Store launch?

Prepared 2026-09-29 for Ahmed (and Husain). Repo `smartcompare` main `eed4ee10`. Price and limit figures come from vendor pages fetched on 2026-09-29. Each figure carries a claim id, and section 6 lists the source for every id.

---

## 1. The answer in three sentences

Production is down for one reason only: the OpenAI organization has no prepaid credit left (`credit_balance_exhausted`), and OpenAI's documented fix is "Add credits" [A-C1]. **Top up OpenAI by $100** (minimum $50), turn on auto-recharge, and submit the App Store build on the stack that every test and quality baseline was measured on. That needs no code change [A-C1, A-C4, B2-C11]. Anthropic is a post-launch failover unit, not a launch path: the config-only shim breaks on current Claude models and drops JSON mode and moderation, and the native SDK migration takes 1.5–2 weeks [B1-C1, B1-C3, B1-C7, B2 effort].

---

## 2. What is broken today and what Apple's reviewer would see

**Root cause.** Railway log 2026-09-28T21:45Z shows OpenAI returning 429 `{"type":"insufficient_quota","code":"credit_balance_exhausted"}` from `extraction_service.parse_product_query` (orchestrator measured facts). OpenAI documents this code as "Your organization has no prepaid credits remaining". Its solution is to add credits at `platform.openai.com/settings/organization/billing`. The same page says "Retrying billing, spend, or quota errors won't restore API access" [A-C1, R-C3, R-C6].

**What each flow returns today** (backend responses from the call-site inventory; the exact on-screen copy for the 400/500 cases was not traced in the mobile app):

| Flow | Response today | Reviewer experience |
|---|---|---|
| Text compare `q=` (`/api/v1/text/compare`, `/text/quick`) | HTTP 400 "Could not identify two products to compare…" (the parse 429 is caught) | Every typed compare fails |
| SSE stream `/text/compare/stream` | HTTP 200 carrying an SSE `error` event with the same text | Every streamed compare fails |
| Camera `/api/v1/image/identify` | HTTP 500 "Image analysis failed. Please try again." (`identify_products` does not catch the 429; the credit is refunded) | Every photo compare fails **[SESSION 69 CORRECTION (2026-09-29): since #258 (main 3c5e4ff4) this returns 503 `LLM_UNAVAILABLE` (image_routes.py:303-315; the 500 remains for non-transient errors); the app on main shows the outage copy with Back (phones get it with the next OTA or the store build).]** |
| explicit_pair / vision after the parse | HTTP 200 `success:true`, but degraded: deterministic winner, template reason "{winner} is the stronger overall pick.", blank `key_tradeoff`/`winner_declaration`, and `comparison.error = "verdict generation unavailable"` | Looks like a thin, broken result, not an error [A-C19]; since #258 the app on main shows `results.degraded.note` and hides the template reason (phones get it with the next OTA or the store build) |
| `/api/v1/url/compare` | 503 `LLM_UNAVAILABLE` | Fails [A-C19] |
| L3/L4 moderation | Fails OPEN (safety silently off) | Not visible |

**The degraded HTTP 200 is a hazard even after the top-up.** If credit runs out or rate limits hit in the middle of a compare, the user gets `success:true` with a template verdict, not an error [A-C19]. The existing smoke script would pass that response [A-C17]. The verification in section 3 therefore asserts that `comparison.error` is absent.

**Not fixed by any LLM decision** (source: pitch-prep memory 2026-09-27):
- No TestFlight or production iOS build has ever existed; only ad-hoc preview builds, on Husain's individual Apple team.
- `qaren.app` returns 522.
- The Arabic walkthrough in `APPLY_PACK_AHMED.md` needs working compares, so the top-up has to come before it.

---

## 3. Option A: stay on OpenAI and top up now (recommended)

### 3.1 Dashboard steps (Ahmed, about 30 min)

0. **Confirm which org you are paying.** In platform.openai.com → API keys, match the *name* of the key set as Railway `web`'s `OPENAI_API_KEY` to its org/project. Never print or paste the key value. Every live call uses this one shared key: `select_client_for_user` has zero callers, so `OPENAI_API_KEY_PRIVATE` is never read [A-C21].
1. **Read Settings → Organization → Limits first.** Record in `docs/runbooks/2026-09-02-openai-tpm-launch-sizing.md` §1, with the date: tier, gpt-4o RPM/TPM, gpt-4o-mini RPM/TPM/RPD, monthly usage limit, and any enforced spend limits. The runbook's tier row is still `_unverified_` and it calls this check "a hard launch gate" [A-C8 gate part, R-C18]. Your org's limits are shown "under the limits section of your account settings" [A-C4].
2. **Buy credits at Settings → Organization → Billing.** Recommended **$100**, minimum $50 (arithmetic in 3.2). After buying, re-open Limits and confirm the tier moved. The fetched page says graduation is automatic but does not say how fast it happens [A-C4, cost-topup].
3. **Turn on auto-recharge on the same page.** Suggested setting: recharge ≥ $50 when the balance falls below $20. The help article covering the fields, minimums and credit expiry returned HTTP 403, so it is **unfetched**. A search snippet (not a fetch) says credits expire after 1 year and the auto-recharge minimum is $5. Confirm both on the billing page [A-C7].
4. **Set spend alerts, not hard caps.** `organization_spend_limit_exceeded`, `project_spend_limit_exceeded` and `organization_usage_limit_exceeded` are all 429s that would recreate this outage. Check three places:
   - Billing, for the credit balance.
   - Organization Limits, for the org spend limit and the OpenAI-assigned usage limit (raising the usage limit takes a request).
   - The **project's own settings**, for the project spend limit [A-C2].

### 3.2 How much to top up

Unit costs are **modelled, not measured on a live account**. They use fetched Standard prices: gpt-4o $2.50 input / $10.00 output per 1M tokens; gpt-4o-mini $0.15 / $0.60; `omni-moderation-latest` Free [A-C3]. They also use the runbook token profile: cold ≈ 19–25k mini tokens (an estimate), plus a verdict prompt of 5,498–5,942 tokens (token-counted offline, twice), plus max_tokens=1000 [B2-C12 corrected].

| Leg | Arithmetic | USD |
|---|---|---|
| gpt-4o verdict input | 5,498–5,942 × $2.50/1M | $0.0137–0.0149 |
| gpt-4o verdict output | 500–1,000 × $10/1M | $0.005–0.010 |
| gpt-4o-mini cold leg | 19k at 85/15 → 25k at 80/20 split | $0.0041–0.0060 |
| **Cold compare** | sum of the above | **$0.023–0.031** (verdict ≈ 81–83%) |
| **Warm compare** | ~$0.0003 parse + full verdict (there is no comparison-level verdict cache) | **$0.019–0.025** |
| Planning figure | blended 60% cold / 40% warm (the warm share is an assumption), high end × 1.5 | **$0.044 per compare** |
| Camera identify (extra) | gpt-4o-mini vision; 4032×3024 photo → 4 tiles → ~26.1k input tokens; tall screenshot → 8 tiles → ~48.8k | $0.004–0.008 per request |

[cost-cold corrected; A-C23; R-C19]

| Scenario | Compares | Planning $ |
|---|---|---|
| App Review (assume all cold) | 50 | $2.30 |
| Demo / pitch week | 200 | $8.70 |
| Month 1 at 50/day | 1,500 | $65 |
| **Subtotal** | | **≈ $76** |
| + ~30% buffer | | **≈ $100** |

[cost-topup]

- **$100** covers the subtotal above. It also brings total paid to the fetched Tier 3 threshold ("$100 paid"), which comes with a $1,000/month usage limit and 800,000 gpt-4o TPM [A-C4, A-C5].
- **$50** is the Tier 2 threshold ("$50 paid", $500/month, 450,000 gpt-4o TPM). It covers review plus the demo week plus about **18 days** at 50/day at planning rates [A-C4, A-C5, cost-topup corrected].
- At 200/day the planning cost is about $261/month. Tier 1's $100/month limit would cut service off around day 17–23 at nominal cost, or day 11–12 at planning cost. Auto-recharge and Tier ≥ 2 are needed at that volume [cost-topup corrected].
- Do not buy Anthropic credits for this launch. The app has no Anthropic code path, and Haiku 4.5 costs 6.7–8.3× gpt-4o-mini per token [B1-C13, A-C3].

### 3.3 Tier gate: throughput

The published gpt-4o limits are: Tier 1 500 RPM / 30,000 TPM; Tier 2 5,000 / 450,000; Tier 3 5,000 / 800,000 [A-C5]. For gpt-4o-mini, Tier 1 also caps at **10,000 requests/day** [A-C6].

OpenAI's guide says a request counts "the maximum of `max_tokens` and the estimated number of tokens", not their sum [A-C8 refuted → corrected]. Verdicts per minute across the whole deployment, modelled:

| Tier | Vendor formula (~5.5–5.9k per verdict) | Runbook's conservative premise (prompt + 1,000) |
|---|---|---|
| 1 | ~5.0–5.5 | ~4.3–4.6 |
| 2 | ~76–82 | ~66–69 |
| 3 | ~135–145 | ~118–123 |

[A-C8, A-C24, R-C18 corrected]

- **Tier 1** is enough for a single Apple reviewer. A demo room where five or more people tap Compare in the same minute will get mid-compare 429s.
- With about 6 mini calls per cold compare (unmeasured), the Tier 1 mini daily cap works out to roughly 1,000–1,700 cold compares per day.
- **Gate:** do not submit until Settings → Limits shows the tier and the TPM figures.

### 3.4 Railway `web` env changes: names, values, order, canary

Values shown are non-secret. Ahmed makes these changes in the Railway dashboard.

| Order | Variable | Value | Why / source |
|---|---|---|---|
| 1 | `OPENAI_MAX_RETRIES` | `1` | Cuts the worst-case verdict chain from 6 attempts to 3 [A-C9]; all other calls go from 3 attempts to 2 |
| 1 | `OPENAI_FALLBACK_MAX_RETRIES` | `0` | Same. If this is left unset it inherits `1`, which gives 4 attempts [A-C9] |
| 1 | `ENABLE_PRICE_CACHE_WARMER` (on `price-warmer`) | stays `false` | Each warmed query is a full cold compare, up to 25 per run [R-C12] |
| 1 | `ENABLE_EVAL_CRON`, `ENABLE_FEWSHOT_ROTATION` | stay unset | Both are fail-closed; neither script is registered as a cron on main [R-C13] |
| 2 | **Redeploy / restart `web`**, then `/health` = 200 | — | Required. The module client and both `get_client` caches read the retry count only when first built; only the verdict fallback reads it per call [A-C10] |
| 3 | `ENABLE_FULL_STREAM_DEADLINE` | `true`, **canary only** | Runbook §4 calls it "a hard pairing with OpenAI re-funding". Without it, one degraded stream tail can hold an SSE connection ~6.5 min (modelled). But the cap is `STREAM_HARD_CAP_SECONDS` (default **25 s**), measured from generator entry, and a slow-but-valid verdict gets cut to a PARTIAL [A-C16 corrected]. The flag is read per call. Run 3 cold `nocache=true` stream compares. If any comes back PARTIAL or without a verdict, set it back to `false` for the review window |
| 3 (optional) | `ENABLE_PREVERDICT_DISCONNECT_ABORT` | `true` | "complementary", not required [A-C16] |
| 4 | `ENABLE_LLM_PREFLIGHT_BREAKER` | `true` **only if Tier ≥ 2**; leave it OFF during verification | Read per call, default OFF [A-C12]. It trips after 3 consecutive transient failures (TPM 429s count) and then refuses every compare for 600 s [A-C13, A-C15]. On Tier 1, one burst would lock a reviewer out for 10 minutes |

**Known gaps Option A does not fix:**
- `url_extraction_service.get_client` passes no `max_retries`, so `/url/*` keeps the SDK default of 2 [A-C11].
- A breaker short-circuit reaches the app as the generic "Sharper match coming up — try with brand or model." That copy is misleading during an outage. The camera path treats the 503 as a timeout [A-C14 refuted → corrected].

### 3.5 Verification after the top-up (gate before submission)

Keep the breaker OFF. Space the calls out (Tier 1 allows about 5 verdicts/min). If the anonymous usage gate rejects a call, add your own test session header; never paste a real credential into a transcript.

```bash
BASE=https://web-production-58776.up.railway.app

# 1. Health
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/health"                 # expect 200

# 2. Smoke pack: expect exit 0. NOTE: registers a throwaway prod user on every run;
#    its only compare probe is a CACHED pair (region=bahrain, nocache=false), so it
#    proves the parse leg is back, NOT that the verdict is real  [A-C17]
python scripts/bundle_d_prod_smoke.py --verbose

# 3. Uncached text compare, en then ar: must be a real verdict, not the degraded 200  [A-C18, A-C19]
for L in en ar; do
  curl -sG "$BASE/api/v1/text/compare" \
    --data-urlencode "q=<pre-tested demo pair>" --data-urlencode "region=bahrain" \
    --data-urlencode "nocache=true" --data-urlencode "lang=$L" \
    -o "cmp_$L.json" -w "$L HTTP %{http_code}\n"
  python -c "import json;r=json.load(open('cmp_$L.json'));c=r.get('comparison') or {};ok=r.get('success') is True and 'error' not in c and bool(c.get('key_tradeoff'));print('$L','REAL VERDICT' if ok else 'DEGRADED',c.get('error'))"
  sleep 20
done

# 4. SSE stream: expect no 'error' event, a final result event, and no PARTIAL
curl -N -sG "$BASE/api/v1/text/compare/stream" \
  --data-urlencode "q=<second pre-tested pair>" --data-urlencode "nocache=true" > stream.txt
grep -c "event: error" stream.txt                                          # expect 0

# 5. Camera: 1–4 real product photos, multipart field 'images'  [A-C18]
curl -s -F "images=@photo1.jpg" "$BASE/api/v1/image/identify?region=bahrain" \
  -w "\nHTTP %{http_code}\n"                                               # expect 200, not 500
```

6. **Logs and usage (dashboards).**
   - In the Railway `web` logs for the verification window, search for `429`, `insufficient_quota`, `credit_balance_exhausted` and `[CIRCUIT]`. Expect none.
   - The OpenAI Usage page should show gpt-4o and gpt-4o-mini requests at the matching times.
   - Use the Usage page for spend. `metadata.total_cost` prices every call at gpt-4o-mini rates [R-C16].
   - Do not paste the post-restart logs anywhere. `extraction_service.py:66` logs the last 10 characters of the key at INFO on first build [A-C22].
7. **Device.** Run the pre-tested demo pairs in en and ar, plus one camera compare, on the exact build Apple will receive. If step 3.4/4 turned the breaker on, run one more compare afterwards.
8. **During review.** Check the balance and auto-recharge daily. Do not switch `OPENAI_MODEL_VERDICT` to gpt-4o-mini to relieve Tier 1: that is an unmeasured quality change.

**Other watch items:**
- Verdicts silently drop to gpt-4o-mini once the day's gpt-4o counter reaches 800k tokens (`DAILY_4O_CAP` 1,000,000 × 0.80). My arithmetic puts that at roughly 115–145 verdicts per UTC day. It does not matter at 50/day; it does matter at 200/day [R-C14].
- Privacy: users who opt out of AI data sharing are still routed through the shared "data-sharing project" key. If the App Store privacy labels or the policy promise opt-out routing, fix the wording before submitting [A-C21].

**Effort.** About 1.5–2.5 hours of Ahmed's time, $100 cash, and no code or PR.

---

## 4. Option B: Anthropic, the honest delta

### B1: the OpenAI-SDK compatibility endpoint (config only: `OPENAI_BASE_URL=https://api.anthropic.com/v1/` plus `OPENAI_MODEL_*`)

**What works.** Routing really is config-only:
- The base-URL validator accepts the Anthropic URL [B1-C19].
- Every model id can be set through env [B1-C20].
- Image `url` is "Fully supported" [B1-C4].

**What breaks** (Anthropic's own page, fetched 2026-09-29):
- **Vendor stance.** "…not considered a long-term or production-ready solution for most use cases" [B1-C1].
- **Current-generation models fail on every call.** On Opus 5.5/5/4.8/4.7 and Sonnet 5.5/5, any non-default temperature returns 400 on every request [B1-C7]. Every app chat call sends a temperature [B1-C9]. A 400 contains no `429`/`rate`/`quota` text, so the verdict fallback never fires [B1-C11]. B1 therefore only works on legacy models: Haiku 4.5, Sonnet 4.6/4.5, Opus 4.6/4.5, where thinking is off by default [B1-C8].
- **JSON mode is gone.** `response_format` is "Ignored" [B1-C3]. Four sites call `json.loads` on the raw reply (targeted and synthesized specs, variant disambiguation, critique) and fail silently to `{}`/None on any fenced or chatty reply. The verdict and extraction sites do cope with a fully fenced ```` ```json ``` ```` reply, but fail on prose before the fence or on a tag that is not lowercase `json`. A failed verdict becomes the degraded HTTP 200 [B1-C10 refuted → corrected].
- **No moderation.** No moderations endpoint is documented, so L3/L4 fail open on 100% of requests [B1-C6, R-C17].
- **No prompt caching.** "Prompt caching is not supported" [B1-C5].
- **Account risks.**
  - A new org "may start in the Evaluation tier, with limits below the standard limits".
  - The Start tier has a $500/month spend cap. Hitting it returns a 429 with no `retry-after` until the 1st of the next month [B1-C15].
  - Which HTTP code prepaid-credit exhaustion returns is not stated [B1-C18].
  - A multi-workspace key needs the `anthropic-workspace-id` header, which the repo cannot send; use a single-workspace key [B1-C2].
  - Haiku 4.5 retirement is "Not sooner than October 15, 2026", 16 days away [B1-C12].
- **Cost.** Haiku 4.5 on the mini leg plus a Sonnet 5 verdict comes to about $0.040–0.073 per cold compare, against $0.022–0.031 on OpenAI: about 1.9–2.4× (outer range 1.3–3.4×). The extra cost is almost all Haiku 4.5 vs gpt-4o-mini [B1-C22 corrected, B1-C13, B1-C14].
- **Camera.** The server accepts 4 × 10 MiB raw images with no resizing [B1-C17]. Claude allows 10 MB *base64* per image and 32 MB per request (413 above that) [B1-C16].
- **No safety net.** No test and no quality baseline has ever run on Claude. All 15,763 CI tests mock OpenAI, and the verdict A/B ran only on OpenAI models [B2-C11].

**Effort.** About 15 min of config, plus 3–5 h of same-day live smoke testing on every flow. Rollback is under 5 min (unset the vars and restart). **Use it only as an emergency stop-gap** if OpenAI billing cannot be restored in time, and only on `claude-haiku-4-5` / `claude-sonnet-4-6`.

### B2: native Anthropic SDK behind a provider flag

**Scope:**
- 16 chat sites plus 1 moderation site across about 15 app files, plus 3 scripts.
- 7 JSON schemas for `output_config.format` (no schema-free mode; recursive, numeric and length constraints unsupported) [B2-C6].
- A moderation replacement.
- A usage-field remap and a per-model cost table.
- About 140–250 of the 838 test functions in 33 mock-shaped test files need edits [B2-C10].

**What cannot carry over:**
- **temperature=0 determinism.** Non-default sampling returns 400 on Opus 5/5.5 *and* Sonnet 5; this is documented, not inferred [B2-C7]. The T=0 arm was the measured win: 18/18 variance ids recovered, on gpt-4o [B2-C11].
- **Thinking must be disabled explicitly** on Opus 5 / Sonnet 5. Opus 5.5 cannot turn it off [B2-C7].
- **Tokenizer.** Claude 4.7+ models produce "approximately 30% more tokens" [B2-C3].

**Caching minimums.** 512 tokens on Opus 5 and 5.5, 1,024 on Sonnet 5, 4,096 on Haiku 4.5 [B2-C9 refuted → corrected]. The 5.5k+ verdict prompt clears all of them.

**Cost per cold compare, modelled:**
- Sonnet 5 for every role: about $0.08–0.13.
- Haiku 4.5 standard + Sonnet 5 verdict: about $0.05–0.07.

Both are modelled until re-counted with `count_tokens` [B2-C13 corrected].

**Calendar.** 5–8 working days nominal, 1.5–2 weeks realistic on this box, plus 4 eval runs (bias45 with a Claude arm ×2, smoke20, the 360-query corpus at about $30–50, and an Arabic native review).

**When it makes sense.** After launch, as a failover merged dark with the default `LLM_PROVIDER=openai`. It moves the out-of-credits outage class but does not remove it, because the Start-tier spend cap fails the same way [B2-C5].

---

## 5. Recommendation and follow-up to file

**Decision.**
1. Option A today: top up **$100** (minimum $50), enable auto-recharge, set alerts rather than hard caps, and read Settings → Limits.
2. Apply `OPENAI_MAX_RETRIES=1` and `OPENAI_FALLBACK_MAX_RETRIES=0`, then restart.
3. Verify with the section 3.5 gate, including `comparison.error` absent in both en and ar.
4. Canary `ENABLE_FULL_STREAM_DEADLINE`. Turn the breaker on only at Tier ≥ 2.
5. Then run the Arabic walkthrough and the device demo, and submit.

Do not switch provider before App Review.

**Separate launch blockers that no LLM choice fixes** (pitch-prep memory):
- A production/TestFlight iOS build has never been made.
- The Apple team is Husain's individual account.
- `qaren.app` returns 522.

**Follow-up unit to file (post-launch).** *"LLM provider failover: native Anthropic adapter behind `LLM_PROVIDER` (default `openai`)."* Acceptance:
- The `anthropic.AsyncAnthropic` adapter hoists the system prompt, skips thinking blocks, sets thinking disabled on Opus 5 / Sonnet 5, and remaps usage fields.
- 7 `output_config.format` schemas.
- A moderation ruling: keep OpenAI `omni-moderation-latest` (free) or use a Claude classifier.
- `cache_control` on the static verdict prefix.
- Per-model cost rates, replacing the hardcoded gpt-4o-mini rates.
- Mock rewrites across the 33 test files.
- Dark merge after adversary review.
- Re-baseline before any flip: bias45 ×2, smoke20, the 360-query corpus, Arabic native review.
- Pin `anthropic` and measure retry and exception behaviour on the *pinned* version (the openai lock is 3.3.1 while 2.21.0 is installed locally [A-C20, R-C11]).

**Small companion issues surfaced here** (each an independent fix):
- (a) `url_extraction_service.get_client` ignores `OPENAI_MAX_RETRIES` [A-C11].
- (b) No `LLM_UNAVAILABLE` client copy; outages show "try with brand or model" [A-C14].
  **SESSION 69 CORRECTION (2026-09-29):** FIXED: PR #258, `home.errors.engineUnavailable.*`.
- (c) Remove the key-suffix INFO log at `extraction_service.py:66` [A-C22].
  **SESSION 69 CORRECTION (2026-09-29):** FIXED: PR #252, main d6e613a3, deployed.
- (d) `bundle_d_prod_smoke.py` should assert an uncached real verdict and stop creating prod users [A-C17].
- (e) The PDPL opt-out routing is dead code; decide whether to implement it or fix the disclosure wording [A-C21].
- (f) `DAILY_4O_CAP` silent downgrade: log it and size it for 200/day [R-C14].
  **SESSION 69 CORRECTION (2026-09-29):** filed: (a) #265, (d) #267, (e) #266, (f) #268.

---

## 6. Claims table

Prefixes: **A** = Option A analysis, **B1** = compat endpoint, **B2** = native SDK, **R** = risk-first lens, **COST** = cost model. Status: confirmed / corrected (confirmed with a material fix) / refuted (the corrected text is what this memo uses).

| id | claim (as used in this memo) | status | source |
|---|---|---|---|
| A-C1 | 429 `credit_balance_exhausted` = "no prepaid credits remaining"; fix "Add credits" at settings/organization/billing; retries won't restore access | confirmed | developers.openai.com/api/docs/guides/error-codes, fetched 2026-09-29 |
| A-C2 | Org spend, project spend and org usage limits are separate 429s; org limits at settings/organization/limits; **project** spend limit in the project's own settings | corrected | same page, 2026-09-29 |
| A-C3 | gpt-4o $2.50/$1.25/$10.00; gpt-4o-mini $0.15/$0.075/$0.60 per 1M; omni-moderation-latest Free (Standard tier) | confirmed | developers.openai.com/api/docs/pricing, 2026-09-29 |
| A-C4 | Tiers: T1 $5 paid/$100 mo; T2 $50/$500; T3 $100/$1,000; T4 $250/$5,000; T5 $1,000/$200,000; automatic graduation; no waiting period listed | confirmed | developers.openai.com/api/docs/guides/rate-limits, 2026-09-29 |
| A-C5 | gpt-4o T1 500/30k, T2 5k/450k, T3 5k/800k, T4 10k/2M, T5 10k/30M (RPM/TPM) | confirmed | developers.openai.com/api/docs/models/gpt-4o, 2026-09-29 |
| A-C6 | gpt-4o-mini T1 500 RPM/200k TPM **+ 10,000 RPD**; T2 5k/2M; T3 5k/4M; T4 10k/10M; T5 30k/150M | confirmed | developers.openai.com/api/docs/models/gpt-4o-mini, 2026-09-29 |
| A-C7 | Auto-recharge fields, minimums, activation delay and expiry unfetched (help.openai.com 403); search snippet says 1-year expiry and $5 minimum (unverified) | confirmed | WebFetch 403 2026-09-29 |
| A-C8 | Retry settings 1/0 give 3 attempts (from 6); tier check is a hard gate. Per-verdict TPM is max(max_tokens, est. tokens) ≈ 5.5–5.9k, so ~5.0–5.5/min at T1 (4.4–4.6 is a conservative lower bound) | refuted | runbook §1-3; rate-limits guide 2026-09-29 |
| A-C9 | `verdict_chain_max_attempts` = (1+max)+(1+fallback); fallback inherits; defaults give 6; setting only MAX=1 gives 4 | confirmed | app/services/model_config.py:169-205 |
| A-C10 | Retry count read only at client construction (module client, `_client_cache`, `_client`); only the verdict fallback reads per call, so a restart is required | confirmed | openai_service.py:34-79; extraction_service.py:58-77, 2675-2678 |
| A-C11 | `url_extraction_service.get_client` has no max_retries and ignores OPENAI_MAX_RETRIES | confirmed | url_extraction_service.py:29-37 |
| A-C12 | ENABLE_LLM_PREFLIGHT_BREAKER read per call, default OFF; OFF = bare create | confirmed | api_budget_service.py:709-714, 951-967 |
| A-C13 | Breaker: 3 consecutive transient failures, 600 s recovery, 1 half-open probe; 429/5xx/connection/timeout count | confirmed | api_budget_service.py:272-274, 595-601, 904-924, 980-995 |
| A-C14 | Short-circuit gives success:false, `LLM_UNAVAILABLE`, 503; the app does **not** show the English string: text/URL show "Sharper match coming up — try with brand or model.", camera treats it as a timeout | refuted | structured_comparison_service.py:1713-1748, 3585-3603; text_routes.py:399; SmartCompareApp errorCopy.ts, api.ts:1011-1015, failureClassification.ts:57 |
| A-C15 | Preflight refuses only while the breaker is OPEN and inside cooldown; caps waste after a trip | confirmed | CLAUDE.md:588; api_budget_service |
| A-C16 | FULL_STREAM_DEADLINE is "a hard pairing with OpenAI re-funding"; ~6.5 min tail when OFF (modelled); cap is `STREAM_HARD_CAP_SECONDS` default **25 s** over the whole stream and can cut valid verdicts to PARTIAL, so canary it | corrected | runbook §4; structured_comparison_service.py:1636-1656 |
| A-C17 | Smoke script registers a prod user every run; only compare probe is cached `q=iPhone 15 vs Samsung Galaxy S24&region=bahrain&nocache=false`, key-presence check | corrected | scripts/bundle_d_prod_smoke.py:58, 161-162, 293-308, 450-468 |
| A-C18 | `/text/compare` and `/compare/stream` take q or product_a+b, region, nocache, lang (+specs, reviews, pros_cons, selected_category); `/image/identify` 1–4 images | confirmed | text_routes.py:642-656, 825-839; image_routes.py:144-197 |
| A-C19 | Verdict failure gives HTTP 200 success:true with `comparison.error`, template reason, blank tradeoff; `/url/compare` returns success:false `LLM_UNAVAILABLE` | corrected | extraction_service.py:2754-2756; response_builder.py:1892, 2219; url_extraction_service.py:657-666 |
| A-C20 | Lock pins openai==3.3.1, sentry-sdk==2.68.1 | confirmed | requirements.txt:97, 142 |
| A-C21 | `select_client_for_user` has 0 callers; all traffic on OPENAI_API_KEY ("data-sharing project"); opt-out has no effect | confirmed | openai_service.py:48-90; repo grep |
| A-C22 | Key's last 10 chars logged at INFO on first build (line **66**) | corrected | extraction_service.py:65-66 @ eed4ee10 |
| A-C23 | Cold ≈ $0.017–0.040 clean first attempt; $50 ≈ 1,250–3,000 cold compares (modelled) | confirmed | arithmetic on A-C3 × runbook |
| A-C24 | T2 ≈ 66–69/min, T1 ≈ 4.4–4.6/min under the prompt+max_tokens premise; ≈ 76–82 / 5.0–5.5 under the vendor formula | corrected | A-C5 × A-C8 |
| B1-C1 | Compat layer "not considered a long-term or production-ready solution" | confirmed | platform.claude.com/docs/en/api/openai-sdk, 2026-09-29 |
| B1-C2 | Base URL `https://api.anthropic.com/v1/`, Claude key, Claude model names; multi-workspace keys need `anthropic-workspace-id` (repo cannot send it) | confirmed | same page |
| B1-C3 | `response_format` Ignored; seed etc. Ignored; n=1; temperature 0–1; max_tokens/stream supported | confirmed | same page |
| B1-C4 | image_url `url` Fully supported, `detail` Ignored; system messages hoisted and concatenated | confirmed | same page |
| B1-C5 | Prompt caching not supported; *_tokens_details always empty | confirmed | same page |
| B1-C6 | Rate-limit headers supported; error messages not equivalent; /v1/messages limits; no moderations endpoint documented | confirmed | same page |
| B1-C7 | Non-default temperature returns 400 on Opus 5.5/5/4.8/4.7, Sonnet 5.5/5 (+Fable/Mythos); Haiku 4.5 accepts T=0 with thinking off | confirmed | platform.claude.com/.../thinking, 2026-09-29 |
| B1-C8 | Thinking off by default on 4.x incl. Haiku 4.5; on by default on Claude 5 (Opus 5.5/Fable always on); counts toward max_tokens | confirmed | thinking-troubleshooting page, 2026-09-29 |
| B1-C9 | All 15 chat sites send a temperature; stripped only for `^gpt-5` | confirmed | model_config.py:61-123; call sites |
| B1-C10 | 4 sites `json.loads` raw content; verdict/extraction sites extract the fenced body (fail only on prose before the fence or a non-lowercase tag) | refuted | openai_service.py 340/415/477; verdict_critique_service.py 191; extraction_service.py 2698-2703 |
| B1-C11 | Fallback fires only if verdict≠standard model **and** error text has 429/rate/quota; otherwise error dict (outer catch L2753-2755) | corrected | extraction_service.py:2652-2690, 2753-2755 |
| B1-C12 | Model ids; Haiku 4.5 retire "Not sooner than October 15, 2026"; Sonnet 4.6 Legacy, not before 2027-02-17 | confirmed | platform.claude.com/docs/en/models/*, 2026-09-29 |
| B1-C13 | Haiku 4.5 $1/$5; Sonnet 4.6 $3/$15; Sonnet 5.5 & 5 $2/$10; Opus 5.5 $4/$20; Opus 5 $5/$25 | confirmed | platform.claude.com/docs/en/about-claude/pricing, 2026-09-29 |
| B1-C14 | OpenAI Standard prices as A-C3 | confirmed | developers.openai.com/api/docs/pricing, 2026-09-29 |
| B1-C15 | Start: Haiku 4.5 / Sonnet 4.x 1,000 RPM / 2M ITPM / 400k OTPM; $500/mo cap; Evaluation tier; spend-cap 429 has no retry-after | confirmed | platform.claude.com/docs/en/api/rate-limits, 2026-09-29 |
| B1-C16 | 10 MB base64 per image, 8000×8000, JPEG/PNG/GIF/WebP; 32 MB request, 413 | confirmed | vision + errors pages, 2026-09-29 |
| B1-C17 | Server accepts 1–4 images ≤10 MiB raw, no resize, data-URI with detail auto | confirmed | image_routes.py 116-220; openai_service.py 121-213 |
| B1-C18 | 400 (incl. user-set spend limit), 402 billing, 429 (incl. tier cap), 529; credit-exhaustion code not stated | confirmed | errors + rate-limits pages, 2026-09-29 |
| B1-C19 | Base-URL validator accepts Anthropic URL; SCOPE note's "hardcoded at ~12 sites" is stale (model_config maps roles); moderation fails open | corrected | llm_provider.py; content_safety_service.py ~247-262 |
| B1-C20 | No model-id literals outside `_ROLE_DEFAULTS`; 5 roles env-overridable | confirmed | git grep app/*.py @ eed4ee10 |
| B1-C21 | 4o daily counter counts whatever `OPENAI_MODEL_VERDICT` is; the structured_comparison path (:905) never records usage | corrected | model_router_service.py:37-76; extraction_service.py:2520, 2695 |
| B1-C22 | Claude (Haiku 4.5 + Sonnet 5) cold ≈ $0.040–0.073 vs OpenAI $0.022–0.031, ≈ 1.9–2.4× (outer 1.3–3.4×), modelled | corrected | B1-C13/C14 × runbook |
| B2-C1 | Sonnet 5 $2 / $2.50 5m write / $4 1h / $0.20 hit / $10; $2/$10 now standard, $3/$15 rise cancelled | confirmed | pricing page, 2026-09-29 |
| B2-C2 | Opus 5 $5/$6.25/$0.50/$25; Opus 5.5 $4/$5/$0.20/$20 (0.05× hit); Haiku 4.5 $1/$1.25/$0.10/$5 | confirmed | pricing page, 2026-09-29 |
| B2-C3 | Claude 4.7+ tokenizer ≈ 30% more tokens (workload-dependent); Haiku 4.5 on the previous tokenizer | confirmed | pricing page, 2026-09-29 |
| B2-C4 | OpenAI Standard prices as A-C3 | confirmed | developers.openai.com/api/docs/pricing, 2026-09-29 |
| B2-C5 | Start Sonnet 5 / Opus 5 each 1,000/2M/400k; $500 cap; `enforced_spend_limit_reached` 429, no retry-after; Evaluation tier; cache reads excluded from ITPM | confirmed | rate-limits page, 2026-09-29 |
| B2-C6 | `output_config.format` json_schema on opus-5 / sonnet-5 / haiku-4-5; no recursive/numeric/length constraints; grammar cached 24 h from last use | confirmed | structured-outputs page, 2026-09-29 |
| B2-C7 | Non-default sampling returns 400 on Opus 4.7+ incl. 5/5.5 **and Sonnet 5 (documented)**; Opus 5 / Sonnet 5 accept thinking disabled, Opus 5.5 rejects it; prefill rejected | corrected | opus-5-5 migration guide, 2026-09-29 |
| B2-C8 | Compat layer not production-ready; ignores response_format / detail; no caching; Claude 5 thinking on by default | confirmed | openai-sdk page, 2026-09-29 |
| B2-C9 | Min cacheable: Opus 5.5 **512**, Opus 5 **512**, Sonnet 5 1,024, Haiku 4.5 4,096; order tools → system → messages | refuted | prompt-caching page, 2026-09-29 |
| B2-C10 | 33 mock-shaped test files / 838 test fns; 141 chat.completions refs in 27 files; 4 app files import openai; choices / any-marker counts approximate | corrected | git grep @ eed4ee10 |
| B2-C11 | T=0 arm recovered 18/18 completed variance ids at the same cost and latency; control 0.444 on bias45; all arms OpenAI | confirmed | docs/plans/2026-06-12-s2-shadow-results.md |
| B2-C12 | Runbook lines 35-37 call cold 19–25k mini + ~4.5k verdict and warm 5.2k "estimates"; the 5,498–5,942 verdict figure is a later offline token count (line 47); max_tokens now at extraction_service.py:2640/2685 | refuted | runbook lines 35-47; extraction_service.py |
| B2-C13 | Cold: OpenAI $0.024–0.030; Sonnet 5 all ≈ $0.08–0.13; + Opus 5 verdict ≈ $0.10–0.175; Haiku + Sonnet 5 ≈ $0.05–0.07; warm undefined | corrected | arithmetic on fetched prices × runbook |
| B2-C14 | No explicit OpenAIIntegration listed, but sentry-sdk auto-enables it (and AnthropicIntegration) | corrected | sentry_service.py:290-311; sentry_sdk integrations list (2.54.0 local) |
| R-C1 | OpenAI Standard prices as A-C3 | confirmed | pricing page, 2026-09-29 |
| R-C2 | Tier qualifications as A-C4 | confirmed | rate-limits guide, 2026-09-29 |
| R-C3 | "Don't retry quota, billing, or other errors that require you to take action." | confirmed | rate-limits guide, 2026-09-29 |
| R-C4 | gpt-4o T1–T3 limits as A-C5 | confirmed | gpt-4o model page, 2026-09-29 |
| R-C5 | gpt-4o-mini T1 500/10k RPD/200k; T2 5k/2M | confirmed | gpt-4o-mini model page, 2026-09-29 |
| R-C6 | `credit_balance_exhausted` is distinct from rate-limit 429s; `error.type` can still be `insufficient_quota` | confirmed | error-codes page, 2026-09-29 |
| R-C7 | Compat layer: not production-ready; response_format ignored; temp 0–1; Claude 5 thinking on; no moderations; no caching | confirmed | openai-sdk page, 2026-09-29 |
| R-C8 | Anthropic Start Haiku 4.5 / Sonnet 5 1,000/2M/400k; Evaluation tier; spend-cap 429 no retry-after | confirmed | rate-limits page, 2026-09-29 |
| R-C9 | Anthropic prices as B1-C13; ~30% tokenizer on 4.7+ (not Haiku 4.5) | confirmed | pricing page, 2026-09-29 |
| R-C10 | openai.com/api/pricing returned 403 (unfetched); prices from developers.openai.com | confirmed | WebFetch 2026-09-29 |
| R-C11 | openai 2.21.0 (local) retries any 429 unless `x-should-retry:false`; pinned 3.3.1 behaviour unmeasured | confirmed | openai/_base_client.py:773-806; requirements.txt:97 |
| R-C12 | Warmer runs a full `compare_from_text(nocache=True)` per query (≤25/run, Serper-capped), fail-closed; CLAUDE.md records `false` and 187155ed1 (documented, not live-checked) | corrected | scripts/cron_warm_price_cache.py:98-102, 218-271; CLAUDE.md:331, 580 |
| R-C13 | ENABLE_EVAL_CRON / ENABLE_FEWSHOT_ROTATION fail-closed; nightly "~$2/night" is an unmeasured docstring estimate; not registered as crons | confirmed | cron_eval_nightly.py:25, 54; cron_few_shot_rotation.py:33, 86 |
| R-C14 | `DAILY_4O_CAP` 1,000,000 × 0.80: verdict silently routes to mini at 800k tokens/UTC day; Redis-down reads 0 | confirmed | model_router_service.py:35-93 |
| R-C15 | json_object at 6 fixed sites + extraction_service.py:1781 only when ENABLE_PRICE_FALLBACK_MAY_DECLINE is on; parse at 339-340; targeted and synthesized specs return `{}` on any exception | corrected | openai_service.py 334-422; extraction_service.py; verdict_critique_service.py:183 |
| R-C16 | No model-id literals outside model_config; hardcoded gpt-4o-mini rates at openai_service.py:254-258 skew cost reporting | confirmed | git grep @ eed4ee10 |
| R-C17 | Moderation is OpenAI-specific and fails open; a swap loses L3 and L4 | confirmed | llm_provider.py:56-59; content_safety_service.py |
| R-C18 | Verdict 5,498–5,942 + max_tokens 1000; vendor formula gives ~5.0–5.5/min at T1 (runbook premise ~4.3–4.6); chain = 6 when env unset (prod not checked); tier `_unverified_`, hard gate | refuted | runbook; rate-limits guide + gpt-4o page 2026-09-29; model_config.py |
| R-C19 | Cold OpenAI ≈ $0.02–0.03, verdict ~70–85%; derived | corrected | arithmetic on R-C1 × runbook |
| R-C20 | main = eed4ee10 (merge of #250) | confirmed | git log -1 main |
| COST-cold | Cold $0.023–0.031, warm **$0.019–0.025**, blended planning $0.044; no comparison-level verdict cache; Claude cold ≈ $0.07 vs ≈ $0.03 | corrected | pricing pages 2026-09-29; cache_service.py:769-775 (no callers) |
| COST-topup | $100 recommended (≈ $76 planned + 30%, reaches T3 threshold); $50 = T2, covers ≈ 18 days at 50/day; T1 cap at 200/day stops ≈ day 17–23 nominal / 11–12 planning; auto-recharge + alerts | corrected | rate-limits guide + model pages 2026-09-29; arithmetic |
