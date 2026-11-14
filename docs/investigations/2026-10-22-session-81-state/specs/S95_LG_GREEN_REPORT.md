# S95-LG URL-WINNER-GUARD: GREEN report (GREEN round, Opus 5.5, 2026-11-14)

VERDICT: BLOCKED (no commit). HEAD stays 731bcddf531a7e123963246168ca19f262859337.

## 1. The blocking evidence (GL-3 vs the frozen RED G2)
- With the GL-3 adapter (scorer on per-product shallow copies with rating / review_count lifted from reviews) the frozen RED file is 21 of 22: tests/test_s95_lg_url_winner_guard.py::test_g2_on_passes_the_scores_summary_and_the_scorer_winner fails at :331 `assert kwargs["scores_summary"] == summary`.
- Cause: the row's expected `summary` comes from `_scorer_view` (:203-209), which runs the REAL scorer on the UNLIFTED written-back products (`compute_scores(copy.deepcopy(products))`, :207). GL-3 makes the guard's scorer read lifted copies, so on the RED fixture (A 4.9 / 900, B 4.1 / 40 nested under reviews) the summary gains the fragrance review / popularity dims: `projection: comparable ... presentation: comparable` -> `projection: stronger ... presentation: stronger` for product A (log red_adapter_g2.log :35-43). The winner stays index 1 (G1, G5 pass).
- Without the adapter (the RED prototype bytes a83844dd...) G7 fails (measured). No adapter consistent with GL-3 keeps the unlifted summary; the RED file is frozen (step 0 sha rule, GL-7 'the frozen RED file'). Per the brief: a gate fails for a reason not fixable inside the five paths without editing the frozen RED file -> BLOCKED.
- [pyt] tag=s95g-g2-red-adapter start=2026-11-14 20:45:57 end=2026-11-14 20:46:00 elapsed=4s bound=600s status=FAIL rc=1 | [hermeticity] sentinel checked 24 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) (1 failed = RED G2, 23 passed)

## 2. Step 0 (base check)
- git rev-parse HEAD = 731bcddf531a7e123963246168ca19f262859337; branch feature/s95-url-winner-guard; status `?? tests/test_s95_lg_url_winner_guard.py` only; RED sha256 7b6aec460c27b91ea832694287e72a0ef4302b7731770248e90b717e401cb537 (match); no .qa-mutation.lock.
- Byte copies in this folder: base_ues.py d235862b... (71862, CRLF), base_role_fix.py 52577c13... (32296, CRLF), base_CLAUDE.md a0788e54... (784105, CRLF), red_file_copy.py 7b6aec46...

## 3. GL-4 TDD (adapter rows written BEFORE the adapter)
- tests/test_s95_lg_url_winner_guard_adapter.py (9096 bytes, LF, ASCII, the RED file's patch idiom; fragrances; equal price 40.0 BHD and equal specs; rating 3.1 / 500 vs 4.8 / 500 nested under reviews):
  - G7 test_g7_on_the_scorer_reads_the_lifted_rating: PRECONDITIONS (no top-level rating / review_count; the real scorer on the RAW products does NOT pick 1; on hand-lifted copies it picks 1); ON, the model picks 0 -> asserts the verdict call's score_winner_index == 1 and the delivered winner_index == 1.
  - G8 test_g8_on_the_delivered_products_stay_unlifted (PIN): ON; the fake extraction hands out the pre-built dicts themselves; no delivered product holds a top-level rating / review_count; each equals its deep copy taken before the call.
- base: [pyt] tag=s95g-g1-adapter-base start=2026-11-14 20:40:56 end=2026-11-14 20:40:59 elapsed=3s bound=600s status=FAIL rc=1 | [hermeticity] sentinel checked 2 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s): G7 FAIL (AssertionError: score_winner_index is None, not 1), G8 PASS
- proto (red/proto.diff applied with the Edit tool; the working copy == red/proto_copy.py, sha a83844dd..., +49/-1): [pyt] tag=s95g-g1-adapter-proto start=2026-11-14 20:44:15 end=2026-11-14 20:44:18 elapsed=3s bound=600s status=FAIL rc=1 | [hermeticity] sentinel checked 2 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s): G7 FAIL (AssertionError: score_winner_index is 0, not 1), G8 PASS

