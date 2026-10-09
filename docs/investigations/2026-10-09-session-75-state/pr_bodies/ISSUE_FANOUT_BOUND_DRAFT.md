FANOUT-BOUND: bound the compare's adapter fan-out itself (D3 of FANOUT-STARVE, deferred)

## Context
FANOUT-STARVE (session 75, PR #<FANOUT_PR>) named and bounded the fan-out's starvation points around the fan-out (executor 96, libuv pool 64, Serper connect 8 s, the unified-search bound, the Phase-2 residual guard, the parse stall guard) and left D3 -- a bound on the fan-out ITSELF -- as the follow-up (spec `docs/investigations/2026-10-09-session-75-state/specs/FANOUT_STARVE_SPEC.md` D3; review items M8, m2, m5; rulings FS-R1..R20).

## What is still unbounded
Under `ENABLE_BH_GCC_CATALOG_SOURCES` one compare launches about 30 blocking adapter fetches (15 hosts x 2 products, ledger 2026-10-08 14:24) onto the shared default executor. A second and third concurrent compare multiply that; the 96-thread pool holds three full fan-outs, the fourth queues behind them and its adapters read as TIMEOUT / SLOW-MISS drops (R-W18 lines) although the sources answered. `/health.adapter_executor.queued` (FANOUT-STARVE D1) now shows the queue depth, so the condition is observable before this unit exists.

## Proposed unit (flagged, default OFF, read per call)
- `ENABLE_FANOUT_BOUND` + knob `FANOUT_MAX_CONCURRENT_ADAPTERS` (default 12 per compare): a per-request `asyncio.Semaphore` around the adapter submissions in `price_service` / `source_router` fan-out so one compare can never hold more than N executor slots; the remaining candidates wait in asyncio, not in the pool queue; the race deadline (`_PRICE_RACE_TIMEOUT` 15 s) is unchanged, so a bounded compare may price FEWER candidates in the window (stated limit, measured by the genuine-BH share on canary).
- A process-wide cap `FANOUT_MAX_CONCURRENT_COMPARES` (default 3) is OUT of scope here (it belongs with `#114` / the limiter work).
- Pins: flag OFF byte-identical (the corpus harness is blind to this: pin on the submission order and count); under the flag at most N adapter calls in flight (a fake executor that records concurrency); the SLOW-MISS / TIMEOUT drop lines unchanged in meaning; `/health.adapter_executor.queued` stays 0 under a 3-compare load test with the flag ON (an integration measurement, not a unit node).
- Canary: `run_canary.sh` with `--form both` before and after the flip; watch `[FANOUT] wave=... completed= failed= cancelled=` and the genuine share.

## Also from the FANOUT-STARVE review (same area, same unit or its own)
- M8: the 9 s inner adapter clamp (M13-34) and the 15 s race leave a 6 s window in which a late adapter result is discarded although the race is still open -- measure whether the clamp should follow the residual.
- m2: the `_fetch_product_data` twin paths (sync / stream) duplicate the fan-out setup -- one helper.
- m5: the price-warmer runs the same fan-out off-clock with no executor install -- give it the bounded path too.

Filed from session 75 (2026-10-09). Owner call: the default N and whether the per-compare bound is wanted before the App Store review window.
