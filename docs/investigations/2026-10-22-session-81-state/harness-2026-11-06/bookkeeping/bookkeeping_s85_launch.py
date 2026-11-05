import datetime, os, subprocess, sys
DOCS = "C:/Users/SynAckITPC/Documents/AI/sc-docs-70"
STATE = DOCS + "/docs/investigations/2026-10-22-session-81-state"
os.chdir(STATE)
models = sys.argv[1] if len(sys.argv) > 1 else "(model stamps not yet read)"
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
line = ("- %s S85 TWO SPEC LANES LAUNCHED at 07:59 (the docs commit afd455df carries the briefs): lane A = wf_da0e3118-8e6 (scripts/wf_unit_spec.js: spec + adversarial review; args <scratchpad>/S81-20_spec_args.json; the brief specs/S81_20_BRIEF.md; worktree sc-s81-s20 detached at 6869a3e6, no junction; the spec lands at sc-s81-s20/.qa-s80/S81-20_UNIT_SPEC.md + _SPEC_REVIEW.md), lane B = wf_ea75debc-c93 (the same script; args <scratchpad>/S81-11_spec_args.json; the brief specs/S81_11_BRIEF.md; worktree sc-s81-s11 detached at 6869a3e6 WITH the node_modules junction; the client exceptions in the title; the spec lands at sc-s81-s11/.qa-s80/S81-11_UNIT_SPEC.md + _SPEC_REVIEW.md); preconditions: weekly usage 22 pct all models / 26 pct Fable, node -e 0 0.62 s, cpu 14 pct, no pytest on the box; the agent models from the first transcripts: %s; active_workflows.txt = both runs; the stall monitor started report-only (interval 600, idle alarm 2400, pytest max 2100); a one-shot backstop cron at 09:03. The orchestrator context 45 pct of 1M. NEXT: on each spec + review, the rulings file (RULINGS_S81_20 / RULINGS_S81_11), then the RED rounds through scripts/wf_unit_red.js (two gate-heavy lanes; S81-20's RED builds the base record at 6869a3e6 by per-file reuse as its last step; S81-11's RED with the client exceptions)." % (ts, models))
with open("ledger.md", "a", encoding="utf-8", newline="\n") as fh:
    fh.write(line + "\n")
before = subprocess.run(["git", "-C", DOCS, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
subprocess.run(["git", "-C", DOCS, "add", "docs/investigations/2026-10-22-session-81-state/ledger.md"], check=True)
r = subprocess.run(["git", "-C", DOCS, "commit", "-m", "S85: the two spec lanes launched (S81-20 wf_da0e3118-8e6, S81-11 wf_ea75debc-c93), the ledger line\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"], capture_output=True, text=True)
print("commit rc", r.returncode); print(r.stdout[-600:]); print(r.stderr[-600:])
after = subprocess.run(["git", "-C", DOCS, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
print("HEAD before", before, "after", after, "MOVED" if before != after else "NOT MOVED")
p = subprocess.run(["git", "-C", DOCS, "push", "origin", "docs/session-81-state"], capture_output=True, text=True)
print("push rc", p.returncode, (p.stdout + p.stderr)[-400:])
