# LANE L2 — YouTube ingestion (cited review signal)

**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l2`
**Branch:** `feature/s3-l2-youtube`
**Owner:** L2
**Merge order:** L5 → L4 → **L2** → L3 → L1 (I merge 3rd)

## Mission
Add YouTube as a CITED review signal:
- `app/services/youtube_service.py` — Data API v3 (`YOUTUBE_API_KEY`, Railway + main .env; NOT yet in this worktree's .env).
  `search.list` (find product-review videos, 100 units) + `videos.list` (statistics, 1 unit). Returns
  `{review_count_signal, top_video_title, top_channel, video_url}` or `None` on miss/error. Graceful-None.
- Quota metering in `api_budget_service.py`: `youtube_search_calls_today` daily counter, circuit breaker (Firecrawl pattern), fail-open on Redis down. Prefer `videos.list` (1u) over repeat searches.
- Reviews-race participant: inner `wait_for` cap + `None` on miss — **MUST NOT extend p95**. Slow call drops out.
- Cited-evidence surfacing: `review_count_signal` + sentiment cue from `top_video_title` as a cited review source ("N YouTube reviews", attributed to channel). NO scary copy; NEVER the word "estimated"; cite the source.
- `ENABLE_YOUTUBE_SOURCE` flag (default OFF in code; Railway flip only when QA green) + 14d cache.

## Architecture decision (precedent: S2 I2.5 consult_review_sources)
YouTube enrichment lives INSIDE `review_service.get_reviews()` as a `consult_youtube_source()`-style sibling that runs AFTER `extraction_persisted=True` (the F3/G2 ordering — finished reviews cached BEFORE the optional enrichment so a wait_for cancel can't lose them). Wrapped in its OWN inner `wait_for` (≤ the reviews race budget). Result attaches to `reviews["youtube_review_signal"]`. This keeps `structured_comparison_service.py` Phase-1 task structure UNTOUCHED and reuses the exact persist-first pattern. Flag OFF → instant no-op, zero cost.

## Task ledger
- [x] L2.1 `youtube_service.py` + 9 MOCKED unit tests (TDD) — GREEN
- [x] L2.2 Quota metering in api_budget_service — provider config + daily UNIT counter (try_consume_youtube_credit / get_youtube_unit_usage) + 12 dedicated metering tests GREEN (check-and-increment, over-budget rollback, fail-open x2, TTL-first-write-only, env override, record_usage path)
- [x] L2.3 Reviews-race participant — `consult_youtube_source()` (flag-gated, wait_for-capped 4.0s, None-on-miss/error/timeout) + `youtube_source_enabled()` reader + wired into get_reviews AFTER extraction-persist. 10 tests GREEN incl. p95 timeout-drop pin + persist-before-consult order pin + failure-doesnt-break-reviews + flag-off-no-key. 36 existing I2.5 consult tests still green.
- [x] L2.4 Cited-evidence surfacing — verdict prompt (extraction_service: _extract_youtube_signal / _build_youtube_signal_block / _scrub_youtube_signal_if_off + _humanize_count, wired into generate_comparison gated on flag + scrubbed in json.dumps payload) + response reviews section (response_builder._youtube_signal_for_response, flag-gated, inline key). 16 tests GREEN incl. NO-scary-copy + NEVER-"estimated" + cite-channel + humanized-count + rollback-scrub. 92 existing verdict/extraction/response/I2.5 tests green (forbidden-words audit passes).
- [x] L2.5 `ENABLE_YOUTUBE_SOURCE` flag (default OFF) + 14d cache + inert-when-OFF chain + streaming parity (structured_comparison_service streaming reviews SSE event now carries youtube_review_signal via the same flag-gated helper) + privacy allow-list pin. 8 tests GREEN. 65 total L2 tests green.

## Discipline
- TDD: failing test → confirm fail → minimal impl → confirm pass → commit.
- Path-restricted commits; push-per-commit (`git push -u origin feature/s3-l2-youtube`); NO stash.
- LANE_STATE.md updated every commit.
- CREDIT GATE: YouTube has its own free quota (10k units/day). Live smokes OK but ANNOUNCE to team-lead + prefer MOCKED. NEVER Serper full-200.
- ACK every team-lead message.

## Log
- (init) Read §L2 + CLAUDE.md reviews pipeline + api_budget_service circuit-breaker + I2.5 precedent. Confirmed YOUTUBE_API_KEY in main repo .env (absent in worktree .env). Wrote LANE_STATE. Starting L2.1.
- L2.1 GREEN: `youtube_service.fetch_youtube_review_signal()` — search.list (100u) + batched videos.list (1u), statistics-as-strings coercion, top-by-views, budget-gated, 14d cache, None-on-miss/error/no-key/exhausted, never raises. 9 mocked tests pass. Verified real API shape via docs. Added `youtube` provider config + daily-UNIT counter to api_budget_service. Commit 09157ed.
- L2.2 GREEN: 12 quota-metering tests. Commit fdcc5d0.
- L2.3 GREEN: consult_youtube_source (flag-gated, wait_for 4.0s, p95-safe) + wired into get_reviews post-persist. 10 tests. Commit 3ee57b2.
- L2.4 GREEN: cited-evidence — verdict block (extraction_service) + response surface (response_builder), copy rules enforced. 16 tests. Commit 7743aa1.
- L2.5 GREEN: flag default-OFF + 14d cache + inert-when-OFF + streaming SSE parity + privacy allow-list. 8 tests. (committing now)
- ALL 65 L2 tests green. Full free-tier regression sweep running (needs dummy env: worktree has NO .env — OPENAI_API_KEY/SUPABASE_* must be set inline; 2 unrelated files instantiate OpenAI at import).

## Last commit
7743aa1 (L2.4) — L2.5 commit pending regression-sweep confirmation

## Pre-merge gate notes (for the dispatcher)
- Worktree has NO .env. For LIVE smoke: copy YOUTUBE_API_KEY (+ OPENAI/SERPER/SUPABASE/UPSTASH) from main repo .env per rotation playbook — ANNOUNCE first.
- Free-tier sweep needs env vars set inline (conftest loads from .env which is absent here).
- New env flags to register at close-out: `ENABLE_YOUTUBE_SOURCE` (default OFF), `YOUTUBE_DAILY_UNIT_BUDGET` (default 9000), `YOUTUBE_API_KEY` (already on Railway).
- I merge 3rd (L5 → L4 → L2 → L3 → L1). My diff touches shared files (review_service get_reviews, extraction_service generate_comparison, response_builder reviews section, structured_comparison_service streaming event, api_budget_service) — all ADDITIVE + flag-gated OFF, so zero behavior change in prod until the Railway flip.

## Blockers
(none)
