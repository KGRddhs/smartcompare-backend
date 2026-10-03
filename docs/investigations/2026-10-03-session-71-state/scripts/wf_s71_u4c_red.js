export const meta = {
  name: 's71-u4c-red',
  description: 'Session 71 U4c RED under the synack-build-orchestrator loop: one Opus agent writes and proves the failing tests for the in-app MYEZ mark; it stops there so the Fable orchestrator can gate the spec and tests before any implementation.',
  phases: [
    { title: 'Red', detail: 'tests first: write, prove red for the right reason at base, neighbours unaffected', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b'
const APPDIR = WT + '/SmartCompareApp'
const SPEC = WT + '/docs/investigations/2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md'
const NOTES = SP + '/u4c2/red'
const SPECNOTES = SP + '/u4c2'
const HEADSHA = 'eb86075e'

const CONTEXT = [
  'CLIENT UNIT U4c of the MYEZ Apple launch lane (repo smartcompare; React Native / Expo SDK 54 app in SmartCompareApp/). Worktree ' + WT + ' (branch feature/s71-u4c-inapp-mark, HEAD = main ' + HEADSHA + '; it has its OWN real node_modules that match the lock: never install, uninstall or update anything). The unit replaces the old Qaren Q-ring drawn by src/components/QarenLogo.tsx with the MYEZ mark (a bundled PNG rendered by scripts/render_myez_icons.py), drops the app-name text beside the mark, and makes the JS splash mark start at the native launch-screen position at full opacity. Today is 2026-10-03 (session 71).',
  'Read the agent rules file FIRST and obey it: ' + RULES + ' (the client-gate rules apply: PROJECT tools by path from ' + APPDIR + ' under coreutils timeout, versions printed first, never jest -u, a .snap in the diff is a defect, never jest.mock(path, factory, { virtual: true }) on an existing module).',
  'THE SPEC IS AUTHORITATIVE: ' + SPEC + ' (sha256 4761bf07671300aa...). Read it IN FULL, once at the start and again before reporting. It ends with TWO binding sections that supersede its body, the later one winning: "## Review corrections (BINDING ...)" (corrections 1-12 and the reviewer answers) and "## Orchestrator rulings (BINDING ...)" (UR1-UR15). Settled, do not re-open: sizes 128/256/384 (UR2); QaranIcon / RevealBurst and the ForgotPassword / Register text logos are OUT (UR3); fadeDuration={0} stays (UR7); the manifest keys mark_outputs + mark_geometry (UR8); the RTL compensation computed at RENDER time in SplashScreen while splashMarkLayout stays physical and pure, with RED C6 and mutants M14/M15 (UR10, correction 1); corrections 2, 3, 4, 5, 8, 9, 10 as written (UR11); the single snapshot update belongs to GREEN, never to you (UR12); no file-top import of a module this unit creates (UR14).',
  'The spec writer and the reviewer left scratch material you may READ (never copy blindly; re-measure what you rely on): ' + SPECNOTES + ' (notes.md, the expected manifest, the expected snapshot and its diff, the prototype outputs with their pixels_sha256 values, contact sheets) and ' + SPECNOTES + '/review (probe components and probe tests).',
].join('\n')

const WORK_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'red_table', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes' },
  gates: { type: 'array', items: { type: 'string' }, description: 'verbatim summary lines of every jest / tsc / eslint run with its command' },
  red_table: { type: 'array', items: { type: 'string' }, description: 'one line per test id (A1..A8, B1..B13, C1..C6, D1..D3, E1, F1 and the PINs): "<id> | RED or PIN | result at base | the failure line that proves the stated reason"' },
  deviations_from_spec: { type: 'array', items: { type: 'string' } }, git_status_final: { type: 'string' },
  residual_risk: { type: 'string' }, summary: { type: 'string' } } }

phase('Red')
const red = await agent([
  'ROLE: RED agent (tests first; tests only). You write ONLY test files inside ' + APPDIR + '/__tests__ (UR13): the three NEW files brand/inAppMark.u4c.test.ts, SplashScreen.mark.u4c.test.tsx and utils/splashMarkLayout.u4c.test.ts, and the three EDITS the spec names: components/QarenLogo.test.tsx (rewritten), case 1 of SplashScreen.test.tsx (inverted), case 2 of components/hero/LoadingRings.test.tsx (rewritten). You edit NOTHING under src/, assets/, scripts/ or docs/, no .snap, no mock, no jest/babel/metro config, not the spec. You STOP after proving the reds: the orchestrator reviews the spec and your tests before any implementation begins.',
  CONTEXT,
  'WRITE the tests of spec section 5 as corrected and ruled (RED ids A1-A8, B1-B5, B9-B11, B13, C1-C4 plus C6, D1-D3, E1, F1; PIN ids B6, B7, B8, B12, C5; the extra assertions of corrections 2, 4 and 5). Binding conventions: every test carries its id in its name; existing working copies are CRLF (i/lf w/crlf): edit existing test files with the Edit tool only, a whole-file diff of an existing file is a defect unless the spec says the file is rewritten (QarenLogo.test.tsx is); new files via the Write tool; PNG and JSON data are read with fs and decoded with __tests__/helpers/pngDecode.ts, never required; AST checks use the installed typescript package as brand.hardcoded.s69 does; the mark host is found by host type "Image" first (correction 2), then its props are read; anything that needs src/utils/splashMarkLayout loads it INSIDE the it body (correction 3, UR14); the RTL case C6 flips the mocked I18nManager inside the test and restores it afterwards (the repo mock __mocks__/react-native.ts exports a mutable I18nManager); no snapshot assertion is added anywhere; no test depends on wall-clock time; mock window 390x844 exactly as the spec states.',
  'PROOF at base (HEAD ' + HEADSHA + ' with only your test files changed), every command by path under timeout with the tool version printed first: (a) each of your six files alone: paste the jest summary and, per test id, the failure line that proves the STATED reason (a RED that fails because the suite cannot load, or for another reason, is a wrong red: fix it); every PIN in those files passes; (b) the neighbour set of spec gate G6 in one run: the only failures are your RED ids, and the two LoadingRings snapshots still PASS; (c) the FULL suite once (timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci): report suites and tests totals, list every failing test id, and confirm every failure is one of your REDs (no other suite fails or fails to load; the known flake HistoryScreen.mobileJank.m21 is re-run once alone before it counts); state the totals GREEN must reach (correction 10); (d) tsc --noEmit on the project: your test files must type-check at base (use local structural types or require inside the test where a module does not exist yet; never @ts-ignore a whole file); (e) eslint on your changed files: 0 errors; (f) git status --porcelain lists only your six test files and the untracked spec folder; git diff --stat shows no .snap and no whole-file rewrite except QarenLogo.test.tsx.',
  'If a test in the spec cannot be written as specified (the framework behaves differently from the spec claim), do NOT bend it silently: measure, write the closest honest test, and list the deviation with its measurement. If a spec RED passes at base or a spec PIN fails at base, stop on that test, report it, and continue with the others.',
  'Notes: ' + NOTES + ' (create it; keep a running notes.md from the first measurement on; logs go there). Return files changed with final sha256, gates (verbatim summary lines with commands), the red_table, deviations from the spec (each with its reason), git status, residual risk, summary. Budget: 90 minutes from your first tool call.',
].join('\n'), { label: 'u4c:red', phase: 'Red', model: 'opus', schema: WORK_SCHEMA })
return { red }
