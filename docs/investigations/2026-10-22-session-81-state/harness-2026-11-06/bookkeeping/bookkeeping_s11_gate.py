import datetime, os, re, subprocess, sys, pathlib, shutil
SCR = "C:/Users/SynAckITPC/AppData/Local/Temp/claude/cde30765822f13ce/03431011-0c7e-4ecd-b0ce-08ff47f4af10/scratchpad"
DOCS = "C:/Users/SynAckITPC/Documents/AI/sc-docs-70"
STATE = DOCS + "/docs/investigations/2026-10-22-session-81-state"
os.chdir(STATE)
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
runid = sys.argv[1] if len(sys.argv) > 1 else "(GREEN run id pending)"
models = sys.argv[2] if len(sys.argv) > 2 else "(model stamps pending)"
copies = [(SCR + "/GATE_S81_11.md", "specs/GATE_S81_11.md"), (SCR + "/S81-11_RED_REPORT.md", "specs/S81_11_RED_REPORT.md"),
          (SCR + "/S81-11_red/COMM_SET.txt", "specs/S81_11_COMM_SET.txt"), (SCR + "/S81-11_red/E_ROWS.tsv", "specs/S81_11_E_ROWS.tsv"),
          (SCR + "/S81-11_red/NATIVE_READ_DRAFT.md", "specs/S81_11_NATIVE_READ_DRAFT.md")]
for src, dst in copies:
    shutil.copyfile(src, dst); b = pathlib.Path(dst).read_bytes(); print(dst, len(b), "non-ascii", sum(1 for x in b if x > 127))
p = pathlib.Path("DEFECT_LEDGER.md"); t = p.read_text(encoding="utf-8")
t2 = re.sub(r"\| spec reviewed APPROVE_WITH_CHANGES \(RULINGS_S81_11 R-S11-11\.\.41, [^)]*\); RED running \|",
            "| RED DONE + GATED (GATE_S81_11 GC-1..16: 8 frozen files, 124 nodes = 96 RED / 28 PIN, 40 mutants with M36 equivalent); GREEN + 2 adversaries running (%s) |" % ts, t, count=1)
assert t2 != t, "S81-11 row not updated"
p.write_text(t2, encoding="utf-8", newline="\n")
line = ("- %s S81-11 HONEST-FRAGRANCE-UI RED DONE + GATED, GREEN + TWO ADVERSARIES LAUNCHED: the RED wf_7fea8738-619 finished 09:51 (1 agent, 558k tokens, 117 tool uses, 54 min): 8 RED files under sc-s81-s11/SmartCompareApp/__tests__/s11/ (LF, ASCII; the shas in GATE_S81_11 GC-1); 124 nodes at base = 96 RED (every failure an assertion) / 28 PIN; the prototype IN PLACE (the client exception) 124 / 124, tsc rc 0, eslint 0 errors, the 23 backend pins + 6 CLAUDE.md readers green on the prototype through pyt.py; 40 mutants, 39 killed, M36 equivalent by ruling; the comm set 232 suites + 8 + 23 + 6 (the base reused from the spec; at head comm -13 = the E-row set as expected, comm -23 empty); the worktree restored (36 paths, 0 sha mismatches). Deviations D-1..D-9 ruled in GATE_S81_11 (GC-4 the AR copy without diacritics (the b3a fence stands, not an E-row); GC-5 232 suites = the set of record; GC-6 the E-rows E1-E15 + E1e + E8b per S81_11_E_ROWS.tsv, E15 re-pointed to the reason-carrying Alert shape; GC-7 the gregorian date by a static row, Hermes a stated limit; GC-8 the RED-defined names confirmed; GC-9 the RED's coming-soon EN strings stand, the App-Review adversary judges; GC-11 FOCUS: two adversaries in place; GC-13 the CLAUDE.md block after the S81-G5 block; GC-16 the [NATIVE READ] table at GREEN). Filed: specs/GATE_S81_11.md, S81_11_RED_REPORT.md, S81_11_COMM_SET.txt, S81_11_E_ROWS.tsv, S81_11_NATIVE_READ_DRAFT.md. GREEN + the two adversaries (correctness; appreview; both in place on byte copies) launched as %s through scripts/wf_unit_green.js (args <scratchpad>/S81-11_green_args.json; the NEW branch feature/s81-s11-honest-fragrance-ui from 6869a3e6; the CLAUDE.md block after the S81-G5 block; no full jest; the PR body <= 25,600 B); the agent models from the first transcript: %s. Lanes: this GREEN + the S81-20 RED (wf_84fe3638-ce3) = two." % (ts, runid, models))
with open("ledger.md", "a", encoding="utf-8", newline="\n") as fh:
    fh.write(line + "\n")
before = subprocess.run(["git", "-C", DOCS, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
paths = ["docs/investigations/2026-10-22-session-81-state/" + d for _, d in copies] + ["docs/investigations/2026-10-22-session-81-state/DEFECT_LEDGER.md", "docs/investigations/2026-10-22-session-81-state/ledger.md"]
subprocess.run(["git", "-C", DOCS, "add"] + paths, check=True)
r = subprocess.run(["git", "-C", DOCS, "commit", "-m", "S85: S81-11 RED gated (GATE_S81_11 GC-1..16), the RED report set filed, GREEN + two adversaries launched; the ledger line, the DEFECT row\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"], capture_output=True, text=True)
print("commit rc", r.returncode); print(r.stdout[-400:]); print(r.stderr[-800:])
after = subprocess.run(["git", "-C", DOCS, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
print("HEAD before", before, "after", after, "MOVED" if before != after else "NOT MOVED")
pu = subprocess.run(["git", "-C", DOCS, "push", "origin", "docs/session-81-state"], capture_output=True, text=True)
print("push rc", pu.returncode, (pu.stdout + pu.stderr)[-300:])
