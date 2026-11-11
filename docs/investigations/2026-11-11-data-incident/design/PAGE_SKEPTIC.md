# PAGE SKEPTIC: review of PAGE_INVENTORY.md and PAGE_DESIGN_PROPOSAL.md

Written 2026-11-11 by the skeptic of the S92-FIX incident lane. READ-ONLY round: no test, no build, no network, no production probe, no git write. Every file:line below was re-read in this run on the plain exports (src/a74caba7 for app/ and the OTA client, src/683f56c0 for the store client). Short names as in the inventory (RB, SS, SCS, RC, RA, DB, RS, ST). Nothing here says a production problem is fixed.

## Verdict

SOUND_WITH_CORRECTIONS. The inventory's citations hold: every RB, SS, RC, RA and DB line I re-read says what the inventory says (spot list in section 1). The design has the right skeleton, but it has five defects that change what a user would see, and it is missing four consumers or render paths. Fix them before the owner reads the questions.

## 1. Citations re-read (all CONFIRMED unless noted)

| Claim | Re-read | Result |
|---|---|---|
| 12 factual-verdict templates | RB:1084, 1088, 1089, 1093, 1094, 1097, 1098, 1112, 1121, 1129, 1131, 1175; return shape RB:1181 | confirmed. Note RB:1083: the channel clause is OPTIONAL (`cite` is "" when no channel), and `views` is a humanized STRING (RB:1068 `views_human`), not an int |
| winner-reason templates | RB:192-193 (tuple of two), RB:1414 | confirmed; the inventory table (b) omits RB:193 "leads on the overall picture." (the proposal has it) |
| tradeoff template | RB:244 | confirmed |
| bar captions | SS:3246, 3248, 3260, 3292, 3300, 3302, 3352, 3369, 3381, 3386, 3393, 3398, 3403, 3411, 3615, 3617, 3667, 3668, 3676, 3677, 3679, 3681, 3683, 3685 | confirmed |
| placeholder score 75 | SS:3168 `_NEUTRAL_DISPLAY_SCORE = 75` | confirmed |
| MISSING_SCORE 50, normalizers | SS:297, SS:2546-2558, SS:2339-2353 | confirmed |
| one-side-missing dims emitted | SS:3570-3589 (`was_missing_a/b` set, popped before the wire at SS:3931) | confirmed |
| `_dim_winner` None on a missing side | SS:3226-3227 | confirmed |
| client score fallback when `winner` null | DB:262-268 (the `aWins` ternary) | confirmed |
| DB inner filter | DB:82-88 | confirmed |
| verdict candidates skip only price/reviews/value | RB:932-933; `_runner_up_dim_candidate` RB:953-989 skips nothing by key | confirmed |
| key_differences always [] | RB:2297, SCS:5647 | confirmed |
| category_profile only on root products | RB:2258, RB:2268; overview.products built RB:1944-1995 without it; RS:431-433 | confirmed (code reading) |
| price pill hidden on pending | RC:593 | confirmed |
| outer bar gate | RC:527 | confirmed |
| R-A8, R-A10, B8, C2 | record/s80/PLAN_S80.md:29, :31, :64, :75 | confirmed text; see D7 on how the proposal treats R-A10 |
| URL body and B4 fill | url_extraction_service.py:1483-1509, `_v2_verdict_fill` from :1534 | confirmed |
| share invitee drop | referral_service.py:178 (`_REASONS_KEYS`) | confirmed |
| governorate Arabic names | CL ar.json:395-399 (the proposal says 394-399; 394 is the heading key) | trivial |

No citation was found to be wrong in a way that changes a conclusion.

## 2. Defects in the design (each with the code that refutes it)

### D1. The "size" the design shows is the size of the REJECTED listing, not of the perfume compared (wrong product)

`_mark_size_pending` (price_service.py:2402-2418) pends a price with reason size_mismatch and keeps `size=price.get("size")`, the size of the listing that was rejected because it did not match the pair's target size (the target rule, price_service.py:2270-2290: "flagship-100ml target"). So on R3 the "40ml" on Armani is the size of the bottle we did NOT compare.
- Proposal section 5 row 2 (`size_ml` from `price.size`) and its R3 reading "Size 40 ml vs -" would list 40 ml as Armani's size in key differences, under N5 = blank as well.
- Proposal section 5 "Variant back-fill" and Q7 would put "40ml" under the Armani name on BOTH live bundles (variant line, RC:358, ST RC:304), with no update and no way to undo it on those bundles.
- Correction: a size may describe the product only when it comes from the user's typed name (`_product_size_text_fields` reads `full_name` / `name` first, price_service.py:2021-2040) or from a price that was ACCEPTED at the pair's basis. The size of a pended listing may appear only beside that listing's price (N5 = show), labelled as the listing's size. Q7 must say this in words.

