# CLIENT-TRUTH: Arabic strings for native review (session 74, 2026-10-08)

Every AR value written or changed by the unit, with its source tag as the GREEN/fix agents recorded it. The native reviewer confirms each line or proposes the replacement; replacements land as a copy-only follow-up (the fences pin shapes, not wording, except where a test says so).

- AMENDMENT this round: no catalog value changed (en.json f0c51670..., ar.json 910be451... are byte-identical to GREEN). The GREEN list below therefore stands unchanged; the exact AR text of every key is its ar.json value at sha 910be451. Tags: [SPEC] = spec AR verbatim (verified by green/verify_ar.py); [SPEC+CT2] = spec text plus a GREEN clause; [DERIVED] = cut from the old AR value; [GREEN] = composed by GREEN, needs the closest review. Western digits only.
- NEW (ruling Y4, position only): referrals.share.subtitle [GREEN] now renders directly ABOVE the privacy toggles, after the reward block, instead of under the title. The reviewer should check that the AR text reads as the heading of the three share toggles (name / result / reasons) under RTL.
- NEW (ruling Y5): results.medicalNote AR is now pinned byte-for-byte to the spec text by medicalNote.s74.test.tsx (AR_MEDICAL_NOTE, ASCII \u escapes). A native-review change to this string must update that constant in the same edit.
- referrals.share.reward.later [SPEC+CT2: GREEN appended the cap clause '(up to 3 friends)'] (EN: 'Bonus comparisons for 7 days when a friend you invite signs up and runs their first comparison (up to 3 friends)'). Check the parenthesis under RTL; EN is now also pinned to contain 'signs up' (Y10).
- referrals.share.subtitle [GREEN, ruling CT10, EN 'What your friend gets']
- referrals.loop1.toast [DERIVED: first sentence of old ar:445, = spec]
- referrals.loop1.counter [SPEC, without the trailing period, matching EN]
- referrals.quiz.signupBody [SPEC]
- referrals.quiz.signupCtaSoft [DERIVED: old value cut at the dash, brand kept; CT4/G5]
- notifications.prePrompt.body [DERIVED: old ar:688 minus exactly the bonus-expiry clause; CT3]
- editProfile.avatar.placeholder [SPEC]
- results.price.pending [SPEC]
- onboarding.s12.title [SPEC]
- results.medicalNote [SPEC]
- results.confidence.sheet.price.sources_zero [SPEC; unreachable, guarded > 0]
- results.confidence.sheet.price.sources_one [SPEC]
- results.confidence.sheet.price.sources_two [SPEC]
- results.confidence.sheet.price.sources_few [SPEC]
- results.confidence.sheet.price.sources_many [SPEC]
- results.confidence.sheet.price.sources_other [SPEC]
- results.confidence.sheet.reviews.count_zero [GREEN; unreachable, guarded > 0]
- results.confidence.sheet.reviews.count_one [GREEN]
- results.confidence.sheet.reviews.count_two [GREEN]
- results.confidence.sheet.reviews.count_few [GREEN]
- results.confidence.sheet.reviews.count_many [GREEN; tanween orthography alef+fathatan as in the spec's sources_many, while history.hero uses fathatan+alef; the reviewer picks the house form (Y11)]
- results.confidence.sheet.reviews.count_other [GREEN]
- results.confidence.sheet.specs.citations_zero [GREEN; unreachable, guarded > 0]
- results.confidence.sheet.specs.citations_one [GREEN]
- results.confidence.sheet.specs.citations_two [GREEN]
- results.confidence.sheet.specs.citations_few [GREEN]
- results.confidence.sheet.specs.citations_many [GREEN]
- results.confidence.sheet.specs.citations_other [GREEN]
- AR keys REMOVED (both catalogs, GREEN): referrals.share.reward.now, referrals.share.messagePreview, referrals.share.error.weeklyCap, referrals.status.title, referrals.status.creditsAvailable, register.clipboardConsent.{title,message,accept,reject}, and the base keys results.confidence.sheet.{price.sources,reviews.count,specs.citations}, replaced by the six forms. en/ar have 1007 keys each and the key sets are equal.

## Stated limits of the unit (as committed)

- 1 No device rendering. There was no on-device Arabic/RTL check of any changed screen: reward line parenthesis, medical note in the why block, the share sheet without the preview, the subtitle now above the toggles with the new title spacing (Y4), and Register without the banner.
- 2 No Arabic string has had native review. 14 AR values are GREEN-composed (share.subtitle, reviews.count_* x6, specs.citations_* x6, the reward.later cap clause). The EN wording of the CT14 forms and of the '(up to 3 friends)' clause is GREEN's, not the spec's. No catalog value changed this round.
- 3 CT10/Y4: the referrals.share.subtitle EN is the ruling's words verbatim, 'What your friend gets' with no period. It now sits directly above the privacy toggles, after the reward block. Under ruling Y4 no node pins its position, so moving it back stays green. The title style gained marginBottom spacing.md (one line, my call) because the gap after the title used to come from the subtitle. Nobody has looked at it on screen.
- 4 The reward block is hidden only when the parent passes lifetimeRemaining === 0. ResultsScreen passes that only after a share in the same screen (CTR-2), so a capped user who opens the sheet first still sees the block. The 'up to 3 friends' copy keeps that case true. CT1/CT2 go red by design if LIFETIME_CAP or BONUS_EXPIRY_DAYS change in referral_service.py.
- 5 AMENDED (Y1-Y3). Medical-note trigger: arms (b) and (c) read `${brand ?? ''} ${name ?? ''} ${variant ?? ''}` per product, plus the raw top-level result.query (string only; metadata.query is not read). Dose = number + mg|mcg|iu, and a space then a pack count is allowed ('500mg 24 tablets'). A unit glued to a digit is a model code ('2024 MG5'). There is no ug/micro-g and no gram dose ('Metformin 1g' gets no note). A year before the MG car brand still reads as a dose ('2023 MG ZS', '2024 MG 5'), and because the query is now scanned, a query like '2023 MG ZS vs ...' shows the note. Context-only tokens (vinegar, glucose, flu, dose, dosage, pharmacy) never fire alone, so 'Dexcom glucose monitor', 'Cold & Flu tablets' with no brand token or dose, and a name containing only 'pharmacy' show no note unless another arm fires. The query arm also fires on any free-text query that carries an active token or a dose, whatever the products are. A category string with extra words ('Health & Supplements') still does not normalise. History payloads carrying category_used remain unverified. No lookbehind is used; Array.prototype.includes runs at module init. Neither has been run on Hermes.
- 6 The medical note is absent on the InviteeQuizScreen result and the text-only share body (N5, out of scope).
- 7 Sentry: client exception values are blank except the three shapes matched whole and anchored at the start (now pinned by Y6 and G6), so events keep only type + minified frames (sourcemaps are not uploaded). The message/extra scrub is the existing pattern set only: a bare email or free text in event.message is NOT redacted. It goes one level into extra; logentry, contexts, tags and nested extra are untouched. Under ruling Y13 the U8 'error message' clause stays. The query rung relies on axios encoding.
- 8 AMENDED (Y12): gitleaks dir over sentry.test.ts exits 1 with the 3 pre-existing findings on unchanged HEAD lines 38/44/110, which counts as no new finding. The pre-commit hook and the CI secret-scan were not run (no git write).
- 9 Dead keys with false claims are left unrendered (Q5/N7/Y11): referrals.share.toast.confirm, referrals.quiz.placeholder, referrals.status.subtitle.
- 10 CT5 cross-unit: the Loop 2 push still says 'Expires in 3 days' while the in-app line says 7 days. Only the U3c rider R7 fixes it; the PR body must record the dependency.
- 11 CT18/N3/Y14: clipboardFallbackService.ts and expo-clipboard stay. The undeployed redirect Worker still says the code is on the clipboard; the PR body must make any Worker deploy wait until the clipboard read is re-enabled. Also from Y14: if scripts/cron_expire_bonuses.py is ever wired, the pre-prompt regains the clause and the CT3 node is revisited.
- 12 N1 follow-up, not done: recent searches survive sign-out, and @qaren_onboarding_draft_v1 is not cleared at deletion.
- 13 The app.json and inventory change is native-only: it reaches users only through eas build --profile production, and the ASC labels are refilled from the inventory. No Apple/Expo doc was read.
- 14 AMENDED: this round ran 26 byte-copy mutant runs (see mutants). The final adversary still owes its own independent mutants. No base-vs-head comm full suite ran this round (the RED base measurement stands), and no detached scratch worktree was made (it would need node_modules).
- 15 AMENDED: the ShareBottomSheet diff re-indents the reward block (GREEN). This round also moved the subtitle Text, added a Y4 comment, the title marginBottom and an updated style comment. ResultsContent.tsx, ResultsScreen.tsx, HomeScreen.tsx, authService.ts, clipboardFallbackService.ts and every backend file are untouched this round.
- 16 AMENDED: the Edit tool DECODES \u escapes written in new_string into real characters. It did so once in medicalNote (AR_MEDICAL_NOTE). I caught it with final_check.py and rewrote the file to ASCII escapes after a byte copy. All final clientTruth test files are 0 non-ASCII bytes. sentry.test.ts (21) and ConfidenceDetailsSheet.test.tsx (80) carry only pre-existing non-ASCII on unchanged lines. Added non-ASCII lines are only in production comments (em dash / section sign, house style), en.json loop1.toast and ar.json.
- 17 Parallel jest runs still print 'A worker process has failed to exit gracefully' once in the FULL run. It is pre-existing and was not traced.
- 18 AMENDED: the spec set was read in full at the start. Before reporting I re-checked it item by item against the diff and confirmed it is unchanged: mtimes are before my first read; sha256 35156eae (SPEC), 6088ddf5 (REVIEW), be14b147 (RULINGS with the 17:05 Y section).
- 19 NEW (Y7): CT-R2 is a source pin. It checks code lines only; lines starting //, *, /* or {/* are treated as comments. It catches 'expo-clipboard' string literals and getStringAsync/hasStringAsync identifiers. A clipboard read through another API (e.g. a different clipboard module or a wrapper with another name) is not caught. The behavioural CT-R1 observes only clipboardFallbackService.
- 20 NEW (Y8): the node checks that, before any tap, no rendered text contains the head of the EN and AR messageWithLink template (the text before {{link}}). A preview built from a different template or a reworded message would not be caught.
- 21 NEW (Y9): the rejection is injected by key on the repo's AsyncStorage jest mock (a one-shot reject for @qaren_recent_searches). Real-device storage errors were not exercised.
- 22 NEW: one node beyond the ruling's list (the Y3 both-sides boundary over every active backend token, X+tok / tok+x). Without it, the leading-boundary mutant MF6b survived the ruling's Adolfo/Fluke negatives.
- 23 NEW: the CT6 arm (b) mirror node in medicalNote.s74.test.tsx was amended rather than appended. It is a new, uncommitted file, and Y3 changed the contract it pinned. The G4 equality node is unchanged.
