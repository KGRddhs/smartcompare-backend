# S81-G4 KB-SERVE: S81-18 KB-FIRST-SERVE + S81-19 GAP-QUEUE + D16 OPERATOR-INGEST + D17 MEASURE-COVERAGE

Base `0b19de5bcc1416111d48bc725359b95151a658ca` (origin/main as fetched in the final round, #384 G3; `git rebase origin/main` reported the branch up to date: zero commits replayed, zero conflicts). HEAD: `ded9a8df5da0ad120a9df242076b89514b066b9d` (two commits on the base: `48a82a5e` the GREEN commit carrying the five frozen RED files with E-G4-1; `ded9a8df` fix round 1 with the gate rows and the CLAUDE.md stated-limit ids). Branch `feature/s81-g4-kb-serve`. The final round committed nothing.
The fourth SAFE group under LC-9 (one spec, one RED, one GREEN, one adversary). Spec `.qa-s80/S81-G4_UNIT_SPEC.md` (sha256 a3888322...), rulings `specs/RULINGS_S81_G4.md` (R-G4-1..14), RED gate `specs/GATE_S81_G4.md` (GC-1..8).

Every flag is a NEW name, default OFF, read PER CALL; flag OFF = one env read and the base statements at every hook site. No migration, no Lua, no middleware, no legal text, no client file, no new dependency, no new external host, no new credential name.

## S81-18 KB-FIRST-SERVE + the verdict-cache key log
- Flags: `ENABLE_KB_FIRST_SERVE`, `ENABLE_VERDICT_CACHE_LOG` (independent); knobs `KB_FIRST_SERVE_TIMEOUT_SECONDS`, `KB_FIRST_SERVE_MAX_ASOF_DAYS`, `VERDICT_CACHE_LOG_MAX_KEYS`.
- Code: NEW `app/services/kb_serve.py`; hooks H0-H8 in `structured_comparison_service.py` (H0 the one card task before both product gathers; H1-H6 in `_fetch_product_data`; H7 `metadata.kb_hit` in `_stamp_unit_metadata`; H8 the key line before both verdict calls + the seed after a successful verdict); the keyword `kb_price_asof` on the three entries and at the five route call sites (`text_routes` x4, `image_routes` x1); the C4 guard in `kb_ingest` (a KB-served price is never re-observed).
- RED nodes: `tests/test_s81_s18_kb_first_serve.py` R1-R20 (25 nodes) + PIN P1-P4 (13 nodes, incl. the golden `tests/fixtures/s81_s18_flag_off_golden.json`).
- Flip preconditions: 045 applied; `ENABLE_SYNC_DB_OFFLOAD` ON on `web`; the KB populated (G2 APPLY, `ENABLE_KB_INGEST` ON); `ENABLE_VERDICT_CACHE_LOG` a week first.

## S81-19 GAP-QUEUE (the enrich worker + the price refresh)
- Flags: `ENABLE_KB_ENRICH_WORKER` (mode: OFF / DRY / `apply`), `ENABLE_KB_GAP_FILL`, `ENABLE_KB_GAP_WEB_SEARCH` (INERT: logs `not_built` once per run); knobs `KB_ENRICH_*`.
- Code: NEW `scripts/cron_kb_enrich.py` + `railway.kbenrich.json`. Redis single flight `SET kbenrich:sf:<hash> NX EX` fail-CLOSED (R-G4-6), owner check before DELETE; one state CAS per gap (payload `{state}` only); `PoliteFetcher(require_tos=True)` at 4 s; no adapter / render / LLM import; no `kb_service` token in the script.
- RED nodes: `tests/test_s81_s19_gap_queue.py` R1-R15 (32 nodes) + PIN P1-P2.
- Flip preconditions: 045; the robots cron + ToS verdicts recorded; the `kb-enrich` service; one DRY run first.

## D16 OPERATOR-INGEST
- Flag: `ENABLE_OPERATOR_INGEST`; knob `KB_OPERATOR_PAGE_MAX`.
- Code: NEW `app/services/kb_operator.py`; `GET /api/v1/admin/kb/operator` + `POST /api/v1/admin/kb/ingest` appended to `app/api/admin_routes.py` (`include_in_schema=False`; the flag gate the FIRST dependency raising the Starlette base-class 404, then the EXISTING `verify_admin_key`, the existing 30/min limiter); NEW runbook `docs/runbooks/2026-11-kb-operator-ingest.md` (the clipboard-only bookmarklet, the curl template, names only).
- Refusals: 400 `KB_URL_REFUSED` / `KB_HOST_UNKNOWN` / `KB_HOST_CANDIDATE` / `KB_HOST_NOT_REVIEWED` / `KB_IDENTITY_UNRESOLVED` / `KB_PAYLOAD_TOO_LARGE` / `KB_STORE_UNAVAILABLE` (a raising write too) / `KB_LICENCE_FIELD` (R-G4-7: the licence spec fields only with `source` partner). Never a bare 503.
- RED nodes: `tests/test_s81_d16_operator_ingest.py` R1-R11 (11 nodes) + PIN P1-P3 (7 nodes; P2 the OpenAPI path-set sha, held in `SCHEMA_PATHSET_SHA256` since E-G4-1).
- Flip preconditions: 045; D17 running; the ToS review on each blocked host captured.

## D17 MEASURE-COVERAGE
- Flag: `ENABLE_KB_COVERAGE_ROLLUP` (mode); knob `KB_COVERAGE_MAX_HOSTS`.
- Code: NEW `scripts/cron_kb_coverage.py` + `railway.kbcoverage.json`: the closed metric list over the `kb_offers_latest` view, ages against `kb_seed_common._now()`, 4-dp shares, every gap / hint state incl. zeros, ONE HGETALL pipeline over the live + blocked hosts (an empty hash = absent, never zero), `search_logs` read with exactly `products_found,success,is_synthetic,created_at`, ONE upsert on (day, metric) through `build_coverage_row`.
- RED nodes: `tests/test_s81_d17_coverage.py` R1-R9 (23 nodes).
- Flip preconditions: 045; the `kb-coverage` service; one DRY run first.

## Deliberate pin changes (spec 4.1 / 12.4)
| row | file | change |
|---|---|---|
| E1 | `tests/test_s81_kb_schema.py` | P01_ALLOWED + P01_FUNCTIONS gain `app/services/kb_serve.py` and `app/services/kb_operator.py` (`kb_leaf`, the exact import line) |
| E2 | `tests/test_s81_kb_schema.py` | P02_ALLOWED gains five exact lines: kb_serve `KB_PRODUCT_CARD_RPC`, kb_operator `KB_SPECS_TABLE` + `KB_COVERAGE_TABLE`, cron_kb_coverage `KB_COVERAGE_TABLE` + `KB_OFFERS_LATEST_VIEW` |
| E-G4-1 | `tests/test_s81_d16_operator_ingest.py` (frozen RED) | the digest identifier `OPENAPI_PATHS_SHA256` renamed `SCHEMA_PATHSET_SHA256` at its two occurrences (lines 53 / 597), value and comment unchanged: the pre-commit gitleaks step read the old name (it carries `API`) + 64 hex as a generic-api-key (RULINGS_FIX1_S81_G4 F1-1) |
No other pin moved. GREEN-owned gate rows (fix round 1, F1-3): NEW `tests/test_s81_g4_gate_rows.py`, G4-GR1 (a FULL hit carries the card's `rating` and `review_count` in the `_fetch_product_data` result; kills ADV-3) and G4-GR2 (the S81-19 single-flight release deletes only a lock holding this run's id; kills ADV-7).

## Counts and gates (final round at HEAD `ded9a8df`, RULINGS_REBASE_S81_G4 RB-G4-1..5)
- Frozen files byte-identical on disk and as `git show HEAD:<path>`: `tests/test_s81_s18_kb_first_serve.py` 7be2ed3a..., `tests/fixtures/s81_s18_flag_off_golden.json` 8ab15ee0..., `tests/test_s81_s19_gap_queue.py` a400b679..., `tests/test_s81_d16_operator_ingest.py` 1bb52146... (E-G4-1), `tests/test_s81_d17_coverage.py` 03b7ccf6...; the gate rows `tests/test_s81_g4_gate_rows.py` 0dc8d17f...; CLAUDE.md d31b1fe6... (working copy); every app/, scripts/, docs/ and railway file equal to the GREEN table. No pin rows this round (none ruled).
- `git diff --name-only origin/main...HEAD` = exactly the 20 G4 files; `git diff --check` clean; no whole-file diff (20 files, 8885 insertions, 17 deletions); no conflict markers in CLAUDE.md, app/, tests/.
- The four RED files + the gate rows + `tests/test_s81_kb_schema.py` + `tests/test_secret_scan_static.py`, flags OFF: `[pyt] tag=g4f-red-off start=2026-11-04 23:09:26 end=2026-11-04 23:09:57 elapsed=32s bound=600s status=OK rc=0` (679 passed; [netguard] blocked 0)
- The four RED files + the gate rows, the seven flags exported in ONE runner call (the two modes as true = DRY): `[pyt] tag=g4f-red-on start=2026-11-04 23:10:00 end=2026-11-04 23:10:09 elapsed=9s bound=600s status=OK rc=0` (119 passed; [netguard] blocked 0)
- CI-order set (spec 12.2, the 15 GREEN files + the gate rows) OFF: `[pyt] tag=g4f-ciorder-off start=2026-11-04 23:10:16 end=2026-11-04 23:11:15 elapsed=59s bound=1200s status=FAIL rc=1` (5 failed, 1541 passed; the 5 = the environmental `test_s16_r27_hygiene_of_g2_files` CRLF nodes, baseline both sides; [netguard] blocked 28 attempts from 10 nodes, the base figure)
- R8 pair `tests/test_sentry_channels_u8d_unit.py` + `tests/test_sentry_channels_u8d.py`: `[pyt] tag=g4f-r8-pair start=2026-11-04 23:11:16 end=2026-11-04 23:11:41 elapsed=25s bound=600s status=OK rc=0` (273 passed)
- `tests/test_paid_route_metering.py` without / with the seven flags: `[pyt] tag=g4f-paid-off start=2026-11-04 23:11:44 end=2026-11-04 23:11:51 elapsed=7s bound=600s status=OK rc=0` / `[pyt] tag=g4f-paid-on start=2026-11-04 23:11:53 end=2026-11-04 23:11:57 elapsed=4s bound=600s status=OK rc=0` (21 passed each)
- CLAUDE.md readers `tests/test_ci_gates.py` + `tests/test_behavior_dimension_translation.py`: `[pyt] tag=g4f-claudemd start=2026-11-04 23:11:58 end=2026-11-04 23:12:08 elapsed=9s bound=600s status=OK rc=0` (79 passed)
- Comm set MEASURED at HEAD: 666 files (GREEN's 665 = the RED's 661 + the four RED files, + `tests/test_s81_g4_gate_rows.py`; no `.githooks` file, no precommit-hook file in the set) in 27 chunks of <= 25 (bound 1200; 22 chunks OK, the failing chunks 01 / 13 / 14 / 15 / 19 hold only baseline nodes) + `tests/test_secret_scan_static.py` alone (OK); 27,406 passed, 12 failed + 2 errors (the cold-tiktoken `tests/test_prompt_truth.py` pair), 56 skipped, 119 deselected (the four network-flaky nodes where present); vs the STORED base record `base_records/0b19de5b.../90b85603...txt` (REUSED under LC-6, as GREEN and the adversary did): HEAD failures 14, base failures 14, `comm -13` EMPTY, `comm -23` EMPTY; the 14 baseline nodes (test_auth_interceptor x2, test_page_scraping x2, test_personalization_bundle_c x2, test_prompt_truth x2, s10 r06, the five s16 r27 CRLF nodes) identical both sides; the five files absent from the record (the four G4 RED files + the gate rows) contribute no failure.
- Client fences (14, by path through the junction, jest 29.7.0, node v24.11.1): 13 / 14 suites, 236 / 240; the 4 failed nodes = exactly the `config/nativeBundle.w37` drift nodes d5, k2, k4, k5 (baseline).
- FULL jest suite ONCE (LC-7): `[jest] tag=g4final-full start=2026-11-04 23:39:45 end=2026-11-04 23:40:17 rc=1` (Test Suites: 1 failed, 3 skipped, 385 passed, 386 of 389 total; Tests: 4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total).
- ruff E9,F63,F7,F82 + py_compile clean on the 4 new modules, the 5 edited app files and the 6 G4 test files; json.loads on the two railway files and the golden.
- Corpus gate NOT run: `app/services/price_service.py` is not in the diff. Hook test files (`tests/test_precommit_hook*.py`) NOT run: the unit touches no `.githooks` file (RB-G4-3 (h)).
- Adversary (one, correctness lens with the second lens folded in, LC-1): SOUND, 0 blocking, 0 major; 42 / 42 ruled mutants KILLED + 11 adversary mutants (ADV-3 / ADV-7 now killed by G4-GR1 / G4-GR2; ADV-9 equivalent at this base); its minors are stated limits (LC-4). Reports: `specs/S81_G4_ADV1_correctness.md`, `specs/S81_G4_FIX1_REPORT.md`, `specs/S81_G4_GREEN_REPORT.md`, `specs/S81_G4_RED_REPORT.md`; the final-round [pyt] lines in `specs/S81_G4_FINAL_REPORT.md` (filed by the orchestrator).

## Stated limits (R-G4-12)
- S81-18-L1 inline RPC without `ENABLE_SYNC_DB_OFFLOAD`; L2 a miss pays up to the card-read bound before the base path; L3 a partial hit keeps the L2 reads of the legs it cannot serve; L4 D05 labels a KB price `stale / served_from_cache`; L5 the key's model is the configured verdict model; L6 no orphan drain of the bounded card task; L7 the full-hit spec set is measured for fragrances only; L8 the would-hit set is per process; L9 URL mode never KB-serves; L10 the KB price title is synthesized; L11 (R-G4-2) on the wire a KB price is told from a live scrape only by `as_of` and `metadata.kb_hit`.
- S81-19-L1 demand is a proxy (demand_count + last_seen); L2 web search inert; L3 the Shopify suggest JSON and same-host anchors only; L4 a lost owner-check race expires by TTL (no Lua); L5 no identity minted from a page; L6 rating / review_count only from the D08 rating; L7 `specs` -> `licence` wholesale; L8 a fetched hint is `closed`; L9 (R-G4-6) no `exhausted` state.
- D16-L1 with the flag OFF another method answers 405 and a malformed JSON body on POST answers 422 VALIDATION_ERROR before any dependency runs (FastAPI decodes the body first; no key check, no client, no handler), where an unregistered path answers 404; L2 no HTML page; L3 operator identities are `high`; L4 no kb_reviews from the operator path; L5 the coverage block is empty until D17 runs; L6 (R-G4-7) the partner source is trusted for the licence fields by the operator's own review; L7 a future `captured_at` is accepted (build_offer_row checks first_seen <= last_seen only) and S81-18's classify treats a negative age as FRESH, so an operator typo can shadow later genuine observations of that variant / merchant / market in the `kb_offers_latest` DISTINCT ON until the date passes (operator error only, dark admin-only flag; follow-up D16b refuses captured_at later than now plus a small skew and classify refuses age < 0).
- D17-L1 identity / pair hit rates are a search_logs proxy; L2 host counters only under `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH`; L3 no per-pair completeness; L4 medians over at most 100,000 paged rows; L5 `_paged` reads with range() and no ORDER BY, so a table above PAGE_SIZE (500) rows can skip or repeat rows across pages and the shares can be slightly off; L6 the host pipeline uses `exec()` only, so on the redis:// fallback client (redis-py `execute`) the host family is omitted with one WARNING. Follow-up D17b: order by the primary key; the exec / execute fallback as G3's live_robots does.

## Owner steps (names only; a dated ledger line per step)
1. Apply 045 then 047 (owner item 29).
2. `ENABLE_SYNC_DB_OFFLOAD` ON on `web` BEFORE `ENABLE_KB_FIRST_SERVE`.
3. The KB populated (G2 APPLY runs; `ENABLE_KB_INGEST` ON) before the KB-first canary; `ENABLE_VERDICT_CACHE_LOG` ON first for a week (log only).
4. Create the `kb-enrich` and `kb-coverage` Railway services from `railway.kbenrich.json` / `railway.kbcoverage.json` with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN` (the off-clock cap name `LLM_SPEND_CAP_OFFCLOCK_USD` stays unused until S81-21); one DRY run each, then `apply` (D17 before D16).
5. The ToS review on each blocked host the operator will capture, then `ENABLE_OPERATOR_INGEST` ON on `web`.
6. The interim `ENABLE_TIER_FILL_RESIDUAL_GUARD` flip after its own canary.
7. Canary items: the `metadata.kb_hit` rate per product, `stage_timings_ms` p50 / p95 on KB hits, the `[KB_SERVE]` WARNING rate, the `[VERDICT_CACHE] would_hit` rate, the `[KB_ENRICH] totals` per run (spend 0 until S81-21), the operator view's queue sizes, the coverage metrics.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
