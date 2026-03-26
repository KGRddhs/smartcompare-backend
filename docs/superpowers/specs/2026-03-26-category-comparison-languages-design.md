# Category Comparison Languages + Backend Production Hardening

> **Date**: 2026-03-26
> **Status**: Design approved, pending implementation plan
> **Rollback**: See `docs/ROLLBACK_SCORING_V1.md` for reverting scoring changes

## Problem

SmartCompare currently treats all 9 categories the same way — same scoring dimensions, same prompt style, same reasoning approach. But a user comparing two foundations needs fundamentally different intelligence than someone comparing two phones. Each category has its own "language" for what "better" means, how to prove it, and what risks matter.

Additionally, the backend is missing critical features required for App Store / Google Play approval.

## Scope

### Part A: Category Comparison Languages (Prompt + Scoring)
1. Category-specific scoring dimensions (replace universal 6 dimensions)
2. Category-specific GPT prompt personalities (reasoning style + language)
3. Trust validation layer (cross-check GPT claims against scores)
4. Context auto-inference (detect user intent from query + category)
5. Personalization fairness (not everyone cares about price)

### Part B: Backend Production Hardening
6. Account deletion endpoint (App Store requirement)
7. Privacy policy / Terms of Service endpoints
8. Password strength upgrade
9. Email confirmation re-enable
10. App version check endpoint
11. Code cleanup (dead code removal, print→logger)

### Out of Scope
- Frontend changes (separate spec)
- New categories beyond existing 9
- Push notifications (deferred)
- Usage quota enforcement (deferred)

---

## Part A: Category Comparison Languages

### A1. Category-Specific Scoring Dimensions

Each category gets 6 scoring dimensions tailored to what actually matters in that domain. Replaces the current universal `price_score, spec_score, review_score, value_score, reliability_score, popularity_score`.

#### Electronics
| Dimension | Key | What It Measures | Data Source |
|-----------|-----|-----------------|-------------|
| Performance | `performance_score` | Processor, RAM, benchmark-adjacent specs | Extracted specs (numeric) |
| Value for Money | `value_score` | Price-to-spec ratio, tier-aware | Price + spec aggregate |
| Build Quality | `build_quality_score` | Materials, water resistance, weight | Extracted specs + reviews |
| Feature Set | `feature_score` | Camera, display, connectivity, storage | Extracted specs (count + quality) |
| Ecosystem Fit | `ecosystem_score` | OS, brand ecosystem, compatibility | Extracted specs + reviews |
| Future-Proofing | `futureproof_score` | Latest standards, update support, spec headroom | Specs (5G, WiFi version, OS version) |

**Weights**: `performance: 0.25, value: 0.20, build_quality: 0.15, feature: 0.20, ecosystem: 0.10, futureproof: 0.10`

#### Grocery
| Dimension | Key | What It Measures | Data Source |
|-----------|-----|-----------------|-------------|
| Nutritional Quality | `nutrition_score` | Protein, fiber, vitamins vs sugar, sodium, calories | Extracted nutrition specs |
| Ingredient Transparency | `ingredient_score` | Ingredient count, recognizability, certifications | Extracted ingredient list |
| Taste Reputation | `taste_score` | Review sentiment about taste/flavor | Review text analysis |
| Value per Serving | `serving_value_score` | Price per serving/unit, not just shelf price | Price ÷ count/servings |
| Dietary Fit | `dietary_score` | Organic, halal, allergen-free, dietary compliance | Extracted specs + certifications |
| Availability | `availability_score` | Retailer count, GCC availability signals | Shopping data source count |

**Weights**: `nutrition: 0.25, ingredient: 0.20, taste: 0.20, serving_value: 0.15, dietary: 0.15, availability: 0.05`

#### Supplements
| Dimension | Key | What It Measures | Data Source |
|-----------|-----|-----------------|-------------|
| Ingredient Efficacy | `efficacy_score` | Bioavailable forms, clinical dosages, active ingredient quality | Specs + Bahrain drug DB |
| Safety & Certification | `safety_score` | Third-party testing, certifications, registration status | Specs + drug DB match |
| Dosage Accuracy | `dosage_score` | Clinical vs sub-therapeutic dosing, serving size | Extracted dosage specs |
| Value per Serving | `serving_value_score` | Price per serving, not shelf price | Price ÷ count |
| Form Convenience | `form_score` | Capsule vs gummy vs powder, ease of compliance | Extracted form spec |
| Brand Trust | `trust_score` | Manufacturing transparency, review consistency, fact-check | Reviews + fact_check data |

