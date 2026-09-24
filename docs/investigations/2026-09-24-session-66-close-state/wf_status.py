"""Print started/result labels for each workflow journal listed in WF."""
import json, os, sys, datetime

BASE = r"C:\Users\SynAckITPC\.claude\projects\C--Users-SynAckITPC-Documents-AI\a47353ce-a0e3-4273-b85d-f21cfa01e031\subagents\workflows"
WF = {
    "retro green w1": "wf_81cfdb3f-b68",
    "R-W18 green": "wf_6b26f70f-e02",
    "R-W04 red": "wf_96263ebe-b30",
    "retro w1 red": "wf_cc8dbbb5-ddc",
    "pr rescue": "wf_69649ad9-4d9",
    "W4-10 polish": "wf_8aecce8a-519",
    "W4-4 polish": "wf_7d0366cd-a17",
    "W4-3 adv r1": "wf_e5bc83b1-065",
    "W4-9 fix": "wf_fa2afc37-fd8",
    "W4-2 red": "wf_9ddf3190-1d5",
    "R-W0 green": "wf_57e50329-233",
}
extra = sys.argv[1:]
for e in extra:
    WF[e] = e

for name, wf in WF.items():
    p = os.path.join(BASE, wf, "journal.jsonl")
    if not os.path.exists(p):
        print(f"{name:18s}: NO JOURNAL ({wf})")
        continue
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    lab = {r["agentId"]: r.get("label") for r in rows if r.get("type") == "started"}
    done = [lab.get(r["agentId"], "?") for r in rows if r.get("type") == "result"]
    started = [r.get("label") for r in rows if r.get("type") == "started"]
    pending = [s for s in started if s not in done]
    fin = [r for r in rows if r.get("type") in ("finished", "completed", "done")]
    print(f"{name:18s}: done={done} pending={pending}{' FINISHED' if fin else ''}")
print(datetime.datetime.now().strftime("%H:%M"))
