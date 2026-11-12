# S81-07 MEAS-CLAUDE-GATE: ADVERSARY REPORT, lens CORRECTNESS (Opus 5.5, 2026-11-12, 06:53-07:40 AST)

Written by a shell python step. Unit worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s07, branch
feature/s81-07-meas-claude-gate, HEAD f10c6ae34fcf72232f88362e094801bad954a80c VERIFIED at start and at end;
git status --short of the unit worktree empty at the end (never edited). Every probe and mutant ran in my own
detached scratch worktree <scratch>/S81-07_green/adv_correctness at f10c6ae3 (python only, no junction), removed with
git worktree remove --force, absent from git worktree list, path gone; the mutated file sha256-verified after every
restore (44f6eb83... = the committed blob); .qa-mutation.lock created and removed. No network, no live API, no
variable set in any shell, no .env read, no secret printed.

VERDICT: NOT_READY (0 blocking, 3 major, 8 minor).

## Runs ([pyt] lines)
- Unit file on a fresh scratch checkout (autocrlf CRLF fixtures): [pyt] tag=s07g-advc-unit start=2026-11-12 06:54:22,
  1 failed / 163 passed in 38.35s (test_r35_fixtures: a CR byte in a fixture), [hermeticity] sentinel checked 164
  test(s), [netguard] blocked 0 attempt(s) from 0 node(s). (Its final [pyt] status line was lost with the detached
  shell; the log holds the summary.)
- Unit file on the LF blob bytes (script 44f6eb83..., RED 30ac9d7b..., fixtures from git show):
  [pyt] tag=s07g-advc-unit2 start=2026-11-12 06:59:04 end=2026-11-12 06:59:38 elapsed=34s bound=600s status=OK rc=0
  164 passed, 1 warning in 30.21s; [hermeticity] sentinel checked 164 test(s); [netguard] blocked 0 attempt(s).
- 37 mutants of my own (table below): each [pyt] tag=s07g-advc-A<nn> bound 600, the whole unit file.
- Probes: [pyt] tag=s07g-advc-probe start=2026-11-12 07:32:56 end=2026-11-12 07:33:05 elapsed=10s bound=600s
  status=FAIL rc=1 (2 failed, 1 passed: the failures ARE findings MAJ-2 and m5; netguard 0).
- Offline python probes (no pytest, a socket guard, no credential name): fidelity_probe.py -> fidelity.json,
  bars_probe.py. Every pytest waited on the foreign-process probe (waitfree.ps1); the longest wait about 3 minutes.

## Fidelity (R-S07-8), independent capture
fidelity_probe.py ran the harness's own A1 builder sequence (rounds 0, 7, 13 of compare_pairs.json) twice: once with
the harness's _capture (route spy + to_claude_request) and once with an INDEPENDENT capture through the router's real
route() (role_enabled / decide patched to the Claude branch, _dispatch_claude spied). 48 / 48 requests equal (16 per
round; caps: classify 32, parse 768, specs 1536 x2, price 512 x2, image_tier3 256 x2, reviews 1024 x2, verdict 1536,
price_training 384, specs_targeted 384, specs_synthesized 512, disambiguate 256, url_extract 1200; model
claude-haiku-5-5). The Dispatcher passes exactly the captured request + timeout=25.0 to messages.create (the router's
create sends the same keys; system as NOT_GIVEN when empty). 0 sockets blocked. Moderation: the harness's fake
rebuilds {model, system, messages, max_tokens, thinking, output_config} = the keys the router's
guarded_anthropic_create passes to messages.create (llm_router.py:960-978 at HEAD). Pinned SDK measured:
AsyncMessages.count_tokens accepts output_config / system / thinking (the A5 request is legal); models.retrieve(model_id).

