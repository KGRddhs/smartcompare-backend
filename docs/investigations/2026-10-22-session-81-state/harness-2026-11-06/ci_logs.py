"""Fetch a failing GitHub Actions job log for a commit (REST; the token from the git
credential helper via pr_rest.token(), never printed).

  ci_logs.py <head-sha> <job-name-substring> [tail-lines]

Prints the job id / conclusion, then the matching 'FAIL' / 'Tests:' / error lines and
the log tail. The log redirect target (a signed blob URL) is fetched WITHOUT the auth
header, as GitHub documents.
"""
import json
import re
import sys
import urllib.error
import urllib.request

import pr_rest

REPO = pr_rest.REPO


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _get(path, raw=False):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": "Bearer " + pr_rest.token(),
            "Accept": "application/vnd.github+json",
            "User-Agent": "s82-ci-logs",
        },
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=120) as r:
            body = r.read()
            return r.status, dict(r.headers), body
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def main():
    sha, needle = sys.argv[1], sys.argv[2]
    tail_n = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    st, _, body = _get(f"/repos/{REPO}/commits/{sha}/check-runs?per_page=50")
    runs = json.loads(body.decode("utf-8")).get("check_runs", [])
    hit = [c for c in runs if needle.lower() in c["name"].lower()]
    if not hit:
        print("no check-run matching", needle, "among", [c["name"] for c in runs])
        return 2
    c = hit[0]
    print(f"check-run {c['name']} id={c['id']} status={c['status']} conclusion={c['conclusion']} url={c.get('html_url')}")
    job_id = c["id"]  # a GitHub Actions check-run id == the job id
    st, hdr, body = _get(f"/repos/{REPO}/actions/jobs/{job_id}/logs")
    if st in (301, 302, 303, 307) and hdr.get("Location"):
        with urllib.request.urlopen(urllib.request.Request(hdr["Location"], headers={"User-Agent": "s82-ci-logs"}), timeout=180) as r:
            text = r.read().decode("utf-8", "replace")
    elif st == 200:
        text = body.decode("utf-8", "replace")
    else:
        print("log fetch status", st, body[:300])
        return 3
    lines = text.splitlines()
    print("log lines:", len(lines))
    pat = re.compile(r"(FAIL |✕|Tests:|Test Suites:|Error:|error |ELIFECYCLE|exit code|Process completed|Snapshot|timed out|TIMEOUT)")
    print("--- matching lines")
    shown = 0
    for ln in lines:
        if pat.search(ln):
            print(ln[:260])
            shown += 1
            if shown > 80:
                print("... (more)")
                break
    print("--- tail")
    for ln in lines[-tail_n:]:
        print(ln[:260])
    return 0


if __name__ == "__main__":
    sys.exit(main())
