# S81-16b KB-BRANDS GREEN report (GREEN agent, Opus 5.5, 2026-11-04)

Unit S81-16b (FOCUS: migration 052). Base 0b19de5b; branch feature/s81-s16b-kb-brands; HEAD 28eec42b2055920604acb1e4ef9765fe74126625 (one commit through the hook, no push, no PR, no rebase).
Written through the shell (python), per the report rule.

## Files (sha256 on disk after; before = the byte copies in S81-16b_green_before/)
- migrations/052_kb_brands.sql  after fef8ec199d02dfd6121e9cbacc61c6e363ba077dc9ffd9b9608cd194fe85d1d8  before (new)
- migrations/rollback/052_kb_brands.sql  after 766cff1cd3e2372902751bb63f0681bac46b6ce9de9291b457f441f41fc33bf2  before (new)
- app/services/kb_service.py  after b9c25bc125d1d221c84c6fcd423189fd57931162b592891ab1a744c93410c3a2  before 162f5c1f7c87de87df3176c341a585c05b001764f175f095e9a517df498c1fd5
- scripts/kb_seed_common.py  after e1bb9d46184174b93b0ae35bae3efa24901d92947a96da696e79c630d672d0e4  before 34e03725bb69cfb93172706c7245629ac0ca3a55f27d9f49fb51433b6ff324ae
- scripts/seed_kb_brands_wikidata.py  after 61c54417802dd5ab970bde94580598b07bc76ec29faa079362d8b642639cf031  before 17783921530063f7394b4615906ec72e0352b077f98478e49ac475753281b477
- tests/test_s81_s16_kb_seed.py  after 9f6f020939f64a101425db77d9e940bda7ca526890e226534831caf62b2adcf9  before 2cb4a7794ae880f5969fdb65326d4a1b9321a4bfc0fb724422f5e9a8fa901b8c
- tests/test_s81_kb_schema.py  after 234da82c21dd6fa53706f7f76de789a1ed54f79eeead498c771ae306e18b9470  before 9f420bc0a82b5610732f91279c8f3cfbfdcc97aae02f15341a498757011ed59e
- tests/test_s81_s16b_kb_brands.py  after cd67db3bd75d90ae90eeb90ce48c90aac4bb9131ac8e99753e99b36738b75cbd  before (new)
- CLAUDE.md  after 8b0725bca73b1756b135cc8f930429031bcab06ad4f83f772c19b03d6e5d4bcd  before c02ac5a5a3cb1ab413dd37e115454e99c7be8e196ee07df4abf32b21bfd1b4ab

Frozen RED file re-hashed first and last: cd67db3b...38b75cbd (byte-identical, committed).
APPLY drafts for the orchestrator to file: S81-16b_green/apply/APPLY_052_{1_PRECHECK,2_ONE_PASTE,3_POSTCHECK}.sql (ONE_PASTE regenerated from the final 052 bytes; sqlfluff clean, ASCII, LF).

