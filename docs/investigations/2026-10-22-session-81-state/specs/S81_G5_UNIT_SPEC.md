# S81-G5 LEARN-SEARCH: group unit spec (D22 NIGHTLY-LEARNING alone)

- Group: S81-G5 LEARN-SEARCH (the fifth SAFE group under LC-9); this spec carries ONE unit, D22 NIGHTLY-LEARNING. S81-21 WEB-SEARCH-CAPPED joins a later group spec once S81-07 lands (owner-blocked: the Anthropic test key).
- Flag: `ENABLE_LEARNING_JOB` (NEW name, default OFF, the G2 mode idiom through `scripts/kb_seed_common.run_mode`).
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-g5 (detached at base). Branch to cut: `feature/s81-g5-learn-search`.
- Base sha: ec747b496953869c0370e4f28bf025c6f694a97d (origin/main after #386). `git status --short` was EMPTY before and after every probe of this spec (only this gitignored file exists under `.qa-s80/`).
- Evidence pointers: group brief `specs/S81_G5_BRIEF.md`; PLAN_S81 :170 (D22 text, binding as re-cut by the brief); PLAN_S80 section 0 + `runs/research/contract_freeze.json` (re-read: D22 touches no response path, no client-read key, no envelope); `scripts/s81-common.txt` LC-1..LC-9; ledger tail (newest line 2026-11-05 02:49 S84 STARTED).
- Measurement location: <scratchpad>/g5spec/ (base1.log, base2.log). Every file:line below was read at ec747b49 in this run.
- Personal-data rule: no personal value anywhere; every id, key, email shape or phone shape a RED row needs is built at run time from synthetic parts (`"u" + "-0001"`, `"a" * 64`, `"x" + "@" + "example.invalid"`, `"+97" + "3"`).

---

## 0. THE GROUP

### 0.1 The one branch, the unit, the flag

| Item | Value |
|---|---|
| Branch | `feature/s81-g5-learn-search` from ec747b49 |
| Units | D22 NIGHTLY-LEARNING (lane data) |
| Flags | `ENABLE_LEARNING_JOB` (mode: unset / blank / garbage / false / 0 / no / off = OFF; true / 1 / yes / on = DRY; the exact word `apply` (strip + lower) = WRITE) |
| Knobs | `LEARNING_WINDOW_DAYS` (7, 1..30), `LEARNING_MIN_CASES` (3, 1..100), `LEARNING_MIN_DEVICES` (2, 1..10), `LEARNING_MAX_ROWS` (5000, 100..50000, per table), `LEARNING_EXEMPLARS_PER_CATEGORY` (5, 3..5); every one through `kb_seed_common.int_knob` read per call (unset / blank / garbage / inf / nan / negative / 0 -> default; else clamped) |
| New credential names | none (the service-role names already exist: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) |
| Migration | none (053 would make the unit FOCUS; the proposals / exemplar tables are D22b) |
| app/ files | none (the plan's two app/ items are withdrawn into D22c, section 10) |

### 0.2 Change list (the whole group = D22's)

1. NEW `scripts/cron_learning.py` (the job).
2. NEW `railway.learning.json` (the service config, the kbcoverage pattern).
3. NEW `tests/test_s81_d22_nightly_learning.py` (the RED file; RED writes it, GREEN never edits a frozen row).
4. EDIT `tests/test_s81_kb_schema.py` (E1: two `P02_ALLOWED` rows for the new kb_* relation literals of `scripts/cron_learning.py`).
5. DELETE `scripts/cron_few_shot_rotation.py` (E2, the brief's rule (g) option (i)).
6. DELETE `tests/test_cron_few_shot_rotation.py` (E3, the test file of the deleted script).
7. EDIT `tests/test_exemplar_contamination.py` docstring lines 19-20 and 159-161 only (E4, the stale rotation-cron sentences; no assertion moves). Optional: the orchestrator may rule E4 out (section 11 Q3).
8. EDIT `CLAUDE.md`: one new `**SESSION 81 flags (S81-G5 LEARN-SEARCH ...)**` block after the S81-G4 owner-steps bullet (`CLAUDE.md:565`) and one clause in the Feature Flags pointer line (`CLAUDE.md:341`, after the S81-G4 clause).

No other file.

### 0.3 Files shared between units / the order GREEN applies them

One unit only, so no file is shared between units of this group. Files shared with earlier merged units (the order GREEN edits them): (1) the two NEW files (cron_learning.py, railway.learning.json); (2) the deletions E2 / E3; (3) `tests/test_s81_kb_schema.py` E1 (the S81-G2 / G4 row form, appended after the `scripts/cron_kb_coverage.py` rows at :355-356); (4) `tests/test_exemplar_contamination.py` E4; (5) CLAUDE.md last (block + pointer clause). `scripts/kb_seed_common.py` and `scripts/cron_kb_coverage.py` are READ, never edited (D17b owns the `_paged` ORDER BY fix).

### 0.4 DEFECT_LEDGER row (draft, the ledger's column form, names only)

| D22 | NIGHTLY-LEARNING (G5 LEARN-SEARCH, SAFE): scripts/cron_learning.py + railway.learning.json: a nightly DB-only job over the window of comparison_feedback / comparisons / user_events / search_logs / verdict_critiques / kb_gaps / kb_feedback (kb_* absent before 045 = a counted skip): the six failure buckets, the category x source x field clusters, the systematic rule (>= LEARNING_MIN_CASES cases from >= LEARNING_MIN_DEVICES distinct users / devices, user_id a named PROXY), KB correction proposals (judge_state pending, never applied), exemplar candidate sets and candidate eval cases in a de-identified report, learning.* rows in kb_coverage_daily through build_coverage_row (apply only); cron_few_shot_rotation retired (E2 / E3) | ENABLE_LEARNING_JOB | tests/test_s81_d22_nightly_learning.py (counts at the RED gate) | feature/s81-g5-learn-search | SPEC |

---

## Unit D22

### 1. BASE STATE (measured at ec747b49)

#### 1.1 The shared contracts D22 reuses (scripts/kb_seed_common.py, CRLF working copy, ASCII)

| file:line | what | D22 use |
|---|---|---|
| kb_seed_common.py:1-22 | module docstring: stdlib-only at module top, every app import lazy | cron_learning follows it (module top: stdlib + `import scripts.kb_seed_common as common`) |
| :39-42 | `MODE_OFF / MODE_DRY / MODE_APPLY`, `_TRUTHY` | the mode values |
| :45-46 | `PAGE_SIZE = 500`, `MAX_PAGES = 200` | the page size of every D22 read |
| :54 / :53 | `KB_GAPS_TABLE = "kb_gaps"`, `KB_SPECS_TABLE = "kb_specs"` | referenced as `common.KB_GAPS_TABLE` / `common.KB_SPECS_TABLE` (no new literal) |
| :68-80 | `run_mode(flag_name)`: first statement `os.getenv(flag_name, "false").strip().lower()`; `apply` -> apply, truthy -> dry, else off | `learning_mode()` = `common.run_mode(FLAG)` |
| :83-85 | `cli_mode(mode, dry_run)`: `--dry-run` downgrades apply | reused |
| :93-118 | `_knob_value` (finite, >= 0 else None) / `int_knob(name, default, low, high)` (unusable or 0 with low > 0 -> default; else clamp) | every D22 knob |
| :133-136 | `_admin_client()` lazy `database_service.get_admin_supabase_client()` | the client seam (monkeypatched in tests) |
| :139-140 | `_now()` UTC | the clock seam |
| :143-145 | `kb_leaf()` lazy `from app.services import kb_service as _kb` (the P01-allowed importer) | `build_coverage_row` and `KB_METRIC_REGEX` through it (D22 never names kb_service) |
| :148-155 | `bump`, `log_counts` | reused for the table counters |
| :158-163 | `write_report(path, report)`: ASCII JSON, LF, `indent=1`, `sort_keys=True`; no-op without a path | the --report JSON |
| :166-176 | `resolve_client` logs WARNING and returns None (D17 then exits 0) | NOT reused: the brief's failure table wants exit 1 after one ERROR line (2.6) |
| :361-462 | `KbWriter` (products / variants / specs / offers / gaps / brands / ledger; no coverage method) | NOT used: the coverage write follows D17's own path (1.2) |

Flag-reader idiom measured: `run_mode` is the house idiom with the extra `apply` word; it reads the env per call, never memoised.

#### 1.2 The D17 template (scripts/cron_kb_coverage.py, CRLF working copy, 374 lines)

| file:line | what |
|---|---|
| :31-36 | `PREFIX = "[KB_COVERAGE]"`, `FLAG`, `KB_COVERAGE_TABLE = "kb_coverage_daily"` (P02 row), `KB_OFFERS_LATEST_VIEW`, `SEARCH_LOGS_TABLE = "search_logs"`, `SEARCH_LOG_COLUMNS = "products_found,success,is_synthetic,created_at"` |
| :49-51 | `coverage_mode()` = `common.run_mode(FLAG)` |
| :96-111 | `_paged(client, table, columns, filters)`: `client.table(t).select(cols)` + filters + `.range(start, start+PAGE_SIZE-1).execute()`; a non-list page raises TypeError; NO `.order()` (the D17b lesson: D22 orders every read) |
| :129-135 | `_Rollup.guarded`: one WARNING `family=<label> read failed (<Type>)`, the family omitted |
| :238-239 | the search_logs read with `gte` / `lt` on `created_at` |
| :301-309 | `_write_report`: markdown, ASCII, LF |
| :321-325 | `main(argv=None, client=None, redis=None)`: `mode = coverage_mode()` FIRST; OFF = one INFO line `mode=off <FLAG> not set; skipping run`, return 0 before argparse |
| :333-337 | bad `--day` -> WARNING, return 0 |
| :346-358 | `kb = common.kb_leaf()`; one `[KB_COVERAGE] metric=... value=... n=...` INFO line per metric; `kb.build_coverage_row(day=day, metric=name, value=value, n=n)`; a None row counted `not_built` |
| :360-364 | APPLY only: `client.table(KB_COVERAGE_TABLE).upsert(rows, on_conflict="day,metric").execute()`; a raise = one WARNING, exit 0 |
| :365-367 | the totals line; return 0 |

`railway.kbcoverage.json` (14 lines, LF, ASCII): `build.watchPatterns` = [`scripts/cron_kb_coverage.py`, `scripts/kb_seed_common.py`, `railway.kbcoverage.json`]; `deploy.startCommand` = `python -m scripts.cron_kb_coverage`; `deploy.restartPolicyType` = `NEVER`; no cronSchedule (the schedule is set in the dashboard).

Q3 answer: D22 reuses D17's EXACT write call shape (`client.table(<kb_coverage_daily>).upsert(rows, on_conflict="day,metric").execute()`, rows from `kb.build_coverage_row`). `cron_kb_coverage.py` sits in P02_ALLOWED (two rows, tests/test_s81_kb_schema.py:355-356) and NOT in P01 (it imports the leaf only through `common.kb_leaf()`), which proves the row form D22 needs: P02 rows only.

#### 1.3 The KB leaf and the 045 tables

| file:line | what |
|---|---|
| app/services/kb_service.py:53 | `KB_CATEGORY = "fragrances"` |
| :55-59 | `KB_TABLES` incl. `kb_gaps`, `kb_feedback`, `kb_coverage_daily` |
| :89-97 | `KB_COLUMNS["kb_gaps"] = (id, product_key, field, demand_count, first_seen, last_seen, state, source_hint)`; `["kb_feedback"] = (id, compare_request_id, product_id, field, verdict, device_key, created_at)`; `["kb_coverage_daily"] = (day, metric, value, n)` |
| :132 | `KB_METRIC_REGEX = "^[a-z][a-z0-9_.:-]{0,127}$"` |
| :794-813 | `build_coverage_row(*, day, metric, value, n)`: `day` a `date` (not datetime), metric matches the regex, value int / float / Decimal finite (not bool), `n` int 0..INT4_MAX; returns `{"day": str(day), "metric", "value": str(Decimal), "n"}` or None; never raises |
| migrations/045_kb_core.sql:273-300 | `kb_gaps` (no created_at; `last_seen` timestamptz; `field ~ '^[a-z][a-z0-9_]{0,63}$'`; state in open / queued / needs_operator / licence / closed; UNIQUE (product_key, field)) |
| :301-309 | `kb_feedback` (compare_request_id uuid NOT NULL, product_id text FK kb_products, field regex, verdict correct / wrong / unsure, `device_key ~ '^[a-f0-9]{64}$'`, created_at) |
| :311-317 | `kb_coverage_daily` (day, metric CHECK = the regex, value numeric, n integer >= 0, PRIMARY KEY (day, metric)) |

045 / 047 / 050 / 052 are WRITTEN NOT APPLIED (ledger 2026-11-05 01:14). Measured: NO writer of kb_feedback exists anywhere in app/ or scripts/ (`build_feedback_row` :765 has no caller; grep of `build_feedback_row|"kb_feedback"` outside the leaf = none). So after 045 the kb_feedback input is still empty until a writer lands (stated limit L5).

#### 1.4 The signal tables (Q1: columns, join keys, writers, RLS)

| table | DDL / writer evidence | columns D22 selects | actor | join key |
|---|---|---|---|---|
| comparison_feedback | created outside migrations/ (dashboard); 027:27-34 adds winner_correct / price_correct / specs_correct with CHECK in correct / wrong / unsure (:45-60); writer `feedback_service.save_feedback` :197-251: record keys useful, mattered_most, user_id (when authed), comparison_id, change_suggestion, the three 027 columns (:226-245), insert :247 returns `data[0]["id"]` (an `id` exists); RLS 010:11 + :46-50 | `id,user_id,comparison_id,useful,winner_correct,price_correct,specs_correct,created_at` (NEVER change_suggestion, mattered_most) | user_id (PROXY; null for anonymous feedback) | comparison_id -> comparisons.id |
| comparisons | 001 (full_response jsonb, product_names text[]), 020 (schema_version); writer `database_service.save_comparison` :413, record :459-468 = full_response, query, input_type, product_names (`p["name"]` of the first two overview products, :452-457), schema_version 2, user_id when known. MEASURED: there is NO `category_used` COLUMN (no migration adds one; the writer never sets one); the category lives at `full_response.category_used` (response_builder.py:2286 `result["category_used"] = category_used`) | `id,user_id,product_names` + PostgREST JSON paths (2.3): `category:full_response->>category_used`, `wi:full_response->>winner_index`, the per-product price method / currency / amount, the verdict fields (NEVER `query`, NEVER bare `full_response`) | user_id | id |
| user_events | created outside migrations/; writers `feedback_service.track_event` :254-286 and `track_events_batch` :289-319: event_type, event_data jsonb, user_id, comparison_id, session_id (so user_events DOES carry comparison_id; 013:56 joins on it); event types = `feedback_routes.VALID_EVENT_TYPES` :60-92; RLS 010:12 + 041 | `id,user_id,event_type,comparison_id,created_at` with `in_("event_type", EVENT_TYPES)` (NEVER event_data) | user_id | comparison_id |
| search_logs | 002:5-16 (id, user_id, query, input_type, products_found, success, error_message, cost, duration_ms, created_at) + 042:133 is_synthetic; writer `database_service.log_search` :753-797 | `id,user_id,success,is_synthetic,created_at` (NEVER query, error_message, products_found) | user_id | none (no comparison id) |
| verdict_critiques | 030:40-75 (id, comparison_id FK, bias / vagueness / hedging / missing_citation / pain_workflow_align scores 0..10 nullable, regenerated, regen_reason, critic_model, critic_tokens_used, created_at); writer `feedback_service._persist_verdict_critique` :166 | `id,comparison_id,bias_score,missing_citation_score,created_at` | via comparisons.user_id | comparison_id |
| kb_gaps | 045:273-300 (1.3) | `id,field,state,demand_count,last_seen` (window on last_seen) | none | none |
| kb_feedback | 045:301-309 (1.3) | `id,compare_request_id,product_id,field,verdict,device_key,created_at` | device_key (a real device) | product_id -> kb_specs.product_id |
| kb_specs (grounding only) | 045 (`KB_COLUMNS["kb_specs"]` = id, product_id, field, lang, value, source_url, extractor, model, cited, captured_at) | `product_id,field,source_url,cited` with `in_("product_id", chunk)` | n/a | product_id |

user_events failure / confirmation types (from VALID_EVENT_TYPES :60-92): ABANDON = (`result_abandon`, `compare_cancelled`, `scan_failed`); CONFIRM = (`save`, `share_completed`, `screenshot`). No user_events type names a FIELD, so user_events feeds context metrics only, never a bucket (2.4).

#### 1.5 Q2: the per-product source keys inside comparisons.full_response

- `feedback_service._without_verdict_critique` :27-52 strips ONLY `metadata._verdict_critique`; prices, category and verdict text survive into the stored row.
- `full_response.overview.products[i].price` = `price_service.public_price_view(pd["price"])` (response_builder.py:1938; public_price_view strips `_*` keys and `guard_rejected`): carries `source_method` (the CLAUDE.md enum `local_bhd | converted_usd | page_scrape | page_scrape_rendered | firecrawl | scrapedo_rendered | estimated`), `amount`, `currency`, `retailer`, `url`.
- `full_response.specs.products[i].specs` (response_builder.py:1986-1994) carries NO per-field source host: the specs source axis is the constant `specs` (stated limit L6).
- Verdict text: `full_response.comparison` (the BC alias the rotation reads: cron_few_shot_rotation.py:155-196 reads `winner_index`, `winner_reason`, `key_tradeoff`, `value_context.product_0/1`); the deterministic shipped winner is top-level `full_response.winner_index` (response_builder.py:2285).

#### 1.6 Q4: the judge, ENABLE_SELF_CRITIQUE and verdict_critiques

- compare_judgements (S81-22) does not exist at ec747b49 (no migration, no module).
- `ENABLE_SELF_CRITIQUE`: CLAUDE.md:341 lists it `(OFF - verdict self-critique pass)`; NO dated ledger line names it (grep of the S81 ledger and PLAN_S80: none). Per R-A15 it is OFF-by-default and UNKNOWN in production; D22 is designed for both states: verdict_critiques is OPTIONAL input (zero rows = verdict_unsupported 0).
- Axis semantics: `verdict_critique_service.CRITIQUE_AXES` :46-52, `CRITIQUE_THRESHOLD = 7` :56 ("10 = best"; any axis strictly below 7 flags regen). D22 maps verdict_unsupported = `missing_citation_score < 7 OR bias_score < 7` (a null score never counts), mirroring the constant as `CRITIQUE_THRESHOLD = 7` in cron_learning (no import of verdict_critique_service, which imports openai_service at module top :40); a PIN row pins the equality.

#### 1.7 Q5: scripts/cron_few_shot_rotation.py (434 lines)

- Read-merge-write of `data/verdict_exemplars.json` (:7, :64 `_EXEMPLAR_FILE`, `_write_exemplar_file` :329, `tmp.write_text` :366); gate `ENABLE_FEWSHOT_ROTATION` fail-closed (:86); never registered on Railway (:38-46; no railway*.json names it: measured); its exemplars carry `_provenance.source_pattern_id = comparison_id` (:201-216) = a uuid INTO a committed data/ file (the privacy shape D22's report refuses).
- Importers: ONLY `tests/test_cron_few_shot_rotation.py:27` (12 tests). `tests/test_exemplar_contamination.py` names it in docstrings only (:19-20, :159-161). No .github, Procfile, railway or pyproject reference.
- `ENABLE_FEWSHOT_ROTATION` is ALSO one of the legal fill-in flags: `scripts/fill_in_legal.py:70-80` (SEVEN_FLAGS), `tests/test_legal_docs_u8.py:57` and :232-242, `tests/fixtures/legal_fill_in_u8.json:20` (`"off"`). These are the U8 legal machinery: D22 does NOT touch them (a FOCUS surface); the recorded `"off"` stays true after the deletion.
- data/verdict_exemplars.json: `exemplars[]` EMPTY in all 9 categories (measured; pinned by `tests/test_exemplar_contamination.py::test_canonical_exemplars_are_empty` :104); loaded by `app/services/verdict_exemplar_loader.py:35`, injected at `app/services/extraction_service.py:2213-2218` (`build_exemplar_block(category)`). The parked file `data/verdict_exemplars.s3_parked.json`: 26 exemplars, every `_provenance.synthetic is True`, no uuid-shaped source_pattern_id (measured).
- Ruling proposed: option (i) DELETE the script and its test file (E2 / E3): nothing else imports it, the flag is unset and the service never existed, so production is byte-identical; it removes the only code path that writes user-derived exemplars under data/. The refusal is then two PIN/RED rows (5: R26 RED, P1 PIN).

#### 1.8 Q6: scripts/shadow_experiments.py + scripts/dump_l2_for_shadow.sql

- Contract (:1-57): `prepare` reconstructs verdict inputs for GOLD queries from the L2 `product_*` tables (DB reads only, $0, offline-testable; `SHADOW_L2_DUMP` file input :687), computes scores offline; `run --arm ...` calls OpenAI per arm (metered cost, live_unit); `dump` is a DB read (:1535-1540); grading imports eval_runner.
- There is NO frozen-input PAIRWISE replay and the only replay (`run`) is an LLM call, so no $0 DB-only replay exists. The replay does NOT ship in G5: a proposal batch would be replayed in D22b as `prepare` over the affected gold ids + a judge arm (stated limit L8).

#### 1.9 Pins and readers D22 must respect (measured)

| file:line | rule D22's new script must satisfy |
|---|---|
| tests/test_s81_kb_schema.py:331-357 | `P01_ALLOWED` / `P01_FUNCTIONS` / `P02_ALLOWED`: D22 needs no P01 row (it never names kb_service) and TWO P02 rows (E1) |
| :366-397 | P01: no Constant containing `kb_service` with `app.` or `/` in app/ or scripts/ |
| :400-414 | P02: no string Constant EQUAL to a kb_* relation name (incl. `kb_offers_latest`, :66) outside P02_ALLOWED -> every kb table name in cron_learning lives in ONE constant assignment; never a dict key or select literal equal to a relation name |
| :516 | `test_s14_r01_files_exist_once`: the migration census, UNCHANGED (no migration) |
| tests/test_s81_s05_request_context.py:1355-1370, :1635-1641 | scripts/ text must not contain `request_context`, `device_key_pepper`, `x-ai-consent-version`, `x-compare-request-id`, `header_state`, `legacy_hash`, `device_lookup_keys` (the column `compare_request_id` does not match `x-compare-request-id`) |
| tests/test_s81_s08b_legacy_fingerprint.py:1198 | the same two banned names over app/ + scripts/ |
| tests/test_legal_s78.py:329 | no `@gmail.com` string constant in app/ + scripts/ |
| tests/test_legal_disclosure_s77.py:725 | no `QarenBot` / `NAMED_AGENT` in a new scripts/ file |
| tests/test_retro_w1_2b.py:349 | no `cleanup_expired_ratings` caller |
| tests/test_u3c_store_false_pin.py:27, :467 | the scripts/ OpenAI-call scan (D22 makes no LLM call) |
| tests/test_s81_s16b_kb_brands.py:943-949 | every railway*.json: startCommand never names `seed_kb_brands_wikidata` |

#### 1.10 Base pass state through the bounded runner (worktree sc-s81-g5 at ec747b49)

```
[pyt] tag=g5spec-base1 start=2026-11-05 03:06:45 end=2026-11-05 03:06:58 elapsed=13s bound=600s status=FAIL rc=1
  tests/test_cron_few_shot_rotation.py tests/test_exemplar_contamination.py tests/test_s81_d17_coverage.py
  tests/test_s81_kb_schema.py tests/test_s81_g4_gate_rows.py tests/test_legal_s78.py
  1 failed, 604 passed; [hermeticity] sentinel checked 605 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
  FAILED tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene  (the KNOWN baseline: the CRLF working
  copy of scripts/cron_kb_coverage.py under core.autocrlf=true; the stored e1491c97 record lists it, D2 of that round)
[pyt] tag=g5spec-base2 start=2026-11-05 03:07:22 end=2026-11-05 03:07:41 elapsed=20s bound=600s status=OK rc=0
  tests/test_s81_s16b_kb_brands.py tests/test_s81_s05_request_context.py tests/test_s81_s08b_legacy_fingerprint.py
  tests/test_u3c_store_false_pin.py tests/test_retro_w1_2b.py tests/test_legal_disclosure_s77.py
  tests/test_exemplar_injection_content.py tests/test_verdict_exemplar_loader.py tests/test_shadow_experiments.py
  574 passed, 1 skipped; [hermeticity] sentinel checked 575 test(s); [netguard] blocked 1 attempt(s) from 1 node(s)
  [netguard]   tests/test_exemplar_injection_content.py::test_per_category_token_budget_held [egress] socket.getaddrinfo
  openaipublic.blob.core.windows.net:443  (tiktoken cold cache; the test still passed: record identically at head)
```

Lesson carried into section 5: a hygiene row on a CRLF working copy fails on this box, so every D22 hygiene row normalises `\r\n` to `\n` before asserting "no `\r`" (the git blob is LF).

Libraries on the pinned venv (.venv-qaren): supabase 2.31.0, postgrest 2.31.0 (requirements.txt:115, :171). Measured signatures of `SyncSelectRequestBuilder`: `order(column, *, desc=False, nullsfirst=None, foreign_table=None)`, `range(start, end, foreign_table=None)`, `gte(column, value)`, `lt(column, value)`, `in_(column, values)`, `limit(size, *, foreign_table=None)`, `eq(column, value)`. `postgrest.exceptions.APIError(error: dict)` exposes `.code` (measured: `APIError({"code": "PGRST205", ...}).code == "PGRST205"`; PGRST205 = relation not in the schema cache, 42P01 = undefined table).

Line endings: every backend file read is a CRLF working copy (core.autocrlf=true; `file` reports CRLF), the index LF; railway.kbcoverage.json is LF.

### 2. CONTRACT

#### 2.1 Flag and knobs (read per call, never memoised, never at import)

| name | reader | default / range | notes |
|---|---|---|---|
| `ENABLE_LEARNING_JOB` | `learning_mode()` = `common.run_mode(FLAG)` as the FIRST statement of `main` | OFF | OFF -> one INFO line, return 0, before argparse, before any client, before `kb_leaf()` |
| `LEARNING_WINDOW_DAYS` | `window_days()` = `common.int_knob(..., 7, 1, 30)` | 7 | the window length |
| `LEARNING_MIN_CASES` | `min_cases()` = `int_knob(..., 3, 1, 100)` | 3 | systematic threshold |
| `LEARNING_MIN_DEVICES` | `min_devices()` = `int_knob(..., 2, 1, 10)` | 2 | distinct actors threshold |
| `LEARNING_MAX_ROWS` | `max_rows()` = `int_knob(..., 5000, 100, 50000)` | 5000 | per-table read cap |
| `LEARNING_EXEMPLARS_PER_CATEGORY` | `exemplars_per_category()` = `int_knob(..., 5, 3, 5)` | 5 | 1 or 2 clamp to 3; 9 clamps to 5 |

#### 2.2 Module constants (new keys; names fixed so the RED rows can read them)

```
PREFIX = "[LEARNING]"
FLAG = "ENABLE_LEARNING_JOB"
REPORT_SCHEMA = "learning-report/1"
KB_COVERAGE_TABLE = "kb_coverage_daily"            # E1 P02 row
KB_FEEDBACK_TABLE = "kb_feedback"                  # E1 P02 row
COMPARISON_FEEDBACK_TABLE = "comparison_feedback"
COMPARISONS_TABLE = "comparisons"
USER_EVENTS_TABLE = "user_events"
SEARCH_LOGS_TABLE = "search_logs"
VERDICT_CRITIQUES_TABLE = "verdict_critiques"
READ_TABLES = (COMPARISON_FEEDBACK_TABLE, COMPARISONS_TABLE, USER_EVENTS_TABLE, SEARCH_LOGS_TABLE,
               VERDICT_CRITIQUES_TABLE, common.KB_GAPS_TABLE, KB_FEEDBACK_TABLE, common.KB_SPECS_TABLE)
FEEDBACK_COLUMNS = "id,user_id,comparison_id,useful,winner_correct,price_correct,specs_correct,created_at"
COMPARISON_COLUMNS = ("id,user_id,product_names,category:full_response->>category_used,"
                      "wi:full_response->>winner_index,"
                      "m0:full_response->overview->products->0->price->>source_method,"
                      "m1:full_response->overview->products->1->price->>source_method,"
                      "a0:full_response->overview->products->0->price->>amount,"
                      "a1:full_response->overview->products->1->price->>amount,"
                      "c0:full_response->overview->products->0->price->>currency,"
                      "c1:full_response->overview->products->1->price->>currency,"
                      "cwi:full_response->comparison->>winner_index,"
                      "wr:full_response->comparison->>winner_reason,"
                      "kt:full_response->comparison->>key_tradeoff,"
                      "vc:full_response->comparison->value_context")
EVENT_COLUMNS = "id,user_id,event_type,comparison_id,created_at"
SEARCH_COLUMNS = "id,user_id,success,is_synthetic,created_at"
CRITIQUE_COLUMNS = "id,comparison_id,bias_score,missing_citation_score,created_at"
GAP_COLUMNS = "id,field,state,demand_count,last_seen"
KB_FEEDBACK_COLUMNS = "id,compare_request_id,product_id,field,verdict,device_key,created_at"
SPEC_COLUMNS = "product_id,field,source_url,cited"
BUCKETS = ("identity_wrong", "price_wrong", "spec_missing", "spec_wrong", "verdict_unsupported", "verdict_wrong")
CATEGORIES = ("electronics", "grocery", "supplements", "makeup", "skincare", "haircare", "fragrances", "fashion", "other")
D05_FIELDS = ("identity", "image", "price", "size", "concentration", "specs", "rating", "review_count")  # mirror, PIN P6
SOURCE_METHODS = ("local_bhd", "converted_usd", "page_scrape", "page_scrape_rendered", "firecrawl",
                  "scrapedo_rendered", "estimated")
SOURCES_EXTRA = ("mixed", "unknown", "specs", "verdict", "critic", "kb", "kb_gap")
ACTIONS = ("recheck_source", "drop_source_for_field", "needs_operator", "no_action")
ABANDON_EVENTS = ("result_abandon", "compare_cancelled", "scan_failed")
CONFIRM_EVENTS = ("save", "share_completed", "screenshot")
GAP_OPEN_STATES = ("open", "queued", "needs_operator")
HINT_PREFIX = "pdp_"
CRITIQUE_THRESHOLD = 7        # mirrors verdict_critique_service.CRITIQUE_THRESHOLD (PIN P5)
MISSING_TABLE_CODES = ("42P01", "PGRST205")
IN_CHUNK = 100
```

No other kb_* relation literal; `common.KB_GAPS_TABLE` / `common.KB_SPECS_TABLE` are referenced, never re-spelled. A dict keyed by table uses the constants (`{KB_FEEDBACK_TABLE: ...}`), never a literal key.

#### 2.3 Reads (every one paged, ordered on the primary key, capped)

`_read(client, table, columns, window_col=None, start=None, end=None, in_col=None, in_vals=None, extra_in=None)`:
- windowed form: `client.table(t).select(columns)` [`.in_(col, vals)` for user_events event types] `.gte(window_col, start_iso).lt(window_col, end_iso).order("id").range(a, b).execute()`, pages of `common.PAGE_SIZE` (500) until a short page or `max_rows()` rows (the last page range is cut at the cap: `range(a, min(a + PAGE_SIZE, cap) - 1)`); reaching the cap = status `capped`.
- by-id form (comparisons by `id`, kb_specs by `product_id`): ids de-duplicated and sorted, chunks of `IN_CHUNK` (100): `client.table(t).select(columns).in_(in_col, chunk).order(order_col).range(0, IN_CHUNK*8 - 1).execute()` where `order_col` is `id` for comparisons and `product_id` for kb_specs (kb_specs has an `id` too: order `"id"` for both; the select need not include the order column); total rows bounded by `max_rows()`.
- window: `end = datetime(day+1, 00:00 UTC)`, `start = end - timedelta(days=window_days())`, ISO strings with `+00:00`; `window_col` = `created_at` for comparison_feedback, user_events, search_logs, verdict_critiques, kb_feedback; `last_seen` for kb_gaps.
- `day` = `--day YYYY-MM-DD` when given, else `(common._now() - 1 day).date()` (the previous UTC day, D17's rule). The coverage rows are stamped with that `day`.
- A page that is not a list raises TypeError inside the table guard.

Read order: comparison_feedback, verdict_critiques, user_events, search_logs, kb_gaps, kb_feedback (windowed), then comparisons (by the comparison_ids of in-window feedback + critiques), then kb_specs (by the product_ids of kb_feedback spec cases). No write before every read is done.

#### 2.4 Buckets, cases, actors

A CASE is one (bucket, case key); duplicates collapse (a user who reports the same comparison twice is one case).

| bucket | source table -> rule | case key | field | source | actor |
|---|---|---|---|---|---|
| price_wrong | comparison_feedback `price_correct == "wrong"` | ("cf", comparison_id or row id) | `price` | m0 == m1 in SOURCE_METHODS -> that; both in SOURCE_METHODS and different -> `mixed`; else `unknown` | ("u", user_id) or none |
| price_wrong | kb_feedback `verdict == "wrong"` and field `price` | ("kf", compare_request_id, product_id, field) | `price` | `kb` | ("d", device_key) or none |
| spec_wrong | comparison_feedback `specs_correct == "wrong"` | ("cf", ...) | `specs` | `specs` | user |
| spec_wrong | kb_feedback wrong, field not in (`price`, `identity`) | ("kf", ...) | the field (regex `^[a-z][a-z0-9_]{0,63}$`, else `other`) | `kb` | device |
| identity_wrong | kb_feedback wrong, field `identity` (045 allows it; no writer exists at base, L5) | ("kf", ...) | `identity` | `kb` | device |
| verdict_wrong | comparison_feedback `winner_correct == "wrong"` | ("cf", ...) | `verdict` | `verdict` | user |
| verdict_unsupported | verdict_critiques `missing_citation_score < 7` or `bias_score < 7` (ints only) | ("vc", comparison_id) | `verdict` | `critic` | the joined comparisons.user_id |
| spec_missing | kb_gaps state in GAP_OPEN_STATES, field not starting `pdp_` (R-G2-13) | ("kg", id) | the field | `kb_gap` | none (kb_gaps carries no actor) |

Category: comparison-backed cases = `category` of the joined comparisons row, lower-stripped, if in CATEGORIES else `unknown` (missing comparison = `unknown`); kb-backed cases = `kb.KB_CATEGORY` through `common.kb_leaf()` (`fragrances`). search_logs and user_events feed NO bucket (no field): they feed `learning.searches.failed` (success is False and is_synthetic is not True; n = such rows' total) and `learning.events.abandon` / `learning.events.confirm` (value = events, n = distinct users). The identity_wrong row in the report carries `inputs: ["kb_feedback"]` and `note: "no writer at base; SF1 / CL3 add the identity signals"`.

Actors: an in-memory set of tagged ids; an anonymous row adds a case and no actor; actor values never leave the process (only counts). `actor_basis` in the report names the proxy: `{"comparison_feedback": "user_id (proxy for device)", "verdict_critiques": "comparisons.user_id (proxy)", "kb_feedback": "device_key", "kb_gaps": "none"}`.

#### 2.5 Clusters, the systematic rule, proposals, exemplars, eval cases

- CLUSTER key = (category, source, field, bucket); `cases` = number of cases, `actors` = distinct actors over those cases, `demand` = sum of kb_gaps demand_count (spec_missing only, else 0), `systematic` = `cases >= min_cases() and actors >= min_devices()`. Sorted by (bucket, category, source, field).
- PROPOSAL for every systematic cluster: keys exactly `{bucket, category, source, field, cases, distinct_actors, judge_state, grounding, proposed_action}`; `judge_state = "pending"`; `grounding` = a list (at most 3, sorted) of `{product_id, field, source_url}` from kb_specs rows with `cited is True`, the same field and a product_id among the cluster's kb_feedback cases (kb-sourced spec_wrong only), else `[]`; `proposed_action`:
  - price_wrong + source `estimated` -> `drop_source_for_field`; price_wrong + another SOURCE_METHODS value -> `recheck_source`; price_wrong + `mixed` / `unknown` / `kb` -> `needs_operator`;
  - spec_wrong + non-empty grounding -> `recheck_source`; spec_wrong otherwise -> `needs_operator`;
  - identity_wrong, spec_missing -> `needs_operator`;
  - verdict_wrong, verdict_unsupported -> `no_action` (the judge join is D22b).
  NOTHING is applied: D22 never writes kb_specs / kb_offers / kb_products / kb_gaps / data/.
- EXEMPLAR CANDIDATES: comparison_feedback rows with `useful is True` and `winner_correct == "correct"` whose comparison joined; candidate = `{product_names: [n0, n1], winner_index: int(cwi), winner_reason: wr, key_tradeoff: kt or "", value_context: {product_0, product_1}}` only when cwi parses to 0 / 1, wr is a non-empty str, product_names has >= 2 str, vc is a dict with both keys (the rotation's filter :155-196). De-duplicated per (category, n0, n1); per category sorted by (n0, n1) and cut to `exemplars_per_category()`; version = `<day ISO>.<16 chars>` where the 16 chars are `base64.b32encode(sha256(json.dumps(set, sort_keys=True, ensure_ascii=True).encode("ascii")).digest()).decode("ascii").lower()[:16]` (base32 lower-case: no 64-hex, no 8-digit run). Owner review in the report; NEVER written under data/.
- EVAL CANDIDATES: the same confirmed rows with `wi` parsing to 0 / 1: `{category, product_names: [n0, n1], confirmed_winner_index: int(wi), confirmed_prices: {"product_0": {"amount": float, "currency": str} | null, "product_1": ...}}`; prices only when `price_correct == "correct"` and both amount (float-parsable, finite) and currency (3 upper-case letters) exist. De-duplicated per (category, n0, n1), sorted. For the owner to ratify BY HAND into data/validation_gold_truth.json (whose query rows carry category / expected_winner_index / expected_prices); the cron never writes data/.
- DE-IDENTIFICATION SCREEN (structural, not only a test): `_clean(text)` is False when the string matches any of `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}` (case-insensitive), `[0-9a-fA-F]{64}`, `@`, `\+973`, `[0-9]{8}`; an exemplar or eval candidate with ANY unclean string (names, reason, tradeoff, value_context values) is DROPPED and counted (`learning.dropped.deidentify`); a grounding entry with an unclean source_url is dropped. Product names, field names, categories, source names and verdict text are the ONLY strings that reach the report or the log; no user_id, device_key, email, query text, change_suggestion, event_data, compare_request_id, comparison id or row id ever does.

#### 2.6 Outputs, log templates, exit codes

Log lines (logger `cron_learning`, INFO unless stated; every value an int, a closed-vocabulary word, a category / field / source name, a product name or a version string):
```
[LEARNING] mode=off ENABLE_LEARNING_JOB not set; skipping run
[LEARNING] bad --day; skipping run                                   (WARNING, exit 0)
[LEARNING] no service-role client (<Type>)                           (ERROR inside the except arm, exit 1)
[LEARNING] mode=<dry|apply> day=<YYYY-MM-DD> window_days=<int>
[LEARNING] table=<name> status=<ok|absent|error|capped> rows=<int>   (one per READ_TABLES entry)
[LEARNING] table=<name> read failed (<Type>)                         (WARNING, status absent / error)
[LEARNING] cluster bucket=<b> category=<c> source=<s> field=<f> cases=<int> actors=<int> systematic=<0|1>
[LEARNING] proposal bucket=<b> category=<c> source=<s> field=<f> action=<a> grounding=<int>
[LEARNING] exemplar_set category=<c> version=<v> count=<int>
[LEARNING] exemplar category=<c> version=<v> names=<n0> || <n1>
[LEARNING] eval_case category=<c> winner=<0|1> prices=<0|1> names=<n0> || <n1>
[LEARNING] metric=<name> value=<v> n=<int>
[LEARNING] report write failed (<Type>)                              (WARNING, exit 0)
[LEARNING] upsert failed (<Type>)                                    (WARNING, exit 0)
[LEARNING] totals rows=<int> not_built=<int> clusters=<int> systematic=<int> mode=<dry|apply>
```
The verdict TEXT of exemplar candidates is in the report file only (the log carries names; L4).

Report (`--report <path>`, through `common.write_report`: ASCII JSON, LF, sorted keys) with keys exactly: `schema` (REPORT_SCHEMA), `day`, `mode`, `window_days`, `window_start`, `window_end`, `thresholds` {min_cases, min_devices, max_rows, exemplars_per_category}, `judge_state` ("pending"), `actor_basis`, `tables` {<table>: {rows, status, error: <Type> or null}}, `buckets` {<bucket>: {cases, actors, inputs, note}}, `clusters` [..], `proposals` [..], `exemplar_candidates` {<category>: {version, count, exemplars: [..]}}, `eval_candidates` [..], `context` {events_abandon, events_confirm, searches_failed, searches_total}, `dropped_deidentify`, `metrics` [[name, value, n], ..]. `--report-md <path>` (optional) writes an ASCII LF markdown summary (the metric table + the cluster table + the proposal table + the exemplar names; no verdict text).

kb_coverage_daily rows (APPLY only; ONE `client.table(KB_COVERAGE_TABLE).upsert(rows, on_conflict="day,metric").execute()`; every row from `kb.build_coverage_row(day=day, metric=name, value=value, n=n)`; a None row counted `not_built`). The CLOSED metric list (Q7):

| metric | value | n | emitted |
|---|---|---|---|
| `learning.cases.<bucket>` x 6 | cases | distinct actors | always (identity_wrong 0 / 0 at base) |
| `learning.clusters.total` | clusters | clusters | always |
| `learning.clusters.systematic` | systematic clusters | same | always |
| `learning.proposals` | proposals | same | always |
| `learning.exemplar_candidates` | candidates | categories with a set | always |
| `learning.eval_candidates` | candidates | same | always |
| `learning.actors` | distinct actors over all cases | same | always |
| `learning.events.abandon` / `learning.events.confirm` | events | distinct users | always |
| `learning.searches.failed` | failed non-synthetic rows | non-synthetic rows | always |
| `learning.dropped.deidentify` | dropped candidates / groundings | same | always |
| `learning.skipped.<table>` | 1 | 0 | only for a table absent or errored |
| `learning.capped.<table>` | rows read | rows read | only for a table that hit max_rows |

16 always-emitted names + at most 16 conditional ones; every name matches KB_METRIC_REGEX (longest `learning.skipped.comparison_feedback` = 36 chars); disjoint from D17's `kb.` / `proxy.` / `host.` prefixes. Idempotent per day: the (day, metric) upsert replaces a same-day re-run's rows (a conditional metric of an earlier same-day run that does not recur stays: L10).

Exit codes: OFF 0; bad --day 0; client construction failure 1; everything else 0 (a table failure, a report failure and an upsert failure are WARNINGs).

#### 2.7 Failure table

| failure | behaviour |
|---|---|
| flag unset / garbage / false | one INFO line, exit 0, no argparse, no client, no kb_leaf, no file |
| `--day` unparsable | one WARNING, exit 0, no client |
| no injected client and `common._admin_client()` raises or returns None | one ERROR line (type name), exit 1, nothing read |
| a kb_* table absent before 045 (exception with `.code` in MISSING_TABLE_CODES) | status `absent`, one WARNING, `learning.skipped.<table>`, its buckets 0, the run continues |
| any other exception on one table (PostgREST error, TypeError page) | status `error`, one WARNING with the type name, `learning.skipped.<table>`, the run continues |
| comparisons read fails | the joined cases keep category `unknown` and source `unknown`; exemplar / eval candidates empty; verdict_unsupported actors 0 |
| a table reaches max_rows | status `capped`, `learning.capped.<table>`, the run continues with the rows read |
| report path unwritable | one WARNING, the log copy stands, exit 0 |
| upsert raises | one WARNING, exit 0 |
| a candidate fails the de-identification screen | dropped, counted |

#### 2.8 Flag-OFF identity (the main invariant)

With `ENABLE_LEARNING_JOB` unset (or any OFF value), `main` returns 0 after exactly one INFO line; no client is constructed (a raising `_admin_client` is never called), the injected client receives zero calls, `kb_leaf` is never called, argparse never runs (a garbage argv does not raise), no file is created, and no app module is imported by the import of `scripts.cron_learning` (module top = stdlib + `scripts.kb_seed_common`). Production is byte-identical because no Railway service runs the script until the owner creates it, and nothing else imports it. The deletion E2 is production-byte-identical (no importer, flag unset, service never existed).

#### 2.9 Seams

`main(argv=None, client=None)` (the injected client for tests); `common._now` (clock); `common._admin_client` (client factory); `common.kb_leaf` (the leaf); the module attributes `learning_mode`, `window_days`, `min_cases`, `min_devices`, `max_rows`, `exemplars_per_category`; `run = main`; `if __name__ == "__main__": logging.basicConfig(level=logging.INFO); raise SystemExit(main())`.

### 3. CHANGE LIST (D22)

0. Byte copies before any edit (Python `shutil.copyfile` into the notes folder, sha256 recorded): tests/test_s81_kb_schema.py, tests/test_exemplar_contamination.py, CLAUDE.md, scripts/cron_few_shot_rotation.py, tests/test_cron_few_shot_rotation.py.
1. NEW `scripts/cron_learning.py` (ASCII, LF in the blob): sections 2.1-2.9; module docstring names the flag, the mode idiom, the DB-only rule, the de-identification rule and the stated limits L1-L4 in one paragraph each.
2. NEW `railway.learning.json` (ASCII, LF):
```
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "watchPatterns": [
      "scripts/cron_learning.py",
      "scripts/kb_seed_common.py",
      "railway.learning.json"
    ]
  },
  "deploy": {
    "startCommand": "python -m scripts.cron_learning",
    "restartPolicyType": "NEVER"
  }
}
```
3. EDIT tests/test_s81_kb_schema.py (E1): after `("scripts/cron_kb_coverage.py", 'KB_OFFERS_LATEST_VIEW = "kb_offers_latest"'),` (:356) add `("scripts/cron_learning.py", 'KB_COVERAGE_TABLE = "kb_coverage_daily"'),` and `("scripts/cron_learning.py", 'KB_FEEDBACK_TABLE = "kb_feedback"'),` plus a one-line comment `#: S81-G5 E1: the D22 job's two relation constants.` P01 unchanged.
4. DELETE scripts/cron_few_shot_rotation.py (E2) and tests/test_cron_few_shot_rotation.py (E3).
5. EDIT tests/test_exemplar_contamination.py docstrings (E4): :19-20 becomes "Feedback-sourced exemplars (synthetic:false) are no longer produced: the rotation cron was retired by S81-G5 (D22 keeps candidates in its report, never under data/)." and the sentence at :159-161 that cites test_cron_few_shot_rotation is rewritten to name the D22 refusal pin instead. No code line changes.
6. EDIT CLAUDE.md (section 8 text).

No other file.

### 4. EXISTING PINS

#### 4.1 Deliberate changes

| E | file | change | reason |
|---|---|---|---|
| E1 | tests/test_s81_kb_schema.py:341-357 | P02_ALLOWED + 2 rows keyed by file and exact line | the G2 / G3 / G4 form; the two relation constants of the new job |
| E2 | scripts/cron_few_shot_rotation.py | deleted | brief rule (g) option (i): the only code path that writes user-derived exemplars (with a comparison uuid) under data/; no importer; flag unset; never registered |
| E3 | tests/test_cron_few_shot_rotation.py (12 tests) | deleted | the test file of the deleted script (the G1 judgeme_service precedent) |
| E4 | tests/test_exemplar_contamination.py :19-20, :159-161 | docstring text only | stale references to the deleted cron (edit-in-place rule); optional per Q3 |

#### 4.2 Must stay green (unchanged)

tests/test_s81_kb_schema.py (every row incl. P01 :366, P02 :400, P03 :417, R01 :516), tests/test_exemplar_contamination.py (assertions incl. :104), tests/test_exemplar_injection_content.py, tests/test_verdict_exemplar_loader.py, tests/test_verdict_prompt_exemplar_injection.py, tests/test_prompt_fence.py (no fenced byte moves: D22 touches no prompt and no data/ file), tests/test_s81_d17_coverage.py (D17 untouched; its r9 stays the known CRLF baseline locally), tests/test_s81_s16b_kb_brands.py (pin5 railway glob), tests/test_legal_docs_u8.py (the ENABLE_FEWSHOT_ROTATION fill-in flag untouched), the scripts/ walkers of 1.9, the CLAUDE.md readers (tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py, tests/test_s81_s04_spend_breaker.py, tests/test_s81_s08b_legacy_fingerprint.py, tests/test_s81_s23_bypass_retire.py), tests/test_shadow_experiments.py.

### 5. RED TESTS: tests/test_s81_d22_nightly_learning.py

Hermetic: no socket (the netguard), no real client; the fake Supabase client is the D17 test's recorder form (tests/test_s81_d17_coverage.py:96-140: `_Query` recording `op`, `columns`, `filters`, `orders`, `rng`, `lim`), extended with `in_` and with filter EVALUATION (gte / lt / in_ applied to the seeded rows, `order` sorting, `range` slicing) so the window and the paging are real; a table can be seeded to raise (an object with `.code = "PGRST205"`, or RuntimeError). Seeded through `main(argv, client=fake)`. Module access through a `find_spec` helper + assertions (`_mod()` asserts the module exists), so every RED row fails at base on an AssertionError only. An autouse fixture deletes the flag and the five knobs, and pins `common._now` to `NOW = 2026-11-05 03:00 UTC` (default day 2026-11-04, window [2026-10-29, 2026-11-05)). B1: every OFF / no-op PIN or RED row runs with the FULL configuration (the five knobs set to synthetic in-range values, `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` set to synthetic strings built at run time) plus a call recorder. The flag readers are pinned with upper-case and padded values. All synthetic ids built at run time.

The seeded fixture `_world()` (built in code, no fixture file): 6 comparisons (fragrances x 4, electronics x 1, one with an unknown category), feedback rows giving cluster A (fragrances, page_scrape, price, price_wrong: 3 cases from 2 users), cluster B (fragrances, specs, specs, spec_wrong: 3 cases from 1 user), cluster C (electronics, verdict, verdict, verdict_wrong: 2 cases from 2 users), one anonymous price_wrong case, confirmed rows (useful + winner_correct correct) for 4 fragrance pairs and 1 electronics pair (one with price_correct correct), one confirmed row whose winner_reason carries an email shape (dropped), verdict_critiques (scores 6 / 7 / null), user_events of every ABANDON / CONFIRM type plus one type outside both (ignored) whose event_data holds a sentinel string, search_logs (success / failed / synthetic, each with a sentinel query), kb_gaps (open price field, open `pdp_x` hint, closed), kb_feedback (wrong concentration x 3 from 2 device keys, the matching cited kb_specs row), and rows outside the window on both edges. Sentinels (query text, change_suggestion, event_data, every user id / device key / compare_request_id / comparison id) are collected for R14.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | test_r1_module_and_seams | `scripts.cron_learning` importable; `main`, `run`, `learning_mode`, the five knob readers, every 2.2 constant present with the exact values | RED (module absent) | 3.1 |
| R2 | test_r2_off_is_one_line_and_nothing_else[unset, "", "false", " FALSE ", "0", "off", "no", "garbage", "dry"] | full config + recorder: exit 0; exactly one log record == the OFF template; `_admin_client` (raising stub) not called; injected client 0 calls; `kb_leaf` (spy) not called; `main(["--bogus"])` does not raise; tmp `--report` path not created | RED | 2.8 |
| R3 | test_r3_dry_reads_and_never_writes["true", " TRUE ", "1", "yes", "On"] | report written; every recorded op is `select`; zero upsert / insert / update / delete on ANY table; the metric lines present | RED | 2.3, 2.6 |
| R4 | test_r4_apply_one_upsert_through_the_builder["apply", " APPLY "] | exactly one write op: upsert on `kb_coverage_daily` with `on_conflict == "day,metric"`; payload == the list of `build_coverage_row` outputs (spy wraps the real leaf builder; every call keyword-only with day == date(2026,11,4)); no other write | RED | 2.6 |
| R5 | test_r5_cli_dry_run_downgrades_apply | flag `apply` + `--dry-run` -> no write; mode=dry in the header line | RED | 2.6 |
| R6 | test_r6_read_discipline | per table: the select column string equals the 2.2 constant; windowed tables carry exactly one `gte` and one `lt` on the 2.3 column with the window ISO edges; every read carries `order("id")`; user_events carries `in_("event_type", ABANDON_EVENTS + CONFIRM_EVENTS)`; no recorded select string contains `query`, `change_suggestion`, `mattered_most`, `event_data`, `error_message`, `products_found`, or a bare `full_response` token | RED | 2.3 |
| R7 | test_r7_paging_and_cap | 1,200 seeded in-window feedback rows: ranges (0,499), (500,999), (1000,1499) with ordered ids; with `LEARNING_MAX_ROWS=700`: rows read 700, status capped, `learning.capped.comparison_feedback` value 700 n 700; `LEARNING_MAX_ROWS=50` clamps to 100 | RED | 2.3 |
| R8 | test_r8_bucket_counts | `report["buckets"]` cases / actors equal the literal dict of the fixture (identity_wrong 0 / 0 with inputs ["kb_feedback"]); out-of-window rows excluded on both edges | RED | 2.4 |
| R9 | test_r9_clusters_and_systematic_rule | cluster A systematic, B not (1 actor), C not (2 cases), the anonymous case adds a case and no actor; clusters sorted by (bucket, category, source, field) | RED | 2.5 |
| R10 | test_r10_knobs_move_the_rule | `LEARNING_MIN_CASES=2` -> C systematic; `LEARNING_MIN_DEVICES=1` -> B systematic; `LEARNING_MIN_CASES` in ("0", "-1", "inf", "nan", "x", "") -> 3; `LEARNING_MIN_DEVICES=99` -> 10; `LEARNING_WINDOW_DAYS=1` narrows the window (fewer cases); `=31` clamps to 30 | RED | 2.1 |
| R11 | test_r11_window_and_day | default day = previous UTC day; `--day 2026-10-30` moves both edges; `--day 2026-13-01` -> WARNING, exit 0, no client call | RED | 2.3 |
| R12 | test_r12_proposals | one proposal per systematic cluster; key set exact; judge_state "pending"; actions per the 2.5 mapping (price page_scrape -> recheck_source; a seeded `estimated` systematic cluster -> drop_source_for_field; kb concentration with the cited kb_specs row -> recheck_source + one grounding entry {product_id, field, source_url}); no write op on kb_specs / kb_offers / kb_products / kb_gaps / kb_feedback in apply mode | RED | 2.5 |
| R13 | test_r13_exemplar_candidates | only useful + winner_correct correct rows; per-category count = min(confirmed, knob); `LEARNING_EXEMPLARS_PER_CATEGORY=1` -> 3, `=9` -> 5; entry key set exact; version matches `^\d{4}-\d{2}-\d{2}\.[a-z2-7]{16}$`, stable across two runs, changes when one winner_reason changes | RED | 2.5 |
| R14 | test_r14_report_log_and_rows_are_deidentified | over the report file text, the md file, every log message and every upsert row: none of the sentinels; no match of the uuid regex, `[0-9a-fA-F]{64}`, `@`, `\+973`, `[0-9]{8}`; the email-shaped candidate dropped and `learning.dropped.deidentify` >= 1 | RED | 2.5 |
| R15 | test_r15_eval_candidates | shape exact; confirmed_prices only for the price_correct correct row (amount float, currency 3 letters); others null | RED | 2.5 |
| R16 | test_r16_absent_kb_tables_are_counted_skips | kb_gaps + kb_feedback raise `.code = "PGRST205"`: exit 0; tables status absent; `learning.skipped.kb_gaps` and `learning.skipped.kb_feedback` value 1 n 0; spec_missing 0; the comparison_feedback metrics still present | RED | 2.7 |
| R17 | test_r17_one_table_error_isolated | user_events raises RuntimeError: one WARNING naming `RuntimeError` and no message text; status error; the rest present | RED | 2.7 |
| R18 | test_r18_client_failure_exits_one | flag true, no injected client, `_admin_client` raises: exit 1; exactly one ERROR record carrying the type name only; no read | RED | 2.7 |
| R19 | test_r19_unwritable_report_keeps_the_log | `--report` = an existing directory: WARNING, exit 0, metric lines logged | RED | 2.7 |
| R20 | test_r20_metric_names_closed_and_valid | every emitted name in the closed list (built in the test from 2.6, not read from the module); each matches `KB_METRIC_REGEX`; none starts with `kb.`, `proxy.`, `host.`; values int / float finite; n int >= 0; the 16 always-emitted names present | RED | 2.6 |
| R21 | test_r21_apply_is_idempotent_per_day | two apply runs on the same seeded world: two upserts, identical payloads, same on_conflict | RED | 2.6 |
| R22 | test_r22_db_only_no_llm_no_network | AST of the module: module-level imports only stdlib + `scripts.kb_seed_common`; no Import / ImportFrom anywhere of `app.services.openai_service`, `anthropic`, `openai`, `httpx`, `requests`, `curl_cffi`, `aiohttp`, `urllib.request`, `app.services.serper_service`, `app.services.llm_router`; the source text has no `kb_service` | RED | 2.8 |
| R23 | test_r23_never_writes_data_dir | a DRY and an APPLY run in a tmp cwd create no file other than the two report paths; the module source contains no `"data"` path segment and no `write_text` | RED | 2.5 |
| R24 | test_r24_railway_config | railway.learning.json exists; parsed == the 3.2 object; ASCII; after `\r\n` -> `\n` no `\r` | RED | 3.2 |
| R25 | test_r25_script_hygiene | cron_learning.py ASCII; after `\r\n` -> `\n` no `\r`; none of the banned 1.9 needles (`request_context`, `x-compare-request-id`, `legacy_hash`, `device_lookup_keys`, `QarenBot`, `NAMED_AGENT`, `@gmail.com`, `cleanup_expired_ratings`) | RED | 3.1 |
| R26 | test_r26_rotation_cron_retired | `scripts/cron_few_shot_rotation.py` absent; no `.py` under app/, scripts/, tests/ (this file excluded) imports or names the module `cron_few_shot_rotation` (docstring mentions in tests/test_exemplar_contamination.py allowed only if E4 is ruled out: the row then scans import statements only) | RED (the script exists) | E2 / E3 |
| R27 | test_r27_verdict_unsupported_threshold | critique scores 6 -> case, 7 -> no case, null -> no case (both axes) | RED | 2.4 |
| R28 | test_r28_context_metrics | events abandon / confirm counts and distinct users; the out-of-set event type ignored; searches failed excludes synthetic | RED | 2.4 |
| R29 | test_r29_log_templates | every INFO / WARNING record matches one 2.6 template regex; the totals line last | RED | 2.6 |
| P1 | test_p1_no_user_derived_exemplar_under_data | data/verdict_exemplars.json + data/verdict_exemplars.s3_parked.json: every exemplar has `_provenance.synthetic is True` and a source_pattern_id with no uuid shape; canonical exemplars[] empty | PIN (green: 0 / 26 measured) | stays |
| P2 | test_p2_run_mode_contract | `common.run_mode("ENABLE_LEARNING_JOB")` over the R2 / R3 / R4 values (full config) -> off / dry / apply; `int_knob` fallbacks for the 2.1 ranges | PIN | stays |
| P3 | test_p3_builder_accepts_the_learning_names | `build_coverage_row` (the real leaf) returns a row for each always-emitted name and for `learning.skipped.comparison_feedback` (names built in the test), day 2026-11-04, value 0 and 1.5, n 0 | PIN | stays |
| P4 | test_p4_no_railway_service_runs_rotation_or_learning_twice | every railway*.json: startCommand never names `cron_few_shot_rotation`; at most one names `cron_learning` | PIN (green at base: none names either) | stays |
| P5 | test_p5_critique_threshold_mirror | `verdict_critique_service.CRITIQUE_THRESHOLD == 7` and CRITIQUE_AXES contains the two axes D22 reads | PIN | stays |
| P6 | test_p6_field_and_event_vocabularies | `kb_ingest.D05_FIELDS` == the 2.2 tuple literal (in the test); every ABANDON / CONFIRM event in `feedback_routes.VALID_EVENT_TYPES`; `kb_service.KB_COLUMNS` for kb_gaps / kb_feedback / kb_specs contain every column D22 selects | PIN | stays |
| P7 | test_p7_feedback_writer_columns | the source of `feedback_service.save_feedback` assigns `record["winner_correct"]`, `["price_correct"]`, `["specs_correct"]`, `["user_id"]`, `["comparison_id"]`; `database_service.save_comparison` record has no `category_used` key (so D22 must read the JSON path) | PIN | stays |

Counts at spec: 29 RED rows (R2 / R3 / R4 / R10 parametrised: about 45 RED nodes) and 7 PIN rows (about 9 nodes); the RED gate records the measured node counts.

### 6. MUTATION TABLE (on byte copies of scripts/cron_learning.py at GREEN; restore + sha256 after each)

| M | mutation (exact-string edit) | killing rows |
|---|---|---|
| M1 | OFF branch `return 0` moved after `_client(...)` (client built before the mode check) | R2, R18 |
| M2 | `run_mode(FLAG)` -> `house_flag(FLAG)` semantics (truthy writes) | R3, R4 |
| M3 | drop `.order("id")` from the windowed read | R6, R7 |
| M4 | `.lt(window_col, end)` -> `.lte(...)` or removed | R8, R11 |
| M5 | `actors >= min_devices()` -> `cases >= min_devices()` | R9, R10 |
| M6 | add `change_suggestion` to FEEDBACK_COLUMNS | R6, R14 |
| M7 | skip the de-identification screen | R14 |
| M8 | write the upsert also in DRY | R3 |
| M9 | `on_conflict="day,metric"` -> `"metric"` | R4, R21 |
| M10 | a kb table read error raises instead of counted skip | R16, R17 |
| M11 | `exemplars_per_category` default 5 -> 10 / clamp removed | R13 |
| M12 | `< CRITIQUE_THRESHOLD` -> `<=` | R27 |
| M13 | `HINT_PREFIX` filter removed on kb_gaps | R8 |
| M14 | client failure returns 0 | R18 |
| M15 | `judge_state` "pending" -> "agreed" | R12 |

### 7. GATES (cheapest first) AND THE COMM SET

1. `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on scripts/cron_learning.py and the RED file; `json.loads` railway.learning.json; bytes > 127 = 0 in every written file.
2. The RED file (bound 600): RED rows red at base on AssertionError only, PIN rows green; at head every row green.
3. tests/test_s81_kb_schema.py (E1) and tests/test_exemplar_contamination.py (E4) (bound 600).
4. The comm set by the union rule, base vs head, chunks of at most 25 files, bound 1200, `comm -13` and `comm -23` of the sorted FAILED node ids EMPTY. The set at BASE (44 files, set sha256 803bde0c... over the sorted LF list):
   - reference grep (`kb_seed_common|kb_service|cron_kb_coverage|cron_few_shot_rotation|verdict_exemplars|kb_coverage_daily|FEWSHOT`): test_cron_few_shot_rotation (base only), test_exemplar_contamination, test_exemplar_injection_content, test_legal_docs_u8, test_m21_brand_dedup_and_verdict_copy, test_per_category_anti_patterns, test_s81_d09_feed_walker, test_s81_d11_pdp_discovery, test_s81_d14_live_robots, test_s81_d16_operator_ingest, test_s81_d17_coverage, test_s81_g2_gate_rows, test_s81_kb_schema, test_s81_s15_gate_rows, test_s81_s15_registry_robots, test_s81_s16_kb_seed, test_s81_s16b_kb_brands, test_s81_s17_kb_ingest, test_s81_s18_kb_first_serve, test_s81_s19_gap_queue, test_shadow_experiments, test_verdict_exemplar_loader, test_verdict_prompt_exemplar_injection, test_verdict_prompt_forbidden_words_audit;
   - the house source-scanning pins: test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_secret_scan_static, test_hermeticity_pins;
   - the scripts/ walkers: test_legal_s78, test_legal_disclosure_s77, test_retro_w1_2b, test_s81_s05_request_context, test_s81_s08b_legacy_fingerprint (+ test_u3c_store_false_pin, test_s81_kb_schema above);
   - the railway glob reader: test_s81_s16b_kb_brands (above);
   - the CLAUDE.md readers: test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s23_bypass_retire;
   - the gate rows that drive scripts/: test_s81_g2_gate_rows (above), test_s81_g4_gate_rows;
   - importers of an edited module: none (no app/ module edited; kb_seed_common and cron_kb_coverage are read only); app/main.py does not import scripts/.
   At HEAD: the 43 surviving files + tests/test_s81_d22_nightly_learning.py (44). The deleted test file's base FAILED set must be empty (12 green at base, measured base1) so `comm -23` stays meaningful.
   Base record: built by the RED at ec747b49 by per-file reuse of the stored e1491c97 record (4b65c5db..., 307 files) and the 0b19de5b records (90b85603..., 661; c5734182..., 302) under GC-9: a member is reused only when its text references none of kb_service / kb_seed_common / seed_kb_brands_wikidata / tests/test_s81_s16_kb_seed.py / tests/test_s81_kb_schema.py nor CLAUDE.md, is not a glob walker, and its file did not change at ec747b49; every other member runs at base. By that rule the reuse candidates are only test_exemplar_injection_content, test_m21_brand_dedup_and_verdict_copy, test_per_category_anti_patterns, test_shadow_experiments, test_verdict_*, test_model_config*, test_prompt_fence, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_start_command, test_hermeticity_pins, test_secret_scan_static, test_exemplar_contamination (if they are members of a stored record); the rest run at base. Stored under harness/base_records/ec747b49.../<set-sha>.txt with the [pyt] lines (LC-6).
   Known base noise to record identically: test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene (CRLF, measured base1); the tiktoken egress line of test_exemplar_injection_content (measured base2); test_prompt_truth's two cold-tiktoken ERRORs if that file enters a chunk.
5. The fourteen backend-scanning client jest fences, BY PATH through the orchestrator's junction, at GREEN and at the final round (house rule for a scripts/ footprint; D22 moves no literal they read, expected 13 / 14 with the four w37 drift nodes): brand/inAppMark.u4c, clientTruth/{medicalNote,privacyManifest,shareTruth}.s74, clipboardFallbackService, config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService (+ .edges), ResultsScreen.timeout. The FULL jest suite once in the last round (LC-7).
6. The pre-commit hook files are NOT in the set (no .githooks edit). The gitleaks keyword rule: no constant name in cron_learning.py carries access / auth / api / credential / creds / key / password / secret / token AND a 64-hex literal (D22 has no hex literal at all; the RED file builds its 64-hex sentinel at run time as `"a" * 64`).

### 8. CLAUDE.md ROW + OWNER STEPS (names only)

Block inserted after the S81-G4 owner-steps bullet (CLAUDE.md:565), ASCII only:

```
**SESSION 81 flags (S81-G5 LEARN-SEARCH: D22 NIGHTLY-LEARNING, 2026-11-05; default OFF, read PER CALL; a new name, so unset in production by construction (Railway not read); the fifth SAFE group under LC-9 (PLAN_S81 :170 as re-cut by specs/S81_G5_BRIEF.md: scripts only, no migration, no app/ file; S81-21 joins a later group); spec `.qa-s80/S81-G5_UNIT_SPEC.md` of the unit worktree, the orchestrator's review `specs/RULINGS_S81_G5.md` and the RED gate `specs/GATE_S81_G5.md` in `docs/investigations/2026-10-22-session-81-state/`; the frozen RED file `tests/test_s81_d22_nightly_learning.py`; no migration, no client file, no new credential name):**
- `ENABLE_LEARNING_JOB` (mode: unset / garbage OFF, true / 1 / yes / on DRY RUN, `apply` WRITE; `--dry-run` downgrades) + knobs `LEARNING_WINDOW_DAYS` (7, 1..30), `LEARNING_MIN_CASES` (3, 1..100), `LEARNING_MIN_DEVICES` (2, 1..10), `LEARNING_MAX_ROWS` (5000 per table, 100..50000), `LEARNING_EXEMPLARS_PER_CATEGORY` (5, 3..5) (D22 NIGHTLY-LEARNING, `scripts/cron_learning.py`, service config `railway.learning.json`, a separate service). Nightly, DB only (the service-role client; no LLM, no Serper, no other network): reads the window ending at the previous UTC midnight of comparison_feedback, verdict_critiques, user_events, search_logs, kb_gaps, kb_feedback (paged, ordered on id, capped; a kb_* table absent before 045 is a counted skip) plus the joined comparisons (JSON paths only, never the query text) and kb_specs for grounding; builds the six buckets (identity_wrong from kb_feedback only, no writer yet; price_wrong; spec_missing from open non-`pdp_` kb_gaps; spec_wrong; verdict_unsupported from verdict_critiques below 7 on missing_citation or bias; verdict_wrong), the category x source x field clusters and the SYSTEMATIC rule (cases >= LEARNING_MIN_CASES from >= LEARNING_MIN_DEVICES distinct actors; user_id is a PROXY for a device outside kb_feedback; the judge is absent, so every proposal carries judge_state pending and NOTHING is applied); writes the de-identified report (`--report` JSON, `--report-md`; product names, fields, sources, verdict text and counts only, never a user id, device key, email, query text, comment or request id) and logs counts and names (the log is the durable copy: Railway's filesystem is ephemeral); APPLY also upserts the closed `learning.*` metric list into kb_coverage_daily per (day, metric) through `build_coverage_row`. KB correction proposals, the exemplar candidate sets (versioned by day + content hash) and the candidate eval cases are for the owner to review; nothing is written under data/. `scripts/cron_few_shot_rotation.py` (its data/ write of feedback exemplars) is deleted. Stated limits: the judge join, the exemplar and proposal tables and the rotation of exemplars into the cached verdict prefix are D22b (FOCUS: migration 053 + the prompt-fence digests); no $0 replay exists (shadow_experiments' replay calls OpenAI); the behaviour-profile select fix and the variant-hint learned file are D22c.
- **Owner steps (names only; a dated ledger line per step):** (1) apply 045 then 047 (owner item 29) then 052; (2) create the `learning` Railway service from `railway.learning.json` with `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` and a nightly cron schedule at a different hour from `kb-coverage`; (3) set `ENABLE_LEARNING_JOB=true` and make ONE DRY run; read the run log (learning.cases.* per bucket, learning.clusters.systematic, the proposals, the exemplar candidates, the eval candidates, the skipped tables); (4) then `apply`; ratify eval cases by hand into data/validation_gold_truth.json only through a reviewed PR. Rollback: unset the variable.
```

Feature Flags pointer clause appended after the S81-G4 clause on CLAUDE.md:341: `` `ENABLE_LEARNING_JOB` and the `LEARNING_*` knobs (S81-G5 LEARN-SEARCH, default OFF): the rows of the **SESSION 81 flags (S81-G5 LEARN-SEARCH, ...)** block. ``

### 9. STATED LIMITS

- L1 The judge is absent at ec747b49 (compare_judgements = S81-22): the systematic rule degrades to user signals; every proposal is judge_state pending; D22b adds the judge join.
- L2 `user_id` is a PROXY for a device on comparison_feedback / user_events / search_logs / verdict_critiques (via comparisons); anonymous rows add cases and no actor (so anonymous-only clusters never reach the rule).
- L3 identity_wrong has only the kb_feedback `identity` input, which no code writes yet: 0 until SF1 (046) / CL3 or a kb_feedback writer lands.
- L4 The report file is ephemeral on Railway; the log is the durable copy and carries names and counts but NOT the exemplar verdict text (the owner reads the text from a local DRY run or after D22b's table).
- L5 kb_gaps / kb_feedback / kb_specs / kb_coverage_daily exist only after 045 is applied: before it the kb reads are counted skips and APPLY's upsert fails with one WARNING (rows logged).
- L6 The specs source axis is the constant `specs` (the stored response has no per-field source host); price clusters use source_method (no host), so a host-level proposal needs the operator.
- L7 kb_gaps carries no actor: spec_missing clusters never become systematic; they are reported with their demand.
- L8 No $0 DB-only replay exists (shadow_experiments `run` calls OpenAI; no pairwise judge): the offline proof is D22b.
- L9 The window edges are whole UTC days ending at the previous midnight; rows written after midnight wait for the next night. The per-table cap bounds a run; a capped table is counted, its tail unread (ordered by id, so the read is deterministic, not the newest rows).
- L10 A conditional `learning.skipped.*` / `learning.capped.*` row written by an earlier same-day run is not removed by a later same-day run that does not hit the condition.
- L11 Category comes from `full_response.category_used` (no column): a row whose JSON lacks it is `unknown`.
- L12 The legal fill-in flag list still names `ENABLE_FEWSHOT_ROTATION` (recorded `off`); it becomes a name with no code after E2 (the U8 legal machinery is not touched: FOCUS).

### 10. OUT OF SCOPE

- D22b (FOCUS): migration 053 (service-role tables for proposals and versioned exemplar sets), the judge join with compare_judgements after S81-22, the rotation of ratified exemplars into the cached verdict prefix (the prompt-fence digests), a frozen-input pairwise replay.
- D22c PROFILE-SELECT + VARHINT-RETIRE (a follow-up SAFE unit, the LC-9 re-cut by file cohesion):
  (1) the behaviour-profile select `app/services/structured_comparison_service.py:5947` reads `user_events` with `select("event_type, metadata")` while every writer stores `event_data` (`app/services/feedback_service.py:270` (record key) and :304, `app/api/feedback_routes.py:223`; no migration creates user_events), so the fire-and-forget `_update_behavior_profile` (:5931-5953) has raised inside its except arm (one WARNING) and never written `users.behavior_profile` (:5952); fixing the token makes returning users' later compares read a profile at :5924 and pass it to compute_scores: NOT byte-identical, hence its own dark flag in D22c;
  (2) `_VARHINT_LEARNED_PATH` `app/services/price_service.py:9066` + `_varhint_append_learned` :9156-9173 append to data/variant_hint_learned.json only under `variant_llm_hint_enabled()` (B3b, default OFF) and nothing reads the file (the only other reference is tests/test_variant_llm_hint_b3b.py:66, which suppresses the write): "deleted" in D22c = the append, the path constant, the data file and the test suppression, proven byte-identical by the price_service corpus SHA gate.
- S81-21 WEB-SEARCH-CAPPED (after S81-07).
- D17b (the `_paged` ORDER BY in cron_kb_coverage.py).
- Any change to the legal fill-in machinery, data/verdict_exemplars*.json, data/validation_gold_truth.json, eval_runs (D22 reads none of them at runtime; eval_runs found no use).

### 11. OPEN QUESTIONS (for the LC-8 review)

- Q1 Exit code on a client construction failure: the brief says exit 1 after one ERROR line; D17 exits 0 with a WARNING (`resolve_client`). Spec follows the brief (exit 1; a Railway cron then shows a failed run). Confirm.
- Q2 search_logs: the brief floated "success with an empty products_found" as spec_missing; measured, products_found is the list of identified product NAMES, so an empty list is an identity / parse failure with no field: spec feeds search_logs into the context metric `learning.searches.failed` only and never selects products_found. Confirm (or rule it into identity_wrong as a proxy).
- Q3 E4 (the two docstring sentences of tests/test_exemplar_contamination.py): include (edit-in-place rule) or rule out (R26 then scans import statements only).
- Q4 kb_feedback field `identity` -> identity_wrong (the 045 DDL allows it; no writer yet) instead of the brief's "always n = 0, source unavailable": the counts are identical today; confirm the mapping.
- Q5 LEARNING_MAX_ROWS default 5000 / range 100..50000 (a spec-chosen knob name and range; the brief left it open).
- Q6 PostgREST JSON-path select with array index (`full_response->overview->products->0->price->>source_method`) is the documented PostgREST form, but it is NOT measured against the live project (never probed); the ONE DRY run is its proof; if a path returns null the cases fall to `unknown` (never an error). Accept as an owner-run check (owner step 3).
- Q7 SAFE check (section 12): the job reads user tables with the service-role client and writes only de-identified aggregates; privacy policy app/legal/privacy_policy.md:59 already covers "producing de-identified statistics about comparisons and preferences" (no legal text change). Orchestrator to confirm SAFE.

Not done in this spec: no code, no RED file, no base record (the RED builds it), no jest run, no probe of production, Railway or Supabase.

---

## 12. THE GROUP CHECK

- Combined comm set = D22's (section 7.4): 44 files at base (set sha256 803bde0ca1b911bb47e68c007228505b1b280a9c69a5d59c7828fab148598e96 over the sorted LF path list), 44 at head (minus tests/test_cron_few_shot_rotation.py, plus tests/test_s81_d22_nightly_learning.py). CI-order set (one runner call, bound 1200): the RED file, tests/test_s81_kb_schema.py, tests/test_exemplar_contamination.py, tests/test_s81_d17_coverage.py, tests/test_s81_s16b_kb_brands.py, tests/test_legal_docs_u8.py, tests/test_ci_gates.py.
- Combined footprint: 2 new non-test files (scripts/cron_learning.py, railway.learning.json), 1 deleted script, 1 new test file, 1 deleted test file, 2 edited test files (E1, E4), CLAUDE.md. NO app/, migrations/, SmartCompareApp/, .github/, .githooks/, data/, requirements*, app/legal/ file.
- Shared-file plan: section 0.3 (no intra-group sharing; CLAUDE.md and tests/test_s81_kb_schema.py are shared with merged units and edited by GREEN in that order).
- PR plan: ONE PR from `feature/s81-g5-learn-search`, body at most 25,600 bytes measured with python: the group summary, one short D22 section (flag, mode, outputs, buckets, the systematic rule, the de-identification rule), the counts, the E-rows table (E1-E4), the stated limits L1-L12, the owner steps names-only (section 8), no [NATIVE READ] items (no client copy); mutation tables and gate logs filed under specs/ by name.
- SAFE check (LC-1 surfaces), each measured against the footprint:
  - auth / tokens / sessions: NOT touched (no auth module, no token; the service-role client is the existing `database_service.get_admin_supabase_client` through `kb_seed_common._admin_client`).
  - quota / billing / refunds: NOT touched.
  - legal or privacy text: NOT touched (app/legal untouched; scripts/fill_in_legal.py and its fixture untouched; the outputs fit privacy_policy.md:59).
  - consent path: NOT touched.
  - security middleware: NOT touched.
  - migrations: NONE added (045 / 047 / 050 / 052 unchanged; test_s14_r01 census unchanged).
  - Redis / Lua scripts: NOT touched (D22 reads no Redis).
  - App-Review-visible client surface: NOT touched (no client file, no response key, no envelope).
  - secrets or key handling: NOT touched (no new credential name; no key literal; reads only the existing service-role names at the owner's service).
  - The kb_coverage_daily write through the builder with the service-role client = the SAFE telemetry class of R-G3-1 / R-G4-1.
  focus_surfaces_found: none. D22 stays in the group.
