# Genuine-BH price + missing-data bundle — DESIGN (2026-06-22)

> Brainstormed + approved by Ahmed 2026-06-22 (this session). Diagnosis is DONE — this design
> builds on the gated audit in `docs/plans/2026-06-22-price-genuine-data-codex-audit-and-next-session.md`
> (PART C = Codex gated; PART D = the 45-finding discovery sweep gated vs `main 2244ad4`; PART E = the
> per-category discovery matrix). The content-honesty bundle (score-leak / +Npt / price-pending /
> review-grammar / specs) is DONE + live (backend `2244ad4`, FE EAS `d3bff791`). **This is the DATA
> problem**, not a content problem.
>
> **Branch:** `feature/genuine-bh-price-data`. **Predecessor:** `[[fragrance-content-quality-shipped]]`.

## Goal (Ahmed)

> "correct data, no missing data."

Two outcomes, within $0 / low-risk reach this bundle, **backend-only** (the FE pending-render path
already exists — `ResultsContent.tsx:127`, `ResultsScreen.tsx:385` render `price.unavailable` as
"Pricing lands in an upcoming update." — so **no EAS leg** unless we deliberately touch the FE):

1. **No missing data** — no category silently returns `None`; no raw `N/A` leak.
2. **Correct data** — more products resolve to a genuine-BH BHD price (fewer `converted_usd`); the
   right products take the right price path (F1 misroute).

---

## HARD INVARIANTS (Ahmed's 9 guardrails — these GOVERN every workstream)

These override any convenience. The gap-detection Workflow and every implement/review wave must gate
against them.

- **G1 — "no missing data" ≡ "no silent `None` / no raw `N/A` leak", NOT a real-price promise.**
  If a genuine-BH or a real *cited* converted price cannot be **verified**, return a **structured
  pending price with a reason** (`make_pending_price(reason=…)`) — NEVER a fabricated amount, NEVER a
  bare `None` that the FE renders as "N/A". The invariant is *shape*, not *value*.
- **G2 — supplement detector stops bare-substring matching.** Require **whole-token** supplement
  evidence. For ambiguous nutrient tokens (`iron`, `collagen`, `protein`, `zinc`, `calcium`, `d3`)
  require a corroborating **dose / form / brand** signal. Unambiguous tokens (`multivitamin`,
  `probiotic`, `softgel`, a known supplement brand) may stand alone.
- **G3 — park ONLY trustworthy prices.** Park iHerb / pharmacy / cited-snippet prices **only when a
  real retailer + source URL exists.** Retailer-less GPT output is **never** promoted to a showable
  price. Estimate-only → pending shape (no displayed amount). CDE-2 may attribute a BH-pharmacy
  retailer **only** with deterministic evidence from a matched snippet / link / domain — **no guessed
  retailer assignment.**
- **G4 — EL-2 device-class split.** Bare brands (`samsung`/`galaxy`/`xiaomi`/`huawei`/`oneplus`/
  `nvidia`/`amd`) must **not** trip the flagship floor without a co-occurring **device-class noun**.
  Keep the floor for true phones / laptops / consoles / GPUs.
