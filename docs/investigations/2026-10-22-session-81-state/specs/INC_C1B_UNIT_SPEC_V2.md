# INC-C1b: unit spec V2 (main lane spec writer, Opus 5.5, 2026-11-22)

V2 applies the orchestrator's rulings RU-1..RU-15 (lane-s98/inc-c1b/RULINGS_INC_C1B.md) to V1 (INC_C1B_UNIT_SPEC.md, sha256 af247cff2e31e90c0b35be24afce581f04e771d8f47dfa695c88b1f6903b43a1) and its review (INC_C1B_SPEC_REVIEW.md, verdict AMEND). Where V1 or the review differs from a ruling, the ruling wins. Changed against V1: this header, sections 1, 2.2, 2.3, 3.2, 4, 5.1, 5.3-5.5, 6, 7.2, 7.3, 8, 9, 10, 11 (11.4 new), 12, 13 (now a pointer), 14, and Appendix A (new: V1's section 13, for INC-RT1). Section numbers are V1's.

Base: main `7e2e317c` (byte copy c1b/base: SmartCompareApp src, __tests__, __mocks__, configs; app/; tests/test_s81_12_legal_v3.py and, since V2, tests/test_comparison_id_echo.py, tests/test_events_allowlist_superset.py, tests/test_s81_sf1_surfaces_be.py). INC-C1 (#428) is in the base: services/homeEntryIntent.ts, __tests__/c1/, 1,038 catalog keys. Cites are file:line at 7e2e317c; client paths are under SmartCompareApp/src. RB = app/services/response_builder.py, SS = app/services/scoring_service.py, ES = app/services/extraction_service.py, SCS = app/services/structured_comparison_service.py, LR = app/services/llm_router.py, HR = app/api/history_routes.py. Glyphs that are not ASCII are written as bracketed hex code points ([2605] the star, [B7] the middle dot, [2191] the up arrow); Arabic as in INC-C1 V2 section 6: "quoted ASCII" plus [hex code points], 20 = space. ESTABLISHED = read in code or measured on the owner's screens; LIKELY = best reading.

Test data: the owner's phone test of 22 Nov 2026, "Imagination men" vs "Creed Aventus" (the owner's case file, private notes; rows B-a, B-b, B-c, B-d, B-f; every B row was checked against the owner's screens and the code below). Public test files may use the two names and the numbers of the case, never a screenshot, an account value or a private note path; they cite "the owner's phone test of 22 Nov 2026".

## 1. Scope and placement (RU-1, RU-2, RU-6, RU-12)

INC-C1b is CLIENT ONLY (RU-1): T7-09, T7-11, the B-b client part, B-d, B-f. B-a, the B-b server part and B-c go to a sibling server unit, working name INC-RT1 RESULT-TRUTH (three switches, default off, merged dark), proposed to the relay at the gate; its design is Appendix A, and none of it is built or tested in INC-C1b.

| item | producer at 7e2e317c | side | placement | files |
|---|---|---|---|---|
| T7-09 picture retry | ProductImage.tsx:73, :103: the first onError sets `errored` and the placeholder stays for the life of the mount | client | IN | components/primitives/ProductImage.tsx, services/sentry.ts |
| T7-11 "Saved on" | HR:164 sends `comparison.created_at`; api.ts:517-531 (getComparison) drops it | client | IN | services/api.ts, types/types.ts, services/fieldStatusView.ts, components/results/ResultsContent.tsx, i18n en/ar |
| B-a price claim | model text `overview.winner.key_tradeoff` (ES:1056, :1086; rule ES:1093 already forbids it); the fail-closed price-adjective drop covers pros/cons only (RB:2006-2028); key_tradeoff ships after strip_score_internals only (RB:2039, :2098, :2441-2443) | server | INC-RT1 SD-A (Appendix A.1) | none here |
| B-b equal values | (a) client: RunnerUpWinsCard.tsx:50-63 lists by score and never reads `winner`; DimensionBars.tsx:263-269, :280-282, :302-306 paint by score when the server says `winner: null`. (b) server: fragrance longevity is a spec/review composite (SS:2176, :2339-2352) that ignores equal hours (F4.1 swaps only on a gap >= 1 h, SS:2430-2445); margin >= 3 crowns a side (SS:3189, :3235-3237); one-sided-missing dims are drawn against the 50 sentinel (SS:297, :3226-3227) | both | client part IN (RU-2 design, 5.3); server part INC-RT1 SD-B (A.2) | components/results/RunnerUpWinsCard.tsx, components/results/DimensionBars.tsx |
| B-c size win | RB:823-861 `_spec_row_winner`: larger numeric wins for any field outside `_SPEC_SMALLER_WINS` (volume 100 > 50 -> 0); the client only paints it (ResultsAccordion.tsx:228-238, :605-615) | server | INC-RT1 SD-C (A.3); no client guard (RU-14) | none here |
| B-d reviews header | ResultsAccordion.tsx:170-196 sums review_count over both and weights the rating by count; :267-276 prints "... reviews across both" | client | IN | components/results/ResultsAccordion.tsx, i18n en/ar |
| B-f CONCENTRATION | ResultsAccordion.tsx:637-639 label Text with no line rule; style :922-930 (width 96, 11 pt, uppercase, letterSpacing 0.4) | client | IN | components/results/ResultsAccordion.tsx |

The B rows against the pictures (all hold):
- B-a ESTABLISHED (screen 1): runner-up prose "Imagination men offers a brighter, more versatile citrus profile with strong projection and a lower retail price point." while the left card reads `results.price.pending` "No confirmed price yet." (ResultsContent.tsx:224, so `price.unavailable` is true).
- B-b ESTABLISHED (screens 1, 2): "+ 8h vs 8h" under WHERE THE RUNNER-UP WINS; Longevity "8h vs 8h" left green and longer (434 against 414 px, 51.2 %); Projection "Heavy vs Heavy projection" right green and longer. Measurements in 5.1. The bridge's transcription "Longevity: left side green, a little under half the width" is wrong: 51.2 % is a little over half (RU-6).
- B-c ESTABLISHED (screen 5): VOLUME row, left "100 ml" in the accent colour, right "50 ml".
- B-d ESTABLISHED (screens 2-4): Reviews sub "4.4[2605] avg [B7] 5,600 reviews across both"; in the body only Creed Aventus has a star row ("4.4 [B7] 5,600 reviews"), Imagination men has a praise paragraph only.
- B-f ESTABLISHED (screen 5): "CONCENTRATI" / "ON". Only SCENT FAMILY wraps, at its space; TOP NOTES, HEART NOTES and BASE NOTES each fit on one line (RU-6).

Summary. INC-C1b (client, over-the-air): T7-09, T7-11, the B-b client part, B-d, B-f; 11 files; 2 new catalog keys (1,038 -> 1,040); 22 RED rows and 12 pins in 6 test files (section 10). B-a, the B-b server part and B-c are INC-RT1's (Appendix A). S81-07m does not take B-a (4.4).

B-b closing (RU-2). Case row B-b closes fully only when the client part AND INC-RT1's SD-B are live: the client part stops crowning a side the server did not crown; equal shown facts then draw equal bars through SD-B (i) (equal scores), and one-sided-missing dims leave the screen through SD-B (iii) (`caption_key: 'limited_data'`). The PR body says this in one sentence. The over-the-air publish that carries INC-C1b does NOT wait for SD-B: with the bars proportional and no win colour on a winner-null dim, every caption and the verdict's line1 still point at the longer bar, so the client part adds no contradiction on its own (Q6, answered by RU-2).

Class: FOCUS (RU-12). Two adversaries after GREEN: (1) correctness under every server answer, flag mix and stored body (History bodies saved since F2.4 carry `winner: null` on many dims, SS:3911-3927, so the paint change reaches many stored results); (2) words and RTL. Switch: none on the client (the app has no remote flag store; config/features.ts holds build-time defaults, so a client flag would need another publish to flip, the same act as a rollback). Every new behaviour keys on data: a failed image, a readable `created_at` on a stored body, an explicit `winner: null`, one-sided review figures, a one-word label. Shipping: merged code reaches phones only through an over-the-air publish (runtime 1.0.0), the owner's; INC-C1 and INC-C1a ride along if they are not yet published (Q9, relay).

Production flags. ENABLE_LISTING_MATCH_GUARD (ON on web since 22 Nov 08:03) is the gender-line rule of price selection, cache read and display (price_service.py:8342-8367, :9007-9009; Creed Aventus is one of its four lines). It touches no item's code path; it can only pend more prices, so B-a fires more often (INC-RT1's SD-A). ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT and ENABLE_FIELD_STATUS_METADATA (not set on web) are read by no item; with field status off ResultsAccordion gets no `honest` prop (ResultsContent.tsx:719-736) and B-d / B-f render the base accordion.

