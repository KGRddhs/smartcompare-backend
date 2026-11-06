# S81-22 FIX ROUND 1 REPORT (fix agent, Opus 5.5, 2026-11-06)

Unit S81-22 COMPARE-RUNS + capped judge, fix round 1 per specs/RULINGS_FIX1_S81_22.md. Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s22, branch feature/s81-s22-compare-runs. Start HEAD 0d588d0b52a6532359a051d85ae89698e452cd63 (verified; git status --short empty; GC-1 shas c1cb9375... / 39a46d1c... re-hashed equal). NEW HEAD c22ff9c03ccb39273c32bdb190f72607b6ad9fb5 (ONE commit through the hook, "All checks passed!"; no push, no PR, no rebase). Written through the shell (python), not the Write tool's report path.

## 1. Amended frozen rows (ruled pin-fix) and the new RED shas

tests/test_s81_s22_judge.py, line numbers at c22ff9c0:
- test_j09_batch_body_deidentified :626-627 custom ids == "r" + sha256(run id)[:16] over the sorted run ids (was ["r0001", "r0002"]) [F1-3]
- test_j09_batch_body_deidentified :636 key set without "temperature"; :637 `"temperature" not in p` (was `p["temperature"] == 0`) [F1-2, the ruled J09 amendment]
- test_j11_g2_spend_sequence :667-668 the want sequence gains ("db.upsert", "compare_judgements") right after ("batches.create", 3) [F1-3: the markers before the poll; DEVIATION D1: not named in the rulings, forced by "markers upserted IMMEDIATELY after batches.create"]
- test_j14_partial_read_no_ledger_no_delete :739 `[r for r in _upserts(fc, "haiku") if r["flags"] != ["batch_pending"]] == []` (was `_upserts(fc, "haiku") == []`) [F1-3, D1]
- test_j14c_resume_first :782-783 the pre-fed results carry the hashed ids (was r0001 / r0002) [F1-3, the ruled J14c amendment]
- test_j15_parse_failure :854 and test_j15b_note_cut_and_escaped :866 read the haiku rows without the batch_pending markers [F1-3, D1]
No frozen row pinned maxItems / maxLength / pattern (grep of all three S22 test files); their ABSENCE is asserted by the new row test_jf1_2. Nothing else in the frozen files changed (git diff -U0: 7 hunks at the lines above + the appended section).

New sha256 (supersede GATE_S81_22 GC-1):
- tests/test_s81_s22_judge.py b7c2c377e4c6b8c5b0db77dc16a746963b16f6f765910275c60df436577d8430
- tests/test_s81_s22_compare_runs.py db13c005e04f3e9986190a538f6baa77ddaa587178ab1677f8399360922000eb
- tests/test_s81_s22_gate_rows.py 6ad6b7eac8a7aa35c54d4586428b685f7a623d95711e696afe2e0b661b4c6d06
(blob == disk for each; LF, ASCII.)

## 2. RED step (new rows; HEAD code 0d588d0b)

Appended: judge J-F1-1 test_jf1_1_escalation_params_mirror_router, J-F1-2 test_jf1_2_batch_params_follow_g2_and_caps_in_code, J-F1-3a test_jf1_3a_resume_maps_by_hashed_id, J-F1-3b test_jf1_3b_markers_right_after_create, J-F1-3c test_jf1_3c_cancel_only_on_total_marker_failure; compare_runs R-F1-4 test_rf1_4_field_status_capped; gate rows G22-GR4 test_g22_gr4_dry_resume_writes_nothing, G22-GR5 test_g22_gr5_sample_boundary_not_sampled.
- [pyt] tag=s22f1-red-all start=2026-11-06 18:58:24 end=2026-11-06 18:58:35 elapsed=12s bound=600s status=FAIL rc=1 ; 10 failed, 199 passed ; [hermeticity] sentinel checked 209 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
- The 10 failures, every one an AssertionError (log lines E AssertionError ... / file:line: AssertionError): j09 (positional ids), j11 (no marker step), j14c[ended] (positional resume), jf1_1, jf1_2, jf1_3a, jf1_3b, jf1_3c, rf1_4, g22_gr4. Every other row green: 199 = the 201 prior nodes minus the 3 red amended nodes (j09, j11, j14c[ended]) plus the green G22-GR5; the amended j14 / j15 x4 / j15b / j14c[running|lost] green at HEAD.
- G22-GR5 is a prove-nothing row (green at HEAD); it is RED-then-green on its byte-copy mutant O09 (mut13 below). G22-GR4 is red at HEAD (resume.filled == 0 with hashed ids) and also kills O07 (mut12).

