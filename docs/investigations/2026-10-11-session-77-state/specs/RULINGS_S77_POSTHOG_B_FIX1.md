# Orchestrator rulings: PostHog unit B, fix round 1 (written 2026-10-12, for session 78)

GREEN (wf_acc1290f-59a) is committed as a WIP commit on `feature/s77-posthog-server` (worktree `sc-s77-posthog`), marked DO NOT MERGE.

- **GREEN gates:** RED 139/139; comm gate over 149 files with branch-only-NEW empty in both directions; fill-in round-trip byte-identical; ruff, py_compile and the lock reproduce.
- **Adversary verdict: NOT READY** — 1 MAJOR, 10 MINOR, 5 surviving mutants. The full reports are in `runs/posthog_b_green_wf_acc1290f.md`.

These rulings bind the fix round. Run it test-first: every fix gets a pin that is red against the WIP commit, then the code. Then a final adversary on the exact bytes, then commit, PR and CI.

## Fixes
- **PF1 (F1, MAJOR) — keep the analytics preference across every writer of `users.preferences`.**
  - `save_preferences` (auth_routes.py ~1266-1292) carries `analytics_enabled` over from the stored preferences. `UserPreferencesRequest` may also accept it as an optional field; carrying it over is required either way.
  - The cohort seed path (~1606-1609) preserves it too.
  - `should_seed` ignores toggle-only keys (`analytics_enabled`, and the existing toggles such as `notifications_enabled`). Measure which toggle keys exist before deciding; never change seeding for a real preference answer.
  - Pins:
    - a stored False survives a full Edit-Preferences save, with and without the key in the body;
    - a stored False survives a cohort seed;
    - `should_seed({"analytics_enabled": False})` is True only when nothing but toggles is present (keep base behaviour for real answers).
  - Re-run the auth preference suites, including `test_auth_preference_toggles_w314.py` and the cohort-seed tests.
- **PF2 (F2) — per-user generation counter.**
  - `invalidate_analytics_preference` bumps the counter.
  - A preference read stores its result only if the generation it started with is unchanged.
  - Pin: invalidation during an in-flight read leaves no stale True.
- **PF3 (F3) — re-check before sending.** Re-check `_deleted_users` (and the flag) in the send step, immediately before `client.capture`. Pin the failure-event path too: this kills surviving mutant M03.
- **PF4 (F4) — no per-deletion client construction on the loop.** B2 must not construct an `httpx.AsyncClient` on the loop per deletion. Build one lazily in `to_thread` and reuse it, or use the repo's existing shared async client if one exists (measure it). Pin it off-loop.
- **PF5 (F5) — strip queries from links without a scheme.** Query-shaped text after a bare host or path in `query` is stripped (anything from `?` to the next whitespace) before the 200-character cap. Pin: `www.noon.com/p/x?a=1&token=S vs y` has no `token`.
- **PF6 (F6, and GREEN deviation 1) — a dedicated `posthog` executor.**
  - The executor is a `ThreadPoolExecutor`, `max_workers=2`, thread_name_prefix `posthog`, built lazily. It is used for client construction, capture, the preference read and the shutdown flush. It is never the default `qaren-worker` adapter pool.
  - The preference read has its own timeout of 3 s (`asyncio.wait_for`).
  - A failed or timed-out read is cached as "opted out" for 60 s (negative TTL), so a Supabase brownout costs one read per user per minute.
  - Pins: the executor name, the timeout, the negative-cache TTL.
- **PF7 (F7) — capture without delaying the follow-ups.**
  - The capture in `track_after_persist` must not delay the existing follow-ups: home:savings bust, user_events, critique write, Referral Loop 2.
  - Spawn it with the repo's `fire_and_forget` (registered with the W1-6 drain set) after the falsy-id check, or run it after the follow-ups. Measure which keeps the RED pins green. Prefer `fire_and_forget`.
  - Pin: a slow capture does not delay the follow-ups.
- **PF8 (F8) — fill URL-compare events from the URL path's shape.**
  - Derive the products, winner and category from the URL-compare response shape: top-level `products`, `winner_index`, `category_used`.
  - Pin with a recorded `compare_from_urls` shape.
- **PF9 (F9) — keep the shutdown window inside 30 s.** The PostHog shutdown arithmetic must account for posthog's own atexit flush (1.0 s). Either:
  - disable posthog's atexit registration, if 7.60.1 allows it (measure the code: `client.py:1068`, `_ATEXIT_FLUSH_TIMEOUT_SECONDS` at `:139`), or
  - lower `POSTHOG_SHUTDOWN_FLUSH_TIMEOUT` to 0.5 so that 20 + 8 + 0.5 + 0.25 + 1.0 <= 30.

  Update the shutdown-window pin to the full sum (never weaken it). The shutdown flush runs on the dedicated executor (PF6).
- **PF10 (F10) — kill the 5 surviving mutants with pins.**
  - M03 is covered by PF3.
  - M10: `price_found` respects `unavailable`.
  - M15: toggles route invalidation.
  - M16: the response key is echoed only when sent.
  - M23: `client.capture` runs off the loop.
- **PF11 (F11) — docs.**
  - The B2 flag row states "unit L live first" as a precondition, because B2 sends user ids to eu.posthog.com.
  - The fixture `_comment` says eight flags.
  - The CLAUDE.md row's "even one racing the erase" sentence is made true by PF3, or reworded.

## GREEN deviations — adjudicated
1. **Executor.** Replaced by PF6.
2. **PG11 p99 (5.7 ms on Windows).** ACCEPTED for this unit.
   - Cause: posthog's `system_context()` runs a WMI query per capture on Windows only. The Linux stand-in measured p99 0.366 ms.
   - The capture now runs on the dedicated executor, so the loop cost is GIL contention only.
   - The canary watches `/health loop_lag_max_60s_ms` after activation.
3. **bulk_delete path without a trailing slash, JSON body.** ACCEPTED (docs). Verify live at the first activation with one deleted test account.
4. **PG7 pin in `test_conftest_env_safety.py`.** ACCEPTED.
5. **"Eight" wording and the fixture comment key.** ACCEPTED (PF11 finishes it).
6. **Network for the uv compile and context7.** ACCEPTED.
7. **The extra constructor knobs** (max_queue_size 1000, flush_at 50, flush_interval 5.0, timeout 5, max_retries 2). ACCEPTED, and pin them.

## Gates for fix round 1
- The RED set plus the new PF pins pass.
- The comm set over the same 149 files (unioned with every new test file and the cohort-seed / preference test files) shows branch-only-NEW empty against base 18121839.
- The fill-in round-trip stays byte-identical and `render --check` returns rc 0.
- ruff and py_compile are clean, and the lock is unchanged.
- The final adversary on the exact bytes returns READY.
