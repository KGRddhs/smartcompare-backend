# S77 POSTHOG B GREEN notes
- 03:15 start. RED shas verified: 488e75a6 (server), 91ad84ae (drain). worktree HEAD 18121839.
- 03:35 G1 + G2 legal run
- 03:40 G5 run1 (capture ON the loop): p50 30.2 ms p99 51.4 ms per capture; cProfile: 100% in posthog.utils.system_context -> platform.win32_ver -> WMI query per call (Windows only). Spec 4.3 fallback applies: capture moves into asyncio.to_thread.
- 03:44 G5 run3 (capture in to_thread): per-capture longest loop stall p50 0.237 p99 5.688 max 39.7 ms; property build on loop p99 0.013 ms; capture never on loop thread; 0 http; 0 netguard.
- 03:46 G5 run4 (supplementary, win32_ver memoised = Linux stand-in): per-capture loop stall p50 0.101 p99 0.366 max 1.02 ms; wall p50 0.233; bare on-loop capture (memo) p50 0.018 p99 0.143.
