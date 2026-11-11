# PAGE DESIGN PROPOSAL: one fixed perfume result page (units X4, X5, X6, X7)

Written 2026-11-11 for the founder first, then the build team. It is a proposal: nothing here is built, nothing is switched on, and no production problem is fixed by this document. The facts behind it, with file and line, are in PAGE_INVENTORY.md in the same folder.

## Part 1. In plain English

### What you saw, in one paragraph

You expected one fixed page for every perfume comparison. There is none. Today each part of the page appears only when its data exists. So result 1 had no score bars, result 2 had four and result 3 had one. Three of those five bars were not what their label says: two "longevity" and "projection" bars were really star ratings, one "presentation" bar was really the number of ratings, and the "versatility" win in result 3 came from a default value of 50 standing in for missing data. The sentences the server writes (the verdict lines, the bar captions, the priority names) are English only, so the Arabic page showed English. And "key differences" has never been built: the server always sends an empty list and no version of the app shows it.

### What we propose

One page, the same ten parts in the same order, every time. When we know something, we show it. When we know part of it, we show the part and say what is missing. When we do not know it, the part stays on the page and says so in one short honest line. Nothing vanishes, and nothing is made up.

### The page, top to bottom

1. **Top bar.** Back, the badge, share. Unchanged.
2. **The two perfumes.** Each card always has: a photo (or a grey tile that says "No photo found yet"), the name, a short details line (for example "EDP - 100 ml", or "Size not listed yet"), and the price. The price shows the amount when we found one. If your answer to N5 is "show it with its size", a price for a different bottle shows with its size, for example "85.000 BHD - 125 ml". If no price was found it says "No confirmed price yet."
3. **Why this fits you.** When the written explanation exists, you see it. When it does not (like today, while the OpenAI key is broken), you see one honest line, "The written explanation is unavailable this time. The facts below are what we could confirm.", and then the short fact lines the server builds. These fact lines and your priority chip will now be in Arabic on the Arabic app.
4. **Key differences (new).** A small table of the facts that differ between the two: price, bottle size, price per ml, rating and number of ratings, concentration, and, when we have them, longevity, projection and scent family. If we have too few facts, it says "Not enough confirmed facts to list differences yet."
5. **Score bars.** Always the same five rows for perfumes: Price, Ratings, Longevity, Projection, Value. A row with real data on both sides shows two bars. A row known for one perfume only says "Known for one perfume only" and shows no winner. A row with no data says "Not known yet". Star ratings are never again shown as longevity or projection, and a default of 50 never wins a row.
6. **What we know.** Always three pills: Price, Reviews, Specs. When a price is missing, the price pill says "Not confirmed" instead of disappearing.
7. **Dig deeper: Reviews.** Always there. Per perfume: the star rating and count, or "No rating found yet".
8. **Dig deeper: Pros and cons.** Always there, even when the written explanation is missing; then it says "Pros and cons come from the written explanation, which is unavailable this time."
9. **Dig deeper: Specs.** Always there, as a fixed list of perfume details (concentration, size, scent family, top, heart and base notes, longevity, projection, season, occasion). A detail known for one perfume shows that value and a dash for the other. If nothing is known, it says "Not listed by the stores we can read yet" (a line the app already has).
10. **Feedback card.** Unchanged here. Another session is changing it (unit CL3).

Two things leave the page: the "where the runner-up wins" card (its content now lives in the bars and in key differences) and the "At a glance" row (it never appears on a real result today). The "+53 shoppers" line is already gone in the update; your 2026-10-22 ruling removes it, and unit X9 stops the server sending it.

### What changes for people using the app today

The App Store version and the update both keep today's layout until they take a new update with this page. Of the three server changes:
- X5 (Arabic text as codes) and X7 (key differences) change nothing that today's apps show.
- X6 (honest bars) DOES change today's apps once you switch it on: the fake longevity, projection, presentation and versatility bars disappear, so results show fewer bars, and the verdict line stops citing them. That is the honest fix, but it is visible, so it is your call (question Q3).

### What you would see first

1. X6 first: it is the only server change you can see on your phone without a new app. Repeat result 2 and the two star-rating bars are gone; repeat result 3 and "Armani leads on Versatility" is gone.
2. X5 and X7 next: they are invisible until the new page ships, so their proof is in the saved rows.
3. X4 (the new page) last: it needs your design approval and your reading of every new Arabic line, and it ships in the update AFTER Friday's second update.

No switch is flipped until the OpenAI key works again (N1); all flips are paused until then.

### Questions for you (my recommendation after each)

The full list with reasons is in Part 2, section 10. In short:
- Q1. Drop the character, versatility and presentation bars for perfumes, since we have no honest data for them? Recommended: yes.
- Q2. Fix the perfume bars to Price, Ratings, Longevity, Projection, Value? Recommended: yes.
- Q3. Accept that turning on X6 also removes the fake bars from today's apps? Recommended: yes.
- Q4. Remove the "where the runner-up wins" card? Recommended: yes.
- Q5. Use the new honest line when the written explanation is missing? Recommended: yes.
- Q6. Keep spec values (for example "Woody Aromatic") as the stores wrote them, even in English, for now? Recommended: yes, as a stated limit.
- Q7. Show "EDP - 100 ml" under the name on today's apps too, from the name and the listing? Recommended: yes.
- N5 and N5b (bottle sizes): recommended "show it with its size", then option (a).

## Part 2. Technical tables

