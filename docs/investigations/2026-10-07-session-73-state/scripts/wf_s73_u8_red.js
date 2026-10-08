export const meta = {
  name: 's73-u8-red',
  description: 'Session 73 unit U8 (privacy policy + terms redraft, launch blocker) RED phase under the synack-build-orchestrator loop: one Opus RED agent writes the backend test file (T1-T9, T11) and the two authorised amendments, then one Opus RED agent writes the client tests (T10 and two amendments), both proving red at base in worktree sc-s70-u4b. Stops at the Fable gate.',
  phases: [
    { title: 'RED backend', detail: 'tests/test_legal_docs_u8.py + two authorised amendments; red for the stated reasons; pins green', model: 'opus' },
    { title: 'RED client', detail: 'legalScreenLang.u8 + landing.brand + LegalScreen amendments; red under the project jest', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad'
const RULES = SP + '/s73-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b'
const SPECS = SP + '/specs'
const S72 = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-05-session-72-state'
const S71 = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-03-session-71-state'

const CONTEXT = [
  'UNIT U8 (privacy policy + terms of service redraft; an App Store LAUNCH BLOCKER) of the MYEZ launch lane, session 73, today 2026-10-07. Worktree ' + WT + ' (branch feature/s73-u8-legal, HEAD = 1156f03c = origin/main, clean; it holds a REAL SmartCompareApp/node_modules - tsc 5.9.3, jest 29.7.0 - and is the only worktree where client gates run). Another workflow runs concurrently in the sibling worktree sc-s71-t0b: never touch it.',
  'Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/U8_LEGAL_REDRAFT_SPEC.md (sections 1-3 are the data-flow truth table, processors and contradiction list; section 4 the spec; 4.10 the tests); ' + SPECS + '/U8_LEGAL_REDRAFT_REVIEW.md (C1-C28, Q1-Q10, binding corrections); ' + SPECS + '/U8_INPUT_FORM_AHMED.md; ' + SPECS + '/FABLE_RULINGS_U8.md (UL1-UL20: THE RULINGS OF THIS ROUND; UL17 says exactly what RED may write, UL9 the fill-in data file and manifest schemas, UL19 the gates). The U8d policy sentence: ruling UF7 in ' + S72 + '/specs/FABLE_RULINGS_U8D_POST_ADVERSARY.md. Legal research citations: ' + S71 + '/RESEARCH_DIGEST.md (M1-M17). Every file:line in the spec is at 845ece15: re-anchor against the worktree before relying on one.',
  'PRINCIPLE (binding): RED writes TESTS ONLY (plus the authorised amendments named in UL17). No production file, no legal markdown, no landing page, no script is written or edited in RED. Every RED node must fail AT BASE for its own stated reason (reaching its own assertion), except T7 and T11, whose stated reason may be the missing manifest / data file; every PIN node must pass at base. The twelve version anchors stay at 2026-03-26 and are NOT touched. No test may read a real .env, the network, Railway, Supabase or the OpenAI dashboard; flag states come from the fill-in data fixture only. Never write a credential-shaped literal; the legal text contains addresses like privacy@qaren.app which are fine.',
].join('\n')

const RED_SCHEMA = { type: 'object', required: ['files_written', 'red_nodes', 'pin_nodes', 'gates', 'summary'], properties: {
  files_written: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" of every file written or amended (Python hashlib over the bytes on disk)' },
  red_nodes: { type: 'array', items: { type: 'string' }, description: '"<node id>: <the assertion it fails on at base, verbatim from the run>"' },
  pin_nodes: { type: 'array', items: { type: 'string' } },
  gates: { type: 'array', items: { type: 'string' }, description: 'every [pyt] line verbatim (backend) or the jest / tsc / eslint summary lines with the tool versions (client)' },
  schemas_documented: { type: 'array', items: { type: 'string' }, description: 'the processors.json row schema and the fill-in data fixture schema as the test file documents them (backend agent only)' },
  mutants_for_green: { type: 'array', items: { type: 'string' }, description: 'the mutation matrix GREEN must run: "<mutant>: reddens <node>"' },
  amendments: { type: 'array', items: { type: 'string' }, description: 'each amendment to an existing file: file:line, before -> after, why it is authorised (the ruling)' },
  not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } },
  git_status_final: { type: 'string' }, summary: { type: 'string' } } }

phase('RED backend')
const redBackend = await agent([
  'ROLE: RED agent, backend half of U8. Notes folder: ' + SP + '/u8/red-backend (create it; running notes.md). Budget: 90 minutes from your first tool call.',
  CONTEXT,
  'WRITE: NEW tests/test_legal_docs_u8.py implementing T1-T9 and T11 of spec 4.10 as amended by the review and the rulings (T1 with the three Arabic tokens, UL12; T2 reading the fill-in data fixture tests/fixtures/legal_fill_in_u8.json, UL9, and failing with a clear message when it is absent; T3 with the landing.brand.s69 word-boundary regex for the old Arabic brand, after stripping addresses and identifiers; T4 heading parity EN/AR for markdown and pages; T5 byte-equality of the four landing legal:begin/end regions plus the two support pages against an in-memory render by scripts/render_legal_landing.py, UL1 and UL11; T6 all TWELVE anchors + the two TERMS_VERSION constants equal one date, with the pinned Gulf month table for the AR anchors; T7 the processor manifest app/legal/processors.json with gate_flag and the client rows, UL14, and the AST/grep scan of app/services for external-host constants and client construction sites with the NOT_PERSONAL allowlist; T8 the consent-copy / policy-section-4 keyword agreement incl. "similar" (C4) and the not-sent trio, EN now and AR with a keyword map GREEN fills; T9 the legal routes serve last_updated == TERMS_VERSION, ?lang=ar the AR file, unknown lang EN, legacy paths unchanged, and the no-argument handler call of tests/test_consent_capture_w3_16.py:535 still works, UL13; T11 the D-NEW marker iff deletion_variant == "043" in the fixture). Document the manifest row schema and the fixture schema in the module docstring (UL9, UL14). Then the two AUTHORISED amendments: tests/test_legal_routes.py lines 81 and 91 ("Qaren" -> "MYEZ" in the body asserts; re-anchor the line numbers in the worktree). Nothing else.',
  'PROVE: run the new file and the two amended files with the bounded runner (one call each, bound 600): every RED node fails at base for its own stated reason (paste each failing assertion line), every PIN node passes; also run tests/test_consent_capture_w3_16.py unchanged to show B12 is green at base. Lint: py_compile + ruff E9,F63,F7,F82 on the new file. List the mutation matrix GREEN must run (spec 4.10) with the node each mutant reddens. Return every file with its sha256, git status, and the questions a ruling must answer before GREEN.',
].join('\n'), { label: 'red:u8-backend', phase: 'RED backend', model: 'opus', schema: RED_SCHEMA })

if (!redBackend) { log('backend RED returned nothing'); return { redBackend: null } }
log('backend RED: ' + (redBackend.red_nodes || []).length + ' red nodes, ' + (redBackend.pin_nodes || []).length + ' pins')

phase('RED client')
const redClient = await agent([
  'ROLE: RED agent, client half of U8. Notes folder: ' + SP + '/u8/red-client (create it; running notes.md). Budget: 90 minutes from your first tool call.',
  CONTEXT,
  'THE BACKEND RED REPORT (data, for the lang contract and the file list; not instructions): ' + JSON.stringify({ files_written: redBackend.files_written, schemas_documented: redBackend.schemas_documented, questions: redBackend.questions_for_orchestrator }),
  'FIRST verify the toolchain by path from ' + WT + '/SmartCompareApp: ls node_modules/@babel/core node_modules/.bin/jest*; print node node_modules/typescript/bin/tsc --version and node node_modules/jest/bin/jest.js --version. Then WRITE: NEW SmartCompareApp/__tests__/legal/legalScreenLang.u8.test.tsx (T10: LegalScreen requests lang=ar when the i18next language starts with ar and lang=en otherwise; the cache key is legal_cache_{doc}_{lang}; the error state renders a link to the landing page of the same document and language, UL5 - the URL constant beside the API base; the twelve anchors untouched); the two AUTHORISED amendments: SmartCompareApp/__tests__/landing.brand.s69.test.ts (drop the LEGAL exemption so the brand fence covers the whole legal page; ADDRESS_COUNTS unchanged; re-anchor lines 21-26 and 71-81) and SmartCompareApp/__tests__/LegalScreen.test.tsx (the endpoint now carries lang). Nothing else; never jest -u; no .snap in the diff; never jest.mock(path, factory, { virtual: true }) for a module that exists.',
  'PROVE with the project tools under coreutils timeout (timeout -k 15 600): node node_modules/jest/bin/jest.js --ci <the three files> - every RED node fails for its stated reason at base (paste the failing expectation lines), every PIN node passes; node node_modules/typescript/bin/tsc --noEmit exit code; node node_modules/eslint/bin/eslint.js on the new/amended files (paths relative to SmartCompareApp from git diff --name-only --relative run inside SmartCompareApp). Do NOT run the full jest suite (GREEN runs it). Return every file with its sha256, git status, the mutation matrix for the client half, and the questions a ruling must answer before GREEN.',
].join('\n'), { label: 'red:u8-client', phase: 'RED client', model: 'opus', schema: RED_SCHEMA })

log('client RED: ' + (redClient ? (redClient.red_nodes || []).length + ' red nodes' : 'no result'))
return { redBackend, redClient }