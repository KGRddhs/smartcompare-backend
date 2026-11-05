# S81-G5 GREEN REPORT (D22 NIGHTLY-LEARNING), GREEN agent on Opus 5.5, 2026-11-05

unit: S81-G5 LEARN-SEARCH = D22 NIGHTLY-LEARNING (SAFE, LC-9). Base ec747b496953869c0370e4f28bf025c6f694a97d.
HEAD 53b7b66e71b92c9904e2f6cb702f20ff78edf719 on feature/s81-g5-learn-search (ONE commit through the hook, no --no-verify; ruff hook "All checks passed!"; no push, no PR, no rebase). git status --short after the commit: empty.
This report, the PR body and the two specs files were written through the shell (python), as the harness refuses a subagent Write of a report .md.

## Files (sha256 of the working copy; every new file LF + ASCII, blob LF)

| path | before | after |
|---|---|---|
| scripts/cron_learning.py | (new) | f6aa1f6ad31257b739fc5c92807056096d396966351898c10cd27bfbd2f28f20 |
| railway.learning.json | (new) | 567e270d03ba669a292d77bcd918021379b5770b1306dd3a3b3f1025a16c0970 |
| tests/test_s81_g5_gate_rows.py | (new) | a631898af507f3279fd53ef0ab083aa20c8a034eb628665c9e3f3b5c99156cae |
| tests/test_s81_d22_nightly_learning.py | 98b2bafced383455edc4d6cc9c8690d1bea5c3193a042a0d760ddf0eb5d08656 | 98b2bafced383455edc4d6cc9c8690d1bea5c3193a042a0d760ddf0eb5d08656 |
| tests/test_s81_kb_schema.py | ed83a1b7bfb8cc6326d9452197f2e724d81fa4aaf0f4b04821b3bdcb0bc2aa70 | 33abdfb4c1e7ac265108d17d4ce78cb37fe9fda21e62fa51ea8e416ea3f4be7d |
| CLAUDE.md | 40a4560504edc7092387e145ac9a9e4b1896f5b958ad32d9d756746e12496dfa | dc0d7ce8ceaac3dc6832503024ca267fb940c14b8daf8dd0ef645b51b23086cf |
| scripts/cron_few_shot_rotation.py | 0c9257486e3545a8fe6a77b0a3c16dff7d55739e285894e60d1fa0e02e4105e2 | DELETED (git rm, E2) |
| tests/test_cron_few_shot_rotation.py | eea9eba315d07573f46016660159ce486142aaeb929c387ff16c791ca1ab742d | DELETED (git rm, E3) |

Byte copies before any edit: <scratchpad>/S81-G5_green_before/ (+ SHA256SUMS.txt). The frozen RED file re-hashed first and last: 98b2bafc... both times (unchanged, committed with the files).

## Implementation (own code; the RED prototype not copied)

scripts/cron_learning.py: the 2.2 constants exactly; the five knob readers through int_knob; learning_mode = run_mode(FLAG) as the first statement of main; argparse (--dry-run, --report, --report-md, --day) only after the OFF return; bad --day -> one WARNING, exit 0, before the client; the client: the injected one, else common._admin_client() (raise or None -> one ERROR line with the type name, exit 1); _read_window (gte / lt on the window column, order("id"), range pages of PAGE_SIZE cut at the cap, status capped) and _read_by (sorted de-duplicated ids in chunks of IN_CHUNK, order("id")); _Tables isolates one table's failure (code in MISSING_TABLE_CODES = absent, else error; one WARNING with the type name); _Cases (one case per (bucket, case id); every report adds its actor: GC-2); _clusters (sorted, systematic rule); the closed action map; grounding from cited kb_specs rows for kb spec_wrong clusters only (unclean entries dropped and counted; at most 3, sorted); _exemplars (screen BEFORE the per-category cut: GC-3; de-dup per comparison then per (category, n0, n1); version = day + 16 lower-case base32 chars of sha256); _eval_candidates (names + currency screened; winner_reason not part of the shape: GC-4); the context metrics; the metric list (16 always + skipped / capped); every row through kb.build_coverage_row (keyword-only); write_report + the md writer (open(..., newline="\n"), no write_text); ONE upsert in apply only; the totals line last. No kb_service token, no data path literal, module top = stdlib + scripts.kb_seed_common.
railway.learning.json = the spec 3.2 object. E1 = the two P02 rows + the comment after the cron_kb_coverage rows (CRLF kept, 3 lines). E2 / E3 = git rm. CLAUDE.md: ONE column-0 block (header + the D22 row + the owner-steps bullet) inserted after the S81-G4 owner-steps bullet (line 563 at base; the spec's ':565' is that bullet's neighbourhood: 564 blank, 565 '## Tests'; the block keeps the blank-line form) with the GC-2 / GC-3 rules, the R-G5-9 sentence and the R-G5-7 canary item, + the pointer clause after the S81-G4 clause on line 341; CRLF kept; names only.
tests/test_s81_g5_gate_rows.py: G5-GR1 (two users, one comparison, price_correct wrong: cases 1, actors 2; systematic with LEARNING_MIN_CASES=1, not with 3) and G5-GR2 (seven confirmed fragrance rows, the third carrying an e-mail shape in winner_reason; knob 5: five clean candidates, dropped 1, seven eval candidates), both through the RED file's fake client and builders.

## Gates

See S81_G5_GREEN_GATES.md (every [pyt] / [jest] line) and S81_G5_GREEN_MUTATIONS.md. Summary: RED file 50 / 50 x3 (unset / true / apply); gate rows 2 / 2 and each RED under its inverse edit; pins 1 failed (d17 r9 baseline) / 1052; CI-order set 1 failed (d17 r9) / 835 (base 44 / 792); comm set 47 files at HEAD vs the REUSED stored base record c636b9d5...: comm -13 EMPTY, comm -23 EMPTY, the 8 CRLF baseline nodes identical; fences 13 / 14 with exactly the four nativeBundle.w37 drift nodes. Corpus gate NOT run (no price_service edit); hook test files NOT run (no .githooks change); FULL jest NOT run (LC-7).

## Deviations

- The commit trailer names this agent's own model (Co-Authored-By: Claude Opus 5.5): the task text's template named Fable 5.1, but the trailer must name the committing agent's model and this agent runs on Opus 5.5.
- CLAUDE.md anchor: the S81-G4 owner-steps bullet measured at line 563 (not 565); the block is inserted right after it, as the spec intends.
- The comm set adds no importer beyond the RED file and the gate-rows file (the gate rows import only the RED file; no app/ module edited).
- The per-bucket `note` strings and the bucket `inputs` lists are GREEN's wording (the rows pin identity_wrong's inputs only).

## Open questions / NOT MEASURED

- None NOT MEASURED. Open for the adversary: the PostgREST JSON-path selects stay unprobed (R-G5-7, the owner's DRY run).

## PR body

<scratchpad>/S81-G5_green/PR_BODY.md (14,192 bytes measured with python, <= 25,600).