## 2. T7-09: one picture retry and a host-only breadcrumb

### 2.1 Producer (client)
- ProductImage.tsx:73 `const [errored, setErrored] = React.useState(false);`, :77-79 reset on an `imageUrl` change, :81 `const usable = isUsableUrl(imageUrl) && !errored;`, :103 `onError={() => setErrored(true)}`. One failed fetch (a slow first byte, a CDN blip) puts the placeholder (:118-153) on the tile until the url changes or the screen remounts.
- Consumers: Results cards (ResultsContent.tsx:409-416), History rows and hero, Home SmartPick, Profile tiles. No signal reaches Sentry, so the failure rate is unknown. (The server allowlists an /events type "image_load_failed", app/api/feedback_routes.py:94, that the client never fires; INC-C1b does not start firing it: a per-failure network call would cost more than an on-device breadcrumb.)

### 2.2 Fix (RU-7, RU-8)
1. ProductImage: `RETRY_DELAY_MS = 1500`; new state `attempt` (0 the first load, 1 the one retry) and a timer ref. onError:
   - while a retry timer is pending: ignored, so a doubled native error arms one timer at most (RU-8);
   - at attempt 0: `setErrored(true)` (the placeholder shows at once, so the state-4 pins ProductImage.test.tsx:88-109 hold) and one 1,500 ms timer that clears the ref, sets attempt 1 and `errored` false; the placeholder branch had unmounted the Image, so a fresh Image mounts and the native view loads the same uri again (no cache-busting query: signed CDN urls stay valid);
   - at attempt 1: `setErrored(true)` for good, then the breadcrumb call inside try/catch.
   The reset effect (:77-79) also sets attempt 0, and its cleanup clears a pending timer (a url change and an unmount). The effect body copies the ref into a local and the cleanup reads that local, so react-hooks/exhaustive-deps raises no new warning (RU-8). A design that arms the timer in an effect keyed on `errored` and `attempt` is equally acceptable if it keeps one timer at most and clears it on a url change and an unmount: row I7 observes the timer count, not the design. No prop, testID or style changes.
2. sentry.ts, beside addSseFallbackBreadcrumb (:255-268): `export function addImageLoadBreadcrumb(imageUrl: string): void`. host = the authority without user info or port, lower-cased, from `/^[a-z][a-z0-9+.-]*:\/\/(?:[^/?#@]*@)?([^/?#:]+)/i` (no URL class), else 'unknown' (an address without "//"; other address kinds: the follow-up INC-C1c); at most one breadcrumb per host per app session (module Set, cap 20 hosts); `Sentry.addBreadcrumb({ category: 'image', level: 'warning', message: 'product image did not load after one retry', data: { host } })`, exactly these four keys; wrapped in try/catch. Never the path, the query, the scheme, user info or the port: scrubString would not redact "u:secret@" or ":8443" (sentry.ts:30-48), so the extraction itself drops them (row I6). scrubBeforeBreadcrumb (:201-214) still runs at creation. No trackEvent or `event_type:` literal (the events-allowlist reader, 11.2).
3. The call site wraps the call in try/catch, so a suite whose `services/sentry` mock lacks the export (sixteen suites mock that path at base, most with a partial factory) cannot crash on an image error.

### 2.3 Rows
Section 10.1 (I1-I7, P-I1). Strings: none.

### 2.4 Risk
One extra request per failing image (one retry per mount and url, 1.5 s later); a History list with many dead images makes that many extra requests. The breadcrumb ring stays small (one per host per session).

### 2.5 Limits
L1, L2.

## 3. T7-11: "Saved on <date>" on a History result

### 3.1 Producer (client)
- HR:138-167 (GET /api/v1/comparisons/{id}) returns `comparison.created_at` (:164; database_service.py:539-566 selects "*").
- api.ts:517-531: `return comparison?.id ? { ...full, comparison_id: comparison.id } : full;` (:530) drops created_at.
- ResultsScreen.tsx:997 passes `resultOrigin={route?.params?.comparison_id ? 'stored' : 'live'}`; ResultsContent prints listed dates per price (:196-200) but nothing for the result itself.

