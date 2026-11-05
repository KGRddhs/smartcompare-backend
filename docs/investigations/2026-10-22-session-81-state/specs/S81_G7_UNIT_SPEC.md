# S81-G7 FOLLOWUPS - group unit spec (D16b + D17b + D22c + D22d)

Spec writer: Opus 5.5 (claude-opus-5-5), 2026-11-05 12:10-13:10 AST. Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-g7`, detached at the base `6869a3e655805afd3adbba43f99578dd79585934` (origin/main after #388); `git status --short` empty before and after every probe (only this gitignored `.qa-s80/` file is new). Branch for GREEN: `feature/s81-g7-followups`. Measurement notes and logs: `<scratchpad>/g7spec/` (scratchpad = `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/03431011-0c7e-4ecd-b0ce-08ff47f4af10/scratchpad`). Binding inputs read in full: `scripts/s81-common.txt` (incl. LC-1..LC-9 and the MOVING MAIN lines to 6869a3e6), `specs/S81_G7_BRIEF.md`, PLAN_STATUS "Cross-unit notes from the S84 briefs", `specs/RULINGS_REBASE_S81_G5.md` (RB-G5-3 = L14, RB-G5-7 = L15), PLAN_S80 section 0 + `runs/research/contract_freeze.json` (re-read before section 2). Personal-data rule: every value in this spec, the RED files and the fixture is synthetic, built at run time where a shape matters; no real name, email, phone, id or address. No production probe was made (the D22c column facts come from the measured M22 review record, cited in place).

## 0. The group

| Unit | What | Flag | Files (non-test) | RED file |
|---|---|---|---|---|
| D16b OPERATOR-INGEST-DATES | the operator ingest refuses a future `captured_at` (beyond a 300 s skew) with the existing 422 `VALIDATION_ERROR` shape; `kb_serve.classify` and the D17 coverage ages treat a future `last_seen` / `captured_at` (beyond the skew) as unknown, never as the freshest offer | none new: rides `ENABLE_OPERATOR_INGEST` (route 404 when OFF), `ENABLE_KB_FIRST_SERVE` (classify only reached when ON), `ENABLE_KB_COVERAGE_ROLLUP` | `app/services/kb_serve.py`, `app/services/kb_operator.py`, `scripts/cron_kb_coverage.py` | `tests/test_s81_d16b_operator_dates.py` |
| D17b COVERAGE-PAGING | `_paged` orders every paged read by the primary key `id`; the host pipeline runs through the live_robots `exec` / `execute` fallback | none new: rides `ENABLE_KB_COVERAGE_ROLLUP` | `scripts/cron_kb_coverage.py` | `tests/test_s81_d17b_coverage_paging.py` |
| D22c PROFILE-SELECT (1) | under a NEW dark flag the two phantom-column selects of `_update_behavior_profile` are repointed at live columns (user_events `event_data`, comparisons `full_response` JSON paths), so the profile write can run; flag OFF byte-identical, pinned by a golden | NEW `ENABLE_BEHAVIOR_PROFILE_EVENT_DATA` (default OFF, read per call) | `app/services/structured_comparison_service.py` | `tests/test_s81_d22c_profile_select.py` + `tests/fixtures/s81_d22c_flag_off_golden.json` |
| D22c VARHINT-RETIRE (2) | `_VARHINT_LEARNED_PATH`, `_varhint_append_learned`, its one call, `data/variant_hint_learned.json` and the B3b test suppression deleted (dead code; R-A1 pure-defect class, proven byte-identical by the corpus gate) | unflagged | `app/services/price_service.py`, `data/variant_hint_learned.json` (deleted) | `tests/test_s81_d22c_varhint_retire.py` |
| D22d LEARNING-HARDENING | `_read_by` pages each IN chunk in id-ordered pages (L14); an unclean kb_feedback field name counts in `dropped_deidentify` (G5-GR6 E-row); control characters escaped on render in the log and markdown name cells (L15) | none new: rides `ENABLE_LEARNING_JOB` | `scripts/cron_learning.py` | `tests/test_s81_d22d_learning_hardening.py` |

Every flag is unset in production (newest ledger line 2026-11-05 12:11 names none of them set; `ENABLE_BEHAVIOR_PROFILE_EVENT_DATA` is a new name, unset by construction). Nothing changes in production until an owner flip.

Change list per unit: section 3 of each unit. Shared files and GREEN order:
- `scripts/cron_kb_coverage.py` is shared by D17b (`_paged`, `_hosts`) and D16b (`_field_shares`, `_ages`, one helper). GREEN applies D16b's `kb_serve.FUTURE_SKEW_SECONDS` first (the one definition both other D16b hunks read), then the D17b hunks of cron_kb_coverage, then the D16b hunk of cron_kb_coverage, then kb_operator, then D22c (2) (price_service + data + the B3b E-row), then D22c (1) (scs + golden), then D22d (cron_learning + the GR6 E-row), then CLAUDE.md last (one G7 block, five rows, plus the :341 pointer clause).
- `CLAUDE.md`: one block shared by all four units (section 8 of each unit gives its row).
- No other file is shared. No migration. No `SmartCompareApp/` file. No `.github/` file.

Order of GREEN application inside each file: hunks bottom-up are not required (the Edit tool preserves CRLF); every app/ and scripts/ file is CRLF in the working copy (measured with `file`: kb_operator.py, kb_serve.py, cron_kb_coverage.py, cron_learning.py, structured_comparison_service.py, price_service.py, admin_routes.py all "with CRLF line terminators"); a whole-file diff in `git diff --stat` is a defect.

---

## Unit D16b OPERATOR-INGEST-DATES

### 1. Base state (measured at 6869a3e6)

| # | Site | Measured |
|---|---|---|
| 1.1 | `app/services/kb_operator.py:61-71` | `REFUSALS` = the eight `KB_*` codes (URL_REFUSED, HOST_UNKNOWN, HOST_CANDIDATE, HOST_NOT_REVIEWED, IDENTITY_UNRESOLVED, PAYLOAD_TOO_LARGE, STORE_UNAVAILABLE, LICENCE_FIELD); each a 400 through `admin_routes._kb_operator_refusal` (`app/api/admin_routes.py:1308-1309`). |
| 1.2 | `kb_operator.py:150-175` | `OperatorIngest` (pydantic v2, `extra="forbid"`); `captured_at: Optional[datetime] = None` (:164); ONE field validator today (`_specs_shape`, :167-175, raises `ValueError` -> FastAPI 422). No bound on `captured_at`. |
| 1.3 | `kb_operator.py:117-118` | `_now()` = `datetime.now(timezone.utc)`, a module-attribute seam the D16 harness patches (`tests/test_s81_d16_operator_ingest.py:281` `mp.setattr(mod, "_now", lambda: NOW)`). |
| 1.4 | `kb_operator.py:277-280` | `_aware(moment, fallback)`: a naive datetime is read as UTC; None -> the fallback (the route's `now`). |
| 1.5 | `kb_operator.py:325` | `captured = _aware(body.captured_at, now)`; it reaches `build_offer_row(captured_at=captured)` (:345-348), `build_image_row` (:351-352), `build_spec_row` (:355-356). `kb_service.build_offer_row` sets `last_seen = captured_at` when `last_seen` is None (`app/services/kb_service.py:596`). So a future `captured_at` becomes a future `kb_offers.last_seen`. |
| 1.6 | `app/api/admin_routes.py:1335-1361` | the ingest route: dependencies `operator_gate` (FIRST; flag OFF -> Starlette 404) then `verify_admin_key`; the body is parsed by FastAPI before the handler; `OperatorRefusal` -> 400 `KB_*`; any other exception -> 400 `KB_STORE_UNAVAILABLE` (never 5xx). |
| 1.7 | `app/middleware/error_handler.py:31` + `:235-251` | 422 maps to `VALIDATION_ERROR`; `validation_exception_handler` builds `{success:false, error:"Validation error: <loc>: <msg>", code:"VALIDATION_ERROR", request_id}` with status 422. The G4 contract already uses this for a bad field: `tests/test_s81_d16_operator_ingest.py:475-485` (R7: an extra key, a bad currency, 21 JSON-LD items, a negative amount -> 422). Answer to Q1: the existing validation code for a bad field is **422 VALIDATION_ERROR**; it is reused (no new code, nothing added to REFUSALS). |
| 1.8 | `app/services/kb_serve.py:174-181` | `_ts`: ISO parse, naive -> UTC, garbage -> None. |
| 1.9 | `kb_serve.py:225-280` | `classify`: per BH/BHD allowed offer, `age = now - seen` (:260); `age <= GENUINE_PRICE_DB_TTL` (7 d, `app/services/product_data_service.py:28-30`) -> `fresh` (:261-262), `accepts_asof and age <= max_asof_days()*86400` -> `asof`, else `stale` (:263-266); the grade group is sorted by `-seen.timestamp()` (:268-269) so the NEWEST `last_seen` is `dicts[0]` = the served price. A NEGATIVE age (future `last_seen`) is `<= fresh_window`, so it grades `fresh` and, being the newest, wins: the defect. |
| 1.10 | `kb_serve.py:99-100` | `_now()` seam; the only caller of classify is `structured_comparison_service.py:6057` (H1, inside the S81-18 card task, absent with `ENABLE_KB_FIRST_SERVE` OFF). |
| 1.11 | `scripts/cron_kb_coverage.py:63-70`, `:77-78`, `:184-222` | the coverage `_ts` (same shape), `_hours(now, t)`; `_field_shares` counts a product `fresh` when `_ts(last_seen) >= now - 7 d` (:196-199: a future `last_seen` counts fresh); `_ages` takes the median of `_hours(now, t)` over `last_seen` and `captured_at` (:216-222: a future value enters the median as a NEGATIVE hour count). Same defect class (the brief's "any D17 reader of kb_offers_latest ages"). |
| 1.12 | `scripts/cron_kb_enrich.py:159-177`, `:218-219` | the price refresh orders by `last_seen` (oldest first); a future row is refreshed last. Not edited (section 10). |
| 1.13 | libraries (pinned venv `.venv-qaren`) | pydantic v2 (`field_validator` in use at :167), FastAPI `RequestValidationError` path measured above. |
| 1.14 | flag idiom | `operator_ingest_enabled()` (:86-88) `os.getenv("ENABLE_OPERATOR_INGEST","false").strip().lower() in _TRUTHY`, read per call by `operator_gate`. |

1.15 Base pass state (bounded runner, one call over the twelve touched pin files of the group):
`[pyt] tag=g7spec-base-pins start=2026-11-05 12:17:55 end=2026-11-05 12:18:19 elapsed=25s bound=1200s status=FAIL rc=1` - `2 failed, 801 passed`; `[hermeticity] sentinel checked 803 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`. The two failures are the known environmental CRLF hygiene rows, identical in the stored S81-20 record at this sha: `tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only` (the runbook's working copy is CRLF) and `tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene` (cron_kb_coverage.py working copy CRLF). Files in that run: test_s81_d16_operator_ingest, test_s81_s18_kb_first_serve, test_s81_g4_gate_rows, test_s81_d17_coverage, test_s81_d22_nightly_learning, test_s81_g5_gate_rows, test_variant_llm_hint_b3b, test_variant_hint_reference_b3a, test_behavior_integration, test_m18_offload_sweep_residual, test_behavior_dimension_translation, test_s81_kb_schema.

### 2. Contract

- One constant, defined ONCE: `kb_serve.FUTURE_SKEW_SECONDS: int = 300` (5 min; the clock-skew allowance between the operator's browser clock, the app host and the DB). kb_operator and cron_kb_coverage read it through a function-local `from app.services import kb_serve` (the existing kb_operator pattern at :188; kb_serve is not kb_service, so the P01 pin `tests/test_s81_kb_schema.py:330-389` is unaffected; no kb_* relation literal is added, so P02 is unaffected).
- (a) Ingest: a new `field_validator("captured_at")` on `OperatorIngest`: `None` passes; otherwise `moment = value if value.tzinfo else value.replace(tzinfo=utc)`; `if moment > _now() + timedelta(seconds=kb_serve.FUTURE_SKEW_SECONDS): raise ValueError("captured_at is in the future")`. `_now` is the module seam read at validation time. Boundary: exactly `now + 300 s` is ACCEPTED; `now + 301 s` is refused. Result: HTTP 422 `{success:false, code:"VALIDATION_ERROR", error:"Validation error: body -> captured_at: ...", request_id}` from the existing handler (the error text carries the handler's existing arrow; tests assert on `status_code` and the `code` / `success` FIELDS only, never on the message text). Zero client calls (the body fails before the handler runs). Never a 500, never a silent accept.
- (b) `kb_serve.classify`: inside the offer loop, after `seen = _ts(...)`: `if seen is not None and seen > now + timedelta(seconds=FUTURE_SKEW_SECONDS): seen = None` (so the existing `seen is None -> continue` skip applies: the offer is treated exactly like one with an unreadable `last_seen`). Within the skew a slightly-future `last_seen` keeps today's behaviour (grade `fresh`, `as_of` = that instant). Consequence: a future-only card -> `price_state` `none` (never `fresh`); a future offer beside a genuine one -> the genuine one is `dicts[0]`, the future one is not in `candidates`.
- (c) `cron_kb_coverage`: one helper `_past(value, now) -> Optional[datetime]` = `_ts(value)` unless it is later than `now + FUTURE_SKEW_SECONDS` (then None); `_field_shares`' fresh set and both `_ages` lists use `_past(..., self.now)` instead of `_ts(...)`. A future value is therefore absent from `kb.field.offer_fresh_share`'s numerator and from both median lists (and from their `n`); `kb.field.offer_share` (any offer) is unchanged.
- Flag-OFF identity (the main invariant): `ENABLE_OPERATOR_INGEST` OFF -> `operator_gate` raises the 404 BEFORE body validation (FastAPI solves dependencies before it raises collected body errors; R-row P1 proves it with a future body), so the OFF response stays `{"detail":"Not Found"}` exactly as an unregistered path; classify is unreachable with `ENABLE_KB_FIRST_SERVE` OFF (the frozen S18 PIN rows); the coverage job exits 0 before any I/O with its flag OFF (frozen D17 R1). For a body or card whose timestamps are all <= now + 300 s, every output is byte-identical to base (PIN rows).
- New keys: none (no response key, no log line, no metric). New log lines: none.
- Failure table:

| Input | Base | After |
|---|---|---|
| ingest `captured_at` = now + 1 d (flag ON, key ok) | 200, rows written with the future instant | 422 VALIDATION_ERROR, zero client calls |
| ingest `captured_at` = now + 300 s | 200 | 200 (unchanged) |
| ingest `captured_at` naive, 1 d ahead | 200 | 422 (naive read as UTC, as `_aware` does) |
| ingest `captured_at` absent / past | 200 | 200, byte-identical rows |
| ingest any body, flag OFF | 404 unregistered shape | same |
| classify, only offer last_seen = now + 1 d | `fresh`, served | `none`, price None |
| classify, future + genuine (now - 1 d) | future served (newest) | genuine served; future absent from candidates |
| classify, last_seen = now + 4 min | fresh | fresh (unchanged) |
| coverage, a future last_seen | counted fresh; a negative hour in the median | not fresh; not in the median or its n |

- Seams: `kb_operator._now`, `kb_serve._now` (classify takes `now` as an argument; the test passes it), `kb_serve.FUTURE_SKEW_SECONDS` (read at call time through the module attribute, so a test may monkeypatch it).

### 3. Change list

Byte copies first (`shutil.copyfile` of the three files to the GREEN notes folder; sha256 recorded).
1. `app/services/kb_serve.py`: add `FUTURE_SKEW_SECONDS = 300` beside `PRICE_STATES` (:53) with a one-line comment; in `classify` (after :255) the two-line future check of 2(b); docstring line in the module header noting the rule.
2. `app/services/kb_operator.py`: import `timedelta` (the `from datetime import` line :38); the `captured_at` field validator of 2(a) inside `OperatorIngest` after `_specs_shape`; one docstring line in the module header.
3. `scripts/cron_kb_coverage.py`: `_past` beside `_ts` (:63-70); `_field_shares` :198-199 and `_ages` :217-218 read `_past(value, self.now)`.
4. New `tests/test_s81_d16b_operator_dates.py` (section 5).
No other file (the D16 runbook is not edited: it states no clock rule; the CLAUDE.md row is section 8).

### 4. Existing pins

4.1 Deliberate changes: none. No frozen row pins the acceptance of a future `captured_at` or the grading of a future `last_seen` (measured: `tests/test_s81_d16_operator_ingest.py` uses `NOW` or no `captured_at`; `tests/test_s81_s18_kb_first_serve.py:241` builds `last_seen = NOW - timedelta(days=days)` with `days` in {6, 8, 31, ...} >= 0; `tests/test_s81_d17_coverage.py` seeds past instants only).
4.2 Must stay green: `tests/test_s81_d16_operator_ingest.py` (all rows; r10 stays the environmental CRLF failure, identical base/head), `tests/test_s81_s18_kb_first_serve.py` (R7/R8 classify rows), `tests/test_s81_g4_gate_rows.py`, `tests/test_s81_d17_coverage.py` (R3 EXPECTED literals; r9 environmental), `tests/test_s81_kb_schema.py` (P01 / P02), `tests/test_s81_s19_gap_queue.py`.

### 5. RED tests: `tests/test_s81_d16b_operator_dates.py`

Hermetic: `import app.main` FIRST (the dotenv guard), the route harness rebuilt locally on the D16 shape (a fake service-role client with `_Query` / `_Client` recorders that count every `table()` call; the admin key built at run time with `secrets.token_hex(32)`; `KB_OPERATOR_PAGE_MAX` set to a synthetic "7"; `ENABLE_SYNC_DB_OFFLOAD` unset; `kb_operator._now` patched to `NOW = 2026-11-02T06:00Z`); synthetic hosts `store-a.example.com`; netguard on; pure ASCII, LF. Missing symbols are read with `getattr` and asserted (never an import error).

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_skew_constant` | `getattr(kb_serve, "FUTURE_SKEW_SECONDS", None) == 300` and an int | AssertionError (absent) | 3.1 |
| R2 | `test_r2_future_captured_at_refused` | flag ON, `captured_at = NOW + 1 d` (ISO Z) -> status 422, body `success is False` and `code == "VALIDATION_ERROR"`; the fake client saw ZERO `table()` calls | AssertionError (200) | 3.2 |
| R3 | `test_r3_skew_boundary` | NOW + 301 s -> 422; NOW + 300 s -> 200 and the offer row equals `build_offer_row(..., captured_at=NOW+300s)` | AssertionError (301 s accepted) | 3.2 |
| R4 | `test_r4_naive_future_refused` | `captured_at` naive `2026-11-03T06:00:00` -> 422 | AssertionError | 3.2 |
| R5 | `test_r5_reads_the_now_seam` | with `_now` patched to NOW, `captured_at = 2026-11-03T06:00Z` (in the REAL past on any run day after 2026-11-03, the future of the seam) -> 422 (kills a mutant that reads the wall clock) | AssertionError | 3.2 |
| R6 | `test_r6_classify_future_only_is_unknown` | `classify(card with one BH/BHD allowed offer, last_seen NOW + 1 d)` -> `price is None`, `price_state == "none"`, `candidates == []` | AssertionError (`fresh`) | 3.1 |
| R7 | `test_r7_classify_future_never_shadows` | offers last_seen NOW + 2 d (amount 99.0) and NOW - 1 d (amount 42.5) -> `price["amount"] == 42.5`, `price["as_of"]` == the NOW - 1 d instant in Z form, `len(candidates) == 1` | AssertionError (99.0 served) | 3.1 |
| R8 | `test_r8_coverage_future_not_fresh_not_aged` | drive `cron_kb_coverage.main(["--day", ...], client=fake, redis=None)` DRY with one product whose only offer has last_seen = now + 3 d and captured_at = now + 3 d, plus one product with a 1 d old offer -> `kb.field.offer_fresh_share` value 0.5 with n 2, and `kb.price.age_median_hours` n == 1 (the future value absent) | AssertionError (share 1.0, n 2) | 3.3 |
| P1 | `test_p1_flag_off_404_with_future_body` | full configuration (key, knob set, `_now` patched) with the flag OFF in each spelling `None / "false" / " 0 " / "OFF"`: POST a future-dated body -> 404 and the body equals the unregistered-path body (`/api/v1/admin/kb/__absent__`); zero client calls; the admin-key dependency never ran (a recorder on `verify_admin_key` through `app.dependency_overrides` is NOT used: assert instead that a request WITHOUT the key also gets 404, not 403) | green | base |
| P2 | `test_p2_past_and_absent_unchanged` | flag ON: `captured_at` absent -> rows use NOW (as D16 R4); `captured_at = NOW - 1 d` -> the offer / image / spec rows equal the builders' output for that instant | green | base |
| P3 | `test_p3_within_skew_classify_unchanged` | last_seen NOW + 4 min -> `price_state == "fresh"`, `as_of` == that instant; a 6 d old offer -> fresh; a 8 d old offer with `accepts_asof=True` -> `asof` (the S18 R8 arithmetic restated with the full card) | green | base |
| P4 | `test_p4_coverage_past_world_identical` | the frozen D17 world (imported from `tests.test_s81_d17_coverage`, its `EXPECTED` dict) yields the identical metric triples (no future value in it) | green | base |

