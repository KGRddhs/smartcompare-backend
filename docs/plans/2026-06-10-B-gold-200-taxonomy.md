# Bundle B — Gold-Set Expansion 50 → 200 Taxonomy Manifest

**Owner:** F5-gold (Lane F5, Bundle B Session 1 "Foundation")
**Plan:** `docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md` § Lane F5
**Extends:** `docs/plans/2026-06-08-A-validation-matrix-50q.md` (the original 50-query matrix)
**Data file:** `data/validation_gold_truth.json` (existing 50 + 150 new = 200)
**Schema test:** `tests/test_gold_truth_schema.py`

---

## 1. Purpose

Expand the objective eval gold set from 50 to 200 fact-anchored Bahrain-user
comparison queries. The +150 are **deliberately weighted toward the
0%-Bahrain-hit-rate product classes** surfaced by B0-D's bias matrix —
classes where the engine historically fell back to `gpt_training`-priced
estimates because no Bahrain retail listing was consulted:

- **Local / regional grocery brands** (Patchi, Bateel, Al Ain, Almarai,
  Nadec, KDD, Rabea, Ahmad Tea class) — these never appear on amazon.com.
- **AC / home appliances** (Carrier, Gree, Midea, Daikin, Super General
  class) — Bahrain-market split units, water heaters, fans, kettles.
- **Haircare** — the single thinnest existing class (3 entries).
- **Mid-market non-luxury** across fashion / makeup / skincare — the
  drugstore + high-street tier, not the prestige tier the original set
  over-indexed on.

The original 50 are **frozen** — not touched by this lane (their
`max_wall_seconds` stays 25.0). All 150 new entries get
`max_wall_seconds: 30.0` (the raised B0-C Item 3 streaming cap).

## 2. Schema (mirrors the verified per-entry shape — unchanged from the 50)

```json
{
  "id": "groc-005",
  "query": "Al Ain rose water vs Cortas rose water",
  "category": "grocery",
  "region": "bahrain",
  "expected_prices": {
    "product_0": {"min": 0.8, "max": 2.5, "currency": "BHD", "note": "lulu.com.bh / megamart.bh 300ml — regional brand, no amazon.com listing"},
    "product_1": {"min": 0.9, "max": 2.8, "currency": "BHD", "note": "carrefourbh.com 300ml; widened from GCC noon.com where BH price unverified"}
  },
  "expected_specs": {
    "product_0": {"volume": "300ml"},
    "product_1": {"volume": "300ml"}
  },
  "expected_winner_index": 0,
  "expected_winner_rationale": "Local UAE production + GCC distribution depth, lower price per ml",
  "forbidden_facts": ["Al Ain organic certification standard", "Cortas Lebanese single-origin damask", "rose water SPF claim"],
  "max_wall_seconds": 30.0
}
```

Field semantics are identical to the 50q matrix doc § 4. New-entry authoring rules:

- **`expected_prices.product_N`** — `{min, max}` is a BAND of observed
  Bahrain retail BHD. **Every new entry (id ≥ 51) MUST carry a `note`**
  on at least one product naming the retailer/source checked (schema test
  enforces this). Where a Bahrain price is genuinely unverifiable online,
  widen the band from a GCC source (noon.com / amazon.ae × ≈ BHD 0.376/USD)
  and SAY SO in the note — honest provenance over fake precision.
- **`expected_specs.product_N`** — 2–4 load-bearing keys only, partial
  dict, category-appropriate (electronics: storage/os/display; supplements:
  active_ingredient/form; grocery: volume/weight; skincare: active_ingredient/spf).
  Empty `{}` is allowed where the comparison hinges on brand/price not specs.
- **`expected_winner_index`** — Bahrain-buyer perspective (price-per-value,
  local availability, GCC distribution). Subject to Ahmed ratification (F5.4).
- **`forbidden_facts`** — 3+ plausible-but-false claims (the trap axis):
  cross-generation spec bleed, marketing-speak not in the official sheet,
  wrong-tier feature attribution, fabricated certifications.

## 3. Canonical Bahrain provenance sources (from `app/services/source_router.py` SOURCE_REGISTRY)

| Tier | Domains |
|---|---|
| Bahrain (weight 3.0) | lulu.com.bh, carrefourbh.com, sharafdg.com.bh, extra.com.bh, geant.com.bh, bn.boots.com, bolo.bh, behbehani.com, eroselectronics.com, jumboelectronics.com, talabat.com, spinneysbahrain.com, megamart.bh |
| GCC (weight 1.5) | noon.com, amazon.ae, sharafdg.com, ounass.com, bloomingdales.ae, tryano.com |
| Global (weight 1.0) | amazon.com, iherb.com, sephora.com, fragrantica.com, gsmarena.com, brand official sites |

Provenance notes cite these by name. Supplements prefer iherb.com USD→BHD
or bn.boots.com JSON-LD (matrix § 6 rule 2).

## 4. Target distribution (200 total)

Combined existing + new, sorted by total. Weak classes (grocery, haircare)
get the heaviest new allocation; electronics stays largest by absolute count
but AC/appliances become a deliberate sub-focus.