### D2. "Nothing changes for the live bundles" is false for N5 = show: unit X1 puts the other bottle's amount in `price.amount`

The incident report's X1 backing check is "products[1].price.amount not null, size_ml stored" (INCIDENT_AND_DATA_PLAN_2026-11-11.md:100). Both live bundles print `price.amount` with NO size: CL `formatPrice` RC:188-206 never reads `size`; ST formatPrice ST RC:135-142 the same. They then also feed it to every price comparison:
- `_price_candidate` (RB:873-894) has no size check: line1 "X comes in N% cheaper." (RB:1088) and line2 "lighter on the wallet" (RB:1121) compare a 125 ml price with a 100 ml price;
- `_dim_price` (SS:3240-3269) writes "BHD N less" and the value dim (SS:3314-3420) "more per dinar";
- both bundles' pending filter (RC:212, ST RC:159) no longer fires, so those bars show.
The proposal's section 3 and section 7 do not name the wire shape X1 uses or this effect. Correction: before N5 is asked, state the wire shape (either `price.amount` stays null and the found amount rides in a NEW key, or the amount is filled and the live bundles show a different bottle's price with no size), and state that under N5b (a) the "no cheaper claim" rule must hold in `_price_candidate`, `_format_line2`, `_dim_price` and `_dim_value`, not only in the new bar state.

### D3. The value row still compares prices of different bottles

Section 2 marks value "known" when "all inputs real", and its partial column is "n/a". Under N5 = show and N5b (a), both amounts are real but the sizes differ, so value would be "known" and its caption ("Noticeably more per dinar here", SS:3398) makes the cheaper claim that section 3 forbids. Correction: value is "unknown" (or "partial") whenever the price row is not "known".

### D4. Default and proxy dims still reach the user through paths X6 does not touch

X6 changes `build_dimensions_v2` and the two RB dim candidates only. Three other paths read the same proxy and default-50 scores:
1. `overview.winner.key_tradeoff` = "{loser} stays competitive on {dim}." (RB:238-244), from `compute_tradeoff_pairs(scoring_result["dimension_winners"], ...)` (SCS:3850-3857). The dim can be versatility or presentation. RunnerUpWinsCard renders it on BOTH live bundles whenever the body is not degraded (RC:239-241). After N1 works, "X stays competitive on versatility" can come from a default 50.
2. The AI verdict prompt: `build_scores_summary` (SS:3017-3095) sends "longevity: stronger / weaker" per dim from the score breakdown, with `breakdown.get(dim, 50)` (SS:3068, 3071) and including the star-proxy longevity and projection. After N1 works, the AI prose (winner reason, pros, cons) can repeat "longer-lasting" from star ratings. R-A8 (PLAN_S80.md:29) already rules "the verdict prompt's scoring context omits limited_data dims"; the proposal does not carry that part of the ruling.
3. The crown: Q8 defers it, so R3's Armani still "wins" with every score at the default 50 (inventory part c, consequence 5), with TopMatchBadge and the winner styling. See D9.
Correction: X6 must also cover the tradeoff source and the prompt summary for fragrances under the same flag, or the proposal must list both as stated limits with their own owner question.

### D5. Assumption 6 ("the live product is fragrance-only") is false today

The fragrance-only gate (ENABLE_FRAGRANCE_ONLY_GATE) is an S81 flag; the lane header H2 says every S81 flag is OFF except two others, and the incident report X3 row (INCIDENT_AND_DATA_PLAN_2026-11-11.md:102) says it still waits on the v3 Terms and the second OTA. So non-fragrance comparisons are served today. With X5 covering only the fragrance captions and X4 client rule 2 hiding any un-coded sentence on the Arabic UI, a non-fragrance result on the new app would lose its bar captions in Arabic. Correction: state the limit against the gate's real state, or add ids for the non-fragrance captions (`+{margin}pt edge`, SS:3617, and the generic tail of `_compose_delta_text`).

