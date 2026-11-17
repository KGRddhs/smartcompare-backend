"""INC-SEC-1 DATABASE-ACCESS: the frozen static rows (RED at base afde168f).

The unit adds migrations/055_app_user_access_tightening.sql (app-role policies,
privileges and a second users row trigger for six profile columns), its rollback
migrations/rollback/055_app_user_access_tightening.sql, the read-only catalog check
docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql, and four server
changes: C1 (create_share_token has no user branch), C2 (save_feedback writes with the
server client), C2b (feedback keeps a comparison_id only when the caller may name it)
and C3 (ENABLE_REFERRAL_SAME_DEVICE_CHECK, default OFF: the invitee select gains the
device hash only when ON).

Nothing here touches a database: every row is a text or AST scan of repo files, or a
call of a server function with in-memory fakes. A row whose file or symbol is missing
fails on an AssertionError (never an import error). Rows named *_pin_* are PIN rows,
green at base. Synthetic ids only. Pure ASCII, LF.
"""

from __future__ import annotations

import ast
import asyncio
import base64
import hashlib
import importlib
import logging
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / "migrations"
RB = MIG / "rollback"
NAME = "055_app_user_access_tightening.sql"
UP = MIG / NAME
DOWN = RB / NAME
CHECK = (
    ROOT
    / "docs"
    / "investigations"
    / "2026-11-17-session-96-state"
    / "APPLY_055_CHECK.sql"
)
M054_UP = MIG / "054_users_entitlement_guard.sql"
M054_DOWN = RB / "054_users_entitlement_guard.sql"
M054_CHECK = (
    ROOT
    / "docs"
    / "investigations"
    / "2026-11-17-session-97-state"
    / "APPLY_054_CHECK.sql"
)

# X01: the merged 054 blobs at afde168f (sha256 over the LF bytes, base64).
M054_UP_LF_SHA256 = "dzEHMoM39ECzRbswCy/grDuWCAvspNfDlPGht/vBbSo="
M054_DOWN_LF_SHA256 = "TkmljMAY+mTld2UlAUpcgL5+qMK3+OyYDO/ON4S91Vk="
M054_CHECK_LF_SHA256 = "UWhFixGKdV+L7StjzH1bcH4Tdl4X4RjGhylpmY6ecHQ="

FUNC = "public.users_profile_guard()"
TRIGGER = "users_profile_guard"
MESSAGE = "users profile columns are server-managed (INC-SEC-1)"
MESSAGE_054 = "users entitlement columns are server-managed (INC-T1b)"

SIX = (
    "email",
    "created_at",
    "attribution_source",
    "last_comparison_at",
    "behavior_profile",
    "demographics_profile",
)
INSERT_RULES = {
    "email": "IS NOT NULL",
    "created_at": "IS DISTINCT FROM now()",
    "attribution_source": "IS NOT NULL",
    "last_comparison_at": "IS NOT NULL",
    "behavior_profile": "IS DISTINCT FROM '{}'::jsonb",
    "demographics_profile": "IS NOT NULL",
}
ELEVEN_054 = (
    "subscription_tier",
    "subscription_expires_at",
    "lifetime_comparisons_used",
    "referral_bonus_comparisons_this_month",
    "referral_bonus_reset_at",
    "lifetime_invites_consumed",
    "device_fingerprint_hash",
    "referral_code",
    "terms_accepted_at",
    "terms_version",
    "age_attested_at",
)

# 054's role test (tests/test_inc_t1b_users_entitlement_guard.py:81-88), compacted.
ROLE_TEST = (
    "v_request_role := coalesce( "
    "nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', "
    "nullif(current_setting('request.jwt.claim.role', true), '') ); "
    "IF current_user NOT IN ('anon', 'authenticated') "
    "AND (v_request_role IS NULL OR v_request_role = 'service_role') THEN "
    "RETURN NEW; END IF;"
)

TEN_TABLES = (
    "admin_audit_log",
    "comparison_feedback",
    "comparisons",
    "products",
    "rating_cache",
    "referral_invites",
    "search_logs",
    "user_events",
    "user_usage",
    "users",
)

# The 26 measured policies on the ten tables (catalog policies.txt, 2026-11-17):
# (table, name) -> (cmd, role, USING, WITH CHECK).
CENSUS = {
    ("admin_audit_log", "audit_insert"): ("INSERT", "public", None, "true"),
    ("comparison_feedback", "Users can insert own feedback"): (
        "INSERT",
        "public",
        None,
        "((auth.uid() = user_id) OR (user_id IS NULL))",
    ),
    ("comparison_feedback", "Users can read own feedback"): (
        "SELECT",
        "public",
        "(auth.uid() = user_id)",
        None,
    ),
    ("comparison_feedback", "feedback_insert"): (
        "INSERT",
        "public",
        None,
        "((auth.uid() = user_id) OR (user_id IS NULL))",
    ),
    ("comparison_feedback", "feedback_select"): (
        "SELECT",
        "public",
        "(auth.uid() = user_id)",
        None,
    ),
    ("comparisons", "comparisons_delete"): (
        "DELETE",
        "public",
        "(auth.uid() = user_id)",
        None,
    ),
    ("comparisons", "comparisons_insert"): (
        "INSERT",
        "public",
        None,
        "(auth.uid() = user_id)",
    ),
    ("comparisons", "comparisons_select"): (
        "SELECT",
        "public",
        "((auth.uid() = user_id) OR (share_token IS NOT NULL))",
        None,
    ),
    ("comparisons", "comparisons_update"): (
        "UPDATE",
        "public",
        "(auth.uid() = user_id)",
        None,
    ),
    ("products", "products_service_role_all"): ("ALL", "service_role", "true", "true"),
    ("rating_cache", "Service role has full access to rating_cache"): (
        "ALL",
        "public",
        "true",
        None,
    ),
    ("referral_invites", "referral_invites_select_own"): (
        "SELECT",
        "authenticated",
        "((referrer_user_id = auth.uid()) OR (redeemed_by_user_id = auth.uid()))",
        None,
    ),
    ("search_logs", "search_logs_insert"): (
        "INSERT",
        "public",
        None,
        "((auth.uid() = user_id) OR (user_id IS NULL))",
    ),
    ("search_logs", "search_logs_select"): (
        "SELECT",
        "public",
        "(auth.uid() = user_id)",
        None,
    ),
    ("user_events", "Users can insert own events"): (
        "INSERT",
        "public",
        None,
        "((auth.uid() = user_id) OR (user_id IS NULL))",
    ),
    ("user_events", "events_insert"): (
        "INSERT",
        "public",
        None,
        "((auth.uid() = user_id) OR (user_id IS NULL))",
    ),
    ("user_events", "events_select"): (
        "SELECT",
        "public",
        "(auth.uid() = user_id)",
        None,
    ),
    ("user_usage", "usage_insert"): (
        "INSERT",
        "public",
        None,
        "(auth.uid() = user_id)",
    ),
    ("user_usage", "usage_select"): (
        "SELECT",
        "public",
        "(auth.uid() = user_id)",
        None,
    ),
    ("user_usage", "usage_update"): (
        "UPDATE",
        "public",
        "(auth.uid() = user_id)",
        None,
    ),
    ("users", "Service role full access"): (
        "ALL",
        "public",
        "(auth.role() = 'service_role'::text)",
        None,
    ),
    ("users", "Users can read own data"): (
        "SELECT",
        "public",
        "(auth.uid() = id)",
        None,
    ),
    ("users", "Users can update own data"): (
        "UPDATE",
        "public",
        "(auth.uid() = id)",
        None,
    ),
    ("users", "users_insert"): ("INSERT", "public", None, "(auth.uid() = id)"),
    ("users", "users_select"): ("SELECT", "public", "(auth.uid() = id)", None),
    ("users", "users_update"): ("UPDATE", "public", "(auth.uid() = id)", None),
}

