# S81-10 FRAGRANCE-ONLY-GATE: adversary report, lens QUOTA-AND-BILLING (Opus 5.5 adversary; written through the shell)

- unit: S81-10 FRAGRANCE-ONLY-GATE (FOCUS, GC-11 lens quota-and-billing); worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s10, branch feature/s81-s10-fragrance-only-gate, HEAD 0523a06fe25e4df3682b26a83daa72bf2f2ee543 (verified 13:40 and again at the end); base 6c14ac95.
- RED files re-hashed at the start and at the end, in the unit worktree and as HEAD blobs: tests/test_s81_s10_fragrance_gate.py d988882a08ac3c57624b8d1ef89492b5a8d0d7ed203a73fa9cfb76fbadad12ac; tests/fixtures/s81_s10_flag_off_golden.json 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a. Never edited.
- every probe and mutant ran in MY scratch worktree <scratchpad>/S81-10_adv_quotaandbilling (git worktree add --detach at 0523a06f). core.autocrlf checked the five new LF files out as CRLF, so they were rewritten from git show HEAD:<path>; then all 14 changed files were sha-identical to the unit worktree. Mutation lock created and removed by the harness; a manifest of 3,460 files (tracked + my probe) identical before and after the 35 mutants; worktree deregistered at the end (git worktree remove --force; absent from git worktree list) but its folder stayed on disk after a Filename too long stop (see End state). The unit worktree was never written.
- notes and logs: <scratchpad>/S81-10_adv/qb/ (notes.md, mut_harness.py, mutants.json, mut_results.tsv, logs/, probe source copied there as test_zz_qb_probe.py).

VERDICT: NOT_READY. One BLOCKING item (the time-bombed frozen golden; the same defect as the correctness lens B1, measured here independently). No MAJOR. No defect found in the GREEN billing code: every R-A3 obligation holds on the exact bytes, measured end to end with the REAL orchestrator behind the REAL routes. Nine MINOR items (coverage gaps, wording, cross-unit notes).

## BLOCKING
B1-qb (frozen RED, not GREEN code; = correctness B1): the committed golden is wall-clock dependent, so the strongest flag-OFF identity pins are red on ANY bytes since 2026-11-02T10:00Z and the PR CI will be red. Golden scenario G10 (GET /api/v1/home/smart-pick, flag OFF) stores the body text "updated_at":"3d ago"; home_routes._format_updated_at computes now - created_at, and the RED row data uses the FIXED created_at 2026-10-29T10:00:00Z (_comparison_row cmp-1) with no clock freeze in _run_golden. Measured on the exact GREEN bytes: qb-red-off (13:48, ambient OFF) and qb-red-on (14:08, ambient ON) both 10 failed = test_p01_flag_off_golden[unset,false,0,off,empty] + test_r54_off_calls_nothing_of_the_gate[same five], every one AssertionError ("G10", "body") with "3d ago" vs "4d ago"; from 2026-11-05T10:00Z the label becomes "Older" (still a mismatch, permanently). GREEN last ran them green at 12:47 AST (09:47Z), 13 minutes before the label flipped. The OFF identity itself HOLDS: my QB01 rows re-run the frozen P01 / R54 functions unchanged with home_routes._format_updated_at evaluated at the record clock (2026-11-02T08:30Z): 10 passed ambient OFF (qb-probe-1/-2/-3) and ambient ON (qb-red-on). Fix (orchestrator ruling, test-only, LC-2): amend the frozen RED so the Harness default smart-pick rows (cmp-1 / cmp-2, RED file lines 652-653) build created_at relative to the run clock (e.g. now - 3 d - 2 h keeps the stored "3d ago" byte-identical) or freeze the formatter clock inside _run_golden; re-hash the RED file; keep the golden bytes; then re-state the GREEN report and PR body lines "140 / 140" and "P01, R54 byte-identical".

## MAJOR
none.

