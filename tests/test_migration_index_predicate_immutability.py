"""Guard: no volatile/stable functions in any CREATE INDEX ... WHERE predicate.

Bundle B B.1 (F3.2, item 2 — dispatcher-requested after the 028 apply
failure). Postgres requires partial-index predicates to be IMMUTABLE
(https://www.postgresql.org/docs/current/sql-createindex.html). Functions
like `now()`, `CURRENT_TIMESTAMP`, and `CURRENT_DATE` are STABLE, not
IMMUTABLE, so a partial index gated on them is rejected at apply time with
ERROR 42P17 ("functions in index predicate must be marked IMMUTABLE") and the
whole migration transaction rolls back.

The 028 migration originally shipped `idx_pwe_recent` with
`WHERE created_at > now() - interval '90 days'` — syntactically valid, so the
107 structural drift tests passed, but it failed at apply. This static scan
catches that class: it parses every CREATE INDEX statement across
migrations/*.sql, isolates the WHERE predicate, and asserts no volatile/stable
function appears in it.

A pinned fixture (the exact OLD 028 text) proves the detector goes RED on the
pattern it is meant to catch.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "migrations"

# Non-immutable time functions that are illegal inside an index predicate.
# Matched case-insensitively. now() and the SQL-standard spellings.
VOLATILE_IN_PREDICATE = (
    "now()",
    "current_timestamp",
    "current_date",
    "current_time",
    "transaction_timestamp()",
    "statement_timestamp()",
    "clock_timestamp()",
    "timeofday()",
)


def _strip_sql_line_comments(sql: str) -> str:
    """Drop `-- ...` line comments so a function name mentioned in an
    explanatory comment is never mistaken for one in actual DDL."""
    return re.sub(r"--[^\n]*", "", sql)


def _index_predicates(sql: str) -> list[tuple[str, str]]:
    """Return (full_create_stmt, where_predicate) for every CREATE INDEX in
    `sql` that has a WHERE clause. SQL comments are stripped first.

    The predicate is everything between WHERE and the statement-terminating
    semicolon. Parenthesised column lists before WHERE are consumed by the
    non-greedy `.*?` so the WHERE we find is the predicate's, not a column
    expression's.
    """
    clean = _strip_sql_line_comments(sql)
    out: list[tuple[str, str]] = []
    for m in re.finditer(
        r"(CREATE\s+INDEX\b.*?;)",
        clean,
        re.IGNORECASE | re.DOTALL,
    ):
        stmt = m.group(1)
        wm = re.search(r"\bWHERE\b(.*);", stmt, re.IGNORECASE | re.DOTALL)
        if wm:
            out.append((stmt, wm.group(1)))
    return out


def _volatile_hits(predicate: str) -> list[str]:
    low = predicate.lower()
    return [fn for fn in VOLATILE_IN_PREDICATE if fn in low]


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


# ---------------------------------------------------------------------------
# The guard itself — runs over every committed migration.
# ---------------------------------------------------------------------------

def test_no_migration_files_present_is_a_bug():
    """Sanity: the scan would vacuously pass if it found no files."""
    assert _migration_files(), f"no migrations/*.sql found under {MIGRATIONS_DIR}"


@pytest.mark.parametrize("sql_path", _migration_files(), ids=lambda p: p.name)
def test_index_predicates_are_immutable(sql_path: Path):
    """No CREATE INDEX ... WHERE predicate may reference a volatile/stable
    time function — Postgres rejects it at apply (42P17)."""
    sql = sql_path.read_text(encoding="utf-8")
    offenders = []
    for stmt, predicate in _index_predicates(sql):
        hits = _volatile_hits(predicate)
        if hits:
            # Surface the index name + offending function for a clear failure.
            name_m = re.search(r"CREATE\s+INDEX(?:\s+IF\s+NOT\s+EXISTS)?\s+(\w+)", stmt, re.IGNORECASE)
            idx_name = name_m.group(1) if name_m else "<unknown>"
            offenders.append(f"{idx_name}: {sorted(hits)}")
    assert not offenders, (
        f"{sql_path.name} has volatile function(s) in a CREATE INDEX WHERE "
        f"predicate (illegal — 42P17 at apply): {offenders}"
    )


# ---------------------------------------------------------------------------
# Detector self-test — the OLD 028 text MUST trip the scan (RED fixture).
# ---------------------------------------------------------------------------

# Exact pre-correction 028 index DDL (the line that failed apply).
_OLD_028_BAD_INDEX = """
CREATE INDEX IF NOT EXISTS idx_pwe_recent
  ON public.pain_workflow_events (workflow_name, created_at DESC)
  WHERE created_at > now() - interval '90 days';
"""


def test_detector_flags_old_028_recent_index():
    """Pin the exact pattern the dispatcher caught: the scanner must report a
    now() hit for the old idx_pwe_recent predicate. If this ever goes GREEN
    the detector has regressed."""
    preds = _index_predicates(_OLD_028_BAD_INDEX)
    assert len(preds) == 1, "fixture should contain exactly one partial index"
    _, predicate = preds[0]
    assert _volatile_hits(predicate) == ["now()"]


def test_detector_ignores_now_outside_index_predicate():
    """now() in a column DEFAULT or a regular WHERE (not an index predicate)
    must NOT be flagged — only index predicates are illegal."""
    benign = """
    CREATE TABLE public.t (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX idx_plain ON public.t (created_at);
    -- A backfill query (comment) using now() is also fine:
    -- DELETE FROM public.t WHERE created_at < now() - interval '1 day';
    """
    preds = _index_predicates(benign)
    # idx_plain has no WHERE, so nothing to scan; DEFAULT now() isn't an index.
    assert preds == []


def test_036_has_matching_rollback():
    """Issue #116 — migration 036 (home_savings_aggregate) must ship as a
    forward/rollback PAIR, following the 025-035 convention. The IMMUTABLE
    index-predicate scan above covers its DDL automatically via the glob."""
    fwd = MIGRATIONS_DIR / "036_home_savings_aggregate.sql"
    rb = MIGRATIONS_DIR / "rollback" / "036_home_savings_aggregate.sql"
    assert fwd.exists(), f"missing forward migration: {fwd}"
    assert rb.exists(), f"missing rollback migration: {rb}"
    # Both must be readable UTF-8 and reference the same function.
    assert "home_savings_aggregate" in fwd.read_text(encoding="utf-8")
    assert "home_savings_aggregate" in rb.read_text(encoding="utf-8")


def test_detector_ignores_immutable_index_predicate():
    """A partial index with an IMMUTABLE predicate (e.g. IS NOT NULL) is the
    legal, common case and must pass clean."""
    ok = """
    CREATE INDEX IF NOT EXISTS idx_ok
      ON public.t (col)
      WHERE col IS NOT NULL;
    """
    preds = _index_predicates(ok)
    assert len(preds) == 1
    assert _volatile_hits(preds[0][1]) == []
