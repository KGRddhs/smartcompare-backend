export const meta = {
  name: 's68-red-w04efg',
  description: 'Session 68 unit 1 RED phase on Opus 5.5: W0-4e/W0-4f/W0-4g follow-ups of R-W04 (backfill cap exemption + offloaded scan, extract_from_url extractors on the price-parse pool, pool stats on /health, the r1 test-hardening pins) - reproductions, red tests, mutant survival, satisfiability prototype, comm and CI-order sets',
  phases: [
    { title: 'Red', detail: 'measure at 61585c58, write tests/test_retro_w0_4_efg.py + the allowlist edit, prove every red/pin/kill row, prototype satisfiability in a detached scratch worktree', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const DIR = 'C:/Users/SynAckITPC/Documents/AI/sc-w0-4efg'
const SPEC = DIR + '/.qa-s68/W0_4EFG_SPEC.md'
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/b1819d0c-d9c5-466a-ba0d-b82774c624db/scratchpad'
const COMMON_PATH = MYSP + '/s68-common.txt'

const RED_SCHEMA = {
  type: 'object',
  required: ['unit', 'base_sha_confirmed', 'files_written', 'red_count', 'pin_count', 'kill_count', 'failures_are_right_reason', 'failure_evidence', 'pins_evidence', 'kill_evidence', 'mutant_survival_at_head', 'prototype', 'comm_set', 'ci_order_set_base_run', 'measurements', 'spec_disagreements', 'questions_for_fable', 'git_status_final', 'scratch_cleanup'],
  properties: {
    unit: { type: 'string' },
    base_sha_confirmed: { type: 'boolean', description: 'git rev-parse HEAD == 61585c58 and git status --short empty at start' },
    files_written: { type: 'array', items: { type: 'string' }, description: 'one entry per file: "<path> <sha256>" (the final bytes on disk)' },
    red_count: { type: 'integer' },
    pin_count: { type: 'integer' },
    kill_count: { type: 'integer' },
    failures_are_right_reason: { type: 'boolean' },
    failure_evidence: { type: 'string', description: 'verbatim pytest summary lines for the new file at HEAD (both flag states) + one sentence per RED row naming the genuine absent behaviour it fails on' },
    pins_evidence: { type: 'string', description: 'every PIN row green at HEAD: node names + summary line' },
    kill_evidence: { type: 'string', description: 'per KILL row: the mutant applied (file, the exact edit), the red node names under the mutant, the sha256-verified restore' },
    mutant_survival_at_head: { type: 'string', description: 'the four r1 mutants rebuilt at HEAD against the EXISTING pins: SURVIVED/KILLED each, with the summary lines and the restores' },
    prototype: { type: 'string', description: 'the satisfiability prototype in the detached scratch worktree: diff stat, the six unit files summary lines in both flag states, the patch file path written under .qa-s68/, and the worktree removal' },
    comm_set: { type: 'string', description: 'how .qa-s68/comm_set.txt was derived, its size, and the first 10 entries' },
    ci_order_set_base_run: { type: 'string', description: '.qa-s68/ci_order_set.txt (sorted) and the ONE-process run of that set at HEAD WITHOUT the new test file: summary line + every failing node id and whether it is in tests/.pre_impl_failures.txt' },
    measurements: { type: 'array', items: { type: 'string' } },
    spec_disagreements: { type: 'array', items: { type: 'string' }, description: 'spec claims found WRONG when tested, with the measurement; empty if none' },
    questions_for_fable: { type: 'array', items: { type: 'string' } },
    git_status_final: { type: 'string' },
    scratch_cleanup: { type: 'string', description: 'git worktree list output showing no scratch worktree remains; confirmation that no .env copy exists under the scratchpad' },
  },
}

const prompt = `You are running the RED phase of unit W0-4e/W0-4f/W0-4g (myez/Qaren backend), the follow-ups of the merged R-W04 retro (PR #196). Worktree: ${DIR} (branch retro/w0-4efg-followups at 61585c58 = origin/main). Spec (authoritative): ${SPEC}. Shared rules: read ${COMMON_PATH} in full FIRST and obey every line.

CONTEXT TO READ (in the worktree): docs/investigations/2026-09-24-session-67-state/prbody_R-W04.md (the whole file; the "Stated limits / follow-ups" paragraph and "## Follow-ups"), docs/investigations/2026-09-24-session-67-state/retro_adv_R-W04_r1.json (tests_that_prove_nothing - the five rows, four of which are the KILL targets), docs/investigations/2026-09-24-session-67-state/retro_rulings_R-W04.txt, CLAUDE.md's ENABLE_PRICE_PARSE_OFFLOAD row (grep 'ENABLE_PRICE_PARSE_OFFLOAD' in CLAUDE.md) and its W0 ACTIVATION ORDER step (2). Code: app/services/price_service.py (price_parse_offload_enabled, PRICE_FETCH_MAX_BYTES, _get_price_parse_pool, _get_price_parse_semaphore, run_parse_offloaded, curl_fetch_html), app/services/structured_comparison_service.py (_extract_price_from_html_maybe_offloaded, _lazy_bh_pdp_backfill, the price_service import block), app/services/url_extraction_service.py (extract_json_ld, extract_meta_tags, extract_amazon_data, extract_noon_data, extract_generic_data, _price_parse_offload_enabled, extract_with_ai, extract_from_url), app/main.py (loop_lag_snapshot, health_check), scripts/verify_flag_byte_identity.py (compare_results, main), and the existing tests tests/test_retro_w0_4.py (its fixtures _zero_network / _w04_env / _fresh_parse_pool, the AST guard, the cap tests, test_w04b_lazy_backfill_caller_flag_off_scans_the_whole_search_page, test_w04c_extract_with_ai_sends_the_same_prompt_flag_on_vs_off), tests/test_verify_flag_byte_identity.py (_run_main), tests/test_health_loop_lag.py (test_health_handler_is_a_pure_dict_read), tests/test_lazy_bh_pdp_backfill.py, tests/test_price_parse_offload.py. Line numbers in the spec were measured at 61585c58 - re-locate every anchor by symbol.

YOUR TASK, in order:
0. Confirm 'git rev-parse HEAD' is 61585c58 and 'git status --short' is empty; if not, STOP and report.
1. MEASURE the defects at HEAD, each with a pasted result: (E) the flag-ON backfill loses an href past 3,000,000 chars (drive scs._lazy_bh_pdp_backfill exactly as the existing OFF pin does but with ENABLE_PRICE_PARSE_OFFLOAD=true); (F) with tests/test_retro_w0_4.py's _TRANSITIVE_ALLOWLIST set to frozenset() the transitive AST guard reports ('url_extraction_service.py', 'extract_from_url') - do this measurement on a byte snapshot and restore it, then make the edit permanent in step 2; (G) price_service has no price_parse_pool_stats and /health has no price_parse_pool key (TestClient GET through a pytest probe); (H) rebuild the four r1 mutants (N_curl_cap_flag_true_only_literal, N_ues_text_trunc_on, N_harness_compare_intersection_only, N_harness_compare_whole_payload_not_results) from byte snapshots, run the EXISTING pins (tests/test_retro_w0_4.py and tests/test_verify_flag_byte_identity.py) against each, record SURVIVED/KILLED, restore sha256-verified. Also measure and record: the repo's expected flag-OFF values; the thread name prefix of the pool; whether ThreadPoolExecutor exposes _work_queue on the pinned Python (3.12.9).
2. WRITE the tests exactly as the spec's section 4 lists them: the NEW file tests/test_retro_w0_4_efg.py (own autouse fixtures copied from tests/test_retro_w0_4.py's pattern: zero-network guard incl. curl_cffi.requests.get, fresh pool by TYPE, flag/env reset; synthetic fixture pages; no corpus files; no network) and the ONE edit to tests/test_retro_w0_4.py (the allowlist to frozenset()). Every test name and row id from the spec; the docstring of each test states RED / PIN / KILL and the reason. Reds must fail for the RIGHT reason (an assertion on the absent behaviour), never on a setup error, ImportError or AttributeError at collection - a missing function is asserted for inside the test (hasattr / getattr with a message) so the failure names the absence.
3. RUN the new file with the flag unset and with =true; paste the summaries; every RED row fails as intended, every PIN row is green at HEAD. For each KILL row: apply its mutant from a byte snapshot, run the new file, record the red node names, restore, sha256-verify. Run tests/test_retro_w0_4.py once to confirm only the allowlist edit turned red (exactly one node: test_w04c_no_async_def_reaches_a_soup_helper_inline).
4. SATISFIABILITY PROTOTYPE (the design must be provable before the gate): create a detached scratch worktree under your scratchpad at 61585c58, implement the spec's design MINIMALLY there (sections 1-3), copy the new test file and the allowlist edit in, run the six unit files (tests/test_retro_w0_4.py tests/test_retro_w0_4_efg.py tests/test_price_parse_offload.py tests/test_verify_flag_byte_identity.py tests/test_lazy_bh_pdp_backfill.py tests/test_health_loop_lag.py) with the flag unset AND =true - all green (paste); ruff + py_compile clean there. Save 'git diff' of the prototype's app/ and scripts/ changes to ${DIR}/.qa-s68/proto_w04efg.patch (gitignored; the green may READ it, never copy it blindly). Do NOT run the corpus gate. Remove the scratch worktree; confirm with git worktree list. If any red row cannot be made green by the design, STOP the prototype, keep the tests, and report the row in spec_disagreements with the measurement.
5. DERIVE and write ${DIR}/.qa-s68/comm_set.txt (every tests/*.py referencing price_service, structured_comparison_service, url_extraction_service, verify_flag_byte_identity, 'app.main' or 'from app import main' / 'import main'; sorted; one path per line) and ${DIR}/.qa-s68/ci_order_set.txt (the spec section 5(f) list re-derived by grep for the touched symbols curl_fetch_html, _lazy_bh_pdp_backfill, extract_from_url, url_extraction_service, run_parse_offloaded, _PRICE_PARSE_POOL, price_parse, health_check, '/health', verify_flag_byte_identity - plus the six unit files; sorted alphabetically). Run the CI-order set MINUS tests/test_retro_w0_4_efg.py in ONE process at HEAD under the guard with --timeout=60 and CI's deselects (build --deselect args from tests/.pre_impl_failures.txt lines that carry a node id); paste the summary and list every failing node id, marking whether it is in tests/.pre_impl_failures.txt. Do NOT run the comm set (the green does).
6. Report per the schema. Leave the worktree with ONLY tests/test_retro_w0_4_efg.py (new), tests/test_retro_w0_4.py (allowlist edit) and the gitignored .qa-s68/ files changed; 'git status --short' verbatim in git_status_final. Never commit.`

log('unit 1 RED: W0-4e/f/g in ' + DIR)
const red = await agent(prompt, { label: 'red:W0-4efg', phase: 'Red', model: MODEL, effort: 'high', schema: RED_SCHEMA })
return { unit: 'W0-4efg', red }
