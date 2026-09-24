"""Fetch the failing GitHub Actions job log for a PR's head sha (token via git credential fill, never printed).
  ci_logs.py <pr> [job-name-substring]
"""
import json, re, sys, urllib.request, urllib.error
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import pr_rest

REPO = pr_rest.REPO
def get(path):
    st, body = pr_rest.api("GET", path)
    return st, body

def main(n, want="backend-tests"):
    st, pr = get(f"/repos/{REPO}/pulls/{n}")
    sha = pr["head"]["sha"]
    st, cr = get(f"/repos/{REPO}/commits/{sha}/check-runs?per_page=50")
    runs = cr.get("check_runs", [])
    for r in runs:
        print(f"check-run {r['name']}: {r.get('status')}/{r.get('conclusion')} id={r['id']}")
    bad = [r for r in runs if want in r["name"] and r.get("conclusion") not in ("success", "skipped", "neutral", None)]
    for r in bad:
        job_id = r["id"]
        url = f"https://api.github.com/repos/{REPO}/actions/jobs/{job_id}/logs"
        req = urllib.request.Request(url, headers={"Authorization": "token " + pr_rest.token(), "Accept": "application/vnd.github+json", "User-Agent": "qaren-pr-rest"})
        class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return urllib.request.Request(newurl, headers={"User-Agent": "qaren-pr-rest"})
        opener = urllib.request.build_opener(NoAuthRedirect())
        try:
            with opener.open(req, timeout=300) as resp:
                text = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            print("log fetch failed", e.code, e.read()[:200]); continue
        out = f"ci_log_{n}_{job_id}.txt"
        open(out, "w", encoding="utf-8").write(text)
        lines = text.splitlines()
        print(f"--- {r['name']} log: {len(lines)} lines -> {out}")
        # print FAILED / ERROR summary lines and the short test summary
        keep = [l for l in lines if re.search(r"FAILED|ERROR |Error|error:|passed|failed|deselected|short test summary|assert", l)]
        for l in keep[-80:]:
            print(l[:300])

if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "backend-tests")
