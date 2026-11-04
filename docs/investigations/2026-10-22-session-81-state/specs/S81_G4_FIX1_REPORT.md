# S81-G4 FIX ROUND 1 REPORT (fix agent, Claude Opus 5.5, 2026-11-04)

Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g4, branch feature/s81-g4-kb-serve, base 0b19de5bcc1416111d48bc725359b95151a658ca.
HEAD (commit 2) = ded9a8df5da0ad120a9df242076b89514b066b9d. Scope TEST + DOCS ONLY: no app/, scripts/, migrations/, .githooks/, SmartCompareApp/ or .github/ byte changed vs the GREEN table.

## 1. Starting state (verified)
- HEAD 0b19de5b; `git diff --cached --name-only` = the 19 GREEN paths (12 A + 7 M); `git diff` empty; `git status --short` = exactly those 19 lines.
- 19 / 19 sha256 equal to S81-G4_green/files_sha.json (sha256_after). Byte copy of the frozen D16 file (and the other frozen files, the GREEN CLAUDE.md) kept at S81-G4_fix1/frozen_before/.

## 2. E-G4-1 (F1-1)
Exactly two changed lines (python line diff against the frozen byte copy), LF kept, 0 CR, 0 bytes > 127; each line differs only in the identifier:
```
53 : OPENAPI_PATHS_SHA256 = "9dbd...9809"  # 76 paths at 0b19de5b  ->  SCHEMA_PATHSET_SHA256 = (same value, same comment)
597:             assert digest == OPENAPI_PATHS_SHA256, (len(paths), digest)  ->  assert digest == SCHEMA_PATHSET_SHA256, (len(paths), digest)
```
- tests/test_s81_d16_operator_ingest.py: 65d01860... -> **1bb5214636e868ef53e026bbc89a8fea8554fb011aefe20f41ac1d95b232aceb** (for the GC-1 amendment).
- The other four frozen files re-hashed first and last, unchanged: s18 7be2ed3a..., golden 8ab15ee0..., s19 a400b679..., d17 03b7ccf6....

## 3. Commits (F1-2), both through the hook, never --no-verify
- Commit 1 = 48a82a5e76a622540dc6b8173d2ec435a8e072b3 (the GREEN commit, 19 files). Hook output: `All checks passed!` / `[feature/s81-g4-kb-serve 48a82a5e] feat(kb): S81-G4 KB-SERVE (S81-18 + S81-19 + D16 + D17), dark KB-first serve, enrich worker, operator ingest, coverage rollup`.
  `git diff --stat 0b19de5b..48a82a5e` = the 19 files only (8748 insertions, 17 deletions); worktree bytes 18 / 19 = the GREEN table, the D16 file = E-G4-1; `git status --short` empty.
  Note: the HEAD blobs of the 7 edited CRLF files differ from the worktree sha only by autocrlf normalisation (proved for all 7: worktree bytes with CRLF -> LF == the blob); the GREEN table sha is a worktree-bytes sha.
- Commit 2 = ded9a8df5da0ad120a9df242076b89514b066b9d (tests/test_s81_g4_gate_rows.py new, CLAUDE.md edited). Hook output: `All checks passed!` / `[feature/s81-g4-kb-serve ded9a8df] test(kb): S81-G4 fix round 1, E-G4-1 digest name, gate rows G4-GR1 / G4-GR2, stated limits D16-L7 / D17-L5 / D17-L6`.
- `git log --oneline 0b19de5b..HEAD` = exactly the two commits; `git status --short` empty.

