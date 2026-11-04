# S81-G3 KB-INGEST group spec (measured): S81-17 KB-INGEST (+ D05 field_status / kb_gaps) + D14 LIVE-ROBOTS (+ attempt hooks)

- Group: S81-G3 KB-INGEST, the third SAFE group under LC-9 (s81-common.txt OWNER RULING 2026-10-29). ONE branch `feature/s81-g3-kb-ingest`, ONE spec (this file), the orchestrator's spec review (LC-8), ONE RED round writing both RED files, ONE GREEN, ONE adversary (correctness lens with the engineering checks of 12.6 folded in), ONE rebase, ONE PR.
- Units: S81-17 KB-INGEST (lane A; PLAN_S81 :157; VERIFY corrections :85-89; owner decisions 7 and 11) closing D05; D14 LIVE-ROBOTS + attempt hooks (lane B; PLAN_S81 :158; owner decision 11).
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-g3`, detached at base `744616e37d031923e522e30740b687de76482ee9` (`git rev-parse HEAD`), `git status --short` empty at the start and after every probe (this file sits under the gitignored `.qa-s80/`, `.gitignore:72 .qa-*/`).
- Evidence: PLAN_S81.md (:85-89 KB/registry/robots VERIFY bullets, :157, :158, owner decisions 7 / 11 at :203 / :209), S81_G3_BRIEF.md (Q1-Q9), PLAN_S80 section 0 (frozen build-3 contract, additive keys only, never a bare 503), R-A1 / R-A4 / R-A5 / R-A13 / R-A15, RULINGS_S81_G1 R-G1-1 (the `ROBOTS_ENTRY_LOOKUP` hand-off), the S81-15 record contract (`robots_registry.robots_record`), the G2 writer idiom (`scripts/kb_seed_common.py` KbWriter / url_gate).
- Personal-data rule: no real names, emails, phone numbers, device ids or account ids in this file or in anything the group writes; synthetic hosts only (`store-a.example.com`, `store-b.example.com`, `cdn.shopify.com` as the named platform CDN), built at run time where a shape matters. No secret value; variable NAMES only. Production flag state: the newest dated ledger line (2026-11-04 10:36) names none of the group's flags; all are NEW names, so unset in production by construction (R-A15).
- Measurement location: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/g3spec/` (`base_pins.log`, `corpus_base.log`, `gate_base.json`, `comm.py`, `comm_final2.txt`). Nothing in the worktree was written except this file. Every file:line below was read at 744616e3 in this run.
- Base run (bounded runner, flags unset): `tests/test_s81_kb_schema.py tests/test_s81_d08_jsonld_widen.py tests/test_s81_g1_gate_rows.py tests/test_s81_s15_registry_robots.py tests/test_shopify_pdp_json.py tests/test_woocommerce_adapter.py tests/test_algolia_service.py tests/test_url_extraction.py tests/test_s75_fanout_identity.py tests/test_fire_and_forget_wrap.py` -> 1087 passed, 11 warnings. `[pyt] tag=g3spec-base-pins start=2026-11-04 10:46:57 end=2026-11-04 10:47:28 elapsed=31s bound=600s status=OK rc=0`; `[hermeticity] sentinel checked 1087 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- Corpus gate at base (Q6): `scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_KB_INGEST,ENABLE_FIELD_STATUS_METADATA,ENABLE_LIVE_ROBOTS_REGISTRY,ENABLE_LIVE_ROBOTS_HEALTH_FLUSH --out <scratchpad>/g3spec/gate_base.json` (venv python, cwd the worktree) -> `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656`, `OVERALL SHA256 601338261705718a85c8c4ff281cefd47368a8c7aa1b12c2aad501baae18a1ef`, rc=0 (10:45:09-10:52:06). GREEN re-runs the SAME command at HEAD: the two OVERALL lines must be equal. Price_service lines the hooks touch: `curl_fetch_html` :14929-14952 and `curl_fetch_html_same_site` :14975-15054 plus one import beside :46; none is on the `extract_price_from_html` path the corpus exercises.
- NOT MEASURED in this run: the 609-file comm-set base record (section 12.1 gives the derivation, the file list and its sha; LC-6: GREEN computes it once at 744616e3 and stores it under `harness/base_records/744616e3.../<set-sha>.txt`); the fourteen client fences (no literal they read moves, 7.3).

## 0. The group

### 0.1 Branch, units, flags

| unit | flag (new name, default OFF, read PER CALL, the FIRST statement of its predicate) | reader | lane |
|---|---|---|---|
| S81-17 | `ENABLE_KB_INGEST` (the one ingest job per compare) | NEW `app/services/kb_ingest.py::kb_ingest_enabled` | A |
| S81-17 (D05) | `ENABLE_FIELD_STATUS_METADATA` (sub-flag: the additive `metadata.field_status` exposure only; independent of `ENABLE_KB_INGEST`, ruled in 2.1 of S81-17) | `kb_ingest.field_status_metadata_enabled` | A |
| D14 | `ENABLE_LIVE_ROBOTS_REGISTRY` (the verdict before every live fetch, the robots_skip / attempt counters, the `ROBOTS_ENTRY_LOOKUP` reader) | NEW `app/services/live_robots.py::live_robots_enabled` | B |
| D14 (health) | `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH` (sub-flag: the ONE Redis pipeline per compare; only meaningful with the main flag ON; SEVERABLE, see 12.7) | `live_robots.health_flush_enabled` | B |

Idiom (the `price_service.exact_gate_enabled` / `jsonld_widen.image_pipeline_v2_enabled` form, measured at `app/services/jsonld_widen.py:56-63`): `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")`, read per call, never cached. Flip preconditions (stated, never built): `ENABLE_SYNC_DB_OFFLOAD` ON before `ENABLE_KB_INGEST` (plan :157; see S81-17 2.6 for what it still guards); 045 applied (owner item 29) before either unit's flag; the S81-15 robots cron covering 100 % of live hosts (owner items 25 / 33) and the M6 named-UA dry run before `ENABLE_LIVE_ROBOTS_REGISTRY`.

### 0.2 Change list per unit (detail in each unit's section 3)

S81-17: NEW `app/services/kb_ingest.py` (flags, the pure `field_status`, the pure job builder, the off-loop writer); `app/services/structured_comparison_service.py` (ONE helper method `_kb_ingest_tail` + two call lines: REST after the moderation pass before `return result` :4774-4781, stream after the moderation pass before the `settle_complete` yield :5686-5692); `tests/test_s81_kb_schema.py` (E-rows: P01_ALLOWED / P01_FUNCTIONS / P02_ALLOWED widened for `kb_ingest.py`, the G2 E1 / E2 form); NEW `tests/test_s81_s17_kb_ingest.py` + `tests/fixtures/s81_s17_flag_off_golden.json`; CLAUDE.md (one row in the G3 block + the :341 pointer clause).

D14: NEW `app/services/live_robots.py` (flags, the verdict function, the per-process robots memo, the per-compare attempt aggregator, the health flush, the `ROBOTS_ENTRY_LOOKUP` reader); `app/services/price_service.py` (`curl_fetch_html` :14929, `curl_fetch_html_same_site` :14975 initial URL + every hop; one module import at :46); `app/services/shopify_pdp_service.py` (`_fetch_once` :325 per hop); `app/services/woocommerce_service.py` (`fetch_woocommerce_store_api_price` :302, before each GET); `app/services/algolia_service.py` (`fetch_algolia_price` :747 before the harvest, `_fetch_explicit_store_price` :850 before the first query); `app/services/url_extraction_service.py` (`extract_from_url` base path before `fetch_page` :1132; `_fetch_page_v2` :494 initial + every hop; `_V2_FETCH_OUTCOME_REASONS` :1000 one additive entry); `app/services/structured_comparison_service.py` (`_init_provider_attempts` :3552 binds the aggregator; one `finally:` arm on the REST try :4288/:4783 and on the stream try :4979/:5695 calls the flush); NEW `tests/test_s81_d14_live_robots.py` + `tests/fixtures/s81_d14_flag_off_golden.json`; CLAUDE.md (one row + the :341 pointer clause).

### 0.3 Shared files and the order GREEN applies them

Shared: `app/services/structured_comparison_service.py` (S81-17: `_kb_ingest_tail` + two call lines at the success exits; D14: `_init_provider_attempts` + two `finally:` arms; disjoint hunks, none on the same line) and `CLAUDE.md` (one block, two rows). S81-17's job CALLS D14's pure verdict function `live_robots.url_verdict` and the memo snapshot (flag-free accessors; the D14 flag gates only the live fetch hooks, the seam answer and the counters), so `live_robots.py` is written FIRST.
GREEN order: (1) `live_robots.py`; (2) the D14 fetcher hooks (price_service, shopify_pdp, woo, algolia, url_extraction); (3) `kb_ingest.py`; (4) scs: `_init_provider_attempts`, `_kb_ingest_tail` + its two call lines, the two `finally:` arms; (5) `tests/test_s81_kb_schema.py` E-rows; (6) CLAUDE.md last: ONE new column-0 block "SESSION 81 flags (S81-G3 KB-INGEST: S81-17 KB-INGEST + D14 LIVE-ROBOTS, ...)" inserted after :551 (the S81-G2 owner-steps bullet) holding both rows, plus one pointer clause on :341.

### 0.4 Known rebases, dependencies, defect-ledger rows (drafted, names only)