## A1 shape and call counts (R-S07-17)
A1_ROUND_ORDER = classify, parse, Phase 1 {specs x2, price x2, image_tier3 x2} (gather), Phase 2 {reviews x2}
(gather), verdict, price_training, specs_targeted, specs_synthesized, disambiguate, url_extract = 16 per round, 20
rounds = 320; A0 2 (Haiku + Sonnet ids), A2 40, A3 20, A4 100, A5 20, A6 120 (60 x reps 2) = 622 <= 700. Spacing 30 s
via _sleep between rounds; tail_span_ms = Phase 2 start to verdict end. Matches; GREEN's dry_all2.json shows the same.

## Pass bars recomputed by hand (bars_probe.py on synthetic results)
- TEXT, every non-verdict site 19/20 JSON-valid: pooled 209/220 = 0.95 < 0.98 -> NO-GO [json_valid_pooled_min]; each
  site 0.95 >= 0.90 passes. Script: ('NO-GO', ['json_valid_pooled_min']). Match.
- TEXT, 2 max_tokens hits at each of 11 sites: pooled 22/220 = 0.10 > 0.02 fails; per site 2 <= 2 passes. Script:
  ('NO-GO', ['max_tokens_pooled_max']). Match.
- MODERATION fp 0, recall 18/20 = 0.90, fail-closed 1, p95 3.0, all ON the bars -> GO. Script ('GO', []). Match.
- VISION Haiku 0.80 / Sonnet 0.85 (diff -0.05 ON the bar after the 9-decimal round) -> GO; Sonnet 0.86 -> NO-GO
  [haiku_minus_sonnet_min]. Match.
- VERDICT A1 20/20 + A6 118/120 = 138/140 = 0.9857, mismatch 12/120 = 0.10, agreement 0.90, refusals 1 -> GO;
  A6 116/120 -> 136/140 = 0.9714 -> NO-GO [json_valid_pooled_min]. Match. CRITIC / WEB_SEARCH -> NOT RUN.

