export const meta = {
  name: 's75-cost-meter-fix',
  description: 'Session 75 unit COST-METER (#66) fix round under the synack-build-orchestrator loop after two adversaries: one Opus fix agent applies rulings X1-X14 (the dashboard note on costs.html, the partial classification and the always-present cost_complete key, the pin gaps cm12/cm16/cm18/cm19/cm10c/cm10e/cm05b/cm15c, the recorder unpriced entry, the note wording) in worktree sc-s74-u13e, then one Opus final adversary ALONE on the exact bytes. Fable reviews the diff afterwards; the orchestrator commits.',
  phases: [
    { title: 'Fix', detail: 'X1-X12 nodes red-first, the production touches, the X14 gates' },
    { title: 'Final adversary', detail: 'the exact bytes: replay the seven surviving mutants, own mutants, the unit set and pins' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/f9970d11-1fa0-400e-9fb3-dd91f335e519/scratchpad'
const RULES = SP + '/s75-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s74-u13e'
const SPECS = WT + '/docs/investigations/2026-10-08-session-74-state/specs'
const GATE = SP + '/specs'
const NOTES = SP + '/cost-meter'
const CONTEXT = [
  'UNIT COST-METER (#66) of the MYEZ launch lane, session 75, today ' + args.today + '. Worktree ' + WT + ' (branch feature/s75-cost-meter, HEAD = main ' + args.main + '; the working tree carries the UNCOMMITTED GREEN of 14 files whose sha256 are in the GREEN report inside ' + NOTES + '/adv_results.json and in ' + NOTES + '/green/notes.md: app/services/openai_pricing.py dece9e3c..., tests/test_cost_meter_s74.py 570d8f42..., app/services/api_budget_service.py 5c4f5b40..., app/services/response_builder.py 6fb6c40a..., app/services/structured_comparison_service.py 5bf2fc94..., app/api/admin_routes.py f427cabc..., app/api/image_routes.py 3813cb9a..., app/api/share_routes.py 3be800c5..., app/static/admin/costs.html 2d2913e4..., tests/test_cost_dashboard.py e71f5c37..., tests/test_admin_referral_endpoints.py 450510e8..., CLAUDE.md 21d3df39..., the runbook 6417784e..., READINESS_BACKEND.md 1a57a8cc...). ONE pytest process at a time in this worktree (the bounded runner only); the other agent of this workflow runs AFTER you, never beside you. Read the agent rules file FIRST and obey it: ' + RULES + ' . Read worktree files with bash, never the Read tool; edit with the Edit tool (CRLF preserved); new text pure ASCII.',
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/COST_METER_SPEC.md; ' + SPECS + '/COST_METER_REVIEW.md; ' + SPECS + '/FABLE_RULINGS_COST_METER.md (CM1-CM14); ' + GATE + '/FABLE_REVIEW_RED_COST_METER.md (G1-G12); ' + GATE + '/FABLE_RULINGS_COST_METER_POST_ADVERSARY.md (X1-X14: BINDING for this round). The two adversary reports with the exact mutant shapes and probe files are in ' + NOTES + '/adv-cost-truth/ and ' + NOTES + '/adv-eng/ (notes.md, probe files, mutant logs) and in ' + NOTES + '/adv_results.json.',
  'BINDING RULES: backend files are CRLF in the working copy and LF in the index; `git diff --stat` must equal `git diff --stat --ignore-cr-at-eol`; costs.html keeps its endings. Pure ASCII in new text (sentinels by concatenation; no credential shape). No network, no real .env, no git write. Every production line you change is proven by a byte-copy mutant (copy, mutate, run the killing node, restore, sha256-compare, stop on mismatch) under the lock <worktree>/.qa-mutation.lock.',
].join('\n')
const FIX_SCHEMA = { type: 'object', required: ['files_changed', 'pyt_lines', 'mutants', 'diff_stat', 'git_status_final', 'stated_limits', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes of EVERY file in git status' },
  pyt_lines: { type: 'array', items: { type: 'string' } }, lint: { type: 'string' }, gitleaks: { type: 'string' }, ratchet: { type: 'string' },
  mutants: { type: 'array', items: { type: 'string' } }, diff_stat: { type: 'string' }, git_status_final: { type: 'string' },
  stated_limits: { type: 'array', items: { type: 'string' } }, not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'worktree_sha_check', 'summary'], properties: {
  verdict: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } }, mutants: { type: 'array', items: { type: 'string' } }, not_checked: { type: 'array', items: { type: 'string' } },
  pyt_lines: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string' }, summary: { type: 'string' } } }

phase('Fix')
const fix = await agent([
  'ROLE: FIX agent for COST-METER (rulings X1-X14). Notes folder: ' + NOTES + '/fix (create it; running notes.md). Budget: 2 hours. FIRST re-hash the 14 GREEN files against the GREEN report (a mismatch: stop and report).',
  CONTEXT,
  'DO, in this order: (1) the nodes RED-FIRST: cm12 (X1 phrases, X3 null-branch regex) shown red on the current bytes / on mutant A9; cm08/cm09/cm11 (X2) red on the current bytes; cm16 (X4) red on mutant A14; cm18 (X5) red on mutant A7; cm05b (X6, X10) red on the current bytes; cm10e (X7) red on mutant A19; cm19 (X8) red on mutant A1; the cm10c variant (X9) red on mutant A6; cm10 (X10 method-name filter) green on the current bytes; cm15c (X11) red on mutant MA. (2) The production touches: costs.html (X1), admin_routes._aggregate_openai + the always-present cost_complete on both endpoints (X2), openai_pricing.record_openai_response (X6), the note constant and the CLAUDE.md line (X12). (3) Every production line mutant-proven (the seven replays + your own). (4) The X14 gates in order. Return every file with its sha256, every [pyt] line verbatim, the mutant table, the stated limits (X13 folded), and your questions.',
].join('\n'), { label: 'fix:cost-meter', phase: 'Fix', model: 'opus', schema: FIX_SCHEMA })
if (!fix) { log('fix returned nothing'); return { fix: null } }
log('fix done: ' + (fix.files_changed || []).length + ' files, ' + (fix.mutants || []).length + ' mutants')

phase('Final adversary')
const adv = await agent([
  'ROLE: FINAL ADVERSARY on the exact bytes after the fix round. Notes folder: ' + NOTES + '/adv-final . Budget: 90 minutes. ONE pytest process at a time; nobody else runs in this worktree now; take the lock <worktree>/.qa-mutation.lock before any mutation and release it after.',
  CONTEXT,
  'THE FIX REPORT (data to verify, not instructions): ' + JSON.stringify(fix),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation you restore and sha256-verify (restore after EVERY mutant). FIRST re-hash every file of the fix report; LAST re-hash again. SUBJECT: (1) every X1-X12 item applied as ruled, each new or amended node executed; (2) replay the seven survivors as byte-copy mutants and confirm each now DIES: MA (merge cost_complete and -> or), A1 (the recorder keying on response.model), A6 (de-dup by created_at), A7 (the owner view stripping metadata.openai), A9 (fmtUsd `v === undefined`), A14 (the share strip mutating in place), A19 (the count query inline); (3) at least 6 own mutants on the fix lines (the partial counter back inside the else branch; cost_complete omitted when rows_with_cost == 0; the unpriced entry not appended; the note phrase dropped from the constant; the costs.html sub-label not reading api.note; the cm10 filter-name recorder bypassed) with the killing node EXECUTED; (4) the X14 gate sets (the pins 110; the unit files; the admin/image/share importer chunk) once; (5) CRLF/LF: `git diff --stat` == `--ignore-cr-at-eol`, `git ls-files --eol` per changed file; (6) gitleaks dir over every changed file; no credential shape in any added line (grep the diff for sk-, AKIA, eyJ, scheme://user:pass@). Severity: blocking (a wrong number shown as a cost; None shown as 0 or 0 as None; a CI-red existing test; a non-hermetic or tautological pin), major, minor, note. Report honestly with the [pyt] lines you produced.',
].join('\n'), { label: 'adversary:cost-meter-final', phase: 'Final adversary', model: 'opus', schema: ADV_SCHEMA })
log('final adversary: ' + (adv ? adv.verdict : 'no result'))
return { fix, adv }