Short names as in PAGE_INVENTORY.md (CL, ST, RC, RA, DB, RS, RB, SS, SCS). Proposed flag names avoid the scanner keyword list of the lane header H7 (no KEY, TOKEN, AUTH and similar in a name): ENABLE_HONEST_FRAGRANCE_BARS (X6), ENABLE_RESULT_TEXT_CODES (X5), ENABLE_DIFFERENCES_LIST (X7). Each is new, default OFF, read per call, flag-OFF byte-identical and pinned (H1). New response keys are ADDITIVE; no existing key is removed, renamed or retyped.

### 1. The fixed sections (fragrance category)

| # | Section | Known | Partly known | Not known | Existing keys used | NEW keys (type) | Server | Client |
|---|---|---|---|---|---|---|---|---|
| 1 | Header | as today | n/a | n/a | none | none | none | X4: none |
| 2a | Photo | image | n/a | grey tile + caption `results.honest.noPhoto` | `overview.products[i].image_url` | none | none (photo time budget is X2) | X4: caption under the placeholder |
| 2b | Name | name | n/a | n/a | `overview.products[i].name` | none | none | none |
| 2c | Details line | "EDP - 100 ml" | the known half, e.g. "EDP" | `results.honest.sizeUnknown` | `overview.products[i].variant` (RB:553-610; fragrances use `volume_ml` + `concentration`, RB:572-573) | none: X7 back-fills `variant` from the name's concentration (`extract_concentration`, price_service.py:4076) and the listing size (`price.size`) when specs lack them | X7 | X4: always render the line (today only if truthy, RC:358-366) |
| 2d | Price | amount (+ size per N5) | amount found for another size: per N5 / N5b (section 3) | `results.price.pending` (reused) | `price.{amount, currency, unavailable, reason, size, source_method}`, provenance keys | `price.size_ml` (int, unit X1, not this lane) | X1 | X4: size suffix and per-ml line per N5b |
| 3a | Explanation | AI prose (`overview.winner.reason` when not degraded) | n/a | `results.verdict.noWriteUp` replaces `results.degraded.note` | `comparison.error`, `overview.winner.reason`, `overview.winner.key_tradeoff` (prose moves here from the runner-up card) | `overview.winner.reason_msg`, `overview.winner.key_tradeoff_msg` (Msg, section 4) for the TEMPLATE fallbacks only | X5 | X4 |
| 3b | Fact lines | line1 + line2 rendered from codes in the app language | line1 only | nothing extra (3a's honest line stands) | `scoring_v2.factual_verdict.{line1, line2}` (English, kept for live bundles) | `scoring_v2.factual_verdict.line1_msg`, `.line2_msg` (Msg) | X5 (codes), X6 (no fact from a limited or one-sided dim) | X4 |
| 3c | Priority chip | "Weighted (up) Longevity, (down) Wear value" in the app language | n/a | chip hidden: no priorities is not missing data (a stated exception: it is personal, not a fact about the perfumes) | `scoring_v2.personalization.applied_shifts[*].direction` | `applied_shifts[*].dim` (string, the public dim key, e.g. "wear_value") | X5 | X4: label via `results.dimension.<dim>` (exists, CL ar.json:210-256) |
| 4 | Key differences | up to 6 fact rows | rows with one side "-" | `results.keyDiff.none` | heading `results.keyDifferences` (exists, CL ar.json:131) | `key_differences_v2`: list of DiffRow (section 5); `key_differences` (frozen string[]) filled with English lines | X7 | X4: new block |
| 5 | Score bars | five fixed rows with bars | `results.bars.knownForOne`, no bar, no winner | `results.honest.notKnownYet`, no bar | `scoring_v2.dimensions[*]` | per dim: `state` ("known" / "partial" / "unknown"), `basis` ("price" / "rating" / "specs" / "none"), `delta_msg` (Msg) | X6 (state, basis, honest set), X5 (`delta_msg`) | X4: render all five rows by key, never filter |
| 6 | What we know | three pills | price pill level `results.confidence.level.unconfirmed` when a price is pending | same | `scoring_v2.confidence_legs`, `confidence_details` | none | none | X4: never hide the price pill (today RC:593) |
| 7 | Reviews | per product rating + count + praise | rating without praise, or praise without rating | per product `results.reviews.noRating`; both: `results.reviews.noneFound` (replaces "Reviews are still coming in.") | `reviews.products[i].{rating, rating_count, review_count, review_praise}` | none | none (rating coverage is X8) | X4 |
| 8 | Pros and cons | lists | one side empty: that side `results.honest.notKnownYet` | degraded: `results.prosCons.needsWriteUp`; never removed | `overview.products[i].{pros, cons}`, `comparison.error` | none | none | X4: stop `hideProsCons` (RA:278-288) |
| 9 | Specs | fixed fragrance rows | value on one side, "-" on the other (today dropped, RA ~598) | `results.honest.notListed` (exists) | `specs.products[i].specs`, `specs.specs_comparison.rows`, `metadata.field_status` | none | none | X4: fixed row list from `results.spec.*` keys (exist) |
| 10 | Feedback | existing card | n/a | n/a | as today | none | none | none (CL3 owns it) |

Removed from the fragrance page: the runner-up card (RC:504-510), the "At a glance" row (RA:167; it never renders, inventory row 9a), the cohort badge (already gone in CL). The partial and medical notes (RC:431-454) stay as conditional notes inside section 3 because they describe the result, not a missing field.

### 2. The fixed fragrance bars and the rule for an unknown bar (X6 server, X4 client)

Under ENABLE_HONEST_FRAGRANCE_BARS, for a same-category fragrance pair, `build_dimensions_v2` (SS:3848-3933) emits exactly these five dims, in this order, every time:

| Order | key | Label key (exists) | Honest source | "known" when | "partial" when | "unknown" when |
|---|---|---|---|---|---|---|
| 1 | price | `results.dimension.price` | the two shelf prices | both amounts real AND (sizes equal, or N5b = (b) per-ml) | one amount real, or sizes differ under N5b = (a) | no real amount |
| 2 | reviews | `results.dimension.reviews` | real star ratings (derived excluded, SS:3280-3288) | both real | one real | none real |
| 3 | longevity | `results.dimension.longevity` | specs `longevity` / `longevity_hours`, NOT a Tier-3 model value | both parse to hours or a known phrase (SS:3787-3800 table) | one side | neither. NEVER the review score (today SS:2339-2353 falls back to it) |
| 4 | projection | `results.dimension.projection` | specs `sillage` (SS:3670-3676), NOT a Tier-3 value | both | one | neither. NEVER the review score (today SS:2177) |
| 5 | value | `results.dimension.value` | price and real rating (SS:3314-3420); per ml if N5b = (b) | all inputs real | n/a (treated as unknown) | any input missing |

Not emitted for fragrances under the flag: character (spec-count proxy), versatility (fact-check proxy), presentation (rating-count proxy), wear_value (already skipped, SS:3896). This applies the S80 ruling R-A8, "proxy dimensions without evidence on either side emit caption_key:'limited_data' ... never a 50-sentinel bar" (record/s80/PLAN_S80.md:29), and owner question Q1.

Wire shape of each row (all existing keys keep their types):
- known: as today, plus `state: "known"`, `basis`, `delta_msg`.
- partial and unknown: `score_a = score_b = 75`, `caption_key: "limited_data"`, `confidence: "low"`, `winner: null`, the existing English placeholder `delta_text`, plus `state: "partial" | "unknown"`, `basis`, and for partial `known_side: 0 | 1` (int). This reuses the placeholder shape the live bundles already DROP (DB:82-88; RunnerUpWinsCard.tsx:57), so a new unknown row is invisible to them.

Rules the server enforces under the flag:
1. A default 50 never reaches a fragrance bar: a one-side-missing dim becomes "partial" (today it is emitted with 50 on the missing side, SS:3570-3589).
2. The factual verdict never cites a dim that is not "known": `_top_dim_candidate` and `_runner_up_dim_candidate` (RB:920-989) skip `caption_key == "limited_data"` and any non-known state.
3. The crown (`winner_index`, `overview.winner.product_index`, `scoring_v2.overall_score`) is NOT changed by X6. The overall score still contains the defaults (inventory part c, consequence 5). Whether a winner may be named at all when one product's scores are all defaults is question Q8, outside these units.

Client rule (X4): render the five rows by key in this order whatever the list holds; a missing row renders as "unknown". known: two bars, the per-row winner from `winner` only (never the score heuristic DB:262-268 when `winner` is null). partial: label + `results.bars.knownForOne`, no bar. unknown: label + `results.honest.notKnownYet`, no bar. The legend renders always. A body without `state` (an old cached row, or the flag OFF) is read with today's filter, so a stored row never shows a fake bar it did not have.

### 3. Price and bottle size (depends on N5 / N5b and unit X1)

| Owner answer | Card price line | Price bar | Key-difference rows |
|---|---|---|---|
| N5 = blank (today) | `results.price.pending` | partial or unknown | price row shows "-" for that side |
| N5 = show with size, N5b = (a) | "85.000 BHD - 125 ml" (`results.price.withSize`) and a per-ml line (`results.price.perMl`) on each card | "partial" with `results.price.differentSizes`; no winner, no "cheaper" claim | Price, Size and Price per ml rows, no highlight |
| N5 = show with size, N5b = (b) | as (a) | "known" on price per ml; caption "{{amount}} less per ml" | Price per ml row highlighted |

Recommended: N5 "show with its size", N5b (a). Reason: comparing per ml across bottle sizes favours the big bottle by construction (larger bottles are usually cheaper per ml), so a per-ml "cheaper" claim would not compare like with like; (a) states the facts and makes no claim.

### 4. Server text as codes (X5): the contract

**Shape.** A Msg is an object `{"id": string, "args": object}`. `id` is from the closed vocabulary below. `args` holds only: product indexes (`p`: 0 or 1; the app inserts the name it already shows, isolated for right-to-left), dimension keys (`dim`: a public dim key such as "longevity"), plain numbers (`pct` int, `stars` number with 1 decimal, `amount` number, `hi`/`lo` int hours, `views` int), a currency code (`currency`), booleans (`here`, `cross_tier`), an enum (`level` for sillage), and one proper name (`channel`). Never an English sentence. The app formats numbers with its own digit policy and currency formatter (RC:200, utils/formatNumber).

**Where it travels (all NEW, additive, only when ENABLE_RESULT_TEXT_CODES is ON).** Every old English field stays, byte-identical, for the live bundles.

| New key | Type | Beside the old field | Built at |
|---|---|---|---|
| `scoring_v2.factual_verdict.line1_msg` | Msg | `line1` (RB:1181) | `_format_line1` RB:1073-1098 |
| `scoring_v2.factual_verdict.line2_msg` | Msg | `line2` | `_format_line2` RB:1101-1131; fallback line RB:1175 |
| `scoring_v2.dimensions[i].delta_msg` | Msg | `delta_text` | `_dim_price` SS:3240-3269, `_dim_reviews` SS:3272-3311, `_dim_value` SS:3314-3420, `_compose_delta_text` SS:3592-3734 |
| `scoring_v2.personalization.applied_shifts[i].dim` and the same on `personalization.applied_shifts[i]` | string | `dim_display` | `_compute_applied_shifts` SS:686-716 |
| `overview.winner.reason_msg` | Msg, only when the reason is a template (RB:192-193, RB:1414) | `reason` | RB, after the scrub |
| `overview.winner.key_tradeoff_msg` | Msg, only when the tradeoff is the template (RB:244) | `key_tradeoff` | RB:197-246 |

**Vocabulary.**

| id | args | Replaces (file:line) |
|---|---|---|
| fv.l1.yt_attention | p, views, channel | RB:1084 |
| fv.l1.cheaper | p, pct | RB:1088 |
| fv.l1.premium | p, pct | RB:1089 |
| fv.l1.more_stars | p, stars | RB:1093 |
| fv.l1.despite_lower_reviews | p | RB:1094 |
| fv.l1.leads_on | p, dim | RB:1097 |
| fv.l1.on_top | p | RB:1098 |
| fv.l1.edges_overall | p | RB:1175, RB:192 |
| fv.l1.leads_overall | p | RB:193 |
| fv.l2.ahead_on | p, dim | RB:1112 |
| fv.l2.lighter_wallet | p, pct | RB:1121 |
| fv.l2.rates_higher | p | RB:1129 |
| fv.l2.close_alternative | p | RB:1131 |
| wr.stronger_overall | p (or none) | RB:1414 |
| kt.competitive_on | p, dim | RB:244 |
| dim.limited | none | SS:3246, 3292, 3352, 3369 (and every X6 partial / unknown row) |
| dim.price.less | amount, currency | SS:3260 |
| dim.reviews.same | none | SS:3300 |
| dim.reviews.stars_higher | stars | SS:3302 |
| dim.value.comparable | cross_tier | SS:3381 |
| dim.value.nearly_identical | cross_tier | SS:3386 |
| dim.value.slightly_higher | here, cross_tier | SS:3393-3394 |
| dim.value.noticeably_more | here, cross_tier | SS:3398-3399 |
| dim.value.substantially_stronger | here, cross_tier | SS:3403-3404 (and the prefix SS:3411-3412) |
| dim.comparable | none | SS:3615 |
| dim.longevity.hours | hi, lo | SS:3667 |
| dim.longevity.longer | none | SS:3668 |
| dim.projection.levels | a, b (sillage enum: intimate / moderate / strong / enormous) | SS:3676, only when BOTH free-text values map to the enum; else dim.projection.stronger |
| dim.projection.stronger | none | SS:3677 |
| dim.character.distinctive | none | SS:3679 (needed only while X6 is OFF) |
| dim.versatility.more | none | SS:3681 (same) |
| dim.presentation.more_polished | none | SS:3683 (same) |
| dim.wear_value.higher | none | SS:3685 (same) |

Non-fragrance captions ("+Npt ...", SS:3617 and the generic tail of `_compose_delta_text`) get no id: the live product is fragrance-only, and a caption without `delta_msg` is shown by the new client in English UI only (rule 3 below).

**Client rules (X4).**
1. Msg present and id known: render `t(<client key for id>, args)`, with `p` replaced by the displayed product name and `dim` by `t('results.dimension.<dim>')`.
2. Arabic UI, Msg absent or id unknown: show NO server English sentence; the section shows its honest line (3a stays). English UI: fall back to the old English field.
3. Never concatenate translated fragments; one key per id.

**The region.** No code is needed. The only server-written region text on the page is `cohort_summary.governorate` inside the cohort badge, which exists only in ST and is removed by the ruled X9 (stop sending `cohort_summary`). The closed governorate set already has Arabic names in both bundles (`demographics.governorate.*`, CL ar.json:394-399) if a future surface needs them.

**Prior ruling to reconcile.** S80 ruled the opposite delivery for the same templates: localize them on the server BY VALUE when `output_lang == 'ar'` (R-A10, PLAN_S80.md:31; unit B8, :64), because the store app renders values verbatim and would then show Arabic with no update. It was never built (inventory part b). The two are compatible: codes (X5) for the new app, and optionally Arabic values in the OLD fields for `lang=ar` requests so the store app and the current update also lose the English. The by-value option changes what both live bundles show and does not reach the camera path (no `lang` there, inventory part b). Question Q9.

### 5. Key differences (X7)

**What it lists.** Facts only, no AI, built inside `build_comparison_response` just before RB:2297 from `product_data` (inventory part d). At most 6 rows, in this fixed order, each row only when at least one side is known:

| Order | row `field` | Label key (exists unless marked) | Value per side | `highlight` (which side the row favours) | Source |
|---|---|---|---|---|---|
| 1 | price | `results.price` (exists, "السعر") | amount + currency, or null | the lower price ONLY when both are real and the sizes are equal (N5b (a)) | `price.amount`, `price.currency` |
| 2 | size_ml | `results.spec.size` (exists) | int ml or null | none | `price.size` / X1 `size_ml` / specs `volume` (non-Tier-3) |
| 3 | price_per_ml | NEW `results.keyDiff.perMl` | number or null | none under N5b (a); the lower under (b) | 1 / 2 |
| 4 | rating | `results.dimension.reviews` (exists) | {rating, count} or null; derived excluded | the higher, only when both real and the gap is >= 0.1 | `rating`, `rating_count` |
| 5 | concentration | `results.spec.concentration` (exists) | enum (EDP / EDT / Parfum / Extrait / EDC) or null | none | `extract_concentration(name)` (price_service.py:4076), else non-Tier-3 specs |
| 6 | longevity / sillage / scent_family | `results.spec.longevity`, `results.spec.sillage`, `results.spec.scent_family` (exist) | value text as extracted, or null | none | non-Tier-3 specs |

A row whose two values are equal is left out (it is not a difference). Rows 1-5 are numbers or enums the app formats itself, so they need no translation. Row 6 values are free text as extracted (question Q6).

**Wire.** `key_differences_v2`: list of DiffRow `{"field": string, "values": [v0, v1], "highlight": 0 | 1 | null}` (NEW, additive). The frozen `key_differences` (string[]) is filled with plain English lines built from the same rows (for example "Price: 133.460 BHD vs not confirmed"), because no bundle renders it (RS:437, ST RS:414) and the URL path's B4 already fills it with text. The link path keeps its own body (url_extraction_service.py:1495-1506) and is outside X7 (its result fails during the outage anyway: LLM_UNAVAILABLE, :1483-1493).

**Variant back-fill (X7, same helper).** When specs give no `volume_ml` / `concentration`, `_compose_variant_string` (RB:553-610) uses the concentration from the name and the listing size. Unlike the rest of X7 this IS visible on both live bundles (the variant line, RC:358-366, ST RC:304), so it is question Q7.

**Today's three rows, as X7 would read them (by the code, not measured):** R1: Price (133.460 BHD vs "-"), concentration equal (left out): 1 row. R2: Price (one side), Ratings 4.6 (85) vs 4.8 (6,600): 2 rows. R3: Price (one side; Armani's found 40 ml price only if N5 = show), Size 40 ml vs "-": 1-2 rows. When no row qualifies the block shows `results.keyDiff.none`.

