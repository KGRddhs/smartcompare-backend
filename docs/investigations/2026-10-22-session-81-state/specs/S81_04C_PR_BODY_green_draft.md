## S81-04c REFUSAL-LOG-HYGIENE (FOCUS; NO flag: log-only under R-A1 (b))

Branch `feature/s81-s04c-refusal-log-hygiene`, one commit `4c7cd430` on `a74caba7`. Spec `.qa-s80/S81-04c_UNIT_SPEC.md` (5d052c5a...), rulings `specs/RULINGS_S81_04C.md` (R-04C-12..27) over the brief `specs/S81_04C_BRIEF.md` (R-04C-1..11), gate `specs/GATE_S81_04C.md` (GC-1..GC-12).

### What it does
An `api_budget_service.LLMUnavailableError` (or any subclass) that reaches one of the eight request-path except arms now logs ONE WARNING by type (`<prefix>: <TypeName>`, no `exc_info`, no exception text) in every flag state. On sentry-sdk 2.68.1 with `LoggingIntegration(level=logging.ERROR)` a WARNING is neither an event nor a breadcrumb, so an exhausted spend lane, an open W1-3 breaker or a vision-V2 no-content outcome no longer raises one Sentry event per refused request. There is no flag: nothing else moves.

| Arm | File | Base record (class member) | After |
|---|---|---|---|
| A1 parse | extraction_service | role OFF: ERROR + exc_info + text | WARNING `Product parsing error: <Type>` (the `elif`, R-04C-13) |
| A2 verdict | extraction_service | role OFF: ERROR + exc_info + text | WARNING `Comparison generation error: <Type>`; the base dict, no raise |
| A3 camera | image_routes | role OFF: ERROR with text | WARNING `[IMAGE] Vision call failed: <Type>` (the `elif`); both refunds + 503 / 500 unchanged |
| A4 url | url_extraction_service | role OFF: ERROR by type | WARNING `AI extraction error: <Type>`; `{"error": str(e)}` unchanged |
| B1 specs / B2 price / B3 price fallback | extraction_service | ERROR `exc_summary` (both states) | WARNING by type (both states, L4) |
| B4 reviews | extraction_service | ERROR + exc_info + text (both states) | WARNING by type (both states, L4) |

Invariant (R-04C-12 as amended): every response body, status, SSE frame, refund (call, label, count, order), raise / return flow, `any_role_enabled()` read sequence and every NON-class log record is byte-identical; only the class record at the eight arms changes (group A with role flags OFF, group B in both states). The role-ON S81-06 lines are byte-unchanged. No prompt or payload moves, so the corpus gate is NOT run.

### Defect -> RED nodes (tests/test_s81_s04c_refusal_log_hygiene.py, frozen 774e3e61..., 102 nodes = 23 RED + 79 PIN)
| Defect | Nodes |
|---|---|
| S81-04c (R-S04-10) class at ERROR with role flags OFF | R1 `test_r1_class_refusal_warns_by_type_role_off[parse,verdict,url_extract,specs,price,price_training,reviews]`, R2 `test_r2_camera_refusal_warns_by_type_role_off` |
| subclasses print their own name (R-04C-6) | R3 `test_r3_subclass_prints_its_own_name[8 arms]` |
| group B in the role-ON state (R-04C-12) | R4 `test_r4_group_b_role_on_warns_by_type[specs,price,price_training,reviews]` |
| vision-V2 no-content / spend refusal paths | R5 `test_r5_vision_v2_no_content_warns_by_type`, R6 `test_r6_spend_refusal_warns_by_type_after_the_spend_line` |
| no Sentry event (R-04C-14, positive control) | R7 `test_r7_no_sentry_event_for_a_refusal` |
| identity (PIN) | P0 synthetic-text guard, P1 non-class records (21), P2 deliveries (16), P3 read sequences (32), P4 camera refunds + status (4), P5 anon refund (1), P6 role-ON rows (4) |

At base: 23 failed (all AssertionError), 79 passed. At HEAD: 102 passed. Mutation table (RED round, prototype): 25 mutants, 24 KILLED, M21 (the two camera refunds swapped) EQUIVALENT by R-04C-22; M19 / M20 (one refund dropped) KILLED.

### Deliberate pin changes (spec 4.1)
| E | Old node id | New node id | Change |
|---|---|---|---|
| E1 | `tests/test_s81_s06_router_gate_rows.py::test_g03c_flag_off_parse_site_keeps_the_base_error_line` | `tests/test_s81_s06_router_gate_rows.py::test_g03c_flag_off_parse_site_refusal_warns_by_type` | role flags OFF, FULL config: exactly one record, WARNING, `exc_info` None, message `Product parsing error: LLMUnavailableError`; NEW delivery assertion `st == "ok"` and the base parse-error tuple (R-04C-16); never weakens a delivery assertion |

Every other reader of the changed lines stays green unedited (spec 4.1 "stays green" table).

