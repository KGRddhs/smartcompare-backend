# B3 FIX ROUND 1 REPORT: VISION-IDENTITY-V2 (ENABLE_VISION_IDENTITY_V2)

- Unit B3, flag ENABLE_VISION_IDENTITY_V2 + knob VISION_TIMEOUT_SECONDS. Worktree
  C:/Users/SynAckITPC/Documents/AI/sc-s80-b3, branch feature/s80-b3-vision-identity-v2.
- Start: HEAD 764d44162dd83563dc5c9aa930dcb9c192f35f89 verified, `git status --short` empty, no
  .qa-mutation.lock; RED file sha256 36b78a404deefbc4fbea66b2d75574f203346a8e53550a3ddf04d3550e4af15e.
- End: HEAD 7b1e3ecf81ef2bb24ce08e84d89c0069f98b386a (one commit through the pre-commit hook:
  "All checks passed!"), `git status --short` empty, no lock. Not pushed, not rebased, no stash.
- Window 2026-10-20 09:31 -> 10:14 AST. Agent model: claude-opus-5-5.
- Inputs read: s80-common.txt (incl. the 2026-10-20 addendum), PLAN_S80 sections 0-1,
  RULINGS_BATCH1 (B3), GATE_B3, B3_UNIT_SPEC 2.6 / 4.2 / 7 / 8, B3_GREEN_REPORT, both adversary
  reports, RULINGS_FIX1_B3 (read again before this report), PR_BODY.md, the CLAUDE.md row.
- No .env read, no secret printed, no network, no production probe; flag state not read (a new
  name). No personal values (synthetic ids and product strings only).

## Files (final sha256 of bytes on disk)

| file | change | sha256 |
|---|---|---|
| tests/test_s80_b3_vision_identity_v2.py (RED, frozen) | +352 / -0 (append-only; the old 65,236 B are a prefix of the new 80,670 B; LF; 0 bytes > 127) | e8b2c9c109679a0f4581c6c5441af000487f04158c1349aa0f99ee98c82f8642 |
| CLAUDE.md | 2 / 2 (lines :474 header and :475 row only; CRLF kept, 0 bare LF; high-byte count 3979 before and after) | 48643ee836ceb16baf18b315c2de04dcb88ce20b8efdab7d11fe23928ab7c534 |
| <scratchpad>/B3_green/PR_BODY.md (not in the repo) | amended F3-2..F3-5 + fix-round section; LF; the only 4 bytes > 127 are the mandated trailer emoji | 45bdd56776318de2d6cb54f89522e04b83382ca0b2b4cf542fd1918340cc8ecd |
| <scratchpad>/B3_fix1/comm_head_list_fix1.txt | GREEN's 248 + tests/test_price_fallback_may_decline.py = 249 | 238a3d035a427283110f02fb928a41664b92b190bd56f3be5ad83c7bf2eb1ccc |

No production file changed (app/ untouched at the fix HEAD: `git diff 764d4416 HEAD --numstat` lists
only the two files above).

## F3-1 PIN rows (26 nodes appended; every row above the banner byte-identical)

