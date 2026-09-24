"""R-MIG retro-fix W1-2b: `cleanup_expired_ratings` is REAL, anon-executable and
out of band — migration 040 closes it; the repo stops asserting it does not exist.

SPEC: the retro adversary report on W1-2 (PR #153) defect 1, plus the
orchestrator's binding rulings for W1-2b:

  * a NEW migration numbered **040** (039 is reserved for the M13-29 RLS
    migration, 038 is W3-16's) carrying an idempotent DO block that, IF a public
    function named `cleanup_expired_ratings` exists, REVOKEs EXECUTE FROM
    PUBLIC, anon, authenticated. Revoke ONLY: no grant to service_role, because
    no repo caller exists (pinned below).
  * 040's header carries the exact catalog queries Ahmed runs first
    (pg_proc / proacl / pg_get_functiondef, and the anon-executable SECURITY
    DEFINER census).
  * the wrong "does not exist" assert in
    test_migration_037_security_definer_grants.py::
    test_census_sees_the_known_security_definer_functions is deleted and
    replaced with a pin that 040 names the function.
  * the 037 header note and the next-units doc lines that call it nonexistent
    are corrected.

WHY THE OLD CLAIM WAS WRONG (evidence in the repo, not just the report):
docs/investigations/2026-09-06-full-review-verified.json records "cleanup_expired_ratings
exists live but in NO migration" and a GET-only anon probe returning SQLSTATE
25006 "cannot execute DELETE in a read-only transaction" — the anon role passed
the EXECUTE check and the body ran. A repo grep cannot see a function created
out of band. Re-measured for this unit on a LOCAL throwaway PostgreSQL 18.1
cluster (Supabase-style roles + stock default privileges, stand-in body): after
the repo's 036 then 037, `has_function_privilege('anon', …)` is still TRUE for
an out-of-band `cleanup_expired_ratings()` and the anon read-only call still
reaches its DELETE (25006), while delete_user_cascade answers 42501.

RED tests fail today because 040 does not exist and the prose/assert are
unchanged. PIN tests pass today and must stay green through the fix.
"""

from __future__ import annotations

import re

import pytest

from tests._retro_r_mig_sql import (
    MIGRATION_037,
    MIGRATIONS_DIR,
    NEXT_UNITS_DOC,
    REPO_ROOT,
    TEST_037,
    comment_lines,
    code_only,
    dollar_bodies,
    forward_sql_files,
    function_source,
    install_network_guard,
    norm,
    read,
    security_definer_creates,
    strip_line_comments,
)

FN = "cleanup_expired_ratings"


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = install_network_guard(monkeypatch)
    yield
    assert not attempts, f"R-MIG tests must never touch the network: {attempts}"


def _migration_040():
    hits = sorted(MIGRATIONS_DIR.glob("040_*.sql"))
    if len(hits) != 1:
        pytest.fail(
            f"expected exactly one migrations/040_*.sql (W1-2b ruling: 040 carries "
            f"the cleanup_expired_ratings revoke; 038 is W3-16's, 039 is the "
            f"M13-29 RLS migration's), found {[p.name for p in hits]}"
        )
    return hits[0]


# ---------------------------------------------------------------------------
# RED — migration 040
# ---------------------------------------------------------------------------

def test_migration_040_exists_exactly_once():
    path = _migration_040()
    assert path.stat().st_size > 0


def _do_body_040() -> str:
    """The ONE dollar-quoted DO body of 040, comments stripped, normalised."""
    raw = strip_line_comments(read(_migration_040()))
    bodies = [norm(raw[s:e]) for s, e in dollar_bodies(raw)]
    assert len(bodies) == 1, f"040 must carry exactly one DO body, found {len(bodies)}"
    return bodies[0]


# `FOR <rec> IN SELECT <list> FROM <from> WHERE <cond> LOOP` inside 040's body.
_FOR_LOOP = re.compile(
    r"\bfor\s+(?P<rec>\w+)\s+in\s+select\s+(?P<cols>.*?)\s+from\s+(?P<frm>.*?)"
    r"\s+where\s+(?P<cond>.*?)\s+loop\b"
)
# The revoke the loop EXECUTEs: `EXECUTE format('<literal>', <rec>.<a>, <rec>.<b>);`
_EXECUTED_REVOKE = re.compile(
    r"\bexecute\s+format\s*\(\s*'(?P<lit>revoke\s+[^']*)'\s*,\s*(?P<args>[^;]*?)\)\s*;"
)


