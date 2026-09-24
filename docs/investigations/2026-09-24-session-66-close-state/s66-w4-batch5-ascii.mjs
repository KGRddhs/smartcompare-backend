export const meta = {
  name: 's66-w4-batch5',
  description: 'W4 batch 5 on Opus 5.5, TDD per the Synack Build Orchestrator: mode=red writes failing tests from the reviewed specs (FABLE REVIEW RULINGS appended, binding) and stops for the Fable gate; mode=green runs Green -> Adversary -> one Fix round -> re-adversary per unit',
  phases: [
    { title: 'Red', detail: 'failing tests, right-reason failures proven, comm-gate BASE recorded', model: 'claude-opus-5-5' },
    { title: 'Green', detail: 'minimal implementation, every pin mutation-checked, all gates', model: 'claude-opus-5-5' },
    { title: 'Adversary', detail: 'independent attempt to refute', model: 'claude-opus-5-5' },
    { title: 'Fix', detail: 'one fix round for blocking/major defects, then re-adversary', model: 'claude-opus-5-5' },
  ],
}

const MODEL = 'claude-opus-5-5'
const MODE = (args && args.mode) ? String(args.mode) : 'red'
const ONLY = (args && Array.isArray(args.only)) ? args.only : null
const RULINGS = (args && args.rulings && typeof args.rulings === 'object') ? args.rulings : {}
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/a47353ce-a0e3-4273-b85d-f21cfa01e031/scratchpad'

const COMMON = `
ENVIRONMENT AND HARD RULES (violating any of these fails the task):
- Windows 11. Git Bash and PowerShell available. For Python always set PYTHONIOENCODING=utf-8 (cp1252 console; Arabic glyphs may be in test data - never print them, write them to files and read the files).
- Git Bash heredocs mangle backticks, backslashes and backslash-letter sequences. Use the Write/Edit tools for source and test files; never build source with heredocs.
- Backend files: core.autocrlf=true means the working copy is CRLF and the index LF. Edit with the Edit tool (it preserves line endings); if you write programmatically, derive from \`git show HEAD:<path>\` bytes (LF) and write LF. Check \`git diff --stat\` shows only the lines you meant - a whole-file diff is a defect.
- NEVER run git commit, git push, git checkout, git stash, git reset, git rebase, git clean in any existing worktree. You write files only; the orchestrator commits. The ONE allowed git write is creating your own DETACHED scratch worktree for a BASE run (git worktree add --detach <your scratchpad>/<name> <base sha>; copy .env into it; backend-only, no node_modules junction) and removing it afterwards with git worktree remove; confirm removal with git worktree list.
- NEVER use 'git checkout -- <file>' to restore a file: implementations are UNCOMMITTED and checkout erases them. Before every mutation take a byte copy in Python, restore from that copy, sha256-compare, stop on mismatch.
- NEVER touch any directory other than your assigned worktree (plus your own scratchpad). Other agents work concurrently in sc-w4-1 (W4-1, uncommitted, under review), sc-w4-2/3/4/9/10 and sc-w3-* - never write there; read-only \`git -C <dir> diff\` is allowed for composition checks and must be snapshotted and stated.
- NEVER run a recursive delete anywhere. NEVER run _proof/sweep2.py. The proof corpus at C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof is READ-ONLY.
- Do not install packages; do not modify requirements*.txt or lockfiles. Report installed vs pinned versions for anything you measure (local fastapi 0.115.0 / starlette 0.38.6 / pydantic 2.7.0 / supabase 2.28.0 drift from the pins is known - assert on codes and shapes, never message text that the pinned version may format differently).
- Never run tests marked live_db / live_unit / integration, never set LIVE=1, never touch a real database, Railway, Serper, OpenAI or the network (a socket guard in probes is encouraged). NEVER call any Railway MCP tool, and never call list_variables anywhere.
- Test commands: PYTHONIOENCODING=utf-8 python -m pytest <files> -q -p no:cacheprovider -p no:randomly --timeout=120 ; sets add -m "not (live_unit or live_db or integration)". Lint: python -m ruff check --select E9,F63,F7,F82 --no-cache <files> and python -m py_compile <files>.
- The spec file is authoritative, INCLUDING its final "FABLE REVIEW RULINGS (binding, 2026-09-23)" section, which OVERRIDES anything above it where they conflict (scope, design, tests, mutation table, PR text). Read the spec in full ONCE at start and again before reporting. Where the FABLE RED-GATE RULINGS quoted in your prompt (if any) conflict with both, they win.
- Report honestly: paste real summary lines; never claim a state you did not observe. Your final text is the return value (raw data), not prose.

SHARED FACTS: base for every unit is b63a8368 (origin/main is 64afd23b; every commit after b63a8368 is docs-only, so code anchors hold, but the spec's line numbers were measured 2026-09-11 - re-locate every anchor by symbol). W4-1 (ENABLE_SHOPPING_CURRENCY_TRUTH) is UNCOMMITTED in sc-w4-1 and will merge before this batch; its structured_comparison_service.py hunks sit at :~1214 (+5 lines) and :~8227-8290 and its price_service.py hunks in extract_price_from_shopping - expect anchors after :1214 to shift by +5 after the rebase. Phones run the preview channel from 97b5f15 (2026-09-02) via sync REST (ENABLE_EXPO_FETCH_SSE_DEFAULT=false); every backend change must stay compatible with those phones and any result fork sits behind a default-OFF ENABLE_* flag read per call (os.getenv at call time, never memoised). CI required checks: backend-lint, backend-tests, dependency-audit, frontend-tests, frontend-typecheck; backend-tests deselects the node ids in tests/.pre_impl_failures.txt (do not edit that file).
`

