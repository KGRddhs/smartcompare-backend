# S81-G4 KB-SERVE group spec (measured): S81-18 KB-FIRST-SERVE (+ the verdict-cache key log) + S81-19 GAP-QUEUE (the enrich worker + the price refresh) + D16 OPERATOR-INGEST + D17 MEASURE-COVERAGE

- Group: S81-G4 KB-SERVE, the fourth SAFE group under LC-9 (s81-common.txt OWNER RULING 2026-10-29). ONE branch `feature/s81-g4-kb-serve`, ONE spec (this file), the orchestrator's spec review (LC-8), ONE RED round writing the four RED files, ONE GREEN, ONE adversary (correctness lens with the engineering checks of 12.6 folded in), ONE rebase, ONE PR.
- Units: S81-18 KB-FIRST-SERVE + the verdict-cache key log (lane A; PLAN_S81 :161); S81-19 GAP-QUEUE enrich worker + price refresh (lane data; PLAN_S81 :162, the worker half); D16 OPERATOR-INGEST (lane B; PLAN_S81 :162, the operator half); D17 MEASURE-COVERAGE (lane data; PLAN_S81 :163).
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-g4`, detached at base `0b19de5bcc1416111d48bc725359b95151a658ca` (`git rev-parse HEAD`), `git status --short` empty at the start and after every probe (this file sits under the gitignored `.qa-s80/`).
- Evidence: PLAN_S81.md (:161-:163, the M4 / M5 unit text; owner decisions 7 / 11), S81_G4_BRIEF.md (Q1-Q10 and classification rules a-d), PLAN_S80 section 0 (frozen build-3 contract: additive keys only, never a bare 503, `overview.products[i].image_url` an absolute https raster URL or null) and `runs/research/contract_freeze.json` (keys: category, summary, findings, recommendations, open_questions, sources; finding 1 = the client-read paths, none removed or retyped here), R-A1 / R-A4 / R-A5 / R-A13 / R-A15, RULINGS_S81_G3 (R-G3-1..18; the `kbh:` Redis class ruled SAFE there), the G2 contracts R-G2-13 (the `pdp_` hint rows) / R-G2-14 (D11 checks robots only; S81-19 applies ToS + robots), the S81-14 builders.
- Personal-data rule: no real names, emails, phone numbers, device ids or account ids in this file or in anything the group writes; synthetic hosts only (`store-a.example.com`, `store-b.example.com`), synthetic identities built at run time; the admin key in tests built at run time (`secrets.token_hex(32)`), never a literal. No secret value; variable NAMES only. Production flag state: the newest dated ledger line (2026-11-04 19:08, "G4 KB-SERVE GROUP SPEC LAUNCHED") names none of the group's flags; every flag here is a NEW name, so unset in production by construction (R-A15).
- Measurement location: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/g4spec/` (`base_pins.log`, `comm.py`, `comm_set.txt`, `new_vs_g3.txt`, `recompute.txt`). Nothing in the worktree was written except this file. Every file:line below was read at 0b19de5b in this run.
- Base run (bounded runner, flags unset): `tests/test_s81_kb_schema.py tests/test_s81_s17_kb_ingest.py tests/test_s81_d14_live_robots.py tests/test_s75_fanout_identity.py tests/test_s81_s15_registry_robots.py tests/test_admin_key_and_sentry_scrub.py tests/test_s81_d11_pdp_discovery.py tests/test_s81_s16_kb_seed.py tests/test_s81_d09_feed_walker.py tests/test_flush_live_price_key.py tests/test_s81_s04_spend_breaker.py` -> 5 failed, 1609 passed, 13 warnings. `[pyt] tag=g4spec-base-pins start=2026-11-04 19:22:52 end=2026-11-04 19:23:54 elapsed=61s bound=600s status=FAIL rc=1`; `[hermeticity] sentinel checked 1614 test(s)`; `[netguard] blocked 52 attempt(s) from 12 node(s)` (all in `test_s81_s04_spend_breaker.py`, the `supabase.invalid:443` sentinel, pre-existing). The 5 failures are `tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common|seed_kb_batch|seed_kb_brands_wikidata|cron_feed_walker|cron_pdp_discovery]` = `assert b"\r" not in raw` (`tests/test_s81_s16_kb_seed.py:1097`): ENVIRONMENTAL (the working copy is CRLF under core.autocrlf=true; CI checks out LF and is green); recorded identically at base and HEAD; the new G4 scripts are written LF on disk (2.x of S81-19 / D17) so a G4 copy of that hygiene row passes on this box.
- Corpus gate (brief rule d): NOT RUN. No unit edits `app/services/price_service.py` (S81-19 CALLS `price_service.extract_price_from_html` :13952 from a script; nothing in it moves). If GREEN's diff ever touches price_service, GREEN runs `scripts/verify_flag_byte_identity.py` at base and HEAD with the four request-path flags and the OVERALL SHA256 lines must be equal.
- NOT MEASURED in this run: the 661-file comm-set base record (12.1 gives the derivation, the list, its sha and the LC-6 reuse split); the fourteen client fences (no literal they read moves, 7.3 of S81-18); the flag-OFF 404 identity of the D16 routes against an unregistered path (designed in D16 2.4, measured by the RED PIN row D16-P1 at base).

## 0. The group

### 0.1 Branch, units, flags

| unit | flag (new name, default OFF, read PER CALL, the FIRST statement of its predicate) | reader | idiom | lane |
|---|---|---|---|---|
| S81-18 | `ENABLE_KB_FIRST_SERVE` (the one gathered `kb_product_card` read, the KB-served legs, the `X-Client-Capabilities` read, `metadata.kb_hit`) | NEW `app/services/kb_serve.py::kb_first_serve_enabled` | house boolean | A |
| S81-18 | `ENABLE_VERDICT_CACHE_LOG` (independent: the key + ONE INFO line per eligible compare; nothing stored) | `kb_serve.verdict_cache_log_enabled` | house boolean | A |
| S81-19 | `ENABLE_KB_ENRICH_WORKER` (the worker run: off / dry / apply) | NEW `scripts/cron_kb_enrich.py::enrich_mode` -> `kb_seed_common.run_mode` | G2 mode (true = DRY, apply = WRITE) | data |
| S81-19 | `ENABLE_KB_GAP_FILL` (the gap-ladder leg inside a run; follows the parent mode; OFF = price refresh only) | `cron_kb_enrich.gap_fill_enabled` -> `kb_seed_common.house_flag` | house boolean | data |
| S81-19 | `ENABLE_KB_GAP_WEB_SEARCH` (INERT sub-flag of ladder step 3: ON logs `step=web_search status=not_built` once per run and skips; never a provider call) | `cron_kb_enrich.web_search_requested` -> `house_flag` | house boolean | data |
| D16 | `ENABLE_OPERATOR_INGEST` (the two admin JSON routes; OFF = the unregistered-path 404) | NEW `app/services/kb_operator.py::operator_ingest_enabled` | house boolean | B |
| D17 | `ENABLE_KB_COVERAGE_ROLLUP` (the daily rollup run: off / dry / apply) | NEW `scripts/cron_kb_coverage.py::coverage_mode` -> `run_mode` | G2 mode | data |

House boolean = `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")` (the `price_service.exact_gate_enabled` per-call idiom; `kb_ingest.kb_ingest_enabled` :81-83 is the in-group copy). G2 mode = `kb_seed_common.run_mode` :67-79 (`apply` writes, the truthy set is DRY, everything else OFF) and `cli_mode` :82 (`--dry-run` downgrades apply). Knobs (all parse defensively through `kb_seed_common.int_knob` / `float_knob` :110 / :120 shapes; in app/ modules a local copy of the same rule: unset / blank / garbage / inf / nan / <= 0 -> default, else clamped): S81-18 `KB_FIRST_SERVE_TIMEOUT_SECONDS` (1.0, 0.2..3.0), `KB_FIRST_SERVE_MAX_ASOF_DAYS` (30, 8..90), `VERDICT_CACHE_LOG_MAX_KEYS` (10000, 100..100000); S81-19 `KB_ENRICH_MAX_GAPS` (200, 1..2000), `KB_ENRICH_HOSTS_PER_GAP` (3, 1..10), `KB_ENRICH_HEAD_N` (50, 1..1000), `KB_ENRICH_TAIL_MAX` (500, 1..5000), `KB_ENRICH_TAIL_WEEKDAY` (7 = Sunday ISO, 1..7), `KB_ENRICH_DEMAND_DAYS` (7, 1..30), `KB_ENRICH_FETCH_TIMEOUT_SECONDS` (4.0, 1.0..4.0), `KB_ENRICH_LOCK_SECONDS` (900, 60..3600); D16 `KB_OPERATOR_PAGE_MAX` (50, 1..200); D17 `KB_COVERAGE_MAX_HOSTS` (500, 1..5000). The off-clock spend cap is the EXISTING breaker knob `LLM_SPEND_CAP_OFFCLOCK_USD` (`llm_spend_breaker.py:122`): no new spend knob.

