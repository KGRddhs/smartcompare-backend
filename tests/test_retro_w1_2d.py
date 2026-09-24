"""R-MIG retro-fix W1-2d: 037 must apply on today's production schema, where
035 and 036 are NOT applied.

SPEC: the retro adversary report on W1-2 (PR #153) defect 3, plus the
orchestrator's binding rulings for W1-2d:

  * statement 4 becomes conditional on
    `to_regprocedure('public.home_savings_aggregate(uuid)')`, so 037 no longer
    depends on 035 (which it never did) or 036;
  * the apply order is corrected everywhere it is written — the 037 header and
    the next-units doc lines here (CLAUDE.md is a docs PR: the sentence is
    recorded in .qa-retro/R-MIG_pr_body_facts.txt, CLAUDE.md is not edited).

RE-MEASURED for this unit on a LOCAL throwaway PostgreSQL 18.1 cluster
(Supabase-style roles, stock default privileges, stand-in function bodies with
the real signatures), on a schema WITHOUT 036:
  * `psql -v ON_ERROR_STOP=1 -f migrations/037_...sql` -> rc 3, `ERROR: function
    public.home_savings_aggregate(uuid) does not exist` at :236; the proacl of
    all three existing functions is byte-identical before and after (the whole
    file rolled back). Under psql's default (no ON_ERROR_STOP) the rest of the
    file hits "current transaction is aborted" and COMMIT rolls back — same
    byte-identical ACL. So today the CR-SECURITY-01 fix cannot land until two
    unrelated feature migrations are applied, one of which (035) says in its own
    header not to apply it yet.
  * a scratch copy with statement 4 wrapped in the to_regprocedure DO guard
    applies rc 0 on the same schema and closes delete_user_cascade /
    increment_lifetime_comparisons for anon + authenticated.
  * CONSEQUENCE THE RULING DOES NOT COVER (see the last RED test): if 036 is
    then applied LATE, its PUBLIC-only revoke leaves anon=X on
    home_savings_aggregate (Supabase default privileges); re-running the
    guarded 037 closes it (anon_x true -> false).

The PIN block also kills four of the five mutants the adversary showed
surviving the existing guard (M1 delete statement 4, M2 narrow its revoke to
PUBLIC, M3 drop service_role from resolve_referral_code, M4 drop BEGIN/COMMIT)
and adds an order-aware census that kills M6 (a later DROP+CREATE with no
revoke). Those pins pass today.
"""

from __future__ import annotations

import re

import pytest

from tests._retro_r_mig_sql import (
    MIGRATION_037,
    MIGRATIONS_DIR,
    NEXT_UNITS_DOC,
    GRANT_FN,
    REVOKE_FN,
    arg_types,
    code_only,
    comment_lines,
    create_or_drop_events,
    dollar_bodies,
    forward_sql_files,
    grant_roles,
    header_of,
    install_network_guard,
    norm,
    qualified,
    read,
    revoke_roles,
    security_definer_creates,
    strip_line_comments,
    top_level_revokes,
)

# Migrations written but NOT applied in production (035/036 per the 037 header
# and CLAUDE.md, verified live 2026-09-06: 033/034 applied, 035/036 not).
UNAPPLIED_UPSTREAM = ("035_spec_spine.sql", "036_home_savings_aggregate.sql")

HSA = ("public.home_savings_aggregate", ("uuid",))
RRC = ("public.resolve_referral_code", ("text",))
SERVICE_ROLE_ONLY = {
    ("public.delete_user_cascade", ("uuid",)),
    ("public.increment_lifetime_comparisons", ("uuid",)),
}


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = install_network_guard(monkeypatch)
    yield
    assert not attempts, f"R-MIG tests must never touch the network: {attempts}"


def _functions_created_in_unapplied_upstream() -> set[tuple[str, tuple[str, ...]]]:
    out = set()
    for name in UNAPPLIED_UPSTREAM:
        for sig, _off in create_or_drop_events(read(MIGRATIONS_DIR / name)):
            out.add(sig)
    return out


# ---------------------------------------------------------------------------
# RED — the guard
# ---------------------------------------------------------------------------

def test_unapplied_upstream_census_is_not_vacuous():
    """PIN-ish sanity for the RED test below: 036 creates home_savings_aggregate."""
    assert HSA in _functions_created_in_unapplied_upstream()


