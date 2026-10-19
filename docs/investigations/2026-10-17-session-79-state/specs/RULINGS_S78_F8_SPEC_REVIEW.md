# Rulings on the S78-F8 spec review (Fable, binding, 2026-10-17 ~06:55 AST)

**Spec:** `sc-s78-alltimeout/.qa-s78/S78_F8_UNIT_SPEC.md`, sha256 `bfd14cc0...6c58` (the spec writer's bytes; NOT edited by the review).
**Review:** `scratchpad/f8/S78_F8_SPEC_REVIEW.md` (verdict APPROVE_WITH_CHANGES, 6 refuted claims RC-1..RC-6, corrections F8-A1..A13, design risks DR-1..DR-6; the review's prototypes measured every shape named below).
**Precedence:** these rulings amend the spec and win where they conflict; the brief's D1-D10 stand as amended here; `RULINGS_S78_TG_SM.md` (the house rules) still binds.

## R1. Scope (D1) stands: the REST hard-cap handler only. F8b is a decision for the owner at the gate.

The two H6 guards (REST scs:4141-4155, stream scs:4827-4844) stay out of this unit. DR-3 / stated limit 1 is CONFIRMED by the review's probe R6 (an all-timeout gather whose post-loop stages finish under the cap returns INSUFFICIENT_DATA from H6 in 3 ms with no `[L2.7]` line) and it interacts with S78-TG: once `ENABLE_TIER_FILL_RESIDUAL_GUARD` is on, more all-timeout compares finish under the cap and land on H6, not here. The orchestrator presents this at the RED gate with two options for the owner (A: this unit as specified, F8b as the next unit on the same flag; B: fold both H6 sites into this unit before GREEN). RED is written for A. Nothing in the RED file may assume B.

## R2. F8-A1: option (b), the eager record of the two DATA races (D7 holds in BOTH arms).

RC-1 is accepted: in the mid-gather arm a data race that RAISED leaves no key (both base done-callbacks swallow the exception, scs:5582 / scs:5703) and the spec predicate reports TIMEOUT for it, which contradicts D7 and DR-1 (a deterministic leaf failure would ship "give it another tap" with no line naming the error).

Design (the review's measured prototype `f8-proto-eager`, 12/12 shapes, pins OFF 66/66, FY25 9/9 ON and OFF):

- In `_fetch_product_data`, ONE hoisted read per product, placed immediately before the price task is created (scs:~5565): `_record_races = partial_slot is not None and _flag_on("ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT")`. Flag OFF (or `partial_slot` None): `_record_races` is False, no callback is attached, nothing is written, the post-loop block is skipped on the same boolean (no second env read).
- Under `_record_races`, a done-callback is attached to `_price_task` (after its creation, next to `_stash_price_cb`) and to `_specs_task` (after its creation, next to `_stash_specs_cb`). The callback is one bound method `self._record_phase1_race(slot, key, task)` (or a `functools.partial` over it): `if task.cancelled(): return` (a cancel by the hard cap records NOTHING: the race was cut, not completed); `exc = task.exception()`; outcome = "timeout" if `isinstance(exc, asyncio.TimeoutError)` else "error" if `exc is not None` else "ok"; it writes `outcomes.setdefault(slot, {})[key] = outcome` through the same getattr-safe dict access as the post-loop block. The callback never raises (wrap the body in `try/except Exception: pass` the way the base callbacks do).
- The post-loop block (spec 2.4) stays, guarded by the same `_record_races` boolean, and writes ALL four keys from `phase1_results` with `_phase1_race_outcome` (it overwrites the eager entries with the same classification; for a race that ran to the loop the two writers agree by construction).
- Reviews and image_url are never recorded eagerly (they never count).

The predicate (spec 2.5) becomes, per populated slot `pd` (None slots skipped; at least one populated slot required):

```
if pd.get("specs") is not None or pd.get("price") is not None:   # R3 (7.2): usable data present, any arm
    return False
rec = outcomes.get(slot)
if not isinstance(rec, dict):
    # no record at all (the flag was OFF when this product's tasks were created, i.e. a mid-request
    # flip): a landed key is a completed race -> fail closed to base
    if "specs" in pd or "price" in pd:
        return False
    continue                                   # identities only, nothing recorded: cut by the cap
for key in ("specs", "price"):
    if key in rec and rec[key] != "timeout":   # a completed ("ok") or raised ("error") data race
        return False
# a data race ABSENT from rec was cancelled by the cap or never started (the unified search / drug
# lookup precede it) or did not run (include_specs False): it counts as timed out (DR-2, a stated limit)
return populated > 0   (after the loop)
```

Consequences for the spec tables:
- F18 row (10) (`both {"specs": "timeout"}`, no price key) becomes **True** (the price race was cut by the cap). Add rows: (15) `[dict(IDENT, price={"amount": 9.5, ...}), IDENT]` with an all-timeout record for both -> False (R3); (16) `[IDENT, IDENT]`, `{0: {"specs": "error"}}` (an eager record of a raised specs race, price cut) -> False; (17) `{0: {"specs": "ok"}}` -> False; (18) `{0: {"price": "timeout"}, 1: {"price": "timeout"}}` with identity-only dicts -> True; (19) `{0: {"price": "error"}}` -> False.
- New real-entry rows: F19 (specs raises RuntimeError, price hangs, cap 1.0 s, flag on): INSUFFICIENT_DATA with `INSUFF_KEYS`, no `CAP_RE` line, the record `rec[0]["specs"] == "error"` and `"price" not in rec[0]` (RED by the record half: at base there is no record; the body half is a PIN); F19b: price raises, specs hangs -> INSUFFICIENT_DATA, `rec[0]["price"] == "error"`; F19c: specs completes with a dict, price hangs -> the PARTIAL path (usable) in both states (PIN) and `rec[0]["specs"] == "ok"` under the flag (RED half).
- F1b (real entry, specs + price hang, reviews / image return): unchanged expectation (TIMEOUT, `rec == {}`: a cancelled task records nothing).
- F11 (the post-loop block): unchanged (all four keys after the loop; `partial_slot` None -> `{}`); add the assertion that with the flag on the record is ALREADY present for specs/price before the loop ends is NOT required (callback order is not pinned).
- Mutants: M28 "the eager callbacks are not attached" (killed by F19 / F19b record halves); M29 "a cancelled task is recorded as error or ok" (killed by F1b: the record must stay `{}` and the verdict TIMEOUT); M30 "the eager callback reads the flag at callback time instead of the hoisted boolean" is EQUIVALENT (accepted survivor; record it).
- D8 / stated limit 5 (the mid-request flip) is unchanged: ON at creation / OFF at the handler -> the flag-first predicate returns False; OFF at creation / ON at the handler -> no record, the landed keys fail closed.

## R3. F8-A2: spec 7.2 is IN, applied to every populated slot FIRST (see the predicate above).

Probe R2 (a parked 9.5 BHD price, `_build_partial_response` raising) must stay INSUFFICIENT_DATA under the flag. Add F18 row (15), the real-entry row F20 (PIN: the parked price stub + a `_build_partial_response` monkeypatched to raise -> `code == "INSUFFICIENT_DATA"` in both flag states; no `CAP_RE` line) and mutant M27 "the 7.2 check removed" (killed by F18 (15) and F20's flag-on half). Strike stated limit 8.

## R4. F8-A3: every row that asserts on `_phase1_race_outcomes` content is split.

F3(a), F6, F7 (and the new F19 family): a PIN half (the verdict, the key set, the error text, the base log lines) and a RED half (the record read with `rec = getattr(svc, "_phase1_race_outcomes", None)`; `assert isinstance(rec, dict)` FIRST so base fails on an AssertionError, never a KeyError / TypeError). Gate 5.1's RED count is updated accordingly.

## R5. F8-A4: M22 rewritten.

M22a "the record block placed before the GATHER" (a NameError on `phase1_results`, killed by every real-entry row); M22b "the record block mutates `result` or `phase1_results`" (killed by F2's 8 base `[L2.6]` lines and F11). "Placed before the loop" is an equivalent mutant: struck.

## R6. F8-A5: the D5 line is pinned at WARNING exactly.

`_cap_lines(caplog)` filters `levelno == logging.WARNING`. Mutant M26 "the D5 line at ERROR" is killed by F1. Reason (measured by the review): at ERROR a `query=%r` line becomes a Sentry event (`LoggingIntegration(level=ERROR)`, sentry_service.py:651) and no existing pin catches a new in-except ERROR line (test_sentry_channels_u8d_unit.py covers four named templates only). The spec's section 1.4 records F8-A9: the 400 -> 503 move adds NO Sentry event (`_captured_5xx = range(500, 600) - {503}`, sentry_service.py:637/641/645).

## R7. The D5 line format (spec 7.1, amended for R2).

With the eager record, "cut mid-gather" is not well-defined per slot. The line is:

`[L2.7] hard-cap: every Phase-1 data race timed out or was cut (products=%d, data races recorded=%d, timed out=%d) for query=%r -- reporting TIMEOUT, not INSUFFICIENT_DATA`

where `products` = populated buffer slots, `recorded` = the number of `specs` / `price` entries across all records, `timed out` = those entries equal to "timeout". One helper computes the three counts (pure; called only after the predicate returned True). Expected groups: F1 (2, 0, 0); F1b (2, 0, 0); F2 (2, 4, 4); F3b (2, 4, 4); F12(a) include_specs False (2, 2, 2); F12(b) (2, 2, 2). `CAP_RE` = `^\[L2\.7\] hard-cap: every Phase-1 data race timed out or was cut \(products=(\d+), data races recorded=(\d+), timed out=(\d+)\) for query=.+ -- reporting TIMEOUT, not INSUFFICIENT_DATA$` (F8-A12: `query=.+`, never `query='.*'`).

## R8. F8-A7: the comm set gains chunk 09 (the 12 symbol-only consumer files).

The derivation rule is widened: every `tests/test_*.py` that contains the module string `structured_comparison_service` OR any of the symbols `StructuredComparisonService`, `get_comparison_service`, `compare_from_text` (which also matches `compare_from_text_streaming`), UNION the source-scanning pins and the CLAUDE.md readers as the spec lists them, MINUS the two precommit-hook files (the TG Q7 exclusion stands). RED regenerates `.qa-s78/comm_set.txt` with that rule (expected 230 files, 10 chunks), records the sha256 of the list, and runs ONLY the new chunk (the files not in the spec's `comm_final.txt`) at base to complete the base failure set; the spec's nine base chunk runs stand as recorded. GREEN re-greps at HEAD.

## R9. Accepted as written, recorded in the spec by RED (no code change)

- F8-A6 / RC-2 / RC-6: stated limit 10 rewritten: camera envelope ON (prod) -> NO client UI change (ResultsScreen.tsx:338-346 already renders 'timeout' for every non-outage code); envelope OFF -> 'generic' becomes 'timeout' (ResultsScreen.tsx:310-320); the camera failure row moves from "INSUFFICIENT_DATA" to "TIMEOUT" at image_routes.py:512 (W4-13 OFF) and :526 (W4-13 ON).
- F8-A8: `/text/quick` (text_routes.py:1413-1452, admin-only): stays HTTP 400; its `detail` text and its failure row (:1442) move to `TIMEOUT_FRIENDLY_MESSAGE`. A stated limit.
- F8-A10 / RC-5: the 1.2 H6 sentence is replaced by the measured facts (the await at scs:4147; `_cancel_profile_task` swallows CancelledError at scs:571-573; probe R6: H6 returns in 3 ms with no cap line).
- F8-A11: stated limit 15 and the CLAUDE.md row say: never set `ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT` in a local `.env` (the unedited existing pin `tests/test_partial_specs_stash_on_price_timeout.py::...::test_both_hang_falls_through_to_insufficient_data` goes red: 1 of 57 measured; CI runs flag OFF). The TG limit-8 precedent.
- F8-A13: no-op consumers recorded: `scripts/verify_after_credits.py` (the FAIL reason string moves http_400 -> http_503; both FAIL) and `scripts/cron_warm_price_cache.py:225-241` (reads products only).
- DR-2: a stated limit: the mid-gather arm counts never-started data races (behind the unified search or the drug lookup) as cut by the cap; the D5 line cannot tell "never started" from "running".
- DR-4: pre-existing and out of scope (a leaf raising CancelledError is stored as a VALUE by the base loop and ships a PARTIAL); recorded in the spec's limits, no row.
- DR-6: the moves by design (KPI bucket, 5xx rate, `/text/quick` detail, the canary reason string) are stated limits and the canary reading.
- 7.3 (F8 split into F8a PIN / F8b RED), 7.4 (F13 = all nine FY25 scenarios with the flag ON), 7.6 (the comm superset and the two precommit exclusions): confirmed.

## R10. F15 (the route end-to-end node) stays, conditionally.

RED keeps F15 (GET + POST, both flag states) and runs the house netguard ratchet (`scripts/netguard_ratchet.py`, the way CI runs it; read its usage first) over the new file: the two `neutralized.supabase.invalid` sentinel attempts per node must NOT count as new egress nodes. If the ratchet flags them, F15 is dropped from the file (the mocked-service route nodes in tests/test_http_400_cap_cut_mapping.py already pin the 503 mapping) and the report says so with the ratchet output.

## R11. F13 evidence belongs to GREEN.

The spec's F13 measurement is a BASE run (it cannot contain the record block). GREEN runs FY25 at HEAD with the flag ON and OFF (bound 600 each) and pastes both summaries; the review's prototype measurement (9/9 both states) is a forecast, not the gate.

## R12. The CLAUDE.md row (GREEN) carries, in this order

effect ON (the predicate in one sentence, the WARNING line verbatim); flag OFF byte-identical (the nodes that pin it: F4a/F4b/F4c, F5-off, F8a, F9, F20-off, the FY25 node, the existing hard-cap pins); stated limits numbered: (1) the H6 guards out of scope = F8b, with the TG interaction; (2) the KPI bucket moves (text, camera, `/text/quick`); (3) 400 -> 503 on `/text/compare`, no Sentry event; (4) the stream untouched; (5) the mid-request flip fails closed; (6) a parked / genuine price on a timeout is a PARTIAL; (7) reviews / image never count; (8) never-started races count as cut; (9) `api_calls` absent on these rows; (10) the camera envelope-ON row; (11) refund / metering unchanged; (12) `include_specs=False`; (13) `ENABLE_EARLY_SPECS_STASH` OFF inert; (14) the retry copy (owner's call); (15) the local `.env` hazard; the canary (a unit test plus log review of the next natural occurrence: grep the D5 line; count the H6 `INSUFFICIENT_DATA: both products' Phase 1 fetches returned None` lines in the same window to size F8b); rollback = unset (per call, immediate); the merge order (#354, #355, #356, then this unit rebased).

## R13. House rules restated for RED

One new test file `tests/test_s78_all_timeout_cap_as_timeout.py`; no edit to any existing test, fixture, conftest or app file; every RED node fails at base on an AssertionError; pure ASCII, LF; no credential shape; the bounded runner only; the worktree's conftest netguard (run bare); the prototype in a detached scratch worktree under the RED agent's scratchpad, the patch saved to `.qa-s78/proto_S78-F8.patch`, the mutation table (M1-M30 as amended: M22a/M22b, M26-M29; M30 recorded as equivalent) applied to the prototype bytes; the probe files deleted; `git status --short` clean except the new test file and the gitignored `.qa-s78/`.
