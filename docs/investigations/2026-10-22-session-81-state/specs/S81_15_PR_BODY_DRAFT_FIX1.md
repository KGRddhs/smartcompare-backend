# S81-15 REGISTRY-ROBOTS-DENY: kb_merchants registry memo + daily robots cron (two dark flags)

Branch `feature/s81-s15-registry-robots-deny`: GREEN `ce01175f` + fix round 1 `ad1e260c` (RULINGS_FIX1_S81_15), base `86d5a24d` (main with S81-14 #373; the rebase onto `a8f01379` (S81-06 #374) is the next step, F1-29). Both flags default OFF, read per call, new names (unset in production by construction). Every gate below ran on the COMMITTED bytes of `ad1e260c` (F1-25).

## What the flags do

- `ENABLE_MERCHANT_REGISTRY_DB` (+ `MERCHANT_REGISTRY_MEMO_SECONDS` 600 [300..900], `MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS` 5 [1..30], `MERCHANT_REGISTRY_MAX_STALE_SECONDS` 3600 [900..21600]): the router's registry comes from `kb_merchants` through a per-process memo (`app/services/merchant_registry.py`). One paged read (`status in (live, blocked)`, `.order('host')`, 500-row pages) in a background task via `asyncio.to_thread` under `wait_for`; callers never await it; the task is created OUTSIDE the memo lock in a FRESH `contextvars` context (F1-12), so its log lines never carry a request's context. Two sets (R-S15-1): SELECTION (`source_router.registry_rows`, read only by `_routable_registry`: the selectors, `score_source`, `source_usage`, `is_render_only_domain`) = live, not-denied rows; LOOKUP (`registry_lookup_rows`, read by `_registry_row_for_host` and the three direct readers) keeps blocked and denied rows, so a cron-blocked host keeps its tier, currency and global-tier refusals. sha256 snapshot over the decode columns + the catalog flag. Failures never raise: code registry until a good load, then the last good list up to max stale; one WARNING per window by reason. Flag OFF: `SOURCE_REGISTRY` by identity, no read, no task, no log.
- `ENABLE_ROBOTS_REGISTRY_CRON` (+ `ROBOTS_CRON_MAX_HOSTS` 500 [1..5000], `ROBOTS_CHALLENGE_PARK_DAYS` 7 [1..30] (a fraction 0 < v < 1 clamps to 1, F1-23), `ROBOTS_DUE_SLACK_SECONDS` 3600 [0..21600], read once per run (F1-3)): `app/services/robots_registry.py` + `scripts/cron_robots_registry.py` (a new Railway cron service, `railway.robots.json`). Daily: a host is due when its stored `robots.next_reread` (read time + 24 h, the RFC 9309 cache bound) is at or before the run start + the slack, so each daily run re-reads every host the previous daily run read (measured 40 / 40 / 40 over three runs 24 h apart; 40 / 0 / 40 / 0 at GREEN). Sequential, polite (max(Crawl-delay <= 60, 2 s)), QarenBot UA (`robots_eval.QARENBOT_UA`), no impersonation, redirects by hand (`allow_redirects=False`) with the SSRF check on every hop; robots read from the probe origin (the sample PDP origin only when it is the row host or a subdomain of it; a cross-site or PARENT-host sample, the three `*.salla.sa` stores, is listed under `robots.other_origins`, F1-4); every body capped at 3,000,000 BYTES before decoding (F1-11); `default_validate` answers with a reason: a refused name or address is SSRF (`health.ssrf` initial / `ssrf_redirect` on a hop), a resolver failure is `robots_unreadable` with `health.dns = unresolved`, never an SSRF label (F1-13); fail-closed `decide_robots`; the D14 record (rules + probed, frozen by the fixture; additive `rules_truncated` / `other_origins` only when relevant, F1-27); transitions (live -> blocked robots_disallow / robots_unreadable / challenge / ssrf_redirect, Option A rejoin, candidates never blocked, promotion gates robots -> tos -> pdp -> platform); Option C residential rider (a residential / operator record < 30 days is never replaced; its `next_reread` moves to the lapse day, F1-14); conditional updates on `updated_at`; every deny_hosts host refused by name before any request at every entry point (the cron run, the seed's `--hosts` read, `--classify`; F1-10). Flag OFF: one INFO, no read, no fetch. The live path is untouched (D14 owns live lookups).
- Off-clock seed `scripts/seed_kb_merchants.py` (dry run default; `--apply`, `--classify [N]` over EVERY live platform-NULL row (F1-15), `--source residential --hosts`): 410 rows (317 live / 92 candidate / 1 blocked deny), 411 entries, each from `kb_service.build_merchant_row` + `created_at` on INSERT only.

## Fix round 1 (RULINGS_FIX1_S81_15, commit ad1e260c)

- F1-1 / F1-7 / F1-9: the sanctioned RED-file edits E6 (R9 / R22 vs the merged kb_service), E7 (R38 eol-agnostic), E8 (R41 watch list). F1-2: E3 / E4 narrow the S81-14 p01 / p02 exemptions to one line each (the merchant_registry module docstring now says "the S81-14 KB leaf", so p01's string clause needs no second exemption). F1-8: the dead UA mirror literal deleted, E5 re-pins test_t4.
- F1-3: `ROBOTS_DUE_SLACK_SECONDS` (default 3600, read once per run) in the due test; the stored `next_reread` stays read time + 24 h. F1-4: a parent-host sample is another origin. F1-10: `robots_registry.entry_refusal` + `DENY_REFUSAL`; probe_host returns `{"refused": "deny_hosts", "verdict": None}` and classify_host returns None before any request, each with one `[ROBOTS_REGISTRY] refused host=<host> reason=deny_hosts` INFO; the seed prints the refusal for `--hosts` and a `classify refused=N` line. F1-11: `MAX_BODY_BYTES` cap on `resp.content` before decoding (the response charset, else utf-8, errors replaced). F1-12: the memo task created outside `_LOCK` in a fresh context. F1-13: `default_validate` returns `VALIDATE_OK` / `VALIDATE_SSRF` / `VALIDATE_DNS` (the injected bool seams still work: truthy = fetch); `RobotsVerdict.dns` + `health.dns`. F1-14: the young residential branch writes `robots.next_reread` = its fetched_at + 30 d. F1-15: `--classify` drops the blank-mechanism filter. F1-21: the merchant_registry docstring corrected. F1-22: `robots_eval.rules_for_agent` alias, used by the registry. F1-23: `_int_knob` clamps 0 < v < 1 to 1.
- F1-5 / F1-6 / F1-16 / F1-19: gate rows only (the code was already right; the rows kill G9a / G9c / G9d, EM1-EM3, EM6, G4b). Docs: the S81-15 CLAUDE.md block (cadence + knob, deny belt, D14 additive keys, limits, owner steps 3 / 5 / 7) and the Environment Variables flag sentence.

## Rulings -> test nodes (R = tests/test_s81_s15_registry_robots.py, G = tests/test_s81_s15_gate_rows.py)

| id | what | nodes |
|---|---|---|
| R-S15-1 / GC-9 | SELECTION vs LOOKUP; blocked rows keep tier + refusals; score_source / source_usage / is_render_only_domain read SELECTION (F1-5) | R r4, r8b, r11, r11b, r11c[x2], r21, r21b, p7, p8; G f1_5a, f1_5b, f1_5c |
| R-S15-2 / GC-6 / GC-7 | redirects by hand, SSRF per hop, probe origin, other_origins, parent host (F1-4), production seams (F1-6) | R r34b, r34c, r35; G gc6, gc7, f1_4, f1_6a, f1_6b, f1_6c |
| F1-13 | resolver failure vs SSRF refusal | G f1_13a, f1_13b, f1_6b |
| F1-11 | byte cap before decoding | G f1_6a |
| F1-3 | daily cadence + slack knob | G f1_3, f1_3b[x9] |
| F1-10 | deny belt at every entry point | G f1_10a, f1_10b |
| F1-12 | memo task outside the lock, fresh context | G f1_12 |
| F1-14 / R-S15-4 / GC-5 | Option C rider; young record due at lapse | R r31b, r22; G gc5, f1_14 |
| F1-16 / GC-4 | paged reads ordered by host (request path + cron) | R r6, r6b; G gc4, f1_16 |
| F1-23 | integer knob clamp | G f1_23[x2] |
| R-S15-3 | the D14 record contract | R r29, r29b, r29c[x3], r29d, r32b |
| R-S15-5 / R-S15-6 | D9 emitter pin (E1), UA in robots_eval (E2, E5) | R r39, r40, p9; tests/test_domain_s76.py::test_t4 |
| R-S15-7 / R-S15-8 | memo, B1 PINs | R r2, r2b, r5, r6, r15, r16, r17[x6], r17b, r19, r20, r20b, p1[x28], p2, p3 |
| R-S15-9 / R-S15-10 | origins + catalog state, status filter + paging | R r7[x4], r8[x2], r12, r13, r14 |
| R-S15-11 / GC-1..3 | ownership, conditional writes, seed wraps the builder | R r9, r22, r23, r24, r25, r36b; G gc1, gc2, gc3 |
| R-S15-12 | challenge = body signature or cf-mitigated only | R r27[x36], r30[x9] |
| R-S15-13 / GC-8 / F1-15 | --classify scope = every live platform-NULL row | R r26, r26b; G gc8 |
| R-S15-14 / F1-9 | railway.robots.json + the watch list | R r41 |
| R-S15-15 / 17 / 18 / GC-10 | politeness, order, candidates, PDP price gate | R r31, r32[x7], r34, r36; G gc10 |
| hygiene | light import, no impersonation, log hygiene (eol-agnostic, F1-7) | R r37, r38, r43, p4, p5, p6 |

## Deliberate pin changes

| # | file::node | change |
|---|---|---|
| E1 | tests/test_legal_disclosure_s77.py::test_s77_d9_bot_page_claim_matches_the_runtime | QARENBOT_FILES += app/services/robots_registry.py (GREEN) |
| E2 | tests/test_legal_s78.py (UA_FILES) | sitemap _ROBOTS_UA -> (app/services/robots_eval.py, QARENBOT_UA) (GREEN) |
| E3 | tests/test_s81_kb_schema.py::test_s14_p01_no_importer_of_kb_service | allows ONLY the function-local `from app.services import kb_service as _kb` inside merchant_registry.build_seed_rows (keyed by file + exact line text + the enclosing function; a module-top import still fails); docstring names S81-15 (F1-2) |
| E4 | tests/test_s81_kb_schema.py::test_s14_p02_no_kb_relation_literal_outside_the_leaf | allows ONLY the `KB_MERCHANTS_TABLE = "kb_merchants"` line of merchant_registry.py (file + exact line text); docstring names S81-15 (F1-2) |
| E5 | tests/test_domain_s76.py::test_t4_robots_user_agents_point_at_getmyez_and_mirror_each_other | reads the UA through robots_eval.QARENBOT_UA (the dead mirror literal in sitemap_discovery_service.py is deleted, F1-8) |
| E6 | tests/test_s81_s15_registry_robots.py::test_r9_entry_round_trip, ::test_r22_seed_rows_counts_and_contract | RED-A/B (F1-1): want key `search` -> `search_descriptor`; `_registry_ok([e2], s.domain)`; `_registry_ok(r["registry"], r["host"])` (the RED stubbed the pre-S81-14-fix kb_service) |
| E7 | tests/test_s81_s15_registry_robots.py::test_r38_no_impersonation_and_log_hygiene | eol-agnostic: CRLF -> LF first, then pure ASCII and no lone CR (F1-7; green on a CRLF and on an LF working copy) |
| E8 | tests/test_s81_s15_registry_robots.py::test_r41_railway_robots_cron_config | the watch list gains app/services/merchant_registry.py and app/services/deny_hosts.py (F1-9) |

RED file sha256: 5bb3bc4c1ccd21abffeece4b221d82289b9a250008c391bf91f3c0e23f52be09 -> 66ac62995ab5738510216f228112d8437ed51d1c0901acd49d993cb7ad11b9e1 (E6 + E7 + E8 only; every other row byte-identical). Fixture 314d5e0d2b8fd81929e0f2ee15399afb77b73efc5735e60b3dccb0b882e50d84 unchanged. In the GREEN-owned G file: gc2 / gc6 / gc7 read with `.get()` (F1-19), gc5 follows F1-14 (`next_reread` moves to the lapse day), gc8 is widened and renamed (F1-15).

## Seed census (measured at ad1e260c from the real seed builders)

- 410 rows = 317 live, 92 candidate, 1 blocked (fragrantica.com, deny), 1 collision, 411 entries.
- First sample URL vs the row host: same host 248, subdomain 119, cross-site 2 (bh.redtagfashion.com, somman.com), PARENT 3 (parfumdeal.salla.sa, rose-store-27.salla.sa, journey1.salla.sa: now their own `https://<host>/robots.txt` with `https://salla.sa` under other_origins), no sample 38.
- `--classify` scope: 244 live platform-NULL rows = 234 blank-mechanism + 10 unmapped-mechanism (beautyboothqa.com rest_json, bolo.bh sitemap, boutiqaat.com sitemap, danube.sa algolia, extra.com unbxd, goldenscent.com algolia, nahdionline.com algolia, nasserpharmacy.com json_api, noon.com noon_catalog, sephora.me provider); the first 20 by host are all blank-mechanism.

## Gates (bounded runner, .venv-qaren, one pytest at a time; on the committed bytes of ad1e260c unless noted)

- RED proof of E6 at base 86d5a24d (detached scratch worktree with the amended RED file + fixture, removed and verified gone): r9, r22 (and r38, r41) fail on AssertionError only: `[pyt] tag=s15f1-red-r9r22-base start=2026-10-29 00:46:31 end=2026-10-29 00:46:35 elapsed=4s bound=600s status=FAIL rc=1` ([hermeticity] 4, [netguard] blocked 0).
- RED step on the pre-fix code bytes (the new rows appended, code = GREEN): 24 failed, every one an AssertionError (gc5, gc8, f1_3, f1_3b x9, f1_4, f1_6a, f1_6b, f1_10a, f1_10b, f1_12, f1_13a, f1_14, f1_23 x2, r41, p01), 776 passed (the PIN-type rows f1_5a/b/c, f1_6c, f1_13b, f1_16 green: their proof is their mutant): `[pyt] tag=s15f1-red-prefix start=2026-10-29 00:54:40 end=2026-10-29 00:55:03 elapsed=22s bound=600s status=FAIL rc=1` ([hermeticity] 800, [netguard] 0).
- Both unit files, flags unset: 264 passed `[pyt] tag=s15f1-unit-off start=2026-10-29 01:03:12 end=2026-10-29 01:03:26 elapsed=15s bound=600s status=OK rc=0`; ENABLE_MERCHANT_REGISTRY_DB=true + ENABLE_ROBOTS_REGISTRY_CRON=true exported: 264 passed `[pyt] tag=s15f1-unit-on start=2026-10-29 01:03:27 end=2026-10-29 01:03:41 elapsed=14s bound=600s status=OK rc=0` ([hermeticity] 264, [netguard] 0 both).
- PIN rows with ENABLE_MERCHANT_REGISTRY_DB=false ENABLE_ROBOTS_REGISTRY_CRON=off exported: 37 passed `[pyt] tag=s15f1-pins-falsy start=2026-10-29 01:03:49 end=2026-10-29 01:03:55 elapsed=6s bound=600s status=OK rc=0`.
- Identity pins A (21 files incl. test_domain_s76): 932 passed, 3 skipped `[pyt] tag=s15f1-pinsA start=2026-10-29 01:04:04 end=2026-10-29 01:04:19 elapsed=16s bound=1200s status=OK rc=0`; B (8 spec pins + test_s81_kb_schema + test_retro_w0_4 + test_retro_w0_4_efg): 1111 passed `[pyt] tag=s15f1-pinsB start=2026-10-29 01:04:26 end=2026-10-29 01:06:25 elapsed=119s bound=1200s status=OK rc=0` ([netguard] blocked 22 from 21 nodes: test_hermeticity_pins' designed rows).
- CI-order set (GREEN's 31 + test_s81_kb_schema + test_retro_w0_4 + test_retro_w0_4_efg, alphabetical): 2307 passed, 3 skipped `[pyt] tag=s15f1-ci-order start=2026-10-29 01:13:13 end=2026-10-29 01:15:39 elapsed=145s bound=1200s status=OK rc=0` ([hermeticity] 2307, [netguard] 22 from 21 nodes, designed).
- R38 on a CRLF working copy of the four new .py files (byte copies, restored, sha-verified): `[pyt] tag=s15f1-r38-crlf start=2026-10-29 01:28:46 end=2026-10-29 01:28:50 elapsed=5s bound=600s status=OK rc=0`.
- Comm set (F1-28): GREEN's 340 files UNION a re-derivation at ad1e260c (edited modules, the new symbols, importers of the edited tests) = 342 (+ tests/test_retro_w0_1.py, tests/test_url_validator_offloop.py: symbol class, both green), 14 chunks of <= 25, bound 1200, against GREEN's fresh base record at 86d5a24d. HEAD failures = 3, identical to base: tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence and ::test_truth_on_prefix_static_and_cacheable (cold tiktoken ERRORs), tests/test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged (red at 86d5a24d in the shared venv while the anthropic SDK is installed; green on main since #374). **branch-only-new = EMPTY.** Netguard blocks total 389 = GREEN's HEAD total (the unit adds no network attempt).
  - `[pyt] tag=s15f1-head-00 start=2026-10-29 01:15:54 end=2026-10-29 01:16:29 elapsed=36s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-01 start=2026-10-29 01:16:30 end=2026-10-29 01:17:23 elapsed=54s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-02 start=2026-10-29 01:17:23 end=2026-10-29 01:17:39 elapsed=16s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-03 start=2026-10-29 01:17:40 end=2026-10-29 01:18:11 elapsed=31s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-04 start=2026-10-29 01:18:11 end=2026-10-29 01:19:20 elapsed=69s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-05 start=2026-10-29 01:19:27 end=2026-10-29 01:19:50 elapsed=23s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-06 start=2026-10-29 01:19:50 end=2026-10-29 01:20:14 elapsed=24s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-07 start=2026-10-29 01:20:15 end=2026-10-29 01:20:32 elapsed=17s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-08 start=2026-10-29 01:20:32 end=2026-10-29 01:21:25 elapsed=53s bound=1200s status=FAIL rc=1` (the two cold-tiktoken ERRORs)
  - `[pyt] tag=s15f1-head-09 start=2026-10-29 01:21:25 end=2026-10-29 01:24:36 elapsed=192s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-10 start=2026-10-29 01:24:42 end=2026-10-29 01:26:13 elapsed=91s bound=1200s status=FAIL rc=1` (the u8d node)
  - `[pyt] tag=s15f1-head-11 start=2026-10-29 01:26:13 end=2026-10-29 01:26:33 elapsed=20s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-12 start=2026-10-29 01:26:33 end=2026-10-29 01:27:24 elapsed=51s bound=1200s status=OK rc=0`
  - `[pyt] tag=s15f1-head-13 start=2026-10-29 01:27:24 end=2026-10-29 01:27:51 elapsed=27s bound=1200s status=OK rc=0`
- py_compile + ruff 0.16.5 `--select E9,F63,F7,F82` clean on every touched python file; the full repo ruff config clean on the new modules, scripts and the G file; new files LF + ASCII; edited CRLF files keep CRLF and their non-ASCII counts; the pre-commit hook passed.
- The four tests/test_precommit_hook*.py files: NOT run (no .githooks input changed; CI is the arbiter).

## Mutation table (fix round 1; byte copies, one exact-string edit matched once, both unit files, restore + sha256 compare; all 19 KILLED on AssertionError only)

| id | mutant | killed by (G) |
|---|---|---|
| G7c | a parent-host sample treated as same-site | f1_4 |
| G9a | score_source reads LOOKUP | f1_5a |
| G9c | source_usage reads LOOKUP | f1_5b |
| G9d | is_render_only_domain reads LOOKUP | f1_5c |
| G4b | the cron paged read without .order(host) | f1_16 |
| EM1 | default_validate accepts every URL past the name check | f1_6b, f1_13a, f1_13b |
| EM2 | default_fetch lets the library follow redirects | f1_6a |
| EM3 | the cron entry wires a no-op validator | f1_6c |
| EM6 | the byte cap removed | f1_6a |
| SLACK | run_cron passes no due slack | f1_3 |
| DENY_PROBE | probe_host deny belt removed | f1_10a |
| DENY_CLASSIFY | classify_host deny belt removed | f1_10b |
| DNS_AS_SSRF | a resolver failure labelled SSRF | f1_13a |
| SSRF_AS_DNS | every refusal labelled DNS | f1_6b, f1_13b |
| NEXT_REREAD | the young residential branch keeps the stale next_reread | gc5, f1_14 |
| KNOB | _int_knob maps 0 < v < 1 to the default | f1_23 x2 |
| TASK_CTX | the refresh task inherits the request context | f1_12 |
| TASK_LOCK | the refresh coroutine created under _LOCK | f1_12 |
| CLASSIFY_SCOPE | --classify narrowed back to blank-mechanism rows | gc8 |

Each run `[pyt] tag=s15f1-mut-<id> ... elapsed=15-21s bound=600s status=FAIL rc=1`, 2026-10-29 01:07:38 .. 01:12:52; the GREEN round's 65-mutant RED table and the adversaries' tables stand for the unchanged code.

## Stated limits

- Inert until the owner applies 045 and runs the seed; flag ON before that = the code registry + one WARNING per window. The first compares of a process use the code registry until the first refresh lands; a table change reaches a process within one memo window.
- One origin per host row: a cross-site or PARENT-host sample origin and an adapter origin on another site are listed in `robots.other_origins`, not read (D14 treats them as missing: skip + queue); adapters on API hosts (salla, unbxd, algolia, rest_json) have no record.
- A candidate whose sample PDP redirects to another origin (http -> https, www <-> apex) never passes the PDP gate (fail-closed; the seed lists the canonical URL) (F1-17).
- Rule lists are capped at 200 per agent (`rules_truncated`); the byte cap bounds what is decoded and stored, but curl_cffi still receives (buffers) the whole response (no streamed read).
- A redirect hop TO a deny_hosts host is not refused by name (the per-hop SSRF check still runs); the belt is at the entry points (F1-10).
- `default_validate` calls `url_validator.validate_external_url_async` directly (spec 2.5): its docstring at app/utils/url_validator.py:412 ("Only reached under ENABLE_OFFLOOP_DNS_RESOLVE") is now inexact (the dns-resolve pool and its 2 s bound run whatever the flag; the memo stays flag-gated); not edited (outside the footprint) (F1-13). Only a refused URL pays one extra resolve (5 s bound) that tells a resolver failure from a refused address; both answers are fail-closed.
- The three residential seed records (klinq.com, nazih.qa, numberc.com) are dated 2026-08-31: past the 30-day protection on the first run, so owner step 3 must precede owner step 5 (OWNER_ACTIONS item 30, F1-20).
- With ENABLE_MERCHANT_REGISTRY_DB on `web` only, the price-warmer would keep the code registry and keep fetching cron-blocked hosts: owner step 7 flips both services in one window (F1-18).
- The cron runs the code of its last deploy: railway.robots.json watches the script, the config and the cron's direct imports (robots_registry.py, robots_eval.py, merchant_registry.py, deny_hosts.py), NOT the deeper closure (url_validator, kb_service, the price stack the PDP gate imports): `railway redeploy -s <cron service>` after such a change (F1-9). Config-as-code is deprecated for legacy services on 2026-12-01.
- S81-14 follow-up (F1-24, DEFECT_LEDGER S81-14b): kb_service._registry_ok derives the allowed entry keys from get_type_hints(Source), so the appended Source.deny widens it to accept an entry key `deny` that _source_from_entry ignores (inert; deny is a row column).
- Gate 6 (the router suites with ENABLE_MERCHANT_REGISTRY_DB exported, GREEN round) proves the fallback only (those suites prime no memo); the DB branch under the consumer functions is covered by the memo-primed rows (R p1 x28, r11b, r21b; G f1_5a/b/c) (F1-26).
- The memo task gets its fresh context through `contextvars.Context().run(loop.create_task, coro)`: the effect of `create_task(coro, context=contextvars.Context())` without depending on the loop accepting the keyword (uvloop 0.22.1 on Railway is not measurable on this Windows box).
- On a Windows checkout with core.autocrlf=true the four new .py files arrive CRLF; R38 is now eol-agnostic (E7); no .gitattributes change in this unit (a later unit may add eol=lf).
- Live adapters keep impersonate=chrome until the owner's UA ruling after M6; Crawl-delay is parsed in-house; the PDP gate's real extraction / platform detection on a live PDP is NOT MEASURED (recorders); the seed's existing-host read is one PostgREST page (refuses at 1,000 rows).

## Owner steps (names only; a dated ledger line each)

1. Apply 045 (S81-14) with its PRECHECK / POSTCHECK.
2. `python -m scripts.seed_kb_merchants` (dry run): record `rows=410 live=317 candidate=92 blocked=1 collisions=1 entries=411`; then `--apply` with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (names only).
3. BEFORE step 5, from a residential connection: `--source residential --hosts klinq.com,nazih.qa,numberc.com --apply` (their seed records are dated 2026-08-31; OWNER_ACTIONS item 30).
4. Optionally `--classify` (20, dry run) and record the counts.
5. Create the Railway cron service from `railway.robots.json` (start `python -m scripts.cron_robots_registry`, restart NEVER; never `web` / `price-warmer`), schedule it daily (for example `30 2 * * *`), set `ENABLE_ROBOTS_REGISTRY_CRON=true`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` on that service only (`ROBOTS_DUE_SLACK_SECONDS` optional, default 3600).
6. Review ToS for candidates reported `failing_gate = tos` (`tos {reviewed_at, verdict, terms_url}`).
7. After one full pass and after App Review approval: `ENABLE_MERCHANT_REGISTRY_DB=true` on `web` AND `price-warmer` in the same canary window (until then the warmer keeps the code registry); rollback = unset on both (per call).

## NOT MEASURED

- Real curl_cffi, DNS, redirects and Supabase / PostgREST behaviour (paging, ordering, the conditional-update return shape): fakes and patched seams only (curl_cffi.requests.get and socket.getaddrinfo patched in G f1_6a / f1_6b / f1_13a / f1_13b).
- uvloop (Railway) task creation: not available on this Windows box.
- extract_price_from_html / detect_platform_verdict / detect_platform on a real PDP (recorders); real cron wall time over 410 hosts; Protego parity (R-S15-19, by design).

## Rebase (F1-29, the next step)

Onto origin/main a8f01379 (S81-06 #374): CLAUDE.md union in session order (S81-06 then S81-15); tests/test_s81_kb_schema.py carries main's E11 hunk (the p06 digest) and this unit's E3 / E4 hunks; requirements untouched; a FRESH base record at a8f01379 for the comm set; the u8d node is expected green at that main.

&#x1F916; Generated with [Claude Code](https://claude.com/claude-code)
