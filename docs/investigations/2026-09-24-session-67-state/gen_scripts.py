"""Generate the session-67 workflow scripts from the session-66 ones (splicing the
GROUPS/COMMON/schema blocks verbatim so no scope text is re-typed), then syntax-check
each by wrapping it in an async body (node --check alone rejects the top-level return)."""
import pathlib, subprocess, sys

SP = pathlib.Path("C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/75660a55-e14a-4de1-80dc-a537f2af315e/scratchpad")
ST = pathlib.Path("C:/Users/SynAckITPC/Documents/AI/sc-docs-66/docs/investigations/2026-09-24-session-66-close-state")
MYSP = SP.as_posix()

old = (ST / "s66-retro-fix-ascii.mjs").read_text(encoding="utf-8")
common = old[old.index("const COMMON = `"): old.index("const GROUPS = [")]
common = common.replace(
    "Base = origin/main 1c6f6796 (your worktree was created from it today).",
    "Base = 1c6f6796 (every retro branch was cut from it; origin/main has since moved to d70dd876 - do NOT rebase, the orchestrator does that after SOUND).",
)
assert "d70dd876" in common
# lesson from the close: every report that writes files carries their final sha256
common = common.rstrip("`\n") + "\n- Every report that writes or edits a file MUST carry the final sha256 of every file written (the close of session 66 could only restore R-BREAKER's mutant because its green recorded them). NEVER import app.* before tests/conftest.py has run and never run pytest without a process-wide non-loopback socket guard (rule 9 of the R-W0 rulings; the R-W0 harness incident loaded real .env keys into module-level clients).`\n"
groups = old[old.index("const GROUPS = ["): old.index("const UNITS = GROUPS")]
schemas = old[old.index("const RED_SCHEMA"): old.index("const redPrompt")]
old_red_task = old[old.index("YOUR TASK - tests only"): old.index("The orchestrator (Fable) gates before any green.")]
old_green_task = old[old.index("Implement the MINIMAL change per defect"): old.index("report git status --short verbatim.")] + "report git status --short verbatim."

