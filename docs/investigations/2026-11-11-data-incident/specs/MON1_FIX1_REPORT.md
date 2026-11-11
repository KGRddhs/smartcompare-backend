# MON1 FIX ROUND 1 REPORT (LLM-CREDENTIAL-HEALTH; Opus 5.5 fix agent; 2026-11-12)

Branch fix/inc-mon1-llm-credential-health. Start HEAD c6592b539920b6189552dbc6aa23d7d7be435d91 (verified, status clean). ONE commit 95f50119ac9aeb05d8025bad4400aa6d93c0ad69 through the hook (ruff tier + black passed; not bypassed); not pushed, not rebased, no stash. Status clean after the commit; the node_modules junction untouched. Once merged the unit is "merged, NOT yet proven" (H6).

## Frozen RED files (re-hashed at start and end, unchanged; no frozen row contradicts F1-1/F1-2/F1-3, so no F1-8 stop)
- tests/test_inc_mon1_credential_health.py 10061c0a64da034588602258d5020c015f97e95f7020e9eb0251a2c94bf56c71
- tests/test_inc_mon1_probe.py 2950c33e70d30a3dd69361a9726ce1421b778c4a9a00354067b213a530845880
- Checked against the new rules: L08 (rejected, ok, rejected cooled -> pending, quota clears it, ok cooled -> pending; events [rejected, ok, quota]); L12 / G2 (one suppressed WARNING, three L1 lines); H08 (the Claude moderation-site 403 is moderation-sourced, so a moderation success clears it); H10 (moderation 401); P13 / P14 (probe rule unchanged).

## Gate-rows file (appended only; G1-G4 byte-identical)
- tests/test_inc_mon1_gate_rows.py before fb468da909539bb85bfb83ffcfa2f1b12f15be33f1ab20597b9650ec097f2b25, after d8a07d4fed1be7e6c62a9f6986972f58b5bfca1389afef27a3f31e567aff05dc (blob = working copy, LF).
- Rows added (11): test_g5_monitor_path_fails_open, test_g6_shutdown_cancels_and_awaits_the_probe_task, test_g7_scope_exit_raising_after_the_send_is_one_event, test_g8_closed_set_guard_sends_nothing, test_g9_health_snapshot_returns_copies, test_g10_cooldown_is_a_fixed_window, test_g11_a_suppressed_rejection_is_never_lost, test_g11_a_transition_out_clears_the_pending_mark, test_g12_a_suppressed_recovery_is_never_lost, test_g13_moderation_success_never_clears_quota_or_dispatch_403, test_g14_moderation_success_clears_a_401_and_only_after_the_call.

## RED step at c6592b53
- [pyt] tag=inc-mon1-fix1-red start=2026-11-12 00:32:48 end=2026-11-12 00:32:55 elapsed=7s bound=600s status=FAIL rc=1 (3 failed, 13 passed)
- FAILED on AssertionError only: G11 (suppressed rejection), G12, G13. The five existing rows stayed green.
- DEVIATION 1: the rulings expected G10-G14 to fail at HEAD. G10, the G11 transition-out row and G14 are GREEN at HEAD because the HEAD bytes already behave that way (the window was already fixed, AM08 being a mutant of correct bytes; HEAD has no pending mark to leave behind; a moderation success already cleared a 401 and note_success already followed the awaited call). Each is proven by a mutant instead.
- Pin mutants at c6592b53 (sha-verified byte copies, each restore sha256-verified, lock .qa-mutation.lock created and removed), all KILLED on AssertionError:
  - A09 view raising -> codeless 503, G5: [pyt] tag=inc-mon1-fix1-red-a09 start=2026-11-12 00:33:49 end=00:33:54 elapsed=4s bound=600s status=FAIL rc=1
  - A09b leaf absent -> 503, G5: [pyt] tag=inc-mon1-fix1-red-a09b end=00:33:59 elapsed=4s status=FAIL rc=1
  - A17b shutdown sets None without cancel/await, G6: [pyt] tag=inc-mon1-fix1-red-a17b end=00:34:05 elapsed=4s status=FAIL rc=1
  - AM17 cancel without await, G6: [pyt] tag=inc-mon1-fix1-red-am17 end=00:34:11 elapsed=4s status=FAIL rc=1
  - A15 fail-safe resends after a post-send scope error, G7: [pyt] tag=inc-mon1-fix1-red-a15 end=00:34:17 elapsed=4s status=FAIL rc=1
  - AM18 closed-set guard removed, G8: [pyt] tag=inc-mon1-fix1-red-am18 end=00:34:22 elapsed=4s status=FAIL rc=1
  - AM22 snapshot returns live records, G9: [pyt] tag=inc-mon1-fix1-red-am22 end=00:34:28 elapsed=4s status=FAIL rc=1
  - AM08 sliding window, G10: [pyt] tag=inc-mon1-fix1-red-am08 end=00:34:34 elapsed=4s status=FAIL rc=1
  - A16 moderation note_success above the call, G14: [pyt] tag=inc-mon1-fix1-red-a16 end=00:34:39 elapsed=4s status=FAIL rc=1

