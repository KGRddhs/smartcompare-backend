# INC-M1a FIX ROUND 1 REPORT (Claude Opus 5.5, 2026-11-17 14:39 AST)

Worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-m1a, branch fix/inc-m1a-resolver-fold. Start HEAD 06deda559bc1bdebf249edf3b23c072e5b37956b (verified, git status empty). New HEAD e60a656c6a8979b7370bd69bb231afe8ed1866b1 (ONE commit on 06deda55; no amend, no push, no stash, no rebase: the fix-round rulings name no step 0). git status --short after the commit: empty. Written through python.

## Files (sha256 on disk after)
- app/services/product_resolver.py: +16 -10 vs 06deda55; 02a41e51fbd4f95299bd8c7a2b35de4371601561d7f0c4c101bf44d250906d12 (CRLF working copy, blob LF, 0 bytes > 127)
- CLAUDE.md: +1 -1 vs 06deda55 (the M1a bullet only); 27408945ee0c0f098fe560b9dabdd2633a79a146df92e5a0c63d18a67ff24185 (CRLF kept; 3904 non-ASCII bytes before and after)
- tests/test_inc_m1a_gate_rows.py: NEW, 317 lines, 78 rows; 3adcb236813b70f5cbeca35bc37bbddbba1b2fc3792684efedac7602f9f0a4d4 (LF, 0 bytes > 127; committed blob same sha)
- tests/test_inc_m1a_resolver_fold.py: untouched, 63fc6a67b082317f3346d702a97d1880e2ca4dca8c9df66314b212d7cef0cfd3 at start and end
- PR body draft: C:/Users/SynAckITPC/AppData/Local/Temp/claude/cde30765822f13ce/e8bbde46-f2b1-4f83-9479-dcdff600313a/scratchpad/INC-M1a_fix1/PR_BODY.md (20,276 B; the 4 non-ASCII bytes are the attribution robot glyph inherited from GREEN's draft)

## FX1 (B1) GREEN hunk
- `_token_distance(alias_token, typed_token, exact_single=False)`: `if alias_token.isdigit() or (exact_single and len(alias_token) == 1):` (default = the base rule).
- `_best_window(alias, core, exact_single=False)` passes it through.
- `_lexicon_side` (the D5 line search) calls `_best_window(alias, core, exact_single=True)`; `_line_within_typed` is byte-identical to base (`_best_window(line_tokens, core)`). No other caller of either function exists (grep).
- No flag added: resolve_lexicon is not flag-gated (M1R-9 link key); the flag-OFF compare path is unchanged (PIN-0 rows green ON and OFF).

## FX2 (M1) RED step: tests/test_inc_m1a_gate_rows.py
- SR: test_sr1 (10 names x flag on/off = 20 rows, golden medium/none, never (YSL, Y)); test_sr2 (6 names x on/off = 12 rows, high/lexicon (YSL, Y, conc, flanker)). Arabic tokens built with chr().
- MG: test_mg1 guard accepts (9 base-only accepts + 6 accepts true under both rules = 15); test_mg2 guard refusals (5); test_mg3 accept_model_side accepts (9); test_mg4 accept_model_side refusals (5); test_mg5 end to end through resolve_pair with the r21 seam (flag ON, TEXT ON, PRE ON, consent 3, synthetic key from tests/test_inc_r1_seam.py, fake SDK; 1 Anthropic call, no OpenAI call; outcome resolved) (9); test_mg6 end to end refusals (coco, luna; outcome ask) (2); test_mg7 hygiene (1).
- Inputs from probe_guard.txt / probe_accept.txt; expected values measured with the base distance rule substituted (probe_mg.py -> probe_mg_head.txt).
- Proof 1, at 06deda55: 27 failed (the MG accept rows mg1 x9, mg3 x9, mg5 x9), 27 of 27 AssertionError; 51 passed (every SR row, the MG refusals, the both-rule accepts, mg7).
- Proof 2, mutant X1 (the D1 rule reverted, `if alias_token.isdigit():`) on a byte copy of the 06deda55 bytes: 20 failed (all sr1 rows), 20 of 20 AssertionError; restored sha 88c3276b... (= 06deda55 resolver).
- Proof 3, after FX1: unit file + pin file + test_inc_r1_resolver.py 372 passed, flag ON and OFF.
- Proof 4, mutant M4 (`_line_within_typed` calls `_best_window(line_tokens, core, exact_single=True)`, the 06deda55 behaviour): 27 failed (MG accepts), all AssertionError.
- Extra mutants on the fixed bytes: M5 (rule global again) 27 failed; X1L (`_lexicon_side` drops exact_single=True) 20 failed; X1P (`_best_window` stops passing exact_single) 20 failed. KILLED 5 of 5. Every mutant restored and sha-verified (02a41e51...), lock file created and removed per mutant.

## Runs ([pyt] / [jest] lines)
- [pyt] tag=inc-m1a-fix1-red-head start=2026-11-17 14:24:10 end=2026-11-17 14:24:14 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\red_head.log
- [pyt] tag=inc-m1a-fix1-mut-X1_head start=2026-11-17 14:24:36 end=2026-11-17 14:24:40 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_X1_head.log
- [pyt] tag=inc-m1a-fix1-unit-true start=2026-11-17 14:25:36 end=2026-11-17 14:25:48 elapsed=11s bound=600s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\unit_true.log
- [pyt] tag=inc-m1a-fix1-unit-false start=2026-11-17 14:25:49 end=2026-11-17 14:26:01 elapsed=12s bound=600s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\unit_false.log
- [pyt] tag=inc-m1a-fix1-mut-M4 start=2026-11-17 14:26:13 end=2026-11-17 14:26:17 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_M4.log
- [pyt] tag=inc-m1a-fix1-mut-M5 start=2026-11-17 14:26:18 end=2026-11-17 14:26:22 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_M5.log
- [pyt] tag=inc-m1a-fix1-mut-X1L start=2026-11-17 14:26:23 end=2026-11-17 14:26:27 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_X1L.log
- [pyt] tag=inc-m1a-fix1-mut-X1P start=2026-11-17 14:26:28 end=2026-11-17 14:26:32 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_X1P.log
- [pyt] tag=inc-m1a-fix1-resolver7 start=2026-11-17 14:27:34 end=2026-11-17 14:28:03 elapsed=29s bound=1200s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\resolver7.log
- [pyt] tag=inc-m1a-fix1-comm-c01 start=2026-11-17 14:28:10 end=2026-11-17 14:28:42 elapsed=32s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c01.log
- [pyt] tag=inc-m1a-fix1-comm-c02 start=2026-11-17 14:28:42 end=2026-11-17 14:30:51 elapsed=128s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c02.log
- [pyt] tag=inc-m1a-fix1-comm-c03 start=2026-11-17 14:30:52 end=2026-11-17 14:31:39 elapsed=48s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c03.log
- [pyt] tag=inc-m1a-fix1-comm-c04 start=2026-11-17 14:31:45 end=2026-11-17 14:33:27 elapsed=102s bound=1200s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c04.log
- [pyt] tag=inc-m1a-fix1-comm-c05 start=2026-11-17 14:33:28 end=2026-11-17 14:35:19 elapsed=111s bound=1200s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c05.log
- [pyt] tag=inc-m1a-fix1-comm-c06 start=2026-11-17 14:35:26 end=2026-11-17 14:36:18 elapsed=52s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c06.log
- [pyt] tag=inc-m1a-fix1-comm-c07 start=2026-11-17 14:36:19 end=2026-11-17 14:36:36 elapsed=17s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c07.log
- [jest] tag=inc-m1a-fix1-fences start=2026-11-17 14:36:46 end=2026-11-17 14:36:53 rc=1 (jest 29.7.0; 15 suites, 4 failed / 246 passed; the 4 = config/nativeBundle.w37 d5 / k2 / k4 / k5, the accepted drift; probe before the run printed no jest process)
- Every pytest run: [netguard] blocked 0; [hermeticity] sentinel checked = the collected count. BOX_GO existed from the first tool call; every pytest ran directly through pyt.py with PYT_VIA_GATE=1, one at a time; no BUSY, no TIMEOUT.

## Gates
- Unit file + pin file + test_inc_r1_resolver.py ON / OFF: 372 / 372 passed.
- The 7 resolver suites: 1 failed (test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content, base record), 699 passed (= GREEN).
- Comm set, 156 files in the RED chunks 01-07 at the new bytes: 15 failed ids, every one in INC-M1a/comm/base_failed_ids.txt; branch-only-NEW EMPTY; base-only = test_inc_i2a_picture_not_cut.py::test_e27_elapsed_includes_the_wait (the timing flake, passed). Ids: INC-M1a_fix1/comm/head_failed_ids.txt.
- Whole tree one process: NOT re-run (no module-level state change; the rulings say so).
- Client fences: run once, result above.
- ruff E9,F63,F7,F82 clean (product_resolver.py, the pin file); py_compile clean; black 26.5.1 --check clean on product_resolver.py (allowlisted; the hook's black step also passed at commit). The pin file is not black-formatted (black would wrap 3 long lines) and is not on the allowlist; left as frozen at the RED step so its sha stays the RED sha.

## Documentation rulings
- m1: the CLAUDE.md M1a bullet and the PR body carry the exact sentence "with ENABLE_PRODUCT_RESOLVER OFF nothing changes, except the INC-U1 link key (product.link_key, brand and variant in the /url response) when ENABLE_URL_LINK_RESULT is ON (M1R-9; both OFF on web)"; "the resolver is not called" and "reads no lines file" are gone (asserted by write_pr.py).
- m2: the bullet says the one-character rule is the lexicon arm's only and the model-arm guard keeps the base D5 rule.
- m3: the PR body's resolver-suites line now carries its [pyt] line (this round's run; GREEN's run had none in its log).
- m4-m7: stated limits in the PR body (m7 read as the adversary's inert-code list X2 / X8 / X9); m4 and m5 also in the CLAUDE.md bullet.

## Deviations
1. The fix-round rulings file has no section titled "Procedure for the fix agent"; I followed its FX1-FX3, the "Proof, in this order" list and "Gates for the fix round". It names no step 0, so no rebase was run.
2. Proof 1 says "the MG rows FAIL": the MG refusal rows and the 6 accepts true under both rules PASS at 06deda55 by design (pins both ways, as FX2 asks for a refusal the guard already makes); the 27 base-only accept rows fail.
3. The MG end-to-end rows reuse the r21 seam through the helpers of tests/test_inc_r1_seam.py (as the frozen RED file does), not by importing tests/test_inc_r1_resolver.py.
4. The MG expected values were measured on the 06deda55 bytes with the base distance rule substituted (the adversary's method), not on a 9bc13109 checkout; the only resolver difference that reaches these Latin inputs is the distance rule.
5. CLAUDE.md gained two stated-limit clauses beyond m1 / m2 (m5, and the model-arm Y limit below) to keep the row true.

## Open questions for the gate
1. With the model arm reachable, a high-confidence model answer (Yves Saint Laurent, Y) for typed YSL L'Homme / YSL B / YSL by / YSL Ya passes the base guard (d) and is accepted as (YSL, Y, EDT) (probe_model_y.txt). FX1 orders the base rule there, and at base the guard accepted any one-letter model line the same way; it needs the model to name the wrong line with high confidence. Stated as a limit; rule whether a later unit narrows guard (d) for a one-letter line.
2. m4 (a bare typed Y resolves to YSL Y high) stays an owner question for the resolver window.

## NOT MEASURED
- Nothing in the rulings' gate list. The whole-tree one-process run was not re-run by ruling.

## PROOF ON THE PHONE: unchanged (PR body). Merged, NOT yet proven.