**Weights**: `efficacy: 0.30, safety: 0.25, dosage: 0.15, serving_value: 0.10, form: 0.10, trust: 0.10`

#### Makeup
| Dimension | Key | What It Measures | Data Source |
|-----------|-----|-----------------|-------------|
| Shade/Color Match | `shade_score` | Shade range breadth, undertone coverage, inclusivity | Extracted shade_range spec |
| Wear Longevity | `longevity_score` | Hours of wear, transfer resistance, oxidation | Reviews (wear-time mentions) |
| Skin Compatibility | `skin_compat_score` | Non-comedogenic, suitable for skin types, irritation risk | Specs + ingredient analysis |
| Finish Quality | `finish_score` | Texture, pigmentation, blendability, coverage | Reviews (finish/texture mentions) |
| Ingredient Safety | `ingredient_safety_score` | Clean formula, fragrance-free, cruelty-free | Extracted ingredient specs |
| Value for Performance | `perf_value_score` | Price relative to wear time and coverage quality | Price + longevity + finish |

**Weights**: `shade: 0.20, longevity: 0.25, skin_compat: 0.20, finish: 0.15, ingredient_safety: 0.10, perf_value: 0.10`

#### Skincare
| Dimension | Key | What It Measures | Data Source |
|-----------|-----|-----------------|-------------|
| Active Ingredients | `actives_score` | Concentration, form quality (e.g., encapsulated retinol) | Extracted active_ingredient + specs |
| Efficacy Evidence | `evidence_score` | Clinical study mentions, dermatologist references in reviews | Reviews (clinical/dermatologist mentions) |
| Skin Compatibility | `skin_compat_score` | Skin type match, irritation potential, pH balance | Specs (skin_type, ph_level, fragrance_free) |
| Formulation Quality | `formulation_score` | Ingredient list quality, clean/natural, no harmful additives | Extracted ingredient specs |
| Sensory Experience | `sensory_score` | Texture, absorption, scent, daily-use comfort | Reviews (texture/feel mentions) |
| Value for Results | `results_value_score` | Price relative to active ingredient quality and concentration | Price + actives quality |

**Weights**: `actives: 0.25, evidence: 0.20, skin_compat: 0.20, formulation: 0.15, sensory: 0.10, results_value: 0.10`

#### Haircare
| Dimension | Key | What It Measures | Data Source |
|-----------|-----|-----------------|-------------|
| Hair Type Match | `hair_match_score` | Compatibility with hair type (curly/straight/fine/thick/color-treated) | Specs (hair_type, hair_concern) |
| Results Effectiveness | `results_score` | Frizz control, shine, moisture, damage repair outcomes | Reviews (outcome mentions) |
| Ingredient Quality | `ingredient_score` | Sulfate-free, paraben-free, bond repair, natural ingredients | Extracted ingredient specs |
| Scent Appeal | `scent_score` | Fragrance quality and persistence (2nd most important factor) | Reviews (scent mentions) |
| Multi-Benefit Value | `multi_value_score` | Problems solved per product, price per use | Specs (feature count) + price |
| Scalp Safety | `scalp_score` | Gentle formulation, scalp irritation risk, pH balance | Specs + ingredient analysis |

**Weights**: `hair_match: 0.25, results: 0.25, ingredient: 0.15, scent: 0.15, multi_value: 0.10, scalp: 0.10`

#### Fragrances
| Dimension | Key | What It Measures | Data Source |
|-----------|-----|-----------------|-------------|
| Scent Character | `character_score` | Note composition quality, uniqueness, complexity | Extracted notes specs + reviews |
| Longevity | `longevity_score` | Hours of wear on skin | Extracted longevity spec + reviews |
| Sillage/Projection | `projection_score` | How far scent radiates, trail quality | Extracted sillage spec + reviews |
| Occasion Versatility | `versatility_score` | Day/night, summer/winter, casual/formal range | Specs (season, occasion) + reviews |
| Value per Wear | `wear_value_score` | Price ÷ (volume × concentration × longevity) | Price + volume + concentration |
| Presentation | `presentation_score` | Bottle design, brand heritage, gift appeal | Reviews + brand recognition |

