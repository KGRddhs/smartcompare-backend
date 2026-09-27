## W4-13: search_logs records what happened, and the admin readers skip the probe traffic

Findings: PO-RECORDED-MEASURED-01, -07, -10, -11; PO-CATEGORIES-I18N-13; LS-MEASURED-EVIDENCE-07, -08.
PO-RECORDED-MEASURED-17 (anon_id) stays OPEN as its own row for Ahmed (Q5), because a fingerprint-derived id can be re-linked to users.device_fingerprint_hash.

### Defects (measured at ac887e2d, which is 61585c58 plus the auth-only #202)
- **The four admin readers aggregate every row.** 88.6 % of the recorded search_logs series is 13 probe strings. On the fixture, the daily avg_duration is 3,667 ms over 12 rows, where the organic truth is 22,000 ms over 2 rows. popular[0] is 'product1 vs product2'.
- **Failure rows never carry a cost.** Four of the five failure sites pass no `cost`. camera.unsuccessful reads metadata.total_cost, which is always absent there, because the orchestrator puts total_cost at the TOP level.
- **Delivered partials are not marked** in the log.
- **The stream logs its success:False TERMINALS as successes**, with success True and cost 0. These are STREAM_TIMEOUT, INSUFFICIENT_DATA and the moderation refusal. This is consistent with the recorded "0 of 721 stream failures" (an inference: those rows were written by older code).
- **Abandoned streams and mid-stream raises write no row.**
- **/url/compare and POST /text/quick write no row at all.**
- **Codeless failures and the camera exception log the service's str(e)** into search_logs.error_message.

### Design
There are two per-call flags. Both default OFF and are read with `.strip().lower() in (true, 1, yes, on)`. Each has ONE definition, in database_service.

