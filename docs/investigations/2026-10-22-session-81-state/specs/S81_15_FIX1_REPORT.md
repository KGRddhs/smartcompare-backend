# S81-15 REGISTRY-ROBOTS-DENY: fix round 1 report (fix agent: Opus 5.5, 2026-10-29; written through the shell, the harness refuses a subagent Write of a report .md)

- Unit S81-15 (ENABLE_MERCHANT_REGISTRY_DB + ENABLE_ROBOTS_REGISTRY_CRON, lane B). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s15, branch feature/s81-s15-registry-robots-deny.
- Start: HEAD ce01175fc07335025932a1c3d51f25604073893f verified, git status --short empty; RED test 5bb3bc4c..., fixture 314d5e0d..., gate rows d77f554c... re-hashed OK; byte copies of the 14 files to edit in <scratchpad>/S81-15_fix1_before/ (SHA256SUMS.json).
- End: ONE commit ad1e260c838b4cc904058d6c0d1ec9787c00ab7b on the branch (hook passed; trailer Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>; no push, no rebase, no stash); git status --short empty; .qa-mutation.lock absent; scratch worktree base86 removed (absent from git worktree list and from disk).
- Base for the comm set: GREEN's fresh record at 86d5a24d (<scratchpad>/S81-15_green/comm_base_failed_all_86d5a24d.txt).
- Notes: <scratchpad>/S81-15_fix1/notes.md; patch scripts p1..p6 + fixlib.py; mutation harness mut_harness.py + mut_results_all.json + mut_<id>.log; comm/ (derive_comm_fix1.py, comm_files_head.txt (342), comm_chunks_head.json, head_NN.log, head_NN_failed.txt, comm_head_failed_all.txt, comm_branch_only_new.txt (empty)).

## RED files (sha256, disk = committed blob)
- tests/test_s81_s15_registry_robots.py: 5bb3bc4c1ccd21abffeece4b221d82289b9a250008c391bf91f3c0e23f52be09 -> 66ac62995ab5738510216f228112d8437ed51d1c0901acd49d993cb7ad11b9e1 (E6 = F1-1 3 strings, E7 = F1-7 R38, E8 = F1-9 R41; nothing else)
- tests/fixtures/s81_s15_robots_record.json: 314d5e0d2b8fd81929e0f2ee15399afb77b73efc5735e60b3dccb0b882e50d84 (unchanged)
- tests/test_s81_s15_gate_rows.py (GREEN-owned): d77f554cac5882790b9fd5e3b328893ee9d248637dcef19f5e96cfde96b50b88 -> 03f761ccd451552e5b6b0c5510b02f9f3638b2b4012fbedf1afa9da062fe960e

## Files changed in ad1e260c (git numstat +/-; sha256 on disk; CRLF files: blob sha differs by the eol only)
- app/services/robots_registry.py +186 -42 9622690c5ed5116ff8f305691bd44bdd74c0a7f902d8c687b6279b8b4744f835 (LF)
- app/services/merchant_registry.py +22 -10 f0daf106ef65b26b5e7ef8945e1c4dde60568b1940f26434b050a8e1cd86264c (LF)
- app/services/robots_eval.py +5 -0 de9de5faf4503ee454b5c49237dab85e6c12888037171088986b0fdb48ff28e3 (CRLF; blob bb584acb...)
- app/services/sitemap_discovery_service.py +3 -8 9ec91392e7bd5660e29084f2bf57e2c70a408d4e87889e9ff8c70bc83ee7de99 (CRLF; blob dd724261...)
- railway.robots.json +2 -0 e882e469390b384d1906e5464a7fc562baee268c89fc617973fdf4d7a48b185a (LF)
- scripts/cron_robots_registry.py +12 -7 f05a6d52aff9818539cfda71c818e890a10a4d095e12809b5c12a5741cc2607b (LF)
- scripts/seed_kb_merchants.py +25 -19 818a84c1af8a6c64b8a29116acd760ccbe8de8255a5f6ab48bd8bb90fd501b2d (LF)
- tests/test_s81_s15_gate_rows.py +440 -14 03f761ccd451552e5b6b0c5510b02f9f3638b2b4012fbedf1afa9da062fe960e (LF)
- tests/test_s81_s15_registry_robots.py +8 -6 66ac62995ab5738510216f228112d8437ed51d1c0901acd49d993cb7ad11b9e1 (LF)
- tests/test_s81_kb_schema.py +37 -5 7056eea758d7a0a3c7bced87bad14b8f0a5b0cdf5007381d87b6247ec5bd1c15 (CRLF; blob a28d5d7b...)
- tests/test_domain_s76.py +8 -2 c80e32ed36d27cfaf165243e2a6a5731132aa085d320106132bf92792712fa67 (CRLF; blob 209d5ae8...)
- CLAUDE.md +5 -5 32bfcf2afa295dc78ec434c6106962e73b15c1dac85ba0ccd954afc8e9d961fe (CRLF, non-ASCII count 3937 unchanged; blob 811ffb3e...)
Every write byte-checked: new / LF files 0 bytes > 127; CRLF files keep CRLF, no bare LF, non-ASCII counts unchanged; the only added line with bytes > 127 is the re-added CLAUDE.md Feature Flags line (66, same as its removed twin). Added-line sweep (@gmail, +973, 8-digit runs, sk-/AKIA/xox/JWT/credentialed URL/PEM): 0 hits.