**Weights**: `character: 0.25, longevity: 0.25, projection: 0.15, versatility: 0.15, wear_value: 0.10, presentation: 0.10`

#### Fashion
| Dimension | Key | What It Measures | Data Source |
|-----------|-----|-----------------|-------------|
| Craftsmanship | `craft_score` | Material quality, stitching, hardware, construction | Extracted material/craftsmanship specs |
| Fit & Comfort | `fit_score` | Size accuracy, comfort reviews, return rate signals | Reviews (fit/comfort mentions) |
| Style & Design | `style_score` | Aesthetic appeal, trend relevance, design details | Extracted style/design specs + reviews |
| Durability | `durability_score` | Material longevity, wear resistance, care requirements | Specs (material, care_instructions) |
| Brand Heritage | `heritage_score` | Brand prestige, craftsmanship history, authenticity | Brand recognition + luxury detection |
| Cost per Wear | `cpw_score` | Price ÷ expected wears (durability × versatility) | Price + durability + style versatility |

**Weights**: `craft: 0.25, fit: 0.20, style: 0.20, durability: 0.15, heritage: 0.10, cpw: 0.10`

#### Other
| Dimension | Key | What It Measures | Data Source |
|-----------|-----|-----------------|-------------|
| Core Function | `function_score` | Does it do what it claims? Feature completeness | Extracted specs + reviews |
| Build Quality | `build_score` | Materials, construction, perceived quality | Specs (material, weight) + reviews |
| User Reviews | `review_score` | Aggregate rating and review quality | Rating + review_count |
| Value for Money | `value_score` | Price relative to feature set and quality | Price + function + build |
| Brand Reliability | `reliability_score` | Brand recognition, warranty, fact-check quality | Fact_check + brand data |
| Feature Match | `feature_match_score` | How well features align with typical use case | Specs vs expected features |

**Weights**: `function: 0.25, build: 0.15, review: 0.25, value: 0.15, reliability: 0.10, feature_match: 0.10`

### A2. Personalization Integration (Fairness by Design)

The existing 3-layer personalization system adapts these new dimensions:

**Layer 1 — Explicit preferences (±30% cap)**:
- `PRIORITY_ADJUSTMENTS` becomes `CATEGORY_PRIORITY_ADJUSTMENTS[category][priority]` — same priority keyword maps to DIFFERENT dimensions per category
- Example mappings for "quality" priority:
  - Electronics: `{performance_score: +0.10, build_quality_score: +0.10, value_score: -0.10}`
  - Makeup: `{longevity_score: +0.10, finish_score: +0.10, perf_value_score: -0.10}`
  - Supplements: `{efficacy_score: +0.10, safety_score: +0.10, serving_value_score: -0.10}`
  - Fragrances: `{character_score: +0.10, longevity_score: +0.10, wear_value_score: -0.10}`
- Example mappings for "price" priority:
  - Electronics: `{value_score: +0.15, performance_score: -0.10}`
  - Makeup: `{perf_value_score: +0.15, shade_score: -0.10}`
  - Supplements: `{serving_value_score: +0.15, efficacy_score: -0.10}`
- Full mapping table to be defined during implementation for all 8 priorities × 9 categories (72 entries)
- `BUDGET_ADJUSTMENTS` similarly remapped per category

**Layer 2 — Behavioral profile (±10% cap)**:
- `dimension_sensitivity` from behavior_service maps to new dimension keys
- Behavioral learning naturally adapts as users interact with category-specific results

**Layer 3 — Session signals (±5% cap)**:
- Tab dwell mapping updated for new dimensions
- Works the same mechanically, just maps to new dimension keys

**Fairness guarantee**: No dimension is ever zeroed out. Even if a user says "I don't care about price," the price-related dimension still contributes (just weighted down). The recommendation always shows ALL dimensions — personalization only changes emphasis, never hides information.

### A3. Category-Specific GPT Prompt Personalities

Each category gets a `CATEGORY_PROMPT_PERSONALITY` dict injected into the verdict/comparison prompt. Controls:

1. **Reasoning style**: What to lead with in the recommendation
2. **Evidence language**: How to cite proof (numbers vs descriptions vs experiences)
3. **Risk framing**: What concerns to address proactively
4. **Comparison voice**: The tone and vocabulary appropriate for the domain
5. **Auto-context inference**: Instructions for detecting user intent from query

```python
CATEGORY_PROMPT_PERSONALITIES = {
    "electronics": {
        "reasoning_style": "Lead with quantifiable differences. Cite specific specs and performance gaps.",
        "evidence_language": "Use numbers: percentages, hours, benchmark scores, pixel counts. 'Product A delivers 23% better battery life (14h vs 11.4h)' — never 'Product A has somewhat better battery.'",
        "risk_framing": "Address obsolescence risk, ecosystem lock-in, and whether the price premium justifies the spec bump.",
        "comparison_voice": "Technical but accessible. Think expert reviewer explaining to a smart friend, not a spec sheet.",
        "context_inference": "Infer use case from product type: phones=daily driver, laptops=work/gaming/creative, headphones=commute/studio/gym. Tailor value assessment to inferred use.",
    },
    "grocery": {
        "reasoning_style": "Lead with ingredient quality and nutritional differences. Health implications over taste unless products are nutritionally similar.",
        "evidence_language": "Cite ingredient lists, nutritional values per serving, and certifications. '3g less sugar per serving and no artificial preservatives' — specific, label-verifiable claims.",
        "risk_framing": "Address hidden ingredients, misleading 'healthy' claims, allergen risks. In GCC: halal compliance and import freshness.",
        "comparison_voice": "Health-conscious and practical. Like a nutritionist explaining label differences to a shopper.",
        "context_inference": "Infer dietary context: protein products=fitness, organic=health-conscious, snacks=family/convenience. Adjust value framing accordingly.",
    },
    "supplements": {
        "reasoning_style": "Lead with ingredient forms and dosages. Distinguish clinical doses from marketing doses. Safety first, then efficacy.",
        "evidence_language": "Use clinical language: 'methylfolate (bioavailable form) at 400mcg clinical dosage' vs 'folic acid at sub-therapeutic 200mcg.' Reference third-party testing status.",
        "risk_framing": "Address safety explicitly: contaminants, mislabeled dosages, regulatory gaps. Mention Bahrain drug registration status if available.",
        "comparison_voice": "Evidence-based and cautious. Like a pharmacist explaining supplement differences — informed but not promotional.",
        "context_inference": "Infer health goal: protein=fitness/muscle, vitamins=daily health, specific supplements=targeted concern. Frame recommendation around the health objective.",
    },
    "makeup": {
        "reasoning_style": "Lead with real-world performance: wear time, shade inclusivity, skin compatibility. Specs are secondary to experience.",
        "evidence_language": "Describe outcomes on skin: '12-hour wear without oxidation' and '40 shades covering warm/cool/neutral undertones.' Focus on what it looks and feels like, not ingredient lists.",
        "risk_framing": "Address shade-matching anxiety, skin reaction risk, and performance in GCC humidity/heat. Inclusivity matters — note if shade range is limited for deeper skin tones.",
        "comparison_voice": "Experienced and relatable. Like a beauty consultant who has tested both products, not a lab report.",
        "context_inference": "Infer occasion: foundation=daily/event, lipstick=casual/statement, eyeshadow=natural/dramatic. Frame recommendation around the intended look.",
    },
    "skincare": {
        "reasoning_style": "Lead with active ingredient analysis: what actives, what concentration, what form. Then discuss compatibility and evidence of results.",
        "evidence_language": "Combine science and outcomes: '0.3% encapsulated retinol (reduced irritation) with niacinamide for barrier support.' Reference clinical claims when available.",
        "risk_framing": "Address skin damage anxiety directly: irritation potential, purging vs breakout distinction, sensitivity concerns. Always mention skin type compatibility.",
        "comparison_voice": "Ingredient-savvy and evidence-based. Like a dermatologist-endorsed review — scientific rigor with practical advice.",
        "context_inference": "Infer skin concern from product type: serum=targeted treatment, moisturizer=daily hydration, cleanser=routine foundation. Match recommendation to skincare routine context.",
    },
    "haircare": {
        "reasoning_style": "Lead with hair type compatibility and expected results. Ingredients matter but outcomes matter more.",
        "evidence_language": "Describe tangible results: 'reduced frizz for 3+ days' and 'lightweight enough for fine hair without weighing it down.' Scent description matters — it's worn all day.",
        "risk_framing": "Address the fear of making hair worse: dryness, breakage, color fading, buildup. Note if switching from current product carries risk.",
        "comparison_voice": "Results-focused and sensory. Like a trusted hairstylist recommending between two products — practical, not clinical.",
        "context_inference": "Infer hair concern from product type: shampoo=daily care, treatment=damage repair, styling=hold/texture. Consider color-treated status from product targeting.",
    },
    "fragrances": {
        "reasoning_style": "Lead with scent description and character. Longevity and projection are the decisive metrics. Price is secondary to the experience.",
        "evidence_language": "Use evocative language for scent: 'Opens with bright bergamot and pink pepper, settling into warm oud and amber.' Quantify longevity (hours) and projection (intimate/moderate/strong).",
        "risk_framing": "Address blind-buy anxiety: skin chemistry variation, season appropriateness, occasion fit. Note if a discovery set is available. GCC: note heat performance.",
        "comparison_voice": "Descriptive and cultured. Like a fragrance connoisseur at a boutique — poetic but informative. Respect the GCC fragrance tradition (oud, bakhoor, Arabian perfumery).",
        "context_inference": "Infer occasion from product style: fresh/citrus=daytime/casual, oud/amber=evening/formal, versatile=signature scent candidate. Designer vs niche positioning matters.",
    },
    "fashion": {
        "reasoning_style": "Lead with material quality and craftsmanship, then fit and style. For luxury items, brand heritage and authenticity matter.",
        "evidence_language": "Describe tangible quality: 'full-grain Italian leather with hand-stitched detailing' vs 'bonded leather with machine finishing.' Use cost-per-wear logic for value assessment.",
        "risk_framing": "Address fit uncertainty, authenticity concerns (especially luxury), and durability expectations. Note return policy relevance. GCC: note climate appropriateness.",
        "comparison_voice": "Quality-focused and style-aware. Like a personal stylist who understands both construction and aesthetics — not just a spec comparison.",
        "context_inference": "Infer use context: sneakers=casual daily, dress shoes=formal, bags=everyday/occasion. For luxury, consider investment piece vs trend item positioning.",
    },
    "other": {
        "reasoning_style": "Lead with how well each product fulfills its core purpose. Balance specs with user reviews when category-specific expertise is limited.",
        "evidence_language": "Cite reviews and ratings prominently. Use specific review mentions when available. Fall back to spec comparison for measurable differences.",
        "risk_framing": "Address value-for-money concern and brand reliability. When data is limited, be transparent about confidence level.",
        "comparison_voice": "Balanced and practical. Like a well-researched buyer's guide — helpful without pretending to be an expert in every domain.",
        "context_inference": "Infer general use case from product names and search context. Frame recommendation around practical utility.",
    },
}
```