# The policies 055 drops (two of them, comparisons_select and
# referral_invites_select_own, are re-created narrower).
DROPPED = {
    ("comparisons", "comparisons_select"),
    ("comparisons", "comparisons_insert"),
    ("comparisons", "comparisons_update"),
    ("rating_cache", "Service role has full access to rating_cache"),
    ("admin_audit_log", "audit_insert"),
    ("comparison_feedback", "feedback_insert"),
    ("comparison_feedback", "Users can insert own feedback"),
    ("comparison_feedback", "Users can read own feedback"),
    ("search_logs", "search_logs_insert"),
    ("user_events", "events_insert"),
    ("user_events", "Users can insert own events"),
    ("users", "users_insert"),
    ("users", "Users can read own data"),
    ("users", "Users can update own data"),
    ("users", "Service role full access"),
    ("user_usage", "usage_insert"),
    ("user_usage", "usage_update"),
    ("referral_invites", "referral_invites_select_own"),
}

# The 21 objects that hold all seven privileges for anon and authenticated.
MEASURED_21 = (
    "admin_audit_log",
    "bahrain_approved_drugs",
    "comparison_feedback",
    "comparisons",
    "deep_review_credits",
    "eval_runs",
    "pain_workflow_events",
    "products",
    "rating_cache",
    "re_engagement_events",
    "referral_invites",
    "referral_redemptions",
    "search_logs",
    "user_events",
    "user_preference_history",
    "user_usage",
    "users",
    "verdict_critiques",
    "vw_cohort_feedback_lift",
    "vw_cohort_match_rate",
    "vw_cohort_persona_distribution",
)
VIEWS = (
    "vw_cohort_match_rate",
    "vw_cohort_persona_distribution",
    "vw_cohort_feedback_lift",
)

# P04: the revoke map of section 4 (object -> privileges), every one FROM anon, authenticated.
REVOKE_MAP = {
    "public.comparisons": {"INSERT", "UPDATE"},
    "public.rating_cache": {"ALL"},
    "public.admin_audit_log": {"ALL"},
    "public.comparison_feedback": {"INSERT", "UPDATE", "DELETE"},
    "public.search_logs": {"INSERT", "UPDATE", "DELETE"},
    "public.user_events": {"INSERT", "UPDATE", "DELETE"},
    "public.users": {"INSERT", "DELETE"},
    "public.vw_cohort_match_rate": {"ALL"},
    "public.vw_cohort_persona_distribution": {"ALL"},
    "public.vw_cohort_feedback_lift": {"ALL"},
    "public.user_usage": {"INSERT", "UPDATE", "DELETE"},
    "FUNCTION public.resolve_referral_code(text)": {"EXECUTE"},
    "ALL TABLES IN SCHEMA public": {"TRUNCATE", "TRIGGER", "REFERENCES"},
    "public.eval_runs": {"ALL"},
    "public.verdict_critiques": {"ALL"},
    "public.products": {"ALL"},
}

CHECK_SECTIONS = (
    "K01 policies",
    "K02 app_role_privileges",
    "K03 service_role",
    "K04 users_triggers",
    "K05 guard_function",
    "K06 column_defaults",
    "K07 views",
    "K08 resolve_referral_code",
    "K09 table_facts",
    "K10 definer_functions_writing_users",
    "K11 server_version_num",
)

# Today's invitee select (referral_service.py:793), byte for byte.
INVITEE_SELECT_TODAY = "id, email, subscription_tier, display_name"
INVITEE_SELECT_ON = (
    "id, email, subscription_tier, display_name, device_fingerprint_hash"
)
SAME_DEVICE_FLAG = "ENABLE_REFERRAL_SAME_DEVICE_CHECK"

UUID_CMP = "5a5a5a5a-0000-4000-8000-000000000001"
UUID_OWNER = "5a5a5a5a-0000-4000-8000-000000000002"
UUID_OTHER = "5a5a5a5a-0000-4000-8000-000000000003"
UUID_REFERRER = "5a5a5a5a-0000-4000-8000-000000000004"
UUID_INVITE = "5a5a5a5a-0000-4000-8000-000000000005"
SYNTH_HASH = "ab" * 32

NOT_OWNED = "[FEEDBACK] FEEDBACK_COMPARISON_NOT_OWNED"
UNREAD = "[FEEDBACK] FEEDBACK_OWNERSHIP_UNREAD"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _require(path: Path) -> str:
    assert path.exists(), "missing %s" % path.relative_to(ROOT).as_posix()
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def _strip_literals(sql: str) -> str:
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def _code(sql: str) -> str:
    """SQL outside every dollar-quoted body and comment."""
    no_comments = _strip_comments(sql)
    return re.sub(r"\$(\w*)\$.*?\$\1\$", "$$", no_comments, flags=re.DOTALL)


def _stmts(sql: str) -> list:
    return [_compact(s) for s in _code(sql).split(";") if s.strip()]


def _dollar_body(sql: str, tag: str) -> str:
    m = re.search(r"\$%s\$(.*?)\$%s\$" % (tag, tag), _strip_comments(sql), re.DOTALL)
    assert m, "no $%s$ block" % tag
    return m.group(1)


def _function_body(sql: str) -> str:
    m = re.search(r"AS \$function\$(.*?)\$function\$;", sql, re.DOTALL)
    assert m, "no $function$ body"
    return m.group(1)


def _exec_strings(sql: str) -> list:
    """The SQL text of every EXECUTE '<literal>' (comments stripped, quotes undoubled)."""
    return [
        _compact(m.replace("''", "'"))
        for m in re.findall(r"EXECUTE\s+'((?:[^']|'')*)'", _strip_comments(sql))
    ]


def _all_stmts(sql: str) -> list:
    return _stmts(sql) + _exec_strings(sql)


def _policy_name(raw: str) -> str:
    return raw[1:-1] if raw.startswith('"') else raw


