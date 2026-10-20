export const meta = {
  name: 's80-unit-adversaries',
  description: 'Two adversaries (lenses in order, sequential) on a given HEAD of a unit branch, after a fix round changed the GREEN bytes',
  phases: [{ title: 'Adversaries', detail: 'correctness then engineering (or the lenses given) on the exact bytes' }],
}

// args: { unit: {id, title, worktree, branch, flag, headSha, reportPath, prBodyPath, redFiles: [{path, sha256}], lenses, extraMutants}, common, plan, r0, rulings, gatePath, fixRulingsPath, pyt, scratch }
const A = args
const u = A.unit
const RULES = [
  'Common brief (read first and again before reporting): ' + A.common,
  'Plan (sections 0 and 1 binding): ' + A.plan + ' . R0 rulings: ' + A.r0 + ' . Batch rulings (the unit section): ' + A.rulings + ' . RED gate: ' + A.gatePath + ' . Fix-round rulings (amend the gate): ' + (A.fixRulingsPath || 'none'),
  'Bounded runner: python "' + A.pyt + '" --bound <s> --tag <tag> --log <file> --cwd <worktree> -- <pytest args> (read --help first). Bounds: unit/pin file or one mutant 600 s; CI-order set or a comm chunk of at most 25 files 1200 s; ceiling 1800 s. ONE pytest at a time; a TIMEOUT is re-run once alone, then reported NOT MEASURED. Paste every [pyt] summary line into the report.',
  'Frozen RED files: ' + u.redFiles.map(f => f.path + ' (sha256 ' + f.sha256 + ')').join('; ') + '. Never edit the worktree. Probes and mutants run in YOUR OWN detached scratch worktree (`git worktree add --detach <scratchpad>/' + u.id + '_adv2_<lens> ' + u.headSha + '`, removed at the end; sha-verify before and after). Never read or print .env or any secret value (names only); production flag state only from the newest dated ledger line.',
].join('\n')

const ADV_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' }, lens: { type: 'string' }, head_sha_verified: { type: 'string' },
    verdict: { type: 'string', enum: ['SOUND', 'NOT_READY'] },
    blocking: { type: 'array', items: { type: 'string' } }, major: { type: 'array', items: { type: 'string' } }, minor: { type: 'array', items: { type: 'string' } },
    mutants_applied: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, killed_by: { type: 'string' }, survived: { type: 'boolean' } }, required: ['id', 'survived'] } },
    reruns: { type: 'array', items: { type: 'string' } }, prove_nothing: { type: 'array', items: { type: 'string' } }, report_path: { type: 'string' },
  },
  required: ['unit', 'lens', 'head_sha_verified', 'verdict', 'blocking', 'major', 'minor', 'mutants_applied', 'reruns'],
}

function advPrompt(lens) {
  return [
    'You are an ADVERSARY, lens: ' + lens + ', for unit ' + u.id + ': ' + u.title + '. Find what is wrong with the bytes; default to doubt. Worktree ' + u.worktree + ' on branch ' + u.branch + ' at HEAD ' + u.headSha + ' (verify first; if HEAD differs, stop with NOT_READY). Flag: ' + u.flag + '.',
    RULES,
    'The GREEN/fix reports: ' + u.reportPath + ' ; the PR body draft: ' + u.prBodyPath + '.',
    'Lens duties. correctness: re-run the unit files ON and OFF from the exact bytes; re-apply at least ten spec mutants plus these hand mutants: ' + (u.extraMutants || 'none named') + ' ; probe the runtime truth of every claim in the reports and the CLAUDE.md row (flag-OFF identity incl. every pinned 400 body, the error-handler mapping and its scope, billing R-A3 on every new exit, the contract freeze in PLAN section 0); list prove-nothing rows. engineering (plus security for a route unit): diff hygiene (CRLF/LF, ASCII, deletions justified, imports per spec), re-derive the comm set with the union rule incl. edited test-support modules and compare with the unit list (a missing file is a MAJOR), re-run three comm chunks plus the CI-order set, ruff + py_compile, the source-scanning pins, the two CLAUDE.md readers, the hook test files ALONE (TIMEOUT rule), SSRF and log-hygiene (no user content or full URL in any log line), and the row and PR body against the bytes.',
    'Verdict SOUND (no blocking, no major) or NOT_READY. Write the report to <scratchpad>/' + u.id + '_adv2/' + lens.replace(/[^a-z]/g, '') + '_REPORT.md and return the structured output.',
  ].join('\n\n')
}

phase('Adversaries')
const out = []
for (const lens of (u.lenses || ['correctness', 'engineering'])) {
  const r = await agent(advPrompt(lens), { label: 'adv2:' + u.id + ':' + lens, phase: 'Adversaries', schema: ADV_SCHEMA })
  out.push({ lens, result: r })
  log('adversary ' + lens + ': ' + (r ? r.verdict : 'no report'))
}
return out