## RED step
- (a) E6 proof at base: detached scratch worktree <scratchpad>/S81-15_fix1/base86 at 86d5a24d with the amended RED file + fixture copied in: r9, r22, r38, r41 fail, all four AssertionError (the merchant_registry / robots_registry / railway.robots.json absence asserts): [pyt] tag=s15f1-red-r9r22-base start=2026-10-29 00:46:31 end=2026-10-29 00:46:35 elapsed=4s bound=600s status=FAIL rc=1; [hermeticity] sentinel checked 4; [netguard] blocked 0. Worktree removed with git worktree remove --force; verified gone.
- (b) New rows appended to the G file (26 new nodes in 17 functions) + gc2/gc6/gc7 .get() (F1-19) + gc5 (F1-14 consequence) + gc8 widened and renamed (F1-15) + E3/E4 + E5 + E8; run on the PRE-FIX code bytes (code = GREEN ce01175f): 24 failed / 776 passed, 24 location lines all AssertionError: [pyt] tag=s15f1-red-prefix start=2026-10-29 00:54:40 end=2026-10-29 00:55:03 elapsed=22s bound=600s status=FAIL rc=1; [hermeticity] sentinel checked 800; [netguard] blocked 0.
  - RED (fail pre-fix): test_f1_3_a_daily_cron_rereads_every_host_every_day, test_f1_3b_due_slack_knob[x9], test_f1_4_a_parent_host_sample_is_another_origin, test_f1_6a_default_fetch_is_named_unredirected_and_byte_capped, test_f1_6b_default_validate_refuses_internal_targets_and_accepts_a_public_address, test_f1_10a_residential_read_refuses_a_deny_hosts_host_before_any_fetch, test_f1_10b_classify_refuses_a_deny_hosts_host_before_any_fetch, test_f1_12_refresh_task_is_created_outside_the_lock_in_a_fresh_context, test_f1_13a_a_resolver_failure_is_unreadable_with_health_dns, test_f1_14_young_residential_row_is_due_when_the_protection_lapses, test_f1_23_integer_knobs_clamp_a_fraction_to_one[x2] = 20 new nodes; amended existing rows red pre-fix by design: gc5, gc8 (renamed test_gc8_classify_scope_is_every_live_platform_null_row_including_literals), r41 (E8), test_s14_p01 (E3: the merchant_registry module docstring still named kb_service beside a '/').
  - PIN-type new rows (green pre-fix; the behaviour was already right at GREEN; each is proven by its mutant below): test_f1_5a_score_source_reads_selection_for_a_cron_blocked_host, test_f1_5b_source_usage_reads_selection_for_a_cron_blocked_host, test_f1_5c_is_render_only_domain_reads_selection_for_a_cron_blocked_host, test_f1_6c_cron_entry_wires_the_production_seams, test_f1_13b_a_metadata_address_is_an_initial_ssrf_refusal, test_f1_16_cron_paged_read_orders_by_host.
  - Existing rows green pre-fix: r9 / r22 (E6), r38 (E7), test_s14_p02 (E4), test_t4 (E5) and every other existing row.
