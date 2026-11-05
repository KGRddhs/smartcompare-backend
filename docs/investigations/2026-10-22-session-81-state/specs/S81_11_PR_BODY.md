# S81-11 HONEST-FRAGRANCE-UI (+ D20 HONEST UNKNOWNS)

Base `6869a3e6` (origin/main, fetched 2026-11-05 11:41 AST: unmoved, nothing replayed) -> HEAD `04270c90` on `feature/s81-s11-honest-fragrance-ui`: two commits, GREEN `5fcb9fba` + the final round `04270c90` (test + docs only), both through the pre-commit hook. A CLIENT FOCUS unit: no runtime flag, no `features.ts` constant. It merges now and ships ONLY in the first post-approval OTA together with S81-08 and the consent v3 copy (UB-R4); that OTA is the flip precondition of `ENABLE_FRAGRANCE_ONLY_GATE` (R-S10-14). Rulings: RULINGS_S81_11 (R-S11-11..41, the brief's R-S11-1..10 beneath), GATE_S81_11 (GC-1..GC-16), RULINGS_REBASE_S81_11 (RB-S11-1..12). Reports (filed under `specs/` by the orchestrator): S81_11_RED_REPORT.md, S81_11_GREEN_REPORT.md, S81_11_ADV1_correctness.md, S81_11_ADV2_appreview.md, the final round's REBASE_REPORT, S81_11_NATIVE_READ.md.

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
| C21 | CLAUDE.md: one column-0 block after the S81-G5 block + the :341 pointer clause (GREEN); the final round edits the block in place (counts, OFF identity, resultOrigin, owner steps, L15 / L17-L23) and rewrites the Frontend "CohortBadge inline below verdict" sentence in place, dated (RB-S11-3..7) | the 6 CLAUDE.md readers |
| GR | NEW `__tests__/s11/gateRows.s11.test.tsx` (final round, RB-S11-2): G11-GR1..GR4 | the gate rows (11 nodes) |

Absent `categories_live` / `surfaces` / `reason` = today's requests and Alerts. The exact OFF identity of the Results card (RB-S11-4): today's rendering is byte-identical ONLY when the body carries NO `metadata.field_status` / `section_status` AND NO `price.as_of`; a `price.as_of` alone (`ENABLE_KB_FIRST_SERVE` ON, R-G4-2) adds the as-of / listed-on line and, on a LIVE body older than 30 days, the honest line in place of the amount (the owner's 30-day rule, R-S11-5); so `ENABLE_KB_FIRST_SERVE` is render-changing for this OTA and flips only after it. ResultsContent is reached only through the Results entry; the invitee quiz and a shared result render their own screens without D20 (RB-S11-7).

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

## Gate rows (final round, RB-S11-2; test-only)

`SmartCompareApp/__tests__/s11/gateRows.s11.test.tsx` (NEW, 546 lines, pure ASCII, LF, sha256 b13b1c4ca19289a8badebb7faa04c19d1acf9b49de60d39ef5e61b609e273a82; no new copy key, nothing rendered by a new module). Four rows in 11 jest nodes, all green at HEAD; each proven RED on a sha-verified byte copy of the source file carrying the correctness adversary's edit, under `.qa-mutation.lock`, restored sha256-equal:

| row | pins | mutant (file) | killing nodes |
|---|---|---|---|
| G11-GR1 | a Link compare answered 200 success:false with a top-level INSUFFICIENT_DATA reason renders the per-reason sentence (`friendlyErrorKey(code, response.data.reason)`); no reason / no_evidence = the generic sentence | O3, the reason dropped (HomeScreen.tsx) | 3 (same_identity, placeholder_identity, category_conflict) |
| G11-GR2 | under field_status price unknown (and a live converted price over 30 days) the honest line renders and the converted-USD caption does NOT; the other card keeps its caption | O10, the caption under the honest line (ResultsContent.tsx) | 2 |
| G11-GR3 | the dateless marker (results.price.checkedEarlier, `-checked-`) renders only for a LIVE body whose field_status price is `stale` with as_of null; a STORED body renders the amount with no marker; fresh / unknown / known entries never render it | O11, staleNoDate on stored bodies; O18, staleNoDate on any entry (fieldStatusView.ts) | 1 each |
| G11-GR4 | the coming-soon toast calls `AccessibilityInfo.announceForAccessibility` on iOS (once, the toast text) and NOT on Android, where the toast carries `accessibilityLiveRegion="polite"` | O14, the announcement on both platforms (HomeScreen.tsx) | 1 |

The eight frozen RED files are byte-identical to GC-1 (re-hashed on disk and as HEAD blobs before and after the round commit, all eight equal to the GC-1 sha256 values); every GREEN file except CLAUDE.md is byte-identical to the GREEN sha table (62 rows, 0 mismatches).

## Counts and gates (final round; every tool by path through the junction: node v24.11.1, jest 29.7.0, typescript 5.9.3, eslint v9.39.4)

- RED + gate rows: 9 files, 135 / 135 green (124 RED + 11 gate-row nodes; `[jest] tag=s11final-red9 rc=0`). At base the RED is 96 fail by assertion / 28 PIN pass (GC-2).
- Mutants: the RED round's 40 (39 KILLED, M36 EQUIVALENT by ruling, GC-3); the correctness adversary's 37 (19 RED re-applies + 18 own: 13 KILLED, 5 prove-nothing survivors O3 / O10 / O11 / O14 / O18), all five now KILLED by the gate rows (`[jest] tag=s11final-mut-O3 / O10 / O11 / O14 / O18 rc=1`, assertion failures, restored sha-equal).
- In-band order pairs, both orders (the GREEN's order-preserving `--testSequencer`): the GREEN's seven pairs + gateRows x HomeScreen.errorCopy.a11 + gateRows x honestUnknowns.s11: 18 runs, all rc 0; one in-band run of the touched set + the gate rows: 52 suites, 688 passed (`s11final-inband-touched2 rc=0`).
- tsc `--noEmit` rc 0 (`s11final-tsc`); eslint over the 56 changed ts(x) files incl. the new one: 0 errors, 270 warnings of the pre-existing classes (require-style mocks, import/first).
- Jest comm set: the GREEN's 239 suites (the RED's 240 jest entries minus the deleted CohortBadge.test, incl. the 8 s11 files) + gateRows = 240 suites in 10 chunks of <= 25 at HEAD: 2,524 passed, 13 pending, 4 failed = exactly the four `config/nativeBundle.w37` drift nodes; base (reused from the spec / RED / GREEN records) = the same four: `comm -13` EMPTY, `comm -23` EMPTY.
- Backend (pyt.py, the only pytest of the round): the 23 SmartCompareApp-scanning pins `[pyt] tag=s11final-be-c1 elapsed=127s status=OK rc=0` (1,846 passed, 4 deselected; netguard 39 / 29) and the CLAUDE.md readers `[pyt] tag=s11final-be-c2 elapsed=34s status=OK rc=0` (458 passed; netguard 24 / 2); with test_ci_gates in c1 these are the 6 readers. Base 1,846 / 458: `comm -13` EMPTY.
- Copy fences: en / ar 1,011 / 1,011 leaves, parity 0; 15 added / 10 changed / 17 deleted keys (RB-S11-3); `copy-policy.test.ts` and the b3a honestCopy fence green (comm set); no forbidden EN or AR word; GC-4 diacritics 0 hits (the catalogs are unchanged by the final round).
- FULL jest ONCE (LC-7, the arbiter; `[jest] tag=s11final-full rc=1`, read from full.json): 410 suites, 4,006 tests: 3,976 passed, 4 failed = exactly the four `config/nativeBundle.w37` drift nodes, 13 pending, 13 todo; snapshots 41 matched, 0 added / updated / unmatched / unchecked, 0 files removed. 3,976 = the 3,852 baseline + 124 RED + 11 gate rows - 11 nodes the GREEN's E-rows removed (CohortBadge.test 6, E1c 1, E3 1, E5 1, the s3 anchor it.each 1, one parametrised node).
- Footprint vs `6869a3e6`: 63 paths = the GREEN's 62 + the gate-rows file; hunks only on existing files; no package.json / package-lock.json / app.json / native / .env / app/ / scripts/ / migrations/ / tests/*.py change; the only .snap change is the GREEN's hand-deleted E3 block (147 lines); `git status --short` empty.
- NOT RUN by ruling (RB-S11-9; a client unit: no app/, scripts/, migrations/ or .githooks file): the R8 sentry pair, tests/test_paid_route_metering.py as a separate flag-on/off gate (it runs inside the 23 pins), the pre-commit hook test files (the unit touches no .githooks file), a pytest CI-order set, the corpus gate, a base scratch worktree (it would need a junction).

Gate logs and the mutation table: the final round's REBASE_REPORT; GREEN: S81_11_GREEN_GATE_LOGS.txt; RED: S81_11_RED_REPORT.md section 5.

## Stated limits

- L1 the other unreferenced catalog keys stay (a cleanup follow-up).
- L2 `surfaces` is absent until SF1: the coming-soon chips and the toast are dormant code, exercised only on synthetic bodies.
- L3 every D20 / reason rendering is dormant until its backend flag flips: field_status (ENABLE_FIELD_STATUS_METADATA), section_status (ENABLE_RESULT_STATUS_METADATA), as_of (ENABLE_KB_FIRST_SERVE), reason (S81-20 / ENABLE_RESULT_GATE).
- L4 the launch store is per JS session: a flip is seen after the next launch; Expo Go never reads it (ABSENT).
- L5 no replacement for the removed counters until S81-11b; the Profile strip shows two tiles.
- L6 the field-level honest line covers size and concentration only.
- L8 the SSE transport is OFF in production until G6b: the CATEGORY_NOT_LIVE non-OK arm is exercised by tests only until then.
- L9 build 3 keeps its generic copy on CATEGORY_NOT_LIVE until this OTA, so the gate flip waits for propagation.
- L10 no device E2E in the unit (owner TestFlight check).
- L11 the device clock drives fresh / last seen (a future as_of is clamped to fresh).
- S81-11-L12 a KB price shows the merchant host as the store label until kb_merchants carries a display name (S81-18b).
- S81-11-L13 between this OTA and the gate flip the row says fragrances while the gate-OFF backend still compares every category.
- S81-11-L14 the `category_coming_soon_tap` event waits for SF1 / S81-11c.
- S81-11-L15 SF1 turns `surfaces` on only when the same chips would pass in front of a reviewer (owner steps 3 and 4).
- S81-11-L16 the Hermes gregorian date is unmeasured on device (Node ICU 77 already resolves ar-SA to gregory; the explicit calendar option is pinned statically).
- S81-11-L17 the 1.0.0 listing's Description and Keywords name seven categories until the 1.0.1 metadata is live: the Promotional Text is updated at the OTA, 1.0.1 is submitted aligned promptly, and ENABLE_FRAGRANCE_ONLY_GATE flips preferably after the 1.0.1 metadata is live, or after the owner's recorded acceptance of the window (MINOR-1).
- S81-11-L18 the as-of line shows month and day, no year (MINOR-6).
- S81-11-L19 a live body with `price.as_of` older than 30 days and no field_status renders the honest line in place of the amount (the owner's rule; dormant until ENABLE_KB_FIRST_SERVE) (MINOR-7, m4).
- S81-11-L20 the `PersonalizationChip.tsx` header comment still names the deleted badge (the cleanup follow-up; no src edit in the final round, m6).
- S81-11-L21 a field_status price `unknown` beside a showable-shaped amount that `price_is_showable` rejects renders the bare amount (m2).
- S81-11-L22 a `stale` entry with reason `unmarked` renders the dateless marker (m3).
- S81-11-L23 TrendingNearYou can offer a non-fragrance pair that the gate refuses with the coming-soon copy after the flip; not in this unit (m7).

## Adversaries (both SOUND; RB-S11-1: every finding a MINOR, no src change in the final round)

- Correctness: 0 blocking / 0 major / 7 minors. m1 (five prove-nothing survivors) -> the gate rows G11-GR1..GR4, all five KILLED; m2 -> L21; m3 -> L22; m4 (the OFF identity wording) -> the CLAUDE.md block and this body reworded in place, ENABLE_KB_FIRST_SERVE named in the flip order, L19; m5 (key counts) -> 15 / 10 / 17 is the record (RB-S11-3); m6 -> the CLAUDE.md Frontend sentence rewritten in place (dated) + L20; m7 -> L23.
- App Review: 0 blocking / 0 major / 9 minors. MINOR-1 -> L17 + owner step 4; MINOR-2 -> L15 reworded; MINOR-6 -> L18; MINOR-7 -> L19. Notes, no change: MINOR-3 (the "coming soon" wording stands, GC-9), MINOR-4 ("for now" twice: cosmetic, the title is the RED's), MINOR-5 (a long host truncates the one-line as-of row in narrow RTL: owner step 5), MINOR-8 (nominative brand names in the examples, as the base's iPhone / Galaxy), MINOR-9 (the Soon chips' one-word hint; dormant).

## Owner steps (names only; a dated ledger line per step)

1. The OTA slot: the FIRST post-approval OTA, with S81-08 + consent v3, from a main holding every client unit; run `npm ls` then `npm ci` in `SmartCompareApp/` first. Nothing reaches a phone before approval (UB-R4).
2. The flip order (R-S11-9 / RB-S11-12): ENABLE_FRAGRANCE_ONLY_GATE only after this OTA has propagated (two launches) and preferably after the 1.0.1 metadata is live (L17); ENABLE_FIELD_STATUS_METADATA with or after it; ENABLE_RESULT_GATE after it; ENABLE_KB_FIRST_SERVE is render-changing for this OTA (the as-of lines and the 30-day honest line), so it also flips only after the OTA.
3. Keep `surfaces` OFF in every App Review window.
4. App Store Connect: update the Promotional Text at the OTA; submit 1.0.1 with the description, keywords and screenshots aligned to the fragrance-only launch promptly.
5. The TestFlight device check: the one-chip category row and line (EN + AR, a narrow RTL screen), a fragrance compare, the honest lines, the narrow-RTL as-of row and the Hermes Arabic as-of date once the G3 / G4 flags are on, a non-fragrance pair after the flip (text, link, camera: the coming-soon copy, never the Paywall).
6. SF1 carries the `surfaces` contract (`skincare` / `makeup` booleans; only the boolean `true` counts) and the VALID_EVENT_TYPES widening with the event (S81-11c).

## [NATIVE READ]

Every added or changed Arabic string (15 added, 10 changed), the diacritics note and the month-name rule: `specs/S81_11_NATIVE_READ.md` (key | EN | AR | note). The Arabic script lives only there; this body stays ASCII.

## Deviations (reported, not silent)

- Key counts 15 / 10 / 17 (the gate text's 12 / 7 counted the spec table only; RB-S11-3).
- `onboarding.s1.quote_3` AR re-cut for the b3a r31 standalone-verb rule; 9 AR values stripped of diacritics (RB-S11-8).
- E-row titles renamed with their rows (E1c, E1d, E1e, E2, E6 27 -> 26, E7, E8, E8b, E11); the s3 anchor list shrinks by one it.each node.
- The gate rows are four rows in 11 jest nodes (per-reason, per-state and control nodes), so the s11 total is 135 nodes, not the 128 the brief anticipated; RB-S11-2 says "FIVE rows" but names four (GR1..GR4), and four were written.
- Both commit trailers name the committing model (Claude Opus 5.5).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
