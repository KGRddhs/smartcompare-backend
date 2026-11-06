# S81-SF1 SURFACES-BE: ENABLE_FEEDBACK_V2 + ENABLE_SURFACES_FIELD (dark), migrations 046 + 049 (written, not applied)

Base `18cb9e04a36382fc417307500a092486f618d95e` (origin/main), HEAD `00173abf831f6f67b6494c45999499a17f8be050` on `feature/s81-sf1-surfaces-be` (two commits through the hook: GREEN `bb012e34` + the final-round commit `00173abf`; the rebase onto the fetched origin/main was a no-op). FOCUS unit (LC-1): migrations, the App-Review-visible `surfaces` key, stored user text. The hook test files `tests/test_precommit_hook*.py` were NOT RUN (no `.githooks` change). Nothing changes in production on merge: both flags are new names (unset), 046 / 049 are not applied, and the client line reaches phones only with the post-approval OTA (UB-R4).

## What the unit does

- `ENABLE_FEEDBACK_V2` (default OFF, read per call; `feedback_service.feedback_v2_enabled`, and the SAME name through the local one-liner `database_service._feedback_v2_enabled`: the import cycle forbids the import; parity pinned by r02). ON:
  - `POST /api/v1/feedback`: `useful` optional; `identity_correct` (correct | wrong | unsure), `wrong_side` (first | second | both), `preference` (first | second | neither | unsure), `correction` (raw input refused past 1,000 chars, C0 + DEL refused, stripped, blank -> null, at most 80 after the strip), `source` (result | contact, default result), `compare_request_id` (uuid, canonical lower case). A body with no answer is a 422 whose message ends with `feedback body carries no answer` (the GC-4d set). `save_feedback` writes `useful` only when not null, each 046 column only when not null, `source` always.
  - `POST /api/v1/events`: `compare_request_id` per item (uuid-validated) reaches `track_events_batch` and the record.
  - `POST /api/v1/referrals/share` (`ShareTargetV2`) and `ReferralService.create_invite` (`_share_targets()`): `sms`, `email`, `more`.
  - `log_search` writes `search_logs.compare_request_id` from the S81-05 request context, read inside under the flag; no new parameter (signature pinned by p42).
- `ENABLE_SURFACES_FIELD` + knob `APP_SURFACES_LIVE` (`version_routes.surfaces_field_enabled` / `surfaces_live`): ON, `/api/v1/app/version` carries `surfaces = {"skincare": bool, "makeup": bool}` (JSON booleans; unknown tokens ignored; unset = both false, key present) after the five keys and BEFORE `categories_live`. OFF: key absent, knob never read (p07 recorder).
- Unflagged by ruling (R-A1, R-SF1-38, R-SF1-27):
  - `VALID_EVENT_TYPES` gains `category_coming_soon_tap`, `share_channel_selected`, `share_target_opened`, `store_cta_tap` at the END of the one literal list.
  - In EVERY state those four types keep only their `EVENT_PROPERTY_ALLOWLIST` key with a passing value: `category` in {skincare, makeup}; `channel` / `share_target` in the nine share values; `merchant_id` = the 045 `kb_merchants.host` CHECK pattern (`MERCHANT_HOST_PATTERN`, pinned equal to `kb_service.KB_HOST_REGEX` by gate row GR4: feedback_routes may not import the KB leaf, P01), full match, at most 253 chars (the cap pinned in use by GR6). Anything else is dropped (never a 422) and counted in ONE INFO `[EVENTS] properties dropped type=%s n=%d` per item. Existing types unfiltered (L1).
  - The three except arms log constants only: `[FEEDBACK] save failed type=%s code=%s`, `[EVENTS] batch insert failed type=%s code=%s`, `[SEARCH_LOG] insert failed type=%s code=%s` (`database_service.postgrest_error_code`: the short PostgREST / SQLSTATE code or None, pinned by GR5), no `exc_info`, no exception text (the PostgREST failing row carries user text; the G9 cluster shows `Failing row contains (...)` with the row values). The OFF log identity therefore excludes these three lines.
  - Client: `HomeScreen.handleComingSoon` fires `trackEvent('category_coming_soon_tap', { category: key });` after the iOS announce and before the toast timer (S81-11c; the literal; `trackEvent` already imported).

