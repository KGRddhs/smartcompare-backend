export const meta = {
  name: 's71-u4c-spec',
  description: 'Session 71 U4c spec (read-only): the in-app MYEZ mark replacing the old QarenLogo Q-ring on the JS splash, Home, Profile, History, onboarding Step 1 and LoadingRings; measure, write the spec, adversarial review',
  phases: [
    { title: 'Spec', detail: 'measure every QarenLogo site, snapshot pins, asset options; write the spec' },
    { title: 'Review', detail: 'adversarial spec review, binding corrections' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const CLONE = 'C:/Users/SynAckITPC/Documents/AI/smartcompare'
const APPDIR = CLONE + '/SmartCompareApp'
const SPEC = SP + '/u4c/U4C_INAPP_MARK_SPEC.md'
const NOTES = SP + '/u4c'
const MASTER = 'C:/Users/SynAckITPC/Downloads/MYEZ-icon-white-2048.png'
const U4B_SPEC = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-09-30-session-70-state/U4B_ICONS_DEPS_SPEC.md'
const BASE = '94c097cd'

const CONTEXT = [
  'UNIT U4c of the MYEZ (Arabic brand in the catalogs) Apple App Store launch lane, repo smartcompare (React Native / Expo SDK 54 app in SmartCompareApp/). The app was renamed Qaren -> MYEZ in session 69 (PR #257: every user-visible string), and session 70/71 unit U4b (running in a sibling worktree, do not touch it) ships the NATIVE launcher art from the master PNG ' + MASTER + ' (2048x2048 RGBA, a white rounded tile with a black "MY/EZ" wordmark and an emerald #10B981 dot). U4c is the JS half: the IN-APP glyph is still the old Qaren Q-ring drawn by src/components/QarenLogo.tsx (react-native-svg: a Q ring + tail + emerald dot), rendered at SplashScreen.tsx:112 (128 pt, the JS splash right after the native splash), HomeScreen.tsx:900, ProfileScreen.tsx:355, HistoryScreen.tsx:939, onboarding Step01Welcome.tsx:76 and LoadingRings.tsx:212 (re-anchor by symbol; those line numbers are from 2026-09-30 at base ' + BASE + '). App Review would see the Q-ring right after the MYEZ native splash, so U4c should land BEFORE the production build; it is OTA-capable (JS + a bundled PNG asset only).',
  'Identifiers stay qaren (bundle id com.qaren.app, slug, qaren://, EAS project, Sentry org, the @qaren_* storage keys). The component NAME QarenLogo may stay as an identifier or be replaced by a new MyezLogo component: measure which costs less (call sites, tests, snapshots) and recommend; the orchestrator rules.',
  'READ-ONLY UNIT FOR YOU: measure in the CLONE ' + CLONE + ' at main ' + BASE + ' (never write a file there, never git checkout/stash/commit there, never npm install anything; jest MAY be run by path from ' + APPDIR + ' with `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci <paths>` - never -u, never the full suite). Write ONLY the spec file ' + SPEC + ' and notes under ' + NOTES + '. Read the agent rules file FIRST and obey it: ' + RULES + ' (the pytest/backend parts do not apply; the shell/secrets/no-git-write rules do).',
  'Inputs you must read: the U4b spec ' + U4B_SPEC + ' (sections 1.14, 1.18, 4 = the master geometry, the renderer scripts/render_myez_icons.py that U4b adds with its mark-extraction algorithm and the four outputs incl. splash-icon.png = the transparent wordmark at 30 % width; and its BINDING sections). U4c may ADD a renderer output (e.g. SmartCompareApp/assets/brand/myez-mark.png, a transparent-background wordmark+dot at a fixed pixel size with @2x/@3x variants or one large PNG) by extending that script - state exactly how, so the two units do not conflict (U4c builds ON TOP of U4b after it merges; say so).',
].join('\n')

const SPEC_SCHEMA = { type: 'object', required: ['spec_path', 'spec_sha256', 'base_sha', 'open_questions', 'summary'], properties: {
  spec_path: { type: 'string' }, spec_sha256: { type: 'string' }, base_sha: { type: 'string' },
  open_questions: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const REVIEW_SCHEMA = { type: 'object', required: ['verdict', 'corrections', 'spec_sha256_after', 'summary'], properties: {
  verdict: { type: 'string', enum: ['APPROVED', 'APPROVED_WITH_CORRECTIONS', 'REJECTED'] },
  corrections: { type: 'array', items: { type: 'string' } }, spec_sha256_after: { type: 'string' }, summary: { type: 'string' } } }

phase('Spec')
const spec = await agent([
  'ROLE: spec writer (read-and-measure only).',
  CONTEXT,
  'TASK: measure everything U4c touches and write the spec to ' + SPEC + ' (create the folder). Required sections: Base SHA (print git -C ' + CLONE + ' rev-parse HEAD); Measured facts, each with the command and an output excerpt: (a) QarenLogo.tsx in full (props: size, colours; what it draws; its theme usage); (b) EVERY import/use of QarenLogo across src/, App.tsx, __tests__/ and __mocks__/ (git grep), with the size and surrounding layout at each site (what sits next to it: the brand text, the loading rings animation, the hero); (c) every jest test and SNAPSHOT that pins QarenLogo or the screens that render it (grep __tests__/**/*.snap for "QarenLogo" and for the SVG path data; list each .snap file and which test writes it - a .snap change needs a ruling, the session rules treat it as a defect unless the spec assigns it); (d) how LoadingRings uses the glyph (is the Q-ring part of the animation geometry? what breaks if a wordmark replaces a round mark); (e) how images are bundled: jest.config.js moduleNameMapper for png (fileStub), metro asset handling, any existing require(\'../assets/...\') image usage in src/ and how tests mock it, expo-image vs RN Image in the dependency list, and whether the W3-7 nativeBundle test or any other test walks SmartCompareApp/assets; (f) the brand text next to the glyph after #257 (the catalog keys, EN "MYEZ" / AR Arabic form) so the glyph+text composition is not "MYEZ" twice; (g) RTL: the JS splash and Home header under I18nManager RTL (the wordmark is Latin letters - does it mirror? it must not); (h) the master geometry you need from the U4b spec (ink bbox, the 32 px right offset, the dot) and the pixel sizes the six sites need at @3x (e.g. 128 pt -> 384 px) to choose the asset size(s). Then: Design options with evidence - (A) a bundled PNG asset rendered with React Native Image (resizeMode contain, explicit width/height from the size prop; @1x/@2x/@3x files or a single large file) produced by extending U4b\'s renderer deterministically; (B) a react-native-svg vector of the wordmark (needs a vector source the repo does not have - state what Ahmed would have to supply); (C) keep QarenLogo on some sites (which, and why). Recommend ONE with the measured costs. Requirements R1..Rn (exact files; keep or replace the QarenLogo identifier per your recommendation; the component API; the asset(s); the renderer extension; what each site renders after; any .snap files assigned for update and WHY each changes); the RED test list (name, file, assertion, why red at base - include: no site renders the Q-ring SVG any more, the asset exists with the recorded sha256 and dimensions, RTL does not mirror the image, a size prop maps to the intended width/height); Gates (jest by path on every touched suite; FULL jest; tsc; eslint on changed files; no .snap drift beyond the assigned list; the U4b renderer --check still passes); Stated limits (no device verification; the asset is correct only over the app\'s background colours - measure which backgrounds the six sites use, light and dark theme if the app has one); Open questions for the orchestrator (identifier keep vs replace; LoadingRings treatment; snapshot policy; whether the in-app mark should be the tile (white rounded square) or the bare wordmark+dot; dark backgrounds).',
  'Return the spec path, its sha256, the base sha, your open questions and a short summary.',
].join('\n'), { label: 'u4c:spec', phase: 'Spec', schema: SPEC_SCHEMA })

phase('Review')
const review = await agent([
  'ROLE: ADVERSARIAL spec reviewer. Your job is to REFUTE claims in the spec, not to confirm them. Read-and-measure only (same read-only rules; no edits except appending to the spec file).',
  CONTEXT,
  'The spec is ' + SPEC + ' (sha256 reported by its writer: ' + (spec ? spec.spec_sha256 : 'unknown') + '). Re-measure EVERY factual claim: every QarenLogo site (did the writer miss one - grep for the SVG path data and for "Q-ring" too), every snapshot that would change, the LoadingRings geometry, the jest png mapping and how Image sources resolve under jest (does a require of a PNG in a component break any existing test runner config?), the RTL mirroring claim (I18nManager.isRTL and Image - measure in the installed react-native what mirrors), the asset-size arithmetic, and whether the recommended option really is OTA-capable (a new bundled asset IS shipped by eas update; confirm from expo-updates/metro docs in node_modules, not from memory). Look for what the spec MISSED: Android/iOS Image caching of a changed asset with the same path, the W3-7 nativeBundle test or the U4b b-tests walking assets/, accessibility labels on the glyph, the share card / referral screens that may draw the brand, the landing pages (out of scope - say so), and the sequencing against U4b (same renderer file).',
  'Writer open questions: ' + JSON.stringify(spec ? spec.open_questions : []),
  'Append a section "## Review corrections (BINDING - supersede the body)" to the spec with numbered corrections, each with its measurement. Answer the writer open questions with a RECOMMENDATION each (the orchestrator will confirm). Return verdict, corrections, the spec sha256 after your edit, and a summary.',
].join('\n'), { label: 'u4c:spec-review', phase: 'Review', schema: REVIEW_SCHEMA })

return { spec, review }
