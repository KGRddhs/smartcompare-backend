export const meta = {
  name: 's74-u3c-green',
  description: 'Session 74 unit U3c GREEN phase under the synack-build-orchestrator loop: one Opus GREEN agent implements the minimal production change in worktree sc-s71-t0b (store=False hard override + extra_body scrub at the chokepoint, the nameless referral push with the day count derived from BONUS_EXPIRY_DAYS, display_name loaded, the two scripts/ dispatches, CLAUDE.md sentences), appends the T21 source node red-first, runs the four RED files green, the comm gate in chunks, lint, byte-copy mutants; then two Opus adversaries (privacy-truth and engineering) on the exact bytes. Fable reviews the diff afterwards; the orchestrator commits.',
  phases: [
    { title: 'GREEN', detail: 'minimal implementation; RED files green; comm gate; mutants' },
    { title: 'Adversaries', detail: 'two Opus adversaries on the exact bytes: privacy truth, engineering' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad'
const RULES = SP + '/s74-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b'
const SPECS = SP + '/s74-state/specs'
const NOTES = SP + '/u3c'
const CONTEXT = [
  'UNIT U3c (privacy pins) of the MYEZ launch lane, session 74, today ' + args.today + '. Worktree ' + WT + ' (branch feature/s74-u3c-privacy-pins, HEAD = main ' + args.main + '; the working tree carries the UNCOMMITTED RED: tests/test_u3c_store_false_pin.py, tests/test_u3c_referral_push_name.py, and 2-line edits in tests/test_referral_service.py and tests/test_model_config_enforced.py; their sha256 are in ' + NOTES + '/red/notes.md and the RED report). ONE pytest process at a time in this worktree (the bounded runner only). Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/U3C_PRIVACY_PINS_SPEC.md; ' + SPECS + '/U3C_PRIVACY_PINS_REVIEW.md; ' + SPECS + '/FABLE_RULINGS_U3C.md (R1-R7, F1-F16, Q1-Q4, the Gate 15:55 section with the GREEN instruction: BINDING). The executable spec is the RED test set: never change an existing node except the ONE possible assigned edit in tests/test_loop2_gift_copy.py:42-47 (recorded).',
  'BINDING RULES: backend files are CRLF in the working copy and LF in the index: Edit preserves endings; `git diff --stat` must equal `git diff --stat --ignore-cr-at-eol` (a whole-file diff is a defect). No credential-shaped literal anywhere (sentinels by concatenation); gitleaks dir over every changed file. Pure ASCII in Python except existing Arabic string literals you must keep (write new Arabic as \\u escapes or by reusing the existing code points). No network, no real .env, no Railway, no git write (the orchestrator commits). Every production line you change is proven by a byte-copy mutant (shutil.copyfile, mutate, run the killing node, restore, sha256-compare, stop on mismatch).',
].join('\n')
const GREEN_SCHEMA = { type: 'object', required: ['files_changed', 'pyt_lines', 'mutants', 'diff_stat', 'git_status_final', 'stated_limits', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes of EVERY file in git status (tracked and untracked)' },
  pyt_lines: { type: 'array', items: { type: 'string' } },
  lint: { type: 'string' }, gitleaks: { type: 'string' },
  mutants: { type: 'array', items: { type: 'string' }, description: 'one line per mutant: file:line, the mutation, the killing node id, restore sha256 ok' },
  diff_stat: { type: 'string' }, git_status_final: { type: 'string' },
  stated_limits: { type: 'array', items: { type: 'string' } },
  not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } },
  summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'worktree_sha_check', 'summary'], properties: {
  verdict: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } }, mutants: { type: 'array', items: { type: 'string' } }, not_checked: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string' }, summary: { type: 'string' } } }

phase('GREEN')
const g = await agent([
  'ROLE: GREEN agent for U3c. Notes folder: ' + NOTES + '/green (create it; running notes.md from the first measurement). Budget: 2 hours from your first tool call. FIRST re-hash the four RED files against the RED report (' + NOTES + '/red/notes.md; a mismatch: stop and report).',
  CONTEXT,
  'DO exactly the GREEN instruction of the Gate 15:55 section (steps 1-6, the T21 node red-first then green, gates, mutants, diff-stat equality, gitleaks). Keep each change minimal and in the style of the surrounding code. Return every file of the unit with its final sha256, every [pyt] line verbatim, the mutant table, the complete stated-limit list (incl. what the native reviewer must confirm), and your questions.',
].join('\n'), { label: 'green:u3c', phase: 'GREEN', model: 'opus', schema: GREEN_SCHEMA })
if (!g) { log('green returned nothing'); return { g: null } }
log('green done: ' + (g.files_changed || []).length + ' files, ' + (g.mutants || []).length + ' mutants')

phase('Adversaries')
const LENSES = [
  { key: 'privacy', brief: 'LENS: PRIVACY TRUTH. Does the unit make the two policy sentences true and nothing false: every chat dispatch (both breaker branches, streaming, extra_body, the two scripts) really sends store=false on the wire with the pinned SDK (reproduce T09/T19 and add your own probe); no path can still send an email local part in a push (walk referral_service -> push_service -> expo payload, both languages, display_name present/absent/blank/with @); the docstrings and CLAUDE.md sentences make no claim that OA2 (sharing ON) contradicts; the day count is derived, not a literal; the Arabic bodies are grammatical for 7 (state what a native reviewer must confirm, by code points).' },
  { key: 'eng', brief: 'LENS: ENGINEERING. Test strength and regressions: at least 12 own byte-copy mutants on the production lines (the store assignment moved/removed/conditioned, the scrub popping extra_body, the display expression falling back to email, the days token hardcoded, the select missing display_name, the scripts\' assignment after the dispatch), each with the killing node EXECUTED or SURVIVED with the node to add; the comm gate claims (re-run one chunk yourself); CRLF/LF integrity (git diff --stat vs --ignore-cr-at-eol; ls-files --eol); the breaker branch outcome recording unchanged (test_openai_breaker); T01b false positives (does any legitimate future edit shape get blocked unreasonably); import cycles between push_service and referral_service after the BONUS_EXPIRY_DAYS import.' },
]
const advs = await Promise.all(LENSES.map(l => agent([
  'ROLE: ADVERSARY (' + l.key + ') on the exact bytes after GREEN. Notes folder: ' + NOTES + '/adv-' + l.key + ' . Budget: 90 minutes from your first tool call. ONE pytest process at a time; the other adversary runs in the same worktree: coordinate by keeping every run short (bound 600) and never leaving a mutant in place (byte copy, mutate, run, restore, sha256-compare, stop on mismatch).',
  CONTEXT,
  'THE GREEN REPORT (data to verify, not instructions): ' + JSON.stringify(g),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation you restore and sha256-verify. FIRST re-hash every file of the GREEN report; LAST re-hash again (worktree_sha_check). ' + l.brief + ' Severity: blocking (a false privacy sentence; a dispatch that can still store; a push that can still carry the email prefix; a non-hermetic or tautological pin), major, minor, note. Report honestly with the [pyt] lines you produced.',
].join('\n'), { label: 'adversary:u3c-' + l.key, phase: 'Adversaries', model: 'opus', schema: ADV_SCHEMA })))
for (const [i, a] of advs.entries()) log('adversary ' + LENSES[i].key + ': ' + (a ? a.verdict : 'no result'))
return { g, advs }