## Flag-OFF identity

Outside the unflagged parts above (the four appended event types accept where the base 422s; the L2 message; the L16 OpenAPI document; the three narrowed log lines): `FeedbackRequest` has a before model-validator whose first statement reads the flag; OFF it validates a dict body through `_FeedbackRequestBase` (the frozen 18cb9e04 model) and returns its dump, so a body without `useful` gives the SAME 422 bytes (`Validation error: body -> useful: Field required`, U+2192 on the wire) and every new field is accepted and dropped; a non-dict body is left to `FeedbackRequest` itself (same class name in the error). `ShareRequest.share_target` OFF raises `PydanticCustomError('literal_error', 'Input should be {expected}', ...)` with the base six for any value outside them: the base error list byte-for-byte (p30: 8 values x 7 OFF spellings, the model errors too). `EventItem.compare_request_id` OFF returns None (dropped, never validated). The `save_feedback` call carries the nine base kwargs (p11), the stored rows are the base dicts (p12, p26, p41), the W4-13 ledger is unchanged in both SF1 states. Every PIN row runs with the full companion configuration and recorders (ruling B1).

## Migrations (WRITTEN, NOT APPLIED; proven on a throwaway PostgreSQL 18.1 cluster)

- The 046 header and the `source` column comment claim no reader (L21; the D22b follow-up adds one); the G9 run below applied the GREEN bytes, which differ from HEAD only in that comment text and header.
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

## Final round (RULINGS_REBASE_S81_SF1, RB-SF1-1..6)

- Replay: `git fetch origin main` = `18cb9e04` (unmoved); `git rebase origin/main` = a no-op (0 commits replayed, no conflict).
- ONE round commit `00173abf` on top of the GREEN commit `bb012e34` (through the hook; test-only + docs + one SQL comment):
  - `tests/test_s81_sf1_gate_rows.py` gains **G-SF1-GR5** (`database_service.postgrest_error_code` returns None, never exception text, for a ValueError, an httpx.ConnectError and a code-less / text-code APIError whose str carries a synthetic failing-row marker; the three narrowed except-arm records carry no marker; both flag states) and **G-SF1-GR6** (a 300-character host-shaped `store_cta_tap.merchant_id` is DROPPED by the unflagged filter, the 253-character cap in use, a 253-character host kept; counted once in the INFO line).
  - `migrations/046_comparison_feedback_v2.sql`: the header sentence and the `COMMENT ON COLUMN public.comparison_feedback.source` text no longer claim a reader (now: "No reader filters on this column yet; the D22b follow-up excludes contact rows."); no other SQL change; `APPLY_046_2_ONE_PASTE.sql` regenerated (body byte-identical to the migration; the other five APPLY files unchanged).
  - `CLAUDE.md` (the S81-SF1 block, in place, CRLF kept): the flag-OFF sentence qualified by the unflagged parts; GR5 / GR6 named; L18-L21; the counts sentence (48 mutants = 47 + M40b by G9).
- The frozen RED file is untouched.

## Counts and gates (at HEAD `00173abf`)

