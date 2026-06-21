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

### Ready-to-paste kickoff (next session)
```
Read docs/plans/2026-06-21-fragrance-content-quality-bundle.md (full catfix-session findings + this bundle's scope) and memory/project_catfix_shipped.md. catfix shipped (main 698006a); this bundle fixes the fragrance CONTENT quality found via a fresh nocache pull (NOT the stale screenshots).
STEP 0 FIRST: run ~6 fragrance pairs through prod ?nocache=true, inspect the FULL content (price/verdict/pros-cons/reviews/specs), and pin the confirmed bugs as failing tests — do not trust screenshots.
Then fix, TDD: F1 strip raw scores from verdict/pros text (no-internals; the A.10.x audit has a gap); F2 propagate price-pending into the verdict/pros prompt + decide the asymmetric-pend UX; F3 confirm/fix metadata.category_used on q=. F4 (G1 subtype spec-drop) + F5 (URL scoring) are larger/deferred — scope separately.
Verify EVERY change with a FRESH nocache pull inspecting actual content (the twice-burned lesson), not HTTP-200 or a screenshot. Ship: free-unit gate green + smoke20 vs 54b603e8 (winner-flat expected) + a fresh-pull content confirm + EAS preview.
```