- **G5 — SSE parity + total scrub.** The SSE `prices` event uses the **same** price-pending projection
  as the final response. Widen the internal-score scrub to **every user-visible GPT text field** (not
  only the prior bundle's 5 — enumerate all).
- **G6 — WS-F is mandatory.** The all-category Bahrain source matrix + a **drift-guard test** ship in
  this bundle. This is what prevents the fix becoming supplement/fragrance-only.
- **G7 — WS-G verify-or-omit.** TIER-2 adapters (namshi / fashion / aldeerah) ship **only** if
  liveness-verified. No assumption-based registry rows.
- **G8 — sitemap-probe = fast-follow.** Designed, not built this bundle, unless TIER-1 **and**
  low-risk TIER-2 gates are already green with budget headroom.
- **G9 — SCRAPEDO_SUPER stays OFF** in Railway (Ahmed's action). Keep code plumbing + provider trace.
  Re-enable only under the controlled experiment protocol (documented in WS-H).

**No-fab carry-over (do NOT regress `2244ad4`):** prices never invented; ratings never AI-generated;
`estimated` is an explicit honest fallback that PENDS in the UI; genuine = the
`_GENUINE_BH_SOURCE_METHODS` set. Re-run the shipped score-leak / price-pending / review-grammar
guards in the regression gate.

---

## Workstreams

All anchors below are **gated vs `main 2244ad4`** (PART D). The gap-detection Workflow re-verifies
each before implementation; line numbers may have drifted slightly (re-grep symbols, don't trust raw
line numbers).

### WS-A — F1 supplement-misroute gate + detector precision  *(the "correct data" keystone)*

**Problem (CONFIRMED):** `structured_comparison_service.py:3910`
`is_supplement = (category == "supplements") or is_supplement_query(full_name)`. `is_supplement_query`
(`price_service.py:579-584`) substring-matches `SUPPLEMENT_KEYWORDS` (`iron`/`protein`/`collagen`/
`zinc`/`calcium`/`omega`/`d3`/…), so a correctly-categorized **non-supplement** whose *name* carries a
supplement substring force-routes to the iHerb-only branch → Serper Shopping + Shopify/Algolia
suppressed (`scs:4009/4012/4049`). Independent of catfix FIX-1 (that fixed the parser `category`, not
this OR). **Invisible to smoke20.**

**Approach (Fork 1 — combined, approved):**
1. **Category gate** at `scs:3910`:
   `is_supplement = (category == "supplements") or (category in ("other", None) and is_supplement_query(full_name))`
   — when the LLM resolved a *concrete non-supplement* category, trust it.
2. **+ Detector precision (G2)** — rewrite `is_supplement_query` to:
   - **whole-token** match (word boundaries), never bare substring;
   - split `SUPPLEMENT_KEYWORDS` into **UNAMBIGUOUS** (stand-alone: `multivitamin`, `probiotic`,
     `softgel`, `capsule`, `melatonin`, `biotin`, `coq10`, `glucosamine`, `creatine`, `turmeric`,
     `folic`, `supplement`, `fish oil`, + supplement brands `now foods`/`solgar`/`nature made`/
     `garden of life`/`kirkland`) vs **AMBIGUOUS** (`iron`, `collagen`, `protein`, `zinc`, `calcium`,
     `omega`, `magnesium`, `d3`, `d-3`, `mineral`);
   - an AMBIGUOUS token counts only with a corroborating **dose** (`mg`/`mcg`/`iu`), **form**
     (`softgel`/`capsule`/`tablet`/`gummy`/`caplet`/`count`/`ct`), or **supplement brand** signal.
   - keep the existing `HIGH_VALUE_KEYWORDS` short-circuit (a high-value electronics query is never a
     supplement) — but note WS-C narrows that set; verify the interaction.

**Unit-pin contract (the F1 misroute set — pin BOTH directions; this is invisible to smoke20):**
- MUST-NOT route to supplement branch: `Tefal steam iron`, `collagen serum`, `protein shaker`,
  `food container`, `Samsung Galaxy S24` (sanity).
- MUST still route to supplement branch: `Vitamin D3 5000 IU`, `NOW Foods Omega-3 1000mg softgels`,
  `Solgar Magnesium Citrate 200mg`, `Centrum Multivitamin`.
- WATCH (gap-detection to resolve): `Optimum Nutrition Whey Protein` (protein-powder *is* a supplement
  but may lack a dose/form/brand-in-set token — consider adding `whey`/`powder` corroboration or the
  brand).

### WS-B — Supplement "no missing data": bounded sub-stages + trustworthy park  *(the "no missing data" keystone)*

**Problem (CONFIRMED + mechanized):** the supplement Tier-2 chain (`scs:4639-4704`) is
**unbounded-sequential** (iHerb curl `timeout=15` as the *first* await, `price_service:3741`;
`_try_pharmacy_urls` serial `[:3]@10s`, called twice `:3934/:3951`) AND supplements **never** park a
fallback (`self._parked_price` set only on the non-supplement converted path, `scs:4120`) → on the
30s `STREAM_HARD_CAP` it returns `None` (live NOW/Solgar D3 = 30.0s / both-None).

**Approach (Fork 2 — bounded + trustworthy park, keep structure; approved):**
1. **Per-stage `asyncio.wait_for`** inside the supplement branch: iHerb ~4s, the two pharmacy passes
   parallelized under one ~5s outer bound, the page-scrape loop ~3s. No single stage eats the whole
   budget. (Latency-parallelization of *everything* = deferred Fork 2-B.)
2. **Park ONLY trustworthy prices (G3):** when iHerb / pharmacy / a cited-snippet extract yields a
   price **with a real retailer + source URL**, stash it into `self._parked_price[full_name]` so a
   cap-timeout returns *that real price*, not `None`. A retailer-less GPT extract is **not** parked as
   showable.
3. **Terminal honesty (G1):** if no trustworthy genuine/cited price resolves, the supplement path
   returns the **pending shape** (`make_pending_price(reason="pending_genuine")`) — an honest
   `estimated` *amount* is allowed only where the existing contract already displays estimates as
   pending; never a bare `None`. (Pairs with WS-D SIB-5: the chokepoint normalizes any residual
   `None` → pending.)
4. **CDE-2 (deterministic only, G3):** when iHerb organic is empty but a price was extracted from a
   matched `bh_organic` snippet, attribute the **retailer from that matched snippet's link/domain**
   (`scs:4716`) — only with deterministic evidence, no guess.
5. **Optional (low-risk):** relax the iHerb matcher (`NOW`/`NOW Foods`, `D3`/`D-3`/`cholecalciferol`;
   preserve strength/count/form) + per-stage reject-reason tracing (`[SUPPL_REJECT] reason=…`) as a
   verify aid.

### WS-C — EL-2 device-class precision

**Problem (CONFIRMED):** `HIGH_VALUE_KEYWORDS` (`price_service:332-336`) carries **bare brands**
(`samsung`/`galaxy`/`xiaomi`/`huawei`/`oneplus`/`nvidia`/`amd`); a genuine sub-50 "Samsung 25W
charger" (~8 BHD) trips `is_high_value_query` → the 50-BHD flagship floor
(`is_implausible_high_value_price`, `:560/570`) + `min_price=100` (`:2760`) → dropped / pended.

**Approach (G4):** split the set into **device-class tokens** (`iphone`/`macbook`/`ipad`/`laptop`/
`playstation`/`xbox`/`nintendo`/`rtx`/`geforce`/`radeon`/`gpu`/`pixel` — always high-value) vs **bare
brands** (`samsung`/`galaxy`/`xiaomi`/`huawei`/`oneplus`/`nvidia`/`amd` — high-value **only** with a
co-occurring device-class noun, e.g. `phone`/`laptop`/`tablet`/`console`/`tv`/`watch`/`buds`). Pin:
"Samsung 25W charger" passes at ~8 BHD; "Samsung Galaxy S24" still floored; "iPhone 15" still floored.
Note: `galaxy` is a Samsung sub-brand spanning phones *and* accessories (Buds/Watch) — treat as a bare
brand needing a device noun, and let the gap-detection pressure-test it.

### WS-D — Honesty-siblings the prior bundle left open  *(regression-sensitive — re-run shipped guards)*

All backend-only. Must NOT regress the score-leak / price-pending / grammar guards from `2244ad4`.
- **SIB-1 (G5):** the SSE `prices` event (`scs:2806-2813`) emits a raw price the final card pends →
  apply the **same** projection the final response uses (`is_price_showable` → `make_pending_price`)
  **before** the yield. Mirrors the FIX-2 NO-FAB guard already on the SSE reviews event (`scs:2827`).
- **SIB-4 → widened (G5):** the chokepoint scrub (`response_builder` `has_score_internals`) covers
  pros/cons + winner_reason/key_tradeoff/declaration/name. **Widen to every user-visible GPT text
  field** — enumerate them (known leakers: `value_context`, `best_for`, `spec_advantages`,
  `personalized_insights`; the gap-detection enumerates the rest) — and tighten the prompt rule
  (`extraction_service:646/654/672`) which currently *invites* numbers into specs/insights.
- **SIB-5 (G1):** `response_builder.py:1212` `if not isinstance(_price, dict): continue` — a raw
  `None`/non-dict price skips `make_pending_price` → FE "N/A". Normalize it to the **pending shape**
  instead of skipping. (FE already renders `.unavailable` — verified.)

### WS-E — Genuine-share reach, low-risk $0

- **CDE-3:** seed `self._price_candidates` from Tier-1 / short-circuit prices (today populated only by
  the fan_out, `scs:4593`) so fairness re-selection doesn't pend a genuine Tier-1 price on mixed-size
  pairs.
- **DM-3:** raise `bh['organic'][:4]` → `[:8]` (`scs:1312`) to match the `limit=8` discovery breadth;
  downstream gates handle quality.
- **F8 + CDE-4:** registry-reconcile `aldeerahpharmacy.com` **only if liveness-verified** (WS-G /
  verify-or-omit); don't 30d-negative-cache a Tier-3 `estimated` reached only via a per-request
  guard-reject.

### WS-F — All-category Bahrain source matrix + discovery contract  *(MANDATORY — G6)*

The category-wide deliverable that prevents a supplement/fragrance-only fix. Two artifacts:
1. **The matrix** (doc, seeded from PART E) — for **each** of the 9 categories
   (`CATEGORY_SPEC_SCHEMAS.keys()`): **source path** (curl-JSON-LD / Shopify-`products.json` / Algolia
   / render-only(starved) / super-OFF), **fallback path** (`converted_usd` → `estimated` → pending),
   and **known gap** (the structural, documented hole). Lives at
   `docs/contracts/bahrain-source-matrix.md` (or similar).
2. **The drift-guard test** — a static test that asserts **every** `CATEGORY_SPEC_SCHEMAS` category
   maps to ≥1 registered genuine-BH source **OR** is listed in an explicit `KNOWN_SOURCE_GAPS` set
   (with a reason). Matches the repo's static-guard pattern
   (`test_migration_index_predicate_immutability.py`, `test_eval_genuine_methods_parity.py`). This is
   what makes "every category has an explicit path" **non-drifting**.

This workstream also drives WS-G: the matrix surfaces *which* categories fall to `converted_usd` and
*which* candidate adapters would close them — only the liveness-verified ones ship; the rest are
recorded as `KNOWN_SOURCE_GAPS`.

### WS-G — TIER-2 verified low-risk adapters (verify-or-omit — G7)

Candidates (each ships **only** if `scripts/verify_source_registry.py` liveness confirms, under a
tight Serper cap):
- **namshi BH** (`en-bahrain.namshi.com`, Algolia — one `ALGOLIA_STORES` row + one registry `Source`,
  *iff* the BH Algolia app-id is confirmed live);
- **fashion candidates** the code comments name — `rivolishop.com`, level-shoes BH,
  `bathandbodyworks.com.bh` (verify-or-omit);
- **aldeerah** (`aldeerahpharmacy.com`, already in `PHARMACY_DOMAINS`, add the registry `Source` row —
  F8) iff live.

Unverified candidates → recorded in WS-F `KNOWN_SOURCE_GAPS`, not shipped. **No assumption-based
rows.**

### WS-H — SCRAPEDO_SUPER revert + experiment protocol (G9)

Code default already OFF (cost-neutral). **Ahmed reverts** `SCRAPEDO_SUPER=false` on Railway. Keep all
code plumbing, gated registry rows, and the provider trace. Document the **5-point re-enable protocol**
in the WS-F contract doc: (1) fixed small query set; (2) provider attempt trace inspected;
(3) per-run credit cap; (4) explicit before/after genuine-BH win evidence; (5) immediate revert if no
confirmed Bahrain-PDP price win.

---

## Deferred (designed, not built this bundle)

- **Sitemap-probe channel (F5)** — designed as a fast-follow (G8): a `/sitemap.xml` curl probe for
  registry domains that yield zero Serper PDPs (the unindexed BH SPAs sephora.bh/boutiqaat/bolo.bh).
  Built this bundle only if TIER-1 + low-risk TIER-2 gates land green with budget headroom.
- **Warmer cron + `ENABLE_PRICE_CACHE_WARMER`** on **paid** Serper — the *sustained* genuine-share
  lever for the structural luxury/render-only tail (Western fragrance/haircare/makeup). Ahmed's
  action; a cache-reading eval variant is a separate need (eval_runner uses `nocache` = cold).
- **F3** `category_used=None` on the COMPLETED/sync path (partial path already fixed).
- **claude.ai/design upload** of the WS-I ResultsScreen ref (re-sync the now-genuine contract; local
  ref already synced).

---

## Process

1. **Gap-detection planning Workflow** (ultracode, dynamic) — adversarial finders over: the supplement
   path, the price cascade / parked-fallback, the discovery layer + the all-category matrix, the
   honesty-siblings + the "every user-visible GPT field" scrub enumeration, the F1 detector edge
   cases, the EL-2 edge cases. Each finding **gated vs real code** (PART D table is the prior; new
   findings must be grepped + anchor-read). Output → a wave-structured implementation plan
   (`docs/plans/2026-06-22-genuine-bh-price-missing-data-implementation.md`).
2. **Implement in Workflow waves** — SEQUENTIAL implement agents (race-free, exactly one writer on the
   shared tree, per-task path-restricted commit) + parallel-but-**throttled** adversarial reviewers
   (≤2-3 concurrent — a 529 burst wiped 6-7-wide fan-outs late-session; resume via
   `Workflow({scriptPath, resumeFromRunId})`). **Never** run the full suite inside an implement task
   (only the single regression reviewer + a temp-main-worktree `comm` gate). The **dispatcher gates
   every wave** — re-derive each reviewer finding vs real code (~¼ are no-ops).

## Ship gate

- **Free-unit green** — branch-vs-main `comm` of the sorted FAILED-test sets → branch-only-NEW == [].
- **smoke20** vs baseline `54b603e8` (winner ≥ 0.50, factual 1.0 held) — POST-deploy (eval_runner is a
  prod-HTTP harness; `source .env` first to dodge the stale-`SUPABASE_*` baseline-fetch false-fail).
- **Fresh-`nocache` genuine-share confirm** via `.qa-frag-content/g4_extract.py` (classifies
  GENUINE/converted/pending) — diagnose ONLY from fresh prod pulls inspecting
  `metadata.source_trace` + per-product `price.source_method`, NEVER screenshots or a top-level
  HTTP-200. Confirm: supplements no longer `None`; F1 misroute pins hold; EL-2 accessory passes.
- **Unit-pinned F1 misroute set** green (invisible to smoke20 — the static contract is the proof).
- Backend-only → **no EAS** unless the FE is deliberately touched.
- **Deploy** = explicit per-deploy authorization from Ahmed (the classifier gates default-branch
  `git push origin main`).

## Gotchas (durable, this session-line)

- Stale `SUPABASE_*` env breaks the eval baseline-fetch (tooling false-fail "GATE FAIL") — restart
  Claude Code or `source .env`, not just `unset`.
- Deploy-classifier gates default-branch pushes (explicit per-deploy "go"; doesn't carry across).
- eval is POST-deploy; `nocache` = cold (won't reflect the warmer's cached share).
- Serper free is finite (~2,500 one-time) — WS-G liveness checks under a tight cap; the warmer needs
  PAID Serper.
- railway CLI works after Ahmed's `railway login` (kinghaleem999@, empowering-enthusiasm/production/web).
