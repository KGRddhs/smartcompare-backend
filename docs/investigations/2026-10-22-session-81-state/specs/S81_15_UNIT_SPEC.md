# S81-15 unit spec (measured): REGISTRY-ROBOTS-DENY, the merchant registry from kb_merchants + the daily QarenBot robots cron

- Unit: S81-15 REGISTRY-ROBOTS-DENY (backend, lane B, one PR, two dark flags `ENABLE_MERCHANT_REGISTRY_DB` + `ENABLE_ROBOTS_REGISTRY_CRON`, both default OFF, read per call). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s81-s15`, branch `feature/s81-s15-registry-robots-deny`, base main `dfc6502f791cdccbf0a620041f66888a734015d3` (`git rev-parse HEAD` = that sha; `git status --short` empty at the start and after every probe below; `.qa-s80/` is gitignored by `.gitignore:72` `.qa-*/`).
- Evidence: PLAN_S81 M4 unit text S81-15 (`PLAN_S81.md:154`), the VERIFY "Knowledge base, registry, crawler" bullets (`:88`, `:89`), Fable ruling F1 and F4 (`:123`), owner decisions 7 and 11 (`:203`, `:209`), the unit brief `specs/S81_15_BRIEF.md`, research digests `runs/research/A3.json` (registry fit, robots enforced only off-clock), `R4.json`, `R13.json`, `R15.json` (country is "serves BH", not currency), `runs/measure/registry_fragrance.json` (S81-02), the robots ruling `docs/policies/2026-08-31-robots-unreadable-ruling.md` (fail-closed, Option A re-read + Option C rider).
- Sister units and contracts: S81-14 KB-SCHEMA (migration 045 `kb_merchants`; its spec did not exist when this spec was measured (searched 15:03 and 15:31 AST), so the column list below is read from `specs/S81_14_BRIEF.md` item 1 and the extra columns this unit needs are stated as a binding dependency in 2.2 and question Q1); D03 DENY-AND-GUARDS (merged #368: `deny_hosts.DENY_HOSTS`, `is_denied_host`, `kb_source_allowed`, the `_routable_registry` filter and its identity pin); D14 LIVE-ROBOTS (owns every live per-fetch robots lookup; this unit only produces verdicts); D16 OPERATOR-INGEST (owns the admin view of the blocked list); S81-16 / D09 (the next robots consumers). Known rebase: the CLAUDE.md SESSION 81 anchor (after the S81-03 row, `CLAUDE.md:485-486` at base) is shared with every S81 unit row.
- Production flag state: the newest dated ledger line (`2026-10-22-session-81-state/ledger.md`, 14:25 AST 2026-10-23) records no state for `ENABLE_BH_GCC_CATALOG_SOURCES`, `ENABLE_LONGEST_HOST_MATCH`, `ENABLE_SYNC_DB_OFFLOAD` or `ENABLE_DATA_GUARDS_V2` beyond "every flag OFF in production" for the S81 flags; CLAUDE.md:341 says the catalog flag is ON since 2026-06-26, but by R-A15 that is documentation, not a ledger line. The design therefore holds in BOTH catalog states (rows R8, R12). The two new names are unset in production by construction.
- Personal-data rule: no real name, email, phone, address, device id or account id appears in this file or anything the unit writes; hosts are public merchant domains or synthetic `.test` hosts; every credential in tests is a synthetic value built at run time. The QarenBot UA string is reused by symbol (`sitemap_discovery_service._ROBOTS_UA`), never retyped.
- Measurement location: `C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fd8b3d1b-a491-48e3-953f-ca3a804fd9ca\scratchpad\S81-15\` (`notes.md`, `probe_catalog.py/.out`, `probe_registry.py`, `probe_registry_off.out`, `probe_registry_on.out`, `probe_seed_counts.py/.out`, `base_reg.log`, `base_pins.log`, `comm_set.txt` and its five parts). Nothing in the worktree was written except this file.

## 0. What the unit does

Behind `ENABLE_MERCHANT_REGISTRY_DB` (default OFF, read per call): the routed merchant registry (every `source_router` consumer, plus three direct readers) comes from the `kb_merchants` table through a per-process memo (window `MERCHANT_REGISTRY_MEMO_SECONDS`, default 600, clamped 300..900) refreshed by ONE Supabase read through `run_db`, scheduled off the request path (stale-while-revalidate on the running loop) and keyed on the table snapshot (max `updated_at` + row count). Any read failure, an empty or truncated result, or a call before the first refresh lands serves the in-code `SOURCE_REGISTRY` (fail-open to today's registry, one WARNING by type per process per window). Only rows with `status = 'live'`, `deny = false` and a host that `deny_hosts.is_denied_host` does not match are routed; `blocked` and `candidate` rows never are. Flag OFF the accessor returns `SOURCE_REGISTRY` itself (identity) and nothing else is read. An off-clock, owner-run `scripts/seed_kb_merchants.py` builds the table from the 44 literal rows and the 368 rows of `data/bh_gcc_sources.json` (410 hosts: 317 live, 92 candidate, 1 blocked = fragrantica.com as `deny`), dry run by default. Behind `ENABLE_ROBOTS_REGISTRY_CRON`: `scripts/cron_robots_registry.py` (a Railway cron on the worker service) reads `/robots.txt` of every due live or candidate host once a day as QarenBot (concurrency 1, delay max(Crawl-delay, 2 s)), applies the fail-closed rule (404/410 allow; any other non-2xx, a timeout, an error or a challenge page = unreadable -> blocked `robots_unreadable`; the most restrictive of the QarenBot and `*` groups decides), parks a challenged host (`challenge.parked_until`, blocked `challenge`), records `robots {state, status, body_sha, fetched_at, next_reread, crawl_delay}`, lets a cron-blocked host rejoin when a later read allows it (Option A), and promotes a candidate to live only when robots allow AND the owner's ToS verdict is `allowed` AND one validated PDP AND a known platform; otherwise the failing gate is named. No live fetcher reads robots in this unit (D14). Partner / CTA fields are stored and never read by scoring.

## 1. Base state (measured at dfc6502f)

### 1.1 The registry today

| what | where | measured fact |
|---|---|---|
| `Source` | `app/services/source_router.py:30-97` | frozen dataclass, 19 fields in order: `domain, tier, categories, weight, usage, is_shopify, is_render_only, is_algolia, requires_super, locale_paths, subdomain_patterns, currency, discovery_query_templates, mechanism, pdp_url_pattern, sample_url, status, priority_rank, search_descriptor` (probe_registry_off.out). Tuple defaults are bare `()`. |
| literals | `_LITERAL_ROWS` `:98-372` | 44 rows (24 bahrain, 9 gcc, 11 global); non-default fields used by literals: is_algolia 2, currency 8, mechanism 7, is_render_only 5, subdomain_patterns 2, pdp_url_pattern 5, sample_url 5, status 5, locale_paths 3, requires_super 1, discovery_query_templates 1, is_shopify 5, usage 3 (fields the catalog loader never maps, A3). `noon.com` is a literal TWICE: index 23 (`:308`, gcc, is_render_only) and index 24 (`:329`, bahrain, `mechanism="noon_catalog"`), ordered deliberately so first-match readers resolve noon to gcc (comment `:309-328`). `fragrantica.com` is index 38 (`:349`, global, fragrances, 1.0), the only literal `is_denied_host` matches. `footlocker.com.bh` (`:281`) is also a json row (status dead). |
| catalog file | `data/bh_gcc_sources.json` | a list of 368 rows; keys `domain, tier, weight, categories, mechanism, is_shopify, is_algolia, is_render_only, currency, country, genuine_method, sample_url, priority_rank, status` on every row, `search` on 95, `note`/`measured` on 4; status live 275 / dead 61 / provider-test-candidate 18 / render-only 14; live mechanisms: blank 199, shopify 33, woo_store_json 30, salla_api 4, magento_graphql 3, algolia 3, occ_rest 2, rest_json 1; tier bahrain 132 / gcc 236; country BH 145, UAE 62, KSA 57, QA 38, OM 38, KW 28; no duplicate domain, no `www.`, no upper case, no deny-label host (probe_catalog.out). Every json row builds a `Source` through `_row_to_source` when its status is forced to live (0 rejects, probe_seed_counts.out). |
| loader | `:380-534` | `_CATALOG_DATA_PATH` `:408-410`; `_ADMITTED_STATUSES = {"live"}` `:417`; `_VALID_TIERS` `:424`; `_row_to_source(row)` `:427-472` (never raises; maps only domain, tier, categories, weight, is_shopify, is_algolia, is_render_only, currency, mechanism, sample_url, status, priority_rank, search); `_catalog_sources_enabled()` `:475-485` (`ENABLE_BH_GCC_CATALOG_SOURCES`, house idiom, read when called); `_load_catalog_rows()` `:488-529` (flag OFF -> []; dedup: a catalog domain equal to or a subdomain of a literal domain, or a repeat, is skipped). `SOURCE_REGISTRY = _LITERAL_ROWS + _load_catalog_rows()` `:534`, assembled ONCE at import: catalog OFF 44 rows and `SOURCE_REGISTRY == _LITERAL_ROWS`; catalog ON 319 rows = 44 + 275 (no live json row is deduped) (probe_registry_on.out). Admitting a host needs a code change or a restart (the defect). |
| D03 accessor | `_ROUTABLE_MEMO` `:545`, `_routable_registry()` `:548-558` | flag `ENABLE_DATA_GUARDS_V2` OFF -> `return SOURCE_REGISTRY` (identity); ON -> a list of the same rows minus denied hosts, memoised while `memo[0] is SOURCE_REGISTRY`. |
| consumers through `_routable_registry` | `_registry_row_for_host` `:588-622` (flag `ENABLE_LONGEST_HOST_MATCH` `:571-585`), `match_registry_apex` `:625-639`, `registry_tier` `:642-672`, `get_sources_for_category` `:701-735`, `get_shopify_/algolia_/jsonapi_/curl_pagescrape_/sitemap_sources_for_category` `:738-846`, `_direct_fetch_sources` `:856-871` (+ the seven mechanism selectors `:874-908`), `get_gcc_shopify_pagescrape_sources_for_category` `:911-953`, `source_usage` `:956-978`, `score_source` `:981-1007`, `is_render_only_domain` `:1182-1203`, `build_site_discovery_query` `:1207` | all iterate `_routable_registry()`; `search_descriptor_service.descriptor_for_host` (`:201-234`, measured to `:236`) and `shopify_pdp_service` (`:743`) reach rows through `_registry_row_for_host`. Registry ORDER is load-bearing: first-match-wins resolution (noon), selector order, and the `(tier, priority_rank, registry index)` fan-out sort. |
| direct readers of `SOURCE_REGISTRY` outside source_router | `cache_service._registry_domains` `:521-534` (admin dashboard probe list); `magento_graphql_service._expected_currency_for` `:277-301` (exact-apex currency, `:294-295`); `price_service._curl_timeout_for_url` `:14876-14893` (live: bahrain-tier hosts get `BH_REGISTRY_CURL_TIMEOUT`, `:14881-14885`); `structured_comparison_service._bh_locale_known_retail_domains` `:2852-2875` (memoised ONCE per process in `_BH_LOCALE_KNOWN_DOMAINS`, reads SOURCE_REGISTRY + every json row regardless of status) | D03 left all four untouched (D03 spec L3). Scripts reading the code registry: `scripts/verify_source_registry.py:38`, `build_source_registry_data.py:347`, `verify_bh_gcc_sources.py`. |
| `Source.status` | grep over source_router / scs / price_service | no consumer reads `Source.status` (only `_row_to_source` filters on the json status). |

### 1.2 Robots, challenge and PDP code that exists

| what | where | measured fact |
|---|---|---|
| evaluator | `app/services/robots_eval.py:1-230` | pure, offline, never raises; `NAMED_AGENT = "QarenBot"` `:74`; `parse_groups` keeps only allow/disallow lines (Crawl-delay is NOT parsed); `can_fetch(body, agent, url)` `:204-230`: most specific named token, else every `*` group merged; empty/unparseable body = allow; the caller must never pass `""` for a FAILED fetch (module docstring, the ruling). `can_fetch(body, "*", url)` evaluates the `*` groups (no token is a substring of `"*"`). |
| the one robots fetch + UA | `sitemap_discovery_service.py:383-417` | `_ROBOTS_UA = "%s/1.0 (+https://getmyez.com/bot; contact: <first-party support address>)" % robots_eval.NAMED_AGENT` `:387-389`; `_ROBOTS_TIMEOUT = 20` `:390`; `_default_robots_fetch` uses `curl_cffi.requests.get` with that UA and NO `impersonate` in `asyncio.to_thread` `:399-416`; `_robots_policy` `:419-453`: 2xx -> body, 404/410 -> `""` allow-all, anything else or an exception -> `None` = unreadable (fail-closed); its WARNING lines carry the exception text (pre-existing; the new code logs types only). |
| descriptor probe | `search_descriptor_service.probe_search_descriptor` `:445-...`, `RobotsUnreadableError` `:84` | the second off-clock enforcer. |
| challenge signature | `price_service.classify_capture(html, price=None, http_status=None)` `:13005-13071`; `_WALL_HTTP_STATUS` = {401, 403, 407, 429, 451, 511} + 520..530; `_WALL_SIGNATURES` `:12862-12874` (cloudflare `cf_chl_opt`/`__cf_chl_`/"just a moment", perimeterx `px-captcha`, imperva `_incapsula_`/`incap_ses`, distil, "access denied", ...); anchored variant behind `ENABLE_WALL_SIGNATURE_ANCHOR` (`wall_anchor_enabled` `:12958-12981`) | returns `CAPTURE_WALLED` / `CAPTURE_EMPTY_SHELL` (< 30,000 bytes) / ...; no vendor label. |
| PDP URL check | `price_service.validate_scrape_url(url)` `:1007-1029` | http(s), a dotted netloc, no `/search`, `/category`, `/collection`, `/c/`, `/s?k=`, `/browse`; under `ENABLE_DATA_GUARDS_V2` a denied URL is refused first. |
| platform | `platform_router.detect_platform(html, url="")` `:558-600`, `detect_platform_verdict(html, url, robots_txt)` `:515-555` | labels in `COMMERCE_PLATFORMS` (`:155-160`, incl. `unknown`); evidence order markup, URL, robots body; never raises. |
| SSRF guard | `app/utils/url_validator.validate_external_url(url)` `:312`, `validate_external_url_async` `:375` | resolves the host and refuses private / loopback / link-local. |
| DB read helper | `app/utils/db_offload.run_db(call)` `:35-40` | `async def`; `ENABLE_SYNC_DB_OFFLOAD` ON -> `asyncio.to_thread(call)`, OFF -> `call()` inline (blocks the loop for the call). |
| admin client | `database_service.get_admin_supabase_client()` `:239` | service-role client; raises `ValueError` when `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` are unset; `database_service` calls no `load_dotenv`. |
| cron house pattern | `scripts/cron_index_sitemaps.py` | module docstring with the Railway registration steps; `load_dotenv(override=False)` in a try at import; `async def main()` returns None when the flag is off with one INFO; `run = main` alias; failures swallowed and logged. |

### 1.3 Flag-reader idiom

`os.getenv("ENABLE_X", "false").strip().lower() in ("true", "1", "yes", "on")`, read per call, the FIRST statement of the new predicate (D03 `deny_hosts.data_guards_v2_enabled` `:114-116`). Knobs parse defensively: unset, blank, garbage, `nan`, `inf`, `<= 0` fall back to the default; finite values outside the clamp are clamped.

### 1.4 Libraries on the pinned venv (`.venv-qaren`, matches the locks)

`supabase 2.31.0`, `postgrest 2.31.0`, `curl_cffi 0.16.1`, `httpx 0.28.1`, `pytest 9.1.1`, `pytest-asyncio 1.4.0`, `pytest-timeout 2.4.0`. **Protego is NOT installed and is in neither lock** (`pip list`, `requirements*.txt`): the crawl-delay parse is in-house stdlib code (2.5); Protego as an oracle is question Q4 (a dev-lock addition is a package command, the orchestrator's).

### 1.5 Guards the new code must not trip

- `tests/test_s81_d03_deny_and_guards.py::test_r1i_single_deny_literal_list` (`:587`): no second banned-host literal container anywhere under `app/` (new modules use `deny_hosts` functions only).
- `tests/test_legal_docs_u8.py::test_t7b_external_hosts_and_clients_map_to_manifest` (`:1039`): no external-host URL literal (first-party `getmyez.com` / `qaren.app` exempt, `:759`) and no `create_client` / `OpenAI` / `Redis` construction in a new `app/services` module (use `get_admin_supabase_client`; f-string URLs carry no literal host).
- The U3c / model-config / prompt-fence AST pins (no LLM call is added). The `tests/_env_safety.CREDENTIALS_UNSET` rule: no new credential name is read (the seed and cron reuse `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`).
- The netguard: every fetch in tests is an injected recorder; the real fetcher is never called by a test.
- D03 `_ROUTABLE_MEMO` (strong reference, `memo[0] is reg`): the DB list must be a STABLE object across same-snapshot refreshes (R16), or D03 re-filters on every refresh.

### 1.6 Line endings

Every touched backend file is `i/lf w/crlf` (`git ls-files --eol`: source_router.py, price_service.py, cache_service.py, magento_graphql_service.py, CLAUDE.md, scripts/cron_index_sitemaps.py, tests/test_s81_d03_deny_and_guards.py). Edits keep CRLF (the Edit tool preserves it); new files are LF and pure ASCII; `git diff --stat` must show no whole-file diff.

### 1.7 Seed counts (measured, probe_seed_counts.out)

Literal entries 44 on 43 hosts (noon.com carries entries 23 and 24); json rows 368, one collides with a literal host (`footlocker.com.bh`, json status dead: the literal wins, the json entry is not seeded); catalog hosts 367; hosts total 410; denied hosts 1 (`fragrantica.com`); live hosts 317 (42 literal hosts + 275 json live); candidate hosts 92 (61 dead + 18 provider-test-candidate + 14 render-only, minus the collision); live blank-mechanism json rows 199; json sample_url empty 0, literal sample_url empty 39; `/products.json` sample urls 66.

### 1.10 Base pass state (bounded runner, one process at a time, every unit flag unset)

- Registry / router / robots / descriptor / platform / curl-timeout / dashboard / UCP / D03 / liveness / descriptor-fields / render-only / tier15 gate (18 files: `test_bh_gcc_registry_loader.py, test_m13_registry_longest_host.py, test_source_router_bahrain_first.py, test_source_router_discovery.py, test_source_router_liveness_i53.py, test_source_router_shopify_l13.py, test_robots_unreadable_ruling.py, test_search_descriptor_d3.py, test_platform_router.py, test_bh_registry_curl_timeout.py, test_bahrain_source_matrix_coverage.py, test_tier15_hit_rate_metric.py, test_ucp_json_price.py, test_s81_d03_deny_and_guards.py, test_registry_liveness_gate.py, test_source_descriptor_fields.py, test_is_render_only_flag.py, test_tier15_registry_gate.py`): 865 passed, 3 skipped, 1 deselected.
  `[pyt] tag=s15-base-reg start=2026-10-23 15:25:57 end=2026-10-23 15:27:19 elapsed=83s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 865 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- Pins (8 files: `test_legal_docs_u8.py, test_sitemap_discovery.py, test_magento_gql_adapter.py, test_cron_eval_nightly.py, test_hermeticity_pins.py, test_model_config.py, test_model_config_enforced.py, test_u3c_store_false_pin.py`): 304 passed.
  `[pyt] tag=s15-base-pins start=2026-10-23 15:36:32 end=2026-10-23 15:39:45 elapsed=193s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 304 test(s)`; `[netguard] blocked 22 attempt(s) from 21 node(s)` (all inside `test_hermeticity_pins.py`, whose rows assert the guard blocks them; designed, not egress).

