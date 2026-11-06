# S81-22 COMPARE-RUNS + capped judge: adversarial spec review (Opus, privacy-and-spend second lens)

- Spec: `.qa-s80/S81-22_UNIT_SPEC.md`, sha256 730c5017f09c2accdf261e3318a8ff76fb4071c3fa164926ded725ec2a6ea78b (re-hashed first: MATCH). Worktree HEAD 18cb9e04a36382fc417307500a092486f618d95e, `git status --short` empty before and after.
- Probes: a `git archive` copy of app/ tests/ migrations/ scripts/ data/ + .sqlfluff under `<scratchpad>/s22rev/wt` (deleted after this review). Nothing written in the worktree except this file.
- VERDICT: **APPROVE_WITH_CHANGES** - the design is sound and most citations re-measure, but one measured pin collision (B1) contradicts section 4.2, and two spend defects (B2, B3) must be ruled before RED.

## 1. Measured probes

P1 - the 048 hook against the 043 fence (probe 048 = the 043 CREATE byte-copied + the spec 2.9.5 statement after the comparison_feedback DELETE + the REVOKE). The scratch copy has no docs/ or .githooks, so docs-reading nodes fail in both runs. Base vs probe on the same three files:
- base (no 048): `[pyt] tag=s22rev-fencebase start=2026-11-06 15:30:20 end=2026-11-06 15:30:34 elapsed=14s bound=600s status=FAIL rc=1`: 7 failed / 81 passed (all 7 = docs-missing in the scratch copy: one-paste / precheck / postcheck / check-files / backfill / retro_w1_2d next-units doc).
- probe (048 present): `[pyt] tag=s22rev-fence048 start=2026-11-06 15:30:00 end=2026-11-06 15:30:13 elapsed=13s bound=600s status=FAIL rc=1`: 9 failed / 79 passed. The **two branch-only-new** failures:
  - `tests/test_migration_043_delete_user_cascade.py::test_fence_flags_each_dropped_delete` -> `AssertionError: ('kb_feedback', [])` (:1200)
  - `tests/test_migration_043_delete_user_cascade.py::test_fence_flags_each_weakened_delete_predicate` -> `AssertionError: ('kb_feedback', [])`
  - green with 048: test_cascade_erases_or_keeps_every_user_referencing_table, test_fence_reads_the_latest_definition, test_retro_w1_2d REVOKE census, test_migration_037 (exactly one GRANT).
- `[pyt] tag=s22rev-kb048 start=2026-11-06 15:30:41 end=2026-11-06 15:31:11 elapsed=30s bound=600s status=FAIL rc=1`: test_s81_kb_schema + s16b + index immutability + sqlfluff_config with the probe 048: 5 failed / 712 passed. r01 is the expected E1. The four sqlfluff_config hook / requirements nodes fail because the scratch copy has no .githooks and no requirements files. p05 / p07 / r08 / r20 and the s16b fence row are GREEN, and the probe 048 lints clean.

## 2. Refuted claims (measured truth, file:line)

R1. Section 4.2 says "the fence pins (:1055-1300) [stay green and unedited] WITH 048 present". REFUTED by P1. `test_fence_flags_each_dropped_delete` (:1192-1201) and `test_fence_flags_each_weakened_delete_predicate` (:1204-1212) iterate EVERY `kind == "delete"` statement of the LATEST definition (`_latest()` :638) and require a new gap for it. kb_feedback is not in `fence_user_tables`, so dropping or weakening its DELETE produces no gap. The alias-free form (2.9.5, Q1) does not escape it: it parses as a DELETE, and that is exactly what these two rows walk. The alias form (R-S22-10) fails `test_cascade_erases_or_keeps_every_user_referencing_table` instead ("unrecognised statement", :546). Either form needs an E-row in tests/test_migration_043_delete_user_cascade.py, a file section 4.2 lists as unedited and section 3 does not name.

R2. J27 says "a snapshot carrying `</EVIDENCE>` ... tags is neutralised". REFUTED. `prompt_sanitizer.sanitize_untrusted_block` (:55-72) only calls `neutralize_prompt_tags`, whose regex is `<\s*(/?)\s*(USER_INPUT|SEARCH_RESULTS)\s*>` (:13). `json.dumps(..., ensure_ascii=True)` does not escape `<` or `>`. A product name or verdict text holding `</EVIDENCE>` therefore closes the fence verbatim. Use the existing `<SEARCH_RESULTS>` region, or a script-local EVIDENCE neutraliser. Widening the shared regex would move the w4_11 prompt digests.

