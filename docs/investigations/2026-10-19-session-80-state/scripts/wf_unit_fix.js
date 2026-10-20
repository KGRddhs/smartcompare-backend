export const meta = {
  name: 's80-unit-fix',
  description: 'Per unit fix round: one agent does RED-then-GREEN on the adversary findings per the fix rulings, then one re-verifier on the exact new bytes',
  phases: [
    { title: 'Fix', detail: 'RED rows for every finding, then the smallest hunks, gates, commit on the branch' },
    { title: 'Reverify', detail: 'correctness re-verifier on the new HEAD: mutants per fix, gates, docs against bytes' },
  ],
}

// args: { unit: {id, title, worktree, branch, flag, specPath, reviewPath, gatePath, fixRulingsPath, advReports: [paths], redFiles: [{path, sha256}], headSha}, common, plan, r0, rulings, pyt, scratch }
const A = args
const u = A.unit
const RULES = [
  'Common brief (read first and again before reporting): ' + A.common,
  'Plan (sections 0 and 1 binding): ' + A.plan + ' . R0 rulings: ' + A.r0 + ' . Batch rulings (the unit section): ' + A.rulings + ' . RED gate: ' + u.gatePath + ' . FIX-ROUND RULINGS (binding for this round, they amend everything above): ' + u.fixRulingsPath + ' . Adversary reports this round answers: ' + u.advReports.join(' ; '),
  'Bounded runner: python "' + A.pyt + '" --bound <s> --tag <tag> --log <file> --cwd <worktree> -- <pytest args> (read --help first). Bounds: unit/pin file or one mutant 600 s; CI-order set or a comm chunk of at most 25 files 1200 s; ceiling 1800 s. ONE pytest at a time on this box (another workflow may share it; a TIMEOUT is re-run once alone, then reported NOT MEASURED). Paste every [pyt] summary line into the report.',
  'Current frozen RED files (the fix round may append rows and apply only the hygiene the rulings name; every other row stays byte-identical): ' + u.redFiles.map(f => f.path + ' (sha256 ' + f.sha256 + ')').join('; ') + '. You never read or print .env or any secret value (names only); production flag state comes only from the newest dated ledger line. Pure ASCII and LF in every file you write (keep CRLF where an existing file has it, e.g. CLAUDE.md); check bytes > 127 after each write; no personal values; the pre-commit hook refuses sk-/JWT/PEM/credentialed-URL shapes, build such sentinels by concatenation.',
].join('\n')

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' },
    head_sha: { type: 'string' },
    red_files: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, sha256: { type: 'string' } }, required: ['path', 'sha256'] } },
    rows_added: { type: 'array', items: { type: 'string' } },
    red_step: { type: 'object', properties: { new_rows_failed: { type: 'integer' }, every_failure_is_assertion_error: { type: 'boolean' }, existing_rows_passed: { type: 'integer' }, pyt_line: { type: 'string' } }, required: ['new_rows_failed', 'every_failure_is_assertion_error', 'existing_rows_passed', 'pyt_line'] },
    files_changed: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, sha256_after: { type: 'string' }, added: { type: 'integer' }, deleted: { type: 'integer' } }, required: ['path', 'sha256_after'] } },
    unit_run_on: { type: 'string' },
    unit_run_off: { type: 'string' },
    gates: { type: 'array', items: { type: 'string' } },
    docs_applied: { type: 'array', items: { type: 'string' } },
    pr_body_path: { type: 'string' },
    deviations: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
    report_path: { type: 'string' },
  },
  required: ['unit', 'head_sha', 'red_files', 'rows_added', 'red_step', 'files_changed', 'unit_run_on', 'unit_run_off', 'gates', 'docs_applied', 'deviations', 'open_questions'],
}

const ADV_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' },
    lens: { type: 'string' },
    head_sha_verified: { type: 'string' },
    verdict: { type: 'string', enum: ['SOUND', 'NOT_READY'] },
    blocking: { type: 'array', items: { type: 'string' } },
    major: { type: 'array', items: { type: 'string' } },
    minor: { type: 'array', items: { type: 'string' } },
    mutants_applied: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, killed_by: { type: 'string' }, survived: { type: 'boolean' } }, required: ['id', 'survived'] } },
    reruns: { type: 'array', items: { type: 'string' } },
    report_path: { type: 'string' },
  },
  required: ['unit', 'lens', 'head_sha_verified', 'verdict', 'blocking', 'major', 'minor', 'mutants_applied', 'reruns'],
}

phase('Fix')
const fix = await agent([
  'You are the FIX agent (RED-then-GREEN) for unit ' + u.id + ': ' + u.title + ', fix round on branch ' + u.branch + ' at HEAD ' + u.headSha + ' in ' + u.worktree + ' (verify both first; `git status --short` must be empty).',
  RULES,
  'Follow the "Procedure for the fix agent" in the fix-round rulings file exactly, in order: RED step (append the rows the rulings name, prove each new row fails at HEAD on an AssertionError only, existing rows still green, record the new sha256 of every RED file), GREEN step (smallest additive hunks; the flag first in every gated predicate; flag OFF byte-identical), the documentation rulings on the CLAUDE.md row and the PR body draft, the gates the rulings list, then ONE commit on the branch with `git add <paths>` and `git commit -m "<msg>\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -- <paths>` (no push, no rebase, no stash). Write the fix report to <scratchpad>/' + u.id + '_fix1/' + u.id + '_FIX1_REPORT.md and return the structured output with the new HEAD sha.',
].join('\n\n'), { label: 'fix:' + u.id, phase: 'Fix', schema: FIX_SCHEMA })
if (!fix) { log('fix agent produced no report'); return { fix: null, reverify: null } }
log('fix ' + u.id + ' at ' + fix.head_sha)

phase('Reverify')
const reverify = await agent([
  'You are the RE-VERIFIER (correctness lens) for unit ' + u.id + ' fix round 1. Worktree ' + u.worktree + ' on branch ' + u.branch + ' at HEAD ' + fix.head_sha + ' (verify first; if HEAD differs, stop with NOT_READY). Default to doubt.',
  RULES,
  'The fix report: ' + (fix.report_path || '<scratchpad>/' + u.id + '_fix1/' + u.id + '_FIX1_REPORT.md') + ' ; the RED files now: ' + fix.red_files.map(f => f.path + ' (' + f.sha256 + ')').join('; ') + ' ; the PR body: ' + (fix.pr_body_path || '<scratchpad>/' + u.id + '_green/PR_BODY.md') + '.',
  'Never edit the worktree. Probes and mutants run in YOUR OWN detached scratch worktree (`git worktree add --detach <scratchpad>/' + u.id + '_fix1_adv ' + fix.head_sha + '`, removed at the end; sha-verify before and after). Follow the "Re-verifier" section of the fix-round rulings: re-hash the RED files; unit ON and OFF; at least eight mutants including one per fix, applied to sha-verified byte copies and killed; the CI-order set; the comm chunks the rulings name; the hook test files ALONE with the TIMEOUT rule; the CLAUDE.md row and the PR body checked sentence by sentence against the bytes; confirm every adversary MAJOR and MINOR of the previous round is closed or recorded. Verdict SOUND (no blocking, no major) or NOT_READY. Write the report to <scratchpad>/' + u.id + '_fix1/REVERIFY_REPORT.md and return the structured output.',
].join('\n\n'), { label: 'reverify:' + u.id, phase: 'Reverify', schema: ADV_SCHEMA })
log('reverify ' + u.id + ': ' + (reverify ? reverify.verdict : 'no report'))
return { fix, reverify }