## 2. Contract

Contract freeze (PLAN_S80 section 0, `runs/research/contract_freeze.json`): this unit adds no response key, no status code, no refusal and no client-visible text. Flag ON changes only WHICH registry rows route (a host the cron blocked leaves the routed set at the next refresh; a promoted candidate joins it). No bare 503 is possible from this unit (it raises nothing on the request path).

### 2.1 Flags and knobs

| name | reader | default | parse |
|---|---|---|---|
| `ENABLE_MERCHANT_REGISTRY_DB` | `merchant_registry.merchant_registry_db_enabled()` | OFF | house idiom, per call |
| `ENABLE_ROBOTS_REGISTRY_CRON` | `robots_registry.robots_registry_cron_enabled()` | OFF | house idiom, per call (read first in the cron `main`) |
| `MERCHANT_REGISTRY_MEMO_SECONDS` | `merchant_registry.memo_seconds()` | 600.0 | float; unset/blank/garbage/nan/inf/<= 0 -> 600; else clamped to [300, 900]; read at every freshness check |
| `ROBOTS_CRON_MAX_HOSTS` | `robots_registry.max_hosts_per_run()` | 500 | int; garbage/<= 0 -> 500; clamped [1, 5000] |
| `ROBOTS_CHALLENGE_PARK_DAYS` | `robots_registry.challenge_park_days()` | 7 | int; garbage/<= 0 -> 7; clamped [1, 30] |
| `ENABLE_BH_GCC_CATALOG_SOURCES` (existing) | `source_router._catalog_sources_enabled()` | as today | read at every DB refresh under the new flag (R12) |

