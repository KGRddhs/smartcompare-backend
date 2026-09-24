"""Fallback route: apply 040 -> 037 -> 038 through the Supabase Management API.

Usage (Ahmed's own terminal; the token is read from the environment and never printed):
    set SUPABASE_ACCESS_TOKEN=<personal access token from supabase.com/dashboard/account/tokens>
    python apply_migrations_mgmt_api.py census          # read-only: the 040 census + 037 BEFORE checks
    python apply_migrations_mgmt_api.py apply 040       # applies one file, then re-runs its verification
    python apply_migrations_mgmt_api.py apply 037
    python apply_migrations_mgmt_api.py apply 038
Every result is printed as JSON rows; nothing secret is in the output.
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

REPO = "C:/Users/SynAckITPC/Documents/AI/smartcompare"
PROJECT_REF = "qulajmyxdbdkchvecmvc"
API = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
FILES = {
    "040": "migrations/040_revoke_cleanup_expired_ratings.sql",
    "037": "migrations/037_security_definer_grants_and_rls.sql",
    "038": "migrations/038_users_consent_capture.sql",
}
Q = {
    "040_fn": """SELECT p.oid::regprocedure AS signature, p.prosecdef, p.proacl, left(pg_get_functiondef(p.oid), 4000) AS definition
                 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                 WHERE n.nspname = 'public' AND p.proname = 'cleanup_expired_ratings'""",
    "040_census": """SELECT p.oid::regprocedure AS signature, p.proacl
                     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                     WHERE n.nspname = 'public' AND p.prosecdef AND has_function_privilege('anon', p.oid, 'EXECUTE')
                     ORDER BY 1""",
    "037_rls": """SELECT c.relowner::regrole AS owner, c.relrowsecurity, c.relforcerowsecurity
                  FROM pg_class c WHERE c.oid = 'public.user_events'::regclass""",
    "037_policies": """SELECT policyname, permissive, cmd, roles, qual, with_check
                       FROM pg_policies WHERE schemaname = 'public' AND tablename = 'user_events'""",
    "037_acl": """SELECT p.proname, p.proacl FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                  WHERE n.nspname = 'public' AND p.proname IN ('delete_user_cascade', 'increment_lifetime_comparisons',
                  'resolve_referral_code', 'home_savings_aggregate')""",
    "038_cols": """SELECT column_name, data_type FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'users'
                   AND column_name IN ('terms_accepted_at', 'terms_version', 'age_attested_at')""",
}
VERIFY = {"040": ["040_fn", "040_census"], "037": ["037_acl", "037_rls", "037_policies"], "038": ["038_cols"]}


def token():
    t = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if not t:
        sys.exit("SUPABASE_ACCESS_TOKEN is not set in this shell")
    return t


def run(sql):
    req = urllib.request.Request(API, method="POST", data=json.dumps({"query": sql}).encode(),
                                 headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:800].decode("utf-8", "replace")


def show(label, res):
    st, body = res
    print(f"--- {label}: HTTP {st}")
    print(json.dumps(body, indent=1, default=str)[:6000] if not isinstance(body, str) else body)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "census"
    if mode == "census":
        for k in ("040_fn", "040_census", "037_rls", "037_policies", "037_acl", "038_cols"):
            show("BEFORE " + k, run(Q[k]))
        return
    if mode == "apply":
        n = sys.argv[2]
        sql = io.open(f"{REPO}/{FILES[n]}", encoding="utf-8").read().replace("\r\n", "\n")
        for k in VERIFY[n]:
            show(f"BEFORE {n} {k}", run(Q[k]))
        show(f"APPLY {n}", run(sql))
        for k in VERIFY[n]:
            show(f"AFTER {n} {k}", run(Q[k]))
        return
    sys.exit("mode must be census or apply <040|037|038>")


if __name__ == "__main__":
    main()
