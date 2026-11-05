# S81-20 ADVERSARY REPORT - lens: correctness (Opus 5.5), 2026-11-05
Unit S81-20 B2-RESULT-GATE-V2. HEAD 404b4ba525d42074a52f514ab0ac7299b857dbf4 verified (branch feature/s81-s20-result-gate-v2, base 6869a3e6, one commit). Scratch worktree <scratchpad>/S81-20_adv_correctness (detached at HEAD, no junction), removed at the end. The GREEN worktree was never edited.

VERDICT: NOT_READY (1 MAJOR, test-only; no production-code defect found).

## Byte verification
- Every changed file was re-hashed against the GREEN table. All 17 match: CLAUDE.md, the six app files, the eight E-row files (E8 included), the gate-rows file (c88caa06...) and the RED file (13aa83ad...).
- A fresh Windows checkout (core.autocrlf=true) writes the two NEW LF test files as CRLF. The RED file then measures 74,229 B with sha 46c6c360.... The committed blobs are LF and equal the GREEN table. I rewrote both files from `git show HEAD:` before any run.
- The RED file was re-hashed first and last, in my worktree and in the GREEN worktree: 13aa83ade66d14759278e6da14668f60d48dabdcb1002b4d7bb29c0a88c0180c.

## Runs (one pytest at a time; [pyt] lines)
- RED + gate rows, flag unset: [pyt] tag=s20c-unit-off start=2026-11-05 11:38:41 end=2026-11-05 11:38:48 elapsed=7s bound=600s status=OK rc=0 (178 passed = 166 + 12).
- RED + gate rows, ENABLE_RESULT_GATE=true in the runner env only: [pyt] tag=s20c-unit-on start=2026-11-05 11:38:55 end=2026-11-05 11:39:06 elapsed=11s bound=600s status=OK rc=0 (178 passed).
- E-row files E1-E7 + tests/test_w4_13_flag_off_ledger.py, flag exported: [pyt] tag=s20c-erows-on start=2026-11-05 12:06:54 end=2026-11-05 12:07:30 elapsed=36s bound=1200s status=OK rc=0 (823 passed).
  - Covers the FY25 nine digests, the T23 OpenAPI snapshot, the B1 P10 / P11 purity pins and the R8 pair.