retro = r'''export const meta = {
  name: 's67-retro-resume',
  description: 'Session 67 resume of the retro-fix wave on Opus 5.5: mode=adversary re-reviews the six finished greens (committed as UNVERIFIED wip) with a fresh adversary -> one fix round -> re-adversary, at most 3 groups concurrently; mode=green resumes the two killed greens (R-AUTH, R-MAIN) from their partial wip commits then adversary/fix/re-adversary; mode=red resumes the killed R-W04 red and stops for the Fable gate',
  phases: [
    { title: 'Red', detail: 'R-W04 red resume', model: 'claude-opus-5-5' },
    { title: 'Green', detail: 'R-AUTH / R-MAIN green resume from the partial wip', model: 'claude-opus-5-5' },
    { title: 'Adversary', detail: 'fresh independent refutation on the exact committed bytes', model: 'claude-opus-5-5' },
    { title: 'Fix', detail: 'one fix round, re-adversary', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const MODE = (args && args.mode) ? String(args.mode) : 'adversary'
const ONLY = (args && Array.isArray(args.only)) ? args.only : null
const LIMIT = (args && args.limit) ? Number(args.limit) : 3
const MYSP = '__MYSP__'
const VENV = 'C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe'
const RETRO = MYSP + '/retro_adversary_results.json'

__COMMON__
__GROUPS__
const STATE = {
  'R-METER':   { branch: 'retro/w2-1-metering',        wip: 'd43f9bdb', unitFiles: 'tests/test_retro_w2_1.py tests/test_paid_route_metering.py', closeCount: '107 passed (04:57)', commNote: 'the green ran NO comm gate (a recorded gap): run the HEAD comm gate over the 17-file grep set the red phase recorded in .qa-retro/ and compare against its recorded base FAILED ids; a base run needs your own detached scratch worktree of 1c6f6796' },
  'R-BREAKER': { branch: 'retro/w1-3-breaker',         wip: '7a7dfc24', unitFiles: 'tests/test_retro_w1_3.py tests/test_openai_breaker.py', closeCount: '71 passed (after the green bytes of api_budget_service.py, sha256 c26a60ba, were restored over a killed adversary\'s mutant; the mutant commit 38e8808f sits below the restore commit 7a7dfc24 - review HEAD only)', commNote: 'green recorded comm 16-file set 322/0 at base, head equal' },
  'R-CLIENT':  { branch: 'retro/w1-4-client-logout',   wip: '26b6b100', unitFiles: 'SmartCompareApp/__tests__/authService.logoutRefreshFirst.w1-4d.test.ts SmartCompareApp/__tests__/authService.logoutRevoke.w1-4.test.ts SmartCompareApp/__tests__/authService.bootOptimistic.a3.test.ts (jest by path from SmartCompareApp: node node_modules/jest/bin/jest.js --ci <files>) plus node node_modules/typescript/bin/tsc --noEmit', closeCount: '56/56 across the 3 suites + tsc OK (05:08)', commNote: 'green recorded 68 suites / 712 tests 0 failed but the FULL jest suite was NEVER run: run it ONCE on HEAD from SmartCompareApp with --maxWorkers=25% (never -u), report suites/tests/snapshots, and explain every failing suite (judge whether the unit\'s files are involved; the orchestrator re-runs it after the rebase)' },
  'R-MIG':     { branch: 'retro/w1-2-migration-037',   wip: '66496835', unitFiles: 'tests/test_retro_w1_2b.py tests/test_retro_w1_2c.py tests/test_retro_w1_2d.py tests/test_migration_037_security_definer_grants.py tests/test_migration_index_predicate_immutability.py', closeCount: '96 passed, 4 deselected (05:00)', commNote: 'green recorded comm 25-file set 512/0; migration numbers are binding (038 = W3-16 merged, 039 reserved for the M13-29 RLS migration, 040 = the cleanup_expired_ratings revoke); a LOCAL throwaway PostgreSQL may be used only if one is already installed on this box - report which, else reason from the SQL' },
  'R-W18':     { branch: 'retro/w1-8-adapter-drop',    wip: 'e1d7be86', unitFiles: 'tests/test_retro_w1_8.py tests/test_adapter_drop_visibility.py', closeCount: '33 passed (05:02); structured_comparison_service.py sha256 b2b9bf06 == the green\'s recorded sha', commNote: 'green recorded comm 152-file set with 2 failed = the base\'s 2' },
  'R-W0':      { branch: 'retro/w0-1-w0-2',            wip: 'da16bada', unitFiles: 'the guarded runner unit set: .qa-retro/run_pytest.py over tests/test_retro_w0_1.py tests/test_retro_w0_2.py tests/test_url_validator_offloop.py tests/test_url_validator_offloop_hops.py (+ the database_service reuse files the runner lists)', closeCount: '59 passed + 46 passed in the two runner sets (05:03)', commNote: 'green recorded the 35-file comm set through the SAME guarded runner .qa-retro/run_pytest.py with exactly the 5 accepted base failures (3 example.com SSRF nodes + test_live_opt_in_restores_the_environment_end_to_end + the deselected test_app_main_still_imports_under_the_sentinels); NEVER run pytest here without that runner' },
  'R-AUTH':    { branch: 'retro/w1-4-w1-9-auth',       wip: 'f8481f62', redFiles: 'tests/test_retro_w1_4_logout_expired.py tests/test_retro_w1_4_server.py tests/test_retro_w1_9_429.py (+ the red-phase edits to tests/test_auth_refresh_and_revocation.py and tests/test_supabase_client_reuse.py)', partial: 'app/api/auth_routes.py and app/services/auth_service.py carry a PARTIAL green (killed mid-implementation, 4 files changed, 422 insertions / 84 deletions at the kill)' },
  'R-MAIN':    { branch: 'retro/w1-1-w1-7-w1-9-main',  wip: 'b519f9de', redFiles: 'tests/test_retro_w1_1.py tests/test_retro_w1_7_w1_10.py tests/test_retro_w1_9.py', partial: 'app/main.py and app/services/sentry_service.py carry a PARTIAL green (killed mid-implementation, 109 insertions / 43 deletions at the kill)' },
  'R-W04':     { branch: 'retro/w0-4-parse-offload',   wip: 'faeb5c2d', redFiles: 'tests/test_retro_w0_4.py (PARTIAL - the red agent was killed mid-run; nothing is gated)' },
}
const UNITS = GROUPS.filter((g) => !ONLY || ONLY.includes(g.key))

__SCHEMAS__
const limiter = (n) => {
  let active = 0
  const q = []
  const next = () => {
    if (active >= n || !q.length) return
    active++
    const { fn, res, rej } = q.shift()
    fn().then(res, rej).finally(() => { active--; next() })
  }
  return (fn) => new Promise((res, rej) => { q.push({ fn, res, rej }); next() })
}
const run = limiter(LIMIT)

const advPrompt = (g, round, fixReport) => {
  const s = STATE[g.key]
  const first = g.key === 'R-METER'
    ? 'A first adversary round already ran on an EARLIER state of this worktree and returned SOUND with five minors and eight prove-nothing rows (' + MYSP + '/retro_adv_r0_R-METER.json - READ IT IN FULL); a fix round then edited the worktree and was KILLED before it could report, so the wip commit holds the green PLUS an unreported partial fix. Treat this as RE-REVIEW ROUND 1 of that report: verify each minor and each prove-nothing row is closed or still open (re-run the mutation), then review the WHOLE diff again as if new.'
    : 'A previous adversary for this group was KILLED mid-run before reporting; nothing from it survives - this is round 0. KNOWN HAZARD: killed adversaries left in-place MUTATIONS on disk three times in session 66 (W4-3, W4-9, R-BREAKER); the wip commit was re-verified at the close (unit files re-run, count below) but you re-run them FIRST and compare.'
  return `You are an ADVERSARIAL reviewer for retro-fix group ${g.key} (units: ${g.units.join(', ')}) in worktree ${g.dir}. Your job is to REFUTE the work, not to bless it.
STATE: the green phase finished and its work is COMMITTED on branch ${s.branch} as an UNVERIFIED wip commit ${s.wip} above base 1c6f6796; the worktree must be CLEAN (run git status --short FIRST; if anything is present, stop and report it). The unit diff = git diff 1c6f6796..HEAD (name-status first, then the hunks).
${round > 0 ? 'RE-REVIEW ROUND ' + round + ': a fixer addressed your blocking/major defects and prove-nothing rows; its report is below. Verify each is closed (re-run the mutation), then look again at everything the fix touched. The fixer\'s edits are UNCOMMITTED on top of the wip commit (git diff HEAD shows exactly them).\nFIX REPORT:\n' + JSON.stringify(fixReport, null, 1) : first}
INPUTS (read all in full before touching anything): the reviewer reports = ${RETRO} (entries whose "unit" starts with this group's unit keys); the red report = ${MYSP}/retro_red_${g.key}.json; the implementer's GREEN report = ${MYSP}/retro_green_${g.key}.json; the FABLE RED-GATE RULINGS (binding, they override the scope where they conflict) = ${MYSP}/retro_rulings_${g.key}.txt. SCOPE AND RULINGS: ${g.scope}
FIRST: re-run the unit files (${s.unitFiles}) on the venv; the close re-run recorded ${s.closeCount}. If your count differs, diagnose that before anything else - a mutant on disk is a BLOCKING defect (name the line and the sha).
THEN, assuming the implementation is wrong until checked: (1) read the whole diff hunk by hunk against the rulings and the red report; every new statement that forks a result must sit under its named per-call flag read, or be proven additive/byte-identical by a pin; CRLF hygiene (no whole-file diffs). (2) Re-run every mutation the green reported from byte snapshots (never git checkout; sha256-verified restores) and try mutations it did not; anything that survives removal of its fix goes in tests_that_prove_nothing. (3) Drive the unhappy paths the original reviewer named and new ones through the REAL functions on the venv. (4) Verify flag-OFF identity / unflagged additivity through the real functions. (5) Comm gate: ${s.commNote}. (6) Leave the worktree byte-identical: git status --short empty and git diff --stat empty at the end; report worktree_left_byte_identical honestly. (7) In summary, list the sha256 of every file in the diff as you found it at the start. reproduced:true only if you ran it. Do not fix anything. If sound, say SOUND.
${COMMON}`
}

const fixPrompt = (g, adv) => {
  const s = STATE[g.key]
  return `You are the FIXER for retro-fix group ${g.key} in worktree ${g.dir} (branch ${s.branch}, green committed as wip ${s.wip} above 1c6f6796; the worktree is clean at start - confirm). Inputs: reviewer reports ${RETRO}; red report ${MYSP}/retro_red_${g.key}.json; green report ${MYSP}/retro_green_${g.key}.json; FABLE RED-GATE RULINGS (binding) ${MYSP}/retro_rulings_${g.key}.txt; scope/rulings: ${g.scope}
The adversary found the defects and prove-nothing rows below. For each defect: re-derive it from code; if real, fix it MINIMALLY inside the scoped design with a load-bearing pin mutation-checked from a byte snapshot; if you believe it is WRONG, do not fix it - dispute it in deviations_from_spec with a measurement. Fold every tests_that_prove_nothing row into a real pin or explain why it is a deliberate pin. Re-run the unit files (${s.unitFiles}) in every flag state, ruff + py_compile (or tsc + eslint by path for the client unit), the comm gate HEAD (${s.commNote}); update pr_text; never commit; leave only intended changes (uncommitted, on top of the wip commit); report git status --short verbatim and the final sha256 of every file you wrote.
Defects:
${JSON.stringify(adv.defects, null, 1)}
tests_that_prove_nothing:
${JSON.stringify(adv.tests_that_prove_nothing, null, 1)}
${COMMON}`
}

const greenResumePrompt = (g) => {
  const s = STATE[g.key]
  return `You are implementing the GREEN phase of retro-fix group ${g.key} (units: ${g.units.join(', ')}) in worktree ${g.dir}.
STATE: a previous green agent was KILLED mid-implementation. Its PARTIAL, UNVERIFIED work is committed as wip ${s.wip} on branch ${s.branch} above base 1c6f6796 (the worktree is clean - confirm with git status --short FIRST). ${s.partial}. The red phase's GATED test files are in that commit too: ${s.redFiles}.
INPUTS (read in full first): the RED report ${MYSP}/retro_red_${g.key}.json; the reviewer reports ${RETRO}; the FABLE RED-GATE RULINGS (binding; they override the scope where they conflict) ${MYSP}/retro_rulings_${g.key}.txt. SCOPE AND RULINGS: ${g.scope}
YOUR TASK: (1) AUDIT the partial first: git diff 1c6f6796..HEAD -- app/ hunk by hunk against the rulings; run the red files and record what is green/red now; decide per hunk KEEP (it matches the rulings and a red test proves it) or REPLACE (rewrite it minimally). To restore a file to its base bytes write the output of git show 1c6f6796:<path> with the Write tool (LF -> the working copy is CRLF, so compare with git diff, not by bytes) - NEVER git checkout --, never git reset. Record the audit verdict per hunk in deviations_from_spec. (2) Then finish the green exactly as scoped: ${old_green_task} (3) Your report MUST carry the final sha256 of every file you wrote.
${COMMON}`
}

const redResumePrompt = (g) => {
  const s = STATE[g.key]
  return `You are implementing the RED (failing-test) phase of retro-fix group ${g.key} (units: ${g.units.join(', ')}) in worktree ${g.dir}.
STATE: a previous red agent was KILLED mid-run. Its PARTIAL test file is committed as wip ${s.wip} on branch ${s.branch} above base 1c6f6796: ${s.redFiles}. Nothing is gated. The worktree is clean - confirm with git status --short FIRST. app/ and scripts/ are at base bytes (verify: git diff 1c6f6796..HEAD --stat must list only the test file).
SPEC: the retroactive adversary reports in ${RETRO} for these units - read every defect, its why_it_matters, its proposed_fix_unit and the tests_that_prove_nothing list in full. SCOPE AND RULINGS (binding): ${g.scope}
YOUR TASK - audit the partial file first (which reds exist, which fail for the RIGHT reason on the venv, which are vacuous), keep what is right and finish it; then: ${old_red_task}The orchestrator (Fable) gates before any green. Your report MUST carry the final sha256 of every file you wrote.
${COMMON}`
}

const serious = (a) => a ? a.defects.filter((d) => d.severity !== 'minor') : []

const reviewChain = async (g, round0) => {
  const adv = await run(() => agent(advPrompt(g, round0, null), { label: 'adversary:' + g.key, phase: 'Adversary', model: MODEL, effort: 'high', schema: ADV_SCHEMA }))
  if (!adv) return { group: g.key, adversary_r0: null, fix: null, adversary_r1: null, final_verdict: 'adversary died' }
  if (serious(adv).length || adv.tests_that_prove_nothing.length) {
    const fix = await run(() => agent(fixPrompt(g, adv), { label: 'fix:' + g.key, phase: 'Fix', model: MODEL, effort: 'high', schema: GREEN_SCHEMA }))
    const adv2 = await run(() => agent(advPrompt(g, round0 + 1, fix), { label: 'adversary:' + g.key + '-r1', phase: 'Fix', model: MODEL, effort: 'high', schema: ADV_SCHEMA }))
    return { group: g.key, adversary_r0: adv, fix, adversary_r1: adv2, final_verdict: adv2 ? adv2.verdict : 'agent died' }
  }
  return { group: g.key, adversary_r0: adv, fix: null, adversary_r1: null, final_verdict: adv.verdict }
}

log('retro-resume mode=' + MODE + ' limit=' + LIMIT + ': ' + UNITS.map((g) => g.key).join(', '))

if (MODE === 'red') {
  const reds = await parallel(UNITS.map((g) => () => run(() => agent(redResumePrompt(g), { label: 'red:' + g.key, phase: 'Red', model: MODEL, effort: 'high', schema: RED_SCHEMA }))))
  const out = UNITS.map((g, i) => ({ group: g.key, red: reds[i] }))
  log('reds: ' + out.map((r) => r.group + '=' + (r.red ? r.red.failing_count + ' failing' : 'died')).join(', '))
  return { mode: 'red', results: out }
}

if (MODE === 'green') {
  const results = await pipeline(
    UNITS,
    (g) => run(() => agent(greenResumePrompt(g), { label: 'green:' + g.key, phase: 'Green', model: MODEL, effort: 'high', schema: GREEN_SCHEMA })),
    async (green, g) => {
      if (!green) return { group: g.key, green: null, final_verdict: 'green died' }
      const r = await reviewChain(g, 0)
      return Object.assign({ green }, r)
    }
  )
  const done = results.filter(Boolean)
  log('retro-resume green: ' + done.map((r) => r.group + '=' + r.final_verdict).join(', '))
  return { mode: 'green', results: done }
}

const results = await parallel(UNITS.map((g) => () => reviewChain(g, g.key === 'R-METER' ? 1 : 0)))
const done = results.filter(Boolean)
log('retro-resume adversary: ' + done.map((r) => r.group + '=' + r.final_verdict).join(', '))
return { mode: 'adversary', results: done }
'''
retro = retro.replace('__MYSP__', MYSP).replace('__COMMON__', common).replace('__GROUPS__', groups).replace('__SCHEMAS__', schemas)
retro = retro.replace('${old_green_task}', old_green_task.replace('`', "'").replace('${', '$ {')).replace('${old_red_task}', old_red_task.replace('`', "'").replace('${', '$ {'))
(SP / "s67-retro-resume.mjs").write_text(retro, encoding="ascii", errors="strict")