| row | nodes | pins | kills |
|---|---|---|---|
| test_XB1_non_delivery_exits_never_read_preferences | 8 (refusal_503, none_content_503, expiry_503, bad_request_500, length_action_error, moderation_blocked, zero_products_action_error, need_second_product) | flag ON, signed in, prefs completed, metering + envelope ON: the exit is the expected one, identify is the only event, prefs.calls == [], no compare, refunds == consumes | XB1, BM1 |
| test_XB1b_delivery_reads_preferences_once_after_identify | 1 | events == [identify, prefs], one read, user_id + user_preferences forwarded, lifetime metered | XB1, BM1 |
| test_XB2_length_reply_without_content_is_no_content | 1 | length + null content -> LLMUnavailableError, the no-content WARNING, no length WARNING | XB2 |
| test_XB2b_route_length_reply_without_content_is_coded_503 | 1 | route: coded 503 LLM_UNAVAILABLE + friendly copy, no action key, refunded, no compare | XB2 |
| test_XB3_each_image_encoded_once | 4 ([true-1], [true-2], [true-3], [None-2]) | encode_image_bytes_to_base64 called once per image, in order, both flag states; one dispatch | XB3 (the three ON nodes) |
| test_Y1_v2_reply_logs_cache_telemetry_once | 1 | _log_cache_telemetry called once with the reply and "identify_products"; the [OPENAI_CACHE] line | Y1 |
| test_Y2_dispatch_errors_are_not_logged_as_timeouts | 2 (bad_request, rate_limit) | the raised SDK error propagates as itself; no "[VISION_V2] vision call timed out" record | Y2 |
| test_Y2b_route_dispatch_errors_keep_their_classification | 2 ([bad_request-500-SERVER_ERROR], [rate_limit-503-LLM_UNAVAILABLE]) | 500 SERVER_ERROR + the literal / coded 503 + friendly copy; refunded; no compare; no prefs read; no timed-out record | Y2 (and XB1 / BM1) |
| test_Y3_refusal_with_string_content_is_no_content | 1 | refusal + a parsable two-product string -> LLMUnavailableError, refused=True WARNING, no counts line, refusal text never logged | Y3 |
| test_Z1_Z3_vision_prompt_v2_sha_pinned | 1 | sha256(VISION_PROMPT_V2) == VISION_PROMPT_SHA_ON (7d7f2c83...dd24, measured 2026-10-20 from the module AST) and the sent text under the flag has the same sha | Z1, Z2, Z3 |
| test_Z1_Z3_vision_prompt_v2_rule_substrings | 4 (confidence_low, no_invention, numbered_from_0, zero_based) | each rule quoted from the constant occurs exactly once | Z1 (no_invention, confidence_low), Z2 (numbered_from_0), Z3 (zero_based) |

Row-count check: 105 -> 131 nodes. The new rows are GREEN at HEAD by design (F3-1 pins); at
764d4416 + the new file they passed 131/131 in the scratch worktree too.

## Mutation table (scratch worktree <scratchpad>/B3_fix1/wt, detached at 764d4416, the new RED
file copied in; source sha256 equal to the unit worktree; byte copy -> exact edit or block move ->
the unit file through pyt.py, flag unset -> restore -> sha256 compare; lock held and removed;
worktree removed with `git worktree remove --force`, absent from `git worktree list`)

| id | mutant | failed rows | non-assert E-lines | restore |
|---|---|---|---|---|
| XB1 | prefs block moved BEFORE `vision_ledger = start_openai_ledger()` | 11 (XB1 x8, XB1b, Y2b x2) | none | sha equal |
| BM1 | prefs block moved AFTER that line | 11 (same) | none | sha equal |
| XB2 | length check (+ `_parse_failure`) moved above the no-content check | 2 (XB2, XB2b) | none | sha equal |
| XB3 | flag-first branch moved below the V1 content build | 3 (XB3 ON x3) | none | sha equal |
| Y1 | `_log_cache_telemetry` dropped from V2 | 1 (Y1) | none | sha equal |
| Y2 | `except asyncio.TimeoutError` -> `except Exception` | 4 (Y2 x2, Y2b x2) | none | sha equal |
| Y3 | refusal honoured only when content is not a str | 1 (Y3) | none | sha equal |
| Z1 | no-invention rule deleted | 3 (sha, no_invention, confidence_low) | none | sha equal |
| Z2 | "numbered from 1 ... image_index 1 is the first image" | 2 (sha, numbered_from_0) | none | sha equal |
| Z3 | "the 1-based number" | 2 (sha, zero_based) | none | sha equal |

