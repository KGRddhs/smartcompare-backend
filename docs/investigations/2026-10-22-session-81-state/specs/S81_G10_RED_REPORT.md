# S81-G10 RED REPORT (D-S22-J1 + S81-22b + S81-22c + S81-04d; orchestrator Opus 5.5 by the owner's ruling of 2026-11-07)

- Agent: the S81-G10 RED agent, Opus 5.5 (claude-opus-5-5). Session 89, 2026-11-09, 14:38Z start.
- Base: 90d4ed74bdd16f62130dc9f7a4727620f8a1cea2 (real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g10, detached, `git status --short` empty at start).
- Spec: .qa-s80/S81-G10_UNIT_SPEC.md sha256 53ebfa6920a3c0dcd1949d78bf396c29542e57f225ceb1c5a4c9a5892359c8d2 (re-measured; 94,975 B ASCII LF), as amended by specs/RULINGS_S81_G10.md R-G10-1..16 (binding), brief specs/S81_G10_BRIEF.md.
- Notes folder: <scratchpad>/S81-G10_red/ (notes.md, progress.txt, every probe / script / log named below). <scratchpad> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/07cedb96-2752-480a-aa62-62e55837e125/scratchpad.
- This report is written through the shell (make_report.py) to <scratchpad>/S81-G10_red/RED_REPORT.md and <scratchpad>/S81-G10_RED_REPORT.md; COMM_SET.txt, COMM_SET_HEAD.txt and comm_reasons.tsv beside it.

## 1. Files written in the real worktree (exactly five, R-G10-13; pure ASCII, LF; no 8-digit run, no secret shape, no gitleaks-keyword digest name)

| file | bytes | sha256 |
|---|---|---|
| tests/test_s81_s22j1_judge_jsonb_filter.py | 21706 | 94143f05ad736ec4d4cb5fb8abfcb30b7d8cb8ada252b8227cecbf8496b2bbbb |
| tests/test_s81_s22b_self_critique_retire.py | 21860 | bd94edc8296784e3c62918baa816eb61cc7bb216d13b11ce86fdc91bd97735ec |
| tests/test_s81_s22c_kb_product_ids.py | 13654 | 364f88a80688ba9b9935910447007820e736252f8e39c274b31d1ae606d2fa15 |
| tests/test_s81_s04d_durable_retrieve.py | 16807 | 5be53dbdf19e0b2975e01496d04c8d123f696bcbd4f925ca1d6488e66264483c |
| tests/fixtures/s81_s22b_flag_off_golden.json | 146604 | de994a8e88f11ba4a0246253a31e90302bd3c1a5da6277b82ddf23ab6181b10c |

`git status --short` of the real worktree: only these five `??` entries (section 9).

## 2. The rows per unit (RED fail at base on AssertionError only; PIN green at base)

### D-S22-J1 tests/test_s81_s22j1_judge_jsonb_filter.py: RED 6 / PIN 16 (22 nodes)
The real postgrest 2.31.0 SyncPostgrestClient over an httpx MockTransport fake PostgREST (400 / 22P02 to `cs.{batch_pending}`, 200 + the pending marker to `cs.["batch_pending"]`, 200 [] elsewhere); `scripts.cron_compare_judge` resolved by find_spec in the body; `cj._now` / `common._now` frozen at 2026-11-09 09:00Z; KNOBS synthetic.
- RED test_r1_resume_operand_is_json -- AssertionError: the resume read sent 'cs.{batch_pending}' (decoded param; also pins the full param list of that request).
- RED test_r2_resume_raw_query -- AssertionError: raw query `...flags=cs.%7Bbatch_pending%7D...` (wants `flags=cs.%5B%22batch_pending%22%5D`, no `cs.%7B`).
- RED test_r3_dry_end_to_end_provider_absent -- AssertionError: {'APIError': 1} (= the 2026-11-07 DRY totals).
- RED test_r4_dry_end_to_end_batch_ended -- AssertionError: resume filled 0, errors {'APIError': 1} (wants filled 1, no POST/PATCH/DELETE, no ledger, no delete).
- RED test_r5_apply_end_to_end_batch_ended -- AssertionError (same) (wants ONE llm_spend_ledger POST, ONE compare_judgements upsert POST on_conflict=run_id,judge with the column SET (the `columns` param order varies per process: str hash randomisation, measured) and Prefer resolution=merge-duplicates, the haiku row flags [], ONE compare_runs PATCH id=in.(run) judged_at, ONE batches.delete).
- RED test_r6_apply_batch_lost -- AssertionError (same) (wants ONE upsert of the marker with flags ["batch_lost"], lost 1).
- PIN test_p1_off_makes_no_request[6 spellings x companions on/off] (12): unset / "" / false / 0 / off / " FALSE ": rc 0, zero transport requests, `kb_seed_common._admin_client` never called (client=None), Anthropic factory never called, no breaker call, no report file.
- PIN test_p2_other_requests_unchanged[companions on/off] (2): DRY, no pending rows: the ordered (method, table, params minus the flags param) list equals the literal recorded at base (j1_probe.py -> j1_probe_knobs.json; 7 requests: resume GET, recompare GET, window GET, expired HEAD, sonnet HEAD, the two DRY prune HEADs).
- PIN test_p3_containment_sweep: AST over app/ + scripts/: exactly one chained `.contains(` (scripts/cron_compare_judge.py `_resume`), no overlaps/ov/cs/cd/contained_by call, no `cs.{`/`ov.{`/`cd.{` literal (the scripts/check_channel_freshness.py `ancestry.contains(sha)` look-alike has a Name receiver and is not counted).
- PIN test_p4_flags_column_is_jsonb_array: 048's `flags jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(flags) = 'array')`.

