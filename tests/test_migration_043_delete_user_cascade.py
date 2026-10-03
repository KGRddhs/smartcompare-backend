"""U8b (S71, MYEZ Apple launch lane): static pins for migration 043, its
rollback, the one-paste files the owner applies, and the deletion fence.

SPEC: docs/investigations/2026-10-03-session-71-state/U8B_ACCOUNT_DELETION_SPEC.md
sections 5.1 and 5.3 (static half), as corrected by the binding review
corrections C1-C14 and the orchestrator rulings UR1-UR15.

Account deletion (App Store guideline 5.1.1(v)) must erase every personal
column of the kept users row and every user-owned row. At base (eb86075e) the
cascade is still the 025 body: the two fence coverage tests list its 25 gaps
(20 users columns, admin_audit_log.ip_address and four tables), and every 043
pin fails inside its body because the file does not exist yet.

Hermetic: pure text scans of files in the repo (pathlib, utf-8); nothing
connects to a database; an autouse guard fails any test that even tries the
network. Mutants are built in memory from the real migration text and are
never written to the worktree. Nothing this unit creates is imported at module
top: auth_service.DELETED_USER_CACHE_KEY_TEMPLATES is read inside a test body.
"""

from __future__ import annotations

import ast
import functools
import hashlib
import re
from pathlib import Path

import pytest

from tests._retro_r_mig_sql import (
    GRANT_FN,
    MIGRATIONS_DIR,
    REPO_ROOT,
    ROLLBACK_DIR,
    code_only,
    comment_lines,
    create_or_drop_events,
    dollar_bodies,
    forward_sql_files,
    install_network_guard,
    norm,
    read,
    strip_line_comments,
    top_level_revokes,
)

MIG_043_NAME = "043_delete_user_cascade_full_erasure.sql"
MIG_043 = MIGRATIONS_DIR / MIG_043_NAME
ROLLBACK_043 = ROLLBACK_DIR / MIG_043_NAME
MIG_025 = MIGRATIONS_DIR / "025_delete_user_cascade_completeness.sql"
STATE_DIR = REPO_ROOT / "docs" / "investigations" / "2026-10-03-session-71-state"
PRECHECK = STATE_DIR / "APPLY_043_1_PRECHECK.sql"
ONE_PASTE = STATE_DIR / "APPLY_043_2_ONE_PASTE.sql"
POSTCHECK = STATE_DIR / "APPLY_043_3_POSTCHECK.sql"
BACKFILL = STATE_DIR / "APPLY_043_4_BACKFILL_ORPHANS.sql"
APP_DIR = REPO_ROOT / "app"

NIL_UUID = "00000000-0000-0000-0000-000000000000"
CASCADE_SIG = ("public.delete_user_cascade", ("uuid",))

# ---------------------------------------------------------------------------
# Allowlists (R5 format; every value is a justification of >= 40 characters)
# ---------------------------------------------------------------------------

# The out-of-band public.users DDL (no migration creates the table).
USERS_BASELINE_COLUMNS: dict[str, str] = {
    "id": "docs/CONTEXT_DATABASE_API.md:84 (uuid primary key); live per UR2 metadata",
    "email": "docs/CONTEXT_DATABASE_API.md:85 (email TEXT, nullable); live per UR2",
    "display_name": "docs/CONTEXT_DATABASE_API.md:86 (display_name TEXT); live per UR2",
    "auth_provider": "docs/CONTEXT_DATABASE_API.md:87 (auth_provider TEXT); live per UR2",
    "subscription_tier": "docs/CONTEXT_DATABASE_API.md:88; also 011:28 ADD COLUMN IF NOT EXISTS",
    "subscription_expires_at": "docs/CONTEXT_DATABASE_API.md:89 (TIMESTAMPTZ); live per UR2",
    "created_at": "docs/CONTEXT_DATABASE_API.md:90; live per UR2 metadata (C11 resolved)",
    "updated_at": "docs/CONTEXT_DATABASE_API.md:91; read by the 013 vw_cohort_match_rate view",
    "preferences": "2026-06-08 phase-1 schema audit (preferences jsonb); live per UR2",
    "preferences_completed": "2026-06-08 phase-1 schema audit (boolean default false); live per UR2",
    "behavior_profile": "2026-06-08 phase-1 schema audit (behavior_profile jsonb); live per UR2",
}

# Out-of-band tables that hold a user reference (no CREATE TABLE in migrations).
OUT_OF_BAND_USER_TABLES: dict[str, tuple[str, ...]] = {
    "comparisons": ("user_id",),
    "comparison_feedback": ("user_id",),
    "user_events": ("user_id",),
}

# R4.1 (justification for created_at rewritten per C11).
KEEP_USERS_COLUMNS: dict[str, str] = {
    "id": (
        "Primary key of the de-identified stub: a random v4 uuid that identifies no "
        "person once every other column is erased; target of the FKs in "
        "011/014/028/029, and the key the auth-failure retry needs."
    ),
    "created_at": "account creation date on the stub; no person-identifying value",
}

# R4.2 (ruling UR3: the audit rows are kept, their ip_address is set to NULL).
KEEP_TABLE_COLUMNS: dict[tuple[str, str], str] = {
    ("admin_audit_log", "user_id"): (
        "Security events (login_success, invite_code_redeemed, referral abuse flags) "
        "are kept for fraud and abuse forensics; the key is the stub's random uuid, "
        "and 043 sets ip_address to NULL on these rows."
    ),
}

# C5(d): false positives of the widened personal-name regex (measured empty).
NOT_PERSONAL: dict[tuple[str, str], str] = {}

# R3 tombstone map, normalised lower-case value text (UR2: 25 columns).
EXPECTED_TOMBSTONE: dict[str, str] = {
    "email": "null",
    "display_name": "null",
    "auth_provider": "null",
    "subscription_tier": "'free'",
    "subscription_expires_at": "null",
    "updated_at": "now()",
    "preferences": "null",
    "preferences_completed": "false",
    "behavior_profile": "null",
    "lifetime_comparisons_used": "0",
    "demographics_profile": "null",
    "demographics_dismissed_count": "0",
    "demographics_dismissed_at": "null",
    "referral_code": "null",
    "referral_bonus_comparisons_this_month": "0",
    "referral_bonus_reset_at": "null",
    "expo_push_token": "null",
    "notifications_enabled": "false",
    "last_comparison_at": "null",
    "attribution_source": "null",
    "device_fingerprint_hash": "null",
    "lifetime_invites_consumed": "0",
    "terms_accepted_at": "null",
    "terms_version": "null",
    "age_attested_at": "null",
}

# UR2: the 27 live users columns.
KNOWN_USERS_COLUMNS = frozenset(
    {"id", "created_at"} | set(EXPECTED_TOMBSTONE)
)

# Section 2b: the 12 user-referencing tables.
KNOWN_USER_TABLES = frozenset(
    {
        "comparisons", "comparison_feedback", "user_events", "search_logs",
        "user_usage", "admin_audit_log", "referral_invites", "referral_redemptions",
        "deep_review_credits", "re_engagement_events", "pain_workflow_events",
        "user_preference_history",
    }
)

# R1.4 + C2: the ordered DELETE targets of the 043 body.
EXPECTED_DELETE_ORDER = [
    "user_events", "comparison_feedback", "comparisons", "search_logs",
    "user_usage", "referral_invites", "referral_redemptions",
    "deep_review_credits", "re_engagement_events", "pain_workflow_events",
    "user_preference_history",
]

# C8: per-user Redis key templates that are deliberately NOT purged on deletion.
KEPT_USER_CACHE_KEY_TEMPLATES: dict[str, str] = {
    "usage:daily:{user_id}:{*}": (
        "integer daily quota counter (usage_service.py:150-174), TTL 24 h; holds no "
        "content and keeps quota symmetry (spec R4.3)"
    ),
    "usage:monthly:{user_id}:{*}": (
        "integer monthly quota counter (usage_service.py:150-174), TTL about 32 d; "
        "holds no content (spec R4.3)"
    ),
    "usage:{user_id}:{*}": (
        "legacy integer daily usage counter (cache_service.py:812-824), TTL 24 h; "
        "holds no content (spec R4.3)"
    ),
}

