export const meta = {
  name: 's71-u8c-green',
  description: 'Session 71 U8c GREEN under the synack-build-orchestrator loop (Opus agents; the Fable orchestrator gated the RED test PASS): the one-line from-None fix on the deletion route, bounded gates, byte-copy mutants on the edited file, one Opus adversary (Sentry leak lens), fix round. The orchestrator reviews the diff before any commit.',
  phases: [
    { title: 'Green', detail: 'the one-line edit, gates, MU1-MU8 on the edited file', model: 'opus' },
    { title: 'Adversary', detail: 'Sentry leak lens: try to make the chained text reach any envelope item', model: 'opus' },
    { title: 'Fix', detail: 'apply surviving findings', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-u8b'
const SPEC = WT + '/docs/investigations/2026-10-03-session-71-state/U8C_SENTRY_CHAIN_SPEC.md'
const NOTES = SP + '/u8c'
const HEADSHA = 'b90b5f07'
const TEST = 'tests/test_account_deletion_u8c_sentry_chain.py'

const CONTEXT = [
  'BACKEND UNIT U8c of the MYEZ launch lane (repo smartcompare; FastAPI in app/ - the DEPLOYED backend; never edit backend/app/). Worktree ' + WT + ' (branch feature/s71-u8c-sentry-chain, HEAD = main ' + HEADSHA + '; untracked: the spec and the frozen RED test). Today is 2026-10-03 (session 71). Issue #292: DELETE /auth/account raises HTTPException(500) inside its except arm, so the Sentry Starlette integration ships the chained exception text (email, URL) for httpx.ConnectError, AuthApiError, RuntimeError and the sentinel word of an APIError message.',
  'Read the agent rules file FIRST and obey it: ' + RULES + '. Every pytest run goes through the bounded runner; never touch the network, Railway, Supabase or a real Sentry DSN; never print a credential.',
  'THE SPEC IS AUTHORITATIVE: ' + SPEC + ' (sha256 57428e4705a15e31...). Read it IN FULL. It ends with THREE binding sections that supersede its body, later ones winning: "## Review corrections (BINDING ...)" (C1-C9), "## Orchestrator rulings (BINDING ...)" (UR1-UR10) and "## Orchestrator gate on the RED tests (BINDING ...)" (UG1-UG4: the ONE edited line, the gates, no comm gate, the follow-up).',
  'THE RED TEST EXISTS AND PASSED THE ORCHESTRATOR GATE: ' + TEST + ' (sha256 prefix 233a3807faa668b7; byte copy in ' + NOTES + '/red_frozen, never edit it or the copy). At HEAD: 8 failed / 16 passed. The RED agent notes, logs and its in-memory swap harness are in ' + NOTES + '/red (read-only reference).',
].join('\n')

const WORK_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'pr_text', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes' },
  gates: { type: 'array', items: { type: 'string' }, description: 'verbatim [pyt] lines and summary lines' },
  deviations_from_spec: { type: 'array', items: { type: 'string' } },
  git_status_final: { type: 'string' }, residual_risk: { type: 'string' }, pr_text: { type: 'string' }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'defects', 'minors', 'files_sha256_at_start', 'worktree_left_byte_identical', 'summary'], properties: {
  verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] }, defects: { type: 'array', items: { type: 'string' } },
  minors: { type: 'array', items: { type: 'string' } }, files_sha256_at_start: { type: 'array', items: { type: 'string' } },
  worktree_left_byte_identical: { type: 'boolean' }, summary: { type: 'string' } } }

