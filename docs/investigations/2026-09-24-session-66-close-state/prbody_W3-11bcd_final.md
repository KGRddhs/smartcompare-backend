## W3-11bcd — the Arabic pack: one digit policy, prices with the ISO minor unit, catalog relative time, code-routed Home copy, a11y labels, and an i18n literal fence (client, OTA-gated)

### Defects (RTL-05/06/07/08/09/14, measured at base b63a8368)
- Mixed digit systems: Arabic-Indic digits inside `ar.json` (age ranges, budgets, "٧٣٪", "٣٨٨ متسوّق") next to ASCII digits from `{{count}}` interpolations and `toFixed` sites; device-locale `toLocaleDateString('ar-SA')` renders drifted from both.
- Prices rendered symbol-first via `toLocaleString()` / `toFixed(0)` with no minor unit (BHD/KWD/OMR have 3), on Results, History and the smart-pick tiles.
- Relative time: an English-only helper (`3h`, `5d`) and a device-locale date for Arabic users in the Profile recent-decisions row; History's `formatTimeAgo` carried hard-coded copy in a util.
- Home's two `success:false` compare paths rendered `data.error` (backend English prose: "We don't compare this category", "Could not identify …") into the alert.
- `accessibilityLabel="Back"` / `"Share"` on the Results header buttons; a literal `' is required'` suffix and `'Registration failed'` fallback; the ESLint i18next rule in `jsx-text-only` mode was blind to every literal outside JSX children (measured: 0 messages while `accessibilityLabel="Back"`, `'N/A'` and `Alert.alert('…')` literals shipped).
- `results.valueMatch.cheaper_of_two`: a lone key ending in i18next's reserved `_two` plural suffix.

### Change
- `src/utils/formatNumber.ts` (NEW): `APP_DIGIT_SYSTEM = 'latn'` (the signed policy — flipping it is NOT a one-constant change: 35 `{{count}}` families and six `toFixed` sites need their own unit), `toAsciiDigits`, `applyDigitSystem`, `formatNumber` (pure JS, grouping + fraction control; a non-empty numeric string formats, every other non-number renders as `String(n)` — never a fabricated `0.000`), `formatPrice` (amount then localized symbol with the ISO minor-unit width, both languages: `12.345 د.ب` / `329.000 BHD`).
- `src/utils/formatDate.ts`: `formatTimeAgo(d, language, t)` is catalog-backed (`time.justNow` + the `time.{minutes,hours,days}Ago` plural families with six Arabic forms each); `formatDate` maps the engine's digits to the policy. Shared by `HistoryScreen` and `ProfileEditorialSections` (its local `timeAgo` removed).
- `ResultsContent`, `HistoryScreen` (local `formatPrice` removed), `HomeEditorialSections` smart-pick tiles, `ResultsAccordion` review counts: through `formatNumber` / `formatPrice`.
- `HomeScreen`: both `success:false` paths route by CODE — `CONTENT_UNAVAILABLE` → the content-block handler with the backend `layer` (new optional `ComparisonResult.layer`), `TIMEOUT`/`STREAM_TIMEOUT` → the settling copy, else `friendlyErrorKey`; `data.error` is never render input.
- `ar.json` normalised to ASCII digits and `%` (0 Arabic-Indic digits and 0 U+066A left; en/ar key sets equal at 937); `cheaper_of_two` → `cheaperOfTwo`; `results.a11y.back/share`, `auth.registerFailed`; `ForgotPasswordScreen` uses `auth.emailRequired`.
- `LoadingScreenVariants` shimmer sweep follows the reading direction, read at render time (never module scope).
- `eslint.config.js`: `no-restricted-syntax` selectors for literal English in user-visible JSX attributes (`accessibilityLabel|accessibilityHint|placeholder|title|label`, `label="English"` self-label excluded), the literal arms of `setError(...)` and `Alert.alert(...)`, and the `'N/A'` literal. CI's own eslint step (`eslint "src/**/*.{ts,tsx}"`) is the tree-wide enforcer: measured exit 0, 0 errors, 147 warnings under the 149 ceiling.

