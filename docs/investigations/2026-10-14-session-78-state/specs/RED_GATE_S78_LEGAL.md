# RED gate S78-LEGAL (orchestrator, 2026-10-14 ~04:20 AST): PASS with one gate edit

## Input

- RED workflow: wf_a81e4977-88b. Report: `runs/s78_legal_red_wf_a81e4977.json`.
- Deviations and questions: `runs/s78_red_gate_input.md`.

## Re-measured by the orchestrator

- **Base run:** `[pyt] tag=s78-gate-base`, 24 failed and 4 passed. The 4 that pass are the guard pins R8, R19, R24 and M1.
- **Failure reasons:** every failure is an AssertionError. There are no collection errors.
- **False positives:** zero town-name hits over the RED prototype outputs, `scratchpad/s78red/proto_out`.

## Gate edit G9 (made by the orchestrator in the RED files)

The RED fixture stored a sha256 of the controller's home-town name. Town names are few, so the digest is reversible by enumerating Bahraini towns, and the repo is public. Two changes were made:

- **Fixture.** `home_town_sha256` was replaced by `bahrain_towns_latin`, a generic list of 48 Bahraini town and area names. It is public geography, not tied to anyone, and the controller's town is one entry among 48.
- **Test.** `_town_digests(fx)` now builds the digests from that list, and R2, R7 and R20 use it.

The node ids are unchanged. New sha256 values (from `sha256sum`):
- `tests/test_legal_s78.py`: see ledger 04:20
- `tests/fixtures/legal_s78.json`: see ledger 04:20

## Answers to the RED questions (binding for GREEN)

| ID | Ruling |
|---|---|
| G1 | The Q9 separate node is accepted. GREEN replaces the address at `test_abuse_detection.py:122` with `firstname.lastname@example.com`, or any example.com value that keeps `is_disposable` False and keeps the test's meaning. |
| G2 | The RED-drafted Arabic (changes_ar for LT5, s5_carveout_ar for LT10, the LT9 precedence bullet) is accepted. GREEN uses the fixture strings VERBATIM. Every new Arabic sentence goes on the native-review list in the PR body. |
| G3 | S77 D10 changes only through the updated P14-P16 constants. D10 must pass after GREEN. |
| G4 | d3c (n) changes per LT10. List it in the P-list with that reason. |
| G5 | The 52 collateral prototype failures are expected. GREEN adds POSTAL_ADDRESS_AR to COMPLETE_VALUES, to d3c ar_values and to every synthetic data set that needs it. After GREEN, every existing legal pin is green, except the deliberate P-list changes, each listed with its reason. |
| G6 | R7's exact AR interim equality is accepted. Any later AR re-wording edits the fixture string and the data together. |
| G7 | GREEN re-measures and updates ADDRESS_COUNTS in `SmartCompareApp/__tests__/landing.brand.s69.test.ts` and PRIVACY_PAGE_ADDRESSES in `tests/test_legal_disclosure_s77.py`. The worktree cannot run jest, so CI frontend-tests is the arbiter. |
| G8 | YouTube is never named in any served legal text, in either YOUTUBE_CLAUSE state. |
| G10 | GREEN must NOT edit `tests/test_legal_s78.py` or `tests/fixtures/legal_s78.json`. If a RED assertion is wrong, STOP and report with evidence. |
| G11 | The effective date is 2026-10-14 in every one of the twelve anchors. Use a single source wherever the machinery allows, and list every place that holds a literal. |

### G12. Gates GREEN must pass and paste

1. The RED file: 28 passed.
2. Every legal pin file, green.
3. The comm set from spec section 6 plus the 7 source-scanning files (M7), in chunks of at most 25, with branch-only-NEW empty against a base worktree at 4772d492.
4. ruff `E9,F63,F7,F82` and py_compile on every changed `.py`.
5. `scripts/render_legal_landing.py --check`, rc 0.
6. `scripts/fill_in_legal.py --dry-run` after the fill: 0 lines.
7. A personal-data scan of every changed file and of the final diff. It runs in memory, compares against the base address, its components and digit runs, the personal emails and the phone, and prints counts only: 0 hits.
8. A mutation check: delete each fix below and show that a RED node turns red.
   - the UA change;
   - the interim postal value;
   - the Apple section item 10;
   - the carve-outs;
   - the providers-on-request sentence;
   - the anchors date.
