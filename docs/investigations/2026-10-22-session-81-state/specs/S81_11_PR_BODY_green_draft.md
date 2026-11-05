# S81-11 HONEST-FRAGRANCE-UI (+ D20 HONEST UNKNOWNS)

Base `6869a3e6` (origin/main) -> HEAD `5fcb9fba` on `feature/s81-s11-honest-fragrance-ui` (one commit, through the pre-commit hook). A CLIENT FOCUS unit: no runtime flag, no `features.ts` constant. It merges now and ships ONLY in the first post-approval OTA together with S81-08 and the consent v3 copy (UB-R4); that OTA is the flip precondition of `ENABLE_FRAGRANCE_ONLY_GATE` (R-S10-14). Spec `.qa-s80/S81-11_UNIT_SPEC.md` (sha256 2e3529a3...), RULINGS_S81_11 (R-S11-11..41, the brief's R-S11-1..10 beneath), GATE_S81_11 (GC-1..GC-16).

## The unit: changes -> RED rows -> no flag -> the OTA slot

| change | what | RED rows (frozen, `SmartCompareApp/__tests__/s11/`) |
|---|---|---|
| C1 / A | `CohortBadge.tsx` deleted (Results, ReferralLanding; R-S11-31) | fabricated.s11 A1 / A2 |
| C2 | InviteeQuiz: no scores (or a non-finite overall) = no match-score row; the 78 fallback is gone | fabricated.s11 A4 / A4b + PIN 91% |
| C3 | LoadingRings: no `counterTarget` default; the chip renders only for a numeric target; guarded init (R-S11-20) | fabricated.s11 A3 / A3b / A3c / A3d + 2 PINs |
| C4 / C5 | NEW `src/services/launchSurfaces.ts` (parse / record / get / subscribe / useLaunchSurfaces / categoryToSend; no event constant, R-S11-27); `checkForcedUpdate` records the parsed body after the json parse (the Expo Go early return unchanged, R-S11-19) | launchSurfaces.s11 (13) |
| C6 / C7 / C11 | the row: ONE Fragrances chip (unselected by default) + "Fragrances only for now" in both states; Skincare / Makeup only under `surfaces` as enabled coming-soon chips (badge, accessibility hint, 2.5 s inline toast, iOS `announceForAccessibility`, R-S11-23); QUICK_CATS = one tile; the nudge deleted; both send sites through `categoryToSend` (R-S11-3 / R-S11-34) | categoryRow.s11 B1-B8b |
| C7 / C8 / C9 | the savings banner, Profile tile and History line removed (R-S11-6); the six `home.savings.count_*` keys kept (R-S11-11) | copy.s11 A6, fabricated.s11 A6 |
| C10 / C15 / C16 | NEW `src/services/fieldStatusView.ts`; ResultsContent price provenance (honest line / as of / last seen / listed on / checked earlier; `resultOrigin` live vs stored); ResultsAccordion optional `honest` prop (section line for `unavailable` only; size / concentration field lines), passed ONLY when metadata carries section_status or field_status | honestUnknowns.s11 (31) |
| C12 / C13 / C14 | `friendlyErrorKey(code, reason?)` + the CATEGORY_NOT_LIVE arms; parseApiError reads `reason` top-level then `detail`; the SSE non-OK arm split (CATEGORY_NOT_LIVE -> onError, no REST); reason forwarded from both terminal frames and the error event; the camera category_not_live / reason states | refusals.s11 (22), refusalsCamera.s11 (6), sseFallback.s11 (16) |
| C17 | types: `ProductPrice.as_of`, `metadata.field_status` / `section_status`, top-level `reason` (additive optional) | tsc |
| C18 | catalogs (CRLF kept): 15 added / 10 changed / 17 deleted keys, 1,011 leaves each, parity 0; every new or changed AR value without harakat, shadda or tanween (GC-4) | copy.s11 (12) |
| C21 | CLAUDE.md: one column-0 block after the S81-G5 block + the :341 pointer clause | the 6 CLAUDE.md readers |

Absent `categories_live` / `surfaces` / `field_status` / `section_status` / `as_of` / `reason` = today's requests and today's render (the PIN rows of the RED files, per surface).

## E-rows (test files only; every edit carries an `S81-11 (E<n>)` comment)

| E | file | change |
|---|---|---|
| E1 | components/CohortBadge.test.tsx | deleted with the component |
| E1b | 13 files: the `jest.mock(.../CohortBadge)` block (incl. the medicalNote.s74 fence: the mock only) | replaced by a one-line comment |
| E1c | components/ResultsContent.render | anchor dropped; the two cohort rows -> "renders NO cohort badge slot" |
| E1d | ResultsScreen.bundleE.s3, ResultsScreen.redesign, screens/ResultsScreen.bundle_c_integration, ReferralLandingScreen.redesign | each cohort pin inverted to absence; the s3 anchor list drops the slot |
| E1e | components/ResultsContent.rewriteOrder | anchor dropped; the order row -> the slot is absent |
| E2 | InviteeQuizScreen.matchScore.m18 | "renders NO match score when the payload carries no scores" |
| E3 | hero/LoadingRings.test + its .snap | the default-snapshot row deleted and its export block hand-deleted (no `jest -u`) |
| E4 / E13 | fixtures/b3a_copy.json | the two orphan keys out of the learning list and both maps; the three quotes follow the new copy |
| E5 | demographics.i18n | basedOn out of REQUIRED_KEYS; its {{count}} row deleted |
| E6 | i18n/brand.myez.s69 | basedOn out of BRAND_KEYS (the count keys stay); 27 -> 26 in two titles + the comment |
| E7 | ShareBottomSheet.redesign | toast.confirm out of the list; the copy row -> an absence row |
| E8 | i18n/priceDigits.crossScreen.w414 | PIN 13 loses the History savings clause |
| E8b | HistoryScreen.bundleE.s3 | the stat strip row pins NO savings key |
| E9 | HomeScreen.catfix.d1, HomeScreen.bundleE.s3.integration | the spread regex re-pinned to `sendCategory` (count >= 2, plus `categoryToSend(selectedCategory, launchSurfaces)` twice); nudge rows -> the fragrance-only line in both chip states; the chip-tap row in two states (no version body: `{}`; categories_live: fragrances) |
| E10 | components/CategorySelector | one chip / one icon without surfaces; the pressed and selected chip is fragrances |
| E11 | HomeScreen.bundleE.s3 | the editorial order row: Smart -> Quick -> Trending, SavingsBanner absent |
| E15 | ResultsScreen.networkMatrix.m18 | the Alert-shape regex re-pointed to the reason-aware form (CATEGORY_NOT_LIVE without the count; the rest `friendlyErrorKey(parsed.code, parsed.reason)` + count), still exactly 2 sites |

E12 / E14 and the other E11 / E13 readers measured green with no edit.

## Counts and gates (every tool by path through the junction: node v24.11.1, jest 29.7.0, typescript 5.9.3, eslint v9.39.4)

- RED: 124 nodes in 8 files, 124 / 124 green at HEAD (`[jest] tag=s11green-red1 ... rc=0`); the eight files byte-identical to GC-1 (re-hashed before and after the commit). At base: 96 RED fail by assertion / 28 PIN pass (GC-2).
- Mutants (the RED round): 40 applied, 39 KILLED, M36 (the counterTarget guard) EQUIVALENT by ruling (GC-3). The adversaries re-apply at least ten.
- In-band order pairs, both orders (an order-preserving `--testSequencer`, GC-12): categoryRow.s11 x HomeScreen.bundleE.s3.integration, refusals.s11 x HomeScreen.errorCopy.a11, honestUnknowns.s11 x components/ResultsContent.render, sseFallback.s11 x api.streamComparison.expoFetch, refusals.s11 x errorCopy.a11, launchSurfaces.s11 x appVersionService.a9, refusalsCamera.s11 x screens/camera.engineUnavailable.s69: 14 runs, all rc 0; one in-band run of the touched set: 51 suites, 677 passed.
- tsc `--noEmit` rc 0; eslint over the 55 changed / new ts(x) files: 0 errors (warnings of the pre-existing classes).
- Jest comm set: the RED's 240 jest entries minus the deleted CohortBadge.test = 239 suites in 10 chunks of <= 25: the only failures are the four `config/nativeBundle.w37` drift nodes, as at base: `comm -13` EMPTY, `comm -23` EMPTY.
- Backend (pyt.py, the only pytest of the round): the 23 SmartCompareApp-scanning pins `[pyt] tag=s11green-be-c1 elapsed=71s status=OK rc=0` (1846 passed, 4 deselected; netguard 39 / 29 as at base) and the 6 CLAUDE.md readers `[pyt] tag=s11green-be-c2 elapsed=16s status=OK rc=0` (458 passed); base = the spec's [pyt] lines (1846 / 458): `comm -13` EMPTY. test_events_allowlist_superset stays green (no event literal in src).
- Copy fences: en / ar 1,011 / 1,011, parity 0; .copy-policy.json, i18n parity and the b3a honestCopy fence green; no forbidden EN word and no forbidden AR pair in any new or changed value; no EN digit outside a placeholder; GC-4 diacritics: 0 hits.
- Footprint (GC-14): the 2 new leaves, 16 edited src files, the 2 catalogs, CohortBadge.tsx deleted, the E-row test files (+ fixtures/b3a_copy.json, + the hand-edited .snap), the 8 RED files, CLAUDE.md. No package.json / package-lock.json / app.json / native / .env / app/ / scripts/ / migrations/ / tests/*.py change. New files ASCII + LF; CRLF kept in every existing file (`git diff --stat` shows hunks only).
- NOT RUN by ruling (R-S11-1 / R-S11-38): the R8 pair, paid-route metering as a gate, the hook test files, a pytest CI-order set, the corpus gate, a base scratch worktree. The FULL jest suite: NOT run (LC-7: the final round).

Gate logs: `S81_11_GREEN_GATE_LOGS.txt`; the RED mutation table: `S81_11_RED_REPORT.md` section 5 (+ `mutation_table.json`); the Arabic list: `S81_11_NATIVE_READ.md` (all filed under `specs/` by the orchestrator).

## Stated limits

- L1 the other unreferenced catalog keys stay (a cleanup follow-up).
- L2 `surfaces` is absent until SF1: the coming-soon chips and the toast are dormant code, exercised only on synthetic bodies.
- L3 every D20 / reason rendering is dormant until its backend flag flips: field_status (ENABLE_FIELD_STATUS_METADATA), section_status (ENABLE_RESULT_STATUS_METADATA), as_of (ENABLE_KB_FIRST_SERVE), reason (S81-20 / ENABLE_RESULT_GATE).
- L4 the launch store is per JS session: a flip is seen after the next launch; Expo Go never reads it (ABSENT).
- L5 no replacement for the removed counters until S81-11b; the Profile strip shows two tiles.
- L6 the field-level honest line covers size and concentration only; other unknowns rely on the section line and the existing placeholders.
- L8 the SSE transport is OFF in production until G6b: the CATEGORY_NOT_LIVE non-OK arm is exercised by tests only until then.
- L9 build 3 keeps its generic copy on CATEGORY_NOT_LIVE until this OTA, so the gate flip waits for propagation.
- L10 no device E2E in the unit (owner TestFlight check).
- L11 the device clock drives fresh / last seen (a future as_of is clamped to fresh).
- S81-11-L12 a KB price shows the merchant host as the store label until kb_merchants carries a display name (S81-18b).
- S81-11-L13 between this OTA and the gate flip the row says fragrances while the gate-OFF backend still compares every category.
- S81-11-L14 the `category_coming_soon_tap` event waits for SF1 / S81-11c (with the VALID_EVENT_TYPES widening).
- S81-11-L15 the App-Review reading of the coming-soon copy rests on owner steps 3 and 4 (no date and no feature is promised).
- S81-11-L16 the Hermes gregorian date is unmeasured on device (Node ICU 77 already resolves ar-SA to gregory; the explicit calendar option is pinned statically).

## Owner steps (names only; a dated ledger line per step)

1. The OTA slot: the FIRST post-approval OTA, with S81-08 + consent v3, from a main holding every client unit; run `npm ls` then `npm ci` in `SmartCompareApp/` first (the installed expo 54.0.34 drifts from the pinned ~54.0.37). Nothing reaches a phone before approval (UB-R4).
2. The flip order (R-S11-9): `ENABLE_FRAGRANCE_ONLY_GATE` only after this OTA has propagated (two launches); `ENABLE_FIELD_STATUS_METADATA` with or after it; `ENABLE_RESULT_GATE` after it.
3. Keep `surfaces` OFF in every App Review window (SF1 must not ship it on during a review).
4. Align the App Store Connect description and screenshots to the fragrance-only launch before the 1.0.1 submission.
5. The TestFlight device check: the one-chip row and the line (EN + AR, a narrow RTL screen), a fragrance compare, the honest lines and the Hermes Arabic as-of date once the G3 / G4 flags are on, a non-fragrance pair after the flip (text, link, camera: the coming-soon copy, never the Paywall).
6. SF1 carries the `surfaces` contract (an object of `skincare` / `makeup` booleans; only the boolean `true` counts) and the VALID_EVENT_TYPES widening with the event (S81-11c).

## [NATIVE READ]

Every added or changed Arabic string (15 added, 10 changed), the diacritics note and the month-name rule: `specs/S81_11_NATIVE_READ.md` (the S81_10_NATIVE_READ.md format: key | EN | AR | note). The Arabic script lives only there; this body stays ASCII.

## Deviations (reported, not silent)

- Key counts: 15 added / 10 changed / 17 deleted (the gate wording "12 added / 7 changed" counts the spec KEYS table only; the three ruling keys `results.price.listedOn` / `listedOnNoStore` / `checkedEarlier` and the three reworded keys insufficientData / comparison / s17 make 15 / 10); the leaf count 1,011 per catalog is the gate's.
- `onboarding.s1.quote_3` AR re-cut a second time: the spec text carried the standalone verb that the b3a r31 brand fence forbids in a changed value, so the AR reads "know the difference in size and price" (EN unchanged).
- Test titles renamed with their rows: E1c, E1d, E1e, E2, E6 (27 -> 26), E7, E8, E8b, E10 keeps its titles, E11; the s3 anchor list shrinks by one it.each node.
- The commit trailer names the committing model (Claude Opus 5.5).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