10 / 10 KILLED by AssertionError only. Raw records: <scratchpad>/B3_fix1/mut_results.jsonl; logs
<scratchpad>/B3_fix1/mut_logs/; harness <scratchpad>/B3_fix1/mutate_fix1.py.

## Runs (every pytest through pyt.py, one at a time; flag state in the runner env only)

```
unit file at HEAD (+26 rows), flag unset: 131 passed, 10 warnings; [hermeticity] 131; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3fix1-unit-off-1 start=2026-10-20 09:43:56 end=2026-10-20 09:45:17 elapsed=81s bound=600s status=OK rc=0
unit file, ENABLE_VISION_IDENTITY_V2=true: 131 passed, 10 warnings; [hermeticity] 131; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3fix1-unit-on-1 start=2026-10-20 09:45:34 end=2026-10-20 09:46:21 elapsed=47s bound=600s status=OK rc=0
scratch worktree, unmutated (mutation baseline): 131 passed; [hermeticity] 131; [netguard] blocked 0
[pyt] tag=b3fix1-scratch-baseline start=2026-10-20 09:50:45 end=2026-10-20 09:51:37 elapsed=51s bound=600s status=OK rc=0
[pyt] tag=b3fix1-mut-XB1 start=2026-10-20 09:51:48 end=2026-10-20 09:52:54 elapsed=66s bound=600s status=FAIL rc=1   (11 failed, 120 passed)
[pyt] tag=b3fix1-mut-BM1 start=2026-10-20 09:52:57 end=2026-10-20 09:53:47 elapsed=50s bound=600s status=FAIL rc=1   (11 failed, 120 passed)
[pyt] tag=b3fix1-mut-XB2 start=2026-10-20 09:53:50 end=2026-10-20 09:54:44 elapsed=54s bound=600s status=FAIL rc=1   (2 failed, 129 passed)
[pyt] tag=b3fix1-mut-XB3 start=2026-10-20 09:54:47 end=2026-10-20 09:56:04 elapsed=77s bound=600s status=FAIL rc=1   (3 failed, 128 passed)
[pyt] tag=b3fix1-mut-Y1 start=2026-10-20 09:56:11 end=2026-10-20 09:57:10 elapsed=59s bound=600s status=FAIL rc=1    (1 failed, 130 passed)
[pyt] tag=b3fix1-mut-Y2 start=2026-10-20 09:57:35 end=2026-10-20 09:58:11 elapsed=37s bound=600s status=FAIL rc=1    (4 failed, 127 passed)
[pyt] tag=b3fix1-mut-Y3 start=2026-10-20 09:58:13 end=2026-10-20 09:58:36 elapsed=23s bound=600s status=FAIL rc=1    (1 failed, 130 passed)
[pyt] tag=b3fix1-mut-Z1 start=2026-10-20 09:58:36 end=2026-10-20 09:58:54 elapsed=17s bound=600s status=FAIL rc=1    (3 failed, 128 passed)
[pyt] tag=b3fix1-mut-Z2 start=2026-10-20 09:58:55 end=2026-10-20 09:59:05 elapsed=10s bound=600s status=FAIL rc=1    (2 failed, 129 passed)
[pyt] tag=b3fix1-mut-Z3 start=2026-10-20 09:59:06 end=2026-10-20 09:59:12 elapsed=6s bound=600s status=FAIL rc=1     (2 failed, 129 passed)
tests/test_price_fallback_may_decline.py (F3-2): 17 passed; [hermeticity] 17; [netguard] blocked 0
[pyt] tag=b3fix1-pricefallback start=2026-10-20 10:04:45 end=2026-10-20 10:04:58 elapsed=12s bound=600s status=OK rc=0
CI-order set (GREEN's 30 files, the spec 4.2 identity pins inside): 1385 passed, 1 skipped, 1 deselected, 23 warnings; [hermeticity] 1386; [netguard] blocked 29 attempt(s) from 23 node(s) (all 23 in tests/.network_attempt_baseline.txt; = GREEN's line)
[pyt] tag=b3fix1-ciorder start=2026-10-20 10:05:15 end=2026-10-20 10:06:19 elapsed=64s bound=1200s status=OK rc=0
CLAUDE.md readers (tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py) on the final CLAUDE.md: 79 passed; [hermeticity] 79; [netguard] blocked 0
[pyt] tag=b3fix1-claude-readers start=2026-10-20 10:06:53 end=2026-10-20 10:06:58 elapsed=5s bound=600s status=OK rc=0
```