| Category | Existing | + New | Total | % of 200 |
|---|---|---|---|---|
| Electronics | 12 | 22 | 34 | 17% |
| Grocery | 4 | 28 | 32 | 16% |
| Supplements | 6 | 16 | 22 | 11% |
| Haircare | 3 | 18 | 21 | 10% |
| Skincare | 5 | 14 | 19 | 10% |
| Other | 5 | 14 | 19 | 10% |
| Fragrances | 6 | 12 | 18 | 9% |
| Makeup | 5 | 13 | 18 | 9% |
| Fashion | 4 | 13 | 17 | 8% |
| **Total** | **50** | **150** | **200** | **100%** |

## 5. New-entry ID ranges (continues existing scheme `{prefix}-{NNN}`)

Existing max per category: elec-012, supp-006, frag-006, make-005,
skin-005, hair-003, fash-004, groc-004, other-005. New entries continue
sequentially from there.

| Category | Prefix | New ID range | New count |
|---|---|---|---|
| Electronics | `elec-` | elec-013 … elec-034 | 22 |
| Grocery | `groc-` | groc-005 … groc-032 | 28 |
| Haircare | `hair-` | hair-004 … hair-021 | 18 |
| Supplements | `supp-` | supp-007 … supp-022 | 16 |
| Skincare | `skin-` | skin-006 … skin-019 | 14 |
| Other | `other-` | other-006 … other-019 | 14 |
| Fragrances | `frag-` | frag-007 … frag-018 | 12 |
| Makeup | `make-` | make-006 … make-018 | 13 |
| Fashion | `fash-` | fash-005 … fash-017 | 13 |

## 6. Product-type coverage within each category (the stress axes)

- **Electronics (22):** AC split units (Carrier / Gree / Midea / Daikin /
  Super General — the Bahrain home-appliance 0%-hit class, ≥6 entries),
  monitors, routers, printers, mid-market phones (Realme / Tecno / Infinix
  — GCC-popular, low amazon.com visibility), soundbars, power banks,
  smartwatches (Amazfit class), projectors, mid-tier laptops (HP / Lenovo / Asus).
- **Grocery (28):** Regional dairy (Almarai / Nadec / Al Ain), local
  sweets/dates (Patchi / Bateel / Al Foah), tea (Rabea / Ahmad / Lipton),
  juice (KDD / Rani / Barbican non-alc), rice (India Gate / Daawat —
  GCC staple), cooking oil, honey, water (Aquafina / Nestlé Pure Life),
  laban/yoghurt, canned goods, spreads, biscuits (regional brands first).
- **Haircare (18):** Shampoo/conditioner pairs (drugstore: Tresemmé /
  Sunsilk / Dove / L'Oréal Elvive), oils (Vatika / Dabur Amla — South-Asian
  diaspora staple in Bahrain), masks, serums, leave-ins, anti-dandruff,
  curl creams, keratin treatments, hair colour.
- **Supplements (16):** Multivitamins, single-nutrient (D3 / Mg / Zinc /
  B12 / Iron), protein, collagen, probiotics, omega, biotin — iHerb +
  bn.boots.com paths.
- **Skincare (14):** Mid-market cleansers/moisturisers/serums (Simple /
  Neutrogena / Nivea / Cetaphil), SPF (the Gulf-climate axis), retinol,
  vitamin C, hyaluronic, body care.
- **Other (14):** Home appliances (kettles, blenders, fans, air fryers,
  water heaters, irons, vacuum, water dispensers, microwaves) — Bahrain
  mid-market brands (Black+Decker / Philips / Kenwood / Braun / Super General).
- **Fragrances (12):** Arabic/oriental houses heavier (Lattafa / Armaf /
  Ajmal / Rasasi / Swiss Arabian / Al Haramain) + mid designer.
- **Makeup (13):** Drugstore-vs-drugstore + regional (Maybelline / L'Oréal /
  Revlon / NYX / essence / Wet n Wild + Huda / MIKYAJY).
- **Fashion (13):** Mid-market footwear (Skechers / Puma / New Balance /
  Crocs), denim (Levi's / Lee), modest wear, mid watches (Citizen / Fossil),
  backpacks, sunglasses.

## 7. Authoring batches (F5.2)

Authored in batches of 25, committed per batch (`git commit -m "data(gold):
batch N (ids X-Y)" -- data/validation_gold_truth.json`, pushed after each):

| Batch | IDs | Focus |
|---|---|---|
| 1 | elec-013…034 (22) + groc-005…007 (3) | Electronics incl. AC/appliances + grocery start |
| 2 | groc-008…032 (25) | Grocery local/regional brands (heavy) |
| 3 | hair-004…021 (18) + supp-007…013 (7) | Haircare (heavy) + supplements start |
| 4 | supp-014…022 (9) + skin-006…019 (14) + make-006…007 (2) | Supplements finish + skincare + makeup start |
| 5 | make-008…018 (11) + frag-007…018 (12) + fash-005…006 (2) | Makeup finish + fragrances + fashion start |
| 6 | fash-007…017 (11) + other-006…019 (14) | Fashion finish + other/home appliances |

(6 batches × ~25 = 150. Batch boundaries cross categories to keep each
commit ≈ 25 entries; per-category counts still match § 4.)

## 8. Ratification (F5.4)

When all 150 are authored + schema-validated, F5-gold sends team-lead a
`RATIFICATION REQUIRED` summary table (id | query | winner pick | one-line
rationale). Ahmed ratifies the winner labels; F5-gold then writes
`_metadata.ratified_by` / `_metadata.ratified_at` and commits. **The lane is
NOT complete until ratification is recorded and pushed.** This blocks F4.6
(the S1 eval baseline).
