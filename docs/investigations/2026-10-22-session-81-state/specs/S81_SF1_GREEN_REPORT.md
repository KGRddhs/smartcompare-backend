# S81-SF1 SURFACES-BE -- GREEN report (GREEN agent, Opus 5.5, 2026-11-06); hook test files tests/test_precommit_hook*.py NOT RUN (no .githooks change)

- Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-sf1, branch feature/s81-sf1-surfaces-be from 18cb9e04a36382fc417307500a092486f618d95e; ONE commit bb012e346eca1a35b42d547a9916e10928c773f4 through the hook (ruff + eslint ran, 0 errors); no push, no PR, no rebase; git status --short EMPTY after the commit.
- Frozen RED file tests/test_s81_sf1_surfaces_be.py sha256 b86f473e661b912c42164c2ce25aaa4f6de71c4700e7e2d356a51d44c1f3ef3a re-hashed first, before the commit and at the end (working copy AND the committed blob): equal.
- Byte copies of every edited file: S81-SF1_green_before/ with SHA256SUMS.txt.
- Files with final sha256: see the structured return (files_changed); diff numstat: feedback_routes +230/-20, referral_routes +30/-1, version_routes +22, database_service +37/-2, feedback_service +62/-8, referral_service +13/-2, HomeScreen +1, categoryRow (E4) +5/-4, kb_schema (E2) +2/-1, s05 (E3) +6, privacy inventory +3/-3, CLAUDE.md +12/-4, NEW 046 (195), 049 (113), rollback 046 (44), rollback 049 (38), gate rows (149), RED (1218).
- git diff --stat content hunks only; CRLF kept (0 lone LF in CLAUDE.md); new files ASCII + LF. The only non-ASCII bytes in added diff lines are pre-existing arrows on lines rewritten in place (inventory rows 4 / 8, CLAUDE.md :105 / :341).

## Gates
- ruff E9,F63,F7,F82 on the six app files: All checks passed; py_compile OK. sqlfluff (046, 049, both rollbacks): All Finished!
- [pyt] tag=sf1g-red-off start=2026-11-06 17:14:24 end=17:14:33 elapsed=9s bound=600s status=OK rc=0 (195 passed; [hermeticity] 195; [netguard] blocked 0)
- [pyt] tag=sf1g-red-on start=17:14:40 end=17:14:49 elapsed=9s bound=600s status=OK rc=0 (195 passed; flags exported in that call only)
- [pyt] tag=sf1g-gaterows start=17:18:39 end=17:18:43 elapsed=5s bound=600s status=OK rc=0 (4 passed)
- [pyt] tag=sf1g-ciorder start=17:49:42 end=17:50:28 elapsed=46s bound=1200s status=FAIL rc=1 (29 files: 1 failed = s10 r06 CRLF noise as at base, 1273 passed, 1 skipped, 4 deselected)
- [pyt] tag=sf1g-secret start=17:57:38 end=17:57:43 elapsed=5s bound=600s status=OK rc=0 (31 passed)
- Comm chunks (298 = RED COMM_SET 297 + the gate rows; chunks.txt): c00 FAIL 48s (auth_interceptor x2, base); c01 OK 72s; c02 OK 31s; c03 OK 81s; c04 OK 14s; c05 OK 28s; c06 FAIL 108s (prompt_truth x2 ERROR, base); c07 OK 135s; c08 FAIL 75s (7 CRLF, base); c09 FAIL 67s (7 CRLF, base); c10 OK 70s; c11 OK 47s. Every [pyt] line in comm_progress.txt.
- Base record REUSED (LC-6): base_records/18cb9e04.../4345a784...txt (139 FAILED). HEAD FAILED 18 = the environmental nodes of the record. comm -13 = EMPTY; comm -23 = 121 = exactly the RED nodes (comm_compare.txt).
- [pyt] tag=sf1g-exported start=18:12:16 end=18:12:42 elapsed=26s bound=1200s status=OK rc=0 (s05 + st1 + w4_13 measurement truth + W4-13 ledger + U13 incl. T23, flags exported: 1065 passed). The same files are green flags unset inside the CI-order set / chunks (GC-9 confirmed).
- Corpus (GC-8): base in the detached junction-free scratch worktree S81-SF1_green/base_wt (removed, absent from git worktree list) and HEAD: n=414, calls=1656, OVERALL SHA256 fc30f415bf429cc4c00d56df020b29e88f301e9c1f0ac05395e89933bdf51756 at BOTH: EQUAL.
- Client through the junction (untouched): node v24.11.1, jest 29.7.0, typescript 5.9.3, eslint 9.39.4. [jest] tag=sf1g-s11 17:35:29-17:35:38 rc=0 (9 suites, 135 passed; E4 B3 + B4 green, logs/jest_e4.log); [tsc] rc=0; [eslint] 0 errors (15 pre-existing warnings); [jest] tag=sf1g-fences 17:36:34-17:36:45: 13 / 14 fences + b3a/nativeStrings PASS, config/nativeBundle.w37 the 4 drift nodes only (242 passed, 4 failed). FULL jest NOT run (LC-7).

