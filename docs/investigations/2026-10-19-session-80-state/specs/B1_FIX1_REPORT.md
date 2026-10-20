# B1 fix round 1 report (fix agent, RED-then-GREEN): RESULT-STATUS + TELEMETRY (ENABLE_RESULT_STATUS_METADATA)

Window 2026-10-20 07:25 - 08:25 AST. Worktree C:/Users/SynAckITPC/Documents/AI/sc-s80-b1, branch
feature/s80-b1-result-status. Start: HEAD 2bbd58a9eae6aa172339ee7cc717e875ff2bbc73, `git status --short`
empty, RED shas equal the frozen rows. End: HEAD dacc919e897ebdd539f835686f2f077ebe29e289 (one commit on
the branch, through the pre-commit hook, no push / rebase / stash), `git status --short` empty. Rulings
followed: specs/RULINGS_FIX1_B1.md (binding), with s80-common.txt, PLAN_S80 sections 0-1, RULINGS_R0,
RULINGS_BATCH1 (B1), GATE_B1 and both adversary reports. No .env read, no production / Railway / Supabase /
Sentry / network access; every pytest through pyt.py, one process at a time, none in the background.

Model note (for the orchestrator's model check): this agent ran on Opus 5.5 (claude-opus-5-5), not Fable;
the commit trailer therefore reads `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (deviation 1).

## RED files

| file | sha256 before (frozen) | sha256 after (new frozen set) |
|---|---|---|
| tests/test_s80_b1.py | 88130f327757d9e53feb47bbe877f9a065783b2e3a01f90c623360de46a35dfb | 71a50e8e2e8b643e954eeaabaafcb10b73b3e285bd4a0136d42180b35425a1fc (76,769 B, LF, 0 bytes > 127) |
| tests/test_s80_b1_feedback.py | 0bd1117880ac96cee0aee35832814ae7eee620b6bef09bba7b0513648ea59ab3 | unchanged |

Changes to tests/test_s80_b1.py: F1-7 removed `import os` and `get_optional_user` (C420 / B905 left);
12 nodes appended (F1-1..F1-6); every existing row byte-identical.

RED step at 2bbd58a9 (app bytes unchanged, the extended RED file): 12 failed (exactly the 12 new nodes,
every one an AssertionError, a call that raised there is turned into a value first), 187 passed:
`[pyt] tag=b1fix-red start=2026-10-20 07:37:53 end=2026-10-20 07:38:03 elapsed=10s bound=600s status=FAIL rc=1`
(`[hermeticity] sentinel checked 199 test(s)`, `[netguard] blocked 0 attempt(s) from 0 node(s)`).
Failure reasons: F1-1a/b/c/d + F1-4 `('<exit>', 'supported_result')` vs `unsupported_category` (the
MAJ-1 gap, after the body-side assertions passed: the real orchestrator stamps the conflict pair);
F1-2[*] `(100.0, 150.0) == (None, None)` etc.; F1-2b `(3, 190.0) == (2, 150.0)`; F1-3 `1 == 0`;
F1-5 `'raised OverflowError' == {}`; F1-6 `set() == {gather, post_gather, scoring, verdict}`.

## Rows added (tests/test_s80_b1.py)

- test_b1_f1_1a_emitter_tags_equal_the_stamp_on_a_conflict_body (F1-1; + the reader's totality and the unstamped-body case)
- test_b1_f1_1b_telemetry_equals_stamp_text_post_and_get_conflict_pair (F1-1, real orchestrator via FY25 fakes, explicit pair "Samsung Galaxy S24 phone" / "Dior Sauvage eau de parfum")
- test_b1_f1_1c_telemetry_equals_stamp_camera_conflict_body (F1-1)
- test_b1_f1_1d_telemetry_equals_stamp_stream_conflict_pair (F1-1, the stream route)
- test_b1_f1_4_stream_twin_captures_categories_before_the_write_back (F1-4 / X18s + the stream message)
- test_b1_f1_2_profile_site_skips_stamped_non_supported_rows[prices|names|images] (F1-2, P8-style per site + the one-reader identity)
- test_b1_f1_2b_profile_routes_skip_stamped_non_supported_rows (F1-2, /profile/monthly-stats + /profile/recent-decisions)
- test_b1_f1_3_training_data_fields_are_not_auditable_evidence (F1-3, pure + builder)
- test_b1_f1_5_wall_helpers_are_total_on_non_finite_and_non_int_walls (F1-5, incl. the emitter's elapsed_ms fallback)
- test_b1_f1_6_partial_stage_tag_is_whitelisted_to_the_server_constants (F1-6, the set read from the scs source by AST)

## GREEN hunks (smallest additive; flag first in every gated predicate unchanged)

- app/services/result_gate.py (LF): `MODEL_KNOWLEDGE_MARKERS = {tier3_synthesis, training_data}` used by
  `_tier3_fields` (F1-3); `PARTIAL_STAGES` (F1-6); `_finite` (F1-5: `_num(v) and v == v and v not in (inf,
  -inf)`); `stamped_product_categories(result)` = the ONE reader of `metadata.product_categories` (F1-1);
  `_bucket` / `telemetry_extras` / `stamp_camera_stage_timings` use `_finite`; `telemetry_tags` assesses with
  the stamped categories when no assessment is passed and whitelists `partial_stage`.
- app/services/sentry_service.py (CRLF): imports the reader; `capture_result_status` assesses with
  `product_categories=stamped_product_categories(result)`; the `elapsed_ms` fallback passes the raw value to
  the total helpers (a non-finite elapsed is an absent wall; identical for finite values); docstring per D1-2.
- app/api/profile_routes.py (CRLF): `from app.api.home_routes import _result_status_supported`; the three
  readers return `(None, None)` for a stamped non-supported row (F1-2).
- CLAUDE.md (CRLF kept, non-ASCII count unchanged): the B1 header line and row rewritten in place (D1-1,
  D1-2, D1-4, D1-5, D1-6, F1-1..F1-6, the closed profile limit, both quotas, the measured local-.env hazard).
- PR body: <scratchpad>/B1_green/PR_BODY.md edited in place (copy B1_fix1/PR_BODY.fix1.md, sha256
  db4c3005f52ca9c20d075e475f4ef4718323b84a829004f01806eb0b657b3acd): D1-1..D1-9 incl. D1-3 (X19 killer =
  test_b1_r9_builder_stamps_lane1_supported[*] via section_status['price']), D1-7 (the p5a node name), D1-8
  (`tests/_env_safety.py` dropped), D1-9 (X22a / M16 / M9 accepted; M11 now killed; X18s pinned), the MYEZ
  table rows, a "Fix round 1" gates section and owner step 3 with both quotas.

Flag OFF byte-identical: P1 (5 values), P2 (nine FY25 digests), P3, P4, P5/P5b, the FY25 node alone and the
W4-13 ledger are green on the fix bytes (below).

## Files (final sha256 on disk = committed bytes)

| file | +/- | sha256 |
|---|---|---|
| CLAUDE.md | +2 -2 | 806f84483dcd0fce63f3a3475d8e8a34a9c1ad55fee407ef0fe56dab10123ed5 |
| app/api/profile_routes.py | +8 -0 | 750b689de9983d1ca63a7c8136dc672f4fe469007d198024de930afbae0fa1ee |
| app/services/result_gate.py | +55 -16 | d591223075d6ccc036e3fe796cc1e73784ea99c9022368b7af4ddb03eae1f69e |
| app/services/sentry_service.py | +8 -6 | a49bc68385afcd6cf76aa43af863e57e8e50e5f226631bb62c2d5a7ef69c569a |
| tests/test_s80_b1.py | +306 -2 | 71a50e8e2e8b643e954eeaabaafcb10b73b3e285bd4a0136d42180b35425a1fc |

## Runs ([pyt] lines verbatim)

```
unit files (both) 226 passed, flag unset   [pyt] tag=b1fix-unit-off start=2026-10-20 07:40:25 end=2026-10-20 07:40:57 elapsed=32s bound=600s status=OK rc=0
unit files (both) 226 passed, flag ON      [pyt] tag=b1fix-unit-on start=2026-10-20 07:41:08 end=2026-10-20 07:41:30 elapsed=22s bound=600s status=OK rc=0
  (both: [hermeticity] sentinel checked 226 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
identity pins alone, flag unset:
  test_s75_fanout_identity 3 passed        [pyt] tag=b1fix-id-s75_fanout_identity start=2026-10-20 07:46:37 end=2026-10-20 07:46:42 elapsed=4s bound=600s status=OK rc=0
  test_w4_13_flag_off_ledger 2 passed      [pyt] tag=b1fix-id-w4_13_flag_off_ledger start=2026-10-20 07:46:42 end=2026-10-20 07:46:47 elapsed=5s bound=600s status=OK rc=0
  test_stage_timings 2 passed              [pyt] tag=b1fix-id-stage_timings start=2026-10-20 07:46:48 end=2026-10-20 07:46:57 elapsed=9s bound=600s status=OK rc=0   ([netguard] blocked 18 attempt(s) from 2 node(s): the base egress class)
  test_s71_u13 137 passed                  [pyt] tag=b1fix-id-s71_u13_compare_auth_req start=2026-10-20 07:46:57 end=2026-10-20 07:47:05 elapsed=8s bound=600s status=OK rc=0
  test_paid_route_metering 21 passed       [pyt] tag=b1fix-id-paid_route_metering start=2026-10-20 07:47:06 end=2026-10-20 07:47:13 elapsed=6s bound=600s status=OK rc=0   ([netguard] blocked 2 attempt(s) from 2 node(s): the sentinel class)
  test_sentry_channels_u8d_unit 141 passed [pyt] tag=b1fix-id-sentry_channels_u8d_unit start=2026-10-20 07:47:13 end=2026-10-20 07:47:29 elapsed=16s bound=600s status=OK rc=0
  test_sentry_channels_u8d 131 passed      [pyt] tag=b1fix-id-sentry_channels_u8d start=2026-10-20 07:47:30 end=2026-10-20 07:47:36 elapsed=7s bound=600s status=OK rc=0
  test_observability 24 passed             [pyt] tag=b1fix-id-observability start=2026-10-20 07:47:37 end=2026-10-20 07:47:40 elapsed=3s bound=600s status=OK rc=0
  test_retro_w1_1 39 passed                [pyt] tag=b1fix-id-retro_w1_1 start=2026-10-20 07:47:40 end=2026-10-20 07:47:52 elapsed=11s bound=600s status=OK rc=0
CLAUDE.md readers 79 passed (row before the last sentence)  [pyt] tag=b1fix-claude-readers start=2026-10-20 07:47:52 end=2026-10-20 07:47:57 elapsed=4s bound=600s status=OK rc=0
CLAUDE.md readers 79 passed (final bytes)                   [pyt] tag=b1fix-claude-readers start=2026-10-20 08:19:56 end=2026-10-20 08:20:03 elapsed=6s bound=600s status=OK rc=0
CI-order set (23 files = GREEN's 20 + test_profile_routes.py, test_profile_priorities_normalize.py, test_w4_12_display_contract.py), flag unset, 1306 passed
                                           [pyt] tag=b1fix-ci-order start=2026-10-20 07:48:30 end=2026-10-20 07:49:21 elapsed=50s bound=1200s status=OK rc=0
  [hermeticity] sentinel checked 1306 test(s); [netguard] blocked 20 attempt(s) from 4 node(s) (test_paid_route_metering x2 sentinel neutralized.supabase.invalid:443, test_stage_timings x2 egress api.openai.com:443 = the baseline class)
CI-order set, flag ON exported (information): 1 failed (test_w4_12_display_contract.py::test_sse_complete_payload_values_unchanged, the local-.env hazard), 1305 passed
                                           [pyt] tag=b1fix-ci-order-on start=2026-10-20 07:49:27 end=2026-10-20 07:50:15 elapsed=48s bound=1200s status=FAIL rc=1
comm set (305 files: GREEN's 305 - tests/_env_safety.py + tests/test_profile_priorities_normalize.py), flag unset, chunks of 25, bound 1200, the four NETWORK_FLAKY_EXCLUDE ids deselected:
  comm-00 798 passed                       [pyt] tag=b1fix-comm-00 start=2026-10-20 07:50:42 end=2026-10-20 07:51:18 elapsed=36s bound=1200s status=OK rc=0
  comm-01 3 failed, 1013 passed, 1 skip    [pyt] tag=b1fix-comm-01 start=2026-10-20 07:51:18 end=2026-10-20 07:52:29 elapsed=71s bound=1200s status=FAIL rc=1
  comm-02 503 passed, 1 skip               [pyt] tag=b1fix-comm-02 start=2026-10-20 07:52:29 end=2026-10-20 07:52:47 elapsed=18s bound=1200s status=OK rc=0
  comm-03 2985 passed                      [pyt] tag=b1fix-comm-03 start=2026-10-20 07:52:47 end=2026-10-20 07:54:24 elapsed=97s bound=1200s status=OK rc=0
  comm-04 612 passed                       [pyt] tag=b1fix-comm-04 start=2026-10-20 07:54:24 end=2026-10-20 07:55:03 elapsed=39s bound=1200s status=OK rc=0
  comm-05 454 passed                       [pyt] tag=b1fix-comm-05 start=2026-10-20 07:55:04 end=2026-10-20 07:55:26 elapsed=22s bound=1200s status=OK rc=0
  comm-06 4 failed, 576 passed             [pyt] tag=b1fix-comm-06 start=2026-10-20 07:55:31 end=2026-10-20 07:56:04 elapsed=33s bound=1200s status=FAIL rc=1
  comm-07 344 passed, 2 errors, 1 xfail    [pyt] tag=b1fix-comm-07 start=2026-10-20 07:56:04 end=2026-10-20 07:56:30 elapsed=25s bound=1200s status=FAIL rc=1
  comm-08 1654 passed                      [pyt] tag=b1fix-comm-08 start=2026-10-20 07:56:30 end=2026-10-20 07:59:32 elapsed=182s bound=1200s status=OK rc=0
  comm-09 1197 passed, 1 skip, 1 xfail     [pyt] tag=b1fix-comm-09 start=2026-10-20 07:59:32 end=2026-10-20 08:01:13 elapsed=100s bound=1200s status=OK rc=0
  comm-10 367 passed, 1 skip               [pyt] tag=b1fix-comm-10 start=2026-10-20 08:01:13 end=2026-10-20 08:02:02 elapsed=49s bound=1200s status=OK rc=0
  comm-11 1152 passed, 35 xfailed          [pyt] tag=b1fix-comm-11 start=2026-10-20 08:02:03 end=2026-10-20 08:02:49 elapsed=46s bound=1200s status=OK rc=0
  comm-12 81 passed                        [pyt] tag=b1fix-comm-12 start=2026-10-20 08:02:50 end=2026-10-20 08:03:02 elapsed=12s bound=1200s status=OK rc=0
  FAILED/ERROR = test_camera_vision.py::TestIdentifyProductsMocked x3, test_page_scraping.py x2, test_personalization_bundle_c.py x2 (the seven tests/.pre_impl_failures.txt rows), test_prompt_truth.py x2 (cold-tiktoken ERRORs): exactly GREEN's 9 -> branch-only-NEW vs GREEN = EMPTY (comm -13 and comm -23 both empty)
comm set, flag ON exported (information; the engineering lens's NOT MEASURED item):
  commON-00 798 passed                     [pyt] tag=b1fix-commON-00 start=2026-10-20 08:03:36 end=2026-10-20 08:04:10 elapsed=34s bound=1200s status=OK rc=0
  commON-01 3 failed, 1013 passed          [pyt] tag=b1fix-commON-01 start=2026-10-20 08:04:13 end=2026-10-20 08:05:33 elapsed=80s bound=1200s status=FAIL rc=1
  commON-02 503 passed                     [pyt] tag=b1fix-commON-02 start=2026-10-20 08:05:33 end=2026-10-20 08:05:49 elapsed=16s bound=1200s status=OK rc=0
  commON-03 2985 passed                    [pyt] tag=b1fix-commON-03 start=2026-10-20 08:05:50 end=2026-10-20 08:07:37 elapsed=107s bound=1200s status=OK rc=0
  commON-04 612 passed                     [pyt] tag=b1fix-commON-04 start=2026-10-20 08:07:39 end=2026-10-20 08:08:36 elapsed=57s bound=1200s status=OK rc=0
  commON-05 454 passed                     [pyt] tag=b1fix-commON-05 start=2026-10-20 08:08:36 end=2026-10-20 08:08:57 elapsed=21s bound=1200s status=OK rc=0
  commON-06 4 failed, 576 passed           [pyt] tag=b1fix-commON-06 start=2026-10-20 08:09:05 end=2026-10-20 08:09:38 elapsed=33s bound=1200s status=FAIL rc=1
  commON-07 1 failed, 343 passed, 2 errors [pyt] tag=b1fix-commON-07 start=2026-10-20 08:09:39 end=2026-10-20 08:10:04 elapsed=25s bound=1200s status=FAIL rc=1
  commON-08 1654 passed                    [pyt] tag=b1fix-commON-08 start=2026-10-20 08:10:04 end=2026-10-20 08:13:05 elapsed=181s bound=1200s status=OK rc=0
  commON-09 1197 passed                    [pyt] tag=b1fix-commON-09 start=2026-10-20 08:13:05 end=2026-10-20 08:14:25 elapsed=80s bound=1200s status=OK rc=0
  commON-10 367 passed                     [pyt] tag=b1fix-commON-10 start=2026-10-20 08:14:26 end=2026-10-20 08:15:19 elapsed=53s bound=1200s status=OK rc=0
  commON-11 1 failed, 1151 passed          [pyt] tag=b1fix-commON-11 start=2026-10-20 08:15:20 end=2026-10-20 08:16:10 elapsed=51s bound=1200s status=FAIL rc=1
  commON-12 81 passed                      [pyt] tag=b1fix-commON-12 start=2026-10-20 08:16:11 end=2026-10-20 08:16:22 elapsed=11s bound=1200s status=OK rc=0
  extra over the OFF run = test_response_builder_winner_card_consistency.py::test_no_mismatch_overview_winner_unchanged and test_w4_12_display_contract.py::test_sse_complete_payload_values_unchanged (exact overview.winner dict vs the stamp's `supported` key)
those two at the GREEN commit 2bbd58a9 (detached scratch worktree <scratchpad>/B1_fix1/wt_green, removed afterwards, `git worktree list` clean):
  flag ON  2 failed                        [pyt] tag=b1fix-green-flagon-hazard start=2026-10-20 08:16:57 end=2026-10-20 08:17:15 elapsed=17s bound=600s status=FAIL rc=1
  flag OFF 2 passed                        [pyt] tag=b1fix-green-flagoff-hazard start=2026-10-20 08:17:16 end=2026-10-20 08:17:26 elapsed=9s bound=600s status=OK rc=0
```
All comm / CI chunks: `[hermeticity]` sentinel counts equal the node counts; netguard blocks only the classes
GREEN recorded (no NEW node class seen in the per-chunk lines; the ratchet script itself was not run).

## Mutation check (fix round; byte copies, exact edits matching once, the F1 rows via pyt.py -k, restored and sha256-compared, .qa-mutation.lock created and removed)

10 applied, 10 KILLED (AssertionError only), 10 restores ok, post-run sha256 -c OK on all four app files.

| id | mutant | killing rows | [pyt] |
|---|---|---|---|
| FM1 | emitter drops the stamped categories | f1_1a, f1_1b, f1_1c, f1_1d, f1_4 | `[pyt] tag=b1fix-FM1 start=2026-10-20 07:42:27 end=2026-10-20 07:42:35 elapsed=9s bound=600s status=FAIL rc=1` |
| FM2 | telemetry_tags fallback drops them | f1_1a | `[pyt] tag=b1fix-FM2 start=2026-10-20 07:42:36 end=2026-10-20 07:42:47 elapsed=11s bound=600s status=FAIL rc=1` |
| FM3 | profile savings skip removed | f1_2[prices], f1_2b | `[pyt] tag=b1fix-FM3 start=2026-10-20 07:42:47 end=2026-10-20 07:42:56 elapsed=9s bound=600s status=FAIL rc=1` |
| FM4 | profile names skip removed | f1_2[names], f1_2b | `[pyt] tag=b1fix-FM4 start=2026-10-20 07:42:57 end=2026-10-20 07:43:05 elapsed=8s bound=600s status=FAIL rc=1` |
| FM5 | profile image skip removed | f1_2[images] | `[pyt] tag=b1fix-FM5 start=2026-10-20 07:43:05 end=2026-10-20 07:43:14 elapsed=9s bound=600s status=FAIL rc=1` |
| FM6 | training_data counts | f1_3 | `[pyt] tag=b1fix-FM6 start=2026-10-20 07:43:15 end=2026-10-20 07:43:19 elapsed=5s bound=600s status=FAIL rc=1` |
| FM7 | X18s stream capture after the write-back | f1_1d, f1_4 | `[pyt] tag=b1fix-FM7 start=2026-10-20 07:43:20 end=2026-10-20 07:43:24 elapsed=5s bound=600s status=FAIL rc=1` |
| FM8 | finite guard removed | f1_5 | `[pyt] tag=b1fix-FM8 start=2026-10-20 07:43:25 end=2026-10-20 07:43:31 elapsed=7s bound=600s status=FAIL rc=1` |
| FM9 | partial_stage whitelist removed | f1_6 | `[pyt] tag=b1fix-FM9 start=2026-10-20 07:43:32 end=2026-10-20 07:43:40 elapsed=8s bound=600s status=FAIL rc=1` |
| M11 | (adversary survivor) tag ignores metadata.partial | f1_6 | `[pyt] tag=b1fix-M11 start=2026-10-20 08:17:57 end=2026-10-20 08:18:20 elapsed=24s bound=600s status=FAIL rc=1` |

Non-pytest: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` clean on the 4 changed .py; py_compile clean;
full default ruff head-vs-fix per file equal (result_gate 0/0, sentry_service 0/0, profile_routes 4/4;
the RED file 5 -> 3 = the two removed F401); `git diff --check` clean; added-line sweep (379 lines): 0
sk- / AKIA / xox / JWT / PEM / credentialed-URL / email / +973 / 8-digit / non-ASCII; line endings kept
(CLAUDE.md, profile_routes.py, sentry_service.py CRLF with 0 bare LF; result_gate.py and the RED file LF).

## Deviations

1. Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, not the Fable 5.1 trailer the
   computed task named: this agent is Opus 5.5 (claude-opus-5-5) and the session's attribution instruction
   names Opus 5.5; writing Fable would claim another model. The orchestrator's model check expected Fable.
2. F1-5 uses `_finite` (`_num(v) and v == v and v not in (inf, -inf)`) instead of `math.isfinite`: the
   frozen P11 purity row pins result_gate's imports to os / re / typing / __future__ / text_sanitize.
3. F1-4 has no hunk (the stream capture already precedes the write-back); its row is RED at 2bbd58a9 only
   through its telemetry half (MAJ-1); FM7 (= X18s) proves the capture half bites on the fix bytes.
4. F1-1: the ONE decider is `result_gate.stamped_product_categories`; it is used by the emitter AND by
   `telemetry_tags`' no-assessment fallback (pinned by FM2), so a direct `telemetry_tags(body)` call equals
   the stamp too.
5. The emitter's `elapsed_ms` fallback now passes the raw value to the total helpers instead of `int()`
   (identical for finite values; a non-finite elapsed no longer drops the whole message).
6. F1-6 "else omitted" read as: a partial body whose `partial_stage` is a str outside PARTIAL_STAGES omits
   the key; a non-partial body or a non-str stage keeps `none` (frozen R17 asserts `none` for non-partials).
7. The CLAUDE.md row and the PR body gained one measured stated limit not named by the rulings: the two
   pre-existing pins that go red with the flag in a local `.env` (found by the flag-ON comm run).
8. The CI-order set grew to 23 files (the pins of the functions this round touched).
9. The PR body draft (outside the repo) keeps the 4-byte robot emoji of the required attribution line.

## Open questions for the gate

1. The two flag-ON local-.env hazard pins (test_response_builder_winner_card_consistency.py::
   test_no_mismatch_overview_winner_unchanged, test_w4_12_display_contract.py::
   test_sse_complete_payload_values_unchanged): accept as a stated limit (done) or a test-only follow-up
   that pops ENABLE_RESULT_STATUS_METADATA in those files (the FY25 E1 pattern)?
2. `home_routes._result_status_supported` is a private name with a second importer now (profile_routes);
   promote it to a public name in a later unit?
3. The model / trailer mismatch (deviation 1).

## NOT MEASURED

- The pre-commit hook test files (D1-10 assigns them, run ALONE, to the re-verifier); this commit itself
  passed the hook.
- scripts/netguard_ratchet.py over a QAREN_NETGUARD_REPORT for the comm runs (per-chunk netguard lines only).
- The spec section 6 mutation table was not re-applied (only the 9 fix-round mutants + M11); X22a, M16 and
  M9 stay accepted survivors per D1-9 (not re-run).

## End state

sc-s80-b1: HEAD dacc919e897ebdd539f835686f2f077ebe29e289 on feature/s80-b1-result-status, `git status
--short` empty, no .qa-mutation.lock, scratch worktree removed, no pytest process of mine alive (every run
synchronous through pyt.py). Notes, scripts and logs: <scratchpad>/B1_fix1/ (notes.md, apply_red.py,
new_rows.py.txt, mutate.py, mutate2.py, mutants*.json, comm_set_fix1.py, comm_files_fix1.txt,
comm_reasons_fix1.tsv, run_gates.py, run_gates_on.py, gates/, logs/, apply_claude_md.py, apply_pr_body.py,
PR_BODY.fix1.md, bytecopy/, this report).