R3. R26 ("every new module-level name lacks ... key / token ...") fails on the spec's own names: `ROW_KEYS` and `LLM_CALL_KEYS` (2.2) contain KEY, and `JUDGE_MAX_TOKENS` (2.10) contains TOKEN. The E-G4-1 rule targets digest / hash constants carrying a 64-hex value, not every name. Narrow R26 to string constants whose value is 40+ hex (or rename the three).

R4. M21 ("camera line moved before the envelope arm", killed by R21) is an EQUIVALENT mutant. The arm fires only when `comparison_unsuccessful = not result.get("success")` (image_routes :629, :772), and `record_compare_run` returns on `success is not True`, so the moved line can never write a row. No row can kill it. Replace it with an AST row (extend R22 to the camera and URL sites: the call sits inside the `if result.get("success") is True:` block at :781).

R5. Spec 1.6: the ledger is "visible at the exit" for every input type. Measured: the URL path never binds an OpenAI ledger. `start_openai_ledger` is called only at scs :4293 / :4954 and image_routes :376, and `compare_from_urls` (url_extraction_service :1343) never reaches scs. Its extraction legs run in `asyncio.gather` children (:1389). URL rows therefore carry `llm_calls = None`, and the "never the producing model" routing (2.10.8) is blind for them. Camera rows LOSE the vision calls: the compare's own bind replaces the ContextVar, and the route keeps `vision_ledger` as a local (:376, :648, :679). Both need stated limits, or a `vision_records=` argument from the camera route.

R6. 2.9.3 says "the ruling fixed the column LIST and left types to the spec". R-S22-2 lists `data_coverage text NULL` explicitly. The spec silently retypes it to smallint. The brief rule says "a measurement that contradicts one is reported as a question, never silently overridden". The int is the measured value (result_gate :529, :545), but this must be a question.

R7. Citation drift in 1.8 (seed_kb_batch): `_anthropic_factory` is :92 (not :91), `build_requests` :249 (not :248), `anthropic_usage_record` :479 (not :478), `breaker = ...` :513 (not :510), `br.reserve(br.LANE_OFFCLOCK, bound)` :517 (not :514). Every other cited line re-measures: text_routes :885 / :1090 / :1481-1482, image :781-782, url :392, sentry :671-697, request_context :298-313, model_config :224-246, breaker :101-122 / :1102 / :1182 / :1224, llm_pricing :99-119 / :620, kb_seed_common :39-166, 045 :19-26 / :301-309 / :336 / :411-425, 043 :166-234.

## 3. Blocking issues (rule before RED)

B1 (pin collision, measured, R1). An E-row on tests/test_migration_043_delete_user_cascade.py is needed: restrict the two mutant rows to statements whose table is in `fence_user_tables` (or name kb_feedback as a known non-user hook table). Add it to section 3, section 4.1 (E3) and the 7.2 gate 4 list, and drop it from the 4.2 "unedited" list. Without it GREEN goes red in the migration readers.

B2 (spend: a not-ended batch is paid twice). Steps 9 and 2.15 handle a batch that does not end within JUDGE_MAX_WAIT_SECONDS 3600 as "pending; reserve held; no delete; nothing written". There is no `--resume` (G2 has one: seed_kb_batch :528-535) and no persisted batch id. The runs stay `judged_at NULL`, the next night submits them again in a NEW batch, the first batch is still processed and billed by Anthropic, its results are never read or ledgered, and its inputs persist 29 days because it is never deleted. Rule one of these:
- `batches.cancel` on timeout, then a results read of what finished;
- a durable pending-batch record (e.g. the llm_spend_ledger row with `provider_batch_id`, request_count 0) that the next run resumes before it submits;
- a G2-style `--resume`.
Add a J row and a mutant for it.

B3 (spend: repeated Haiku on unjudged runs). A run left `judged_at NULL` (escalation_capped, refused, breaker_off, or programmatic-only) is re-read on every night inside JUDGE_WINDOW_DAYS (up to 30), and step 9 re-batches it to Haiku each time. Step 11's capped runs are exactly these. Skip runs that already hold a `haiku` judgement row (the UNIQUE (run_id, judge) makes the check cheap), or set a per-run attempt marker. With the window at its default of 1 the overlap is small but nonzero (job-time drift). At 30 it multiplies spend by up to 30.

## 4. Corrections (non-blocking; fold into RULINGS)

C1. P01 is self-contradictory: "the second [client] with every compare_runs symbol replaced by RAISING stubs". The route calls `record_compare_run` unconditionally (the flag is read inside), so a raising stub of that function makes every flag-OFF request raise. State the seams: the REAL `record_compare_run` runs, with raising stubs on `build_run_row`, `_insert` and `_query_hmac`, and recorders on `_async_utils.fire_and_forget`, `_db_offload.run_db` and `get_admin_supabase_client`. Then M01 / M02 are killed by the recorder counts and not by a 500.

