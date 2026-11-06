# S81-SF1 SURFACES-BE -- adversarial spec review

- Unit: S81-SF1 SURFACES-BE (FOCUS). Reviewer lens: correctness + privacy-and-appreview (folded).
- Spec: .qa-s80/S81-SF1_UNIT_SPEC.md, sha256 2621dd63953f8a103fa548dd1e3b93516c45ae2373e83d23ceb531f25b060b4d (re-hashed at start: match). Base 18cb9e04 (worktree HEAD measured = base; git status --short = 0 lines before; only this review file after).
- Probes (scratch only, notes folder <scratchpad>/sf1rev/): probe_mech.py (FastAPI 0.141.1 + pydantic 2.13.4 replica of the 1.9 (a) mechanism through a real RequestValidationError), probe_m2.py (mutant M2), an APIError str probe.
- Pytest (one run): [pyt] tag=sf1-rev-base start=2026-11-06 15:39:39 end=2026-11-06 15:39:45 elapsed=6s bound=600s status=OK rc=0 (8 passed: d22 p6/p7, s05 p01, the events superset rows) / [hermeticity] sentinel checked 8 test(s) / [netguard] blocked 0 attempt(s) from 0 node(s).

## Verdict: APPROVE_WITH_CHANGES

The core mechanism holds by measurement (the OFF 422 bytes, the T23 closure). No blocking defect in the design; five MAJOR corrections (log hygiene of the failure arms, the store_cta_tap value rule, the missing inventory fence, the RED form of four rows, the owner flip order) must land in the rulings before RED.

## Confirmed (re-measured, not refuted)

