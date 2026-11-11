# PAGE v2 VERIFY: PAGE_DESIGN_V2.md, OWNER_BRIEF_RESULT_PAGE.md, RESULT_PAGE_MOCK.html

Written 2026-11-11 by the verifier of the S92-FIX incident lane. READ-ONLY round: no pytest, jest, tsc, eslint, network, git write, package manager, production probe or .env read. Every file:line below was re-read in this run on the plain exports (src/a74caba7 for app/ and the OTA client, src/683f56c0 for the store client) and the record copy. Short names as in PAGE_DESIGN_V2.md (RB, SS, PS, RC, RA, DB, HR, IR). Nothing here says a production problem is fixed.

## Verdict

READY_WITH_NOTES. The design is sound and follows every binding decision. Every PAGE_SKEPTIC.md finding is applied, and the citations I spot-checked hold. But one claim is false and reaches the founder: the History list does NOT show the server caption (V1 below), yet question 12 in the brief and in the mock says it does. Three smaller errors also need fixing (V2 to V4). Make the edits in section 6 before the brief and the mock go to the founder.

## 1. Skeptic findings not applied, or applied only in part

| Skeptic item | Status in v2 | Evidence |
|---|---|---|
| D1 "Q7 must say this in words" (a size never comes from a rejected listing) | applied in PAGE_DESIGN_V2.md Q10. The owner brief's Q10 and the mock's Q10 drop that clause ("Show 'EDP - 100 ml' under the names on today's apps too? Yes.") | OWNER_BRIEF_RESULT_PAGE.md:53; RESULT_PAGE_MOCK.html:284 |
| D7 (R-A10 ruling) | applied. v2 section 13 says PLAN_S80.md:31 was "not re-read". I re-read it: line 31 is R-A10 and says what v2 says. The flag ENABLE_ARABIC_VERDICT_OUTPUT exists (app/services/extraction_service.py) | record/s80/PLAN_S80.md:31 |

Every other item is applied correctly: D1-D6, D8, D9, the s1 citation notes, the s3 missing consumers, s4 and s5, and the s7 unverified list. The two "applied differently" items keep reasons that hold. `results.honest.notKnownYet` is used only for an empty pros or cons side. The product size comes from the typed name or the accepted title, never from `price.size` (PS:2021-2045, PS:2402-2417).

## 2. New or changed claims that are false or wrong

