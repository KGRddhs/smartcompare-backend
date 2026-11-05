import datetime, os, subprocess, pathlib, sys
# usage: python bookkeeping_g7_merge.py <merge time HH:MM>   (run AFTER `pr_rest.py merge 391`, BEFORE the worktree removal)
mt = sys.argv[1]
SCR = "C:/Users/SynAckITPC/AppData/Local/Temp/claude/cde30765822f13ce/03431011-0c7e-4ecd-b0ce-08ff47f4af10/scratchpad"
DOCS = "C:/Users/SynAckITPC/Documents/AI/sc-docs-70"; STATE = DOCS + "/docs/investigations/2026-10-22-session-81-state"
MEM = "C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents/memory"
WT = "C:/Users/SynAckITPC/Documents/AI/sc-s81-g7"
os.chdir(STATE); ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def git(*a, cwd=WT):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True).stdout.strip()

print("fetch rc", subprocess.run(["git", "-C", WT, "fetch", "-q", "origin", "main"]).returncode)
full = git("rev-parse", "origin/main"); sha = full[:8]
parents = git("log", "-1", "--format=%P", "origin/main").split()
stat = git("diff", "--shortstat", "05303c6f", "origin/main")
subj = git("log", "-1", "--format=%s", "origin/main")
print("origin/main", sha, "|", subj, "| parents", " ".join(p[:8] for p in parents), "|", stat)
assert "05303c6f" in [p[:8] for p in parents] and "ce3ec2a7" in [p[:8] for p in parents], "origin/main is not the #391 merge commit"

# DEFECT_LEDGER: the G7 FOLLOWUPS row -> MERGED (line-based last-cell replacement)
p = pathlib.Path("DEFECT_LEDGER.md"); t = p.read_text(encoding="utf-8")
def _last_cell(text, prefix, repl):
    out = []
    for ln in text.split(chr(10)):
        if ln.startswith(prefix):
            parts = ln.split(" | "); parts[-1] = repl + " |"; ln = " | ".join(parts)
        out.append(ln)
    return chr(10).join(out)
t2 = _last_cell(t, "| G7 FOLLOWUPS |", "MERGED PR #391 (2026-11-05 %s -> main %s; %s; D22c's select DARK behind ENABLE_BEHAVIOR_PROFILE_REBUILD, D16b / D17b / D22d ride ENABLE_OPERATOR_INGEST / ENABLE_KB_COVERAGE_ROLLUP / ENABLE_LEARNING_JOB (all OFF), the varhint retire unflagged with the corpus SHA equal)" % (mt, sha, stat.strip()))
assert t2 != t, "G7 row"
p.write_text(t2, encoding="utf-8", newline="\n")

# PLAN_STATUS: the Finished row + the dated line
row = ("| G7 FOLLOWUPS = D16b + D17b + D22c + D22d (SAFE group, LC-9) | #391 | 2026-11-05 %s | `ENABLE_BEHAVIOR_PROFILE_REBUILD` (NEW, OFF; D22c only): both `_update_behavior_profile` selects read event_data under the flag through the `_profile_rows_v2` normaliser, the OFF literals unchanged and pinned by the three-scenario golden tests/fixtures/s81_d22c_flag_off_golden.json; "
       "the varhint dead code (structured_comparison_service + price_service) and data/variant_hint_learned.json deleted UNFLAGGED (the corpus OVERALL SHA d2e16d30... equal at the base and at HEAD under --flags ENABLE_VARIANT_LLM_HINT,ENABLE_BEHAVIOR_PROFILE_REBUILD); D16b (rides ENABLE_OPERATOR_INGEST): a captured_at beyond kb_serve.FUTURE_SKEW_SECONDS (300 s) is refused and a negative age classifies through the shared `kb_serve.beyond_skew(moment, now)`; "
       "D17b (rides ENABLE_KB_COVERAGE_ROLLUP): `_paged` ORDER BY the primary key + the exec-then-execute Redis pipeline fallback; D22d (rides ENABLE_LEARNING_JOB): the paged kb_specs grounding read (`_read_by` in 100-value IN chunks, every distinct row), the dropped_deidentify count (wrong verdict + unclean field name only), `_render` escaping C0 + DEL through a str.translate table; "
       "the five frozen RED files + the golden + the gate rows G7-GR1..GR3 (tests/test_s81_g7_gate_rows.py, the adversary's ADV-O1 / O2 / O4 killed; ADV-O3 equivalent) + E1 / E2; the base record at 05303c6f (a0bfab95..., 695 files); the four minors MIN-1..4 as gate rows / stated limits L-D22c-6 / L-D22d-4; the hook test files NOT MEASURED locally (CI green); "
       "flip precondition: ENABLE_BEHAVIOR_PROFILE_REBUILD only after a canary window with the scoring_method `behavioral` share read; main %s |\n" % (mt, sha))
pathlib.Path("PLAN_STATUS_S81_2026-10-24.md").open("a", encoding="utf-8", newline="\n").write("\n" + row + "- %s FINISHED: G7 FOLLOWUPS (D16b + D17b + D22c + D22d; the sixth SAFE group under LC-9) merged as PR #391 (main %s; %s). NOTHING IN FLIGHT. S81-12 draft PR #378 HELD. NEXT per the grouped build order: SF1 SURFACES-BE (046 + 049 + the events allowlist; the S81-11 contract) and S81-22 COMPARE-RUNS (048) as the FOCUS lanes, then a SAFE follow-up group (S81-20b + B1b + S81-11b + S81-18b), S81-24 + MS4, S81-12b, CL3 / CL4 after SF1, NT1; S81-07 owner-blocked.\n" % (ts, sha, stat.strip()))