### 2.2 kb_merchants: the columns this unit reads and writes (dependency on S81-14 045)

From `specs/S81_14_BRIEF.md` item 1: `host` (PK), `country`, `currency_hint`, `platform`, `platform_confidence`, `adapter`, `search_template`, `robots` jsonb, `politeness` jsonb, `health` jsonb, `challenge` jsonb, `tos` jsonb, `deny` bool, `status` (candidate | live | blocked), `blocked_reason`, `partner` jsonb, `created_at`, `updated_at`.

**Binding addition (D-1), measured necessity:** a lossless registry needs every `Source` field, and `host` as a PK cannot hold the two `noon.com` literal rows. This unit therefore requires ONE more column in 045: `registry jsonb NOT NULL DEFAULT '[]'::jsonb` = an ARRAY of entries, one per registry row on that host, each entry `{order:int, origin:"literal"|"catalog", tier, categories:[str], weight:number, usage, is_shopify, is_render_only, is_algolia, requires_super, locale_paths:[str], subdomain_patterns:[str], currency, discovery_query_templates:[str], mechanism, pdp_url_pattern, sample_url, status, priority_rank:int, search: <SearchDescriptor.to_row()> | null}`. `order` = the literal index (0..43) for literals and `1000 + json index` for catalog rows, so a flattened, order-sorted read reproduces `_LITERAL_ROWS + catalog` exactly. If 045 freezes without it, this unit adds `migrations/051_kb_merchants_registry.sql` (+ rollback) with the one `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` and a PRECHECK / POSTCHECK pair (question Q1). Writers set `updated_at` explicitly to ISO UTC now on every insert and update (no dependency on a trigger). `platform_confidence` is read and written as text in {`mechanism`, `probe`, `url`} or null (Q6 if 045 types it otherwise).

Keys this unit owns inside the jsonb columns: `robots = {state: "allow"|"disallow"|"unreadable", status: int|null, body_sha: str|null, fetched_at: ISO str, next_reread: ISO str, crawl_delay: float|null}`; `challenge = {vendor: str, parked_until: ISO str}` or `{}`; `health = {pre_block_status: "live"|"candidate", promotion: {failing_gate: "robots"|"tos"|"pdp"|"platform", checked_at: ISO str}}` (either key optional); `tos` is READ only (`verdict`, `reviewed_at`, `terms_url`; written by the owner / D16). `blocked_reason` in `BLOCKED_REASONS = ("deny", "robots_unreadable", "robots_disallow", "challenge", "owner")`; the cron manages only `robots_unreadable`, `robots_disallow`, `challenge`; `deny` and `owner` are sticky (never changed, never fetched).

### 2.3 `app/services/merchant_registry.py` (new leaf; imports stdlib, `deny_hosts`, `app.utils.db_offload.run_db`; `source_router` and `database_service` lazily inside functions)

- `merchant_registry_db_enabled() -> bool`; `memo_seconds() -> float`.
- `KB_MERCHANTS_TABLE = "kb_merchants"`; `READ_COLUMNS = "host,status,deny,blocked_reason,registry,partner,updated_at"`; `MAX_ROWS = 1000` (the Supabase PostgREST default page; a result with `len >= MAX_ROWS` is treated as truncated).
- `registry_rows(fallback: list) -> list` (called only by `source_router.registry_rows()`): flag OFF -> `return fallback` FIRST (no other read). Flag ON -> if the memo is fresh (`_monotonic() - loaded_at < memo_seconds()`) return the memo's list (the DB list, or `fallback` after a failure); else try `asyncio.get_running_loop()`: when a loop runs in this thread and no refresh task is pending on THAT loop, create exactly one task `refresh_merchant_registry()` and keep a strong reference (`_REFRESH = (loop, task)`); never awaits, never blocks; return the stale memo list if one exists, else `fallback`. A call from a thread with no running loop schedules nothing.
- `async refresh_merchant_registry() -> None` (never raises): `result = await run_db(lambda: _admin_client().table(KB_MERCHANTS_TABLE).select(READ_COLUMNS).execute())` (ONE read; the client is built inside the lambda); `rows = result.data`; failure classes -> memo = (`None` list marker meaning "serve fallback", snapshot None, loaded_at = now) and ONE WARNING per window `"[MERCHANT_REGISTRY] read failed reason=%s; serving the code registry"` with `type(exc).__name__`, or the constants `not_a_list`, `truncated`, `empty`. Success: `snapshot = (max(str(updated_at)), len(rows))`; equal to the memo's snapshot -> keep the SAME list object, bump loaded_at; else decode (2.4) and store a new list; one INFO per rebuild `"[MERCHANT_REGISTRY] refreshed hosts=%d routed=%d blocked=%d candidate=%d skipped=%d"` (ints only).
- `partner_for_host(host) -> Optional[dict]`: flag OFF -> None with no read; ON -> the memoised `partner` dict of that host from the same read, else None. No caller in this unit (a later CTA / "Sponsored" unit); never read by scoring (R20).
- Seed builders (pure): `source_to_entry(source, order, origin) -> dict`, `build_seed_rows(literal_rows, catalog_json_rows, now_iso) -> list[dict]`, `plan_seed(seed_rows, existing_hosts) -> (inserts, updates)`, `SEED_OWNED_COLUMNS = ("country", "currency_hint", "adapter", "search_template", "registry", "deny", "updated_at")`, `PLATFORM_FOR_MECHANISM = {"shopify": "shopify", "woo_store_json": "woocommerce", "salla_api": "salla", "magento_graphql": "magento", "occ_rest": "sap_hybris"}`.
- Test seams: `_monotonic` (prod `time.monotonic`), `_admin_client` (prod lazy `database_service.get_admin_supabase_client`), `_reset_for_tests()` (clears memo, refresh handle, warning window), `run_db` bound at module top (patchable as `merchant_registry.run_db`).