def _b64sha(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode()


def _revokes(sql: str) -> list:
    out = []
    for s in _all_stmts(sql):
        m = re.match(r"REVOKE (.+?) ON (.+) FROM (.+)$", s)
        if m:
            privs = {p.strip() for p in m.group(1).split(",")}
            out.append((privs, m.group(2).strip(), m.group(3).strip()))
    return out


def _grants(sql: str) -> list:
    out = []
    for s in _all_stmts(sql):
        m = re.match(r"GRANT (.+?) ON (.+) TO (.+)$", s)
        if m:
            privs = {p.strip() for p in m.group(1).split(",")}
            out.append((privs, m.group(2).strip(), m.group(3).strip()))
    return out


def _split_objects(objects: str) -> list:
    if objects.startswith("FUNCTION ") or objects.startswith("ALL TABLES"):
        return [objects]
    return [o.strip() for o in objects.split(",")]


def _tables_without_rls(sql: str) -> list:
    """P10 detector: tables CREATEd in the SQL without an ENABLE ROW LEVEL SECURITY."""
    code = _code(sql)
    created = re.findall(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?((?:\w+\.)?\w+)",
        code,
        re.IGNORECASE,
    )
    missing = []
    for name in created:
        bare = name.split(".")[-1]
        pat = (
            r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?(?:\w+\.)?%s\s+"
            r"ENABLE\s+ROW\s+LEVEL\s+SECURITY" % re.escape(bare)
        )
        if not re.search(pat, code, re.IGNORECASE):
            missing.append(name)
    return missing


def _module(name: str):
    return importlib.import_module(name)


def _require_attr(module_name: str, attr: str):
    obj = getattr(_module(module_name), attr, None)
    assert obj is not None, "%s.%s is missing" % (module_name, attr)
    return obj


def _parse(rel: str) -> ast.AST:
    return ast.parse((ROOT / rel).read_text(encoding="utf-8"))


def _function_node(rel: str, name: str):
    for node in ast.walk(_parse(rel)):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise AssertionError("%s: %s not found" % (rel, name))


def _calls_name(func: ast.AST, name: str) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Name) and f.id == name) or (
                isinstance(f, ast.Attribute) and f.attr == name
            ):
                return True
    return False


# ---------------------------------------------------------------------------
# M-rows: the up migration
# ---------------------------------------------------------------------------


def test_m01_files_exist_once_and_reserved_numbers_untouched():
    assert sorted(p.name for p in MIG.glob("055_*.sql")) == [NAME]
    assert sorted(p.name for p in RB.glob("055_*.sql")) == [NAME]
    assert CHECK.exists(), "missing the read-only check"
    for reserved in ("039", "051", "053"):
        assert not list(MIG.glob(reserved + "_*.sql")), (
            "%s is reserved for another unit" % reserved
        )
        assert not list(RB.glob(reserved + "_*.sql")), (
            "%s is reserved for another unit" % reserved
        )


def test_m02_055_and_054_exist_053_absent():
    _require(UP)
    numbers = {int(p.name[:3]) for p in MIG.glob("[0-9][0-9][0-9]_*.sql")}
    assert 55 in numbers and 54 in numbers, sorted(numbers)[-4:]
    assert 53 not in numbers


@pytest.mark.parametrize("path", [UP, DOWN, CHECK], ids=["up", "down", "check"])
def test_m03_ascii_no_digit_runs(path):
    text = _require(path)
    assert all(ord(ch) < 128 for ch in text), "non-ASCII character"
    assert not re.search(r"\d{8}", text), "an 8-digit run"
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", text), "an id-shaped literal"


@pytest.mark.parametrize("path", [UP, DOWN], ids=["up", "down"])
def test_m04_one_transaction_lock_timeout_first(path):
    sql = _require(path)
    stmts = _stmts(sql)
    assert stmts[0] == "BEGIN" and stmts[-1] == "COMMIT", (stmts[0], stmts[-1])
    code = _code(sql)
    assert code.count("BEGIN;") == 1 and code.count("COMMIT;") == 1
    if path == UP:
        assert stmts[1] == "SET LOCAL lock_timeout = '5s'", stmts[1]
    for s in stmts:
        if s.upper().startswith("SET "):
            assert s.upper().startswith("SET LOCAL "), "session-level SET: %s" % s


def test_m05_function_header_invoker_and_no_definer_outside_comments():
    sql = _require(UP)
    head = (
        "CREATE OR REPLACE FUNCTION public.users_profile_guard() RETURNS trigger "
        "LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $function$"
    )
    assert head in _compact(_strip_comments(sql)), "function header changed"
    assert "SECURITY DEFINER" not in _compact(_strip_comments(sql)).upper()
    assert _compact(_strip_comments(sql)).count("CREATE OR REPLACE FUNCTION") == 1


def test_m06_trigger_shape():
    sql = _require(UP)
    want = (
        "CREATE OR REPLACE TRIGGER users_profile_guard BEFORE INSERT OR UPDATE ON public.users "
        "FOR EACH ROW EXECUTE FUNCTION public.users_profile_guard();"
    )
    assert want in _compact(_code(sql)), "trigger statement changed"
    assert len(re.findall(r"CREATE (?:OR REPLACE )?TRIGGER", _code(sql))) == 1


def test_m07_role_test_is_054s_and_first():
    body054 = _compact(_function_body(_require(M054_UP)))
    assert ROLE_TEST in body054, "the 054 anchor moved"
    body = _compact(_function_body(_require(UP)))
    assert ROLE_TEST in body, "role test differs from 054's"
    assert body.index(ROLE_TEST) < body.index(
        "IF TG_OP = 'INSERT'"
    ), "role test must run first"
    assert body.count("RETURN NEW;") == 3
    assert (
        "auth.role()" not in body and "auth.uid()" not in body
    ), "no dependency on the auth schema"


def test_m08_update_arm_is_exactly_the_six():
    body = _compact(_function_body(_require(UP)))
    update_arm = body.split("IF TG_OP = 'INSERT' THEN", 1)[1].split(
        "END IF; RETURN NEW; END IF;", 1
    )[1]
    pairs = re.findall(r"NEW\.(\w+) IS DISTINCT FROM OLD\.(\w+)", update_arm)
    assert [a for a, _b in pairs] == list(SIX), pairs
    assert all(a == b for a, b in pairs)
    assert set(re.findall(r"\bNEW\.(\w+)", body)) == set(SIX)
    assert set(re.findall(r"\bOLD\.(\w+)", body)) == set(SIX)
    assert not set(SIX) & set(ELEVEN_054)


def test_m09_insert_arm_values():
    body = _compact(_function_body(_require(UP)))
    insert_arm = body.split("IF TG_OP = 'INSERT' THEN", 1)[1].split(
        "RAISE EXCEPTION", 1
    )[0]
    got = re.findall(
        r"NEW\.(\w+) (IS DISTINCT FROM .+?|IS NOT NULL)(?= OR NEW\.| THEN)", insert_arm
    )
    assert dict(got) == INSERT_RULES, got
    assert [c for c, _r in got] == list(SIX)