## 4. The GL-3 adapter (in the working tree, uncommitted)
- url_extraction_service.py: `_URL_GUARD_LIFTED_KEYS = (("rating", "rating"), ("review_count", "count"))` and `_url_guard_scorer_inputs(products)` after `url_winner_guard_enabled()`: one SHALLOW `dict(product)` per product; a top-level key that is absent or None takes `reviews[nested]` when `reviews` is a dict and the nested value is not None; nothing else is lifted (fact_check absent). The scorer step calls `guard_service.compute_scores(_url_guard_scorer_inputs(products))`; names from `_display_product_names(products)`; summary, verdict kwargs, tradeoffs and reconcile read that one scoring_result. Delivered `products` untouched. Otherwise the RED prototype shape (proto.diff) unchanged. File 75965 bytes, CRLF 1643, bare LF 0, sha 8eca4929628cf8e9b6513d53bfb43d20fd3470461e49d6b579345b6787a6c27d; numstat +75 / -1; added lines 0 non-ASCII bytes.
- With the adapter: G7 PASS, G8 PASS, RED 21 of 22 (G2, section 1).

## 5. Candidate A for the gate: a one-line pin-fix of RED G2 (MEASURED in place, then restored)
- Edit (red_g2_pinfix_candidate.diff, candidate sha 24ed90c0278482bc0296b2cdf825c3be5a3542400efaaecfe3e9140868746027): `_scorer_view` :207 `result = service.compute_scores(copy.deepcopy(products))` -> `result = service.compute_scores([dict(p, rating=p["reviews"]["rating"], review_count=p["reviews"]["count"]) for p in copy.deepcopy(products)])` (an in-test lift, no reference to the unit's helper, so no import / attribute error at base). It feeds the preconditions of G1 / G2 / G5 / P2 and G2's expected summary.
- Under W/.qa-mutation.lock (agent s95lg-green), RED byte copy first:
  - GREEN module bytes: [pyt] tag=s95g-m-candA-green start=2026-11-14 20:47:57 end=2026-11-14 20:48:00 elapsed=3s bound=600s status=OK rc=0 | [hermeticity] sentinel checked 24 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s): 24 passed (RED 22 + adapter 2)
  - base module bytes d235862b: [pyt] tag=s95g-m-candA-base start=2026-11-14 20:49:11 end=2026-11-14 20:49:15 elapsed=4s bound=600s status=FAIL rc=1 | [hermeticity] sentinel checked 24 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s): 15 failed (the 14 RED rows G1, G2, G3, G5, G6 x10 + G7), 9 passed (G4, P1 x4, P2 x3, G8); every failure an AssertionError (the RED-at-base profile 14 / 8 is kept).
- Restored: RED 7b6aec46... match=True; module 8eca4929... match=True; lock removed.
- Option B (alternative): drop GL-3 (L-1 stays a stated limit); the RED prototype bytes a83844dd... are 22 of 22 and the RED round's proto comm record covers them; the adapter file is then not committed (G7 is red there by design).

