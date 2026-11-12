# S81-12d RED REPORT (relaunch on 445f8de3; OPENAI-EGRESS-STOP; Opus 5.5 RED agent; 2026-11-12)

Written through the shell. Base origin/main 445f8de3e624d3d52a6903bafa6bfae0cb750cf6. Rulings A-K applied (J and K newest).
Nothing here says a production problem is fixed: hermetic rows are necessary, never the production proof (H6).

## Files (ADDED to the real worktree sc-inc-12d, untracked; nothing else touched)
- tests/test_s81_s12d_openai_egress_stop.py  66635 B  sha256 817530e20b0f357d8a445043c1f6ba8d578f5c1f7ba2de7207a65c76effcb269
- tests/test_s81_s12d_no_byte_e2e.py          28792 B  sha256 e563bc1df021f06b6b35cbfe7ee199d459e3a09aac1fd62a524d76c88fdf4cfe
- copies: <SP>/S81-12d/red/r2/final/. ASCII only, LF only, no 8-digit run, no credential shape, ruff E9/F63/F7/F82 clean.

## Base record (K-4 a): tree(445f8de3) = tree(cccfb855) = 692a3f9308c88a10259d737d900a13e422e0d644.
Copied to <SP>/harness/base_records/445f8de3e624d3d52a6903bafa6bfae0cb750cf6/a3b26842...{.files,.txt,.header.txt} (773 files, 27 ids), header says so. B1-B4 NOT re-run (K-4 b).

## Runs ([pyt] lines)
- B5 base, both RED files, real worktree (final bytes):
  [pyt] tag=inc-12d-red-base-final start=2026-11-12 13:05:27 end=2026-11-12 13:05:54 elapsed=27s bound=600s status=FAIL rc=1 (waited=23s)  -> 62 failed, 62 passed; every failure AssertionError (0 non-assert lines); failed set = r2/red_base_failed.txt
  (first base run on pre-normalisation bytes: tag=inc-12d-red-base 12:53:54-12:54:17 elapsed=22s status=FAIL rc=1, the same 62/62 and the same failed set)
- CI-order 7.3 at base, order 1 (16 files): [pyt] tag=inc-12d-ci-base1-final start=13:06:19 end=13:07:56 elapsed=96s bound=1200s status=FAIL rc=1 -> 62 failed, 1529 passed; failed set == alone set
- CI-order at base, order 2 (s20 first): [pyt] tag=inc-12d-ci-base2-final start=13:08:04 end=13:08:31 elapsed=26s bound=1200s status=FAIL rc=1 -> 62 failed, 228 passed; == alone set
- Prototype OFF (RED files): [pyt] tag=inc-12d-proto-final-off start=13:11:00 end=13:11:25 elapsed=25s bound=600s status=OK rc=0 -> 124 passed
- Prototype ON (ENABLE_OPENAI_EGRESS_STOP=true exported for the one call): [pyt] tag=inc-12d-proto-final-on start=13:11:29 end=13:11:54 elapsed=25s bound=600s status=OK rc=0 -> 124 passed
- Prototype CI order 1, flag unset: [pyt] tag=inc-12d-ci-proto1-off start=13:08:40 end=13:10:09 elapsed=89s bound=1200s status=FAIL rc=1 -> 1 failed (tests/test_s81_s03_llm_ledger_v2.py::test_k1_guarded_llm_create_untouched = E1), 1590 passed
- Prototype CI order 2, flag unset: [pyt] tag=inc-12d-ci-proto2-off start=13:10:18 end=13:10:43 elapsed=26s bound=1200s status=OK rc=0 -> 290 passed
- Prototype CI order 1 with the flag exported ON (earlier bytes): [pyt] tag=inc-12d-ci-order-proto-on 13:02:09-13:03:30 elapsed=81s status=FAIL rc=1 -> 257 failed / 1334 passed: 255 nodes of OTHER files that do not delete the flag (u3c, s03, s04, s06, breaker, cost meter, content_safety ...: they assert OpenAI traffic, which the ambient stop removes) + K1 + one E01 flake (fixed below). The two RED files are hermetic to the ambient flag (proto-final-on). Recorded as data, not a defect: CI never exports the flag.
- E-row measurement on the prototype (14 files): [pyt] tag=inc-12d-proto-erows2 start=12:43:15 end=12:44:50 elapsed=95s bound=1200s status=FAIL rc=1 -> 1 failed (K1), 1540 passed.