### 6. Every new user-visible string

Separator note: the app joins parts with the middle dot U+00B7 (for example `results.reviews.ratingWithCount`); this document writes it as " - " outside Arabic lines to stay ASCII. Arabic drafts follow src/i18n/.copy-policy.json (no banned superlatives, none of the scary words, never the word for "estimated") and the calm tone of the existing lines (for example `results.price.pending` "لا يوجد سعر مؤكد بعد.", CL ar.json:146). Every Arabic draft below is marked [NATIVE READ]: the owner reads each before the OTA (the S81-11 owner step practice).

#### 6a. Page strings (client, X4)

| Key (proposed) | English | Arabic draft | Reuse note |
|---|---|---|---|
| results.honest.noPhoto | No photo found yet | لا توجد صورة بعد [NATIVE READ] | new |
| results.honest.sizeUnknown | Size not listed yet | الحجم غير مذكور بعد [NATIVE READ] | new; the long form already exists as `results.spec.size` + `results.honest.notListed` (RA:149-151) |
| results.honest.notKnownYet | Not known yet | غير معروف بعد [NATIVE READ] | new |
| results.honest.notListed | Not listed by the stores we can read yet | (exists, CL ar.json:702) | REUSED for the empty Specs table |
| results.price.pending | No confirmed price yet. | (exists, CL ar.json:146) | REUSED |
| results.price.withSize | {{price}} - {{size}} ml | {{price}} · {{size}} مل [NATIVE READ] | new (N5) |
| results.price.perMl | {{price}} per ml | {{price}} لكل مل [NATIVE READ] | new (N5b) |
| results.price.differentSizes | Different bottle sizes, so no cheaper claim | حجما العبوتين مختلفان، لذا لا نقارن السعر مباشرة [NATIVE READ] | new (N5b (a)) |
| results.verdict.noWriteUp | The written explanation is unavailable this time. The facts below are what we could confirm. | الشرح المكتوب غير متاح هذه المرة. ما يلي هو ما استطعنا تأكيده. [NATIVE READ] | new; replaces `results.degraded.note` on the fixed page (that note says the prices below are real even above a missing price, T4 G3) |
| results.keyDifferences | Key Differences | (exists, CL ar.json:131) | REUSED heading |
| results.keyDiff.none | Not enough confirmed facts to list differences yet. | لا تتوفر حقائق مؤكدة كافية لعرض الفروقات بعد. [NATIVE READ] | new |
| results.keyDiff.perMl | Price per ml | السعر لكل مل [NATIVE READ] | new |
| results.bars.knownForOne | Known for one perfume only | معروف لعطر واحد فقط [NATIVE READ] | new |
| results.confidence.level.unconfirmed | Not confirmed | غير مؤكد [NATIVE READ] | new |
| results.reviews.noRating | No rating found yet | لم نجد تقييماً بعد [NATIVE READ] | new |
| results.reviews.noneFound | No ratings or reviews found for these two yet. | لم نجد تقييمات أو آراء لهذين العطرين بعد. [NATIVE READ] | new; replaces "Reviews are still coming in." (it promises arrival, T4 G6) |
| results.prosCons.needsWriteUp | Pros and cons come from the written explanation, which is unavailable this time. | الإيجابيات والسلبيات تأتي من الشرح المكتوب، وهو غير متاح هذه المرة. [NATIVE READ] | new |
| results.spec.notes_top / notes_heart / notes_base / scent_family / longevity / sillage / season / occasion / concentration / size | (exist) | (exist, CL ar.json:793-841) | REUSED as the fixed Specs rows |