- 1.9 (a): the before model-validator delegating to a frozen base copy reproduces the base 422 through FastAPI for 15 bodies ({}, comparison_id bad, useful null / "maybe", [1], "x", JSON null, bad JSON, mattered_most + bad id, change_suggestion 1001, ...): every 422 errors list identical (type / loc / msg / input / ctx); only 200 echoes differ (the probe's own response dump). M2 (isinstance dropped) is killable: [1] / "x" give `model_type` "... instance of <frozen class>" vs base `model_attributes_type` (FastAPI validates with from_attributes).
- 1.11: T23 compares only `_referenced_components` of the ten operations (tests/test_s71_u13_compare_auth_required.py:955-1003); no re-record needed. Other /openapi.json readers (test_flush_live_price_key.py:543, test_retro_w1_9.py:387, test_m13_21) read other paths only.
- 1.1 / 1.2 / 1.5 / 1.7 file:line rows re-read: feedback_routes.py:60-93, :102-127, :171-232; feedback_service.py:197-251 (insert :247, except :249-251), :312-319; version_routes.py:12-24; HomeScreen.tsx:149-160; categoryRow.s11.test.tsx:315-379: as stated.
- 1.3: feedback_service imports referral_service only function-locally (feedback_service.py:124): no cycle for C9. The database_service cycle (feedback_service.py:9) is real.
- S81-05 census form (tests/test_s81_s05_request_context.py:1345-1400): E3 as written is the right change.

## Refuted claims / measured contradictions

1. Section 7 item 6 / 4.2 ("the fourteen backend-scanning client fences" cover the docs edit): REFUTED. SmartCompareApp/__tests__/b3a/nativeStrings.b3a.test.ts:17 reads docs/privacy-data-inventory.md and r37 (:141-164) parses every `| n |` row by splitting cells on unescaped pipes (cells[1] = the type, cells[5] = the purposes). It is NOT in the fourteen; C17 edits rows 4 / 6 / 8. A cell shift (an unescaped pipe in the appended text, or text appended after the last pipe) is caught only by the final full jest (LC-7).
2. 2.4 failure table ("ON, 046 / 049 not applied: fails inside the except arm, a WARNING, response unchanged"): INCOMPLETE for the share path. ReferralService.create_invite inserts referral_invites with no try (the insert after the :306-310 check); share_comparison catches only WeeklyInviteCapExceeded and ValueError (referral_routes.py:176-231). ON + 049 unapplied + `sms` = an APIError 23514 -> 500 INTERNAL_ERROR on a synchronous user-facing route, captured by Sentry with the PostgREST details.
3. Privacy (implicit in 2.2 / P61 "no record message contains the correction text"): REFUTED for the failure arms. feedback_service.py:250 logs `f"Error saving feedback: {e}"`; measured: `str(postgrest.exceptions.APIError(...))` prints the whole dict incl. `details` ("Failing row contains (...)" for 23502 / 23514 = the whole row: user_id, comparison_id, change_suggestion and the new `correction`). The 2.4 row "ON, useful still NOT NULL live -> 23502" is an anticipated path that lands stored user text in Railway logs. (Sentry: LoggingIntegration(level=ERROR), sentry_service.py:736, so WARNING lines stay out of Sentry events; the 500 of item 2 does reach Sentry.) P61 measures only success paths.
4. L13 (keys-only allowlist; a URL may ride in merchant_id): a stated limit that contradicts the binding ruling R-SF1-5 ("a merchant id only: never a URL, a price or a product name"). Not acceptable as a limit.
5. C3 header claim "indexes are partial on an all-NULL column at apply time, so the build is instant": REFUTED in form. A non-CONCURRENT CREATE INDEX scans the whole table even for an all-NULL partial predicate, and every ALTER TABLE in the one transaction holds ACCESS EXCLUSIVE on user_events / search_logs / referral_invites until COMMIT, so a long admin analytics read on search_logs queues every log_search insert behind the ALTER. Small today, but "instant" is not measured on the live sizes (the PRECHECK reports a row count for comparison_feedback only).
6. 4.2 lists tests/test_s81_d22_nightly_learning.py as "stay green" without naming its constraint: test_p6 (:1553-1556) reads VALID_EVENT_TYPES by `ast.literal_eval` of the module-level Assign in feedback_routes.py, and test_p7 (:1586-1590) collects save_feedback's `record[...]` keys by AST. A GREEN that builds the list by concatenation or a helper constant breaks p6 with a non-assertion ValueError. Unlisted pin collision (stays green only if the four names go INSIDE the literal, as C5 says).

## Corrections (for the rulings)

- C-1 (MAJOR, privacy): under ENABLE_FEEDBACK_V2 the except arms on the unit's paths (save_feedback, track_events_batch, log_search) must log type names / the PostgREST code only (for example `[FEEDBACK] save failed type=%s code=%s`), never `{e}`; OFF keeps the base line byte-identical. Add a RED row: ON + a recording client raising APIError whose details carry a synthetic correction -> no record message contains it. Mutant: the ON arm logs `{e}`.
- C-2 (MAJOR, privacy, R-SF1-5): add value rules to the allowlist filter (ON): merchant_id must match a closed id shape (for example ^[a-z0-9][a-z0-9._-]{0,63}$); category in {skincare, makeup} (the S81-11 chip keys); share_target in WIDENED_SHARE_TARGETS; channel in a closed channel set; a value failing its rule drops the key and is counted in the same INFO n. Rows + a mutant (a URL accepted). Delete L13.
- C-3 (MAJOR, comm set): add SmartCompareApp/__tests__/b3a/nativeStrings.b3a.test.ts (r37) to the GREEN client gate by path; C17 must say the appended text goes INTO column 3 ("Where the client sends it") and carries no unescaped pipe.
- C-4 (MAJOR, RED form): rows that would fail at base with a non-assertion: R14 (a direct `save_feedback(identity_correct=...)` call -> TypeError), R32 ON half (`create_invite(..., "sms")` raises ValueError at base), R50-R53 (reading a missing migration file -> FileNotFoundError), R54 (`referral_routes.ShareTargetV2` -> AttributeError). Each must assert existence / signature first (`assert path.exists()`, `assert "identity_correct" in inspect.signature(...).parameters`, getattr(..., None)), or drive through the route.
- C-5 (MAJOR, failure table + owner step): add the share row of refuted item 2 (ON before 049 -> 500 + Sentry) and the 23502 log-content consequence; and make owner step (3) "ENABLE_FEEDBACK_V2 ON after 046 + 049 are applied and BEFORE (or with) the OTA that carries CL3 / CL4". ON is safe for build 3 (it always sends `useful`, six-value targets, no new types), while OFF + a CL3 / CL4 client = every Q1-only answer 422-dropped and every sms / email / more share 422-refused (the invite never created). As written ("only after ... the first post-approval OTA (CL3 / CL4 send the fields)") the order opens that window.
- C-6 (migration): add `NOTIFY pgrst, 'reload schema';` to 046 and 049 (the 042 precedent, migrations/042_search_logs_is_synthetic.sql:128 and :165): under ON `source` is written on EVERY feedback insert, so a stale PostgREST schema cache = PGRST204 on every feedback write until a reload. R51 / R52 pin it.
- C-7 (migration): `SET LOCAL lock_timeout` (for example '5s') at the top of 046 and 049 so an apply behind a long reader fails fast instead of queueing live writes; the PRECHECKs report row counts of user_events, search_logs and referral_invites.
- C-8 (data quality): under ON a body `{}` is accepted and stores a row carrying only `source` (+ user_id): anonymous empty-row spam at 30/min that the CL3 answer-rate read and D22b count. Rule: under ON at least one answer field (useful, identity_correct, wrong_side, preference, correction, the three 027 fields, a non-empty mattered_most or change_suggestion), else a 422 (ON only; build 3 always sends useful). Optional: wrong_side / correction only with identity_correct = wrong.
- C-9 (row gap): no row pins "flag ON + knob unset -> `surfaces` PRESENT with both false" at the route (R04 tests the parser only; a GREEN that omits the key on an empty knob survives every row). Add R09 + a mutant.
- C-10 (correction hygiene): reject or strip control characters (U+0000 makes the insert fail 22P05 and lands in the except arm; a newline is not part of a product name) and cap the raw input before strip (a Field max_length, for example 400) so a huge body is refused at the model.
- C-11 (stated limit missing): with the flag OFF the published OpenAPI document changes (useful no longer required, the six new fields, the nine-value share_target enum), the class the #55 precedent called an OFF-path divergence (tests/test_flush_live_price_key.py:525-547). Not production-visible (test_m13_21), but a docs consumer reads a contract the server refuses: state it as L16.
- C-12 (GREEN hygiene): the S81-05 census (tests/test_s81_s05_request_context.py:1355-1368) fails any app file whose text contains `request_context`, `x-compare-request-id` or `header_state` outside the allowlist: no comment or docstring in feedback_routes.py / feedback_service.py / referral_* / version_routes.py may name the module or the header (only database_service.py joins, through E3).
- C-13 (L9): record the pre-046 nullability where the rollback can read it (for example a COMMENT ON COLUMN useful written by the 046 guard only when it dropped NOT NULL) and let rollback 046 restore NOT NULL only then, instead of an owner skipping a DO block by hand.

## Blocking issues

None at the spec level, provided C-1..C-5 are ruled before RED (C-1 and C-2 change rows and mutants; C-4 changes the RED form; C-5 is the owner-step text the CL3 / CL4 consumers depend on).

## Contract risks

- R1: CL3 / CL4 have no server capability signal; they rely on the owner flipping ENABLE_FEEDBACK_V2 before their OTA (C-5). If the order slips, the OFF identity itself (P10 / P30) becomes the refusal: Q1-only feedback lost silently, sms / email / more refused with a 422 the CL4 sheet must handle (PLAN :176 says 'other' until 049, but the client cannot see 049).
- R2: between merge and the flip the four new event types are accepted UNFILTERED (the filter is under the flag while the widening is not). Filtering touches only requests that 422 at base, so it is byte-identical for every base-accepted request and could ship unflagged under R-A1; the brief R-SF1-5 rules it under the flag: an orchestrator choice to confirm (question 3).
- R3: a NULL `useful` lowers vw_cohort_feedback_lift.useful_pct (L11); ContactUs rows already sit in the same denominator; the dashboard reading changes on the flip, not on merge.
- R4: compare_request_id is client-asserted on feedback and events (L6); 043 detaches cross-user rows by comparison_id only, so a forged id can link a row to another user's run in S81-22's join (best effort; no erasure gap for the user's own rows, which 043 deletes by user_id).
- R5: the App-Review surface is the `surfaces` key only; OFF = absent (P07 with the knob set). The owner step "OFF in every review window" is the only control; no code guard ties it to a binary version (acceptable by R-S11-29 (b)).

## Pin collisions not listed in 4.1 / 4.2

- tests/test_s81_d22_nightly_learning.py::test_p6_field_and_event_vocabularies (ast.literal_eval of VALID_EVENT_TYPES: the list must stay one literal Assign) and ::test_p7_feedback_writer_columns (AST of save_feedback `record` keys: a superset is fine).
- SmartCompareApp/__tests__/b3a/nativeStrings.b3a.test.ts r37 (the inventory table parser).
- tests/test_s81_s05_request_context.py::test_s05_p01 needles beyond E3 (C-12).
- No FY25 / w4_11 / retro_w2_1 / W4-13 fixture collision found: test_s75_fanout_identity drives scs directly (no log_search), IDENTITY_NODES (tests/test_s81_kb_schema.py:474-479) pins files this unit does not edit.

## Questions for the orchestrator

1. Spec Q1 (T23): confirmed by measurement; rule "no re-record" and record the R-SF1-4 sentence as superseded.
2. C-5: ENABLE_FEEDBACK_V2 ON after 046 + 049 and BEFORE the CL3 / CL4 OTA (not "after the first post-approval OTA")?
3. R2: ship the property filter unflagged (it only narrows types that 422 at base) or keep it under the flag as R-SF1-5 says?
4. C-2 value rules over the spec's Q4 keys-only default; name the closed `channel` set (CL4's builder: whatsapp, telegram, x, sms, email, copy, more?).
5. C-8 (the at-least-one-answer rule under ON) and its recorded 422 literal.
6. C-1's ON log template, and whether the OFF arm stays `{e}` (identity) or is narrowed unflagged as a log-only change.
7. Spec Q2: the local one-liner in database_service (the usage_service.py:179 precedent) vs a stdlib leaf for both readers; this review prefers the one-liner + R02 parity (no new file).
8. C-6 / C-7: NOTIFY pgrst + lock_timeout in both migrations (042 has the NOTIFY; no migration in the corpus sets lock_timeout).

Not done in this review: no pytest beyond the one probe run; the G9 cluster was not re-run; the comm-set recipe counts (278 / 104 / 38 files) were not re-derived; the jest suites were not run (no junction).
