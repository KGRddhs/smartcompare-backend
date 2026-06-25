# Bahrain Source Matrix Contract (genuine-bh-price-missing-data bundle)

**Status:** LOCKED + IMPLEMENTED. Owner: be-core. Consumers: price pipeline, eval, qa, future source-discovery work.
**As-shipped:** WS-4 (this bundle) — drift-guard `tests/test_bahrain_source_matrix_coverage.py`, this doc. Registry source of truth: `app/services/source_router.py::SOURCE_REGISTRY`.
**Precedent:** `docs/contracts/d2-error-contract.md`.

This is the contract for **which Bahrain product categories have a genuine-BHD
price source on live traffic, which fall back to converted/estimated/pending,
and why** — plus the verify-or-omit pipeline for adding new sources. It exists so
a future registry edit can never *silently* strand a category to
`converted_usd → estimated → pending` without a recorded, reasoned gap.

---

## 1. Invariants + the genuine-capable definition

**G1 (no silent None / no fabricated amount):** a category with no genuine BH
source resolves to an **honest** `converted_usd → estimated → structured pending`
(`{amount: null, unavailable: true, reason: pending_genuine}`), NEVER a bare
`None` / `"N/A"` and NEVER a fabricated number.

**Genuine-BH-capable (the drift-guard predicate):** a category is COVERED iff
`get_sources_for_category(cat)` (with `SCRAPEDO_SUPER` in its default-OFF state)
yields ≥1 **bahrain-tier** source that is **NOT `is_render_only`** AND **NOT
`requires_super`** — i.e. a source reachable for genuine BHD on the live 12s
clock via **(a) curl/JSON-LD**, **(b) Shopify `/products.json`**, or **(c) a
public Algolia index**.

**Render-only and requires_super rows are DEAD on live traffic** (the live 12s
clock starves the Firecrawl/Scrape.do render tier — T4; `SCRAPEDO_SUPER` is OFF
by default and fail-closed at `source_router._super_routing_enabled`). They are
real, priced stores — they just need a render budget the live path doesn't have.
They count toward genuine coverage ONLY when the warmer (off-clock, paid Serper)
or a `SCRAPEDO_SUPER` experiment (WS-H §7) is running.

---

## 2. The all-category matrix (gated vs the live `SOURCE_REGISTRY`)

Canonical 9-category set = `frozenset(CATEGORY_SPEC_SCHEMAS.keys())`
(`extraction_service.py:101`) = `{electronics, grocery, supplements, other,
makeup, skincare, haircare, fragrances, fashion}` (== `CATEGORY_FAIRNESS` keys,
`price_service.py`).

Columns (a)-(c) = **live-reach genuine BHD**. Columns (d)-(e) = real-but-starved
(render budget / `SCRAPEDO_SUPER` only). (f) = the honest degrade cascade. (g) =
the recorded structural gap.

