"""R-MIG retro-fix W1-2c: CR-SECURITY-02 has TWO possible live causes, and 037
(plus its rollback) must stop assuming it is "RLS off".

SPEC: the retro adversary report on W1-2 (PR #153) defect 2, plus the
orchestrator's binding rulings for W1-2c:

  * 037's header gains the BEFORE checks — `pg_class relrowsecurity /
    relforcerowsecurity` and `pg_policies` for user_events — and the rule that
    ANY policy other than events_insert / events_select means CR-SECURITY-02 is
    NOT closed by 037.
  * the rollback no longer unconditionally DISABLEs RLS: it restores the
    recorded BEFORE value, with a header warning.
  * the misdiagnosing failure message in
    test_migration_037_security_definer_grants.py::
    TestMigration037LiveGrantsAndRls::test_anon_cannot_read_user_events is fixed.
  * a source pin that the header contains the pg_policies query.

RE-MEASURED for this unit on a LOCAL throwaway PostgreSQL 18.1 cluster
(Supabase-style anon/authenticated/service_role[BYPASSRLS], auth.uid() shim,
010's events_insert/events_select, 4 rows):
  * policy branch — RLS already ON + an out-of-band `FOR SELECT USING (true)`
    policy: anon count = 4 BEFORE 037 and still 4 AFTER the repo's 037
    (relrowsecurity stays t). 037 closes nothing.
  * the repo's rollback/037 then sets relrowsecurity = f (BEFORE was t) and
    anon `DELETE ... RETURNING` removes 1 row — worse than before 037.
  * RLS-off branch (the only one 037's header describes): anon 4 -> 0 after
    037, service_role still reads all rows and inserts an identified row.

RED tests fail today on the unchanged prose/rollback/test message. PIN tests
pass today and must stay green through the fix.
"""

from __future__ import annotations

import re

import pytest

from tests._retro_r_mig_sql import (
    MIGRATION_037,
    ROLLBACK_037,
    TEST_037,
    code_only,
    comment_lines,
    function_source,
    header_of,
    install_network_guard,
    norm,
    read,
    strip_line_comments,
)


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = install_network_guard(monkeypatch)
    yield
    assert not attempts, f"R-MIG tests must never touch the network: {attempts}"


def _header_037() -> str:
    return norm(comment_lines(header_of(read(MIGRATION_037))))


# ---------------------------------------------------------------------------
# RED — 037 header: the BEFORE checks and the rule
# ---------------------------------------------------------------------------

def test_037_header_carries_the_before_rls_state_query_for_user_events():
    """Today `relrowsecurity` appears only in the FORCE note AFTER `BEGIN;`, as
    an owner check — not as a BEFORE check an operator runs and keeps."""
    header = _header_037()
    for needle in ("relrowsecurity", "relforcerowsecurity", "user_events"):
        assert needle in header, (
            f"037's apply-time header (before BEGIN;) must carry the BEFORE "
            f"pg_class check; `{needle}` missing"
        )
    assert re.search(r"pg_class", header), "the BEFORE check reads pg_class"


def test_037_header_carries_the_pg_policies_query_for_user_events():
    header = _header_037()
    assert "pg_policies" in header, "037's header must carry the pg_policies BEFORE query"
    assert re.search(r"tablename\s*=\s*'user_events'", header), (
        "the pg_policies query must filter tablename = 'user_events'"
    )
    assert re.search(r"schemaname\s*=\s*'public'", header), (
        "the pg_policies query must filter schemaname = 'public'"
    )


def test_037_header_states_that_an_extra_policy_means_cr_security_02_is_not_closed():
    header = _header_037()
    assert "events_insert" in header and "events_select" in header, (
        "the rule must name the two expected policies"
    )
    assert re.search(
        r"cr-security-02[^.]{0,200}\b(is\s+not\s+closed|not\s+closed|does\s+not\s+close)"
        r"|(does\s+not\s+close|not\s+close)[^.]{0,120}cr-security-02",
        header,
    ), (
        "037's header must state that RLS already on, or any policy other than "
        "events_insert/events_select, means 037 does NOT close CR-SECURITY-02"
    )