def test_m10_refusal_sqlstate_and_fixed_message():
    body = _compact(_function_body(_require(UP)))
    raises = re.findall(r"RAISE EXCEPTION USING (.*?);", body)
    want = "ERRCODE = '42501', MESSAGE = '%s'" % MESSAGE
    assert raises == [want, want], raises
    assert "server-managed" in MESSAGE and MESSAGE != MESSAGE_054
    assert (
        "%" not in MESSAGE
        and "RAISE NOTICE" not in body
        and "DETAIL" not in body.upper()
    )


def test_m11_guard_function_assert_order():
    sql = _compact(_strip_comments(_require(UP)))
    assert "DO $guard$" in sql and "DO $assert$" in sql
    assert (
        sql.index("DO $guard$")
        < sql.index("CREATE OR REPLACE FUNCTION")
        < sql.index("DO $assert$")
    )
    guard = sql.split("DO $guard$", 1)[1].split("$guard$;", 1)[0]
    assert "'055 guard: " in guard
    for name in (
        (
            "public.users",
            "public.comparisons",
            "public.comparison_feedback",
            "public.search_logs",
            "public.user_events",
            "public.admin_audit_log",
            "public.user_usage",
            "public.referral_invites",
            "public.products",
            "public.eval_runs",
            "public.verdict_critiques",
            "public.resolve_referral_code(text)",
        )
        + tuple("public." + v for v in VIEWS)
        + SIX
    ):
        assert "'%s'" % name in guard, name
    assert "rating_cache" not in guard, "rating_cache is not required (S08)"


def test_m12_up_never_names_054_objects():
    code = _code(_require(UP))
    assert "users_entitlement_guard" not in code.lower()
    for s in _stmts(_require(UP)):
        if s.upper().startswith("DROP "):
            assert s.upper().startswith("DROP POLICY IF EXISTS "), s
        assert not s.upper().startswith("ALTER TABLE"), s
        assert not s.upper().startswith("ALTER TRIGGER"), s


# ---------------------------------------------------------------------------
# P-rows: policies and privileges of the up migration
# ---------------------------------------------------------------------------


def test_p01_comparisons_statements():
    stmts = _stmts(_require(UP))
    for want in (
        "DROP POLICY IF EXISTS comparisons_select ON public.comparisons",
        "CREATE POLICY comparisons_select ON public.comparisons AS PERMISSIVE FOR SELECT TO authenticated "
        "USING (auth.uid() = user_id)",
        "DROP POLICY IF EXISTS comparisons_insert ON public.comparisons",
        "DROP POLICY IF EXISTS comparisons_update ON public.comparisons",
        "REVOKE INSERT, UPDATE ON public.comparisons FROM anon, authenticated",
    ):
        assert want in stmts, want
    assert not any(
        "comparisons_delete" in s for s in stmts
    ), "comparisons_delete is kept"


def test_p02_no_open_branch_for_app_roles():
    sql = _require(UP)
    creates = [s for s in _all_stmts(sql) if s.upper().startswith("CREATE POLICY")]
    assert creates, "no CREATE POLICY"
    for s in creates:
        m = re.search(r"\bTO (.+?) (?:USING|WITH CHECK)\b", s)
        assert m, s
        roles = {r.strip().lower() for r in m.group(1).split(",")}
        if roles & {"public", "anon", "authenticated"}:
            assert "IS NULL" not in s.upper(), s
            assert "share_token" not in s, s
            assert not re.search(r"\(\s*true\s*\)", s, re.IGNORECASE), s


def test_p03_every_drop_names_a_census_policy_and_no_loop():
    sql = _require(UP)
    drops = set()
    for s in _all_stmts(sql):
        m = re.match(r'DROP POLICY IF EXISTS ("[^"]+"|\w+) ON public\.(\w+)$', s)
        if s.upper().startswith("DROP POLICY"):
            assert m, s
            drops.add((m.group(2), _policy_name(m.group(1))))
    assert all(d in CENSUS for d in drops), sorted(drops - set(CENSUS))
    assert drops == DROPPED, sorted(drops ^ DROPPED)
    assert "format(" not in _strip_comments(sql) and "%I" not in sql, "no policy loop"


def test_p04_revoke_map():
    got = {}
    for privs, objects, grantees in _revokes(_require(UP)):
        assert grantees == "anon, authenticated", (objects, grantees)
        for obj in _split_objects(objects):
            got.setdefault(obj, set()).update(privs)
    assert got == REVOKE_MAP, {k: sorted(v) for k, v in got.items()}


def test_p05_rating_cache_only_inside_a_to_regclass_do():
    sql = _require(UP)
    assert "rating_cache" not in _code(sql), "rating_cache outside the DO block"
    body = _dollar_body(sql, "rc")
    assert "to_regclass('public.rating_cache') IS NOT NULL" in _compact(body)
    rest = re.sub(r"EXECUTE\s+'(?:[^']|'')*'", "", body).replace(
        "to_regclass('public.rating_cache')", ""
    )
    assert "rating_cache" not in rest, "rating_cache named outside an EXECUTE string"
    execs = [e for e in _exec_strings(sql) if "rating_cache" in e]
    assert execs == [
        'DROP POLICY IF EXISTS "Service role has full access to rating_cache" ON public.rating_cache',
        "REVOKE ALL ON public.rating_cache FROM anon, authenticated",
    ], execs


def test_p06_users_statements():
    stmts = _stmts(_require(UP))
    for want in (
        "DROP POLICY IF EXISTS users_insert ON public.users",
        'DROP POLICY IF EXISTS "Users can read own data" ON public.users',
        'DROP POLICY IF EXISTS "Users can update own data" ON public.users',
        'DROP POLICY IF EXISTS "Service role full access" ON public.users',
        "REVOKE INSERT, DELETE ON public.users FROM anon, authenticated",
    ):
        assert want in stmts, want
    assert not any(
        re.search(r"\busers_(select|update)\b", s) for s in stmts
    ), "users_select / users_update kept"


def test_p07_views_revoke():
    sql = _require(UP)
    want = (
        "REVOKE ALL ON public.vw_cohort_match_rate, public.vw_cohort_persona_distribution, "
        "public.vw_cohort_feedback_lift FROM anon, authenticated"
    )
    assert want in _stmts(sql), want
    assert "security_invoker" not in _code(sql).lower()


def test_p08_f7_f10_f8_f9_statements():
    sql = _require(UP)
    stmts = _stmts(sql)
    for want in (
        "DROP POLICY IF EXISTS usage_insert ON public.user_usage",
        "DROP POLICY IF EXISTS usage_update ON public.user_usage",
        "REVOKE INSERT, UPDATE, DELETE ON public.user_usage FROM anon, authenticated",
        "DROP POLICY IF EXISTS referral_invites_select_own ON public.referral_invites",
        "CREATE POLICY referral_invites_select_own ON public.referral_invites AS PERMISSIVE FOR SELECT "
        "TO authenticated USING (referrer_user_id = auth.uid())",
        "REVOKE EXECUTE ON FUNCTION public.resolve_referral_code(text) FROM anon, authenticated",
        "ALTER FUNCTION public.resolve_referral_code(text) SET search_path = public",
        "REVOKE TRUNCATE, TRIGGER, REFERENCES ON ALL TABLES IN SCHEMA public FROM anon, authenticated",
        "REVOKE ALL ON public.eval_runs, public.verdict_critiques, public.products FROM anon, authenticated",
    ):
        assert want in stmts, want
    assert not any("usage_select" in s for s in stmts), "usage_select is kept"
    for s in _all_stmts(sql):
        if s.upper().startswith("REVOKE"):
            assert not re.search(
                r"\bPUBLIC\b(?!\.)", s.split(" FROM ", 1)[1], re.IGNORECASE
            ), s