### 3.2 Fix (RU-9)
1. api.ts:530: additive `saved_at` = `comparison.created_at` when it is a string and `Number.isFinite(Date.parse(created_at))`, set independently of `comparison_id`, so with or without an id (RU-9). `comparison_id` keeps its rule (`comparison.id` truthy). With neither, `full` is returned as today; the 404 branch is unchanged; the server's string is passed as is.
2. types/types.ts: ComparisonResult gains `saved_at?: string` beside `comparison_id` (:298), documented as set only on a body re-opened by id (getComparison) from a readable created_at.
3. fieldStatusView.ts: new pure `formatSavedOnDate(dateIso, language)`: returns '' when `Date.parse(dateIso)` is not finite (never toISOString on an Invalid Date, RU-9); else `toLocaleDateString` with `{ year: 'numeric', month: 'short', day: 'numeric', calendar: 'gregory' }`, locale 'en-US' or 'ar-SA-u-ca-gregory' (as formatAsOfDate :91-100), then `applyDigitSystem(toAsciiDigits(...))`; its catch (a locale missing from the phone's ICU) returns the ISO date of the valid date, `toISOString().slice(0, 10)`. It carries the year, accepted by RU-10 (a saved result can come from an earlier year; formatAsOfDate prints month and day only).
4. ResultsContent: when `resultOrigin === 'stored'`, `Number.isFinite(Date.parse(result.saved_at))` (RU-9) and the formatted date is not '': a Text, testID `results-saved-on`, numberOfLines 1, caption style (11 pt, text.secondary, marginBottom spacing.sm), `t('results.savedOn', { date: formatSavedOnDate(saved_at, lang) })`, as the first child of the ScrollView content, above `results-content-hero-pair` (:380). Otherwise nothing: live results, a missing origin and bodies without a readable field stay byte-identical. The server's created_at format already parses on phones (HistoryScreen.tsx:500 and :785 read the same column).
5. Strings: row 1 of section 9.

### 3.3 Rows, risk, limits
Section 10.2 (S1-S3, P-S1, P-S2). Risk: none on live results; a stored result gains one line. Limit L3.

## 4. B-a: no price claim about a side with no confirmed price (server, INC-RT1)

### 4.1 Producer (server)
- The sentence is `overview.winner.key_tradeoff`, model output of COMPARISON_SYSTEM (ES:1056 "ONE sentence naming the other product's strongest advantage", ES:1086). The prompt already forbids it (ES:1093, PENDING PRICE); the verdict payload already hides a pended amount (ES:2482-2513). The model wrote it anyway (LIKELY from its own knowledge of the retail price).
- The builder: Task C3 (RB:2006-2028) drops price-adjective pros/cons of a pended product only. key_tradeoff gets `strip_score_internals` only (RB:2039) and ships at RB:2098, in the BC alias (RB:2441-2443) and in the stored row; winner_reason likewise (RB:2036-2038, :2097, :2453). `_PRICE_ADJECTIVE_RE` (RB:795-800) holds `pric(?:e|ey|ier|y)\b`, which matches "price point".
- The client renders the text as received: ResultsContent.tsx:311-313 -> RunnerUpWinsCard.tsx:91-96 (SCORE_INTERNALS_RE only), :110-114.

### 4.2 Root cause
The fail-closed price-claim drop stops at pros/cons; the runner-up and winner prose escape it.

### 4.3 Fix
Not in INC-C1b (RU-1): INC-RT1's SD-A (Appendix A.1). No client change: the client is not the producer, and a client text filter would need English and Arabic word lists, would duplicate the server rule, and would still miss bodies the server serves to clients that have not taken the update.

### 4.4 S81-07m does not fit
ENABLE_ANTHROPIC_MODERATION (LR:59-65) only routes the L3 output-moderation role to a Claude Haiku classifier (content_safety_service.py:251-256 -> LR:1192-1199, :1247-1290). Its prompt (LR:160-167) classifies harassment, hate, self-harm, sexual, violence and illicit content and fails CLOSED; a flag refuses the whole compare as CONTENT_UNAVAILABLE (SCS:5059-5085). A price claim is a truth defect, not a safety category: putting it there would change an owner-reviewed prompt (R-S06-6), add a paid call per compare, refuse whole comparisons instead of dropping one sentence, and act only while the moderation role routes to Claude.

### 4.5 Rows, strings, scope, limits
Rows: none in INC-C1b (INC-RT1 owns SV-A1..A5 and P-SV-A). Strings: none. Scope of the claim (RU-11): B-a closes only for what INC-RT1 covers (the widened English price words, and an Arabic list after a native read, A.1); stored History rows keep their prose (L9). Data-lane touch: O2 / O3 / D1 left Imagination unpriced (the trigger).

## 5. B-b: equal values are never a win and draw equal bars

### 5.1 What the screens show (measured on the owner's screens, 921 px wide, the bar's mid line)
| bar (caption) | A px | B px | A share | reading |
|---|---|---|---|---|
| Character ("More distinctive") | 475 | 373 | 0.560 | spec signal, both real |
| Longevity ("8h vs 8h") | 434 | 414 | 0.512 | spec_secondary: A spec only (no reviews), B 0.6 spec + 0.4 x 88 |
| Projection ("Heavy vs Heavy projection") | 307 | 541 | 0.362 | 50 / (50 + 88) = 0.362: A = MISSING_SCORE 50, B = review 4.4 -> 88 |
| Versatility ("More versatile") | 385 | 463 | 0.454 | 50 / (50 + 60) = 0.455 |
| Presentation ("Better presented") | 282 | 565 | 0.333 | 50 / (50 + 100) = 0.333 |

The review re-measured the five bars to +-1 px. LIKELY (three A shares equal the 50 sentinel to 0.1 %): Imagination men had no review, reliability or popularity signal, so those three dims were one-sided missing and the server sent `winner: null` for them (SS:3226-3227). Solving Character and Longevity together gives A about 72.9 and B about 69.5 for longevity, a margin of about 3.4, so the server LIKELY sent `winner: 0` for longevity. The relay's read of the stored row would make both ESTABLISHED (Q2, optional: the RED rows are hermetic with the measured numbers). The bridge's "Longevity a little under half" is wrong (51.2 %, RU-6).

### 5.2 Producers
- Server, the scores: SS:2175-2179 maps fragrance `longevity_score` to spec_secondary and `projection_score` to the review signal; SS:2339-2352 spec_secondary = 0.6 spec + 0.4 review (spec alone when reviews are missing); the F4.1 reconcile (SS:2411-2445) swaps only when the hours differ by at least 1 h, so equal hours keep the unequal composite. `_dim_winner` (SS:3192-3237) returns None for a one-sided-missing dim or a margin under 3.0, else the larger score. The caption is computed from the specs and ignores the scores: SS:3667 `f"{int(max(ha, hb))}h vs {int(min(ha, hb))}h"`, SS:3676 `f"{sa} vs {sb} projection"`.
- Client, the win: RunnerUpWinsCard.tsx:50-63 lists a dim when `sr > sw` and never reads `winner`. DimensionBars.tsx:263-269 uses `winner` only when it is 0 or 1 and otherwise compares scores ("Ties go to overall winner"), so the server's `winner: null` (Decision B, or a tie under 3 points) is painted as a win (:302-306) and the value / price hero delta takes the accent (:280-282).
- So: Projection, Versatility and Presentation: the server says no winner, and the client paints one. Longevity: the server itself LIKELY crowns A on a composite that ignores the equal hours, and the client follows. "+ 8h vs 8h": both.

### 5.3 Fix, client part (IN; the RU-2 design replaces V1's equal halves)
1. DimensionBars DimensionRow: `const noWinner = dimension.winner === null;` (an explicit null only; undefined is a row saved before F2.4 and keeps today's rule). When noWinner: `winnerSide` null (no accent on either fill: :302-306 -> DimensionBar.tsx:53-54 paints both text.secondary) and `heroDeltaColor` text.primary (:280-282). DimensionBar keeps `left={Math.max(1, score_a)}` and `right={Math.max(1, score_b)}` (:325-327): PROPORTIONS UNCHANGED, no forced equal halves (RU-2). The hidden score hooks (:350-361) keep the raw scores; the cross-tier rule is unchanged.
2. RunnerUpWinsCard `runnerUpWinningDims` (:50-63), after the numeric-pair check: `if (d.winner === null) return false; if (d.winner === 0 || d.winner === 1) return d.winner === runnerUp;` else today's `sr > sw`. The header comment (:12-16) says that rows follow the server's per-dim winner when one is sent and the score comparison only for rows without it (RU-15).
3. Captions stay the server's.

Why the proportions stay (RU-2): equal halves would assert an equality nobody measured, would hide the server's 50 sentinel instead of removing it, and would add caption-versus-bar and line1-versus-bar contradictions on the owner's own case (review R-1: "More versatile", "Better presented" and "Creed Aventus leads on Presentation." over equal halves). Proportional bars without the win colour keep every caption and line1 pointing at the longer bar while no longer crowning a side the server did not crown.

### 5.4 Server part (INC-RT1)
SD-B (Appendix A.2, RU-3): (i) equal shown facts make a tie (equal scores, `winner` None), both ends of an hour range compared; (ii) the factual verdict ranks only dims that have a winner; (iii) a one-sided-missing category dim ships `caption_key: 'limited_data'`, so every client, old or updated, hides it; no sentinel averaging.

### 5.5 Rows, strings, risk, limits
Section 10.3 (B1-B5, P-B1, P-B2, P-B3). Strings: none. Risk: every winner-null bar on every result, live and stored since F2.4, loses its win colour and its runner-up row, sub-3-point ties included; that is the server's own verdict; lengths do not move. A `winner` 0 or 1 that disagrees with the raw scores (the value dim's cross-tier framing) now decides the runner-up list as it already decides the paint. History rows without `winner` keep today's paint and list. Limits L4, L5, L6, L13.

## 6. B-c: size is never marked as a win (server, INC-RT1)

### 6.1 Producer (server)
RB:2166-2173 ships `specs.specs_comparison.rows` from `_build_specs_rows` (RB:885-922). Each row's winner comes from `_spec_row_winner` (RB:823-861): when both values are numeric, the larger wins unless the field is in `_SPEC_SMALLER_WINS` (RB:765-773). Volume "100 ml" vs "50 ml" -> 0. The client only paints winner 0 or 1 (ResultsAccordion.tsx:228-238, :605-615); it computes nothing.

### 6.2 Root cause
The per-row winner treats a pack size as a quality.

### 6.3 Fix
Not in INC-C1b (RU-1): INC-RT1's SD-C (Appendix A.3), whose field list also takes count and net weight (RU-14 Q4; ES:1092 already treats volume, unit count and net weight as a basis). No client guard (RU-14 Q3): stored History bodies and old servers keep the size paint (L9).

### 6.4 Rows, strings, limits
Rows: none in INC-C1b (INC-RT1 owns SV-C1..C3 and P-SV-C). Strings: none. Limit L9. Data-lane touch: O1 wants the Volume row to agree with the priced size or to mark the priced size; that mark must not be the accent win paint.

## 7. B-d: ratings and counts per product; the header never spreads one side over both

### 7.1 Producer (client)
- ResultsAccordion.tsx:170-174 `totalReviews = reviewSrc.reduce((acc, p) => acc + (p.review_count ?? 0), 0)`.
- :178-196 averages the rated products only, weighted by review_count.
- :267-276 sub = avg + `t('results.accordion.reviewsAvg')` + " [B7] " + formatNumber(total) + " " + `t('results.accordion.reviewsSub')` ("reviews across both").
- With one side rated, the other side's absence vanishes: 5,600 + 0 "across both", and 4.4 weighted by 5,600 / 5,600. The per-product body (:401-466, ReviewPraiseBlock :678-737) is already right.

### 7.2 Fix
- N = reviewSrc.length; R = products whose rating is a number > 0; C = products whose review_count is a number > 0; `oneSided = N >= 2 && ((R > 0 && R < N) || (C > 0 && C < N))`.
- oneSided: sub = `t('results.accordion.reviewsEach')` (row 2, "Shown per product" as ruled in RU-10), with no figure.
- Otherwise today's expression, byte for byte: with both rated and counted, the weighted average and the total really cover both; with neither, the bare phrase; with counts only or ratings only on both sides, today's line.

### 7.3 Rows, strings, risk, limits
Section 10.4 (D1-D3, P-D1..P-D3). String row 2. Risk: none beyond the one-sided header. Limit L7, with the owner's question Q11. Data-lane touch: B-e / O3 (identity); once Imagination resolves to the Louis Vuitton product with reviews, both sides carry figures and today's header returns.

## 8. B-f: the label CONCENTRATION fits on one line or breaks at a sensible place (RU-5, RU-6)

### 8.1 Producer (client)
ResultsAccordion.tsx:637-639: the label Text (`style={styles.specsCellKey}`, text = t of 'results.spec.' + key with the key as defaultValue) sets no line rule. :922-930 sets width 96, fontSize 11, fontWeight 500, uppercase, letterSpacing 0.4, centred. "CONCENTRATION" needs about 100-109 pt at 11 pt (screen 5: "CONCENTRATI" spans 198 of 921 px), more than the 96-pt column, and a single word wider than its box wraps at a character. On screen 5 only SCENT FAMILY wraps, at its space; TOP NOTES, HEART NOTES and BASE NOTES fit on one line (RU-6).

### 8.2 Fix
- label = the same `t(...)`; `oneWord = !/\s/.test(String(label).trim())`.
- oneWord: `numberOfLines={1}`, `adjustsFontSizeToFit`, `minimumFontScale={0.85}` (RU-5). Precedent: StatBlock.tsx:42-48, an 11-pt uppercase eyebrow whose 0.85 floor "never drops below caption tier", device-walked. CONCENTRATION needs a scale of only about 0.88-0.96.
- Several words: unchanged (they break at a space). Column width and style unchanged, so the table stays aligned. The specs header's empty middle cell (the label-styled Text between the two product names, ResultsAccordion.tsx:567) is not a label and takes no rule.
- AR: the Concentration label [627 644 62A 631 643 64A 632] is one word and takes the same rule; the Scent family label [639 627 626 644 629 20 627 644 639 637 631] wraps at the space.

### 8.3 Rows, strings, risk, limits
Section 10.5 (F1, F2, P-F1, P-F2). Strings: none. Risk: a one-word label now shrinks (to 0.85 at most) instead of wrapping (a no-op at default sizes for the short ones). Limit L8. Moved pin: the accordion snapshot (11.1).

## 9. Strings (OWNER READ; RU-10)

EN is literal. AR is quoted ASCII plus bracketed hex code points (U+ and leading zeros dropped; 20 space), decoded with String.fromCodePoint. INC_C1B_STRINGS.json beside this file is a machine copy (written by a script from the same words, its code points asserted against this table, json ensure_ascii); the table rules. Both rows are new keys; no value changes.

| # | key | EN | AR (code points) | read |
|---|---|---|---|---|
| 1 | `results.savedOn` | Saved on {{date}} | [645 62D 641 648 638 629 20 628 62A 627 631 64A 62E 20] "{{date}}" | [NATIVE READ]; the year in the date is accepted (RU-10) |
| 2 | `results.accordion.reviewsEach` | Shown per product | [645 639 631 648 636 629 20 644 643 644 20 645 646 62A 62C] | [NATIVE READ], the primary (RU-10) |
| 2-alt | `results.accordion.reviewsEach` | For each product separately | [644 643 644 20 645 646 62A 62C 20 639 644 649 20 62D 62F 629] | the alternative for the owner's read (V1's row 2) |

