"""Wait for green:R-AUTH to land in the workflow journal, then write its report file and
wip-commit the green's uncommitted output in sc-r-auth so the adversary sees a clean tree
with the whole unit in git diff 1c6f6796..HEAD."""
import json, subprocess, time, sys
J = "C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents-AI/75660a55-e14a-4de1-80dc-a537f2af315e/subagents/workflows/wf_82ff570b-a61/journal.jsonl"
WT = "C:/Users/SynAckITPC/Documents/AI/sc-r-auth"
deadline = time.time() + 4 * 3600
while time.time() < deadline:
    labels, res = {}, {}
    for line in open(J, encoding='utf-8'):
        try: r = json.loads(line)
        except Exception: continue
        if r.get('type') == 'started': labels[r['agentId']] = r.get('label')
        if r.get('type') == 'result': res[labels.get(r['agentId'])] = r.get('result')
    if 'green:R-AUTH' in res:
        g = res['green:R-AUTH']
        json.dump(g, open('retro_green_R-AUTH.json', 'w', encoding='utf-8'), indent=1)
        print(time.strftime('%H:%M:%S'), 'green:R-AUTH landed; files:', g.get('files_changed'), flush=True)
        st = subprocess.run(["git", "-C", WT, "status", "--porcelain"], capture_output=True, text=True).stdout
        print("status before commit:\n" + st, flush=True)
        if st.strip():
            subprocess.run(["git", "-C", WT, "add", "-A"], check=True)
            msg = ("wip(R-AUTH): green resume output (session 67, UNVERIFIED - adversary pending)\n\n"
                   "Committed by the orchestrator the moment the green agent reported, so the adversary reviews a clean tree.\n\n"
                   "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>")
            r = subprocess.run(["git", "-C", WT, "commit", "-q", "-m", msg], capture_output=True, text=True)
            print("commit rc", r.returncode, r.stdout[-400:], r.stderr[-400:], flush=True)
            print(subprocess.run(["git", "-C", WT, "log", "--oneline", "-2"], capture_output=True, text=True).stdout, flush=True)
        sys.exit(0)
    time.sleep(10)
print("timed out waiting for green:R-AUTH")
sys.exit(1)