def test_p09_assert_names_each_end_state_check():
    sql = _require(UP)
    body = _compact(_dollar_body(sql, "assert"))
    for piece in (
        "ARRAY['public', 'anon', 'authenticated']",
        "user_id IS NULL",
        "share_token",
        "p.qual = 'true'",
        "p.with_check = 'true'",
        "p.cmd IN ('INSERT', 'ALL')",
        "has_table_privilege(",
        "'TRUNCATE'",
        "'TRIGGER'",
        "'REFERENCES'",
        "t.tgenabled = 'O'",
        "(t.tgtype::integer & 23) = 23",
        "(t.tgtype::integer & 8) = 0",
        "'public.users_profile_guard()'::regprocedure",
        "NOT p.prosecdef",
        "LIKE 'search_path=%'",
        "has_function_privilege('anon', 'public.resolve_referral_code(text)', 'EXECUTE')",
        "has_function_privilege('authenticated', 'public.resolve_referral_code(text)', 'EXECUTE')",
        "NOT has_function_privilege('service_role', 'public.resolve_referral_code(text)', 'EXECUTE')",
        "'public.vw_cohort_match_rate', 'SELECT'",
        "'public.vw_cohort_persona_distribution', 'SELECT'",
        "'public.vw_cohort_feedback_lift', 'SELECT'",
    ):
        assert piece in body, piece
    for table in TEN_TABLES:
        assert "'%s'" % table in body, table
    assert len(re.findall(r"RAISE EXCEPTION '055 assert: ", body)) >= 6


SQL_NO_RLS = "BEGIN;\nCREATE TABLE IF NOT EXISTS public.synthetic_rows (id uuid PRIMARY KEY);\nCOMMIT;\n"
SQL_WITH_RLS = SQL_NO_RLS.replace(
    "COMMIT;", "ALTER TABLE public.synthetic_rows ENABLE ROW LEVEL SECURITY;\nCOMMIT;"
)


def test_p10_new_tables_enable_row_security_with_a_positive_control():
    assert _tables_without_rls(SQL_NO_RLS) == [
        "public.synthetic_rows"
    ], "the detector misses a bare table"
    assert (
        _tables_without_rls(SQL_WITH_RLS) == []
    ), "the detector flags a table with row security"
    files = [
        p for p in sorted(MIG.glob("[0-9][0-9][0-9]_*.sql")) if int(p.name[:3]) >= 55
    ]
    assert files, "no migration numbered 055 or later"
    for path in files:
        assert _tables_without_rls(_require(path)) == [], path.name


# ---------------------------------------------------------------------------
# D-row: the rollback
# ---------------------------------------------------------------------------


def _expected_create(table: str, name: str) -> str:
    cmd, role, using, check = CENSUS[(table, name)]
    qname = '"%s"' % name if " " in name else name
    out = "CREATE POLICY %s ON public.%s AS PERMISSIVE FOR %s TO %s" % (
        qname,
        table,
        cmd,
        role,
    )
    if using is not None:
        out += " USING (%s)" % using
    if check is not None:
        out += " WITH CHECK (%s)" % check
    return out


def test_d01_rollback_restores_exactly():
    down = _require(DOWN)
    code = _code(down)
    stmts = _all_stmts(down)
    tf = [s for s in stmts if re.match(r"DROP (TRIGGER|FUNCTION)", s)]
    assert tf == [
        "DROP TRIGGER IF EXISTS users_profile_guard ON public.users",
        "DROP FUNCTION IF EXISTS public.users_profile_guard()",
    ], tf
    for table, name in sorted(DROPPED):
        want = _expected_create(table, name)
        assert want in stmts, want
        qname = '"%s"' % name if " " in name else name
        drop = "DROP POLICY IF EXISTS %s ON public.%s" % (qname, table)
        assert drop in stmts and stmts.index(drop) < stmts.index(want), drop
    for i, s in enumerate(stmts):
        if s.startswith("CREATE POLICY"):
            m = re.match(
                r'CREATE POLICY ("[^"]+"|\w+) ON (public\.\w+) AS PERMISSIVE ', s
            )
            assert m, "no AS PERMISSIVE: %s" % s
            assert (
                "DROP POLICY IF EXISTS %s ON %s" % (m.group(1), m.group(2)) in stmts[:i]
            ), s
    assert "ON ALL TABLES" not in code.upper(), "grant back on named objects only"
    assert (
        "users_entitlement_guard" not in down and "054" not in down
    ), "the rollback names nothing of 054"
    assert _stmts(down)[0] == "BEGIN" and _stmts(down)[-1] == "COMMIT"
    assert code.count("BEGIN;") == 1 and code.count("COMMIT;") == 1
    header = down.split("BEGIN;", 1)[0]
    assert (
        "RE-OPENS" in header and "ruled rollback" in header and "byte-equal" in header
    )
    granted = {}
    for privs, objects, grantees in _grants(down):
        assert grantees == "anon, authenticated", (objects, grantees)
        for obj in _split_objects(objects):
            granted.setdefault(obj, set()).update(privs)
    for obj, privs in REVOKE_MAP.items():
        if obj == "ALL TABLES IN SCHEMA public":
            continue
        assert privs <= granted.get(obj, set()), (obj, sorted(granted.get(obj, set())))
    for name in MEASURED_21:
        got = granted.get("public." + name, set())
        assert "ALL" in got or {"TRUNCATE", "TRIGGER", "REFERENCES"} <= got, (
            name,
            sorted(got),
        )
    assert (
        "ALTER FUNCTION public.resolve_referral_code(text) RESET search_path" in stmts
    )
    rc = _compact(_dollar_body(down, "absent"))
    assert "to_regclass('public.rating_cache') IS NOT NULL" in rc
    assert "rating_cache" not in code


# ---------------------------------------------------------------------------
# K-rows: the read-only check
# ---------------------------------------------------------------------------


def test_k01_check_is_one_select_statement():
    text = _require(CHECK)
    code = _strip_literals(_strip_comments(text))
    stmts = [s.strip() for s in code.split(";") if s.strip()]
    assert len(stmts) == 1, len(stmts)
    assert stmts[0].upper().startswith(("SELECT", "WITH"))
    for word in (
        "INSERT",
        "UPDATE",
        "DELETE",
        "TRUNCATE",
        "MERGE",
        "ALTER",
        "CREATE",
        "DROP",
        "GRANT",
        "REVOKE",
        "COPY",
        "CALL",
        "DO",
        "SET",
        "PERFORM",
        "EXECUTE",
        "SET_CONFIG",
        "PG_SLEEP",
    ):
        assert not re.search(r"\b%s\b" % word, code.upper()), word
    assert "UNION ALL" in code.upper()