Counts: RED 8, PIN 4.

### 6. Mutation table (byte copies, `.qa-mutation.lock`, `pyt.py -k`, bound 600 each)

| M | Mutation | Killed by |
|---|---|---|
| M1 | validator `>` -> `>=` (300 s refused) | R3 |
| M2 | validator reads `datetime.now(timezone.utc)` instead of `_now()` | R5 |
| M3 | validator drops the naive-to-UTC branch (naive compare raises TypeError -> 500 or 422 by accident) | R4 (asserts 422 AND code; a TypeError surfaces as 500) |
| M4 | `FUTURE_SKEW_SECONDS = 0` | R3, P3 |
| M5 | classify future check removed | R6, R7 |
| M6 | classify future check turns `seen` into `now` instead of None | R6 |
| M7 | coverage `_past` used in `_ages` only (not `_field_shares`) | R8 |
| M8 | coverage `_past` returns `_ts` unconditionally | R8 |

### 7. Comm set
The group's (section 12). D16b alone would be the D16 / S18 / D17 / G4 files plus the kb_serve importers (structured_comparison_service and its importers): already inside the group set.

### 8. CLAUDE.md row and owner steps
Row (inside the G7 block, section 12.5): `- D16b OPERATOR-INGEST-DATES (no new flag; rides ENABLE_OPERATOR_INGEST / ENABLE_KB_FIRST_SERVE / ENABLE_KB_COVERAGE_ROLLUP): the operator ingest refuses a captured_at later than now + kb_serve.FUTURE_SKEW_SECONDS (300 s) with the existing 422 VALIDATION_ERROR (never a 500, never a silent accept); kb_serve.classify and the coverage ages treat a last_seen / captured_at beyond the skew as unknown (never the freshest offer, never a negative age); every timestamp at or before now + 300 s is handled byte-identically. RED tests/test_s81_d16b_operator_dates.py.`
Owner steps: none (nothing to flip; the next operator ingest after the flag's own flip simply refuses a typo'd future date).