def test_every_037_statement_naming_an_unapplied_upstream_function_is_regprocedure_guarded():
    """Every mention (comments stripped) of a function that only an UNAPPLIED
    migration creates must sit inside a dollar-quoted DO body that checks
    `to_regprocedure('public.<name>(<types>)') IS NOT NULL` — PostgreSQL has no
    `REVOKE ... IF EXISTS` for a function, and a top-level REVOKE on a missing
    function aborts the whole transaction (measured, rc 3, ACL unchanged)."""
    raw = strip_line_comments(read(MIGRATION_037))
    spans = dollar_bodies(raw)
    offenders = []
    for (qname, types) in sorted(_functions_created_in_unapplied_upstream()):
        bare = qname.split(".", 1)[1]
        # R-MIG fix (tests_that_prove_nothing, mutant N5): pin the guard's
        # TRUTH VALUE, not just its substring — `IS NOT NULL AND false` (or
        # `OR true`) contains the substring and never / always runs the body.
        # The guard must be the WHOLE IF condition: `IF <guard> THEN`.
        guard = norm(f"if to_regprocedure('{qname}({', '.join(types)})') is not null then")
        for m in re.finditer(re.escape(bare), raw, re.IGNORECASE):
            covering = [(s, e) for s, e in spans if s <= m.start() < e]
            if not covering or not any(
                guard in norm(raw[s:e]).replace(", ", ",").replace(",", ", ")
                for s, e in covering
            ):
                line = raw.count("\n", 0, m.start()) + 1
                offenders.append(f"037:{line} names {qname}{types} outside a to_regprocedure guard")
    assert not offenders, (
        "037 must apply on a database where 035/036 are not applied: "
        f"{offenders}"
    )


# ---------------------------------------------------------------------------
# RED — the apply-order text
# ---------------------------------------------------------------------------

_BAD_ORDER = re.compile(r"035\s*(?:->|→)\s*036\s*(?:->|→)\s*037")


def test_037_header_drops_the_035_036_037_hard_prerequisite():
    header = norm(header_of(read(MIGRATION_037)))
    assert not _BAD_ORDER.search(header), (
        "037's header still prescribes 035 -> 036 -> 037; 037 never depended on "
        "035, and after the guard it does not depend on 036 either"
    )
    assert "hard prerequisite" not in header


def test_037_header_explains_the_guard_and_that_035_is_independent():
    header = norm(comment_lines(header_of(read(MIGRATION_037))))
    assert "to_regprocedure" in header, "the header must explain the statement-4 guard"
    assert re.search(r"035[^.]{0,160}independent|independent[^.]{0,160}035", header), (
        "the corrected order: '037 any time; 036 whenever its flag is readied; "
        "035 independent'"
    )


def test_next_units_doc_no_longer_prescribes_035_036_037():
    text = read(NEXT_UNITS_DOC)
    bad = [
        i + 1
        for i, line in enumerate(text.splitlines())
        if _BAD_ORDER.search(line)
    ]
    assert not bad, (
        "docs/investigations/2026-09-08-session-65-next-units.md still prescribes "
        f"035 -> 036 -> 037 at lines {bad}"
    )


def test_no_investigations_doc_prescribes_035_036_037():
    """R-MIG fix (adversary defect 3): the ruling corrects the apply order
    'everywhere it is written', and docs/investigations/2026-09-11-w3-remainder-
    state.md:126 still told Ahmed to 'apply migrations `035 → 036 → 037`' — the
    false prerequisite (035's own header says not to apply it) in the doc an
    operator reads for their to-do list. Every investigations doc, recursively.
    (CLAUDE.md and docs/CONTEXT_SESSION_LOG.md are corrected by the separate
    docs PR per the ruling; they are not scanned here.)"""
    root = MIGRATIONS_DIR.parent / "docs" / "investigations"
    offenders = [
        f"{path.relative_to(root).as_posix()}:{i + 1}"
        for path in sorted(root.rglob("*.md"))
        for i, line in enumerate(read(path).splitlines())
        if _BAD_ORDER.search(line)
    ]
    assert not offenders, f"035 -> 036 -> 037 is still prescribed at {offenders}"