def test_k02_check_sources_are_catalog_only():
    code = _strip_literals(_strip_comments(_require(CHECK)))
    ctes = set(re.findall(r"(?:WITH|,)\s+(\w+)\s+AS\s+\(", code, re.IGNORECASE))
    for src in re.findall(
        r"\b(?:FROM|JOIN)\s+(?:LATERAL\s+)?([\w.]+)", code, re.IGNORECASE
    ):
        assert (
            src.split(".")[0].lower() in ("pg_catalog", "information_schema")
            or src in ctes
        ), src
    assert not re.search(
        r"\bpublic\.\w+\b", code
    ), "a public relation named outside a literal"
    for m in re.finditer(r"\bprosrc\b", code):
        before = code[: m.start()].upper()
        last_where = before.rfind("WHERE")
        assert last_where > before.rfind("SELECT") and last_where > before.rfind(
            "FROM"
        ), "prosrc outside WHERE"


def test_k03_check_sections_lists_and_words():
    text = _require(CHECK)
    for name in CHECK_SECTIONS:
        assert "'%s' AS section" % name in text, name
    lists = [
        re.findall(r"'(\w+)'", block.split(")", 1)[0])
        for block in text.split("column_name IN (")[1:]
    ]
    assert list(SIX) in lists, lists
    arrays = [
        re.findall(r"'(\w+)'", block.split("]", 1)[0])
        for block in text.split("ARRAY[")[1:]
    ]
    assert list(MEASURED_21) in arrays, "the measured-21 list"
    for word in ("rolbypassrls", "server_version_num", "aclexplode", "140000"):
        assert word in _strip_comments(text), word
    code = _strip_comments(text)
    assert (
        code.count("aclexplode") >= 2
    ), "PUBLIC's ACL rows for the relations and for the function"


# ---------------------------------------------------------------------------
# L-row: sqlfluff with the repo .sqlfluff
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [UP, DOWN, CHECK], ids=["up", "down", "check"])
def test_l01_sqlfluff_clean(path):
    text = _require(path)
    from sqlfluff.core import FluffConfig, Linter

    linter = Linter(config=FluffConfig.from_path(str(ROOT)))
    res = linter.lint_string(text, fname=path.relative_to(ROOT).as_posix())
    bad = [(v.rule_code(), v.line_no) for v in res.get_violations()]
    assert bad == [], bad


# ---------------------------------------------------------------------------
# X01 PIN: 054 untouched
# ---------------------------------------------------------------------------


def test_x01_pin_054_files_byte_equal_to_the_merged_blobs():
    for path, want in (
        (M054_UP, M054_UP_LF_SHA256),
        (M054_DOWN, M054_DOWN_LF_SHA256),
        (M054_CHECK, M054_CHECK_LF_SHA256),
    ):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        assert _b64sha(data) == want, path.name


# ---------------------------------------------------------------------------
# W-rows: AST walk over app/ and scripts/
# ---------------------------------------------------------------------------

WRITE_METHODS = ("insert", "update", "upsert", "delete")


def _table_of(call: ast.Call):
    """The literal table name of a .table("<x>") receiver somewhere down the chain, else None."""
    node = call.func.value if isinstance(call.func, ast.Attribute) else None
    while isinstance(node, (ast.Call, ast.Attribute)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "table"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            return node.args[0].value
        node = node.func if isinstance(node, ast.Call) else node.value
    return None


def _writes(func: ast.AST) -> set:
    out = set()
    for node in ast.walk(func):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in WRITE_METHODS
        ):
            table = _table_of(node)
            if table is not None:
                out.add((table, node.func.attr))
    return out


def _user_scoped_functions() -> dict:
    found = {}
    for base in ("app", "scripts"):
        for path in sorted((ROOT / base).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == "get_user_supabase_client":
                        continue
                    if _calls_name(node, "get_user_supabase_client"):
                        found[(rel, node.name)] = _writes(node)
    return found


USER_SCOPED_WRITERS = {
    ("app/api/auth_routes.py", "update_push_token"),
    ("app/api/auth_routes.py", "update_reengagement_subs"),
    ("app/api/auth_routes.py", "update_preference_toggles"),
    ("app/services/database_service.py", "delete_comparison"),
}
CLOSED_WRITES = {
    (t, m)
    for t in (
        "comparisons",
        "comparison_feedback",
        "search_logs",
        "user_events",
        "admin_audit_log",
        "rating_cache",
        "user_usage",
    )
    for m in ("insert", "update", "upsert")
} | {("users", "insert"), ("users", "upsert")}


def test_w01_user_scoped_write_set():
    writers = {k for k, w in _user_scoped_functions().items() if w}
    assert writers == USER_SCOPED_WRITERS, sorted(writers ^ USER_SCOPED_WRITERS)


def test_w02_no_user_scoped_write_to_a_closed_table():
    bad = {
        k: sorted(w & CLOSED_WRITES)
        for k, w in _user_scoped_functions().items()
        if w & CLOSED_WRITES
    }
    assert bad == {}, bad


def _users_write_keys(func: ast.AST) -> set:
    dict_vars = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    dict_vars.setdefault(tgt.id, set()).update(
                        k.value for k in node.value.keys if isinstance(k, ast.Constant)
                    )
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (
                    isinstance(tgt, ast.Subscript)
                    and isinstance(tgt.value, ast.Name)
                    and isinstance(tgt.slice, ast.Constant)
                ):
                    dict_vars.setdefault(tgt.value.id, set()).add(tgt.slice.value)
    keys = set()
    for node in ast.walk(func):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("update", "insert", "upsert")
            and node.args
        ):
            continue
        if _table_of(node) != "users":
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Dict):
            keys.update(k.value for k in arg.keys if isinstance(k, ast.Constant))
        elif isinstance(arg, ast.Name):
            keys.update(dict_vars.get(arg.id, set()))
    return keys


