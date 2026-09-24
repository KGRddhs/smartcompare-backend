"""Shared, network-free helpers for the R-MIG retro-fix tests.

Used by tests/test_retro_w1_2b.py, tests/test_retro_w1_2c.py and
tests/test_retro_w1_2d.py (W1-2 migration 037 retro-fix group). The leading
underscore keeps pytest from collecting this module.

Everything here is a pure text scan of files in the repo. Nothing connects to a
database; the three test files additionally install an autouse socket guard.
"""

from __future__ import annotations

import ast
import ipaddress
import re
import socket
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "migrations"
ROLLBACK_DIR = MIGRATIONS_DIR / "rollback"

MIGRATION_037 = MIGRATIONS_DIR / "037_security_definer_grants_and_rls.sql"
ROLLBACK_037 = ROLLBACK_DIR / "037_security_definer_grants_and_rls.sql"
TEST_037 = REPO_ROOT / "tests" / "test_migration_037_security_definer_grants.py"
NEXT_UNITS_DOC = (
    REPO_ROOT / "docs" / "investigations" / "2026-09-08-session-65-next-units.md"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def norm(text: str) -> str:
    """Lower-case and collapse all whitespace (CRLF-safe)."""
    return " ".join(text.lower().split())


# ---------------------------------------------------------------------------
# SQL text helpers (same semantics as test_migration_037's, kept local so the
# green phase can rewrite that file without breaking these pins)
# ---------------------------------------------------------------------------

DOLLAR_OPEN = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


def strip_line_comments(sql: str) -> str:
    return "\n".join(re.sub(r"--.*$", "", line) for line in sql.splitlines())


def comment_lines(sql: str) -> str:
    """Only the `-- ...` comment text, one line each (the prose a human reads)."""
    out = []
    for line in sql.splitlines():
        m = re.search(r"--(.*)$", line)
        if m:
            out.append(m.group(1))
    return "\n".join(out)


def dollar_bodies(sql: str) -> list[tuple[int, int]]:
    """(start, end) offsets of every `$tag$ ... $tag$` body interior."""
    spans: list[tuple[int, int]] = []
    i, n = 0, len(sql)
    while i < n:
        m = DOLLAR_OPEN.match(sql, i)
        if not m:
            i += 1
            continue
        close = sql.find(m.group(0), m.end())
        if close == -1:
            break
        spans.append((m.end(), close))
        i = close + len(m.group(0))
    return spans


def blank_dollar_bodies(sql: str) -> str:
    out = list(sql)
    for start, end in dollar_bodies(sql):
        for j in range(start, end):
            if out[j] != "\n":
                out[j] = " "
    return "".join(out)


def code_only(sql: str) -> str:
    """Comments stripped AND dollar bodies blanked: top-level DDL only."""
    return blank_dollar_bodies(strip_line_comments(sql))


def header_of(sql: str) -> str:
    """Everything before the first top-level `BEGIN;` line (the operator header)."""
    m = re.search(r"^\s*BEGIN\s*;\s*$", sql, re.IGNORECASE | re.MULTILINE)
    return sql[: m.start()] if m else sql


def qualified(name: str) -> str:
    parts = [p.strip().strip('"') for p in name.strip().split(".") if p.strip()]
    if not parts:
        return ""
    schema = parts[-2].lower() if len(parts) > 1 else "public"
    return f"{schema}.{parts[-1].lower()}"


def arg_types(arg_list: str) -> tuple[str, ...]:
    out = []
    for raw in arg_list.split(","):
        toks = raw.strip().split()
        if toks:
            out.append(toks[-1].strip().lower())
    return tuple(out)


Signature = tuple[str, tuple[str, ...]]

CREATE_FN = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+([A-Za-z0-9_.\"]+)\s*\(([^)]*)\)",
    re.IGNORECASE,
)
DROP_FN = re.compile(
    r"DROP\s+FUNCTION\s+(?:IF\s+EXISTS\s+)?([A-Za-z0-9_.\"]+)\s*\(([^)]*)\)",
    re.IGNORECASE,
)
REVOKE_FN = re.compile(
    r"REVOKE\s+(?:ALL(?:\s+PRIVILEGES)?|EXECUTE)\s+ON\s+FUNCTION\s+"
    r"([A-Za-z0-9_.\"]+)\s*\(([^)]*)\)(.*?);",
    re.IGNORECASE | re.DOTALL,
)
GRANT_FN = re.compile(
    r"GRANT\s+(?:ALL(?:\s+PRIVILEGES)?|EXECUTE)\s+ON\s+FUNCTION\s+"
    r"([A-Za-z0-9_.\"]+)\s*\(([^)]*)\)\s*TO\s+([^;]+);",
    re.IGNORECASE | re.DOTALL,
)


def revoke_roles(tail: str) -> tuple[str, ...]:
    m = re.search(r"\bfrom\s+(.+)$", " ".join(tail.split()), re.IGNORECASE)
    if not m:
        return ()
    body = re.sub(r"\b(cascade|restrict)\b", " ", m.group(1), flags=re.IGNORECASE)
    return tuple(
        re.sub(r"^group\s+", "", r.strip().strip('"').lower())
        for r in body.split(",")
        if r.strip()
    )


def grant_roles(text: str) -> tuple[str, ...]:
    return tuple(r.strip().lower() for r in text.split(",") if r.strip())


def security_definer_creates(sql: str) -> list[tuple[Signature, int]]:
    """(signature, offset) for each CREATE ... FUNCTION ... SECURITY DEFINER."""
    clean = code_only(sql)
    out = []
    for m in CREATE_FN.finditer(clean):
        end = clean.find(";", m.end())
        stmt = clean[m.start(): end if end != -1 else len(clean)]
        if "security definer" in norm(stmt):
            out.append(((qualified(m.group(1)), arg_types(m.group(2))), m.start()))
    return out


def create_or_drop_events(sql: str) -> list[tuple[Signature, int]]:
    """(signature, offset) for every CREATE FUNCTION or DROP FUNCTION."""
    clean = code_only(sql)
    out = []
    for rx in (CREATE_FN, DROP_FN):
        for m in rx.finditer(clean):
            out.append(((qualified(m.group(1)), arg_types(m.group(2))), m.start()))
    return out


def top_level_revokes(sql: str) -> list[tuple[Signature, tuple[str, ...], int]]:
    clean = code_only(sql)
    return [
        (
            (qualified(m.group(1)), arg_types(m.group(2))),
            revoke_roles(m.group(3)),
            m.start(),
        )
        for m in REVOKE_FN.finditer(clean)
    ]


def forward_sql_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


# ---------------------------------------------------------------------------
# Python-source helper: pull ONE function's source out of a test file
# ---------------------------------------------------------------------------

def function_source(path: Path, func_name: str) -> str | None:
    src = read(path)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return ast.get_source_segment(src, node)
    return None


# ---------------------------------------------------------------------------
# Zero-network guard (installed per file by an autouse fixture)
# ---------------------------------------------------------------------------

def _is_loopback_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    host = str(host)
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False


def install_network_guard(monkeypatch) -> list[str]:
    """Block every non-loopback connect / getaddrinfo; return the attempt log.

    The caller asserts the log is empty at teardown, so a test that even TRIES
    to reach the network fails, whether or not the attempt raised inside code
    that swallowed the error.
    """
    attempts: list[str] = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo
    af_unix = getattr(socket, "AF_UNIX", None)

    def _allowed(sock, address) -> bool:
        if af_unix is not None and getattr(sock, "family", None) == af_unix:
            return True
        host = address[0] if isinstance(address, tuple) and address else address
        return _is_loopback_host(host)

    def guarded_connect(self, address, *args, **kwargs):
        if _allowed(self, address):
            return real_connect(self, address, *args, **kwargs)
        attempts.append(f"connect {address!r}")
        raise OSError(f"network blocked by R-MIG zero-network guard: {address!r}")

    def guarded_connect_ex(self, address, *args, **kwargs):
        if _allowed(self, address):
            return real_connect_ex(self, address, *args, **kwargs)
        attempts.append(f"connect_ex {address!r}")
        raise OSError(f"network blocked by R-MIG zero-network guard: {address!r}")

    def guarded_getaddrinfo(host, *args, **kwargs):
        if _is_loopback_host(host):
            return real_getaddrinfo(host, *args, **kwargs)
        attempts.append(f"getaddrinfo {host!r}")
        raise socket.gaierror(f"DNS blocked by R-MIG zero-network guard: {host!r}")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    return attempts
