# S81-20 ADVERSARY (quotaandbilling) - verdict SOUND

Unit S81-20 B2-RESULT-GATE-V2. HEAD verified 404b4ba525d42074a52f514ab0ac7299b857dbf4 (sc-s81-s20, branch feature/s81-s20-result-gate-v2; git status clean). Frozen RED file re-hashed first and last in sc-s81-s20: 13aa83ade66d14759278e6da14668f60d48dabdcb1002b4d7bb29c0a88c0180c (the committed blob is the same bytes).

Scratch worktree: <scratchpad>/S81-20_adv_quotaandbilling (detached at the GREEN HEAD, no junction). Note: this box has core.autocrlf=true, so a plain worktree add checks the LF RED file out as CRLF (74,229 B, sha 46c6c360...). I re-checked out the blobs as LF (autocrlf=false), then re-applied CRLF to the six app files + CLAUDE.md with python. After that, all nine files (RED, gate rows, six app files, CLAUDE.md) sha-matched the GREEN worktree, before the probes and again after every mutant restore (qb_sha_before / qb_sha_after / qb_sha_green.txt under S81-20_adv/). Other repo files in the scratch tree are LF. That does not affect the files under test. Worktree removed at the end.

## GC-15: the real routes on the S81-09 FakeRedis Lua recorder plus the real category_gate
Probe: tests/test_qb_probe_s20.py in the scratch tree only (copy: S81-20_adv/qb_probe_s20.py.txt; not committed). The setup:
- ONE combined FakeRedis: the S81-09 recorder plus an emulation of REFUSAL_INCR_SCRIPT plus MGET.
- Installed on usage_service.redis_client AND cache_service.redis_client (in prod both names point at one client).
- The real consume_comparison_credit / refund_comparison_credit and the real category_gate (budget_state_async, record_refusal_async, budget_exempt_async on the S81-09 tier stub).
- Every paid leaf stubbed through the S81-09 _stub_routes.
- Sites: text POST, text GET, stream, URL POST, URL GET, camera.
- Bodies: the RED's body_v10 / url_noev / VISION FRAG_SAME.

| row | what | result |
|---|---|---|
| QB1 x12 | result gate ON, fragrance gate OFF, W4-13 truth OFF and ON | 1 consume EVAL; refund keys == {daily, device_daily} exactly; ONE DEVICE_REFUND_SCRIPT EVAL over the same two keys; counters back to their start value; NO MGET and NO refusal INCR (no budget read, no count); lifetime 0; history 0; record_comparison 0; exactly ONE search_logs row, result_gate:<reason>, success False, in BOTH W4-13 states; the reason key on the wire (body and stream frames) |
| QB2 x6 | fragrance gate ON, budget open | ONE refusal INCR EVAL on the account key (counter 0 -> 1); ONE keyed refund EVAL; one row; lifetime / history 0 |
| QB3 x6 | fragrance gate ON, budget spent between the pre-consume check and the exit (a concurrent refusal; REFUSAL_DAILY_BUDGET=2) | NO refund EVAL, NO refusal INCR (GC-6), the consumed credit kept (counters 2/2), one row, lifetime / history 0 |
| QB4 x6 | result gate OFF, same thin bodies | delivered 200; no refund; no result_gate row; no reason key |
| QB5 x2 | anonymous camera with ENABLE_ANON_USAGE_GATE | metering ON: refund_anon_comparison_credit called ONCE with the check's consumed_keys. Metering OFF: no anon refund (L22, as stated) |
| QB6 x6 | device quota OFF (the legacy consume) | the keyed refund restores every usage counter (net zero) |
| QB7 | stream with ENABLE_COMPARISON_ID_ECHO ON plus both gates ON | no persist, no comparison_id, both terminal frames carry reason no_evidence, 1 INCR, 1 refund EVAL, 1 row |
| QB8 x6 | refusal-budget keys | the INCR keys at the exit == the MGET keys of the S81-10 pre-consume check (account AND device key) on every route, the stream settle task included (the request ContextVars reach the settle coroutine) |
| QB9 x8 | S81-10 CATEGORY_NOT_LIVE result on text POST / GET / stream / URL, result gate OFF vs ON | identical status, refund and rows; no reason key; no result_gate row; no route-level INCR (EQ1 holds at runtime) |