| Category | (a) curl / JSON-LD genuine | (b) Shopify-json | (c) Algolia | (d) render-only (starved) | (e) super-OFF / CF-walled | (f) fallback | (g) KNOWN GAP |
|---|---|---|---|---|---|---|---|
| **electronics** | gcc.lulu, bahrain.sharafdg.com, extra.com, bahrain.microless.com | shopalmoayyed.com, sonyworld.bh | — | noon.com | — | converted_usd → estimated → pending | mid-tier accessories floored by EL-2 (G4 narrows the floor); official brand sites are global→converted |
| **grocery** | gcc.lulu, talabat.com, bateel.bh | — | — | megamart.bh, alosraonline.com | — | converted_usd → estimated → pending | none structural — strongest curl coverage |
| **supplements** | gcc.lulu, bahrainpharmacy.com, bolo.bh, nasserpharmacy.com *(+ iHerb `bh.iherb.com` curl, a SEPARATE branch)* | — | — | bn.boots.com | — | iHerb → pharmacy → converted → estimated → pending | thinness eased post-recon (lulu + bahrainpharmacy + bolo curl + nasser JSON-API + the iHerb side-branch); F1 misroute + bounded-stage timeout (WS-1/WS-2 fixes); aldeerah curl source ABSENT (F8 — verify-or-omit, §5) |
| **makeup** | gcc.lulu, bahrainpharmacy.com, bahrain.ounass.com, bolo.bh, nasserpharmacy.com, boutiqaat.com | — | — | bn.boots.com | sephora.me | converted_usd → estimated → pending | Western drugstore→converted; boutiqaat genuine via sitemap+curl JSON-LD (Wave-3c); CF-walled premium structural (sephora.me) |
| **skincare** | gcc.lulu, bahrainpharmacy.com, bolo.bh, nasserpharmacy.com, boutiqaat.com | — | — | bn.boots.com | sephora.me | converted_usd → estimated → pending | bolo (curl) + nasser (JSON-API) + boutiqaat (sitemap+curl, Wave-3c) added category genuine reach; CF-walled premium structural (sephora.me) |
| **haircare** | gcc.lulu, bahrainpharmacy.com *(JSON-LD reach for haircare SKUs unproven)*, nasserpharmacy.com, boutiqaat.com | — | — | bn.boots.com | — | converted_usd → estimated → pending | nasser JSON-API + boutiqaat (sitemap+curl, Wave-3c) added genuine reach; premium→converted |
| **fragrances** | gcc.lulu, jalilaperfumes.com, bahrain.ounass.com, nasserpharmacy.com, boutiqaat.com | bh.asgharali.com, en-bh.ajmal.com, alhajisbahrain.com | — | — | sephora.me | converted_usd → estimated → pending | Western luxury (Tom Ford/Creed/Chanel)→converted/estimated; Eastern/local genuine via the Shopify stores + nasser JSON-API + boutiqaat (sitemap+curl, Wave-3c) |
| **fashion** | gcc.lulu, bahrain.ounass.com | — | en-bh.6thstreet.com | — | — | converted_usd → estimated → pending | THIN (2 curl + 1 Algolia); namshi BH un-wired (F6/WS-G, §5) |
| **other** | gcc.lulu (the ONLY source — all-category row) | — | — | — | — | converted_usd → estimated → pending | THINNEST — lulu-only (STRICT gap); mitigation is upstream category resolution (F1), not a dedicated `other` retailer |

**Matrix notes (corrections vs the design draft):**
1. `bahrainpharmacy.com` is registered for **supplements + skincare + makeup +
   haircare** (`source_router.py`), broader than originally credited.
2. `bahrain.ounass.com` covers **fashion + fragrances + makeup** only — NOT
   skincare/haircare.
3. `jalilaperfumes.com` is a **plain-curl** fragrance row (no `is_shopify`).
4. The Shopify fragrance stores (asgharali / ajmal / alhajis) are the cheapest
   genuine-BHD win for Eastern/local perfume — `/products.json`, $0, no render.
5. **Source-intel recon (2026-06-23) — Wave-1 registry corrections:**
   - `bolo.bh` moved from render-only(starved) → **(a) CURL-genuine**: it is a
     Nuxt SSR storefront whose PDP carries a genuine BHD price in PLAIN-curl
     static HTML (the prior `is_render_only` flag was STALE). Covers
     **supplements + makeup + skincare**. Discovery is via its OWN products
     sitemap (16 children, ~336k URLs / ~20MB) — **OFF-CLOCK ONLY**; the sitemap
     must NEVER be fetched on the 15s request clock. `mechanism="sitemap"`.
   - `nasserpharmacy.com` moved from render-only(starved) → **(a) JSON-API
     genuine**: bare Apache (NO Cloudflare), genuine BHD served DIRECTLY by its
     OWN JSON API (`newapi.nasserpharmacy.com /v1/filterSearchs`, no Serper, no
     render). Covers **supplements + skincare + makeup + haircare + fragrances**.
     `mechanism="json_api"`.
   - `sephora.bh` → **`sephora.me` (`/bh-en`)**: the canonical BH Sephora is
     `sephora.me`, NOT `sephora.bh` (which 301s + is unverified). It is
     Akamai-walled (`403 AkamaiGHost` from a non-BH IP) → a **(e) provider-test
     candidate** (`requires_super=True`), NOT a canonical curl/super-OFF row.