Flip preconditions (stated, never built): 045 applied (owner item 29) before ANY G4 flag; `ENABLE_SYNC_DB_OFFLOAD` ON on `web` before `ENABLE_KB_FIRST_SERVE` (the RPC goes through `run_db`, inline on the loop when the offload is OFF, `app/utils/db_offload.py:29-35`); the KB populated (G2 APPLY runs, G3 `ENABLE_KB_INGEST` ON) and a hit-rate canary read (`metadata.kb_hit` counts) before the KB-first canary; the enrich and coverage Railway services created by the owner from `railway.kbenrich.json` / `railway.kbcoverage.json`; D17 before D16 (the view shows D17's latest day).

### 0.2 Change list per unit (detail in each unit's section 3)
- S81-18: NEW `app/services/kb_serve.py`; EDIT `app/services/structured_comparison_service.py` (one import line; H0 x2; H1-H6 inside `_fetch_product_data`; H7 inside `_stamp_unit_metadata`; H8 x2 at the verdict calls; the `kb_price_asof` keyword on `compare_from_text` / `_compare_from_text_impl` / `compare_from_text_streaming`); EDIT `app/api/text_routes.py` (four call sites :661 / :882 / :1145 / :1470) and `app/api/image_routes.py` (:560): the capability keyword, house `**({...} if ... else {})` form; EDIT `app/services/kb_ingest.py` (two lines: the KB-served price is never re-observed); NEW `tests/test_s81_s18_kb_first_serve.py` + `tests/fixtures/s81_s18_flag_off_golden.json`.
- S81-19: NEW `scripts/cron_kb_enrich.py`, NEW `railway.kbenrich.json`, NEW `tests/test_s81_s19_gap_queue.py`. No app/ module (2.1 of S81-19 says why).
- D16: NEW `app/services/kb_operator.py`; EDIT `app/api/admin_routes.py` (two routes, one import); NEW `docs/runbooks/2026-11-kb-operator-ingest.md` (the bookmarklet and the curl template, names only); NEW `tests/test_s81_d16_operator_ingest.py`.
- D17: NEW `scripts/cron_kb_coverage.py`, NEW `railway.kbcoverage.json`, NEW `tests/test_s81_d17_coverage.py`.
- Shared: `tests/test_s81_kb_schema.py` (E1 / E2: P01 / P02 widened for kb_serve, kb_operator and cron_kb_coverage, exact lines), `CLAUDE.md` (one G4 block, four rows, after the S81-G3 block at :553-556).

### 0.3 Shared files and the order GREEN applies them
| file | units | order |
|---|---|---|
| `tests/test_s81_kb_schema.py` | S81-18 (E1 kb_serve P01 + E2 one P02 line), D16 (E1 kb_operator P01 + E2 two P02 lines), D17 (E2 two P02 lines) | ONE edit after all four code changes |
| `CLAUDE.md` | all four | LAST, one block |
| `scripts/kb_seed_common.py` | S81-19, D17 (read-only reuse) | never edited |
| `app/services/kb_ingest.py` | S81-18 (edit), S81-19 / D16 (read-only reuse of `rung_for`, the table constants, `_insert_ignore`) | S81-18 edits it; the others only import |
GREEN order: D17 -> S81-19 -> D16 -> S81-18 (scripts first, the live compare path last, so a red RED row of the live path is never masked by an unfinished script), then the E-rows, then CLAUDE.md.

### 0.4 Known rebases, dependencies, defect-ledger rows (drafted, names only)
- S81-16b (lane B, FOCUS, in flight: migration 051 kb_brands, `kb_service.build_brand_row`, an E-row on the G2 row R23) edits `app/services/kb_service.py` and may widen `tests/test_s81_kb_schema.py` P01 / P02: a textual rebase collision on the P01_ALLOWED / P02_ALLOWED sets only (both sides ADD lines). G4 never touches kb_brands nor kb_service.py.
- S81-12 (draft PR #378, HELD) and S81-08 (client) do not touch G4 files (measured by name: neither edits structured_comparison_service.py hook regions nor admin_routes.py).
- DEFECT_LEDGER rows (the house form `| id | NAME (group, class): summary |`), drafted for the orchestrator: `S81-18 | KB-FIRST-SERVE (G4, SAFE): the KB card replaces the per-field L2 reads for the legs it can serve; full hits skip the paid legs; the price age served as as_of; the verdict-cache key logged as would-hit`; `S81-19 | GAP-QUEUE (G4, SAFE): the demand-ranked kb_gaps ladder off-clock under a Redis single flight; the QarenBot price refresh head daily / tail weekly; the web-search step INERT`; `D16 | OPERATOR-INGEST (G4, SAFE by the existing admin gate): the operator view + the captured-payload ingest for blocked / partner hosts`; `D17 | MEASURE-COVERAGE (G4, SAFE): the daily kb_coverage_daily rollup + the weekly report`.

## Unit S81-18 KB-FIRST-SERVE + the verdict-cache key log

### 1. Base state (measured at 0b19de5b)

#### 1.1 The live product fetch and its L1 / L2 sites (Q1)
| site | file:line | what it does at base |
|---|---|---|
| per-request service | `structured_comparison_service.py:10000` (`get_structured_comparison_service` returns a NEW `StructuredComparisonService()`), `:4268` / `:4989` (`self._price_candidates = {}` per request) | instance attributes are per-request state |
| REST product gather | `:4464-4467` profile task, `:4470-4473` `asyncio.gather(self._fetch_product_data(products[0], ..., partial_slot=0), ...(products[1], ..., partial_slot=1))` | the two products fetched in parallel |
| stream product gather | `:5162-5165` profile task, `:5173-5179` `asyncio.wait_for(asyncio.gather(... partial_slot=0 / 1), timeout=STREAM_HARD_CAP_SECONDS)` | same, hard-capped |
| `_fetch_product_data` | `:5907-6663` | `result` dict `:5935`; `_PHASE1_TIMEOUTS` `:5967`; `_record_races` `:6000`; `_price_task = asyncio.ensure_future(asyncio.wait_for(_timed_task("price", self._get_price(...)), ...))` `:6001-6004` (launched BEFORE the unified search); unified search block `:6056-6094` with the L1 GETs `specs_hit` / `reviews_hit` `:6060-6061` (`_cache_get_async` `:1101`); specs task `:6127-6130`; price appended `:6152-6153`; reviews task `:6155-6166`; image task `:6176-6190`; gather `:6193`; post-gather loop `:6219-6233`; page-image piggyback `:6325-6348`; rating race `:6430-6431`; smart fallback `:6469-6472`; Tier 2 `:6518-6541` (residual guard `:6520`); Tier 3 `:6549-6572` (`:6551`) |
| specs L1 then L2 | `_get_specs`: `:6737` L1, `:6744-6745` `get_cached_specs(cache_key)` | `product_data_service.py:200-221` (30-day TTL `:18`), through `run_db` |
| price L1 then L2 | `_get_price`: `:7007` L1, `:7018-7022` `get_cached_price(cache_key, region)` | `product_data_service.py:249-326`; freshness `_price_row_fresh` `:116-145` (genuine 7 d `GENUINE_PRICE_DB_TTL` `:28`, else 24 h `PRICE_DB_TTL` `:19`) |
| reviews L1 then L2 | `review_service.get_reviews` `:722`, L2 `:756-762` `get_cached_reviews` | `product_data_service.py:367-386` (14 d `:20`); the success dict keys `average_rating` / `total_reviews` (`extraction_service.py` extract_reviews :1850, the error shape at +55, the coercion at +81-97) |
| fairness re-selection | REST `:4516-4519`, stream `:5270-5273` `reconcile_pair_fairness(product_data, query, category_used, candidates_by_name=self._price_candidates)` (`price_service.py:3301`) | re-selects from `self._price_candidates[full_name]` (normalized candidate shape `value / size / source_method / retailer / title / variant_rank / raw_data`, gated by `is_price_showable`) built by `_seed_shortcircuit_candidates(full_name, *, kind, currency="BHD", price_dicts=None, ...)` `:9464` (kind `price_dicts` `:9632-9636`) |
| verdict call | REST `:4582` `scores_summary`, `:4595` `_verdict_quality`, `:4597-4605` `generate_comparison(...)`; stream `:5434`, `:5453`, `:5458-5467` `_verdict_coro = generate_comparison(...)` | `extraction_service.py:2536`: `verdict_model = await model_router.get_model(priority="high")` `:2566`; `system_msg = build_verdict_prompt(products=[p1, p2], comparison_quality=..., user_cohort=demographics_profile, category=category)` `:2578-2583`; `build_verdict_prompt` `:2161` |
| eligibility inputs | REST `:4554-4557` (`behavior_profile`, `demographics_profile` from `_profile_task`), `:4574-4578` `cohort_profile = self._derive_cohort_profile(user_preferences, demographics_profile)` then `compute_scores(product_data, preferences=user_preferences, behavior_profile=behavior_profile, cohort_profile=cohort_profile)`; stream `:5418-5428`; winner `scoring_result.get("winner_index", 0)` (REST `:4689`, stream `:5443`, `reconcile_winner_prose` `:5559`) | `_derive_cohort_profile` `:5788-5806`: explicit prefs win, no demographics -> None |
| metadata idiom | `_stamp_unit_metadata` `:3923-3947` (flag-ON-only keys, all three paths) | the S81-18 `kb_hit` key rides it |
| G3 tail | `_kb_ingest_tail` `:3886-3921`, call lines REST `:4819`, stream `:5749` | G4 never moves them |
| model id | `model_router_service.get_model` `:71-101` (priority high -> `verdict_model()` unless the 4o counter is over the threshold) | the key uses `model_config.verdict_model()` (pure env read), stated limit L5 |

#### 1.2 The card RPC (Q2)
`migrations/045_kb_core.sql:425-482`: `kb_product_card(p_product_id text, p_lang text DEFAULT 'en') RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path TO 'public'`; body `jsonb_build_object('product', to_jsonb(p.*), 'variants', [...ORDER BY v.id], 'offers', [the latest row per (variant, merchant, market, currency): ORDER BY last_seen DESC, sale first, captured_at DESC, id DESC], 'images', [ORDER BY captured_at DESC, id], 'specs', [cited only, lang p_lang else en, one per field], 'rating', {sources, review_count, rating})` `FROM kb_products p WHERE p.id = p_product_id`; NO row -> the function returns NULL (a SQL function over an empty FROM). RLS: EXECUTE granted to service_role only `:523` / `:528`. Pinned client: `supabase==2.31.0`, `postgrest==2.31.0` (`requirements.txt:171`, `:115`); measured on `.venv-qaren`: `SyncPostgrestClient.rpc(self, func: str, params: dict[str, str], count=None, head=False, get=False) -> SyncRPCFilterRequestBuilder`, so the call is `client.rpc("kb_product_card", {"p_product_id": pid, "p_lang": lang}).execute()` with `.data` = the jsonb (a dict) or None. Size: bounded by the KB row counts per product (variants x merchants offers, images, cited specs); no live size measured (045 not applied, R-A15); the stated budget is a canary item.

#### 1.3 Identity keys
`kb_service.kb_product_id(brand, name, variant=None)` `:231-254` (the juice id `fragrances|<brand>|<name>|<conc>`; None on a placeholder identity R-A5 or a non-fragrance spine), the SAME function G3's `kb_ingest.run_job` keys on (`kb_ingest.py:427-428`), so a G3-written card is found by the same key. `kb_variant_key` `:257`. Vocabulary `:132-146`; `KB_GAP_STATES` `:145`.

#### 1.4 The capability header (Q4)
No reader of `X-Client-Capabilities` exists in app/ (measured grep: zero matches for `Client-Capabilities`, `client_capabilities`, `price_asof` under `app/`). The S81-05 middleware binds only three headers (`app/utils/request_context.py:76-82`, `bind_from_headers` :218-253) and none reaches `StructuredComparisonService`. The client sends it: `SmartCompareApp/src/services/requestContext.ts:17-19` (the doc: `CLIENT_CAPABILITIES` joined with ','; `price_asof` ships with the as-of rendering) and `:153` (`headers['X-Client-Capabilities'] = CLIENT_CAPABILITIES.join(',')`), built 3 does not send it (S81-08 is not shipped). The five compare call sites own a `request: Request`: `text_routes.py:594` (call :661), `:800` (:882), `:994` (:1145), `:1432` (:1470), `image_routes.py:200` (:560). Existing optional-keyword idiom at every site: `**({"output_lang": _ol} if (_ol := ...) else {})`, `**({"fragrance_gate": _gate} if _gate is not None else {})` (`text_routes.py:671-672`). The 24 h / 7 d rule: `product_data_service._price_row_fresh` :116-145 over `PRICE_DB_TTL` / `GENUINE_PRICE_DB_TTL`; `price_service.PRICE_CACHE_TTL` :143 / `GENUINE_PRICE_CACHE_TTL` :157; genuineness `price_service.is_genuine_source_method` :161, `_GENUINE_BH_SOURCE_METHODS` :17090-17112.

#### 1.5 Response projection of a price and the client source-method map
`price_service.public_price_view` :9396-9412 strips `guard_rejected` and every `_`-prefixed key under `ENABLE_EXACT_PRICE_GATE` (default ON, :4370); a non-underscore key such as `as_of` passes to the wire. `is_price_showable` :1877 refuses a source_method outside `_showable_source_methods()` (:1907-1909). The client maps `source_method` through `SmartCompareApp/src/services/sourceMethod.ts` APPROVED (`page_scrape` -> 'Retailer page'; an unknown method suppresses the pill). `response_builder.py:60-77` reads `_cached` for `cache_hit` / `genuine_from_cache` metadata.

#### 1.6 The self-observation hazard (measured)
G3's job writes a kb_offers observation for any genuine-method price on an allowed registry URL (`kb_ingest.py:443-453`); it does not read `_cached` (the only `_cached` readers are `kb_ingest.py:196` / `:200` for D05 and `response_builder.py:71`). A KB-served price carrying a genuine method would therefore be RE-OBSERVED by G3 (a `last_seen` bump through `KB_OFFER_UPSERT_SET`, `kb_service.py:153`), so a stale KB price would look freshly seen forever. S81-18 closes it (2.6, change C4).

#### 1.7 Pins that constrain the new text (measured)
- `tests/test_s81_kb_schema.py:331-344` P01_ALLOWED / P01_FUNCTIONS / P02_ALLOWED, `test_s14_p01_no_importer_of_kb_service` :358-389, `test_s14_p02_no_kb_relation_literal_outside_the_leaf` :392-406; `KB_RELATION_NAMES` :66 includes `kb_product_card` (KB_FUNCTIONS :59-65). -> E1 / E2.
- `tests/test_s81_s15_registry_robots.py:776-789` p5 (no `robots_registry` text anywhere in app/ outside robots_registry.py / merchant_registry.py; no `kb_merchants` text in the live fetchers) and `:792-805` p6 (structured_comparison_service.py imports no `merchant_registry` and holds no `"partner"` string constant): kb_serve.py and the scs hunks carry neither.
- `tests/test_s75_fanout_identity.py:277` FY25 (flag-OFF REST / stream digests vs main), `:294`, `:310`; the FY25 faked pipeline `_install` :100-252 is the RED harness (copied, never imported).
- No `tests/_env_safety.CREDENTIALS_UNSET` change (no new credential name; the service-role client is the existing `get_admin_supabase_client`).

#### 1.8 Flag idiom, line endings, libraries
House boolean (0.1). Every backend file of the footprint is CRLF in the working copy (measured: `structured_comparison_service.py` 10000 / 10000 lines CR-terminated, `text_routes.py` 2054, `kb_ingest.py` 509, `admin_routes.py` 1299): the Edit tool preserves endings; NEW files are written LF. No new dependency: `asyncio`, `hashlib`, `json`, `logging`, `os`, `collections.OrderedDict`, `datetime` + in-repo leaves.

#### 1.10 Base pass state
The base run above (1609 passed; the 5 environmental r27 rows). `tests/test_s75_fanout_identity.py`, `tests/test_s81_s17_kb_ingest.py`, `tests/test_s81_d14_live_robots.py`, `tests/test_s81_kb_schema.py`, `tests/test_flush_live_price_key.py` all green at base.

### 2. Contract

#### 2.1 Flags and knobs
`ENABLE_KB_FIRST_SERVE`, `ENABLE_VERDICT_CACHE_LOG` (independent), `KB_FIRST_SERVE_TIMEOUT_SECONDS` (1.0, 0.2..3.0: the `asyncio.wait_for` bound of the gathered card read), `KB_FIRST_SERVE_MAX_ASOF_DAYS` (30, 8..90: the oldest `last_seen` a past-TTL KB price may have for a `price_asof` client), `VERDICT_CACHE_LOG_MAX_KEYS` (10000, 100..100000: the per-process LRU of seen keys).

#### 2.2 Public surface of `app/services/kb_serve.py` (stdlib at top; `kb_service` only through `kb_leaf()`; `product_data_service`, `database_service`, `db_offload`, `image_service`, `model_config`, `extraction_service` imported lazily inside functions)
- `KB_PRODUCT_CARD_RPC = "kb_product_card"` (E2 line), `LICENCE_FIELDS = ("notes_top", "notes_heart", "notes_base", "longevity", "sillage")`, `KB_HIT_VALUES = ("full", "partial", "miss")`.
- `kb_first_serve_enabled() -> bool`, `verdict_cache_log_enabled() -> bool`, `timeout_seconds() -> float`, `max_asof_days() -> int`, `max_log_keys() -> int`; seams `_now()` (aware UTC) and `_admin_client()`.
- `client_price_asof(request) -> bool`: reads `ENABLE_KB_FIRST_SERVE` FIRST (OFF -> False, no header read); then `request.headers.get("x-client-capabilities")`; a value over 512 chars, a non-str or an exception -> False; else `"price_asof" in {t.strip().lower() for t in value.split(",")}`. Never logs the value.
- `required_spec_fields(category) -> tuple`: `extraction_service.CRITICAL_SCHEMA_FIELDS.get(category, [])` minus `LICENCE_FIELDS`, order kept. Measured for `fragrances` (`extraction_service.py:378` NON_NEGOTIABLE `["concentration", "longevity"]` + `:403` PREFERRED `["scent_family", "sillage", "notes_top", "notes_heart", "notes_base", "season"]`, composed at :417-422): `("concentration", "scent_family", "season")`. Any other category -> the full list minus licence fields (the fragrance-only gate keeps them rare; stated L7).
- `async fetch_cards(products, lang) -> list`: two entries in product order. Per product `pid = kb_leaf().kb_product_id(brand, name, variant)`; pid None -> None with NO call. Otherwise ONE `await run_db(lambda: client.rpc(KB_PRODUCT_CARD_RPC, {"p_product_id": pid, "p_lang": lang_or_en}).execute())`; the two run in ONE `asyncio.gather` inside ONE `asyncio.wait_for(..., timeout_seconds())`. `.data` a dict with a dict `product` -> the card; anything else -> None. Total: a timeout, a client None or any exception -> `[None, None]` plus ONE `logger.warning("[KB_SERVE] card read failed: %s", type(exc).__name__)`; never raises, never retries. `lang_or_en` = `output_lang` when it is `"ar"` else `"en"`.
- `classify(card, *, category, region, now, accepts_asof) -> dict` (pure): returns `{"hit", "pid", "version", "price", "price_state", "candidates", "specs", "specs_complete", "image_url", "reviews", "rating", "review_count"}`:
  - `card is None` -> `hit = "miss"`, every other value None / False / [] (`price_state = "none"`).
  - Offers eligible: `region == "bahrain"` and `market == "BH"` and `observed_currency == "BHD"` and amount > 0 and `in_stock is not False` and `kb_service.kb_source_allowed(canonical_url)`; per offer `age = now - parse(last_seen)`; `fresh` when `age <= product_data_service.GENUINE_PRICE_DB_TTL` (read at call time; every KB offer is a genuine BH observation by the G3 / G2 / D16 writers' rule, so the 7 d window applies); `asof` when not fresh and `accepts_asof` and `age <= max_asof_days()`; else refused. Served price = the eligible fresh offer (else asof offer) with the newest `last_seen`, ties -> the lower amount, then the lower `variant_id`. `price_state` in `fresh | asof | stale_refused | none`.
  - The price dict (additive keys only): `{"amount": float, "currency": "BHD", "retailer": merchant_id, "url": canonical_url, "source_method": "page_scrape", "estimated": False, "title": "<brand> <name> <concentration> <size_ml>ml" (parts present only), "size": "<size_ml>ml" when the variant has size_ml, "as_of": last_seen as ISO-8601 Z, "_cached": True, "_cache_source": "kb"}` plus `"in_stock": bool` when the row has a bool. `source_method` is `page_scrape` (open question Q1: the honest client label 'Retailer page', the 7 d genuine window, showable; no new method string, which `is_price_showable` would refuse and the client would render with no pill).
  - `candidates`: every eligible offer of the same `price_state` class as the served one, as price dicts of the same shape (fed to `_seed_shortcircuit_candidates(kind="price_dicts")`, which applies `is_price_showable` itself).
  - `specs`: `{field: value}` of the card's cited specs (the RPC returns cited rows only) plus `"_field_confidence": {field: "kb_cited"}`, `"_cached": True`, `"_cache_source": "kb"`; `specs_complete = set(required_spec_fields(category)) <= set(fields)` (and at least one field).
  - `image_url`: the first card image with an `https://` URL that `image_service._is_valid_image_url` accepts and `kb_source_allowed` (045 already enforces https + the deny belt); else None.
  - `reviews`: when `card.rating.sources > 0` and `rating` is a number: `{"average_rating": float, "total_reviews": int or None, "_cached": True, "_cache_source": "kb"}`, and `rating` / `review_count` the same numbers; else None.
  - `version`: `card.product.updated_at` when a non-empty str, else `sha256(json.dumps(card, sort_keys=True, separators=(",", ":"), default=str))[:16]`.
  - `hit = "full"` iff `card.product.identity_confidence == "high"` and `price_state in ("fresh", "asof")` and `specs_complete` and `image_url` is not None; else `"partial"`.
- `async served(value)`: returns `value` (the coroutine the Phase-1 slots await in place of a live leg, so `_timed_task` / `wait_for` / the done callbacks see the same shapes).
- `verdict_key(*, pids, versions, scores_summary, winner_index, lang, model, prompt) -> str`: `sha256("\x1f".join([pid0 or "-", pid1 or "-", v0 or "-", v1 or "-", sha256(scores_summary or ""), str(int(winner_index)), lang or "en", model or "-", sha256(prompt or "")]).encode("utf-8")).hexdigest()`.
- `log_verdict_key(*, user_preferences, demographics_profile, behavior_profile, product_data, scores_summary, winner_index, lang, category, comparison_quality, views) -> Optional[str]`: reads `ENABLE_VERDICT_CACHE_LOG` FIRST (OFF -> None, nothing else read); eligible only when `not user_preferences and demographics_profile is None and behavior_profile is None`; else None (no line). The model = `model_config.verdict_model()`; the prompt = `extraction_service.build_verdict_prompt(products=[p0, p1], comparison_quality=comparison_quality, user_cohort=None, category=category)` (the eligible user has no cohort, so this IS the static prefix the verdict call builds; `scores_summary` is hashed separately). pids / versions from `views` (the per-slot classify results; a miss or no flag -> the live identity key `kb_product_id(brand, name, variant)` or "-", version "-"). `would_hit = key in _SEEN`. Logs ONE `logger.info("[VERDICT_CACHE] would_hit=%d key=%s", would_hit, key[:16])`. Returns the key. Total: any exception -> None and one DEBUG line.
- `seed_verdict_key(key)`: key None -> no-op; else insert into the per-process `OrderedDict` LRU `_SEEN` (thread lock; evict oldest past `max_log_keys()`). Called only after a successful verdict (the "non-supported rows never seed it" rule: a verdict that raised, timed out or fell back never reaches the seed line).

#### 2.3 The hooks (structured_comparison_service.py; flag OFF = the base statements; Q1)
- Import: `from app.services import kb_serve` beside the G3 imports (module attribute access only).
- H0 (REST before `:4470`, stream before `:5173`): `if kb_serve.kb_first_serve_enabled(): self._kb_cards_task = asyncio.ensure_future(kb_serve.fetch_cards(products, output_lang)); self._kb_hit_marks = ["miss", "miss"]`. Flag OFF: one env read, no attribute written. The task is total and bounded by the knob (it never raises and ends within `KB_FIRST_SERVE_TIMEOUT_SECONDS`), so an early exit leaves no stranded work beyond that bound (L6).
- H1 (`_fetch_product_data`, after `result` `:5935`, before `_price_task` `:6001`): `_kb = None; _kb_task = getattr(self, "_kb_cards_task", None)`; `if _kb_task is not None and partial_slot in (0, 1): cards = await _kb_task; _kb = kb_serve.classify(cards[partial_slot], category=category, region=region, now=kb_serve._now(), accepts_asof=bool(getattr(self, "_kb_price_asof", False))); self._kb_hit_marks[partial_slot] = _kb["hit"]`. The flag is read ONCE per compare at H0; H1-H7 key on the per-request task (a mid-request flip cannot split a compare). Non-orchestrator callers (`partial_slot` None, e.g. `text_routes.py:1756`'s mirror and the warmer) never serve from the KB.
- H2 price (`:6001-6004`): the coroutine inside the existing `asyncio.ensure_future(asyncio.wait_for(_timed_task("price", <coro>, stage_timings), timeout=...))` becomes `kb_serve.served(_kb["price"])` when `_kb and _kb["price"] is not None`, else the base `self._get_price(brand, name, variant, region, search_query, nocache, category)`; when served, `self._seed_shortcircuit_candidates(full_name, kind="price_dicts", price_dicts=_kb["candidates"])` runs once before the task. The done callbacks `:6017-6023` and the orphan drain are unchanged.
- H3 specs + unified search (`:6056-6094`, `:6127-6130`): `_kb_specs = _kb["specs"] if (_kb and _kb["specs_complete"]) else None`; `_kb_full = bool(_kb and _kb["hit"] == "full")`. The unified-search condition becomes `(include_specs and not specs_hit and _kb_specs is None) or (include_reviews and not reviews_hit and not _kb_full)`; the specs task coroutine is `kb_serve.served(_kb_specs)` when `_kb_specs` is not None. The L1 GETs `:6060-6061` stay (they are the L1, not the L2; brief: the L2 is what the card replaces).
- H4 reviews (`:6155-6166`): on `_kb_full` the reviews coroutine is `kb_serve.served(_kb["reviews"])` (None when the card has no rating: the base reviews-miss value, `_price_fallback_on_miss` :6884 returns None for non-price keys).
- H5 image (`:6176-6190`): when `_kb and _kb["image_url"]` the image coroutine is `kb_serve.served(_kb["image_url"])` (the post-gather piggyback `:6325-6348` keys on `result["price"].get("image_url")`, absent on a KB price, so it does not override).
- H6 Phase 2 / Tier 2 / Tier 3 (`:6420-6472`, `:6518`, `:6549`): on `_kb_full` the rating race and smart fallback are not appended (`result["rating"] = _kb["rating"]`, `result["review_count"] = _kb["review_count"]`) and the two tier blocks are skipped exactly as the S78-TG residual skip skips them (`tier2_filled = {}` / `tier3_filled = {}`, no mark).
- H7 (`_stamp_unit_metadata` `:3923`, after the tier marks): `marks = getattr(self, "_kb_hit_marks", None); if marks: metadata["kb_hit"] = list(marks)` (additive, both entries in KB_HIT_VALUES; written on the REST success body, the partial builder and the stream complete payload: the three existing call sites).
- H8 (REST before `:4595`, stream before `:5453`): `_vkey = kb_serve.log_verdict_key(user_preferences=user_preferences, demographics_profile=demographics_profile, behavior_profile=behavior_profile, product_data=product_data, scores_summary=scores_summary, winner_index=scoring_result.get("winner_index", 0), lang=output_lang, category=category_used, comparison_quality=verdict_comparison_quality(product_data), views=getattr(self, "_kb_views", None))` (the per-slot classify results are stored as `self._kb_views` at H1 under the flag); after the verdict returns (REST after `:4606` `self._track_gpt_cost(usage)`; stream after its `comparison, usage = ...` resolution, both arms of the `_full_deadline_on` branch): `kb_serve.seed_verdict_key(_vkey)`. Flag OFF: one env read inside `log_verdict_key`, `_vkey` None, the seed a no-op.
- Signature: `compare_from_text` (:4053), `_compare_from_text_impl` (:4212), `compare_from_text_streaming` (:4859) gain the keyword `kb_price_asof: bool = False` (additive, last); `compare_from_text` forwards it ONLY when True (`**({"kb_price_asof": True} if kb_price_asof else {})`); the impl / stream set `self._kb_price_asof = True` only when it is True. Route call sites: `**({"kb_price_asof": True} if kb_serve.client_price_asof(request) else {})` at the five sites (1.4). Flag OFF: one env read per route call, no keyword passed, the call byte-identical.

#### 2.4 Seams
`kb_serve._now`, `kb_serve._admin_client`, `kb_serve.fetch_cards` (a recorder), `kb_serve._SEEN` (cleared per test); the FY25 harness fakes `_get_price` / `_get_specs` / `_get_reviews` / `get_product_image_url` / `search_web` / `generate_comparison` as RAISING or counting recorders.

#### 2.5 Failure table (flag ON)
| input | outcome |
|---|---|
| 045 not applied (RPC missing: PostgREST error) | `fetch_cards` -> `[None, None]` + one WARNING; both misses; the live path runs as base |
| `ENABLE_SYNC_DB_OFFLOAD` OFF | `run_db` runs the RPC inline on the loop (base behaviour of every L2 read); a precondition, not guarded (L1) |
| timeout over the knob | `[None, None]`, one WARNING `TimeoutError` |
| pid None (placeholder / non-fragrance spine) | miss for that slot, no RPC for it |
| card with identity medium / low | partial: served legs only where the data qualifies; never a full hit |
| KB price past 7 d, client without `price_asof` | `stale_refused`: the price leg runs live (base) |
| KB price past 7 d, `price_asof` client, `last_seen` within the knob | served with `as_of` |
| region not bahrain | no KB price (offers are BH / BHD); other legs may serve |
| card images all refused | no KB image; image race runs |
| verdict-cache log raises | None, one DEBUG line; the verdict unaffected |
| any classify exception | treated as a miss for that slot (classify is total; a raise is caught at H1 with one WARNING) |
Never a new error code, never a 503, never a refusal: S81-18 only serves or falls through.

#### 2.6 Flag-OFF identity (the main invariant) and the self-observation guard
Flag OFF: H0 and the route reader are one env read each; H1-H7 read a missing attribute (None) and run the base statements; H8 is one env read; no RPC, no header read, no key, no log line, no attribute written. Proven by the FY25 digests unchanged (`test_s75_fanout_identity.py:277`), the new golden `tests/fixtures/s81_s18_flag_off_golden.json` (REST, stream, camera bodies with the FULL configuration present: both flags OFF, the three knobs set, the header sent) and raising recorders on `kb_serve.fetch_cards`, `client.rpc` and `kb_serve.verdict_key`. C4 (kb_ingest): `_PRICE_KEYS` (`kb_ingest.py:264-267`) gains `"_cache_source"` and the offer condition (`:446-448`) gains `and price.get("_cache_source") != "kb"`: with S81-18 OFF no price carries `"kb"`, so G3's writes are unchanged (the projection gains one internal key valued None; no pin compares the projection's key set: measured, `tests/test_s81_s17_kb_ingest.py` reads `build_job` output only through `run_job` :426-429 and `_check_vocab` on field_status).

### 3. Change list (GREEN, after D16; byte-copy every existing file first into `<scratchpad>/S81-G4_green_before/` with sha256)
- C1 NEW `app/services/kb_serve.py` (2.2; LF; pure ASCII; no `robots_registry`, no `kb_merchants`, no `partner` text).
- C2 EDIT `app/services/structured_comparison_service.py`: the import; H0 x2; H1-H6; H7; H8 x2 (+ the two seed lines); the three signatures. CRLF kept.
- C3 EDIT `app/api/text_routes.py` (4 sites) and `app/api/image_routes.py` (1 site): the capability keyword, plus `from app.services import kb_serve` in each.
- C4 EDIT `app/services/kb_ingest.py`: `_PRICE_KEYS` + the offer condition (2.6).
- C5 NEW `tests/fixtures/s81_s18_flag_off_golden.json` (recorded by RED at base).
- No other file (the E-rows and CLAUDE.md are the group's, 0.3).

### 4. Existing pins
#### 4.1 Deliberate changes
- E1 (shared, 12.4) `tests/test_s81_kb_schema.py:331-337`: P01_ALLOWED gains `("app/services/kb_serve.py", "from app.services import kb_service as _kb")`, P01_FUNCTIONS gains `"app/services/kb_serve.py": "kb_leaf"`.
- E2 (shared) `:338-351`: P02_ALLOWED gains `("app/services/kb_serve.py", 'KB_PRODUCT_CARD_RPC = "kb_product_card"')`.
#### 4.2 Must stay green and unedited
FY25 / FY5 (`tests/test_s75_fanout_identity.py`), `tests/test_s81_s17_kb_ingest.py` (all 28 rows: C4 must not move one), `tests/test_s81_g3_gate_rows.py`, `tests/test_s81_d14_live_robots.py`, the S81-15 p5 / p6, `tests/test_flush_live_price_key.py`, `tests/test_w4_13_measurement_truth.py:1852-1860` and `tests/test_s81_s05_request_context.py:1443` (the per-path OpenAPI pins: a keyword with a default on a service method changes no route schema; the route signatures do not change), `tests/test_genuine_predicate_parity.py`, every comm-set member.

### 5. RED tests: `tests/test_s81_s18_kb_first_serve.py` (new; pure ASCII; hermetic: netguard on; the compare driven through the FY25 pattern `tests/test_s75_fanout_identity.py:100-252` COPIED; the service-role client an in-memory recorder with `rpc(name, params) -> builder.execute()` returning configured cards and recording the executing thread; `run_db` patched to a recorder that runs the lambda; every live leg a RAISING recorder unless the row says otherwise; synthetic identities `Brand Alpha` / `Scent One` built at run time; every missing symbol read through a getattr / find_spec helper so a base run fails on an AssertionError only)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_module_and_flags` | `kb_serve` importable; both readers False unset, True for `" TRUE "`, `"1"`, `"yes"`, `"On"`, False for `"0"`, `"apply"`, garbage | RED | C1 |
| R2 | `test_r2_knobs_parse_defensively` | each knob: unset / "" / "abc" / "inf" / "nan" / "-1" / "0" -> default; over / under -> clamped | RED | C1 |
| R3 | `test_r3_client_price_asof` | flag OFF -> False and the request's `headers.get` never called (recorder); ON: `"price_asof"`, `" Price_AsOf ,x"` -> True; `"x,y"`, 513 chars, non-str -> False | RED | C1 |
| R4 | `test_r4_required_spec_fields_fragrances` | `("concentration", "scent_family", "season")`; no LICENCE_FIELDS member in any category's result | RED | C1 |
| R5 | `test_r5_fetch_cards_one_gather_two_rpcs_through_run_db` | two `rpc("kb_product_card", {"p_product_id": pid, "p_lang": "en"})` calls, each inside the `run_db` recorder; pid = `kb_service.kb_product_id(...)`; a placeholder product -> no call for it; `"ar"` output -> `p_lang "ar"` | RED | C1 |
| R6 | `test_r6_fetch_cards_total` | rpc raises / timeout (knob 0.2, a slow fake) / client None / `.data` list -> `[None, None]`, one WARNING with the type name only | RED | C1 |
| R7 | `test_r7_classify_full_partial_miss` | the matrix: None -> miss; high + fresh BH offer + the three cited specs + https image -> full; any one missing -> partial; identity medium -> partial | RED | C1 |
| R8 | `test_r8_price_ttl_and_asof` | last_seen 6 d -> fresh; 8 d + accepts_asof False -> `stale_refused`, price None; 8 d + True -> served with `as_of` = last_seen Z; 31 d + True (knob 30) -> refused; non-BHD / market AE / region kuwait / in_stock False -> not eligible | RED | C1 |
| R9 | `test_r9_price_dict_shape` | exact key set `{amount, currency, retailer, url, source_method, estimated, title, size, as_of, _cached, _cache_source}` (+ in_stock when bool); `source_method == "page_scrape"`; `is_price_showable(full_name, price)` True for the synthetic exact identity | RED | C1 |
| R10 | `test_r10_rest_full_hit_skips_paid_legs` | flag ON, two full cards: `search_web`, `_get_price`, `_get_specs`, `_get_reviews`, `get_product_image_url`, the rating race, `_smart_fallback_extract`, `tier2_fill_non_negotiables`, `tier3_synthesize_non_negotiables` are RAISING recorders and never called; the body's products carry the KB price (`as_of` present), specs and image; `metadata.kb_hit == ["full", "full"]` | RED | C2 |
| R11 | `test_r11_stream_full_hit_same` | R10 on the stream path; the complete payload's `metadata.kb_hit` | RED | C2 |
| R12 | `test_r12_partial_runs_only_missing_legs` | card with price only: `_get_price` never called, `_get_specs` / `_get_reviews` / image called once each, `search_web` called once; `kb_hit == ["partial", "miss"]` for a miss on slot 1 | RED | C2 |
| R13 | `test_r13_candidates_seeded_for_fairness` | two eligible offers (50 ml, 100 ml): `self._price_candidates[full_name]` holds both (normalized shape, `raw_data` = the price dict) before `reconcile_pair_fairness` runs (recorder) | RED | C2 |
| R14 | `test_r14_asof_only_with_header` | the TestClient with the header `X-Client-Capabilities: price_asof` and a 10-day offer -> KB price served with `as_of`; without the header -> `_get_price` called (live) | RED | C2 + C3 |
| R15 | `test_r15_camera_route_forwards_capability` | image_routes call recorder: keyword `kb_price_asof=True` present only with flag ON + the header | RED | C3 |
| R16 | `test_r16_verdict_key_log_eligible_only` | ENABLE_VERDICT_CACHE_LOG ON: anonymous compare -> ONE `[VERDICT_CACHE] would_hit=0 key=<16 hex>` line; same compare again -> `would_hit=1`; with user_preferences, with demographics, with a behaviour profile -> no line | RED | C1 + C2 |
| R17 | `test_r17_verdict_key_inputs` | the key changes when each one input changes (pid, version, scores_summary, winner_index, lang, model env, category prompt) and not otherwise; the log line carries no name, no URL (regex `^\[VERDICT_CACHE\] would_hit=[01] key=[0-9a-f]{16}$`) | RED | C1 |
| R18 | `test_r18_no_seed_on_failed_verdict` | `generate_comparison` raises -> the key is not in `_SEEN`; the LRU evicts past the knob | RED | C1 + C2 |
| R19 | `test_r19_kb_served_price_never_reobserved` | G3 `run_job` over a projection whose price carries `_cache_source "kb"`: no kb_offers insert / update; a live price on the same URL still writes (G3 unchanged) | RED | C4 |
| R20 | `test_r20_card_failure_falls_through` | flag ON, RPC raises: the body equals the flag-OFF body except the additive `metadata.kb_hit == ["miss", "miss"]` | RED | C1 + C2 |
| P1 | `test_p1_flag_off_rest_stream_camera_golden` | FULL configuration (both flags OFF; the three knobs set; the header sent; ENABLE_SYNC_DB_OFFLOAD set): REST / stream / camera bodies == `s81_s18_flag_off_golden.json` (recorded at base, normalized as FY25 `_normalize`) | PIN | base |
| P2 | `test_p2_flag_off_no_rpc_no_header_no_key` | same configuration: raising recorders on `client.rpc`, `kb_serve.fetch_cards` (when present), the request's `headers.get("x-client-capabilities")` and `hashlib.sha256` calls from kb_serve (when present) never fire; no `[VERDICT_CACHE]` / `[KB_SERVE]` line; no `kb_hit` key | PIN | base |
| P3 | `test_p3_flag_off_service_signature_call` | the route->service call recorder sees EXACTLY the base keyword set at the five sites | PIN | base |
| P4 | `test_p4_g3_offer_written_for_live_price` | G3 run_job on a live genuine price writes one offer (the C4 guard does not over-reach) | PIN | base |

### 6. Mutation table (byte copies, the killing rows via `pyt.py -k`, bound 600, restore + sha256)
| id | mutant (exact-string edit) | killed by |
|---|---|---|
| S18-M1 | H0 flag read removed (task always started) | P2 |
| S18-M2 | `fetch_cards` calls `client.rpc` directly, not through `run_db` | R5 |
| S18-M3 | the 7 d window replaced by 24 h | R8 |
| S18-M4 | `accepts_asof` ignored (past-TTL always served) | R8, R14 |
| S18-M5 | full-hit test drops `specs_complete` | R7, R12 |
| S18-M6 | H6 tiers not skipped on a full hit | R10 |
| S18-M7 | candidates not seeded | R13 |
| S18-M8 | eligibility drops the behaviour-profile clause | R16 |
| S18-M9 | seed before the verdict call | R18 |
| S18-M10 | C4 guard removed | R19 |
| S18-M11 | route forwards the keyword with the flag OFF | P3 |
| S18-M12 | `source_method` set to `"kb_offer"` | R9 |
| S18-M13 | `LICENCE_FIELDS` emptied | R4 |

### 7. Comm set, gates
#### 7.1 Comm set: the group set (12.1); S81-18's edited modules: structured_comparison_service, kb_ingest, text_routes, image_routes; the read-only consumers kb_service, product_data_service, extraction_service, model_config, db_offload, image_service, price_service (public_price_view / is_price_showable); the importers of each, app/main.py's importers included.
#### 7.2 Gates for GREEN (cheapest first)
py_compile + ruff E9/F63/F7/F82 on the touched .py; the RED file OFF / ON; `tests/test_s75_fanout_identity.py`; `tests/test_s81_s17_kb_ingest.py tests/test_s81_g3_gate_rows.py tests/test_s81_d14_live_robots.py`; `tests/test_s81_kb_schema.py`; the comm set chunks (base reused per LC-6); the CI-order set (12.2); byte checks (> 127 count 0 on new files; no whole-file diff in `git diff --stat`).
#### 7.3 Client fences
No literal the fourteen backend-scanning client fences read moves (they read `app/legal`, landing, processors.json, `docs/` runbook text named in their files, the SSE and timeout source in SmartCompareApp; G4 adds a runbook file, edits none they read; measured by name: none of the fourteen reads `docs/runbooks/`). LC-5 still runs them by path at GREEN and at the rebase (the footprint touches app/, scripts/, docs/).

### 8. CLAUDE.md row (in the G4 block; wording may tighten, content may not) and owner steps
- `ENABLE_KB_FIRST_SERVE` + `ENABLE_VERDICT_CACHE_LOG` + knobs `KB_FIRST_SERVE_TIMEOUT_SECONDS` (1.0, 0.2..3.0), `KB_FIRST_SERVE_MAX_ASOF_DAYS` (30, 8..90), `VERDICT_CACHE_LOG_MAX_KEYS` (10000) (S81-18 KB-FIRST-SERVE, `app/services/kb_serve.py`; the two flags independent). `ENABLE_KB_FIRST_SERVE` ON: before the product gather the REST / stream compare starts ONE task of two `kb_product_card` RPCs (service role, through `run_db`, bounded by the timeout knob, keyed by `kb_service.kb_product_id`, the G3 ingest key); each product slot classifies its card: full (identity high + a BH / BHD offer within 7 d of `last_seen`, or older up to the knob for a client whose `X-Client-Capabilities` lists `price_asof` + the cited specs `concentration, scent_family, season` for fragrances + an https image) skips the unified search, the specs / reviews LLM, the price fan-out, the image race, the rating race, smart fallback, Tier 2 and Tier 3; partial serves only the legs the card holds and runs the rest live (their own L1 / L2 unchanged); miss = base. The KB price is `source_method page_scrape`, `retailer` the merchant host, the additive `as_of` (last_seen, ISO Z), `_cached` true / `_cache_source kb`; every eligible offer is seeded as a fairness candidate; G3 never re-observes a KB-served price. Additive `metadata.kb_hit` = [slot0, slot1] in full / partial / miss. A card-read failure = one `[KB_SERVE] card read failed: <Type>` WARNING and the base path. `ENABLE_VERDICT_CACHE_LOG` ON: for a compare with no explicit preferences, no cohort and no behaviour profile ONE `[VERDICT_CACHE] would_hit=<0|1> key=<16 hex>` INFO line (sha256 over the ordered pids, card versions, the scores-summary hash, winner_index, lang, the configured verdict model, the static verdict-prompt digest); keys seeded only after a successful verdict into a per-process LRU; nothing cached, nothing served.
- Owner steps (names only): (1) 045 applied (item 29); (2) `ENABLE_SYNC_DB_OFFLOAD` ON on `web` before `ENABLE_KB_FIRST_SERVE`; (3) the KB populated (G2 APPLY runs; `ENABLE_KB_INGEST` ON) and `ENABLE_VERDICT_CACHE_LOG` ON first for a week (log only); (4) `ENABLE_KB_FIRST_SERVE` ON in a canary window: read the `metadata.kb_hit` split, `stage_timings_ms` p50 / p95 on full hits (target cards < 2 s, verdict < 7 s streamed, done < 10 s; prod cap 30 s unchanged), the `[KB_SERVE]` WARNING rate, the genuine-price share.

### 9. Stated limits
- S81-18-L1: the RPC runs inline on the loop when `ENABLE_SYNC_DB_OFFLOAD` is OFF (precondition, not guarded; the same as every L2 read).
- L2: the card read is awaited before the price race starts (a full hit must skip it), so a miss pays up to the RPC wall (bounded by the timeout knob) before the base path begins; measured on the canary.
- L3: a partial hit does not suppress the L2 reads of the legs it cannot serve (those run exactly as base); the L2 is replaced only for the legs the card serves (Q2).
- L4: D05 `field_status` labels a KB price `stale / served_from_cache` (as_of None) because `_cached` is true; the precise KB as_of is the price's `as_of` key (a D05 vocabulary change is out of scope).
- L5: the key's model is the configured verdict model; on a day the 4o counter routes the verdict to the standard model the would-hit overstates.
- L6: an early exit leaves the bounded card task to finish on its own (no orphan drain; it never raises).
- L7: the full-hit spec set exists for fragrances only by measurement; other categories use their critical list minus licence fields.
- L8: the would-hit set is per process and cleared on restart (a LOG instrument, not a cache).
- L9: URL mode (`url_extraction_service`) never KB-serves.
- L10: the KB price `title` is synthesized from the card (brand, name, concentration, size) for the exact-identity gate.

### 10. Out of scope
The verdict cache itself; Tier 2 / Tier 3 / smart fallback leaving the request path for misses (the interim = the owner's `ENABLE_TIER_FILL_RESIDUAL_GUARD` flip after its canary, named in the PR body); `S78 fix 6` (reserve the verdict tail) as a request-path unit; the client as-of rendering (S81-08 / S81-11).

### 11. Open questions (for RULINGS_S81_G4)
- Q1 `source_method "page_scrape"` for a KB-served price (vs a new method string, refused by `is_price_showable` and pill-less on the client).
- Q2 replace the L2 only for the legs the card serves (this spec) vs suppress the L2 of every leg once a card exists (the KB is empty at first flip; the latter would push every partial onto the live fan-out).
- Q3 `as_of` = `last_seen` (the latest confirmation; `captured_at` never moves on a re-observation, `KB_OFFER_UPSERT_SET`) vs the brief's `captured_at`.
- Q4 the capability keyword through the five route call sites (no ContextVar) vs a fourth header in the S81-05 middleware (rejected: it would change S81-05's pinned bind).

## Unit S81-19 GAP-QUEUE: the enrich worker + the price refresh

### 1. Base state (measured at 0b19de5b)

#### 1.1 The queue (Q7)
`migrations/045_kb_core.sql:273-299` `kb_gaps` (`product_key` 14..520, `field ^[a-z][a-z0-9_]{0,63}$`, `demand_count >= 0` default 1, `first_seen <= last_seen`, `state IN ('open', 'queued', 'needs_operator', 'licence', 'closed')` default open, `source_hint` a host or an http(s) URL without query, deny belts, UNIQUE (product_key, field)); index `idx_kb_gaps_open_demand (demand_count DESC, last_seen DESC) WHERE state = 'open'` `:330-331`. Writers at base:
- G3 `kb_ingest.run_job` `:470-482`: the D05 fields `image, price, size, concentration, specs, rating, review_count` (never `identity`, never `pdp_`), state `open` (or `needs_operator` when the price host's row is blocked), source_hint = the registry host, demand by compare-and-set `:344-380`.
- G2 `cron_pdp_discovery.gap_rows` `:275-290`: field `pdp_<sha256(host)[:16]>` (`gap_field` :115-116), state `queued`, demand_count 0, source_hint the canonical PDP URL, product_key the juice id (`ranked_juices` :119-145, the same `kb_products.id`); a re-discovery updates last_seen only (`KbWriter.gaps` :423-437).
- No reader of kb_gaps exists (measured grep: only the two writers and `KB_GAPS_TABLE` constants `kb_ingest.py:55`, `kb_seed_common.py:54`).

#### 1.2 The G2 off-clock toolkit
`scripts/kb_seed_common.py`: stdlib-only top (:23-37); `run_mode` :67, `cli_mode` :82, `house_flag` :87, `int_knob` :110, `float_knob` :120; seams `_admin_client` :132, `_now` :138; `kb_leaf` :142 (the P01-allowed importer); `read_merchant_rows` :182-198 (READ_COLUMNS :44 = `host,status,deny,blocked_reason,registry,robots,challenge,tos,currency_hint,country,platform,updated_at`: NO `search_template`); `rows_by_host` :201, `merchant_for_host` :209, `row_currency` :234; `url_gate(row, url, now, *, require_tos=False)` :250-290 (the order bad_url -> denied -> no_row -> denied -> not_live -> tos -> no_record -> origin -> robots; identical to `live_robots.url_verdict` :179-210 plus the tos step: `VERDICT_REASONS` :54-56 = GATE_REASONS minus tos); `PoliteFetcher(fetch=None, validate=None, sleep=None, require_tos=False)` :302-339 with `async get(url, row=None, now=None, *, gate=True, timeout=20.0, delay=None)` :325 (the gate on the first URL and every hop, the stored crawl delay, the SSRF validator, `MAX_BODY_CHARS` 3,000,000); `KbWriter` :360-440 (`offers` :402 insert-ignore + one re-observation update per row; `gaps` :423 last_seen-only). `scripts/cron_feed_walker.py:447` builds `PoliteFetcher(require_tos=True)` (the ToS precedent).

#### 1.3 The registry search template
`kb_merchants.search_template` (045 :113-115) is seeded from `bh_gcc_sources.json` `search.url_template` (`merchant_registry.py:598`; e.g. the Shopify suggest form `https://<host>/search/suggest.json?q={q}&resources[type]=product&resources[limit]=10`, `data/bh_gcc_sources.json:44`). The `{q}` placeholder is the only variable.

#### 1.4 Extraction and identity
`price_service.extract_price_from_html(html, product_name, currency, domain, url, category=None, outcome_out=None, final_url=None)` :13952 (the deterministic JSON-LD / page extractor the corpus gate exercises, with the exact-identity gate); `kb_ingest.rung_for(method)` :124 (method -> evidence rung; None for converted / render / estimates); `jsonld_widen.allowed_image_url(image, url, OFFICIAL_BRAND_DOMAINS)` (the D08 image policy G3 uses at `kb_ingest.py:455-457`).

#### 1.5 Redis single flight (Q5)
No single flight anywhere in app/ (`price_service.py:265`: "There is no single-flight/lock/SETNX anywhere in `app/`"). Pinned `upstash-redis==1.7.0` (`requirements.txt:202`), measured on `.venv-qaren`: `Redis.set(self, key, value, nx=None, xx=None, get=None, ex=None, px=None, exat=None, pxat=None, keepttl=None)`; the formatter `format_set` returns `res == "OK"` (True acquired, False not); `Redis.delete(*keys)`. `cache_service.redis_client` :166 (`_build_redis_client`; the `redis://` fallback is redis-py, whose `set(..., nx=True, ex=...)` returns True / None).

#### 1.6 The breaker's off-clock lane (Q5)
`llm_spend_breaker.py`: `LANE_OFFCLOCK = "offclock"` :106, cap env `LLM_SPEND_CAP_OFFCLOCK_USD` :122 (default 2.0 :116), `cap_usd(lane)` :308, `reserve(lane, upper_bound_usd) -> Optional[ReserveTicket]` :1182, `settle(ticket, actual_usd)` :1224, `record(lane, actual_usd, admitted_usd=None)` :1102; the G2 seeder reserves before the create (`seed_kb_batch.py:517`). S81-19 makes NO LLM call (2.1), so it calls none of them.

#### 1.7 The service pattern
`railway.warmer.json` / `railway.pdpdiscovery.json` (measured): `build.watchPatterns` = the entry script (+ `scripts/kb_seed_common.py` for G2) + the config file; `deploy.startCommand` `python -m scripts.<entry>`; `restartPolicyType NEVER`. Entry shape: `cron_pdp_discovery.main(argv=None, client=None)` :342-355 (mode FIRST; OFF = one INFO, exit 0, nothing imported), `run = main`.

#### 1.10 Base pass state
`tests/test_s81_d11_pdp_discovery.py`, `tests/test_s81_d09_feed_walker.py` green; `tests/test_s81_s16_kb_seed.py` green except the 5 environmental r27 rows (header).

### 2. Contract

#### 2.1 Placement (the spec decides)
Everything in `scripts/cron_kb_enrich.py`: there is no request-path consumer of the ladder in G4, and S81-20 needs only the gap WRITE (G3 already has it); a scripts-only unit adds no P01 / P02 row (it reuses `common.kb_leaf`, the common table constants, `merchant_registry.KB_MERCHANTS_TABLE` and `kb_ingest.KB_IMAGES_TABLE` by import). No LLM call exists in G4's ladder (steps 1, 2 and the refresh are fetch + the deterministic extractor; step 3 is inert), so the spend cap is a DRY-printed bound (`lane=offclock cap_usd=<cap_usd(LANE_OFFCLOCK)> planned_usd=0.00`) and the breaker is never called; S81-21 wires `reserve` / `settle` when the search step is built.

#### 2.2 The run
`main(argv=None, client=None, redis=None) -> int`: (1) `mode = common.run_mode("ENABLE_KB_ENRICH_WORKER")` FIRST; OFF -> `[KB_ENRICH] mode=off ENABLE_KB_ENRICH_WORKER not set; skipping run`, exit 0, nothing else read. (2) args `--dry-run`, `--report <path>`, `--leg all|gaps|refresh` (default all); `cli_mode`. (3) `client = common.resolve_client(client, PREFIX)` (None -> exit 0). (4) `asyncio.run(_run(...))`. Legs: gaps (only when `ENABLE_KB_GAP_FILL` is ON), refresh (always). DRY: reads only (kb_gaps, kb_merchants with `search_template`, kb_offers_latest), prints the ranked queue (product_key, the open fields, demand, last_seen), the ladder plan per gap (step names and host names), the refresh plan counts (head / tail) and the spend bound; NO fetch, NO Redis command, NO write. APPLY: the full run. Exit 0 always (a failed leg = one WARNING with the type name).

#### 2.3 The gap ladder (APPLY)
- Read: `kb_gaps` select `product_key,field,demand_count,last_seen,state,source_hint` `.eq("state", "open").gte("last_seen", now - KB_ENRICH_DEMAND_DAYS).order("demand_count", desc=True).order("last_seen", desc=True).limit(KB_ENRICH_MAX_GAPS)`; fields starting `pdp_` dropped (belt). Rank per product_key = (max demand_count, latest last_seen). The plan's "7-day distinct-compare demand" needs compare_runs (S81-22): stated L1.
- Registry: one paged read of `kb_merchants` with `READ_COLUMNS + ",search_template"` through `merchant_registry.KB_MERCHANTS_TABLE` (no literal); the juice brand / name from `kb_products` (select `id,brand,name` `.in_("id", chunk)`).
- Single flight per product_key: `ok = redis.set("kbenrich:sf:" + sha256(product_key)[:32], run_id, nx=True, ex=KB_ENRICH_LOCK_SECONDS)`; not ok -> skip, counted `locked`; the key deleted at the end of the product's ladder only if it still holds `run_id` (a GET then DELETE; a lost race leaves the TTL to expire it, stated L4). Redis None or raising -> the product is skipped, counted `lock_unavailable` (fail-closed: two overlapping runs never fetch the same product).
- Per gap field (the closed map; Q7):
  - `specs` (and any field in `LICENCE_GAP_FIELDS = ("specs",)`) -> state `licence` (step 5; never fetched: notes / longevity are licensed content).
  - `price, image, size, concentration, rating, review_count` -> steps 1, 2, 3, 4 in order until the field is filled.
  - Step 1 registry adapter search ($0): up to `KB_ENRICH_HOSTS_PER_GAP` registry rows with status live, a `search_template`, `tos.verdict == "allowed"`, ordered country BH first then host; the URL = template with `{q}` -> `quote_plus(brand + " " + name)`; `common.PoliteFetcher(require_tos=True).get(url, row, now, timeout=KB_ENRICH_FETCH_TIMEOUT_SECONDS)` (the persisted robots verdict + ToS on the first URL and every hop); candidate PDP URLs from the body (JSON: `resources.results.products[].url`, resolved against the origin; else same-host `<a href>` values whose path is not the search path), first 2 candidates, each fetched the same way; extraction 2.5.
  - Step 2 the sitemap / CDX PDP (consumes R-G2-13): the `kb_gaps` rows of the same product_key with field `pdp_*` and state `queued` (one select per product); each hint URL -> its registry row (`merchant_for_host`) -> the same polite fetch -> extraction 2.5; the HINT row then moves: a 2xx fetch (filled or not) -> `closed`; a gate refusal `not_live` on a blocked row or `tos` -> `needs_operator`; a fetch error / non-2xx / timeout -> stays `queued` (retried next run).
  - Step 3 web search: `ENABLE_KB_GAP_WEB_SEARCH` ON -> ONE `[KB_ENRICH] step=web_search status=not_built` INFO line per run and a `web_search_not_built` count; OFF -> nothing. Never an import of an LLM module, never a provider call.
  - Step 4 the operator queue: when every candidate host of the product was refused for `not_live` (blocked) or `tos`, or the product has no live search host but a blocked registry host in its hints -> the gap moves `open -> needs_operator` (D16's queue).
  - A filled field -> the gap moves `open -> closed`.
- State moves: ONE update per gap `update({"state": new}).eq("product_key", k).eq("field", f).eq("state", old)` (a compare-and-set on the state; `demand_count`, `first_seen`, `source_hint` never move; a lost CAS counted, never retried); `new` must be in `kb.KB_GAP_STATES`.

#### 2.4 The price refresh (APPLY; out of process)
- Head (daily): the `KB_ENRICH_HEAD_N` product ids with the largest `sum(demand_count)` over kb_gaps rows (any state, non-`pdp_`, last_seen within the window), then by id. Tail (weekly, only on ISO weekday `KB_ENRICH_TAIL_WEEKDAY`): up to `KB_ENRICH_TAIL_MAX` other product ids holding offers, the oldest `last_seen` first.
- Per product (under the same single flight): its offers from `kb_offers` (latest per (variant, merchant, market, currency), selected client-side from `select("variant_id,merchant_id,market,observed_currency,amount,canonical_url,last_seen,list_vs_sale").like("variant_id", pid + "|%")`); each canonical_url -> its registry row -> `PoliteFetcher(require_tos=True).get(url, row, now, timeout=KB_ENRICH_FETCH_TIMEOUT_SECONDS)` (4 s; NO fallback adapter, NO render tier, NO Magento GraphQL wall path: only the GET of the stored PDP); a 2xx -> extraction 2.5 -> `KbWriter.offers([...])` (insert-ignore on the observation key; the same amount = one `KB_OFFER_UPSERT_SET` update, i.e. `last_seen` moves; a new amount = a new observation). Non-2xx / refused -> counted per reason, nothing written.

#### 2.5 Extraction to rows (both legs)
`price = price_service.extract_price_from_html(html, f"{brand} {name}", currency, host, url, category="fragrances", final_url=final_url)`; a dict with a positive amount and `rung_for(price["source_method"])` not None and `price.get("estimated") is not True` -> `kb.build_offer_row(variant_id=kb.kb_variant_key(pid, conc, size_ml), merchant_id=row["host"], market=row country (ISO 2-3 upper) else skip, amount, observed_currency=price["currency"], evidence_rung, canonical_url=kb.canonical_offer_url(final_url or url), captured_at=now, size_ml, in_stock)`; the variant / product rows through `build_variant_row` / `build_product_row` only when the product row exists (never a new identity minted from a page: L5); `price.get("image_url")` passing `jsonld_widen.allowed_image_url` -> `build_image_row(source="retailer_jsonld")`. Every write through `KbWriter` (insert-ignore). Which gap fields count as filled: price (an offer row built), image (an image row built), size (size_ml on the variant), concentration (the pid's concentration axis non-"-"), rating / review_count (only when the extraction carried the D08 rating; else not filled, L6).

#### 2.6 Log lines (constants, hosts and ints only)
`[KB_ENRICH] mode=<m> gap_fill=<0|1> web_search=<0|1>`; per product `[KB_ENRICH] product step=<search|pdp_hint|refresh> host=<host> outcome=<filled|empty|refused:<reason>|error:<Type>>` (no URL path, no name); one totals line `[KB_ENRICH] totals gaps=.. filled=.. closed=.. needs_operator=.. licence=.. hints_closed=.. locked=.. lock_unavailable=.. refresh_fetched=.. refresh_written=.. refused=.. web_search_not_built=..`.

#### 2.7 Failure table
| input | outcome |
|---|---|
| mode off / garbage | one INFO, exit 0, no import of app |
| client None | exit 0 |
| kb_gaps / kb_merchants read raises | one WARNING, the leg ends, exit 0 |
| Redis None / set raises | the product skipped (`lock_unavailable`) |
| lock held | skipped (`locked`) |
| gate refusal | counted by reason; blocked / tos -> needs_operator per 2.3 |
| fetch timeout (4 s) / non-2xx | counted; the gap stays open, the hint stays queued |
| extraction None / identity mismatch | `empty`; nothing written |
| builder None | `not_built` (KbWriter count) |
| web-search sub-flag ON | one `not_built` line; no call |

#### 2.8 Flag-OFF identity
OFF: `main` returns 0 after one env read and one INFO line: no app import (asserted with `sys.modules` before / after), no client, no Redis. The worker is a new service: nothing at base runs it.

### 3. Change list (GREEN, first after D17)
- C1 NEW `scripts/cron_kb_enrich.py` (LF, ASCII; imports `scripts.kb_seed_common as common` at top, everything else lazily; no `kb_*` relation literal: the constants by import).
- C2 NEW `railway.kbenrich.json`: `{"$schema": "https://railway.com/railway.schema.json", "build": {"watchPatterns": ["scripts/cron_kb_enrich.py", "scripts/kb_seed_common.py", "railway.kbenrich.json"]}, "deploy": {"startCommand": "python -m scripts.cron_kb_enrich", "restartPolicyType": "NEVER"}}`.
- No other file.

### 4. Existing pins
#### 4.1 Deliberate changes
None (no P01 / P02 row: 2.1).
#### 4.2 Must stay green and unedited
`tests/test_s81_d11_pdp_discovery.py` (the hint contract R-G2-13), `tests/test_s81_s16_kb_seed.py`, `tests/test_s81_d09_feed_walker.py`, `tests/test_s81_kb_schema.py` P01 / P02 (unchanged for this unit), `tests/test_s81_s04_spend_breaker.py`, the S81-15 p5 (scripts are outside app/).

### 5. RED tests: `tests/test_s81_s19_gap_queue.py` (new; pure ASCII; hermetic; the Supabase client an in-memory recorder (table / select / eq / gte / in_ / like / order / limit / range / upsert(on_conflict, ignore_duplicates) / update / execute) with seeded rows; Redis a fake with `set(key, value, nx=, ex=)` / `get` / `delete` recording calls; `PoliteFetcher` replaced by a fake whose `get` records (url, timeout, require_tos) and returns configured `FetchResult`s; `extract_price_from_html` a recorder; the breaker functions RAISING recorders; `common._now` fixed; every missing symbol through a find_spec helper)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_entry_exists_and_mode` | `scripts.cron_kb_enrich` importable; `enrich_mode()` off / dry / apply over the G2 matrix; `gap_fill_enabled()` / `web_search_requested()` house booleans | RED | C1 |
| R2 | `test_r2_off_is_inert` | mode off: exit 0, one INFO line, no client call, no Redis call, no `app.` module newly in `sys.modules` | RED | C1 |
| R3 | `test_r3_dry_reads_only` | dry: the ranked queue and the plan printed (JSON report via `--report`), zero fetches, zero Redis commands, zero upsert / update / insert | RED | C1 |
| R4 | `test_r4_rank_and_window` | open rows ranked by demand then last_seen; rows older than the window and `pdp_` fields excluded; at most the knob | RED | C1 |
| R5 | `test_r5_single_flight` | `set("kbenrich:sf:<32 hex>", run_id, nx=True, ex=900)` before any fetch of the product; False -> no fetch, `locked` counted; Redis None -> `lock_unavailable`, no fetch | RED | C1 |
| R6 | `test_r6_specs_gap_goes_licence` | a `specs` gap: one CAS update to `licence` (`.eq("state", "open")`), no fetch for it | RED | C1 |
| R7 | `test_r7_step1_search_template_polite` | search URL = template with the quoted query; fetch through the fake with `require_tos=True`, `timeout=4.0`; then the PDP candidate fetched; an offer row built through `build_offer_row` and sent by `KbWriter`; the price gap CAS-moved to `closed` | RED | C1 |
| R8 | `test_r8_step2_pdp_hint_consumed` | a queued `pdp_<16 hex>` hint for the product: fetched; the hint -> `closed` after a 2xx; -> `needs_operator` on a `tos` refusal; stays `queued` on a timeout | RED | C1 |
| R9 | `test_r9_step3_inert` | `ENABLE_KB_GAP_WEB_SEARCH` ON: exactly one `step=web_search status=not_built` line per run; no import of `llm_router` / `llm_provider` / `anthropic`; the breaker recorders never fire | RED | C1 |
| R10 | `test_r10_step4_blocked_to_operator` | every host refused `not_live` on a blocked row -> the gap `open -> needs_operator` | RED | C1 |
| R11 | `test_r11_cas_never_moves_demand_or_hint` | every gap update payload is exactly `{"state": <new>}` filtered on product_key, field and the old state; a lost CAS counted, not retried | RED | C1 |
| R12 | `test_r12_refresh_head_daily_tail_weekly` | head = top-N by summed demand; tail only on the configured weekday; each offer URL fetched with timeout 4.0 and require_tos; a same-amount re-observation = one update of `KB_OFFER_UPSERT_SET`; no adapter / render module imported | RED | C1 |
| R13 | `test_r13_log_lines_constants_only` | every `[KB_ENRICH]` line matches its template; no URL path, no name, no query | RED | C1 |
| R14 | `test_r14_railway_config` | `railway.kbenrich.json` parses; watchPatterns, startCommand, restartPolicyType NEVER as C2 | RED | C2 |
| R15 | `test_r15_hygiene` | the script and the config are LF and pure ASCII (the r27 rule) | RED | C1 + C2 |
| P1 | `test_p1_pdp_discovery_contract_unchanged` | `cron_pdp_discovery.gap_field` / `gap_rows` produce the R-G2-13 row shape (state queued, demand 0, canonical hint) | PIN | base |
| P2 | `test_p2_url_gate_tos_equals_verdict_plus_tos` | over a matrix of rows / URLs: `common.url_gate(row, url, now, require_tos=True)` is None iff `live_robots.url_verdict(url, row, now)` is None and `row.tos.verdict == "allowed"` | PIN | base |

### 6. Mutation table
| id | mutant | killed by |
|---|---|---|
| S19-M1 | mode read after the client resolve | R2 |
| S19-M2 | DRY performs a fetch | R3 |
| S19-M3 | `nx=True` dropped | R5 |
| S19-M4 | lock failure falls through to fetch | R5 |
| S19-M5 | `require_tos=False` | R7, R12 |
| S19-M6 | timeout 20.0 | R7, R12 |
| S19-M7 | `specs` fetched instead of licence | R6 |
| S19-M8 | hint closed on a timeout | R8 |
| S19-M9 | CAS payload carries `demand_count` | R11 |
| S19-M10 | the web-search sub-flag imports `llm_router` | R9 |
| S19-M11 | `pdp_` rows ranked as demand | R4 |
| S19-M12 | tail runs daily | R12 |

### 7. Comm set, gates
7.1 the group set (12.1); this unit edits no existing module. 7.2 gates: py_compile, ruff, the RED file, `tests/test_s81_d11_pdp_discovery.py tests/test_s81_s16_kb_seed.py tests/test_s81_d09_feed_walker.py`, json.loads of the config, the byte checks. 7.3 no client fence literal moves.

### 8. CLAUDE.md row and owner steps
- `ENABLE_KB_ENRICH_WORKER` (mode: unset / garbage OFF, true / 1 / yes / on DRY RUN, `apply` WRITE; `--dry-run` downgrades) + `ENABLE_KB_GAP_FILL` + the INERT `ENABLE_KB_GAP_WEB_SEARCH` + knobs `KB_ENRICH_MAX_GAPS` (200), `KB_ENRICH_HOSTS_PER_GAP` (3), `KB_ENRICH_HEAD_N` (50), `KB_ENRICH_TAIL_MAX` (500), `KB_ENRICH_TAIL_WEEKDAY` (7), `KB_ENRICH_DEMAND_DAYS` (7), `KB_ENRICH_FETCH_TIMEOUT_SECONDS` (4.0, max 4), `KB_ENRICH_LOCK_SECONDS` (900) (S81-19 GAP-QUEUE, `scripts/cron_kb_enrich.py`, service config `railway.kbenrich.json`, the warmer pattern). APPLY nightly: the open non-`pdp_` kb_gaps of the last 7 days ranked by demand_count then last_seen (a PROXY for the plan's distinct-compare demand until S81-22) walk the ladder per product under a Redis single flight (`SET kbenrich:sf:<hash> NX EX`; no Redis = the product skipped): `specs` -> `licence` (never fetched); other fields: (1) the registry search template of live, ToS-allowed hosts, (2) the G2 `pdp_` hints of the product (queued -> closed after a 2xx; -> needs_operator on a blocked / ToS refusal), (3) web search NOT BUILT (the sub-flag only logs `not_built`; S81-21), (4) blocked / ToS-refused everywhere -> `needs_operator`; a filled field -> `closed` (one state CAS per gap; demand / hint never move). Fetches are QarenBot `PoliteFetcher(require_tos=True)` with the persisted robots verdict, 4 s, no fallback adapter, no render tier; rows only through the S81-14 builders (insert-ignore). The price refresh: the most-demanded `KB_ENRICH_HEAD_N` products daily, the tail weekly, re-fetching each stored canonical URL and writing a new observation (same amount = last_seen moves). No LLM call: the off-clock lane cap is printed in DRY, the breaker is not called. DRY prints the queue, the plan and the bound; reads only.
- Owner steps: (1) 045 applied; (2) the robots cron covering the live hosts and the ToS verdicts recorded (no ToS = no fetch); (3) create the `kb-enrich` Railway service from `railway.kbenrich.json` with the service-role and Upstash variable NAMES (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`) and a nightly cron schedule; (4) one DRY run (`ENABLE_KB_ENRICH_WORKER=true`, `ENABLE_KB_GAP_FILL=true`), read the report; (5) then `apply`; canary items: the totals line per run, kb_gaps state counts (D17), the refresh written count.

### 9. Stated limits
- S81-19-L1: demand = demand_count + last_seen within 7 days (compare_runs, S81-22, not built).
- L2: the web-search step is inert (S81-21).
- L3: the search-template step parses the Shopify suggest JSON shape and same-host anchors only; other storefront search pages yield `empty`.
- L4: a lock whose owner check loses a race expires by TTL (no Lua compare-and-delete: the Lua class stays out of the group).
- L5: the worker never mints a new product identity from a page; it fills products that exist (G3 / G2 / D16 create them).
- L6: rating / review_count fill only when the extraction carries the D08 rating; otherwise the gap stays open.
- L7: `specs` gaps go to `licence` wholesale (the D05 `specs` field is not split per spec field).
- L8: the hint state `fetched` of the brief is not a 045 state: a fetched hint is `closed` (no migration).

### 10. Out of scope
`S78 fix 6` (reserve the verdict tail) belongs to the request path (not this unit); the interim `ENABLE_TIER_FILL_RESIDUAL_GUARD` flip is an owner step the PR body names; the Haiku web_search step (S81-21); the CDX leg itself (G2's sub-flag).

### 11. Open questions
- Q5 scripts-only placement (no `app/services/kb_gap_ladder.py`) for G4.
- Q6 `specs` -> `licence` wholesale vs a per-spec-field split (needs a D05 vocabulary change).
- Q7 the single flight fail-closed when Redis is absent (vs fail-open for a one-process cron).

## Unit D16 OPERATOR-INGEST

### 1. Base state (measured at 0b19de5b)
- `app/api/admin_routes.py`: `router = APIRouter(tags=["admin"])` :36; `verify_admin_key(x_admin_key: str = Header(default=""))` :40-66 (bytes `hmac.compare_digest`, 403 `Invalid admin key`, blank key = unset); every route `@router.get(...)` + `@limiter.limit("30/minute")` + `request: Request` + `_=Depends(verify_admin_key)` (e.g. :70-78); NO POST route exists (measured: zero `@router.post` / `@router.put`); imports `run_db` :24, `get_admin_supabase_client` :19.
- `app/main.py:468` `app.include_router(admin_router, prefix="/api/v1/admin")`; the gated static mount `/admin` :479-572 (`_AdminAuthenticatedStaticFiles`, X-Admin-Key or Basic); exception handlers :171-173 register `fastapi.HTTPException` (:6) -> `error_handler.http_exception_handler` :160 (the `{success, error, code, request_id}` envelope; `STATUS_CODE_MAP` :24-35) and `RequestValidationError`; an unknown path is Starlette's router 404, a `starlette.exceptions.HTTPException` (the base class, NOT caught by the app's subclass handler) rendered by FastAPI's default handler as `{"detail": "Not Found"}`. CORS `allow_origins=ALLOWED_ORIGINS` (:125-128): a bookmarklet POSTing from a merchant origin would be refused by CORS, so D16's bookmarklet never posts (2.5).
- OpenAPI pins are per path (`tests/test_w4_13_measurement_truth.py:1852-1860`, `tests/test_s81_s05_request_context.py:1443`, `tests/test_flush_live_price_key.py:543`); no fixture lists `/api/v1/admin` paths (measured grep of `tests/fixtures`: zero hits). The brief's "T23 fixture" is satisfied by `include_in_schema=False` (the published schema does not change; P2 pins the sorted path set's sha at base).
- Registry columns: `kb_merchants.tos` jsonb (045 :120), `status` / `blocked_reason` :122-123 (blocked needs a reason :130-131); `robots` jsonb with `fetched_at` / `state` (S81-15 record); the G2 ToS reading `tos.verdict == "allowed"` (`kb_seed_common.py:272-275`, `cron_feed_walker.py:380-382`); `reviewed_at` is the S81-15 record key `tos {reviewed_at, verdict, terms_url}` (PLAN_S81 S81-15 text).
- The kb writer helpers: `kb_ingest._insert_ignore` :317-324 and `_offer_rows_changed` :327-341 (module attributes), the builders (S81-14).
- Base pass: `tests/test_admin_key_and_sentry_scrub.py` green (header run).

### 2. Contract
#### 2.1 Flag and knob
`ENABLE_OPERATOR_INGEST`; `KB_OPERATOR_PAGE_MAX` (50, 1..200).
#### 2.2 `app/services/kb_operator.py` (stdlib + pydantic at top; kb_service via `kb_leaf()`; merchant_registry / kb_ingest / deny_hosts / database_service lazily)
- `KB_SPECS_TABLE = "kb_specs"`, `KB_COVERAGE_TABLE = "kb_coverage_daily"` (E2 lines); the other table names from `kb_ingest` by attribute.
- `operator_ingest_enabled()`, `page_max()`, `kb_leaf()` (E1), seams `_now()`, `_admin_client()`.
- `operator_gate()`: a FastAPI dependency; `if not operator_ingest_enabled(): raise starlette.exceptions.HTTPException(status_code=404)` (the base class: rendered exactly like an unregistered path); else returns None.
- Models (pydantic v2, `model_config = ConfigDict(extra="forbid")`): `OperatorPrice {amount: float (gt 0, lt 1e11), currency: str (pattern ^[A-Z]{3}$)}`; `OperatorIngest {source: Literal["operator", "partner"] = "operator", page_url: str (max 2048), brand: Optional[str] (1..128), name: Optional[str] (1..256), variant: Optional[str] (1..64), jsonld: List[Dict[str, Any]] (max 20 items), og_image: Optional[str] (max 2048), price: Optional[OperatorPrice], market: str = "BH" (pattern ^[A-Z]{2,3}$), size_ml: Optional[int] (1..9999), in_stock: Optional[bool], captured_at: Optional[datetime], specs: Dict[str, str] (max 32 keys; each key the KB field regex, each value 1..2000)}`; the handler refuses a body whose `json.dumps` exceeds 262,144 bytes.
- `read_view(client, limit) -> dict` (sync, run through `run_db`): `{"blocked": [{host, status, blocked_reason, robots_state, robots_fetched_at, tos_verdict, tos_reviewed_at}], "needs_operator": [{product_key, field, demand_count, last_seen, source_hint}], "coverage": {"day": <date or None>, "metrics": [{metric, value, n}]}, "limit": <n>}`; blocked = kb_merchants `select("host,status,blocked_reason,robots,tos").eq("status", "blocked").order("host").limit(n)`; needs_operator = kb_gaps `.eq("state", "needs_operator").order("demand_count", desc=True).order("last_seen", desc=True).limit(n)`; coverage = the latest `day` of kb_coverage_daily then its rows (at most 200). No user id, no device, no personal field exists in these tables.
- `ingest(client, body, now) -> dict` (sync, through `run_db`): (1) URL: `canonical = kb.canonical_offer_url(body.page_url)`; None, `not kb.kb_source_allowed(canonical)` or `deny_hosts.is_denied_url(body.page_url)` -> refuse `KB_URL_REFUSED`. (2) Row: the registry row of the host (exact, else the longest parent; one select of `host,status,deny,tos`); none -> `KB_HOST_UNKNOWN`; `deny` -> `KB_URL_REFUSED`; status `candidate` -> `KB_HOST_CANDIDATE`; status `blocked` without a non-empty `tos.reviewed_at` -> `KB_HOST_NOT_REVIEWED`; live -> accepted. (3) Identity: `body.brand` / `body.name` when both given (manual entry) else the first JSON-LD node whose `@type` is or contains `Product` (`brand` str or `brand.name`, `name`); `pid = kb.kb_product_id(brand, name, variant)`; None -> `KB_IDENTITY_UNRESOLVED`. (4) Rows through the builders (insert-ignore with `kb_ingest._insert_ignore`, the offer re-observation with `_offer_rows_changed`): product (`identity_confidence "high"`: an operator-verified identity; concentration from the pid axis), variant (`size_ml`), offer (when `price`: `evidence_rung "operator"`, `merchant_id` the row host, `market`, `canonical_url`, `captured_at = body.captured_at or now`, `in_stock`), image (when `og_image` https: `source "operator"`, `provenance_host` the row host), specs (each `specs` entry: `extractor "operator"`, `source_url = canonical`, `cited True`, lang en). Never kb_reviews, kb_feedback, kb_merchants. (5) Gaps: for the fields filled (price, image, size, concentration, specs) ONE `update({"state": "closed"}).eq("product_key", pid).in_("field", filled).in_("state", ["open", "needs_operator"])` (never `pdp_` hints, never demand). (6) ONE INFO `[KB_OPERATOR] ingest source=<operator|partner> host=<host> products=%d variants=%d offers=%d images=%d specs=%d gaps_closed=%d not_built=%d`. Returns those counts.
#### 2.3 The routes (admin_routes.py; import `from app.services import kb_operator`)
- `@router.get("/kb/operator", include_in_schema=False)` `@limiter.limit("30/minute")` `async def kb_operator_view(request: Request, _gate=Depends(kb_operator.operator_gate), _=Depends(verify_admin_key))`: `limit` read from `request.query_params.get("limit")` (int, clamped 1..`page_max()`, garbage -> `page_max()`; no declared Query param, so no validation precedes the gate); returns `{"success": True, **view}`.
- `@router.post("/kb/ingest", include_in_schema=False)` `@limiter.limit("30/minute")` `async def kb_operator_ingest(request: Request, body: kb_operator.OperatorIngest, _gate=Depends(kb_operator.operator_gate), _=Depends(verify_admin_key))`: returns `{"success": True, "written": counts}`; a refusal raises `HTTPException(status_code=400, detail={"code": <KB_*>, "error": <constant text>})` (the structured-detail unwrap :168-172 puts the code on the envelope); a client None -> 503 is FORBIDDEN (never a bare 503): it returns 400 `KB_STORE_UNAVAILABLE`.
- The gate is the FIRST declared dependency: FastAPI solves sub-dependencies in declaration order before params and body, so with the flag OFF neither the admin key, the body nor the limiter body runs (the decorator wraps the endpoint, which is never called). No new header, key, rate rule, static file or mount.
#### 2.4 Flag-OFF identity
OFF: both paths answer exactly what an unregistered path answers (status 404, body `{"detail":"Not Found"}`, the same header set modulo the per-request id), proven by P1 against the never-registered sibling `/api/v1/admin/kb/__absent__` in the same run; the OpenAPI document byte-identical (P2). Stated limit L1: another METHOD on the two paths (e.g. GET `/kb/ingest`) answers 405 where base answers 404 (the router matches the path; no client calls these paths).
#### 2.5 The bookmarklet (docs only)
`docs/runbooks/2026-11-kb-operator-ingest.md`: a `javascript:` snippet the operator runs in their OWN browser on a merchant page; it collects `location.href`, every `script[type="application/ld+json"]` parsed, `meta[property="og:image"]`, and copies ONE JSON object of the 2.2 shape to the clipboard (never a network call: CORS would refuse it and no key enters a page); the operator posts it with the documented curl template (`-H "X-Admin-Key: $ADMIN_API_KEY"`, the variable NAME only) or from a terminal. Names only; no host list, no personal value.
#### 2.6 Failure table (flag ON)
| input | outcome |
|---|---|
| no / wrong admin key | 403 `Invalid admin key` (verify_admin_key unchanged) |
| > 30 / min | the existing limiter 429 |
| extra key / bad currency / 21 JSON-LD items | 422 (the house validation envelope) |
| body > 256 KB | 400 `KB_PAYLOAD_TOO_LARGE` |
| URL denied / not canonical | 400 `KB_URL_REFUSED` |
| host not in the registry | 400 `KB_HOST_UNKNOWN` |
| candidate host | 400 `KB_HOST_CANDIDATE` |
| blocked host without `tos.reviewed_at` | 400 `KB_HOST_NOT_REVIEWED` |
| identity unresolved / placeholder | 400 `KB_IDENTITY_UNRESOLVED` |
| builder None for a row | counted `not_built`; the rest written |
| client None | 400 `KB_STORE_UNAVAILABLE` |
| a write raises | 400 `KB_STORE_UNAVAILABLE` + one WARNING (type name) |

### 3. Change list (GREEN, after S81-19)
- C1 NEW `app/services/kb_operator.py`. C2 EDIT `app/api/admin_routes.py` (one import, two routes appended after `/costs/gauges` :1255; CRLF kept). C3 NEW `docs/runbooks/2026-11-kb-operator-ingest.md`. No other file (E-rows shared).

### 4. Existing pins
#### 4.1 Deliberate changes
- E1 (shared): P01_ALLOWED gains `("app/services/kb_operator.py", "from app.services import kb_service as _kb")`, P01_FUNCTIONS `"app/services/kb_operator.py": "kb_leaf"`.
- E2 (shared): P02_ALLOWED gains `("app/services/kb_operator.py", 'KB_SPECS_TABLE = "kb_specs"')` and `("app/services/kb_operator.py", 'KB_COVERAGE_TABLE = "kb_coverage_daily"')`.
#### 4.2 Must stay green
`tests/test_admin_key_and_sentry_scrub.py`, `tests/test_admin_referral_endpoints.py`, `tests/test_cost_dashboard.py`, `tests/test_analytics.py`, `tests/test_be_harness.py`, `tests/test_m13_21_openapi_gated.py`, the per-path OpenAPI pins (1), the S81-15 p5 (no `robots_registry` text in kb_operator.py), every app.main importer in the comm set.

### 5. RED tests: `tests/test_s81_d16_operator_ingest.py` (new; pure ASCII; hermetic; `app.main` imported FIRST (the dotenv guard), then `monkeypatch.setenv("ADMIN_API_KEY", secrets.token_hex(32))`; the TestClient over `app.main.app`; the service-role client an in-memory recorder through the `kb_operator._admin_client` seam; registry rows seeded in the recorder)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_module_flag_knob` | module importable; the flag matrix; `page_max` defensive | RED | C1 |
| R2 | `test_r2_view_requires_key_when_on` | ON: no key -> 403; key -> 200 `success true` with `blocked`, `needs_operator`, `coverage`, `limit` | RED | C1 + C2 |
| R3 | `test_r3_view_content_and_bounds` | the blocked projection keys exactly; needs_operator ordered by demand then last_seen; `?limit=999` -> clamped to the knob; no personal field anywhere in the body | RED | C1 + C2 |
| R4 | `test_r4_ingest_happy_path_operator` | live host: product / variant / offer (rung operator) / image (source operator) / specs (cited, source_url canonical) built through the builders and upserted with `ignore_duplicates=True`; the matching open + needs_operator gaps CAS-closed; `pdp_` hints untouched | RED | C1 + C2 |
| R5 | `test_r5_blocked_host_needs_review` | blocked host without `tos.reviewed_at` -> 400 envelope code `KB_HOST_NOT_REVIEWED`, zero writes; with it -> accepted | RED | C1 + C2 |
| R6 | `test_r6_refusal_codes` | candidate / unknown / denied (a DENY_HOSTS URL built at run time) / placeholder identity / oversize -> the 2.6 codes, zero writes | RED | C1 + C2 |
| R7 | `test_r7_validation` | extra key, bad currency, 21 JSON-LD items -> 422; never 500 | RED | C2 |
| R8 | `test_r8_partner_source` | `source "partner"` writes the same rows and logs `source=partner` | RED | C1 |
| R9 | `test_r9_log_line_constants` | one `[KB_OPERATOR] ingest` line: host + ints only; no URL path, no name | RED | C1 |
| R10 | `test_r10_runbook_names_only` | the runbook exists; contains `javascript:`, `navigator.clipboard`, `X-Admin-Key`, `ADMIN_API_KEY`; contains no `fetch(` / `XMLHttpRequest` in the snippet, no 64-hex run, no `@` email shape | RED | C3 |
| P1 | `test_p1_flag_off_equals_unregistered_path` | FULL configuration (flag OFF, knob set, a valid admin key sent, a valid body): GET `/api/v1/admin/kb/operator` and POST `/api/v1/admin/kb/ingest` -> status, JSON body and header names equal to the same request on `/api/v1/admin/kb/__absent__` (x-request-id value excluded); the client recorder sees no call; `verify_admin_key` (wrapped recorder) never runs | PIN | base |
| P2 | `test_p2_openapi_unchanged` | `sorted(app.openapi()["paths"])` sha256 == the literal recorded at base by RED (schema rebuilt with `app.openapi_schema = None`, restored after) | PIN | base |
| P3 | `test_p3_existing_admin_routes_unchanged` | `/api/v1/admin/stats/daily` without a key -> 403 envelope unchanged with the flag ON and OFF | PIN | base |

### 6. Mutation table
| id | mutant | killed by |
|---|---|---|
| D16-M1 | gate raises `fastapi.HTTPException(404)` (the subclass: the house envelope) | P1 |
| D16-M2 | gate declared after `verify_admin_key` | P1 |
| D16-M3 | `include_in_schema` dropped | P2 |
| D16-M4 | the `tos.reviewed_at` check removed | R5 |
| D16-M5 | candidate hosts accepted | R6 |
| D16-M6 | gap close drops the state filter (closes `pdp_` / closed rows) | R4 |
| D16-M7 | `ignore_duplicates=False` | R4 |
| D16-M8 | limit not clamped | R3 |
| D16-M9 | the identity check skipped (placeholder accepted) | R6 |

### 7. Comm set, gates
7.1 the group set (12.1): the importers of admin_routes and app.main. 7.2 py_compile, ruff, the RED file, `tests/test_admin_key_and_sentry_scrub.py tests/test_admin_referral_endpoints.py tests/test_cost_dashboard.py tests/test_m13_21_openapi_gated.py tests/test_s81_kb_schema.py`. 7.3 no fence literal moves.

### 8. CLAUDE.md row and owner steps
- `ENABLE_OPERATOR_INGEST` + knob `KB_OPERATOR_PAGE_MAX` (50, 1..200) (D16 OPERATOR-INGEST, `app/services/kb_operator.py` + two routes in `app/api/admin_routes.py` under the EXISTING `verify_admin_key` dependency and the existing 30/min limiter; no new header, key, rate rule or mount; both routes `include_in_schema=False`). OFF: `GET /api/v1/admin/kb/operator` and `POST /api/v1/admin/kb/ingest` answer exactly as an unregistered path (404 `{"detail": "Not Found"}`; another method answers 405, D16-L1). ON: the view returns the blocked registry hosts (host, status, blocked_reason, robots state / fetched_at, ToS verdict / reviewed_at), the `needs_operator` gaps by demand, and D17's latest coverage day (page size clamped); the ingest takes a captured payload (page_url, the page's JSON-LD, og:image, a price {amount, currency}, size, stock, captured_at, manual specs; `source` operator or partner; extra keys refused; 256 KB cap) for a registry host that is live, or blocked WITH `tos.reviewed_at`; refusals are 400 with codes `KB_URL_REFUSED`, `KB_HOST_UNKNOWN`, `KB_HOST_CANDIDATE`, `KB_HOST_NOT_REVIEWED`, `KB_IDENTITY_UNRESOLVED`, `KB_PAYLOAD_TOO_LARGE`, `KB_STORE_UNAVAILABLE`; rows only through the S81-14 builders (identity high, offer rung operator, image source operator, specs cited to the page), then the matching open / needs_operator gaps closed. The bookmarklet (docs/runbooks/2026-11-kb-operator-ingest.md) only copies the payload to the clipboard; the operator posts it with curl.
- Owner steps: (1) 045 applied; (2) D17 running (the view's coverage block); (3) the ToS review recorded on each blocked host the operator will capture; (4) `ENABLE_OPERATOR_INGEST` ON on `web`; canary: the `[KB_OPERATOR]` lines, the needs_operator queue size (the view), the 4xx codes.

### 9. Stated limits
- D16-L1: a wrong METHOD on the two paths answers 405 with the flag OFF (base 404).
- L2: no HTML page in G4 (curl only); a page under the existing gated mount is a follow-up.
- L3: operator identities are written `high` (operator-verified).
- L4: kb_reviews are never written by the operator path.
- L5: the view's coverage block is empty until D17 runs (the key is present with `day: null`).

### 10. Out of scope
New auth, a new key, a new rate rule, CORS, a static page; partner feed automation; Smart fallback / Tier 2 / Tier 3 leaving the request path.

### 11. Open questions
- Q8 starlette base-class 404 for the OFF identity (vs the house envelope 404, which would differ from an unregistered path).
- Q9 live hosts accepted without a `tos.reviewed_at` (their ToS passed at candidate -> live) vs requiring it for every host.

## Unit D17 MEASURE-COVERAGE

### 1. Base state (measured at 0b19de5b)
- `kb_coverage_daily (day date, metric text CHECK ^[a-z][a-z0-9_.:-]{0,127}$, value numeric, n integer >= 0, PRIMARY KEY (day, metric))` (045 :311-317); `kb_service.build_coverage_row(*, day, metric, value, n)` :786-806 (date not datetime; finite numeric; returns `{"day": str(day), "metric", "value": str(num), "n"}`); `KB_METRIC_REGEX` :130.
- Sources: kb_products (id, identity_confidence, concentration), kb_variants (product_id, size_ml), kb_offers (latest per key; `last_seen`, `captured_at`), kb_images (product_id), kb_specs (product_id, field, cited), kb_reviews (product_id), kb_gaps (field, state). `search_logs` (`migrations/002_search_logs_and_products.sql:5-16`: id, user_id, query, input_type, products_found jsonb, success, error_message, cost, duration_ms, created_at; `042` adds `is_synthetic`); the writer `database_service.py:775-799` (products_found = the product NAMES list). compare_runs does not exist (S81-22).
- The `kbh:` counters: `live_robots._flush_sync` :434-459: key `"kbh:" + <UTC %Y%m%d> + ":" + host`, hash field `<source>:<outcome>`, outcomes `ok / fail / robots_skip / challenge` (:58), present only under `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH`. Pinned upstash `hgetall(key)` and `pipeline()` (measured signatures).
- Base pass: n/a (new script); `tests/test_s81_kb_schema.py` green.

### 2. Contract
#### 2.1 The run
`scripts/cron_kb_coverage.py`: `main(argv=None, client=None, redis=None) -> int`; `coverage_mode()` = `common.run_mode("ENABLE_KB_COVERAGE_ROLLUP")` FIRST (OFF -> one INFO, exit 0, nothing imported); args `--day YYYY-MM-DD` (default: yesterday UTC), `--report <path>` (markdown), `--dry-run`; reads only through the service-role client (paged, `common.PAGE_SIZE` / `MAX_PAGES`); DRY prints every metric line and writes the report, never the DB; APPLY additionally ONE upsert of all rows `client.table(KB_COVERAGE_TABLE).upsert(rows, on_conflict="day,metric").execute()` (idempotent per (day, metric): a re-run replaces). Constants: `KB_COVERAGE_TABLE = "kb_coverage_daily"`, `KB_OFFERS_LATEST_VIEW = "kb_offers_latest"` (E2 lines); the other kb names from `common` / `kb_ingest`.
#### 2.2 The closed metric list (Q8; every name matches KB_METRIC_REGEX; value / n)
| metric | value | n |
|---|---|---|
| `kb.products.total` | count of kb_products | same |
| `kb.products.identity_high_share` | share with identity high (4 dp) | products |
| `kb.field.offer_share` / `kb.field.offer_fresh_share` | products with >= 1 latest offer / with one whose last_seen is within 7 d | products |
| `kb.field.image_share` / `kb.field.specs_cited_share` / `kb.field.rating_share` / `kb.field.size_share` / `kb.field.concentration_share` | per-product presence (specs_cited = the S81-18 required set all cited) | products |
| `kb.field.complete_share` | products with fresh offer + image + required cited specs + size + concentration | products |
| `kb.price.age_median_hours` | median hours since `last_seen` of the latest offers | offers |
| `kb.price.capture_age_median_hours` | median hours since `captured_at` | offers |
| `kb.gaps.state.<open, queued, needs_operator, licence, closed>` | non-`pdp_` gap rows per state | same |
| `kb.hints.state.<queued, closed, needs_operator>` | `pdp_` rows per state | same |
| `proxy.identity_hit_share` | share of the day's names (search_logs success, `is_synthetic` not true) that normalize to a kb_products `brand name` or `name` | names |
| `proxy.pair_hit_share` | share of the day's rows with exactly two names both matched | such rows |
| `host.robots_skip:<host>` / `host.challenge:<host>` | the summed `*:robots_skip` / `*:challenge` fields of `kbh:<day>:<host>` | the summed attempts of that key |
A host metric exists only when its key exists (absent never zero); hosts are the live + blocked registry hosts (at most `KB_COVERAGE_MAX_HOSTS`, one pipeline of HGETALL); a metric name over 128 chars is skipped and counted. Normalization for the proxy: casefold, non-alphanumerics to spaces, collapse spaces. search_logs is read with `select("products_found,success,is_synthetic,created_at")` only: never `user_id`, `query` or `error_message`. Pair-level completeness and the true identity / pair hit rates need compare_runs (S81-22): stated L1.
#### 2.3 The report
Markdown to `--report`: the day, a table metric / value / n in the 2.2 order, the proxy disclaimer line; names and numbers only (host names are registry hosts, not personal data).
#### 2.4 Log lines
`[KB_COVERAGE] mode=<m> day=<YYYY-MM-DD>`; `[KB_COVERAGE] metric=<name> value=<num> n=<int>` per metric; `[KB_COVERAGE] totals rows=%d not_built=%d skipped_long=%d redis=<0|1>`.
#### 2.5 Failure table
| input | outcome |
|---|---|
| off | one INFO, exit 0 |
| a table read raises | that metric family omitted, one WARNING (type), the rest written |
| search_logs unreadable | the proxy metrics omitted |
| Redis None / raises | no host metrics, `redis=0` |
| builder None | `not_built`, row not sent |
| upsert raises | one WARNING, exit 0 |
#### 2.6 Flag-OFF identity
OFF: one env read and one INFO line; nothing imported or read. A new service: nothing at base runs it.

### 3. Change list (GREEN, FIRST)
- C1 NEW `scripts/cron_kb_coverage.py` (LF, ASCII). C2 NEW `railway.kbcoverage.json` (`watchPatterns` `["scripts/cron_kb_coverage.py", "scripts/kb_seed_common.py", "railway.kbcoverage.json"]`, `startCommand` `python -m scripts.cron_kb_coverage`, `restartPolicyType` NEVER): a separate service (the spec decides: the coverage and enrich flags flip independently, each with its own schedule).

### 4. Existing pins
- E2 (shared): P02_ALLOWED gains `("scripts/cron_kb_coverage.py", 'KB_COVERAGE_TABLE = "kb_coverage_daily"')` and `("scripts/cron_kb_coverage.py", 'KB_OFFERS_LATEST_VIEW = "kb_offers_latest"')`. No P01 row (`common.kb_leaf`). Must stay green: `tests/test_s81_kb_schema.py`, `tests/test_s81_d14_live_robots.py` (the `kbh:` format is read, never written).

### 5. RED tests: `tests/test_s81_d17_coverage.py` (new; pure ASCII; hermetic; the client recorder with seeded kb_* and search_logs rows (synthetic names); Redis a fake with `pipeline().hgetall(...)` / `exec()`; `common._now` fixed)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_entry_and_mode` | importable; the mode matrix; OFF inert (no client call, no `app.` import) | RED | C1 |
| R2 | `test_r2_metric_names_closed_and_valid` | the emitted names are exactly the 2.2 list for the seeded data; each matches `KB_METRIC_REGEX` | RED | C1 |
| R3 | `test_r3_values_on_seeded_kb` | for a seeded KB of 4 products the shares, the two medians and the gap / hint counts equal hand-computed literals | RED | C1 |
| R4 | `test_r4_proxy_reads_no_personal_columns` | the search_logs select string is exactly `products_found,success,is_synthetic,created_at`; synthetic rows excluded; proxy values as hand-computed | RED | C1 |
| R5 | `test_r5_host_metrics_absent_never_zero` | a host with no `kbh:` key emits no metric; a key with `curl:robots_skip 3` + `woo:robots_skip 2` -> value 5 | RED | C1 |
| R6 | `test_r6_apply_upserts_through_builder` | APPLY: ONE upsert with `on_conflict="day,metric"`, every row equal to `build_coverage_row(...)`; DRY: no upsert | RED | C1 |
| R7 | `test_r7_report_markdown` | the report holds the day, the table and the proxy line; no 8-digit run, no `@` | RED | C1 |
| R8 | `test_r8_failure_isolation` | a raising kb_specs read omits only the specs-dependent metrics; Redis None -> `redis=0` | RED | C1 |
| R9 | `test_r9_railway_config_and_hygiene` | the config as C2; script + config LF and ASCII | RED | C1 + C2 |

### 6. Mutation table
| id | mutant | killed by |
|---|---|---|
| D17-M1 | `user_id` added to the search_logs select | R4 |
| D17-M2 | an absent host emitted as 0 | R5 |
| D17-M3 | `on_conflict` dropped (insert) | R6 |
| D17-M4 | DRY upserts | R6 |
| D17-M5 | median over captured_at for `age_median_hours` | R3 |
| D17-M6 | synthetic rows counted | R4 |

### 7. Comm set, gates
7.1 the group set. 7.2 py_compile, ruff, the RED file, `tests/test_s81_kb_schema.py`, json.loads of the config, byte checks.

### 8. CLAUDE.md row and owner steps
- `ENABLE_KB_COVERAGE_ROLLUP` (mode: OFF / DRY / `apply`) + knob `KB_COVERAGE_MAX_HOSTS` (500) (D17 MEASURE-COVERAGE, `scripts/cron_kb_coverage.py`, service config `railway.kbcoverage.json`). Daily for the previous UTC day: the closed metric list (kb.products.*, kb.field.*_share incl. complete_share, kb.price.age_median_hours from last_seen and capture_age_median_hours, kb.gaps.state.*, kb.hints.state.*, the PROXY identity / pair hit shares from search_logs names vs kb_products (columns products_found, success, is_synthetic, created_at only), host.robots_skip:<host> / host.challenge:<host> from the D14 `kbh:` counters when present, never zero when absent) upserted into kb_coverage_daily per (day, metric) through `build_coverage_row`; `--report` writes the weekly markdown (names and numbers only). DRY prints and writes the report, never the DB. The true pair / identity rates wait for compare_runs (S81-22).
- Owner steps: (1) 045 applied; (2) create the `kb-coverage` Railway service from `railway.kbcoverage.json` (service-role + Upstash variable NAMES; a daily cron); (3) one DRY run; (4) `apply`; (5) read the first week beside the R15 model with n.

### 9. Stated limits
- D17-L1: identity / pair hit rates are a search_logs PROXY (names, no compare_runs).
- L2: host counters exist only under `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH` (absent otherwise).
- L3: per-pair completeness is not computed (needs compare_runs).
- L4: the medians are computed client-side over paged reads (bounded by `MAX_PAGES` x `PAGE_SIZE` = 100,000 rows; beyond that the metric's n says so).

### 10. Out of scope
The fold of the `kbh:` counters into kb_merchants.health (D14b); compare_runs (S81-22).

### 11. Open questions
- Q10 a separate `kb-coverage` service (this spec) vs an entry of the enrich service.

## 12. The group

### 12.1 Combined comm set (the union rule)
Derivation (`<scratchpad>/g4spec/comm.py`, re-runnable: `python -I comm.py <worktree> <out> <stored G3 set>`): every `tests/test_*.py` / conftest.py whose text references any of `structured_comparison_service, product_data_service, extraction_service, scoring_service, kb_service, kb_ingest, live_robots, cache_service, llm_spend_breaker, admin_routes, admin_router, text_routes, image_routes, request_context, app.main, "app import main", kb_seed_common, merchant_registry, jsonld_widen, model_config, db_offload, kb_serve, kb_operator, cron_kb_enrich, cron_kb_coverage, "railway."` (431) UNION every test that reads source by path / module path / glob / ast / os.walk / `"app"` segments / `.github` / SmartCompareApp / CLAUDE.md / `"scripts/"` / openapi (265) UNION the stored G3 set `comm_final2.txt` (609, every member still present) MINUS the four `test_precommit_hook*.py` = **661 files**, list `<scratchpad>/g4spec/comm_set.txt`, sha256 `90b85603e5dbb51268a6221c22b5b18a2785c1b8572f25a455e6faf9eb18ee15`; the 52 members new vs G3 in `new_vs_g3.txt` (scoring / dimension / model-router / sync-db-offload / budget suites among them). It holds the CLAUDE.md readers (`test_ci_gates.py`, `test_behavior_dimension_translation.py`), `test_s81_kb_schema.py`, `test_secret_scan_static.py`, `test_hermeticity_pins.py`, the per-path OpenAPI pins, the admin suites, FY25, every G1 / G2 / G3 / S81-10 / S81-10b file. Plus the four new RED files at HEAD. LC-6: the RED agent builds the 0b19de5b record ONCE by per-file reuse of the stored 744616e3 record (`base_records/744616e3.../ba26af35....txt`) for every member that references none of the eight G3-edited modules (structured_comparison_service, price_service, shopify_pdp_service, woocommerce_service, algolia_service, url_extraction_service, kb_ingest, live_robots) nor CLAUDE.md / a glob walker, and RE-RUNS the rest (the `recompute.txt` split, computed in this run by grep: 439 files incl. the 52 new members, sha256 `23022997ad0cd974601ad800e1eaf686ee5404f7acc4d6cc776766cd182a1b07`; the other 222 members are reuse candidates under the R-G3-12 reuse rule recorded in the 744616e3 header) at 0b19de5b, stored under `base_records/0b19de5b.../<set-sha>.txt` with the [pyt] lines. Chunks of at most 25 files, bound 1200, base vs HEAD `comm -13` of the FAILED node ids EMPTY; the 5 environmental r27 rows appear on both sides.

### 12.2 CI-order set (one process, alphabetical, bound 1200)
`tests/test_s81_d16_operator_ingest.py tests/test_s81_d17_coverage.py tests/test_s81_s18_kb_first_serve.py tests/test_s81_s19_gap_queue.py tests/test_s81_kb_schema.py tests/test_s81_s17_kb_ingest.py tests/test_s81_g3_gate_rows.py tests/test_s81_d14_live_robots.py tests/test_s81_d11_pdp_discovery.py tests/test_s81_s16_kb_seed.py tests/test_s75_fanout_identity.py tests/test_admin_key_and_sentry_scrub.py tests/test_flush_live_price_key.py tests/test_w4_13_measurement_truth.py tests/test_s81_s05_request_context.py`, all flags OFF and again with the seven G4 flags ON (the two modes as `apply` is never set in a test env: DRY truthy).

### 12.3 Combined footprint
NEW (13): `app/services/kb_serve.py`, `app/services/kb_operator.py`, `scripts/cron_kb_enrich.py`, `scripts/cron_kb_coverage.py`, `railway.kbenrich.json`, `railway.kbcoverage.json`, `docs/runbooks/2026-11-kb-operator-ingest.md`, the four RED files, `tests/fixtures/s81_s18_flag_off_golden.json`, and nothing else new. EDITED (7): `app/services/structured_comparison_service.py`, `app/services/kb_ingest.py`, `app/api/text_routes.py`, `app/api/image_routes.py`, `app/api/admin_routes.py`, `tests/test_s81_kb_schema.py` (E1 / E2), `CLAUDE.md`. 20 files. No migration, no Lua, no middleware, no legal text, no client file, no requirements change, no new external host (Supabase, Upstash and the registry merchants exist; the web-search step is inert), no processors.json row.

### 12.4 Shared-file plan
0.3. The E-row edit (one hunk): P01_ALLOWED + P01_FUNCTIONS gain kb_serve and kb_operator; P02_ALLOWED gains the five exact lines (kb_serve 1, kb_operator 2, cron_kb_coverage 2). CLAUDE.md: one `**SESSION 81 flags (S81-G4 KB-SERVE: S81-18 + S81-19 + D16 + D17, ...)**` block after :556 with the four rows of the units' sections 8 and one owner-steps line; the `Feature Flags` paragraph at :341 gains one pointer sentence naming the G4 flags (the G3 precedent).

### 12.5 PR plan
ONE PR from `feature/s81-g4-kb-serve`, body at most 25,600 bytes (measured with python): summary; one short section per unit (defect id -> RED nodes -> flag -> preconditions); the E-rows (E1, E2); the counts; the stated limits by id; owner steps names only (apply 045 then 047 (item 29); `ENABLE_SYNC_DB_OFFLOAD` ON before `ENABLE_KB_FIRST_SERVE`; the KB populated (G2 APPLY, `ENABLE_KB_INGEST` ON) before the KB-first canary; `ENABLE_VERDICT_CACHE_LOG` a week first; the `kb-enrich` and `kb-coverage` services from their railway.*.json with the service-role / Upstash names and the breaker cap name `LLM_SPEND_CAP_OFFCLOCK_USD`; the interim `ENABLE_TIER_FILL_RESIDUAL_GUARD` flip after its canary; the canary items: `metadata.kb_hit` rate per product, `stage_timings_ms` p50 / p95 on KB hits, the `[VERDICT_CACHE] would_hit` rate, the enrich totals and spend (0 until S81-21), the operator view's queue sizes, the coverage metrics); mutation tables and gate logs filed as specs/ files and referenced by name.

### 12.6 The adversary's folded engineering checks (LC-1)
(1) flag-OFF byte identity at every hook site (S81-18 goldens + raising recorders; the D16 unregistered-path equality and the OpenAPI sha; the two scripts inert when OFF); (2) no `robots_registry` text in app/ outside the two S81-15 modules, no `kb_merchants` literal in the new app modules, no `partner` constant / `merchant_registry` import in structured_comparison_service.py (p5 / p6); (3) every KB write through the S81-14 builders, insert-ignore, never kb_feedback; the gap CAS payloads carry `state` only; (4) the RPC only through `run_db`; the card task total and bounded; (5) the verdict-cache line constants and 16 hex only, eligible users only, seeded after success only; (6) the enrich fetches all `require_tos=True`, 4 s, no adapter / render import; the single flight before any fetch; the web-search sub-flag imports nothing; (7) D16: the gate the FIRST dependency, starlette base-class 404, no new auth / header / rate rule / mount, `include_in_schema=False`, 400 codes never a bare 503; (8) D17 never selects `user_id` / `query`; absent host metrics never zero; (9) the importers of every edited module in the comm set (app/main.py importers included); (10) CRLF preserved on edited files, LF + ASCII on new files; (11) PR body size; (12) the C4 kb_ingest guard moves no G3 row.

### 12.7 SAFE check (the FOCUS surfaces, each measured)
| surface | touched? | evidence |
|---|---|---|
| auth / tokens / sessions | NO new logic. D16 adds two routes that DEPEND on the existing `verify_admin_key` (admin_routes.py:40-66) unchanged, the existing 30/min limiter, no new header / key name / rate rule / mount (rule b). S81-18 reads one request header (`X-Client-Capabilities`) in five route handlers: not an auth input, never stored or logged. | D16 2.3, S81-18 2.3 |
| quota / billing / refunds | no | usage_service, the Lua, the metering and refund paths untouched; S81-18 changes which legs run under its flag, never a reserve / consume / refund; the breaker is never called by S81-19 |
| legal or privacy text | no | no app/legal, processors.json, consent copy; the runbook is operator docs |
| consent path | no | consent_version unread |
| security middleware | no | app/middleware untouched; CORS untouched (the bookmarklet never posts) |
| migrations | no | none added; 045 / 047 / 050 untouched; kb_brands (051) never touched |
| Redis / Lua scripts | Redis (non-Lua) only: S81-19's `SET kbenrich:sf:<hash> NX EX` + GET / DELETE single flight in an off-clock script (a new `kbenrich:` namespace, no quota / usage key, no EVAL); D17's read-only HGETALL of the D14 `kbh:` keys. The class RULINGS_S81_G3 ruled SAFE for `kbh:` (telemetry, no Lua / quota key). Severable: if ruled FOCUS, S81-19's lock becomes a no-op (one Railway cron process at a time, `restartPolicyType NEVER`) and D17 omits the host metrics; nothing else changes. | S81-19 1.5 / 2.3, D17 2.2 |
| App-Review-visible client surface | no client file; backend responses change only under default-OFF flags (additive `metadata.kb_hit`, the additive price `as_of`, the KB-served values themselves) | S81-18 2.6 |
| secrets or key handling | no new credential name; `ADMIN_API_KEY` read only by the existing dependency; tests build the key at run time; the runbook names the variable only | D16 2.5 |
No unit reports FOCUS: `focus_surfaces_found` is empty, with the Redis (non-Lua) note above for the orchestrator's ruling.

## Not done in this spec
No code, no RED file, no fixture written; the comm-set base record and the fourteen client fences not run; the corpus gate not run (no price_service edit); no DEFECT_LEDGER / PLAN_STATUS edit (rows drafted in 0.4 for the orchestrator).
