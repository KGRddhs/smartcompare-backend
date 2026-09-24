export const meta = {
  name: 's66-w4-polish',
  description: 'Pre-merge polish for W4 batch-5 units whose final adversary returned SOUND with reproduced MINOR defects: one fixer per unit closes the named minors with pins, then a short adversary re-check confirms nothing regressed (backend units; pinned venv)',
  phases: [
    { title: 'Polish', detail: 'fixer per unit, minimal, pinned', model: 'claude-opus-5-5' },
    { title: 'Recheck', detail: 'adversary re-check of the polished diff', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/a47353ce-a0e3-4273-b85d-f21cfa01e031/scratchpad'
const VENV = 'C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe'

const COMMON = [
  'ENVIRONMENT AND HARD RULES (violating any of these fails the task):',
  '- Windows 11. Worktree root = FastAPI backend (Python 3.12). ALWAYS run backend tests with the pinned venv ' + VENV + ' (fastapi 0.141.1 / pydantic 2.13.4 / supabase 2.31.0 / pytest 9.1.1 = the CI pins); PYTHONIOENCODING=utf-8; -q -p no:cacheprovider -p no:randomly --timeout=300; sets add -m "not (live_unit or live_db or integration)". Lint: ruff check --select E9,F63,F7,F82 --no-cache + py_compile.',
  '- Backend files are CRLF in the working copy: use the Edit tool; git diff --stat must show only intended lines.',
  '- NEVER git commit/push/checkout/stash/reset/rebase/clean. Never `git checkout -- <file>`: everything is UNCOMMITTED unit work. Byte-snapshot before every mutation; restore from the snapshot; sha256-verify.',
  '- Work ONLY in your assigned worktree plus your OWN subfolder of the scratchpad (the root is shared). Never call any Railway MCP tool; never print an env value; never the network (autouse socket guard in every new/changed test file: block non-loopback connect and getaddrinfo, fail the test on any attempt); never LIVE=1 / live_db / live_unit / integration.',
  '- The spec (its FABLE REVIEW RULINGS binding) and the red-gate rulings bind. Report honestly; paste real output; final text is raw data.',
].join('\n')

const UNITS = (args && Array.isArray(args.units) && args.units.length) ? args.units : []
if (!UNITS.length) throw new Error('args.units required: [{key, dir, spec, results, resultKey, minors}]')

const FIX_SCHEMA = {
  type: 'object',
  required: ['unit', 'files_changed', 'minors_addressed', 'all_unit_tests_pass', 'test_evidence', 'lint_clean_backend', 'comm_or_preserve_evidence', 'mutation_checks', 'pr_body_facts_delta', 'git_status_final', 'residual_risk'],
  properties: {
    unit: { type: 'string' }, files_changed: { type: 'array', items: { type: 'string' } },
    minors_addressed: { type: 'array', items: { type: 'string' }, description: 'one per numbered minor: FIXED (how, pin name, mutation count) or DISPUTED (with the measurement)' },
    all_unit_tests_pass: { type: 'boolean' }, test_evidence: { type: 'string' }, lint_clean_backend: { type: 'boolean' },
    comm_or_preserve_evidence: { type: 'string' }, mutation_checks: { type: 'array', items: { type: 'string' } },
    pr_body_facts_delta: { type: 'array', items: { type: 'string' } }, git_status_final: { type: 'string' }, residual_risk: { type: 'string' },
  },
}
const ADV_SCHEMA = {
  type: 'object',
  required: ['unit', 'verdict', 'defects', 'tests_that_prove_nothing', 'worktree_left_byte_identical', 'summary'],
  properties: {
    unit: { type: 'string' }, verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] },
    defects: { type: 'array', items: { type: 'object', required: ['severity', 'location', 'claim', 'why_it_matters', 'reproduced'], properties: {
      severity: { type: 'string', enum: ['blocking', 'major', 'minor'] }, location: { type: 'string' }, claim: { type: 'string' }, why_it_matters: { type: 'string' }, reproduced: { type: 'boolean' } } } },
    tests_that_prove_nothing: { type: 'array', items: { type: 'string' } }, worktree_left_byte_identical: { type: 'boolean' }, summary: { type: 'string' },
  },
}

phase('Polish')
const results = await pipeline(
  UNITS,
  (u) => agent(`You are the pre-merge POLISH fixer for unit ${u.key} in worktree ${u.dir}. The unit's final adversary returned SOUND with reproduced MINOR defects; the orchestrator (Fable) rules that the following must be closed BEFORE the commit, minimally and inside the spec's design (${u.dir}/${u.spec}; the FABLE REVIEW RULINGS at its end bind; the unit's green/fix/adversary reports are in ${u.results} under the keys ${JSON.stringify(u.resultKeys)} - read the LAST adversary entry there first, and the fix/green report's pr_text, which you must update via pr_body_facts_delta):
${u.minors}

Work order: git status --short and git diff --stat FIRST and keep every existing change (all of it is uncommitted unit work - never git checkout). For each numbered item: re-derive it from the code, fix minimally, add or adjust a load-bearing pin, mutation-check it from a byte snapshot with a sha-verified restore, and record the count. Then re-run the unit's own test file(s) and the Preserve set the spec names on the pinned venv, ruff + py_compile. Report pr_body_facts_delta (sentences to add to or replace in the PR body). Leave ONLY intended changes; report git status --short verbatim.
${COMMON}`, { label: 'polish:' + u.key, phase: 'Polish', model: MODEL, effort: 'high', schema: FIX_SCHEMA }),
  (fix, u) => fix ? agent(`You are the ADVERSARY re-checking the pre-merge polish of unit ${u.key} in worktree ${u.dir} (spec ${u.dir}/${u.spec}, rulings at its end binding; prior reports in ${u.results}). The polish fixer reported:
${JSON.stringify(fix, null, 1)}
The minors it was asked to close:
${u.minors}
1. git diff / git status: review the polish hunks in the context of the whole unit diff. Confirm each minor is genuinely closed (re-run its mutation from a byte snapshot) and that the polish introduced no regression: re-run the unit file(s) and the Preserve set on the pinned venv.
2. Anything the fixer DISPUTED: verify the measurement.
3. Leave the worktree byte-identical (sha before/after). reproduced:true only when you ran it. If sound, say SOUND.
${COMMON}`, { label: 'recheck:' + u.key, phase: 'Recheck', model: MODEL, effort: 'medium', schema: ADV_SCHEMA }).then((adv) => ({ unit: u.key, fix, recheck: adv, final_verdict: adv ? adv.verdict : 'recheck died' })) : { unit: u.key, fix: null, recheck: null, final_verdict: 'polish died' }
)
const done = results.filter(Boolean)
log('w4 polish: ' + done.map((r) => r.unit + '=' + r.final_verdict).join(', '))
return { results: done }
