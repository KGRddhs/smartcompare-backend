# S81-G4 KB-SERVE: S81-18 KB-FIRST-SERVE + S81-19 GAP-QUEUE + D16 OPERATOR-INGEST + D17 MEASURE-COVERAGE

Base `0b19de5bcc1416111d48bc725359b95151a658ca` (origin/main, #384 G3). HEAD: `NOT COMMITTED (pre-commit gitleaks refusal, see the GREEN report)`. Branch `feature/s81-g4-kb-serve`.
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
- RED nodes: `tests/test_s81_d16_operator_ingest.py` R1-R11 (11 nodes) + PIN P1-P3 (7 nodes; P2 the OpenAPI path-set sha).
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
No other pin moved.

## Counts and gates
- The four RED files + `tests/test_s81_kb_schema.py`, flags OFF: `[pyt] tag=g4g-red-off2 start=2026-11-04 21:57:01 end=2026-11-04 21:57:14 elapsed=13s bound=600s status=OK rc=0 (673 passed incl. tests/test_legal_disclosure_s77.py; [netguard] blocked 0)`
- Same, the seven flags exported in ONE runner call (the two modes as DRY): `[pyt] tag=g4g-red-on2 start=2026-11-04 21:56:47 end=2026-11-04 21:56:59 elapsed=12s bound=600s status=OK rc=0 (673 passed; [netguard] blocked 0)`
- CI-order set (spec 12.2, 15 files) OFF: `[pyt] tag=g4g-ciorder-off start=2026-11-04 21:28:34 end=2026-11-04 21:29:27 elapsed=53s bound=1200s status=FAIL rc=1 (5 failed, 1535 passed; [netguard] blocked 28 attempts from 10 nodes, the base figure)` (5 failures = the five environmental `test_s16_r27_hygiene_of_g2_files` CRLF nodes, baseline both sides)
- Comm set: 665 files (the RED's 661 + the four RED files, re-derived by the union rule at HEAD: 0 other additions) in 27 chunks of <= 25 + `tests/test_secret_scan_static.py` alone, vs the STORED base record `base_records/0b19de5b.../90b85603...txt` (REUSED, LC-6). HEAD failures 14, base failures 14, branch-only-NEW (`comm -13`) = 0 (EMPTY); fixed vs base = 0.
- The first HEAD pass found ONE branch-only node, `tests/test_legal_disclosure_s77.py::test_s77_d9_bot_page_claim_matches_the_runtime` (a docstring of `scripts/cron_kb_enrich.py` named the robots agent, so the emitter pin counted the file); the docstring was reworded (no code change) and chunk 09 + `tests/test_s81_kb_schema.py` + `tests/test_s81_s16_kb_seed.py` re-ran: `[pyt] tag=g4g-comm-09b start=2026-11-04 21:55:44 end=2026-11-04 21:56:28 elapsed=44s bound=1200s status=FAIL rc=1` (5 failed = the r27 baseline, 1176 passed); the comm -13 is then EMPTY.
- Client fences (14, by path through the junction, jest 29.7.0, node v24.11.1): 13 / 14 suites; 4 failed nodes = exactly the four `config/nativeBundle.w37` drift nodes (baseline).
- ruff E9,F63,F7,F82 + py_compile clean on the 4 new modules, the 5 edited app files and the test file; json.loads on the two railway files and the golden; new files pure ASCII + LF; edited files CRLF kept (`git diff --stat` hunks only).
- Corpus gate NOT run: `app/services/price_service.py` is not in the diff. Hook test files NOT run (no `.githooks` change). FULL jest NOT run (LC-7: the last round before the PR).
- Per-chunk [pyt] lines, the mutation table (42 / 42 KILLED at the RED prototype) and the gate logs: `specs/S81_G4_GREEN_GATE_LOGS.md` / `specs/S81_G4_RED_REPORT.md` (filed by the orchestrator).

## Stated limits (R-G4-12)
- S81-18-L1 inline RPC without `ENABLE_SYNC_DB_OFFLOAD`; L2 a miss pays up to the card-read bound before the base path; L3 a partial hit keeps the L2 reads of the legs it cannot serve; L4 D05 labels a KB price `stale / served_from_cache`; L5 the key's model is the configured verdict model; L6 no orphan drain of the bounded card task; L7 the full-hit spec set is measured for fragrances only; L8 the would-hit set is per process; L9 URL mode never KB-serves; L10 the KB price title is synthesized; L11 (R-G4-2) on the wire a KB price is told from a live scrape only by `as_of` and `metadata.kb_hit`.
- S81-19-L1 demand is a proxy (demand_count + last_seen); L2 web search inert; L3 the Shopify suggest JSON and same-host anchors only; L4 a lost owner-check race expires by TTL (no Lua); L5 no identity minted from a page; L6 rating / review_count only from the D08 rating; L7 `specs` -> `licence` wholesale; L8 a fetched hint is `closed`; L9 (R-G4-6) no `exhausted` state.
- D16-L1 another method answers 405 with the flag OFF; L2 no HTML page; L3 operator identities are `high`; L4 no kb_reviews from the operator path; L5 the coverage block is empty until D17 runs; L6 (R-G4-7) the partner source is trusted for the licence fields by the operator's own review.
- D17-L1 identity / pair hit rates are a search_logs proxy; L2 host counters only under `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH`; L3 no per-pair completeness; L4 medians over at most 100,000 paged rows.

## Owner steps (names only; a dated ledger line per step)
1. Apply 045 then 047 (owner item 29).
2. `ENABLE_SYNC_DB_OFFLOAD` ON on `web` BEFORE `ENABLE_KB_FIRST_SERVE`.
3. The KB populated (G2 APPLY runs; `ENABLE_KB_INGEST` ON) before the KB-first canary; `ENABLE_VERDICT_CACHE_LOG` ON first for a week (log only).
4. Create the `kb-enrich` and `kb-coverage` Railway services from `railway.kbenrich.json` / `railway.kbcoverage.json` with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN` (the off-clock cap name `LLM_SPEND_CAP_OFFCLOCK_USD` stays unused until S81-21); one DRY run each, then `apply` (D17 before D16).
5. The ToS review on each blocked host the operator will capture, then `ENABLE_OPERATOR_INGEST` ON on `web`.
6. The interim `ENABLE_TIER_FILL_RESIDUAL_GUARD` flip after its own canary.
7. Canary items: the `metadata.kb_hit` rate per product, `stage_timings_ms` p50 / p95 on KB hits, the `[KB_SERVE]` WARNING rate, the `[VERDICT_CACHE] would_hit` rate, the `[KB_ENRICH] totals` per run (spend 0 until S81-21), the operator view's queue sizes, the coverage metrics.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