- After the GREEN hunks (before the commit): 800 passed: [pyt] tag=s15f1-green1 start=2026-10-29 00:59:27 end=2026-10-29 00:59:58 elapsed=31s bound=600s status=OK rc=0; [hermeticity] 800; [netguard] 0.

## Gates at the committed HEAD ad1e260c (F1-25)
- Both unit files, flags unset: 264 passed: [pyt] tag=s15f1-unit-off start=2026-10-29 01:03:12 end=2026-10-29 01:03:26 elapsed=15s bound=600s status=OK rc=0; [hermeticity] 264; [netguard] blocked 0.
- Both unit files, ENABLE_MERCHANT_REGISTRY_DB=true ENABLE_ROBOTS_REGISTRY_CRON=true exported: 264 passed: [pyt] tag=s15f1-unit-on start=2026-10-29 01:03:27 end=2026-10-29 01:03:41 elapsed=14s bound=600s status=OK rc=0; [hermeticity] 264; [netguard] blocked 0.
- PIN rows (-k test_p) with ENABLE_MERCHANT_REGISTRY_DB=false ENABLE_ROBOTS_REGISTRY_CRON=off exported: 37 passed: [pyt] tag=s15f1-pins-falsy start=2026-10-29 01:03:49 end=2026-10-29 01:03:55 elapsed=6s bound=600s status=OK rc=0.
- Pin set A (21 files incl. test_domain_s76): 932 passed, 3 skipped, 1 deselected: [pyt] tag=s15f1-pinsA start=2026-10-29 01:04:04 end=2026-10-29 01:04:19 elapsed=16s bound=1200s status=OK rc=0; [hermeticity] 932; [netguard] 0.
- Pin set B (8 spec pins + test_s81_kb_schema + test_retro_w0_4 + test_retro_w0_4_efg): 1111 passed: [pyt] tag=s15f1-pinsB start=2026-10-29 01:04:26 end=2026-10-29 01:06:25 elapsed=119s bound=1200s status=OK rc=0; [hermeticity] 1111; [netguard] blocked 22 attempt(s) from 21 node(s) (test_hermeticity_pins designed rows).
- CI-order (GREEN's 31 + test_s81_kb_schema + test_retro_w0_4 + test_retro_w0_4_efg = 34 files, alphabetical, -rfE): 2307 passed, 3 skipped, 1 deselected: [pyt] tag=s15f1-ci-order start=2026-10-29 01:13:13 end=2026-10-29 01:15:39 elapsed=145s bound=1200s status=OK rc=0; [hermeticity] 2307; [netguard] blocked 22 from 21 (designed). (The Bash wrapper backgrounded this one run after 120 s; it was the only pytest running and nothing else started until it exited.)
- R38 on a CRLF working copy of the four new .py files (lock, byte copies, restored, sha-verified, git status empty after): 1 passed: [pyt] tag=s15f1-r38-crlf start=2026-10-29 01:28:46 end=2026-10-29 01:28:50 elapsed=5s bound=600s status=OK rc=0. (LF copy: the unit runs above.)
- ruff 0.16.5 --select E9,F63,F7,F82 --no-cache on the 10 touched python files: All checks passed; full repo ruff config on robots_registry / merchant_registry / both scripts / the G file: All checks passed; py_compile OK; railway.robots.json json.load OK; the pre-commit hook passed on the commit.

## Comm set (F1-28)
- 342 files = GREEN's 340 (comm_files_head.txt) UNION a re-derivation at ad1e260c (GREEN's derive_comm.py widened: edited tests test_domain_s76 / test_s81_kb_schema / the unit files as import targets; symbols + rules_for_agent, _rules_for_agent, entry_refusal, due_slack_seconds, default_validate, default_fetch, MAX_BODY_BYTES, DENY_REFUSAL, ROBOTS_DUE_SLACK_SECONDS, validate_external_url_async, _schedule_refresh, deny_hosts): + tests/test_retro_w0_1.py and tests/test_url_validator_offloop.py (symbol class; both green at HEAD, so no base record needed). Minus test_precommit_hook*. 14 chunks (13 x 25 + 17), bound 1200.
- [pyt] tag=s15f1-head-00 start=2026-10-29 01:15:54 end=2026-10-29 01:16:29 elapsed=36s bound=1200s status=OK rc=0 (797 passed; hermeticity 797; netguard 22 from 5)
- [pyt] tag=s15f1-head-01 start=2026-10-29 01:16:30 end=2026-10-29 01:17:23 elapsed=54s bound=1200s status=OK rc=0 (1046 passed; hermeticity 1047; netguard 17 from 4)
- [pyt] tag=s15f1-head-02 start=2026-10-29 01:17:23 end=2026-10-29 01:17:39 elapsed=16s bound=1200s status=OK rc=0 (1146 passed; hermeticity 1147; netguard 1 from 1)
- [pyt] tag=s15f1-head-03 start=2026-10-29 01:17:40 end=2026-10-29 01:18:11 elapsed=31s bound=1200s status=OK rc=0 (1103 passed; hermeticity 1103; netguard 44 from 14)
- [pyt] tag=s15f1-head-04 start=2026-10-29 01:18:11 end=2026-10-29 01:19:20 elapsed=69s bound=1200s status=OK rc=0 (1552 passed; hermeticity 1554; netguard 28 from 23)
- [pyt] tag=s15f1-head-05 start=2026-10-29 01:19:27 end=2026-10-29 01:19:50 elapsed=23s bound=1200s status=OK rc=0 (344 passed; hermeticity 344; netguard 0)
- [pyt] tag=s15f1-head-06 start=2026-10-29 01:19:50 end=2026-10-29 01:20:14 elapsed=24s bound=1200s status=OK rc=0 (3639 passed; hermeticity 3641; netguard 0)
- [pyt] tag=s15f1-head-07 start=2026-10-29 01:20:15 end=2026-10-29 01:20:32 elapsed=17s bound=1200s status=OK rc=0 (1028 passed; hermeticity 1028; netguard 128 from 7)
- [pyt] tag=s15f1-head-08 start=2026-10-29 01:20:32 end=2026-10-29 01:21:25 elapsed=53s bound=1200s status=FAIL rc=1 (470 passed, 2 errors = the cold-tiktoken pair; hermeticity 473; netguard 7 from 2)
- [pyt] tag=s15f1-head-09 start=2026-10-29 01:21:25 end=2026-10-29 01:24:36 elapsed=192s bound=1200s status=OK rc=0 (2956 passed; hermeticity 2956; netguard 0)
- [pyt] tag=s15f1-head-10 start=2026-10-29 01:24:42 end=2026-10-29 01:26:13 elapsed=91s bound=1200s status=FAIL rc=1 (1 failed = the u8d pin, 2068 passed; hermeticity 2069; netguard 37 from 9)
- [pyt] tag=s15f1-head-11 start=2026-10-29 01:26:13 end=2026-10-29 01:26:33 elapsed=20s bound=1200s status=OK rc=0 (830 passed; hermeticity 837; netguard 1 from 1)
- [pyt] tag=s15f1-head-12 start=2026-10-29 01:26:33 end=2026-10-29 01:27:24 elapsed=51s bound=1200s status=OK rc=0 (588 passed; hermeticity 588; netguard 96 from 25)
- [pyt] tag=s15f1-head-13 start=2026-10-29 01:27:24 end=2026-10-29 01:27:51 elapsed=27s bound=1200s status=OK rc=0 (970 passed; hermeticity 980; netguard 8 from 8)
- HEAD failed set (3): ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence; ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable; FAILED tests/test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged. Identical in GREEN's base record (the known environmental base nodes). comm -13 base HEAD = EMPTY (branch-only-new empty; p01 / p02 now green by E3 / E4; R9 / R22 green by E6). Netguard total 389 = GREEN's HEAD total (chunk boundaries shifted by the 2 added files).