C2. R03: "the first statement is `if not compare_run_ledger_enabled(): return`" must skip a leading docstring Expr, or forbid one. Say which.

C3. Owner steps 8.2 / 8.1 (5) omit migration 050. The judge's ONE ledger row per batch and per escalation set goes to llm_spend_ledger, which is "written NOT applied" (the ledger line). Add "050 applied" as an ENABLE_BATCH_JUDGE apply precondition, or the spend record is the WARNING line only (2.15 "ledger insert fails").

C4. `common.log_counts` does `int(v)` over every value (kb_seed_common :152-155). The 2.12 report holds nested dicts (programmatic_fail, batch, escalation, pruned, evidence_bytes, errors), so passing the report to log_counts raises TypeError. Log a flattened counts dict and keep the nested dict for `write_report` only.

C5. Self-produced routing (2.10.8) is broader than R-S22-7. The ruling says "a run whose judged field's producing model equals the judge model". The spec tests ANY call in llm_calls. Once S81-06 routes any role to Anthropic (every role defaults to claude-haiku-5-5, model_config :224-230), nearly every run skips the Haiku batch and becomes an escalation candidate capped at 20 per run. Most runs then end escalation_capped forever, and B3 multiplies that. Rule field-level matching (the verdict / critic roles produce the judged fields; moderation and vision do not), or accept it as a stated limit with the expected share.

C6. Window ageing: a run that leaves JUDGE_WINDOW_DAYS with judged_at NULL is never judged again, but 2.14 tells D22b "judged_at NULL is pending". State "unjudged-expired" (created_at older than the window and judged_at NULL), so D22b does not count those runs as pending forever.

