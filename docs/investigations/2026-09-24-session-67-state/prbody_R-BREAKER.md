## Retro-fix R-BREAKER (W1-3 (#147, merged in session 65 without review))

Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (Fable-gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 agents with Fable gating, on the pinned CI stack.

**Verdict:** adversary round 0 SOUND (5 minors, 3 prove-nothing rows) -> fix round (pins for the cancelled-probe outcome and the probe-only Exception arm; a teardown-class `except BaseException` release arm, probe-only) -> adversary round 1 **SOUND** (one equivalent mutant recorded, no test gap).

**Gates:** unit files (`tests/test_retro_w1_3.py` + `tests/test_openai_breaker.py`) 79 nodes green on the pinned venv under a process-wide netguard in both flag states; comm gate over the 16-file set base == head; `ENABLE_LLM_PREFLIGHT_BREAKER` OFF byte-identical (pinned); every mutation from byte snapshots, sha-verified restores.

**Stated limits / follow-ups (W1-3c, not this unit):** a dispatch admitted fail-open during an INCR blip carries probe=True and its release can reset the counter under a real in-flight probe (a second concurrent probe); a stale half_open memo routes a non-probe admission through is_circuit_closed so a 4xx wipes a standing CLOSED streak.

---

## R-BREAKER: W1-3 OpenAI preflight breaker, cancellation and half-open probe fixes (flag-internal, default OFF)

### Defects (retroactive adversary review of PR #147)
- **W1-3a (BLOCKING).** `guarded_llm_create` recorded a breaker failure on every bare `asyncio.CancelledError`. One compare's outer wall cancels every guarded dispatch still in flight. That wall can be the Tier-2 4 s wall, the stream hard cap, a per-stage `wait_for`, a client disconnect or a shutdown. So a single compare could reach `CB_FAILURE_THRESHOLD` while OpenAI was healthy, and the breaker then refused every compare from every user for 600 s. Reproduced through the real `tier2_fill_non_negotiables`: one compare left the blob at `{'state':'open','failure_count':4}`.
- **W1-3b.** An admitted half-open probe that ended in a non-transient outcome recorded nothing. That covers a 4xx other than 429 (context-length or content-policy 400, 401/403/404/409/422) and any non-SDK exception. The single probe INCR was spent and the blob stayed `half_open`. Every later dispatch was denied (INCR >= 2) until the 3600 s blob TTL expired. Meanwhile the read-only preflight admitted every compare, and each one paid the full scrape fan-out before failing at the LLM.
- **Interaction, measured by the red phase.** A literal W1-3a fix (just drop the record) would turn a cancelled half-open probe into exactly the W1-3b wedge.

### Fix (`app/services/api_budget_service.py`, all inside `ENABLE_LLM_PREFLIGHT_BREAKER`)
- `_openai_dispatch_admission()` now returns `(admitted, outcome_matters, probe)`. `probe` is True only when admission went through `is_circuit_closed`'s recovery path.
- **CancelledError arm:** records **nothing**. If this dispatch held the probe, it releases the slot. The cancellation is then re-raised unchanged.
- **Non-transient exception on a probe:**
  - A 4xx other than 429 (`_openai_server_answered`) records **success-for-health**: OpenAI answered, so the breaker closes.
  - Anything else **releases the slot**.
- **Any other BaseException on a probe** (KeyboardInterrupt, SystemExit, or GeneratorExit when an orphaned coroutine is closed) **releases the slot** and re-raises. This was added in the fix phase so that "every admitted probe records a total outcome" holds for every exception Python can raise inside the call.
- **Transient outcomes are unchanged** and still record one failure each: 429, connection error, `APITimeoutError`, 5xx, and a `TimeoutError` raised inside the call. A 429 probe still re-opens the breaker for a fresh window.
- **New `openai_release_half_open_probe()`.** It reads the flag itself on every call, and acts only on a blob that is still `half_open`. It **resets** the per-trip probe counter to `"0"` rather than decrementing it. The reset also discards the INCRs of checks denied while the probe was in flight; a DECR would leave the counter >= 1 and wedge the breaker again. Cost: one GET + one SET, only on that rare path.
- `structured_comparison_service.py` is unchanged.

### Tests
- **Red file.** `tests/test_retro_w1_3.py` goes from 12 RED to green. The inverted MINOR-5 test in `tests/test_openai_breaker.py` is green.
- **13 GREEN-phase pins** fix which total outcome each probe shape records:
  - a non-SDK exception releases the slot; it is not a success;
  - a 4xx records success-for-health;
  - the release is a reset, not a DECR;
  - a CLOSED-streak admission makes no release call;
  - the release writes nothing unless the blob is `half_open`;
  - the helper is a no-op with the flag OFF.
- **8 FIX-phase pins** close the tests the adversary showed prove nothing:
  - `test_fix_cancelled_probe_is_a_release_not_a_verdict[outer-wall|task-cancel]`: right after the cancel, the blob is still `half_open`, `failure_count` is unchanged and the probe key reads `"0"`. This kills N5 (a cancel recorded as SUCCESS), which had survived 71/71.
  - `test_fix_closed_streak_non_transient_outcome_is_not_recorded[400|ValueError|teardown]`: on a CLOSED breaker with a standing streak, each of these makes exactly 1 GET and 0 SETs and leaves the streak untouched. This kills N1 (`elif probe` -> `elif outcome_matters`), which had survived 71/71.
  - `test_fix_teardown_base_exception_on_probe_releases_the_slot`, `test_fix_orphaned_probe_coroutine_closed_releases_the_slot` and `test_fix_flag_off_teardown_and_close_touch_nothing`: pins for the new BaseException arm.
- **Mutation matrices.**
  - Green phase: all 14 mutations killed, including the reviewer's M6, M10 and M14.
  - Fix phase: 9 mutations killed (N5, N6, MB, N10, N1, and BA1-BA4 on the new arm). Every restore was sha256-verified.
- **Comm gate.** The 16-file module-reference set plus the new file, run at HEAD under a netguard plugin: 383 passed / 0 failed. `comm -13` against the base (322 passed / 0 failed) is empty.

### Flag
| Flag | Default | Change |
|---|---|---|
| `ENABLE_LLM_PREFLIGHT_BREAKER` | OFF (per call) | No new flag. The flag-OFF path is byte-identical: the early return is untouched, and every new arm sits after it. Pinned: M14 kills 40 nodes, and a new flag-OFF teardown/close pin makes 0 Redis ops. |

### Activation gate (unchanged order; this PR satisfies items 1-3 of the reviewer's gate)
1. W1-3a: one compare's wall cancelling 3 or more dispatches cannot open the breaker. Pinned. A cancelled probe is a release, never a verdict. Pinned.
2. W1-3b: a non-transient, cancelled or torn-down half-open probe cannot wedge deny-all behind an admitting preflight. Pinned.
3. W1-3d: the 4xx-never-trips pin and the no-read-with-flag-OFF entry pin. Both are in the red file.
4. **Still owed before any flip:** a measured count (from staging `stage_timings` or a flag-ON shadow log) of guarded dispatches per compare under current Bright Data latency.
5. **Still owed before any flip:** `ENABLE_BRIGHTDATA_BUDGET_GATE=true` on `web` and `price-warmer`. This flag is not a spend control.

### Honest limits
- **The breaker no longer sees a slow-but-alive OpenAI stall shorter than the SDK's own deadline.** The client timeout is `httpx.Timeout(120, connect=30)` with `OPENAI_MAX_RETRIES` retries. The compare walls (4 s Tier-2, 30 s hard cap) cancel long before that, and a cancellation no longer counts. Only 429, 5xx, connection errors and full SDK timeouts trip the breaker. An in-guard `deadline` kwarg would restore stall detection. Not done here.
- **A 4xx on a probe counts as success-for-health.** A dead key (401) on the probe closes the breaker, and compares then fail at the LLM exactly as they do with the flag OFF. The breaker is a transport-health signal, not a key-validity check.
- **A SIGKILLed or OOM-killed probe still orphans the slot** until the 3600 s blob TTL, because no Python code runs there. An in-process teardown or a closed orphan coroutine now releases the slot.
- The release path adds one GET + one SET. That happens only with the flag ON, and only on a half-open probe with a non-verdict outcome.

### Follow-ups (named, not addressed)
- **W1-3c:** cross-worker streak decay. A success seen by another worker never resets the shared `failure_count`, so 3 non-consecutive failures still trip the breaker. Reproduced by the reviewer as P3.
- **Stale-memo probe path (fix-phase adversary P6, W1-3c territory).** A worker whose 60 s memo still says `half_open` routes a dispatch through `is_circuit_closed` on a blob that is already CLOSED with a streak. That makes `probe=True`, so a 400 records success and wipes the streak (measured 2 -> 0), where the ordinary CLOSED path leaves it at 2. Flag ON only. It is defensible under "the server answered", but inconsistent.
- **Fail-open probe over-admission (fix-phase adversary P5).** `_openai_dispatch_admission` returns `probe=True` for a fail-open admission (`_redis_incr` returns 0 during a Redis blip). If that dispatch is then cancelled, its release SETs the counter to `"0"` while the real probe is still in flight, and one extra concurrent probe is admitted. The over-admission is bounded, happens only with the flag ON, and needs a Redis INCR failure during a live probe. The fix needs `is_circuit_closed` (shared with the firecrawl/scrapedo/serper breakers) to report whether it actually took the probe. It belongs with the stale-probe window below.
- Per-compare contextvar dedupe (at most one recorded failure per compare).
- A stale-probe window in `is_circuit_closed` (re-admit a probe after about 2x the request timeout). It closes the SIGKILL/OOM orphaned-probe case.
- Optional: the preflight denies while a half-open probe is outstanding (a plain GET of the probe counter).
- An in-guard `deadline` kwarg to restore genuine-stall detection (see Honest limits).
- **PO-RECORDED-MEASURED-04c:** the existing compare tests in `tests/test_openai_breaker.py` are not zero-network. Measured across phases: 36 google.serper.dev and 61 neutralized.supabase.invalid getaddrinfo attempts from 6 existing tests (red phase and fix-phase HEAD); 30/61 in the green phase. Their flag-OFF `bd_search_web > 0` assertions flake with DNS and ordering state. Fix: in that file's autouse fixture, reset `serper_service.SERPER_API_KEY`, stub `get_admin_supabase_client`, and add a socket guard.
- Reviewer minor: the corpus SHA from `scripts/verify_flag_byte_identity.py` proves nothing for this unit, because that harness never reaches `guarded_llm_create`. Flag-OFF identity rests on the pins above.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
