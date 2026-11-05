"""pyt.py - the ONE way to run pytest in session 68b (Ahmed's 2026-09-26 harness request).

  python pyt.py --bound SECONDS --tag NAME --log FILE [--cwd WORKTREE] [--plugin auto|yes|no]
                [--per-test SECONDS] -- <pytest args: files, -k, --collect-only, ...>

What it guarantees:
  * a HARD wall-clock bound: on expiry the whole process tree is killed (taskkill /T /F)
    and the run is reported as status=TIMEOUT (exit 124) - a measurement failure to
    report, never something to wait on.  Bounds above the 1800 s ceiling are clamped.
  * a per-test timeout (--timeout=<per-test>, default 120) unless the caller passes one;
  * '-p no:cacheprovider -p no:randomly' and the free-tier marker filter unless passed;
  * the network guard chosen for the worktree: worktrees whose tests/conftest.py wires
    tests/_netguard.py run bare; every other worktree gets the qaren_netguard plugin
    with its PYTHONPATH (auto) - the caller never passes the plugin itself;
  * PYTHONIOENCODING=utf-8; the full output tee'd to --log; a compact stdout (summary,
    [netguard]/[hermeticity] lines, FAILED/ERROR ids, the tail) and ONE final line
      [pyt] tag=... start=... end=... elapsed=...s bound=...s status=OK|FAIL|TIMEOUT rc=...
  * a JSON ledger line appended to <this dir>/pyt_ledger.jsonl for the stall monitor.
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
NETGUARD_DIR = os.path.join(HERE, "netguard")
LEDGER = os.path.join(HERE, "pyt_ledger.jsonl")
CEILING = 1800
DEFAULT_MARK = "not (live_unit or live_db or integration)"
SUMMARY_RE = re.compile(r"^(=+ )?.*\b(\d+ (passed|failed|error|errors|skipped|deselected|xfailed|xpassed|warnings?))\b.* in [\d.]+s")
COLLECT_RE = re.compile(r"^\d+(/\d+)? tests? collected")


def now():
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def worktree_has_conftest_guard(cwd):
    conftest = os.path.join(cwd, "tests", "conftest.py")
    guard = os.path.join(cwd, "tests", "_netguard.py")
    if not (os.path.isfile(conftest) and os.path.isfile(guard)):
        return False
    try:
        with open(conftest, encoding="utf-8", errors="replace") as fh:
            return "_netguard" in fh.read()
    except OSError:
        return False


def kill_tree(pid):
    try:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, timeout=120)
    except Exception as exc:  # noqa: BLE001
        print("[pyt] taskkill failed: %s" % exc, flush=True)


def _pid_alive(pid):
    """Windows-safe liveness check (never os.kill: on Windows a 0 signal terminates the target)."""
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"], capture_output=True, text=True, timeout=30).stdout
        return str(pid) in out.split()
    except Exception:
        return False


def _acquire_tag_lock(tag):
    """Refuse a second live run of the same --tag (2026-10-29: two agents launched the same chunk driver
    twice, 3 s apart: double load, interleaved logs). Writes <HERE>/locks/<tag>.lock or exits 125."""
    import atexit, re
    lock_dir = os.path.join(HERE, "locks")
    os.makedirs(lock_dir, exist_ok=True)
    lock = os.path.join(lock_dir, re.sub(r"[^A-Za-z0-9_.-]", "_", tag) + ".lock")
    if os.path.exists(lock):
        try:
            old = int((open(lock, encoding="utf-8").read().split() or ["0"])[0])
        except Exception:
            old = 0
        if old and old != os.getpid() and _pid_alive(old):
            print("[pyt] tag=%s status=DUPLICATE rc=125 (a run with this tag is live: pid %d; this run was NOT started; wait for it or use a new tag)" % (tag, old), flush=True)
            sys.exit(125)
    with open(lock, "w", encoding="utf-8") as fh:
        fh.write("%d %s" % (os.getpid(), time.strftime("%Y-%m-%d %H:%M:%S")) + chr(10))
    def _release():
        try:
            if os.path.exists(lock) and (open(lock, encoding="utf-8").read().split() or ["0"])[0] == str(os.getpid()):
                os.remove(lock)
        except Exception:
            pass
    atexit.register(_release)
    return lock


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--bound", type=int, required=True, help="hard wall-clock bound in seconds (ceiling 1800)")
    ap.add_argument("--tag", required=True, help="short name of this run for the ledger and the [pyt] line")
    ap.add_argument("--log", required=True, help="file that receives the full pytest output")
    ap.add_argument("--cwd", default=os.getcwd(), help="the worktree to run in (default: current dir)")
    ap.add_argument("--plugin", choices=["auto", "yes", "no"], default="auto")
    ap.add_argument("--per-test", type=int, default=120, help="pytest-timeout per test when none is passed")
    ap.add_argument("--tail", type=int, default=25, help="how many trailing log lines to echo")
    ap.add_argument("rest", nargs=argparse.REMAINDER, help="pytest arguments after --")
    a = ap.parse_args()
    rest = list(a.rest)
    if rest and rest[0] == "--":
        rest = rest[1:]
    if not rest:
        raise SystemExit("[pyt] no pytest arguments given after --")

    bound = max(30, min(int(a.bound), CEILING))
    if a.bound > CEILING:
        print("[pyt] bound %d clamped to the %d s ceiling" % (a.bound, CEILING), flush=True)
    cwd = os.path.abspath(a.cwd)
    if not os.path.isdir(cwd):
        raise SystemExit("[pyt] cwd does not exist: %s" % cwd)

    use_plugin = {"yes": True, "no": False, "auto": not worktree_has_conftest_guard(cwd)}[a.plugin]
    argv = [VENV_PY, "-m", "pytest"]
    if use_plugin:
        argv += ["-p", "qaren_netguard"]
    joined = " ".join(rest)
    if "no:cacheprovider" not in joined:
        argv += ["-p", "no:cacheprovider"]
    if "no:randomly" not in joined:
        argv += ["-p", "no:randomly"]
    if not any(x.startswith("--timeout") for x in rest):
        argv += ["--timeout=%d" % a.per_test]
    if "-m" not in rest and not any(x.startswith("-m=") for x in rest):
        argv += ["-m", DEFAULT_MARK]
    argv += rest

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if use_plugin:
        prev = env.get("PYTHONPATH")
        env["PYTHONPATH"] = NETGUARD_DIR + (os.pathsep + prev if prev else "")

    log_path = os.path.abspath(a.log)
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    _acquire_tag_lock(a.tag)
    start_ts = time.time()
    start = now()
    status, rc = "OK", None
    with open(log_path, "wb") as log:
        log.write(("[pyt] %s tag=%s cwd=%s plugin=%s bound=%ds\n[pyt] argv=%s\n" % (
            start, a.tag, cwd, use_plugin, bound, json.dumps(argv))).encode("utf-8"))
        log.flush()
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        try:
            rc = proc.wait(timeout=bound)
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
            kill_tree(proc.pid)
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                pass
            rc = 124
    elapsed = time.time() - start_ts
    if status == "OK" and rc != 0:
        status = "FAIL"

    # compact echo
    try:
        with open(log_path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        lines = []
    summary, extras, failed = [], [], []
    for ln in lines:
        s = ln.strip()
        if SUMMARY_RE.search(s) or COLLECT_RE.search(s) or s.startswith("no tests ran"):
            summary.append(s)
        elif s.startswith("[netguard]") or s.startswith("[hermeticity]") or s.startswith("[netguard-ratchet]"):
            extras.append(s)
        elif s.startswith("FAILED ") or s.startswith("ERROR "):
            failed.append(s)
    print("[pyt] --- summary lines ---", flush=True)
    for s in summary[-3:]:
        print(s, flush=True)
    for s in extras[-6:]:
        print(s, flush=True)
    if failed:
        print("[pyt] --- FAILED/ERROR ids (%d) ---" % len(failed), flush=True)
        for s in failed[:60]:
            print(s, flush=True)
        if len(failed) > 60:
            print("[pyt] ... %d more in the log" % (len(failed) - 60), flush=True)
    if not summary:
        print("[pyt] --- no pytest summary line; last %d log lines ---" % a.tail, flush=True)
        for s in lines[-a.tail:]:
            print(s[:300], flush=True)
    if status == "TIMEOUT":
        print("[pyt] TIMEOUT: the process tree was killed after %ds. This is a MEASUREMENT FAILURE: re-run this ONE gate once, alone; if it times out again report it as NOT MEASURED. Never raise the bound." % bound, flush=True)
    final = "[pyt] tag=%s start=%s end=%s elapsed=%.0fs bound=%ds status=%s rc=%s log=%s" % (
        a.tag, start, now(), elapsed, bound, status, rc, log_path)
    print(final, flush=True)
    try:
        with open(LEDGER, "a", encoding="utf-8") as led:
            led.write(json.dumps({
                "start": start, "end": now(), "elapsed_s": round(elapsed, 1), "bound_s": bound,
                "status": status, "rc": rc, "tag": a.tag, "cwd": cwd, "plugin": use_plugin,
                "log": log_path, "args": rest, "summary": summary[-1] if summary else None,
                "netguard": [x for x in extras if x.startswith("[netguard]")][-1:] or None,
                "pid": os.getpid(),
            }) + "\n")
    except OSError as exc:
        print("[pyt] ledger write failed: %s" % exc, flush=True)
    sys.exit(rc if rc is not None else 1)


if __name__ == "__main__":
    main()
