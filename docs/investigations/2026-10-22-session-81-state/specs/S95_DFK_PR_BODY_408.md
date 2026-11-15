## S95-DFK: deflake `test_red_late_start_healthy_host_is_not_blacklisted` (test-only)

The test failed the first CI run of #403, #404, the #405 era and #407; each passed on a re-run. In #407's failed attempt (job 132592255457 on 1c139d02) the failure is at `tests/test_retro_w0_1.py:572`, `assert True is False`, which is `assert verdict is False`: the late resolve finished before its caller's deadline.

### Cause
`_start_near_deadline` releases the blocker at 0.8 T (T = 2.0 s), and the late "healthy" resolve then slept 0.2 T. It therefore finished at about T, the caller's own deadline, with zero designed margin. Jitter decided the verdict. A fixed 0.1 s sleep also assumed the blocker had already reached the single worker.

### Change (one file, +30 / -7; every assertion and message kept)
- The helper waits, with a bound, until the stub records that the blocker STARTED, then asserts it, instead of the fixed 0.1 s sleep.
- The helper gains one optional `on_caller_returned` hook, called right after the late call returns. With the default, the sibling test is unchanged apart from the bounded wait above.
- The late healthy resolve waits, with a bound, on a `caller_returned` event instead of sleeping 0.2 T. It therefore finishes after its caller timed out by construction, still about 0.2 T into its run, as ruling 2 needs.

### Proof
- Margin (late finish minus caller return), 30 runs each, on this Windows box. Base: median -0.35 ms, negative in 23 of 30, 0 failures; Windows clock granularity masks the Linux failure. Head: positive in 30 of 30, 0 failures. The sibling test is positive at both.
- Power, the same at base and head. M1 (memoise any started timeout) and M3 (the start stamped at submit) are killed by the sibling test. M1 + M2 combined is killed by both near-deadline tests. M2 alone (keep the negative after a zombie success) is killed by three other tests of the file.
- The whole file passes (30 tests). Five files run in CI single-process order: 237 passed.
- One adversary (TEST-ONLY, SAFE by the leaner chain): SOUND, with 20 of 20 separate runs at the head.

### Stated limits
- The hook runs before the helper's observations are read, as the spec prescribes. Its only caller discards them.
- A fixed 0.2 s settle and a start precondition weaker than the sibling's both predate this change and are untouched.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
