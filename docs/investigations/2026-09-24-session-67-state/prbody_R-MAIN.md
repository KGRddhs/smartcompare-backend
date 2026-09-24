## Retro-fix R-MAIN (units merged in session 65 without review: W1-1 #142, W1-7/W1-10 #144, W1-9 #152)

Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 with Fable gating, on the pinned CI stack (fastapi 0.141.1 / starlette 1.6.0 / slowapi 0.1.10).

**History worth knowing:** the session-66 close commit of this branch (`b519f9de`) carried a 59-slot loop-lag ring (`maxlen=LOOP_LAG_WINDOW_SLOTS - 1`) left on disk by a killed green - its own `test_window_is_exactly_sixty_ticks` killed it. The session-67 green resume restored the 60-slot ring and pinned it; the round-1 adversary then caught a test-order dependence (a module-level `_before_send` binding that `tests/test_observability.py`'s reload rebinds, deterministic in CI's alphabetical order), fixed in round 2 and proven by running the pair in CI order. Round-2 adversary: SOUND (one cosmetic comment minor, fixed by the orchestrator).

**Gates (round 2):** unit set 201 passed (flag unset) / 199 + 2 by-design flag-OFF-state nodes with `ENABLE_DEFAULT_RATE_LIMITS=true` process-wide; the 9-file unit set + `test_observability.py` + `test_backend_cleanup.py` in CI order: 243 passed; comm gate over the 61-file set + the unit's own files: base and head FAILED sets identical (the 9 pre-existing netguard DNS casualties); 9 mutants killed incl. C5, the ring-max, the 59-slot ring, the middleware revert and the transaction-hook unwire; ruff + py_compile clean.

---

retro(R-MAIN): W1-1b Sentry transaction scrub, W1-1c /admin Basic 500 -> 401, W1-9c async-aware default limiter, W1-10b windowed loop-lag max

W1-1b (security, unflagged): init_sentry now passes before_send_transaction. It runs the same request-region scrub as before_send, through one shared helper (_scrub_request_region), so the two hooks cannot drift. The scrub covers the X-Admin-Key, Authorization and Cookie headers, PII in the URL and in the raw query_string, and the request data and cookies. Before this, every sampled performance transaction for an authenticated admin request sent X-Admin-Key to Sentry verbatim, because the SDK's own header filter does not list it. Trace ids, spans and contexts are left alone, and 503 transactions are NOT dropped.

W1-1c (security, unflagged): the Basic branch of the /admin/* static mount now catches (ValueError, UnicodeError). b64decode(str) raises a plain ValueError on a raw byte >= 0x80, and binascii.Error is a subclass of ValueError, so the old clause missed that case and the mount returned 500. `Basic \xff\xfe` now returns 401 with WWW-Authenticate. The try wraps only the decode, so an error while serving an authenticated request still surfaces as a 500 and is not turned into a 401. This is now pinned: test_serving_error_on_authenticated_basic_request_is_not_a_401 kills the mutant that moves partition, compare_digest and super().__call__ back inside the try.

W1-9c (inside ENABLE_DEFAULT_RATE_LIMITS, default OFF): with the flag on, the app registers slowapi's SlowAPIASGIMiddleware instead of SlowAPIMiddleware. On the pinned slowapi 0.1.10, SlowAPIMiddleware cannot await our async handler, so its 429s shipped a bare {"error": ...} body. With the ASGI variant, the default-limited routes 429 with the envelope, code RATE_LIMITED and Retry-After. With the flag OFF the app is byte-identical: no middleware, pinned by a fresh exec.

Two measured limits on the pinned stack (fastapi 0.141.1 / slowapi 0.1.10):
(a) slowapi's _find_route_handler cannot see through fastapi's _IncludedRouter entries, so router routes are NEVER default-limited, decorated or not. The default reaches only app-level routes. On Railway that means /health, / and /favicon.ico. Locally, where docs are enabled, the four FastAPI docs routes are added.
(b) SlowAPIASGIMiddleware re-sends the held http.response.start before every body message, so a multi-chunk response on a default-limited route breaks with the flag ON.

Limit (b) is accepted as a stated limit because every route the default can reach today answers in one chunk. This is pinned by TestW19cStatedLimitSingleChunk:
- The reachable set is pinned for both configs.
- Each reachable route delivers exactly one start and one body directly under the middleware.
- A scratch-app measurement pin records the double start on the pinned slowapi.

The old test "decorated route is exempt from the default" was vacuous, because POST /api/v1/feedback is unreachable, not exempt. It is rewritten to pin what is true: the route is unresolvable by the default limiter, and its own 30/minute decorator contract still holds with the flag ON.

CLAUDE.md correction: the ENABLE_DEFAULT_RATE_LIMITS row says the flag rate-limits "the 21 previously-undecorated routes". That is false on the pinned stack. Router-included routes are never default-limited; only the app-level /health, / and /favicon.ico are (plus the docs routes where docs are enabled). Flipping the flag therefore does not rate-limit /app/version, /usage/status, /auth/me or the referral routes.

Follow-up W1-9d (not in this PR):
- If router routes must carry the blanket default, it needs a handler lookup that descends into _IncludedRouter. That would rate-limit every client at 10/min per path, so it needs a verified ENABLE_PROXY_AWARE_RATELIMIT first.
- Before any multi-chunk response (StreamingResponse, or FileResponse over 64 KiB) becomes reachable by the default limiter with the flag ON, fix the slowapi start re-send (upgrade or local middleware) or exempt that route.
- The stated-limit pins fail if the reachable set grows.

W1-10b (additive key): /health and loop_lag_snapshot() gain loop_lag_max_60s_ms, the max over a 60-slot ring of per-tick lag samples floored at 0. Before this, loop_lag_max_ms was a high-water mark since process start that never decays, so a new stall after an old one was invisible. The existing keys are unchanged. The recorder recomputes the windowed max once per tick, so /health stays a dict read that never walks the ring. This is pinned by test_windowed_max_is_computed_by_the_recorder_not_by_health, which kills a snapshot that computes max(ring).

W1-7b: tests/test_retro_w1_7_w1_10.py makes the loop-lag pins non-vacuous:
- A synthetic tick is read back through GET /health without the heartbeat overwriting it.
- The heartbeat records now - previous and advances previous.
- The shutdown handler is registered.
tests/test_health_loop_lag.py is intentionally untouched; its vacuous nodes are backstopped by these mutation-verified pins.

Fix round 2 (review of round 1):
- BLOCKING test-order defect fixed. tests/test_retro_w1_1.py no longer holds a module-level reference to any sentry_service attribute; everything resolves through the module object at call time. tests/test_observability.py, which sorts first in CI, importlib.reload()s sentry_service, and that had broken an identity assert. Proven in one process in CI order: test_observability.py then test_retro_w1_1.py went from 1 failed to 0 failed. The full unit set plus test_observability.py and test_backend_cleanup.py passes 243/243 in alphabetical order.
- Added pins for C5, the recorder-computed windowed max and the single-chunk stated limit, and rewrote the vacuous router-route test.
- Mutation matrix: 9 of 9 killed, including the two round-1 survivors (C5 and the snapshot that computes max(ring)).
- Comm gate: 61 files plus the unit's 3 retro files show the same failure set as base 1c6f6796 (9 netguard DNS casualties, all present at base).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