#### 6b. Message strings (client keys for the X5 vocabulary; `{{name}}` = the displayed product name, `{{dim}}` = `results.dimension.<dim>`)

The English keeps today's server wording, so the English UI does not change, except the three proxy captions, reworded to pass the server's own banned-word list (app/models/scoring_v2.py:9-14 lists "better" among the banned caption words).

| Client key | English | Arabic draft |
|---|---|---|
| results.msg.fv.l1.yt_attention | {{name}} draws far more reviewer attention (~{{views}} YouTube views, led by {{channel}}). | {{name}} يحظى باهتمام أكبر بكثير من المراجعين (نحو {{views}} مشاهدة على يوتيوب، أبرزها لدى {{channel}}). [NATIVE READ] |
| results.msg.fv.l1.cheaper | {{name}} comes in {{pct}}% cheaper. | {{name}} أرخص بنسبة {{pct}}%. [NATIVE READ] |
| results.msg.fv.l1.premium | {{name}} carries a {{pct}}% price premium for the upgrade. | سعر {{name}} أعلى بنسبة {{pct}}% مقابل الترقية. [NATIVE READ] |
| results.msg.fv.l1.more_stars | {{name}} earns {{stars}} more stars from reviewers. | تقييم {{name}} أعلى بـ {{stars}} نجمة لدى المراجعين. [NATIVE READ] |
| results.msg.fv.l1.despite_lower_reviews | {{name}} edges ahead despite slightly lower reviews. | {{name}} يتقدم قليلاً رغم تقييمات أقل بقليل. [NATIVE READ] |
| results.msg.fv.l1.leads_on | {{name}} leads on {{dim}}. | {{name}} يتقدم في {{dim}}. [NATIVE READ] |
| results.msg.fv.l1.on_top | {{name}} comes out on top. | {{name}} يتقدم في المحصلة. [NATIVE READ] |
| results.msg.fv.l1.edges_overall | {{name}} edges ahead on the overall picture. | {{name}} يتقدم قليلاً في الصورة العامة. [NATIVE READ] |
| results.msg.fv.l1.leads_overall | {{name}} leads on the overall picture. | {{name}} يتقدم في الصورة العامة. [NATIVE READ] |
| results.msg.fv.l2.ahead_on | {{name}} pulls ahead on {{dim}}. | {{name}} يتقدم في {{dim}}. [NATIVE READ] |
| results.msg.fv.l2.lighter_wallet | {{name}} stays {{pct}}% lighter on the wallet. | {{name}} أخف على الجيب بنسبة {{pct}}%. [NATIVE READ] |
| results.msg.fv.l2.rates_higher | {{name}} rates a touch higher with shoppers. | تقييم {{name}} أعلى قليلاً لدى المتسوقين. [NATIVE READ] |
| results.msg.fv.l2.close_alternative | {{name}} stays in the conversation as a close alternative. | {{name}} يبقى بديلاً قريباً. [NATIVE READ] |
| results.msg.wr.stronger_overall | {{name}} is the stronger overall pick. | {{name}} هو الأقوى في المجمل. [NATIVE READ] |
| results.msg.kt.competitive_on | {{name}} stays competitive on {{dim}}. | {{name}} يبقى منافساً في {{dim}}. [NATIVE READ] |
| results.msg.dim.limited | (no caption; the row shows its state line) | (none) |
| results.msg.dim.price.less | {{price}} less | أقل بـ {{price}} [NATIVE READ] |
| results.msg.dim.reviews.same | Same rating | التقييم نفسه [NATIVE READ] |
| results.msg.dim.reviews.stars_higher | {{stars}} stars higher | أعلى بـ {{stars}} نجمة [NATIVE READ] |
| results.msg.dim.value.comparable | Comparable value | قيمة متقاربة [NATIVE READ] |
| results.msg.dim.value.nearly_identical | Nearly identical value | قيمة شبه متطابقة [NATIVE READ] |
| results.msg.dim.value.slightly_higher_here / _other | Slightly higher value here / on the other side | قيمة أعلى قليلاً هنا / لدى الآخر [NATIVE READ] |
| results.msg.dim.value.noticeably_more_here / _other | Noticeably more per dinar here / on the other side | قيمة أكبر بوضوح لكل دينار هنا / لدى الآخر [NATIVE READ] |
| results.msg.dim.value.substantially_stronger_here / _other | Substantially stronger value ratio / Substantially stronger value on the other side | قيمة أقوى بكثير هنا / لدى الآخر [NATIVE READ] |
| results.msg.dim.value.cross_tier | Across tiers: {{text}} | عبر فئات سعرية مختلفة: {{text}} [NATIVE READ] |
| results.msg.dim.comparable | Comparable | متقارب [NATIVE READ] |
| results.msg.dim.longevity.hours | {{hi}}h vs {{lo}}h | {{hi}} ساعة مقابل {{lo}} ساعة [NATIVE READ: the counted noun after 3-10 is plural in Arabic; plural forms may be needed] |
| results.msg.dim.longevity.longer | Longer-lasting | ثبات أطول [NATIVE READ] |
| results.msg.dim.projection.levels | {{a}} vs {{b}} projection | انتشار {{a}} مقابل {{b}} [NATIVE READ] |
| results.msg.dim.projection.stronger | Stronger projection | انتشار أقوى [NATIVE READ] |
| results.msg.sillage.intimate / moderate / strong / enormous | close to the skin / moderate / strong / very strong | قريب من البشرة / معتدل / قوي / قوي جداً [NATIVE READ] |
| results.msg.dim.character.distinctive | More distinctive | طابع أكثر تميزاً [NATIVE READ] (only while X6 is OFF) |
| results.msg.dim.versatility.more | More versatile | استخدامات أكثر تنوعاً [NATIVE READ] (same) |
| results.msg.dim.presentation.more_polished | More polished presentation | تغليف أكثر أناقة [NATIVE READ] (same; today "Better presented") |
| results.msg.dim.wear_value.higher | Higher everyday value | قيمة يومية أعلى [NATIVE READ] (same; today "Better everyday value") |