def test_037_header_says_to_rerun_037_if_036_lands_after_it():
    """BEYOND THE LITERAL RULING — flagged for the orchestrator. With the guard,
    the corrected order lets 036 land AFTER 037; 036's own revoke names PUBLIC
    only, so under Supabase default privileges anon keeps EXECUTE on
    home_savings_aggregate (measured: anon_x=true after a late 036; re-running
    the guarded 037 -> false). The red-gate ruling kept this test AND amended
    036 to revoke FROM PUBLIC, anon (pinned in
    test_pin_036_revokes_home_savings_aggregate_from_anon), so the re-run is
    belt and braces; the header instruction still has to be there."""
    header = norm(comment_lines(header_of(read(MIGRATION_037))))
    assert re.search(r"re-?(run|apply|applied|running|applying)[^.]{0,60}\b037\b[^.]{0,160}\b036\b"
                     r"|\b036\b[^.]{0,200}re-?(run|apply|applied|running|applying)[^.]{0,60}\b037\b",
                     header), (
        "037's header must tell the operator to re-run 037 after 036 is applied "
        "later, or anon keeps EXECUTE on home_savings_aggregate"
    )


# ---------------------------------------------------------------------------
# PINS — pass today, must stay green (M1/M2/M3/M4 killers + guard scope)
# ---------------------------------------------------------------------------

def _all_revokes_incl_bodies(sql: str):
    """REVOKEs anywhere in comment-stripped SQL, INCLUDING dollar bodies (the
    guarded statement 4 lives in one after the fix)."""
    clean = strip_line_comments(sql)
    return [
        ((qualified(m.group(1)), arg_types(m.group(2))), revoke_roles(m.group(3)))
        for m in REVOKE_FN.finditer(clean)
    ]


def _all_grants_incl_bodies(sql: str):
    clean = strip_line_comments(sql)
    return [
        ((qualified(m.group(1)), arg_types(m.group(2))), grant_roles(m.group(3)))
        for m in GRANT_FN.finditer(clean)
    ]


def test_pin_statement_4_narrows_anon_but_never_authenticated():
    """M1 (delete statement 4) and M2 (narrow its revoke to FROM PUBLIC) both
    survived the existing guard. Statement 4 must revoke PUBLIC and anon, must
    NOT revoke authenticated (the RLS-scoped user client calls it), and must
    re-grant authenticated + service_role."""
    sql = read(MIGRATION_037)
    revokes = [roles for sig, roles in _all_revokes_incl_bodies(sql) if sig == HSA]
    assert revokes, "037 statement 4 (home_savings_aggregate revoke) is gone"
    assert all({"public", "anon"} <= set(r) for r in revokes), revokes
    assert all("authenticated" not in r for r in revokes), revokes
    grants = [set(roles) for sig, roles in _all_grants_incl_bodies(sql) if sig == HSA]
    assert grants and all({"authenticated", "service_role"} <= g for g in grants), grants
    assert all(not ({"anon", "public"} & g) for g in grants), grants


def test_pin_036_revokes_home_savings_aggregate_from_anon():
    """Ruling (1): with statement 4 guarded, 036 may land AFTER 037, and then
    036's own revoke is the one that has to close anon. A PUBLIC-only revoke
    leaves Supabase's explicit default anon grant standing (measured locally:
    anon_x=true after a late PUBLIC-only 036). 036's top-level REVOKE must name
    PUBLIC and anon, and must NOT name authenticated (the RLS-scoped user
    client calls it)."""
    revokes = [
        roles
        for sig, roles, _off in top_level_revokes(read(MIGRATIONS_DIR / "036_home_savings_aggregate.sql"))
        if sig == HSA
    ]
    assert revokes, "036 no longer revokes home_savings_aggregate at top level"
    assert all({"public", "anon"} <= set(r) for r in revokes), revokes
    assert all("authenticated" not in r for r in revokes), revokes


def test_pin_036_grants_home_savings_aggregate_to_authenticated_and_service_role_only():
    """R-MIG fix (tests_that_prove_nothing, mutant N6). The REVOKE pin above
    says nothing about 036's GRANT: adding `anon` to it (`TO anon,
    authenticated, service_role`) survived all 96 nodes, and in the '036 lands
    after 037' order the corrected apply order permits, that GRANT is the LAST
    word on the ACL — it would hand anon EXECUTE right back after the revoke.
    036's top-level grant must name exactly authenticated + service_role."""
    grants = [
        set(grant_roles(m.group(3)))
        for m in GRANT_FN.finditer(code_only(read(MIGRATIONS_DIR / "036_home_savings_aggregate.sql")))
        if (qualified(m.group(1)), arg_types(m.group(2))) == HSA
    ]
    assert grants, "036 no longer grants EXECUTE on home_savings_aggregate at top level"
    assert all(g == {"authenticated", "service_role"} for g in grants), grants


