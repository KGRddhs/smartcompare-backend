export const meta = {
  name: 's67-w42-polish',
  description: 'W4-2 polish after adversary r1 SOUND: pin that the /text/prices strip removes ONLY _discovery_url (mutant X15), correct two PR-text inaccuracies, re-run gates; one Opus 5.5 fixer then a verifier; the orchestrator commits.',
  phases: [
    { title: 'Polish', detail: 'one pin + PR text corrections', model: 'claude-opus-5-5' },
    { title: 'Verify', detail: 'independent check', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/75660a55-e14a-4de1-80dc-a537f2af315e/scratchpad'
const VENV = 'C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe'
const DIR = 'C:/Users/SynAckITPC/Documents/AI/sc-w4-2'

const COMMON = `
ENVIRONMENT AND HARD RULES (violating any fails the task):
- Windows 11. Backend FastAPI, Python 3.12. ALWAYS run backend tests with the pinned venv ${VENV} (the exact CI pins); PYTHONIOENCODING=utf-8; -q -p no:cacheprovider -p no:randomly --timeout=120; sets add -m "not (live_unit or live_db or integration)"; run under the unit's process-wide guard plugin (-p w42_netguard with PYTHONPATH=.qa-w4/comm_tools/stubs, as the green did). Lint: ${VENV} -m ruff check --select E9,F63,F7,F82 --no-cache; py_compile.
- Backend files are CRLF in the working copy: use the Edit tool; git diff --stat must show only intended lines.
- NEVER git commit/push/checkout/stash/reset/rebase/clean in any existing worktree; you write files only; the orchestrator commits. NEVER 'git checkout -- <file>'; byte-snapshot before every mutation, restore from it, sha256-verify. Work ONLY in ${DIR} plus your scratchpad. Never run a recursive delete. Never install packages. Never live_db/live_unit/integration, never LIVE=1, never the network, never any Railway MCP tool, never print an env value. NEVER run _proof/sweep2.py; the _proof corpus is read-only. A copy of .env may live only inside a detached scratch worktree you remove afterwards.
- Never import app.* before tests/conftest.py has run. Your report MUST carry the final sha256 of every file you wrote.`

const TASK = `Unit W4-2 (ENABLE_SHOPPING_DISCOVERY_URL_SPLIT) in worktree ${DIR}: branch feature/s65-w4-2-shopping-url-split at wip f6d0d3b4 (the committed red) with the green + fix-round edits UNCOMMITTED on top (git status --short must show exactly M app/services/price_service.py, M app/services/structured_comparison_service.py, M tests/test_shopping_price_not_self_pending.py - confirm FIRST; anything else, stop and report). The spec is ${DIR}/.qa-w4/W4_2_UNIT_SPEC.md (its last section, the FABLE REVIEW RULINGS, binds). The full workflow record (green, adversary r0, fix, adversary r1 - all SOUND) is ${MYSP}/harvest_w42.json - read the r1 adversary's three minors and the fix report's pr_text.
YOUR TASK (polish, minimal): (1) ADD one GREEN-PHASE PIN in tests/test_shopping_price_not_self_pending.py proving the get_regional_prices strip (the fixer's hunk in structured_comparison_service.py) removes ONLY the private _discovery_url key: a bahrain entry carrying other underscore-prefixed keys (e.g. _cached, _seed) must keep them on the wire exactly as base does, while _discovery_url is stripped; mutation-check it: X15 (strip every key starting with '_') must go RED, and reverting the strip entirely must go RED on the existing test_19 (re-run it). (2) Correct pr_text (return the FULL corrected pr_text): the mutation count is 27 (16 M + 8 N + 3 D; M0 is a control, not a mutation); the KPI/canary sentence must attribute the usable_exact_genuine drop to W4-1 alone (under R1 the split reader is False whenever ENABLE_SHOPPING_CURRENCY_TRUTH is off, so W4-2 changes nothing with W4-1 off; measured: the Amazon no-link row is already converted_usd at base with TRUTH on) and state W4-2's actual extra effect on the KPI honestly. (3) Re-run the unit file with flags unset, with the split flag on, and with both split + TRUTH on; the 8-file Preserve set (164); ruff + py_compile. Leave only the intended files modified; report git status --short verbatim and the final sha256 of every file you wrote.`

const FIX_SCHEMA = { type: 'object', required: ['unit', 'files_changed', 'test_evidence', 'mutation_checks', 'lint_clean', 'pr_text', 'git_status_final', 'file_sha256'], properties: {
  unit: { type: 'string' }, files_changed: { type: 'array', items: { type: 'string' } }, test_evidence: { type: 'string' }, mutation_checks: { type: 'array', items: { type: 'string' } },
  lint_clean: { type: 'boolean' }, pr_text: { type: 'string' }, git_status_final: { type: 'string' }, file_sha256: { type: 'array', items: { type: 'string' } } } }
const VERIFY_SCHEMA = { type: 'object', required: ['unit', 'verdict', 'defects', 'summary', 'worktree_left_byte_identical'], properties: {
  unit: { type: 'string' }, verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] },
  defects: { type: 'array', items: { type: 'object', required: ['severity', 'location', 'claim', 'reproduced'], properties: { severity: { type: 'string', enum: ['blocking', 'major', 'minor'] }, location: { type: 'string' }, claim: { type: 'string' }, reproduced: { type: 'boolean' } } } },
  summary: { type: 'string' }, worktree_left_byte_identical: { type: 'boolean' } } }

log('w42-polish: start')
const fix = await agent(`You are the POLISHER for unit W4-2.\n${TASK}\n${COMMON}`, { label: 'polish:W4-2', phase: 'Polish', model: MODEL, effort: 'high', schema: FIX_SCHEMA })
if (!fix) return { fix: null, verify: null, final_verdict: 'polisher died' }
const verify = await agent(`You are an ADVERSARIAL verifier for the W4-2 polish in worktree ${DIR} (wip f6d0d3b4 + uncommitted green/fix/polish edits = git diff HEAD). The polisher reported:\n${JSON.stringify(fix, null, 1)}\nThe task it was given:\n${TASK}\nAssume it is wrong until checked: read the diff (the polish must be test-only plus nothing outside the three files; the strip hunk itself unchanged); re-run the new pin, mutation X15 and the strip-revert yourself from byte snapshots (sha-verified restores, never git checkout); re-run the unit file in the three flag states and the Preserve set; check the two pr_text corrections against the measurements. Leave the worktree byte-identical to the polisher's state. reproduced:true only if you ran it. Do not fix anything. If sound, say SOUND.\n${COMMON}`, { label: 'verify:W4-2-polish', phase: 'Verify', model: MODEL, effort: 'high', schema: VERIFY_SCHEMA })
log('w42-polish: ' + (verify ? verify.verdict : 'verifier died'))
return { fix, verify, final_verdict: verify ? verify.verdict : 'verifier died' }
