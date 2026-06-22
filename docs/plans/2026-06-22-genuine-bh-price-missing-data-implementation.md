# Genuine-BH Price + Missing-Data Bundle — Wave-Structured Implementation Plan

**Source design:** `docs/plans/2026-06-22-genuine-bh-price-missing-data-design.md`
**Base:** backend `main 2244ad4` (code `dd66be1`). **Backend-only, NO EAS** except the FE-adjacent SSE-shape note in WS-E (which needs an EAS preview verify, NOT new FE code).
**Built by:** sequential ultracode Workflow implement waves (exactly ONE writer on the shared tree at a time; per-task path-restricted commit). Dispatcher gates EACH wave.

---

## HARD INVARIANTS (Ahmed's guardrails — every wave honors these)

- **G1** — "no missing data" = NO silent `None` / NO raw `N/A` leak, NOT a real-price promise. No verifiable genuine/cited price → structured `make_pending_price(reason=...)`, NEVER a fabricated amount, NEVER a bare `None`.
- **G2** — supplement detector stops bare-substring matching; whole-token + dose/form/brand corroboration for ambiguous tokens (iron/collagen/protein/zinc/calcium/d3).
- **G3** — park ONLY trustworthy prices (real retailer + source URL). Retailer-less GPT output (`gpt_organic_extract`) is NEVER promoted to showable. Estimate-only → pending. CDE-2 retailer attribution requires deterministic matched-snippet/link/domain evidence (no guess).
- **G4** — EL-2 bare brands (samsung/galaxy/xiaomi/huawei/oneplus/nvidia/amd) must not trip the flagship floor without a device-class noun; keep the floor for true phones/laptops/consoles/GPUs.
- **G5** — SSE prices event uses the SAME pending projection as the final response; widen the score-internals scrub to EVERY user-visible GPT text field.
- **No-fab carry-over** — do NOT regress the shipped score-leak / price-pending / review-grammar guards (`main 2244ad4`).

---

## WAVE DEPENDENCY GRAPH (build order)

```
WS-1 (detector: price_service.py is_supplement_query + EL-2 split)   ── independent, lowest risk, BOTH callers of HIGH_VALUE in one file
   │  (must land before WS-2: the scs:3910 category gate + supplement branch read the new predicates)
   ▼
WS-2 (scs supplement branch: category gate + per-stage wait_for + trustworthy park + CDE-2)
   │  (reads WS-1's is_supplement_query/is_high_value_query; owns the scs supplement region 3910 + 4639-4856 + _price_fallback_on_miss)
   ▼
WS-3 (scs genuine-reach: CDE-3 candidate-seed + DM-3 [:8] + CDE-4 negcache-skip)   ── scs price-cascade region (NON-overlapping with WS-2's supplement region)
   │
WS-4 (source registry + matrix: source_router.py F8 row + WS-F drift-guard test + contract doc)   ── independent of WS-1/2/3 (own files); WS-G adapters verify-or-omit
   │
WS-5 (HONESTY / G5 — response_builder.py widened scrub + SIB-5 + SIB-1 SSE parity + prompt tighten)   ── LAST (most regression-sensitive; touches the shipped 2244ad4 scrub chokepoint)
```

**Why this order:**
- WS-1 first — both `is_supplement_query` and `is_high_value_query` live in `price_service.py` and are **coupled** (the supplement short-circuit must repoint to the narrowed `is_high_value_query`); doing them in one wave avoids a two-writer race on the same file and a split-brain predicate. Lowest regression risk (pure functions, fully unit-pinnable).
- WS-2 second — the scs `:3910` category gate calls `is_supplement_query` and the EL-2-gated drops at `:4097/4315/4485/4768` call `is_implausible_high_value_price`; both must see WS-1's new behavior. WS-2 owns the **supplement sub-region** of scs.
- WS-3 third — owns the **non-supplement price-cascade region** of scs (fan_out seed, bahrain harvest, negcache). File-overlaps scs with WS-2 but **non-overlapping line regions** — still sequential (one writer at a time) to keep per-task path-restricted commits clean.
- WS-4 parallel-eligible-but-sequenced — own files (`source_router.py`, new test, new doc). No dep on WS-1/2/3. Placed 4th only for fan-out throttling; could swap with WS-3.
- WS-5 last — the honesty chokepoint is the most regression-sensitive surface (the shipped `test_response_builder_scrubs_score_leaks` canonical guard); landing it last means every other wave's tests are green before we touch it.

---

# WAVE WS-1 — Detector precision (price_service.py): supplement whole-token + EL-2 device-class split

**Fixes landed:** F1 (detector half: `is_supplement_query` rewrite, G2) + EL-2 (`is_high_value_query` split + `is_implausible_high_value_price` follows, G4) + the **mandatory coupled repoint** of the two short-circuits.

**Files + anchors (all `price_service.py`, exact at HEAD):**
- `:332-336` `HIGH_VALUE_KEYWORDS` def → split into `HIGH_VALUE_DEVICE_TOKENS` + `HIGH_VALUE_BRANDS` + `HIGH_VALUE_DEVICE_NOUNS`; keep a derived BC alias `HIGH_VALUE_KEYWORDS = HIGH_VALUE_DEVICE_TOKENS | HIGH_VALUE_BRANDS` (re-exported at `scs:1551`, imported `scs:718` — must not break `self.HIGH_VALUE_KEYWORDS`).
- `:404-411` `SUPPLEMENT_KEYWORDS` → split into `SUPPLEMENT_UNAMBIGUOUS` (incl. supp-brand subset) + `SUPPLEMENT_AMBIGUOUS` + add `SUPPLEMENT_DOSE_RE`, `SUPPLEMENT_FORM_TOKENS`.
- `:544-547` `is_high_value_query` → device-token-always-true, bare-brand-requires-(device-noun OR `_PHONE_MODEL_RE`).
- `:563-570` `is_implausible_high_value_price` → unchanged body (calls `is_high_value_query`, inherits the narrowing automatically).
- `:579-584` `is_supplement_query` → whole-token + corroboration rewrite; **repoint short-circuit to `if is_high_value_query(product_name): return False`** (NOT the raw set) — OR drop the short-circuit entirely (redundant under whole-token).
- `:639` `is_fragrance_query` short-circuit → **repoint to `is_high_value_query()` too** (mandatory coupled edit — same split bypass risk).
- `:2760 / :2798 / :2800` (`extract_price_from_shopping`) — `is_hv` drives `min_price=100` (`:2798`) AND `strict_title_match`-gating (`:2800`). NO code change here, but these are **3 behaviors riding the one narrowed predicate** — they must be re-pinned (the narrowing relaxes both for now-non-HV accessories; that is the intended EL-2 win).

**Design specifics (from Finder 1 + Finder 3, RESOLVED):**

*Supplement detector (G2):*
- `SUPPLEMENT_UNAMBIGUOUS` MUST include the sports/supp brands so existing regression tests hold: **`nordic naturals`, `centrum`, `now foods`, `solgar`, `nature made`, `optimum nutrition`, `dymatize`, `myprotein`, `muscletech`** (+ the rest from Finder 1 §2b). **This is the single highest-risk omission** — `test_error_paths.py:104` asserts `Nordic Naturals Omega-3 → True`; under strict corroboration it breaks unless `nordic naturals` is UNAMBIGUOUS.
- `SUPPLEMENT_AMBIGUOUS` = `{iron, collagen, protein, zinc, calcium, omega, omega-3, magnesium, mineral, d3, d-3, b12, b-12, potassium, whey}` → match ONLY with a co-occurring dose (`SUPPLEMENT_DOSE_RE`) OR form token OR supp-brand.
- Word-boundary via lookaround `(?<![a-z0-9])...(?![a-z0-9])` (NOT `\b`) so `d3`/`d-3`/`omega-3` match cleanly and `iron` does NOT match "environment".
- `Optimum Nutrition Whey Protein` resolves True via the **brand** (closing token), not the ambiguous "protein".