### 2.4 The decode (refresh -> routed list)

For each row: `host = deny_hosts.normalize_host(row["host"])`; skip unless `status == "live"` and `deny is False` and not `is_denied_host(host)` (the belt is flag-free, so a mis-seeded deny host never routes in any D03 state); for each entry of `row["registry"]` (a list; anything else skips the row): skip `origin == "catalog"` when `source_router._catalog_sources_enabled()` is False; build `source_router._source_from_entry(host, entry)` (new, beside `_row_to_source`, never raises, None for a malformed entry). Sort all `(order, origin, Source)` by `order`; then apply `_load_catalog_rows`' dedup verbatim: catalog entries whose domain equals or is a subdomain of a literal-origin domain, or repeats an earlier catalog domain, are dropped. No routed entry -> failure `empty`. `platform`, `adapter`, `robots`, `tos`, `partner` never reach a `Source` (live routing is unchanged by classification or by partner data in this unit).

### 2.5 `app/services/robots_registry.py` (new; stdlib + `robots_eval` + `deny_hosts` at top; `price_service`, `platform_router`, `url_validator`, `database_service`, `sitemap_discovery_service` lazily inside the cron-only functions, so importing it never imports `price_service` / `extraction_service` (R41))

- `robots_registry_cron_enabled()`, `max_hosts_per_run()`, `challenge_park_days()`; `QARENBOT_UA` = `sitemap_discovery_service._ROBOTS_UA` (one UA string in the repo, R37); `MIN_DELAY_SECONDS = 2.0`; `MAX_CRAWL_DELAY_SECONDS = 60.0`; `ROBOTS_TIMEOUT_SECONDS = 20` (the existing `_ROBOTS_TIMEOUT`); `REREAD_HOURS = 24`.
- `parse_crawl_delay(body, agent) -> Optional[float]`: the RFC 9309 grouping of `robots_eval.parse_groups` (consecutive `User-agent` lines share a record; same-token records merge; most specific named token, else `*`), reading `Crawl-delay:` values; a non-number, nan, inf or < 0 is ignored; the largest value of the selected groups; capped at `MAX_CRAWL_DELAY_SECONDS`.
- `decide_robots(status, headers, body, probe_url) -> RobotsVerdict(state, status, body_sha, crawl_delay, challenge_vendor)` (pure): `status is None` (timeout / network error / SSRF refusal) -> unreadable; 2xx -> if `price_service.classify_capture(body, None, status) == CAPTURE_WALLED` -> unreadable with a challenge vendor; else `allowed = robots_eval.can_fetch(body, NAMED_AGENT, probe_url) and robots_eval.can_fetch(body, "*", probe_url)` -> allow | disallow, `body_sha = sha256(body.encode("utf-8")).hexdigest()`, `crawl_delay = max` of the QarenBot and `*` parses; 404/410 -> allow, `body_sha = ""`, crawl_delay None; any other status -> unreadable, and a challenge when `status in _WALL_HTTP_STATUS` and the vendor is not `unknown`. `probe_url` = the host's first live entry `sample_url` (else first entry), else `https://<host>/`.
- `challenge_vendor(status, headers, body) -> str`: header `cf-mitigated` or `server: cloudflare` or body `cf_chl`/"just a moment" -> `cloudflare`; header `server: AkamaiGHost` or body "Reference #" with "access denied" -> `akamai`; `px-captcha`/`perimeterx` -> `perimeterx`; `_incapsula_`/`incap_ses` -> `imperva`; `distil` -> `distil`; else `unknown`. Case-insensitive.
- `robots_record(verdict, now) -> dict` (the 2.2 `robots` shape; `next_reread = now + 24 h`; ISO `...Z`).
- `next_row_update(row, verdict, now, gates=None) -> Optional[dict]` (pure transition table, 2.6).
- `async probe_host(row, fetch, sleep, now) -> dict` (robots read, then the promotion gates for a candidate, sequential, sleeping `max(crawl_delay or 0, MIN_DELAY_SECONDS)` before every request after the first); `fetch(url, headers, timeout) -> (status, headers, body)` raising on a network error (prod: `curl_cffi.requests.get(url, headers={"User-Agent": QARENBOT_UA, "Accept": "*/*"}, timeout=...)` in `asyncio.to_thread`, NO `impersonate`; every URL first passes `validate_external_url_async`, a refusal = `status None`).
- `async run_cron(client, fetch, sleep, now) -> dict` counts by state (the cron script's body; injectable for tests).
- Log lines: one INFO per probed host `"[ROBOTS_CRON] host=%s state=%s"` (exactly two args: the row host and the state constant); one summary INFO with ints; WARNING by exception type for a failed row write (`"[ROBOTS_CRON] write failed reason=%s"`); no URL, body, header value or exception text in any line.

### 2.6 The cron transition table (one update per host, `updated_at` = now)

| row before | verdict / gate | row after |
|---|---|---|
| `deny` true, or `is_denied_host`, or `blocked_reason in ("deny","owner")` | not probed | unchanged (no fetch) |
| `challenge.parked_until > now` | not probed | unchanged (no fetch) |
| `robots.next_reread > now` | not due | unchanged (no fetch) |
| live | allow | live; robots record |
| live | disallow / unreadable / challenge | blocked, `blocked_reason` robots_disallow / robots_unreadable / challenge, `health.pre_block_status = "live"`, challenge `{vendor, parked_until = now + park days}` for a challenge |
| blocked (cron-managed reason) | allow (and no challenge) | `health.pre_block_status` (live or candidate), `blocked_reason` null, challenge `{}` (Option A rejoin) |
| blocked (cron-managed reason) | still failing | blocked, reason updated, robots record |
| candidate | not allow | blocked as above with `pre_block_status = "candidate"` |
| candidate | allow; then `tos.verdict == "allowed"`; then PDP (`validate_scrape_url(probe_url)` True, robots allow, fetch 2xx, `classify_capture` not walled and not empty_shell); then platform (`detect_platform_verdict(pdp_html, probe_url, robots_body).commerce_platform != "unknown"`) | live, `platform` + `platform_confidence = "probe"`, `health.promotion` removed |
| candidate | allow but a gate fails | candidate; `health.promotion = {failing_gate, checked_at}` = the FIRST failing gate in the order robots, tos, pdp, platform; a walled PDP also parks the host as a challenge; no PDP fetch unless tos passed |

### 2.7 Seed (`scripts/seed_kb_merchants.py`)

`python -m scripts.seed_kb_merchants` = dry run (reads the two sources, prints `rows=410 live=317 candidate=92 blocked=1 collisions=1 entries=411` and the per-platform counts; writes nothing, needs no credential). `--apply` (owner run, service-role env from Railway): one read of existing hosts, then inserts of new hosts (every column, `status` / `blocked_reason` / `platform*` / jsonb columns as built) and updates of existing hosts limited to `SEED_OWNED_COLUMNS` (cron- and owner-managed columns are never overwritten), deny hosts always forced to `deny true, status blocked, blocked_reason deny`; batches of at most 100; idempotent. `--classify N` (dry by default, `--apply` writes `platform` + `platform_confidence` only): for at most N live blank-mechanism rows (default dry run N = 20), runs the robots-gated `robots_registry.probe_host` platform probe and prints counts by label. Row building: literal `Source`s -> `source_to_entry(s, index, "literal")`, kb status live (deny -> blocked), `country` / `adapter` null, `currency_hint = s.currency or null`; json rows -> `_row_to_source(dict(row, status="live"))` with `dataclasses.replace(..., status=row["status"])`, entry order `1000 + index`, origin catalog, kb status live iff json status is live else candidate, `country`, `currency_hint`, `adapter = genuine_method`; a json host equal to a literal host is not seeded (counted as a collision); `platform` = `PLATFORM_FOR_MECHANISM[mechanism]` with confidence `mechanism`, else `unknown` / null; `search_template` = the descriptor `url_template` or null; `partner`, `robots`, `politeness`, `health`, `challenge`, `tos` = `{}`. Never imported by app code; never run by the harness.

### 2.8 `source_router` changes

`registry_rows() -> List[Source]`: `return merchant_registry.registry_rows(SOURCE_REGISTRY)` (the module global read at call time, so tests that patch `source_router.SOURCE_REGISTRY` keep working). `_routable_registry()`: `reg = registry_rows()` replaces the two reads of `SOURCE_REGISTRY` (`:551`, `:552`); the D03 OFF branch returns `reg`. `_source_from_entry(host, entry)` beside `_row_to_source`. The three direct readers (`cache_service:526-529`, `magento_graphql_service:294-295`, `price_service:14881-14885`) read `registry_rows()` instead of `SOURCE_REGISTRY` (each a one-line change inside the existing lazy import); `structured_comparison_service._bh_locale_known_retail_domains` is left as is (memoised once per process; it already reads every json row regardless of status, so it is a superset; a DB-only new host stays outside it = the path rung fails closed for it, stated limit L6).

### 2.9 Flag-OFF identity (the unit's main invariant)

With `ENABLE_MERCHANT_REGISTRY_DB` unset or any falsy spelling: `source_router.registry_rows() is source_router.SOURCE_REGISTRY`; `_routable_registry()` returns exactly what it returns at base (the same object with D03 OFF, the D03-filtered memo with D03 ON); no `kb_merchants` read, no `run_db` call, no task created, no log line, no new import of `price_service` or `database_service` at module import; every consumer output equals its base literal. With `ENABLE_ROBOTS_REGISTRY_CRON` OFF the cron returns None after one INFO and makes no client call and no fetch. Pinned by P1-P6 with the FULL configuration present (both new flags' neighbours, every knob set to a synthetic value, a recording admin client, a recording `run_db`, a recording fetcher) so a not-gated mutant is killed.

### 2.10 Failure table (flag ON)

| case | registry served | log |
|---|---|---|
| before the first refresh lands (process start) | `SOURCE_REGISTRY` | none |
| `get_admin_supabase_client` raises (no credentials) | `SOURCE_REGISTRY` for the window | WARNING reason=ValueError, once per window |
| `.execute()` raises (table missing because 045 not applied, PostgREST error, network) | `SOURCE_REGISTRY` | WARNING reason=<type>, once per window |
| `result.data` not a list | `SOURCE_REGISTRY` | WARNING reason=not_a_list |
| 0 routed entries (table empty / seed not run / all blocked) | `SOURCE_REGISTRY` | WARNING reason=empty |
| `len(rows) >= 1000` | `SOURCE_REGISTRY` | WARNING reason=truncated |
| one malformed row / entry | the rest | counted in `skipped` of the INFO line |
| same snapshot on refresh | the same list object | none |
| call from a worker thread (no running loop), memo expired | the stale memo list, or `SOURCE_REGISTRY` | none; nothing scheduled |
| the event loop the refresh task was bound to closed | a new task on the current loop | none |

Cron: a failed robots fetch = unreadable (fail-closed, never `""`); a failed row write -> WARNING by type, next host continues; the cron never raises out of `main` (exit 0 with counts).

### 2.11 Test seams (production values in brackets)

`merchant_registry._monotonic` [`time.monotonic`], `merchant_registry._admin_client` [lazy `database_service.get_admin_supabase_client`], `merchant_registry.run_db` [`app.utils.db_offload.run_db`], `merchant_registry._reset_for_tests()`; `robots_registry.run_cron(client, fetch, sleep, now)` [`get_admin_supabase_client()`, the curl_cffi fetcher, `asyncio.sleep`, `datetime.now(timezone.utc)`]; `scripts/seed_kb_merchants.main(argv, client=None, probe=None)` [None -> `get_admin_supabase_client()` only under `--apply`]; `scripts/cron_robots_registry.main()` -> `run_cron(...)` with production seams.

## 3. Change list, in the order GREEN applies it

0. Byte copies (Python `shutil.copyfile`) of `source_router.py`, `price_service.py`, `cache_service.py`, `magento_graphql_service.py`, `CLAUDE.md` into the notes folder, with sha256.
1. `app/services/merchant_registry.py` (new, LF, ASCII): 2.1, 2.3, 2.4 builders.
2. `app/services/source_router.py`: `registry_rows()`, `_source_from_entry()`, the `_routable_registry` read (2.8). Import `merchant_registry` at module top (it imports no `source_router` at module level).
3. `app/services/price_service.py:14881-14885`, `app/services/cache_service.py:526-529`, `app/services/magento_graphql_service.py:294-295`: `SOURCE_REGISTRY` -> `registry_rows()` inside the existing lazy imports.
4. `app/services/robots_registry.py` (new): 2.5, 2.6.
5. `scripts/seed_kb_merchants.py` (new): 2.7.
6. `scripts/cron_robots_registry.py` (new; the `cron_index_sitemaps.py` header pattern, the Railway steps in its docstring, `run = main`).
7. `migrations/051_kb_merchants_registry.sql` + `migrations/rollback/051_kb_merchants_registry.sql` + `.qa-s80/APPLY_051_{1_PRECHECK,2_ONE_PASTE,3_POSTCHECK}.sql` ONLY if Q1 rules that 045 does not carry the `registry` column (sqlfluff clean under `.sqlfluff`; then the migration readers join the comm set).
8. `tests/test_s81_s15_registry_robots.py` (the RED file, already committed by RED; GREEN does not edit it unless a ruling says so).
9. CLAUDE.md: the S81-15 row after the S81-03 row (section 8) and the two names in the Environment Variables flag list sentence of that block.
No other file. Explicitly untouched: `structured_comparison_service.py`, `search_descriptor_service.py`, `shopify_pdp_service.py`, `sitemap_discovery_service.py`, `robots_eval.py`, `deny_hosts.py`, `platform_router.py`, every adapter, `url_extraction_service.py`, `app/main.py`, `data/*.json`, `app/legal/processors.json`, `tests/conftest.py`, `tests/_env_safety.py`, `tests/.pre_impl_failures.txt`, `requirements*`.

## 4. Existing pins

### 4.1 Pins that change deliberately

None. Every existing test stays green and unedited at head in both catalog states with the new flags OFF (the accessor returns the same object; the three direct readers resolve the same global). If GREEN finds a test that patches `source_router.SOURCE_REGISTRY` and asserts the IDENTITY of an object a direct reader iterated, that is a finding for a ruling, not an edit.

### 4.2 Pins that must stay green and unedited (green at base, 1.10)

The 26 files of 1.10, in particular: `test_s81_d03_deny_and_guards.py::test_p2_registry_never_mutated` (`SOURCE_REGISTRY is before_obj`, 44 literals, `[38]` fragrantica), `::test_r1i_single_deny_literal_list`; `test_bh_gcc_registry_loader.py` (catalog flag semantics); `test_m13_registry_longest_host.py`; `test_robots_unreadable_ruling.py` (fail-closed callers); `test_search_descriptor_d3.py` (robots_eval cases); `test_bh_registry_curl_timeout.py`, `test_tier15_hit_rate_metric.py`, `test_magento_gql_adapter.py` (the three direct readers); `test_legal_docs_u8.py::test_t7b_*`; `test_model_config.py`, `test_model_config_enforced.py`, `test_u3c_store_false_pin.py`; `test_cron_eval_nightly.py` (cron house contract); `test_hermeticity_pins.py`.

## 5. RED tests: `tests/test_s81_s15_registry_robots.py` (new; pure ASCII; hermetic)

House rules: R rows fail at base on an AssertionError ONLY (missing modules and names read through `_mod` / `_attr` helpers built on `importlib.util.find_spec` + `getattr`, asserted, never raised; the scripts read through `find_spec("scripts.seed_kb_merchants")`). P rows are green at base and run with the FULL configuration (autouse fixture: `ENABLE_ROBOTS_REGISTRY_CRON=true`, `MERCHANT_REGISTRY_MEMO_SECONDS=300`, `ROBOTS_CRON_MAX_HOSTS=3`, `ROBOTS_CHALLENGE_PARK_DAYS=2`, `ENABLE_DATA_GUARDS_V2` and `ENABLE_LONGEST_HOST_MATCH` parametrised both ways, synthetic `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` set after an `app.main` import; `database_service.get_admin_supabase_client` patched with a recorder that records and raises; `app.utils.db_offload.run_db` patched with a recorder; `merchant_registry._reset_for_tests()` when present). The fake Supabase client is an in-memory object recording `table(name)`, `select(cols)`, `insert(rows)`, `update(dict)`, `eq(col, val)`, `execute()`; seeded rows come from the real `build_seed_rows` over the real `_LITERAL_ROWS` and `data/bh_gcc_sources.json` (zero network). Synthetic hosts end in `.test`. Every fetch is an injected recorder; the netguard stays on. Flag-OFF base literals (domain lists, tiers) are recorded as literals in the file at RED time, catalog OFF (the CI state) and catalog ON (via `_load_catalog_rows()` under a monkeypatched env).

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_db_flag_reader` | `merchant_registry_db_enabled()` True for `TRUE`, ` on `, `1`, `Yes`; False for unset, ``, `false`, `0`, `off`, `no`, `garbage`, `FALSE ` | RED (module absent) | 2.1 |
| R2 | `test_r2_memo_seconds_knob` | unset/``/`abc`/`nan`/`inf`/`-5`/`0` -> 600.0; `60` -> 300.0; `5000` -> 900.0; ` 450 ` -> 450.0 | RED | 2.1 |
| R3 | `test_r3_cron_flag_and_knobs` | cron flag table as R1; `max_hosts_per_run` (`0`->500, `9999`->5000, `abc`->500, `7`->7); `challenge_park_days` (`0`->7, `99`->30) | RED | 2.1 |
| P1 | `test_p1_flag_off_consumers_identical[d03,lhm,falsy]` | flag OFF (each FALSY spelling): `get_sources_for_category("fragrances")` domains, `score_source`, `registry_tier("noon.com") == "gcc"`, `match_registry_apex("uae.sharafdg.com")`, `source_usage`, `is_render_only_domain("noon.com")`, every mechanism selector, `build_site_discovery_query(...)`, `descriptor_for_host("bh.jashanmal.com")`, `price_service._curl_timeout_for_url`, `cache_service._registry_domains()`, `magento_graphql_service._expected_currency_for("en-kwt.ajmal.com")` equal the recorded base literals; the admin-client and `run_db` recorders are EMPTY | PIN | 2.9 |
| P2 | `test_p2_flag_off_object_identity` | flag OFF, D03 OFF: `_routable_registry() is SOURCE_REGISTRY` before and after 50 consumer calls; `SOURCE_REGISTRY` and `_LITERAL_ROWS` objects and members unchanged; `len(_LITERAL_ROWS) == 44` | PIN | 2.9 |
| P3 | `test_p3_flag_off_no_task` (async) | inside a running loop, flag OFF, 20 consumer calls: `len(asyncio.all_tasks())` unchanged; caplog has no `MERCHANT_REGISTRY` record | PIN | 2.9 |
| P4 | `test_p4_bh_locale_set_untouched` | AST: `structured_comparison_service._bh_locale_known_retail_domains` still names `SOURCE_REGISTRY` and `_CATALOG_DATA_PATH` | PIN | 2.8 |
| P5 | `test_p5_live_fetchers_read_no_robots_registry` | no module under `app/` other than `robots_registry.py` / `merchant_registry.py` contains the token `robots_registry`; `price_service.py`, `url_extraction_service.py`, `shopify_pdp_service.py`, the adapters contain no `kb_merchants` | PIN | item 4 of the brief |
| P6 | `test_p6_scoring_never_reads_partner` | `scoring_service.py`, `response_builder.py`, `structured_comparison_service.py` import no `merchant_registry` and contain no `"partner"` string literal | PIN | 2.3 |
| R4 | `test_r4_accessor_identity_off` | `source_router.registry_rows` exists and, flag OFF, `registry_rows() is SOURCE_REGISTRY` | RED (attr absent) | 2.8 |
| R5 | `test_r5_on_before_refresh_serves_code_registry` | flag ON, no loop running, empty memo: `registry_rows() is SOURCE_REGISTRY`; admin recorder empty | RED | 2.3 |
| R6 | `test_r6_single_flight_refresh` (async) | flag ON, empty memo, fake client: the first `get_sources_for_category` call returns the base literal list and creates exactly ONE task; nine more calls before it finishes create none; after `await` of the task the fake client saw ONE `table("kb_merchants")`, ONE `select(READ_COLUMNS)`, ONE `execute()`, all through the `run_db` recorder | RED | 2.3 |
| R7 | `test_r7_on_routes_db_rows` (async) | after a refresh over seeded rows plus a synthetic live `newshop.test` (bahrain, fragrances): `get_sources_for_category("fragrances")` contains `newshop.test`; `registry_tier("newshop.test") == "bahrain"`; holds with D03 OFF and ON | RED | 2.4, 2.8 |
| R8 | `test_r8_record_equality[catalog_off,catalog_on]` | the decoded list == `[s for s in _LITERAL_ROWS + (catalog ? _load_catalog_rows() : []) if not is_denied_host(s.domain)]` (43 / 318 entries) element by element | RED | 2.4, 2.7 |
| R9 | `test_r9_entry_round_trip` | for all 319 catalog-ON Sources: `_source_from_entry(s.domain, source_to_entry(s, i, origin)) == s` | RED | 2.3, 2.8 |
| R10 | `test_r10_noon_two_entries` | the seeded `noon.com` row has 2 entries, orders 23 and 24; after refresh `registry_tier("noon.com") == "gcc"` and `get_noon_sources_for_category("fragrances")` holds the bahrain entry | RED | 2.2, 2.4 |
| R11 | `test_r11_blocked_candidate_deny_never_routed` | rows: blocked (robots_unreadable), live with `deny` true, live `fragrantica.com` with deny false (mis-seed), candidate: none appears in `registry_rows()`, `score_source`, `registry_tier` | RED | 2.4 |
| R12 | `test_r12_catalog_flag_at_refresh` | catalog OFF at refresh -> only literal-origin entries; ON -> catalog entries too | RED | 2.4 |
| R13 | `test_r13_literal_dedup` | a catalog entry on `bh.amazon.ae.test`-style subdomain of a literal-origin synthetic host and an exact repeat are dropped, mirroring `_load_catalog_rows` | RED | 2.4 |
| R14 | `test_r14_order_independent_of_row_order` | shuffled DB rows decode to the identical list | RED | 2.4 |
| R15 | `test_r15_memo_window` (async) | knob `60` -> window 300: at t0+299 no new task; at t0+300 one task; knob `600` honoured | RED | 2.3 |
| R16 | `test_r16_snapshot_keeps_identity` (async) | same rows twice -> `registry_rows()` returns the SAME object; a changed `updated_at` -> a new object; with D03 ON `_routable_registry()` returns the same filtered object across the same-snapshot refresh | RED | 2.3 |
| R17 | `test_r17_failures_fall_back[no_client,execute_raises,not_a_list,empty,truncated,all_malformed]` | `registry_rows() is SOURCE_REGISTRY` after the refresh; exactly ONE WARNING whose args are (`ValueError` / the synthetic exception's type name / `not_a_list` / `empty` / `truncated` / `empty`); a second refresh in the same window adds no WARNING; after the window one more; no record carries a host or a message | RED | 2.10 |
| R18 | `test_r18_one_bad_row_skipped` | a row whose `registry` is a string and an entry with `weight: "x"` are skipped; the rest routes; INFO `skipped` count 2 | RED | 2.4 |
| R19 | `test_r19_worker_thread_call` | an expired memo read from a `threading.Thread`: returns the stale list, raises nothing, creates no task | RED | 2.3 |
| R20 | `test_r20_partner_for_host` | flag OFF -> None and no read; ON after refresh -> the stored dict; no `Source` field holds partner data | RED | 2.3 |
| R21 | `test_r21_direct_readers_use_accessor` | patch `source_router.registry_rows` with a recorder: each of the three direct readers calls it once; flag ON with `newshop.test` live bahrain: `_curl_timeout_for_url("https://newshop.test/p/1") == BH_REGISTRY_CURL_TIMEOUT` | RED | 2.8 |
| R22 | `test_r22_seed_rows_counts` | `build_seed_rows(_LITERAL_ROWS, json, now)`: 410 rows; status live 317 / candidate 92 / blocked 1; `fragrantica.com` deny true, blocked_reason `deny`; `footlocker.com.bh` carries the literal entry only; entries 411; every row's keys == the 2.2 column set + `registry`; no key `id`, `email`, `user`, `device` | RED | 2.7 |
| R23 | `test_r23_seed_platform_and_fields` | live mechanism rows -> mapped platform + `mechanism`; 199 live blank rows -> `unknown` + null; catalog rows carry json `country`, `currency_hint`, `adapter = genuine_method`; literal rows null country / adapter | RED | 2.7 |
| R24 | `test_r24_plan_seed_idempotent_and_non_clobbering` | `plan_seed(rows, existing={"bh.jashanmal.com", "fragrantica.com"})`: updates touch only `SEED_OWNED_COLUMNS` (plus the forced deny triple for fragrantica); inserts carry every column; planning twice is equal | RED | 2.7 |
| R25 | `test_r25_seed_script_dry_run_writes_nothing` | `seed_kb_merchants.main([], client=fake)` prints `rows=410 live=317 candidate=92 blocked=1 collisions=1 entries=411`; the fake saw no insert / update / upsert; `--apply` performs inserts then updates in batches of at most 100 | RED (script absent) | 2.7 |
| R26 | `test_r26_seed_classify_dry_run` | `--classify 20` calls the injected probe for exactly 20 live blank-mechanism rows, writes nothing, prints per-label counts; a robots-disallowed row is not page-fetched | RED | 2.7 |
| R27 | `test_r27_decide_robots_table` | (200, allow) allow; (200, `User-agent: *` `Disallow: /`) disallow; (200, QarenBot `Disallow: /` + `*` allow) disallow; (200, `*` `Disallow: /products/` + QarenBot `Allow: /`, probe `/products/x`) disallow; (404) allow body_sha ``; (410) allow; (403) unreadable; (500) unreadable; (None) unreadable; (301) unreadable; (200, a "Just a moment" page) unreadable with vendor cloudflare; (200, ``) allow | RED | 2.5 |
| R28 | `test_r28_crawl_delay` | `*` 5 -> 5.0; QarenBot 10 + `*` 3 -> 10.0; `abc` -> None; `-1` -> None; absent -> None; `999` -> 60.0; a second `*` group's delay merges | RED | 2.5 |
| R29 | `test_r29_body_sha_and_record` | sha256 hex of the UTF-8 body for 2xx; `` for 404/410; None for unreadable; `robots_record` keys exactly `state, status, body_sha, fetched_at, next_reread, crawl_delay`, `next_reread - fetched_at == 24 h` | RED | 2.5 |
| R30 | `test_r30_challenge_vendor` | the vendor table of 2.5, case-insensitive, `unknown` otherwise | RED | 2.5 |
| R31 | `test_r31_transitions` | every row of the 2.6 table, including Option A rejoin to `pre_block_status`, sticky `deny` / `owner` (no fetch recorded), parked and not-due hosts skipped | RED | 2.6 |
| R32 | `test_r32_promotion_gates` | candidate: all gates pass -> live + platform `probe`; tos missing -> candidate, failing_gate `tos`, and the fetch recorder shows ONLY the robots URL; walled PDP -> failing_gate `pdp` + parked; platform unknown -> `platform`; robots disallow -> blocked `robots_disallow` | RED | 2.6 |
| R33 | `test_r33_cron_flag_off` | `cron_robots_registry.main()` with the full configuration and flag OFF: returns None, one INFO, the fake client and fetch recorders empty | RED (script absent) | 2.9 |
| R34 | `test_r34_cron_sequential_polite_named` | flag ON, 3 hosts: max in-flight fetches == 1; the sleep recorder shows `max(crawl_delay, 2.0)` before every request after the first; every request header `User-Agent == sitemap_discovery_service._ROBOTS_UA`; no `impersonate` keyword reaches the fetcher; one update per host; one INFO per host with args exactly `(host, state)` | RED | 2.5 |
| R35 | `test_r35_ssrf_and_deny_not_fetched` | a host the SSRF validator refuses -> unreadable with no fetch; a `deny` row and an `is_denied_host` row with status live -> no fetch, no update | RED | 2.5, 2.6 |
| R36 | `test_r36_run_bound_and_due` | `ROBOTS_CRON_MAX_HOSTS=3` bounds the probed hosts; a host with `next_reread` in the future is not probed | RED | 2.6 |
| R37 | `test_r37_robots_registry_import_is_light` | a subprocess (`python -I`, cwd = repo) importing `app.services.robots_registry` and `app.services.merchant_registry` leaves `app.services.price_service`, `app.services.extraction_service` and `app.services.database_service` out of `sys.modules` | RED | 2.3, 2.5 |
| R38 | `test_r38_no_impersonation_and_log_hygiene` | AST of `robots_registry.py` and `merchant_registry.py`: no `impersonate` keyword; every logger call's format args are names bound to ints / constants / `type(...).__name__` / the `host` and `state` pair of the per-host INFO; ERROR level only inside `except` arms | RED | 2.5 |

Counts: 38 R rows (R1-R38) and 6 PIN rows (P1-P6), some parametrised (P1 over 2 x 2 x 7, R8 over 2, R17 over 6). The RED agent proves satisfiability with an in-place prototype on byte copies (restored and sha-checked), then the file is frozen.

## 6. Mutation table (each mutant applied to a byte copy, run through the bounded runner with `-k <killer>`, bound 600, restored and sha-checked; KILLED = an assertion failure)

| # | mutant | killer |
|---|---|---|
| M1 | `merchant_registry.registry_rows` skips the flag read (always the DB path) | P1, P3 |
| M2 | flag reader without `.strip().lower()` | R1 |
| M3 | knob without the clamp | R2, R15 |
| M4 | knob accepts nan / inf | R2 |
| M5 | decode admits `candidate` | R11 |
| M6 | decode ignores `deny` | R11 |
| M7 | decode drops the `is_denied_host` belt | R11 |
| M8 | no sort by `order` | R14, R8 |
| M9 | catalog flag ignored at refresh | R12, R8 |
| M10 | rebuild on an equal snapshot | R16 |
| M11 | empty result stored as an empty list (no fallback) | R17[empty] |
| M12 | WARNING on every refresh, not once per window | R17 |
| M13 | refresh awaited inline in `registry_rows` (no task) | R6, R19 |
| M14 | single flight removed | R6 |
| M15 | `_routable_registry` D03-OFF branch returns `SOURCE_REGISTRY` instead of `reg` | R7 |
| M16 | `_curl_timeout_for_url` reverted to `SOURCE_REGISTRY` | R21 |
| M17 | `decide_robots` treats 403 as allow | R27 |
| M18 | only the QarenBot group consulted (not the most restrictive) | R27 |
| M19 | 404 treated as unreadable | R27 |
| M20 | a 200 challenge page treated as readable | R27 |
| M21 | crawl delay = min of the groups | R28 |
| M22 | promotion without the ToS gate | R32 |
| M23 | PDP fetched before the ToS gate | R32 |
| M24 | cron not gated on its flag | R33 |
| M25 | `asyncio.gather` over hosts | R34 |
| M26 | 2 s floor removed | R34 |
| M27 | cron changes a `deny` / `owner` row | R31 |
| M28 | Option A rejoin always to `live` | R31 |
| M29 | seed writes fragrantica as live | R22 |
| M30 | `plan_seed` updates `status` on existing hosts | R24 |
| M31 | `impersonate="chrome"` added to the prod fetcher | R38 |
| M32 | the per-host INFO logs the URL | R34, R38 |

## 7. Comm set and gates for GREEN (cheapest first; every pytest through the bounded runner, one process at a time)

1. `py_compile` and `ruff check --select E9,F63,F7,F82 --no-cache` on the 4 touched app files, the 2 new app files, the 2 scripts and the test file.
2. Byte checks: new files LF and pure ASCII (bytes > 127 = 0); `git diff --stat` shows no whole-file diff on a CRLF file.
3. The unit file (bound 600), catalog flag unset, then with `ENABLE_BH_GCC_CATALOG_SOURCES=true` exported for that runner call only.
4. The 26 files of 1.10 at head (two calls, bound 1200), then the CI-order set = the unit file + those files (bound 1200).
5. Comm set (zero-regression gate), measured at base: 366 files (`comm_set.txt` in the notes folder) = module grep `source_router|robots_eval|price_service|cache_service|magento_graphql_service|search_descriptor_service|shopify_pdp_service|sitemap_discovery_service|platform_router|deny_hosts|db_offload|database_service` over `tests/*.py` (297) UNION the symbol grep (`SOURCE_REGISTRY`, `_LITERAL_ROWS`, `_routable_registry`, `_ROUTABLE_MEMO`, `_registry_row_for_host`, `match_registry_apex`, `registry_tier`, `get_sources_for_category`, `score_source`, `source_usage`, `is_render_only_domain`, `_curl_timeout_for_url`, `_registry_domains`, `_expected_currency_for`, `_catalog_sources_enabled`, `_load_catalog_rows`, `can_fetch`, `NAMED_AGENT`, `_ROBOTS_UA`, `detect_platform`, `classify_capture`, `validate_scrape_url`, `run_db`; 67) UNION files naming an edited module by path (38) UNION the walkers over `app/` (`rglob` / `glob` / `inspect.getsource` / `ast.parse` / `read_text` with an app path; 146, an over-inclusive upper bound) UNION the listed source-scanning pins (`test_model_config.py`, `test_model_config_enforced.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py`, `test_start_command*.py`) UNION the CLAUDE.md readers (`test_ci_gates.py`, `test_behavior_dimension_translation.py`), MINUS the `test_precommit_hook*.py` files; plus the new unit file; plus, only if migration 051 lands, the migration readers (`test_migration_index_predicate_immutability.py`, `test_migration_04*.py`, `test_retro_r_mig*`). No SmartCompareApp-scanning test is required (no client-visible contract change). Chunks of at most 25 files (15 chunks), bound 1200, at base and at head, `comm -13` of the sorted FAILED node-id sets EMPTY; a branch-only-new failure is re-run once against base. The two known tiktoken ERROR nodes of `tests/test_prompt_truth.py` are recorded identically on both sides if they appear.
6. ON measurement (not a gate): the router chunks at head with `ENABLE_MERCHANT_REGISTRY_DB=true` exported per runner call (no client -> fallback): every node must stay green (the fallback IS `SOURCE_REGISTRY`); list any node that turns red.
7. The mutation table of section 6.
8. The pre-commit hook test files are NOT run (no `.githooks` change).

## 8. CLAUDE.md row and owner steps

### 8.1 The flag row (GREEN writes it after the S81-03 row; wording may be tightened, content may not)

**SESSION 81 flags (S81-15 REGISTRY-ROBOTS-DENY, 2026-10-23; both default OFF, read PER CALL; new names, so unset in production by construction (Railway not read); PLAN_S81 unit S81-15 (M4, lane B), owner decisions 7 and 11; spec `.qa-s80/S81-15_UNIT_SPEC.md` of the unit worktree):**
- `ENABLE_MERCHANT_REGISTRY_DB` + knob `MERCHANT_REGISTRY_MEMO_SECONDS` (S81-15, `app/services/merchant_registry.py::merchant_registry_db_enabled`; every `source_router` consumer and the three direct readers (`cache_service._registry_domains`, `magento_graphql_service._expected_currency_for`, `price_service._curl_timeout_for_url`) read `source_router.registry_rows()`). **Effect ON:** the routed registry is the `kb_merchants` table (migration 045 by S81-14 with the `registry` jsonb entry array), memoised per process (default 600 s, clamped 300..900), refreshed by ONE read through `run_db` in a background task (stale-while-revalidate; never on the caller), stable while the snapshot (max `updated_at`, row count) is unchanged; only `status = live`, `deny = false` rows on a host `deny_hosts` does not match are routed (blocked and candidate rows never are); catalog-origin entries count only while `ENABLE_BH_GCC_CATALOG_SOURCES` is on, so a seeded table reproduces today's registry record for record in both catalog states, minus fragrantica. Any failure (no credentials, 045 not applied, error, not a list, empty, 1,000+ rows) serves the in-code `SOURCE_REGISTRY` with ONE `[MERCHANT_REGISTRY] read failed reason=<type|constant>` WARNING per window. **Flag OFF:** `registry_rows() is SOURCE_REGISTRY`, no read, no task, no line (pinned by `tests/test_s81_s15_registry_robots.py` P1-P6). **Preconditions:** 045 applied; the seed run with `--apply` and its counts in the ledger; `ENABLE_SYNC_DB_OFFLOAD` ON first (else the one read per window blocks the loop); the cron has covered every live host once. **Stated limits:** the first compares of each process use the code registry until the first refresh lands; a change reaches a process within one window; `partner` is stored and read only by `partner_for_host` (no caller; never scoring); `_bh_locale_known_retail_domains` keeps the code set (a DB-only host gets no BH-locale path credit); classification never rewrites routing fields.
- `ENABLE_ROBOTS_REGISTRY_CRON` + knobs `ROBOTS_CRON_MAX_HOSTS` (500), `ROBOTS_CHALLENGE_PARK_DAYS` (7) (S81-15, `app/services/robots_registry.py`, entry `scripts/cron_robots_registry.py`, a Railway cron on the worker service, owner-scheduled daily). **Effect ON:** every due live or candidate host's `/robots.txt` is read once a day as QarenBot (the `sitemap_discovery_service._ROBOTS_UA` string, no impersonation, SSRF-checked, concurrency 1, delay max(Crawl-delay capped 60 s, 2 s)); fail-closed: 404/410 allow, any other non-2xx, a timeout, an error or a challenge page = unreadable -> blocked `robots_unreadable`; the most restrictive of the QarenBot and `*` groups on the host's sample PDP path decides (`robots_disallow`); a challenge parks the host (`challenge {vendor, parked_until}`, blocked `challenge`); `robots {state, status, body_sha, fetched_at, next_reread, crawl_delay}` recorded; a cron-blocked host rejoins its prior status on a later allow (ruling Option A); `deny` / `owner` blocks are sticky; a candidate becomes live only when robots allow AND `tos.verdict = allowed` (no PDP fetch before it) AND one validated PDP (`validate_scrape_url`, 2xx, not walled) AND a known platform (`detect_platform_verdict`), else it stays candidate with `health.promotion.failing_gate`. One INFO per host (host + state only). **Flag OFF:** the cron returns after one INFO, no read, no fetch. **The live path is untouched:** no fetcher reads robots in this unit (D14 LIVE-ROBOTS owns the persisted-verdict lookup); with both flags ON the only live effect is that a host the cron blocks leaves the routed registry at the next memo refresh. **Stated limits:** the seed (`scripts/seed_kb_merchants.py`, dry run by default) is the owner's run; the first pass needs one daily run per 500 hosts; a host with robots allow but a challenge is blocked, not evaded; the 61 dead json rows seed as candidate and will mostly block as `robots_unreadable` on the first pass; live adapters still impersonate Chrome until the owner's UA ruling after M6; crawl-delay is parsed in-house (Protego is not a dependency).

### 8.2 Owner steps (names only, in this order)

1. Publish the QarenBot contact page at the URL the UA names (`https://getmyez.com/bot`) before the first cron run.
2. Apply migration 045 (S81-14) with its PRECHECK / POSTCHECK (and 051 if Q1 rules it).
3. Run `python -m scripts.seed_kb_merchants` (dry run) and record its count line in the ledger; then `--apply` from the worker service environment (service-role variable NAMES `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`; never pasted); record the applied counts.
4. Optionally `--classify 20` (dry run) and record the per-platform counts; `--classify N --apply` only after reading them.
5. Create the Railway cron on the worker service: command `python -m scripts.cron_robots_registry`, schedule daily (e.g. `30 2 * * *`), variable `ENABLE_ROBOTS_REGISTRY_CRON=true` on that service only.
6. Review ToS for each candidate the cron reports with `failing_gate = tos` (write `tos {reviewed_at, verdict, terms_url}`, names only in the ledger; the admin surface is D16's).
7. After one full pass covers every live host (ledger line with the state counts) and `ENABLE_SYNC_DB_OFFLOAD` is ON: set `ENABLE_MERCHANT_REGISTRY_DB=true` on `web` in its own canary window (after App Review approval); watch the `[MERCHANT_REGISTRY]` lines and the per-category source counts; rollback = unset the variable (per call, immediate).

## 9. Stated limits

- L1 Not applied until the owner runs 045 (+ 051) and the seed; flag ON before that is the code registry plus one WARNING per window.
- L2 The first compares after a process start (and the first after each expiry on a cold loop) use the code registry or the stale memo; a table change reaches a process within one window (300-900 s).
- L3 With `ENABLE_SYNC_DB_OFFLOAD` OFF the one read per window runs inline on the loop (about one Supabase RTT every 10 minutes per process).
- L4 A PostgREST page above 1,000 rows (registry growth) is refused as `truncated` and serves the code registry; paging is a follow-up.
- L5 Platform classification and promotion write `platform`, `platform_confidence`, `status`; they never rewrite an entry's `mechanism` or flags, so a classified blank row still routes as before (adapter assignment is a later unit).
- L6 `_bh_locale_known_retail_domains` keeps the code set (memoised once per process); a DB-only host gets no BH-locale path credit (fail-closed).
- L7 The PDP gate checks reachability, robots and the wall signature, not a price (the existing liveness script `verify_bh_gcc_sources.py` stays the price proof; Q3).
- L8 Robots are judged on the host's sample PDP path; a disallowed PDP path blocks the host, a path-level allow elsewhere is D14's per-URL lookup.
- L9 The cron runs from Railway's datacenter egress; under the ruling's Option C rider a datacenter wall on robots is still unreadable (blocked), never fail-open.
- L10 Crawl-delay parsing is in-house; values above 60 s are capped (a host asking for more is probed at most daily anyway).
- L11 Dead json rows seed as candidate (the brief); the first pass mostly blocks them as `robots_unreadable` (Q2).
- L12 Live adapters keep `impersonate="chrome"` (unchanged); the UA ruling after M6 is the owner's.
- L13 Partner / CTA fields are stored, exposed only by `partner_for_host`, and never read by scoring or rendering in this unit.

## 10. Out of scope

D14 live per-fetch robots lookups and attempt hooks; D16 admin view and operator ingestion; adapter assignment for classified rows; the deletion of the fragrantica literal row (the later R-A1 PR, F1); KB writers (S81-16 / S81-17); Common Crawl CDX; web_search discovery (S81-21); the UCP MCP probe (R13); any client change.

## 11. Open questions for the orchestrator

- Q1 (blocking for GREEN): does S81-14's 045 carry `kb_merchants.registry jsonb` (the entry array of 2.2) and leave `updated_at` writer-maintained? If not, this unit adds migration 051 (change list item 7). Measured reason: `host` PK cannot hold the two `noon.com` literal rows, and the 14 S81-14 columns cannot reproduce 15 of the 19 `Source` fields.
- Q2: seed the 61 dead json rows as `candidate` (the brief, as specified) or as `blocked` with a new reason `dead`?
- Q3: should "one validated PDP" also require a price from `extract_price_from_html` (heavier, imports the extractor into the cron), or is reachability + robots + wall signature enough (as specified)?
- Q4: add Protego to `requirements-dev.in` as a crawl-delay ORACLE for a parity row (package command, 14-day rule), or keep the in-house parser only (as specified)?
- Q5: confirm the three direct readers move to the accessor (as specified, per the brief) while `_bh_locale_known_retail_domains` stays on the code set.
- Q6: the 045 type of `platform_confidence` (text enum assumed: `mechanism` | `probe` | `url`).
- Q7: confirm a candidate whose platform reads `unknown` (a JSON-LD host) stays candidate (failing_gate `platform`) until the owner sets the platform, rather than promoting on the JSON-LD evidence.
- Q8: confirm that with both flags ON a cron block removing a live host from routing is the intended live effect of this unit (the brief's "never returned as live"), distinct from D14's per-URL lookup.

Not done in this spec: no RED file, no prototype, no mutation run (sections 5 and 6 are the plan for the RED and GREEN agents); the comm set was listed at base, not run; Protego was not measured (not installed); the S81-14 spec was not available to read.
