export const meta = {
  name: 's66-w3-polish',
  description: 'Pre-merge polish for W3 units whose final adversary returned SOUND with reproduced MINOR defects that are real product/security issues: one fixer per unit closes the named minors with pins, then a short adversary re-check confirms nothing regressed',
  phases: [
    { title: 'Polish', detail: 'fixer per unit, minimal, pinned', model: 'claude-opus-5-5' },
    { title: 'Recheck', detail: 'adversary re-check of the polished diff', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/a47353ce-a0e3-4273-b85d-f21cfa01e031/scratchpad'
const SP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/45fe3c1b-4c76-4d34-a783-b5624da26d5e/scratchpad/b6'

const COMMON = [
  'ENVIRONMENT AND HARD RULES (violating any of these fails the task):',
  '- Windows 11. Worktree root = FastAPI backend (Python 3.12); SmartCompareApp/ = Expo/RN/TS client. Base b63a8368; origin/main 64afd23b is docs-only ahead.',
  '- SmartCompareApp/node_modules is a JUNCTION into a shared install: never delete it, never recursive-delete anything, never npm install/ci, never edit package.json or lockfiles.',
  '- Client tools by PATH from SmartCompareApp: node node_modules/typescript/bin/tsc --noEmit ; node node_modules/jest/bin/jest.js --ci <paths> ; node node_modules/eslint/bin/eslint.js <files>. Full suite once at the end if any client file changed: node node_modules/jest/bin/jest.js --ci --maxWorkers=25%, compared with ' + SP + '/baseline.txt plus this unit\'s own added suites; never -u.',
  '- Backend: PYTHONIOENCODING=utf-8 python -m pytest tests/<file> -q -p no:randomly -p no:cacheprovider ; -m "not (live_unit or live_db or integration)" for sets; ruff check --select E9,F63,F7,F82 + py_compile. Prefer the pinned venv python at C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe for backend runs (it matches CI: fastapi 0.141.1 / pydantic 2.13.4 / supabase 2.31.0 / pytest 9.1.1) and report if a result differs from the global python.',
  '- Backend files are CRLF in the working copy: use the Edit tool; git diff --stat must show only the intended lines.',
  '- NEVER git commit/push/checkout/stash/reset/rebase/clean. Never `git checkout -- <file>`: everything is UNCOMMITTED. Byte-snapshot before every mutation; restore from the snapshot; sha256-verify.',
  '- Work ONLY in your assigned worktree plus your own scratchpad. Never call any Railway MCP tool; never print an env value.',
  '- The spec (its final rulings section binding) and the Fable red-gate rulings quoted in your prompt bind. Report honestly; paste real output; final text is raw data.',
].join('\n')

const DEFAULT_UNITS = [
  { key: 'W3-6', dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w3-pwreset', spec: '.qa-w3b/W3_6_UNIT_SPEC.md', backend: true,
    minors: `(1) app/services/auth_service.py complete_password_recovery: a Supabase TRANSPORT failure during get_user is reported as RECOVERY_TOKEN_INVALID, and the screen then shows the 'link expired' dead-end card although the token is still valid. Fix: distinguish the transport/upstream class (the same class W1-4 maps to 503 REFRESH_UPSTREAM_UNAVAILABLE at auth_routes.py:~636-643) from a genuine invalid/expired token; return a retryable code (reuse the existing upstream-unavailable code/shape) for transport failures; the screen keeps the form and shows a retry copy for that code. Pin both branches (backend node + screen node), mutation-checked.
(2) __tests__/ResetPasswordScreen.w36.test.tsx weak-password node: isWeakPassword reduced to length-only survives — add a pin per rule (uppercase, lowercase, digit) so each rule reddens when dropped.
(3) usePreventScreenCapture() on the new-password screen is unpinned — add a pin that the hook is invoked on mount (mock the module).
(4) After a failure, loading must clear so the submit button re-enables — pin it (mutation: never clear loading -> red).
Do NOT touch jest.config.js beyond what is already there; do NOT change src/navigation/linking.ts's shape (the orchestrator reconciles it with W3-15 at merge).` },
  { key: 'W3-13', dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w3-ci', spec: '.qa-w3b/W3_13_UNIT_SPEC.md', backend: true,
    minors: `(1) The DATED non-blocking flip in ci.yml (three places) is already in the past on 2026-09-23. Re-date it to 2026-10-07 (two weeks from today) in all three places and in the runbook/PR-body sentence, keeping test_channel_freshness_is_non_blocking_until_the_dated_flip green and pinning the new date; the job still skips green without EXPO_TOKEN.
(2) scripts/check_channel_freshness.py main(): only ChannelError maps to the UNRESOLVABLE exit code; any other exception (UnicodeDecodeError while reading, JSON errors, subprocess errors) escapes as a traceback with exit status 1, which COLLIDES with the STALE code and carries no ::error:: annotation. Fix: catch Exception in main(), emit a ::warning:: annotation naming the exception class, and exit with the UNRESOLVABLE code; pin it (mutation: drop the catch -> red).
(3) The resolve-step -> check-step file handoff in ci.yml is unpinned (three mutations survived: update:list writes to a different $RUNNER_TEMP file, the check step reads a different --view-json path). Add a test_ci_gates pin that the file the resolve step writes is byte-identical to the path the check step reads (parse the YAML, compare the two strings), mutation-checked.
(4) test_canary_runbook_publishes_to_the_channel_with_devices misses 'npx eas-cli update --branch production' and 'eas update --channel production'. Widen the regex to catch eas-cli invocations and --channel, pin both mutants.
(5) The rollback fixtures give the rollback group a gitCommitHash that eas-cli 18.8.1 does not send (roll-back-to-embedded publishes no hash): make the fixtures faithful (no hash on rollback groups) and make the script's rollback branch handle the absent hash; pin.
(6) The runbook section-9 seeded cells that were INFERRED (runtimeVersion 1.0.0, 'sourcemaps uploaded: no' on the 2026-09-02 row) must be marked 'unrecorded' rather than stated, per the preamble's own rule.
This unit has no client files; tsc/eslint/jest do not apply — say so instead of reporting them clean.` },
  { key: 'W3-15', dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w3-push', spec: '.qa-w3b/W3_15_UNIT_SPEC.md', backend: false,
    minors: `(1) SECURITY-ADJACENT: src/services/pushNavigation.ts pathFromPushUrl's prefix match has no HOST boundary: 'https://qaren.appcomparison/abc' (host qaren.appcomparison) is accepted and navigated. Fix: parse the URL (or match 'qaren://' and 'https://qaren.app/' + optional trailing slash exactly, with the host compared as a whole), reject any other host; pin the boundary cases ('https://qaren.appcomparison/abc', 'https://qaren.app.evil.com/x', 'https://evil.com/qaren.app/x', 'qaren://' bare) — mutation: remove the boundary -> red.
(2) Spec §5's L8/L9 mutation claim is half true: 'drop the parse.code upper-casing' reddens only L8. Make L9 discriminate (a lowercase-code fixture that only the upper-casing turns into a route) or relabel L9 honestly in its test name and the PR facts.
(3) Carry-forward items (a cold-start LINKING URL qaren://comparison/X hydrating a Results-only root stack with an unhandled back arrow; a tap for comparison B while Results(A) is focused reusing the route key) stay documented as limits in pr_body_facts — do not redesign them here; but ADD a pin that documents the current behaviour of each so a later change is visible.
Do NOT change jest.config.js (its transform is required and value-checked); do NOT change src/navigation/linking.ts's exported shape.` },
]

const UNITS = (args && Array.isArray(args.units) && args.units.length) ? args.units : DEFAULT_UNITS

const FIX_SCHEMA = {
  type: 'object',
  required: ['unit', 'files_changed', 'minors_addressed', 'all_unit_tests_pass', 'test_evidence', 'tsc_clean', 'eslint_clean', 'lint_clean_backend', 'full_suite_evidence', 'mutation_checks', 'pr_body_facts_delta', 'git_status_final', 'residual_risk'],
  properties: {
    unit: { type: 'string' }, files_changed: { type: 'array', items: { type: 'string' } },
    minors_addressed: { type: 'array', items: { type: 'string' }, description: 'one per numbered minor: FIXED (how, pin name, mutation count) or DISPUTED (with the measurement)' },
    all_unit_tests_pass: { type: 'boolean' }, test_evidence: { type: 'string' },
    tsc_clean: { type: 'boolean' }, eslint_clean: { type: 'boolean' }, lint_clean_backend: { type: 'boolean' },
    full_suite_evidence: { type: 'string' }, mutation_checks: { type: 'array', items: { type: 'string' } },
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
  (u) => agent(`You are the pre-merge POLISH fixer for unit ${u.key} in worktree ${u.dir}. The unit's final adversary returned SOUND with reproduced MINOR defects; the orchestrator (Fable) rules that the following must be closed BEFORE the commit, minimally and inside the spec's design (${u.dir}/${u.spec}; the FABLE REVIEW RULINGS at its end bind; the red/green/adversary reports for this unit are in ${MYSP}/w3_all_results.json under key "${u.key}" — read the LAST adversary entry there first):
${u.minors}

Work order: git status --short and git diff --stat FIRST and keep every existing change (all of it is uncommitted unit work — never git checkout). For each numbered item: re-derive it from the code, fix minimally, add or adjust a load-bearing pin, mutation-check it from a byte snapshot with a sha-verified restore, and record the count. Then re-run the unit's own test files, the neighbour suites the spec names, ${u.backend ? 'pytest on the unit files + ruff + py_compile (use the pinned venv python), ' : ''}${u.backend ? '' : 'tsc, eslint on changed files, and the full jest suite once. '}Report pr_body_facts_delta (sentences to add to the PR body). Leave ONLY intended changes; report git status --short verbatim.
${COMMON}`, { label: 'polish:' + u.key, phase: 'Polish', model: MODEL, effort: 'high', schema: FIX_SCHEMA }),
  (fix, u) => fix ? agent(`You are the ADVERSARY re-checking the pre-merge polish of unit ${u.key} in worktree ${u.dir} (spec ${u.dir}/${u.spec}, rulings at its end binding). The polish fixer reported:
${JSON.stringify(fix, null, 1)}
The minors it was asked to close:
${u.minors}
1. git diff / git status: review the polish hunks in the context of the whole unit diff. Confirm each minor is genuinely closed (re-run its mutation from a byte snapshot) and that the polish introduced no regression: re-run the unit files, the neighbour suites${u.backend ? ', pytest on the unit files' : ', tsc'}; ${u.backend ? 'no client file may have changed' : 'confirm jest.config.js and linking.ts export shapes are unchanged'}.
2. Anything the fixer DISPUTED: verify the measurement.
3. Leave the worktree byte-identical (sha before/after). reproduced:true only when you ran it. If sound, say SOUND.
${COMMON}`, { label: 'recheck:' + u.key, phase: 'Recheck', model: MODEL, effort: 'medium', schema: ADV_SCHEMA }).then((adv) => ({ unit: u.key, fix, recheck: adv, final_verdict: adv ? adv.verdict : 'recheck died' })) : { unit: u.key, fix: null, recheck: null, final_verdict: 'polish died' }
)
const done = results.filter(Boolean)
log('polish: ' + done.map((r) => r.unit + '=' + r.final_verdict).join(', '))
return { results: done }
