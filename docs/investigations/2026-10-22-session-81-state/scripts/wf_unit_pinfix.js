export const meta = {
  name: 's82-unit-pinfix',
  description: 'Per unit: one agent applies the orchestrator-named pin edits on the unit branch inside its worktree (one commit through the hook is the only sanctioned git write), re-runs the named gates and patches the PR body; returns the new HEAD and every gate line',
  phases: [
    { title: 'Pinfix', detail: 'named edits, one commit through the hook, the named gates, the PR body patch' },
  ],
}

// args: { unit: {id, title, worktree, branch, headSha, edits: [..], gates: [..], footprint: [..], prBodyPath, prBodyEdits: [..], outDir}, common, rulings, pyt, scratch }
const A = args
const U = A.unit

const SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' },
    verdict: { type: 'string', enum: ['READY_FOR_PR', 'BLOCKED'] },
    head_before: { type: 'string' },
    head_after: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    gates: { type: 'array', items: { type: 'string' } },
    footprint_check: { type: 'string' },
    pr_body_path: { type: 'string' },
    report_path: { type: 'string' },
    deviations: { type: 'array', items: { type: 'string' } },
  },
  required: ['unit', 'verdict', 'head_before', 'head_after', 'files_changed', 'gates', 'footprint_check', 'pr_body_path', 'report_path'],
}

const PROMPT = [
  'You are the PIN-FIX agent for unit ' + U.id + ': ' + U.title + '.',
  'Common brief (read it FIRST and again before reporting): ' + A.common + ' . Rulings binding for this round: ' + A.rulings + ' .',
  'Worktree: ' + U.worktree + ' on branch ' + U.branch + ' at HEAD ' + U.headSha + ' (verify all three and that git status --short is EMPTY before anything; a mismatch = stop and report BLOCKED). Put the path in a shell variable once and never name a sibling worktree by path.',
  'GIT EXCEPTION FOR THIS TASK ONLY, IN THIS WORKTREE ONLY: git add <the edited files> and ONE git commit through the hook (never --no-verify) with the Co-Authored-By trailer naming YOUR OWN model. NEVER: push, checkout --, restore, stash, reset, rebase, merge, clean, any force flag, any write outside this worktree and your notes folder (' + A.scratch + '/' + U.outDir + '/).',
  'EDITS (apply EXACTLY these, nothing else; the Edit tool preserves line endings; pure ASCII; byte-check > 127 after each write; take a byte copy of each file before editing into your notes folder and record sha256 before and after): ' + U.edits.join(' || '),
  'GATES after the commit, every pytest through python "' + A.pyt + '" --bound <s> --tag <tag> --log <notes>/<name>.log --cwd <worktree> -- <args>, ONE pytest process at a time, every [pyt] line pasted: ' + U.gates.join(' || ') + ' . A TIMEOUT is a measurement failure: re-run that one gate once alone, then report it NOT MEASURED with both [pyt] lines.',
  'FOOTPRINT: git diff --name-only origin/main...HEAD must list EXACTLY these files (sorted): ' + U.footprint.join(', ') + ' ; git diff --check origin/main...HEAD clean; no whole-file diff (git diff --stat origin/main...HEAD).',
  'PR BODY: patch ' + U.prBodyPath + ' IN PLACE through your shell (python, exact-string replacements, never a rewrite from memory): ' + U.prBodyEdits.join(' || ') + ' ; pure ASCII; keep every other byte; record its size and sha256 before and after.',
  'Report to ' + A.scratch + '/' + U.outDir + '/PINFIX_REPORT.md THROUGH YOUR SHELL (the harness refuses a subagent Write of a report .md): HEAD before and after, the edits with shas, every [pyt] line, the footprint check, the PR body patch summary, deviations, git status --short. Then return the structured output. Budget 60 minutes from your first tool call. Never claim a state you did not observe.',
].join('\n\n')

phase('Pinfix')
const out = await agent(PROMPT, { label: 'pinfix:' + U.id, phase: 'Pinfix', schema: SCHEMA })
log('pinfix verdict: ' + (out ? out.verdict : 'no result'))
return out
