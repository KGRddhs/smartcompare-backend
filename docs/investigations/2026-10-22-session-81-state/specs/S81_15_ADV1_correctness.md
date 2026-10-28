# S81-15 REGISTRY-ROBOTS-DENY: adversary report, lens CORRECTNESS (agent Opus 5.5, 2026-10-28; written through the shell, the harness refuses a subagent Write of a report .md)

- Unit S81-15 (ENABLE_MERCHANT_REGISTRY_DB + ENABLE_ROBOTS_REGISTRY_CRON, lane B). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s15, HEAD ce01175fc07335025932a1c3d51f25604073893f verified first and last; git status --short empty first and last; never edited.
- RED files re-hashed first and last in the worktree: test 5bb3bc4c1ccd21abffeece4b221d82289b9a250008c391bf91f3c0e23f52be09, fixture 314d5e0d2b8fd81929e0f2ee15399afb77b73efc5735e60b3dccb0b882e50d84: OK.
- Scratch: git worktree add --detach <scratchpad>/S81-15_adv_correctness ce01175f. A fresh Windows checkout (core.autocrlf=true) turns the 8 new LF files into CRLF, so the W bytes of those 8 files were copied in with shutil.copyfile; then all 17 changed files were sha256-equal to W. Mutation lock created and deleted; every restore sha-verified; after the last mutant 17 of 17 files equal to W. Removed with git worktree remove --force: absent from git worktree list and from disk.
- VERDICT: NOT_READY (1 blocking = ruling-gated CI red; 3 major).

## Runs (bounded runner, .venv-qaren, one pytest at a time)
- Unit files, flags unset: 2 failed (R9, R22) / 236 passed. [pyt] tag=s15adv-c-unit-off start=2026-10-28 23:05:15 end=2026-10-28 23:05:30 elapsed=15s bound=600s status=FAIL rc=1; [hermeticity] sentinel checked 238; [netguard] blocked 0.
- Unit files, both flags ON: 2 failed (R9, R22) / 236 passed. [pyt] tag=s15adv-c-unit-on start=2026-10-28 23:05:35 end=2026-10-28 23:05:49 elapsed=15s bound=600s status=FAIL rc=1; [hermeticity] 238; [netguard] blocked 0.
- E1/E2 + test_domain_s76 + test_s81_kb_schema + test_retro_w0_4: 2 failed (test_s14_p01, test_s14_p02) / 751 passed. [pyt] tag=s15adv-c-pins start=2026-10-28 23:31:19 end=2026-10-28 23:32:28 elapsed=69s bound=600s status=FAIL rc=1; [hermeticity] 753; [netguard] blocked 0.
- 79 mutant runs over 76 distinct mutants (tags s15adv-c-<id>, bound 600, every run status OK or FAIL, no TIMEOUT): 73 with -k killers; the 3 first-pass survivors (G4b, G9a, G8a) re-run and 3 later mutants (G9c, G9d, G7c) run against BOTH full unit files (tags s15adv-c-<id>-all, each 2 failed = R9/R22 only, 236 passed; e.g. [pyt] tag=s15adv-c-G7c-all start=2026-10-28 23:28:48 end=2026-10-28 23:29:02 elapsed=15s bound=600s status=FAIL rc=1). Logs: <scratchpad>/S81-15_adv/mut_<id>.log, results mut_results.json.
- These match the GREEN report numbers (unit 2F/236P both flag states; E1/E2 green; p01/p02 red).

## BLOCKING (ruling-gated; not a GREEN code defect)
B1. CI is red at these bytes on 4 nodes: tests/test_s81_s15_registry_robots.py::test_r9_entry_round_trip and ::test_r22_seed_rows_counts_and_contract (frozen RED rows), tests/test_s81_kb_schema.py::test_s14_p01_no_importer_of_kb_service and ::test_s14_p02_no_kb_relation_literal_outside_the_leaf (branch-only-new; GC-12 requires EMPTY). Verified unsatisfiable by ANY conforming implementation: main kb_service._registry_ok(value, host) takes 2 args (R22 raises TypeError; R9 calls the 1-arg form) and refuses a non-Source key such as the RED row R9 key search (GC-3 requires the real post-fix module); GC-2 makes the seed wrap kb_service.build_merchant_row and the request path must name the table, so p01 and p02 must redden. The GREEN amendments were diffed against the frozen files: RED-A/B change exactly 3 strings (search -> search_descriptor; _registry_ok([e2], s.domain); _registry_ok(r[registry], r[host])); E3/E4 add 2 exemptions. Merge needs the orchestrator to rule RED-A/B and E3/E4 (see m8 on the E3 width).