- Rebases: CLAUDE.md (any later block; the union is mechanical). `tests/test_s81_kb_schema.py` P01/P02 (any later writer unit widens the same sets: union). `structured_comparison_service.py` tails (S81-22 COMPARE-RUNS later inserts at the `capture_result_status` exits, not these lines).
- Consumes: the S81-14 leaf (builders, `KB_BUILDER_KEYS`, `kb_product_id`, `kb_variant_key`, `canonical_offer_url`), the S81-15 record contract (`kb_merchants.robots` = `robots_record` :472-503), the D08 seam `jsonld_widen.ROBOTS_ENTRY_LOOKUP` :459 + `rating_host_allowed` :410-443, the B1 pure `result_gate.assess_result` :509.
- Provides: `metadata.field_status` (S81-11 D20 consumer), demand-ranked `kb_gaps` (S81-19 consumer), the Redis health counters (D14b fold, S81-20/D17 consumers).
- DEFECT_LEDGER rows to add (column form `| Unit | Title | Flag | RED file | Branch / HEAD | Status |`):
  - `| S81-17 | KB-INGEST (G3 KB-INGEST, SAFE): ONE off-loop ingest job per successful compare (REST + stream + camera) through the S81-14 builders and the service-role client: kb_products / kb_variants at identity_confidence high, kb_offers on registry hosts with an allow verdict (genuine methods only, one shared last_seen), kb_images (the JSON-LD page image), kb_reviews (channel-1 aggregates); no kb_specs (no per-field source URL on the live path), no kb_feedback | ENABLE_KB_INGEST | tests/test_s81_s17_kb_ingest.py | feature/s81-g3-kb-ingest | SPEC |`
  - `| D05 | FIELD-STATUS (G3, with S81-17): the per-product field_status {state, source, reason} (identity, image, price fresh/stale/unknown + as_of + rung, size, concentration, specs, rating, review_count) exposed as the additive metadata.field_status and folded into demand-ranked kb_gaps rows (insert-ignore + compare-and-set demand_count, no migration) | ENABLE_FIELD_STATUS_METADATA (exposure) + ENABLE_KB_INGEST (gaps) | tests/test_s81_s17_kb_ingest.py | feature/s81-g3-kb-ingest | SPEC |`
  - `| D14 | LIVE-ROBOTS + attempt hooks (G3): one app/ verdict function over the persisted robots record (per-process memo of host,status,deny,robots,challenge), consulted before every live fetch of the curl wave / shopify_pdp (incl. UCP) / woo / algolia / url_extraction, robots_skip + ok/fail/challenge aggregated per compare, ONE Redis pipeline per compare (severable sub-flag), the D08 ROBOTS_ENTRY_LOOKUP wired; UA unchanged | ENABLE_LIVE_ROBOTS_REGISTRY + ENABLE_LIVE_ROBOTS_HEALTH_FLUSH | tests/test_s81_d14_live_robots.py | feature/s81-g3-kb-ingest | SPEC |`

## Unit D14 LIVE-ROBOTS + attempt hooks

(Written first: S81-17 consumes its verdict function.)

### 1. Base state (measured at 744616e3)

#### 1.1 The persisted record and the existing evaluators
| fact | file:line |
|---|---|
| `kb_merchants` columns robots / health / challenge / tos jsonb objects, status candidate/live/blocked, deny => blocked | `migrations/045_kb_core.sql:102-133` |
| `robots_record` writes {state, status, body_sha, fetched_at, next_reread (+24 h), crawl_delay, origin, source, rules {qarenbot, star}, probed, [rules_truncated]} | `app/services/robots_registry.py:472-503` |
| the probe origin = the first same-site sample PDP origin else `https://<host>` | `robots_registry.py:516-561` |
| `rating_host_allowed(entry, url, now)`: row live, not deny, not a DENY_HOSTS host / URL, robots.state allow, no rules_truncated, fresh (now < next_reread + ROBOTS_GRACE 24 h), BOTH rules.qarenbot and rules.star allow the path, challenge clear | `app/services/jsonld_widen.py:410-443` (`ROBOTS_GRACE` :82, `_challenge_clear` :395-407, `rules_allow` :340-370) |
| `ROBOTS_ENTRY_LOOKUP = _no_entry` (module attribute read at call time) | `jsonld_widen.py:447-459`; read by `channel1_rating` :478-520 |
| the G2 gate (the MODEL): bad_url -> denied -> no_row -> not_live -> [tos] -> no_record -> origin (`robots.origin == _origin_of(url)`) -> robots (`rating_host_allowed`) | `scripts/kb_seed_common.py:250-285` |
| `deny_hosts.normalize_host` (strip, lower, drop :port, trailing dots, ONE leading www.) | `app/services/deny_hosts.py:119-135` |
| `_origin_of(url)` = scheme://host[:port] | `robots_registry.py:248-257` |

#### 1.2 The registry memo (Q3)
`merchant_registry.READ_COLUMNS = "host,status,deny,blocked_reason,registry,partner"` (:75), `READ_STATUSES = ("live","blocked")` (:77), memo state :168-182 (selection / lookup / partners / snapshot), `_serve` :236-248, refresh single-flight in a fresh `contextvars.Context` :206-233, paged read :296-317, all behind `ENABLE_MERCHANT_REGISTRY_DB` (:117-119; `registry_rows` / `registry_lookup_rows` return the fallback untouched when OFF :251-262). The memo carries NO robots / challenge column. Pins on the column list: `tests/test_s81_s15_registry_robots.py:914-917` (R6: `DECODE_COLUMNS <= cols <= DECODE_COLUMNS | {"updated_at"}`) - widening READ_COLUMNS reddens that frozen row (an E-row on a FOCUS-era file) and couples D14 to `ENABLE_MERCHANT_REGISTRY_DB`. DECISION: a SECOND per-process memo inside `live_robots.py` (columns `host,status,deny,robots,challenge`, statuses live + blocked, the merchant_registry knobs reused by name: `MERCHANT_REGISTRY_MEMO_SECONDS` 600 (300..900), `..._READ_TIMEOUT_SECONDS` 5, `..._MAX_STALE_SECONDS` 3600), the same single-flight + fresh-Context refresh pattern, the read off-loop through `asyncio.to_thread`. Cost: one extra paged select per process per memo window (410 seeded rows = one page of 500, measured from the S81-15 seed counts in the DEFECT_LEDGER S81-15 row: 317 live / 92 candidate / 1 blocked); memory = 318 small dicts.

#### 1.3 Source-scanning pins that constrain the new module text (measured)
- `tests/test_s81_s15_registry_robots.py:777-789` `test_p5_live_fetchers_read_no_robots_registry`: ANY `app/**/*.py` other than robots_registry.py / merchant_registry.py whose TEXT contains `robots_registry` fails; and price_service.py, url_extraction_service.py, shopify_pdp_service.py + every `app/services/*.py` whose name contains shopify/woo/salla/magento/algolia/noon/unbxd/occ/rest_json/bolo/boutiqaat/nasser/iherb must not contain the text `kb_merchants`. CONSTRAINT: `live_robots.py` and `kb_ingest.py` never contain the string `robots_registry` (not even in a comment; the origin helper is re-implemented, 2.3), the hooked fetchers never contain `kb_merchants` (the table name lives only in `live_robots.py`, read as `merchant_registry.KB_MERCHANTS_TABLE`). Neither new file name matches an adapter key. Kept green, no E-row.
- `tests/test_s81_s15_registry_robots.py:791-803` `test_p6`: scs / scoring / response_builder never import `merchant_registry` and carry no `"partner"` constant: scs imports only `live_robots` / `kb_ingest`.
- `tests/test_s80_url_mode_v2.py:1438-1447` `test_fetch_page_untouched_pin`: `inspect.getsource(fetch_page)` sha pinned -> D14 does NOT edit `fetch_page`; the base path is hooked at its caller `extract_from_url` :1132.
- `tests/test_shopify_pdp_json.py:718-735`: every importer of shopify_pdp_service consults its flags; `live_robots` never imports it.
- `tests/test_s81_kb_schema.py:350-396` P01 / P02: `live_robots.py` neither imports `kb_service` nor names a kb_* relation literal (uses `merchant_registry.KB_MERCHANTS_TABLE`).

#### 1.4 The live fetchers (Q8: none receives the registry row; every lookup keys on the URL host)
| fetcher | file:line | request | UA | registry row passed? |
|---|---|---|---|---|
| `curl_fetch_html(url, *, cap)` | `price_service.py:14929-14952` | curl_cffi GET, `impersonate="chrome"`, allow_redirects=True, in `asyncio.to_thread` | chrome impersonation | no (URL) |
| `curl_fetch_html_same_site(url, domain, ...)` | `price_service.py:14975-15054` (initial validate :15023, hop loop :15030-15050) | GET per hop, allow_redirects=False | chrome | no (URL + domain) |
| `fetch_page_price` | `price_service.py:15057-` | calls `curl_fetch_html_same_site` | - | covered by the hop hook |
| `shopify_pdp_service._fetch_once(js_url, domain)` | `shopify_pdp_service.py:325-356` (per hop after `_hop_is_allowed_async` :336) | `_curl_get` :260-275 chrome | chrome | no; reached by `fetch_shopify_pdp_json` :550, `fetch_ucp_json_product` :893, `fetch_ucp_json_availability` :938, `fetch_ucp_json_price` :977 (all through `_fetch_feed_body` :587-607) |
| `woocommerce_service.fetch_woocommerce_store_api_price(domain, ...)` | `:302-365` (GET :340, /v1 retry :346) | `_do_get` :291-299 chrome | chrome | no (domain) |
| `algolia_service.fetch_algolia_price(domain, ...)` / `_harvest_config(domain)` | `:747`, `:221-290` (landing GET :247-252) | chrome | chrome | no (domain) |
| `algolia_service._fetch_explicit_store_price(domain, ...)` | `:850-` (POST to the Algolia DSN host :357) | chrome | chrome | no |
| `url_extraction_service.fetch_page(url)` | `:438-491` (Chrome UA literal :441) | httpx, manual hops | Chrome UA string | no; caller `extract_from_url` :1132 |
| `url_extraction_service._fetch_page_v2(url)` | `:494-548` (UA literal :505, initial :516-521, hop :527-535) | httpx | Chrome UA string | no; caller `_extract_from_url_v2` :1035, outcome map `_V2_FETCH_OUTCOME_REASONS` :1000-1001 -> STORE_UNREADABLE |

#### 1.5 The existing attempt telemetry (the shape)
`_record_provider_attempt(*, provider, url, retailer_domain, status, cost, outcome, html_kb, detected_cf, elapsed_ms)` appends to the ContextVar `_PROVIDER_ATTEMPTS_CTX` (scs :96-106, :148-176), bound per compare by `_init_provider_attempts` (:3552-3559, called at :4228 REST and :4937 stream), attached to `metadata.source_trace.races.price.attempts` (:3561-3581, :4664-4670) - it is RESPONSE-VISIBLE metadata. D14 therefore keeps its counters in its OWN ContextVar (never in `source_trace`), keyed `(source, host, outcome)` -> int, the provider-attempt vocabulary (source = the fetcher label, outcome in ok | fail | robots_skip | challenge).

