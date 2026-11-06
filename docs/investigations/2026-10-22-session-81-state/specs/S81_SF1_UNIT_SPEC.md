# S81-SF1 SURFACES-BE -- unit spec

- Unit: S81-SF1 SURFACES-BE (FOCUS by LC-1: migrations 046 + 049, the App-Review-visible `surfaces` knob, a new stored user free text `correction`, one client line shipped only in the post-approval OTA). Lane A, session 86.
- Flags: `ENABLE_FEEDBACK_V2` + `ENABLE_SURFACES_FIELD` (both NEW names, default OFF, read PER CALL with the house idiom as the FIRST statement of every gated predicate) + the knob `APP_SURFACES_LIVE` (comma-separated chip keys from the CLOSED set {skincare, makeup}). New names, so unset in production by construction (Railway not read). The `VALID_EVENT_TYPES` widening and the event property allowlist DICT are unflagged (R-A1); the allowlist FILTER is under `ENABLE_FEEDBACK_V2`.
- Worktree: `C:/Users/SynAckITPC/Documents/AI/sc-s81-sf1`, detached at base `18cb9e04a36382fc417307500a092486f618d95e`; `git status --short` EMPTY before and after every probe of this spec (measured: 0 lines at start; no file of the worktree was written except this spec under the gitignored `.qa-s80/`).
- Branch (GREEN creates it): `feature/s81-sf1-surfaces-be`.
- Evidence: notes folder `<scratchpad>/sf1/` (`<scratchpad>` = `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/4478042e-6f11-47b0-addf-eb1422827e28/scratchpad`): `probe_base.json` + `probe_base2.json` (the measured base wire bodies, model errors, OpenAPI fragments), `base_a.log` / `base_b.log` (section 1.10), `proto/` (the 046 / 049 / rollback prototypes, sqlfluff-clean, applied on a throwaway PostgreSQL 18 cluster: section 1.8), `test_sf1_probe_base*.py` (the scratch probes; never committed).
- Binding inputs: the orchestrator brief `specs/S81_SF1_BRIEF.md` (rulings R-SF1-1..R-SF1-16, cited by id), PLAN_S81 :169 (the unit text), :108, :114-115, the Standing constraints, F4 (migration numbers), owner decisions 1-12; PLAN_S80 section 0 (the contract freeze) and R-A1 / R-A13; `scripts/s81-common.txt` (LC-1..LC-9, the MOVING MAIN lines to 18cb9e04); `specs/RULINGS_S81_11.md` R-S11-23 / R-S11-27 / R-S11-29 and `specs/S81_11_UNIT_SPEC.md` section 2 (the launchSurfaces contract).
- Sister units and contracts: S81-11 (merged #389) is the CONSUMER of `surfaces` (`SmartCompareApp/src/services/launchSurfaces.ts`, unchanged here) and deferred the `category_coming_soon_tap` emission to this unit (S81-11c, R-S11-27); S81-10 (merged) owns `categories_live` (unchanged); S81-05 (merged) binds `compare_request_id` in the request context; S81-22 (the parallel lane, migration 048) is the judge-join reader of `compare_request_id`; CL3 / CL4 (client, after SF1) are the SENDERS of every new field; D22b (migration 053) adds the new columns to the learning buckets. Known rebase hunks with S81-22: the CLAUDE.md anchor after the S81-G7 block, `docs/privacy-data-inventory.md` rows, `tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once` (the reserved tuple line), `tests/test_s81_s05_request_context.py` (the consumer census): section 11 Q10.
- Personal-data rule: no real name, email, phone, device id, account id or address anywhere; user ids are synthetic `sf1-<node>` strings; uuids are built at run time (`uuid.uuid4()` or the fixed synthetic `12345678-1234-4123-8123-123456789abc` the B1 file already uses); the `correction` fixtures are product names only (for example `Dior Sauvage EDT`); no credential-shaped literal; no digest constant named with a gitleaks keyword (E-G4-1).
- Pure ASCII + LF in every new file (this spec included; the U+2192 arrow of the wire 422 message is written `\u2192` everywhere in this file and in Python source).

## 0. What the unit does

The backend half of the honest-feedback and remote-flagged-surfaces design, landing DARK:

1. Migration 046 widens `public.comparison_feedback` with `identity_correct`, `wrong_side`, `preference`, `correction` (at most 80 characters), `source` (`result` | `contact`, NOT NULL DEFAULT `result`) and `compare_request_id uuid` (+ a partial index) and drops NOT NULL on `useful` only inside a guard that reads the live `information_schema.columns.is_nullable` (R-SF1-2). `price_correct` already exists (027): not re-added.
2. Migration 049 re-creates the `referral_invites.share_target` CHECK with the widened set (+ `sms`, `email`, `more`), the live constraint name resolved from `pg_constraint` inside the guard, and adds `compare_request_id uuid` (+ partial index) to `user_events` and `search_logs` (R-SF1-3).
3. Under `ENABLE_FEEDBACK_V2`: `POST /api/v1/feedback` accepts `useful` as optional plus the new answer fields, `source` and `compare_request_id`; `POST /api/v1/events` accepts `compare_request_id` per item and FILTERS the `event_data` of the four new event types to a closed per-type property allowlist; `POST /api/v1/referrals/share` and `ReferralService.create_invite` accept the three new targets; `log_search` writes `search_logs.compare_request_id` from the S81-05 request context. Flag OFF: every request acceptance, 422 body, response, stored row, W4-13 ledger record and log line is byte-identical to 18cb9e04 (R-SF1-4, R-SF1-9, R-SF1-10).
4. Unflagged (R-A1): `VALID_EVENT_TYPES` gains `category_coming_soon_tap`, `share_channel_selected`, `share_target_opened`, `store_cta_tap` APPENDED at the end; `EVENT_PROPERTY_ALLOWLIST` is a closed module dict; the ONE client line `trackEvent('category_coming_soon_tap', { category: key });` in `HomeScreen.handleComingSoon` (S81-11c; R-SF1-7).
5. Under `ENABLE_SURFACES_FIELD`: `GET /api/v1/app/version` carries `surfaces` = `{"skincare": <bool>, "makeup": <bool>}` from `APP_SURFACES_LIVE`, placed after the five keys and BEFORE `categories_live` (R-SF1-6; section 1.5). OFF = the key absent.
6. Docs: one CLAUDE.md block, the :341 pointer clause, the :578 S81-11 sentence and the :105 FeedbackRequest sentence rewritten in place; `docs/privacy-data-inventory.md` rows 4 / 6 / 8 rewritten in place (no new Apple data type: section 11 Q8).

Nothing changes in production on merge: both flags are new names (unset), 046 / 049 are written NOT applied (owner items), the event widening only accepts more, and the client line reaches phones only in the post-approval OTA (UB-R4).

## 1. Base state MEASURED (18cb9e04, read in this run)

### 1.1 Routes and models (`app/api/feedback_routes.py`, 232 lines, CRLF working copy)

| Symbol | file:line | Measured |
|---|---|---|
| `_validate_optional_uuid` | :13-26 | None / blank -> None; else `str(uuid.UUID(s))`; else `ValueError("comparison_id must be a valid UUID")` |
| imports | :28-31 | `get_optional_user`, `limiter`, `save_feedback, track_events_batch` (from `app.services.feedback_service`), `fire_and_forget` |
| `VALID_MATTERED_MOST` | :44-50 | unchanged by this unit |
| `VALID_EVENT_TYPES` | :60-93 | a list of 31 names; `image_load_failed` LAST at :92 (after `scan_cancelled`); the 422 message of `validate_event_type` interpolates the WHOLE list (:156-159) |
| `MAX_BATCH_SIZE` | :95 | 50 |
| `FeedbackRequest` | :102-127 | `useful: bool` REQUIRED (:103); `comparison_id` (:104, uuid validator :113-116); `mattered_most` (:105, validator :118-127); `change_suggestion` max_length 1000 (:106); the 027 fields `winner_correct` / `price_correct` / `specs_correct` `Optional[Literal["correct","wrong","unsure"]]` (:109-111); `model_config` = `{}` (extra = ignore, measured) |
| `EventItem` | :130-160 | `event_type: str` (:131, validator :153-160), `event_data: dict` (:132, 10,000-byte cap :146-151), `comparison_id` (:133, validator :135-144); `model_config` = `{}` |
| `EventBatchRequest` | :163-164 | `events: List[EventItem]`, max_length 50 |
| `submit_feedback` | :171-201 | 30/minute; `fire_and_forget(save_feedback(user_id=, comparison_id=, useful=, mattered_most=, change_suggestion=, access_token=, winner_correct=, price_correct=, specs_correct=), label="save_feedback")` (:186-199); response `{"success": True, "message": "Feedback received"}` (:201) |
| `track_events` | :204-232 | 60/minute; per item `{"user_id", "event_type", "event_data", "comparison_id"}` (:220-225); `fire_and_forget(track_events_batch(events), label="track_events_batch")` (:230); response `"<n> events received"` (:232) |

The brief's line numbers (:60-96, :102-124, :169-200, :203-227) are a few lines off; the symbols above are the measured ones.

### 1.2 Writers (`app/services/feedback_service.py`, 319 lines, CRLF)

- Module imports (:8-11): `cache_service`, `database_service` (`get_supabase_client, save_comparison`), `model_config.critic_model`, `db_offload.run_db`. So `database_service` CANNOT import `feedback_service` at module top (a cycle): section 2.1 places a local reader in `database_service` (the S81-09 `_referral_rewards_paused` precedent, referral_service.py:54).
- `save_feedback` :197-251: the record :226-243 = `{"useful": useful, "mattered_most": mattered_most}` + `user_id` / `comparison_id` / `change_suggestion` when truthy + the 027 keys when not None; insert through `run_db(... table("comparison_feedback").insert(record) ...)` (:247); the user client when `user_id and access_token` (:221-223), else the service-role client. Only caller: feedback_routes.py:187.
- `track_event` :254-286 (single insert into `user_events`, :282): not called by this unit's paths (callers: `save_comparison_and_track_cohort`); untouched.
- `track_events_batch` :289-319: per item `{"event_type", "event_data"}` + `user_id` / `comparison_id` / `session_id` when truthy (:302-311); one batch insert (:315). Only caller: feedback_routes.py:230.

### 1.3 Referral (`app/api/referral_routes.py`, `app/services/referral_service.py`)

- `ShareTarget = Literal["whatsapp", "copy", "x", "telegram", "snapchat", "other"]` referral_routes.py:80; `ShareRequest` :92-138 (`model_config = {"extra": "ignore"}` :108, `comparison_id` :110, `share_target: ShareTarget` :111); the router-level `_require_referral_enabled` dependency (:57-78: 503 before auth and body); `share_comparison` :176-231 calls `service.create_invite(..., share_target=body.share_target, ...)` (:205-213); a service `ValueError` -> 400 `VALIDATION_ERROR` with `str(exc)` (:225-229).
- referral_service.py:32 `_VALID_SHARE_TARGETS = {"whatsapp", "copy", "x", "telegram", "snapchat", "other"}`; `create_invite` :257-; the defence-in-depth check :306-310 raises `ValueError(f"share_target {share_target!r} not in allowed set {sorted(_VALID_SHARE_TARGETS)}")`; the code-redeem path writes `"share_target": "other"` (:126-128, unchanged). referral_service imports `database_service` (:21-24); no cycle with `feedback_service`.
- migrations/014_referral_system.sql:22 `share_target TEXT NOT NULL CHECK (share_target IN ('whatsapp','copy','x','telegram','snapchat','other'))` (unnamed inline: PostgreSQL names it `referral_invites_share_target_check`; no other migration touches it: grep `share_target` over migrations/ = 014 only).

### 1.4 `log_search` (`app/services/database_service.py`)

- Module app-imports: only `app.utils.db_offload.run_db` (:24).
- `search_log_synthetic_marker_enabled` :725; `log_search(query, input_type="text", user_id=None, products_found=None, success=True, error_message=None, cost=0.0, duration_ms=0, is_synthetic=None)` :753-802; the record :781-794 (`user_id` / `error_message` when truthy; `is_synthetic` when not None AND the W4-13 flag); insert :799 through `run_db`.
- Callers: 25 sites in text_routes / image_routes / url_routes, mostly `fire_and_forget(log_search(...))`; a task created inside the request keeps the ContextVar snapshot (request_context.py:49-53, "read the accessors on the request path BEFORE any offload"); the read happens inside `log_search` BEFORE `run_db`.
- `app/utils/request_context.py`: `compare_request_id()` :169-171 returns the bound canonical uuid4 string or None; bound only under `ENABLE_REQUEST_CONTEXT_HEADERS` by the S81-05 middleware. The consumer census `tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app` (:1352) admits only `_ALLOWED_CTX_FILES` and, per consumer, the exact form `from app.utils import request_context as _request_context` with a pinned attribute set (`_CTX_CONSUMER_ATTRS` :1345-1349): a deliberate pin change E3 (section 4.1).
- The W4-13 chain: `tests/test_w4_13_flag_off_ledger.py` re-drives 45 scenarios incl. an `inserts` scenario through the REAL `log_search` and compares kwargs, labels and insert records to `tests/fixtures/w4_13_flag_off_ledger.json`; the ST1 twin `tests/test_s81_st1_usage_path_offloop.py` :2262 calls the same ledger. `log_search` gains NO parameter (R-SF1-9), so the kwargs records cannot move; the insert records move only when an id is bound AND the flag is ON (never in the ledger's scenarios). `tests/test_s81_kb_schema.py` IDENTITY_NODES pins the digest of the ledger test and fixture: neither file is edited.

### 1.5 `/app/version` (`app/api/version_routes.py`, 30 lines, CRLF)

- :2 `import os`; :7 `from app.services import category_gate as _category_gate`; `get_version_info` :12-24: the five keys :14-20, then `categories_live` under `_category_gate.fragrance_only_gate_enabled()` with the comment "the LAST key, ON only" (:21-23); `check_version` :27-30.
- Measured base body (flags unset): keys `["min_version", "latest_version", "force_update", "update_url_ios", "update_url_android"]`, values `"1.0.0", "1.0.0", false, "", ""`.
- Order pin: `tests/test_s81_s10_fragrance_gate.py::test_r51_version_categories_live` (:2058-2063) asserts `list(body) == [five keys, "categories_live"]` with the S81-10 flag ON (SF1 unset). So R-SF1-6's condition holds: `categories_live` is pinned LAST; `surfaces` goes BETWEEN the five keys and `categories_live`. The same file's static row (:2183-2187) asserts `app/api/version_routes.py` never contains the text `request_context` (a guard the new code must not trip).
- `tests/test_version_routes.py` asserts presence and defaults only; no "exactly five keys" pin.
- The consumer (S81_11_UNIT_SPEC :121-133, `launchSurfaces.ts`): `surfaces` accepted only as a plain object; per chip key `skincare` / `makeup` the chip is on ONLY when the value is the boolean `true`; unknown keys ignored; non-object / absent = every chip off; the client contract does not depend on key order. Rows B9 / B4 of the s11 suite pin the client side.

### 1.6 Readers of the touched tables (Q7)

- `comparison_feedback`: the insert (feedback_service.py:247); `structured_comparison_service._update_behavior_profile` :5989 `select("useful")` -> `behavior_service._compute_winner_agreement` :99-102 counts `is True` / `is False` (a NULL `useful` counts in neither: safe); `scripts/cron_learning.py` :69 `FEEDBACK_COLUMNS = "id,user_id,comparison_id,useful,winner_correct,price_correct,specs_correct,created_at"` (explicit: reads none of the new columns; `correction` is NOT in it); the view `vw_cohort_feedback_lift` (013 :46-57, read by admin_routes.py:746 `/admin/cohort/feedback`): `COUNT(*)` denominator with `FILTER (WHERE cf.useful = true)` numerator, so a NULL-`useful` row (a Q1-only CL3 answer) lowers `useful_pct` (stated limit L11; section 11 Q7); 043 `delete_user_cascade` :174 deletes by user_id and :180 detaches cross-user rows by comparison_id (the new columns need no cascade change). No `select("*")` of comparison_feedback / user_events / search_logs in app/ or scripts/ (grep).
- `user_events` / `search_logs` readers: analytics_service.py (:31/:79/:102/:143, explicit columns), admin_routes.py:785, scs :5990, cron_learning EVENT_COLUMNS / SEARCH_COLUMNS (:82-83): none reads `compare_request_id`.
- No string literal `"correction"` / `'correction'` exists in app/ or scripts/ at base (grep): the pin P60 holds the post-GREEN set to the two writer files.

### 1.7 Client (read-only except the one line; `SmartCompareApp/` LF working copy)

- `src/screens/HomeScreen.tsx`: `trackEvent` ALREADY imported in the `../services/api` named import (:69-71; no import change); `comingSoonKey` state :141, the timer ref :142, the unmount cleanup :143-148, `handleComingSoon` :149-160 = clear the timer (:150), set the key (:151), build the message (:152-154), the iOS announce (:155), the 2,500 ms timer (:156-159).
- `__tests__/s11/categoryRow.s11.test.tsx`: describe "S81-11 B2 / B3 / B4 -- coming-soon chips only under surfaces" (:287); `it('B3: a coming-soon tap -> the toast (+ iOS announcement), no event, no navigate, no compare'` (:315) asserts `mockTrackEvent.mock.calls.filter((c) => c[0] === 'category_coming_soon_tap')` `toHaveLength(0)` (:346-348); `it('B4: ...'` (:364) asserts `toHaveLength(0)` after a fragrance tap (:376-378).
- `__tests__/s11/launchSurfaces.s11.test.ts` :176-183 (`R-S11-27: no event-name constant is exported`): `launchSurfaces.ts` must not export the literal: unchanged by this unit.
- CLAUDE.md :578 (the S81-11 client block): "... NO event: `category_coming_soon_tap` ships with SF1's VALID_EVENT_TYPES widening (R-S11-27, S81-11c)."; CLAUDE.md :105: "`FeedbackRequest`: `useful, comparison_id, mattered_most, change_suggestion` + the three optional 027 fields ...".

### 1.8 Migrations (Q4)

- Present: 001-045, 047, 050, 052 (+ `add_share_token.sql`, `rollback/`); 046 and 049 FREE (048 = S81-22, 051 = S81-17b, 053 = D22b). The CREATE TABLE of `comparison_feedback` and `user_events` is NOT in the repo (the live tables predate the migration corpus); `search_logs` is 002; `referral_invites` is 014.
- Reserved-number pin: `tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once` (:521-529) asserts `not list(MIG.glob(n + "_*.sql"))` for `("046", "048", "049", "051")`: a deliberate pin change E2 (section 4.1). `tests/test_s81_s03_llm_ledger_v2.py::test_h1_...` (:2269) says "nothing about 045-049": no assertion on them.
- Readers that glob every migration: `test_migration_index_predicate_immutability.py` (:81, :195), `_retro_r_mig_sql.py` (:189; used by test_retro_w1_2b/2c/2d, test_migration_041..044, test_account_deletion_u8b*, test_s79_b3b, test_s81_kb_schema, test_s81_s03, test_s81_s16b), `test_migration_037_security_definer_grants.py` (:295-299, :365, :458: the REVOKE census of SECURITY DEFINER functions; 046 / 049 define NO function, so no REVOKE is owed), `test_s81_kb_schema.py` (:469 the sqlfluff skip-limit row; :1180 the policy census: 046 / 049 create no policy), `test_sqlfluff_config.py`.
- House form copied from 027 (DROP CONSTRAINT IF EXISTS + ADD CONSTRAINT; ADD COLUMN IF NOT EXISTS), 043 (the guard / assert DO blocks), 052 (header + BEGIN / COMMIT + the rollback file form). The APPLY files live in the docs state folder (`specs/APPLY_052_{1_PRECHECK,2_ONE_PASTE,3_POSTCHECK}.sql` precedent), not in the repo.
- PROTOTYPE MEASURED (G9 form, this spec): `proto/046_comparison_feedback_v2.sql`, `proto/049_share_target_and_request_ids.sql`, `proto/rollback_046.sql`, `proto/rollback_049.sql` lint clean (`python -m sqlfluff lint --config .sqlfluff`, sqlfluff 4.3.0: "All Finished!", 0 violations). On a throwaway PostgreSQL 18 cluster (`initdb` under `proto/pgdata`, port 54391, a mimic of the four live tables, `useful boolean NOT NULL`, the 014 inline share_target CHECK, 027 applied from the repo file): 046 applied (rc 0), re-applied (rc 0, NOTICE skips only); 049 applied and re-applied (rc 0); final state: the six new columns, `source text NOT NULL DEFAULT 'result'` (both pre-existing rows read `result`), `useful` `is_nullable = YES`, the share_target CHECK `CHECK ((share_target = ANY (ARRAY['whatsapp'::text, ..., 'other'::text, 'sms'::text, 'email'::text, 'more'::text])))` under the name `referral_invites_share_target_check`; negative inserts each refused by its CHECK (identity_correct `maybe`, wrong_side `third`, preference `both`, an 81-char correction, source `admin`, share_target `facebook`); a positive row (useful NULL, every new column set, an 80-char correction, source `contact`) and an `sms` invite inserted; rollback 049 REFUSED while the `sms` row exists (RAISE, rc 3), rollback 046 REFUSED while a NULL-`useful` row exists (RAISE, rc 3); after deleting those rows both rollbacks ran (rc 0): 10 columns, `useful` NOT NULL again, the six-value CHECK back; 046 + 049 re-applied after the rollback (rc 0). A second database: 046 without 027 -> `046 guard: the three 027 CHECK constraints are missing (apply 027 first)` (rc 3); 049 with a second CHECK mentioning share_target -> `049 guard: expected exactly one share_target CHECK, found 2` (rc 3); 046 with `useful` already nullable -> rc 0, the DROP NOT NULL skipped. Cluster stopped (`pg_ctl stop -m fast`, rc 0); the data directory is left in the notes folder (no recursive delete).
- `pg_constraint` filter: `contype = 'c'` excludes the PostgreSQL 18 NOT NULL rows (`contype = 'n'`); the live (Supabase 15 per the 027 note) name is resolved, never assumed.

### 1.9 The measured 422 bytes (Q1) and the reproduction mechanism

Wire shape (`app/middleware/error_handler.py::validation_exception_handler` :253-269): `{"success": false, "error": "Validation error: <loc parts joined by ' \u2192 '>: <msg of the FIRST error>", "code": "VALIDATION_ERROR", "request_id": <random>}`; only the first error's `loc` and `msg` reach the wire. Measured at base (`probe_base.json`, `probe_base2.json`; request_id dropped):

| Body | status | `error` |
|---|---|---|
| feedback `{}` | 422 | `Validation error: body \u2192 useful: Field required` |
| feedback `{"comparison_id": "bad"}` | 422 | same (first error = useful `missing`; second = comparison_id value_error) |
| feedback `{"identity_correct": "correct", "source": "contact"}` | 422 | same |
| feedback `{"useful": null}` | 422 | `Validation error: body \u2192 useful: Input should be a valid boolean` |
| feedback `{"useful": "maybe"}` | 422 | `Validation error: body \u2192 useful: Input should be a valid boolean, unable to interpret input` |
| feedback `[1]` / `"x"` | 422 | `Validation error: body: Input should be a valid dictionary or object to extract fields from` |
| feedback JSON `null` | 422 | `Validation error: body: Field required` |
| feedback `{` (bad JSON) | 422 | `Validation error: body \u2192 1: JSON decode error` |
| feedback `{"useful": true, "mattered_most": ["bogus"], "comparison_id": "bad"}` | 422 | `Validation error: body \u2192 comparison_id: Value error, comparison_id must be a valid UUID` |
| feedback `{"useful": true, "change_suggestion": <1001 x>}` | 422 | `Validation error: body \u2192 change_suggestion: String should have at most 1000 characters` |
| feedback `{"useful": true, "correction": <500 x>, "compare_request_id": "zzz", "source": "bogus", "identity_correct": "bogus", "wrong_side": 7, "preference": "x"}` | 200 | `{"success": true, "message": "Feedback received"}` (extras ignored) |
| events `[{"event_type": "save", "compare_request_id": "bad", "event_data": {"a": 1}}]` | 200 | `{"success": true, "message": "1 events received"}` |
| events `[{"event_type": "save", "event_data": {"k": <10001 v>}}]` | 422 | `Validation error: body \u2192 events \u2192 0 \u2192 event_data: Value error, event_data too large (max 10KB)` |
| share `share_target` in {`sms`, `email`, `more`, `foo`, `5`, `null`, `WhatsApp`} (auth overridden) | 422 | `Validation error: body \u2192 share_target: Input should be 'whatsapp', 'copy', 'x', 'telegram', 'snapchat' or 'other'` |

Model-level errors (pydantic 2.13.4, `e.json(include_url=False)`): feedback `{}` -> `[{"type": "missing", "loc": ["useful"], "msg": "Field required", "input": {}}]`; share `sms` -> `[{"type": "literal_error", "loc": ["share_target"], "msg": "Input should be 'whatsapp', 'copy', 'x', 'telegram', 'snapchat' or 'other'", "input": "sms", "ctx": {"expected": "'whatsapp', 'copy', 'x', 'telegram', 'snapchat' or 'other'"}}]` (the full list per input is in `probe_base.json`).

Mechanism chosen BY MEASUREMENT (pure pydantic replica in the notes run, the same version):
- (a) FeedbackRequest: ONE model whose new fields are optional, with `@model_validator(mode="before")` whose FIRST statement is `if not feedback_v2_enabled():`; under OFF and `isinstance(data, dict)` it validates `data` with a frozen copy of the 18cb9e04 class (`_FeedbackRequestBase`, the exact base fields and validators) and returns `_FeedbackRequestBase.model_validate(data).model_dump()`: a base `ValidationError` raised inside the before-validator propagates UNCHANGED (measured: identical `type` / `loc` / `msg` / `input` / `ctx` and order for `{}`, `{"comparison_id": "bad"}`, `{"useful": null}`); the dump carries only base keys, so every new field takes its default (accepted and DROPPED, never a 422 the base does not raise). A non-dict input is returned untouched so the SAME class name `FeedbackRequest` produces the base non-dict error (the frozen class is never named in an error). ON returns `data` unchanged.
- (c) ShareRequest: `share_target` annotated with the nine-value Literal and a `@field_validator("share_target", mode="before")` whose first statement reads the flag; under OFF a value that is not `isinstance(v, str) and v in BASE_SHARE_TARGETS` raises `PydanticCustomError("literal_error", "Input should be {expected}", {"expected": "'whatsapp', 'copy', 'x', 'telegram', 'snapchat' or 'other'"})`: measured IDENTICAL to the base error list for 36 inputs (12 values incl. `5`, `None`, `True`, `{"a": 1}`, `["x"]`, `WhatsApp` x 3 comparison_id values) and for a body missing share_target; ON: the nine-value literal error (`'whatsapp', ..., 'other', 'sms', 'email' or 'more'`).
- EventItem `compare_request_id`: `@field_validator("compare_request_id", mode="before")`, first statement the flag read; OFF returns None (dropped, never validated); ON validates like comparison_id with the message `compare_request_id must be a valid UUID`.

### 1.10 Base pass state (through pyt.py; `.venv-qaren`, pydantic 2.13.4, fastapi 0.141.1, starlette 1.6.0)

- Set A (17 files: test_s80_b1_feedback, test_feedback, test_feedback_service, test_feedback_allowlist_superset, test_events_allowlist_superset, test_m13_29_feedback_uuid, test_version_routes, test_referral_routes, test_referral_service, test_referral_share_privacy, test_referral_share_status_lifetime, test_referral_must_fixes, test_db_improvements, test_share_routes, test_referral_e2e, test_domain_s76, test_auth_routes_invite_fingerprint): 248 passed, 1 skipped.
  `[hermeticity] sentinel checked 248 test(s)` / `[netguard] blocked 11 attempt(s) from 6 node(s)` (the conftest sentinel host `neutralized.supabase.invalid`, as at every base) /
  `[pyt] tag=sf1-spec-base-a start=2026-11-06 15:16:59 end=2026-11-06 15:17:14 elapsed=15s bound=1200s status=OK rc=0`
- Set B (12 files: test_w4_13_flag_off_ledger, test_s81_kb_schema, test_migration_index_predicate_immutability, test_sqlfluff_config, test_retro_w1_2d, test_migration_027_comparison_feedback_correctness, test_migration_043_delete_user_cascade, test_s71_u13_compare_auth_required, test_s81_s10_fragrance_gate, test_m13_21_openapi_gated, test_migration_037_security_definer_grants, test_s81_d22_nightly_learning): 1 failed, 1023 passed, 4 deselected. The one failure is ENVIRONMENTAL base noise, `tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content` (`assert b"\r" not in raw`: the worktree's autocrlf working copy of `data/fragrance_lexicon.json` is CRLF; CI checks out LF): record it identically at base and head.
  `[hermeticity] sentinel checked 1024 test(s)` / `[netguard] blocked 0 attempt(s) from 0 node(s)` /
  `[pyt] tag=sf1-spec-base-b start=2026-11-06 15:17:25 end=2026-11-06 15:18:19 elapsed=54s bound=1200s status=FAIL rc=1`
- Probes: `[pyt] tag=sf1-spec-probe ... elapsed=10s bound=600s status=OK rc=0`, `[pyt] tag=sf1-spec-probe2 ... elapsed=5s bound=600s status=OK rc=0` (scratch files, `-p tests.conftest --rootdir=<worktree>`).

### 1.11 OpenAPI readers (Q2): the T23 re-record is NOT needed

`tests/test_s71_u13_compare_auth_required.py::test_T23_openapi_unchanged` (:987-1003) compares the ten U13 operations and ONLY the components in the transitive `$ref` closure of those ten operations (`_referenced_components` :955-, rule UG1). Measured closure of the committed fixture: `Body_identify_and_compare_api_v1_image_identify_post`, `HTTPValidationError`, `QuickCompareRequest`, `TextCompareRequest`, `URLCompareRequest`, `URLExtractRequest`, `ValidationError`. `FeedbackRequest`, `EventItem`, `EventBatchRequest` and `ShareRequest` are stored in the fixture's `components` (the share_target enum at fixture :1431) but are OUTSIDE the compared closure, so T23 stays green with every model change of this unit and the fixture is NOT re-recorded (a measured contradiction of PLAN :169 / R-SF1-4's "re-recorded deliberately": section 11 Q1; no E-row is written for it). The other OpenAPI readers read path sets, parameter names or other operations only: test_s81_d16_operator_ingest p2 (sorted path set: SF1 adds no path), test_s81_s05 p02 (header parameters), test_s81_s08b p10 (fingerprint parameter), test_u13e E13 (/url/detect), test_u3b b5 (PreferenceTogglesBody), test_w4_13 :1852 (five compare paths), `_route_introspection.py` (paths). No pin reads the three models' schemas. The OpenAPI document is served only outside the Railway env (test_m13_21_openapi_gated).

## 2. Contract

### 2.1 Flags, knob and readers (R-SF1-1)

| Reader | Where | Body |
|---|---|---|
| `feedback_v2_enabled() -> bool` | app/services/feedback_service.py (module level, public) | `return os.getenv("ENABLE_FEEDBACK_V2", "false").strip().lower() in ("true", "1", "yes", "on")` (feedback_service gains `import os`) |
| `_feedback_v2_enabled() -> bool` | app/services/database_service.py (private one-liner, the SAME name string; no import of feedback_service: the cycle of 1.2) | the same body |
| `surfaces_field_enabled() -> bool` | app/api/version_routes.py | `return os.getenv("ENABLE_SURFACES_FIELD", "false").strip().lower() in ("true", "1", "yes", "on")` |
| `surfaces_live() -> dict` | app/api/version_routes.py | `tokens = {t.strip().lower() for t in os.getenv("APP_SURFACES_LIVE", "").split(",")}`; `return {k: (k in tokens) for k in SURFACE_KEYS}` with `SURFACE_KEYS = ("skincare", "makeup")` (key order fixed; values are Python `bool`, JSON `true` / `false`; unknown tokens ignored; unset / blank / garbage = both False) |

Imports: `feedback_routes` imports `feedback_v2_enabled` from `app.services.feedback_service` (the existing import line :30 widened); `referral_routes` and `referral_service` import it from `app.services.feedback_service` (no cycle: feedback_service imports no referral module). Every gated predicate calls its reader as its FIRST statement, so OFF reads no further state (no knob, no request context, no allowlist).

### 2.2 New keys and types (all additive)

Request `FeedbackRequest` (ON only; OFF = accepted and dropped):
- `useful: Optional[bool] = None` (OFF: REQUIRED through the frozen base, the base 422 bytes)
- `identity_correct: Optional[Literal["correct", "wrong", "unsure"]] = None`
- `wrong_side: Optional[Literal["first", "second", "both"]] = None` (which product was wrong, in the body's product order)
- `preference: Optional[Literal["first", "second", "neither", "unsure"]] = None`
- `correction: Optional[str] = None`: a `field_validator` (after) strips; empty after strip -> None; longer than 80 after strip -> `PydanticCustomError("string_too_long", "String should have at most {max_length} characters", {"max_length": 80})` (the wire: `Validation error: body \u2192 correction: String should have at most 80 characters`)
- `source: Literal["result", "contact"] = "result"`
- `compare_request_id: Optional[str] = None`: ON validated like comparison_id (canonical `str(uuid.UUID(s))`; blank -> None; else `ValueError("compare_request_id must be a valid UUID")`)
- Constants (module level, feedback_routes.py): `IDENTITY_VALUES = ("correct", "wrong", "unsure")`, `WRONG_SIDE_VALUES = ("first", "second", "both")`, `PREFERENCE_VALUES = ("first", "second", "neither", "unsure")`, `FEEDBACK_SOURCES = ("result", "contact")`, `CORRECTION_MAX_CHARS = 80` (parity rows R54 tie them to the 046 text).

Request `EventItem`: `compare_request_id: Optional[str] = None` (OFF dropped; ON uuid-validated). Module constants: `VALID_EVENT_TYPES` += the four names (appended, unflagged); `EVENT_PROPERTY_ALLOWLIST = {"category_coming_soon_tap": frozenset({"category"}), "share_channel_selected": frozenset({"channel"}), "share_target_opened": frozenset({"share_target"}), "store_cta_tap": frozenset({"merchant_id"})}` (closed; unflagged constant, applied only under ON).

Request `ShareRequest.share_target`: `ShareTargetV2 = Literal["whatsapp", "copy", "x", "telegram", "snapchat", "other", "sms", "email", "more"]` + the OFF before-validator of 1.9 (c); `ShareTarget` (the six-value alias, :80) is KEPT unchanged (an importable name); `BASE_SHARE_TARGETS = ("whatsapp", "copy", "x", "telegram", "snapchat", "other")`, `WIDENED_SHARE_TARGETS = BASE_SHARE_TARGETS + ("sms", "email", "more")`.

Service `ReferralService.create_invite`: the check :306-310 reads `_share_targets()` = `_VALID_SHARE_TARGETS | {"sms", "email", "more"}` when `feedback_v2_enabled()` else `_VALID_SHARE_TARGETS` (unchanged object); the message keeps the f-string form, so OFF bytes equal base.

Writes under ON (R-SF1-10):
- `submit_feedback`: OFF calls `save_feedback` with EXACTLY the nine base kwargs (same order, same values); ON adds `identity_correct=`, `wrong_side=`, `preference=`, `correction=`, `source=`, `compare_request_id=` (and `useful` may be None).
- `save_feedback` gains six keyword parameters (default None); `useful: Optional[bool]`; the record writes `useful` only when not None (OFF callers always pass a bool: byte-identical), each new key only when not None (the 027 pattern); `source` arrives only under ON (route) and is then always written.
- `track_events`: OFF builds today's four-key dict and never reads the allowlist; ON filters the four new types' `event_data` to their allowlist (a new dict, the sent dict untouched), logs `[EVENTS] properties dropped type=%s n=%d` at INFO once per filtered item (the type is an allowlisted constant; `n` an int), and adds `"compare_request_id"` to the dict only when not None. Existing types are unfiltered in BOTH states (L1). The 10,000-byte cap (a field validator) runs before the filter.
- `track_events_batch`: writes `record["compare_request_id"]` when `evt.get("compare_request_id")` (the key arrives only under ON).
- `log_search`: after the `is_synthetic` line: `if _feedback_v2_enabled():` then `crid = _request_context.compare_request_id()` and `record["compare_request_id"] = crid` when not None; NO new parameter (signature literal pinned by P42); `database_service` gains `from app.utils import request_context as _request_context` (the census form of 1.4).

Response `/app/version` (ON only): `surfaces: {"skincare": bool, "makeup": bool}` inserted after `update_url_android` and BEFORE the `categories_live` block; with both flags ON the key order is the five keys, `surfaces`, `categories_live`. The comment at :21 stays true ("the LAST key").

No other response changes: `/feedback` and `/events` and `/referrals/share` responses keep their literals in both states. Contract freeze (PLAN_S80 section 0, `runs/research/contract_freeze.json`): every new key is additive; no build-3 key is removed, renamed or retyped; no refusal or 503 is added (the only new 422s exist under ON only, on endpoints whose 422 build 3 already swallows: fire-and-forget).

### 2.3 Flag-OFF identity (the main invariant)

With `ENABLE_FEEDBACK_V2` unset / `""` / `false` / `0` / `off` / `no` AND the FULL companion configuration present (`ENABLE_SURFACES_FIELD=true`, `APP_SURFACES_LIVE=skincare,makeup`, `ENABLE_REQUEST_CONTEXT_HEADERS=true` with a bound `compare_request_id`, `ENABLE_FRAGRANCE_ONLY_GATE` in both states): every 422 body field of 1.9 equals the recorded literal; every 200 response equals its literal; the `save_feedback` kwargs, the `track_events_batch` dicts, the feedback / events / search_logs / invite insert payloads equal the base literals; no `[EVENTS]` line; the W4-13 ledger equals its fixture record by record. With `ENABLE_SURFACES_FIELD` OFF (same spellings) and `APP_SURFACES_LIVE=skincare,makeup` set: `/app/version` equals the base body (S81-10 OFF: five keys; S81-10 ON: the r51 six keys) and `APP_SURFACES_LIVE` is never read (recorder).

The ONE unflagged wire change: the event_type 422 message embeds the list (1.1), so an unknown type's 422 message grows by the four names in every state (R-A1 class; no pin reads it; build 3 swallows it: L2).

### 2.4 Failure table

| Case | Behaviour |
|---|---|
| ON, 046 not applied | every feedback insert fails 42703 (`source` always written) inside `save_feedback`'s except arm: a WARNING, response unchanged (fire-and-forget); prevented by the owner order (R-SF1-15), never a code guard |
| ON, 049 not applied, id bound | the `search_logs` insert fails 42703 for that row (the whole row lost); an event with an id fails its whole batch insert; owner order |
| ON, `useful` still NOT NULL live | a Q1-only feedback (useful None) fails 23502 in the except arm; the 046 guard drops it on apply |
| ON, malformed `compare_request_id` on one event | the WHOLE batch 422s (the comparison_id precedent, M13-29): L5 |
| ON, unknown key on a new type | dropped, one INFO line, never a 422 |
| ON, unknown chip token in the knob | ignored (never on the wire) |
| knob unset / blank / garbage, flag ON | `{"skincare": false, "makeup": false}` (the key present, both off) |
| flag value with spaces / case | parsed by `.strip().lower()` (pinned with ` TRUE `, `On`) |
| Redis / network | not touched by this unit |

### 2.5 Test seams (production values in brackets)

`feedback_routes.save_feedback` / `fire_and_forget` / `track_events_batch` (module attributes, monkeypatched by the B1 file already); `feedback_service.get_supabase_client` [the service-role client]; `database_service.get_supabase_client` + `run_db` [inline when ENABLE_SYNC_DB_OFFLOAD OFF]; `request_context._COMPARE_REQUEST_ID` set through `request_context.bind_from_headers` with `ENABLE_REQUEST_CONTEXT_HEADERS=true` and an `x-compare-request-id` header [bound by the S81-05 middleware]; `referral_routes.ReferralService` [the real service]; `app.dependency_overrides[get_current_user]` [Supabase verify]; `version_routes.os` recorder (a wrapper exposing `getenv` that records names) [the `os` module].

## 3. Change list (GREEN order; every edit starts from a byte copy, sha recorded; CRLF app/ files edited with the Edit tool, `git diff --stat` content lines only)

C1. NEW `migrations/046_comparison_feedback_v2.sql`: the prototype body of 1.8 (proto sha in the notes folder) under a full header: unit, columns and sets, "WRITTEN NOT APPLIED; MERGING CHANGES NOTHING IN PRODUCTION", apply order (after 027; before 049; the flag after both), the guard (table, `useful` boolean, the three 027 CHECK names), the live `is_nullable` check and that the PRECHECK reports it, `price_correct` not re-added (027), `correction` never read by a prompt / exemplar builder / store report, `source` (result | contact) and that learning readers exclude contact, no function / no RLS / no GRANT change (the existing 010 policies cover new columns: no column-level grant exists in the corpus for this table), the rollback path. ASCII, LF, one BEGIN / COMMIT, sqlfluff clean.
C2. NEW `migrations/rollback/046_comparison_feedback_v2.sql`: the prototype rollback (drop exactly the six columns; `SET NOT NULL` on `useful` inside a DO that RAISEs while a NULL row exists) + a header stating that the PRECHECK's recorded `useful_is_nullable` is the pre-046 state and that the SET NOT NULL is right only when it read `NO` (L9).
C3. NEW `migrations/049_share_target_and_request_ids.sql`: the prototype body (the pg_constraint resolution, exactly one match or RAISE, `EXECUTE format('... DROP CONSTRAINT %I', live_name)`, ADD `referral_invites_share_target_check` with the nine values, the two uuid columns + partial indexes `idx_user_events_request` / `idx_search_logs_request`, the assert block) + the header (independent of 046; applied after it; indexes are partial on an all-NULL column at apply time, so the build is instant; no RLS / function / GRANT).
C4. NEW `migrations/rollback/049_share_target_and_request_ids.sql`: refuse while an `sms` / `email` / `more` invite exists; restore the six-value CHECK under the same name; drop the two columns.
C5. EDIT `app/api/feedback_routes.py`: import `feedback_v2_enabled` (+ `model_validator`, `PydanticCustomError` from `pydantic_core`); the constants of 2.2; append the four names to `VALID_EVENT_TYPES` after `"image_load_failed"` (a comment line naming S81-SF1 / R-A1); `EVENT_PROPERTY_ALLOWLIST`; `_FeedbackRequestBase` (the verbatim 18cb9e04 FeedbackRequest body and validators, a docstring saying it is the frozen OFF contract); `FeedbackRequest` = the base fields with `useful: Optional[bool] = None` + the new fields + the before model-validator of 1.9 (a) + the correction / compare_request_id validators; `EventItem.compare_request_id` + its before-validator; `submit_feedback` and `track_events` per 2.2 (each handler's first statement is `v2 = feedback_v2_enabled()`, read once per request; then `user_id`).
C6. EDIT `app/services/feedback_service.py`: `import os`; `feedback_v2_enabled()`; `save_feedback` six new kwargs + the `useful` not-None write; `track_events_batch` the `compare_request_id` key when present.
C7. EDIT `app/api/version_routes.py`: `SURFACE_KEYS`, `surfaces_field_enabled()`, `surfaces_live()`; in `get_version_info` before the S81-10 block: `if surfaces_field_enabled(): info["surfaces"] = surfaces_live()` (comment: S81-SF1, ON only, before categories_live which stays LAST). No `request_context` text in the file (the S10 static row).
C8. EDIT `app/api/referral_routes.py`: import `feedback_v2_enabled`, `PydanticCustomError`; `BASE_SHARE_TARGETS`, `WIDENED_SHARE_TARGETS`, `ShareTargetV2`, `_BASE_SHARE_EXPECTED` (the measured ctx string); `ShareRequest.share_target: ShareTargetV2` + the before-validator. `ShareTarget` (:80) unchanged.
C9. EDIT `app/services/referral_service.py`: import `feedback_v2_enabled`; `_WIDENED_SHARE_TARGETS = frozenset(_VALID_SHARE_TARGETS | {"sms", "email", "more"})`; `_share_targets()`; the check :307 reads `_share_targets()` (the message from the same set).
C10. EDIT `app/services/database_service.py`: `from app.utils import request_context as _request_context`; `_feedback_v2_enabled()`; the three lines in `log_search` after :794.
C11. EDIT `SmartCompareApp/src/screens/HomeScreen.tsx`: ONE line after the iOS announce (:155) and before the timer (:156): `    trackEvent('category_coming_soon_tap', { category: key });` (the literal event name; `trackEvent` already imported at :69).
C12. EDIT `SmartCompareApp/__tests__/s11/categoryRow.s11.test.tsx` (E4): the B3 title `... no event, no navigate, no compare` -> `... one category_coming_soon_tap event, no navigate, no compare`; the assertion :346-348 -> `const soon = mockTrackEvent.mock.calls.filter((c) => c[0] === 'category_coming_soon_tap'); expect(soon).toHaveLength(1); expect(soon[0]).toEqual(['category_coming_soon_tap', { category: 'skincare' }]);`. B4 (:364-379) UNCHANGED.
C13. EDIT `tests/test_s81_kb_schema.py` (E2): `for n in ("046", "048", "049", "051"):` -> `for n in ("048", "051"):` (one line; S81-22 edits the same line: known rebase).
C14. EDIT `tests/test_s81_s05_request_context.py` (E3): `_ALLOWED_CTX_FILES` gains `"app/services/database_service.py"`; `_CTX_CONSUMER_ATTRS` gains `"app/services/database_service.py": {"compare_request_id"}` (a named `_LOG_SEARCH_CTX_ATTRS` constant with a comment `# S81-SF1 (R-SF1-9): log_search reads only compare_request_id.`).
C15. NEW `tests/test_s81_sf1_surfaces_be.py`: the RED file of section 5 (written by RED, frozen at the gate).
C16. EDIT `CLAUDE.md`: the block of section 8 after the S81-G7 block (inserted after the G7 owner-steps bullet, :594, one blank line before its heading); the :341 pointer clause gains the SF1 sentence after the S81-G7 sentence; :578's last sentence rewritten in place (8.3); :105's FeedbackRequest sentence rewritten in place (8.3).
C17. EDIT `docs/privacy-data-inventory.md`: rows 4, 6 and 8 rewritten IN PLACE (8.4); row 5 and the manifest array untouched (the client fences read row 5 and the array).
C18. Notes-folder deliverables the orchestrator files in the docs state folder (never in the repo): `APPLY_046_{1_PRECHECK,2_ONE_PASTE,3_POSTCHECK}.sql`, `APPLY_049_{1_PRECHECK,2_ONE_PASTE,3_POSTCHECK}.sql` (8.5); the ONE_PASTE files regenerated from the FINAL migration bytes (a two-line header + the migration text).

No other file. (`structured_comparison_service.py`, `launchSurfaces.ts`, the i18n catalogs, `tests/fixtures/s71_u13_flag_off_baseline.json` and the W4-13 fixture are NOT edited; no dependency, no lock, no `.githooks` change.)

## 4. Existing pins

### 4.1 Pins that change deliberately

| E | Node | Reason |
|---|---|---|
| E1 | none for T23: `tests/test_s71_u13_compare_auth_required.py::test_T23_openapi_unchanged[*]` stays GREEN unedited (1.11); the plan's re-record is not performed (Q1) | measured |
| E2 | `tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once` | 046 and 049 now exist (the reserved tuple loses them; 048 / 051 stay reserved) |
| E3 | `tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app` | `database_service.log_search` becomes the fourth consumer, attribute set `{"compare_request_id"}` (R-S05-10 names consumer units as deliberate pin changes) |
| E4 | `SmartCompareApp/__tests__/s11/categoryRow.s11.test.tsx` node "S81-11 B2 / B3 / B4 -- coming-soon chips only under surfaces B3: a coming-soon tap -> the toast (+ iOS announcement), one category_coming_soon_tap event, no navigate, no compare" (renamed from "... no event, ...") | the event ships with SF1 (R-SF1-7, R-S11-27) |

### 4.2 Pins that must stay green and unedited

`tests/test_s80_b1_feedback.py` (incl. `test_b1_f7_allowlists_append_only`: the 25-name prefix and uniqueness; `test_b1_f6_existing_pins_hold`: `hacker_event` 422), `tests/test_events_allowlist_superset.py` (all five; after C11 the literal is found and allowlisted), `tests/test_feedback.py`, `test_feedback_service.py`, `test_feedback_allowlist_superset.py`, `test_m13_29_feedback_uuid.py`, `test_version_routes.py`, `test_s81_s10_fragrance_gate.py` (r51 order, the request_context static row; r06 is base noise), `test_s81_s10_gate_rows.py`, `test_referral_*` (incl. `test_referral_routes.py:64` `facebook` refused in both states), `test_share_routes.py`, `test_domain_s76.py`, `test_auth_routes_invite_fingerprint.py`, `tests/fixtures/s81_s09_flag_off_golden.json` readers, `test_w4_13_flag_off_ledger.py` + `test_s81_st1_usage_path_offloop.py` (both SF1 states), `test_db_improvements.py`, `test_m18_offload_sweep_residual.py`, `test_migration_*` (every file), `test_retro_w1_2b/2c/2d`, `test_sqlfluff_config.py`, `test_migration_index_predicate_immutability.py`, `test_s81_d22_nightly_learning.py`, `test_s81_g5_gate_rows.py`, `test_s71_u13_compare_auth_required.py` (T17 + T23), `test_s81_d16_operator_ingest.py` p2, the client `__tests__/s11/*` except E4 (B4, launchSurfaces R-S11-27, gateRows), the fourteen backend-scanning client fences.

## 5. RED tests: `tests/test_s81_sf1_surfaces_be.py`

Hermetic (the B1 file's limiter-off fixture, `TestClient(app)`, the recording Supabase clients, the netguard), no network, synthetic ids, pure ASCII + LF. Every RED row fails at base on an AssertionError only (missing symbols read through `getattr(module, name, None)` and asserted; the four event types 422 at base = an assertion on the status). Every PIN row runs with the FULL configuration of 2.3 and a call recorder (B1 rule). An autouse fixture deletes `ENABLE_FEEDBACK_V2`, `ENABLE_SURFACES_FIELD`, `APP_SURFACES_LIVE`, `ENABLE_REQUEST_CONTEXT_HEADERS`, `ENABLE_FRAGRANCE_ONLY_GATE` before each row and resets the request ContextVars after (the S81-05 `reset_request_context` tokens). Literals: `ARROW = "\u2192"`; `MISSING_USEFUL = "Validation error: body " + ARROW + " useful: Field required"`; `SHARE_BASE = "Validation error: body " + ARROW + " share_target: Input should be 'whatsapp', 'copy', 'x', 'telegram', 'snapchat' or 'other'"`; the other 1.9 strings; `BASE_EVENTS_31` (the full measured base list); `BASE_SAVE_KWARGS = ("user_id", "comparison_id", "useful", "mattered_most", "change_suggestion", "access_token", "winner_correct", "price_correct", "specs_correct")`; `LOG_SEARCH_PARAMS = ["query", "input_type", "user_id", "products_found", "success", "error_message", "cost", "duration_ms", "is_synthetic"]`. `OFF = [None, "", "false", "0", "off", "no", " FALSE "]`, `ON = ["true", " TRUE ", "1", "yes", "On"]`.

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R01 | `test_r01_feedback_v2_reader` | `getattr(feedback_service, "feedback_v2_enabled", None)` is callable; True for every ON spelling, False for every OFF spelling (and `2`, `enabled`) | RED (None) | C6 |
| R02 | `test_r02_log_search_reader` | `database_service._feedback_v2_enabled` same table; the two readers agree on 14 spellings | RED | C10 |
| R03 | `test_r03_surfaces_reader` | `version_routes.surfaces_field_enabled` same table | RED | C7 |
| R04 | `test_r04_surfaces_knob_parse` | `surfaces_live()` under each knob value: unset / `""` / `",,,"` / `"fashion"` / `"skincare;makeup"` -> `{"skincare": False, "makeup": False}`; `"skincare"` -> (T, F); `" Makeup , SKINCARE "` -> (T, T); `"makeup,fragrances,electronics"` -> (F, T); `list(result) == ["skincare", "makeup"]`; `all(type(v) is bool)` | RED | C7 |
| R05 | `test_r05_version_surfaces_on` | ENABLE_SURFACES_FIELD ON (each spelling), knob `skincare`: body == the five base values + `"surfaces": {"skincare": True, "makeup": False}`; `list(body)` == five + `["surfaces"]`; the raw JSON text contains `"skincare":true` (a JSON boolean, never a string) | RED | C7 |
| R06 | `test_r06_version_key_order_both_flags` | SF1 ON + ENABLE_FRAGRANCE_ONLY_GATE ON: `list(body) == five + ["surfaces", "categories_live"]` | RED | C7 |
| P07 | `test_p07_version_off_identity` | ENABLE_SURFACES_FIELD each OFF spelling, `APP_SURFACES_LIVE=skincare,makeup`, ENABLE_FEEDBACK_V2 ON: S81-10 OFF -> body == the base five-key literal; S81-10 ON -> the r51 six-key literal; the `version_routes.os` recorder saw NO `getenv("APP_SURFACES_LIVE")` | PIN | C7 gated |
| R08 | `test_r08_unknown_chip_never_on_wire` | knob `skincare,fashion,makeup,FRAGRANCES,electronics`: `set(body["surfaces"]) == {"skincare", "makeup"}` and both True | RED | C7 |
| P10 | `test_p10_feedback_off_422_bytes` | each OFF spelling + full config: every 1.9 feedback 422 body (9 bodies incl. `[1]`, `"x"`, `null`, bad JSON) -> status 422, `body["success"] is False`, `body["code"] == "VALIDATION_ERROR"`, `body["error"] ==` the literal, `request_id` a str; AND `FeedbackRequest.model_validate(b)` raises with `json.loads(e.json(include_url=False))` == the recorded base error list for the dict bodies | PIN | C5 gated |
| P11 | `test_p11_feedback_off_accepts_and_drops` | each OFF spelling + full config: the extras body of 1.9 -> 200 `{"success": True, "message": "Feedback received"}`; the `save_feedback` recorder saw ONE call whose kwargs keys == `BASE_SAVE_KWARGS` in order and whose values equal the base values (useful True, the rest None / [] ) | PIN | C5 gated |
| P12 | `test_p12_feedback_off_stored_row` | OFF + full config, through the REAL `save_feedback` (route recorder for `fire_and_forget` runs the coroutine) with a recording client: the insert payload == `{"useful": True, "mattered_most": ["price"], "comparison_id": UUID, "change_suggestion": "s", "winner_correct": "correct"}` exactly, with every new field also sent | PIN | C5 + C6 gated |
| R13 | `test_r13_feedback_on_accepts_v2` | ON: body without useful + `identity_correct "wrong"`, `wrong_side "first"`, `preference "second"`, `correction "  Dior Sauvage EDT  "`, `compare_request_id UUID.upper()`: 200; recorder kwargs include `useful=None`, `identity_correct="wrong"`, `wrong_side="first"`, `preference="second"`, `correction="Dior Sauvage EDT"`, `source="result"`, `compare_request_id=UUID` (canonical lower) | RED (422 at base) | C5 |
| R14 | `test_r14_feedback_on_stored_row` | ON, real `save_feedback`: payload has NO `useful` key when None; has the five sent keys + `source`; `useful` False is written as False | RED | C6 |
| R15 | `test_r15_feedback_on_422s` | ON: correction 81 chars after strip -> 422 `... correction: String should have at most 80 characters`; correction `"   "` -> 200 and `correction=None`; identity_correct `maybe` / wrong_side `third` / preference `both` / source `admin` -> 422 `literal_error` messages; compare_request_id `bad` -> 422 `... compare_request_id: Value error, compare_request_id must be a valid UUID`; `useful` `"maybe"` -> the base bool message | RED | C5 |
| R16 | `test_r16_feedback_on_contact_source` | ON: `source "contact"` stored as `"contact"`; omitted -> `"result"` | RED | C5 + C6 |
| R20 | `test_r20_event_types_appended` | `VALID_EVENT_TYPES[:31] == BASE_EVENTS_31`; `VALID_EVENT_TYPES[31:] == ["category_coming_soon_tap", "share_channel_selected", "share_target_opened", "store_cta_tap"]`; unique | RED | C5 |
| R21 | `test_r21_property_allowlist_dict` | `getattr(fr, "EVENT_PROPERTY_ALLOWLIST", None)` == the closed dict of 2.2 exactly (frozensets); keys are the four new names, all in VALID_EVENT_TYPES; `store_cta_tap` -> `{"merchant_id"}` only | RED | C5 |
| R22 | `test_r22_new_types_accepted_off` | each OFF spelling: a batch of the four types with extra keys -> 200 `"4 events received"`; the `track_events_batch` recorder dicts == the four-key base shape with `event_data` AS SENT; no `[EVENTS]` record at DEBUG on any logger | RED (422 at base) | C5 (unflagged widening) |
| R23 | `test_r23_property_filter_on` | ON: `store_cta_tap {"merchant_id": "m1", "url": "u", "price": 9}` -> stored `{"merchant_id": "m1"}`; `share_target_opened {"share_target": "sms", "x": 1}` -> `{"share_target": "sms"}`; `share` (existing) with extras -> unchanged; exactly one INFO `[EVENTS] properties dropped type=store_cta_tap n=2` and one `... type=share_target_opened n=1`; the record messages carry no value (`m1`, `u`) | RED | C5 |
| P24 | `test_p24_events_off_identity` | each OFF spelling + full config: `save` with `compare_request_id "bad"` and `UUID` -> 200; dicts == `{"user_id", "event_type", "event_data", "comparison_id"}` exactly (no compare_request_id key) | PIN | C5 gated |
| R25 | `test_r25_events_on_request_id` | ON: an item with `compare_request_id UUID` -> the dict carries it; real `track_events_batch` record carries it; an item without -> no key; `"bad"` -> 422 `... events \u2192 0 \u2192 compare_request_id: Value error, compare_request_id must be a valid UUID` | RED | C5 + C6 |
| P26 | `test_p26_events_batch_off_records` | OFF, real `track_events_batch` with a recording client: records == base literal for a 3-item batch (user / comparison / session keys) | PIN | C6 |
| R27 | `test_r27_size_cap_before_filter` | ON: `store_cta_tap` with `event_data` of 10,001+ bytes -> 422 the base `event_data too large (max 10KB)` message (the cap precedes the filter) | RED (422 at base for a different reason: the row asserts the TYPE was accepted by checking the message is the size message, not the event_type message) | C5 |
| P30 | `test_p30_share_off_422_bytes` | each OFF spelling + full config, ENABLE_REFERRAL_SYSTEM on, auth overridden: share_target in {`sms`, `email`, `more`, `foo`, `5`, `null`, `WhatsApp`, `True`} -> 422 `error == SHARE_BASE`; `ShareRequest.model_validate` errors == the base list; `create_invite` recorder never called | PIN | C8 gated |
| R31 | `test_r31_share_on_widened` | ON: `sms` / `email` / `more` -> `create_invite` called with that target (recorder; the route returns its 201 stub body); `facebook` -> 422 with the nine-value message | RED | C8 |
| R32 | `test_r32_service_share_targets` | `ReferralService.create_invite` with a recording client: ON `sms` passes the check (reaches `ensure_code_for_user`); OFF `sms` raises `ValueError` whose `str` == `"share_target 'sms' not in allowed set ['copy', 'other', 'snapchat', 'telegram', 'whatsapp', 'x']"` (the base literal) | RED (ON half) | C9 |
| P33 | `test_p33_code_redeem_other` | the code-redeem insert payload carries `"share_target": "other"` in both states | PIN | unchanged |
| R40 | `test_r40_log_search_on_bound_id` | ON + ENABLE_REQUEST_CONTEXT_HEADERS ON + a bound header uuid: the real `log_search` insert record carries `compare_request_id` == the canonical id; ON + nothing bound -> no key | RED | C10 |
| P41 | `test_p41_log_search_off_identity` | each OFF spelling + a bound id: the record == the base literal; a recorder on `request_context.compare_request_id` (patched on the module object) saw ZERO calls | PIN | C10 gated |
| P42 | `test_p42_log_search_signature` | `list(inspect.signature(database_service.log_search).parameters) == LOG_SEARCH_PARAMS` | PIN | R-SF1-9 |
| R50 | `test_r50_migration_files_once` | exactly one `046_*.sql` = `046_comparison_feedback_v2.sql` and one `049_*.sql` = `049_share_target_and_request_ids.sql` in migrations/ and rollback/; each starts with BEGIN and ends with COMMIT (the `_retro_r_mig_sql` statement splitter); ASCII, no CR, ends with LF | RED | C1-C4 |
| R51 | `test_r51_046_text` | the six `ADD COLUMN IF NOT EXISTS` with types (`text NULL` x 4, `text NOT NULL DEFAULT 'result'`, `uuid NULL`); the five CHECK constraint names and their value sets (compact text); `char_length(correction) <= 80`; `idx_comparison_feedback_request` partial on `compare_request_id IS NOT NULL`; `ALTER COLUMN useful DROP NOT NULL` appears ONLY inside a DO block that reads `is_nullable`; no `price_correct` ADD; no `CREATE FUNCTION`, `SECURITY DEFINER`, `POLICY`, `GRANT`, `REVOKE` | RED | C1 |
| R52 | `test_r52_049_text` | `pg_constraint`, `contype = 'c'`, `ILIKE '%share_target%'`, `<> 1` + RAISE, `DROP CONSTRAINT %I`; the nine-value ADD CONSTRAINT `referral_invites_share_target_check`; two `uuid NULL` columns + the two partial indexes; no function / policy / grant | RED | C3 |
| R53 | `test_r53_rollbacks` | rollback 046 drops exactly the six columns and guards `SET NOT NULL` with a NULL-row RAISE; rollback 049 RAISEs on sms / email / more rows, restores the six values, drops the two columns | RED | C2, C4 |
| R54 | `test_r54_parity` | the 046 sets == `IDENTITY_VALUES` / `WRONG_SIDE_VALUES` / `PREFERENCE_VALUES` / `FEEDBACK_SOURCES` and `CORRECTION_MAX_CHARS == 80`; the 049 nine values == `WIDENED_SHARE_TARGETS` == `sorted(referral_service._WIDENED_SHARE_TARGETS)` == `typing.get_args(referral_routes.ShareTargetV2)` | RED | C1, C3, C5, C8, C9 |
| P60 | `test_p60_correction_readers` | `scripts/cron_learning.py` `FEEDBACK_COLUMNS` excludes `correction` and `compare_request_id` (read through the module constant); the files under app/ and scripts/ containing a `"correction"` / `'correction'` string literal (regex) are a subset of `{app/api/feedback_routes.py, app/services/feedback_service.py}`; no `select("*")` on comparison_feedback in app/ or scripts/ | PIN | privacy lens |
| P61 | `test_p61_log_hygiene_on` | ON, DEBUG on every logger: a feedback with a correction + id, an events batch with ids + filtered keys, a log_search with a bound id: no record message contains the correction text, any uuid, `merchant_id` value, or the knob value | RED (the paths 422 at base; the row asserts status 200 first) | C5, C6, C10 |
| P62 | `test_p62_superset_fence_and_client_line` | the literal `trackEvent('category_coming_soon_tap'` appears exactly ONCE under `SmartCompareApp/src` (in HomeScreen.tsx) and the name is in VALID_EVENT_TYPES; `launchSurfaces.ts` does not contain the literal | RED (absent at base) | C11, C5 |

Counts: RED rows 30 (R01-R06, R08, R13-R16, R20-R23, R25, R27, R31, R32, R40, R50-R54, P61*, P62*: P61 and P62 are RED at base and keep their P ids for their lens); PIN rows 11 (P07, P10, P11, P12, P24, P26, P30, P33, P41, P42, P60). The client E-row E4 is a jest change, not a pytest row. Fixtures are built from this brief (the unit has no tester scenario in `eval_regression.json`: the events / feedback / version surfaces are not compare-path outputs).

## 6. Mutation table (byte copy, exact one-match edit, the killing rows via pyt.py -k with bound 600, restore, sha256 compare; under `.qa-mutation.lock`)

| M | Mutant (on the GREEN bytes) | Killed by |
|---|---|---|
| M1 | `feedback_v2_enabled` returns True (not gated) | P10, P11, P12, P24, P30, P41 |
| M2 | the before model-validator drops the `isinstance(data, dict)` check (delegates a list) | P10 (`[1]`: the frozen class name in the message) |
| M3 | the OFF branch returns `data` instead of the base dump | P10 (`{}` -> 200), P11 |
| M4 | `submit_feedback` passes the new kwargs in both states | P11 |
| M5 | `save_feedback` writes `useful` unconditionally | R14 |
| M6 | `source` omitted from the ON kwargs | R16, R14 |
| M7 | correction limit 81 / no strip | R15, R13 |
| M8 | EventItem OFF validator validates instead of dropping | P24 |
| M9 | the four event names inserted BEFORE `image_load_failed` (order) | R20, test_b1_f7 (prefix holds: R20 only) |
| M10 | `EVENT_PROPERTY_ALLOWLIST["store_cta_tap"]` gains `url` | R21, R23 |
| M11 | the filter applied under OFF | R22 |
| M12 | the filter applied to every type | R23 (the `share` item) |
| M13 | the `[EVENTS]` line carries the dropped key names | P61, R23 (exact message) |
| M14 | `share_target` OFF validator removed (nine-value literal under OFF) | P30 |
| M15 | `_share_targets()` returns the widened set in both states | R32 (OFF half) |
| M16 | `log_search` reads the context before the flag | P41 (recorder) |
| M17 | `log_search` writes the key when None | R40 (unbound half) |
| M18 | `surfaces_live` accepts any token (`{t: True for t in tokens}`) | R08, R04 |
| M19 | values `str(k in tokens).lower()` (strings, not booleans) | R04, R05 |
| M20 | `surfaces` placed after `categories_live` | R06 |
| M21 | `surfaces_field_enabled` ignores `.strip()` | R03 (` TRUE `) |
| M22 | the knob read before the flag | P07 (recorder) |
| M23 | 046 `DROP NOT NULL` outside the DO guard | R51 |
| M24 | 049 `<> 1` -> `= 0` | R52 |
| M25 | the client line moved into the timer callback | E4 (jest: called after `advanceTimersByTime` only, the `toHaveLength(1)` before the timer fails) |
| M26 | the client line uses a constant instead of the literal | P62 |

The jest mutant M25 runs through the junction at GREEN (one run of the s11 categoryRow file). Expected equivalent survivors: none named; any survivor is reported for a ruling.

## 7. Comm set and gates for GREEN (cheapest first)

1. `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on the six app files and the RED file; `sqlfluff lint --config .sqlfluff` on the four SQL files; bytes > 127 = 0 and no CR in every new file; `git diff --stat` content lines only for the CRLF app files.
2. The RED file in both flag states (bound 600): flags unset, then `ENABLE_FEEDBACK_V2=true ENABLE_SURFACES_FIELD=true` exported for that one runner call (the rows set their own states; the second run proves no row depends on the ambient env).
3. The pins: set A + set B of 1.10 (bound 1200 each) + `tests/test_s81_s05_request_context.py` + `tests/test_s81_st1_usage_path_offloop.py` + `tests/test_w4_13_flag_off_ledger.py` again with `ENABLE_FEEDBACK_V2=true` exported (the ledger identical in both SF1 states, R-SF1-9).
4. G9 (the S81-16b precedent): the FINAL 046 / 049 / rollbacks on a throwaway PostgreSQL 18 cluster in the GREEN notes folder: the 1.8 sequence (apply, re-apply, negatives, refused rollbacks, rollbacks, re-apply, the guard RAISEs, the nullable-skip path) + APPLY_046 / APPLY_049 PRECHECK and POSTCHECK grids as expected; NOT MEASURED if the binaries do not start.
5. The comm set (R-SF1-12), chunks of at most 25 files, bound 1200, base record by per-file reuse (LC-6 / GC-9 of `05303c6f/a0bfab95...` 695 files and the older records: a member is reused only when its text references none of `kb_serve`, `kb_operator`, `structured_comparison_service`, `price_service`, `cron_kb_coverage`, `cron_learning`, `variant_hint_learned` nor CLAUDE.md, is not a glob walker and its own file did not change since the record; the rest at base in a junction-free scratch worktree; the record stored as `base_records/18cb9e04.../<set-sha256>.txt`). Members (measured recipe at base, 278 files before the named additions; GREEN re-derives and the set grows only):
   - the reference grep over `feedback_routes|feedback_service|version_routes|referral_routes|referral_service|database_service|app\.main|TestClient` in tests/*.py;
   - every importer of an edited test-support helper (none edited);
   - the migration readers: every `tests/test_migration_*.py`, `test_retro_w1_2b/2c/2d`, `test_sqlfluff_config`, `test_migration_index_predicate_immutability`, `test_account_deletion_u8b*`, `test_s79_b3b_apple_revoke`, `test_s81_s03_llm_ledger_v2`, `test_s81_s16b_kb_brands`, `test_s81_kb_schema`;
   - the SmartCompareApp-scanning backend tests (25 files mention `SmartCompareApp`, incl. `test_events_allowlist_superset`, `test_feedback_allowlist_superset`, the copy fences, the client-truth pins);
   - the CLAUDE.md readers by the import graph: `test_ci_gates`, `test_behavior_dimension_translation`, `test_s81_s04_spend_breaker`, `test_s81_s08b_legacy_fingerprint`, `test_s81_s08b_gate_rows`, `test_s81_s23_bypass_retire` (+ any reader the grep for `CLAUDE.md|CLAUDE_MD` adds: 38 files matched the text at base, most of them for comments; run all 38);
   - the named source-scanning pins in EVERY backend set: `test_migration_index_predicate_immutability`, `test_openai_key_log_hygiene_s69`, `test_model_config*`, `test_prompt_fence`, `test_u3c_store_false_pin`, `test_start_command*`, `test_sentry_channels_u8d_unit` and every glob / rglob / listdir / scandir / getsource / ast.parse reader (104 files matched at base);
   - named members whatever the grep says: `test_s71_u13_compare_auth_required`, `test_version_routes`, `test_s80_b1_feedback`, `test_feedback*`, `test_referral_*`, `test_share_routes`, `test_domain_s76`, `test_auth_routes_invite_fingerprint`, the s09 golden readers (`test_s81_s09_device_quota`), the W4-13 chain (`test_w4_13_flag_off_ledger`, `test_w4_13_measurement_truth`, `test_s81_st1_usage_path_offloop`), `test_s81_s05_request_context`, `test_s81_s10_fragrance_gate`, `test_s81_s10_gate_rows`, `test_s81_d22_nightly_learning`, `test_s81_g5_gate_rows`, the new RED file;
   - MINUS the four `tests/test_precommit_hook*.py` files: NOT RUN (no `.githooks` change; say so in every GREEN / final title).
   `comm -13` of the sorted FAILED node ids (base vs head) EMPTY; r06 lexicon CRLF noise and the two tiktoken-cold prompt_truth ERRORs recorded identically.
6. Client (the orchestrator creates the junction at GREEN): `node node_modules/jest/bin/jest.js --ci __tests__/s11` (the E4 node green; B4 and launchSurfaces unchanged and green), `node node_modules/typescript/bin/tsc --noEmit`, `node node_modules/eslint/bin/eslint.js src/screens/HomeScreen.tsx __tests__/s11/categoryRow.s11.test.tsx`, the fourteen backend-scanning client fences by path (docs/, migrations/, app/ and SmartCompareApp/src are touched); the FULL jest once in the final round (LC-7) at the 3,976 + the four w37 drift-node baseline.
7. The corpus gate (`scripts/verify_flag_byte_identity.py` over `_proof`): NOT expected to move (no extraction-spine file); run once at GREEN as a measurement with the flags the RED measured.
8. The hook on every commit (never `--no-verify`); the added-line sweep (no `@gmail`, `+973`, 8-digit runs, key shapes; no gitleaks keyword in a constant name holding a digest).

## 8. CLAUDE.md row text and owner steps (names only)

### 8.1 The block (inserted after the S81-G7 owner-steps bullet, one blank line before the heading)

**SESSION 81 flags (S81-SF1 SURFACES-BE, 2026-11-xx; TWO new flags `ENABLE_FEEDBACK_V2` + `ENABLE_SURFACES_FIELD` and the knob `APP_SURFACES_LIVE`, default OFF, read PER CALL, new names, so unset in production by construction (Railway not read); FOCUS (migrations 046 + 049 written NOT applied, the App-Review-visible `surfaces` key, the stored free text `correction`); spec `.qa-s80/S81-SF1_UNIT_SPEC.md` of the unit worktree, the review and rulings `specs/RULINGS_S81_SF1.md` and the gate `specs/GATE_S81_SF1.md` in `docs/investigations/2026-10-22-session-81-state/`; the frozen RED file `tests/test_s81_sf1_surfaces_be.py`; one client line, shipped only in the post-approval OTA):**
- `ENABLE_FEEDBACK_V2` (read by `feedback_service.feedback_v2_enabled`, the same name read locally by `database_service._feedback_v2_enabled`): ON, `POST /api/v1/feedback` accepts `useful` as optional and `identity_correct` (correct | wrong | unsure), `wrong_side` (first | second | both), `preference` (first | second | neither | unsure), `correction` (stripped, at most 80 characters, else a 422), `source` (result | contact, default result) and `compare_request_id` (a uuid, else a 422), written only when sent (`useful` only when not null, `source` always); `POST /api/v1/events` takes `compare_request_id` per item and filters the `event_data` of `category_coming_soon_tap` -> {category}, `share_channel_selected` -> {channel}, `share_target_opened` -> {share_target}, `store_cta_tap` -> {merchant_id} (`EVENT_PROPERTY_ALLOWLIST`; unknown keys dropped with one INFO `[EVENTS] properties dropped type=<type> n=<int>` per item, never a 422); `POST /api/v1/referrals/share` and `create_invite` accept `sms`, `email`, `more`; `log_search` writes `search_logs.compare_request_id` from the S81-05 request context (no new parameter). Flag OFF: byte-identical, incl. the 422 bytes of a body without `useful` and of a share_target outside the six (pinned by P10 / P30 with the full configuration); every new field is accepted and dropped. Readers that exclude `source = 'contact'` and never read `correction` (a prompt, an exemplar builder or a store report): pinned by P60.
- Unflagged (R-A1): `VALID_EVENT_TYPES` gains the four names at the end (the 422 message for an unknown type lists them); `HomeScreen.handleComingSoon` fires `trackEvent('category_coming_soon_tap', { category })` (S81-11c; OTA only).
- `ENABLE_SURFACES_FIELD` + `APP_SURFACES_LIVE` (read by `version_routes.surfaces_field_enabled` / `surfaces_live`): ON, `/api/v1/app/version` carries `surfaces` = `{"skincare": <bool>, "makeup": <bool>}` (a chip is true only when its key is in the comma-separated knob; unknown tokens ignored; unset = both false), after the five keys and before `categories_live` (the S81-11 `launchSurfaces.ts` contract). OFF: the key absent, the knob never read (P07).
- Migrations: `046_comparison_feedback_v2.sql` (the six columns, the five CHECKs, `idx_comparison_feedback_request`, `useful` DROP NOT NULL only when the live column is NOT NULL) and `049_share_target_and_request_ids.sql` (the share_target CHECK re-created by its live name with nine values; `compare_request_id` + a partial index on `user_events` and `search_logs`), each with a rollback; WRITTEN, NOT APPLIED; the one-paste files `specs/APPLY_046_*` / `APPLY_049_*`.
- Stated limits: the existing event types stay unfiltered; `image_load_failed` has no client emission yet; ContactUs rows are told apart by `source` (no new table) and today's rows all read `result`; the client-asserted `compare_request_id` is never checked against a run; no per-user rate change; the knob knows only the two chip keys; a NULL `useful` lowers `vw_cohort_feedback_lift.useful_pct`; T23 needed no re-record (the models are outside its closure).
- **Owner steps (names only; a dated ledger line per step):** (1) apply 046 then 049 (PRECHECK, ONE_PASTE, POSTCHECK each; send the PRECHECK grids: `useful_is_nullable` and the live share_target CHECK name); (2) update the App Privacy label (the correction text is user content) BEFORE the OTA that sends it; (3) `ENABLE_FEEDBACK_V2` ON on `web` only after (1) and the first post-approval OTA (CL3 / CL4 send the fields; nothing sends them before); (4) keep `ENABLE_SURFACES_FIELD` OFF in EVERY App Review window; ON (with `APP_SURFACES_LIVE`) only after the S81-11 OTA has propagated, never with a date in any copy; (5) `search_logs.compare_request_id` fills only once `ENABLE_REQUEST_CONTEXT_HEADERS` is ON and the S81-08 header ships; canary reads (names only): the `[EVENTS] properties dropped` count, the `Error saving feedback` / `Error batch tracking events` / `Error logging search` WARNING rate, the share_target counts by value; rollback = unset the variable (per call, immediate), then the rollback files only if needed.

### 8.2 The :341 pointer clause (after the S81-G7 sentence)

`ENABLE_FEEDBACK_V2` + `ENABLE_SURFACES_FIELD` and the knob `APP_SURFACES_LIVE` (S81-SF1 SURFACES-BE, default OFF): the rows of the **SESSION 81 flags (S81-SF1 SURFACES-BE, ...)** block.

### 8.3 In-place rewrites

- :578 last sentence: "NO event: `category_coming_soon_tap` ships with SF1's VALID_EVENT_TYPES widening (R-S11-27, S81-11c)." -> "A coming-soon tap fires `trackEvent('category_coming_soon_tap', { category })` (S81-SF1, unflagged with the VALID_EVENT_TYPES widening; R-S11-27, S81-11c)."
- :105: "`FeedbackRequest`: `useful, comparison_id, mattered_most, change_suggestion` + the three optional 027 fields `winner_correct / price_correct / specs_correct` (B1, S80, `Literal` correct | wrong | unsure, written only when sent)" -> the same + "; under `ENABLE_FEEDBACK_V2` (S81-SF1) `useful` is optional and the 046 fields `identity_correct / wrong_side / preference / correction / source / compare_request_id` are accepted (flag OFF: the base model and its 422 bytes)". (Section 11 Q6.)

### 8.4 docs/privacy-data-inventory.md (rewritten in place; no new Apple data type)

- Row 4 `OtherUserContent`: append "; under `ENABLE_FEEDBACK_V2` (S81-SF1) the optional correct product name `correction` (at most 80 characters; never sent to a model, an exemplar or a store report) and the answer columns `identity_correct` / `wrong_side` / `preference` -> `POST /api/v1/feedback` (`comparison_feedback`, migration 046)".
- Row 6 `UserID`: append "; a per-compare random `compare_request_id` (uuid4, the S81-08 `X-Compare-Request-Id` value; not a device or account id) keys feedback, events and `search_logs` rows under `ENABLE_FEEDBACK_V2` (migrations 046 / 049)".
- Row 8 `ProductInteraction`: append "; S81-SF1 events `category_coming_soon_tap` {category}, `share_channel_selected` {channel}, `share_target_opened` {share_target}, `store_cta_tap` {merchant_id only} (the property allowlist under `ENABLE_FEEDBACK_V2`)".
Purposes and the manifest array unchanged (owner / legal confirm: section 11 Q8).

### 8.5 The APPLY files (contents for GREEN; filed by the orchestrator)

- `APPLY_046_1_PRECHECK.sql` (read-only, one row): `pg15_or_later`, `feedback_table_present`, `useful_is_boolean`, `useful_is_nullable` (`YES` / `NO`: the pre-046 state, record it), `the_027_checks` = 3, `v2_columns_absent` = true (0 of the six), `row_count` (an int, no row content).
- `APPLY_046_2_ONE_PASTE.sql`: a two-line header + the FINAL 046 text.
- `APPLY_046_3_POSTCHECK.sql`: `column_count_v2` = 6, `useful_nullable` = YES, `source_default` = `'result'::text`, `source_not_null` = true, `check_count_v2` = 5, `request_index_present` = true, `null_source_rows` = 0.
- `APPLY_049_1_PRECHECK.sql`: `invites_present`, `events_present`, `search_logs_present`, `share_target_check_count` = 1, `share_target_check_name` (the live name, record it), `share_target_check_def` (the six values), `request_columns_absent` = true.
- `APPLY_049_2_ONE_PASTE.sql`: header + the FINAL 049 text.
- `APPLY_049_3_POSTCHECK.sql`: `share_target_check_count` = 1, the name `referral_invites_share_target_check`, the definition carrying the nine values, `events_request_uuid` = true, `search_logs_request_uuid` = true, both indexes present.

## 9. Stated limits (R-SF1-16 and measured)

- L1: the existing event types are unfiltered in both states (a later tightening follows the owner's names-only read of stored `event_data` keys).
- L2: the unknown-event_type 422 message grows by the four names in every state (the list echo, R-A1; build 3 swallows the 422).
- L3: `image_load_failed` (already allowlisted at :92) has no client emission; a client follow-up, not this unit.
- L4: ContactUs is routed out of the learning signal by the `source` column (R-SF1-8), not by a new table or endpoint (the plan's wording "routed out of comparison_feedback" read as "out of the learning readers"); until the one-line ContactUsScreen change (CL3's chain) every row is `result`, and the existing ContactUs rows stay `result` after 046 (recognisable today by the `[Category] Subject` prefix of `change_suggestion`; no backfill: Q5).
- L5: a malformed `compare_request_id` on one event 422s the whole batch under ON (the comparison_id precedent).
- L6: `compare_request_id` on feedback and events is CLIENT-ASSERTED: no server check that it matches a run (S81-22's join is best-effort); anonymous `/feedback` and `/events` stay forgeable (PLAN standing risk), so no learning signal auto-applies from them.
- L7: `useful` becomes nullable only after the owner's live check (the 046 guard); `price_correct` is not added (027 has it).
- L8: no per-user rate change on the endpoints (30/min, 60/min).
- L9: rollback 046 restores NOT NULL on `useful` whenever no NULL row exists, even if the PRECHECK had read it already nullable: the owner skips that DO block when the recorded pre-046 state was `YES`.
- L10: the knob accepts only the two chip keys; a third category needs a code change by design (the S81-11 parser ignores unknown keys).
- L11: `vw_cohort_feedback_lift` counts NULL-`useful` rows in its denominator, so `useful_pct` falls as Q1-only answers arrive (the view is out of scope: Q7).
- L12: a flag flip between the model validator's read and the handler's read of the same request can drop a v2 field or store `source` with a base body; benign, never a wrong value.
- L13: the store_cta_tap allowlist keeps KEYS only; a client can still put a URL into `merchant_id`'s value (Q4).
- L14: the T23 fixture is not re-recorded (Q1); the plan's sentence is satisfied vacuously.
- L15: an anonymous `correction` survives account deletion when it carries no user id (043 detaches by comparison_id and deletes by user_id).

## 10. Out of scope

CL3 / CL4 and every client send of the new fields (the ContactUs `source: 'contact'` line, the feedback card, the share builder, `share_target_opened` / `store_cta_tap` emissions, `image_load_failed`); a contact table or endpoint; the learning readers (D22b adds identity_correct / wrong_side / preference to the buckets; S81-22's judge join); `structured_comparison_service` (no edit); the `vw_cohort_feedback_lift` view; a value-shape rule for event properties; a backfill of historical ContactUs rows; any dependency, lock or `.githooks` change; the App Privacy label and App Store Connect text (owner steps).

## 11. Open questions for the orchestrator

- Q1 (R-SF1-4 / PLAN :169, measured contradiction): T23 compares only the `$ref` closure of the ten U13 operations, which contains none of FeedbackRequest / EventItem / EventBatchRequest / ShareRequest (1.11); the fixture needs NO re-record and stays green. Ruling asked: confirm no re-record (this spec's design, L14), or order a deliberate re-record anyway (a gratuitous fixture diff of the stored-but-uncompared components).
- Q2 (R-SF1-1, measured cycle): `database_service` cannot import `feedback_service` at module top (feedback_service imports database_service). This spec gives `database_service` a private one-liner reading the SAME env name (the S81-09 `_referral_rewards_paused` precedent) with a parity row (R02); the alternative is a function-local import inside `log_search` (an import per call). Ruling asked.
- Q3 (E3): the S81-05 consumer census gains `database_service.py` with `{"compare_request_id"}`; S81-22 likely edits the same table (compare_runs reads the context): a both-sides union at the second rebase.
- Q4 (L13, privacy lens): add a value rule for `store_cta_tap.merchant_id` (for example a string matching `^[a-z0-9][a-z0-9._-]{0,63}$`, else the key is dropped and counted in the same INFO line)? Not in R-SF1-5; the spec keeps keys-only unless ruled.
- Q5 (L4): backfill the existing ContactUs rows to `source = 'contact'` in 046 (by the `[` prefix of `change_suggestion`)? The spec does not (a data rewrite of applied rows; the prefix is a convention, not a key).
- Q6 (8.3): the :105 sentence is rewritten in place (edit-in-place principle) though R-SF1-14 names only :341 and :578; confirm.
- Q7 (L11): `vw_cohort_feedback_lift` (013, read by `/admin/cohort/feedback`) treats NULL `useful` as not-useful; a `CREATE OR REPLACE VIEW` with `WHERE cf.useful IS NOT NULL` would belong in 046 or a later migration. Out of scope here unless ruled.
- Q8 (R-SF1-11, "gains rows"): the inventory table rows are Apple data types; the new columns fall under the declared types 4 / 6 / 8, so this spec rewrites those rows in place instead of adding rows (a new row would need a manifest / app.json change and the native 1.0.1 binary). The App Privacy label wording for the owner (names only): "Other User Content: product feedback incl. an optional corrected product name; linked; App Functionality / Analytics". Confirm.
- Q9 (FOCUS check): nothing found that makes the unit more than FOCUS-by-migration-and-surface: no auth, consent, quota or security-middleware change; the feedback user client path (RLS) is unchanged; the 010 RLS INSERT policies cover the new columns (no column-level grants on these tables in the corpus; the live grants are the owner's PRECHECK to confirm).
- Q10 (collision map with S81-22): CLAUDE.md (the anchor after the S81-G7 block and the :341 clause: both add a block / sentence), `docs/privacy-data-inventory.md` (rows 5 / 6 / 8 likely), `tests/test_s81_kb_schema.py` r01 (the same tuple line: SF1 removes 046 / 049, S81-22 removes 048), `tests/test_s81_s05_request_context.py` (the census, Q3), `tests/test_migration_043_delete_user_cascade.py` (S81-22 only); migrations do not collide (046 / 049 vs 048). Every one is a both-sides union at whichever rebase comes second.
- Q11 (the RED gate): R27's base failure is a 422 for the event_type, the head a 422 for the size: the row asserts the message text, so it is an AssertionError at base; confirm the row form is acceptable.

Not done in this spec: no source, test, migration or docs file of the worktree was written (only this spec under `.qa-s80/`); the comm-set base record was not built (the RED round builds it, R-SF1-12); the jest suites were not run (no junction); G9 ran on the PROTOTYPE SQL only, the FINAL files are GREEN's G9.