def test_037_header_rule_compares_the_expected_policy_definitions_not_only_names():
    """R-MIG fix (adversary defect 4): a rule keyed on policy NAMES alone calls
    037 a close when events_select itself was redefined out of band under its
    own name. Measured on the local PG 18 cluster: RLS off + events_select
    USING (true) -> after 037 relrowsecurity f -> t and anon still counts 4 of
    4. The header must (a) SELECT every column the comparison needs, (b) print
    010:56-59's definitions as pg_policies renders them, and (c) state that
    any difference also means CR-SECURITY-02 is NOT closed."""
    header = _header_037()
    m = re.search(r"select\s+([^;]*?)\s+from\s+pg_policies\b", header)
    assert m, "037's header lost the pg_policies BEFORE query"
    cols = {c.strip() for c in m.group(1).split(",")}
    missing = {"policyname", "permissive", "cmd", "roles", "qual", "with_check"} - cols
    assert not missing, f"the pg_policies BEFORE query must select {sorted(missing)}"
    # pg_policies' own rendering of 010:56-59 (measured on PG 18.1):
    assert "qual (auth.uid() = user_id)" in header, (
        "the header must print events_select's expected qual as pg_policies renders it"
    )
    assert "with_check ((auth.uid() = user_id) or (user_id is null))" in header, (
        "the header must print events_insert's expected with_check as pg_policies renders it"
    )
    assert re.search(
        r"any\s+difference\s+in\s+permissive,\s+cmd,\s+roles,\s+qual\s+or\s+with_check"
        r"[\s\S]{0,300}?does\s+not\s+close\s+cr-security-02",
        header,
    ), (
        "037's header must state that a same-named policy whose definition "
        "differs from 010:56-59 ALSO means 037 does NOT close CR-SECURITY-02"
    )


def test_pin_037_stays_under_sqlfluffs_large_file_skip_limit():
    """R-MIG fix-phase pin: sqlfluff 4.3.0 (the dev-lock pin) SKIPS any file
    over `large_file_skip_byte_limit` (default 20000 bytes) with only a
    WARNING and exit 0 — measured: the first draft of this fix grew 037 to
    20580 bytes (CRLF working copy) and `sqlfluff lint` printed 'Skipping to
    avoid parser lock' and 'All Finished!'. .sqlfluff promises every migration
    is linted, so the header's growth must not silently opt 037 out."""
    cfg = read(MIGRATION_037.parent.parent / ".sqlfluff")
    m = re.search(r"^\s*large_file_skip_byte_limit\s*=\s*(\d+)", cfg, re.MULTILINE)
    limit = int(m.group(1)) if m else 20000
    if limit == 0:
        return  # the limit is disabled repo-wide; nothing is skipped
    size = MIGRATION_037.stat().st_size  # the working copy: CRLF on Windows, the larger form
    assert size < limit, (
        f"037 is {size} bytes, over sqlfluff's {limit}-byte skip limit: the "
        "pre-commit hook and any lint would silently skip it"
    )


def test_037_header_no_longer_asserts_enable_alone_is_sufficient():
    header = _header_037()
    assert 'only purpose is to make "apply 037" sufficient' not in header, (
        "037's header still asserts the RLS-off cause as fact; measured: with an "
        "out-of-band USING(true) policy, anon reads 4/4 rows after 037"
    )


# ---------------------------------------------------------------------------
# RED — rollback/037
# ---------------------------------------------------------------------------

def test_rollback_037_does_not_unconditionally_disable_rls():
    """A top-level `ALTER TABLE ... DISABLE ROW LEVEL SECURITY` flips the table
    to RLS-off even when it was ON before 037 (measured: relrowsecurity t -> f,
    then anon DELETE ... RETURNING = 1 row). The DISABLE may survive only
    inside a condition on the recorded BEFORE value, or not at all."""
    top = norm(code_only(read(ROLLBACK_037)))
    assert not re.search(
        r"alter\s+table\s+(?:public\.)?user_events\s+disable\s+row\s+level\s+security",
        top,
    ), "rollback/037 still DISABLEs RLS on user_events unconditionally"


def test_rollback_037_header_warns_disable_is_right_only_when_before_was_false():
    prose = norm(comment_lines(read(ROLLBACK_037)))
    assert "relrowsecurity" in prose, (
        "rollback/037 must tell the operator to compare against the recorded "
        "BEFORE relrowsecurity value"
    )
    assert "before" in prose


