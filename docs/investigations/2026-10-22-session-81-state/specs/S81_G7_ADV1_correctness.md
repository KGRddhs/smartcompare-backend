# S81-G7 ADVERSARY REPORT - correctness lens (engineering + data checks folded in, LC-1)

Agent: Opus 5.5 (claude-opus-5-5), 2026-11-05. Written through the shell (heredocs).
Unit: S81-G7 FOLLOWUPS (D16b + D17b + D22c (1)+(2) + D22d). GREEN HEAD 4b0f3b9c9192c3c6c69c883c0c4a60461aca9ec5 on feature/s81-g7-followups (verified first in sc-s81-g7; unchanged at the end). Base 6869a3e6.

## VERDICT: SOUND (no blocking, no major; 4 minors -> stated limits under LC-4)

## Method
- Own detached scratch worktree S81-G7_adv_correctness at 4b0f3b9c (no junction), REMOVED at the end (git worktree remove --force). core.autocrlf=true checks out CRLF, so the worktree was re-materialised from the HEAD blobs (git -c core.autocrlf=false -c core.eol=lf archive HEAD | tar -x; git diff HEAD empty): every probe ran on the exact committed LF bytes. The 15 changed/frozen hashes (head_lf_shas.txt) re-verified after the mutants: 15/15 OK.
- Frozen files (GC-1) re-hashed FIRST and LAST in sc-s81-g7 (working copy and HEAD blob): 6fd81d37 / 927dc060 / ff9b45da / 79a33372 / 15c5dc0f / 8c793a16 all equal. The GREEN table hashes are CRLF working-copy hashes; my CRLF checkout reproduced every one (82bb323e, a99da79c, 4f212546, 47c92eae, 79f7c167, 6997e623, aeb8fc4d, 306cd6ac, 360cc6e1). Base and HEAD blobs are all LF (0 CR): no line-ending churn.
- One pytest at a time; never beside the corpus gate.

