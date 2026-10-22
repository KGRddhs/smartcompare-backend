# D03 fix round 1: re-verifier report (correctness lens; engineering checks included as the rulings ask)

- Unit D03 DENY-AND-GUARDS (`ENABLE_DATA_GUARDS_V2`). Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-d03`, branch `feature/s81-d03-deny-and-guards`.
- HEAD verified at start (23:51 AST) and end (01:01 AST): `53bf18a7aedc154ad85a54e3ac474fd5f895ff13`; `git status --short` EMPTY at both points; the unit worktree was never edited.
- Model: Opus 5.5 (claude-opus-5-5).
- RED file: frozen blob at 5244f716 = `ae8fffc7ffe50205af9170a82f1de22ca38e629482b1afc93bf1c0181610449c` (MATCH); fix-round file (working copy AND 53bf18a7 blob) = `16390347e3c1e408dc29f2f2e2bbf0b28b24a2eaca839fde88dfdc1ba7494787` (MATCH, as the fix agent recorded). AST compare (`reverify/red_ast_compare.py`): the first 155 top-level statements of the new file are AST-identical, in order, to the 155 of the frozen file (black is formatting only); 34 statements appended from line 1762 (12 test functions, helpers, constants, `import logging`); no old row changed or missing.
- Probes and mutants ran ONLY in my detached scratch worktree `<scratchpad>/D03_fix1_adv` at 53bf18a7 (the two LF files byte-copied from the unit worktree; all 11 diff files sha-identical to the unit worktree before and after every mutant: `reverify/sha_start.txt`, `reverify/sha_end.txt` ALL_SAME). `.qa-mutation.lock` held only during the mutation batches, removed. Scratch worktree removed with `git worktree remove --force`; `git worktree list` no longer shows it. No pytest of mine left running. No .env read or copied.
- Notes and raw evidence: `<scratchpad>/D03_fix1/reverify/` (probe.json, probe_summary.txt, probe2.json, mut_res_b1..b3.json, mut/*.log + *.xml, bytecheck.out, red_ast_compare.out, pyt_lines.txt, every chunk list and log).

## Verdict: SOUND (0 blocking, 0 major, 5 minor)

## Runs (every [pyt] line; summary after ::)

```
[pyt] tag=d03rv-unit-off start=2026-10-23 00:08:18 end=2026-10-23 00:08:38 elapsed=20s bound=600s status=OK rc=0 :: 288 passed; hermeticity 288; netguard 0
[pyt] tag=d03rv-unit-on start=2026-10-23 00:08:47 end=2026-10-23 00:08:52 elapsed=5s bound=600s status=OK rc=0 :: 288 passed (ENABLE_DATA_GUARDS_V2=true for the runner only); hermeticity 288; netguard 0
[pyt] tag=d03rv-probe1 start=2026-10-23 00:10:39 end=2026-10-23 00:10:42 elapsed=4s bound=600s status=OK rc=0 :: MAJ-1 closure probe (scratch file, removed)
[pyt] tag=d03rv-mut-R0-basecode-5244f716 ... status=FAIL rc=1 :: 18 failed / 270 passed, every failure AssertionError (RED step re-measured)
[pyt] tag=d03rv-mut-V01..V23 (23 lines, table below)
[pyt] tag=d03rv-probe2 start=2026-10-23 00:24:38 end=2026-10-23 00:24:42 elapsed=4s bound=600s status=OK rc=0 :: stash / W4-7 replay / log-count probe
[pyt] tag=d03rv-ci-order start=2026-10-23 00:28:30 end=2026-10-23 00:30:37 elapsed=127s bound=1200s status=OK rc=0 :: 81 files sorted: 2555 passed, 1 skipped, 6 deselected; netguard 28 nodes, all in tests/.network_attempt_baseline.txt; hermeticity 2556
[pyt] tag=d03rv-on-00 start=2026-10-23 00:31:52 end=2026-10-23 00:32:33 elapsed=42s bound=1200s status=FAIL rc=1 :: ON: 1 failed = tests/test_fragrance_content_quality.py::test_review_praise_no_interior_per_domain_artifact (named ON-only red), 655 passed
[pyt] tag=d03rv-on-01 start=2026-10-23 00:32:38 end=2026-10-23 00:33:53 elapsed=75s bound=1200s status=FAIL rc=1 :: ON: 1 failed = tests/test_retailer_quotes_from_reviews.py::TestRetailerQuotesGraceful::test_bare_numeric_citation_also_mapped (named ON-only red), 1400 passed, 4 deselected
[pyt] tag=d03rv-on-02 start=2026-10-23 00:34:08 end=2026-10-23 00:34:24 elapsed=16s bound=1200s status=OK rc=0 :: ON: 247 passed
[pyt] tag=d03rv-off-00 start=2026-10-23 00:35:03 end=2026-10-23 00:35:26 elapsed=23s bound=1200s status=OK rc=0 :: 594 passed, 1 deselected; netguard 5 nodes (baseline)
[pyt] tag=d03rv-off-01 start=2026-10-23 00:35:33 end=2026-10-23 00:38:00 elapsed=147s bound=1200s status=OK rc=0 :: 1278 passed, 9 skipped, 10 deselected, 35 xfailed; netguard 20 nodes (baseline)
[pyt] tag=d03rv-hook-collect start=2026-10-23 00:38:46 end=2026-10-23 00:38:53 elapsed=7s bound=300s status=OK rc=0 :: 327 hook nodes collected
[pyt] tag=d03rv-hook1 start=2026-10-23 00:39:05 end=2026-10-23 00:48:28 elapsed=563s bound=560s status=TIMEOUT rc=124 :: tests/test_precommit_hook.py: 28 of 62 passed, 0 F, at the bound
[pyt] tag=d03rv-hook1-rerun start=2026-10-23 00:50:02 end=2026-10-23 00:59:24 elapsed=562s bound=560s status=TIMEOUT rc=124 :: re-run once: 28 of 62 passed, 0 F, at the bound -> NOT MEASURED
```
The 37 lines verbatim: `reverify/pyt_lines.txt` (from the harness ledger). One pytest of mine at a time throughout.

Sets: ci-order = the fix agent's 81-file list (`D03_fix1/ci_order_set_f1.txt`: GREEN 48 + the 38-file Shopping set + test_ci_gates), contains every shop-set file. ON chunks = shop set (38) UNION every test referencing review_service (17) = 54 files, chunks of 25/25/4. OFF chunks = the 34 CLAUDE.md readers UNION the 10 source-scanning pins (test_model_config, _enforced, prompt_fence, u3c, start_command, migration_index_predicate, openai_key_log_hygiene, sentry_channels_u8d, ci_gates, behavior_dimension_translation) UNION the 12 review_service importers outside the ci-order set, minus the ci-order files = 46 files, chunks 25/21. Every review_service importer and every shop file is in the fix agent's 410-file comm set (re-checked). The three app/-path readers outside that set (test_prompt_truth, test_s79_b3b_apple_revoke, test_scoring_calibration_bundle_c) read only unedited files. `.github/black-clean-paths.txt` readers: test_ci_gates (ran), test_precommit_hook (writes its own tmp allowlist; never reads the repo file), .githooks/pre-commit and ci.yml.

## MAJ-1 / MAJ-E1 closure, measured with the REAL functions (probe1, probe2)

Grid: D03 OFF/ON x W4-1 OFF/ON x W4-2 split OFF/ON (with W4-1) x ask BHD/AED x row {Fragrantica `/bh-en/` link, plain fragrantica link, parfumo link + source Parfumo, source-only denied (google.com listing link + source Fragrantica), source-only denied (allowed link + source Basenotes)}, single-row pool and mixed pool (+ an allowed 60 BHD / 600 AED row).
- D03 OFF, W4-1 ON, BHD, `/bh-en/`: `Fragrantica|www.fragrantica.com|45.0|converted_usd` with evidence `[False, ['global_tier']]` (= base 5244f716, the adversary probe3 shape).
- D03 ON, every W4-1 / W4-2 state, both asks, every denied row shape: single-row pool -> None; mixed pool -> `Perfume Shop BH|bh.perfume-shop.test|60.0 (600.0)|local_bhd`. Evidence helper -> `[False, ['denied_host']]` for every denied link on every ask (a listing link keeps `listing_url`, an allowed link `[True, []]`).
- Stash (`_seed_shortcircuit_candidates`, floor-clearing prices 55/56/60 BHD): D03 OFF seeds all 3 rows (both W4-1 states); D03 ON seeds only the allowed row, no `[DATA_GUARDS_V2]` line.
- W4-7 `_count_identity_matched_rows` over the same pool: OFF 3, ON 1, 0 D03 lines (the replay filter covers logger `app.services.price_service`).
- Door: two calls ON -> exactly two lines `[DATA_GUARDS_V2] shopping rows dropped (denied host) count=2 by=link host=www.fragrantica.com` (one per call; matches stated limit 15); OFF 0 lines.
- The shared `_shopping_items_cache` list keeps its length after the drop (2 of 2).
Verdict: MAJ-1 = MAJ-E1 CLOSED for all three ruling sites, both W4-1 states, both asks.

## Mutation table (23 mutants on sha-verified byte copies, exact-once edits, whole unit file, bound 600; 22 KILLED by AssertionError, 1 SURVIVED; every restore sha-identical)

| id | edit | result | killed by |
|---|---|---|---|
| R0 (RED step, not a mutant) | price/review/scs/deny_hosts at their 5244f716 bytes | 18 failed / 270 passed, AssertionError only | f1_1a x4, f1_1b x4, f1_1c, f1_1d x4, f1_1e, f1_4a x2, f1_4b, f1_6 (exactly the 18 new RED nodes; the 20 new PIN nodes green at 5244f716) |
| V01 (F1-1) | front-door drop disabled | KILLED (5) | f1_1a x4, f1_1c |
| V02 (F1-1) | evidence-helper deny disabled | KILLED (4) | f1_1b x4 |
| V03 (F1-1) | stash drop disabled | KILLED (5) | f1_1d x4, f1_1e |
| V04 (F1-1) | door drop moved after the W4-1 evidence rule (per candidate) | KILLED (1) | f1_1c |
| V05 (F1-1) | `_shopping_row_denied` ignores the source name | KILLED (10) | f1_1a, f1_1c, f1_1d, f1_1e |
| V06 (F1-1) | `_shopping_row_denied` ignores the link | KILLED (10) | f1_1a, f1_1c, f1_1d, f1_1e |
| V07 (F1-1 OFF) | door drop ungated | KILLED (8) | f1_1p x8 |
| V08 (F1-1 OFF) | evidence deny ungated | KILLED (8) | f1_1p x8 |
| V09 (F1-1 OFF) | stash drop ungated | KILLED (8) | f1_1p x8 |
| V10 (F1-1) | drop mutates the input list in place | KILLED (4) | f1_1a x4 |
| V11 (F1-1 log) | log carries the full URL | KILLED (1) | f1_1c |
| V12 (F1-1 log) | door drop silent (log=False) | KILLED (1) | f1_1c |
| V13 (F1-1 log) | the stash logs too (log=True) | SURVIVED (288 passed) | - (MIN-RV-3) |
| V14 (F1-2, A9) | `_registrable_label` labels[-3] -> labels[-2] | KILLED (1) | f1_2 |
| V15 (F1-3, D6) | `collect_retailer_ratings` deny skip after `seen.add` | KILLED (1) | f1_3 |
| V16 (F1-5, G3) | ON piggyback without `.strip()` | KILLED (1) | f1_5 |
| V17 (F1-6) | by-name import binding of `_is_valid_image_url` in scs | KILLED (1) | f1_6 |
| V18 (F1-4) | quotes deny back to `is_denied_host(<netloc domain>)` | KILLED (2) | f1_4a x2 |
| V19 (F1-4) | attribution deny back to `is_denied_host(<netloc domain>)` | KILLED (2) | f1_4a x2 |
| V20 (F1-4) | backslash rule removed | KILLED (2) | f1_4a[backslash], f1_4b |
| V21 (F1-4) | `is_denied_url` reads the netloc | KILLED (1) | f1_4p |
| V22 (F1-4) | backslash rule over the whole URL | KILLED (1) | f1_4p |
| V23 (F1-4) | label rule over the netloc without the backslash condition | KILLED (2) | f1_2, f1_4p |

## Engineering checks (measured)
- ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on the 9 D03 Python files: All checks passed!; py_compile clean (pycache prefix in my notes folder). Wider F401/F811/F841 on the 5 fix-round Python files: 28 at 5244f716, 28 at HEAD.
- black 26.5.1 (venv, the CI pin): the exact CI command over `.github/black-clean-paths.txt` (23 paths incl. the two new ones): 23 files would be left unchanged, rc 0.
- Bytes (`reverify/bytecheck.out`): price_service / review_service / scs / black-clean-paths / CLAUDE.md working copies CRLF with 0 bare LF; bytes > 127 identical at the 5244f716 and 53bf18a7 blobs and the working copy (CLAUDE.md 3961, price_service 5590, review_service 251, scs 3006, black-clean-paths 15); deny_hosts.py and the RED file LF, 0 bytes > 127; `git diff --check` clean; 1161 added lines: 0 hits for @gmail, +973, 8-digit runs, sk-, AKIA, xox, JWT, PEM, credentialed URL; 0 non-ASCII added lines.
- No test patches the removed scs name `_is_valid_image_url` or `review_service.is_denied_host`; no local name shadows the new scs `image_service` module binding.
- MIN-E8: DEFECT_LEDGER.md carries the D03, D03b, D03c, D03d rows (lines 7-10).

## CLAUDE.md row and PR body, sentence by sentence (bytes = the 53bf18a7 CLAUDE.md row and `D03_fix1/PR_BODY.md`)
TRUE as measured: 288 nodes (161 RED = 143 + 18, 127 PIN/GUARD = 107 + 20); the 18 fail at 5244f716 on AssertionError only; item 9 (drop before currency / evidence / short-circuit, new list, cache untouched, both W4-1 states, every ask, denied-only pool -> no price, `denied_host` before every rung, one host-only line per extraction call, stash silent, W4-7 replay filters the line and stops counting the row); item 4 (hostname through `is_denied_url`, userinfo and backslash); item 6 (module attribute, stored stripped); flag-OFF list (probe3 shape `converted_usd` / `global_tier` under W4-1 ON and `local_bhd` under W4-1 OFF, cheapest denied row wins, stash seeds every row, userinfo link attributed by its netloc); limit 5 (no fetch and no label path remains for the registry_tier None: door, stash, chokepoint; the other `registry_tier == "global"` refusals at price_service `_is_genuine_bh_candidate`, scs :2170 and :2913 guard fetched candidates or the harvest, all behind the chokepoint); limits 9, 11-15; the mutation, CI-order, pin-group, Shopping-set, comm and CLAUDE.md-reader figures match the fix agent's [pyt] lines (comm 410 files: 18463 passed / 2 failed = the two .pre_impl_failures page_scraping nodes, summed from the 17 chunk lines); the five deny_hosts mutants were re-run on the post-black bytes; MIN-E1, E2, E3, E4, E5, MIN-4, MIN-6, MIN-7 wording present.
Inaccurate or incomplete: see MIN-RV-1 (limit 2 omits a prompt) and MIN-RV-2 (limit 14 names only the backslash differential). No false sentence about the fix-round behaviour found.

## Previous round: every MAJOR and MINOR
- MAJ-1 (correctness) = MAJ-E1 (engineering): CLOSED (F1-1; measured above; V01-V13).
- MIN-1 (A9): CLOSED (f1_2; V14 KILLED). MIN-2 (D6): CLOSED (f1_3; V15 KILLED). MIN-3 (userinfo): CLOSED (f1_4a; V18/V19 KILLED). MIN-4 (Salvatore): RECORDED (limit 13, canary pairs, D03d). MIN-5 (G3): CLOSED (f1_5; V16 KILLED). MIN-6: CLOSED (wording in the row, PR body, deny_hosts docstring). MIN-7: RECORDED (follow-up in the row and the PR body). GREEN Q1: ACCEPTED as limit 6. The X19 template note: RECORDED as an orchestrator-script item (scripts/wf_unit_green.js), no unit bytes involved.
- MIN-E1: CLOSED (cited by name). MIN-E2: CLOSED (two literal tuples). MIN-E3: CLOSED (Basenotes). MIN-E4: CLOSED (limits 11 and 12; spec L8 in limit 3). MIN-E5: CLOSED (equivalent by ruling, stated). MIN-E6: CLOSED (black clean, both files allowlisted, CI command green). MIN-E7: CLOSED for the backslash shape (f1_4b, V20-V23; limit 14); residual differentials = MIN-RV-2. MIN-E8: CLOSED (ledger rows exist). MIN-E9: CLOSED (f1_6; V17 KILLED).

## MINOR (new this round; none blocks)
- **MIN-RV-1 (scope truth, pre-existing, not a fix-round regression):** limit 2 and the DEFECT_LEDGER D03c row name the specs / reviews / Tier-3 image prompts only. The Tier-2 GPT organic price prompt (`structured_comparison_service`, `extract_price(brand, name, variant, region, search_context)` over `search_price_organic`, about :8558) also receives denied-host organic text, and its OUTPUT retailer / url is labelled `local_bhd` / `converted_usd` by retailer presence alone (no deny check, no registry_tier read, so D03 does not make it worse in either flag state). A GPT-named Fragrantica retailer would ship as a price source. Practically unreachable (the banned sites sell nothing). Recommend: add this prompt to limit 2 and to the D03c scope (input filter + an output check on `price["retailer"]` / `price["url"]`).
- **MIN-RV-2 (stated-limit completeness):** the conservative authority rule covers the backslash only. Measured with the real `is_denied_url`: `https://%66ragrantica.com/x` False and `https://<fullwidth f>ragrantica.com/x` False, while a WHATWG parser percent-decodes and IDNA-maps both hosts to fragrantica.com; a tab inside the host is True (urlsplit strips it). Recommend one clause in limit 14: "percent-encoded and IDNA-mapped hosts are not normalised".
- **MIN-RV-3 (prove-nothing gap, log volume only):** mutant V13 (the stash also logs the drop line) survives all 288 nodes, so "the stash is silent because the front door logged the same pool" is unpinned. One assertion in f1_1d / f1_1e (`[DATA_GUARDS_V2]` absent from caplog) closes it.
- **MIN-RV-4 (pre-existing scope edge, record only):** denied Shopping rows still reach `cross_validate_specs_with_shopping` (spec `verified` marks) and the fact-check price median, which read `_shopping_items_cache` directly; no display surface, the deny_hosts docstring scopes its promise to paths that consult the module. A follow-up line in the row would make the boundary explicit.
- **MIN-RV-5 (ruling text):** RULINGS_FIX1_D03 names `tests/test_shopping_discovery_url_split.py`, which does not exist; the W4-2 pins live in `tests/test_shopping_price_not_self_pending.py` (dca64e77), which is in the 38-file Shopping set and in my ON and CI-order runs. No gap.

