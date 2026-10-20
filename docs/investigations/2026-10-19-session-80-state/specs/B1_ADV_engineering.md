# B1 adversary (engineering lens): RESULT-STATUS + TELEMETRY (ENABLE_RESULT_STATUS_METADATA)

Agent: b1-adv-engineering. Window 2026-10-20 06:07 - 07:25 AST. Worktree under review
C:/Users/SynAckITPC/Documents/AI/sc-s80-b1, branch feature/s80-b1-result-status, HEAD verified
2bbd58a9eae6aa172339ee7cc717e875ff2bbc73 at the start and at the end (base 81df2b64; rebase target
origin/main 4a38ce93). Never edited the unit worktree. Every probe ran in my own detached scratch worktree
<scratchpad>/B1_adv_engineering (2bbd58a9, `git status --short` empty before and after; removed at the end).
Notes, scripts, logs: <scratchpad>/B1_adv/eng/ (notes.md, comm_derive.py + comm_mine.tsv +
comm_missing_from_green.tsv, run_eng.py, probe_tags.py + probe_tags_out.json, gates/*.json|*.log|SUMMARY.txt).

## Verdict: NOT_READY (0 blocking, 2 major, 10 minor)

## RED files (re-hashed at the start and at the end; both equal to the frozen rows)

| file | sha256 (start) | sha256 (end) |
|---|---|---|
| tests/test_s80_b1.py | 88130f327757d9e53feb47bbe877f9a065783b2e3a01f90c623360de46a35dfb | 88130f327757d9e53feb47bbe877f9a065783b2e3a01f90c623360de46a35dfb |
| tests/test_s80_b1_feedback.py | 0bd1117880ac96cee0aee35832814ae7eee620b6bef09bba7b0513648ea59ab3 | 0bd1117880ac96cee0aee35832814ae7eee620b6bef09bba7b0513648ea59ab3 |

Every other file of the commit in the unit worktree matches GREEN's FINAL sha256 table byte for byte
(re-hashed: CLAUDE.md 73652c2a..., result_gate.py 48bcbb7d..., response_builder.py dc3d446f...,
structured_comparison_service.py 7533fa10..., sentry_service.py e7bdd707..., image_routes.py 0aa86d20...,
text_routes.py 9da410d6..., url_routes.py 0c930879..., home_routes.py 04ec255d..., feedback_routes.py
02cb01f6..., feedback_service.py b8441b61..., test_s75_fanout_identity.py c690a3a4...).

## MAJOR

### MAJ-E1 The telemetry message contradicts the stamped body on a category conflict (row + PR body claim false)

`sentry_service.capture_result_status` computes `assessment = assess_result(result)` WITHOUT
`product_categories`, and `result_gate.assess_result` reads the categories ONLY from its kwarg (never from
the body's `metadata.product_categories`, which the builder stamps). So `identity_coherence(None)` is True
on the telemetry path and every category-conflict body is reported as a crowned result. Independently
confirmed with a pure call on the GREEN bytes (no app import beyond result_gate + text_sanitize, no env,
no network; `probe_tags.py`, output `probe_tags_out.json`): a two-product body (Samsung Galaxy S24 phone /
Dior Sauvage eau de parfum, real prices and ratings, category_used electronics) stamped with
`product_categories=["electronics","fragrances"]` gives the STAMP `unsupported_category`, reasons
`["category_conflict"]`, `identity_confidence low`; the TAGS the emitter builds from the same body give
`result_status=supported_result`, `reasons=none`, `identity_confidence=high`, `winner_emitted=true`.
(The correctness adversary measured the same through the real camera route, its MAJ-1.)
Engineering consequence: the CLAUDE.md row ("One PII-free Sentry info message ... with the tags ...
result_status ...", the Canary "the comparison_result_status messages grouped by the result_status x
input_type tags") and the PR body (MYEZ-011 row: r12 / r16 category conflict; "Telemetry contract") state
that the Sentry stream measures the status; for the category-conflict class it cannot: `unsupported_category`
and `category_conflict` are unreachable in the message stream while the stored row says the opposite. The
row's own sentence "the tags are recomputed from the body, never read from metadata" is the cause. No RED
row compares the message tags with the stamp on a conflict body (R17 / R18 use same-category bodies; R17b
carries no category_conflict). Fix (flag-ON path only): pass
`product_categories=(result.get("metadata") or {}).get("product_categories")` into `assess_result` in
`capture_result_status`, plus a RED row asserting tags == stamp (status, reasons, identity_confidence,
winner_emitted) on a conflict body; then the row and PR body sentences hold.

### MAJ-E2 Binding ruling B1-R11 Q7 (profile surfaces) is not implemented

RULINGS_BATCH1 B1-R11 Q7 (binding for RED and GREEN): "apply the same result_status skip to
profile_routes.py:75/:97/:141 in this unit with a P8-style pin". At HEAD `profile_routes.py:65-83`
(`_extract_winner_loser_prices`, the /profile/monthly-stats savings), `:86-107` (`_extract_product_names`,
/profile/recent-decisions) and `:126-147` (`_extract_product_image_urls`) still key on the top-level
`winner_index` with no `result_status` check, so after the flip a stamped non-supported row is counted as
savings and shown as a decision on the profile surface (MYEZ-027 not closed there). GREEN disclosed it
(deviation 1, question 1; stated in the CLAUDE.md row and the PR body) because the frozen RED files carry no
row for it. Resolution needs the orchestrator: a fix round (RED row in the home_routes P8 / R22 pattern +
the reader hunk) or an explicit amendment of B1-R11 Q7 deferring it (to C1 or a follow-up unit). Until one
exists, the bytes do not meet a binding ruling.

## MINOR (documentation rulings for the orchestrator)

1. Sentry ERROR-event quota missing from the owner steps and the row. Under the flag every delivered
   compare emits one `capture_message(level="info")` into the BACKEND project (init sets no `sample_rate`,
   so 100 % of them are sent, and info messages count as error events), on top of the 100 % compare
   transactions the row does mention. The precedent `comparison_wall_time` is a CLIENT message
   (SmartCompareApp/src/lib/performance/wallTimeInstrumentation.ts:106, the react-native project), not a
   backend one. init_sentry's own 503 comment records the project's concern about flooding the error stream.
   Owner step 3 should read "the Sentry plan's transaction AND error-event quota (one info event per
   delivered compare)".
2. `/home/savings` skip is on the legacy scan only. With `ENABLE_HOME_SAVINGS_AGGREGATE` ON (needs
   migration 036, unapplied) `home_savings` returns the `home_savings_aggregate` RPC result, whose SQL keys on
   `full_response ->> 'winner_index'` (migrations/036 :56, :69) and would count stamped non-supported rows.
   The row and the PR body say "/home/savings ... skip stamped non-supported rows" unqualified; add the
   stated limit (the spec 2.4 sentence "The savings and smart-pick RPC/legacy selects are unchanged" implies
   it, the row drops it).
3. "the only OFF-state work is the per-call flag read at each site, three perf_counter reads on the camera
   route and the per-product category capture" (row and PR body): the camera route makes SIX perf_counter
   reads (three walls); the URL route evaluates `int((time.time() - _start) * 1000)` as an argument in both
   flag states; the traces sampler runs on EVERY transaction in both states (a flag read plus a
   `sentry_sdk.get_client().options` lookup when there is no parent decision). Behaviour-neutral; wording.
4. "the tags are recomputed from the body, never read from metadata" (row): `partial_stage` / `partial` and
   the `elapsed_ms` fallback for `compare_ms` ARE read from `metadata` (sentry_service capture_result_status;
   result_gate.telemetry_tags). Wording (and see MAJ-E1, which this rule causes).
5. "build 3 ignores every new key" (row and PR body) contradicts the same row's CR1 sentence: the stamped
   `metadata.winner_index = None` changes the build-3 History LIST (history_routes._extract_winner_index
   returns it, P7). Reword to "build 3 renders no new key; the History list loses the winner highlight of a
   stamped non-supported row (CR1)".
6. result_gate's module docstring "Every function is total ... never raises" is false for non-finite walls:
   `telemetry_tags(..., compare_ms=float('inf'))` raises OverflowError and `nan` ValueError (probe; `_bucket`,
   `telemetry_extras` and `stamp_camera_stage_timings` share the `int(value)`). Unreachable today (walls are
   perf_counter ints, `elapsed_ms` is an int) and the emitter's except arm would log the WARNING; a
   `math.isfinite` guard or the docstring wording.
7. The tag-grammar claim `^[a-z0-9_,]+$` is not enforced in code: `partial_stage` is passed through from
   `metadata.partial_stage` as any str (server constants today: gather / post_gather / scoring / verdict).
   Not a PII leak today; a one-line whitelist would make the claim structural.
8. PR body cites `test_b1_p5a` (no such node; the node is `test_b1_p5a_init_sentry_kwargs_kept`). Every other
   cited node / prefix exists (53 test functions, 214 nodes: 187 + 27; p1[5] p2[2] p3[2] p4[2] p5[42] p5b[3]
   as stated).
9. The frozen RED file tests/test_s80_b1.py carries 5 report-only ruff findings (F401 `os`, F401
   `get_optional_user`, C420 :480, B905 :585 / :755); the blocking tier (E9,F63,F7,F82) is clean, so no CI
   effect; recorded only (frozen file).
10. GREEN's comm list includes `tests/_env_safety.py` (a helper inherited from the RED list; collected as an
    explicit path with 0 tests). Harmless; drop it from the canonical list.

## Engineering checks that PASSED

- Diff hygiene: `git diff --check 81df2b64 HEAD` clean; 2249 added lines, 0 CR, 0 tabs; bytes > 127 in added
  lines = 3, all CLAUDE.md :105 (the pre-existing arrow kept on the rewritten line; CLAUDE.md 1367 non-ASCII
  chars / 3979 bytes at base and head). Index is LF for all 14 files; the unit worktree copies: every edited
  file CRLF with 0 bare-LF lines, the three new files LF, 0 bytes > 127. The 3 deleted lines are all in-place
  rewrites (CLAUDE.md :105, the feedback_routes typing import, the FY25 UNIT_ENV tuple). Commit message ASCII,
  trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; author identity is the repo's configured
  git identity (same as every main commit).
- Imports: exactly the spec's (result_gate: os, re, typing, text_sanitize.dedup_brand_name; response_builder:
  STATUS_SUPPORTED, assess_result, result_status_metadata_enabled; sentry_service: + telemetry_extras, justified
  by B1-R10; routes: capture_result_status / stamp_camera_stage_timings; feedback_routes: Literal). No import
  cycle (text_sanitize imports only `re`; app/__init__.py and app/services/__init__.py are empty).
- Control flow: the REST capture (scs :4288) and the stream capture (:4919) sit in the linear try body before
  every build site that passes `product_categories`, so no path reaches a build with the name unbound;
  `canonicalize_category` is total (returns "other" for None / non-str). `result["metadata"]` and
  `result["overview"]["winner"]` are created by the builder's result literal (:1903 / :2071), so the stamp's
  writes cannot fail half-way.
- Added-line sweep: 0 sk- / AKIA / xox / JWT / PEM / credentialed-URL shapes, 0 emails, 0 +973, 0 owner
  names; the three 8-digit runs are synthetic UUIDs in the frozen RED files.
- Telemetry tags / extras PII: every tag value derives from a fixed vocabulary or an int (input_type call-site
  constants, STATUSES, CONFIDENCE_LEVELS, REASONS, bool flags, coverage ints, bucket digit strings,
  server-side partial_stage); extras are two ints. No name, brand, query, URL, host, id or amount reaches a tag
  or extra; the app sets no Sentry user (grep: no set_user; the one set_tag is `comparison_renderable`).
- Comm set re-derivation (union rule: module names + touched symbols + route paths + source-scanning pin globs
  incl. test_start_command*.py / test_model_config*.py + app-walking/reading tests + CLAUDE.md readers +
  SmartCompareApp scanners + migration/manifest readers, minus test_precommit_hook*.py): 349 candidates vs
  GREEN's 305. The 45 extra candidates were triaged one by one (list in comm_missing_from_green.tsv): 9 only
  MENTION CLAUDE.md in a docstring (the only two readers are test_ci_gates.py and
  test_behavior_dimension_translation.py), 8 read the source of UNCHANGED modules (database_service,
  auth_service, push_service, price_service, robots_eval, the cron and channel scripts), 6 are live-only
  (`integration` / `live_unit`), 5 name a compare route path without exercising a changed handler (a fake
  ASGI scope, the harness scripts, route introspection, /auth/me + /usage/status, a usage_service unit), 3
  reference an unchanged symbol (`canonicalize_category` x2, an unrelated budget-alert `capture_message`),
  14 are migration / manifest readers (no migration or manifest change; test_migration_027 run anyway in
  srcpins). No material file is missing from GREEN's list; GREEN-only = `tests/_env_safety.py` (minor 10).
- netguard ratchet (scripts/netguard_ratchet.py over a QAREN_NETGUARD_REPORT per run, against
  tests/.network_attempt_baseline.txt): rc 0 on every run; no NEW egress node. The only WARNING (new node,
  sentinel hosts only, allowed) is the pre-existing S78-F8 node
  tests/test_s78_all_timeout_cap_as_timeout.py::test_F15_route_end_to_end[off|on], not B1's.
- Lint: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` clean on all 13 changed .py files; `py_compile` clean;
  full default ruff finding counts base == head per edited file (feedback_routes 4/4, home_routes 4/4,
  image_routes 6/6, text_routes 10/10, url_routes 12/12, feedback_service 0/0, response_builder 3/3,
  sentry_service 0/0, structured_comparison_service 21/21, test_s75 0/0); result_gate.py 0.
- CLAUDE.md row placement and the rebase (GA-8): `git merge-tree --write-tree --merge-base 81df2b64 4a38ce93
  2bbd58a9` is CLEAN (tree 05adca71); 4a38ce93 changes CLAUDE.md only, and H0 rewrote the B3-B header line
  (:471) while B1 inserts after the unchanged :472 bullet, so no conflict. In the rebased CLAUDE.md the B1
  block sits at :474, after the B3-B block (:471) and before `## Tests` (:477). The two CLAUDE.md readers pass
  on the HEAD file (79) AND on the rebased file swapped into the scratch worktree (79; byte copy, restored,
  sha256 equal, `.qa-mutation.lock` created and removed).
- Row / PR numbers verified against the bytes: spec sha 05d48e2c...; R0-5 4/27 vs 1/27 and "3 of 52" (spec
  :127, :627, :639); the 027 CHECK values correct | wrong | unsure (migrations/027 :49, :55) match the
  `Literal`; the four sampler paths match the routers (text :578 / :774 / :958, image :163, url :336 / :373 with
  the /api/v1/{text,image,url} prefixes); "first writer of metadata.winner_index" (only response_builder
  :2293 writes it; history_routes :38 reads it); 221 / 2 and 2249 / 3 diff counts; E1 is one tuple entry; the
  CI-order count reproduces (1155 = GREEN's 1155, flag OFF and ON); GREEN's comm failures (9 node ids) are the
  seven tests/.pre_impl_failures.txt nodes plus the two cold-tiktoken test_prompt_truth ERRORs measured alike
  at base; my chunk A reproduces the three camera_vision baseline nodes and nothing else.

## Prove-nothing rows (engineering lens)

- No row asserts telemetry tags == the stamp on a category-conflict body (the MAJ-E1 gap: R17 / R18 / R17b all
  pass with the defect present).
- P8 / R22 pin the legacy `/home/savings` scan only; nothing pins the aggregate-RPC path's behaviour on a
  stamped row (minor 2).

## Runs (every [pyt] line verbatim; all in the scratch worktree at 2bbd58a9, flag unset unless marked ON)

```
CI-order set (GREEN's 20 files, alphabetical, one process), flag OFF -- 1155 passed
[pyt] tag=b1eng-ci_off start=2026-10-20 06:17:15 end=2026-10-20 06:18:44 elapsed=89s bound=1200s status=OK rc=0
  [hermeticity] sentinel checked 1155 test(s); [netguard] blocked 20 attempt(s) from 4 node(s) (test_paid_route_metering x2 sentinel, test_stage_timings x2 egress = baseline)
CI-order set, flag ON exported on the runner call only -- 1155 passed
[pyt] tag=b1eng-ci_on start=2026-10-20 06:18:52 end=2026-10-20 06:19:50 elapsed=58s bound=1200s status=OK rc=0
  [hermeticity] sentinel checked 1155 test(s); [netguard] blocked 20 attempt(s) from 4 node(s) (same 4 baseline nodes)
Comm chunk A (25 files: sentry / observability / camera / metering / error envelopes) -- 3 failed, 1020 passed
[pyt] tag=b1eng-chunkA start=2026-10-20 06:19:56 end=2026-10-20 06:20:48 elapsed=52s bound=1200s status=FAIL rc=1
[pyt] tag=b1eng-chunkA start=2026-10-20 06:25:19 end=2026-10-20 06:26:13 elapsed=55s bound=1200s status=FAIL rc=1   (re-run with the netguard report)
  [hermeticity] sentinel checked 1023 test(s); [netguard] blocked 150 attempt(s) from 19 node(s); ratchet OK (19 attempting nodes, baseline 205)
  FAILED = tests/test_camera_vision.py::TestIdentifyProductsMocked::{test_empty_product_fields_normalized,
  test_malformed_response_returns_error, test_successful_identification} = tests/.pre_impl_failures.txt rows 81-83
Comm chunk B (25 files: builder / orchestrator / partial / hard cap / FY25 / stream) -- 657 passed
[pyt] tag=b1eng-chunkB start=2026-10-20 06:21:19 end=2026-10-20 06:23:22 elapsed=123s bound=1200s status=OK rc=0
  [hermeticity] sentinel checked 657 test(s); [netguard] blocked 86 attempt(s) from 40 node(s); ratchet OK (only WARNING: the pre-existing S78-F8 node test_F15_route_end_to_end[off|on], sentinel hosts only)
Comm chunk C (25 files: routes / feedback / home / history / profile / security / W4-13) -- 831 passed
[pyt] tag=b1eng-chunkC start=2026-10-20 06:23:33 end=2026-10-20 06:23:55 elapsed=23s bound=1200s status=OK rc=0
  [hermeticity] sentinel checked 831 test(s); [netguard] blocked 27 attempt(s) from 21 node(s); ratchet OK
Source-scanning pins + migration / manifest / legal readers + hermeticity (24 files) -- 973 passed, 1 skipped
[pyt] tag=b1eng-srcpins start=2026-10-20 06:26:32 end=2026-10-20 06:29:19 elapsed=168s bound=1200s status=OK rc=0
  [hermeticity] sentinel checked 974 test(s); [netguard] blocked 22 attempt(s) from 21 node(s); ratchet OK
  (test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py,
  test_start_command.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py,
  test_sentry_channels_u8d_unit.py, test_migration_027/037/043, the five legal / processors.json readers,
  test_secret_scan_static.py, test_hermeticity_pins.py, test_conftest_env_safety.py (its pre-existing skip),
  test_logger_no_query_leak.py, test_u3b_sharing_branch_removed.py, test_diagnostics_flag_gated.py,
  test_retro_w0_4.py, test_s70_prefetch_gather_retrieved.py)
The two CLAUDE.md readers at HEAD -- 79 passed
[pyt] tag=b1eng-claude start=2026-10-20 06:29:41 end=2026-10-20 06:29:45 elapsed=4s bound=600s status=OK rc=0
  [hermeticity] sentinel checked 79 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
The two CLAUDE.md readers on the REBASED CLAUDE.md (merge-tree 05adca71 bytes, CRLF, swapped in; restored) -- 79 passed
[pyt] tag=b1eng-claude-rebased start=2026-10-20 06:30:20 end=2026-10-20 06:30:29 elapsed=9s bound=600s status=OK rc=0
  [hermeticity] sentinel checked 79 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
Unit files collect-only (node counts for the PR-body check) -- 214 collected (187 + 27)
[pyt] tag=b1eng-collect start=2026-10-20 06:33:16 end=2026-10-20 06:33:19 elapsed=4s bound=600s status=OK rc=0
Pre-commit hook files, -k "not dash" (167 nodes, one call) -- TIMEOUT after 149 nodes, all 149 passed ('.' only, no F/E)
[pyt] tag=b1eng-hook_nodash start=2026-10-20 06:34:25 end=2026-10-20 07:04:27 elapsed=1802s bound=1800s status=TIMEOUT rc=124
  (box load: sibling GREEN B3 + B3 RED gates; node -e 0 = 1.78 s at 06:35, 0.37-0.57 s later)
  the 18 nodes the bound cut, measured by split, alone:
[pyt] tag=b1eng-hook_nodash-sel start=2026-10-20 07:05:06 end=2026-10-20 07:07:59 elapsed=173s bound=1800s status=OK rc=0   (test_precommit_hook_round2.py not dash: 15 passed)
[pyt] tag=b1eng-hook_tail3 start=2026-10-20 07:08:41 end=2026-10-20 07:09:27 elapsed=46s bound=600s status=OK rc=0   (the last 3 sh-variant nodes of test_precommit_hook_phase_b_round2.py: 3 passed)
[pyt] tag=b1eng-hookcollect-nd start=2026-10-20 07:08:15 end=2026-10-20 07:08:18 elapsed=3s bound=600s status=OK rc=0   (167/327 collected: 31 + 57 + 64 + 15)
[pyt] tag=b1eng-hookcollect-d start=2026-10-20 07:08:21 end=2026-10-20 07:08:23 elapsed=2s bound=600s status=OK rc=0   (160/327 collected: 31 + 57 + 57 + 15)
Pre-commit hook files, -k dash, two of the four files (46 nodes) -- 46 passed
[pyt] tag=b1eng-hook_dash-sel start=2026-10-20 07:09:39 end=2026-10-20 07:19:25 elapsed=586s bound=1800s status=OK rc=0
  [hermeticity] sentinel checked 46 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
Engineering mutant EM1 (E1 removed: the flag dropped from the FY25 UNIT_ENV tuple on a byte copy; the file run
with ENABLE_RESULT_STATUS_METADATA=true exported on the runner call) -- KILLED
[pyt] tag=b1eng-mut-EM1 start=2026-10-20 07:04:51 end=2026-10-20 07:04:56 elapsed=5s bound=600s status=FAIL rc=1
  1 failed, 2 passed: tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main
  AssertionError "FY25: flag-OFF scenarios moved against main 6cff57af: ['rest_pair_full', 'rest_q_full', ...]";
  restored from the byte copy, sha256 c690a3a4... equal; .qa-mutation.lock created and removed.
```
Non-pytest: ruff 0.16.5 blocking tier + py_compile on the 13 changed .py files (clean); default ruff base vs
head per file (equal counts); `git diff --check` (clean); `git merge-tree --write-tree` onto 4a38ce93 (clean,
05adca71); probe_tags.py (pure result_gate call; MAJ-E1 and minor 6 values in probe_tags_out.json).

## Questions for the orchestrator

1. MAJ-E1: accept the one-line fix (pass the stamped `metadata.product_categories` into the emitter's
   `assess_result`) with a new RED row, or rule that telemetry deliberately ignores categories (then the row,
   PR body and canary text must say `unsupported_category` is never reported to Sentry).
2. MAJ-E2: fix round (RED row + profile_routes hunk) or an explicit B1-R11 Q7 amendment deferring it.
3. Minor 1: add the error-event quota to owner step 3 (or sample the info message).

## NOT MEASURED

- The pre-commit hook files' `-k dash` half for tests/test_precommit_hook_phase_b.py (57 nodes) and
  tests/test_precommit_hook_phase_b_round2.py (57 nodes): 114 nodes NOT MEASURED within the 90-minute budget
  (about 11-13 s per node on this box; B1 edits no .githooks file and the commit itself passed the hook). The
  `not dash` half (167) is fully measured (149 before the bound + 18 by split, all passed); 46 of the 160 dash
  nodes passed. The one-call `not dash` gate itself TIMED OUT once (line above); it was not re-run whole (the
  re-run would not fit the budget), its remainder was measured by split instead.
- Spec mutants and the X19 hand mutant: the correctness lens's duty (not re-applied here); one engineering
  mutant (EM1) applied and KILLED.
- Flag-ON comm chunks A / B / C (only the CI-order set and GREEN's three smoke runs were measured ON), so the
  developer-.env hazard class (an existing pin that reddens with the flag set locally) is measured for those
  1155 + 351 nodes only.

## End state

- Unit worktree sc-s80-b1: HEAD 2bbd58a9eae6aa172339ee7cc717e875ff2bbc73 (start and end), `git status
  --short` empty; never edited. RED files re-hashed at the end: tests/test_s80_b1.py
  88130f327757d9e53feb47bbe877f9a065783b2e3a01f90c623360de46a35dfb, tests/test_s80_b1_feedback.py
  0bd1117880ac96cee0aee35832814ae7eee620b6bef09bba7b0513648ea59ab3 (equal to the frozen rows).
- Scratch worktree <scratchpad>/B1_adv_engineering: `git status --short` empty after every probe (both
  byte-copy probes restored with sha256 equal; no .qa-mutation.lock left); removed with `git worktree remove
  --force` (rc 0); `git worktree list` no longer lists it; the directory is gone.
- No pytest process of mine alive at the end (process command lines matched on my tags: 0).
- No .env read, copied or printed; no production / Railway / Supabase / Sentry / network access; no git write
  other than the detached scratch worktree add / remove (merge-tree writes objects only, no ref).
- Files written (all under <scratchpad>/B1_adv/, ASCII, LF): engineering_REPORT.md; eng/notes.md,
  eng/comm_derive.py (+ comm_derive.out, comm_mine.tsv, comm_missing_from_green.tsv), eng/run_eng.py,
  eng/probe_tags.py (+ probe_tags_out.json), eng/mut_e1.py, eng/fill_report.py, eng/gates/* (logs, json,
  netguard reports, SUMMARY.txt), eng/full_diff.txt, eng/app_diff.txt, eng/claude_md_diff.txt,
  eng/CLAUDE.rebased.lf.md, eng/CLAUDE.md.head.bytecopy, eng/test_s75_fanout_identity.py.bytecopy,
  eng/hook_tail3.txt, eng/pyt_lines.txt.
