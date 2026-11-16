# INC-C1a SIZE-LABEL: RED report (S96, RED agent, 2026-11-16 20:59-21:17 AST)

Base b0ad260363e0cf0074e4ee596b140d073466e92a, worktree sc-s96-c1a, branch fix/inc-c1a-size-label. Written through the shell (the harness refuses a subagent's Write of a report .md).

## RED file
SmartCompareApp/__tests__/c1a/sizeLabel.c1a.test.tsx, sha256 7a9f3fffcb66005736a929a55d8498f41526b3b562816856b331c94e36ada05d, 24664 bytes, 0 non-ASCII bytes, LF. Harness = the S81-11 honestUnknowns pattern (plain jest.mock of installed packages and child components, the REAL ResultsContent, a t over the real en.json / ar.json). Arabic built from code points (CR-2, PAGE_DESIGN_V2.md table rows 368-370, read with python as UTF-8); P1 goldens recorded at base (run s96c-red-base1) and embedded as escaped literals. No fixture file.

## Base measurements (file:line at b0ad2603)
- requestContext.ts:38 `CLIENT_CAPABILITIES: readonly string[] = []`; :148-156 buildContextHeaders, the header added at :152-154 when the list is non-empty; doc comment :17-19.
- ResultsContent.tsx:53 `import { formatPrice as formatAmountWithCurrency } from '../../utils/formatNumber'`; :187-205 local formatPrice (pending -> results.price.pending, null -> results.priceNA, converted -> `${base} ${t('results.convertedUSD')}`); :383 the render site; :391-401 the converted caption results-product-converted-<i>; :145-185 the S81-11 provenance line; :767-772 styles.convertedCaption.
- formatNumber.ts:96-100 `formatPrice(amount: number, currencyCode: string, t: TranslateFn): string`, digits = CURRENCY_FRACTION_DIGITS[code] ?? 2 (BHD/KWD/OMR 3). NO digits override -> CR-3 applies: add an optional 4th parameter.
- types.ts:60-73 ProductPrice (no size keys); :307 ComparisonResult.metadata.
- i18n parity fences: __tests__/i18n.test.ts (key sets + interpolation vars), __tests__/copy-policy.test.ts, __tests__/s11/copy.s11.test.tsx (leaf count 1,011), __tests__/s11e/arCopy.s11e.test.ts P3 (1,011 each), __tests__/s81_08/i18nKeys.s81_08.test.ts.
- BASE FACT: a converted_usd price shows the converted label TWICE on today's card (price line "58.110 BHD (converted from USD)" AND the caption "(converted from USD)"); golden converted-en-0.

## Runs
- [jest] tag=s96c-red-base2 29.7.0 21:06:21-21:06:23 rc=1: C1-C7 FAIL (7 x expect(received) assertion), P1 P2 PASS.
- [jest] tag=s96c-red-base3 (final bytes, restored base) 21:15:21-21:15:23 rc=1: 7 failed / 2 passed, 7 assertion failures, 0 TypeError/ReferenceError/import errors.
- [jest] tag=s96c-red-sgbase (101 stay-green files) 21:07:16-21:07:27 rc=1: 1137 tests, 1120 pass, 4 fail = the accepted nativeBundle.w37 drift nodes, 13 todo.
- [jest] tag=s96c-red-fullbase (FULL suite, base + RED file) 21:15:29-21:15:42 rc=1: 414 suites, 4081 tests, 11 fail = 7 RED rows + 4 nativeBundle.w37.
- tsc 5.9.3 --noEmit base rc=0 (0 lines); eslint 9.39.4 "src/**/*.{ts,tsx}" (the CI frontend-tests command) base rc=0, 0 errors / 147 warnings; the RED file: 0 errors, 2 import/first warnings (the S81-11 suite pattern).
- [jest] tag=s96c-red-proto2 21:11:45-21:11:47 rc=0: 9/9 pass on the prototype.
- [jest] tag=s96c-red-sgproto 21:11:55-21:12:05 rc=1: 1137 tests, 12 fail = 4 nativeBundle + 8 moved pins.
- [jest] tag=s96c-red-fullproto 21:13:28-21:13:44 rc=1: 4081 tests, 22 fail = 4 nativeBundle + 18 moved pins (list below); RED 9/9.
- tsc proto rc=0, 0 errors; eslint src proto rc=0, 0 errors / 147 warnings (= base); eslint on the 6 diffed files + RED file: 0 errors.

## Rows (each test name starts with its id)
- C1 CLIENT_CAPABILITIES deep-equals ['price_size']; buildContextHeaders({}) carries X-Client-Capabilities === 'price_size' (no price_asof); mergeContextHeaders puts it on a config. requestContext loaded in isolateModules with deviceFingerprint and authService doMocked (plain, not virtual).
- C2 catalog keys equal the spec strings; BHD 58.11 size 100 -> "58.110 BHD · 100 ml" EN and AR (separator U+00B7), the bare amount node absent; card 1 9.5/30; a price with as_of + size shows the size line AND results-product-asof-0.
- C3 catalog keys; formatAmountWithCurrency 3-arg call = '58.110 BHD' (CR-3 pin) and (as any)(0.5811,'BHD',t,4) = '0.5811 BHD'; perml-0 text = "0.5811 BHD per ml" EN / AR; SAR per_ml 0.125 -> "0.125 SAR per ml" (minor unit + 1); the per-ml node style equals the converted caption node style; per_ml undefined / null / 0 / -0.5 / NaN / Infinity / '0.5811' -> no line and no "per ml" text; size null / 0 / 10000 / no size key with per_ml -> no line.
- C4 (CR-4) converted + size 100 -> "58.110 BHD (converted from USD) · 100 ml" EN and AR, the label once in that line, the card's label count equal to the same body without size keys (today's 2).
- C5 controls: size 1 labelled, size 9999 matches /^58\.110 BHD · 9,?999 ml$/ (grouping left to GREEN); then 0, -5, 1.5, 10000, "100", null, NaN, Infinity (with per_ml) -> card texts and testID set identical to the body without size keys, no perml / different-sizes id, EN and AR.
- C6 control: the shown side gets the label and the perml id; then unavailable+amount null, unavailable+amount 58.11, amount null (each with size_ml 100 + per_ml) and an S81-11 honest-line card (field_status unknown, estimated) -> identical to the body without size keys, EN and AR.
- C7 catalog keys; different_sizes + two shown prices -> exactly one results-price-different-sizes with the EN / AR text; same_size, unknown, absent, a string marker, one pending side, one amount-null side -> none and the text absent from both cards.
- P1 three bodies with no new key (shown pair; converted + pending; N/A + SAR) x EN/AR -> both card texts equal the base golden; no perml / different-sizes id.
- P2 en/ar key sets equal and interpolation vars match; asof-0 (2 d) and lastseen-0 (10 d) text identical with and without size_ml / per_ml, EN and AR.

