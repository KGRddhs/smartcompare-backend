import datetime, os, subprocess, pathlib, sys
# usage: python close_s85.py <main short sha> <merge time HH:MM>   (run AFTER the sc-s81-g7 worktree is removed: the clean point)
sha, mt = sys.argv[1], sys.argv[2]
SCR = "C:/Users/SynAckITPC/AppData/Local/Temp/claude/cde30765822f13ce/03431011-0c7e-4ecd-b0ce-08ff47f4af10/scratchpad"
DOCS = "C:/Users/SynAckITPC/Documents/AI/sc-docs-70"; STATE = DOCS + "/docs/investigations/2026-10-22-session-81-state"
MEM = "C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents/memory"
os.chdir(STATE); ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
assert not pathlib.Path("C:/Users/SynAckITPC/Documents/AI/sc-s81-g7").exists(), "sc-s81-g7 still exists: not the clean point"

# the hand-off: the placeholders filled, copied into the state folder
h = pathlib.Path(SCR + "/NEXT_SESSION_PROMPT_S86.md").read_text(encoding="utf-8")
assert "<S86_MAIN_SHA>" in h and "<S86_MERGE_TIME>" in h
h = h.replace("<S86_MAIN_SHA>", sha).replace("<S86_MERGE_TIME>", mt)
assert "<S86_" not in h
pathlib.Path("NEXT_SESSION_PROMPT_S86.md").write_text(h, encoding="utf-8", newline="\n")
print("hand-off", pathlib.Path("NEXT_SESSION_PROMPT_S86.md").stat().st_size, "bytes")

# the ledger close line
line = ("- %s S85 CLOSED at the clean point: origin/main %s (three merges this session: #389 S81-11 HONEST-FRAGRANCE-UI + D20 12:34, #390 S81-20 B2-RESULT-GATE-V2 15:02, #391 G7 FOLLOWUPS %s); every flag OFF; 045 / 047 / 050 / 052 written NOT applied; S81-12 draft PR #378 HELD; NOTHING in flight; the lane worktrees sc-s81-s11 / sc-s81-s20 / sc-s81-g7 retired (junctions unlinked first, the clone's node_modules/@babel/core verified); "
        "NEXT_SESSION_PROMPT_S86.md written in this folder (first work: the SF1 SURFACES-BE + S81-22 COMPARE-RUNS FOCUS briefs and spec lanes, then a SAFE follow-up group); the crons deleted, the stall monitor stopped; the S85 scratchpad keeps the harness + base_records + the args templates.\n" % (ts, sha, mt))
pathlib.Path("ledger.md").open("a", encoding="utf-8", newline="\n").write(line)

# memory: the description line rewritten; MEMORY.md pointer replaced
mp = pathlib.Path(MEM + "/project-myez-session85-resume-2026-11-05.md"); lines = mp.read_text(encoding="utf-8").split("\n")
desc = ("description: SESSION 85 CLOSED 2026-11-05 %s at the clean point (session 03431011-0c7e-4ecd-b0ce-08ff47f4af10; Fable 5.1 orchestrator, Opus 5.5 agents): main %s (three merges: #389 S81-11 HONEST-FRAGRANCE-UI + D20 (client, OTA-only), #390 S81-20 B2-RESULT-GATE-V2 (dark), #391 G7 FOLLOWUPS = D16b + D17b + D22c + D22d (dark); every flag OFF; 045 / 047 / 050 / 052 written NOT applied; S81-12 draft PR #378 HELD); nothing in flight; "
        "paste NEXT_SESSION_PROMPT_S86.md from the session-81 state folder (first work: the SF1 + S81-22 FOCUS briefs and spec lanes, then a SAFE follow-up group; copy the S85 harness + base_records first); the record = ledger.md" % (ts[-5:], sha))
n = 0
for i, ln in enumerate(lines):
    if ln.startswith("description: "):
        lines[i] = desc; n += 1; break
assert n == 1, "description line"
mp.write_text("\n".join(lines), encoding="utf-8", newline="\n")
idx = pathlib.Path(MEM + "/MEMORY.md"); il = idx.read_text(encoding="utf-8").split("\n")
new = ("- [RESUME HERE - SESSION 85 CLOSED 2026-11-05 %s at the clean point: main %s (three merges: #389 S81-11 client OTA-only, #390 S81-20 dark, #391 G7 FOLLOWUPS dark; every flag OFF; 045 / 047 / 050 / 052 written NOT applied); nothing in flight; paste NEXT_SESSION_PROMPT_S86.md from the session-81 state folder (first work: the SF1 + S81-22 FOCUS briefs and spec lanes, then the SAFE follow-up group; copy the S85 harness + base_records first)](project-myez-session85-resume-2026-11-05.md)"
       " - the S85 scratchpad path, the harness and the args templates live there; the named source-scanning pins join every backend comm set; the S81-10 refusal budget bounds result-gate refusals; no await in a stream generator's finally; the hook test files are NOT RUN for a unit without a .githooks change." % (ts[-5:], sha))
n = 0
for i, ln in enumerate(il):
    if ln.startswith("- [RESUME HERE - SESSION 85"):
        il[i] = new; n += 1; break
assert n == 1, "MEMORY.md pointer"
idx.write_text("\n".join(il), encoding="utf-8", newline="\n")
print("memory updated")

before = subprocess.run(["git", "-C", DOCS, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
paths = ["docs/investigations/2026-10-22-session-81-state/" + f for f in ("ledger.md", "NEXT_SESSION_PROMPT_S86.md")]
subprocess.run(["git", "-C", DOCS, "add"] + paths, check=True)
r = subprocess.run(["git", "-C", DOCS, "commit", "-q", "-m", "S85 CLOSED at the clean point (main %s): NEXT_SESSION_PROMPT_S86.md + the ledger close line\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" % sha], capture_output=True, text=True)
after = subprocess.run(["git", "-C", DOCS, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
print("commit rc", r.returncode, "HEAD", before, "->", after, "MOVED" if before != after else "NOT MOVED"); print(r.stderr[-300:])
pu = subprocess.run(["git", "-C", DOCS, "push", "-q", "origin", "docs/session-81-state"], capture_output=True, text=True); print("push rc", pu.returncode, pu.stderr[-200:])