## MAJOR
M1. The daily robots cron re-reads every host every OTHER day, not once a day. robots_registry.run_cron evaluates due_rows ONCE with the run start clock, while next_row_update stamps each host next_reread = its own fetch time + REREAD_HOURS (24). Under the documented daily schedule (30 2 * * *) every host processed after the first instant of a run has next_reread later than the next run start, so it is not due the next day. Measured with the real run_cron, a fake client honouring the conditional update, 40 live rows, a clock advancing 3 s per call and four daily starts at 02:30: due 40 / 0 / 40 / 0, written 40 / 0 / 40 / 0 (<scratchpad>/S81-15_adv/probe_cadence.out). The CLAUDE.md row (read once a day), the PR body (Daily) and the cron docstring are therefore false in steady state, and the persisted verdict that D14 / S81-16 will consume reaches about 48 h of age (RFC 9309 caps a cached robots.txt at 24 h). No row runs two consecutive runs with an advancing clock (R36 uses a fixed clock). Fix: a due test with slack (for example next_reread <= now + 1 h) or a shorter REREAD_HOURS (for example 20), plus one row that runs run_cron twice 24 h apart and asserts every host is due again.
M2. GC-7 / R-S15-2 deviation for three of the four rows the ruling names. probe_plan treats a sample host that is a PARENT of the row host as same-site (clause: or host.endswith(. + s_host)), so the seeded candidates parfumdeal.salla.sa, rose-store-27.salla.sa and journey1.salla.sa (sample PDPs on https://salla.sa/<store>/...) read https://salla.sa/robots.txt as their PRIMARY record (origin https://salla.sa, probed / and the sample path on salla.sa, no other_origins). Review C14 lists these as different-host rows (four -> salla.sa), RED open question 7 names salla.sa, and GC-7 rules that such a row reads its OWN https://<host>/robots.txt with the sample origin under robots.other_origins (D14: missing -> skip + queue). Only somman.com (the fourth) and bh.redtagfashion.com follow GC-7. Seed census (probe_origins.out): same host 248, subdomain (www etc) 119, cross-site 2, PARENT 3, no sample 38. The clause is unpinned: mutant G7c (drop it, i.e. the ruling reading) SURVIVES both full unit files; gc7 and R34c cover only a cross-site and a www sample. Fix: drop the parent clause (or obtain a ruling that a parent-domain sample is same-site) and add a gate-named row for a *.salla.sa row.
M3. GC-9 SELECTION half is unpinned and the PR body mapping overstates it. Mutants G9a (score_source reads _lookup_registry), G9c (source_usage) and G9d (is_render_only_domain) all SURVIVE both full unit files. Runtime truth at HEAD is correct (probe_runtime.out: sephora.com cron-blocked, flag ON: score_source 0.5 vs 1.0 at base, registry_tier global and match_registry_apex sephora.com kept), but no row asserts it, so a later edit can let robots-blocked hosts keep their registry weight, usage or render routing silently. The PR body maps R-S15-1 / GC-9 to r4, r8b, r11, r11b, r11c, r21, r21b, p7, p8: none of them reads these three functions for a blocked host. Fix: one row (cron-blocked host, flag ON, refreshed): score_source == 0.5, source_usage == price, is_render_only_domain False for a render-only blocked host, while registry_tier / match_registry_apex keep the base answers.

## MINOR (documentation rulings for the orchestrator)
m1. GC-8 wording vs code: --classify eligibility is live AND platform NULL AND blank mechanism (_blank_mechanism). GC-8 reads every LIVE row with platform NULL, literal rows included. Census of the 410 seed rows: 244 live platform-NULL rows, 234 blank-mechanism (classified), 10 with an unmapped mechanism NOT classified (extra.com, bolo.bh, nasserpharmacy.com, sephora.me, boutiqaat.com, noon.com [these 6 literal], goldenscent.com, danube.sa, beautyboothqa.com, nahdionline.com). RED question 8 presupposed blank-mechanism, so the gate may have meant that; rule it (or drop the filter). Not declared as a deviation; gc8 encodes the narrower scope.
m2. GC-4 on the CRON paged read: robots_registry._read_rows carries .order(host) but no row pins it (mutant G4b SURVIVES both unit files); only the request-path read is pinned (gc4 kills G4a).
m3. default_validate returns False for a DNS failure or timeout as well as for an SSRF hit, so a transient resolver failure on the first robots URL is stored as health.ssrf initial, and on a redirect hop blocks a LIVE host with blocked_reason ssrf_redirect (a security label) until the next read. Diagnostic only (fail-closed is right); state it or carry a reason from the validator.
m4. The young residential / operator branch of next_row_update writes only health + updated_at, so robots.next_reread stays at the residential record value: such a row is due on every run and sorts first (oldest next_reread) for up to 30 days (probe_runtime.out: due again one hour later = True). Harmless at 410 hosts and a daily run.
m5. The PDP gate (and classify_host) refuses any redirect hop to another origin (_pdp_may_fetch compares origins), so a sample PDP that redirects http -> https or www <-> apex can never pass the pdp gate: the candidate stays failing_gate pdp. Fail-closed and consistent with one origin per row, but not stated.
m6. Owner step 7 sets ENABLE_MERCHANT_REGISTRY_DB on web only; the price-warmer (an off-clock service that fetches registry sources through source_router) keeps the code registry and keeps fetching cron-blocked and owner-denied hosts. Not a regression vs base; state it or extend the step.
m7. Three GREEN gate rows kill their mutants with a KeyError, not an AssertionError (gc2 on G2a, gc6 on G6b, gc7 on G7b: direct dict indexing). Still a failure; an explicit assert gives the reason.
m8. The proposed E3 exempts the WHOLE file app/services/merchant_registry.py from test_s14_p01, so any later kb_service import there passes silently; a narrower exemption (the one lazy import inside build_seed_rows) keeps the inert-leaf pin meaningful.
m9. Confirmed by probe: the three residential seed records (klinq.com, nazih.qa, numberc.com, all LIVE catalog rows) carry fetched_at 2026-08-31, already 58 days old, so a datacenter 403 on the first cron run blocks them (robots_unreadable). Correctly documented as owner step 3 before step 5 (GREEN deviation 9); the ordering is the only protection.
m10. Docstring nit: merchant_registry says banned hosts in LOOKUP read Source.status blocked; a deny_hosts host stored live (mis-seeded) keeps its stored status with deny True (the seed never stores it that way).

## Mutation table (76 mutants on sha-verified byte copies in the scratch worktree; exact-string edit matched once; killers via -k, survivors re-run on both full unit files)

| id | mutant | result | killed by (first node) |
|---|---|---|---|
| M1 | registry_rows skips the flag read | KILLED | test_p1_flag_off_consumers_identical[off-off-unset] |
| M1d | registry_lookup_rows ungated | KILLED | test_p1_flag_off_consumers_identical[off-off-unset] |
| M1c | partner_for_host ungated | KILLED | test_p1_flag_off_consumers_identical[off-off-unset] |
| M2 | flag reader without strip/lower | KILLED | test_r1_db_flag_reader[TRUE] |
| M3 | memo knob without the clamp | KILLED | test_r2_memo_seconds_knob[60-300.0] |
| M4 | knob accepts nan / inf | KILLED | test_r2_memo_seconds_knob[nan-600.0] |
| M6 | decode ignores deny | KILLED | test_r11_blocked_candidate_and_denied_never_selected |
| M7 | decode drops the is_denied_host belt | KILLED | test_r11_blocked_candidate_and_denied_never_selected |
| M8 | no sort by order | KILLED | test_r14_order_independent_of_row_order |
| M9 | catalog flag ignored at refresh | KILLED | test_r8_record_equality[off] |
| M10 | rebuild on an equal snapshot | KILLED | test_r16_snapshot_keeps_identity_and_sees_unbumped_edits |
| M11 | empty result stored (no fallback) | KILLED | test_r17_failures_fall_back_with_one_warning_per_window[empty] |
| M12 | WARNING on every refresh | KILLED | test_r17_failures_fall_back_with_one_warning_per_window[no_client] |
| M14 | single flight removed | KILLED | test_r6_single_flight_refresh_off_loop_with_status_filter |
| M33 | lookup set drops blocked/denied rows | KILLED | test_r8b_lookup_set_keeps_blocked_and_denied_rows |
| M36b | snapshot lacks the catalog flag | KILLED | test_r12_catalog_flag_read_at_refresh |
| M37 | failed refresh reverts at once | KILLED | test_r17b_failed_refresh_keeps_last_good_list_until_max_stale |
| M37b | last good list kept forever | KILLED | test_r17b_failed_refresh_keeps_last_good_list_until_max_stale |
| M44 | read not off the loop | KILLED | test_r6_single_flight_refresh_off_loop_with_status_filter |
| M45 | no server-side status filter | KILLED | test_r6_single_flight_refresh_off_loop_with_status_filter |
| MDEDUP | literal dedup set built from live literal rows only (R-S15-9) | KILLED | test_r13_literal_dedup_from_every_literal_origin_entry |
| G4a | GC-4 request-path read without .order('host') | KILLED | test_gc4_paged_read_orders_by_host |
| G2a | GC-2 no created_at on INSERT | KILLED (KeyError) | test_gc2_seed_wraps_build_merchant_row_and_created_at_on_insert_only |
| G2b | GC-2 created_at in the update payload | KILLED | test_gc2_seed_wraps_build_merchant_row_and_created_at_on_insert_only |
| M29 | seed writes the banned host live | KILLED | test_r8b_lookup_set_keeps_blocked_and_denied_rows |
| M30 | plan_seed updates status on existing hosts | KILLED | test_r24_plan_seed_idempotent_and_non_clobbering |
| G1 | GC-1 robots_disallow not a cron reason | KILLED | test_r31_transitions |
| M17 | 403 treated as allow | KILLED | test_r27_decide_robots_table[403-headers8--urls8-unreadable-None-off] |
| M18 | only the QarenBot group consulted | KILLED | test_r27_decide_robots_table[200-headers3-User-agent: |
| M19 | 404 treated as unreadable | KILLED | test_r27_decide_robots_table[404-headers6--urls6-allow-None-off] |
| M20 | a challenge page treated as readable | KILLED | test_r27_decide_robots_table[200-headers12-<!DOCTYPE |
| M38 | wall check on plain-text robots | KILLED | test_r27_decide_robots_table[200-headers14-# |
| M39 | server: cloudflare counted as a challenge | KILLED | test_r27_decide_robots_table[520-headers15--urls15-unreadable-None-off] |
| M21 | crawl delay = min of the groups | KILLED | test_r28b_verdict_crawl_delay_is_the_max_of_both_groups |
| M34 | no SSRF check on redirect hops | KILLED | test_r34b_redirects_followed_by_hand_with_ssrf_on_every_hop |
| M35 | allow_redirects not False | KILLED | test_r34_cron_is_sequential_polite_and_named |
| M26 | 2 s floor removed | KILLED | test_r34_cron_is_sequential_polite_and_named |
| M49 | a browser UA | KILLED | test_r34_cron_is_sequential_polite_and_named |
| G6a | GC-6 initial refusal reported ssrf_redirect | KILLED | test_gc6_initial_ssrf_refusal_is_unreadable_and_a_refused_hop_is_ssrf_redirect |
| G6b | GC-6 health.ssrf not recorded | KILLED (KeyError) | test_gc6_initial_ssrf_refusal_is_unreadable_and_a_refused_hop_is_ssrf_redirect |
| G6c | GC-6 every refusal labelled hop | KILLED | test_gc6_initial_ssrf_refusal_is_unreadable_and_a_refused_hop_is_ssrf_redirect |
| G5a | GC-5 a datacenter ALLOW replaces a young residential record | KILLED | test_gc5_datacenter_allow_never_replaces_a_young_residential_record |
| G5b | GC-5 30-day window widened to 60 | KILLED | test_r31b_residential_verdict_is_never_downgraded_by_the_datacenter |
| M40 | young residential verdict downgraded | KILLED | test_r31b_residential_verdict_is_never_downgraded_by_the_datacenter |
| G7a | GC-7 cross-site sample read from the sample origin | KILLED | test_r34c_robots_is_read_from_the_probe_origin |
| G7b | GC-7 other_origins not recorded | KILLED (KeyError) | test_gc7_cross_origin_sample_reads_the_host_rows_own_robots |
| M51 | robots read from the kb host, not the probe origin | KILLED | test_r34c_robots_is_read_from_the_probe_origin |
| M50 | adapter path left out of the probe set | KILLED | test_r32b_adapter_path_joins_the_probe_set |
| M22 | promotion without the ToS gate | KILLED | test_r32_promotion_gates[tos_missing] |
| M41 | PDP gate without a price | KILLED | test_r32_promotion_gates[no_price] |
| G10a | GC-10 title not through the sanitiser | KILLED | test_gc10_pdp_gate_product_name_is_the_sanitised_page_title |
| G10b | GC-10 empty product name to the extractor | KILLED | test_gc10_pdp_gate_product_name_is_the_sanitised_page_title |
| M42 | candidate blocked on a robots failure | KILLED | test_r31_transitions |
| M28 | Option A rejoin always live | KILLED | test_r31_transitions |
| M54 | park days knob ignored | KILLED | test_r31_transitions |
| M47 | cron update not conditional | KILLED | test_r36b_cron_updates_are_conditional_and_a_lost_race_is_skipped |
| M27 | cron touches deny/owner/tos rows | KILLED | test_r35_ssrf_refusal_and_sticky_rows_are_not_fetched |
| M48 | probe order by host only | KILLED | test_r36_run_bound_due_order_parked_and_not_due |
| M53 | rule lists not capped | KILLED | test_r29d_rule_lists_are_capped_at_200 |
| M58 | D14 record drops probed | KILLED | test_r29_robots_record_is_the_frozen_d14_contract |
| G4b | GC-4 cron read without .order('host') | SURVIVED |  |
| M15 | _routable_registry D03-OFF returns SOURCE_REGISTRY | KILLED | test_r7_on_routes_operator_rows_in_both_catalog_states[off-off] |
| M15b | _lookup_registry D03-OFF returns SOURCE_REGISTRY | KILLED | test_r7_on_routes_operator_rows_in_both_catalog_states[off-off] |
| G9a | GC-9 score_source reads LOOKUP | SURVIVED |  |
| G9b | GC-9 _registry_row_for_host reads SELECTION | KILLED | test_r11b_cron_blocked_global_host_keeps_its_refusals |
| M16 | _curl_timeout_for_url reverted to SOURCE_REGISTRY | KILLED | test_r7_on_routes_operator_rows_in_both_catalog_states[off-off] |
| M16b | cache_service._registry_domains reverted | KILLED | test_r21_direct_readers_read_the_lookup_accessor |
| M16c | magento _expected_currency_for reverted | KILLED | test_r21_direct_readers_read_the_lookup_accessor |
| M24 | cron not gated on its flag | KILLED | test_r33_cron_flag_off_does_nothing |
| G8a | GC-8 classify admits non-live rows (client side) | SURVIVED |  |
| G8b | GC-8 classify writes without --apply | KILLED | test_r26_seed_classify_dry_run_and_apply |
| G8c | GC-8 default 20 changed | KILLED | test_gc8_classify_scope_is_live_platform_null_blank_mechanism_rows_including_lit |
| M57 | seed --apply batches above 100 | KILLED | test_r25_seed_script_dry_run_writes_nothing_and_apply_batches |
| G9c | GC-9 source_usage reads LOOKUP | SURVIVED |  |
| G9d | GC-9 is_render_only_domain reads LOOKUP | SURVIVED |  |
| G7c | GC-7 parent-domain sample treated as another origin (the R-S15-2 reading) | SURVIVED |  |

Totals: 70 killed, 6 survived (G4b, G9a, G9c, G9d, G7c real gaps -> m2, M3, M2; G8a equivalent: the server-side .eq(status, live) the fake honours makes the client-side status filter redundant).

## Runtime truth of the claims (GREEN report, CLAUDE.md row, PR body)
- Flag-OFF identity: with a FRESH primed memo holding a different DB list and the flag unset, source_router.registry_rows() and registry_lookup_rows() are SOURCE_REGISTRY by identity and partner_for_host is None (probe_runtime.out); p1 x28 kill M1 / M1c / M1d. TRUE.
- Flag reader: a padded mixed-case value reads truthy; M2 killed. TRUE.
- Decode vs base: an untouched seeded table (catalog off) decodes to SELECTION == SOURCE_REGISTRY minus fragrantica.com, record for record, and LOOKUP == the base domains in order (fragrantica kept, deny True, status blocked). TRUE (the row says minus fragrantica).
- Seed counts: 410 rows = 317 live, 92 candidate, 1 blocked (fragrantica deny), 1 collision, 411 entries, built through the real kb_service.build_merchant_row (probe_seed.out). TRUE.
- D03 interplay: flag ON + ENABLE_DATA_GUARDS_V2 ON -> registry_tier(fragrantica.com) None (denied host), flag ON + D03 OFF -> global as at base. TRUE (R-S15-1).
- GC-5, GC-6, GC-10, GC-1, GC-2, GC-4 (request path): the gate rows kill their mutants (G5a, G5b, G6a, G6b, G6c, G10a, G10b, G1, G2a, G2b, G4a). TRUE.
- GC-7: TRUE for cross-site and www samples, FALSE for the three parent-domain *.salla.sa rows (M2).
- GC-9: runtime TRUE, pin claim FALSE (M3).
- GC-8: matches R-S15-13 + literals, narrower than the GC-8 sentence (m1).
- Read once a day / Daily: FALSE in steady state (M1).
- Error-handler mapping, billing R-A3, contract freeze (PLAN section 0): no route, envelope, refund or response key is touched; merchant_registry never raises into a consumer (every accessor path is wrapped and falls back), the cron and seed are off-clock. Nothing to map; no finding.

## Prove-nothing rows / gates
- Gate 6 (the 48 source_router files with ENABLE_MERCHANT_REGISTRY_DB exported): none of those tests primes the memo or provides a client, so flag ON serves the fallback (SOURCE_REGISTRY); it proves the fallback is identical, not the DB branch.
- The PIN run with ENABLE_MERCHANT_REGISTRY_DB=false / ENABLE_ROBOTS_REGISTRY_CRON=off exported: the p rows set their own spellings through monkeypatch, so the export adds nothing.
- gc8 client-side status filter: equivalent to the server-side eq the fake applies (G8a survives as an equivalent mutant).
- R38 byte check: depends on the checkout line endings (a Windows autocrlf checkout of ce01175f makes the 8 new files CRLF); proves the committed blob only on an LF checkout.
- GREEN identity pins A/B with flags unset: flag-OFF identity of the consumer suites only.

## NOT MEASURED
- Real curl_cffi, DNS, redirects and Supabase / PostgREST paging, ordering and conditional-update return shapes (fakes only, as in the GREEN).
- extract_price_from_html / detect_platform_verdict on a real PDP (recorders only).
- The comm set and the CI-order set (engineering lens); not re-run here.
- Real cron wall time over 410 hosts (2 s floor, up to 60 s Crawl-delay).

## Files written (notes folder <scratchpad>/S81-15_adv/, all through the shell or as scripts)
notes.md, mut_harness.py, mutants.py, mut_results.json, mutants_summary.json, mut_<id>.log, probe_runtime.py + .out, probe_seed.out, probe_origins.out, probe_cadence.out, probe_salla.out, pins_e1e2.log, unit_off.log, unit_on.log, claude_diff*.txt, this report.

## Questions for the orchestrator
1. B1: rule RED-A/B (3 strings in the frozen RED file) and E3/E4 (tests/test_s81_kb_schema.py p01/p02); consider the narrower E3 of m8.
2. M2: is a parent-domain sample (the three *.salla.sa stores whose PDPs live on https://salla.sa/<store>/) same-site (as built, unpinned) or another origin (C14, RED question 7, GC-7)? Either way one gate-named row.
3. m1: GC-8 scope = blank-mechanism live platform-NULL rows (as built and pinned by gc8, which asserts a live platform-NULL woo_store_json row is NOT classified) or every live platform-NULL row (10 more rows)?
4. M1: the fix shape (a due slack in due_rows, or REREAD_HOURS below 24, or next_reread computed from the run start).

## Final state (checked at the end)
- Worktree HEAD ce01175fc07335025932a1c3d51f25604073893f; git status --short lines: 0; RED test sha 5bb3bc4c1ccd21abffeece4b221d82289b9a250008c391bf91f3c0e23f52be09; fixture sha 314d5e0d2b8fd81929e0f2ee15399afb77b73efc5735e60b3dccb0b882e50d84.
- Scratch worktree entries in git worktree list: 0 (removed; directory absent).
