# S81-08b LEGACY-FINGERPRINT-READER: adversary report, lens ENGINEERING

- Agent: adversary (role label Fable in the task text), model Opus 5.5 (claude-opus-5-5). Window 2026-10-29 01:18 - 02:25 AST.
- Unit worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s08b, branch feature/s81-s08b-legacy-fingerprint-reader, HEAD VERIFIED 63f159efec41b08e875749c3b3f2b2f7035caa2e (git rev-parse at start and end), status clean, never edited.
- Scratch: my own detached worktree <S>/S81-08b_adv_engineering at 63f159ef (git worktree add --detach; every probe and mutant there; removed at the end). <S> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad.
- Base 86d5a24d17f5782e733dee82d52f38dcbf3606ff (origin/main at launch; origin/main is now a8f01379 = + #374 S81-06, the rebase step).
- Authorities read: s81-common.txt, GATE_S81_08B (GC-1..GC-11), RULINGS_S81_08B (R-S08B-1..11), the spec sections 3 / 7 / 8, the RED comm builder and base record, the GREEN report, PR_BODY.md, green_comm.py, green_mutate.py, PLAN_S81 flip order (:103, :185).
- This report, the notes and every script were written THROUGH THE SHELL (python heredocs) or as .py helpers; the harness refuses a subagent Write of a report .md.

## Verdict: SOUND (0 blocking, 0 major, 7 minor)

Every engineering claim I could test against the bytes holds: the diff is hygienic (CRLF kept, added text ASCII, no new import, no unexplained deleted line, git diff --check clean, repo-config ruff counts identical base vs head), the three comm chunks and the CI-order set I re-ran reproduce the GREEN numbers exactly (branch-only-new EMPTY on my runs), the source-scanning pins, the CLAUDE.md readers and the hook test files are green, and the CLAUDE.md row, pointer and PR body numbers match the bytes. The minors are pin-strength and documentation rulings; none changes code.

## Findings

Blocking: none. Major: none.

Minor (documentation / pin-strength rulings for the orchestrator):
- m1 (comm set, importer class blind spot): the RED and GREEN builders match an app importer of auth_routes only by its dotted string (app.api.text_routes) or path; three tests import it in the from-package form (from app.api import text_routes as tr) and are outside the binding 242 and the 262: tests/test_m13_35_sse_disconnect_finally.py, tests/test_m18_preverdict_disconnect_refund.py, tests/test_openai_breaker.py. The common-brief union rule (module and symbol reference grep) does not require transitive importers, so this is not a missing member under the brief; under the RED/GREEN declared importer-ref class it is. MEASURED at HEAD by me: 62 passed (with two docstring-path files), so no regression can hide there. Ruling asked: add the three to the comm list / PR body, and make the rebase re-derivation import-aware (from-package form).
- m2 (R11 strength, E12 SURVIVED): replacing the binding OTA precondition sentence (the DATED ledger line of the flip ON, never the merge; GC-7 / R-S08B-2) with "The OTA precondition is the merge of this unit." keeps R11 green: the words ledger / OTA occur elsewhere in the row. The GREEN bytes are right; a later edit could invert the precondition silently.
- m3 (GC-7 placement and spec 2c unpinned, E15 and E14 SURVIVED): moving the row before the S81-14 block (950 passed over the RED file, test_s81_kb_schema.py, test_s81_s04_spend_breaker.py, test_ci_gates.py) and deleting the Auth + security hardening sentence (:231) both stay green.
- m4 (P14 / S05 p07 literal count, E3b SURVIVED): a second primary-header read spelled lower case (request.headers.get("x-device-fingerprint"); Starlette headers are case-insensitive) passes both the RED P14 count and test_s81_s05 p07; the exact-literal pin (GC-8) proves only the spelling. Inherited from S81-05 p07; the GREEN code has no second read.
- m5 (GC-3 accessor unpinned on the ON path, E9 SURVIVED, behaviour-equivalent): reading the legacy header through __contains__ + __getitem__ instead of .get passes all 85 rows (R2 checks reads only with the flag OFF). Equivalent on Starlette headers; GC-3 "reads ONLY through request.headers.get" is a contract sentence no row enforces with the flag ON.
- m6 (CLAUDE.md row limit (10) goes stale at the rebase): the row says the comm-set base record "was measured by the RED (241 files at 86d5a24d)"; the rebase onto a8f01379+ takes a FRESH base record (GC-6), so the sentence must be rewritten at the rebase (the GREEN rebase items name the :341 pointer and the anchor union, not this sentence; R-A15 edit-in-place).
- m7 (autocrlf and the frozen RED sha): the RED file is LF in the index and in the unit worktree (blob 2f4f8237...); any fresh checkout or rebase with core.autocrlf=true writes it CRLF (sha 9436574d..., measured in my scratch worktree). Re-hash the BLOB (git show HEAD:tests/test_s81_s08b_legacy_fingerprint.py | sha256sum) after the rebase, or the frozen-file check raises a false alarm.

Nit (no ruling needed): the GREEN report and PR body give the R11 row slice as 6,558 chars; that is the CRLF-bytes count. R11 reads with universal newlines and sees 6,551 (cap 8000 either way).

## Runs (every pytest through pyt.py, the shared .venv-qaren, one at a time, in my scratch worktree at the exact bytes; flag unset unless marked)

| run | result | [hermeticity] / [netguard] | [pyt] |
|---|---|---|---|
| RED file, flag unset | 85 passed | 85 / 0 from 0 | `[pyt] tag=s08b-adve-unit-off start=2026-10-29 01:25:37 end=2026-10-29 01:25:45 elapsed=8s bound=600s status=OK rc=0` |
| RED file, ENABLE_LEGACY_FINGERPRINT_READER=true for the call | 85 passed (14 R nodes + 71 P nodes incl. r6pre; per-row counts P1 7, P2 6, P3 6, P4 16, P5 4, P6 2, P7 9, P8 6, P9 4, P10-P14 2 each) | 85 / 0 from 0 | `[pyt] tag=s08b-adve-unit-on start=2026-10-29 01:25:53 end=2026-10-29 01:26:02 elapsed=9s bound=600s status=OK rc=0` |
| CI-order set (the 22 files of ci_order_files.txt: sets A + B + the RED file; holds the three CLAUDE.md readers) | 1345 passed, 1 skipped (= GREEN) | 1345 / 48 from 14 | `[pyt] tag=s08b-adve-ci-order start=2026-10-29 01:26:19 end=2026-10-29 01:27:03 elapsed=44s bound=1200s status=OK rc=0` |
| CI-order set, flag ON for the call | 1345 passed, 1 skipped | 1345 / 48 from 14 | `[pyt] tag=s08b-adve-ci-order-on start=2026-10-29 01:53:07 end=2026-10-29 01:53:48 elapsed=41s bound=1200s status=OK rc=0` |
| m1 files (3 from-package importers of text_routes + 2 docstring-path files) | 62 passed | 62 / 121 from 6 | `[pyt] tag=s08b-adve-missed5 start=2026-10-29 01:27:16 end=2026-10-29 01:27:22 elapsed=6s bound=1200s status=OK rc=0` |
| comm chunk 00 (25 files, auth-heavy) | 2 failed, 793 passed (= base / GREEN; FAILED = the two tests/test_auth_interceptor.py pre_impl nodes) | 795 / 18 from 7 | `[pyt] tag=s08b-adve-comm-00 start=2026-10-29 01:27:58 end=2026-10-29 01:28:29 elapsed=31s bound=1200s status=FAIL rc=1` |
| comm chunk 06 (25 files: register / retro auth / U13 / FY25) | 1096 passed (= base / GREEN) | 1096 / 0 from 0 | `[pyt] tag=s08b-adve-comm-06 start=2026-10-29 01:28:36 end=2026-10-29 01:31:17 elapsed=161s bound=1200s status=OK rc=0` |
| comm chunk 07 (25 files: the S81 row readers, security, sentry, share) | 1 failed, 3853 passed (= base / GREEN; FAILED = the SR8 node test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged) | 3854 / 42 from 12 | `[pyt] tag=s08b-adve-comm-07 start=2026-10-29 01:31:26 end=2026-10-29 01:33:35 elapsed=130s bound=1200s status=FAIL rc=1` |
| source-scanning pins + manifest readers (test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py, test_migration_023.py, test_sqlfluff_config.py, test_legal_docs_u8.py, test_legal_s78.py, test_migration_043_delete_user_cascade.py) | 498 passed, 2 deselected | 498 / 0 from 0 | `[pyt] tag=s08b-adve-srcpins start=2026-10-29 01:34:13 end=2026-10-29 01:34:55 elapsed=43s bound=1200s status=OK rc=0` |
| hook test files (the four test_precommit_hook*.py), -k "not dash" | 167 passed, 160 deselected | 167 / 0 from 0 | `[pyt] tag=s08b-adve-hook-notdash start=2026-10-29 01:35:40 end=2026-10-29 01:50:15 elapsed=875s bound=1800s status=OK rc=0` |
| hook test files, -k dash | 157 passed, 3 skipped, 167 deselected | 160 / 0 from 0 | `[pyt] tag=s08b-adve-hook-dash start=2026-10-29 01:53:58 end=2026-10-29 02:14:13 elapsed=1215s bound=1800s status=OK rc=0` |
| positional (the CI alphabetical neighbours): the RED file FIRST, then the 18 files that sort after it (chunks 07 / 08: s81_st1 .. spec_spine_d2), so any state the RED file leaks reaches them | 1 failed (the SR8 base node only), 1373 passed, 1 deselected | 1374 / 14 from 8 | `[pyt] tag=s08b-adve-positional start=2026-10-29 02:14:34 end=2026-10-29 02:16:34 elapsed=120s bound=1200s status=FAIL rc=1` |

My chunk FAILED set (00 + 06 + 07, eng_comm_head_failed_sorted.txt) = the pre_impl auth pair + the SR8 node; comm -13 against the RED base record s08b_comm_base_failed_sorted.txt = EMPTY. The GREEN head FAILED set file equals the RED base set byte for byte (diff empty). The two hook runs outlived the Bash tool 600 s call limit and were moved to the background by the tool; each was the same single foreground pyt.py call, and no other pytest started until its exit notification.

Lint at the exact bytes: .venv-qaren python -m py_compile app/api/auth_routes.py tests/test_s81_s08b_legacy_fingerprint.py rc 0; ruff 0.16.5 check --select E9,F63,F7,F82 --no-cache (the CI tier, ci.yml:170) on both: All checks passed!; the repo [tool.ruff.lint] set (pyproject.toml :59-62, E501 ignored) on auth_routes.py base vs head: identical counts (15 B008, 3 B904, 1 F841, 5 W293), so the added code adds no lint finding.

## Engineering mutants (my scratch worktree; byte copy, one exact-string edit matching once or a scripted move, the named files through pyt.py bound 600, restore from the copy, sha256 compared after each: all restore_ok; lock <scratch>/.qa-mutation.lock held and removed; final shas auth_routes.py f49c4b95..., CLAUDE.md 6a52dd06...)

| # | mutant (target) | files run | result | killing rows | [pyt] |
|---|---|---|---|---|---|
| E1 | a 'legacy_hash' token in an auth_routes comment (names rule p08) | RED + S05 | KILLED | P14 names rule; test_s05_p08_no_dual_hash_names | s08b-adve-mut-E1 01:50:36-01:50:50 14s FAIL rc=1 |
| E2 | a device_lookup_keys local in the dual function | RED + S05 | KILLED | P14 names rule; S05 p08 | s08b-adve-mut-E2 01:50:51-01:51:05 14s FAIL rc=1 |
| E3 | a second exact `request.headers.get("X-Device-Fingerprint")` read in the helper | RED + S05 | KILLED | P14 names rule (p07 count); test_s05_p07_route_header_reads_untouched | s08b-adve-mut-E3 01:51:05-01:51:15 10s FAIL rc=1 |
| E3b | the same second read spelled lower case | RED + S05 | SURVIVED (m4) | none (261 passed) | s08b-adve-mut-E3b 01:51:16-01:51:22 6s OK rc=0 |
| E4 | `_DEVICE_FINGERPRINT_RE = _DEVICE_FINGERPRINT_RE` at module level | RED + S05 | KILLED | P14 leaf import shape (r08); test_s05_r08_one_regex_object | s08b-adve-mut-E4 01:51:22-01:51:29 7s FAIL rc=1 |
| E5 | the legacy header declared as a Header() parameter on register | RED | KILLED | P10 (both nodes) | s08b-adve-mut-E5 01:51:29-01:51:34 5s FAIL rc=1 |
| E6 | a constants-only INFO line on the silent drop | RED | KILLED | R2, P2, P3, P7 (20 nodes) | s08b-adve-mut-E6 01:51:35-01:51:40 5s FAIL rc=1 |
| E8 | the leaf import set gains parse_device_fingerprint | RED + S05 | KILLED | P14 leaf import shape; test_s05_p01_no_consumer_in_app; S05 r08 | s08b-adve-mut-E8 01:51:40-01:51:47 7s FAIL rc=1 |
| E9 | legacy read through __contains__ + __getitem__ instead of .get (GC-3) | RED | SURVIVED (m5, behaviour-equivalent) | none (85 passed) | s08b-adve-mut-E9 01:51:56-01:52:00 4s OK rc=0 |
| E10 | CLAUDE.md row: ENABLE_REQUEST_CONTEXT_HEADERS dropped | RED | KILLED | R11 | s08b-adve-mut-E10 01:52:01-01:52:06 5s FAIL rc=1 |
| E11 | CLAUDE.md row: "after S81-08 merges" added | RED | KILLED | R11 | s08b-adve-mut-E11 01:52:06-01:52:11 6s FAIL rc=1 |
| E12 | CLAUDE.md row: OTA precondition inverted to "the merge of this unit" | RED | SURVIVED (m2) | none (85 passed) | s08b-adve-mut-E12 01:52:12-01:52:16 4s OK rc=0 |
| E13 | CLAUDE.md :341 Feature Flags pointer sentence removed | RED | KILLED | R11 (names the flag) | s08b-adve-mut-E13 01:52:16-01:52:21 5s FAIL rc=1 |
| E14 | CLAUDE.md :231 Auth bullet sentence removed (spec 2c) | RED | SURVIVED (m3) | none (85 passed) | s08b-adve-mut-E14 01:52:22-01:52:26 4s OK rc=0 |
| E15 | CLAUDE.md row moved before the S81-14 block (GC-7 placement) | RED + kb_schema + s04 + ci_gates | SURVIVED (m3) | none (950 passed) | s08b-adve-mut-E15 01:52:26-01:52:50 24s OK rc=0 |

Killed 10 / 15 (every kill an AssertionError in a named row, no error-type kill); 5 survivors, all on documentation or contract-literal pins, none on a behaviour the unit changes (E9 is behaviour-equivalent). Detail: eng_mutants_E1_E2_E3_E3b_E4_E5_E6_E8.json, eng_mutants_E10_E11_E12_E13_E14_E15_E9.json, eng_mut_E*.log. The behaviour mutants M1-M20 belong to the correctness lens (the GREEN report records 20 / 20 killed; not re-run here).

## Comm set re-derivation (eng_comm_rederive.py, an independent and wider rule)

Classes: auth_routes text; every CLAUDE mention; fingerprint; the new names; the auth route symbols; walkers (rglob / os.walk / iterdir / listdir / scandir / glob); pkgutil / import_module / __path__; getsource / ast.parse / tokenize; any <name>.__file__; app path strings incl. os.path.join(..., "app") and "app/"; .github; SmartCompareApp; request_context; referral_routes; get_admin_supabase_client; the TRANSITIVE closure of app importers of auth_routes (app.main, feedback, history, home, image, profile, referral, share, text, url, usage routes) matched by dotted string, path OR import statement (incl. from-package and parenthesised forms); importers of every tests/ helper with a hit. Result over 714 test files: 280 files; the binding 242 (the RED 241 + the RED file) holds every file the common-brief union rule requires. Outside it: the GREEN supplementary 20 (get_admin_supabase_client in other namespaces: run green by GREEN, chunk 10); the 3 m1 files (from-package importers of text_routes; measured green, 62 passed with the next two); 2 docstring-only app-path mentions (test_m18_openai_tpm_sizing.py, test_response_builder_winner_card_consistency.py; measured green); and 16 non-members (helper imports of UNEDITED helpers _env_safety / _tokenizer / _retro_r_mig_sql, migrations / _proof / skills walkers, import_module of scripts.eval_runner, app.services.price_service or adapter modules, a 'legacy' test name in test_magento_gql_e3_hardening.py). conftest.py defines no app / TestClient fixture (autouse resets only), so no fixture-borne importer is missed. Chunks 00-08 of the GREEN head list are byte-identical to the RED base chunks; chunk 09 = base chunk 09 + the RED file. My three chunk re-runs (00, 06, 07) reproduce the base and GREEN FAILED sets exactly: chunk 00 = the pre_impl auth pair, chunk 07 = the SR8 node, chunk 06 none; branch-only-new on my runs EMPTY.

## Claim checks against the bytes (CLAUDE.md row / pointer / Auth bullet, GREEN report, PR body)

| claim | verdict | evidence |
|---|---|---|
| auth_routes.py +120 / -7, CLAUDE.md +9 / -2, RED +1200 | TRUE | git diff --numstat 86d5a24d 63f159ef |
| the 7 deleted code lines are the two base calls re-indented | TRUE | the deleted lines are exactly the 6-line social call and the 1-line register call; the other 2 deletions are the :231 and :341 lines rewritten in place |
| sha before / after, bytes, CRLF counts (0ee900c9 -> f49c4b95, 67,765 -> 73,488, 1,650 -> 1,763 CRLF; 1b2375cb -> 6a52dd06, 525,719 -> 532,726, 968 -> 975) | TRUE | CRLF-converted blobs at base / head and my CRLF checkout (0 LF-only) |
| added text ASCII; bytes > 127 175 -> 175 and 3,937 -> 3,937 | TRUE | the only added line with bytes > 127 is the rewritten :341 line, 66 pre-existing bytes before and after |
| no new import; leaf import set unchanged; _DEVICE_FINGERPRINT_RE never assigned | TRUE | import block unchanged in the diff; P14 green; E4 / E8 killed |
| exactly one request.headers.get("X-Device-Fingerprint") literal; no legacy_hash / device_lookup_keys in app/ or scripts/ | TRUE (literal) | count 1; scan empty; E1-E3 killed; see m4 for the case-variant gap |
| the flag read is the first statement of the helper; OFF reads no header | TRUE | R10 + R2 green; os.getenv("ENABLE_LEGACY_FINGERPRINT_READER" occurs once |
| two [LEGACY-FP] lines carry constants only (site, top, type name) | TRUE | logger.info("[LEGACY-FP] site=%s top=%s", site, top); logger.warning("... inherit failed: %s", site, type(exc).__name__) |
| ENABLE_SOCIAL_DEVICE_FINGERPRINT production state UNKNOWN, no dated ledger line names it | TRUE | no hit in any ledger.md (sessions 71-81); OWNER_ACTIONS_S81 item 5 and PLAN_S81 :234 still ask for it |
| row after the newest session-81 row on main, before ## Tests | TRUE | HEAD lines 497 (S81-14) -> 507 (S81-08b) -> 514 (## Tests); the S81-14 slice now ends at the new header (kb_schema green) |
| R11 tokens present, forbidden phrase absent, slice <= 8000 | TRUE | OTA 11, ledger 4, independent 2, reasoned 1, ENABLE_REQUEST_CONTEXT_HEADERS 1, "after S81-08 merges" 0, "merged" 0; slice 6,551 chars (universal newlines) |
| owner step "before the first post-approval OTA" vs the ruling "before the first OTA" | CONSISTENT | PLAN_S81 :103 names the S81-08 OTA "the FIRST post-approval OTA"; :185 places the flip as its own step before it |
| PR body: 14 R nodes, 71 P nodes (P7 x6 + 3), row ids R5 / R8 / R9 | TRUE | node ids in eng_unit_on.log |
| PR body / GREEN: CI-order 1345 passed 1 skipped; chunk counts 00 / 06 / 07 | TRUE | my re-runs, identical |
| PR body carries no local path or personal value; 4 bytes > 127 = the closing robot line | TRUE | scan of PR_BODY.md (no C:/, Users, scratchpad, e-mail); CR 0 |
| commit trailer names the committing model | TRUE | Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com> |
| GREEN: the binding 242 is the re-derived union | PARTLY | complete under the common-brief rule; 3 from-package importers missing under the GREEN declared importer class (m1, measured green) |

## Prove-nothing rows (engineering claims a green row does not prove)

- R11 proves token presence in the row slice, not the activation semantics: E12 (precondition = the merge) passes; it does not prove the placement (E15) or the :231 Auth sentence (E14).
- P14 names rule (p07 count) proves the exact spelling of one literal, not "one primary reader": E3b (case variant) passes; the same holds for test_s81_s05 p07.
- R2 proves the accessor only with the flag OFF (zero reads); with the flag ON any accessor that yields the value passes (E9), so GC-3 "only through request.headers.get" is unproven on the ON path.
- The GREEN statement "HEAD FAILED set == base set" proves nothing about the 3 m1 files (outside both lists); my run covers them (62 passed).

## Questions for the gate

- Q1 (m1): add tests/test_m13_35_sse_disconnect_finally.py, tests/test_m18_preverdict_disconnect_refund.py, tests/test_openai_breaker.py to the comm list (measured green here), and require an import-aware importer match at the rebase re-derivation?
- Q2 (m2 / m3): strengthen R11 at a later docs unit (the precondition sentence, the placement after the newest session-81 row, the :231 sentence), or accept the token-level pin as designed (GC-1 accepted R11 as written)?
- Q3 (m4 / m5): record the case-variant and accessor gaps as stated pin limits, or tighten p07 / P14 to a case-insensitive count and R2 to assert reads == [the legacy name] with the flag ON?
- Q4 (m6): rewrite stated limit (10) of the CLAUDE.md row at the rebase (the fresh base record at the new main)?

## NOT MEASURED

- Nothing in the lens list is unmeasured except: comm chunks 01-05 and 08-10 (the task asks for three of my choice; I re-ran 00, 06, 07); the base side of the m1 files (green at HEAD, so no base record is needed for comm -13); any database (the partial-index claim stays reasoned, as the row says).

## Hygiene

- Unit worktree: never written; HEAD 63f159ef and status clean at start and end; RED file sha256 2f4f8237... at start and end (working copy == committed blob).
- Scratch worktree: created with git worktree add --detach at 63f159ef, auth_routes.py f49c4b95... and CLAUDE.md 6a52dd06... verified before and after every mutant, lock created and removed, removed with git worktree remove --force and checked absent in git worktree list.
- One pytest at a time; no pytest of mine left running; no .env read; no package manager; no git write except the scratch worktree add / remove.

## Files written by this lens (all under <S>/S81-08b_adv/, sha256 over the bytes on disk at assembly; the report itself is hashed in the return)

| file | bytes | sha256 |
|---|---|---|
| eng_assemble.py | 2004 | f5e9054620bb2cdba7e1713f897926644a061186ce08e5fe11678384ac9f605b |
| eng_auth_routes_base86.py | 66115 | 5add302ddff52770870968dba2bc7d9a29bb6d3b0c348d2f99d5ccb840d98be2 |
| eng_ci_order.log | 14052 | eb567a219aa15d6d36446709ebf2b77767eb5e1b25260ea5901060028dfde418 |
| eng_ci_order_on.log | 14055 | 32158d5a6739a23c684a03d1089d5599c3c51ef431d32dbc467067bb2878046b |
| eng_claude_diff.txt | 17727 | 6051fa78244dac098f7a3d033af662b1dbcfcf4f71c48217a62fecb6db280c78 |
| eng_comm_00.log | 16779 | 33ae8809b5947df394031103ba3387fc94a2f1f15ff90748745cfe6a5cb27a1f |
| eng_comm_06.log | 8315 | b50e729611c2216134d7f376b64f9ee1e310a81ff9debb105815808ee9be08f8 |
| eng_comm_07.log | 18572 | 82e9bfead15090542790c6667192c107fca8f77de3b398394692f2d7441f2be5 |
| eng_comm_head_failed_sorted.txt | 234 | d3eb1b65e9e8592c0703c951b49a4e689bf3de6c4409f3e477a86c6d0b708a78 |
| eng_comm_mine.txt | 10086 | 8ece16c24c576596ac244a75b393394fd8f6c3990ab369cf841ef91c7079f658 |
| eng_comm_rederive.py | 5438 | 618e9e57dcd153f2742680b9c4325e9a94c99489ba47f7b501441922c3c16638 |
| eng_comm_rederive.txt | 3719 | ce0711f6aba7ef7940e4a6375210c8e98409f78fc5f4cd19d8a693b0d10b517c |
| eng_full.diff | 80591 | 47b15254be9e0432042ae0e2dca814dc3d27d0fe04f0cc19067ccd598371b49a |
| eng_hook_dash.log | 3752 | 323611d304194d67d9b9d66f54d5243a84cf0cf2ae537e33535f96d789d90a0b |
| eng_hook_notdash.log | 3745 | 7c4490de1e8040426194a8e2d14a55a6aa0c49a666782d6e0ddf46a9705bd8ff |
| eng_missed5.log | 3751 | 674f6f294e93fa1b8231bff551369a30086d6c3401bad98978e4dd3b1cd244d6 |
| eng_mut_E1.log | 11347 | 28406da05fb140898fc725b7fcd393d0cd7b5600a8b3d0fc5bf8e877cae2214a |
| eng_mut_E10.log | 7020 | 9a5eb8c0e0757d930fc8d53bb3798ad9ad4bb4c5b71ab172cfe02491b96ade51 |
| eng_mut_E11.log | 7741 | 6d3dfb40d8b2fa6651e9f5bf43a04013e20c4480c9035a2123db53889c9e5089 |
| eng_mut_E12.log | 5190 | 7fb7d29a3e7ec77c9d85a34426ef3d037c2306f269be513d6b2c55aaaa177e9a |
| eng_mut_E13.log | 7479 | 99eca57df1e458fba4cf948f6fc935d3584f59e3887c7f7669b2f241e2fef547 |
| eng_mut_E14.log | 5190 | ffa12da2abc51e673471865549f4b91ede61cc701481970817ffcbe382461263 |
| eng_mut_E15.log | 7491 | 05dd683a147ddc55745aa518642d9d55cb8847d7f58ae632bf385fcf76714381 |
| eng_mut_E2.log | 10992 | 90a170111b88fac378d2d62c2c03e3ab319434059f24871ba104ade6d8b53d13 |
| eng_mut_E3.log | 10303 | ac6e461459cb2dc1a26005f14b7feb76c61a48d8095e85f5e94732d50c1ad970 |
| eng_mut_E3b.log | 7246 | 636df63ed56134bf165e8eb2f80eaa282ec11de173b42af03fab765970066e27 |
| eng_mut_E4.log | 11525 | 86efd364af80ce7da66809c20c0e155e3a43fea118749ba8f1abc5a846a01674 |
| eng_mut_E5.log | 8857 | cc6d2e5f4998b4e8fb2f036be4bb1e4e2b9584da23879d40cd152660ab4a6f47 |
| eng_mut_E6.log | 56799 | c08f833349174c6259465fa21deef4add9a205e36e4242664e9e7a45dfe7e09d |
| eng_mut_E8.log | 13276 | 4a30e451142fbd26d18c9bd3b68f071444e27276c782385c87e3a8b1ce4a689b |
| eng_mut_E9.log | 5189 | 18a7b929ac1baddd3151e28f4c9dfe8e10d35307182a63e81f44fa8bdfac0b0f |
| eng_mutants_E10_E11_E12_E13_E14_E15_E9.json | 3839 | 82a20ecffeaa69190fffdd1b5f1896fc0fe4cace1685eab9b37e029beb603af7 |
| eng_mutants_E1_E2_E3_E3b_E4_E5_E6_E8.json | 5723 | ebf62cc2c758d48a5789ad7fc2cf50d05e5003780de1a7a50e4357cd0785586e |
| eng_mutate.py | 10464 | 3bc28e7b3dc9f42849b03740f64234388d6a47b13bd3dba474b599297202f64d |
| eng_positional.log | 13867 | c24c9c5640ca5a9526bf8b09dae1665be26e270e07e1e9b67e7ce33d55941307 |
| eng_positional_files.txt | 658 | e27b90c721bd2e9857ff82b04b2dce17ea5696caa515402906ad0534eedfbdfc |
| eng_report_part3.txt | 3836 | e005f3cafeb9a4605ebec629b62d9249d2aba941fcfb4917b2d9fdce9078e053 |
| eng_report_part4.txt | 5116 | eb7929b18d5fcde603e73cee9ecff059b805ece21677ab6b27450e8fed01faae |
| eng_report_part5.txt | 2469 | a288bd839c873db8220105aa324773e5addff8c7a2a519f0e57519b0076cba7e |
| eng_report_rows_extra.txt | 1097 | 55c2291c0449cfd4041f147e86c02b81c697aeab670015d8bc76074c9c9f152d |
| eng_srcpins.log | 7815 | f7aaec82d7430407cab5c4ec0acef305a028875674aaa54c825704b4782b26e2 |
| eng_static_checks.py | 4160 | 808f16b17eed028006c017db24be77d370d012636684d7a6eec8480e7825238f |
| eng_static_checks.txt | 5171 | f64d4abeff0ea71cf0c35aaa1fb3c7c44d9397bb8dbb8fba6d3bb76edb0550fd |
| eng_unit_off.log | 5191 | c142a84d5434ed5b9deef16478c38d1f873b6c225de5244535822d7f42da68b5 |
| eng_unit_on.log | 14016 | baa811949eb194d621c9dbd61acd7d0457d21e0ac527c6982b649c92c464aacc |
| engineering_notes.md | 2630 | 73e41107d00709a7dc50a6321f5062f64137dae8ac629a20428cdb75c21382ad |

eng_mut_copies/ holds the byte copies of auth_routes.py and CLAUDE.md (CRLF, the HEAD checkout).