### D6. An existing visible "limited data" row was missed

DimensionBars already renders a visible row for any dim with `data_insufficient: true`: label + `results.dimensions.limited_data` ("Limited data", en.json:208; ar.json:205), DB:68, DB:148-154, DB:224-233, byte-identical in ST. The proposal's assumption 3 says only the `limited_data` placeholder shape is safe and that a new shape risks the zero-score node; it does not mention this path. It matters because the incident report's X6 proof (INCIDENT_AND_DATA_PLAN_2026-11-11.md:105) says the longevity / projection rows "show 'not known'" on the phone; with the proposal's shape they VANISH on both live bundles, so that proof can only pass on the X4 app. The owner should choose: invisible rows on the live apps (the proposal) or a visible "Limited data" row on the live apps today (set `data_insufficient: true`, scores null). Q3 must carry this choice and the proof text must be reconciled with the incident report.

### D7. Q9 re-asks a question the owner already ruled, and states the camera limit as permanent

R-A10 (PLAN_S80.md:31) is a ruling: deterministic templates are localized SERVER-SIDE by value when `output_lang == 'ar'`, under the EXISTING flag ENABLE_ARABIC_VERDICT_OUTPUT, and W4-14b adds `lang` to /image/identify and /url/compare. The proposal presents by-value Arabic as an optional "Q9, later" and says it "does not reach the camera path"; under the ruling the camera path gets `lang`. Codes for the new app may be a better design, but changing the delivery of a ruled unit is a ruling the owner makes in words: Q9 must say "this replaces (or adds to) your R-A10 ruling", and must say that only R-A10 removes English from the two live bundles.

### D8. The X5 contract breaks its own rule 3 and two templates

- Rule 3 ("never concatenate translated fragments") is broken by `results.msg.dim.value.cross_tier` = "Across tiers: {{text}}" (a translated caption nested in another) and by `dim.projection.levels`, which inserts two translated sillage words into a third string. One key per (id, cross_tier) and per (a, b) pair, or drop the levels caption.
- `fv.l1.yt_attention` has a mandatory `{{channel}}`, but the server omits the clause when no channel exists (RB:1083). Two ids are needed, or the Arabic renders a dangling clause.
- `views` is a humanized string today (RB:1068), not an int; the client needs its own humanizer if the arg is an int (state which).
- `dim.price.less` lists args `amount, currency` but its client key uses `{{price}}`; say the client formats `amount + currency` into `price`.
- `fv.l1.edges_overall` / `fv.l1.leads_overall` are also the WINNER-REASON templates (RB:192-193), which go to `overview.winner.reason_msg`, not `factual_verdict`; naming them `fv.l1.*` invites a wrong placement.

### D9. Owner questions that hide a default

| Question | What the recommendation hides |
|---|---|
| N5 "show it with its size" | the live bundles' view (D2): with X1's wire shape they show the other bottle's price with no size and run cheaper claims on it |
| N5b (a) | value (D3) still compares; the per-ml line itself invites the comparison the option says it avoids; "favours the bigger bottle by construction" is an empirical claim, not a construction, and was not measured |
| Q7 "yes" | the size shown can be the rejected listing's (D1) |
| Q8 "not in these units" | the default-50 crown stays on both live apps and on the new page; no unit in this lane owns it, and the "result-gate lane" that would is UNVERIFIED (no spec found in the record copy) |
| Q3 "yes" | the choice between invisible and visible unknown rows on the live apps (D6) |
| Q10 "yes" | on the new app in Arabic, EVERY saved comparison reopened from History (bodies without `*_msg`) loses its verdict lines and bar captions; state it |

## 3. Missing consumers and render paths