## MINOR (documentation rulings / stated limits by LC-4; the code is correct in every case)
- m1 (R-S10-8 coverage, overlaps correctness m1) the admin-key bypass is pinned on POST (P06) and the camera (test_gc6_admin_key_camera_bypasses_the_gate) only. QM01 (the GET gate block reads `and True` instead of the marker) and QM02 (the same on the stream) pass the whole RED file + gate rows; only my probe test_qb03_admin_key_bypass_get_and_stream kills them. GET is the route scripts/eval_runner.py:1021 and scripts/bundle_d_prod_smoke.py call (the measurement path R-S10-8 exists for); scripts/verify_after_credits.py drives the stream. Code correct (QB03 green). Suggest one P06-shaped row for GET and one for the stream in the GREEN-owned tests/test_s81_s10_gate_rows.py.
- m2 (route-level double count unpinned) QM12 (the camera post-resolve arm calls record_refusal_async a second time) passes the unit suite: R38 counts refunds and compares but no EVALs, and its FakeService never counts, so a second INCR in the route is invisible; R33 / R34 / P08 have the same blind spot on the text arms. Killed only by my end-to-end probe test_qb02_camera_post_resolve_counted_once_refunded_once. A doubled count halves the budget (lock-out after 5 refusals). Suggest `assert not _evals(h.rec)` in R38-style route rows or an end-to-end row (QB02 shape).
- m3 (anon refunds on the gate exits unpinned) QM10 (camera post-resolve arm without _refund_anon_credit) and QM15 (camera 2-product rule-1 exit without it) SURVIVE everything; QM09 (budget exit without it) is killed only by my probe test_qb04_camera_budget_anon_metering_on_refunds_once. Reachable only with ENABLE_COMPARE_AUTH_REQUIRED OFF + ENABLE_ANON_USAGE_GATE ON + metering ON (production runs auth ON, so an anonymous non-admin camera call is 401 before the body). Code correct today.
- m4 (wording) the bypass exists only under ENABLE_COMPARE_AUTH_REQUIRED ON: the marker is set in require_paid_route_user admin branch, which the auth-OFF early return never reaches. Measured: with auth OFF the same X-Admin-Key GET of "best laptop vs dell laptop" is refused 400 CATEGORY_NOT_LIVE (test_qb03_admin_key_with_auth_flag_off_is_gated; GC-6 pins the marker half). PR body "What the flag does" item 5 and the CLAUDE.md row say "bypasses the gate" with no condition; add "(under ENABLE_COMPARE_AUTH_REQUIRED ON, as in production since 2026-10-03)".
- m5 (anon accounting with metering OFF) an anonymous camera call over the refusal budget with ENABLE_ANON_USAGE_GATE ON and ENABLE_PAID_ROUTE_METERING OFF keeps the anon-gate debit (test_qb04_camera_budget_anon_metering_off_keeps_the_debit: anon_consume 1, refund_anon 0): the base W2-1d rule (metering OFF = debit at the gate, no refund anywhere). So "the budget 429 is never billed" holds for signed-in callers always and for anonymous ones only with metering ON. Not reachable in production (auth ON, metering ON). One stated-limit clause.
- m6 (GREEN D3 has a budget consequence; the gate Q2) with no chip (the camera always; any client that sends none) a house-evidence pair whose resolver A2b answer is a positive non-fragrance is refused AND counted: measured camera ("Gucci", "Guilty") + ("Prada", "Luna Rossa") with the A2b fake answering fashion: CATEGORY_NOT_LIVE fashion, one EVAL on both keys, one refund, one A2b call (the resolver one, C11) (test_qb06_camera_house_pair_positive_a2b_refused_and_counted). A fashion-house perfume that A2b misreads is a false refusal that also spends budget; ten in a day lock the subject out of every compare (L13). If D3 is confirmed, add the canary read "one fashion-house perfume camera pair without a form word proceeds" and state the budget consequence.
- m7 (cross-unit for S81-11; widen R-S10-15) the stream pre-consume refusals are plain JSON 400 / 429 (before StreamingResponse). Both the build-3 client (683f56c0 SmartCompareApp/src/services/api.ts: `if (!response.ok || !response.body) throw` then the outer catch runs runRestCompare) and the merged S81-08 client (api.ts:896-897 -> :990-991) fall back to the REST GET on a non-OK stream response, and the GET runs the gate again. Every stream rule-1 refusal or budget 429 is therefore two requests: still $0 and never billed (both stop before the consume), but two [CATEGORY-GATE] INFO lines, two 10/min limiter slots and, for the budget, two Upstash MGETs; the canary refusal-rate read doubles for stream refusals. R-S10-15 covers only an SSE error EVENT; ask S81-11 to skip the fallback on a non-OK stream response whose JSON code is CATEGORY_NOT_LIVE, and read the canary refusal rate per request id.
- m8 (equivalent survivor, no action) QM22 (a raising tier read EXEMPTS the account) survives, but it is equivalent for the real seam: usage_service._get_user_tier_info catches every Exception itself and returns the free default, so the except arm in budget_exempt_async is unreachable with the production helper. Re-check when the rebase collapses the seam to the S81-09 helper.
- m9 (informational) billing-adjacent test files outside the 425-file comm set (tests/test_m13_37_freemium_atomic_consume.py, test_usage_device_inheritance.py, test_usage_referral_bonus.py, test_usage_service_internals.py, test_usage_tiers.py, test_referral_expiry.py, test_analytics.py, test_security_middleware.py, test_m13_02_proxy_aware_ratelimit.py) reference only the unedited usage_service or name an edited route in a docstring or a synthetic scope, so the union rule does not require them; run at HEAD anyway: 93 passed (qb-billing-extra). No missing comm member found for my lens.