## Mutation table (my own, 37; KILLED = an assertion failure of the unit file; first killing row shown)
A01_json_valid_counts_unparsable SURVIVED - elapsed=34s bound=600s status=OK rc=0
A02_schema_accepted_counts_400 SURVIVED - elapsed=31s bound=600s status=OK rc=0
A03_a4_arabic_uses_all SURVIVED - elapsed=37s bound=600s status=OK rc=0
A04_a6_mismatch_inverted KILLED test_r33_verdict_eval_plan elapsed=45s bound=600s status=FAIL rc=1
A05_a6_agreement_always_one SURVIVED - elapsed=34s bound=600s status=OK rc=0
A06_m1_fail_closed_drops_refusal SURVIVED - elapsed=34s bound=600s status=OK rc=0
A07_eval_text_site_min_le KILLED test_r72_go_exactly_on_every_bar[TEXT] elapsed=37s bound=600s status=FAIL rc=1
A08_eval_vision_diff_reversed KILLED test_r72b_one_bar_crossed[VISION-haiku_minus_sonnet_min] elapsed=36s bound=600s status=FAIL rc=1
A09_eval_moderation_recall_le KILLED test_r72_go_exactly_on_every_bar[MODERATION] elapsed=42s bound=600s status=FAIL rc=1
A10_sticky_stop_removed KILLED test_r66_sticky_stop_inflight_sends_awaited elapsed=46s bound=600s status=FAIL rc=1
A11_transient_gt KILLED test_r24_three_consecutive_transient[seq0-True-3] elapsed=70s bound=600s status=FAIL rc=1
A12_rate_limit_retries_gt KILLED test_r25_rate_limit_retry_after[header0-2] elapsed=42s bound=600s status=FAIL rc=1
A13_5xx_unbilled KILLED test_r44_booking_table elapsed=43s bound=600s status=FAIL rc=1
A14_unmatched_intent_not_booked KILLED test_r46_unmatched_intent_booked_and_resent elapsed=55s bound=600s status=FAIL rc=1
A15_nontransient_not_completed_on_readback SURVIVED - elapsed=100s bound=600s status=OK rc=0
A16_stream_usage_none_overwrites KILLED test_r38_stream_ttft elapsed=47s bound=600s status=FAIL rc=1
A17_percentile_floor_rank KILLED test_r55_percentiles_and_proposals elapsed=35s bound=600s status=FAIL rc=1
A18_ceil_half_round KILLED test_r55_percentiles_and_proposals elapsed=37s bound=600s status=FAIL rc=1
A19_settle_skips_unit SURVIVED - elapsed=37s bound=600s status=OK rc=0
A20_tail_span_from_round_start SURVIVED - elapsed=37s bound=600s status=OK rc=0
A21_max_calls_gt KILLED test_r14_request_equals_router elapsed=38s bound=600s status=FAIL rc=1
A22_request_guard_no_scheme KILLED test_r69_client_hook_refuses_other_urls elapsed=40s bound=600s status=FAIL rc=1
A23_key_inner_space_allowed KILLED test_r54b_key_malformed_refused[a elapsed=43s bound=600s status=FAIL rc=1
A24_a4_arabic_needs_both SURVIVED - elapsed=36s bound=600s status=OK rc=0
A25_identity_hit_brand_only KILLED test_r73_vision_identity_rule elapsed=36s bound=600s status=FAIL rc=1
A26_eval_text_includes_verdict SURVIVED - elapsed=40s bound=600s status=OK rc=0
A27_m1_p95_is_p50 SURVIVED - elapsed=40s bound=600s status=OK rc=0
A28_timeouts_never_counted SURVIVED - elapsed=36s bound=600s status=OK rc=0
A29_ledger_negative_usd_accepted KILLED test_r47_corrupt_ledger_refuses[{"call_id": elapsed=37s bound=600s status=FAIL rc=1
A30_reserve_ignores_unit SURVIVED - elapsed=37s bound=600s status=OK rc=0
A31_w_citations_zero KILLED test_r74_web_search_accept_and_reject elapsed=36s bound=600s status=FAIL rc=1
A32_retry_after_no_min SURVIVED - elapsed=35s bound=600s status=OK rc=0
A33_eval_text_maxtok_site_ge KILLED test_r72_go_exactly_on_every_bar[TEXT] elapsed=36s bound=600s status=FAIL rc=1
A34_prior_completed_dropped_from_pool SURVIVED - elapsed=35s bound=600s status=OK rc=0
A35_report_always_go SURVIVED - elapsed=29s bound=600s status=OK rc=0
A36_tail_proposal_p50 SURVIVED - elapsed=35s bound=600s status=OK rc=0
A37_classify_proposal_from_verdict SURVIVED - elapsed=31s bound=600s status=OK rc=0

Counts: 19 KILLED, 18 SURVIVED. A19 (settle skips unit_spent) and A30 (reserve ignores the unit term) are EQUIVALENT
under start step 7 (unit_on_disk + max_usd <= 15 and spent <= the stage cap imply the in-run unit term never binds);
A19 still mis-reports results.json unit_spent_usd (unpinned). The other 16 survivors are the evidence below.

## Findings

### MAJOR
- MAJ-1 THE GO / NO-GO OUTPUT AND ITS INPUTS ARE UNPINNED (GC-12, GC-16, R-S07-7). The rows pin evaluate_role on
  hand-written fixtures (R72 / R72b / R72c), but NO row ties the summary that writes those shapes from the ledger
  records to a figure, and NO row reads a verdict from REPORT.md. Surviving mutants: A35 the top REPORT table prints
  ("GO", []) for every role whatever the results; A01 A1 json_valid counts unparsable answers as valid; A02
  schema_accepted counts a 400 as accepted; A03 / A24 the A4 Arabic refusal count and the Arabic classification; A05
  A6 agreement always 1.0; A06 M1 fail_closed drops refusals; A27 M1 p95 replaced by p50; A28 A1 timeouts never
  counted; A26 TEXT pools the verdict site; A36 / A37 the tail and classify proposals from the wrong percentile /
  site. Each can turn a NO-GO into a GO (or a wrong knob proposal) in the bytes the owner reads, with 164 / 164 green.
  The code reads correct to me today (re-derived above): a coverage defect on a FOCUS unit's decision path. Fix: rows
  that run a stage on scripted fakes (unparsable JSON, a 400 at a format site, an Arabic-name refusal, rep 0 / rep 1
  disagreement, a moderation refusal, a timeout) and assert the results.json metric AND the REPORT.md verdict cell;
  one row asserting the three proposal values from a known results set.
- MAJ-2 A RESUME CORRUPTS THE TAIL PROPOSAL (R-S07-20; R-S07-4 "a re-run RESUMES"). _run_a1 appends a tail_span_ms
  for every round, including rounds whose calls are completed in the ledger and replay with no send: their span is
  about 0 ms, and the spans of the earlier run are not carried (meta is per run). PROBE (fake clock, 1 s per create):
  run 1 --max-calls 32 -> spans [3000.0, 3000.0]; resume --max-calls 16 -> spans [0.0, 0.0, 3000.0]. A text stage
  stopped after A1 (in A4 / A6 by transient / budget / max_minutes) and resumed replays all 20 rounds: every span 0, so
  REPORT.md proposes ANTHROPIC_TAIL_RESERVE_SECONDS 0.0 beside the current 6.5. A20 (span from the round start) and
  A34 (earlier runs' completed calls dropped from every metric) also survive: the resume path of the metrics has no
  row. Fix: record a span only when the round's Phase 2 and verdict were sent in this run, or derive spans per round
  from the ledger; a resume row.
- MAJ-3 RULED REPORT FIGURES ARE MISSING WHILE CLAUDE.md AND THE PR BODY SAY THEY ARE REPORTED. R-S07-31 "REPORTED,
  NOT A BAR: the cost per synthetic compare (p50, p95) and the compares per day it allows under the breaker's live
  cap": no code computes either (no per-compare cost, no breaker cap read; REPORT.md prints setting totals only).
  CLAUDE.md block (the PASS BARS bullet) says "Reported, not a bar: the cost per synthetic compare and the three
  timeout proposals"; PR_BODY.md line 113 the same. R-S07-2 "the cache_read share": not computed (the ledger holds
  cache_read_tokens per call only), while PR_BODY.md L3 says "the cache_read share measures automatic caching only".
  R-S07-23 "the sensitive-looking subset is reported": the A4 metrics hold n / refusals / n_arabic / refusals_arabic
  only (fragrance_names.json carries 20 rows of group "sensitive"; nothing reports them). Fix: compute and print the
  per-compare cost p50 / p95 over the A1 rounds, compares per day under the breaker's live cap, the cache_read share
  per site and the sensitive-subset refusal count; or rule them dropped and correct CLAUDE.md and the PR body.

### MINOR (documentation rulings / stated limits)
- m1 A fresh Windows checkout with core.autocrlf=true gets CRLF fixtures and a red R35 (reproduced: 1 failed / 163
  passed); the blobs are LF and the unit file is 164 / 164 on them. Stated by the gates report D2; the harness itself
  parses CRLF JSON fine.
- m2 A15 survives: the read-back marks a call completed only on ok (no row resumes a 400 / 409), so "a re-run never
  re-sends a completed call_id" for a non-transient error has no row (spend effect 0 for a 400, worst case for a 409).
- m3 A32 survives: a retry-after of 0 (or negative): the 1 s floor has no row.
- m4 REPORT.md prints the current knob values as literals (4.0, 20.0, 6.5) instead of reading the router's knob
  functions; the tail line omits the censored count, and a timed-out tail leg enters tail_span_ms as a finite span,
  not +inf (R-S07-19 "every proposal prints the number of censored samples").
- m5 PROBE: an APIStatusError with an unlisted status (402, 408, 410, 418, 451: measured on the pinned SDK, class
  APIStatusError) crashes the stage (exit 3, "crashed class=APIStatusError"), booked at the worst case. The spec
  failure table says "any other exception -> 3", so this is the contract, but a deterministic one can never be passed
  by a resume (the call is not completed). CLAUDE.md "a 4xx rejection books 0" is wider than the code (409 and the
  unlisted 4xx book the worst case; L14 states 409 only).
- m6 PROBE: start step 7 counts the stage's own prior spend twice (in unit_spent and as the full max_usd): with 13.2 USD
  on disk (web_search 2.5 of 3.0) a web_search resume is refused unit_ceiling (exit 4) although the stage has 0.5 and
  the unit 1.8 left; the operator must pass a lower --max-usd. Literal contract text; the refusal could say so.
- m7 VISION hit_rate and the A6 mismatch rate divide by successful calls only (failed calls leave n_scored), so errors
  do not lower those rates (A6 json_valid does count them). A choice, unstated.
- m8 An unreadable --flags-file or --set path (FileNotFoundError) is a crash (exit 3), not a refusal (exit 2); the
  vision mime type is png-or-jpeg by file extension only.

## Prove-nothing rows (each shown by a surviving mutant)
R29 (role rows exist, no verdict cell read: A35); R56b (one span counted, its value never: A20); R33 (mismatches only;
agreement A05 and A1 json_valid A01 unread); R72 / R72b / R72c (fixtures hand-written, no stage-to-summary link: A01-A03,
A06, A24, A26-A28); R55 (proposal math only, not the report's inputs: A36, A37); R25 (retry-after 2 / missing / 999, no
floor case: A32); R21 / R46 (resume of an ok / unmatched call only: A15, A34).

## Footprint and comm set
- git diff --stat 6b909e0a..f10c6ae3: CLAUDE.md (+11 / -1), scripts/meas_claude_gate.py, tests/_env_safety.py (+1),
  tests/fixtures/s81_s07/{_gen_fixtures.py + 5 json}, tests/test_s81_s07_meas_harness.py. Nothing under app/, no
  requirements file, no client file, no .github, no migration (R-S07-1 holds). Every new blob 0 CR and 0 bytes > 127
  (CLAUDE.md's non-ASCII bytes pre-exist). RED blob sha256 30ac9d7b... = the step-0 sha of the amendments' GATE section.
- Comm list (182 members, comm_list_head.txt) against my derivation (every tests/*.py reading _env_safety /
  CREDENTIALS_UNSET / CLAUDE.md / the unit names or walking with glob / rglob / os.walk / listdir / scandir / iterdir,
  plus every scripts-path reader): the non-members are the excluded pre-commit hook files, the RED file itself, the
  helpers (conftest, _netguard, _env_safety, _retro_r_mig_sql, two generators), test_s81_d16_operator_ingest.py (a
  docstring mention only) and six readers of OTHER named scripts (eval_runner, build_cohorts, seed_kb_merchants,
  cron_robots_registry; not walkers). No missing member found.

## Numbers of the reports and CLAUDE.md checked against the bytes
622 / 320 / 40 / 20 / 100 / 20 / 120 calls, 1.443 / 0.261 / 3.612 / 1.331 USD (dry_all2.json), caps 4 / 2 / 5 / 3 and
15.00, exit codes 0 / 2 / 3 / 4 / 5 / 6 / 130, the 60,000-token search bound, retry-after at most 60 s three times, the
refused-name rule, the guard in every mode, the lock on every exit, 164 nodes, the sha table of the GREEN report: all
match. Wrong or unbacked: "cost per synthetic compare" and "cache_read share" (MAJ-3); "a 4xx rejection books 0" (m5).
The GATES report's 78 / 78 killed was not re-run; my 37 add the survivors above.

## Files (notes folder <scratch>/S81-07_green/adv/correctness_notes)
mutants_adv.py, mut_driver.py, mut_results.json, mut_summary.txt, mut_A*.log, unit.log, unit2.log, fidelity_probe.py,
fidelity.json, bars_probe.py, test_zz_adv_probe_s07.py (copied into the scratch tests/ for the run, deleted there),
adv_probe.json, probe.log, comm_members.txt, cand.txt, cand_missing.txt, llm_router.py (a git show HEAD copy).
