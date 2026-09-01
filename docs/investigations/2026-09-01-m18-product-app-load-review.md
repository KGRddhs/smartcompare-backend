# M18 — Product-output, app, mobile and load/scale review (2026-09-01)

**Base:** `main 593ec1e` (deployed, `/health` 200, `/openapi.json` 404). Working tree clean.
**Method:** 4 parallel ultracode workflows (Fable finders → refute-by-default verifiers), plus an Opus
gap-closure run for the 12 agents killed by a model limit mid-run. 19 find lanes, 19 verify lanes,
2 synthesis agents, 1 completeness critic. **207 findings filed → 175 survived verification → 0 P0
(code) / 28 P1 / 78 P2 / 69 P3.** ~15% were refuted or downgraded by the adversarial pass.
Machine-readable set: `2026-09-01-m18-verified.json` (every row carries `evidence`, `fix`, and the
verifier's `verify_reason`).

**Deliberately NOT re-reviewed:** the M13 review (`2026-08-31-m13-full-review.md`, 131 findings) and
its 4 fix waves. Every lane deduped against it; rows that merely re-filed an M13-NN finding were
refuted. This review covers what M13 explicitly scoped out — **product-OUTPUT quality** (prompts, LLM
answer correctness, scoring rubric, verdict text), the **DB**, **cron/admin/landing**, the **mobile
app**, **load/scale**, and **defects introduced by the four fix waves themselves**.

**Spend constraints honoured:** OpenAI is `429 credit_balance_exhausted` (re-confirmed live), so no
live compares were run — output quality was scored from recorded outputs, committed fixtures, the
offline `_proof` corpus and static analysis, and every such claim is labelled. No Serper / Firecrawl /
Scrape.do calls. **No load test was run**; the load answer is architecture + measured baseline, and the
load-test plan in §3 stays parked pending Ahmed's explicit GO.

---

## §0 — STOP THE LINE: two live production misconfigurations

These are not code defects. They are Railway environment state, verified first-hand this session with
`railway variables`, and they invert the product's spend controls. **Neither is in CLAUDE.md.**

### M18-00A — `web` allows exactly ONE Serper call, ever, then goes permanently dark (P0, live)

`SERPER_LIFETIME_LIMIT=1` is set on the prod `web` service.

The knob's own contract (`app/services/api_budget_service.py:88-98,170-195`): unset = gate **inert**
(metered, never blocked); `0` = explicit off switch; **any positive value arms the gate at that
number**. `_serper_gate_engaged()` returns true for `1`, so `serper_gate_allows()` delegates to
`has_budget("serper")` with `limit=1`. The live counter `budget:serper:lifetime` is currently **absent**
(read directly from prod Upstash — same instance as local `.env`, host prefix verified identical), so
the *first* live call is admitted; the moment usage is recorded, `remaining = 1 - used <= 0` and
**all six Serper entry points go dark app-wide** — price, specs, reviews, images, the 4-way discovery
fan-out — plus the warmer. A lifetime key has no TTL, so it never recovers on its own.

This is exactly the "scheduled outage is not a budget control" failure the `#60` implementation notes
say they refused to ship — reintroduced through configuration. The degradation is *silent and benign-
shaped*: a budget-out returns the same empty result as a missing key, so `/health` stays 200, no error
is raised, and output quietly collapses to estimates.

**Why it is urgent now:** the moment OpenAI credits land and step-1 canary compares run, Serper dies
after the first call and every canary reading is garbage — and it will look like a code regression in
the fix waves. **Fix before any canary:** set `SERPER_LIFETIME_LIMIT` to the key's real ceiling, or `0`
to disable the gate. If the `1` was a deliberate spend freeze during the OpenAI outage, `0` is the
documented way to express that, and it must be recorded in CLAUDE.md.

### M18-00B — the mirror image: unbounded spend on the cron that actually burns credits (P1, live)

The separate `price-warmer` Railway service has **`ENABLE_PRICE_CACHE_WARMER=true`** — CLAUDE.md
documents this flag as **OFF** — and has **no `SERPER_LIFETIME_LIMIT` at all**, so its gate is inert
and its Serper spend is unbounded. The warmer costs ~10-30 credits per query.

So the configuration is precisely inverted: **spend is bounded to ~zero where users are served, and
unbounded where a cron spends unattended.** The Railway lane also found the warmer re-triggering on
pushes to `main` (20 deploys in 51h), which is a spend path nobody is watching.

---

## §1 — The four answers

### Can it handle a huge load of people at the same time? **No — not remotely, and the reason is a one-line config bug, not the architecture.**

At today's defaults the product is a **~10-compares-per-minute, ~10-30-simultaneously-active-user
system for the entire deployment** — not per user. A "huge load" is 2-4 orders of magnitude past it.

What breaks, in order:

1. **Shared-bucket 429s at 10 compares/min, deployment-wide.** `key_func` falls through to
   `get_remote_address` (`rate_limiter.py:52-59`) with `ENABLE_PROXY_AWARE_RATELIMIT` unset, and the
   start command is bare `uvicorn app.main:app` (`railway.json:7`) with **no `--proxy-headers`** — so
   uvicorn's default `forwarded_allow_ips=127.0.0.1` excludes Railway's proxy peer and
   `request.client.host` is the *shared edge-proxy IP*. Every decorated limit is one global bucket.
   The 11th compare in any minute, from anyone, gets 429. Worse on auth: **register 3/min, login 5/min,
   account-deletion 1/min — all totals across all users.** One script at 1/min denies account deletion
   (an App Store requirement) to everybody. This is also a near-free per-route DoS lever.
2. **The single event loop** (1 process, 1 worker — confirmed from the start command and the
   `Started server process [1]` log). Every hot-path Supabase `.execute()` and every Upstash command
   is a blocking round trip inline: a warm authed compare blocks the loop ~2.2-2.4s, a cold one ~6-7s,
   an app-open ~1.5-4s. Ceiling ~0.15-0.5 cold compares/s and ~0.4-1.0 app-opens/s, with a quality
   cliff at **3-4 concurrent cold compares** where wall-clock deadlines start eating each other and
   partial/insufficient-data rates spike while `/health` still looks perfect.
3. **OpenAI Tier-1 TPM** once credits return: gpt-4o verdict 30K TPM ÷ 4.5K = **6.6 verdicts/min**;
   mini 200K ÷ 20K = **10 cold compares/min**. `model_router` only watches a *daily* token counter, so
   it is blind to TPM, and a 429 storm triples request volume into a default-unbounded streaming tail.
4. **The 40-thread executor** — 2 cold fan-outs fit, the 3rd queues, and queued adapters burn their
   whole timeout in the queue and return `None`, so **price capture collapses silently** with zero errors.
5. **Upstash command budget** — 40-60 commands per cold compare. At 1000 concurrent users that is
   ~500K commands/hour, an entire free-tier month in one hour. When the quota dies, caching, the
   freemium gate, the API spend gates and token revocation **all fail open simultaneously** — the
   spend meters disable exactly when spend amplifies.
6. **RAM last**, 1-2 orders of magnitude behind (idle RSS measured 0.132GB, CPU 0.18%). The plan's RAM
   ceiling is not exposed by any read-only Railway tool, so no absolute headroom claim is made.

**The interaction nobody had written down, and it dictates fix order:** the mis-keyed rate limiter is
currently the thing *protecting* the event loop — 10 compares/min × a 30s cap bounds concurrent cold
compares to ~5. **Land the offloads first, raise the limits second.** Fixing the rate-limit key before
the event-loop offloads removes the accidental guard and converts a clean 429 into a whole-deployment
stall.

Measured vs modelled, honestly: the entire code/config inventory, Railway variable state, idle RSS/CPU,
1 replica, and current-deployment edge latency (p50 8ms / p95 35ms on the no-I/O handler at effectively
zero traffic) are **measured**. Every concurrency number above is **modelled**. The largest uncertainty
is Railway→Upstash RTT, which has never been measured — the "163ms" in the code comments is a dev-box
number. 7-day percentiles are unobtainable: Railway retains logs per deployment and 19 prior
deployments are already removed.

### Is the product's output any good? **The engine is well-built; the rubric it scores with is not.**

15 of the 28 P1s are product-output. The pattern is that deterministic scoring and the LLM prose have
drifted apart, and the surfaces that should catch that are dead:

- **The winner card can name and praise the losing product.** `response_builder.py:1131-1147` overrides
  `winner_index` with the deterministic winner, but `:1384-1429` ships GPT's own `winner_declaration`
  and name beside it, and `:1716` leaves GPT's `comparison.winner_index` untouched. The app reads
  `overview.winner.name` for the headline and the share message (`ResultsScreen.tsx:422-431`), so a
  torn card reaches the user and the share text. No test asserts the two agree (PO-recorded-01).
- **Spec scoring sums raw unit magnitudes**, so battery *notation* rather than product quality decides
  electronics winners (PO-rubric-01), and the `CATEGORY_MIN_COVERAGE` penalty is inverted in effect —
  **a 1-field product outscores a fully-specified one** (PO-rubric-02).
- **`MISSING_SCORE=50` makes no-data beat bad-data**: an unrated product beats an identical 2.0-star
  product (PO-rubric-03).
- **`value_badge` is a constant `fair_price` for 7 of 9 categories** because the badge site reads a
  dimension key those categories don't have (PO-rubric-04), and the behavioural ±10% layer is
  dead-keyed for 8 of 9 while `scoring_method` still reports `behavioral` (PO-rubric-05).
- **Fact-checking is largely ceremonial.** Price cross-validation is currency-blind, so it *verifies*
  the 9.8× wrong-currency class the W2 wave exists to fix (PO-fact-check-01); spec-citation
  verification is **dead on every cache hit** because cached specs lose `_search_snippets`
  (PO-fact-check-02); the confidence pills users act on ignore `fact_check` entirely and inflate, and
  the one sheet where a user could inspect the evidence crashes (PO-fact-check-04/05).
- **`page_scrape_jsonld` — the flagship genuine-Bahrain provenance — is missing from `_PRICE_TRUST_SET`**
  (`scoring_service.py:615-623`), so the most trustworthy price is scored as estimate-grade
  (PO-fact-check-06; independently re-derived by me).
- **The prompts push confidence the data can't support**: "Be DECISIVE" plus trust rules that mandate
  quantified claims, with a never-empty-cons rule that converts pipeline data gaps into product
  criticism (PO-prompts-02/03, PO-verdict-text-08).
- **Arabic users get English.** An `ar` request receives English verdict, review and overview text
  end-to-end — there is no AR generation path (PO-verdict-text-02).

Calibration on the recorded evidence: the Opus verifier **refuted or downgraded 7 of 13** recorded-output
findings because they attributed mid-June recorded artifacts to current code — several had already been
fixed (the pended-price verdict leak, derived-rating suppression, score-internal scrubbing of pros/cons).
That is the review working as intended. But it also exposes the real gap: **only 26 recorded comparisons
exist and all predate 2026-06-21**, and the deterministic judge has measured production exactly three
times, last on 2026-06-17 — so **every M13 fix wave is unscored** (PO-recorded-12).

### Is the code sound after four fix waves? **Yes, with two live interaction bugs the waves created.**

- **W3 × W3: the drain defeats the refund.** M13-35's drain-not-abandon means a pre-verdict disconnect
  no longer cancels, so `complete_response` is captured, the `finally` takes the metering branch, and
  M13-37's refund (which requires `complete_response` absent) never fires. A network blip at second 2
  of a 30s stream **burns a free credit and runs the full unbounded OpenAI tail**. Pre-wave, a dropped
  connection was free. CLAUDE.md's claim that the else-refund covers "a pre-verdict cancel" is wrong for
  the dominant real-disconnect path (CD-interactions-01, verified down to the pinned starlette/uvicorn
  ASGI spec version).
- **W2: the region-currency guard doesn't cover what it claims.** `ENABLE_REGION_CURRENCY_GUARD` pends
  only at the final projection, but the SSE `prices` event builds its own block that skips the guard,
  and `compute_scores` runs *before* it on both paths — so **the winner and the verdict are still
  decided by the mismatched price** while the final payload shows "pending". A canary that inspects
  final payloads sees pends and wrongly concludes the guard works (CD-interactions-02). This is a hard
  precondition on the runbook's region-guard flip.

Plus: three RLS holes M13 never looked at (`admin_audit_log` INSERT `WITH CHECK (true)`; the three L2
product-cache tables open to anon writes = a **cache-poisoning path into user-served prices**; migration
013's cohort views bypassing RLS as definer views) — all capped at P2 because the app ships no Supabase
client and the anon key isn't in the bundle. And **the M13-29 RLS migration never landed**: nothing after
`032` touches feedback/events policies, so the forgery gap is still open, narrowed by W1's route-layer
UUID validation.

**CI truth:** the 16 red backend tests are **not** wave regressions. 11 are pre-existing baseline rows;
the headline scare — `test_m13_03_paid_work_gating` — is **definitively not a regression**, it is
dependency drift (the dev machine runs fastapi 0.115.0 against a lock pinning 0.141.1, whose lazy
`include_router` breaks route-table introspection). The more serious finding is structural: **branch
protection requires only the three jobs that structurally cannot fail**, and `backend-lint` /
`dependency-audit` / `frontend-typecheck` hide `exit 1` behind `continue-on-error` (CD-ci-truth-01/04).
Meanwhile the new `frontend-tests` job is **ratchet-ready now**: jest is 2103/2103 green and `tsc` is 0
— only the 8 `i18next/no-literal-string` errors block making it required.

### Is the mobile app in shape? **It's the healthiest codebase here and the most misconfigured deployment.**

Measured: `npx tsc --noEmit` **exit 0**, jest **2103 passed / 0 failed** (220 suites), CI's ESLint count
reproduced exactly (151 problems, 8 errors — all hardcoded strings in Paywall/History/Loading). But:

- **SSE streaming is dead on every phone.** `streamComparison` requires `response.body`
  (`api.ts:415`); React Native's fetch doesn't provide a ReadableStream and the app ships **no
  `expo/fetch` and no polyfill** — so every text compare throws into the non-streaming fallback at
  `api.ts:509` and **runs a second full backend compare**. Users have never seen the staged reveal the
  UI was built for, and with W3's drain-not-abandon the abandoned first compare still runs to
  completion server-side. This doubles demand at exactly the 10/min ceiling (MB-perf-01, MB-flows-06;
  mechanism independently re-derived by me).
- **Phones are running a freemium gate that dead-ends paying users.** The on-device gate is still
  hardcoded `used < 3`, so premium and referral-bonus users hit a wall the backend would have allowed
  (MB-two-lever-02) — this is precisely what `eas update` fixes and it is the strongest argument for
  shipping W4 promptly. The pending OTA is **native-compatible** (zero dependency changes since the
  last build), and the delta is `270a240..593ec1e` — 55 files, +718/−4281.
- **A channel trap:** all documented installed builds follow `preview`, so an `eas update --branch
  production` would reach nobody (MB-two-lever-07).
- **Both App Store blockers are still unresolved** at main: the icons remain byte-identical to the Expo
  template, and the live legal docs still open with "DRAFT".
- Arabic plurals resolve to **English** for counts 0, 2, 3-10 and 11-99 (only `_one`/`_other` exist,
  no `Intl.PluralRules` polyfill), and directional icons are never mirrored in RTL — two flip helpers
  exist with one consumer between them (MB-i18n-rtl-01/02/03).
- **Contract breaks:** the app sends `metadata.query` where a `comparison_id` is expected, so W1's new
  UUID validation now **422-rejects every feedback submission** from the results screen
  (MB-contract-01); the share-invite flow is unreachable; the referral screens select a `response_data`
  column nothing writes.
- **Flows:** `performRefresh` reports success whenever *any* token is present regardless of what
  `refreshSession()` returned, and there is **no path back to Auth** after a session is cleared
  mid-session — the app keeps rendering Main (MB-flows-01/02).

---

## §2 — Proposed waves (findings → units, through the standing gates)

Nothing here is a direct fix. Each unit goes through TDD (red first), module-reference comm, flag-OFF
byte-identity where it touches the price path, and Fable review before commit.

| Wave | Theme | Units | Why this order |
|---|---|---|---|
| **W0 — config, no code** | §0 A+B | Set `SERPER_LIFETIME_LIMIT` to the real ceiling or `0`; bound the warmer's spend; record both in CLAUDE.md | Blocks every canary. Zero code risk. Do first. |
| **W1 — output truth** | PO-recorded-01, PO-fact-check-06/02/01, PO-rubric-01/02/03/04/05 | Reconcile the winner card to one source of truth; add `page_scrape_jsonld` to the trust set; fix the coverage-penalty inversion and the missing-data-beats-bad-data rule; make `scoring_method` honest | Highest user-visible harm; all deterministic and unit-testable offline, so no OpenAI needed |
| **W2 — wave interactions** | CD-interactions-01, CD-interactions-02, CD-wave-diffs-01/02/03 | Gate the drain on progress-already-captured; move the region guard ahead of scoring and into the SSE block; unlock the half-open breaker | Two are live credit/OpenAI leaks; the third is a hard precondition on the region-guard flip |
| **W3 — load foundations** | U1, U2, E1, E2, S1, R2 | `/home/savings` → SQL aggregate; project `/home/smart-pick`; finish the offload sweep; drop the redundant gate round trips; suppress the client double-pipeline; replace `memory://` limiter storage | **Must precede** any rate-limit fix — the mis-keyed limiter is the current guard |
| **W4 — rate-limit anchor** | R1, W2(worker), O1 | Verified per-client anchor (`--proxy-headers` + trusted-hop, not leftmost XFF); second worker as an explicit decision; fix the zero-HA restart budget | Only safe after W3 |
| **W5 — mobile** | MB-perf-01, MB-contract-01, MB-flows-01/02, MB-two-lever-07, i18n plurals/RTL | Real streaming (`expo/fetch`) or drop the SSE path; fix the feedback id; fix refresh/logout; correct the EAS channel; Arabic plurals + icon mirroring | Ship `eas update` for W4 **before** this, so testers stop hitting the `used < 3` wall |

Full unit specs (scope, files, tests, assumptions) for the load units U1/U2/E1/E2/R1/R2/S1/I1/I2/L1/T1/O1-O4
are in the capacity synthesis; they carry file:line citations and measured-vs-modelled labels.

---

## §3 — What could not be known, and what unblocks it

- **Live output quality.** OpenAI 429 means no compare ran. The judge's grading functions are
  importable and score a recorded payload offline, but the corpus is 26 rows from a mid-June engine.
  **The moment credits land — and after §0A is fixed —** re-baseline with
  `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 54b603e8-4eab-41c9-a34d-a5e391446559`
  (`--concurrency 1`, full UUID, `set -a; source .env; set +a` first). Judge the axis averages, never
  `pass_rate`.
- **Load behaviour.** No test was run and none will be without an explicit GO. The plan requires
  isolation: a separate Railway environment **with its own Upstash and Supabase**, because prod
  credentials are shared even from localhost. Staged ramp, abort criteria, and what to watch are in the
  capacity synthesis.
- **Railway plan limits** (RAM/vCPU ceiling) are not exposed by read-only tooling — read them off the
  dashboard before trusting any absolute headroom number.
- **Upstash RTT from Railway** has never been measured; every concurrency ceiling scales with it.
- Review gaps the completeness critic named for a follow-up lane: image-pipeline output quality, the
  share page, `/home/smart-pick` output, SSE partial-output quality, legacy-row rendering in History,
  and the truthfulness of the category-mismatch banner.

---

## §4 — Findings

Severity is post-verification (downgrades applied). `verify_reason` for every row is in the JSON.

### P1 (28)

| ID | Team | Finding | Location |
|---|---|---|---|
| `CD-ci-truth-01` | Code / DB / CI | Dev machine never installed the lock: fastapi 0.115.0/pytest 8.2.0 local vs fastapi 0.141.1/pytest 9.1.1 on CI and Railway prod | `requirements.txt:47` |
| `CD-ci-truth-04` | Code / DB / CI | Branch protection requires only the three jobs that structurally cannot fail on their signal; backend-tests (15,747 tests) is not a required check | `ci.yml:104` |
| `CD-interactions-01` | Code / DB / CI | W3xW3: M13-35 drain defeats M13-37 refund - pre-verdict disconnect burns a credit + full OpenAI tail | `text_routes.py:565` |
| `CD-interactions-02` | Code / DB / CI | W2: region-currency guard covers only the final projection - SSE prices event and scores/verdict still consume the unguarded price | `structured_comparison_service.py:3806` |
| `LS-capacity-math-01` | Load / scale | Deployment-wide ~10/min ceiling on every compare route: decorated 10/minute limits keyed on the shared Railway edge-proxy IP | `rate_limiter.py:97` |
| `LS-capacity-math-02` | Load / scale | Flags-off event-loop blocking bounds the whole service at ~0.15-0.5 cold compares/s and ~0.4-0.5 app-opens/s at the measured 163ms Upstash RTT | `db_offload.py:38` |
| `LS-capacity-math-03` | Load / scale | OpenAI Tier-1 TPM caps the restored product at ~6-10 compares/min, and a 429 storm triples request volume with an unbounded flags-off SSE tail | `openai_service.py:27` |
| `LS-event-loop-01` | Load / scale | /home/savings does an UNBOUNDED all-rows full_response SELECT synchronously on the event loop | `home_routes.py:152` |
| `LS-event-loop-02` | Load / scale | W3 flags-ON future still leaves ~55-60% of per-compare loop blocking inline - the offload waves cover a minority of the request path | `structured_comparison_service.py:4272` |
| `LS-railway-metrics-01` | Load / scale | Deployment-wide shared rate-limit buckets are the binding capacity ceiling: 10 compares/min TOTAL | `rate_limiter.py:59` |
| `LS-railway-metrics-02` | Load / scale | Flags-off event loop: inline sync Supabase+Upstash caps compare throughput at ~0.5-2.5/s and converts concurrency into 30s-cap timeouts | `db_offload.py:40` |
| `LS-ratelimit-01` | Load / scale | All decorated per-route limits share ONE deployment-wide bucket (key = shared Railway edge-proxy IP) — global capacity ceiling and near-free per-route DoS lever | `rate_limiter.py:59` |
| `MB-perf-01` | Mobile app | SSE streaming is dead on-device: every text compare silently runs TWO full backend comparisons back-to-back with zero progress UI | `api.ts:415` |
| `MB-two-lever-02` | Mobile app | On-phone freemium gate is still hardcoded used<3 — premium and referral-bonus users dead-end at the paywall until the OTA fires | `useComparisonCounter.ts:63` |
| `PO-fact-check-01` | Product output | Price cross-validation is currency-blind: it verifies the 9.8x wrong-currency error class and rejects correct conversions | `fact_check_service.py:156` |
| `PO-fact-check-02` | Product output | Spec-citation verification is dead on every cache-hit: cached specs lose _search_snippets so all specs grade 'unverified' - 24/24 recorded product sides show specs_verified=0 | `structured_comparison_service.py:5022` |
| `PO-fact-check-03` | Product output | Citation check cannot flag a contradiction and is trivially bypassed: unit swaps verify, contradicted numbers earn 'likely' (scored above honest 'training'), and coincidental digits in shopping titles | `fact_check_service.py:48` |
| `PO-fact-check-04` | Product output | The confidence pills users act on ignore fact_check and inflate: unverified fields count as 'citations' (specs reads strong at 0% verified) and the price pill never reads price_verified | `scoring_service.py:894` |
| `PO-fact-check-05` | Product output | The 'What we know' sheet - the only surface where a user can act on confidence evidence - crashes on live payloads: backend ships dicts, frontend maps string arrays | `ConfidenceDetailsSheet.tsx:53` |
| `PO-fact-check-06` | Product output | page_scrape_jsonld - the flagship genuine-BH provenance - is missing from _PRICE_TRUST_SET: genuine scraped BHD prices display a weak price pill and take the full estimate-grade score penalty | `scoring_service.py:615` |
| `PO-prompts-01` | Product output | Winner card can name and praise the losing product: GPT verdict prose ships unreconciled when deterministic scoring overrides winner_index | `response_builder.py:1131` |
| `PO-prompts-03` | Product output | Trust rules + category personalities mandate quantified (and compliance) claims the data cannot support, and no downstream layer verifies verdict prose numbers | `prompt_personalities.py:72` |
| `PO-recorded-01` | Product output | Torn winner card: winner name/reason keep GPT's pick while product_index is deterministic | `response_builder.py:1388` |
| `PO-rubric-01` | Product output | Spec score sums raw unit magnitudes - battery notation, not product quality, decides electronics winners | `scoring_service.py:1411` |
| `PO-rubric-02` | Product output | CATEGORY_MIN_COVERAGE penalty is inverted in effect - a 1-field product outscores a full-spec product 3.9x | `scoring_service.py:1427` |
| `PO-rubric-03` | Product output | MISSING_SCORE=50 makes no-data beat bad-data: an unrated product beats an identical 2.0-star product | `scoring_service.py:1104` |
| `PO-rubric-04` | Product output | value_badge is a constant 'fair_price' for 7 of 9 categories - the badge site reads a dim key those categories never emit, and the tier lookup key never matches | `structured_comparison_service.py:3303` |
| `PO-rubric-05` | Product output | The behavioral +/-10% layer is dead-keyed for 8 of 9 categories while scoring_method reports 'behavioral' | `behavior_service.py:12` |

### P2 (78)

| ID | Team | Finding | Location |
|---|---|---|---|
| `CD-ci-truth-02` | Code / DB / CI | FastAPI 0.141.1 lazy include_router (_IncludedRouter in app.routes) breaks all 3 route-table tests — the entire CI-vs-baseline delta, undiagnosed in #89 | `test_endpoint_shapes_vs_jsx.py:478` |
| `CD-ci-truth-03` | Code / DB / CI | DEFINITIVE: M13-03 fix did NOT regress — test_price_kpi_route_declares_admin_dependency is dependency-version-fragile and was born red on CI | `test_m13_03_paid_work_gating.py:56` |
| `CD-ci-truth-06` | Code / DB / CI | frontend-tests measured counts are in: jest 2103/0 and tsc 0 errors are ratchet-ready NOW; eslint hides 8 errors/143 warnings behind the green job | `ci.yml:235` |
| `CD-ci-truth-11` | Code / DB / CI | test_extraction_prompt_bundle_c failure is the one pre-existing row that flags a REAL product gap: inference_source='model_knowledge' leaks into the serialized API response | `test_extraction_prompt_bundle_c.py:282` |
| `CD-db-rls-02` | Code / DB / CI | admin_audit_log INSERT policy WITH CHECK (true) lets any anon-key holder forge security-audit rows | `011_security_completion_freemium.sql:46` |
| `CD-db-rls-03` | Code / DB / CI | product_specs/prices/reviews L2-cache tables have USING(true)+WITH CHECK(true) — anon cache poisoning path to users | `012_product_data_tables.sql:19` |
| `CD-db-rls-04` | Code / DB / CI | Migration 013 cohort views over users PII have no security_invoker and no REVOKE — RLS-bypassing read of aggregate demographics | `013_demographics_cohort.sql:23` |
| `CD-interactions-03` | Code / DB / CI | W3xW3: atomic freemium gate adds 4-6 blocking Upstash RTTs on the event loop, uncovered by either W3 offload flag | `usage_service.py:152` |
| `CD-interactions-04` | Code / DB / CI | W4xBackend: M13-14 gate compares LIFETIME used against MONTHLY-expiring referral bonus - referral loop progressively dead-ends and backend-allowed compares are paywalled | `useComparisonCounter.ts:63` |
| `CD-interactions-05` | Code / DB / CI | W1xW3: anonymous usage gate keeps the exact check-then-record TOCTOU that M13-37 closed for authenticated users | `usage_service.py:43` |
| `CD-interactions-06` | Code / DB / CI | W1+W3 residual: /image/identify runs a full paid compare with NO usage gate for authenticated users - the only unmetered compare surface left | `image_routes.py:89` |
| `CD-uncovered-01` | Code / DB / CI | Push crons have no overlap protection: send-then-stamp with no atomic claim double-pushes on concurrent runs and permanently drops reminders on failed sends | `cron_expire_bonuses.py:156` |
| `CD-uncovered-02` | Code / DB / CI | Arabic-locale Contact Us breaks the documented `[Bug]%` grep contract — the prefix is the LOCALIZED category label | `ContactUsScreen.tsx:62` |
| `CD-uncovered-03` | Code / DB / CI | Admin analytics endpoints run unbounded full-table scans + N+1 sequential BLOCKING Supabase calls on the event loop | `admin_routes.py:297` |
| `CD-uncovered-05` | Code / DB / CI | Force-update kill-switch is dead wiring: /app/version has ZERO client consumers, so APP_MIN_VERSION / APP_FORCE_UPDATE flips do nothing | `version_routes.py:13` |
| `CD-wave-diffs-01` | Code / DB / CI | M13-31 rewrite can lock a provider breaker in HALF_OPEN indefinitely: every gate check consumes the probe AND refreshes the 1h state TTL, but nothing guarantees the probe ever records | `api_budget_service.py:514` |
| `CD-wave-diffs-02` | Code / DB / CI | Streaming route still burns the freemium credit on cold-path timeouts: STREAM_TIMEOUT / INSUFFICIENT_DATA terminals arrive as settle_complete/complete with success:false, so the M13-35 finally meters  | `text_routes.py:576` |
| `CD-wave-diffs-03` | Code / DB / CI | M13-10 stash parity is broken against M13-09: the short-circuit seed does not apply the strict-shopping currency pend, so with ENABLE_SHOPPING_STRICT_CURRENCY ON the fairness re-select can serve the e | `structured_comparison_service.py:7397` |
| `CD-wave-diffs-05` | Code / DB / CI | ENABLE_REGION_CURRENCY_GUARD violates the pinned SIB-1 invariant: the guard pends only in build_comparison_response, so the SSE `prices` event flashes the region-mismatched price the final payload the | `response_builder.py:1252` |
| `LS-capacity-math-04` | Load / scale | ThreadPoolExecutor-40 knee: 3rd concurrent cold fan-out queues; sustained >0.6-1.4 cold compares/s silently collapses price capture | `executor.py:30` |
| `LS-capacity-math-06` | Load / scale | Drain-not-abandon retains 100% of server work on disconnect; with the client's SSE-to-REST fallback one flaky tap can cost two full paid pipelines | `text_routes.py:561` |
| `LS-event-loop-03` | Load / scale | Freemium gate burns 2 Supabase + up to 6 Redis round trips serially inline before any compare work starts | `usage_service.py:199` |
| `LS-event-loop-04` | Load / scale | Token-revocation check is a blocking Redis GET on EVERY authed request and is in neither offload set | `auth_service.py:312` |
| `LS-event-loop-06` | Load / scale | /home/smart-pick pulls 5 complete full_response payloads (~0.25-1MB) through a sync execute on the loop | `home_routes.py:550` |
| `LS-event-loop-07` | Load / scale | Nobody filed the cheapest lever: a second uvicorn worker - the deployment is pinned to 1 loop by a start-command default, not by a design constraint | `Procfile:1` |
| `LS-railway-metrics-03` | Load / scale | Zero-HA topology with a hard restart budget: 1 replica x 1 worker, ON_FAILURE max 3 retries, then permanent downtime | `railway.json:11` |
| `LS-railway-metrics-04` | Load / scale | memory:// limiter storage makes horizontal scaling change rate-limit semantics (limits multiply per replica) and wipes state every deploy | `rate_limiter.py:110` |
| `LS-ratelimit-02` | Load / scale | 21 undecorated routes are unmetered today; worst are authenticated Supabase-blocking routes that amplify into whole-deployment event-loop stalls | `main.py:137` |
| `LS-ratelimit-03` | Load / scale | slowapi memory:// storage resets every deploy/restart and is a latent multi-worker footgun | `rate_limiter.py:110` |
| `MB-contract-01` | Mobile app | FE sends metadata.query as comparison_id — M13-29 UUID validators now 422-reject every ResultsScreen event batch and every feedback submission | `ResultsScreen.tsx:331` |
| `MB-contract-02` | Mobile app | SSE 'error' event handler drops code/layer — CONTENT_UNAVAILABLE contract never fires on the streaming path and raw exception text leaks to the user | `api.ts:475` |
| `MB-contract-03` | Mobile app | Share-invite flow is unreachable: sharableComparisonId reads keys no backend payload ever carries, and api.ts discards the wrapper id it already had | `ResultsScreen.tsx:419` |
| `MB-contract-04` | Mobile app | History winner_index derives from the unreconciled GPT comparison.winner_index — History rows can name the opposite winner from the Results screen | `history_routes.py:40` |
| `MB-contract-05` | Mobile app | Referral landing + invitee quiz select a 'response_data' column that nothing writes — comparisons persist under 'full_response' | `referral_service.py:478` |
| `MB-flows-01` | Mobile app | performRefresh discards refreshSession()'s result and reports success whenever ANY token is still stored — the 401 retry replays the identical dead token | `api.ts:49` |
| `MB-flows-02` | Mobile app | No path back to Auth after a session is cleared mid-session — the app keeps rendering Main with no token | `App.tsx:233` |
| `MB-flows-03` | Mobile app | Registration that needs email confirmation reports success and then silently dead-ends on the Register screen | `RegisterScreen.tsx:208` |
| `MB-flows-04` | Mobile app | Onboarding completion persistence is fire-and-forget with no retry or local draft, so a failed save silently loses every answer and re-runs all 17 steps on the next launch | `NewOnboardingHost.tsx:67` |
| `MB-flows-05` | Mobile app | ResultsScreen classifies failures by HTTP status only, so an offline or 5xx failure is reported as the user's fault and offers no retry | `ResultsScreen.tsx:293` |
| `MB-flows-06` | Mobile app | Any mid-stream SSE failure silently re-runs the entire comparison as a non-streaming GET, double-metering the user's freemium quota | `api.ts:482` |
| `MB-flows-08` | Mobile app | History hero marquee taps are a silent no-op for any recent decision not in the loaded page, including one the user just deleted | `HistoryScreen.tsx:762` |
| `MB-flows-09` | Mobile app | ContactUs localizes the category prefix, so the documented '[Bug]' operator grep never matches Arabic reporters | `ContactUsScreen.tsx:62` |
| `MB-i18n-rtl-03` | Mobile app | Directional icons are never mirrored in RTL: two flip helpers exist with exactly one consumer; 14+ chevron/arrow sites render backwards for Arabic users | `rtl.ts:8` |
| `MB-perf-02` | Mobile app | Compare abort path exists but has zero callers — in-flight compare survives unmount/logout and setState fires on a dead screen | `HomeScreen.tsx:112` |
| `MB-perf-04` | Mobile app | LoadingRings reads SharedValue.value during render: rings animate only while a 60fps JS setState loop runs (2.4s), then freeze; orphaned infinite UI-thread animation continues | `LoadingRings.tsx:134` |
| `MB-perf-07` | Mobile app | HistoryScreen rows: entering-stagger tied to list index leaves scrolled-in rows blank up to ~2s and repeats on re-mount; every search keystroke re-renders all mounted rows | `HistoryScreen.tsx:571` |
| `MB-perf-08` | Mobile app | ProductImage decodes full-resolution og:image bitmaps into 64-160px tiles — no resizeMethod, no expo-image, dozens of oversized decodes per History/Home screen | `ProductImage.tsx:99` |
| `MB-security-01` | Mobile app | Sentry breadcrumb scrubbing is dead code: wrong event shape, and the unit test pins the wrong shape | `sentry.ts:100` |
| `MB-security-02` | Mobile app | No mobile parity for the backend R21 query-string PII scrub (q/query/email/search/text) or before_breadcrumb URL scrub | `sentry.ts:28` |
| `MB-security-04` | Mobile app | Certificate pin set has no RSA-chain backup (ISRG Root X1 / R-series absent) — a repeat of the documented 2026-07-06 brick is one CA profile change away | `certificatePinning.ts:42` |
| `MB-two-lever-01` | Mobile app | Phones lack all 7 Wave-4 commits: delta is 270a240..593ec1e, 55 files, +718/-4281 | `SmartCompareApp` |
| `MB-two-lever-03` | Mobile app | OTA baseline unverified: no EAS group ID was ever recorded for the 270a240 cert-pin OTA — if it never fired, EAS builds are still fully bricked | `SESSION_BUNDLES.md:646` |
| `PO-fact-check-07` | Product output | verify_price returns 'verified' from absence of evidence: no shopping items or no parseable prices yields price_verified=True with source_count=0 plus a +0.1 reliability bonus | `fact_check_service.py:141` |
| `PO-fact-check-08` | Product output | Review-sentiment check protects nothing real: numeric-only, 0.8-of-5 tolerance, and the Serper side is a review-count-weighted average over unmatched shopping items | `fact_check_service.py:127` |
| `PO-fact-check-09` | Product output | verify_review_sentiment raises TypeError on a string average_rating at an unguarded call site, failing the entire product side | `fact_check_service.py:126` |
| `PO-fact-check-10` | Product output | Bundle E Decision 7's replacement surfaces were never wired: is_data_freshness_shaky has zero production callers and per-dimension confidence never reads fact_check - the all-bad-signals state ships w | `fact_check_service.py:213` |
| `PO-fact-check-11` | Product output | 'Ratings NEVER AI-generated' has one enforcement gap: GPT-emitted source_ratings survive because the real-ratings overwrite never fires on the live path | `extraction_service.py:1669` |
| `PO-prompts-02` | Product output | Verdict stack is structurally biased toward a confident winner on thin evidence: 'Be DECISIVE' with the weird-comparison off-ramp dead in prod, and a self-critique that grades bias/grounding without e | `extraction_service.py:987` |
| `PO-prompts-04` | Product output | The <USER_INPUT> trust boundary is trivially escapable: sanitize_prompt_input never neutralizes the literal closing tag | `prompt_sanitizer.py:22` |
| `PO-prompts-05` | Product output | Serper snippet digest enters specs/price/reviews prompts OUTSIDE the untrusted region - scraped web text is implicitly trusted and a poisoned snippet caches for 7 days | `extraction_service.py:819` |
| `PO-prompts-06` | Product output | Grocery non-negotiable field 'weight' does not exist in the grocery spec schema - a perpetual paid Tier-2/Tier-3 chase for a field the extractor filter drops and the UI never renders | `extraction_service.py:346` |
| `PO-prompts-07` | Product output | Prod-default specs prompt examples teach off-schema keys ('notes', 'volume_ml') whose values the filter silently drops - then the paid refill cascade re-buys what the model already produced | `extraction_service.py:481` |
| `PO-prompts-08` | Product output | Worked examples assert full spec sheets for REAL current SKUs (iPhone 17, Galaxy S25 Ultra, Tobacco Vanille...) - prompt-baked numbers that anchor the very queries users make | `extraction_service.py:430` |
| `PO-prompts-09` | Product output | Verdict stack hardcodes Bahrain-buyer grading while the API serves six GCC regions - system-prompt authority overrides the per-request region | `extraction_service.py:992` |
| `PO-prompts-10` | Product output | PRODUCT_PARSER_PROMPT has zero rules for Arabic-script queries in a bilingual AR/EN product - search_query script is left to model whim, breaking the Latin-oriented match pipeline | `extraction_service.py:87` |
| `PO-recorded-11` | Product output | Extractor picks the 1ml sample offer over the real bottle and drops JSON-LD availability | `price_service.py:12878` |
| `PO-recorded-12` | Product output | The judge has measured prod exactly 3 times, last on 2026-06-17 — every M13 fix wave is unscored | `eval_persistence.py:83` |
| `PO-rubric-06` | Product output | Top-weighted dimension labels misdescribe what is measured: 'Presentation' is review count, 'Versatility' is fact-check verification rate | `scoring_service.py:1534` |
| `PO-rubric-07` | Product output | _normalize_price kept the undampened 70-point cliff the A1 work removed from every other dim - a 1% price gap reads as decisive | `scoring_service.py:1776` |
| `PO-rubric-08` | Product output | trust_validation never reads the verdict - fabricated GPT claims pass clean while honest split verdicts get confidence 'reduced' | `trust_validation_service.py:99` |
| `PO-rubric-09` | Product output | The runner-up card fallback can crown a NO-DATA dimension as the loser's best case | `scoring_service.py:2065` |
| `PO-verdict-text-01` | Product output | Review surface launders retailer/brand marketing copy into fabricated 'Owners say' sentiment | `review_service.py:421` |
| `PO-verdict-text-02` | Product output | Arabic requests receive English verdict/review/overview text end-to-end with no AR path or fallback marker | `text_routes.py:278` |
| `PO-verdict-text-03` | Product output | build_review_praise emits ungrammatical glue and literal '[]' husks on real highlight shapes — reproducible today on the primary review surface | `review_service.py:392` |
| `PO-verdict-text-04` | Product output | Fact-check internals leak into user-facing cons ('Price deviation of 53.9% from expected') and the score scrub provably misses them | `text_sanitize.py:7` |
| `PO-verdict-text-05` | Product output | Doubled brand in user-facing copy: '{brand} {name}' concatenated without dedup at three sites → 'TOM FORD TOM FORD OUD WOOD 100 ML' | `structured_comparison_service.py:3211` |
| `PO-verdict-text-07` | Product output | Price-pended products still get price-tier prose in value_context/best_for — the C3 fail-closed net covers only pros/cons | `response_builder.py:1360` |
| `PO-verdict-text-09` | Product output | 'weird' comparison_quality is the modal label on real traffic (14/15 recorded rows) — sparse specs alone trigger it, contradicting its own contract | `structured_comparison_service.py:791` |

### P3 (69)

| ID | Team | Finding | Location |
|---|---|---|---|
| `CD-ci-truth-07` | Code / DB / CI | frontend-typecheck's continue-on-error is justified by a stale '7 pre-existing TS errors' comment — tsc is actually green, so a required check is voluntarily blind to the next type break | `ci.yml:205` |
| `CD-ci-truth-08` | Code / DB / CI | backend-lint's hidden exit 1 is the whole-repo black drift step, and the drift ratchet is moving BACKWARD: 693 files would be reformatted vs the recorded 603/619 baseline | `ci.yml:148` |
| `CD-ci-truth-09` | Code / DB / CI | 11 of the 16 CI failures are pre-existing baseline rows, each root-caused locally: 2 diagnostic-by-choice, 2 TDD-RED-by-design, 4 stale/hermeticity test bugs, 3 fixture bugs — zero wave regressions am | `.pre_impl_failures.txt:39` |
| `CD-ci-truth-12` | Code / DB / CI | Baseline carries one order-dependent artifact: test_database_service::test_save_comparison_skips_when_not_renderable passes solo and on CI, fails only under full-suite ordering locally | `.pre_impl_failures.txt:45` |
| `CD-db-rls-05` | Code / DB / CI | Migration 024 rollback needlessly destroys legitimate 'luxury' budget preferences (data loss) | `024_pre_rollback_downgrade.sql:22` |
| `CD-db-rls-06` | Code / DB / CI | resolve_referral_code SECURITY DEFINER granted to anon returns the referrer's internal UUID, callable directly via PostgREST rpc | `014_referral_system.sql:97` |
| `CD-db-rls-07` | Code / DB / CI | Migration 022 adds CHECK constraints without DROP IF EXISTS — non-idempotent, re-apply fails | `022_referral_invites_code_redeem.sql:27` |
| `CD-interactions-07` | Code / DB / CI | W3: refund recomputes date-keyed counters at refund time - midnight/month rollover burns the old credit and mints a negative one in the new window | `usage_service.py:258` |
| `CD-interactions-08` | Code / DB / CI | W3xW3xM10: ENABLE_SYNC_DB_OFFLOAD puts per-request auth/usage DB calls in the same 40-thread pool as up-to-9s parked adapter fetches | `executor.py:30` |
| `CD-uncovered-04` | Code / DB / CI | test_cron_warm_price_cache.py import permanently mutates pytest-process env (WARMER_CONTEXT=1, off-clock timeouts) with no restore — the exact hazard test_seed_zyte_guard already fixed for zyte | `test_cron_warm_price_cache.py:7` |
| `CD-uncovered-08` | Code / DB / CI | cron_reengagement promises cursor pagination but implements a single unordered LIMIT 1000 — users beyond the first 1000 starve on every run | `cron_reengagement.py:44` |
| `CD-uncovered-06` | Code / DB / CI | Live assetlinks.json ships a literal placeholder cert fingerprint; AASA-declared paths /r/*, /c/*, /q/* have no web fallback (404) | `assetlinks.json:7` |
| `CD-uncovered-07` | Code / DB / CI | Every landing page references /favicon.png but the asset is never shipped — 8 pages × both locales 404, silenced in the nginx config | `Dockerfile:22` |
| `CD-uncovered-10` | Code / DB / CI | legal_routes hardcodes last_updated in code, duplicating the date inside the served markdown — guaranteed drift on the planned Qaren redraft | `legal_routes.py:30` |
| `CD-wave-diffs-04` | Code / DB / CI | M13-40 third JSON-LD pass (LIVE via default-ON ENABLE_JSONLD_FIRST) lets candidates in DIFFERENT currencies compete on raw numeric amount — smallest-numeral currency wins, not the right offer | `price_service.py:10755` |
| `CD-wave-diffs-07` | Code / DB / CI | M13-09 strict-shopping over-pends two genuine shapes: 'US$ 25.99' (letter-dollar regex matches the S of US) and Arabic-Indic-numeral target-glyph prices (digits not stripped from the residue) | `price_service.py:9345` |
| `CD-wave-diffs-08` | Code / DB / CI | ENABLE_EXTENDED_FALLBACK_RATES does not reach the direct-adapter convertibility gates — a TRY/PLN/CAD-base store still skips with the flag ON, so a canary of the flag will under-measure it | `price_service.py:14448` |
| `CD-wave-diffs-09` | Code / DB / CI | refund_comparison_credit across a UTC day/month rollover decrements the NEW window's key to -1, permanently: the -1 key never gets a TTL and offsets that user's counter forever | `usage_service.py:262` |
| `CD-wave-diffs-10` | Code / DB / CI | POST/GET /compare burn the reserved credit on an uncaught raise: refund fires only on a success:false RESULT, so any exception out of compare_from_text (or the post-gate plumbing) → 500 with the credi | `text_routes.py:224` |
| `LS-capacity-math-05` | Load / scale | GIL/CPU parse convoy is an unmodeled ceiling: 40 threads parsing up-to-3MB pages contend with the event loop for one GIL | `price_service.py:13879` |
| `LS-event-loop-05` | Load / scale | Blocking Redis inside the 15s price race: raw has_budget, flag-OFF provider gates, and per-200 record_usage steal race budget from every concurrent compare | `review_service.py:793` |
| `LS-event-loop-08` | Load / scale | Post-response fire-and-forget tail blocks the loop ~0.9-1.6s per authed compare and is charged to OTHER users' latency | `feedback_service.py:33` |
| `LS-event-loop-09` | Load / scale | Ceiling note: Railway healthcheck shares the blocked loop - sustained saturation during a deploy window can flap the service | `railway.json:8` |
| `LS-railway-metrics-05` | Load / scale | price-warmer is armed (ENABLE_PRICE_CACHE_WARMER=true) and re-runs on every push to main — silent Serper burn + background prod load the moment keys revive | `cron_warm_price_cache.py:271` |
| `LS-railway-metrics-06` | Load / scale | 7-day p95/p99 and error-rate are unobtainable: per-deployment log retention x 20-deploy churn destroys the baseline the canary plan depends on | `2026-08-31-m13-full-review.md:1` |
| `MB-contract-06` | Mobile app | No client-side deadline on the SSE stream (or camera fetch) and abort is never invoked — backend's flag-OFF unbounded verdict tail can pin the loader forever | `api.ts:410` |
| `MB-contract-08` | Mobile app | Unified error envelope drops tier/remaining from 429 USAGE_LIMIT — FE UsageLimitError type promises fields the wire never carries | `error_handler.py:92` |
| `MB-contract-09` | Mobile app | parseApiError blankets every 503 to TIMEOUT, overriding explicit non-timeout codes like FEATURE_DISABLED | `api.ts:635` |
| `MB-contract-10` | Mobile app | Phantom typed keys: scoring.win_margin and scoring.products never exist on the wire — share-CTA variants dead and invitee match score hardcoded to 78 | `types.ts:349` |
| `MB-flows-07` | Mobile app | History is hard-capped at 50 rows with no pagination and no truncation signal | `HistoryScreen.tsx:356` |
| `MB-flows-10` | Mobile app | category_switched is never surfaced, so a user whose category hint was overridden is shown the result as if it matched their pick | `ResultsScreen.tsx:723` |
| `MB-flows-11` | Mobile app | Auth screens are the copy-contract hole: two catalog strings say 'failed' and every error path renders raw axios/backend English | `en.json:1` |
| `MB-flows-12` | Mobile app | ResultsScreen carries a write-only usageStatus plus a dead orchestrator helper block, costing a /usage/status round trip on every result view | `ResultsScreen.tsx:164` |
| `MB-i18n-rtl-01` | Mobile app | AR plural coverage is _one/_other only; Arabic counts 0,2,3-10,11-99 resolve to English, and both jest fences are structurally blind to it | `ar.json:855` |
| `MB-i18n-rtl-02` | Mobile app | No Intl.PluralRules polyfill and no compatibilityJSON: plural behavior on Hermes phones diverges from the Node/jest environment that validates it | `index.ts:24` |
| `MB-i18n-rtl-04` | Mobile app | TwoInputShell double-mirrors under forceRTL: explicit 'row-reverse' when isRTL cancels RN's automatic row flip, putting the numeral circle on the wrong side in Arabic | `TwoInputShell.tsx:684` |
| `MB-i18n-rtl-05` | Mobile app | Five physical textAlign:'left'/'right' sites are not RTL-aware; the ResultsAccordion spec-value cells invert their hug-the-center design in Arabic | `ResultsAccordion.tsx:880` |
| `MB-i18n-rtl-06` | Mobile app | Arabic-Indic digit policy is inconsistent across ar.json (32 values Arabic-Indic vs 20 Western), including the same sentence in both systems and one string mixing both | `ar.json:883` |
| `MB-i18n-rtl-07` | Mobile app | Currency display is two different languages in one app: Results shows Latin ISO codes with unpinned toLocaleString, Paywall shows localized 'د.ب' — and BHD loses its 3-decimal convention | `ResultsContent.tsx:129` |
| `MB-i18n-rtl-08` | Mobile app | Live {count} call sites resolve to bare keys with no plural forms — 'Across 1 decisions' / 'عبر 1 قرارات' at count=1 | `HomeEditorialSections.tsx:296` |
| `MB-i18n-rtl-09` | Mobile app | W4's new ScanCameraScreen permission pad ignores the arabicLineHeightMultiplier contract — which only 2 components app-wide actually consume | `ScanCameraScreen.tsx:622` |
| `MB-perf-03` | Mobile app | Loader-holding timeouts: camera identify has NO timeout (indefinite spinner), text/url/history paths hold 120s — 4x any server budget | `api.ts:20` |
| `MB-perf-05` | Mobile app | RevealBurst's spring/timing animations drive shared values that are never bound to any style — the winner celebration renders static, animation work is dead | `RevealBurst.tsx:104` |
| `MB-perf-06` | Mobile app | Zero React.memo in the entire app; ResultsScreen orchestrator re-renders the full ~1,650-line results tree on each of ~5 early state transitions, including exactly at winner-reveal | `ResultsContent.tsx:100` |
| `MB-security-03` | Mobile app | Pre-SecureStore plaintext token residue in AsyncStorage is never deleted, and Android auto-backup includes it | `authService.ts:349` |
| `MB-security-06` | Mobile app | Google sign-in has no nonce binding (Supabase 'Skip nonce checks' ON) — any bearer of a valid Google id_token can mint a Qaren session | `authService.ts:489` |
| `MB-security-07` | Mobile app | Release-build pinning init failure is silent fail-open — the catch assumes Expo Go and emits no production telemetry | `certificatePinning.ts:53` |
| `MB-security-08` | Mobile app | User PII (email) at rest in plaintext AsyncStorage with Android auto-backup left at default-on | `authService.ts:294` |
| `MB-two-lever-04` | Mobile app | Pending OTA is native-compatible: zero dependency changes since the last build, app.json untouched, runtime stays 1.0.0 | `package.json` |
| `MB-two-lever-05` | Mobile app | Babel console-strip DOES ride the OTA (bundled at eas update time) — but only if the publish env is production | `babel.config.js:51` |
| `MB-two-lever-06` | Mobile app | CANARY_NEW_ONBOARDING_PERCENT=100 verified correct for testers; no features.ts const flips behavior when the update lands | `features.ts:30` |
| `MB-two-lever-07` | Mobile app | Channel-targeting risk: all documented installed builds follow 'preview' — an eas update to --branch production reaches zero devices | `eas.json:15` |
| `MB-two-lever-08` | Mobile app | App Store blocker 1 UNRESOLVED at main: icon/splash/adaptive are still the untouched create-expo-app scaffolding bytes | `icon.png` |
| `MB-two-lever-09` | Mobile app | App Store blocker 2 UNRESOLVED at main: live legal docs still open with 'DRAFT — This document is a template' | `privacy_policy.md:7` |
| `PO-fact-check-12` | Product output | confidence_details always reports freshness 'live', even on fully cached responses | `response_builder.py:883` |
| `PO-fact-check-13` | Product output | CLAUDE.md still documents fact_check.overall_confidence (high/medium/low) - a field dropped by Bundle E Decision 7 | `CLAUDE.md:200` |
| `PO-recorded-09` | Product output | Winner axis is the weakest judged axis and flips on identical queries within hours | `scoring_service.py:809` |
| `PO-recorded-03` | Product output | 18/26 recorded outputs shipped under category 'other', producing all-N/A generic spec tables | `extraction_service.py:1108` |
| `PO-recorded-05` | Product output | Two scoring systems ship in one payload; winner-card margin comes from the legacy one | `response_builder.py:1429` |
| `PO-recorded-07` | Product output | Review summaries assert volume/agreement with zero verified reviews and launder marketing copy as owner consensus | `review_service.py:439` |
| `PO-recorded-08` | Product output | Fact-check computes damning signals that never reach the shipped price/review confidence | `fact_check_service.py:207` |
| `PO-recorded-10` | Product output | Factual axis: ~46 of 200 gold verdicts contained a forbidden fact at last measurement, never re-measured | `eval_runner.py:856` |
| `PO-recorded-13` | Product output | Doubled-brand display strings ship in winner declarations and evidence lines | `openai_service.py:271` |
| `PO-rubric-10` | Product output | Session +/-5% signals shift positionally-guessed dims - 'reviews' dwell boosts build quality in electronics | `scoring_service.py:2209` |
| `PO-rubric-11` | Product output | Value-math gap (35 xfail stubs): a budget-tier user comparing two luxury products gets zero acknowledgment anywhere | `test_value_math.py:63` |
| `PO-rubric-12` | Product output | The documented +/-30% explicit cap drifts to +32% after renormalization | `scoring_service.py:1230` |
| `PO-verdict-text-08` | Product output | Never-empty-cons prompt rule converts pipeline data gaps into product criticism — degraded tiers dress emptiness as flaws | `extraction_service.py:982` |
| `PO-verdict-text-10` | Product output | clean_review_citations leaves 'Per domain: ' husks on trailing/interior citations and passes '[pcmag.com]'-form markers through untouched in persisted review text | `review_service.py:145` |
| `PO-verdict-text-12` | Product output | Verdict calibration coverage is uneven: 4/9 categories inject nothing, and no anti-pattern targets the dominant recorded failure mode (score-margin cited as the 'why') | `verdict_exemplars.json:49` |

---

## §5 — Units filed

All 28 confirmed P1 findings were filed as GitHub issues on `KGRddhs/smartcompare-backend`, deduped where several lanes confirmed one defect (the load group's 8 findings are 4 units). Each carries the house format and is self-contained — an implementer needs no access to this report to execute one. P2 and P3 rows in §4 remain backlog and were not filed.

| Issue | Unit | Findings |
|---|---|---|
| [#97](https://github.com/KGRddhs/smartcompare-backend/issues/97) | [ops] fix SERPER_LIFETIME_LIMIT=1 on the prod web service before any canary | M18-00A |
| [#98](https://github.com/KGRddhs/smartcompare-backend/issues/98) | [ops] bound the price-warmer service's Serper spend and take it off push-triggered deploys | M18-00B, LS-railway-metrics-05 |
| [#99](https://github.com/KGRddhs/smartcompare-backend/issues/99) | [verdict] make the winner card name and praise the deterministic winner, not GPT's pick | PO-recorded-01 |
| [#100](https://github.com/KGRddhs/smartcompare-backend/issues/100) | [scoring] normalize spec fields per-field before aggregating instead of summing raw cross-unit magnitudes | PO-rubric-01, PO-rubric-02 |
| [#101](https://github.com/KGRddhs/smartcompare-backend/issues/101) | [scoring] stop letting a missing signal outscore a measured bad one — renormalize instead of injecting 50 | PO-rubric-03 |
| [#102](https://github.com/KGRddhs/smartcompare-backend/issues/102) | [scoring] resolve the category's value dimension for value_badge instead of hardcoding 'value_score' | PO-rubric-04 |
| [#103](https://github.com/KGRddhs/smartcompare-backend/issues/103) | [scoring] translate behavioral sensitivity into category dimension keys and label scoring_method by what actually moved | PO-rubric-05 |
| [#104](https://github.com/KGRddhs/smartcompare-backend/issues/104) | [scoring] add the genuine-BH source methods to _PRICE_TRUST_SET so scraped Bahrain prices stop scoring as estimates | PO-fact-check-06 |
| [#105](https://github.com/KGRddhs/smartcompare-backend/issues/105) | [mobile] make the "What we know" sheet render the live confidence_details dict instead of crashing | PO-fact-check-05 |
| [#106](https://github.com/KGRddhs/smartcompare-backend/issues/106) | [fact-check] normalize shopping-row currency before the price cross-check | PO-fact-check-01 |
| [#107](https://github.com/KGRddhs/smartcompare-backend/issues/107) | [fact-check] carry spec citation confidence across the specs cache so the citation layer runs on warm traffic | PO-fact-check-02 |
| [#108](https://github.com/KGRddhs/smartcompare-backend/issues/108) | [fact-check] make the citation rubric unit-aware and able to emit "flagged" | PO-fact-check-03 |
| [#109](https://github.com/KGRddhs/smartcompare-backend/issues/109) | [scoring] wire fact_check verification into the confidence pills | PO-fact-check-04 |
| [#110](https://github.com/KGRddhs/smartcompare-backend/issues/110) | [verdict] reconcile winner prose with the deterministic winner index at the response chokepoint | PO-prompts-01 |
| [#111](https://github.com/KGRddhs/smartcompare-backend/issues/111) | [prompts] make the quantify trust rule evidence-conditional and drop the ungrounded halal-compliance instruction | PO-prompts-03 |
| [#112](https://github.com/KGRddhs/smartcompare-backend/issues/112) | [api] refund the credit and skip metering when the SSE client leaves before the verdict | CD-interactions-01 |
| [#113](https://github.com/KGRddhs/smartcompare-backend/issues/113) | [pipeline] apply the region-currency guard before scoring so the streamed price and the verdict use the guarded price | CD-interactions-02 |
| [#114](https://github.com/KGRddhs/smartcompare-backend/issues/114) | [ratelimit] anchor the limiter key on a verified per-client IP before arming any rate limit | LS-ratelimit-01, LS-capacity-math-01, LS-railway-metrics-01 |
| [#115](https://github.com/KGRddhs/smartcompare-backend/issues/115) | [perf] finish the offload sweep for the request-path blocking calls W3 left inline | LS-event-loop-02, LS-capacity-math-02, LS-railway-metrics-02 |
| [#116](https://github.com/KGRddhs/smartcompare-backend/issues/116) | [home] replace the unbounded /home/savings full_response SELECT with a SQL-side aggregate | LS-event-loop-01 |
| [#117](https://github.com/KGRddhs/smartcompare-backend/issues/117) | [llm-cost] size the OpenAI launch against TPM and bound the 429 retry amplification | LS-capacity-math-03 |
| [#118](https://github.com/KGRddhs/smartcompare-backend/issues/118) | [mobile] stop every compare from running two full backend comparisons | MB-perf-01 |
| [#119](https://github.com/KGRddhs/smartcompare-backend/issues/119) | [mobile] ship the pending EAS OTA so phones stop dead-ending premium and referral users at 3 compares | MB-two-lever-02 |
| [#120](https://github.com/KGRddhs/smartcompare-backend/issues/120) | [ci] Make the merge gate real: require backend-tests and frontend-tests, un-blind frontend-typecheck | CD-ci-truth-04 |
| [#121](https://github.com/KGRddhs/smartcompare-backend/issues/121) | [ci] Refuse to certify a regression baseline captured against an off-lock environment | CD-ci-truth-01 |

