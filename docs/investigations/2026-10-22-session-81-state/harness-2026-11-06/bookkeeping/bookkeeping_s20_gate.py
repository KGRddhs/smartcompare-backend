import datetime, os, re, subprocess, sys, pathlib, shutil
SCR = "C:/Users/SynAckITPC/AppData/Local/Temp/claude/cde30765822f13ce/03431011-0c7e-4ecd-b0ce-08ff47f4af10/scratchpad"
DOCS = "C:/Users/SynAckITPC/Documents/AI/sc-docs-70"
STATE = DOCS + "/docs/investigations/2026-10-22-session-81-state"
os.chdir(STATE)
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
runid = sys.argv[1] if len(sys.argv) > 1 else "(GREEN run id pending)"
models = sys.argv[2] if len(sys.argv) > 2 else "(model stamps pending)"
copies = [(SCR + "/GATE_S81_20.md", "specs/GATE_S81_20.md"), (SCR + "/S81-20_RED_REPORT.md", "specs/S81_20_RED_REPORT.md"),
          (SCR + "/S81-20_red/COMM_SET.txt", "specs/S81_20_COMM_SET.txt")]
for src, dst in copies:
    shutil.copyfile(src, dst); b = pathlib.Path(dst).read_bytes(); print(dst, len(b), "non-ascii", sum(1 for x in b if x > 127))
p = pathlib.Path("DEFECT_LEDGER.md"); t = p.read_text(encoding="utf-8")
t2 = re.sub(r"\| spec reviewed APPROVE_WITH_CHANGES \(RULINGS_S81_20 R-S20-23\.\.46, [^)]*\); RED running \|",
            "| RED DONE + GATED (GATE_S81_20 GC-1..15: the frozen file 13aa83ad..., 166 nodes = 122 RED / 44 PIN, 42 mutants + EQ1 / EQ2, the 388-file base record at 6869a3e6 stored); GREEN + 2 adversaries running (%s) |" % ts, t, count=1)
assert t2 != t, "S81-20 row not updated"
p.write_text(t2, encoding="utf-8", newline="\n")
line = ("- %s S81-20 B2-RESULT-GATE-V2 RED DONE + GATED, GREEN + TWO ADVERSARIES LAUNCHED: the RED wf_84fe3638-ce3 finished 10:40 (1 agent, 540k tokens, 102 tool uses, 59 min): ONE RED file tests/test_s81_s20_result_gate.py (72,464 B, LF, ASCII, no hex-named constant; sha 13aa83ad...) in sc-s81-s20 at 6869a3e6; 166 nodes at base = 122 RED (every failure an AssertionError) / 44 PIN; the prototype in a removed scratch worktree 166 / 166 with the flag unset and exported, the B1 P10 / P11 purity green; 42 mutants KILLED incl. M39 (the S81-10 order), M40 / M41 (the budget interplay), M42 (the stream had_error operand), EQ1 / EQ2 equivalent by ruling; the 388-file comm set re-derived identical and its BASE RECORD at 6869a3e6 STORED (base_records/6869a3e6.../97218ca8...: per-file reuse + 9 base chunks + the secret scan alone; the base failures = the known environmental nodes only); the worktree restored (47 restores sha-matched). Deviations ruled in GATE_S81_20: GC-5 the budget interplay pinned through recorders (the quota adversary proves the EVAL on the FakeRedis); GC-6 a spent budget is NOT re-counted (no record call) and keeps the credit (the GREEN-owned gate row G20-GR1); GC-7 NO await inside the stream generator's finally: ONE fire-and-forget settle coroutine (read -> decide -> refund-or-keep -> record) + the gate rows G20-GR2 (AST pin) / G20-GR3 (the client-cancel arm = the base arm); GC-8 a success body with no products = placeholder_identity (R7), url_gate_reason None under two products; GC-9 the other deviations accepted (R55's V1 half = PIN P19; R58 folded into R30[image]; the G3 tail observed through the fire_and_forget recorder); GC-10 the T23 snapshot with the flag exported, the corpus gate, the fourteen fences and the E8+ local-.env sweep are GREEN's; GC-11 FOCUS: two adversaries (correctness; quotaandbilling, the GC-15 brief). The junction created at sc-s81-s20/SmartCompareApp/node_modules for the fences. Filed: specs/GATE_S81_20.md, S81_20_RED_REPORT.md, S81_20_COMM_SET.txt. GREEN + the two adversaries launched as %s through scripts/wf_unit_green.js (args <scratchpad>/S81-20_green_args.json; the NEW branch feature/s81-s20-result-gate-v2 from 6869a3e6; the CLAUDE.md block after the S81-G5 block: the S81-11 lane adds a block at the same anchor, a both-sides-added union at whichever rebase comes second); the agent models from the first transcript: %s. Lanes: this GREEN + the S81-11 GREEN (wf_5369ebad-7fe) = two; the G7 spec waits." % (ts, runid, models))
with open("ledger.md", "a", encoding="utf-8", newline="\n") as fh:
    fh.write(line + "\n")
before = subprocess.run(["git", "-C", DOCS, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
paths = ["docs/investigations/2026-10-22-session-81-state/" + d for _, d in copies] + ["docs/investigations/2026-10-22-session-81-state/DEFECT_LEDGER.md", "docs/investigations/2026-10-22-session-81-state/ledger.md"]
subprocess.run(["git", "-C", DOCS, "add"] + paths, check=True)
r = subprocess.run(["git", "-C", DOCS, "commit", "-m", "S85: S81-20 RED gated (GATE_S81_20 GC-1..15), the RED report set filed, GREEN + two adversaries launched; the ledger line, the DEFECT row\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"], capture_output=True, text=True)
print("commit rc", r.returncode); print(r.stdout[-400:]); print(r.stderr[-800:])
after = subprocess.run(["git", "-C", DOCS, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
print("HEAD before", before, "after", after, "MOVED" if before != after else "NOT MOVED")
pu = subprocess.run(["git", "-C", DOCS, "push", "origin", "docs/session-81-state"], capture_output=True, text=True)
print("push rc", pu.returncode, (pu.stdout + pu.stderr)[-300:])
