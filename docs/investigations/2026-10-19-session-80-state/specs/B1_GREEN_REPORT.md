# B1 GREEN report: RESULT-STATUS + TELEMETRY (ENABLE_RESULT_STATUS_METADATA)

Agent: b1-green (Fable, claude-fable-5-1). Window 2026-10-20 03:33 - 04:05 AST. Worktree
C:/Users/SynAckITPC/Documents/AI/sc-s80-b1; base 81df2b641454e0301cca51a3ba01bf8ef3d7e649; branch
feature/s80-b1-result-status (created with the ONE allowed `git checkout -b`); GREEN commit
2bbd58a9eae6aa172339ee7cc717e875ff2bbc73 (the pre-commit hook ran and passed: `All checks passed!`); no push,
no rebase, no PR (the orchestrator's steps). `git status --short` EMPTY after the commit. No .env read, no
production / Railway / Supabase / Sentry / network access (the netguard blocked only the pre-existing baseline
classes); every pytest through the bounded runner, one process at a time, 0 pytest processes alive at the end.
Notes: <scratchpad>/B1_green/notes.md; byte copies: <scratchpad>/B1_green_before/ (SHA256SUMS.json); edit
scripts: apply_edits.py (37 anchors, each exactly once), apply_claude_md.py; gate records:
<scratchpad>/B1_green/gates/*.json|*.log + SUMMARY.txt; comm list comm_files_green.txt + comm_reasons_green.tsv;
PR body: <scratchpad>/B1_green/PR_BODY.md.

## RED files (frozen; re-hashed at the start and at the end, both equal)

| file | sha256 | state |
|---|---|---|
| tests/test_s80_b1.py | 88130f327757d9e53feb47bbe877f9a065783b2e3a01f90c623360de46a35dfb | FROZEN-OK (59270 B, 0 > 127, LF) |
| tests/test_s80_b1_feedback.py | 0bd1117880ac96cee0aee35832814ae7eee620b6bef09bba7b0513648ea59ab3 | FROZEN-OK (7874 B, 0 > 127, LF) |

Neither was edited. No RED row was found wrong.

## Files written / edited (sha256 over the bytes on disk after the commit; git numstat vs base)

| file | sha256 after | sha256 before | +/- |
|---|---|---|---|
| app/services/result_gate.py (NEW, LF, 25797 B, 0 > 127) | 48bcbb7d679878cdf282aef71d6b1657dd3d0c44d8aefac9d6912f9667b02df9 | (new) | +620 |
| app/services/response_builder.py | dc3d446fd1f149458f9c6a9d81596a5003676650f155fd2ce94a15b68a388ab2 | 6fb6c40ad8edf902cee0dd2bc563b9102d288857c0b2683f591870de9df43c60 | +43 / -0 |
| app/services/structured_comparison_service.py | 7533fa10c1303d5a58175d48199347c31ec3620d86f55303292e35f0fbaf7084 | 7db53e39fee4f93159b08f8834d27094d3b7e3e081976e402ac17306681df6d2 | +13 / -0 |
| app/services/sentry_service.py | e7bdd7075f1639ea4c36f7e8b68e3df09a380c2eacb0bc0fa888b460c76735ef | 91366057632e431732c3a212592bb30176084700ea59210ef671f7a5464e11ee | +86 / -0 |
| app/api/image_routes.py | 0aa86d20e6fdf5f5d1233d16adcbd1b41332356ae29887e04cdb07a4e660ade3 | 3813cb9af4a296e77429b954086405dd3a571774a2a3e44ce8727ed69b2a95ef | +20 / -0 |
| app/api/text_routes.py | 9da410d6e57386d827c9fb11b10a3ac72a171d51510747f0d01565606d3bd416 | 22799ae4e484eaae3dd5752e86b775057ab0ac730d2b8af632b098ad97c85fef | +10 / -0 |
| app/api/url_routes.py | 0c930879d65641ba9d9a4b008a63b1af43c76f1c6df0a64524d96d7bfdc0eaf6 | bc3d0822e7e89906d6248fb66af710e755f7755dbd7e9d770107bb430d1557db | +5 / -0 |
| app/api/home_routes.py | 04ec255dab18e33d02182272e52e15e0c40c24901664af196ff1c0cb4aaf0d6c | 2acdb64b42d038ff21ecd5b1cd20e3c8cfd96ba016fc546f25b04a9b1561091a | +17 / -0 |
| app/api/feedback_routes.py | 02cb01f6b67fd638fbc681c63f1e5b18a280ab43813faedc98c6785727c69e80 | 21de13c7edadff8ffd1e3b5d3acd678a1e0bed13cd740c6186ffe8df09d47898 | +14 / -1 |
| app/services/feedback_service.py | b8441b61b82aac1acdc008b72b9353a227c4b91c238d6616fe8460644ae541ce | c318f11cffe85ed8e8b11643ce7f120a4b8e38717071b5e32d82ae86c5651e07 | +11 / -0 |
| tests/test_s75_fanout_identity.py (E1) | c690a3a45546c0462c3001ec75596b262021091664eef9d253c22d596705188e | 3130b7f126a7f9832f4341900d147b080b376c723d0a0cf427ba0b59156adece | +2 / -1 |
| CLAUDE.md (the flag row + the :105 /feedback line in place) | 73652c2a851732c6df62975398c306155b0d9765b7d050153392cff0686626b3 | ab7ec7dde1724998f7d12a4d5a2c70ee55efdad95c89c6c025413a21929d7415 | +4 / -1 |

Every edited file kept its CRLF working copy (bare-LF lines 0) and its non-ASCII byte count (only ASCII CRLF lines
were added; CLAUDE.md 1367 before == after); `git diff --stat` is content lines only (221 insertions / 2 deletions
over the ten edited files before the CLAUDE.md edit; 2249 / 3 in the commit incl. the three new files). No other
file: no requirements*, migration, processors.json, client file, .githooks or tests/.pre_impl_failures.txt change.

## What was implemented (the spec change list as amended by the review, RULINGS_BATCH1 B1-R1..R12 and GATE_B1)

1. `app/services/result_gate.py` (new, pure: os / re / typing / `text_sanitize.dedup_brand_name`; no I/O, no
   `async def`; the P11 banned substrings absent): the R-A4 vocabulary, `norm` (Arabic range built with chr() so the
   file stays ASCII), the placeholder set compared after `norm` on both sides (RED deviation 5), `same_identity`
   with the axis veto on BOTH arms (deviation 4), `identity_coherence` (R0-4), `price_is_showable` /
   `price_is_present_literal` (numeric non-bool amount, deviation 6), `rating_is_real`, `real_spec_rows` with NA via
   `strip().lower()` (B1-R2) and the tier-3 exclusion, `literal_spec_items`, `dim_is_discriminating`, the AUDITABLE
   and LITERAL facts over the RAW `products` alias first (B1-R7), `section_status`, `identity_confidence`,
   `assess_result` (every applicable reason in REASONS order; the status of the first), `telemetry_tags` with the
   GA-2 bucket tags, `telemetry_extras` (raw ints), `stamp_camera_stage_timings` (flag first; existing dict only),
   `result_status_metadata_enabled` (the house idiom).
2. `response_builder.py`: the module-level import (`assess_result` bound by name so P13's monkeypatch reaches it);
   the `product_categories` kwarg + docstring paragraph; the stamp block between `result["tier_context"]` and
   `_strip_inference_markers(result)`, flag first, every value computed before the first write, the writes additive
   only, `metadata.winner_index = None` on a non-supported body, `except Exception` -> ONE WARNING
   `[RESULT_STATUS] assess failed: %s` (type name).
3. `structured_comparison_service.py`: `product_categories = [canonicalize_category(_p.get("category")) for _p in
   products]` captured immediately BEFORE both write-back loops (REST before the `_partial_build_ctx.update`, B1-R8;
   stream before the write-back, then into the dict literal), passed to the REST, stream and partial builds (the
   partial from `ctx.get("product_categories")`). Four insertions per the spec, in both flag states (unused OFF).
4. `sentry_service.py`: the module-top import of result_gate; `compare_traces_sampler` (the four compare paths at
   1.0 under the flag; else `parent_sampled` when not None, else the LIVE `sentry_sdk.get_client().options`
   `traces_sample_rate`, 0.1 only when none -- B1-R1; `sentry_sdk` looked up at call time so a patched `get_client`
   is honoured); `capture_result_status` (flag first; a non-dict or non-success body never emits; `compare_ms`
   from `metadata.elapsed_ms` when the caller passed none; ONE `capture_message("comparison_result_status",
   level="info", tags=..., extras=...)`; the except arm's ONE WARNING by type); `traces_sampler=compare_traces_sampler`
   beside the kept `traces_sample_rate=0.1`.
5. `image_routes.py`: the three `perf_counter` walls (identify, moderation, compare), `stamp_camera_stage_timings`
   after the openai merge, the emitter before `return result` gated on `result.get("success") is True` (B1-R6).
6. `text_routes.py`: the emitter before both `return result` (POST, GET); the stream emitter at the end of the
   M18 CD-interactions-01 success block, `complete_response.get("success") is True` only.
7. `url_routes.py`: the emitter with `compare_ms=int((time.time() - _start) * 1000)` before `return result`.
8. `home_routes.py`: `_result_status_supported` (unflagged reader keyed on the stored stamp; absent / non-dict ->
   True); the early `(None, None)` in `_extract_winner_loser_prices`; the `continue` in `_select_smart_pick` (Q5).
9. `feedback_routes.py` / `feedback_service.py`: the two allowlist groups (append-only), `Literal`, the three
   optional fields, the three kwargs threaded and written only when not None.
10. E1: `ENABLE_RESULT_STATUS_METADATA` in the FY25 `UNIT_ENV` (the nine digests unchanged, 3/3 green).
11. CLAUDE.md: the `**SESSION 80 flag (B1, ...)**` block after the B3-B block and before `## Tests` (content per
    spec 8.1, amended: B1-R1 sampler rule, B1-R6, B1-R7, GA-1 explicit-pair limit, GA-2 buckets, the Q7 limit, CR1
    as the precondition); the :105 `/feedback` line rewritten in place. GA-8's rebase onto 4a38ce93 and the row's
    placement after the H0 block are the orchestrator's (the row sits at the base's anchor).

## Runs (every [pyt] line verbatim; counts = passed unless stated)

Unit ON 187 | `[pyt] tag=b1green-unit-on start=2026-10-20 03:41:39 end=2026-10-20 03:41:47 elapsed=8s bound=600s status=OK rc=0`
Unit OFF 187 | `[pyt] tag=b1green-unit-off start=2026-10-20 03:41:48 end=2026-10-20 03:41:56 elapsed=8s bound=600s status=OK rc=0`
Feedback 27 | `[pyt] tag=b1green-unit-fb start=2026-10-20 03:41:57 end=2026-10-20 03:42:00 elapsed=3s bound=600s status=OK rc=0`
Unit ON 187 (after the C420 touch) | `[pyt] tag=b1green-unit-on2 start=2026-10-20 03:47:27 end=2026-10-20 03:47:36 elapsed=9s bound=600s status=OK rc=0`
Unit OFF 187 (idem) | `[pyt] tag=b1green-unit-off2 start=2026-10-20 03:47:36 end=2026-10-20 03:47:45 elapsed=8s bound=600s status=OK rc=0`
Feedback 27 (idem) | `[pyt] tag=b1green-unit-fb2 start=2026-10-20 03:47:45 end=2026-10-20 03:47:48 elapsed=3s bound=600s status=OK rc=0`
[hermeticity] sentinel checked 187 / 187 / 27; [netguard] blocked 0 on every unit run.

Spec 1.10 run 1 (5 files) 119 | `[pyt] tag=b1green-run1 start=2026-10-20 03:42:45 end=2026-10-20 03:42:50 elapsed=5s bound=600s status=OK rc=0`
Identity pins alone: test_s75_fanout_identity.py 3 | `[pyt] tag=b1green-id-fy25 start=2026-10-20 03:42:51 end=2026-10-20 03:42:55 elapsed=4s bound=600s status=OK rc=0`
test_w4_13_flag_off_ledger.py 2 | `[pyt] tag=b1green-id-w413 start=2026-10-20 03:42:56 end=2026-10-20 03:42:59 elapsed=4s bound=600s status=OK rc=0`
test_stage_timings.py 2 ([netguard] blocked 18 from 2 nodes, egress api.openai.com -- the base baseline class) | `[pyt] tag=b1green-id-stage start=2026-10-20 03:43:00 end=2026-10-20 03:43:09 elapsed=9s bound=600s status=OK rc=0`
test_s71_u13_compare_auth_required.py 137 | `[pyt] tag=b1green-id-u13 start=2026-10-20 03:43:10 end=2026-10-20 03:43:15 elapsed=5s bound=600s status=OK rc=0`
test_paid_route_metering.py 21 ([netguard] blocked 2 sentinel attempts, baseline) | `[pyt] tag=b1green-id-meter start=2026-10-20 03:43:15 end=2026-10-20 03:43:19 elapsed=4s bound=600s status=OK rc=0`
test_sentry_channels_u8d_unit.py 141 | `[pyt] tag=b1green-id-u8dunit start=2026-10-20 03:43:20 end=2026-10-20 03:43:29 elapsed=10s bound=600s status=OK rc=0`
test_observability.py 24 | `[pyt] tag=b1green-id-obs start=2026-10-20 03:43:30 end=2026-10-20 03:43:33 elapsed=3s bound=600s status=OK rc=0`
test_retro_w1_1.py 39 | `[pyt] tag=b1green-id-retro start=2026-10-20 03:43:34 end=2026-10-20 03:43:42 elapsed=7s bound=600s status=OK rc=0`
test_sentry_channels_u8d.py 131 | `[pyt] tag=b1green-id-u8dchild start=2026-10-20 03:43:42 end=2026-10-20 03:43:48 elapsed=6s bound=600s status=OK rc=0`

Flag-ON smoke (ENABLE_RESULT_STATUS_METADATA=true exported on the runner call only; information): run1 119 |
`[pyt] tag=b1green-smoke-run1 start=2026-10-20 03:47:49 end=2026-10-20 03:47:54 elapsed=5s bound=600s status=OK rc=0`;
run2 7 | `[pyt] tag=b1green-smoke-run2 start=2026-10-20 03:47:54 end=2026-10-20 03:48:06 elapsed=11s bound=600s status=OK rc=0`;
run3 225 | `[pyt] tag=b1green-smoke-run3 start=2026-10-20 03:48:06 end=2026-10-20 03:48:21 elapsed=15s bound=600s status=OK rc=0`.
No existing pin reddens under the flag (the FY25 node stays green through E1's UNIT_ENV pop).

Comm set at HEAD (305 files = the RED list 288 UNION 17 walks-app-by-path files; 13 chunks of <= 25, bound 1200,
the four NETWORK_FLAKY_EXCLUDE node ids deselected on every chunk; `scripts/comm_set.py` does not exist in the
tree, so the list is `comm_set_green.py`'s union rule over `tests/*.py` at HEAD):
chunk00 788 | `[pyt] tag=b1green-comm-00 start=2026-10-20 03:48:21 end=2026-10-20 03:48:58 elapsed=37s bound=1200s status=OK rc=0`
chunk01 3 failed, 997 | `[pyt] tag=b1green-comm-01 start=2026-10-20 03:48:58 end=2026-10-20 03:50:08 elapsed=69s bound=1200s status=FAIL rc=1`
chunk02 518 | `[pyt] tag=b1green-comm-02 start=2026-10-20 03:50:08 end=2026-10-20 03:50:26 elapsed=18s bound=1200s status=OK rc=0`
chunk03 2989 | `[pyt] tag=b1green-comm-03 start=2026-10-20 03:50:27 end=2026-10-20 03:51:56 elapsed=90s bound=1200s status=OK rc=0`
chunk04 594 | `[pyt] tag=b1green-comm-04 start=2026-10-20 03:51:57 end=2026-10-20 03:52:33 elapsed=36s bound=1200s status=OK rc=0`
chunk05 465 | `[pyt] tag=b1green-comm-05 start=2026-10-20 03:52:33 end=2026-10-20 03:52:52 elapsed=19s bound=1200s status=OK rc=0`
chunk06 4 failed, 580 | `[pyt] tag=b1green-comm-06 start=2026-10-20 03:52:53 end=2026-10-20 03:53:27 elapsed=35s bound=1200s status=FAIL rc=1`
chunk07 343, 2 errors | `[pyt] tag=b1green-comm-07 start=2026-10-20 03:53:28 end=2026-10-20 03:53:53 elapsed=26s bound=1200s status=FAIL rc=1`
chunk08 1642 | `[pyt] tag=b1green-comm-08 start=2026-10-20 03:53:54 end=2026-10-20 03:56:36 elapsed=163s bound=1200s status=OK rc=0`
chunk09 1197 | `[pyt] tag=b1green-comm-09 start=2026-10-20 03:56:36 end=2026-10-20 03:57:50 elapsed=74s bound=1200s status=OK rc=0`
chunk10 367 | `[pyt] tag=b1green-comm-10 start=2026-10-20 03:57:51 end=2026-10-20 03:58:39 elapsed=49s bound=1200s status=OK rc=0`
chunk11 1152, 35 xfailed | `[pyt] tag=b1green-comm-11 start=2026-10-20 03:58:40 end=2026-10-20 03:59:24 elapsed=45s bound=1200s status=OK rc=0`
chunk12 (5 files) 81 | `[pyt] tag=b1green-comm-12 start=2026-10-20 03:59:25 end=2026-10-20 03:59:36 elapsed=11s bound=1200s status=OK rc=0`
HEAD failures (9): tests/test_camera_vision.py::TestIdentifyProductsMocked::{test_empty_product_fields_normalized,
test_malformed_response_returns_error, test_successful_identification}; tests/test_page_scraping.py::TestFetchPagePriceJsonLD::
test_jsonld_nested_offers_picks_lowest; tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction;
tests/test_personalization_bundle_c.py::{test_applied_shifts_list_is_default_empty_when_no_priorities,
test_full_response_payload_audit_no_magnitude_keys} (the seven .pre_impl_failures.txt nodes the RED base run recorded);
tests/test_prompt_truth.py::{test_render_digests_match_base_except_the_fence, test_truth_on_prefix_static_and_cacheable}
(ERROR: the netguard refusing the cold tiktoken download `openaipublic.blob.core.windows.net`; the file was not in the RED
base list, so it was re-run ALONE at base in a detached scratch worktree at 81df2b64 (removed afterwards; `git worktree list`
clean) and at HEAD -- identical 2 errors, same two node ids, same cause):
base 31 passed, 2 skipped, 1 xfailed, 2 errors | `[pyt] tag=b1green-pt-base start=2026-10-20 04:01:19 end=2026-10-20 04:01:22 elapsed=3s bound=600s status=FAIL rc=1`
HEAD 31 passed, 2 skipped, 1 xfailed, 2 errors | `[pyt] tag=b1green-pt-head start=2026-10-20 04:01:23 end=2026-10-20 04:01:26 elapsed=3s bound=600s status=FAIL rc=1`
branch-only-NEW = HEAD failures minus base failures = EMPTY. The unit's 191 RED rows (red at base) pass at HEAD.

CI-order set (20 files alphabetical, one process: the two unit files, the pin files above, test_w4_13_measurement_truth.py,
test_comparison_id_echo.py, the two CLAUDE.md readers) 1155 | `[pyt] tag=b1green-ci-order start=2026-10-20 03:59:36 end=2026-10-20 04:00:20 elapsed=44s bound=1200s status=OK rc=0`

Lint: `ruff check --select E9,F63,F7,F82 --no-cache` clean on all 11 python files; `py_compile` clean; full default ruff
before == after per edited file (3/21/0/6/10/12/4/4/0 pre-existing findings, none added) and 0 on result_gate.py after the
C420 fix; the pre-commit hook passed. Added-line sweep (git diff 81df2b64 + the new files, 2249 lines): sk-/AKIA/xox/JWT/PEM/
credentialed-URL 0, @gmail 0, +973 0, owner names 0, 8-digit runs 3 = the frozen RED files' synthetic UUID literals.

Counts: RED rows 191 green at HEAD (167 + 24); PIN rows 23 green at HEAD in both states (20 + 3); unit total 214 = 187 + 27.
Mutants: not re-run by GREEN (the RED agent killed 35/35 on the prototype; the adversaries run them on these bytes; X19 is the
correctness adversary's hand mutant, GA-4).

## Deviations (each measured; nothing silently applied to a spec, review or ruling file)

1. B1-R11 Q7 (the `result_status` skip in profile_routes.py:75/:97/:141 "with a P8-style pin") is NOT implemented: the frozen
   RED files carry no row for profile_routes and the gate (GA-6) made the RED files the contract; an unpinned reader change
   would violate R-A13. Recorded as a stated limit in the CLAUDE.md row and the PR body; needs a RED row (a fix round) or a
   ruling deferring it to C1 (spec L13 stands).
2. The emitter `capture_result_status` itself refuses a non-dict or non-success body (in addition to the site gates the
   rulings name: camera B1-R6, stream `success is True`): one more line of defence, no behaviour difference on any exit.
3. The sampler's final fallback constant is named `_TRACES_SAMPLE_RATE_FALLBACK` (0.1) and is reached only when no client
   carries a rate or the sampler raises (B1-R1 wording honoured: the live option first, never the constant alone).
4. The comm set is 305 files, not the RED's 288: the union rule's "every test that walks or reads app/ by path" was applied
   by grep at HEAD and added 17 files (one of them tests/test_prompt_truth.py, whose two cold-tiktoken ERRORs are identical
   at base and HEAD, measured alone on both sides).
5. GA-8's rebase onto origin/main 4a38ce93 and the row placement after the H0 block are left to the orchestrator (the task
   forbids a rebase here); the row sits at the base's anchor (after the B3-B block, before `## Tests`).
6. One post-run touch on the new module (ruff C420, `dict.fromkeys`) after the first green; the unit files were re-run in
   both states (187 / 187 / 27) and the module was re-byte-checked (25797 B, 0 > 127).

## Questions for the gate / the adversaries

1. B1-R11 Q7: run a fix round that adds a RED row for profile_routes (the home_routes pattern) and the hunk, or defer to C1?
2. The 17 walks-app-by-path files: keep them in the unit's comm set definition (the RED list lacked them)?
3. tests/test_prompt_truth.py: the two cold-tiktoken ERRORs fire on this box under the netguard in BOTH trees; the brief's
   wording ("record them identically at base and head") is satisfied; CI warms the cache (R22), so no CI red is expected.

## NOT MEASURED

- Mutation run on the GREEN bytes (the adversaries' step; X19 by hand per GA-4).
- The W4-11 render-digest fixture, the T23 OpenAPI fixture: not regenerated (no prompt, no route parameter change);
  tests/test_s71_u13_compare_auth_required.py 137 passed at HEAD is the evidence.
- Nothing TIMEOUT; nothing re-run for a timeout.

`git status --short` at the end: empty (everything committed on feature/s80-b1-result-status at 2bbd58a9; the two RED files
committed byte-identical to the frozen rows). Scratch worktree <scratchpad>/B1_green/scratch_base removed; `git worktree
list` carries no B1_green entry. No .qa-mutation.lock was created (no mutation run).
