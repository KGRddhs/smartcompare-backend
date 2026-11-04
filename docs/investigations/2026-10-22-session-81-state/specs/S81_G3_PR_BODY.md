# S81-G3 KB-INGEST: S81-17 KB-INGEST + D05 FIELD-STATUS, D14 LIVE-ROBOTS + attempt hooks

Base `744616e37d031923e522e30740b687de76482ee9` (origin/main) -> HEAD `eb10eab1251ce87aa005ca20a20435a95e1f8f62` (three commits: GREEN `efa33a81`, fix round 1 `32f9b76a`, the final-round docs commit `eb10eab1`; no replay, origin/main unchanged at 744616e3) on `feature/s81-g3-kb-ingest`. The third SAFE group under LC-9 (one spec, one RED, one GREEN, one adversary). Every flag is a NEW name, default OFF, read PER CALL at the hook (the `price_service.exact_gate_enabled` idiom); flag OFF is one env read and the base statements at every hook site. Spec `.qa-s80/S81-G3_UNIT_SPEC.md`, review `specs/RULINGS_S81_G3.md` (R-G3-1..18), RED gate `specs/GATE_S81_G3.md` (GC-1..GC-11), RED report `specs/S81_G3_RED_REPORT.md`, GREEN report `S81-G3_GREEN_REPORT.md`, adversary `specs/S81_G3_ADV1_correctness.md`, fix rulings `specs/RULINGS_FIX1_S81_G3.md`, fix report `S81-G3_FIX1_REPORT.md`, re-verifier `specs/S81_G3_REVERIFY_REPORT.md`, final-round rulings `specs/RULINGS_REBASE_S81_G3.md` (RB-G3-1..5), final report `REBASE_REPORT.md` (gate logs, the mutation table and the comm lists live there and in the GREEN folder, referenced by name).

## D14 LIVE-ROBOTS + attempt hooks (MYEZ D14)

