# S78-F8 adversarial spec review

- Spec under review: `C:/Users/SynAckITPC/Documents/AI/sc-s78-alltimeout/.qa-s78/S78_F8_UNIT_SPEC.md`,
  sha256 `bfd14cc0231256f849b082d4987518a0ff18f75b0840f2304eb03169b6a26c58` (636 lines), identical at the
  start (06:07) and at the end of this review. Not edited.
- Base: worktree HEAD `e0f3e4759052b07a24717384a7a4d462ddadaf21`, tree clean at start and at end
  (`git status --short` empty; only the gitignored `.qa-s78/` and `tests/__pycache__/`).
- Reviewer scratch: `scratchpad/f8/review_agent/` (notes.txt, probe copies, logs, the two prototype
  patch scripts `apply_spec_sketch.py` / `apply_eager_record.py`, `proto_eager_variant.diff`).
- Method: every anchor re-grepped at base; one probe in the worktree (deleted); one GREEN PROTOTYPE in a
  detached scratch worktree at `e0f3e475` with the spec's section 2 sketch applied VERBATIM (additive
  only: 81 insertions, 0 deletions, ruff E9/F63/F7/F82 clean, py_compile clean), then two variants;
  worktree removed (`git worktree list` shows no f8proto).

## Verdict

APPROVE_WITH_CHANGES.

The design fixes the motivating capture (capture-3 shape -> TIMEOUT, measured on the prototype), is
additive, and is flag-OFF identical on everything measured (prototype: existing handler pins 57/57 OFF,
FY25 9/9 OFF and ON). But two behaviours of the sketch contradict the spec's own rules and must be
ruled before RED: (1) the mid-gather arm reports TIMEOUT for a data race that RAISED (D7 is false
there), and (2) the partial-build-failure fall-through reports TIMEOUT while a usable price exists
(the spec's own 7.2, measured reachable and wrong). The camera-consumer claim is refuted, three PIN
rows cannot pass at base, one mutant is equivalent, the D5 level is not pinned, and the comm set misses
12 consumer files.

## Refuted claims (each with the measurement)

RC-1. D7 / section 1.7 Q2 ("D4's mid-gather rule is therefore correct") / F6's "only 'timeout' flips;
an error keeps the base verdict (D7)" / brief D7 "a race that RAISED keeps INSUFFICIENT_DATA".
FALSE for the mid-gather arm. Both done-callbacks swallow `Exception` and write nothing
(scs:5582 `except (asyncio.TimeoutError, asyncio.CancelledError, Exception): pass`, scs:5703 the same),
and a cancel drains the tasks before the loop (scs:5756-5772), so a race that raised before a
mid-gather cap leaves the same identity-only dict as a timed-out one. Measured:
- review probe R1 (specs raises RuntimeError, price hangs, cap 1.0 s): base INSUFFICIENT_DATA, buffer
  both slots `extra_keys []`, `error_fetch_lines []`, `any_runtimeerror_text 0`, the spec predicate
  (2.5, copied verbatim) on that state with the flag ON -> True. R1b (price raises, specs hangs): same.
- GREEN prototype (sketch verbatim, flag ON): P_R1 -> `code TIMEOUT`, keys = the TIMEOUT five, D5 line
  groups (2, 0, 0, 2), `error_lines []`; P_R1b -> TIMEOUT, same. So the user gets "Still gathering
  prices" for an errored race and no log line anywhere names the error.

RC-2. Stated limit 10 (camera) and the brief's "Client camera path" row: "under
ENABLE_CAMERA_FAILURE_ENVELOPE (ON in prod) the envelope carries code: TIMEOUT, so the client
classifies the row 'timeout' (failureClassification.ts:123) instead of 'generic'". FALSE with the
envelope ON. `classifyUnsuccessfulCameraComparison` is called only on the envelope-OFF shape
(`action === 'comparison' && success === false`, SmartCompareApp/src/screens/ResultsScreen.tsx:310-320).
With the envelope ON the body is `action: 'comparison_failed'` (app/api/image_routes.py:117-121), which
ResultsScreen.tsx:338-346 maps to `setLoadError('timeout')` for EVERY non-outage code, INSUFFICIENT_DATA
included (outage codes are routed earlier by `isCameraEngineOutageResponse`, failureClassification.ts:
104-109). So in prod (envelope ON since 2026-10-03) the camera path shows no visible change; only the
failure row's `error_message` moves ("INSUFFICIENT_DATA" -> "TIMEOUT"). The 'generic' -> 'timeout' change
exists only with the envelope OFF.

RC-3. F3 (a), F6 and F7 are labelled PIN with "(passes: probe ...)", but each asserts on
`_phase1_race_outcomes` content: F3 (a) "record slot of A has specs == 'ok'", F6 "record specs ==
'error', price == 'timeout' on both", F7 "under ON the record has price == 'timeout'". The attribute
does not exist at base (`grep -n _phase1_race_outcomes app/` -> 0 hits; review probe
`has_outcomes_attr false` on all 8 shapes), so `getattr(svc, "_phase1_race_outcomes", {})[0]` raises
KeyError (or an AssertionError with `.get`). These rows fail at base; they are not PINs, and as written
they would fail on a KeyError, which the spec's own RED rule forbids. (The verdict halves do pass at
base: probe F3/F6/F7 in spec 1.5; prototype P_F3a/P_F6 INSUFFICIENT_DATA.)

