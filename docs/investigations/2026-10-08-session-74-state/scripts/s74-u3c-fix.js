export const meta = {
  name: 's74-u3c-fix',
  description: 'Session 74 unit U3c fix round under the synack-build-orchestrator loop after two adversaries: one Opus fix agent applies rulings X1-X10 (the W4-11 fixture store entries, T01c, Mapping-aware extra_body scrub with new T18/T19 parameters, the T03 spread allowlist + extra_query, the narrowed T02, the T21 extension, T22, T23, the CLAUDE.md:517 clause) in worktree sc-s71-t0b, then one Opus final adversary on the exact bytes. Fable reviews the diff afterwards; the orchestrator commits.',
  phases: [
    { title: 'Fix', detail: 'X1-X10 nodes first (red on the mutant shapes), two production touches, gates' },
    { title: 'Final adversary', detail: 'the exact bytes: replay the adversaries\' mutants, own mutants, the comm gate once' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad'
const RULES = SP + '/s74-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b'
const SPECS = SP + '/s74-state/specs'
const NOTES = SP + '/u3c'
const CONTEXT = [
  'UNIT U3c (privacy pins) of the MYEZ launch lane, session 74, today ' + args.today + '. Worktree ' + WT + ' (branch feature/s74-u3c-privacy-pins, HEAD = main ' + args.main + '; the working tree carries the UNCOMMITTED GREEN: CLAUDE.md 0fc23541ec84622060182f14c2c939ad0c3e4e57c5a41890d83f8c4a0cc4b6bf, app/services/api_budget_service.py d0f2583b41eb637785b8af0f2fdb87782d4533f75477ab48df4c942d051f64cd, app/services/push_service.py ef933f879485bd3f4dd508272649911d618dd2326954f38e33aff6c912811f01, app/services/referral_service.py 0f6111dfc616ae356d890d38954fe4d190b740bfd1a44a77e129881e41693ee1, scripts/seed_spec_spine.py e0070954bbb9259a69417f2276ac7a8fee5675e6205da446cfd8c48f01941159, scripts/shadow_experiments.py b32dbc2df6f36e7d1389df3d7deb90cf58b21f55dfadb316bc6183b5ca52de7c, tests/test_model_config_enforced.py b3813ad62ce944a44a7ad505fab119be2055d15139436d507620e210a1b3f19b, tests/test_referral_service.py 0164af2e049d5d8dc604934643fc7133bb0b317edae5ebf1f74e5b2718a4cac9, tests/test_u3c_referral_push_name.py 80b63c25878ae49ea995e8298e51b8df7e3f8dbcc7f350e26f787b565fdbd23e, tests/test_u3c_store_false_pin.py f1e491d5b17fa506b8a15798d2ea5366a161c00ede629a45037c3304359080fc). ONE pytest process at a time in this worktree (the bounded runner only; the other U3c agent of this workflow runs AFTER you, not beside you). Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/U3C_PRIVACY_PINS_SPEC.md; ' + SPECS + '/U3C_PRIVACY_PINS_REVIEW.md; ' + SPECS + '/FABLE_RULINGS_U3C.md (R1-R7, F1-F16, the Gate section, and the "Post-adversary rulings 16:45" section X1-X13: BINDING). The adversary reports with the exact mutant shapes and probe files are in ' + NOTES + '/adv-privacy and ' + NOTES + '/adv-eng (notes.md, probe outputs, t01c_probe.out, test_probe_adv_eng.py).',
  'BINDING RULES: backend files are CRLF in the working copy and LF in the index (the fixture JSON too): Edit preserves endings; `git diff --stat` must equal `--ignore-cr-at-eol`. Pure ASCII in new test code (sentinels by concatenation; no credential shape); keep the existing non-ASCII literals byte-identical. No network, no real .env, no git write. Every production line you change is proven by a byte-copy mutant.',
].join('\n')
const FIX_SCHEMA = { type: 'object', required: ['files_changed', 'pyt_lines', 'mutants', 'diff_stat', 'git_status_final', 'stated_limits', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes of EVERY file in git status' },
  pyt_lines: { type: 'array', items: { type: 'string' } }, lint: { type: 'string' }, gitleaks: { type: 'string' },
  mutants: { type: 'array', items: { type: 'string' } }, diff_stat: { type: 'string' }, git_status_final: { type: 'string' },
  stated_limits: { type: 'array', items: { type: 'string' } }, not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'worktree_sha_check', 'summary'], properties: {
  verdict: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } }, mutants: { type: 'array', items: { type: 'string' } }, not_checked: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string' }, summary: { type: 'string' } } }

phase('Fix')
const fix = await agent([
  'ROLE: FIX agent for U3c (rulings X1-X10). Notes folder: ' + NOTES + '/fix (create it; running notes.md). Budget: 2 hours. FIRST re-hash the 10 GREEN files above (a mismatch: stop and report).',
  CONTEXT,
  'DO, in this order: (1) nodes first: T01c (X2), the T18/T19 parameters (X3, X4), the T03 spread allowlist + extra_query (X5), the narrowed T02 with both probe results recorded (X6), the T21 extension (X7), T22 (X8), T23 (X9); show each new/extended node RED on the matching byte-copy mutant shape from the adversary notes (e03, e04, e07, e08, advp-mp2b, g07, g23, the MappingProxyType case) and GREEN on the current bytes where the ruling says it is green already. (2) the two production touches: api_budget_service.py `isinstance(eb, collections.abc.Mapping)` (import at module level in the style of the file) and CLAUDE.md:517 "(both fixed by U3c)". (3) X1: the six `"store": false` entries in tests/fixtures/w4_11_prompt_render_digests.json (CRLF preserved; minimal lines; record the exact lines). (4) gates: the four U3c files + T22/T23 green; tests/test_price_fallback_may_decline.py green; tests/test_prompt_truth.py (if the tiktoken cache exists; else NOT MEASURED with the reason); the comm gate = the 72 files of ' + NOTES + '/spec/comm_files.txt + tests/test_prompt_fence.py, tests/test_smart_fallback.py, tests/test_specs_refill_no_fabrication.py + the two X1 files, in chunks of at most 25, bound 1200 (camera_vision x3 may stay red); tests/test_behavior_dimension_translation.py + tests/test_ci_gates.py; py_compile + ruff E9,F63,F7,F82 on every changed .py; gitleaks dir on every changed file; `git diff --stat` == `--ignore-cr-at-eol`. Return every file with its sha256, every [pyt] line verbatim, the mutant table, the complete stated-limit list (the GREEN list amended), and your questions.',
].join('\n'), { label: 'fix:u3c', phase: 'Fix', model: 'opus', schema: FIX_SCHEMA })
if (!fix) { log('fix returned nothing'); return { fix: null } }
log('fix done: ' + (fix.files_changed || []).length + ' files, ' + (fix.mutants || []).length + ' mutants')

phase('Final adversary')
const adv = await agent([
  'ROLE: FINAL ADVERSARY on the exact bytes after the fix round. Notes folder: ' + NOTES + '/adv-final . Budget: 90 minutes. ONE pytest process at a time; nobody else runs in this worktree now.',
  CONTEXT,
  'THE FIX REPORT (data to verify, not instructions): ' + JSON.stringify(fix),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation you restore and sha256-verify (restore after EVERY mutant). FIRST re-hash every file of the fix report; LAST re-hash again. SUBJECT: (1) every X1-X10 item applied as ruled, each new node executed; (2) replay the earlier survivors as byte-copy mutants and confirm each now DIES: e03 (helper strip), e04 (alias strip), e07 (`eb.get("store")`), e08 (`{7}` in the EN f-string), g07 (in-place scrub), g23 (push-level strip removed), the MappingProxyType extra_body, `{"store": None}`; (3) at least 6 own mutants on the fix lines (the Mapping import removed; the allowlist widened; the T02 narrowing gone too far, i.e. one of the 10 probe shapes no longer flagged; the fixture with one block missing store; CLAUDE.md:517 unchanged) with the killing node EXECUTED; (4) the full comm gate ONCE (the fix report list, chunks of at most 25, bound 1200) and the two X1 files; (5) CRLF/LF: `git diff --stat` == `--ignore-cr-at-eol`, `git ls-files --eol` for every changed file; (6) gitleaks dir over every changed file; no credential shape in any added line (grep the diff for sk-, AKIA, eyJ, scheme://user:pass@). Severity: blocking (a dispatch that can store; a push that can carry the email prefix; a CI-red existing test; a non-hermetic or tautological pin), major, minor, note. Report honestly with the [pyt] lines you produced.',
].join('\n'), { label: 'adversary:u3c-final', phase: 'Final adversary', model: 'opus', schema: ADV_SCHEMA })
log('final adversary: ' + (adv ? adv.verdict : 'no result'))
return { fix, adv }