## The GC-11 quota-and-billing duties, each with its measurement
1. R-A3, the $0 refusals never consume: text_gate evaluates rule 1 BEFORE budget_subject, the budget read, the preferences read and the consume on all three text routes (the stream raise precedes StreamingResponse). RED R16-R18 assert no prefs / consume / Redis / tier read; mutants QM29 (budget read before rule 1) and QM30 (rule-1 refusal counted) KILLED by R16. The camera has no $0 rule (its rule 1 is post-vision, refunded and counted by GC-4 / R-S10-13: R37, R40, QM13 KILLED).
2. Every post-consume refusal refunds exactly once, never metered, sync / stream / camera. Read: POST / GET reuse the M13-37 failure arm (one fire_and_forget refund before _surface_comparison_failure raises; the new CATEGORY_NOT_LIVE arm sits after the TIMEOUT / LLM_UNAVAILABLE arm and before the generic coded arm); the stream yields ("error", refusal) and returns, so the finally takes the had_error arm once; the camera arms go through the _refund_state / _anon_refund_state latches. Measured END TO END with the REAL StructuredComparisonService behind the REAL routes (only parse / fetch / A2b / consume / refund faked; my probe tests/test_zz_qb_probe.py): POST and GET 400 CATEGORY_NOT_LIVE with consume 1, refund 1 (usage_refund.text.post / .get), one EVAL over the account + device keys, no record_lifetime / save / capture_result_status, no fetch, no profile task; the stream: exactly one SSE error frame, no complete / settle_complete, the same counts (usage_refund.text_stream), also with ENABLE_PREVERDICT_DISCONNECT_ABORT ON; the camera post-resolve: action "error" CATEGORY_NOT_LIVE, one refund (usage_refund.image.category_not_live), one EVAL (the orchestrator one), the real resolver ran, no compare-through, no search_logs row. A parse other / other proceeds uncounted (no EVAL, fetch reached; the INSUFFICIENT_DATA failure then refunds once). Mutants QM04, QM11, QM16-QM19 KILLED by the RED; QM12 only by the probe (m2).
3. The two-axis budget EVAL and EXPIREAT: REFUSAL_INCR_SCRIPT loops INCR + EXPIREAT ARGV[1] over #KEYS and returns #KEYS (R43 pins the normalised text); _incr_keys passes [str(next_reset + 3600)] through llm_spend_breaker._eval, which picks the upstash keyword shape or the redis-py positional shape; the pinned signatures read in the venv: upstash-redis 1.7.0 eval(script, keys=None, args=None) and mget(*keys); redis 8.1.0 eval(script, numkeys, *keys_and_args) and mget(keys, *args) (mget(*keys) is valid for both). EXPIREAT is always in the future (next reset after now + 1 h), so the EVAL can never delete a key. Mutants KILLED: QM23 (no grace), QM24 (EXPIREAT from now), QM26 (first key only = RED M33), QM20 (any -> all, the account-only read), QM31 (device-only subject), QM27 (nil read as spent), QM28 (raising read refuses).
4. The budget 429 is never billed: text_gate raises 429 CATEGORY_NOT_LIVE (scope refusal_daily, retry_after through the W1-9 block, resets_at) before the preferences read and the consume; the camera returns its HTTP 200 action "error" budget body before its consume and the vision call (any metering state) and gives the anon debit back when metering is ON (QB04, m5 for OFF). R20 (3 routes x 2 axes), R21, R36; QM14 (camera budget skipped under metering) and QM34 (retry_after as str) KILLED; QM35 (evidence requests skip the budget, the PLAN :198 loop) KILLED by R19. Build-3 / S81-08 clients never auto-retry a 429 and only route USAGE_LIMIT to the Paywall (683f56c0 api.ts:216-222 and :341-356; the same branches at HEAD SmartCompareApp/src/services/api.ts:231 and :372), so CATEGORY_NOT_LIVE 429 never opens it.
5. The exemptions: budget_exempt_async is awaited only when a counter is spent (QM21, the tier read on every request, KILLED by R48); allow-list parsing equals S81-09 _device_quota_exempt at eaccd550 (split on commas / whitespace, lower-case, canonical uuid tokens, first 50); premium via usage_service._get_user_tier_info; exempt accounts still get the rule-1 / post-resolve refusals and their refusals still count on the shared device key (by R-S10-1 / R-S10-7). QM22 equivalent (m8).
6. The admin-key bypass: request.state.paid_route_admin is set only in require_paid_route_user admin branch (GC-6 rows; QM07 marker for everyone and QM08 marker from an unverified header with auth OFF both KILLED); POST (P06, QM03 KILLED), camera (gc6 row), GET and stream correct but pinned only by my probe (m1); conditional on auth ON (m4).
7. Flag-OFF golden byte identity: holds at the record clock (QB01, 10 / 10 ambient OFF and ON) under the five OFF spellings with the full configuration and the raising recorders; the committed P01 / R54 are red (B1-qb).
8. The 043 census and the p01 E-rows re-measured: both files green in full (qb-erows: 227 passed; p07 included). Non-vacuous: QM38 (the E1 KEPT row removed) and QM39 (the account key prefix renamed in category_gate) each turn test_every_per_user_cache_key_is_purged_or_kept red; QM40 (a third request_context attribute), QM41 (a needle string in category_gate) and QM42 (a module-level leaf import) each turn test_s05_p01_no_consumer_in_app red. Only the two sanctioned existing test files changed (git diff --name-only 6c14ac95 HEAD).