C7. Escalation count cap: PLAN_S81 :114 / :168 say "the escalation lane's daily USD and count caps". JUDGE_ESCALATION_MAX_PER_RUN is per script run: a manual rerun or a restart doubles it. Either make it a per-Riyadh-day count (the breaker's day) or state the limit.

C8. 2.10.9 step "APPLY: `breaker = br.spend_breaker_enabled()`; `ticket = br.reserve(...)`" reads as an unconditional reserve. G2 reserves only when the breaker is ON (seed_kb_batch :513-520), and with it OFF it neither reserves nor records (:551-562). Write the conditional explicitly. J11 covers only breaker ON: add a breaker-OFF row with zero reserve / settle / record calls.

C9. 2.10.11 user-'wrong' join: compare_runs.comparison_id is NULL whenever ENABLE_COMPARISON_ID_ECHO is OFF (production: every flag OFF, ledger 2026-11-06 15:10), and comparison_feedback has no compare_request_id at base. The 'wrong' trigger is therefore inert in production until echo ON or SF1. State it, and pin the comparison_feedback select to exactly (comparison_id, winner_correct) filtered `.in_("comparison_id", ids)`, so the judge never reads feedback user_id or free text (a J row). winner_correct exists since 027 (:28, :49).

C10. Gitleaks hygiene for the RED author: P04 / P05 / PJ1 store 64-hex literals (sha256 of files, device_key HMAC outputs). Their constant names must carry none of access / auth / api / credential / creds / key / password / secret / token. `DEVICE_KEY_*` is the natural name and would block the commit. Name it in the RED brief.

C11. R20 / R17 use a recorder in place of fire_and_forget, so the `_insert(row)` coroutine object is never awaited, which gives a RuntimeWarning (pytest has no filterwarnings=error, pyproject :38). The recorder should `.close()` unscheduled coroutines to keep the logs clean.

C12. The 048 rollback order: once 048 is applied, rolling back 045 alone (dropping kb_feedback) breaks every account deletion (42P01 inside delete_user_cascade), and deletion is an App Store requirement. The 048 header and the APPLY_048 POSTCHECK should state "roll back 048 before 045". Section 9 should note that any failure in the hook statement aborts the whole deletion (one function, one transaction).

C13. R-S22-10 vs the 043 fence (Q1): the alias-free text is the right form for `_DEL_RX`. But see R1/B1: no form of the statement leaves the fence file unedited.

## 5. Contract risks

K1 (legal truth). R-S12-18 / GC-2 let S81-12 record that kb_feedback is "deleted with the account's compare records". Measured: the hook reaches only runs whose comparison_id is set, which needs ENABLE_COMPARISON_ID_ECHO ON plus a signed-in text compare (1.3). Production has the echo OFF, so the hook deletes nothing, and the deletion leg of the recorded sentence would be false (only the 365-day TTL holds). Either make ENABLE_COMPARISON_ID_ECHO ON a flip precondition of every kb_feedback writer (none exists at base: only cron_learning reads it), or have S81-12 record the TTL alone. This is the orchestrator's call; it touches published legal text.

K2 (shared escalation lane). The live router reserves LANE_ESCALATION for Sonnet escalations (llm_router :1120, :1129, :1213). The nightly judge drawing the same lane's daily cap (default 1.0 USD, LLM_SPEND_CAP_ESCALATION_USD) can exhaust it, so live escalations are refused for the rest of that Riyadh day. R-S22-7 names this lane, so this is a ruling-level risk. Say whether to accept it (state the limit) or give the judge a sub-budget.

K3 (personalised verdict prose to the batch). L-VERDICT admits that the snapshot's verdict reason / key_tradeoff / declaration can carry cohort- or profile-shaped prose. PLAN_S81 :114 and R-S22-5 say "strip user ids / profile / cohort before any batch". Option: drop the verdict prose fields (keep the structured winner index / margin / supported) when `body.personalized` is True or `personalization_factors` is non-empty. That is a pure builder rule, testable on PERSONAL_BODY.

K4 (OpenTelemetry names, L-OTEL, unverified here too: no fetch). `gen_ai.operation.name` is, to this reviewer's knowledge, an enum of operation kinds (chat, text_completion, embeddings, ...), not a role. Mapping the role into it (R-S22-6) would misuse the attribute. The cache attribute spelling in recent semconv versions may also differ from `gen_ai.usage.cache_read_input_tokens`. The JSON is internal, so the cost is low, but it should not be described as OTel-conformant until it is verified.

K5. `refusal_reason` CHECK `^[a-z_]{1,64}$`: the house refusal codes are upper case (CATEGORY_NOT_LIVE, INSUFFICIENT_DATA). S81-22b would need a migration or a lower-casing rule. State the vocabulary now.

K6. The 048 hook deletes ALL kb_feedback rows sharing a target-linked compare_request_id, including rows another device wrote with a reused / forged id. This is harmless for privacy (it deletes more, never less), but the 7.3 "another user's run ... is NOT reachable" story should say that it is the RUN that is unreachable, not the feedback row.

K7. No response key, request field, refusal shape or credit path changes. T23, the FY25 digests, the w4_11 digests (as long as R2 is fixed locally), the s10 / s10b goldens and the W4-13 fixture do not move. The camera envelope interaction is safe (R4). No codeless 503 is added. Confirmed by reading.

## 6. Pin collisions (complete list)

- tests/test_migration_043_delete_user_cascade.py::test_fence_flags_each_dropped_delete and ::test_fence_flags_each_weakened_delete_predicate: MEASURED red with 048 (P1). Not in section 4.1.
- tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once (E1, measured red as expected) and P02_ALLOWED (E2): as stated.
- No other collision among the 043 / 037 / retro_w1_2d / index-immutability / kb_schema p05 / p07 / r08 / r20 / s16b readers (measured green with the probe 048).
- App-only AST scanners (test_s81_s06_router_gate_rows :844, test_s81_s03_llm_ledger_v2 :508 `_LEDGER` readers, test_s81_d03_deny_and_guards :589, test_model_config_enforced :124) do not reach scripts/. compare_runs.py must read `current_openai_ledger()` and never `_LEDGER`.

## 7. Questions for the orchestrator

1. B1: approve the E-row on the 043 fence file (restrict the two mutant rows to user tables), and drop that file from the 4.2 "unedited" list?
2. B2: which pending-batch rule: cancel-on-timeout, a durable pending record resumed next run, or a G2 `--resume`?
3. B3: skip runs that already have a haiku judgement row (recommended), or add an attempt marker?
4. K1: make ENABLE_COMPARISON_ID_ECHO ON a precondition for any kb_feedback writer, or have S81-12 record the 365-day TTL alone (not "deleted with the account")?
5. K2: accept the judge sharing the live escalation lane's daily cap (state it), or set a judge sub-budget inside the lane?
6. K3: drop the verdict prose from the snapshot when the body is personalised?
7. C5: field-level "producing model" (verdict / critic roles only), or any call?
8. R6: data_coverage smallint (measured int 0..4) against the ruling's text. Rule.
9. C7: per-run or per-Riyadh-day escalation count cap?
10. R5: pass the camera vision records into record_compare_run (a 6th keyword), or state the camera / URL llm_calls limits?
11. R2: fence the evidence inside `<SEARCH_RESULTS>` (the existing sanitizer), or a script-local `<EVIDENCE>` neutraliser?
12. C3: is 050 applied an explicit precondition for ENABLE_BATCH_JUDGE=apply?