def test_040_revokes_cleanup_expired_ratings_from_public_anon_and_authenticated():
    """The revoke is dynamic (`EXECUTE format('REVOKE ... %s FROM ...')`)
    because the live signature is unknown. It must name all three default
    grantees — a PUBLIC-only revoke leaves Supabase's explicit anon grant
    standing (measured on the local cluster: `anon=X/postgres` survives a
    PUBLIC-only revoke).

    R-MIG fix (adversary defect 2, mutant N2): the roles are read from the
    literal that `EXECUTE format(...)` RUNS, not from any revoke-shaped string.
    `PERFORM format(...)` builds the same string and never runs it — measured
    on the local PG 18 cluster: rc 0, NOTICE 'revoked EXECUTE on 2 ...
    signature(s)', and anon still executed cleanup_expired_ratings."""
    body = _do_body_040()
    m = _EXECUTED_REVOKE.search(body)
    assert m, (
        "040's DO body must RUN its revoke via `EXECUTE format('REVOKE ...', ...)`; "
        "a `PERFORM format(...)` (or a bare string) builds it and never executes it"
    )
    lit = m.group("lit")
    assert re.match(r"revoke\s+(?:all(?:\s+privileges)?|execute)\s+on\s+function\b", lit), lit
    tail = re.search(r"\bfrom\s+(.+)$", lit)
    assert tail, f"the executed revoke names no grantee: {lit!r}"
    roles = {
        r.strip().strip('"')
        for r in re.sub(r"\b(cascade|restrict)\b", " ", tail.group(1)).split(",")
        if r.strip()
    }
    assert {"public", "anon", "authenticated"} <= roles, (
        "040 must `REVOKE ALL ON FUNCTION <cleanup_expired_ratings sig> FROM PUBLIC, "
        f"anon, authenticated`; the executed revoke names {sorted(roles)}"
    )
    assert body.count("execute format(") == 1, (
        "exactly one dynamic statement: the per-signature revoke"
    )


def test_040_loop_is_filtered_to_exactly_cleanup_expired_ratings_in_public():
    """R-MIG fix (adversary defect 1, mutants N1 and N4). The ONE property that
    keeps 040 from revoking EXECUTE on every function in schema public is the
    loop's name filter. Measured on the local PG 18 cluster: with
    `AND p.proname = 'cleanup_expired_ratings'` deleted, 040 applied rc 0,
    printed '040: revoked EXECUTE on 6 public.cleanup_expired_ratings
    signature(s)', and took EXECUTE from anon AND authenticated on all 6
    public functions — resolve_referral_code (signup's anon RPC) and an
    unrelated get_public_stats included. `LIKE 'cleanup%'` widens it the same
    way. So: the loop's WHERE must be a pure AND of equality predicates, one of
    them `proname = 'cleanup_expired_ratings'` and one restricting the schema
    to public; no OR, no pattern match."""
    body = _do_body_040()
    m = _FOR_LOOP.search(body)
    assert m, "040's DO body must loop `FOR <rec> IN SELECT ... FROM ... WHERE ... LOOP`"
    assert re.search(r"\bpg_proc\b", m.group("frm")), "the loop must read pg_proc"
    cond = m.group("cond")
    assert not re.search(r"\bor\b|\bnot\b|\blike\b|\bilike\b|\bsimilar\b|~|\bany\b|\bin\s*\(", cond), (
        f"the loop's WHERE must be a pure AND of equalities, got {cond!r}"
    )
    conjuncts = [c.strip().strip("()").strip() for c in re.split(r"\band\b", cond)]
    assert any(
        re.fullmatch(r"(?:\w+\.)?proname\s*=\s*'cleanup_expired_ratings'", c) for c in conjuncts
    ), (
        "the loop must be filtered to `proname = 'cleanup_expired_ratings'` — without "
        f"it 040 revokes every public function; WHERE conjuncts: {conjuncts}"
    )
    assert any(
        re.fullmatch(r"(?:\w+\.)?nspname\s*=\s*'public'", c)
        or re.fullmatch(r"(?:\w+\.)?pronamespace\s*=\s*'public'::regnamespace", c)
        for c in conjuncts
    ), f"the loop must be restricted to schema public; WHERE conjuncts: {conjuncts}"