Priority-chip names need no new string: the app renders `results.dimension.<dim>` (CL ar.json:210-256; e.g. "wear_value" -> "قيمة الاستخدام", "longevity" -> "الثبات"). The English chip then reads "Wear value" / "Character" instead of today's "value per wear" / "scent character" (a small stated wording change in the English UI of the new app only).

Count (measured from the two tables above): 14 new page strings (6a) + 40 new message strings (6b: 15 verdict / reason / tradeoff lines and 25 caption and sillage strings, each "/" alternative counted separately) = 54 new Arabic strings for the owner's native read. Reused: `results.honest.notListed`, `results.price.pending`, `results.keyDifferences`, `results.price`, plus the `results.spec.*` and `results.dimension.*` families.

### 7. What the two LIVE bundles show (store 683f56c0 and OTA f1e20c39)

| State | Store binary 683f56c0 | OTA f1e20c39 (= main a74caba7 client) |
|---|---|---|
| All three flags OFF (default after merge) | unchanged, byte-identical bodies (each unit pins flag-OFF identity) | unchanged |
| ENABLE_RESULT_TEXT_CODES ON (X5) | unchanged: only new keys are added; every English field is the same text; DB, FactualVerdict and PersonalizationChip read only the old fields | unchanged |
| ENABLE_DIFFERENCES_LIST ON (X7), without the variant back-fill | unchanged: `key_differences` is never rendered (ST RS:414); `key_differences_v2` is unknown to it | unchanged (RS:437) |
| X7 variant back-fill ON | CHANGES: a details line such as "EDP - 100ml" appears under the name where specs were empty (ST RC:304) | same change (RC:358-366) |
| ENABLE_HONEST_FRAGRANCE_BARS ON (X6) | CHANGES: the proxy bars vanish (R2 would show 1 bar instead of 4; R3 0 instead of 1); line1 / line2 stop citing a non-known dim (R3 would read "... edges ahead on the overall picture." instead of "... leads on Versatility."); the new unknown rows are invisible (limited_data is dropped, DB:82-88) | same change |
| Any flag ON, the share invitee view | `key_differences` text could reach a shared view (referral_service.py:178); whether a web page renders it is UNVERIFIED | same |