# ---------------- W4-2 green ----------------
w4 = (ST / "s66-w4-batch5-ascii.mjs").read_text(encoding="utf-8")
w4common = w4[w4.index("const COMMON = `"): w4.index("const ALL = [")]
w4common = w4common.replace(
    "SHARED FACTS: base for every unit is b63a8368 (origin/main is 64afd23b; every commit after b63a8368 is docs-only, so code anchors hold, but the spec's line numbers were measured 2026-09-11 - re-locate every anchor by symbol). W4-1 (ENABLE_SHOPPING_CURRENCY_TRUTH) is UNCOMMITTED in sc-w4-1 and will merge before this batch; its structured_comparison_service.py hunks sit at :~1214 (+5 lines) and :~8227-8290 and its price_service.py hunks in extract_price_from_shopping - expect anchors after :1214 to shift by +5 after the rebase.",
    "SHARED FACTS: base for W4-2 is 6ab9d7ea (= W4-1 ENABLE_SHOPPING_CURRENCY_TRUTH MERGED as #173; shopping_currency_truth_enabled exists in app/services/price_service.py at HEAD - verify, STOP if not). origin/main has since moved to d70dd876 (W3-14 auth copy, W4-10 scoring_service dedup, W3-11bcd client Arabic pack, docs) - none of those touch the shopping rung; do NOT rebase, the orchestrator does. The spec's line numbers were measured 2026-09-11 - re-locate every anchor by symbol. W4-3 (#177, prescoring showable guard in structured_comparison_service.py + price_service.py) and W4-4/W4-9 are OPEN PRs being merged concurrently - keep your hunks function-local.",
)
assert "6ab9d7ea" in w4common
w4common = w4common.replace(
    "Other agents work concurrently in sc-w4-1 (W4-1, uncommitted, under review), sc-w4-2/3/4/9/10 and sc-w3-* - never write there;",
    "Other agents work concurrently in sc-w4-3/4/9, sc-pr36/44 and the sc-r-* worktrees - never write there;",
)
w4common = w4common.replace(
    "- Test commands: PYTHONIOENCODING=utf-8 python -m pytest",
    "- ALWAYS use the pinned venv C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe (fastapi 0.141.1 / starlette 1.6.0 / pydantic 2.13.4 / supabase 2.31.0 / httpx 0.28.1 / pytest 9.1.1 = the CI pins), never the global python.\n- Test commands: PYTHONIOENCODING=utf-8 <venv python> -m pytest",
)
w4common = w4common.rstrip("`\n") + "\n- Your report MUST carry the final sha256 of every file you wrote. NEVER import app.* before tests/conftest.py has run and never run pytest without a process-wide non-loopback socket guard (use .qa-w4/comm_tools/run_comm.py for the comm sets).`\n"
w4schemas = w4[w4.index("const RED_SCHEMA"): w4.index("const redPrompt")]
w4entry = w4[w4.index("  { key: 'W4-2'"): w4.index("]\nconst UNITS = ALL")]
w4green_task = w4[w4.index("YOUR TASK:\n1. Implement EXACTLY"): w4.index("${COMMON}`\n\nconst advPrompt")]
w4adv = w4[w4.index("const advPrompt = (u, green, round) =>"): w4.index("const fixPrompt")]
w4fix = w4[w4.index("const fixPrompt = (u, adv) =>"): w4.index("log('W4 batch 5 mode='")]