| # | Claim in v2 / brief / mock | What the code says | Where it must change |
|---|---|---|---|
| V1 | P7: "the History list renders the same server caption as the Home smart pick" (also section 7 X6 row "new Home and History captions inherit the honest line1", L-HOME, L-HOME-AR, Q12, brief Q12, mock Q12, and the finalizer's "new finding") | FALSE. The History list route builds summaries with id, query, product_names, input_type, winner_index, the two image urls and created_at. It sends NO `verdict_short` (app/api/history_routes.py:116-125, route at :87; the client calls /api/v1/comparisons/history, services/api.ts:478). So `item.verdict_short` is undefined and the row shows `formatTitle(item)` = "A vs B" from the product names (HistoryScreen.tsx:495, :499, :414-424; the type comment says "Backend MAY surface", :77-79). In app/, only home_routes.py writes `verdict_short` (HR:648, :693). The store client's History reads the same route | drop History from P7, section 7, L-HOME, L-HOME-AR and Q12 in all three files. P7 becomes "History shows the two names; no server sentence; no limit" |
| V2 | X5 arg table: `hi, lo` "int, hours (SS:3667) or dose amounts (SS:3705, :3709)" | FALSE for doses. `_extract_dose` returns a float with decimals (SS:3821-3831), and the captions print it with `:g` (SS:3705, :3709), for example "2.5 mg". Hours are cast to int (SS:3667). An int-typed dose would print a wrong number | type `hi, lo` as number, or split them into int hours and number doses (B6 "typed args") |
| V3 | Brief section 1 table, today's "Why this fits you": "a grey note, then two English sentences, also in Arabic" | WRONG for the founder. Today the two fact lines are English on the Arabic app too (RB:1073-1131 builds English only; v2 Part 1 line 33 says this correctly). "also in Arabic" reads as if an Arabic version exists | OWNER_BRIEF_RESULT_PAGE.md:14: "then two English sentences, even on the Arabic app" |
| V4 | Details line written "EDP - 100 ml" (Part 1, 5.3, Q10, brief, mock). The mock draws "EDP · 100 مل" with an Arabic unit | INCONSISTENT with v2's own rule. `_compose_variant_string` puts volume first, then concentration ("100ml · EDP", RB:572-573, RB:603-610). v2 section 4 client rule 5 shows `variant` VERBATIM as server data ("100ml - EDP"). So the Arabic page would show Latin "100ml · EDP", not "EDP · 100 مل" | either X7 changes the order and X4 builds the line from typed fields (state both, with new keys), or the mock, the brief and Q10 show "100ml · EDP" |
| V5 | 5.1 row 5: "PS:4072-4084 patterns and function" | citation slip. The patterns are at PS:4060-4069, `_SIZE_ML_RE` is at PS:4073, and `extract_concentration` is at PS:4076-4084. The conclusion ("Profumo" reads null) holds | fix the line range |
| V6 | P7 cite "CL HistoryScreen.tsx:615" | :615 is a JSX comment. The render is at :617-619 (ST :619-621) | minor |

## 3. Claims re-measured and CONFIRMED (spot list)

| Claim | Re-read |
|---|---|
| B1: an off-size side keeps `amount` null; no price reader can use a new key | PS:2005-2018, PS:2409-2413; `_safe_price_amount` RB:842-852; `_price_candidate` RB:873-894; line2 fallback RB:1114-1121; `_get_price` SS:3171-3175 feeds `_dim_price` SS:3240-3262 and `_dim_value` |
| B2 sources | `_product_size_text_fields` PS:2021-2045 (name first); `_SIZE_ML_RE` PS:4073; "Profumo" matches no pattern PS:4060-4069 |
| Q3: the visible "Limited data" row exists on both bundles | DB:68, DB:82-88, DB:148-154, DB:224-233; DimensionBars.tsx byte-identical in CL and ST (cmp this run); en.json:208, ar.json:205 |
| price and value rows hidden when any price pends; pill hidden | RC:212, RC:555-562, RC:593; ST RC:159, :488-492, :526 |
| outer gate | RC:527 |
| runner-up card source and hide rule | RB:238-244; RC:239-241, ST RC:186-188; RunnerUpWinsCard.tsx:100; SCS:3850, :4750, :5598; F4.2 SS:2763-2769 |
| prompt summary defaults | SS:3068, :3071; SCS:4653, :5504 |
| proxies and defaults | SS:2175-2179, SS:297, SS:3168, SS:3226-3227, SS:3566-3589, SS:3880-3881, SS:3896, SS:1814-1824 |
| fact-line and winner-reason templates (20 ids) | RB:192-193, RB:1066-1068, RB:1083-1098, RB:1111-1131, RB:1175, RB:1414-1415, RB:244 |
| caption branches (30 ids) | SS:3246-3302, SS:3380-3412, SS:3608-3733 |
| cross-tier and point-math captions are already replaced on screen | DB:276-291; `safeDelta` and POINT_MATH_RE in _deltaText.ts:19, :43-47 |
| `score_a` / `score_b` typed int; core keys exactly price, reviews, value; max 8 rows | app/models/scoring_v2.py:24-31, :56-68 |
| banned caption words include "pick" and "better" | app/models/scoring_v2.py:9-14 |
| Home caption copies line1 when the flag is ON | HR:629-648; HES:115, :230 in both trees |
| link body has no overview or scoring_v2; LLM_UNAVAILABLE while AI fails | url_extraction_service.py:1483-1509; HomeScreen.tsx:618, :642 |
| no screen passes the stream callbacks | services/api.ts:654-660, :961-968 (grep of CL src, tests excluded) |
| key_differences is always []; no bundle renders it; share passes it | RB:2297; RS:437, ST RS:414; referral_service.py:178 |
| reused keys | en.json:160/ar.json:157, en.json:705/ar.json:702, en.json:261/ar.json:258, en.json:770/ar.json:767, ar.json:131, ar.json:146, ar.json:793, :841 |
| incident report | IR:100 says "price.amount not null" (to restate under B1); IR:103 puts X4 after Friday's second OTA; IR:105 is the X6 proof text |
| string counts | 13 page + 20 + 11 + 9 + 6 = 59 Arabic strings; 50 ids (recounted from the tables) |
| copy policy | no `banned_ar` or `scary_vocab_ar` pattern in any of the 64 Arabic table cells. No `banned_en` or `scary_vocab_en` pattern in the new English strings or the mock (regex run of i18n/.copy-policy.json this run) |
| R1 and R3 shapes used by the mock | record/incident/T1_trace.md:16-17, :29, :59-64, :101-103, :117-119, :149-151 (R1: photos found, ratings derived; R3: no photos, ratings derived, Versace 25.000 with a "100ml" title) |

## 4. Binding decisions and owner-facing rules

| Check | Result |
|---|---|
| B1-B7 from the finalizer prompt (wf_inc_design_v2.js:49) | followed: sections 0, 2, 2.4, 3, 4, 8, 9, 10 |
| Facts of record (no app-version signal; dark flags; client changes only in a later OTA after design approval and the Arabic read; the gate is OFF; CL3 shown as existing) | followed |
| Brief: plain language, no file names | yes, 917 words, no file names |
| Brief: each question one line with a recommendation | yes, 16 questions |
| Brief: nothing says a problem is fixed | yes |
| Brief: no date promised | yes. Note: "in the update AFTER Friday's second update" (OWNER_BRIEF_RESULT_PAGE.md:37) names a day to give an order, not to promise a date. "after the next legal update" would avoid any reading as a date |
| Brief wording risks | section 2 "fake bars and the default 'win' stop appearing" can be read as the overall winner, which X6 does NOT move (Q5). Say "the default win on a bar". Section 2 also omits that the shoppers line leaves the store app (X9, ruled) |

## 5. The mock against THE PHONE MOCK rules

| Rule | Result |
|---|---|
| title of 2-4 words | "Result Page Mock" |
| inline CSS and JS; no external request | grep for http, src=, href=, url(, @import, fetch, XMLHttpRequest, localStorage, form, input, img, link, sendBeacon, WebSocket: no hit |
| system fonts | yes (font stack only) |
| colour tokens on :root; dark under prefers-color-scheme guarded by :root:not([data-theme="light"]), and again under :root[data-theme="dark"] | yes |
| explicit body background | yes |
| 360 px, 16 px gutter, no horizontal scroll | `.wrap` padding 16 px; grids use min-width 0; table-layout fixed; overflow-wrap anywhere. NOT rendered in this round: UNVERIFIED on a real 360 px screen |
| localStorage | none |
| size | 27,293 bytes, LF, valid UTF-8 |
| Arabic first, then English; the state switch in the right order, state 1 on load | yes (lines 110-117, 292) |
| state 1 = the R1 shape with no AI text | yes: honest lines for the explanation, pros and cons, review highlights and specs. Prices, photos, derived ratings shown as "No rating available", the 5 bars, 3 key-difference rows (matches v2 5.2) |
| state 3 = the R3 shape | yes: no photos, Armani pending, Versace 25.000 at 100 ml, 4 key-difference rows, never 40 ml |
| same sections in the same order in all states | yes: cards 1-10 and the five bars in the same order, drawn by one function |
| Arabic strings equal the v2 table | yes: every new string used matches a v2 table cell character for character. Every other Arabic string matches an existing ar.json value exactly (script check this run) |
| labelled a design proposal; Arabic lines are drafts | yes (line 106). The banner sits at the top only and scrolls away on a phone; a sticky banner would be safer |
| Questions for you, one line each with the recommendation | yes, the same 16 as the brief. So Q10 and Q12 carry the issues in sections 1 and 2 |
| no analytics, forms or links out | yes |
| ASCII except Arabic (lane rule) | NOT met: the English strings and the markup use non-ASCII marks (U+2039, U+203A, U+00B7, U+2014, U+2605) |

## 6. Edits needed before the founder reads the brief and the mock

1. V1: remove "History" from Q12 in the brief (line 57) and in the mock (line 286). Fix P7, section 7, L-HOME and L-HOME-AR in v2 the same way.
2. V3: in the brief (line 14), change "also in Arabic" to "even on the Arabic app".
3. V4: decide the details-line form ("100ml · EDP" verbatim, or a client-built "EDP · 100 مل"), then make the mock, the brief and Q10 match it.
4. D1: add "never from a price for another bottle size" to Q10 in the brief and the mock.
5. V2 and V5: fix the arg type and the line range in v2 (the founder does not see them).

## 7. For the orchestrator

- The finalizer's "new finding" (History = P7) is refuted (V1). Do not carry it into any brief.
- v2 section 3 states the X1 items E-X1-a, E-X1-b and E-X1-c and the IR:100 restatement correctly (IR:100 re-read).
- A minor X4 RED item: today a cross-tier value row always shows `results.value.different_tier`, even when the server caption is "Comparable value" (DB:279-291 checks `is_cross_tier` only). Mapping that row to `dim.value.comparable` would change what the screen shows, so X4 should keep the `isCrossTier` override.

## 8. Not verified in this round

- How the mock renders at 360 px (nothing was rendered).
- Whether the R1 Aventus listing title, as stored, states 100 ml (T1 gives it from the logs).
- The production flag values listed in v2 section 15.
- Every runtime check is DEFERRED TO RED, with the commands in v2 section 15.
