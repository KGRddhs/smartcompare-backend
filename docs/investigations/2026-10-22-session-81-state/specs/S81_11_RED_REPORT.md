# S81-11 RED REPORT (HONEST-FRAGRANCE-UI + D20) -- RED agent, Opus 5.5, 2026-11-05 08:59-09:55 AST

Base 6869a3e655805afd3adbba43f99578dd79585934 (sc-s81-s11, rev-parse verified). Spec sha 2e3529a3... (as briefed), review, RULINGS_S81_11 (R-S11-11..41) and the brief (R-S11-1..10) read in full. Toolchain by path through the junction (node_modules/@babel/core and .bin/jest present): node v24.11.1, jest 29.7.0, typescript 5.9.3, eslint v9.39.4.
Client exceptions honoured: prototype + mutation table IN PLACE under sc-s81-s11/.qa-mutation.lock on shutil byte copies (bytes/ manifest of 36 paths incl. 2 new + 1 deleted src + CohortBadge.test + 13 E1b test files + usageService.ts), restored and sha256-compared (restored 36 mismatch 0; lock removed; `git diff --quiet` rc 0). NO scratch worktree. No npm / npx / git write / .env.
NOT RUN by ruling R-S11-1 / R-S11-38: the R8 pair, paid-route metering as a gate (its file ran only as a SmartCompareApp scanner in c1), the hook files, a pytest CI-order set, the corpus gate, a base scratch worktree. The FULL jest suite: NOT run (LC-7, the final round).
This file was written through the shell (python), per the harness rule; also copied to <scratchpad>/S81-11_RED_REPORT.md.

## 1. RED files (8, pure ASCII, LF, 0 bytes > 127, 0 CRLF)
```
__tests__/s11/categoryRow.s11.test.tsx 17785 b30471b3b72c468c84179ffb189a3ea2b5efe1e007559f367c913c6706af0b5e hi 0 crlf 0
__tests__/s11/copy.s11.test.tsx 11414 f676178130161ea4159c75b5f1b4c258997e55c0c4b2e0bc22be15119eed0d7e hi 0 crlf 0
__tests__/s11/fabricated.s11.test.tsx 9950 35aa66559feacf7d067532232a5aa3e2b8d1143b6b5b29cd547fb7edad64529e hi 0 crlf 0
__tests__/s11/honestUnknowns.s11.test.tsx 28437 489889830480f09a4b7e97777b43a6e42145b05283e0111096ed6b272daa08de hi 0 crlf 0
__tests__/s11/launchSurfaces.s11.test.ts 11608 e4abba60b17be97e22e7c980525842f4db0faeda4c0072e5f71a628dde8fe726 hi 0 crlf 0
__tests__/s11/refusals.s11.test.tsx 18899 751b24d660e3ae2b5c0a225113491dcd8c5115467dadd647069bddaca9fe07f5 hi 0 crlf 0
__tests__/s11/refusalsCamera.s11.test.tsx 7723 573a9c139e8da60105b9337c3c3a286992fd90f4a367fd1d4e2dff2a1ea11152 hi 0 crlf 0
__tests__/s11/sseFallback.s11.test.ts 11389 c3e4224ca2065b9c99450b680edcdaa0da523841c62ca11344f250b317161256 hi 0 crlf 0
```
Deviation from spec 5 file names: +1 file `refusalsCamera.s11.test.tsx` (the camera rows need the ResultsScreen harness; one file per harness). The event rows and P11 are deleted (R-S11-27).