## GREEN step (app/services/llm_credential_health.py only; content_safety_service.py NOT changed)
- F1-1: `_PENDING` {(provider, state): status}. When emit_alert reports a suppressed transition, the mark is set while the provider still holds that state. A same-state (confirming) outcome with a mark and the window expired stamps the cool-down, clears the mark and sends once (the newest status). Any transition clears every mark of that provider without emitting. `_reset_credential_health_state` clears it.
- F1-2: `_cooled(key, now)`: only an emitted event stamps `_LAST_ALERT`; a suppressed one never does (behaviour unchanged, now pinned by G10).
- F1-3: `_moderation_may_clear(prev)`: a moderation success moves `rejected` to `ok` only when the record carried 401 or source moderation; never quota, never a dispatch / probe 403 (then no record, no event). A dispatch success clears any state (unchanged). The moderation call order in content_safety_service already satisfied F1-3 and is now pinned by G14.
- emit_alert now returns bool (True admitted, False suppressed; serper_service ignores it); the send moved into `_send` (the same sys.modules lookup). `_monotonic` is read once per `_transition`, before the lock.
- No new log line (the optional late-event WARNING was NOT added), no flag, no await, no I/O, no new import. Every GC-8 seam kept.
- sha256 (blob = working copy, LF): before c5b22404c6ae713e6af69cc80debc282ed2521adf6636392d243270b9bb5d729, after d1cfd190bb9230b04b726dc0bdc4eba3f94be70b88e268655a3eeb6dd5c65c49.

## Fix mutants on the GREEN bytes (all KILLED on AssertionError; every restore sha256-verified)
- FM1 pending mark removed -> G11/G12: [pyt] tag=inc-mon1-fix1-green-fm1_pending_removed start=2026-11-12 00:36:57 end=00:37:01 elapsed=4s bound=600s status=FAIL rc=1
- FM2 pending emitted without waiting for the cool-down -> G11/G12: [pyt] tag=inc-mon1-fix1-green-fm2_pending_no_wait end=00:37:07 elapsed=4s status=FAIL rc=1
- FM3 window made sliding -> G10: [pyt] tag=inc-mon1-fix1-green-fm3_sliding_window end=00:37:13 elapsed=4s status=FAIL rc=1
- FM4 moderation success clears quota -> G13: [pyt] tag=inc-mon1-fix1-green-fm4_moderation_clears_quota end=00:37:18 elapsed=4s status=FAIL rc=1
- FM5 note_success moved above the moderation call -> G14: [pyt] tag=inc-mon1-fix1-green-fm5_note_success_above_call end=00:37:24 elapsed=4s status=FAIL rc=1
- FM6 mark survives a transition out -> G11 transition-out row: [pyt] tag=inc-mon1-fix1-green-fm6_mark_survives_transition_out end=00:37:30 elapsed=4s status=FAIL rc=1
- FM7 two events for one mark -> G11: [pyt] tag=inc-mon1-fix1-green-fm7_two_events_one_mark end=00:37:36 elapsed=4s status=FAIL rc=1
- FM8 moderation success clears a dispatch 403 -> G13: [pyt] tag=inc-mon1-fix1-green-fm8_moderation_clears_dispatch_403 end=00:37:41 elapsed=4s status=FAIL rc=1