---

## 3. Live-reach legend

| Column | Flag | Live (12s clock)? | Genuine BHD source for the drift-guard? |
|---|---|---|---|
| (a) curl / JSON-LD | (none) / plain row | ✅ yes | ✅ yes |
| (b) Shopify | `is_shopify=True` | ✅ yes (`/products.json` direct) | ✅ yes |
| (c) Algolia | `is_algolia=True` | ✅ yes (public index direct) | ✅ yes |
| (d) render-only | `is_render_only=True` | ❌ starved (render budget only) | ❌ no (warmer/super only) |
| (e) super / CF-walled | `requires_super=True` | ❌ filtered out (flag OFF, fail-closed) | ❌ no |

---

## 4. KNOWN GAPS (mirrors `tests/test_bahrain_source_matrix_coverage.py`)

**LENIENT `KNOWN_SOURCE_GAPS` (merge gate) = `{}` (EMPTY today).**
Every category has ≥1 live genuine-BH source because `gcc.luluhypermarket.com`
(empty-`categories` all-category curl row) covers all 9. A future edit that
deletes a category's last curl/Shopify/Algolia bahrain row (or flips it
render-only) MUST add an entry **with a reason** — the test fails otherwise.

**STRICT `STRICT_KNOWN_SOURCE_GAPS` (thinness ledger):**

| Category | Strict gap reason |
|---|---|
| **other** | lulu-only (all-category row) — `other` is the catch-all fallback bucket, not a real shopping category; the mitigation is upstream category resolution (F1), not a category-specific BH source. No dedicated `other` retailer exists or is wanted. |

The strict guard EXCLUDES lulu's all-category row to surface lulu-only reliance.
Today only `other` is lulu-only. The **source-intel recon (2026-06-23)** eased
the beauty/pharmacy thinness: `bolo.bh` (now a plain-curl genuine row) +
`nasserpharmacy.com` (now a JSON-API genuine row) add category-specific genuine
reach to `supplements` / `skincare` / `makeup` / `haircare` beyond
bahrainpharmacy — so a deletion of bahrainpharmacy alone no longer strands them.
`haircare` remains the thinnest beauty category (no bolo coverage); all PASS
strict (see (g) above).

**Invariant:** a lenient gap (no source at all) is necessarily also a strict gap
(`test_lenient_gaps_are_subset_of_strict_gaps`).

---

## 5. WS-G candidate-adapter pipeline (verify-or-omit — G7)

**No registry row lands without a passing liveness probe.** A row is added ONLY
after `scripts/verify_source_registry.py` HEAD-resolve + control-calibration
(controls `google.com` + `shopalmoayyed.com` must be 200 in-env FIRST; `403/405/429`
= ALIVE; NXDOMAIN / non-alive = DEAD) **AND** the category-specific positive +
negative price gate below. Unverified → recorded here as **PENDING-LIVENESS** and
**NO row ships** (the carrefour/spinneys lesson: a dead/render-walled domain
starves the `limit=8` discovery window).

**This bundle's disposition: control-calibration PASSED** (registry liveness gate
exit 0, all current rows live, controls 200). HEAD probes were run for every
candidate below. **No candidate completed its FULL liveness contract → NO new
registry row shipped this bundle.** Each is recorded PENDING-LIVENESS with the
exact blocker.

