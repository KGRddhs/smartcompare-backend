"""Migration 041 — drop the out-of-band `user_events` SELECT policy that lets the
anon role read every row (CR-SECURITY-02, the half migration 037 cannot close).

MEASURED LIVE on 2026-09-24 (Supabase project qulajmyxdbdkchvecmvc, SQL editor,
BEFORE applying 037/040/038), exactly the BEFORE CHECKS 037's header prescribes:

    SELECT c.relowner::regrole, c.relrowsecurity, c.relforcerowsecurity
      FROM pg_class c WHERE c.oid = 'public.user_events'::regclass;
    -> postgres | true | false                (RLS is ALREADY ENABLED)

    SELECT policyname, permissive, cmd, roles, qual, with_check
      FROM pg_policies WHERE schemaname='public' AND tablename='user_events';
    -> "Service role can read all events" | PERMISSIVE | SELECT | {public} | true | NULL
       "Users can insert own events"      | PERMISSIVE | INSERT | {public} | NULL | ((auth.uid() = user_id) OR (user_id IS NULL))
       events_insert                      | PERMISSIVE | INSERT | {public} | NULL | ((auth.uid() = user_id) OR (user_id IS NULL))
       events_select                      | PERMISSIVE | SELECT | {public} | (auth.uid() = user_id) | NULL

    anon-key `HEAD /rest/v1/user_events` with `Prefer: count=exact`
    -> 200, content-range 0-146/147     (147 rows visible to anon)

So 037's THE RULE applies: RLS is already on, and a policy other than
events_insert / events_select exists — the anon read comes from the misnamed
"Service role can read all events" policy (service_role BYPASSES RLS, so a
policy granting it SELECT is meaningless; what the policy actually does is grant
SELECT to every role, including anon). 037's `ENABLE ROW LEVEL SECURITY` is a
no-op here and does NOT close CR-SECURITY-02; the fix 037's header prescribes is
"a follow-up migration that drops (or re-creates) the offending policies BY
NAME, written from that pg_policies output". This is that migration.

Numbering: 038 is W3-16's, 039 is reserved for the M13-29 RLS migration, 040 is
the cleanup_expired_ratings revoke — hence 041.

These tests are pure text scans (no database). RED before the two files exist;
each pin names the mutation that reddens it.
"""

from __future__ import annotations

import re

import pytest

from tests._retro_r_mig_sql import (
    MIGRATIONS_DIR,
    ROLLBACK_DIR,
    code_only,
    comment_lines,
    install_network_guard,
    norm,
    read,
)

MIGRATION_041 = MIGRATIONS_DIR / "041_user_events_drop_public_select_policy.sql"
ROLLBACK_041 = ROLLBACK_DIR / "041_user_events_drop_public_select_policy.sql"

OFFENDING_POLICY = "Service role can read all events"
KEPT_POLICIES = ("events_insert", "events_select", "Users can insert own events")

_DROP_POLICY = re.compile(
    r"DROP\s+POLICY\s+(?P<ifexists>IF\s+EXISTS\s+)?\"(?P<name>[^\"]+)\"\s+ON\s+(?P<table>[A-Za-z0-9_.\"]+)\s*;",
    re.IGNORECASE,
)
_CREATE_POLICY = re.compile(
    r"CREATE\s+POLICY\s+\"(?P<name>[^\"]+)\"\s+ON\s+(?P<table>[A-Za-z0-9_.\"]+)(?P<rest>.*?);",
    re.IGNORECASE | re.DOTALL,
)


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = install_network_guard(monkeypatch)
    yield
    assert attempts == [], f"a pure text scan must never touch the network: {attempts}"


def _forward() -> str:
    assert MIGRATION_041.exists(), f"{MIGRATION_041.name} is missing from migrations/"
    return read(MIGRATION_041)


def _rollback() -> str:
    assert ROLLBACK_041.exists(), f"{ROLLBACK_041.name} is missing from migrations/rollback/"
    return read(ROLLBACK_041)


# ---------------------------------------------------------------------------
# forward migration
# ---------------------------------------------------------------------------


def test_041_exists_and_is_one_transaction():
    """Mutation: delete the file, or drop BEGIN/COMMIT (a half-applied file is
    the failure mode the SQL editor's single-transaction wrap protects against
    only when the file itself is transactional)."""
    clean = code_only(_forward())
    assert re.search(r"^\s*BEGIN\s*;\s*$", clean, re.IGNORECASE | re.MULTILINE), "041 must open with BEGIN;"
    assert re.search(r"^\s*COMMIT\s*;\s*$", clean, re.IGNORECASE | re.MULTILINE), "041 must end with COMMIT;"


