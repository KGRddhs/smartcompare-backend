# S81-SF1 SURFACES-BE: ENABLE_FEEDBACK_V2 + ENABLE_SURFACES_FIELD (dark), migrations 046 + 049 (written, not applied)

Base `18cb9e04a36382fc417307500a092486f618d95e` (origin/main), HEAD `bb012e346eca1a35b42d547a9916e10928c773f4` on `feature/s81-sf1-surfaces-be` (one commit through the hook). FOCUS unit (LC-1): migrations, the App-Review-visible `surfaces` key, stored user text. The hook test files `tests/test_precommit_hook*.py` were NOT RUN (no `.githooks` change). Nothing changes in production on merge: both flags are new names (unset), 046 / 049 are not applied, and the client line reaches phones only with the post-approval OTA (UB-R4).

## What the unit does

- `ENABLE_FEEDBACK_V2` (default OFF, read per call; `feedback_service.feedback_v2_enabled`, and the SAME name through the local one-liner `database_service._feedback_v2_enabled`: the import cycle forbids the import; parity pinned by r02). ON:
  - `POST /api/v1/feedback`: `useful` optional; `identity_correct` (correct | wrong | unsure), `wrong_side` (first | second | both), `preference` (first | second | neither | unsure), `correction` (raw input refused past 1,000 chars, C0 + DEL refused, stripped, blank -> null, at most 80 after the strip), `source` (result | contact, default result), `compare_request_id` (uuid, canonical lower case). A body with no answer is a 422 whose message ends with `feedback body carries no answer` (the GC-4d set). `save_feedback` writes `useful` only when not null, each 046 column only when not null, `source` always.
  - `POST /api/v1/events`: `compare_request_id` per item (uuid-validated) reaches `track_events_batch` and the record.
  - `POST /api/v1/referrals/share` (`ShareTargetV2`) and `ReferralService.create_invite` (`_share_targets()`): `sms`, `email`, `more`.
  - `log_search` writes `search_logs.compare_request_id` from the S81-05 request context, read inside under the flag; no new parameter (signature pinned by p42).
- `ENABLE_SURFACES_FIELD` + knob `APP_SURFACES_LIVE` (`version_routes.surfaces_field_enabled` / `surfaces_live`): ON, `/api/v1/app/version` carries `surfaces = {"skincare": bool, "makeup": bool}` (JSON booleans; unknown tokens ignored; unset = both false, key present) after the five keys and BEFORE `categories_live`. OFF: key absent, knob never read (p07 recorder).
- Unflagged by ruling (R-A1, R-SF1-38, R-SF1-27):
  - `VALID_EVENT_TYPES` gains `category_coming_soon_tap`, `share_channel_selected`, `share_target_opened`, `store_cta_tap` at the END of the one literal list.
  - In EVERY state those four types keep only their `EVENT_PROPERTY_ALLOWLIST` key with a passing value: `category` in {skincare, makeup}; `channel` / `share_target` in the nine share values; `merchant_id` = the 045 `kb_merchants.host` CHECK pattern (`MERCHANT_HOST_PATTERN`, pinned equal to `kb_service.KB_HOST_REGEX` by gate row GR4: feedback_routes may not import the KB leaf, P01), full match, at most 253 chars. Anything else is dropped (never a 422) and counted in ONE INFO `[EVENTS] properties dropped type=%s n=%d` per item. Existing types unfiltered (L1).
  - The three except arms log constants only: `[FEEDBACK] save failed type=%s code=%s`, `[EVENTS] batch insert failed type=%s code=%s`, `[SEARCH_LOG] insert failed type=%s code=%s` (`database_service.postgrest_error_code`: the short PostgREST / SQLSTATE code or None), no `exc_info`, no exception text (the PostgREST failing row carries user text; the G9 cluster shows `Failing row contains (...)` with the row values). The OFF log identity therefore excludes these three lines.
  - Client: `HomeScreen.handleComingSoon` fires `trackEvent('category_coming_soon_tap', { category: key });` after the iOS announce and before the toast timer (S81-11c; the literal; `trackEvent` already imported).

