export const meta = {
  name: 's81-unit-rebase',
  description: 'Per unit: one agent rebases the unit branch onto origin/main inside its worktree (the one sanctioned git write for this task), resolves the named conflict classes by union, adds the orchestrator-named pin rows, re-runs the post-rebase gates and finalises the PR body; returns the new HEAD and every gate line',
  phases: [
    { title: 'Rebase', detail: 'fetch, rebase, union-resolve the named conflicts, pin rows, gates, PR body' },
  ],
}

// args: { unit: {id, title, worktree, branch, headSha, redFile, pinRows: [..], conflictFiles: [..], footprint: [..], ciOrderFiles, commNotes, prBodyIn, outDir}, common, plan, rulings, gate, pyt, scratch }
const A = args
const U = A.unit

const SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' },
    verdict: { type: 'string', enum: ['READY_FOR_PR', 'BLOCKED'] },
    head_before: { type: 'string' },
    base_main: { type: 'string' },
    head_after: { type: 'string' },
    commits_replayed: { type: 'integer' },
    conflicts: { type: 'array', items: { type: 'string' } },
    resolutions: { type: 'array', items: { type: 'string' } },
    pin_rows_added: { type: 'array', items: { type: 'string' } },
    mutants: { type: 'array', items: { type: 'string' } },
    red_file_sha256: { type: 'string' },
    footprint_check: { type: 'string' },
    gates: { type: 'array', items: { type: 'string' } },
    not_measured: { type: 'array', items: { type: 'string' } },
    pr_body_path: { type: 'string' },
    report_path: { type: 'string' },
    deviations: { type: 'array', items: { type: 'string' } },
  },
  required: ['unit', 'verdict', 'head_before', 'base_main', 'head_after', 'conflicts', 'resolutions', 'pin_rows_added', 'red_file_sha256', 'gates', 'pr_body_path', 'report_path'],
}

const PROMPT = [
  'You are the REBASE-AND-GATES agent for unit ' + U.id + ': ' + U.title + '.',
  'Common brief (read it FIRST and again before reporting): ' + A.common + ' . Plan of record: ' + A.plan + ' . Unit rulings (binding): ' + A.rulings + ' . RED gate note: ' + A.gate + ' .',
  'Worktree: ' + U.worktree + ' on branch ' + U.branch + ' at HEAD ' + U.headSha + ' (verify both, and that git status --short is empty, before anything). Put the path in a shell variable once and never name a sibling worktree by path.',
  'GIT EXCEPTION FOR THIS TASK ONLY, IN THIS WORKTREE ONLY (the common brief forbids these otherwise): git fetch origin main; git rebase origin/main; git add <conflicted file>; GIT_EDITOR=true git rebase --continue; one git commit for the pin rows (through the hook, never --no-verify, with the Co-Authored-By trailer naming YOUR OWN model); git rebase --abort ONLY when a conflict falls outside the rules below (then report BLOCKED with the conflict text). NEVER: push, checkout --, restore, stash, reset, clean, merge, rebase -i, any force flag, any write outside this worktree and your notes folder (' + A.scratch + '/' + U.outDir + '/).',
  'Expected conflicts (measured by the orchestrator with git merge-tree): ' + U.conflictFiles.join(', ') + '. Each is the "both sides added at the same anchor" class: main carries the B1 (#364) and B3 (#365) additions, the branch carries this unit\'s. RESOLUTION RULE = UNION, in session order (B1, B3, then this unit): CLAUDE.md keeps every flag row and paragraph of both sides (never drop or reword a row); test files keep both sides\' list entries, clear-list entries and recorder entries; a conflicting numeric count (a site count, a ">= N" floor) takes the value the REBASED tree measures when that file is run (never a value lower than either side implies). Conflicts can repeat on each of the ' + U.commitsToReplay + ' replayed commits: resolve each the same way. After every continue run git diff --check; at the end grep for <<<<<<< / >>>>>>> over CLAUDE.md, app/ and tests/ must be empty. Preserve line endings (backend files CRLF in the working copy): resolve with the Edit tool or Python with explicit newline handling; git diff --stat origin/main...HEAD must show no whole-file diff and ONLY these files: ' + U.footprint.join(', ') + ' (any other file = a deviation to report, not to fix).',
  'PIN ROWS (test-only, appended to ' + U.redFile + ' after the rebase; record the file\'s new sha256; each must be green at HEAD and prove its mutant on a sha-verified byte copy, restored and sha-compared, under .qa-mutation.lock): ' + U.pinRows.join(' || '),
  'GATES at the rebased HEAD, every pytest through python "' + A.pyt + '" --bound <s> --tag <tag> --log <notes>/<name>.log --cwd <worktree> -- <args>, ONE process at a time, every [pyt] line pasted: (1) the unit file flag ON and flag OFF; (2) each conflicted test file alone, flag OFF; (3) the R8 pair tests/test_sentry_channels_u8d_unit.py and tests/test_sentry_channels_u8d.py alone; (4) tests/test_paid_route_metering.py with and without the flag exported; (5) the CI-order set (' + U.ciOrderFiles + ') flag OFF; (6) the comm set re-derived at the rebased HEAD: ' + U.commNotes + ' run in chunks of at most 25 files (bound 1200) at HEAD and at the base (a DETACHED scratch worktree of origin/main under your notes folder, removed afterwards and verified gone), comm -13 of the sorted FAILED node-id sets EMPTY (the cold-tiktoken pair tests/test_prompt_truth.py identical both sides); (7) the two CLAUDE.md readers tests/test_ci_gates.py and tests/test_behavior_dimension_translation.py; (8) ruff --select E9,F63,F7,F82 --no-cache and py_compile on every touched python file; (9) the hook files tests/test_precommit_hook*.py ALONE once at the 1800 s ceiling split -k "not dash" / -k dash; a TIMEOUT is re-run once alone, then reported NOT MEASURED with both [pyt] lines (the unit touches no .githooks file: say so). A TIMEOUT anywhere else: re-run once alone, then NOT MEASURED.',
  'PR BODY: finalise ' + U.prBodyIn + ' into ' + A.scratch + '/' + U.outDir + '/PR_BODY.md: base = origin/main (the sha you fetched), HEAD = the rebased sha, the RED file sha after the pin rows, the round-4 fix and re-verifier reports named, the two pin rows and their mutants, the comm paragraph rewritten from the MEASURED list (true member count, chunk results), the hook-files sentence stating exactly what was measured, every stated limit kept; pure ASCII; no personal values; the orchestrator appends the generation trailer.',
  'Report to ' + A.scratch + '/' + U.outDir + '/REBASE_REPORT.md (new HEAD, base sha, every conflict with its resolution, the pin rows and mutants, every [pyt] line, NOT MEASURED items, deviations, git status --short) and return the structured output. Budget 2 hours from your first tool call; cheapest gates first after the rebase; if the budget cannot fit everything, report what you measured and what you did not. Never claim a state you did not observe.',
].join('\n\n')

phase('Rebase')
const out = await agent(PROMPT, { label: 'rebase:' + U.id, phase: 'Rebase', schema: SCHEMA })
log('rebase verdict: ' + (out ? out.verdict : 'no result'))
return out