## Mutation table (19/19 KILLED, AssertionError only; mut_harness.py; lock created and deleted; each restore sha256-equal to the committed bytes)
| id | file | mutant | killed by |
|---|---|---|---|
| G7c | robots_registry | parent-host sample same-site again | test_f1_4_a_parent_host_sample_is_another_origin |
| G9a | source_router | score_source reads _lookup_registry | test_f1_5a |
| G9c | source_router | source_usage reads _lookup_registry | test_f1_5b |
| G9d | source_router | is_render_only_domain reads _lookup_registry | test_f1_5c |
| G4b | robots_registry | _read_rows without .order(host) | test_f1_16 |
| EM1 | robots_registry | default_validate -> OK past the name check | test_f1_6b, test_f1_13a, test_f1_13b |
| EM2 | robots_registry | allow_redirects=True | test_f1_6a |
| EM3 | cron script | a no-op validator wired by main | test_f1_6c |
| EM6 | robots_registry | the byte cap removed | test_f1_6a |
| SLACK | robots_registry | run_cron passes slack 0 | test_f1_3_a (40/0/40) |
| DENY_PROBE | robots_registry | probe_host deny check removed | test_f1_10a |
| DENY_CLASSIFY | robots_registry | classify_host deny check removed | test_f1_10b |
| DNS_AS_SSRF | robots_registry | resolver failure -> SSRF | test_f1_13a |
| SSRF_AS_DNS | robots_registry | every refusal -> DNS | test_f1_6b, test_f1_13b |
| NEXT_REREAD | robots_registry | young branch without the robots next_reread | test_gc5, test_f1_14 |
| KNOB | robots_registry | _int_knob 0<v<1 -> default | test_f1_23 x2 |
| TASK_CTX | merchant_registry | loop.create_task(coro) (inherits the context) | test_f1_12 |
| TASK_LOCK | merchant_registry | the coroutine created under _LOCK | test_f1_12 |
| CLASSIFY_SCOPE | seed script | --classify back to blank-mechanism rows | test_gc8 |
[pyt] lines: tag=s15f1-mut-<id>, 2026-10-29 01:07:38 .. 01:12:52, elapsed 15-21 s each, bound=600s, status=FAIL rc=1 (e.g. [pyt] tag=s15f1-mut-G7c start=2026-10-29 01:07:38 end=2026-10-29 01:07:55 elapsed=17s bound=600s status=FAIL rc=1; [pyt] tag=s15f1-mut-CLASSIFY_SCOPE start=2026-10-29 01:12:37 end=2026-10-29 01:12:52 elapsed=16s bound=600s status=FAIL rc=1); all 19 lines in mut_results_all.json.