- CI-order set (GREEN's 56 files), flag unset: [pyt] tag=s20c-ci-order start=2026-11-05 12:00:03 end=2026-11-05 12:03:32 elapsed=209s bound=1200s status=FAIL rc=1.
  - 4610 passed, 1 failed: test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (CRLF, in the base record). This equals GREEN's result.
- Comm chunks 5 / 10 / 14 of GREEN's chunks.json at HEAD, flag unset:
  - [pyt] tag=s20c-comm-5 start=2026-11-05 11:53:31 end=2026-11-05 11:55:04 elapsed=94s bound=1200s status=OK rc=0 (575 passed)
  - [pyt] tag=s20c-comm-10 start=2026-11-05 11:55:07 end=2026-11-05 11:57:54 elapsed=166s bound=1200s status=FAIL rc=1. Two failures, both in the stored base record: test_s81_d16_operator_ingest::test_r10_runbook_names_only and test_s81_d17_coverage::test_r9_railway_config_and_hygiene.
  - [pyt] tag=s20c-comm-14 start=2026-11-05 11:57:58 end=2026-11-05 11:59:39 elapsed=101s bound=1200s status=OK rc=0 (800 passed, 35 xfailed)
  - The base record base_records/6869a3e6.../97218ca8...txt was REUSED (LC-6). `comm -13` vs it: EMPTY.
- The two named pins missing from the set (see m2) plus three route-text candidates, flag unset: [pyt] tag=s20c-extra-pins start=2026-11-05 11:53:03 end=2026-11-05 11:53:21 elapsed=17s bound=600s status=OK rc=0 (356 passed, 3 skipped).
- ruff 0.16.5 --select E9,F63,F7,F82 + py_compile on the six app files, the gate-rows file, the RED file and the eight E-row files: clean.
  - F401 reports 4 unused imports, all on unchanged base lines: uuid, save_comparison x2 and HttpUrl.
- No TIMEOUT. NOT MEASURED: none.
- Not re-run: the jest fences and the corpus gate. I read GREEN's logs: the corpus OVERALL SHA cedae008...3f48 is equal on both sides (414 records / 1656 calls); the fence log shows 236 / 240 passed with the four nativeBundle.w37 nodes failing.

## Mutants
Each mutant was applied to a sha-verified byte copy in my worktree, then restored and sha-verified (True every time). Driver: S81-20_adv/mut_driver.py; results: S81-20_adv/mutants.jsonl.

### Spec mutants: 19 applied, 19 KILLED
| Mutant | Edit | Killed by |
|---|---|---|
| M5 | reason arm deleted | test_r20_text_post_v09_refused[w413_off] |
| M6 | handler block deleted | r20 |
| M9 | text refund keyless | r20 |
| M11 | any-low -> both-low | test_r13_camera_gate_table |
| M12 | _is_product check removed | r13 |
| M13 | snapshot ignored | test_r54_camera_enrichment_evasion[ENRICH] |
| M14 | stamp gated on B1 | test_r25_category_conflict_b2_alone |
| M16 | string reading removed | test_r11[zero] |
| M17 | price and -> or | r11 |
| M19 | vocabulary check removed | test_r80_envelope_passthrough |
| M20 | refusal on the first frame only | test_r30_device_quota_keys[text_stream] |
| M21 | stream refund keyless | r30[text_stream] |
| M23 | elif -> if | r30[text_stream] |
| M24 | unsupported_category dropped | test_r06_category |
| M28 | camera placeholder on side 0 only | r13 |
| M30 | stamp ungated | test_p08_off_builder_no_categories |
| M31 | surface arm ungated | test_p09_off_surface_detail_two_keys |
| M35 | keys_out not passed | r30[url_post] |
| M38 | rating range dropped | r11 ("6") |

For M5-M19 the driver's first parser missed the [pyt] tag lines; each log shows "1 failed" on the node named above. M20 onward have their lines, for example [pyt] tag=s20c-mut-M20 ... elapsed=12s bound=600s status=FAIL.

### Own mutants: 12 applied, 9 KILLED, 3 SURVIVED
| Mutant | Edit | Result |
|---|---|---|
| A1 | camera ignores spent (refunds anyway) | KILLED by test_r36_refusal_budget_spent_keeps_credit[camera] |
| A2 | URL record_refusal skipped | KILLED by test_r35_refusal_counted_on_budget[url] |
| A3 | camera_gate_categories without the _is_product test | SURVIVED, EQUIVALENT in production: openai_service sets `_category` only in the V2 builder, next to `_is_product: True` (:391-394) |
| A4 | handler INSUFFICIENT_DATA code test dropped | KILLED by r80 |
| A5 | W3-2 persist operand removed | KILLED by test_r41_stream_refusal_not_persisted_under_echo |
| A6 | re.ASCII removed | KILLED by test_r11[arabic_indic] |
| A7 | reason dropped from the refusal body | KILLED by test_r16_refusal_body_shape |
| A8 | stream settle row input_type text_stream -> text | SURVIVED (prove-nothing, m3) |
| A9 | text exit ignores spent | KILLED by r36[text_post] |
| A10 | camera _rg_on forced False | KILLED by r30[image] |
| A11 | camera same_identity on the enriched p0 / p1 instead of the snapshot view | SURVIVED, near-equivalent (m3) |
| A12 | url_gate_reason refuses a one-product body | KILLED by test_r09_totality |

A11 is near-equivalent because the size enrichment appends the same size_or_count on both sides, and the size axis vetoes differing sizes either way.

## Runtime truth probes (each claim checked against the code)
- **Flag OFF.**
  - Every new read is the env read only: the FIRST statement of result_gate_refusal; the one `_rg_on` read before the enrichment; the first operand of the builder stamp, the surface arm and the handler block.
  - The keyless `_refund_reserved_credit(label)` body is unchanged.
  - The URL `keys_out` fills a dict that nothing reads when the flag is OFF.
  - Stream frames are unchanged: refusal None leaves data untouched.
  - Pinned by the P rows, the FY25 digests and the W4-13 ledger, all green in both states in my runs. TRUE.
- **Error handler.**
  - The fourth block sits after B4 / S81-09 / S81-10 and before retry_after.
  - `reason` passes only for code INSUFFICIENT_DATA with a reason in the four-tuple.
  - B4's passthrough codes do not include INSUFFICIENT_DATA, so the blocks do not overlap. TRUE.
- **Surface call.** `_surface_comparison_failure` always RAISES for the refusal (the coded INSUFFICIENT_DATA arm). The URL block's bare call therefore cannot fall through to delivery. TRUE.
- **Camera.**
  - Placeholder is read on the pre-enrichment snapshot.
  - Any-low applies only to `_is_product` dicts. Note: the V2 builder maps a missing or unknown confidence to "low" (openai_service :374-376), so a V2 item without a confidence is refused low_confidence. This is within R-S20-5 and the flip precondition "camera low share".
  - Same identity uses the brand / name / size view; features are not read.
  - Category comes only from two V2 canonical `_category` values.
  - The block runs after the S81-10 pair gate (CATEGORY_NOT_LIVE wins) and before the try. TRUE.
- **Budget interplay.**
  - Text, URL and camera read budget_state_async for the same subject S81-10 uses (`budget_subject(user)`).
  - Spent: no refund and no record. Not spent: the keyed refund, then ONE record. Gate OFF or admin: refund, no read.
  - The stream finally has no await (G20-GR2) and schedules ONE settle task. TRUE.
- **Other pinned facts.** The G3 tail fact is pinned by r33 / r34 (green). The URL ASCII reading on the real bh / ae fixtures is pinned by r11 (green). P10 / P11 purity: result_gate.py imports only os, re, typing and text_sanitize. TRUE.
- **Contract freeze (PLAN_S80 section 0).** Text and URL refusals are 400 INSUFFICIENT_DATA through _surface_comparison_failure. The camera returns action:'error' before compare_from_text. No new code, no 503; `reason` is additive only. TRUE.
- **CLAUDE.md block.** One block at :576-579, before ## Tests (:580), plus the :341 pointer clause. Its numbers (166, 135 nodes / 19 files, labels, reasons, L1-L23) match the bytes and the sweep file.

## Findings
### MAJOR
- **MJ1: the spec 4.1 E8+ row and GC-10 were not executed for files that HAVE a clean list.**
  - The spec's E8+ row says: add ENABLE_RESULT_GATE only to each file that goes red with the flag exported; a red file without a list is named in the CLAUDE.md row instead. GC-10 says a red file joins 4.1 by name as an E-row, never silently.
  - GREEN's sweep (sweep_only.txt) shows candidate files that HAVE a list going red with the flag exported:
    - tests/test_s81_s09_device_quota.py: 7 nodes (CLEAN_ENV :97)
    - tests/test_s81_s10_fragrance_gate.py: 17 nodes (_CLEAR_ENV :500)
    - tests/test_s81_s10_gate_rows.py: 1 node (delenv :252 / :288)
    - tests/test_s81_s18_kb_first_serve.py: 9 nodes (CLEARED_ENV :82)
    - plus test_s81_s09_gate_rows and test_s81_s17_kb_ingest, per GREEN's Q1
  - GREEN named all 19 files in L12 instead (D2, "spec 7.4 alternative"). That alternative applies only to files without a list.
  - Fix: either one-name E-rows (E9+) in a TEST-ONLY round (LC-2), each file proven green with and without the flag, or an orchestrator ruling that accepts D2.
  - No production impact: CI runs the flag unset.

### MINOR (stated limits / documentation, LC-4)
- **m1 (E8).** The tests/test_s81_kb_schema.py IDENTITY_NODES re-pin moves a pin outside E1-E7 without the brief's STOP.
  - E1 forced it mechanically, and it follows the RB6-11 precedent. A ruling is owed (GREEN Q2).
  - The re-pinned value equals `git show HEAD:tests/test_s75_fanout_identity.py | sha256sum` (93c59246...).
- **m2 (comm set vs the union rule).** tests/test_migration_index_predicate_immutability.py and tests/test_openai_key_log_hygiene_s69.py are NAMED source-scanning pins in s81-common. Both are absent from the RED's 388-file list and from GREEN's 390-file list.
  - Neither reads an edited file: they read migrations/*.sql and extraction_service. Both are green at HEAD (s20c-extra-pins).
  - My grep re-derivation (module / symbol / app.main / route text / scanner patterns) found no other missing test module. tests/_env_safety.py, tests/conftest.py and tests/fixtures/_gen_w4_13_flag_off_ledger.py match, but they are not test modules.
- **m3 (prove-nothing rows).**
  - A8: nothing pins the stream settle row's input_type "text_stream".
  - A11: the rows cannot tell camera same_identity on the snapshot view from the enriched dicts.
  - A3 is equivalent in production.
  - G20-GR1 accepts `status_code in (200, 400)`; the budget_reads assertion is what carries the row.
- **m4 (PR body accuracy).**
  - "No 64-hex literal" is false: E8 adds the IDENTITY_NODES 64-hex value, and GREEN's own report says so.
  - "No constant named with a gitleaks keyword" is literally false for the frozen RED file (AUTHREQ, ENVELOPE_KEYS). They are not digests, and the hook passed.
  - L24 says "the RED file's flag-exported sweep list", but the list comes from the comm-set sweep.
- **m5 (PR body not pure ASCII).** The required attribution line's emoji gives a max byte of 240. Size is 11,087 B, under 25,600.

## Hygiene
- 2,423 added lines. The one non-ASCII added line is the CLAUDE.md :341 Feature Flags line, which carries its BASE em dash.
- No personal value.
- Blobs are LF with CRLF working copies, as at base.
- Footprint = GC-13 + E8. No scs, kb_ingest, usage_service, category_gate, migration, client, requirements, .githooks or data file.
