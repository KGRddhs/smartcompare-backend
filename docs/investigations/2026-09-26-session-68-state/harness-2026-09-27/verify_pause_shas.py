"""Compare every dirty worktree file against the sha256 recorded in the pause doc. Read-only."""
import hashlib, os, re, subprocess, sys
AI = "C:/Users/SynAckITPC/Documents/AI"
DOC = "C:/Users/SynAckITPC/Documents/AI/smartcompare/docs/investigations/2026-09-26-session-68-state/pause-2026-09-26/PAUSE_STATE_2026-09-26.md"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()
expected = {}
wt = None
for ln in open(DOC, encoding="utf-8"):
    m = re.match(r"^### (sc-[\w-]+) @", ln)
    if m:
        wt = m.group(1); continue
    m = re.match(r"^- ([0-9a-f]{64})  (.+)$", ln.rstrip())
    if m and wt:
        expected.setdefault(wt, {})[m.group(2)] = m.group(1)
bad = 0
for wt, files in expected.items():
    d = os.path.join(AI, wt)
    st = subprocess.run(["git", "status", "--short"], cwd=d, capture_output=True, text=True).stdout
    now = set(l[3:].strip().strip('"') for l in st.splitlines() if len(l) > 3)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=d, capture_output=True, text=True).stdout.strip()
    print(f"== {wt} @ {head}: {len(files)} recorded, {len(now)} dirty now")
    for f, exp in files.items():
        p = os.path.join(d, f)
        if not os.path.isfile(p):
            print(f"  MISSING {f}"); bad += 1; continue
        got = sha(p)
        if got != exp:
            print(f"  MISMATCH {f}: now {got[:12]} expected {exp[:12]}"); bad += 1
    extra = now - set(files)
    if extra:
        print(f"  EXTRA dirty files not in the pause doc: {sorted(extra)}"); bad += 1
print("RESULT:", "ALL MATCH" if not bad else f"{bad} problem(s)")