### Gates at HEAD 4c7cd430 (bounded runner; one pytest at a time, foreign processes checked first)
- RED file + E1 file: 183 passed. `[pyt] tag=s04c-green-unit start=2026-11-11 18:41:31 end=2026-11-11 18:41:47 elapsed=16s bound=600s status=OK rc=0` (`[hermeticity] sentinel checked 183`, `[netguard] blocked 0`)
- CI-order set (s20_result_gate first as the lifespan user, then s03, s04, s04c, s04d, s05, s06_anthropic_router, s06_router_gate_rows): 1367 passed, 0 failed. `[pyt] tag=s04c-green-ciorder start=2026-11-11 18:42:19 end=2026-11-11 18:43:28 elapsed=69s bound=1200s status=OK rc=0` (`[netguard] blocked 48 attempt(s) from 11 node(s)`: the supabase.invalid sentinels, base noise)
- tests/test_secret_scan_static.py: 31 passed. `[pyt] tag=s04c-green-secretscan ... elapsed=10s bound=600s status=OK rc=0`
- tests/test_s80_url_mode_v2.py alone (GC-5): 456 passed. `[pyt] tag=s04c-green-urlv2 start=2026-11-11 18:43:40 end=2026-11-11 18:43:51 elapsed=11s bound=600s status=OK rc=0`
- Comm set: 375 files (the stored record's set 0a224f48...; the re-derivation at HEAD gives 312, all inside it; no file newly referenced), 15 chunks of 25, bound 1200, 0 TIMEOUT: HEAD FAILED 23 = base 47 minus the 23 RED nodes minus the url_mode_v2 wall-clock flake; `comm -13` (branch-only-NEW) EMPTY. Chunk lines `s04c-green-comm-00..14` in the GREEN report.
- CLAUDE.md readers by the import graph (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire) + the secret scan + the .md walkers + test_s81_s06_anthropic_router re-run AFTER the CLAUDE.md edit: 908 passed. `[pyt] tag=s04c-green-claudemd start=2026-11-11 19:14:48 end=2026-11-11 19:15:35 elapsed=47s bound=1200s status=OK rc=0`
- The fourteen backend-scanning client fences (clipboardFallbackService both files) + the seven b3a suites by path through the junction, jest 29.7.0: 21 / 22 suites, 337 / 341 tests; the only failures are the four config/nativeBundle.w37 drift nodes (the baseline). `[jest] tag=s04c-green-fences start=2026-11-11 19:16:08 end=2026-11-11 19:16:20 rc=1`
- ruff E9,F63,F7,F82 + py_compile on the three app files, the E1 file and the RED file: clean; black 26.5.1 --check on the E1 and RED files: unchanged; the hook passed. `git diff --stat`: hunks only, CRLF kept, 0 added non-ASCII bytes. Not run by rule: the FULL jest (the final round's, LC-7), the hook test files (no .githooks change), the corpus gate (no prompt / payload change).

### Stated limits
- L1 A W1-3 denial logs no line of its own (`_openai_dispatch_admission`); an operator sees the arm's WARNING by type, one `[CIRCUIT] openai breaker TRIPPED` WARNING per trip and the compare-entry `[CIRCUIT] openai breaker OPEN` WARNING; no Sentry signal of an OPEN breaker (R-04C-24). ENABLE_LLM_PREFLIGHT_BREAKER is not in the flip order of record.
- L2 The specs / price / price-fallback arms still return `{"error": str(e)}` and the url arm `{"error": str(e)}`; by code read only (GC-6) the specs string is stripped by `_clean_specs` and the price error dicts are never returned; the reassignments at scs :6599 / :6632 / :6663 were not traced; the request-level proof belongs to S81-04e.
- L3 The parse and camera arms carry a deliberate duplicated WARNING body (the `elif`) so the role read stays first; ruff SIM114 (report-only) flags both, the blocking tier does not.
- L4 Group B changes the role-ON record too (base ERROR in both states).
- L5 The WARNING arms that print the exception text (classify, image tier 3 `%r`, specs_targeted, specs_synthesized, disambiguate) and the `query=%r` of both compare-entry OPEN WARNINGs: follow-up S81-04e REFUSAL-TEXT-HYGIENE (PLANNED, R-04C-19).
- L6 M21 (camera refunds swapped) is an equivalent mutant: one latch fires per request.

### Follow-up
S81-04e REFUSAL-TEXT-HYGIENE (planned; classified at its own brief).

### CLAUDE.md (in place, dated 2026-11-11, names only)
The S81-04 stated limit (9); the W1-3 row and the ENABLE_VISION_IDENTITY_V2 row gain one sentence each; the S81-06 clause; the :341 pointer clause in merge order (S81-G8, S81-24, S81-G9, S81-G10, S81-04c); the lagging rows: migration 052 applied + 300 kb_brands rows (ledger 417), the S81-G9 owner steps DONE (417-418), the S81-G10 judge DRY run DONE (419), the store state at :195 / :592 (415-416), ENABLE_LLM_LEDGER_V2 ON on web since the 2026-11-11 17:53 flip line with its canary NOT passed yet (430); the new S81-04c block after the S81-G10 block. The ENABLE_LLM_SPEND_BREAKER canary sentence counts `[SPEND]` lines and 503s, never the limit-(9) events: not edited.

### Owner steps (names only)
None to flip. PROOF STANDARD: merged is not proven; the production proof of this unit is the breaker canary's log read (a refusal shows the breaker's `[SPEND]` line and the arm's WARNING by type, and no Sentry event of the class). Nothing changes in production at the merge: no class member reaches an arm while ENABLE_LLM_PREFLIGHT_BREAKER, ENABLE_VISION_IDENTITY_V2, ENABLE_LLM_SPEND_BREAKER and every role flag are unset on web (ledger line 316 + the flips filed since).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
