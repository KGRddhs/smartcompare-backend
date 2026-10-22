export const meta = {
  name: 's80-unit-green',
  description: 'Per unit: Opus GREEN implements to the frozen RED files, then (when args.adversaries > 0) two Opus adversaries on the exact bytes; fix rounds are launched separately by the orchestrator',
  phases: [
    { title: 'GREEN', detail: 'implement to green, flag-OFF identity, comm set at HEAD, report' },
    { title: 'Adversaries', detail: 'correctness then engineering lens on the exact bytes' },
  ],
}

// args: { unit: {id, title, worktree, branch, flag, specPath, reviewPath, gatePath, rulingsSection, redFiles: [{path, sha256}], lenses: [string]}, common, plan, r0, rulings, baseSha, mainSha, pyt, scratch, adversaries }
const A = args
const u = A.unit
const RULES = [
  'Common brief (read first and again before reporting): ' + A.common,
  'Plan (sections 0 and 1 binding): ' + A.plan + ' . R0 rulings: ' + A.r0 + ' . Batch rulings: ' + A.rulings + ' (your unit section) . RED gate (binding, amends the spec): ' + u.gatePath,
  'Base sha: ' + A.baseSha + ' ; the rebase target before the PR: origin/main ' + A.mainSha + ' . Bounded runner: python "' + A.pyt + '" --bound <s> --tag <tag> --log <file> --cwd <worktree> -- <pytest args> (read --help first). Bounds: unit/pin file or one mutant 600 s; CI-order set or a comm chunk of at most 25 files 1200 s; ceiling 1800 s. ONE pytest at a time on this box. Paste every [pyt] summary line into the report. A TIMEOUT is a measurement failure: re-run once alone, then report NOT MEASURED.',
  'The RED files are FROZEN: ' + u.redFiles.map(f => f.path + ' (sha256 ' + f.sha256 + ')').join('; ') + ' . Re-hash them first and at the end; a wrong row is reported, never edited. You never read or print .env or any secret value (names only); production flag state comes only from the newest dated ledger line. Pure ASCII and LF in every file you write (keep CRLF where an existing file has it, e.g. CLAUDE.md); check bytes > 127 after each write. No personal values anywhere. The pre-commit hook refuses sk-/JWT/PEM/credentialed-URL shapes.',
].join('\n')

const GREEN_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' },
    head_sha: { type: 'string' },
    branch: { type: 'string' },
    red_files_rehash_ok: { type: 'boolean' },
    files_changed: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, sha256_before: { type: 'string' }, sha256_after: { type: 'string' }, added: { type: 'integer' }, deleted: { type: 'integer' } }, required: ['path', 'sha256_after'] } },
    unit_run_on: { type: 'string' },
    unit_run_off: { type: 'string' },
    identity_pins: { type: 'array', items: { type: 'string' } },
    comm_set: { type: 'object', properties: { files: { type: 'integer' }, chunks: { type: 'integer' }, head_failures: { type: 'array', items: { type: 'string' } }, branch_only_new: { type: 'array', items: { type: 'string' } }, pyt_lines: { type: 'array', items: { type: 'string' } } }, required: ['files', 'chunks', 'head_failures', 'branch_only_new', 'pyt_lines'] },
    ci_order_set: { type: 'string' },
    lint: { type: 'string' },
    claude_md_row: { type: 'string' },
    pr_body_path: { type: 'string' },
    deviations: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
    report_path: { type: 'string' },
  },
  required: ['unit', 'head_sha', 'red_files_rehash_ok', 'files_changed', 'unit_run_on', 'unit_run_off', 'comm_set', 'lint', 'claude_md_row', 'deviations', 'open_questions'],
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
    prove_nothing: { type: 'array', items: { type: 'string' } },
    report_path: { type: 'string' },
  },
  required: ['unit', 'lens', 'head_sha_verified', 'verdict', 'blocking', 'major', 'minor', 'mutants_applied', 'reruns'],
}