So, unless the owner says yes to Q3 (X6) and Q7 (variant back-fill), nothing changes for people on today's apps.

### 8. Slicing plan

| Slice | Unit | Kind | Needs the client? | Visible on today's apps when ON? | Depends on | Why this place in the order |
|---|---|---|---|---|---|---|
| 1 | X6 HONEST BARS (ENABLE_HONEST_FRAGRANCE_BARS) | backend, dark | no | YES (proxy bars and proxy verdict facts disappear) | Q1, Q2, Q3; N1 proven before its flip | the soonest thing the owner can see on the phone without a new app; smallest footprint (SS `build_dimensions_v2` + RB candidates) |
| 2 | X5 TEXT CODES (ENABLE_RESULT_TEXT_CODES) | backend, dark | yes, for anything visible | no | the X6 vocabulary for partial / unknown rows (`dim.limited`); Q9 | the new page cannot render Arabic without it; ship it before X4 so X4 is built against real bodies |
| 3 | X7 DIFFERENCES (ENABLE_DIFFERENCES_LIST) | backend, dark | yes (block); the variant back-fill no | only the back-fill (Q7) | N5 / N5b for the price rows; X1 for `size_ml` (optional: `price.size` works without it) | independent of X5; X7 and X5 both edit RB near RB:2297 and RB:1073-1181, so run them one after the other, not in parallel, to avoid rebase rounds |
| 4 | X4 FIXED PAGE | client, merged to main, shipped by a later OTA | it is the client | n/a (needs the OTA) | design approval (this document), the owner's native read of the 54 strings, X5 / X6 / X7 merged (dark is enough to build), Friday's SECOND OTA out first (X4 cannot make it, incident report X4 row), ENABLE_FEEDBACK_V2 ON before any OTA from a main that carries CL3 (risk K1) | the page shell can be built against fixtures while slices 1-3 are in review; the OTA goes out only after the flags it reads are ON and canaried |