## Flag-OFF identity

`FeedbackRequest` has a before model-validator whose first statement reads the flag; OFF it validates a dict body through `_FeedbackRequestBase` (the frozen 18cb9e04 model) and returns its dump, so a body without `useful` gives the SAME 422 bytes (`Validation error: body -> useful: Field required`, U+2192 on the wire) and every new field is accepted and dropped; a non-dict body is left to `FeedbackRequest` itself (same class name in the error). `ShareRequest.share_target` OFF raises `PydanticCustomError('literal_error', 'Input should be {expected}', ...)` with the base six for any value outside them: the base error list byte-for-byte (p30: 8 values x 7 OFF spellings, the model errors too). `EventItem.compare_request_id` OFF returns None (dropped, never validated). The `save_feedback` call carries the nine base kwargs (p11), the stored rows are the base dicts (p12, p26, p41), the W4-13 ledger is unchanged in both SF1 states. Every PIN row runs with the full companion configuration and recorders (ruling B1).

## Migrations (WRITTEN, NOT APPLIED; proven on a throwaway PostgreSQL 18.1 cluster)

- `046_comparison_feedback_v2.sql`: `SET LOCAL lock_timeout = '5s'`; guard (the table, `useful` boolean, the three 027 CHECKs); `identity_correct`, `wrong_side`, `preference`, `correction` (at most 80), `source text NOT NULL DEFAULT 'result'`, `compare_request_id uuid` + `idx_comparison_feedback_request` (partial); `useful` DROP NOT NULL only inside the DO block that reads `is_nullable`, which then writes the column comment `sf1_dropped_not_null`; assert block; `NOTIFY pgrst, 'reload schema'`. Rollback drops the six columns and restores NOT NULL only when the comment is present (then clears it), refusing while a NULL `useful` row exists.
- `049_share_target_and_request_ids.sql`: lock_timeout; the share_target CHECK resolved from `pg_constraint` (contype c, exactly one or RAISE), dropped by its live name, re-created as `referral_invites_share_target_check` with nine values; `user_events.compare_request_id` + `search_logs.compare_request_id` uuid + `idx_user_events_request` / `idx_search_logs_request` (partial, immutable predicate); assert; NOTIFY. Rollback refuses while an sms / email / more invite exists, restores the six values, drops the two columns.
- G9 (`g9/g9_outputs.txt`): 57 PASS steps, 0 unexpected. Database (i) (`useful` NOT NULL): PRECHECK / ONE_PASTE / POSTCHECK of both, re-apply, 9 CHECK / type negatives refused, the positive v2 row and sms / email / more invites accepted, both rollbacks REFUSED while blocking rows exist, both rollbacks after the delete (useful NOT NULL restored, comment cleared, six-value CHECK back), re-apply after rollback. Database (ii) (`useful` already nullable): no comment written, rollback keeps it nullable; **M40b** (`IF TRUE OR` rollback on a byte copy) restored NOT NULL on (ii): KILLED (L17). Guards: 046 without 027 RAISEs; 049 with two share_target CHECKs RAISEs.

## RED rows -> flag -> flip order

| Area | RED / PIN nodes (tests/test_s81_sf1_surfaces_be.py) | Gate |
|---|---|---|
| readers | r01 r02 r03 r04 | both flags + knob |
| /app/version | r05 r05b r06 r08; PIN p07 | ENABLE_SURFACES_FIELD |
| /feedback | r13 r14 r15 r15b r15c r16; PIN p10 p11 p12 | ENABLE_FEEDBACK_V2 |
| /events | r20 r21 r22 r23 r23b r25 r27; PIN p24 p26 | widening + filter unflagged; request id flagged |
| share | r31 r32; PIN p30 p33 | ENABLE_FEEDBACK_V2 |
| log_search | r40; PIN p41 p42 | ENABLE_FEEDBACK_V2 |
| migrations | r50 r51 r52 r53 r54 | owner apply |
| privacy | p60 p61 r70 p62 | unflagged log arms; the client line |