const ALL = [
  { key: 'W4-3', dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w4-3', spec: '.qa-w4/W4_3_UNIT_SPEC.md', flag: 'ENABLE_PRESCORING_SHOWABLE_GUARD', pricePath: true,
    extra: 'Backend unit on the compare orchestrator: a pre-scoring showable guard mirroring #113 apply_region_currency_guard, in BOTH twins (compare_from_text and compare_from_text_streaming) plus the guard_rejected harvest in response_builder. Flag default OFF, per call; flag OFF must be byte-identical (the reviewer measured the full-response sha equal). Key files: app/services/structured_comparison_service.py (both twins), app/services/response_builder.py (harvest + the chokepoint append idempotency under the flag), the helper wherever the spec places it. Comm set: the spec\'s grep union (record it in .qa-w4/comm-set-W4-3.txt). The corpus byte-identity harness is BLIND to this unit (ruling R10) - run it once as a formality and say so.' },
  { key: 'W4-4', dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w4-4', spec: '.qa-w4/W4_4_UNIT_SPEC.md', flag: 'ENABLE_HONEST_PARTIAL_SCORING', pricePath: false,
    extra: 'Backend unit on partial responses: ENABLE_HONEST_PARTIAL_SCORING (default OFF, per call) with the stage split of ruling R1 (post-gather => compute_scores on the stash; early-buffer => scoring_v2 null AND overview.winner.reason / key_tradeoff / recommendation blanked) plus the UNFLAGGED metadata.partial_stage (vocabulary gather / post_gather / scoring / verdict, never none). Key files: app/services/response_builder.py (_build_partial_response / build_comparison_response), app/services/structured_comparison_service.py (the partial sites; the streaming path never stashes - document, do not fix). Comm set = the spec\'s grep union + the 10 SmartCompareApp scanners = 204 files with the new file. No corpus byte-identity gate (not a price-path unit); flag-OFF identity is proven by the comm set having identical failure sets in both states.' },
  { key: 'W4-9', dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w4-9', spec: '.qa-w4/W4_9_UNIT_SPEC.md', flag: null, pricePath: false,
    extra: 'UNFLAGGED backend unit: replace str(e) with the INTERNAL_ERROR envelope. Scope per ruling R2: the two orchestrator generic catches (scs sync + stream), extraction_service.parse_product_query\'s catch (+ the parser exits emit `parsed` with only `products`), extraction_service.generate_comparison\'s catch (its error rides SUCCESS payloads, is persisted and publicly shared), and an SSE route floor at text_routes (codeless error payload gets code INTERNAL_ERROR + the constant). Every red test injects failures where the phones\' real request shape reaches them (explicit_pair via _resolve_pair_category; the vision path skips parse_product_query) under a socket guard. Comm set: the spec\'s 189-file set + the new files (.qa-w4/comm-set-W4-9.txt exists - rebuild and compare). Never claim a UI improvement: phones use sync REST and show the axios string before and after.' },
  { key: 'W4-10', dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w4-10', spec: '.qa-w4/W4_10_UNIT_SPEC.md', flag: null, pricePath: false,
    extra: 'UNFLAGGED backend regression fix in app/services/scoring_service.py (compute_dimension_winners label spelling through text_sanitize.dedup_brand_name with str() coercion, ruling R4) PLUS ruling R3 (build_scores_summary reads price_tiers_by_index - the `price tier: unknown` half of the same regression) PLUS ruling R2 (scripts/shadow_experiments.py offline prompt names through the same dedup). price_tiers KEYS stay raw. Comm set: the spec\'s 78-file set (.qa-w4/comm-set-W4-10.txt exists - rebuild and compare) + tests touching shadow_experiments. The PR body leads with the main-path live effect (the gpt-4o verdict prompt\'s Dimension-leaders line changes for every brand-repeating pair).' },
  { key: 'W4-2', dir: 'C:/Users/SynAckITPC/Documents/AI/sc-w4-2', spec: '.qa-w4/W4_2_UNIT_SPEC.md', flag: 'ENABLE_SHOPPING_DISCOVERY_URL_SPLIT', pricePath: true,
    extra: 'PRICE-PATH backend unit, launched ONLY after W4-1 has merged and this worktree has been rebased onto it (verify: shopping_currency_truth_enabled must exist in app/services/price_service.py at HEAD; if it does not, STOP and report). Flag coupled to W4-1 in code (ruling R1), the tier-7 backfill guard is the load-bearing edit and the Tier-1 park edit is DROPPED (R2), tests 8/9 drive the real _get_price on the existing harness (R3), the key is _discovery_url (R4). Comm set: the spec\'s grep (price_service|structured_comparison_service|source_router|exchange_rate_service) recorded in .qa-w4/comm-set-W4-2.txt. Byte-identity gate per the spec with the honest scope sentence (the harness never enters the shopping rung).' },
]
const UNITS = ALL.filter((u) => (!ONLY || ONLY.includes(u.key)))