*EL-2 split (G4):*
- `HIGH_VALUE_DEVICE_TOKENS` = `{iphone, pixel, macbook, ipad, laptop, playstation, xbox, nintendo, rtx, geforce, radeon, gpu}` (self-identifying — always HV).
- `HIGH_VALUE_BRANDS` = `{samsung, galaxy, xiaomi, huawei, oneplus, nvidia, amd}` (HV only with a device signal).
- `HIGH_VALUE_DEVICE_NOUNS` = `{phone, smartphone, laptop, notebook, ultrabook, tablet, console, tv, television, graphics card, gpu, monitor}` — **explicitly EXCLUDE `watch`/`buds`/`band`/`fit`** (those are the accessory classes the floor must NOT catch).
- `_PHONE_MODEL_RE` — confirms a flagship device even without a device noun ("Samsung Galaxy S24" has NO device noun). From Finder 3 §3. **Load-bearing + brittle** — must NOT match accessory model contexts (`Mi Band 8`). Gate the regex behind "no accessory-noun present" OR exclude band/watch/buds/fit from the model pattern.
- BC alias retained; re-export `HIGH_VALUE_DEVICE_TOKENS`/`HIGH_VALUE_BRANDS` from scs too if any test imports them.

**Cross-fix interaction (DISPATCHER-GATE — see Open Questions Q1):** WS-1 does the narrowing AND the repoint in the same wave, so there is no split-brain window. The supplement detector under whole-token matching no longer *needs* the short-circuit (no electronics token = no supplement token). **Recommended: drop the `is_high_value_query` short-circuit from the rewritten `is_supplement_query` entirely** and pin `Samsung Galaxy S24 → False` / `iPhone 16 Pro → False` to prove decoupling. If kept, it MUST call `is_high_value_query()` not the raw set.

**TEST CONTRACTS (TDD — write first, `tests/test_el2_device_class_floor.py` + extend `tests/test_supplement_detector_precision.py` [new]):**

EL-2 floor predicate:
- `test_is_high_value_query_device_class` (parametrized): `Samsung 25W charger→False`, `Samsung Galaxy S24→True`, `Samsung Galaxy Buds2 Pro→False`, `Samsung Galaxy Watch 6→False`, `Xiaomi Mi Band 8→False`, `iPhone 15→True`, `MacBook Air M3→True`, `NVIDIA RTX 4090→True` (device-token path), `PlayStation 5→True`, `Sony WH-1000XM5 headphones→False` (documents non-covered gap).
- `test_charger_not_floored` — `is_implausible_high_value_price("Samsung 25W charger", 8.0) is False`.
- `test_s24_floored` — `is_implausible_high_value_price("Samsung Galaxy S24", 11.9) is True` (the load-bearing model-regex case; floor protects the genuine flagship from an 11.9 case-scrape).
- `test_phone_model_regex_excludes_accessories` — `Xiaomi Mi Band 8`/`Galaxy Watch 6`/`Galaxy Buds` do NOT match `_PHONE_MODEL_RE`.

Supplement detector (G2):
- `test_supplement_unambiguous_tokens` — `Vitamin D3 5000 IU`, `Centrum Multivitamin`, `NOW Vitamin D-3 5000 IU` → True.
- `test_supplement_ambiguous_needs_corroboration` — `Tefal steam iron`, `collagen serum`, `protein shaker`, `protein bar`, `cast iron skillet`, `calcium antacid` → **False**; `Solgar Magnesium Citrate 200mg`, `NOW Foods Omega-3 1000mg softgels` → True.
- `test_supplement_brand_corroboration` — `Optimum Nutrition Whey Protein → True` (brand closes it), `Nordic Naturals Omega-3 → True` (brand), `Garden of Life Protein → True`.
- `test_word_boundary_no_substring` — `environmental sensor`, `food container` → False (no `iron`/false match).
- `test_supplement_short_circuit_decoupled` (or `_repointed`) — `iPhone 15→False`, `Samsung Galaxy S24→False`, `NOW Foods Omega-3 1000mg softgels→True`.

Downstream `min_price` integration pins:
- `test_charger_survives_min_price_filter` — an 8-BHD Samsung-charger shopping candidate survives `extract_price_from_shopping` (`min_price` no longer 100).
- `test_s24_under_100_dropped` — an 11.9-BHD S24 candidate still dropped by `min_price`.

**REGRESSION GUARDS to re-run (HARD — these break silently):**
- `tests/test_error_paths.py::TestIsSupplementQuery` (the `Nordic Naturals Omega-3→True` pin)
- `tests/test_price_fallback.py::TestSupplementRouting`
- `tests/test_category_canonicalization.py::test_classify_category_from_text*` (`is_supplement_query` is double-used by `extraction_service.py:802` classifier — `NOW Foods Vitamin D3→supplements`, `Centrum Multivitamin tablets→supplements` must hold)
- `tests/test_eval_genuine_methods_parity.py` (floor change must not let a wrong scrape become genuine)

**Dependencies:** none (lowest in the graph).

---

# WAVE WS-2 — Supplement branch: category gate + bounded stages + trustworthy park + CDE-2 (scs supplement region)

**Fixes landed:** F1 (routing half: the `:3910` category gate) + supplement-fallback (per-stage `wait_for` T1/T2/T3 + trustworthy park + G1 terminal in `_price_fallback_on_miss`) + CDE-2 (deterministic retailer attribution) + SIB-4/SIB-5-adjacent terminal fix (the bare-`None` → pending at `_price_fallback_on_miss`).

**Files + anchors (`structured_comparison_service.py`, the supplement sub-region + the shared `_price_fallback_on_miss`):**
- `:3910` — the misroute OR → category gate:
  ```python
  is_supplement = (
      (category == "supplements")
      or (category in ("other", None) and is_supplement_query(full_name))
  )
  ```
  **Highest-value/lowest-risk ~3 LOC.** Trust a concrete non-supplement LLM/catfix category; only consult the name-keyword OR when unresolved.
