"""Migration 044 -- public.apple_siwa_tokens (B3-B, S79; spec section 5.2 with the
binding ruling B6: an explicit GRANT SELECT, INSERT, UPDATE to service_role).

The table keeps the Apple refresh token only so account deletion can revoke it;
it is service-role only (RLS on, no policy, REVOKE ALL from PUBLIC / anon /
authenticated, exactly one GRANT, to service_role) and its rows leave with the
auth user (FK to auth.users ON DELETE CASCADE). MERGING CHANGES NOTHING in
production: the owner applies 044 before flipping ENABLE_APPLE_TOKEN_REVOCATION.

Pure text scans in the 041 / 042 style (no database). RED before the two files
exist; each docstring names the mutant it kills.
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

MIGRATION_044 = MIGRATIONS_DIR / "044_apple_siwa_tokens.sql"
ROLLBACK_044 = ROLLBACK_DIR / "044_apple_siwa_tokens.sql"
TABLE = "public.apple_siwa_tokens"


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = install_network_guard(monkeypatch)
    yield
    assert not attempts, f"044 pins must never touch the network: {attempts}"


def _require(path) -> str:
    assert path.is_file(), f"{path.relative_to(MIGRATIONS_DIR.parent)} does not exist"
    return read(path)


def _statements(sql: str) -> list[str]:
    """Comment-stripped, literal-blanked, whitespace-normalised, lower-case statements."""
    text = code_only(sql)
    text = re.sub(r"'(?:[^']|'')*'", "''", text)
    return [norm(s) for s in text.split(";") if s.strip()]


def _paren_norm(text: str) -> str:
    return re.sub(r"\s*([()])\s*", r"\1", norm(text))


def _split_top(text: str) -> list[str]:
    out, depth, cur = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur))
    return [c.strip() for c in out]


def test_044_and_rollback_exist_exactly_once_and_039_stays_reserved():
    """M1 (RED: absent): one 044 forward file and one rollback, both named
    044_apple_siwa_tokens.sql; 039 stays reserved (no 039_* file)."""
    assert sorted(p.name for p in MIGRATIONS_DIR.glob("044_*.sql")) == ["044_apple_siwa_tokens.sql"]
    assert sorted(p.name for p in ROLLBACK_DIR.glob("044_*.sql")) == ["044_apple_siwa_tokens.sql"]
    assert not list(MIGRATIONS_DIR.glob("039_*")), "039 is reserved"


def test_044_is_one_transaction():
    """M2 (RED: absent): first statement BEGIN, last COMMIT, exactly one of each."""
    stmts = _statements(_require(MIGRATION_044))
    assert stmts and stmts[0] == "begin" and stmts[-1] == "commit", stmts[:1] + stmts[-1:]
    assert stmts.count("begin") == 1 and stmts.count("commit") == 1, stmts


def test_044_creates_exactly_the_token_table():
    """M3 (RED: absent; kills X36): one CREATE TABLE IF NOT EXISTS
    public.apple_siwa_tokens with exactly the four columns (FK to auth.users
    ON DELETE CASCADE)."""
    stmts = _statements(_require(MIGRATION_044))
    creates = [s for s in stmts if s.startswith("create table")]
    assert len(creates) == 1, creates
    m = re.fullmatch(r"create table if not exists public\.apple_siwa_tokens \((.*)\)", creates[0])
    assert m, creates[0]
    cols = [_paren_norm(c) for c in _split_top(m.group(1))]
    expected = [
        _paren_norm(c) for c in (
            "user_id uuid primary key references auth.users (id) on delete cascade",
            "refresh_token text not null",
            "created_at timestamptz not null default now()",
            "updated_at timestamptz not null default now()",
        )
    ]
    assert cols == expected, cols


def test_044_is_service_role_only():
    """M4 (RED: absent; kills X37, X38; ruling B6): RLS enabled, no policy,
    REVOKE ALL ... FROM PUBLIC, anon, authenticated, exactly one GRANT:
    SELECT, INSERT, UPDATE to service_role."""
    stmts = _statements(_require(MIGRATION_044))
    assert f"alter table {TABLE} enable row level security" in stmts, stmts
    assert not [s for s in stmts if "create policy" in s], "044 must create no policy"
    assert f"revoke all on table {TABLE} from public, anon, authenticated" in stmts, stmts
    grants = [s for s in stmts if s.startswith("grant ")]
    assert len(grants) == 1, grants
    g = re.fullmatch(r"grant (.+?) on (?:table )?(\S+) to (.+)", grants[0])
    assert g, grants[0]
    privileges = {p.strip() for p in g.group(1).split(",")}
    assert privileges == {"select", "insert", "update"}, privileges
    assert g.group(2) == TABLE, g.group(2)
    assert [r.strip() for r in g.group(3).split(",")] == ["service_role"], g.group(3)


def test_044_touches_nothing_else():
    """M5 (RED: absent): no function, DROP, index, policy, DML, other table;
    every statement is one of the allowed kinds and every relation named is
    public.apple_siwa_tokens."""
    stmts = _statements(_require(MIGRATION_044))
    allowed = (
        re.compile(r"begin|commit"),
        re.compile(r"create table if not exists public\.apple_siwa_tokens \(.*\)"),
        re.compile(r"alter table public\.apple_siwa_tokens enable row level security"),
        re.compile(r"revoke all on table public\.apple_siwa_tokens from .+"),
        re.compile(r"grant [a-z, ]+ on (?:table )?public\.apple_siwa_tokens to .+"),
        re.compile(r"comment on table public\.apple_siwa_tokens is ''"),
        re.compile(r"comment on column public\.apple_siwa_tokens\.[a-z_]+ is ''"),
    )
    stray = [s for s in stmts if not any(rx.fullmatch(s) for rx in allowed)]
    assert not stray, stray
    for s in stmts:
        for bad in ("function", "drop ", "create index", "create policy", "update ", "delete ",
                    "insert "):
            if bad in ("update ", "delete ", "insert "):
                assert not s.startswith(bad.strip()), s
            else:
                assert bad not in s, s
    targets = re.findall(r"\btable (?:if not exists )?([\w.\"]+)", " ".join(stmts))
    assert targets and set(targets) == {TABLE}, targets


def test_044_header_states_apply_order_and_rollback():
    """M6 (RED: absent): the comment lines name the flag, 'before', the rollback
    path, 'service role' and auth.users."""
    comments = comment_lines(_require(MIGRATION_044))
    low = comments.lower()
    for needle in ("ENABLE_APPLE_TOKEN_REVOCATION", "rollback/044_apple_siwa_tokens.sql", "auth.users"):
        assert needle in comments, needle
    for needle in ("before", "service role"):
        assert needle in low, needle


def test_044_rollback_drops_only_the_table_and_says_flag_off_first():
    """M7 (RED: absent): the rollback is BEGIN; DROP TABLE IF EXISTS
    public.apple_siwa_tokens; COMMIT and nothing else; its header names the
    flag and 'off'."""
    sql = _require(ROLLBACK_044)
    assert _statements(sql) == ["begin", f"drop table if exists {TABLE}", "commit"], _statements(sql)
    comments = comment_lines(sql)
    assert "ENABLE_APPLE_TOKEN_REVOCATION" in comments
    assert "off" in comments.lower()


def test_044_passes_the_u8b_fence_with_the_keep_entry():
    """M8 (RED: the fence has no apple_siwa_tokens table; kills X39): the 043
    fence sees the new table as {user_id: id}, the KEEP entry exists and is
    justified, and the fence reports no gap."""
    from tests import test_migration_043_delete_user_cascade as t043

    files = t043.real_forward_files()
    tables = t043.fence_user_tables(files)
    assert "apple_siwa_tokens" in tables, "the fence finds no apple_siwa_tokens table"
    assert tables["apple_siwa_tokens"] == {"user_id": "id"}, tables["apple_siwa_tokens"]
    keep = t043.KEEP_TABLE_COLUMNS.get(("apple_siwa_tokens", "user_id"))
    assert isinstance(keep, str) and len(keep) >= 40, keep
    assert "apple_siwa_tokens" in t043.KNOWN_USER_TABLES
    rep = t043.fence_report(files)
    assert not rep["table_gaps"], rep["table_gaps"]