### Tests (13 new suites / 61 nodes)
`i18n/digitPolicy.w311` (the catalog fence), `i18n/pluralFamilies.fence.w311`, `utils/formatNumber.test` (incl. the null/undefined/''/[]/true no-fabrication rows), `utils/formatDate.test`, `HistoryScreen.timeAgo.w311` and `ProfileEditorialSections.timeAgo.w311` (real i18next `ar` instance; the HistoryRow call site pinned), `components/ResultsAccordion.digitPolicy.w311` (simulated `ar-SA` device locale), `components/ResultsContent.a11y.w311`, `HomeEditorialSections.smartPickPrice.w311`, `HomeScreen.arabicAlerts.w311` (SSE and URL arms, `layer` forwarding, TIMEOUT/STREAM_TIMEOUT/INSUFFICIENT_DATA), `LoadingScreenVariants.shimmerRTL.w311` (start value AND the `withTiming` target sign), `api.terminalRouting.w311` (api.ts required once in a 60 s `beforeAll`), `lint/i18nFence.w311` (ONE stdin ESLint invocation over a fixture of 13 positives, 4 negatives and a control; deleting the `'N/A'` selector reddens both tests; 24-27 s idle).
- Evidence: full jest `--maxWorkers=25%` 294 passed / 3 skipped of 297 suites, 2813 passed / 13 skipped / 13 todo, 44/44 snapshots = baseline (281 / 2752 / 44) + these 13 suites and 61 tests; tsc 5.9.3 clean; the CI eslint command exit 0.
- Mutation-checked from byte snapshots with sha-verified restores across green, adversary SOUND (7 minors, 6 prove-nothing rows) → fix round → re-review SOUND → polish (formatNumber coercion narrowed, api.terminalRouting hoist, fence single-invocation) → recheck SOUND: shimmer `* dir` (target and start), OMR row + the exact fraction-digits set, the coercion and the isFinite guard, the HistoryRow `t` identity, the two ResultsAccordion sites, the three Home URL-arm codes, the SSE `layer` forwarding, the smart-pick `toFixed(0)` revert, the 20-day Profile case, the `'N/A'` selector — every one reddens a named test.

### Review trail
Red → Fable red gate → green → adversary SOUND → fix → re-review SOUND → polish → recheck SOUND (one residual: the fence's child kill was load-sensitive at 100 s on the shared box — raised by the orchestrator to a 300 s jest budget / 240 s kill, still far below the previous 600/570) → Fable diff review.

### Limits, disclosed
- The fence is a fixture-level pin; its cost is ESLint config + plugin loading under CPU contention (the 100 s kill fired in 5 of 13 runs at 85-95 % CPU on the shared dev box; idle 24-27 s). A red of the form "ran past N s and was killed" is a timing failure, not a rule failure.
- `formatNumber` coerces hex and exponent numeric strings as any `Number()` rule does (`'0x10'` → 16); no caller sends those.
- `RegisterScreen` still renders `result.error` before the new `auth.registerFailed` fallback (pre-existing pattern outside this pack's rulings; follow-up `PO-COPY-01` together with W3-14's `settingsErrorKey`).
- The Android digit rendering and RTL sweep are jest-proven, never phone-proven: the on-device Arabic walkthrough after the OTA remains the verification.

### Activation
Client-only; phones on 97b5f15 are unaffected until `eas update --branch preview --clear-cache` (Ahmed's lever). No flag. `APP_DIGIT_SYSTEM` is the Ahmed sign-off item.

🤖 Generated with [Claude Code](https://claude.com/claude-code)


## Verification on the rebased tree (main `7368f862`, 2026-09-24)

- Rebased clean onto `7368f862` after W3-14 (#174) merged; the six overlapping files (`ar.json`, `en.json`, `HomeScreen.tsx`, `RegisterScreen.tsx`, `ResultsScreen.tsx`, `types.ts`) auto-merged with no conflict markers.
- `node node_modules/typescript/bin/tsc --noEmit`: clean.
- `node node_modules/eslint/bin/eslint.js` on every touched `.ts`/`.tsx`: 0 errors, 145 warnings (all pre-existing patterns: `no-require-imports` in tests, `array-type`, unused imports in the legacy screens).
- FULL jest on the rebased tree (`--maxWorkers=25%`): 318 suites passed / 3 skipped, 3,109 tests passed, 44 snapshots (main at `7368f862`: 306 suites / 3,050 tests / 44 snapshots; this unit adds 13 suites and 59 passing tests). ONE suite red: `__tests__/lint/i18nFence.w311.test.ts`, both tests with the message `eslint on src/screens/__fence_fixture__.tsx ran past 240 s and was killed`. That is the fence's own timing kill, not a rule failure. Measured on the dev box during that run: `node -e 0` took 29-82 s per spawn, `git --version` 43 s, a direct ESLint run of the three-line fixture took 631-1,015 s with total rule time under 5 s (`TIMING=1`), i.e. process-creation and module-load latency local to the box (Windows Defender is off; Surfshark Antivirus real-time scanning and NZXT CAM process hooks are the suspects). Earlier in the session the same file measured 24-27 s idle and 16.8 s inside a passing full suite. The frontend-tests CI job is the arbiter for this suite; a red there of the same "ran past N s and was killed" shape is a timing failure and should be re-run before the rule is blamed.
- Backend: no backend file touched (client-only unit), so the backend gates are vacuous.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