Lint / syntax on the one touched Python file: `ruff check --select E9,F63,F7,F82 --no-cache` "All checks
passed!" (and `--select F` clean); `py_compile` rc 0. Added-line sweep over the 354 added lines:
@gmail 0, +973 0, sk- 0, eyJ 0, PRIVATE KEY 0, AKIA 0, xox 0, credentialed URL 0, 8-digit runs 0.
The pre-commit hook passed on the commit.

## Documentation rulings applied

- F3-2: the comm-set rule (edited test-support modules) stated in the PR body with the run; the
  importers of tests/w4_11_prompt_digest_recorder.py at HEAD are test_model_config_enforced,
  test_prompt_fence, test_prompt_truth (already in GREEN's 248) and test_price_fallback_may_decline
  (added: 249). No test imports any of the edited test FILES (grep).
- F3-3: the hard flip precondition in the CLAUDE.md row and PR-body owner step 1 is the off-route
  smoke (`ENABLE_VISION_IDENTITY_V2=true python -c "..."` on a Railway shell on `web`), with the
  expected results and "do not flip; open an issue"; "the owner never flips to test"; the activation
  sentence points at it.
- F3-4: the "one client-visible value change" sentence replaced by the measured list (row + PR limit
  10); the confidence clause corrected (missing -> low, V1 medium; unrecognised -> low, V1 verbatim);
  limit 5 gains the placeholder-pair spend clause + canary item; limit 14 (PR 15) widened to the ~53
  authed camera nodes; new limit (row 15, PR 17) two products at image_index 0 keep one + canary item.
- F3-5: PR-body defect row for R12 x15; rebase note (merge-tree: CLAUDE.md only, base :501-:502 =
  branch :504-:505, take B3's two lines); `_select_vision_products_v2` vs the spec's
  `_select_best_per_image` noted as internal; the scs ruff per-rule list completed (SIM102 / SIM103 /
  SIM118, unchanged base vs HEAD); the hook-file NOT MEASURED note and the re-verifier instruction.

## Adversary findings closed or recorded

- MAJ-E1 (comm set misses test_price_fallback_may_decline): closed (F3-2, run green, list 249).
- MAJ-E2 / min-6 (BM1 / XB1 placement unpinned): closed (XB1 x8, XB1b; BM1 and XB1 both killed).
- min-1 (hard precondition not executable): closed (F3-3 wording).
- min-2 (prompt rules unpinned): closed (Z1_Z3 sha + 4 substrings; Z1-Z3 killed).
- min-3 (both products at index 0): recorded (row limit 15, PR limit 17, canary item).
- min-4 / engineering minor 1 (client-visible list): closed (measured list in row + PR limit 10).
- min-5 / engineering minor 5 (limit 14 understated): closed (widened).
- min-7 / min-8 / min-9 (XB2, XB3, Y1-Y3): closed (pins; all killed); min-9's empty-tail canary
  note recorded (row activation canary, PR limit 18).
- min-10 (placeholder spend): closed (limit 5 clause + canary item).
- engineering minors 2 / 3 / 4: closed (rebase note, R12 row, ruff list); minor 6 (hook files):
  recorded NOT MEASURED for the re-verifier (F3-5); minor 7 (X19 naming): recorded (no X19 in B3;
  the hand block-moves are XB1-XB3 / BM1); minor 8: no action (confirmations).

## Deviations

- D1 Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`: the rulings say "the
  Co-Authored-By trailer naming your own model"; this agent runs on claude-opus-5-5, so it does not
  write the task text's "Claude Fable 5.1" (same as GREEN's D2). The orchestrator records the model.
- D2 A fourth Z substring (`numbered from 0 in the order they are given (image_index 0 is the first
  image)`) beyond the ruling's three, so Z2 is killed by a substring row as well as by the sha row.
- D3 BM1 (the engineering adversary's after-the-line variant) run in addition to the ruling's XB1:
  10 mutants, all killed.
- D4 XB1 also covers the moderation-blocked exit (exit 3) and both action-error exits (2 and 4).
- D5 F3-4's "a null brand reads Unknown" corrected to the measured case: the V1 normaliser is
  `p.get("brand") or "Unknown"` / `p.get("name") or "Unknown Product"`, so a null brand / name reads
  the same default in both; the change is a WHITESPACE-only brand / name (V1 kept it) and an empty
  size / price (V1 kept ""). "V1 waited unbounded" written precisely: no route-level bound, only the
  SDK client's 120 s per-attempt timeout and its retries (`openai_service.client`).
- D6 F3-3's "two products with `image_index` 0 and 1, and `category` ..." written as `_image_index`
  / `_category` (the internal keys `identify_products` returns; the public dicts carry neither).
- D7 The CLAUDE.md row also gained a one-sentence "Fix-round pins" summary (so a deliberate prompt
  edit re-pins VISION_PROMPT_SHA_ON in the same PR) and the empty-tail timeout canary clause
  (correctness min-9); the header names RULINGS_FIX1_B3.
- D8 The unit's comm list is a new file <scratchpad>/B3_fix1/comm_head_list_fix1.txt (249); GREEN's
  comm_head_list.txt is left as GREEN wrote it.
- D9 The two numbering schemes differ (row limits 1-15, PR limits 1-18); each cross-reference uses
  its own document's numbers.

## NOT MEASURED

- The pre-commit hook test files (tests/test_precommit_hook*.py): not run by this agent (F3-5 assigns
  the not-dash set ALONE to the re-verifier); the fix commit passed the hook itself.
- The full comm set was not re-run: the fix changes no app file and adds only test rows and two
  CLAUDE.md lines; the CLAUDE.md readers and the one added comm file were run (above).
- Live OpenAI behaviour (structured outputs with image input): the owner's off-route smoke.

## Questions for the gate / re-verifier

- Q1 Confirm the trailer / model record (D1).
- Q2 Accept D5 (the measured correction of the ruling's "null brand" item) and D6.
- Q3 Accept D2 / D3 / D4 (extra substring, BM1, wider XB1 exit coverage) as strengthening.

## git status --short (worktree, at the end)

(empty) -- HEAD 7b1e3ecf81ef2bb24ce08e84d89c0069f98b386a.

## Notes folder

<scratchpad>/B3_fix1/: notes.md, prompt_sha.py, mutate_fix1.py, mut_results.jsonl, mut_logs/,
mut_backup/, before/ (byte copies of CLAUDE.md and PR_BODY.md before the edits), RED_before.py,
unit_off_1.log, unit_on_1.log, scratch_baseline.log, pricefallback.log, ciorder.log,
claude_readers.log, ciorder_netguard_nodes.txt, ciorder_nodes_clean.txt, baseline_nodes.txt,
comm_head_list_fix1.txt, added_lines.txt, claude_diff_head.txt, this report. The files this agent
authored (this report, notes.md, mutate_fix1.py, prompt_sha.py, comm_head_list_fix1.txt) are pure
ASCII + LF; the runner logs and mut_results.jsonl carry the runner's CRLF; claude_diff_head.txt and
the byte copies in before/ and mut_backup/ carry the repo's own bytes (non-ASCII, CRLF) unchanged.
