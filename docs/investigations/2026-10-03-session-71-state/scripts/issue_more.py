"""issue_more.py get <n> <out-file> | comment <n> <body-file> | close <n> <body-file>  -- via pr_rest api()."""
import sys
from pr_rest import api, REPO

def main():
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "get":
        st, res = api("GET", f"/repos/{REPO}/issues/{a[1]}", None)
        if st != 200:
            raise SystemExit(f"get failed status={st} {str(res)[:300]}")
        open(a[2], "w", encoding="utf-8", newline="\n").write("# " + res["title"] + "\n\nstate: " + res["state"] + "\n\n" + (res.get("body") or ""))
        print("saved", a[2], "state", res["state"], "title", res["title"][:120].encode("ascii", "replace").decode())
    elif len(a) == 3 and a[0] == "comment":
        body = open(a[2], encoding="utf-8").read()
        st, res = api("POST", f"/repos/{REPO}/issues/{a[1]}/comments", {"body": body})
        if st != 201:
            raise SystemExit(f"comment failed status={st} {str(res)[:300]}")
        print("commented", res["html_url"])
    elif len(a) == 3 and a[0] == "close":
        body = open(a[2], encoding="utf-8").read()
        st, res = api("POST", f"/repos/{REPO}/issues/{a[1]}/comments", {"body": body})
        print("comment", st)
        st, res = api("PATCH", f"/repos/{REPO}/issues/{a[1]}", {"state": "closed"})
        print("closed", a[1], st, res.get("state") if isinstance(res, dict) else str(res)[:120])
    else:
        raise SystemExit(__doc__)

if __name__ == "__main__":
    main()
