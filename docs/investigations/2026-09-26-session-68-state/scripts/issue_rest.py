"""issue_rest.py create <title> <body-file> [label,label]  -- files a GitHub issue via pr_rest's api()."""
import sys
from pr_rest import api, REPO

def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[0] != "create":
        raise SystemExit(__doc__)
    title, bodyfile = a[1], a[2]
    labels = [x for x in (a[3].split(",") if len(a) > 3 else []) if x]
    body = open(bodyfile, encoding="utf-8").read()
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    st, res = api("POST", f"/repos/{REPO}/issues", payload)
    if st != 201:
        raise SystemExit(f"issue create failed status={st} {str(res)[:300]}")
    print(f"created issue #{res['number']} {res['html_url']}")

if __name__ == "__main__":
    main()
