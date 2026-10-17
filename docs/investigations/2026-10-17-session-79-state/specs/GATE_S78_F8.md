# S78-F8 at the Fable gate (RED done, GREEN not started) -- for the owner's yes

Unit S78-F8 = plan fix 8 (`COMPARE_QUALITY_PLAN_S78.md`): an all-timeout hard cap is reported as TIMEOUT (503, app copy
home.errors.timeout) instead of INSUFFICIENT_DATA (400, "choose different products").
Worktree `sc-s78-alltimeout`, branch `feature/s78-all-timeout-cap-as-timeout`, base main `e0f3e475`.
Flag `ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT`, default OFF, read per call (`_flag_on`), no knob. Ships dark; the flip is the owner's.

## What the whey capture actually showed (re-read of the 2026-10-14 log)

Product A: all four Phase-1 races timed out at 03:59:33. Product B: specs, price and image timed out at 03:59:38 but its
REVIEWS race completed. The cap fired at 03:59:46 while the tiers were still running; the handler saw two products with
specs None and price None and returned INSUFFICIENT_DATA. So the rule is about the DATA races (specs, price), the two
races INSUFFICIENT_DATA is about; a completed reviews or image race must not keep the 400.

## The design (spec + adversarial review + rulings, all measured at e0f3e475)

1. Under the flag, each product records the outcome of its data races: "timeout" / "error" / "ok", from done-callbacks
   on the price and specs tasks (a task cancelled by the hard cap records nothing) and, once the Phase-1 loop ran, for
   all four races. Flag OFF: no callback, no record, one env read per product and nothing else.
2. In the REST hard-cap handler, inside today's INSUFFICIENT_DATA branch only: when every registered product has no
   usable specs or price AND every recorded data race is a timeout AND no data race completed or raised, return the
   EXISTING TIMEOUT body (same five keys, same copy) and log ONE WARNING
   `[L2.7] hard-cap: every Phase-1 data race timed out or was cut (products=N, data races recorded=N, timed out=N) for query=... -- reporting TIMEOUT, not INSUFFICIENT_DATA`.
   Anything else (a race that returned nothing, a race that raised, a parked price, no evidence) keeps today's body.
3. Nothing else moves: the stream path, the partial path, the refund (fires for every failure code), metering.

## What changes for the user and for the numbers (flag ON)

- The whey shape: 503 + "Still gathering prices -- give it another tap in a moment." instead of 400 + "Thin data on that pair".
- Camera: with the failure envelope ON (prod) the client already shows the timeout state for both codes: no UI change.
- search_logs error_message moves from the INSUFFICIENT_DATA sentence to the TIMEOUT sentence (the admin error-stats
  bucket moves by the same rows); the Railway 5xx count rises by the same rows; no Sentry event (503 is excluded).
- /text/quick (admin-only) stays 400 but its detail text moves.

## The finding the owner should weigh: fix 8 alone may rarely fire once fix 3 is on

An all-timeout pair reaches this handler only when the cap fires while a product is still in Phase 2 / the tier fills.
When both products finish under the cap, the post-gather H6 guard returns INSUFFICIENT_DATA in milliseconds and this
unit never runs (measured by the reviewer: 3 ms, no cap line). S78-TG (fix 3, PR #355) skips the tier fills near the
deadline, so with it ON more all-timeout pairs finish under the cap and land on H6: the same pair would still say
"choose different products". Closing that needs the same record and predicate at the two H6 sites (REST + stream)
= unit S78-F8b.

Options:
- A (recommended): this unit as specified (the cap handler), then S78-F8b right after on the SAME flag, before any flip.
  Cost: a second small unit (~half a day under the harness).
- B: fold both H6 sites into this unit now: a RED extension (~6 rows), then GREEN. Cost: one more RED pass (~30 min).

Either way the flag stays OFF until the owner's yes after the canary.

## Owner calls recorded for the flip (not for the build)

- The copy: "give it another tap" for a pair whose sources are slow every time (retry amplification); the old copy
  steered to a different pair. Canary reading: the repeat-query rate after the WARNING line.
- The canary: a unit test plus log review of the next natural occurrence (grep the WARNING line); count the H6
  `INSUFFICIENT_DATA: both products' Phase 1 fetches returned None` lines in the same window to size F8b. Rollback = unset.

## Gates at RED (orchestrator-verified)

- RED file `tests/test_s78_all_timeout_cap_as_timeout.py`: 84 nodes, 58 RED / 26 PIN at base e0f3e475; the
  orchestrator's own run: `58 failed, 26 passed in 43.06s` ([pyt] gate-f8-red), the identical failed set in both flag
  states, every failure an AssertionError naming the absent behaviour.
- Satisfiability prototype (scratch worktree, removed): 84/84 flag OFF, 85/85 flag ON incl. the FY25 identity node;
  106 added lines, 0 removed; ruff + py_compile clean; 31 of 31 mutants killed (one equivalent survivor recorded).
- Comm set 230 files (10 chunks) with the 4 pre-existing base failures recorded; CI-order set 733 -> 759 passed + the
  58 reds, no leakage; the five existing hard-cap pin files 53/53; netguard ratchet OK (sentinel attempts only);
  secret / personal-data scan 0; worktree clean apart from the new file.

## Merge order

#354 (docs) first, then #355 (TG) and #356 (SM), then this unit rebased (its CLAUDE.md row inserts at the same anchor as theirs).

## The question

Approve GREEN for option A (recommended), or ask for option B first?
