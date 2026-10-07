import json, sys, re, collections
rows = []
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line:
        continue
    try:
        rows.append(json.loads(line))
    except Exception:
        pass
print("rows", len(rows))
if rows:
    print("keys", sorted(rows[0].keys()))
def g(r, *names):
    for n in names:
        if n in r and r[n] not in (None, ""):
            return r[n]
    return ""
ts = sorted(str(g(r, "timestamp", "time")) for r in rows)
print("span", ts[0][:19] if ts else None, "->", ts[-1][:19] if ts else None)
def tmpl(p):
    p = str(p).split("?")[0]
    p = re.sub(r"/[0-9a-fA-F-]{16,}", "/<id>", p)
    p = re.sub(r"/text/prices/.+", "/text/prices/<product>", p)
    return p[:70]
def uaclass(u):
    u = str(u).lower()
    if not u:
        return "none"
    for k, v in (("okhttp", "mobile-android"), ("cfnetwork", "mobile-ios"), ("darwin", "mobile-ios"), ("expo", "mobile-expo"), ("qaren", "app"), ("myez", "app"), ("curl", "curl"), ("python", "python"), ("bot", "bot"), ("spider", "bot"), ("crawl", "bot"), ("mozilla", "browser"), ("go-http", "go"), ("zgrab", "scanner")):
        if k in u:
            return v
    return "other"
by = collections.Counter()
ua = collections.Counter()
day = collections.Counter()
api = collections.Counter()
for r in rows:
    path = g(r, "path", "url")
    st = g(r, "httpStatus", "status", "statusCode")
    u = uaclass(g(r, "userAgent", "user_agent"))
    by[(tmpl(path), str(st))] += 1
    ua[u] += 1
    day[str(g(r, "timestamp", "time"))[:10]] += 1
    if "/api/v1/" in str(path):
        api[(tmpl(path), str(st), u)] += 1
print("per day", dict(sorted(day.items())))
print("ua classes", ua.most_common())
print("--- top path/status")
for (p, s), n in by.most_common(25):
    print(f"{n:5d} {s:4s} {p}")
print("--- /api/v1 by path/status/ua")
for (p, s, u), n in sorted(api.items(), key=lambda x: -x[1])[:40]:
    print(f"{n:5d} {s:4s} {u:14s} {p}")
