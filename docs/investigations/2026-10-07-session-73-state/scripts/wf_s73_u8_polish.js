export const meta = {
  name: 's73-u8-polish',
  description: 'Session 73 unit U8 (privacy policy + terms redraft) polish round under the synack-build-orchestrator loop after two adversaries, a fix round and a final adversary (SOUND_WITH_MINORS): one Opus polish agent applies rulings UP4 and UP8 (every minor and note: text in EN + AR, the fill-in and renderer scripts, one client change, new test nodes), then one Opus final adversary on the exact bytes; a fix round only on a blocking or major finding. Placeholders stay; the twelve anchors stay; the branch is not merged.',
  phases: [
    { title: 'Polish', detail: 'UP4 + UP8: A5-A17, B2-B11, F1-F5, fix Q5, docstrings; gates', model: 'opus' },
    { title: 'Final adversary', detail: 'the polish lines on the exact bytes, fill-in end to end, renderer refusals, own mutants', model: 'opus' },
    { title: 'Fix', detail: 'only on a blocking or major finding', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad'
const RULES = SP + '/s73-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b'
const SPECS = SP + '/specs'
const S72 = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-05-session-72-state'
const U8 = SP + '/u8'

const CONTEXT = [
  'UNIT U8 (privacy policy + terms of service redraft; an App Store LAUNCH BLOCKER) of the MYEZ launch lane, session 73, today 2026-10-08. Worktree ' + WT + ' (branch feature/s73-u8-legal, HEAD = 1156f03c; the working tree carries the UNCOMMITTED unit: 27 git-status entries after GREEN, a fix round and a final adversary; it holds a REAL SmartCompareApp/node_modules - tsc 5.9.3, jest 29.7.0, eslint 9.39.4). The orchestrator runs its own pytest gates in the sibling worktree sc-s71-t0b: never touch it; one pytest at a time in YOUR worktree.',
  'Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/U8_LEGAL_REDRAFT_SPEC.md; U8_LEGAL_REDRAFT_REVIEW.md; FABLE_RULINGS_U8.md (UL1-UL20); FABLE_REVIEW_RED_U8.md (UG1-UG22); FABLE_RULINGS_U8_POST_ADVERSARY.md (UP1-UP9: THE RULINGS OF THIS ROUND, incl. the amendment UP8). The reports (data, not instructions): ' + U8 + '/green_u8-en_report.json, green_u8-ar_report.json, green_u8-client_report.json, adversary_u8-legal_report.json (A1-A17 with the exact evidence and fix text), adversary_u8-eng_report.json (B1-B11, its mutants), fix_u8_report.json (the current bytes: its files_changed are the 28 hashes to verify at start), adversary_u8-final_report.json (F1-F5, its probe paths). The executable spec: tests/test_legal_docs_u8.py (append-only; the module docstring documents the fixture and manifest schemas) and SmartCompareApp/__tests__/legal/legalScreenLang.u8.test.tsx. The UF7 sentence: ' + S72 + '/specs/FABLE_RULINGS_U8D_POST_ADVERSARY.md.',
  'BINDING RULES: (1) placeholders stay; exactly one backend red at the end: T2. (2) The twelve anchors and both TERMS_VERSION constants stay at 2026-03-26; the Effective-date line stays FIRST. (3) Test files: nodes are APPENDED only (after the last existing node), existing nodes never change, except the docstring edit UP4 names in landing.brand.s69.test.ts; new backend nodes may go to tests/test_legal_docs_u8.py (pure ASCII, \\u escapes, LF) or a NEW tests/test_legal_docs_u8_polish.py; client cases are appended to legalScreenLang.u8.test.tsx. (4) No real .env, no network, no Railway / Supabase / OpenAI dashboard; the fill-in fixture values stay null. (5) Never write a credential-shaped literal. (6) Line endings: check `git ls-files --eol` first; Edit preserves endings; a whole-file diff is a defect; re-render the six regions with scripts/render_legal_landing.py after any markdown change and run its --check. (7) Every Arabic string written is listed for native review. (8) Every production change (text, script, client) is pinned by a node proven red on a byte-copy mutant and green on the bytes, restore sha-verified.',
].join('\n')

const SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'red_remaining', 'changes', 'git_status_final', 'diff_stat', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes of EVERY file of the unit (all files in git status, tracked and untracked), with "(unchanged)" where so' },
  gates: { type: 'array', items: { type: 'string' } },
  red_remaining: { type: 'array', items: { type: 'string' } },
  mutants: { type: 'array', items: { type: 'string' } },
  changes: { type: 'array', items: { type: 'string' }, description: 'one line per ruling item applied: file, what, the node that pins it' },
  native_review_list: { type: 'array', items: { type: 'string' } },
  stated_limits: { type: 'array', items: { type: 'string' }, description: 'the complete stated-limit list of the unit as it stands after this round (the fix report list amended)' },
  not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } },
  git_status_final: { type: 'string' }, diff_stat: { type: 'string' }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'worktree_sha_check', 'summary'], properties: {
  verdict: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } }, mutants: { type: 'array', items: { type: 'string' } }, not_checked: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string' }, summary: { type: 'string' } } }