## 6. Mutants (byte copy, one exact edit, restore + sha after each; all AssertionError)
| id | edit | result |
|---|---|---|
| M7 | no lift (= the RED prototype bytes) | KILLED by G7 (s95g-g1-adapter-proto) |
| M8 | `view = dict(product)` -> `view = product` (the lift writes the delivered dicts) | KILLED by G8 ('delivered product 0 holds a top-level rating') |
| E1-M1 | the call gains `score_winner_index=None` beside `**verdict_kwargs` | KILLED by test_v09 (keyword list) |
| E1-M2 | `if guard_scoring is not None or True:` around the keys | KILLED by test_v09 (keys outside the guard branch, line 1510) |
| E1-M3 | `if True:` for the predicate | KILLED by test_v09 (guard_scoring set outside the predicate branch, line 1504) |
- [pyt] tag=s95g-m-mutM8 start=2026-11-14 20:49:27 end=2026-11-14 20:49:30 elapsed=3s bound=600s status=FAIL rc=1 | [hermeticity] sentinel checked 2 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-m-e1-m1 start=2026-11-14 20:52:01 end=2026-11-14 20:52:04 elapsed=4s bound=600s status=FAIL rc=1 | [hermeticity] sentinel checked 1 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-m-e1-m2 start=2026-11-14 20:52:05 end=2026-11-14 20:52:09 elapsed=4s bound=600s status=FAIL rc=1 | [hermeticity] sentinel checked 1 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-m-e1-m3 start=2026-11-14 20:53:10 end=2026-11-14 20:53:13 elapsed=4s bound=600s status=FAIL rc=1 | [hermeticity] sentinel checked 1 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s)

## 7. E1 (GL-2) in tests/test_s81_s07c_role_fix.py (uncommitted)
- test_v09_url_caller_unchanged keeps its name; the docstring names S95-LG and the superseded V4 ruling. Asserts: module-wide exactly one generate_comparison call, and it is the one inside compare_from_urls; args products[0], products[1], region; keywords [("category", "category_used"), (None, "verdict_kwargs")]; the only read of verdict_kwargs is that `**`; its first binding is a top-level statement of the function bound to an empty dict literal; every later binding is a dict literal with exactly the constant keys scores_summary / score_winner_index inside the BODY of `if guard_scoring is not None:`; guard_scoring is first bound top-level to None and set to anything but None only inside the BODY of `if url_winner_guard_enabled():`. Helpers `_v09_inside_if_body`, `_v09_store_statements` (any non-plain binding form fails the pin).
- File 36564 bytes, CRLF 692, bare LF 0, sha 3a67f2140125303b788a813fac6eb915010ed5ed1b6a2a60c46e5f7b006671d2; numstat +71 / -4; 0 non-ASCII added bytes.
- [pyt] tag=s95g-g3-rolefix start=2026-11-14 20:51:33 end=2026-11-14 20:51:38 elapsed=5s bound=600s status=OK rc=0 | [hermeticity] sentinel checked 17 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s): 17 passed

## 8. CLAUDE.md (GL-5, uncommitted)
- claude_md_insert.py: read the bytes (sha a0788e54 checked), ONE anchor `

## Tests
`, the line before the blank = the S81-07c owner-steps line, inserted at byte 577744 (the start of `## Tests`): 9 block lines + 1 blank line, 4925 bytes, ASCII, CRLF; proof new[:pos] == old[:pos] and new[pos+len:] == old[pos:]; 784105 -> 789030 bytes, sha 7110ee480f53d7668ef1cc4cd3b35b8a90264f413728721f5e13bf3daebd0256; CRLF 1146 -> 1156, bare LF 0; numstat +10 / -0; one hunk @@ -683,0 +684,10 @@. Block text: claude_md_block.txt.
- Heading `**SESSION 81 follow-up unit (S95-LG URL-WINNER-GUARD, 2026-11-14; ...)**`; bullets: Why, ON (the lift, the summary + score_winner_index through the S81-07c path, the reconcile after a delivered verdict), failure arms, OFF byte-identical (P1), tests + E1, canary + rollback (spec 8, with the RED Q-4 precision: on a mismatch row with ENABLE_WINNER_PROSE_RECONCILE unset the declaration ships empty), stated limits L-1..L-4, owner steps.

## 9. Lint
- ruff 0.16.5 `check --select E9,F63,F7,F82 --no-cache` on the module, the adapter file, the role-fix file and the RED file: All checks passed; py_compile rc 0 (same four files).