## Runs (every pytest through pyt.py, one process at a time, foreground; all in the scratch worktree)
```
[pyt] tag=qb-red-off start=2026-11-02 13:48:27 end=2026-11-02 13:48:35 elapsed=7s bound=600s status=FAIL rc=1   (RED file, flag unset: 10 failed, 130 passed = B1-qb, every failure G10 body "3d ago" vs "4d ago")
[pyt] tag=qb-probe-1 start=2026-11-02 13:58:32 end=2026-11-02 13:58:37 elapsed=5s bound=600s status=OK rc=0     (probe: 21 passed; [hermeticity] 21; [netguard] blocked 0)
[pyt] tag=qb-probe-2 start=2026-11-02 14:01:31 end=2026-11-02 14:01:40 elapsed=9s bound=600s status=OK rc=0     (probe + the camera resolve assertion: 21 passed; [netguard] blocked 0)
[pyt] tag=qb-qm01 .. qb-qm42 (35 mutant runs, 14:01:57-14:07:02, bound 600, each 4-10 s; lines in <scratchpad>/S81-10_adv/qb/mut_results.tsv and harness/pyt_ledger.jsonl)
[pyt] tag=qb-erows start=2026-11-02 14:07:48 end=2026-11-02 14:07:58 elapsed=10s bound=600s status=OK rc=0       (test_migration_043_delete_user_cascade.py + test_s81_s05_request_context.py: 227 passed; [hermeticity] 227; [netguard] blocked 0)
[pyt] tag=qb-red-on start=2026-11-02 14:08:05 end=2026-11-02 14:08:15 elapsed=10s bound=600s status=FAIL rc=1    (flag ON ambient: RED + gate rows + probe = 10 failed (the same P01 / R54 ten), 164 passed; [hermeticity] 174; [netguard] blocked 0)
[pyt] tag=qb-billing-extra start=2026-11-02 14:13:07 end=2026-11-02 14:13:14 elapsed=7s bound=1200s status=OK rc=0 (9 billing-adjacent files outside the comm set: 93 passed; [netguard] blocked 0)
[pyt] tag=qb-billing-comm start=2026-11-02 14:13:32 end=2026-11-02 14:14:04 elapsed=32s bound=1200s status=OK rc=0 (12 billing comm-set files: 429_contract, comparison_id_echo, cost_meter_s74, m13_35, m18_preverdict_disconnect_refund, m18_usage_symmetry, paid_route_metering, retro_w1_9_429, retro_w2_1, s81_st1_usage_path_offloop, w4_13_flag_off_ledger, w4_13_measurement_truth: 994 passed; [hermeticity] 994; [netguard] blocked 2 attempt(s) from 2 node(s): the neutralized.supabase.invalid sentinel in test_paid_route_metering, base behaviour)
[pyt] tag=qb-probe-3 start=2026-11-02 14:16:10 end=2026-11-02 14:16:14 elapsed=5s bound=600s status=OK rc=0     (probe incl. QB06: 22 passed; [netguard] blocked 0)
```
Also: ruff --select E9,F63,F7,F82 on the 11 touched Python files: All checks passed; py_compile: OK; json.loads of data/fragrance_lexicon.json and the golden: OK; bytes > 127: 0 in category_gate.py, the lexicon, the gate rows (HEAD blobs); CLAUDE.md non-ASCII count 3937 at base and at HEAD (GREEN claim confirmed).

