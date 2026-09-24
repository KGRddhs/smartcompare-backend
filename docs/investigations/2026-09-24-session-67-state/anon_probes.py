"""Anon-key probes for the 037/040/038 apply (prints status codes and short bodies only; never a key)."""
import io
import json
import os
import sys
import urllib.error
import urllib.request

from dotenv import dotenv_values

env = dotenv_values("C:/Users/SynAckITPC/Documents/AI/smartcompare/.env")
URL = (env.get("SUPABASE_URL") or "").strip().rstrip("/")
KEY = (env.get("SUPABASE_ANON_KEY") or "").strip()
assert URL.startswith("https://") and len(KEY) > 20, "env not loaded"
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}


def call(label, method, path, body=None, extra=None):
    req = urllib.request.Request(URL + path, method=method, headers={**H, **(extra or {})},
                                 data=(json.dumps(body).encode() if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()[:200].decode("utf-8", "replace")
            print(f"{label}: HTTP {r.status} content-range={r.headers.get('content-range')} body={raw!r}")
    except urllib.error.HTTPError as e:
        raw = e.read()[:220].decode("utf-8", "replace")
        print(f"{label}: HTTP {e.code} body={raw!r}")
    except Exception as e:  # noqa: BLE001
        print(f"{label}: {type(e).__name__}: {e}")


tag = sys.argv[1] if len(sys.argv) > 1 else "probe"
print("==", tag, "==")
# GET on an RPC runs in a read-only transaction: it cannot mutate (25006 = anon passed EXECUTE and hit the DELETE)
call("GET  rpc/cleanup_expired_ratings", "GET", "/rest/v1/rpc/cleanup_expired_ratings")
# nil uuid: if the call DOES succeed it deletes nothing
call("POST rpc/delete_user_cascade(nil)", "POST", "/rest/v1/rpc/delete_user_cascade",
     {"target_user_id": "00000000-0000-0000-0000-000000000000"})
call("POST rpc/increment_lifetime_comparisons(nil)", "POST", "/rest/v1/rpc/increment_lifetime_comparisons",
     {"p_user_id": "00000000-0000-0000-0000-000000000000"})
call("HEAD user_events count=exact", "HEAD", "/rest/v1/user_events?select=id",
     extra={"Prefer": "count=exact", "Range": "0-0"})
call("GET  users.terms_accepted_at", "GET", "/rest/v1/users?select=terms_accepted_at&limit=1")