**ENABLE_SEARCH_LOG_TRUTH (flag 1).** It has no precondition and is a live kill-switch.
- T1: POST/GET failure rows carry `cost`. The value is the top-level total_cost, else metadata.total_cost, else 0.0. NaN, inf, negative, bool, str and an int too large for a float all give 0.0. A top-level total_cost of exactly 0.0 is a valid cost and never falls through to metadata.total_cost (pinned, ruling R11(c)).
- T2: a delivered partial keeps success True and gets error_message 'partial:<stage>'. Only `metadata.partial is True` (W4-4's own stamp) counts; a truthy-but-not-True value such as 1 or 'yes' writes no note (pinned, R11(d)).
- T3: a stream terminal whose payload has `success is False` logs a failure under the NEW label log_search.text_stream.terminal_failure. `is False` is deliberate: a terminal WITHOUT a `success` key keeps HEAD's success row (pinned, R11(b)). Billing is UNCHANGED.
- T4: the stream error row carries the event's own text (already floored by W4-9) and its cost.
- T5: an abandoned or raised stream writes ONE failure row, keyed on client_gone: 'client_gone_before_complete' or 'stream_incomplete'.
- T6: the camera unsuccessful cost uses three rungs (R3):
  1. top-level total_cost + vision;
  2. else metadata.total_cost as-is (the route already added vision);
  3. else vision alone.
- T7: the camera exception row carries vision_cost. Its message is the constant 'camera_exception', never str(e) (post-green R9(b)). Flag OFF keeps today's str(e).
- T8: /url/compare writes a success, failure or exception row on both verbs.
  - The query keeps scheme + host + an explicit port + path. It drops the query string, the fragment and the userinfo (R4).
  - user_id is the caller's id from get_optional_user, or None for an anonymous caller.
  - There is no cost, because compare_from_urls exposes none.
  - The '<2 products' failure logs its own route literal verbatim (R9(a)). Every other codeless message is floored.
- T9: POST /text/quick writes rows (Q7/D1).
- R1: under flag 1, every failure row's error_message passes the SAME W4-9 codeless floor as the response (`_is_codeless_safe_message`, no second allowlist).
  - A coded result logs its message unchanged.
  - A codeless message that is not allowlisted logs INTERNAL_ERROR_FRIENDLY_MESSAGE.
  - Exception rows log constants: 'url_compare_exception', 'quick_compare_exception' and 'camera_exception'.
  - On the stream error row (T4) the floor is defence in depth: the W4-9 SSE floor has already rewritten that same dict in place, so the row-floor mutant (X26) is an accepted EQUIVALENT mutant (ruling R11), not a coverage gap. The row floor stays.
- C3: every NEW or changed failure row is built AFTER its refund fire_and_forget and before the raise. This is pinned at every such site, including the camera exception row (T7), where a raising row builder still fires the reserved-credit refund (authed + metering) and the anon-credit refund (anon gate + metering + fingerprint) (R11(a)). The row builders are TOTAL over any input. That includes a products list holding non-dict items, a non-dict metadata, and an int total_cost too large for a float.
- R2: under flag 1, the existing rows at the five reordered sites (T1 POST failure, T1 GET failure, T4 stream error event, T6 camera.unsuccessful, T7 camera exception) move AFTER their refund. This also REORDERS the fire_and_forget labels on those paths. There is no response, status or SSE change. With flag 1 OFF each of the five keeps HEAD's log -> refund order byte-identically, and the committed ledger now proves that at ALL FIVE sites: T1 POST and GET through the authed POST/GET failure scenarios, and T4, T6 and T7 through the three refund-firing scenarios added in fix round 5 (ruling R14; see "Fix round 5"). Before round 5 no ledger scenario fired a refund at T4/T6/T7, so a refund moved before the flag-OFF log there changed no record.
- The url and quick delivery rows sit after their metering calls.

**ENABLE_SEARCH_LOG_SYNTHETIC_MARKER (flag 2), with the SEARCH_LOG_SYNTHETIC_TOKEN knob.** HARD PRECONDITION: migration 042 is APPLIED.
- log_search gains `is_synthetic=None`. The key is written only when it is not None AND flag 2 is ON.
- Every site passes the caller's classification, including both /url/compare verbs. A request is synthetic when the X-Qaren-Synthetic header equals the token:
  - both must be non-empty, checked before the compare (C2);
  - the compare is compare_digest over bytes with surrogateescape;
  - there is no broad except.
- The four readers select `, is_synthetic` and drop rows where it `is True`; NULL and False rows are kept. The three dict readers report `synthetic_excluded`.
- The shared Sentry request scrub (`_scrub_request_region`, used by both before_send and before_send_transaction) redacts X-Qaren-Synthetic (D4).
- scripts/eval_runner.py sends the header only when the token is set.
- The token is least-privilege: if it leaks, the holder can mark or hide only their OWN traffic. Rotation is to set a new value on Railway `web` and in the eval runner's env. No code changes.

### Flag rows (CLAUDE.md, at merge)
| name | default | effect ON | flag-OFF identity | knobs |
|---|---|---|---|---|
| ENABLE_SEARCH_LOG_TRUTH | OFF, read per call | T1-T9 + R1 + R9 as above; no client-visible byte changes | committed pin `tests/test_w4_13_flag_off_ledger.py` + `tests/fixtures/w4_13_flag_off_ledger.json`: 45 scenarios recorded at the pre-unit base, asserted record by record at HEAD (every log_search site's kwargs in call order, the fire_and_forget labels in call order -- which include the refund labels, so the log -> refund order is pinned at all five sites flag 1 reorders -- and the status and body or SSE chunks) | none |
| ENABLE_SEARCH_LOG_SYNTHETIC_MARKER | OFF, read per call | the writer key, the reader filter and synthetic_excluded | the same committed ledger: its `readers` scenarios (select strings + outputs), its `inserts` scenario (the four insert records the REAL log_search builds, no `is_synthetic` key) and its `eval_headers` scenario; plus pins 8, 10 and 16. Pin 10 alone covers "the kwarg passed while flag 2 is OFF", because the base writer rejects that kwarg and no recorded call can pass it | SEARCH_LOG_SYNTHETIC_TOKEN (secret, read per call, never logged; rotation = new value on web + eval env) |

### APPLY_PACK row: 042
Apply 042 AFTER merge and BEFORE flag 2. To roll back, turn flag 2 OFF FIRST, then run rollback/042, which discards the classification.
- The census is an OPERATOR instruction (R5, no DO block). The Supabase SQL editor wraps one pasted multi-statement script in one transaction, so paste the census, the body and the AFTER check into ONE run.
- **One transaction is not one snapshot (R12).** At PostgreSQL's default READ COMMITTED isolation each statement takes its own snapshot, while now() is fixed at transaction start. A probe-string row committed between the census SELECT and the UPDATE (with created_at before that now()) is therefore TAGGED but NOT COUNTED, and AFTER may exceed BEFORE - EXCLUDED by exactly that many rows. Pause the eval runner (and any other probe harness) for the apply. Otherwise, accept a small positive difference and re-run the census afterwards.
- Paste back three numbers: BEFORE = a + b, EXCLUDED = c, and AFTER = BEFORE - EXCLUDED (or slightly more, per the line above). Paste a_pull and c_pull beside them for the anchor.
- Sanity anchors from the 2026-09-02 pull: a_pull = 11,724 and c_pull = 295, so the pull window tags 11,429. The organic series re-states to 1,808 rows / 82.08 % / p50 20,937 ms. The live buckets a and c also count pre-June rows and rows written since the pull, so a > 11,724 or c > 295 is expected, not an anomaly.
- Residual ambiguity: the 295 excluded probe-#1 rows (>= 10 s) may still be probes, and probe-#1 rows under 10 s may be users.

### Activation order
1. **Flip flag 1 alone.** Publish the KPI series change the day it flips; both effects below are definition changes.
   - Under T5/T3, abandoned streams and moderation/timeout terminals count as FAILURES in get_error_stats, so the stream failure rate rises from 0.
   - Failure rows now carry a cost, so the cost KPI rises.
2. **Apply 042**, using the paste-back above, with the eval runner paused.
3. **Set SEARCH_LOG_SYNTHETIC_TOKEN** on web and in the eval env, then flip flag 2.
4. **Run the one-minute canary.** The count of rows written after the flip must be > 0. log_search swallows insert errors, so silence means a missing column. Then check that the count of `is_synthetic IS NULL` rows after the flip is 0.

### Gates (fix round 5, on the final bytes; the box was idle)
Every pytest run went through the bounded runner with the pinned venv. The runner added the process-wide netguard plugin (`-p qaren_netguard`, log header `plugin=True`) by itself, because this worktree's tests/conftest.py predates the conftest guard (the hermeticity unit is not merged yet). The worktree HEAD is still ac887e2d, deliberately not rebased; current main is 16800eb6. `git diff --name-only ac887e2d 16800eb6` touches none of this unit's code or test files, and neither ci.yml nor tests/.pre_impl_failures.txt (it changes app/main.py, price_service, structured_comparison_service, url_extraction_service, two test_retro_w0_4* files and docs, including the session-68 state folder's copies of W4-13 spec/report documents).
- **Unit files (4):** test_m18_preverdict_disconnect_refund.py, test_migration_042_search_logs_is_synthetic.py, test_w4_13_flag_off_ledger.py and test_w4_13_measurement_truth.py. 243 passed, blocked 0, in all 4 flag states (unset; flag 1; flag 2 + token; both + token), about 5 s each.
- **CI-order set (21 files, one process per state, CI's deselects):** 701 passed, 0 failed, in all 4 states. blocked 17 / 46 / 17 / 46, every one at the fail-open neutralized.supabase.invalid:443 insert.
- **Preserve set (34 files = the spec's 32 + ruling C10's two):** 786 passed, 10 deselected, in all 4 states. blocked 29 / 58 / 29 / 58, every target a fail-open Supabase insert or getaddrinfo api.openai.com.
- **Comm set: not re-run in fix round 5.** Only test-side files changed this round (the ledger generator, its fixture and the ledger test); no app, script, migration or rollback byte moved since fix round 3, and the ledger test is covered by the unit and CI-order runs above. The last comm run (fix round 4, HEAD, flags + token unset, the recorded 119 files in CI order, 5 chunks of at most 25, CI's deselects) gave 4 failed / 3116 passed / 4 skipped, blocked 435. The 4 failures are the guard-caused SSRF DNS nodes, all in .qa-s68/specs/W4_13_comm_base_failed.txt, so `comm -13` against the base failed set was EMPTY (the spec's recorded 113-file base run at 61585c58 also reported blocked 435; R13: base unchanged).
- **Committed flag-OFF ledger (R10 + R14 + R15):** 45 records, records sha 019611da. It was re-recorded in fix round 5 at the pre-unit base ac887e2d, in a detached scratch worktree with the round-5 generator and the head helper module copied in (cmp-identical; test_retro_w2_1.py is identical at base and HEAD), flags + token unset; a probe confirmed app.__file__ inside the scratch worktree and a log_search signature without `is_synthetic`, so the base code ran. It was then re-derived record by record, 0 of 45 differing each time, at base2 (a second base run), at HEAD (the committed ledger test, green in all 4 flag states) and at current main 16800eb6 (a second detached scratch worktree). Against the round-4 recording (sha 9cabe14b): 3 records ADDED and 4 camera records' labels MOVED (R15); the other 38 records are byte-identical (see "Fix round 5").
- **Mutation (byte snapshots through the runner, flags + token unset, every restore sha-verified):**
  - R14 (the adversary's own edits, reused verbatim): N1, the camera.unsuccessful refunds moved before the flag-OFF log: 1 red, the committed ledger test, record camera.insufficient.meter_True.authed. N2, the camera-exception refunds moved before the flag-OFF log: 1 red, the committed ledger test, record camera.raise.meter_True.authed. N3, the stream error-event refund moved before the flag-OFF log: 1 red, the committed ledger test, record stream.error_event.authed_consumed. Each moved record differs only in its label order (refund label first).
  - X20, the camera success-site `_truth and` guard dropped: 1 red, the committed ledger test.
  - X11b, the T7 row moved before the camera refunds: 2 red (the camera_exception and camera_exception_anon C3 nodes).
  - X7, T3's `is False` weakened to falsy: 1 red.
  - X14, `v < 0` weakened to `v <= 0`: 1 red.
  - X15, `partial is True` weakened to truthy: 2 red.
  - R12a (the whole pre-R12 042 file restored) and R12b (the old "no row lands in between" sentence re-inserted): 1 red each, the R12 header pin.
  - INS1, log_search writes `is_synthetic` unconditionally: 3 red, including the committed ledger test.
  - INS3, `error_message` dropped from the insert record: 2 red, including the committed ledger test.
  - INS2, the flag-2 check dropped, is killed only by pin 10 (`test_log_search_record_flag_off_identical`; measured in fix round 4, unchanged app bytes since).
  - R15 in the generator: removing BOTH the per-scenario label copies and the fire_and_forget unwind makes the committed ledger test red (6 of 45 records moved: the pile-up returns). Removing only one half is an EQUIVALENT mutant (243 passed each, measured): the copy alone and the unwind alone each give every record exactly its own labels. Both halves are kept, as R15 rules.
  - X26 is an accepted equivalent mutant (see R1 above).
  - The earlier rounds' 39 mutants were killed on the round-2 bytes and were not re-run. The seven app/script files and migrations/rollback/042 are sha-identical to the pre-round-3 snapshot. migrations/042_search_logs_is_synthetic.sql DID change after the round-2 table: fix round 3 rewrote its header under ruling R12 (sha 6ba7faf5 -> f56d3a29). The change is comment-only (every non-comment line is identical, measured), so the round-2 body mutants M23/M24 still stand; the header change itself is covered by R12a/R12b above.
- **Lint:** ruff E9,F63,F7,F82 clean and py_compile clean on the two .py files changed this round (and on the 12 changed or new .py files in fix round 4). sqlfluff 4.3.0 was clean on 042 + rollback in fix round 4; neither file changed since. `git diff --name-only -- app/ scripts/` is still exactly the six ruled app files + scripts/eval_runner.py.
- **Corpus:** scripts/verify_flag_byte_identity.py is N/A. This is not a price-path unit, and that harness drives extract_price_from_html only.

### Fix round 3 (Fable rulings R10-R13, after adversary round 2 returned SOUND)
- **R10: the C7 call ledger is a committed pin.** Before, the HARD flag-OFF identity rule was guarded at one site (the camera success-site cost selector) only by a scratch file. The pin is made of three files:
  - `tests/fixtures/_gen_w4_13_flag_off_ledger.py` is the generator. Its app imports are lazy, and it is regenerated only through a pytest probe. Its docstring carries a regeneration log.
  - `tests/fixtures/w4_13_flag_off_ledger.json` holds the records (42 at fix round 3; 45 since the fix-round-5 regeneration). Its `_meta` names the generator, the recording commit and the rule.
  - `tests/test_w4_13_flag_off_ledger.py` pins the exact scenario count (now 45) and compares record by record.
  - The fixture has been deliberately regenerated twice at the same base ac887e2d, each time stated in the generator's log: fix round 4 (the `inserts` scenario, see below) and fix round 5 (R14 added three refund-firing scenarios; R15 stopped the camera records' labels piling up across scenarios, which moved four camera records' labels -- see "Fix round 5").
- **R11: four predicates pinned.**
  - (a) The camera exception row joins the C3 set: a raising row builder still fires both camera refunds.
  - (b) A stream terminal without a `success` key keeps HEAD's success row under flag 1.
  - (c) A top-level total_cost of 0.0 is logged as 0.0, with metadata 0.02 beside it.
  - (d) metadata.partial of 1 or 'yes' writes no partial note.
- **R12: the 042 header states READ COMMITTED truth.** The old "no row lands in between" guarantee is gone. The header pin asserts the corrected sentence and the pause instruction.

### Fix round 4 (adversary round 3: two minors, one prove-nothing row)
- **The ledger's `inserts` scenario was vacuous; it is not any more.** The generator runs all its scenarios under one monkeypatch. The five url scenarios patch `database_service.log_search` with a recording stub, and that patch was still active when the generator made its four direct `log_search` calls. So the scenario recorded `[]` at base and at HEAD and pinned nothing about the insert record, which is exactly where flag 2's `is_synthetic` key is written.
  - The generator now captures the REAL writer before any scenario runs, re-binds it before the four calls, and asserts that exactly 4 insert records were captured.
  - The fixture was deliberately regenerated at ac887e2d. Only `inserts` moved (`[]` to the 4 records).
  - The fixture-header test now also asserts that `inserts` holds 4 records and none carries `is_synthetic`.
  - INS1 and INS3 now redden the committed ledger test. INS2 cannot, as stated in the flag table.
- No app, script, migration or rollback file changed in fix round 4.

### Fix round 5 (adversary round 4: SOUND with three minors and one prove-nothing row; Fable rulings R14-R16)
- **R14: the ledger now proves R2's flag-OFF log -> refund order at all five reordered sites.** Adversary round 4 showed that no committed scenario fired a refund at T4, T6 or T7 (every camera scenario was anonymous without a fingerprint, and the stream error event was anonymous), so N1/N2/N3 survived the unit files and the CI-order set. Three scenarios were added, recorded at base ac887e2d through the committed generator:
  - `camera.insufficient.meter_True.authed`: INSUFFICIENT_DATA, authed, metering ON, so `_refund_reserved_credit` fires at camera.unsuccessful (T6). Labels at base: log_search.camera.unsuccessful, then usage_refund.image.comparison_unsuccessful.
  - `camera.raise.meter_True.authed`: the compare raises, authed, metering ON, so the camera-exception refund fires (T7). Labels at base: log_search.camera.failure, then usage_refund.image.comparison_failed.
  - `stream.error_event.authed_consumed`: the stream error event, authed with a CONSUMED credit, so its refund fires (T4). Labels at base: log_search.text_stream.failure, then usage_refund.text_stream.
  - Each record's `labels` is the fire_and_forget sequence (log_search is itself fire_and_forget'd), so the ORDER of the log and the refund is part of the record. The generator asserts each refund actually fired (non-vacuity) but deliberately not their order; the order is pinned by the record comparison and, statically, by the fixture-header test (log label before refund label in each of the three committed records).
  - Measured: N1, N2 and N3 each redden `test_flag_off_ledger_equals_the_pre_unit_recording_record_by_record`, each moving exactly its own new record.
  - All three refunds fired at base from the existing helpers (tests.test_w4_13_measurement_truth `_camera` / `_stream` with `user=AUTHED`, `meter=True`, `consumed=True`), so no context had to be invented.
- **R15: the camera records no longer pile up labels.** test_retro_w2_1._install wraps whatever `image_routes.fire_and_forget` currently is, so under the generator's single monkeypatch each camera scenario's wrapper chained over the previous ones and appended to every earlier scenario's live label list. The generator now re-binds the real `image_routes.fire_and_forget` before every camera scenario (and once after the last) and snapshots each scenario's lists as its own copies. The unit test helpers are unchanged. The regeneration at base moved exactly these four records, labels only:
  - camera.delivered.meter_False: 5 labels -> ['log_search.camera.success']
  - camera.insufficient.meter_False: 4 labels -> ['log_search.camera.success']
  - camera.delivered.meter_True: 3 labels -> ['log_search.camera.success']
  - camera.insufficient.meter_True: 2 labels -> ['log_search.camera.unsuccessful']
  - camera.raise already carried its single label and did not move. The fixture-header test now pins that every camera record carries exactly one log_search label per recorded log_search call.
- **R16: pr_text corrections.** The Gates section no longer claims that no migration byte changed since round 2 (042's header changed in fix round 3, comment-only); main is named as 16800eb6; the R2 paragraph and the flag table now say the ledger proves the flag-OFF log -> refund order at all five reordered sites; the R10 paragraph records the fix-round-5 regeneration.
- Only the generator, the fixture and the ledger test changed in fix round 5. Every other unit file keeps its round-4 sha.

### Stated limits
- **CD-wave-diffs-02.** Under flag 1, for success:False terminals the stream LOG says failure while the BILL says delivered. This lasts until W4-13b.
- **The NULL window.** Rows from 2026-09-03 to the flag-2 flip are never classified, and the readers count them as organic permanently. Measure the window at activation.
- **D2.** The sync CONTENT_UNAVAILABLE exits (prefilter and moderation_api) carry no total_cost, so T1 logs 0.0 for a PAID moderation_api run.
- **URL rows carry cost 0.0.**
- **The readers have no .range().** The PostgREST max-rows cap can silently truncate any aggregate. The flag-2 canary on /admin/stats/popular can pass or fail on truncation alone.
- **The pre-existing str(e) leak.** The leak of str(e) into error_message on POST/GET codeless failures and on the camera exception stays byte-identical with flag 1 OFF (pinned). Only flag 1 closes it.
- **Harness marker.** Only eval_runner marks its traffic.
- **Camera cost sum.** The camera's rung-1 sum of two finite floats can in theory round to inf, for example 1e308 + 1e308. That is not client-visible: log_search swallows the insert error.
- **042 apply-time race.** Under READ COMMITTED, a probe row committed mid-script can make AFTER exceed BEFORE - EXCLUDED. The header says so and says to pause the eval runner.
- **Ledger scope.** The committed ledger pins flag-OFF identity over its 45 recorded scenarios. A new flag-OFF log_search site that no scenario drives needs its own pin; AST test 11 and pin 16 cover site presence and kwargs. The anon-credit refund (`_refund_anon_credit`) at T6/T7 fires in no ledger scenario; its order relative to the flag-OFF log is not pinned there (the reserved-credit refund, which sits beside it in the same block, is).

### Follow-ups
- W4-13b: the stream meters success:False terminals.
- W4-13c: the synthetic header for bias_matrix_probe.py, bundle_d_prod_smoke.py and run_validation_matrix.py.
- PO-RECORDED-MEASURED-01c: the readers have no .range() (the PostgREST cap).
- D2: add total_cost to the moderation-refusal and CONTENT_UNAVAILABLE exits.

### CLAUDE.md corrections for the docs PR
- Add the two flag rows and the knob.
- Add the 042 row to the Migrations line: apply AFTER merge and BEFORE flag 2, with the eval runner paused, and turn flag 2 OFF before rollback. 039 stays reserved.
- Record that the analytics readers filter only under flag 2.
- Record that search_logs.error_message may carry 'partial:<stage>' on success rows, and the constants 'url_compare_exception', 'quick_compare_exception' and 'camera_exception' under flag 1.
- Record that the flag-OFF identity of the log_search call sites (kwargs, labels in call order including the refund labels, responses), of the four readers, of the log_search insert record and of the eval-runner headers is pinned by the committed ledger `tests/fixtures/w4_13_flag_off_ledger.json` over its 45 scenarios. Any change to a flag-OFF log_search call is a deliberate regeneration through its generator, stated in the PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
