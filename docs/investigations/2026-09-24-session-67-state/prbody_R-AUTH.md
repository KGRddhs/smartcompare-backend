## Retro-fix R-AUTH (W1-4 server half (#139) + W1-9 429 lockout (#152), merged in session 65 without review)

Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (Fable-gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 agents with Fable gating, on the pinned CI stack.

**Verdict:** the session-66 wip `f8481f62` turned out to be a COMPLETE green (the session-67 resume audited every hunk, KEEP, no edit; 123 unit nodes, 26 mutants killed incl. the reviewer's M7/M9/MB) -> adversary round 0 DEFECTIVE (major, gated on `ENABLE_LOGOUT_UPSTREAM_REVOCATION`: the expired-bearer logout branch let an UNAUTHENTICATED caller trigger an upstream gotrue refresh POST + a Redis SETEX per request with a forged expired JWT and any refresh_token string, no rate limit; minor: two TTL-less lockout-counter paths) -> fix round (the expired-bearer branch spends a 10/minute budget per limiter key, its own bucket, checked only after the JWT-expiry and refresh-token checks; `track_failed_login` re-arms a legacy TTL-less key with `expire(..., nx=True)`; 14 new pins) -> adversary round 1 **SOUND** (1 minor on PR text, 4 unpinned edges).

**Unflagged (defects with no legitimate reader):** W1-4b refresh failures are classified by TYPE (AuthRetryableError, httpx transport/timeout errors, AuthUnknownError with an upstream 5xx/429 status) - everything else stays 401; W1-4c server-side Supabase clients are built with `auto_refresh_token=False, persist_session=False` on both branches of `get_auth_client` (`SyncClientOptions.replace()` cannot set False - measured), so a refresh never leaves an orphaned Timer that spends the device's refresh token; W1-9b lockout arming is atomic (`SET NX EX` + `INCR`) and `check_account_locked` re-arms a non-positive TTL instead of leaving a permanent lock.

**Inside `ENABLE_LOGOUT_UPSTREAM_REVOCATION` (default OFF, flag OFF byte-identical, pinned):** a valid bearer logs out via `admin.sign_out(access_token, "local")` through `run_db` regardless of the refresh token; an EXPIRED bearer with a refresh_token body refreshes once (`set_session`, rotates) then signs out local, blacklists, and never logs `str(e)` - budgeted at 10/minute per limiter key so forged tokens cannot drive upstream traffic.

**Gates:** 123 + 14 unit nodes green on the pinned venv under a process-wide netguard in both flag states; comm gate over the recorded 47-file set + the retro files: base == head (the two `test_auth_interceptor` baseline ids); every mutation from byte snapshots, sha-verified restores.

**Stated limits / follow-ups:** (1) with `ENABLE_PROXY_AWARE_RATELIMIT` ON the limiter key is the LEFTMOST X-Forwarded-For entry, which the caller writes - measured: 30 forged expired JWTs with rotating XFF gave 30 upstream refresh POSTs; `/auth/refresh` itself is bypassed the same way today, so this is the existing proxy-aware limiter's exposure, not new - follow-up W1-9e (key on the rightmost trusted hop) BEFORE flipping the logout flag on a proxy-aware deployment; (2) unpinned edges recorded by the r1 adversary: the 10/minute window value, the budget-after-qualification ordering, a disabled limiter, the scope string - test-hardening follow-up W1-4f; (3) `error_handler._retry_after_seconds` +1 round-up (reviewer MA) is outside this group.

**CLAUDE.md correction carried by the next docs PR:** the W1-4 flag row's 'INERT until the client sends it' no longer holds - with the flag ON the backend revokes by the access token regardless of the refresh token.

**Adversary round-1 minors, verbatim summary:**
- PR text / activation gate step 3 and 'Honest limits' ('preferably flip ENABLE_PROXY_AWARE_RATELIMIT first, so the expired-bearer budget is p: With ENABLE_PROXY_AWARE_RATELIMIT on, the limiter key is the LEFTMOST X-Forwarded-For entry. The caller writes that entry, so the expired-bearer budget is keyed on a string the attacker chooses. Measured with flag ON and proxy-aware ON: 30 forged expired JWTs, each with a different leftmost XFF, gave 30 x 200, 30 upstream POST /auth/v1/token, 30 blacklist setex. Control run: /auth/refresh with rot

---

## R-AUTH retro fix: W1-4 server (refresh 503 by type, no server auto-refresh, logout revocation by access token, expired-bearer logout, throttled) and W1-9b (lockout never permanent, 429 always carries a window)

### Defects fixed (retro adversary reports, reproduced against the real pinned SDK with a loopback fake gotrue and an in-memory Upstash fake)

1. **W1-4b (blocking).** `/auth/refresh` decided "transient" by substrings of `str(e)`, so most real outage shapes still returned 401: 429 (JSON and HTML), 500 (JSON and HTML), 502, 503, 520, 522, 544, a dropped socket and a real SDK `ReadTimeout('timed out')`. On both client builds a 401 is a forced logout.
2. **W1-4c (major).** The throw-away anon client auto-refreshed. Each login or refresh armed a daemon Timer that later spent the refresh token just handed to the device.
3. **W1-4 server minor / client-half defect 2.** With the flag ON, a logout without a refresh token revoked nothing. Gotrue revokes by the JWT's session, and the refresh-token value never reached it anyway.
4. **W1-4 client-half defect 1.** A logout carrying an expired Bearer got 401 before `logout_user` ran, so nothing was revoked upstream.
5. **W1-9b (major).** Lockout arming was INCR then EXPIRE-if-1. One lost EXPIRE made the counter TTL-less, so five failures over any span locked the account permanently, with a windowless 429.
6. **Fixer round, adversary defect 1 (major, blocks flipping the flag).** The expired-bearer branch in (4) was reachable without authentication, because the JWT signature is never verified, and it had no throttle. Forty forged requests caused 40 upstream POST /token calls on gotrue's per-IP refresh budget (shared by the fleet from the Railway IP), 40 Redis blacklist writes and 40 WARNINGs.
7. **Fixer round, adversary defect 2 (minor).** Two TTL-less counter paths were left: a legacy key stuck without a TTL, and a key that expires between SET NX and INCR.

### Fix

- **`_is_transient_refresh_error` (UNFLAGGED, refresh path only).** Transient means any of:
  - `AuthRetryableError`
  - `httpx.TransportError`
  - `AuthApiError` with status 429 or >= 500
  - `AuthUnknownError` whose `original_error` or `__context__` is an `httpx.HTTPStatusError` with status 429 or >= 500

  A transient error returns the categoriser's transient dict unchanged, and the route maps it to 503 REFRESH_UPSTREAM_UNAVAILABLE. Every other shape stays 401. Login, register, password reset and social login keep today's result.
- **`get_auth_client` (UNFLAGGED).** Both branches build the anon client with `ClientOptions(auto_refresh_token=False, persist_session=False)` through the constructor. `build_supabase_client_options` is untouched.
- **`logout_user` under ENABLE_LOGOUT_UPSTREAM_REVOCATION.**
  - Valid bearer: `admin.sign_out(access, "local")` via `asyncio.to_thread`.
  - Expired bearer plus refresh token: `set_session`, then `sign_out({"scope": "local"})`, offloaded. A rejected pair still returns 200 and logs ONE warning with the exception type only.
  - Flag OFF: unchanged.
- **`/auth/logout` (`_LogoutRoute`, flag-gated).**
  - Under the flag, an expired Bearer (unverified `exp` in the past) with a string `refresh_token` in the body is accepted. It spends a **10/minute-per-limiter-key budget (the /auth/refresh budget) from its own bucket**, checked before any upstream call, Redis write or log line.
  - Over budget, or on a limiter-storage error (fails closed), the route re-raises its original 401. That is byte-identical to the flag-OFF answer, and the client clears locally either way.
  - Anything else re-raises the original exception.
- **`track_failed_login` / `check_account_locked` (UNFLAGGED).**
  - Arming is `SET key 0 NX EX 900`, then `INCR`, then a guarded `EXPIRE key 900 NX`. The EXPIRE arms a legacy TTL-less key and a key recreated by INCR, and never extends a live window. A failure of the EXPIRE never changes the returned count.
  - A locked count whose TTL reads -2, -1 or 0 is re-armed, and the 429 carries `retry_after_seconds` = the window plus `Retry-After`.

### Flag row

No new flag. ENABLE_LOGOUT_UPSTREAM_REVOCATION (existing, default OFF, read per call) now means:
- revoke by the access token for EVERY build (it is no longer inert until the OTA);
- accept an expired Bearer plus a refresh token, throttled to 10/min per limiter key.

The CLAUDE.md row must say this. Its "INERT until the client sends it" and "the OTA is the activation lever" lines are false. While ENABLE_PROXY_AWARE_RATELIMIT is OFF, the limiter key is the shared Railway proxy IP, so the expired-bearer budget is one deployment-wide 10/min bucket. That is the same regime /auth/refresh runs under today. Legitimate expired logouts beyond it get the old 401 and a local clear.

### Activation gate

1. W1-4b, W1-4c and W1-9b go live on deploy.
2. ENABLE_STRICT_OPTIONAL_AUTH precondition (1) is true only once this is deployed. Correct the CLAUDE.md "IS NOW LIVE" line.
3. Before flipping ENABLE_LOGOUT_UPSTREAM_REVOCATION, run the prod canary with a test account:
   - log in, log out, then POST /auth/refresh with the old refresh token: expect 401;
   - repeat with an access token older than 1 h;
   - count the `[auth] logout upstream leg failed` WARNINGs: expect about 0;
   - check logout p95 and event-loop lag;
   - preferably flip ENABLE_PROXY_AWARE_RATELIMIT first, so the expired-bearer budget is per client rather than per deployment.
4. EXPIRE NX needs Redis 7 semantics on Upstash. If Upstash rejects the option, the guarded call is a no-op and new keys stay armed by SET NX EX, so nothing regresses. Confirm on the first prod failed login (ttl > 0 on a legacy key).

### Evidence

- Unit set: 137/137 green with flags unset and with all related flags on.
- Pre-fix bytes turn exactly the 4 new defect nodes red.
- 13 fixer mutants are all killed, including the adversary's 5 survivors: N_transient_msg_changed, N_transient_log_raw_e, N_expired_backstop_raw_e, N_exp_window_plus60 and N_route_any_status.
- The green's earlier 26 mutants plus the reviewer's M7, M8, M9 and MB still hold.
- Comm gate over 53 files: 3 failed, the same as base (2 test_auth_interceptor baseline nodes plus the network-guarded TestUrlDetectSsrf). comm -13 is empty.
- ruff (E9/F63/F7/F82) and py_compile are clean. Full-config ruff shows zero delta.
- A non-loopback socket guard was on for every run.

### Honest limits

- The expired-bearer branch still decides on an UNVERIFIED `exp`, because the server holds no JWT verification key. It is now bounded to the refresh budget per limiter key. A holder of a stolen refresh token can end that session, which the token alone already allowed.
- For TTL -2 the 429 reports the full 900 s window although the lock has lifted. This follows the ruling.
- Redis TTL rounds to the nearest second while slowapi rounds up (+1). Not addressed.
- The logout leg uses `asyncio.to_thread`, not `run_db`, which runs inline when ENABLE_SYNC_DB_OFFLOAD is off.
- The EXPIRE NX adds one Upstash REST call per failed login.

### Follow-ups

- **R-MAIN:** SlowAPIMiddleware should be SlowAPIASGIMiddleware, and the CLAUDE.md:348 precondition added.
- **Logout 422s** non-JSON bodies.
- **R-CLIENT:** the W1-4 client half.
- **Round-up pin:** the +1 round-up in error_handler._retry_after_seconds (reviewer MA) is still unpinned.
- **Lockout rounding:** use PTTL with ceil(ms/1000)+1.
- **Categoriser else-branch** logs the raw `{e}`.
- **social_login** returns raw str(e)[:300] in the [B4-BE-DIAG] response.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