## Mutation table (35 billing mutants on sha-verified byte copies; harness <scratchpad>/S81-10_adv/qb/mut_harness.py, definitions mutants.json; selection = the RED file + the gate rows + my probe with -k excluding the ten time-bombed nodes (QB01 runs them at the record clock); E-row mutants run their pin node only; restore by shutil.copyfile + sha256, manifest of 3,460 files identical before and after)
| id | mutant | verdict (unit suite) | first killing row |
|---|---|---|---|
| QM01 | GET admin bypass removed | SURVIVES the unit suite | probe qb03[get] only (m1) |
| QM02 | stream admin bypass removed | SURVIVES the unit suite | probe qb03[stream] only (m1) |
| QM03 | POST admin bypass removed (= M40) | KILLED | test_p06 |
| QM04 | the CATEGORY_NOT_LIVE surface arm dead (= M27) | KILLED | test_r33_r34[post] |
| QM07 | marker set for every caller under auth ON | KILLED | test_gc6_marker_only_on_the_admin_branch |
| QM08 | an unverified X-Admin-Key marks the request (auth OFF) | KILLED | test_gc6_marker_only_on_the_admin_branch |
| QM09 | camera budget exit without the anon refund | SURVIVES the unit suite | probe qb04 only (m3) |
| QM10 | camera post-resolve arm without the anon refund | SURVIVED (all) | none (m3) |
| QM11 | camera post-resolve arm without the reserved refund | KILLED | test_r38 |
| QM12 | camera post-resolve arm counts again | SURVIVES the unit suite | probe qb02 camera only (m2) |
| QM13 | camera 1-product rule-1 exit not counted | KILLED | test_r40 |
| QM14 | camera budget read skipped under metering | KILLED | test_r36 |
| QM15 | camera 2-product rule-1 exit without the anon refund | SURVIVED (all) | none (m3) |
| QM16 | sync refusal counted twice | KILLED | test_r24 |
| QM17 | stream refusal not counted | KILLED | test_r25 |
| QM18 | stream refusal without return (falls to the fetch) | KILLED | test_r25 |
| QM19 | refusal_result success True (billed as a delivery) | KILLED | test_r24 |
| QM20 | budget spent only when BOTH axes are spent | KILLED | test_r20[post-acct] |
| QM21 | tier read on every gated request | KILLED | test_r48 |
| QM22 | a raising tier read exempts | SURVIVED (equivalent, m8) | none |
| QM23 | EXPIREAT without the 1 h grace | KILLED | test_r24 |
| QM24 | EXPIREAT from now + 1 day | KILLED | test_r24 |
| QM26 | EVAL over the first key only (= M33) | KILLED | test_r24 |
| QM27 | a nil counter reads as spent | KILLED | test_r19 |
| QM28 | a raising budget read refuses | KILLED | test_r23 |
| QM29 | budget read before rule 1 | KILLED | test_r16 |
| QM30 | rule-1 $0 refusal counted | KILLED | test_r16 |
| QM31 | device-only subject when the device key is bound | KILLED | test_r19 |
| QM34 | retry_after as a str (no Retry-After) | KILLED | test_r20[post-acct] |
| QM35 | evidence requests skip the budget (PLAN :198) | KILLED | test_r19 |
| QM38 | E1 KEPT row removed | KILLED | test_every_per_user_cache_key_is_purged_or_kept |
| QM39 | account key prefix renamed in the writer | KILLED | test_every_per_user_cache_key_is_purged_or_kept |
| QM40 | a third request_context attribute | KILLED | test_s05_p01_no_consumer_in_app |
| QM41 | a needle string in category_gate.py | KILLED | test_s05_p01_no_consumer_in_app |
| QM42 | a module-level leaf import | KILLED | test_s05_p01_no_consumer_in_app |
Counts: 35 applied; 28 KILLED by the unit own rows (incl. the 5 E-row non-vacuity mutants); 4 killed only by my probe (QM01, QM02, QM09, QM12); 3 survive everything (QM10, QM15, QM22 = equivalent).

