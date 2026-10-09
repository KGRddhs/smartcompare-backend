import pathlib, shutil, sys

SP = pathlib.Path(r"C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/f9970d11-1fa0-400e-9fb3-dd91f335e519/scratchpad")
SRC = pathlib.Path(r"C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-08-session-74-state/scripts/s74-common.txt")

text = SRC.read_bytes().decode("ascii")

repls = [
    ("SESSION 74 AGENT RULES", "SESSION 75 AGENT RULES"),
    ("Today is 2026-10-08 (session 74)", "Today is 2026-10-09 (session 75)"),
    ("main = dfbda511 (#332 session-73 docs; ",
     "main = 4c0f3c99 (#339 session-74 docs checkpoint 3; merged 2026-10-08: #334 CLIENT-TRUTH, #335 U3c, #337 U13e, #338 BE-HARNESS; "),
    ("609148ee-5724-4d44-9ca2-c3b84ed07b25", "f9970d11-1fa0-400e-9fb3-dd91f335e519"),
    ("(sc-s71-*, sc-s70-u4b, sc-docs-70)", "(sc-s71-*, sc-s74-*, sc-s70-u4b, sc-docs-70)"),
    ("(file:line at main dfbda511,", "(file:line at main 4c0f3c99,"),
]
for a, b in repls:
    if a not in text:
        print("MISSING anchor:", a)
        sys.exit(1)
    text = text.replace(a, b)

addenda = """
- (session 75 addenda) This rules file lives at BOTH <scratchpad>/s75-common.txt and <scratchpad>/harness/s75-common.txt (identical copies; read either). Never run a character-level difflib.SequenceMatcher over a whole large file (CLAUDE.md is about 250 KB; it hung 10+ minutes): diff one line, or use 'git diff --word-diff'. Git Bash heredocs must stay pure ASCII on this box. Reading a worktree file with the Read tool injects that worktree's CLAUDE.md (about 86 K tokens): read worktree files with bash (cat, sed -n, head) and write new files into your notes folder first, then cp.
- (session 75 addenda) MUTATION LOCK: before the first mutation in a worktree create <worktree>/.qa-mutation.lock containing your agent label and the time; delete it after the last restore. If the file exists and is not yours, STOP mutating and report it. A final adversary has the worktree ALONE; two harnesses in one worktree contaminate each other's windows (measured 2026-10-08).
- (session 75 addenda) Worktrees of this session: sc-s74-u13e = COST-METER (branch feature/s75-cost-meter), sc-s71-t0b = FANOUT-STARVE (branch feature/s75-fanout-starve), sc-s74-ct = client units (its SmartCompareApp/node_modules is a JUNCTION into sc-s70-u4b: never delete, move or recreate anything under it; one jest at a time across sc-s74-ct and sc-s70-u4b), sc-s70-u4b = U8 legal PR #330 (do not touch). Production facts you may cite without probing (never probe production yourself): Railway web runs with ADAPTER_EXECUTOR_MAX_WORKERS=96, UV_THREADPOOL_SIZE=64, SERPER_CONNECT_TIMEOUT=8 since 2026-10-08; uvicorn auto-selects uvloop (0.22.1 pinned, no --loop flag); canary 6 (2026-10-08 21:20, A1.8 rule) FAILED: q-form compares partial at stage gather at the 30 s cap with 0/2 prices, while the product_a/product_b probe reached the verdict with 1/2 prices (report: docs/investigations/2026-10-08-session-74-state/canary/canary6_report.json on main).
"""
text = text.rstrip("\n") + "\n" + addenda.lstrip("\n")

data = text.encode("ascii")
for dest in (SP / "s75-common.txt", SP / "harness" / "s75-common.txt"):
    dest.write_bytes(data)
    print("wrote", dest, len(data), "bytes; non-ascii:", sum(1 for b in data if b > 127))
