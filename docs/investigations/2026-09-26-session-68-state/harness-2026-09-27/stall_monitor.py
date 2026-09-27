"""stall_monitor.py - the session-68b watchdog (Ahmed's 2026-09-26 harness request).

Every --interval seconds it
  1. probes process-spawn latency (the venv python running 'pass'); above --spawn-alarm
     seconds the box is PATHOLOGICAL (the session-66/68 slow-spawn state);
  2. lists every pytest process (python.exe whose command line runs pytest):
       age above --pytest-max seconds  -> KILLED as a runaway (pyt.py bounds every run at
                                          1800 s, so an older pytest is outside the harness);
       parent process gone             -> KILLED as an orphan of a stopped agent;
  3. reads the journal of every workflow listed in active_workflows.txt (one run id per
     line, '#' comments allowed): an agent with a 'started' event and no 'result' whose
     elapsed time exceeds its phase bound (green/fix 7200 s, adversary/red 5400 s, other
     7200 s) or whose transcript has been idle for more than --idle-alarm seconds is a
     STALL (reported once per agent);
  4. samples CPU load and the python / node process counts;
  5. writes stall_report.txt (latest tick) and appends stall_log.txt.
--exit-on-alarm: exit 3 on the first STALL or PATHOLOGY (a background shell then returns
to the orchestrator).  --max-minutes N: exit 0 after N minutes as a heartbeat.
--once: one tick, print the report, exit (0, or 3 on alarm).
"""
import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = "C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
SESSION = "0a2845de-abfe-4bca-b433-df4ce9787ab5"
WF_DIR = ("C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents-AI/%s/subagents/workflows" % SESSION)
ACTIVE = os.path.join(HERE, "active_workflows.txt")
REPORT = os.path.join(HERE, "stall_report.txt")
LOG = os.path.join(HERE, "stall_log.txt")
STATE = os.path.join(HERE, "stall_state.json")
PHASE_BOUND = {"green": 7200, "fix": 7200, "adversary": 5400, "red": 5400, "spec": 5400}

PS_PROCS = (
    "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|node|pytest)' } | "
    "Select-Object ProcessId, ParentProcessId, Name, "
    "@{n='Created';e={ if ($_.CreationDate) { $_.CreationDate.ToUniversalTime().ToString('o') } else { '' } }}, "
    "@{n='Cmd';e={ if ($_.CommandLine) { $_.CommandLine.Substring(0, [Math]::Min(300, $_.CommandLine.Length)) } else { '' } }} | "
    "ConvertTo-Json -Compress"
)
PS_ALIVE = "(Get-Process -Id %d -ErrorAction SilentlyContinue) -ne $null"
PS_LOAD = "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"


def now():
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ps(cmd, timeout=120):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout or "").strip()


def spawn_probe():
    t = time.time()
    try:
        subprocess.run([VENV_PY, "-c", "pass"], capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        return 300.0
    return time.time() - t


def list_procs():
    out = ps(PS_PROCS, timeout=180)
    if not out:
        return []
    data = json.loads(out)
    if isinstance(data, dict):
        data = [data]
    procs = []
    for p in data:
        created = None
        if p.get("Created"):
            try:
                created = _dt.datetime.fromisoformat(p["Created"].replace("Z", "+00:00")).timestamp()
            except ValueError:
                created = None
        procs.append({"pid": int(p["ProcessId"]), "ppid": int(p.get("ParentProcessId") or 0),
                      "name": p.get("Name"), "created": created, "cmd": p.get("Cmd") or ""})
    return procs


def is_pytest(p):
    c = p["cmd"]
    return p["name"].lower().startswith("python") and ("-m pytest" in c or "pytest" in c.split("\\")[-1].split("/")[-1][:20]) and "stall_monitor" not in c and "pyt.py" not in c


def kill(pid):
    try:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, timeout=120)
        return True
    except Exception:  # noqa: BLE001
        return False


def read_active():
    ids = []
    if os.path.isfile(ACTIVE):
        for ln in open(ACTIVE, encoding="utf-8"):
            s = ln.strip()
            if s and not s.startswith("#"):
                ids.append(s.split()[0])
    return ids


def workflow_agents(run_id):
    """Return [{agent, label, phase, started_at, last_activity, done}] for one run."""
    d = os.path.join(WF_DIR, run_id)
    jp = os.path.join(d, "journal.jsonl")
    if not os.path.isfile(jp):
        return None
    labels, phases, done = {}, {}, set()
    for raw in open(jp, encoding="utf-8", errors="replace"):
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        if ev.get("type") == "started":
            labels[ev["agentId"]] = ev.get("label") or ""
            phases[ev["agentId"]] = ev.get("phase") or ""
        elif ev.get("type") == "result":
            done.add(ev.get("agentId"))
    out = []
    for aid, label in labels.items():
        meta = os.path.join(d, "agent-%s.meta.json" % aid)
        tr = os.path.join(d, "agent-%s.jsonl" % aid)
        started_at = os.path.getmtime(meta) if os.path.isfile(meta) else (os.path.getctime(tr) if os.path.isfile(tr) else None)
        last = os.path.getmtime(tr) if os.path.isfile(tr) else started_at
        out.append({"agent": aid, "label": label, "phase": phases.get(aid, ""), "started_at": started_at,
                    "last_activity": last, "done": aid in done})
    return out


