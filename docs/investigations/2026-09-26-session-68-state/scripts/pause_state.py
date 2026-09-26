"""Session 68 PAUSE snapshot: harvest the stopped workflows, record every worktree's
dirty files with sha256 (never modifying anything), list leftover pytest processes."""
import hashlib
import json
import os
import subprocess
import sys
import time

SP = os.path.dirname(os.path.abspath(__file__))
WF = r"C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents-AI/b1819d0c-d9c5-466a-ba0d-b82774c624db/subagents/workflows"
AI = r"C:/Users/SynAckITPC/Documents/AI"
OUT = os.path.join(SP, "PAUSE_STATE_2026-09-26.md")
lines = ["# SESSION 68 PAUSE STATE - " + time.strftime("%Y-%m-%d %H:%M:%S local"), ""]

def sh(cmd, cwd=None, timeout=900):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, shell=False)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return f"<{type(e).__name__}: {e}>"

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# 1. harvest journals of the four stopped workflows
runs = {
    "wf_b2fa7eff-2c7": "HERMETICITY fix round 6 (R22)",
    "wf_7aa90e86-09c": "W4-8 green",
    "wf_a4c9e61f-6ae": "W4-13 fix round 3 (R10-R13)",
    "wf_5c5b1883-e87": "W4-6a green",
}
lines.append("## Stopped workflows (TaskStop ~20:40 local) and what their journals hold")
for run, label in runs.items():
    jp = os.path.join(WF, run, "journal.jsonl")
    started, results = [], {}
    try:
        for raw in open(jp, encoding="utf-8"):
            try:
                ev = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if ev.get("type") == "started":
                started.append(ev.get("label"))
            elif ev.get("type") == "result":
                results[ev.get("agentId")] = ev
        # map agentId -> label via started events order is not reliable; re-scan
        lab_by_agent = {}
        for raw in open(jp, encoding="utf-8"):
            try:
                ev = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if ev.get("type") == "started":
                lab_by_agent[ev.get("agentId")] = ev.get("label")
        done = [lab_by_agent.get(a, a) for a in results]
        lines.append(f"- `{run}` {label}: started={started} completed={done}")
        # harvest completed results to JSON
        outj = os.path.join(SP, f"pause_{run}.json")
        json.dump({lab_by_agent.get(a, a): ev.get("result") for a, ev in results.items()}, open(outj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        lines.append(f"  harvested -> scratchpad/pause_{run}.json")
    except Exception as e:  # noqa: BLE001
        lines.append(f"- `{run}` {label}: journal unreadable <{type(e).__name__}>")
lines.append("")

# 2. worktree dirty files + shas (read-only)
wts = {
    "sc-hermetic": "test/hermeticity-183-184-185-186 (COMMITTED 41728973 on 88cb78ae = round-5 SOUND bytes; PR #207 red at collection; round-6 R22 edits UNCOMMITTED on top, mid-round)",
    "sc-w4-13": "feature/s68-w4-13-measurement-truth (HEAD ac887e2d; round-2 SOUND bytes + round-3 R10-R13 fixer DONE, its adversary killed mid-run -> possible mutant)",
    "sc-w4-12": "feature/s68-w4-12-display-contract (HEAD ac887e2d; round-3 SOUND bytes; R19-R20 round 4 NOT started)",
    "sc-w4-8": "feature/s68-w4-8-category-blocklist (HEAD 04acb757; red gated; green agent killed mid-run -> partial implementation)",
    "sc-w4-6a": "feature/s68-w4-6a-scoring-truth (HEAD 04acb757; red gated; green agent DONE, its adversary killed mid-run -> possible mutant)",
    "sc-w4-11": "feature/s68-w4-11-prompt-truth (HEAD 88cb78ae; specs copied; red NOT started)",
    "sc-w4-7": "feature/s68-w4-7-rubric-readers (HEAD 88cb78ae; specs copied; red NOT started)",
    "sc-w0-4efg": "retro/w0-4efg-followups (MERGED as #205; retire)",
}
lines.append("## Worktrees: dirty files with sha256 at pause (nothing modified; re-run each unit's files before trusting a tree whose adversary was killed)")
for wt, desc in wts.items():
    d = os.path.join(AI, wt)
    if not os.path.isdir(d):
        lines.append(f"### {wt}: MISSING")
        continue
    head = sh(["git", "rev-parse", "--short", "HEAD"], cwd=d).strip()
    status = sh(["git", "status", "--short"], cwd=d)
    lines.append(f"### {wt} @ {head} - {desc}")
    lines.append("```")
    lines.append(status.rstrip() or "(clean)")
    lines.append("```")
    files = []
    for ln in status.splitlines():
        if len(ln) > 3:
            files.append(ln[3:].strip().strip('"'))
    for f in files:
        p = os.path.join(d, f)
        if os.path.isfile(p):
            lines.append(f"- {sha(p)}  {f}")
    lines.append("")

# 3. leftover python processes (killed agents may leave pytest running)
lines.append("## Leftover python processes at pause (command lines)")
ps = sh(["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Select-Object ProcessId,CreationDate,@{n='cmd';e={$_.CommandLine.Substring(0,[Math]::Min(220,$_.CommandLine.Length))}} | Format-Table -AutoSize -Wrap | Out-String -Width 400"], timeout=600)
lines.append("```")
lines.append(ps.strip()[:8000])
lines.append("```")

open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("written", OUT, len(lines), "lines")
