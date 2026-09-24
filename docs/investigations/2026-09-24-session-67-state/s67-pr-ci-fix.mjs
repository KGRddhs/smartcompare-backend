export const meta = {
  name: 's67-pr-ci-fix',
  description: 'Close the two CI-red open PRs after their rebase onto main d70dd876: W4-3 (#177) three pins written against the pre-W4-10 label spelling; W4-9 (#178) two socket-guard nodes that attempt Serper DNS only in CI. One Opus 5.5 fixer per PR, then an adversary verifies; the orchestrator commits.',
  phases: [
    { title: 'Fix', detail: 'minimal, test-only where possible, CI condition reproduced locally', model: 'claude-opus-5-5' },
    { title: 'Verify', detail: 'independent check of the fix and its proof', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/75660a55-e14a-4de1-80dc-a537f2af315e/scratchpad'
const VENV = 'C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe'

const COMMON = `
ENVIRONMENT AND HARD RULES (violating any fails the task):
- Windows 11. Backend FastAPI, Python 3.12. ALWAYS run backend tests with the pinned venv ${VENV} (fastapi 0.141.1 / starlette 1.6.0 / pydantic 2.13.4 / supabase 2.31.0 / httpx 0.28.1 / pytest 9.1.1 = the exact CI pins); PYTHONIOENCODING=utf-8; -q -p no:cacheprovider -p no:randomly --timeout=120; sets add -m "not (live_unit or live_db or integration)". Lint: ${VENV} -m ruff check --select E9,F63,F7,F82 --no-cache; py_compile.
- Backend files are CRLF in the working copy: use the Edit tool; git diff --stat must show only intended lines.
- NEVER git commit/push/checkout/stash/reset/rebase/clean in any existing worktree; you write files only; the orchestrator commits. NEVER 'git checkout -- <file>'; byte-snapshot before every mutation, restore from it, sha256-verify. Work ONLY in your assigned worktree plus your scratchpad; other agents work in the other sc-* worktrees concurrently - never touch them. Never run a recursive delete. Never install packages. Never live_db/live_unit/integration, never LIVE=1, never the network, never any Railway MCP tool, never print an env value (report variable NAMES only).
- NEVER import app.* before tests/conftest.py has run; never run pytest without a process-wide non-loopback socket guard when the set can reach the network.
- Report honestly; paste real summary lines; final text is raw structured data. Your report MUST carry the final sha256 of every file you wrote.`

const UNITS = [
  { key: 'W4-3', pr: 177, dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w4-3', head: 'b840e941', unitFiles: 'tests/test_prescoring_showable_guard.py', log: MYSP + '/ci_log_177_107459439309.txt',
    task: `CI backend-tests failed 3 nodes and the SAME 3 fail locally on the rebased tree (b840e941 = the W4-3 commit rebased onto main d70dd876): tests/test_prescoring_showable_guard.py::test_r7b_pin_current_manufactured_cross_tier and ::test_10b_pin_flag_off_end_to_end_numbers_hold[unset|false] assert dimension-winner labels 'Bose Bose QuietComfort Ultra' / 'Sony Sony WH-1000XM5'. ROOT CAUSE (verified by the orchestrator): W4-10 (#176, merged after W4-3's base) made compute_scores spell dimension-winner labels through text_sanitize.dedup_brand_name, so the labels are now 'Bose QuietComfort Ultra' / 'Sony WH-1000XM5'. These three are PINS of flag-OFF current behaviour; the guard itself is unaffected.
YOUR TASK: (1) confirm the root cause yourself (git log --oneline 7368f862..d70dd876 -- app/services/scoring_service.py; read dedup_brand_name); (2) change ONLY the expected label strings in those three pins (and any other expectation in the file that pins the doubled spelling - grep for it) to the deduped spelling; touch NOTHING under app/; (3) run the unit file with the flag unset, with ENABLE_PRESCORING_SHOWABLE_GUARD=false and with =true (expect 50/50 each, as the PR recorded); (4) prove each edited pin still binds: with the flag unset, temporarily mutate the guard reader to return True (byte snapshot, sha-verified restore) and show the three pins (or the file) go red the way they did before the label change - i.e. the pins still detect the guard forking flag-OFF numbers; (5) run the neighbours the PR body names: tests/test_shopping_currency_truth.py tests/test_m18_region_guard_prescoring.py tests/test_m13_region_currency_guard.py tests/test_price_showable.py (203 expected); ruff + py_compile on the test file; (6) write a short 'Rebase note' paragraph for the PR body (${MYSP}/prbody_W4-3.md exists - do NOT edit it; return the paragraph in pr_text).` },
  { key: 'W4-9', pr: 178, dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w4-9', head: '0b5d540d', unitFiles: 'tests/test_w49_extraction_catch_redaction.py tests/test_m13_26_image_error_envelope.py tests/test_text_error_envelope_no_raw_exception.py', log: MYSP + '/ci_log_178_107459482414.txt',
    task: `CI backend-tests (ubuntu, the FULL free-tier suite in ONE pytest process, ~17.8k nodes) failed 2 nodes of tests/test_w49_extraction_catch_redaction.py at the socket_guard fixture's teardown (line ~136): 'W4-9 socket guard: real egress attempted' with 22 x ('getaddrinfo', "b'google.serper.dev'"); serper_service logged 'Search error: W4-9 socket guard: DNS for b'google.serper.dev' blocked' at 01:55:31Z. LOCALLY the file passes alone (15 passed on the rebased tree 0b5d540d = the W4-9 commit on main d70dd876) and passed in the green (46 nodes over the two unit files). So the failure is ORDER- or ENV-dependent. The full CI log is at the path above (read it: find the two FAILED node ids, the tests that ran just before them, and any env facts). Candidate causes to test, not guess: (a) a module-level SERPER_API_KEY/SERPER_API_KEYS read at import (app/services/serper_service.py:46) or tests/_env_safety.py sentinel values that make a search fire; (b) a preceding test that patches serper_service.SERPER_API_KEY or the key list at module level without restoring; (c) the pre-warmed import order in CI (.github/workflows/ci.yml backend-tests job) vs local. Reproduce the CI condition locally under a socket guard: run the file together with the preceding files from the CI order in ONE process (bisect the prefix until the 2 nodes fail), or set the env the way CI does - show the reproduction. THEN make the two tests HERMETIC regardless of order/env inside the unit's own test file (e.g. patch the Serper entry point the extraction path calls, or delenv/patch the key names in the fixture) WITHOUT weakening the socket guard's assertion and WITHOUT touching app/ (if the leak is a pre-existing test's unrestored module patch, name it and STILL make this file hermetic; report the offender as a follow-up). Re-run: the file alone, the reproduction order (now green), the two other unit files, ruff + py_compile; pr_text = a 'CI hermeticity note' paragraph for the PR body (${MYSP}/prbody_W4-9.md exists - do NOT edit it).` },
]

const FIX_SCHEMA = { type: 'object', required: ['unit', 'root_cause', 'files_changed', 'test_evidence', 'mutation_or_repro_proof', 'lint_clean', 'pr_text', 'git_status_final', 'file_sha256'], properties: {
  unit: { type: 'string' }, root_cause: { type: 'string' }, files_changed: { type: 'array', items: { type: 'string' } }, test_evidence: { type: 'string' },
  mutation_or_repro_proof: { type: 'string' }, lint_clean: { type: 'boolean' }, pr_text: { type: 'string' }, git_status_final: { type: 'string' }, file_sha256: { type: 'array', items: { type: 'string' } } } }
const VERIFY_SCHEMA = { type: 'object', required: ['unit', 'verdict', 'defects', 'summary', 'worktree_left_byte_identical'], properties: {
  unit: { type: 'string' }, verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] },
  defects: { type: 'array', items: { type: 'object', required: ['severity', 'location', 'claim', 'reproduced'], properties: { severity: { type: 'string', enum: ['blocking', 'major', 'minor'] }, location: { type: 'string' }, claim: { type: 'string' }, reproduced: { type: 'boolean' } } } },
  summary: { type: 'string' }, worktree_left_byte_identical: { type: 'boolean' } } }

const fixPrompt = (u) => `You are fixing the CI failure of PR #${u.pr} (unit ${u.key}) in worktree ${u.dir}, which is CLEAN at ${u.head} (git status --short must be empty - confirm FIRST; if not, stop and report). CI log: ${u.log}. Unit files: ${u.unitFiles}.
${u.task}
Leave the worktree with ONLY the intended files modified (uncommitted); report git status --short verbatim.
${COMMON}`

const verifyPrompt = (u, fix) => `You are an ADVERSARIAL verifier for the CI fix of PR #${u.pr} (unit ${u.key}) in worktree ${u.dir} (base commit ${u.head}; the fixer's UNCOMMITTED edits are exactly git diff HEAD). The fixer reported:
${JSON.stringify(fix, null, 1)}
The task it was given:
${u.task}
Assume it is wrong until checked: read the diff (nothing under app/ may have changed; the socket guard assertion must be intact for W4-9); re-run the unit files yourself in every flag state named; re-run the fixer's mutation/reproduction proof yourself (byte snapshots, sha-verified restores; never git checkout); for W4-9 confirm the reproduction actually failed before the fix and passes after (if the fixer could not reproduce, say so and judge whether the hermeticity change is still correct). Leave the worktree byte-identical to the fixer's state (report worktree_left_byte_identical). reproduced:true only if you ran it. Do not fix anything. If sound, say SOUND.
${COMMON}`

log('pr-ci-fix: ' + UNITS.map((u) => u.key).join(', '))
const results = await pipeline(
  UNITS,
  (u) => agent(fixPrompt(u), { label: 'fix:' + u.key, phase: 'Fix', model: MODEL, effort: 'high', schema: FIX_SCHEMA }),
  async (fix, u) => {
    if (!fix) return { unit: u.key, fix: null, verify: null, final_verdict: 'fixer died' }
    const v = await agent(verifyPrompt(u, fix), { label: 'verify:' + u.key, phase: 'Verify', model: MODEL, effort: 'high', schema: VERIFY_SCHEMA })
    return { unit: u.key, fix, verify: v, final_verdict: v ? v.verdict : 'verifier died' }
  }
)
const done = results.filter(Boolean)
log('pr-ci-fix: ' + done.map((r) => r.unit + '=' + r.final_verdict).join(', '))
return { results: done }