def phase_bound(label, phase):
    key = (label.split(":")[0] if label else phase or "").lower()
    for k, v in PHASE_BOUND.items():
        if key.startswith(k):
            return v
    return 7200


def load_state():
    if os.path.isfile(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except ValueError:
            pass
    return {"reported": []}


def save_state(st):
    json.dump(st, open(STATE, "w", encoding="utf-8"))


def tick(a, st):
    lines = ["# stall monitor tick %s" % now()]
    alarms = []
    # 1. spawn latency
    lat = spawn_probe()
    lines.append("spawn_probe_s=%.1f (alarm at %d)" % (lat, a.spawn_alarm))
    if lat > a.spawn_alarm:
        alarms.append("PATHOLOGY: spawn probe took %.0f s" % lat)
    # 2. processes
    try:
        procs = list_procs()
        by_pid = {p["pid"]: p for p in procs}
        py = [p for p in procs if p["name"].lower().startswith("python")]
        nd = [p for p in procs if p["name"].lower().startswith("node")]
        pyt = [p for p in py if is_pytest(p)]
        lines.append("procs: python=%d node=%d pytest=%d" % (len(py), len(nd), len(pyt)))
        t = time.time()
        for p in pyt:
            age = (t - p["created"]) if p["created"] else -1
            parent_alive = p["ppid"] in by_pid or (ps(PS_ALIVE % p["ppid"], timeout=60).strip().lower() == "true")
            tag = ""
            if age > a.pytest_max:
                tag = "KILLED runaway (age %.0f s > %d)" % (age, a.pytest_max)
                kill(p["pid"])
            elif not parent_alive:
                tag = "KILLED orphan (parent %d gone)" % p["ppid"]
                kill(p["pid"])
            lines.append("  pytest pid=%d ppid=%d age=%.0fs %s :: %s" % (p["pid"], p["ppid"], age, tag, p["cmd"][:160]))
    except Exception as exc:  # noqa: BLE001
        lines.append("procs: census FAILED (%s: %s)" % (type(exc).__name__, str(exc)[:200]))
    # 3. workflows
    active = read_active()
    lines.append("active workflows: %s" % (", ".join(active) if active else "(none listed)"))
    t = time.time()
    for run in active:
        agents = workflow_agents(run)
        if agents is None:
            lines.append("  %s: no journal yet" % run)
            continue
        for ag in agents:
            if ag["done"]:
                lines.append("  %s %s: DONE" % (run, ag["label"]))
                continue
            el = (t - ag["started_at"]) if ag["started_at"] else -1
            idle = (t - ag["last_activity"]) if ag["last_activity"] else -1
            bound = phase_bound(ag["label"], ag["phase"])
            flag = ""
            key = run + ":" + ag["agent"]
            if el > bound:
                flag = "STALL elapsed %.0f s > bound %d" % (el, bound)
            elif idle > a.idle_alarm:
                flag = "STALL idle %.0f s > %d" % (idle, a.idle_alarm)
            if flag and key not in st["reported"]:
                alarms.append("%s %s: %s" % (run, ag["label"], flag))
                st["reported"].append(key)
            lines.append("  %s %s: running elapsed=%.0fs idle=%.0fs bound=%ds %s" % (run, ag["label"], el, idle, bound, flag))
    # 4. load
    try:
        lines.append("cpu_load_pct=%s" % ps(PS_LOAD, timeout=60))
    except Exception as exc:  # noqa: BLE001
        lines.append("cpu_load_pct=? (%s)" % type(exc).__name__)
    if alarms:
        lines.append("ALARMS:")
        lines.extend("  " + x for x in alarms)
    text = "\n".join(lines) + "\n"
    open(REPORT, "w", encoding="utf-8").write(text)
    open(LOG, "a", encoding="utf-8").write(text + "\n")
    save_state(st)
    return text, alarms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=600)
    ap.add_argument("--spawn-alarm", type=int, default=30)
    ap.add_argument("--pytest-max", type=int, default=2100)
    ap.add_argument("--idle-alarm", type=int, default=2400)
    ap.add_argument("--exit-on-alarm", action="store_true")
    ap.add_argument("--max-minutes", type=int, default=0)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    st = load_state()
    deadline = time.time() + a.max_minutes * 60 if a.max_minutes else None
    while True:
        text, alarms = tick(a, st)
        print(text, flush=True)
        if a.once:
            sys.exit(3 if alarms else 0)
        if alarms and a.exit_on_alarm:
            print("[stall_monitor] exiting on alarm", flush=True)
            sys.exit(3)
        if deadline and time.time() >= deadline:
            print("[stall_monitor] heartbeat: max-minutes reached", flush=True)
            sys.exit(0)
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