def test_pin_no_executable_sql_anywhere_grants_home_savings_aggregate_to_anon_or_public():
    """Same mutant class, estate-wide: a GRANT to anon/PUBLIC on this SECURITY
    DEFINER function in ANY forward migration or rollback (dollar bodies
    included — 037's statement 4 lives in one) re-opens /rpc for anon in
    whichever apply order puts it last. Comments are stripped, so the
    rollbacks' commented-out escape hatches stay allowed."""
    offenders = []
    for path in forward_sql_files() + sorted((MIGRATIONS_DIR / "rollback").glob("*.sql")):
        for sig, roles in _all_grants_incl_bodies(read(path)):
            if sig == HSA and {"anon", "public"} & set(roles):
                offenders.append(f"{path.name}: TO {', '.join(roles)}")
    assert not offenders, offenders


def test_pin_resolve_referral_code_regrant_names_service_role():
    """M3: dropping service_role from the re-grant survived the existing guard;
    in the PUBLIC-default world that leaves referral_service.py's admin-client
    caller with no EXECUTE once PUBLIC is revoked."""
    grants = [set(r) for sig, r in _all_grants_incl_bodies(read(MIGRATION_037)) if sig == RRC]
    assert grants and any({"anon", "authenticated", "service_role"} <= g for g in grants), grants


def test_pin_037_is_exactly_one_transaction():
    """M4: removing BEGIN/COMMIT survived. The header's 'loud and total, never
    half-applied' claim depends on them."""
    stmts = [s.strip().lower() for s in code_only(read(MIGRATION_037)).split(";") if s.strip()]
    assert stmts[0] == "begin", stmts[:1]
    assert stmts[-1] == "commit", stmts[-1:]
    assert stmts.count("begin") == 1 and stmts.count("commit") == 1


def test_pin_only_unapplied_upstream_functions_are_guarded():
    """The guard is for 036's function ONLY. delete_user_cascade,
    increment_lifetime_comparisons and resolve_referral_code exist in
    production; wrapping them too would turn a typo or a signature drift into
    a silent no-op instead of a loud, total rollback."""
    top = top_level_revokes(read(MIGRATION_037))
    top_sigs = {sig for sig, _roles, _off in top}
    for sig in SERVICE_ROLE_ONLY | {RRC}:
        assert sig in top_sigs, f"{sig} must stay a TOP-LEVEL revoke in 037"


def _order_aware_offenders(files: list[tuple[str, str]]) -> list[str]:
    """For every SECURITY DEFINER signature, the LAST forward file that CREATEs
    or DROPs it must be followed — later in that file, or in a later file — by
    a top-level REVOKE naming PUBLIC (and, for the service-role-only pair,
    anon and authenticated too). A DROP+CREATE resets the ACL to the default
    privileges, so a revoke that ran earlier protects nothing."""
    census = set()
    for _name, sql in files:
        census.update(sig for sig, _off in security_definer_creates(sql))
    offenders = []
    for sig in sorted(census):
        last = None
        for idx, (_name, sql) in enumerate(files):
            offs = [off for s, off in create_or_drop_events(sql) if s == sig]
            if offs:
                last = (idx, max(offs))
        if last is None:
            continue
        need = {"public", "anon", "authenticated"} if sig in SERVICE_ROLE_ONLY else {"public"}
        covered = False
        for idx in range(last[0], len(files)):
            for s, roles, off in top_level_revokes(files[idx][1]):
                if s != sig or (idx == last[0] and off < last[1]):
                    continue
                if need <= set(roles):
                    covered = True
        if not covered:
            offenders.append(f"{sig} last (re)defined in {files[last[0]][0]} with no later revoke")
    return offenders


def test_pin_order_aware_census_is_green_on_the_forward_path():
    files = [(p.name, read(p)) for p in forward_sql_files()]
    assert not _order_aware_offenders(files)


def test_pin_order_aware_census_detects_a_later_drop_and_recreate():
    """M6 self-test: a later migration that DROPs and re-CREATEs
    delete_user_cascade as SECURITY DEFINER with no revoke must be flagged —
    the existing set-union guard missed it (21 passed / 4 skipped)."""
    files = [(p.name, read(p)) for p in forward_sql_files()]
    files.append((
        "999_mutant.sql",
        "DROP FUNCTION IF EXISTS public.delete_user_cascade(uuid);\n"
        "CREATE FUNCTION public.delete_user_cascade(target_user_id uuid) RETURNS void "
        "LANGUAGE plpgsql SECURITY DEFINER AS $$ BEGIN END; $$;\n",
    ))
    offenders = _order_aware_offenders(files)
    assert any("delete_user_cascade" in o and "999_mutant.sql" in o for o in offenders), offenders
