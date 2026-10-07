import json, sys
from pr_rest import api, REPO
out = {"issues": [], "prs": []}
page = 1
while True:
    st, res = api("GET", f"/repos/{REPO}/issues?state=open&per_page=100&page={page}", None)
    if st != 200:
        raise SystemExit(f"list failed {st} {str(res)[:200]}")
    if not res:
        break
    for it in res:
        row = {"n": it["number"], "title": it["title"], "labels": [l["name"] for l in it.get("labels", [])], "created": it["created_at"][:10], "updated": it["updated_at"][:10], "body": (it.get("body") or "")}
        (out["prs"] if "pull_request" in it else out["issues"]).append(row)
    page += 1
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=True, indent=1)
print("open issues", len(out["issues"]), "open prs", len(out["prs"]))
for r in out["prs"]:
    print("PR", r["n"], r["title"][:100].encode("ascii", "replace").decode())
for r in out["issues"]:
    print(r["n"], r["created"], ",".join(r["labels"])[:30], "|", r["title"][:110].encode("ascii", "replace").decode())