Flip order (R-SF1-29): apply 046 then 049 -> `ENABLE_FEEDBACK_V2` ON on `web` (safe for build 3: every build-3 body carries `useful`, build 3 sends none of the four new types, the six share values are unchanged) -> the first OTA that carries CL3 / CL4. Never the reverse. `ENABLE_SURFACES_FIELD` OFF in every App Review window; ON only after the S81-11 OTA has propagated.

## E-rows (deliberate pin changes)

| E | Node | Change |
|---|---|---|
| E1 | none | T23 (`tests/test_s71_u13_compare_auth_required.py::test_T23_openapi_unchanged`) green unedited, flags unset AND exported (R-SF1-17) |
| E2 | `tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once` | the reserved tuple `("046", "048", "049", "051")` -> `("048", "051")` (+ one comment line); S81-22 edits the same line: union by hand at the second rebase |
| E3 | `tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app` | `_ALLOWED_CTX_FILES` + `_CTX_CONSUMER_ATTRS` admit `app/services/database_service.py` with `_LOG_SEARCH_CTX_ATTRS = {"compare_request_id"}` (S81-22 adds compare_runs.py: union) |
| E4 | `SmartCompareApp/__tests__/s11/categoryRow.s11.test.tsx` B3 | renamed "... one category_coming_soon_tap event, ..."; `toHaveLength(0)` -> exactly one call equal to `['category_coming_soon_tap', { category: 'skincare' }]`; B4 and `launchSurfaces.s11.test.ts` :180 unchanged |

No other pin moved.

## Counts and gates

