# G-INC-1 ADVERSARY REPORT (lens: correctness + the GC-8 named checks; agent Opus 5.5; 2026-11-11)

HEAD verified a92b0ba325914c59fbb26a2e7803bf8317aa2bbc (start and end); worktree git status empty. Frozen RED files re-hashed start and end: x9 b2ef4d34..., x10 f1c7f330..., x8 8a2cc6d6..., x2a febb83de... (all match GC-1). Scratch worktree <SP>/G-INC-1_adv/wt (short path; the long name exceeds MAX_PATH) at a92b0ba3, clean after every restore, removed with git worktree remove --force; git worktree list shows 0 entries.

VERDICT: NOT_READY (one BLOCKING; no defect found in the GREEN app/ bytes).

## BLOCKING
B1 CI WILL BE RED: tests/test_inc_x10_listing_match_guard.py::test_p10_2_flag_off_identity_full_config[unset,false,padFALSE,zero,garbage] fail when tests/test_identity_stamps_wave_b.py is collected first (CI = one `python -m pytest tests/` process, alphabetical; "test_id" < "test_inc"). wave_b imports scripts/measure_warmed_kpi.py at COLLECTION time, which does os.environ.setdefault("WARMER_CONTEXT","1") (scripts/measure_warmed_kpi.py:18); the wave_b restore list _MEASURE_ENV_KEYS (tests/test_identity_stamps_wave_b.py:57-59) omits WARMER_CONTEXT, so the warmer write veto makes should_cache_price refuse the women's listing and the P10-2 base-value line fails (`assert ps.should_cache_price(INCIDENT_Q, ...) is True` -> False). Reproduced:
  [pyt] tag=inc-g1-adv-order start=2026-11-11 23:07:44 end=2026-11-11 23:07:49 elapsed=5s bound=600s status=FAIL rc=1 (wave_b + x10: 5 failed)
  [pyt] tag=inc-g1-adv-order2 start=2026-11-11 23:07:58 end=2026-11-11 23:08:05 elapsed=7s bound=600s status=FAIL rc=1 (wave_b + the four RED files: 5 failed, 97 passed; only P10-2)
  [pyt] tag=inc-g1-adv-ciorder start=2026-11-11 23:14:41 end=2026-11-11 23:15:58 elapsed=77s bound=1200s status=FAIL rc=1 (spec 12.2 CI-order set + wave_b in alphabetical position: only the 5 P10-2 nodes fail)
 Side effect: R10-10 (should_cache refuses the women's listing) passes VACUOUSLY in CI order (the veto, not the guard, refuses). The defect is in the frozen RED file's env fixture (no delenv of WARMER_CONTEXT), not in the GREEN app/ bytes; GREEN reported it as OPEN Q1. Fix = test-only pin-fix (LC-2): the RED file's autouse _env adds monkeypatch.delenv("WARMER_CONTEXT", raising=False) (or wave_b restores it, an extra E-row); the next round's CI-order set must contain test_identity_stamps_wave_b.py before the RED files (GREEN Q2).

## MAJOR
none.

## GC-8 NAMED CHECKS
- INC-X9 absent path (git show 683f56c0): ResultsScreen.tsx:988-1006 resolveCohortPeerCount / resolveCohortGovernorate read `cohort_summary ?? personalization?.cohort ?? null` and return 0 / '' when absent; CohortBadge.tsx:62 `if (peerCount <= 0 || !governorate) return null;`. The backend `personalization` block (response_builder.py:1357, :2084) has no `cohort` key, so the fallback never fires. The builder reads cohort_summary only at RB:2200-2212; get/set_comparison_cache have zero callers (no whole-response replay). was_cohort_block_active is pure (extraction_service.py:2102-2119), so dropping its call from the helper removes no side effect. `_COHORT_GOV_SKIP` had no other reader at a74caba7 (git grep). Every other key identical: P9-2 / P9-3 drop only VOLATILE_ALLOWED = {timestamp, generated_at, created_at, elapsed_ms, elapsed_seconds, request_id, cached_at, fetched_at, retrieved_at} (clock and id fields only) and assert the measured volatile set is a subset. SOUND.
- INC-X10 truth table T1-T18: all rows green ON; the four table lines are correct product knowledge (Eros / Dylan Blue / Aventus men default with women siblings Pour Femme / Pour Femme / for Her; D&G Light Blue women default with the Pour Homme sibling) and EACH line's default side is pinned: mutants flipping each default (A10-eros, A10-dylan, A10-aventus, A10-lightblue) and dropping the Dylan line are all KILLED. Over-rejection of a legitimate one-sided listing: the same-side marked rows T7/T9/T14, the unmarked T10, both-sides T11/T18 and the non-table women's bases T5/T6 stay ACCEPT (P10-1). Cached-entry path: H2 in _descriptor_backstop_axes_verdict reached via backstop_identity_verdict from _cache_price_identity_ok (scs:1263) and is_price_showable (ps:1998); R10-8 / R10-9 kill M10-6. Category string "fragrances" is the production value (category_gate / extraction_service). The descriptor lru key does not need the new flag (the flag is read in _vd_gender_line_flip per call, not in the descriptor). SOUND.
- INC-X8: _phase2_cached_rating calls only extract_rating_from_shopping (rating_service.py:127-272: no await, no httpx, no LLM; already imported at scs:1540, no new import); acceptance identical to get_verified_rating tier 0 (rating_service.py:285-290); returns the same dict (same keys, same rating_source). KB-full exclusion pinned (M8-7 KILLED by P8-6). The flag is the first conjunct (M8-1 KILLED by P8-1, full config). SOUND.
- INC-X2a: same awaits in the same order (search_images, extract_image_via_gpt), same returns (.strip() kept), same exceptions (the sync credit gate still propagates; CancelledError is not caught by the `except Exception` arms, as at base); the CancelledError arm has no await and a bare raise (M2-1, M2-5 KILLED); log lines carry constants, closed-set outcomes, type names and ints only (M2-2 KILLED in RED); GC-5 grammar of both lines verified character for character (A2-gramcancel KILLED). SOUND.
- Group: flag-OFF identity with the FULL configuration: P8-1 green and kills M8-1; P10-2 green in isolation and kills M10-1, but RED in CI order (B1). Footprint off the eight arms PR #399 edited (a74caba7..6b909e0a: 1 hunk image_routes.py, 6 extraction_service.py, 1 url_extraction_service.py): the branch touches none of those files. git merge-tree onto 6b909e0a: conflict in CLAUDE.md only (expected; the final round's union, GC-9).

## Runs (scratch worktree at a92b0ba3)
- [pyt] tag=inc-g1-adv-on start=2026-11-11 23:07:24 end=2026-11-11 23:07:30 elapsed=6s bound=600s status=OK rc=0 (both flags ON: 84 passed) [hermeticity] sentinel checked 84 test(s) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=inc-g1-adv-off start=2026-11-11 23:07:32 end=2026-11-11 23:07:37 elapsed=6s bound=600s status=OK rc=0 (both flags unset: 84 passed) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=inc-g1-adv-order / order2 / ciorder: see B1.
- [pyt] tag=inc-g1-adv-comm09 start=2026-11-11 23:16:26 end=2026-11-11 23:18:05 elapsed=99s bound=1200s status=OK rc=0 (1926 passed)
- [pyt] tag=inc-g1-adv-comm16 start=2026-11-11 23:18:07 end=2026-11-11 23:18:42 elapsed=35s bound=1200s status=FAIL rc=1 (2 failed = test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys, ::test_applied_shifts_list_is_default_empty_when_no_priorities; both in the base record 23f5330f)
- [pyt] tag=inc-g1-adv-comm17 start=2026-11-11 23:18:44 end=2026-11-11 23:19:08 elapsed=24s bound=1200s status=FAIL rc=1 (2 errors = the two test_prompt_truth.py tiktoken nodes; base-known)
- [pyt] tag=inc-g1-adv-pins start=2026-11-11 23:19:27 end=2026-11-11 23:19:54 elapsed=26s bound=1200s status=OK rc=0 (test_model_config*.py, test_prompt_fence.py, test_u3c_store_false_pin.py, the CLAUDE.md readers test_ci_gates.py + test_behavior_dimension_translation.py, the migration predicate pin, openai key hygiene, sentry u8d, start_command: 432 passed)
- ruff E9,F63,F7,F82 on the 3 app files + the E-row file + the 4 RED files: All checks passed; default ruff set 59 = GREEN's 21+38 (same at base); py_compile ok.
- Hook test files: NOT run (no .githooks change; excluded by the comm rule). Jest fences / full jest: NOT run (no client file; GREEN's fence run stands; LC-7 full jest is the final round's).

## Mutants (on byte copies in the scratch worktree; restore sha256 verified after each; lock created and removed)
Spec mutants re-cut on the GREEN bytes, all KILLED by AssertionError: M9-1, M9-2, M9-4, M10-1, M10-2, M10-3 (re-cut: the GREEN line carries a trailing comment), M10-4, M10-5, M10-6, M10-8, M10-9, M8-1, M8-2, M8-3, M8-4, M8-7, M2-1, M2-4, M2-5 (19).
Own mutants: KILLED A10-eros, A10-dylan, A10-aventus, A10-lightblue, A10-dropdylan, A8-grammar, A8-hitmiss, A8-verified, A2-err, A2-gramcancel, A2-pigskip. SURVIVED: A10-beautywide (H1 widened from "fragrances" to _FRAGRANCE_BEAUTY_CATEGORIES), A2-llmerr (llm_pick error outcome logged as "miss").
Logs: <SP>/G-INC-1_adv/amut_*.log, amut_results.json, amut_results_run1.json; harness <SP>/G-INC-1_adv/amut.py.

## Comm set re-derivation
GREEN's 736-file list vs all 770 tests/test_*.py: 34 excluded = 4 test_precommit_hook*.py + 30 others; none of the 30 references price_service / structured_comparison_service / image_service / rating_service / response_builder / CLAUDE.md nor reads app/ as source (the hits read scripts/ or data/ JSON, or cohort_service). No missing member.

## MINOR (stated limits / documentation)
m1 A10-beautywide survives: the fragrances-only scope against makeup / skincare / haircare is unpinned (P10-4 covers only fashion and None).
m2 A2-llmerr survives: the llm_pick "error:<T>" outcome is unpinned (the serper_images one is pinned by R2-4).
m3 The GREEN report and the PR body print `NO [pyt] LINE` in place of every [pyt] summary line (8 places): the evidence lines are missing; the PR body must not ship the placeholder.
m4 PR body "26 mutants, none survived": the RED table ran 25 (M9-3 not applicable after R-G1-6); say 25 applied + 1 not applicable.
m5 The E-row test names now contradict their assertion (test_broadened_governorate_quality_still_emits asserts None) by GC-6 design (names unchanged); the remaining None rows of test_cohort_summary_orchestrator.py now prove nothing about gating (the helper is a constant None).
m6 X10 is fail-open for non-Latin titles (Arabic gender words are not in the token sets), and a candidate whose only marker is a pronoun in marketing text ("gift for her" on a men's Eros listing) would be rejected; neither is in L-X10-1..5.
m7 CLAUDE.md will conflict on the replay onto 6b909e0a (measured with git merge-tree); the final round's union, already planned (GC-9).

## Prove-nothing rows
- R10-10 in CI order (passes through the WARMER_CONTEXT veto, B1).
- The tests/test_cohort_summary_orchestrator.py None rows (the helper is a constant).
- P9-5 (a source-count footprint pin, not behaviour).

No worktree file edited.