- RED file `tests/test_s81_sf1_surfaces_be.py` sha256 `b86f473e661b912c42164c2ce25aaa4f6de71c4700e7e2d356a51d44c1f3ef3a` (re-hashed first and last, working copy and blob): 195 / 195 flags unset `[pyt] tag=sf1f-red-off elapsed=6s bound=600s status=OK rc=0`; 195 / 195 with ENABLE_FEEDBACK_V2=true ENABLE_SURFACES_FIELD=true APP_SURFACES_LIVE=skincare exported in the runner call only `[pyt] tag=sf1f-red-on elapsed=6s bound=600s status=OK rc=0` (121 RED + 74 PIN; R51 and R50 included).
- Gate rows `tests/test_s81_sf1_gate_rows.py` (G-SF1-GR1..GR6, 7 nodes; sha256 `f34ac1d2e6f75d0e3f79d97638fc41bb0317585b5e172af0d8664a5ac2d90af6`): 7 / 7 unset `[pyt] tag=sf1f-gaterows-off elapsed=4s status=OK rc=0` and exported `[pyt] tag=sf1f-gaterows-on elapsed=5s status=OK rc=0` (GR3 re-run against the reworded 046).
- Mutants: the RED round's 48 = 47 KILLED by the rows + M40b KILLED by the G9 cluster proof (the RED report's prose 47 / 46 is superseded); GREEN's 7 gate-row mutants KILLED; the final round's 2: **A01** (`return str(exc)[:200]` in place of `return None` in `postgrest_error_code`) KILLED by GR5 `[pyt] tag=sf1f-mut-A01 elapsed=4s status=FAIL rc=1` (AssertionError); **A03** (the 253 cap replaced by `True`) KILLED by GR6 `[pyt] tag=sf1f-mut-A03 elapsed=4s status=FAIL rc=1` (AssertionError); both on sha-verified byte copies under `.qa-mutation.lock`, restored, sha equal. Jest M25 (the line moved into the timer) KILLED by E4. GC-7 deviation, named: the gate's "literal replaced by a constant" mutant (GREEN's M26) cannot turn E4 or `tests/test_events_allowlist_superset.py` red (identical behaviour; the fence reads literals only); it is killed by p62 + GR2.
- E-row files flags unset: `tests/test_s81_kb_schema.py` + `tests/test_s81_s05_request_context.py` 705 passed `[pyt] tag=sf1f-erows elapsed=18s status=OK rc=0`.
- R8 pair `tests/test_sentry_channels_u8d_unit.py` + `tests/test_sentry_channels_u8d.py`: 273 passed `[pyt] tag=sf1f-r8 elapsed=18s status=OK rc=0`. `tests/test_paid_route_metering.py` 21 passed unset `[pyt] tag=sf1f-paid-off status=OK rc=0` and exported `[pyt] tag=sf1f-paid-on status=OK rc=0`.
- CLAUDE.md readers by the import graph (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire): 510 passed `[pyt] tag=sf1f-readers elapsed=17s status=OK rc=0`.
- CI-order set of record (29 files): 1 failed (`tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content`, the CRLF working-copy node of the base record), 1273 passed, 1 skipped `[pyt] tag=sf1f-ciorder elapsed=42s bound=1200s status=FAIL rc=1` (equal to GREEN).
- Comm set (measured): the GREEN's 298 files (the RED's 297 + the gate-rows file) at HEAD = `tests/test_secret_scan_static.py` alone (31 passed `[pyt] tag=sf1f-secret status=OK rc=0`) + 12 chunks of at most 25 (297 members, bound 1200): c00 FAIL 33s (auth_interceptor x2), c01 OK 43s, c02 OK 28s, c03 OK 71s, c04 OK 13s, c05 OK 25s, c06 FAIL 104s (prompt_truth x2 ERROR, cold tiktoken), c07 OK 135s, c08 FAIL 74s (7 CRLF nodes), c09 FAIL 66s (7 CRLF nodes), c10 OK 71s, c11 OK 47s. Against the STORED base record `base_records/18cb9e04.../4345a784...txt` (REUSED outright, LC-6: the same main sha): HEAD FAILED 18 = exactly the environmental nodes of the record (test_auth_interceptor x2, test_prompt_truth x2, d16 r10, d17 r9, d22c p1 x5, s10 r06, s16 r27 x5, s19 r15); `comm -13` (branch-only NEW) = EMPTY; `comm -23` = exactly the 121 RED nodes.
- Corpus gate NOT repeated: the GREEN measured `fc30f415...` equal at base and HEAD; the round commit changes no app/ or scripts/ file.
- Client (through the orchestrator's junction; node 24.11.1, jest 29.7.0, typescript 5.9.3, eslint 9.39.4): `__tests__/s11` 9 suites / 135 passed; tsc --noEmit rc 0; eslint on HomeScreen.tsx 0 errors (3 warnings); the fourteen fences + `b3a/nativeStrings.b3a.test.ts`: 13 / 14 + b3a green, 242 passed, exactly the four `config/nativeBundle.w37` drift nodes failed; the FULL jest ONCE (LC-7, from full.json): 3,976 passed + 4 failed (the w37 nodes only) + 13 pending + 13 todo (4,006), 41 / 41 snapshots; the E4 node passes with its new expectation.
- Lint: ruff E9/F63/F7/F82 (no cache) + py_compile clean on the gate-rows file (the six app files unchanged since GREEN, clean there); sqlfluff clean on 046; the hook ran ruff + sqlfluff on the round commit.
- The hook test files `tests/test_precommit_hook*.py` were NOT RUN: the unit changes no `.githooks` file (RB-SF1-3).

## Stated limits

L1 existing event types unfiltered; L2 the unknown-type 422 lists the four names in every state; L3 `image_load_failed` has no client emission; L4 ContactUs rows are told apart by `source` only after the CL3 client line (no backfill); L5 a malformed `compare_request_id` on one event 422s the whole batch under ON; L6 `compare_request_id` is client-asserted; L7 `useful` becomes nullable only through the 046 guard; L8 no rate change; L10 the knob knows two chip keys; L11 NULL `useful` lowers `vw_cohort_feedback_lift.useful_pct` (SF1b); L12 a flip between the model's and the handler's flag reads can drop a v2 field for that one request; L14 / L16 T23 needs no re-record while the published OpenAPI document changes with the flag OFF (served only outside the Railway env); L15 an anonymous `correction` survives account deletion when it carries no user id; L17 the rollback comment gate is proven by the G9 run, not a frozen row; L18 the `merchant_id` rule applies `KB_HOST_REGEX` only, not the 045 top-label CHECK: dotted numeric hosts such as 10.0.0.1 stay in `event_data` (follow-up SF1c ANDs `kb_service.KB_HOST_TOP_LABEL_REGEX` with a row); L19 erasure: 043 nulls `comparison_id` on surviving feedback / events rows but nothing severs `compare_request_id` on anonymous rows; inside SF1 the deleted user's `search_logs` row goes, so no link survives at this commit; once a device-keyed table stores the same id the follow-up 043b severs it at deletion (S81-22's hook note names it); L20 `save_feedback` / `track_events_batch` still RETURN `{'error': str(e)}` to `fire_and_forget`, which discards results: nothing reaches a log or a response (a follow-up narrows the return); L21 the 046 `source` column comment describes a D22b reader, not a HEAD behaviour. (L9 / L13 withdrawn.) Also: "flag OFF byte-identical" holds outside the unflagged parts (the four appended event types accept where the base 422s; the L2 message; the L16 OpenAPI document; the three narrowed log lines); the b3a inventory parser is a named client gate; the S81-22 collisions (the CLAUDE.md anchor + the :341 clause, the kb_schema r01 line, the s05 allowlist) are both-sides unions at the second rebase; a pre-existing comment on `useful` would be overwritten by 046 (the PRECHECK reports `useful_has_comment`).