### A4. Trust Validation Layer

Post-generation cross-check between GPT claims and deterministic scores. Zero extra API cost — uses data already computed.

**Validation rules (all categories):**
1. **Winner alignment**: GPT winner must match scoring winner, OR GPT must explicitly explain the override (e.g., "Despite lower specs score, Product B wins on real-world experience")
2. **Magnitude check**: If GPT says "much better" on a dimension, the score gap must be > 15 points. If gap is < 5, language must be "marginally" or "slightly"
3. **Claim-score consistency**: Each dimension mentioned in GPT verdict must align directionally with scores
4. **No phantom advantages**: GPT can't claim an advantage on a dimension where the product actually scores lower

**Category-specific validation:**
| Category | Extra Validation |
|----------|-----------------|
| Electronics | Numeric spec claims checked against extracted spec values |
| Grocery | Nutrition claims checked against extracted nutrition data |
| Supplements | Dosage claims checked against extracted dosage, drug DB status |
| Makeup | Shade range claims checked against extracted shade_range count |
| Skincare | "Gentler" claims checked for irritant ingredients in both products |
| Haircare | "Sulfate-free" / "paraben-free" claims verified against ingredient specs |
| Fragrances | Longevity claims checked against extracted longevity ratings |
| Fashion | Material quality claims checked against extracted material specs |
| Other | General review/rating alignment |

