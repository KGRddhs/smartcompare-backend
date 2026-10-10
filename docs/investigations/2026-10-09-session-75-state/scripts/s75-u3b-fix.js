export const meta = {
  name: 's75-u3b-fix',
  description: 'Session 75 unit U3b fix round under the synack-build-orchestrator loop after two adversaries: one Opus fix agent applies rulings UY1-UY8 (the consent sheet layout: numeric ScrollView cap from the window height, flashScrollIndicators, maxFontSizeMultiplier; the OpenAPI wording pin B5; the spy kwargs pin; the stale comments) in worktree sc-s74-ct, then one Opus final adversary ALONE on the exact bytes. Fable reviews the diff afterwards; the orchestrator commits.',
  phases: [
    { title: 'Fix', detail: 'UY1-UY5 red-first, the production touches, the UY8 gates incl. the FULL jest suite' },
    { title: 'Final adversary', detail: 'the exact bytes: replay the survivors, own mutants, FULL jest, backend set' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/f9970d11-1fa0-400e-9fb3-dd91f335e519/scratchpad'
const RULES = SP + '/s75-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s74-ct'
const SPECS = SP + '/specs'
const NOTES = SP + '/u3b'
const CONTEXT = [
  'UNIT U3b (AI consent v2 under D3 = C) of the MYEZ launch lane, session 75, today ' + args.today + '. Worktree ' + WT + ' (branch feature/s75-u3b-consent-v2, HEAD = main ' + args.main + '; the working tree carries the UNCOMMITTED GREEN run 2 of 23 files whose sha256 are in ' + NOTES + '/adv_results.json (the GREEN report) and ' + NOTES + '/green/notes.md). SmartCompareApp/node_modules is a JUNCTION into sc-s70-u4b: never delete, move or recreate anything under it; ONE jest at a time; client tools by path from ' + WT + '/SmartCompareApp under coreutils `timeout -k 15 600` (the FULL suite under 1500), versions printed first; backend gates through the bounded runner only; the other agent of this workflow runs AFTER you, never beside you. Read the agent rules file FIRST and obey it: ' + RULES + ' . Read worktree files with bash, never the Read tool; edit with the Edit tool (CRLF preserved); new text pure ASCII.',
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/U3B_CONSENT_V2_SPEC.md; ' + SPECS + '/U3B_CONSENT_V2_REVIEW.md; ' + SPECS + '/FABLE_RULINGS_U3B.md (UB-R1..R21); ' + SPECS + '/FABLE_REVIEW_RED_U3B.md (UG-1..UG-11); ' + SPECS + '/FABLE_RULINGS_U3B_POST_ADVERSARY.md (UY1-UY9: BINDING for this round). The two adversary reports with the exact mutant shapes and probe files are in ' + NOTES + '/adv-consent-truth/ and ' + NOTES + '/adv-eng/ and in ' + NOTES + '/adv_results.json.',
  'BINDING RULES: backend files are CRLF in the working copy and LF in the index; `git diff --stat` must equal `git diff --stat --ignore-cr-at-eol`. Pure ASCII in new text (no credential shape). No network, no real .env, no git write. Every production line you change is proven by a byte-copy mutant under the lock <worktree>/.qa-mutation.lock (copy, mutate, run the killing node, restore, sha256-compare, stop on mismatch). The fence sha 372c50484085fa859a576a62367c743365735fab6dda31f336552a4ae2a21a02 must still hold (the copy does not change in this round).',
].join('\n')
const FIX_SCHEMA = { type: 'object', required: ['files_changed', 'jest_lines', 'pyt_lines', 'mutants', 'diff_stat', 'git_status_final', 'stated_limits', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' } }, jest_lines: { type: 'array', items: { type: 'string' } }, pyt_lines: { type: 'array', items: { type: 'string' } },
  tsc: { type: 'string' }, eslint: { type: 'string' }, lint: { type: 'string' }, gitleaks: { type: 'string' },
  mutants: { type: 'array', items: { type: 'string' } }, diff_stat: { type: 'string' }, git_status_final: { type: 'string' },
  stated_limits: { type: 'array', items: { type: 'string' } }, not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'worktree_sha_check', 'summary'], properties: {
  verdict: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } }, mutants: { type: 'array', items: { type: 'string' } }, not_checked: { type: 'array', items: { type: 'string' } },
  jest_lines: { type: 'array', items: { type: 'string' } }, pyt_lines: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string' }, summary: { type: 'string' } } }

phase('Fix')
const fix = await agent([
  'ROLE: FIX agent for U3b (rulings UY1-UY8). Notes folder: ' + NOTES + '/fix (create it; running notes.md). Budget: 2 hours. FIRST re-hash the 23 GREEN files against the GREEN report (a mismatch: stop and report).',
  CONTEXT,
  'DO, in this order: (1) the nodes RED-FIRST: the aiConsentSheetScroll.s75 amendments and new nodes (UY1) red on the current bytes; B5 (UY3) red on mutant B17; the B3 kwargs assertions (UY4) red on mutant B12E and on a timeout change. (2) The production touches: AiConsentSheet.tsx per UY1; the comment-only edits of UY5. (3) Every production line mutant-proven incl. the three visibility mutants of CT2-m1. (4) The UY8 gates in order incl. the FULL jest suite once. Return every file with its sha256, every jest and [pyt] summary line verbatim, the mutant table, the stated limits (UY6 folded), and your questions.',
].join('\n'), { label: 'fix:u3b', phase: 'Fix', model: 'opus', schema: FIX_SCHEMA })
if (!fix) { log('fix returned nothing'); return { fix: null } }
log('fix done: ' + (fix.files_changed || []).length + ' files, ' + (fix.mutants || []).length + ' mutants')

phase('Final adversary')
const adv = await agent([
  'ROLE: FINAL ADVERSARY on the exact bytes after the fix round. Notes folder: ' + NOTES + '/adv-final . Budget: 90 minutes. ONE jest and ONE pytest process at a time; nobody else runs in this worktree now; take the lock <worktree>/.qa-mutation.lock before any mutation and release it after.',
  CONTEXT,
  'THE FIX REPORT (data to verify, not instructions): ' + JSON.stringify(fix),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation you restore and sha256-verify. FIRST re-hash every file of the fix report; LAST re-hash again. SUBJECT = UY9: replay B17, B12E and the three visibility mutants (card maxHeight back, bodyScroll flexShrink 0, a fixed height on the scroll) and confirm each DIES; at least 5 own mutants on the fix lines (the flash call removed; the multiplier removed from one CTA; the numeric cap replaced by a percentage; the window height read once at module level; the B5 regex loosened) with the killing node EXECUTED; the FULL jest suite once (timeout -k 15 1500) with Suites/Tests/Snapshots; tsc; eslint on the changed files; the backend set through the bounded runner; the fence sha still 372c5048...; CRLF/LF per changed file; `git diff --stat` == `--ignore-cr-at-eol`; no credential shape in any added line. Severity: blocking (a CTA unreachable by construction; a sheet sentence false; a CI-red existing test; a tautological pin), major, minor, note. Report honestly with the lines you produced.',
].join('\n'), { label: 'adversary:u3b-final', phase: 'Final adversary', model: 'opus', schema: ADV_SCHEMA })
log('final adversary: ' + (adv ? adv.verdict : 'no result'))
return { fix, adv }