- `:3828-3846` `_price_fallback_on_miss` — **G1 chokepoint terminal fix:** when `key=="price"` and nothing parked, return `make_pending_price(reason="pending_genuine")` instead of bare `None`. This covers EVERY price-key timeout (supplement + non-supplement) — the FE never gets a `null` that renders "N/A".
- `:4639-4695` supplement branch — wrap each await in per-stage `asyncio.wait_for` (NONE exist today, grep-confirmed):
  - Stage 1 iHerb (`:4651` `fetch_iherb_price`) → `wait_for(..., 4.0)` + TimeoutError→None. **Also shrink the inner `curl_requests.get(timeout=15)` at `price_service.py:3743` → ~4s** (the `run_in_executor` future can't hard-cancel; the inner timeout must shrink to avoid a leaked thread).
  - Stage 2+3 pharmacy (`gather` at `:4665-4667` + `fetch_pharmacy_price` at `:4673`) → wrap `fetch_pharmacy_price` in `wait_for(..., 5.0)` (guards the 2×3×10≈60s worst case at `price_service.py:3934/3951/3970`). Optionally bound the `gather` at `:4667` with `wait_for(..., 4.0)`.
  - Stage 4 page-loop (`:4679-4689`, `(iherb_organic+bh_organic)[:5]`) → extract into a small inner coroutine, wrap `wait_for(..., 3.0)`.
  - Net worst-case ≈ 4+5+3+GPT(~2-4) ≈ 14-16s → the outer 15s `_PRICE_RACE_TIMEOUT` becomes a backstop, not the primary failure.
- **Trustworthy park (G3):** at each supplement stage that yields a price (iHerb `:4652-4663`, pharmacy `:4674-4677`, page-scrape `:4686-4689`, GPT-with-real-retailer), stash into `self._parked_price[full_name]` BEFORE continuing — **gated by `is_price_showable(full_name, price)`** (NOT a hand-rolled `retailer and url`), so the park inherits the shipped sample/decant/accessory/haircare guards. A retailer-less `gpt_organic_extract` is NEVER parked.
- **CDE-2 (G3) at `:4716`** — `_has_retailer = bool(price.get("retailer")) or (is_supplement and iherb_organic)`. When `price.get("amount")` AND `not price.get("retailer")` AND `iherb_organic` empty: attribute a retailer ONLY from a deterministically matched `bh_organic` item — derive `domain = urlparse(link).netloc.replace("www.","")`, accept ONLY if domain ∈ `PHARMACY_DOMAINS` (`price_service.py:417-421`) OR `known_supplement_retailers` (`scs:4680`) AND the extracted price ties to that item (title/snippet brand+name token-match OR the GPT `source`/`url` already in that item). If matched → set `retailer`/`url`/`source_method="local_bhd"` → showable+parkable. NO deterministic match → leave `gpt_organic_extract` (pends). NEVER guess.
- **Reject-reason tracing (optional, flag-gated):** reuse `DEBUG_STAGE_TIMINGS` pattern OR add `DEBUG_SUPPL_REJECT` checked once at branch entry; one `logger.info("[SUPPL_REJECT] stage=%s reason=%s name=%s")` per drop point. No-op in prod.

**REFUTED / do-NOT-do (carry from Finder 2):**
- **DM-1 is REFUTED** — the render escalation (`scs:4149-4630`) is NOT `is_supplement`-gated and runs BEFORE the supplement branch. Do NOT "wire render into supplements."
- The `scs:4856 {"amount":None,...}` empty-dict terminal is ALREADY pended by response_builder (it's a dict). The ONLY un-pended terminal is the bare `None` from `_price_fallback_on_miss` on timeout — fixed above.

**TEST CONTRACTS (TDD — `tests/test_supplement_branch_genuine.py` [new]):**
- `test_supplement_category_gate_trusts_concrete_category` — `category="electronics"` + a name with a supplement substring → `is_supplement` False (routing layer, pins the `:3910` gate).
- `test_supplement_timeout_returns_pending_not_none` — mock iHerb/pharmacy/page to hang past their `wait_for` bounds (or patch `_PHASE1_TIMEOUTS["price"]` low) → `result["price"]` is `{amount:None, unavailable:True, reason:"pending_genuine"}`, NOT `None` (G1; pins `_price_fallback_on_miss`).
- `test_supplement_iherb_hit_is_parked_and_returned` — iHerb returns price w/ retailer+url+amount → `self._parked_price[full_name]` populated AND a forced cancel → `_price_fallback_on_miss` returns the parked price (not None).
- `test_retailerless_gpt_extract_pends_not_parked_not_shown` — iHerb/pharmacy/page miss, `extract_price` returns amount + `retailer=None`, no deterministic match → `source_method=="gpt_organic_extract"`, `is_price_showable` False, NOT in `_parked_price`, final FE price pending (G3+G1).
- `test_cde2_attributes_retailer_from_matched_bh_organic_snippet` — iHerb organic empty; `bh_organic` has an item whose `link` domain ∈ `PHARMACY_DOMAINS` + title brand/name match; GPT amount + `retailer=None` → relabeled `local_bhd`, retailer=pharmacy name, url=snippet link, showable, parked. NEGATIVE half: domain NOT a known BH retailer → stays unassigned, pends (no guessed attribution).
- `test_supplement_substage_wait_for_bounds` — patch a stage to sleep > its `wait_for` → stage bypassed (returns None), chain proceeds to next stage rather than blowing the 15s cap.

**REGRESSION GUARDS:** `tests/test_price_fallback.py`, `tests/test_price_showable.py` (full), `tests/test_explicit_pair_category.py` (catfix FIX-1 routing), `tests/test_category_canonicalization.py`.

**Dependencies:** WS-1 (reads the rewritten `is_supplement_query`; the `:3910` gate behavior depends on the corroboration logic being correct).

---

# WAVE WS-3 — Genuine-reach in the price cascade (scs non-supplement region): CDE-3 + DM-3 + CDE-4

**Fixes landed:** CDE-3 (seed `self._price_candidates` from short-circuit/Tier-1 — the **FULL candidate set**, not the winner) + DM-3 (`bh['organic'][:4]→[:8]`) + CDE-4 (don't 30d-negative-cache a guard-rejected estimate).

**Files + anchors (`structured_comparison_service.py`, the price-cascade/discovery region — NON-overlapping line spans with WS-2):**

*CDE-3 (CONFIRMED + SHARPENED — winner-only seed is a NO-OP, see Open Questions Q2):*
- Existing seed (the ONLY one): `:4593` `self._price_candidates.setdefault(full_name, []).extend(_retained)` (fan_out only).
- Consumers: `:2293` (sync) / `:2780` (stream) `reconcile_pair_fairness(..., candidates_by_name=self._price_candidates)`.
- Short-circuit returns that bypass seeding: `:4128` (Tier-1 Serper Shopping), `:4263` (Shopify `/products.json`), `:4347` (Algolia), `:3871-3873`/`:3879-3883` (L1/L2 cache hit), page-scrape `:4801-4804`.
- **FIX:** on each short-circuit path (except cache hits — documented residual), seed `self._price_candidates[full_name]` with the **full viable candidate set the path observed**, normalized to the fan_out candidate shape (`{value/size, source_method, retailer, title, raw_data}` per `reselect_to_target_value:1884-1901`, carry `raw_data`=the price dict so the genuine `source_method` survives the `is_price_showable` gate at `:1905`). Tier-1 → `self._shopping_items_cache[full_name]` items that pass `is_price_showable`. Shopify/Algolia → the parsed alternates list (NOT only `shop_best`/`algolia_best`). Fail-open `try/except pass` (mirror `:4586-4595`). NO new network. G1 (only real candidates) + G3 (`is_price_showable` gate).

*DM-3 (CONFIRMED — domain diversity, not result count):*
- `:1312` `for item in bh["organic"][:4]:` → `[:8]`. The sitelink sub-loop at `:1318-1320` extends automatically. `limit=8` at `:4387-4389` queries up to 8 distinct BH registry domains (`source_router.py:655-674` `[:limit]`); top-4 are often 1-2 dominant domains → genuine PDPs from the other queried domains land at 5-8 and are silently dropped. Downstream gate (`scs:1292-1307`: `validate_scrape_url`, reject review-only, reject variant-mismatch, **require `weight≥1.5`**) rejects noise. Leave official `[:2]`/authorized `[:5]`/gcc `[:3]` unchanged (bahrain-only scope).

*CDE-4 (CONFIRMED narrow residual — no flag distinguishes guard-reject-estimate from structural-estimate today):*
- Guard-rejects returning None: `:4491` (`is_implausible_high_value_price`) + `:4504` (`is_implausible_low_fragrance_price`).
- Negcache writes: `:4819` (converted_fallback — **DO NOT TOUCH, SF-1-exempt**) + `:4852` (Tier-3 estimate).
- `_record_negative_price_cache` `:5061-5079`, gated `should_negative_cache` (`price_service.py:200-207`; `converted_usd→False :204-205`, `estimated→True :206-207`), 30d TTL `price_service.py:138`. Suppression on next request `:3891-3901`.
- **FIX:** thread a closure-local `nonlocal _guard_rejected_this_request=False` set True at `:4491`/`:4504`; at `:4852` pass `_record_negative_price_cache(..., suppress_if=_guard_rejected_this_request)` → skip the sentinel (or cap TTL to 24h `PRICE_CACHE_TTL`) so a later-correct PDP isn't suppressed 30d. Do NOT touch the converted path. G1/no-fab preserved (just re-runs the cascade next time).

**TEST CONTRACTS (TDD — `tests/test_genuine_reach_cascade.py` [new]):**

CDE-3:
- `test_cde3_tier1_shortcircuit_seeds_candidates` — fragrance pair, A wins via Tier-1 short-circuit holding 50ml AND 100ml shopping_items, common target 50ml → A NOT pended (re-selected) where pre-fix it pended.
- `test_cde3_single_candidate_still_pends_honestly` — A holds only a 100ml short-circuit price, target 50ml, no 50ml candidate → still pends (G1 — no fabrication; documents residual).
- `test_cde3_at_target_shortcircuit_noop` — A's price already at target → no re-selection, byte-identical price (tolerance pass-through regression guard).
- `test_cde3_no_seed_on_cache_hit_documented` — L1 cache-hit path remains un-seeded (asserts the documented residual, not a regression).

DM-3:
- `test_dm3_harvests_bh_pdp_at_position_5_8` — `results_by_tier["bahrain"]["organic"]` with positions 1-4 dominant-domain non-PDP/weight<1.5 and position 6 a genuine registry PDP (weight≥1.5) → position-6 PDP harvested post-fix.
- `test_dm3_position_5_8_noise_rejected` — position-6 off-registry marketplace URL (weight<1.5) → still rejected.
- `test_dm3_variant_mismatch_still_rejected_in_window` — a position-7 "iPhone 15 Pro Max" PDP for an "iPhone 15" query → rejected by `variant_mismatch`.

CDE-4:
- `test_cde4_guard_reject_skips_30d_negcache` — fan_out winner rejected by `is_implausible_high_value_price` → Tier-3 estimate → `set_negative_cache` NOT called with 30d TTL (skipped or 24h).
- `test_cde4_genuine_structural_miss_still_negcaches` — fan_out genuinely empty (no winner, no reject) → Tier-3 estimate → 30d sentinel IS written (Task 1.3 preserved — don't over-correct).
- `test_cde4_converted_path_unchanged` — parked converted_fallback resolves → `should_negative_cache` still False (SF-1 regression guard, byte-identical).
- `test_cde4_later_correct_pdp_not_suppressed` — after a guard-reject request, a 2nd request with a now-valid PDP re-runs the cascade (no sentinel hit) → genuine price.

**REGRESSION GUARDS:** `tests/test_price_size_reconcile.py`, `tests/test_pair_size_basis_fairness.py`, `tests/test_eval_genuine_methods_parity.py`, the SF-1 converted_usd guards.

**Dependencies:** WS-1 (CDE-4 reads `is_implausible_high_value_price`; the guard-reject sites call the narrowed predicate). Soft-dep on WS-2 (same file, sequential — but non-overlapping line regions).

---

# WAVE WS-4 — Source registry + all-category matrix (source_router.py + new test + new doc): F8 + WS-F + WS-G

**Fixes landed:** F8 (`aldeerahpharmacy.com` registry row — verify-or-omit) + WS-F (G6 drift-guard test + KNOWN_SOURCE_GAPS + contract doc) + WS-G (candidate-adapter liveness contracts, verify-or-omit).

**Files + anchors:**
- `source_router.py:57-252` `SOURCE_REGISTRY` — add the F8 row IFF the WS-G liveness probe passes (see below). Confirmed absent today (0 grep hits for `aldeerah`).
- `price_service.py:303` (search template) + `:420` (`PHARMACY_DOMAINS`) — already present; no change.
- NEW `tests/test_bahrain_source_matrix_coverage.py` — the drift-guard.
- NEW `docs/contracts/bahrain-source-matrix.md` — the contract doc (precedent: `docs/contracts/d2-error-contract.md`).

### THE REAL ALL-CATEGORY MATRIX (gated vs the actual `SOURCE_REGISTRY`, for the contract doc)

Canonical 9-category set = `frozenset(CATEGORY_SPEC_SCHEMAS.keys())` (`extraction_service.py:101`) = `{electronics, grocery, supplements, other, makeup, skincare, haircare, fragrances, fashion}` (== `CATEGORY_FAIRNESS` keys at `price_service.py:1543`).

Live-reach for genuine BHD requires column (a) curl/JSON-LD, (b) Shopify-json, or (c) Algolia. `is_render_only` (d) and `requires_super` (e) are NOT genuine on live traffic today.

| Category | (a) curl/JSON-LD genuine | (b) Shopify-json | (c) Algolia | (d) render-only (starved) | (e) super-OFF / CF-walled | (f) fallback | (g) KNOWN GAP |
|---|---|---|---|---|---|---|---|
| **electronics** | sharafdg.com, extra.com, microless.com, lulu | shopalmoayyed, sonyworld.bh | — | noon.com | — | converted_usd→estimated→pending | mid-tier accessories dropped by EL-2 floor (G4 fixes); official brand sites global→converted |
| **grocery** | lulu, bateel.bh, talabat.com | — | — | megamart.bh, alosraonline.com | — | converted_usd→estimated→pending | none structural — strongest curl coverage |
| **supplements** | bahrainpharmacy.com, lulu (+ iHerb `bh.iherb.com` curl, separate branch) | — | — | bn.boots.com, bolo.bh, nasserpharmacy.com | — | iHerb→pharmacy→converted→estimated→pending(post-WS-2) | F1 misroute + T1/T2/T3 timeout + no parked fallback (WS-2 fixes); aldeerah curl source ABSENT (F8) |
| **makeup** | bahrainpharmacy.com, ounass.bh, lulu | — | — | bn.boots, bolo, nasserpharmacy | sephora.bh, boutiqaat | converted_usd→estimated→pending | Western drugstore→converted; CF-walled premium structural |
| **skincare** | bahrainpharmacy.com, lulu | — | — | bn.boots, bolo, nasserpharmacy | sephora.bh, boutiqaat | converted_usd→estimated→pending | only ONE curl source; most resolve converted |
| **haircare** | bahrainpharmacy.com (registered; JSON-LD reach unproven), lulu | — | — | bn.boots, nasserpharmacy | boutiqaat | converted_usd→estimated→pending | thin curl reach; premium→converted/render-only |
| **fragrances** | bahrain.ounass.com, jalilaperfumes.com, lulu | asgharali, ajmal (en-bh), alhajis | — | nasserpharmacy | sephora.bh, boutiqaat | converted_usd→estimated→pending | Western luxury (Tom Ford/Creed/Chanel)→converted/estimated; Eastern/local genuine via Shopify |
| **fashion** | bahrain.ounass.com, lulu | — | en-bh.6thstreet.com | — | — | converted_usd→estimated→pending | THIN (2 curl + 1 Algolia); namshi BH un-wired (F6/WS-G) |
| **other** | lulu (only — all-category row) | — | — | — | — | converted_usd→estimated→pending | THINNEST — one source; mitigation is upstream category resolution (F1) |

**PART E corrections (vs the design's matrix):** (1) `bahrainpharmacy.com` is registered for **makeup AND haircare AND skincare AND supplements** (`source_router.py:126`) — broader curl source than credited; (2) `ounass.bh` does NOT cover skincare/haircare (only fashion/fragrances/makeup, `:201-204`); (3) `jalilaperfumes` is a plain-curl row (no `is_shopify`).

**Cross-cutting (gated):** NO `/sitemap.xml` discovery (F5, structural, permanent); `is_render_only` rows dead on the live 12s clock (T4); `requires_super` rows filtered out when `SCRAPEDO_SUPER` OFF (`get_sources_for_category:367-374`, fail-closed); iHerb is a separate supplement branch NOT routed through `get_sources_for_category`.

### THE DRIFT-GUARD TEST (`tests/test_bahrain_source_matrix_coverage.py`)

Genuine-BH-capable predicate: a category is COVERED iff `get_sources_for_category(cat)` (called with `SCRAPEDO_SUPER` in its default-OFF state) yields ≥1 **bahrain-tier** source that is NOT `is_render_only` AND NOT `requires_super` (i.e. curl/JSON-LD OR `is_shopify` OR `is_algolia`).

```python
"""WS-F (G6) drift-guard: every CATEGORY_SPEC_SCHEMAS category must map to >=1
registered genuine-BH-capable source (curl/JSON-LD, Shopify, or Algolia, bahrain
tier, live on the 12s clock) OR be in KNOWN_SOURCE_GAPS with a reason.
Render-only / super rows are DEAD on live traffic (T4 / SCRAPEDO_SUPER OFF) —
they do NOT count as genuine-capable here."""
from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS
from app.services.source_router import get_sources_for_category

CANONICAL_CATEGORIES = frozenset(CATEGORY_SPEC_SCHEMAS.keys())

# A category with NO live-reachable genuine-BH source today. Each entry MUST
# carry a reason. EMPTY today: gcc.luluhypermarket.com (empty categories tuple,
# bahrain tier, curl) is genuine-capable for EVERY category. This set is the
# SAFETY NET: a future edit that strands a category must record the gap WITH A
# REASON, never silently drop to converted/None.
KNOWN_SOURCE_GAPS: dict[str, str] = {}

def _genuine_bh_capable(category: str) -> bool:
    for s in get_sources_for_category(category):
        if s.tier != "bahrain":
            continue
        if s.is_render_only or s.requires_super:
            continue  # dead on live traffic
        return True
    return False

def test_every_category_has_a_genuine_bh_source_or_explicit_gap():
    uncovered = []
    for cat in sorted(CANONICAL_CATEGORIES):
        if _genuine_bh_capable(cat):
            continue
        if cat in KNOWN_SOURCE_GAPS:
            assert KNOWN_SOURCE_GAPS[cat], f"{cat} gap needs a non-empty reason"
            continue
        uncovered.append(cat)
    assert not uncovered, (
        "Categories with NO live-reachable genuine-BH source and NOT in "
        f"KNOWN_SOURCE_GAPS: {uncovered}.")

def test_known_source_gaps_are_real_gaps():
    for cat in KNOWN_SOURCE_GAPS:
        assert cat in CANONICAL_CATEGORIES, f"unknown category in gaps: {cat}"
        assert not _genuine_bh_capable(cat), (
            f"{cat} is in KNOWN_SOURCE_GAPS but DOES have a live genuine-BH "
            "source now — remove the stale gap entry.")

def test_canonical_set_is_the_nine_schema_keys():
    assert CANONICAL_CATEGORIES == frozenset(CATEGORY_SPEC_SCHEMAS.keys())
    assert len(CANONICAL_CATEGORIES) == 9
```

**Recommended SECOND (strict) test** (DISPATCHER-GATE Q5): the lenient guard passes trivially on lulu's all-category reach — it proves "a path EXISTS" not "the path produces genuine BHD." Add `test_every_category_has_a_category_specific_bh_source_or_gap` that excludes empty-`categories`-tuple all-category rows (lulu) → surfaces `other` (lulu-only) and `haircare` (bahrainpharmacy-only, reach-unproven) as documented thin spots via `KNOWN_SOURCE_GAPS` reasons. Ship BOTH: lenient gates merges (no false reds); strict documents thinness.

Also: `test_f8_aldeerah_in_registry_iff_verified` + `test_f8_registry_pharmacy_domain_parity` (every `PHARMACY_DOMAINS` key with a real storefront is in `SOURCE_REGISTRY` or `KNOWN_SOURCE_GAPS`).

### WS-G — CANDIDATE LIVENESS-CHECK LIST (verify-or-omit, G7 — **a SEPARATE verify step before ANY registry row**)

Adapters ship **verify-or-omit**: each row lands ONLY after a passing `scripts/verify_source_registry.py` run (HEAD-resolve + control-calibrate: controls `google.com` + `shopalmoayyed.com` must be 200 in-env FIRST; `403/405/429`=ALIVE; NXDOMAIN/non-alive=DEAD — the I5.3 sandbox-DNS guard at `source_router.py:59-65`) PLUS the category-specific positive+negative price gate below. Unverified → recorded in `KNOWN_SOURCE_GAPS` with reason, NOT shipped. **These are liveness STEPS, not a code deliverable — the implement agent runs the probe, then either adds the row (verified) or records the gap.**

| Candidate | Wiring target | Liveness contract (ALL must pass before the row ships) |
|---|---|---|
| **aldeerah** `aldeerahpharmacy.com` (F8) | `Source("aldeerahpharmacy.com","bahrain",("supplements","skincare","makeup","haircare"),3.0)` [+`is_render_only=True` iff JS-rendered] | (1) `verify_source_registry` HEAD-200/403. (2) Curl a real PDP (via `catalogsearch/result/?q=` template) through `extract_price_from_html` → static BHD JSON-LD/OG price → plain row; if JS-SPA no static price → `is_render_only=True` (warmer-only). (3) Confirm it actually stocks the claimed categories (Magento — check for an Algolia index too; prefer Algolia path if present). OMIT/render-flag per result. |
| **namshi BH** `en-bahrain.namshi.com` (F6) | one `ALGOLIA_STORES` row (`algolia_service.py:53`) + registry `Source(is_algolia=True,tier="bahrain",categories=("fashion",))` | (1) HEAD-200/403. (2) `extract_algolia_config(page_html, chunk_js)` returns non-None `{app_id,api_key,index}` with a **BHD/`_bh_`/bahrain index** (NOT the AE index). (3) Positive: `fetch_algolia_price("Nike Air Max", domain)` → genuine BHD + passing `strict_title_match` (mirrors the 6thStreet proof). (4) Negative: a cross-category query does NOT return a fashion mis-match (scope to `("fashion",)` if BH makeup rides a separate index). OMIT if app-id/index unharvestable OR AE-only. |
| **rivolishop.com** (fashion) | `Source(...,"bahrain",("fashion",),...)` IF curl-capable | HEAD-200/403; confirm a **BH/BHD** storefront exists (not UAE/AED-only); curl PDP→static BHD price (else render-flag); platform check (Shopify→`is_shopify`, Algolia→`ALGOLIA_STORES`). OMIT if AED-only or no static price. |
| **level-shoes BH** (`level-shoes.com` is in `GCC_LUXURY_RETAILERS:399`) | `Source(...,"bahrain"/"gcc",("fashion","fragrances"?),...)` | HEAD-200/403 on BH-locale URL; confirm `level-shoes.com/en-bh/` BHD catalog exists; curl PDP→static JSON-LD (luxury SPA likely render-only→warmer-only). OMIT if no BH locale or no static price. |
| **bathandbodyworks.com.bh** (makeup/skincare/haircare/body) | `Source("bathandbodyworks.com.bh","bahrain",("makeup","skincare","haircare"),3.0)` IF curl-capable | HEAD-200/403; curl PDP→static BHD price (Shopify→`/products.json` `is_shopify=True`); confirm displayed currency is BHD. OMIT if NXDOMAIN or AED/render-only-only. |

**Contract doc structure (`docs/contracts/bahrain-source-matrix.md`):** (1) header/invariants + genuine-capable definition; (2) the matrix table above; (3) live-reach legend; (4) KNOWN GAPS mirroring the test; (5) WS-G candidate-adapter pipeline table; (6) drift-guard reference; (7) **WS-H — `SCRAPEDO_SUPER` 5-point experiment protocol** (super-rows are a registry concern, so this is the doc's natural home): fixed small query set targeting `requires_super` rows (sephora.bh/boutiqaat) → inspect `metadata.source_trace…attempts` provider trace (G4 measured super NEVER fired across 9 nocache pulls — baseline to beat) → per-run Scrape.do credit cap → explicit before/after genuine-share evidence → immediate `SCRAPEDO_SUPER=false` revert if no confirmed BH-PDP win.

**TEST CONTRACTS:** the drift-guard tests above + the F8 parity tests. **No live-network tests in the free-unit tier** — WS-G liveness is a `scripts/verify_source_registry.py` run the implement agent executes manually, recorded in the commit message / gap reasons.

**REGRESSION GUARDS:** `tests/test_eval_genuine_methods_parity.py`, any existing `source_router`/registry tests, `tests/test_migration_index_predicate_immutability.py` pattern (static-guard idiom reference only).

**Dependencies:** none on WS-1/2/3 (own files). Sequence 4th for fan-out throttling.

---

# WAVE WS-5 — Honesty (G5): widened scrub + SIB-5 None→pending + SIB-1 SSE parity + prompt tighten (response_builder.py + extraction_service.py + scs SSE event)

**LAST wave — most regression-sensitive (touches the shipped `2244ad4` scrub chokepoint).** Fixes: SIB-4 (widen the score-internals scrub to EVERY user-visible GPT text field) + SIB-5 (raw None/non-dict price → pending shape, G1) + SIB-1 (SSE prices event uses the SAME pending projection, G5) + the tightened prompt rule.

**Files + anchors:**
- `app/services/response_builder.py` — the single chokepoint `build_comparison_response` (`:1055-1613`):
  - SIB-4 widened scrub: insert a new block AFTER the pros/cons scrub (`:1242-1250`) and BEFORE the `result = {...}` assembly, mutating the SOURCE `comparison` keys in place (so every downstream surface — dedicated slot AND `result["comparison"]` BC alias — is clean in one pass).
  - SIB-5: `:1212` `if not isinstance(_price, dict): continue` → normalize to `make_pending_price(currency="BHD", reason="pending_genuine")` + null `best_price`/`retailer`, then `continue`.
- `app/services/structured_comparison_service.py` — SIB-1: `:2806-2813` SSE `prices` event → apply the SAME projection (`is_price_showable`→`make_pending_price`) onto a COPY before yield (mirror the FIX-2 NO-FAB rating guard at `:2827`).
- `app/services/extraction_service.py` — prompt tighten: `:646`, `:654` (neutralize the "with specific number" invitations), `:672` (widen the forbidden-words rule to ALL fields).

### THE COMPLETE USER-VISIBLE GPT-FIELD ENUMERATION (G5 — implementers need the FULL list)

`build_comparison_response` is the single chokepoint for sync + streaming `complete`. Every field carrying free GPT text a user can see:

**Already SCRUBBED (pass through `has_score_internals`/`strip_score_internals` — DO NOT regress):**
| Field path | Source | Scrub site |
|---|---|---|
| `overview.products[i].pros` / `.cons` | `pd["pros_cons"]` (← popped `comparison.product_N_pros/cons`) | `:1242-1250` (drop) |
| `overview.products[i].pros_cons.{pros,cons}` | same dict in-place | `:1242-1250` |
| `products[i].pros`/`.cons` (legacy alias) | same dict | `:1242-1250` in-place |
| `overview.winner.reason` | `comparison.winner_reason` | `:1282` (strip + qualitative fallback) |
| `overview.winner.declaration` | `comparison.winner_declaration` | `:1287` (strip + `""`) |
| `overview.winner.name` | `comparison.winner_declaration` | `:1290-1291` (strip + product-name fallback) |
| `overview.winner.key_tradeoff` | `comparison.key_tradeoff` | `:1286` (strip + `""`) |
| `recommendation` (top-level) | `_scrubbed_reason` | `:1600` |
| `comparison.winner_reason`/`.winner_declaration`/`.key_tradeoff` (BC alias) | `comparison` | `:1592-1596` |

**BYPASSING the scrub today — the SIB-4 leak set to FIX (scrub the SOURCE `comparison` keys in place):**
| # | Field path | Source line | Shape | Scrub strategy |
|---|---|---|---|---|
| B1 | `overview.products[i].value_context` | `:1344` (← `comparison.value_context` dict, `:1301-1310`) | string (per-product dict OR legacy string) | **STRIP** per value (`strip_score_internals`; `""` if fully leaked — FE tolerates) |
| B2 | `overview.products[i].best_for` | `:1352` (← `comparison.best_for.product_{i}`) | string (per-product dict) | **STRIP** per value |
| B3 | `specs.products[i].spec_advantages` | `:1390` (← `comparison.specs_comparison.product_{i}_advantages`) | list[str] | **DROP** leaker element (pros/cons semantics) |
| B4 | `specs.specs_comparison.product_0_advantages`/`product_1_advantages`/`similar` | `:1398-1401` (spread of `comparison.specs_comparison`) | lists | **DROP** (SAME source as B3 — scrubbing the source key cleans both surfaces) |
| B5 | `personalization.personalized_insights[].insight` | `:1462` (← `comparison.personalized_insights`) | list[dict], `.insight` GPT text | **STRIP** the `insight` sub-field (keep the item; FE skips blank insight) |
| B6 | `personalized_insights[].insight` (top-level alias) | `:1606` (SAME `comparison.personalized_insights`) | same | covered by scrubbing the source key |
| B7 | `comparison.value_context`/`.best_for`/`.specs_comparison`/`.personalized_insights` (BC alias) | `:1597` (`result["comparison"]=comparison`) | raw comparison dict | covered by mutating `comparison` in place (the `:1592-1596` alias scrub covers ONLY winner-text) |

**Drop-vs-strip:** value_context/best_for/personalized_insights.insight → STRIP (1-sentence fields, `""` if fully leaked, FE tolerant); spec_advantages/similar list items → DROP the whole element (an advantage that is purely a score is meaningless once the number is removed).

**Why mutate `comparison` in place (NOT the emit sites):** the four fields surface on BOTH a dedicated slot AND `result["comparison"]` (B7). One source-dict mutation before `result = {...}` is the single chokepoint; the `_value_context_for(i)` closure (`:1303-1310`), the `best_for`/`spec_advantages` reads, and `personalized_insights` (both `:1462` and `:1606`) then all read clean values, and `result["comparison"]=comparison` ships clean too. NO new bypass surface.

**REFUTED — do NOT widen there:** `product_N_pros/cons` are `.pop()`'d off `comparison` at `scs:2412-2417`/`2945-2950` → NOT on the BC alias → already safe.

**Lower-risk GPT fields (NOT confirmed leaks — defense-in-depth OPTIONAL, flag as out-of-scope-unless-cheap):** `reviews.products[i].review_summary.{consensus,highlights[]}` (governed by `_clean_review_citations`, review prompt never emits scores — a score in a highlight is theoretical only). `review_praise`/`retailer_quotes`/`variant`/`scoring_v2.factual_verdict` are deterministic or non-GPT — out of scope (but verify the existing `_compose_delta_text` qualitative behavior is not regressed).

### SIB-5 (None→pending, G1)

`:1212` — replace the `continue`:
```python
_price = pd_item.get("price")
if not isinstance(_price, dict):
    # SIB-5/G1 — a raw None / non-dict price (supplements-None,
    # _price_fallback_on_miss terminal) must render the calm pending line, not
    # the FE "N/A" branch (ResultsContent.tsx:128).
    pd_item["price"] = make_pending_price(currency="BHD", reason="pending_genuine")
    pd_item["best_price"] = None
    if "retailer" in pd_item:
        pd_item["retailer"] = None
    continue
```
Order is safe: runs INSIDE the price-pending `try` (`:1207-1231`), AFTER the estimated-note strip (`:1191`, dict-only) and `_compute_cache_observability` (`:60-70`, dict-guarded). `make_pending_price` import already in scope (`:1208`). **Belt-and-suspenders with WS-2's `_price_fallback_on_miss` terminal fix** — WS-2 makes the bare-None case impossible upstream; SIB-5 is the response_builder backstop. Both ship.

### SIB-1 (SSE prices parity, G5)

`scs:2806-2813` — apply the same projection per-product onto a COPY before `yield ("prices", prices_payload)` (mirror the reviews FIX-2 NO-FAB guard at `:2827`). Project so a sample/estimated price the final card pends is never briefly shown mid-stream; a raw None also pends (SIB-5 parity). **FE graceful:** `StreamingProductCard.tsx:92` gates on `product?.price?.amount != null` → a pending shape (`amount:None`+`unavailable:True`) keeps the slot hidden during streaming, then `complete` renders the calm line. **No FE code change** — but the SSE payload shape is FE-adjacent → an EAS preview verify is warranted (the existing build already tolerates `amount==null`; confirm `StreamingProductCard.tsx:49-50` marks `amount?` optional — it does).

### THE PROMPT TIGHTEN (extraction_service.py, two edits in `COMPARISON_SYSTEM`)

- Edit A (`:646`, `:654`) — neutralize the number-invitations to point at product facts, not scores:
  - `:646` → `"product_0_advantages": ["advantage citing a concrete product spec or measurement (e.g. '48MP camera', '5000mAh battery') — NEVER an internal score or point value"]`
  - `:654` → `"insight": "1-2 sentence insight citing a concrete product fact or spec figure (max 200 chars) — NEVER an internal score, point margin, or '/100' value"`
- Edit B (`:672`) — widen the forbidden-words rule to ALL fields (value_context, best_for, specs_comparison advantages, personalized_insights, in addition to winner_reason/key_tradeoff/winner_declaration/pros/cons).

Prompt = first line; the chokepoint scrub = fail-closed backstop (the shipped `text_sanitize.py` pattern — both ship).

**TEST CONTRACTS (TDD — add to `tests/test_fragrance_content_quality.py` + `tests/test_response_builder_*`):**

Widened scrub:
- `test_widened_scrub_value_context_per_product` — `comparison.value_context={"product_0":"...score of 100..."}` → `overview.products[0].value_context` clean AND `comparison.value_context` clean.
- `test_widened_scrub_best_for` — best_for leak → both surfaces clean.
- `test_widened_scrub_spec_advantages_drops_leaker` — `product_0_advantages=["+18pt longevity","Real 100ml"]` → only "Real 100ml" survives in `specs.products[0].spec_advantages` AND `specs.specs_comparison.product_0_advantages` AND the comparison alias.
- `test_widened_scrub_personalized_insights_insight` — insight with "overall score" → stripped on `personalization.personalized_insights` AND top-level alias AND BC comparison alias.
- `test_widened_scrub_value_context_legacy_string` — legacy string value_context leak → stripped.
- `test_widened_scrub_clean_fields_untouched` — clean value_context/best_for/advantages/insight survive verbatim (no over-scrub).

SIB-5:
- `test_response_builder_none_price_becomes_pending` — `price=None` → `unavailable:True`, `amount:None`, `reason:"pending_genuine"`.
- `test_response_builder_nondict_price_becomes_pending` — `price=42.0` (bare float) → pending shape (no raw float leak).
- `test_response_builder_none_price_suppresses_price_dim` — None price → Price dimension delta not asserted (pricePending path), best_price/retailer nulled.
- `test_response_builder_genuine_dict_price_unaffected` — genuine dict price passes through.

SIB-1:
- `test_sse_prices_event_pends_non_showable_price` — estimated/sample price → `("prices", payload)` carries `price.unavailable==True`/`amount None`.
- `test_sse_prices_event_passes_showable_genuine` — genuine local_bhd → real amount unchanged.
- `test_sse_prices_projection_does_not_mutate_product_data` — after the yield, `product_data[i]["price"]` is still the raw dict (COPY guard) so `complete` re-projection is correct.

Prompt:
- `test_comparison_prompt_forbids_scores_in_all_fields` — `COMPARISON_SYSTEM` mentions value_context/best_for/specs_comparison/personalized_insights in the forbidden-words rule; no bare "with specific number" without the "never a score" qualifier (extends `test_base_prompt_forbids_numeric_score_cite`).

**REGRESSION GUARDS — re-run ALL (G5 must not regress the `2244ad4` contract):**
- Score-leak/scrub: `test_strip_score_internals_removes_known_leaks`, `test_strip_score_internals_keeps_clean_facts`, `test_base_prompt_forbids_numeric_score_cite`, `test_scores_summary_has_no_raw_numbers`, `test_deterministic_partial_verdict_no_score_margin`, **`test_response_builder_scrubs_score_leaks` (the canonical guard — widened additions must EXTEND, not break it)**.
- +Npt qualitative: `test_compose_delta_text_no_point_unit_for_fragrance_dims`, `test_compose_delta_text_longevity_real_spec_phrase_survives`, `test_compose_delta_text_projection_reads_sillage_field`, all of `tests/test_compose_delta_text_per_category.py`.
- Price-pending: `test_verdict_safe_product_strips_pending_amount_without_mutating`, `test_verdict_safe_product_preserves_showable_price`, `test_comparison_system_forbids_price_claims_when_pending`, `test_response_builder_drops_price_adjective_for_pending_product`, `test_estimated_fragrance_becomes_pending`, `test_sample_decant_flagged_becomes_pending`, `test_sample_grade_low_fragrance_price_becomes_pending`, `test_genuine_bhd_passes_through`, `test_converted_usd_real_price_shown`, `test_electronics_genuine_unaffected`, **`test_c2_size_mismatch_reason_survives_c1_normalization` (SIB-5 must not clobber an upstream size_mismatch reason — guarded by `if _price.get("unavailable") is True: continue` at `:1218`)**, `test_pending_price_kills_cross_price_dimension_delta`.
- Review-grammar: all of `tests/test_review_paraphrase.py` + the `test_review_praise_*`/`test_frame_*`/`test_lower_first_*`/`test_strip_attribution_*` set in `test_fragrance_content_quality.py`.
- Showable/fairness (touched by SIB-1/SIB-5 imports): all of `tests/test_price_showable.py`, `tests/test_price_size_reconcile.py`, `tests/test_pair_size_basis_fairness.py`.

**Dependencies:** WS-2 (SIB-5 is the backstop to WS-2's `_price_fallback_on_miss` terminal — both must agree on `reason="pending_genuine"`). Last in the graph regardless.

---

## F1 UNIT-PIN SET (HARD CONTRACT — invisible to smoke20)

The gold-query misroutes are NOT in the smoke20 subset → **a green smoke20 is NOT proof for this class**. These MUST be unit-pinned at BOTH layers (the `is_supplement_query` function in WS-1 AND the routing through `_resolve_pair_category`/`is_supplement` at `scs:3910` in WS-2). The ultracode review caught exactly this class (catfix FIX-1) — treat it as a ship-blocker.

**MUST-NOT route to supplement branch** (function-level `is_supplement_query` → False AND routing-level → non-supplement):
`Tefal steam iron`, `collagen serum`, `protein shaker`, `protein bar`, `food container`, `cast iron skillet`, `calcium antacid`, `Vitamin C serum` (function may return True via "vitamin" UNAMBIGUOUS — that is ACCEPTABLE; the category gate at `:3910` + catfix FIX-1 override it to skincare; do NOT over-narrow "Vitamin C serum" at the function level), `Samsung Galaxy S24` (sanity).

**MUST still route to supplement branch:**
`Vitamin D3 5000 IU`, `NOW Foods Omega-3 1000mg softgels`, `Solgar Magnesium Citrate 200mg`, `Centrum Multivitamin`, `NOW Vitamin D-3 5000 IU`, `Optimum Nutrition Whey Protein` (brand-closed), `Nordic Naturals Omega-3` (brand-closed — **the single most likely silent regression; `test_error_paths.py:104` asserts True**).

Pin these in `tests/test_supplement_detector_precision.py` (WS-1, function level) AND `tests/test_explicit_pair_category.py` / a new routing test (WS-2, routing level).

---

## OPEN QUESTIONS / DISPATCHER-GATE FLAGS

**Q1 — WS-1 narrowing HIGH_VALUE vs the `is_supplement_query` short-circuit (cross-fix interaction, the task's named risk).** Confirmed by Finders 1 + 3: the short-circuit at `:582` (and `is_fragrance_query:639`) currently reads the raw `HIGH_VALUE_KEYWORDS` set. If WS-1 narrows the set WITHOUT repointing, the floor and the supplement guard disagree on what's high-value — a SILENT inconsistency (not a test failure). **GATE:** WS-1 MUST either (a) repoint both short-circuits to `is_high_value_query()` (the function), OR (b) drop the short-circuit from the whole-token `is_supplement_query` entirely (recommended — redundant under whole-token; no electronics token = no supplement token). Pin `Samsung Galaxy S24→False`/`iPhone 16 Pro→False` either way. Both finders independently flag this as MANDATORY, not optional.

**Q2 — CDE-3 is OVER-STATED as written ("seed from Tier-1/short-circuit prices") → a winner-only seed is a NO-OP.** Finder 5 sharpened: a single short-circuit price has ONE value/size; `_resolve_to_target` either passes through at-tolerance (seed unused) or needs a DIFFERENT candidate at the target (the winner == cur, so no help). **GATE:** the implementer MUST scope CDE-3 as "seed the FULL retained candidate set the short-circuit path observed" (shopping_items / shopify alternates / algolia alternates), NOT the single winner — else it ships a false "fix" that closes the item with zero behavior change. The `test_cde3_at_target_shortcircuit_noop` + `test_cde3_single_candidate_still_pends_honestly` pins prove the scope is right.

**Q3 — `_PHONE_MODEL_RE` is load-bearing + brittle (precision vs no-wrong-scrapes, EL-2).** Every flagship-floor protection for bare brands now hinges on this regex. Under-matching ("S24Ultra", "Galaxy S 24") silently drops the floor → a wrong-cheap accessory could be served as a genuine flagship = a no-wrong-scrapes regression. Over-matching catches `Mi Band 8`/`Galaxy Watch` → re-introduces the EL-2 false-drop. **GATE:** the gap-detection / adversarial reviewer must pressure-test sub-brand model strings BOTH ways; pin the Mi-Band canary AND a broad flagship-model corpus. Prefer slight over-match on the model (keeps the floor) but EXCLUDE band/watch/buds/fit from the pattern.

**Q4 — Sony/Bose/CPU non-coverage is a deliberate scope line, NOT a fix.** `is_high_value_query` never covered Sony/CPUs today (`sony`/`ryzen` not in `HIGH_VALUE_KEYWORDS`). The split doesn't change that. **GATE:** document `Sony WH-1000XM5→False` and `AMD Ryzen 7→False` as KNOWN non-covered (the unit-pin includes them as documentation rows), so they aren't mistaken for a regression. Adding global-audio-tier brands + a headphone noun is a SEPARATE additive enhancement — do NOT silently bundle.

**Q5 — WS-F lenient drift-guard passes trivially on lulu's all-category reach.** It proves "a path EXISTS" not "the path produces genuine BHD in practice" (lulu's JSON-LD coverage is uneven for luxury fragrance/premium beauty). **GATE:** ship BOTH the lenient guard (gates merges, no false reds) AND a strict category-specific variant (documents `other`/`haircare` thinness via `KNOWN_SOURCE_GAPS` reasons). KNOWN_SOURCE_GAPS seed is EMPTY today — the strict test's gap entries are the only non-empty seed and must each carry a reason.

**Q6 — WS-G adapters ship verify-or-omit; the liveness probe is a SEPARATE manual step.** No registry row lands without a passing `scripts/verify_source_registry.py` run + the category-specific positive/negative price gate. **GATE:** if the implement agent cannot run live network probes (sandbox DNS), it records the candidate in `KNOWN_SOURCE_GAPS` with the reason and ships NO row — it must NOT add an assumption-based row (the carrefour/spinneys lesson: a dead/render-walled domain starves the `limit=8` discovery window). F8's aldeerah row is the only one with prior evidence (in `PHARMACY_DOMAINS` + a search template) but still needs the curl-scrapeability + `is_render_only` determination before shipping.

**Q7 — Anchor drift: NEGLIGIBLE.** All finders re-grepped against current HEAD (`2244ad4`); every named anchor held within ±0-3 lines. Confirmed exact this session: `scs:3910`, `scs:1312`, `scs:2813`, `response_builder.py:1212`, `price_service.py:332/544/563/579`. The only naming nuance: the module fn is `fetch_pharmacy_price` (no underscore) at `price_service.py:3918`; `_fetch_pharmacy_price` is the thin service-method wrapper at `scs:1836`. No symbol moved or was renamed.

**Q8 — DM-3 mechanism mis-described in the design (but fix + risk are right).** The real lever is **domain diversity** (8 queried domains, only top-4 read), NOT "more results / a rarely-hit ceiling." Doesn't change the one-line fix (`[:4]→[:8]`) or the low-risk verdict (the `weight≥1.5` registry gate rejects noise) — but the contract doc + commit message should describe it correctly.

---

## SHIP-GATE (end-of-bundle, before prod)

1. **Free-unit `comm` zero-regression gate** — the authoritative gate. Run the full free-unit suite (`python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`) on the branch AND on a temp `main` worktree; `comm` the sorted FAILED-test sets → **branch-only-NEW == [] across WS-1..WS-5**. The documented order-flaky `test_rate_limiting_complete` (real GET) is the only acceptable extra. Run this ONCE via the single regression reviewer, NOT per implement task (per-task `git stash` caused the 35-min grind; whole-suite inside an implement task ground ~35 min on a clean tree).
2. **smoke20 vs `54b603e8`** — `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 54b603e8 --concurrency 1`. ACCEPT on winner ≥ baseline (0.50) / factual HELD (1.0); a specs dip ≈ cold-run/timeout noise (NOT a regression — the documented "GATE FAIL" false-positive is the stale-`SUPABASE_*`-env baseline-fetch tooling, restart CC or `source .env` first). **smoke20 does NOT cover the F1 misroute class** — the F1 unit-pin set is the proof for that class, not smoke20.
3. **Fresh-nocache genuine-share confirm** — prod `nocache` pull of a supplement pair (NOW/Solgar D3) → price is genuine OR structured pending, NEVER bare None / "N/A" (G1). A fragrance pair → no score-leak in any text field, SSE prices event pends a non-genuine price (G5). An electronics accessory pair ("Samsung 25W charger") → not floored out (G4). Inspect the ACTUAL content (the stale-cache-masks-fix + verify-the-RESULT-not-a-glance gotchas — a top-level HTTP-200 is NOT proof).
4. **F1 unit-pins green** — both layers (function + routing). Hard ship-blocker.
5. **Backend-only / NO EAS** — all five waves are backend. The ONE FE-adjacent surface is SIB-1's SSE `prices` payload shape (WS-5); the existing FE build tolerates `amount==null` so no FE code change, but run an **EAS preview verify** of the streaming path to confirm a pending price doesn't tick a number mid-stream. No `eas update` ships new FE code in this bundle.
6. **No-fab carry-over** — the WS-5 regression-guard list (the full `2244ad4` score-leak / price-pending / review-grammar set) is GREEN. The widened scrub EXTENDS `test_response_builder_scrubs_score_leaks`, never breaks it.
