# S95-LG URL-WINNER-GUARD: FIX-2 report (Opus 5.5, 2026-11-14)

VERDICT: COMMITTED. HEAD a142d2f11fa536ae84f74079800db5042b966bf7 on feature/s95-url-winner-guard (parent baf675841b3070a85faf1e90e0a0dd4957392a42); one commit through the hook, no push. Time: first tool call 21:49, commit 22:18:05, report 22:2x (local).
Read in full at the start and again before this report: GATE_S95_LG.md (GL-1..GL-17, ADDENDA 1 and 2), S95_LG_UNIT_SPEC.md, adv/S95_LG_ADV_REPORT.md, fix1/S95_LG_FIX1_REPORT.md, s81-common.txt. Notes, logs, drivers: this folder (notes.md, *.log, *.out, mut.py, comm_chunk.py, edit_claude_md*.py, sweep.py).

## 0. Start state
- HEAD baf675841b3070a85faf1e90e0a0dd4957392a42, branch feature/s95-url-winner-guard, `git status --short` empty, no lock.
- Byte copies (copy_start.py): start_ues.py 8eca4929... (75965 B, CRLF 1643, bare LF 0, non-ASCII 18), start_CLAUDE.md 7110ee48... (789030 B), start_red.py 24ed90c0..., start_adapter.py d5b80198..., start_rolefix.py 3a67f214...; each git hash-object == its HEAD blob.

