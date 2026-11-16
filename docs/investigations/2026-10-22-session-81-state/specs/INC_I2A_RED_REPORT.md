# INC-I2a PICTURE-NOT-CUT: RED report (S96, RED agent Opus 5.5, 2026-11-16 22:35-23:40 AST)

Base main fd983471f3949178ebbbd6d56070d571b37fec93, worktree sc-s96-i2a, branch fix/inc-i2a-picture-not-cut. Spec V2 + RULINGS R-1..R-19 read in full before and after.

## Files (new, untracked; nothing else changed)
- tests/test_inc_i2a_picture_not_cut.py: sha256 9e99caf355a48b1e4de39698dea4aee88bb9394b523122819f1a60da90858627, 60292 bytes, 0 non-ASCII, LF, black-clean (black 26.5.1), ruff CI tier + full repo rule set clean. 67 nodes (E1..E28 = 50 nodes; E23 parity pin 4; P1 8; P2..P5 5).
- tests/fixtures/inc_i2a_flag_off_golden.json: sha256 ae5e31faf2fbe1cadd65f75007b795a720d6864a7eb82bdb3d8621f165c224da, 1818 bytes, ASCII, LF. Recorded at base by a temporary recorder test (deleted); flag "false" and R ON gave the identical snapshot.
- Measured at base: CASCADE_SRC_SHA_BASE 3f3b8ad50c077e5408270f85373d8fe0a88100a15cace2ca186612590a14ad8b; PICK_GUARD_RULES (GUARD_SET digest[:8]) b39b9d79.

## Runs
- base: [pyt] tag=s96a-red-base4 elapsed=51s status=FAIL rc=1: 50 failed (every E row, AssertionError only, 0 other error types), 17 passed (E23 x4, P1 x8, P2..P5); netguard 0, hermeticity 67.
- prototype: [pyt] tag=s96a-red-proto1 elapsed=34s status=OK rc=0: 67 passed; netguard 0.
- comm set (union rule): 467 files, sha256(list) 0c845fa0caf0785fad5c9e7c87d70078ec4c1ddabb3ef82a0e7f428cbe786a62, 19 chunks, bound 1200 each, all ran to completion (no TIMEOUT). Base 27 FAILED (stored harness/base_records/fd983471.../0c845fa0....txt + .files.txt); head 26 FAILED; comm -13 EMPTY. Base-only: test_shopify_pdp_json.py::TestPerDomainSpacing::test_back_to_back_fetches_sleep_between_requests (timing). Moved pins: none.
- mutants: 32 of 32 KILLED (M1..M28 with M9a/b/c, M19a/b, M22a/b), each the RED file alone with -k, bound 600, AssertionError kills (M19a: str/list params die with AttributeError, the denied/http params by assertion).
- lint: ruff --select E9,F63,F7,F82 on the touched .py: clean. black --check: image_service.py and structured_comparison_service.py are NOT black-clean at base either and not in .github/black-clean-paths.txt (not applicable); the RED file is black-clean (change 4: add it).

## R-8
git grep scripts/ tests/ docs/ (scan_iter, .scan(, keys(, flushdb, PREFIXES, KEY_PREFIX, redis-cli --scan/del): NO Redis flush / purge key-prefix list exists. Nearest: tests/test_migration_043_delete_user_cascade.py:1287 (C8 per-user f-string key fence: user-id keys only; imgpick names are concatenated with no user id): not applicable. GREEN adds nothing for R-8.

## Restore
proto.diff (63129 bytes, sha256 252f7d20...) saved before restore and identical after the mutants. Restore from byte copies: hash-object == HEAD blob for image_service.py (336b3f89), structured_comparison_service.py (6c555e5a), CLAUDE.md (c1aadfbb); lock removed; git status --short = the two new files only.

## Interfaces the RED file fixes (GREEN must match)
IMG: LATE_BIND_FLAG_ENV, late_bind_enabled, PICK_GUARD_RULES ("b39b9d79"), PICK_CACHE_PREFIX, image_late_bind_max_wait_seconds, image_late_bind_reserve_seconds, image_late_max_seconds, image_pick_cache_ttl_seconds (int), pick_cache_name(relevance, variant), get_product_image_url_late(name, *, region, payload, variant, state, relevance); get_cached / set_cached / try_consume_serper_image_credit / search_images / extract_image_via_gpt resolved as module globals per call; set_cached(name, {"u","t"}, ttl). SCS: _late_image_job(coro, bound, slot, state), _late_page_image_choice(price, is_vision), _late_bind_wait_seconds(deadline, now), self._late_images {slot: {task, fut, state, result, is_vision, price_phase1, closed}}, _late_image_bind (async), _late_image_drain_now, _late_image_choose. Log grammars exactly as spec 2(g).

## Deviations / assumptions
1. Knob reader names chosen by the RED agent (spec names only image_late_max_seconds).
2. E5/E6/E7/E10/E11/E14/E16/E26 drive the real _fetch_product_data plus an explicit _late_image_bind() (no full compare); E2/E3/E4/E12/E13/E20/E23/E25/E27/P1/P4 drive full compares through the copied FY25 driver (no scs.get_product_image_url patch).
3. E23 holds the job pending by an ON-only slow cache read (1.5 s): a held Serper would block Phase 1 at base and the parity pin could not be green there.
4. P1 "R ON": ENABLE_PRODUCT_RESOLVER acts only on explicit_pair; the driver uses the parser path, so R ON there is the same path (identical golden). The resolved-name difference (R-12) is covered by E19 only.
5. E13 stream = the product-data hard-cap arm; the stream tail (_emit_stream_deadline_partial) drain is E23.
6. Mutant forms: M1 = the late call awaits the payload first; M5 = the chooser cancels a pending job; M7 = a credit before the cache read; M12 = a module-level flag read; M13 = OFF reads a knob; M17 = the KB-first branch dropped (no path stores a KB value); M20 = the shield dropped (an unguarded set alone is unreachable in E20; E20 asserts fut not cancelled); M21 = drain writes None.
7. Prototype: fire_and_forget imported locally inside the start block (as the base _fire_and_forget wrapper does); _late_images reset beside both `self._partial_product_data = None`; the IMG knob parse uses `0 < v < inf` (no math import); CLAUDE.md edit minimal (one Feature Flags sentence after the ENABLE_IMAGE_GUARD_SHORT_LINE one + a short block after INC-I2e): GREEN writes the full block.
8. Comm set source-scanning part approximated by grep (inspect.getsource / ast.parse, or read_text / glob / listdir / open together with an app/ or .github path) UNION the named pins and the CLAUDE.md readers, MINUS test_precommit_hook*.py.

## NOT MEASURED
- The fourteen client jest fences (no jest run by this agent).
- Production behaviour, Serper latency, Upstash latency (hermetic only).

## Open questions for the gate
- OQ1 / OQ2 of the spec stand (serper_await kept; an llm_pick started before the life closes may finish after the build).
- P1 R ON does not exercise the resolver (deviation 4): accept, or require an explicit_pair golden with a resolver fixture?
