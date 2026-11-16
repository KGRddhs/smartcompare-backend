# INC-I2e GUARD-SHORT-LINE: RED report (S96, s96e-red agent, Opus 5.5, 2026-11-16)

Worktree C:/Users/SynAckITPC/Documents/AI/sc-s96-i2e, branch fix/inc-i2e-guard-short-line, base b0ad260363e0cf0074e4ee596b140d073466e92a. Notes folder = this folder (notes.md is the running log). Written through the shell.

## 1 Base measurements (git show HEAD)
- app/services/image_relevance.py 569 lines; @dataclass(frozen=True) :322 / class Identity :323 (6 fields); _line_tokens :334-348; identity :351-378; check :381-404; image_query :407; relevance_kwargs :433-452; RelevanceCall :455; module imports :34-45.
- structured_comparison_service.py: import :1603; call site :6338 (relevance_kwargs(brand, name, category, partial_slot, is_vision)); KB-served branch :6326 (kb_serve.served(...) if the KB image exists, else get_product_image_url); page-image guard :6479.
- Base reasons of every E case: base_cases.txt. All "name" except E4 line "No 5" vs "Chanel No.5 EDP" -> None and vs "Chanel No 19 Eau de Parfum" -> None; E7 line "Chanel N(deg)5" vs both titles -> None (the base accepts No 19).

## 2 Identity equality / construction
Only tests/test_inc_i1_picture_must_match.py references image_relevance under tests/. It calls leaf.identity(...) (:641, :659) and passes the result to check / image_query. No Identity(...) construction (positional or keyword), no == on an Identity, no dataclasses.replace / asdict / astuple / fields under tests/. New defaulted fields at the END of Identity are safe (the prototype uses that form).

## 3 RED file
tests/test_inc_i2e_guard_short_line.py sha256 38090ba9bee4365db463cea2d8bc41858dcf0da77b2b69cc0894fe874e4a4f45, 21287 bytes, 0 non-ASCII, LF only. black 26.5.1 --check clean (in W); ruff E9,F63,F7,F82 clean; the repo's full ruff config clean. Rows: E1-E9 (RED), P1 (x5 S spellings), P2 (x2), P3 (x3 G spellings), P4. P1 base reasons are literals (CASES last column) measured at b0ad2603.

## 4 RED at base
first bytes: [pyt] tag=s96e-red-base start=2026-11-16 19:58:22 end=2026-11-16 19:58:26 elapsed=4s bound=600s status=FAIL rc=1 / [hermeticity] sentinel checked 20 test(s) / [netguard] blocked 0 attempt(s) from 0 node(s)
final bytes (after the restore): [pyt] tag=s96e-red-base2 start=2026-11-16 20:23:19 end=2026-11-16 20:23:22 elapsed=3s bound=600s status=FAIL rc=1 / [hermeticity] sentinel checked 20 test(s) / [netguard] blocked 0 attempt(s) from 0 node(s)
9 failed (E1-E9; 9 AssertionErrors, 0 other errors), 11 passed (P1-P4). No E row passes at base.

