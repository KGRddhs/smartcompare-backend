"""harvest.py <wf_id> <out.json> [--list] : map every finished agent's result to its label (this session)."""
import json
import os
import sys

SESSION = "0a2845de-abfe-4bca-b433-df4ce9787ab5"
WF = "C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents-AI/%s/subagents/workflows" % SESSION


def main():
    wf, out = sys.argv[1], sys.argv[2]
    jp = os.path.join(WF, wf, "journal.jsonl")
    labels, res, started = {}, {}, []
    for line in open(jp, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("type") == "started":
            labels[r["agentId"]] = r.get("label")
            started.append(r.get("label"))
        if r.get("type") == "result":
            res[labels.get(r["agentId"], r["agentId"])] = r.get("result")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("started", started)
    print("harvested", list(res.keys()), "->", out)


if __name__ == "__main__":
    main()