#### 1.6 Redis (Q4, measured on the pinned venv `.venv-qaren`, upstash-redis 1.7.0 = `requirements.txt:202`)
`cache_service.redis_client` (:166) is the SYNC `upstash_redis.Redis` (built :60-160). `upstash_redis.client.Pipeline` has `hincrby(key, field, increment)`, `expire`, `exec() -> List[...]` (measured `hasattr` + `inspect.signature`); `Redis.pipeline()` sends the stacked commands as ONE REST call (`multi_exec="pipeline"`; the async twin `AsyncPipeline.exec` measured: one `self._http.execute(..., from_pipeline=True)`). Off-loop runner: `app/utils/redis_offloop.py:126 run_redis_offloop_pool(fn, *args, durable=False)` (one job on the shared `redis-offloop` pool whatever ENABLE_PRICE_PATH_REDIS_OFFLOOP says). CHOSEN mechanism: ONE pipeline per compare = for each touched host one `HINCRBY kbh:<YYYYMMDD UTC>:<host> <source>:<outcome> <n>` per non-zero counter + ONE `EXPIRE <key> 691200` (8 days); cost = one REST round trip (about 20-60 ms, off the loop, never awaited by the response) and 0 rows in Supabase. NOT chosen (stated): a service-role write of absolute per-host values into `kb_merchants.health` - PostgREST has no multi-row update with per-row values without an RPC (= migration 051, FOCUS), so it is N single-row UPDATEs per compare, and absolute values merged from a memo snapshot up to 600 s old lose concurrent compares' counts (last writer wins). The fold of the counters into `kb_merchants.health` is the S81-15 cron's next pass and is OUT of this group (D14b): `scripts/cron_robots_registry.py` is untouched.

#### 1.7 Flag idiom, line endings, libraries, guards
The idiom of 0.1 (`jsonld_widen.py:56-63`, `merchant_registry.py:117-119`, `db_offload.py:29-32`). Backend files are CRLF in the working copy (`cat -A app/utils/db_offload.py` shows `^M$`), LF in the index; the Edit tool keeps CRLF; new files are written LF (git normalises). Libraries: stdlib + the in-repo leaves only; no new dependency. Guards: the netguard (tests), `tests/_env_safety.CREDENTIALS_UNSET` (no new credential name: the unit reads only flag / knob names), the U8d log rule (host only, never path / query; constants and ints).

#### 1.10 Base pass state
The base run in the header (1087 passed) covers `test_s81_s15_registry_robots.py`, `test_s81_d08_jsonld_widen.py`, `test_s81_g1_gate_rows.py`, `test_shopify_pdp_json.py`, `test_woocommerce_adapter.py`, `test_algolia_service.py`, `test_url_extraction.py`. `tests/test_s80_url_mode_v2.py` is in the comm set (not run here).

### 2. Contract

#### 2.1 Flags and knobs
`ENABLE_LIVE_ROBOTS_REGISTRY` (main), `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH` (the Redis flush; checked AFTER the main flag; ON alone does nothing). Knobs (read per call, `_float_knob` semantics of `merchant_registry.py:122-133`: unset / garbage / inf / nan / <= 0 -> default, else clamped): the three MERCHANT_REGISTRY_* memo knobs reused by name (no new name); `LIVE_ROBOTS_HEALTH_TTL_DAYS` (8, clamped 1..30). No credential name.