def _users_writers() -> dict:
    found = {}
    for base in ("app", "scripts"):
        for path in sorted((ROOT / base).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    keys = _users_write_keys(node)
                    if keys:
                        found[(rel, node.name)] = (
                            keys,
                            _calls_name(node, "get_user_supabase_client"),
                        )
    return found


def test_w03_pin_user_scoped_users_writers_touch_none_of_the_six():
    scoped = {k: keys for k, (keys, user) in _users_writers().items() if user}
    assert set(scoped) == {
        ("app/api/auth_routes.py", "update_push_token"),
        ("app/api/auth_routes.py", "update_reengagement_subs"),
        ("app/api/auth_routes.py", "update_preference_toggles"),
    }, sorted(scoped)
    for key, keys in scoped.items():
        assert not keys & set(SIX), (key, keys)


def test_w04_pin_every_writer_of_the_six_is_service():
    writers = {
        k: user for k, (keys, user) in _users_writers().items() if keys & set(SIX)
    }
    assert writers, "no writer of the six found (the walk is blind)"
    assert not any(writers.values()), sorted(k for k, user in writers.items() if user)


def test_w05_pin_the_app_has_no_database_client():
    pkg = (ROOT / "SmartCompareApp" / "package.json").read_text(encoding="utf-8")
    assert "supabase" not in pkg.lower()
    hits = []
    for path in sorted((ROOT / "SmartCompareApp" / "src").rglob("*")):
        if path.is_file() and path.suffix in (".ts", ".tsx", ".js", ".jsx"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for word in ("createClient", "rest/v1", "@supabase"):
                if word in text:
                    hits.append((path.relative_to(ROOT).as_posix(), word))
    assert hits == [], hits


def test_w06_pin_share_route_two_arguments_and_admin_share_page():
    tree = _parse("app/api/share_routes.py")
    calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "create_share_token"
    ]
    assert (
        len(calls) == 1 and len(calls[0].args) == 2 and not calls[0].keywords
    ), ast.dump(calls[0])
    src = ast.get_source_segment(
        (ROOT / "app/services/database_service.py").read_text(encoding="utf-8"),
        _function_node("app/services/database_service.py", "get_shared_comparison"),
    )
    assert "client = get_admin_supabase_client()" in src
    assert "get_user_supabase_client" not in src


# ---------------------------------------------------------------------------
# C-rows: the server code
# ---------------------------------------------------------------------------


def test_c01_create_share_token_has_no_user_branch():
    fn = _function_node("app/services/database_service.py", "create_share_token")
    params = [a.arg for a in fn.args.args + fn.args.kwonlyargs]
    assert params == ["comparison_id", "user_id"], params
    assert not _calls_name(fn, "get_user_supabase_client")
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "get_comparison_by_id"
        ):
            assert not node.keywords and len(node.args) == 1, ast.dump(node)


class _Resp:
    def __init__(self, data):
        self.data = data


class _Chain:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.op = None

    def select(self, cols, *a, **k):
        self.op = "select"
        self.client.calls.append(("select", self.table, cols))
        return self

    def eq(self, key, value):
        self.client.calls.append(("eq", self.table, key, value))
        return self

    def limit(self, n):
        self.client.calls.append(("limit", self.table, n))
        return self

    def single(self):
        self.client.calls.append(("single", self.table))
        return self

    def insert(self, record):
        self.op = "insert"
        self.client.calls.append(("insert", self.table, dict(record)))
        return self

    def execute(self):
        if self.op == "insert":
            return _Resp([{"id": "fb-row"}])
        if self.client.read_raises:
            raise RuntimeError("synthetic read failure")
        return _Resp(self.client.rows.get(self.table, []))


class _FakeClient:
    def __init__(self, rows=None, read_raises=False):
        self.rows = rows or {}
        self.read_raises = read_raises
        self.calls = []

    def table(self, name):
        self.calls.append(("table", name))
        return _Chain(self, name)

    def tables(self):
        return [c[1] for c in self.calls if c[0] == "table"]

    def inserts(self):
        return [
            c[2]
            for c in self.calls
            if c[0] == "insert" and c[1] == "comparison_feedback"
        ]


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        if not any(r is record for r in self.records):
            self.records.append(record)


def _run_save_feedback(monkeypatch, admin, user_id, comparison_id, access_token=None):
    fs = _module("app.services.feedback_service")
    ds = _module("app.services.database_service")
    user_client = _FakeClient()
    built = []

    def _user(tok):
        built.append(tok)
        return user_client

    monkeypatch.delenv("ENABLE_FEEDBACK_V2", raising=False)
    monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    monkeypatch.setattr(ds, "get_user_supabase_client", _user)
    monkeypatch.setattr(fs, "get_supabase_client", lambda: admin)
    handler = _ListHandler()
    log = logging.getLogger(fs.__name__)
    log.addHandler(handler)
    old_level = log.level
    log.setLevel(logging.DEBUG)
    try:
        out = asyncio.run(
            fs.save_feedback(
                user_id=user_id,
                comparison_id=comparison_id,
                useful=True,
                mattered_most=["price"],
                access_token=access_token,
            )
        )
    finally:
        log.removeHandler(handler)
        log.setLevel(old_level)
    warnings = [r for r in handler.records if r.levelno >= logging.WARNING]
    return out, built, user_client, warnings


def test_c02_signed_in_feedback_uses_the_service_client():
    fs = _module("app.services.feedback_service")
    helper = getattr(fs, "_owned_comparison_id", None)
    assert helper is not None and asyncio.iscoroutinefunction(
        helper
    ), "_owned_comparison_id missing"
    tree = _parse("app/services/feedback_service.py")
    top = [n.name for n in tree.body if isinstance(n, ast.AsyncFunctionDef)]
    assert "_owned_comparison_id" in top, "the helper lives at module level"
    fn = _function_node("app/services/feedback_service.py", "save_feedback")
    assert (
        len([n for n in ast.walk(fn) if isinstance(n, ast.ExceptHandler)]) == 1
    ), "GR1: one except arm"
    assert not _calls_name(fn, "get_user_supabase_client")


def test_c02_behaviour_with_a_token(monkeypatch):
    _require_attr("app.services.feedback_service", "_owned_comparison_id")
    admin = _FakeClient(rows={"comparisons": [{"user_id": UUID_OWNER}]})
    out, built, user_client, _w = _run_save_feedback(
        monkeypatch, admin, UUID_OWNER, UUID_CMP, access_token="synthetic-access"
    )
    assert built == [] and user_client.calls == [], "a user client was built"
    assert out.get("success") is True, out
    assert admin.tables()[-1] == "comparison_feedback", admin.tables()
    assert len(admin.inserts()) == 1


C03_CASES = {
    "1_signed_in_owner": (
        UUID_OWNER,
        {"comparisons": [{"user_id": UUID_OWNER}]},
        False,
        True,
        None,
    ),
    "2_signed_in_foreign": (
        UUID_OWNER,
        {"comparisons": [{"user_id": UUID_OTHER}]},
        False,
        False,
        NOT_OWNED,
    ),
    "3_signed_in_missing": (UUID_OWNER, {"comparisons": []}, False, False, NOT_OWNED),
    "4_signed_in_read_raises": (UUID_OWNER, {}, True, False, UNREAD),
    "5_anonymous_no_row": (None, {"comparisons": []}, False, True, None),
    "6_anonymous_owned_row": (
        None,
        {"comparisons": [{"user_id": UUID_OTHER}]},
        False,
        False,
        NOT_OWNED,
    ),
    "7_anonymous_null_owner": (
        None,
        {"comparisons": [{"user_id": None}]},
        False,
        True,
        None,
    ),
    "8_anonymous_read_raises": (None, {}, True, False, UNREAD),
}