## Rows (31 RED + 7 PIN; parametrised ids multiply nodes: 62 RED nodes, 62 PIN nodes)
File A RED: S12D-01..06, -09, -10, -11, -14 (16 sites), -15, -16 (8 arms), -17, -18, -20, -21 (J-5: 2 arms x 2 role flags), MC-1, MC-2[stop_on], MC-3[stop_on], MC-4.
File A PIN: S12D-07, -08, -12 (8 cases incl. OPENAI_BASE_URL stock, D-2), -13, -19, -22 (J-5 + J-11: 2 arms x consent / anthropic / W1-3 admission / spend), MC-2[stop_off_pin_half], MC-3[stop_off_pin_half].
File B RED: E01/E02, E03 (+ ENABLE_FULL_STREAM_DEADLINE, D-2), E04 (+ ENABLE_VISION_IDENTITY_V2), E05 (+ ENABLE_URL_MODE_V2), E06 (quick, parse, price-kpi), E07, E09, E10 (re-ruled), E11, E12.
File B PIN: E08 (12 entries x unset / "false" / " garbage "): status, OpenAI request count per path, base64 sha256 of the normalised body, frozen from two base OFF runs per entry.
Base OFF measured: text get/post/stream 11 chat + 1 moderation (200); camera 1 chat, 500 SERVER_ERROR (v1, v2); url 3 chat, 503 LLM_UNAVAILABLE (v1, v2); parse 1 (200); price-kpi 3 (200); quick 1 (400 BAD_REQUEST); warmer 1.

## Draft verification (K-4 d): the 6b909e0a draft re-run at 445f8de3 (tag inc-12d-dev-a1) and every row re-checked
- S12D-08 PIN failed at base (stub returned object(); route() reads .choices): stub now a ClaudeChatResult.
- S12D-16[camera] ConnectError: the sync recorder refused TestClient's 'testserver'; the recorder now passes 'testserver' through (all four httpx/httpx2 send methods), refuses every other host.
- The stop counter counted flag-OFF calls (the helper is CALLED when OFF): it now counts only raising calls.
- verdict_fallback has no catching arm in the harness: both states raise (RAISING_SITES).
- Added: S12D-20 no-subclass (AST + __subclasses__), S12D-21, S12D-22, MC-1..MC-4, file B entirely.

## Prototype (scratch worktree, thrown away; <SP>/S81-12d/red/tools/proto.py)
H1 after the prologue in guarded_llm_create (before the spend admit and before every MON1 hook); H2 in moderate_output after the Claude branch inside the try; H3 / H4 in the two scripts; the J-3 operand `and not isinstance(e, _llm_breaker.OpenAIEgressStoppedError)` at extraction_service.py verdict arm (:2833) and url_extraction_service.py url_extract arm (:988); K-2 (3.11) providers_in_use: function-local `from app.services import api_budget_service as _abs` and `and not _abs.openai_egress_stop_enabled()` on the openai leg. MON1 test_l01 checks module-TOP imports only and Y01 env names: both stay green (measured), so no E-row and no alternative needed. The classifier needed no change (MC-1 green by construction).
Not prototyped (GREEN): the docstring sentence and census comment of 3.1 (they move K1 further; E1 is re-measured on GREEN bytes anyway).