### 9. Stated limits
- L-D16b-1: the 300 s skew lets a capture up to 5 min ahead through and serves it as fresh with that `as_of` (sized for clock drift, not a security bound).
- L-D16b-2: rows already stored with a future `last_seen` (none expected: the route has never been ON in production) stay in the table; classify ignores them until the date passes; the enrich worker's oldest-first refresh (`cron_kb_enrich.py:218-219`) still sorts them last.
- L-D16b-3: no lower bound on `captured_at` (a very old capture is accepted and graded stale by age, as today).

### 10. Out of scope
The enrich worker's ordering; a DB CHECK on `kb_offers.last_seen` (a migration: FOCUS); the runbook text; a new refusal code.

### 11. Open questions
- Q-D16b-1: the 300 s skew value (proposed; any value 60..900 satisfies the rows if R3 is re-parameterised). Default: 300.

---

## Unit D17b COVERAGE-PAGING

### 1. Base state (measured at 6869a3e6)

| # | Site | Measured |
|---|---|---|
| 1.1 | `scripts/cron_kb_coverage.py:96-113` | `_paged(client, table, columns, filters=())`: `client.table(table).select(columns)`, the filters, then `.range(start, start + PAGE_SIZE - 1).execute()` for `page in range(MAX_PAGES)` until a short page; NO `.order(...)`: PostgREST without an ORDER BY gives no stable row order across range requests above one page (rows can repeat or be skipped). `common.PAGE_SIZE = 500`, `MAX_PAGES = 200` (`scripts/kb_seed_common.py:45-46`). |
| 1.2 | `_paged` callers | `kb_products` (:139), `kb_offers_latest` (:142), `kb_variants` (:145), `kb_images` (:151), `kb_reviews` (:156), `kb_specs` (:160), `kb_gaps` (:225), `search_logs` (:238-239, with a gte/lt window). |
| 1.3 | primary keys (Q2) | `migrations/045_kb_core.sql`: kb_products `id text PRIMARY KEY` (:136), kb_variants `id text PRIMARY KEY` (:151), kb_offers / kb_images / kb_specs / kb_reviews / kb_gaps `id uuid PRIMARY KEY` (:169, :203, :229, :253, :274); the view `kb_offers_latest` (:351-362) selects `o.id` (the offer pk, unique per row of the DISTINCT ON view); `search_logs` `id UUID PRIMARY KEY` (`migrations/002_search_logs_and_products.sql:5-6`). Every paged relation therefore orders on `id`. The house idiom: `kb_seed_common.read_merchant_rows` orders by its pk `host` (:183-198); `cron_learning._page` orders by `id` (:273-282). |
| 1.4 | `cron_kb_coverage.py:262-298` `_hosts` | ONE pipeline: `pipe = self.redis.pipeline()`, `pipe.hgetall(...)` per host, `return list(pipe.exec() or [])` (:273-276) inside `self.guarded("hosts", read)`; a client without `exec` raises AttributeError -> one WARNING and NO host metric. |
| 1.5 | pinned clients (Q2, measured on `.venv-qaren`) | `upstash-redis 1.7.0`: `Pipeline` has `exec()` (signature `()`, runs the queue) AND `execute(command: List) -> Pipeline` (queues ONE raw command, does NOT run); `redis-py 8.1.0`: `Pipeline` has only `execute()` (runs). So `execute` must never be preferred on upstash: the live_robots form `fn = getattr(pipe, "exec", None) or getattr(pipe, "execute"); fn()` (`app/services/live_robots.py:456-459`, G3-GR4) is correct for both. `_default_redis()` (:312-319) returns `cache_service.redis_client`, which is the upstash client or the `redis.from_url` fallback (`app/services/cache_service.py:101-166`). |
| 1.6 | D17 frozen fakes | `tests/test_s81_d17_coverage.py:110-160` `_Query` supports `order` (records `(column, desc)`; `_Client._execute` sorts by `_cmp_key` :95-101, rows missing the column sort as equal keys); `_Pipe` (:220-235) has both `exec()` and `execute()` (zero-arg). No frozen row asserts an empty `orders` list or the absence of an order call (measured: `ops` record table / op / payload / kwargs / filters / columns only). |
| 1.7 | flag | `coverage_mode()` (:49-51) -> `common.run_mode(FLAG)` read FIRST in `main`; off -> exit 0 before I/O. |
| 1.10 | base pass state | the group run in D16b 1.15 (test_s81_d17_coverage: all green but the environmental r9). |

### 2. Contract
- `_paged` orders every page by `id` ascending: `query.order(PAGE_ORDER_COLUMN)` after the filters, before `.range(...)`, with the module constant `PAGE_ORDER_COLUMN = "id"` (a column, not a relation, so P02 is unaffected). Every caller in 1.2 is covered (one place). Ascending, `desc=False` (the default; the call passes no `desc`).
- `_hosts.read`: `run = getattr(pipe, "exec", None) or getattr(pipe, "execute")`; `return list(run() or [])`. On upstash `exec` is chosen (never the one-argument queueing `execute`); on redis-py `execute`.
- DRY and apply: output unchanged except row ORDER of reads (the metrics are order-free sets, counts and medians); for any table under PAGE_SIZE the report and the upserted rows are byte-identical to base (PIN). Above PAGE_SIZE the read becomes complete and duplicate-free (the defect fix).
- Flag OFF: unchanged (exit 0 before any I/O).
- New keys / logs / metrics: none.
- Failure table: a raising page -> the existing `guarded` WARNING and the dependent metrics omitted (unchanged); a pipeline exposing neither name -> AttributeError inside `guarded("hosts")` -> no host metric (unchanged class); a redis-py pipeline -> host metrics present (was: none).

### 3. Change list
Byte copy first. `scripts/cron_kb_coverage.py`: `PAGE_ORDER_COLUMN = "id"` beside `SEARCH_LOG_COLUMNS` (:35); `_paged` gains `.order(PAGE_ORDER_COLUMN)` (:103-105 region); `_paged` docstring "ordered by the primary key id"; `_hosts.read` uses the fallback (:273-276) with the live_robots comment. New `tests/test_s81_d17b_coverage_paging.py`. No other file.

### 4. Existing pins
4.1 Deliberate changes: none (no frozen row pins the unordered call or `pipe.exec()` by name; `_Pipe.exec` exists so the frozen R5 `("pipeline.exec", n)` record still appears under the fallback).
4.2 Stay green: `tests/test_s81_d17_coverage.py` R1-R8 (r9 environmental), `tests/test_s81_g4_gate_rows.py`, `tests/test_s81_kb_schema.py`, `tests/test_s81_d14_live_robots.py` (not edited; listed because it pins the form D17b copies).