### S81-22b tests/test_s81_s22b_self_critique_retire.py + the golden tests/fixtures/s81_s22b_flag_off_golden.json: RED 10 / PIN 9 (19 nodes)
The orchestrator driver is the S81-18 harness (tests/test_s81_s18_kb_first_serve.py `_compare`, imported as a test-support module); a recorder on `llm_router.route` (site keys; a scripted all-9 critique answer at the `critique` site; `verdict_critique_service.get_client` stubbed where the module exists); `feedback_service.save_comparison` / `delete_cached` / `track_event` / `referral_service.ReferralService` recorders (+ `_persist_verdict_critique` where it exists); the FULL companion config (ENABLE_ARABIC_VERDICT_OUTPUT + output_lang ar, ENABLE_COMPARISON_ID_ECHO, ENABLE_COMPARE_RUN_LEDGER (the row via compare_runs.build_run_row), ENABLE_LLM_LEDGER_V2 ON, ENABLE_FULL_STREAM_DEADLINE OFF and ON, every S81-06 role flag OFF).
- RED test_r1_module_absent -- AssertionError: verdict_critique_service still exists.
- RED test_r2_no_reference_left -- AssertionError: 55 retired references (54 line hits = the spec's 1.4 map + the module file itself).
- RED test_r3_orchestrator_surface -- AssertionError: assert (not True) (`_apply_self_critique` present).
- RED test_r4_save_path_surface -- AssertionError: ['_persist_verdict_critique', '_without_verdict_critique', 'critic_model'].
- RED test_r5_model_config_without_the_openai_critic -- AssertionError: assert not True (critic_model present; then the resolved_models literal of 4 roles).
- RED test_r6_preflight_ignores_the_retired_name -- AssertionError: ENABLE_SELF_CRITIQUE still adds the critic's provider (role flags text + verdict ON, consent 3 via `llm_router._consent_version`, openai preflight OPEN, anthropic CLOSED; unset -> False holds at base, true -> True at base).
- RED test_r7_manifest_row -- AssertionError: the 7-entry openai module list (wants the 6 of the base list minus the module; every other openai field and the R22 identity fields of every other row equal base).
- RED test_r8_rest_inertness -- AssertionError: ['critique', 'critique'] (the routed site keys with ENABLE_SELF_CRITIQUE=true).
- RED test_r9_stream_inertness -- AssertionError: ['critique', 'critique'].
- RED test_r9b_stream_inertness_under_the_full_stream_deadline -- AssertionError: ['critique', 'critique'] (also the persisted payload, follow-ups and run row equal the unset ones).
- PIN test_r10_persisted_payload_is_the_body: persist_comparison hands save_comparison the SAME object; follow-ups == [cache_bust, track_event, loop2].
- PIN test_p1_off_identity_golden[6 spellings] (6): the golden recorded at base (scratch recorder test, two snapshots equal = deterministic): REST + SSE payloads (deadline OFF/ON), routed site keys ([] both), persisted payload (is the body), follow-ups, the compare_runs row (stage_timings dropped).
- PIN test_p2_router_and_model_tables_kept: ROLE_FLAGS, _ENTRY_ROLES, every SiteSpec (role, max tokens, expects_json, schema-is-None; `critique` included), _ANTHROPIC_ROLE_DEFAULTS, anthropic_model('critic') == claude-haiku-5-5, the two consent gates callable.
- PIN test_p3_the_table_and_its_migration_kept: 030 + rollback LF sha256 and both migrations listings (base64 digests).

### S81-22c (with D-S22-K1) tests/test_s81_s22c_kb_product_ids.py: RED 7 / PIN 17 (24 nodes)
Seams: the S81-18 driver (`_on`, `_card`, `_compare`, `_golden_snapshot`, `_raising_recorders`) and the S81-22 row builder / route harness (tests/test_s81_s22_compare_runs.py `_row`, `body_frag`, `Rec`, `_route_world`, `_hit`, `_full`; through it tests/test_s81_s20_result_gate.py).
- RED test_r1_rest_full_full -- AssertionError: None (kb_hit ["full","full"] asserted unchanged first).
- RED test_r2_stream_full_full -- AssertionError: None.
- RED test_r3_partial_miss_and_a_miss_view_id_is_never_served -- AssertionError: None (classify wrapped so a MISS view carries a ghost pid: the stamp must still give None).
- RED test_r4_camera_path -- AssertionError: None.
- RED test_r5_row_from_the_key -- AssertionError: assert None == ['fragrances|acme|nimbus-noir|EDP', None] (plus the element-nulled-with-survivor cases).
- RED test_r6_d_s22_k1_producer_vocabulary -- AssertionError: assert None == ['full', 'miss'] (plus partial/partial, full/full, miss/miss, the frozen hit/miss, and bogus / FULL / wrong lengths -> None).
- RED test_r7_end_to_end_text_post -- AssertionError: sources_used.kb_hit None (both flags ON; the S81-18 driver's full/miss body through text POST; wants the row's kb_product_ids [P0 id, None] and kb_hit [full, miss]).
- PIN test_p1_kb_off_identity[6 spellings x companions on/off] (12): no kb_product_ids anywhere, no KB entry point (raising recorders); companions OFF: the S81-18 golden; companions ON: the unset-spelling payloads under the same config (deviation D1).
- PIN test_p2_both_miss_no_key[no-cards, raising-rpc] (2); PIN test_p3_shapes_never_raise; PIN test_p4_compare_runs_imports_no_kb_module; PIN test_p5_ledger_off_no_insert_no_build (route, raising stubs).

### S81-04d tests/test_s81_s04d_durable_retrieve.py: RED 4 / PIN 6 (10 nodes)
The real `_run_bounded_async` / `record_soon`, LLM_SPEND_REDIS_TIMEOUT_SECONDS=0.05, a fake upstash-shaped client (eval sleeps 0.3 s then raises or lands), a loop exception-handler recorder, gc.collect inside the loop, caplog, an asyncio spy for the wrapped future's callbacks.
- RED test_r1_late_failure_after_the_bound_is_retrieved -- AssertionError: ['Future exception was never retrieved'].
- RED test_r2_awaiter_cancelled_then_late_failure_is_retrieved -- AssertionError: ['Future exception was never retrieved'].
- RED test_r3_record_soon_late_eval_failure -- AssertionError: ['Future exception was never retrieved'] (then: fail_open exactly 1, the breaker logger's lines == [the one fail-open WARNING]).
- RED test_r4_the_twin_and_its_attach_point -- AssertionError: llm_spend_breaker._retrieve_quietly is missing (then: ast.dump of the twin body == redis_offloop's, docstring aside, same arg name; the attach inside `if durable:` before the one shield call).
- PIN test_p1_late_success_lands_once; PIN test_p2_cancelled_inner_future_is_left_alone; PIN test_p3_in_bound_failure_propagates[durable, plain] (2); PIN test_p4_plain_path_unchanged (the wrapped future's callbacks at wait_for == ['_call_check_cancel']); PIN test_p5_leaf_import_rule.

Totals: RED 27 (6 + 10 + 7 + 4), PIN 48 (16 + 9 + 17 + 6); 75 nodes.

## 3. The base runs and the prototype ([pyt] lines in section 8)
- Base (real worktree, files present, nothing else changed): j1 6F/16P (g10red-j1-base), 04d 4F/6P (g10red-04d-base), 22c 7F/17P (g10red-22c-base2; g10red-22c-base was the first draft whose P1 companions-ON cells failed against the S81-18 golden: deviation D1), 22b 10F/9P (g10red-22b-base). Re-runs after the digest re-encoding (section 1): g10red-j1-base2 / g10red-22b-base2. Every failure line `E   AssertionError` (logs j1_base.log, s04d_base.log, s22c_base2.log, s22b_base.log).
- The P1 golden: recorded at base in the scratch worktree by a scratch-only recorder test (tests/test_zz_g10_record_golden.py, never in the real worktree) through the RED module's own `_snapshot` (two snapshots equal), g10red-22b-record.
- Prototype: a DETACHED junction-free scratch worktree <scratchpad>/S81-G10_red/proto at 90d4ed74 (`git worktree add --detach`), carrying the four units in the spec's GREEN order (proto_apply.py `all` = J1 + 04d + the 22c scs insertion FIRST against base lines + compare_runs; THEN proto_22b.py = the six scs deletions by anchor-checked ranges (+8 shift) + feedback_service / llm_router / model_config / api_budget_service / processors.json / legal_s78.json / the module and the two suites deleted; THEN proto_erows.py (the D-S22-K1 widening the spec agent's script had left out, the three remaining retired references, and every E-row) and proto_erows2.py (EB11b, EB12b found by the prototype)). CRLF kept everywhere; `git diff --stat`: 30 files changed, 142 insertions(+), 1674 deletions(-), hunks only (proto_diffstat.txt). The exact diffs: proto_code.patch (app/ + scripts/) and proto_erows.patch (tests/).
- Prototype runs: the four RED files 75 passed (g10red-proto-red; re-run after the re-encoding g10red-proto-red2); set A (S81-22 / S81-04 / S81-18 / G4 / G8 / s77 / kb_schema / shutdown_drain / s24) 5 failed / 1483 passed = the base-record environmental nodes only (j01, b02, s18b r2, s24 r92 + p83); set B (the 22b E-row files + the openai_breaker importers + the legal manifest readers + migration 030 + prompt_fence + the SSE contract files) found TWO E-rows the spec's table lacks (EB11b, EB12b) -> fixed -> g10red-proto-B2 55/55; set C (source-scanning pins, orchestrator / SSE / deadline / settle files, s20 lifespan user, CLAUDE.md readers, G9 gate rows) 3 = the base-record env nodes (s10 r06 + the two test_prompt_truth cold-tiktoken ERRORs). ruff E9,F63,F7,F82 + py_compile clean on the five files.

## 4. The code edits GREEN makes (the prototype's, exact strings in proto_apply.py / proto_22b.py / proto_erows.py; diff proto_code.patch)
- scripts/cron_compare_judge.py `_resume` (:502): `.contains("flags", ["batch_pending"])` -> `.contains("flags", json.dumps(["batch_pending"]))` (R-G10-8 inline; one comment line naming the jsonb rule is GREEN's).
- app/services/llm_spend_breaker.py: `_retrieve_quietly(fut)` defined right before `_run_bounded_async` (body `if not fut.cancelled(): fut.exception()` + a docstring; any docstring wording, the ARG NAME `fut` is part of R4's ast.dump equality) and `if durable: future.add_done_callback(_retrieve_quietly)` between the wrap_future line and the shield line.
- app/services/structured_comparison_service.py: S81-22c FIRST inside `_stamp_unit_metadata` after `metadata["kb_hit"] = list(kb_marks)` (the 8 lines: views padded to 2, the full/partial + non-empty str pid predicate, `if any(kb_ids): metadata["kb_product_ids"] = kb_ids`); THEN the six S81-22b deletions by anchor (the `self._regen_model_downgraded` init; the sync I3.1 call block; the sync I3.2 `_crit_meta` threading; the stream `_critique_coro` / wait_for block; the stream I3.2 threading; `_apply_self_critique` + `_verdict_critique_metadata`). The sync I3.1 deletion leaves two blank lines (cosmetic; collapse optional).
- app/services/compare_runs.py: `_kb_product_ids(meta)` beside `_cache_hits`; `"kb_product_ids": _kb_product_ids(meta)`; D-S22-K1 `all(m in ("hit", "miss") ...)` -> `all(m in ("full", "partial", "miss", "hit") ...)` (NOT in the spec agent's proto_apply.py; in the spec's change list 22c.3 step 3).
- app/services/feedback_service.py: the critic_model import, `_without_verdict_critique`, the persist argument -> `full_response=full_response`, `_crit = ...`, the I3.2 block, `_persist_verdict_critique`; the track_after_persist docstring "three follow-ups ... (savings-cache bust -> cohort event -> referral Loop 2; the critique persist was retired by S81-22b)".
- app/services/llm_router.py: `_self_critique_on` and the two-line critic leg deleted; the docstring clause "the critic when ENABLE_SELF_CRITIQUE is ON," deleted (else R2 stays red: measured). ROLE_FLAGS / _ENTRY_ROLES / SITES / consent gates untouched (R-G10-2).
- app/services/model_config.py: the OpenAI `"critic"` default + its comment, `critic_model()`; `_ANTHROPIC_ROLE_DEFAULTS["critic"]` KEPT.
- app/services/api_budget_service.py :947 comment line; scripts/cron_learning.py :100 comment -> `# the retired self-critique pass's threshold (S81-22b); PIN P5 holds the literal` (else R2 red: measured); app/legal/processors.json :67 the one module line; DELETE app/services/verdict_critique_service.py.

## 5. The E-rows (GREEN's; each proven on the prototype; exact strings in proto_erows.py / proto_erows2.py / proto_22b.py; diff proto_erows.patch)
| E-row | file | anchor / old | new | reason (measured) |
|---|---|---|---|---|
| EJ1 | tests/test_s81_s22_judge.py `_Q.execute` | `elif name == "contains":` / `rows = [r ... for x in a[1])]` | `vals = json.loads(a[1]) if isinstance(a[1], str) else a[1]` + `... for x in vals)]` | the frozen fake pinned the rejected array literal (a str operand iterated its characters): J-M5 = 5 frozen nodes red without it |
| EJ2 | tests/test_s81_s22d_ledger_pins.py `S22_LF_SHA` | `"tests/test_s81_s22_judge.py": "b7c2c377...d8430"` | the post-EJ1 LF sha256 (9245b85b462ce576f1b7eb4ee93232491cd51ecefcbadeab2729d969ee695905 for the prototype's exact EJ1 bytes; GREEN recomputes for its own EJ1 text) | p2 frozen-file pin follows EJ1 |
| EB1 | tests/test_arabic_verdict_output_w414.py | env list `"ENABLE_SELF_CRITIQUE",`; `_install_recorders` (`holder = {"gen": [], "regen_args": []}` + the `_apply_self_critique` recorder); test_29 / 29b / 29c regen_args asserts; test_33 | env line deleted; `holder = {"gen": [], "stopped": []}` + a raising recorder on `trust_validation_service.validate_verdict` (the first call after the verdict on BOTH paths: imported at call time, scs :4712 sync / :5567 stream at the prototype) appending "validate_verdict"; the regen_args asserts -> `assert holder["stopped"] == ["validate_verdict"]` (gen asserts kept); test_33 deleted | R-G10-3: the stop point measured on both paths; 29 / 29b / 29c[sync] / 29c[stream] / 33 red without it |
| EB2 | tests/test_comparison_quality_v2.py | `import app.services.verdict_critique_service as vcs`; the `# Self-critique: an honest hedge ...` section (`_critique` + TestCritiqueHedgingExemption, 3 nodes) | deleted | collection ImportError otherwise |
| EB3 | tests/test_feedback_service.py :26 | `monkeypatch.setattr(fs, "_persist_verdict_critique", AsyncMock())` | deleted | AttributeError in test_successful_save_busts_home_savings_cache |
| EB4 | tests/test_model_config.py | the three `"critic": ...` rows (LEGACY_DEFAULTS, RESOLVERS, ENV_VARS) | deleted | collection AttributeError |
| EB5 | tests/test_model_config_enforced.py | the vcs import; `>= 16` (docstring + assert); the `critique_verdict` branch of `_call` (4 lines); the SHIPPED `critique_verdict` row; `resolved_models()` literal with `"critic"` | deleted / `>= 15` (docstring: "since S81-22b 15 (the critique dispatch retired)") / literal without critic | measured red set of the spec (4 nodes + collection) |
| EB6 | tests/test_openai_breaker.py | `from app.services import verdict_critique_service as vc_mod`; the `MINOR 6` section (test_verdict_critique_dispatch_feeds_the_breaker) | deleted | collection of this file and of test_cost_meter_s74 / test_s81_s03_llm_ledger_v2 / test_retro_w1_3 / test_s81_s22d_ledger_pins (importers) |
| EB7 | tests/test_s70_model_router_downgrade.py | docstring `R2.6 the self-critique regen: the served verdict's marker wins.`; the R2.6 block up to the R2.8 header | `R2.6 the self-critique regen: retired by S81-22b (its rows deleted).`; block deleted (the env list's ENABLE_SELF_CRITIQUE delenv kept: harmless) | 5 nodes import the deleted module |
| EB8 | tests/test_s81_d22_nightly_learning.py p5 | reads app/services/verdict_critique_service.py | reads scripts/cron_learning.py CRITIQUE_THRESHOLD == 7 and migrations/030 `bias_score integer NULL` / `missing_citation_score integer NULL` (whitespace-normalised) | the module file is gone |
| EB9 | tests/test_s81_s06_anthropic_router.py | the vcs import; REPLIES["critique"]; BASE_KW["critique"]; run_site's critique branch (4 lines); r14's "critique" param + its elif (2 lines); p10's `"critic": "gpt-4o-mini",`; SITE_FUNCS' verdict_critique_service row; p07 + p13 `run_site("critique", ...)` | deleted; p07 / p13 re-pointed to `run_site("classify", ...)` with `BASE_KW["classify"]` | 12 nodes red otherwise; SITE_ROLES / SITE_CAPS / every `_route("critique", ...)` row KEPT (the kept SiteSpec) |
| EB10 | tests/test_s81_s06_router_gate_rows.py | G05 cell `(({"text", "verdict"}, True, False, True), True)`; G13_SITE_KEYS `"critique"`; `len(G13_SITE_KEYS) == 16` | `False` (comment: ENABLE_SELF_CRITIQUE inert); removed; `== 15` | G05 cell 3 + G13 red otherwise |
| EB11 | tests/test_u3c_store_false_pin.py :455 | `assert sites >= 16, "... since S81-06, saw %d"` | `>= 15`, "... since S81-22b" | spec EB11 |
| EB11b (NEW, not in the spec table) | tests/test_u3c_store_false_pin.py :454 / :456 | the comment `16 routed sites (16 + 16 + 1 = 33 spreads ...)`; `assert spreads >= 33, "... 33 spreads since S81-06 (16 + 16 + 1) ..."` | comment + `-> 15 routed sites (15 + 15 + 1 = 31 spreads)`; `>= 31`, "31 spreads since S81-22b (15 + 15 + 1)" | measured on the prototype: "census floor is 33 spreads ..., saw 31" (test_u3c_03) |
| EB12 | tests/test_comparison_id_echo.py | `_base_result` docstring + its `_verdict_critique` entry; FollowUps.install `_persist_critique` recorder + setattr; the four `["cache_bust", "track_event", "persist_critique", "loop2"]` pins (:606, :953, :980, :1023); `follow_ups.calls[3][1]` (:610) | removed; removed; `["cache_bust", "track_event", "loop2"]`; `calls[2][1]` | 22 ERROR nodes (the setattr of a deleted attribute) |
| EB12b (NEW) | tests/test_comparison_id_echo.py `Insert` + 8c | `self.calls.append(kwargs)` only; 8c reads `insert.calls[0]["full_response"]` and asserts the response KEEPS `_verdict_critique` | `Insert.snapshots` (a json round trip of full_response AT CALL TIME); 8c reads `insert.snapshots[0]`, keeps `comparison_id` not in the row + cohort_injected, drops the keeps-`_verdict_critique` assert, adds row metadata == response metadata | measured on the prototype: with no sanitizing copy the route's later comparison_id echo mutates the recorded object ("comparison_id" seen in the recorder; the insert itself happened before the echo) |
| EB13 | tests/fixtures/legal_s78.json :283 | `"app/services/verdict_critique_service.py",` in manifest_base.openai.module | deleted | R22 equality with processors.json |
| EC1 | tests/test_s81_s11b_result_aggregates.py | P1: `got = _g8_snapshot(monkeypatch, truth)` | `got = _set_aside_kb_product_ids(_g8_snapshot(monkeypatch, truth))` + the helper after `_truth_key` (pops metadata.kb_product_ids from every kb_hit == ["full","full"] payload, asserts each == [P0 id, P1 id] and at least one seen) | R-G10-6; the G8 golden NOT re-recorded |
| EC2 | tests/test_s81_s18b_store_label.py | P1: same line | same helper (before the PIN-rows header) + the same call | R-G10-6 |

## 6. Mutation tables (byte copies in the prototype under <proto>/.qa-mutation.lock; each restore sha256-verified; killing rows via pyt -k, bound 600; mut.py, mutation_results*.json, mut_<id>.log)
| M | file | edit | result | killing rows (AssertionError) | restore sha256 ok |
|---|---|---|---|---|---|
| B-M1 | app/services/verdict_critique_service.py | restore verdict_critique_service.py | KILLED | test_r1_module_absent, test_r2_no_reference_left | True |
| B-M2 | app/services/structured_comparison_service.py | restore a no-op _apply_self_critique | KILLED | test_r2_no_reference_left, test_r3_orchestrator_surface | True |
| B-M3 | app/services/feedback_service.py | restore _without_verdict_critique (identity) | KILLED | test_r2_no_reference_left, test_r4_save_path_surface | True |
| B-M4 | app/services/model_config.py | restore "critic" in _ROLE_DEFAULTS | KILLED | test_r5_model_config_without_the_openai_critic | True |
| B-M5 | app/services/llm_router.py | restore the preflight critic leg (env read) | KILLED | test_r6_preflight_ignores_the_retired_name | True |
| B-M6 | app/legal/processors.json | restore the processors.json line | KILLED | test_r7_manifest_row | True |
| B-M7 | app/services/model_config.py | over-delete _ANTHROPIC_ROLE_DEFAULTS["critic"] | KILLED | test_p2_router_and_model_tables_kept | True |
| B-M8 | app/services/llm_router.py | over-delete SITES["critique"] | KILLED | test_p2_router_and_model_tables_kept | True |
| B-M9 | app/services/llm_router.py | remove "critic" from ROLE_FLAGS | KILLED | test_p2_router_and_model_tables_kept | True |
| B-M10 | app/services/structured_comparison_service.py | thread metadata["_verdict_critique"] = {} on the sync path when the env var is true (FIRST occurrence = sync) | KILLED | test_r8_rest_inertness | True |
| C-M1 | app/services/structured_comparison_service.py | drop the stamp | KILLED | test_r1_rest_full_full, test_r2_stream_full_full, test_r3_partial_miss_and_a_miss_view_id_is_never_served, test_r4_camera_path, test_r7_end_to_end_text_post | True |
| C-M2 | app/services/structured_comparison_service.py | stamp also when both null | KILLED | test_p2_both_miss_no_key[no-cards], test_p2_both_miss_no_key[raising-rpc] | True |
| C-M3 | app/services/structured_comparison_service.py | accept a miss view's pid | KILLED | test_r3_partial_miss_and_a_miss_view_id_is_never_served | True |
| C-M4 | app/services/structured_comparison_service.py | reshape kb_hit to the ids | KILLED | test_r1_rest_full_full | True |
| C-M5 | app/services/compare_runs.py | build_run_row keeps None | KILLED | test_r5_row_from_the_key, test_r7_end_to_end_text_post | True |
| C-M6 | app/services/compare_runs.py | the D-S22-K1 widening reverted | KILLED | test_r6_d_s22_k1_producer_vocabulary, test_r7_end_to_end_text_post | True |
| C-M7 | app/services/compare_runs.py | widen to any str | KILLED | test_r6_d_s22_k1_producer_vocabulary | True |
| C-M8 | app/services/structured_comparison_service.py | the stamp outside `if kb_marks:` (as stated) | SURVIVED | - | True |
| C-M8b | app/services/structured_comparison_service.py | the stamp outside `if kb_marks:` AND without the any() guard | KILLED | test_p1_kb_off_identity[unset-companions-on], test_p1_kb_off_identity[unset-companions-off], test_p1_kb_off_identity[empty-companions-on], test_p1_kb_off_identity[empty-companions-off], test_p1_kb_off_identity[false-companions-on], test_p1_kb_off_identity[false-companions-off], test_p1_kb_off_identity[zero-companions-on], test_p1_kb_off_identity[zero-companions-off], test_p1_kb_off_identity[off-companions-on], test_p1_kb_off_identity[off-companions-off], test_p1_kb_off_identity[padded-FALSE-companions-on], test_p1_kb_off_identity[padded-FALSE-companions-off] | True |
| D-M1 | app/services/llm_spend_breaker.py | no attach | KILLED | test_r1_late_failure_after_the_bound_is_retrieved, test_r2_awaiter_cancelled_then_late_failure_is_retrieved, test_r3_record_soon_late_eval_failure | True |
| D-M2 | app/services/llm_spend_breaker.py | the twin without the cancelled guard | KILLED | test_p2_cancelled_inner_future_is_left_alone | True |
| D-M3 | app/services/llm_spend_breaker.py | attach only when not durable | KILLED | test_r1_late_failure_after_the_bound_is_retrieved, test_r2_awaiter_cancelled_then_late_failure_is_retrieved, test_r4_the_twin_and_its_attach_point | True |
| D-M4 | app/services/llm_spend_breaker.py | the callback logs a WARNING | KILLED | test_r3_record_soon_late_eval_failure | True |
| D-M5 | app/services/llm_spend_breaker.py | attach on both branches (EQUIVALENT behaviourally by R-G10-10) | KILLED | test_r4_the_twin_and_its_attach_point, test_p4_plain_path_unchanged | True |
| J-M1 | scripts/cron_compare_judge.py | revert to the array literal | KILLED | test_r1_resume_operand_is_json, test_r2_resume_raw_query, test_r3_dry_end_to_end_provider_absent, test_r4_dry_end_to_end_batch_ended, test_r5_apply_end_to_end_batch_ended, test_r6_apply_batch_lost | True |
| J-M2 | scripts/cron_compare_judge.py | the wrong flag | KILLED | test_r1_resume_operand_is_json, test_r2_resume_raw_query, test_r3_dry_end_to_end_provider_absent, test_r4_dry_end_to_end_batch_ended, test_r5_apply_end_to_end_batch_ended, test_r6_apply_batch_lost | True |
| J-M3 | scripts/cron_compare_judge.py | the filter form with the literal | KILLED | test_r1_resume_operand_is_json, test_r2_resume_raw_query, test_r3_dry_end_to_end_provider_absent | True |
| J-M4 | scripts/cron_compare_judge.py | drop judge=eq.haiku | KILLED | test_r1_resume_operand_is_json, test_p2_other_requests_unchanged[companions-on], test_p2_other_requests_unchanged[companions-off] | True |
| J-M5 | tests/test_s81_s22_judge.py | EJ1 reverted (the fake iterates characters) | KILLED | test_j14c_resume_first[ended], test_j14c_resume_first[running], test_j14c_resume_first[lost], test_jf1_3a_resume_maps_by_hashed_id, test_g22_gr4_dry_resume_writes_nothing | True |
| J-M6 | scripts/cron_compare_judge.py | compact separators (EQUIVALENT by R-G10-10) | SURVIVED | - | True |

Verdict: every non-equivalent mutant KILLED by an AssertionError. J-M6 SURVIVED (EQUIVALENT by R-G10-10). D-M5: behaviourally EQUIVALENT by R-G10-10, here KILLED structurally (R4's AST `if durable` clause and P4's wrapped-future callback snapshot). C-M8 AS STATED ("the stamp outside `if kb_marks:`") SURVIVED: behaviourally EQUIVALENT (with ENABLE_KB_FIRST_SERVE OFF nothing sets `_kb_views`, so the any() guard writes no key; `_kb_views` and `_kb_hit_marks` are assigned together at scs :4528-4532 / :5249-5253, so whenever views exist the marks are truthy): RULING OWED (Q1); C-M8b (outside the gate AND without the any() guard) KILLED by P1 (12 nodes). Mutants re-run on the final bytes after the digest re-encoding: see mutation_results_*.json (latest per id shown above).

## 7. The corpus gate at the prototype HEAD (alone; the eight-flag list)
scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_SELF_CRITIQUE,ENABLE_KB_FIRST_SERVE,ENABLE_COMPARE_RUN_LEDGER,ENABLE_BATCH_JUDGE,ENABLE_LLM_SPEND_BREAKER,ENABLE_SCRAPEDO_SUPER,ENABLE_KB_BRANDS,ENABLE_KB_COVERAGE_ROLLUP, the pinned venv, ALONE (no pytest live; only the two stall_monitor.py processes), cwd = the prototype HEAD (all four units + every E-row), 2026-11-09 18:12:48 - 18:20:15 (local time):
    RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656
    OVERALL SHA256 387fa35c600f6ea9f049d38a84966f435b9827ed2ed636c0144b7b56f1d09181
  = EQUAL to the spec base value 387fa35c... (rc 0; output corpus_proto.txt / corpus_proto.json). Not re-run at base (the HEAD value matched; the brief: re-run at base only if it differs).

## 8. Every [pyt] line of this round (from harness/pyt_ledger.jsonl, tags g10red-*)
```
[pyt] tag=g10red-j1-base start=2026-11-09 17:46:51 end=2026-11-09 17:46:58 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=g10red-04d-base start=2026-11-09 17:49:31 end=2026-11-09 17:49:40 elapsed=9s bound=600s status=FAIL rc=1
[pyt] tag=g10red-22c-base start=2026-11-09 17:52:29 end=2026-11-09 17:52:34 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-22c-base2 start=2026-11-09 17:53:11 end=2026-11-09 17:53:15 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-22b-record start=2026-11-09 17:55:51 end=2026-11-09 17:55:54 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=g10red-22b-base start=2026-11-09 17:56:04 end=2026-11-09 17:56:09 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-proto-red start=2026-11-09 18:00:18 end=2026-11-09 18:00:32 elapsed=14s bound=600s status=OK rc=0
[pyt] tag=g10red-proto-A start=2026-11-09 18:00:49 end=2026-11-09 18:01:37 elapsed=47s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-proto-B start=2026-11-09 18:01:56 end=2026-11-09 18:03:22 elapsed=86s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-proto-B2 start=2026-11-09 18:04:00 end=2026-11-09 18:04:09 elapsed=10s bound=600s status=OK rc=0
[pyt] tag=g10red-proto-C start=2026-11-09 18:04:23 end=2026-11-09 18:05:52 elapsed=89s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M1 start=2026-11-09 18:07:30 end=2026-11-09 18:07:35 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M2 start=2026-11-09 18:07:35 end=2026-11-09 18:07:39 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M3 start=2026-11-09 18:07:39 end=2026-11-09 18:07:44 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M4 start=2026-11-09 18:07:44 end=2026-11-09 18:07:48 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M5 start=2026-11-09 18:07:48 end=2026-11-09 18:07:54 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M6 start=2026-11-09 18:07:54 end=2026-11-09 18:07:59 elapsed=6s bound=600s status=OK rc=0
[pyt] tag=g10red-mut-D-M1 start=2026-11-09 18:07:59 end=2026-11-09 18:08:06 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-D-M2 start=2026-11-09 18:08:06 end=2026-11-09 18:08:10 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-D-M3 start=2026-11-09 18:08:11 end=2026-11-09 18:08:16 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-D-M4 start=2026-11-09 18:08:16 end=2026-11-09 18:08:21 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-D-M5 start=2026-11-09 18:08:21 end=2026-11-09 18:08:30 elapsed=9s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-C-M1 start=2026-11-09 18:08:30 end=2026-11-09 18:08:35 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-C-M2 start=2026-11-09 18:08:35 end=2026-11-09 18:08:40 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-C-M3 start=2026-11-09 18:08:40 end=2026-11-09 18:08:45 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-C-M4 start=2026-11-09 18:08:45 end=2026-11-09 18:08:50 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-C-M5 start=2026-11-09 18:08:50 end=2026-11-09 18:08:55 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-C-M6 start=2026-11-09 18:08:55 end=2026-11-09 18:09:01 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-C-M7 start=2026-11-09 18:09:01 end=2026-11-09 18:09:06 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-C-M8 start=2026-11-09 18:09:06 end=2026-11-09 18:09:10 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=g10red-mut-C-M8b start=2026-11-09 18:09:10 end=2026-11-09 18:09:16 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M1 start=2026-11-09 18:09:16 end=2026-11-09 18:09:20 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M2 start=2026-11-09 18:09:20 end=2026-11-09 18:09:24 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M3 start=2026-11-09 18:09:24 end=2026-11-09 18:09:29 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M4 start=2026-11-09 18:09:29 end=2026-11-09 18:09:33 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M5 start=2026-11-09 18:09:33 end=2026-11-09 18:09:37 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M6 start=2026-11-09 18:09:37 end=2026-11-09 18:09:42 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M7 start=2026-11-09 18:09:42 end=2026-11-09 18:09:46 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M8 start=2026-11-09 18:09:46 end=2026-11-09 18:09:50 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M9 start=2026-11-09 18:09:50 end=2026-11-09 18:09:54 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M10 start=2026-11-09 18:09:54 end=2026-11-09 18:09:59 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-j1-base2 start=2026-11-09 18:22:26 end=2026-11-09 18:22:32 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=g10red-22b-base2 start=2026-11-09 18:22:32 end=2026-11-09 18:22:36 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-proto-red2 start=2026-11-09 18:22:49 end=2026-11-09 18:23:02 elapsed=13s bound=600s status=OK rc=0
[pyt] tag=g10red-mut-J-M1 start=2026-11-09 18:23:03 end=2026-11-09 18:23:07 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M2 start=2026-11-09 18:23:07 end=2026-11-09 18:23:11 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M3 start=2026-11-09 18:23:11 end=2026-11-09 18:23:15 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M4 start=2026-11-09 18:23:15 end=2026-11-09 18:23:19 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M5 start=2026-11-09 18:23:19 end=2026-11-09 18:23:24 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-J-M6 start=2026-11-09 18:23:25 end=2026-11-09 18:23:30 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=g10red-mut-B-M1 start=2026-11-09 18:23:30 end=2026-11-09 18:23:34 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M2 start=2026-11-09 18:23:34 end=2026-11-09 18:23:39 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M3 start=2026-11-09 18:23:39 end=2026-11-09 18:23:43 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M4 start=2026-11-09 18:23:43 end=2026-11-09 18:23:47 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M5 start=2026-11-09 18:23:47 end=2026-11-09 18:23:52 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M6 start=2026-11-09 18:23:52 end=2026-11-09 18:23:56 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M7 start=2026-11-09 18:23:56 end=2026-11-09 18:24:00 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M8 start=2026-11-09 18:24:00 end=2026-11-09 18:24:04 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M9 start=2026-11-09 18:24:04 end=2026-11-09 18:24:08 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-mut-B-M10 start=2026-11-09 18:24:08 end=2026-11-09 18:24:12 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=g10red-ciorder-base start=2026-11-09 18:24:42 end=2026-11-09 18:26:13 elapsed=91s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-secretscan-base start=2026-11-09 18:26:31 end=2026-11-09 18:26:36 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=g10red-base-c01 start=2026-11-09 18:26:43 end=2026-11-09 18:27:22 elapsed=39s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-base-c02 start=2026-11-09 18:27:22 end=2026-11-09 18:28:01 elapsed=40s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c03 start=2026-11-09 18:28:01 end=2026-11-09 18:28:55 elapsed=54s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c04 start=2026-11-09 18:28:55 end=2026-11-09 18:29:29 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c05 start=2026-11-09 18:29:30 end=2026-11-09 18:30:53 elapsed=84s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c06 start=2026-11-09 18:30:53 end=2026-11-09 18:31:12 elapsed=19s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c07 start=2026-11-09 18:31:12 end=2026-11-09 18:31:38 elapsed=26s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c08 start=2026-11-09 18:31:39 end=2026-11-09 18:32:24 elapsed=46s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-base-c09 start=2026-11-09 18:32:24 end=2026-11-09 18:34:03 elapsed=99s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-base-c10 start=2026-11-09 18:34:03 end=2026-11-09 18:36:27 elapsed=144s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c11 start=2026-11-09 18:36:27 end=2026-11-09 18:37:19 elapsed=51s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-base-c12 start=2026-11-09 18:37:19 end=2026-11-09 18:38:47 elapsed=88s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-base-c13 start=2026-11-09 18:38:47 end=2026-11-09 18:40:00 elapsed=73s bound=1200s status=FAIL rc=1
[pyt] tag=g10red-base-c14 start=2026-11-09 18:40:00 end=2026-11-09 18:40:46 elapsed=46s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c15 start=2026-11-09 18:40:46 end=2026-11-09 18:41:38 elapsed=52s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c16 start=2026-11-09 18:41:38 end=2026-11-09 18:42:24 elapsed=46s bound=1200s status=OK rc=0
[pyt] tag=g10red-base-c17 start=2026-11-09 18:42:24 end=2026-11-09 18:42:34 elapsed=10s bound=1200s status=OK rc=0
```
The [netguard] lines: base RED files 0 blocked; proto A 24 from 2 nodes (test_s81_s04 r42 / p08: neutralized supabase.invalid, as at base); proto B 189 from 31 nodes (test_streaming api.openai.com egress + the openai_breaker preflight rows: neutralized; all passed); proto C neutralized supabase.invalid (s20 / s04 rows). [hermeticity] sentinel lines in each log.

## 9. The comm set and the base record
- Re-derivation: the spec's comm.py (S81-G10/comm.py) re-run read-only on the real worktree (the four RED files excluded) reproduces 726 members, set sha256 f963d6dc3e690e244bf1a54242ba4a34514f33cd6682f2054ff8ea7c9293d8de (comm_a.py). The FIXPOINT in BOTH directions (comm_b.py: every test importing a member test module, directly or through a tests helper; every tests module a member imports, transitively through helpers): 0 additions (one round). The AST importer forms (`from app.services import <module>`, `import app.services.x as y`, the string-constant importlib form) are the spec's; a separate string-target sweep of every non-member (a constant naming a closure module or an app/ / scripts/ path) found 0.
- ONE ADDITION by measurement: tests/test_subtype_spec_reconciliation.py imports app.services.extraction_service (a closure member) but starts with a UTF-8 BOM, so the spec's `ast.parse(read_text("utf-8"))` failed and read it as empty (the only BOM / unparseable .py in app/ scripts/ tests/, measured; the closure itself is unaffected).
- The set of record: BASE 727 members (the 726 + the addition; the two suites deleted at HEAD included; the RED files absent) sha256 1f35353bd1e00e9986c97831e91adda916b4302a9363239309665bb85fb23428 (COMM_SET.txt); HEAD 729 = BASE - tests/test_self_critique_orchestration.py - tests/test_verdict_critique_service.py + the four RED files, sha256 3fa62c6b54f9d04bcbe3cbc6dfc5ba2df4b6f8a5273f3d0c84e63e0d6f882bdb (COMM_SET_HEAD.txt). comm_reasons.tsv: one reason per member (the spec's reasons + the addition's). The four test_precommit_hook*.py excluded; no .githooks change.
- The RED files import tests.test_s81_s18_kb_first_serve (22b, 22c) and tests.test_s81_s22_compare_runs (22c, which imports tests.test_s81_s20_result_gate and tests.test_migration_043_delete_user_cascade): all members of the set.
- The base-record plan (comm_plan.py -> base_plan.tsv): REUSE 323 (310 from f4461556/e18102fb..., 13 from 39ac80ba) and RUN 404 (17 chunks of <= 25). Stricter than the spec's 330 / 396: the reuse rule is applied TRANSITIVELY through the tests modules a member imports (8 members moved REUSE -> RUN: test_exemplar_injection_content, test_migration_041_user_events_public_select_policy, test_price_fallback_may_decline, test_prompt_caching, test_prompt_truth, test_retro_w1_2c, test_scoring_rubric_truth, test_w4_13_flag_off_ledger); the addition is a REUSE (f4461556, unchanged, no exclusion). The reused members' FAILED ids copied from the stored records: 2 (tests/test_personalization_bundle_c.py x2).
- Stored: harness/base_records/90d4ed74bdd16f62130dc9f7a4727620f8a1cea2/1f35353bd1e00e9986c97831e91adda916b4302a9363239309665bb85fb23428.{txt,files,header.txt,pyt.log} (the stored records' form; the header names the reused and the run members).
- Header lines 1-5:
    # base record 90d4ed74bdd16f62130dc9f7a4727620f8a1cea2, set sha256 1f35353bd1e00e9986c97831e91adda916b4302a9363239309665bb85fb23428 (727 files = the S81-G10 comm set of record at base: the spec's 726 (f963d6dc...) re-derived to a fixpoint in both directions by the RED agent + 1 addition (tests/test_subtype_spec_reconciliation.py: imports app.services.extraction_service; the spec's derivation read 
    # built 2026-11-09 15:42 UTC by the S81-G10 RED agent (Opus 5.5) per R-G10-12 / the 2026-11-07 16:44 MOVING MAIN line (GC-9 per-file reuse, LC-6), strengthened: reused only when neither the member nor any tests module it imports transitively names a 90d4ed74/f4461556-touched module, CLAUDE.md, a docs/policies file, an S81-24 module (for a 39ac80ba reuse), app.main / TestClient or walks a glob / di
    # REUSED per file: 323 members (310 from f4461556/e18102fb..., 13 from 39ac80ba/fe55771e... + 99bacbe8...); their FAILED ids copied from the stored .txt files: 2
    # RUN at 90d4ed74 in the REAL worktree sc-s81-g10 (detached at 90d4ed74; the five RED-round files in no chunk): 404 members in 17 chunks of <= 25 (bound 1200); plan with reasons: S81-G10_red/base_plan.tsv
    # FAILED node ids: 27 (reused 2 + run 25)
- The FAILED node-id set (27, sorted):
    tests/test_auth_interceptor.py::test_sign_in_with_social_exception
    tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
    tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
    tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
    tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
    tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
    tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
    tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
    tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
    tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
    tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
    tests/test_s81_s18b_store_label.py::test_r2_table_shape
    tests/test_s81_s19_gap_queue.py::test_r15_hygiene
    tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
    tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
    tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene
    tests/test_s81_s24_auth_throttle.py::test_r92_hygiene
- The chunk [pyt] lines:
    [pyt] tag=g10red-base-c01 start=2026-11-09 18:26:43 end=2026-11-09 18:27:22 elapsed=39s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c01.log
    [pyt] tag=g10red-base-c02 start=2026-11-09 18:27:22 end=2026-11-09 18:28:01 elapsed=40s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c02.log
    [pyt] tag=g10red-base-c03 start=2026-11-09 18:28:01 end=2026-11-09 18:28:55 elapsed=54s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c03.log
    [pyt] tag=g10red-base-c04 start=2026-11-09 18:28:55 end=2026-11-09 18:29:29 elapsed=34s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c04.log
    [pyt] tag=g10red-base-c05 start=2026-11-09 18:29:30 end=2026-11-09 18:30:53 elapsed=84s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c05.log
    [pyt] tag=g10red-base-c06 start=2026-11-09 18:30:53 end=2026-11-09 18:31:12 elapsed=19s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c06.log
    [pyt] tag=g10red-base-c07 start=2026-11-09 18:31:12 end=2026-11-09 18:31:38 elapsed=26s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c07.log
    [pyt] tag=g10red-base-c08 start=2026-11-09 18:31:39 end=2026-11-09 18:32:24 elapsed=46s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c08.log
    [pyt] tag=g10red-base-c09 start=2026-11-09 18:32:24 end=2026-11-09 18:34:03 elapsed=99s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c09.log
    [pyt] tag=g10red-base-c10 start=2026-11-09 18:34:03 end=2026-11-09 18:36:27 elapsed=144s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c10.log
    [pyt] tag=g10red-base-c11 start=2026-11-09 18:36:27 end=2026-11-09 18:37:19 elapsed=51s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c11.log
    [pyt] tag=g10red-base-c12 start=2026-11-09 18:37:19 end=2026-11-09 18:38:47 elapsed=88s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c12.log
    [pyt] tag=g10red-base-c13 start=2026-11-09 18:38:47 end=2026-11-09 18:40:00 elapsed=73s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c13.log
    [pyt] tag=g10red-base-c14 start=2026-11-09 18:40:00 end=2026-11-09 18:40:46 elapsed=46s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c14.log
    [pyt] tag=g10red-base-c15 start=2026-11-09 18:40:46 end=2026-11-09 18:41:38 elapsed=52s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c15.log
    [pyt] tag=g10red-base-c16 start=2026-11-09 18:41:38 end=2026-11-09 18:42:24 elapsed=46s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c16.log
    [pyt] tag=g10red-base-c17 start=2026-11-09 18:42:24 end=2026-11-09 18:42:34 elapsed=10s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\07cedb96-2752-480a-aa62-62e55837e125\scratchpad\S81-G10_red\base_logs\c17.log
- TIMEOUT re-runs / NOT MEASURED: none
- The 27 ids are IDENTICAL to the stored f4461556/e18102fb... FAILED set (diff empty): the CRLF working-copy hygiene rows (s16 r27 x5, s18b r2, s19 r15, s22 b02 / j01, s24 p83 / r92, d16 r10, d17 r9), the cold-tiktoken test_prompt_truth ERRORs x2, s10 r06, the d22c p1 golden x5, test_auth_interceptor x2, test_page_scraping x2, test_personalization_bundle_c x2 (reused); no new base failure at 90d4ed74.

## 10. Once at base: the CI-order set of spec 12.3 and the secret scan
- CI-order set of spec 12.3 at base (ONE call, bound 1200, flags unset, the real worktree with the five files present; the 33 files in CI's alphabetical order, tests/test_health_loop_lag.py (a lifespan user) ahead of every RED file, tests/test_s81_s20_result_gate.py also ahead of the s22 RED files): 30 failed / 2095 passed; [hermeticity] sentinel checked 2125 test(s); [netguard] blocked 189 attempt(s) from 18 node(s) (neutralized; as in the prototype set B).
  [pyt] tag=g10red-ciorder-base start=2026-11-09 18:24:42 end=2026-11-09 18:26:13 elapsed=91s bound=1200s status=FAIL rc=1
  The 30 = the 27 RED nodes BY DESIGN (s04d r1-r4; s22b r1-r9b; s22c r1-r7; s22j1 r1-r6) + the 3 CRLF-environment nodes of the stored base records (tests/test_s81_s18b_store_label.py::test_r2_table_shape, tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf, tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first). Every PIN row green in CI order (no P73-class order dependency: the 22c / 22b / 04d / j1 PIN rows ran after the lifespan users).
- tests/test_secret_scan_static.py ALONE at base (the real worktree with the five files present): 31 passed; [hermeticity] sentinel checked 31 test(s); [netguard] blocked 0 attempt(s) from 0 node(s).
  [pyt] tag=g10red-secretscan-base start=2026-11-09 18:26:31 end=2026-11-09 18:26:36 elapsed=5s bound=600s status=OK rc=0
- NOT RUN by this round (as briefed): the fourteen backend-scanning client fences + b3a / nativeStrings (GREEN's, through the orchestrator's junction); the four tests/test_precommit_hook*.py (no .githooks change).

## 11. Restore check
- Real worktree sc-s81-g10: HEAD 90d4ed74bdd16f62130dc9f7a4727620f8a1cea2; `git diff --quiet` rc=0 (no tracked file differs from the index/base); `git status --short`:
    ?? tests/fixtures/s81_s22b_flag_off_golden.json
    ?? tests/test_s81_s04d_durable_retrieve.py
    ?? tests/test_s81_s22b_self_critique_retire.py
    ?? tests/test_s81_s22c_kb_product_ids.py
    ?? tests/test_s81_s22j1_judge_jsonb_filter.py
- No .qa-mutation.lock in the real worktree (absent); every mutation ran in the scratch worktree, each restore sha256-verified (mut.py).
- Scratch worktree <scratchpad>/S81-G10_red/proto removed with `git worktree remove --force` (no junction was ever created there); `git worktree list` lines naming S81-G10_red: 0.
- No orphan pytest: the live python.exe processes are the two stall_monitor.py processes (the orchestrator harness), none of this agent.
- Real worktree base sha re-verified: HEAD 90d4ed74 before (14:38Z) and after (15:43Z); only the five new files untracked.

## 12. Deviations from the spec (each measured)
- D1 (22c P1): with ENABLE_RESULT_AGGREGATES / ENABLE_STORE_LABEL ON the payloads do NOT equal the S81-18 golden at base (the three scenarios move: the G8 flags stamp their own additive keys); P1 is split: companions OFF -> the S81-18 golden; companions ON -> every OFF spelling equals the unset spelling under the same configuration; both: no kb_product_ids anywhere, no KB entry point (raising recorders).
- D2 (22c R7 / P5): two hops: the S81-18 orchestrator driver produces the real full/miss (full/full) body, the S81-22 route harness injects it into text POST (`_route_world` + `Rec`); not one TestClient run through the real orchestrator.
- D3 (22b R7): "every other row equal a base literal" is pinned as the R22 identity fields (id, kind, module, hosts, gate_flag, personal_data) of every other row + every openai field; the other rows' text fields are not pinned, so the held S81-12 branch's processors.json hunks (`_comment`, the anthropic `public_name`) cannot collide with this file.
- D4 (22b P1 / R9b): the golden also carries the routed site keys, the follow-ups and the compare_runs row (build_run_row over the REST body = the "insert recorder" at the orchestrator level; stage_timings dropped); R9b also compares those under ENABLE_SELF_CRITIQUE=true.
- D5: the spec agent's proto_apply.py omitted the D-S22-K1 widening; the spec agent's proto_22b.py omitted the llm_router docstring clause and the cron_learning comment (R2 stays red without them, measured); this prototype applied all three.
- D6: two E-rows the spec's table lacks: EB11b (the u3c spreads floor 33 -> 31) and EB12b (the echo test's call-time payload snapshot), both measured red on the prototype without them.
- D7: the comm set gains one member (the BOM file); the base-record reuse rule applied transitively (8 members moved to RUN).
- D8: C-M8 as stated is an equivalent mutant (Q1); C-M8b added and killed. D-M5 killed structurally (Q3).
- D9: the 22b digests are base64 of the raw sha256 (the S81-22 BASE_BLOBS precedent) and the synthetic uuids are built at run time: the added-line sweep's 8-digit-run rule (a hex digest held "22232503" / "26413009").
- D10 (04d P2): the controlled pool future is cancelled after the awaiter's bound (it never runs); the cancel-before-bound variant propagates CancelledError to the awaiter by shield design and is not a PIN.

## 13. Open questions for the gate
- Q1: rule C-M8 (the stamp outside `if kb_marks:` keeping the any() guard) EQUIVALENT, or require a row that sets `_kb_views` without marks (an unreachable state)? Recommended: equivalent, stated limit.
- Q2: EJ2's new hex value contains an 8-digit run ("93232491"); the existing S22_LF_SHA entries already contain digit runs (committed through the hook), so the added-line sweep's treatment of a hex sha in that table needs the orchestrator's eye; GREEN recomputes the value for its exact EJ1 bytes.
- Q3: record D-M5 as KILLED (structural rows R4 / P4) or keep R-G10-10's EQUIVALENT label with the structural kill noted?
- Q4: EB7 keeps ENABLE_SELF_CRITIQUE in test_s70's delenv list (inert, harmless); EB1 removed it from the w414 list; GREEN may harmonise.