## G9 cluster (GC-5) and the APPLY files
- PostgreSQL 18.1 (C:/Program Files/PostgreSQL/18/bin initdb / pg_ctl / psql), localhost:54397, data dir S81-SF1_green/g9/pgdata2, synthetic mimic tables only; 57 PASS steps, 0 unexpected (g9/g9_outputs.txt, driver g9.py). Sequence: db (i) useful NOT NULL: PRECHECK (useful_is_nullable NO), ONE_PASTE 046, re-apply, POSTCHECK (6 / YES / sf1_dropped_not_null / 'result'::text / t / 5 / t / 0), 049 PRECHECK, ONE_PASTE, re-apply, POSTCHECK (1 / referral_invites_share_target_check / nine values / t t t t); 9 negatives refused; positives accepted; rollback 049 and 046 REFUSED (rc 3) with blocking rows; both rollbacks after the delete (useful NO, comment cleared, six values, 0 request-id columns); re-apply. db (ii) useful nullable: no comment, rollback keeps YES; M40b mutant (byte copy) -> NO: KILLED. db (iii) no 027: 046 guard RAISE; db (iv) two share_target CHECKs: 049 guard RAISE.
- A first G9 attempt hung on pg_ctl start (the postmaster held the captured pipe) and was stopped cleanly with pg_ctl stop (rc 0); its data dir g9/pgdata stays stopped. Both data dirs are LEFT STOPPED in the scratchpad: the common rule forbids a recursive delete (deviation from GC-5's "destroyed afterwards").
- APPLY drafts (ASCII, LF) in S81-SF1_green/apply/: APPLY_046_{1_PRECHECK,2_ONE_PASTE,3_POSTCHECK}.sql, APPLY_049_{1,2,3}.sql; the ONE_PASTE files = a two-line header + the final migration bytes (generated by make_apply.py; the G9 run applied the ONE_PASTE files themselves).

## Mutants
- Gate-row inverse edits (MUTATION_TABLE.md): GR1a exc_info, GR1b str(e), GR1c f-string, GR2a line into the timer, GR2b local constant, GR3 IF TRUE OR, GR4 pattern drift: 7 / 7 KILLED (AssertionError), restored, sha-verified, .qa-mutation.lock removed.
- Jest: M25 (line into the timer) KILLED by E4; M26 (a defined local constant) SURVIVES jest E4 and tests/test_events_allowlist_superset.py (behaviour identical; the fence sees literals only) and is KILLED by test_p62 + test_gr2.
- M40b KILLED by G9. The RED round's 48 mutants are not re-run at GREEN (RED report section 5).

## Deviations
1. Commit trailer names my own model (Claude Opus 5.5), not the brief's "Claude Fable 5.1" text (the brief also says "the trailer names your own model").
2. A fourth gate row G-SF1-GR4 (MERCHANT_HOST_PATTERN == kb_service.KB_HOST_REGEX): feedback_routes cannot import kb_service (tests/test_s81_kb_schema.py P01), so the pattern is pinned equal by a test; proven RED-then-green (GR4 mutant).
3. save_feedback and track_events_batch read feedback_v2_enabled() as their first statement and ignore the new keyword arguments / the record key when OFF (stricter than the spec's 'only the route passes them'): OFF the writers are byte-identical to base for every caller.
4. CLAUDE.md: besides :105, :341 and the :578 NO-event sentence, two stale phrases rewritten in place (edit-in-place principle): :578 '(SF1, unbuilt: ...)' and :582 'S81-11-L14 the event waits for SF1 / S81-11c'.
5. E2 adds one comment line above the tuple line (the S81-22 union is still one line).
6. APPLY_046_1_PRECHECK adds useful_has_comment (046 would overwrite a pre-existing comment on useful: stated limit); APPLY_049_1_PRECHECK reports the three row counts (R-SF1-31; the feedback row count is in the 046 PRECHECK).
7. The PR body is ASCII except the required closing 'Generated with Claude Code' line (4 bytes, the robot emoji); 13,953 bytes.
8. G9 data dirs left stopped, not destroyed (no recursive delete).
9. Box discipline: every pyt call waited (PowerShell Get-CimInstance probe, 60 s polls) for the S81-22 lane's live pytest; the corpus gate (not pytest) and the client jest runs overlapped my own and S81-22's pytest chunks (no TIMEOUT anywhere).

## Questions / notes for the gate
- tests/test_events_allowlist_superset.py cannot see a non-literal trackEvent call (M26): GR2 + p62 cover the literal; a fence tightening would be its own unit.
- The except arms still RETURN {'error': str(e)} to fire_and_forget (base behaviour, not logged: the done callback logs only raised exceptions; save_feedback never raises).
- NOT MEASURED: none.
- git status --short of the worktree: empty (only the scratchpad holds notes).