## Gates
- G1 py_compile OK on the edited .py files + the RED file; ruff --select E9,F63,F7,F82 --no-cache: All checks passed (full ruff on the three app/scripts files also clean); the hook passed on commit.
- G2 new files ASCII + LF (0 bytes > 127); edited files keep CRLF; `git diff --stat` hunks only (CLAUDE.md 2+/2-); added-line sweep (@gmail, +973, 8-digit runs, key shapes) empty.
- G3 `sqlfluff lint --config .sqlfluff` 052 + rollback: All Finished!, rc 0 (and the three APPLY_052 files).
- G4 RED file 129/129 flags unset `[pyt] tag=s16b-green-red-off elapsed=6s status=OK rc=0`; 129/129 with ENABLE_KB_BRANDS=apply KB_BRANDS_MAX=1 ENABLE_KB_SEED=apply for that one call `[pyt] tag=s16b-green-red-on elapsed=10s status=OK rc=0`; netguard 0.
- G5 E-row files 673 passed / 5 failed = exactly the environmental G2 R27 CRLF nodes (as at base; R27 re-checked on the LF bytes: clean) `[pyt] tag=s16b-green-g5 elapsed=14s status=FAIL rc=1`.
- G6 seven migration readers 168 passed `[pyt] tag=s16b-green-g6 elapsed=25s status=OK rc=0`.
- G7 comm set 303 files (the RED 302, sha c5734182..., + the RED file; HEAD set sha fcceee0b...) in 13 chunks + test_secret_scan_static.py alone: 19,140 passed, 6 failed, 2 errors = the 8 base-record nodes; `comm -13` vs the STORED base record (LC-6, reused, not re-run) EMPTY, `comm -23` EMPTY.
- G8 33/33 mutants KILLED on AssertionError (M01-M30 + M31 / M32 / M33), byte copies restored and sha-verified, the lock removed.
- G9 throwaway PostgreSQL 18.1 (port 55432): 045 applied; PRECHECK all true; 052 applied; POSTCHECK grid exactly as stated (check_count 6, host_index_unique f, every anon / authenticated privilege f, sr_truncate f); re-apply clean; 16 negative inserts refused (15 x 23514, NULL label 23502); the trigger moved updated_at; anon / authenticated SELECT and UPDATE refused; ON CONFLICT DO NOTHING RETURNING: 1 row then 0; the 045 rollback first failed 2BP01 and changed nothing; rollback 052 then 045 clean; cluster stopped, data directory left.
- G10 CLAUDE.md readers 481 passed `[pyt] tag=s16b-green-g10 elapsed=20s status=OK rc=0`.
- Client fences: the fourteen by path through the junction (node v24.11.1, jest 29.7.0): 13/14 suites, 236 passed / 4 failed = exactly the four config/nativeBundle.w37 drift nodes. The hook test files NOT run (no .githooks change); the FULL jest NOT run (LC-7: the last round).

