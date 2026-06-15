# A1 + A3 — Genuine-BH Source Scoping (CF-free discovery + CF-walled luxury attack)

**Date:** 2026-06-15
**Author:** be-sourcing (Genuine-Share Push + Polish bundle, Thrust A — tasks #14/#16)
**Companion:** `docs/investigations/2026-06-15-render-wall-bh-retailers.md` (the prior render-wall finding this builds on)
**Serper spend:** 16 credits (cap was 100). Everything else (Shopify `/products.json`, `/meta.json`, curl JSON-LD PDP, prod `fetch_shopify_price`, CF-walled alt-source probe) = **$0** (no Serper, no Firecrawl/render).

---

## A1 — Discover CF-free genuine BH sources for the structural-estimate categories

**Question:** find CF-FREE genuine BH sources for the structural categories (luxury
fragrance beyond alhajis/ajmal/asgharali; premium haircare; gadgets) via targeted
Serper/curl-JSON-LD + Shopify `/products.json` probing.

### Method (FREE-first)
1. 15 Serper `gl=bh` `/search` discovery queries (5 per structural gap) harvested
   real BH-native candidate domains. (`.qa-bh-sourcing/_a1_serper_discovery.py`)
2. $0 probing of each candidate through the **production extractors**
   (`extract_price_from_html`, `fetch_shopify_price`, `_fetch_shopify_catalog`) — so a
   HIT means production would actually consume the price, not just "the page loads."
   (`_a1_free_extract_probe.py`, `_a1_relevance_check.py`, `_a1_pdp_confirm.py`)

### Result — 1 strong genuine-BH add

| Source | Category | Path | Genuine-BHD evidence |
|---|---|---|---|
| **sonyworld.bh** | electronics (audio gadgets) | Shopify `/products.json`, base **BHD** | prod `fetch_shopify_price("sonyworld.bh","Sony WH-1000XM5")` → **145.0 BHD, `shopify_json`**; "Sony LinkBuds" → 49.0 BHD; 176 products |

`sonyworld.bh` is the official Sony Bahrain store and directly fills the **audio-gadget**
structural gap (the warmer's `warm-gadget-003` = WH-1000XM5 vs Bose). It is consumed by
the EXISTING Shopify cascade — only needs the registry row
`Source("sonyworld.bh","bahrain",("electronics",),3.0,is_shopify=True)`. No new code path.

### Candidates rejected (honest, with reason)

| Candidate | Why rejected |
|---|---|
| junaidperfumes.com / perfumistaaloud.com | Shopify BHD + curl-extractable, BUT catalogs are **Arabic-oud houses** (Motayeb Oud, Oud Wz Musk), not the Western designer/niche brands (Tom Ford/Creed/Dior) driving the fragrance estimate gap. Overlaps existing alhajis/ajmal/asgharali oud coverage — ~zero incremental genuine-share. |
| nazih.bh (premium haircare) | Direct PDPs have static prices, BUT (a) `site:nazih.bh "Olaplex No 3"` returns ONLY the homepage → Google hasn't indexed its PDPs, so the prod Serper `site:` discovery can't surface the right PDP; (b) its `catalogsearch` listing is JS-rendered (0 `product-item-link` anchors in static HTML); (c) the homepage/category scrape mis-attributes (19.03 BHD off a `/skin.html` CATEGORY page, not an Olaplex PDP). **Discovery-blocked** → not reliably consumable. |
| myperfumeshop.bh | Shopify but **AUD base** → converted_usd, not genuine local_bhd. |
| switchstore.com | Shopify BHD but budget no-name brands (Ravoz/Endefo/Zenet); no premium Apple/Sony/Bose/Dyson gadgets. |
| virginmegastore.bh / dyson.com.bh / bahrain.whizzcart.com / alhawaj.com / purpleorchidbh.com | 403 or JS-SPA (BHD strings present, no static extract → render-only, same class as the CF-walled set). |

### Headline
The **luxury fragrance + premium haircare** estimate gap is **CONFIRMED structural** — no
CF-free, *discoverable* genuine BH source surfaced. The one genuine win is **sonyworld.bh
for audio gadgets**.

---

## A3 — CF-walled luxury (sephora.bh / bolo.bh / boutiqaat): any reachable genuine source?

**Question:** for the Cloudflare-walled luxury beauty/fragrance retailers, is there ANY
reachable genuine source — an alt retailer, a brand `.com` BH store, a public API, or a
*justified* CF-bypass?

The prior render-wall investigation already proved the trio is **Cloudflare-protected and
NOT Firecrawl/Scrape.do-extractable** (the render scrapers get the CF block interstitial,
not a PDP). A3 attacks the remaining angle: an OTHER reachable source for the same products.

### Method
$0 probe of brand-direct `.com` stores + GCC luxury-beauty alt-retailers for a Shopify BHD
base or a curl-extractable BHD JSON-LD PDP. ZERO Serper, ZERO Firecrawl.
(`.qa-bh-sourcing/_a3_cf_walled_alt_source.py`)

### Result — clean negative: 0 alt sources with genuine BHD

- **Brand-direct** (Fenty / Huda Beauty / Kayali) are Shopify but **USD / AED base**
  (global / UAE stores) → converted_usd at best, never genuine BHD. No BH-base brand store.
- **GCC alt-retailers** (Faces/Chalhoub, Wojooh, GoldenScent, brandatt) are not Shopify and
  do not expose a curl JSON-LD BHD price — Magento/SPA storefronts, several themselves
  region-gated to AED/SAR.
- Dior beauty `dior.com` = 403; CT `.com` = USD; no BH-base anything.

### Recommendation
**Accept the structural gap.** There is no CF-free, BHD-genuine alternative reachable for the
luxury beauty/fragrance products behind the sephora.bh / bolo.bh / boutiqaat wall. The honest
`converted_usd` fallback remains the correct safety net (Lever B — removing it — stays
declined). Unlocking these would require a **CF-bypass-capable scraper tier** (paid anti-bot /
stealth browser) — a budget + vendor decision, not a code fix. Deferred (flagged for Ahmed,
same as the prior investigation).

---

## Net effect on genuine-share

- **+ audio-gadget genuine** via sonyworld.bh (pending dispatcher GO on the single registry
  write) + the A2 warmer pairs that target it.
- **Fragrance/haircare/luxury-beauty estimates remain structural** — confirmed twice now
  (render-wall + this alt-source attack). The genuine wins keep coming from the curl-
  extractable BH sources the registry already reaches (alhajis, bahrain.ounass.com, lulu
  `/en-bh/`, sharafdg, microless, the Shopify fragrance stores) + sonyworld.bh.

## Repro harnesses (all in `.qa-bh-sourcing/`, cache-disabled, no prod write)
- `_a1_serper_discovery.py` — 15-credit BH-retailer discovery (the only Serper spend bar 1).
- `_a1_free_extract_probe.py` / `_a1_relevance_check.py` / `_a1_pdp_confirm.py` — $0 prod-extractor probing.
- `_a3_cf_walled_alt_source.py` — $0 CF-walled alt-source attack.
