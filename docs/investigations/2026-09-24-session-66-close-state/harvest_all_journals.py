"""Harvest every completed agent result from the session's workflow journals
into one JSON per workflow (label -> result) and print a status table."""
import json, os, sys

BASE = r"C:\Users\SynAckITPC\.claude\projects\C--Users-SynAckITPC-Documents-AI\a47353ce-a0e3-4273-b85d-f21cfa01e031\subagents\workflows"
SP = sys.argv[1]
WF = {
    "retro-green-w1": "wf_81cfdb3f-b68",
    "R-W18-green": "wf_6b26f70f-e02",
    "R-W0-green": "wf_57e50329-233",
    "R-W04-red": "wf_96263ebe-b30",
    "retro-w1-red": "wf_cc8dbbb5-ddc",
    "pr-rescue": "wf_69649ad9-4d9",
    "W4-10-polish": "wf_8aecce8a-519",
    "W4-4-polish": "wf_7d0366cd-a17",
    "W4-batch5-green": "wf_e5bc83b1-065",
    "W4-9-green": "wf_fa2afc37-fd8",
    "W4-2-red": "wf_9ddf3190-1d5",
}
for name, wf in WF.items():
    p = os.path.join(BASE, wf, "journal.jsonl")
    if not os.path.exists(p):
        print(f"{name:18s} {wf}: NO JOURNAL"); continue
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    lab = {r["agentId"]: r.get("label") for r in rows if r.get("type") == "started"}
    started = [r.get("label") for r in rows if r.get("type") == "started"]
    res = {lab.get(r["agentId"], "?"): r["result"] for r in rows if r.get("type") == "result"}
    pending = [s for s in started if s not in res]
    out = os.path.join(SP, f"journal_{name}.json")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    verdicts = {k: (v.get("verdict") if isinstance(v, dict) else None) for k, v in res.items() if k.startswith("adversary")}
    print(f"{name:18s} {wf}: done={list(res)} pending(killed)={pending} verdicts={verdicts}")