## 10. Units and the comm set at the GREEN working tree (uncommitted, HEAD 731bcddf + the edits)
- [pyt] tag=s95g-g6-units start=2026-11-14 20:55:51 end=2026-11-14 20:55:58 elapsed=6s bound=1200s status=FAIL rc=1 | [hermeticity] sentinel checked 41 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s): 1 failed (RED G2), 40 passed (RED 21 + adapter 2 + role-fix 17)
- Comm set (GL-6): the 135 files of red/comm_set.txt (sha 306abcc2...) in the RED chunks, chunk 5 + the adapter file = 136 files; the RED base record REUSED (LC-6).
  - [pyt] tag=s95g-g6-ch0 start=2026-11-14 20:56:10 end=2026-11-14 20:56:45 elapsed=36s bound=1200s status=OK rc=0 | [hermeticity] sentinel checked 765 test(s) | [netguard] blocked 9 attempt(s) from 3 node(s): 764 passed, 1 skipped, 2 deselected
  - [pyt] tag=s95g-g6-ch1 start=2026-11-14 20:56:55 end=2026-11-14 20:58:31 elapsed=96s bound=1200s status=OK rc=0 | [hermeticity] sentinel checked 867 test(s) | [netguard] blocked 169 attempt(s) from 39 node(s): 867 passed
  - [pyt] tag=s95g-g6-ch2 start=2026-11-14 20:59:13 end=2026-11-14 21:01:16 elapsed=124s bound=1200s status=FAIL rc=1 | [hermeticity] sentinel checked 3007 test(s) | [netguard] blocked 27 attempt(s) from 3 node(s): 3004 passed, 2 skipped, 1 xfailed, 2 ERROR (the two cold-tiktoken test_prompt_truth nodes)
  - [pyt] tag=s95g-g6-ch3 start=2026-11-14 21:01:28 end=2026-11-14 21:03:34 elapsed=126s bound=1200s status=FAIL rc=1 | [hermeticity] sentinel checked 2633 test(s) | [netguard] blocked 24 attempt(s) from 9 node(s): 2626 passed, 7 FAILED (the base CRLF / ASCII byte checks)
  - [pyt] tag=s95g-g6-ch4 start=2026-11-14 21:04:22 end=2026-11-14 21:05:32 elapsed=70s bound=1200s status=OK rc=0 | [hermeticity] sentinel checked 1074 test(s) | [netguard] blocked 73 attempt(s) from 25 node(s): 1073 passed, 1 xfailed
  - [pyt] tag=s95g-g6-ch5 start=2026-11-14 21:05:41 end=2026-11-14 21:05:59 elapsed=18s bound=1200s status=OK rc=0 | [hermeticity] sentinel checked 626 test(s) | [netguard] blocked 20 attempt(s) from 12 node(s): 626 passed (624 + G7 + G8)
  - HEAD failing set (head_record.txt) = the 9 ids of red/base_record.txt exactly: comm -13 EMPTY (no NEW failure), comm -23 EMPTY. E1 is green (proto had it red: proto cp3 8 FAILED, HEAD 7). netguard counts per chunk identical to base.

