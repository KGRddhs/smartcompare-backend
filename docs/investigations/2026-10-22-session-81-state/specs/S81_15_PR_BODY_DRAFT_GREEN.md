# S81-15 REGISTRY-ROBOTS-DENY: kb_merchants registry memo + daily robots cron (two dark flags)

Branch `feature/s81-s15-registry-robots-deny`, HEAD `ce01175f`, base `86d5a24d` (main with S81-14 #373). Both flags default OFF, read per call, new names (unset in production by construction).

## What the flags do

- `ENABLE_MERCHANT_REGISTRY_DB` (+ `MERCHANT_REGISTRY_MEMO_SECONDS` 600 [300..900], `MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS` 5 [1..30], `MERCHANT_REGISTRY_MAX_STALE_SECONDS` 3600 [900..21600]): the router's registry comes from `kb_merchants` through a per-process memo (`app/services/merchant_registry.py`). One paged read (`status in (live, blocked)`, `.order('host')`, 500-row pages) in a background task via `asyncio.to_thread` under `wait_for`; callers never await it. Two sets (R-S15-1): SELECTION (`source_router.registry_rows`, read only by `_routable_registry`) = live, not-denied rows; LOOKUP (`registry_lookup_rows`, read by `_registry_row_for_host` and the three direct readers) keeps blocked and denied rows, so a cron-blocked host keeps its tier, currency and global-tier refusals. sha256 snapshot over the decode columns + the catalog flag (equal snapshot = same list objects). Failures never raise: code registry until a good load, then the last good list up to max stale; one WARNING per window by reason. Flag OFF: `SOURCE_REGISTRY` by identity, no read, no task, no log.
- `ENABLE_ROBOTS_REGISTRY_CRON` (+ `ROBOTS_CRON_MAX_HOSTS` 500 [1..5000], `ROBOTS_CHALLENGE_PARK_DAYS` 7 [1..30]): `app/services/robots_registry.py` + `scripts/cron_robots_registry.py` (a new Railway cron service, `railway.robots.json`). Daily, sequential, polite (max(Crawl-delay<=60, 2 s)), QarenBot UA (`robots_eval.QARENBOT_UA`), no impersonation, redirects by hand with the SSRF check on every hop, robots read from the probe origin; fail-closed `decide_robots`; the D14 record (rules + probed, frozen by the fixture); transitions (live -> blocked robots_disallow / robots_unreadable / challenge / ssrf_redirect, Option A rejoin, candidates never blocked, promotion gates robots -> tos -> pdp (priced extraction under the sanitised title) -> platform); Option C residential rider (no datacenter downgrade of a residential / operator record < 30 days); conditional updates on `updated_at`. Flag OFF: one INFO, no read, no fetch. The live path is untouched (D14 owns live lookups).
- Off-clock seed `scripts/seed_kb_merchants.py` (dry run default; `--apply`, `--classify [N]`, `--source residential --hosts`): 410 rows (317 live / 92 candidate / 1 blocked deny), 411 entries, each from `kb_service.build_merchant_row` + `created_at` on INSERT only.

## Rulings / defects -> test nodes (tests/test_s81_s15_registry_robots.py unless noted; GC rows in tests/test_s81_s15_gate_rows.py)

| id | what | nodes |
|---|---|---|
| R-S15-1 / GC-9 | SELECTION vs LOOKUP, blocked rows keep tier + refusals | r4, r8b, r11, r11b, r11c[off,on], r21, r21b, p7, p8 |
| R-S15-2 / GC-6 / GC-7 | redirects by hand, SSRF per hop, probe origin, other_origins | r34b, r34c, r35, gc6, gc7 |
| R-S15-3 | the D14 record contract | r29 (fixture), r29b, r29c[x3], r29d, r32b |
| R-S15-4 / GC-5 | Option C residential rider | r31b, r22 (seeded residential reads), gc5 |
| R-S15-5 / R-S15-6 | D9 emitter pin (E1), UA in robots_eval (E2) | r39, r40, p9 |
| R-S15-7 / R-S15-8 | memo: off-loop read, timeout, sha snapshot, max stale, B1 PINs | r2, r2b, r5, r6, r15, r16, r17[x6], r17b, r19, r20, r20b, p1[x28], p2, p3 |
| R-S15-9 / R-S15-10 / GC-4 | origins + catalog state, status filter + paging + order | r6, r6b, r7[x4], r8[x2], r12, r13, r14, gc4 |
| R-S15-11 / GC-1 / GC-2 / GC-3 | column ownership, conditional writes, seed wraps the builder | r23, r24, r25, r36b, gc1, gc2, gc3 |
| R-S15-12 | challenge = body signature or cf-mitigated only (both anchor states) | r27[x36], r30[x9] |
| R-S15-13 / GC-8 | --classify scope, dry run | r26, r26b, gc8 |
| R-S15-14 | railway.robots.json | r41 |
| R-S15-15 / R-S15-17 / R-S15-18 / GC-10 | politeness, probe order, candidates, PDP price gate, title name | r31, r32[x7], r34, r36, gc10 |
| spec 2.9 / R1-R3 | flag + knob readers | r1[x13], r3[x11], r3b[x13] |
| hygiene | light import, no impersonation, log hygiene, scripts not imported | r37, r38, r43, p4, p5, p6 |

## Deliberate pin changes (spec 4.1 as amended)

| # | file::node | change | status |
|---|---|---|---|
| E1 | tests/test_legal_disclosure_s77.py::test_s77_d9_bot_page_claim_matches_the_runtime | QARENBOT_FILES += app/services/robots_registry.py | APPLIED |
| E2 | tests/test_legal_s78.py::test_s78_r4_user_agent_is_the_lr7_value (UA_FILES) | sitemap _ROBOTS_UA -> (app/services/robots_eval.py, QARENBOT_UA) | APPLIED |
| E3 | tests/test_s81_kb_schema.py::test_s14_p01_no_importer_of_kb_service | exempt app/services/merchant_registry.py (GC-2: the seed builders wrap build_merchant_row) | NOT APPLIED (brief: E1/E2 only); red at HEAD; S81-14 PR #373 names p01/p02 the deliberate-change points for S81-15; measured green on a copy |
| E4 | tests/test_s81_kb_schema.py::test_s14_p02_no_kb_relation_literal_outside_the_leaf | exempt the ONE literal 'kb_merchants' (KB_MERCHANTS_TABLE) in merchant_registry.py | NOT APPLIED; same |
| RED-A | test_r9_entry_round_trip | want_keys 'search' -> 'search_descriptor'; kb._registry_ok([e2]) -> kb._registry_ok([e2], s.domain) | wrong row vs the real post-F1-3 validator; NOT edited (frozen); measured green on a copy |
| RED-B | test_r22_seed_rows_counts_and_contract | kb._registry_ok(r['registry']) -> kb._registry_ok(r['registry'], r['host']) | same |

Unlisted reader kept green without an edit: tests/test_domain_s76.py::test_t4 regex-reads `_ROBOTS_UA = "..." %` from sitemap_discovery_service.py; the literal stays there as a mirror and `_ROBOTS_UA` is rebound to `robots_eval.QARENBOT_UA` on the next line (R39 identity). Clean alternative for a ruling: E5 = test_domain_s76 reads robots_eval QARENBOT_UA, then delete the mirror line.

## Gates (bounded runner, .venv-qaren, one pytest at a time)

- Gate 0 (RED file at base 86d5a24d): 192 failed (all AssertionError) / 37 passed. `[pyt] tag=s15g-gate0 elapsed=20s status=FAIL rc=1`, [hermeticity] 229, [netguard] blocked 0.
- Unit files at HEAD, flags unset: 2 failed (R9, R22: RED-A/B) / 236 passed `[pyt] tag=s15g-unit-off elapsed=15s status=FAIL rc=1`; flags exported ON: same `[pyt] tag=s15g-unit-on elapsed=17s status=FAIL rc=1`; PIN rows with falsy exports 37/37 `[pyt] tag=s15g-pins-falsy elapsed=6s status=OK rc=0`; gate rows 9/9 `[pyt] tag=s15g-gaterows1 elapsed=5s status=OK rc=0`; final at HEAD (unit files + E1/E2 files + test_domain_s76 + test_retro_w0_4) 460 passed / 2 failed (R9, R22) `[pyt] tag=s15g-final-head elapsed=80s status=FAIL rc=1`.
- RED-A/B measured on a copy: `[pyt] tag=s15g-r9r22-amended elapsed=4s status=OK rc=0` (2 passed). E3/E4 measured on a copy: `[pyt] tag=s15g-kbp01p02-amended elapsed=5s status=OK rc=0` (2 passed).
- Identity pins (spec 1.10, 26 files + E1/E2 files + test_domain_s76 + test_s81_kb_schema): A 932 passed `[pyt] tag=s15g-pinsA elapsed=15s status=OK rc=0`; B `[pyt] tag=s15g-pinsB elapsed=57s status=FAIL rc=1` (only p01/p02 = E3/E4).
- CI-order set (31 files): 1472 passed / 2 failed (R9, R22) `[pyt] tag=s15g-ci-order elapsed=106s status=FAIL rc=1`, [hermeticity] 1474, [netguard] blocked 22 from 21 nodes (test_hermeticity_pins' designed blocks).
- Comm set: 340 files (the RED's 308 UNION 32 re-derived at HEAD: module / symbol / source-reader / tree-walker / railway reader / named pins + CLAUDE.md readers / importers of edited tests / unit files; minus test_precommit_hook*), 14 chunks of <= 25, bound 1200, at HEAD and at a FRESH base record (detached scratch worktree at 86d5a24d, no junction, removed and verified gone). HEAD failures 7; base failures 3 + the 192 RED nodes of gate 0. Identical both sides: tests/test_prompt_truth.py (the two cold-tiktoken ERRORs) and tests/test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged (environmental: sentry auto-enables AnthropicIntegration on the shared venv; red at base). **branch-only-new = 2: test_s14_p01 + test_s14_p02 (E3/E4 above), nothing else.**
- Gate 6 (spec 7.6, router chunks = the 48 files referencing source_router, ENABLE_MERCHANT_REGISTRY_DB=true exported): `[pyt] tag=s15g-routeron-00 elapsed=28s status=OK rc=0`, `[pyt] tag=s15g-routeron-01 elapsed=34s status=FAIL rc=1` (only p01/p02, flag-independent); no node turned red under the flag.
- py_compile + ruff E9,F63,F7,F82 clean (full repo ruff config clean on the new files); new files LF + ASCII; edited CRLF files no whole-file diff, non-ASCII counts unchanged; pre-commit hook passed.

## Stated limits

- Inert until the owner applies 045 and runs the seed; flag ON before that = the code registry + one WARNING per window.
- First compares of a process use the code registry until the first refresh lands; a table change reaches a process within one memo window.
- One origin per host row: a cross-origin sample or adapter origin is listed in `robots.other_origins`, not read (D14 treats it as missing). Adapters on API hosts (salla, unbxd, algolia, rest_json) have no record.
- Rule lists are capped at 200 per agent (`rules_truncated` marks a cap).
- The three 2026-08-31 residential reads are seeded with that date: past 30 days on the first run, so a fresh `--source residential` read is needed first or the datacenter result applies.
- The PDP gate's real extraction / platform detection on a live PDP is NOT MEASURED (recorders in the tests).
- The seed's existing-host read is one PostgREST page (refuses at 1,000 rows).
- The cron runs the code of its last deploy (watch patterns: its script, robots_registry.py, robots_eval.py, the config); price_service / platform_router changes do not redeploy it.
- On a Windows checkout with core.autocrlf=true the four new .py files arrive CRLF, which reddens R38's byte check locally (CI on Linux is LF).
- Live adapters keep impersonate=chrome until the owner's UA ruling after M6; Crawl-delay is parsed in-house.

## Owner steps (names only; a dated ledger line each)

1. Apply 045 (S81-14) with its PRECHECK / POSTCHECK.
2. `python -m scripts.seed_kb_merchants` (dry run): record `rows=410 live=317 candidate=92 blocked=1 collisions=1 entries=411`; then `--apply` with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (names only).
3. From a residential connection: `--source residential --hosts klinq.com,nazih.qa,numberc.com --apply`.
4. Optionally `--classify` (20, dry run) and record the counts.
5. Create the Railway cron service from `railway.robots.json` (start `python -m scripts.cron_robots_registry`, restart NEVER; never `web` / `price-warmer`), schedule daily, set `ENABLE_ROBOTS_REGISTRY_CRON=true`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` on that service only. Config-as-code is deprecated for legacy services on 2026-12-01 (dashboard watch paths as the fallback).
6. Review ToS for candidates reported `failing_gate = tos` (`tos {reviewed_at, verdict, terms_url}`).
7. After one full pass and after App Review approval: `ENABLE_MERCHANT_REGISTRY_DB=true` on `web` in its own canary window; rollback = unset (per call).

Merge needs the orchestrator's rulings on E3/E4 and RED-A/B first (see the pin table); the CLAUDE.md row sits after the S81-14 block (union at rebase).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