## Gates re-run ([pyt] lines)
[pyt] tag=g7adv-units-off start=2026-11-05 14:33:05 end=2026-11-05 14:33:12 elapsed=7s bound=600s status=OK rc=0 (60 passed; [hermeticity] sentinel checked 60; [netguard] blocked 0)
[pyt] tag=g7adv-units-on start=2026-11-05 14:33:13 end=2026-11-05 14:33:20 elapsed=7s bound=600s status=OK rc=0 (60 passed; ENABLE_BEHAVIOR_PROFILE_REBUILD=true in the runner env only; [netguard] blocked 0)
[pyt] tag=g7adv-ciorder start=2026-11-05 14:52:11 end=2026-11-05 14:53:37 elapsed=86s bound=1200s status=OK rc=0 (21 files, 1164 passed; [hermeticity] 1164; [netguard] blocked 22 from 21 nodes = test_hermeticity_pins by design). On LF bytes the 3 env CRLF nodes (d16 r10, d17 r9, s19 r15) PASS: GREEN's 1161 + 3 are environmental.
[pyt] tag=g7adv-pins-readers start=2026-11-05 14:53:40 end=2026-11-05 14:54:26 elapsed=45s bound=1200s status=OK rc=0 (15 files: test_model_config, _enforced, test_prompt_fence, test_u3c_store_false_pin, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_start_command, test_s81_kb_schema + CLAUDE.md readers test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire: 1394 passed; [netguard] blocked 24 from 2 nodes = the s04 neutralized-supabase sentinels)
[pyt] tag=g7adv-comm-01 start=2026-11-05 14:54:42 end=2026-11-05 14:55:12 elapsed=30s bound=1200s status=FAIL rc=1 (2 failed = the two test_auth_interceptor base-record nodes; 745 passed)
[pyt] tag=g7adv-comm-03 start=2026-11-05 14:55:16 end=2026-11-05 14:56:10 elapsed=54s bound=1200s status=OK rc=0 (1260 passed, 3 skipped, 5 deselected)
[pyt] tag=g7adv-comm-20 start=2026-11-05 14:56:14 end=2026-11-05 14:57:59 elapsed=105s bound=1200s status=OK rc=0 (3565 passed)
Comm chunks = GREEN's chunk_01 / _03 / _20 lists: FAILED nodes vs the reused base record ab9758ed... (17): comm -13 EMPTY.
Corpus gate at HEAD, alone (14:44:06-14:52:00, exit 0), --flags ENABLE_VARIANT_LLM_HINT,ENABLE_BEHAVIOR_PROFILE_REBUILD: RECORDS n=414 calls=1656; OVERALL SHA256 d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf == the GC-4 base value.
ruff 0.16.5 --select E9,F63,F7,F82 on 8 edited + 5 RED files: All checks passed; py_compile OK. (Report-only full ruleset: B009 on cron_kb_coverage.py:297, the same pattern as live_robots.py:458; not a CI tier, no finding.)
Hygiene: no 64-hex literal, no keyword-named constant, no 8-digit run, no at sign beyond decorators in added lines; 0 non-ASCII added bytes; no dependency / migration / client / requirements / .githooks file; no leftover reference to the deleted symbols or file outside the RED file, the CLAUDE.md row and historical docs/investigations; _varhint_normalized_family still used (price_service:9123).
NOT RUN: the fourteen client jest fences (no junction by the script; GREEN's 13/14 + the four w37 nodes stands), the hook test files (no .githooks edit), the full jest (LC-7, final round).

## Mutants on the GREEN bytes (34 applied; S81-G7_adv/mutation_table_adv.md with every [pyt] line; raw mut_results*.json)
25 spec mutants re-applied by hand on sha-verified byte copies (D16b-M1..M5, M7, M8; D17b-M1..M5; D22c-M1, M3, M4, M5, M6, M9; D22d-M1..M6, M8): ALL KILLED (D16b-M1 hits the shared beyond_skew, since GREEN routes all three readers through one rule; D22d-M4 approximated as a counter stuck at 1). The GREEN report and PR body cite the RED round's 31 mutants on the prototype; this is the first mutation evidence on GREEN's own shape, and it agrees.
Own mutants KILLED: ADV-O5 validator reads kb_serve._now (R2-R5), ADV-O6 classify ignores its now argument (R6/R7), ADV-O7 products alias ->> (R2/R3/R5), ADV-O8 skew in minutes (R3), ADV-O9 main ignores the gathered count (d22d R4 + G5 GR6).
SURVIVED (prove-nothing rows): ADV-O1 _read_by returns after the FIRST 100-value chunk; ADV-O2 _render leaves DEL 0x7F raw; ADV-O3 ON normalisation also applied with the flag OFF (unobservable: the OFF selects fail first; equivalent); ADV-O4 the dropped counter also counts unclean names on non-wrong kb_feedback rows.

## Runtime truth per claim
D16b: OperatorIngest with _now=2026-11-02T06:00Z: +300 s (Z) accept; +300.000001 s refuse; +301 s refuse; naive +299 accept / +301 refuse; a +03:00 offset equal to NOW+301 s refuse, NOW+60 s accept; an epoch int 1 d ahead refuse; far past / None accept. FUTURE_SKEW_SECONDS read at call time (patched 600: +500 s accepted). 422 VALIDATION_ERROR + zero client calls held by R2 and the killed M2/M3/O5. classify on the S18 card: +299 / +300 s fresh with that as_of; +301 s and +1 d none, 0 candidates. _past: +300 s kept; +301 s, garbage, None -> None. TRUE.
D17b: 045 (kb_products / kb_variants text pk; offers / images / specs / reviews / gaps uuid pk; view kb_offers_latest selects o.id) + 002 (search_logs id pk): every paged relation carries id; R1 asserts order id asc on every select op. Pinned clients measured: upstash-redis 1.7.0 Pipeline has exec() and a one-argument execute(command) that queues; redis-py 8.1.0 has no exec; the fallback picks exec on upstash (sync and asyncio) and execute on redis-py. TRUE.
D22c (1): the OFF literals (scs:5986-5987) equal base :5945 / :5947 and the golden; the flag read is the first try statement and per call (M4 killed); ON selects, normalisation and the write through the real behavior_service held by R2-R5; full_response is JSONB (migration 001) so the aliases are valid. TRUE.
D22c (2): deletion + git rm; corpus SHA pair equal; B3b suite green in the CI-order set. TRUE.
D22d: _read_by probe (id-ordered fake, 250 values, chunks of 600 / 1250 / 300 rows): 2150 rows, all distinct, requests (0,499),(500,999) | (0,499),(500,999),(1000,1499) | (0,499), each order id asc; cap 1000 -> 1000 "capped", last request (0,399). dropped = 6 on GR6. _render escapes TAB, DEL, 0x85, U+2028, U+2029, keeps a backslash, returns non-str unchanged; the three render sites edited. TRUE.

## Comm set (union rule re-derived independently: AST import closure of the six edited modules over app/ + scripts/ = 101 modules; tests naming a closure module or stem; the symbol list incl. GREEN's new symbols; app.main / TestClient users; the forced pins; CLAUDE.md readers; readers / walkers with an app / scripts / data path; helper importers; minus test_precommit_hook*)
Mine 703 vs GREEN's 699 (+ secret_scan alone). GREEN-only 5 (the 4 _render substring hits + test_m13_02_proxy_aware_ratelimit from the RED set). Mine-only 9 = test_secret_scan_static (run alone by GREEN) + 8 false positives of my broader reader rule (migration SQL readers 027 / 029 / 030 / 031, test_sqlfluff_config, test_skill_frontmatter, test_gitleaks_config (historical PR ranges), test_cohort_service (an open() spy)); none reads a changed file. NO MISSING FILE. Edited test modules: test_s81_g5_gate_rows is imported by the D22d RED file (in the set); test_variant_llm_hint_b3b has no importer.

## CLAUDE.md block and PR body vs the bytes
Block at CLAUDE.md:575-581 (heading + D16b, D17b, ENABLE_BEHAVIOR_PROFILE_REBUILD, D22c VARHINT-RETIRE, D22d rows + owner steps names-only) after the S81-G5 owner-steps bullet (574), before ## Tests (583); the :341 clause added after the S81-G5 clause; 0 non-ASCII added; no line holding both scoring_method and enum; every factual claim checked above holds. PR body 8,318 bytes; non-ASCII = only the 4-byte attribution emoji; the counts (60 nodes 26 / 34, 31 mutants with D22d-M7 equivalent, 946 + 3, 1161 + 3, the SHA pair, 691 + 4 + 5, 17 nodes, fences 13/14 with the four w37 nodes) match the logs; stated limits by id; owner steps names-only; [NATIVE READ] EMPTY.

## Findings
BLOCKING: none.
MAJOR: none.
MINOR (stated limits by default, LC-4):
- MIN-1 (test gap, ADV-O1 survived): no row drives cron_learning._read_by across more than one 100-value IN chunk; a regression that stops after the first chunk passes the RED, D22 and G5 files. GREEN's code is correct (multi-chunk probe above). Suggested L-D22d-4.
- MIN-2 (data, flip window): with ENABLE_BEHAVIOR_PROFILE_REBUILD ON, a comparison whose full_response is NULL or lacks category_used gives category_affinity a None key, stored as "null" (measured: {"null": 0.5, "fragrances": 0.5}); the spec failure table's "behavior_service maps it to its default bucket" is not true (c.get("category_used", "other") returns None for a present-None key). category_affinity has no reader in app/ today. v1 rows keep products under full_response.overview.products (migration 026), so the ON alias gives [] for them. Suggested L-D22c-6.
- MIN-3 (doc rendering): the S81-G7 heading (CLAUDE.md:575) follows the S81-G5 owner-steps list item without a blank line, so CommonMark renders it as a lazy continuation of that bullet (the G5 heading at 572 has a blank line before it). The final round's union can add the blank line; no reader depends on it.
- MIN-4 (unpinned edges, ADV-O2 / ADV-O4): DEL (0x7F) escaping is implemented but unpinned (R6 covers 0x09 / 0x85 / U+2029, R5 LF / ESC / U+2028); the dropped count's restriction to verdict == wrong rows is unpinned (GREEN's placement matches the spec).
Prove-nothing / equivalent rows: ADV-O3 (unobservable under OFF); D22d-M7 (R-G7-9); the mutant counts in the GREEN report / PR body are RED's prototype measurement (re-measured here on GREEN's bytes: 25 / 25 killed).

## Files (all under S81-G7_adv/)
correctness_REPORT.md, mutation_table_adv.md, mut_results.json, mut_results2.json, muts.json, muts2.json, mutate_adv.py, probe1.py, probe2.py, comm_adv.py, comm_adv.tsv, comm_adv.txt, units_off.log, units_on.log, ciorder.log, pins_readers.log, comm_01.log, comm_03.log, comm_20.log, gate_head.log, gate_head.json, head_lf_shas.txt.