def test_rollback_037_no_longer_claims_to_restore_the_state_the_finding_recorded():
    prose = norm(comment_lines(read(ROLLBACK_037)))
    assert "returns user_events to the state the finding recorded" not in prose, (
        "false when the live cause was a permissive policy: the rollback then "
        "leaves the table worse than before 037"
    )


# ---------------------------------------------------------------------------
# RED — the live pin's misdiagnosing message
# ---------------------------------------------------------------------------

def test_live_user_events_pin_no_longer_misdiagnoses_a_policy_leak_as_rls_off():
    src = function_source(TEST_037, "test_anon_cannot_read_user_events")
    assert src is not None, "keep the live user_events pin"
    flat = norm(src)
    assert "not that the policy is wrong" not in flat, (
        "the pin still says a non-zero count means RLS is off, not a policy "
        "problem — the permissive-policy branch produces the same count"
    )
    assert "pg_policies" in flat, (
        "the failure text must send the operator to the pg_policies query too"
    )


# ---------------------------------------------------------------------------
# PINS — pass today, must stay green
# ---------------------------------------------------------------------------

def test_pin_037_still_enables_rls_and_does_not_force_disable_or_touch_policies():
    """037 must not guess policy names (the ruling moves any drop to a follow-up
    written from the pg_policies output) and FORCE stays undecided."""
    top = norm(code_only(read(MIGRATION_037)))
    assert re.search(
        r"alter\s+table\s+(?:public\.)?user_events\s+enable\s+row\s+level\s+security", top
    )
    assert not re.search(r"\bforce\s+row\s+level\s+security\b", top)
    assert not re.search(r"\bdisable\s+row\s+level\s+security\b", top)
    assert not re.search(r"\b(create|drop|alter)\s+policy\b", top)


def test_pin_rollback_037_ships_a_null_before_value_and_disables_only_when_it_was_false():
    """Green-phase pin on ruling (4): the rollback restores the RECORDED BEFORE
    value of relrowsecurity. The source can only pin the shape (the behaviour
    was run on the local PG 18 cluster): the value ships as NULL, a NULL value
    RAISEs (nothing changes on an unedited run), the TRUE branch does not
    DISABLE, and the only DISABLE sits in the final ELSE branch (value false).
    Deleting the IF, dropping the RAISE, or defaulting the value to false each
    turn this red."""
    body = norm(strip_line_comments(read(ROLLBACK_037)))
    assert re.search(r"before_relrowsecurity\s+boolean\s*:=\s*null\s*;", body), (
        "rollback/037 must ship before_relrowsecurity := NULL so an unedited run "
        "changes nothing"
    )
    m = re.search(
        r"if\s+before_relrowsecurity\s+is\s+null\s+then\s+raise\s+exception\b(.*?)"
        r"\belsif\s+before_relrowsecurity\s+then\b(.*?)\belse\b(.*?)\bend\s+if\s*;",
        body,
    )
    assert m, "rollback/037's DO block lost its NULL -> RAISE / TRUE / ELSE shape"
    null_arm, true_arm, false_arm = m.group(1), m.group(2), m.group(3)
    assert "disable row level security" not in null_arm + true_arm, (
        "only the recorded-false branch may DISABLE RLS"
    )
    assert re.search(
        r"alter\s+table\s+public\.user_events\s+disable\s+row\s+level\s+security", false_arm
    ), "the recorded-false branch must DISABLE RLS (037's ENABLE is what changed it)"
    assert body.count("disable row level security") == 1


def test_pin_rollback_037_still_refuses_to_reverse_any_grant_or_revoke():
    """The comment block's four GRANT ... TO PUBLIC lines must stay comments."""
    top = norm(code_only(read(ROLLBACK_037)))
    assert not re.search(r"\bgrant\b", top), "rollback/037 must not re-grant EXECUTE"
    assert not re.search(r"\brevoke\b", top)


def test_pin_live_user_events_pin_counts_and_never_pulls_rows():
    """Privacy: the live pin must never print other people's event data."""
    src = function_source(TEST_037, "test_anon_cannot_read_user_events")
    assert src is not None
    flat = norm(src)
    assert 'count="exact"' in flat and ".limit(1)" in flat
    assert "result.count == 0" in flat