| Missing item | Evidence | Why it matters |
|---|---|---|
| Home smart-pick caption copies `factual_verdict.line1` (flagged) into `verdict_short`, rendered verbatim by both bundles | app/api/home_routes.py:628-648, :693; CL and ST HomeEditorialSections.tsx:115, :230 | X6 changes this caption on both live apps (when that flag is ON, UNVERIFIED); X5 gives it no code, so Arabic Home keeps English; absent from proposal section 7 |
| The link (URL) compare body renders on the same Results screen | HomeScreen.tsx:618, :642 `navigateToResultsWithFloor(response.data)`; body url_extraction_service.py:1500-1509 has no `overview` / `scoring_v2` | the fixed ten-section page has no defined state for a body with neither; after N1 works link compares return this body |
| The SSE progressive payload | SCS:5647 | the fixed page will render "unknown" states on early payloads, then flip; say whether X4 renders progressive bodies through the fixed page |
| `overview.products[i].variant` is server text shown verbatim ("100ml · EDP") | RB:553-610, RB:1950 | not in X5's vocabulary; acceptable as units and abbreviations, but list it as a stated exception in the X4 proof's "no English" rule |
| Existing near-duplicate keys | `results.noRating` "No rating available" (en.json:160, ar.json:157) vs proposed `results.reviews.noRating`; `results.dimensions.limited_data` (en.json:208, ar.json:205) vs proposed `results.honest.notKnownYet` | reuse or retire one; two keys for one meaning split the native read |

## 4. Copy policy and Arabic drafts

- `results.msg.wr.stronger_overall` Arabic draft uses "الأقوى" ("the strongest"), an absolute superlative, where the English is comparative ("stronger"). The copy policy bans absolute superlatives in intent (i18n/.copy-policy.json `_doc`, Bundle E Decision 5) even though its pattern list does not catch this word. Use a comparative form. The English keeps "pick", which is on the server and client banned-word lists (app/models/scoring_v2.py:9-14; FactualVerdict.tsx:24-38); the proposal says it rewords captions to pass that list, so it should say why this one is kept (it is today's RB:1414 text and is not rendered through FactualVerdict).
- `results.price.differentSizes`: the Arabic says "so we do not compare the price directly", the English says "so no cheaper claim"; the two say different things. One meaning, then the native read.
- No draft uses a banned scary word (تعذر, فشل, تقدير, مُقدَّر) or a banned pattern: checked against .copy-policy.json in this run.
- The 54 count (14 + 40) and the 33-entry vocabulary were recounted and match.

## 5. Proofs on the phone that could pass while the problem remains

| Slice | How it passes falsely | Correction |
|---|---|---|
| X6 | Every check is an ABSENCE ("no Longer-lasting bar"). Pair 2 also loses its proxy bars if this run's ratings come back derived or missing (both sides missing means the dim is omitted, SS:3570-3571), so the proof passes with X6 broken | add a positive control in the same screenshot: the Reviews bar visible with real ratings on both sides, and the saved row's longevity / projection rows present with `state` "unknown" and `caption_key` "limited_data"; for pair 3, the versatility row is ABSENT from the list (not merely hidden) |
| X6 | "`winner_index` equals the value a flag-OFF run gives" cannot be done on production without a second flip in the same window | make it a hermetic before / after on the saved row inputs, and say in words it is not the production proof (H6 c) |
| X4 | Client rule 2 hides any un-coded sentence in Arabic, so "no English sentence" passes even when X5 is OFF or broken (the sections just show their honest lines) | require, for each golden pair whose row has `factual_verdict.line1_msg`, the Arabic fact line visible; and print the ids found in the row next to the screenshot |
| X7 | "key_differences non-empty" is met by one English price line no app renders | keep it, but state that X7's phone proof exists only with X4 |

## 6. What the documents get right (kept)

The section inventory, the store-versus-OTA table (cohort line only, with today's flags), the proxy audit of R1-R3, the finding that no bundle renders `key_differences` (RS:437, ST RS:414) and that filling the frozen `string[]` key is invisible, the additive-only key rule, and the decision that X6 leaves the crown alone as a separate question are all supported by the code read in this run.

## 7. Unverified in this round

- ENABLE_SMART_PICK_VERDICT_CAPTION, ENABLE_URL_MODE_V2 and ENABLE_FRAGRANCE_ONLY_GATE production values (the last is OFF by H2's general statement, not by a dated read I made).
- Whether a non-pended price carries `price.size`, and whose size it is (listing or product).
- Whether `review_raw` (the projection signal, SS:2544-2551) excludes a derived rating; if not, R-A8's "GPT-estimated ratings never drive a category dimension" is broken today as well.
- Whether a "result-gate lane" spec exists that owns Q8.
- Whether specs read from older caches carry `_field_confidence` (result_gate.py:253-258); a spec without it is treated as NOT model knowledge, so X6's "not a Tier-3 value" rule would let an unmarked model value count as "known". X6 must say which way an unmarked value goes.