## 4. The 20-file table at commit 2
| status | sha256 (worktree bytes) | sha256 (HEAD blob) | path |
|---|---|---|---|
| fix1-edit | d31b1fe6ced981110b0b6cb02079417f439c9ff16b8e8af6aa8ed92301fe4c72 | 97f014641bafd0111451ac5ffc7f852f2ab281a92399a85d10efe49149ffc6c8 | CLAUDE.md |
| GREEN-equal | 151cddc3024ed12214cc1bcb95fdbd458abf9197fe309733031a0e6455df7a96 | 6cdcde3417d56754b4fc98026a05212cf299bd4dbd73fde82714af862008cd41 | app/api/admin_routes.py |
| GREEN-equal | 987e89f9362bdfc596ff6c58101321240433eb79f5419e7f44e2c35f8c5b91d5 | 398716435275a5445c56393e7f8134f5bd4cb4f1d612382386e3a50061232687 | app/api/image_routes.py |
| GREEN-equal | 437bc724e96685c1d3b31c55573150d80d72194edc90af9da3d172316cc470e2 | 17272f3ada28dd3baf2cce3b1b505835de7bb236595e23e2822daefb35783a3a | app/api/text_routes.py |
| GREEN-equal | 00849ecacf43f74f85b031fe86db78e05c8d4429c18a1b299b524774a9b417c3 | 1d79b06d7c2cffa907b61f60e817c316864e5f06eebfd87455c914533ebe5264 | app/services/kb_ingest.py |
| GREEN-equal | fc17b39c9ef1994c4a850b4b4b6a76236469a5de8cda90d7eae602f346bca94a | fc17b39c9ef1994c4a850b4b4b6a76236469a5de8cda90d7eae602f346bca94a | app/services/kb_operator.py |
| GREEN-equal | 7009e45331a5b65af47a14ae0f7221aed58d4d3fb58d571aeaa36a0652884505 | 7009e45331a5b65af47a14ae0f7221aed58d4d3fb58d571aeaa36a0652884505 | app/services/kb_serve.py |
| GREEN-equal | 32d61a98f6b56cb026a9175f34b0c2b3f1d550d02d102bcf743f47003b231f1c | 1b11102314d20b2c285f7b663fa3ed511747ac522c2c0b49c30e61f87c080153 | app/services/structured_comparison_service.py |
| GREEN-equal | c1f289b6524aadca4e09ca4444c01ff760ce45a26887970e431d5c2b5e51535f | c1f289b6524aadca4e09ca4444c01ff760ce45a26887970e431d5c2b5e51535f | docs/runbooks/2026-11-kb-operator-ingest.md |
| GREEN-equal | 5ec64a9badb80126e89c9880f6d4e50f2d7dd0b0c6149b10cc96b0d97338c9bb | 5ec64a9badb80126e89c9880f6d4e50f2d7dd0b0c6149b10cc96b0d97338c9bb | railway.kbcoverage.json |
| GREEN-equal | 6ad03fb14557606232bf1c91902a5f25103e384e648285b11c7b150cbd043326 | 6ad03fb14557606232bf1c91902a5f25103e384e648285b11c7b150cbd043326 | railway.kbenrich.json |
| GREEN-equal | ff2b9c45273e10fe483b73eb445325b83520cd8e628847586b40038f176637b9 | ff2b9c45273e10fe483b73eb445325b83520cd8e628847586b40038f176637b9 | scripts/cron_kb_coverage.py |
| GREEN-equal | 33414373aa304bfaf00f9a5fcfaea7050da28e7dcd2cede4f9c16d592caddf2e | 33414373aa304bfaf00f9a5fcfaea7050da28e7dcd2cede4f9c16d592caddf2e | scripts/cron_kb_enrich.py |
| GREEN-equal | 8ab15ee0c25633f8df73b8acec93dcf6568b395ed7bcfcfdd5c28ff6e0eb8d6b | 8ab15ee0c25633f8df73b8acec93dcf6568b395ed7bcfcfdd5c28ff6e0eb8d6b | tests/fixtures/s81_s18_flag_off_golden.json |
| E-G4-1 | 1bb5214636e868ef53e026bbc89a8fea8554fb011aefe20f41ac1d95b232aceb | 1bb5214636e868ef53e026bbc89a8fea8554fb011aefe20f41ac1d95b232aceb | tests/test_s81_d16_operator_ingest.py |
| GREEN-equal | 03b7ccf6140148c884e8e2b4f57123baee3c38207712ebedfecc320659f2f317 | 03b7ccf6140148c884e8e2b4f57123baee3c38207712ebedfecc320659f2f317 | tests/test_s81_d17_coverage.py |
| fix1-new | 0dc8d17ff60e26007913e0ae884d37ef2be3e60ac7a506198c273f413520fae1 | 0dc8d17ff60e26007913e0ae884d37ef2be3e60ac7a506198c273f413520fae1 | tests/test_s81_g4_gate_rows.py |
| GREEN-equal | 5a2b4d60c606a1219b246d04278d61a58bbd10ae2026d6a1834eefe44f76dc8f | 97fcc8bcfa5519d54e4d9528d236d4103ade061df67389af430a22e2b7c49cb4 | tests/test_s81_kb_schema.py |
| GREEN-equal | 7be2ed3a9c05c6680b654cf3bf548ade374873056e03ec01836e8d66cb769cd2 | 7be2ed3a9c05c6680b654cf3bf548ade374873056e03ec01836e8d66cb769cd2 | tests/test_s81_s18_kb_first_serve.py |
| GREEN-equal | a400b6795ed166df98a59326c49f04565c60157777b6a2dce7a1bdc7481ffe84 | a400b6795ed166df98a59326c49f04565c60157777b6a2dce7a1bdc7481ffe84 | tests/test_s81_s19_gap_queue.py |

17 GREEN-equal + E-G4-1 + the two fix-round files. No app/ or scripts/ byte differs from the GREEN table.

