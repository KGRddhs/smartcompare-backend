# Fragrance Content Quality — Next Bundle Plan + Full catfix-Session Findings (2026-06-21)

> Successor to **catfix** (`docs/plans/2026-06-20-fragrance-category-allcat-implementation.md`, shipped to prod as main `698006a`). This doc carries (1) the FULL findings from the catfix session and (2) the scope for the next **"fragrance content quality"** bundle. Cross-session handoff: `memory/project_catfix_shipped.md`. Audit matrix (G1): `docs/plans/2026-06-20-allcat-audit-matrix.md`.

---

## PART 1 — Full findings from the catfix session (2026-06-20 → 2026-06-21)

### 1.1 What shipped (catfix → main `698006a`, one clean merge over base `5eef9d9`; EAS preview group `0c39fc44`)
4-Opus worktree team (be-core / be-render / test / fe) + dispatcher.
- **Keystone:** resolve the pair category + WRITE it onto `products[i]["category"]` BEFORE the `_fetch_product_data` gather, on BOTH sync + stream paths, via the shared `_resolve_pair_category` helper (`structured_comparison_service.py`). Scoring / spec-schema / category-aware source discovery all key off that per-product field. (Pre-catfix, the explicit_pair/vision paths used a hardcoded `supplements`/`other` binary → fragrances rendered as `other`.)
- **A5** rating honesty (derived/estimated ratings suppressed in projections + `_safe_rating` + `_dim_value` + `gpt_review_aggregate` at source); **A6** variant "N/A" leak; **A7** Scrape.do real-cost metering (`render_page_with_status` → `(html,status,cost)`); **B1** fragrance `scent_family` in PREFERRED; **B2** all-9-category render audit (GREEN); **D1** FE null-default + conditional `selected_category`.

### 1.2 The ultracode review caught a REAL regression (FIX-1) — the headline lesson
An adversarial multi-agent Workflow review was run BEFORE the prod ship. It found a HIGH regression the TDD team + cross-QA had missed: `_resolve_pair_category` runs on ALL THREE paths INCLUDING the `q=` parser path, where it let the deterministic `classify_category_from_text` keyword classifier OVERRIDE the LLM's full-context category. **4/200 gold queries misroute** — `Tefal steam iron`→supplements (`is_supplement_query('iron')`), `Vitamin C serum`→supplements (`'vitamin'`), `True Skin concealer`→skincare (`'skin'`), `food container`→grocery (`'food'`). **smoke20 structurally cannot see this** (none of the 4 IDs are in the subset). 
- **FIX-1** (`7f8a4e0`): on the `q=` parser path the LLM-emitted per-product category is AUTHORITATIVE; `classify_category_from_text` is a fallback only when the LLM said `other`. Name-detection stays authoritative for explicit_pair/vision (their per-product field is only the deterministic stub). Threaded `parser_path = not (vision_products or explicit_pair)` from both callers.
- **FIX-2** (`4b27017`): the A5 `rating_derived` guard was missing on the SSE intermediate `reviews` event (latent NO-FAB leak + a false code comment) → now mirrors the `response_builder` projection.
- **Polish (CLEANUP-1..5):** deleted prod-dead `resolve_category` (6 uncovered precedence cases PORTED to `_resolve_pair_category` tests first); URL-compare canonical enum + category routed into `generate_comparison`; `classify_category_llm` `asyncio.wait_for`; partial-ctx category seed; api.ts SSE-fallback gated.

### 1.3 Verification
- Free-unit gate: 48 pre-existing reds byte-identical, **ZERO catfix-introduced** (the only extra was the documented order-flaky `test_rate_limiting_complete`).
- **D2 cold prod probe** (Versace Eros vs Dior Sauvage): `category_used=fragrances`, real ratings, genuine prices. ⚠️ This checked only TOP-LEVEL fields — it did NOT inspect the full rendered content, and MISSED the content issues below.
- **smoke20 ACCEPTED**: winner FLAT 0.500 / factual HELD 1.000 / 0 estimates / 0 errors. specs 0.925 vs baseline `54b603e8` 0.9875 = cold-run/timeout noise (over-cap run). The "GATE FAIL" was a **stale-OS-env shadow**, not a regression (see 1.5).