@pytest.mark.parametrize("case", sorted(C03_CASES))
def test_c03_ownership_rule(monkeypatch, case):
    _require_attr("app.services.feedback_service", "_owned_comparison_id")
    user_id, rows, raises, kept, line = C03_CASES[case]
    admin = _FakeClient(rows=rows, read_raises=raises)
    token = "synthetic-access" if user_id else None
    out, built, _uc, warnings = _run_save_feedback(
        monkeypatch, admin, user_id, UUID_CMP, access_token=token
    )
    assert built == [], "a user client was built"
    assert out.get("success") is True, out
    reads = [c for c in admin.calls if c[0] != "table" and c[1] == "comparisons"]
    assert reads == [
        ("select", "comparisons", "user_id"),
        ("eq", "comparisons", "id", UUID_CMP),
        ("limit", "comparisons", 1),
    ], reads
    inserts = admin.inserts()
    assert len(inserts) == 1, inserts
    assert ("comparison_id" in inserts[0]) is kept, inserts[0]
    if kept:
        assert inserts[0]["comparison_id"] == UUID_CMP
    msgs = [(r.getMessage(), r.args) for r in warnings]
    assert msgs == ([] if line is None else [(line, ())]), msgs


def test_c03_9_no_comparison_id_no_read(monkeypatch):
    _require_attr("app.services.feedback_service", "_owned_comparison_id")
    admin = _FakeClient()
    out, built, _uc, warnings = _run_save_feedback(
        monkeypatch, admin, UUID_OWNER, None, access_token="synthetic-access"
    )
    assert built == [] and out.get("success") is True, out
    assert "comparisons" not in admin.tables(), admin.tables()
    assert len(admin.inserts()) == 1 and warnings == []


class _UsersClient:
    """A projecting fake: select(cols) records the string, execute returns only those keys."""

    def __init__(self, row):
        self.row = row
        self.selects = []

    def table(self, name):
        assert name == "users", name
        client = self

        class _Q:
            def select(self, cols, *a, **k):
                client.selects.append(cols)
                self.cols = [c.strip() for c in cols.split(",")]
                return self

            def eq(self, *a):
                return self

            def single(self):
                return self

            def execute(self):
                return _Resp({k: client.row[k] for k in self.cols if k in client.row})

        return _Q()


def _full_config(monkeypatch, value):
    monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")
    monkeypatch.setenv("REAL_ACTION_MIN_SECONDS", "5")
    monkeypatch.delenv("ENABLE_DEVICE_DAILY_QUOTA", raising=False)
    monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    if value is None:
        monkeypatch.delenv(SAME_DEVICE_FLAG, raising=False)
    else:
        monkeypatch.setenv(SAME_DEVICE_FLAG, value)


def _loop2(monkeypatch):
    rs = _module("app.services.referral_service")
    ads = _module("app.services.abuse_detection_service")
    row = {
        "id": UUID_OWNER,
        "email": "invitee@example.invalid",
        "subscription_tier": "free",
        "display_name": "Synthetic",
        "device_fingerprint_hash": SYNTH_HASH,
    }
    users = _UsersClient(row)
    monkeypatch.setattr(rs, "get_admin_supabase_client", lambda: users)
    monkeypatch.setattr(ads, "get_admin_supabase_client", lambda: MagicMock())
    monkeypatch.setattr(
        ads.AbuseDetectionService,
        "_get_referrer_device_hash",
        lambda self, rid: SYNTH_HASH,
    )
    monkeypatch.setattr(
        ads.AbuseDetectionService, "passes_real_action_gate", lambda self, cid: True
    )
    monkeypatch.setattr(
        ads.AbuseDetectionService, "is_disposable_email", lambda self, email: False
    )
    seen = []
    original = ads.AbuseDetectionService.evaluate_invite

    def _spy(self, invite, invitee):
        seen.append(dict(invitee))
        return original(self, invite, invitee)

    monkeypatch.setattr(ads.AbuseDetectionService, "evaluate_invite", _spy)
    monkeypatch.setattr(rs, "log_audit_event", AsyncMock())
    svc = rs.ReferralService()
    svc._find_unredeemed_invite_for_invitee = AsyncMock(
        return_value={
            "id": UUID_INVITE,
            "referrer_user_id": UUID_REFERRER,
            "redeemed_by_user_id": UUID_OWNER,
            "redeemed_at": None,
            "device_fingerprint_hash": SYNTH_HASH,
        }
    )
    svc._count_user_comparisons = AsyncMock(return_value=1)
    svc._referrer_device_lifetime_count = AsyncMock(return_value=0)
    svc._get_referrer_subscription_tier = AsyncMock(return_value="free")
    svc._grant_loop2_rewards = AsyncMock()
    svc._update_invite_as_redeemed = AsyncMock()
    svc._send_loop2_push = AsyncMock()
    svc._flag_invite = AsyncMock()
    return svc, users, seen


@pytest.mark.parametrize(
    "value", [None, "false", " OFF ", "0"], ids=["unset", "false", "OFF_padded", "zero"]
)
def test_c04_a_switch_off_is_todays_select(monkeypatch, value):
    _require_attr(
        "app.services.referral_service", "_referral_same_device_check_enabled"
    )
    _full_config(monkeypatch, value)
    svc, users, seen = _loop2(monkeypatch)
    asyncio.run(svc.try_trigger_loop2(UUID_OWNER, UUID_CMP))
    assert users.selects == [INVITEE_SELECT_TODAY], users.selects
    assert len(seen) == 1 and "device_fingerprint_hash" not in seen[0], seen
    svc._grant_loop2_rewards.assert_awaited_once()
    assert svc._grant_loop2_rewards.await_args.kwargs.get("grant_amount") == 5
    svc._flag_invite.assert_not_awaited()


@pytest.mark.parametrize("value", ["true", " TRUE ", "1", "yes", "on"])
def test_c04_b_switch_on_flags_same_device(monkeypatch, value):
    _require_attr(
        "app.services.referral_service", "_referral_same_device_check_enabled"
    )
    _full_config(monkeypatch, value)
    svc, users, seen = _loop2(monkeypatch)
    asyncio.run(svc.try_trigger_loop2(UUID_OWNER, UUID_CMP))
    assert users.selects == [INVITEE_SELECT_ON], users.selects
    assert len(seen) == 1 and seen[0].get("device_fingerprint_hash") == SYNTH_HASH, seen
    svc._flag_invite.assert_awaited_once_with(UUID_INVITE, "SAME_DEVICE")
    svc._grant_loop2_rewards.assert_not_awaited()


def test_c04_c_switch_read_per_call(monkeypatch):
    _require_attr(
        "app.services.referral_service", "_referral_same_device_check_enabled"
    )
    _full_config(monkeypatch, None)
    svc, users, _seen = _loop2(monkeypatch)
    asyncio.run(svc._load_invitee(UUID_OWNER))
    monkeypatch.setenv(SAME_DEVICE_FLAG, "true")
    asyncio.run(svc._load_invitee(UUID_OWNER))
    monkeypatch.setenv(SAME_DEVICE_FLAG, "false")
    asyncio.run(svc._load_invitee(UUID_OWNER))
    assert users.selects == [
        INVITEE_SELECT_TODAY,
        INVITEE_SELECT_ON,
        INVITEE_SELECT_TODAY,
    ], users.selects