[pyt] summary lines:
- [pyt] tag=s20qb-probe1 start=2026-11-05 12:17:48 end=2026-11-05 12:17:53 elapsed=5s bound=600s status=OK rc=0 (30 passed)
- [pyt] tag=s20qb-probe2 start=2026-11-05 12:20:25 end=2026-11-05 12:20:31 elapsed=6s bound=600s status=FAIL rc=1 (6 failed in QB6: a PROBE artifact. The legacy monthly key is created at 0 by incr/decr, so the store compare saw a new key at 0. Fixed in the probe by comparing missing = 0. Not a code defect.)
- [pyt] tag=s20qb-probe3 start=2026-11-05 12:20:44 end=2026-11-05 12:20:50 elapsed=5s bound=600s status=OK rc=0 (39 passed)
- [pyt] tag=s20qb-probe4 start=2026-11-05 12:27:59 end=2026-11-05 12:28:04 elapsed=5s bound=600s status=OK rc=0 (QB8 6 passed)
- [pyt] tag=s20qb-probe5 start=2026-11-05 12:28:57 end=2026-11-05 12:29:02 elapsed=5s bound=600s status=OK rc=0 (QB9 8 passed)

Probe discrimination (mutants on sha-verified byte copies, each restored and sha-verified):
- mA: text POST keyless refund. s20qb-mA FAIL, 2 failed: KILLED by QB1.
- mB: _result_gate_exit `if not spent` -> `if True`. s20qb-mB FAIL: KILLED by QB3.
- mC: camera `if not _s20_spent` -> `if True`. s20qb-mC FAIL: KILLED by QB3.
- mD: URL `if not _s20_spent` -> `if True`. s20qb-mD FAIL: KILLED by QB3.
- mE: stream settle keyless refund. s20qb-mE FAIL, 2 failed: KILLED by QB1.

Against the COMMITTED rows:
- mF: the settle's `if not spent` -> `if True`. s20qb-mF FAIL, 2 failed: KILLED by G20-GR1/GR2.
- mG: the camera record_refusal_async dropped. It SURVIVES the gate-rows file (s20qb-mG OK: GR1 is the spent case, so this is expected). It is KILLED by RED r35 / r60 (s20qb-mG2 FAIL, 2 failed).

## The committed files from the exact bytes
- [pyt] tag=s20qb-red-off start=2026-11-05 12:21:05 end=2026-11-05 12:21:13 elapsed=9s bound=1200s status=OK rc=0: RED + gate rows = 178 passed (166 + 12), flag unset.
- [pyt] tag=s20qb-red-on start=2026-11-05 12:21:14 end=2026-11-05 12:21:22 elapsed=8s bound=1200s status=OK rc=0: 178 passed with ENABLE_RESULT_GATE=true exported in the runner environment only.