| Candidate | Wiring target | Liveness contract (ALL must pass) | This-bundle status |
|---|---|---|---|
| **aldeerah** `aldeerahpharmacy.com` (F8) | `Source("aldeerahpharmacy.com","bahrain",("supplements","skincare","makeup","haircare"),3.0)` [+`is_render_only=True` iff JS-rendered] | (1) HEAD-200/403. (2) curl a real PDP via `catalogsearch/result/?q=` → `extract_price_from_html` → static BHD JSON-LD/OG price → plain row; if JS-SPA / no static price → `is_render_only=True`. (3) confirm it stocks the claimed categories (Magento — check for an Algolia index, prefer that path). | **PENDING-LIVENESS.** (1) ✅ HEAD-200. (2) ❌ the `catalogsearch/result/?q=` PDP path returned **HTTP 502 Bad Gateway** (twice); the homepage (852 KB) carried `priceCurrency`/`BHD` strings but **NO JSON-LD, NO `og:price`, NO static `"price": N.NN`** → curl-scrapeability + `is_render_only` UNDETERMINED. (3) not reached. **Verify-or-omit → no row.** Already a `price_service.PHARMACY_DOMAINS` row + search template — the pharmacy-search fallback path can still reach it; only the routed-registry curl-scrape is unproven. Re-probe when the search endpoint is back; if static BHD JSON-LD appears → plain row, else `is_render_only=True`. |
| **namshi BH** `en-bahrain.namshi.com` (F6) | one `ALGOLIA_STORES` row (`algolia_service.py`) + `Source(is_algolia=True,tier="bahrain",categories=("fashion",))` | (1) HEAD-200/403. (2) `extract_algolia_config` returns a non-None `{app_id,api_key,index}` with a **BHD/`_bh_`/bahrain index** (NOT the AE index). (3) positive: `fetch_algolia_price("Nike Air Max", domain)` → genuine BHD + `strict_title_match`. (4) negative: a cross-category query does not mis-match. OMIT if app-id/index unharvestable OR AE-only. | **PENDING-LIVENESS.** (1) ❌ HEAD **ReadTimeout** (blocked, not even step 1) — anti-bot wall; the Algolia-config harvest needs a successful page fetch + JS-chunk parse, not attempted. **No row.** Re-attempt with a render fetch to harvest the config; verify the index currency is BHD (not the AE index) before wiring. |
| **rivolishop.com** (fashion) | `Source(...,"bahrain",("fashion",),...)` IF curl-capable | HEAD-200/403; confirm a **BH/BHD** storefront (not UAE/AED-only); curl PDP → static BHD price (else render-flag); platform check (Shopify→`is_shopify`, Algolia→`ALGOLIA_STORES`). OMIT if AED-only or no static price. | **PENDING-LIVENESS.** (1) ✅ HEAD-200. (2)-(3) NOT verified — BH/BHD-storefront confirmation + curl-PDP static-price + platform determination not done. **No row.** |
| **level-shoes BH** (`level-shoes.com` ∈ `GCC_LUXURY_RETAILERS`) | `Source(...,"bahrain"/"gcc",("fashion","fragrances"?),...)` | HEAD-200/403 on the BH-locale URL; confirm `level-shoes.com/en-bh/` BHD catalog; curl PDP → static JSON-LD (luxury SPA likely render-only → warmer-only). OMIT if no BH locale or no static price. | **PENDING-LIVENESS.** (1) ✅ HEAD-200 (apex). (2)-(3) BH-locale catalog + curl-PDP static-price NOT verified (luxury SPA — likely render-only). **No row.** |
| **bathandbodyworks.com.bh** (makeup/skincare/haircare/body) | `Source("bathandbodyworks.com.bh","bahrain",("makeup","skincare","haircare"),3.0)` IF curl-capable | HEAD-200/403; curl PDP → static BHD price (Shopify→`/products.json` `is_shopify=True`); confirm displayed currency is BHD. OMIT if NXDOMAIN or AED/render-only. | **PENDING-LIVENESS.** (1) ✅ HEAD-200. (2)-(3) curl-PDP static-price + BHD-currency confirmation + platform check NOT done. **No row.** |

**Liveness STEPS, not a code deliverable:** the implement agent runs the probe,
then either adds the row (verified) or records the gap here. No live-network
tests in the free-unit tier — `tests/test_bahrain_source_matrix_coverage.py`
pins the verify-or-omit *invariant* (aldeerah ABSENT until verified), and
`scripts/verify_source_registry.py` is the manual liveness step.

---

## 6. Drift-guard reference

`tests/test_bahrain_source_matrix_coverage.py` (free-unit, $0):