EXPECTED_PURGED_TEMPLATES = frozenset(
    {
        "home:savings:{user_id}",
        "home:smart_pick:{user_id}",
        "profile_recent:{user_id}",
        "monthly_stats:{user_id}",
        "priorities_weighted:{user_id}",
    }
)


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = install_network_guard(monkeypatch)
    yield
    assert not attempts, f"U8b static tests must never touch the network: {attempts}"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _lf(text: str) -> str:
    return text.replace("\r\n", "\n")


def _require(path: Path) -> str:
    """Read a file this unit creates; FAIL (not error, not skip) if absent."""
    if not path.exists():
        pytest.fail(
            f"U8b: {path.relative_to(REPO_ROOT).as_posix()} does not exist yet "
            "(RED until GREEN writes it)"
        )
    return _lf(read(path))


def _compact(text: str) -> str:
    return "".join(text.lower().split())


def _blank_literals(sql: str) -> str:
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def _split_top(text: str) -> list[str]:
    out, cur, depth = [], "", 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _balanced(text: str, open_idx: int) -> str:
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i]
    return text[open_idx + 1:]


def md5_norm(body: str) -> str:
    """R8.1: drop whole-line -- comments, collapse whitespace, trim, md5."""
    kept = " ".join(ln for ln in body.splitlines() if not ln.strip().startswith("--"))
    return hashlib.md5(" ".join(kept.split()).encode()).hexdigest()


def _function_body_raw(sql: str) -> str:
    """Text between `AS $function$` and the closing `$function$` (raw)."""
    m = re.search(r"\bAS\s+\$function\$", sql, re.IGNORECASE)
    assert m, "no `AS $function$` in the file"
    end = sql.find("$function$", m.end())
    assert end != -1, "unterminated $function$ body"
    return sql[m.end():end]


def _tagged_body(sql: str, tag: str) -> tuple[str, int, int]:
    m = re.search(r"\$" + tag + r"\$(.*?)\$" + tag + r"\$", sql, re.DOTALL)
    assert m, f"no ${tag}$ ... ${tag}$ block in the file"
    return m.group(1), m.start(), m.end()


# ---------------------------------------------------------------------------
# Cascade body parser (shared by the 043 pins and the fence)
# ---------------------------------------------------------------------------

_PUBLIC = r'(?:"?public"?\s*\.\s*)?'
_Q_IDENT = r'(?:"([^"]+)"|([A-Za-z_][A-Za-z0-9_]*))'

_DEL_RX = re.compile(
    r"^DELETE\s+FROM\s+(?:ONLY\s+)?(" + _PUBLIC + r")" + _Q_IDENT + r"(?:\s+WHERE\s+(.*))?$",
    re.IGNORECASE | re.DOTALL,
)
_UPD_RX = re.compile(
    r"^UPDATE\s+(?:ONLY\s+)?(" + _PUBLIC + r")" + _Q_IDENT
    + r"\s+SET\s+(.*?)(?:\s+WHERE\s+(.*))?$",
    re.IGNORECASE | re.DOTALL,
)
_DETACH_WHERE_RX = re.compile(
    r"^comparison_id in \( ?select (\w+)\.id from (?:public\.)?comparisons (?:as )?(\w+) "
    r"where (\w+)\.user_id = target_user_id ?\)$"
)
_TERM_RX = re.compile(r'^"?([a-z_][a-z0-9_]*)"?\s*=\s*target_user_id$')


def _ident(m: re.Match, i: int) -> str:
    return (m.group(i) or m.group(i + 1) or "").lower()


