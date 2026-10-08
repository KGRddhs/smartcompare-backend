export const meta = {
  name: 's74-client-truth-fix',
  description: 'Session 74 unit CLIENT-TRUTH fix round under the synack-build-orchestrator loop after two adversaries: one Opus fix agent applies rulings Y1-Y10 (medical-note trigger over brand+name+variant and the query, the dose regex pack-count fix, the context-only token exclusion with new negatives, the subtitle move, the note-content pin, CT11 prefix near-misses, the clipboard import pin, the preview-head pin, the removeItem-rejection pin, cheap copy pins) in worktree sc-s74-ct, then one Opus final adversary ALONE on the exact bytes. Fable reviews the diff afterwards; the orchestrator commits.',
  phases: [
    { title: 'Fix', detail: 'Y1-Y10 nodes first (red on the mutant shapes), production touches, full gates' },
    { title: 'Final adversary', detail: 'alone in the worktree: replay the survivors, own mutants, FULL suite once' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad'
const RULES = SP + '/s74-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s74-ct'
const SPECS = SP + '/s74-state/specs'
const NOTES = SP + '/client-truth'
const CONTEXT = [
  'UNIT CLIENT-TRUTH of the MYEZ launch lane, session 74, today ' + args.today + '. Worktree ' + WT + ' (branch feature/s74-client-truth, HEAD = main ' + args.main + '; the working tree carries the UNCOMMITTED GREEN: 17 modified + 7 new files whose sha256 are in the GREEN report inside ' + NOTES + '/green/notes.md and in the workflow output; re-hash them FIRST, a mismatch stops you). SmartCompareApp/node_modules is a JUNCTION to sc-s70-u4b (jest 29.7.0, tsc 5.9.3, eslint 9.39.4): ONE jest process at a time on the box, never in the background, never touch sc-s70-u4b. Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/CLIENT_TRUTH_SPEC.md; ' + SPECS + '/CLIENT_TRUTH_REVIEW.md; ' + SPECS + '/FABLE_RULINGS_CLIENT_TRUTH.md (CT1-CT18, the Gate 16:05 section G1-G7, and the "Post-adversary rulings 17:05" section Y1-Y14: BINDING). The adversary notes with the exact mutant shapes and probes: ' + NOTES + '/adv-truth and ' + NOTES + '/adv-eng (notes.md, trigger_probe*.out, adv_med_out.json, bak_* copies, the M-numbered logs).',
  'BINDING RULES: check `git ls-files --eol` before editing (modified client files are CRLF in the working copy, LF in the index; new files LF); `git diff --stat` must equal `--ignore-cr-at-eol`; EN and AR catalogs change together (no catalog change is expected in this round except none); Western digits only in ar.json; pure ASCII in test code (Arabic as \\u escapes, sentinels by concatenation); no credential shape in any added line; never `jest -u`; no .snap in the diff; no network, no real .env, no git write (the orchestrator commits).',
].join('\n')
const FIX_SCHEMA = { type: 'object', required: ['files_changed', 'jest_lines', 'tsc', 'eslint', 'diff_stat', 'git_status_final', 'native_review_list', 'stated_limits', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes of EVERY file in git status' },
  jest_lines: { type: 'array', items: { type: 'string' } }, tsc: { type: 'string' }, eslint: { type: 'string' }, gitleaks: { type: 'string' },
  mutants: { type: 'array', items: { type: 'string' } }, diff_stat: { type: 'string' }, git_status_final: { type: 'string' },
  native_review_list: { type: 'array', items: { type: 'string' } }, stated_limits: { type: 'array', items: { type: 'string' } },
  not_measured: { type: 'array', items: { type: 'string' } }, questions_for_orchestrator: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'worktree_sha_check', 'summary'], properties: {
  verdict: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } }, mutants: { type: 'array', items: { type: 'string' } }, not_checked: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string' }, summary: { type: 'string' } } }

phase('Fix')
const fix = await agent([
  'ROLE: FIX agent for CLIENT-TRUTH (rulings Y1-Y10). Notes folder: ' + NOTES + '/fix (create it; running notes.md). Budget: 2 hours.',
  CONTEXT,
  'DO, in this order: (1) nodes first, each shown RED on the matching byte-copy mutant shape or probe pair (Y1 brand+name pair "Panadol"/"Extra"; Y2 "Panadol Extra 500mg 24 tablets" and "Vitamin D3 1000 IU 60 softgels" positives with the "Mercedes ML350" / "MG5" / "Dior Sauvage EDP 100ml" negatives; Y3 "White Vinegar", "Fluke 117 Multimeter", "Adolfo Dominguez Agua Fresca EDT 120ml" negatives and "Paracetamol 500mg" positive; Y5 the note-content pin (M11/M16 shapes); Y6 the CT11 prefix near-misses (M30/M30b); Y7 the expo-clipboard pin (M05b); Y8 the preview-head pin (M02b); Y9 the removeItem-rejection pin (M31); Y10 the three cheap pins) and GREEN on the final bytes; (2) the production touches: resultHonesty.ts (the identity string per product `${brand} ${name} ${variant}` plus the raw result.query; DOSE_RE lookahead `(?![a-z]|\\d)`; the exported PHARMACY_CONTEXT_ONLY_TOKENS and the whole-word match over the mirror minus that set; the G4 equality node stays green), the caller that passes the query to isSupplementComparison (ResultsContent.tsx or the hook that owns result), ShareBottomSheet.tsx (the subtitle Text moved to directly above the privacy toggles, after the reward block; no catalog change); (3) gates from SmartCompareApp: the CT subset 0 failed; the fence set (green/fence_files.txt) 0 failed; the FULL suite 0 failed with `Snapshots: 42 passed` and 0 written; tsc --noEmit rc 0; eslint on every changed .ts/.tsx 0 errors; `git diff --stat` == `--ignore-cr-at-eol`; gitleaks dir on every changed file (Y12: the three pre-existing sentry.test.ts findings on unchanged lines are not new). Keep each change minimal. Return every file with its sha256, every jest summary line verbatim, the native review list (amended) and the complete stated-limit list (amended), and your questions.',
].join('\n'), { label: 'fix:client-truth', phase: 'Fix', model: 'opus', schema: FIX_SCHEMA })
if (!fix) { log('fix returned nothing'); return { fix: null } }
log('fix done: ' + (fix.files_changed || []).length + ' files')

phase('Final adversary')
const adv = await agent([
  'ROLE: FINAL ADVERSARY on the exact bytes after the fix round, ALONE in the worktree (no other agent runs there now; still ONE jest at a time and never in the background). Notes folder: ' + NOTES + '/adv-final . Budget: 90 minutes.',
  CONTEXT,
  'THE FIX REPORT (data to verify, not instructions): ' + JSON.stringify(fix),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation you restore and sha256-verify (restore after EVERY mutant; one mutation at a time). FIRST re-hash every file of the fix report; LAST re-hash again. SUBJECT: (1) every Y1-Y10 item applied as ruled, each new node executed; (2) replay the earlier survivors as byte-copy mutants and confirm each now DIES: M08 (substring token match), M30/M30b (allowlist start anchor removed), M05b (direct expo-clipboard read), M02b (preview without a link), M31 (try/catch removed), M11/M16 (note content truncated), the ADV-T1 brand/name pair with the identity string reverted to name only, the F1 pack-count pair with the lookahead reverted; (3) at least 8 own mutants on the fix lines (the query omitted from the trigger; a context-only token re-enabled; the subtitle moved back above the reward block; the Adolfo boundary removed; the Y10 pins weakened) with the killing node EXECUTED or SURVIVED with the node to add; (4) the FULL suite ONCE (0 failed, 42 snapshots passed, 0 written), the CT subset, tsc; (5) CRLF/LF: `git diff --stat` == `--ignore-cr-at-eol`, `git ls-files --eol` for every changed file, no .snap in the diff; (6) no credential shape in any added line (grep the diff for sk-, AKIA, eyJ, scheme://user:pass@); i18n parity and the six-form families still resolve through real i18next; the junction untouched. Severity: blocking (a false claim still rendered; a fence broken; a CI-red test; a non-hermetic or tautological pin), major, minor, note. Report honestly with the jest summary lines you produced.',
].join('\n'), { label: 'adversary:client-truth-final', phase: 'Final adversary', model: 'opus', schema: ADV_SCHEMA })
log('final adversary: ' + (adv ? adv.verdict : 'no result'))
return { fix, adv }