def test_040_revokes_by_identity_signature_so_a_default_argument_cannot_break_apply():
    """R-MIG fix (adversary defect 2, mutant N3). `REVOKE ... ON FUNCTION f(<args>)`
    accepts only the identity argument list. `pg_get_function_arguments`
    renders DEFAULTs too — measured on the local PG 18 cluster with an overload
    `cleanup_expired_ratings(p_days integer DEFAULT 7)`: `syntax error at or
    near "DEFAULT"`, rc 3, the whole apply rolled back. The loop must feed the
    revoke from `pg_get_function_identity_arguments` (or `oid::regprocedure`),
    and the executed format args must be the loop record's columns."""
    body = _do_body_040()
    assert not re.search(r"\bpg_get_function_arguments\s*\(", body), (
        "pg_get_function_arguments renders DEFAULT clauses and breaks the REVOKE"
    )
    loop = _FOR_LOOP.search(body)
    run = _EXECUTED_REVOKE.search(body)
    assert loop and run, "040's loop / executed revoke not found"
    rec = loop.group("rec")
    cols = loop.group("cols")
    identity = re.search(
        r"pg_get_function_identity_arguments\s*\(\s*(?:\w+\.)?oid\s*\)\s+as\s+(\w+)", cols
    )
    regproc = re.search(r"(?:\w+\.)?oid\s*::\s*regprocedure\s+as\s+(\w+)", cols)
    assert identity or regproc, (
        "the loop must select the identity signature "
        f"(pg_get_function_identity_arguments or oid::regprocedure): {cols!r}"
    )
    args = [a.strip() for a in run.group("args").split(",")]
    sig_col = (identity or regproc).group(1)
    assert f"{rec}.{sig_col}" in args, (
        f"the executed revoke must be fed the loop's identity column {rec}.{sig_col}; got {args}"
    )
    if identity:
        assert re.search(r"(?:\w+\.)?proname\b", cols) and f"{rec}.proname" in args, (
            "with identity args, the function name must come from the loop record too"
        )
        assert "public.%i(%s)" in run.group("lit"), (
            "the executed revoke must target public.%I(%s) — schema-qualified, "
            "name quoted as an identifier, identity args spliced"
        )


def test_040_resolves_the_function_by_name_from_the_catalog_inside_a_do_block():
    """Idempotent and signature-agnostic: nobody knows the live argument list,
    so a hardcoded `cleanup_expired_ratings()` REVOKE would error (or, behind a
    to_regprocedure guess, silently no-op) on any other signature. The ruling:
    'if a public function of that name exists'. Verified implementable on the
    local cluster: a DO block looping `pg_proc` by proname in schema public and
    EXECUTE-ing the revoke per `oid::regprocedure` returns rc=0 on a database
    WITHOUT the function, rc=0 WITH it (anon then gets 42501), and rc=0 again
    on re-run. (The name filter itself is pinned, as a WHERE conjunct, by
    test_040_loop_is_filtered_to_exactly_cleanup_expired_ratings_in_public —
    the substring checks here are satisfied by the SELECT list alone.)"""
    raw = strip_line_comments(read(_migration_040()))
    flat = norm(raw)
    assert re.search(r"\bdo\s+\$", flat), "040 must be a DO block (idempotent, guarded)"
    assert "pg_proc" in flat and "proname" in flat, (
        "040 must resolve the function(s) by NAME from pg_proc, not from a guessed signature"
    )
    assert "'public'" in flat or "'public'::regnamespace" in flat, (
        "040 must restrict the lookup to schema public"
    )
    inside = [norm(raw[s:e]) for s, e in dollar_bodies(raw)]
    assert any("revoke" in body and "pg_proc" in body for body in inside), (
        "the REVOKE must sit INSIDE the guarded DO body, so a database without "
        "the function applies 040 as a no-op instead of failing"
    )
    top_level = norm(code_only(read(_migration_040())))
    assert "revoke" not in top_level, (
        "a top-level REVOKE on an out-of-band function fails the whole apply "
        "wherever the function (or that signature) is absent"
    )


def test_040_grants_nothing_and_neither_creates_nor_drops_the_function():
    """Revoke only (ruling: grant to service_role only if a repo caller exists —
    none does, see the pin below). 040 must not guess the body (CREATE) nor
    destroy a live object nobody has read (DROP)."""
    flat = norm(strip_line_comments(read(_migration_040())))
    assert not re.search(r"\bgrant\b", flat), "040 must not GRANT anything"
    assert not re.search(r"\bcreate\s+(or\s+replace\s+)?function\b", flat), (
        "040 must not (re)create cleanup_expired_ratings — its live body is unknown"
    )
    assert not re.search(r"\bdrop\s+function\b", flat), "040 must not DROP the function"