## Owner steps (names only; a dated ledger line per step)

1. Apply 046 then 049 (in that order) with `APPLY_046_{1_PRECHECK,2_ONE_PASTE,3_POSTCHECK}` and `APPLY_049_*` (send the PRECHECK rows: `useful_is_nullable`, `useful_has_comment`, the live share_target CHECK name, the row counts).
2. The App Privacy label wording before the OTA that sends the fields: User Content (the optional corrected product name), Identifiers (the compare request id).
3. `ENABLE_FEEDBACK_V2` ON on `web` after (1) and BEFORE the CL3 / CL4 OTA (safe for build 3).
4. `ENABLE_SURFACES_FIELD` OFF in every App Review window; ON (with `APP_SURFACES_LIVE`) only after the S81-11 OTA.
5. SF1b (the `vw_cohort_feedback_lift` denominator) after a read of the answer rates; the ContactUs `source: 'contact'` line rides CL3.

Rollback = unset the variable (per call); the rollback files only after the unset.

## [NATIVE READ]

EMPTY (no new user-facing copy).

Reports (session-81 state folder, specs/): `S81_SF1_RED_REPORT.md`, `S81_SF1_GREEN_REPORT.md`, `S81_SF1_ADV1_correctness.md` (SOUND, 5 minors), `S81_SF1_ADV2_privacyandappreview.md` (SOUND, 3 minors), `S81_SF1_FINAL_REPORT.md` (this round); `GATE_S81_SF1.md`, `RULINGS_S81_SF1.md`, `RULINGS_REBASE_S81_SF1.md`. Beside them: `MUTATION_TABLE.md`, `g9/g9_outputs.txt`, `comm_compare.txt`, the APPLY files `APPLY_046_*.sql` / `APPLY_049_*.sql` (the final-round set).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
