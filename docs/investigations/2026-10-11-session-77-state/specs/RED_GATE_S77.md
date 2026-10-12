# Orchestrator RED gate: unit S77 REDIS-OFFLOOP (2026-10-11 ~20:15)

RED file: tests/test_s77_redis_offloop.py, sha256 f42bc7318a8ad64e66ceb2168a2be23317fe47f1312e372ba6b85e66a074ade4, 1997 lines, pure ASCII.
Independent re-run by the orchestrator: [pyt] tag=s77-redgate elapsed=17s status=FAIL rc=1 -> 107 failed, 44 passed (66 AssertionError, 41 ModuleNotFoundError raised inside test bodies). Worktree status: only the new test file is untracked. GATE: APPROVED.

Answers to the RED agent's questions (binding for GREEN):
- G1 Heartbeat bounds: ACCEPTED as written (>= 6 ticks for the 0.3 s case, >= 8 for the 0.4 s case, OFF <= 1), based on the measured Windows timer granularity; the relative bounds of RO6 stay.
- G2 test_parity_s6[nocache]: ACCEPTED (no in-scope call in either branch; asserts no GET and equal call lists).
- G3 The two extra AST pins (async awaited _negcache with exactly one durable dispatch and every call site awaited; exactly one S4b lambda evaluating sitemap_discovery_is_cold inside with its four keyword arguments) and the sitemap_discovery_is_cold direct-call ban: ACCEPTED as part of the GREEN gate.
- G4 Dispatch shapes are BINDING: run_redis_offloop receives a bare callable name (get_cached, set_cached, resolve_pdp_via_sitemap, ...) with positional arguments, or a zero-argument lambda for S4b only. No functools.partial, no local aliases.
- G5 The S4b :8436 row design (Dior Sauvage EDT 100ml KWD woo hit, should_negative_cache patched True, keys built through scs.build_size_aware_price_cache_key): ACCEPTED.
- G6 GREEN may change a RED test ONLY for a PROVEN wrong-reason failure (a test that cannot pass against any correct implementation of the spec + rulings). It must report the exact diff, why the test was wrong, and proof that the edited test still turns red on a relevant mutant. Any other test change is a defect. The orchestrator re-reviews every test edit at the diff gate.
- G7 The extra env names the autouse fixture deletes (PRICE_CACHE_BUST, ENABLE_SITEMAP_MATCH_V2, ENABLE_NORMALIZE_WORDS_EMPTY_FIX, ENABLE_GENUINE_PRICE_PRIORITY, ENABLE_GENUINE_PRICE_CLOBBER_GUARD, ENABLE_REVIEW_SOURCE_CONSULT): ACCEPTED.
