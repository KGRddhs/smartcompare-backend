export const meta = {
  name: 's74-u3c-red',
  description: 'Session 74 unit U3c RED phase under the synack-build-orchestrator loop: one Opus RED agent writes the two new test files (from the spec drafts amended by the Fable rulings) and the two ruled existing-test edits into worktree sc-s71-t0b, proves every node red at base for its stated reason through the bounded runner, runs gitleaks over the new files, touches no production file. Fable gates afterwards.',
  phases: [ { title: 'RED', detail: 'tests first; red for the right reason at main dfbda511' } ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad'
const RULES = SP + '/s74-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b'
const SPECS = SP + '/s74-state/specs'
const NOTES = SP + '/u3c'
const SCHEMA = { type: 'object', required: ['files_written', 'pyt_lines', 'gitleaks', 'git_status', 'red_reasons', 'summary'], properties: {
  files_written: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" for every file written or edited, final bytes on disk' },
  pyt_lines: { type: 'array', items: { type: 'string' }, description: 'every [pyt] summary line verbatim' },
  gitleaks: { type: 'string', description: 'the gitleaks dir command and its rc / findings over the new files' },
  lint: { type: 'string' },
  git_status: { type: 'string' },
  red_reasons: { type: 'array', items: { type: 'string' }, description: 'per node: red or green at base and the assertion message that proves the reason' },
  not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } },
  summary: { type: 'string' } } }

phase('RED')
const red = await agent([
  'ROLE: RED agent for unit U3c (privacy pins). Notes folder: ' + NOTES + '/red (create it; running notes.md from the first measurement). Budget: 90 minutes from your first tool call.',
  'Worktree ' + WT + ' (branch feature/s74-u3c-privacy-pins = main ' + args.main + ', clean). You MAY write under tests/ of this worktree only; NO production file, NO git command (the orchestrator commits). Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/U3C_PRIVACY_PINS_SPEC.md; ' + SPECS + '/U3C_PRIVACY_PINS_REVIEW.md; ' + SPECS + '/FABLE_RULINGS_U3C.md (BINDING: R1-R6, F1-F16, Q1-Q4). The spec writer drafts: ' + NOTES + '/spec/draft/ (tests/test_u3c_store_false_pin.py and tests/test_u3c_referral_push_name.py). The reviewer probes: ' + NOTES + '/review/ (t01_ext_probe.py, t02_bypass_probe.out, the gitleaks scan outputs): reuse their shapes.',
  'DO: (1) write tests/test_u3c_store_false_pin.py and tests/test_u3c_referral_push_name.py into the worktree from the drafts, amended exactly per the rulings: F1 api_key="test-key"; F2 the attribute rule for T02 (all 10 probe shapes flagged, green at main); F3 the T01 extension (no kwargs.<method>() except .get, no Store/Del of kwargs after the two privacy lines, each dispatch node has no positional args and exactly one **kwargs keyword); R2 a runtime node where extra_body={"store": True} must arrive as False in the captured kwargs AND in the T09 request body, and the T03 denylist extended to store=, extra_body=, user=, safety_identifier=, metadata=, prompt_cache_key=, extra_headers=; F6 the full AR body pinned by code points via chr() (bonus=5) in T15/T16; F8 the T04 dominance rule; F13 T08 dropped; F4 docstrings reworded (no 30-day claim: "sent with store=False so none becomes a stored completion (dashboard Logs); the organisation data-sharing setting is separate and unaffected"). Pure ASCII, LF, no credential-shaped literal (build any sentinel by concatenation). (2) apply the two R6 existing-test edits with the Edit tool, minimal lines, endings preserved (tests/test_referral_service.py:1011-1012; tests/test_model_config_enforced.py:266). (3) run EACH file through the bounded runner (bound 600; tags u3c-store, u3c-referral, u3c-refsvc, u3c-mce) at base: every RED node must fail for its stated reason (quote the assertion message), every GUARD node (T02, T03, T10, T16 and the extended T01 parts that are green-at-main) must pass; a node failing for a setup/import reason is a defect you fix before reporting. (4) gitleaks dir over the two new files with the repo config (cd to the worktree; `gitleaks dir tests/test_u3c_store_false_pin.py --config .gitleaks.toml --no-banner`, same for the other; paste rc). (5) py_compile + ruff (E9,F63,F7,F82) on the four files. (6) `git status --porcelain` and `git diff --stat` (the two edited files must show tiny diffs, no whole-file diff; check `git ls-files --eol` for them first). Return every file with its sha256 and every [pyt] line verbatim.',
].join('\n'), { label: 'red:u3c', phase: 'RED', model: 'opus', schema: SCHEMA })
log('red: ' + (red ? (red.pyt_lines || []).length + ' pyt lines' : 'no result'))
return { red }