- What: NEW `app/services/live_robots.py`. Flag `ENABLE_LIVE_ROBOTS_REGISTRY` ON: the curl wave (`curl_fetch_html`, `curl_fetch_html_same_site` initial + every hop), `shopify_pdp_service._fetch_once` (each hop, after the SSRF gate), the WooCommerce Store API (each GET), the Algolia storefront (merchant origin, harvest + explicit store) and URL mode (`extract_from_url` before `fetch_page`, which is byte-unchanged; `_fetch_page_v2` initial + every hop) ask `live_robots.gate` first. The verdict `url_verdict` is the G2 `url_gate` order over the PERSISTED S81-15 record (a per-process memo of `host,status,deny,robots,challenge`, live + blocked rows, single-flight off-loop refresh in a fresh Context, the MERCHANT_REGISTRY_* knobs reused); a skip returns each fetcher's existing miss value, counts `robots_skip` and logs one INFO line with the source, the normalized host and the reason. Fail-closed (a cold memo skips). URL mode V2: `STORE_UNREADABLE` with reason `robots_skip` (one additive `_V2_FETCH_OUTCOME_REASONS` entry). Every hooked fetcher that observes a response records ok / fail (challenge on `cf-mitigated: challenge`) under curl / curl_same_site / shopify / woo / algolia / url_extraction (GC-5) into a per-compare ContextVar bound in `_init_provider_attempts`; never in the response. Sub-flag `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH`: the bare `finally:` arm of the REST and stream compares hands ONE job (fire-and-forget, label `live_robots_health_flush`) to the S77 `redis-offloop` pool: ONE pipeline of `HINCRBY kbh:<UTC day>:<host> <source>:<outcome> <n>` + one `EXPIRE` per key (`LIVE_ROBOTS_HEALTH_TTL_DAYS`, 8, 1..30), one `exec` (or `execute` on a redis-py pipeline, F1-3); a raising client or pipeline is one WARNING with the exception type, and with no Redis client configured the flush is silent (spec 2.2 wins over its 2.5 line, D14-L11). `jsonld_widen.ROBOTS_ENTRY_LOOKUP` is wired at import (flag OFF it answers None). UA and `impersonate="chrome"` unchanged.
- RED nodes: `tests/test_s81_d14_live_robots.py` 77 RED (L1 x2, L2 x20, L2b x20, L3 x4, L4 x10, L5 x11, L6, L7, L8 x4, L9 x2, L10, L11) + 35 PIN (P1 x32, P2 x2, P3); golden `tests/fixtures/s81_d14_flag_off_golden.json`. Gate rows `tests/test_s81_g3_gate_rows.py::test_g3_gr2_every_hook_records_outcomes` (7 nodes, GC-5), `test_g3_gr3_no_projection_and_unbind_when_off` (part b: the live_robots seam driven twice on ONE context, the adversary's ADV-8 probe shape, not two full compares: bind, two records, flush, a repeated flush per cycle = exactly ONE pipeline + ONE exec per cycle, the unbind) and `test_g3_gr4_flush_uses_exec_or_execute` (2 nodes).
- Flip preconditions: 045 applied; the robots cron (owner item 25) covering 100 % of live hosts (owner item 33) and the M6 named-UA dry run; then the main flag in its own canary window; the health sub-flag after it.

## S81-17 KB-INGEST + D05 FIELD-STATUS (MYEZ S81-17, D05)

- What: NEW `app/services/kb_ingest.py` + `StructuredComparisonService._kb_ingest_tail`, called at the two success exits only (REST between the L3 moderation refusal block and the behaviour-profile block; stream after the refusal yields, before `settle_complete`; the camera path through the REST exit). Both flags are read first; both OFF returns. `ENABLE_FIELD_STATUS_METADATA` stamps the additive `metadata.field_status` (2-list, body order, the closed 2.2 vocabulary; the S81-11 D20 contract). `ENABLE_KB_INGEST` runs `_fire_and_forget(asyncio.to_thread(kb_ingest.run_job, snap), "kb_ingest")`, never awaited. The job (worker thread; no LLM, no Serper, no fetch, no request-context read) writes through the S81-14 builders with the service-role client, insert-ignore: kb_products / kb_variants at identity high (fragrance products), kb_offers for a genuine method with an evidence rung (converted_usd / estimates / render tiers refused, plus the builder belt, GC-7) on a live registry host whose persisted verdict allows the URL, market BH, one shared captured_at = first_seen = last_seen, the re-observation update of `KB_OFFER_UPSERT_SET` matched through Decimal (GC-6); kb_images (D08 image policy + allow verdict); kb_reviews (channel-1 JSON-LD only); kb_gaps for unknown D05 fields at identity high or medium (insert-ignore, one select, one compare-and-set per existing row, `gap_cas_lost` counted, never retried; `needs_operator` on a blocked host; never `pdp_`; at most `KB_INGEST_GAP_MAX`, 16, 1..64). No kb_specs, no kb_feedback. ONE INFO line per job, ints only, with `elapsed_ms` (R-G3-7).
- RED nodes: `tests/test_s81_s17_kb_ingest.py` 63 RED (S1 x2, S2, S3 x12, S4 x2, S5, S6 x4, S7 x2, S8 x2, S9 x2, S10, S11 x4, S12 x11, S13, S14 x4, S15 x2, S16, S17 x6, S18, S19, S20, S21 x3) + 11 PIN (P1 x8, P2 x3); golden `tests/fixtures/s81_s17_flag_off_golden.json`. Gate rows `test_g3_gr1_offer_reobservation_amount_normalised` (3 nodes, GC-6) and `test_g3_gr3_no_projection_and_unbind_when_off` (2 nodes, REST + stream; part a: both flags OFF = zero calls of build_job / _now / assess_result and no WARNING).
- Flip preconditions: 045 then 047 applied; `ENABLE_SYNC_DB_OFFLOAD` ON before `ENABLE_KB_INGEST`; the robots cron has run (no record = no offer); `ENABLE_FIELD_STATUS_METADATA` with the S81-11 OTA after approval.

## Deliberate pin changes (spec 4.1; no other pin moved)

| id | file | change | reason |
|---|---|---|---|
| E1 | `tests/test_s81_kb_schema.py` | P01_ALLOWED + `("app/services/kb_ingest.py", "from app.services import kb_service as _kb")`; P01_FUNCTIONS + `"app/services/kb_ingest.py": "kb_leaf"` | the live writer calls the S81-14 builders through the ONE function-local import (the G2 E1 precedent) |
| E2 | `tests/test_s81_kb_schema.py` | P02_ALLOWED + the six `KB_*_TABLE = "kb_*"` lines (products, variants, offers, images, reviews, gaps) keyed to `app/services/kb_ingest.py` | the table names defined once, one per line (the G2 E2 precedent) |

## Fix round 1 (RULINGS_FIX1_S81_G3; the adversary NOT_READY: 0 blocking, 2 major, 7 minor)

- M-1: `app/services/price_service.py` :51 lost one space in the `ENABLE_PAGE_SCRAPE` line outside every spec hunk; the base bytes are restored (CRLF kept): `git diff 744616e3 -- app/services/price_service.py` now holds only the import beside :46 and the two curl hooks (18 insertions, 0 deletions).
- M-2 + m-3: the new row G3-GR3 pins the no-projection half of spec 2.6 / R-G3-10 (both flags OFF under the full configuration: zero build_job / _now / assess_result calls at the REST and stream success exits; a raising build_job logs nothing) and the unbind in `flush_attempts`; mutants S17-M3 (the early return removed) and ADV-8 (the unbind dropped) KILLED on byte copies, restored and sha-verified.
- m-1: `_flush_sync` calls `exec` when the pipeline has it, else `execute` (the redis-py fallback of cache_service's redis:// path); G3-GR4 pins both shapes; mutant G3-GRM4 (the fallback dropped) KILLED.
- m-2, m-4, m-6: stated limits D14-L10, S81-17-L10, D14-L11 below. m-5: CONFIRMED (cards and gaps for category fragrances only; the CLAUDE.md S81-17 row already says it, no edit). m-7: every gate re-ran at the fix HEAD and again at the final HEAD (below); ruff B905 (zip without strict= at kb_ingest.py:278) is report-only and left.

## Re-verifier (fix round 1) and the final round

- Re-verifier verdict (`specs/S81_G3_REVERIFY_REPORT.md`, correctness lens on the fix bytes `32f9b76a`): SOUND, 0 blocking, 0 major, 5 minor. Mutants S17-M3, ADV-8, G3-GRM4, RV-1, RV-2, RV-4, RV-5, RV-6 KILLED; RV-7 detected by the numstat gate; RV-3 survives as equivalent (stated limit D14-L12). Its minors are stated limits or wording (LC-4): mi-1 = D14-L12; mi-2 = the G3-GR3 part (b) wording, corrected in the docs commit (the live_robots seam driven twice on ONE context, the ADV-8 probe shape, not two full compares) and in this body; mi-3 = the CLAUDE.md S81-G3 block now names G3-GR1..G3-GR4 and its D14 Redis sentence reads exec (upstash-redis) or execute (redis-py), a client None = a silent flush, a raising pipeline = one WARNING; mi-4 = the GREEN-run kills named below; mi-5 = the hook-files measurement note under Stated limits.
- Final round (RULINGS_REBASE_S81_G3 RB-G3-1..5): `git fetch origin main` + `git rebase origin/main` reported up to date (origin/main 744616e3, zero commits replayed, no conflict). ONE docs commit through the hook (test docstring + CLAUDE.md only, no assertion moved, no pin row). The four frozen RED files byte-identical first and last (GC-1 hashes); the gate-rows file changes by docstring lines only (sha256 at HEAD 86dfe368...).

## Counts and gates (every pytest through pyt.py, one at a time; final HEAD `eb10eab1` unless named)

- RED files + gate rows + `tests/test_s81_kb_schema.py`: 729 passed OFF and 729 passed with the four flags exported in ONE runner call (186 RED-file nodes + 14 gate rows + 529 kb_schema).
- CI-order set (spec 12.2, GC-4): the existing members OFF 1757 passed / 1 failed (the base box node `test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content`); the three G3 files 200 passed OFF and 200 passed ON (1957 passed in all, as at the fix HEAD).
- Corpus gate at `eb10eab1` (the four flags forced OFF; 17:53:51-18:01:06, rc=0): `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656`, `OVERALL SHA256 601338261705718a85c8c4ff281cefd47368a8c7aa1b12c2aad501baae18a1ef` = base (also equal at the fix HEAD `32f9b76a`).
- Mutants: G3-GRM1 (Decimal normalisation dropped) and G3-GRM2 (algolia / url_extraction recording dropped) KILLED at GREEN `efa33a81`; S17-M3, ADV-8 (G3-GR3) and G3-GRM4 (G3-GR4) KILLED at the fix HEAD `32f9b76a` by the fix round and again by the re-verifier; the 24 + 2 spec / RED mutants are the adversary's re-application. The final round adds no row and no mutant (RB-G3-5).
- Comm set at `eb10eab1` (LC-6: the STORED base record at 744616e3 REUSED, set sha256 ba26af35..., 14 ids; no base re-run): the RED's 609 files + the three G3 test files = 612 files, measured in 25 chunks of at most 25 files (bound 1200; 611 files) + `tests/test_secret_scan_static.py` alone; 26,236 passed, 12 failed + 2 errors = 14 FAILED / ERROR ids at HEAD, identical to the 14 baseline ids (test_auth_interceptor x2, test_page_scraping x2, test_personalization_bundle_c x2, test_prompt_truth x2 cold tiktoken, s10 r06, the five s16 r27 CRLF nodes); `comm -13` branch-only-NEW: EMPTY. No TIMEOUT, no re-run. The CLAUDE.md readers (`test_ci_gates.py`, `test_behavior_dimension_translation.py`), the R8 pair and `test_paid_route_metering.py` are members and green.
- Client fences (the fourteen backend-scanning suites by path through the junction, jest 29.7.0, node v24.11.1, at `eb10eab1`): 13 / 14 PASS; nativeBundle.w37 FAIL with exactly the 4 known drift nodes (d5, k2, k4, k5); Tests 4 failed / 236 passed.
- FULL jest suite once (LC-7) at `eb10eab1`: Test Suites 1 failed, 3 skipped, 385 passed (389); Tests 4 failed, 13 skipped, 13 todo, 3794 passed (3824); Snapshots 42 passed; the 4 failures are exactly the nativeBundle.w37 drift nodes; no -u, no .snap.
- Hook test files: NOT run in the final round (no `.githooks` file in the diff; RB-G3-3 (h)); see the mi-5 note.
- Lint: ruff E9,F63,F7,F82 + py_compile on the eight app files and the four test files: clean; json.loads on the two goldens: OK. `git diff --check` clean; `git status --short` empty.
- Footprint: 15 files (14 of spec 12.3 + the gate-rows file, GC-10); `git diff 744616e3 -- app/services/price_service.py` = 18 insertions, 0 deletions (the spec hunks only); no migration, requirements, .github, .githooks, app/legal, landing or SmartCompareApp file.

## Stated limits

- D14-L1 the UA stays Chrome under the flag while the verdict is judged as the named agent AND `*`; D14-L2 another origin of a registry host (www / apex, http / https, a subdomain without its own record) is skipped until the cron reads that origin; D14-L3 a cold or long-failing memo skips every gated fetch (the first compare after a deploy may skip); D14-L4 URL mode fails closed for any host without an allow record (R-G3-2); D14-L5 counters of attempts finishing after the compare's `finally` are dropped, off-compare callers are gated but uncounted; D14-L6 the Redis counters are not folded into the merchant health column (D14b) and expire after the TTL; D14-L7 the Algolia DSN API host is not robots-checked (the merchant origin decides); D14-L8 the first flush builds the `redis-offloop` pool, so `/health` shows `redis_offloop_pool` even with `ENABLE_PRICE_PATH_REDIS_OFFLOOP` unset; D14-L9 the Magento GraphQL, Salla, OCC, rest_json, noon and unbxd adapters and the render tiers stay ungated (D14c), so the flag does not yet cover them; D14-L10 the redirect target of `curl_fetch_html` (allow_redirects=True) and of the Algolia landing GET is fetched without a verdict and its outcome is attributed to the initial host (the hop-gated fetchers are same_site, Shopify and URL-mode V2; the final-URL verdict is D14b's); D14-L11 with no Redis client configured the health flush is silent (no WARNING): no Redis is a deployment state, not an error.
- D14-L12 (re-verifier mi-1) the position of the unbind in `flush_attempts` relative to its empty-bucket / health-OFF early return is unpinned (RV-3 survives); it is equivalent in production because `bind_attempts` re-binds at each compare start and nothing records after the compare's `finally`.
- Measurement note (re-verifier mi-5) the four pre-commit hook test files together hit the runner's 1800 s TIMEOUT in the fix round and the two round-2 files then passed 151 / 151 alone (`test_precommit_hook_phase_b.py` not fully measured); no `.githooks` file is in the diff, every commit passed the hook, and the final round does not run them (RB-G3-3 (h)).
- S81-17-L1 identity confidence is a PAIR value; S81-17-L2 no kb_specs from the live path (S81-17c); S81-17-L3 CAS increments without retry lose concurrent increments (counted `gap_cas_lost`; S81-17b); S81-17-L4 up to about 23 PostgREST round trips per job on one default-executor thread (S81-17b RPC after the canary); S81-17-L5 kb_reviews / kb_images rows are first-observation-wins; S81-17-L6 a `stale` price carries no as_of; S81-17-L7 a gap row's state is set at insert only; S81-17-L8 market BH only; S81-17-L9 at identity medium a gap row can carry the pair's less certain identity; S81-17-L10 the sync `load_records_sync` path has no single flight, so concurrent ingest jobs at a memo-window edge each run the paged read, bounded by the executor width.
- GREEN additions (cards and gaps for fragrances CONFIRMED, F1-5): the job writes cards and gaps only for products whose category is `fragrances` (KB_CATEGORY; `kb_product_id` alone would also mint an id for a non-fragrance name); a WooCommerce or curl response that raises after a recorded outcome can count one ok and one fail for the same attempt.

## Owner steps (names only; a dated ledger line each)

1. Apply 045 then 047 (owner item 29).
2. `ENABLE_SYNC_DB_OFFLOAD` ON on `web` with its canary, BEFORE `ENABLE_KB_INGEST`.
3. The robots cron (owner item 25) has run; flip `ENABLE_KB_INGEST` on `web` in a canary window.
4. The robots cron at 100 % of live hosts (owner item 33) and the M6 named-UA dry run; then `ENABLE_LIVE_ROBOTS_REGISTRY` on `web` in its own canary window; then `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH`.
5. `ENABLE_FIELD_STATUS_METADATA` with the S81-11 OTA, after approval.

Canary items: the `kb_ingest` WARNING rate; the `[KB_INGEST] job` counts and `elapsed_ms`; kb_gaps growth; `[LIVE_ROBOTS] skip` lines per host (the `source=url_extraction` hosts are registry candidates); /health loop lag and `redis_offloop_pool`; the genuine-price share.

## Final-round [pyt] / [jest] lines (HEAD `eb10eab1`)

```
[pyt] tag=g3final-unit-off start=2026-11-04 17:51:13 end=2026-11-04 17:51:33 elapsed=20s bound=600s status=OK rc=0   (729 passed)
[pyt] tag=g3final-unit-on start=2026-11-04 17:51:34 end=2026-11-04 17:51:54 elapsed=20s bound=600s status=OK rc=0   (729 passed; the four flags exported in ONE runner call)
[pyt] tag=g3final-ci-off start=2026-11-04 17:52:07 end=2026-11-04 17:52:42 elapsed=36s bound=1200s status=FAIL rc=1   (1757 passed / 1 failed = s10 r06)
[pyt] tag=g3final-ci-g3-off start=2026-11-04 17:52:43 end=2026-11-04 17:52:59 elapsed=15s bound=1200s status=OK rc=0   (200 passed)
[pyt] tag=g3final-ci-g3-on start=2026-11-04 17:53:00 end=2026-11-04 17:53:15 elapsed=15s bound=1200s status=OK rc=0   (200 passed)
[pyt] tag=g3final-comm-00 start=2026-11-04 18:01:29 end=2026-11-04 18:02:02 elapsed=33s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-01 start=2026-11-04 18:02:02 end=2026-11-04 18:02:27 elapsed=24s bound=1200s status=FAIL rc=1
[pyt] tag=g3final-comm-02 start=2026-11-04 18:02:27 end=2026-11-04 18:03:34 elapsed=67s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-03 start=2026-11-04 18:03:34 end=2026-11-04 18:04:10 elapsed=36s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-04 start=2026-11-04 18:04:11 end=2026-11-04 18:04:26 elapsed=15s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-05 start=2026-11-04 18:04:27 end=2026-11-04 18:04:46 elapsed=18s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-06 start=2026-11-04 18:04:46 end=2026-11-04 18:06:57 elapsed=131s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-07 start=2026-11-04 18:06:57 end=2026-11-04 18:08:06 elapsed=69s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-08 start=2026-11-04 18:08:07 end=2026-11-04 18:08:38 elapsed=32s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-09 start=2026-11-04 18:08:39 end=2026-11-04 18:09:03 elapsed=24s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-10 start=2026-11-04 18:09:03 end=2026-11-04 18:09:15 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-11 start=2026-11-04 18:09:15 end=2026-11-04 18:09:42 elapsed=26s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-12 start=2026-11-04 18:09:42 end=2026-11-04 18:10:09 elapsed=27s bound=1200s status=FAIL rc=1
[pyt] tag=g3final-comm-13 start=2026-11-04 18:10:10 end=2026-11-04 18:10:41 elapsed=31s bound=1200s status=FAIL rc=1
[pyt] tag=g3final-comm-14 start=2026-11-04 18:10:41 end=2026-11-04 18:11:03 elapsed=22s bound=1200s status=FAIL rc=1
[pyt] tag=g3final-comm-15 start=2026-11-04 18:11:04 end=2026-11-04 18:13:28 elapsed=145s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-16 start=2026-11-04 18:13:29 end=2026-11-04 18:14:58 elapsed=89s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-17 start=2026-11-04 18:14:59 end=2026-11-04 18:16:27 elapsed=88s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-18 start=2026-11-04 18:16:27 end=2026-11-04 18:17:28 elapsed=60s bound=1200s status=FAIL rc=1
[pyt] tag=g3final-comm-19 start=2026-11-04 18:17:29 end=2026-11-04 18:18:32 elapsed=63s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-20 start=2026-11-04 18:18:32 end=2026-11-04 18:18:51 elapsed=19s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-21 start=2026-11-04 18:18:52 end=2026-11-04 18:19:52 elapsed=60s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-22 start=2026-11-04 18:19:53 end=2026-11-04 18:20:40 elapsed=47s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-23 start=2026-11-04 18:20:40 end=2026-11-04 18:21:10 elapsed=30s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-24 start=2026-11-04 18:21:10 end=2026-11-04 18:21:25 elapsed=15s bound=1200s status=OK rc=0
[pyt] tag=g3final-comm-secret start=2026-11-04 18:21:27 end=2026-11-04 18:21:45 elapsed=18s bound=1200s status=OK rc=0
[jest] tag=g3final-fences start=17:55:26 end=17:55:36 rc=1
[jest] tag=g3final-full start=2026-11-04 17:55:52 end=2026-11-04 17:56:17 rc=1
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
