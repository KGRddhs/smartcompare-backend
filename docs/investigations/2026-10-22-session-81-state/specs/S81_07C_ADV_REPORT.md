# S81-07c CLAUDE-ROLE-FIX: ADVERSARY report (correctness lens + the folded second lens; Opus 5.5; written through the shell)

VERDICT: SOUND. Blocking 0, major 0, minor 3 (each a stated limit by default, LC-4).

- HEAD verified: W = C:/Users/SynAckITPC/Documents/AI/sc-s81-s07c, branch feature/s81-07c-role-fix, HEAD 1da03aff3bbb784b5f83656158405260f5874b71 (one commit on c6ebbd2ed593081cb6241915c36ae29af4c29bca); `git status --short` empty at 23:15 and at the end; nothing written in W.
- Window: first tool call 23:15:33, report about 00:02 (budget 00:45).
- Read in full at the start and again before this report: s81-common.txt, GATE_S81_07C.md, S81_07C_UNIT_SPEC.md, red/S81_07C_RED_REPORT.md, red/E_ROWS.md, red/proto.diff; also green/S81_07C_GREEN_REPORT.md, gates/S81_07C_GATES_REPORT.md, gates/PR_BODY.md.
- Every probe and mutant ran in my own detached scratch worktree <adv>/wt at 1da03aff (python only, no junction), removed with `git worktree remove --force` (rc 0; absent from `git worktree list`; directory gone). Every pytest went through harness/pyt.py behind waitfree.ps1 -OwnTagPrefix s07c- (`free poll=0` each time) and a 20 s settle; no TIMEOUT, no DUPLICATE; no process killed.
- Diff: 9 files, +690 / -23 (CLAUDE.md 13, extraction_service 27, llm_router 15, structured_comparison_service 2, meas_claude_gate 9, s06 11, s07 harness 9, the RED file 625 new, s22b 2); no whole-file diff; every added byte ASCII except the rewritten CLAUDE.md :341 line, whose 63 non-ASCII bytes are pre-existing (63 before and after; the inserted sentence is pure ASCII). RED file sha256 a197e2f2... (working copy and blob; LF; 0 bytes > 127).

## Every [pyt] line of this round

```
[pyt] tag=s07c-adv-probe1 start=2026-11-12 23:33:57 end=2026-11-12 23:34:25 elapsed=28s bound=600s status=OK rc=0 | 4 passed | [hermeticity] sentinel checked 4 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s07c-adv-doubt-head start=2026-11-12 23:41:07 end=2026-11-12 23:41:29 elapsed=22s bound=1200s status=OK rc=0 | 522 passed, 51 deselected | [hermeticity] sentinel checked 522 test(s) | [netguard] blocked 8 attempt(s) from 8 node(s)
[pyt] tag=s07c-adv-mut-MX1 start=2026-11-12 23:43:29 end=2026-11-12 23:43:36 elapsed=7s bound=600s status=OK rc=0 | 17 passed
[pyt] tag=s07c-adv-mut-MX2 start=2026-11-12 23:44:01 end=2026-11-12 23:44:09 elapsed=7s bound=600s status=OK rc=0 | 17 passed
[pyt] tag=s07c-adv-mut-MX3 start=2026-11-12 23:44:34 end=2026-11-12 23:44:42 elapsed=7s bound=600s status=OK rc=0 | 17 passed
[pyt] tag=s07c-adv-mut-MX4 start=2026-11-12 23:45:22 end=2026-11-12 23:46:43 elapsed=80s bound=600s status=FAIL rc=1 | 7 failed, 197 passed
[pyt] tag=s07c-adv-mut-MX5 start=2026-11-12 23:47:09 end=2026-11-12 23:47:38 elapsed=30s bound=600s status=FAIL rc=1 | 2 failed, 429 passed
[pyt] tag=s07c-adv-probe2 start=2026-11-12 23:48:52 end=2026-11-12 23:48:56 elapsed=5s bound=600s status=OK rc=0 | 1 passed, 4 deselected | [hermeticity] sentinel checked 1 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s)
```

