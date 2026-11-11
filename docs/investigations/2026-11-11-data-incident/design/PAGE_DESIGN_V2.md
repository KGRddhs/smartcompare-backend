# PAGE DESIGN v2: one fixed perfume result page (units X4, X5, X6, X7)

Written 2026-11-11 by the finalizer of the S92-FIX incident lane. v2 replaces PAGE_DESIGN_PROPOSAL.md (v1), which stays unchanged in this folder. It applies every finding of PAGE_SKEPTIC.md (disposition in section 13), the orchestrator's binding decisions and the owner rulings of 2026-11-11 (table below). A stopped run left a partial v2 written before two owner rulings arrived; its text was reused only where this run re-measured it.

READ-ONLY round: no test, build, network, git write, package manager, production probe or .env read. Every file:line that is new or changed in v2 was re-read in this run on the plain exports: main a74caba7 (app/ and SmartCompareApp/src, the client equal to the live OTA bundle f1e20c39) and the store client 683f56c0. Short names as in PAGE_INVENTORY.md (CL, ST, RC, RA, DB, RS, RB, SS, SCS), plus PS = app/services/price_service.py, HR = app/api/home_routes.py, HES = SmartCompareApp/src/components/HomeEditorialSections.tsx, IR = record/incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md, T1 = record/incident/T1_trace.md, X1S = design/X1_SKEPTIC.md, X1B = design/X1_BRIEF_DRAFT.md. Nothing here is built or switched on. No production problem is fixed by this document. A merged unit is "merged, NOT yet proven" until the owner's phone shows it (H6).

## Binding decisions and owner rulings applied

| # | Decision | Where it lands |
|---|---|---|
| B1 | The price row follows the X1 wire shape: `price.amount` stays null for an off-size listing; the other bottle rides in a NEW additive key. Today's apps show nothing new and make no cross-size claim. | sections 3, 5, 7 |
| B2 | A size describes the product only when it comes from the typed name or from a price accepted at the pair's basis. | sections 1 (2c), 3, 5 |
| B3 | The value bar is unknown whenever the price bar is not known. | section 2 |
| B4 | Every place a default or a proxy can still reach the user is brought under the X6 flag or listed as a stated limit with its own owner question. | section 2.4, section 12 |
| B5 | The live product is NOT fragrance-only today (ENABLE_FRAGRANCE_ONLY_GATE is OFF): every rule states what a non-fragrance result does. | section 0 |
| B6 | The X5 contract has no nested translated fragment, an id for every branch of every template, typed args (numbers stay numbers), and separate ids for the verdict line and the winner reason. | section 4 |
| B7a | OWNER RULING (N5 / N5b): show each found price with its bottle size and a per-ml line; make no cheaper claim when the two sizes differ. No longer a question. | sections 3, 5, 6 |
| B7b | OWNER RULING: the cohort line is removed. No longer a question (X9 stops the server sending it; CL already removed the badge, RC:600-601). | section 1 |
| B7c | OWNER RULING "No, wait for Claude": no bridge credential. Production has NO AI text until the first Claude text role is live (days away). The honest states of the explanation, the pros and cons, the review text and the specs are what the founder sees first. | Part 1 opening, sections 8 and 9 (every check that needs AI text is marked "after the Claude switch") |

## Part 1. In plain English

### The coming days: what the page shows with no AI text

Until the Claude switch, every comparison runs without AI text: no written explanation, no pros and cons, no review highlights and, in practice, no perfume details (the specs come from AI extraction, T1 rows "specs A {}"). Prices, photos, star ratings and the server's own short fact lines do not need AI and show whatever the search found.

| Section | Today's apps during these days (store app and current update) | The new page with no AI text (mock state 1) |
|---|---|---|
| Top bar | back, badge, share | same |
| Photos | the photo, or a grey tile with no words | the photo, or a grey tile that says "No photo found yet" |
| Details line | absent (brand and variant are empty on this path) | "EDP - 100 ml" from the typed name and an accepted price, or "Size not listed yet" |
| Price | the amount, or "No confirmed price yet." (a price found for another bottle size is hidden) | the amount with its bottle size and a per-ml line; a price found for another bottle size is shown with its own size and "Different bottle sizes, so we do not compare the prices." |
| Why this fits you | a grey note that says the scores and prices below are real, then two ENGLISH fact lines, also on the Arabic app | "The written explanation is unavailable this time. The facts below are what we could confirm.", then the same two fact lines in the app's language |
| Key differences | not shown (never built) | price, per-ml price, size and concentration rows where known |
| Score bars | 0 to 4 bars, some of them star ratings shown as longevity or projection, English captions | the same five rows every time; an unknown row says "Limited data" |
| What we know | the price pill disappears when a price is missing | three pills; a missing price says "Not confirmed" |
| Shoppers line | "+53 shoppers" on the store app only (removed in the update) | gone |
| Reviews | the rating if a real one was found, else "Reviews are still coming in." | per perfume the rating or "No rating available", and "Review highlights are unavailable this time." |
| Pros and cons | the whole row is removed | always there: "Pros and cons come from the written explanation, which is unavailable this time." |
| Specs | the two names and nothing else | the fixed list of perfume details; with nothing known it says "Not listed by the stores we can read yet" |
| Feedback card | unchanged | unchanged (another session owns it) |

Which reaches the founder's phone first, the new page or the Claude switch, depends on dates not fixed yet (UNVERIFIED). The new page shows the right-hand column whenever a result has no AI text, so this is also the state any later AI outage would show.

### What you saw, and what we propose

There is no fixed perfume page today: each part appears only when its data exists, so result 1 had no score bars, result 2 had four and result 3 had one. Three of those five bars were not what their label says (two were star ratings, one was the number of ratings) and Armani's "versatility" win came from a default value of 50 standing in for missing data. The server's sentences are English only, and "key differences" was never built.

We propose one page, the same ten parts in the same order, every time. Known facts are shown. A part we know only for one perfume says so. A part we do not know stays on the page with one short honest line. Nothing vanishes, nothing is made up, and a default value never wins anything you can see.

### The page, top to bottom

1. **Top bar.** Back, the badge, share. Unchanged.
2. **The two perfumes.** A photo or a grey tile that says "No photo found yet"; the name; a details line ("EDP - 100 ml", or "Size not listed yet"); the price with its bottle size and a per-ml line. A size appears in the details line only when it came from the name you typed or from a price accepted for the pair's bottle size. A price found for another bottle size is shown with that bottle's size and the line "Different bottle sizes, so we do not compare the prices."; nothing on the page then says which is cheaper.
3. **Why this fits you.** The written explanation when it exists; otherwise one honest line. Then the two short fact lines the server builds, in the app's language.
4. **Key differences (new).** Price, price per ml, size, rating, concentration and, when known, longevity, projection and scent family. With too few facts it says so.
5. **Score bars.** The same five rows for perfumes: Price, Reviews, Longevity, Projection, Value. Both sides known: two bars. One side known: "Known for one perfume only", no bars, no winner. Not known: "Limited data". Value is shown only when price and ratings are both known.
6. **What we know.** Always three pills: Price, Reviews, Specs.
7. **Dig deeper: Reviews.** Always there: per perfume the rating and count, then the review highlights or their honest line.
8. **Dig deeper: Pros and cons.** Always there, with its honest line when the explanation is missing.
9. **Dig deeper: Specs.** Always there, a fixed list of perfume details; a detail known for one perfume shows a dash for the other.
10. **Feedback card.** Unchanged here; another session owns it (unit CL3).

Two things leave the perfume page: the "where the runner-up wins" card and the "At a glance" row (it never appears on a real result today, PAGE_INVENTORY.md row 9a). The shoppers line is already gone in the update; X9 removes it from the store app.

### What changes for people on today's apps

Both live bundles (the store app 683f56c0 and the update f1e20c39) read the live server and send no app-version signal, so every server change reaches both at once. They keep today's layout until they take a later update with this page.
- X5 (text as codes) and the X7 list change nothing they show.
- X6 (honest bars) DOES change what they show once it is switched on: the star and count bars and the default-50 win stop appearing and stop being cited in the fact lines; the runner-up sentence and the AI's scoring notes stop using them; with a yes to Q3 an unknown bar shows a "Limited data" row they can already draw.
- The X7 details-line fill ("EDP - 100 ml" under the name) is visible on today's apps: its own switch and its own question (Q10).
- The other-bottle price (unit X1) is invisible on today's apps by construction (B1): they keep "No confirmed price yet." and make no claim.

### The order the pieces ship in

1. X6 first (honest bars): the only change visible on today's apps without an update; its main proof works best with no AI text.
2. X5 and X7 next: invisible until the new page ships; their proof is in the saved rows.
3. X4 (the new page) last: it needs the founder's approval of this design and a native read of every new Arabic line, and it ships in the update AFTER Friday's second update (IR:103).

Switches stay paused while AI calls fail (H2). With the "wait for Claude" ruling that pause lasts until the Claude switch works, unless the founder rules otherwise (Q16).

## Part 2. Technical tables

Proposed flags (new, default OFF, read per call, flag-OFF byte-identical and pinned, H1; names avoid the H7 scanner words): ENABLE_HONEST_FRAGRANCE_BARS (X6), ENABLE_RESULT_TEXT_CODES (X5), ENABLE_DIFFERENCES_LIST (X7 list), ENABLE_DETAILS_LINE_FILL (X7 details-line fill, split so each flip has one visible effect). New response keys are ADDITIVE; no key either bundle reads is removed, renamed or retyped.

### 0. Fragrance and non-fragrance results (B5)

ENABLE_FRAGRANCE_ONLY_GATE is OFF (H2; IR:102 places it after the v3 Terms and the second OTA), so other categories are served today. A pair uses the category dims only when both canonical categories match (`same_category`, SS:3880-3881).