#### 2.2 Public surface of `app/services/live_robots.py` (stdlib + deny_hosts + jsonld_widen at top; merchant_registry / database_service / cache_service / redis_offloop imported lazily inside functions)
- `live_robots_enabled() -> bool`, `health_flush_enabled() -> bool` (each the FIRST statement reads its env var).
- `VERDICT_REASONS = ("bad_url", "denied", "no_row", "not_live", "no_record", "origin", "robots")` (the url_gate reasons minus `tos`; `robots` covers disallow / unreadable / expired / truncated / parked challenge, all decided by `jsonld_widen.rating_host_allowed`).
- `url_verdict(url, row, now) -> Optional[str]`: None = allow, else one VERDICT_REASONS member; pure, total, never raises (an exception = "bad_url"); the url_gate order: scheme http(s) + host else bad_url; `deny_hosts.is_denied_url(url)` -> denied; row not a dict -> no_row; `row["deny"]` -> denied; status != "live" -> not_live; `robots` not a dict or no `origin` -> no_record; `robots["origin"] != _origin_of(url)` -> origin; `not jsonld_widen.rating_host_allowed({status, deny, robots, challenge}, url, now)` -> robots. `_origin_of` re-implemented in this module (1.3: never the text of the S81-15 module name).
- `row_for_host(host) -> Optional[dict]`: the memo row view {host, status, deny, robots, challenge} for `deny_hosts.normalize_host(host)`, else the row of the longest registry host that host is a subdomain of (the `kb_seed_common.merchant_for_host` rule :206-218), else None; a deep copy; NO I/O on the caller (schedules a refresh when stale, 2.4).
- `records_snapshot() -> Optional[Dict[str, dict]]` (flag-free; the last good load or None) and `load_records_sync(client) -> Dict[str, dict]` (flag-free; the paged read for a worker thread; it also stores a good load into the memo under the lock). Consumed by S81-17.
- `gate(url, source) -> bool`: the hook. FIRST statement `if not live_robots_enabled(): return True` (OFF reads nothing else). ON: `reason = url_verdict(url, row_for_host(host_of(url)), _now())`; reason None -> True; else `record(source, host, "robots_skip")`, one INFO line `[LIVE_ROBOTS] skip source=%s host=%s reason=%s` (constants + the normalized host; never path / query), return False. A cold memo (no good load yet) = `no_row` = skip (fail-closed, R-W "missing = skip").
- `record(source, host, outcome)`: ON only; `outcome in ("ok", "fail", "robots_skip", "challenge")`, increments the per-compare aggregator if one is bound (ContextVar `_ATTEMPTS_CTX`, default None -> silent no-op, the `_record_provider_attempt` rule).
- `bind_attempts() -> None` (ON only: binds a fresh dict), `flush_attempts() -> None` (reads the bound dict, unbinds it, and when `health_flush_enabled()` hands ONE job to `run_redis_offloop_pool` through `async_utils.fire_and_forget(..., "live_robots_health_flush")`; empty dict / no Redis client -> nothing; never raises).
- `robots_entry_lookup(host) -> Optional[Mapping]`: `if not live_robots_enabled(): return None` FIRST; else `row_for_host(host)` projected to {status, deny, robots, challenge}. At module import `jsonld_widen.ROBOTS_ENTRY_LOOKUP = robots_entry_lookup` (R-G1-1 hand-off; flag OFF it answers None for every host = `_no_entry`'s answer; the D08 R13 row `seam(HOST) is None` stays green with the flag unset).
- Test seams (module attributes read at call time): `_now`, `_monotonic`, `_admin_client`, `_redis_client`.

#### 2.3 The hooks (each a flag-first `if live_robots.live_robots_enabled():` block; flag OFF the original statements run unchanged)
| site | under the flag |
|---|---|
| `curl_fetch_html` :14929 (before the to_thread GET) | `if not gate(url, "curl"): return None`; after the response: `record("curl", host, "ok" if 200 else "challenge" if the `cf-mitigated` header equals `challenge` else "fail")`; the except arm records "fail" |
| `curl_fetch_html_same_site` :15023 + each hop :15040 | gate the initial URL and every `nxt` before it is fetched (`"curl_same_site"`); skip -> `return None` (the existing honest-miss value); record per terminal response |
| `shopify_pdp_service._fetch_once` :336 | after `_hop_is_allowed_async`, `gate(current, "shopify")` per hop; skip -> `return None, None` (the existing blocked-hop value); record per response |
| `woocommerce fetch_woocommerce_store_api_price` :340 / :346 | `gate(<the exact store-API URL>, "woo")` before each GET; skip -> `return None`; record |
| `algolia fetch_algolia_price` (before `_harvest_config` :773) and `_fetch_explicit_store_price` (before the first query :868) | `gate("https://" + domain + "/", "algolia")`; skip -> `return None` (the Algolia DSN host is the provider API, not the merchant: the merchant origin decides) |
| `url_extraction extract_from_url` :1132 | `if live_robots_enabled() and not gate(url, "url_extraction"): html = None` else the base `await fetch_page(url)` (fetch_page untouched, 1.3) -> the existing `Failed to fetch URL` body |
| `url_extraction _fetch_page_v2` :516 + hop :527 | gate initial + every hop; skip -> `result.update(outcome="robots_skip", final_url=current)`; `_V2_FETCH_OUTCOME_REASONS` gains `"robots_skip": "robots_skip"` (unreachable OFF) -> STORE_UNREADABLE (a code build 3 renders) with reason `robots_skip` |
| scs `_init_provider_attempts` :3552 | `live_robots.bind_attempts()` (OFF: the flag read only) |
| scs REST try :4288-4802 and stream try :4979-5716 | a `finally:` arm: `live_robots.flush_attempts()` (OFF: the flag read only; never awaits; never raises) |

The User-Agent / `impersonate="chrome"` of every fetcher is UNCHANGED under the flag (the named-UA switch is a later knob after M6: stated limit D14-L1).

#### 2.4 The memo
State {rows: Dict[host, view] | None, loaded_at, good_at, failed, warned_at} under a `threading.Lock`; `row_for_host` serves the last good load while `now - good_at <= MAX_STALE` (else None = skip) and schedules ONE refresh per loop when `now - loaded_at >= MEMO_SECONDS` (merchant_registry `_schedule_refresh` pattern :206-233, fresh `contextvars.Context`); the refresh = `asyncio.wait_for(asyncio.to_thread(_read_rows, client), READ_TIMEOUT)`; a failure keeps the last good load and logs ONE WARNING per window with the exception type. Rows with status candidate are never read (server filter `in_("status", ["live","blocked"])`).

#### 2.5 Failure table (flag ON)
| input | result |
|---|---|
| memo cold / refresh failing past MAX_STALE | every gated fetch skipped (`no_row`), counted robots_skip; the compare degrades to its existing miss paths |
| record expired (now >= next_reread + 24 h) | skip `robots` |
| origin differs (www vs apex, http vs https) | skip `origin` (robots files are per origin; stated D14-L2) |
| rules_truncated | skip `robots` |
| challenge parked | skip `robots` |
| aggregator unbound (a fetch outside a compare, e.g. a warmer) | gate still decides; `record` is a silent no-op |
| Redis client None / pipeline raises | no flush; ONE WARNING `[LIVE_ROBOTS] health flush failed: <type>` from the done-callback; the response never sees it |
| any exception inside `gate` | treated as skip `bad_url` (fail-closed) and never raised to the fetcher |

#### 2.6 Flag-OFF identity (the main invariant)
OFF: every hook is one env read and the base statements; no memo read, no Supabase client, no ContextVar write, no Redis call, `ROBOTS_ENTRY_LOOKUP(host)` answers None. Proven by PIN rows with the FULL configuration (memo knobs set, a seeded DISALLOW row for the test host, a raising client / Redis recorder, the sub-flag ON) and a call recorder per fetcher (golden call sequences recorded at base in `tests/fixtures/s81_d14_flag_off_golden.json`), plus the corpus gate (Q6: the hooks sit in the fetchers, not in `extract_price_from_html`, so the corpus SHA is unaffected by construction; it is re-printed at HEAD).

### 3. Change list (GREEN, in order; byte-copy every existing file first into `<scratchpad>/S81-G3_green_before/` with sha256)
1. NEW `app/services/live_robots.py` (2.2-2.5; pure ASCII; no `robots_registry` text).
2. `app/services/price_service.py`: `from app.services import live_robots` beside :46; hooks in `curl_fetch_html` and `curl_fetch_html_same_site` (2.3).
3. `app/services/shopify_pdp_service.py`: function-local `from app.services import live_robots` inside `_fetch_once`; the per-hop hook.
4. `app/services/woocommerce_service.py`, `app/services/algolia_service.py`: module import + hooks.
5. `app/services/url_extraction_service.py`: module import; the `extract_from_url` caller hook; `_fetch_page_v2` hooks; one `_V2_FETCH_OUTCOME_REASONS` entry. `fetch_page` byte-unchanged.
6. `app/services/structured_comparison_service.py`: `from app.services import live_robots`; `_init_provider_attempts` line; two `finally:` arms.
7. NEW `tests/test_s81_d14_live_robots.py` (the RED round writes it; GREEN never edits it) + `tests/fixtures/s81_d14_flag_off_golden.json` (RED records it at base).
8. CLAUDE.md row (section 8).
No other file.

### 4. Existing pins
#### 4.1 Deliberate changes
None for D14 (1.3: every constraining pin is satisfied by construction, no frozen row edited).
#### 4.2 Must stay green and unedited
`tests/test_s81_s15_registry_robots.py` (p5 / p6 / R6), `tests/test_s81_s15_gate_rows.py`, `tests/test_s81_d08_jsonld_widen.py` (R13 default seam None), `tests/test_s81_g1_gate_rows.py`, `tests/test_s80_url_mode_v2.py` (fetch_page sha), `tests/test_shopify_pdp_json.py`, `tests/test_woocommerce_adapter.py`, `tests/test_algolia_service.py`, `tests/test_url_extraction.py`, `tests/test_s75_fanout_identity.py` (FY25 digests), every comm-set member (12.1).

### 5. RED tests: `tests/test_s81_d14_live_robots.py` (new; pure ASCII; hermetic: netguard on, fakes only; the memo seeded through the `_admin_client` seam with an in-memory client that records table / select / in_ / order / range / execute and the executing thread; Redis faked with a recorder pipeline; `_now` / `_monotonic` patched; every missing symbol read through a getattr / find_spec helper so a base run fails on an AssertionError only)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| L1 | readers | `live_robots_enabled` / `health_flush_enabled` exist; unset / "" / "false" / "0" / " OFF " -> False; "true" / " TRUE " / "1" / "yes" / "on" -> True; each re-read per call (setenv between calls flips it) | RED (module absent) | 2.1 |
| L2 | verdict table (parametrized, 16 cases) | allow (both rule lists allow, fresh, origin equal); denied (DENY_HOSTS URL; row deny); no_row; not_live (blocked, candidate); no_record ({} robots; no origin); origin (www vs apex; http vs https); robots (state disallow; unreadable; star disallows the path while qarenbot allows; qarenbot disallows while star allows; expired past next_reread + 24 h; rules_truncated; challenge parked in the future); bad_url (non-str, ftp://, no host) | RED | 2.2 |
| L2b | parity with the G2 gate | for every L2 case `url_verdict(u, row, now) == kb_seed_common.url_gate(row, u, now)` (require_tos False) | RED | 2.2 |
| L3 | memo read | flag ON, first `gate` call on a running loop: ONE refresh task; ONE select of exactly {host,status,deny,robots,challenge} on `merchant_registry.KB_MERCHANTS_TABLE` with `in_("status", ["live","blocked"])`, `range(0, 499)`, executed off the loop thread; a second call inside MEMO_SECONDS reads nothing; a failing refresh keeps the last good load until MAX_STALE, then skips | RED | 2.4 |
| L4a-g | skip per fetcher (flag ON, the test host seeded DISALLOW) | the fake transport is NEVER called; the return is the existing miss value (curl: None; same_site: None at the initial URL and at a hop whose host record disallows; shopify `_fetch_once`: (None, None); woo: None; algolia harvest + explicit: None; `extract_from_url` base: the `Failed to fetch URL` body; `_fetch_page_v2` -> `_extract_from_url_v2` returns code STORE_UNREADABLE, reason `robots_skip`); one robots_skip counted per skip with the fetcher label | RED | 2.3 |
| L5 | allow passes byte-identical args | flag ON + ALLOW record: each fake transport receives exactly the base call (same URL, `impersonate="chrome"`, same timeout / headers / UA literal) as the L9 golden; outcome ok / fail / challenge counted (200; 404; 403 + `cf-mitigated: challenge`) | RED | 2.3 |
| L6 | no inline robots fetch | across L4 / L5 no transport call URL ends with `/robots.txt` and no fetch happens inside `gate` | RED | 2.2 |
| L7 | seam | flag ON: `jsonld_widen.ROBOTS_ENTRY_LOOKUP` (after importing live_robots) returns {status, deny, robots, challenge} for a seeded host and None for an unknown one; `channel1_rating` produces the D08 rating for an ALLOW host; flag OFF: None for every host and no memo read | RED | 2.2 |
| L8 | flush once per compare | flags ON (main + health), the faked compare (the FY25 driver pattern of `tests/test_s75_fanout_identity.py:202-252`) with two hosts fetched: ONE `pipeline()` + ONE `exec()` per compare for REST and for stream; HINCRBY `kbh:<UTC day>:<host>` `<source>:<outcome>` n + one EXPIRE 691200 per host; no exec when nothing was attempted; health flag OFF -> no pipeline | RED | 2.2, 2.3 |
| L9 | flush failure | `exec` raising -> one WARNING with the exception type; the REST body / stream events equal the no-failure run | RED | 2.5 |
| L10 | fail-closed on gate error | `url_verdict` patched to raise -> skip, no exception reaches the fetcher | RED | 2.5 |
| L11 | log hygiene | every `[LIVE_ROBOTS]` record carries the host and constants only: no URL path, query, `?` or `/` after the host | RED | 2.2 |
| P1 | flag OFF identity per fetcher | FULL config (sub-flag ON, knobs set, the host seeded DISALLOW through a client recorder, Redis recorder): each fetcher's transport call sequence == the base golden `s81_d14_flag_off_golden.json` (recorded at base by the RED agent); the client recorder and the Redis recorder are EMPTY; the flag rows parametrized over unset / "false" / " 0 " / "OFF" | PIN (green at base: the golden is recorded at base, the recorders are attributes the base never calls) | 2.6 |
| P2 | OFF compare identity | FULL config, the FY25 scenarios (REST + stream): normalized digests equal the base digests in the golden; `_PROVIDER_ATTEMPTS_CTX` contents equal base | PIN | 2.6 |
| P3 | seam OFF | `jsonld_widen.ROBOTS_ENTRY_LOOKUP("any.example.com")` is None with the flag unset (importing every app module first) | PIN | 2.2 |

Counts (D14): 11 RED rows (L4 as 7 parametrized nodes, L2 as 16) and 3 PIN rows; final node counts are the RED agent's to report.

### 6. Mutation table (byte copies, the killing rows via `pyt.py -k`, bound 600, restore + sha256)
| id | mutant (exact-string edit in the GREEN file) | killed by |
|---|---|---|
| D14-M1 | `gate` returns True before the flag check is consulted ON (skip never happens) | L4a-g |
| D14-M2 | the flag check removed (`gate` always evaluates) | P1 (client recorder non-empty) |
| D14-M3 | `rules.star` check dropped (qarenbot only) - in the verdict by passing a copy without `star` | L2 (star-disallow case) |
| D14-M4 | origin comparison removed | L2 origin cases, L2b |
| D14-M5 | expired-record test inverted | L2 expired |
| D14-M6 | `_fetch_page_v2` hop gate removed (initial only) | L4g hop case |
| D14-M7 | shopify per-hop gate moved before `_hop_is_allowed_async` and returns on allow | L5 (args) / L4c |
| D14-M8 | flush called per fetch instead of per compare | L8 (exec count) |
| D14-M9 | `flush_attempts` ignores `health_flush_enabled` | L8 (health OFF) |
| D14-M10 | `robots_entry_lookup` ignores the flag | P3, L7 OFF |
| D14-M11 | the memo select widened to `*` | L3 |
| D14-M12 | the log line carries the full URL | L11 |

### 7. Comm set, gates
#### 7.1 Comm set: the group set of 12.1 (D14's edited modules: price_service, shopify_pdp_service, woocommerce_service, algolia_service, url_extraction_service, structured_comparison_service; the read-only consumers jsonld_widen, merchant_registry, deny_hosts, async_utils; the importers of each, app/main.py's importers included).
#### 7.2 Gates for GREEN (cheapest first)
py_compile + ruff `E9,F63,F7,F82` on the six edited app files + live_robots.py; the RED file OFF and ON (`ENABLE_LIVE_ROBOTS_REGISTRY=true ENABLE_LIVE_ROBOTS_HEALTH_FLUSH=true` in the runner's environment only); the 4.2 pins; the corpus gate (Q6, base and head, one sitting); the comm set chunks at HEAD vs the cached base record.
#### 7.3 Client fences
No literal any of the fourteen backend-scanning client fences reads moves (measured: the fences read `app/api/{auth,history,home,profile}_routes.py`, `app/middleware/error_handler.py`, `app/services/{analytics,attribution,database,extraction,push,reengagement,referral,scoring,usage}_service.py`, `scripts/{cron_expire_bonuses,render_legal_landing,render_myez_icons}.py` and `robots_eval.py` via landing.domain.s76; none is edited). They still run by path at GREEN and at the rebase (LC-5: the footprint touches app/).

### 8. CLAUDE.md row (in the G3 block; wording may tighten, content may not) and owner steps
- `ENABLE_LIVE_ROBOTS_REGISTRY` + sub-flag `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH` + knob `LIVE_ROBOTS_HEALTH_TTL_DAYS` (8, 1..30; the memo reuses the three `MERCHANT_REGISTRY_*` knobs) (D14 LIVE-ROBOTS, `app/services/live_robots.py`): flag ON, every live fetch of the curl wave (`curl_fetch_html`, `curl_fetch_html_same_site` incl. each hop), `shopify_pdp_service._fetch_once` (the .js / .json / UCP endpoints, each hop), the WooCommerce Store API, the Algolia storefront (merchant origin) and URL mode (`extract_from_url` before `fetch_page`, `_fetch_page_v2` each hop) first asks `live_robots.url_verdict` over the PERSISTED S81-15 record (a per-process memo of `host,status,deny,robots,challenge`, live + blocked rows, never a robots.txt fetch): deny -> row -> live -> record -> same origin -> the most restrictive of QarenBot and `*`, fresh, untruncated, no parked challenge; anything else is a skip recorded as `robots_skip` (fail-closed: a cold memo skips). Outcomes ok / fail / robots_skip / challenge are aggregated per compare in a ContextVar (never in the response) and, with the sub-flag, flushed as ONE Upstash pipeline (`HINCRBY kbh:<UTC day>:<host> <source>:<outcome>` + EXPIRE) per compare; the fold into `kb_merchants.health` is D14b. `jsonld_widen.ROBOTS_ENTRY_LOOKUP` answers the record under the flag (D08 channel 1). The User-Agent and `impersonate="chrome"` are UNCHANGED (the named-UA switch waits for M6). Flag OFF: one env read per fetch, byte-identical (PIN P1-P3, the corpus gate).
- Owner steps (names only; a dated ledger line each): (1) apply 045 (owner item 29); (2) the robots cron (owner item 25) run until it covers 100 % of live hosts (owner item 33; read the cron's own coverage count); (3) the M6 named-UA dry run on the adapter hosts; (4) flip `ENABLE_LIVE_ROBOTS_REGISTRY` on web in a canary window and watch robots_skip per host in the logs, /health loop lag and the genuine-price share; (5) only then `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH`.

### 9. Stated limits
- D14-L1: the UA stays Chrome under the flag while the verdict is judged as QarenBot AND `*` (the most restrictive): the named-UA switch is a later knob after M6.
- D14-L2: a URL on another origin of a registry host (www vs apex, http vs https, a subdomain without its own record) is skipped until the cron reads that origin.
- D14-L3: a cold or long-failing memo skips every gated fetch (fail-closed by the plan's "missing = skip"); the first compare after a deploy may skip until the first refresh lands (about one read RTT).
- D14-L4: URL mode under the flag refuses any host without an allow record (owner decision 11 extends robots to the live path; the 2026-08-31 ruling had listed the user-requested PDP fetch as outside robots): see Q-D14-1.
- D14-L5: counters for attempts that finish after the compare's `finally` (cancelled fan-out stragglers) are dropped; the warmer and other off-compare callers are gated but uncounted.
- D14-L6: the Redis counters are not folded into `kb_merchants.health` by this group (D14b); they expire after 8 days.
- D14-L7: the Algolia DSN API host is not robots-checked; the merchant's origin decides.

### 10. Out of scope
The named-UA switch; any robots.txt fetch on the live path; the cron fold (D14b); the S81-15 cron, seed and memo (untouched); the operator path (D16); Magento / Salla / OCC / rest_json / noon / unbxd adapters and the render tiers (firecrawl, scrapedo, Zyte, Bright Data) - not in the plan's D14 list (stated: they are not gated in this group, D14c).

### 11. Open questions (for RULINGS_S81_G3)
- Q-D14-1: URL mode under the flag: fail-closed for every non-registry host (spec default, plan text) or skip only on an explicit disallow / challenge / expired record of a REGISTRY host (missing row = allow, the 2026-08-31 ruling)?
- Q-D14-2: the Redis flush is a FOCUS surface by the letter of LC-1 ("Redis / Lua scripts"); the spec keeps it as a severable sub-flag (12.7): keep in G3 (telemetry counters, no Lua, no quota key, the `cache_service.record_tier15_attempt` class) or move to D14b?
- Q-D14-3: gate the remaining adapters (Magento / Salla / OCC / rest_json) in a D14c?

## Unit S81-17 KB-INGEST (+ D05)

### 1. Base state (measured at 744616e3)

#### 1.1 The two success exits (Q1)
| exit | file:line |
|---|---|
| REST entry `compare_from_text` (wait_for wrapper; the timeout PARTIAL returns at :4112 and never reaches the builder) | `structured_comparison_service.py:4009-4166` |
| REST impl `_compare_from_text_impl`; outer try :4288 / except :4783 | `:4168` |
| build -> `attach_data_freshness_notice` :4711 -> `_stamp_unit_metadata` :4712 -> stage timings :4713-4723 -> `cohort_injected` :4728-4731 -> L3 `moderate_output` :4757 -> refusal `CONTENT_UNAVAILABLE` return :4758-4771 -> behaviour-profile `_fire_and_forget` :4775-4779 -> `return result` :4781 | `:4682-4781` |
| stream `compare_from_text_streaming`; outer try :4979 / except :5695 | `:4804` |
| build -> `attach_data_freshness_notice` :5604 -> `_stamp_unit_metadata` :5605 -> timings -> `cohort_injected` :5619-5622 -> profile `_fire_and_forget` :5626-5630 -> moderation :5659 (M13-04 residual :5660-5669) -> refusal yields :5683-5684 -> `yield ("settle_complete", complete_response)` :5692, `("complete", ...)` :5693 | `:5575-5693` |
| camera: `image_routes.py:560` calls `compare_from_text(..., vision_products=...)` (the same impl and exit; vision products read at :4290-4292) | `app/api/image_routes.py:560` |
| other callers of the same exits: `text_routes.py:661, :882, :1470` (REST), `:1145` (stream) | `app/api/text_routes.py` |
| `_fire_and_forget(coro, label)` -> `app.utils.async_utils.fire_and_forget` (create_task named by label, registry, WARNING done-callback) | scs `:354-364`, `app/utils/async_utils.py:44-90` |
| the flag-ON-only metadata idiom `_stamp_unit_metadata` (writes a key only when its mark exists; flag OFF no key) | `:3879-3903` |

#### 1.2 Identity confidence (Q2)
B1's flag is `ENABLE_RESULT_STATUS_METADATA` (`result_gate.py:83-85`); the stamp is `response_builder.py:2303-2327` (before `_strip_inference_markers` :2346). `result_gate.assess_result(result, product_categories=, vision_confidences=)` (:509-555) and `identity_confidence(products, *, same, coherent, vision_confidences, facts_per_product)` (:470-487) are PURE and flag-free: computable without B1. It is a PAIR value (unresolved / low / medium / high), not per product (stated S81-17-L1). At the scs tail the tier-3 `_field_confidence` markers are already stripped from the RESPONSE (`response_builder.py:1423-1454`, :2346) but the per-product `product_data[i]["specs"]["_field_confidence"]` (set by `_clean_specs` :3490-3491) is the job's source for tier-3 detection; `assess_result` is called on the final body with `product_categories` (in scope at both exits) and `vision_confidences=None` (B3 has not threaded it: R-A4 L1).

#### 1.3 What the live path carries per product (`product_data[i]`, built by `_fetch_product_data` :5841-6663)
`brand`, `name` (display), `full_name`, `variant`, `category` (:5870-5873); `price` dict: `amount`, `currency`, `url`, `retailer`, `source_method`, `_cached` (False = fetched in this compare :6869, :7712, :7874, :8018, :8115; True = L1/L2 :6947, :7018), `size` ("<n>ml", `price_service._stamp_listing_size` :12076-12090), `image_url` (page image), `_jsonld_facts` {gtin, sku, size, rating} under ENABLE_IMAGE_PIPELINE_V2 / ENABLE_JSONLD_RATING (`jsonld_widen.stamp_jsonld_facts` :292-336, stamped in `price_service.py:14167-14171`); `image_url` (the served image; D08 piggyback :6249-6282); `specs` (cleaned, `_field_confidence` tier-3 markers, `MODEL_KNOWLEDGE_MARKERS` `result_gate.py:70`); `_spec_confidence` (verified / likely / unverified per field, :6286-6310, computed against `_search_snippets` = TEXT only, popped at :6287 - NO per-field source URL exists on the live path); `rating`, `review_count`, `rating_verified`, `rating_source`, `rating_derived`, `jsonld_rating` {value, count, source host, url} (:6552-6590); `reviews`.
Genuine price methods: `price_service._GENUINE_BH_SOURCE_METHODS` :17072-17093 (`price_is_showable` `result_gate.py:210-221` admits converted_usd).

#### 1.4 The KB leaf, schema and the G2 writer idiom
`kb_service.py` (KB_CATEGORY :53, KB_COLUMNS :60-98, KB_BUILDER_KEYS :106-112, KB_IDENTITY_CONFIDENCE :134, KB_EVIDENCE_RUNGS :138-140, KB_GAP_STATES :146, KB_OFFER_OBSERVATION_KEY :151-153, KB_OFFER_UPSERT_SET :154, `kb_source_allowed` :215, `kb_product_id` :231-254, `kb_variant_key` :257-279, `canonical_offer_url` :282-316, builders :523-783). 045: kb_offers.merchant_id REFERENCES kb_merchants(host) :171 (an offer needs an existing merchant row); UNIQUE kb_offers observation :197, kb_images (product_id, url) :225, kb_specs (product_id, field, lang) :249, kb_reviews (product_id, source_url) :270, kb_gaps (product_key, field) :298; kb_gaps.demand_count integer default 1 >= 0 :276, state CHECK :279-281, source_hint deny-belted :282-292. RLS: service_role only :495-517. The G2 writer (`scripts/kb_seed_common.KbWriter` :347-445): builder-key check, `upsert(..., ignore_duplicates=True)` insert-ignore, offer re-observation = one UPDATE of KB_OFFER_UPSERT_SET per row, gaps re-discovery updates last_seen only. A scripts/ module is never imported by app/ (`tests/test_s81_s15_registry_robots.py:2203-2209` R43 pattern), so the live writer is re-homed in `kb_ingest.py`.
Request context (`app/utils/request_context.py` compare_request_id :169, device_fingerprint :164, consent_version :159): the only 045 columns for them are in kb_feedback, which S81-17 does NOT write -> S81-17 reads no request context.
Service-role client: `database_service.get_admin_supabase_client` :239 (memoised sync client; the `run_db` threads already share it).

#### 1.5 Off-loop and the offload flag
`app/utils/db_offload.py:29-42` (`sync_db_offload_enabled`, `run_db`: flag OFF runs the blocking call INLINE on the loop). The ingest job runs ENTIRELY inside one `asyncio.to_thread` call, so none of its Supabase calls touches the loop whatever `ENABLE_SYNC_DB_OFFLOAD` says; the precondition remains the plan's owner gate (it moves the OTHER request-path Supabase calls off the loop, so the added thread work does not stack on loop stalls; 2.6).

#### 1.6 Pins enumerating kb_* writers, service-role callers, hosts, egress (Q7)
- `tests/test_s81_kb_schema.py:331-344` P01_ALLOWED / P01_FUNCTIONS / P02_ALLOWED; `test_s14_p01_no_importer_of_kb_service` :350-382 (kb_service imported only function-locally inside the named function with the exact line text); `test_s14_p02_no_kb_relation_literal_outside_the_leaf` :385-397. -> E1 / E2 (4.1).
- `test_s14_p03_012_clients_are_admin` :400-: the 012 tables only (kb_* not covered): unaffected.
- `tests/test_s81_s15_registry_robots.py` p5 / p6 / R43 (1.3 of D14): satisfied by construction.
- External hosts / processors.json (T7b): NO new external host (Supabase and Upstash exist); no row.
- `tests/_env_safety.CREDENTIALS_UNSET`: no new credential name.

#### 1.7 Flag idiom, line endings, libraries
As D14 1.7. No new dependency; `copy`, `datetime`, `logging`, `os`, `re`, `asyncio` + in-repo leaves.

#### 1.10 Base pass state
The header run (1087 passed) includes `tests/test_s81_kb_schema.py`, `tests/test_s75_fanout_identity.py` (the FY25 flag-OFF digests: the model for this unit's golden), `tests/test_fire_and_forget_wrap.py`.

### 2. Contract

#### 2.1 Flags (the D05 exposure ruling)
`ENABLE_KB_INGEST` gates the job (built, scheduled, written). `ENABLE_FIELD_STATUS_METADATA` gates ONLY the additive `metadata.field_status` key. They are independent: the honest-unknown UI (S81-11 D20) can read field_status before the KB is written, and the KB can be filled with the response byte-identical. Both OFF: no key, no job, byte-identical at both exits. No knob except `KB_INGEST_GAP_MAX` (16, clamped 1..64: the most gap rows one job writes).

#### 2.2 D05 `field_status` (pure; `kb_ingest.field_status(product_data, result, *, captured_at)` -> list of two dicts, the products order of the body)
Per product: `{"identity", "image", "price", "size", "concentration", "specs", "rating", "review_count"}`, each `{"state", "source", "reason"}`; `price` also carries `"as_of"` (ISO-8601 Z or None) and `"rung"` (a KB_EVIDENCE_RUNGS member or None). Vocabulary (closed sets; never a free text, URL, name or number other than as_of):
| field | known / fresh when | source | unknown reasons |
|---|---|---|---|
| identity | not `result_gate.product_is_placeholder({brand, name})` and `kb_product_id` mints an id | `vision` when the compare had vision_products, else `parse` | `placeholder_identity`, `no_product_id` |
| image | the served `image_url` is an https URL | `retailer_page` when it equals the price page image accepted by `jsonld_widen.allowed_image_url`, else `search` | `no_image` |
| price | `price_is_showable(price)`: `fresh` when `price["_cached"] is False` (as_of = captured_at), `stale` otherwise (as_of None; reason `served_from_cache` or `unmarked`) | the normalized price host | `no_price`, `estimated` |
| size | `price["size"]` parses as an int ml, else a non-NA, non-tier-3 `specs["volume"]` | `listing` / `specs` | `no_size`, `model_knowledge` |
| concentration | non-NA, non-tier-3 `specs["concentration"]` | `specs` | `no_concentration`, `model_knowledge` |
| specs | at least one non-private, non-NA, non-tier-3 spec field | `search` | `no_specs`, `model_knowledge` |
| rating | `result_gate.rating_is_real(product)` | `retailer_jsonld` when `jsonld_rating` supplied it, else `provider` | `no_rating`, `derived_rating` |
| review_count | an int > 0 | as rating | `no_review_count` |
`rung`: `page_evidence` for page_scrape / page_scrape_jsonld / local_bhd; `platform_api` for shopify_json / woo_store_api / salla_api / occ_rest_bhd / magento_graphql_bhd / rest_json_bhd; None otherwise (converted_usd, render tiers, estimates). Exposure (flag ON): `result["metadata"]["field_status"] = <the list>` at both exits after the moderation pass (a `setdefault("metadata", {})` like the timings line :4723). The key never appears on a refusal, a parse failure or a timeout partial.

#### 2.3 The job (one per successful compare, `ENABLE_KB_INGEST` ON)
`_kb_ingest_tail(self, result, product_data, *, product_categories, region, vision)` (scs, called at both exits after the moderation pass; stream: before the `settle_complete` yield; REST: before `return result`): FIRST statements read the two flags; both OFF -> return. Otherwise, on the loop, with NO I/O: `snap = kb_ingest.build_job(result, product_data, product_categories=..., region=..., vision=..., captured_at=kb_ingest._now())` = a deep-copied plain-data projection (brand, name, variant, category, price subset, image subset, specs field names with tier-3 flags, rating subset, `assess_result` identity confidence, the field_status list); if the exposure flag is ON stamp `field_status`; if the ingest flag is ON `_fire_and_forget(asyncio.to_thread(kb_ingest.run_job, snap), "kb_ingest")`. The response is returned / yielded immediately: its bytes and timing never depend on the job; a job exception is the WARNING of the existing done-callback (`async_utils.py:74-90`) and never reaches the caller. The builder itself runs inside `try/except Exception` (one WARNING `[KB_INGEST] build failed: <type>`; the response untouched).
`run_job(snap)` (worker thread; NO LLM call, NO Serper call, no fetch):
1. `client = _admin_client()`; None -> one WARNING, return.
2. `records = live_robots.records_snapshot() or live_robots.load_records_sync(client)` (flag-free; the D14 verdict data).
3. Per product with `identity_confidence == "high"` and category == KB_CATEGORY and a minted `kb_product_id`: `build_product_row` (identity_confidence "high", concentration = the id's 4th part or None) and `build_variant_row` (`kb_variant_key(pid, conc, size_ml)`; gtin / sku from `_jsonld_facts`); insert-ignore (`upsert(..., on_conflict="id", ignore_duplicates=True)`).
4. Offers (same products): the price passes ALL of: `source_method in _GENUINE_BH_SOURCE_METHODS` and in the rung map (render tiers excluded), not estimated, `canonical_offer_url(price.url)` mints, the price host's record row exists with status live and `live_robots.url_verdict(price.url, row, now) is None`; `merchant_id` = that row's host; market = `"BH"` for region bahrain (else no offer); `observed_currency` = `price["currency"]` (ISO-3); `evidence_rung` = the rung map; `captured_at` = `first_seen` = `last_seen` = the job's ONE captured_at (one observation = one shared last_seen); `in_stock` only when a bool is present. Insert-ignore on KB_OFFER_OBSERVATION_KEY; every row the insert did not return = ONE update of KB_OFFER_UPSERT_SET (the KbWriter.offers rule).
5. Images (same products): `price["image_url"]` accepted by `jsonld_widen.allowed_image_url(img, price.url, OFFICIAL_BRAND_DOMAINS)` AND the price URL's verdict allow -> `build_image_row(source="retailer_jsonld" when `_jsonld_facts` is present else "retailer_og", provenance_host = the price host)`; insert-ignore on (product_id, url). Provenance only (URL + host; never re-hosted).
6. Reviews (same products): `jsonld_rating` present (channel 1 already passed `rating_host_allowed`) -> `build_review_row(source="retailer_jsonld", source_url=jsonld_rating.url, aggregate_rating, review_count)`; insert-ignore on (product_id, source_url); never a Serper / consensus / GPT rating; never a DENY_HOSTS source (the builder's belt).
7. Specs: NONE written (measured 1.3: the live LLM spec values carry snippet indices, not URLs, so no value is "cited" with a source_url; `build_spec_row` refuses `cited=True` without one). Every specs / concentration miss is a gap instead (stated S81-17-L2; the KB specs come from G2 and S81-19).
8. Gaps (identity_confidence high OR medium, a minted product id): for each D05 field other than identity whose state is `unknown` (price `unknown` included; `stale` is not a miss), one `build_gap_row(product_key=pid, field=<the D05 name>, first_seen=captured_at, demand_count=1, state="needs_operator" if the price host's row is blocked else "open", source_hint=<the price host when it is a registry host, else None>)`; at most KB_INGEST_GAP_MAX rows. The D05 names never match `^pdp_` (the G2 R-G2-13 namespace is disjoint; the job asserts it before sending). Q5 increment: (a) ONE insert-ignore batch on (product_key, field); (b) for the rows the insert did not return, ONE select `product_key, field, demand_count, state` with `.in_("product_key", <ids>)` and `.in_("field", <fields>)`; (c) per existing row ONE conditional update `{"demand_count": n + 1, "last_seen": captured_at}` `.eq(product_key).eq(field).eq("demand_count", n)` (compare-and-set); an empty update result = a lost increment counted `gap_cas_lost`, never retried; state / source_hint / first_seen of an existing row never move.
9. ONE INFO line `[KB_INGEST] job products=%d variants=%d offers=%d offer_updates=%d images=%d reviews=%d gaps=%d gap_increments=%d gap_cas_lost=%d not_built=%d` (ints only; never a name, query or URL).
Round trips per job (worst case): 2 (products, variants) + 1 + <= 2 (offers) + 1 (images) + 1 (reviews) + 1 + 1 + <= 14 (gaps) = <= 23, all in the one worker thread. The single-round-trip `kb_ingest_compare` RPC is S81-17b (migration 051, FOCUS) if the canary shows the thread time matters (Q-S17-2).

#### 2.4 Seams
`kb_ingest._now`, `kb_ingest._admin_client`, `kb_ingest.kb_leaf()` (the ONE function-local `from app.services import kb_service as _kb`), `live_robots.records_snapshot` / `load_records_sync`, scs `_fire_and_forget` (the label `kb_ingest`), `asyncio.to_thread` (the RED patches `kb_ingest.run_job` to a blocking recorder to prove the response does not wait).

#### 2.5 Failure table (flags ON)
| input | result |
|---|---|
| moderation refuses | no job, no field_status (the refusal returns / yields before the hook) |
| parse failure, category refusal, INSUFFICIENT_DATA, timeout partial, INTERNAL_ERROR, LLM_UNAVAILABLE | no job, no key (none reaches the hook) |
| build_job raises | one WARNING, the body unchanged, no job |
| no service-role client / Supabase error inside the job | the job ends; the done-callback WARNING; the response already left |
| identity low / unresolved | no rows at all |
| identity medium | gaps only |
| a builder returns None | that row is skipped and counted `not_built` |
| a CAS update loses a race | counted, not retried |

#### 2.6 Flag-OFF identity (the main invariant) and the offload precondition
Both flags OFF: `_kb_ingest_tail` returns after two env reads; no projection, no task, no key. Proven by PIN rows with the FULL configuration (`KB_INGEST_GAP_MAX` set, `ENABLE_SYNC_DB_OFFLOAD` both ways, a raising `_admin_client`, a recorder on `_fire_and_forget` labels and on `asyncio.to_thread`) and the golden digests of `tests/fixtures/s81_s17_flag_off_golden.json` (REST, stream, camera; recorded at base with the FY25 normalisation). `ENABLE_KB_INGEST` ON alone also leaves the body byte-identical (R23). `ENABLE_SYNC_DB_OFFLOAD`: the job is off-loop either way; the precondition stays an owner gate (the plan, :157) because the ingest adds a default-executor thread per compare beside the inline Supabase calls that flag moves.

### 3. Change list (GREEN, after D14's live_robots.py; byte copies first)
1. NEW `app/services/kb_ingest.py`: flags, `field_status`, `build_job`, `run_job`, the writer (the KbWriter semantics re-homed; the table names as module constants `KB_PRODUCTS_TABLE = "kb_products"` etc., one per line), `kb_leaf()` with the one function-local import. Pure ASCII, no `robots_registry` text.
2. `app/services/structured_comparison_service.py`: `from app.services import kb_ingest`; NEW method `_kb_ingest_tail` (beside `_stamp_unit_metadata` :3879); REST call line between the moderation `if not _l3.allowed:` block (ends :4771) and the behaviour-profile block :4773; stream call line after the refusal block (:5685) and before :5692.
3. `tests/test_s81_kb_schema.py` E1 / E2 (4.1).
4. NEW `tests/test_s81_s17_kb_ingest.py` + `tests/fixtures/s81_s17_flag_off_golden.json` (the RED round).
5. CLAUDE.md row (8).
No other file.

### 4. Existing pins
#### 4.1 Deliberate changes
- E1 `tests/test_s81_kb_schema.py:331-335`: P01_ALLOWED gains `("app/services/kb_ingest.py", "from app.services import kb_service as _kb")`; P01_FUNCTIONS gains `"app/services/kb_ingest.py": "kb_leaf"`. Reason: the live writer must call the S81-14 builders (the G2 E1 precedent for scripts/kb_seed_common.py).
- E2 `tests/test_s81_kb_schema.py:336-344`: P02_ALLOWED gains the exact lines `KB_PRODUCTS_TABLE = "kb_products"`, `KB_VARIANTS_TABLE = "kb_variants"`, `KB_OFFERS_TABLE = "kb_offers"`, `KB_IMAGES_TABLE = "kb_images"`, `KB_REVIEWS_TABLE = "kb_reviews"`, `KB_GAPS_TABLE = "kb_gaps"` keyed to `app/services/kb_ingest.py`. Reason: the table names defined once (the G2 E2 precedent). No other pin moves.
#### 4.2 Must stay green and unedited
`tests/test_s75_fanout_identity.py` (FY25 digests with every flag OFF), `tests/test_fire_and_forget_wrap.py`, `tests/test_m13_33_review_fire_and_forget.py`, the S81-10 / S81-10b goldens and gate rows, `tests/test_s81_d08_jsonld_widen.py`, `tests/test_s81_g1_gate_rows.py`, `tests/test_s81_s15_*`, the S81-14 P03-P06 rows, every comm-set member.

### 5. RED tests: `tests/test_s81_s17_kb_ingest.py` (new; pure ASCII; hermetic; the compare driven through the FY25 faked pipeline pattern of `tests/test_s75_fanout_identity.py:100-252` (copied, never imported); the Supabase client an in-memory recorder (table / upsert(on_conflict, ignore_duplicates) / insert / select / in_ / eq / update / execute + the executing thread) that returns configurable `data`; the D14 records seeded through `live_robots.records_snapshot`; recorders that RAISE on `guarded_llm_create`, the Serper search entry points and every fetcher; synthetic identities built at run time)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| S1 | readers | `kb_ingest_enabled`, `field_status_metadata_enabled` exist; padded / upper / garbage rows as L1; re-read per call | RED | 2.1 |
| S2 | field_status full product | a product with a genuine fresh JSON-LD price, an accepted page image, listing size, concentration, specs, channel-1 rating + count -> every field known / fresh; price `as_of` = captured_at Z, rung `page_evidence`, source the price host | RED | 2.2 |
| S3 | field_status misses (parametrized, 11 cases) | placeholder identity; no image; estimated price -> unknown `estimated`; `_cached` True -> stale `served_from_cache`; absent mark -> stale `unmarked`; no size; tier-3 concentration -> `model_knowledge`; only tier-3 specs; derived rating; no review_count; platform method -> rung `platform_api`, converted_usd -> rung None | RED | 2.2 |
| S4 | exposure REST + stream | `ENABLE_FIELD_STATUS_METADATA` ON: the REST success body and the stream `settle_complete` + `complete` payloads carry `metadata.field_status` (a 2-list, the 2.2 vocabulary only); every other key equals the flag-OFF run | RED | 2.2 |
| S5 | exposure camera | the same through `compare_from_text(..., vision_products=[...])`: identity source `vision` | RED | 2.2 |
| S6 | no key off the success exits | moderation refusal (REST + stream), parse failure, timeout partial: no `field_status`, no `kb_ingest` task | RED (the positive half fails at base) | 2.5 |
| S7 | one job per compare | `ENABLE_KB_INGEST` ON: exactly ONE `_fire_and_forget` with label `kb_ingest` per REST compare and per stream compare, created after the moderation call and before the return / the `settle_complete` yield (order recorder); the job callable reaches `asyncio.to_thread` | RED | 2.3 |
| S8 | never awaited | `run_job` patched to block on a threading.Event: the REST body returns and the stream yields `complete` while the job is still blocked; then released | RED | 2.3 |
| S9 | job failure | `run_job` raising: the body equals the no-failure run; one WARNING naming `kb_ingest` from the done-callback | RED | 2.5 |
| S10 | builder-only writes | every row sent has exactly `KB_BUILDER_KEYS[table]`; only kb_products / kb_variants / kb_offers / kb_images / kb_reviews / kb_gaps are touched; never kb_feedback / kb_specs / kb_merchants / kb_coverage_daily; upserts carry `ignore_duplicates=True` | RED | 2.3 |
| S11 | confidence gates | high: cards + offers + images + reviews + gaps; medium (empty brand on one side): gaps only; low (same identity) / unresolved (placeholder): no write at all | RED | 2.3 |
| S12 | offer refusals (parametrized, 10 cases) | converted_usd; estimated; a render-tier method (scrapedo_rendered); non-registry host; row blocked; robots disallow; expired record; origin mismatch; DENY_HOSTS host; region not bahrain -> no kb_offers row; the allowed case writes one row with merchant_id = the row host, market BH, the currency, rung, canonical URL (query dropped), captured_at = first_seen = last_seen | RED | 2.3 |
| S13 | re-observation | the insert returns [] -> ONE update carrying exactly KB_OFFER_UPSERT_SET, filtered on the six observation-key columns | RED | 2.3 |
| S14 | images | an accepted JSON-LD image on an allow host -> one kb_images row (retailer_jsonld, provenance host); an image on a deny host / an http image / a disallow host -> none | RED | 2.3 |
| S15 | reviews | `jsonld_rating` -> one kb_reviews row (retailer_jsonld, source_url, rating, count); a provider (Serper) rating -> none | RED | 2.3 |
| S16 | no specs | verified LLM specs present -> zero kb_specs calls; their misses are gaps | RED | 2.3 |
| S17 | gaps | each unknown field -> one row (product_key = the kb_product_id, field = the D05 name, demand 1, state open, source_hint the registry host); blocked price host -> `needs_operator`; an existing row (insert returns []) -> one select + one CAS update with `demand_count` n+1 and `.eq("demand_count", n)`; an empty CAS result -> `gap_cas_lost` counted, no retry; state / source_hint never in an update payload; no `pdp_` field ever sent; identity misses never written; at most KB_INGEST_GAP_MAX rows | RED | 2.3 |
| S18 | idempotent | the same compare twice: the second job inserts nothing new (insert-ignore) and only updates | RED | 2.3 |
| S19 | budget | the job (run inline) calls no LLM, no Serper, no fetcher (raising recorders) | RED | 2.3 |
| S20 | log line | one `[KB_INGEST] job ...` INFO record per job, ints only (no URL, brand, name or query text) | RED | 2.3 |
| S21 | ingest does not change the body | `ENABLE_KB_INGEST` ON, exposure OFF: REST / stream / camera digests equal the base golden | RED (no job at base; the job-count half fails) | 2.6 |
| P1 | flag OFF identity | FULL config (knob set, `ENABLE_SYNC_DB_OFFLOAD` both ways, raising `_admin_client` installed through a getattr-safe patch that is a no-op at base), flags unset / "false" / " 0 " / "OFF": REST, stream and camera digests == `s81_s17_flag_off_golden.json` (recorded at base); the `_fire_and_forget` label recorder never sees `kb_ingest`; `asyncio.to_thread` never receives a kb_ingest callable | PIN (green at base) | 2.6 |
| P2 | exits untouched OFF | the moderation-refusal and parse-failure bodies equal their base literals | PIN | 2.6 |

Counts (S81-17): 21 RED rows (S3 11 nodes, S12 10 nodes), 2 PIN rows; the final node counts are the RED agent's to report.

### 6. Mutation table
| id | mutant | killed by |
|---|---|---|
| S17-M1 | `_kb_ingest_tail` called BEFORE the moderation pass (REST) | S6 (refusal gets a job) |
| S17-M2 | stream hook after the `settle_complete` yield | S4 / S7 order |
| S17-M3 | the flag check removed (job always built) | P1 |
| S17-M4 | `await asyncio.to_thread(...)` inline instead of fire-and-forget | S8 |
| S17-M5 | the confidence gate `== "high"` widened to `in ("high","medium")` for cards | S11 |
| S17-M6 | the robots verdict skipped for offers | S12 (disallow / expired / origin) |
| S17-M7 | converted_usd admitted to offers | S12 |
| S17-M8 | the CAS `.eq("demand_count", n)` dropped | S17 |
| S17-M9 | the `pdp_` guard dropped and a field renamed `pdp_price` | S17 |
| S17-M10 | `ignore_duplicates=True` dropped (overwrite) | S10 / S18 |
| S17-M11 | field_status written with the exposure flag OFF (ingest ON) | S21 |
| S17-M12 | kb_specs written from verified LLM specs | S16 |

### 7. Comm set, gates
The group set (12.1). Gates for GREEN, cheapest first: py_compile + ruff on kb_ingest.py, scs; the RED file OFF and ON (`ENABLE_KB_INGEST=true ENABLE_FIELD_STATUS_METADATA=true` in the runner's environment only); `tests/test_s81_kb_schema.py` after E1 / E2; FY25; the comm chunks at HEAD vs the cached base record.

### 8. CLAUDE.md row and owner steps
- `ENABLE_KB_INGEST` + sub-flag `ENABLE_FIELD_STATUS_METADATA` + knob `KB_INGEST_GAP_MAX` (16, 1..64) (S81-17 KB-INGEST with D05 FIELD-STATUS, `app/services/kb_ingest.py`): at the two success exits ONLY (REST after the L3 moderation pass, before `return result`; stream after it, before the `settle_complete` yield; the camera path through the same exit), a plain-data projection is built on the loop (no I/O) and, with `ENABLE_KB_INGEST`, ONE `_fire_and_forget` (label `kb_ingest`) wrapping ONE `asyncio.to_thread` job writes through the S81-14 builders with the service-role client (insert-ignore): kb_products / kb_variants at identity confidence high (`result_gate.assess_result`, flag-free), kb_offers only for genuine non-render methods on a live registry host whose persisted robots verdict allows the URL (`live_robots.url_verdict`), market BH, one shared last_seen per observation, kb_images (the page image under the D08 policy), kb_reviews (channel-1 JSON-LD aggregates only); NO kb_specs (no per-field source URL on the live path) and no kb_feedback; every unknown D05 field of an identity-high/medium product becomes a kb_gaps row (insert-ignore, then compare-and-set `demand_count` + last_seen; a lost race is counted, never retried; `needs_operator` when the price host is blocked; never the G2 `pdp_` namespace). No LLM call, no Serper call; one INFO count line per job. `ENABLE_FIELD_STATUS_METADATA` adds `metadata.field_status` (per product: identity, image, price fresh/stale/unknown + as_of + rung, size, concentration, specs, rating, review_count; each {state, source, reason}). Both OFF: byte-identical (PIN P1 goldens).
- Owner steps (names only): (1) apply 045 (owner item 29); (2) `ENABLE_SYNC_DB_OFFLOAD` ON on web with its canary; (3) `ENABLE_LIVE_ROBOTS_REGISTRY` is NOT required for ingest (the verdict data is read flag-free) but the robots cron must have run (no record = no offer); (4) flip `ENABLE_KB_INGEST` on web in a canary window: watch the `kb_ingest` WARNING rate, the `[KB_INGEST] job` counts, kb_gaps growth, /health loop lag and executor pressure; (5) `ENABLE_FIELD_STATUS_METADATA` with the S81-11 OTA (after approval).

### 9. Stated limits
- S81-17-L1: identity confidence is a PAIR value; both products are carded or neither.
- S81-17-L2: no kb_specs from the live path (no per-field source URL); spec knowledge comes from G2 / S81-19.
- S81-17-L3: demand_count increments use compare-and-set without retry; concurrent compares of the same product within one read-update window lose increments (counted `gap_cas_lost`); exactness needs the S81-17b RPC.
- S81-17-L4: up to about 23 PostgREST round trips per job on one default-executor thread (no migration allowed); S81-17b collapses them into one RPC.
- S81-17-L5: a kb_reviews / kb_images row is first-observation-wins (insert-ignore); refresh is S81-19's.
- S81-17-L6: price `stale` carries no as_of (the price dict holds no fetch timestamp; `_cached` only).
- S81-17-L7: a gap row's state is set at insert only; a host blocked later does not move an existing gap to needs_operator.
- S81-17-L8: market is BH only (the only region the app serves).

### 10. Out of scope
kb_feedback (S81-21), compare_runs (S81-22), the KB-first serve (S81-18), kb_specs from the live path, the RPC (S81-17b), price refresh, the operator queue UI (D16), any client change (S81-11).

### 11. Open questions
- Q-S17-1: the exposure sub-flag `ENABLE_FIELD_STATUS_METADATA` (spec ruling) vs riding `ENABLE_KB_INGEST`.
- Q-S17-2: S81-17b (`kb_ingest_compare` RPC, migration 051, FOCUS) now or after the canary measures the thread time?
- Q-S17-3: gaps for identity-medium products (spec: yes) or high only?

## 12. The group

### 12.1 Combined comm set (the union rule)
Derivation (`<scratchpad>/g3spec/comm.py`, re-runnable): every `tests/test_*.py` / conftest.py whose text references any of `structured_comparison_service, price_service, shopify_pdp_service, woocommerce_service, algolia_service, url_extraction_service, jsonld_widen, robots_registry, merchant_registry, kb_service, deny_hosts, async_utils, result_gate, app.main, "app import main", kb_ingest, live_robots` (427) UNION every test that reads source by path / module path / glob / ast / os.walk / `"app"` segments / .github / SmartCompareApp / CLAUDE.md (261) = 515, UNION the stored G1 (592), G2 (68) and S81-10b (108) comm sets (files that still exist), MINUS the four `test_precommit_hook*.py` = **609 files**, list `<scratchpad>/g3spec/comm_final2.txt`, sha256 `ba26af35866801b40d145a9735a7797b0677efacf71e2154b8bb18b4a70093ec`. It holds the CLAUDE.md readers (`test_ci_gates.py`, `test_behavior_dimension_translation.py`), `test_s81_kb_schema.py`, `test_secret_scan_static.py`, `test_hermeticity_pins.py`, the S81-15 / D08 / G1 / G2 / S81-10 / S81-10b files, `test_s80_url_mode_v2.py`, FY25. Plus the two new RED files at HEAD. Chunks of at most 25 files, bound 1200, base vs HEAD `comm -13` of the FAILED node ids EMPTY (base reused per LC-6 once stored).
### 12.2 CI-order set (one process, alphabetical, bound 1200)
`tests/test_s81_d14_live_robots.py tests/test_s81_s17_kb_ingest.py tests/test_s81_kb_schema.py tests/test_s81_s15_registry_robots.py tests/test_s81_d08_jsonld_widen.py tests/test_s81_g1_gate_rows.py tests/test_s75_fanout_identity.py tests/test_s80_url_mode_v2.py tests/test_shopify_pdp_json.py tests/test_woocommerce_adapter.py tests/test_algolia_service.py tests/test_url_extraction.py tests/test_fire_and_forget_wrap.py tests/test_s81_s10_fragrance_gate.py tests/test_s81_s10b_links_gate.py`, OFF and with the four flags ON.
### 12.3 Combined footprint
NEW: `app/services/live_robots.py`, `app/services/kb_ingest.py`, two RED files, two golden fixtures. EDITED: `app/services/{structured_comparison_service,price_service,shopify_pdp_service,woocommerce_service,algolia_service,url_extraction_service}.py`, `tests/test_s81_kb_schema.py` (E1 / E2), `CLAUDE.md`. 14 files. No migration, no Lua, no route, no middleware, no legal text, no client file, no requirements change.
### 12.4 Shared-file plan
0.3. The scs hunks: (a) two imports; (b) `_init_provider_attempts` one line (D14); (c) `_kb_ingest_tail` method (S81-17); (d) REST call line (S81-17) and REST `finally:` (D14); (e) stream call line (S81-17) and stream `finally:` (D14). GREEN applies D14 (b, d-finally, e-finally) then S81-17 (c, d-call, e-call).
### 12.5 PR plan
ONE PR from `feature/s81-g3-kb-ingest`, body at most 25,600 bytes (measured with python): summary; one short section per unit (MYEZ / defect ids D05, D14, S81-17 -> RED nodes -> flag -> preconditions); the E-rows (E1, E2); the counts; the stated limits by id; owner steps names only (apply 045 then 047 (item 29); ENABLE_SYNC_DB_OFFLOAD ON before ENABLE_KB_INGEST; the robots cron at 100 % + the M6 dry run before ENABLE_LIVE_ROBOTS_REGISTRY; the canary items: the ingest job WARNING rate, kb_gaps growth, robots_skip per host, /health loop lag); mutation tables and gate logs filed as specs/ files and referenced by name.
### 12.6 The adversary's folded engineering checks (LC-1)
(1) flag-OFF byte identity at every hook site: goldens + raising recorders + the corpus SHA base == head; (2) no `robots_registry` text in app/ outside the two S81-15 modules and no `kb_merchants` text in the hooked fetchers (p5); (3) the job never awaited on the response path, never raising to the caller, never on a refusal / partial; (4) builder-only writes and insert-ignore; no kb_specs / kb_feedback; (5) the CAS payload never carries state / source_hint; (6) the UA unchanged under the flag; (7) the log lines host / constants / ints only; (8) the importers of every edited module in the comm set (app/main.py importers included); (9) CRLF preserved (no whole-file diff in `git diff --stat`); (10) PR body size.
### 12.7 SAFE check (the FOCUS surfaces, each measured)
| surface | touched? | evidence |
|---|---|---|
| auth / tokens / sessions | no | no auth module, no route, no header read (request_context unread) |
| quota / billing / refunds | no | usage_service, the Lua, the metering paths untouched; the job runs after the response and never refunds |
| legal or privacy text | no | no app/legal, processors.json, consent copy (no new processor or host) |
| consent path | no | consent_version unread |
| security middleware | no | app/middleware untouched; the SSRF validators are called unchanged (the gate is ADDED before them) |
| migrations | no | none added; 045 / 047 / 050 untouched; the RPC is S81-17b |
| Redis / Lua scripts | **YES (D14 health flush only)**: one Upstash REST pipeline of HINCRBY + EXPIRE counters per compare under `ENABLE_LIVE_ROBOTS_HEALTH_FLUSH`, a new key namespace `kbh:`; no Lua, no EVAL, no quota / usage key, fail-open | 1.6 / 2.2 of D14 |
| App-Review-visible client surface | no client file; backend responses change only under default-OFF flags (an additive `metadata.field_status`; URL mode STORE_UNREADABLE with reason `robots_skip`, a code build 3 already renders) | 2.2 / 2.3 |
| secrets or key handling | no | no credential name read; the existing admin client and Redis client reused |
The group is SAFE except the one Redis touch, which is isolated behind its own sub-flag and severable: if the orchestrator rules it FOCUS, GREEN omits `flush_attempts`'s Redis job (the aggregator then ends in ONE INFO count line per compare), L8 / L9 / D14-M8 / D14-M9 move to a D14b RED file, and the rest of G3 stays SAFE with no other change.

## Not done in this spec
No code, no RED file, no fixture written; the comm-set base record and the fourteen client fences not run; the corpus gate run at base only (head is GREEN's); no DEFECT_LEDGER / PLAN_STATUS edit (rows drafted in 0.4 for the orchestrator).
