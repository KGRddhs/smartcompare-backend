import sys
from pr_rest import api, REPO
st, u = api("GET", "/user", None)
print("user", st, u.get("login"), "plan", (u.get("plan") or {}).get("name"))
st, r = api("GET", f"/repos/{REPO}", None)
print("repo", st, "private", r.get("private"), "visibility", r.get("visibility"), "default", r.get("default_branch"), "forks", r.get("forks_count"), "stars", r.get("stargazers_count"))
st, b = api("GET", f"/repos/{REPO}/branches/main/protection", None)
print("protection", st, "required checks:", ((b.get("required_status_checks") or {}).get("contexts") if st == 200 else str(b)[:160]))
st, rs = api("GET", f"/repos/{REPO}/rulesets", None)
print("rulesets", st, [x.get("name") for x in rs] if st == 200 else str(rs)[:120])
st, runs = api("GET", f"/repos/{REPO}/actions/runs?per_page=6&status=completed", None)
if st == 200:
    for run in runs.get("workflow_runs", [])[:6]:
        rid = run["id"]
        st2, t = api("GET", f"/repos/{REPO}/actions/runs/{rid}/timing", None)
        ms = (t.get("run_duration_ms") if st2 == 200 else None)
        bill = t.get("billable", {}) if st2 == 200 else {}
        mins = sum((v.get("total_ms", 0) for v in bill.values())) / 60000 if bill else None
        print("run", rid, run.get("name"), run.get("head_branch"), run.get("conclusion"), "wall min", round((ms or 0)/60000, 1), "billable min", round(mins, 1) if mins is not None else "n/a")
st, bl = api("GET", f"/users/{REPO.split('/')[0]}/settings/billing/actions", None)
print("billing actions", st, {k: bl.get(k) for k in ("total_minutes_used", "included_minutes", "total_paid_minutes_used")} if st == 200 else str(bl)[:160])