## 2. Base and prototype runs of the RED files
Base (final bytes): [jest] tag=s11red-base-final start=2026-11-05 09:47:28 end=2026-11-05 09:47:45 rc=1
Prototype (final bytes): [jest] tag=s11red-proto-2 start=2026-11-05 09:43:22 end=2026-11-05 09:43:38 rc=0
```
file                          nodes  base failed/passed  proto failed/passed
categoryRow.s11.test.tsx        10      10 / 0              0 / 10
copy.s11.test.tsx               12      11 / 1              0 / 12
fabricated.s11.test.tsx         14      11 / 3              0 / 14
honestUnknowns.s11.test.tsx     31      24 / 7              0 / 31
launchSurfaces.s11.test.ts      13      12 / 1              0 / 13
refusals.s11.test.tsx           22      16 / 6              0 / 22
refusalsCamera.s11.test.tsx      6       4 / 2              0 / 6
sseFallback.s11.test.ts         16       8 / 8              0 / 16
TOTAL                          124      96 / 28             0 / 124
```
Assertion proof: every one of the 96 base failures is an expect() AssertionError (failureMessages carry the expect matcher text; 0 OTHER, 0 suite load errors). Missing modules are read through loadOptional and asserted; static rows read files with fs.readFileSync, CRLF normalised, comments stripped (RC9). The 28 base passes are the PIN rows (absent = today) and the PIN-at-base helper rows. Per node (status, class, node id, first message line):
```
suites 8 failedSuites 8 tests 124 passed 28 failed 96 pending 0
FAILED ASSERT __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > D1: non-OK 400 with CATEGORY_NOT_LIVE -> onError once, ZERO REST calls | Error: expect(jest.fn()).not.toHaveBeenCalled()
FAILED ASSERT __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > D1b: the code under body.detail (legacy shape) is honoured too | Error: expect(jest.fn()).not.toHaveBeenCalled()
FAILED ASSERT __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > D2: non-OK 429 budget body -> onError once (status 429), ZERO REST calls | Error: expect(jest.fn()).not.toHaveBeenCalled()
PASSED OTHER __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > PIN P6: non-OK 500 with an unreadable body -> exactly ONE REST compare (today) | 
PASSED OTHER __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > PIN P6b: non-OK 400 with ANOTHER code -> exactly ONE REST compare (today) | 
PASSED OTHER __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > PIN: an OK response with no body keeps the REST fallback once (today) | 
PASSED OTHER __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > PIN P5: an SSE error event with CATEGORY_NOT_LIVE -> onError once, ZERO REST calls | 
FAILED ASSERT __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > R-S11-26: the error event forwards its reason into the synthetic data | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > R-S11-26: a success:false complete frame forwards its reason | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > R-S11-26: a success:false settle_complete frame forwards its reason | Error: expect(received).toBe(expected) // Object.is equality
PASSED OTHER __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > PIN: a reasonless success:false complete keeps today's synthetic data shape | 
PASSED OTHER __tests__/s11/sseFallback.s11.test.ts :: S81-11 SSE transport (flag ON through the test seam) > PIN: a reasonless error event keeps today's synthetic data shape | 
FAILED ASSERT __tests__/s11/sseFallback.s11.test.ts :: S81-11 R-S11-26 -- parseApiError reads reason top-level, then detail > a top-level string reason is returned | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/sseFallback.s11.test.ts :: S81-11 R-S11-26 -- parseApiError reads reason top-level, then detail > a reason under detail is returned | Error: expect(received).toBe(expected) // Object.is equality
PASSED OTHER __tests__/s11/sseFallback.s11.test.ts :: S81-11 R-S11-26 -- parseApiError reads reason top-level, then detail > PIN: a non-string or absent reason is never returned | 
PASSED OTHER __tests__/s11/sseFallback.s11.test.ts :: S81-11 R-S11-26 -- parseApiError reads reason top-level, then detail > PIN: a 429 CATEGORY_NOT_LIVE keeps its code and retryAfterSeconds | 
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B9 -- parseLaunchSurfaces truth table > the module exists with its documented API | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B9 -- parseLaunchSurfaces truth table > categories_live: only an array of strings is accepted (lower-cased, trimmed) | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B9 -- parseLaunchSurfaces truth table > surfaces: a chip is true ONLY for the boolean true; unknown keys ignored | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B9 -- parseLaunchSurfaces truth table > a non-object payload is ABSENT | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B9 -- parseLaunchSurfaces truth table > recordLaunchSurfaces never throws, stores and notifies subscribers | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B9 -- parseLaunchSurfaces truth table > R-S11-27: no event-name constant is exported (the event ships with SF1) | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B8 -- categoryToSend (R-S11-3 / R-S11-34) > fragrances ONLY when selected AND categories_live carries it | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B10 -- checkForcedUpdate feeds the store (C5) > a body carrying categories_live is recorded; the gate decision is unchanged | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B10 -- checkForcedUpdate feeds the store (C5) > a rejecting fetch / non-OK / non-JSON body leaves the store ABSENT | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B10 -- checkForcedUpdate feeds the store (C5) > Expo Go (no native version): no fetch AND the store stays ABSENT | Error: expect(received).not.toBeNull()
PASSED OTHER __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 B10 -- checkForcedUpdate feeds the store (C5) > a forced-update body still blocks (the record call never changes the decision) | 
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 R-S11-19 -- the store is fed only from checkForcedUpdate > appVersionService records the parsed payload after the json parse, inside the try | Error: expect(received).toMatch(expected)
FAILED ASSERT __tests__/s11/launchSurfaces.s11.test.ts :: S81-11 R-S11-19 -- the store is fed only from checkForcedUpdate > no other src file calls recordLaunchSurfaces, and launchSurfaces does no network | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/refusalsCamera.s11.test.tsx :: S81-11 C4 -- camera CATEGORY_NOT_LIVE (refusal + budget bodies) > camera_refusal_body -> results-category-not-live-state with the two strings and Back | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/refusalsCamera.s11.test.tsx :: S81-11 C4 -- camera CATEGORY_NOT_LIVE (refusal + budget bodies) > camera_budget_body -> results-category-not-live-state with the two strings and Back | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/refusalsCamera.s11.test.tsx :: S81-11 C6 -- camera reason same_identity / category_conflict > action error + reason same_identity -> results-reason-state with the reason copy | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/refusalsCamera.s11.test.tsx :: S81-11 C6 -- camera reason same_identity / category_conflict > action error + reason category_conflict -> results-reason-state with the reason copy | Error: expect(received).not.toBeNull()
PASSED OTHER __tests__/s11/refusalsCamera.s11.test.tsx :: S81-11 PIN rows -- camera absent = today (R-A6) > P7: action error with no code / no reason, placeholder_identity, low_confidence -> vision_failed | 
PASSED OTHER __tests__/s11/refusalsCamera.s11.test.tsx :: S81-11 PIN rows -- camera absent = today (R-A6) > P8: action comparison_failed (no code) -> the timeout state | 
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E1r -- priceProvenance truth table (the owner staleness rule) > the module exports the documented API and constants | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E1r -- priceProvenance truth table (the owner staleness rule) > converted: 23 h fresh, 25 h stale; genuine: 6 d fresh, 8 d stale, 31 d unknown | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E1r -- priceProvenance truth table (the owner staleness rule) > R-S11-12: an estimate under field_status unknown/estimated is the honest line; absent field_status = none | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E1r -- priceProvenance truth table (the owner staleness rule) > unavailable / no amount: unknown only under field_status unknown, else none | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E1r -- priceProvenance truth table (the owner staleness rule) > dates: no as_of anywhere -> none; field_status as_of used; price.as_of preferred; future -> fresh; unparsable -> none | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E1r -- priceProvenance truth table (the owner staleness rule) > R-S11-14: the store is price.retailer as-is (a host included), else null | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E1r -- priceProvenance truth table (the owner staleness rule) > R-S11-18: field_status stale with as_of null -> the dateless stale marker | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E1r -- priceProvenance truth table (the owner staleness rule) > R-S11-13: a STORED body with a date is listed (never aged out); without a date none | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 field_status / section_status readers > productFieldStatus: only an array entry that is a plain object | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 field_status / section_status readers > R-S11-21: the section line is for unavailable ONLY | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 R-S11-24 -- the as-of date is gregorian in both locales > a known date renders Nov 3 (EN) and the gregorian November (AR), never Hijri | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 R-S11-24 -- the gregorian calendar is explicit in the source > fieldStatusView names the gregorian calendar (Node ICU 77 defaults ar-SA to gregory; Hermes may not) | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E2r / E3r -- the card price under field_status / as_of > E2r: price unknown/no_price + amount null -> the honest line in the card-0 price Text (R-S11-17) | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E2r / E3r -- the card price under field_status / as_of > R-S11-12: an estimate under field_status renders the honest line and NO amount | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E2r / E3r -- the card price under field_status / as_of > E3r: 2 d -> "<store>, as of <date>"; 10 d -> last seen; 31 d -> the honest line, no amount | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E2r / E3r -- the card price under field_status / as_of > R-S11-18: field_status stale with as_of null -> the dateless checked-earlier marker | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E2r / E3r -- the card price under field_status / as_of > R-S11-13: a STORED body renders the amount WITH its listed date, never aged out | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E2r / E3r -- the card price under field_status / as_of > R-S11-25: the narrow RTL card renders the AR honest line with numberOfLines set | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E2r / E3r -- the card price under field_status / as_of > ResultsScreen passes resultOrigin stored for the comparison_id (History) entry | Error: expect(received).toMatch(expected)
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 the honest prop handed to ResultsAccordion (C15) > section_status partial / unavailable / available -> sections {specs false, reviews true, pros_cons false} | Error: expect(received).toBeDefined()
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 the honest prop handed to ResultsAccordion (C15) > field_status alone -> honest.fields carries the per-product entries | Error: expect(received).toEqual(expected) // deep equality
PASSED OTHER __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 the honest prop handed to ResultsAccordion (C15) > PIN P1 (M21): absent metadata -> no honest prop at all | 
PASSED OTHER __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 PIN P1 / R-S11-16 -- absent metadata = today, per surface (green at base) > origin undefined: the price strings equal today's and no honest testID renders | 
PASSED OTHER __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 PIN P1 / R-S11-16 -- absent metadata = today, per surface (green at base) > origin live: the price strings equal today's and no honest testID renders | 
PASSED OTHER __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 PIN P1 / R-S11-16 -- absent metadata = today, per surface (green at base) > origin stored: the price strings equal today's and no honest testID renders | 
PASSED OTHER __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 PIN P1 / R-S11-16 -- absent metadata = today, per surface (green at base) > a live body with no as_of renders an identical tree for origin live and absent | 
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E4r / E5r -- ResultsAccordion honest lines (C16) > E4r: reviews unavailable -> the section line first in its body; specs partial / proscons available -> none | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E4r / E5r -- ResultsAccordion honest lines (C16) > E4r-b: specs unavailable -> the section line is the first child of the specs body | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E4r / E5r -- ResultsAccordion honest lines (C16) > E5r: size unknown + no size/volume row -> the field line; concentration unknown but listed -> none | Error: expect(received).not.toBeNull()
PASSED OTHER __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E4r / E5r -- ResultsAccordion honest lines (C16) > E5r-b: a size unknown WITH a volume row -> no field line | 
PASSED OTHER __tests__/s11/honestUnknowns.s11.test.tsx :: S81-11 E4r / E5r -- ResultsAccordion honest lines (C16) > PIN: no honest prop -> no honest testID in any open body (today) | 
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B1 -- ABSENT surfaces: one Fragrances chip + the fragrance-only line > renders exactly category-chip-fragrances and home-fragrance-only-line; no nudge | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B1 -- ABSENT surfaces: one Fragrances chip + the fragrance-only line > the line stays when the Fragrances chip is selected (both row states) | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B2 / B3 / B4 -- coming-soon chips only under surfaces > B2: surfaces {skincare, makeup} -> chips fragrances, skincare, makeup in order, both badged | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B2 / B3 / B4 -- coming-soon chips only under surfaces > B3: a coming-soon tap -> the toast (+ iOS announcement), no event, no navigate, no compare | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B2 / B3 / B4 -- coming-soon chips only under surfaces > B4: invalid surfaces render no soon chip and a fragrance tap queues no coming-soon event | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B5 -- QUICK_CATS is the one fragrances tile > QuickCategories renders exactly home-quick-cat-fragrances | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B6 / B7 / B8 -- selected_category gated on categories_live (R-S11-3) > B6: chip selected + ABSENT version body -> no selected_category on text or link | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B6 / B7 / B8 -- selected_category gated on categories_live (R-S11-3) > B7: chip selected + categories_live [fragrances] -> fragrances on text and link | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B6 / B7 / B8 -- selected_category gated on categories_live (R-S11-3) > B8: chip NOT selected + categories_live [fragrances] -> no selected_category | Error: expect(received).not.toBeNull()
FAILED ASSERT __tests__/s11/categoryRow.s11.test.tsx :: S81-11 B6 / B7 / B8 -- selected_category gated on categories_live (R-S11-3) > B8b: a QUICK_CATS pick sets the chip but still sends only through the gate | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C1 / C2 -- text path CATEGORY_NOT_LIVE > C1: a 400 renders the coming-soon Alert, never the Paywall | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C1 / C2 -- text path CATEGORY_NOT_LIVE > C2: a 429 (retry_after_seconds 3600, refusal_daily) renders the same Alert, no seconds | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C1 / C2 -- text path CATEGORY_NOT_LIVE > C1b: a success:false terminal carrying CATEGORY_NOT_LIVE renders the same Alert | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C3 -- link path CATEGORY_NOT_LIVE (R-S10B-15) > a 400 renders the coming-soon Alert | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C3 -- link path CATEGORY_NOT_LIVE (R-S10B-15) > a 429 renders the same Alert, no seconds, no Paywall | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C3 -- link path CATEGORY_NOT_LIVE (R-S10B-15) > a success:false body with CATEGORY_NOT_LIVE renders the same Alert | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C5 -- INSUFFICIENT_DATA reason copy (S81-20 additive, R-S11-26) > text: reason same_identity -> its own sentence | Error: expect(received).toBeDefined()
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C5 -- INSUFFICIENT_DATA reason copy (S81-20 additive, R-S11-26) > link: reason same_identity -> its own sentence | Error: expect(received).toBeDefined()
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C5 -- INSUFFICIENT_DATA reason copy (S81-20 additive, R-S11-26) > text: reason placeholder_identity -> its own sentence | Error: expect(received).toBeDefined()
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C5 -- INSUFFICIENT_DATA reason copy (S81-20 additive, R-S11-26) > link: reason placeholder_identity -> its own sentence | Error: expect(received).toBeDefined()
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C5 -- INSUFFICIENT_DATA reason copy (S81-20 additive, R-S11-26) > text: reason category_conflict -> its own sentence | Error: expect(received).toBeDefined()
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C5 -- INSUFFICIENT_DATA reason copy (S81-20 additive, R-S11-26) > link: reason category_conflict -> its own sentence | Error: expect(received).toBeDefined()
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C5 -- INSUFFICIENT_DATA reason copy (S81-20 additive, R-S11-26) > text: a reason under detail (legacy shape) is read too | Error: expect(received).toBeDefined()
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C5 -- INSUFFICIENT_DATA reason copy (S81-20 additive, R-S11-26) > text: a success:false terminal forwards its reason | Error: expect(received).toBeDefined()
PASSED OTHER __tests__/s11/refusals.s11.test.tsx :: S81-11 PIN rows -- absent = today (green at base) > P2: INSUFFICIENT_DATA with no reason / no_evidence / an unknown reason -> today | 
PASSED OTHER __tests__/s11/refusals.s11.test.tsx :: S81-11 PIN rows -- absent = today (green at base) > P3: 429 USAGE_LIMIT on text and link -> navigate(Paywall, {initialUsage}) | 
PASSED OTHER __tests__/s11/refusals.s11.test.tsx :: S81-11 PIN rows -- absent = today (green at base) > P4: RATE_LIMITED 429 with retry_after_seconds 5 keeps the seconds sentence | 
PASSED OTHER __tests__/s11/refusals.s11.test.tsx :: S81-11 PIN rows -- absent = today (green at base) > P4b: an engine outage keeps its own title + body | 
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C7 -- errorCopy map (C12) > CATEGORY_NOT_LIVE -> categoryNotLive / fragrancesOnly | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/refusals.s11.test.tsx :: S81-11 C7 -- errorCopy map (C12) > INSUFFICIENT_DATA + reason -> the reason key; no_evidence / unknown / none -> today | Error: expect(received).toBe(expected) // Object.is equality
PASSED OTHER __tests__/s11/refusals.s11.test.tsx :: S81-11 C7 -- errorCopy map (C12) > PIN: the single-argument results are unchanged (absent reason = today) | 
PASSED OTHER __tests__/s11/refusals.s11.test.tsx :: S81-11 C7 -- errorCopy map (C12) > every key the map can return exists in both catalogs | 
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F1 -- ADD / CHANGE / DELETE (both catalogs) > every spec ADD key exists with its exact EN value and a non-empty AR value | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F1 -- ADD / CHANGE / DELETE (both catalogs) > every ruling ADD key exists in both catalogs with its placeholder set | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F1 -- ADD / CHANGE / DELETE (both catalogs) > every CHANGE key carries its new EN value; AR is non-empty and not English | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F1 -- ADD / CHANGE / DELETE (both catalogs) > R-S11-22: insufficientData / comparison are fragrance-neutral (brand and name, no model) | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F1 -- ADD / CHANGE / DELETE (both catalogs) > R-S11-32: onboarding.s17.tag_echoes_body carries no digit in either catalog | Error: expect(received).not.toMatch(expected)
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F1 -- ADD / CHANGE / DELETE (both catalogs) > the 17 deleted keys are absent from both catalogs (R-S11-11 / R-S11-36) | Error: expect(received).toEqual(expected) // deep equality
PASSED OTHER __tests__/s11/copy.s11.test.tsx :: S81-11 F1 -- ADD / CHANGE / DELETE (both catalogs) > PIN R-S11-11: the six home.savings.count_* keys stay in both catalogs | 
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F1 -- ADD / CHANGE / DELETE (both catalogs) > parity 0 and 1,011 leaves per catalog | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F2 -- the new and changed values obey the copy policy > no banned / scary pattern; no EN digit outside {{...}} | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F3 / A5 -- no electronics / other-category / fabricated copy remains > no catalog value names iPhone / Galaxy / sunscreen / multivitamin / Compare anything | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 F3 / A5 -- no electronics / other-category / fabricated copy remains > no catalog value or src string literal says "shopped smarter" or "30 seconds" | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/copy.s11.test.tsx :: S81-11 A6 -- HomeEditorialSections renders no savings banner > even when getHomeSavings resolves a met threshold | Error: expect(received).toBeNull()
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A1 / A2 -- CohortBadge is deleted with zero renderers left > A1: the module no longer exists | Error: expect(received).toBe(expected) // Object.is equality
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A1 / A2 -- CohortBadge is deleted with zero renderers left > A2: ResultsContent / ReferralLanding / ResultsScreen carry no CohortBadge token or slot | Error: expect(received).toEqual(expected) // deep equality
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A3 -- LoadingRings has no fabricated counter (C3, R-S11-20) > A3: no counterTarget -> no counter chip and no digit at all | Error: expect(received).toBeNull()
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A3 -- LoadingRings has no fabricated counter (C3, R-S11-20) > A3b: showCounter alone (no target) still renders no chip | Error: expect(received).toBeNull()
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A3 -- LoadingRings has no fabricated counter (C3, R-S11-20) > A3c (R-S11-20): animated with no target never ticks a NaN or a number | Error: expect(received).toEqual(expected) // deep equality
PASSED OTHER __tests__/s11/fabricated.s11.test.tsx :: S81-11 A3 -- LoadingRings has no fabricated counter (C3, R-S11-20) > PIN: an explicit real target still renders its chip (Step14 cohort count path) | 
PASSED OTHER __tests__/s11/fabricated.s11.test.tsx :: S81-11 A3 -- LoadingRings has no fabricated counter (C3, R-S11-20) > PIN: showCounter={false} with a target renders no chip | 
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A3 -- LoadingRings has no fabricated counter (C3, R-S11-20) > A3d: the component source carries no 2074 default | Error: expect(received).not.toMatch(expected)
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A4 -- InviteeQuiz renders no fabricated match score (C2) > A4: no scoring -> no quiz-match-score row and no 78% | Error: expect(received).toBeNull()
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A4 -- InviteeQuiz renders no fabricated match score (C2) > A4b: a non-finite overall is not a score either | Error: expect(received).toBeNull()
PASSED OTHER __tests__/s11/fabricated.s11.test.tsx :: S81-11 A4 -- InviteeQuiz renders no fabricated match score (C2) > PIN: a real overall still renders (91.4 -> 91%) | 
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A6 -- the savings tile and line are gone from Profile and History (C8 / C9) > ProfileEditorialSections renders no savings tile | Error: expect(received).not.toMatch(expected)
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A6 -- the savings tile and line are gone from Profile and History (C8 / C9) > HistoryScreen renders no savings line | Error: expect(received).not.toMatch(expected)
FAILED ASSERT __tests__/s11/fabricated.s11.test.tsx :: S81-11 A6 -- the savings tile and line are gone from Profile and History (C8 / C9) > HomeEditorialSections has no SavingsBanner | Error: expect(received).not.toMatch(expected)
```

