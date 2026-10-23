# S81-06 ANTHROPIC-ROUTER: RED report (agent RED, Opus 5.5)

Unit S81-06 (lane A), flags ENABLE_ANTHROPIC_{TEXT,VISION,VERDICT,CRITIC,MODERATION} + ENABLE_SONNET_ESCALATION + ENABLE_OPENAI_PRE_V3.
RED base e1878dd836e721d7e8c6c53fe1aa3d2b9fadb83e (worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s06, detached, HEAD verified).
Precedence applied: RULINGS_S81_06 (R-S06-1..18) > review corrections > spec.
Notes folder: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/S81-06_red/ (notes.md, every log, junit xml, comm/, mut/, proto/).

## File written (the only change in the real worktree)

| path | sha256 | bytes |
|---|---|---|
| tests/test_s81_s06_anthropic_router.py | 8e1e03e66eac67ffc0849a0b01094c835467d0d11127834df2b7aba368bae84b | 130820 |

Pure ASCII (0 bytes > 127), LF (0 CR), no NUL, ruff E9/F63/F7/F82 clean. git status --short: `?? tests/test_s81_s06_anthropic_router.py` only.

## Re-anchor at e1878dd8
dfc6502f..e1878dd8 = ST1 only (CLAUDE.md, review_service.py, usage_service.py, redis_offloop.py, the ST1 test). Every spec anchor in the touched app files re-measures UNCHANGED (sites :1385 :1525 :1583 :1742 :1791 :1847 :2643 :2685; image_service :186; openai_service :474 :642 :758 :833 :895; url_extraction :945; critique :174; moderation :252; scs :1732 :1755 :1836 :3972 :3992 :4153 :4724 :4747; image_routes :342/:345). S81-04 contract read from b5f29e35 and S81-05 from e6d35a46 via `git show` on the shared object store (no checkout, no extra worktree).

## Step 2: base pin runs (re-taken at e1878dd8, one process at a time)
- `[pyt] tag=s06-red-base-a start=2026-10-23 22:06:34 end=2026-10-23 22:07:24 elapsed=50s bound=1200s status=OK rc=0` (10 files): 509 passed, 1 skipped, 2 deselected; `[hermeticity] sentinel checked 510 test(s)`; `[netguard] blocked 121 attempt(s) from 6 node(s)` (test_openai_breaker sentinel class, baseline). The spec's one failure (the env-safety child timeout) did NOT recur in-set on the idle box.
- `[pyt] tag=s06-red-base-envsafety start=2026-10-23 22:08:01 end=2026-10-23 22:08:25 elapsed=24s bound=600s status=OK rc=0`: 24 passed, 1 skipped, 2 deselected; `[hermeticity] sentinel checked 25 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- `[pyt] tag=s06-red-base-b start=2026-10-23 22:09:48 end=2026-10-23 22:10:19 elapsed=32s bound=1200s status=OK rc=0` (10 files): 588 passed; `[hermeticity] sentinel checked 588 test(s)`; `[netguard] blocked 20 attempt(s) from 1 node(s)` (test_retro_w1_3 curl_cffi, baseline).
- `[pyt] tag=s06-red-base-c start=2026-10-23 22:10:46 end=2026-10-23 22:12:14 elapsed=88s bound=1200s status=OK rc=0` (9 files): 741 passed, 1 deselected; `[hermeticity] sentinel checked 741 test(s)`; `[netguard] blocked 8 attempt(s) from 8 node(s)` (w49 sentinel class).
- Total 1,838 passed (spec: 1,837 + the timing node, which passed here in-set and alone).
- The review's 7 added files ran inside the comm set (chunks below): all green at base.

## Step 3-4: the RED file at base
`[pyt] tag=s06-red-base-v2 start=2026-10-23 22:48:59 end=2026-10-23 22:49:27 elapsed=28s bound=600s status=FAIL rc=1`
- 341 nodes: 230 failed (every one AssertionError: junit messages parsed, 0 non-assertion, 0 errors), 111 passed.
- `[hermeticity] sentinel checked 341 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- 73 RED rows (230 nodes) all red, 18 PIN rows (111 nodes) all green.
- RED rows: R01, R02, R02b, R02c, R03 (x7 flags x14 values), R03b, R04 (x15 real sites), R04b, R05 (x6), R05b, R06, R07, R08, R08b (x4), R08c, R08d, R09 (post/get), R09b (post/get), R09c, R09d, R10, R10c, R11 (x4), R11b, R11c, R11d, R12 (x6), R12b, R13, R13b, R13c, R14 (x8), R15, R16, R16f (x6), R16g (x8), R17, R17b, R17c, R17d, R18, R19, R20, R20b, R21, R22, R23, R24, R25, R25b, R26, R27 (x2), R27b, R28, R28b, R29 (x5), R29b, R30, R30b, R31, R32, R33 (x5 cells), R34a, R34b, R35, R36, R36b, R37, R38, R39, R39b, R40, R41.
- PIN rows: P01 (15 sites x 6 OFF spellings, FULL config), P02, P03 (x6), P04, P05, P06, P07, P08, P09, P09b, P09c, P10, P11, P12, P13, P17, P17b.
- Base failure reasons (per row, base_reasons.txt): router absent (most), anthropic fake 0 calls at the real sites, INSUFFICIENT_DATA instead of the envelope (R07/R08d), INTERNAL_ERROR stream event (R08/R17d), 500/400 routes (R09/R09b), identify ran (R09d), [None, None] scope (R24), S81-05 / S81-04 file absent (R05b/R25b), real SDK absent (R16/R34a), warn 0 (R34b), CREDENTIALS_UNSET / manifest / SEVEN_FLAGS / requirements absent (R35-R37), direct guarded_llm_create (R39).