## 3. GREEN step

scripts/cron_compare_judge.py (LF, ASCII; sha256 0c2bf368bfae26b3f0ebc5a7a1294dc844cb06a2469d0ab03114ba41658ff2ea):
- F1-1 `_escalate`: `req["params"] = lr._escalation_request(req["params"])` (the router function itself: the escalation model from model_config, thinking between_tools; the batch params carry no temperature since F1-2); lazy `from app.services import llm_router as lr`; the loop keys the request on run["id"].
- F1-2 `build_request(run_id, evidence, model)`: no "temperature"; `JUDGE_SCHEMA` flags = {"type": "array", "items": {"type": "string"}}, note = {"type": "string"}; `FLAGS_MAX = 8`; `_valid_answer` returns (verdicts, flags[:8], note[:300] rendered, capped); a flag off `_FLAG_RX` stays unparsed; `batch.answer_capped` / `escalation.answer_capped` count capped answers.
- F1-3 `custom_id(run_id)` = "r" + sha256(str(run_id))[:16]; `_resume` builds by_cid by recomputation; `_read_results(..., where)` counts an unknown id in `<where>.unmatched` and ignores it; `_write_markers` upserts the batch_pending markers right after `batches.create` (chunked by WRITE_BATCH, ERROR `%s batch marker write failed (%s)` + `batch.markers_failed` per failed chunk, `batch.markers_written`); zero written -> `ac.messages.batches.cancel(batch_id)` (`batch.cancelled`; a cancel failure is an ERROR + counted), settle(ticket, None) when a ticket is held, return before any poll; the timeout path no longer appends markers (already written). New report keys live inside batch / resume / escalation (the top-level key set is pinned by J22: DEVIATION D2, the ruled names `markers.failed` / `answer.capped` are spelled `batch.markers_failed` / `batch.answer_capped` / `escalation.answer_capped`).
app/services/compare_runs.py (LF; sha256 0605ee62fb4b88609f672bd3e9b6d745f3207c88d671494cab3fba72d820bd31): F1-4 `FIELD_STATUS_MAX_BYTES = 16384`; `_field_status` returns {"truncated": True} when json.dumps(fs, ensure_ascii=True, sort_keys=True, default=str) exceeds it (or cannot serialize). Runs only inside build_run_row (flag ON); flag OFF untouched.
- ruff --select E9,F63,F7,F82 on the 5 files: All checks passed!; py_compile clean.
- [pyt] tag=s22f1-green-off start=2026-11-06 18:59:56 end=2026-11-06 19:00:07 elapsed=10s bound=600s status=OK rc=0 ; 209 passed ; [hermeticity] 209 ; [netguard] blocked 0
- [pyt] tag=s22f1-green-on (ENABLE_COMPARE_RUN_LEDGER=true ENABLE_BATCH_JUDGE=apply in the runner env only) start=2026-11-06 19:00:07 end=2026-11-06 19:00:17 elapsed=10s bound=600s status=OK rc=0 ; 209 passed ; [hermeticity] 209 ; [netguard] blocked 0

## 4. Mutants (byte copies, .qa-mutation.lock held and removed, restore sha-verified after each; 14 / 14 KILLED by AssertionError, nonassert E lines 0)

- s22f1-mut00 | MF1-1a escalation keeps the batch params | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut00 start=2026-11-06 19:00:49 end=2026-11-06 19:00:54 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_jf1_1_escalation_params_mirror_router
- s22f1-mut01 | MF1-1b escalation sends temperature 0 | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut01 start=2026-11-06 19:00:55 end=2026-11-06 19:01:00 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_jf1_1_escalation_params_mirror_router
- s22f1-mut02 | MF1-2a batch temperature restored | KILLED | killing=2 nonassert_E=0 | [pyt] tag=s22f1-mut02 start=2026-11-06 19:01:01 end=2026-11-06 19:01:06 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_j09_batch_body_deidentified - Assert...
    FAILED tests/test_s81_s22_judge.py::test_jf1_2_batch_params_follow_g2_and_caps_in_code
