# Genuine-Price CORRECTNESS — IMPLEMENTATION SPEC (single source of truth)

> Every workflow agent on this build MUST read this file first, then
> `docs/plans/2026-06-27-genuine-price-correctness-build.md` (the hardened plan) and
> `.qa-correctness-gaps.json` (the 75 confirmed gaps). This file PINS the architecture
> decisions so there is NO per-file drift. Branch: `feature/genuine-price-correctness`
> (off prod `b207bfa` / code `135e21c`). Python 3.12, FastAPI. Windows: always pass
> `encoding='utf-8'` to open()/subprocess.

## CARDINAL RULE
Select a price ONLY if it is the EXACT requested product — **model + concentration +
size/storage + variant + count** — **native BHD or honest converted_usd, current PDP price,
in stock, valid PDP URL**. A miss must **PEND** (`make_pending_price`). Provenance
(`source_method ∈ _GENUINE_BH_SOURCE_METHODS`) is necessary but NOT sufficient. The gate must
ALSO NOT over-reject (no false pends on legitimate alias wording).

---

## ARCHITECTURE (locked — do not deviate)

### Where the shared code lives
All new shared functions go in **`app/services/price_service.py`**, near the existing
matchers (after `extract_storage_gb`, ~line 2569). Rationale: `zyte_service`, every adapter
(`woocommerce/salla/occ/magento_graphql/algolia/rest_json/unbxd`), `structured_comparison_service`
and `response_builder` ALL already `from app.services.price_service import ...`. price_service
imports NONE of them → no circular import. Single home = single source of truth, the plan's
"ONE shared gate / ONE shared selector" requirement.

### Three enforcement layers (defence in depth)
1. **Per-extractor / per-adapter gate** — each candidate-selection site calls `is_exact_match`
   to REJECT wrong SKUs during selection, and `select_best` to pick by authority (never cheapest).
2. **Cross-adapter consume (Tier-2)** — `structured_comparison_service._consume_adapter_prefetch`
   replaces `min(genuine_observed, key=amount)` (scs.py:4674) with `select_best`.
3. **Fail-closed BACKSTOP at the response chokepoint** — `is_price_showable` (price_service:983),
   called by EVERY adapter before returning AND by the single response chokepoint
   (`response_builder.py:1234`) + the streaming path (`scs.py:2983`), is strengthened to PEND on
   `in_stock is False`, invalid/listing URL, or (when identity is available) non-exact match.
   This catches any path that bypasses or pre-dates layer 1.

