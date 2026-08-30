"""Static guards for the sqlfluff migration gate (M10 unit 4).

`.githooks/pre-commit` stanza 5 has invoked `sqlfluff lint` on staged
migrations since it was written, but sqlfluff was in neither the dev lock nor
any developer's PATH, so every run took the "not installed" branch. The stanza
read like a gate and had never linted a file.

This module pins the *shape* of the fix so it cannot rot back into a no-op:
the config exists and names the dialect, every muted rule carries its measured
reason, the tool stays declared in the dev lock, and the hook keeps the one
environment variable that stops it failing on clean SQL.

Every assertion here is a file-on-disk assertion — no network, no credentials,
no cost — except the last, which runs the real linter and is skipped when
sqlfluff is not installed. Mirrors `tests/test_ci_gates.py`'s approach for the
black allowlist.
"""

from __future__ import annotations

import configparser
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SQLFLUFF_CFG = REPO_ROOT / ".sqlfluff"
SQLFLUFF_IGNORE = REPO_ROOT / ".sqlfluffignore"
PRE_COMMIT = REPO_ROOT / ".githooks" / "pre-commit"
DEV_IN = REPO_ROOT / "requirements-dev.in"
DEV_LOCK = REPO_ROOT / "requirements-dev.txt"
MIGRATIONS = REPO_ROOT / "migrations"


def _cfg() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    # sqlfluff config is INI with `#` comments, which configparser handles.
    parser.read(SQLFLUFF_CFG, encoding="utf-8")
    return parser


def _excluded_rules() -> list[str]:
    raw = _cfg().get("sqlfluff", "exclude_rules", fallback="")
    return [code.strip() for code in raw.split(",") if code.strip()]


def test_sqlfluff_config_exists_and_pins_the_postgres_dialect():
    """Without a committed config, the first person to install sqlfluff meets
    stock defaults against 43 files of applied production DDL."""
    assert SQLFLUFF_CFG.exists(), "missing repo-root .sqlfluff"
    assert _cfg().get("sqlfluff", "dialect", fallback=None) == "postgres"


def test_every_excluded_rule_carries_a_reason():
    """A rule muted with no written reason is an unreviewable silent mute.

    The config documents each exclusion with its MEASURED violation count; this
    asserts the documentation cannot drift away from the exclusion list.
    """
    text = SQLFLUFF_CFG.read_text(encoding="utf-8")
    comments = [ln for ln in text.splitlines() if ln.lstrip().startswith("#")]
    undocumented = []
    for code in _excluded_rules():
        # the reason line is `#   LT02: 321  Indentation. ...`
        if not any(re.search(rf"\b{re.escape(code)}\b\s*:\s*\d+", ln) for ln in comments):
            undocumented.append(code)
    assert not undocumented, (
        "these excluded rules carry no `CODE: <measured count>` reason comment "
        f"in .sqlfluff: {undocumented}"
    )


def test_excluded_rules_are_not_empty_and_look_like_rule_codes():
    codes = _excluded_rules()
    assert codes, "exclude_rules is empty — if the corpus is clean, delete the key"
    bad = [c for c in codes if not re.fullmatch(r"[A-Z]{2}\d{2}", c)]
    assert not bad, f"not sqlfluff rule codes: {bad}"


def test_line_length_rule_is_enforced_not_muted():
    """LT05 is the one layout rule the corpus can actually satisfy.

    The longest lintable line is 178 chars, so the limit sits just above it and
    the rule stays ON to catch a runaway new line. Muting it instead would give
    up the only enforced layout guard on the corpus.
    """
    assert "LT05" not in _excluded_rules(), "LT05 must stay enforced, not excluded"
    limit = _cfg().getint("sqlfluff", "max_line_length", fallback=0)
    assert limit >= 178, f"max_line_length={limit} would fail the existing corpus"
    assert limit <= 200, (
        f"max_line_length={limit} is so wide the rule stops meaning anything; "
        "ratchet DOWN toward 120 as long lines are wrapped, never up"
    )


def test_keyword_capitalisation_is_enforced():
    """Measured 0 violations at `upper` — it is free, so it must stay on."""
    assert "CP01" not in _excluded_rules()
    policy = _cfg().get(
        "sqlfluff:rules:capitalisation.keywords",
        "capitalisation_policy",
        fallback=None,
    )
    assert policy == "upper"