### 5. RED tests: `tests/test_s81_d17b_coverage_paging.py`
Hermetic; reuses the frozen D17 fakes and world through `importlib.import_module("tests.test_s81_d17_coverage")` (its `_Client`, `_Query`, `_Redis`, `_run`, `EXPECTED`) plus two local fakes; the flag set per row; `kb_seed_common._now` patched as the D17 harness does; pure ASCII, LF.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_every_page_ordered_by_id` | DRY run on the D17 world: every select op of the eight relations records `orders == [("id", False)]` (a recorder subclass of the frozen `_Query` that appends to the op dict) | AssertionError (`[]`) | 3 |
| R2 | `test_r2_unordered_store_paged_completely` | a fake `_UnstableClient` whose select WITHOUT an order returns, for range request k, the slice of the rows rotated by 37*k (deterministic, models PostgREST's unstable order), and WITH `order("id")` the id-sorted slice; 1,200 synthetic kb_products rows (ids `fragrances|b|n-00001..`): the run's `kb.products.total` n == 1200 AND the set of product ids the job read (recorded) has 1200 distinct members, no duplicate | AssertionError (duplicates / missing ids) | 3 |
| R3 | `test_r3_redis_py_pipeline_executes` | a `_PyPipe` exposing ONLY `execute()` (no `exec` attribute: `__getattr__` raises AttributeError for `exec`): host metrics `host.robots_skip:<host>` present with the D17 R5 values (5 / 16); totals line ends `redis=1` | AssertionError (no host metric, redis=0) | 3 |
| P1 | `test_p1_upstash_pipeline_uses_exec_never_queueing_execute` | a `_UpPipe` with `exec()` and a ONE-ARGUMENT `execute(command)` that records a call and returns self: host metrics identical to D17 R5; the recorder shows `exec` called once and `execute` never | green | base |
| P2 | `test_p2_small_tables_byte_identical` | the D17 world: the APPLY upsert payload and the `--report` markdown bytes equal a base literal recorded by the RED agent at base (sha256 constant named `REPORT_SHA256_BASE`, a 64-hex built from a stored literal split in two halves so no single 64-hex literal sits in the file) | green | base |
| P3 | `test_p3_flag_off_no_io` | full configuration (redis fake with hashes, client fake with rows) and the flag OFF in each spelling: exit 0, zero client ops, zero redis calls | green | base |

Counts: RED 3, PIN 3.

### 6. Mutation table
| M | Mutation | Killed by |
|---|---|---|
| M1 | order call removed | R1, R2 |
| M2 | `order("id", desc=True)` | R1 |
| M3 | order placed on only the first page (page 0) | R1 (every op), R2 |
| M4 | fallback reversed (`execute` preferred) | P1 |
| M5 | fallback removed (`pipe.exec()` only) | R3 |
| M6 | `PAGE_ORDER_COLUMN = "created_at"` | R1 |

### 7. Comm set: the group's (section 12).

### 8. CLAUDE.md row
`- D17b COVERAGE-PAGING (no new flag; rides ENABLE_KB_COVERAGE_ROLLUP): scripts/cron_kb_coverage.py _paged orders every paged read by the primary key id (PostgREST paging without an ORDER BY is not stable above PAGE_SIZE 500), and the host pipeline runs through the live_robots exec / execute fallback (upstash-redis 1.7.0: exec; its one-argument execute only queues; redis-py: execute); DRY / apply output unchanged for a table under 500 rows. RED tests/test_s81_d17b_coverage_paging.py.`
Owner step: re-read the next kb-coverage DRY run log after the merge (names only).

### 9. Stated limits
- L-D17b-1: ordering on `id` adds a sort on each page read (an index scan on the pk; no measured cost on the real tables, which are near-empty before 045 / the seed runs).
- L-D17b-2: the `kb_offers_latest` view's DISTINCT ON order is per (variant, merchant, market, currency); the outer `ORDER BY id` re-sorts the view's rows (correct, a sort over the whole view per page; the view is small).

### 10. Out of scope: MAX_PAGES (200 x 500 = 100,000 rows cap, unchanged); a keyset (id > last) paging rewrite.
### 11. Open questions: none.

---

## Unit D22c PROFILE-SELECT + VARHINT-RETIRE

### 1. Base state (measured at 6869a3e6)

| # | Site | Measured |
|---|---|---|
| 1.1 | `app/services/structured_comparison_service.py:5931-5955` `_update_behavior_profile` | inside ONE try: (a) `comparisons.select("category_used, products, created_at").eq(user_id).order(created_at desc).limit(50)` (:5945); (b) `comparison_feedback.select("useful").eq(user_id).limit(200)` (:5946); (c) `user_events.select("event_type, metadata").eq(user_id).order(created_at desc).limit(200)` (:5947); `build_behavior_profile(comparisons, feedback, events)` (:5949-5951); `users.update({"behavior_profile": profile}).eq("id", user_id)` (:5952); `except Exception as e: logger.warning(f"Failed to update behavior profile: {e}")` (:5953-5954). Each execute goes through `run_db` (offloaded only under `ENABLE_SYNC_DB_OFFLOAD`). |
| 1.2 | the writers' column | `app/services/feedback_service.py:268-272` and `:302-306` write `{"event_type", "event_data"}`; `app/api/feedback_routes.py:220-227` builds `event_data`; no repo migration creates user_events. |
| 1.3 | **the comparisons select is ALSO phantom (measured record, not re-probed)** | `docs/investigations/2026-09-06-full-review-state/partial-m22-code-review.json:1001-1016` (CR-DATA-MIGRATIONS-05, P1, "measured", 2026-09-06): the live client returned 42703 for `comparisons.select('category_used, products, created_at')` ("column comparisons.category_used does not exist") AND for `user_events.select('event_type, metadata')`; the live comparisons columns were `created_at, full_response, id, input_type, product_names, query, schema_version, share_token, user_id`; 0 of 18 users had a non-empty behavior_profile. No migration since adds `category_used` / `products` to comparisons (grep of `migrations/*.sql` for `category_used`: no hit; `001_update_comparisons.sql` adds full_response / query / input_type). So the FIRST select (a) raises before (c) is reached: **repointing (c) alone would leave the write dead in production**. This spec therefore repoints BOTH (a) and (c) under the one new flag (deviation D-1 from the brief's one-select wording; Q-D22c-1). The category and product list live inside `full_response` (`response_builder.py:2255` `result["products"] = product_data`, `:2286` `result["category_used"] = category_used`); the PostgREST JSON-path alias idiom `alias:full_response->>key` is already in production use by `scripts/cron_learning.py:72-83` (`category:full_response->>category_used`, measured through the G5 RED fakes and merged in #388). |
| 1.4 | callers + label | `_fire_and_forget(self._update_behavior_profile(user_id), "behavior_profile_update")` at `:4856-4860` (sync path) and `:5732-5736` (streaming); `_fire_and_forget` (:354-365) delegates to `app.utils.async_utils.fire_and_forget`. Unchanged. |
| 1.5 | behavior_service | `build_behavior_profile` (`app/services/behavior_service.py:156-170`) reads comparisons' `category_used`, `created_at`, `products[*].price` (:32-98) and events' `event_type` + `metadata` (`.get("metadata", {})`, :111-117); unchanged by this unit (the aliases deliver exactly these keys). |
| 1.6 | readers of `users.behavior_profile` | `_fetch_behavior_profile` (:5917-5929, returns None for `{}`) -> `compute_scores(behavior_profile=...)` (:4596 / :5467) -> `scoring_service.py:1402-1404` `apply_behavioral_adjustments` (uses ONLY `dimension_sensitivity`, :2914-2924) and the label (:1636-1652: with `ENABLE_BEHAVIORAL_DIM_TRANSLATION` OFF, ANY truthy profile labels `scoring_method = "behavioral"`, ahead of `personalized`); `home_routes.py:754-790` and `profile_routes.py:495-506` (fallback priority from `dimension_sensitivity`); `kb_serve.log_verdict_key` (:362-371: a non-None profile makes the compare "personalised", so no would-hit verdict-key line). |
| 1.7 | what a first real write changes (Q3) | `dimension_sensitivity` is computed only from `tab_switch` events; NO file under `SmartCompareApp/src` emits `tab_switch` or `dwell_ms` (grep: zero hits), so with today's client the written profile carries `category_affinity`, `price_range_preference`, `winner_agreement`, `comparison_count`, `last_updated` and an EMPTY `dimension_sensitivity`: the weights do not move; what moves is the `scoring_method` label (`behavioral` for every returning user with a profile while `ENABLE_BEHAVIORAL_DIM_TRANSLATION` is OFF; with it ON the label follows the weights, so it stays as today), the verdict-cache eligibility (S81-18 H8), and the Home / Profile fallback (unchanged while `dimension_sensitivity` is empty). The client renders no `scoring_method` (grep of `SmartCompareApp/src/**/*.tsx`: zero hits). Privacy: `docs/privacy-data-inventory.md:38` already declares the `tab_switch` read-back into `behavior_profile` as Personalization (no text change). |
| 1.8 | pins of the path | `tests/test_behavior_integration.py:152-191` (MagicMock chain; asserts `build_behavior_profile` called once; the error path swallowed), `tests/test_m18_offload_sweep_residual.py:147-200` (4 executes off-loop with `ENABLE_SYNC_DB_OFFLOAD`; the feedback select bounded); both run with the new flag unset: unchanged. |
| 1.9 | flag idiom in scs | `spec_confidence_cache_enabled()` (:368-384): `os.getenv("ENABLE_X", "").strip().lower() in ("true","1","yes","on")`, a module function read per call. |
| 1.10 | VARHINT dead block | `app/services/price_service.py:9054` (comment naming the file), `:9066-9068` `_VARHINT_LEARNED_PATH`, `:9156-9172` `_varhint_append_learned`, its ONE caller `:9210-9212` inside `_consult_variant_llm_hint` (:9175-9213), which runs only under `variant_llm_hint_enabled()` (:9073; B3b, default OFF, read per call); no reader of the file anywhere (grep of app/ scripts/ tests/ data/: only price_service and the test suppression). `data/variant_hint_learned.json` (817 bytes) holds only a `_metadata` object (no learned entry). `tests/test_variant_llm_hint_b3b.py:64-68` fixture `no_learned_write` monkeypatches `ps._varhint_append_learned`; 13 tests take it as a parameter (:100, :107, :113, :120, :127, :164, :182, :205, :238, :251, :265, :299, :311). Other mentions are historical docs (`docs/investigations/2026-08-31-m13-*`), not edited. |
| 1.11 | corpus gate (Q3) | `scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof` (the `_proof` corpus lives in that checkout, not in this worktree). `price_service.py` has not changed since `32f9b76a` (G3 fix round 1), and G3 measured OVERALL SHA256 `601338261705718a85c8c4ff281cefd47368a8c7aa1b12c2aad501baae18a1ef` (n=414, calls=1656) at that bytes; app/ changes since 0b19de5b are kb_* / routes / scs only (git diff --stat 0b19de5b..6869a3e6), none on the corpus path. Expected base SHA = 6013...a1ef; the RED agent re-measures it at base (not run by this spec: a 7 min non-pytest run). |
| 1.12 | base pass state | D16b 1.15 run: test_variant_llm_hint_b3b, test_variant_hint_reference_b3a, test_behavior_integration, test_m18_offload_sweep_residual, test_behavior_dimension_translation all green at base. |

### 2. Contract

(1) PROFILE-SELECT
- Flag `ENABLE_BEHAVIOR_PROFILE_EVENT_DATA` (new; carries no gitleaks keyword), default OFF, read PER CALL by a module function `behavior_profile_event_data_enabled() -> bool` in structured_comparison_service (the :368 idiom), called ONCE per `_update_behavior_profile` call, as the FIRST statement inside the try (before any client is built), its result held in a local. OFF -> the base body runs unchanged: the same three select strings, the same order, the same update, the same except arm and warning text.
- ON: the two selects become
  - comparisons: `"category_used:full_response->>category_used, products:full_response->products, created_at"` (same `.eq("user_id")`, `.order("created_at", desc=True)`, `.limit(50)`);
  - user_events: `"event_type, metadata:event_data"` (same eq / order / limit 200);
  - the feedback select unchanged;
  - before `build_behavior_profile`, rows are normalised (ON only): a comparisons row whose `products` is not a list gets `[]`; an events row whose `metadata` is not a dict gets `{}` (so a NULL `event_data` cannot raise inside behavior_service). Nothing else changes: the update call, the except arm, the warning text, the `behavior_profile_update` label.
- Constants: `_PROFILE_COMPARISON_COLUMNS_V2` and `_PROFILE_EVENT_COLUMNS_V2` (module constants; names carry no gitleaks keyword); the OFF strings stay inline literals as at base (byte identity of the OFF lines).
- Flag-OFF identity (the main invariant), pinned by the golden `tests/fixtures/s81_d22c_flag_off_golden.json`: for three fake-store scenarios, the ordered call list on the fake client (table, select string, every filter / order / limit with its arguments, execute, update payload) plus whether the warning was logged, recorded at base by the RED agent: (A) LIVE-LIKE: the fake raises a PostgREST-shaped error (an Exception subclass with `code = "42703"`) for any selected base column outside the live set {comparisons: created_at, full_response, id, input_type, product_names, query, schema_version, share_token, user_id; comparison_feedback: id, user_id, comparison_id, useful, created_at; user_events: id, user_id, event_type, event_data, comparison_id, created_at; users: id, behavior_profile} -> ONE execute (comparisons), no update, one WARNING starting `Failed to update behavior profile: `; (B) PERMISSIVE: the fake answers every select (rows given) -> four executes and the update payload with `last_updated` normalised (behavior_service calls `datetime.now()`: the test patches `behavior_service.datetime` with a fixed-clock subclass); (C) EVENTS-ONLY-RAISE: only user_events raises -> three executes, no update. The golden is compared for the spellings unset / "false" / " 0 " / "OFF" / "" with the FULL configuration present (the flag variable set to those values, `ENABLE_SYNC_DB_OFFLOAD` unset, a recorder on `run_db`).
- ON rows: scenario A' (the live-like fake) -> four executes, ONE `users.update` with a NON-EMPTY profile whose `category_affinity` comes from `full_response.category_used` values and whose `price_range_preference.avg_price_viewed` comes from `full_response.products[*].price.amount` (the fake resolves the alias paths), `dimension_sensitivity` from `tab_switch` rows' `event_data` (`to`, `dwell_ms` >= 2000).
- Failure table: ON + a raising store -> the same except arm (WARNING, no raise, no update); ON + `event_data` NULL -> `{}` (no raise); ON + `full_response` NULL -> `category_used` None (behavior_service maps it to its default bucket), `products` [] ; flag spelled garbage -> OFF.
- Seams: `database_service.get_supabase_client` and `behavior_service.get_behavior_service` (both imported function-locally at call time, as the existing pins patch them).
- Interactions stated (no code): with the flag ON and `ENABLE_BEHAVIORAL_DIM_TRANSLATION` OFF, every returning user with a written profile is labelled `behavioral` (weights unchanged while no client emits `tab_switch`); the S81-18 verdict-cache would-hit line stops for those users.

(2) VARHINT-RETIRE
- Deleted: `_VARHINT_LEARNED_PATH` (:9066-9068), `_varhint_append_learned` (:9156-9172), the call at :9210-9212, the `data/variant_hint_learned.json` file; the comment at :9054 rewritten ("caches the verdict" without the file clause) and the docstring of `_consult_variant_llm_hint` (":9183 (cached + learned)") rewritten to "(cached)". `_consult_variant_llm_hint` keeps every other behaviour: cache hit -> return; per-run cap; the LLM call; high-confidence verdict -> Redis cache write -> return.
- Identity: the price_service corpus gate OVERALL SHA256 at HEAD == at base with every flag OFF (expected `6013...a1ef`); the B3b suite green with the hint flag ON (nothing appended: no open() of any data path).
- Unflagged (R-A1: a change proven byte-identical; the deleted function had no reader and its only effect was a repo-file write that never happens on Railway's read-only image in practice).

### 3. Change list
Byte copies of every file first.
1. `app/services/structured_comparison_service.py`: `behavior_profile_event_data_enabled()` beside `spec_confidence_cache_enabled` (:368); the two `_V2` column constants beside it; inside `_update_behavior_profile` (:5931-5954): the flag read as the first try statement, a conditional choice of the comparisons and events select strings, the ON-only normalisation before `build_behavior_profile`. The OFF literals stay byte-identical on their lines (the `git diff -w` review shows only added lines and the two selects' string arguments moved into a conditional expression; the OFF strings remain the literal `"category_used, products, created_at"` and `"event_type, metadata"`).
2. `app/services/price_service.py`: the deletions and the two comment / docstring rewrites of 2(2). CRLF preserved.
3. `data/variant_hint_learned.json`: deleted (`git rm` by the orchestrator at commit; GREEN deletes the file on disk).
4. `tests/test_variant_llm_hint_b3b.py`: E1 (section 4.1).
5. New `tests/test_s81_d22c_profile_select.py`, `tests/fixtures/s81_d22c_flag_off_golden.json` (recorded at base by the RED agent through the RED file's own recorder function, `pytest` never writes it: the RED agent runs the recorder once through a small script, commits the JSON, pure ASCII, LF, `sort_keys`, `indent=1`), `tests/test_s81_d22c_varhint_retire.py`.
No other file (behavior_service.py, feedback_service.py, the readers in 1.6 untouched).

### 4. Existing pins
4.1 Deliberate changes:
- E1 `tests/test_variant_llm_hint_b3b.py`: the `no_learned_write` fixture (:64-68) is deleted and the parameter removed from the 13 test signatures listed in 1.10 (the fixture patches a symbol that no longer exists; `monkeypatch.setattr` with `raising=True` default would raise AttributeError). Reason: the dead write it suppressed is gone; R-row V4 replaces its intent (no data/ write).
4.2 Stay green: `tests/test_behavior_integration.py`, `tests/test_m18_offload_sweep_residual.py`, `tests/test_behavior_dimension_translation.py` (golden `tests/fixtures/behavioral_flag_off_golden.json`), the S81-ST1 offloop rows (`tests/test_s81_st1_usage_path_offloop.py`), `tests/test_variant_llm_hint_b3b.py` (after E1), `tests/test_variant_hint_reference_b3a.py`, `tests/test_hermeticity_pins.py`, `tests/test_ci_gates.py`.

### 5. RED tests

`tests/test_s81_d22c_profile_select.py` (hermetic; `import app.main` first; a local `_FakeSupabase` with the live column set of 2(1) and a JSON-alias resolver for `alias:col->>key` / `alias:col->key` / `alias:col`; synthetic user id built at run time `"u-" + "0"*8`; netguard on; the flag set per row with monkeypatch only):

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_reader_spellings` | `getattr(scs, "behavior_profile_event_data_enabled", None)` callable; ON for "true", " TRUE ", "On", "1", "yes"; OFF for unset, "", "false", " 0 ", "OFF", "garbage" | AssertionError (absent) | 3.1 |
| R2 | `test_r2_on_selects_live_columns` | flag ON, live-like fake: the comparisons select string == `"category_used:full_response->>category_used, products:full_response->products, created_at"`, the user_events select == `"event_type, metadata:event_data"`, the feedback select == `"useful"`; four executes | AssertionError | 3.1 |
| R3 | `test_r3_on_writes_a_profile` | flag ON, live-like fake with 2 comparisons (full_response category `fragrances`, products with BHD amounts 40.0 / 60.0), 1 feedback row useful True, 2 user_events (`tab_switch` with event_data `{"to": "specs", "dwell_ms": 5000}`, `share` with event_data None): exactly ONE `users.update` whose payload `behavior_profile` has `category_affinity == {"fragrances": 1.0}`, `price_range_preference["avg_price_viewed"] == 50.0`, `winner_agreement["agreed"] == 1`, a non-empty `dimension_sensitivity`, `comparison_count == 2`; no WARNING | AssertionError (no update) | 3.1 |
| R4 | `test_r4_on_null_payloads_do_not_raise` | ON, events with `event_data` None only and a comparison with `full_response` None: one update, no WARNING | AssertionError | 3.1 |
| R5 | `test_r5_flag_read_per_call` | two consecutive calls, ON then OFF (env flipped between): the first issues the V2 strings, the second the base strings | AssertionError | 3.1 |
| P1 | `test_p1_flag_off_golden` | for each OFF spelling (unset, "", "false", " 0 ", "OFF") with the full configuration, scenarios A / B / C produce call lists and warning flags EQUAL to the golden JSON (loaded; its sha256 equals the in-file constant `GOLDEN_DIGEST`, split-built at run time) | green | base |
| P2 | `test_p2_on_raising_store_keeps_except_arm` | ON with a fake that raises on every execute: no exception escapes, one WARNING starting `Failed to update behavior profile: `, no update | green | base (the except arm exists) |
| P3 | `test_p3_label_and_call_sites_unchanged` | AST of the scs source: exactly two `_fire_and_forget(self._update_behavior_profile(user_id), "behavior_profile_update")` calls | green | base |
| P4 | `test_p4_behavior_service_untouched` | `behavior_service.py` text sha256 equals the base literal recorded by the RED agent (split-built) | green | base |