### 1.4 On-device check — CORRECTED via a fresh `nocache` pull (the screenshots were stale)
Ahmed's on-device screenshots (Tom Ford Oud Voyager 100ml vs Oud Wood 100ml) looked "atrocious." A fresh `nocache` pull of the CURRENT `698006a` backend proved the screenshots were **largely STALE CACHE** (the documented stale-cache-masks-fix gotcha).
- **STALE / gone in current:** the "94.0 BHD" price contradiction, the raw "49.8" score, the 70.69 price (now **146.64** converted_usd), "6-8hr" longevity (now 10-12).
- **CURRENT real content issues** (NOT catfix regressions — the category fix WORKS, renders fragrance) → the scope for THIS bundle:
  1. **Raw scores leak into the verdict/pros TEXT** — recommendation: *"wins with a 10.7-point higher overall score"*; Oud Wood pro: *"Strong presentation score of 100"*. The `49.8` was stale but the LEAK PATTERN is current with different numbers. Violates "no backend internals in reveals."
  2. **Asymmetric pricing** — Voyager 146.64 BHD shown, **Oud Wood `pending` (`reason=pending_genuine` = no genuine BH source found)**. Poor UX + a structural BH-source gap; NOT a contradiction (the screenshot's "94.0" was stale).
  3. **Soft price-reference while pending** — Oud Wood con: *"premium price point"* while its price is pended (the verdict references a price the card hides).
  4. **`metadata.category_used = None`** on this q= pull (vs the D2 pair = `fragrances`). `category_used` IS populated 32× in `structured_comparison_service.py`, so this is most likely a **partial-response artifact** (fragrance compares run near the 30s `STREAM_HARD_CAP`; this response was 25.5 KB) OR a q= metadata edge case. The CONTENT was correctly fragrance.
  - Reviews now carry REAL ratings + sources (mercari via Google Shopping).

### 1.5 Durable lessons + gotchas (recorded in CLAUDE.md + memory)
- **VERIFY THE RESULT, NOT A GLANCE — twice this session I diagnosed from a glance** (the D2 top-level probe, then the screenshots) and both were wrong/incomplete. The ONLY reliable check is a fresh `nocache` pull with the actual content inspected. This is `[[prove-it-works]]` + the stale-cache gotcha combined.
- **Stale-cache-masks-the-fix:** re-running the SAME pair serves the 7d-specs / 24h-price cache (a pre-fix payload) → a "still broken" screenshot is usually stale cache. Re-test a FRESH/different pair or `?nocache=true`.
- **Stale OS `SUPABASE_*` env (RESOLVED 2026-06-21):** `SUPABASE_URL/ANON_KEY/SERVICE_KEY` were exported in the **User-scope** Windows env pointing at a DELETED project (`khatrmxzrvjzlbtcetva` → NXDOMAIN); `load_dotenv()` (no override) let the dead var win → broke the smoke20 persist/baseline-fetch (this was the "GATE FAIL", NOT box-DNS, NOT a regression). Removed from User scope; restart Claude Code to shed a session's inherited copy. Per-command workaround: `$env:SUPABASE_URL=$null; $env:SUPABASE_ANON_KEY=$null; $env:SUPABASE_SERVICE_KEY=$null`.
- **Serper vs Scrape.do:** Serper = search/discovery, the foundation of EVERY compare (finite ~2,500/free account). Scrape.do = page-RENDER fallback that needs a URL Serper provides — it CANNOT replace search. The lever to cut per-compare Serper is the cache WARMER (paid Serper to populate → free reads), not more Scrape.do.
- **EAS `*` suffix** on the commit hash = repo had uncommitted changes at bundle time (here just `.claude`/qa-scratch, not FE drift) — verify with `git status -- SmartCompareApp/`.
- **Ultracode review earned its keep:** an adversarial review BEFORE ship caught a regression a thorough TDD team + cross-QA missed (the q= path was outside their explicit_pair/vision scope). Gate every reviewer finding against the real code — but here all 4 confirmed findings were real.

---

## PART 2 — Next bundle: FRAGRANCE CONTENT QUALITY

**Goal:** the fragrance comparison RESULT is faithful + clean — no raw internal numbers in user-facing text, consistent price handling (card ↔ verdict), genuine BH prices where sourceable, and complete specs. **All grounded in FRESH `nocache` pulls, not screenshots.**

### Step 0 (MANDATORY, do FIRST) — fresh-pull content audit
Before any code: run ~5-8 fragrance pairs through prod `?nocache=true` (designer + niche; both-priced, one-pending, and both-pending cases) and inspect the FULL content (prices, verdict text, pros/cons, reviews text, specs per product). Build the REAL current bug list — do NOT trust the stale screenshots. Cost: ~5-8 Serper compares. Pin the confirmed bugs as failing tests.

### F1 — Raw scores leak into the verdict/pros TEXT (HIGH, no-internals-in-reveals)
**Symptom (fresh-pull-confirmed):** "wins with a 10.7-point higher overall score", "Strong presentation score of 100" in user-facing text.
**Anchors (grep to confirm lines):** the verdict GPT (`extraction_service.py` `generate_comparison` / `COMPARISON_SYSTEM` prompt — likely feeds the dimension/overall scores into the prompt and GPT echoes them); `response_builder.py` (`factual_verdict`, pros/cons assembly); `scoring_service.py` (the score source). The Bundle-C **A.10.x "verdict prompt forbidden-words audit"** was supposed to strip internals — **find the gap** (it doesn't catch "X-point higher overall score" / "score of N").
**Fix direction:** do NOT feed raw numeric scores into the verdict/pros prompt (pass ordinal/qualitative framing — "leads on", "higher", dim NAMES — not the numbers); + a post-generation regex/forbidden-pattern strip for "\d+(\.\d+)?[- ]point", "score of \d+", "overall score". Add tests pinning that no raw score survives in `recommendation` / pros / cons.

### F2 — Price-pending consistency (card ↔ verdict) + asymmetric-pend UX (MED)
**Symptom:** Oud Wood `pending_genuine` (card hides price) but the verdict/pros still reference its price qualitatively ("premium price point"); and one-priced/one-pending is jarring.
**Anchors:** `price_service.py` (`make_pending_price` / `is_price_showable` / `pending_genuine`); `response_builder.py` (price-pending projection); the verdict prompt construction (what price info is passed per product).
**Fix direction:** when a product's price is pending, suppress its price (and price-derived claims) from the VERDICT prompt + pros/cons too — not just the card (parallels the catfix FIX-2 "guard at every surface" pattern). For the asymmetric-pend UX, decide a rule: if one side pends, either pend both (consistent) OR render a neutral "price unavailable for this one" line; FE/render call. Separately, the structural BH-source gap (no genuine BH price for some fragrances like Oud Wood) is the warmer/genuine-share lever (paid Serper) — out of scope for the text-consistency fix.

### F3 — `metadata.category_used = None` on q= (INVESTIGATE)
**Anchors:** `structured_comparison_service.py` (32× `category_used`; the metadata population on the q= path + the partial/hard-cap-timeout path). Confirm whether it's a partial-response artifact (the fresh pull ran near the 30s cap) or a real q= gap; if real, ensure `category_used` is always set in `metadata` for the FE. Likely low-effort once reproduced under a non-timed-out pull.

### F4 (DEFERRED from catfix) — G1 subtype spec-drop
`_build_specs_prompt` prompts GPT with `PRODUCT_TYPE_SCHEMAS[subtype]` field names but `extract_specs` filters to `CATEGORY_SPEC_SCHEMAS[category]` → mismatched fields silently dropped → EMPTY/asymmetric specs (TVs/watches/protein = 0 survive; fragrances partial). HIGH-value, broad blast radius (`extract_specs` + `category_profile` + label overrides + FE i18n + fairness extractors). Full evidence in `docs/plans/2026-06-20-allcat-audit-matrix.md`. Tackle as its own sub-effort (consider a design pass) — it explains the "—" specs asymmetry seen in the (stale) screenshots; re-confirm the CURRENT fragrance spec completeness in the Step-0 audit first.

### F5 (DEFERRED from catfix) — URL-compare full scoring
`compare_from_urls` runs `generate_comparison` (verdict) ONLY, not `compute_scores`/`build_dimensions_v2` → URL-mode renders no dimension bars. catfix's CLEANUP-2 routed the category into the verdict but left this. Separate, larger change.

### Execution + budget
- **Solo-or-small-team** (F1/F2/F3 are focused backend edits; F4 is bigger). The git-index-race + shared-file serialization lessons from catfix apply if a team is used.
- **Budget:** Step-0 audit ~5-8 Serper compares; otherwise mostly $0 unit/scoring tests. The structural BH-source gap (F2 tail) + measuring genuine-share need PAID Serper + the warmer — keep separate.
- **Eval caveat (still true):** `eval_runner` is a PROD-HTTP harness (post-deploy); smoke20 can't see the q= category class (unit-pin instead); the smoke20 baseline is `54b603e8`.

---

## PART 3 — PRE-PROVIDER-CHANGE work items (Ahmed-specified, FACT-CHECKED vs 698006a 2026-06-21)

> Ahmed's directive: these are implemented **BEFORE any scraping-provider change** (Scrape.do geo/trace + a possible Zyte bakeoff). Each item below was verified against the real code — anchors + verdicts are confirmed, not assumed. **Design principle (Ahmed):** the Results shell should *render the data contract*, NOT rescue weak/contradictory data after the fact. The items split into a BACKEND honesty/quality wave (P1–P6, do first) and a DESIGN/contract wave (P7–P9).

> **SCOPE COMMITMENT (Ahmed, 2026-06-21) — these are ALL in-scope FIXES this bundle, not deferred or conditional:** (1) the **score leak** (P1–P5, all THREE sources) IS fixed; (2) the **review-praise grammar** (P6) IS fixed — the construction bug is confirmed live in current code, so it ships regardless of the stale screenshot (Step 0 only confirms the exact triggering data so the test is realistic — it does NOT gate the fix); (3) **Scrape.do being under-leveraged/undervalued** (P8) IS fixed — give it a real geo-targeted render attempt at the CF-walled BH retailers (it's currently written off to estimates too early) + the provider trace, with Zyte as an A/B candidate only if Scrape.do still can't crack them. None of these three is "maybe."

> **PLANNING METHOD (Ahmed):** next session AUTHORS this plan via an **ultracode dynamic Workflow** that FIRST detects further gaps (adversarial multi-agent sweep over the verdict/score/price/review/spec pipeline + the Scrape.do provider path) BEFORE finalizing the plan — the same adversarial-review pattern that caught the catfix q= regression. Treat P1–P9 below as the VERIFIED seed, not the complete list; the workflow's job is to find what this fact-check missed (gate every finding against real code — ~half of LLM-reviewer "must-fixes" are no-ops, per [[feedback-verify-llm-reviewer-findings]]).

### 🔑 Root-cause finding: the score-leak has THREE sources, not one
The "10.7-point higher overall score" / "score of 100" leak (F1) originates in THREE places — fixing only the prompt leaves it shipping:
1. **Prompt instruction** — `extraction_service.py:1762` (inline "## Verdict Requirements" block in `generate_comparison`, appended after `build_verdict_prompt` — NOT a constant literally named `COMPARISON_SYSTEM`): *"State the winner with the score margin in under 20 words. Cite the single most important numeric advantage."*
2. **Raw `scores_summary`** — `scoring_service.build_scores_summary` (`scoring_service.py:2244`) emits `"{name}: {overall}/100 overall"`, `Breakdown: {dim}={score}`, `"Score winner: {name} by {margin} points"`; injected into the prompt at `extraction_service.py:1759`. (Its `dimension_winners` block is ALREADY qualitative names — keep that.)
3. **⚠️ Deterministic code fallback (proposal missed this)** — `structured_comparison_service.py:4831`: `f"{winner_name} leads on the overall score by {margin} points."` fires in CODE when GPT returns no `winner_reason`. Pure Python, no prompt involved → survives any prompt-only fix.

### P1 — Ban raw internals in ALL user-visible text (HIGH) — VERIFIED, gap is real
Forbidden in `recommendation`/`winner_reason`/`key_tradeoff`/pros/cons/any reveal: `overall score`, `score of`, `/100`, `N-point higher`, `+Npt`, bare `\d+(\.\d+)? points`. Verified: there is currently **NO post-generation scrub** catching these in verdict/pros text (extensive scrub infra exists for prices/copy-policy/Sentry, none for verdict numerics; the Bundle-C "A.10.x verdict forbidden-words audit" is prompt-side only). Fix = a shared `_strip_score_internals(text)` applied to the GPT verdict text AND the deterministic fallback (#3 above) AND pros/cons (see P5). Pin with tests on all three sources.

### P2 — Remove "state the score margin" from the verdict prompt — VERIFIED anchor
Edit `extraction_service.py:1762`: drop "with the score margin" + "Cite the single most important numeric advantage"; replace with qualitative framing ("name the single most important advantage in plain words — a dimension or capability, never a number").

### P3 — Replace raw `scores_summary` with a PRIVATE qualitative summary — VERIFIED anchor
Rewrite `scoring_service.build_scores_summary` (`scoring_service.py:2244-2295`) to emit: winner NAME, leading-dimension NAMES (the existing `dimension_winners` is already name-based — keep), a confidence band (high/med/low, NOT a number), cross-tier note — and **NO** `overall/100`, NO `Breakdown: dim=NN`, NO `by N points`. The GPT verdict must reason from facts + qualitative leaders, not the raw scoreboard. (Keep it as the internal prompt context — just strip the numbers.)

### P4 — Verdict-safe product projection before GPT (pending prices have NO amount) — VERIFIED structurally
The verdict prompt does `json.dumps(_p1/_p2)` of the FULL product dict (`extraction_service.py:1795-1799`), and `make_pending_price` runs in the `response_builder` PROJECTION which is DOWNSTREAM of `generate_comparison` → GPT currently sees the raw amount even when the card later pends it (= the "premium price point" while pended, F2). Fix = build a verdict-safe copy of each product before the dump: if a price is pending/unavailable, drop `amount` (and any price-derived field) so GPT cannot reference it. **PIN FIRST** with a test asserting the dict handed to `generate_comparison` has no amount on a pending price (the catfix "capture test" pattern).

### P5 — Sanitize GPT pros/cons after generation, FAIL CLOSED — VERIFIED gap
No pros/cons numeric/price-leak scrub exists today. Add a post-generation pass: drop any pro/con containing a banned score pattern (P1) OR a price for a product whose price is pending. Fail CLOSED (drop the offending item, don't ship it). Belt-and-suspenders to the prompt-side fixes.

### P6 — Fix review-praise grammar — IN SCOPE, SHIPS (construction bug VERIFIED live in current code)
`review_service.build_review_praise:490` does `f"Owners consistently highlight {woven}."` with `_lower_first` applied → if a highlight point is "Known for its luxurious scent" you get "Owners consistently highlight known for its luxurious scent." The CONSTRUCTION bug is REAL in current `698006a` code — **the fix ships this bundle.** (The atrocious screenshot was stale, so Step 0 just confirms the exact triggering highlight data so the unit test reflects a real case — that re-check does NOT gate the fix; the broken construction is reason enough.) Fix: when a clause begins with a relative/participial lead ("known for", "described as", "praised for", "noted for", "loved for"), reshape the frame ("Owners note it is known for…") or pick a different lead — never glue "highlight" + "known for". Add unit tests with those leading forms (assert no "highlight known for"/"highlight described as" output).

### P7 — Fragrance specs UI contract (DESIGN/FE) — no one-sided rows unless labeled; no score-point deltas
No spec row should show a value for one product and "—" for the other UNLESS explicitly labeled "confirmed only for X" (honest asymmetry, not silent). And remove score-point deltas (`+Npt`) from the fragrance spec/dimension captions. The `+Npt` text comes from the delta-text builder (`scoring_service.py` ~2909, the "+28pt …" fallback) — ⚠️ this is the same area as the documented stale-flaky `test_compose_delta_text_returns_empty_on_missing_score_sentinel`; tread carefully + re-baseline that test. (Note P7 overlaps F4/G1 — asymmetric "—" specs are partly the subtype spec-drop.)

### P8 — FIX Scrape.do being under-leveraged/undervalued + add provider trace; Zyte = A/B candidate only (IN SCOPE)
Two distinct "undervalued" angles — be clear which:
- **Metering undervaluation: ALREADY FIXED in catfix A7** — the old meter recorded 1 unit on `status==200` only; `render_page_with_status` now returns the real header cost (`(html,status,cost)`), so Scrape.do's true credit burn is counted. (Recorded here so it's not re-opened.)
- **CAPABILITY under-leverage: FIX THIS BUNDLE.** Scrape.do (residential proxies, Tier 1.5d) is currently written off to GPT `estimated` prices too early on the CF-walled BH luxury retailers (`sephora.bh`/`bolo.bh`/`boutiqaat` — the documented structural render-wall, `docs/investigations/2026-06-15-render-wall-bh-retailers.md`). Give it a REAL chance: add **geo targeting** (BH/GCC geo param) + correct render config + tuned timeout to `scrapedo_service`, so a walled retailer gets a genuine residential-proxy render attempt before falling to estimate. + a per-request **provider TRACE** (which provider rendered, geo, cost, status, outcome) so we MEASURE per-domain success and can prove whether Scrape.do now cracks them. ⚠️ this path COSTS Scrape.do credits (900/mo budget) — gate behind the existing circuit-breaker + measure burn.
- **Zyte = A/B bakeoff CANDIDATE only** (NOT in the codebase, NOT a default). Only after Scrape.do is properly geo-leveraged + traced: if it STILL can't crack the walled retailers, bake Zyte off against it behind a flag on those domains. Provider SWAP is a later decision driven by the trace data — this bundle makes Scrape.do earn-or-fail honestly first.

### P9 — claude.ai/design result-page contract-wiring — DO LAST: AFTER the plan is made AND the backend honesty fixes are implemented (Ahmed, 2026-06-21)
**Sequencing (Ahmed's ruling, supersedes any "do it now"): the Claude-design segment is the FINAL step — run it only AFTER this bundle is planned AND P1–P8 (the backend honesty/quality fixes) are implemented + shipped.** Rationale: the design "renders the data contract, not rescues weak data after the fact" — so the contract must first be made HONEST by the backend (P3 qualitative summary, P4 pending-price honesty, P6 real review sentiment, P7 spec-row rules); only then do you wire the result page to render the now-clean per-category contract.
- **Then (post-implementation): wire/re-sync the EXISTING category-driven Results shell to the cleaned contract** — for fragrances render: scent profile, notes, concentration, longevity/projection EVIDENCE (not a bare number), CONFIRMED-vs-pending price status, REAL review sentiment; honest absent/pending states (no invented or rescued data). The shell ALREADY exists (faithful-results 1:1 redesign shipped; `ui_kits/mobile/ResultsScreen.jsx` + `design-sync` infra) → re-sync via the normal `/design-sync` diff-and-integrate flow, **do NOT rebuild from scratch.**
- **Why design isn't skipped:** the atrocious result was partly a CONTRACT failure (raw score shown, pended price beside a soft price-ref, one-sided spec rows). The backend P-items make the data honest; the design step makes the result PAGE render that honest contract per category — the durable closure.
- Mechanics: `superpowers:brainstorming` + claude.ai/design "Qaren Design System" project (`c57eb43f-…`); per-category source of truth = `CATEGORY_DIMENSIONS`/`CATEGORY_SPEC_SCHEMAS`/`CATEGORY_FAIRNESS`; validate edited refs with `@babel/parser` per `memory/project_design_sync_qaren.md`.

### Sequencing
1. **Plan FIRST** via the ultracode gap-detection Workflow (above). 2. **P1–P6** (backend honesty/quality, $0) implement next — precondition for trusting any provider measurement. 3. **P7** (FE spec contract) + **P8** (Scrape.do geo-render + trace) land alongside. 4. **P9 claude.ai/design = LAST** — only AFTER the plan is made AND P1–P8 are implemented/shipped, wire the result page to render the now-clean contract (re-sync the existing shell, don't rebuild). The Zyte bakeoff + the structural-BH-source genuine-share work need PAID Serper + the warmer — separate, after the honesty wave.

---

## Ready-to-paste kickoff (next session)
```
Plan the "fragrance content quality" bundle. Read docs/plans/2026-06-21-fragrance-content-quality-bundle.md (full catfix-session findings + PART 3 the fact-checked P1–P9 items) and memory/project_catfix_shipped.md FIRST. catfix shipped (main 698006a) and its category fix WORKS; this bundle fixes the fragrance CONTENT quality. The atrocious on-device result was LARGELY STALE CACHE — diagnose ONLY from fresh nocache pulls, never screenshots/HTTP-200 (the twice-burned lesson).

PLANNING METHOD (Ahmed): AUTHOR this plan via an ULTRACODE dynamic Workflow — first run an adversarial multi-agent gap-detection sweep over the verdict/score/price/review/spec pipeline + the Scrape.do provider path (the same pattern that caught the catfix q= regression), THEN write the plan. Treat P1–P9 as the VERIFIED seed, not the full list — the workflow's job is to find what the fact-check missed. Gate every workflow finding against real code (~half of LLM-reviewer must-fixes are no-ops). Then superpowers:writing-plans.

STEP 0 (before coding): run ~6 fragrance pairs through prod ?nocache=true, inspect FULL content (price/verdict/pros-cons/reviews/specs), pin confirmed bugs as failing tests.

IN-SCOPE FIXES (all ship this bundle — none deferred/conditional):
- SCORE LEAK (P1–P5) — 🔑 THREE sources, fix ALL: prompt instruction extraction_service.py:1762, raw scores_summary scoring_service.py:2244 (injected :1759), AND the deterministic code fallback structured_comparison_service.py:4831. P1 shared score-internals scrub (none exists today) on verdict text + that fallback + pros/cons; P2 strip "state the score margin" at :1762; P3 build_scores_summary → qualitative (winner + leading-dim NAMES + confidence band, NO numbers); P4 verdict-safe projection BEFORE GPT (verdict json.dumps the full dict at :1797 BEFORE make_pending_price → pending prices drop amount; PIN with a capture test); P5 sanitize pros/cons FAIL CLOSED.
- GRAMMAR (P6) — FIX SHIPS: review_service.py:490 "Owners consistently highlight {woven}" breaks on "known for"/"described as" leads (construction verified live in 698006a). Step 0 confirms the triggering data; it does NOT gate the fix.
- SCRAPE.DO UNDER-LEVERAGE (P8) — FIX SHIPS: metering undervaluation already fixed (A7); CAPABILITY under-use is this bundle — geo-targeted real render attempt at CF-walled BH retailers (currently written off to estimates too early) + provider trace; Zyte = A/B candidate ONLY if Scrape.do still fails (not a default, not yet in codebase).
- P7 FE spec contract (no one-sided rows unless labeled + no +Npt deltas — touches the stale-flaky test_compose_delta_text). P9 claude.ai/design = a LIGHTWEIGHT per-category CONTRACT pass NOW (define the fragrance data contract the P-items render to), full shell rebuild DEFERRED (re-sync the existing shell after).
- DEFERRED/larger: F3 (category_used=None on q=, likely a partial artifact), F4 (G1 subtype spec-drop), F5 (URL-compare full scoring).

Verify EVERY change with a FRESH nocache pull inspecting actual content. Ship: free-unit gate green + smoke20 vs 54b603e8 (winner-flat expected) + fresh-pull content confirm + EAS preview. Budget: P1–P7 + the design contract are ~$0 (Step 0 ~6 Serper compares); the Scrape.do render attempts cost Scrape.do credits (gate behind the breaker); the Zyte bakeoff + genuine-share need paid Serper + the warmer (separate).
```
