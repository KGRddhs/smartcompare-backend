export const meta = {
  name: 's71-u8c-red',
  description: 'Session 71 U8c RED under the synack-build-orchestrator loop: one Opus agent writes and proves the failing Sentry-chain test for the deletion route (issue #292) with the child-process in-memory-transport idiom; it stops there so the Fable orchestrator can gate the test before the one-line fix.',
  phases: [
    { title: 'Red', detail: 'tests first: write the child-process Sentry pin, prove red for the right reason at base, pins green', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-u8b'
const SPEC = WT + '/docs/investigations/2026-10-03-session-71-state/U8C_SENTRY_CHAIN_SPEC.md'
const NOTES = SP + '/u8c/red'
const SPECNOTES = SP + '/u8c'
const HEADSHA = 'b90b5f07'

const CONTEXT = [
  'BACKEND UNIT U8c of the MYEZ launch lane (repo smartcompare; FastAPI in app/ - the DEPLOYED backend; never edit backend/app/). Worktree ' + WT + ' (branch feature/s71-u8c-sentry-chain, HEAD = main ' + HEADSHA + '; the only untracked file is the spec). Today is 2026-10-03 (session 71). Issue #292: DELETE /auth/account raises HTTPException(500) inside its except arm, so the Sentry Starlette integration ships the chained exception text (email, URL) for httpx.ConnectError, AuthApiError and RuntimeError, and the sentinel word of an APIError .message; the fix (GREEN, not you) is ` from None` on that raise.',
  'Read the agent rules file FIRST and obey it: ' + RULES + '. Every pytest run goes through the bounded runner; never touch the network, Railway, Supabase or a real Sentry DSN (Sentry only through init_sentry with an in-memory transport and a dummy DSN, in a child process); never print a credential.',
  'THE SPEC IS AUTHORITATIVE: ' + SPEC + ' (sha256 fd003ccf79a2c180...). Read it IN FULL, once at the start and again before reporting. It ends with TWO binding sections that supersede its body, the later one winning: "## Review corrections (BINDING ...)" (C1-C9) and "## Orchestrator rulings (BINDING ...)" (UR1-UR10). Settled: the child-process fixture order of C2, log handlers attached after the app import (C3), sentinel hygiene (C4), the APIError fourth scenario with the sentinel in .message (C5), the kill set = the new file + the two U8b files (C6), mutants MU1-MU8 (C7), traces_sample_rate 1.0 and the all-items sweep (UR6), the route log event asserted in the Sentry channel (UR3).',
  'The spec writer and reviewer left working probes you may READ (re-measure what you rely on, never copy blindly): ' + SPECNOTES + ' (notes.md, test_probe_u8c.py, u8c_swap_plugin.py, survey.*) and ' + SPECNOTES + '/review. The W1-1b child-process idiom to follow is in tests/test_retro_w1_1.py.',
].join('\n')

const WORK_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'red_table', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes' },
  gates: { type: 'array', items: { type: 'string' }, description: 'verbatim [pyt] lines and summary lines' },
  red_table: { type: 'array', items: { type: 'string' }, description: 'one line per test id: "<id> | RED or PIN | result at base | the failure line that proves the stated reason"' },
  deviations_from_spec: { type: 'array', items: { type: 'string' } }, git_status_final: { type: 'string' },
  residual_risk: { type: 'string' }, summary: { type: 'string' } } }

phase('Red')
const red = await agent([
  'ROLE: RED agent (tests first; tests only). You write EXACTLY one file in ' + WT + ': tests/test_account_deletion_u8c_sentry_chain.py (LF, pure ASCII, no credential-shaped literal). You edit nothing under app/, no existing test, not the spec. You STOP after proving the reds: the orchestrator gates the test before the one-line fix.',
  CONTEXT,
  'WRITE the tests of spec section 5 as corrected and ruled: the RED nodes (the four failure shapes through the real route under TestClient in a child process with init_sentry + in-memory transport + traces 1.0: the 500 event carries exactly one exception value, the HTTPException, and no envelope item of any type contains the email, the URL host or the sentinel; the route log event present exactly once) and the PIN nodes (status, envelope and the U8b type-only log line unchanged; the success path with every flag False as the negative control; whatever else section 5 lists). Each test carries its id in its name.',
  'PROOF, all through the bounded runner (one pytest at a time): (a) the new file at HEAD: every RED fails FOR THE STATED REASON (the leak flag set, or the exception list longer than one; paste the proving line per id), every PIN passes, zero collection errors, no [netguard] line naming a node of the file; (b) satisfiability: with the spec swap plugin (' + SPECNOTES + '/u8c_swap_plugin.py, or your own in-memory monkeypatch of the handler that adds from None - NEVER an edit of app/) the whole file passes; (c) the two U8b files and tests/test_account_deletion.py stay green with your file present in one process; (d) py_compile and ruff --select E9,F63,F7,F82 --no-cache on the new file; (e) hygiene: the file is LF and pure ASCII, holds no sk- shaped string, no email that looks real (use the .test or .example reserved domains), and git status shows exactly the new file plus the spec.',
  'If a test in the spec cannot be written as specified (the SDK or framework behaves differently from the spec claim), do NOT bend it silently: measure, write the closest honest test, and list the deviation with its measurement. If a spec RED passes at base or a spec PIN fails at base, stop on that test, report it, and continue with the others.',
  'Notes: ' + NOTES + ' (create it; keep a running notes.md from the first measurement on). Return files changed with final sha256, gates (verbatim [pyt] lines), the red_table, deviations from the spec, git status, residual risk, summary. Budget: 75 minutes from your first tool call.',
].join('\n'), { label: 'u8c:red', phase: 'Red', model: 'opus', schema: WORK_SCHEMA })
return { red }