def test_no_sqlfluffignore_hides_migrations_without_reason():
    """Measured: 0 of 43 files fail to PARSE, so nothing needs ignoring.

    If a future parse failure forces one, every entry must still be a real
    file — a stale ignore silently un-lints a migration forever.
    """
    if not SQLFLUFF_IGNORE.exists():
        return
    missing = []
    for line in SQLFLUFF_IGNORE.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        if not (REPO_ROOT / entry).is_file():
            missing.append(entry)
    assert not missing, f".sqlfluffignore names files that do not exist: {missing}"


def test_hook_lints_staged_migrations_including_rollbacks():
    """The hook's pathspec must reach every migration, rollbacks included.

    git's pathspec wildmatch lets `*` cross `/`, so `migrations/*.sql` already
    covers `migrations/rollback/*.sql` — this asserts that behaviour rather than
    assuming it, since the natural reading of the glob says otherwise.
    """
    text = PRE_COMMIT.read_text(encoding="utf-8")
    assert "SQL_FILES=" in text and "migrations/" in text

    listed = subprocess.run(
        ["git", "ls-files", "--", "migrations/*.sql"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if listed.returncode != 0:
        pytest.skip("git not available")
    matched = {ln.strip() for ln in listed.stdout.splitlines() if ln.strip()}
    assert matched, "the hook's pathspec matches no migrations at all"
    assert any("rollback/" in p for p in matched), (
        "the hook's pathspec no longer reaches migrations/rollback/*.sql — "
        "every rollback script, i.e. exactly what runs under pressure, would "
        "be outside the gate"
    )


def test_hook_forces_utf8_io_for_sqlfluff():
    """Guard for a measured false failure, not a style preference.

    sqlfluff's success message contains an emoji. On Windows with a non-console
    stdout (GUI git client, IDE commit box, any pipe) the stream defaults to
    cp1252, the write raises UnicodeEncodeError, and sqlfluff exits 1 with ZERO
    violations — refusing a commit whose SQL is clean. Without this env var the
    gate fails closed on correct input, which is how a gate gets deleted.
    """
    text = PRE_COMMIT.read_text(encoding="utf-8")
    invocation = [
        ln
        for ln in text.splitlines()
        if "sqlfluff lint" in ln and not ln.lstrip().startswith("#")
    ]
    assert invocation, "no `sqlfluff lint` invocation found in the hook"
    for line in invocation:
        assert "PYTHONIOENCODING=utf-8" in line, (
            "sqlfluff must be invoked with PYTHONIOENCODING=utf-8; without it a "
            "clean corpus exits 1 on Windows when stdout is not a console"
        )


def test_hook_keeps_the_not_installed_escape_hatch():
    """A developer without the dev requirements must still be able to commit."""
    text = PRE_COMMIT.read_text(encoding="utf-8")
    assert "command -v sqlfluff" in text, (
        "the `command -v sqlfluff` guard is what keeps the hook inert for "
        "anyone who has not installed the dev requirements"
    )


def test_sqlfluff_is_declared_in_dev_requirements_and_pinned_in_the_lock():
    """Declared with a floor like every other entry; pinned exactly by the lock,
    which is what CI installs and diffs."""
    assert re.search(
        r"^sqlfluff\s*[><=]=", DEV_IN.read_text(encoding="utf-8"), re.MULTILINE
    ), "requirements-dev.in does not declare sqlfluff"
    assert re.search(
        r"^sqlfluff==\d+\.\d+", DEV_LOCK.read_text(encoding="utf-8"), re.MULTILINE
    ), "requirements-dev.txt does not pin sqlfluff to an exact version"


def test_sqlfluff_lints_the_migration_corpus_clean():
    """The acceptance run. Skipped without the dev requirements installed.

    This is the assertion that would catch the config drifting away from the
    corpus — e.g. a new migration that the exclude-set does not cover.
    """
    pytest.importorskip("sqlfluff")
    result = subprocess.run(
        ["python", "-m", "sqlfluff", "lint", "migrations/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, (
        "sqlfluff reports violations on the committed migrations:\n"
        f"{result.stdout}\n{result.stderr}"
    )