Row 1 follows results.price.listedOn's AR [645 639 631 648 636 20 628 62A 627 631 64A 62E] "{{date}}" (its last word is the same); [645 62D 641 648 638 629] is feminine (the comparison) and is already in common.offline, aiConsent.body and legal.offline.banner.

Row 2 (RU-10) uses the owner's own case words (case row B-d: "Ratings and counts are shown per product"). AR cross-check against ar.json: [645 639 631 648 636] is the first word of results.price.listedOn and listedOnNoStore (masculine); the [629] ending makes it feminine to agree with the section label results.reviews [627 644 62A 642 64A 64A 645 627 62A] (a plural of things takes a feminine singular adjective); [644 643 644 20 645 646 62A 62C] is in loading.tip.cross_checks and results.tips.retailers. The alternative: [644 643 644 20 645 646 62A 62C] as above; [639 644 649] is in 32 keys (e.g. results.valueMatch.above_range); [62D 62F 629] appears in ar.json only inside other words (as in [648 627 62D 62F 629]), never as this word. The primary sits beside results.accordion.prosConsSub "Each product, both sides" (en.json:802) without repeating it (review R-8). If the owner picks the alternative, the gate changes the two catalog values and the one ROW2 constant in reviewsHeader.c1b and strings.c1b, nothing else.

Both rows pass .copy-policy.json (no banned or scary word), carry equal {{vars}} in EN and AR ({{date}} / none), no digit, no plural suffix and no time promise.

## 10. Test rows (RED fails at base on an expect assertion; a pin passes at base and after)

### 10.0 Rules
- New files in SmartCompareApp/__tests__/c1b/ (the RED byte copy: c1b/red/SmartCompareApp/__tests__/c1b/, with c1b/red/MANIFEST.md), ASCII sources, Arabic built with String.fromCodePoint from section 9 and 8.2.
- F1 carried: observe only through surfaces that exist at base: renders of ProductImage, ResultsContent, ResultsScreen, ResultsAccordion, DimensionBars, RunnerUpWinsCard; the existing exports runnerUpWinningDims and getComparison (the real api.ts through jest.requireActual). No import of a new symbol (addImageLoadBreadcrumb and formatSavedOnDate stay unimported); jest.mock only existing paths (@sentry/react-native, react-i18next, react-native-reanimated, axios, expo-localization, services/api, services/certificatePinning, services/authService, services/demographicsTrigger, hooks/useLanguage, lib/performance/wallTimeInstrumentation, and the c1a component mocks); new elements are queried with queryBy* + expect, and a node that may be absent at base is fired only when present, so no getBy* throws before the RED assertion; tsc stays at 0 errors at base (Dimension.winner already admits null; getComparison returns any).
- Each RED row ends in one expect over an object, so the base diff names exactly what is missing (for example `savedOn: false` next to `content: true`).
- Real catalogs through an i18next instance (the referralExpiryPlurals / c1 lastChecked pattern, mockLang per render) for T7-11, B-d and B-f; B-b uses a passthrough t. Dates at 12:00Z, so CI (UTC) and the box (UTC+3) agree. T7-09 and S3 use fake timers.
- RU-8: `mockAddBreadcrumb.mockClear()` in beforeEach (jest.config.js sets no clearMocks); each T7-09 row uses its own host (the de-dup is module state).
- Models: ProductImage.test.tsx, c1a/sizeLabel.c1a (ResultsContent harness), c1/lastChecked.c1 (real i18next), c1/strings.c1, api.getComparison.comparisonId.m18 (axios mock), ResultsScreen.historyFloor.a17 (History path), components/RunnerUpWinsCard.test.tsx, components/DimensionBars.test.tsx, components/ResultsAccordion.render.test.tsx.