const RED_SCHEMA = {
  type: 'object',
  required: ['unit', 'test_files_written', 'failing_count', 'failures_are_right_reason', 'failure_evidence', 'comm_base', 'measurements_run', 'spec_disagreements'],
  properties: {
    unit: { type: 'string' },
    test_files_written: { type: 'array', items: { type: 'string' } },
    failing_count: { type: 'integer' },
    failures_are_right_reason: { type: 'boolean' },
    failure_evidence: { type: 'string', description: 'verbatim summary lines + one sentence per failing test naming the genuine absent behaviour' },
    comm_base: { type: 'string', description: 'the comm-gate BASE run: set size, command shape, sorted FAILED ids file, and that every failure is in tests/.pre_impl_failures.txt' },
    measurements_run: { type: 'array', items: { type: 'string' } },
    spec_disagreements: { type: 'array', items: { type: 'string' }, description: 'spec or ruling claims found WRONG when tested, with evidence; empty if none' },
  },
}
const GREEN_SCHEMA = {
  type: 'object',
  required: ['unit', 'files_changed', 'all_unit_tests_pass', 'test_evidence', 'lint_clean', 'mutation_checks', 'comm_gate', 'byte_identity', 'measurements_run', 'pr_text', 'deviations_from_spec', 'git_status_final', 'residual_risk'],
  properties: {
    unit: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    all_unit_tests_pass: { type: 'boolean', description: 'unit file green in every flag state the spec names' },
    test_evidence: { type: 'string' },
    lint_clean: { type: 'boolean' },
    mutation_checks: { type: 'array', items: { type: 'string' }, description: 'one per key test and per mutation-table row: what changed, the observed red count and node names, restored from a byte snapshot with matching sha256' },
    comm_gate: { type: 'string', description: 'HEAD run over the recorded set + the unit file; comm -13 base head; anything not in tests/.pre_impl_failures.txt explained' },
    byte_identity: { type: 'string', description: 'price-path units: base -> head -> base2 record-by-record with the honest scope; others: the flag-OFF proof used' },
    measurements_run: { type: 'array', items: { type: 'string' } },
    pr_text: { type: 'string', description: 'Ready-to-paste PR body: defect, design, flag row (default, effect ON, composition, activation order), KPI/canary lines, honest limits, follow-ups, gates - every disclosure the rulings require' },
    deviations_from_spec: { type: 'array', items: { type: 'string' } },
    git_status_final: { type: 'string' },
    residual_risk: { type: 'string' },
  },
}
const ADV_SCHEMA = {
  type: 'object',
  required: ['unit', 'verdict', 'defects', 'tests_that_prove_nothing', 'worktree_left_byte_identical', 'summary'],
  properties: {
    unit: { type: 'string' },
    verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] },
    defects: { type: 'array', items: { type: 'object', required: ['severity', 'location', 'claim', 'why_it_matters', 'reproduced'], properties: {
      severity: { type: 'string', enum: ['blocking', 'major', 'minor'] }, location: { type: 'string' }, claim: { type: 'string' }, why_it_matters: { type: 'string' }, reproduced: { type: 'boolean' } } } },
    tests_that_prove_nothing: { type: 'array', items: { type: 'string' } },
    worktree_left_byte_identical: { type: 'boolean' },
    summary: { type: 'string' },
  },
}