The billing chunk (25 files, each in GREEN's COMM_SET_HEAD; list in S81-20_adv/qb_billing_set.txt):
- Files: b2_strict_optional_auth, comparison_id_echo, image_identify_llm_unavailable_s69, m13_37, m18_usage_symmetry, paid_route_metering, retro_w2_1, s71_u13 x2, s80_b3, s80_url_mode_v2, s81_s03, s81_s04, s81_s06 x2, s81_s09 x2, s81_s10 x2, s81_s10b, s81_s18, s81_st1, shutdown_drain, w4_13_measurement_truth, w4_13_flag_off_ledger.
- [pyt] tag=s20qb-bill-off start=2026-11-05 12:22:09 end=2026-11-05 12:24:04 elapsed=115s bound=1200s status=OK rc=0: 3171 passed, flag unset. The W4-13 flag-OFF ledger is green.
- [pyt] tag=s20qb-bill-on start=2026-11-05 12:24:11 end=2026-11-05 12:25:51 elapsed=99s bound=1200s status=FAIL rc=1: 85 failed / 3086 passed with the flag exported.
- All 85 node ids are a SUBSET of GREEN's sweep_only.txt (comm -23 empty).
- Every failure I read is a thin stub body refused as designed (400 INSUFFICIENT_DATA no_evidence where the pin expects 200), or an old one-argument refund stub receiving the keyed refund.
- No double refund, no double count and no metering of a refusal was seen.
- test_w4_13_flag_off_ledger stays green even with the flag exported.

## Code read (billing paths)
- text POST / GET: consumed_keys are captured at the consume site. The exit sits after the failure branch, so a success:False (CATEGORY_NOT_LIVE, H6, TIMEOUT) never reaches it. The order is: refund (fire_and_forget) BEFORE the raise, then record, then the row, then the raise.
- Stream:
  - the first terminal decides;
  - persist is skipped;
  - the finally's new first arm schedules ONE settle coroutine and awaits nothing;
  - client-gone takes the base keyless incomplete arm (L21);
  - had_error takes the base keyless arm (R62).
- URL: the keys_out dict is additive. The refund comes before the raise, and the paid_route_metering delivery block is unreachable on a refusal.
- Camera: the refusal comes after the S81-10 pair gate and before the compare. _refund_reserved_credit keeps the at-most-once latch. The anon refund follows the metering rule.
- The gated condition is identical to the pre-consume S81-10 gate on every route (flag ON and not admin).
- category_gate's budget_state_async and record_refusal_async never raise (fail-open). The stream settle additionally wraps each leg.

## Findings
BLOCKING: none. MAJOR: none.

MINOR (stated limits / wording, LC-4):
- QB-m1: PR_BODY.md is not pure ASCII. Line 108 is the harness-mandated attribution line with the robot emoji (4 bytes > 127). The brief's "pure ASCII" and the attribution rule conflict; the orchestrator rules which one wins.
- QB-m2: the PR body canary row says "refunds == refusals". The CLAUDE.md block correctly says "(minus spent-budget keeps)". Refusals that consumed nothing (anonymous text, premium or exempt with consumed False, metering-OFF camera) also have no refund. The PR body should carry the same qualifier.
- QB-m3: the CLAUDE.md Accounting sentence "every refusal refunds ... BEFORE the raise" is unqualified. The next sentence qualifies it (spent keeps the credit), and the stream has no raise: its refund lands in the settle task after the response (L25 in the PR body). Wording only.
- QB-m4: app/api/url_routes.py _url_row's base comment "only ever called under flag 1" is now stale. The S81-20 refusal calls it in both W4-13 states (by design, L6). Comment only.
- QB-m5: the E8+ sweep reds (135 nodes in 19 files, incl. the billing files s09 / s10 / s10 gate rows) are named in CLAUDE.md L12 and not cleaned by E-rows. This deviates from GC-10's "joins by name as an E-row" (GREEN D2 / Q1). It is not silent and CI (flag unset) is green. The orchestrator rules; a fix round would be one-name additions.
- QB-note (design, already ruled GC-6 / R-S20-38): a caller whose refusal budget fills between the pre-consume check and the exit pays one credit for a refused compare. The canary row "refusal-budget hits attributable to the result gate" observes it.

## Prove-nothing rows
None in my lens. G20-GR1 alone does not kill a dropped camera record (mG), but RED r35 / r60 do.

## Hygiene
I made no edit to sc-s81-s20. All probes and mutants ran in my own scratch worktree and it is removed. One pytest at a time; no pytest left running. No .env read, no secret printed, the flag never set outside the runner environment, no network, no package manager.
