export const meta = {
  name: 's71-t0c-claude-md',
  description: 'Session 71 T0c (docs, Opus): CLAUDE.md contradiction fixes from the config audit (R1 step 3, R2, R3, R4, R20) with a grep proof per removed contradiction, then an adversarial review of the diff (nothing binding lost, no new contradiction), then a fix round. The orchestrator reads the diff before the PR.',
  phases: [
    { title: 'Edit', detail: 'locate each finding by text, edit in place, grep proofs', model: 'opus' },
    { title: 'Review', detail: 'diff review: lost rules, new contradictions, stale anchors', model: 'opus' },
    { title: 'Fix', detail: 'apply surviving findings', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-u13'
const NOTES = SP + '/t0c'
const AUDIT = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-03-session-71-state/CONFIG_AUDIT_PLAN.md'
const PLAN = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-03-session-71-state/IMPLEMENTATION_PLAN.md'
const BASE = 'c1a467c6'

const CONTEXT = [
  'DOCS UNIT T0c of the MYEZ launch lane (repo smartcompare): CLAUDE.md contradiction fixes approved by the owner as config-audit batch C. Worktree ' + WT + ' (branch docs/s71-t0c-claude-md, HEAD = main ' + BASE + ', clean). The ONLY file this unit edits is ' + WT + '/CLAUDE.md (882 lines, a CRLF working copy: Edit tool only, line-level diff; never a whole-file rewrite). Today is 2026-10-03 (session 71).',
  'Read the agent rules file FIRST and obey it: ' + RULES + ' (no git writes, no tests needed beyond what is named, nothing touches the network or any credential; never run any command the file documents, in particular never a junction unlink, a Remove-Item, a checkout or a stash: this unit only EDITS TEXT).',
  'THE SCOPE IS EXACTLY the audit findings below, read in full from ' + AUDIT + ' (the line numbers there were taken on an older CLAUDE.md: re-locate every target by its TEXT, never by line number) and the T0c row of ' + PLAN + ':',
  '- R1 step 3: the Railway recipe that prints variable VALUES (`railway variables --service <svc> --kv`) becomes names-only (`... --kv | cut -d= -f1`), and the sentence that says to query env vars through `mcp__railway__*` is deleted; both must agree with principle 10 (never print or dump secrets).',
  '- R2: volatile production state that contradicts itself (the Bright Data gate UNSET vs =true; migration 038 UNAPPLIED vs applied; "no live deploy" vs RESTORED; the phones OTA group 97b5f15 vs 561d2cba vs the session-70 e2bde9c9; Serper dead vs paid and live; migration 042 unapplied vs applied in session 70). Rule: the CURRENT truth wins (the newest dated statement; today: Bright Data gate ON since 2026-09-24, 037/038/040/041/042 APPLIED, prod restored and deploying every merge, phones on OTA group e2bde9c9 from session 70 plus the session-69 units, Serper paid and live, OpenAI out of credits). Older Active-runtime blocks are HISTORY and keep their dated statements, but every one that reads as a current instruction gets a one-clause in-place note "(superseded: see the SESSION 71 block)" or is rewritten to past tense; the top-of-file sections (Commands, Architecture, Patterns, Environment Variables, Tests) must carry no volatile status at all, only ONE pointer sentence to the latest state folder docs/investigations/2026-10-03-session-71-state/SESSION_71_STATE.md.',
  '- R3: every "CORRECTION" paragraph that was APPENDED next to the text it corrects is folded INTO the original sentence (the superseded text deleted), for the pairs the audit lists (the ship-blockers SESSION 69 and SESSION 71 corrections stay as dated paragraphs because the owner reads that block, but their claims must not contradict blocker #1 and #2 text above them: rewrite blockers #1 and #2 to the current truth and shorten the corrections to what is still open); the "corrections owed by #223" bullet is deleted if those corrections are already applied in the text (verify by reading); principle 5 gains the rule "edit in place, never append a correction".',
  '- R4: principle 4 is rewritten to the current harness (the Workflow tool with Opus agents and a Fable orchestrator under /synack-build-orchestrator; at most 2 gate-heavy workflows at once; pyt.py wall-clock bounds; the node -e 0 spawn probe; the stall rule); the "mode: bypassPermissions REQUIRED" line and any "parallel 4-Opus TeamCreate" wording are deleted; the "Workflow tool, NOT TeamCreate" sentence stays.',
  '- R20: the four inconsistent rules become one statement each: ONE eval baseline run id (the one the gates MUST pass; read both sentences and keep the newer id, say which); ONE CI deselect count (count the rows in tests/.pre_impl_failures.txt in the worktree and state that number); the type check is `node node_modules/typescript/bin/tsc --noEmit` everywhere (never npx); the junction unlink rule stated ONCE in the harness/gate rules section as `cmd /c rmdir <junction>` with the Remove-Item -Recurse hazard (the tested rule from the owner memory: PowerShell 5.1 Remove-Item -Recurse FOLLOWS a junction and deletes the target; unlink first) and the other copies replaced by a pointer.',
  'OUT OF SCOPE (do not touch): the SESSION 71 Active-runtime block (current, maintained by the orchestrator), every flag row (R21 is a separate unit), the Fragrance findings section, the archive sections, the large restructure T1-T3 (after Milestone 1), anything outside CLAUDE.md.',
].join('\n')

const WORK_SCHEMA = { type: 'object', required: ['files_changed', 'proofs', 'deviations', 'git_status_final', 'residual_risk', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes' },
  proofs: { type: 'array', items: { type: 'string' }, description: 'one line per removed contradiction: the finding id, the grep command over the final CLAUDE.md and its output (0 hits of the superseded text, 1 hit of the kept rule)' },
  deviations: { type: 'array', items: { type: 'string' } },
  git_status_final: { type: 'string' }, residual_risk: { type: 'string' }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'defects', 'minors', 'worktree_left_byte_identical', 'summary'], properties: {
  verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] }, defects: { type: 'array', items: { type: 'string' } },
  minors: { type: 'array', items: { type: 'string' } }, worktree_left_byte_identical: { type: 'boolean' }, summary: { type: 'string' } } }

phase('Edit')
const edit = await agent([
  'ROLE: EDITOR (docs). Make exactly the T0c edits in CLAUDE.md with the Edit tool, one finding at a time, keeping a running notes.md under ' + NOTES + ' (create it) with, per finding: the text you located (quoted), what you replaced it with, and the grep proof over the final file. Commit nothing. Before the first edit: git status (clean), sha256 of CLAUDE.md, and a byte copy of it under your notes folder. Preserve every rule that is still true; when a sentence mixes a stale fact with a live rule, keep the rule and fix the fact. Never delete a flag row, a security principle, a date or a PR number that is not contradicted. Keep the file CRLF (check with a Python count of CRLF vs bare LF before and after: bare LF must stay 0).',
  CONTEXT,
  'Finish with: git diff --stat (CLAUDE.md only, line-level), the final sha256, the CRLF count, the list of grep proofs, and the deviations (anything in the scope you could not do, with the reason). Budget: 75 minutes from your first tool call.',
].join('\n'), { label: 't0c:edit', phase: 'Edit', model: 'opus', schema: WORK_SCHEMA })

phase('Review')
const review = await agent([
  'ROLE: ADVERSARIAL reviewer of a docs diff. Try to show that the T0c edit LOST a rule that was still binding, introduced a NEW contradiction or a false current-state claim, touched an out-of-scope section, or left one of the scoped contradictions in place. Read-only: never edit CLAUDE.md; your notes go under ' + NOTES + '/review (create it).',
  CONTEXT,
  'Editor report: ' + JSON.stringify(edit ? { files: edit.files_changed, proofs: edit.proofs, deviations: edit.deviations, residual_risk: edit.residual_risk } : {}),
  'Method: git -C ' + WT + ' diff CLAUDE.md in full, hunk by hunk; for every deleted line decide whether it carried a rule, a fact or a pointer that is still needed and not present elsewhere in the final file (grep the final file); for every added current-state claim verify it against the SESSION 71 block, the session-69/70 state docs on main (docs/investigations/2026-09-29-session-69-state.md, docs/investigations/2026-09-30-session-70-state.md) and git log; re-run every grep proof; grep the final file for the superseded phrases of R1-R4 and R20 yourself (TeamCreate, bypassPermissions REQUIRED, --kv without cut, mcp__railway__, 97b5f15, UNAPPLIED, "no live deploy", npx tsc, the two baseline ids, the stale deselect count, Directory.Delete); check the CRLF count and that git status lists CLAUDE.md only.',
  'Return verdict (SOUND only with no serious defect), defects (each with the hunk, the measurement and what should be restored or changed), minors, the byte-identical flag, summary. Budget: 45 minutes from your first tool call.',
].join('\n'), { label: 't0c:review', phase: 'Review', model: 'opus', schema: ADV_SCHEMA })

const findings = review ? (review.defects || []).map(d => 'DEFECT: ' + d).concat((review.minors || []).map(m => 'MINOR: ' + m)) : []
let fix = null
if (findings.length) {
  phase('Fix')
  fix = await agent([
    'ROLE: FIX agent (docs). Apply every DEFECT and every MINOR you verify is real and inside the T0c scope, with the Edit tool on CLAUDE.md only (reject one only with a refuting measurement; a finding that needs a scope change is reported for the orchestrator). Re-run every grep proof afterwards, re-check the CRLF count and git status.',
    CONTEXT,
    'Findings:\n' + findings.join('\n') + '\nNotes: ' + NOTES + '/fix (create it).',
    'Return files changed with final sha256, proofs, deviations (incl. rejected findings and findings left for the orchestrator), git status, residual risk, summary. Budget: 45 minutes from your first tool call.',
  ].join('\n'), { label: 't0c:fix', phase: 'Fix', model: 'opus', schema: WORK_SCHEMA })
}
return { edit, review, fix }