## E-rows measured on the prototype (K-5, J-7)
- E1 tests/test_s81_s03_llm_ledger_v2.py::test_k1_guarded_llm_create_untouched (K1 digest) - the ONLY moved pin.
- NOT moved (green with the prototype): the arm pins of test_s81_s04c_refusal_log_hygiene.py, test_s81_s06_anthropic_router.py, test_s81_s06_router_gate_rows.py (J-7 candidates); every row of test_inc_mon1_credential_health.py / _probe.py / _gate_rows.py (incl. G01 GATING_AST_B64, L01, Y01); u3c, content_safety, s04, model_config_enforced, u8d, spec_spine_d2, shadow_experiments.

## Mutation table (prototype byte copies in the scratch worktree; lock .qa-mutation.lock; killing rows only via -k; bound 600; restore + sha256 verified per mutant; driver tools/mutants.py; logs r2/mut/inc-12d-mut-*.log; results r2/mut/mutants.json). Every kill is an AssertionError.
| Id | Mutant | Result | Killing nodes |
|---|---|---|---|
| M01 | delete H1 | KILLED | S12D-03 x2, -05 |
| M02 | H1 below the spend admit | KILLED | S12D-03 x2, -04, -05 |
| M03 | H1 inside the preflight-OFF branch | KILLED | S12D-03 x2, -05 |
| M04 | H1 before the store write | KILLED | S12D-04, -05 |
| M05 | reader default "true" | KILLED | S12D-01, -12 x3 (unset), -13[None], -19[None] |
| M06 | reader without strip | KILLED | S12D-01 |
| M07 | reader ("true","1") only | KILLED | S12D-01 |
| M08 | reader cached at import | KILLED | S12D-01, -17 |
| M09 | class derives from RuntimeError | KILLED | S12D-02, -16 x8, E04 x2 |
| M10 | helper raises plain LLMUnavailableError | KILLED | S12D-03 x2, -16 x8 |
| M11 | message gains " (rate stop)" | KILLED | S12D-02, -15 |
| M12 | log line at ERROR | KILLED | S12D-10, -11 |
| M13 | latch removed | KILLED | S12D-10 |
| M14 | latch shared across surfaces | KILLED | S12D-10 |
| M15 | log line carries kwargs.get("model") | KILLED | S12D-05, -10 |
| M16 | delete H2 | KILLED | S12D-06, -14[moderation] |
| M17 | H2 before decide_moderation() | KILLED | S12D-07 |
| M18 | H2 after get_client() | KILLED | S12D-06 |
| M19 | H2 outside the try | KILLED | S12D-06 |
| M20 | delete H3 | KILLED | S12D-18, -20 |
| M21 | H4 inside the retry loop after the create | KILLED | S12D-18, -20 |
| M22 | H1 passes "moderations" | KILLED | S12D-10, -20 |
| M23 | helper returns instead of raising | KILLED | S12D-03 x2, -14 x16 |
| M24 | helper inverted | KILLED | S12D-03 x2, -12 x8 |
| M25 | app module gains import tiktoken (I-4) | KILLED | S12D-20 |
| M26 | operand removed at the verdict arm | KILLED | S12D-21[verdict] x2, E10, E11 |
| M27 | operand removed at the url_extract arm | KILLED | S12D-21[url_extract] x2, E12 |
| M28 | exclusion widened to the whole class (both arms in one mutant) | KILLED | S12D-22 x8 (both arms, all four kinds) |
| M29 | subclass of the stop class under app/ | KILLED | S12D-20 |
| MM-1 | in-use exclusion removed | KILLED | MC-2[stop_on], MC-3[stop_on] |
| MM-2 | H1 moved after the create inside MON1's try (the failure hook sees the 401) | KILLED | MC-4 |
| MM-3 | classifier maps the stop class to rejected | KILLED | MC-1, MC-4 |
| M-D9 | H4 before the store write (ruling D-9) | SURVIVED | equivalent by ruling D-9 (both raise before any create) |
Totals: 32 counted mutants KILLED (M01-M29, MM-1..3); M-D9 run as the ruled-equivalent survivor (diff: H4's two lines moved above `kwargs["store"] = False` in _create_with_retry).

## Comm set (step 7; K-4 a)
List <SP>/S81-12d/red/r2/comm_list.txt (775 = the 773-file stored base set a3b26842... + the two new RED files); per-file reasons <SP>/S81-12d/red/r2/comm_reasons.tsv (whole free tier G-2 / I-2; module-grep hits for the seven touched modules: 238 file-module pairs, every hit file is a member; named source-scanning pins; CLAUDE.md readers). No whole-tree base pass (K-4 a): the base record is the stored cccfb855 record by tree equality (27 FAILED/ERROR ids). Chunks NOT run at base by ruling.

## Restore check
Real worktree HEAD 445f8de3; sha256 of all 3583 tracked files after == before (r2/base_tracked_sha_445f8de3.txt vs r2/after_tracked_sha.txt: identical); git status --short = only the two new test files; scratch worktree removed (git worktree remove --force; absent from worktree list); no inc-12d python process alive.

## Deviations from the spec (as amended)
1. Census (S12D-20): at 445f8de3 the dispatch set has a SIXTH function: MON1's llm_credential_probe._metadata_call (models.retrieve x2, openai + anthropic; the D-6 chain rule cannot tell the anthropic one apart). Its OpenAI leg is gated by the K-2 (3.11) in-use rule, not a stop statement; the row lists it in GATED_BY_IN_USE and asserts that providers_in_use reads `<module>.openai_egress_stop_enabled()` exactly once.
2. E08 freezes per entry a base64 sha256 of the normalised body (plus status and per-path counts), not the full body text (size; the added-line sweep). Normalisation: VOLATILE keys dropped (ids, clocks, durations, elapsed_seconds), the SDK 401 texts and the stop message -> <ERR>, metadata.source_trace lists compared order-free (measured: products order swapped once under load in the CI-order run; the base digests were re-measured after this change and did not move).
3. E08 parameters: D-2's ENABLE_FULL_STREAM_DEADLINE / ENABLE_VISION_IDENTITY_V2 / ENABLE_URL_MODE_V2 are separate ENTRIES (e03_stream_deadline, e04_camera_vision_v2, e05_url_mode_v2), each with its own frozen OFF literal.
4. The e2e harness stubs the spend breaker's Redis edges (entry_refuses_async False, admit returns no ticket) and the Shopify / noon / Serper / URL-validator I/O (the w49 quota_outage harness); the flag reads stay real.
5. S12D-22 runs with the stop OFF (a stop ON would raise before the admission / spend denial, so those members could not be reached); the consent and Anthropic members are raised at the chokepoint seam.
6. S12D-14 asserts zero raising stops OFF (the helper is called, returns None); the spec's "stops == 0" read literally would be wrong.
7. File B imports helpers (not tests, not fixtures) from file A.
8. Mutant count: the rulings say 32 with one ruled equivalent; M01-M29 + MM-1..3 = 32 are all KILLED and D-9 is a 33rd run (M-D9) that survives as ruled.

## Open questions for the gate
- Q1 Rule deviation 1 (the census now carries MON1's probe call, gated by the in-use rule) and whether GREEN should also put a stop statement in _metadata_call's openai leg (belt and braces; not required by K-2).
- Q2 Accept the E08 digest form (deviation 2) and the source_trace order-free rule.
- Q3 Accept E1 (K1) as the only E-row: measured on the prototype, none of the J-7 / K-5 candidates moved.
- Q4 Flag exported ambient ON makes 255 nodes of other files fail (they assert OpenAI traffic); recorded only.

## Not measured
- The comm set head pass (GREEN's job); the fourteen client fences (no client change).
- K1's new digest (GREEN bytes).