## Prove-nothing / partial rows (billing)
- R33 / R34 / P08 / R38 feed a LITERAL refusal through the route FakeService: they prove each route arm refunds once and never meters, but they cannot see a count made in the route (m2) and never run the orchestrator, so the composition "the orchestrator counts once, the route refunds once" is unpinned in the unit suite. My end-to-end QB02 rows (real orchestrator, real routes) are green on the exact bytes.
- P06 proves the admin bypass on POST only; the GET / stream halves are unproven in the unit suite (m1).
- R36 / R37 / R38 / R40 run signed-in callers only: the three _refund_anon_credit calls the unit added are unproven (m3).
- P01 / R54 (the identity pins) currently prove nothing because they fail on the wall clock (B1-qb).

## Claims in the GREEN report / PR body / CLAUDE.md row checked against the bytes (lens subset)
- "never billed (no preferences read, no consume)", "ONE MGET", "ONE Lua EVAL increments both keys (EXPIREAT the next reset + 1 h)", "other proceeds, an A2b failure included, never counted", the camera "budget before the consume (any metering state)", "a rule-1 pair, or a rule-1 single product, is refunded and counted", "never comparison_failed (the arm runs before exit 7)", L7 fail-open, L10 (no search_logs row on the $0 and camera refusals; the text post-resolve refusals keep the base failure row), L13 (past the budget no compare starts), the E1 / E2 rows: TRUE (measured above).
- "the admin-key harness path ... bypasses the gate": true only under ENABLE_COMPARE_AUTH_REQUIRED ON (m4).
- "Flag OFF byte-identical (the committed golden, P01, R54)" and "140 / 140": the identity is true at the record clock; the committed pins are red since 2026-11-02T10:00Z (B1-qb).
- C27 overshoot "bounded by the limiter": true; note that for a free account still in the lifetime-free branch the consume never caps a concurrent burst (that branch is allowed regardless of the daily cap and refusals never bump the lifetime count), so the 10/min limiter is the only bound there (at most about one minute of in-flight requests above the budget per subject). Wording only.
- PR body size 22,976 bytes (<= 25,600); the two non-ASCII spans are the [NATIVE READ] Arabic column and the attribution line, as D8 says.

## Rebase notes for the S81-09 collapse (informational; eaccd550 read with git show only)
- reset_window probes usage_service._usage_window(now) -> (day, next_reset) and usage_service.riyadh_reset_enabled(): both exist with exactly those shapes at eaccd550 (usage_service.py:184 and :240), so the seam already works on the S81-09 merge before the collapse.
- the local allow-list parse equals S81-09 _device_quota_exempt at eaccd550 (:190-212).
- at eaccd550 the text routes still refund with refund_comparison_credit(user_id) and S81-09 carries its device debit in the ContextVar _DEVICE_DEBIT (usage_service.py:337). A post-resolve refusal must give back BOTH the account credit and the S81-09 device debit, or every refusal burns one of the 3 device compares. Worth one end-to-end row at the rebase (the QB02 shape with ENABLE_DEVICE_DAILY_QUOTA ON, sync and stream: the stream refund runs in the event_generator finally).

## NOT MEASURED
- the live Upstash MGET and multi-key EVAL (CROSSSLOT, reply shape): no Lua runtime, no network; the fakes emulate them (stated in the PR body; a canary read).
- a real client disconnect before the refusal event (TestClient cannot drive request.is_disconnected; the Half-B / client_gone arms read by code only; QB05 runs Half-B ON with the client present).
- the full comm set, the CI-order set, the 14 client fences, the full jest suite (correctness / engineering scope); my lens re-ran 12 billing comm files (994 passed) + 9 adjacent files (93 passed).
- the S81-09 composition (the rebase).