## 5. Gate rows (F1-3) and the kill proofs
- G4-GR1 `test_g4_gr1_full_hit_carries_card_rating`: ENABLE_KB_FIRST_SERVE ON, two FULL cards (4.6 / 31 and 4.2 / 57), a recording wrapper on `_fetch_product_data`; asserts kb_hit [full, full], zero live rating calls and the result (rating, review_count) pairs == [(4.2, 57), (4.6, 31)] (values, not presence).
- G4-GR2 `test_g4_gr2_release_owner_check[other_str|other_bytes|own_str|own_bytes|absent]`: `EnrichRun.release` with a recording fake Redis; another run id (str / bytes) -> no DELETE, key kept; this run id (str / bytes) -> exactly one DELETE; GET None -> no DELETE.
- Seams: the frozen S18 file is reached through `importlib.import_module("tests.test_s81_s18_kb_first_serve")` (the G3-GR3 precedent); pure ASCII, LF; netguard 0.
- At HEAD: 6 passed, 10 warnings in 3.06s
- Kill proofs in a detached scratch worktree at 0b19de5b (scratchpad/S81-G4_fix1_scratch, NO junction ever created; the 19 GREEN files + the gate rows copied in, 20 / 20 sha-equal), each mutant applied on the byte copy, run, restored (sha-equal); the worktree was then removed and pruned.
  - ADV-3 (the three-line `if _kb_full:` rating / review_count write after the rating_data block deleted): 1 failed, 5 passed, 10 warnings in 3.73s; GR1 fails on `AssertionError: [(4.2, None), (4.6, None)] == [(4.2, 57), (4.6, 31)]`; GR2 green. Observation: with the write deleted the rating value still arrives (another path carries the card rating), review_count does not; the row kills on review_count.
  - ADV-7 (`if held == self.run_id:` dropped, release deletes unconditionally): 3 failed, 3 passed, 10 warnings in 4.30s; GR2[other_str], [other_bytes], [absent] fail on AssertionError (the recorded DELETE); own_* and GR1 green.
  - Every failing node in both kill logs failed on an AssertionError (no other exception type on an `E ` line).

## 6. Documentation (F1-4 / F1-5 / F1-6)
- CLAUDE.md (CRLF kept, 0 non-CRLF lines, `git diff --stat` 2 insertions / 2 deletions, added text pure ASCII, sha256 d31b1fe6...): the D16 row clause now reads `another method answers 405 and a malformed JSON body on POST answers 422 before any dependency runs, D16-L1)`; the D16 row ends `Stated limits (ids; the text in the PR body): D16-L1..D16-L7.`; the D17 row ends `Stated limits (ids; the text in the PR body): D17-L1..D17-L6.` (deviation 1).
- PR body draft scratchpad/S81-G4_fix1/PR_BODY.md (12173 bytes <= 25,600): HEAD + the two commits, the E-G4-1 row in the pin table, the gate rows, D16-L1 widened, D16-L7 with the D16b follow-up, D17-L5 / D17-L6 with the D17b follow-up, a fix-round gates line.

## 7. Gates (F1-8), one pytest at a time, every run through pyt.py
- ruff --select E9,F63,F7,F82: All checks passed (gate rows + D16 file); py_compile: clean.
- Byte checks: gate rows 0 bytes > 127, 0 CR; CLAUDE.md 0 non-CRLF lines; D16 file exactly two changed lines.
- OFF (four RED files + test_s81_kb_schema + gate rows + test_secret_scan_static): 679 passed, 11 warnings in 27.95s
- ON (seven flags exported, the two mode flags true = DRY; four RED files + gate rows): 119 passed, 11 warnings in 5.60s
- NOT run this round (F1-8): the CI-order set, the comm set, the fourteen client fences, the corpus gate, the hook test files, the FULL jest (the final round, LC-7).

## 8. Deviations
1. The CLAUDE.md G4 D16 / D17 rows carried no stated-limit id list (only the inline D16-L1); F1-5 / F1-6 say to add the ids there, so one ids-only sentence was appended to each row naming the full ranges D16-L1..D16-L7 and D17-L1..D17-L6 (the GREEN PR body ids plus the new ones).
2. The scratch worktree was removed with `git worktree remove --force`; safe because it never held a junction (checked: no SmartCompareApp/node_modules there).

No open questions.

## 9. The [pyt] summary lines (verbatim)
- [pyt] tag=g4fix1-gr-head start=2026-11-04 22:49:35 end=2026-11-04 22:49:39 elapsed=4s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_fix1\logs\gr_head.log
- [pyt] tag=g4fix1-kill-adv3 start=2026-11-04 22:50:34 end=2026-11-04 22:50:39 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_fix1\logs\kill_adv3.log (the expected kill)
- [pyt] tag=g4fix1-kill-adv7 start=2026-11-04 22:50:54 end=2026-11-04 22:51:00 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_fix1\logs\kill_adv7.log (the expected kill)
- [pyt] tag=g4fix1-off start=2026-11-04 22:53:13 end=2026-11-04 22:53:42 elapsed=29s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_fix1\logs\off.log (679 passed; [netguard] blocked 0)
- [pyt] tag=g4fix1-on start=2026-11-04 22:54:02 end=2026-11-04 22:54:09 elapsed=7s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_fix1\logs\on.log (119 passed; [netguard] blocked 0)
