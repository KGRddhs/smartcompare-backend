"""W1-2 — every SECURITY DEFINER function in migrations/ must be locked down.

Findings `CR-SECURITY-01` (SECURITY DEFINER functions executable by PUBLIC) and
`CR-SECURITY-02` (`user_events` readable by the anon role).

This file has TWO HALVES WITH DIFFERENT LIFETIMES, and that split is the point
of the unit:

  * The SOURCE half (everything above the `live_db` class) is a static scan of
    `migrations/`. It runs in CI on every push, it is what stops migration 038
    repeating the mistake, and it keeps working whether or not anybody ever
    applies 037.

  * The `live_db` half can actually SEE the finding. A source scan cannot tell
    you whether the live database matches the SQL in this repo — `010:12`
    already says `ALTER TABLE user_events ENABLE ROW LEVEL SECURITY` and
    `010:56-59` already defines `events_insert` / `events_select`, so the
    source is RIGHT and the finding is that production does not match it. Those
    pins are marked `live_db` (CI skips them; `LIVE=1` is required to restore
    credentials, see `tests/_env_safety.py`) and are meant to be run BY HAND,
    ONCE, AFTER migration 037 is applied. That run — not the merge of this
    file — is the evidence that production is fixed.

WHY "THE SERVICE ROLE BYPASSES GRANTS" IS NOT A PREMISE THIS FILE RESTS ON
(the correction that drives the shape of the guards below):

  Supabase's `service_role` is an ordinary role carrying `BYPASSRLS`. It is NOT
  a superuser, and `BYPASSRLS` is about ROW security — it says nothing about
  the EXECUTE privilege. A role may call a function only through a grant to
  itself, to `PUBLIC`, or to a role it is a member of. On a stock Supabase
  project the `postgres`-owned functions in `public` also carry EXPLICIT
  default-privilege grants to `anon, authenticated, service_role`, and we
  CANNOT see this database's real ACL from a repo checkout.

  Both readings therefore have to be survivable, and only one shape is:

    REVOKE ALL ON FUNCTION public.f(args) FROM PUBLIC, anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.f(args) TO service_role;

  A PUBLIC-only revoke is the no-op case — if `anon` holds an explicit grant it
  survives untouched and the finding is not closed — and an absent
  `TO service_role` grant is the outage case, because `service_role`'s EXECUTE
  might have been resting on exactly the default the revoke removes.

WHY THE FOUR FUNCTIONS ARE NOT THE SAME PROBLEM (measured, not read):

  | function                            | defined at         | REVOKE? | GRANT?                    |
  |-------------------------------------|--------------------|---------|---------------------------|
  | delete_user_cascade(uuid)           | 010:70, 025:28     | no      | none                      |
  | increment_lifetime_comparisons(uuid)| 011:55             | no      | none                      |
  | resolve_referral_code(text)         | 014:97             | no      | anon, authenticated 014:102|
  | home_savings_aggregate(uuid)        | 036:47             | yes 036:94 | authenticated, service_role 036:95 |

  * `delete_user_cascade` and `increment_lifetime_comparisons` are reached ONLY
    through the service-role client (`database_service.py:384`;
    `usage_service.py:514` and `:706`, all `get_admin_supabase_client()`), so
    `service_role` is the only role that needs EXECUTE — asserted below in both
    directions, so a future migration can neither drop the grant the real
    caller depends on nor "fix" a report by granting them to `authenticated`,
    which would hand every logged-in user a one-call account-destruction
    primitive for ANY uuid plus a freemium-counter primitive.
  * `resolve_referral_code` is DELIBERATELY granted to `anon`: signup resolves
    an invite code before the user exists. That grant is a product requirement,
    not a defect, and the pin below demands the re-GRANT be present AFTER the
    revoke, in the same file.

SCOPE OF EACH SCAN — the two directories are NOT interchangeable:

  * The DEFINITION census covers `migrations/*.sql` AND
    `migrations/rollback/*.sql`. `rollback/025` re-creates
    `delete_user_cascade` as SECURITY DEFINER, and a census a rollback file
    could opt out of would be a census with a hole in it.
  * The REVOKE credit covers `migrations/*.sql` ONLY. A rollback file is not on
    the forward path: nobody runs it as part of applying migrations, so a
    REVOKE that lives only there protects nothing. Crediting it would let the
    guard go green on a database that has never seen the statement.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "migrations"
ROLLBACK_DIR = MIGRATIONS_DIR / "rollback"

MIGRATION_037 = MIGRATIONS_DIR / "037_security_definer_grants_and_rls.sql"
ROLLBACK_037 = ROLLBACK_DIR / "037_security_definer_grants_and_rls.sql"

# A uuid that cannot belong to a real account. Supabase mints v4 uuids; the nil
# uuid is never generated. Used ONLY by the live pins, and only so that a
# permission error is what is being asserted rather than an effect.
IMPOSSIBLE_USER_ID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# SQL parsing helpers
#
# Everything here strips `--` comments FIRST and blanks dollar-quoted function
# BODIES, so neither prose nor a function body can satisfy a structural claim.
# (The 036 cross-tenant pin in test_migration_index_predicate_immutability.py
# learned the comment half the hard way: its first version passed against a
# file whose auth.uid() appeared only in a comment.)
# ---------------------------------------------------------------------------

_DOLLAR_OPEN = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


def _strip_sql_line_comments(sql: str) -> str:
    """Drop `-- …` line comments, preserving newlines."""
    return "\n".join(re.sub(r"--.*$", "", line) for line in sql.splitlines())


def _blank_dollar_quoted_bodies(sql: str) -> str:
    """Replace the inside of every `$$ … $$` / `$tag$ … $tag$` body with spaces.

    A function body is not DDL about that function's privileges, and it is the
    one place a literal `SECURITY DEFINER` or `REVOKE` could appear as data.
    Blanking (rather than deleting) keeps every offset stable so the
    revoke-before-grant ORDER check below still means what it says.
    """
    out = list(sql)
    i = 0
    n = len(sql)
    while i < n:
        m = _DOLLAR_OPEN.match(sql, i)
        if not m:
            i += 1
            continue
        tag = m.group(0)
        close = sql.find(tag, m.end())
        if close == -1:
            # Unterminated body: leave the remainder alone rather than guess.
            break
        for j in range(m.end(), close):
            if out[j] != "\n":
                out[j] = " "
        i = close + len(tag)
    return "".join(out)


def _code_only(sql: str) -> str:
    return _blank_dollar_quoted_bodies(_strip_sql_line_comments(sql))


def _arg_types(arg_list: str) -> tuple[str, ...]:
    """`'target_user_id UUID'` -> `('uuid',)`; `'uuid'` -> `('uuid',)`.

    Postgres identifies a function by name + argument TYPES, so a REVOKE has to
    be matched to a definition on types, never on the parameter names (a REVOKE
    is normally written with bare types and a CREATE with named parameters).
    """
    types: list[str] = []
    for raw in arg_list.split(","):
        tokens = raw.strip().split()
        if not tokens:
            continue
        types.append(tokens[-1].strip().lower())
    return tuple(types)


def _qualified_name(qualified: str) -> str:
    """`public.delete_user_cascade` -> `public.delete_user_cascade`;
    `delete_user_cascade` -> `public.delete_user_cascade`.

    THE SCHEMA IS KEPT, defaulting to `public` when absent. Dropping it (an
    earlier version of this file did) means a REVOKE written against
    `extensions.delete_user_cascade` — a different function, in a schema this
    project does not serve — would credit the `public` one and the guard would
    go green on an untouched hole. Postgres resolves an unqualified name
    through `search_path`, which on Supabase puts `public` first, so `public`
    is the right default for this repo's files.

    Unquoted identifiers fold to lower case in Postgres, which is what the
    `.lower()` reproduces; this repo contains no quoted identifiers, where the
    fold would be wrong.
    """
    parts = [p.strip().strip('"') for p in qualified.strip().split(".") if p.strip()]
    if not parts:
        return ""
    name = parts[-1].lower()
    schema = parts[-2].lower() if len(parts) > 1 else "public"
    return f"{schema}.{name}"


_CREATE_FN = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+([A-Za-z0-9_.\"]+)\s*\(([^)]*)\)",
    re.IGNORECASE,
)

# `ALTER FUNCTION public.f(uuid) SECURITY DEFINER;` is the OTHER way a function
# becomes SECURITY DEFINER — it needs no CREATE in the same file, so a census
# built only on CREATE would never see it.
_ALTER_FN = re.compile(
    r"ALTER\s+FUNCTION\s+([A-Za-z0-9_.\"]+)\s*\(([^)]*)\)([^;]*);",
    re.IGNORECASE | re.DOTALL,
)

_REVOKE_FN = re.compile(
    r"REVOKE\s+(?:ALL(?:\s+PRIVILEGES)?|EXECUTE)\s+ON\s+FUNCTION\s+"
    r"([A-Za-z0-9_.\"]+)\s*\(([^)]*)\)(.*?);",
    re.IGNORECASE | re.DOTALL,
)

_GRANT_FN = re.compile(
    r"GRANT\s+(?:ALL(?:\s+PRIVILEGES)?|EXECUTE)\s+ON\s+FUNCTION\s+"
    r"([A-Za-z0-9_.\"]+)\s*\(([^)]*)\)\s*TO\s+([^;]+);",
    re.IGNORECASE | re.DOTALL,
)

Signature = tuple[str, tuple[str, ...]]


def _security_definer_functions(sql: str) -> list[Signature]:
    """Return `(qualified_name, arg_types)` for every SECURITY DEFINER function.

    Two forms are recognised:

      * `CREATE [OR REPLACE] FUNCTION … SECURITY DEFINER` — the clause legally
        appears either BEFORE the body (010, 025, 036) or AFTER it
        (`$$ LANGUAGE plpgsql SECURITY DEFINER;` — 011:61), so the whole
        statement, body blanked, is what gets searched: from the CREATE up to
        the first `;` that is not inside a dollar-quoted body.
      * `ALTER FUNCTION … SECURITY DEFINER` — no CREATE required, so a file
        that only flips an existing function still enters the census.
    """
    clean = _code_only(sql)
    found: list[Signature] = []

    for m in _CREATE_FN.finditer(clean):
        end = clean.find(";", m.end())
        stmt = clean[m.start(): end if end != -1 else len(clean)]
        if "security definer" in " ".join(stmt.lower().split()):
            found.append((_qualified_name(m.group(1)), _arg_types(m.group(2))))

    for m in _ALTER_FN.finditer(clean):
        if "security definer" in " ".join(m.group(3).lower().split()):
            found.append((_qualified_name(m.group(1)), _arg_types(m.group(2))))

    deduped: list[Signature] = []
    for sig in found:
        if sig not in deduped:
            deduped.append(sig)
    return deduped


def _revoke_roles(tail: str) -> tuple[str, ...]:
    """Roles named after `FROM` in a REVOKE tail, lower-cased and de-noised."""
    normalized = " ".join(tail.split())
    m = re.search(r"\bfrom\s+(.+)$", normalized, re.IGNORECASE)
    if not m:
        return ()
    body = re.sub(r"\b(cascade|restrict)\b", " ", m.group(1), flags=re.IGNORECASE)
    roles: list[str] = []
    for raw in body.split(","):
        token = raw.strip().strip('"').lower()
        token = re.sub(r"^group\s+", "", token)
        if token:
            roles.append(token)
    return tuple(roles)


def _revokes(sql: str) -> list[tuple[Signature, tuple[str, ...]]]:
    """`(signature, revoked_roles)` for every `REVOKE … ON FUNCTION …`."""
    clean = _code_only(sql)
    out: list[tuple[Signature, tuple[str, ...]]] = []
    for m in _REVOKE_FN.finditer(clean):
        sig = (_qualified_name(m.group(1)), _arg_types(m.group(2)))
        out.append((sig, _revoke_roles(m.group(3))))
    return out


def _revoked_from_public(sql: str) -> list[Signature]:
    """Signatures with a `REVOKE … ON FUNCTION … FROM PUBLIC` in `sql`."""
    return [sig for sig, roles in _revokes(sql) if "public" in roles]


def _function_grants(sql: str) -> list[tuple[Signature, tuple[str, ...]]]:
    """`(signature, roles)` for every GRANT … ON FUNCTION."""
    clean = _code_only(sql)
    out: list[tuple[Signature, tuple[str, ...]]] = []
    for m in _GRANT_FN.finditer(clean):
        sig = (_qualified_name(m.group(1)), _arg_types(m.group(2)))
        roles = tuple(r.strip().lower() for r in m.group(3).split(",") if r.strip())
        out.append((sig, roles))
    return out


def _forward_sql_files() -> list[Path]:
    """The APPLY path. A rollback file is deliberately not on it."""
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _all_sql_files() -> list[Path]:
    return _forward_sql_files() + sorted(ROLLBACK_DIR.glob("*.sql"))


def _sig(name: str, *types: str) -> Signature:
    return (_qualified_name(name), tuple(types))


def _rel(path: Path) -> str:
    """Path relative to the repo root. `migrations/rollback/025_*.sql` and
    `migrations/025_*.sql` share a BASENAME, so a failure message keyed on
    `path.name` names the same file twice and points at neither."""
    return path.relative_to(REPO_ROOT).as_posix()


def _census() -> dict[Signature, list[str]]:
    """signature -> the migration files that define it as SECURITY DEFINER.

    Forward AND rollback: `rollback/025` re-creates `delete_user_cascade`.
    """
    out: dict[Signature, list[str]] = {}
    for path in _all_sql_files():
        sql = path.read_text(encoding="utf-8")
        for sig in _security_definer_functions(sql):
            out.setdefault(sig, []).append(_rel(path))
    return out


def _all_revoked() -> set[Signature]:
    """Signatures revoked from PUBLIC on the FORWARD path only.

    Deliberately NOT `_all_sql_files()`: a REVOKE that exists only in
    `migrations/rollback/` never runs when migrations are applied, so crediting
    it would green this guard against a database where PUBLIC still holds
    EXECUTE.
    """
    revoked: set[Signature] = set()
    for path in _forward_sql_files():
        revoked.update(_revoked_from_public(path.read_text(encoding="utf-8")))
    return revoked


# Signatures whose ONLY callers authenticate as the service role:
#   database_service.py:384  delete_user_cascade             get_admin_supabase_client()
#   usage_service.py:514,706 increment_lifetime_comparisons  get_admin_supabase_client()
# `service_role` is an ordinary role with BYPASSRLS, not a superuser, so it
# needs an EXPLICIT EXECUTE grant — and nobody else may hold one.
SERVICE_ROLE_ONLY = {
    _sig("delete_user_cascade", "uuid"),
    _sig("increment_lifetime_comparisons", "uuid"),
}

# The grantees a stock Supabase project hands EXECUTE by default. A revoke that
# names only PUBLIC leaves these standing, which is the no-op case.
DEFAULT_GRANTEES = ("public", "anon", "authenticated")

# The one deliberate anonymous exposure. Signup resolves an invite code before
# the account exists, so this grant is a product requirement.
RESOLVE_REFERRAL_CODE = _sig("resolve_referral_code", "text")


# ---------------------------------------------------------------------------
# Sanity — a scan that finds nothing passes vacuously
# ---------------------------------------------------------------------------

def test_migration_files_are_discoverable():
    assert _forward_sql_files(), f"no *.sql found under {MIGRATIONS_DIR}"
    assert sorted(ROLLBACK_DIR.glob("*.sql")), f"no *.sql found under {ROLLBACK_DIR}"


def test_census_sees_the_known_security_definer_functions():
    """Parser pin. If this ever shrinks, every guard below went vacuous.

    Also pins the correction to the consolidated report: it names
    `cleanup_expired_ratings` as one of the three offenders and NO SUCH
    FUNCTION EXISTS — `grep -rn cleanup_expired_ratings migrations/ app/`
    returns nothing. The real third offender is `resolve_referral_code`, whose
    fix differs in kind (keep the anon grant).
    """
    census = _census()
    for sig in (
        _sig("delete_user_cascade", "uuid"),
        _sig("increment_lifetime_comparisons", "uuid"),
        RESOLVE_REFERRAL_CODE,
        _sig("home_savings_aggregate", "uuid"),
    ):
        assert sig in census, f"census lost {sig[0]}{sig[1]} — the parser regressed"
    assert not [n for (n, _t) in census if n.endswith(".cleanup_expired_ratings")], (
        "cleanup_expired_ratings does not exist in this repo; do not carry the "
        "consolidated report's text forward"
    )


def test_census_covers_the_rollback_directory():
    """`rollback/025:18` re-creates `delete_user_cascade` as SECURITY DEFINER.

    The DEFINITION census must see it — a rollback that reintroduces the hole
    is a real regression path. (The REVOKE credit is the opposite: forward-only.
    See `test_a_revoke_that_lives_only_in_a_rollback_earns_no_credit`.)
    """
    files = _census().get(_sig("delete_user_cascade", "uuid"), [])
    assert any(f.startswith("migrations/rollback/") for f in files), (
        "the census no longer scans migrations/rollback/ — rollback/025 "
        f"re-creates delete_user_cascade as SECURITY DEFINER; saw {files}"
    )


# ---------------------------------------------------------------------------
# THE DURABLE GUARD
# ---------------------------------------------------------------------------

def test_every_security_definer_function_is_revoked_from_public():
    """A SECURITY DEFINER function runs as its OWNER, so PUBLIC EXECUTE on one
    is a privilege-escalation primitive that PostgREST publishes as
    `/rpc/<name>`. PostgreSQL grants EXECUTE to PUBLIC by DEFAULT, so silence
    is not safety: every such function needs an explicit
    `REVOKE ALL ON FUNCTION … FROM PUBLIC` on the FORWARD path (036:94 is the
    template).

    This is the half of the unit that keeps working whether or not anybody
    applies 037 — it is what stops migration 038 repeating the mistake.
    """
    revoked = _all_revoked()
    offenders = sorted(
        f"{name}({', '.join(types)}) defined in {', '.join(files)}"
        for (name, types), files in _census().items()
        if (name, types) not in revoked
    )
    assert not offenders, (
        "SECURITY DEFINER function(s) with no `REVOKE ALL ON FUNCTION … FROM "
        f"PUBLIC` anywhere in migrations/*.sql: {offenders}. PUBLIC holds "
        "EXECUTE by default and PostgREST exposes every executable function as "
        "an RPC endpoint. Copy the shape at "
        "migrations/036_home_savings_aggregate.sql:94-96 into "
        "migrations/037_security_definer_grants_and_rls.sql. A REVOKE in "
        "migrations/rollback/ does NOT count — it never runs on the apply path."
    )


def test_a_revoke_that_lives_only_in_a_rollback_earns_no_credit():
    """Direct pin on the forward-only rule, so the guard above cannot be
    satisfied by moving its REVOKEs into `migrations/rollback/037_*.sql`.

    Every signature the forward path revokes must be revoked by a file under
    `migrations/` itself, never only by its rollback twin.
    """
    forward = _all_revoked()
    rollback_only: set[Signature] = set()
    for path in sorted(ROLLBACK_DIR.glob("*.sql")):
        for sig in _revoked_from_public(path.read_text(encoding="utf-8")):
            if sig not in forward:
                rollback_only.add(sig)
    census = _census()
    offenders = sorted(
        f"{name}({', '.join(types)})"
        for (name, types) in rollback_only
        if (name, types) in census
    )
    assert not offenders, (
        "these SECURITY DEFINER functions are revoked ONLY in "
        f"migrations/rollback/: {offenders}. A rollback file is not on the "
        "apply path, so that REVOKE protects nothing — move it into "
        "migrations/037_security_definer_grants_and_rls.sql."
    )


def test_service_role_only_functions_are_granted_to_service_role_and_nobody_else():
    """`delete_user_cascade` and `increment_lifetime_comparisons` are called
    ONLY through the service-role client, and `service_role` is an ordinary
    role with `BYPASSRLS` — NOT a superuser. `BYPASSRLS` concerns row security;
    it grants no EXECUTE privilege. So after a revoke that names the default
    grantees, these two need an EXPLICIT
    `GRANT EXECUTE … TO service_role` or the admin client stops being able to
    delete an account and to increment the lifetime counter.

    Both directions are asserted:

      * EXACTLY ONE forward-migration grant to `service_role` per function —
        so the grant cannot be dropped, and cannot be quietly duplicated in a
        later migration with different roles.
      * NO grant to PUBLIC / anon / authenticated in ANY migration file,
        rollback included — granting either function to `authenticated` would
        hand every logged-in user a one-call account-destruction primitive for
        any uuid, and a freemium-counter primitive.
    """
    service_role_grants: dict[Signature, list[str]] = {
        sig: [] for sig in SERVICE_ROLE_ONLY
    }
    forbidden: list[str] = []

    for path in _all_sql_files():
        is_forward = path.parent == MIGRATIONS_DIR
        for sig, roles in _function_grants(path.read_text(encoding="utf-8")):
            if sig not in SERVICE_ROLE_ONLY:
                continue
            name, types = sig
            pretty = f"{_rel(path)}: {name}({', '.join(types)}) TO {list(roles)}"
            if {"public", "anon", "authenticated"} & set(roles):
                forbidden.append(pretty)
            if is_forward and "service_role" in roles:
                service_role_grants[sig].append(pretty)

    assert not forbidden, (
        "these functions are reached only through the service-role client; a "
        "grant to PUBLIC, anon or authenticated can only widen exposure and "
        f"never enables a real caller: {forbidden}"
    )
    for sig, hits in sorted(service_role_grants.items()):
        name, types = sig
        assert len(hits) == 1, (
            f"expected exactly ONE `GRANT EXECUTE ON FUNCTION {name}"
            f"({', '.join(types)}) TO service_role` in migrations/*.sql, found "
            f"{len(hits)}: {hits}. The revoke below names anon and "
            "authenticated as well as PUBLIC, so `service_role` cannot be left "
            "resting on a default grant that the revoke removes."
        )


def test_service_role_only_functions_revoke_the_supabase_default_grantees():
    """`REVOKE … FROM PUBLIC` ALONE IS THE NO-OP CASE.

    On a stock Supabase project the `postgres`-owned functions in `public`
    carry explicit default-privilege grants to `anon, authenticated,
    service_role`. Removing PUBLIC's grant then leaves `anon`'s explicit grant
    exactly where it was, and `/rpc/delete_user_cascade` stays open to an
    unauthenticated caller — the finding, not closed, with a migration in the
    repo that looks like it closed it.

    We cannot read the live ACL from here, so the revoke has to be correct
    under EITHER state: it must name PUBLIC and the two default grantees.
    """
    seen: dict[Signature, list[str]] = {sig: [] for sig in SERVICE_ROLE_ONLY}
    missing: list[str] = []

    for path in _forward_sql_files():
        for sig, roles in _revokes(path.read_text(encoding="utf-8")):
            if sig not in SERVICE_ROLE_ONLY:
                continue
            name, types = sig
            seen[sig].append(_rel(path))
            absent = [role for role in DEFAULT_GRANTEES if role not in roles]
            if absent:
                missing.append(
                    f"{_rel(path)}: REVOKE on {name}({', '.join(types)}) names "
                    f"{list(roles)} — missing {absent}"
                )

    for sig, files in sorted(seen.items()):
        name, types = sig
        assert files, (
            f"no `REVOKE ALL ON FUNCTION {name}({', '.join(types)}) FROM "
            "PUBLIC, anon, authenticated;` in migrations/*.sql"
        )
    assert not missing, (
        "a revoke that does not name anon and authenticated is a no-op "
        "wherever Supabase's default privileges granted them EXECUTE "
        f"explicitly: {missing}"
    )


def test_resolve_referral_code_keeps_its_anon_grant_after_the_revoke():
    """The anon grant at 014:102 is a PRODUCT REQUIREMENT, not a defect: an
    anonymous visitor resolves an invite code before signing up.

    `REVOKE ALL … FROM PUBLIC` removes the grant `anon` inherits through PUBLIC
    as well, so the revoking file MUST re-`GRANT EXECUTE … TO anon,
    authenticated` after it — in that file and after that statement, because
    migrations apply in file order and 014's grant is upstream of 037's revoke.
    Revoking without the re-grant breaks signup on an invite link.
    """
    hits = []
    for path in _forward_sql_files():
        clean = _code_only(path.read_text(encoding="utf-8"))
        for rm in _REVOKE_FN.finditer(clean):
            sig = (_qualified_name(rm.group(1)), _arg_types(rm.group(2)))
            if sig != RESOLVE_REFERRAL_CODE:
                continue
            if "public" not in _revoke_roles(rm.group(3)):
                continue
            regrant_roles: set[str] = set()
            for gm in _GRANT_FN.finditer(clean):
                if gm.start() <= rm.end():
                    continue  # a grant BEFORE the revoke is undone by it
                if (_qualified_name(gm.group(1)), _arg_types(gm.group(2))) != sig:
                    continue
                regrant_roles.update(
                    r.strip().lower() for r in gm.group(3).split(",") if r.strip()
                )
            hits.append((_rel(path), regrant_roles))

    assert hits, (
        "no `REVOKE ALL ON FUNCTION resolve_referral_code(text) FROM PUBLIC` "
        "in migrations/*.sql — it is still exposed by PostgreSQL's PUBLIC "
        "default rather than by its explicit grant"
    )
    for filename, roles in hits:
        assert {"anon", "authenticated"} <= roles, (
            f"{filename} revokes resolve_referral_code(text) from PUBLIC but "
            f"only re-grants to {sorted(roles) or 'nobody'}. Signup resolves an "
            "invite code anonymously — `anon` and `authenticated` must both be "
            "re-granted AFTER the revoke, in the same file."
        )


# ---------------------------------------------------------------------------
# Migration 037 itself
# ---------------------------------------------------------------------------

def test_migration_037_and_its_rollback_exist():
    """036 is the highest committed migration, so 037 is the right number.
    Ship the rollback alongside (032/033/035/036 precedent)."""
    assert MIGRATION_037.exists(), f"missing {MIGRATION_037}"
    assert ROLLBACK_037.exists(), f"missing {ROLLBACK_037}"


def test_migration_037_enables_rls_on_user_events():
    """`CR-SECURITY-02`. The SOURCE has said the right thing since `010:12`
    (`ALTER TABLE user_events ENABLE ROW LEVEL SECURITY`) plus the
    `events_insert` / `events_select` policies at `010:56-59` — the finding is
    that the LIVE database does not match, i.e. 010 never applied that part or
    RLS was turned back off. 037 re-asserts it (idempotent) so that applying
    037 is sufficient; the `live_db` pin below is what proves it took effect.
    """
    if not MIGRATION_037.exists():
        pytest.fail(f"missing {MIGRATION_037}")
    clean = " ".join(_code_only(MIGRATION_037.read_text(encoding="utf-8")).lower().split())
    assert re.search(
        r"alter\s+table\s+(?:public\.)?user_events\s+enable\s+row\s+level\s+security",
        clean,
    ), (
        "037 must re-assert `ALTER TABLE user_events ENABLE ROW LEVEL "
        "SECURITY` — the existing policies are inert while RLS is off on the "
        "live table"
    )


def test_migration_037_header_states_the_apply_order_and_the_live_proof():
    """The operator reads the MIGRATION, not the PR.

    Two facts have to be in that file or the apply is done on wrong
    information: (a) 033 and 034 are ALREADY APPLIED (verified live
    2026-09-06) and only 035 and 036 precede this one, so the order is
    035 -> 036 -> 037; (b) the ACL query and the anon-key RPC probe that
    prove the revoke actually landed. A `proacl` reading is the only way to
    tell "revoked" from "the default grant is still there".
    """
    header = MIGRATION_037.read_text(encoding="utf-8").lower()
    for needle, why in (
        ("035 -> 036 -> 037", "the apply order after 033/034 (already applied)"),
        ("proacl", "the pg_proc ACL query that proves the revoke landed"),
        ("42501", "the anon-key RPC probe's expected permission-denied code"),
        ("service_role=x", "what a correct proacl entry looks like after 037"),
    ):
        assert needle in header, (
            f"migration 037's header must state {why}; `{needle}` is missing"
        )
    assert "033, 034, 035 and 036 are also unapplied" not in header, (
        "033 and 034 ARE applied (verified live 2026-09-06, "
        "CR-DATA-MIGRATIONS-07) — a security migration must not carry a wrong "
        "operational fact"
    )


# ---------------------------------------------------------------------------
# Detector self-tests — the scanner must go red on the pattern it exists for,
# and must NOT be satisfiable by prose. These stay green.
# ---------------------------------------------------------------------------

_UNGUARDED = """
CREATE OR REPLACE FUNCTION public.nuke_everything(target_user_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  DELETE FROM users WHERE id = target_user_id;
END;
$$;
"""

_GUARDED = _UNGUARDED + """
REVOKE ALL ON FUNCTION public.nuke_everything(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.nuke_everything(uuid) TO service_role;
"""


def test_detector_flags_an_unrevoked_security_definer_function():
    assert _security_definer_functions(_UNGUARDED) == [_sig("nuke_everything", "uuid")]
    assert _revoked_from_public(_UNGUARDED) == []


def test_detector_clears_a_revoked_security_definer_function():
    sig = _sig("nuke_everything", "uuid")
    assert sig in _security_definer_functions(_GUARDED)
    assert sig in _revoked_from_public(_GUARDED)


def test_detector_reads_every_role_named_in_a_revoke():
    """The three-role revoke is the whole point of the BLOCKING correction, so
    the parser has to see all three — a reader that stopped at `PUBLIC` would
    make `test_service_role_only_functions_revoke_the_supabase_default_grantees`
    unfalsifiable."""
    (sig, roles), = _revokes(
        "REVOKE ALL ON FUNCTION public.f(uuid) FROM PUBLIC, anon, authenticated;"
    )
    assert sig == _sig("f", "uuid")
    assert roles == ("public", "anon", "authenticated")


def test_detector_matches_a_named_parameter_against_a_bare_type_revoke():
    """A CREATE writes `(target_user_id UUID)`, a REVOKE writes `(uuid)`.
    Postgres identifies the function by TYPES; so must the scan, or every
    revoke would look unmatched and this guard would be permanently red."""
    created = _security_definer_functions(_GUARDED)[0]
    assert created == _revoked_from_public(_GUARDED)[0]


def test_detector_keeps_the_schema_so_a_wrong_schema_revoke_does_not_credit():
    """`extensions.nuke_everything(uuid)` is a DIFFERENT function.

    An earlier version of this file reduced every name to its bare identifier,
    so a revoke in any schema credited the `public` one and the guard could go
    green while the exposed function stayed exposed. An unqualified name still
    resolves to `public` (Supabase's search_path), which 010/011/014 rely on.
    """
    wrong_schema = _UNGUARDED + """
    REVOKE ALL ON FUNCTION extensions.nuke_everything(uuid) FROM PUBLIC;
    """
    assert _security_definer_functions(wrong_schema) == [
        _sig("public.nuke_everything", "uuid")
    ]
    assert _revoked_from_public(wrong_schema) == [
        _sig("extensions.nuke_everything", "uuid")
    ]
    assert _sig("nuke_everything", "uuid") not in _revoked_from_public(wrong_schema)

    unqualified = _UNGUARDED + """
    REVOKE ALL ON FUNCTION nuke_everything(uuid) FROM PUBLIC;
    """
    assert _sig("nuke_everything", "uuid") in _revoked_from_public(unqualified)


def test_detector_ignores_security_definer_in_a_comment():
    """036:27 mentions SECURITY DEFINER in prose. Prose must never register as
    a definition, and prose must never satisfy a REVOKE."""
    prose = """
    -- SECURITY DEFINER (the delete_user_cascade precedent): callable through
    -- the RLS-scoped user client.
    -- REVOKE ALL ON FUNCTION public.ghost(uuid) FROM PUBLIC;
    -- ALTER FUNCTION public.ghost(uuid) SECURITY DEFINER;
    CREATE OR REPLACE FUNCTION public.ghost(p_id uuid)
    RETURNS void LANGUAGE sql AS $$ SELECT 1; $$;
    """
    assert _security_definer_functions(prose) == []
    assert _revoked_from_public(prose) == []


def test_detector_ignores_security_definer_inside_a_function_body():
    """A body is data, not privilege DDL. Blanking bodies is what stops a
    string literal from silently registering as a definition."""
    body = """
    CREATE OR REPLACE FUNCTION public.logger(p_id uuid)
    RETURNS void LANGUAGE plpgsql AS $$
    BEGIN
      INSERT INTO notes (t) VALUES ('SECURITY DEFINER');
      INSERT INTO notes (t) VALUES ('REVOKE ALL ON FUNCTION x(uuid) FROM PUBLIC;');
    END;
    $$;
    """
    assert _security_definer_functions(body) == []
    assert _revoked_from_public(body) == []


def test_detector_sees_security_definer_written_after_the_body():
    """011:61 is `$$ LANGUAGE plpgsql SECURITY DEFINER;` — the clause is legal
    on either side of the body, and missing this form would silently drop
    increment_lifetime_comparisons out of the census."""
    trailing = """
    CREATE OR REPLACE FUNCTION increment_lifetime_comparisons(target_user_id UUID)
    RETURNS void AS $$
    BEGIN
        UPDATE users SET n = n + 1 WHERE id = target_user_id;
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """
    assert _security_definer_functions(trailing) == [
        _sig("increment_lifetime_comparisons", "uuid")
    ]


def test_detector_sees_security_definer_added_by_alter_function():
    """`ALTER FUNCTION public.f(uuid) SECURITY DEFINER;` needs no CREATE in the
    same file, so a census built only on CREATE would never see a migration
    that flips an existing function — the cheapest way to reintroduce this
    finding without tripping any guard."""
    altered = """
    CREATE OR REPLACE FUNCTION public.later_definer(p_id uuid)
    RETURNS void LANGUAGE sql AS $$ SELECT 1; $$;
    ALTER FUNCTION public.later_definer(uuid) SECURITY DEFINER;
    """
    assert _security_definer_functions(altered) == [
        _sig("later_definer", "uuid")
    ]

    # And an ALTER that does something else must NOT enter the census.
    unrelated = """
    ALTER FUNCTION public.later_definer(uuid) SET search_path = public;
    """
    assert _security_definer_functions(unrelated) == []

    # Both forms in one file must collapse to one census entry, not two.
    both = """
    CREATE OR REPLACE FUNCTION public.twice(p_id uuid)
    RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$ BEGIN END; $$;
    ALTER FUNCTION public.twice(uuid) SECURITY DEFINER;
    """
    assert _security_definer_functions(both) == [_sig("twice", "uuid")]


def test_detector_does_not_credit_a_revoke_from_a_role_other_than_public():
    """`REVOKE … FROM anon` is not the guard. Only FROM PUBLIC removes the
    default grant every role inherits."""
    partial = _UNGUARDED + """
    REVOKE ALL ON FUNCTION public.nuke_everything(uuid) FROM anon;
    """
    assert _revoked_from_public(partial) == []


# ---------------------------------------------------------------------------
# LIVE PINS — the half that can actually see the finding.
#
# Marked live_db so CI skips them. NOT RUN as part of this unit, deliberately:
# they reach production infrastructure, and running them BEFORE 037 is applied
# would only re-measure the finding.
#
# WHEN TO RUN: after `037` has been applied to the live database, in order,
# after 035 and 036 (033 and 034 are already applied). That run is the evidence
# that production is fixed. Merging this file changes nothing in production.
#
# HOW TO RUN (PowerShell, from the repo root):
#     $env:LIVE=1
#     $env:PYTHONIOENCODING="utf-8"
#     python -m pytest tests/test_migration_037_security_definer_grants.py `
#         -v -m live_db -p no:randomly
#
# `LIVE=1` is mandatory: without it tests/_env_safety.py has stripped the
# credentials out of the environment and the conftest collection hook skips
# every live-tier item, so a bare `-m live_db` reports "skipped", not "passed".
# ---------------------------------------------------------------------------

def _supabase_available() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))


@pytest.mark.live_db
class TestMigration037LiveGrantsAndRls:
    """Post-apply verification against the real database, with the ANON key.

    The anon key is the right credential for every pin in this class: it is the
    role PostgREST hands an unauthenticated caller, and the whole finding is
    about what that role can reach. It is server-side only — the mobile client
    ships NO Supabase credential (`grep -rniE
    "SUPABASE_ANON|SUPABASE_KEY|SUPABASE_URL|createClient" SmartCompareApp/src
    SmartCompareApp/app.json SmartCompareApp/eas.json` returns nothing, and
    `supabase` does not appear in SmartCompareApp/package.json), which is what
    makes this P1 rather than P0.
    """

    @pytest.fixture
    def anon_client(self):
        if not _supabase_available():
            pytest.skip("SUPABASE_URL / SUPABASE_ANON_KEY not configured")
        from supabase import create_client

        return create_client(
            os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"]
        )

    def test_anon_cannot_read_user_events(self, anon_client):
        """WOULD ASSERT: an unauthenticated `count=exact` over `user_events`
        returns 0 rows.

        RED BEFORE 037 IS APPLIED: the finding recorded 146 rows visible to the
        anon role, containing 7 distinct real user uuids. `events_select` is
        `USING (auth.uid() = user_id)` and an anon caller has a NULL
        `auth.uid()`, so 0 is the only correct answer once RLS is actually in
        effect on the table — a non-zero count means RLS is still off, not that
        the policy is wrong.

        A count, not the rows: this test must never pull other people's event
        data into a CI log.
        """
        result = (
            anon_client.table("user_events")
            .select("id", count="exact")
            .limit(1)
            .execute()
        )
        assert result.count == 0, (
            f"{result.count} user_events rows are readable with the ANON key — "
            "row level security is not in effect on the live table (the "
            "policies from 010:56-59 are inert while RLS is off)"
        )

    def test_anon_cannot_execute_delete_user_cascade(self, anon_client):
        """WOULD ASSERT: `/rpc/delete_user_cascade` is rejected for `anon` with
        PostgreSQL's `42501 permission denied`.

        RED BEFORE 037: PostgreSQL grants EXECUTE to PUBLIC by default and
        nothing has ever revoked it, so the anon role can call a one-statement
        account-destruction primitive for ANY uuid.

        42501 SPECIFICALLY — a 404 / PGRST202 "Could not find the function" is
        NOT accepted as proof. That answer is also what an absent function, a
        typo'd name and a stale PostgREST schema cache produce, so it cannot
        distinguish "037 closed the hole" from "037 was never applied to this
        schema". If PostgREST answers 404 here, settle it with the `proacl`
        query in migration 037's header instead of relaxing this assertion.

        THE ARGUMENT IS THE NIL UUID ON PURPOSE. Never call this with a real
        user id — if the revoke has not taken effect, the call SUCCEEDS and
        destroys that account. The nil uuid deletes nothing (every DELETE
        matches zero rows), so the only observable is the permission error,
        which is exactly what is being asserted. If this ever fails by
        SUCCEEDING, 037 did not take effect and the function is still open.
        """
        with pytest.raises(Exception) as excinfo:
            anon_client.rpc(
                "delete_user_cascade", {"target_user_id": IMPOSSIBLE_USER_ID}
            ).execute()
        message = str(excinfo.value).lower()
        assert "permission denied" in message or "42501" in message, (
            "expected PostgreSQL 42501 permission denied for the anon role; a "
            "404/PGRST202 does not prove the revoke landed (see the proacl "
            f"query in migration 037's header). Got: {excinfo.value!r}"
        )

    def test_anon_cannot_execute_increment_lifetime_comparisons(self, anon_client):
        """WOULD ASSERT: `/rpc/increment_lifetime_comparisons` is rejected for
        `anon` with `42501 permission denied`, on the same terms.

        RED BEFORE 037 for the same reason. This one is a freemium-counter
        primitive rather than a destructive one — an anonymous caller can burn
        any user's lifetime allowance. Same nil-uuid discipline: the UPDATE
        matches zero rows, so only the permission error is observable.
        """
        with pytest.raises(Exception) as excinfo:
            anon_client.rpc(
                "increment_lifetime_comparisons",
                {"target_user_id": IMPOSSIBLE_USER_ID},
            ).execute()
        message = str(excinfo.value).lower()
        assert "permission denied" in message or "42501" in message, (
            "expected PostgreSQL 42501 permission denied for the anon role; a "
            "404/PGRST202 does not prove the revoke landed (see the proacl "
            f"query in migration 037's header). Got: {excinfo.value!r}"
        )

    def test_anon_can_still_resolve_a_referral_code(self, anon_client):
        """WOULD ASSERT: `/rpc/resolve_referral_code` still WORKS for `anon`.

        This is the pin that catches the plausible wrong fix. 037 revokes this
        function from PUBLIC and re-grants it to `anon, authenticated,
        service_role`; if the re-grant is dropped, the source guards above
        still pass their shape checks but every invite link breaks at signup,
        and nothing else in the estate would notice.

        The code below cannot match any real referral code (`referral_code`
        values are `QR-XXXXXX`), so the correct outcome is an EMPTY result set
        — not an error. An exception here means the grant was lost; a non-empty
        result would mean the argument accidentally matched and should be
        changed, not asserted on.
        """
        result = anon_client.rpc(
            "resolve_referral_code", {"p_code": "QR-ZZZZZZ-NOT-A-REAL-CODE"}
        ).execute()
        assert result.data in ([], None), (
            "sentinel code unexpectedly resolved — pick another impossible "
            f"code rather than asserting on real data: {result.data!r}"
        )