Stubs (R-S06-16): app.utils.request_context and app.services.llm_spend_breaker are installed in sys.modules ONLY while their real file is absent (ModuleSpec'd stubs); every row patches the accessor on whatever module object sys.modules holds, so at GREEN every row runs against the REAL modules. Rows that need the REAL module/SDK assert it first: R05b (S81-05), R25b (S81-04), R16 + R34a (the real anthropic SDK; GREEN's dedicated venv .venv-s81-06). The fake `anthropic` module (ModuleSpec, the 1.11.0 exception hierarchy, NOT_GIVEN) is installed for every node and lifted for R16/R34a; P09b pins that the fake is the one in use; P09 pins `_netguard.classify_host("api.anthropic.com") == "egress"` and `_blocks(...)` without an attempt.

## Step 5: prototype (scratch worktree, thrown away)
Prototype = proto/llm_router.py + proto/apply_proto.py (+ two follow-up edits: disambiguate cost, camera scope merge).
- ON: `[pyt] tag=s06-proto-on-v2 start=2026-10-23 22:49:32 end=2026-10-23 22:49:49 elapsed=17s bound=600s status=FAIL rc=1` = 337 passed, 4 failed; `[hermeticity] sentinel checked 341 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`. The 4 = R05b, R25b (the real S81-05/S81-04 modules are not on this base) and R16, R34a (the real SDK is not installed): environment-gated by design, green only at GREEN.
- OFF (PIN rows only): `[pyt] tag=s06-proto-off-v2 start=2026-10-23 22:49:57 end=2026-10-23 22:50:03 elapsed=5s bound=600s status=OK rc=0` = 111 passed; `[hermeticity] sentinel checked 111 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- Prototype notes for GREEN: (1) llm_router imports request_context / llm_spend_breaker LAZILY in the prototype (they are absent at this base); at GREEN a module-top import is fine. (2) a `**kw` spread into messages.create would break R38 (keyword None): the prototype passes system=`anthropic.NOT_GIVEN` when absent. (3) SITES needs an `expects_json` attribute (R-S06-15 trigger (b)); vision_v2's schema resolved lazily (circular import with openai_service). (4) the format-None JSON sites (parse, specs, price, price_training, reviews, verdict, verdict_fallback, specs_targeted, specs_synthesized, url_extract, critique) get a JSON-only system line + the Claude-branch fence strip; image_tier3, vision_v1 ({"products": [...]}, unwrapped to the array), vision_v2 (the B3 schema), disambiguate (enum true/false/unknown) get closed schemas. (5) compare_from_text maps an LLMUnavailableError out of the impl and the stream's generic except maps it under any role flag ON; the gate at both entries. (6) the camera gate raises ConsentUpdateRequiredError inside the existing vision try (its coded-503 + refund exit); the url gate is at the top of _compare_urls_metered (before the reserve). (7) the camera scope llm ledger (current_llm_records() after bind) merged into metadata.llm. (8) the processors row's category_ar = the 33-char phrase at privacy_policy_ar.md line 57 (computed with Python, never printed).

## Step 6: mutation table (60 mutants on prototype bytes; byte copy -> exact edit matching once -> pyt -k -x -> restore -> sha256 equal; .qa-mutation.lock held and removed)
All restores sha-verified. 59 KILLED by an AssertionError; M34 counted separately (see below).

| id | mutant | killed by |
|---|---|---|
| M01' | role_enabled always True (replaces the equivalent M01, R-S06-16) | P01[classify-None] |
| M02 | flag reader without strip().lower() | R03[TEXT- TRUE ] |
| M03 | MIN_CONSENT_VERSION 2 | R05[two] |
| M04 | >= -> > | R05[three] |
| M05 | PRE_V3 inverted | R05[none] |
| M06 | refuse path calls dispatch | R06 |
| M07 | REST entry gate removed | R07 |
| M08 | stream entry gate removed | R08 |
| M09 | entry gate reads consent before the flags | P02 (consent recorder) |
| M10 | temperature forwarded | R04[classify] |
| M11 | thinking omitted | R04[classify] |
| M12 | output_config.format dropped | R04[disambiguate] |
| M13 | system left inside messages | R04[classify] |
| M14 | media_type check removed | R11b |
| M15 | unknown kwarg dropped | R12 |
| M16 | prompt_tokens = input only | R13 |
| M17 | refusal raised before the ledger record | R15 |
| M18 | type name in the wrapper str | R17 (and R16f) |
| M18b | `from e` (cause kept) | R16f[0] |
| M19 | 529 / OverloadedError not transient | R16f[1] |
| M20 | terminal 400 records a failure | R16g[0] |
| M21 | max_retries hard-coded 2 | R18 |
| M22 | key unset falls back to OpenAI | R19 |
| M23 | breaker state ignored | R20 |
| M24 | CancelledError records a failure | R21 |
| M24b | cancelled probe not released | R21 |
| M25 | wait_for unbounded | R22 |
| M26 | bind_request_scope binds with all flags OFF | P04 |
| M27 | REST impl scope bind removed (approximates "bound in a child after the first call") | R24 |
| M28 | spend admit not awaited before the call | R25 |
| M29 | escalation cap 2 | R26 |
| M30 | escalation lane "live" | R26 |
| M31 | moderation path still calls moderations.create | R29[flagged] |
| M32 | sampling_kwargs keeps temperature for claude ids | R31 |
| M33 | preflight ignores the anthropic breaker | R33[cell0] |
| M34 | include_prompts=True | R34a red BEFORE the mutation (SDK absent): NOT MEASURED here; killable only in GREEN's venv |
| M35 | 4o counter recorded for a Claude verdict | R40 |
| M36 | a site passes another guarded_llm_create binding | R39 |
| M37 | the refuse log line carries the prompt | R41 |
| MC2 | entry gate counts vision | R08b[text] |
| MC4 | key unset at entry not refused | R08d |
| MC5 | moderation refusal fails open | R29[refusal] |
| MC9a | classify knob read regardless of the decision | P12 |
| MC9b | vision knob read regardless | P12 |
| MC9c | tail reserve knob read regardless | P12 |
| MC12 | disambiguate cost priced at the OpenAI id | R40 |
| MC13 | camera scope llm not merged | R10c |
| MS2 | generate_comparison re-raise removed | R17 |
| MS2b | REST LLMUnavailable mapping removed | R17c |
| MS2c | stream LLMUnavailable mapping removed | R17d |
| MS3 | /url/compare gate removed | R09b[post] |
| MS3b | site 15 re-raise removed | R09c |
| MS4 | camera gate removed | R09d |
| MS5 | vision_v1 array unwrap removed | R13c |
| MS6 | fence strip removed | R13b |
| MS9 | breaker Redis on the loop (no to_thread) | R20b |
| MS10 | explicit base_url dropped | R18 |
| MS11 | schema escalation on a non-JSON site | R27b |
| MS12 | moderated text unfenced | R29b |
| MS13 | preflight ignores the openai breaker in the mixed window | R33[cell0] |

Notes: part 1 (M01-M26 minus M14) ran on the test bytes before the final `_raised_by` / R13b / camera-harness edits; M14 and MS6 were re-run after them (the first M14/MS6 runs failed on pytest.raises `Failed` / a JSONDecodeError, i.e. not AssertionError, so those rows were rewritten assertion-only). Equivalence: none claimed; M01 of the spec is equivalent by its own contract and was replaced (R-S06-16).

## Step 7: comm set at base (real worktree)
List: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/S81-06_red/comm_files.txt (447 files) with per-file reasons comm_reasons.tsv. Union of: module/symbol reference grep (extraction_service, openai_service, image_service, url_extraction_service, verdict_critique_service, content_safety_service, structured_comparison_service, model_config, sentry_service, image_routes, text_routes, url_routes, api_budget_service, llm_pricing, guarded_llm_create, llm_router, llm_spend_breaker, request_context, fill_in_legal, _env_safety, CREDENTIALS_UNSET, processors.json, requirements.in/.txt, LLMUnavailableError, moderate_output, identify_products, generate_comparison, compare_from_text, compare_from_urls, extract_with_ai, critique_verdict, SEVEN_FLAGS, black-clean-paths, w4_11_prompt_digest_recorder) + the named source-scanning pins + the review's 7 files + every source-scanning class (read_text, __file__, inspect.getsource, ast.parse, glob/rglob, "app" joins, listdir/scandir, .github, CLAUDE.md, SmartCompareApp, legal text) + test_start_command*; MINUS test_precommit_hook*.py and the new RED file; the 4 NETWORK_FLAKY_EXCLUDE nodes deselected. 18 chunks (<= 25 files, bound 1200):
- `[pyt] tag=s06-comm-base-00 ... elapsed=202s ... status=OK rc=0` 821 passed
- `[pyt] tag=s06-comm-base-01 ... elapsed=160s ... status=OK rc=0` 597 passed
- `[pyt] tag=s06-comm-base-02 ... elapsed=82s ... status=OK rc=0` 1605 passed, 1 skipped
- `[pyt] tag=s06-comm-base-03 ... elapsed=15s ... status=OK rc=0` 432 passed
- `[pyt] tag=s06-comm-base-04 ... elapsed=38s ... status=OK rc=0` 1471 passed, 2 skipped
- `[pyt] tag=s06-comm-base-05 ... elapsed=208s ... status=OK rc=0` 1894 passed, 1 skipped
- `[pyt] tag=s06-comm-base-06 ... elapsed=40s ... status=OK rc=0` 598 passed
- `[pyt] tag=s06-comm-base-07 ... elapsed=22s ... status=OK rc=0` 339 passed
- `[pyt] tag=s06-comm-base-08 ... elapsed=19s ... status=OK rc=0` 568 passed, 1 skipped
- `[pyt] tag=s06-comm-base-09 ... elapsed=35s ... status=FAIL rc=1` 2 failed, 3630 passed, 22 skipped: test_page_scraping::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, ::TestFetchPagePriceOpenGraph::test_og_meta_extraction (both rows of tests/.pre_impl_failures.txt, base noise)
- `[pyt] tag=s06-comm-base-10 ... elapsed=36s ... status=OK rc=0` 638 passed, 4 skipped
- `[pyt] tag=s06-comm-base-11 ... elapsed=105s ... status=FAIL rc=1` 902 passed, 2 errors: test_prompt_truth::test_render_digests_match_base_except_the_fence, ::test_truth_on_prefix_static_and_cacheable (the known cold-tiktoken pair)
- `[pyt] tag=s06-comm-base-12 ... elapsed=101s ... status=OK rc=0` 2350 passed
- `[pyt] tag=s06-comm-base-13 ... elapsed=109s ... status=OK rc=0` 1468 passed, 1 xfailed
- `[pyt] tag=s06-comm-base-14 ... elapsed=60s ... status=OK rc=0` 744 passed, 2 skipped
- `[pyt] tag=s06-comm-base-15 ... elapsed=58s ... status=OK rc=0` 613 passed, 6 skipped
- `[pyt] tag=s06-comm-base-16 ... elapsed=40s ... status=OK rc=0` 509 passed, 35 xfailed
- `[pyt] tag=s06-comm-base-17 ... elapsed=26s ... status=OK rc=0` 1117 passed, 10 skipped
Totals: 20,296 passed; base failure set = the 2 baselined test_page_scraping nodes + the 2 tiktoken ERRORs, exactly the recorded base noise. (Full [pyt] lines with start/end and per-chunk [netguard]/[hermeticity] lines: comm/chunkNN.log.)

## Step 8: restore check
Real worktree HEAD e1878dd8; `git diff --quiet HEAD` rc 0 over 3,418 tracked files; status = only the new test file untracked. Scratch worktree removed with `git worktree remove --force` (worktree list no longer shows it). No pytest process with an `s06-` tag alive.

## Deviations from the spec (rulings applied; for the gate)
1. Schemas (R-S06-1): no OPEN_OBJECT_SCHEMA (R01 asserts its absence); R02b asserts every schema is None or CLOSED; R02c pins only the ruling-mandated ones (image_tier3, vision_v2 = B3 schema, vision_v1 {"products": array}, disambiguate enum). The per-site choice for the other JSON sites is left to GREEN; R13b pins the fence strip only where a JSON site has no format.
2. SITES gains `expects_json` (R-S06-15 trigger (b)); classify False, every other site True.
3. R09 asserts the EXISTING refund shape (refund_comparison_credit(user_id) once) per R-S06-2; R17 moved to the generate_comparison boundary; R17b pins "ANY role flag ON"; R17c/R17d pin the REST/stream mapping; P17/P17b pin flag-OFF identity.
4. R33 is the 5-cell AND table (R-S06-4); assumption: the active providers are those of the text + verdict roles.
5. R11 (passthrough) forces the no-Pillow branch; R11c (cap) and R11d (Pillow downscale) cover both R-S06-8 branches (Pillow is dev-only in requirements-dev.txt, so production takes the cap branch).
6. R18 asserts the explicit base_url (R-S06-7); R19 asserts the key check precedes the spend admit and the breaker read; R20b asserts the breaker GET off the loop and the 0.5 s fail-open.
7. R29: refusal -> (False, 'refusal'), dispatch failure -> (False, 'unavailable') (R-S06-6 fail closed); malformed JSON outcome NOT pinned (open). R29b: fenced moderated text + synthetic prompt.
8. R36: the row is appended at the END and GATED by ENABLE_ANTHROPIC_TEXT (R-S06-14, not the spec's gate_flag null); R36b asserts eight fill-in flags (literal_eval of SEVEN_FLAGS in scripts/fill_in_legal.py).
9. R37 pins anthropic==1.12.1 (R-S06-13).
10. Sentry: R34a needs the real SDK (child probe, memory transport); R34b asserts a live client and ONE WARNING when the SDK is not importable (R-S06-11).
11. No RED rows for: R-S06-7's additive /health breaker key; R-S06-12's cache-key provider axis and the WARNING-not-ERROR log rule for the four dispatch-level refusal sites; R-S06-17 owner steps (docs). Named as gaps for the gate.
12. P09: netguard has no host list (measured); pinned via classify_host/_blocks with no attempt (a NEW egress node would trip the ratchet).
13. M27 approximated by deleting the impl bind (the "child task" placement is not single-edit expressible); M34 is not killable without the real SDK.

## Open questions for the gate
- Q-a: is "active providers = text + verdict roles" the intended R-S06-4 scope (critic / moderation OFF still on OpenAI)?
- Q-b: the moderation classifier's malformed-JSON outcome (spec: fail open; R-S06-6 names refusal / dispatch failure only).
- Q-c: R-S06-12 (cache key provider axis, WARNING-level refusals at the four sites) and the R-S06-7 /health key need rows: add in a RED amendment or at GREEN?
- Q-d: the url gate placement: before the credit reserve (prototype) vs after with a refund; R09b accepts either (refunds == consumes).
- Q-e: R-S06-5 camera gate scope: the prototype refuses on the vision role only; should the camera also refuse for the compare roles before identify (the text entry refuses later anyway)?