## 3. The contract the RED rows fix for GREEN (named, beyond the spec text)
- src/services/launchSurfaces.ts: parseLaunchSurfaces / recordLaunchSurfaces / getLaunchSurfaces / subscribeLaunchSurfaces / useLaunchSurfaces / categoryToSend / __resetLaunchSurfaces / ABSENT_LAUNCH_SURFACES; NO event-name constant (R-S11-27); fed only from checkForcedUpdate (one statement after the json parse, R-S11-19); no network in the leaf.
- src/services/fieldStatusView.ts: productFieldStatus, isFieldUnknown, priceProvenance(price, fieldPrice, nowMs, origin?), sectionNeedsHonestLine (unavailable ONLY, R-S11-21), formatAsOfDate(dateIso, lang) (gregorian, R-S11-24; a static row requires the explicit u-ca-gregory / calendar option because Node ICU 77 already defaults ar-SA to gregory), constants 24 / 7 / 30.
- priceProvenance kinds: none | fresh | stale | staleNoDate (R-S11-18) | unknown | listed (R-S11-13 stored, dateful, never aged). An estimate under field_status unknown -> unknown (R-S11-12); absent field_status -> none. Store = price.retailer as-is incl. a host (R-S11-14).
- ResultsContent: optional prop resultOrigin (live default | stored); ResultsScreen passes stored for the comparison_id entry (static row). Card testIDs: results-product-price-honest-<i> (numberOfLines set, R-S11-25), -asof-, -lastseen-, -listed-, -checked-; honest prop passed ONLY when metadata carries section_status or field_status (kills M21: RC5 equivalence not needed).
- ResultsAccordion: honest={sections:{specs,reviews,pros_cons}, fields:[..]}; section line results-accordion-honest-<specs|reviews|proscons> FIRST child of the body; field line results-accordion-honest-field-<size|concentration>-<i> only when the side has no non-NA value for volume/size resp. concentration. C16 label keys (R-S11-37): results.spec.size (EN "Size") for size and results.spec.concentration (EN "Concentration"); the spec row keys checked are volume / size / concentration.
- Keys added beyond the spec 12 (rulings): results.price.listedOn {store,date}, results.price.listedOnNoStore {date}, results.price.checkedEarlier (no placeholder). Deleted: 17 (spec 23 minus the six home.savings.count_*, R-S11-11). Leaf count 1,011 per catalog (1,013 - 17 + 15).
- Reworded by ruling (constraints pinned, wording GREEN's): home.errors.insufficientData + home.errors.comparison (no "model", contain "brand" and "name", R-S11-22); onboarding.s17.tag_echoes_body digit-free EN + AR (R-S11-32).
- HomeScreen: home-fragrance-only-line in both row states; home-coming-soon-toast 2,500 ms + AccessibilityInfo.announceForAccessibility on iOS (R-S11-23); soon chips accessibilityState {disabled:false, selected:false} + an accessibilityHint; a soon tap never changes the selected chip; zero /app/version fetches during a compare; CATEGORY_NOT_LIVE Alert = (t(home.categories.fragrancesOnly), t(home.errors.categoryNotLive)) with no digit.
- api.ts: parseApiError returns reason (top-level, then detail; string only; absent = no key, R-S11-26); the SSE non-OK arm split (R-S11-19), the CATEGORY_NOT_LIVE body (or body.detail) -> one onError(status, body), no REST; the reason forwarded from complete / settle_complete success:false frames and the error arm; reasonless synthetic shapes unchanged (PIN).
- ResultsScreen camera: results-category-not-live-state (title + body + common.back), results-reason-state (same_identity / category_conflict); placeholder_identity / low_confidence / no code -> vision_failed (P7).

## 4. Prototype (in place, thrown away)
Files (git diff --stat at the prototype, before restore):
```
.../ResultsContent.confidenceSheet.test.tsx        |   1 -
 .../__tests__/ResultsContent.imageUrl.test.tsx     |   1 -
 .../__tests__/ResultsContent.partialNote.test.tsx  |   1 -
 .../__tests__/ResultsContent.perCategory.test.tsx  |   1 -
 .../__tests__/ResultsContent.scoreGuard.test.tsx   |   1 -
 .../ResultsContent.specsComparisonShape.test.tsx   |   1 -
 .../__tests__/ResultsContent.v2Wiring.test.tsx     |   1 -
 .../__tests__/clientTruth/medicalNote.s74.test.tsx |  11 --
 .../__tests__/components/CohortBadge.test.tsx      |  86 --------------
 .../components/ResultsContent.a11y.w311.test.tsx   |   3 -
 .../components/ResultsContent.render.test.tsx      |  11 --
 .../ResultsContent.rewriteOrder.test.tsx           |   8 --
 .../components/ResultsContent.runnerUp.test.tsx    |   1 -
 .../screens/ResultsScreen.degraded.s69.test.tsx    |   1 -
 .../src/components/CategorySelector.tsx            |  58 +++++++--
 SmartCompareApp/src/components/CohortBadge.tsx     | 105 ----------------
 .../src/components/HomeEditorialSections.tsx       |  48 +-------
 .../src/components/ProfileEditorialSections.tsx    |   7 --
 .../src/components/hero/LoadingRings.tsx           |  13 +-
 .../src/components/results/ResultsAccordion.tsx    |  45 +++++++
 .../src/components/results/ResultsContent.tsx      | 132 ++++++++++++++++-----
 SmartCompareApp/src/i18n/ar.json                   |  52 ++++----
 SmartCompareApp/src/i18n/en.json                   |  52 ++++----
 SmartCompareApp/src/screens/HistoryScreen.tsx      |   7 --
 SmartCompareApp/src/screens/HomeScreen.tsx         |  76 +++++++++---
 SmartCompareApp/src/screens/InviteeQuizScreen.tsx  |  10 +-
 .../src/screens/ReferralLandingScreen.tsx          |  16 ---
 SmartCompareApp/src/screens/ResultsScreen.tsx      |  80 +++++++------
 SmartCompareApp/src/services/api.ts                |  53 ++++++++-
 SmartCompareApp/src/services/appVersionService.ts  |   2 +
 SmartCompareApp/src/services/errorCopy.ts          |  15 ++-
 SmartCompareApp/src/types/types.ts                 |   7 ++
 32 files changed, 440 insertions(+), 466 deletions(-)
```
Plus the NEW src/services/launchSurfaces.ts and src/services/fieldStatusView.ts (LF), the DELETED src/components/CohortBadge.tsx and __tests__/components/CohortBadge.test.tsx (E1), and the 13 E1b jest.mock deletions. Saved: <scratchpad>/S81-11_red/prototype.diff (git diff --binary + the two new files) and prototype_files/ (36 byte copies + SHA256SUMS.txt). Not done in the prototype (GREEN's): the remaining E-rows, the LoadingScreenVariants comment edits (C3 text only), CLAUDE.md (C21), gateRows.s11, the .snap block (E3).
- [tsc] tag=s11red-proto-tsc start=09:26:25 end=09:26:36 rc=2
- [tsc] tag=s11red-proto-tsc2 start=09:26:50 end=09:27:01 rc=0
- [eslint] tag=s11red-proto-eslint files=25 start=09:27:17 end=09:27:30 rc=0
- tsc: the first run (rc 2) named __tests__/components/CohortBadge.test.tsx (E1, deleted next) and HomeScreen data.reason on ComparisonResult (fixed with an any read); the second run rc 0.
- eslint: 0 errors, 153 warnings (pre-existing classes: unused vars in ResultsScreen, require imports in api.ts, Array<T> in types.ts).
- Prototype findings for the gate: (a) b3a honestCopy r31b goes RED on onboarding.s1.quote_1 because the spec KEYS-table AR carries a tanween (D-1); (b) ResultsScreen.networkMatrix.m18 pins the exact `t(friendlyErrorKey(parsed.code), { count: parsed.retryAfterSeconds })` call shape twice (E15 new, or GREEN keeps that literal shape and adds the CATEGORY_NOT_LIVE / reason arms around it); (c) ResultsContent.rewriteOrder pins the cohort anchor (E1e new); (d) HistoryScreen.bundleE.s3 pins the savings line (E8b new).

## 5. Mutation table (in place on byte copies; each restored + sha256-compared, all OK)
Spec mutants M4 and M27 (the event) are DELETED by R-S11-27. M21 is KILLED (not recorded equivalent). Added: M22b, M29-M42 for the rulings. 40 mutants: 39 KILLED (all by AssertionError), 1 SURVIVED (M36).
| M | mutant | result | killing rows (file :: test) | [jest] |
|---|---|---|---|---|
| M1 | categoryToSend ignores categories_live | KILLED | launchSurfaces.s11.test.ts :: fragrances ONLY when selected AND categories_live carries it; categoryRow.s11.test.tsx :: B6: chip selected + ABSENT version body -> no selected_category on text or link; categoryRow.s11.test.tsx :: B8b: a QUICK_CATS pick sets the chip but still sends only through the gate | [jest] tag=s11red-mut-M1 start=2026-11-05 09:35:35 end=2026-11-05 09:35:49 rc=1 |
| M2 | categoryToSend ignores the selection | KILLED | categoryRow.s11.test.tsx :: B8: chip NOT selected + categories_live [fragrances] -> no selected_category; launchSurfaces.s11.test.ts :: fragrances ONLY when selected AND categories_live carries it | [jest] tag=s11red-mut-M2 start=2026-11-05 09:35:49 end=2026-11-05 09:35:56 rc=1 |
| M3 | parseLaunchSurfaces truthy skincare test | KILLED | categoryRow.s11.test.tsx :: B4: invalid surfaces render no soon chip and a fragrance tap queues no coming-soon event; launchSurfaces.s11.test.ts :: surfaces: a chip is true ONLY for the boolean true; unknown keys ignored | [jest] tag=s11red-mut-M3 start=2026-11-05 09:35:56 end=2026-11-05 09:36:04 rc=1 |
| M5 | onComingSoon also calls onChange | KILLED | categoryRow.s11.test.tsx :: B3: a coming-soon tap -> the toast (+ iOS announcement), no event, no navigate, no compare | [jest] tag=s11red-mut-M5 start=2026-11-05 09:38:42 end=2026-11-05 09:38:50 rc=1 |
| M6 | the nudge kept beside the line | KILLED | categoryRow.s11.test.tsx :: renders exactly category-chip-fragrances and home-fragrance-only-line; no nudge | [jest] tag=s11red-mut-M6 start=2026-11-05 09:36:12 end=2026-11-05 09:36:20 rc=1 |
| M7 | recordLaunchSurfaces call removed | KILLED | launchSurfaces.s11.test.ts :: a body carrying categories_live is recorded; the gate decision is unchanged; launchSurfaces.s11.test.ts :: appVersionService records the parsed payload after the json parse, inside the try; launchSurfaces.s11.test.ts :: no other src file calls recordLaunchSurfaces, and launchSurfaces does no network | [jest] tag=s11red-mut-M7 start=2026-11-05 09:36:20 end=2026-11-05 09:36:30 rc=1 |
| M8 | record before the Expo Go return with its own fetch | KILLED | launchSurfaces.s11.test.ts :: Expo Go (no native version): no fetch AND the store stays ABSENT; launchSurfaces.s11.test.ts :: appVersionService records the parsed payload after the json parse, inside the try | [jest] tag=s11red-mut-M8 start=2026-11-05 09:36:30 end=2026-11-05 09:36:37 rc=1 |
| M9 | friendlyErrorKey CATEGORY_NOT_LIVE arm removed | KILLED | refusals.s11.test.tsx :: C1: a 400 renders the coming-soon Alert, never the Paywall; refusals.s11.test.tsx :: C2: a 429 (retry_after_seconds 3600, refusal_daily) renders the same Alert, no seconds; refusals.s11.test.tsx :: C1b: a success:false terminal carrying CATEGORY_NOT_LIVE renders the same Alert | [jest] tag=s11red-mut-M9 start=2026-11-05 09:36:37 end=2026-11-05 09:36:44 rc=1 |
| M10 | count passed on CATEGORY_NOT_LIVE + a {{count}} sentence | KILLED | refusals.s11.test.tsx :: C2: a 429 (retry_after_seconds 3600, refusal_daily) renders the same Alert, no seconds | [jest] tag=s11red-mut-M10 start=2026-11-05 09:36:44 end=2026-11-05 09:36:57 rc=1 |
| M11 | isUsageLimitError widened to any 429 | KILLED | refusals.s11.test.tsx :: C2: a 429 (retry_after_seconds 3600, refusal_daily) renders the same Alert, no seconds; refusals.s11.test.tsx :: a 429 renders the same Alert, no seconds, no Paywall; refusals.s11.test.tsx :: P4: RATE_LIMITED 429 with retry_after_seconds 5 keeps the seconds sentence | [jest] tag=s11red-mut-M11 start=2026-11-05 09:42:56 end=2026-11-05 09:43:04 rc=1 |
| M12 | SSE non-OK arm falls through to runRestCompare | KILLED | sseFallback.s11.test.ts :: D1: non-OK 400 with CATEGORY_NOT_LIVE -> onError once, ZERO REST calls; sseFallback.s11.test.ts :: D1b: the code under body.detail (legacy shape) is honoured too; sseFallback.s11.test.ts :: D2: non-OK 429 budget body -> onError once (status 429), ZERO REST calls | [jest] tag=s11red-mut-M12 start=2026-11-05 09:37:05 end=2026-11-05 09:37:14 rc=1 |
| M13 | SSE non-OK arm swallows every non-OK body | KILLED | sseFallback.s11.test.ts :: PIN P6: non-OK 500 with an unreadable body -> exactly ONE REST compare (today); sseFallback.s11.test.ts :: PIN P6b: non-OK 400 with ANOTHER code -> exactly ONE REST compare (today) | [jest] tag=s11red-mut-M13 start=2026-11-05 09:37:14 end=2026-11-05 09:37:22 rc=1 |
| M14 | camera CATEGORY_NOT_LIVE routed to timeout | KILLED | refusalsCamera.s11.test.tsx :: camera_refusal_body -> results-category-not-live-state with the two strings and Back; refusalsCamera.s11.test.tsx :: camera_budget_body -> results-category-not-live-state with the two strings and Back | [jest] tag=s11red-mut-M14 start=2026-11-05 09:37:22 end=2026-11-05 09:37:30 rc=1 |
| M15 | camera placeholder_identity routed to the reason state | KILLED | refusalsCamera.s11.test.tsx :: P7: action error with no code / no reason, placeholder_identity, low_confidence -> vision_failed | [jest] tag=s11red-mut-M15 start=2026-11-05 09:37:30 end=2026-11-05 09:37:37 rc=1 |
| M16 | INSUFFICIENT_DATA no_evidence mapped to a reason key | KILLED | refusals.s11.test.tsx :: P2: INSUFFICIENT_DATA with no reason / no_evidence / an unknown reason -> today; refusals.s11.test.tsx :: PIN: the single-argument results are unchanged (absent reason = today) | [jest] tag=s11red-mut-M16 start=2026-11-05 09:37:37 end=2026-11-05 09:37:46 rc=1 |
| M17 | priceProvenance converted window 7 d | KILLED | honestUnknowns.s11.test.tsx :: converted: 23 h fresh, 25 h stale; genuine: 6 d fresh, 8 d stale, 31 d unknown | [jest] tag=s11red-mut-M17 start=2026-11-05 09:37:46 end=2026-11-05 09:37:53 rc=1 |
| M18 | priceProvenance 30-day cap removed | KILLED | honestUnknowns.s11.test.tsx :: converted: 23 h fresh, 25 h stale; genuine: 6 d fresh, 8 d stale, 31 d unknown; honestUnknowns.s11.test.tsx :: R-S11-13: a STORED body with a date is listed (never aged out); without a date none; honestUnknowns.s11.test.tsx :: E3r: 2 d -> "<store>, as of <date>"; 10 d -> last seen; 31 d -> the honest line, no amount | [jest] tag=s11red-mut-M18 start=2026-11-05 09:37:53 end=2026-11-05 09:38:01 rc=1 |
| M19 | priceProvenance infers a date from source_method | KILLED | honestUnknowns.s11.test.tsx :: dates: no as_of anywhere -> none; field_status as_of used; price.as_of preferred; future -> fresh; unparsable -> none; honestUnknowns.s11.test.tsx :: R-S11-18: field_status stale with as_of null -> the dateless stale marker; honestUnknowns.s11.test.tsx :: R-S11-13: a STORED body with a date is listed (never aged out); without a date none | [jest] tag=s11red-mut-M19 start=2026-11-05 09:38:01 end=2026-11-05 09:38:09 rc=1 |
| M20 | priceProvenance ignores estimated | KILLED | honestUnknowns.s11.test.tsx :: R-S11-12: an estimate under field_status unknown/estimated is the honest line; absent field_status = none; honestUnknowns.s11.test.tsx :: R-S11-12: an estimate under field_status renders the honest line and NO amount | [jest] tag=s11red-mut-M20 start=2026-11-05 09:38:09 end=2026-11-05 09:38:17 rc=1 |
| M21 | ResultsContent passes honest always | KILLED | honestUnknowns.s11.test.tsx :: PIN P1 (M21): absent metadata -> no honest prop at all | [jest] tag=s11red-mut-M21 start=2026-11-05 09:38:50 end=2026-11-05 09:38:58 rc=1 |
| M22 | section line when available | KILLED | honestUnknowns.s11.test.tsx :: R-S11-21: the section line is for unavailable ONLY; honestUnknowns.s11.test.tsx :: section_status partial / unavailable / available -> sections {specs false, reviews true, pros_cons false} | [jest] tag=s11red-mut-M22 start=2026-11-05 09:38:58 end=2026-11-05 09:39:06 rc=1 |
| M22b | section line when partial (R-S11-21) | KILLED | honestUnknowns.s11.test.tsx :: R-S11-21: the section line is for unavailable ONLY; honestUnknowns.s11.test.tsx :: section_status partial / unavailable / available -> sections {specs false, reviews true, pros_cons false} | [jest] tag=s11red-mut-M22b start=2026-11-05 09:39:06 end=2026-11-05 09:39:13 rc=1 |
| M23 | field line even when the row exists | KILLED | honestUnknowns.s11.test.tsx :: E5r: size unknown + no size/volume row -> the field line; concentration unknown but listed -> none; honestUnknowns.s11.test.tsx :: E5r-b: a size unknown WITH a volume row -> no field line | [jest] tag=s11red-mut-M23 start=2026-11-05 09:39:13 end=2026-11-05 09:39:21 rc=1 |
| M24 | LoadingRings default restored to 2074 | KILLED | fabricated.s11.test.tsx :: A3: no counterTarget -> no counter chip and no digit at all; fabricated.s11.test.tsx :: A3b: showCounter alone (no target) still renders no chip; fabricated.s11.test.tsx :: A3c (R-S11-20): animated with no target never ticks a NaN or a number | [jest] tag=s11red-mut-M24 start=2026-11-05 09:39:21 end=2026-11-05 09:39:28 rc=1 |
| M25 | InviteeQuiz ?? 78 restored | KILLED | fabricated.s11.test.tsx :: A4: no scoring -> no quiz-match-score row and no 78%; fabricated.s11.test.tsx :: A4b: a non-finite overall is not a score either | [jest] tag=s11red-mut-M25 start=2026-11-05 09:39:28 end=2026-11-05 09:39:37 rc=1 |
| M26 | a savings banner composed again | KILLED | copy.s11.test.tsx :: even when getHomeSavings resolves a met threshold | [jest] tag=s11red-mut-M26 start=2026-11-05 09:39:37 end=2026-11-05 09:39:45 rc=1 |
| M28 | QUICK_CATS keeps a skincare tile | KILLED | categoryRow.s11.test.tsx :: QuickCategories renders exactly home-quick-cat-fragrances | [jest] tag=s11red-mut-M28 start=2026-11-05 09:39:45 end=2026-11-05 09:39:53 rc=1 |
| M29 | stored bodies aged out (R-S11-13) | KILLED | honestUnknowns.s11.test.tsx :: R-S11-13: a STORED body with a date is listed (never aged out); without a date none; honestUnknowns.s11.test.tsx :: R-S11-13: a STORED body renders the amount WITH its listed date, never aged out | [jest] tag=s11red-mut-M29 start=2026-11-05 09:39:53 end=2026-11-05 09:40:00 rc=1 |
| M30 | dateless stale marker dropped (R-S11-18) | KILLED | honestUnknowns.s11.test.tsx :: R-S11-18: field_status stale with as_of null -> the dateless stale marker; honestUnknowns.s11.test.tsx :: R-S11-18: field_status stale with as_of null -> the dateless checked-earlier marker | [jest] tag=s11red-mut-M30 start=2026-11-05 09:40:00 end=2026-11-05 09:40:09 rc=1 |
| M31 | as-of date on the ar-SA default calendar (R-S11-24) | KILLED | honestUnknowns.s11.test.tsx :: fieldStatusView names the gregorian calendar (Node ICU 77 defaults ar-SA to gregory; Hermes may not) | [jest] tag=s11red-mut-M31 start=2026-11-05 09:43:04 end=2026-11-05 09:43:12 rc=1 |
| M32 | error event drops reason (R-S11-26) | KILLED | sseFallback.s11.test.ts :: R-S11-26: the error event forwards its reason into the synthetic data | [jest] tag=s11red-mut-M32 start=2026-11-05 09:40:16 end=2026-11-05 09:40:24 rc=1 |
| M33 | parseApiError ignores the top-level reason (R-S11-26) | KILLED | sseFallback.s11.test.ts :: a top-level string reason is returned | [jest] tag=s11red-mut-M33 start=2026-11-05 09:40:24 end=2026-11-05 09:40:31 rc=1 |
| M34 | an estimate under field_status shows its amount (R-S11-12) | KILLED | honestUnknowns.s11.test.tsx :: R-S11-12: an estimate under field_status unknown/estimated is the honest line; absent field_status = none; honestUnknowns.s11.test.tsx :: R-S11-12: an estimate under field_status renders the honest line and NO amount | [jest] tag=s11red-mut-M34 start=2026-11-05 09:40:31 end=2026-11-05 09:40:39 rc=1 |
| M35 | no iOS announcement (R-S11-23) | KILLED | categoryRow.s11.test.tsx :: B3: a coming-soon tap -> the toast (+ iOS announcement), no event, no navigate, no compare | [jest] tag=s11red-mut-M35 start=2026-11-05 09:40:39 end=2026-11-05 09:40:47 rc=1 |
| M36 | counterTarget guard removed (R-S11-20) | SURVIVED | - | [jest] tag=s11red-mut-M36 start=2026-11-05 09:43:12 end=2026-11-05 09:43:20 rc=0 |
| M37 | the toast never hides | KILLED | categoryRow.s11.test.tsx :: B3: a coming-soon tap -> the toast (+ iOS announcement), no event, no navigate, no compare | [jest] tag=s11red-mut-M37 start=2026-11-05 09:40:55 end=2026-11-05 09:41:04 rc=1 |
| M38 | coming-soon chip marked disabled (R-S11-23) | KILLED | categoryRow.s11.test.tsx :: B2: surfaces {skincare, makeup} -> chips fragrances, skincare, makeup in order, both badged | [jest] tag=s11red-mut-M38 start=2026-11-05 09:41:04 end=2026-11-05 09:41:12 rc=1 |
| M39 | the line only when no chip is selected | KILLED | categoryRow.s11.test.tsx :: the line stays when the Fragrances chip is selected (both row states) | [jest] tag=s11red-mut-M39 start=2026-11-05 09:41:12 end=2026-11-05 09:41:20 rc=1 |
| M41 | CATEGORY_NOT_LIVE title arm removed | KILLED | refusals.s11.test.tsx :: C1: a 400 renders the coming-soon Alert, never the Paywall; refusals.s11.test.tsx :: C2: a 429 (retry_after_seconds 3600, refusal_daily) renders the same Alert, no seconds; refusals.s11.test.tsx :: C1b: a success:false terminal carrying CATEGORY_NOT_LIVE renders the same Alert | [jest] tag=s11red-mut-M41 start=2026-11-05 09:41:20 end=2026-11-05 09:41:28 rc=1 |
| M42 | camera CATEGORY_NOT_LIVE keeps the retry CTA | KILLED | refusalsCamera.s11.test.tsx :: camera_refusal_body -> results-category-not-live-state with the two strings and Back; refusalsCamera.s11.test.tsx :: camera_budget_body -> results-category-not-live-state with the two strings and Back | [jest] tag=s11red-mut-M42 start=2026-11-05 09:41:28 end=2026-11-05 09:41:36 rc=1 |
M36 (the R-S11-20 counterTarget guard removed): SURVIVED, proposed EQUIVALENT: with no target the chip is not rendered (showCounter && typeof counterTarget === number), so a NaN counter state can never reach the screen; the guard is defensive only. Ruling owed.
M11 note: its first run also hit a TypeError in P4 (alert not called); P4 now asserts the Alert call count first, and the rerun is a clean assertion kill.

## 6. Comm set
List: <scratchpad>/S81-11_red/COMM_SET.txt (268 entries: the spec jest_comm2.txt 232 suites, sha 85e99e2e...a0c9c verified; + 8 s11 files; + 23 SmartCompareApp-scanning backend pins; + 5 CLAUDE.md readers (test_ci_gates is in the 23: 6 readers in all)); reasons: comm_reasons.tsv. Deviation: the rulings cite 260 suites; the sha-verified list holds 232.
Base side REUSED (spec 1.10): [jest] tag=s11spec-base-comm start=2026-11-05 08:16:31 end=2026-11-05 08:17:54 rc=1 (232 suites, 2,400 passed / 4 failed = the four config/nativeBundle.w37 drift nodes, 13 pending); [pyt] tag=s11spec-be-c1 elapsed=62s status=OK rc=0 (1846 passed, 4 deselected); [pyt] tag=s11spec-be-c2 elapsed=15s status=OK rc=0 (458 passed). No suite outside the spec list was touched by the rows or the prototype, so no extra base run.
Head side (the prototype; 239 suites = 232 - CohortBadge.test + 8 s11; 10 chunks of <= 25, one jest at a time):
- [jest] tag=s11red-head-chunk_00 start=2026-11-05 09:28:05 end=2026-11-05 09:28:26 rc=1
- [jest] tag=s11red-head-chunk_01 start=2026-11-05 09:28:29 end=2026-11-05 09:28:44 rc=1
- [jest] tag=s11red-head-chunk_02 start=2026-11-05 09:28:47 end=2026-11-05 09:29:03 rc=1
- [jest] tag=s11red-head-chunk_03 start=2026-11-05 09:29:06 end=2026-11-05 09:29:20 rc=1
- [jest] tag=s11red-head-chunk_04 start=2026-11-05 09:29:23 end=2026-11-05 09:29:39 rc=1
- [jest] tag=s11red-head-chunk_05 start=2026-11-05 09:29:42 end=2026-11-05 09:29:57 rc=1
- [jest] tag=s11red-head-chunk_06 start=2026-11-05 09:30:00 end=2026-11-05 09:30:18 rc=1
- [jest] tag=s11red-head-chunk_07 start=2026-11-05 09:30:21 end=2026-11-05 09:30:37 rc=1
- [jest] tag=s11red-head-chunk_08 start=2026-11-05 09:30:39 end=2026-11-05 09:30:53 rc=1
- [jest] tag=s11red-head-chunk_09 start=2026-11-05 09:30:55 end=2026-11-05 09:31:09 rc=0
- [jest] tag=s11red-e1b start=2026-11-05 09:32:50 end=2026-11-05 09:33:08 rc=1
- head totals: 239 suites, 2,328 passed, 39 failed, 13 pending, 13 suites failing to LOAD (the E1b CohortBadge mocks); after the prototype E1b deletion the 13 suites load: 150 passed / 4 failed (E1c / E1e).
- [hermeticity] sentinel checked 1846 test(s)
- [netguard] blocked 39 attempt(s) from 29 node(s)
- ========= 1846 passed, 4 deselected, 13 warnings in 65.63s (0:01:05) ==========
- [hermeticity] sentinel checked 458 test(s)
- [netguard] blocked 24 attempt(s) from 2 node(s)
- ====================== 458 passed, 13 warnings in 14.34s ======================
Backend head == base (1846 / 458 passed, the same netguard counts 39/29 and 24/2): the events fence (test_events_allowlist_superset) stays green: no literal event name in src.
Sorted failed-node sets: base_failed.txt (4 = the w37 drift nodes), head_failed_final.txt (43). `comm -23` = EMPTY (every drift node fails at head too). `comm -13` = 39 nodes, EVERY one an E-row (0 unassigned; E_ROWS.tsv):
```
E-row	node
E8b NEW (History hero savings row, C9; not named in spec 4.1)	__tests__/HistoryScreen.bundleE.s3.test.tsx :: Bundle E S3 ? HistoryScreen JSX element-order (HistoryScreen.jsx 1-388) > HistoryHeroStats renders stat strip: decisions count + savings BHD
E9 + R-S11-15 (:382-401 two states)	__tests__/HomeScreen.bundleE.s3.integration.test.tsx :: HomeScreen S3 integration ? text compare flow via TwoInputShell > catfix D1 ? selected_category IS sent once a category chip is tapped
E9 + R-S11-15 (:382-401 two states)	__tests__/HomeScreen.bundleE.s3.integration.test.tsx :: catfix D1 ? category nudge visibility > hides the nudge once a category chip is tapped
E9 + R-S11-15 (:382-401 two states)	__tests__/HomeScreen.bundleE.s3.integration.test.tsx :: catfix D1 ? category nudge visibility > shows the nudge on first render (no category selected by default)
E11	__tests__/HomeScreen.bundleE.s3.test.tsx :: HomeScreen S3 ? JSX:438-651 editorial sections render flat-sibling order > the 4 editorial sections render in the JSX order Smart?Quick?Savings?Trending
E9 + R-S11-15 (:71-78 regex re-pinned to the categoryToSend form)	__tests__/HomeScreen.catfix.d1.test.tsx :: catfix D1 ? category nudge > en.json + ar.json both define home.categories.nudge
E9 + R-S11-15 (:71-78 regex re-pinned to the categoryToSend form)	__tests__/HomeScreen.catfix.d1.test.tsx :: catfix D1 ? category nudge > renders the nudge only when no category is selected
E9 + R-S11-15 (:71-78 regex re-pinned to the categoryToSend form)	__tests__/HomeScreen.catfix.d1.test.tsx :: catfix D1 ? category nudge > uses the home.categories.nudge i18n key (with a safe defaultValue)
E9 + R-S11-15 (:71-78 regex re-pinned to the categoryToSend form)	__tests__/HomeScreen.catfix.d1.test.tsx :: catfix D1 ? selected_category sent only when a chip is selected > stream + url paths use the conditional spread guard
E2	__tests__/InviteeQuizScreen.matchScore.m18.test.tsx :: InviteeQuizScreen ? match score reads the real scoring payload (M18 MB-contract-10) > keeps the 78 fallback ONLY when the payload carries no scores at all
E1d	__tests__/ReferralLandingScreen.redesign.test.tsx :: ReferralLandingScreen redesign ? Phase 4 Task 38 > renders the cohort badge slot when cohort_match has data
E1d	__tests__/ResultsScreen.bundleE.s3.test.tsx :: Bundle E S3 ? JSX element-order (ResultsScreen.jsx 1-410) > Cohort line renders via CohortBadge slot below the verdict (JSX 367-377)
E1d	__tests__/ResultsScreen.bundleE.s3.test.tsx :: Bundle E S3 ? JSX top-down element ORDER (lexical) > all anchors appear in JSX top-down order
E1d	__tests__/ResultsScreen.bundleE.s3.test.tsx :: Bundle E S3 ? JSX top-down element ORDER (lexical) > anchor #4 "results-cohort-badge-slot" appears in lexical order
E15 NEW (HomeScreen Alert-shape source regex :105-113 counts 2 call sites of the exact friendlyErrorKey(parsed.code), {count} form)	__tests__/ResultsScreen.networkMatrix.m18.test.ts :: HomeScreen ? MB-perf-03/MB-contract-02 (source) > the terminal error fallback on BOTH compare paths resolves copy from the code
E1d	__tests__/ResultsScreen.redesign.test.tsx :: ResultsScreen redesign ? Phase 3 Task 30 (source assertions) > imports CohortBadge from the new component
E1d	__tests__/ResultsScreen.redesign.test.tsx :: ResultsScreen redesign ? Phase 3 Task 30 (source assertions) > renders the cohort badge slot below the verdict block
E7	__tests__/ShareBottomSheet.redesign.test.tsx :: ShareBottomSheet ? i18n catalog > adds reward + toast keys EN + AR
E7	__tests__/ShareBottomSheet.redesign.test.tsx :: ShareBottomSheet ? i18n catalog > uses the design ? 4e toast copy "Sent to {{name}}. We'll add 5 more if they sign up."
E4 / E13 (r26); r31b = DEVIATION D-1 (AR copy, not an E-row)	__tests__/b3a/honestCopy.b3a.test.tsx :: B3-A honest copy (C4) > r26 the 12 changed values (and the A13 learning values) equal the fixture in EN and AR
E4 / E13 (r26); r31b = DEVIATION D-1 (AR copy, not an E-row)	__tests__/b3a/honestCopy.b3a.test.tsx :: B3-A honest copy (C4) > r31b (A8 / MR11) new and changed AR values carry no harakat, shadda or tanween outside the brand
E10 + R-S11-15 (:12 / :31 / :42 / :51)	__tests__/components/CategorySelector.test.tsx :: CategorySelector ? lucide glyphs > fires onChange with the category value when a chip is tapped
E10 + R-S11-15 (:12 / :31 / :42 / :51)	__tests__/components/CategorySelector.test.tsx :: CategorySelector ? lucide glyphs > marks the active chip via accessibilityState.selected
E10 + R-S11-15 (:12 / :31 / :42 / :51)	__tests__/components/CategorySelector.test.tsx :: CategorySelector ? lucide glyphs > renders a chip for each of the 9 categories
E10 + R-S11-15 (:12 / :31 / :42 / :51)	__tests__/components/CategorySelector.test.tsx :: CategorySelector ? lucide glyphs > renders a lucide icon next to each chip label (mock-icon host element)
E1c	__tests__/components/ResultsContent.render.test.tsx :: ResultsContent ? render coverage > renders cohort badge with peer count + governorate
E1c	__tests__/components/ResultsContent.render.test.tsx :: ResultsContent ? render coverage > renders the JSX top-down element order anchors
E1e NEW (not in spec 4.1: the cohort anchor in the rewrite-order rows)	__tests__/components/ResultsContent.rewriteOrder.test.tsx :: ResultsContent ? REWRITE element order per ResultsScreen.jsx > places cohort badge AFTER confidence pills (JSX 367-377)
E1e NEW (not in spec 4.1: the cohort anchor in the rewrite-order rows)	__tests__/components/ResultsContent.rewriteOrder.test.tsx :: ResultsContent ? REWRITE element order per ResultsScreen.jsx > renders all 8 anchor sections in the JSX top-down order
E5	__tests__/demographics.i18n.test.ts :: style profile i18n keys > basedOn includes {{count}} interpolation in BOTH languages
E5	__tests__/demographics.i18n.test.ts :: style profile i18n keys > en + ar both define "profile.styleProfile.basedOn"
E3	__tests__/hero/LoadingRings.test.tsx :: LoadingRings hero > renders default snapshot
E6	__tests__/i18n/brand.myez.s69.test.ts :: S69 U-R T1 ? catalog brand fence (MYEZ / ????) > every renamed value carries the brand and none of the copy-policy banned vocabulary
E6	__tests__/i18n/brand.myez.s69.test.ts :: S69 U-R T1 ? catalog brand fence (MYEZ / ????) > no blind replace: the other words containing ???? (??????, ?????????, ????? ?) are intact and ???? never sits inside a former ??????
E6	__tests__/i18n/brand.myez.s69.test.ts :: S69 U-R T1 ? catalog brand fence (MYEZ / ????) > standalone Arabic ?????? survives ONLY on the 10 verb keys (the brand uses are gone)
E6	__tests__/i18n/brand.myez.s69.test.ts :: S69 U-R T1 ? catalog brand fence (MYEZ / ????) > the ar values carrying standalone ?????? are exactly the same 27 brand keys (parity both ways)
E6	__tests__/i18n/brand.myez.s69.test.ts :: S69 U-R T1 ? catalog brand fence (MYEZ / ????) > the en values carrying MYEZ are exactly the 27 brand keys
E8	__tests__/i18n/priceDigits.crossScreen.w414.test.ts :: W4-14 price / count digits under lng=ar > PIN 13: Results price, History hero savings, History count and Home savings count carry one digit class (ASCII, no U+0660-0669/U+06F0-06F9)
E1d	__tests__/screens/ResultsScreen.bundle_c_integration.test.tsx :: ResultsScreen Bundle C integration ? confidence pills + chip > does NOT remove CohortBadge (spec ? 7d ? stays separate from personalization chip)
E1	__tests__/components/CohortBadge.test.tsx :: <whole file deleted by the prototype; base nodes in jest_base.json>
E1b	__tests__/ResultsContent.confidenceSheet.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/ResultsContent.imageUrl.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/ResultsContent.partialNote.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/ResultsContent.perCategory.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/ResultsContent.scoreGuard.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/ResultsContent.specsComparisonShape.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/ResultsContent.v2Wiring.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/clientTruth/medicalNote.s74.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/components/ResultsContent.a11y.w311.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1c	__tests__/components/ResultsContent.render.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1e NEW (not in spec 4.1: the cohort anchor in the rewrite-order rows)	__tests__/components/ResultsContent.rewriteOrder.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/components/ResultsContent.runnerUp.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
E1b	__tests__/screens/ResultsScreen.degraded.s69.test.tsx :: <SUITE LOAD FAILURE>  (masked at head before the E1b mock deletion; after it the suite loads, see the e1b run)
```
E-rows measured GREEN at head (no edit needed, R-S11-37): E12 clientTruth/shareTruth.s74, E13 HomeScreen.currentDesign.contract / HomeScreen.redesign / onboarding/Step01Welcome, E14 errorCopy.a11 / errorCopy.w314 / errorCopy.engineUnavailable.s69, hero/LoadingRings.animation (R-S11-20), honestCounts.s69, i18n/plurals + pluralFamilies.fence.w311 (R-S11-11), HomeScreen.errorCopy.a11, HomeScreen.rateLimitedSeconds.w314, appVersionService.a9. The E1 node ids (CohortBadge.test, 6 nodes) are in jest_base.json.

## 7. Deviations from the spec / rulings (reported, not silently changed)
- D-1 (copy fence): the spec KEYS-table AR for onboarding.s1.quote_1 carries a tanween; b3a/honestCopy.b3a r31b (A8 / MR11) forbids harakat / shadda / tanween in new or changed AR values of the b3a keys and goes RED at head. Several other spec AR cells carry tanween / shadda (not b3a-scoped). Ruling owed: drop the marks or E-row r31b.
- D-2: a ninth RED file refusalsCamera.s11.test.tsx (the camera harness differs from the Home harness).
- D-3: the comm list is 232 suites (sha-verified jest_comm2.txt), not 260 as the rulings say.
- D-4: new E-rows not in spec 4.1: E1e ResultsContent.rewriteOrder (2 nodes), E8b HistoryScreen.bundleE.s3 (1), E15 ResultsScreen.networkMatrix.m18 (1, avoidable if GREEN keeps the literal call shape).
- D-5: the R-S11-24 gregorian row cannot be behavioural on this runtime (Node 24 / ICU 77 resolves ar-SA to the gregorian calendar), so a static source row pins the explicit calendar; Hermes behaviour is unmeasured (L10 / owner device check).
- D-6: AR literals in the RED files are \u escapes produced by a script from tool-decoded text (asciify.py), not typed escapes; bytes verified 0 > 127.
- D-7: A2 is static (source tokens + slot testID) plus the A1 module absence; no ResultsContent render with cohort data (the CohortBadge mock cannot exist at head).
- D-8: home.errors.categoryNotLive EN (spec) says "More categories are coming soon." -- R-S11-29(a) accepts "More categories are coming."; the App-Review adversary should re-read "soon".

## 8. Restore check
`git status --short` at the end: `?? SmartCompareApp/__tests__/s11/` only (.qa-mutation.lock removed); `git diff --quiet` rc 0; snap.py restore: 36 paths, 0 sha mismatches (the 2 new src files removed, the 2 deleted files restored). No orphan jest / pytest (each run was a foreground bounded call).

## 9. Files
<scratchpad>/S81-11_red/: notes.md, RED_REPORT.md, COMM_SET.txt, comm_reasons.tsv, E_ROWS.tsv, NATIVE_READ_DRAFT.md, mutation_table.json, mut/*.json, base_final.json + base_final_nodes.txt, proto2.json, s11red-head/chunk_*.json, base_failed.txt, head_failed_final.txt, comm13.txt, comm23.txt, prototype.diff, prototype_diffstat.txt, prototype_files/, bytes/, pyt_be_c1_head.log, pyt_be_c2_head.log, tsc_proto.log, eslint_proto.log, jest_lines.txt.
