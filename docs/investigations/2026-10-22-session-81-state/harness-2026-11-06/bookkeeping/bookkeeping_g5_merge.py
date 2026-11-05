import datetime, io, os, re
D = "C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-22-session-81-state"
os.chdir(D)
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
MAIN = "6869a3e6"

def rw(path, fn):
    t = io.open(path, encoding="utf-8").read()
    io.open(path, "w", encoding="utf-8", newline="\n").write(fn(t))

def f_defect(t):
    n = len(re.findall(r"\| spec reviewed \(RULINGS_S81_G5, [^)]*\); RED running \|", t))
    assert n == 1, "D22 row status not found once: %d" % n
    return re.sub(r"\| spec reviewed \(RULINGS_S81_G5, [^)]*\); RED running \|",
                  "| MERGED #388 2026-11-05 07:15 (main %s; HEAD 50e3f3a5: GREEN 53b7b66e replayed onto 00e4120d + the final-round commit; 50 RED nodes + 7 gate rows, 15 + 39 mutants, the full jest 3,852 + the four w37 drift nodes) |" % MAIN, t)
rw("DEFECT_LEDGER.md", f_defect)

row = ("| D22 NIGHTLY-LEARNING (G5 LEARN-SEARCH, SAFE, scripts-only) | #388 | 2026-11-05 07:15 | `ENABLE_LEARNING_JOB` (unset / garbage OFF; true DRY; apply WRITE; read per call as the first statement of main) + knobs `LEARNING_WINDOW_DAYS` (7, 1..30), `LEARNING_MIN_CASES` (3, 1..100), `LEARNING_MIN_DEVICES` (2, 1..10), `LEARNING_MAX_ROWS` (5000, 100..50000), `LEARNING_EXEMPLARS_PER_CATEGORY` (5, 3..5): scripts/cron_learning.py + railway.learning.json: the nightly DB-only job (no LLM, no Serper) over the window of comparison_feedback / verdict_critiques / user_events / search_logs / kb_gaps / kb_feedback (kb_* absent before 045 = a counted skip) with paged id-ordered capped reads, the six buckets, the category x source x field clusters, the systematic rule (cases >= 3 from >= 2 distinct actors, user_id a named proxy; one comparison reported by two users = 1 case, 2 actors), KB correction proposals with judge_state pending (never applied), exemplar candidate sets (the de-identification screen before the per-category cut; never written under data/) and eval candidates in a de-identified report, learning.* rows in kb_coverage_daily through build_coverage_row in apply mode only; scripts/cron_few_shot_rotation.py + its test RETIRED (E2 / E3); stated limits L1-L15 (the judge absent until S81-22; the per-axis buckets read 0 until CL3 / SF1 send the correctness fields; the kb_specs grounding read beyond 800 rows; control characters in logged names); follow-ups D22b (migration 053 tables + the judge join + the prefix rotation, FOCUS, after S81-22), D22c (the user_events select fix + the variant_hint_learned retirement, SAFE), D22d (the paged kb_specs read, the dropped_deidentify count for an unclean field name, escaping on render); main %s |\n") % MAIN
def f_plan(t):
    anchor = "\n| CL2 CLIENT-SPEED (G6 CLIENT-PERF, client) |"
    i = t.find(anchor)
    assert i >= 0, "CL2 row not found"
    j = t.find("\n", i + 1)
    t = t[:j + 1] + row + t[j + 1:]
    t = t.rstrip("\n") + ("\n- %s FINISHED: G5 LEARN-SEARCH (D22 NIGHTLY-LEARNING; the fifth SAFE group under LC-9, scripts-only) merged as PR #388 (main %s; 8 files: scripts/cron_learning.py + railway.learning.json NEW, tests/test_s81_g5_gate_rows.py NEW, the frozen RED file, tests/test_s81_kb_schema.py E1, CLAUDE.md, scripts/cron_few_shot_rotation.py + tests/test_cron_few_shot_rotation.py DELETED). NOTHING IN FLIGHT at the clean point (the S85 hand-off written): seventeen S81 units + G1 + G2 + G3 + G4 + S81-16b + G5 + G6 on main; every flag OFF; S81-12 draft PR #378 HELD. NEXT per the grouped build order: the FOCUS units S81-20 B2-RESULT-GATE-V2, S81-22 COMPARE-RUNS + capped judge (migration 048; the judge D22 waits for), SF1 SURFACES-BE (046 + 049), S81-24 + MS4, S81-12b, S81-07 (owner-blocked), the client S81-11 HONEST-FRAGRANCE-UI (+ D20; the ENABLE_FRAGRANCE_ONLY_GATE flip precondition), CL3, CL4, NT1; the SAFE follow-ups batchable as a group (D16b + D17b + D22c + D22d, + S81-19b); G6b (SS1 + CL5) after owner item 19; CL2b after the TestFlight device check; S81-21 after S81-07; D22b after S81-22; S81-17b / S81-17c / D14b / D14c / EOL-ATTRS.\n") % (ts, MAIN)
    return t
