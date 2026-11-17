"""INC-T1b USERS-ENTITLEMENT-GUARD: the frozen static rows (RED at base 5cd93c6a).

The unit adds migrations/054_users_entitlement_guard.sql (a BEFORE INSERT OR UPDATE
row trigger on public.users that refuses an entitlement-column change made by an anon
or authenticated caller), its rollback migrations/rollback/054_users_entitlement_guard.sql
and the read-only catalog check
docs/investigations/2026-11-17-session-97-state/APPLY_054_CHECK.sql. Nothing here
touches a database: every row is a text or AST scan of repo files. A row whose file is
missing fails on an AssertionError (never an import error). The W-rows (writer walk) are
PIN rows, green at base: they pin the writers of public.users the guard must not break.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / "migrations"
RB = MIG / "rollback"
UP = MIG / "054_users_entitlement_guard.sql"
DOWN = RB / "054_users_entitlement_guard.sql"
CHECK = ROOT / "docs" / "investigations" / "2026-11-17-session-97-state" / "APPLY_054_CHECK.sql"
M043 = MIG / "043_delete_user_cascade_full_erasure.sql"

FUNC = "public.users_entitlement_guard()"
TRIGGER = "users_entitlement_guard"
MESSAGE = "users entitlement columns are server-managed (INC-T1b)"

# The eleven guarded columns (IN), in the order the function names them.
GUARDED = (
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

# The INSERT arm: each guarded column must equal its column default.
INSERT_RULES = {
    "subscription_tier": "IS DISTINCT FROM 'free'",
    "subscription_expires_at": "IS NOT NULL",
    "lifetime_comparisons_used": "IS DISTINCT FROM 0",
    "referral_bonus_comparisons_this_month": "IS DISTINCT FROM 0",
    "referral_bonus_reset_at": "IS DISTINCT FROM (date_trunc('month', now()) + interval '1 month')",
    "lifetime_invites_consumed": "IS DISTINCT FROM 0",
    "device_fingerprint_hash": "IS NOT NULL",
    "referral_code": "IS NOT NULL",
    "terms_accepted_at": "IS NOT NULL",
    "terms_version": "IS NOT NULL",
    "age_attested_at": "IS NOT NULL",
}

# The 27 columns of public.users the migrations know (043 guard list + id + created_at).
CENSUS = (
    "id", "email", "display_name", "auth_provider", "subscription_tier",
    "subscription_expires_at", "created_at", "updated_at", "preferences",
    "preferences_completed", "behavior_profile", "lifetime_comparisons_used",
    "demographics_profile", "demographics_dismissed_count", "demographics_dismissed_at",
    "referral_code", "referral_bonus_comparisons_this_month", "referral_bonus_reset_at",
    "expo_push_token", "notifications_enabled", "last_comparison_at", "attribution_source",
    "device_fingerprint_hash", "lifetime_invites_consumed", "terms_accepted_at",
    "terms_version", "age_attested_at",
)
NOT_GUARDED = (
    "id", "email", "display_name", "auth_provider", "created_at", "updated_at",
    "preferences", "preferences_completed", "behavior_profile", "demographics_profile",
    "demographics_dismissed_count", "demographics_dismissed_at", "expo_push_token",
    "notifications_enabled", "last_comparison_at", "attribution_source",
)

ROLE_TEST = (
    "v_request_role := coalesce( "
    "nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', "
    "nullif(current_setting('request.jwt.claim.role', true), '') ); "
    "IF current_user NOT IN ('anon', 'authenticated') "
    "AND (v_request_role IS NULL OR v_request_role = 'service_role') THEN "
    "RETURN NEW; END IF;"
)


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


def _function_body(sql: str) -> str:
    m = re.search(r"AS \$function\$(.*?)\$function\$;", sql, re.DOTALL)
    assert m, "no $function$ body in 054"
    return m.group(1)


def _code(sql: str) -> str:
    """054 outside every dollar-quoted body and comment."""
    no_comments = _strip_comments(sql)
    return re.sub(r"\$(\w*)\$.*?\$\1\$", "$$", no_comments, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# M-rows: the migration
# ---------------------------------------------------------------------------

def test_m01_files_exist_once_and_reserved_numbers_untouched():
    assert sorted(p.name for p in MIG.glob("054_*.sql")) == ["054_users_entitlement_guard.sql"]
    assert sorted(p.name for p in RB.glob("054_*.sql")) == ["054_users_entitlement_guard.sql"]
    assert CHECK.exists(), "missing the read-only check"
    for reserved in ("039", "051", "053"):
        assert not list(MIG.glob(reserved + "_*.sql")), "%s is reserved for another unit" % reserved
        assert not list(RB.glob(reserved + "_*.sql")), "%s is reserved for another unit" % reserved


def test_m02_next_free_number():
    """054 is the next number after 052 once the reserved 039 / 051 / 053 are skipped."""
    _require(UP)
    numbers = sorted({int(p.name[:3]) for p in MIG.glob("[0-9][0-9][0-9]_*.sql")})
    assert numbers[-1] == 54, numbers[-4:]
    assert 52 in numbers and 53 not in numbers


@pytest.mark.parametrize("path", [UP, DOWN, CHECK], ids=["up", "down", "check"])
def test_m03_ascii_no_digit_runs(path):
    text = _require(path)
    assert all(ord(ch) < 128 for ch in text), "non-ASCII character"
    assert not re.search(r"\d{8}", text), "an 8-digit run"
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", text), "an id-shaped literal"


@pytest.mark.parametrize("path", [UP, DOWN], ids=["up", "down"])
def test_m04_one_transaction(path):
    code = _code(_require(path))
    stmts = [s.strip() for s in code.split(";") if s.strip()]
    assert stmts[0] == "BEGIN" and stmts[-1] == "COMMIT", (stmts[0], stmts[-1])
    assert code.count("BEGIN;") == 1 and code.count("COMMIT;") == 1


def test_m05_function_header_security_invoker_and_search_path():
    sql = _require(UP)
    head = (
        "CREATE OR REPLACE FUNCTION public.users_entitlement_guard() RETURNS trigger "
        "LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $function$"
    )
    assert head in _compact(sql), "function header changed"
    assert "SECURITY DEFINER" not in _strip_comments(sql).upper()
    assert _compact(sql).count("CREATE OR REPLACE FUNCTION") == 1


def test_m06_trigger_shape():
    sql = _require(UP)
    want = (
        "CREATE OR REPLACE TRIGGER users_entitlement_guard BEFORE INSERT OR UPDATE ON public.users "
        "FOR EACH ROW EXECUTE FUNCTION public.users_entitlement_guard();"
    )
    assert want in _compact(_code(sql)), "trigger statement changed"
    assert len(re.findall(r"CREATE (?:OR REPLACE )?TRIGGER", _code(sql))) == 1


def test_m07_role_test_text_is_the_first_branch():
    body = _compact(_function_body(_require(UP)))
    assert ROLE_TEST in body, "role test changed"
    assert body.index(ROLE_TEST) < body.index("IF TG_OP = 'INSERT'"), "role test must run first"
    assert body.count("RETURN NEW;") == 3
    assert "auth.role()" not in body and "auth.uid()" not in body, "no dependency on the auth schema"


def test_m08_update_arm_guards_exactly_the_eleven_columns():
    body = _function_body(_require(UP))
    update_arm = body.split("IF TG_OP = 'INSERT' THEN", 1)[1].split("END IF;\n    RETURN NEW;\n  END IF;", 1)[1]
    pairs = re.findall(r"NEW\.(\w+) IS DISTINCT FROM OLD\.(\w+)", update_arm)
    assert [a for a, _b in pairs] == list(GUARDED), pairs
    assert all(a == b for a, b in pairs)
    assert set(re.findall(r"\bNEW\.(\w+)", body)) == set(GUARDED)
    assert set(re.findall(r"\bOLD\.(\w+)", body)) == set(GUARDED)


def test_m09_insert_arm_compares_each_column_with_its_default():
    body = _compact(_function_body(_require(UP)))
    insert_arm = body.split("IF TG_OP = 'INSERT' THEN", 1)[1].split("RAISE EXCEPTION", 1)[0]
    got = re.findall(r"NEW\.(\w+) (IS DISTINCT FROM .+?|IS NOT NULL)(?= OR NEW\.| THEN)", insert_arm)
    assert dict(got) == INSERT_RULES, got
    assert [c for c, _r in got] == list(GUARDED)


def test_m10_refusal_sqlstate_and_fixed_message():
    body = _compact(_function_body(_require(UP)))
    raises = re.findall(r"RAISE EXCEPTION USING (.*?);", body)
    want = "ERRCODE = '42501', MESSAGE = '%s'" % MESSAGE
    assert raises == [want, want], raises
    assert "%" not in MESSAGE and "RAISE NOTICE" not in body and "DETAIL" not in body.upper()


def test_m11_guard_and_assert_blocks():
    sql = _compact(_require(UP))
    assert "DO $guard$" in sql and "DO $assert$" in sql
    guard = sql.split("DO $guard$", 1)[1].split("$guard$;", 1)[0]
    assert re.findall(r"'(\w+)'", guard.split("unnest(ARRAY[", 1)[1].split("])", 1)[0]) == list(GUARDED)
    asserted = sql.split("DO $assert$", 1)[1].split("$assert$;", 1)[0]
    for piece in ("t.tgenabled = 'O'", "(t.tgtype::integer & 23) = 23", "(t.tgtype::integer & 8) = 0",
                  "NOT p.prosecdef", "LIKE 'search_path=%'",
                  "'public.users_entitlement_guard()'::regprocedure"):
        assert piece in asserted, piece
    assert sql.index("DO $guard$") < sql.index("CREATE OR REPLACE FUNCTION") < sql.index("DO $assert$")


def test_m12_no_privilege_change_no_index_no_row_write():
    code = _code(_require(UP)).upper()
    for word in ("GRANT", "REVOKE", "CREATE INDEX", "ALTER TABLE", "DROP ", "INSERT INTO", "DELETE FROM",
                 "TRUNCATE", "DISABLE TRIGGER"):
        assert word not in code, word
    assert not re.search(r"\bUPDATE\s+(PUBLIC\.)?USERS\b", code)


def test_m13_index_predicate_pins_still_hold():
    from tests import test_migration_index_predicate_immutability as timm

    sql = _require(UP)
    for _stmt, predicate in timm._index_predicates(sql):
        assert not timm._volatile_hits(predicate)


# ---------------------------------------------------------------------------
# C-rows: the column decision (27 columns, eleven IN)
# ---------------------------------------------------------------------------

def test_c01_census_is_the_043_column_list_plus_id_and_created_at():
    text = _require(M043)
    guard_list = text.split("public.users lacks column(s)")[0].rsplit("unnest(ARRAY[", 1)[1].split("])", 1)[0]
    cols = re.findall(r"'(\w+)'", guard_list)
    assert len(CENSUS) == 27 and len(set(CENSUS)) == 27
    assert sorted(cols + ["id", "created_at"]) == sorted(CENSUS)


def test_c02_in_and_out_partition_the_census():
    assert len(GUARDED) == 11
    assert set(GUARDED) | set(NOT_GUARDED) == set(CENSUS)
    assert not set(GUARDED) & set(NOT_GUARDED)
    for must in ("subscription_tier", "subscription_expires_at", "lifetime_comparisons_used",
                 "referral_bonus_comparisons_this_month", "referral_bonus_reset_at",
                 "lifetime_invites_consumed"):
        assert must in GUARDED


def test_c03_erasure_writes_only_values_the_service_role_path_sets():
    """043 / 048 delete_user_cascade reset every guarded column; it runs as service role
    (database_service.delete_user_data_cascade, admin client), so the guard lets it pass."""
    for name in ("043_delete_user_cascade_full_erasure.sql", "048_compare_runs.sql"):
        text = _compact(_require(MIG / name))
        block = text.rsplit("UPDATE public.users SET", 1)[1].split("WHERE id = target_user_id", 1)[0]
        for col in GUARDED:
            assert re.search(r"\b%s = " % col, block), (name, col)
        assert "REVOKE ALL ON FUNCTION public.delete_user_cascade(uuid) FROM PUBLIC, anon, authenticated" in text


# ---------------------------------------------------------------------------
# D-rows: the down migration
# ---------------------------------------------------------------------------

def test_d01_down_drops_exactly_what_up_creates():
    up = _code(_require(UP))
    down = _code(_require(DOWN))
    created = set(re.findall(r"CREATE OR REPLACE (FUNCTION|TRIGGER) ([\w.]+(?:\(\))?)", up))
    assert created == {("FUNCTION", FUNC), ("TRIGGER", TRIGGER)}, created
    dropped = re.findall(r"DROP (FUNCTION|TRIGGER) IF EXISTS ([\w.]+(?:\(\))?)", down)
    assert sorted(dropped) == sorted(created), dropped
    assert "DROP TRIGGER IF EXISTS users_entitlement_guard ON public.users;" in _compact(down)
    assert _compact(down).index("DROP TRIGGER") < _compact(down).index("DROP FUNCTION")
    for word in ("CREATE", "ALTER", "INSERT", "UPDATE", "DELETE", "GRANT", "REVOKE", "CASCADE"):
        assert not re.search(r"\b%s\b" % word, down.upper()), word


# ---------------------------------------------------------------------------
# K-rows: the read-only check
# ---------------------------------------------------------------------------

def test_k01_check_is_select_only():
    text = _require(CHECK)
    code = _strip_literals(_strip_comments(text))
    stmts = [s.strip() for s in code.split(";") if s.strip()]
    assert len(stmts) == 8, len(stmts)
    assert all(s.upper().startswith(("SELECT", "WITH")) for s in stmts)
    for word in ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "MERGE", "ALTER", "CREATE", "DROP", "GRANT",
                 "REVOKE", "COPY", "CALL", "DO", "SET", "PERFORM", "EXECUTE", "SET_CONFIG", "PG_SLEEP"):
        assert not re.search(r"\b%s\b" % word, code.upper()), word


def test_k02_check_reads_no_users_row():
    code = _strip_literals(_strip_comments(_require(CHECK)))
    assert not re.search(r"\b(FROM|JOIN)\s+(\"?public\"?\.)?\"?users\"?\b", code, re.IGNORECASE)
    assert not re.search(r"\bauth\.users\b", code, re.IGNORECASE), "auth.users only as a regclass literal"
    for src in re.findall(r"\b(?:FROM|JOIN)\s+([\w.]+)", code, re.IGNORECASE):
        assert src.split(".")[0] in ("pg_catalog", "information_schema"), src


def test_k03_check_sections_and_guarded_list():
    text = _require(CHECK)
    for n, name in enumerate(("trigger_on_users", "guard_function", "rls_flags", "policies", "column_grants",
                              "guarded_column_defaults", "auth_users_triggers",
                              "definer_functions_writing_users"), start=1):
        assert "'%d %s' AS section" % (n, name) in text, name
    for block in text.split("AND cp.column_name IN (", 1)[1:] + text.split("AND col.column_name IN (", 1)[1:]:
        assert re.findall(r"'(\w+)'", block.split(")", 1)[0]) == list(GUARDED)


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
# W-rows (PIN, green at base): the writers of public.users
# ---------------------------------------------------------------------------

# Every (file, function) in app/ and scripts/ whose users insert / update names a guarded
# column, with the token in that function that proves the client is the service role.
ADMIN_WRITERS = {
    ("app/api/auth_routes.py", "_inherit_device_counter"): "admin_client.table(\"users\").update(",
    ("app/api/auth_routes.py", "_inherit_device_counter_with_legacy"): "admin_client.table(\"users\").update(",
    ("app/services/auth_service.py", "register_user"): "admin = get_admin_client()",
    ("app/services/auth_service.py", "sign_in_with_social"): "admin = get_admin_client()",
    ("app/services/database_service.py", "create_user"): "client = get_supabase_client()",
    ("app/services/database_service.py", "update_user_subscription"): "client = get_supabase_client()",
    ("app/services/referral_service.py", "ensure_code_for_user"): "self.client.table(\"users\").update(",
    ("app/services/referral_service.py", "get_status"): "self.client.table(\"users\").update(",
    ("app/services/referral_service.py", "_grant_loop2_rewards"): "self.client.table(\"users\").update(",
    ("app/services/usage_service.py", "_maybe_reset_referral_bonus"): "client.table(\"users\").update(",
}


def _users_write_keys(func: ast.AST) -> set:
    """Keys of every dict passed to .update / .insert / .upsert on a table("users") chain."""
    dict_vars = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    dict_vars.setdefault(tgt.id, set()).update(
                        k.value for k in node.value.keys if isinstance(k, ast.Constant))
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (isinstance(tgt, ast.Subscript) and isinstance(tgt.value, ast.Name)
                        and isinstance(tgt.slice, ast.Constant)):
                    dict_vars.setdefault(tgt.value.id, set()).add(tgt.slice.value)
    keys = set()
    for node in ast.walk(func):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("update", "insert", "upsert") and node.args):
            continue
        recv = node.func.value
        if not (isinstance(recv, ast.Call) and isinstance(recv.func, ast.Attribute) and recv.func.attr == "table"
                and recv.args and isinstance(recv.args[0], ast.Constant) and recv.args[0].value == "users"):
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Dict):
            keys.update(k.value for k in arg.keys if isinstance(k, ast.Constant))
        elif isinstance(arg, ast.Name):
            keys.update(dict_vars.get(arg.id, set()))
    return keys


def _walk_writers():
    found = {}
    for base in ("app", "scripts"):
        for path in sorted((ROOT / base).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    keys = _users_write_keys(node)
                    if keys:
                        found[(rel, node.name)] = (keys, ast.get_source_segment(path.read_text(encoding="utf-8"), node))
    return found


def test_w01_guarded_column_writers_are_the_walked_admin_set():
    found = _walk_writers()
    guarded_writers = {k for k, (keys, _src) in found.items() if keys & set(GUARDED)}
    assert guarded_writers == set(ADMIN_WRITERS), sorted(guarded_writers ^ set(ADMIN_WRITERS))
    for key, token in ADMIN_WRITERS.items():
        assert token in found[key][1], key


def test_w02_user_scoped_writers_touch_no_guarded_column():
    found = _walk_writers()
    user_scoped = {k: keys for k, (keys, src) in found.items() if "get_user_supabase_client" in src}
    assert set(user_scoped) == {
        ("app/api/auth_routes.py", "update_push_token"),
        ("app/api/auth_routes.py", "update_reengagement_subs"),
        ("app/api/auth_routes.py", "update_preference_toggles"),
    }, sorted(user_scoped)
    for key, keys in user_scoped.items():
        assert not keys & set(GUARDED), (key, keys)


def test_w03_the_admin_tokens_resolve_to_the_service_role_client():
    db = (ROOT / "app/services/database_service.py").read_text(encoding="utf-8")
    assert re.search(r"def get_supabase_client\(\) -> Client:.*?return get_admin_supabase_client\(\)", db, re.DOTALL)
    ref = (ROOT / "app/services/referral_service.py").read_text(encoding="utf-8")
    assert "self.client = get_admin_supabase_client()" in ref
    usage = (ROOT / "app/services/usage_service.py").read_text(encoding="utf-8")
    tier = usage.split("async def _get_user_tier_info", 1)[1].split("\ndef ", 1)[0]
    assert "client = get_admin_supabase_client()" in tier and "_maybe_reset_referral_bonus(client, user_id, data)" in tier
    assert usage.count("_maybe_reset_referral_bonus(") == 2, "one definition, one caller"
    auth = (ROOT / "app/services/auth_service.py").read_text(encoding="utf-8")
    assert re.search(r"def get_admin_client\(\) -> Client:.*?SUPABASE_SERVICE_KEY|def get_admin_client\(\) -> Client:.*?service", auth, re.DOTALL)


def test_w04_entitlement_rpcs_run_through_the_admin_client():
    usage = (ROOT / "app/services/usage_service.py").read_text(encoding="utf-8")
    for m in re.finditer(r"client\.rpc\(\"increment_lifetime_comparisons\"", usage):
        before = usage[:m.start()].rsplit("client = ", 1)[1].split("\n", 1)[0]
        assert before == "get_admin_supabase_client()", before
    db = (ROOT / "app/services/database_service.py").read_text(encoding="utf-8")
    cascade = db.split("async def delete_user_data_cascade", 1)[1].split("\nasync def ", 1)[0]
    assert "client = get_admin_supabase_client()" in cascade and "delete_user_cascade" in cascade