### The identity must survive to the backstop
Today `extract_price_from_shopping` does `best.pop("title", None)` at price_service:3151 — the
candidate title is destroyed before `is_price_showable` ever sees it. **STOP stripping
`title`/`name`/`in_stock`/`url` before the showable gate.** Keep them on the price dict through
to the chokepoint. After the showable normalization in `response_builder`, a FINAL UX projection
may drop purely-internal keys (`title`, `match_score`, `variant_rank`, `confidence`,
`retailer_score`) BUT **must keep `url`, `in_stock`, `amount`, `currency`, `retailer`,
`source_method`, `size`** (Wave D's KPI reads `in_stock` + `url`).

---

## THE SHARED HELPERS (Wave B)

### `is_exact_match(query_name: str, candidate_title: str, category: Optional[str], *, candidate_brand: str = "") -> bool`
Set-EQUALITY identity gate. Returns True iff `candidate_title` is the SAME product as `query_name`.

Generalize Zyte's `_identity_tokens` (zyte_service.py:145) into a category-aware primitive in
price_service. The identity token set = diacritic-folded words (`_fold` / NFKD) minus:
- the brand words (so sephora's brand-omitted titles still match — keep brand-aware behaviour),
- the concentration PHRASE (via `_CONCENTRATION_PATTERNS` — strip "eau de parfum"/"parfum intense"
  but KEEP a standalone product word like the "intense" in "Dior Homme Intense"),
- size tokens (ml + oz), storage tokens (GB/TB), and count tokens (capsules/tablets/…) — these are
  compared on SEPARATE axes, not as identity words,
- form noise (`_FORM_TOKENS`) and sub-3-char noise — **EXCEPT keep 2-digit model numbers**
  (the Zyte electronics gap: `len(w) > 2` drops "15"/"24"-class model numbers; fix by keeping
  pure-digit tokens of length ≥ 2 as identity, e.g. "s24"→s24 already survives but a bare model
  number "15" in "iPhone 15" must survive).

Then exactness = ALL of:
- identity token sets are EQUAL (NOT subset — that is `strict_title_match`'s bug; NOT best-overlap),
- concentration equality (both `extract_concentration` results equal, OR see absent-axis policy),
- size equality (`extract_size_ml_any`), storage equality (`extract_storage_gb`), count equality
  (`_COUNT_RE`), weight/volume equality where the category demands it — per the qualifier table below,
- per-category variant qualifier equality (FE/SE/Lite/Neo/Pro/Max/Plus/Ultra/Mini/Air/5G/gen/…).

**Absent-axis policy (over-rejection guard — apply consistently, 1I):**
- If the QUERY omits an axis (no storage/size/concentration stated) → that axis does NOT reject;
  selection prefers a canonical basis via the existing soft signals (`variant_precision_rank`,
  `flagship_basis_bonus`, `_CONCENTRATION_PREFERENCE`) — **never cheapest**. The exact gate only
  REJECTS on an EXPLICIT mismatch (query says EDP, candidate says EDT → reject; query silent → keep).
- If the candidate omits an axis the query states → reject only when the axis is REQUIRED for that
  category (storage for a phone/laptop the query pinned; concentration for a fragrance the query
  pinned). A silent candidate on a non-pinned axis is kept (benefit of the doubt, ranked lower).

### Per-category qualifier / axis table (`CATEGORY_IDENTITY_AXES`)
A central config mapping category → which axes are identity-discriminating + the variant-qualifier
token set. Pin it in price_service. Initial table (extend as tests demand):
- **electronics**: variant {FE, SE, Lite, Neo, Pro, Max, Plus, Ultra, Mini, Air, "5G", gen};
  size axis = storage (GB/TB) REQUIRED when query states it; screen-inch is a soft size signal.
- **fragrances**: concentration REQUIRED when stated (EDP/EDT/EDC/Parfum/Extrait); size = ml.
- **supplements**: count REQUIRED when stated; form (capsules/tablets/softgels); strength (mg/IU).
- **makeup/skincare/haircare**: volume/weight (ml/g); shade is an OPEN alias class (see below).
- **grocery**: weight/volume + count/pack.
- **fashion**: size + colorway are OPEN alias classes (see below) → default to NOT rejecting on
  color/size unless a test proves a needed reject; fashion is intentionally permissive.
- **other / None**: identity-token equality + numbers_match only (no category axis).

### `select_best(candidates: List[dict], query_name: str, category: Optional[str]) -> Optional[dict]`
Among candidates that are **exact ∧ in-stock ∧ valid-URL**, pick by:
1. retailer authority — `source_router.score_source(url, category)` (HIGHER wins),
   then existing `retailer_score` / OFFICIAL_BRAND_DOMAINS signals,
2. variant precision (`variant_rank`) — closer to the stated size/concentration,
3. **amount as the LAST tiebreak only, among equally-authoritative-and-precise candidates.**

**NEVER `min(amount)` / `variants[0]` / `>= best: continue` / first-hit.** Returns None when no
candidate is exact ∧ in-stock ∧ valid-URL (→ caller pends).

### Availability policy (`parse_availability` + `is_available`) — 1C
Handle ALL schema.org forms (string, URL-form `http://schema.org/InStock`, None, list, dict) WITHOUT
`TypeError` (the current `"OutOfStock" not in availability` crashes on None/non-str — gap #41):
- `InStock` / `OnlineOnly` / `LimitedAvailability` → available = True.
- `OutOfStock` / `SoldOut` / `Discontinued` → available = False → PEND, and the extractor must NOT
  select it even if it is the cheapest exact match (a costlier in-stock exact beats a cheaper OOS).
- `PreOrder` / `BackOrder` → available = "future" (policy flag) → treat as NOT current → PEND
  (buyable-but-future ≠ current PDP price). Flag it, don't silently show.
- **Absent / unknown (None / no signal)** → available = None → treat as SHOWABLE (avoid false-pends
  on clean adapters like nasser that omit the field). `is_price_showable` PENDs only on an EXPLICIT
  `in_stock is False`.
- Zyte hardcodes `in_stock=True` (zyte_service) and the HTML OG/microdata/Woo paths hardcode True —
  replace with the real parsed availability where the source exposes it; keep True only where there
  genuinely is no availability signal (= unknown).
- **Transient-OOS ≠ structural dead-end:** a temporarily-OOS exact match must NOT be written to the
  30-day negative cache as a structural gap — use a short TTL / distinct marker (see Wave C negcache).

### Valid-URL gate — 1E
"Valid PDP URL" = present AND not `source_router.is_non_pdp_listing_url(url)` AND not a bare
homepage/synthesized `build_retailer_url` search URL. Enforce in `is_price_showable` + `select_best`.
**Over-rejection guard:** a genuine BH source that legitimately has NO url (some `local_bhd`) must
NOT be pended for a missing url — gate the url check to "url present AND is-a-listing-url → reject".

### `is_price_showable(product_name, price, category=None)` — strengthen the backstop
Add a third `category` kwarg (keyword, default None — back-compatible). After the existing checks
(amount>0, source_method ∈ showable, accuracy guards, sample/decant), ADD fail-closed:
- `price.get("in_stock") is False` → False.
- url present AND `is_non_pdp_listing_url(url)` → False.
- candidate identity available (`price.get("title") or price.get("name")`) AND category resolvable
  AND `not is_exact_match(product_name, identity, category)` → False, AND stamp
  `price["guard_rejected"] = "<reason>"` so Wave D can MEASURE the pend (no silent drop).
Every ~20 adapter/chokepoint call site inherits this automatically. Pass `category` from the caller
where available (response_builder has `pd_item.get("category")`; adapters know their query category).

---

## EVERY SELECTION SITE TO FIX (exhaustive — gaps #0,1,2,3,5,6,8,9,10,11,12,19,21,34,43,44,45,46,65,66,67,68,69)

| Site | File:line | Current bug | Fix |
|---|---|---|---|
| JSON-LD | price_service.py:3298 | `price_val < best_price["amount"]` (cheapest across offers/products); OOS kept; only literal `OutOfStock`; no size/conc/storage reject | per-offer availability via `is_available`; collect candidates; `select_best`; `is_exact_match(query_name, product_name, category)` reject |
| Shopping | price_service.py:3134-3153 | `amount` last sort key = cheapest; `in_stock=True` hardcoded (3091); `title` popped (3151); strict only for high-value | `select_best`; keep title; `is_exact_match` for ALL queries (not just high-value) |
| OG / microdata / Woo-span | price_service.py:3411-3470+ (`extract_price_from_html`) | ZERO identity match; `in_stock=True` hardcoded; first price on page | route through `is_exact_match` + availability, or disable when a stricter path exists; no first-price |
| WooCommerce adapter | woocommerce_service.py:~178 | `>= best_amount: continue` (cheapest); no OOS reject | `select_best`; availability; `is_exact_match` |
| Shopify | (shopify path) | `variants[0]` blind | choose the variant matching the requested size/storage/concentration; `select_best`; else PEND |
| Algolia | algolia_service.py (`_match_algolia_hit`/`_catalog_match_hit`) | best-overlap, no variant/conc/in-stock; `_match_algolia_hit` skips is_price_showable | `is_exact_match`; availability; route through is_price_showable |
| Magento GraphQL | magento_graphql_service.py | min/first variant | requested SKU; `select_best`; availability |
| rest_json (panda) | rest_json_service.py | `_title_matches` weak; min/first variant | `is_exact_match`; `select_best`; availability |
| unbxd | unbxd_service.py | accepts `wasPrice` (struck-through); dead-wired | use CURRENT price only; `is_exact_match`; (dead-wired → fix the gate but it stays uninvoked; add a test) |
| salla | salla_service.py | (verify) | `is_exact_match`; `select_best`; availability |
| occ | occ_service.py | OK on OOS (the one that rejects) | align to shared `is_available`; `is_exact_match` |
| **Tier-2 consume** | scs.py:4674 | `min(genuine_observed, key=amount)` | `select_best` (authority, exact, in-stock) |
| **Tier-3 fairness** | price_service.py:1162 `reselect_to_target_size`, :2033 `reselect_to_target_value`, :2123 `reconcile_pair_fairness` | re-select cheapest with NO variant/conc/in-stock re-check | re-check `is_exact_match`+in-stock; pick by `select_best`, not cheapest |
| converted_usd fallback | price_service.py (shopping/jsonld stamp) + scs consume | returns regardless of exactness; consume short-circuits cheapest | gate converted by `is_exact_match` too (1J — converted_usd-beats-genuine is IN SCOPE) |

---

## CACHE-KEY CORRECTNESS (Wave C — 1G; gaps #15,32,54,56,57,58,59,60,61,62,73)
- `build_size_aware_price_cache_key` (price_service:2671) folds ONE size axis → EDP/EDT collide,
  FE/base collide, distinctive tokens living only in `search_query` (concentration/variant) are
  dropped. Add **concentration + variant-qualifier + storage** axes alongside size.
- **Derive the key from the RESOLVED match identity, not the raw request** — the matcher's identity
  IS the cache key's identity (single source of truth). A wrong-size/variant match must never cache
  under the correct-identity key.
- Alias WORDING only: EDT≡"eau de toilette", oz≡ml-snapped, case/punct — PRESERVE semantic axes
  (EDP≠EDT, 256≠128, FE≠base). Strip the oz token from `base_name` too (gap #61: oz vs ml wordings
  of the same size currently produce different keys).
- `get_specs_cache_key` (product_data_service / scs) has NO size/conc/variant axis → EDP/EDT +
  128/256 specs collide — fix with the same axes.
- Negative-cache + L2 DB inherit the collapsed key → a PEND for one concentration/variant is served
  for its sibling — fixed by the corrected key. Verify the negcache + L2 read/write paths use it.

---

## KPI (Wave D — 1H; gaps #17,27,50,51,52,63,72)
`usable_exact_genuine = (exact SKU/variant ∧ native BHD ∧ current PDP ∧ in_stock ∧ valid URL) / ALL
requested (incl pending)`.
- Emit `in_stock`, `url`, and a `resolved_identity` stamp on the response price (no UX leak of internals).
- Build a NON-circular exact-SKU truth set: 30–50 real BH-available products per category for at least
  electronics/fashion/fragrances (ideally all 9), with expected exact SKU + a current genuine BHD
  reference. **MUST be disjoint from `data/warmer_catalog.json`** (Phase 2 warms that; reading it back
  measures the warm, not correctness) — pin disjointness with a test
  (`tests/test_kpi_set_disjoint_from_warmer.py`).
- Measure COLD and WARMED separately; pin `GENUINE_BH_SOURCE_METHODS` parity
  (`tests/test_eval_genuine_methods_parity.py` already exists — keep it green).
- Per-category PASS gate: electronics/fashion/fragrances ≥ 85% usable_exact_genuine → gates Phase 2.
- The Serper-heavy KPI eval RUN is the LAST step (this fresh session) — author the scaffolding +
  the truth-set + the metric in eval_runner; the dispatcher runs the actual eval at the end.

---

## NO-FAB / DORMANCY / ROLLBACK (1J; gaps #71,74)
- New exact PENDs MUST be flagged (`price["guard_rejected"] = reason`) + counted in eval metadata —
  the 30-day negcache must not silently freeze gate-rejected products.
- The exact gate runs on EVERY request (NOT catalog-flag gated) → high blast radius. Add a rollback
  env flag (e.g. `ENABLE_EXACT_PRICE_GATE`, default **ON** in code but flippable) so the whole new
  gate can be disabled in prod without a revert. When OFF, behaviour reverts to b207bfa exactly.
- Gate process per wave: `comm` zero-regression (`branch-only-NEW == []` vs the cached main baseline
  `.qa-correctness/main-baseline-failed.txt`); no-fab (PEND on a miss, never ship wrong/near).

## ANTI-OVER-REJECTION ALIAS CLASSES (1I; gaps #25,31,70) — mandatory greens in Wave A
Enumerate + test so the strict gate does NOT false-pend:
- brand appearing only in the JSON-LD `brand` field (not the name) — already handled, keep.
- storage/size living only in `search_query` (not `name`) — must still match.
- oz≡ml ("3.4 oz"≡"100ml"), EDT≡"eau de toilette", case/punctuation/diacritics.
- legit color / edition / "for men"/"for women" / pack-of-1 tokens (decide: alias, don't reject).
- regional model numbers (SM-S921 ≡ Galaxy S24) — decide alias or numbers-tolerant.
- accessories-of-query stay REJECTED (a case is not the phone) — `is_accessory` already does this.

---

## GATE COMMANDS
- Free-unit suite: `bash .qa-correctness/run_free_unit.sh .qa-correctness/<label>-failed.txt`
  then `comm -13 .qa-correctness/main-baseline-failed.txt .qa-correctness/<label>-failed.txt`
  (output MUST be empty = no NEW failures). Main baseline captured at branch creation.
- Syntax: `python -m py_compile <file>`.
- Per-feature reds: `python -m pytest tests/<new_test>.py -q`.