rw("PLAN_STATUS_S81_2026-10-24.md", f_plan)

mm = ("- MOVING MAIN 2026-11-05 07:15: origin/main = %s (#388 S81-G5 LEARN-SEARCH = D22 NIGHTLY-LEARNING merged 07:15: NEW scripts/cron_learning.py (the DB-only learning job under ENABLE_LEARNING_JOB + the five LEARNING_* knobs; reads only through the service-role client; writes learning.* rows into kb_coverage_daily in apply mode), railway.learning.json, tests/test_s81_g5_gate_rows.py (G5-GR1..GR7), the frozen RED file tests/test_s81_d22_nightly_learning.py; EDITED tests/test_s81_kb_schema.py (E1: P02_ALLOWED + the two cron_learning rows), CLAUDE.md (the S81-G5 block after the S81-G6 block + the :341 clause); DELETED scripts/cron_few_shot_rotation.py and tests/test_cron_few_shot_rotation.py (dead code, the flag never registered). No app/ file, no migration. Base records: the stored 00e4120d record (9a85c0b0..., 48 files) and the ec747b49 / e1491c97 / 0b19de5b records stay reusable PER FILE for members that reference none of cron_learning / cron_few_shot_rotation / kb_seed_common nor tests/test_s81_kb_schema.py nor CLAUDE.md and are not glob walkers (GC-9); the CLAUDE.md readers (by the import graph: test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire), tests/test_s81_kb_schema.py, the scripts/ walkers and the railway config readers need a base re-run at %s. Every flag unset: nothing changes in production until the owner creates the learning service and makes the ONE DRY run (after 045).\n") % (MAIN, MAIN)
with io.open("scripts/s81-common.txt", "a", encoding="utf-8", newline="\n") as fh:
    fh.write(mm)

line = ("- %s G5 LEARN-SEARCH (D22) MERGED: PR #388 merged 07:15 (7 / 7 green, mergeable_state clean; `pr_rest.py merge 388`) -> origin/main %s (the merge commit of 50e3f3a5 on 00e4120d; 8 files, 2,710 insertions / 744 deletions). ENABLE_LEARNING_JOB unset: DARK; the owner steps in the PR body (apply 045 / 047 / 052; the learning service from railway.learning.json with the service-role NAMES; ONE DRY run and the log read, the first canary item = category / source unknown dominating; the schedule only after). Bookkeeping: DEFECT_LEDGER D22 -> MERGED; PLAN_STATUS Finished row + the dated line (the next units and the follow-ups incl. D22d); the MOVING MAIN line in scripts/s81-common.txt (the 8 files, the base-record reuse rule, the reader set); memory. The sc-s81-g5 junction unlinked with [System.IO.Directory]::Delete (the clone's node_modules/@babel/core verified) and the worktree removed. NOTHING IN FLIGHT: seventeen S81 units + G1 + G2 + G3 + G4 + S81-16b + G5 + G6 on main (two merges this session: #387 G6 CLIENT-PERF, #388 G5 LEARN-SEARCH), every flag OFF; S81-12 draft PR #378 HELD. The clean point: NEXT_SESSION_PROMPT_S85.md next." % (ts, MAIN))
with io.open("ledger.md", "a", encoding="utf-8", newline="\n") as fh:
    fh.write(line + "\n")

M = "C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents/memory/project-myez-session84-resume-2026-11-05.md"
t = io.open(M, encoding="utf-8").read().rstrip("\n")
t += ("\n\n**Update %s AST:** PR #388 (G5 LEARN-SEARCH = D22) MERGED at 07:15 -> main %s (8 files; dark behind ENABLE_LEARNING_JOB); sc-s81-g5 retired; the bookkeeping done (DEFECT_LEDGER, PLAN_STATUS + D22d, the MOVING MAIN line). NOTHING IN FLIGHT: two merges this session (#387 G6 CLIENT-PERF = CL2, #388 G5 LEARN-SEARCH = D22); every flag OFF; S81-12 draft PR #378 HELD. The clean point: NEXT_SESSION_PROMPT_S85.md being written (the next units = the FOCUS S81-20 / S81-22 / SF1 / S81-24 + MS4 / S81-11 client (+ D20) / CL3 / CL4 / NT1 and a SAFE follow-up group D16b + D17b + D22c + D22d).\n") % (ts, MAIN)
io.open(M, "w", encoding="utf-8", newline="\n").write(t)
print("bookkeeping done", ts)