w42 = r'''export const meta = {
  name: 's67-w4-2-green',
  description: 'W4-2 ENABLE_SHOPPING_DISCOVERY_URL_SPLIT green on Opus 5.5 from the gated red (wip f6d0d3b4): Green -> Adversary -> one Fix round -> re-adversary, with the Fable red-gate rulings from the session-66 close doc (binding)',
  phases: [
    { title: 'Green', detail: 'minimal implementation, every pin mutation-checked, all gates', model: 'claude-opus-5-5' },
    { title: 'Adversary', detail: 'independent attempt to refute', model: 'claude-opus-5-5' },
    { title: 'Fix', detail: 'one fix round for blocking/major defects, then re-adversary', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const RULINGS = (args && args.rulings && typeof args.rulings === 'object') ? args.rulings : {}
const MYSP = '__MYSP__'

__COMMON__
const ALL = [
__ENTRY__]
const UNITS = ALL

__SCHEMAS__
const greenPrompt = (u) => `You are implementing the GREEN phase of unit ${u.key} (myez/Qaren backend). Worktree: ${u.dir}. Spec: ${u.dir}/${u.spec} - its LAST section "FABLE REVIEW RULINGS (binding, 2026-09-23)" overrides the body.
The RED phase report (tests, failing counts, measurements, comm-gate base, spec disagreements) is at ${MYSP}/w4_red_${u.key}.json - READ IT IN FULL FIRST.
${RULINGS[u.key] ? 'FABLE RED-GATE RULINGS for this unit (binding; they override the spec AND the review rulings where they conflict):\n' + RULINGS[u.key] : 'Fable reviewed the red report and issued no rulings beyond the spec and its appended review rulings.'}
${u.extra}

STATE ON DISK: the red phase's test file tests/test_shopping_price_not_self_pending.py (16 right-reason reds / 35 pins) is COMMITTED as wip f6d0d3b4 on branch feature/s65-w4-2-shopping-url-split above base 6ab9d7ea, so git status --short is EMPTY and git diff 6ab9d7ea..HEAD --stat lists ONLY that test file - confirm both FIRST; if anything else is present, stop and report. The .qa-w4/ folder (spec, comm tools, recorded comm set and gate_base_W4-2.json) is gitignored and on disk.
__GREEN_TASK__${COMMON}`

__ADV__
__FIX__
log('W4-2 green: ' + UNITS.map((u) => u.key).join(', '))
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
log('W4-2 green: ' + done.map((r) => r.unit + '=' + r.final_verdict).join(', '))
return { mode: 'green', results: done }
'''
w42 = (w42.replace('__MYSP__', MYSP).replace('__COMMON__', w4common).replace('__ENTRY__', w4entry)
          .replace('__SCHEMAS__', w4schemas).replace('__GREEN_TASK__', w4green_task).replace('__ADV__', w4adv).replace('__FIX__', w4fix))
w42 = w42.replace("git status --short\\` and \\`git diff --stat\\` FIRST and confirm; if anything else is present, stop and report.", "")
(SP / "s67-w4-2-green.mjs").write_text(w42, encoding="ascii", errors="strict")

# syntax check: wrap in an async body
for name in ("s67-retro-resume.mjs", "s67-w4-2-green.mjs"):
    src = (SP / name).read_text(encoding="utf-8").replace("export const meta", "const meta", 1)
    chk = SP / ("check_" + name)
    chk.write_text("(async () => {\n" + src + "\n})()\n", encoding="utf-8")
    r = subprocess.run(["node", "--check", str(chk)], capture_output=True, text=True)
    print(name, "SYNTAX", "OK" if r.returncode == 0 else "FAIL", r.stderr[:800])
    non_ascii = [i for i, ch in enumerate((SP / name).read_text(encoding='utf-8')) if ord(ch) > 126 or (ord(ch) < 32 and ch not in "\n\r\t")]
    print(name, "non-ascii/control chars:", len(non_ascii), "bytes:", (SP / name).stat().st_size)
