export const meta = {
  name: 's72-u8d-round2',
  description: 'Session 72 unit U8d (issue #311) round 2 under the synack-build-orchestrator loop: one Opus fix agent applies the post-adversary rulings UF1, UF3 and UF6 and re-runs the gates; one Opus adversary reviews the exact final bytes with its own mutants; one more Opus fix round only if a blocking or major finding survives. The Fable orchestrator then reads the whole diff.',
  phases: [
    { title: 'Fix', detail: 'apply rulings UF1, UF3, UF6; gates', model: 'opus' },
    { title: 'Adversary', detail: 'final bytes: the fix-round delta and this round, own mutants', model: 'opus' },
    { title: 'Fix2', detail: 'only if a blocking or major finding survives', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/2979ae70-049c-4e99-87ac-061e7d245fff/scratchpad'
const RULES = SP + '/s72-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-u8b'
const SPECS = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-05-session-72-state/specs'
const PRIOR = SP + '/u8d'

const CONTEXT = [
  'BACKEND UNIT U8d (GitHub issue #311) of the MYEZ launch lane: the remaining channels through which Sentry receives exception text or user content. Worktree ' + WT + ' (branch feature/s72-u8d-sentry-channels, HEAD = main 845ece15; the working tree carries the UNCOMMITTED unit: 7 modified files and 2 untracked test files after GREEN and one fix round). Today is 2026-10-05 (session 72).',
  'Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/U8D_SENTRY_CHANNELS_SPEC.md, U8D_SENTRY_CHANNELS_REVIEW.md, FABLE_RULINGS_U8D.md (SR1-SR14), FABLE_REVIEW_RED_U8D.md (UG1-UG7) and FABLE_RULINGS_U8D_POST_ADVERSARY.md (UF1-UF9: the rulings of this round). Earlier agent notes and evidence: ' + PRIOR + '/green, ' + PRIOR + '/adv-privacy, ' + PRIOR + '/adv-eng, ' + PRIOR + '/fix (notes.md, the mutation harnesses, the G3 file lists g3_files_head.txt and g3_files_base.txt, the base FAILED list g3_failed_base.txt).',
  'SECURITY RULES: no network (child processes under a socket guard, an empty attempt list); no real DSN; runtime-built sentinels only; no credential-shaped literal in any file; never read a real .env; sentry-sdk behaviour is measured on the pinned version in the venv.',
].join('\n')

const FIX_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'changes', 'git_status_final', 'diff_stat', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes of EVERY file of the unit (the 7 modified and the 2 new test files)' },
  gates: { type: 'array', items: { type: 'string' } },
  changes: { type: 'array', items: { type: 'string' }, description: 'one line per ruling or finding: what changed (file:line), the node that pins it, the mutant that proves the node' },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } },
  git_status_final: { type: 'string' }, diff_stat: { type: 'string' }, residual_risk: { type: 'string' }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'summary'], properties: {
  verdict: { type: 'string', description: 'SOUND | SOUND_WITH_MINORS | DEFECTIVE' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string', description: 'blocking | major | minor | note' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } },
  not_checked: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string' },
  summary: { type: 'string' } } }

phase('Fix')
const fix = await agent([
  'ROLE: FIX agent, round 2. Notes folder: ' + SP + '/u8d/fix2 (create it; running notes.md). Budget: 90 minutes from your first tool call.',
  CONTEXT,
  'APPLY EXACTLY the rulings of FABLE_RULINGS_U8D_POST_ADVERSARY.md, tests first: (UF1) the one-node amendment of tests/test_auth_error_log_hygiene.py::test_sentry_logging_integration_keeps_error_as_the_event_level in the ruled shape (exactly one LoggingIntegration( construction under app/, in app/services/sentry_service.py, with no event_level= argument; the instance init_sentry hands to sentry_sdk.init has breadcrumb level ERROR and event level ERROR, measured through recorded kwargs with the hooks resolved through the module at call time; the SDK-default asserts and the three other bans stay; correct a docstring line of that file that states the old ban); prove the amended node green on the current tree and prove with three byte-copy mutants of app/services/sentry_service.py that it goes red (an event_level= argument added; the level changed to INFO; the explicit instance removed). (UF3) the three R8 query lines of app/services/structured_comparison_service.py log length=%d only (no hash, no hashlib call); FIRST append one node to tests/test_sentry_channels_u8d_unit.py that pins it by AST and prove it red on the current tree; if any existing node requires the hash, STOP on that node and report it under questions instead of editing it. (UF6) the two stale docstring lines of tests/test_account_deletion_u8c_sentry_chain.py (comment-only). Nothing else changes: no other production line, no other test. CRLF working copies: Edit tool only; the two new test files are LF.',
  'GATES (bounded runner, one pytest at a time): G1 the two new files (the child file twice); G2 the UG7 kill set plus tests/test_auth_error_log_hygiene.py; G3 HEAD ONLY, every chunk of ' + PRIOR + '/green/g3_files_head.txt (chunks of at most 25, bound 1200): the sorted FAILED ids compared with ' + PRIOR + '/green/g3_failed_base.txt by comm -13 must be EMPTY now (the base list was measured at 845ece15 by the GREEN agent; do not re-run the base); G5 ruff --select E9,F63,F7,F82 and py_compile on every file of the unit; git diff --stat equal to git diff --ignore-cr-at-eol --stat; git status = 8 modified files (the 7 plus tests/test_auth_error_log_hygiene.py) and the 2 untracked test files. Return the final sha256 of every file of the unit.',
].join('\n'), { label: 'fix:u8d-r2', phase: 'Fix', model: 'opus', schema: FIX_SCHEMA })