- s22f1-mut03 | MF1-2b schema maxItems restored | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut03 start=2026-11-06 19:01:07 end=2026-11-06 19:01:12 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_jf1_2_batch_params_follow_g2_and_caps_in_code
- s22f1-mut04 | MF1-2c flags cap removed | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut04 start=2026-11-06 19:01:13 end=2026-11-06 19:01:18 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_jf1_2_batch_params_follow_g2_and_caps_in_code
- s22f1-mut05 | MF1-2d capped counter dropped | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut05 start=2026-11-06 19:01:19 end=2026-11-06 19:01:24 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_jf1_2_batch_params_follow_g2_and_caps_in_code
- s22f1-mut06 | MF1-3a resume positional ids | KILLED | killing=3 nonassert_E=0 | [pyt] tag=s22f1-mut06 start=2026-11-06 19:01:25 end=2026-11-06 19:01:30 elapsed=6s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_j14c_resume_first[ended] - Assertion...
    FAILED tests/test_s81_s22_judge.py::test_jf1_3a_resume_maps_by_hashed_id - As...
    FAILED tests/test_s81_s22_gate_rows.py::test_g22_gr4_dry_resume_writes_nothing
- s22f1-mut07 | MF1-3b no marker before the poll | KILLED | killing=3 nonassert_E=0 | [pyt] tag=s22f1-mut07 start=2026-11-06 19:01:31 end=2026-11-06 19:01:36 elapsed=6s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_j11_g2_spend_sequence - AssertionErr...
    FAILED tests/test_s81_s22_judge.py::test_j14b_pending_on_timeout - AssertionE...
    FAILED tests/test_s81_s22_judge.py::test_jf1_3b_markers_right_after_create - ...
- s22f1-mut08 | MF1-3c cancel arm removed | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut08 start=2026-11-06 19:01:37 end=2026-11-06 19:01:43 elapsed=6s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_jf1_3c_cancel_only_on_total_marker_failure
- s22f1-mut09 | MF1-3d cancel on a partial marker failure | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut09 start=2026-11-06 19:01:43 end=2026-11-06 19:01:49 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_jf1_3c_cancel_only_on_total_marker_failure
- s22f1-mut10 | MF1-3e orphan answer not counted | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut10 start=2026-11-06 19:01:49 end=2026-11-06 19:01:55 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_judge.py::test_jf1_3a_resume_maps_by_hashed_id - as...
- s22f1-mut11 | MF1-4 field_status cap off | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut11 start=2026-11-06 19:01:55 end=2026-11-06 19:02:01 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_compare_runs.py::test_rf1_4_field_status_capped - A...
- s22f1-mut12 | O07 DRY resume writes the ledger | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut12 start=2026-11-06 19:02:01 end=2026-11-06 19:02:07 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_gate_rows.py::test_g22_gr4_dry_resume_writes_nothing
- s22f1-mut13 | O09 sample boundary <= | KILLED | killing=1 nonassert_E=0 | [pyt] tag=s22f1-mut13 start=2026-11-06 19:02:07 end=2026-11-06 19:02:12 elapsed=5s bound=600s status=FAIL rc=1
    FAILED tests/test_s81_s22_gate_rows.py::test_g22_gr5_sample_boundary_not_sampled

## 5. F1-6: 048 on a throwaway local PostgreSQL 18.1 cluster (MEASURED)

