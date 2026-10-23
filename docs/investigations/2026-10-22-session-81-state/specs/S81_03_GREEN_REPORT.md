# S81-03 LLM-LEDGER-V2 GREEN report (Opus 5.5 GREEN agent, 2026-10-23 02:54-03:58 AST)

- Unit: S81-03 LLM-LEDGER-V2, flag `ENABLE_LLM_LEDGER_V2`, lane B. Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-s03`, branch `feature/s81-s03-llm-ledger-v2`, base `95cf6f864b4e70980ca191daa064c0118e223c13`, HEAD `9896f0d31bfd8727ec64a6f6b88c305d08b748f7` (one commit, through the pre-commit hook; not pushed, not rebased, no PR).
- `git status --short` after the commit: empty (the four `.qa-s80/APPLY_050_*` files and the spec/review are gitignored).
- Notes folder: `<scratchpad>/S81-03_green/` (notes.md, logs, `mutants_green.py` + `mut/`, `comm/` with `comm_set.txt`, `comm_reasons.tsv`, `run_comm_head.py`, 16 chunk logs + json, `pyt_lines.txt`, `head_failed.txt`; `PR_BODY.md`; `claude_md_row.txt`). Byte copies of every edited file before the edit: `<scratchpad>/S81-03_green_before/` + `SHA256SUMS.txt`.

## RED file
- Re-hashed first: `13d1be3ab5ec742a5b8c32a77f97a70328eba0c680a0b079c97dace020c9ec84` (115,335 B) = the gate sha.
- The one permitted edit (G-3): the U6 PIN row appended at the end. The first 115,335 bytes of the final file hash to the gate sha (every RED row byte-identical). Final sha `dc61b2b316dc3c6b319df1d97fc5bd790f1d3f79e55040ba6b3078fafd94fa17` (117,289 B, 197 nodes, ASCII, LF).
- U6 green at base: a detached scratch worktree of 95cf6f86 under the notes folder (no node_modules), the RED file copied in, `[pyt] tag=s03green-u6-base start=2026-10-23 03:55:03 end=2026-10-23 03:55:09 elapsed=7s bound=600s status=OK rc=0` (10 passed: U6, U4 x7, U5, B7); removed with `git worktree remove --force`, `git worktree list` shows 0 rows.

## Files (final sha256 on disk; before = S81-03_green_before)
| path | +/- | before | after |
|---|---|---|---|
| app/services/llm_pricing.py | +680 (new) | - | 504b9d5e19fc943ee8c888b174dac93ac76844f01b6c4312ff81a8f52da18126 |
| app/services/response_builder.py | +22 | dc3d446f... | 6588555f61585ff0de9263b54b799dd32a8d959315abbffb3ef872d699c79f75 |
| app/services/structured_comparison_service.py | +15/-3 (TG only) | ff33fdd9... | 7cdd3b12aa2324bcd083ffe5d5a7d5888436d9371769f2eaacc95d954d672701 |
| app/services/openai_service.py | +19/-6 | ff15a9fe... | 395a0bcf32c8705f1cd772bbf8e360f8396118116b582f4c084202208e8173f1 |
| app/services/model_router_service.py | +22/-1 | 12cfb15d... | d7a655c967d2893d6cb8f21f992d220d38a77b88a7f223862e032dac47bd5832 |
| app/api/image_routes.py | +16 | 1a440b0f... | 5f1185057046467a36083f89a12ac565a3d2e7ecb4c71596bda58dd29ac521a4 |
| app/api/share_routes.py | +5/-2 | 3be800c5... | 2d947f49cba7ed224dcb2599cb268de82961dfe4a0207ad8f0db4fd7e9fa0014 |
| app/api/admin_routes.py | +186/-1 | 71a38c16... | dda3e00cba5ab190111d3c1eef7897920193e58874b5219823404bc0161e7146 |
| app/static/admin/costs.html | +21 (CRLF kept, 24 bytes > 127 as base) | a64ca0db... | 4b159ee3f3a117f5a5be44a72dcd56fb0bbff59121d078b22d94782bbceb63f7 |
| migrations/050_llm_spend_ledger.sql | +76 (new) | - | e16192e44eba703e912f2f4f5352391ed0e9fedb7627f8bf2d9875d4e69de140 |
| migrations/rollback/050_llm_spend_ledger.sql | +13 (new) | - | 48f03861956328ed0106687b28d21ea89f4e81b2fef47fb850161d27269b4766 |
| tests/test_s75_fanout_identity.py | +2/-1 (E1) | c690a3a4... | ef4f981e17545ed56faf3a7645b6392cd4237be62ca24d46beb4b18d7650146f |
| tests/test_s81_s03_llm_ledger_v2.py | +2533 (RED + U6) | 13d1be3a... | dc61b2b316dc3c6b319df1d97fc5bd790f1d3f79e55040ba6b3078fafd94fa17 |
| CLAUDE.md | +2 (CRLF kept) | cf89f795... | 2837226e8e5f8a50b7374907235a6370200f785f4bf1febbe449869c541d5ffc |
| .qa-s80/APPLY_050_1_PRECHECK.sql / _2_ONE_PASTE.sql (= the forward file) / _3_POSTCHECK.sql | new, gitignored | - | for the orchestrator to copy to the state folder |

`app/services/openai_pricing.py` (K2) and `app/services/api_budget_service.py` (K1) sha-identical to base. Bytes > 127: 0 in every new file and on every added line of the edited files; CR: 0 in new files; no whole-file diff.

## Runs ([pyt] lines)
- `[pyt] tag=s03green-unit-off start=2026-10-23 03:09:31 ... status=FAIL rc=1` (1 failed A13: the OTEL phrase was split over two comment lines; fixed)
- `[pyt] tag=s03green-unit-off start=2026-10-23 03:09:55 end=2026-10-23 03:10:11 elapsed=16s bound=600s status=OK rc=0` (196 passed)
- `[pyt] tag=s03green-unit-on start=2026-10-23 03:10:13 end=2026-10-23 03:10:19 elapsed=7s bound=600s status=OK rc=0` (196 passed)
- `[pyt] tag=s03green-u6 start=2026-10-23 03:11:02 end=2026-10-23 03:11:06 elapsed=4s bound=600s status=OK rc=0` (1 passed)
- `[pyt] tag=s03green-pins start=2026-10-23 03:12:56 end=2026-10-23 03:13:31 elapsed=36s bound=1200s status=OK rc=0` (630 passed; [hermeticity] sentinel checked 630 test(s); [netguard] blocked 1 attempt(s) from 1 node(s): tests/test_share_routes.py::test_view_shared_no_auth_needed [sentinel], the known baseline node)
- `[pyt] tag=s03green-ci-order start=2026-10-23 03:50:16 end=2026-10-23 03:51:02 elapsed=46s bound=1200s status=OK rc=0` (1312 passed, 1 deselected; [hermeticity] sentinel checked 1312 test(s); [netguard] blocked 15 attempt(s) from 9 node(s), all baseline nodes; the one egress-class node test_security_regression::TestBundleBContentSafety::test_dual_shape_product_a_b_hits_sanitizer is in tests/.network_attempt_baseline.txt and in the RED base chunk 12 log)
- After the U6 literal change (0.0123456789 -> 0.0123456, no 8-digit run in an added row): `[pyt] tag=s03green-unit-off2 start=2026-10-23 03:52:16 end=2026-10-23 03:52:28 elapsed=12s bound=600s status=OK rc=0` (197 passed; [hermeticity] 197; [netguard] 0) and `[pyt] tag=s03green-unit-on2 start=2026-10-23 03:52:30 end=2026-10-23 03:52:38 elapsed=8s bound=600s status=OK rc=0` (197 passed)
- `[pyt] tag=s03green-collect-mig ... 03:56:42 elapsed=13s status=OK rc=0` (collect-only: the +1 comm node is tests/test_migration_index_predicate_immutability.py::test_index_predicates_are_immutable[050_llm_spend_ledger.sql])
- ruff `--select E9,F63,F7,F82 --no-cache` on the 9 changed .py: All checks passed. py_compile: clean. sqlfluff 4.3.0 `lint --config .sqlfluff` on both 050 files: rc 0. Pre-commit hook on the commit: passed (ruff, sqlfluff "All Finished!").

## Mutation table (on GREEN's bytes; `mutants_green.py`, one harness, the lock created and deleted, every restore sha-verified, pre-run shas re-checked after every batch)
77 mutants, 76 KILLED, 1 SURVIVED. The RED table's 70 adapted to the GREEN code (M15s replaced: it is equivalent by G-5 on GREEN's None contract; M15 and M52 re-run in GREEN's shape as M15r / M52r, both killed by assertions) plus G2, U6a-U6d and RG1.
- KILLED: M1 (49 nodes), M2, M3, M3b, M4, M5, M6, M7, M8, M9, M10, M11, M11b, M11c, M12, M13, M14, M15 (TypeError crash), M15r, M16, M17, M17b, M18, M19, M20a, M20b, M20c, M21, M22, M22b, M22c, M23, M24, M25, M26, M26b, M27, M28, M28b, M29, M29b, M30, M30b, M31, M32, M33, M34, M35, M36, M37, M38, M39, M40, M41, M42, M43, M44, M45, M46, M47, M48, M49, M50, M51, M52 (TypeError crash), M52r, M53, M54, M55, M56, M57, U6a, U6b, U6c (all three by test_u6), U6d (20 nodes: B4 / B5 / U4), RG1 (unclaimed add made non-read-only and marking every entry taken: B3 / U1 / U2 / U3). Killer lists: `mut/mut_compact.json`. The fault-row mutants M49 / M50 / M53 / M54 fail by the injected `_LeafBoom` reaching the test (or its assertion), the RED design; U6a is converted to an AssertionError by U6.
- SURVIVED: **G2** (Sonnet long-context boundary 200,000 -> 100,000). No RED row pins the G-2 boundary: A9 asserts Sonnet 100,000 flat and 250,000 None, which a 100K or a 200K threshold both satisfy (the RED report's Q2). Proposed hygiene row for an adversary to name: `_price("anthropic", "claude-sonnet-5-5", input_tokens=150000, output_tokens=1000) == approx(0.31)` and `input_tokens=200000 -> approx(0.41)` and `200001 -> None`.

## Comm set (zero-regression gate, flag unset)
- Set: 379 files = the RED agent's 378 (`S03_red/comm/comm_set.txt`) re-derived at HEAD by my own grep (edited modules / symbols, `llm_pricing`, the harness modules, source scanners of `app/`, the named source-scanning pins, CLAUDE.md readers, migration readers, SmartCompareApp scanners, minus the 4 hook files): the grep added nothing; union + the unit RED file. Importers of the edited test file tests/test_s75_fanout_identity.py (test_s78_tier_fill_residual_guard.py, test_s80_b1.py) and the CLAUDE.md readers test_ci_gates.py / test_behavior_dimension_translation.py are in it. 16 chunks of at most 25 files, bound 1200, one at a time, the 4 NETWORK_FLAKY_EXCLUDE nodes deselected (as at base).
- HEAD totals: 14,268 passed, 4 failed, 2 errors, 41 skipped, 70 deselected, 37 xfailed. Base (RED report): 14,070 passed, 4 failed, 2 errors. +198 = the 197 RED-file nodes + the 050 parametrised node above.
- HEAD failures: tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction, tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities, tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys (the four tests/.pre_impl_failures.txt nodes), tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence and ::test_truth_on_prefix_static_and_cacheable (ERROR, cold tiktoken cache). Identical to the base set. **branch-only-NEW: EMPTY.** Netguard totals equal base: 686 attempts from 200 nodes.
- [pyt] lines (all 16): see `comm/pyt_lines.txt`; summary: 01 32s OK (794 passed) / 02 43s OK (1189 passed, 5 deselected) / 03 63s OK (1033 passed, 1 skipped, 3 deselected) / 04 22s OK (375 passed, 1 skipped, 10 deselected) / 05 105s OK (3017 passed) / 06 39s OK (628 passed, 14 deselected) / 07 16s OK (312 passed) / 08 21s OK (625 passed, 10 deselected) / 09 35s FAIL rc=1 (4 failed, 718 passed, 24 skipped, 7 deselected) / 10 27s FAIL rc=1 (350 passed, 4 skipped, 2 deselected, 1 xfailed, 2 errors) / 11 117s OK (1032 passed) / 12 120s OK (1808 passed, 1 xfailed) / 13 58s OK (625 passed, 2 skipped, 11 deselected) / 14 58s OK (486 passed, 8 deselected) / 15 52s OK (1197 passed, 9 skipped, 35 xfailed) / 16 5s OK (79 passed); each with its [hermeticity] line equal to the node count run.
- Note: the comm run used the RED file with U6's earlier literal (0.0123456789); the only later change is that literal (re-run OFF and ON above, 197/197 each).

## Design notes (own code; the measured prototype was the reference)
- G-1: claims in `_CLAIM_REGISTRY` keyed `(id(openai_ledger), id(llm_records))`, strong references kept in the entry, 256 entries, oldest evicted, one `threading.Lock`. `unclaimed_openai_cost_usd()` is read-only (`_taken_for` never inserts; RG1 pins that it does not over-claim).
- G-2: `LONG_CONTEXT_THRESHOLD_PROMPT_TOKENS = {haiku: 100000, sonnet: 200000}`; above it Haiku uses `HAIKU_LONG_CONTEXT`, Sonnet is None.
- G-3: the unclaimed add is the builder's own try block with the `[LLM-LEDGER] unclaimed failed type=%s -- base value` WARNING.
- G-5: `tracked_call_cost_usd(usage)` returns a float for a claimed priced candidate, else None; the TG's verbatim base lines add the estimate (so ON with no match is bit-identical to base, C3 / C4 / C5).
- TG: a local import (no second scs hunk), `cost = None`, then the flag-first predicate `llm_ledger_v2_enabled() and isinstance(usage, dict)`; the base three lines verbatim under `if cost is None`.
- `merge_llm_summaries` uses the `merge_openai_summaries` cost rule (sum of the non-None); `build_llm_metadata` merges an llm part only when a non-OpenAI record exists (so an all-unpriced OpenAI compare keeps cost None after S81-06 binds an empty llm ledger).
- `/costs/api`: the return dict is bound to `body` and returned after the ON block (no key or value change OFF).

## Deviations
1. Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, not the "Claude Fable 5.1" of the task template: this agent runs on Opus 5.5 and the common brief forbids claiming another model (trailer = the committing agent's own model).
2. U6 row placed at the END of the RED file (append-only, so the prefix hash proves every RED row byte-identical), not next to U1-U5.
3. U6 uses the literal 0.0123456 instead of the RED rows' 0.0123456789 so the added row carries no 8-digit run (the added-line sweep); the RED rows themselves are unchanged and still carry 8-digit numeric literals (0.0123456789, 0.02750005, 0.00031785, the dated id 20261001 and a synthetic UUID), numeric test data, not personal values.
4. Mutation table: M15s not run (equivalent by G-5 on GREEN's None contract); M15 / M52 measured both in the RED shape (killed by TypeError) and in GREEN's shape (M15r / M52r, killed by assertions).
5. `PR_BODY.md` ends with the required robot-emoji line (the one non-ASCII line, outside the repo).
6. Branch name: the task's `feature/s81-s03-llm-ledger-v2` (the spec's OQ-1 suggested `feature/s81-llm-ledger-v2`).

## Open questions for the gate / adversaries
1. G2 survives: add a hygiene PIN for the Sonnet 200,000 boundary (150,000 flat 0.31, 200,000 flat 0.41, 200,001 None)? The gate allows only U6; an adversary must name it.
2. The registry's 256 bound vs in-flight compares (stated limit 14): accept, or size it from UVICORN_LIMIT_CONCURRENCY in a follow-up?

## NOT MEASURED
- Nothing timed out. Not run: the pre-commit hook test files (no .githooks edit, excluded per the brief); a base comm run (the base failure set is the RED report's, as the task instructs); any live system.
