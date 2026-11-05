## S81-20 B2-RESULT-GATE-V2 (ENABLE_RESULT_GATE, default OFF) - refuse unsupported verdicts as non-deliveries

Base `6869a3e655805afd3adbba43f99578dd79585934`; HEAD `404b4ba525d42074a52f514ab0ac7299b857dbf4` (branch `feature/s81-s20-result-gate-v2`). FOCUS unit (the quota path): GREEN + two adversaries (correctness; quotaandbilling). Every flag OFF in production: nothing changes on merge.

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
`tests/test_s81_s20_result_gate.py` (frozen, sha256 prefix `13aa83ad`) has 166 nodes: 122 RED at base (AssertionError only) and 44 PIN. All 166 are green at HEAD with the flag unset and with `ENABLE_RESULT_GATE=true` exported. MYEZ ids: MYEZ-001 (category-conflict half), MYEZ-002, MYEZ-003, MYEZ-012 (text / stream / URL), MYEZ-004 (camera, R-S20-4), MYEZ-007 (refusal half), MYEZ-011, MYEZ-027. All map to `ENABLE_RESULT_GATE`. Per-row evidence: specs/S81_20_RED_REPORT.md.

Flip preconditions (names only):
- App Store approval of build 3.
- B1's canary window: `ENABLE_RESULT_STATUS_METADATA` ON and the `comparison_result_status` distribution read.
- The D17 pair hit rate from `kb_coverage_daily`, after 045 and the kb-coverage service.
- The camera low-confidence share read.
- The R-A2 order: after the S81-11 OTA, with `ENABLE_FRAGRANCE_ONLY_GATE` flipped FIRST.
- The owner's yes.

### Gate rows (GREEN-owned, `tests/test_s81_s20_gate_rows.py`, 12 nodes)
G20-GR1: spent budget -> no refund AND no record (text POST / GET / stream / URL / camera). G20-GR2: no Await in the stream finally (base: none); the single settle label; the settle sequence (open / spent / gate OFF). G20-GR3: client gone before the refusal terminal -> keyless incomplete refund, no exit budget read, no record, the T5 row. Each row was proven RED-then-green by an inverse edit on a byte copy of GREEN's code, restored and sha-verified: 8 inverse edits, all KILLED (table: specs/S81_20_GREEN_GR_MUTATION_TABLE.md).

### Deliberate pin changes (spec 4.1) - one-name additions of `ENABLE_RESULT_GATE` to env-clean lists
| # | File | List |
|---|---|---|
| E1 | tests/test_s75_fanout_identity.py | UNIT_ENV |
| E2 | tests/test_retro_w2_1.py | _clean_flags |
| E3 | tests/test_s71_u13_compare_auth_required.py | CLEAN_ENV |
| E4 | tests/test_paid_route_metering.py | _CLEAN_ENV |
| E5 | tests/test_w4_13_measurement_truth.py | _clean_flags |
| E6 | tests/test_s80_b1.py | CLEAR |
| E7 | tests/test_s80_b3_vision_identity_v2.py | UNIT_ENV |
| E8 | tests/test_s81_kb_schema.py:475 | IDENTITY_NODES: the FY25 node LF sha re-pinned (moved by E1; the S81-04 / S81-06 RB6-11 precedent; deviation D1) |
Each E-row file was proven green with the flag unset and with it exported (one runner call each, with the RED file): [pyt] s20g-erows-off OK 987 passed / [pyt] s20g-erows-on OK 987 passed.

### Counts and gates
- RED file: 166 / 166 flag unset ([pyt] s20g-unit-off1 OK) and exported ([pyt] s20g-unit-on1 OK).
- Mutants (RED round): 42 KILLED (M1-M42 incl. M32b, M37a-c), plus EQ1 / EQ2 equivalent by ruling. GR inverse edits: 8 KILLED.
- Comm set: 390 files (the RED round's 388 + the RED file + the gate-rows file) in 16 chunks of at most 25, plus tests/test_secret_scan_static.py alone. It reuses the stored base record `harness/base_records/6869a3e6.../97218ca8...txt` (LC-6). HEAD failures: 18 (17 base environmental + 1 E8 node, green after the re-pin: [pyt] s20g-kbschema-off OK 529 passed). comm -13 vs base (branch-only NEW): EMPTY after E8 (before E8: tests/test_s81_kb_schema.py::test_s14_p06_identity_nodes_untouched[tests/test_s75_fanout_identity.py]).
- E8+ local-.env sweep (comm set with the flag exported): 135 nodes beyond the base noise in 19 files go red with ENABLE_RESULT_GATE exported (thin stub bodies refused); named in the CLAUDE.md L12 limit, no clean-list edits beyond E1-E7 (open question Q1).
- CI-order set (spec 7.5): [pyt] s20g-ci-order FAIL rc=1: 4610 passed, 1 failed = tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (environmental CRLF, in the base record).
- Corpus gate (`scripts/verify_flag_byte_identity.py`, flag OFF): base OVERALL cedae008...3f48 (git-archive tree of 6869a3e6) / HEAD OVERALL cedae008...3f48 (equal; 414 records / 1656 calls).
- Client fences: 13 / 14 with exactly the four config/nativeBundle.w37 drift nodes (jest 29.7.0, node v24.11.1: 14 suites, 240 tests, 236 passed, 4 failed = nativeBundle.w37 d5 / k2 / k4 / k5). The full jest suite was not run (LC-7: the final round). No .githooks change, so the hook test files were not run.
- ruff E9/F63/F7/F82 + py_compile clean. The six app files keep CRLF (hunks only). New test file is ASCII + LF. No 64-hex literal; no constant named with a gitleaks keyword.
Gate logs: specs/S81_20_GREEN_GATE_LOGS.md.

### Stated limits
These follow spec section 9 + RULINGS_S81_20:
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
- L12: never set the flag in a local `.env`.
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
- L23 (R-S20-38): the loop bound exists only with both flags ON.
- L24 (GREEN): the RED file's flag-exported sweep list above (L12) is named, not cleaned; E1 moves the FY25 node's file sha (E8 re-pin).
- L25 (GREEN): the stream settle runs after the response bytes; a process killed between the terminal frame and the settle task loses that refund (the base refund arms are fire-and-forget too).

### Owner steps (names only; a dated ledger line per step)
None to merge. After approval:
1. `ENABLE_RESULT_STATUS_METADATA` ON on `web` for one window; read the `comparison_result_status` distribution.
2. The D17 pair hit rate (after 045 and the kb-coverage service).
3. The camera low-confidence share.
4. The S81-11 OTA live and `ENABLE_FRAGRANCE_ONLY_GATE` flipped first.
5. Flip `ENABLE_RESULT_GATE` on `web` with the owner's yes. Canary rows: refusals per user per day by reason; refusal-budget hits from the result gate; `[RESULT_GATE]` lines vs B1's delivery distribution; the 400 INSUFFICIENT_DATA rate; refunds == refusals; no history rows.

Rollback = unset the variable.

### [NATIVE READ]
(empty: no Arabic string in this unit)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