Flip order after N1 is proven (one flag per canary window, the relay sets each on the owner's yes): X6, then X5, then X7, then the X4 OTA. Each window repeats the slice's proof below.

### 9. PROOF ON THE PHONE per slice (H6: nothing is called fixed until the phone shows it)

Golden set (incident report section 4): 1 Aventus vs Layton, 2 La Vie Est Belle vs YSL Libre, 3 Acqua di Gio Profumo vs Eros EDP, 4 Sauvage EDP vs Bleu de Chanel EDP, 5 Baccarat Rouge 540 vs Khamrah. Pairs 1-3 are no longer never-compared, so each first proof includes pair 4 or 5. The free tier allows 3 comparisons a day (N6): a five-pair proof spreads over two days unless N6 (b) is ruled. Each claim records the row id and the UTC time.

| Slice | Pairs | Must be visible on the phone (store app AND updated app) | Backing row / log check |
|---|---|---|---|
| X6 | 2 and 3, plus 4 | pair 2 (while specs are still empty): no "Longer-lasting", no "Stronger projection", no "Better presented" bar; pair 3: no "More versatile" bar and the verdict line does not say "leads on Versatility". If the AI key works and real longevity / sillage arrive, a longevity or projection bar with "Nh vs Nh" is CORRECT, not a regression | the new rows: `scoring_v2.dimensions` holds exactly price, reviews, longevity, projection, value; longevity / projection carry `state` "unknown" or "partial" and `caption_key` "limited_data" when specs lack the value; no character / versatility / presentation; `factual_verdict.line1` does not name a non-known dim; `winner_index` equals the value a flag-OFF run gives (the crown did not move) |
| X5 | 1, 2, 3 | nothing new on today's apps (state this in the report, it is expected) | each row carries `factual_verdict.line1_msg` / `line2_msg`, `delta_msg` on every dim, `applied_shifts[*].dim`; every `id` is in the vocabulary; the English fields equal a flag-OFF body |
| X7 | 1, 2, 3, plus 5 | nothing on today's apps except, if Q7 = yes, the "EDP" / size details line under the names | `key_differences` non-empty (at least the price row on pairs 1-3, the rating row on pair 2); `key_differences_v2` rows match section 5; the completeness score's key-differences point turns 1 |
| X4 | all five, Arabic UI, on the UPDATED app | the five screenshots show the same ten sections in the same order; every empty field shows its Arabic honest line; no English sentence except product names and spec values (Q6); key differences block present; five bar rows; the store app keeps today's layout | the completeness score (incident report section 4) printed next to each screenshot; the rows carry the X5 / X6 / X7 keys; the device runs the OTA (N3 check: the Home headline "قارن بين عطرين.") |

A hermetic test run of any slice is necessary and is not the production proof.

### 10. Open questions for the owner (one question each, my recommendation, and why)

| # | Question | Recommended | Why |
|---|---|---|---|
| Q1 | Drop the character, versatility and presentation bars for perfumes? | Yes | each is a proxy with no honest source (spec count, fact-check share, rating count; inventory part c); the S80 ruling R-A8 already says no proxy bar without evidence |
| Q2 | Fix the perfume bars to Price, Ratings, Longevity, Projection, Value? | Yes | these five have a real source when data exists; a fixed list is what makes the page the same every time |
| Q3 | Accept that switching on X6 also removes the fake bars from today's apps? | Yes | it is the honest fix and needs no update; the cost is fewer bars on sparse results |
| Q4 | Remove the "where the runner-up wins" card from the perfume page? | Yes | it can only appear when it has content (the opposite of a fixed page); its content now lives in the bars, key differences and the explanation |
| Q5 | Replace the grey "write-up unavailable ... the scores and prices below are real" note with "The written explanation is unavailable this time. The facts below are what we could confirm."? | Yes | the old note claims real prices directly above a missing price (T4 G3) |
| Q6 | Keep spec values (notes, scent family, season) as the stores wrote them, possibly English, in the first version? | Yes, as a stated limit | translating free text is a separate, AI-dependent job; labels are already Arabic |
| Q7 | Show "EDP - 100 ml" under the names on today's apps too (from the name and the listing)? | Yes | it is a fact we already hold, and it fills an empty line on both live apps without an update |
| Q8 | Should a winner be named when one perfume's scores are all defaults (result 3: Armani "won" with every score at 50)? | Not in these units: send it to the result-gate lane as its own ruling | changing the crown touches the frozen winner keys and History / Home readers (the B1 note on `winner_index`, incident report X3 row); X6 only stops defaults from showing as bars or verdict facts |
| Q9 | Also send ARABIC text in the old English fields when the app asks in Arabic (the S80 R-A10 plan), so today's apps lose the English too? | Yes, as a later separate dark unit after X5 | it reaches the store app with no update; it does not reach the camera path (no language sent there) and it changes what both live apps show, so it needs its own window |
| Q10 | In Arabic, when the app meets a server sentence it has no code for, hide it rather than show English? | Yes | showing English on the Arabic page is the defect we are removing; the section's honest line stays |
| Q11 | Remove the "At a glance" row? | Yes | it never appears on a real result today (inventory row 9a) |
| N5 | When a found price is for a different bottle size: blank it (today) or show it with its size? | Show it with its size | a real price with its size is a fact; blanking it hid three real prices on 2026-11-11 (T1) |
| N5b | Then (a) both prices with sizes, a per-ml line, no cheaper claim, or (b) compare per ml? | (a) | per ml favours the bigger bottle by construction; (a) states facts and makes no claim (section 3) |

### 11. Assumptions (each with why it beats the alternative)

1. **Codes, not finished Arabic sentences, in the new keys.** The app already owns every Arabic string and the copy-policy fence (src/i18n/.copy-policy.json, run by the jest copy-policy test); server-side Arabic would need a second copy pipeline and a server copy fence. The alternative (by-value Arabic) is kept as Q9 for the live apps only.
2. **Product index, not product name, in `args`.** The app already shows its own name for each card; passing the index keeps one source for the name and lets the app isolate Latin names in right-to-left text.
3. **Unknown and partial bars reuse the `limited_data` placeholder shape.** Both live bundles already drop it (DB:82-88, RunnerUpWinsCard.tsx:57), so the new rows cost the live apps nothing; a brand-new row shape would risk the dev-only zero-score node (DB:95-110) or a contract breach.
4. **X6 does not move the crown.** Moving it would touch frozen keys read by History, Home and Profile; the honest-display fix and the winner question are separable (Q8).
5. **`key_differences` (frozen string[]) is filled with English text, and the structured list rides in a new key.** No bundle renders the old key (RS:437, ST RS:414), and retyping it is forbidden (H1).
6. **The live product is fragrance-only**, so X5 / X6 cover the fragrance templates; other categories keep their English captions with no code (stated limit).
7. **Line numbers in this document were measured on the exports at a74caba7 and 683f56c0 in this run.** Row values for R1-R3 come from the verified extracts T1 and T4; this round read no database.

### 12. Not verified in this round

- Whether ENABLE_URL_MODE_V2 and ENABLE_SMART_PICK_VERDICT_CAPTION are ON in production (both readers named in PAGE_INVENTORY.md part b and d).
- Whether a web share page outside this repo renders `key_differences`.
- Whether `extract_concentration` reads "Profumo" as a concentration.
- Versace's fact-check object in row e2320ca7 (the 30 is consistent with an all-unverified fact-check, SS:2096).
- Every jest, tsc and pytest check of the claims is DEFERRED TO RED (PAGE_INVENTORY.md, last section).