### 10.1 productImage.c1b.test.tsx (T7-09)
Harness: `jest.mock('@sentry/react-native', ...)` = the global stub's surface with `addBreadcrumb: (...a) => mockAddBreadcrumb(...a)`; services/sentry real; `jest.useFakeTimers()` in beforeEach; `act` around every timer advance.
- I1 RED: img1; fire 'error' on pi-img; advance 1,499 ms: pi-placeholder, no pi-img (passes at base); advance 1 ms: pi-img with source.uri the same url, no placeholder. Base: FAIL (retryUri null).
- I2 RED: img2; error, advance 1,500: the retry pi-img is present (asserted before firing); fire 'error' on it; after 10,000 ms still placeholder, no pi-img; mockAddBreadcrumb called once with exactly {category: 'image', level: 'warning', message: 'product image did not load after one retry', data: {host: 'img2.example.com'}}; the serialised calls hold no '/p/', 'sig=', '.jpg' or 'https'. Base: FAIL (no retry pi-img).
- I3 RED: img3; one error, advance 1,500: pi-img with the url; after another 10,000 ms still pi-img and zero breadcrumbs. Base: FAIL (no retry pi-img).
- I4 RED: (a) error on url A (img4), rerender with url B at 500 ms: pi-img with B at once; advance 1,500 (past A's due time): one pi-img, uri B; fire 'error' on B: placeholder; advance 1,500: pi-img with B again. (b) rerender with C after B's retry was used: pi-img C; one error; advance 1,500: pi-img with C again. Base: FAIL (B is not retried).
- I5 RED: three images in one tree, pa and pb on img5, pc on img6, each failing twice: hosts recorded ['img5.example.com', 'img6.example.com']. Base: FAIL ([]).
- I6 RED (RU-7): 'https://u:secret@IMG7.Example.COM:8443/p/a.jpg?sig=x' and 'data:image/png;base64,AAAA', each failing twice: hosts ['img7.example.com', 'unknown']; the serialised calls hold no 'secret', 'u:', '8443', 'IMG7', 'Example', 'base64', 'AAAA' or 'data:image'. Base: FAIL (no retry pi-img).
- I7 RED (RU-8): img8; two onError calls in one act (before React re-renders): the pending fake timers (`jest.getTimerCount()` read after `jest.runAllTicks()`, so queued microtask jobs never count) rise by exactly 1 and the placeholder shows; after 1,500 ms the retry pi-img with the url and no timer left. img9: one error raises the count by 1; an unmount brings it back to the start. Base: FAIL (the count rises by 0).
- P-I1 pin: right after the first error the placeholder shows with placeholderTone '#FFEAD4' and pi-img is gone (the state-4 contract of ProductImage.test.tsx:88-109 under fake timers). Base: PASS.
- Mutants: no retry (I1); retry at once (I1 at 1,499 ms); a second retry (I2); full url or extra keys in the breadcrumb (I2); breadcrumb at the first error (I3); timer not cleared on url change, attempt not reset on url change (I4); no de-dup (I5); user info kept, port kept, no lower-casing, a data: uri read as a host (I6); no pending-timer guard, no clear on unmount (I7).

### 10.2 savedOn.c1b.test.tsx (T7-11)
Harness: getComparison through the real api.ts (`jest.requireActual`, loaded on first use) with axios mocked (m18 pattern); ResultsContent with the c1 lastChecked harness; ResultsScreen with services/api mocked and fake timers (a17 pattern).
- S1 RED: wrapper.comparison {id, full_response, created_at '2026-11-22T12:00:00.000000+00:00'} -> payload.saved_at equals that string and comparison_id is the id; the same without an id -> saved_at set and no comparison_id key (RU-9). Base: FAIL (saved_at undefined).
- S2 RED: ResultsContent, resultOrigin 'stored', result.saved_at as in S1: EN `results-saved-on` reads "Saved on Nov 22, 2026" and its testID sits after results-content-header and before results-content-hero-pair; AR: present, starts with row 1's AR prefix [645 62D 641 648 638 629 20 628 62A 627 631 64A 62E 20], contains "22" and "2026", no Arabic-Indic digit (U+0660-0669, U+06F0-06F9) and no ASCII letter. Base: FAIL (no element).
- S3 RED: ResultsScreen with route.params.comparison_id and getComparison resolving {...stored body, comparison_id, saved_at}: the screen mounts into results-loading-state, fetches the id once, renders results-content and `results-saved-on`. Base: FAIL (savedOn false while content is true).
- P-S1 pin: no saved_at key when created_at is missing, a number or 'not-a-date', each with and without an id; comparison_id is the id exactly when one is sent; the 404 contract (missing full_response) stands. Base: PASS.
- P-S2 pin: no `results-saved-on` on a live result with saved_at, on a result without resultOrigin, on a stored result without saved_at or with 'not-a-date' (results-content present in each). Base: PASS.
- Mutants: saved_at from metadata.timestamp, or only with an id (S1); the line on a live result or without an origin (P-S2); no year (S2); device-locale digits in AR (S2); the line placed below the hero pair (S2); saved_at from any string (P-S1, 'not-a-date').

### 10.3 dimensionTruth.c1b.test.tsx (B-b client; RU-2)
Harness: DimensionBars and RunnerUpWinsCard real; ResultsContent with the c1a harness minus its DimensionBars mock; `colors` from src/theme; a passthrough t. A bar reads as {aAccent, bAccent, aShare, bShare}, the shares to one decimal from flexBasis.
- B1 RED: `runnerUpWinningDims([longevity {71.5, 70.0, '8h vs 8h', winner null}, character {72.9, 57.2, 'More distinctive', winner 0}], 1)` -> ['character'], and the card renders `runner-up-wins-dim-character` but no `runner-up-wins-dim-longevity`; with winnerIndex 0, a dim the server gave to A {70, 80, winner 0} is not listed and one it gave to B {80, 70, winner 1} is. Base: FAIL (['longevity', 'character']; ['value']; []).
- B2 RED: DimensionBars [projection {50, 88, 'Heavy vs Heavy projection', winner null}], winnerIndex 1 -> {aAccent false, bAccent false, aShare 36.2, bShare 63.8}. Base: FAIL (bAccent true).
- B3 RED: [longevity {71.2, 71.2, '8h vs 8h', winner null}], winnerIndex 1 -> no accent, 50 / 50. Base: FAIL (the tie paints the overall winner's side).
- B4 RED: ResultsContent with the case dims (price, reviews, value limited_data; character 72.9/57.2 w0; longevity 72.9/69.5 w0; projection 50/88 null; versatility 50/60 null; presentation 50/100 null), Imagination men's price pending, winnerIndex 1; press results-v2-bars-expand-row: projection {no accent, 36.2 / 63.8}, versatility {no accent, 45.5 / 54.5}, presentation {no accent, 33.3 / 66.7}. Base: FAIL (bAccent true on all three).
- B5 RED: [value {82, 70, 'BHD 2 less', winner null}], winnerIndex 0: bars-row-value-delta-hero colour colors.text.primary and the bar {no accent, 53.9 / 46.1}. Base: FAIL (accent).
- P-B1 pin: character w0 and the case's longevity w0 at winnerIndex 1 keep the fill-a accent and their shares (56.0 / 44.0, 51.2 / 48.8); the case's longevity is still a runner-up row (L4; SD-B owns equal facts). Base: PASS.
- P-B2 pin: dims without `winner` keep the score rule (battery 80/70 paints A at winnerIndex 1; a 75/75 tie paints B at winnerIndex 1 and A at 0); the card list for dims without `winner` is today's ['comfort', 'value'] (a limited_data placeholder excluded). Base: PASS.
- P-B3 pin (RU-2): projection, versatility and presentation with winner null keep their shares [36.2, 63.8], [45.5, 54.5], [33.3, 66.7]. Base: PASS.
- Mutants: null still painted by score (B2, B3, B4); hero delta accent on null (B5); runner-up list ignores null, or ignores 0 / 1 (B1); neutral also for winner 0 / 1 (P-B1); undefined read as null (P-B2); forced equal halves (P-B3, B2, B4).

### 10.4 reviewsHeader.c1b.test.tsx (B-d)
Harness: ResultsAccordion real; react-i18next -> an i18next instance over the real catalogs (EN, AR). D1-D3, P-D1 and P-D2 read the header sub (the second Text under results-accordion-toggle-reviews) with the section closed, so no body text can match.
- D1 RED: reviewProducts [Imagination men {rating null, review_count 0, praise}, Creed Aventus {rating 4.4, review_count 5600, praise}], EN and AR: the sub equals row 2 and holds neither '5,600', '4.4' nor the reviewsSub words. Base: FAIL ("4.4[2605] avg [B7] 5,600 reviews across both").
- D2 RED: one rated, both counted (Imagination men null / 1,200; Creed Aventus 4.4 / 5,600) -> row 2 (EN, AR). Base: FAIL ("4.4[2605] avg [B7] 6,800 reviews across both").
- D3 RED: both rated, one counted (Imagination men 4.1 / null; Creed Aventus 4.4 / 5,600) -> row 2 (EN, AR). Base: FAIL ("4.4[2605] avg [B7] 5,600 reviews across both").
- P-D1 pin: both rated and counted (4.4 / 520; 4.6 / 720): EN "4.5[2605] avg [B7] 1,240 reviews across both"; AR "4.5" + [2605 20 645 62A 648 633 637] + " [B7] 1,240 " + [622 631 627 621 20 645 646 20 643 644 627 20 627 644 645 646 62A 62C 64A 646]. Base: PASS.
- P-D2 pin: none rated and none counted -> the bare reviewsSub; both counted, none rated (null / 1,200; null / 5,600) -> "6,800 " + reviewsSub; both rated, none counted (4.4; 4.2) -> "4.3" + reviewsAvg + " [B7] " + reviewsSub; EN and AR. Base: PASS.
- P-D3 pin: the D1 body (toggle open, overall winner Creed Aventus): the Creed Aventus block reads ["Creed Aventus", "4.4 [B7] 5,600 reviews", its praise]; the Imagination men block [name, its praise], no rating line. Base: PASS.
- Mutants: aggregate kept one-sided (D1); row 2 also when both are full (P-D1); the counts-only or ratings-only case moved to row 2 (P-D2); the C-side test dropped (D3); the R-side test dropped (D2); the body touched (P-D3).

### 10.5 specLabel.c1b.test.tsx (B-f)
Harness: as 10.4; specsProducts [{concentration 'EDP', scent_family 'Citrus aromatic'}, {concentration 'EDP', scent_family 'Woody'}]; press results-specs-toggle.
- F1 RED: EN label node 'Concentration': numberOfLines 1, adjustsFontSizeToFit true, minimumFontScale 0.85. Base: FAIL (all undefined).
- F2 RED: AR label node [627 644 62A 631 643 64A 632]: the same props. Base: FAIL.
- P-F1 pin: 'Scent family' (EN) and [639 627 626 644 629 20 627 644 639 637 631] (AR) carry no numberOfLines, adjustsFontSizeToFit or minimumFontScale; the one empty label-styled Text (the header's middle cell) carries none. Base: PASS.
- P-F2 pin: the label style flattens to exactly {width 96, fontSize 11, fontWeight '500', color text.secondary, textAlign 'center', textTransform 'uppercase', letterSpacing 0.4} (EN, AR). Base: PASS.
- Mutants: the rule on multi-word labels or on the header cell (P-F1); one line without shrink, or the floor 0.7 (F1, F2); a widened column or an extra style (P-F2).

### 10.6 strings.c1b.test.ts
- T1 RED: the two keys equal section 9 rows 1 and 2 (EN literal, AR decoded) in en.json / ar.json. Base: FAIL (missing).
- T2 RED: control (both keys non-empty in both catalogs) plus property: no digit (ASCII, U+0660-0669, U+06F0-06F9), EN not /update|soon|shortly|next|minute|hour/i, AR without the three INC-C1 time words, no plural suffix, {{vars}} equal to ['date'] / [] in EN and AR, an Arabic letter in AR, no .copy-policy.json hit. Base: FAIL (the control).
- P-T1 pin: EN and AR key sets equal. Base: PASS.

Totals: RED 22 (I 7, S 3, B 5, D 3, F 2, T 2); pins 12 (P-I1, P-S1, P-S2, P-B1, P-B2, P-B3, P-D1, P-D2, P-D3, P-F1, P-F2, P-T1); 34 tests in 6 files, plus every existing suite named in 11.2.

## 11. Moved pins, GREEN comm set, bundle rule, acceptance walk

### 11.1 Moved pins (quote each, never weaken; any other failure is a finding)
- tests/test_s81_12_legal_v3.py:242 `BASE_I18N_KEY_COUNT = 1038` -> 1040; :243 `BASE_I18N_NAMESET_SHA256` "8e8b2a2c07848340d557cd70d34ee954bb4dcb3d04fb944d364daf77f99077ec" -> "53bb907f581a61c8e52f3b35648af4673ff36c15c8d24d4f5ffaa2c15c515c6a" (sha256 of the 1,040 sorted names joined by newline, recomputed for V2 on the base catalogs plus the two keys; RU-10 moved words, not names; keep the split-literal form, the constant name already passed gitleaks). Add under :241 "INC-C1b (2026-11-2x) re-recorded: + results.savedOn, results.accordion.reviewsEach; the other 1,038 names still hash to INC-C1's 8e8b2a2c... (CC-8)", and prove that claim at GREEN.
- SmartCompareApp/__tests__/s11/copy.s11.test.tsx:192 `... + 3 + 24` -> `... + 3 + 24 + 2` (1,038 -> 1,040); comment :191 "INC-C1b adds 2 keys (1,040 leaves)".
- SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts:141 `{ ar: 1038, en: 1038 }` -> `{ ar: 1040, en: 1040 }`; comment :140.
- SmartCompareApp/__tests__/components/__snapshots__/ResultsAccordion.edgeCases.test.tsx.snap: the three one-word label nodes ('display', 'battery', 'storage') gain `adjustsFontSizeToFit={true}`, `minimumFontScale={0.85}`, `numberOfLines={1}` (RU-5); the header's empty middle cell and the reviews header (both sides without rating or count there: the bare phrase) do not move. Re-record that file only and show the diff.
- Expected to stay green (checked at base): ProductImage.test.tsx (the placeholder shows at once; the url-change row clears the timer), ResultsContent.imageUrl / SmartPickCard.imageUrl / HistoryScreen.imageUrl error rows, ResultsAccordion.render (both-rated aggregate; the bare fallback), ResultsAccordion.digitPolicy.w311, .v2 and perCategory (every v2 fixture is rated and counted on both sides; v2's sparse row asserts the body only), DimensionBars and RunnerUpWinsCard suites (no test dim has `winner: null` apart from limited_data placeholders, which are dropped; no v2 fixture has a winner-null dim, probed again for V2), ResultsContent.rewriteOrder (relative order of the existing anchors only), api.getComparison.comparisonId.m18 (no whole-payload equality), the c1 P2 global pin (no plural family; equal vars).

### 11.2 GREEN comm set
- Client: the full suite in one process (`npx jest --ci --runInBand`; only the 4 accepted nativeBundle.w37 nodes may fail); each c1b file paired --runInBand both orders with ProductImage.test.tsx and components/ResultsAccordion.render.test.tsx (module state in sentry.ts); `tsc --noEmit` 0 errors; eslint on the changed files and CI's `eslint 'src/**/*.{ts,tsx}'` (0 errors, no new warning).
- Backend (no app/ change in INC-C1b): every `.py` hit of `git grep -l SmartCompareApp -- tests/` at the GREEN head in one pyt.py run, waiting outside the runner. Readers of this unit's files: test_s81_12_legal_v3 (moved), test_s81_12_gate_rows, test_dimension_label_catalog_parity_w414, test_register_benefits_parity_s69, test_legal_docs_u8* (catalogs); test_inc_sec1_app_user_access, test_security_regression, test_migration_037_security_definer_grants (src scans); test_timeout_partial_integration (the copy-policy mirror); and the three of RU-13, read for V2:
  - tests/test_comparison_id_echo.py: names api.ts:413 and types.ts:289 only in its docstring and assert messages; it reads no client file and drives the server routes. HOLDS (api.ts's return expression changes; nothing reads it).
  - tests/test_events_allowlist_superset.py: rglob over SmartCompareApp/src/*.ts* (production files) for literal event types in `trackEvent('x'`, `fireEvent('x'`, `fireAnalytics('x'` and `event_type: 'x'`, each asserted in VALID_EVENT_TYPES. INC-C1b adds none: the new signal is a Sentry breadcrumb (category 'image'), not an /events type. HOLDS, as long as the GREEN writes no such literal (2.2 step 2).
  - tests/test_s81_sf1_surfaces_be.py: its only client read (test_p62) counts `trackEvent('category_coming_soon_tap'` over src/*.ts* (once, in HomeScreen.tsx) and reads services/launchSurfaces.ts; its BASE_EVENTS_31 lists "image_load_failed", an allowlisted /events type the client does not fire and INC-C1b does not start firing. HOLDS.
  - Also read for V2: __tests__/bootSentryAlarm.w312 and bootSentryOrder.w312 execute the compiled sentry.ts in their boot sandbox (helpers/w312BootSandbox.ts); the new code adds a function and a module-level Set (no import, no call at load), so they hold; they run in the full suite.
- Class FOCUS (RU-12): the two adversaries run after GREEN on these records.

### 11.3 Bundle rule
`git diff --name-only 7e2e317c <M> -- SmartCompareApp`, minus __tests__, is exactly: src/components/primitives/ProductImage.tsx, src/services/sentry.ts, src/services/api.ts, src/types/types.ts, src/services/fieldStatusView.ts, src/components/results/ResultsContent.tsx, src/components/results/RunnerUpWinsCard.tsx, src/components/results/DimensionBars.tsx, src/components/results/ResultsAccordion.tsx, src/i18n/en.json, src/i18n/ar.json (11). No app.json, package, lock, locales or native change; nothing is published.

### 11.4 Acceptance walk (RU-4)
After INC-RT1's flips (SD-A, SD-B, SD-C on web) and the over-the-air publish that carries INC-C1b, the owner at his phone runs (1) a fresh compare of the case pair "Imagination men" vs "Creed Aventus", and (2) a synthetic equal-facts pair (two fragrances whose listed longevity hours and sillage words are equal), in case the data lane has re-resolved Imagination by then. Expected on (1): no price claim about an unpriced side (B-a), no "+ 8h vs 8h" and equal Longevity bars (B-b), the one-sided dims gone (B-b, SD-B (iii)), no accent on the Volume row (B-c), the Reviews header "Shown per product" while one side is unrated (B-d), CONCENTRATION on one line (B-f); on (2): equal bars and no runner-up row for the equal facts. On the stored 22 Nov History row only these change: T7-11 ("Saved on Nov 22, 2026"), B-d, B-f and the winner-null paint (Projection, Versatility and Presentation lose their green; Longevity stays green and listed, L4); its prose and its volume paint stay (L9). The proof standard is the owner's: fixed = seen on the app.

## 12. Stated limits
- L1 (T7-09) One retry only; a host down for minutes keeps the placeholder. Platform image caches differ; the retry is a fresh mount of the same uri.
- L2 (T7-09) One breadcrumb per host per app session (20 hosts at most), and it reaches Sentry only attached to a later event.
- L3 (T7-11) The date is the phone's local date of created_at, with the year. Only bodies opened by id carry it (History, Home and Profile taps, a `comparison/:comparison_id` deep link, navigation/linking.ts:83); the History list is unchanged.
- L4 (B-b) A server `winner` 0 or 1 at equal shown values (the case's longevity, margin about 3.4) still paints and still lists "+ 8h vs 8h" until INC-RT1's SD-B (i) is on. Stored History rows keep their stored winners and scores.
- L5 (B-b) A winner-null row keeps the server's caption over proportional, uncoloured bars; a comparative caption ("More versatile", "Better presented") still points at the longer bar, so the client adds no contradiction; the row leaves the screen only with SD-B (iii) (RU-3).
- L6 (B-b) With the update live and SD-B (ii) off, the FactualVerdict line can name a dim the bars show without a winner ("Creed Aventus leads on Presentation."); its bar is still the longer one, so line and bar agree on length. SD-B (ii) fixes new rows only: Home SmartPick tiles read the stored line (A.2).
- L7 (B-d) With both sides rated and counted, the header still shows the weighted average and the total "across both" (true, but a blend of two products); whether it goes per product too is the owner's question Q11.
- L8 (B-f) The shrink floor is 0.85 (about 9.4 pt, caption tier, RU-5). Below it (very large accessibility text) iOS truncates with an ellipsis instead of breaking; minimumFontScale is iOS-only, so Android shrinks by its own rule. Device check: the owner's walk.
- L9 (B-a, B-c) No client change: both need INC-RT1 and its flips. Stored History rows keep their prose and their volume paint (RU-14 Q3).
- L10 The case also needs the data lane: Imagination's missing signals (O3 / B-e) make the sentinel bars and the one-sided reviews; O1 the Volume / price size.
- L11 ENABLE_LISTING_MATCH_GUARD touches no item; it can only pend more prices (more SD-A triggers).
- L12 Moved to Appendix A.1 (SD-A's Arabic coverage is INC-RT1's, RU-11).
- L13 (B-b) Winner-null bars still draw the server's scores, the 50 sentinel included (the case's three one-sided dims), until SD-B (iii) sends them as limited_data; the client no longer colours them, it does not hide them.

## 13. Server dependencies
Moved to Appendix A (RU-1). INC-C1b builds and tests none of it.

## 14. Open questions
Answered by the rulings: Q1 (RU-1, the sibling server unit INC-RT1), Q3 (RU-14, no client size guard), Q4 (RU-14, count and net weight join SD-C), Q5 (RU-3, SD-B (iii) limited_data), Q6 (RU-2, no publish coupling), Q7 (RU-12, FOCUS), Q8 (RU-10, the year accepted; the words still owe the native read, Q12).
Open:
- Q2 (relay, optional, read-only) The stored comparisons row of 22 Nov 2026 00:24-00:25Z for the owner's account: scoring_v2.dimensions (key, score_a, score_b, winner, delta_text), overview.winner.key_tradeoff, specs.specs_comparison.rows (volume), reviews.products (rating, review_count), products[0].price.unavailable. It turns 5.1's LIKELY into ESTABLISHED; the RED rows do not wait for it.
- Q9 (relay) Are INC-C1a's and INC-C1's bytes already on the phones? The bundle list from 7e2e317c names only INC-C1b's files.
- Q10 (relay) Is the Arabic verdict output on for web? It sizes INC-RT1's SD-A (A.1).
- Q11 (owner, RU-10) With both sides rated and counted, does the blended "avg ... across both" header stay (today, L7) or go per product too?
- Q12 (owner, [NATIVE READ]) Row 1's words, and row 2's: the primary "Shown per product" or the alternative "For each product separately" (section 9).
- Relay at the gate: INC-RT1 and its place in the queue.

## Appendix A. For INC-RT1 (sibling server unit, not built here)
V1's section 13, condensed, with RU-3, RU-11, RU-14 (Q4) and RU-15. Proposed to the relay at the gate; it needs the relay's word. Switches are read per call (house idiom `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")`), default off, so production is byte-identical until the owner flips each one. Hermetic backend rows in one new file (working name tests/test_inc_rt1_result_truth.py). The comm set includes the fourteen client jest fences that read repo files (the backend-unit rule), the existing tests of the functions touched (grep tests/ for `_spec_row_winner`, `build_dimensions_v2`, `_build_factual_verdict`, `_top_dim_candidate`, `_leaks_price_adjective`), and each switch added wherever the house lists flags. The names below are free at 7e2e317c.

### A.1 SD-A (B-a): ENABLE_VERDICT_PRICE_CLAIM_GUARD
- RB: `strip_price_claims(text) -> str` beside `_leaks_price_adjective` (RB:803-807): drop each sentence (split as text_sanitize's `_SENT_SPLIT`) that the price-claim pattern matches; "" when every sentence leaks.
- Pattern (RU-11): `_PRICE_ADJECTIVE_RE` (RB:795-800) widened for this use with "better value", "costs less", "lower cost", "less money", "bargain", "pocket-friendly"; an Arabic price-claim list, with a native read, before the unit claims B-a for Arabic output (the ARABIC_VERDICT_OUTPUT directive, ES:2661-2662; Q10). The B-a claim is scoped to what the unit covers.
- RB build_comparison_response, after the C3 block (RB:2028) and the winner-text locals (RB:2035-2045): with the switch on and any product whose price is not shown (shown = a dict whose `unavailable` is not True and whose `amount` is a finite number): `_scrubbed_tradeoff = strip_price_claims(_scrubbed_tradeoff)`; `_scrubbed_reason = strip_price_claims(_scrubbed_reason) or _QUALITATIVE_WINNER_REASON(_winner_name)`. These locals feed overview.winner (RB:2097-2098), the BC alias (RB:2441-2443), recommendation (RB:2453) and the stored row. Not in scrub_verdict_prose (RB:506-566): it sees no prices, and phones never stream.
- Rows: SV-A1 (the case sentence with product 0 unpriced -> key_tradeoff "" and the alias ""), SV-A2 (two sentences, the price one dropped), SV-A3 (winner_reason "Creed Aventus is cheaper and lasts longer." with product 0 unpriced -> the qualitative fallback), SV-A4 (each widened English phrase dropped), SV-A5 (the Arabic list, after the read); P-SV-A (switch off byte-identical; both priced unchanged; no price word unchanged).
- Risk: fail-closed; a true sentence about the priced side's own price also drops while the other side is unpriced.

### A.2 SD-B (B-b): ENABLE_DIM_WINNER_TRUTH
- (i) SS build_dimensions_v2, category loop (SS:3889-3903), switch on, dim "longevity" or "projection" with both scores real and the shown facts equal: `score_a = score_b = round((a + b) / 2, 1)`, so `_dim_winner` returns None and the captions stay. Equal facts: longevity = both hour ranges parsed with BOTH ends and equal at both ends after the caption's own truncation (RU-3: `_extract_hours` takes the first number only, SS:3811-3813, so "8 hours" vs "8-10 hours" would read as a tie while the Specs table shows different facts); projection = both sillage (or projection) strings present and equal after strip().lower() (SS:3673-3676). Only two real scores are equalised; a sentinel side goes through (iii).
- (ii) RB `_top_dim_candidate` (RB:1070-1100) and `_runner_up_dim_candidate` (RB:1103-1129), switch on: skip a dim whose "winner" is None (set before `_build_factual_verdict`, RB:1459-1464). In the case, line1 no longer names Presentation; line2 stays "Imagination men pulls ahead on Character." Home SmartPick reads the stored `factual_verdict.line1` (home_routes.py:673-693, under ENABLE_SMART_PICK_VERDICT_CAPTION), so (ii) fixes new rows only (RU-15).
- (iii) (RU-3) a category dim with one side's signal missing (`_signal_missing_for`, SS:318-334; Decision B, SS:3226-3227) ships `caption_key: 'limited_data'`, so every client, old or updated, hides it (DimensionBars drops it, RunnerUpWinsCard excludes it); the 50 sentinel is never averaged with a real score.
- Overall-score limit (RU-3): (i) changes the displayed dims only; the overall score still counts the composite longevity gap of about 3.4 on a dim the owner's priority chip can weight up (screen 1: "[2191] longevity").
- Rows: SV-B1 (longevity "8-10 hours" on both, 72.9 / 69.5 -> 71.2 / 71.2, winner None, delta "8h vs 8h"), SV-B1b ("8 hours" vs "8-10 hours" -> unchanged), SV-B2 (sillage "Heavy" on both, two real scores -> equal, winner None), SV-B3 (`_build_factual_verdict` with presentation winner None -> line1 does not name it), SV-B4 (the case's versatility / presentation with product_0 missing -> limited_data, and no line names them); P-SV-B (switch off byte-identical; 6 vs 10 h unchanged; "Heavy" vs "Moderate" unchanged).

### A.3 SD-C (B-c): ENABLE_SPEC_SIZE_NO_WINNER
- RB `_spec_row_winner` (RB:823-861), first statement: with the switch on and `field.lower()` in `_SPEC_SIZE_FIELDS` -> None (a neutral row, also for a one-sided N/A size). The set: "volume", "volume_ml", "size", "size_ml", "size_options", and the count and net-weight fields (RU-14 Q4; the exact field names read from the category spec lists; ES:1092 treats volume, unit count and net weight as a basis).
- Rows: SV-C1 (('volume', '100 ml', '50 ml') -> None), SV-C2 (('size', '100ml', '50ml') and ('size_ml', 100, 50) -> None), SV-C3 (a count 240 vs 120 -> None); P-SV-C (switch off -> today's 0 / 1 / 0; switch on -> storage, weight and battery unchanged).

### A.4 Related observations and data-lane rows (V1 13.4, 13.5)
- R-1 Fragrance projection bars come from the review rating, not the sillage (SS:2177): a "Heavy vs Moderate projection" caption can sit over bars that favour the moderate side.
- R-3 WHAT WE KNOW "Reviews [B7] High" with one side unrated (screen 2): the server's confidence legs (RB:1334 ff.); the same family as B-d.
- O1 (Volume row vs priced size) touches B-c; O2 / O3 / D1 (no price for the right product) trigger B-a; O3 / B-e (identity) produce the sentinel dims (B-b) and the one-sided reviews (B-d); D2 touches none.

## Addendum 1 (S100 orchestrator, 2026-11-22 09:56): the owner's second and third tests of 22 Nov
Sources (private relay notes): the owner's case file (private notes) (row T3) and the owner's case file (private notes) (rows W2 text half, W3, W4), assigned to the main lane by the relay at 09:53. Records checked first (the working-together rule): the data lane's PC1b rows named W1-W3 are its own gate rows; ruling ORCH-SZ1-A gives the data half of W2 (the priced bottle size is the shown size, with W1 and O1) to a new data unit INC-SZ1, and the text half of W2 to the main lane; no other lane builds server result text.
- W3 (the header spread "4.6 avg, 12,000 reviews across both" while only the Versace side has a rating and a count): the B-d family, IN INC-C1b. New RED row D4 in reviewsHeader.c1b.test.tsx: Versace Eros EDP 4.6 / 12,000 against Creed Aventus with no figure -> row 2, no '12,000', no '4.6', no "across both" (EN, AR). Base: FAIL ("4.6[2605] avg [B7] 12,000 reviews across both"). Totals now RED 23, pins 12, 35 tests.
- W4 (CONCENTRATION breaks mid-word): the same label as B-f, IN INC-C1b, covered by F1 / F2 (the EN and AR label rows); no new row.
- W2 text half ("Priced at 25 BHD for 50ml" beside a 100 ml price) and T3 (the result text gives the unidentified side a full note pyramid): SERVER result text, NOT INC-C1b. Proposed for INC-RT1 (Appendix A) with B-a, the B-b server half and B-c: W2 after INC-SZ1's data half (the text must state the priced size or none), T3 a rule that the verdict and pros text carry no description, notes or claim for a side without an identity. Neither fits S81-07m (the output-safety classifier).