RC-4. Mutation row M22 "record block placed before the loop ... killed by F2 (8 [L2.6] lines), F13".
"Placed before the loop" is an EQUIVALENT mutant: the block only reads `phase1_results` / `phase1_keys`,
both final once the gather returns (scs:5755); between scs:5755 and the loop (scs:5780) it computes the
same dict, logs nothing, mutates nothing. No node can kill it.

RC-5. Spec 1.2, REST H6 row: "No await between 4133 and 4141, so a post-gather all-None pair never
reaches the cap handler." The reason is wrong: the H6 branch itself awaits
`_cancel_profile_task(_profile_task)` at scs:4147 before returning, and `_profile_task` is non-None
whenever `user_id` is set (scs:4116-4120; every authenticated compare). The conclusion probably still
holds because `_cancel_profile_task` swallows the CancelledError (scs:560-574: `except
(asyncio.CancelledError, Exception): pass`), so the impl returns the H6 body even if the cap fires
there; that outcome was NOT measured here.

RC-6. Spec 1.4 camera row / limit 2: "Failure row error_message=result.get("code") ... (526)". There are
two sites, image_routes.py:512 (W4-13 OFF) and :526 (W4-13 ON), both inside `if
unsuccessful_not_billed:` (:503, metering ON).

Confirmed (re-measured, no change needed): every scs anchor of 1.1-1.3 (handler 3853-3900 with the
partial branch 3856, build-failure ERROR 3865-3871, no-usable WARNING 3875-3879, INSUFFICIENT_DATA
3885-3893, TIMEOUT 3894-3900; `_flag_on` 1760-1761; `TIMEOUT_FRIENDLY_MESSAGE` 1696; cap 1632; init
3239-3265; buffer helpers 3519-3547; `_partial_stage` 3549; `_build_partial_response` 3565; resets 3983 /
3991 and 4620 / 4625; gather 4123-4126; stash 4133; H6 4141-4155; stream cap 4759-4821, stream H6
4827-4844; `_fetch_product_data` 5474-6221, registration 5503-5524, `_PHASE1_TIMEOUTS` 5538-5555,
price task 5565-5568, callbacks 5579-5584 / 5694-5705, gather 5755, drain 5756-5772, loop 5780-5798,
`_price_fallback_on_miss` 6376); the Q2 write list (awk over 5474-6221: 5581, 5702, 5791, 5796, 5798,
5906, 6038, 6064, 6088, plus `result.update` 6185 which writes `_shopping_listing_count` only); only
callers of `_fetch_product_data` are 4124/4125/4762/4763; `result` never rebound (one assignment 5503,
the other returns at 5958/5969 are a nested function's); route mapping text_routes.py:521-551; refund
before the surface call (666-677, 694; GET the same); `api_calls` 0 hits in text_routes.py and
image_routes.py; KPI `Counter` analytics_service.py:154-155; per-request instances
(scs:9472-9474); Q6 7 sites in 6 files; Q3 / Q4 / Q5.

## Corrections F8-A1..

F8-A1 (D7, the mid-gather arm; justified by RC-1). Fable chooses one:
- (a) Minimal: keep D3/D4, correct D7 to "only 'timeout' flips the verdict for a RECORDED slot; for a
  slot cut mid-gather a race that raised is indistinguishable from one the cap cut and reports TIMEOUT",
  add it as a stated limit, and add RED rows F19 (`_install_real` specs=`_raise_rt`, price=`_hang`,
  reviews/image return, rating not reached -> TIMEOUT, D5 groups (2,0,0,2), zero ERROR lines) and F19b
  (price raises, specs hangs) so GREEN's behaviour is pinned instead of accidental.
- (b) Preferred: under the flag, record the two DATA races eagerly from done-callbacks on `_price_task`
  and `_specs_task` (`if t.cancelled(): return`; else `"ok"` if `t.exception() is None` else
  `_phase1_race_outcome(t.exception())`), keyed by slot; the recorded arm checks only the keys present
  (`for k in ("specs", "price"): if k in rec and rec[k] != "timeout": return False`, a missing key =
  still running at the cap = timeout); the post-loop block MERGES into the slot dict. Measured on the
  prototype (`apply_eager_record.py` on top of F8-A2): P_R1 / P_R1b -> INSUFFICIENT_DATA; P_F2, P_F1b,
  P_F3b, P_F12 TIMEOUT with the same D5 groups; P_F3a, P_F6 INSUFFICIENT_DATA; flag OFF INSUFFICIENT_DATA
  with `outcomes {}`; FY25 9/9 unmoved ON and OFF; existing pins OFF 66/66 (incl.
  test_lever1_orphan_cancel_i56.py and test_latency_stack_i56.py). Extra mutants to add: callback attached
  under OFF (killed by F4b), cancelled recorded as "timeout"/"error" (killed by F19 with a hang), merge
  replaced by overwrite (equivalent on these shapes; drop or pin a callback-only key).

F8-A2 (rule spec 7.2 IN; justified by RC-1's prototype and probe R2). Measured: probe R2 (F7 shape with
`_build_partial_response` raising): base INSUFFICIENT_DATA after `[L2.7] partial build failed`,
`_partial_has_usable_data()` True, buffer price `{'amount': 9.5, 'currency': 'BHD', ...}`; sketch
prototype -> `code TIMEOUT`, D5 groups (2, 4, 4, 0) "every Phase-1 data race timed out" beside a 9.5 BHD
price; hardened prototype (recorded arm first returns False when `pd.get("specs") is not None or
pd.get("price") is not None`) -> INSUFFICIENT_DATA with P_F2 / P_F1b / P_F3b / P_F12 / P_F3a / P_F6
unchanged. Apply the check to EVERY populated slot (the plan's "identities only"), add F18 row 15
(recorded all-timeout + `price` dict not None -> False), a real-entry RED/PIN row F20 for the R2 shape
(PIN at base, must stay INSUFFICIENT_DATA after GREEN), and mutant M27 "the None check removed" (killed by
F20, F18 row 15). Strike stated limit 8 once ruled in.

F8-A3 (justified by RC-3). Split F3 (a), F6 and F7 into a PIN half (verdict, key set, error text, base
log lines, no CAP_RE line; passes at base) and a RED half (the record content read with
`rec = getattr(svc, "_phase1_race_outcomes", None)`; `assert isinstance(rec, dict)` first so base fails
on an AssertionError, never a KeyError), and update the RED count of gate 5.1.

F8-A4 (justified by RC-4). M22: drop "placed before the loop" (equivalent). Keep "mutating `result` /
`phase1_results`" (killed by F2's base lines and F13), or replace the first half with "placed before the
gather" (NameError on `phase1_results`, killed by every real-entry row).

F8-A5 (D5 level). `_cap_lines` must filter `r.levelno == logging.WARNING` exactly (the spec text "WARNING
records" is ambiguous), and add mutant M26 "D5 line logged at ERROR" (killed by F1). Justification: the
line carries `query=%r`; at ERROR it becomes a Sentry event and breadcrumb
(`LoggingIntegration(level=logging.ERROR)`, app/services/sentry_service.py:651), and no existing pin
catches a NEW in-except ERROR line: tests/test_sentry_channels_u8d_unit.py pins four NAMED in-except
templates (`red_r8_in_except_lines_no_user_content`, prefix list at :876-) and outside-except lines only
(`_outside_except_error_calls` skips calls `_inside_except`, :830-846); the handler line sits inside
`except asyncio.TimeoutError:` (scs:3853).

F8-A6 (justified by RC-2, RC-6). Rewrite limit 10: "with the envelope ON (prod) the client already shows
'timeout' for INSUFFICIENT_DATA (ResultsScreen.tsx:338-346), so the camera UI does not change; with the
envelope OFF, ResultsScreen.tsx:310-320 -> classifyUnsuccessfulCameraComparison moves 'generic' ->
'timeout'". In 1.4 and limit 2 cite image_routes.py:512 and :526.

F8-A7 (comm set). Regenerated: `grep -rlE "structured_comparison_service" tests/ --include=*.py` -> 182
files, all 182 present in `comm_final.txt` (sha matches the spec's 1063f188...). But
`grep -rlE "StructuredComparisonService|get_comparison_service|compare_from_text" tests/` adds 12 files
that name the service or its entry without the module string, none in the spec's list:
tests/test_b2_strict_optional_auth.py, test_category_selection.py, test_http_400_cap_cut_mapping.py,
test_lane1_integration.py, test_m13_03_paid_work_gating.py, test_m13_25_compare_body_maxlength.py,
test_m13_26_image_error_envelope.py, test_m13_35_sse_disconnect_finally.py,
test_m18_preverdict_disconnect_refund.py, test_price_kpi_endpoint.py, test_s71_u13_pins.py,
test_text_routes_error_mapping.py (test_s71_u13_compare_auth_required.py is the 13th and is already in
via the source-scan rule). All mock the service (measured: `AsyncMock` / stub classes patched on
`app.api.text_routes.get_comparison_service` or `image_routes.StructuredComparisonService`), so they
cannot see the change, but they are the route-level consumers of the two bodies and F15 adds a
real-service route node beside them: add them as chunk 09 (12 files), base vs HEAD. No other gap:
every file that globs `*.py` under app/, every CLAUDE.md reader (tests/test_ci_gates.py:934/1392,
tests/test_behavior_dimension_translation.py:226) and the eight named pins are in the list.

F8-A8 (missing consumer). Add `/text/quick` (POST, admin; app/api/text_routes.py:1413-1452) to 1.4 and
limit 2/3: it calls the same `compare_from_text` and maps EVERY failure to `HTTPException(400,
detail=result.get("error"))` (1449-1452), so it stays 400 and its detail text (and its W4-13 failure row,
1442) moves from the INSUFFICIENT_DATA sentence to TIMEOUT_FRIENDLY_MESSAGE.

F8-A9 (Sentry, measured). Add to 1.4: the 400 -> 503 move adds no Sentry event because the FastAPI and
Starlette integrations capture `frozenset(range(500, 600)) - {503}` (sentry_service.py:637, 641, 645);
the D5 WARNING is neither an event nor a breadcrumb (:651).

F8-A10 (justified by RC-5). Replace the 1.2 H6 sentence with the measured facts (await at 4147;
`_cancel_profile_task` swallows CancelledError at 571-574) and mark "the cap handler is not reached from
the H6 branch" as unmeasured, or add a probe row.

F8-A11 (limit 15, measured). With the flag exported ON for the whole existing-pin set on the sketch
prototype, exactly one node of 57 fails:
tests/test_partial_specs_stash_on_price_timeout.py::TestSyncHardCapSalvagesSpecs::test_both_hang_falls_through_to_insufficient_data.
That file never delenvs the new flag and tests/conftest.py loads `.env`, so a developer `.env` carrying
the flag reddens it locally. Add "never set ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT in a local .env" to the
limits and to the CLAUDE.md row (the #55 flush-flag precedent).

F8-A12 (test robustness, minor). The 2.6 regex `for query='.*'` fails when `%r` picks double quotes (a
query containing an apostrophe). Use `for query=.+ -- reporting` or `query=(['"]).*\1`. Latent (the
test queries are fixed).

F8-A13 (consumer note). scripts/verify_after_credits.py `evaluate_compare` (167-175) records the reason
`http_%s`, so these rows move from `http_400` to `http_503`; both are FAIL. Add to 1.4 as a no-op
consumer. `scripts/cron_warm_price_cache.py:225-241` reads only `products`, absent from both bodies.

## Missing items

- A RED row for a data race that raised before a mid-gather cap (F19 / F19b), or the eager-record design
  (F8-A1).
- A real-entry row for the partial-build-failure fall-through (F20) and the F18 row 15 (F8-A2).
- Mutants M26 (D5 at ERROR) and M27 (7.2 check removed); M22 rewritten (F8-A4, F8-A5).
- The 12 symbol-only consumer files in the comm set (F8-A7).
- `/text/quick` in the consumer table (F8-A8); Sentry's 503 exclusion (F8-A9); the canary reason move
  (F8-A13).
- The camera envelope-ON client branch (ResultsScreen.tsx:338-346) in 1.4 (F8-A6).
- The `.env` hazard on the existing pin (F8-A11).
- Evidence for F13 at HEAD: the spec's F13 evidence is a BASE run, which cannot contain the record block.
  The sketch prototype measured FY25 9/9 unmoved with the flag ON (and OFF), so the claim holds; GREEN
  must still run it.

## Design risks

- DR-1 (if F8-A1 is not taken): a raised `_get_specs` / `_get_price` with the other data race still
  running at the cap ships "Still gathering prices" and is invisible in the logs (prototype P_R1 / P_R1b:
  `error_lines []`); retry amplification (limit 14) then hits a deterministic failure.
- DR-2: the mid-gather arm also counts a race that never STARTED (specs / reviews / image wait for the
  unified search, scs:5619-5654, and the supplements drug lookup, 5668-5675) as timed out. That is the
  right verdict for a hard cap, but D5's `cut mid-gather` cannot distinguish "never started" from
  "running"; fine for the canary as long as the doc says so.
- DR-3: limit 1 is real and large. Review probe R6 (all four races raising TimeoutError, Phase 2 not hung,
  cap 5.0 s): the pair gather completed in 0.003 s wall and the REST H6 guard returned INSUFFICIENT_DATA
  (`h6_lines 1`, no `[L2.7]` line). Any all-timeout pair whose post-loop stages finish under the cap never
  reaches this unit; F8b should be scheduled with the canary (7.7).
- DR-4: a leaf raising `asyncio.CancelledError` is stored by the base loop as a VALUE (scs:5798) and the
  product ships as a PARTIAL with `specs {}` (review probe R4: success True, metadata.partial True,
  buffer specs `{}`); the "error" classification of CancelledError (F10) is therefore never consulted on
  that shape. Pre-existing; out of scope; worth one line in the limits.
- DR-5: the eager-record option adds two done-callbacks per product on the hot path under the flag and a
  second env read (or a hoisted single read); the flag-OFF path stays callback-free (prototype pins OFF
  66/66).
- DR-6: KPI and alerting move by design (limits 2/3); `/text/quick` and the canary reason string move too
  (F8-A8, F8-A13).

## Probes run

1. Review probe `tests/test_zz_s78f8_review_probe.py` in the worktree (8 nodes; shapes R1 raised specs
   mid-gather, R1b raised price mid-gather, R2 partial-build failure + parked price, R3 mixed recorded /
   mid-gather, R4 CancelledError leaf, R5 flag flip between record and handler, R6 the H6 path, R7 the
   capture-3 shape; the spec's 2.5 predicate copied verbatim and evaluated on the real post-cap state):
   `8 passed, 10 warnings in 35.09s`; `[netguard] blocked 0 attempt(s) from 0 node(s)`
   `[pyt] tag=f8-review-probe start=2026-10-17 06:22:08 end=2026-10-17 06:22:50 elapsed=42s bound=600s status=OK rc=0`
   Results: R1 / R1b predicate True on identity-only buffers with zero error lines; R2 usable True and
   predicate True; R3 True (A recorded) / False (A unrecorded); R4 PARTIAL success; R5 False both ways
   (D8 holds); R6 H6 INSUFFICIENT_DATA in 0.003 s, no cap; R7 True (Q3 holds). Copy kept as
   `review_agent/test_zz_s78f8_review_probe.py.copy`; the file and its .pyc deleted; tree clean.
2. GREEN prototype, detached worktree `review_agent/f8proto` at e0f3e475, sketch verbatim
   (`apply_spec_sketch.py`, scs sha256 fba95056...):
   `12 passed, 10 warnings in 39.55s`
   `[pyt] tag=f8-review-proto start=2026-10-17 06:33:28 end=2026-10-17 06:34:19 elapsed=50s bound=600s status=OK rc=0`
   P_R1 TIMEOUT, P_R1b TIMEOUT, P_R2 TIMEOUT (usable True), P_F2 TIMEOUT (2,4,4,0), P_F1b TIMEOUT
   (2,0,0,2), P_F3a INSUFFICIENT_DATA (record specs ok), P_F3b TIMEOUT (2,4,4,0), P_F6 INSUFFICIENT_DATA
   (record specs error), P_F12 TIMEOUT (2,2,2,0), OFF INSUFFICIENT_DATA with outcomes {}, FY25 9/9 unmoved
   ON and OFF; every CAP line matched the 2.6 regex at WARNING.
3. Existing handler pins on the sketch prototype, flag unset (7 files):
   `57 passed, 2 deselected, 12 warnings in 49.83s`
   `[pyt] tag=f8-proto-pins-off start=2026-10-17 06:34:43 end=2026-10-17 06:35:37 elapsed=53s bound=600s status=OK rc=0`
4. The same set with `ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT=true` exported:
   `1 failed, 56 passed, 2 deselected, 12 warnings in 73.51s` (FAILED test_both_hang_falls_through_to_insufficient_data only)
   `[pyt] tag=f8-proto-pins-on start=2026-10-17 06:35:52 end=2026-10-17 06:37:15 elapsed=83s bound=600s status=FAIL rc=1`
5. Sketch + 7.2 hardening (`--harden-72`, scs sha256 f60e0040...), recorded shapes:
   `8 passed, 4 deselected, 10 warnings in 22.89s` (P_R2 -> INSUFFICIENT_DATA; the rest unchanged)
   `[pyt] tag=f8-proto-harden72 start=2026-10-17 06:37:56 end=2026-10-17 06:38:23 elapsed=27s bound=600s status=OK rc=0`
6. Hardened + eager data-race record (`apply_eager_record.py`, scs sha256 c043eed4...):
   `12 passed, 10 warnings in 31.27s` (P_R1 / P_R1b -> INSUFFICIENT_DATA; the rest unchanged; FY25 9/9 ON and OFF)
   `[pyt] tag=f8-proto-eager start=2026-10-17 06:39:25 end=2026-10-17 06:39:59 elapsed=34s bound=600s status=OK rc=0`
7. Existing pins (9 files incl. test_lever1_orphan_cancel_i56.py, test_latency_stack_i56.py) on the
   eager variant, flag unset:
   `66 passed, 2 deselected, 12 warnings in 77.76s`
   `[pyt] tag=f8-proto-eager-pins-off start=2026-10-17 06:40:17 end=2026-10-17 06:41:43 elapsed=86s bound=600s status=OK rc=0`
8. Comm-set regeneration (grep only, no pytest): modref 182 == the spec's 182; symbol-only consumer
   files 12 missing (F8-A7). Lists: `review_agent/modref.txt`, `symref.txt`, `spec_comm.txt`.

Prototype worktree removed with `git worktree remove --force` (no node_modules junction in a fresh
checkout); `git worktree list` has no f8proto entry.