def test_040_header_carries_the_catalog_queries_ahmed_runs_first():
    """Before anyone trusts 040: read the real signature, ACL and body, and run
    the anon-executable SECURITY DEFINER census in the same session."""
    prose = norm(comment_lines(read(_migration_040())))
    for needle, why in (
        (FN, "the function this migration exists for"),
        ("pg_proc", "the catalog the queries read"),
        ("proacl", "the ACL column that shows anon=X / =X/postgres"),
        ("pg_get_functiondef", "the live body, which exists in no migration"),
        ("prosecdef", "SECURITY DEFINER flag for the census"),
        ("has_function_privilege('anon'", "the anon-executable census predicate"),
    ):
        assert needle in prose, f"040 header must carry {why}: `{needle}` missing"


# ---------------------------------------------------------------------------
# RED — the false refutation, in the test and in the prose
# ---------------------------------------------------------------------------

def test_census_parser_pin_no_longer_asserts_cleanup_expired_ratings_is_absent():
    src = function_source(TEST_037, "test_census_sees_the_known_security_definer_functions")
    assert src is not None, (
        "keep the parser pin (it guards every census test from going vacuous); "
        "only its wrong cleanup_expired_ratings assert is to be deleted"
    )
    flat = norm(src)
    assert "does not exist in this repo" not in flat and "no such function exists" not in flat, (
        "the census pin still tells future authors cleanup_expired_ratings does "
        "not exist — the live review measured it present (25006 on an anon GET)"
    )
    assert not re.search(r"assert\s+not\s+\[[^\]]*cleanup_expired_ratings", flat), (
        "the absence assertion over the census is still there"
    )
    assert "040" in flat, "replace it with a pin that migration 040 names the function"


def test_037_header_no_longer_calls_cleanup_expired_ratings_nonexistent():
    prose = norm(comment_lines(read(MIGRATION_037)))
    assert "no such function exists" not in prose, (
        "037's header still says cleanup_expired_ratings does not exist"
    )
    assert "040" in prose, "037's header must point at 040 for cleanup_expired_ratings"


def test_next_units_doc_no_longer_calls_cleanup_expired_ratings_nonexistent():
    text = norm(read(NEXT_UNITS_DOC))
    assert "cleanup_expired_ratings` does not exist" not in text, (
        "docs/investigations/2026-09-08-session-65-next-units.md still says "
        "`cleanup_expired_ratings` DOES NOT EXIST (line ~64)"
    )
    assert "040" in text, "the next-units doc must name migration 040 as the fix"


# ---------------------------------------------------------------------------
# PINS — pass today, must stay green
# ---------------------------------------------------------------------------

def test_pin_migration_numeric_prefixes_are_unique():
    """038 (W3-16), 039 (M13-29 RLS) and 040 (this unit) are being written in
    parallel; migration numbers have collided between workstreams before."""
    seen: dict[str, list[str]] = {}
    for path in forward_sql_files():
        m = re.match(r"^(\d+)_", path.name)
        if m:
            seen.setdefault(m.group(1), []).append(path.name)
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dupes, f"duplicate migration numbers: {dupes}"


def test_pin_only_migration_040_touches_cleanup_expired_ratings_in_code():
    offenders = [
        p.name
        for p in forward_sql_files()
        if FN in norm(strip_line_comments(read(p))) and not p.name.startswith("040_")
    ]
    assert not offenders, (
        f"{FN} must be handled by migration 040 only (038/039 are other units'): {offenders}"
    )


def test_pin_no_repo_caller_of_cleanup_expired_ratings_so_revoke_only_is_safe():
    """The ruling's 'revoke only' rests on this: no caller in app/ or scripts/.
    If one appears, a service_role grant (or a caller change) must be decided
    before 040 is applied."""
    callers = []
    for base in ("app", "scripts"):
        for path in (REPO_ROOT / base).rglob("*.py"):
            try:
                if FN in path.read_text(encoding="utf-8", errors="ignore"):
                    callers.append(path.relative_to(REPO_ROOT).as_posix())
            except OSError:
                continue
    assert not callers, f"a repo caller of {FN} now exists: {callers}"


def test_pin_census_still_sees_the_four_known_security_definer_functions():
    census = set()
    for path in forward_sql_files():
        census.update(sig for sig, _off in security_definer_creates(read(path)))
    for sig in (
        ("public.delete_user_cascade", ("uuid",)),
        ("public.increment_lifetime_comparisons", ("uuid",)),
        ("public.resolve_referral_code", ("text",)),
        ("public.home_savings_aggregate", ("uuid",)),
    ):
        assert sig in census, f"census lost {sig}"