## Ruling coverage (F1-1 .. F1-29)
- Code: F1-3 (due_slack_seconds + due_rows(slack) + run_cron reads it once), F1-4 (probe_plan drops the parent clause), F1-8 (mirror literal deleted), F1-9 (railway.robots.json + cron docstring), F1-10 (entry_refusal, DENY_REFUSAL; probe_host / classify_host refuse first; seed prints refusals), F1-11 (MAX_BODY_BYTES, _decode_body), F1-12 (_schedule_refresh), F1-13 (VALIDATE_OK / SSRF / DNS, _validation_reason, _refusal_reason, _all_public, RobotsVerdict.dns, health.dns), F1-14 (young branch next_reread = fetched_at + 30 d), F1-15 (seed --classify scope; _blank_mechanism deleted), F1-21 (docstring), F1-22 (robots_eval.rules_for_agent, used by _rules_of), F1-23 (_int_knob <= 0).
- Tests: F1-1 (E6), F1-2 (E3 / E4), F1-5, F1-6, F1-7 (E7), F1-8 (E5), F1-9 (E8), F1-16, F1-19 rows; gc5 follows F1-14; gc8 per F1-15.
- Docs (CLAUDE.md S81-15 block + the Environment Variables flag sentence; PR_BODY.md): F1-3 (true daily cadence, the knob), F1-4 (census), F1-9 / F1-13 / F1-17 limits, F1-10 (deny belt at every entry point), F1-12, F1-14, F1-15, F1-18 (owner step 7 on web AND price-warmer), F1-20 (owner step 3 before step 5; 2026-08-31 dates; OWNER_ACTIONS item 30 named; the OWNER_ACTIONS file itself is the orchestrator's), F1-24 (stated), F1-26 (stated), F1-27 (D14 additive keys documented). F1-25 (gates on the committed bytes), F1-28 (comm set) done; F1-29 is the later rebase step (not done).

## Deviations (each with the reason it beats the alternative)
1. R41 amended (E8) in the RED file: the task text names only F1-1 / F1-7 as RED-file edits, but RULINGS_FIX1_S81_15 F1-9 (binding, "amends everything above") sanctions the R41 amendment as E8 and the GREEN step lists it; applied in the RED step so it is proven red pre-fix and green after.
2. other_origins for the parent-host rows carries the ORIGIN form ["https://salla.sa"] (the ruling text writes ["salla.sa"]): every other_origins value in the frozen r34c and in gc7 is an origin with its scheme; a bare host here would split the D14 contract in two shapes.
3. F1-12 uses contextvars.Context().run(loop.create_task, coro) instead of loop.create_task(coro, context=contextvars.Context()): the same effect (the task copies the empty context it is created in) without depending on the loop accepting the context= keyword (uvloop 0.22.1 runs on Railway and cannot be measured on this Windows box); killed by TASK_CTX.
4. E3 needed one more hunk: the narrowed p01 also flags merchant_registry's MODULE docstring (it named kb_service beside a '/'); the docstring now says "the S81-14 KB leaf" instead of adding a second allow-list entry (F1-2 allows exactly one).
5. Six new rows are PIN-type, not RED (f1_5a/b/c, f1_6c, f1_13b, f1_16): they pin behaviour already right at GREEN (the adversaries' runtime truth); "every NEW row fails at the pre-fix bytes" cannot hold for them; each is proven by its mutant (G9a/G9c/G9d, EM3, SSRF_AS_DNS, G4b).
6. F1-13: default_validate still calls url_validator first and pays ONE extra resolve (5 s bound, DNS_CLASSIFY_TIMEOUT_SECONDS, a constant, no knob) only after a refusal; a re-resolve that yields only public addresses (the validator's 2 s timeout or a transient error) is labelled DNS, else SSRF; a non-http(s) scheme is refused up front as SSRF. The injected test seams keep answering with a bool (truthy = fetch).
7. F1-10: classify_host returns None (not a reason string) for a refused host, because --classify would write any string as a platform label; the refusal is recorded by the INFO line `[ROBOTS_REGISTRY] refused host=<host> reason=deny_hosts` and the seed's `classify refused=N` line; probe_host returns {"refused": "deny_hosts", "verdict": None, ...} and `--hosts` prints `<source> host=<h> refused=deny_hosts (never fetched)`. run_cron gained an unreachable-in-practice `if verdict is None: continue` (due_rows already skips deny_hosts rows).
8. gc5 amended (its robots-unchanged and key-set assertions follow F1-14) and gc8 renamed (the old name said blank-mechanism).
9. CI-order also carries test_retro_w0_4_efg.py (the W0-4 guard pair); the comm set carries 2 more files than GREEN's list.
10. PR_BODY.md writes the attribution robot as the HTML entity &#x1F916; so the file stays pure ASCII.
11. No .gitattributes change (F1-7 says none).

## Open questions for the gate
1. Confirm the origin form for robots.other_origins (["https://salla.sa"]) vs the ruling's ["salla.sa"].
2. Confirm the PIN-type classification of the six rows in deviation 5.
3. Confirm Context().run(...) as the F1-12 form (or require the literal context= keyword).
4. entry_refusal follows the ruling (is_denied_host only): an owner-blocked row (deny=true, host not in deny_hosts) typed into --source residential --hosts is still read once (the write is refused by next_row_update). Extend the belt to the deny column?
5. A robots.txt redirect hop TO a deny_hosts host is not refused by name (stated limit); add a per-hop deny check in a later unit?

## NOT MEASURED
- Real curl_cffi / DNS / redirects / PostgREST (paging, order, conditional-update return shape): fakes and patched seams only.
- uvloop task creation with the fresh context (no uvloop on Windows).
- The four tests/test_precommit_hook*.py files (no .githooks input changed; CI is the arbiter); gate 6 not re-run this round (F1-26: it proves the fallback only).
- extract_price_from_html / platform detection on a real PDP; real cron wall time over 410 hosts; Protego parity.

## git status --short (worktree, at the end)
(empty)