No jest run (the fences are the GATES round's; no client file in the diff).

## Named checks

C1 THE EVALUATION IS NOT WEAKENED: PASS.
- `git diff c6ebbd2e 1da03aff -- scripts/meas_claude_gate.py` = exactly two hunks: @@ -1688 (A1 verdict builder: `score_winner_index=1` + a 2-line comment, :1694) and @@ -1785 (A6 builder: `score_winner_index=c["gold_winner_index"]` + a 1-line comment, :1794). A6_SENTENCE, GO_THRESHOLDS, `_metrics` (incl. the A6 arm), `evaluate_role`, the `_plan_text` gold read, the A1 round order and the report text are byte-identical by that diff. `tests/fixtures/` has an empty diff (the gold bytes unchanged; V11 pins the LF sha 78134acf...).
- Trace: `_gen_fixtures.py` verdict_gold: `res = svc.compute_scores([pa, pb])`, `gold_winner_index = res["winner_index"]`, stored as product_a = pa / product_b = pb, which the A6 builder passes as product1 / product2. Production: scs :4707 (REST) and :5569 (streaming) pass `scoring_result.get("winner_index")` with `scoring_result = scoring_service.compute_scores(product_data, ...)` and product_data[0] / [1] as product1 / product2. Same scorer, same order: the harness passes the value production passes. The scorer's winner_index is a plain int (`overalls.index(max(overalls))` or the literal 1, scoring_service :1600 / :1619; `_empty_result` only for fewer than 2 products).
- Note (no finding): with the index given, A6 measures adherence to the given index, which is the production WINNER_INDEX_MISMATCH rule A6_SENTENCE names; sentence and bars untouched (GC-11).

C2 THE BLOCK: PASS.
- `_FIXED_WINNER_BLOCK` (extraction_service :2558) equals the spec V3 bytes (V02), ASCII, LF; emitted at :2639 only for `type(x) is int and x in (0, 1)`, inside `if scores_summary:`, right after the scores f-string and before the preferences / cohort block; formatted with ints only (label = index + 1), so no product name or other user-influenced text enters the system message.
- Probe P1 (the BASE extraction_service loaded side by side from `git show c6ebbd2e:`, the route seam captured): 648 combinations (scores_summary SUMMARY / None / "" x user_preferences x a cohort profile with ENABLE_COHORT_PERSONALIZATION on x quality normal / weak / weird x output_lang None / ar (ENABLE_ARABIC_VERDICT_OUTPUT on) / en x ENABLE_GPT_WINNER x category fragrances / other / smartphones). HEAD no-keyword request == BASE request (system, user message, every kwarg) 648 / 648; nine invalid values (None, True, False, 2, -1, "1", "0", 1.0, 0.0) == BASE 5,832 / 5,832; valid 0 / 1 with a summary: the block once, directly after the cross-tier sentence and the scores block, removing it gives the BASE bytes, user message and kwargs unchanged, 432 / 432; valid with no summary == BASE 864 / 864. The URL-mode caller shape (no summary) is inside that set. For the verdict prompt this also covers what the two test_prompt_truth ERROR nodes (cold tiktoken cache) cannot measure on this box.

C3 THE CALLERS AND THE FLAG MIX: PASS.
- Both scs calls carry `score_winner_index=scoring_result.get("winner_index")` (V08, AST-exact); `scoring_result` is the compute_scores dict already `.get`-read a few lines above each call (`_vkey`; the SSE scores frame), so no new failure mode; url_extraction_service :1467 unchanged (V09).
- What the model reads (P3: end to end through the real chokepoints, fake clients): every ENABLE_ANTHROPIC_* unset -> the OpenAI create carries the block once (response_format json_object kept); ENABLE_ANTHROPIC_VERDICT ON + consent 3 -> guarded_anthropic_create -> the Claude system carries the block once and still ends with JSON_ONLY_INSTRUCTION, no format, 1536 tokens; VERDICT ON + consent < 3 + ENABLE_OPENAI_PRE_V3 ON -> one OpenAI call carrying the block (PRE_V3 OFF: ConsentUpdateRequiredError as at base). The 429 verdict_fallback call reuses the same system text (P5: block once, equal to the primary, with and without a cohort profile, three categories).
- What the user sees (P4 + reading): the shipped winner is the scorer's index in every state (reconcile_winner_prose, unchanged). Model index == scorer index -> the model's declaration, reason and tradeoff ship (RECONCILE ON or OFF); a residual mismatch -> RECONCILE OFF: declaration and tradeoff dropped, the qualitative reason line; ON: the deterministic fields. ENABLE_FULL_STREAM_DEADLINE ON: the verdict coroutine runs under wait_for(_tail_residual()); on expiry the deterministic partial ships and the block is moot; OFF: awaited directly (same control flow; the system text gained about 330 characters). ENABLE_GPT_WINNER ON: the independent winner stays log-only (GPT_WINNER_DISAGREES, no index override; response_builder :1582-1594). The OpenAI path reads the block too (unmeasured on OpenAI; the OpenAI credential is rejected today, as the CLAUDE.md block states).

C4 IMAGE_TIER3: PASS, with MINOR m1.
- SITES["image_tier3"] = SiteSpec("text", 256, None, True) (llm_router :218); the router diff is only the deleted constant, the SITES comment and that row. P2 (Claude branch, fake client): no `format`, output_config == {"effort": "low"}, thinking disabled, max_tokens 256, system == JSON_ONLY_INSTRUCTION; the fence strip applies (a bare fence and a json fence unwrap; T04 covers the upper-case JSON tag).
- The T4 escalation consequence (L3 as GC-5) is real: ENABLE_SONNET_ESCALATION ON with a bound request scope: a prose or truncated reply -> 2 Claude calls (claude-haiku-5-5, then claude-sonnet-5-5 with thinking between_tools), the compare's one escalation consumed; OFF -> 1 call, 0 escalations, the placeholder. Stated in CLAUDE.md :676 and in PR body L3, both in the GC-5 form.
- `git grep IMAGE_TIER3_SCHEMA 1da03aff -- .` (the whole repo: app, scripts, tests, SmartCompareApp, docs): only the CLAUDE.md block text and the RED T03 getattr; no importer.

C5 THE E-ROWS: PASS. Each committed hunk equals E_ROWS.md / proto.diff. E1 R02c: the equality with the deleted constant becomes `output_schema is None and expects_json is True` (T03 pins the constant gone; the vision_v2 / vision_v1 / disambiguate asserts untouched). E2 R01: one name leaves the exported list (T03 pins it gone). E4a R87: image_tier3 (40, 40) becomes disambiguate (20, 20) AND image_tier3 (0, 40, 40): stronger. E4b `_decision_run`: the scripted 400 moves from k 7 (image_tier3, no longer a schema site) to k 15; R88's own `(disambiguate schema_n, schema_accepted) == (20, 19)` proves k 15 is the disambiguate call, and R88's TEXT cell (json_valid_site_min, schema_accept_min, refusals_a4_max, refusals_a4_arabic_max, timeouts_max) is unchanged, so schema_accept_min stays exercised. E4c R88: disambiguate (20, 19) plus image_tier3 (0, 40). E5 s22b :79: the fourth field (schema is None) False -> True, the new truth (GC-1). None weakened.

C6 THE COMM SET: PASS.
- Re-derived independently by grep over the HEAD tree: module / symbol references (the four modules, generate_comparison, score_winner, IMAGE_TIER3_SCHEMA, image_tier3, SITES, to_claude_request, the reconcile and prompt symbols), source readers (app/ and scripts/ paths incl. leading-slash and f-string forms, getsource, ast.parse, __file__, walkers, string importlib), the CLAUDE.md readers, the importers of the three edited test modules. Every file my wider patterns found outside the 365-member list carries the term only in a docstring, comment or URL, or an unrelated SITES (tests/test_s81_s09_gate_rows.py imports the s09 SITES): no by-rule member is missing. Every named pin and every CLAUDE.md reader by the import graph is in the list.
- Branch-only-new recomputed from the GATES logs: HEAD 24 failed / error ids; the gates base chunks hold 15 and the reused RED base runs (red/base-c1.log, base-s2.log) the other 9 (test_prompt_truth x2, d22c P1 x5, s07 r35, s10 r06): identical sets, EMPTY. Every one of the 365 members is named in a HEAD chunk log.
- Doubt set: 25 behaviour-coupled NON-members (the image_service / Tier-3 suites, the orchestrator integration suites, the TestClient compare-route suites, test_shadow_experiments, test_scoring_service, ...) at HEAD: `s07c-adv-doubt-head` 522 passed, 51 deselected, 0 failed: evidence for the GATES Q3 reading.

C7 SPEND AND SECRETS: PASS. The added app / scripts lines read no environment name, credential, file or network (grep of the added lines for environ / getenv / ANTHROPIC / OPENAI / KEY / TOKEN / http / socket / open( / subprocess / load_dotenv / _read_key / MEAS_: no hit). The RED file sets flags and one run-time-built synthetic credential only through monkeypatch. Dry run re-measured in my scratch worktree (`env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u MEAS_ANTHROPIC_TEST_KEY`, `-m scripts.meas_claude_gate text --dry-run` under a process-wide audit-hook socket recorder): rc 0, stdout and stderr 0 bytes, total_calls 622 (= base), total_worst_usd 1.459691 (A0 2 / A1 320 / A2 40 / A3 20 / A4 100 / A5 20 / A6 120 calls), socket events gethostname 1, __new__ 2, bind 1, connect 1 (the loopback socketpair), non-loopback 0, the five credential names absent at start and end. No .env in the scratch worktree or any ancestor.

C8 MUTANTS (my own, in my scratch worktree; .qa-mutation.lock 23:43 to 23:48; byte copy, one exact edit matching once, restore, sha256 MATCH every time: extraction_service 7e508ed4..., llm_router 9c14b241..., meas_claude_gate e6bcbe3d... = the GREEN values):

| id | edit | ran | RED file | other killer |
|---|---|---|---|---|
| MX1 | extraction_service :2639 guard + `and not demographics_profile` (no block for cohort users) | RED | SURVIVED (17 passed) | none: no other test passes score_winner_index |
| MX2 | the guard + `and category == "fragrances"` | RED | SURVIVED (17 passed) | none |
| MX3 | the 429 verdict_fallback call sends `re.sub(<the block>, "", system_msg)` | RED | SURVIVED (17 passed) | none |
| MX4 | meas_claude_gate evaluate_role: the A6 mismatch denominator n_scored -> n | RED + s07 harness | SURVIVED V11 | KILLED by s07 R72[VERDICT] and R72b x5 (AssertionError) |
| MX5 | llm_router route: the schema-failure escalation only at schema sites (`spec.output_schema is not None and`) | RED + s06 + s06 gate rows | SURVIVED | KILLED by s06 R27[length] and R27[non_json] |

The HEAD code is correct on every survivor's path (P1: the block with a cohort profile and for other / smartphones; P5: the verdict_fallback request carries it): the survivors are RED-coverage limits (m2), not defects.

## Findings

Blocking: none. Major: none.

Minor (stated limits by default, LC-4):
- m1 (C4) The Tier-3 extractor does not return None on every failure. image_service :214 `candidate = parsed.get("image_url")` raises AttributeError when the reply is valid JSON but not an object (JSON null, a JSON string, a list, a number: P2). get_product_image_url :322-326 catches it, so the user sees the placeholder exactly as for None, with one WARNING `[image] Tier 3 orchestrator caught: AttributeError(...)` (a type message, no user data; not a Sentry event) and `[IMG_TIER] ... outcome=error:AttributeError` instead of `miss`. Newly reachable on the Claude branch: the base closed schema constrained the reply to an object, option (b) does not (the OpenAI path already had it: Tier 3 sends no response_format). Three committed texts state the false premise of spec T3: the llm_router SITES comment (:206-207 "returns None on any failure"), CLAUDE.md :673 ("None on any failure"), the PR body T section ("returns None on any failure"). Run 2's image_tier3 json_valid counts such replies as valid while production shows the placeholder. Suggested stated-limit wording: "a JSON non-object reply raises AttributeError in extract_image_via_gpt; the image orchestrator catches it and shows the placeholder; run 2's json_valid counts it as valid". A one-line `isinstance(parsed, dict)` guard is outside this unit (T3).
- m2 (C8) RED coverage: MX1, MX2 and MX3 survive the frozen RED file and the whole comm set (no other test passes score_winner_index): the block is pinned only for category fragrances, without a cohort profile, on the primary verdict call. The HEAD code is right on all three paths (P1: 648 combinations incl. the cohort block rendered 324 times and three categories; P5: the 429 fallback). If the gate wants regression pins, a small gate-rows file (V2 with a cohort profile, a non-fragrance category and the verdict_fallback request) kills all three; else a stated limit.
- m3 (C2 / C3) Prompt interplay is byte-pinned but not behaviour-measured: with comparison_quality 'weird' the block ("picked PRODUCT n as the winner ... never present the other product as the winner") sits beside "Do NOT force a winner_declaration"; with ENABLE_GPT_WINNER ON its "Do not re-decide the winner from ... any other field" precedes the "SEPARATELY ... form your own view" block, which can bias the log-only GPT_WINNER_DISAGREES diagnostic toward agreement. Run 2's A6 builder sends normal quality with every prompt flag off, so neither combination is measured.

## Files of this round (sha256 over the bytes on disk)
- notes.md ce9fb91c... (6898 bytes)
- test_zz_adv_probe.py 0bfb2418... (21559 bytes)
- mut_adv.py 034795a0... (5379 bytes)
- dry_guard.py 7bf2c16a... (1767 bytes)
- go.sh 1afc73a0... (620 bytes)
- gen_adv_report.py 4c91948a... (18128 bytes)
- mut_results.jsonl 9056897e... (5128 bytes)
- probe_out/p1.json efbbf839... (278 bytes)
- probe_out/p2.json 54bcb542... (5723 bytes)
- probe_out/p3.json 64592fbc... (367 bytes)
- probe_out/p4.json a912eb9e... (991 bytes)
- probe_out/p5.json cf46b000... (1567 bytes)
- dry_events.json 223a9bf1... (195 bytes)
- dry/text/plan.json db1aab9d... (574 bytes)
- probe1.log 61d54fd6... (5046 bytes)
- probe2.log cc75cf9e... (5065 bytes)
- doubt-head.log d126ddfe... (8753 bytes)
- mut-MX1.log 24136473... (5398 bytes)
- mut-MX2.log 69946967... (5398 bytes)
- mut-MX3.log 7445375e... (5398 bytes)
- mut-MX4.log b4c669db... (15680 bytes)
- mut-MX5.log 10dc7175... (10890 bytes)

## NOT MEASURED
- Live behaviour of either changed request (run 2 of S81-07 is the measurement; no network, no credential here).
- The fourteen client fences and the 365-member comm set at base and HEAD (the GATES round's runs; I re-checked their logs and ran 25 extra non-members at HEAD, not the members).
- The OpenAI model's response to the block (the OpenAI credential is rejected; P3 shows only that the block reaches the OpenAI request).

## git status --short (W) and worktrees
- W `git status --short`: (empty); HEAD 1da03aff3bbb784b5f83656158405260f5874b71; my scratch worktree removed and absent from `git worktree list`.