phase('Green')
const green = await agent([
  'ROLE: GREEN agent (implementation). Make exactly the UG1 edit (one line of app/api/auth_routes.py, CRLF kept, Edit tool; byte-copy snapshot first), then run every UG2 gate through the bounded runner, one pytest at a time: the new file alone; the kill set in one process; the Sentry and regression files in one process; py_compile + ruff on the edited file; the spec G5 mutants MU1-MU8 as byte-copy mutations of the EDITED file (each: copy, mutate, run the named files, must FAIL, restore, sha256 equal; never git checkout --); git diff --stat (one file, one line). Commit nothing.',
  CONTEXT,
  'PR text (pr_text): the issue, the measured leak at HEAD (the four shapes, what reaches Sentry), the one-line fix and why it works only because the 500 stays a FastAPI HTTPException handled in-route (C1), the test design (child process, real init_sentry, in-memory transport, traces 1.0, the sentinel control through the real scrubber), the gates (verbatim lines), the stated limits (the five other except-arm 5xx sites and the ErrorHandlerMiddleware exc_info line are a follow-up issue; the two Sentry-clean log mutants are killed by the U8b pins, not by this file), process (Opus spec, review, rulings, RED gated PASS, GREEN, adversary). End with the line: Generated with Claude Code.',
  'Notes: ' + NOTES + '/green (create it; running notes from the first measurement). Return files changed with final sha256, gates, deviations, git status, residual risk, pr_text, summary. Budget: 75 minutes from your first tool call.',
].join('\n'), { label: 'u8c:green', phase: 'Green', model: 'opus', schema: WORK_SCHEMA })

phase('Adversary')
const adv = await agent([
  'ROLE: ADVERSARY (Sentry leak lens). Try to REFUTE that the fixed route keeps the chained exception text out of every Sentry envelope item, and that the test would notice if it did not. Read-only except byte-copy mutations restored by sha256; leave the worktree byte-identical (hash the edited file and the frozen test at start and end). Scratch under your notes folder; run tests only through the bounded runner, Sentry only with the in-memory transport in a child process.',
  CONTEXT,
  'Green report: ' + JSON.stringify(green ? { files: green.files_changed, gates: green.gates, deviations: green.deviations_from_spec, residual_risk: green.residual_risk } : {}),
  'Checks: (1) re-run the new file, the kill set and the Sentry files yourself on the GREEN bytes; (2) with your own child-process probe (the W1-1b idiom; the RED notes show a working one) drive the fixed route through the four shapes plus three of your own (an exception whose str() is the email alone; an exception group / a cause chain two deep raised inside the try; an exception raised by the cache purge after the cascade) and sweep EVERY envelope item type (exception events, log events, transactions, sessions, breadcrumbs, extra, tags, contexts, request data incl. headers and the URL) for the sentinels; (3) test the logging path with the root logger at DEBUG and with LOG_LEVEL=DEBUG in the child, and with the Sentry logging integration event level lowered, to see whether any logger in the deletion path formats the exception text; (4) mutants of your own on byte copies (restore by sha256): from None replaced by from e; the HTTPException detail built from str(e); a logger.exception call added; the raise moved outside the route into a helper that re-raises; (5) confirm the edit is one line, CRLF kept, nothing else in the diff, and the frozen test is byte-equal to ' + NOTES + '/red_frozen.',
  'Notes: ' + NOTES + '/adv (create it). Verdict SOUND only if you found no serious defect. Return verdict, defects (each with file:line, the measurement and a failure scenario), minors, sha lists, byte-identical flag, summary. Budget: 60 minutes from your first tool call.',
].join('\n'), { label: 'u8c:adv', phase: 'Adversary', model: 'opus', schema: ADV_SCHEMA })

const findings = adv ? (adv.defects || []).map(d => 'DEFECT: ' + d).concat((adv.minors || []).map(m => 'MINOR: ' + m)) : []
let fix = null
if (findings.length) {
  phase('Fix')
  fix = await agent([
    'ROLE: FIX agent. Apply every DEFECT and every MINOR you verify is real and that the spec, rulings and gate allow (UG1 allows exactly the one line; a finding that needs more, a test edit or a ruling is reported for the orchestrator with your measurement). First re-hash the edited file and the frozen test: if a mutant was left on disk, restore it from the adversary byte copy (never git checkout --). Afterwards re-run the UG2 gates.',
    CONTEXT,
    'Green report files: ' + JSON.stringify(green ? green.files_changed : []),
    'Findings:\n' + findings.join('\n') + '\nNotes: ' + NOTES + '/fix (create it).',
    'Return files changed with final sha256, gates, deviations (incl. rejected findings with the refuting measurement and findings left for the orchestrator), git status, residual risk, the updated full pr_text, summary. Budget: 60 minutes from your first tool call.',
  ].join('\n'), { label: 'u8c:fix', phase: 'Fix', model: 'opus', schema: WORK_SCHEMA })
}
return { green, adversary: adv, fix }
