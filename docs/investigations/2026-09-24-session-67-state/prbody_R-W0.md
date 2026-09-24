## Retro-fix R-W0 (W0-1 DNS memo + W0-2 shared transport (#135, merged in session 65 without review))

Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (Fable-gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 agents with Fable gating, on the pinned CI stack.

**Both flags stay default OFF** (`ENABLE_OFFLOOP_DNS_RESOLVE`, `ENABLE_SUPABASE_CLIENT_REUSE`); flag OFF is byte-identical to base (the M13/M14 construction pins re-run as mutations).

**Verdict:** adversary round 0 SOUND (2 minors, 7 prove-nothing rows) -> fix round (an empty zombie answer no longer drops a negative; 9 of 11 surviving mutants folded into pins) -> adversary round 1 **SOUND** (2 minors recorded below, both stated limits).

**Gates:** 71 unit nodes green through the process-wide guarded runner `.qa-retro/run_pytest.py` (third-party pre-import only, non-loopback socket guard) in both flag states; the 35-file comm set through the same runner with exactly the 5 accepted base failures (3 example.com SSRF nodes + the live-opt-in env test + the deselected cold `import app.main` node); every mutation from byte snapshots with sha-verified restores; the four `gaierror(-2)` stubs in the two existing offloop test files switched to `socket.EAI_NONAME` so they hold on Windows (11001) and Linux (-2).

**W0-2b measurement (red phase):** on one shared HTTP/2 connection httpcore 1.0.9 couples every in-flight Supabase call and allocates h2 stream ids outside its write lock - ~4% of concurrent requests failed with NO hung call; 0 of 3,989 with `http2=False` (loopback TLS+ALPN). The keep-alive HTTP/1.1 pool keeps the CR-PERFORMANCE-03 shared SSLContext win; `max_connections` stays >= the run_db executor width.

**Stated limits / follow-ups:** (1) the done-callback pops ANY `False` memo for the host, including a concurrent private-address negative another call wrote (ruling 3's single mechanism; the next call simply re-resolves) - follow-up W0-1d could key the memo entry by verdict kind; (2) the late re-check after a memo write is unpinned for a PRIVATE or EMPTY zombie answer in the deadline-to-write race window (the done-callback path IS pinned); W0-1c single-flight and the non-finite `SUPABASE_POSTGREST_TIMEOUT_SECONDS` knob stay open follow-ups.

**HARNESS INCIDENT (already on the rotation list):** this group's red phase once imported `app.services.price_service` before conftest neutralised credentials, with no network guard - real OpenAI/Serper/Upstash calls in that alphabetical range cannot be ruled out; rule 9 (never import app.* before conftest, never run pytest without the process-wide guard) is now in every brief.

**Adversary round-1 minors, verbatim summary:**
- app/utils/url_validator.py, validate_external_url_async, the late re-check after _memo_put (`if cfut.done(): _clear_negative_if_resolved_pub: The late re-check's filtering is unpinned. Mutant N24 replaced the call with an unconditional pop whenever the future finished without an exception, dropping the non-empty and allowed-address checks on that path, and it SURVIVED the 71-node unit set. The done-callback path's filtering IS pinned: C3 and D1 are killed. Only the late-write race (the zombie returns between the deadline and the memo wr
- app/utils/url_validator.py _clear_negative_if_resolved_public (carried from round 0, defect 2; the fixer deliberately did not change it): The callback still pops ANY False memo for the host. Re-probed in this round: a concurrent EAI_NONAME negative was popped by a slow public zombie. Output: (False, False, memo after NX (t, False), memo after call 1 (t, False), final None).

---

R-W0 retro-fix of PR #135 (W0-1b + W0-2b): the off-loop DNS memo stops blacklisting healthy hosts, and the shared Supabase transport becomes HTTP/1.1

Both flags stay default OFF: ENABLE_OFFLOOP_DNS_RESOLVE and ENABLE_SUPABASE_CLIENT_REUSE. Nothing is flipped by this PR, and with the flags OFF behaviour is byte-identical (pins listed below).

## Defect 1 (major, W0-2b): the shared HTTP/2 transport couples every Supabase call
Under ENABLE_SUPABASE_CLIENT_REUSE, every Supabase client shared ONE httpx.Client(http2=True). On a single h2 connection, httpcore 1.0.9 couples all in-flight calls:
- A hung PostgREST stream's read timeout tears the connection down and fails every unrelated request on it.
- Even with NO hung call, about 4% of concurrent requests failed. httpcore allocates h2 stream ids outside its write lock (`_sync/http2.py:134` get_next_available_stream_id vs `:144` _send_request_headers), so out-of-order stream ids reach the server, which must kill the connection (RFC 9113 5.1.1).
- The same server with an http2=False client lost 0 of 3,989 requests.

**Fix:** the shared transport is built with `http2=False`: an HTTP/1.1 keep-alive pool with one request per connection. The CR-PERFORMANCE-03 win (one SSLContext/certifi setup) is kept. The read timeout (the SUPABASE_POSTGREST_TIMEOUT_SECONDS knob, default 8 s) and connect timeout (3.0 s) are unchanged. The pool limits stay 100 / 20.

**Pins (tests/test_retro_w0_2.py):**
- pool._http2 is False.
- ALPN against an h2-capable loopback TLS server negotiates HTTP/1.1.
- A hung call stays bounded at knob + 0.5 s under 4 threads of traffic, and no unrelated request fails.
- No-hung-call concurrency: 0 failures.
- A fast request issued during a hung call succeeds.
- max_connections >= the run_db width of 40.
- The pool limits are exactly the base 100 / 20.
- Sequential calls reuse ONE keep-alive TLS connection.

## Defect 5 (minor): flag-OFF anon and user construction was unpinned
Mutations M13 and M14 survived the original unit file. New pins cover flag-OFF get_auth_client() and get_user_supabase_client() (exact ((URL, ANON), {}) call, options None, postgrest 120/120, gotrue 5.0, no shared transport built) and an ON -> OFF rollback. M13 and M14 each turn 2 pins red.

## Defect 2 (major, W0-1b): the 60 s negative memo blacklisted healthy hosts
Three rules close it, all under the per-call flag read:
1. **EAI_NONAME-only memo.** A gaierror is memoised ONLY when exc.errno is in {socket.EAI_NONAME, socket.EAI_NODATA}, read from the platform constants at call time. EAI_AGAIN, EAI_FAIL, a bare gaierror with errno None, and every other code fail closed for THAT call and write nothing. This applies to both the sync and the async validator.
2. **0.75 x timeout rule.** `_resolve` records time.monotonic() when a pool worker starts it. A timeout is memoised only when the job started AND had run at least 0.75 x DNS_RESOLVE_TIMEOUT_SECONDS by the caller's DEADLINE. The deadline is precomputed at submit, so a lagging event loop cannot inflate the run time. A job that never started, or started just before the deadline, writes nothing. A resolve that runs the full bound is still memoised (the P0's black-hole win).
3. **Done-callback pop.** A flag-ON resolve is submitted to the dedicated pool directly (submit + wrap_future, which is what run_in_executor does internally) and gets a done-callback. When a zombie resolve later returns a NON-EMPTY, ALLOWED public answer, any False memo for that host is popped, so the next call re-resolves.
   - It NEVER writes True. test_positive_result_is_not_memoized is the DNS-rebinding contract.
   - A private or EMPTY zombie answer keeps the negative.
   - A late re-check right after the memo write covers the race where the zombie returns between the deadline and that write.

**Pins (tests/test_retro_w0_1.py), all using platform constants:**
- Transient-gaierror reds (EAI_AGAIN, EAI_FAIL, errno None; async and sync).
- A confirmed NXDOMAIN or private address is still memoised, now pinned on the SYNC path too.
- Each confirmed code is memoised on its own. EAI_NODATA is re-pointed to a distinct value, so the pin works on Windows, where EAI_NODATA == EAI_NONAME == 11001.
- A platform without EAI_NODATA still memoises EAI_NONAME.
- A full-bound timeout is still memoised.
- Start-near-deadline, slow-ok and late-start-healthy reds.
- The exact 0.75 fraction, pinned with a per-thread split clock: exactly 0.75 T memoises, just under 0.75 T, 0.60 T and a loop that runs the except branch 10 T late do not, and 0.85 T does.
- The zombie clears but never writes True; a private zombie keeps the negative; an empty zombie keeps the negative; the late re-check holds.
- A cancelled resolve is a normal outcome, not a logged callback failure.
- Flag-OFF direct async never touches the memo.

**Windows vs Linux errno:** EAI_NONAME is -2 on Linux (CI, prod) and 11001 on Windows. Four existing stubs that hard-coded gaierror(-2) now raise socket.EAI_NONAME: tests/test_url_validator_offloop.py:72 and :333, tests/test_url_validator_offloop_hops.py:82 and :410. That is the only edit to existing tests.

## Adversary round 2 (fixer)
- **Fixed, minor: an empty zombie answer dropped a genuine timeout negative.** `_addr_infos_allowed([])` is vacuously True (a pre-existing gap). The callback now requires a non-empty answer before it drops anything. The change is 2 lines inside the flag-ON-only callback. The new pin was red before the fix and green after; reverting the fix (mutant D1) turns it red.
- **Recorded, NOT changed: the callback pops ANY False memo for the host,** including a private-address negative that a concurrent call wrote. Reproduced: both calls still return False, and the next call re-resolves and blocks a private answer again, exactly as flag OFF does, so this is not a security regression. It follows ruling 3 ("pop any False memo") literally. The cost is that a rebinding-style host can keep clearing its own negative, so the memo saves less for it. Tagging memo entries by reason would change the memo shape and is left to the orchestrator.
- **The 7 prove-nothing rows are folded in:**
  - N1, N2, N15 and N3 are killed by the split-clock pin.
  - N6 is killed by the cancelled-callback pin.
  - N5 and N14 are killed by the per-code pins.
  - N10 and N11 are killed by the keep-alive and base-limit pins.
  - N13 is killed by the sync private-address pin.
  - N7 and N9 are equivalent mutants: the pop site re-checks under the lock, and http1=True is httpx's default.

## Flag rows (no new flags)
- **ENABLE_OFFLOOP_DNS_RESOLVE:** memo semantics are confirmed-NXDOMAIN or private-address negatives, plus timeouts whose resolve ran at least 0.75 of the bound by the deadline. A zombie that later resolves to a non-empty public answer drops its negative.
- **ENABLE_SUPABASE_CLIENT_REUSE:** the shared transport is an HTTP/1.1 keep-alive pool (100/20).

The CLAUDE.md W0 flag rows still describe `http2=True` and the started-Event memo rule, and should be updated at merge time.

## Flag-OFF byte-identity
Pins, each re-run as a mutation and killed:
- test_pin_flag_off_gaierror_path_is_base
- test_pin_flag_off_slow_success_is_base
- test_pin_flag_off_never_touches_pool_or_memo
- test_pin_flag_off_direct_async_call_never_drops_a_memo_entry (C5)
- test_flag_off_sync_path_unchanged
- test_pin_flag_off_anon_client_is_the_bare_base_construction (M13)
- test_pin_flag_off_user_client_is_the_bare_base_construction (M14)
- test_pin_flag_off_after_on_rolls_anon_and_user_clients_back
- test_flag_off_construction_unchanged

## Gates
- Unit set: 71 passed with the flags unset.
- Fixer mutation matrix: 19 mutants, 17 killed, 2 equivalent. Each was restored from a byte snapshot with a sha256 check.
- Comm gate over the recorded 35-file set with the guarded runner: batch A 3 failed / 809 passed / 21 deselected, batch B 24 passed / 3 deselected. comm -13 against the recorded base failures is EMPTY; the 3 failures are the network-dependent example.com SSRF nodes that fail identically at base.
- ruff (E9, F63, F7, F82) and py_compile are clean.

## Activation gate
- **ENABLE_OFFLOOP_DNS_RESOLVE** may be canaried as W0 activation step 1 once this lands. Until W0-1c ships, confirm the /url/* limiter caps per-client concurrency at 16 or fewer.
- **ENABLE_SUPABASE_CLIENT_REUSE** is flippable after this lands, subject to the non-finite-knob follow-up and the W3-2 ordering.

## Honest limits
- HTTP/1.1 opens one TLS connection per CONCURRENTLY busy request, up to 100, with 20 kept alive. Keep-alive reuse is pinned on loopback; handshake cost against real Supabase was NOT measured.
- The late-start healthy-host shape is closed by both the 0.75 gate and the callback. Each has its own killing pin.
- A resolve that runs 0.75-1.0 of the bound and then fails with EAI_AGAIN stays memoised for 60 s, by design.
- The callback pop can also remove a concurrent private-address negative (see above).
- tests/test_ssrf_redirect_hardening.py::test_fetch_page_follows_valid_redirect fails whenever ENABLE_OFFLOOP_DNS_RESOLVE is set in the process env, at base and head alike.

## Follow-ups (out of scope under the binding rulings)
1. **W0-1c single-flight (reviewer defect 3):** 16 concurrent validations of one black-holed host fill the 16-worker pool. Needs in-flight coalescing per hostname.
2. **Non-finite SUPABASE_POSTGREST_TIMEOUT_SECONDS (reviewer defect 4):** inf, nan and 1e309 make every request on the transport raise. Add a math.isfinite check and correct the CLAUDE.md sweep line.
3. **Optional:** reason-tagged memo entries, so the zombie callback drops only timeout negatives (round-2 defect 2).
4. **Pre-existing validator gaps**, identical with the flag on or off: 100.64/10, multicast, and an empty addr list are allowed.
5. Update the CLAUDE.md W0 flag rows at merge.

## Red-phase harness incident (for Ahmed)
The red phase's first two base comm-gate attempts used a runner that imported app.* BEFORE tests/conftest.py ran neutralize_credentials(). load_dotenv(override=True) at import then built the module-level OpenAI and Upstash clients with the REAL .env credentials, and those runs had no process-wide network guard. Real OpenAI, Serper or Upstash calls cannot be ruled out. The keys are already on Ahmed's rotation list. Every result in this PR comes from the corrected runner (third-party pre-import only, process-wide non-loopback guard).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