## Gates (every [pyt] summary line)
- [pyt] tag=inc-mon1-fix1-unit-on start=2026-11-12 00:35:35 end=2026-11-12 00:36:02 elapsed=27s bound=600s status=OK rc=0 (ENABLE_LLM_CREDENTIAL_PROBE=true; 2 RED files + gate rows: 146 passed; netguard 0)
- [pyt] tag=inc-mon1-fix1-unit-off start=2026-11-12 00:36:10 end=2026-11-12 00:36:37 elapsed=27s bound=600s status=OK rc=0 (=false; 146 passed)
- [pyt] tag=inc-mon1-fix1-ciorder start=2026-11-12 00:38:05 end=2026-11-12 00:39:32 elapsed=87s bound=1200s status=FAIL rc=1 (1533 passed; 2 failed = tests/test_s81_s24_auth_throttle.py::test_r92_hygiene + ::test_p83_red_file_setenv_hygiene, the base CRLF rows of GC-2; GC-11 order plus test_sentry_service.py and test_sentry_503_suppression.py)
- Comm chunks: 69 files = every test file naming llm_credential_health, content_safety_service, sentry_service or /health, intersected with the RED comm set (comm_reasons.tsv), plus the gate-rows file; lists in MON1_fix1/chunk_00..02.
  - [pyt] tag=inc-mon1-fix1-comm-00 start=2026-11-12 00:39:57 end=2026-11-12 00:41:15 elapsed=78s bound=1200s status=OK rc=0 (2004 passed, 1 skipped)
  - [pyt] tag=inc-mon1-fix1-comm-01 start=2026-11-12 00:41:17 end=2026-11-12 00:44:05 elapsed=168s bound=1200s status=OK rc=0 (2498 passed)
  - [pyt] tag=inc-mon1-fix1-comm-02 start=2026-11-12 00:44:08 end=2026-11-12 00:45:41 elapsed=93s bound=1200s status=FAIL rc=1 (2559 passed, 3 failed)
  - HEAD FAILED (MON1_fix1/head_failed.txt): test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content and the two s24 CRLF rows; all three in base record 23f5330f. `comm -13 base head` = EMPTY.
- ruff (E9,F63,F7,F82; F401,F811,F841) and py_compile clean on the two changed python files; black 26.5.1 --check clean on the 34 ratchet files (and in the hook). Added lines pure ASCII; no key / JWT / PEM / credentialed-URL shape; no digest constant.
- Client jest fences: NOT re-run; no literal they read moves.

## Documentation
- CLAUDE.md (CRLF kept, 1107 CRLF lines): two sentences of the MON1 block rewritten in place: the Alert bullet's cool-down sentence (a fixed window; a suppressed change held pending and emitted once by the first confirming outcome after the window; a change out drops it) and the probe bullet's last sentence (a moderation success no longer clears quota or a dispatch 403, only a 401 or a moderation-raised rejection; a served dispatch clears any state). Working-copy bytes (CRLF): before 4b9bb8be09653ee4806bf027b7a5944ef83f482aa15555f6aee1572ee8eaa71c, after 64f95edc761fd2bd59c3ed7fe36fa0fbb1be3bb926f8fa36ccec61aef2d22e75; blob after e9134bf39380ac567498a65977d54812083d6fdfb5655cfea18a1984d8143131.
- PR body: MON1_fix1/PR_BODY.md, 22,990 bytes (measured with python; limit 25,600). F1-4: PP3 reworded (a redeploy while still rejected adds ONE event to the same issue: its event count rises by one and its "last seen" moves; a second NOTIFICATION only once 24 h have passed since the previous one); owner step 1 says the same in one sentence. F1-5: PP1's serper_keys line made conditional; stated limits L-14 (httpx2 INFO request lines), L-15 (the public count, named for O2), L-16 (the first ok logs the transition line once), L-17 (a process without the Sentry module sends nothing; stamp-then-lookup order ruled as is). Also: the plain-words OpenAI "in use" sentence (A2-4); L-3 and L-9 updated; the defect table and the mutant paragraph gain G5-G14; a fix-round gates section. "merged, NOT yet proven" kept; O2 and O3 named as OPEN. The 4 non-ASCII bytes are the attribution emoji line inherited from the GREEN body (scratch file, not a repo file).
- F1-5 sha labelling: the GREEN report's sha table lists working-copy bytes; for the CRLF files (app/main.py, CLAUDE.md and the edited CRLF service files) those are "working-copy bytes (CRLF)", not blob shas. This report labels every sha it gives.

## Deviations
1. RED step: G10, the G11 transition-out row and G14 are green at c6592b53; each is proven by its mutant instead (AM08 / FM3, FM6, A16 / FM5).
2. G11 is two rows (never-lost and transition-out), so 11 rows were added, not 10.
3. content_safety_service.py is unchanged (the F1-3 rule lives in the leaf; the call order already held).
4. No late-event WARNING added (optional in B.3).
5. emit_alert returns a bool (was None); its one other caller (serper_service) ignores the value.

## Open questions
- None blocking. Noted for the re-verifier: a pending recovery (`ok`) is emitted only on a later served call; with no traffic after a suppressed recovery, the last event stays the outage event until the next call (the probe, when ON, closes this every tick).
