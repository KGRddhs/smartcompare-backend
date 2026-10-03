import datetime as dt, math
from pr_rest import api, REPO
st, runs = api("GET", f"/repos/{REPO}/actions/runs?per_page=100", None)
today = "2026-10-03"
todays = [r for r in runs.get("workflow_runs", []) if r.get("created_at", "").startswith(today)]
print("runs today:", len(todays), "of", len(runs.get("workflow_runs", [])), "fetched")
rid = runs["workflow_runs"][0]["id"]
st, jobs = api("GET", f"/repos/{REPO}/actions/runs/{rid}/jobs", None)
raw = 0.0; billed = 0
for j in jobs.get("jobs", []):
    a = dt.datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))
    b = dt.datetime.fromisoformat(j["completed_at"].replace("Z", "+00:00"))
    m = (b - a).total_seconds() / 60
    raw += m; billed += math.ceil(m)
    print(" job", j["name"], round(m, 1), "min")
print("job-minutes per run: raw", round(raw, 1), "| billed (ceil per job)", billed, "| today x runs =", billed * len(todays))
