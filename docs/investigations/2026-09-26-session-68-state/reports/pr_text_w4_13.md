## W4-13: search_logs records what happened, and the admin readers skip the probe traffic

Findings: PO-RECORDED-MEASURED-01, -07, -10, -11; PO-CATEGORIES-I18N-13; LS-MEASURED-EVIDENCE-07, -08.
PO-RECORDED-MEASURED-17 (anon_id) stays OPEN as its own row for Ahmed (Q5), because a fingerprint-derived id can be re-linked to users.device_fingerprint_hash.

### Defects (measured at ac887e2d, which is 61585c58 plus the auth-only #202)
- **The four admin readers aggregate every row.** 88.6 % of the recorded search_logs series is 13 probe strings. On the fixture, the daily avg_duration is 3,667 ms over 12 rows, where the organic truth is 22,000 ms over 2 rows. popular[0] is 'product1 vs product2'.
- **Failure rows never carry a cost.** Four of the five failure sites pass no `cost`. camera.unsuccessful reads metadata.total_cost, which is always absent there, because the orchestrator puts total_cost at the TOP level.
- **Delivered partials are not marked** in the log.
- **The stream logs its success:False TERMINALS as successes**, with success True and cost 0. These are STREAM_TIMEOUT, INSUFFICIENT_DATA and the moderation refusal, and they are the "0 of 721 stream failures".
- **Abandoned streams and mid-stream raises write no row.**
- **/url/compare and POST /text/quick write no row at all.**
- **Codeless failures and the camera exception log the service's str(e)** into search_logs.error_message.

### Design
There are two per-call flags. Both default OFF and are read with `.strip().lower() in (true, 1, yes, on)`. Each has ONE definition, in database_service.

**ENABLE_SEARCH_LOG_TRUTH (flag 1).** It has no precondition and is a live kill-switch.
- T1: POST/GET failure rows carry `cost`. The value is the top-level total_cost, else metadata.total_cost, else 0.0. NaN, inf, negative, bool, str and an int too large for a float all give 0.0.
- T2: a delivered partial keeps success True and gets error_message 'partial:<stage>'.
- T3: a stream success:False terminal logs a failure under the NEW label log_search.text_stream.terminal_failure. Billing is UNCHANGED.
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
- C3: every NEW or changed failure row is built AFTER its refund fire_and_forget and before the raise. The row builders are TOTAL over any input. That includes a products list holding non-dict items, a non-dict metadata, and an int total_cost too large for a float (fix round 2, below).
- R2: under flag 1, the existing T1/T4/T6/T7 rows move AFTER their refund. This also REORDERS the fire_and_forget labels on those paths. There is no response, status or SSE change.
- The url and quick delivery rows sit after their metering calls.

**ENABLE_SEARCH_LOG_SYNTHETIC_MARKER (flag 2), with the SEARCH_LOG_SYNTHETIC_TOKEN knob.** HARD PRECONDITION: migration 042 is APPLIED.
- log_search gains `is_synthetic=None`. The key is written only when it is not None AND flag 2 is ON.
- Every site passes the caller's classification, including both /url/compare verbs. A request is synthetic when the X-Qaren-Synthetic header equals the token:
  - both must be non-empty, checked before the compare (C2);
  - the compare is compare_digest over bytes with surrogateescape;
  - there is no broad except.
- The four readers select `, is_synthetic` and drop rows where it `is True`; NULL and False rows are kept. The three dict readers report `synthetic_excluded`.
- The shared Sentry request scrub redacts X-Qaren-Synthetic in both hooks (D4).
- scripts/eval_runner.py sends the header only when the token is set.
- The token is least-privilege: if it leaks, the holder can mark or hide only their OWN traffic. Rotation is to set a new value on Railway `web` and in the eval runner's env. No code changes.

### Flag rows (CLAUDE.md, at merge)
| name | default | effect ON | flag-OFF identity | knobs |
|---|---|---|---|---|
| ENABLE_SEARCH_LOG_TRUTH | OFF, read per call | T1-T9 + R1 + R9 as above; no client-visible byte changes | C7 ledger base -> head -> base2 identical record by record (331d21a9, 42/42) | none |
| ENABLE_SEARCH_LOG_SYNTHETIC_MARKER | OFF, read per call | the writer key, the reader filter and synthetic_excluded | the same ledger; pins 8, 10 and 16 | SEARCH_LOG_SYNTHETIC_TOKEN (secret, read per call, never logged; rotation = new value on web + eval env) |

### APPLY_PACK row: 042
Apply 042 AFTER merge and BEFORE flag 2. To roll back, turn flag 2 OFF FIRST, then run rollback/042, which discards the classification.
- The census is an OPERATOR instruction (R5, no DO block). The Supabase SQL editor wraps one pasted multi-statement script in one transaction, so pasting the census, the body and the AFTER check into ONE run is the same-transaction guarantee.
- Paste back three numbers: BEFORE = a + b, EXCLUDED = c, and AFTER = BEFORE - EXCLUDED.
- Sanity anchors from the 2026-09-02 pull: a = 11,724 and c = 295, so AFTER = 11,429 tagged. The organic series re-states to 1,808 rows / 82.08 % / p50 20,937 ms. Live counts will be >= these anchors because of rows written since the pull.
- Residual ambiguity: the 295 excluded probe-#1 rows (>= 10 s) may still be probes, and probe-#1 rows under 10 s may be users.