const redPrompt = (u) => `You are implementing the RED (failing-test) phase of unit ${u.key} (myez/Qaren backend, FastAPI, Python 3.12).
Worktree: ${u.dir}
Spec: ${u.dir}/${u.spec} - read it FIRST and in full. Its LAST section, "FABLE REVIEW RULINGS (binding, 2026-09-23)", was written by the orchestrator after an adversarial review and OVERRIDES the body where they conflict.
${u.extra}

STATE: this worktree is CLEAN at b63a8368 (spec only, nothing started). Run \`git status --short\` FIRST and confirm; if it is not clean, stop and report what is there.
YOUR TASK - tests only, no implementation:
1. Read the spec and the rulings completely, then the current source at every anchor they name (re-locate by symbol; quote the code).
2. Run every measurement the spec or the rulings ask for in the red phase; record each with observed output.
3. Write the tests the spec's Red tests section specifies AS AMENDED by the rulings (added pins, rewritten tests, dropped tests, discriminating fixtures, both-flag-state parametrisations). Include the Preserve pins (they pass today - say so, and label each as a pin).
4. Run them. The red ones MUST fail for the RIGHT reason: read each failure and say why it is the genuine absence of the behaviour, not an import/path/mock/fixture mistake. A test that is red only by ImportError must be written so that a stub implementation still reddens it on an assertion (prove it with a stub in YOUR scratchpad, never in the worktree).
5. Comm gate BASE now (this worktree IS the base): build the set exactly as the spec/rulings define it, record it in ${u.dir}/.qa-w4/comm-set-${u.key}.txt, run with the standing shape, save sorted FAILED ids to .qa-w4/comm-base-${u.key}.txt, and confirm every failure is in tests/.pre_impl_failures.txt.
6. If any part of the spec OR the rulings is WRONG when tested, record it in spec_disagreements with evidence. Do not work around it silently.
Write NO implementation: nothing under app/ or scripts/ except test files under tests/. The orchestrator (Fable) reviews your tests before any green phase starts.
${COMMON}`

