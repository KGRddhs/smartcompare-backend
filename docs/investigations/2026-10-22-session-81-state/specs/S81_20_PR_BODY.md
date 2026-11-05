## S81-20 B2-RESULT-GATE-V2 (ENABLE_RESULT_GATE, default OFF) - refuse unsupported verdicts as non-deliveries
Base `229b61e9349a3dbf54332b53cdd6f923b86093ec` (origin/main after #389); HEAD `3bfb02d5d2970d739f1e02cfabc4dc87502d752b` (branch `feature/s81-s20-result-gate-v2`, 2 commits: the GREEN commit replayed as `ba0ba38f` + the final-round commit). FOCUS unit (the quota path): GREEN + two adversaries (correctness; quotaandbilling). Every flag OFF in production: nothing changes on merge.

### What the flag does
`ENABLE_RESULT_GATE` (new name, default OFF, read per call with the house idiom; no knob). Reader `app/services/result_gate.py::result_gate_enabled`, plus the local one-liner `app/middleware/error_handler.py::_result_gate_keys_enabled`. Read as the FIRST statement of `result_gate_refusal`, as the ONE camera read `_rg_on` (before the size enrichment), and as the first operand of the builder stamp, of the `_surface_comparison_failure` reason arm and of the error handler's fourth passthrough block.

With the flag ON, a comparison that B1's `assess_result` does not support (the gate computes it itself with the stamped categories) is not delivered:
- **Text POST / GET** (`_result_gate_exit`, after the failure branch) and **URL** (after the failure block): HTTP 400 `INSUFFICIENT_DATA` (the H6 sentence) + a top-level `reason` in {placeholder_identity, same_identity, category_conflict, no_evidence}.
- **Stream**: the FIRST terminal decides; both terminal frames carry the refusal (H6 keys, `reason` last). The W3-2 persist gains `and _s20_refusal is None`. A NEW first `finally` branch (the old `if` becomes `elif`, text unchanged) schedules ONE fire-and-forget coroutine `_s20_stream_settle` (label `usage_refund.text_stream.result_gate`). The finally awaits nothing (GC-7).
- **Camera**: after the S81-10 pair gate (CATEGORY_NOT_LIVE wins) and before the paid compare. The body is `{success: false, action: "error", error: CAMERA_GATE_MESSAGE, vision_cost, reason}`, reason in {placeholder_identity (the pre-enrichment identity), low_confidence (ANY low on a V2 `_is_product`), same_identity (features ignored, size veto kept), category_conflict (ONLY from two V2 `_category` values, R-S20-39)}. The call goes through the module attribute `_rg` (R-S20-30).
- **URL reading**: placeholder, then same identity, then the JSON-LD aware evidence count. Strings must be ASCII-only (`re.ASCII`, R-S20-36). A price counts when > 0 and not estimated / unavailable; a rating counts in (0, 5]. No category check.

**The five exits and the accounting (R-A3).** The five exits are text POST, text GET, stream, URL and camera. Each refunds with the consume's `consumed_keys` (POST / GET / stream capture them at the consume site; URL uses the additive `keys_out` of `_reserve_comparison_credit`; camera uses `_refund_reserved_credit(label, consumed_keys=None)`, whose keyless form is byte-equal to base) plus the anon camera credit, BEFORE the raise. No exit calls `record_lifetime_comparison` / `record_comparison` or writes history. Each writes ONE `result_gate:<reason>` row in both W4-13 states and ONE INFO `[RESULT_GATE] refused input=%s reason=%s` with constants only.

**The budget interplay (R-S20-38, GC-6, GC-7).** With `ENABLE_FRAGRANCE_ONLY_GATE` ON (not admin), the exit reads `budget_state_async(subject)`:
- spent: the credit is KEPT, with no refund and no `record_refusal_async`;
- not spent: the keyed refund, then ONE `record_refusal_async`;
- gate OFF: refund and no count.

Text / URL / camera await this inline. The stream does read -> refund or keep -> record -> row inside the settle coroutine. A stream client gone before the refusal terminal takes the base incomplete arm (keyless, T5 row; L21).

**The builder.** It stamps `metadata.product_categories` (setdefault, additive) under this flag too (R-S20-41).

**G3 tail fact (R-S20-23, R33/R34).** A refused no_evidence fragrance pair has already passed the G3 ingest tail inside the orchestrator: cards at identity high, gaps at medium. Placeholder / same / conflict pairs queue nothing. A hard-cap partial refused no_evidence never reaches the tail (L17). No KB write in this unit.

### RED rows -> flag -> flip preconditions
`tests/test_s81_s20_result_gate.py` (frozen; LF sha256 `13aa83ad...0c180c`, blob `6eebb584`, byte-identical after the rebase) has 166 nodes: 122 RED at base (AssertionError only) and 44 PIN. All 166 are green at HEAD with the flag unset and with `ENABLE_RESULT_GATE=true` exported. MYEZ ids: MYEZ-001 (category-conflict half), MYEZ-002, MYEZ-003, MYEZ-012 (text / stream / URL), MYEZ-004 (camera, R-S20-4), MYEZ-007 (refusal half), MYEZ-011, MYEZ-027. All map to `ENABLE_RESULT_GATE`. Per-row evidence: specs/S81_20_RED_REPORT.md.

Flip preconditions (names only):
- App Store approval of build 3.
- B1's canary window: `ENABLE_RESULT_STATUS_METADATA` ON and the `comparison_result_status` distribution read.
- The D17 pair hit rate from `kb_coverage_daily`, after 045 and the kb-coverage service.
- The camera low-confidence share read.
- The R-A2 order: after the S81-11 OTA, with `ENABLE_FRAGRANCE_ONLY_GATE` flipped FIRST.
- The owner's yes.

### Gate rows (GREEN-owned + this round, `tests/test_s81_s20_gate_rows.py`, 13 nodes; LF sha256 `c7f532c54b2b582fd44ec760bf8e16b61d7be767c99d6b0e8e21b902145512ef`)
- G20-GR1: spent budget -> no refund AND no record (text POST / GET / stream / URL / camera).
- G20-GR2: no Await in the stream finally (base: none); the single settle label; the settle sequence (open / spent / gate OFF).
- G20-GR3: client gone before the refusal terminal -> keyless incomplete refund, no exit budget read, no record, the T5 row.
- G20-GR4 (NEW, RB-S20-3, kills the correctness adversary's A8): the stream refusal's ONE `search_logs` row carries `input_type` `text_stream` and is the task scheduled under the settle label `usage_refund.text_stream.result_gate`. Proven RED-then-green: A8 (`input_type="text_stream"` -> `"text"` in `_s20_stream_settle`) applied to a sha-verified byte copy of `app/api/text_routes.py` under `.qa-mutation.lock`: [pyt] tag=s20f-mut-a8 status=FAIL rc=1 (1 failed, 12 deselected, 11 warnings) (AssertionError, KILLED); restored, sha256 `8e40919d...190fc` equal before and after.
GR1-GR3 were proven by 8 inverse edits at GREEN, all KILLED (specs/S81_20_GREEN_GR_MUTATION_TABLE.md).

### Deliberate pin changes - one-name additions of `ENABLE_RESULT_GATE` to env-clean lists
| # | File | List |
|---|---|---|
| E1 | tests/test_s75_fanout_identity.py | UNIT_ENV |
| E2 | tests/test_retro_w2_1.py | _clean_flags |
| E3 | tests/test_s71_u13_compare_auth_required.py | CLEAN_ENV |
| E4 | tests/test_paid_route_metering.py | _CLEAN_ENV |
| E5 | tests/test_w4_13_measurement_truth.py | _clean_flags |
| E6 | tests/test_s80_b1.py | CLEAR |
| E7 | tests/test_s80_b3_vision_identity_v2.py | UNIT_ENV |
| E8 | tests/test_s81_kb_schema.py:475 | IDENTITY_NODES digest re-pin (E1 moved the FY25 file's LF sha; the RB6-11 class, RB-S20-2) |
| E9 | tests/test_s81_s09_device_quota.py | CLEAN_ENV |
| E10 | tests/test_s81_s10_fragrance_gate.py | _CLEAR_ENV |
| E11 | tests/test_s81_s10_gate_rows.py | no own list: it imports E10's autouse fixture `_s10_clean`, so E10 cleans it (no byte change; deviation D-F1) |
| E12 | tests/test_s81_s18_kb_first_serve.py | CLEARED_ENV |
| E13 | tests/test_s81_s09_gate_rows.py | no own list: it imports E9's autouse fixture, so E9 cleans it (no byte change; deviation D-F1) |
| E14 | tests/test_s81_s17_kb_ingest.py | CLEARED_ENV |
E9-E14 close the correctness adversary's MJ1 (RB-S20-1): the six files run green with the flag unset ([pyt] tag=s20f-e9e14-off status=FAIL rc=1 (1 failed, 504 passed, 11 warnings)) and exported ([pyt] tag=s20f-e9e14-on status=FAIL rc=1 (1 failed, 504 passed, 11 warnings)); in both runs the one failure is the environmental CRLF node test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (in the base record). Those six files held 46 of the GREEN sweep's 135 flag-exported reds; the other 13 files (89 nodes) have no clean list and stay named in L12 / L24.
E1-E8 re-proven exported: [pyt] tag=s20f-erows-on status=OK rc=0 (1331 passed, 10 warnings).

### Counts and gates (this round, at HEAD `3bfb02d5`)
- RED file + gate rows: 179 / 179 (166 + 13) flag unset ([pyt] tag=s20f-unit-off status=OK rc=0 (179 passed, 13 warnings)) and exported ([pyt] tag=s20f-unit-on status=OK rc=0 (179 passed, 13 warnings)).
- Mutants: RED round 42 KILLED (M1-M42 incl. M32b, M37a-c) + EQ1 / EQ2 equivalent by ruling; GR inverse edits 8 KILLED; this round A8 KILLED by G20-GR4. Correctness lens: 31 applied, A8 now killed, A3 equivalent (L27), A11 near-equivalent (L28). Quota lens: 7 applied, all killed.
- tests/test_paid_route_metering.py: flag unset [pyt] tag=s20f-meter-off status=OK rc=0 (21 passed, 13 warnings); exported [pyt] tag=s20f-meter-on status=OK rc=0 (21 passed, 13 warnings). The R8 pair (test_sentry_channels_u8d_unit.py + test_sentry_channels_u8d.py) alone: [pyt] tag=s20f-r8 status=OK rc=0 (273 passed, 1 warning).
- CI-order set (57 files: the GREEN's 56 + tests/test_s81_s09_gate_rows.py), flag unset: [pyt] tag=s20f-ci-order status=FAIL rc=1 (1 failed, 4635 passed, 1 deselected, 63 warnings); the one failure is the r06 CRLF node, identical to GREEN.
- Comm set: 392 files (the GREEN 390 + tests/test_migration_index_predicate_immutability.py + tests/test_openai_key_log_hygiene_s69.py) at HEAD, flag unset, 16 chunks of at most 25 (s20f-comm-00..15, bound 1200, all finished, no TIMEOUT; 17,764 passed) + tests/test_secret_scan_static.py alone (s20f-comm-secretscan OK, 31 passed). HEAD FAILED = 17 = the base record exactly (environmental: test_auth_interceptor x2, test_page_scraping x2, test_personalization_bundle_c x2, test_prompt_truth x2 (cold tiktoken, identical both sides), test_s81_d16 r10, test_s81_d17 r9, the r06 CRLF node, test_s81_s16_kb_seed r27 x5, test_s81_s19 r15). Base record at 229b61e9 = base_records/229b61e9.../dd959a10...txt (390 files = the 392 minus the two unit files absent at base): 302 REUSED per file (GC-9) from the stored 6869a3e6 record 97218ca8... (#389 changed only SmartCompareApp/ files + CLAUDE.md), 88 RUN at 229b61e9 in a removed detached junction-free scratch worktree (every CLAUDE.md / SmartCompareApp referencing file incl. the six CLAUDE.md readers by the import graph, every glob walker, the two added pins; s20f-base-00..03 + secretscan: 7,816 passed, 5 failed = the s16 r27 nodes). comm -13 (branch-only NEW) EMPTY; comm -23 EMPTY.
- Corpus gate NOT repeated (no app file changed since the GREEN: every app blob byte-equal to 404b4ba5; GREEN's base / HEAD OVERALL cedae008...3f48 equal, deviation D6).
- Fourteen backend-scanning client fences by path through the junction (jest 29.7.0, node v24.11.1): [jest] tag=s20f-fences rc=1: 13 / 14 suites, 236 / 240 tests; the 4 = config/nativeBundle.w37 d5 / k2 / k4 / k5 (the accepted drift nodes).
- FULL jest ONCE (LC-7), --json, figures from full.json: [jest] tag=s20f-full rc=1: numPassedTests 3976, numFailedTests 4 (the four nativeBundle.w37 drift nodes), numPendingTests 13, numTodoTests 13, of 4006; suites 406 passed / 1 failed of 410; snapshots 41 matched, 0 added / updated / unmatched / removed. Equal to the post-#389 baseline (3,976 + the four w37 nodes).
- ruff E9/F63/F7/F82 + py_compile clean on the six app files and every touched test file. The six app files keep CRLF (hunks only). No 64-hex literal beside a keyword-named constant (E8 re-pins the IDENTITY_NODES digest; the frozen RED file's AUTHREQ / ENVELOPE_KEYS names carry no digest). Pure ASCII except the required attribution line.
- Hook test files (tests/test_precommit_hook*.py) NOT run: the unit touches no .githooks file and the round args rule them out ("the hook test files NOT run (no .githooks change)"); the round commit passed the pre-commit hook.
Gate logs and per-row evidence: specs/S81_20_REBASE_REPORT.md (this round), specs/S81_20_GREEN_GATE_LOGS.md, specs/S81_20_RED_REPORT.md.

### Adversaries
- Correctness (specs/S81_20_ADV1_correctness.md): NOT_READY on ONE MAJOR, MJ1 (test-only: the env-clean rows for files that carry a list), now closed by E9-E14. Minors: m1 the E8 digest re-pin (accepted, RB-S20-2); m2 the two named source-scanning pins join the comm set (done: 392 files, RB-S20-4); m3 the survivors (A8 killed by G20-GR4; A3 / A11 stated limits L27 / L28); m4 / m5 the PR body wording (RB-S20-5, applied here).
- Quotaandbilling (specs/S81_20_ADV2_quotaandbilling.md): SOUND, 0 blocking / 0 major. QB-m1 the PR body wording (RB-S20-5); QB-m2 / QB-m3 the CLAUDE.md canary row and Accounting sentence reworded in place (RB-S20-6); QB-m4 the stale `_url_row` comment, stated limit L26 (RB-S20-7, no src edit); QB-m5 folded into E9-E14. The design note (a budget filling between the pre-consume check and the exit) is GC-6 / R-S20-38, stated in L23 (RB-S20-8).

### Stated limits (spec section 9 + RULINGS_S81_20 + RULINGS_REBASE_S81_20; full text in the CLAUDE.md S81-20 row)
- L1: camera bodies thin after the compare are delivered.
- L2: URL has no category check; a storefront-title name is not a placeholder there.
- L-URL-SAME: a same-product price check is refused (S81-20b).
- L-URL-GAPS / L-CAM-GAPS: no gap is queued.
- L3: the stream's intermediate frames come before the terminal.
- L4: text / URL refusals come after the paid fan-out.
- L5: the B1 message fires on deliveries only.
- L6: the row is written in both W4-13 states (NEW on URL / camera with flag 1 OFF).
- L7: the other exits keep their keyless refunds.
- L8 (R-S20-39): the camera conflict uses V2 `_category` only, so B1's stub stamp can differ.
- L9: B1's predicate limits are inherited.
- L10: `/text/quick` is not gated.
- L11: a mid-request flip can split one request.
- L12: never set the flag in a local `.env`; the 13 sweep files without a clean list stay red with it exported.
- L13: history keeps no trace of a refusal.
- L14: MYEZ-007 refusal half only.
- L15: the features veto is dropped on the camera.
- L16: a V1 low read is not refused.
- L17 (R-S20-23): G3 tail behaviour; a hard-cap partial queues no gap.
- L18: KB full-hit refusals are not countable until S81-22.
- L19: B1 URL telemetry over-reports (B1b).
- L20: the camera row's query is the base camera query string.
- L21: stream client gone -> incomplete arm.
- L22 (R-S20-34): refunds happen where metering is ON; anon credit burn with ENABLE_ANON_USAGE_GATE ON and metering OFF.
- L23 (R-S20-38, RB-S20-8): the loop bound exists only with both flags ON; a budget filling between the pre-consume check and the exit charges that one refused compare.
- L24 (RB-S20-5): the L12 sweep list is the GREEN sweep's record (19 files / 135 nodes), not the RED file's.
- L25: the stream's refund, record and row land in the settle task after the response.
- L26 (RB-S20-7): the stale `_url_row` comment names the pre-S81-20 call pattern; the next unit touching url_routes.py rewrites it.
- L27 (A3, equivalent): `_category` is set only beside `_is_product: True`, so the `_is_product` test is redundant in production.
- L28 (A11, near-equivalent): camera same_identity on the enriched dicts differs only when exactly one side carries a size.

### Owner steps (names only; a dated ledger line per step)
None to merge. After approval (R-S20-20):
1. `ENABLE_RESULT_STATUS_METADATA` ON on `web` for one window; read the `comparison_result_status` distribution.
2. The D17 pair hit rate (after 045 and the kb-coverage service).
3. The camera low-confidence share.
4. The S81-11 OTA live and `ENABLE_FRAGRANCE_ONLY_GATE` flipped first.
5. Flip `ENABLE_RESULT_GATE` on `web` with the owner's yes. Canary rows: result-gate refusals per user per day by reason; the refusal-budget hits from the result gate; the `[RESULT_GATE]` lines vs B1's delivery distribution; the 400 INSUFFICIENT_DATA rate; refunds == refusals that consumed a credit, minus the spent-budget keeps (a refusal with no consumed credit, e.g. anonymous text, an exempt tier, the metering-OFF camera, has no refund); no history rows.

Rollback = unset the variable.

### [NATIVE READ]
(empty: no Arabic string in this unit)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
