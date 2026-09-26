"""harvest.py <wf_id> <out.json> : map every finished agent's result to its label."""
import json, sys
wf, out = sys.argv[1], sys.argv[2]
J = f"C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents-AI/b1819d0c-d9c5-466a-ba0d-b82774c624db/subagents/workflows/{wf}/journal.jsonl"
labels, res = {}, {}
for line in open(J, encoding='utf-8'):
    try: r = json.loads(line)
    except Exception: continue
    if r.get('type') == 'started': labels[r['agentId']] = r.get('label')
    if r.get('type') == 'result': res[labels.get(r['agentId'], r['agentId'])] = r.get('result')
json.dump(res, open(out, 'w', encoding='utf-8'), indent=1)
print('harvested', list(res.keys()), '->', out)