const greenPrompt = (u) => `You are implementing the GREEN phase of unit ${u.key} (myez/Qaren backend). Worktree: ${u.dir}. Spec: ${u.dir}/${u.spec} - its LAST section "FABLE REVIEW RULINGS (binding, 2026-09-23)" overrides the body.
The RED phase report (tests, failing counts, measurements, comm-gate base, spec disagreements) is at ${MYSP}/w4_red_${u.key}.json - READ IT IN FULL FIRST.
${RULINGS[u.key] ? 'FABLE RED-GATE RULINGS for this unit (binding; they override the spec AND the review rulings where they conflict):\n' + RULINGS[u.key] : 'Fable reviewed the red report and issued no rulings beyond the spec and its appended review rulings: follow them and the red report\'s resolutions of its own disagreements.'}
${u.extra}

STATE ON DISK: the red phase left ONLY its test files (plus .qa-w4/ artefacts). Run \`git status --short\` and \`git diff --stat\` FIRST and confirm; if anything else is present, stop and report.
YOUR TASK:
1. Implement EXACTLY the spec's design as amended by the rulings - minimal, no refactors, nothing on the must-NOT-touch list except where a ruling explicitly overrides it. ${u.flag ? 'Every new branch sits under a per-call reader of ' + u.flag + ' (default OFF); flag OFF executes the exact b63a8368 code paths.' : 'This unit is unflagged by ruling; keep the change minimal and additive.'}
2. Run the unit file to green ${u.flag ? 'with the flag unset AND with ' + u.flag + '=true' : ''}; paste the summary lines. Run every Preserve file the spec names.
3. MUTATION-CHECK every key test and every mutation-table row (as amended) from byte snapshots with sha256-verified restores; record counts and node names. A test that survives removal of its fix must be rewritten.
4. Lint + py_compile on every edited module.
5. Comm gate HEAD over the recorded set plus the unit file; comm -13 base head must be empty; explain anything not in tests/.pre_impl_failures.txt.
6. ${u.pricePath ? 'Byte-identity gate: scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof --flags ' + u.flag + ', base -> head -> base2 from your own detached scratch worktree at the merge-base, results arrays compared record-by-record (never the OVERALL digest); remove the scratch worktree afterwards; state the honest scope the rulings give.' : 'Flag-OFF / no-flag proof: the comm set shows identical failure sets before and after; state it.'}
7. Write pr_text with every disclosure the rulings require (flag row, composition, activation order, KPI/canary lines, honest limits, follow-ups with their PO-* ids, the 97b5f15 client anchors).
8. Leave the worktree with ONLY the intended files modified; never commit. Report git status --short verbatim in git_status_final.
${COMMON}`

const advPrompt = (u, green, round) => `You are an ADVERSARIAL reviewer for unit ${u.key}. Your job is to REFUTE the work, not to bless it. Worktree: ${u.dir}. Spec (its LAST section "FABLE REVIEW RULINGS (binding, 2026-09-23)" overrides the body): ${u.dir}/${u.spec}. Red report: ${MYSP}/w4_red_${u.key}.json${RULINGS[u.key] ? '. Fable red-gate rulings (binding):\n' + RULINGS[u.key] : '.'}
${round > 0 ? 'RE-REVIEW ROUND ' + round + ': a fixer addressed your blocking/major defects. Verify each is closed (re-run the mutation), then look again at everything the fix touched.' : ''}
The implementer reported:
${JSON.stringify(green, null, 1)}
${u.extra}

Assume the implementation is wrong until checked.
1. Read the actual diff (git diff; git status for new files). Review the code, not the description. Check the must-NOT-touch list line by line against the rulings' explicit overrides; ${u.flag ? 'verify every new statement sits under the per-call flag read and that flag OFF is the exact b63a8368 path;' : 'verify the change is minimal and additive;'} verify CRLF hygiene (no whole-file diffs).
2. Re-run the reported mutation checks yourself from byte snapshots (never git checkout); try mutations the implementer did not; anything that survives removal of its fix goes in tests_that_prove_nothing. Leave the worktree byte-identical (sha256 before/after; report worktree_left_byte_identical honestly).
3. Re-measure every ruling item through the REAL functions (not the description): the composition cases the rulings name, the 97b5f15 client anchors, the persisted/shared payloads, the KPI/canary claims.
4. Unhappy paths in every flag state the spec names; the standing failure modes (a result fork without a flag; a snapshot silently updated; a mock that makes an assertion vacuous; a swallowed exception reported as success; a number two documents disagree on; a full-set regression explained away).
5. Verify the comm-gate claim (re-run the unit file, the Preserve files and a SAMPLE of the set) and ${u.pricePath ? 'the byte-identity claim (read the gate JSONs and compare the results arrays yourself).' : 'the flag-OFF/no-flag identity claim.'}
6. Report a defect as reproduced:true only if you ran something that demonstrated it. Do not pad. If sound, say SOUND.
Do not fix anything. Report only.
${COMMON}`

