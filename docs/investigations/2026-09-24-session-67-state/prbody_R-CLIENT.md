## Retro-fix R-CLIENT (W1-4 client half (#140, merged in session 65b without review))

Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (Fable-gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 agents with Fable gating, on the pinned CI stack.

**CLIENT-ONLY, OTA-GATED:** phones on `97b5f15` are unaffected until the next `eas update --branch preview`. Backend halves (admin.sign_out regardless of refresh token, the expired-Bearer path) are R-AUTH.

**Verdict:** adversary round 0 DEFECTIVE (major: the logout handoff slot accepted ANY epoch-guarded refresh from ANY session - user A's hung refresh could fill user B's logout) -> fix round (the handoff is keyed to the session epoch the logout ends; a refresh fills only the handoff whose epoch equals the epoch it was sent under; the cross-session scenario is pinned) -> adversary round 1 **SOUND** (2 minors recorded below).

**Gates:** 103 tests across the 7 auth suites (w1-4d, w1-4, a3, api.refreshInterceptor, api.refreshMutex, ...) green; `tsc --noEmit` clean; eslint clean on the changed files; the FULL jest suite at commit time on the rebased tree: `Test Suites: 3 skipped, 320 passed, 320 of 323 total | Tests:       15 skipped, 15 todo, 3150 passed, 3180 total | Snapshots:   44 passed, 44 total`; `api.ts` adds exactly ONE read-only export `getInFlightRefresh()`; `/auth/logout` stays on the interceptor's skip-refresh list; the token is never logged.

**Honest limits / follow-ups (adversary r1 minors):** (1) `epochAtRequest` is captured after refreshSession's SecureStore read, so a read that straddles a logout (the read itself hanging > 5 s across logout -> login(B) -> logout) can still hand A's pair to B's logout - follow-up PO-AUTH-W14D-01: capture the epoch before the read; (2) the handoff fill's `session?.access_token` term is unpinned (mutant A16: a 200 with an empty session would hand off `{access: undefined}` and skip the logout POST) - follow-up PO-AUTH-W14D-02: pin it.

**CLAUDE.md correction carried by the next docs PR:** the W1-4 flag row's 'INERT until the client sends it' holds only until R-AUTH makes the backend call `admin.sign_out(access_token, "local")` regardless of the refresh token.

**Adversary round-1 minors, verbatim summary:**
- SmartCompareApp/src/services/authService.ts refreshSession(): `const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);` runs: The ADV-A1 fix keys the handoff on epochAtRequest. That value is captured after the refresh-token read, so a read that straddles logout #1 still lets user A's refresh fill user B's logout. The schedule: A's refresh starts; its SecureStore read of RT1 stays pending past logout #1, which times out at 5 s, POSTs and runs its final clearSession (epoch 3); the read then resolves, so epochAtRequest = 3 
- SmartCompareApp/src/services/authService.ts refreshSession() handoff fill: the `&& response.data.session?.access_token` term of `if (respons: Nothing pins the access_token term of the fill guard. Mutant A16 drops it and survives all 103 tests in the 7 auth suites. Measured through the real functions: an in-flight refresh that returns 200 {success:true, session:{}} during logout makes the mutant hand off {access: undefined}. logout then takes the handoff branch with token=undefined and sends NO logout POST at all (scratch run: logouts=[]

---

fix(mobile/auth): W1-4d — logout presents a fresh session to /auth/logout (retro R-CLIENT, OTA-gated)

DEFECT (retro adversary on #140, reproduced)
Upstream revocation is skipped silently whenever logout carries an expired or stale access token:
- The server's get_current_user 401s the Bearer before logout_user runs.
- /auth/logout is on the 401 interceptor's skip-refresh list.
- logout() neither waited for a refresh already in flight nor refreshed an expired token.
In the in-flight race, the server finishes rotating RT1 to RT2 while the phone's P-A3 epoch guard discards RT2, so RT2 stays live upstream and nothing revokes it. Measured through the real api.ts and authService.ts: the wire Bearer was 'AT1-expired'.

FIX (client only: SmartCompareApp/src/services/{api,authService}.ts)
- api.ts: ONE new read-only export, getInFlightRefresh(): Promise<RefreshResult> | null. It never starts a refresh.
- authService.logout():
  1. Registers a handoff keyed to the session generation it ends (the epoch before its bump), then bumps the P-A3 epoch FIRST. A refresh that lands after the bump neither writes storage nor fires onSessionRefreshed (today's guard). It hands its rotated pair to the waiting logout IN MEMORY, and only when the epoch it was sent under equals that logout's epoch. A refresh from an EARLIER session can therefore never supply the pair, for example one hung across logout, then login(B), then logout (the second adversary's ADV-A1: B's logout sent A's rotated pair and left B unrevoked). Each logout removes its own handoff in finally.
  2. Waits for an in-flight refresh, raced against a 5 s bound (LOGOUT_REFRESH_WAIT_MS). A black-holed refresh cannot hold the tap, and the request itself is never cut short (P-A3).
  3. If the access token is a JWT whose `exp` has passed (exp <= now), starts ONE refresh through getOrStartRefresh() under the same bound. The payload is decoded without verification and with no atob/Buffer. Malformed tokens are expired-UNKNOWN and are sent as today: bad base64url (including length 1 mod 4), non-JSON, and a missing or non-finite exp. The refresh is skipped when the in-flight wait timed out, because it would coalesce onto the hung promise. After an in-flight refresh that FAILED within the bound, an expired token still gets its one refresh (pinned).
  4. Clears the local session, then sends exactly ONE POST with the freshest pair held. No retry loop. clearSession also stays in finally.
  Why the clear comes before the POST: the request interceptor stamps the STORED token over an explicit Authorization header whenever one is stored, so clearing is what lets an in-memory pair reach the wire.
  Every preparation step swallows its own errors, so at worst the stored pair is sent, exactly as before.
- A pre-logout refresh that returns 401 clears state through the existing dead-session path, and then no logout POST is sent (at most one; ruling 4).
- The logout JSDoc no longer claims "Supabase revokes a session by its REFRESH token". That claim is false on the valid-token path (measured by the retro).
- New test-only export __pendingLogoutHandoffCount(). It is read-only and never called from src; it exists to pin that the handoff is released.

TESTS
- New suite __tests__/authService.logoutRefreshFirst.w1-4d.test.ts, 38 tests. It runs the real api.ts and authService.ts with a stub adapter on the real axios instance, behind an autouse zero-network guard. Pins added on top of the red:
  - Fable ruling pins: the black-holed refresh (fake timers); the storage-never-written pin.
  - Second-adversary pins: ADV-A1 (a refresh hung across logout, login(B), logout still posts B's pair); handoff release; success:false never handed off; a handed-off session without refresh_token sends AT2 with the stored RT; an in-flight transient failure plus an expired token costs one more refresh; no timer left pending (two cases); exp == now is expired, with a +1 s control; a length-1-mod-4 payload is malformed, with an aligned control; a non-finite exp is unknown.
- __tests__/authService.logoutRevoke.w1-4.test.ts:
  - 'sends the SAME stored value' now drives login() and refreshSession() instead of repeating a literal key;
  - the SecureStore-throws spy is restored in finally;
  - new pin: a failure inside the preparation never costs the POST.
- __tests__/authService.bootOptimistic.a3.test.ts:528: the ONLY edit resolves the pending boot-refresh POST while logout is pending. Its assertions are unchanged and green.
- Mutation: the green's 22/22 killed. In this pass, 15 of 18 were killed, including the ADV-A1 identity mutant, handoff release, the success guard, the in-flight-then-expired refresh, timer hygiene and the exp/base64url/isFinite edges. The 3 survivors are equivalent, because all refreshes go through the api.ts singleton: release via clear() versus delete(own), `<=` versus `===` on the epoch, and the spent-RT fallback, whose value equals what storage holds.
- Full jest suite: 290 suites / 2880 tests / 44 snapshots, 0 failed. Base was 290 / 2865 / 44; the +15 are this unit's added tests.
- tsc: clean. eslint: 0 errors.

FLAG
None. The client change is unflagged, following the M13-W4 and M23 precedent, and it is OTA-gated: phones on 97b5f15 are unaffected until the next `eas update --branch preview`. On the no-refresh, unexpired or opaque-token path, the wire bytes are identical to before (pinned). The only difference is ordering: local state is cleared before the POST instead of after.

CLAUDE.md FLAG-ROW CORRECTION (ENABLE_LOGOUT_UPSTREAM_REVOCATION row, "SESSION 65 wave W1 flag" block). Apply at merge:
- Replace "INERT until the client sends it" and "the next `eas update` is the real activation lever, not the env var" with:
  "ENABLE_LOGOUT_UPSTREAM_REVOCATION is NOT inert until the OTA once the backend calls admin.sign_out(access_token, "local") (group R-AUTH). On the valid-access-token path Supabase revokes by the JWT's session, and the refresh-token VALUE never reaches Supabase (retro adversary, measured on the pinned supabase-auth 2.31.0). The client half (PR #140 + W1-4d) matters only for the expired and in-flight paths."
- Also correct "on the expired path revocation happens via that rotation plus the sign_out on the NEW session". That path cannot be reached through the route today: get_current_user 401s an expired Bearer before logout_user runs.

BACKEND HALF
The backend lands in R-AUTH, not here: admin.sign_out(access_token, "local") regardless of the refresh token, the run_db offload of the upstream leg, and the expired-Bearer server path that also covers builds already on phones.

ACTIVATION GATE
The next `eas update --branch preview`. The server-side effect still needs R-AUTH plus ENABLE_LOGOUT_UPSTREAM_REVOCATION=true. After the OTA, check on-device with a test account: log in, idle past 1 h (or log out during a cold boot refresh), log out, then POST /api/v1/auth/refresh with the old refresh token. It must return 401 once R-AUTH is live.

HONEST LIMITS
- If the refresh really is black-holed (it takes longer than 5 s), logout sends the pair it has. That is an expired Bearer on the expired path, which the server still 401s. The rotated RT2 that lands later is discarded by the epoch guard and stays live upstream until R-AUTH's server-side expired-Bearer path exists.
- A later logout may still WAIT up to 5 s on an earlier session's hung refresh. It never uses that refresh's pair.
- Double-tap logout: only the first tap's handoff can match the in-flight refresh. A second tap sends the stored pair or, once the first has cleared storage, sends nothing. This is the same as base.
- Expiry is strict (exp <= now), with no leeway. A token that expires in transit can still 401.
- A 401 on the pre-logout refresh means no logout POST is sent.
- A transient in-flight failure followed by an expired token costs one more bounded refresh attempt. This is now pinned.
- Pre-existing and out of scope: refreshSession's 401 branch calls clearSession() with no epoch check, so an earlier session's hung refresh that finally 401s would clear a later session. This exists on base too.
- In the multi-worker full run, jest printed 'A worker process has failed to exit gracefully' once. --detectOpenHandles over the seven auth suites is clean.

FOLLOW-UPS
- R-AUTH: admin.sign_out(access_token, "local") under the flag with a run_db offload; an optional expired-Bearer server path for pre-OTA builds.
- Consider a small exp leeway (for example 30 s) in isJwtExpired.
- Consider epoch-guarding refreshSession's 401 clearSession (the pre-existing cross-session clear).
- The header of the existing w1-4 test file still repeats the "revokes by REFRESH token" premise. It is prose only.
- HistoryScreen.mobileJank.m21 MB-flows-08 failed in the green's full run and passed in this one. That file mocks both changed modules, so it is flaky; worth its own check.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