# the MOVING MAIN line
mm = ("- MOVING MAIN %s: origin/main = %s (#391 S81-G7 FOLLOWUPS merged %s: the EDITED app/services/kb_serve.py (FUTURE_SKEW_SECONDS + beyond_skew), app/services/kb_operator.py (the future captured_at refusal + the negative-age classify), app/services/structured_comparison_service.py (both _update_behavior_profile selects under ENABLE_BEHAVIOR_PROFILE_REBUILD + _profile_rows_v2; the varhint dead code removed), app/services/price_service.py (the varhint writer removed), "
      "scripts/cron_kb_coverage.py (_paged ORDER BY id + the exec / execute pipeline fallback), scripts/cron_learning.py (_read_by paged, dropped_deidentify, _render escaping), data/variant_hint_learned.json DELETED; the frozen RED tests/test_s81_d16b_operator_dates.py, test_s81_d17b_coverage_paging.py, test_s81_d22c_profile_select.py, test_s81_d22c_varhint_retire.py, test_s81_d22d_learning_hardening.py + tests/fixtures/s81_d22c_flag_off_golden.json; tests/test_s81_g7_gate_rows.py NEW (G7-GR1..GR3); E1 tests/test_variant_llm_hint_b3b.py, E2 tests/test_s81_g5_gate_rows.py; "
      "CLAUDE.md (the S81-G7 block after the S81-20 block with one blank line before its heading; the :341 clause with the S81-11, S81-20 and S81-G7 sentences in merge order); %s). BASE RECORD: 05303c6f/a0bfab95... (695 files) stands for a member referencing none of kb_serve / kb_operator / structured_comparison_service / price_service / cron_kb_coverage / cron_learning / variant_hint_learned nor CLAUDE.md and not a glob walker (GC-9 per-file reuse); "
      "the CLAUDE.md readers by the import graph (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire), the scs / price_service / kb_serve / kb_operator importers, the scripts/ walkers and the corpus harness re-run at %s. CLAUDE.md union order for the next replay: the S81-11, S81-20 and S81-G7 blocks after the S81-G5 block.\n" % (ts, sha, mt, stat.strip(), sha))
pathlib.Path("scripts/s81-common.txt").open("a", encoding="utf-8", newline="\n").write(mm)

# the ledger line
line = ("- %s S81-G7 FOLLOWUPS MERGED: PR #391 merged %s (7 / 7 green, mergeable_state clean; pr_rest.py merge 391) -> origin/main %s (the merge commit of ce3ec2a7 on 05303c6f; %s). ENABLE_BEHAVIOR_PROFILE_REBUILD unset: DARK; D16b / D17b / D22d ride their existing OFF flags; the varhint retire unflagged (corpus SHA equal). The hook test files NOT MEASURED locally (CI = the arbiter, green). "
        "Bookkeeping: DEFECT_LEDGER MERGED; PLAN_STATUS Finished row + the dated line; the MOVING MAIN line in scripts/s81-common.txt (the 17 files, the reuse rule, the union order); memory. Next: the sc-s81-g7 junction unlinked + the worktree removed, then NEXT_SESSION_PROMPT_S86.md at the clean point.\n" % (ts, mt, sha, stat.strip()))
pathlib.Path("ledger.md").open("a", encoding="utf-8", newline="\n").write(line)

# memory: the Update paragraph
mp = pathlib.Path(MEM + "/project-myez-session85-resume-2026-11-05.md"); m = mp.read_text(encoding="utf-8")
m += "\n**Update %s:** G7 FOLLOWUPS (D16b + D17b + D22c + D22d) MERGED as PR #391 (main %s; %s; dark: ENABLE_BEHAVIOR_PROFILE_REBUILD new and OFF). Three merges this session (#389, #390, #391); nothing in flight; the sc-s81-g7 worktree retired next, then NEXT_SESSION_PROMPT_S86.md. Base records: 05303c6f/a0bfab95... (695), 229b61e9/dd959a10... (392), 6869a3e6/97218ca8... (388) + ab9758ed... (691).\n" % (ts, sha, stat.strip())
mp.write_text(m, encoding="utf-8", newline="\n")

before = git("rev-parse", "--short", "HEAD", cwd=DOCS)
paths = ["docs/investigations/2026-10-22-session-81-state/" + f for f in ("DEFECT_LEDGER.md", "ledger.md", "PLAN_STATUS_S81_2026-10-24.md", "scripts/s81-common.txt")]
subprocess.run(["git", "-C", DOCS, "add"] + paths, check=True)
r = subprocess.run(["git", "-C", DOCS, "commit", "-q", "-m", "S85: G7 FOLLOWUPS merged as PR #391 (main %s) with its bookkeeping\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" % sha], capture_output=True, text=True)
after = git("rev-parse", "--short", "HEAD", cwd=DOCS)
print("commit rc", r.returncode, "HEAD", before, "->", after, "MOVED" if before != after else "NOT MOVED"); print(r.stderr[-300:])
pu = subprocess.run(["git", "-C", DOCS, "push", "-q", "origin", "docs/session-81-state"], capture_output=True, text=True); print("push rc", pu.returncode, pu.stderr[-200:])