## Comm set
- HEAD failures (8) = the stored base record: test_prompt_truth x2 (tiktoken env), test_s81_s10_fragrance_gate r06, the five s16 r27 CRLF nodes. branch-only NEW: none.
- Base record REUSED (LC-6): harness/base_records/0b19de5b.../c5734182....txt; not re-run.
- Chunk logs: S81-16b_green/comm/*.log; [pyt] lines in S81-16b_green/comm_progress.txt (secret 34s OK; comm-00..12 OK except 06 (2 tiktoken ERRORs), 08 (s10 r06), 09 (5 r27 CRLF)).
- The driver waited 23 min for the G4 GREEN lane's comm chunks (one pytest at a time); no DUPLICATE, nothing killed.

## Mutants (33/33 KILLED, AssertionError only; S81-16b_green/mutants/results.json, table.txt)
M01 test_s16b_s07_cap_and_order, test_s16b_s09_limit_hit_count
M02 test_s16b_s05_rerun_updates_wikidata_rows_only[none-returned], test_s16b_s05_rerun_updates_wikidata_rows_only[two-returned], test_s16b_s10_write_failure_is_quiet[update]
M03 test_s16b_s05_rerun_updates_wikidata_rows_only[none-returned], test_s16b_s05_rerun_updates_wikidata_rows_only[two-returned]
M04 test_s16b_k01_census_constants, test_s16b_s05_rerun_updates_wikidata_rows_only[none-returned], test_s16b_s05_rerun_updates_wikidata_rows_only[two-returned]
M05 test_s16b_k04_belt_holds_without_the_rule
M06 test_s16b_k03_builder_refuses[host-rule-only], test_s16b_k05_rule_read_at_call_time
M07 test_s16b_s03_dry_counts_no_write
M08 test_s16_r23_brands_dry_and_apply[true], test_s16b_s03_dry_counts_no_write, test_s16b_s04_apply_writes_kb_brands_only[apply-dry-run]
M09 test_s16_r23_brands_dry_and_apply[true], test_s16_r24_brands_robots_failclosed[403], test_s16_r24_brands_robots_failclosed[disallow]
M10 test_s16_r23_brands_dry_and_apply[apply], test_s16b_s04_apply_writes_kb_brands_only[apply], test_s16b_s05_rerun_updates_wikidata_rows_only[none-returned]
M11 test_s16b_s03_dry_counts_no_write
M12 test_s16b_s03_dry_counts_no_write
M13 test_s16b_s03_dry_counts_no_write, test_s16b_s04_apply_writes_kb_brands_only[apply-dry-run], test_s16b_s04_apply_writes_kb_brands_only[apply]
M14 test_s16b_b04_regex_texts_equal_the_leaf, test_s16b_k01_census_constants, test_s16b_k03_builder_refuses[qid-Q01]
M15 test_s16b_s04_apply_writes_kb_brands_only[apply-dry-run], test_s16b_s04_apply_writes_kb_brands_only[apply], test_s16b_s06_dedupe_and_host_choice
M16 test_s16b_s02_off_is_inert[-seed-apply], test_s16b_s02_off_is_inert[-seed-true], test_s16b_s02_off_is_inert[-seed-unset]
M17 test_s16b_s11_no_label_or_host_in_logs
M18 test_s16b_s04_apply_writes_kb_brands_only[apply], test_s16b_s05_rerun_updates_wikidata_rows_only[none-returned], test_s16b_s05_rerun_updates_wikidata_rows_only[two-returned]
M19 test_s16b_b05_service_role_only
M20 test_s16b_b05_service_role_only
M21 test_s16b_b07_host_index_not_unique
M22 test_s16b_b06_trigger_and_045_guard
M23 test_s16b_b03_columns_match_the_leaf, test_s16b_b04_regex_texts_equal_the_leaf
M24 test_s16b_b06_trigger_and_045_guard
M25 test_s16b_b09_rollback_statements
M26 test_s16b_b03_columns_match_the_leaf
M27 test_s16b_s06_dedupe_and_host_choice
M28 test_s16b_s10_write_failure_is_quiet[update], test_s16b_s10_write_failure_is_quiet[upsert]
M29 test_s14_r27_builder_keys[kb_coverage_daily], test_s14_r27_builder_keys[kb_feedback], test_s14_r27_builder_keys[kb_gaps]
M30 test_s16b_pin2_host_derivation_literal, test_s16b_s07_cap_and_order
M31 test_s16b_s04_apply_writes_kb_brands_only[apply-dry-run], test_s16b_s04_apply_writes_kb_brands_only[apply], test_s16b_s06_dedupe_and_host_choice
M32 test_s16b_s03_dry_counts_no_write, test_s16b_s04_apply_writes_kb_brands_only[apply-dry-run], test_s16b_s04_apply_writes_kb_brands_only[apply]
M33 test_s16b_s03_dry_counts_no_write, test_s16b_s04_apply_writes_kb_brands_only[apply-dry-run], test_s16b_s04_apply_writes_kb_brands_only[apply]

## Deviations / choices
- D1 the commit trailer names the committing agent's own model (Claude Opus 5.5), not the 'Fable 5.1' of the procedure template (the brief: the trailer names your own model).
- D2 brand_updates is bumped after each update call returns (pinned by the frozen S10 row: an update that raises leaves brand_updates 0); L13 worded as 'update calls made (attempts that returned)'.
- D3 _run(args, client, mode) takes mode with a default MODE_DRY so a direct two-argument call keeps the DRY behaviour; main passes the resolved mode.
- D4 the write lives in a small helper _write_brands(client, rows, counts) (try / except WARNING / finally adding the writer counters); behaviour as spec 2.5 / GC-4 Q5.
- D5 CLAUDE.md step (8) carries R-S16B-11 (one-off commands carrying ENABLE_KB_BRANDS, never a service variable; ENABLE_KB_SEED confirmed unset or false first) and the row sentence carries R-S16B-13 (kb_ingest keys its writes by its own constants).
- D6 G9: in the plain cluster service_role has no BYPASSRLS, so its SELECT returned 0 visible rows with RLS on (grant present, no permission error); on Supabase service_role bypasses RLS. Recorded, not a defect.
- D7 G10 netguard blocked 24 attempts from 2 s04 nodes (neutralized.supabase.invalid; both PASSED) - unrelated to this unit (s04 is a CLAUDE.md reader only).

## Not measured
- The FULL jest (LC-7, the last round); the hook test files (no .githooks change); the PostgREST half of L7; the Wikidata row count (offline).

## Worktree
- git status --short: empty (all nine files committed); .qa-mutation.lock absent; the junction untouched.
- PR body: S81-16b_green/PR_BODY.md (10,909 B, measured with python).