| Rule | Fragrance pair | Non-fragrance or mixed pair |
|---|---|---|
| Ten fixed sections (X4) | all ten, fixed order | all ten, same order; sections 4, 5 and 9 differ as below |
| Bars (X6) | the fixed five rows of section 2 | UNCHANGED by X6: today's list (three core dims, plus up to five category dims for a same-category pair, SS:3848-3933). X4 renders it with today's filter (DB:82-88) and shows `results.dimensions.limited_data` under the heading when no row survives, instead of an empty section |
| Defaults reaching the user | brought under X6 (section 2.4) | stated limit L-NF1, question Q14 |
| Text codes (X5) | every fragrance template has an id | every other template has an id too (section 4); no category is left without codes |
| Key differences (X7) | price, per ml, size, rating, concentration, longevity, sillage, scent family | price, per ml and rating rows only (size from the typed name or an accepted price still applies; concentration is a fragrance rule) |
| Details-line fill (X7) | concentration and size per B2 | unchanged: today's `_compose_variant_string` (RB:553-610) |
| Specs (X4) | the fixed perfume row list | today's table (rows both sides populate, RA:206-224) plus `results.honest.notListed` when empty |
| Price with size (X1 key) | section 3 | non-fragrance pairs take the target-None path and the legacy both-pending outcome (PS:2348-2354, X1B E5); X1's eligibility test refuses them, so they show today's pending line |
| Strings that say "perfume" | as written | `results.bars.knownForOne` is reached only by fragrance rows (X6), so no product-neutral twin is needed |

### 1. The fixed sections

| # | Section | Known | Partly known | Not known | Keys read (existing) | NEW keys | Server | Client (X4) |
|---|---|---|---|---|---|---|---|---|
| 1 | Header | as today | n/a | n/a | none | none | none | none |
| 2a | Photo | image | n/a | grey tile + `results.honest.noPhoto` | `overview.products[i].image_url` | none | none (photo time is X2) | caption under the placeholder (today none, ProductImage.tsx per PAGE_INVENTORY.md row 2a) |
| 2b | Name | name | n/a | n/a | `overview.products[i].name` | none | none | none |
| 2c | Details line | "EDP - 100 ml" | the known half | `results.honest.sizeUnknown` | `overview.products[i].variant` | none | X7 fill under ENABLE_DETAILS_LINE_FILL, B2 sizes only (section 5.3) | always render the line (today only if truthy, RC:358) |
| 2d | Price | amount, `results.price.withSize`, `results.price.perMl` (section 3) | other-size listing from the X1 key + `results.price.differentSizes` | `results.price.pending` (reused) | `price.{amount, currency, unavailable, reason, source_method}` | X1's `price.offsize_listing` and the size / per-ml keys (section 3) | X1 | section 3 |
| 3a | Explanation | AI prose when not degraded | n/a | `results.verdict.noWriteUp` | `comparison.error`, `overview.winner.reason`, `overview.winner.key_tradeoff` | `overview.winner.reason_msg`, `overview.winner.key_tradeoff_msg` | X5 | a template reason renders from its Msg; AI prose as received |
| 3b | Fact lines | line1 + line2 from codes | line1 only | 3a's honest line stands | `scoring_v2.factual_verdict.{line1, line2}` | `factual_verdict.line1_msg`, `.line2_msg` | X5 codes, X6 (no fact from a row that is not known) | section 4 client rules |
| 3c | Priority chip | dims in the app language | n/a | chip hidden (a personal setting, not a fact: stated exception) | `personalization.applied_shifts[*].direction` | `applied_shifts[*].dim` | X5 | label via `results.dimension.<dim>` |
| 4 | Key differences | up to 8 fact rows | a row with one side "-" | `results.keyDiff.none` | heading `results.keyDifferences` (CL ar.json:131) | `key_differences_v2` | X7 | new block |
| 5 | Score bars | section 2 | section 2 | section 2 | `scoring_v2.dimensions[*]` | per row `state`, `basis`, `known_side`, `delta_msg` | X6, X5 | section 2.3 |
| 6 | What we know | three pills | `results.confidence.level.unconfirmed` on the price pill when a price is pending | same | `confidence_legs`, `confidence_details` | none | none | never hide the price pill (today RC:593 hides it on `pricePending`, RC:212) |
| 7 | Reviews | rating + count, then the review highlights | rating without highlights: `results.reviews.textUnavailable` | per perfume `results.noRating` (REUSED, en.json:160, ar.json:157) + `results.reviews.textUnavailable` | `reviews.products[i].*` | none | none (rating coverage is X8) | replaces "Reviews are still coming in." (`results.accordion.reviewsEmpty`, RA:458-461), which promises an arrival |
| 8 | Pros and cons | lists | an empty side: `results.honest.notKnownYet` | degraded: `results.prosCons.needsWriteUp` | `overview.products[i].{pros, cons}`, `comparison.error` | none | none | stop `hideProsCons` (RA:278-288) |
| 9 | Specs | fixed perfume rows | value on one side, "-" on the other | `results.honest.notListed` (exists, en.json:705, ar.json:702) | `specs.products[i].specs`, `specs.specs_comparison.rows`, `metadata.field_status` | none | none | fixed row list from the existing `results.spec.*` labels (CL ar.json:793-841) |
| 10 | Feedback | existing card | n/a | n/a | as today | none | none | none (CL3 owns it) |

Removed from the perfume page: the runner-up card (RC:504-510) and the "At a glance" row (RA:167). The partial and medical notes (RC:431-454) stay inside section 3 because they describe the result, not a missing field. The cohort badge is already removed in CL (RC:600-601); X9 stops the server sending `cohort_summary`, the only way to remove it from the store app.

Why `results.honest.notKnownYet` survives next to the reused `results.dimensions.limited_data` (PAGE_SKEPTIC.md section 3, "near-duplicate keys"): the bars reuse "Limited data" so the new page and today's apps say the same words on the same row; "Not known yet" is used only for one empty side of Pros and cons, where "Limited data" would be the wrong meaning.

Three bodies reach the Results screen, and the fixed page defines each:
- Text and camera: the full body from `build_comparison_response` (RB:1461).
- Link compare: HomeScreen posts `/api/v1/url/compare` and navigates with `response.data` (HomeScreen.tsx:618, :642). That body has root `products`, `comparison`, `winner_index`, `recommendation`, `key_differences`, `category_used`, `source_urls`, and NO `overview` or `scoring_v2` (url_extraction_service.py:1500-1509). X4 renders it through the same ten sections: names and photos from root `products`; explanation = `recommendation` when non-empty, else `results.verdict.noWriteUp`; no fact lines; key differences = `key_differences` text in the English UI only (the Arabic UI shows `results.keyDiff.none`); bars: a perfume pair shows the five rows as "Limited data", any other pair the section's honest line; the three pills say "Not confirmed". While AI calls fail this path answers LLM_UNAVAILABLE (url_extraction_service.py:1483-1493), so the screen shows its error state, not the page (Q15).
- Progressive stream events: the client defines `onScores`, `onVerdict`, `onFirstPaint`, `onSettleUpdate` (services/api.ts:654-660) and calls them (:961-968), but no screen or component passes them (grep of CL src, tests excluded, found only api.ts). The page renders only the final body and never flips from "not known" to "known" on screen.

### 2. The fixed perfume bars (X6 server, X4 client)

Under ENABLE_HONEST_FRAGRANCE_BARS, for a same-category fragrance pair, `build_dimensions_v2` (SS:3848-3933) emits exactly these five rows, in this order, every time. A non-fragrance pair is untouched (section 0).