## 1. GL-17 rows FIRST (tests/test_s95_lg_url_winner_guard_fix2.py; the RED idiom: extract_from_url on ues, _resolve_pair_category on scs, generate_comparison on es, fragrance_gate=None; the REAL scorer and reconcile except where a row patches a failure; preconditions on the scorer's pick)
- G9 (RED): ON, page E BHD 45.0 vs page F AED 380.0 (equal specs, rating 4.5 / count 300); PRECONDITION the real scorer picks E (0), the model picks F (1) -> the verdict call == the base call, call counters on get_scoring_service / _display_product_names / reconcile_winner_prose / compute_scores / build_scores_summary / compute_tradeoff_pairs all 0, guard records == [(INFO, ues logger, '[URL_GUARD] skipped reason=currency_mismatch')], no WINNER_INDEX_MISMATCH, winner_index 1, body byte-equal (json.dumps) to the flag-OFF body.
- G9b x3 (PINs at HEAD: the guard already runs on these pairs): same_code BHD/BHD, padded_lower_code ' bhd '/BHD, missing_amount BHD 45.0 / AED None -> the call carries scores_summary + score_winner_index == the scorer's pick, that winner ships, no skip line.
- G10 x6 (RED): the lift refuses rating 0, 7.5, True, '4.5' and count True, -1 (that key absent from the scorer's view, the other key lifted, page F lifted in full; a spy on the REAL compute_scores records its input).
- G10b x3 (PINs at HEAD: HEAD lifts every non-None value): rating 5 / count 0, rating 0.1 / count 1, rating 5.0 / count 2 lifted unchanged (type kept).
- G11 x2 v1/v2 (RED): ON + ENABLE_WINNER_PROSE_RECONCILE, the real reconcile re-indexes (one WINNER_INDEX_MISMATCH) then deterministic_verdict_fields raises -> body byte-equal to the flag-OFF body, winner_index 1, comparison == the model's verdict.
- G11b (RED, added after the implementation to kill a shallow-snapshot mutant; proven RED at the HEAD module bytes, see section 3): a reconcile double re-indexes, edits two nested lists, raises -> body byte-equal to the flag-OFF body.
- G12a / G12b x2 / G12c (PINs at HEAD: HEAD's log arms are already correct; their job is coverage, killing M10 / M11): the scorer arm 'type=SyntheticScorerFault', the reconcile arm 'type=SyntheticReconcileFault' (compute_tradeoff_pairs raising; the template step raising), exactly ONE WARNING on the module logger, no exc_info, no exception text / name / host in any record; G12c a None scorer winner -> ONE 'type=TypeError' (GL-16), the base call, no reconcile, body == OFF.
- At HEAD baf67584 before any module edit (s95g-fix2-head-rows): 9 failed (G9 at :297, G10 x6 at :361, G11 x2 at :416; every one an AssertionError), 10 passed (the named PINs).

## 2. The implementation (app/services/url_extraction_service.py, Edit tool, CRLF kept; numstat vs baf67584 82/22)
- GL-13: NEW `_url_guard_liftable(top_key, value)`: never a bool; rating an int / float with 0 < v <= 5 (NaN / inf fail); review_count an int >= 0. `_url_guard_scorer_inputs` lifts a key only when the top-level key is absent / None AND the nested value passes (else the key stays absent).
- GL-12: NEW `_url_guard_currency_mismatch(products)` (pure, never raises): an amount is 'carried' exactly as the scorer reads it (scoring_service._compute_raw_scores: a truthy price.amount that float() accepts; TypeError / ValueError / OverflowError -> not carried); a str code -> .strip().upper(), a non-str code -> None; True only when both amounts are carried and the two codes differ. In compare_from_urls, inside `if url_winner_guard_enabled():` (the flag stays the first read; OFF reads no state): mismatch -> ONE `logger.info("[URL_GUARD] skipped reason=currency_mismatch")`, guard_scoring stays None (the base call, no keyword, no reconcile); else the unchanged scorer try / except.
- GL-14: in the reconcile branch a local `import copy`; `verdict_snapshot = copy.deepcopy(comparison)` is the FIRST statement of the try (before compute_tradeoff_pairs and reconcile_winner_prose); the except restores `comparison.clear(); comparison.update(verdict_snapshot)` when the snapshot exists (a failing deepcopy means the reconcile never ran), then the unchanged constant warning.
- GL-16: the guard comment now says a None scorer winner takes the scorer-failed arm (build_scores_summary raises a TypeError indexing the names; unreachable while compute_scores returns an int), never the reconcile's legacy branch.
- m6 NOT taken (optional): the positional guard_scoring reads stay byte-identical, so the E1-pinned lines (test_v09_url_caller_unchanged) do not move; E1 stays green (17 / 17).
- Final module: sha256 724a277e264c7b4cc44bf561772a833a38c876fd5919adf88446dfe5b254fbeb, 79307 B, CRLF 1703, bare LF 0, non-ASCII 18 (= start); blob 240bc489118d1793e6a2fc809ca1f9c9fd2302ee.

## 3. Mutation table (fix bytes; lock W/.qa-mutation.lock held by the driver mut.py, removed after; byte copy fix_ues_copy.py 724a277e...; after EVERY mutant restored sha 724a277e... match True; each run after waitfree.ps1, bound 600)
| id | exact edit | result | killed by (every failure an AssertionError) |
|---|---|---|---|
| HEAD | the module = the baf67584 bytes (start_ues.py), the FINAL fix2 file | 10 failed / 10 passed | G9, G10 x6, G11 x2, G11b (the RED profile; PINs pass) |
| M10 | reconcile warning also logs exc | KILLED (2) | G12b x2 |
| M11 | reconcile warning -> pass | KILLED (2) | G12b x2 |
| M13 | `if _url_guard_currency_mismatch(products):` -> `if False:` | KILLED (1) | G9 |
| M14 | mismatch ignores a missing amount | KILLED (1) | G9b[missing_amount] |
| M15 | codes not stripped / upper-cased | KILLED (1) | G9b[padded_lower_code] |
| M16 | mismatch always True | KILLED (22, fix2 + RED) | G9b, G10, G10b, G11, G11b, G12b, G12c, RED G1/G2/G5... |
| M17 | lift any non-None value (no validation) | KILLED (6) | G10 x6 |
| M18 | the bool refusal removed | KILLED (2) | G10[rating_bool], G10[count_bool] |
| M19 | rating bound `<= 5` -> `< 5` | KILLED (2) | G10b x2 |
| M20 | count bound `>= 0` -> `> 0` | KILLED (1) | G10b[rating_five_count_zero] |
| M21 | the clear / update restore -> pass | KILLED (3) | G11 x2, G11b |
| M22 | deepcopy -> dict(comparison) (shallow) | KILLED (1) | G11b |
| M23 | skip line INFO -> WARNING | KILLED (1) | G9 |

## 4. CLAUDE.md (the S95-LG block, edited in place from the working-copy bytes; edit_claude_md.py then 2 and 3)
- Each script asserted the start sha, the one heading, the block bounds (heading .. the line before `## Tests`), each replaced substring occurring exactly once, every untouched block line byte-equal, prefix (577744 B) and suffix (206361 B) byte-equal, CRLF only, non-ASCII 3904 -> 3904, no line containing `SESSION 81 unit (S81-07`.
- Lines changed (6 of the block's 9 text lines; numstat 6/6 vs baf67584, 10/0 vs base 731bcddf, still a pure insertion vs base): the heading (GL-1..GL-17 with ADDENDA 1 and 2); ON (the GL-12 skip with its INFO line; the GL-13 lift rule); Failure arms (the GL-14 deep-snapshot restore; the GL-16 None-winner wording); Tests (the fix2 file G9-G12); Canary (the skip-line count); Stated limits L-1..L-6 (L-1 reworded: the model's pick stands only on the scorer-failed and reconcile-failed arms and the cross-currency skip; L-5 cross-currency pairs keep the model's pick (GL-12); L-6 the m5 WINNER_INDEX_MISMATCH display-name limit).
- Final: sha256 ab33a3841e96c2168dc078fe345656926fd3ca0500aa88c2d0fa9c608ad66d32, 791174 B, CRLF; blob bd43889d48d821756bba9af0c57b0f853a0e5138.

## 5. Gates (waitfree.ps1 -OwnTagPrefix s95g- before EVERY pytest; every [netguard] line of the unit runs: blocked 0 attempt(s) from 0 node(s))
- [pyt] tag=s95g-fix2-head-rows start=2026-11-14 21:58:44 end=2026-11-14 21:58:47 elapsed=3s bound=600s status=FAIL rc=1 (9 failed, 10 passed: the RED proof at HEAD; [hermeticity] sentinel checked 19 test(s))
- [pyt] tag=s95g-fix2-early-rows start=2026-11-14 22:00:40 end=2026-11-14 22:00:43 elapsed=3s bound=600s status=OK rc=0 (19 passed)
- [pyt] tag=s95g-fix2-units start=2026-11-14 22:03:44 end=2026-11-14 22:03:50 elapsed=6s bound=1200s status=OK rc=0 (60 passed: RED 22 + adapter 2 + fix2 19 + role_fix 17; [hermeticity] 60)
- [pyt] tag=s95g-fix2-mutHEAD 22:05:30-22:05:33 status=FAIL rc=1 (10 failed, 10 passed); mutM10 22:05:41-22:05:45 FAIL; mutM11 22:05:45-22:05:48 FAIL; mutM13 22:05:49-22:05:52 FAIL; mutM14 22:05:53-22:05:56 FAIL; mutM15 22:05:56-22:06:00 FAIL; mutM16 22:06:00-22:06:04 FAIL; mutM17 22:06:05-22:06:08 FAIL; mutM18 22:06:16-22:06:20 FAIL; mutM19 22:06:20-22:06:23 FAIL; mutM20 22:06:24-22:06:27 FAIL; mutM21 22:06:28-22:06:31 FAIL; mutM22 22:06:32-22:06:35 FAIL; mutM23 22:06:35-22:06:39 FAIL (each bound=600s rc=1)
- ruff 0.16.5 --select E9,F63,F7,F82 --no-cache on the module + the fix2 file: All checks passed!; py_compile rc 0.
- Comm set at the fix tree: 137 files = red/comm_set.txt (135, sha 306abcc2...) + the adapter + the fix2 file, GREEN's chunks 0-4 and chunk 5 + fix2 (chunk files and comm_set_fix2.txt sha 1ea50b17... here); base record = red/base_record.txt (9 ids) REUSED (LC-6: same main 731bcddf; the two new files do not exist at base):
  - [pyt] tag=s95g-fix2-comm0r start=2026-11-14 22:08:28 end=2026-11-14 22:09:04 elapsed=36s bound=1200s status=OK rc=0 (764 passed, 1 skipped; hermeticity 765; netguard 9 / 3)
  - [pyt] tag=s95g-fix2-comm1 start=2026-11-14 22:09:10 end=2026-11-14 22:10:46 elapsed=96s bound=1200s status=OK rc=0 (867 passed; netguard 169 / 39)
  - [pyt] tag=s95g-fix2-comm2 start=2026-11-14 22:10:52 end=2026-11-14 22:12:55 elapsed=123s bound=1200s status=FAIL rc=1 (3004 passed, 2 errors = the two cold-tiktoken test_prompt_truth nodes; netguard 27 / 3)
  - [pyt] tag=s95g-fix2-comm3 start=2026-11-14 22:13:01 end=2026-11-14 22:15:03 elapsed=122s bound=1200s status=FAIL rc=1 (7 failed = test_r35_fixtures, the five s16 r27 hygiene nodes, test_b02_one_transaction_ascii_lf; netguard 24 / 9)
  - [pyt] tag=s95g-fix2-comm4 start=2026-11-14 22:15:09 end=2026-11-14 22:16:20 elapsed=71s bound=1200s status=OK rc=0 (1073 passed; netguard 73 / 25)
  - [pyt] tag=s95g-fix2-comm5 start=2026-11-14 22:16:25 end=2026-11-14 22:16:44 elapsed=19s bound=1200s status=OK rc=0 (646 passed = 624 + adapter 2 + fix2 20; netguard 20 / 12)
  - fix failing set (fix2_record.txt) == the 9 base ids exactly: comm -13 EMPTY (no NEW failure), comm -23 EMPTY; every netguard count equals the base record's.
- After the commit: [pyt] tag=s95g-fix2-units-head start=2026-11-14 22:20:49 end=2026-11-14 22:20:56 elapsed=7s bound=1200s status=OK rc=0 (61 passed: RED 22 + adapter 2 + fix2 20 + role_fix 17; [hermeticity] 61).
- Added-line sweep (sweep.py, patterns self-tested on run-time probes): 627 added lines, 0 non-ASCII, 0 hits.

## 6. The commit (GL-17)
- `git -C W add -- app/services/url_extraction_service.py CLAUDE.md tests/test_s95_lg_url_winner_guard_fix2.py` (rc 0; one informational LF / CRLF warning on the new LF file); staged numstat 6/6, 82/22, 538/0. `git -C W commit -F fix2/commit_msg.txt` (571 B ASCII LF; never --no-verify) 22:18:03-22:18:05 rc 0. Hook output, verbatim (commit_hook.out): `All checks passed!` / `[feature/s95-url-winner-guard a142d2f1] fix(s95): URL winner guard skips cross-currency pairs, validates the lift, restores on a failed reconcile` / ` 3 files changed, 626 insertions(+), 28 deletions(-)` / ` create mode 100644 tests/test_s95_lg_url_winner_guard_fix2.py`.
- Message: the GL-17 subject exactly; a 6-line body (GL-12 / GL-13 / GL-14 / GL-16 + the fix2 rows); the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Verified after: HEAD moved baf67584 -> a142d2f11fa536ae84f74079800db5042b966bf7 (parent baf675841b3070a85faf1e90e0a0dd4957392a42); `git status --short` EMPTY; `git status -sb` = `## feature/s95-url-winner-guard` (no upstream, nothing pushed); no lock file.
- `git show --stat HEAD` = 3 paths: CLAUDE.md 12 (+6/-6), app/services/url_extraction_service.py 104 (+82/-22), tests/test_s95_lg_url_winner_guard_fix2.py +538. `git diff --stat 731bcddf..HEAD` = exactly the six GL-17 paths (CLAUDE.md +10, ues 136, role_fix 75, RED +474, adapter +211, fix2 +538; 1439 / 5).
- Unchanged since baf67584 (HEAD blob == baf67584 blob): tests/test_s95_lg_url_winner_guard.py e25c5596eeba4dac13b0cbcb1d45651114b78fad, tests/test_s95_lg_url_winner_guard_adapter.py 159dcd400905ea45cc3ad943cb76980ac3c0d057, tests/test_s81_s07c_role_fix.py c34925fb14d3e5bece61a5473511008ceaad239b.

| path (committed in a142d2f1) | working-copy bytes | sha256 | HEAD blob |
|---|---|---|---|
| app/services/url_extraction_service.py | 79307 (CRLF) | 724a277e264c7b4cc44bf561772a833a38c876fd5919adf88446dfe5b254fbeb | 240bc489118d1793e6a2fc809ca1f9c9fd2302ee |
| CLAUDE.md | 791174 (CRLF) | ab33a3841e96c2168dc078fe345656926fd3ca0500aa88c2d0fa9c608ad66d32 | bd43889d48d821756bba9af0c57b0f853a0e5138 |
| tests/test_s95_lg_url_winner_guard_fix2.py | 22861 (LF, ASCII) | d990307e6e1d55b242fe06b087ffae166c0373df954007ea04550b5e8750a676 | 8c8b184cc3969955f717660395a5da33ff6261ac |

## 7. Deviations and assumptions (for the gate / the LC-2 re-verifier)
- D1 GL-17 'ONE commit of six paths': a commit records only changed paths, so a142d2f1 touches 3 of the six (the RED file, the adapter and role_fix needed no change; no ruling moved them); the branch diff vs base is the six paths.
- D2 G11b was added AFTER the implementation (to kill the shallow-snapshot mutant M22, which G11 cannot see: the real reconcile only rebinds top-level keys). Its RED proof is the HEAD-bytes swap row of section 3 (the baf67584 module bytes in place under the lock, the final fix2 file: G11b fails on an AssertionError; restored, sha match).
- D3 rows beyond the GL-17 minimum: G9b padded_lower_code and missing_amount (kill M15 / M14), G10b (boundary PINs, kill M19 / M20), G12c (the GL-16 None-winner arm as a PIN).
- A1 'carry a price amount' = the scorer's own reading (truthy + float()), so a 0 / '' / non-numeric amount counts as missing and the pair is guarded on its other signals (no raw cross-currency comparison happens then); the literal alternative `amount is not None` would skip such pairs instead. Chosen because the MAJOR's root cause is the scorer comparing two raw amounts.
- A2 a non-str currency code reads as None, so None vs 'BHD' counts as differing (skip: the amounts are not provably comparable); normalize_product_data always fills a code (raw, retailer or 'USD'), so this is unreachable on the extracted path.
- A3 GL-14's snapshot also covers compute_tradeoff_pairs (it is the first statement of the same try); compute_tradeoff_pairs never writes the verdict, so this changes no outcome.
- m6 not taken (optional); see section 2.
- The first comm chunk-0 run (tag s95g-fix2-comm0, 22:07:24, its log: 764 passed, 0 failed) lost its [pyt] status line (the driver printed the log, and pyt.py writes that line to stdout only); re-run once as s95g-fix2-comm0r (above), same result.
- Observation, no action (outside the six paths): .github/black-clean-paths.txt asks new .py files to be added; none of this unit's three new test files is on it (as FIX-1); CI's blocking black step reads only the list.

## 8. NOT MEASURED (by this round)
- The full jest suite and the client fences (no client-read literal moved; LC-7); no live, network, Railway or provider measurement; no adversary lens of my own beyond the mutation table (LC-2: the re-verifier reviews a142d2f1).

## 9. git -C W status --short (end)
(empty) - HEAD a142d2f11fa536ae84f74079800db5042b966bf7, branch feature/s95-url-winner-guard, no .qa-mutation.lock, nothing pushed.