def test_041_drops_exactly_the_measured_offending_policy_by_name():
    """The ONE statement that closes CR-SECURITY-02: the misnamed permissive
    SELECT-true policy, dropped by its measured name on public.user_events,
    idempotently (IF EXISTS — a re-run on a database where it is already gone
    must be a NOTICE, not an error that rolls the file back).

    Mutations: rename the policy (nothing is dropped, the leak stays); drop a
    second policy (events_select would take the app's own reads with it);
    remove IF EXISTS (the second apply errors)."""
    drops = list(_DROP_POLICY.finditer(code_only(_forward())))
    assert len(drops) == 1, f"041 must contain exactly ONE DROP POLICY, found {len(drops)}"
    d = drops[0]
    assert d.group("name") == OFFENDING_POLICY, f"041 drops {d.group('name')!r}, not the measured offender"
    assert d.group("table").lower().strip('"') in ("public.user_events", "user_events"), d.group("table")
    assert d.group("ifexists"), "the DROP must be IF EXISTS (idempotent re-run)"


def test_041_keeps_the_three_other_policies_and_touches_nothing_else():
    """Mutations: a blanket loop over pg_policies (the header of 037 forbids it:
    names are unknown until the query runs, and this file is written FROM that
    output); an ALTER TABLE / DISABLE RLS / CREATE POLICY sneaking in; a second
    table."""
    clean = code_only(_forward())
    flat = norm(clean)
    for name in KEPT_POLICIES:
        assert f'drop policy if exists "{name.lower()}"' not in flat and f'drop policy "{name.lower()}"' not in flat, (
            f"041 must not drop {name!r}"
        )
    assert not re.search(r"\bcreate\s+policy\b", flat), "041 creates no policy"
    assert not re.search(r"\balter\s+table\b", flat), "041 alters no table (037 owns ENABLE RLS)"
    assert not re.search(r"\bdisable\s+row\s+level\s+security\b", flat)
    assert not re.search(r"\b(drop|create|alter)\s+(table|function|index|role)\b", flat)
    assert not re.search(r"\bpg_policies\b", clean, re.IGNORECASE), (
        "no catalog loop: the offender is named literally, from the measured output"
    )
    tables = {m.group("table").lower().strip('"') for m in _DROP_POLICY.finditer(clean)}
    assert tables <= {"public.user_events", "user_events"}, tables


def test_041_header_carries_the_measured_census_and_the_proof():
    """The operator header must show what was measured (so the next reader can
    re-run the same query and compare), name the rule in 037 it satisfies, and
    state the after-apply proof. Mutation: strip the header."""
    header = norm(comment_lines(_forward()))
    for needle in (
        OFFENDING_POLICY.lower(),
        "users can insert own events",
        "events_insert",
        "events_select",
        "using (true)",
        "relrowsecurity",
        "147",
        "count=exact",
        "pg_policies",
        "037",
        "cr-security-02",
        "service_role bypasses",
    ):
        assert needle in header, f"041's header is missing {needle!r}"
    assert re.search(r"(must|should) (now )?(return|answer|report|be) 0", header) or "0 rows" in header, (
        "041's header must state the anon count=exact proof (0 rows after apply)"
    )


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------


def test_041_rollback_recreates_the_measured_policy_verbatim_and_warns():
    """A rollback restores the PRIOR state exactly (PERMISSIVE, SELECT, roles
    {public}, USING (true)) — and because that prior state IS the leak, its
    header must say so in plain words. Mutations: 'fix' the rollback into a
    safe policy (then it is not a rollback); drop the warning."""
    creates = list(_CREATE_POLICY.finditer(code_only(_rollback())))
    assert len(creates) == 1, f"the rollback must re-create exactly ONE policy, found {len(creates)}"
    c = creates[0]
    assert c.group("name") == OFFENDING_POLICY
    assert c.group("table").lower().strip('"') in ("public.user_events", "user_events")
    rest = norm(c.group("rest"))
    assert "for select" in rest, "the measured policy is FOR SELECT"
    assert "using (true)" in rest, "the measured policy is USING (true)"
    assert "with check" not in rest, "the measured policy has no WITH CHECK"
    assert "restrictive" not in rest, "the measured policy is PERMISSIVE"
    header = norm(comment_lines(_rollback()))
    assert "re-open" in header or "reopens" in header or "re-opens" in header, (
        "the rollback header must say it re-opens the anon read"
    )
    assert "147" in header and "anon" in header


def test_041_rollback_touches_nothing_else():
    flat = norm(code_only(_rollback()))
    assert not re.search(r"\bdrop\s+policy\b", flat), "the rollback drops nothing"
    assert not re.search(r"\balter\s+table\b", flat)
    assert not re.search(r"\b(drop|create|alter)\s+(table|function|index|role)\b", flat)