- RED file (frozen, sha256 `b86f473e...`, re-hashed first and last): 195 / 195 flags unset `[pyt] tag=sf1g-red-off elapsed=9s bound=600s status=OK rc=0`; 195 / 195 with ENABLE_FEEDBACK_V2=true ENABLE_SURFACES_FIELD=true APP_SURFACES_LIVE=skincare exported `[pyt] tag=sf1g-red-on elapsed=9s bound=600s status=OK rc=0` (121 RED + 74 PIN).
- Gate rows `tests/test_s81_sf1_gate_rows.py` (G-SF1-GR1..GR4): 4 / 4 `[pyt] tag=sf1g-gaterows elapsed=5s status=OK rc=0`; each proven RED-then-green by an inverse edit on GREEN's own bytes (7 mutants, 7 KILLED, restored, sha-verified): `MUTATION_TABLE.md`.
- Mutants: the RED round's 48 (47 KILLED + M40b) on the prototype; M40b KILLED by G9; jest M25 (the line moved into the timer) KILLED by E4; M26 (a local constant) survives jest and `tests/test_events_allowlist_superset.py` (the fence cannot see a non-literal) and is KILLED by p62 + GR2.
- CI-order set (29 files, spec 1.10 sets A + B): 1 failed (the r06 CRLF noise, as at base), 1273 passed, 1 skipped `[pyt] tag=sf1g-ciorder elapsed=46s bound=1200s status=FAIL rc=1`.
- Comm set: the RED's 297 files (`specs/S81_SF1_COMM_SET.txt`) + the gate-rows file = 298; `tests/test_secret_scan_static.py` alone (31 passed, `[pyt] tag=sf1g-secret status=OK`) + 12 chunks of at most 25 (bound 1200, 48-135 s each), against the STORED base record `base_records/18cb9e04.../4345a784...txt` (REUSED, LC-6). HEAD FAILED 18 = exactly the environmental nodes of the record (test_auth_interceptor x2, test_prompt_truth x2 cold tiktoken, the CRLF working-copy nodes d16 r10, d17 r9, d22c p1 x5, s10 r06, s16 r27 x5, s19 r15). `comm -13` (branch-only NEW) = EMPTY; `comm -23` = exactly the 121 RED nodes. Per-chunk lines in `comm_progress.txt`, the sets in `comm_compare.txt`.
- Exported-flag re-runs (s05, st1, w4_13 measurement truth, the W4-13 ledger, U13 incl. T23): 1065 passed `[pyt] tag=sf1g-exported elapsed=26s bound=1200s status=OK rc=0`.
- Corpus gate (GC-8, `scripts/verify_flag_byte_identity.py --flags ENABLE_FEEDBACK_V2,ENABLE_SURFACES_FIELD`, 414 records / 1,656 calls): OVERALL SHA256 base == HEAD (`fc30f415...`).
- Client (jest 29.7.0, typescript 5.9.3, eslint 9.39.4, node 24.11.1, through the orchestrator's junction): `__tests__/s11` 9 suites / 135 passed; tsc --noEmit rc 0; eslint on HomeScreen.tsx + the E4 file 0 errors; the fourteen backend-scanning fences + `b3a/nativeStrings.b3a.test.ts` (the r37 inventory parser): 13 / 14 + b3a green, the four `config/nativeBundle.w37` drift nodes only. The FULL jest NOT run (LC-7).
- Lint: ruff E9/F63/F7/F82 + py_compile clean on the six app files; sqlfluff clean on the four SQL files; new files ASCII + LF.

## Stated limits

L1 existing event types unfiltered; L2 the unknown-type 422 lists the four names in every state; L3 `image_load_failed` has no client emission; L4 ContactUs rows are told apart by `source` only after the CL3 client line (no backfill); L5 a malformed `compare_request_id` on one event 422s the whole batch under ON; L6 `compare_request_id` is client-asserted; L7 `useful` becomes nullable only through the 046 guard; L8 no rate change; L10 the knob knows two chip keys; L11 NULL `useful` lowers `vw_cohort_feedback_lift.useful_pct` (SF1b); L12 a flip between the model's and the handler's flag reads can drop a v2 field for that one request; L14 / L16 T23 needs no re-record while the published OpenAPI document changes with the flag OFF (served only outside the Railway env); L15 an anonymous `correction` survives account deletion when it carries no user id; L17 the rollback comment gate is proven by the G9 run, not a frozen row. Also: the three narrowed log arms are a deliberate unflagged log change; the b3a inventory parser is a named client gate; the S81-22 collisions (the CLAUDE.md anchor + the :341 clause, the kb_schema r01 line, the s05 allowlist) are both-sides unions at the second rebase; a pre-existing comment on `useful` would be overwritten by 046 (the PRECHECK reports `useful_has_comment`).

## Owner steps (names only; a dated ledger line per step)

1. Apply 046 then 049 with `APPLY_046_{1_PRECHECK,2_ONE_PASTE,3_POSTCHECK}` and `APPLY_049_*` (send the PRECHECK rows: `useful_is_nullable`, `useful_has_comment`, the live share_target CHECK name, the row counts).
2. The App Privacy label wording before the OTA that sends the fields: User Content (the optional corrected product name), Identifiers (the compare request id).
3. `ENABLE_FEEDBACK_V2` ON on `web` after (1) and BEFORE the CL3 / CL4 OTA.
4. `ENABLE_SURFACES_FIELD` OFF in every App Review window; ON (with `APP_SURFACES_LIVE`) only after the S81-11 OTA.
5. SF1b (the `vw_cohort_feedback_lift` denominator) after a read of the answer rates; the ContactUs `source: 'contact'` line rides CL3.

Rollback = unset the variable (per call); the rollback files only after the unset.

## [NATIVE READ]

EMPTY (no new user-facing copy).

Files beside this body: `MUTATION_TABLE.md`, `g9/g9_outputs.txt`, `comm_compare.txt`, `comm_progress.txt`, `logs/`, `apply/APPLY_046_*.sql`, `apply/APPLY_049_*.sql`, `S81-SF1_GREEN_REPORT.md`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
