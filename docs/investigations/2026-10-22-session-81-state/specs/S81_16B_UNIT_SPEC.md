# S81-16b KB-BRANDS unit spec (measured): migration 051 kb_brands + kb_service.build_brand_row + the APPLY write of scripts/seed_kb_brands_wikidata.py under ENABLE_KB_BRANDS

- Unit: S81-16b KB-BRANDS. FOCUS (LC-1: a migration). The full chain: this spec -> adversarial spec review -> RULINGS_S81_16B -> RED -> gate -> GREEN -> two adversaries (correctness; schema-and-data) -> fix -> rebase -> PR (body <= 25,600 bytes).
- Flag: `ENABLE_KB_BRANDS` (a NEW name, default OFF, read per call as the FIRST statement of `main` through `kb_seed_common.run_mode`; the G2 mode idiom R-G2-1: unset / blank / garbage / false / 0 / no / off / dry -> OFF; true / 1 / yes / on -> DRY; the exact word apply (strip + lower) -> WRITE). Knob `KB_BRANDS_MAX` (int, default 300, clamped 1..5000, the `kb_seed_common.int_knob` shape). New names, so unset in production by construction (R-A15: the newest dated ledger line, 2026-11-04 19:08 in the session-81 ledger, names neither).
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-s16b`, detached at base `0b19de5bcc1416111d48bc725359b95151a658ca` (`git rev-parse HEAD`), `git status --short` EMPTY at the start and after every probe (this file sits under the gitignored `.qa-s80/`, `.gitignore:72 .qa-*/`). Branch for GREEN: `feature/s81-s16b-kb-brands`.
- Evidence: the unit brief `specs/S81_16B_BRIEF.md`; PLAN_S81.md :156 ("Wikidata brand entities (CC0) imported once"); RULINGS_S81_G2.md R-G2-1 (the mode idiom), R-G2-3 (the withdrawn write; S81-16b recorded at RULINGS_S81_G2 :28), R-G2-12 (the PostgREST insert-ignore return shape is unmeasurable offline), R-G2-20 (the canary list); the CLAUDE.md S81-G2 block :547-551 at 0b19de5b; PLAN_S80 section 0 (re-read in this run: additive keys only, never a bare 503, refusals only through build-3 envelopes) and `runs/research/contract_freeze.json` (re-read: keys category / summary / findings / recommendations / open_questions / sources): this unit touches NO response path, so no frozen key can move.
- Sister units and contracts: G2 KB-SEED (#383, merged; this unit amends its frozen RED rows R23 / R24 and its CLAUDE.md row); S81-14 KB-SCHEMA (#373; 045 + the kb_service leaf: consumed, extended additively); G3 KB-INGEST (#384; kb_ingest.py imports kb_service lazily: consumes KB_BUILDER_KEYS for its own five tables only, no change); G4 KB-SERVE (spec in flight in `sc-s81-g4` at 0b19de5b: S81-18 / S81-19 may touch `app/services/kb_service.py` and `tests/test_s81_kb_schema.py` P01 / P02: a KNOWN REBASE on the KB_TABLES tuple and the two allowlists, whichever merges second unions). Owner item 29 applies 045 then 047; 051 is applied after them.
- Personal-data rule: no real names, emails, phone numbers, device ids or account ids in this file or anything the unit writes; synthetic brands and hosts only (`brand-b.example.com`, `Maison Example`), Arabic test strings built at run time from code points; the Wikidata query excludes human items (2.3), so no person's name is imported. No secret value; variable NAMES only.
- Measurement location: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/s16b/` (`base1.log`, `collect.log`, `comm.py`, `comm_base.txt` / `comm_head.txt`, `proto/` = the scratch prototype: the draft migration + rollback, the three APPLY drafts, `proto_builder.py` + `.out`). Nothing in the worktree was written except this file.

## 0. What the unit does

RULINGS_S81_G2 R-G2-3 withdrew the Wikidata write from G2 because 045 has no brand-label column: `scripts/seed_kb_brands_wikidata.py` ships DRY-only (it prints counts and writes official-site hosts to `--report`; `apply` behaves as DRY) and the G2 stated limit S16 L7 / the CLAUDE.md row say "a brands table is S81-16b, a migration". This unit:

1. adds migration `migrations/051_kb_brands.sql` (WRITTEN, NOT APPLIED) + `migrations/rollback/051_kb_brands.sql`: ONE table `public.kb_brands (qid, label_en, label_ar, official_host, source, created_at, updated_at)`, the 045 host belts as CHECKs, a partial index on `official_host`, the 045 trigger function reused, service-role only (RLS on, no policy, the 045 REVOKE / GRANT form);
2. adds `kb_brands` to the S81-14 leaf census (`KB_TABLES`, `KB_COLUMNS`, hence `KB_BUILDER_KEYS`) and ONE pure builder `build_brand_row` with the house belts (`_pg_text_ok`, `_belted_host` = the regex + top-label + deny-label belt, `kb_source_allowed` = the deny rule, `_ts_iso`), None on any refusal, never raises;
3. gives the brand script its OWN flag `ENABLE_KB_BRANDS` and an APPLY mode that WRITES `kb_brands` through `kb_seed_common.KbWriter` (insert-ignore on qid; ONE update of `label_en / label_ar / official_host / updated_at` per row the insert did not return, restricted to `source = 'wikidata'`; nothing ever deleted), capped by `KB_BRANDS_MAX`; the SPARQL query gains the en / ar labels (OPTIONAL rdfs:label + LANG filter), a human-item exclusion and a deterministic ORDER BY; DRY keeps the robots read, ONE SPARQL GET, the host derivation and `--report`, adds the label coverage counts and writes NOTHING; `ENABLE_KB_SEED` never runs this script any more, so R-G2-3's sentence stays true for `ENABLE_KB_SEED`;
4. amends the frozen G2 rows R23 / R24 (+ the G2 file's autouse env list) by the E-rows EK0..EK2, amends `tests/test_s81_kb_schema.py` R27 by E1, adds the RED file `tests/test_s81_s16b_kb_brands.py`;
5. rewrites the S81-16 CLAUDE.md row's brand sentence and owner step (8) in place (no new block); drafts the DEFECT_LEDGER row and the three APPLY_051 files.

No request-path `app/` file changes (the only `app/` edit is the leaf `kb_service.py`, which no request path imports: P01 at `tests/test_s81_kb_schema.py:358-389` holds its importers to `merchant_registry.build_seed_rows`, `kb_seed_common.kb_leaf`, `kb_ingest.kb_leaf`, all function-local and flag-gated); no client file; no new external host (`query.wikidata.org` is already the G2 script's host, `scripts/seed_kb_brands_wikidata.py:28-29`).

## 1. Base state (measured at 0b19de5b)

### 1.1 The brand script `scripts/seed_kb_brands_wikidata.py` (147 lines, ASCII, CRLF working copy / LF blob)

| line | what |
|---|---|
| 1-10 | docstring: "DRY-ONLY by ruling R-G2-3 ... It writes NOTHING to the KB in any mode" |
| 22 | `from scripts import kb_seed_common as common` (the ONLY module-top non-stdlib import) |
| 26 | `FLAG = "ENABLE_KB_SEED"` |
| 27 | `PREFIX = "[KB_BRANDS]"` |
| 28-29 | `ROBOTS_URL = "https://query.wikidata.org/robots.txt"`, `SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"` |
| 32-33 | `SPARQL = ("SELECT DISTINCT ?brand ?site WHERE { ?brand wdt:P1056 wd:Q131746 . ?brand wdt:P856 ?site . } LIMIT 2000")` |
| 34 | `MAX_BRAND_HOSTS = 300` (the report cap of the host list) |
| 37-38 | `sparql_url()` = endpoint + `?format=json&query=` + `quote(SPARQL, safe="")` (207 chars at base) |
| 41-45 | `_parse_args`: `--dry-run`, `--report` |
| 48-50 | `_site_host(binding)` -> the `site.value` string or None |
| 53-88 | `derive_hosts(bindings, existing, counts)`: per binding bump `bindings`; `with_site`; `dh.normalize_host(urlsplit(site).hostname)` (drops ONE `www.`, the port, trailing dots); `invalid` unless `KB_HOST_REGEX` + `KB_HOST_TOP_LABEL_REGEX`; `denied` if `dh.is_denied_host`; `existing` if in kb_merchants; sorted, capped at 300 (`over_cap`), `new` |
| 91-126 | `_run`: `common.read_merchant_rows(client)` (WARNING + return 0 on failure) -> `PoliteFetcher().get(ROBOTS_URL, gate=False, timeout=20.0)` (2xx body, 404 / 410 empty, else INFO "robots unreadable" + return) -> `robots_eval.can_fetch` for QARENBOT_UA AND "*" (else INFO "robots disallow") -> ONE `fetcher.get(sparql_url(), gate=False, timeout=60.0)` -> `json.loads(body)["results"]["bindings"]` (WARNING type name on failure) -> `derive_hosts` -> `common.write_report(args.report, {"hosts", "counts"})` -> `common.log_counts` |
| 129-140 | `main(argv=None, client=None)`: `mode = common.run_mode(FLAG)` FIRST; OFF -> ONE INFO `"%s mode=off ENABLE_KB_SEED not set; skipping run"`, return 0; `cli_mode`; INFO `"%s mode=%s (writes nothing in any mode; apply behaves as dry)"`; `resolve_client`; `asyncio.run(_run(args, client))` |
| 143 | `run = main` |

Measured base behaviour (venv python, the worktree on sys.path, read-only): `derive_hosts` over the 7-binding probe of 5.4 PIN-2 returns `['brand-b.example.com', 'brand-c.example.org']` and counts `bindings=7 denied=1 existing=1 invalid=2 new=2 with_site=6`.

### 1.2 `scripts/kb_seed_common.py` (440 lines)

| line | what |
|---|---|
| 19-21 | docstring: "The five KB table names below are the only kb_* relation literals of G2 and kb_leaf is the only importer of the S81-14 leaf" |
| 39-42 | `MODE_OFF / MODE_DRY / MODE_APPLY`, `_TRUTHY` |
| 47 | `WRITE_BATCH = 100` |
| 50-55 | `KB_PRODUCTS_TABLE` .. `KB_GAPS_TABLE`, `LLM_SPEND_LEDGER_TABLE` |
| 67-79 | `run_mode(flag_name)`: FIRST statement `os.getenv(flag_name, "false").strip().lower()`; `apply` -> APPLY; truthy -> DRY; else OFF |
| 82-84 | `cli_mode(mode, dry_run)` |
| 92-117 | `_knob_value`, `int_knob(name, default, low, high)`: unusable -> default; 0 -> default when low > 0; else `min(max(int(v), low), high)` |
| 132-139 | seams `_admin_client()`, `_now()` |
| 142-144 | `kb_leaf()`: the function-local `from app.services import kb_service as _kb` (P01_ALLOWED) |
| 151-162 | `log_counts` (ints only, `"%s totals %s"`), `write_report` (ASCII JSON, LF, sorted keys, `ensure_ascii=True`) |
| 165-175 | `resolve_client` |
| 302-339 | `PoliteFetcher.get` (`_fetch_following` with the SSRF validator per hop, `allow_redirects=False`, the named headers) |
| 360-440 | `KbWriter`: `_built` (a row whose key set != `KB_BUILDER_KEYS[table]` is counted `not_built`, never sent), `_send` (`upsert(batch, on_conflict=..., ignore_duplicates=True)` in batches of 100, inserted rows = the response data), `offers` / `gaps` (insert-ignore then ONE update per non-returned row: the model for `brands`), `ledger` |

### 1.3 The leaf `app/services/kb_service.py` (806 lines)

| line | what |
|---|---|
| 55-58 | `KB_TABLES` = the ten 045 tables, in 045 order |
| 60-97 | `KB_COLUMNS` per table (the 045 column order) |
| 100-102 | `KB_UUID_ID_TABLES` |
| 106-112 | `KB_BUILDER_KEYS` = columns minus `created_at` and minus a uuid `id` (derived from KB_COLUMNS) |
| 115 | `KB_HOST_REGEX` |
| 122 | `KB_HOST_TOP_LABEL_REGEX` |
| 154 | `KB_OFFER_UPSERT_SET` (the model for `KB_BRAND_UPSERT_SET`) |
| 166-178 | `kb_deny_label_group()`, `kb_host_deny_regex()` = `(^|[.])(basenotes|fimgs|fragrantica|parfumo)[.]` (built from `deny_hosts.DENY_LABELS` at call time; measured text) |
| 181-200 | `_sql_match` (PostgreSQL `~` emulation, `$` -> `\Z`), `_top_label_ok`, `_belted_host` = host regex AND top label AND NOT the deny belt |
| 215-220 | `kb_source_allowed(value)` = `deny_hosts.kb_source_allowed` read at CALL time, False on exception |
| 339-354 | `_str_len`, `_opt_len`, `_is_int`, `_ts_iso` (aware datetime -> isoformat, else None) |
| 383-398 | `_pg_text_ok` (no NUL, no lone surrogate, recursively) |
| 466-520 | `build_merchant_row` (the builder model: `try:` ... `except Exception: return None`) |
| 724-754 | `build_gap_row` (the `source_hint` host belt + `kb_source_allowed`) |
| 786-805 | `build_coverage_row` (the last builder; the new builder goes after it) |

Imports (`:38-51`): stdlib + `deny_hosts`, `price_service`, `result_gate`, `spec_spine_service` at top (R21 `test_s14_r21_leaf_pure` :1223 holds this set); the new builder needs no new import.

### 1.4 Migrations

- Files at base: `migrations/` ends `...044_apple_siwa_tokens.sql, 045_kb_core.sql, 047_012_revoke.sql, 050_llm_spend_ledger.sql, add_share_token.sql`; `rollback/` ends `044, 045, 047, 050`. 046 / 048 / 049 are reserved by PLAN_S81 (SF1, S81-22); 050 is the ledger: **051 is the next free number** (Q4).
- 045 (`migrations/045_kb_core.sql`, 530 lines, CRLF wc / LF blob): `BEGIN` :60; the PG15 DO guard :62-68; `kb_set_updated_at()` :90-100 (plpgsql, SECURITY INVOKER, `SET search_path TO 'public'`); `kb_products.brand text NOT NULL CHECK (char_length(brand) BETWEEN 1 AND 128)` :137 (free text, no FK target exists); the kb_gaps `source_hint` host-or-URL belts + deny belts :283-296; the indexes :319-339 (partial `WHERE gtin IS NOT NULL` form :321); the three `CREATE OR REPLACE TRIGGER ... BEFORE UPDATE ... EXECUTE FUNCTION public.kb_set_updated_at()` :341-349; RLS :484-493; `REVOKE ALL ON TABLE ... FROM PUBLIC, anon, authenticated, service_role` :495-505; `GRANT SELECT, INSERT, UPDATE, DELETE ... TO service_role` :507-516; the function REVOKE / GRANT EXECUTE :519-528; `COMMIT` :530. LF sha256 of the 045 text: `ba853c75a98953e5ca40ba06ffd92fe3acf4a7f6ceb9c19ea5ffd7339f867075`; of `rollback/045_kb_core.sql`: `4a7fcbabc946e5dfbea8e2180dfe8e7ceaa91a8afc439f803dac050eae9043ba`.
- `rollback/045_kb_core.sql` :24 `DROP FUNCTION IF EXISTS public.kb_set_updated_at();` WITHOUT CASCADE: once 051 is applied, a 045 rollback run first fails with 2BP01 (the kb_brands trigger depends on the function) inside its transaction and changes nothing. Hence the ordering rule "roll back 051 before 045" in both 051 headers (stated limit L5; the 045 rollback stays frozen: `test_s14_r16_rollbacks` :1138 pins its statements).
- 050 (`migrations/050_llm_spend_ledger.sql`, 76 lines): the header shape (purpose, "MERGING THIS CHANGES NOTHING IN PRODUCTION", "APPLY ORDER", the service-role paragraph, the postcheck + rollback pointers), `BEGIN` / `COMMIT`, `COMMENT ON TABLE`. `rollback/050` :1-13: header + `BEGIN; DROP TABLE IF EXISTS ...; COMMIT;`.
- The APPLY files live in the docs state folder (`specs/APPLY_045_1_PRECHECK.sql` .. `APPLY_050_3_POSTCHECK.sql`); not in the repo.

### 1.5 Pins and guards the new code must not trip (measured)

| pin | file:line | what it reads | effect on this unit |
|---|---|---|---|
| P01 no kb_service importer | `tests/test_s81_kb_schema.py:331-389` | app/ + scripts/ AST | the brand script reaches the leaf ONLY through `common.kb_leaf()` (it already does, `seed_kb_brands_wikidata.py:59`); no new importer |
| P02 no kb_* relation literal | `:338-406` | string constants in `KB_RELATION_NAMES` = the TEST's own `KB_TABLE_NAMES` (:55-58) + view + functions | `"kb_brands"` is NOT in that set, so the new `KB_BRANDS_TABLE = "kb_brands"` line does not trip it; the RED row B12 carries the kb_brands literal census instead (no frozen-pin edit) |
| P05 sqlfluff skip limit | `:453-460` | `.sqlfluff` | limit 0: 051 is linted |
| R27 builder keys | `:1477-1488` | `tuple(KB_TABLES) == KB_TABLE_NAMES` (the ten) | RED at head without E1 (10 nodes): the deliberate change E1 |
| R21 leaf pure | `:1223` | the leaf's imports | no new import |
| R16 045 rollback statements | `:1138` | rollback/045 | unchanged (L5) |
| 043 fence + census | `tests/test_migration_043_delete_user_cascade.py:368-372` `PERSONAL_RX`, `:410` `real_forward_files` | every forward migration | probed with the draft 051 added: gaps `set()`, no kb_* user table, `KNOWN_USER_TABLES` equal (scratch run, 1.10) |
| index predicates immutable | `tests/test_migration_index_predicate_immutability.py:52-94` | every migration | draft predicate ` official_host IS NOT NULL`: volatile hits `[]` |
| 037 SECURITY DEFINER census | `tests/test_migration_037_security_definer_grants.py:295-299` | forward + rollback | 051 has no function: nothing to census |
| w1_2d grants estate-wide | `tests/test_retro_w1_2d.py:287` | forward + rollback | no GRANT to anon / PUBLIC in 051 |
| share_token width | `tests/test_security_regression.py:1010` | forward | no share_token column |
| G2 R27 hygiene | `tests/test_s81_s16_kb_seed.py:1092-1112` | the five G2 scripts' BYTES | ASCII; no `impersonate`, `Qaren` + `Bot`, `NAMED` + `_AGENT`, `claude` + `-`, `/v1/` + `messages`; no `.table('kb_` outside kb_seed_common; `logger.error` only inside except arms. The new script text must keep all of these. Its `b"\r" not in raw` clause is RED on this Windows checkout for all five scripts at base (the F1-3 environmental limit recorded in CLAUDE.md :550) |
| G2 R02 OFF inert | `:396-423` | the OFF record of BOTH G2 seed scripts: exactly one INFO record containing `ENABLE_KB_SEED` | the new OFF line names BOTH flags (2.2), so R02's 7 brand nodes stay green UNEDITED |
| G2 R23 / R24 | `:991-1013` / `:1016-1027` | brand script keyed on `ENABLE_KB_SEED` (`_dry`) | RED at head without EK1 / EK2 (5 nodes) |
| railway watch patterns | `railway.kbseed.json`, `railway.feedwalker.json`, `railway.pdpdiscovery.json` | `scripts/kb_seed_common.py` is in all three `watchPatterns` | editing kb_seed_common re-deploys (= re-runs) the three G2 jobs in whatever mode their flags hold (the #98 lesson; CLAUDE.md :551 step 11; stated limit L6 + owner step 0) |
| fourteen client fences | `SmartCompareApp/__tests__` | repo-root files by path | grep at base: no suite reads CLAUDE.md, migrations/, kb_service, kb_seed_common or the brand script (mentions in comments only): no fence literal moves |

### 1.6 Flag idiom, libraries, line endings

- Mode idiom: `kb_seed_common.run_mode(FLAG)` (1.2) is the FIRST statement of `main`; nothing else changes in the reader. `ENABLE_KB_SEED` keeps being read only by `scripts/seed_kb_batch.py` (its `FLAG`).
- Libraries on `.venv-qaren`: stdlib only for the new code; `sqlfluff==4.3.0` (`requirements-dev.txt:140`, `python -m sqlfluff --version` -> 4.3.0) for the B11 lint row (importable as `sqlfluff`).
- Line endings: every touched file is `i/lf w/crlf` (`git ls-files --eol`: CLAUDE.md, kb_service.py, kb_seed_common.py, the brand script, 045, 050, both test files). GREEN edits with the Edit tool (CRLF preserved) and writes NEW files LF + ASCII (the house; git normalises). A whole-file diff is a defect.
- Local PostgreSQL: `C:/Program Files/PostgreSQL/18` exists (the S81-14 GC-8 precedent measured 045 on a throwaway PostgreSQL 18.1); NOT run in this spec (GREEN gate G9).

### 1.10 Base pass state (bounded runner, flags unset)

`tests/test_s81_kb_schema.py` (529 nodes), `tests/test_s81_s16_kb_seed.py` (140), `tests/test_s81_g2_gate_rows.py` (9), `tests/test_sqlfluff_config.py` (11), `tests/test_migration_index_predicate_immutability.py` (46), `tests/test_migration_043_delete_user_cascade.py` (51), `tests/test_migration_044_apple_siwa_tokens.py` (8) -> **5 failed, 789 passed**; the five = `test_s16_r27_hygiene_of_g2_files[kb_seed_common|seed_kb_batch|seed_kb_brands_wikidata|cron_feed_walker|cron_pdp_discovery]` (the CRLF working copy, F1-3, environmental; CI on the LF blobs is green).
`[pyt] tag=s16b-spec-base1 start=2026-11-04 19:09:50 end=2026-11-04 19:11:21 elapsed=91s bound=1200s status=FAIL rc=1`; `[hermeticity] sentinel checked 794 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
Collection: `[pyt] tag=s16b-spec-collect start=2026-11-04 19:17:55 end=2026-11-04 19:17:59 elapsed=4s bound=600s status=OK rc=0` (R23 2 nodes, R24 3 nodes, R27 of the schema file 10 nodes).
Scratch probes (venv python, `PYTHONDONTWRITEBYTECODE=1`, the worktree read-only): the draft 051 + rollback `sqlfluff lint --config <worktree>/.sqlfluff` -> "All Finished!" rc 0; both 0 bytes > 127, 0 CR, no 8-digit run, longest line 138; the 043 fence with the draft added -> gaps `set()`; the index-predicate detector -> `[]`; `proto_builder.py` (the builder of 2.4 over the leaf's helpers) -> every row of the 5.2 K03 table refused / accepted as listed (`proto/proto_builder.out`). The node probe before the run: `node -e 0` 2.4 s (a loaded box; one gate at a time).

## 2. Contract

### 2.1 Flag, knob, modes (Q1)

| `ENABLE_KB_BRANDS` | mode | effect |
|---|---|---|
| unset, "", garbage, false, 0, no, off, dry | OFF | ONE INFO `"[KB_BRANDS] mode=off ENABLE_KB_BRANDS not set; skipping run (ENABLE_KB_SEED does not run this script)"`, return 0, BEFORE argv parsing, the client, any fetch or file I/O |
| true, 1, yes, on (any case / padding) | DRY | robots GET, ONE SPARQL GET, the host derivation (unchanged), the brand derivation, the counts, `--report`; NO table write |
| apply (strip + lower) | APPLY | DRY + the `kb_brands` write (2.5); `--dry-run` downgrades to DRY |

`KB_BRANDS_MAX` = `common.int_knob("KB_BRANDS_MAX", 300, 1, 5000)`, read per call by `brands_max()` inside `_run` (never at import): unset / blank / garbage / inf / nan / negative / 0 -> 300; > 5000 -> 5000; "7.9" -> 7. It caps the BRAND ROWS; `MAX_BRAND_HOSTS = 300` stays the constant cap of the report's host list (R-G2-3, R23 unchanged on that point).

Q1 (the flag), answered with measurements: the brand script moves to `ENABLE_KB_BRANDS`. (a) `railway.kbseed.json` runs `python -m scripts.seed_kb_batch` only (startCommand, measured); the brand script is an operator's one-off command on that service, and the owner's G2 step (7) sets `ENABLE_KB_SEED=apply` there for the batch run, so a shared flag would turn the owner's later "brand DRY count" command into a kb_brands WRITE; (b) R-G2-3's sentence ("ENABLE_KB_SEED never writes brands") stays literally true; (c) the cost is two frozen-row amendments (EK1 / EK2) plus the autouse list (EK0); R02 stays unedited because the OFF line names both flags. The alternative (keep ENABLE_KB_SEED) saves EK0-EK2 but couples the batch seeder's APPLY to the brand write: rejected.

### 2.2 Log lines (constants and ints only; never a label, a host or a URL)

- OFF: the line of 2.1 (one record; level INFO).
- mode: `"%s mode=%s (apply writes kb_brands; dry writes nothing)"` (PREFIX, mode).
- existing lines kept verbatim: `kb_merchants read failed (%s)` WARNING, `robots unreadable; nothing read` INFO, `robots disallow the query endpoint; nothing read` INFO, `query failed status=%d` INFO, `query body unreadable (%s)` WARNING.
- NEW: `"%s kb_brands write failed (%s)"` WARNING with `type(exc).__name__`, inside the except arm (never ERROR: an expected owner-precondition failure, e.g. 051 not applied).
- totals: `common.log_counts(PREFIX, counts)` once at the end (ints only).

### 2.3 The SPARQL query (Q2)

```
SELECT DISTINCT ?brand ?site ?label_en ?label_ar WHERE {
  ?brand wdt:P1056 wd:Q131746 . ?brand wdt:P856 ?site .
  FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 . }
  OPTIONAL { ?brand rdfs:label ?label_en . FILTER(LANG(?label_en) = "en") }
  OPTIONAL { ?brand rdfs:label ?label_ar . FILTER(LANG(?label_ar) = "ar") }
} ORDER BY ?brand ?site LIMIT 2000
```
(one Python string, ASCII, built as today; `SPARQL_LIMIT = 2000` a named constant used in the text.)

- Labels: OPTIONAL `rdfs:label` with an exact `LANG(...) = "xx"` filter, NOT the `SERVICE wikibase:label` form: the label service falls back to the bare item id ("Q123") when an item has no label in the language, which would store an id as a brand name; the OPTIONAL form yields an unbound variable (-> None). A Wikidata item has at most one label per language code (offline knowledge of the data model, unverified here), so the OPTIONALs do not multiply rows; regional codes (en-gb, en-ca) and the `mul` default label are NOT matched by `= "en"` (stated limit L2: an item labelled only in `mul` is counted `no_label_en` and skipped).
- `FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 }` excludes items that are instances of human (Q5): the schema-and-data lens (no person's name stored as a brand). It also removes such items from the G2 host list (a deliberate, stated change: a person's official site is no merchant candidate either; L3).
- `ORDER BY ?brand ?site` makes a truncation at LIMIT deterministic; `counts["sparql_limit_hit"] = 1` when the binding count equals `SPARQL_LIMIT` (else the key is absent): the owner reads it in the DRY line.
- The ids P1056 / Q131746 / P856 / P31 / Q5 and the `rdfs:` prefix are offline-unverified (S16 L7 kept): the DRY counts (`bindings`, `with_label_en`, `with_label_ar`) are the owner's check before any APPLY.
- Expected row count under LIMIT 2000: NOT MEASURABLE offline (no network). The bound is 2,000 (brand, site) pairs; distinct brands <= that; brand rows <= `KB_BRANDS_MAX` (300 default). The G2 DRY count has never been run (045 unapplied; no ledger line names it).

### 2.4 The builder (kb_service, pure)

New constants (after `KB_OFFER_UPSERT_SET` :154):
- `KB_QID_REGEX = "^Q[1-9][0-9]{0,11}$"` (equal, as text, to the 051 CHECK; a leading zero is refused: `Q01` and `Q1` would otherwise be two primary keys for one item. The brief's `^Q[0-9]{1,12}$` admits `Q0` / `Q01`; ruled tighter here, Q-open 11.1).
- `KB_BRAND_SOURCES: Tuple[str, ...] = ("wikidata", "operator")`.
- `KB_BRAND_UPSERT_SET: Tuple[str, ...] = ("label_en", "label_ar", "official_host", "updated_at")` (what a Wikidata re-run sets; never qid, source, created_at).
- `KB_TABLES` gains `"kb_brands"` LAST (the ten 045 tables keep their order); `KB_COLUMNS["kb_brands"] = ("qid", "label_en", "label_ar", "official_host", "source", "created_at", "updated_at")`; `KB_BUILDER_KEYS["kb_brands"]` (derived) = the same minus `created_at`; `kb_brands` NOT in `KB_UUID_ID_TABLES`.

```
def build_brand_row(*, qid, label_en, updated_at, label_ar=None, official_host=None,
                    source="wikidata") -> Optional[Dict[str, Any]]
```
Inside `try:` (`except Exception: return None`): `upd = _ts_iso(updated_at)`; refuse unless `_pg_text_ok((qid, label_en, label_ar, official_host, source))`; then ALL of: `_sql_match(KB_QID_REGEX, qid)`; `_str_len(label_en, 1, 128)`; `_opt_len(label_ar, 1, 128)`; `official_host is None or (_str_len(official_host, 1, 253) and _belted_host(official_host) and kb_source_allowed(official_host))`; `source in KB_BRAND_SOURCES`; `upd is not None`. Returns `{"qid", "label_en", "label_ar", "official_host", "source", "updated_at": upd}` (key set == `KB_BUILDER_KEYS["kb_brands"]`). No strip, no case folding inside the builder (the script normalises; the builder only refuses). `_belted_host` = the 051 host CHECK (regex + top label + deny belt); `kb_source_allowed` = the deny RULE (a superset of the belt: it also refuses hyphenated / path / top-level label tokens, measured: `fragrantica-shop.example.com` passes the belt and fails the rule).

### 2.5 The script (APPLY write, idempotent re-run: Q5)

New / changed symbols in `scripts/seed_kb_brands_wikidata.py`:
- `FLAG = "ENABLE_KB_BRANDS"`; `MAX_KNOB = "KB_BRANDS_MAX"`; `SPARQL_LIMIT = 2000`; `SPARQL` (2.3); `brands_max() -> int`.
- `qid_of(binding) -> Optional[str]`: `brand.value` as str, the last `/`-segment (`http://www.wikidata.org/entity/Q42` -> `Q42`; a bare `Q42` stays), else None. Validity is the builder's.
- `_label(binding, key) -> Optional[str]`: the `value` string stripped; "" -> None.
- `_brand_host(site) -> Optional[str]`: `dh.normalize_host(urlsplit(site).hostname or "")` (the same normalisation as `derive_hosts`), None on ValueError / empty; validity is the builder's.
- `derive_brands(bindings, counts, now, cap) -> List[Dict]` (pure apart from the leaf): group the bindings by `qid_of` (`bad_qid` counted per binding whose qid is None or fails `KB_QID_REGEX`); per qid: `label_en` = the first non-None en label, `label_ar` = the first non-None ar label; the host = the SMALLEST (string order) host among the qid's sites for which `build_brand_row(..., official_host=h)` is not None, else None (`brand_host_null` counted); `label_ar` failing the builder alone (over 128, NUL, lone surrogate) -> None, counted `label_ar_dropped`; a qid with no usable `label_en` -> no row, counted `no_label_en`; `with_label_en` / `with_label_ar` = distinct qids carrying that label; rows built with `source="wikidata"`, `updated_at=now` (ONE `common._now()` per run); a builder refusal -> `not_built`; sort the built rows by `int(qid[1:])` ascending; `brand_rows` = min(len, cap), `over_cap_brands` = the excess (key absent when 0); return the first `cap`.
- `_run(args, client, mode)`: as today up to `derive_hosts` (unchanged code and order); then `rows = derive_brands(bindings, counts, common._now(), brands_max())`; in APPLY: `try: writer = common.KbWriter(client); writer.brands(rows)` then `counts.update(writer.counts)` (`kb_brands_sent`, `brand_updates`, `not_built`); `except Exception as exc:` WARNING `kb_brands write failed (%s)` + `counts["write_failed"] = 1` (the rows of earlier batches stand); then `common.write_report(args.report, {"hosts": hosts, "brands": [{k: r[k] for k in ("qid", "label_en", "label_ar", "official_host")} for r in rows], "counts": counts})` and `common.log_counts`. The report is ASCII JSON (Arabic escaped by `ensure_ascii=True`).
- `main`: as 2.1; passes the resolved mode to `_run`.
- Docstring rewritten (no "DRY-ONLY", no "writes NOTHING ... in any mode").

`scripts/kb_seed_common.py`:
- `KB_BRANDS_TABLE = "kb_brands"` beside the five (`:50-54`); the docstring's "five KB table names" -> "six".
- `KbWriter.brands(rows) -> int`: `built = self._built(KB_BRANDS_TABLE, rows)`; `inserted = self._send(KB_BRANDS_TABLE, built, "qid")`; `seen = {r.get("qid") for r in inserted}`; for each built row whose qid is not in `seen` and whose `source == "wikidata"`: `self.client.table(KB_BRANDS_TABLE).update({k: row[k] for k in kb.KB_BRAND_UPSERT_SET}).eq("qid", row["qid"]).eq("source", "wikidata").execute()`; `self.counts["brand_updates"] += n`; returns n. No delete, no select.

Idempotency (Q5): run 1 inserts every row (the upsert returns them: no update). Run 2 over the same Wikidata answer: the insert-ignore inserts nothing, PostgREST returns `[]` (R-G2-12: inserted rows only, unmeasurable offline), so every row gets ONE update that re-sets the four columns (values equal; `updated_at` moves, by the builder and the 045 trigger). A changed label / host in Wikidata is mirrored; a label that disappeared becomes NULL (label_ar) or the brand is skipped (label_en: no row built, so its stored row keeps the old label: L4); a brand gone from Wikidata is never deleted; an `operator` row is never updated (the `.eq("source", "wikidata")` filter) and never inserted over (insert-ignore). If PostgREST returned the conflicting rows too (the unmeasured alternative), run 2 would make NO update and labels would never be refreshed: the owner's canary (8.2 step 6) reads it.

### 2.6 The migration (051; Q3, Q4)

The text measured in `proto/migrations/051_kb_brands.sql` (sha256 `946965cf...648dba`, 4,273 bytes, sqlfluff 4.3.0 clean under the repo config) and `proto/migrations/rollback/051_kb_brands.sql` (sha256 `c9225ca8...984963`, 598 bytes, clean). GREEN copies both VERBATIM (wording of the header may tighten; every statement and every pinned header phrase of 5.1 B10 stays). Statements in order:
1. `BEGIN`;
2. `DO $$ ... IF to_regprocedure('public.kb_set_updated_at()') IS NULL THEN RAISE EXCEPTION '051 needs 045 applied first ...' ... $$` (the 045 dependency made explicit; PG15 is already 045's guard);
3. `CREATE TABLE IF NOT EXISTS public.kb_brands (` `qid text PRIMARY KEY CHECK (qid ~ '^Q[1-9][0-9]{0,11}$')`, `label_en text NOT NULL CHECK (char_length(label_en) BETWEEN 1 AND 128)`, `label_ar text CHECK (label_ar IS NULL OR char_length(label_ar) BETWEEN 1 AND 128)`, `official_host text CHECK (official_host IS NULL OR (char_length(official_host) BETWEEN 1 AND 253 AND official_host ~ '<KB_HOST_REGEX>' AND official_host !~ '<kb_host_deny_regex()>'))`, `source text NOT NULL DEFAULT 'wikidata' CHECK (source IN ('wikidata', 'operator'))`, `created_at timestamptz NOT NULL DEFAULT now()`, `updated_at timestamptz NOT NULL DEFAULT now()`, `CONSTRAINT kb_brands_host_top_label_letter CHECK (official_host IS NULL OR official_host ~ '<KB_HOST_TOP_LABEL_REGEX>')` `)`;
4. `CREATE INDEX IF NOT EXISTS idx_kb_brands_official_host ON public.kb_brands (official_host) WHERE official_host IS NOT NULL`;
5. `CREATE OR REPLACE TRIGGER kb_brands_set_updated_at BEFORE UPDATE ON public.kb_brands FOR EACH ROW EXECUTE FUNCTION public.kb_set_updated_at()`;
6. `ALTER TABLE public.kb_brands ENABLE ROW LEVEL SECURITY`;
7. `REVOKE ALL ON TABLE public.kb_brands FROM PUBLIC, anon, authenticated, service_role`;
8. `GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_brands TO service_role`;
9. `COMMENT ON TABLE public.kb_brands IS '... Wikidata (CC0) ... No user data. Service role only.'`;
10. `COMMIT`.
Rollback: `BEGIN; DROP TABLE IF EXISTS public.kb_brands; COMMIT;` (the trigger, index and checks go with the table; `kb_set_updated_at` is 045's and is KEPT).

Q3 (the column set, UNIQUE): exactly the brief's columns; `official_host` is NOT unique (a house and a sub-brand share a site; Wikidata also lists one site on several items): a plain partial index serves the host -> brands lookup; two rows sharing a host are both kept. No `aliases`, no product link, no FK (kb_products.brand stays free text, 045 :137). No `wikidata_revision` / `fetched_at` column (updated_at is the observation time).
Q6 (FOCUS surfaces): the migration ONLY. No auth / quota / legal / consent / security middleware / Redis / client / secret surface; the leaf builder and the script are SAFE-class. The second adversary lens = schema-and-data: the RLS / REVOKE pattern (the 037 both-readings rule: REVOKE from service_role too, then the explicit GRANT), the rollback (and its order against 045), the builder belts mirroring every CHECK, CC0 licensing (Wikidata structured data is CC0; no attribution duty; the source column records provenance), no personal data (no user column, the human exclusion, the 043 fence).

### 2.7 Failure table

| where | condition | behaviour |
|---|---|---|
| main | flag OFF (any OFF spelling), whatever ENABLE_KB_SEED / KB_BRANDS_MAX / SUPABASE_* hold | one INFO naming both flags; rc 0; no client factory, no fetch, no open(), no event |
| main | no service-role client | `resolve_client` WARNING (type name); rc 0 |
| _run | kb_merchants read raises | WARNING (type name); rc 0; no fetch |
| _run | robots non-2xx / timeout / disallow for QarenBot or '*' | INFO (robots); rc 0; ONE GET only (R24 / EK2) |
| _run | SPARQL non-2xx | INFO status; rc 0; no write |
| _run | SPARQL body not JSON / no results.bindings | WARNING (type name); rc 0; no write |
| derive | bindings not a list | zero rows; counts as built |
| derive | binding without brand / bad qid / no en label | counted (`bad_qid`, `no_label_en`); no row |
| derive | site denied / IP literal / invalid | the row is kept with `official_host = None` (`brand_host_null`) |
| derive | over the cap | the lowest numeric qids kept; `over_cap_brands` |
| APPLY | upsert or update raises (incl. 051 not applied) | WARNING `kb_brands write failed (<Type>)`; `write_failed=1`; earlier batches stand; report + totals still written; rc 0 |
| any | `--dry-run` with apply | DRY (no write) |

### 2.8 Flag-OFF identity (the main invariant)

- With `ENABLE_KB_BRANDS` OFF the script performs NO I/O and emits exactly one INFO record, independent of `ENABLE_KB_SEED` (all modes), `KB_BRANDS_MAX` and the SUPABASE_* names (S02).
- No `app/` request path changes by construction: the only `app/` diff is additive in the leaf (two constants, one tuple entry, one dict entry, one function), whose importers (P01) are flag-gated off-clock code; no `app/` file names `ENABLE_KB_BRANDS`, `KB_BRANDS_MAX` or the brand script (PIN-4); `kb_ingest`'s writes key `KB_BUILDER_KEYS` by its own five table names (unchanged values).
- `seed_kb_batch.py`, `cron_feed_walker.py`, `cron_pdp_discovery.py` are byte-unchanged; their flags are untouched; `KbWriter`'s existing methods are byte-unchanged (only the class gains `brands` and the module one constant).
- `derive_hosts` is byte-unchanged; the report's `hosts` list is unchanged for every binding set without human items (PIN-2 records the base output as a literal).

### 2.9 Test seams (production values in brackets)

`common._admin_client` [the service-role client], `common._now` [`datetime.now(timezone.utc)`], `common.PoliteFetcher(fetch=, validate=, sleep=)` [`robots_registry.default_fetch` / `default_validate` / `asyncio.sleep`], `kb_service.kb_source_allowed` via `deny_hosts.kb_source_allowed` [the deny rule], env `ENABLE_KB_BRANDS` [unset], `KB_BRANDS_MAX` [unset = 300]. The G2 harness (`Rig`, `FakeClient`, `FakeQuery`, `_merchant`) is reused by import of `tests.test_s81_s16_kb_seed` (module object only; the G2 gate-rows precedent).

## 3. Change list (GREEN, in order; byte-copy every existing file first into `<scratchpad>/S81-16b_green_before/` with sha256)

1. NEW `migrations/051_kb_brands.sql` (2.6; LF, ASCII; from the proto file).
2. NEW `migrations/rollback/051_kb_brands.sql` (2.6).
3. `app/services/kb_service.py`: `KB_TABLES` + `"kb_brands"` last (:55-58); `KB_COLUMNS["kb_brands"]` after `kb_coverage_daily` (:96); the three constants of 2.4 after `KB_OFFER_UPSERT_SET` (:154); `build_brand_row` after `build_coverage_row` (:806). No other line.
4. `scripts/kb_seed_common.py`: `KB_BRANDS_TABLE` after `KB_GAPS_TABLE` (:54); docstring "five" -> "six" (:19); `KbWriter.brands` after `gaps` (:437). No other line.
5. `scripts/seed_kb_brands_wikidata.py`: 2.5 (docstring, FLAG, the constants, SPARQL, the new helpers, `derive_brands`, `_run(args, client, mode)`, the OFF / mode lines). `derive_hosts`, `_site_host`, `sparql_url`, `_parse_args` byte-unchanged.
6. `tests/test_s81_s16_kb_seed.py`: EK0, EK1, EK2 exactly as 4.1 (no other edit; the docstring's row counts unchanged).
7. `tests/test_s81_kb_schema.py`: E1 exactly as 4.1.
8. NEW `tests/test_s81_s16b_kb_brands.py` = the frozen RED file (written by the RED agent, byte-identical at GREEN).
9. `CLAUDE.md`: 8.1 (in place, CRLF kept).
No other file. (The APPLY_051 files and the DEFECT_LEDGER row are filed in the docs state folder by the orchestrator from 8.3 / 8.4 and `proto/APPLY_051_*.sql`.)

## 4. Existing pins

### 4.1 Deliberate changes (one row each)

| id | file:line | before | after | why |
|---|---|---|---|---|
| EK0 | `tests/test_s81_s16_kb_seed.py:54` (`_env` autouse) | `for name in ("ENABLE_KB_SEED", "ENABLE_LLM_SPEND_BREAKER", "ANTHROPIC_API_KEY") + KNOBS:` | `for name in ("ENABLE_KB_SEED", "ENABLE_KB_BRANDS", "KB_BRANDS_MAX", "ENABLE_LLM_SPEND_BREAKER", "ANTHROPIC_API_KEY") + KNOBS:` | the brand rows now depend on the new names; hermeticity |
| EK1 | `:982-988` `_brand_bindings` and `:991-1013` R23 | bindings without labels, qids from Q0; `_dry(monkeypatch, mode)` (ENABLE_KB_SEED); `assert rig.client.writes() == []` in both modes | `_brand_bindings` adds `"label_en": {"value": "Brand %d" % i}` to every binding and numbers qids from Q1 (`"Q%d" % (i + 1)`); R23 sets `monkeypatch.setenv("ENABLE_KB_BRANDS", mode)` AND `monkeypatch.setenv("ENABLE_KB_SEED", "apply")` instead of `_dry`; the write assertion becomes `writes = rig.client.writes()`, `if mode == "true": assert writes == []` `else: assert writes and {w[0] for w in writes} == {"kb_brands"} and {w[1] for w in writes} <= {"upsert", "update"}`; every other R23 line unchanged (the two GETs, the validator, the headers, the 300 sorted hosts, the exclusions) | the brief's EK1: R23 keyed on the script's new flag; DRY = no write; APPLY = kb_brands rows only, never kb_merchants (S-M20 stays killed) |
| EK2 | `:1016-1027` R24 | `_dry(monkeypatch)` | `monkeypatch.setenv("ENABLE_KB_BRANDS", "true")` (and nothing else) | R24 drives the brand script; under ENABLE_KB_SEED alone the script is now OFF (zero GETs) and the row would go red for the wrong reason |
| E1 | `tests/test_s81_kb_schema.py:1488` (R27, 10 nodes) | `assert tuple(_attr(kb, "KB_TABLES")) == KB_TABLE_NAMES` | `assert tuple(_attr(kb, "KB_TABLES")) == KB_TABLE_NAMES + ("kb_brands",)  # S81-16b E1: 051 joins the census last` | the leaf census now holds the 051 table; the 045 ten stay first and in order (PIN-3 keeps that half) |

R02 (`:396-423`), P01 / P02, R16, R21, the G2 gate rows and every other pin stay UNEDITED (2.2 keeps R02's message clause true).

### 4.2 Must stay green and unedited

Every node of the comm set (7.1) except the 15 E-row nodes above, which go green at head WITH their edits; in particular: `tests/test_s81_kb_schema.py` (529 nodes, all but R27 unedited), `tests/test_s81_s16_kb_seed.py` R01-R22, R25-R30, P01-P06 (R27's five nodes stay environmentally red on a CRLF checkout, green in CI), `tests/test_s81_g2_gate_rows.py` (9), `tests/test_s81_d09_feed_walker.py`, `tests/test_s81_d11_pdp_discovery.py`, `tests/test_s81_s17_kb_ingest.py`, `tests/test_s81_s15_registry_robots.py`, `tests/test_migration_043_delete_user_cascade.py` (51), `tests/test_migration_index_predicate_immutability.py` (46), `tests/test_migration_037_security_definer_grants.py`, `tests/test_retro_w1_2d.py`, `tests/test_retro_w1_2c.py`, `tests/test_sqlfluff_config.py` (11), `tests/test_security_regression.py`, `tests/test_secret_scan_static.py`, `tests/test_ci_gates.py`, `tests/test_behavior_dimension_translation.py` and the three other CLAUDE.md readers (`test_s81_s04_spend_breaker.py`, `test_s81_s08b_legacy_fingerprint.py`, `test_s81_s23_bypass_retire.py`).

## 5. RED tests: `tests/test_s81_s16b_kb_brands.py` (new; pure ASCII, LF; hermetic)

Harness: `from tests import _retro_r_mig_sql as _sql`, `from tests import test_migration_043_delete_user_cascade as t043`, `from tests import test_migration_index_predicate_immutability as timm`, `from tests import test_s81_s16_kb_seed as s16` (module objects only). Autouse: `import app.main` FIRST (the dotenv hazard), delete `ENABLE_KB_BRANDS`, `KB_BRANDS_MAX`, `ENABLE_KB_SEED` + `s16.KNOBS`, set synthetic `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` built at run time; the netguard (`_sql.install_network_guard`, attempts asserted empty). Missing files / symbols read through `_require(path)` / `_attr(obj, name)` / `s16._mod(name)` helpers, so a base run fails on an AssertionError only. Synthetic bindings built at run time: `_bind(qid, site, en=None, ar=None)` -> `{"brand": {"value": "http://www.wikidata.org/entity/" + qid}, "site": {"value": site}, "label_en": {...}, "label_ar": {...}}` (label keys only when given); Arabic labels from code points (`chr(0x645) + chr(0x64a) + ...`). Every script row runs with the FULL configuration (B1): `ENABLE_KB_SEED=apply`, `KB_BRANDS_MAX` set where the row does not vary it, the s16 `Rig` recorders (client factory, fetch, validate, sleep, events, writes). Fixtures from the brief (no tester scenario applies: eval_regression.json carries compare pairs, not brand entities).

### 5.1 The migration (B rows: RED at base = the files are missing)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| B01 | `test_s16b_b01_files_exist_once` | exactly one `migrations/051_*.sql` named `051_kb_brands.sql` and one `rollback/051_*.sql` of the same name | RED (none) | 3.1 / 3.2 |
| B02 | `test_s16b_b02_one_transaction` | for both files the first top-level statement (comments stripped, dollar bodies blanked: `_sql.code_only`) is `BEGIN`, the last `COMMIT`, no other BEGIN / COMMIT / ROLLBACK | RED | 3.1 / 3.2 |
| B03 | `test_s16b_b03_columns_match_the_leaf` | the compact column items of `kb_brands` (the `t043._balanced` / `_split_top` parse) equal the literal list of 2.6 step 3, in order, AND their names equal `kb_service.KB_COLUMNS["kb_brands"]` | RED | 3.1 / 3.3 |
| B04 | `test_s16b_b04_regex_texts_equal_the_leaf` | the qid CHECK literal == `KB_QID_REGEX`; the host `~` literal == `KB_HOST_REGEX`; the `!~` literal == `kb_host_deny_regex()`; the top-label literal == `KB_HOST_TOP_LABEL_REGEX` (the R25c idiom) | RED | 3.1 / 3.3 |
| B05 | `test_s16b_b05_service_role_only` | statements include `ALTER TABLE public.kb_brands ENABLE ROW LEVEL SECURITY`, `REVOKE ALL ON TABLE public.kb_brands FROM PUBLIC, anon, authenticated, service_role`, `GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_brands TO service_role`; the REVOKE precedes the GRANT; no `CREATE POLICY`; no GRANT naming anon / authenticated / PUBLIC; no `SECURITY DEFINER`; no `CREATE FUNCTION` | RED | 3.1 |
| B06 | `test_s16b_b06_trigger_and_045_guard` | the trigger statement of 2.6 step 5 verbatim (compact); a DO block whose body contains `to_regprocedure('public.kb_set_updated_at()') IS NULL` and `RAISE EXCEPTION`, placed BEFORE the CREATE TABLE | RED | 3.1 |
| B07 | `test_s16b_b07_host_index_not_unique` | `CREATE INDEX IF NOT EXISTS idx_kb_brands_official_host ON public.kb_brands (official_host) WHERE official_host IS NOT NULL`; no `UNIQUE` token in any statement except the PRIMARY KEY's implicit one (no `CREATE UNIQUE INDEX`, no `UNIQUE (`); `timm._volatile_hits` of every 051 predicate == [] | RED | 3.1 |
| B08 | `test_s16b_b08_no_personal_column_no_fk` | no column name matches `t043.PERSONAL_RX`; no `REFERENCES`; `t043.fence_report(t043.real_forward_files())` has no gaps and the fence's user tables equal `KNOWN_USER_TABLES` with 051 visible in `real_forward_files()` names | RED (051 not in the list) | 3.1 |
| B09 | `test_s16b_b09_rollback_statements` | rollback statements == `["BEGIN", "DROP TABLE IF EXISTS public.kb_brands", "COMMIT"]` (compact); no `kb_set_updated_at` outside comments | RED | 3.2 |
| B10 | `test_s16b_b10_headers` | the 051 comment header (lower, whitespace-collapsed) contains `s81-16b`, `rollback/051_kb_brands.sql`, `service role`, `cc0`, `after 045`, `enable_kb_brands`, `not unique`, `(p31 q5)`, `merging this changes nothing in production`; the rollback header contains `before any rollback of 045` and `enable_kb_brands` | RED | 3.1 / 3.2 |
| B11 | `test_s16b_b11_ascii_and_sqlfluff_clean` | both files: 0 bytes > 127, no 8-digit run, `sqlfluff.lint(text, config=FluffConfig.from_path(ROOT))` (the repo `.sqlfluff`) returns no violation (the API form measured by GREEN; the CLI equivalent `python -m sqlfluff lint --config .sqlfluff <file>` rc 0 is the fallback if the API needs a path) | RED | 3.1 / 3.2 |
| B12 | `test_s16b_b12_kb_brands_literal_census` | over `app/` + `scripts/` (AST string constants): `"kb_brands"` appears ONLY in `app/services/kb_service.py` and in exactly ONE line of `scripts/kb_seed_common.py`, whose text is `KB_BRANDS_TABLE = "kb_brands"` | RED (no such line) | 3.3 / 3.4 |

### 5.2 The leaf (K rows)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| K01 | `test_s16b_k01_census_constants` | `KB_TABLES[-1] == "kb_brands"` and `KB_TABLES[:-1]` == the ten; `KB_COLUMNS["kb_brands"]` == the 7-tuple; `KB_BUILDER_KEYS["kb_brands"]` == the 6-tuple without created_at; `"kb_brands" not in KB_UUID_ID_TABLES`; `KB_BRAND_SOURCES == ("wikidata", "operator")`; `KB_BRAND_UPSERT_SET == ("label_en", "label_ar", "official_host", "updated_at")`; `KB_QID_REGEX == "^Q[1-9][0-9]{0,11}$"` | RED | 3.3 |
| K02 | `test_s16b_k02_builder_accepts` (param: minimal / with host / with Arabic label / 128-char label / 12-digit qid / source operator) | a dict, key set == `KB_BUILDER_KEYS["kb_brands"]`, `updated_at == T0.isoformat()`, every input value passed through unchanged | RED | 3.3 |
| K03 | `test_s16b_k03_builder_refuses` (one param per CHECK clause, ids named by clause): qid `Q0`, `Q01`, `q42`, `Q`, `"Q" + "1" * 13` (built at run time: the added-line sweep refuses an 8-digit run), `"Q42 "`, `"Q42\n"`, `42`; label_en None, "", 129 chars, with NUL, with a lone surrogate; label_ar "", 129 chars, NUL; official_host `Brand.Example.com`, `brand`, `192.0.2.10`, `127.0.0.0x1`, `"www." + DENY_HOSTS[0]`, `DENY_HOSTS[0]`, `<deny label>-shop.example.com` (rule-only), `brand.example.com/x`, a 254-char valid-shape host; source `manual`, None; updated_at naive, a str | `build_brand_row(...) is None` | RED (missing builder: the `_attr` assertion) | 3.3 |
| K04 | `test_s16b_k04_belt_holds_without_the_rule` | with `deny_hosts.kb_source_allowed` patched to `lambda v: True`: `"www." + DENY_HOSTS[0]` still refused (the belt), `<deny label>-shop.example.com` now accepted (rule-only) | RED | 3.3 |
| K05 | `test_s16b_k05_rule_read_at_call_time` | with `deny_hosts.kb_source_allowed` patched to a recorder returning False: a valid host is refused and the recorder saw exactly `["brand-b.example.com"]`; with no host the recorder is not called | RED | 3.3 |
| K06 | `test_s16b_k06_never_raises_on_junk` | `object()` for every kwarg -> None; a dict / list label -> None | RED | 3.3 |

### 5.3 The script (S rows; every row: full config, `Rig` recorders)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| S01 | `test_s16b_s01_flag_constant_and_table` | `brands.FLAG == "ENABLE_KB_BRANDS"`; for the s16 `MODE_TABLE` spellings `common.run_mode(brands.FLAG)` reads ENABLE_KB_BRANDS (setenv the spelling there, ENABLE_KB_SEED = "apply" fixed) and returns the table's mode | RED (FLAG is ENABLE_KB_SEED) | 3.5 |
| S02 | `test_s16b_s02_off_is_inert` (param: the 7 s16 `OFF_SPELLINGS` x ENABLE_KB_SEED in {"apply", "true", None}) | rc 0; exactly ONE record from the brand logger, INFO, whose message contains `ENABLE_KB_BRANDS` AND `ENABLE_KB_SEED`; client factory, fetches, validates, sleeps, events, writes all empty; `open` patched records no call (the R02 idiom) | RED (with ENABLE_KB_SEED apply / true the base script runs and fetches) | 3.5 |
| S03 | `test_s16b_s03_dry_counts_no_write` | ENABLE_KB_BRANDS=true: two GETs (robots then SPARQL, both validated, the named headers, `allow_redirects False`), `writes() == []`; the SPARQL URL decodes (`unquote`) to a text containing `?label_en`, `?label_ar`, `FILTER(LANG(?label_en) = "en")`, `FILTER(LANG(?label_ar) = "ar")`, `FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 . }`, `ORDER BY ?brand ?site`, `LIMIT 2000`; the report has `hosts`, `brands`, `counts` with `with_label_en`, `with_label_ar`, `brand_rows` equal to the fixture's literals; the totals line is INFO | RED | 3.5 |
| S04 | `test_s16b_s04_apply_writes_kb_brands_only` (param: --dry-run absent / present) | ENABLE_KB_BRANDS=apply: absent -> every write is table `kb_brands`, kind `upsert`, `on_conflict == "qid"`, `ignore_duplicates is True`, batches of at most 100; every row's key set == `KB_BUILDER_KEYS["kb_brands"]`, `source == "wikidata"`, `updated_at == NOW.isoformat()`, and equal to `kb.build_brand_row(**row-minus-updated_at, updated_at=NOW)`; no `kb_merchants` write, no `delete`, no other table; present (`--dry-run`) -> `writes() == []` | RED | 3.4 / 3.5 |
| S05 | `test_s16b_s05_rerun_updates_wikidata_rows_only` | FakeClient `returned=lambda q, rows: []` (nothing inserted): one `update` per row, its dict keys == `KB_BRAND_UPSERT_SET`, its `eq` filters == `[("qid", <qid>), ("source", "wikidata")]` in that order; a second case `returned` = the first two rows only -> updates only for the others; `counts.brand_updates` in the report == the update count; never `delete` / `insert` | RED | 3.4 |
| S06 | `test_s16b_s06_dedupe_and_host_choice` | bindings: Q7 with sites `https://zeta.example.com/` and `https://alpha.example.com/` -> one row, host `alpha.example.com`; Q8 with only `https://www.<deny host>/` and `http://192.0.2.10/` -> one row, host None, `brand_host_null == 1`; Q9 with no en label -> no row, `no_label_en == 1`; Q10 with a 129-char Arabic label -> row with `label_ar None`, `label_ar_dropped == 1`; Q11 with en `"  Maison Example  "` -> `label_en == "Maison Example"`; a binding with brand value `http://www.wikidata.org/entity/Q01` -> `bad_qid == 1` | RED | 3.5 |
| S07 | `test_s16b_s07_cap_and_order` | 12 valid brands with qids in shuffled numeric order (Q2, Q10, Q3, ...), `KB_BRANDS_MAX=5`: exactly 5 rows written, the 5 lowest NUMERIC qids (Q2, Q3, ... not string order), `over_cap_brands == 7`, `brand_rows == 5`; the report's `hosts` list unaffected by the knob | RED | 3.5 |
| S08 | `test_s16b_s08_knob_table` (param: None, "", "garbage", "inf", "nan", "-5", "0", "7", "7.9", "9000") | `brands.brands_max()` == 300, 300, 300, 300, 300, 300, 300, 7, 7, 5000 | RED (missing) | 3.5 |
| S09 | `test_s16b_s09_limit_hit_count` | 2000 bindings -> `counts["sparql_limit_hit"] == 1`; 1999 -> the key is absent | RED | 3.5 |
| S10 | `test_s16b_s10_write_failure_is_quiet` (param: upsert raises / update raises) | rc 0; one WARNING containing `kb_brands write failed` and the exception TYPE name and no exception text; no ERROR record; `counts.write_failed == 1` in the report; the report and the totals line still written | RED | 3.5 |
| S11 | `test_s16b_s11_no_label_or_host_in_logs` | APPLY over labels built at run time (a unique sentinel per label, an Arabic one included) and hosts: no log record message or args contains any label, host or the SPARQL text; the report contains the labels (escaped ASCII) | RED (no labels at base: the report assertion fails) | 3.5 |
| S12 | `test_s16b_s12_script_hygiene` | the brand script and kb_seed_common bytes with CRLF normalised to LF: ASCII, no lone `\r`, none of the R27 tokens; no `.table(` call with a string literal in the brand script; `logger.error` only inside except arms; the script's module docstring does not contain `DRY-ONLY` or `writes NOTHING` | RED (the docstring clause) | 3.5 |

### 5.4 PIN rows (green at base; full configuration present)

| # | test | assertion | at base |
|---|---|---|---|
| PIN-1 | `test_s16b_pin1_batch_seeder_flag_unchanged` | with ENABLE_KB_BRANDS=apply, KB_BRANDS_MAX=5 set: `seed_kb_batch.FLAG == "ENABLE_KB_SEED"`; ENABLE_KB_SEED OFF -> its one INFO record names ENABLE_KB_SEED and the Rig sees no client / fetch / event | GREEN |
| PIN-2 | `test_s16b_pin2_host_derivation_literal` | with ENABLE_KB_BRANDS=apply, ENABLE_KB_SEED=apply, KB_BRANDS_MAX=1: `derive_hosts` over the 7-binding probe (sites `https://brand-b.example.com/`, `https://store-a.example.com/`, `https://www.<DENY_HOSTS[0]>/`, `http://192.0.2.10/`, `https://Brand-C.Example.org:443/x`, `not a url`, labels present, plus one binding with no site), existing `{"store-a.example.com"}` -> `["brand-b.example.com", "brand-c.example.org"]` and counts `{"bindings": 7, "denied": 1, "existing": 1, "invalid": 2, "new": 2, "with_site": 6}` (measured at base, 1.1) | GREEN |
| PIN-3 | `test_s16b_pin3_the_045_census_unchanged` | `KB_TABLES[:10]` == the ten 045 names in order; `KB_COLUMNS[t]` for the ten == literals copied from base | GREEN |
| PIN-4 | `test_s16b_pin4_app_names_nothing_new` | no `app/**/*.py` text contains `ENABLE_KB_BRANDS`, `KB_BRANDS_MAX` or `seed_kb_brands_wikidata`; `"kb_brands"` appears in no `app/` file other than `app/services/kb_service.py` | GREEN |
| PIN-5 | `test_s16b_pin5_no_service_runs_the_brand_script` | no `railway*.json` startCommand contains `seed_kb_brands_wikidata` | GREEN |
| PIN-6 | `test_s16b_pin6_045_untouched` | the LF sha256 of `migrations/045_kb_core.sql` == `ba853c75...867075` and of `rollback/045_kb_core.sql` == `4a7fcbab...9043ba` | GREEN |

Counts: 30 RED rows (B01-B12, K01-K06, S01-S12) and 6 PIN rows; with the parametrisations about 120 nodes (K03 alone 27). Every RED fails at base on an AssertionError (the `_require` / `_attr` / `_mod` helpers; S02 / S03 / S04 because the base script runs under ENABLE_KB_SEED or never writes); the RED agent proves it by a base run whose log shows `AssertionError` as the only failure type.

## 6. Mutation table (each on a byte copy; an exact-string edit that matches once; the killing rows via `pyt.py -k`, bound 600; restore; sha256 compare)

| id | file | mutant | killed by |
|---|---|---|---|
| M01 | script | `brands_max()` ignored (cap = 300 constant) | S07 |
| M02 | kb_seed_common | `KbWriter.brands` update loop removed | S05, EK1 |
| M03 | kb_seed_common | `.eq("source", "wikidata")` dropped from the update | S05 |
| M04 | kb_seed_common | the update sets `source` too (`KB_BRAND_UPSERT_SET` + source) | K01, S05 |
| M05 | kb_service | `_belted_host` replaced by `_sql_match(KB_HOST_REGEX, h) and _top_label_ok(h)` (the deny belt dropped) | K04 |
| M06 | kb_service | `kb_source_allowed(official_host)` dropped | K03 (rule-only id), K05 |
| M07 | script | the label coverage counts (`with_label_en` / `with_label_ar`) not bumped | S03 |
| M08 | script | the write runs in DRY too (`if mode == MODE_APPLY` -> `if mode != MODE_OFF`) | S03, EK1 (true) |
| M09 | script | `FLAG = "ENABLE_KB_SEED"` (the write under ENABLE_KB_SEED=apply) | S01, S02 |
| M10 | script | `writer.upsert(<merchants table>, ...)` in place of `writer.brands(rows)` (the kb_merchants write: S-M20 class) | S04, EK1 |
| M11 | script | the `FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 . }` clause removed | S03 |
| M12 | script | the en OPTIONAL made mandatory (`OPTIONAL {` dropped for en) | S03 |
| M13 | script | the host choice takes the LARGEST valid host | S06 |
| M14 | kb_service | `KB_QID_REGEX = "^Q[0-9]{1,12}$"` | K01, K03 (Q0 / Q01) |
| M15 | script | rows sorted by the qid STRING | S07 |
| M16 | script | the OFF line emitted after `resolve_client` | S02 |
| M17 | script | a label in the totals line (`log_counts` replaced by a line formatting the first label) | S11 |
| M18 | script | rows built with `source="operator"` | S04 |
| M19 | 051 | `service_role` dropped from the REVOKE | B05 |
| M20 | 051 | `GRANT SELECT ON TABLE public.kb_brands TO anon` added | B05 |
| M21 | 051 | the index made `CREATE UNIQUE INDEX` | B07 |
| M22 | 051 | the trigger statement removed | B06 |
| M23 | 051 | the `!~` deny clause removed | B04 |
| M24 | 051 | the 045 DO guard removed | B06 |
| M25 | rollback 051 | `DROP FUNCTION IF EXISTS public.kb_set_updated_at();` added | B09 |
| M26 | 051 | `label_ar` CHECK upper bound 128 -> 256 | B03 |
| M27 | script | `label_ar_dropped` path keeps the over-long label (the brand dropped instead) | S06 |
| M28 | script | `write_failed` WARNING raised at ERROR | S10 |
| M29 | kb_service | `kb_brands` inserted FIRST in KB_TABLES | K01, PIN-3, E1 |
| M30 | script | `derive_hosts` reads `brands_max()` as its cap | PIN-2 (KB_BRANDS_MAX=1), EK1 (300 hosts) |

Expected: 30 / 30 KILLED. Equivalent-candidate note: M05 is EQUIVALENT under the production deny rule (the belt is a strict subset of the rule); K04 kills it only because the rule is patched open, which is the row's purpose (R-S14-6 / F1-5 precedent).

## 7. Comm set and gates for GREEN

### 7.1 Comm set (union rule)

Derivation (`proto/../comm.py`, run at base): module / symbol references `kb_service`, `kb_seed_common`, `seed_kb_brands_wikidata`, `merchant_registry`, `kb_ingest` (the leaf's importers), `migrations`, `_retro_r_mig_sql`, `test_s81_s16_kb_seed` (an EDITED test-support module: its importer `tests/test_s81_g2_gate_rows.py` and the new RED file join), `test_s81_kb_schema`, `test_migration_043_delete_user_cascade`, `railway.kbseed`, `ENABLE_KB_SEED`, `scripts` (131 files) UNION the source scanners (`"app/`, `__file__`, `inspect.getsource`, `rglob(`, `.glob(`, `ast.parse(`, `os.listdir` / `scandir` / `walk`, `"app"` joins, `.github`, `CLAUDE.md`: 257 files) UNION the named pins (`test_openai_key_log_hygiene_s69.py` added by hand; the others matched) MINUS the three `test_precommit_hook*.py` it matched (`test_precommit_hook.py`, `_phase_b.py`, `_phase_b_round2.py`; the hook files are not edited). Base set: **302 files**, `comm_base.txt` sha256 `c57341827e783b49d685423cb557ac102315428afebcabd4508a7fb257d63479`; head set = base + `tests/test_s81_s16b_kb_brands.py` = 303 files, sha256 `fcceee0b65e153f27e4bf492eda2f34ef69c97f0f0ee643ad204b0a58435f5c1`. No SmartCompareApp-scanning backend test is required (no client-visible contract); the fourteen client fences run by path at GREEN (7.3). The base record does not exist for 0b19de5b (LC-6: GREEN computes it once in chunks of at most 25 files, bound 1200, and stores it under `harness/base_records/0b19de5b.../c5734182....txt`); NOT MEASURED here.

### 7.2 Gates for GREEN (cheapest first)

- G1 `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on the three edited .py files and the RED file.
- G2 bytes: every new file ASCII + LF; `git diff --stat` shows no whole-file diff; the added-line sweep (@gmail, +973, 8-digit runs, key shapes) empty.
- G3 `python -m sqlfluff lint --config .sqlfluff migrations/051_kb_brands.sql migrations/rollback/051_kb_brands.sql` rc 0.
- G4 the RED file alone (bound 600): every row green; then the RED file with `ENABLE_KB_BRANDS=apply` and `KB_BRANDS_MAX=1` exported for that ONE runner call (the flag-ON leak check: still green, the rows set their own env).
- G5 the E-row files: `tests/test_s81_kb_schema.py`, `tests/test_s81_s16_kb_seed.py`, `tests/test_s81_g2_gate_rows.py` (bound 1200): all green except the five R27 CRLF nodes (environmental, as at base).
- G6 the migration readers: `test_sqlfluff_config.py`, `test_migration_index_predicate_immutability.py`, `test_migration_043_delete_user_cascade.py`, `test_migration_037_security_definer_grants.py`, `test_retro_w1_2d.py`, `test_retro_w1_2c.py`, `test_migration_044_apple_siwa_tokens.py`.
- G7 the comm set (7.1) in chunks of at most 25 files, bound 1200, base record (LC-6) vs head: `comm -13` of the sorted FAILED node-id sets EMPTY.
- G8 the mutation table (6), the lock file, byte copies, sha256 restores: 30 / 30 KILLED.
- G9 (the S81-14 GC-8 precedent; the migration is the FOCUS surface): on a THROWAWAY local PostgreSQL 18 cluster under the notes folder (initdb / pg_ctl from `C:/Program Files/PostgreSQL/18/bin`, a free localhost port, roles anon / authenticated / service_role created first, `pgcrypto` / gen_random_uuid available): apply 045, then APPLY_051_1 (grid as expected), 051, APPLY_051_3 (grid as expected), re-apply 051 (idempotent: no error), the negative inserts (`Q01`, a 129-char label, `www.<deny host>`, `192.0.2.10`, source `manual`: each refused by its CHECK), an insert + update showing `updated_at` moved by the trigger, `SET ROLE anon` SELECT refused, the 045 rollback attempted FIRST (fails 2BP01, nothing changed), rollback 051, then rollback 045 succeeds. Report each step with its output; stop the cluster; leave the data directory in the notes folder (no recursive delete). If the binaries do not start on this box, report G9 NOT MEASURED; the POSTCHECK grid is then the owner's proof.
- G10 the CLAUDE.md readers (`test_ci_gates.py`, `test_behavior_dimension_translation.py`, `test_s81_s04_spend_breaker.py`, `test_s81_s08b_legacy_fingerprint.py`, `test_s81_s23_bypass_retire.py`) after 8.1.

### 7.3 Client fences

The fourteen backend-scanning client fences run BY PATH from `SmartCompareApp` through the orchestrator's junction at GREEN and at every rebase (the footprint touches app/, scripts/, migrations/ and CLAUDE.md). Expected green: measured at base, none of them reads a file this unit edits (1.5). A red fence is an E-row of a pin-fix round, never weakened. The full jest suite runs ONCE, in the last round before the PR (LC-7).

## 8. CLAUDE.md row, owner steps, ledger row, APPLY files

### 8.1 CLAUDE.md (in place, CRLF kept; no new block; names only)

Three edits, all inside the S81-G2 block (re-measured at 0b19de5b: the block header :547, the S81-16 row :550, the owner steps :551):
1. :550, the row's opening parenthesis `(S81-16 KB-SEED-BATCH, \`scripts/seed_kb_batch.py\` + \`scripts/seed_kb_brands_wikidata.py\`, a NEW Railway service ...` -> `(S81-16 KB-SEED-BATCH, \`scripts/seed_kb_batch.py\`, a NEW Railway service ...`.
2. :550, the sentence `The brand script (same flag) reads the query service's robots.txt and makes ONE Wikidata SPARQL GET and writes the derived official-site hosts to \`--report\` ONLY: it writes NOTHING to the KB in any mode, \`apply\` behaves as DRY (R-G2-3; a brands table is S81-16b, a migration).` is rewritten IN PLACE as: `The brand script \`scripts/seed_kb_brands_wikidata.py\` has its OWN flag since S81-16b, \`ENABLE_KB_BRANDS\` + knob \`KB_BRANDS_MAX\` (300, 1..5000; the same mode idiom: unset / false OFF, true DRY, apply WRITE; \`ENABLE_KB_SEED\` never runs it): it reads the query service's robots.txt, makes ONE Wikidata SPARQL GET (brands producing perfume with an official website, humans excluded, en / ar labels), writes the derived official-site hosts and the brand rows to \`--report\` with the label coverage counts (with_label_en, with_label_ar, sparql_limit_hit), and only under \`apply\` writes \`kb_brands\` (migration 051, written NOT applied; service role only) through \`KbWriter.brands\`: insert-ignore on qid, then ONE update of label_en / label_ar / official_host / updated_at per existing 'wikidata' row (an 'operator' row never moves, nothing is deleted); Wikidata data is CC0; never a kb_merchants write (R-G2-3 stands for \`ENABLE_KB_SEED\`).`
3. :551, owner step `(8) the brand script DRY only (\`python -m scripts.seed_kb_brands_wikidata --report <file>\`; the binding count is the id check, L7);` -> `(8) the brand script (S81-16b): after 051 is applied (APPLY_051 PRECHECK / ONE_PASTE / POSTCHECK), \`ENABLE_KB_BRANDS=true\` for the DRY count line (\`python -m scripts.seed_kb_brands_wikidata --report <file>\`; the binding and with_label_en counts are the id check, L7), then \`ENABLE_KB_BRANDS=apply\` ONCE, then unset;`.
The S81-16b section also lands in DEFECT_LEDGER (8.3); the CLAUDE.md "Dated apply record" (:92) is unchanged (051 is absent from it = not applied).

### 8.2 Owner steps (names only; one dated ledger line each; the PR body carries them)

0. Before the merge: `ENABLE_KB_SEED`, `ENABLE_FEED_WALKER`, `ENABLE_PDP_DISCOVERY` unset on their services (or the services absent): the merge edits `scripts/kb_seed_common.py`, which all three `railway.*.json` watch, so it re-deploys and re-runs them in whatever mode their flags hold (L6).
1. Apply 045 then 047 (owner item 29) if not yet applied.
2. Apply 051: `APPLY_051_1_PRECHECK.sql` (grid as stated), `APPLY_051_2_ONE_PASTE.sql`, `APPLY_051_3_POSTCHECK.sql` (grid as stated).
3. On the kbseed service: `ENABLE_KB_BRANDS=true`, run `python -m scripts.seed_kb_brands_wikidata --report <file>`; record the totals line (bindings, with_site, with_label_en, with_label_ar, brand_rows, over_cap_brands, sparql_limit_hit) in the ledger.
4. If the counts look right (bindings > 0, with_label_en close to the distinct brands): `ENABLE_KB_BRANDS=apply` (optionally `KB_BRANDS_MAX`), run once; record `kb_brands_sent`, `brand_updates`, `write_failed`.
5. Unset `ENABLE_KB_BRANDS`.
6. Canary (read-only SQL, names only): `SELECT count(*), count(label_ar), count(official_host) FROM public.kb_brands`; after a SECOND apply run a day later, `count(*) FILTER (WHERE updated_at > created_at)` > 0 confirms the update path (the R-G2-12 class; zero there = the insert-ignore returned conflicting rows, a follow-up).
7. The PR body notes the source: Wikidata (CC0), query.wikidata.org, one GET per run.

### 8.3 DEFECT_LEDGER row (drafted; the ledger's column form; names only)

| S81-16b | KB-BRANDS (FOCUS: a migration): migration 051 kb_brands (qid, label_en, label_ar, official_host, source; the 045 host / deny / top-label belts; a partial host index, not unique; the 045 trigger function reused; service role only, the 045 REVOKE / GRANT form; rollback before 045's) WRITTEN NOT APPLIED; kb_service.build_brand_row + kb_brands in KB_TABLES / KB_COLUMNS / KB_BUILDER_KEYS; the G2 brand script moves to its own flag and its APPLY writes kb_brands through KbWriter.brands (insert-ignore on qid + one update of the label / host columns of 'wikidata' rows; never a delete, never kb_merchants), the SPARQL gains en / ar labels, a human exclusion and ORDER BY, capped by KB_BRANDS_MAX; closes the G2 stated limit S16 L7 (brand labels not stored; RULINGS_S81_G2 R-G2-3) | ENABLE_KB_BRANDS (unset / false OFF; true DRY; apply WRITE; read per call) + KB_BRANDS_MAX | tests/test_s81_s16b_kb_brands.py (30 RED / 6 PIN) + E-rows EK0-EK2 (tests/test_s81_s16_kb_seed.py) and E1 (tests/test_s81_kb_schema.py R27) | feature/s81-s16b-kb-brands (sc-s81-s16b, detached 0b19de5b) | SPEC (S81-16b_UNIT_SPEC.md, 2026-11-04) -> adversarial spec review next |

### 8.4 APPLY files (drafted, sqlfluff 4.3.0 clean under the repo config, ASCII, LF)

`proto/APPLY_051_1_PRECHECK.sql` (sha256 `2b447bdc...76805f`: pg15_or_later, kb_045_applied, kb_brands_absent, the three roles), `proto/APPLY_051_2_ONE_PASTE.sql` (sha256 `eafb3f7b...911e9b`: a two-line header + the 051 text; GREEN regenerates it from the FINAL migration bytes so the two never differ), `proto/APPLY_051_3_POSTCHECK.sql` (sha256 `98d3ae7e...3a17fe99`: table_present, relrowsecurity, policy_count 0, column_count 7, check_count 6, fk_count 0, trigger_present, host_index_present, host_index_unique false, service_role S / I / U / D true and TRUNCATE false, anon / authenticated SELECT / INSERT false, row_count 0). The orchestrator files them as `specs/APPLY_051_*.sql` in the session state folder (the 045 / 050 precedent).

## 9. Stated limits

- L1 The Wikidata ids (P1056, Q131746, P856, P31, Q5) and the `rdfs:` prefix are offline-unverified; the DRY counts are the check (S16 L7 kept).
- L2 Labels are exact `en` / `ar`; an item labelled only in a regional code or `mul` is skipped (`no_label_en`) or stored with `label_ar` NULL.
- L3 The human exclusion also removes human items' official sites from the G2 host list (a deliberate change of the DRY host output; no merchant write exists to be affected).
- L4 A brand that loses its en label in Wikidata keeps its last stored row (no row is built, so no update); a brand gone from Wikidata is never deleted; stale rows are an operator matter.
- L5 Rollback order: 051 before 045 (the 045 rollback fails 2BP01 while kb_brands exists, changing nothing; the 045 rollback stays frozen).
- L6 The merge re-deploys the three G2 services (kb_seed_common is in their watch patterns); harmless while their flags are unset (owner step 0).
- L7 The insert-ignore return shape (inserted rows only) is unmeasured offline (R-G2-12): if PostgREST returned conflicting rows, re-runs would not refresh labels; the canary of 8.2 step 6 reads it.
- L8 The SPARQL answer is truncated at 2,000 (brand, site) pairs (`sparql_limit_hit` says so); ORDER BY makes the truncation deterministic, not complete.
- L9 The R27 / S12 hygiene reading of script bytes: S12 normalises CRLF; G2 R27 stays environmentally red on a Windows CRLF checkout (F1-3).
- L10 One update per existing row per run (up to `KB_BRANDS_MAX` round trips), even when nothing changed; acceptable at 300 rows.
- L11 `official_host` NULL means "no usable official site" (none in Wikidata, denied, IP literal or invalid): the reasons are counted, not stored.

## 10. Out of scope

Brand aliases, brand-to-product matching and any FK from kb_products.brand (later units); reading kb_brands on any request path (G4 or later); `operator` row tooling; scheduled re-runs (a one-off import per PLAN_S81 :156); a kb_merchants candidate write from Wikidata (withdrawn by R-G2-3, not revived); Wikidata items without an official website (the site stays mandatory in the query, keeping the G2 brand set comparable); the `mul` / regional label fallback; any change to seed_kb_batch, the feed walker, PDP discovery, 045, 047, 050; the docs state folder (the orchestrator files the APPLY drafts and the ledger row).

## 11. Open questions (for RULINGS_S81_16B)

- 11.1 The qid CHECK: `^Q[1-9][0-9]{0,11}$` (this spec: no leading zero, so one item has one key) vs the brief's `^Q[0-9]{1,12}$`.
- 11.2 The human exclusion (`FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 }`) changes the G2 DRY host list (L3): accept, or apply it to the brand rows only (the query would then need the P31 value bound and a Python filter)?
- 11.3 The OFF line names BOTH flags so G2 R02 stays unedited (the alternative is a fourth E-row EK3 on R02 keyed on ENABLE_KB_BRANDS).
- 11.4 The host choice for a brand with several valid official sites: the smallest host string (deterministic, this spec) vs the first in ORDER BY order (equal here) vs preferring a non-subdomain apex.
- 11.5 The update guard `.eq("source", "wikidata")`: confirm operator rows must never be refreshed by the import.
- 11.6 G9 (the local PostgreSQL apply / rollback run) as a GREEN gate vs a fix-round item if the binaries cannot start on this box.
- 11.7 The report's `brands` list carries labels (CC0 brand names; useful for the owner's eyeball check): confirm, or report qids and hosts only.

Not done in this spec: no RED, GREEN or mutation run; the comm-set base record (7.1) and G9 NOT MEASURED; the expected Wikidata row count is not measurable offline; nothing written outside `.qa-s80/` and the scratchpad.