| Test | Guards |
|---|---|
| `test_every_category_has_a_genuine_bh_source_or_explicit_gap` | LENIENT merge gate — every canonical category covered or in `KNOWN_SOURCE_GAPS` w/ reason |
| `test_known_source_gaps_are_real_gaps` | no stale lenient gap (a recorded gap that now has a source) |
| `test_every_category_has_a_category_specific_bh_source_or_gap` | STRICT thinness ledger — excludes lulu; `other` documented |
| `test_strict_known_source_gaps_are_real_gaps` | no stale strict gap |
| `test_lenient_gaps_are_subset_of_strict_gaps` | a no-source-at-all category is also a strict gap |
| `test_canonical_set_is_the_nine_schema_keys` | the 9-key set hasn't drifted |
| `test_f8_aldeerah_in_registry_iff_verified` | verify-or-omit (G7) — aldeerah ABSENT until curl-PDP evidence lands |
| `test_f8_registry_pharmacy_domain_parity` | every `PHARMACY_DOMAINS` storefront is a registry row OR a recorded pharmacy-search-only gap |

To re-run the manual liveness gate (control-calibrated):
`python -m scripts.verify_source_registry` (exit 0 = all rows live).

---

## 7. WS-H — `SCRAPEDO_SUPER` 5-point experiment protocol

The CF-walled `requires_super` row `sephora.me` is the remaining super-only path
to genuine BHD for Western-luxury makeup/skincare/fragrance, filtered out
everywhere with `SCRAPEDO_SUPER` OFF. (Wave-3c RE-VERIFIED boutiqaat.com OFF the
requires_super set — its /en-bh PDPs serve genuine BHD in plain-curl JSON-LD, so
it is now a `mechanism="sitemap"` $0 curl adapter, NOT a super row.) **Baseline to
beat:** the G4
measurement (genuine-bh latency+warmer bundle) found `super` NEVER fired across
9 nocache pulls — the Tier-1.5d render wave was short-circuited by
`converted_usd` / curl-JSON-LD every time, and the unindexed BH luxury SPAs have
no Serper URL to render. Before claiming super is the genuine-data lever, the
experiment MUST satisfy all five points:

1. **Fixed small query set** targeting the `requires_super` row specifically —
   a handful of Western-luxury makeup/skincare/fragrance pairs whose only BH
   stockist is sephora.me (e.g. a Charlotte Tilbury / Sephora-exclusive pair).
   NOT a broad eval — a targeted probe.
2. **Provider attempt-trace inspected** — read
   `metadata.source_trace…attempts` and confirm a `scrapedo_rendered` (super)
   attempt actually FIRED on a `requires_super` domain (it didn't in G4). If the
   cascade short-circuits before the render tier, the experiment is inconclusive,
   NOT a win.
3. **Per-run Scrape.do credit cap** — bound the Scrape.do spend per run
   (`SCRAPEDO_API` budget in `api_budget_service`, ~900/mo shared) so a runaway
   super sweep can't drain the shared meter / trip the breaker for live traffic.
4. **Explicit before/after genuine-share evidence** — compare the genuine-BH
   source-method share on the fixed query set with `SCRAPEDO_SUPER=false` vs
   `=true`, inspecting the ACTUAL `source_method` per product (a top-level
   HTTP-200 is NOT proof — the stale-cache-masks-fix + verify-the-RESULT
   gotchas). A win = a confirmed BH-PDP price at `scrapedo_rendered` that was
   `converted_usd`/`estimated` before.
5. **Immediate revert if no confirmed BH-PDP win** — set `SCRAPEDO_SUPER=false`
   the moment the experiment shows no confirmed genuine BH-PDP gain. Dormant
   `super` is pure overhead (a CF-blocked datacenter render burns a credit + can
   trip the shared breaker). Keep the G3 trace + the gated registry rows for a
   future DIRECT-URL / sitemap discovery of the unindexed SPAs — that, not
   blind super, is the likely unlock.

**Current posture:** the `super` rows STAY in the registry (gated, fail-closed,
absent with the flag OFF) so the experiment is one flag-flip away. Genuine BH
prices today come from the curl-scrapeable sources (gcc.lulu `page_scrape_jsonld`,
the Shopify perfume stores) + the WARMER (paid Serper) — NOT super-render.