## Prototype (in place, lock W/.qa-mutation.lock, byte copies in red/bak/, diff saved as red/proto.diff 210 lines sha256 42f78d544d10e66c9577938dbde5adeda8c001a47021311ec2dc34d4a8162907 BEFORE restore)
- requestContext.ts: CLIENT_CAPABILITIES = ['price_size'] + the doc comment.
- formatNumber.ts formatPrice(amount, currencyCode, t, fractionDigits?) : an integer 0..6 overrides the width, anything else = today's minor unit (3-arg callers byte-identical).
- types.ts: ProductPrice size_ml? / per_ml? (number | null); metadata.pair_price_sizes? {mode, sizes_ml} | null.
- ResultsContent.tsx: isShownPrice (unavailable !== true, amount finite number), validSizeMl (integer 1..9999 on a shown price), priceLine = results.price.withSize {price: today's formatPrice output, size: formatNumber(size,{maxFraction:0,grouping:false})}; perMlLine (valid size AND per_ml finite > 0; digits = minor unit + 1; formatAmountWithCurrency(per_ml, currency, t, digits)); the perml Text (testID results-product-perml-<i>, styles.convertedCaption, numberOfLines 1) under the price line, before the provenance line, not on an honest-line card; the different-sizes caption (testID results-price-different-sizes, convertedCaption style) right after the hero pair, only for mode different_sizes, two products, both shown and neither on the honest line.
- en.json / ar.json: the three keys after results.price.checkedEarlier (EN as the unit spec, AR byte-exact from PAGE_DESIGN_V2.md rows 368-370), CRLF kept; 1,014 leaves each.

## Moved pins (E-rows for GREEN; every one is caused by the two intended changes; all PASS at base)
Header (X-Client-Capabilities: price_size now on every request that builds context headers):
- s81_08/requestHeaders.s81_08.test.ts:456 B9 `expect(w.rc?.CLIENT_CAPABILITIES).toEqual([]);` and :459 `expect(h['x-client-capabilities']).toBeUndefined();`
- requestHeaders :355 B1, :436 B7 `expect(h).toEqual({ authorization: 'Bearer ' + BEARER_VALUE });`, :511 B13, :527 B14a, :538 B14b `expect(thrown).toEqual({ authorization: ..., 'x-device-fingerprint': NEW });`, :562 B14d (exact header objects; received + "x-client-capabilities": "price_size").
- s81_08/cameraHeaders.s81_08.test.ts:193 C1, :253 C5; s81_08/sseHeaders.s81_08.test.ts:193 D1, :255 D6 (exact header objects).
- api.cameraAuthRetry.u13c.test.ts:333 T1, :486 T9, :583 T17b, :599 T19, :725 T17a "first request shape is today's" (T17a/T17b received a headers object {X-Client-Capabilities: price_size} where base had none).
Catalog size (1,011 -> 1,014):
- s11/copy.s11.test.tsx:191 `expect(e.length).toBe(1013 - DELETED.length + ...)` (Expected 1011, Received 1014).
- s11e/arCopy.s11e.test.ts:140 `toEqual({ ar: 1011, en: 1011 })`.
The stay-green grep set (101 files) caught 8 of these 18; cameraHeaders, sseHeaders, api.cameraAuthRetry.u13c and s11e/arCopy do not name requestContext / the header and were found only by the full run.

## Mutants (prototype, RED file alone; all KILLED on assertions; prototype bytes restored + sha-checked after each)
MC1 list empty -> C1. MC2 client computes amount/size when per_ml is absent -> C3. MC3 size gate ignores shown (pending gets the label) -> C6. MC4 size 10000 accepted -> C3, C5. MC5 caption on same_size -> C7. MC6 converted label appended again inside withSize -> C4. MC7 per-ml digits = minor unit -> C3. MC8 caption without the both-shown check -> C7. Lines: [jest] tag=s96c-red-MC1..MC8 21:14:17-21:14:36, each rc=1.

## Restore
All 6 src files copied back from the byte copies: sha256 equal to the copies and git hash-object equal to the HEAD blob for every one; lock removed; git status --short = `?? SmartCompareApp/__tests__/c1a/` only.

## Other surfaces that print a price amount (CR-5: today's text, not touched by the prototype)
- HomeEditorialSections.tsx:175 / :220 smart pick formatPrice(pick.runner_up_price_bhd / winner_price_bhd, 'BHD', t) (its own /home/smart-pick route; 3-arg call unchanged).
- ResultsScreen.tsx:716-724 getPriceDiff (dead: priceDiff never read) and :573-581 the text-only share body (names + winner + recommendation, no price).
- History: no price line of its own (HistoryScreen.tsx:135, the savings line removed by S81-11); a saved result opens through ResultsScreen -> ResultsContent (resultOrigin 'stored'), so it draws the size label only if the saved body carries size_ml.
- LoadingScreenVariants.tsx:504-508 a ghost price field, no amount. ShareBottomSheet: no price.

## Deviations
- D1 EN withSize: PAGE_DESIGN_V2.md row 368 has "{{price}} - {{size}} ml" (hyphen-minus) while the unit spec 3.2 / C2 say U+00B7; the RED follows the unit spec (AR uses U+00B7 in both).
- D2 The string table is PAGE_DESIGN_V2.md section 6a (rows 368-370), not section 7 (CR-2 says 7; section 7 is the live-bundle table).
- D3 C5 and C6 carry positive controls (size 1 / 9999; the shown side) so the rows fail at base as ordered; the guard halves pass at base by nature.
- D4 C6 adds an inferred case: the S81-11 honest-line card (field_status unknown) with size keys -> today's text, no per-ml line.
- D5 Per-ml precision follows CR-3 (minor unit + 1, SAR 3 places), not spec 3.3's "+ 2 otherwise"; C3 pins the formatter's 4th POSITIONAL parameter as the digits override.
- D6 Not pinned: the 4-digit size grouping (regex 9,?999), the per-ml line's order against the provenance line, the caption's position.
- D7 The full suite was run on the prototype and at base (spec 5, LC-7) in addition to the ordered stay-green set.
- NOT MEASURED: the backend fences reading edited client files (tests/test_comparison_id_echo.py (types.ts); test_dimension_label_catalog_parity_w414.py, test_legal_docs_u8.py, test_legal_docs_u8_d3c.py, test_s81_12_gate_rows.py, test_s81_12_legal_v3.py (en/ar.json)): no pytest was run; --runInBand order pairs not run; nothing on a device.

## Open questions for the gate
- Q1 EN separator: U+00B7 (unit spec) or " - " (design row 368)?
- Q2 Today's card already prints the converted label twice (line + caption). CR-4 "one converted label, always" read as once INSIDE the price line, the caption kept; confirm.
- Q3 A converted price's per-ml line carries no converted marker; acceptable?
- Q4 4-digit sizes: "1,000 ml" or "1000 ml"? (prototype: no grouping).
- Q5 The header now rides the camera upload, the SSE request and the 401 retry (a request that carried no context header now carries one, T17a/T17b); confirm every server route tolerates it (kb_serve reads only price_asof).
- Q6 D4: should an honest-line card ever show the size? (prototype: never).