def _set_map(set_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in _split_top(set_text):
        if "=" not in part:
            out[f"<unparsed:{part}>"] = ""
            continue
        col, val = part.split("=", 1)
        out[col.strip().strip('"').lower()] = " ".join(val.split()).lower()
    return out


def _body_chunks(body: str) -> list[str]:
    return body.split(";")


def _flat(chunk: str) -> str:
    flat = " ".join(chunk.split())
    return re.sub(r"^BEGIN\b\s*", "", flat, flags=re.IGNORECASE)


def parse_body(body: str) -> list[dict]:
    """One dict per statement of a plpgsql cascade body (comments stripped)."""
    out: list[dict] = []
    for idx, chunk in enumerate(_body_chunks(body)):
        flat = _flat(chunk)
        if not flat or flat.upper() == "END":
            continue
        d = _DEL_RX.match(flat)
        if d:
            out.append({
                "idx": idx, "kind": "delete", "table": _ident(d, 2),
                "qualified": bool(d.group(1)), "where": " ".join((d.group(4) or "").split()).lower() or None,
                "flat": flat,
            })
            continue
        u = _UPD_RX.match(flat)
        if u:
            where = " ".join((u.group(5) or "").split()).lower() or None
            setmap = _set_map(u.group(4))
            stmt = {
                "idx": idx, "kind": "update", "table": _ident(u, 2),
                "qualified": bool(u.group(1)), "set": setmap, "where": where, "flat": flat,
            }
            dm = _DETACH_WHERE_RX.match(where or "")
            if setmap == {"comparison_id": "null"} and dm and dm.group(1) == dm.group(2) == dm.group(3):
                stmt["kind"] = "detach"
            out.append(stmt)
            continue
        out.append({"idx": idx, "kind": "other", "table": None, "flat": flat})
    return out


# ---------------------------------------------------------------------------
# The static fence (F1-F6 as widened by C5)
# ---------------------------------------------------------------------------

USER_REF_ID_RX = re.compile(
    r"(^|_)(user|owner|account|profile|member|customer|actor|author|referrer|invitee|redeemer)"
    r"(_user)?_id$|^(created|updated|deleted)_by$"
)
PERSONAL_RX = re.compile(
    r"(^|_)(user|owner|account|profile|member|customer|actor|author|referrer|invitee|redeemer)"
    r"(_user)?_id$|^(created|updated|deleted)_by$|email|phone|full_name|first_name|last_name|"
    r"display_name|address|fingerprint|device_id|install_id|anon_id|push_token|(^|_)ip($|_)|"
    r"ip_address|remote_addr|user_agent|session_id|governorate|gender|birth"
)

_ALTER_HEAD = r"\bALTER\s+TABLE\s+(?:(?:IF\s+EXISTS|ONLY)\s+)*" + _PUBLIC
_USERS_ALTER_RX = re.compile(_ALTER_HEAD + r'(?:"users"|users\b)(.*?);', re.IGNORECASE | re.DOTALL)
_OTHER_ALTER_RX = re.compile(_ALTER_HEAD + _Q_IDENT + r"(.*?);", re.IGNORECASE | re.DOTALL)
_ADD_RX = re.compile(
    r"\bADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?" + _Q_IDENT + r"\s+[A-Za-z]", re.IGNORECASE
)
_DROP_COL_RX = re.compile(r"\bDROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?" + _Q_IDENT, re.IGNORECASE)
_RENAME_RX = re.compile(
    r"\bRENAME\s+(?:COLUMN\s+)?" + _Q_IDENT + r"\s+TO\s+" + _Q_IDENT, re.IGNORECASE
)
_CREATE_TABLE_RX = re.compile(
    r"\bCREATE\s+(?:UNLOGGED\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?" + _PUBLIC + _Q_IDENT + r"\s*\(",
    re.IGNORECASE,
)
_DROP_TABLE_RX = re.compile(
    r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?" + _PUBLIC + _Q_IDENT, re.IGNORECASE
)
_REFS_USERS = r'REFERENCES\s+(?:"?(?:public|auth)"?\s*\.\s*)?(?:"users"|users\b)'
_REFS_USERS_RX = re.compile(_REFS_USERS, re.IGNORECASE)
_TABLE_FK_RX = re.compile(r"FOREIGN\s+KEY\s*\(([^)]*)\)\s*" + _REFS_USERS, re.IGNORECASE)
_CASCADE_CREATE_RX = re.compile(
    r'\bCREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+' + _PUBLIC + r'"?delete_user_cascade"?\s*\(',
    re.IGNORECASE,
)
_NOT_COLUMN_WORDS = frozenset(
    {"constraint", "primary", "unique", "foreign", "check", "exclude", "not", "default",
     "identity", "expression", "column", "like"}
)


@functools.lru_cache(maxsize=1)
def _real_forward_files_cached() -> tuple[tuple[str, str], ...]:
    return tuple((p.name, _lf(read(p))) for p in forward_sql_files())


def real_forward_files() -> list[tuple[str, str]]:
    return list(_real_forward_files_cached())


def fence_users_columns(files: list[tuple[str, str]]) -> set[str]:
    """F1: baseline + ADD/DROP/RENAME COLUMN on users, comments stripped, DO blocks kept."""
    cols = set(USERS_BASELINE_COLUMNS)
    for _name, sql in files:
        text = strip_line_comments(sql)
        for m in _USERS_ALTER_RX.finditer(text):
            body = m.group(1)
            events = []
            for a in _ADD_RX.finditer(body):
                events.append((a.start(), "add", _ident(a, 1), None))
            for d in _DROP_COL_RX.finditer(body):
                events.append((d.start(), "drop", _ident(d, 1), None))
            for r in _RENAME_RX.finditer(body):
                events.append((r.start(), "rename", _ident(r, 1), _ident(r, 3)))
            for _pos, kind, col, new in sorted(events):
                if col in _NOT_COLUMN_WORDS:
                    continue
                if kind == "add":
                    cols.add(col)
                elif kind == "drop":
                    cols.discard(col)
                else:
                    cols.discard(col)
                    cols.add(new)
    return cols


def _classify(table: str, col: str, has_fk: bool) -> str | None:
    if has_fk or USER_REF_ID_RX.search(col):
        return "id"
    if (table, col) in NOT_PERSONAL:
        return None
    if PERSONAL_RX.search(col):
        return "personal"
    return None


def fence_user_tables(files: list[tuple[str, str]]) -> dict[str, dict[str, str]]:
    """F2: {table: {column: 'id' | 'personal'}} for every table except users."""
    out: dict[str, dict[str, str]] = {
        t: {c: "id" for c in cols} for t, cols in OUT_OF_BAND_USER_TABLES.items()
    }
    for _name, sql in files:
        text = strip_line_comments(sql)
        events = []
        for m in _CREATE_TABLE_RX.finditer(text):
            events.append((m.start(), "create", m))
        for m in _OTHER_ALTER_RX.finditer(text):
            events.append((m.start(), "alter", m))
        for m in _DROP_TABLE_RX.finditer(text):
            events.append((m.start(), "droptable", m))
        for _pos, kind, m in sorted(events, key=lambda e: e[0]):
            table = _ident(m, 1)
            if table == "users":
                continue
            if kind == "droptable":
                out.pop(table, None)
                continue
            if kind == "create":
                inner = _balanced(text, m.end() - 1)
                for item in _split_top(inner):
                    toks = item.split()
                    if not toks:
                        continue
                    first = toks[0].lower()
                    if first in ("constraint", "foreign"):
                        for fk in _TABLE_FK_RX.finditer(item):
                            for c in fk.group(1).split(","):
                                c = c.strip().strip('"').lower()
                                if c:
                                    out.setdefault(table, {})[c] = "id"
                        continue
                    if first in _NOT_COLUMN_WORDS:
                        continue
                    col = toks[0].strip('"').lower()
                    kind_c = _classify(table, col, bool(_REFS_USERS_RX.search(item)))
                    if kind_c:
                        out.setdefault(table, {})[col] = kind_c
                continue
            body = m.group(3)
            for fk in _TABLE_FK_RX.finditer(body):
                for c in fk.group(1).split(","):
                    c = c.strip().strip('"').lower()
                    if c:
                        out.setdefault(table, {})[c] = "id"
            for a in _ADD_RX.finditer(body):
                col = _ident(a, 1)
                if col in _NOT_COLUMN_WORDS:
                    continue
                frag = _split_top(body[a.start():])[0] if body[a.start():].strip() else ""
                kind_c = _classify(table, col, bool(_REFS_USERS_RX.search(frag)))
                if kind_c:
                    out.setdefault(table, {})[col] = kind_c
            for d in _DROP_COL_RX.finditer(body):
                col = _ident(d, 1)
                if col in _NOT_COLUMN_WORDS:
                    continue
                if table in out:
                    out[table].pop(col, None)
    return {t: cols for t, cols in out.items() if cols}


def fence_cascade(files: list[tuple[str, str]]) -> tuple[str | None, str]:
    """F3: (file name, comment-stripped body) of the LAST definition."""
    last: tuple[str | None, str] = (None, "")
    for name, sql in files:
        text = strip_line_comments(sql)
        found = None
        for found in _CASCADE_CREATE_RX.finditer(text):
            pass
        if found is None:
            continue
        spans = [s for s in dollar_bodies(text) if s[0] > found.end()]
        if spans:
            s, e = spans[0]
            last = (name, text[s:e])
    return last


def fence_report(files: list[tuple[str, str]]) -> dict:
    """F1-F5 over an ordered list of (file name, sql text)."""
    users_cols = fence_users_columns(files)
    tables = fence_user_tables(files)
    name, body = fence_cascade(files)
    users_gaps: list[str] = []
    table_gaps: list[str] = []
    if name is None:
        users_gaps.append("no CREATE FUNCTION delete_user_cascade found on the forward path")
        return {"file": None, "users_cols": users_cols, "tables": tables,
                "users_gaps": users_gaps, "table_gaps": table_gaps}
    stmts = parse_body(body)
    for s in stmts:
        if s["kind"] == "other":
            table_gaps.append(f"unrecognised statement in the cascade body: {s['flat'][:80]}")

    # F4 -- users columns
    users_updates = [s for s in stmts if s["kind"] == "update" and s["table"] == "users"]
    assigned: dict[str, str] = {}
    for s in users_updates:
        assigned.update(s["set"])
        if s["where"] != "id = target_user_id":
            users_gaps.append(
                f"users UPDATE WHERE is not exactly `id = target_user_id`: {s['where']!r}"
            )
    for c in sorted(users_cols):
        if c in KEEP_USERS_COLUMNS and c in assigned:
            users_gaps.append(f"users.{c} is both KEEP-listed and erased")
        elif c not in KEEP_USERS_COLUMNS and c not in assigned:
            users_gaps.append(f"users.{c} neither cleared nor KEEP-listed")
    for c in sorted(assigned):
        if c not in users_cols:
            users_gaps.append(f"users.{c} assigned but no migration or baseline creates it")
        elif c not in EXPECTED_TOMBSTONE:
            users_gaps.append(f"users.{c} assigned but not in EXPECTED_TOMBSTONE")
        elif assigned[c] != EXPECTED_TOMBSTONE[c]:
            users_gaps.append(
                f"users.{c} tombstone value {assigned[c]!r} != expected {EXPECTED_TOMBSTONE[c]!r}"
            )
    for c in sorted(EXPECTED_TOMBSTONE):
        if c not in users_cols:
            users_gaps.append(f"EXPECTED_TOMBSTONE names users.{c}, which no migration or baseline creates")

    # F5 -- user-referencing tables
    deletes: dict[str, list[dict]] = {}
    updates: dict[str, list[dict]] = {}
    for s in stmts:
        if s["kind"] == "delete":
            deletes.setdefault(s["table"], []).append(s)
        elif s["kind"] == "update" and s["table"] != "users":
            updates.setdefault(s["table"], []).append(s)
    for t, cols in sorted(tables.items()):
        id_cols = {c for c, k in cols.items() if k == "id"}
        if t in deletes:
            for s in deletes[t]:
                where = s["where"]
                if where is None:
                    table_gaps.append(f"{t}: DELETE without a WHERE clause")
                    continue
                terms = [x.strip() for x in re.split(r"\s+or\s+", where)]
                matched = [_TERM_RX.match(x) for x in terms]
                if not all(matched):
                    table_gaps.append(
                        f"{t}: DELETE WHERE is not an exact OR-chain of `<col> = target_user_id`: {where!r}"
                    )
                    continue
                keyed = {mm.group(1) for mm in matched}
                missing = id_cols - keyed
                if missing:
                    table_gaps.append(f"{t}: DELETE does not key on {sorted(missing)}")
            continue
        nulled: set[str] = set()
        for s in updates.get(t, []):
            w = _TERM_RX.match(s["where"] or "")
            if not w or w.group(1) not in id_cols:
                table_gaps.append(
                    f"{t}: UPDATE WHERE is not exactly `<user id column> = target_user_id`: {s['where']!r}"
                )
                continue
            nulled |= {c for c, v in s["set"].items() if v == "null"}
        for c in sorted(cols):
            if c in nulled or (t, c) in KEEP_TABLE_COLUMNS:
                continue
            table_gaps.append(f"{t}.{c} not deleted, not nulled, not KEEP-listed")
    return {"file": name, "users_cols": users_cols, "tables": tables,
            "users_gaps": users_gaps, "table_gaps": table_gaps}


def _all_gaps(report: dict) -> set[str]:
    return set(report["users_gaps"]) | set(report["table_gaps"])


def _redefinition(body: str) -> str:
    return (
        "CREATE OR REPLACE FUNCTION public.delete_user_cascade(target_user_id uuid)\n"
        "RETURNS void\nLANGUAGE plpgsql\nSECURITY DEFINER\nSET search_path TO 'public'\n"
        "AS $function$" + body + "$function$;\n"
    )


def _new_gaps(extra: list[tuple[str, str]]) -> set[str]:
    real = real_forward_files()
    return _all_gaps(fence_report(real + extra)) - _all_gaps(fence_report(real))


def _latest() -> tuple[str, str, list[dict]]:
    name, body = fence_cascade(real_forward_files())
    assert name is not None, "no cascade definition on the forward path"
    return name, body, parse_body(body)


def _replace_chunk(body: str, idx: int, new_chunk: str) -> str:
    chunks = _body_chunks(body)
    chunks[idx] = new_chunk
    return ";".join(chunks)


# ---------------------------------------------------------------------------
# 5.1 -- migration 043 (RED at base: the file does not exist)
# ---------------------------------------------------------------------------

def test_043_and_rollback_exist_exactly_once_and_039_stays_reserved():
    """U8b 5.1 / UR15: 043 is the next number, 039 stays reserved."""
    fwd = sorted(p.name for p in MIGRATIONS_DIR.glob("043_*.sql"))
    rb = sorted(p.name for p in ROLLBACK_DIR.glob("043_*.sql"))
    assert fwd == [MIG_043_NAME], f"U8b: migrations/043_*.sql is {fwd}, expected [{MIG_043_NAME}]"
    assert rb == [MIG_043_NAME], f"U8b: migrations/rollback/043_*.sql is {rb}, expected [{MIG_043_NAME}]"
    assert not list(MIGRATIONS_DIR.glob("039_*.sql")), "039 is reserved"
    assert not list(ROLLBACK_DIR.glob("039_*.sql")), "039 is reserved"


def test_043_is_one_transaction():
    """U8b 5.1 / R1.1: one BEGIN first, one COMMIT last."""
    sql = _require(MIG_043)
    stmts = [" ".join(s.split()).lower() for s in code_only(sql).split(";")]
    stmts = [s for s in stmts if s]
    assert stmts[0] == "begin", stmts[:1]
    assert stmts[-1] == "commit", stmts[-1:]
    assert stmts.count("begin") == 1 and stmts.count("commit") == 1


def test_043_redefines_the_cascade_security_definer_with_pinned_search_path():
    """U8b 5.1 / R1.1: SECURITY DEFINER and the pinned search_path are restated."""
    sql = strip_line_comments(_require(MIG_043))
    m = re.search(r"create\s+or\s+replace\s+function\s+public\.delete_user_cascade\s*\(", sql, re.I)
    assert m, "043 has no CREATE OR REPLACE FUNCTION public.delete_user_cascade("
    end = sql.find("$function$", m.end())
    header = norm(sql[m.start(): end + len("$function$")])
    assert header == (
        "create or replace function public.delete_user_cascade(target_user_id uuid) "
        "returns void language plpgsql security definer set search_path to 'public' "
        "as $function$"
    ), header


def test_043_body_schema_qualifies_every_relation():
    """U8b 5.1 / R1.3: every relation in the $function$ body is public.<table>."""
    body = strip_line_comments(_function_body_raw(_require(MIG_043)))
    targets = re.findall(r"\b(?:delete\s+from|update|from|join|into)\s+([A-Za-z_\"][\w.\"]*)", body, re.I)
    assert targets, "no relation found in the 043 body"
    bad = [t for t in targets if not t.lower().startswith("public.")]
    assert not bad, f"unqualified relations in the 043 body: {bad}"


def test_043_revokes_after_the_create_and_grants_nothing():
    """U8b 5.1 / R1.1, R1.2, UR9: top-level REVOKE after the CREATE; no GRANT anywhere."""
    sql = _require(MIG_043)
    creates = [off for sig, off in create_or_drop_events(sql) if sig == CASCADE_SIG]
    assert creates, "043 does not (re)define public.delete_user_cascade(uuid)"
    revokes = [
        (roles, off) for sig, roles, off in top_level_revokes(sql)
        if sig == CASCADE_SIG and {"public", "anon", "authenticated"} <= set(roles)
    ]
    assert revokes and max(off for _r, off in revokes) > max(creates), (
        f"no REVOKE naming PUBLIC, anon, authenticated after the CREATE: {revokes}"
    )
    grants = [m.group(0) for m in GRANT_FN.finditer(strip_line_comments(sql))]
    assert not grants, f"043 must restate no GRANT (UR9): {grants}"


def test_043_assert_block_proves_secdef_search_path_and_acl():
    """U8b 5.1 / R1.1, Q7: the $assert$ block proves prosecdef, proconfig and the ACL."""
    sql = strip_line_comments(_require(MIG_043))
    body, start, _end = _tagged_body(sql, "assert")
    revoke_off = max(
        (off for sig, _r, off in top_level_revokes(sql) if sig == CASCADE_SIG), default=-1
    )
    commit_off = sql.rfind("COMMIT;")
    assert revoke_off != -1 and revoke_off < start < commit_off, (
        "the $assert$ block must sit after the REVOKE and before COMMIT"
    )
    b = norm(strip_line_comments(body))
    assert "p.prosecdef" in b
    assert "p.proconfig = array['search_path=public']" in b
    assert re.search(r"if not has_function_privilege\( ?'service_role', ?'public\.delete_user_cascade\(uuid\)', ?'execute' ?\)", b), b
    assert re.search(r"has_function_privilege\( ?'anon', ?'public\.delete_user_cascade\(uuid\)', ?'execute' ?\)", b), b
    assert re.search(r"has_function_privilege\( ?'authenticated', ?'public\.delete_user_cascade\(uuid\)', ?'execute' ?\)", b), b


def test_043_assert_block_runs_the_nil_dry_run_inside_the_transaction():
    """U8b C1: PERFORM of the nil-uuid dry run is the FIRST statement of $assert$,
    between the REVOKE and the COMMIT, so a missing column aborts the apply."""
    sql = strip_line_comments(_require(MIG_043))
    body, start, _end = _tagged_body(sql, "assert")
    revoke_off = max(
        (off for sig, _r, off in top_level_revokes(sql) if sig == CASCADE_SIG), default=-1
    )
    assert revoke_off != -1 and revoke_off < start < sql.rfind("COMMIT;"), (
        "the $assert$ block must sit after the REVOKE and before COMMIT"
    )
    first = _flat(body.split(";")[0]).lower()
    assert first == f"perform public.delete_user_cascade('{NIL_UUID}'::uuid)", first


def _guard_arrays(guard: str) -> tuple[list[str], list[str], list[str]]:
    g = strip_line_comments(guard)

    def items(rx: str) -> list[str]:
        m = re.search(rx, g, re.IGNORECASE | re.DOTALL)
        assert m, f"guard array not found: {rx}"
        return re.findall(r"'([^']*)'", m.group(1))

    tables = items(r"unnest\(\s*ARRAY\[([^\]]*)\]\s*\)\s*AS\s+\w+\s*\(\s*tbl\s*\)")
    exists = items(r"unnest\(\s*ARRAY\[([^\]]*)\]\s*\)\s*AS\s+\w+\s*\(\s*col\s*\)")
    notnull = items(r"is_nullable\s*=\s*'NO'[^;]*?=\s*ANY\s*\(\s*ARRAY\[([^\]]*)\]")
    return tables, exists, notnull


def _users_update_043(sql: str) -> dict:
    stmts = parse_body(strip_line_comments(_function_body_raw(sql)))
    ups = [s for s in stmts if s["kind"] == "update" and s["table"] == "users"]
    assert len(ups) == 1, f"expected exactly one users UPDATE in the 043 body, got {len(ups)}"
    return ups[0]


def test_043_guard_block_matches_what_the_function_writes():
    """U8b 5.1 / R1.5: guard arrays == what the body writes; guard before CREATE."""
    sql = _require(MIG_043)
    _g, gstart, _gend = _tagged_body(strip_line_comments(sql), "guard")
    guard, _s, _e = _tagged_body(sql, "guard")
    tables, exists, notnull = _guard_arrays(guard)
    upd = _users_update_043(sql)
    assigned = upd["set"]
    assert set(exists) == set(assigned), (
        f"guard exists-array != assigned users columns: "
        f"only guard {sorted(set(exists) - set(assigned))}, only body {sorted(set(assigned) - set(exists))}"
    )
    want_null = {c for c, v in assigned.items() if v == "null"}
    assert set(notnull) == want_null, (
        f"guard NOT NULL array != columns assigned NULL: "
        f"only guard {sorted(set(notnull) - want_null)}, only body {sorted(want_null - set(notnull))}"
    )
    body = strip_line_comments(_function_body_raw(sql))
    body_tables = {
        "public." + t.lower()
        for t in re.findall(r"\b(?:delete\s+from|update|from|join)\s+public\.(\w+)", body, re.I)
    }
    assert set(tables) == body_tables | {"public.users"}, (
        f"guard table array != body tables + public.users: {sorted(set(tables) ^ (body_tables | {'public.users'}))}"
    )
    create_off = min(off for sig, off in create_or_drop_events(sql) if sig == CASCADE_SIG)
    assert gstart < create_off, "the $guard$ block must sit before the CREATE"


def test_043_guard_probe_set_map_equals_the_function_set_map_and_expected_tombstone():
    """U8b C3: the temp-table probe at the end of $guard$ writes exactly the
    function's 25 assignments, so a live CHECK rejecting a tombstone value aborts
    the apply inside the transaction."""
    sql = _require(MIG_043)
    guard, _s, _e = _tagged_body(sql, "guard")
    g = strip_line_comments(guard)
    gn = norm(g)
    assert re.search(
        r"create temp(orary)? table u8b_probe \( ?like public\.users including defaults "
        r"including constraints ?\) on commit drop", gn
    ), "no CREATE TEMP TABLE u8b_probe (LIKE public.users INCLUDING DEFAULTS INCLUDING CONSTRAINTS) ON COMMIT DROP"
    assert re.search(rf"insert into u8b_probe \( ?id ?\) values \( ?'{NIL_UUID}' ?\)", gn), "no nil-uuid probe INSERT"
    m = re.search(r"\bUPDATE\s+u8b_probe\s+SET\s+(.*?)(?:\s+WHERE\s+[^;]*)?;(.*)$", g, re.I | re.S)
    assert m, "no UPDATE u8b_probe SET ... in $guard$"
    assert norm(m.group(2)) == "end", f"the probe must end the $guard$ block; after it: {norm(m.group(2))!r}"
    order = [gn.find("create temp"), gn.find("insert into u8b_probe"), gn.find("update u8b_probe")]
    assert order == sorted(order), order
    probe = _set_map(m.group(1))
    assigned = _users_update_043(sql)["set"]
    assert probe == assigned, f"probe map != function map: {sorted(set(probe.items()) ^ set(assigned.items()))}"
    assert probe == EXPECTED_TOMBSTONE, f"probe map != EXPECTED_TOMBSTONE: {sorted(set(probe.items()) ^ set(EXPECTED_TOMBSTONE.items()))}"


def test_043_tombstone_values_are_exactly_the_documented_map():
    """U8b 5.1 / R3, UR2: the users UPDATE map == EXPECTED_TOMBSTONE; WHERE id = target_user_id."""
    upd = _users_update_043(_require(MIG_043))
    assert upd["qualified"], "the users UPDATE must target public.users"
    assert upd["set"] == EXPECTED_TOMBSTONE, (
        f"tombstone map differs: {sorted(set(upd['set'].items()) ^ set(EXPECTED_TOMBSTONE.items()))}"
    )
    assert upd["where"] == "id = target_user_id", upd["where"]


def test_043_keeps_025_deletes_in_order_then_the_u8b_deletes():
    """U8b 5.1 / R1.4: 025's seven DELETEs in order, then the four U8b DELETEs,
    then the audit UPDATE, then the users UPDATE (last)."""
    stmts = parse_body(strip_line_comments(_function_body_raw(_require(MIG_043))))
    dels = [s for s in stmts if s["kind"] == "delete"]
    assert [s["table"] for s in dels] == EXPECTED_DELETE_ORDER, [s["table"] for s in dels]
    by = {s["table"]: s["where"] for s in dels}
    assert by["referral_invites"] == "referrer_user_id = target_user_id or redeemed_by_user_id = target_user_id"
    assert by["referral_redemptions"] == "referrer_user_id = target_user_id or invitee_user_id = target_user_id"
    for t in EXPECTED_DELETE_ORDER:
        if t not in ("referral_invites", "referral_redemptions"):
            assert by[t] == "user_id = target_user_id", (t, by[t])
    kinds = [(s["kind"], s["table"]) for s in stmts]
    assert kinds[-1] == ("update", "users"), kinds[-1]
    assert kinds[-2] == ("update", "admin_audit_log"), kinds[-2]
    assert kinds.index(("update", "admin_audit_log")) > max(
        i for i, k in enumerate(kinds) if k[0] == "delete"
    )
    assert [k for k in kinds if k[0] == "other"] == []


def test_043_detaches_cross_user_comparison_refs_before_deleting_comparisons():
    """U8b C2: user_events and comparison_feedback rows of OTHER users that point
    at the target's comparisons are detached immediately before the DELETE."""
    stmts = parse_body(strip_line_comments(_function_body_raw(_require(MIG_043))))
    kinds = [(s["kind"], s["table"]) for s in stmts]
    i = kinds.index(("delete", "comparisons"))
    assert kinds[i - 2: i] == [("detach", "user_events"), ("detach", "comparison_feedback")], kinds[i - 3: i + 1]
    for s in stmts[i - 2: i]:
        assert s["qualified"], s["flat"]
        assert norm(s["flat"]) == (
            f"update public.{s['table']} set comparison_id = null where comparison_id in "
            "( select c.id from public.comparisons as c where c.user_id = target_user_id )"
        ), s["flat"]


def test_043_never_deletes_users_or_audit_rows():
    """U8b 5.1 / R4, UR3, UR6: no DELETE of users or admin_audit_log rows."""
    sql = strip_line_comments(_require(MIG_043))
    assert not re.search(r"\bdelete\s+from\s+(?:only\s+)?" + _PUBLIC + r'"?users"?\b', sql, re.I)
    assert not re.search(r"\bdelete\s+from\s+(?:only\s+)?" + _PUBLIC + r'"?admin_audit_log"?\b', sql, re.I)
    assert not re.search(r"\btruncate\b", sql, re.I)


def test_043_audit_log_ip_is_nulled_for_the_target_only():
    """U8b 5.1 / Q1, UR3: exactly the audit IP UPDATE keyed on the target."""
    stmts = parse_body(strip_line_comments(_function_body_raw(_require(MIG_043))))
    audit = [s for s in stmts if s["table"] == "admin_audit_log"]
    assert len(audit) == 1, [s["flat"] for s in audit]
    assert norm(audit[0]["flat"]) == (
        "update public.admin_audit_log set ip_address = null where user_id = target_user_id"
    ), audit[0]["flat"]


def test_043_dollar_bodies_carry_no_line_comment():
    """U8b 5.1 / R1.8: no `--` inside $guard$, $function$ or $assert$."""
    sql = _require(MIG_043)
    for tag in ("guard", "function", "assert"):
        body, _s, _e = _tagged_body(sql, tag)
        bad = [ln for ln in body.splitlines() if "--" in ln]
        assert not bad, f"`--` inside ${tag}$: {bad}"


def test_043_is_ascii_only():
    """U8b R1.7: the migration is ASCII only (the rollback carries 025's em dash)."""
    _require(MIG_043)
    raw = MIG_043.read_bytes()
    bad = [i for i, b in enumerate(raw) if b > 127]
    assert not bad, f"non-ASCII bytes at offsets {bad[:5]}"


# ---------------------------------------------------------------------------
# 5.1 -- rollback/043
# ---------------------------------------------------------------------------

def _025_statement() -> str:
    lines = _lf(read(MIG_025)).splitlines(keepends=True)
    span = "".join(lines[27:70])
    assert span.startswith("CREATE OR REPLACE FUNCTION public.delete_user_cascade("), span[:80]
    assert span.rstrip("\n").endswith("$function$;"), span[-40:]
    return span.rstrip("\n")


def test_rollback_043_restores_the_025_statement_byte_for_byte():
    """U8b 5.1 / R2: rollback CREATE ... $function$; == 025 lines 28-70 (LF)."""
    rb = _require(ROLLBACK_043)
    start = rb.find("CREATE OR REPLACE FUNCTION public.delete_user_cascade(")
    assert start != -1, "rollback/043 has no CREATE OR REPLACE FUNCTION public.delete_user_cascade("
    open_m = re.search(r"AS \$function\$", rb[start:])
    assert open_m, "rollback/043 has no AS $function$"
    close = rb.find("$function$;", start + open_m.end())
    assert close != -1
    got = rb[start: close + len("$function$;")]
    want = _025_statement()
    assert got == want, "rollback/043 statement differs from migrations/025 lines 28-70"


def test_rollback_043_is_one_transaction_revokes_and_grants_nothing():
    """U8b 5.1 / R2: BEGIN/COMMIT, a REVOKE naming the three roles, no GRANT."""
    rb = _require(ROLLBACK_043)
    stmts = [s for s in (" ".join(x.split()).lower() for x in code_only(rb).split(";")) if s]
    assert stmts[0] == "begin" and stmts[-1] == "commit", (stmts[:1], stmts[-1:])
    assert stmts.count("begin") == 1 and stmts.count("commit") == 1
    revokes = [roles for sig, roles, _o in top_level_revokes(rb) if sig == CASCADE_SIG]
    assert any({"public", "anon", "authenticated"} <= set(r) for r in revokes), revokes
    assert not list(GRANT_FN.finditer(strip_line_comments(rb))), "rollback/043 must grant nothing"


def test_rollback_043_header_says_it_restores_the_function_only():
    """U8b R2: the header says it restores the FUNCTION only; erased data stays erased."""
    rb = _require(ROLLBACK_043)
    head = norm(comment_lines(rb[: rb.find("BEGIN;")] if "BEGIN;" in rb else rb))
    assert "restores the function only" in head, head[:300]
    assert "stay erased" in head, head[:300]
    assert "025" in head


# ---------------------------------------------------------------------------
# 5.1 -- the one-paste files (R8, R9, C1, C2, C4, C9)
# ---------------------------------------------------------------------------

def _txn_span(text: str) -> str:
    b = re.search(r"^BEGIN;[ \t]*$", text, re.M)
    c = list(re.finditer(r"^COMMIT;[ \t]*$", text, re.M))
    assert b and c, "no BEGIN; ... COMMIT; lines"
    return text[b.start(): c[-1].end()]


def test_one_paste_body_is_byte_identical_to_043():
    """U8b 5.1 / R8.2: ONE_PASTE BEGIN;...COMMIT; == 043's (LF)."""
    one = _require(ONE_PASTE)
    mig = _require(MIG_043)
    assert _txn_span(one) == _txn_span(mig), "ONE_PASTE body differs from migrations/043"


def test_precheck_is_read_only():
    """U8b 5.1 / R8.1, C4: no write word and no cascade call in PRECHECK code."""
    pre = _require(PRECHECK)
    code = _blank_literals(code_only(pre))
    writes = re.findall(r"\b(insert|update|delete|alter|create|drop|grant|revoke|truncate)\b", code, re.I)
    assert not writes, f"PRECHECK is not read-only: {writes}"
    assert "delete_user_cascade(" not in code, "PRECHECK calls delete_user_cascade"
    assert re.search(r"\bselect\b", code, re.I)


_MD5_SQL_COMPACT = _compact(
    "md5(btrim(regexp_replace(regexp_replace(p.prosrc, '^\\s*-{2}.*$', '', 'gn'), '\\s+', ' ', 'g')))"
)


def test_postcheck_only_call_is_the_nil_uuid_dry_run_and_its_md5_matches_043():
    """U8b 5.1 / R8.3, C4: one cascade call (nil uuid), md5_norm of 043's body,
    and the same md5_norm SQL expression as PRECHECK."""
    post = _require(POSTCHECK)
    pre = _require(PRECHECK)
    mig = _require(MIG_043)
    code = _blank_literals(code_only(post))
    assert code.count("delete_user_cascade(") == 1, code.count("delete_user_cascade(")
    args = re.findall(r"delete_user_cascade\(\s*'([^']*)'::uuid\s*\)", strip_line_comments(post))
    assert args == [NIL_UUID], args
    digest = md5_norm(_function_body_raw(mig))
    assert f"md5_norm={digest}" in post, f"POSTCHECK does not carry md5_norm={digest}"
    for name, text in (("PRECHECK", pre), ("POSTCHECK", post)):
        assert _MD5_SQL_COMPACT in _compact(strip_line_comments(text)), (
            f"{name} does not carry the md5_norm SQL expression with '^\\s*-{{2}}.*$'"
        )


def test_check_files_have_only_whole_line_comments():
    """U8b C4: in 043, rollback/043 and every APPLY_043_* file, every `--` starts a
    whole-line comment, so the naive comment stripper is exact."""
    for path in (MIG_043, ROLLBACK_043, PRECHECK, ONE_PASTE, POSTCHECK, BACKFILL):
        text = _require(path)
        bad = [ln for ln in text.splitlines() if "--" in ln and not ln.lstrip().startswith("--")]
        assert not bad, f"{path.name}: `--` not at the start of a whole-line comment: {bad[:3]}"


def test_precheck_carries_the_c1_c2_c9_sections():
    """U8b C1 (section 12), C2 (section 10), C9 (sections 8, 11): read-only probes
    for nil-uuid rows, cross-user comparison refs, triggers on all 13 tables, RLS."""
    pre = _require(PRECHECK)
    code = strip_line_comments(pre)
    low = code.lower()
    for word in ("nil_uuid_rows", "cross_user_comparison_refs", "pg_trigger",
                 "relrowsecurity", "relforcerowsecurity", "rolbypassrls", NIL_UUID):
        assert word in low, f"PRECHECK lacks {word!r}"
    for t in sorted(KNOWN_USER_TABLES | {"users"}):
        assert f"public.{t}" in low, f"PRECHECK never names public.{t}"
    for col in ("user_id", "referrer_user_id", "redeemed_by_user_id", "invitee_user_id", "comparison_id"):
        assert col in low, f"PRECHECK never names {col}"
    trig = low[low.find("'trigger'"):]
    trig = trig[: trig.find("union all")] if "union all" in trig else trig
    missing = [t for t in sorted(KNOWN_USER_TABLES | {"users"}) if f"public.{t}" not in trig]
    assert not missing, f"PRECHECK section 8 (triggers) does not cover: {missing}"


def test_backfill_erases_only_orphans_in_one_transaction():
    """U8b R9, UR4: the optional backfill runs the cascade and the audit-IP clear
    only for users with no auth.users row, in one transaction, and writes nothing else."""
    bf = _require(BACKFILL)
    code = _blank_literals(code_only(bf))
    stmts = [s for s in (" ".join(x.split()).lower() for x in code.split(";")) if s]
    assert stmts.count("begin") == 1 and stmts.count("commit") == 1
    assert stmts.index("begin") < stmts.index("commit")
    writes = [w.lower() for w in re.findall(
        r"\b(insert|update|delete|alter|create|drop|grant|revoke|truncate)\b", code, re.I)]
    assert writes == ["update"], writes
    comp = _compact(strip_line_comments(bf))
    assert comp.count("delete_user_cascade(") == 1
    assert (
        "selectpublic.delete_user_cascade(u.id)frompublic.usersasu"
        "wherenotexists(select1fromauth.usersasawherea.id=u.id)"
    ) in comp
    assert "updatepublic.admin_audit_logaslsetip_address=null" in comp
    assert "andnotexists(select1fromauth.usersasawherea.id=l.user_id)" in comp


# ---------------------------------------------------------------------------
# 5.1 RED -- the fence coverage tests (the defect itself at base)
# ---------------------------------------------------------------------------

def test_cascade_erases_or_keeps_every_users_column():
    """U8b 5.1 / F1, F4: every users column is erased to the documented
    tombstone value or KEEP-listed (RED at base: the 20 users gaps of 025)."""
    rep = fence_report(real_forward_files())
    assert not rep["users_gaps"], (
        f"{len(rep['users_gaps'])} users gaps (cascade defined last in {rep['file']}):\n"
        + "\n".join("GAP " + g for g in rep["users_gaps"])
    )


def test_cascade_erases_or_keeps_every_user_referencing_table():
    """U8b 5.1 / F2, F5: every user-referencing table is deleted by an exact
    WHERE, or its user columns are nulled or KEEP-listed (RED at base:
    admin_audit_log.ip_address and four tables)."""
    rep = fence_report(real_forward_files())
    assert not rep["table_gaps"], (
        f"{len(rep['table_gaps'])} table gaps (cascade defined last in {rep['file']}):\n"
        + "\n".join("GAP " + g for g in rep["table_gaps"])
    )


# ---------------------------------------------------------------------------
# 5.3 PIN -- fence self-tests (pass whenever the parser works; base and head)
# ---------------------------------------------------------------------------

def test_fence_sees_the_27_known_users_columns():
    """U8b 5.3 / F1, UR2: the fence rebuilds exactly the 27 live users columns."""
    cols = fence_users_columns(real_forward_files())
    assert cols == KNOWN_USERS_COLUMNS, (
        f"only fence {sorted(cols - KNOWN_USERS_COLUMNS)}, only UR2 {sorted(KNOWN_USERS_COLUMNS - cols)}"
    )


def test_fence_sees_the_12_known_user_tables():
    """U8b 5.3 / F2: the fence finds exactly the 12 user-referencing tables of 2b."""
    tables = fence_user_tables(real_forward_files())
    assert set(tables) == KNOWN_USER_TABLES, (
        f"only fence {sorted(set(tables) - KNOWN_USER_TABLES)}, only 2b {sorted(KNOWN_USER_TABLES - set(tables))}"
    )
    assert tables["admin_audit_log"] == {"user_id": "id", "ip_address": "personal"}, tables["admin_audit_log"]
    assert tables["referral_invites"]["redeemed_by_user_id"] == "id"
    assert tables["referral_redemptions"]["invitee_user_id"] == "id"


def test_keep_allowlists_are_justified_and_not_stale():
    """U8b 5.3 / F6, R4: every KEEP entry is justified (>= 40 chars), exists in
    F1/F2, and is not also erased; EXPECTED_TOMBSTONE and KEEP are disjoint."""
    files = real_forward_files()
    cols = fence_users_columns(files)
    tables = fence_user_tables(files)
    for name, allow in (
        ("USERS_BASELINE_COLUMNS", USERS_BASELINE_COLUMNS),
        ("KEEP_USERS_COLUMNS", KEEP_USERS_COLUMNS),
        ("KEEP_TABLE_COLUMNS", KEEP_TABLE_COLUMNS),
        ("NOT_PERSONAL", NOT_PERSONAL),
        ("KEPT_USER_CACHE_KEY_TEMPLATES", KEPT_USER_CACHE_KEY_TEMPLATES),
    ):
        short = [k for k, v in allow.items() if len(v.strip()) < 40]
        assert not short, f"{name}: justification shorter than 40 chars for {short}"
    stale_u = [c for c in KEEP_USERS_COLUMNS if c not in cols]
    assert not stale_u, f"KEEP_USERS_COLUMNS names no users column: {stale_u}"
    stale_t = [k for k in KEEP_TABLE_COLUMNS if k[1] not in tables.get(k[0], {})]
    assert not stale_t, f"KEEP_TABLE_COLUMNS names no user-ref column: {stale_t}"
    both = sorted(set(KEEP_USERS_COLUMNS) & set(EXPECTED_TOMBSTONE))
    assert not both, f"KEEP-listed and erased: {both}"
    assert set(KEEP_USERS_COLUMNS) | set(EXPECTED_TOMBSTONE) == KNOWN_USERS_COLUMNS


def _assert_new_gap(extra: list[tuple[str, str]], *needles: str) -> None:
    new = _new_gaps(extra)
    for needle in needles:
        assert any(needle in g for g in new), f"no new gap names {needle!r}; new gaps: {sorted(new)}"


@pytest.mark.parametrize(
    "label, sql, needle",
    [
        ("5.3 phone_number via a later ALTER (spec M5 / 044_zz_mutant)",
         "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone_number TEXT;", "users.phone_number"),
        ("C5 A: DO-block ADD COLUMN (the 001 idiom)",
         "DO $$\nBEGIN\n  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' "
         "AND column_name = 'phone_number') THEN\n    ALTER TABLE users ADD COLUMN phone_number TEXT;\n"
         "  END IF;\nEND $$;", "users.phone_number"),
        ("C5 B: quoted identifier",
         'ALTER TABLE "users" ADD COLUMN phone_number TEXT;', "users.phone_number"),
        ("C5 B': quoted schema and table",
         'ALTER TABLE "public"."users" ADD COLUMN "phone_number" TEXT;', "users.phone_number"),
        ("C5 C: REFERENCES users without a column list",
         "CREATE TABLE IF NOT EXISTS public.support_tickets (id uuid PRIMARY KEY, owner uuid "
         "REFERENCES public.users ON DELETE CASCADE, body text);", "support_tickets.owner"),
        ("C5 D: phone_number and full_name",
         "CREATE TABLE IF NOT EXISTS public.waitlist (id uuid PRIMARY KEY, phone_number text, full_name text);",
         "waitlist.phone_number"),
        ("C5 E: anon_id, device_id, client_ip",
         "CREATE TABLE IF NOT EXISTS public.device_installs (id uuid PRIMARY KEY, anon_id text, "
         "device_id text, client_ip inet);", "device_installs.anon_id"),
        ("C5 F: table-level FOREIGN KEY",
         "CREATE TABLE IF NOT EXISTS public.notes (id uuid PRIMARY KEY, author uuid, note text, "
         "CONSTRAINT notes_author_fk FOREIGN KEY (author) REFERENCES public.users (id) ON DELETE CASCADE);",
         "notes.author"),
        ("C5 G: created_by REFERENCES auth.users",
         "CREATE TABLE IF NOT EXISTS public.audit2 (id uuid PRIMARY KEY, created_by uuid "
         "REFERENCES auth.users (id), payload jsonb);", "audit2.created_by"),
        ("5.3 new table with a user FK",
         "CREATE TABLE IF NOT EXISTS public.saved_lists (id uuid PRIMARY KEY, owner_id uuid "
         "REFERENCES public.users (id));", "saved_lists.owner_id"),
        ("5.3 personal column without an FK",
         "CREATE TABLE IF NOT EXISTS public.contact_requests (id uuid PRIMARY KEY, contact_email text);",
         "contact_requests.contact_email"),
        ("C5: ALTER TABLE ADD COLUMN with a user FK on another table",
         "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS submitted_by_user_id uuid "
         "REFERENCES public.users (id);", "products.submitted_by_user_id"),
    ],
)
def test_fence_flags_a_ddl_mutant(label, sql, needle):
    """U8b 5.3 / C5 (a)-(d), spec M5: each DDL mutant, appended in memory as a
    later migration, makes the fence report a NEW gap that names it."""
    _assert_new_gap([("999_m.sql", sql)], needle)
    if needle.startswith("users."):
        _assert_new_gap([("999_m.sql", sql)], f"{needle} neither cleared nor KEEP-listed")
    else:
        _assert_new_gap([("999_m.sql", sql)], f"{needle} not deleted, not nulled, not KEEP-listed")


def test_fence_reads_the_latest_definition():
    """U8b 5.3 / F3: a later file redefining the cascade with no users UPDATE
    makes every column the latest definition clears a new gap."""
    _name, body, stmts = _latest()
    ups = [s for s in stmts if s["kind"] == "update" and s["table"] == "users"]
    assert ups, "the latest cascade has no users UPDATE"
    mutated = _replace_chunk(body, ups[0]["idx"], "\n")
    new = _new_gaps([("999_m.sql", _redefinition(mutated))])
    for col in ups[0]["set"]:
        assert f"users.{col} neither cleared nor KEEP-listed" in new, (col, sorted(new))


def test_fence_flags_each_dropped_delete():
    """U8b 5.4 M2 (generalised): removing any one DELETE from the latest
    definition makes that table a new gap."""
    _name, body, stmts = _latest()
    dels = [s for s in stmts if s["kind"] == "delete"]
    assert len(dels) >= 7, len(dels)
    for s in dels:
        new = _new_gaps([("999_m.sql", _redefinition(_replace_chunk(body, s["idx"], "\n")))])
        assert any(g.startswith(f"{s['table']}.") or g.startswith(f"{s['table']}:") for g in new), (
            s["table"], sorted(new))


def test_fence_flags_each_weakened_delete_predicate():
    """U8b C5 K / C5(e): `... AND consumed_at IS NULL` on any DELETE breaks the
    exact OR-chain shape and is a new gap."""
    _name, body, stmts = _latest()
    for s in (x for x in stmts if x["kind"] == "delete"):
        chunk = _body_chunks(body)[s["idx"]]
        new = _new_gaps([("999_m.sql", _redefinition(
            _replace_chunk(body, s["idx"], chunk + " AND consumed_at IS NULL")))])
        assert f"{s['table']}: DELETE WHERE is not an exact OR-chain" in " ".join(new), (s["table"], sorted(new))


def test_fence_flags_a_dropped_referral_role_clause():
    """U8b 5.4 M7: dropping `OR redeemed_by_user_id = target_user_id` is a gap."""
    _name, body, _stmts = _latest()
    mutated, n = re.subn(r"\s+OR\s+redeemed_by_user_id\s*=\s*target_user_id", "", body, flags=re.I)
    assert n == 1, n
    _assert_new_gap([("999_m.sql", _redefinition(mutated))],
                    "referral_invites: DELETE does not key on ['redeemed_by_user_id']")


def _users_update_variants(body: str, stmts: list[dict]):
    ups = [s for s in stmts if s["kind"] == "update" and s["table"] == "users"]
    assert len(ups) == 1, len(ups)
    up = ups[0]
    return up, (lambda setmap, where: (
        f"\n  UPDATE public.users SET "
        + ", ".join(f"{c} = {v}" for c, v in setmap.items())
        + f" WHERE {where}\n"
    ))


def test_fence_flags_each_dropped_users_assignment():
    """U8b 5.4 M1 (generalised): dropping any one assignment of the users
    UPDATE (email = NULL at head) makes that column a new gap."""
    _name, body, stmts = _latest()
    up, build = _users_update_variants(body, stmts)
    for col in up["set"]:
        rest = {c: v for c, v in up["set"].items() if c != col}
        mutated = _replace_chunk(body, up["idx"], build(rest, up["where"]))
        _assert_new_gap([("999_m.sql", _redefinition(mutated))], f"users.{col} neither cleared nor KEEP-listed")


def test_fence_flags_each_self_assignment():
    """U8b C5 L / 5.4 M11 (generalised): `col = col` (email = email at head) keeps
    the value and is a new gap through the EXPECTED_TOMBSTONE map equality."""
    _name, body, stmts = _latest()
    up, build = _users_update_variants(body, stmts)
    for col in up["set"]:
        setmap = dict(up["set"])
        setmap[col] = col
        mutated = _replace_chunk(body, up["idx"], build(setmap, up["where"]))
        _assert_new_gap([("999_m.sql", _redefinition(mutated))], f"users.{col} tombstone value '{col}'")


def test_fence_flags_a_users_where_that_targets_nobody():
    """U8b C5 M / C5(e): `WHERE id = target_user_id AND false` is a gap."""
    _name, body, stmts = _latest()
    up, build = _users_update_variants(body, stmts)
    mutated = _replace_chunk(body, up["idx"], build(up["set"], "id = target_user_id AND false"))
    _assert_new_gap([("999_m.sql", _redefinition(mutated))], "users UPDATE WHERE is not exactly")


def test_fence_flags_a_value_mismatch_and_an_unknown_statement():
    """U8b C5(f): a wrong tombstone value and an unparsed statement are gaps."""
    _name, body, stmts = _latest()
    up, build = _users_update_variants(body, stmts)
    setmap = dict(up["set"])
    col = sorted(setmap)[0]
    setmap[col] = "'kept'"
    mutated = _replace_chunk(body, up["idx"], build(setmap, up["where"]))
    _assert_new_gap([("999_m.sql", _redefinition(mutated))], f"users.{col} tombstone value \"'kept'\"")
    extra = _replace_chunk(
        body, up["idx"], _body_chunks(body)[up["idx"]] + ";\n  PERFORM pg_sleep(0)")
    _assert_new_gap([("999_m.sql", _redefinition(extra))], "unrecognised statement in the cascade body")


# ---------------------------------------------------------------------------
# C8 -- the reverse Redis drift fence
# ---------------------------------------------------------------------------

_USER_EXPR_RX = re.compile(r"(^|\W)(user_id|uid)($|\W)|current_user\s*\[")
_KEY_PREFIX_RX = re.compile(r"^[a-z][a-z0-9_]*(:[a-z0-9_]+)*:$")


def _normalise_template(parts: list[tuple[str, str | None]]) -> str:
    out = []
    for const, expr in parts:
        if expr is None:
            out.append(const)
        else:
            out.append("{user_id}" if _USER_EXPR_RX.search(expr) else "{*}")
    return "".join(out)


def _app_user_key_templates() -> dict[str, list[str]]:
    """{normalised template: [file:line, ...]} for every f-string in app/ that
    looks like a Redis key (lower-case `a:b:` prefix) and interpolates a user id."""
    found: dict[str, list[str]] = {}
    for path in sorted(APP_DIR.rglob("*.py")):
        tree = ast.parse(read(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.JoinedStr) or not node.values:
                continue
            parts: list[tuple[str, str | None]] = []
            for v in node.values:
                if isinstance(v, ast.Constant):
                    parts.append((str(v.value), None))
                elif isinstance(v, ast.FormattedValue):
                    parts.append(("", ast.unparse(v.value)))
            if not parts or parts[0][1] is not None or not _KEY_PREFIX_RX.match(parts[0][0]):
                continue
            if not any(e is not None and _USER_EXPR_RX.search(e) for _c, e in parts):
                continue
            tpl = _normalise_template(parts)
            found.setdefault(tpl, []).append(
                f"{path.relative_to(REPO_ROOT).as_posix()}:{node.lineno}"
            )
    return found


def test_every_per_user_cache_key_is_purged_or_kept():
    """U8b C8: every per-user Redis key f-string in app/ is purged on deletion
    (auth_service.DELETED_USER_CACHE_KEY_TEMPLATES) or listed in the justified
    KEPT_USER_CACHE_KEY_TEMPLATES (RED at base: the purge constant is absent)."""
    found = _app_user_key_templates()
    assert set(EXPECTED_PURGED_TEMPLATES) <= set(found), (
        f"census lost a known writer: {sorted(set(EXPECTED_PURGED_TEMPLATES) - set(found))}"
    )
    from app.services import auth_service

    purged = getattr(auth_service, "DELETED_USER_CACHE_KEY_TEMPLATES", None)
    assert purged is not None, (
        "U8b: app.services.auth_service.DELETED_USER_CACHE_KEY_TEMPLATES does not exist "
        "(no per-user cache is purged on account deletion)"
    )
    purged_norm = {
        re.sub(r"\{([^}]*)\}", lambda m: "{user_id}" if _USER_EXPR_RX.search(m.group(1)) else "{*}", t)
        for t in purged
    }
    unhandled = {t: where for t, where in found.items()
                 if t not in purged_norm and t not in KEPT_USER_CACHE_KEY_TEMPLATES}
    assert not unhandled, f"per-user cache keys neither purged nor KEPT: {unhandled}"
    stale = [t for t in KEPT_USER_CACHE_KEY_TEMPLATES if t not in found]
    assert not stale, f"KEPT_USER_CACHE_KEY_TEMPLATES names no writer: {stale}"
    both = sorted(purged_norm & set(KEPT_USER_CACHE_KEY_TEMPLATES))
    assert not both, f"both purged and KEPT: {both}"