Script S81-22_fix1/f16.py; outputs S81-22_fix1/f16/f16_outputs.txt (run 2) and f16_outputs_run1.txt (run 1). Port 54398, initdb --auth=trust, listen localhost only; synthetic rows only; the synthetic database dropped and the cluster stopped at the end (the stopped data dirs pgdata / pgdata2 stay under S81-22_fix1/f16/: the brief forbids a recursive delete; the SF1 G9 precedent). Order: a mimic schema (roles anon / authenticated / service_role, the 13 043 tables with the 043 users columns, a 025-style delete_user_cascade + the 037 GRANT to service_role) -> the session-71 APPLY_043_2_ONE_PASTE.sql -> migrations/045_kb_core.sql -> the GREEN APPLY_048_2_ONE_PASTE.sql.
Run 2 (service_role BYPASSRLS, the Supabase form): 50 lines, 0 unexpected:
- 043 apply PASS; 045 apply PASS; 048 apply PASS; objects: compare_runs | compare_judgements | compare_runs_prune(integer) | kb_feedback
- delete_user_cascade md5 (LF text): after 043 91ca0b32dc008b2504d184452d9c3c92 (len 2364 raw: the CRLF paste working copy carries CR), after 048 767cff1bf5a5a654492c56a3499cde50 (has_kb_hook t)
- re-apply the one-paste AND migrations/048_compare_runs.sql: rc=0, NOTICE "already exists, skipping" only (idempotent, no raise)
- guard probe 1 (ADD COLUMN s22_extra to compare_runs): rc=3 ERROR "048 guard: compare_runs exists with a different column set" (PASS); undo
- guard probe 2 (DROP compare_judgements.note): rc=3 ERROR "048 guard: compare_judgements exists with a different column set" (PASS); undo; 048 applies again
- hook: before fb_linked_u1 1 | fb_u2 1 | fb_unlinked 1 | run_r1 1 | cmp_null f | r1_judgements 1 | cmp_c1 1 | cmp_c2 1 ; delete_user_cascade(U1) as service_role ; after 0 | 1 | 1 | 1 | t | 1 | 0 | 1 (the linked kb_feedback row deleted; the other account's and the unlinked one survive; the run survives with comparison_id NULL, its judgement kept)
- privileges: anon_exec f | auth_exec f | anon_runs f | sr_runs t
- compare_runs_prune(365) as service_role = 1 (the 400-day synthetic run)
- rollback migrations/rollback/048_compare_runs.sql PASS; objects after: compare_runs / compare_judgements / compare_runs_prune all NULL, kb_feedback kept; delete_user_cascade md5 91ca0b32... = the 043 body (VERDICT YES); re-apply 048 after the rollback PASS.
Run 1 (service_role WITHOUT BYPASSRLS): identical except compare_runs_prune(365) = 0 (RLS on, no policy, the prune is SECURITY INVOKER) and the raw-md5 verdict NO (CR in the 043 paste body only; the LF text equal). Finding (no defect in 048; no STOP): the prune relies on the service role's BYPASSRLS (true on Supabase); a CRLF paste of 043 stores CR in prosrc, and the 048 rollback restores the LF text (semantically identical). APPLY_048 files unchanged. G22-GR2 stays a text pin (stated).

## 6. The comm set (touched importers + walkers + CLAUDE.md readers + source-scanning pins) and the CI-order set

Set: S81-22_fix1/fix_set.txt, 54 files (the 3 S22 files + test_s81_kb_schema + test_s81_s05_request_context + the scripts/app glob walkers + the six CLAUDE.md readers by the import graph + the source-scanning pins + the 19 CI-order files); 51 of them in the stored record e701a8ba... (726 files, which stands, F1-8), the 3 S22 files HEAD-only. Run on the final bytes (after the CLAUDE.md edit), chunks <= 25, bound 1200:
- [pyt] tag=s22f1-comm-c00 start=2026-11-06 19:06:07 end=2026-11-06 19:08:34 elapsed=147s bound=1200s status=FAIL rc=1 ; 1498 passed, 2 skipped, 1 xfailed, 2 errors (the two cold-tiktoken test_prompt_truth ERRORs) ; [hermeticity] sentinel checked 1501 test(s) ; [netguard] blocked 24 attempt(s) from 23 node(s) (the hermeticity pins' own probes + the neutralized supabase sentinel)
- [pyt] tag=s22f1-comm-c01 start=2026-11-06 19:09:40 end=2026-11-06 19:11:15 elapsed=95s bound=1200s status=FAIL rc=1 ; 6 failed (s10 r06 + s16 r27 x5, the CRLF class), 3130 passed ; [hermeticity] 3136 ; [netguard] blocked 60 attempt(s) from 17 node(s)
- [pyt] tag=s22f1-comm-c02 start=2026-11-06 19:25:26 end=2026-11-06 19:25:38 elapsed=12s bound=1200s status=OK rc=0 ; 264 passed ; [hermeticity] 264 ; [netguard] blocked 0 (waited ~14 min for the SF1 lane's live pytest; never killed)
- HEAD FAILED (8) vs the record's ids of the same 51 files (8): comm -13 EMPTY, comm -23 EMPTY.
- [pyt] tag=s22f1-ciorder start=2026-11-06 19:26:06 end=2026-11-06 19:26:57 elapsed=50s bound=1200s status=FAIL rc=1 ; 1 failed (r06), 1768 passed, 2 errors (tiktoken) = GREEN's numbers and the base noise.
Not run (rulings): the hook test files tests/test_precommit_hook*.py (no .githooks change); the FULL jest (LC-7); the corpus gate and the fourteen client fences (F1-8).

## 7. Documentation

- CLAUDE.md (CRLF kept: 1064 CRLF before and after; additions ASCII; sha256 63623b33561b8cd6b1943c2cc8123f42aab83f4bf6021e6e2bfb26b1cfef8625): the S81-22 block edited IN PLACE (5 lines): header (198 RED nodes, the fix-round rulings, the amended rows, G22-GR1..GR5); ENABLE_COMPARE_RUN_LEDGER (the field_status cap; m6 softened; L-I2I6 + S81-22d); ENABLE_BATCH_JUDGE (step 4: hashed ids, the G2 form, no temperature, the schema without the three keywords, the caps in code, the markers before the poll, the cancel, the recomputed resume; step 5: the router's escalation form, ONE escalation ledger row per cron run; step 7: the report key names supersede spec 2.12; stated limits L-VERDICT / L-POSTFLIP widened, L-API, L-MARKER, the autocrlf note); the migration bullet (the F1-6 measurement); owner steps (S81-22d before step 4; JUDGE_ESCALATION_MAX_PER_DAY=0 the off switch, a 0 USD knob maps to the default: kb_seed_common.float_knob `<= 0 -> default`, int_knob admits 0 when low == 0).
- PR body re-cut: S81-22_fix1/PR_BODY.md, 18,684 bytes (<= 25,600), sha256 d6c3cd414a3ddec55e24222f14a796070a47c7e556f5652554491674d47894dc; the attribution line is the ONE non-ASCII line (privacy m5); HEAD c22ff9c0 named.

## 8. Hygiene

Every touched code / test file LF with 0 bytes > 127; added lines (382): no @gmail / +973 / 8-digit run / 64-hex / sk- / eyJ / AKIA / xox / PEM / credentialed URL; no non-ASCII added line; new constant names FIELD_STATUS_MAX_BYTES / FLAGS_MAX carry no gitleaks keyword; no .env read, no flag or knob in a local .env or the OS environment (flag states only in the runner env); no network beyond the localhost cluster; no git write in another worktree; no package manager.

## 9. Deviations

- D1: test_j11 / test_j14 / test_j15 / test_j15b amended although the rulings name only J09 and J14c: the ruled F1-3 marker timing (an upsert between batches.create and the first poll) breaks J11's exact sequence and the three rows that read every haiku upsert; each amendment is the minimal form (the marker step added to J11's want; the three reads filter the batch_pending markers), listed in section 1 for the re-verifier.
- D2: the ruled report names `markers.failed` / `answer.capped` are spelled `batch.markers_failed` (+ `batch.markers_written`, `batch.cancelled`) and `batch.answer_capped` / `escalation.answer_capped` (J22 pins the top-level key set); `resume.unmatched` as ruled (+ `batch.unmatched` for the fresh batch).
- D3: F1-1 calls `llm_router._escalation_request` directly (a private router function, lazily imported) instead of re-implementing it, so the mirror cannot drift; J-F1-1 compares the sent params with that function's output.
- D4: on a total marker failure the reservation is settled with None (the partial-read form) and the batch is cancelled; a cancelled batch writes no ledger row (any requests it processed before the cancel are unrecorded: stated in L-MARKER).

## 10. Open questions for the gate

- Q1: an errored batch request (result type != succeeded) now keeps its batch_pending marker; the batch is deleted after a complete read, so the next resume sees a 404 and marks the run batch_lost (never re-batched, consistent with R-S22-34; at 0d588d0b such a run had no haiku row and was re-batched the next night). Accept as stated (L-MARKER) or rule a terminal flag in the same upsert?
- Q2: the D1 amendments of J11 / J14 / J15 / J15b need the orchestrator's acceptance as part of the F1-3 pin-fix.

## 11. NOT MEASURED

Nothing ruled for this round is NOT MEASURED. Not probed by design: the live Anthropic API (L-API).

## 12. Files

Edited (committed in c22ff9c0): CLAUDE.md; app/services/compare_runs.py; scripts/cron_compare_judge.py; tests/test_s81_s22_compare_runs.py; tests/test_s81_s22_gate_rows.py; tests/test_s81_s22_judge.py (shas above). Byte copies before the round: S81-22_fix1_before/ (CLAUDE.md f713d6ab..., compare_runs 3113b7af..., judge script 7a917293..., RED c1cb9375... / 39a46d1c..., gate rows 6f5463b9...). Notes: S81-22_fix1/ (run.py, green_patch.py, mutate.py, mutants.txt, f16.py, f16/, claude_edit.py, pr_edit.py, PR_BODY.md, fix_set.txt, head_failed.txt, base_ids_in_set.txt, logs/).

git status --short (worktree, after the commit): empty.