## 11. The five paths (working tree; NOTHING committed; blob = git hash-object, i.e. the would-be LF index blob)
| path | bytes | sha256 | blob | state |
|---|---|---|---|---|
| app/services/url_extraction_service.py | 75965 | 8eca4929628cf8e9b6513d53bfb43d20fd3470461e49d6b579345b6787a6c27d | cb217967764570857fa3ac3e1a6923ad3cbf4ec0 | M (proto + GL-3 adapter) |
| tests/test_s95_lg_url_winner_guard.py | 19607 | 7b6aec460c27b91ea832694287e72a0ef4302b7731770248e90b717e401cb537 | 3e9d247fd2492f6e892d2f47855a4d4b96c5ea8e | ?? frozen, untouched |
| tests/test_s95_lg_url_winner_guard_adapter.py | 9096 | d5b801985f0219e96a72ec0c218ea1274d84116e0c0d686e6f6d0295c97d59a4 | 159dcd400905ea45cc3ad943cb76980ac3c0d057 | ?? new (G7, G8) |
| tests/test_s81_s07c_role_fix.py | 36564 | 3a67f2140125303b788a813fac6eb915010ed5ed1b6a2a60c46e5f7b006671d2 | c34925fb14d3e5bece61a5473511008ceaad239b | M (E1) |
| CLAUDE.md | 789030 | 7110ee480f53d7668ef1cc4cd3b35b8a90264f413728721f5e13bf3daebd0256 | 61ff73c2d8f3fd78f87d6081b202f5849170723d | M (+10 lines) |
- green_tracked.diff (git diff of the three tracked files, 17826 bytes, sha 08c24ac8...) and red_g2_pinfix_candidate.diff in this folder.

## 12. Deviations
- D1: NO commit (step 7 not run, no hook output): BLOCKED per section 1. The working tree is left at the GREEN candidate (not reverted) so a ruling can continue from it; every byte is listed in section 11.
- D2: extra measurements beyond the procedure, to give the gate a measured choice: candidate A in place on the frozen RED file under the mutation lock (byte copy, one edit, restore, sha match) and five mutants (M7, M8, E1-M1..M3).
- D3: G7 carries a second PRECONDITION beyond the gate's words (the real scorer on hand-lifted copies picks 1), so a scorer change fails the row with a fixture message, not a misleading one.
- D4: the Feature Flags pointer paragraph (the ':341 clause' where earlier units add one sentence per unit) gained NO ENABLE_URL_WINNER_GUARD sentence: GL-5 says one block and GL-8 'a pure addition'. Rule it if the sentence is wanted.
- D5: CLAUDE.md L-1 is worded as measured, not as spec 9 L-1: an exact scorer tie resolves to index 0 (argmax; measured at proto on the G7 pair: equal price / specs and no rating -> score_winner_index 0), so only a None scorer winner leaves the model's pick.
- D6: the canary item of spec 8 'the declaration names the shipped winner' is written as RED Q-4 suggested: on agreement rows; on a mismatch row with ENABLE_WINNER_PROSE_RECONCILE unset the declaration ships empty.

## 13. Questions for the gate
- Q-A (blocking): rule G2. Option A = the measured one-line RED pin-fix (section 5: 22 of 22 at the GREEN bytes, the RED-at-base profile kept), committed as the RED file's new blob with the other four paths as they stand (their gates are already green: section 10). Option B = drop GL-3 (the module back to a83844dd..., the adapter file dropped, the CLAUDE.md ON / L-1 wording re-cut; the RED proto comm record holds).
- Q-B: the tie (D5) also reaches the prompt: on a tied link pair ON tells the model 'the deterministic scoring picked PRODUCT 1' (the text path does the same). Accept as a stated limit, or a forward unit (no fixed winner below a margin).
- Q-C: the RED Q-2 coverage gaps stay unpinned (the reconcile-failure arm, LLMUnavailableError under ON, the None scorer winner, the predicate read order); G7 / G8 cover the lift only.

## 14. NOT MEASURED
- The commit, the pre-commit hook output, git show --stat HEAD (BLOCKED before step 7).
- The client jest fences (no client-read literal moved; not run in this round).
- Candidate A's comm set: not needed (the RED file is not a comm member; section 10 holds for the other four paths).
- No live, network, Railway or provider measurement.

## 15. git -C W status --short (end)
```
 M CLAUDE.md
 M app/services/url_extraction_service.py
 M tests/test_s81_s07c_role_fix.py
?? tests/test_s95_lg_url_winner_guard.py
?? tests/test_s95_lg_url_winner_guard_adapter.py
```
HEAD 731bcddf531a7e123963246168ca19f262859337 (unmoved); no .qa-mutation.lock; the RED file at its frozen sha.
