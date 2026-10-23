# S81-14 KB-SCHEMA -- unit spec (lane B; migrations 045 + 047 + a pure leaf; NO runtime flag)

- Unit: S81-14 KB-SCHEMA (PLAN_S81 M4; Fable ruling F4: 045 KB core, 047 the 012 REVOKE; 046/048/049 reserved for other units, 050 taken by S81-03).
- Flag: none. The unit adds no call site: two migration files the owner applies by hand, one leaf module with zero importers, one test file, one CLAUDE.md edit. Inert until the owner applies 045/047 AND a later flagged unit (S81-15 / S81-16 / S81-17 / S81-18) writes or reads.
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-s14 (detached). Branch for GREEN: `feature/s81-kb-schema`.
- Base sha: dfc6502f791cdccbf0a620041f66888a734015d3 (origin/main = 84c861f6 + #369 S81-03). `git status --short` EMPTY before and after every probe of this spec (measured 15:0x and at the end).
- Evidence: measurement notes and the satisfiability prototype in `<scratchpad>/S81-14/` (proto/migrations/045_kb_core.sql, proto/migrations/047_012_revoke.sql, proto/probe.py, probe.out, lint2.json, base_migr.log, base_scan.log). Appendix A of this spec carries the two prototype migrations verbatim.
- Inputs read in full: s81-common.txt, PLAN_S81.md (Standing constraints, VERIFY "Knowledge base, registry, crawler", F1-F4, M4 S81-14 text, owner decisions 1-12), specs/S81_14_BRIEF.md, RULINGS_R0.md, DEFECT_LEDGER.md, runs/research A2 / A3 / R3 / R13 / R15.
- Sister units and contracts: S81-15 REGISTRY (first writer of kb_merchants; reads the partner jsonb for the CTA label only), S81-16 KB-SEED (writes kb_products/variants/offers/specs/images through the builders), S81-17 KB-INGEST (writes cards + kb_gaps through the builders, one RPC per compare), S81-18 KB-FIRST-SERVE (reads `kb_product_card`), S81-19 GAP-QUEUE (kb_gaps state machine), D17 COVERAGE (kb_coverage_daily), S81-22 COMPARE-RUNS (kb_feedback deletion by device_key; compare_request_id join), S81-05 REQUEST-CONTEXT (`device_key()` = HMAC-SHA256 64 lowercase hex, RULINGS_S81_05 R-S05-1). D03 owns `deny_hosts` (reused, never duplicated). No hunk shared with in-flight ST1 / S81-05 except the CLAUDE.md session-81 flag-row anchor (`CLAUDE.md:485-488` at base) and the migrations apply-record line (`CLAUDE.md:92`): known rebases, union in session order.
- Personal-data rule: no real name, email, phone, device id, account id or address anywhere; GTINs, device keys, uuids and every digit run of 8 or more are BUILT AT RUN TIME (the added-line sweep flags 8-digit runs), in tests and in the APPLY_*.sql check files alike.

## 0. What the unit does

Lands the owned knowledge base's schema and identity helpers, inert:
1. `migrations/045_kb_core.sql` (+ rollback): ten service-role tables (kb_merchants, kb_products, kb_variants, kb_offers, kb_images, kb_specs, kb_reviews, kb_gaps, kb_feedback, kb_coverage_daily), the view `kb_offers_latest` (latest offer per SKU x merchant, security_invoker), and three SECURITY INVOKER functions: `kb_gtin_check_digit_ok(text)` (the gtin CHECK), `kb_prune_offers(integer, integer)` (age- and count-bounded prune), `kb_product_card(text) -> jsonb` (the one-call card read). The key split (R15): specs/notes/reviews per JUICE = brand + identity + concentration; price, availability and image per SKU = juice + ml (+ merchant on offers).
2. `migrations/047_012_revoke.sql` (+ rollback): drops the eight 012 policies on product_specs / product_prices / product_reviews BY NAME and revokes every table privilege from PUBLIC, anon, authenticated, re-granting service_role explicitly.
3. `app/services/kb_service.py`: a pure leaf (no I/O, no flag, no clock): `kb_product_id`, `kb_variant_key`, `kb_source_allowed`, `canonical_offer_url`, `gtin_check_digit_ok`, and one row builder per table whose keys are derived-equal to the migration's columns. Zero importers in app/ and scripts/.
4. GREEN also writes the owner's six one-paste files under `.qa-s80/` (APPLY_045_{1_PRECHECK,2_ONE_PASTE,3_POSTCHECK}.sql, APPLY_047_{...}.sql); the orchestrator copies them to the state folder.
5. CLAUDE.md: the apply-record line gains 045 / 047 as WRITTEN, NOT APPLIED, and a SESSION 81 S81-14 row.

No runtime behaviour changes in any state: no app module imports kb_service, no route or service reads a kb_* table, no flag is read.

## 1. Base state MEASURED (dfc6502f)

### 1.1 Migrations
| fact | file:line |
|---|---|
| 012 creates product_specs / product_prices / product_reviews with RLS on and EIGHT policies with no TO clause (apply to PUBLIC): `specs_select` FOR SELECT USING (true), `specs_insert` FOR INSERT WITH CHECK (true), `specs_update` FOR UPDATE USING (true), `prices_select`, `prices_insert`, `reviews_select`, `reviews_insert`, `reviews_update` | migrations/012_product_data_tables.sql:18-21, :40-42, :57-60 |
| 012 header claims product_key = md5(brand|name|variant)[:12]; A2 measured it is the prefixed L1 key (three unjoinable keys) | 012:2; A2 finding 4 |
| No later migration names a policy or grant on the three tables; 033 / 034 only ADD COLUMN title / in_stock to product_prices | grep: 033:30, 034:37 |
| 044 pattern: BEGIN; CREATE TABLE IF NOT EXISTS; ENABLE RLS; `REVOKE ALL ON TABLE ... FROM PUBLIC, anon, authenticated`; one GRANT to service_role; COMMIT | 044:31-52 |
| 050 (newest precedent): REVOKE ALL ... FROM PUBLIC, anon, authenticated, service_role (the default-privilege grants on a stock project; service_role bypasses RLS, not grants) then GRANT SELECT, INSERT only | 050:20-26, :64-68 |
| 037 both-readings rule (REVOKE names anon + authenticated; explicit GRANT to service_role) | 037:48-80 |
| 043 cascade + fence: delete_user_cascade body; the fence vocabulary USER_REF_ID_RX / PERSONAL_RX (PERSONAL_RX matches `gender`, `fingerprint`, `device_id`, `email`, `address`, `(^|_)ip($|_)`, `session_id`, ...) | 043:166-234; tests/test_migration_043_delete_user_cascade.py:359-367 |
| Migration numbers on disk: ... 042, 043, 044, 050; 045-049 free, 039 reserved | `ls migrations` |
| sqlfluff 4.3.0 (venv) with repo `.sqlfluff` (dialect postgres, max_line_length 180, CP01 upper enforced, 11 rules excluded) | .sqlfluff:56-76 |
| MEASURED: sqlfluff SKIPS a file over 20,000 bytes (`large_file_skip_byte_limit` default) with a WARNING on stderr and exit 0, so the hook (.githooks/pre-commit:613-615) and `test_sqlfluff_lints_the_migration_corpus_clean` would pass an unlinted 045. The first prototype (20,556 LF / 20,986 CRLF bytes) was skipped; the trimmed prototype (19,149 LF / 19,554 CRLF) lints with 0 violations, rc 0. Largest existing file: 037 at 19,879 CRLF bytes | proto/lint2.json; `ls -l migrations` |

### 1.2 The 012 clients (047 is app-safe)
Every reader and writer of the three tables uses the service-role client: product_data_service.py:12 (import), :203/:208, :231/:232, :252/:268, :335/:362, :370/:372, :395/:396 (`get_admin_supabase_client()`); app/api/text_routes.py:1789-1799 (the flush DELETE on product_prices, admin client); app/services/reengagement_service.py:76 (self.client = admin) and :237; scripts/shadow_experiments.py:691-707 (admin, :37-39 of that function). No `get_user_supabase_client` near any of them. Note: service_role needs DELETE on product_prices (the flush), so 047 grants SELECT, INSERT, UPDATE, DELETE.

### 1.3 Identity helpers (reused by module attribute, never duplicated)
| helper | where | measured behaviour |
|---|---|---|
| `spine_key(brand, name, variant=None, category="fragrances")` | app/services/spec_spine_service.py:210-242 (SPINE_CATEGORY :108) | `"<cat>|<brand_axis>|<identity>|<conc>|<ml>"`; brand axis via `_BRAND_ALIAS_GROUPS` (:190-207); identity = `_identity_tokens_ps` minus `_category_padding`; conc = `extract_concentration(surface) or "-"`; ml = `extract_size_ml_any` or "-" |
| `extract_concentration` | price_service.py:4069 over `_CONCENTRATION_PATTERNS` :4053-4062 | labels exactly `Extrait, Parfum Intense, EDP, EDT, EDC, Eau Fraiche, Parfum` |
| `extract_size_ml_any` | price_service.py:4115 | int ml (\d{1,4} ml, or fl oz snapped to a standard size), smallest of several, None when absent |
| `_identity_cache_token` | price_service.py:9408 | conc + qualifiers + size token (the L1 price key axis) |
| `size_variant_token` | price_service.py:4307 | size token string |
| `dedup_brand_name` | app/services/text_sanitize.py:24 | display name builder |
| `normalize_words` | price_service.py:3849 | reads `exact_gate_enabled()` (:4363, default ON) and `normalize_words_empty_fix_enabled()` (:3815, default OFF) per call |
| `kb_source_allowed` / `assert_kb_source_allowed` | app/services/deny_hosts.py:217 / :226 | flag-free, never raises; `DENY_LABELS` = {fragrantica, parfumo, basenotes, fimgs} (:87-89) |

Measured spine_key outputs (probe.out, ENABLE_EXACT_PRICE_GATE and ENABLE_NORMALIZE_WORDS_EMPTY_FIX unset):
- ("Dior", "Sauvage Eau de Parfum 100ml Spray for Men") -> `fragrances|christian+dior|sauvage|EDP|100`
- ("Dior", "Sauvage EDP 50 ml Natural Spray") -> `fragrances|christian+dior|sauvage|EDP|50`
- ("Christian Dior", "Sauvage EDP") -> `fragrances|christian+dior|sauvage|EDP|-`
- ("Dior", "Sauvage EDT 100ml") -> `fragrances|christian+dior|sauvage|EDT|100`
- ("YSL", "Y Eau de Parfum 3.4 oz") -> `fragrances|laurent+saint+ysl+yves||EDP|100` (EMPTY identity: the one-letter name is dropped)
- ("", "") -> `fragrances|||-|-`
- ("Lattafa", "Khamrah | 100ml") -> `fragrances|lattafa|khamrah|-|100`
So juice = `spine_key(...).rsplit("|", 1)[0]` merges 100ml / 50ml / sizeless (R15's fix), keeps EDP vs EDT apart, folds Dior / Christian Dior; and an EMPTY identity would merge every YSL EDP into one row (kb_product_id refuses it, 2.4).

### 1.4 Guards the new code must not trip (measured)
- 043 fence: with the prototypes appended, `_new_gaps` = [] , `fence_user_tables` still 13 tables (no kb_*), users columns unchanged (probe.out). Column census of 045 against USER_REF_ID_RX | PERSONAL_RX: 0 hits. The brief's `gender_marker` WOULD hit PERSONAL_RX (`gender`) and turn kb_products into a "user table" (redden test_fence_sees_the_13_known_user_tables and the table-gap test): the column is `audience` ('men'|'women'|'unisex'), measured reason. `device_key` does not hit PERSONAL_RX (the fence's blind spot, stated limit 9).
- test_migration_index_predicate_immutability.py:93-110 (parametrized per file: 045/047 add two new passing ids), :175-207 (the SECURITY DEFINER p_user_id rule: 045 has no SECURITY DEFINER).
- test_migration_037_security_definer_grants.py census (SECURITY DEFINER only; 045 has none); tests/_retro_r_mig_sql.security_definer_creates on the prototypes = [].
- test_retro_w1_2b.py:321-330 numeric prefixes unique (045, 047 unique at base).
- test_sqlfluff_config.py (corpus lint; size limit above).
- tests/test_s81_d03_deny_and_guards.py:586-610 `test_r1i_single_deny_literal_list`: no tuple/list/set of banned host literals in any app module but deny_hosts.py -> kb_service carries no host literal list (the SQL CHECK lists labels, in migrations/, not app/).
- tests/test_legal_docs_u8.py:761, :823-852 T7 scan of app/services: no non-docstring `https?://host` literal and no client constructor in kb_service.
- test_model_config.py:137 / test_model_config_enforced.py:120 (no model id literal, no LLM call), test_u3c_store_false_pin.py:170, test_sentry_channels_u8d_unit.py:834/:1006, test_auth_error_log_hygiene.py:569, test_w4_13_measurement_truth.py:802, test_u3b_sharing_branch_removed.py:47, test_retro_w0_4.py:739/:760, test_retro_w0_4_efg.py:749, test_legal_s78.py:329, test_legal_disclosure_s77.py:725, test_retro_w1_2b.py:350, test_s81_s03_llm_ledger_v2.py:505, test_migration_043:1298 (all scan app/ as source; kb_service must stay a no-I/O, no-log, no-literal-host leaf).
- tests/test_hermeticity_pins.py:1506/:1581 (scan tests/: no raw tiktoken loader in the new test file).

### 1.5 Line endings
core.autocrlf=true; index LF, working copy CRLF for every backend file (`git ls-files --eol`: CLAUDE.md, deny_hosts.py, 050, test_migration_044 all `i/lf w/crlf`). New files are written LF-content (git normalises); pure ASCII (0 bytes > 127 in both prototypes). CLAUDE.md is edited with the Edit tool (preserves CRLF); `git diff --stat` must show 2-3 lines, never the whole file.

### 1.10 Base pass state (bounded runner, base dfc6502f, no env set)
- Migration readers (25 files: test_migration_023/027/028/029/030/031/032/037/041/042/043/044, test_migration_index_predicate_immutability, test_retro_w1_2b, test_retro_w1_2d, test_sqlfluff_config, test_security_regression, test_referral_full_response_column, test_preference_history_wiring, test_m13_29_feedback_uuid, test_eval_persistence, test_delete_user_cascade, test_consent_capture_w3_16, test_legal_docs_u8, test_s79_b3b_apple_revoke): 625 passed, 10 deselected.
  `[pyt] tag=s14-base-migr start=2026-10-23 15:23:34 end=2026-10-23 15:27:51 elapsed=257s bound=1200s status=OK rc=0`
  `[hermeticity] sentinel checked 625 test(s)`; `[netguard] blocked 12 attempt(s) from 6 node(s)` (all six in test_security_regression.py, the committed baseline class).
- Source scanners + CLAUDE.md readers + spine (22 files: test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_auth_error_log_hygiene, test_domain_s76, test_legal_disclosure_s77, test_legal_s78, test_retro_w0_4_efg, test_retro_w0_4, test_s81_d03_deny_and_guards, test_shopify_pdp_json, test_u3b_sharing_branch_removed, test_w4_13_measurement_truth, test_hermeticity_pins, test_ci_gates, test_behavior_dimension_translation, test_spec_spine_d2, test_s81_s03_llm_ledger_v2): 1758 passed.
  `[pyt] tag=s14-base-scan start=2026-10-23 15:29:12 end=2026-10-23 15:42:15 elapsed=783s bound=1200s status=OK rc=0`
  `[hermeticity] sentinel checked 1758 test(s)`; `[netguard] blocked 22 attempt(s) from 21 node(s)` (hermeticity self-tests by design).
- NOT MEASURED at base in this run: the 13 identity-helper importer files (7.1 chunk C), test_s75_fanout_identity.py (FY25), test_w4_13_flag_off_ledger.py; GREEN runs them at base and head.
- Box state: `node -e 0` 7.3 s, `ls` 9.3 s at 15:0x (slow, under the 30 s stop line).

## 2. Contract

### 2.1 Flag and knobs
None. No `os.getenv`, no `os.environ` in kb_service (pinned R21). Contract freeze (PLAN_S80 section 0): no response key, envelope, route, OpenAPI path or status changes; nothing is client-visible; no refusal path exists in this unit.

### 2.2 Main invariant (replaces flag-OFF identity)
NO-CALLER IDENTITY: every app response, log line, Redis and Supabase call is byte-identical to base because (a) no module under app/ or scripts/ imports kb_service or names a kb_* relation (P1, P2), (b) migrations run only when the owner applies them, and 047 removes privileges no app path uses (1.2), (c) the existing nine-digest node and the W4-13 ledger run unedited and green (4.2).

### 2.3 Migration 045 columns (the derived-equality contract; order as listed)
| table | columns (type; constraint summary) |
|---|---|
| kb_merchants | host text PK (bare lower-case host regex); country text (`^[A-Z]{2,3}$`, the registry carries BH/UAE/KSA/QA/OM/KW, measured data/bh_gcc_sources.json); currency_hint text (`^[A-Z]{3}$`); platform text (1-32); platform_confidence numeric(4,3) 0..1; adapter text (1-64); search_template text (1-1024); robots, politeness, health, challenge, tos jsonb NOT NULL DEFAULT '{}' (object); deny boolean NOT NULL DEFAULT false; status text NOT NULL DEFAULT 'candidate' IN (candidate, live, blocked); blocked_reason text (1-64); partner jsonb NOT NULL DEFAULT '{}' (object; never read by scoring); created_at, updated_at timestamptz NOT NULL DEFAULT now(). Table CHECKs: deny -> status blocked; blocked -> reason present; a host carrying a denied label must be deny |
| kb_products | id text PK (14-512 chars, starts `fragrances|`); brand text NOT NULL (1-128); line text (1-256); name text NOT NULL (1-256); concentration text IN the seven labels of 1.3; audience text IN (men, women, unisex); identity_confidence text NOT NULL IN (high, medium, low) (the result_gate vocabulary, result_gate.py:477-486, minus `unresolved`); created_at, updated_at |
| kb_variants | id text PK; product_id text NOT NULL FK kb_products ON DELETE CASCADE; concentration (same enum); size_ml integer 1..9999; gtin text (`kb_gtin_check_digit_ok`); sku text (1-128); created_at, updated_at; CHECK id = product_id + '|' + 1-4 chars |
| kb_offers | id uuid PK DEFAULT gen_random_uuid(); variant_id FK kb_variants CASCADE; merchant_id text FK kb_merchants(host) CASCADE; amount numeric(14,3) > 0; observed_currency char(3) `^[A-Z]{3}$`; evidence_rung text IN (own_token, page_evidence, expected_missing, platform_api, operator) (the `_currency_label_for` hierarchy, price_service.py:12708-12748, rungs 1-3, plus the platform JSON and operator paths; rung 4, a raw unreadable token, is never storable); size_ml 1..9999; list_vs_sale text NOT NULL DEFAULT 'unknown' IN (list, sale, unknown); in_stock boolean; first_seen, last_seen, captured_at timestamptz NOT NULL DEFAULT now(); canonical_url text NOT NULL (scheme + lower host + path, no `?#` or whitespace, deny labels refused); CHECKs first_seen <= last_seen, url host = merchant or a subdomain of it; UNIQUE (variant_id, merchant_id, canonical_url, amount, observed_currency, list_vs_sale) (an identical re-observation bumps last_seen) |
| kb_images | id uuid; product_id FK CASCADE; variant_id text FK kb_variants CASCADE NULL (NULL = juice-level image; R15 puts images per SKU); url text NOT NULL https only, no `#`, <= 2048, deny labels refused; provenance_host text NOT NULL (host regex, deny refused); source text IN (retailer_jsonld, retailer_og, brand_site, partner_feed, operator); captured_at; UNIQUE (product_id, url). URL + provenance only, never a blob |
| kb_specs | id uuid; product_id FK CASCADE; field text (`^[a-z][a-z0-9_]{0,63}$`); value text (1-2000); source_url text (http(s), deny refused, <= 2048); extractor text NOT NULL (1-64); model text (1-64); cited boolean NOT NULL DEFAULT false; captured_at; CHECK cited -> source_url; UNIQUE (product_id, field) |
| kb_reviews | id uuid; product_id FK CASCADE; source text NOT NULL IN (retailer_jsonld, retailer_widget, brand_site, marketplace) (no deny label, no google / serper / youtube: third-party signals stay <= 30-day TTL, VERIFY bullet 3); aggregate_rating numeric(3,2) 0..5; review_count integer >= 0; source_url text NOT NULL (deny refused); captured_at; CHECK rating or count present; UNIQUE (product_id, source_url). NO snippet / text / body column |
| kb_gaps | id uuid; product_key text (14-520; a kb_product_id or kb_variant_key, no FK: a gap can precede its product); field text (snake); demand_count integer NOT NULL DEFAULT 1 >= 0; first_seen, last_seen; state text NOT NULL DEFAULT 'open' IN (open, queued, needs_operator, licence, closed); source_hint text (1-256, no deny label); UNIQUE (product_key, field) |
| kb_feedback | id uuid; compare_request_id uuid NOT NULL; product_id text FK kb_products CASCADE NULL; field text (snake); verdict text IN (correct, wrong, unsure) (R0-2 vocabulary); device_key text NOT NULL `^[a-f0-9]{64}$` (S81-05 HMAC); created_at. Unique index (device_key, compare_request_id, field, coalesce(product_id, '')) = one vote |
| kb_coverage_daily | day date; metric text (`^[a-z][a-z0-9_.:-]{0,127}$`, room for `robots_skip:<host>`); value numeric NOT NULL; n integer >= 0; PK (day, metric) |

Indexes (all predicates IMMUTABLE): idx_kb_merchants_status, idx_kb_variants_product, idx_kb_variants_gtin (WHERE gtin IS NOT NULL), idx_kb_offers_latest (variant_id, merchant_id, captured_at DESC, id DESC), idx_kb_offers_merchant, idx_kb_images_product, idx_kb_images_variant (WHERE variant_id IS NOT NULL), idx_kb_reviews_product, idx_kb_gaps_open_demand (demand_count DESC, last_seen DESC WHERE state = 'open'), idx_kb_feedback_device_key, idx_kb_feedback_product (WHERE product_id IS NOT NULL), uq_kb_feedback_one_vote.

View `kb_offers_latest WITH (security_invoker = true)`: DISTINCT ON (variant_id, merchant_id) every kb_offers column, ORDER BY captured_at DESC, id DESC.

Functions (all `SECURITY INVOKER`, `SET search_path TO 'public'`, every relation schema-qualified):
- `kb_gtin_check_digit_ok(p_gtin text) RETURNS boolean LANGUAGE sql IMMUTABLE STRICT`: true iff 8, 12, 13 or 14 digits and the GS1 mod-10 check digit holds (weights 3,1 from the digit left of the check digit); a CASE guards the regex before any cast.
- `kb_prune_offers(p_max_age_days integer, p_keep_per_merchant integer) RETURNS integer LANGUAGE plpgsql`: raises on bounds outside 1..3650 / 1..1000; deletes only rows that are BOTH beyond the newest `p_keep_per_merchant` per (variant, merchant) AND captured more than `p_max_age_days` ago; returns the row count. The latest offer per merchant is never pruned.
- `kb_product_card(p_product_id text) RETURNS jsonb LANGUAGE sql STABLE`: `{"product": <row>, "variants": [...], "offers": [<kb_offers_latest rows of the product's variants>], "images": [...], "specs": [<cited rows only>], "rating": {"sources", "review_count", "rating" (review-count-weighted mean over rows carrying both, 2 dp, null when none)}}`; NULL when the product does not exist. Array members are `to_jsonb(row)`, so their keys equal the table columns.

Grants: per table and the view `REVOKE ALL ON TABLE public.<t> FROM PUBLIC, anon, authenticated, service_role`; tables `GRANT SELECT, INSERT, UPDATE, DELETE ... TO service_role`; the view `GRANT SELECT` only; functions `REVOKE ALL ON FUNCTION ... FROM PUBLIC, anon, authenticated` + `GRANT EXECUTE ... TO service_role`. RLS enabled on all ten tables, NO policy. A first DO block raises unless `server_version_num >= 150000`.

### 2.4 kb_service.py (pure leaf; never raises; no I/O, no logging, no clock, no env)
Imports: stdlib (`re`, `uuid` only if needed, `datetime` types, `ipaddress`, `typing`, `urllib.parse`) and, by MODULE ATTRIBUTE only, `from app.services import spec_spine_service as _spine`, `from app.services import price_service as _ps`, `from app.services import deny_hosts as _deny` (resolved inside the functions or at module top; never `from app.services.X import name`). Constants: `KB_CATEGORY = "fragrances"`, `KB_CONCENTRATIONS` = tuple(label for _p, label in `_ps._CONCENTRATION_PATTERNS`) computed at call time (not a copied literal), `KB_TABLES` (the ten names), `KB_COLUMNS` (table -> ordered column tuple, equal to 2.3), `KB_BUILDER_KEYS` (table -> KB_COLUMNS minus a uuid `id` and minus `created_at` / `updated_at`), the enum tuples of 2.3.

| function | signature | contract |
|---|---|---|
| kb_product_id | `(brand, name, variant=None) -> Optional[str]` | `_spine.spine_key(brand, name, variant)` (default category) then `rsplit("|", 1)[0]`; None when brand and name are both blank, the brand-axis field or the identity field (fields 2 and 3) is empty, a non-str is passed, or anything raises. Values: 1.3 matrix |
| kb_variant_key | `(product_id, concentration, size_ml) -> Optional[str]` | `product_id + "|" + ml` where ml = `str(size_ml)` for an int 1..9999 (bool refused) or "-" for None; None when product_id is not a kb_product_id shape (starts `fragrances|`, 3 pipes), when `concentration or "-"` differs from product_id's last field, or ml invalid. Invariant: `kb_variant_key(kb_product_id(b, n, v), extract_concentration(s), extract_size_ml_any(s)) == spine_key(b, n, v)` for s = the joined surface |
| kb_source_allowed | `(value) -> bool` | `return _deny.kb_source_allowed(value)` read at CALL time (an alias bound at import is a mutant, M20); flag-free |
| canonical_offer_url | `(url) -> Optional[str]` | http/https only (lower-cased); host = `urlsplit().hostname` lower-cased, trailing dot dropped, ASCII `[a-z0-9.-]` with a dot, not an IP literal; userinfo present -> None; port None or the scheme default -> dropped, any other -> None; backslash, whitespace or a control char anywhere -> None; path kept as given, empty -> "/"; query and fragment dropped; every non-None output matches the 045 canonical_url CHECK |
| gtin_check_digit_ok | `(gtin) -> bool` | str of exactly 8, 12, 13 or 14 ASCII digits with a valid GS1 mod-10 check digit; everything else False (bool, int, None, spaces) |
| build_merchant_row, build_product_row, build_variant_row, build_offer_row, build_image_row, build_spec_row, build_review_row, build_gap_row, build_feedback_row, build_coverage_row | keyword-only args named as the columns; timestamps as aware `datetime` (ISO-8601 strings in the dict) | a dict whose key SET equals `KB_BUILDER_KEYS[table]`, or None when any value breaks a 2.3 CHECK the leaf can evaluate (enum, regex, range, the deny labels via `kb_source_allowed`, `canonical_offer_url(url) == url`, `gtin_check_digit_ok`, `kb_variant_key` extension, cited -> source_url, device_key 64-hex, merchant host vs url host). first_seen / last_seen default to captured_at |

### 2.5 Failure table
| situation | result |
|---|---|
| owner never applies 045/047 | nothing changes; kb_service unused |
| 045 on PostgreSQL < 15 | the first DO block raises; the transaction rolls back whole |
| a writer passes a denied URL/host | builder returns None; the SQL CHECK is the belt |
| empty identity (YSL "Y") | kb_product_id None: the writer skips (never a merged row) |
| flags ENABLE_EXACT_PRICE_GATE / ENABLE_NORMALIZE_WORDS_EMPTY_FIX flipped | identity tokens may change -> new ids (stated limit 4) |
| 047 PRECHECK lists a policy beyond the eight | 047 still removes the anon / authenticated table privileges; the extra policy is dropped by name in a follow-up |

### 2.6 Test seams [production values]
`kb_service._spine` / `_ps` / `_deny` module attributes (monkeypatchable) [the real modules]; `KB_COLUMNS` / `KB_BUILDER_KEYS` [2.3]; env for the identity pins: `ENABLE_EXACT_PRICE_GATE`, `ENABLE_NORMALIZE_WORDS_EMPTY_FIX` set explicitly per row [prod: gate ON, fix OFF].

## 3. Change list (GREEN order; byte copies first)
0. Byte copies (shutil.copyfile + sha256) of CLAUDE.md before editing; mutation lock per the common brief.
1. `migrations/045_kb_core.sql` = Appendix A.1 (the lint-clean prototype; keep it under 19,500 LF bytes; pure ASCII).
2. `migrations/rollback/045_kb_core.sql`: BEGIN; DROP FUNCTION IF EXISTS public.kb_product_card(text); DROP FUNCTION IF EXISTS public.kb_prune_offers(integer, integer); DROP VIEW IF EXISTS public.kb_offers_latest; DROP TABLE IF EXISTS kb_feedback, kb_gaps, kb_reviews, kb_specs, kb_images, kb_offers, kb_variants, kb_products, kb_merchants, kb_coverage_daily (one statement each, children first); DROP FUNCTION IF EXISTS public.kb_gtin_check_digit_ok(text); COMMIT. Header: no flag to flip; destructive (KB rows lost).
3. `migrations/047_012_revoke.sql` = Appendix A.2.
4. `migrations/rollback/047_012_revoke.sql`: BEGIN; the eight CREATE POLICY statements of 012 verbatim (schema-qualified `public.`); `GRANT ALL ON TABLE public.product_specs, ... TO anon, authenticated` (the stock default the 047 PRECHECK relacl is expected to show; header: compare with the recorded PRECHECK output, this re-opens the poisoning path); COMMIT.
5. `app/services/kb_service.py` per 2.4 (LF content, ASCII, docstring states "no importer in app/ yet; S81-15..S81-22 call it").
6. `tests/test_s81_kb_schema.py` (section 5) -- the RED file; GREEN does not weaken it.
7. `.qa-s80/APPLY_045_1_PRECHECK.sql` (read-only: server_version_num, `to_regclass` of the ten tables + view all NULL, the roles anon / authenticated / service_role exist, `to_regprocedure` of the three functions NULL), `APPLY_045_2_ONE_PASTE.sql` (the BEGIN..COMMIT span byte-identical to 045, LF), `APPLY_045_3_POSTCHECK.sql` (relrowsecurity per table; has_table_privilege service_role S/I/U/D true, anon + authenticated SELECT / INSERT false; view SELECT service_role true, anon false; `has_function_privilege` EXECUTE service_role true, anon false; `prosecdef` false for the three; `kb_product_card('fragrances|' || 'x|y|-')` IS NULL; `kb_gtin_check_digit_ok` on a GTIN built by concatenation true and its last digit altered false). Same three for 047: PRECHECK = `SELECT policyname, permissive, cmd, roles, qual, with_check FROM pg_policies WHERE schemaname = 'public' AND tablename IN (...)` + relacl + has_table_privilege anon/authenticated INSERT/UPDATE/DELETE (expected true today); POSTCHECK = zero policies on the three, anon/authenticated SELECT/INSERT/UPDATE/DELETE false, service_role all four true. Every check file: whole-line comments only, read-only, sqlfluff clean, ASCII, no digit run >= 8.
8. CLAUDE.md (Edit tool, CRLF kept): (a) `CLAUDE.md:92` after the 044 clause insert `**045 (\`kb_*\` knowledge-base core, S81-14) and 047 (the 012-table REVOKE, S81-14) written, NOT applied** (the owner applies 045 before any kb_* writer flag flips (S81-15 / S81-16 / S81-17) and 047 after the live pg_policies read; one-paste files in the session-81 state folder);` and change "anything newer than 044" -> keep as is (045/047 are recorded as not applied); (b) the section-8 row after the S81-03 block (`CLAUDE.md:485-486`), before `## Tests` (`:488`).
No other file.

## 4. Existing pins
### 4.1 Pins that change deliberately
None edited. Two parametrized pins GAIN node ids (not edits): `test_migration_index_predicate_immutability.py::test_index_predicates_are_immutable[045_kb_core.sql]` and `[047_012_revoke.sql]` (green).
### 4.2 Pins that must stay green and unedited
Every file of 1.10 plus: test_migration_043 (fence: 13 user tables, no gaps), test_migration_037 census, test_retro_w1_2b prefixes, test_sqlfluff_config corpus lint (045 must actually be linted: R20), test_s81_d03 R1i, test_legal_docs_u8 T7, test_spec_spine_d2 (spine_key untouched), `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main` (nine digests), `tests/test_w4_13_flag_off_ledger.py` (45 scenarios), test_ci_gates + test_behavior_dimension_translation (CLAUDE.md readers).

## 5. RED tests -- `tests/test_s81_kb_schema.py`
Harness: hermetic (autouse zero-network guard from `tests/_retro_r_mig_sql.install_network_guard`, attempts asserted empty); module helper `_kb()` = `importlib.util.find_spec("app.services.kb_service")`, `assert spec is not None, "S81-14 leaf missing"`, then import (RED at base on that AssertionError); `_require(path)` asserts `path.is_file()` before reading (RED on AssertionError, never FileNotFoundError); SQL helpers reuse `tests/_retro_r_mig_sql` (`code_only`, `norm`, `comment_lines`) and the 043 module's `_split_top` / `_balanced` / fence functions by module attribute; Python emulation of a SQL regex translates `[:space:]` to `\s`. Synthetic values built at run time: GTINs from a test-side mod-10 function over digits concatenated from short strings; `DK = "ab" * 32`; uuids via `uuid.uuid4()`; hosts under `.example`. Env per row via monkeypatch: `ENABLE_EXACT_PRICE_GATE` and `ENABLE_NORMALIZE_WORDS_EMPTY_FIX` delenv'd (production defaults) unless the row says otherwise; one row repeats the key matrix with `ENABLE_EXACT_PRICE_GATE=" TRUE "`.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | test_s14_r01_files_exist_once | exactly `045_kb_core.sql` and `047_012_revoke.sql` forward + rollback; no other 045_/047_ file; no 039_ | RED | 3.1-3.4 |
| R2 | test_s14_r02_one_transaction (param 4 files) | first stmt `begin`, last `commit`, one each | RED | 3.1-3.4 |
| R3 | test_s14_r03_045_objects | CREATE TABLE names == the ten; one view kb_offers_latest; CREATE FUNCTION signatures == {kb_gtin_check_digit_ok(text), kb_prune_offers(integer, integer), kb_product_card(text)}; no DROP / DELETE / UPDATE / INSERT at top level | RED | 3.1 |
| R4 | test_s14_r04_columns (param 10 tables) | parsed ordered column names == `kb_service.KB_COLUMNS[t]` == the spec literal of 2.3 | RED | 3.1, 3.5 |
| R5 | test_s14_r05_service_role_only (param 10 tables + view) | ENABLE RLS (tables); no CREATE POLICY in 045; `revoke all on table public.<t> from public, anon, authenticated, service_role`; exactly one GRANT whose roles == [service_role] and privileges == {select, insert, update, delete} (view: {select}) | RED | 3.1 |
| R6 | test_s14_r06_functions | each function: `security invoker`, `set search_path to ''` (literal-blanked), no `security definer`; `revoke all on function ... from public, anon, authenticated`; exactly one GRANT EXECUTE, to service_role; no GRANT naming anon / authenticated / public in 045 incl. dollar bodies | RED | 3.1 |
| R7 | test_s14_r07_fks | every REFERENCES targets public.kb_* and ends `on delete cascade`; no reference to users / auth | RED | 3.1 |
| R8 | test_s14_r08_no_user_column_census | every 045 column misses t043.USER_REF_ID_RX and PERSONAL_RX; `t043._new_gaps([(045), (047)])` == set(); `fence_user_tables` has no kb_* key; no column named device_id / fingerprint* / email / ip* | RED (file absent) | 3.1 (audience not gender_marker) |
| R9 | test_s14_r09_deny_label_checks | each of kb_offers.canonical_url, kb_images.url, kb_images.provenance_host, kb_specs.source_url, kb_reviews.source_url, kb_merchants.host, kb_gaps.source_hint carries a CHECK whose label group set == `deny_hosts.DENY_LABELS`; Python emulation: `https://fr.fragrantica.com/x`, `https://fimgs.net/a.jpg`, `https://parfumo.de/p` rejected, `https://shop.example/p` accepted, `https://notfragrantica.example/p` accepted | RED | 3.1 |
| R10 | test_s14_r10_reviews_source_and_no_text | kb_reviews.source IN list == 2.3; no list member contains a deny label or google / serper / youtube; kb_reviews has no column matching snippet / text / body / quote | RED | 3.1 |
| R11 | test_s14_r11_concentration_enum (param kb_products, kb_variants) | IN list == `[lab for _p, lab in price_service._CONCENTRATION_PATTERNS]` (order and set) | RED | 3.1 |
| R12 | test_s14_r12_indexes | index names == 2.3 set; `_volatile_hits` empty for every predicate | RED | 3.1 |
| R13 | test_s14_r13_view | `with (security_invoker = true)`, `distinct on (o.variant_id, o.merchant_id)`, `order by ... o.captured_at desc, o.id desc`; selects every kb_offers column | RED | 3.1 |
| R14 | test_s14_r14_card | body keys exactly product / variants / offers / images / specs / rating; offers read kb_offers_latest; specs filtered `and s.cited`; `language sql`, `stable`; first DO block checks 150000 | RED | 3.1 |
| R15 | test_s14_r15_prune | raises on out-of-range bounds (1..3650, 1..1000); the DELETE predicate contains both `r.rn > p_keep_per_merchant` and `r.captured_at < now() - make_interval(days => p_max_age_days)`; returns ROW_COUNT | RED | 3.1 |
| R16 | test_s14_r16_rollbacks | rollback/045 statement list == 3.2 exactly; rollback/047 recreates the policy names parsed from 012 and nothing else beyond the GRANT | RED | 3.2, 3.4 |
| R17 | test_s14_r17_047_statements | DROP POLICY IF EXISTS set == the CREATE POLICY (name, table) set parsed from 012 (derived, not a literal); 3 ENABLE RLS; 3 `revoke all ... from public, anon, authenticated`; 3 GRANT select, insert, update, delete to service_role; nothing else; no CREATE POLICY | RED | 3.3 |
| R18 | test_s14_r18_policy_census_closed | replaying CREATE / DROP POLICY over the forward path in file order leaves no policy on the three tables | RED | 3.3 |
| R19 | test_s14_r19_headers | 045 comments name S81-14, `rollback/045_kb_core.sql`, service role, PostgreSQL 15, before; 047 comments name product_data_service, pg_policies or PRECHECK, `rollback/047_012_revoke.sql` | RED | 3.1, 3.3 |
| R20 | test_s14_r20_size_ascii (param 4 files) | LF bytes + newline count < 20000 (sqlfluff large-file skip, measured 1.1); 0 bytes > 127 | RED | 3.1-3.4 |
| R21 | test_s14_r21_leaf_pure | find_spec not None; AST: imports only stdlib allowlist + the three `from app.services import <m> as _x`; no `from app.services.<m> import`; no os.getenv / os.environ / open( / logging / asyncio / socket / supabase / httpx / requests / time.time / datetime.now | RED | 3.5 |
| R22 | test_s14_r22_kb_product_id (param the 1.3 matrix + padded-gate env) | == spine_key(...).rsplit("|",1)[0]; 100ml == 50ml == sizeless; EDP != EDT; Dior == Christian Dior; YSL "Y" -> None; ("", "") -> None; None / 3 / b"x" -> None; a recorder monkeypatched on `spec_spine_service.spine_key` returning a fixed `fragrances|a|b|EDP|9` makes kb_product_id return `fragrances|a|b|EDP` (reuse proven) | RED | 3.5 |
| R23 | test_s14_r23_kb_variant_key | the invariant of 2.4 on the matrix; size None -> `|-`; 0, -1, 10000, True, 1.5, "100" -> None; mismatched concentration -> None; bad product_id -> None | RED | 3.5 |
| R24 | test_s14_r24_source_allowed | a recorder on `deny_hosts.kb_source_allowed` is called once with the value; denied URL / host / name False and allowed True under ENABLE_DATA_GUARDS_V2 unset, "false", " TRUE "; junk (None, 3, b"x") never raises | RED | 3.5 |
| R25 | test_s14_r25_canonical_offer_url (param ~20 rows) | the 2.4 rules row by row (query/fragment drop, case, default-port drop, other port None, userinfo None built at run time, IP None, backslash None, whitespace None, ftp None, empty path "/", trailing dot); every non-None output matches the Python-emulated 045 CHECK | RED | 3.5 |
| R26 | test_s14_r26_gtin | built-valid GTIN-8/12/13/14 True; last digit altered False; lengths 7, 9, 10, 11, 15 False; letters, spaces, None, True, int False | RED | 3.5 |
| R27 | test_s14_r27_builder_keys (param 10 tables) | builder(valid synthetic kwargs) returns a dict; set(keys) == columns parsed from 045 minus uuid id minus created_at / updated_at | RED | 3.5 |
| R28 | test_s14_r28_builders_refuse (param ~12 rows) | denied canonical_url / image url / review source_url, http image, review source "fragrantica", device_key not 64-hex, cited spec without source_url, identity_confidence "unresolved", variant id not extending product, offer url host != merchant, amount 0, currency "bhd" -> None | RED | 3.5 |
| P1 | test_s14_p01_no_importer | AST over app/**/*.py and scripts/**/*.py (minus kb_service.py): no import of / attribute access to kb_service | PIN | stays green |
| P2 | test_s14_p02_no_kb_reader | no `"kb_` table / rpc literal in app/ or scripts/ outside kb_service.py | PIN | stays green |
| P3 | test_s14_p03_012_clients_are_admin | every app/scripts function whose source names product_specs / product_prices / product_reviews in a `.table(` call also calls get_admin_supabase_client (or uses self.client set from it) and never get_user_supabase_client | PIN | 047 safety |
| P4 | test_s14_p04_spine_key_literals | the seven 1.3 outputs as literals, env: gate unset and gate " TRUE ", fix unset | PIN | identity contract |

Counts: 28 RED rows (about 150 nodes with params), 4 PIN rows. B1 rule: no flag exists, so there is no flag-OFF PIN to configure; the "no behaviour change" proof is P1/P2 (no caller) plus the unedited FY25 and W4-13 nodes.

## 6. Mutation table (byte copy, exact-string edit matching once, the killing rows via pyt.py -k, restore, sha256)
| # | mutant | killed by |
|---|---|---|
| M1 | 045: drop `, service_role` from one table REVOKE | R5 |
| M2 | 045: add `GRANT SELECT ON TABLE public.kb_products TO anon;` | R5, R6 |
| M3 | 045: kb_product_card `SECURITY INVOKER` -> `SECURITY DEFINER` | R6 (and the 037 census pin) |
| M4 | 045: kb_variants FK without `ON DELETE CASCADE` | R7 |
| M5 | 045: kb_feedback gains `user_id uuid REFERENCES public.users (id)` | R8, R4 |
| M6 | 045: `audience` -> `gender_marker` | R8, R4 |
| M7 | 045: `basenotes` removed from the kb_offers canonical_url CHECK | R9 |
| M8 | 045: `'google'` added to kb_reviews.source | R10 |
| M9 | 045: `'Eau Fraiche'` removed from kb_products.concentration | R11 |
| M10 | 045: idx_kb_gaps predicate `WHERE last_seen > now() - interval '30 days'` | R12 |
| M11 | 045: view without `WITH (security_invoker = true)` | R13 |
| M12 | 045: card specs without `AND s.cited` | R14 |
| M13 | 045: prune predicate without `r.rn > p_keep_per_merchant AND` | R15 |
| M14 | 047: drop `DROP POLICY IF EXISTS reviews_update ...` | R17, R18 |
| M15 | 047: one REVOKE without `authenticated` | R17 |
| M16 | kb_service: kb_product_id returns the full spine_key | R22 |
| M17 | kb_service: kb_product_id lower().split() normaliser instead of `_spine.spine_key` | R22 (recorder) |
| M18 | kb_service: empty identity allowed | R22 |
| M19 | kb_service: kb_variant_key ignores a concentration mismatch | R23 |
| M20 | kb_service: `kb_source_allowed = _deny.kb_source_allowed` bound at import | R24 (recorder not called) |
| M21 | kb_service: canonical_offer_url keeps the query | R25 |
| M22 | kb_service: canonical_offer_url strips userinfo instead of refusing | R25 |
| M23 | kb_service: GTIN weights 1,3 instead of 3,1 | R26 |
| M24 | kb_service: build_offer_row omits observed_currency | R27 |
| M25 | kb_service: build_offer_row skips the deny check | R28 |
| M26 | kb_service: adds `import os` + `os.getenv("X")` | R21 |
| M27 | rollback/045 omits `DROP FUNCTION IF EXISTS public.kb_gtin_check_digit_ok(text)` | R16 |
| M28 | 045: header padded past 20,000 CRLF bytes | R20 |
| M29 | app/services/text_routes-like importer: a scratch module under app/ importing kb_service | P1 |
Equivalent-survivor candidates for a ruling: none expected.

## 7. Comm set and gates for GREEN (cheapest first)
1. `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on kb_service.py and the test file; bytes > 127 = 0 on every written file; `git diff --stat` (CLAUDE.md 2-3 lines only).
2. sqlfluff (repo config, PYTHONIOENCODING=utf-8) on the 4 migration files AND the 6 APPLY files: 0 violations and NO "Skipping" warning on stderr.
3. One-paste identity: a python check that the BEGIN..COMMIT span of each ONE_PASTE equals its migration (LF).
4. Unit file `tests/test_s81_kb_schema.py` (bound 600): all rows green at head; at base the RED rows fail on AssertionError only (the RED agent's table).
5. Mutation table M1-M29 (bound 600 each).
6. Comm set (chunks <= 25, bound 1200, base and head, `comm -13` of FAILED ids empty): chunk A = the 25 migration readers of 1.10; chunk B = the 22 scanner / CLAUDE.md-reader files of 1.10; chunk C = identity-helper importers test_ws5_honesty, test_winner_prose_reconciliation, test_w4_12_display_contract, test_tradeoffs_dedup_parity, test_s80_url_mode_v2, test_s80_b1, test_price_cache_key_parity, test_m21_brand_dedup_and_verdict_copy, test_fragrance_content_quality, test_flush_live_price_key, test_correctness_cache_key, test_cellular_generation_cache_key, test_cache_key_size_variant, test_s75_fanout_identity, test_w4_13_flag_off_ledger + the new test file. MINUS the four test_precommit_hook*.py (.githooks untouched). No SmartCompareApp-scanning tests (nothing client-visible).

## 8. CLAUDE.md row and owner steps
Row text (insert after the S81-03 block, before `## Tests`):
"**SESSION 81 unit (S81-14 KB-SCHEMA, 2026-10-23; NO flag, no call site; spec `.qa-s80/S81-14_UNIT_SPEC.md` of the unit worktree):** migrations `045_kb_core.sql` (ten service-role kb_* tables + `kb_offers_latest` + `kb_gtin_check_digit_ok` / `kb_prune_offers` / `kb_product_card`) and `047_012_revoke.sql` (the eight 012 policies dropped by name, anon / authenticated table privileges revoked, service_role re-granted) are WRITTEN, NOT APPLIED; `app/services/kb_service.py` is a pure leaf with no importer. Key split: a JUICE (`kb_products.id = spine_key(...)` minus the ml field: brand axis + identity + concentration) carries specs, notes and reviews; a SKU (`kb_variants.id` = juice + `|<ml>`) carries offers (per merchant) and images. An empty identity (e.g. a one-letter name) mints no id. Denied labels (fragrantica, parfumo, basenotes, fimgs) are refused by CHECK on every URL / host column and by `deny_hosts.kb_source_allowed` in the builders. No users FK and no user / email / address / fingerprint column (the 043 fence finds no kb_* table; the brief's `gender_marker` is `audience`, because PERSONAL_RX matches `gender`). Stated limit: `kb_feedback.device_key` (the S81-05 HMAC key) is outside the 043 cascade; deletion by device is S81-22's hook. Apply 045 before any kb_* writer flag (S81-15 / S81-16 / S81-17); apply 047 after the owner's live pg_policies read (app code is unaffected: every 012 reader and writer uses the service-role client)."

Owner steps (names only): (1) run APPLY_045_1_PRECHECK, send the output; (2) APPLY_045_2_ONE_PASTE; (3) APPLY_045_3_POSTCHECK, send the output; (4) APPLY_047_1_PRECHECK (the live pg_policies read), send it; the orchestrator confirms the eight names; (5) APPLY_047_2_ONE_PASTE; (6) APPLY_047_3_POSTCHECK. A ledger line per step.

## 9. Stated limits
1. Inert until the owner applies 045 / 047 and a later flagged unit writes or reads.
2. The SQL CHECKs are a belt: the deny-label regex is a label scan of the authority (stricter than D03's registrable-label rule: `parfumo.shop.example` is refused); the builders' `kb_source_allowed` is the rule.
3. The gtin check is format plus check digit only (no GS1 prefix registry); `kb_gtin_check_digit_ok` is not executable offline (POSTCHECK runs it).
4. kb ids inherit the price path's identity machinery and its flag reads (ENABLE_EXACT_PRICE_GATE ON in prod, ENABLE_NORMALIZE_WORDS_EMPTY_FIX OFF): seeding and serving must run under the same flag state; a flip re-mints ids (orphans, no wrong merge).
5. One-letter / alias-only names lose identity and mint no id (measured YSL "Y"): those juices need a curated alias (S81-16).
6. Fragrance-only: `kb_products.id` must start `fragrances|`; skincare / makeup need a later migration.
7. `updated_at` is set by the writer (no trigger); `kb_offers` grows until `kb_prune_offers` runs (S81-19 / D17 schedule it).
8. Ratings are stored on a 0..5 scale; the writer normalises a page's bestRating.
9. `kb_feedback.device_key` is pseudonymous device data outside the 043 fence vocabulary (the fence's PERSONAL_RX does not match `device_key`) and outside `delete_user_cascade`; S81-22 adds deletion by device and the privacy text (S81-12) must disclose it.
10. The view and functions need PostgreSQL 15+ (refused loudly below).
11. 047's rollback re-opens the anon write path (only for an emergency, with the PRECHECK relacl in hand).
12. The APPLY_*.sql files live in `.qa-s80/` (gitignored) and the docs branch, so no committed test pins them; gate 3 does.

## 10. Out of scope
Any writer or reader (S81-15..S81-22); the registry seed; processors.json (no new external host); the privacy text; migrations 046 / 048 / 049; deleting rows by device; editing the 043 fence vocabulary; black-clean-paths membership for the new files (optional).

## 11. Open questions for the orchestrator
Q1. `gender_marker` renamed `audience` (measured fence hit). Alternative: keep the name and add a NOT_PERSONAL entry to tests/test_migration_043 (edits a pinned file). Default: rename.
Q2. kb_images gains a nullable `variant_id` (R15: image per SKU; the brief lists product_id only). Default: keep.
Q3. Juice id INCLUDES concentration (R15 "brand|line|concentration"; spec_spine_service docstring: EDP / EDT are different compositions), so `kb_variant_key(product_id, concentration, size_ml)` validates the concentration and appends ml only (id equals the full spine_key). PLAN_S81's "variant on concentration + ml" read literally would put concentration on the variant and merge EDP / EDT notes. Default: as specified.
Q4. `kb_product_id` returns Optional[str] (None for an empty identity), not str. Default: Optional.
Q5. canonical_offer_url REFUSES a URL with userinfo or a non-default port (the brief says "no userinfo"; stripping is the alternative). Default: refuse.
Q6. 045 revokes service_role too before re-granting (050 precedent) where 044 did not. Default: 050 form.
Q7. Should the six APPLY files be committed under `docs/investigations/2026-10-22-session-81-state/` in the repo (043 precedent, a CI pin) instead of `.qa-s80/`? Default: `.qa-s80/` + gate 3, per the brief.
Q8. 047 also revokes SELECT (the 012 select policies were USING (true) for anon). App code never reads the three tables with the anon key (1.2). Default: revoke ALL.

Not done in this spec: the RED file, GREEN code, the APPLY files, the comm run at head, the chunk-C base run, any live read.

## Appendix A. Prototype migrations (lint-clean with the repo .sqlfluff, sqlfluff 4.3.0; probed against the 043 fence, the immutability detector and the SECURITY DEFINER census; pure ASCII)

### A.1 migrations/045_kb_core.sql (prototype sha256 71f4221fd5882ecfb93058766051c028bcec3294d640a3feeb9a8dcdb9333038, 19149 LF bytes)

```sql
-- Migration 045: the owned knowledge base core, kb_* (S81-14 KB-SCHEMA, S81)
--
-- Ten tables, one view, three functions. Per JUICE (brand + identity +
-- concentration): kb_products, kb_specs, kb_reviews. Per SKU (juice + ml):
-- kb_variants, kb_offers (SKU x merchant), kb_images. Registry kb_merchants;
-- loop kb_gaps, kb_feedback, kb_coverage_daily. Ids come from
-- app/services/kb_service.py (kb_product_id, kb_variant_key).
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION: no code reads or writes kb_*.
-- APPLY ORDER: before any kb_* writer flag flips (S81-15 / S81-16 / S81-17);
-- none against 047 or 050. PostgreSQL 15+ (security_invoker view).
--
-- Service role only (044 / 050; the 037 both-readings rule): RLS on, no
-- policy, REVOKE ALL from PUBLIC, anon, authenticated, service_role, then one
-- GRANT to service_role. Functions: SECURITY INVOKER, pinned search_path,
-- EXECUTE for service_role only. No users FK, no user / email / address /
-- fingerprint column (the 043 fence sees no kb_* table); kb_feedback.device_key
-- is the S81-05 HMAC key, deleted by device in S81-22 (a stated limit).
-- Denied labels (fragrantica, parfumo, basenotes, fimgs) are refused by CHECK
-- on every URL and host column.
--
-- Postcheck: APPLY_045_3_POSTCHECK.sql. Rollback: migrations/rollback/045_kb_core.sql

BEGIN;

DO $$
BEGIN
  IF current_setting('server_version_num')::int < 150000 THEN
    RAISE EXCEPTION '045 needs PostgreSQL 15 or later';
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION public.kb_gtin_check_digit_ok(p_gtin text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
SECURITY INVOKER
SET search_path TO 'public'
AS $$
  SELECT CASE
    WHEN p_gtin !~ '^([0-9]{8}|[0-9]{12,14})$' THEN false
    ELSE (
      SELECT (10 - (sum(
        substr(p_gtin, i, 1)::int
        * CASE WHEN (length(p_gtin) - i) % 2 = 1 THEN 3 ELSE 1 END
      ) % 10)) % 10
      FROM generate_series(1, length(p_gtin) - 1) AS i
    ) = substr(p_gtin, length(p_gtin), 1)::int
  END
$$;

CREATE TABLE IF NOT EXISTS public.kb_merchants (
    host text PRIMARY KEY CHECK (
        host ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'
    ),
    country text CHECK (country IS NULL OR country ~ '^[A-Z]{2,3}$'),
    currency_hint text CHECK (currency_hint IS NULL OR currency_hint ~ '^[A-Z]{3}$'),
    platform text CHECK (platform IS NULL OR char_length(platform) BETWEEN 1 AND 32),
    platform_confidence numeric(4, 3) CHECK (
        platform_confidence IS NULL OR platform_confidence BETWEEN 0 AND 1
    ),
    adapter text CHECK (adapter IS NULL OR char_length(adapter) BETWEEN 1 AND 64),
    search_template text CHECK (
        search_template IS NULL OR char_length(search_template) BETWEEN 1 AND 1024
    ),
    robots jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(robots) = 'object'),
    politeness jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(politeness) = 'object'),
    health jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(health) = 'object'),
    challenge jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(challenge) = 'object'),
    tos jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(tos) = 'object'),
    deny boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'live', 'blocked')),
    blocked_reason text CHECK (blocked_reason IS NULL OR char_length(blocked_reason) BETWEEN 1 AND 64),
    partner jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(partner) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_merchants_deny_is_blocked CHECK (NOT deny OR status = 'blocked'),
    CONSTRAINT kb_merchants_blocked_has_reason CHECK (status <> 'blocked' OR blocked_reason IS NOT NULL),
    CONSTRAINT kb_merchants_denied_label_is_denied CHECK (
        deny OR host !~ '(^|[.])(fragrantica|parfumo|basenotes|fimgs)[.]'
    )
);

CREATE TABLE IF NOT EXISTS public.kb_products (
    id text PRIMARY KEY CHECK (char_length(id) BETWEEN 14 AND 512 AND left(id, 11) = 'fragrances|'),
    brand text NOT NULL CHECK (char_length(brand) BETWEEN 1 AND 128),
    line text CHECK (line IS NULL OR char_length(line) BETWEEN 1 AND 256),
    name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 256),
    concentration text CHECK (
        concentration IS NULL
        OR concentration IN ('Extrait', 'Parfum Intense', 'EDP', 'EDT', 'EDC', 'Eau Fraiche', 'Parfum')
    ),
    audience text CHECK (audience IS NULL OR audience IN ('men', 'women', 'unisex')),
    identity_confidence text NOT NULL CHECK (identity_confidence IN ('high', 'medium', 'low')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.kb_variants (
    id text PRIMARY KEY,
    product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE,
    concentration text CHECK (
        concentration IS NULL
        OR concentration IN ('Extrait', 'Parfum Intense', 'EDP', 'EDT', 'EDC', 'Eau Fraiche', 'Parfum')
    ),
    size_ml integer CHECK (size_ml IS NULL OR size_ml BETWEEN 1 AND 9999),
    gtin text CHECK (gtin IS NULL OR public.kb_gtin_check_digit_ok(gtin)),
    sku text CHECK (sku IS NULL OR char_length(sku) BETWEEN 1 AND 128),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_variants_id_extends_product CHECK (
        left(id, char_length(product_id) + 1) = product_id || '|'
        AND char_length(id) BETWEEN char_length(product_id) + 2 AND char_length(product_id) + 5
    )
);

CREATE TABLE IF NOT EXISTS public.kb_offers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id text NOT NULL REFERENCES public.kb_variants (id) ON DELETE CASCADE,
    merchant_id text NOT NULL REFERENCES public.kb_merchants (host) ON DELETE CASCADE,
    amount numeric(14, 3) NOT NULL CHECK (amount > 0),
    observed_currency char(3) NOT NULL CHECK (observed_currency ~ '^[A-Z]{3}$'),
    evidence_rung text NOT NULL CHECK (
        evidence_rung IN ('own_token', 'page_evidence', 'expected_missing', 'platform_api', 'operator')
    ),
    size_ml integer CHECK (size_ml IS NULL OR size_ml BETWEEN 1 AND 9999),
    list_vs_sale text NOT NULL DEFAULT 'unknown' CHECK (list_vs_sale IN ('list', 'sale', 'unknown')),
    in_stock boolean,
    first_seen timestamptz NOT NULL DEFAULT now(),
    last_seen timestamptz NOT NULL DEFAULT now(),
    captured_at timestamptz NOT NULL DEFAULT now(),
    canonical_url text NOT NULL CHECK (
        canonical_url ~ '^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^?#[:space:]]*$'
        AND canonical_url !~ '^https?://([^/]*[.])?(fragrantica|parfumo|basenotes|fimgs)[.]'
    ),
    CONSTRAINT kb_offers_seen_order CHECK (first_seen <= last_seen),
    CONSTRAINT kb_offers_url_on_merchant CHECK (
        split_part(split_part(canonical_url, '://', 2), '/', 1) = merchant_id
        OR right(split_part(split_part(canonical_url, '://', 2), '/', 1), char_length(merchant_id) + 1)
        = '.' || merchant_id
    ),
    CONSTRAINT kb_offers_observation UNIQUE (
        variant_id, merchant_id, canonical_url, amount, observed_currency, list_vs_sale
    )
);

CREATE TABLE IF NOT EXISTS public.kb_images (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE,
    variant_id text REFERENCES public.kb_variants (id) ON DELETE CASCADE,
    url text NOT NULL CHECK (
        url ~ '^https://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^#[:space:]]*$'
        AND url !~ '^https://([^/]*[.])?(fragrantica|parfumo|basenotes|fimgs)[.]'
        AND char_length(url) <= 2048
    ),
    provenance_host text NOT NULL CHECK (
        provenance_host ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'
        AND provenance_host !~ '(^|[.])(fragrantica|parfumo|basenotes|fimgs)[.]'
    ),
    source text NOT NULL CHECK (
        source IN ('retailer_jsonld', 'retailer_og', 'brand_site', 'partner_feed', 'operator')
    ),
    captured_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_images_product_url UNIQUE (product_id, url)
);

CREATE TABLE IF NOT EXISTS public.kb_specs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE,
    field text NOT NULL CHECK (field ~ '^[a-z][a-z0-9_]{0,63}$'),
    value text NOT NULL CHECK (char_length(value) BETWEEN 1 AND 2000),
    source_url text CHECK (
        source_url IS NULL OR (
            source_url ~ '^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^#[:space:]]*$'
            AND source_url !~ '^https?://([^/]*[.])?(fragrantica|parfumo|basenotes|fimgs)[.]'
            AND char_length(source_url) <= 2048
        )
    ),
    extractor text NOT NULL CHECK (char_length(extractor) BETWEEN 1 AND 64),
    model text CHECK (model IS NULL OR char_length(model) BETWEEN 1 AND 64),
    cited boolean NOT NULL DEFAULT false,
    captured_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_specs_cited_has_source CHECK (NOT cited OR source_url IS NOT NULL),
    CONSTRAINT kb_specs_product_field UNIQUE (product_id, field)
);

CREATE TABLE IF NOT EXISTS public.kb_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE,
    source text NOT NULL CHECK (
        source IN ('retailer_jsonld', 'retailer_widget', 'brand_site', 'marketplace')
    ),
    aggregate_rating numeric(3, 2) CHECK (aggregate_rating IS NULL OR aggregate_rating BETWEEN 0 AND 5),
    review_count integer CHECK (review_count IS NULL OR review_count >= 0),
    source_url text NOT NULL CHECK (
        source_url ~ '^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^#[:space:]]*$'
        AND source_url !~ '^https?://([^/]*[.])?(fragrantica|parfumo|basenotes|fimgs)[.]'
        AND char_length(source_url) <= 2048
    ),
    captured_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_reviews_has_signal CHECK (aggregate_rating IS NOT NULL OR review_count IS NOT NULL),
    CONSTRAINT kb_reviews_product_url UNIQUE (product_id, source_url)
);

CREATE TABLE IF NOT EXISTS public.kb_gaps (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_key text NOT NULL CHECK (char_length(product_key) BETWEEN 14 AND 520),
    field text NOT NULL CHECK (field ~ '^[a-z][a-z0-9_]{0,63}$'),
    demand_count integer NOT NULL DEFAULT 1 CHECK (demand_count >= 0),
    first_seen timestamptz NOT NULL DEFAULT now(),
    last_seen timestamptz NOT NULL DEFAULT now(),
    state text NOT NULL DEFAULT 'open' CHECK (
        state IN ('open', 'queued', 'needs_operator', 'licence', 'closed')
    ),
    source_hint text CHECK (
        source_hint IS NULL OR (
            char_length(source_hint) BETWEEN 1 AND 256
            AND source_hint !~* '(fragrantica|parfumo|basenotes|fimgs)'
        )
    ),
    CONSTRAINT kb_gaps_seen_order CHECK (first_seen <= last_seen),
    CONSTRAINT kb_gaps_key_field UNIQUE (product_key, field)
);

CREATE TABLE IF NOT EXISTS public.kb_feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    compare_request_id uuid NOT NULL,
    product_id text REFERENCES public.kb_products (id) ON DELETE CASCADE,
    field text NOT NULL CHECK (field ~ '^[a-z][a-z0-9_]{0,63}$'),
    verdict text NOT NULL CHECK (verdict IN ('correct', 'wrong', 'unsure')),
    device_key text NOT NULL CHECK (device_key ~ '^[a-f0-9]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.kb_coverage_daily (
    day date NOT NULL,
    metric text NOT NULL CHECK (metric ~ '^[a-z][a-z0-9_.:-]{0,127}$'),
    value numeric NOT NULL,
    n integer NOT NULL CHECK (n >= 0),
    PRIMARY KEY (day, metric)
);

CREATE INDEX IF NOT EXISTS idx_kb_merchants_status ON public.kb_merchants (status);
CREATE INDEX IF NOT EXISTS idx_kb_variants_product ON public.kb_variants (product_id);
CREATE INDEX IF NOT EXISTS idx_kb_variants_gtin ON public.kb_variants (gtin) WHERE gtin IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kb_offers_latest
    ON public.kb_offers (variant_id, merchant_id, captured_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_kb_offers_merchant ON public.kb_offers (merchant_id);
CREATE INDEX IF NOT EXISTS idx_kb_images_product ON public.kb_images (product_id);
CREATE INDEX IF NOT EXISTS idx_kb_images_variant ON public.kb_images (variant_id) WHERE variant_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kb_reviews_product ON public.kb_reviews (product_id);
CREATE INDEX IF NOT EXISTS idx_kb_gaps_open_demand
    ON public.kb_gaps (demand_count DESC, last_seen DESC) WHERE state = 'open';
CREATE INDEX IF NOT EXISTS idx_kb_feedback_device_key ON public.kb_feedback (device_key);
CREATE INDEX IF NOT EXISTS idx_kb_feedback_product ON public.kb_feedback (product_id) WHERE product_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_kb_feedback_one_vote
    ON public.kb_feedback (device_key, compare_request_id, field, coalesce(product_id, ''));

CREATE OR REPLACE VIEW public.kb_offers_latest
WITH (security_invoker = true) AS
SELECT DISTINCT ON (o.variant_id, o.merchant_id)
    o.id,
    o.variant_id,
    o.merchant_id,
    o.amount,
    o.observed_currency,
    o.evidence_rung,
    o.size_ml,
    o.list_vs_sale,
    o.in_stock,
    o.first_seen,
    o.last_seen,
    o.captured_at,
    o.canonical_url
FROM public.kb_offers AS o
ORDER BY o.variant_id ASC, o.merchant_id ASC, o.captured_at DESC, o.id DESC;

CREATE OR REPLACE FUNCTION public.kb_prune_offers(p_max_age_days integer, p_keep_per_merchant integer)
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO 'public'
AS $$
DECLARE
  v_deleted integer;
BEGIN
  IF p_max_age_days IS NULL OR p_max_age_days < 1 OR p_max_age_days > 3650
     OR p_keep_per_merchant IS NULL OR p_keep_per_merchant < 1 OR p_keep_per_merchant > 1000 THEN
    RAISE EXCEPTION 'kb_prune_offers: bounds out of range';
  END IF;
  WITH ranked AS (
    SELECT
      o.id,
      o.captured_at,
      row_number() OVER (
        PARTITION BY o.variant_id, o.merchant_id
        ORDER BY o.captured_at DESC, o.id DESC
      ) AS rn
    FROM public.kb_offers AS o
  )
  DELETE FROM public.kb_offers AS d
  USING ranked AS r
  WHERE d.id = r.id
    AND r.rn > p_keep_per_merchant
    AND r.captured_at < now() - make_interval(days => p_max_age_days);
  GET DIAGNOSTICS v_deleted = ROW_COUNT;
  RETURN v_deleted;
END
$$;

CREATE OR REPLACE FUNCTION public.kb_product_card(p_product_id text)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path TO 'public'
AS $$
  SELECT jsonb_build_object(
    'product', to_jsonb(p.*),
    'variants', coalesce((
      SELECT jsonb_agg(to_jsonb(v.*) ORDER BY v.id)
      FROM public.kb_variants AS v
      WHERE v.product_id = p.id
    ), '[]'::jsonb),
    'offers', coalesce((
      SELECT jsonb_agg(to_jsonb(l.*) ORDER BY l.variant_id, l.merchant_id)
      FROM public.kb_offers_latest AS l
      INNER JOIN public.kb_variants AS v2 ON l.variant_id = v2.id
      WHERE v2.product_id = p.id
    ), '[]'::jsonb),
    'images', coalesce((
      SELECT jsonb_agg(to_jsonb(i.*) ORDER BY i.captured_at DESC, i.id)
      FROM public.kb_images AS i
      WHERE i.product_id = p.id
    ), '[]'::jsonb),
    'specs', coalesce((
      SELECT jsonb_agg(to_jsonb(s.*) ORDER BY s.field)
      FROM public.kb_specs AS s
      WHERE s.product_id = p.id AND s.cited
    ), '[]'::jsonb),
    'rating', (
      SELECT jsonb_build_object(
        'sources', count(*),
        'review_count', sum(r.review_count),
        'rating', round(
          sum(r.aggregate_rating * r.review_count)
          FILTER (WHERE r.aggregate_rating IS NOT NULL AND r.review_count IS NOT NULL)
          / nullif(sum(r.review_count)
            FILTER (WHERE r.aggregate_rating IS NOT NULL AND r.review_count IS NOT NULL), 0),
          2
        )
      )
      FROM public.kb_reviews AS r
      WHERE r.product_id = p.id
    )
  )
  FROM public.kb_products AS p
  WHERE p.id = p_product_id
$$;

ALTER TABLE public.kb_merchants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_specs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_gaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_coverage_daily ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.kb_merchants FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_products FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_variants FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_offers FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_images FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_specs FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_reviews FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_gaps FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_feedback FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_coverage_daily FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_offers_latest FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_merchants TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_products TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_variants TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_offers TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_images TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_specs TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_reviews TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_gaps TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_feedback TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_coverage_daily TO service_role;
GRANT SELECT ON TABLE public.kb_offers_latest TO service_role;

REVOKE ALL ON FUNCTION public.kb_gtin_check_digit_ok(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.kb_prune_offers(integer, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.kb_product_card(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.kb_gtin_check_digit_ok(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.kb_prune_offers(integer, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.kb_product_card(text) TO service_role;

COMMIT;
```

### A.2 migrations/047_012_revoke.sql (prototype sha256 abb6597efdc231473109d30798890ff7f99e4cc3a685ebaa99f1d603ed97ddb1, 2894 LF bytes)

```sql
-- Migration 047: close the anon / authenticated access migration 012 opened on
-- product_specs, product_prices and product_reviews (S81-14 KB-SCHEMA, S81)
--
-- 012 created eight policies with no TO clause, so they apply to every role
-- (PUBLIC): specs_select / specs_insert / specs_update (USING / WITH CHECK
-- true), prices_select / prices_insert, reviews_select / reviews_insert /
-- reviews_update. With the stock Supabase table grants that lets the public
-- anon key read, insert and update the L2 cache (a poisoning path; M18
-- CD-db-rls-03, PLAN_S81 A2). This file drops the eight policies BY NAME and
-- revokes every table privilege from PUBLIC, anon and authenticated; it
-- re-grants service_role explicitly (the migrations/037 both-readings rule).
--
-- APP CODE IS UNAFFECTED: every reader and writer of the three tables uses the
-- service-role client (app/services/product_data_service.py get_cached_* /
-- save_*, app/api/text_routes.py the cache flush DELETE,
-- app/services/reengagement_service.py, scripts/shadow_experiments.py).
--
-- APPLY ORDER: after the owner's live pg_policies read (APPLY_047_1_PRECHECK
-- .sql). If that read lists a policy on these tables beyond the eight names
-- below, the REVOKE still removes the table privilege from anon and
-- authenticated (a policy cannot grant a privilege), and the extra policy is
-- dropped by name in a follow-up migration. No ordering against 045.
--
-- Owner postcheck (APPLY_047_3_POSTCHECK.sql): no policy left on the three
-- tables; has_table_privilege anon / authenticated INSERT, UPDATE, DELETE and
-- SELECT false; service_role SELECT, INSERT, UPDATE, DELETE true.
--
-- Rollback: migrations/rollback/047_012_revoke.sql

BEGIN;

DROP POLICY IF EXISTS specs_select ON public.product_specs;
DROP POLICY IF EXISTS specs_insert ON public.product_specs;
DROP POLICY IF EXISTS specs_update ON public.product_specs;
DROP POLICY IF EXISTS prices_select ON public.product_prices;
DROP POLICY IF EXISTS prices_insert ON public.product_prices;
DROP POLICY IF EXISTS reviews_select ON public.product_reviews;
DROP POLICY IF EXISTS reviews_insert ON public.product_reviews;
DROP POLICY IF EXISTS reviews_update ON public.product_reviews;

ALTER TABLE public.product_specs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_reviews ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.product_specs FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.product_prices FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.product_reviews FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.product_specs TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.product_prices TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.product_reviews TO service_role;

COMMIT;
```