## Deviations
1. Hook test files: bound 560 s (below the brief's 1200-1800) because a foreground tool call is capped at 600 s and the brief forbids background pytest; at about 20 s per node even on an otherwise idle box (node -e 0 = 0.9 s), tests/test_precommit_hook.py reached 28 of 62 nodes (0 F) in both runs. Re-run once per the TIMEOUT rule (the re-run shared the box with a sibling session's gate, which started meanwhile) -> NOT MEASURED. The other three hook files (265 nodes) were not started (about 90 min at the measured rate).
2. 23 mutants instead of the ten the fix ruling asks for (one or more per fix).

## NOT MEASURED
- The four pre-commit hook test files (two TIMEOUT [pyt] lines above for test_precommit_hook.py; the other three files not run). Relevance: `.githooks/pre-commit` is unchanged; test_precommit_hook.py builds its own tmp-repo allowlist and never reads `.github/black-clean-paths.txt`; the hook's black step reads the allowlist, and black --check over that allowlist is clean (measured). The committed bytes passed the hook at commit time (fix agent).
- The full 410-file comm set at HEAD and at base (the fix agent's 17 chunks; I re-ran the CI-order set, the Shopping and review sets ON, and the CLAUDE.md readers + source-scanning pins OFF only).
- pins1 / pins2 (the fix agent's; their files overlap the CI-order set).

## Questions for the orchestrator
1. MIN-RV-1: widen D03c (and limit 2) to the Tier-2 GPT organic price prompt and its output retailer / url, or rule it out of scope?
2. MIN-RV-2 / MIN-RV-3: fold the one-clause limit and the one-assertion pin into the PR before merge, or record them as follow-ups?

## Files written (all in my notes folder; nothing in the unit worktree)
`<scratchpad>/D03_fix1/REVERIFY_REPORT.md` (this file) and `<scratchpad>/D03_fix1/reverify/` (shacheck.py, red_ast_compare.py, mutate.py, mutants.json, mut_b1..b3.json, mut_res_b1..b3.json, mut/, mutbak/, test_zz_d03_rv_probe.py, test_zz_d03_rv_probe2.py (scratch copies removed with the worktree), probe.json, probe2.json, probe_summary.txt, summarize_probe.py, bytecheck.py, bytecheck.out, red_ast_compare.out, sha_start.txt, sha_end.txt, the chunk lists, every log, pyt_lines.txt).

## git status
- `sc-s81-d03`: `git status --short` empty at start and end; HEAD 53bf18a7aedc154ad85a54e3ac474fd5f895ff13.
- Scratch worktree: removed.
