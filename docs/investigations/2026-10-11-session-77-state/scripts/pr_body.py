"""Read or replace a PR description through pr_rest.api (token never printed).
  pr_body.py get <pr> <outfile>
  pr_body.py set <pr> <bodyfile>
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import pr_rest

cmd, n, path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
if cmd == "get":
    st, pr = pr_rest.api("GET", f"/repos/{pr_rest.REPO}/pulls/{n}")
    assert st == 200, st
    open(path, "w", encoding="utf-8", newline="\n").write(pr.get("body") or "")
    print("title:", pr["title"])
    print("head:", pr["head"]["ref"], pr["head"]["sha"][:8], "| state:", pr["state"], "| draft:", pr.get("draft"))
    print("body chars:", len(pr.get("body") or ""))
elif cmd == "set":
    body = open(path, encoding="utf-8").read()
    st, pr = pr_rest.api("PATCH", f"/repos/{pr_rest.REPO}/pulls/{n}", {"body": body})
    print("PATCH status", st, "| body chars now", len((pr or {}).get("body") or ""))
else:
    raise SystemExit(__doc__)
