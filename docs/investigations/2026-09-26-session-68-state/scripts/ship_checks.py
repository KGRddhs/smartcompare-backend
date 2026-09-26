"""ship_checks.py -- the orchestrator's mechanical pre-commit gate for one unit worktree.

  ship_checks.py <worktree> [--set .qa-s68/ci_order_set.txt] [--flag NAME] [--no-plugin]
                 [--expect path=sha256 ...] [--timeout 60]

Steps (each printed, exit 1 on the first failure):
  1. git status --short (informational) and sha256 of every changed/untracked file;
     any --expect path=sha mismatch fails.
  2. ruff --select E9,F63,F7,F82 + py_compile on every changed/untracked .py.
  3. the CI-order set (sorted) in ONE process with CI's deselects, --timeout, under
     the process-wide guard plugin (unless --no-plugin: for the hermeticity unit,
     whose conftest installs the guard). With --flag NAME the set runs twice
     (NAME unset, NAME=true).
Never commits, never touches the index. Token-free, network-free.
"""
import argparse
import hashlib
import os
import subprocess
import sys

VENV = "C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
NETGUARD = ("C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/"
            "b1819d0c-d9c5-466a-ba0d-b82774c624db/scratchpad/netguard")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def run(cmd, cwd, env=None, check=True):
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if check and r.returncode != 0:
        print(out[-6000:])
        raise SystemExit("FAILED: " + " ".join(cmd[:4]))
    return r.returncode, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree")
    ap.add_argument("--set", default=".qa-s68/ci_order_set.txt")
    ap.add_argument("--flag", default=None)
    ap.add_argument("--no-plugin", action="store_true")
    ap.add_argument("--expect", nargs="*", default=[])
    ap.add_argument("--timeout", default="60")
    ap.add_argument("--skip-tests", action="store_true")
    a = ap.parse_args()
    wt = a.worktree

    rc, st = run(["git", "status", "--short"], wt)
    print(st)
    changed = []
    for line in st.splitlines():
        path = line[3:].strip()
        if not path or line.startswith(" D") or line.startswith("D "):
            continue
        if path.startswith(".qa-"):
            continue
        changed.append(path)
    # committed-but-unmerged work: everything on this branch beyond origin/main
    rc, committed = run(["git", "diff", "--name-only", "--diff-filter=ACM", "origin/main", "HEAD"], wt, check=False)
    for p in committed.splitlines():
        p = p.strip()
        if p and p not in changed and not p.startswith(".qa-"):
            changed.append(p)
    print("changed/untracked files:")
    shas = {}
    for p in changed:
        full = os.path.join(wt, p)
        if os.path.isfile(full):
            shas[p] = sha(full)
            print("  %s %s" % (p, shas[p]))
    bad = []
    for e in a.expect:
        p, _, s = e.partition("=")
        if shas.get(p) != s:
            bad.append((p, s, shas.get(p)))
    if bad:
        for p, want, got in bad:
            print("SHA MISMATCH %s expected %s got %s" % (p, want, got))
        raise SystemExit("FAILED: sha expectations")

    pys = [p for p in changed if p.endswith(".py") and os.path.isfile(os.path.join(wt, p))]
    if pys:
        run([VENV, "-m", "ruff", "check", "--select", "E9,F63,F7,F82", "--no-cache"] + pys, wt)
        run([VENV, "-m", "py_compile"] + pys, wt)
        print("ruff + py_compile clean on %d files" % len(pys))
    if a.skip_tests:
        return
    setp = os.path.join(wt, a.set)
    files = sorted(l.strip() for l in open(setp, encoding="utf-8") if l.strip() and not l.startswith("#"))
    desel = []
    for l in open(os.path.join(wt, "tests/.pre_impl_failures.txt"), encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#"):
            desel.append("--deselect=" + l)
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("ENABLE_PRICE_PARSE_OFFLOAD", None)
    env.pop("PRICE_PARSE_MAX_WORKERS", None)
    plugin = []
    if not a.no_plugin:
        env["PYTHONPATH"] = NETGUARD + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        plugin = ["-p", "qaren_netguard"]
    states = [None] if not a.flag else [None, "true"]
    for state in states:
        e2 = dict(env)
        if state is not None:
            e2[a.flag] = state
        label = ("%s=%s" % (a.flag, state)) if state is not None else "flag unset"
        cmd = [VENV, "-m", "pytest"] + plugin + ["-p", "no:cacheprovider", "-p", "no:randomly",
               "--timeout=" + a.timeout, "-m", "not (live_unit or live_db or integration)", "-q", "-rfE"] + desel + files
        rc, out = run(cmd, wt, env=e2, check=False)
        tail = [l for l in out.splitlines() if l.startswith("FAILED") or l.startswith("ERROR") or "passed" in l or "failed" in l or l.startswith("[netguard]")]
        print("--- CI-order set (%d files) [%s] rc=%d" % (len(files), label, rc))
        for l in tail[-40:]:
            print("   ", l[:300])
        if rc != 0:
            raise SystemExit("FAILED: CI-order set red [%s]" % label)
    print("SHIP CHECKS PASSED")


if __name__ == "__main__":
    main()
