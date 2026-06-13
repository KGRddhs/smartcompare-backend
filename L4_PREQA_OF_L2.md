# L4 read-only pre-QA of L2 (`feature/s3-l2-youtube`) — 2026-06-13

Static review of the L2 diff vs main (no checkout, no edit). Reviewed: youtube_service.py,
api_budget_service.py delta, review_service reviews-race wiring, extraction_service verdict
citation, response_builder surfacing, structured_comparison_service SSE parity, + the 5 test files.

## Verdict: STRONG — merge-ready. No blockers. No L4 collision. One medium plan-conformance note + 2 nits.

## L4-specific: api_budget_service.py interaction — NO CONFLICT ✓
- L2 hunks: PROVIDER_CONFIGS lines 46-65 (adds `"youtube"` key) + new youtube block lines 456-581 (file end).
- L4 hunks: lines 71-107 (`_serper_key_prefix` + `_budget_key`) + 119-161 (`_burn_sentinel_key`).
- Regions are disjoint + non-adjacent. L4 merges before L2 (order L5→L4→L2→…); L2 on top of L4-merged-main auto-merges cleanly. `try_consume_youtube_credit` is a faithful clone of my-neighbor `try_consume_serper_image_credit` (atomic incrby, TTL-on-first-write, rollback-over-limit, fail-open). Zero overlap with serper key-scoping.

## Invariants verified
- **L2.3 p95 guard ✓** — `consult_youtube_source` flag-gates FIRST (OFF→instant None, zero quota), then `asyncio.wait_for(timeout=4.0)`. Sits INSIDE the outer reviews-race `wait_for(_PHASE1_TIMEOUTS["reviews"]=10.0)` (structured_comparison_service.py:2276-2283). Worst case: a slow consult is cancelled by the 10s outer cap → signal dropped, p95 NOT extended. Verified the outer cap wraps `_get_reviews → get_reviews`.
- **Cancel-safety ordering ✓** — `extraction_persisted=True` + `set_cached` (review_service.py:258-263) happen BEFORE the youtube consult (line 290). A mid-consult cancel loses only the in-memory decoration, not persisted reviews. L2 has a test pinning `set_cached` index < `youtube_consult` index (the F3/G2 lesson).
- **L2.1 graceful-None ✓** — no-key→None, cache-first (14d), never raises (all paths → None), record_usage on HTTP-200 only, no wasted videos.list when search.list empty.
- **L2.2 quota metering ✓** — daily UNIT counter `budget:youtube_units:{utc-date}`, 9000/10000 buffer, check-and-increment guards the 100-unit search.list, fail-open on Redis down. Mirrors serper_images.
- **L2.4 cited, no-scary-copy, no-"estimated" ✓** — verdict block `_build_youtube_signal_block` is LABELED + CITED ("top video by <channel>", humanized views) + explicitly "NOT the verdict". Forbidden-vocab scan across all L2 source: clean (only comments STATE the rule). `_humanize_count` formats counts.
- **L2.5 flag default OFF + 14d cache ✓** — `youtube_source_enabled()` default OFF, fresh-read, truthy set. Verdict-block injection + response-builder + extraction all DOUBLE-guard (gate on FLAG not signal-presence) so the 14d cache can't leak a signal past a flag rollback. `_scrub_youtube_signal_if_off` strips cache-carried signal from the raw json.dumps payload (composed with the I2.5 scrub). Tests pin flag-off-by-default + parsing.

## Medium — plan-conformance note (L2 to disposition, not a blocker)
Plan §L2.2 says "circuit-breaker on the Firecrawl pattern." `fetch_youtube_review_signal` never calls `record_failure("youtube")` / `record_success("youtube")` and never checks `is_circuit_closed("youtube")` — so the breaker is wired in PROVIDER_CONFIGS but NOT exercised. A YouTube outage retries every cache-miss (bounded by the 4s wait_for + daily-unit cap, and flag-OFF by default, so damage is contained — but not breaker-protected). The PROVIDER_CONFIGS comment half-acknowledges this ("exists so has_budget()/the circuit breaker/record_usage's burn-alert plumbing treat youtube as a known provider"). **Disposition: either wire record_failure/is_circuit_closed (small), OR have L2 explicitly state the daily-cap + wait_for IS the intended guard and adjust the plan-conformance note. Flag for the gate ultracode review.**

## Nits (non-blocking)
1. **Admin summary key mismatch** — youtube is now in PROVIDER_CONFIGS, so `get_usage_summary` will surface `_budget_key("youtube")` = `budget:youtube:{YYYY-MM}` (near-zero, only videos.list `record_usage` hits it), NOT the authoritative daily `budget:youtube_units:{date}`. Display-only inconsistency; L2's comment acknowledges the daily counter is authoritative. Consider adding youtube_units to the summary like serper_images, or note it.
2. **`record_usage("youtube")` writes a monthly key that nothing reads as budget** — harmless (it's the videos.list meter for the summary), but it means two youtube keys exist (`budget:youtube:{month}` via record_usage + `budget:youtube_units:{date}` via try_consume). Intentional per design; just noting the dual-key surface.

## Tests (static inspection — execution is the gate's job)
5 files, +1243 lines. Assertions pin: p95 timeout-drop, flag-off-no-fetch, graceful-None, persist-before-consult ordering, fail-open, flag parsing, cited-evidence shape, no-"estimated". Coverage of the load-bearing contracts is thorough.

**Bottom line for my cross-QA slot:** when L2 merges, I expect a clean auto-merge in api_budget_service.py and green tests. My one ask is the circuit-breaker disposition (medium). Everything else is nits.