`tests/test_s81_d22c_varhint_retire.py`:

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| V1 | `test_v1_dead_symbols_gone` | `not hasattr(price_service, "_varhint_append_learned")` and `not hasattr(price_service, "_VARHINT_LEARNED_PATH")` | AssertionError | 3.2 |
| V2 | `test_v2_data_file_gone` | `not (ROOT / "data" / "variant_hint_learned.json").exists()` | AssertionError | 3.3 |
| V3 | `test_v3_no_suppression_left` | the text of `tests/test_variant_llm_hint_b3b.py` contains neither `no_learned_write` nor `_varhint_append_learned`; the text of price_service.py contains no `variant_hint_learned` | AssertionError | 3.2, 3.4 |
| V4 | `test_v4_on_path_writes_no_file` | hint flag ON with the B3b preconditions (the exact gate ON, the axes knob as `tests/test_variant_llm_hint_b3b.py`'s `hint_on` fixture sets them), the Redis fake, `openai_service.disambiguate_variant_line` patched to a high-confidence `distinct`: `await ps._consult_variant_llm_hint(...)` returns `"distinct"`, the Redis fake holds the verdict, and a recorder on `builtins.open` saw NO call whose path contains `data` (at base the real function opens the data file: the recorder sees it) | AssertionError | 3.2 |
| P5 | `test_p5_consult_behaviour_kept` | cache hit returns the cached verdict without a client; the cap returns `unknown` without a call; low confidence -> `unknown` (restating B3b rows with recorders, no data write) | green | base |

Counts D22c: RED 9 (R1-R5, V1-V4), PIN 5 (P1-P5).

Corpus gate (GREEN, not a pytest; never beside a pytest): `python scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_VARIANT_LLM_HINT,ENABLE_BEHAVIOR_PROFILE_EVENT_DATA --out <notes>/gate_<side>.json`, base (a detached scratch worktree at 6869a3e6, or the RED agent's measurement) and head; the two OVERALL SHA256 lines equal (n=414, calls=1656).

### 6. Mutation table
| M | Mutation | Killed by |
|---|---|---|
| M1 | the ON events select keeps `metadata` | R2, R3 |
| M2 | the ON comparisons select keeps the phantom columns | R2, R3 |
| M3 | the flag reader drops `.strip()` | R1 |
| M4 | the flag cached at import (a module constant) | R5 |
| M5 | the ON normalisation removed | R4 |
| M6 | the OFF branch uses the V2 strings (flag inverted) | P1, R2 |
| M7 | `_fire_and_forget` label changed | P3 |
| M8 | VARHINT: the call at :9210 kept with a no-op stub | V1 (symbol present) |
| M9 | VARHINT: the Redis verdict write dropped with the deletion | P5 (cached verdict absent) / V4 |

### 7. Comm set: the group's (section 12) (D22c drives its size: structured_comparison_service + price_service and their importers).

### 8. CLAUDE.md rows
`- ENABLE_BEHAVIOR_PROFILE_EVENT_DATA (D22c PROFILE-SELECT, default OFF, read PER CALL by structured_comparison_service.behavior_profile_event_data_enabled at the top of _update_behavior_profile): the fire-and-forget profile write has raised inside its except arm on every call because two selects name phantom columns (comparisons category_used / products and user_events metadata; the M22 review measured 42703 on both, 2026-09-06); ON repoints them at the live columns (category_used:full_response->>category_used, products:full_response->products, created_at; event_type, metadata:event_data) and normalises NULL payloads, so users.behavior_profile is written for the first time; OFF is byte-identical, pinned by tests/fixtures/s81_d22c_flag_off_golden.json. Effect after the flip: no weight moves while no client emits tab_switch (dimension_sensitivity stays empty); the scoring label becomes behavioral for returning users while ENABLE_BEHAVIORAL_DIM_TRANSLATION is OFF; the S81-18 would-hit verdict line stops for profiled users. Precondition: App Review approval of the build in review and the owner's yes; canary alone: the scoring label share and the Failed to update behavior profile WARNING rate (expected to fall to 0). RED tests/test_s81_d22c_profile_select.py.`
`- D22c VARHINT-RETIRE (unflagged dead-code deletion, R-A1): price_service._VARHINT_LEARNED_PATH, _varhint_append_learned, its one call and data/variant_hint_learned.json deleted (no reader; reachable only under the B3b ENABLE_VARIANT_LLM_HINT, default OFF); the Redis verdict cache is the only store; the corpus gate OVERALL SHA256 is unchanged. RED tests/test_s81_d22c_varhint_retire.py.`
Owner steps (names only): after approval, set `ENABLE_BEHAVIOR_PROFILE_EVENT_DATA=true` on web alone in its window; a dated ledger line; watch the two canary items; rollback = unset (per call).

### 9. Stated limits
- L-D22c-1: the first flipped write changes returning users' scoring label (and the verdict-cache eligibility) but not their weights until a client emits `tab_switch`; a future client that emits it moves weights within the +-10 pct behavioural cap.
- L-D22c-2: the ON comparisons select reads the `products` JSON subtree of up to 50 rows per compare (heavier than the base select, which never succeeded); fire-and-forget, off the response path.
- L-D22c-3: a malformed `dwell_ms` (non-number) still raises inside behavior_service and lands in the except arm (no write), as base.
- L-D22c-4: the live column set is taken from the 2026-09-06 measured record (CR-DATA-MIGRATIONS-05), not re-probed (agents never probe production); if a column was added since, ON still reads the right data (the aliases name existing columns).
- L-D22c-5: deleting the learned-file write removes a convergence log that never had an entry; promotion into `data/variant_hint_reference.json` stays a manual step from the Redis cache.

### 10. Out of scope
behavior_service changes; the `comparison_feedback` select; any migration adding columns; a backfill of profiles (the next compare of each user writes it); the B3b flag itself.

### 11. Open questions
- Q-D22c-1 (deviation D-1): the brief names only the user_events select; the measured record shows the comparisons select raises FIRST, so the spec repoints both under the one flag. Ruling requested: accept (recommended; otherwise the flag is a no-op in production) or split the comparisons repoint into its own unit.
- Q-D22c-2: the flag name `ENABLE_BEHAVIOR_PROFILE_EVENT_DATA` covers both selects; an alternative `ENABLE_BEHAVIOR_PROFILE_REBUILD` (the M22 proposal) reads better given D-1. Default: keep the brief's name.

---

## Unit D22d LEARNING-HARDENING

### 1. Base state (measured at 6869a3e6)

| # | Site | Measured |
|---|---|---|
| 1.1 | `scripts/cron_learning.py:273-282` `_page` | select, filters, `.order("id")` (`_ORDER_COLUMN`, :104), `.range(start, end)`, `TypeError` on a non-list. |
| 1.2 | `:285-298` `_read_window` | id-ordered pages of `common.PAGE_SIZE` (500) up to `cap`, "capped" / "ok". |
| 1.3 | `:301-310` `_read_by` | per chunk of `IN_CHUNK` = 100 values: ONE `_page(..., 0, IN_CHUNK * 8 - 1)` = `range(0, 799)`, no further page; status "ok" even when a chunk had more than 800 rows (L14, RB-G5-3). Callers: comparisons by id (:522-524; at most 100 rows per chunk since ids are unique) and kb_specs by product_id (:575-578; a product can hold many spec rows). |
| 1.4 | `:181-184` `_field_name` | `_FIELD_RE` (`^[a-z][a-z0-9_]{0,63}$`) AND `_clean` -> the raw name, else `other`; no counter. `_clean` (:170-174) applies `_UNCLEAN_RES` (:111-117: uuid, 64-hex, at sign, the BH prefix, an 8-digit run). |
| 1.5 | `:549-561` the kb_feedback loop | `_field_name(raw_field)` for a spec_wrong case; an unclean raw name maps silently to `other`. `main` creates `dropped = [0]` (:703) AFTER `_gather`; `_grounding` / `_exemplars` / `_eval_candidates` increment it; the report key `dropped_deidentify` (:765) and the metric `learning.dropped.deidentify` (value, n) = (dropped, dropped) (:626). |
| 1.6 | GR6 (`tests/test_s81_g5_gate_rows.py:266-297`) | six kb_feedback rows (3 x an 8-digit field name `f12345678`, 3 x an at-sign name), both mapped to `other`; asserts `run.report["dropped_deidentify"] == 0` (:286) - "the measured GREEN contract" under RB-G5-9. |
| 1.7 | render sites (L15, RB-G5-7) | the markdown exemplar line `"- %s %s: %s || %s"` with the two product names (:657-658), the log lines `exemplar ... names=%s || %s` (:730-731) and `eval_case ... names=%s || %s` (:734-735); names are user-derived (`comparisons.product_names`) and pass `_clean` even with a newline or ESC inside; `_write_md` opens with `encoding="ascii", errors="backslashreplace"` (:660), which escapes non-ASCII but leaves C0 controls (newline, CR, ESC, TAB) raw; logging leaves all raw. The JSON report is written by `common.write_report` (json, which escapes controls). Cluster / proposal cells carry closed vocabularies or `_field_name` output (regex-safe). |
| 1.8 | flag | `learning_mode()` (:142-143) read FIRST in main; off -> one INFO line, exit 0 before I/O. |
| 1.9 | D22 frozen rows touching the edit | R6 (`tests/test_s81_d22_nightly_learning.py:849-886`: every select `orders == [("id", False)]`; the specs `in_` filter on product_id), R7 (:895-918, the windowed ranges only), R14 (:1136-1167, `dropped_deidentify >= 1`), R29 log templates (:1447+); the default world's kb_feedback field names are clean vocabulary (:408-419), so their exact dropped values do not move. G5-GR1..GR5 / GR7 worlds hold no unclean kb_feedback field (measured: only GR6's `_kb_field_world` does). |
| 1.10 | base pass state | D16b 1.15 run: test_s81_d22_nightly_learning and test_s81_g5_gate_rows all green. |

### 2. Contract
- (1) `_read_by(client, table, columns, column, values, cap)`: per chunk of 100 sorted values, id-ordered pages `range(offset, offset + n - 1)` with `n = min(common.PAGE_SIZE, cap - len(rows))`, appending each page, until a page shorter than `n` (next chunk) or `len(rows) >= cap` (return `rows[:cap], "capped"`); else `rows, "ok"`. The filter (`in_` on the column), the columns and `order("id")` are unchanged. For a chunk under 500 rows: ONE request `range(0, 499)` (was `range(0, 799)`; unpinned; the comparisons read is always this case). For a kb_specs chunk above 500 rows: further pages until complete (was: silently cut at 800).
- (2) The kb_feedback loop: when `raw_field` is a str and `not _clean(raw_field)`, the per-run de-identification counter is incremented once per ROW (the mapping to `other` and the case are unchanged). Plumbing: `_gather` returns an additive key `"dropped_fields": <int>` in its internal dict, and `main` seeds `dropped = [gathered["dropped_fields"]]`. Report keys unchanged (`dropped_deidentify` carries the total); the metric unchanged in name. A clean off-vocabulary name (fails `_FIELD_RE` only, e.g. `Bad-Name`) maps to `other` and is NOT counted (it is not a de-identification event). kb_gaps field names are not counted (out of the brief; Q-D22d-1).
- (3) `_render(text) -> str`: every character in U+0000..U+001F, U+007F..U+009F, U+2028, U+2029 becomes `\xNN` (two lowercase hex digits; U+2028 / U+2029 become `\u2028` / `\u2029`); every other character unchanged (a backslash is NOT doubled). Applied to the two product names at the three render sites of 1.7 (the markdown line and the two log lines). A name without such a character renders byte-identically. The JSON report keeps the raw names (json already escapes them). Log lines stay templates of constants, ints and the escaped names; the de-identification screen is unchanged and still runs before any render.
- Flag OFF: exit 0 before any I/O (unchanged). DRY / apply: unchanged except the three behaviours.
- Failure table: a raising specs page -> `_Tables.read` marks kb_specs error (unchanged); a capped specs read -> status "capped" and the `learning.capped.kb_specs` metric (unchanged mechanism, now also reachable through paging).

### 3. Change list
Byte copy first. `scripts/cron_learning.py`: `_read_by` body (:301-310); `_render` beside `_clean` (:170); the kb_feedback loop counter (:550-561) and `_gather`'s return dict (:603-606); `main` seeds `dropped` (:703); the three render sites (:657-658, :730-731, :734-735). `tests/test_s81_g5_gate_rows.py`: E2. New `tests/test_s81_d22d_learning_hardening.py`. No other file.

### 4. Existing pins
4.1 Deliberate change:
- E2 `tests/test_s81_g5_gate_rows.py:286`: `assert run.report["dropped_deidentify"] == 0` -> `== 6` (the six unclean kb_feedback rows of `_kb_field_world`), plus the docstring's last sentence (:278-280) rewritten: "D22d counts each unclean field-name row in learning.dropped.deidentify (G5-GR6 amended, E2)". Every other GR6 assertion (the `other` cluster, cases / actors (6, 3), the proposal `("other", [], "needs_operator")`, the no-raw-name texts) stays.
4.2 Stay green: `tests/test_s81_d22_nightly_learning.py` (all 57 rows incl. R6 orders, R7 ranges, R14, R29), `tests/test_s81_g5_gate_rows.py` GR1-GR5 / GR7, `tests/test_s81_kb_schema.py` (the two cron_learning P02 rows).

### 5. RED tests: `tests/test_s81_d22d_learning_hardening.py`
Hermetic; drives `scripts/cron_learning.py` through the frozen D22 RED file's fake client and world builders (`importlib.import_module("tests.test_s81_d22_nightly_learning")`: `_run`, `_rid`, `_dev`, `_cid`, `NOW`, `T_IN`, `T_KBFB`, `T_SPECS`, the column constants), the autouse env fixture of the G5 gate-rows file restated (flag and knobs unset, `common._now` patched); synthetic names built at run time; pure ASCII, LF (control characters built with `chr()`).

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_specs_grounding_survives_paging` | world: product P (synthetic id) with 3 wrong kb_feedback rows on field `season` from 3 devices; kb_specs: 900 cited rows of P on other fields with ids `row-ks-a-0000..0899` and ONE cited `season` row with id `row-ks-z-final` (sorts last): the spec_wrong / kb / season proposal has `grounding == [{"product_id": P, "field": "season", "source_url": <url>}]` and action `recheck_source` (or the action `_action` gives for a non-empty grounding, read from the module) | AssertionError (grounding `[]`) | 3 |
| R2 | `test_r2_specs_pages_ranges` | same world, flag "true": the kb_specs select ranges == `[(0, 499), (500, 999)]` (one chunk, two pages, the second short), every one `orders == [("id", False)]`; `report["tables"]["kb_specs"] == {"rows": 901, "status": "ok", "error": None}` | AssertionError (`[(0, 799)]`, rows 800) | 3 |
| R3 | `test_r3_specs_cap_across_pages` | same world with `LEARNING_MAX_ROWS=100` (the knob floor): ranges == `[(0, 99)]`, status "capped", `learning.capped.kb_specs` == (100, 100) | AssertionError (`[(0, 799)]`) | 3 |
| R4 | `test_r4_unclean_field_counted` | the GR6 world (imported from `tests.test_s81_g5_gate_rows._kb_field_world`): `report["dropped_deidentify"] == 6` and metric `learning.dropped.deidentify` == (6, 6) for "true" and "apply" | AssertionError (0) | 3 |
| R5 | `test_r5_control_chars_escaped_on_render` | one confirmed comparison (the D22 `_confirmed_rows`-style builder) whose product names are `"Nova" + chr(10) + "[LEARNING] forged"` and `"Dune" + chr(27) + "[2J" + chr(0x2028) + "x"`: in the markdown file text and in every captured log message, no character in the control set of 2(3) appears; the exemplar log line contains `Nova\x0a[LEARNING] forged` (the 4-char escape) and no log record's message contains a raw newline | AssertionError (raw newline) | 3 |
| R6 | `test_r6_render_helper` | `getattr(mod, "_render")` exists; `_render("a" + chr(9) + "b") == "a\\x09b"`; `_render(chr(0x85)) == "\\x85"`; `_render(chr(0x2029)) == "\\u2029"` | AssertionError (absent) | 3 |
| P1 | `test_p1_clean_names_byte_identical` | the default D22 world: the markdown file bytes and the `exemplar` / `eval_case` log lines equal base literals recorded by the RED agent (sha256 of the md, split-built constant; the log lines as literals) | green | base |
| P2 | `test_p2_report_keeps_raw_names` | R5's world: the JSON report's exemplar `product_names` equal the raw strings (json-escaped on disk, raw after `json.loads`) | green | base |
| P3 | `test_p3_clean_off_vocabulary_not_counted` | kb_feedback field `Bad-Name` (clean, fails the regex): maps to `other`, `dropped_deidentify == 0` | green | base |
| P4 | `test_p4_comparisons_read_single_page` | the default world: every comparisons select carries one `in_` on id, `orders == [("id", False)]`, and returns all its rows (rows == the 8 ids) | green | base (range end differs, rows equal) |
| P5 | `test_p5_flag_off_no_io` | full configuration (knobs set to synthetic values, the fake with every table) and the flag OFF in each spelling: rc 0, one INFO line, zero client ops | green | base |

Counts: RED 6, PIN 5.

### 6. Mutation table
| M | Mutation | Killed by |
|---|---|---|
| M1 | `_read_by` keeps one page per chunk | R1, R2 |
| M2 | page size `PAGE_SIZE + 1` / off-by-one end | R2 |
| M3 | cap ignored inside a chunk | R3 |
| M4 | the counter increments per distinct field instead of per row | R4 (6 vs 2) |
| M5 | the counter also counts clean off-vocabulary names | P3 |
| M6 | `_render` applied to the md line only | R5 (log) |
| M7 | `_render` escapes a backslash too | P1 only if a base name holds one (none) -> EQUIVALENT for the corpus; reported for a ruling |
| M8 | `_render` misses U+2028 | R5, R6 |

### 7. Comm set: the group's (section 12).

### 8. CLAUDE.md row
`- D22d LEARNING-HARDENING (no new flag; rides ENABLE_LEARNING_JOB): scripts/cron_learning.py _read_by reads each 100-value IN chunk in id-ordered pages of 500 up to LEARNING_MAX_ROWS (closes L14: a product with more than 800 cited kb_specs rows lost its grounding); an unclean kb_feedback field name (a de-identification shape) now counts once per row in learning.dropped.deidentify while still mapping to other (G5-GR6 amended, E2); C0 / C1 control characters and U+2028 / U+2029 in product names are escaped as backslash-x on render in the log lines and the markdown report (closes L15; the JSON report keeps the raw value, json-escaped). RED tests/test_s81_d22d_learning_hardening.py.`
Owner step: re-read the next learning DRY run log after the merge.

### 9. Stated limits
- L-D22d-1: paging costs one extra request per 500 spec rows of a chunk (bounded by `LEARNING_MAX_ROWS`).
- L-D22d-2: kb_gaps field names are screened as before but not counted.
- L-D22d-3: a literal `\x0a` typed inside a stored name renders the same as an escaped newline (the backslash is not doubled; the JSON report disambiguates).

### 10. Out of scope: the judge, D22b, kb_gaps counting, any change to the de-identification shapes.
### 11. Open questions
- Q-D22d-1: count unclean kb_gaps field names too? Default: no (the brief and GR6 name kb_feedback only).

---

## 12. The group

### 12.1 Combined comm set (the union rule, re-derived at 6869a3e6)
Derivation (`<scratchpad>/g7spec/comm.py` + the import-closure script, read-only over the worktree): (a) module and symbol reference grep over `tests/**/test_*.py` for the six edited modules (structured_comparison_service, price_service, kb_operator, kb_serve, cron_kb_coverage, cron_learning) and the touched symbols (`_update_behavior_profile`, `behavior_profile_update`, `variant_hint_learned`, `_varhint`, `variant_llm_hint`, `build_behavior_profile`, `user_events`, `OperatorIngest`, `kb/ingest`, `_read_by`, `_paged`, `dropped_deidentify`, `behavior_profile`, the five flag names, `verify_flag_byte_identity`); (b) every importer of an edited module: the transitive import closure of the six modules inside app/ and scripts/ (107 modules, `<scratchpad>/g7spec/closure.txt`; app.main is in it) and every test that names a closure module stem (649 files), plus `app.main` / `app.api` / `TestClient` users; (c) the source-scanning pins (the forced list of the common brief: test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command*, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_secret_scan_static) and every test combining a source read (`inspect.getsource`, `ast.parse`, `__file__`, `read_text`, `read_bytes`) or a walker (`glob` / `rglob` / `os.walk` / `listdir` / `scandir` / `iterdir`) with an app / scripts / data path; (d) the CLAUDE.md readers by the import graph (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire) and every test naming CLAUDE.md; (e) tests/test_s81_kb_schema.py; (f) importers of the test-support helpers that reference edited modules (`_env_safety`, `_hermeticity`, `conftest`, `_gen_w4_13_flag_off_ledger`); MINUS the four `tests/test_precommit_hook*.py` files (the group edits no `.githooks`). No migration, processors.json or legal text changes, so no migration / manifest readers beyond those already in; no SmartCompareApp file, so the SmartCompareApp-scanning backend tests join only through (a)-(c).
Result: **691 files** (`<scratchpad>/g7spec/COMM_SET_G7.txt`, set sha256 `ab9758eddc0c5c7c7546425ac6e8bceaaaa105b793f313c624db44e4e1d2f8fa`), plus the five new RED files at GREEN (excluded from the base record; they are the units).

Base record (LC-6, stored by this spec): `<scratchpad>/harness/base_records/6869a3e655805afd3adbba43f99578dd79585934/ab9758eddc0c5c7c7546425ac6e8bceaaaa105b793f313c624db44e4e1d2f8fa.{files,header.txt,txt}`:
- 382 members reused from the SAME-sha S81-20 record `97218ca8...` (no file changed: same sha);
- 272 members reused per file under GC-9 from older records (167 <- 0b19de5b/90b85603, 99 <- e1491c97/4b65c5db, 6 <- 00e4120d/9a85c0b0; `<scratchpad>/g7spec/comm_reuse_older.txt`): each member's file unchanged since that sha, its text names no module stem changed since that sha, nor CLAUDE.md, nor app.main / TestClient when an app/api, app/middleware or app/main.py file changed, and it is no walker;
- 37 members RUN at 6869a3e6 in this worktree:
  `[pyt] tag=g7spec-comm-base-a start=2026-11-05 12:20:53 end=2026-11-05 12:21:03 elapsed=10s bound=1200s status=OK rc=0` (161 passed, 9 deselected; `[hermeticity] sentinel checked 161 test(s)`; `[netguard] blocked 1 attempt(s) from 0 node(s)` = one collection-time neutralized supabase.invalid connect, outside any test)
  `[pyt] tag=g7spec-comm-base-b start=2026-11-05 12:21:12 end=2026-11-05 12:21:39 elapsed=27s bound=1200s status=OK rc=0` (511 passed, 3 skipped; `[netguard] blocked 0`)
- the base FAILED set = **17 node ids** (all known environmental: the 2 auth_interceptor, 2 page_scraping, 2 personalization_bundle_c, the 2 prompt_truth tiktoken nodes, the 6 CRLF hygiene rows (d16 r10, d17 r9, s16 r27 x5 ... as listed in the .txt), s10 r06 lexicon CRLF, s19 r15 hygiene).
The GREEN / fix / rebase agent REUSES this record when its set and base match (LC-6) and runs the 691 + 5 at HEAD in chunks of <= 25 files (bound 1200; one pytest at a time); `comm -13` of the sorted FAILED sets must be EMPTY.

CI-order set (the group's own files, one call, bound 1200, flag OFF and again with the group's flags ON where a row needs them per row): the five RED files + test_s81_d16_operator_ingest, test_s81_s18_kb_first_serve, test_s81_g4_gate_rows, test_s81_d17_coverage, test_s81_d22_nightly_learning, test_s81_g5_gate_rows, test_variant_llm_hint_b3b, test_variant_hint_reference_b3a, test_behavior_integration, test_m18_offload_sweep_residual, test_behavior_dimension_translation, test_s81_kb_schema, test_s81_d14_live_robots, test_s81_s19_gap_queue, test_ci_gates, test_hermeticity_pins.

Fourteen client fences (D22c edits app/; CLAUDE.md and data/ change): run BY PATH from SmartCompareApp through the junction the orchestrator creates at GREEN (brand/inAppMark.u4c, clientTruth/{medicalNote,privacyManifest,shareTruth}.s74, clipboardFallbackService, config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService(+.edges), ResultsScreen.timeout). Measured: none of the fences reads structured_comparison_service.py, price_service.py, kb_*, cron_*, behavior_service.py or data/variant_hint_learned.json (grep of `SmartCompareApp/__tests__` for those names: only a comment in ResultsScreen.timeout.test.tsx:258 naming price_service.py:1752; that suite reads only `src/` files, :124-129). Expected: green, unchanged. The FULL jest runs once in the final round (LC-7; baseline 3,852 passed + the four nativeBundle.w37 drift nodes).

Other gates (cheapest first): ruff `--select E9,F63,F7,F82` and `py_compile` on the six edited Python files and the five RED files; `json.loads` on the golden; bytes > 127 = 0 in every new file; `git diff --stat` shows no whole-file diff (CRLF preserved); the secret scan (`tests/test_secret_scan_static.py`, in the set) and the added-line sweep (no 64-hex literal in one piece; no constant named with access / auth / api / credential / creds / key / password / secret / token: `GOLDEN_DIGEST`, `REPORT_SHA256_BASE`, `PAGE_ORDER_COLUMN`, `FUTURE_SKEW_SECONDS`, `_PROFILE_*_COLUMNS_V2` are clean); the corpus gate of D22c.

### 12.2 Combined footprint
app/: `app/services/kb_serve.py`, `app/services/kb_operator.py`, `app/services/structured_comparison_service.py`, `app/services/price_service.py`. scripts/: `scripts/cron_kb_coverage.py`, `scripts/cron_learning.py`. data/: `data/variant_hint_learned.json` (deleted). tests/: five new RED files, one new fixture, E1 `tests/test_variant_llm_hint_b3b.py`, E2 `tests/test_s81_g5_gate_rows.py`. CLAUDE.md. No migration, no `.github/`, no `.githooks/`, no `SmartCompareApp/`, no requirements, no railway config.

### 12.3 Shared-file plan
Section 0. The only file two units edit is `scripts/cron_kb_coverage.py` (D17b: `_paged`, `_hosts`; D16b: `_past`, `_field_shares`, `_ages`): disjoint hunks; GREEN applies D17b first then D16b; the RED files of both import the module fresh per row.

### 12.4 PR plan
ONE PR `feature/s81-g7-followups` -> main, body <= 25,600 bytes measured with python: a summary; one short section per unit (D16b, D17b, D22c, D22d: what, flag, RED file, counts); the E-rows table (E1 b3b fixture removal, E2 GR6 0 -> 6); the comm result (691 + 5, the base record id `ab9758ed...`, branch-only-new EMPTY); the corpus gate line (OVERALL SHA256 base == head); the fences and the full-jest figure; the stated limits by id (L-D16b-1..3, L-D17b-1..2, L-D22c-1..5, L-D22d-1..3); the owner steps names-only (D22c's flip after approval with its two canary items; the kb-coverage and learning DRY runs re-read after the merge; nothing else to flip); `[NATIVE READ]` EMPTY (no client copy). Mutation tables and per-row evidence go to specs/ files in the state folder.

### 12.5 CLAUDE.md
ONE block after the S81-G5 block (after its owner-steps bullet, CLAUDE.md:574 at base, before `## Tests`), heading `**SESSION 81 flags (S81-G7 FOLLOWUPS: D16b OPERATOR-INGEST-DATES + D17b COVERAGE-PAGING + D22c PROFILE-SELECT + VARHINT-RETIRE + D22d LEARNING-HARDENING, 2026-11-05; ONE new flag default OFF read PER CALL, unset in production by construction; the sixth SAFE group under LC-9; spec .qa-s80/S81-G7_UNIT_SPEC.md, rulings specs/RULINGS_S81_G7.md):**` followed directly (no blank line inside the block) by the five rows of sections 8 and one owner-steps bullet; and the :341 Feature Flags pointer clause gains `ENABLE_BEHAVIOR_PROFILE_EVENT_DATA` (S81-G7 D22c, default OFF): the row of the **SESSION 81 flags (S81-G7 FOLLOWUPS, ...)** block. Text constraints measured: no line containing both `scoring_method` and `enum` (test_behavior_dimension_translation.py:215-233 reads such lines), none of the five S23 forbidden phrases (test_s81_s23_bypass_retire.py:290-296), pure ASCII in the added text.

DEFECT_LEDGER ids (drafted, names only; the orchestrator files them): `D16b OPERATOR-INGEST-DATES`, `D17b COVERAGE-PAGING`, `D22c PROFILE-SELECT`, `D22c VARHINT-RETIRE`, `D22d LEARNING-HARDENING` (closing G4 stated minors on future dates and paging, M22 CR-DATA-MIGRATIONS-05 / issue #65 behind the flag, G5 L14 / L15 / GR6).

### 12.6 SAFE check (FOCUS surfaces)
| Surface | Touched? | Evidence |
|---|---|---|
| auth / tokens / sessions | no | the operator route keeps `verify_admin_key` untouched; D16b adds a body-field validator behind the flag gate (the 404 comes first) |
| quota / billing / refunds | no | no usage_service / text_routes / metering file |
| legal or privacy text | no | no app/legal or landing file; the profile read-back is already declared in docs/privacy-data-inventory.md:38 (not edited) |
| consent path | no | no aiConsent / consent route |
| security middleware | no | error_handler.py read, not edited |
| migrations | no | none added; D22c deliberately avoids adding columns |
| Redis / Lua scripts | no Lua; one Redis READ path in a dark cron (`_hosts` pipeline method choice, HGETALL only, no write, no script) and a deleted file write in price_service (the Redis verdict write unchanged) |
| App-Review-visible client surface | no client file; D22c (1) is dark and its post-flip effect is a backend label (`scoring_method` is not rendered by the client: measured) |
| secrets or key handling | no | no new credential name; nothing joins CREDENTIALS_UNSET |
Result: **no FOCUS surface; every unit stays in the group** (focus_surfaces_found empty). Note for the orchestrator: D22c (1)'s flip changes stored personalization state for every authed user (the M22 review's canary-alone advice); that is a flip-window item, not a merge-time surface.

Not done in this spec: the RED files, the golden, the corpus gate run at base (expected 6013...a1ef, re-measured by RED), the mutation runs, any production probe.