### Activation order
1. **Flip flag 1 alone.** Publish the KPI series change the day it flips; both effects below are definition changes.
   - Under T5/T3, abandoned streams and moderation/timeout terminals count as FAILURES in get_error_stats, so the stream failure rate rises from 0.
   - Failure rows now carry a cost, so the cost KPI rises.
2. **Apply 042**, using the paste-back above.
3. **Set SEARCH_LOG_SYNTHETIC_TOKEN** on web and in the eval env, then flip flag 2.
4. **Run the one-minute canary.** The count of rows written after the flip must be > 0. log_search swallows insert errors, so silence means a missing column. Then check that the count of `is_synthetic IS NULL` rows after the flip is 0.

### Gates
The fix-round-2 bytes were measured with the process-wide netguard plugin (`-p qaren_netguard`), because the hermeticity unit is not merged yet.
- **Unit files (3):** 234 passed in all 4 flag states (unset, flag 1, flag 2 + token, both + token), blocked 0.
- **CI-order set (20 files, one process per state):** 692 passed x4, 0 failed; blocked 17 (OFF / flag 2) and 46 (flag 1 / both).
- **Preserve set (34 files):** 786 passed, 10 deselected x4; blocked 29 / 58.
  - The both-state run hit one environmental 120 s timeout inside conftest's event-loop socketpair accept, the same box pathology the adversary saw. The re-run at --timeout=300 gave 786 passed.
- **Comm set (119 files):** HEAD gave 4 failed / 3109 passed / 4 skipped. The 4 are the guard-caused SSRF DNS nodes; they fail identically, run alone, at base ac887e2d. `comm -13` is empty.
- **Mutation:** 39 mutants, all killed (the fixer's 2 + the adversary round-1 table of 37 re-run on the fixed bytes), every restore sha-verified.
- **C7 ledger:** base = head = base2 = 331d21a9 (42/42 records). The ON ledger has status, body, SSE and raised identical to OFF in all 42.
- **Lint:** ruff E9,F63,F7,F82 clean, py_compile clean, and sqlfluff clean on 042 + rollback.
- **Corpus:** scripts/verify_flag_byte_identity.py is N/A. This is not a price-path unit, and that harness drives extract_price_from_html only.

### Fix round 2 (adversary round 1)
- **`_log_cost_value` called float(v) unguarded.** An int too large for a float (10**400) raised OverflowError. Under flag 1 that turned a 400 into a 500 SERVER_ERROR on POST, GET and /text/quick, measured. The refund still fired.
  - The fix: `float()` now sits in try/except OverflowError, which returns None, so the builder falls through to the next rung.
  - Pins: a direct builder test, and an OFF-vs-ON wire-equality test over POST, GET, quick, camera and the stream terminal.
- **Three previously unpinned behaviours are now pinned:**
  - url rows carry the caller's user_id (R4), on both verbs and every exit;
  - GET /url/compare carries the synthetic classification: its plumbing is now driven through the real GET route, and GET joins the site matrix and pin 34;
  - `_log_products_found` keeps only the dict items of a products list, so a list holding None, str or int items stays a 200.

### Stated limits
- **CD-wave-diffs-02.** Under flag 1, for success:False terminals the stream LOG says failure while the BILL says delivered. This lasts until W4-13b.
- **The NULL window.** Rows from 2026-09-03 to the flag-2 flip are never classified, and the readers count them as organic permanently. Measure the window at activation.
- **D2.** The sync CONTENT_UNAVAILABLE exits (prefilter and moderation_api) carry no total_cost, so T1 logs 0.0 for a PAID moderation_api run.
- **URL rows carry cost 0.0.**
- **The readers have no .range().** The PostgREST max-rows cap can silently truncate any aggregate. The flag-2 canary on /admin/stats/popular can pass or fail on truncation alone.
- **The pre-existing str(e) leak.** The leak of str(e) into error_message on POST/GET codeless failures and on the camera exception stays byte-identical with flag 1 OFF (pinned). Only flag 1 closes it.
- **Harness marker.** Only eval_runner marks its traffic.
- **Camera cost sum.** The camera's rung-1 sum of two finite floats can in theory round to inf, for example 1e308 + 1e308. That is not client-visible: log_search swallows the insert error.

### Follow-ups
- W4-13b: the stream meters success:False terminals.
- W4-13c: the synthetic header for bias_matrix_probe.py, bundle_d_prod_smoke.py and run_validation_matrix.py.
- PO-RECORDED-MEASURED-01c: the readers have no .range() (the PostgREST cap).
- D2: add total_cost to the moderation-refusal and CONTENT_UNAVAILABLE exits.

### CLAUDE.md corrections for the docs PR
- Add the two flag rows and the knob.
- Add the 042 row to the Migrations line: apply AFTER merge and BEFORE flag 2, and turn flag 2 OFF before rollback. 039 stays reserved.
- Record that the analytics readers filter only under flag 2.
- Record that search_logs.error_message may carry 'partial:<stage>' on success rows, and the constants 'url_compare_exception', 'quick_compare_exception' and 'camera_exception' under flag 1.

🤖 Generated with [Claude Code](https://claude.com/claude-code)