## 5 Comm set and base record
206 files (comm/comm_set.txt; reasons comm/comm_reasons.txt), 9 chunks of <= 25, set sha256 84667417af6ad095d2cd4eb8f1aa642adaf0f071ea506ee3d2016d2b8c9076e9 (over the sorted LF-joined list plus LF). Union: symbol grep (image_relevance, image_service, get_product_image_url, relevance_kwargs, RelevanceCall, Identity, identity(, check(, noon_service, inc_r1) + test_inc_i1_* / test_inc_r1_* + the named source-scanning pins + the source-reader classes (getsource, glob / rglob, os.walk, listdir / scandir, ast.parse, app path literals, .__file__, .github) + the CLAUDE.md readers by grep and the import-graph closure; minus tests/test_precommit_hook.py, _phase_b.py, _phase_b_round2.py. No cached record existed; stored: harness/base_records/b0ad260363e0cf0074e4ee596b140d073466e92a/84667417af6ad095d2cd4eb8f1aa642adaf0f071ea506ee3d2016d2b8c9076e9.txt (+ .members.txt).
Base failing node ids (22; identical at the prototype; environmental: CRLF-working-copy hygiene pins and the two known cold-tiktoken prompt_truth ERRORs):
tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
tests/test_s81_s07_meas_harness.py::test_r35_fixtures
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


## 6 Prototype (in place, under the lock, from byte copies)
image_relevance.py proto sha256 3f59c99468abedf76bd3f2f5069f25c4b0b2ae37c0aca92a2fb75fb8b299b48d (CRLF); CLAUDE.md proto sha256 08fe8fb6ae2f2cbfd0da8f66f945f86c0197680a6d4d1e911d6705c5ab112753. Diff: proto.diff (sha256 2a01f3ed93728bd9d2484e25179bead692994b0ef0cd3272089d5e97ea75dda0; 2 files, +168 / -1). Implementation: SHORT_LINE_FLAG_ENV, short_line_enabled, ELISION, fold_numero, _line_keys, _candidate_keys, four defaulted Identity fields at the END (line_sig, line_short, line_pairs, line_joins) filled always, check's FIRST statement branches to _check_short_line under the flag (the rest of check is the base text), a module docstring paragraph. CLAUDE.md: one sentence after the INC-R1 sentence of the :341 Feature Flags paragraph; the ### block after the INC-R1 owner-steps bullet.
RED at prototype: [pyt] tag=s96e-red-proto start=2026-11-16 20:11:27 end=2026-11-16 20:11:30 elapsed=3s bound=600s status=OK rc=0 (20 passed); final bytes: [pyt] tag=s96e-red-proto2 start=2026-11-16 20:22:24 end=2026-11-16 20:22:26 elapsed=3s bound=600s status=OK rc=0 (20 passed); both [hermeticity] sentinel checked 20 test(s), [netguard] blocked 0 attempt(s) from 0 node(s).
Comm set at prototype: 22 failing ids; comm -13 (prototype-only) EMPTY; comm -23 EMPTY; per-chunk pass counts identical. MOVED PINS: none.
black 26.5.1 --check on the prototype image_relevance.py and on the RED file: both unchanged (clean). CI ruff tier (E9,F63,F7,F82): clean. The repo's full ruff config (report-only): the prototype has one B905 (zip without strict= in _candidate_keys); base has none.

## 7 Comm [pyt] lines (base chunks 01-09, then prototype chunks 01-09)
[pyt] tag=s96e-red-base-c01 start=2026-11-16 20:00:01 end=2026-11-16 20:00:41 elapsed=39s bound=1200s status=OK rc=0
[pyt] tag=s96e-red-base-c02 start=2026-11-16 20:00:41 end=2026-11-16 20:01:58 elapsed=77s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 964 test(s)
[netguard] blocked 13 attempt(s) from 2 node(s)
[pyt] tag=s96e-red-base-c03 start=2026-11-16 20:01:59 end=2026-11-16 20:03:14 elapsed=76s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 973 test(s)
[netguard] blocked 8 attempt(s) from 4 node(s)
[pyt] tag=s96e-red-base-c04 start=2026-11-16 20:03:15 end=2026-11-16 20:03:52 elapsed=38s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 2284 test(s)
[netguard] blocked 4 attempt(s) from 2 node(s)
[pyt] tag=s96e-red-base-c05 start=2026-11-16 20:03:53 end=2026-11-16 20:06:39 elapsed=166s bound=1200s status=FAIL rc=1
[hermeticity] sentinel checked 2843 test(s)
[netguard] blocked 24 attempt(s) from 2 node(s)
[pyt] tag=s96e-red-base-c06 start=2026-11-16 20:06:40 end=2026-11-16 20:08:41 elapsed=121s bound=1200s status=FAIL rc=1
[pyt] tag=s96e-red-base-c07 start=2026-11-16 20:08:41 end=2026-11-16 20:09:54 elapsed=72s bound=1200s status=FAIL rc=1
[pyt] tag=s96e-red-base-c08 start=2026-11-16 20:09:54 end=2026-11-16 20:10:53 elapsed=59s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 277 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-base-c09 start=2026-11-16 20:10:54 end=2026-11-16 20:11:00 elapsed=6s bound=1200s status=OK rc=0
[pyt] tag=s96e-red-proto-c01 start=2026-11-16 20:11:34 end=2026-11-16 20:12:12 elapsed=37s bound=1200s status=OK rc=0
[pyt] tag=s96e-red-proto-c02 start=2026-11-16 20:12:12 end=2026-11-16 20:13:27 elapsed=75s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 964 test(s)
[netguard] blocked 13 attempt(s) from 2 node(s)
[pyt] tag=s96e-red-proto-c03 start=2026-11-16 20:13:28 end=2026-11-16 20:14:36 elapsed=68s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 973 test(s)
[netguard] blocked 8 attempt(s) from 4 node(s)
[pyt] tag=s96e-red-proto-c04 start=2026-11-16 20:14:37 end=2026-11-16 20:15:12 elapsed=35s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 2284 test(s)
[netguard] blocked 4 attempt(s) from 2 node(s)
[pyt] tag=s96e-red-proto-c05 start=2026-11-16 20:15:13 end=2026-11-16 20:17:49 elapsed=156s bound=1200s status=FAIL rc=1
[hermeticity] sentinel checked 2843 test(s)
[netguard] blocked 24 attempt(s) from 2 node(s)
[pyt] tag=s96e-red-proto-c06 start=2026-11-16 20:17:49 end=2026-11-16 20:19:47 elapsed=118s bound=1200s status=FAIL rc=1
[pyt] tag=s96e-red-proto-c07 start=2026-11-16 20:19:48 end=2026-11-16 20:20:58 elapsed=71s bound=1200s status=FAIL rc=1
[pyt] tag=s96e-red-proto-c08 start=2026-11-16 20:20:59 end=2026-11-16 20:21:58 elapsed=59s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 277 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-proto-c09 start=2026-11-16 20:21:59 end=2026-11-16 20:22:04 elapsed=6s bound=1200s status=OK rc=0

## 8 Mutants (each from the prototype byte copy, the RED file alone)
wrote app/services/image_relevance.py 3f59c99468abedf76bd3f2f5069f25c4b0b2ae37c0aca92a2fb75fb8b299b48d
wrote CLAUDE.md 08fe8fb6ae2f2cbfd0da8f66f945f86c0197680a6d4d1e911d6705c5ab112753
======================== 20 passed, 1 warning in 1.89s ========================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-proto2 start=2026-11-16 20:22:24 end=2026-11-16 20:22:26 elapsed=3s bound=600s status=OK rc=0
== M1
wrote app/services/image_relevance.py 86becad1189b9d5b8688dfbc6a2692cc874d3c0cfcc3c07bd9fc59ab11b30afc
=================== 2 failed, 18 passed, 1 warning in 2.41s ===================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-mut-M1 start=2026-11-16 20:22:27 end=2026-11-16 20:22:30 elapsed=3s bound=600s status=FAIL rc=1
FAILED tests/test_inc_i2e_guard_short_line.py::test_e4_chanel_numero_fold - A...
FAILED tests/test_inc_i2e_guard_short_line.py::test_e7_empty_brand_numero_and_joins
== M2
wrote app/services/image_relevance.py 2c01eba2f5297c860ada068e98ba056f128ae8ff1b04cd4a7cdb0bdc45aa974b
=================== 2 failed, 18 passed, 1 warning in 2.39s ===================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-mut-M2 start=2026-11-16 20:22:31 end=2026-11-16 20:22:34 elapsed=3s bound=600s status=FAIL rc=1
FAILED tests/test_inc_i2e_guard_short_line.py::test_e4_chanel_numero_fold - A...
FAILED tests/test_inc_i2e_guard_short_line.py::test_e7_empty_brand_numero_and_joins
== M3
wrote app/services/image_relevance.py 78e859bca020c4f3bbdec25a959f8b505780fdea41eb2c3d3313c9ed5b6ec577
=================== 1 failed, 19 passed, 1 warning in 2.53s ===================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-mut-M3 start=2026-11-16 20:22:35 end=2026-11-16 20:22:38 elapsed=3s bound=600s status=FAIL rc=1
FAILED tests/test_inc_i2e_guard_short_line.py::test_e3_l_eau_d_issey_joins - ...
== M4
wrote app/services/image_relevance.py 4313eb0ae48b25b3511f01cf7f4ad20a4aed0b6fa8fc5b10d97e8fc7ab9dc34f
=================== 1 failed, 19 passed, 1 warning in 2.39s ===================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-mut-M4 start=2026-11-16 20:22:39 end=2026-11-16 20:22:42 elapsed=3s bound=600s status=FAIL rc=1
FAILED tests/test_inc_i2e_guard_short_line.py::test_e1_ysl_y_one_letter_line
== M5
wrote app/services/image_relevance.py a4e6cbf23b01002fc0bf78f47a5165a5951f7f7231c5721dedaae22d556907a2
=================== 1 failed, 19 passed, 1 warning in 2.39s ===================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-mut-M5 start=2026-11-16 20:22:43 end=2026-11-16 20:22:46 elapsed=3s bound=600s status=FAIL rc=1
FAILED tests/test_inc_i2e_guard_short_line.py::test_e5_joined_spellings_both_ways
== M6
wrote app/services/image_relevance.py 5053a06170eea102344fb15a0672d0f8f5d17d0f769f3db6cf0beb1ad29ee14a
=================== 1 failed, 19 passed, 1 warning in 2.43s ===================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-mut-M6 start=2026-11-16 20:22:46 end=2026-11-16 20:22:49 elapsed=3s bound=600s status=FAIL rc=1
FAILED tests/test_inc_i2e_guard_short_line.py::test_e3_l_eau_d_issey_joins - ...
== M7
wrote app/services/image_relevance.py f6d3c0e70aafd64c1fc630234f9a499b055fbd8a49042263402a7511aa7e851a
=================== 1 failed, 19 passed, 1 warning in 2.40s ===================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-mut-M7 start=2026-11-16 20:22:50 end=2026-11-16 20:22:53 elapsed=3s bound=600s status=FAIL rc=1
FAILED tests/test_inc_i2e_guard_short_line.py::test_e6_nothing_of_the_line_to_match
== M8
wrote app/services/image_relevance.py 0e0169002dee2b73aa89154ed59682b78c5cfc1cf7d67aa48cfa7977201e6b96
=================== 9 failed, 11 passed, 1 warning in 2.47s ===================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-mut-M8 start=2026-11-16 20:22:54 end=2026-11-16 20:22:57 elapsed=3s bound=600s status=FAIL rc=1
FAILED tests/test_inc_i2e_guard_short_line.py::test_e1_ysl_y_one_letter_line
FAILED tests/test_inc_i2e_guard_short_line.py::test_e2_ted_baker_m_elision_letter_whole_line
FAILED tests/test_inc_i2e_guard_short_line.py::test_e3_l_eau_d_issey_joins - ...
FAILED tests/test_inc_i2e_guard_short_line.py::test_e4_chanel_numero_fold - A...
FAILED tests/test_inc_i2e_guard_short_line.py::test_e5_joined_spellings_both_ways
FAILED tests/test_inc_i2e_guard_short_line.py::test_e6_nothing_of_the_line_to_match
FAILED tests/test_inc_i2e_guard_short_line.py::test_e7_empty_brand_numero_and_joins
FAILED tests/test_inc_i2e_guard_short_line.py::test_e8_end_to_end_ted_baker_m
FAILED tests/test_inc_i2e_guard_short_line.py::test_e9_flag_read_per_call - A...
== M9
wrote app/services/image_relevance.py df209f43cea8acf4102ddd667763aa79d436ae512a3043d50a37fa00770a9d90
=================== 5 failed, 15 passed, 1 warning in 2.40s ===================
[hermeticity] sentinel checked 20 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-red-mut-M9 start=2026-11-16 20:22:58 end=2026-11-16 20:23:01 elapsed=3s bound=600s status=FAIL rc=1
FAILED tests/test_inc_i2e_guard_short_line.py::test_p1_flag_off_golden_is_the_base[None]
FAILED tests/test_inc_i2e_guard_short_line.py::test_p1_flag_off_golden_is_the_base[false]
FAILED tests/test_inc_i2e_guard_short_line.py::test_p1_flag_off_golden_is_the_base[ FALSE ]
FAILED tests/test_inc_i2e_guard_short_line.py::test_p1_flag_off_golden_is_the_base[0]
FAILED tests/test_inc_i2e_guard_short_line.py::test_p1_flag_off_golden_is_the_base[garbage]
wrote app/services/image_relevance.py 3f59c99468abedf76bd3f2f5069f25c4b0b2ae37c0aca92a2fb75fb8b299b48d
wrote CLAUDE.md 08fe8fb6ae2f2cbfd0da8f66f945f86c0197680a6d4d1e911d6705c5ab112753
DONE

Summary: M1 killed by E4, E7; M2 by E4, E7; M3 by E3 (only the added L'Homme title); M4 by E1 (only the added "Y 2" line); M5 by E5 (only the added cross-text row); M6 by E3 (the Nuit row); M7 by E6; M8 by E1-E9; M9 by P1 x5. 9/9 killed, every kill an AssertionError.

## 9 Restore proof
restore base: image_relevance.py sha256 9e6611e0... hash-object aa631704b20ca8c48d145c8b8556e9bc2319516a == HEAD blob; CLAUDE.md sha256 20c2cabb... hash-object 79bfacd0e43afa4c8f01e4291ac7a25a04e8e4ef == HEAD blob; W/.qa-mutation.lock deleted; git status --short: "?? tests/test_inc_i2e_guard_short_line.py" only.

## 10 Deviations
- D1 spec rule 1c read as: sig2 and short2 empty, joins2 non-empty -> pass iff joins2 & t2, else name; rule 1d only when all three are empty. The literal text would send a non-matching joins line (E3 Nuit) to 1d and pass it on the fragrance word, contradicting E3 and M6.
- D2 three rows beyond section 5 because the listed titles cannot kill M3 / M4 / M5: E1 line "Y 2" (two short tokens), E3 title "Issey Miyake Nuit d'Issey L'Homme Eau de Parfum" (standalone l and d, no leau / eaud join), E5 texts ("Dolce & Gabbana Light", "Blue Perfume Shop") (a join only across texts).
- D3 E4 also pins the fold_numero table and E9 the reader table + SHORT_LINE_FLAG_ENV (contract names), through getattr helpers.
- D4 P2 covers lines Y, M, L'Eau d'Issey, N(deg)5, N(ord)5; "No 5" is excluded because the base ACCEPTS "Chanel No.5 EDP" and "Chanel No 19" with it (measured).
- D5 P4 pins every non-typing module-level import exactly; `from typing import` may gain typing names.
- D6 comm chunks and mutants ran from neutral driver scripts (comm_drive.sh, mut_drive.sh) launched once each with the Bash tool in the background (its foreground cap 600 s < bound 1200 s); each driver ran waitfree before every pytest, one pytest at a time; I waited outside any runner.
- D7 the RED file was edited after the first base run (lint only: zip strict=True, one assert operand order, a simpler P4 loop); re-run at base (s96e-red-base2) and prototype (s96e-red-proto2) with identical outcomes. The comm set does not contain the RED file.
- D8 the elision whole-line drop set is STOP | CONCENTRATION | FRAGRANCE | UNIT words (the spec's words), not NAME_EXCLUDE (which adds "spray").
- D9 .github/black-clean-paths.txt not edited (section 3 item 3 is GREEN's; the RED file IS black-clean, so GREEN adds it).

## 11 Open questions
- Q1 confirm the D1 reading of rules 1c / 1d.
- Q2 should "spray" also leave the whole-line test (a line "M Spray" then keeps M)?
- Q3 B905 in the prototype's _candidate_keys under the full (report-only) ruff config: GREEN may write zip(..., strict=False).
- Q4 NOT MEASURED here: the 14 client jest fences (section 7 assigns them to GREEN because CLAUDE.md changes).
