"""Read-only schema METADATA of the live Supabase project (session 71, U8b).

Fetches the PostgREST OpenAPI document (GET <SUPABASE_URL>/rest/v1/) and prints
column NAMES, types, NOT NULL flags, defaults and foreign-key notes. It reads
NO table row and prints NO credential, URL or project ref.

Run:  railway run -s web python <this file>
"""
import json
import os
import re
import sys
import urllib.request

url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
key = os.environ.get("SUPABASE_SERVICE_KEY") or ""
if not url or not key:
    print("missing SUPABASE_URL or SUPABASE_SERVICE_KEY in the injected environment")
    sys.exit(2)

req = urllib.request.Request(
    url + "/rest/v1/",
    headers={"apikey": key, "Authorization": "Bearer " + key, "Accept": "application/openapi+json"},
)
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
except Exception as exc:  # noqa: BLE001 - print the type only, never the text (it can carry the URL)
    print("openapi fetch failed:", type(exc).__name__)
    sys.exit(1)

defs = doc.get("definitions") or {}
print("tables/views exposed:", len(defs))

FK_RE = re.compile(r"<fk table='([^']+)' column='([^']+)'/>")
USERISH = re.compile(
    r"(^|_)(user|users|referrer|invitee|redeemed_by|owner|created_by)(_id)?$|email|fingerprint|push_token|ip_address|anon_id|device_id|phone|full_name|display_name",
    re.I,
)


def describe(table):
    d = defs.get(table)
    if d is None:
        print("TABLE", table, ": NOT EXPOSED / ABSENT")
        return
    required = set(d.get("required") or [])
    print("TABLE", table, "columns:", len(d.get("properties") or {}))
    for name, p in (d.get("properties") or {}).items():
        fk = FK_RE.findall(p.get("description") or "")
        pk = "PK" if "<pk/>" in (p.get("description") or "") else ""
        default = p.get("default")
        dflt = "" if default is None else " default=" + str(default)[:40]
        print(
            "   %-28s %-28s %s%s%s%s"
            % (
                name,
                (p.get("format") or p.get("type") or "?"),
                "NOT NULL" if name in required else "null ok",
                dflt,
                " " + pk if pk else "",
                (" FK->" + ",".join(t + "." + c for t, c in fk)) if fk else "",
            )
        )


describe("users")
print()
print("user-referencing columns in every exposed table (name match or FK to users):")
for table in sorted(defs):
    props = defs[table].get("properties") or {}
    hits = []
    for name, p in props.items():
        fk = FK_RE.findall(p.get("description") or "")
        if USERISH.search(name) or any(t == "users" for t, _ in fk):
            hits.append(name + ("(FK->" + ",".join(t + "." + c for t, c in fk) + ")" if fk else ""))
    if hits:
        print("  ", table, ":", ", ".join(hits))
print()
print("all exposed tables/views:", ", ".join(sorted(defs)))