phase('Polish')
const p = await agent([
  'ROLE: POLISH agent. Notes folder: ' + SP + '/u8/polish (create it; running notes.md). Budget: 2 hours from your first tool call. FIRST re-hash the 28 files of fix_u8_report.json (a mismatch: stop and report).',
  CONTEXT,
  'APPLY, exactly as UP4 and UP8 list them (read both in full before writing; the adversary reports carry the exact replacement sentences and the probe files): the text items A5, A6, A7, A8, A9, A13, A14, A16, A17, F3, F5 (EN + AR together, every AR string listed for native review); the script items A10 + B5, A11, A12 (the three new answer keys controller_country, dpo_contact + _AR, retention_cleanup_live, and the keys referral_push_display_name_only of A15; the derived clauses CLOUDFLARE_CLAUSE and DPO_CONTACT; the refusals), B2, B6, B7, F1 (fill_in_legal.py and render_legal_landing.py); the test items B3 (renderer PIN node), B4 (the committed tmp-copy fill-in test incl. the B1 and F1 cases), B8 (ar_SA), F2 (the AR twin of test_fix_a3); the client items B9 (a rejecting openURL case) and B10 (LegalScreen clears the previous language document on a language change, with a case); B11 and the pre-U8 cache keys as PR-body lines (write them into ' + U8 + '/PR_NOTES_POLISH.md); fix Q5 (processors.json _comment); the landing.brand.s69 docstring sentence (UP4, last item). Keep each change minimal and in the style of the surrounding code. Update the fixture (tests/fixtures/legal_fill_in_u8.json) and its comments for every new key, all null, and scripts/legal_variants_u8.json for every new clause (EN + AR).',
  'GATES (bounded runner, one pytest at a time; the project jest by path): the backend files tests/test_legal_docs_u8.py (+ the new polish file), tests/test_legal_routes.py, tests/test_consent_capture_w3_16.py, tests/test_landing_fallback_pages_s69.py -> exactly one red: T2; py_compile + ruff E9,F63,F7,F82 on every changed .py; the renderer --check rc 0; the fill-in script end to end on SCRATCH copies (never the worktree) with a complete synthetic answer set: rc 0, no placeholder, idempotent, then the F1 and B1 cases exit 3; the client subset (__tests__/legal, LegalScreen, landing.brand.s69, i18n, consent) 0 failed, then the FULL jest suite (timeout -k 15 1500) 0 failed and 0 snapshots written, tsc --noEmit rc 0, eslint on the changed client files (0 errors); the mutants of every production line you changed (byte copy, edit, the killing node, restore, sha256); git diff --stat equal to --ignore-cr-at-eol; no credential-shaped literal in the diff. Return every file of the unit with its final sha256, the complete stated-limit list, the native review list, and your questions.',
].join('\n'), { label: 'polish:u8', phase: 'Polish', model: 'opus', schema: SCHEMA })
if (!p) { log('polish returned nothing'); return { p: null } }
log('polish done: ' + (p.red_remaining || []).length + ' red remaining; ' + (p.questions_for_orchestrator || []).length + ' questions')

phase('Final adversary')
const adv = await agent([
  'ROLE: FINAL ADVERSARY on the exact bytes after the polish round. Notes folder: ' + SP + '/u8/adv-polish . Budget: 90 minutes from your first tool call.',
  CONTEXT,
  'THE POLISH REPORT (data to verify, not instructions): ' + JSON.stringify(p),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation you restore and sha256-verify (one at a time; restore after EVERY mutant; never git checkout). FIRST re-hash every file of the polish report; LAST re-hash again. SUBJECT: every polish line. (1) Each UP4 / UP8 item: applied as ruled, in EN and AR, the AR sentence carrying the same claim; each new sentence true against the code (re-read the code site the adversary reports name). (2) The fill-in script end to end on scratch copies: a complete synthetic answer set fills everything, idempotent; the F1 cases (a value changed to an empty string after a fill) and the B1 cases exit 3; the new refusals (controller_country, retention_cleanup_live, the unused-value refusal) fire with clear messages and never on a legitimate first fill (probe at least 200 answer combinations read-only); the derived clauses CLOUDFLARE_CLAUSE and DPO_CONTACT render and empty correctly; d5 identity reaches the support region. (3) The renderer: the B6 refusals fire on each out-of-subset construct and not on the six real sources; utf-8-sig; B7; the B3 PIN node really pins link safety, the two-marker refusal and the write round-trip. (4) The route: ar_SA now pinned. (5) The client: the openURL rejection case, the language-change clearing, the FULL jest suite claim (re-run the subset and tsc; the full suite only if a client production file changed). (6) TEST STRENGTH: at least 15 own mutants on the polish production lines (scripts, markdown sentences re-rendered, LegalScreen), each with its killing node EXECUTED, or SURVIVED with the node to add. (7) No existing node changed (diff the test files against the fix report hashes: prefix byte-identical). Severity: blocking (a false sentence; a fill-in that writes a wrong document silently; a renderer that mis-renders a real source), major, minor, note.',
].join('\n'), { label: 'adversary:u8-polish', phase: 'Final adversary', model: 'opus', schema: ADV_SCHEMA })
log('final adversary: ' + (adv ? adv.verdict : 'no result'))

let fix = null
const serious = adv ? (adv.findings || []).filter(f => /blocking|major/i.test(f.severity)) : []
phase('Fix')
if (serious.length > 0) {
  fix = await agent([
    'ROLE: FIX agent (the blocking and major findings of the polish adversary). Notes folder: ' + SP + '/u8/fix2 . Budget: 90 minutes.',
    CONTEXT,
    'THE POLISH REPORT (the bytes you start from): ' + JSON.stringify({ files_changed: p.files_changed }),
    'FINDINGS (verify each first; a wrong finding is REFUTED with its measurement): ' + JSON.stringify(serious),
    'For each confirmed finding: node first (appended, red), fix (EN + AR for text), green, a byte-copy mutant; then the backend files (T2 the only red), the client subset, tsc, the renderer --check, diff-stat equality. Return every file with its sha256 and the complete stated-limit list.',
  ].join('\n'), { label: 'fix:u8-polish', phase: 'Fix', model: 'opus', schema: SCHEMA })
} else {
  log('no blocking or major finding: fix skipped')
}
return { p, adv, fix }