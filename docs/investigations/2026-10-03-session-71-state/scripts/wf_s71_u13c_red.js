export const meta = {
  name: 's71-u13c-red',
  description: 'Session 71 U13c RED under the synack-build-orchestrator loop: one Opus agent writes and proves the failing tests for the camera 401 refresh-and-retry (issue #298) and the camera-only sign-in state; it stops there so the Fable orchestrator can gate the tests before any implementation.',
  phases: [
    { title: 'Red', detail: 'tests first: write the service and screen files, prove red for the right reason at base, pins green, neighbours untouched', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b'
const APPDIR = WT + '/SmartCompareApp'
const SPEC = WT + '/docs/investigations/2026-10-03-session-71-state/U13C_CAMERA_401_SPEC.md'
const NOTES = SP + '/u13c/red'
const SPECNOTES = SP + '/u13c'
const HEADSHA = '72b13bc5'

const CONTEXT = [
  'CLIENT UNIT U13c of the MYEZ Apple launch lane (repo smartcompare; React Native / Expo SDK 54 app in SmartCompareApp/). Worktree ' + WT + ' (branch feature/s71-u13c-camera-401, HEAD = main ' + HEADSHA + '; its OWN real node_modules match the lock: never install anything). Backend U13 is ACTIVE in production: POST /api/v1/image/identify refuses a caller without a valid bearer with 401 AUTH_REQUIRED, after parsing the multipart body. Today the camera upload (identifyFromImages in src/services/api.ts, a raw RN fetch) has no 401 handling: one fetch, no refresh, a thrown Server error 401 that ResultsScreen turns into the generic No comparison loaded state. The unit adds exactly one refresh through the exported zero-argument getOrStartRefresh() single flight and one retry with the same FormData, raced against the identify deadline, and a camera-only sign-in state. Today is 2026-10-03 (session 71).',
  'Read the agent rules file FIRST and obey it: ' + RULES + ' (client gates: PROJECT tools by path from ' + APPDIR + ' under coreutils timeout, versions printed first, never jest -u, a .snap in the diff is a defect, never jest.mock(path, factory, { virtual: true }) on an existing module).',
  'THE SPEC IS AUTHORITATIVE: ' + SPEC + ' (sha256 fb3210dd6f457dd6...). Read it IN FULL, once at the start and again before reporting. It ends with TWO binding sections that supersede its body, the later one winning: "## Review corrections (BINDING ...)" (corrections 1-11 with the updated counts and gates) and "## Orchestrator rulings (BINDING ...)" (UR1-UR8). Settled: Q1 = A (the service throws the existing 401 error on a second 401; the screen shows the camera-only sign-in state; the CTA awaits clearSession then emitSessionInvalid, order pinned); the refresh wait is raced against controller.signal (correction 1); any 401 refreshes, a 403 never (corrections 4, 5); the thrown error is walked deeply for a token (correction 2); response fakes are single-read (correction 3); T1 pins the FormData parts (correction 7); T17 split into T17a PIN and T17b RED (correction 6); G2b covers the 19 ResultsScreen suites (correction 8); mutants M1-M23.',
  'The spec writer and the reviewer left scratch probes you may READ (re-measure what you rely on): ' + SPECNOTES + ' (notes.md, gate_untouched.py, probe_formdata_resend.js, __tests__/probe_base_camera401.test.ts) and ' + SPECNOTES + '/review (the ADV-1..ADV-6 probes).',
].join('\n')

const WORK_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'red_table', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes' },
  gates: { type: 'array', items: { type: 'string' }, description: 'verbatim summary lines of every jest / tsc / eslint run with its command' },
  red_table: { type: 'array', items: { type: 'string' }, description: 'one line per test id (T1-T19 incl. T17a/T17b, S1-S4): "<id> | RED or PIN | result at base | the failure line that proves the stated reason"' },
  deviations_from_spec: { type: 'array', items: { type: 'string' } }, git_status_final: { type: 'string' },
  residual_risk: { type: 'string' }, summary: { type: 'string' } } }

phase('Red')
const red = await agent([
  'ROLE: RED agent (tests first; tests only). You write EXACTLY two NEW files inside ' + APPDIR + '/__tests__ (UR6): api.cameraAuthRetry.u13c.test.ts (the service: RED T1-T11, T17b, T19; PIN T12-T16, T17a, T18 = 20 nodes) and screens/camera.authRequired.u13c.test.tsx (the screen: RED S1-S2; PIN S3-S4). You edit NOTHING under src/, no existing test, no mock, no config, no .snap, not the spec. You STOP after proving the reds: the orchestrator reviews the spec and your tests before any implementation begins.',
  CONTEXT,
  'Binding conventions: every test carries its id in its name; LF, ASCII, Write tool; the service file drives the REAL src/services/api.ts (identifyFromImages) with a fetch fake whose Response objects are single-read (a second text()/json() rejects TypeError Already read, as whatwg-fetch does), with getOrStartRefresh / getToken / clearSession / emitSessionInvalid observed through the module seams the spec names (never a virtual mock of an existing module), fake timers for the deadline race, and a deep walk of the thrown error for any token; the screen file renders the real ResultsScreen through the camera path with the existing mocks the ResultsScreen suites use, asserts the sign-in state by the existing i18n keys, and pins the CTA order (clear-done before emit); no test depends on wall-clock time; no snapshot assertion anywhere.',
  'PROOF at base (HEAD ' + HEADSHA + ' with only your two files added), every command by path under timeout with the tool version printed first: (a) each file alone: paste the jest summary and, per test id, the failure line that proves the STATED reason (a RED that fails because the suite cannot load or for another reason is a wrong red: fix it); every PIN passes; (b) the spec G2 + G2b neighbour sets (the camera / api / ResultsScreen suites incl. aiDispatchFence, bootOptimistic, rtl/directionalIconWiring) in one run: the only failures are your RED ids; (c) the FULL suite once (timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci): totals, every failing id is one of your REDs, no suite fails to load, the known flake HistoryScreen.mobileJank.m21 re-run once alone before it counts, and the totals GREEN must reach; (d) tsc --noEmit: your files type-check at base; (e) eslint on your two files: 0 errors; (f) git status --porcelain lists only your two files and the untracked spec; no .snap in git diff; (g) satisfiability sketch in SCRATCH only (copies of api.ts and ResultsScreen.tsx with the design applied, run through a scratch copy of your tests with --roots at your folder and --modulePaths at the app node_modules): every RED turns green; report which did not.',
  'If a test in the spec cannot be written as specified (the framework behaves differently from the spec claim), do NOT bend it silently: measure, write the closest honest test, and list the deviation with its measurement. If a spec RED passes at base or a spec PIN fails at base, stop on that test, report it, and continue with the others.',
  'Notes: ' + NOTES + ' (create it; keep a running notes.md from the first measurement on; logs go there). Return files changed with final sha256, gates (verbatim summary lines with commands), the red_table, deviations from the spec (each with its reason), git status, residual risk, summary. Budget: 90 minutes from your first tool call.',
].join('\n'), { label: 'u13c:red', phase: 'Red', model: 'opus', schema: WORK_SCHEMA })
return { red }