const fixPrompt = (u, adv) => `You are the FIXER for unit ${u.key} in worktree ${u.dir}. The adversary found blocking/major defects. For each: re-derive it from code; if real, fix it MINIMALLY inside the spec's design as amended by the rulings (${u.dir}/${u.spec}, last section binding${RULINGS[u.key] ? '; Fable red-gate rulings:\n' + RULINGS[u.key] : ''}), add or adjust a load-bearing pin (mutation-checked from a byte snapshot), re-run the unit file in every flag state, the Preserve files, ruff + py_compile, the comm gate HEAD run (comm -13 empty)${u.pricePath ? ' and the byte-identity chain' : ''}. If you believe a defect is WRONG, do not fix it - dispute it in deviations_from_spec with the measurement. Fold every entry of tests_that_prove_nothing into a real pin or explain why it is a deliberate pin. Update pr_text. Never commit.
Defects:
${JSON.stringify(adv.defects, null, 1)}
tests_that_prove_nothing:
${JSON.stringify(adv.tests_that_prove_nothing, null, 1)}
${u.extra}
${COMMON}`

log('W4 batch 5 mode=' + MODE + ': ' + UNITS.map((u) => u.key).join(', '))

if (MODE === 'red') {
  const reds = await parallel(UNITS.map((u) => () => agent(redPrompt(u), { label: 'red:' + u.key, phase: 'Red', model: MODEL, effort: 'high', schema: RED_SCHEMA })))
  const out = UNITS.map((u, i) => ({ unit: u.key, red: reds[i] }))
  log('reds: ' + out.map((r) => r.unit + '=' + (r.red ? r.red.failing_count + ' failing' : 'died')).join(', '))
  return { mode: 'red', results: out }
}

const results = await pipeline(
  UNITS,
  (u) => agent(greenPrompt(u), { label: 'green:' + u.key, phase: 'Green', model: MODEL, effort: 'high', schema: GREEN_SCHEMA }),
  async (green, u) => {
    if (!green) return { unit: u.key, green: null, final_verdict: 'green died' }
    const serious = (a) => a ? a.defects.filter((d) => d.severity !== 'minor') : []
    const adv = await agent(advPrompt(u, green, 0), { label: 'adversary:' + u.key, phase: 'Adversary', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
    if (adv && (serious(adv).length || adv.tests_that_prove_nothing.length)) {
      const fix = await agent(fixPrompt(u, adv), { label: 'fix:' + u.key, phase: 'Fix', model: MODEL, effort: 'high', schema: GREEN_SCHEMA })
      const adv2 = await agent(advPrompt(u, fix || green, 1), { label: 'adversary:' + u.key + '-r1', phase: 'Fix', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
      return { unit: u.key, green, adversary_r0: adv, fix, adversary_r1: adv2, final_verdict: adv2 ? adv2.verdict : 'agent died' }
    }
    return { unit: u.key, green, adversary_r0: adv, fix: null, adversary_r1: null, final_verdict: adv ? adv.verdict : 'agent died' }
  }
)
const done = results.filter(Boolean)
log('W4 batch 5 green: ' + done.map((r) => r.unit + '=' + r.final_verdict).join(', '))
return { mode: 'green', results: done }