function greenPrompt() {
  return [
    'You are the GREEN agent (Fable) for unit ' + u.id + ': ' + u.title + '. Flag: ' + u.flag + '. Worktree: ' + u.worktree + ' (currently detached at the base sha with the two RED files untracked). The spec: ' + u.specPath + ' ; the review: ' + u.reviewPath + ' ; your unit section of the batch rulings: ' + u.rulingsSection + '.',
    RULES,
    'Procedure. (1) Read everything named above in full. Re-hash the RED files. (2) In the worktree: `git checkout -b ' + u.branch + '` (this is the ONE git branch command you may run; no stash, reset, rebase, merge or clean). Byte-copy every file you will edit into <scratchpad>/' + u.id + '_green_before/ with sha256. (3) Implement the spec change list as amended by the review corrections, the rulings and the RED gate, as your own code (the RED prototype text in the gate note is a reference only); the flag is read per call with the house idiom and is the FIRST statement of every gated predicate; flag OFF must be byte-identical on every response body and stored row. Unflagged items only where the rulings say so (allowlist widenings, log-only lines). (4) Run the unit files through the runner with the flag ON (all rows green) and OFF (all rows green); run the identity pins the spec section 4.2 names; run ruff on the changed python files (`python -m ruff check <files>` from the worktree; the hook will run it again) and `python -m py_compile`. (5) Comm set at HEAD: rebuild the list with the union rule (the RED agent left comm_files.txt and comm_reasons.tsv under <scratchpad>/' + u.id + '_red/; re-derive and union with it, adding the files your edits newly reference), run it in chunks of at most 25 files (bound 1200) one at a time; record HEAD failures; compute branch-only-NEW = HEAD failures minus the base failures the RED report recorded; it must be EMPTY. Run the CI-order set once (bound 1200). (6) Write the CLAUDE.md flag row per the spec section 8.1 (house format, variable NAMES only) and any in-place rewrite the spec names; keep CRLF. (7) Commit ONLY your changed files plus the two RED files on the branch with `git add <paths>` and `git commit -m "<type>(scope): <msg>\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -- <paths>` (the pre-commit hook runs; fix what it refuses, never bypass it). Do NOT push, do NOT rebase, do NOT open a PR: the orchestrator does that after the adversaries. (8) Write the PR body draft to <scratchpad>/' + u.id + '_green/PR_BODY.md: what the flag does, the defect ids -> RED node ids map, the deliberate pin changes table (spec 4.1), the comm-set figures with [pyt] lines, the stated limits, the owner steps, and end it with the line "🤖 Generated with [Claude Code](https://claude.com/claude-code)". (9) Write the GREEN report to <scratchpad>/' + u.id + '_green/' + u.id + '_GREEN_REPORT.md and return the structured output with the HEAD sha.',
  ].join('\n\n')
}

function advPrompt(lens, green) {
  return [
    'You are an ADVERSARY (Fable), lens: ' + lens + ', for unit ' + u.id + ': ' + u.title + '. Your job is to find what is wrong with the GREEN bytes; default to doubt. Worktree: ' + u.worktree + ' on branch ' + u.branch + ' at HEAD ' + green.head_sha + ' (verify it first; if HEAD differs, stop and report NOT_READY with the reason).',
    RULES,
    'The GREEN report: ' + (green.report_path || '<scratchpad>/' + u.id + '_green/' + u.id + '_GREEN_REPORT.md') + ' ; the PR body draft: ' + (green.pr_body_path || '<scratchpad>/' + u.id + '_green/PR_BODY.md') + '.',
    'Never edit the worktree. All probes and mutants run in YOUR OWN detached scratch worktree made with `git worktree add --detach <scratchpad>/' + u.id + '_adv_' + lens.replace(/[^a-z]/g, '') + ' ' + green.head_sha + '` and removed at the end (`git worktree remove --force`); sha-verify before and after. One pytest at a time.',
    'Lens duties. correctness: re-run the unit files ON and OFF from the exact bytes; re-apply at least ten of the spec mutants plus any the gate assigned to you (' + u.id + ': the X19 block-move mutant by hand) on sha-verified byte copies and kill them; probe the runtime truth of every claim in the GREEN report and the CLAUDE.md row against the code (flag-OFF identity, the error-handler mapping, billing R-A3, the contract freeze in PLAN section 0); list prove-nothing rows. engineering: diff hygiene (CRLF/LF, ASCII, no deleted lines you cannot justify, no new imports outside the spec), re-derive the comm set with the union rule and compare with GREEN\'s list (a missing file is a MAJOR), re-run three comm chunks of your choice plus the CI-order set, ruff + py_compile, the source-scanning pins (test_model_config*.py, test_prompt_fence.py, the U3c store pin, the migration/manifest readers), the two CLAUDE.md readers, the hook test files, and check the CLAUDE.md row and the PR body against the bytes (every number and claim). security/secrets or client-truth lenses apply when named.',
    'Verdict vocabulary: SOUND (no blocking, no major) or NOT_READY (any blocking or major). Minors are documentation rulings for the orchestrator. Write the report to <scratchpad>/' + u.id + '_adv/' + lens.replace(/[^a-z]/g, '') + '_REPORT.md and return the structured output.',
  ].join('\n\n')
}

phase('GREEN')
const green = await agent(greenPrompt(), { label: 'green:' + u.id, phase: 'GREEN', schema: GREEN_SCHEMA })
if (!green) { log('GREEN produced no report'); return { green: null, adversaries: [] } }
log('GREEN ' + u.id + ' at ' + green.head_sha + '; branch-only-new = ' + JSON.stringify(green.comm_set.branch_only_new))

const n = Number(A.adversaries || 0)
const lenses = (u.lenses || ['correctness', 'engineering']).slice(0, n)
const adversaries = []
if (n > 0) {
  phase('Adversaries')
  for (const lens of lenses) {
    const r = await agent(advPrompt(lens, green), { label: 'adv:' + u.id + ':' + lens, phase: 'Adversaries', schema: ADV_SCHEMA })
    adversaries.push({ lens, result: r })
    log('adversary ' + lens + ': ' + (r ? r.verdict : 'no report'))
  }
}
return { green, adversaries }
