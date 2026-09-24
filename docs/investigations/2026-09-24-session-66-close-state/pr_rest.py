"""GitHub REST helper that tolerates a slow TLS path (gh's Go client caps the
handshake at 10 s and dies on this box tonight). Token comes from the git
credential helper and is NEVER printed.

  pr_rest.py create <head-branch> <title> <body-file>
  pr_rest.py status <pr>
  pr_rest.py watch  <pr> [max_minutes]     # poll; merge when every check-run is green
  pr_rest.py merge  <pr>
"""
import datetime
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = "KGRddhs/smartcompare-backend"
OWNER = REPO.split("/")[0]
_TOK = None


def token():
    global _TOK
    if _TOK:
        return _TOK
    out = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True, timeout=600,
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            _TOK = line[len("password="):].strip()
            return _TOK
    raise SystemExit("no github token from git credential fill")


def api(method, path, body=None, tries=4):
    url = "https://api.github.com" + path
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for i in range(tries):
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Authorization": "token " + token(),
                "Accept": "application/vnd.github+json",
                "User-Agent": "qaren-pr-rest",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, (json.loads(raw) if raw else None)
            except Exception:
                return e.code, {"raw": raw[:300].decode("utf-8", "replace")}
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
            print(f"  api {method} {path}: {last} (try {i + 1}/{tries})", flush=True)
            time.sleep(20)
    return None, {"error": last}


def now():
    return datetime.datetime.now().strftime("%H:%M:%S")


def find_open(head):
    st, prs = api("GET", f"/repos/{REPO}/pulls?state=open&head={OWNER}:{head}&per_page=5")
    if st == 200 and prs:
        return prs[0]["number"], prs[0]["html_url"]
    return None, None


def cmd_create(head, title, bodyfile):
    n, url = find_open(head)
    if n:
        print(f"existing PR #{n} {url}")
        print(f"PR number={n}")
        return 0
    body = open(bodyfile, encoding="utf-8").read()
    st, pr = api("POST", f"/repos/{REPO}/pulls", {"title": title, "head": head, "base": "main", "body": body})
    if st == 201:
        print(f"created PR #{pr['number']} {pr['html_url']}")
        print(f"PR number={pr['number']}")
        return 0
    # a timed-out POST may have created it anyway
    n, url = find_open(head)
    if n:
        print(f"PR #{n} exists after retry {url}")
        print(f"PR number={n}")
        return 0
    print(f"PR CREATE FAILED status={st} body={json.dumps(pr)[:400]}")
    return 1


def status(n):
    st, pr = api("GET", f"/repos/{REPO}/pulls/{n}")
    if st != 200:
        return None
    sha = pr["head"]["sha"]
    st2, cr = api("GET", f"/repos/{REPO}/commits/{sha}/check-runs?per_page=50")
    runs = (cr or {}).get("check_runs", []) if st2 == 200 else []
    total = len(runs)
    done = [r for r in runs if r.get("status") == "completed"]
    ok = [r for r in done if r.get("conclusion") in ("success", "skipped", "neutral")]
    bad = [r for r in done if r.get("conclusion") not in ("success", "skipped", "neutral")]
    return {
        "number": n, "state": pr["state"], "merged": pr.get("merged"), "sha": sha[:8],
        "mergeable": pr.get("mergeable"), "mergeable_state": pr.get("mergeable_state"),
        "total": total, "completed": len(done), "ok": len(ok),
        "bad": [(r["name"], r.get("conclusion")) for r in bad],
        "pending": [r["name"] for r in runs if r.get("status") != "completed"],
    }


def cmd_status(n):
    s = status(n)
    print(now(), json.dumps(s))
    return 0


def cmd_merge(n):
    st, res = api("PUT", f"/repos/{REPO}/pulls/{n}/merge", {"merge_method": "merge"})
    print(now(), f"merge status={st} {json.dumps(res)[:300]}")
    return 0 if st == 200 else 1


def cmd_watch(n, max_minutes=120, min_checks=6):
    deadline = time.time() + max_minutes * 60
    while time.time() < deadline:
        s = status(n)
        if s is None:
            print(now(), "status unavailable; retrying", flush=True)
            time.sleep(60)
            continue
        print(now(), json.dumps(s), flush=True)
        if s["merged"] or s["state"] == "closed":
            print(f"PR #{n} {'MERGED' if s['merged'] else 'CLOSED'}")
            return 0
        if s["bad"]:
            print(f"PR #{n} HAS FAILED CHECKS: {s['bad']}")
            return 2
        if s["total"] >= min_checks and s["completed"] == s["total"] and s["ok"] == s["total"] \
                and s["mergeable_state"] in ("clean", "has_hooks", "unstable"):
            if cmd_merge(n) == 0:
                st, pr = api("GET", f"/repos/{REPO}/pulls/{n}")
                print(f"PR #{n} MERGED; merge sha {(pr or {}).get('merge_commit_sha', '?')[:8]}")
                return 0
        time.sleep(120)
    print(f"PR #{n} watch timed out")
    return 3


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "create":
        sys.exit(cmd_create(a[1], a[2], a[3]))
    if a[0] == "status":
        sys.exit(cmd_status(int(a[1])))
    if a[0] == "merge":
        sys.exit(cmd_merge(int(a[1])))
    if a[0] == "watch":
        sys.exit(cmd_watch(int(a[1]), int(a[2]) if len(a) > 2 else 120))
    raise SystemExit(__doc__)