| Order | key | Label (exists) | Honest source | known | partial | unknown |
|---|---|---|---|---|---|---|
| 1 | price | `results.dimension.price` | the two basis prices (`price.amount`; an off-size listing keeps `amount` null, B1) | both amounts real (both at the pair's basis by the reconcile) | one amount real, with or without an other-size listing on the other side | no real amount |
| 2 | reviews | `results.dimension.reviews` | real star ratings; a derived rating counts as missing (SS:3280-3288) | both real | one real | none real |
| 3 | longevity | `results.dimension.longevity` | specs `longevity` / `longevity_hours` as hours, only when not model knowledge (rule 5) | both give hours | one side | neither. NEVER the review score (today `spec_secondary` falls back to it, SS:2339-2350) |
| 4 | projection | `results.dimension.projection` | specs `sillage` mapped to intimate / moderate / strong / enormous, same rule 5 | both map | one maps | neither. NEVER the review score (today `projection_score` is the `review` signal, SS:2175-2177) |
| 5 | value | `results.dimension.value` | price and real rating (SS:3314-3420) | price row known AND reviews row known | never partial | otherwise (B3: whenever the price row is not known, value is unknown) |

Not emitted for perfumes under the flag: character (spec-count proxy), versatility (fact-check share proxy), presentation (rating-count proxy), wear_value (already skipped, SS:3896). This applies R-A8 (record/s80/PLAN_S80.md:29) and Q1.

#### 2.1 Wire shape of each row (every existing key keeps its type)

- known: as today, plus `state: "known"`, `basis` ("price" / "rating" / "specs"), `delta_msg` (X5). Longevity bar lengths come from the two hour values (a spec item at RED; never 0, DB:95-110); projection from the level (proposal 40 / 60 / 80 / 100). The per-row winner is `_dim_winner` (SS:3192-3238) on those scores.
- partial and unknown: `score_a = score_b = 75` (`_NEUTRAL_DISPLAY_SCORE`, SS:3168), `caption_key: "limited_data"`, `confidence: "low"`, `winner: null`, `delta_text` = "" for the new longevity / projection rows (today's English placeholder for price, reviews and value), plus `state`, `basis`, and for partial `known_side: 0 | 1` (int).
- With Q3 = yes (recommended): partial and unknown rows also carry `data_insufficient: true`. Both live bundles then draw their existing visible row: label plus `results.dimensions.limited_data` ("Limited data", en.json:208; "بيانات محدودة", ar.json:205), selected at DB:68 and drawn by InsufficientRow (DB:148-154, DB:224-233). DimensionBars.tsx is byte-identical in the two bundles (cmp in this run). With Q3 = no the rows stay invisible on today's apps (DB:82-88 drops `limited_data`). This reconciles IR:105 ("those rows show not known"): with Q3 = yes that proof passes on both live apps; with Q3 = no it passes only on the new page.
- Scores stay 75, not null: `score_a` / `score_b` are typed int (app/models/scoring_v2.py:24-28; the frozen contract, record/s80/contract_freeze.json:484), and the visible row needs no score (DB:68 selects on `data_insufficient` alone).
- On both live bundles the price and value rows are removed whenever any price is pending (RC:212, RC:555-562; ST RC:159, :490), so a pended pair shows Reviews, Longevity and Projection rows there. The outer gate (`dimensions.length >= 3` on the raw list, RC:527) always passes with five rows.

#### 2.2 Server rules under the flag

1. A default 50 never reaches a perfume bar: a one-side-missing row becomes "partial" (today it is emitted with 50 on the missing side, SS:3566-3589).
2. The fact lines never cite a row that is not "known": `_top_dim_candidate` (RB:920-950) and `_runner_up_dim_candidate` (RB:953-989) skip `caption_key == "limited_data"` and any `state` other than "known". Today neither checks the caption or the missing flags.
3. The crown (`winner_index`, `overview.winner.product_index`, `scoring_v2.overall_score`) is NOT moved by X6. It still contains defaults (PAGE_INVENTORY.md part c, consequence 5). That is Q5, its own unit.
4. The tradeoff sentence and the AI scoring summary follow the rows (section 2.4, P3 and P4).
5. Model knowledge: a spec value counts as known only when the specs carry a `_field_confidence` map AND the field is not marked model knowledge (`_tier3_fields`, result_gate.py:253-258 returns an EMPTY set when the map is missing, so today an unmarked value would pass as real). Under X6 a spec WITHOUT the map counts as NOT known. How many cached specs carry the map is UNVERIFIED and is measured at RED before the flip.
6. Under the flag the projection caption is `dim.projection.stronger` or `dim.comparable` only. The SS:3676 branch that prints the two raw sillage texts is not used for perfumes, so an Arabic page never carries English sillage words inside a caption.

#### 2.3 Client rule (X4)

Render the five rows by key in this order whatever the list holds; a missing row renders as unknown. known: two bars, and the per-row winner from `winner` only, never the score heuristic (DB:262-268) when `winner` is null. partial: label + `results.bars.knownForOne`, no bars. unknown: label + `results.dimensions.limited_data` (REUSED). The name legend always renders. A body without `state` (an old saved row, or the flag OFF) is read with today's filter (DB:82-88), so a stored row never shows a fake bar it did not have. A non-fragrance body renders today's list by the same filter, with the section's honest line when nothing survives.

#### 2.4 Every place a default or a proxy can still reach the user (B4)

| # | Path | How the default or proxy gets there today (measured) | v2 disposition |
|---|---|---|---|
| P1 | Score bars | proxy signals SS:2175-2179; default 50 SS:297; one-side-missing rows emitted SS:3566-3589 | under X6 (sections 2.1-2.2) |
| P2 | Fact lines (line1, line2) | `_top_dim_candidate` / `_runner_up_dim_candidate` read any row with numbers (RB:920-989) | under X6, rule 2 |
| P3 | Runner-up sentence `overview.winner.key_tradeoff` = "{loser} stays competitive on {dim}." (RB:238-244) | built from `compute_tradeoff_pairs(scoring_result["dimension_winners"], ...)` (SCS:3850, :4750, :5598); when the winner sweeps, F4.2 falls back to the loser's highest raw sub-score (SS:2763-2769), which can be a default 50 or a proxy. Both live bundles render it in the runner-up card when not degraded (RC:239-241; ST RC:187) | under X6: for a perfume pair `deterministic_verdict_fields` takes a tradeoff only from a dim whose X6 row is "known" (longevity_score maps to the longevity row, projection_score to projection; character, versatility, presentation and wear_value never qualify); otherwise `key_tradeoff` is "". Visible on today's apps: the runner-up card hides more often (RunnerUpWinsCard.tsx:100 hides with no tradeoff and no winning row). Question Q4 |
| P4 | The AI verdict prompt | `build_scores_summary` (SS:3017-3104) sends "stronger / weaker / comparable" per dim with `breakdown.get(dim, 50)` (SS:3068, :3071) and a "Dimension leaders" line, including the star-proxy longevity and projection; called at SCS:4653 and SCS:5504 | under X6: for a perfume pair the per-dimension and leaders lines list only dims whose row is "known". This is the R-A8 text "the verdict prompt's scoring context omits limited_data dims" (PLAN_S80.md:29). Flag ON changes the prompt bytes by design; flag OFF stays byte-identical (pinned). Visible only after the Claude switch (no AI text before it). Question Q4 |
| P5 | The crown (`winner_index`, TopMatchBadge, the "stronger overall" rank word in the same summary, the "edges ahead" fact line) | the overall score includes the default 50s (R3: Armani 50 vs Versace 48.3, IR section 1; R1: margin 1.4 from wear_value 75 against a default 50 because Layton's price was blanked, T1 section 5) | stated limit L-CROWN; question Q5; no unit in this lane owns it (v1's "result-gate lane" has no spec in the record copy: UNVERIFIED that it exists) |
| P6 | Home smart-pick caption `verdict_short` | copies `factual_verdict.line1` of a SAVED row when ENABLE_SMART_PICK_VERDICT_CAPTION is ON (HR:629-648); else the winner declaration; both bundles render it verbatim (HES:115, :230 in both trees) | new rows inherit the honest line1 of P2 with no Home change. Rows saved before the X6 flip keep their old line1 (for example "... leads on Versatility.") while they stay on Home: stated limit L-HOME, question Q12. The flag's production value is UNVERIFIED |
| P7 | History list caption `verdict_short` (NEW in v2: missed by v1 and by the skeptic) | HistoryScreen reads `item.verdict_short` and renders it (CL HistoryScreen.tsx:495, :615; ST :497, :617). Which route fills it for History was not traced in this run: UNVERIFIED | same as P6: stated limit L-HOME, question Q12 |
| P8 | Non-fragrance bars and lines | the same default-50 mechanics apply to every category (SS:297, SS:3566-3589) | X6 does not touch them: stated limit L-NF1, question Q14 |
| P9 | Ratings feeding the crown | `review_raw` takes `product["rating"]` with no derived check (SS:1814-1823); whether a derived rating already exists when scoring runs (RB:1614-1621 derives one later, from the scores) is UNVERIFIED | part of L-CROWN (Q5); X6 bars use `_dim_reviews`, which excludes a derived rating (SS:3285-3288) |

### 3. Price and bottle size (B1, B2, B3, owner ruling B7a; unit X1)

**The owner ruling (B7a).** Show each found price with its bottle size and a per-ml line; make no cheaper claim when the two sizes differ. The page follows it as below; it is no longer a question.

**The wire (B1).** For a side pended with `reason: "size_mismatch"`, `price.amount` stays null exactly as today (`make_pending_price`, PS:2005-2018, called by `_mark_size_pending`, PS:2402-2417). The other bottle's real Bahrain listing rides in the NEW additive object `price.offsize_listing` (X1B R-X1-7 table: `amount`, `currency`, `size_ml`, `retailer`, `url`, `title`, `source_method`, and `per_100ml` only under R-X1-7), written at the response-builder chokepoint after the verdict call (X1B R-X1-3, R-X1-4), so the AI prompt never sees it (X1S 2.1). Consequences measured in this run:
- No price comparison can use it: `_safe_price_amount` reads only `price.amount` (RB:842-852), so `_price_candidate` (RB:873-894), the line2 price fallback (RB:1114-1121), `_dim_price` (SS:3240-3262) and `_dim_value` stay on the "missing" path for that side. No cheaper sentence, no "BHD N less", no value ratio. The ruling's "no cheaper claim when the sizes differ" therefore holds in `_price_candidate`, `_format_line2`, `_dim_price` and `_dim_value` by construction, not only in the new bar state (PAGE_SKEPTIC.md D2).
- Both live bundles keep "No confirmed price yet." and keep hiding the price and value bars and the price pill (RC:212, RC:555-562, RC:593; ST RC:159, :490, :526). Neither reads `price.reason`, `price.size` or the new key (X1S row 26).

**Contract items this page needs from X1 (for the orchestrator to fold into the X1 brief; not owner questions).**
- E-X1-a, per-ml everywhere: the ruling says EACH found price carries its size and a per-ml line. X1B gives `size_ml` / `per_100ml` to the partner only beside an off-size listing (R-X1-7). The page needs the same two keys on EVERY shown Bahrain price whose own listing title passes X1B's strict one-size test E4, also when both sides are at the basis. Without it a basis-only pair shows its prices with no size and no per-ml line (stated, not wrong).
- E-X1-b, unit of the line: the ruling says "per ml"; X1B carries `per_100ml`. The page prints per ml (`results.price.perMl`), computed by the client as `per_100ml / 100` through the app digit policy, or from a `per_ml` key if X1 renames it. One field, one choice, settled in the X1 spec.
- E-X1-c, one price card: X1B's client draft keys (`results.price.offsize.withSize`, `.per100`, `.caption`) are replaced by this page's `results.price.withSize`, `results.price.perMl` and `results.price.differentSizes`, so the founder reads one set of Arabic lines (X1S G5).

**What a size may describe (B2).** A size describes the PRODUCT (the details line, the key-differences Size row) only when it comes from:
1. the name the user typed: `full_name` / `name`, read first by `_product_size_text_fields` (PS:2021-2045), one `\d+ml` token (`_SIZE_ML_RE`, PS:4073); or
2. a price accepted at the pair's basis whose OWN listing title states exactly that one size (X1B E4; never the 100 ml flagship default of `effective_pair_size_ml`, PS:2048-2097; never a name-derived basis; never a model-knowledge spec volume).

Never from a pended listing: `_mark_size_pending` keeps the REJECTED listing's `size` on the pending dict (PS:2412), which is why R3's "40ml" belongs to the US-converted listing that was not compared. An other-size listing's size appears ONLY beside that listing's own price, labelled as that bottle's size.

**What the new page shows (X4).**

| Case | Card price line | Per-ml line | Price bar | Value bar | Key-differences rows |
|---|---|---|---|---|---|
| A. both basis prices | amount, plus `results.price.withSize` when the listing title gives the size | under each price whose size is known (E-X1-a) | known; caption from `delta_msg` (`dim.price.less`) | known only if the reviews row is known (B3) | Price and Price per ml, the lower highlighted (same basis size, so the claim is fair) |
| B. one basis price, the other side carries `offsize_listing` | basis side as in A; other side the listing amount with `results.price.withSize` (the LISTING size), then `results.price.differentSizes` | under each price whose size is known | partial, caption `results.price.differentSizes`, no winner | unknown | Price and Price per ml, NO highlight |
| C. one basis price, the other side pending with no listing | basis side as in A; other side `results.price.pending` | basis side only | partial, `results.bars.knownForOne` | unknown | one side "-" |
| D. both sides carry `offsize_listing` | each listing with its own size and `results.price.differentSizes` | under each | unknown, caption `results.price.differentSizes` | unknown | Price and Price per ml, NO highlight, even if the two listing sizes happen to match (the scorer sees two null amounts; stated limit) |
| E. no price at all | `results.price.pending` on both | none | unknown | unknown | no price rows |

The confidence pill reads `results.confidence.level.unconfirmed` in cases B to E.

**Today's crown can come from the blank.** In R1 the crown went to Aventus partly because Layton's price was blanked (wear_value 75 against a default 50, margin 1.4; T1 section 5; X1S 2.6). Showing Layton's bottle on the new page does not move that crown, and the fact line "Creed Aventus EDP edges ahead on the overall picture." stays. That is part of Q5.

### 4. Server text as codes (X5): the contract (B6)

**Shape.** A Msg is `{"id": string, "args": object}`. `id` comes from the closed vocabulary below: ONE id per branch of every template, so no id carries a flag that switches its wording. `args` are typed and never hold an English sentence or a translated fragment.

| arg | type | meaning | client formatting |
|---|---|---|---|
| p | int, 0 or 1 | product index | the name the app already shows, bidi-isolated in right-to-left text |
| dim | string | a public dim key ("longevity", "build_quality", ...) | `t('results.dimension.<dim>')` |
| pct | int | a whole percent (rounded at RB:1086, RB:1120) | app digit policy (utils/formatNumber) |
| stars | number, 1 decimal | a star gap (RB:1091, SS:3298) | app digit policy |
| views | int | the RAW view count; today the server sends a humanized STRING (`views_human`, RB:1068) | a new client compact formatter with localized digits (a RED item for X4) |
| amount | number | a price difference (SS:3258) | joined with `currency` by the app's currency formatter into the `{{price}}` value; a formatted number is data, not a translated fragment |
| currency | string | ISO code, e.g. "BHD" | as above |
| hi, lo | int | hours (SS:3667) or dose amounts (SS:3705, :3709) | app digit policy |
| years | int | warranty years (SS:3645) | app digit policy |
| x | number, 1 decimal | a dose multiplier (SS:3708) | app digit policy |
| unit | string enum IU / mg / mcg / g | a dose unit (SS:3705) | printed as is (Latin abbreviation, stated exception) |
| channel | string | a YouTube channel name (proper noun) | as is, bidi-isolated |
| a, b | string | a spec value exactly as extracted (supplement form; sillage on flag-OFF bodies only, section 2.2 rule 6) | as is: the same stated limit as Q9; not translated, so nothing translated is nested |

**Where it travels.** All NEW, additive, only when ENABLE_RESULT_TEXT_CODES is ON. Every old English field stays byte-identical for the live bundles.

| New key | Type | Beside | Built at |
|---|---|---|---|
| `scoring_v2.factual_verdict.line1_msg` | Msg | `line1` | `_format_line1` RB:1073-1098, fallback RB:1175 |
| `scoring_v2.factual_verdict.line2_msg` | Msg | `line2` | `_format_line2` RB:1101-1131 |
| `scoring_v2.dimensions[i].delta_msg` | Msg | `delta_text` | `_dim_price`, `_dim_reviews`, `_dim_value` (SS:3240-3420), `_compose_delta_text` (SS:3592-3733) |
| `scoring_v2.personalization.applied_shifts[i].dim` and the same on `personalization.applied_shifts[i]` | string | `dim_display` | `_compute_applied_shifts` SS:686-716 (the key is dropped at SS:711 today) |
| `overview.winner.reason_msg` | Msg, only when `reason` IS one of the four reason templates | `reason` | RB:192, RB:193, RB:1414, RB:1415 |
| `overview.winner.key_tradeoff_msg` | Msg, only when `key_tradeoff` IS the template | `key_tradeoff` | RB:244 |
| Home pick `verdict_short_msg` | Msg, only when the caption came from `line1` | `verdict_short` | HR:629-648; rendering it is a Home client change OUTSIDE X4 (stated limit L-HOME-AR, Q12) |

The verdict-line ids (`fv1.*`, `fv2.*`) and the winner-reason ids (`wr.*`) are separate even where today's English is the same sentence (RB:1175 and RB:192), so a reason id can never be placed in a fact line or the reverse (PAGE_SKEPTIC.md D8).

**Vocabulary, part 1: fact lines, winner reason, tradeoff.** Client key = `results.msg.<id>`. `{{name}}` = the displayed name of product `p`; `{{dim}}` = `results.dimension.<dim>`. Every Arabic line is a DRAFT for the founder's native read.

| id | args | Branch (file:line) | English | Arabic draft |
|---|---|---|---|---|
| fv1.yt_attention_channel | p, views, channel | RB:1083-1084, channel present | {{name}} draws far more reviewer attention (~{{views}} YouTube views, led by {{channel}}). | {{name}} يحظى باهتمام أكبر بكثير من المراجعين (نحو {{views}} مشاهدة على يوتيوب، أبرزها لدى {{channel}}). |
| fv1.yt_attention | p, views | RB:1083-1084, no channel | {{name}} draws far more reviewer attention (~{{views}} YouTube views). | {{name}} يحظى باهتمام أكبر بكثير من المراجعين (نحو {{views}} مشاهدة على يوتيوب). |
| fv1.cheaper | p, pct | RB:1088 | {{name}} comes in {{pct}}% cheaper. | {{name}} أرخص بنسبة {{pct}}%. |
| fv1.premium | p, pct | RB:1089 | {{name}} carries a {{pct}}% price premium for the upgrade. | سعر {{name}} أعلى بنسبة {{pct}}% مقابل الترقية. |
| fv1.more_stars | p, stars | RB:1093 | {{name}} earns {{stars}} more stars from reviewers. | تقييم {{name}} أعلى بـ {{stars}} نجمة لدى المراجعين. |
| fv1.despite_lower_reviews | p | RB:1094 | {{name}} edges ahead despite slightly lower reviews. | {{name}} يتقدم قليلاً رغم تقييمات أقل بقليل. |
| fv1.leads_on | p, dim | RB:1096-1097, label present | {{name}} leads on {{dim}}. | {{name}} يتقدم في {{dim}}. |
| fv1.leads_on_strongest | p | RB:1096, empty label | {{name}} leads on its strongest dimension. | {{name}} يتقدم في أقوى جوانبه. |
| fv1.on_top | p | RB:1098 | {{name}} comes out on top. | {{name}} يتقدم في المحصلة. |
| fv1.edges_overall | p | RB:1175 | {{name}} edges ahead on the overall picture. | {{name}} يتقدم قليلاً في الصورة العامة. |
| fv2.ahead_on | p, dim | RB:1111-1112, label present | {{name}} pulls ahead on {{dim}}. | {{name}} يتقدم في {{dim}}. |
| fv2.ahead_on_strongest | p | RB:1111, empty label | {{name}} pulls ahead on its strongest area. | {{name}} يتقدم في أقوى جوانبه. |
| fv2.lighter_wallet | p, pct | RB:1121 | {{name}} stays {{pct}}% lighter on the wallet. | {{name}} أخف على الجيب بنسبة {{pct}}%. |
| fv2.rates_higher | p | RB:1129 | {{name}} rates a touch higher with shoppers. | تقييم {{name}} أعلى قليلاً لدى المتسوقين. |
| fv2.close_alternative | p | RB:1131 | {{name}} stays in the conversation as a close alternative. | {{name}} يبقى بديلاً قريباً. |
| wr.edges_overall | p | RB:192 | {{name}} edges ahead on the overall picture. | {{name}} يتقدم قليلاً في الصورة العامة. |
| wr.leads_overall | p | RB:193 | {{name}} leads on the overall picture. | {{name}} يتقدم في الصورة العامة. |
| wr.stronger_overall | p | RB:1414 | {{name}} is stronger overall. | {{name}} أقوى في المجمل. |
| wr.stronger_overall_noname | none | RB:1415 | Stronger overall. | أقوى في المجمل. |
| kt.competitive_on | p, dim | RB:244 (dim = the tradeoff key without `_score`) | {{name}} stays competitive on {{dim}}. | {{name}} يبقى منافساً في {{dim}}. |

Note on `wr.stronger_overall`: today's English is "... is the stronger overall pick." (RB:1414). The new app's English drops "pick", a word on the server's banned caption list (app/models/scoring_v2.py:9-14) and on FactualVerdict's list; the Arabic is the comparative "أقوى" (stronger), not v1's absolute "الأقوى". The old `reason` field keeps today's text for the live bundles.

**Vocabulary, part 2: bar captions (`delta_msg`), every category.**

| id | args | Branch (file:line) | English | Arabic draft |
|---|---|---|---|---|
| dim.no_caption | none | SS:3246, 3292, 3352, 3369 (placeholders); SS:3609, 3613 (empty); every X6 partial / unknown row | (no caption; the row shows its state line) | (none) |
| dim.price.less | amount, currency | SS:3258-3260 | {{price}} less | أقل بـ {{price}} |
| dim.price.different_sizes | none | X6 partial or unknown price row with an `offsize_listing` | renders `results.price.differentSizes` (section 6) | (same key) |
| dim.reviews.same | none | SS:3300 | Same rating | التقييم نفسه |
| dim.reviews.stars_higher | stars | SS:3302 | {{stars}} stars higher | أعلى بـ {{stars}} نجمة |
| dim.value.comparable | none | SS:3381 | Comparable value | قيمة متقاربة |
| dim.value.nearly_identical | none | SS:3386, not cross-tier | Nearly identical value | قيمة شبه متطابقة |
| dim.value.slightly_higher_a | none | SS:3393, not cross-tier | Slightly higher value here | قيمة أعلى قليلاً هنا |
| dim.value.slightly_higher_b | none | SS:3394, not cross-tier | Slightly higher value on the other side | قيمة أعلى قليلاً لدى الآخر |
| dim.value.noticeably_more_a | none | SS:3398, not cross-tier | Noticeably more per dinar here | قيمة أكبر بوضوح لكل دينار هنا |
| dim.value.noticeably_more_b | none | SS:3399, not cross-tier | Noticeably more per dinar on the other side | قيمة أكبر بوضوح لكل دينار لدى الآخر |
| dim.value.substantially_stronger_a | none | SS:3403, not cross-tier | Substantially stronger value ratio | قيمة أقوى بكثير هنا |
| dim.value.substantially_stronger_b | none | SS:3404, not cross-tier | Substantially stronger value on the other side | قيمة أقوى بكثير لدى الآخر |
| dim.value.cross_tier | none | a value row with `is_cross_tier` true and a caption other than "Comparable value" (the prefix, SS:3411-3412) | renders the EXISTING `results.value.different_tier` (en.json:261, ar.json:258) | (existing) |
| dim.comparable | none | SS:3615 | Comparable | متقارب |
| dim.points | dim | every point-math branch: SS:3617, 3635 (under 5%), 3638, 3649, 3651, 3653, 3710, 3712, 3714, 3716, 3721, 3723, 3732, 3733 | renders `results.dimension.<dim>` | (existing labels) |
| dim.longevity.hours | hi, lo | SS:3667 | {{hi}}h vs {{lo}}h | {{hi}} ساعة مقابل {{lo}} ساعة |
| dim.longevity.longer | none | SS:3668 | Longer-lasting | ثبات أطول |
| dim.projection.levels | a, b | SS:3676 (flag-OFF bodies only, section 2.2 rule 6) | {{a}} vs {{b}} projection | انتشار {{a}} مقابل {{b}} |
| dim.projection.stronger | none | SS:3677 | Stronger projection | انتشار أقوى |
| dim.character.distinctive | none | SS:3679 | More distinctive | طابع أكثر تميزاً |
| dim.versatility.more | none | SS:3681 | More versatile | استخدامات أكثر تنوعاً |
| dim.presentation.more_polished | none | SS:3683 | More polished presentation | تغليف أكثر أناقة |
| dim.wear_value.higher | none | SS:3685 | Higher everyday value | قيمة يومية أعلى |
| elec.battery_pct | pct | SS:3635 (5% or more) | +{{pct}}% battery life | عمر بطارية أطول بنسبة {{pct}}% |
| elec.warranty_longer | years | SS:3645 (the `side` word is "longer" in both branches, SS:3644) | {{years}}-year warranty, longer | ضمان أطول: {{years}} سنة |
| supp.dose_units | hi, lo, unit | SS:3705 | {{hi}} {{unit}} vs {{lo}} {{unit}} | {{hi}} {{unit}} مقابل {{lo}} {{unit}} |
| supp.dose_multiplier | x | SS:3708 | {{x}}x higher dose | جرعة أعلى بمقدار {{x}} مرة |
| supp.dose_plain | hi, lo | SS:3709 | {{hi}} vs {{lo}} per serving | {{hi}} مقابل {{lo}} لكل حصة |
| supp.form_vs | a, b | SS:3720 | {{a}} vs {{b}} | {{a}} مقابل {{b}} |

Why `dim.value.cross_tier` and `dim.points` add no string: both live bundles already replace those captions on screen. A cross-tier value row shows the client string `results.value.different_tier` instead of the server text (DB:276-292, `isCrossTier` and `heroDeltaText`); any caption with point math is replaced by the localized dim label (`safeDelta`, DB:287-288; _deltaText.ts). The ids reproduce today's screen in both languages, and v1's nested "Across tiers: {{text}}" key is gone.

Notes: `dim.longevity.hours` Arabic needs the counted-noun plural after 3 to 10 (i18next plural forms keyed on `hi`); `elec.warranty_longer` the same on `years`. The perfume-only ids `dim.character.*`, `dim.versatility.*`, `dim.presentation.*`, `dim.wear_value.*` are reachable only while X6 is OFF or for categories that share a dim key. "Better presented" and "Better everyday value" are reworded in the client English because "better" is on the server's banned caption list (app/models/scoring_v2.py:9-14); the old `delta_text` keeps today's text.

**Server rule.** Each builder returns its English text and its Msg from the same branch, so a branch cannot exist without an id; a test walks every branch listed above (DEFERRED TO RED: `python <SP>/harness/pyt.py --cwd <worktree> --tag inc-x5-red -- tests/test_inc_x5_*.py`).

**Client rules (X4).**
1. Msg present, id known, args valid: render `t('results.msg.<id>', args)` with `p` and `dim` resolved as above.
2. Arabic UI, Msg absent, id unknown or an arg invalid: show NO server English sentence. A fact line or reason is replaced by the section's honest line (3a); a bar row keeps its bars and loses only its caption. English UI: the old English field.
3. One client key per id; args are data; never join two translated strings.
4. A saved row from before the X5 flip (no `*_msg` keys), reopened from History in Arabic, falls under rule 2: its fact lines and bar captions are replaced by honest lines (cost stated in Q11).
5. Server text shown as data and allowed on the Arabic page: product names, the details line `overview.products[i].variant` (units and abbreviations such as "100ml - EDP", RB:553-610; PAGE_SKEPTIC.md section 3), spec values (Q9), channel names and dose units.

### 5. Key differences (X7)

#### 5.1 What it lists

Facts only, no AI, built inside `build_comparison_response` just before RB:2297 from `product_data`. Fixed order; a row appears only when at least one side is known and the two values differ.

| Order | `field` | Label key (exists unless marked) | Value per side (typed) | `highlight` | Source and rule |
|---|---|---|---|---|---|
| 1 | price | `results.price` | `{amount: number, currency: string, size_ml: int or null}` for a basis price; `{amount, currency, size_ml: int, other_size: true}` for an `offsize_listing`; or null | the lower side ONLY in case A of section 3 (both basis prices) | `price.amount` / `price.currency`; the X1 key; sizes per E-X1-a |
| 2 | price_per_ml | NEW `results.keyDiff.perMl` | number (BHD per ml) or null | the lower side ONLY in case A and only when both sizes are known | from the X1 per-ml figure (E-X1-a, E-X1-b) |
| 3 | size_ml | `results.spec.size` | int or null | none | B2 only (section 3); never `price.size` of a pended price (PS:2412), never the flagship default, never a model-knowledge volume |
| 4 | rating | `results.dimension.reviews` | `{rating: number, count: int}` or null; derived excluded | the higher, only when both are real and the gap is at least 0.1 | `rating`, `rating_count`; `rating_derived` excluded as in `_safe_rating` (RB:855-861) |
| 5 | concentration | `results.spec.concentration` | enum EDP / EDT / EDC / Parfum / Parfum Intense / Extrait / Eau Fraiche, or null | none | `extract_concentration` on the typed name (PS:4072-4084 patterns and function in this run), else a non-model-knowledge spec. Measured: no pattern matches "Profumo" (PS:4060-4069), so "Armani Acqua di Gio Profumo" reads null |
| 6 | longevity | `results.spec.longevity` | hours (int) or the extracted text | none | non-model-knowledge specs (section 2.2 rule 5); after the Claude switch in practice |
| 7 | sillage | `results.spec.sillage` | the level enum or the extracted text | none | same |
| 8 | scent_family | `results.spec.scent_family` | extracted text | none | same; free text (Q9) |

A non-fragrance pair gets rows 1, 2 and 4 only (section 0). Rows 1 to 5 are numbers or enums the app formats itself; rows 6 to 8 may hold free text as extracted (Q9).

**Wire.** `key_differences_v2`: list of `{"field": string, "values": [v0, v1], "highlight": 0 | 1 | null}` (NEW, additive). The frozen `key_differences` (string[]) is filled with plain English lines from the same rows ("Price: 133.460 BHD vs 85.000 BHD (125 ml bottle, different size)"). No bundle renders it (RS:437, ST RS:414). The share invitee view passes it through when reasons are on (referral_service.py:178); whether a web page outside this repo renders it is UNVERIFIED. The link path keeps its own body (url_extraction_service.py:1495-1509) and is outside X7.

#### 5.2 The incident rows as X7 would read them (code reading on the T1 values, not measured on a device)

| Row | Rows produced | Count |
|---|---|---|
| R1 Aventus vs Layton | Price: 133.460 BHD vs Layton's other-size listing 85.000 BHD (its listing size is not established: T1 says only that it was off the 100 ml target; the mock uses 125 ml, Layton's flagship per X1S 3, as an illustration). Price per ml: both, NO highlight. Size: Aventus 100 ml only if its accepted listing title states 100 ml (X1S 2.5 citing T1:117) vs "-". Concentration EDP on both: equal, left out. Ratings derived on both: no row. | 3 (once X1 is merged and ON; before it, Price and Size only) |
| R2 La Vie Est Belle vs Libre | Price: Lancome 34.000 BHD (title "... 100ml", T1) vs Libre's other-size listing 39.000 BHD (size LIKELY 90 ml, not established, T1). Price per ml, no highlight. Rating: 4.8 (6,600) vs 4.6 (85), highlight Lancome. Size: Lancome 100 ml. | 4 |
| R3 Acqua di Gio vs Eros | Price: "-" vs 25.000 BHD (Armani's only listing was a US-converted 40 ml price, refused by X1B E2, so nothing is shown; the Versace listing title says "for Women", X10's question). Price per ml: "-" vs 0.250 BHD. Concentration: "-" vs EDP. Size: "-" vs 100 ml (Versace's listing title states it). Never Armani's 40 ml. | 4 |

When no row qualifies the block shows `results.keyDiff.none`.

#### 5.3 The details line fill (ENABLE_DETAILS_LINE_FILL, its own flag)

When specs give no `volume_ml` / `concentration`, `_compose_variant_string` (RB:553-610) uses the concentration from the typed name and a size by B2 only. A model-knowledge spec `volume_ml` is not used under the flag. Visible on both live bundles (the variant line, RC:358; ST RC:304): Q10. Today's R1 would read "EDP - 100ml" under Aventus and "EDP" under Layton; R3 nothing new under Armani and "EDP - 100ml" under Versace. The Specs table's Size row keeps showing the spec value as extracted (Q9 class), labelled as a spec.

### 6. Every new user-visible string

Arabic drafts follow src/i18n/.copy-policy.json (read in this run: no phrase of `banned_ar`, none of `scary_vocab_ar` تعذر / فشل / تقدير / مُقدَّر; no English `banned_en` phrase) and the calm tone of existing lines (for example `results.price.pending`, CL ar.json:146). Every Arabic line is a DRAFT for the founder's native read before any OTA (the S81-11 owner step practice). This document writes the app's middle dot U+00B7 as " - " in English lines to stay ASCII; the Arabic cells keep the real character.

#### 6a. Page strings (client, X4)

| Key | English | Arabic draft | Note |
|---|---|---|---|
| results.honest.noPhoto | No photo found yet | لا توجد صورة بعد | new |
| results.honest.sizeUnknown | Size not listed yet | الحجم غير مذكور بعد | new |
| results.honest.notKnownYet | Not known yet | غير معروف بعد | new; only for an empty pros or cons side |
| results.price.withSize | {{price}} - {{size}} ml | {{price}} · {{size}} مل | new (B7a) |
| results.price.perMl | {{price}} per ml | {{price}} لكل مل | new (B7a; restored after v1, dropped in the stopped draft) |
| results.price.differentSizes | Different bottle sizes, so we do not compare the prices. | حجما العبوتين مختلفان، لذا لا نقارن السعرين. | new (B7a); English and Arabic now say one thing (PAGE_SKEPTIC.md section 4) |
| results.verdict.noWriteUp | The written explanation is unavailable this time. The facts below are what we could confirm. | الشرح المكتوب غير متاح هذه المرة. ما يلي هو ما استطعنا تأكيده. | new; replaces `results.degraded.note` on the new page |
| results.keyDiff.none | Not enough confirmed facts to list differences yet. | لا تتوفر حقائق مؤكدة كافية لعرض الفروقات بعد. | new |
| results.keyDiff.perMl | Price per ml | السعر لكل مل | new (B7a) |
| results.bars.knownForOne | Known for one perfume only | معروف لعطر واحد فقط | new |
| results.confidence.level.unconfirmed | Not confirmed | غير مؤكد | new |
| results.reviews.textUnavailable | Review highlights are unavailable this time. | خلاصة الآراء غير متاحة هذه المرة. | new in v2 (B7c: the review text needs AI) |
| results.prosCons.needsWriteUp | Pros and cons come from the written explanation, which is unavailable this time. | الإيجابيات والسلبيات تأتي من الشرح المكتوب، وهو غير متاح هذه المرة. | new |

REUSED (no new string): `results.dimensions.limited_data` (unknown bar, en.json:208 / ar.json:205), `results.noRating` (en.json:160 / ar.json:157; replaces v1's proposed `results.reviews.noRating`), `results.honest.notListed`, `results.price.pending`, `results.keyDifferences`, `results.price`, `results.value.different_tier`, and the `results.spec.*`, `results.dimension.*` and `results.confidence.*` families. Dropped from v1: `results.reviews.noRating` and `results.reviews.noneFound` (the per-perfume reused line plus the highlights line cover both), `results.msg.dim.value.cross_tier` (nested fragment), `results.msg.sillage.*` (section 2.2 rule 6).

Two wording notes for the native read. The existing eyebrow `results.whyWePicked` reads "Why this fits you" in English (en.json:770) but "لماذا اخترنا هذا" ("why we picked this") in Arabic (ar.json:767), the phrase the copy policy bans in English; flagged, not changed here. The existing `results.noRating` Arabic "لا يوجد تقييم متاح" says "no rating available" while the new lines say "yet"; acceptable, flagged for the same read.

#### 6b. Message strings

The full list with English and Arabic drafts is the vocabulary in section 4.

#### 6c. Count (measured from the tables above)

| Group | New Arabic strings |
|---|---|
| Page strings (6a) | 13 |
| Fact lines, winner reasons, tradeoff | 20 |
| Core bar captions (price, reviews, value) | 11 |
| Shared and perfume captions (`dim.comparable` and the eight perfume ids) | 9 |
| Non-fragrance captions | 6 |
| Total for the founder's native read | 59 |

Ids that add no string: `dim.no_caption`, `dim.price.different_sizes`, `dim.value.cross_tier`, `dim.points`. Total ids: 50.

### 7. What the two LIVE bundles show (store 683f56c0 and OTA f1e20c39)

| State | Store 683f56c0 | OTA f1e20c39 (= CL) |
|---|---|---|
| All new flags OFF (default after merge) | unchanged; each unit pins flag-OFF byte identity | unchanged |
| X5 ON | unchanged: only new keys; every English field the same text; DimensionBars, FactualVerdict and PersonalizationChip read only the old fields | unchanged |
| X7 list ON | unchanged: `key_differences` is never rendered (ST RS:414); `key_differences_v2` is unknown to it | unchanged (RS:437) |
| X7 details-line fill ON | CHANGES: an "EDP - 100ml" style line where specs were empty (ST RC:304) | same change (RC:358) |
| X6 ON, Q3 = yes | CHANGES: proxy bars and the default win become "Limited data" rows (R2: the Reviews bar plus Longevity and Projection "Limited data" rows instead of 4 bars; R3: Reviews, Longevity, Projection "Limited data" rows instead of one "More versatile" bar); line1 / line2 stop citing a row that is not known (R3 would read "... edges ahead on the overall picture." instead of "... leads on Versatility."); the runner-up card hides more often (P3); the AI prompt hears only known rows (P4, after the Claude switch); new Home and History captions inherit the honest line1 (P6, P7) | same change |
| X6 ON, Q3 = no | as above, but the unknown rows are invisible (R2 1 bar, R3 0 bars) | same |
| X1 ON (other unit) | unchanged: `amount` null, the new key ignored | unchanged |
| R-A10 unit ON (later, Q13) | CHANGES: the template lines arrive in Arabic for Arabic requests | same |
| X9 ON (other unit, ruled) | the shoppers line disappears | nothing to remove (already gone) |
| Any flag ON, the share invitee view | `key_differences` text can reach a shared view (referral_service.py:178); whether a web page renders it is UNVERIFIED | same |

### 8. Slicing plan

"AI text" below means the written explanation, pros and cons, review highlights or AI-extracted specs. Under the owner ruling B7c none exists in production until the first Claude text role is live; every check that needs it is marked **after the Claude switch**.

| Slice | Unit | Kind | Visible on today's apps when ON? | Depends on | Checks that need AI text | Why this place |
|---|---|---|---|---|---|---|
| 1 | X6 HONEST BARS (ENABLE_HONEST_FRAGRANCE_BARS) | backend, dark | YES (section 7) | Q1-Q4; the flip pause (Q16) | the prompt-summary part (P4) and a real longevity / projection bar: **after the Claude switch**. The main proof (fake bars gone, verdict line honest) needs none and works best now, with specs empty | the only change the founder sees without a new app; footprint SS `build_dimensions_v2` + `build_scores_summary`, RB candidates + `deterministic_verdict_fields` |
| 2 | X5 TEXT CODES (ENABLE_RESULT_TEXT_CODES) | backend, dark | no | the X6 state field (`dim.no_caption`); Q13 | none: the codes cover server templates, which exist without AI | the new page cannot render Arabic without it; ship before X4 so X4 builds against real bodies |
| 3 | X7 DIFFERENCES (ENABLE_DIFFERENCES_LIST) + DETAILS LINE (ENABLE_DETAILS_LINE_FILL) | backend, dark | the details line only (Q10) | X1 merged for the other-size price cell and the per-ml row (without it those cells show "-"); E-X1-a | longevity, sillage and scent-family rows: **after the Claude switch**; price, per-ml, size, rating and concentration rows need none | X7 and X5 both edit RB near RB:1073-1181 and RB:2297: run them one after the other |
| 4 | X4 FIXED PAGE | client, merged to main, shipped by a later OTA | n/a | design approval, the native read of the 59 strings, X5 / X6 / X7 merged (dark is enough to build), X1 merged for the price card, Friday's SECOND OTA out first (IR:103), ENABLE_FEEDBACK_V2 ON before any OTA from a main that carries CL3 (risk K1) | the "known" states of the explanation, pros and cons, review highlights and specs: **after the Claude switch**. The honest states can be proven before it | built against fixtures while 1-3 are in review; the OTA goes out only after the flags it reads are ON and canaried |
| later | CROWN unit (Q5) | backend, dark | YES | owner ruling | none | changes frozen winner keys read by History, Home, Profile |
| later | R-A10 by-value Arabic (Q13) | backend, dark, existing flag ENABLE_ARABIC_VERDICT_OUTPUT | YES | X5's id set (one source for both) | none for the template lines | the only route that removes English from today's apps |

Flip order (one flag per canary window, set by the relay on the founder's yes; all paused while AI calls fail, H2, Q16): X6, X5, X7 list, details line, then the X4 OTA. Each window repeats its proof below.

### 9. PROOF ON THE PHONE per slice (H6: nothing is called fixed until the phone shows it)

Golden set (IR section 4): 1 Aventus vs Layton, 2 La Vie Est Belle vs YSL Libre, 3 Acqua di Gio Profumo vs Eros EDP, 4 Sauvage EDP vs Bleu de Chanel EDP, 5 Baccarat Rouge 540 vs Khamrah. Pairs 1-3 are no longer never-compared, so each first proof includes pair 4 or 5. The free tier allows 3 comparisons a day (IR:83, N6). Each claim records the row id, the UTC time, the bundle of the screenshot (store app or updated app) and `cache_hit: false` on the row (a cached body can predate the flip, X1S 2.7). A partial body (`metadata.partial: true`) is never evidence (X1S 2.3). A hermetic test run is necessary and is never the production proof.

| Slice | Pairs | Must be visible on the phone | Positive control in the same screenshot | Backing row / log check | Needs AI text? |
|---|---|---|---|---|---|
| X6 | 2 and 3, plus 4 | store app AND updated app. Pair 2 with specs still empty: no "Longer-lasting", no "Stronger projection", no "Better presented" bar; with Q3 = yes, Longevity and Projection rows read "بيانات محدودة". Pair 3: no "More versatile" bar, and the fact line does not say "leads on Versatility" | pair 2's Reviews bar with both real ratings (4.8 and 4.6) visible | `scoring_v2.dimensions` holds exactly price, reviews, longevity, projection, value in that order; longevity / projection `state` "unknown", `caption_key` "limited_data" (and `data_insufficient: true` with Q3 = yes); character / versatility / presentation ABSENT from the list; `factual_verdict.line1` names no row that is not known; `overview.winner.key_tradeoff` names no dim that is not known. The crown check ("`winner_index` equals a flag-OFF run") is a HERMETIC before / after on the saved row inputs, stated in words as not the production proof (H6 c) | no: best run BEFORE the Claude switch, while specs are empty |
| X6, second check | 4 | a longevity or projection bar with "Nh vs Nh" or "Stronger projection" once real specs arrive is CORRECT, not a regression | the spec row in Specs shows the same value | the row's spec carries a `_field_confidence` map without a model-knowledge mark | **after the Claude switch** |
| X5 | 1, 2, 3 | nothing new on today's apps (expected; the report says so) | none possible | each row carries `line1_msg` / `line2_msg`, a `delta_msg` on every dim, `applied_shifts[*].dim`; every `id` is in section 4; the English fields equal a flag-OFF body (hermetic) | no |
| X7 | 1, 2, 3, plus 5 | nothing on today's apps from the list; its phone proof exists only with X4 (stated) | n/a | `key_differences` non-empty; `key_differences_v2` rows match section 5.2 (R3: no 40 ml anywhere); the completeness score's key-differences point turns 1 (IR section 4) | price, size, rating, concentration rows: no; spec rows: **after the Claude switch** |
| Details line | 1 and 3 | store app AND updated app: "EDP" under Layton and Versace; no size under Armani | Aventus's line shows a size only if its accepted listing states it | the variant strings in the row; no size taken from a pended price | no |
| X4, honest states | all five, Arabic UI, on the UPDATED app (N3 check: the Home headline "قارن بين عطرين.") | the same ten sections in the same order on all five; every empty field shows its Arabic honest line; no English sentence except the items of section 4 client rule 5 | for EVERY pair whose row carries `factual_verdict.line1_msg`, the Arabic fact line is VISIBLE (not only the honest line); print the ids found in the row next to the screenshot | the completeness score next to each screenshot; the rows carry the X5 / X6 / X7 keys | no |
| X4, known states | same pairs | the explanation paragraph, Pros and Cons lists, review highlights and spec rows appear in the same places the honest lines held | the honest lines are gone where the data exists | rows without `comparison.error`, non-empty `pros` / `cons` | **after the Claude switch** |
| X1 price card (X1's own proof restated) | 1 | updated app: Layton shows its BHD price with the listing's size, a per-ml line and the different-size line; store app keeps "No confirmed price yet." | Aventus keeps 133.460 BHD with its size and per-ml line | `products[1].price.amount` null AND `offsize_listing.amount` 85.0 with `size_ml` stored; the listing title contains the shown ml token. IR:100's text "price.amount not null" must be restated by the orchestrator under B1 (X1S 2.7) | no |

### 10. Open questions for the owner (merged and renumbered; the owner brief and the mock use the same numbers)

Ruled on 2026-11-11 and removed from this list: N5 / N5b (show each found price with its size and a per-ml line, no cheaper claim across sizes: B7a), the cohort line (removed: B7b), the bridge credential ("wait for Claude": B7c).

| # | Question | Recommended | Why |
|---|---|---|---|
| Q1 | Drop the character, versatility and presentation bars for perfumes? | Yes | each is a proxy with no honest source (spec count, fact-check share, rating count); R-A8 already rules no proxy bar without evidence |
| Q2 | Show the same five perfume bars every time: Price, Reviews, Longevity, Projection, Value? | Yes | each has a real source when data exists; a fixed list makes the page the same every time |
| Q3 | When honest bars go on, should today's apps show a "Limited data" row for an unknown bar instead of hiding it? | Yes | both live apps can already draw that row (DB:68, DB:148-154); it matches IR:105's proof; hiding makes today's results look emptier |
| Q4 | Should the runner-up sentence and the AI's scoring notes also stop using guessed values (today's apps then show the runner-up card less often)? | Yes | they read the same defaults and proxies (P3, P4); R-A8 already rules the prompt part |
| Q5 | Should a winner still be named when the scores rest on missing data (result 3: every Armani score was the default; result 1: Layton's price was blanked)? | No; build it as its own unit after the honest bars | a default must not win anything visible; it changes frozen winner keys on today's apps, so it needs its own unit and window |
| Q6 | Remove the "where the runner-up wins" card from the new perfume page? | Yes | it can only appear when it has content; its facts now live in the bars and key differences |
| Q7 | Remove the "At a glance" row? | Yes | it never appears on a real result today (PAGE_INVENTORY.md row 9a) |
| Q8 | Use "The written explanation is unavailable this time. The facts below are what we could confirm." when the explanation is missing? | Yes | the old note says the prices below are real directly above a missing price (T4 G3) |
| Q9 | Keep perfume details (notes, scent family, season) as the stores wrote them, possibly in English, in the first version? | Yes, as a stated limit | translating free text is an AI job of its own; the labels are Arabic |
| Q10 | Show "EDP - 100 ml" under the names on today's apps, using only the typed name or a price accepted for that size? | Yes | a fact we hold; it fills an empty line on both live apps; it never uses a rejected listing's size (B2) |
| Q11 | On the new Arabic page, hide a server sentence that has no code (including results saved before the change and reopened from History) instead of showing English? | Yes | English on the Arabic page is the defect; the cost is that old results reopened in Arabic show honest lines instead of their English fact lines |
| Q12 | Accept that Home and History captions saved before the honest-bars switch keep their old sentence? | Yes, as a stated limit | rewriting saved rows is a migration of user history; new rows get the honest sentence automatically (P6, P7) |
| Q13 | Build your earlier ruling (the server writes the template lines in Arabic when the app asks in Arabic) as its own unit after the codes? | Yes | it keeps R-A10 (PLAN_S80.md:31) and is the ONLY route that removes English from today's two apps and the Home caption; the codes serve the new app; the camera path gets it once that path sends a language, as R-A10 already plans |
| Q14 | Until the perfume-only switch is on, keep non-perfume results on the new page with today's bars? | Yes, as a stated limit | the honest-bar rules are perfume rules; rewriting nine categories is out of these units; the perfume-only switch removes the case |
| Q15 | Show link comparisons (two store links) on the same fixed page, with honest lines where data is missing? | Yes | one page for every result; the link body has no bars or fact lines, so those sections show their honest lines |
| Q16 | Keep the honest-bars switch paused until the Claude switch works, like every other switch? | Yes | the record pauses every switch while AI calls fail (one change per window keeps each proof readable); after the Claude switch the fake-bar check still runs on any pair whose details stay empty |

### 11. Assumptions (each with why it beats the alternative)

1. **Codes, not finished Arabic sentences, in the new keys.** The app owns every Arabic string and the copy-policy fence; server-side Arabic needs a second pipeline. By-value Arabic for the live apps stays R-A10 (Q13), built from the same id set so the two never drift.
2. **Product index, not name, in `args`.** One source for the name, isolated for right-to-left text.
3. **Unknown and partial bars reuse the `limited_data` placeholder shape (75 / 75), plus `data_insufficient` with Q3 = yes.** Both live bundles already handle both markers (DB:68, DB:82-88); a null score or a new shape risks the zero-score node (DB:95-110) and retypes a frozen field.
4. **X6 does not move the crown.** Moving it touches frozen keys read by History, Home and Profile; Q5 makes it its own unit.
5. **`key_differences` (frozen string[]) is filled with English and the structured list rides in a new key.** No bundle renders the old key; retyping is forbidden (H1).
6. **The other-size price follows X1's wire (B1).** This page never reads `price.size` of a pended price.
7. **A spec without the model-knowledge marker counts as NOT known** (section 2.2 rule 5): a wrong "known" is worse than one more "Limited data" row.
8. **The per-ml line is printed per ml, as ruled.** Bahrain prices carry three decimals, so "1.335 BHD per ml" stays readable; a per-100-ml print would be a wording change the founder did not rule (E-X1-b).
9. **Line numbers were measured on the exports at a74caba7 and 683f56c0 in this run.** Row values for R1-R3 come from the verified extract T1 and from X1_MEASURE.md / X1S; this round read no database.

### 12. Stated limits (each has its own question)

| Id | Limit | Question |
|---|---|---|
| L-CROWN | the crown and the "edges ahead" fact line can still rest on defaults on every bundle | Q5 |
| L-HOME | Home and History captions saved before the X6 flip keep their old sentence | Q12 |
| L-HOME-AR | the Home and History captions stay English on both live apps and on the new app until a Home client change or R-A10 | Q12, Q13 |
| L-NF1 | non-fragrance bars keep today's default-50 mechanics | Q14 |
| L-SPEC | spec values are shown as the stores wrote them | Q9 |
| L-OLD-AR | old saved results reopened in Arabic lose their English fact lines | Q11 |
| L-PARTIAL | a partial (time-capped) body can still carry two shelf prices of different sizes, un-reconciled (X1S 2.3; X1B R-X1-22) | none new: a pre-existing path; the X1 spec owns it |

### 13. Disposition of every PAGE_SKEPTIC.md finding

Nothing was rejected outright. Two items were applied in a different form than the skeptic proposed; the reason is given.

| Skeptic item | Disposition in v2 | Re-measured in this run |
|---|---|---|
| s1: channel clause optional; `views` is a string | two ids (`fv1.yt_attention_channel`, `fv1.yt_attention`); `views` becomes a raw int with a client formatter | RB:1066-1068, RB:1083-1084 |
| s1: RB:193 omitted from the inventory | `wr.leads_overall` | RB:192-193 |
| s1: governorate line 394 vs 395 | moot: the cohort line is removed (B7b) | n/a |
| D1 rejected-listing size shown as the product's | B2 rule; the pended `size` is never used for the product (sections 3, 5.1 row 3, 5.3) | PS:2402-2417 |
| D2 X1 wire would show another bottle's price on the live apps | B1 wire; no-claim proof by construction in all four price readers (section 3) | RB:842-852, RB:873-894, RB:1114-1121, SS:3240-3262 |
| D3 value compares different bottles | B3: value known only when price and reviews rows are known | SS:3314-3420 |
| D4 tradeoff, prompt summary and crown | P3 and P4 under X6 (Q4); the crown is L-CROWN with Q5 | RB:238-244, SS:2763-2769, SS:3017-3104, SCS:4653, :5504 |
| D5 not fragrance-only | section 0; non-fragrance ids in section 4 | SS:3880-3881, SS:3605-3733 |
| D6 the visible "Limited data" row was missed | Q3 = show it via `data_insufficient`; IR:105 reconciled (section 2.1) | DB:64-88, DB:145-154, DB:224-233; cmp of DB in both bundles |
| D7 Q9 re-asked a ruled question | Q13 now says it KEEPS R-A10 and that only R-A10 removes English from the live apps; camera limit stated as R-A10's own plan, not permanent | record/s80/PLAN_S80.md:31 (as cited by the skeptic; not re-read) |
| D8 nested fragments and missing branches | `dim.value.cross_tier` and `dim.points` reuse client strings; levels caption restricted (rule 6); one id per branch; `dim.price.less` documents `{{price}}` | SS:3376-3412, DB:276-292 |
| D9 questions hiding defaults | N5 / N5b ruled (B7a); Q5 crown with the R1 blank named; Q3 carries the visible / invisible choice; Q11 states the History cost | T1 section 5 |
| s3 Home smart-pick caption | P6, L-HOME, `verdict_short_msg`; FOUND in this run: the History list renders the same field (P7) | HR:626-648, HES:115, :230, HistoryScreen.tsx:495, :615 (ST :497, :617) |
| s3 link compare body | defined in section 1; Q15 | HomeScreen.tsx:618, :642; url_extraction_service.py:1483-1509 |
| s3 SSE progressive payload | no screen passes the stream callbacks; the page renders the final body only | services/api.ts:654-660, :961-968 |
| s3 `variant` server text | section 4 client rule 5 lists it as allowed data | RB:553-610 |
| s3 near-duplicate keys | `results.noRating` and `results.dimensions.limited_data` reused. APPLIED DIFFERENTLY: `results.honest.notKnownYet` is kept for one empty pros or cons side, because "Limited data" means something else there | ar.json:157, :205 |
| s4 "الأقوى" and "pick" | comparative "أقوى"; English drops "pick" | app/models/scoring_v2.py:9-14 |
| s4 differentSizes said two things | one meaning in both languages | n/a |
| s5 X6 proof only absences | positive control and "ABSENT from the list" added | n/a |
| s5 crown check on production | hermetic, stated as not the production proof | n/a |
| s5 X4 proof passes when X5 is broken | the Arabic fact line must be visible on every row that carries `line1_msg` | n/a |
| s5 X7 proof | its phone proof exists only with X4 (stated) | n/a |
| s7 unverified: flag values | still UNVERIFIED (section 15) | n/a |
| s7 unverified: does a non-pended price carry `price.size` | APPLIED DIFFERENTLY: v2 does not depend on it; the product size comes only from the typed name or the accepted listing's own title (E-X1-a) | PS:2021-2045 |
| s7 unverified: `review_raw` excludes derived | it does not check the flag at scoring time (SS:1814-1823); whether a derived rating exists then is UNVERIFIED (P9) | SS:1814-1823 |
| s7 unverified: result-gate lane | still UNVERIFIED; Q5 makes the crown its own unit regardless | n/a |
| s7 unverified: unmarked specs | a spec without `_field_confidence` counts as NOT known under X6 | result_gate.py:253-258 |

### 14. Change log against v1 (PAGE_DESIGN_PROPOSAL.md)

| # | Area | v1 | v2 |
|---|---|---|---|
| 1 | Opening | the outage was "while the OpenAI key is broken" | Part 1 opens with what the page shows in the coming days with no AI text (B7c), section by section, today's apps beside the new page |
| 2 | Price | N5 / N5b open; X1 wire shape unnamed; size from `price.size` | ruled (B7a); B1 wire `price.offsize_listing`, `amount` stays null; five-case table; per-ml line on every price whose size is known; contract items E-X1-a/b/c for X1 |
| 3 | Size | `price.size` could fill the product size and the details line | B2: typed name or an accepted listing's own title only; never a pended listing's size |
| 4 | Value bar | "known when all inputs real" | B3: known only when price and reviews rows are known |
| 5 | Bars on today's apps | unknown rows invisible only | Q3 offers the existing visible "Limited data" row via `data_insufficient`; IR:105 reconciled |
| 6 | Defaults and proxies | X6 covered bars and two fact-line candidates | also the tradeoff sentence and the AI scoring summary (Q4); crown, Home, History and non-fragrance listed as limits with questions (section 12) |
| 7 | Non-fragrance | "the live product is fragrance-only" | false today (B5); section 0 states every rule for other categories; their captions get ids |
| 8 | X5 contract | 33 ids, a nested "Across tiers: {{text}}" key, a two-way sillage caption, a mandatory channel arg, `views` as a string, shared ids for fact line and reason | 50 ids, one per branch, no nested fragment, typed args, separate `fv1` / `fv2` / `wr` ids, two-sided value ids |
| 9 | Strings | 54 new Arabic strings; `results.reviews.noRating`; "الأقوى"; differentSizes said two things | 59 new strings (13 page + 46 message); `results.noRating` and `results.dimensions.limited_data` reused; review-highlights line added; comparative Arabic; one meaning per string |
| 10 | Key differences | 6 rows incl. a per-ml row with an N5b-dependent highlight | 8 rows; per-ml restored by the ruling, highlighted only for two basis prices; concentration for "Profumo" measured as null |
| 11 | Details line | part of the X7 flag | its own flag ENABLE_DETAILS_LINE_FILL and question Q10 |
| 12 | Bodies | text body only | link body and stream events defined (section 1) |
| 13 | Slicing and proofs | no AI distinction; proofs by absence only | every AI-dependent check marked "after the Claude switch"; positive controls; hermetic crown check; cache and partial-body rules |
| 14 | Questions | Q1-Q11 + N5 + N5b, some re-asking a ruling | Q1-Q16, merged and renumbered; N5 / N5b and the cohort line removed as ruled; Q13 keeps R-A10 in words |
| 15 | Shoppers line | "already gone in the update" | ruled removed (B7b); X9 removes it from the store app |

### 15. Not verified in this round, and the deferred runs

- The production values of ENABLE_SMART_PICK_VERDICT_CAPTION, ENABLE_URL_MODE_V2 and ENABLE_FRAGRANCE_ONLY_GATE (the last is OFF by H2's general statement, not by a dated read made here).
- Which route fills `verdict_short` for the History list (P7).
- Whether a web share page outside this repo renders `key_differences`.
- The size in the Layton and Libre listing titles (the mock's 125 ml for Layton is an illustration; X1S section 5).
- How many cached specs carry `_field_confidence` (section 2.2 rule 5).
- Whether a derived rating exists when scoring runs (P9).
- Whether a "result-gate lane" spec exists (P5).
- Whether X1 adopts E-X1-a, E-X1-b and E-X1-c (the X1 brief draft in this folder predates the owner rulings and does not yet carry them).
- Which reaches the founder's phone first, the new page or the Claude switch.
- Every jest, tsc and pytest check is DEFERRED TO RED: X5 / X6 / X7 `python <SP>/harness/pyt.py --cwd <worktree> --tag inc-<unit>-red -- tests/test_inc_<unit>_*.py`; X4 the full jest suite in its worktree after the H5(b) probe, then `npx tsc --noEmit`.