## Questions for the gate
- Q-qb1: rule B1-qb (amend the frozen RED; the identity holds at the record clock).
- Q-qb2: add the P06-shaped GET / stream rows (m1) and an EVAL-count assertion on the route-level refusal rows (m2) to the GREEN-owned gate-rows file in the fix round, or carry them as stated limits (LC-4)?
- Q-qb3: confirm D3 with its budget consequence (m6) and the S81-11 widening of R-S10-15 (m7).

## End state
- unit worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s10: HEAD 0523a06fe25e4df3682b26a83daa72bf2f2ee543, `git status --short` empty (0 lines), the two RED shas unchanged (d988882a... / 159fadb8...). Nothing written there.
- scratch worktree: `git worktree remove --force` DEREGISTERED it (absent from `git worktree list`) but stopped on "Filename too long" (a 259-character path; the command ran without -c core.longpaths=true), leaving a plain folder of 2,702 checked-out repo files (54 MB; no .git link, no node_modules junction, verified) at <scratchpad>/S81-10_adv_quotaandbilling. The common brief forbids an agent recursive delete, so it is left for the orchestrator to delete (any delete is safe: no junction inside).
- no pytest of mine left running (every run foreground); no mutation lock left.
- files written (all through the shell or into my own scratch / notes): this report; <scratchpad>/S81-10_adv/qb/ (notes.md, mut_harness.py, mutants.json, mut_results.tsv, manifest_before.tsv, manifest_after.tsv, tracked.txt, my_refgrep.txt, my_pathgrep.txt, comm_sorted.txt, mut_backup/, logs/, test_zz_qb_probe.py = the probe, sha256 5dfa1c92998094dc9d288362c6f7b28397254689564ca36ed2317a02bd2d9711).