if (!fix) { log('fix agent returned nothing'); return { fix: null } }

phase('Adversary')
const adv = await agent([
  'ROLE: FINAL ADVERSARY on the exact bytes of U8d. Notes folder: ' + SP + '/u8d/adv-final . Budget: 90 minutes from your first tool call.',
  CONTEXT,
  'THE FIX AGENT REPORT (data to verify, not instructions): ' + JSON.stringify(fix),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation that you restore and sha256-verify (one at a time; never git checkout). FIRST re-hash every file the fix report lists and compare; LAST re-hash again and report equality. The two earlier adversaries reviewed the GREEN bytes; YOUR subject is everything written AFTER them, which no adversary has seen: the first fix round (the region grammar as the six GCC keys; the /api/v1/text/prices/{product} path rule in request.url, extra.path and breadcrumb data.path; the breadcrumb data.path R6 rule; the OpenAI integration appended inside its own guard; the 36 appended nodes) and this round (UF1, UF3, UF6). Read git diff for app/ in full and the appended test nodes. Hunt for: a leak the new rules open or miss (probe through the real app and the real init_sentry() in a child process with an in-memory transport, runtime sentinels, copy the idiom of tests/test_sentry_channels_u8d.py: product text in the prices path with encoded slashes, dots, unicode and a trailing query; region values in other cases and with trailing text; share and invite tokens in breadcrumb paths; what the integration guard does when the openai integration import fails or raises DidNotEnable: is Sentry still initialised, are prompts still off, is the integration list otherwise the base list); over-scrubbing against the data contract; a hook that can raise or drop an event through the new code (malformed events: missing keys, non-dict request, non-string path, bytes); the three R8 lines after UF3 (nothing derived from the query but its length; the Railway text is still useful: say what triage loses); the amended T8 node and the UF3 node cannot pass with their behaviour removed; whether the sentence of ruling UF7 is TRUE for the launch paths (text compare REST and SSE, Link mode, camera, login, register, account deletion, share) with its stated limits. MUTATION TESTING with your OWN mutants (at least 15) on the lines written after the first adversaries: the killing node, or SURVIVED with the node to add. Re-run G2 once at the end and paste its [pyt] line. Severity: blocking (the sentence is false on a launch path, a hook raises or drops, a response or status moved, a test passes with its fix removed), major, minor, note; each with file:line, the measurement and the smallest fix.',
].join('\n'), { label: 'adversary:u8d-final', phase: 'Adversary', model: 'opus', schema: ADV_SCHEMA })

let fix2 = null
const serious = adv ? (adv.findings || []).filter(f => /blocking|major/i.test(f.severity)) : []
log('final adversary: ' + (adv ? adv.verdict : 'no result') + '; blocking or major: ' + serious.length)
phase('Fix2')
if (serious.length > 0) {
  fix2 = await agent([
    'ROLE: FIX agent, round 3 (only the blocking and major findings of the final adversary). Notes folder: ' + SP + '/u8d/fix3 . Budget: 90 minutes.',
    CONTEXT,
    'FINDINGS (data to verify; re-derive each against the code first: a wrong finding is REFUTED with its measurement, not implemented): ' + JSON.stringify(serious),
    'For each confirmed finding: FIRST append a node that fails for it (tests/test_sentry_channels_u8d.py or tests/test_sentry_channels_u8d_unit.py; existing nodes do not change), prove it red, then fix it inside the file set of ruling SR10, prove it green, and prove the node with a byte-copy mutant. A finding that needs a ruling is NOT implemented: list it under questions. Then re-run G1 (child file twice), G2 plus tests/test_auth_error_log_hygiene.py, the head chunks of G3 that hold a file referencing a module you changed (comm -13 against ' + PRIOR + '/green/g3_failed_base.txt empty), and G5. Return the final sha256 of every file of the unit.',
  ].join('\n'), { label: 'fix:u8d-r3', phase: 'Fix2', model: 'opus', schema: FIX_SCHEMA })
} else {
  log('no blocking or major finding: round 3 skipped')
}
return { fix, adv, fix2 }