**Output**: `verdict_validation` field in response:
```json
{
  "winner_aligned": true,
  "claims_validated": 5,
  "claims_softened": 1,
  "claims_flagged": 0,
  "confidence_adjustment": null
}
```

### A5. Context Auto-Inference

GPT auto-infers user intent from query + category + personalization. No extra user input required.

**How it works:**
1. Product names parsed → product type detected (already happens in `PRODUCT_PARSER_PROMPT`)
2. Category personality's `context_inference` rule tells GPT how to interpret the product type
3. User's personalization (priorities, budget, lifestyle) provides additional context
4. GPT weaves inferred context into the recommendation: "For daily wear in hot climates, Product A's 12-hour longevity gives it a practical edge"

**No new API calls** — this is prompt instruction only, riding on existing verdict generation.

---

## Part B: Backend Production Hardening

### B1. Account Deletion Endpoint (CRITICAL — App Store Requirement)

**Endpoint**: `DELETE /api/v1/auth/account`
**Auth**: Required (Bearer token)
**Rate limit**: 1/min

**Cascade delete**:
1. Delete all `user_events` where `user_id` matches
2. Delete all `comparison_feedback` where `user_id` matches
3. Delete all `comparisons` where `user_id` matches
4. Delete all `search_logs` where `user_id` matches
5. Clear `preferences` and `behavior_profile` on user record
6. Delete Supabase auth user via admin client
7. Return `{"success": true, "message": "Account and all data deleted"}`

**Safety**: Require re-authentication (password or recent token) before deletion.

### B2. Legal Endpoints

**Endpoints**:
- `GET /api/v1/legal/privacy` → Returns privacy policy as JSON `{title, content, last_updated}`
- `GET /api/v1/legal/terms` → Returns terms of service as JSON `{title, content, last_updated}`

**Implementation**: Static content stored in `app/legal/` directory as markdown files, served via FastAPI endpoint. No auth required.

### B3. Password Strength Upgrade

**Current**: 6-character minimum only
**New**: 10+ characters, must contain: 1 uppercase, 1 lowercase, 1 number

Update `RegisterRequest` and `ChangePasswordRequest` validators in `auth_routes.py`.

### B4. Email Confirmation

Re-enable in Supabase dashboard (not code change). Add:
- `POST /api/v1/auth/resend-verification` — Resends confirmation email
- Rate limit: 3/min

### B5. App Version Check Endpoint

**Endpoint**: `GET /api/v1/app/version`
**No auth required**

```json
{
  "min_version": "1.0.0",
  "latest_version": "1.2.0",
  "force_update": false,
  "update_url_ios": "https://apps.apple.com/app/smartcompare/id...",
  "update_url_android": "https://play.google.com/store/apps/details?id=..."
}
```

Values served from environment variables, updatable without deploy.

### B6. Code Cleanup

1. **Delete** `app/services/comparison_service.py` (289 lines dead code)
2. **Replace** all `print()` with `logger.error()`/`logger.warning()` in `database_service.py` (7 instances)
3. **Add** temp file cleanup for `image_routes.py` uploads (delete after request)

---

## Implementation Strategy

**Team structure**: 4 Opus agents
- **Backend-Scoring**: Category dimensions + scoring engine rewrite
- **Backend-Prompts**: Prompt personalities + trust validation + context inference
- **Backend-Production**: Account deletion, legal, password, version, cleanup
- **Test-QA**: Write tests first (red-green), cross-QA all members' work

**Rules**:
- All features must be 100% complete before team disassembly
- Each member QAs another's work — subpar work gets sent back
- Idle members write red-green tests or wait for QA results
- 80%+ test coverage on all new code
- All 1295+ existing tests must still pass

**Cost impact**: $0 — all changes are prompt modifications (same token count) or pure Python logic. No new API calls added.

---

## Success Criteria

1. Each of the 9 categories produces noticeably different comparison language
2. Electronics comparisons cite numbers; makeup comparisons describe experiences; fragrances evoke character
3. Personalization shifts emphasis WITHOUT hiding information — a "price doesn't matter" user still sees price data
4. Trust validation catches GPT overstatements (measurable via test cases)
5. Account deletion, legal endpoints, password strength, version check all functional
6. All existing tests pass + 80%+ coverage on new code
7. No cost increase per comparison ($0.010 target maintained)