## The 35 mutant [pyt] lines (log= paths dropped; logs in <scratchpad>/S81-10_adv/qb/logs/mut/)
```
QM01 KILLED  [pyt] tag=qb-qm01 start=2026-11-02 14:01:57 end=2026-11-02 14:02:06 elapsed=9s bound=600s status=FAIL rc=1
QM02 KILLED  [pyt] tag=qb-qm02 start=2026-11-02 14:02:06 end=2026-11-02 14:02:17 elapsed=10s bound=600s status=FAIL rc=1
QM03 KILLED  [pyt] tag=qb-qm03 start=2026-11-02 14:02:17 end=2026-11-02 14:02:26 elapsed=9s bound=600s status=FAIL rc=1
QM04 KILLED  [pyt] tag=qb-qm04 start=2026-11-02 14:02:26 end=2026-11-02 14:02:34 elapsed=8s bound=600s status=FAIL rc=1
QM07 KILLED  [pyt] tag=qb-qm07 start=2026-11-02 14:02:35 end=2026-11-02 14:02:43 elapsed=8s bound=600s status=FAIL rc=1
QM08 KILLED  [pyt] tag=qb-qm08 start=2026-11-02 14:02:43 end=2026-11-02 14:02:53 elapsed=10s bound=600s status=FAIL rc=1
QM09 KILLED  [pyt] tag=qb-qm09 start=2026-11-02 14:02:53 end=2026-11-02 14:03:02 elapsed=9s bound=600s status=FAIL rc=1
QM10 SURVIVED  [pyt] tag=qb-qm10 start=2026-11-02 14:03:02 end=2026-11-02 14:03:10 elapsed=7s bound=600s status=OK rc=0
QM11 KILLED  [pyt] tag=qb-qm11 start=2026-11-02 14:03:18 end=2026-11-02 14:03:26 elapsed=8s bound=600s status=FAIL rc=1
QM12 KILLED  [pyt] tag=qb-qm12 start=2026-11-02 14:03:27 end=2026-11-02 14:03:35 elapsed=9s bound=600s status=FAIL rc=1
QM13 KILLED  [pyt] tag=qb-qm13 start=2026-11-02 14:03:36 end=2026-11-02 14:03:43 elapsed=8s bound=600s status=FAIL rc=1
QM14 KILLED  [pyt] tag=qb-qm14 start=2026-11-02 14:03:44 end=2026-11-02 14:03:53 elapsed=9s bound=600s status=FAIL rc=1
QM15 SURVIVED  [pyt] tag=qb-qm15 start=2026-11-02 14:03:53 end=2026-11-02 14:04:00 elapsed=7s bound=600s status=OK rc=0
QM16 KILLED  [pyt] tag=qb-qm16 start=2026-11-02 14:04:00 end=2026-11-02 14:04:09 elapsed=8s bound=600s status=FAIL rc=1
QM17 KILLED  [pyt] tag=qb-qm17 start=2026-11-02 14:04:09 end=2026-11-02 14:04:17 elapsed=8s bound=600s status=FAIL rc=1
QM18 KILLED  [pyt] tag=qb-qm18 start=2026-11-02 14:04:17 end=2026-11-02 14:04:26 elapsed=8s bound=600s status=FAIL rc=1
QM19 KILLED  [pyt] tag=qb-qm19 start=2026-11-02 14:04:26 end=2026-11-02 14:04:34 elapsed=8s bound=600s status=FAIL rc=1
QM20 KILLED  [pyt] tag=qb-qm20 start=2026-11-02 14:04:34 end=2026-11-02 14:04:43 elapsed=9s bound=600s status=FAIL rc=1
QM21 KILLED  [pyt] tag=qb-qm21 start=2026-11-02 14:04:50 end=2026-11-02 14:04:59 elapsed=9s bound=600s status=FAIL rc=1
QM22 SURVIVED  [pyt] tag=qb-qm22 start=2026-11-02 14:04:59 end=2026-11-02 14:05:06 elapsed=7s bound=600s status=OK rc=0
QM23 KILLED  [pyt] tag=qb-qm23 start=2026-11-02 14:05:06 end=2026-11-02 14:05:15 elapsed=8s bound=600s status=FAIL rc=1
QM24 KILLED  [pyt] tag=qb-qm24 start=2026-11-02 14:05:15 end=2026-11-02 14:05:24 elapsed=9s bound=600s status=FAIL rc=1
QM26 KILLED  [pyt] tag=qb-qm26 start=2026-11-02 14:05:24 end=2026-11-02 14:05:33 elapsed=9s bound=600s status=FAIL rc=1
QM27 KILLED  [pyt] tag=qb-qm27 start=2026-11-02 14:05:33 end=2026-11-02 14:05:43 elapsed=9s bound=600s status=FAIL rc=1
QM28 KILLED  [pyt] tag=qb-qm28 start=2026-11-02 14:05:43 end=2026-11-02 14:05:50 elapsed=8s bound=600s status=FAIL rc=1
QM29 KILLED  [pyt] tag=qb-qm29 start=2026-11-02 14:05:51 end=2026-11-02 14:05:59 elapsed=8s bound=600s status=FAIL rc=1
QM30 KILLED  [pyt] tag=qb-qm30 start=2026-11-02 14:05:59 end=2026-11-02 14:06:08 elapsed=9s bound=600s status=FAIL rc=1
QM31 KILLED  [pyt] tag=qb-qm31 start=2026-11-02 14:06:08 end=2026-11-02 14:06:17 elapsed=9s bound=600s status=FAIL rc=1
QM34 KILLED  [pyt] tag=qb-qm34 start=2026-11-02 14:06:17 end=2026-11-02 14:06:25 elapsed=8s bound=600s status=FAIL rc=1
QM35 KILLED  [pyt] tag=qb-qm35 start=2026-11-02 14:06:25 end=2026-11-02 14:06:33 elapsed=8s bound=600s status=FAIL rc=1
QM38 KILLED  [pyt] tag=qb-qm38 start=2026-11-02 14:06:39 end=2026-11-02 14:06:43 elapsed=4s bound=600s status=FAIL rc=1
QM39 KILLED  [pyt] tag=qb-qm39 start=2026-11-02 14:06:43 end=2026-11-02 14:06:47 elapsed=4s bound=600s status=FAIL rc=1
QM40 KILLED  [pyt] tag=qb-qm40 start=2026-11-02 14:06:48 end=2026-11-02 14:06:52 elapsed=5s bound=600s status=FAIL rc=1
QM41 KILLED  [pyt] tag=qb-qm41 start=2026-11-02 14:06:52 end=2026-11-02 14:06:57 elapsed=4s bound=600s status=FAIL rc=1
QM42 KILLED  [pyt] tag=qb-qm42 start=2026-11-02 14:06:57 end=2026-11-02 14:07:02 elapsed=5s bound=600s status=FAIL rc=1
```
