"""S81-14 KB-SCHEMA: migrations 045 (kb_* core) + 047 (the 012 REVOKE) and the
pure leaf app/services/kb_service.py.

RED file per RULINGS_S81_14 (R-S14-1..16) over the spec as amended by its
adversarial review. The unit has NO runtime flag and no call site: the PIN rows
prove no behaviour change (no importer of the leaf, no kb_* relation named in
app/ or scripts/, every 012 client is the service-role client, the identity
helpers it reuses unchanged, the FY25 / W4-13 identity nodes untouched, the
043 fence and column census green, every migration actually linted by
sqlfluff, the flag env set AFTER the dotenv-loading imports). The RED rows pin
the migration text and the leaf.

Deliberate-change points for later units: P1 / P2 (S81-15 merchant_registry
KB_MERCHANTS_TABLE, S81-17 kb_ingest_compare, S81-18 kb_product_card readers)
must be listed by those units as deliberate changes.

Hermetic: no network (the R-MIG zero-network guard, attempts asserted empty),
no .env, no real credential. Synthetic values only: hosts under .example,
GTINs built at run time from short digit strings, device keys built at run
time. Every RED row fails at base on an AssertionError only (missing files and
the missing module are asserted, never raised).
"""
from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from tests import _retro_r_mig_sql as _sql
from tests import test_migration_043_delete_user_cascade as t043
from tests import test_migration_index_predicate_immutability as timm

ROOT = Path(__file__).resolve().parent.parent
MIG = ROOT / "migrations"
RB = MIG / "rollback"
F045 = MIG / "045_kb_core.sql"
F047 = MIG / "047_012_revoke.sql"
R045 = RB / "045_kb_core.sql"
R047 = RB / "047_012_revoke.sql"
F012 = MIG / "012_product_data_tables.sql"
SQLFLUFF_CFG = ROOT / ".sqlfluff"
LEAF = ROOT / "app" / "services" / "kb_service.py"
LEAF_MOD = "app.services.kb_service"
FOUR_FILES = (F045, R045, F047, R047)

KB_TABLE_NAMES = (
    "kb_merchants", "kb_products", "kb_variants", "kb_offers", "kb_images",
    "kb_specs", "kb_reviews", "kb_gaps", "kb_feedback", "kb_coverage_daily",
)
KB_FUNCTIONS = {
    "kb_gtin_check_digit_ok": ("text",),
    "kb_set_updated_at": (),
    "kb_prune_offers": ("integer", "integer"),
    "kb_prune_feedback": ("integer",),
    "kb_product_card": ("text", "text"),
}
KB_RELATION_NAMES = frozenset(KB_TABLE_NAMES) | {"kb_offers_latest"} | set(KB_FUNCTIONS)
TABLES_012 = ("product_specs", "product_prices", "product_reviews")

T0 = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
PID = "fragrances|christian+dior|sauvage|EDP"
VID = PID + "|100"
DK = "ab" * 32  # a synthetic 64-hex device key (S81-05 HMAC shape)


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts = _sql.install_network_guard(monkeypatch)
    yield
    assert attempts == [], "S81-14 tests must not touch the network: %r" % attempts


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n")


def _read(path: Path) -> str:
    return _lf(path.read_text(encoding="utf-8"))


def _require(path: Path) -> str:
    assert path.is_file(), (
        "S81-14: %s does not exist yet (RED until GREEN writes it)"
        % path.relative_to(ROOT).as_posix()
    )
    return _read(path)


def _kb():
    spec = importlib.util.find_spec(LEAF_MOD)
    assert spec is not None, "S81-14 leaf app/services/kb_service.py missing"
    return importlib.import_module(LEAF_MOD)


def _attr(obj, name: str):
    assert hasattr(obj, name), "S81-14: kb_service.%s missing" % name
    return getattr(obj, name)


def _compact(text: str) -> str:
    s = " ".join(text.split())
    s = re.sub(r"\(\s+", "(", s)
    return re.sub(r"\s+\)", ")", s)


def _code(sql: str) -> str:
    """Comments stripped AND dollar bodies blanked (literals kept)."""
    return _sql.code_only(sql)


def _no_comments(sql: str) -> str:
    return _sql.strip_line_comments(sql)


def _statements(sql: str) -> list[str]:
    """Top-level statements of a file (comments stripped, dollar bodies blanked)."""
    return [_compact(s) for s in _code(sql).split(";") if s.strip()]


_CREATE_TABLE = re.compile(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+public\.([a-z_]+)\s*\(", re.I)


def _table_items(sql: str) -> dict[str, list[str]]:
    clean = _no_comments(sql)
    out: dict[str, list[str]] = {}
    for m in _CREATE_TABLE.finditer(clean):
        body = t043._balanced(clean, m.end() - 1)
        out[m.group(1)] = [_compact(x) for x in t043._split_top(body)]
    return out


def _is_constraint(item: str) -> bool:
    return item.upper().startswith(("CONSTRAINT ", "PRIMARY KEY"))


def _columns(sql: str, table: str) -> list[str]:
    items = _table_items(sql).get(table)
    assert items is not None, "045 does not create public.%s" % table
    return [i for i in items if not _is_constraint(i)]


def _constraints(sql: str, table: str) -> list[str]:
    items = _table_items(sql).get(table) or []
    return [i for i in items if _is_constraint(i)]


def _strip_checks(item: str) -> str:
    out, i = "", 0
    while True:
        m = re.search(r"\bCHECK\s*\(", item[i:], re.I)
        if not m:
            return out + item[i:]
        out += item[i:i + m.start()]
        open_idx = i + m.end() - 1
        body = t043._balanced(item, open_idx)
        i = open_idx + len(body) + 2


def _col_tuple(item: str) -> tuple:
    name = item.split()[0]
    rest = _strip_checks(item[len(name):]).strip()
    m = re.match(r"(.+?)(?=\s+(?:PRIMARY|NOT|NULL|DEFAULT|REFERENCES|UNIQUE)\b|$)", rest)
    typ = m.group(1).strip() if m else ""
    up = rest.upper()
    dm = re.search(r"\bDEFAULT\s+('(?:[^']|'')*'(?:::\w+)?|[\w.]+\(\)|\S+)", rest, re.I)
    return (name, typ, ("NOT NULL" in up or "PRIMARY KEY" in up), dm.group(1) if dm else None)


def _function_block(sql: str, name: str) -> str:
    """The whole CREATE FUNCTION statement text for public.<name> (comments stripped)."""
    clean = _no_comments(sql)
    m = re.search(r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.%s\s*\(" % re.escape(name), clean, re.I)
    assert m, "045 does not create public.%s" % name
    body_open = clean.find("$$", m.end())
    body_close = clean.find("$$", body_open + 2)
    assert body_open != -1 and body_close != -1, "public.%s has no $$ body" % name
    return clean[m.start(): body_close + 2]


def _function_body(sql: str, name: str) -> str:
    block = _function_block(sql, name)
    first = block.find("$$")
    return block[first + 2: block.rfind("$$")]


def _function_head(sql: str, name: str) -> str:
    block = _function_block(sql, name)
    return block[: block.find("$$")]


def _signature(head: str) -> tuple:
    m = re.search(r"FUNCTION\s+public\.\w+\s*\((.*?)\)\s*RETURNS", head, re.I | re.S)
    assert m, "no argument list in %r" % head[:80]
    args = [a.strip() for a in m.group(1).split(",") if a.strip()]
    return tuple(a.split()[1].lower() for a in args)


def _check_text(item: str) -> str:
    m = re.search(r"\bCHECK\s*\(", item, re.I)
    assert m, "no CHECK in %r" % item
    return t043._balanced(item, m.end() - 1)


def _quoted_regexes(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"!?~\*?\s*'((?:[^']|'')*)'", text)]


def _py(sql_regex: str) -> re.Pattern:
    pat = sql_regex.replace("[:space:]", r"\s")
    if pat.endswith("$"):
        pat = pat[:-1] + r"\Z"
    return re.compile(pat)


def _labels() -> list[str]:
    from app.services import deny_hosts

    return sorted(deny_hosts.DENY_LABELS)


def _host_belt() -> str:
    return "(^|[.])(" + "|".join(_labels()) + ")[.]"


def _url_belt() -> str:
    return "^https?://([^/]*[.])?(" + "|".join(_labels()) + ")[.]"


HOST_RE = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
HOST_CORE = HOST_RE[1:-1]
OFFER_URL_RE = "^https?://" + HOST_CORE + "/[^?#[:space:]]*$"
IMAGE_URL_RE = "^https://" + HOST_CORE + "/[^#[:space:]]*$"
SOURCE_URL_RE = "^https?://" + HOST_CORE + "/[^#[:space:]]*$"


def _gtin(body: str) -> str:
    """body + its GS1 mod-10 check digit (test-side, independent of the leaf)."""
    n = len(body) + 1
    total = sum(int(body[i - 1]) * (3 if (n - i) % 2 == 1 else 1) for i in range(1, n))
    return body + str((10 - total % 10) % 10)


def _gtins() -> dict[int, str]:
    return {
        8: _gtin("963" + "8507"),
        12: _gtin("036" + "000" + "29145"),
        13: _gtin("400" + "638" + "133393"),
        14: _gtin("1" + "061" + "414" + "100000"),
    }


@pytest.fixture
def prod_identity_env(monkeypatch):
    """R-S14-14 / review C17: import the dotenv-loading modules FIRST, then set
    the production flag state (exact gate ON, empty-fix OFF) explicitly."""
    importlib.import_module("app.main")
    importlib.import_module("app.services.price_service")
    importlib.import_module("app.services.spec_spine_service")

    def _set(gate):
        if gate is None:
            monkeypatch.delenv("ENABLE_EXACT_PRICE_GATE", raising=False)
        else:
            monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
        monkeypatch.delenv("ENABLE_NORMALIZE_WORDS_EMPTY_FIX", raising=False)

    return _set


GATE_STATES = [None, "true", " TRUE "]

# (brand, name, variant) -> spine_key at base e1878dd8 (measured, gate unset / true / " TRUE ").
SPINE_MATRIX = [
    (("Dior", "Sauvage Eau de Parfum 100ml Spray for Men", None), "fragrances|christian+dior|sauvage|EDP|100"),
    (("Dior", "Sauvage EDP 50 ml Natural Spray", None), "fragrances|christian+dior|sauvage|EDP|50"),
    (("Christian Dior", "Sauvage EDP", None), "fragrances|christian+dior|sauvage|EDP|-"),
    (("Dior", "Sauvage EDT 100ml", None), "fragrances|christian+dior|sauvage|EDT|100"),
    (("YSL", "Y Eau de Parfum 3.4 oz", None), "fragrances|laurent+saint+ysl+yves||EDP|100"),
    (("", "", None), "fragrances|||-|-"),
    (("Lattafa", "Khamrah | 100ml", None), "fragrances|lattafa|khamrah|-|100"),
    (("Dior", "Sauvage", "Elixir"), "fragrances|christian+dior|elixir-sauvage|-|-"),
    (("Dior", "Sauvage", "EDP 60ml"), "fragrances|christian+dior|sauvage|EDP|60"),
    (("Unknown", "Unknown Product", None), "fragrances|unknown|product|-|-"),
    (("Dior", "Sauvage EDP 0ml", None), "fragrances|christian+dior|sauvage|EDP|-"),
    (("Dior", "Sauvage EDP 10000 ml", None), "fragrances|christian+dior|sauvage|EDP|-"),
    (("Dior", "Sauvage EDP 7.5ml sample", None), "fragrances|christian+dior|sample-sauvage|EDP|5"),
    (("Dior", "Sauvage EDP 100ml + 10ml travel spray", None), "fragrances|christian+dior|plus-sauvage|EDP|10"),
    (("Dior", "Sauvage EDP 6000ml", None), "fragrances|christian+dior|sauvage|EDP|6000"),
    (("Emporio Armani", "Stronger With You EDT 100ml", None), "fragrances|armani+emporio+giorgio|stronger-you|EDT|100"),
]
# kb_product_id for the same rows (R-S14-3 juice id WITH concentration; R-S14-9 placeholder None).
PRODUCT_IDS = {
    0: PID, 1: PID, 2: PID, 3: "fragrances|christian+dior|sauvage|EDT",
    4: None, 5: None, 6: "fragrances|lattafa|khamrah|-",
    7: "fragrances|christian+dior|elixir-sauvage|-", 8: PID, 9: None,
    10: PID, 11: PID, 12: "fragrances|christian+dior|sample-sauvage|EDP",
    13: "fragrances|christian+dior|plus-sauvage|EDP", 14: PID,
    15: "fragrances|armani+emporio+giorgio|stronger-you|EDT",
}


# ===========================================================================
# PIN rows (green at base; no behaviour change)
# ===========================================================================

def _py_files(*tops: str) -> list[Path]:
    out = []
    for top in tops:
        for p in sorted((ROOT / top).rglob("*.py")):
            if "__pycache__" in p.parts or p.resolve() == LEAF.resolve():
                continue
            out.append(p)
    return out


def test_s14_p01_no_importer_of_kb_service():
    offenders = []
    for path in _py_files("app", "scripts"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            hit = False
            if isinstance(node, ast.Import):
                hit = any("kb_service" in a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                hit = "kb_service" in (node.module or "") or any(a.name == "kb_service" for a in node.names)
            elif isinstance(node, ast.Attribute):
                hit = node.attr == "kb_service"
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                hit = "kb_service" in node.value and ("app." in node.value or "/" in node.value)
            if hit:
                offenders.append("%s:%d" % (path.relative_to(ROOT).as_posix(), getattr(node, "lineno", 0)))
    assert offenders == [], "kb_service gained an importer (S81-14 ships inert): %s" % offenders


def test_s14_p02_no_kb_relation_literal_outside_the_leaf():
    offenders = []
    for path in _py_files("app", "scripts"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in KB_RELATION_NAMES:
                offenders.append("%s:%d %r" % (path.relative_to(ROOT).as_posix(), node.lineno, node.value))
    assert offenders == [], "a kb_* relation is named outside kb_service.py: %s" % offenders


def test_s14_p03_012_clients_are_admin():
    """047 safety: every app / scripts call of .table() on a 012 table sits in a
    function that builds the service-role client (or uses self.client set from
    it) and never the user-scoped client."""
    rx = re.compile(r"\.table\(\s*[\"'](%s)[\"']\s*\)" % "|".join(TABLES_012))
    sites, offenders = [], []
    for path in _py_files("app", "scripts"):
        src = path.read_text(encoding="utf-8")
        if not rx.search(src):
            continue
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(src)
        fns = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        admin_self = "self.client = get_admin_supabase_client()" in src
        lines = src.splitlines()
        for m in rx.finditer(src):
            line = src.count("\n", 0, m.start()) + 1
            sites.append("%s:%d" % (rel, line))
            enclosing = [f for f in fns if f.lineno <= line <= (f.end_lineno or f.lineno)]
            segs = [ast.get_source_segment(src, f) or "" for f in enclosing]
            uses_admin = any("get_admin_supabase_client(" in seg for seg in segs) or (
                "self.client.table(" in lines[line - 1] and admin_self
            )
            if not enclosing or not uses_admin or any("get_user_supabase_client" in seg for seg in segs):
                offenders.append("%s:%d" % (rel, line))
    assert len(sites) >= 11, "positive control: the 11 measured 012 call sites, found %r" % sites
    assert offenders == [], "a 012-table client is not the service-role client: %s" % offenders


@pytest.mark.parametrize("gate", GATE_STATES)
@pytest.mark.parametrize("row,expected", SPINE_MATRIX, ids=[str(i) for i in range(len(SPINE_MATRIX))])
def test_s14_p04_spine_key_literals(prod_identity_env, gate, row, expected):
    prod_identity_env(gate)
    from app.services import spec_spine_service

    assert spec_spine_service.spine_key(*row) == expected


def _sqlfluff_limit() -> int:
    cfg = _read(SQLFLUFF_CFG)
    m = re.search(r"^\s*large_file_skip_byte_limit\s*=\s*(\d+)", cfg, re.MULTILINE)
    return int(m.group(1)) if m else 20000


def test_s14_p05_every_migration_is_linted_by_sqlfluff():
    """Read like tests/test_retro_w1_2c.py (0 = the skip is disabled)."""
    limit = _sqlfluff_limit()
    if limit == 0:
        return
    files = sorted(MIG.glob("*.sql")) + sorted(RB.glob("*.sql"))
    big = [(p.name, p.stat().st_size) for p in files if p.stat().st_size >= limit]
    assert big == [], "sqlfluff would silently SKIP %r (limit %d)" % (big, limit)


IDENTITY_NODES = {
    "tests/test_s75_fanout_identity.py": "f00cd11c5c29566f0f89140c20b0b4d2cee571fe8821203ed846a89b91f73e54",
    "tests/fixtures/s75_fanout_identity_digests.json": "56c378bf05d5135b597367cb8aec9920193dcefd703be047c821df9b3814dc56",
    "tests/test_w4_13_flag_off_ledger.py": "4c051821da78517c0f17a7feaabffa24eaa0d7445737b67d3ace88f544b59993",
    "tests/fixtures/w4_13_flag_off_ledger.json": "9fbf73e177365f352b9243009d9552b5626d7cf7e618adaad5a1856d66231f40",
}


def _lf_sha(rel: str) -> str:
    return hashlib.sha256(_read(ROOT / rel).encode("utf-8")).hexdigest()


@pytest.mark.parametrize("rel", sorted(IDENTITY_NODES))
def test_s14_p06_identity_nodes_untouched(rel):
    """The FY25 nine-digest node and the W4-13 ledger run unedited (LF sha at e1878dd8)."""
    assert _lf_sha(rel) == IDENTITY_NODES[rel], "%s changed: S81-14 edits no identity node" % rel


def test_s14_p07_043_fence_and_census_green():
    files = t043.real_forward_files()
    report = t043.fence_report(files)
    assert t043._all_gaps(report) == set(), "043 fence gaps: %r" % t043._all_gaps(report)
    users_tables = t043.fence_user_tables(files)
    assert set(users_tables) == set(t043.KNOWN_USER_TABLES), sorted(users_tables)
    assert not [t for t in users_tables if t.startswith("kb_")]


def test_s14_p08_flag_env_survives_the_dotenv_imports(prod_identity_env):
    prod_identity_env("true")
    importlib.import_module("app.main")
    importlib.import_module("app.services.extraction_service")
    assert os.environ.get("ENABLE_EXACT_PRICE_GATE") == "true"
    assert "ENABLE_NORMALIZE_WORDS_EMPTY_FIX" not in os.environ
    from app.services import price_service

    assert price_service.exact_gate_enabled() is True
    assert price_service.normalize_words_empty_fix_enabled() is False


# ===========================================================================
# RED rows: the migration text
# ===========================================================================

def test_s14_r01_files_exist_once():
    for p in FOUR_FILES:
        _require(p)
    assert sorted(p.name for p in MIG.glob("045_*.sql")) == ["045_kb_core.sql"]
    assert sorted(p.name for p in MIG.glob("047_*.sql")) == ["047_012_revoke.sql"]
    assert sorted(p.name for p in RB.glob("045_*.sql")) == ["045_kb_core.sql"]
    assert sorted(p.name for p in RB.glob("047_*.sql")) == ["047_012_revoke.sql"]
    assert not list(MIG.glob("039_*")), "039 is reserved"
    for n in ("046", "048", "049", "051"):
        assert not list(MIG.glob(n + "_*.sql")), "%s belongs to another unit (R-S14-12)" % n


@pytest.mark.parametrize("path", FOUR_FILES, ids=lambda p: p.parent.name + "/" + p.name)
def test_s14_r02_one_transaction(path):
    stmts = [s.lower() for s in _statements(_require(path))]
    assert stmts[0] == "begin" and stmts[-1] == "commit", (stmts[:1], stmts[-1:])
    assert stmts.count("begin") == 1 and stmts.count("commit") == 1


def test_s14_r03_045_objects():
    sql = _require(F045)
    code = _code(sql)
    assert sorted(_table_items(sql)) == sorted(KB_TABLE_NAMES)
    assert re.findall(r"CREATE\s+OR\s+REPLACE\s+VIEW\s+public\.(\w+)", code, re.I) == ["kb_offers_latest"]
    created = re.findall(r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.(\w+)", code, re.I)
    assert sorted(created) == sorted(KB_FUNCTIONS)
    for name, sig in KB_FUNCTIONS.items():
        assert _signature(_function_head(sql, name)) == sig, name
    triggers = re.findall(
        r"CREATE\s+OR\s+REPLACE\s+TRIGGER\s+(\w+)\s+BEFORE\s+UPDATE\s+ON\s+public\.(\w+)\s+"
        r"FOR\s+EACH\s+ROW\s+EXECUTE\s+FUNCTION\s+public\.kb_set_updated_at\(\)",
        code, re.I,
    )
    assert sorted(triggers) == sorted(
        (t + "_set_updated_at", t) for t in ("kb_merchants", "kb_products", "kb_variants")
    )
    assert len(re.findall(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\b", code, re.I)) == 3
    for kw in ("DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER\\s+TABLE\\s+public\\.(?!kb_)"):
        bad = [s for s in _statements(sql) if re.match(kw + r"\b", s, re.I)]
        assert bad == [], "045 top level must not %s: %r" % (kw, bad)


# The 045 columns: the full compact definition of every column, in order.
EXPECTED_COLUMNS = {'kb_merchants': ['host text PRIMARY KEY CHECK (host ~ '
                  "'^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$')",
                  "country text CHECK (country IS NULL OR country ~ '^[A-Z]{2,3}$')",
                  "currency_hint text CHECK (currency_hint IS NULL OR currency_hint ~ '^[A-Z]{3}$')",
                  'platform text CHECK (platform IS NULL OR char_length(platform) BETWEEN 1 AND 32)',
                  'platform_confidence text CHECK (platform_confidence IS NULL OR platform_confidence IN '
                  "('mechanism', 'probe', 'url', 'operator'))",
                  'adapter text CHECK (adapter IS NULL OR char_length(adapter) BETWEEN 1 AND 64)',
                  'search_template text CHECK (search_template IS NULL OR char_length(search_template) '
                  'BETWEEN 1 AND 1024)',
                  "registry jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(registry) = 'array')",
                  "robots jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(robots) = 'object')",
                  "politeness jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(politeness) = 'object')",
                  "health jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(health) = 'object')",
                  "challenge jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(challenge) = 'object')",
                  "tos jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(tos) = 'object')",
                  'deny boolean NOT NULL DEFAULT false',
                  "status text NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'live', "
                  "'blocked'))",
                  'blocked_reason text CHECK (blocked_reason IS NULL OR char_length(blocked_reason) BETWEEN '
                  '1 AND 64)',
                  "partner jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(partner) = 'object')",
                  'created_at timestamptz NOT NULL DEFAULT now()',
                  'updated_at timestamptz NOT NULL DEFAULT now()'],
 'kb_products': ['id text PRIMARY KEY CHECK (char_length(id) BETWEEN 14 AND 512 AND left(id, 11) = '
                 "'fragrances|')",
                 'brand text NOT NULL CHECK (char_length(brand) BETWEEN 1 AND 128)',
                 'line text CHECK (line IS NULL OR char_length(line) BETWEEN 1 AND 256)',
                 'name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 256)',
                 "concentration text CHECK (concentration IS NULL OR concentration IN ('Extrait', 'Parfum "
                 "Intense', 'EDP', 'EDT', 'EDC', 'Eau Fraiche', 'Parfum'))",
                 "audience text CHECK (audience IS NULL OR audience IN ('men', 'women', 'unisex'))",
                 "identity_confidence text NOT NULL CHECK (identity_confidence IN ('high', 'medium', 'low'))",
                 'created_at timestamptz NOT NULL DEFAULT now()',
                 'updated_at timestamptz NOT NULL DEFAULT now()'],
 'kb_variants': ['id text PRIMARY KEY',
                 'product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE',
                 "concentration text CHECK (concentration IS NULL OR concentration IN ('Extrait', 'Parfum "
                 "Intense', 'EDP', 'EDT', 'EDC', 'Eau Fraiche', 'Parfum'))",
                 'size_ml integer CHECK (size_ml IS NULL OR size_ml BETWEEN 1 AND 9999)',
                 'gtin text CHECK (gtin IS NULL OR public.kb_gtin_check_digit_ok(gtin))',
                 'sku text CHECK (sku IS NULL OR char_length(sku) BETWEEN 1 AND 128)',
                 'created_at timestamptz NOT NULL DEFAULT now()',
                 'updated_at timestamptz NOT NULL DEFAULT now()'],
 'kb_offers': ['id uuid PRIMARY KEY DEFAULT gen_random_uuid()',
               'variant_id text NOT NULL REFERENCES public.kb_variants (id) ON DELETE CASCADE',
               'merchant_id text NOT NULL REFERENCES public.kb_merchants (host) ON DELETE CASCADE',
               "market text NOT NULL CHECK (market ~ '^[A-Z]{2,3}$')",
               'amount numeric(14, 3) NOT NULL CHECK (amount > 0)',
               "observed_currency char(3) NOT NULL CHECK (observed_currency ~ '^[A-Z]{3}$')",
               "evidence_rung text NOT NULL CHECK (evidence_rung IN ('own_token', 'page_evidence', "
               "'expected_missing', 'platform_api', 'operator'))",
               'size_ml integer CHECK (size_ml IS NULL OR size_ml BETWEEN 1 AND 9999)',
               "list_vs_sale text NOT NULL DEFAULT 'unknown' CHECK (list_vs_sale IN ('list', 'sale', "
               "'unknown'))",
               'in_stock boolean',
               'first_seen timestamptz NOT NULL DEFAULT now()',
               'last_seen timestamptz NOT NULL DEFAULT now()',
               'captured_at timestamptz NOT NULL DEFAULT now()',
               'canonical_url text NOT NULL CHECK (canonical_url ~ '
               "'^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^?#[:space:]]*$' "
               "AND canonical_url !~ '^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]')"],
 'kb_images': ['id uuid PRIMARY KEY DEFAULT gen_random_uuid()',
               'product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE',
               'variant_id text REFERENCES public.kb_variants (id) ON DELETE CASCADE',
               'url text NOT NULL CHECK (url ~ '
               "'^https://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^#[:space:]]*$' "
               "AND url !~ '^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]' AND "
               'char_length(url) <= 2048)',
               'provenance_host text NOT NULL CHECK (provenance_host ~ '
               "'^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$' AND provenance_host !~ "
               "'(^|[.])(basenotes|fimgs|fragrantica|parfumo)[.]')",
               "source text NOT NULL CHECK (source IN ('retailer_jsonld', 'retailer_og', 'brand_site', "
               "'partner_feed', 'operator'))",
               'captured_at timestamptz NOT NULL DEFAULT now()'],
 'kb_specs': ['id uuid PRIMARY KEY DEFAULT gen_random_uuid()',
              'product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE',
              "field text NOT NULL CHECK (field ~ '^[a-z][a-z0-9_]{0,63}$')",
              "lang char(2) NOT NULL DEFAULT 'en' CHECK (lang IN ('en', 'ar'))",
              'value text NOT NULL CHECK (char_length(value) BETWEEN 1 AND 2000)',
              'source_url text CHECK (source_url IS NULL OR (source_url ~ '
              "'^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^#[:space:]]*$' "
              "AND source_url !~ '^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]' AND "
              'char_length(source_url) <= 2048))',
              'extractor text NOT NULL CHECK (char_length(extractor) BETWEEN 1 AND 64)',
              'model text CHECK (model IS NULL OR char_length(model) BETWEEN 1 AND 64)',
              'cited boolean NOT NULL DEFAULT false',
              'captured_at timestamptz NOT NULL DEFAULT now()'],
 'kb_reviews': ['id uuid PRIMARY KEY DEFAULT gen_random_uuid()',
                'product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE',
                "source text NOT NULL CHECK (source IN ('retailer_jsonld', 'retailer_widget', 'brand_site', "
                "'marketplace'))",
                'aggregate_rating numeric(3, 2) CHECK (aggregate_rating IS NULL OR aggregate_rating BETWEEN '
                '0 AND 5)',
                'review_count integer CHECK (review_count IS NULL OR review_count >= 0)',
                'source_url text NOT NULL CHECK (source_url ~ '
                "'^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^#[:space:]]*$' "
                "AND source_url !~ '^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]' AND "
                'char_length(source_url) <= 2048)',
                'captured_at timestamptz NOT NULL DEFAULT now()'],
 'kb_gaps': ['id uuid PRIMARY KEY DEFAULT gen_random_uuid()',
             'product_key text NOT NULL CHECK (char_length(product_key) BETWEEN 14 AND 520)',
             "field text NOT NULL CHECK (field ~ '^[a-z][a-z0-9_]{0,63}$')",
             'demand_count integer NOT NULL DEFAULT 1 CHECK (demand_count >= 0)',
             'first_seen timestamptz NOT NULL DEFAULT now()',
             'last_seen timestamptz NOT NULL DEFAULT now()',
             "state text NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'queued', 'needs_operator', "
             "'licence', 'closed'))",
             'source_hint text CHECK (source_hint IS NULL OR (char_length(source_hint) BETWEEN 1 AND 256 AND '
             "(source_hint ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$' OR "
             'source_hint ~ '
             "'^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^?#[:space:]]*$') "
             "AND source_hint !~ '(^|[.])(basenotes|fimgs|fragrantica|parfumo)[.]' AND source_hint !~ "
             "'^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]'))"],
 'kb_feedback': ['id uuid PRIMARY KEY DEFAULT gen_random_uuid()',
                 'compare_request_id uuid NOT NULL',
                 'product_id text REFERENCES public.kb_products (id) ON DELETE CASCADE',
                 "field text NOT NULL CHECK (field ~ '^[a-z][a-z0-9_]{0,63}$')",
                 "verdict text NOT NULL CHECK (verdict IN ('correct', 'wrong', 'unsure'))",
                 "device_key text CHECK (device_key IS NULL OR device_key ~ '^[a-f0-9]{64}$')",
                 'created_at timestamptz NOT NULL DEFAULT now()'],
 'kb_coverage_daily': ['day date NOT NULL',
                       "metric text NOT NULL CHECK (metric ~ '^[a-z][a-z0-9_.:-]{0,127}$')",
                       'value numeric NOT NULL',
                       'n integer NOT NULL CHECK (n >= 0)']}
# (name, type, not_null, default) per column (review C10).
EXPECTED_COLUMN_TUPLES = {'kb_merchants': [('host', 'text', True, None),
                  ('country', 'text', False, None),
                  ('currency_hint', 'text', False, None),
                  ('platform', 'text', False, None),
                  ('platform_confidence', 'text', False, None),
                  ('adapter', 'text', False, None),
                  ('search_template', 'text', False, None),
                  ('registry', 'jsonb', True, "'[]'::jsonb"),
                  ('robots', 'jsonb', True, "'{}'::jsonb"),
                  ('politeness', 'jsonb', True, "'{}'::jsonb"),
                  ('health', 'jsonb', True, "'{}'::jsonb"),
                  ('challenge', 'jsonb', True, "'{}'::jsonb"),
                  ('tos', 'jsonb', True, "'{}'::jsonb"),
                  ('deny', 'boolean', True, 'false'),
                  ('status', 'text', True, "'candidate'"),
                  ('blocked_reason', 'text', False, None),
                  ('partner', 'jsonb', True, "'{}'::jsonb"),
                  ('created_at', 'timestamptz', True, 'now()'),
                  ('updated_at', 'timestamptz', True, 'now()')],
 'kb_products': [('id', 'text', True, None),
                 ('brand', 'text', True, None),
                 ('line', 'text', False, None),
                 ('name', 'text', True, None),
                 ('concentration', 'text', False, None),
                 ('audience', 'text', False, None),
                 ('identity_confidence', 'text', True, None),
                 ('created_at', 'timestamptz', True, 'now()'),
                 ('updated_at', 'timestamptz', True, 'now()')],
 'kb_variants': [('id', 'text', True, None),
                 ('product_id', 'text', True, None),
                 ('concentration', 'text', False, None),
                 ('size_ml', 'integer', False, None),
                 ('gtin', 'text', False, None),
                 ('sku', 'text', False, None),
                 ('created_at', 'timestamptz', True, 'now()'),
                 ('updated_at', 'timestamptz', True, 'now()')],
 'kb_offers': [('id', 'uuid', True, 'gen_random_uuid()'),
               ('variant_id', 'text', True, None),
               ('merchant_id', 'text', True, None),
               ('market', 'text', True, None),
               ('amount', 'numeric(14, 3)', True, None),
               ('observed_currency', 'char(3)', True, None),
               ('evidence_rung', 'text', True, None),
               ('size_ml', 'integer', False, None),
               ('list_vs_sale', 'text', True, "'unknown'"),
               ('in_stock', 'boolean', False, None),
               ('first_seen', 'timestamptz', True, 'now()'),
               ('last_seen', 'timestamptz', True, 'now()'),
               ('captured_at', 'timestamptz', True, 'now()'),
               ('canonical_url', 'text', True, None)],
 'kb_images': [('id', 'uuid', True, 'gen_random_uuid()'),
               ('product_id', 'text', True, None),
               ('variant_id', 'text', False, None),
               ('url', 'text', True, None),
               ('provenance_host', 'text', True, None),
               ('source', 'text', True, None),
               ('captured_at', 'timestamptz', True, 'now()')],
 'kb_specs': [('id', 'uuid', True, 'gen_random_uuid()'),
              ('product_id', 'text', True, None),
              ('field', 'text', True, None),
              ('lang', 'char(2)', True, "'en'"),
              ('value', 'text', True, None),
              ('source_url', 'text', False, None),
              ('extractor', 'text', True, None),
              ('model', 'text', False, None),
              ('cited', 'boolean', True, 'false'),
              ('captured_at', 'timestamptz', True, 'now()')],
 'kb_reviews': [('id', 'uuid', True, 'gen_random_uuid()'),
                ('product_id', 'text', True, None),
                ('source', 'text', True, None),
                ('aggregate_rating', 'numeric(3, 2)', False, None),
                ('review_count', 'integer', False, None),
                ('source_url', 'text', True, None),
                ('captured_at', 'timestamptz', True, 'now()')],
 'kb_gaps': [('id', 'uuid', True, 'gen_random_uuid()'),
             ('product_key', 'text', True, None),
             ('field', 'text', True, None),
             ('demand_count', 'integer', True, '1'),
             ('first_seen', 'timestamptz', True, 'now()'),
             ('last_seen', 'timestamptz', True, 'now()'),
             ('state', 'text', True, "'open'"),
             ('source_hint', 'text', False, None)],
 'kb_feedback': [('id', 'uuid', True, 'gen_random_uuid()'),
                 ('compare_request_id', 'uuid', True, None),
                 ('product_id', 'text', False, None),
                 ('field', 'text', True, None),
                 ('verdict', 'text', True, None),
                 ('device_key', 'text', False, None),
                 ('created_at', 'timestamptz', True, 'now()')],
 'kb_coverage_daily': [('day', 'date', True, None),
                       ('metric', 'text', True, None),
                       ('value', 'numeric', True, None),
                       ('n', 'integer', True, None)]}
# Table-level constraints by name, plus the primary key items (review C10).
EXPECTED_CONSTRAINTS = {'kb_merchants': ["CONSTRAINT kb_merchants_host_top_label_letter CHECK (host ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)')",
                  "CONSTRAINT kb_merchants_deny_is_blocked CHECK (NOT deny OR status = 'blocked')",
                  "CONSTRAINT kb_merchants_blocked_has_reason CHECK (status <> 'blocked' OR blocked_reason "
                  'IS NOT NULL)'],
 'kb_products': [],
 'kb_variants': ['CONSTRAINT kb_variants_id_extends_product CHECK (left(id, char_length(product_id) + 1) = '
                 "product_id || '|' AND char_length(id) BETWEEN char_length(product_id) + 2 AND "
                 'char_length(product_id) + 5)'],
 'kb_offers': ["CONSTRAINT kb_offers_url_top_label_letter CHECK (canonical_url ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)')",
               'CONSTRAINT kb_offers_seen_order CHECK (first_seen <= last_seen)',
               "CONSTRAINT kb_offers_url_on_merchant CHECK (split_part(split_part(canonical_url, '://', 2), "
               "'/', 1) = merchant_id OR right(split_part(split_part(canonical_url, '://', 2), '/', 1), "
               "char_length(merchant_id) + 1) = '.' || merchant_id)",
               'CONSTRAINT kb_offers_observation UNIQUE (variant_id, merchant_id, market, observed_currency, '
               'amount, list_vs_sale)'],
 'kb_images': ["CONSTRAINT kb_images_url_top_label_letter CHECK (url ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)')",
               "CONSTRAINT kb_images_provenance_top_label_letter CHECK (provenance_host ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)')",
               'CONSTRAINT kb_images_product_url UNIQUE (product_id, url)'],
 'kb_specs': ["CONSTRAINT kb_specs_source_top_label_letter CHECK (source_url IS NULL OR source_url ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)')",
              'CONSTRAINT kb_specs_cited_has_source CHECK (NOT cited OR source_url IS NOT NULL)',
              'CONSTRAINT kb_specs_product_field_lang UNIQUE (product_id, field, lang)'],
 'kb_reviews': ["CONSTRAINT kb_reviews_source_top_label_letter CHECK (source_url ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)')",
                'CONSTRAINT kb_reviews_has_signal CHECK (aggregate_rating IS NOT NULL OR review_count IS NOT '
                'NULL)',
                'CONSTRAINT kb_reviews_product_url UNIQUE (product_id, source_url)'],
 'kb_gaps': ["CONSTRAINT kb_gaps_hint_top_label_letter CHECK (source_hint IS NULL OR source_hint ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)')",
             'CONSTRAINT kb_gaps_seen_order CHECK (first_seen <= last_seen)',
             'CONSTRAINT kb_gaps_key_field UNIQUE (product_key, field)'],
 'kb_feedback': [],
 'kb_coverage_daily': ['PRIMARY KEY (day, metric)']}


@pytest.mark.parametrize("table", KB_TABLE_NAMES)
def test_s14_r04_columns(table):
    sql = _require(F045)
    cols = _columns(sql, table)
    kb = _kb()
    assert [c.split()[0] for c in cols] == list(_attr(kb, "KB_COLUMNS")[table])
    assert [_col_tuple(c) for c in cols] == EXPECTED_COLUMN_TUPLES[table]
    assert cols == EXPECTED_COLUMNS[table]


@pytest.mark.parametrize("table", KB_TABLE_NAMES)
def test_s14_r04b_table_constraints(table):
    sql = _require(F045)
    assert _constraints(sql, table) == EXPECTED_CONSTRAINTS[table]


@pytest.mark.parametrize("rel", KB_TABLE_NAMES + ("kb_offers_latest",))
def test_s14_r05_service_role_only(rel):
    sql = _require(F045)
    code = _compact(_code(sql)).lower()
    if rel != "kb_offers_latest":
        assert "alter table public.%s enable row level security;" % rel in code
    assert "create policy" not in code
    assert code.count("revoke all on table public.%s from public, anon, authenticated, service_role;" % rel) == 1
    grants = re.findall(r"grant ([a-z, ]+) on table public\.%s to ([a-z_, ]+);" % rel, code)
    want = "select" if rel == "kb_offers_latest" else "select, insert, update, delete"
    assert grants == [(want, "service_role")], grants


@pytest.mark.parametrize("name", sorted(KB_FUNCTIONS))
def test_s14_r06_functions(name):
    sql = _require(F045)
    head = _compact(_function_head(sql, name)).lower()
    assert "security invoker" in head and "security definer" not in head
    assert "set search_path to 'public'" in head
    sig = ", ".join(KB_FUNCTIONS[name])
    code = _compact(_code(sql)).lower()
    # F1-9 (fix round 1): the 050 form, service_role included, then the one GRANT EXECUTE.
    assert code.count(
        "revoke all on function public.%s(%s) from public, anon, authenticated, service_role;" % (name, sig)
    ) == 1
    grants = re.findall(r"grant execute on function public\.%s\(([a-z, ]*)\) to ([a-z_, ]+);" % name, code)
    assert grants == [(sig, "service_role")], grants
    assert _sql.security_definer_creates(sql) == []
    whole = _compact(_no_comments(sql)).lower()
    assert not re.search(r"\bgrant\b[^;]*\bto\b[^;]*\b(anon|authenticated|public)\b", whole)


EXPECTED_FKS = sorted([
    ("kb_variants", "product_id", "public.kb_products", "id"),
    ("kb_offers", "variant_id", "public.kb_variants", "id"),
    ("kb_offers", "merchant_id", "public.kb_merchants", "host"),
    ("kb_images", "product_id", "public.kb_products", "id"),
    ("kb_images", "variant_id", "public.kb_variants", "id"),
    ("kb_specs", "product_id", "public.kb_products", "id"),
    ("kb_reviews", "product_id", "public.kb_products", "id"),
    ("kb_feedback", "product_id", "public.kb_products", "id"),
])


def test_s14_r07_fks():
    sql = _require(F045)
    found = []
    for table in KB_TABLE_NAMES:
        for col in _columns(sql, table):
            m = re.search(r"REFERENCES\s+(public\.\w+)\s*\((\w+)\)(.*)$", col, re.I)
            if m:
                assert m.group(3).strip().upper().startswith("ON DELETE CASCADE"), col
                found.append((table, col.split()[0], m.group(1), m.group(2)))
    assert sorted(found) == EXPECTED_FKS
    low = _no_comments(sql).lower()
    assert not re.search(r"references\s+(\"?(public|auth)\"?\s*\.\s*)?\"?users\b", low)
    assert "foreign key" not in low


def test_s14_r08_no_user_column_census():
    sql = _require(F045)
    names = [c.split()[0] for t in KB_TABLE_NAMES for c in _columns(sql, t)]
    assert names, "no columns parsed"
    hits = [n for n in names if t043.USER_REF_ID_RX.search(n) or t043.PERSONAL_RX.search(n)]
    assert hits == [], "045 column(s) the 043 fence would treat as personal: %r" % hits
    for bad in ("gender_marker", "device_id", "email", "fingerprint", "ip", "user_id"):
        assert bad not in names
    files = t043.real_forward_files()
    assert "045_kb_core.sql" in [n for n, _t in files], "the fence must see 045"
    assert t043._all_gaps(t043.fence_report(files)) == set()
    assert not [t for t in t043.fence_user_tables(files) if t.startswith("kb_")]


BELTED = [
    ("kb_offers", "canonical_url", "url"),
    ("kb_images", "url", "url"),
    ("kb_images", "provenance_host", "host"),
    ("kb_specs", "source_url", "url"),
    ("kb_reviews", "source_url", "url"),
    ("kb_gaps", "source_hint", "host"),
    ("kb_gaps", "source_hint", "url"),
]


def _col_item(sql: str, table: str, col: str) -> str:
    for c in _columns(sql, table):
        if c.split()[0] == col:
            return c
    raise AssertionError("045 %s has no column %s" % (table, col))


@pytest.mark.parametrize("table,col,kind", BELTED, ids=["%s.%s.%s" % b for b in BELTED])
def test_s14_r09_deny_label_belts(table, col, kind):
    """R-S14-6: one deny rule (kb_source_allowed); the SQL label CHECKs are belts
    whose label group is derived verbatim from deny_hosts.DENY_LABELS."""
    sql = _require(F045)
    item = _col_item(sql, table, col)
    belt = _host_belt() if kind == "host" else _url_belt()
    assert "!~ '%s'" % belt in item, "%s.%s lacks the %s belt %r" % (table, col, kind, belt)
    rx = _py(belt)
    if kind == "url":
        for bad in ("https://fr.fragrantica.com/x", "https://fimgs.net/a.jpg", "https://parfumo.de/p",
                    "http://www.basenotes.net/x"):
            assert rx.search(bad), bad
        for ok in ("https://shop.example/p", "https://notfragrantica.example/p"):
            assert not rx.search(ok), ok
    else:
        for bad in ("fragrantica.com", "fr.fragrantica.com", "fimgs.net", "parfumo.shop.example"):
            assert rx.search(bad), bad
        for ok in ("shop.example", "notfragrantica.example"):
            assert not rx.search(ok), ok
    kb = _kb()
    assert _attr(kb, "kb_host_deny_regex")() == _host_belt()
    assert _attr(kb, "kb_url_deny_regex")() == _url_belt()


def test_s14_r09b_merchants_carry_no_deny_check():
    """R-S14-2: deny hosts are STORED (deny = true, status blocked); no label check."""
    sql = _require(F045)
    body = " ".join(_table_items(sql)["kb_merchants"])
    for label in _labels():
        assert label not in body, "kb_merchants must not refuse %r by CHECK" % label
    assert "!~" not in body


def test_s14_r10_reviews_source_and_no_text():
    sql = _require(F045)
    item = _col_item(sql, "kb_reviews", "source")
    vals = re.findall(r"'([^']*)'", _check_text(item))
    assert vals == ["retailer_jsonld", "retailer_widget", "brand_site", "marketplace"]
    for v in vals:
        for bad in _labels() + ["google", "serper", "youtube"]:
            assert bad not in v
    cols = [c.split()[0] for c in _columns(sql, "kb_reviews")]
    assert not [c for c in cols if re.search(r"snippet|text|body|quote", c)]


@pytest.mark.parametrize("table", ["kb_products", "kb_variants"])
def test_s14_r11_concentration_enum(table):
    sql = _require(F045)
    from app.services import price_service

    item = _col_item(sql, table, "concentration")
    vals = re.findall(r"'([^']*)'", _check_text(item))
    assert vals == [lab for _p, lab in price_service._CONCENTRATION_PATTERNS]
    assert list(_attr(_kb(), "kb_concentrations")()) == vals


EXPECTED_INDEXES = {'idx_kb_merchants_status': 'CREATE INDEX IF NOT EXISTS idx_kb_merchants_status ON public.kb_merchants '
                            '(status)',
 'idx_kb_variants_product': 'CREATE INDEX IF NOT EXISTS idx_kb_variants_product ON public.kb_variants '
                            '(product_id)',
 'idx_kb_variants_gtin': 'CREATE INDEX IF NOT EXISTS idx_kb_variants_gtin ON public.kb_variants (gtin) WHERE '
                         'gtin IS NOT NULL',
 'idx_kb_offers_latest': 'CREATE INDEX IF NOT EXISTS idx_kb_offers_latest ON public.kb_offers (variant_id, '
                         "merchant_id, market, observed_currency, last_seen DESC, (list_vs_sale = 'sale') DESC, "
                         'captured_at DESC, id DESC)',
 'idx_kb_offers_merchant': 'CREATE INDEX IF NOT EXISTS idx_kb_offers_merchant ON public.kb_offers '
                           '(merchant_id)',
 'idx_kb_images_product': 'CREATE INDEX IF NOT EXISTS idx_kb_images_product ON public.kb_images (product_id)',
 'idx_kb_images_variant': 'CREATE INDEX IF NOT EXISTS idx_kb_images_variant ON public.kb_images (variant_id) '
                          'WHERE variant_id IS NOT NULL',
 'idx_kb_reviews_product': 'CREATE INDEX IF NOT EXISTS idx_kb_reviews_product ON public.kb_reviews '
                           '(product_id)',
 'idx_kb_gaps_open_demand': 'CREATE INDEX IF NOT EXISTS idx_kb_gaps_open_demand ON public.kb_gaps '
                            "(demand_count DESC, last_seen DESC) WHERE state = 'open'",
 'idx_kb_feedback_device_key': 'CREATE INDEX IF NOT EXISTS idx_kb_feedback_device_key ON public.kb_feedback '
                               '(device_key) WHERE device_key IS NOT NULL',
 'idx_kb_feedback_product': 'CREATE INDEX IF NOT EXISTS idx_kb_feedback_product ON public.kb_feedback '
                            '(product_id) WHERE product_id IS NOT NULL',
 'idx_kb_feedback_created': 'CREATE INDEX IF NOT EXISTS idx_kb_feedback_created ON public.kb_feedback '
                            '(created_at)',
 'idx_kb_feedback_request': 'CREATE INDEX IF NOT EXISTS idx_kb_feedback_request ON public.kb_feedback '
                            '(compare_request_id)',
 'uq_kb_feedback_one_vote': 'CREATE UNIQUE INDEX IF NOT EXISTS uq_kb_feedback_one_vote ON public.kb_feedback '
                            "(device_key, compare_request_id, field, coalesce(product_id, '')) WHERE "
                            'device_key IS NOT NULL'}


def test_s14_r12_indexes():
    sql = _require(F045)
    stmts = [s for s in _statements(sql) if re.match(r"CREATE\s+(UNIQUE\s+)?INDEX\b", s, re.I)]
    got = {re.search(r"EXISTS\s+(\w+)", s).group(1): s for s in stmts}
    assert got == EXPECTED_INDEXES
    for s in stmts:
        wm = re.search(r"\bWHERE\b(.*)$", s, re.I)
        if wm:
            assert timm._volatile_hits(wm.group(1)) == [], s
    for _stmt, pred in timm._index_predicates(_no_comments(sql)):
        assert timm._volatile_hits(pred) == []


# F1-4 / F2-1 (fix rounds 1 and 2): among the rows last seen at the same instant the sale wins,
# then the newest capture (the sale key sits BEFORE captured_at).
OFFER_ORDER = "o.last_seen DESC, (o.list_vs_sale = 'sale') DESC, o.captured_at DESC, o.id DESC"
OFFER_PARTITION = "o.variant_id, o.merchant_id, o.market, o.observed_currency"


def test_s14_r13_view():
    """R-S14-1 (a)(b): latest per (variant, merchant, market, currency) by last_seen."""
    sql = _require(F045)
    views = [s for s in _statements(sql) if s.startswith("CREATE OR REPLACE VIEW public.kb_offers_latest ")]
    assert len(views) == 1, "no kb_offers_latest view"
    view = views[0]
    assert "WITH (security_invoker = true) AS" in view
    assert "SELECT DISTINCT ON (%s)" % OFFER_PARTITION in view
    assert view.endswith(
        "ORDER BY o.variant_id ASC, o.merchant_id ASC, o.market ASC, o.observed_currency ASC, "
        + OFFER_ORDER
    ), view[-200:]
    sel = re.search(r"DISTINCT ON \([^)]*\) (.*?) FROM public\.kb_offers AS o", view).group(1)
    cols = [c.strip() for c in sel.split(",")]
    assert cols == ["o." + c for c in EXPECTED_COLUMN_TUPLES_NAMES("kb_offers")]


def EXPECTED_COLUMN_TUPLES_NAMES(table):  # noqa: N802 - reads the pinned literal
    return [t[0] for t in EXPECTED_COLUMN_TUPLES[table]]


def test_s14_r14_card():
    """R-S14-1 (c) + R-S14-13: the card reads kb_offers directly with DISTINCT ON
    over the product's variant ids (never the view) and the language's specs."""
    sql = _require(F045)
    head = _compact(_function_head(sql, "kb_product_card"))
    assert "kb_product_card(p_product_id text, p_lang text DEFAULT 'en')" in head
    assert "LANGUAGE sql" in head and "STABLE" in head
    body = _compact(_function_body(sql, "kb_product_card"))
    keys = re.findall(r"'(\w+)', (?:to_jsonb|coalesce|\()", body)
    assert keys[:6] == ["product", "variants", "offers", "images", "specs", "rating"], keys
    assert "kb_offers_latest" not in body
    assert "SELECT DISTINCT ON (%s) o.* FROM public.kb_offers AS o" % OFFER_PARTITION in body
    assert "WHERE o.variant_id IN (SELECT v2.id FROM public.kb_variants AS v2 WHERE v2.product_id = p.id)" in body
    assert "ORDER BY %s, %s" % (OFFER_PARTITION, OFFER_ORDER) in body
    assert "WHERE s0.product_id = p.id AND s0.cited AND s0.lang IN (p_lang, 'en')" in body
    assert "ORDER BY s0.field, (s0.lang = p_lang) DESC" in body
    assert body.rstrip().endswith("FROM public.kb_products AS p WHERE p.id = p_product_id")
    first_do = _compact(_no_comments(sql)).split("$$")[1]
    assert "current_setting('server_version_num')::int < 150000" in first_do


def test_s14_r15_prune_offers():
    """R-S14-1 + review C4: the whole conjunction and the bounds, as compact text."""
    sql = _require(F045)
    body = _compact(_function_body(sql, "kb_prune_offers"))
    assert (
        "IF p_max_age_days IS NULL OR p_max_age_days < 1 OR p_max_age_days > 3650 "
        "OR p_keep_per_merchant IS NULL OR p_keep_per_merchant < 1 OR p_keep_per_merchant > 1000 THEN "
        "RAISE EXCEPTION 'kb_prune_offers: bounds out of range'; END IF;"
    ) in body
    assert (
        "row_number() OVER (PARTITION BY %s ORDER BY %s) AS rn" % (OFFER_PARTITION, OFFER_ORDER)
    ) in body
    assert (
        "DELETE FROM public.kb_offers AS d USING ranked AS r WHERE d.id = r.id "
        "AND r.rn > p_keep_per_merchant "
        "AND r.last_seen < now() - make_interval(days => p_max_age_days);"
    ) in body
    assert "GET DIAGNOSTICS v_deleted = ROW_COUNT; RETURN v_deleted;" in body
    assert "captured_at <" not in body


def test_s14_r15b_prune_feedback():
    """R-S14-4: the 365-day TTL prune S81-22's nightly job calls."""
    sql = _require(F045)
    body = _compact(_function_body(sql, "kb_prune_feedback"))
    assert (
        "IF p_days IS NULL OR p_days < 1 OR p_days > 3650 THEN "
        "RAISE EXCEPTION 'kb_prune_feedback: bounds out of range'; END IF;"
    ) in body
    assert (
        "DELETE FROM public.kb_feedback AS f WHERE f.created_at < now() - make_interval(days => p_days);"
    ) in body
    assert "GET DIAGNOSTICS v_deleted = ROW_COUNT; RETURN v_deleted;" in body


GTIN_BODY = (
    "SELECT CASE WHEN p_gtin !~ '^([0-9]{8}|[0-9]{12,14})$' THEN false ELSE (SELECT (10 - (sum("
    "substr(p_gtin, i, 1)::int * CASE WHEN (length(p_gtin) - i) % 2 = 1 THEN 3 ELSE 1 END) % 10)) % 10 "
    "FROM generate_series(1, length(p_gtin) - 1) AS i) = substr(p_gtin, length(p_gtin), 1)::int END"
)


def test_s14_r15c_gtin_sql_body():
    """Review C11: the POSTCHECK executes it live; offline the body is pinned."""
    sql = _require(F045)
    assert _compact(_function_body(sql, "kb_gtin_check_digit_ok")) == GTIN_BODY
    head = _compact(_function_head(sql, "kb_gtin_check_digit_ok"))
    for kw in ("LANGUAGE sql", "IMMUTABLE", "STRICT"):
        assert kw in head


def test_s14_r15d_updated_at_trigger_function():
    """R-S14-2: one SECURITY INVOKER trigger function keeps updated_at current."""
    sql = _require(F045)
    assert _compact(_function_body(sql, "kb_set_updated_at")) == "BEGIN NEW.updated_at := now(); RETURN NEW; END"
    head = _compact(_function_head(sql, "kb_set_updated_at"))
    assert "RETURNS trigger LANGUAGE plpgsql" in head


ROLLBACK_045 = [
    "BEGIN",
    "DROP FUNCTION IF EXISTS public.kb_product_card(text, text)",
    "DROP FUNCTION IF EXISTS public.kb_prune_feedback(integer)",
    "DROP FUNCTION IF EXISTS public.kb_prune_offers(integer, integer)",
    "DROP VIEW IF EXISTS public.kb_offers_latest",
] + ["DROP TABLE IF EXISTS public.%s" % t for t in (
    "kb_feedback", "kb_gaps", "kb_reviews", "kb_specs", "kb_images", "kb_offers",
    "kb_variants", "kb_products", "kb_merchants", "kb_coverage_daily",
)] + [
    "DROP FUNCTION IF EXISTS public.kb_set_updated_at()",
    "DROP FUNCTION IF EXISTS public.kb_gtin_check_digit_ok(text)",
    "COMMIT",
]


def _policies_012() -> list[tuple[str, str]]:
    return re.findall(r"CREATE POLICY (\w+) ON (\w+)", _code(_read(F012)))


def test_s14_r16_rollbacks():
    assert _statements(_require(R045)) == ROLLBACK_045
    stmts = _statements(_require(R047))
    assert stmts[0] == "BEGIN" and stmts[-1] == "COMMIT"
    pols = [s for s in stmts[1:-1] if s.startswith("CREATE POLICY")]
    assert [re.match(r"CREATE POLICY (\w+) ON public\.(\w+)", s).groups() for s in pols] == _policies_012()
    rest = [s for s in stmts[1:-1] if not s.startswith("CREATE POLICY")]
    assert rest == [
        "GRANT ALL ON TABLE public.product_specs, public.product_prices, public.product_reviews "
        "TO anon, authenticated"
    ]
    assert len(_policies_012()) == 8


def test_s14_r17_047_statements():
    stmts = _statements(_require(F047))[1:-1]
    drops = [re.match(r"DROP POLICY IF EXISTS (\w+) ON public\.(\w+)$", s) for s in stmts if s.startswith("DROP")]
    assert all(drops), stmts
    assert sorted(m.groups() for m in drops) == sorted(_policies_012())
    rest = [s for s in stmts if not s.startswith("DROP")]
    want = (
        ["ALTER TABLE public.%s ENABLE ROW LEVEL SECURITY" % t for t in TABLES_012]
        + ["REVOKE ALL ON TABLE public.%s FROM PUBLIC, anon, authenticated" % t for t in TABLES_012]
        + ["GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%s TO service_role" % t for t in TABLES_012]
    )
    assert rest == want


def test_s14_r18_policy_census_closed():
    live: set[tuple[str, str]] = set()
    for path in sorted(MIG.glob("*.sql")):
        for s in _statements(_read(path)):
            m = re.match(r"CREATE POLICY (\w+) ON (?:public\.)?(\w+)", s, re.I)
            if m:
                live.add(m.groups())
            m = re.match(r"DROP POLICY IF EXISTS (\w+) ON (?:public\.)?(\w+)", s, re.I)
            if m:
                live.discard(m.groups())
    _require(F047)
    left = sorted(p for p in live if p[1] in TABLES_012)
    assert left == [], "policies still open on the 012 tables: %r" % left


def test_s14_r19_headers():
    h45 = " ".join(_sql.comment_lines(_require(F045)).split()).lower()
    for phrase in (
        "s81-14", "rollback/045_kb_core.sql", "service role", "postgresql 15", "before",
        "pseudonymous", "hmac-sha256", "device_key_pepper", "not a user id", "s81-22",
        "kb_prune_feedback(365)", "ops-only",
        "host, registry, status, deny, blocked_reason and partner only",
        "last_seen, in_stock, evidence_rung and canonical_url only",
        "last_seen desc, captured_at desc, id desc",
    ):
        assert phrase in h45, "045 header lacks %r" % phrase
    h47 = " ".join(_sql.comment_lines(_require(F047)).split()).lower()
    for phrase in ("product_data_service", "rollback/047_012_revoke.sql"):
        assert phrase in h47, phrase
    assert "pg_policies" in h47 or "precheck" in h47


def test_s14_r20_sqlfluff_lints_every_file():
    """R-S14-12: 045 exceeds sqlfluff's 20,000-byte skip; the repo disables the skip."""
    assert _sqlfluff_limit() == 0, ".sqlfluff must set large_file_skip_byte_limit = 0"
    cfg = _read(SQLFLUFF_CFG)
    sect = cfg.split("[sqlfluff]", 1)[1].split("\n[", 1)[0]
    assert re.search(r"^large_file_skip_byte_limit\s*=\s*0\s*$", sect, re.M)


@pytest.mark.parametrize("path", FOUR_FILES, ids=lambda p: p.parent.name + "/" + p.name)
def test_s14_r20b_ascii(path):
    _require(path)
    raw = path.read_bytes()
    assert sum(1 for b in raw if b > 127) == 0
    assert not re.search(rb"[0-9]{8}", raw), "no digit run of 8 or more (the added-line sweep)"


# ===========================================================================
# RED rows: the leaf
# ===========================================================================

STDLIB_OK = {"__future__", "re", "ipaddress", "json", "math", "uuid", "datetime", "decimal", "typing", "urllib.parse"}
# F1-3 (fix round 1): source_router is imported INSIDE the registry validator only (r21b).
APP_OK = {"deny_hosts", "price_service", "result_gate", "spec_spine_service", "text_sanitize", "source_router"}


def test_s14_r21_leaf_pure():
    _kb()
    tree = ast.parse(LEAF.read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bad += [a.name for a in node.names if a.name not in STDLIB_OK]
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "app.services":
                bad += [a.name for a in node.names if a.name not in APP_OK or not (a.asname or "").startswith("_")]
            elif mod not in STDLIB_OK:
                bad.append(mod)
        elif isinstance(node, ast.Name) and node.id in {"open", "print", "eval", "exec", "__import__"}:
            bad.append(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in {
            "getenv", "environ", "now", "utcnow", "today", "time", "monotonic", "sleep",
        }:
            bad.append(node.attr)
        elif isinstance(node, ast.Name) and node.id in {
            "os", "logging", "asyncio", "socket", "supabase", "httpx", "requests", "time",
        }:
            bad.append(node.id)
    assert bad == [], "kb_service must stay a pure, flag-free, no-I/O leaf: %r" % bad


@pytest.mark.parametrize("gate", GATE_STATES)
@pytest.mark.parametrize("idx", range(len(SPINE_MATRIX)))
def test_s14_r22_kb_product_id(prod_identity_env, gate, idx):
    prod_identity_env(gate)
    kb = _kb()
    fn = _attr(kb, "kb_product_id")
    row, key = SPINE_MATRIX[idx]
    assert fn(*row) == PRODUCT_IDS[idx]
    if PRODUCT_IDS[idx] is not None:
        assert PRODUCT_IDS[idx] == key.rsplit("|", 1)[0]


def test_s14_r22b_kb_product_id_rules(prod_identity_env, monkeypatch):
    prod_identity_env(None)
    kb = _kb()
    fn = _attr(kb, "kb_product_id")
    assert fn("Dior", "Sauvage EDP 100ml") == fn("Dior", "Sauvage EDP 50 ml") == fn("Christian Dior", "Sauvage EDP")
    assert fn("Dior", "Sauvage EDP") != fn("Dior", "Sauvage EDT")
    for junk in [(None, "x"), ("x", None), (3, "x"), (b"Dior", "Sauvage"), ("Dior", "Sauvage", 3)]:
        assert fn(*junk) is None, junk
    from app.services import spec_spine_service

    calls = []

    def rec(brand, name, variant=None, category="fragrances"):
        calls.append((brand, name, variant))
        return "fragrances|a|b|EDP|9"

    monkeypatch.setattr(spec_spine_service, "spine_key", rec)
    assert fn("Acme", "Bottle", "Elixir") == "fragrances|a|b|EDP"
    assert calls == [("Acme", "Bottle", "Elixir")], calls
    calls.clear()
    assert fn("Unknown", "Unknown Product") is None
    assert calls == [], "a placeholder identity must not mint an id (R-S14-9)"
    monkeypatch.setattr(spec_spine_service, "spine_key", lambda *a, **k: "fragrances|a||EDP|9")
    assert fn("Acme", "Bottle") is None
    monkeypatch.setattr(spec_spine_service, "spine_key", lambda *a, **k: 1 / 0)
    assert fn("Acme", "Bottle") is None


def test_s14_r23_kb_variant_key(prod_identity_env):
    prod_identity_env(None)
    kb = _kb()
    vk = _attr(kb, "kb_variant_key")
    pid_fn = _attr(kb, "kb_product_id")
    from app.services import price_service

    for idx, (row, key) in enumerate(SPINE_MATRIX):
        pid = pid_fn(*row)
        if pid is None:
            continue
        surface = " ".join(x for x in row if x)
        got = vk(pid, price_service.extract_concentration(surface), price_service.extract_size_ml_any(surface))
        if key.endswith("|6000"):
            assert got == pid + "|-", "R-S14-5: a size above 5000 ml maps to '-'"
        else:
            assert got == key, (row, got, key)
    p = "fragrances|a|b|EDP"
    assert vk(p, "EDP", 100) == p + "|100"
    assert vk(p, "EDP", None) == p + "|-"
    assert vk(p, "EDP", 0) == p + "|-"
    assert vk(p, "EDP", 5000) == p + "|5000"
    assert vk(p, "EDP", 5001) == p + "|-"
    assert vk(p, "EDP", 10000) == p + "|-"
    for bad in (-1, True, 1.5, "100"):
        assert vk(p, "EDP", bad) is None, bad
    assert vk(p, "EDT", 100) is None
    assert vk(p, None, 100) is None
    assert vk("fragrances|a|b|-", None, 50) == "fragrances|a|b|-|50"
    assert vk("fragrances|a|b|-", "EDP", 50) is None
    for bad_pid in ("fragrances|a|b", "skincare|a|b|EDP", "fragrances||b|EDP", "fragrances|a||EDP",
                    "fragrances|a|b|EDP|100", None, 3):
        assert vk(bad_pid, "EDP", 100) is None, bad_pid


@pytest.mark.parametrize("guards", [None, "false", " TRUE "])
def test_s14_r24_source_allowed(monkeypatch, guards):
    if guards is None:
        monkeypatch.delenv("ENABLE_DATA_GUARDS_V2", raising=False)
    else:
        monkeypatch.setenv("ENABLE_DATA_GUARDS_V2", guards)
    kb = _kb()
    fn = _attr(kb, "kb_source_allowed")
    from app.services import deny_hosts

    for v in ("https://fr.fragrantica.com/x", "fimgs.net", "Parfumo", "https://shop.example/fragrantica-notes"):
        assert fn(v) is False, v
    for v in ("https://shop.example/p", "notfragrantica.example"):
        assert fn(v) is True, v
    for junk in (None, 3, b"x", ""):
        assert fn(junk) is deny_hosts.kb_source_allowed(junk)
    seen = []
    monkeypatch.setattr(deny_hosts, "kb_source_allowed", lambda value: seen.append(value) or False)
    assert fn("https://shop.example/p") is False
    assert seen == ["https://shop.example/p"], "read deny_hosts.kb_source_allowed at CALL time"


def _userinfo_url() -> str:
    return "https://" + "user" + ":" + "pw" + "@shop.example/p"


CANON_ROWS = [
    ("https://Shop.Example/p/1?utm=x#frag", "https://shop.example/p/1"),
    ("HTTPS://shop.example/P", "https://shop.example/P"),
    ("http://shop.example:80/p", "http://shop.example/p"),
    ("https://shop.example:443/p", "https://shop.example/p"),
    ("https://shop.example:8443/p", None),
    ("https://shop.example:80/p", None),
    ("https://shop.example", "https://shop.example/"),
    ("https://shop.example?x=1", "https://shop.example/"),
    ("https://shop.example./p", "https://shop.example/p"),
    ("https://sub.shop.example/a/b/", "https://sub.shop.example/a/b/"),
    ("https://shop.example/%7Ep", "https://shop.example/%7Ep"),
    ("https://xn--caf-dma.example/p", "https://xn--caf-dma.example/p"),
    ("USERINFO", None),
    ("https://user@shop.example/p", None),
    ("https://10.0.0.1/p", None),
    ("https://[::1]/p", None),
    ("https://localhost/p", None),
    ("https://shop.example\\evil/p", None),
    ("https://shop.example/a b", None),
    ("https://shop.example/a\tb", None),
    ("https://shop.example/p\x00", None),
    ("ftp://shop.example/p", None),
    ("//shop.example/p", None),
    ("shop.example/p", None),
    ("", None),
    ("https://shop..example/p", None),
    ("https://-shop.example/p", None),
    ("https://shop-.example/p", None),
    ("https://.shop.example/p", None),
    ("https://shop_x.example/p", None),
    ("https://shop.example:abc/p", None),
    ("https://shop.example:99999/p", None),
    ("IDN", None),
    ("https://www.fragrantica.com/perfume/x", None),
]


@pytest.mark.parametrize("raw,expected", CANON_ROWS, ids=[str(i) for i in range(len(CANON_ROWS))])
def test_s14_r25_canonical_offer_url(raw, expected):
    if raw == "USERINFO":
        raw = _userinfo_url()
    elif raw == "IDN":
        raw = "https://caf" + chr(0xE9) + ".example/p"  # a stated limit: IDN is refused
    fn = _attr(_kb(), "canonical_offer_url")
    got = fn(raw)
    assert got == expected, (raw, got)
    if got is not None:
        item = _col_item(_require(F045), "kb_offers", "canonical_url")
        fmt, belt = _quoted_regexes(_check_text(item))
        assert _py(fmt).search(got) and not _py(belt).search(got), got


def test_s14_r25b_junk_never_raises():
    fn = _attr(_kb(), "canonical_offer_url")
    for junk in (None, 3, b"https://shop.example/p", ["https://shop.example/p"]):
        assert fn(junk) is None


def test_s14_r25c_regex_constants_equal_the_sql():
    """R-S14-7: one Python constant per 045 regex text."""
    sql = _require(F045)
    kb = _kb()
    assert _attr(kb, "KB_HOST_REGEX") == HOST_RE
    assert "host ~ '%s'" % HOST_RE in _col_item(sql, "kb_merchants", "host")
    assert "provenance_host ~ '%s'" % HOST_RE in _col_item(sql, "kb_images", "provenance_host")
    assert _attr(kb, "KB_OFFER_URL_REGEX") == OFFER_URL_RE
    assert "canonical_url ~ '%s'" % OFFER_URL_RE in _col_item(sql, "kb_offers", "canonical_url")
    assert _attr(kb, "KB_IMAGE_URL_REGEX") == IMAGE_URL_RE
    assert "url ~ '%s'" % IMAGE_URL_RE in _col_item(sql, "kb_images", "url")
    assert _attr(kb, "KB_SOURCE_URL_REGEX") == SOURCE_URL_RE
    for t in ("kb_specs", "kb_reviews"):
        assert "source_url ~ '%s'" % SOURCE_URL_RE in _col_item(sql, t, "source_url")
    hint = _col_item(sql, "kb_gaps", "source_hint")
    assert "source_hint ~ '%s'" % HOST_RE in hint and "source_hint ~ '%s'" % OFFER_URL_RE in hint
    assert "!~*" not in hint, "the old substring source_hint CHECK is replaced (R-S14-6)"
    for name, txt in (("KB_MARKET_REGEX", "^[A-Z]{2,3}$"), ("KB_CURRENCY_REGEX", "^[A-Z]{3}$"),
                      ("KB_FIELD_REGEX", "^[a-z][a-z0-9_]{0,63}$"), ("KB_METRIC_REGEX", "^[a-z][a-z0-9_.:-]{0,127}$"),
                      ("KB_DEVICE_KEY_REGEX", "^[a-f0-9]{64}$")):
        assert _attr(kb, name) == txt
        assert "'%s'" % txt in _compact(_no_comments(sql)), txt


def test_s14_r26_gtin():
    fn = _attr(_kb(), "gtin_check_digit_ok")
    for n, g in _gtins().items():
        assert len(g) == n and fn(g) is True, g
        altered = g[:-1] + str((int(g[-1]) + 1) % 10)
        assert fn(altered) is False, altered
        assert fn(" " + g) is False and fn(g + " ") is False
        assert fn(int(g)) is False
    for n in (7, 9, 10, 11, 15):
        assert fn("1" * n) is False
    for junk in ("abcdefgh", None, True, 3, b"x", chr(0xFF11) * 8, ""):
        assert fn(junk) is False


def _valid_kwargs(table: str) -> dict:
    return {
        "kb_merchants": dict(host="shop.example", updated_at=T0),
        "kb_products": dict(id=PID, brand="Dior", name="Sauvage", identity_confidence="high", updated_at=T0),
        "kb_variants": dict(id=VID, product_id=PID, concentration="EDP", size_ml=100, gtin=_gtins()[13], updated_at=T0),
        "kb_offers": dict(variant_id=VID, merchant_id="shop.example", market="BH", amount=30,
                          observed_currency="BHD", evidence_rung="own_token",
                          canonical_url="https://shop.example/p/1", captured_at=T0),
        "kb_images": dict(product_id=PID, url="https://cdn.shop.example/i.jpg", provenance_host="shop.example",
                          source="retailer_jsonld", captured_at=T0),
        "kb_specs": dict(product_id=PID, field="top_notes", value="bergamot", extractor="jsonld",
                         captured_at=T0, source_url="https://shop.example/p/1", cited=True),
        "kb_reviews": dict(product_id=PID, source="retailer_jsonld", source_url="https://shop.example/p/1",
                           captured_at=T0, aggregate_rating=4.5, review_count=12),
        "kb_gaps": dict(product_key=PID, field="top_notes", first_seen=T0),
        "kb_feedback": dict(compare_request_id=uuid.uuid4(), field="price", verdict="correct", device_key=DK),
        "kb_coverage_daily": dict(day=date(2026, 10, 23), metric="kb_hit_rate", value=0.5, n=10),
    }[table]


BUILDERS = {
    "kb_merchants": "build_merchant_row", "kb_products": "build_product_row",
    "kb_variants": "build_variant_row", "kb_offers": "build_offer_row", "kb_images": "build_image_row",
    "kb_specs": "build_spec_row", "kb_reviews": "build_review_row", "kb_gaps": "build_gap_row",
    "kb_feedback": "build_feedback_row", "kb_coverage_daily": "build_coverage_row",
}
UUID_ID_TABLES = {"kb_offers", "kb_images", "kb_specs", "kb_reviews", "kb_gaps", "kb_feedback"}


@pytest.mark.parametrize("table", KB_TABLE_NAMES)
def test_s14_r27_builder_keys(table):
    sql = _require(F045)
    kb = _kb()
    row = _attr(kb, BUILDERS[table])(**_valid_kwargs(table))
    assert isinstance(row, dict), "%s refused its valid kwargs" % BUILDERS[table]
    cols = [c.split()[0] for c in _columns(sql, table)]
    want = [c for c in cols if c != "created_at" and not (c == "id" and table in UUID_ID_TABLES)]
    assert set(row) == set(want)
    assert tuple(want) == tuple(_attr(kb, "KB_BUILDER_KEYS")[table])
    if table in ("kb_merchants", "kb_products", "kb_variants"):
        assert row["updated_at"] == T0.isoformat(), "R-S14-2: builders emit updated_at (belt)"
    assert tuple(_attr(kb, "KB_TABLES")) == KB_TABLE_NAMES


NAIVE = datetime(2026, 10, 23, 12, 0)
LATER = T0 + timedelta(days=1)

REFUSALS = [
    # kb_merchants (no deny check here: R-S14-2)
    ("kb_merchants", "host_upper", dict(host="Shop.Example")),
    ("kb_merchants", "host_no_dot", dict(host="shop")),
    ("kb_merchants", "host_empty_label", dict(host="shop..example")),
    ("kb_merchants", "host_edge_hyphen", dict(host="-shop.example")),
    ("kb_merchants", "country_lower", dict(country="bh")),
    ("kb_merchants", "country_long", dict(country="BAHR")),
    ("kb_merchants", "currency_lower", dict(currency_hint="bhd")),
    ("kb_merchants", "platform_empty", dict(platform="")),
    ("kb_merchants", "platform_long", dict(platform="x" * 33)),
    ("kb_merchants", "platform_confidence_numeric", dict(platform_confidence=0.9)),
    ("kb_merchants", "platform_confidence_word", dict(platform_confidence="high")),
    ("kb_merchants", "adapter_long", dict(adapter="x" * 65)),
    ("kb_merchants", "search_template_long", dict(search_template="x" * 1025)),
    ("kb_merchants", "registry_object", dict(registry={})),
    ("kb_merchants", "registry_scalar_member", dict(registry=[1])),
    ("kb_merchants", "registry_bad_origin", dict(registry=[{"origin": "web", "order": 0}])),
    ("kb_merchants", "registry_negative_order", dict(registry=[{"origin": "literal", "order": -1}])),
    ("kb_merchants", "registry_bool_order", dict(registry=[{"origin": "literal", "order": True}])),
    ("kb_merchants", "registry_nan",
     dict(registry=[{"origin": "literal", "order": 0, "search_descriptor": {"w": float("nan")}}])),
    ("kb_merchants", "robots_array", dict(robots=[])),
    ("kb_merchants", "partner_array", dict(partner=[])),
    ("kb_merchants", "tos_string", dict(tos="x")),
    ("kb_merchants", "deny_not_bool", dict(deny=0)),
    ("kb_merchants", "status_unknown", dict(status="dead")),
    ("kb_merchants", "blocked_reason_long", dict(status="blocked", blocked_reason="x" * 65)),
    ("kb_merchants", "deny_without_blocked", dict(deny=True, status="live")),
    ("kb_merchants", "blocked_without_reason", dict(status="blocked")),
    ("kb_merchants", "updated_at_naive", dict(updated_at=NAIVE)),
    ("kb_merchants", "updated_at_none", dict(updated_at=None)),
    # kb_products
    ("kb_products", "id_short", dict(id="fragrances|a")),
    ("kb_products", "id_other_category", dict(id="skincare|acme|cream|-")),
    ("kb_products", "id_long", dict(id="fragrances|" + "x" * 510)),
    ("kb_products", "brand_empty", dict(brand="")),
    ("kb_products", "brand_long", dict(brand="x" * 129)),
    ("kb_products", "line_empty", dict(line="")),
    ("kb_products", "name_long", dict(name="x" * 257)),
    ("kb_products", "name_none", dict(name=None)),
    ("kb_products", "concentration_lower", dict(concentration="edp")),
    ("kb_products", "audience_male", dict(audience="male")),
    ("kb_products", "identity_unresolved", dict(identity_confidence="unresolved")),
    ("kb_products", "updated_at_naive", dict(updated_at=NAIVE)),
    # kb_variants
    ("kb_variants", "id_not_extending", dict(id="fragrances|christian+dior|sauvage|EDX|100")),
    ("kb_variants", "id_bare_pipe", dict(id=PID + "|")),
    ("kb_variants", "id_too_long", dict(id=PID + "|12345")),
    ("kb_variants", "concentration_lower", dict(concentration="edp")),
    ("kb_variants", "size_zero", dict(size_ml=0)),
    ("kb_variants", "size_huge", dict(size_ml=10000)),
    ("kb_variants", "size_bool", dict(size_ml=True)),
    ("kb_variants", "size_float", dict(size_ml=1.5)),
    ("kb_variants", "gtin_bad_digit", dict(gtin="GTIN_ALTERED")),
    ("kb_variants", "gtin_letters", dict(gtin="abcdefgh")),
    ("kb_variants", "sku_long", dict(sku="x" * 129)),
    ("kb_variants", "updated_at_none", dict(updated_at=None)),
    # kb_offers
    ("kb_offers", "variant_empty", dict(variant_id="")),
    ("kb_offers", "merchant_single_label", dict(merchant_id="example")),
    ("kb_offers", "market_lower", dict(market="bh")),
    ("kb_offers", "market_long", dict(market="BAHR")),
    ("kb_offers", "market_none", dict(market=None)),
    ("kb_offers", "amount_zero", dict(amount=0)),
    ("kb_offers", "amount_negative", dict(amount=-1)),
    ("kb_offers", "amount_rounds_to_zero", dict(amount=0.0004)),
    ("kb_offers", "amount_bool", dict(amount=True)),
    ("kb_offers", "amount_string", dict(amount="30")),
    ("kb_offers", "amount_nan", dict(amount=float("nan"))),
    ("kb_offers", "amount_inf", dict(amount=float("inf"))),
    ("kb_offers", "amount_overflow", dict(amount=10 ** 11)),
    ("kb_offers", "currency_lower", dict(observed_currency="bhd")),
    ("kb_offers", "currency_long", dict(observed_currency="BHDX")),
    ("kb_offers", "rung_raw_token", dict(evidence_rung="raw_token")),
    ("kb_offers", "size_zero", dict(size_ml=0)),
    ("kb_offers", "list_vs_sale_rrp", dict(list_vs_sale="rrp")),
    ("kb_offers", "in_stock_string", dict(in_stock="yes")),
    ("kb_offers", "first_after_last", dict(first_seen=LATER, last_seen=T0)),
    ("kb_offers", "captured_naive", dict(captured_at=NAIVE)),
    ("kb_offers", "url_with_query", dict(canonical_url="https://shop.example/p?x=1")),
    ("kb_offers", "url_upper_host", dict(canonical_url="https://WWW.shop.example/p")),
    ("kb_offers", "url_other_host", dict(canonical_url="https://other.example/p")),
    ("kb_offers", "url_suffix_trick", dict(canonical_url="https://notshop.example/p")),
    ("kb_offers", "url_denied", dict(merchant_id="fragrantica-x.example", canonical_url="https://fragrantica-x.example/p")),
    ("kb_offers", "url_denied_token", dict(canonical_url="https://shop.example/fragrantica-notes")),
    # kb_images
    ("kb_images", "url_http", dict(url="http://cdn.shop.example/i.jpg")),
    ("kb_images", "url_denied", dict(url="https://cdn.shop.example/fimgs/x.jpg")),
    ("kb_images", "url_fragment", dict(url="https://cdn.shop.example/i.jpg#x")),
    ("kb_images", "url_long", dict(url="https://cdn.shop.example/" + "x" * 2048)),
    ("kb_images", "url_space", dict(url="https://cdn.shop.example/a b")),
    ("kb_images", "provenance_denied", dict(provenance_host="fragrantica-x.example")),
    ("kb_images", "provenance_denied_sub", dict(provenance_host="parfumo-cdn.shop.example")),
    ("kb_images", "provenance_upper", dict(provenance_host="Shop.Example")),
    ("kb_images", "source_google", dict(source="google")),
    ("kb_images", "variant_empty", dict(variant_id="")),
    ("kb_images", "captured_none", dict(captured_at=None)),
    # kb_specs
    ("kb_specs", "field_upper", dict(field="Top_Notes")),
    ("kb_specs", "field_digit_first", dict(field="1x")),
    ("kb_specs", "field_long", dict(field="x" * 65)),
    ("kb_specs", "lang_fr", dict(lang="fr")),
    ("kb_specs", "lang_upper", dict(lang="EN")),
    ("kb_specs", "value_empty", dict(value="")),
    ("kb_specs", "value_long", dict(value="x" * 2001)),
    ("kb_specs", "source_denied", dict(source_url="https://basenotes-archive.example/x")),
    ("kb_specs", "source_denied_token", dict(source_url="https://shop.example/fragrantica-notes")),
    ("kb_specs", "source_ftp", dict(source_url="ftp://shop.example/x")),
    ("kb_specs", "source_space", dict(source_url="https://shop.example/a b")),
    ("kb_specs", "extractor_empty", dict(extractor="")),
    ("kb_specs", "model_long", dict(model="x" * 65)),
    ("kb_specs", "cited_not_bool", dict(cited="yes")),
    ("kb_specs", "cited_without_source", dict(cited=True, source_url=None)),
    ("kb_specs", "captured_naive", dict(captured_at=NAIVE)),
    # kb_reviews
    ("kb_reviews", "source_fragrantica", dict(source="fragrantica")),
    ("kb_reviews", "source_google", dict(source="google")),
    ("kb_reviews", "rating_over", dict(aggregate_rating=5.01)),
    ("kb_reviews", "rating_negative", dict(aggregate_rating=-0.1)),
    ("kb_reviews", "rating_string", dict(aggregate_rating="4.5")),
    ("kb_reviews", "rating_bool", dict(aggregate_rating=True)),
    ("kb_reviews", "rating_nan", dict(aggregate_rating=float("nan"))),
    ("kb_reviews", "count_negative", dict(review_count=-1)),
    ("kb_reviews", "count_bool", dict(review_count=True)),
    ("kb_reviews", "count_float", dict(review_count=1.5)),
    ("kb_reviews", "count_overflow", dict(review_count=2 ** 31)),
    ("kb_reviews", "no_signal", dict(aggregate_rating=None, review_count=None)),
    ("kb_reviews", "source_url_denied", dict(source_url="https://shop.example/parfumo-review/p")),
    ("kb_reviews", "source_url_no_path", dict(source_url="http://shop.example")),
    # kb_gaps
    ("kb_gaps", "key_short", dict(product_key="fragrances|a")),
    ("kb_gaps", "key_long", dict(product_key="x" * 521)),
    ("kb_gaps", "field_upper", dict(field="Bad")),
    ("kb_gaps", "demand_negative", dict(demand_count=-1)),
    ("kb_gaps", "demand_bool", dict(demand_count=True)),
    ("kb_gaps", "state_done", dict(state="done")),
    ("kb_gaps", "hint_denied_host", dict(source_hint="x.fragrantica")),
    ("kb_gaps", "hint_denied_url", dict(source_hint="https://shop.example/fragrantica-notes")),
    ("kb_gaps", "hint_denied_name", dict(source_hint="fragrantica-x.example")),
    ("kb_gaps", "hint_user_text", dict(source_hint="dior sauvage review please")),
    ("kb_gaps", "hint_no_scheme_path", dict(source_hint="shop.example/p")),
    ("kb_gaps", "hint_query", dict(source_hint="https://shop.example/p?q=1")),
    ("kb_gaps", "hint_long", dict(source_hint="a." + "b" * 255)),
    ("kb_gaps", "first_after_last", dict(first_seen=LATER, last_seen=T0)),
    # kb_feedback
    ("kb_feedback", "request_not_uuid", dict(compare_request_id="not-a-uuid")),
    ("kb_feedback", "request_int", dict(compare_request_id=3)),
    ("kb_feedback", "field_upper", dict(field="Bad")),
    ("kb_feedback", "verdict_yes", dict(verdict="yes")),
    ("kb_feedback", "device_upper", dict(device_key="AB" * 32)),
    ("kb_feedback", "device_short", dict(device_key="ab" * 31)),
    ("kb_feedback", "device_not_hex", dict(device_key="zz" * 32)),
    ("kb_feedback", "device_newline", dict(device_key="ab" * 32 + "\n")),
    ("kb_feedback", "product_empty", dict(product_id="")),
    # kb_coverage_daily
    ("kb_coverage_daily", "day_datetime", dict(day=T0)),
    ("kb_coverage_daily", "day_string", dict(day="2026-10-23")),
    ("kb_coverage_daily", "metric_upper", dict(metric="Bad")),
    ("kb_coverage_daily", "metric_digit_first", dict(metric="1x")),
    ("kb_coverage_daily", "metric_long", dict(metric="x" * 129)),
    ("kb_coverage_daily", "metric_space", dict(metric="a b")),
    ("kb_coverage_daily", "value_bool", dict(value=True)),
    ("kb_coverage_daily", "value_nan", dict(value=float("nan"))),
    ("kb_coverage_daily", "value_string", dict(value="1")),
    ("kb_coverage_daily", "n_negative", dict(n=-1)),
    ("kb_coverage_daily", "n_bool", dict(n=True)),
    # --- fix round 1 (RULINGS_FIX1_S81_14) ---
    # F1-6: no all-digit host (the top-level label carries a letter), on every host and URL host
    ("kb_merchants", "host_all_digit", dict(host="10.0.0.1")),
    ("kb_merchants", "host_digit_top_label", dict(host="shop.123")),
    ("kb_offers", "url_digit_top_label", dict(merchant_id="shop.123", canonical_url="https://shop.123/p")),
    ("kb_images", "url_all_digit_host", dict(url="https://10.0.0.1/i.jpg")),
    ("kb_images", "provenance_all_digit", dict(provenance_host="10.0.0.1")),
    ("kb_specs", "source_all_digit_host", dict(source_url="https://10.0.0.1/x")),
    ("kb_reviews", "source_url_all_digit_host", dict(source_url="https://10.0.0.1/p")),
    ("kb_gaps", "hint_all_digit_host", dict(source_hint="10.0.0.1")),
    ("kb_gaps", "hint_all_digit_url", dict(source_hint="https://10.0.0.1/p")),
    # F1-6: the raw rating is bounded (PostgreSQL would round these into range)
    ("kb_reviews", "rating_just_over", dict(aggregate_rating=5.001)),
    ("kb_reviews", "rating_just_below", dict(aggregate_rating=-0.001)),
    ("kb_reviews", "rating_half_over", dict(aggregate_rating=5.005)),
    # F1-3: the PRESENT registry keys and their types, unique orders, domain == host
    ("kb_merchants", "registry_unknown_key", dict(registry=[{"origin": "literal", "order": 0, "bogus": "x"}])),
    ("kb_merchants", "registry_str_field_type", dict(registry=[{"origin": "literal", "order": 0, "tier": 5}])),
    ("kb_merchants", "registry_float_field_type",
     dict(registry=[{"origin": "literal", "order": 0, "weight": "heavy"}])),
    ("kb_merchants", "registry_bool_field_type",
     dict(registry=[{"origin": "literal", "order": 0, "is_shopify": "yes"}])),
    ("kb_merchants", "registry_tuple_field_type",
     dict(registry=[{"origin": "literal", "order": 0, "categories": "fragrances"}])),
    ("kb_merchants", "registry_tuple_member_type",
     dict(registry=[{"origin": "literal", "order": 0, "categories": [1]}])),
    ("kb_merchants", "registry_int_field_type",
     dict(registry=[{"origin": "literal", "order": 0, "priority_rank": 1.5}])),
    ("kb_merchants", "registry_optional_field_type",
     dict(registry=[{"origin": "literal", "order": 0, "search_descriptor": "x"}])),
    ("kb_merchants", "registry_duplicate_order",
     dict(registry=[{"origin": "literal", "order": 0}, {"origin": "catalog", "order": 0}])),
    ("kb_merchants", "registry_domain_other_host",
     dict(registry=[{"origin": "literal", "order": 0, "domain": "other.example"}])),
    # F1-8: no NUL character and no lone surrogate in any text or jsonb value
    ("kb_merchants", "nul_platform", dict(platform="ab" + chr(0))),
    ("kb_merchants", "surrogate_adapter", dict(adapter="ab" + chr(0xD800))),
    ("kb_merchants", "nul_jsonb_key", dict(robots={"a" + chr(0): 1})),
    ("kb_merchants", "nul_jsonb_value", dict(tos={"note": "a" + chr(0)})),
    ("kb_products", "nul_name", dict(name="Sau" + chr(0) + "vage")),
    ("kb_products", "surrogate_brand", dict(brand="Di" + chr(0xD800) + "or")),
    ("kb_variants", "nul_sku", dict(sku="S" + chr(0) + "K")),
    ("kb_offers", "url_surrogate", dict(canonical_url="https://shop.example/p" + chr(0xD800))),
    ("kb_images", "url_nul", dict(url="https://cdn.shop.example/i" + chr(0) + ".jpg")),
    ("kb_specs", "value_nul", dict(value="berg" + chr(0) + "amot")),
    ("kb_specs", "value_surrogate", dict(value="berg" + chr(0xDC00) + "amot")),
    ("kb_reviews", "source_url_nul", dict(source_url="https://shop.example/p" + chr(0))),
    ("kb_gaps", "key_nul", dict(product_key=PID + chr(0))),
    ("kb_feedback", "product_nul", dict(product_id="p" + chr(0))),
    # --- fix round 2 (RULINGS_FIX2_S81_14) ---
    # F2-2: a bool Source field refuses a non-bool (an int 1)
    ("kb_merchants", "registry_bool_field_int",
     dict(registry=[{"origin": "literal", "order": 0, "is_shopify": 1}])),
    # F2-3: domain == host is EXACT equality after lower-casing: no sibling, apex or Unicode-fold shortcut
    ("kb_merchants", "registry_domain_sibling",
     dict(host="ksa.shop.example", registry=[{"origin": "literal", "order": 0, "domain": "om.shop.example"}])),
    ("kb_merchants", "registry_domain_apex_of_host",
     dict(host="ksa.shop.example", registry=[{"origin": "literal", "order": 0, "domain": "shop.example"}])),
    ("kb_merchants", "registry_domain_non_ascii_fold",
     dict(host="k.example", registry=[{"origin": "literal", "order": 0, "domain": chr(0x212A) + ".example"}])),
    # F2-4: a last label that is all digits or 0x-hex (IPv4 to a WHATWG parser or inet_aton) is refused
    # on every host and URL host (10.0.0.1 rows exist from fix round 1 except on kb_offers)
    ("kb_merchants", "host_hex_last_label", dict(host="127.0.0.0x1")),
    ("kb_merchants", "host_hex_every_label", dict(host="0x7f.0x0.0x0.0x1")),
    ("kb_merchants", "host_hex_after_digits", dict(host="1.2.3.0x4")),
    ("kb_offers", "url_hex_last_label", dict(merchant_id="127.0.0.0x1", canonical_url="https://127.0.0.0x1/p")),
    ("kb_offers", "url_hex_every_label", dict(merchant_id="0x7f.0x0.0x0.0x1", canonical_url="https://0x7f.0x0.0x0.0x1/p")),
    ("kb_offers", "url_hex_after_digits", dict(merchant_id="1.2.3.0x4", canonical_url="https://1.2.3.0x4/p")),
    ("kb_offers", "url_all_digit_host", dict(merchant_id="10.0.0.1", canonical_url="https://10.0.0.1/p")),
    ("kb_images", "url_hex_last_label", dict(url="https://127.0.0.0x1/i.jpg")),
    ("kb_images", "provenance_hex_last_label", dict(provenance_host="127.0.0.0x1")),
    ("kb_specs", "source_hex_last_label", dict(source_url="https://127.0.0.0x1/x")),
    ("kb_reviews", "source_url_hex_last_label", dict(source_url="https://127.0.0.0x1/p")),
    ("kb_gaps", "hint_hex_last_label_host", dict(source_hint="127.0.0.0x1")),
    ("kb_gaps", "hint_hex_last_label_url", dict(source_hint="https://127.0.0.0x1/p")),
    ("kb_images", "url_hex_every_label", dict(url="https://0x7f.0x0.0x0.0x1/i.jpg")),
    ("kb_images", "provenance_hex_every_label", dict(provenance_host="0x7f.0x0.0x0.0x1")),
    ("kb_specs", "source_hex_every_label", dict(source_url="https://0x7f.0x0.0x0.0x1/x")),
    ("kb_reviews", "source_url_hex_every_label", dict(source_url="https://0x7f.0x0.0x0.0x1/p")),
    ("kb_gaps", "hint_hex_every_label_host", dict(source_hint="0x7f.0x0.0x0.0x1")),
    ("kb_gaps", "hint_hex_every_label_url", dict(source_hint="https://0x7f.0x0.0x0.0x1/p")),
    ("kb_images", "url_hex_after_digits", dict(url="https://1.2.3.0x4/i.jpg")),
    ("kb_images", "provenance_hex_after_digits", dict(provenance_host="1.2.3.0x4")),
    ("kb_specs", "source_hex_after_digits", dict(source_url="https://1.2.3.0x4/x")),
    ("kb_reviews", "source_url_hex_after_digits", dict(source_url="https://1.2.3.0x4/p")),
    ("kb_gaps", "hint_hex_after_digits_host", dict(source_hint="1.2.3.0x4")),
    ("kb_gaps", "hint_hex_after_digits_url", dict(source_hint="https://1.2.3.0x4/p")),
]


@pytest.mark.parametrize("table,label,over", REFUSALS, ids=["%s-%s" % (r[0], r[1]) for r in REFUSALS])
def test_s14_r28_builders_refuse(table, label, over):
    """R-S14-11: the builders mirror EVERY 045 CHECK clause (one row per clause)."""
    kb = _kb()
    kwargs = dict(_valid_kwargs(table))
    kwargs.update(over)
    if kwargs.get("gtin") == "GTIN_ALTERED":
        g = _gtins()[13]
        kwargs["gtin"] = g[:-1] + str((int(g[-1]) + 1) % 10)
    assert _attr(kb, BUILDERS[table])(**kwargs) is None, "%s accepted %s" % (BUILDERS[table], label)


ACCEPTS = [
    ("kb_feedback", "device_less_vote", dict(device_key=None)),
    ("kb_feedback", "uuid_string", dict(compare_request_id=str(uuid.UUID(int=7)))),
    ("kb_gaps", "hint_host", dict(source_hint="shop.example")),
    ("kb_gaps", "hint_url", dict(source_hint="https://shop.example/p")),
    ("kb_gaps", "hint_lookalike_host", dict(source_hint="notfragrantica.example")),
    ("kb_specs", "lang_ar", dict(lang="ar")),
    ("kb_offers", "decimal_amount", dict(amount=Decimal("29.990"))),
    ("kb_offers", "subdomain_url", dict(canonical_url="https://www.shop.example/p/1")),
    ("kb_offers", "market_three", dict(market="UAE")),
    ("kb_reviews", "count_only", dict(aggregate_rating=None, review_count=0)),
    ("kb_variants", "sizeless", dict(id=PID + "|-", size_ml=None)),
    ("kb_merchants", "denied_host_stored_blocked",
     dict(host="fragrantica.com", deny=True, status="blocked", blocked_reason="deny_label")),
    ("kb_merchants", "denied_host_not_checked_here", dict(host="fragrantica.com", status="live")),
    ("kb_merchants", "registry_entries",
     dict(registry=[{"origin": "literal", "order": 0, "domain": "noon.com"},
                    {"origin": "literal", "order": 1, "domain": "noon.com"}],
          platform_confidence="mechanism", host="noon.com")),
    # --- fix round 1 (RULINGS_FIX1_S81_14) ---
    # F1-3: presence of every Source field is S81-15's seed contract, so a bare entry is ACCEPTED here
    ("kb_merchants", "registry_no_source_field", dict(registry=[{"origin": "literal", "order": 0}])),
    ("kb_merchants", "registry_typed_entries",
     dict(registry=[{"origin": "catalog", "order": 0, "domain": "shop.example", "tier": "bahrain",
                     "categories": ["fragrances"], "weight": 3.0, "usage": "price", "is_shopify": True,
                     "priority_rank": 5, "search_descriptor": None, "locale_paths": []},
                    {"origin": "operator", "order": 2, "weight": 1, "search_descriptor": {"search": "x"}}])),
    # F1-6: a digit registrable label is a real host (4711.com); only the top-level label needs a letter
    ("kb_merchants", "host_digit_registrable_label", dict(host="4711.com")),
    ("kb_images", "url_digit_registrable_label",
     dict(url="https://cdn.4711.com/i.jpg", provenance_host="4711.com")),
    # F1-6: the rating bounds and the half tie
    ("kb_reviews", "rating_zero", dict(aggregate_rating=0)),
    ("kb_reviews", "rating_five", dict(aggregate_rating=5.0)),
    ("kb_reviews", "rating_rounds_to_five", dict(aggregate_rating=4.995)),
    ("kb_offers", "amount_half_tie", dict(amount=0.0005)),
    # --- fix round 2 (RULINGS_FIX2_S81_14) ---
    # F2-3: the comparison lower-cases the domain (source_router lower-cases both sides at every lookup)
    ("kb_merchants", "registry_domain_case",
     dict(registry=[{"origin": "literal", "order": 0, "domain": "Shop.Example"}])),
    # F2-4: a digit or hex-looking registrable label, or a letter-bearing top label, stays a host
    ("kb_merchants", "host_digit_registrable_163", dict(host="163.com")),
    ("kb_merchants", "host_hex_registrable_label", dict(host="0xbeef.example")),
    ("kb_merchants", "host_hex_like_top_label", dict(host="shop.0xg")),
    ("kb_offers", "url_digit_registrable_163", dict(merchant_id="163.com", canonical_url="https://www.163.com/p")),
    ("kb_images", "url_hex_registrable_label",
     dict(url="https://0xbeef.example/i.jpg", provenance_host="0xbeef.example")),
    ("kb_specs", "source_digit_registrable_label", dict(source_url="https://4711.com/x")),
    ("kb_reviews", "source_url_digit_registrable_163", dict(source_url="https://163.com/p")),
    ("kb_gaps", "hint_digit_registrable_host", dict(source_hint="4711.com")),
    ("kb_gaps", "hint_digit_registrable_url", dict(source_hint="https://cdn.163.com/p")),
]


@pytest.mark.parametrize("table,label,over", ACCEPTS, ids=["%s-%s" % (r[0], r[1]) for r in ACCEPTS])
def test_s14_r28b_builders_accept(table, label, over):
    kb = _kb()
    kwargs = dict(_valid_kwargs(table))
    kwargs.update(over)
    row = _attr(kb, BUILDERS[table])(**kwargs)
    assert isinstance(row, dict), "%s refused %s" % (BUILDERS[table], label)


def test_s14_r28c_merchant_builder_never_calls_the_deny_rule(monkeypatch):
    """R-S14-2: no builder applies kb_source_allowed to kb_merchants."""
    kb = _kb()
    from app.services import deny_hosts

    seen = []
    monkeypatch.setattr(deny_hosts, "kb_source_allowed", lambda v: seen.append(v) or True)
    row = _attr(kb, "build_merchant_row")(
        host="fragrantica.com", deny=True, status="blocked", blocked_reason="deny_label", updated_at=T0,
    )
    assert row is not None and row["deny"] is True and row["status"] == "blocked"
    assert seen == []
    _attr(kb, "build_offer_row")(**_valid_kwargs("kb_offers"))
    assert seen, "positive control: the offer builder does call the deny rule"


def test_s14_r28d_offer_observation_contract():
    """R-S14-1 (a): the observation key and the re-observation SET columns."""
    sql = _require(F045)
    kb = _kb()
    cons = [c for c in _constraints(sql, "kb_offers") if c.startswith("CONSTRAINT kb_offers_observation ")]
    assert len(cons) == 1
    cols = tuple(x.strip() for x in re.search(r"UNIQUE \((.*)\)", cons[0]).group(1).split(","))
    assert cols == ("variant_id", "merchant_id", "market", "observed_currency", "amount", "list_vs_sale")
    assert tuple(_attr(kb, "KB_OFFER_OBSERVATION_KEY")) == cols
    upsert = tuple(_attr(kb, "KB_OFFER_UPSERT_SET"))
    assert upsert == ("last_seen", "in_stock", "evidence_rung", "canonical_url")
    assert not set(upsert) & set(cols)
    assert "captured_at" not in upsert and "first_seen" not in upsert


def test_s14_r29_leaf_never_raises_on_junk():
    kb = _kb()
    for name in BUILDERS.values():
        fn = _attr(kb, name)
        assert fn(**{k: object() for k in _valid_kwargs(_table_of(name))}) is None, name
    for fn_name in ("kb_product_id", "kb_variant_key", "canonical_offer_url", "gtin_check_digit_ok"):
        fn = _attr(kb, fn_name)
        args = {"kb_product_id": (object(), object()), "kb_variant_key": (object(), object(), object()),
                "canonical_offer_url": (object(),), "gtin_check_digit_ok": (object(),)}[fn_name]
        assert fn(*args) in (None, False)


def _table_of(builder: str) -> str:
    return {v: k for k, v in BUILDERS.items()}[builder]


# ===========================================================================
# Fix round 1 (RULINGS_FIX1_S81_14, F1-1..F1-10): rows appended after the
# adversaries on GREEN 0910e7d0. RED = fails on the pre-fix bytes (an
# AssertionError); PIN = green there and kills a named mutant.
# ===========================================================================

# F1-7: every refusal row names the ONE clause it exercises; the fix round's
# mutation table removes only that clause and the row goes red (the clause ids
# are the mutant ids of the round's clause table).
REFUSAL_CLAUSES = {
    "kb_merchants": {
        "merchants.host_regex": ("host_upper", "host_no_dot", "host_empty_label", "host_edge_hyphen"),
        "merchants.host_top_label": ("host_all_digit", "host_digit_top_label"),
        "merchants.country": ("country_lower", "country_long"),
        "merchants.currency": ("currency_lower",),
        "merchants.platform_len": ("platform_empty", "platform_long"),
        "merchants.platform_confidence": ("platform_confidence_numeric", "platform_confidence_word"),
        "merchants.adapter_len": ("adapter_long",),
        "merchants.search_template_len": ("search_template_long",),
        "registry.list": ("registry_object",),
        "registry.entry_object": ("registry_scalar_member",),
        "registry.origin": ("registry_bad_origin",),
        "registry.order_nonnegative": ("registry_negative_order",),
        "registry.order_int": ("registry_bool_order",),
        "registry.order_unique": ("registry_duplicate_order",),
        "registry.json": ("registry_nan",),
        "registry.keys": ("registry_unknown_key",),
        "registry.types": (
            "registry_str_field_type", "registry_float_field_type", "registry_bool_field_type",
            "registry_tuple_field_type", "registry_tuple_member_type", "registry_int_field_type",
            "registry_optional_field_type",
        ),
        "registry.domain_is_host": ("registry_domain_other_host",),
        "merchants.jsonb_objects": ("robots_array", "partner_array", "tos_string"),
        "merchants.deny_bool": ("deny_not_bool",),
        "merchants.status": ("status_unknown",),
        "merchants.blocked_reason_len": ("blocked_reason_long",),
        "merchants.deny_is_blocked": ("deny_without_blocked",),
        "merchants.blocked_has_reason": ("blocked_without_reason",),
        "merchants.updated_at": ("updated_at_naive", "updated_at_none"),
        "merchants.pg_text": ("nul_platform", "surrogate_adapter", "nul_jsonb_key", "nul_jsonb_value"),
    },
    "kb_products": {
        "products.id_len": ("id_short", "id_long"),
        "products.id_prefix": ("id_other_category",),
        "products.brand_len": ("brand_empty", "brand_long"),
        "products.line_len": ("line_empty",),
        "products.name_len": ("name_long", "name_none"),
        "products.concentration": ("concentration_lower",),
        "products.audience": ("audience_male",),
        "products.identity_confidence": ("identity_unresolved",),
        "products.updated_at": ("updated_at_naive",),
        "products.pg_text": ("nul_name", "surrogate_brand"),
    },
    "kb_variants": {
        "variants.id_prefix": ("id_not_extending",),
        "variants.id_len": ("id_bare_pipe", "id_too_long"),
        "variants.concentration": ("concentration_lower",),
        "variants.size_range": ("size_zero", "size_huge"),
        "variants.size_int": ("size_bool", "size_float"),
        "variants.gtin": ("gtin_bad_digit", "gtin_letters"),
        "variants.sku_len": ("sku_long",),
        "variants.updated_at": ("updated_at_none",),
        "variants.pg_text": ("nul_sku",),
    },
    "kb_offers": {
        "offers.variant_len": ("variant_empty",),
        "offers.merchant_host": ("merchant_single_label",),
        "offers.market": ("market_lower", "market_long", "market_none"),
        "offers.amount_positive": ("amount_zero", "amount_negative", "amount_rounds_to_zero"),
        "offers.amount_number": ("amount_bool", "amount_string", "amount_nan", "amount_inf"),
        "offers.amount_max": ("amount_overflow",),
        "offers.currency": ("currency_lower", "currency_long"),
        "offers.evidence_rung": ("rung_raw_token",),
        "offers.size_range": ("size_zero",),
        "offers.list_vs_sale": ("list_vs_sale_rrp",),
        "offers.in_stock": ("in_stock_string",),
        "offers.seen_order": ("first_after_last",),
        "offers.timestamps": ("captured_naive",),
        "offers.canonical": ("url_with_query", "url_upper_host", "url_digit_top_label"),
        "offers.url_on_merchant": ("url_other_host", "url_suffix_trick"),
        "offers.deny_rule": ("url_denied", "url_denied_token"),
        "offers.pg_text": ("url_surrogate",),
    },
    "kb_images": {
        "images.url_format": ("url_http", "url_fragment", "url_space"),
        "images.url_len": ("url_long",),
        "url.top_label": ("url_all_digit_host",),
        "images.url_deny_rule": ("url_denied",),
        "images.provenance_host_regex": ("provenance_upper",),
        "host.top_label": ("provenance_all_digit",),
        "images.provenance_deny_rule": ("provenance_denied", "provenance_denied_sub"),
        "images.source": ("source_google",),
        "images.variant_len": ("variant_empty",),
        "images.captured_at": ("captured_none",),
        "images.pg_text": ("url_nul",),
    },
    "kb_specs": {
        "specs.field": ("field_upper", "field_digit_first", "field_long"),
        "specs.lang": ("lang_fr", "lang_upper"),
        "specs.value_len": ("value_empty", "value_long"),
        "specs.deny_rule": ("source_denied", "source_denied_token"),
        "specs.source_format": ("source_ftp", "source_space"),
        "url.top_label": ("source_all_digit_host",),
        "specs.extractor_len": ("extractor_empty",),
        "specs.model_len": ("model_long",),
        "specs.cited_bool": ("cited_not_bool",),
        "specs.cited_has_source": ("cited_without_source",),
        "specs.captured_at": ("captured_naive",),
        "specs.pg_text": ("value_nul", "value_surrogate"),
    },
    "kb_reviews": {
        "reviews.source": ("source_fragrantica", "source_google"),
        "reviews.rating_bound": (
            "rating_over", "rating_negative", "rating_just_over", "rating_just_below", "rating_half_over",
        ),
        "reviews.rating_number": ("rating_string", "rating_bool", "rating_nan"),
        "reviews.count_range": ("count_negative", "count_overflow"),
        "reviews.count_int": ("count_bool", "count_float"),
        "reviews.has_signal": ("no_signal",),
        "reviews.deny_rule": ("source_url_denied",),
        "reviews.source_format": ("source_url_no_path",),
        "url.top_label": ("source_url_all_digit_host",),
        "reviews.pg_text": ("source_url_nul",),
    },
    "kb_gaps": {
        "gaps.key_len": ("key_short", "key_long"),
        "gaps.field": ("field_upper",),
        "gaps.demand_range": ("demand_negative",),
        "gaps.demand_int": ("demand_bool",),
        "gaps.state": ("state_done",),
        "gaps.hint_deny_rule": ("hint_denied_host", "hint_denied_url", "hint_denied_name"),
        "gaps.hint_shape": ("hint_user_text", "hint_no_scheme_path", "hint_query"),
        "gaps.hint_len": ("hint_long",),
        "host.top_label": ("hint_all_digit_host",),
        "url.top_label": ("hint_all_digit_url",),
        "gaps.seen_order": ("first_after_last",),
        "gaps.pg_text": ("key_nul",),
    },
    "kb_feedback": {
        "feedback.request_uuid": ("request_not_uuid",),
        "feedback.request_type": ("request_int",),
        "feedback.field": ("field_upper",),
        "feedback.verdict": ("verdict_yes",),
        "feedback.device_key": ("device_upper", "device_short", "device_not_hex", "device_newline"),
        "feedback.product_len": ("product_empty",),
        "feedback.pg_text": ("product_nul",),
    },
    "kb_coverage_daily": {
        "coverage.day_date": ("day_datetime", "day_string"),
        "coverage.metric": ("metric_upper", "metric_digit_first", "metric_long", "metric_space"),
        "coverage.value_number": ("value_bool", "value_nan", "value_string"),
        "coverage.n_range": ("n_negative",),
        "coverage.n_int": ("n_bool",),
    },
}


def _clause_of() -> dict:
    out = {}
    for table, clauses in REFUSAL_CLAUSES.items():
        for clause, labels in clauses.items():
            for label in labels:
                assert (table, label) not in out, (table, label)
                out[(table, label)] = clause
    return out


def test_s14_r28e_every_refusal_names_its_clause():
    """F1-7: the clause map covers every refusal row exactly once (and nothing else)."""
    mapped = _clause_of()
    rows = [(t, lab) for t, lab, _o in REFUSALS]
    assert len(rows) == len(set(rows)), "duplicate refusal ids"
    assert set(mapped) == set(rows), (sorted(set(rows) - set(mapped)), sorted(set(mapped) - set(rows)))


PLACEHOLDER_PROBES = [
    ("Dior", "Unknown"), ("Dior", "Unknown Product"), ("Dior", "This Product"), ("Dior", "Product"),
    ("Lattafa", "Unknown"),
]


@pytest.mark.parametrize("gate", [None, "true"])
@pytest.mark.parametrize("brand,name", PLACEHOLDER_PROBES, ids=["%s-%s" % p for p in PLACEHOLDER_PROBES])
def test_s14_r22c_placeholder_name_arm(prod_identity_env, monkeypatch, gate, brand, name):
    """F1-1 (R-A5): the name alone being a placeholder mints no id, and spine_key is never asked."""
    prod_identity_env(gate)
    kb = _kb()
    fn = _attr(kb, "kb_product_id")
    from app.services import result_gate, spec_spine_service

    assert result_gate.product_is_placeholder({"brand": brand, "name": name}) is True
    calls = []
    real = spec_spine_service.spine_key
    monkeypatch.setattr(spec_spine_service, "spine_key", lambda *a, **k: calls.append(a) or real(*a, **k))
    assert fn(brand, name) is None, (brand, name)
    assert calls == [], "a placeholder name must not reach spine_key"
    assert fn("Dior", "Sauvage EDP") == PID, "positive control"
    seen = []
    monkeypatch.setattr(result_gate, "product_is_placeholder", lambda p: seen.append(p) or False)
    assert fn(brand, name) is not None, "read result_gate.product_is_placeholder at CALL time"
    assert seen == [{"brand": brand, "name": name}]


VIEW_TEXT = (
    "CREATE OR REPLACE VIEW public.kb_offers_latest WITH (security_invoker = true) AS "
    "SELECT DISTINCT ON (o.variant_id, o.merchant_id, o.market, o.observed_currency) "
    "o.id, o.variant_id, o.merchant_id, o.market, o.amount, o.observed_currency, o.evidence_rung, o.size_ml, "
    "o.list_vs_sale, o.in_stock, o.first_seen, o.last_seen, o.captured_at, o.canonical_url "
    "FROM public.kb_offers AS o "
    "ORDER BY o.variant_id ASC, o.merchant_id ASC, o.market ASC, o.observed_currency ASC, " + OFFER_ORDER
)


def test_s14_r13b_view_text():
    """F1-2 (A13): the whole view as compact text: the DISTINCT ON key, the full ORDER BY and NO WHERE."""
    sql = _require(F045)
    views = [s for s in _statements(sql) if s.startswith("CREATE OR REPLACE VIEW public.kb_offers_latest ")]
    assert views == [VIEW_TEXT], views
    assert " WHERE " not in views[0]


CARD_TEXT = (
    "SELECT jsonb_build_object('product', to_jsonb(p.*), "
    "'variants', coalesce((SELECT jsonb_agg(to_jsonb(v.*) ORDER BY v.id) FROM public.kb_variants AS v "
    "WHERE v.product_id = p.id), '[]'::jsonb), "
    "'offers', coalesce((SELECT jsonb_agg(to_jsonb(l.*) ORDER BY l.variant_id, l.merchant_id, l.market, "
    "l.observed_currency) FROM (SELECT DISTINCT ON (" + OFFER_PARTITION + ") o.* FROM public.kb_offers AS o "
    "WHERE o.variant_id IN (SELECT v2.id FROM public.kb_variants AS v2 WHERE v2.product_id = p.id) "
    "ORDER BY " + OFFER_PARTITION + ", " + OFFER_ORDER + ") AS l), '[]'::jsonb), "
    "'images', coalesce((SELECT jsonb_agg(to_jsonb(i.*) ORDER BY i.captured_at DESC, i.id) "
    "FROM public.kb_images AS i WHERE i.product_id = p.id), '[]'::jsonb), "
    "'specs', coalesce((SELECT jsonb_agg(to_jsonb(s.*) ORDER BY s.field) FROM (SELECT DISTINCT ON (s0.field) s0.* "
    "FROM public.kb_specs AS s0 WHERE s0.product_id = p.id AND s0.cited AND s0.lang IN (p_lang, 'en') "
    "ORDER BY s0.field, (s0.lang = p_lang) DESC) AS s), '[]'::jsonb), "
    "'rating', (SELECT jsonb_build_object('sources', count(*), 'review_count', sum(r.review_count), "
    "'rating', round(sum(r.aggregate_rating * r.review_count) "
    "FILTER (WHERE r.aggregate_rating IS NOT NULL AND r.review_count IS NOT NULL) / nullif(sum(r.review_count) "
    "FILTER (WHERE r.aggregate_rating IS NOT NULL AND r.review_count IS NOT NULL), 0), 2)) "
    "FROM public.kb_reviews AS r WHERE r.product_id = p.id)) "
    "FROM public.kb_products AS p WHERE p.id = p_product_id"
)


def test_s14_r14b_card_subselects():
    """F1-2 (A11, A12): every card sub-select's correlation predicate, as the whole compact body; no
    stock or freshness filter (that is S81-18's reader contract)."""
    sql = _require(F045)
    body = _compact(_function_body(sql, "kb_product_card"))
    for pred in ("WHERE v.product_id = p.id", "WHERE v2.product_id = p.id", "WHERE i.product_id = p.id",
                 "WHERE s0.product_id = p.id AND s0.cited AND s0.lang IN (p_lang, 'en')",
                 "WHERE r.product_id = p.id", "WHERE p.id = p_product_id"):
        assert pred in body, pred
    for bad in ("in_stock", "now()", "interval", "last_seen >", "last_seen <", "captured_at >", "WHERE true"):
        assert bad not in body, bad
    assert body == CARD_TEXT


HEADER_OFFERS = (
    "Offers: captured_at is the first observation of one exact (variant, merchant, market, currency, amount, "
    "list_vs_sale) row and never moves. A re-observation upserts on kb_offers_observation and sets last_seen, "
    "in_stock, evidence_rung and canonical_url only; a changed amount is a NEW row. Latest = last_seen DESC, "
    "(list_vs_sale = 'sale') DESC, captured_at DESC, id DESC per (variant, merchant, market, currency): the "
    "R-S14-1 order last_seen DESC, captured_at DESC, id DESC with the sale key placed right after last_seen "
    "DESC, so among the rows last seen at the same instant the sale wins, then the newest capture (the sale is "
    "what the shopper pays, also when the list amount changed during the sale: F2-1); idx_kb_offers_latest "
    "carries the same key in the same position, and the prune ages rows by last_seen. The view and the card "
    "serve the latest row whatever its age or stock: freshness and stock filtering are S81-18's reader contract."
)


def test_s14_r19b_header_observation_paragraph():
    """F1-11 (E13): the 045 header's observation paragraph, verbatim (compact)."""
    h = " ".join(_sql.comment_lines(_require(F045)).split())
    assert HEADER_OFFERS in h, h[h.find("Offers:"):][:600]


# F2-4 (fix round 2): the last label carries a letter AND is not all digits or 0x-hex.
TOP_LABEL_RE = "^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)"


def test_s14_r25d_top_label_rule():
    """F1-6: every host (and URL host) carries a letter in its top-level label; one constant = the 045 text."""
    sql = _require(F045)
    kb = _kb()
    assert _attr(kb, "KB_HOST_TOP_LABEL_REGEX") == TOP_LABEL_RE
    cons = [c for c in _constraints(sql, "kb_merchants") if "host_top_label_letter" in c]
    assert cons == ["CONSTRAINT kb_merchants_host_top_label_letter CHECK (host ~ '%s')" % TOP_LABEL_RE], cons
    rx = _py(TOP_LABEL_RE)
    for bad in ("10.0.0.1", "shop.123", "1.2.3.4"):
        assert not rx.search(bad), bad
    for ok in ("shop.example", "4711.com", "163.com", "xn--caf-dma.example", "a.b-c"):
        assert rx.search(ok), ok
    canon = _attr(kb, "canonical_offer_url")
    assert canon("https://shop.123/p") is None
    assert canon("https://cdn.4711.com/p") == "https://cdn.4711.com/p"


def test_s14_r30_numeric_mirror():
    """F1-6 (M65, A2, A3): the builders round half away from zero, like PostgreSQL numeric."""
    kb = _kb()
    offer = _attr(kb, "build_offer_row")
    review = _attr(kb, "build_review_row")
    for raw, want in ((0.0005, "0.001"), (1.0025, "1.003"), (Decimal("29.9995"), "30.000"), (30, "30.000")):
        row = offer(**dict(_valid_kwargs("kb_offers"), amount=raw))
        assert row is not None and row["amount"] == want, (raw, row)
    for raw, want in ((4.985, "4.99"), (4.995, "5.00"), (0, "0.00"), (5, "5.00"), (5.0, "5.00")):
        row = review(**dict(_valid_kwargs("kb_reviews"), aggregate_rating=raw))
        assert row is not None and row["aggregate_rating"] == want, (raw, row)
    for raw in (5.001, -0.001, 5.005, 5.01):
        assert review(**dict(_valid_kwargs("kb_reviews"), aggregate_rating=raw)) is None, raw


def test_s14_r21b_source_router_read_inside_the_validator():
    """F1-3: source_router is imported only inside the registry validator (the leaf stays import-light)."""
    tree = ast.parse(LEAF.read_text(encoding="utf-8"))
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert not [n for n in top if "source_router" in ast.dump(n)], "no module-level source_router import"
    hits = []
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        for node in ast.walk(fn):
            if isinstance(node, ast.ImportFrom) and any(a.name == "source_router" for a in node.names):
                hits.append((fn.name, node.module, [a.asname for a in node.names]))
    assert hits == [("_registry_ok", "app.services", ["_sr"])], hits


def test_s14_r28f_registry_reads_source_fields_at_call_time(monkeypatch):
    """F1-3: the validator reads source_router.Source by module attribute at CALL time."""
    import dataclasses

    kb = _kb()
    build = _attr(kb, "build_merchant_row")
    from app.services import source_router

    entry = {"origin": "literal", "order": 0, "domain": "shop.example", "tier": "bahrain"}
    assert build(host="shop.example", updated_at=T0, registry=[entry]) is not None

    @dataclasses.dataclass(frozen=True)
    class _OnlyDomain:
        domain: str

    monkeypatch.setattr(source_router, "Source", _OnlyDomain)
    assert build(host="shop.example", updated_at=T0, registry=[entry]) is None, "tier is no longer a field"
    assert build(host="shop.example", updated_at=T0, registry=[{"origin": "literal", "order": 0,
                                                                 "domain": "shop.example"}]) is not None


def test_s14_r28g_registry_validator_contract():
    """F1-3: a bare entry is accepted (presence is S81-15's seed contract); present fields are typed."""
    kb = _kb()
    build = _attr(kb, "build_merchant_row")
    from app.services import source_router

    fields = set(source_router.Source.__dataclass_fields__)
    assert {"domain", "tier", "categories", "weight", "search_descriptor", "priority_rank"} <= fields
    for entries in ([{"origin": "literal", "order": 0}],
                    [{"origin": o, "order": i} for i, o in enumerate(("literal", "catalog", "operator", "discovery"))]):
        assert build(host="shop.example", updated_at=T0, registry=entries) is not None, entries
    two_noon = [{"origin": "literal", "order": 0, "domain": "noon.com"}, {"origin": "literal", "order": 1, "domain": "noon.com"}]
    assert build(host="noon.com", updated_at=T0, registry=two_noon) is not None
    assert build(host="shop.example", updated_at=T0, registry=two_noon) is None, "domain == host"


# ===========================================================================
# Fix round 2 (RULINGS_FIX2_S81_14, F2-1..F2-6): rows appended after the
# round-1 re-verifier on ee09729d. RED = fails on the pre-fix bytes (an
# AssertionError); PIN = green there and kills a named mutant.
# ===========================================================================

# F1-7 carried forward: the fix-round-2 refusal rows name their ONE clause; merged into
# REFUSAL_CLAUSES at import so r28e checks the union (the fix-round-1 literal is untouched).
_FIX2_CLAUSES = {
    "kb_merchants": {
        "registry.types": ("registry_bool_field_int",),
        "registry.domain_is_host": (
            "registry_domain_sibling", "registry_domain_apex_of_host", "registry_domain_non_ascii_fold",
        ),
        "merchants.host_top_label": ("host_hex_last_label", "host_hex_every_label", "host_hex_after_digits"),
    },
    "kb_offers": {
        "offers.canonical": (
            "url_hex_last_label", "url_hex_every_label", "url_hex_after_digits", "url_all_digit_host",
        ),
    },
    "kb_images": {
        "url.top_label": ("url_hex_last_label", "url_hex_every_label", "url_hex_after_digits"),
        "host.top_label": ("provenance_hex_last_label", "provenance_hex_every_label", "provenance_hex_after_digits"),
    },
    "kb_specs": {
        "url.top_label": ("source_hex_last_label", "source_hex_every_label", "source_hex_after_digits"),
    },
    "kb_reviews": {
        "url.top_label": ("source_url_hex_last_label", "source_url_hex_every_label", "source_url_hex_after_digits"),
    },
    "kb_gaps": {
        "host.top_label": ("hint_hex_last_label_host", "hint_hex_every_label_host", "hint_hex_after_digits_host"),
        "url.top_label": ("hint_hex_last_label_url", "hint_hex_every_label_url", "hint_hex_after_digits_url"),
    },
}
for _fx_table, _fx_clauses in _FIX2_CLAUSES.items():
    for _fx_clause, _fx_names in _fx_clauses.items():
        REFUSAL_CLAUSES[_fx_table][_fx_clause] = tuple(REFUSAL_CLAUSES[_fx_table].get(_fx_clause, ())) + _fx_names


# ---------------------------------------------------------------------------
# F2-1 (MAJ-1): the offer ranking as BEHAVIOUR. The ORDER BY lists are read from
# the 045 text and evaluated on Python rows (an unknown key fails), so the row
# goes red whenever the bytes rank captured_at before the sale key.
# ---------------------------------------------------------------------------

T_DAY = datetime(2026, 10, 24, 9, 0, tzinfo=timezone.utc)

_ORDER_GETTERS = {
    "o.variant_id": lambda r: r["variant_id"],
    "o.merchant_id": lambda r: r["merchant_id"],
    "o.market": lambda r: r["market"],
    "o.observed_currency": lambda r: r["observed_currency"],
    "o.last_seen": lambda r: r["last_seen"],
    "o.captured_at": lambda r: r["captured_at"],
    "(o.list_vs_sale = 'sale')": lambda r: r["list_vs_sale"] == "sale",
    "o.id": lambda r: uuid.UUID(r["id"]).int,  # PostgreSQL orders uuid bytewise = by its int
}


def _order_spec(order_by: str) -> list:
    spec = []
    for part in order_by.split(", "):
        m = re.fullmatch(r"(.+?)(?: (ASC|DESC))?", part.strip())
        assert m and m.group(1) in _ORDER_GETTERS, "unknown ORDER BY key %r in %r" % (part, order_by)
        spec.append((_ORDER_GETTERS[m.group(1)], m.group(2) == "DESC"))
    return spec


def _sorted_offers(rows: list, order_by: str) -> list:
    out = list(rows)
    for getter, desc in reversed(_order_spec(order_by)):
        out.sort(key=getter, reverse=desc)  # stable, so the keys compose like ORDER BY
    return out


def _offer_partition(r: dict) -> tuple:
    return (r["variant_id"], r["merchant_id"], r["market"], r["observed_currency"])


def _latest_offers(rows: list, order_by: str) -> list:
    seen, out = set(), []
    for r in _sorted_offers(rows, order_by):
        if _offer_partition(r) not in seen:
            seen.add(_offer_partition(r))
            out.append(r)
    return out


def _pruned_offers(rows: list, order_by: str, max_age_days: int, keep: int, now: datetime) -> list:
    rn: dict = {}
    kept = []
    for r in _sorted_offers(rows, order_by):
        rn[_offer_partition(r)] = rn.get(_offer_partition(r), 0) + 1
        if not (rn[_offer_partition(r)] > keep and r["last_seen"] < now - timedelta(days=max_age_days)):
            kept.append(r)
    return kept


def _offer_orders() -> dict:
    sql = _require(F045)
    views = [s for s in _statements(sql) if s.startswith("CREATE OR REPLACE VIEW public.kb_offers_latest ")]
    assert len(views) == 1, views
    card = re.search(r"FROM public\.kb_offers AS o WHERE .*? ORDER BY (.*?)\) AS l\)",
                     _compact(_function_body(sql, "kb_product_card")))
    prune = re.search(r"ORDER BY (.*?)\) AS rn", _compact(_function_body(sql, "kb_prune_offers")))
    assert card and prune, "no offer ORDER BY in the card or the prune"
    return {"view": views[0].split(" ORDER BY ", 1)[1], "card": card.group(1), "prune": prune.group(1)}


def _offer(id_int: int, amount: str, lvs: str, captured_days_ago: float, seen_days_ago: float) -> dict:
    return dict(
        variant_id=VID, merchant_id="shop.example", market="BH", observed_currency="BHD",
        id=str(uuid.UUID(int=id_int)), amount=amount, list_vs_sale=lvs,
        captured_at=T_DAY - timedelta(days=captured_days_ago), last_seen=T_DAY - timedelta(days=seen_days_ago),
    )


@pytest.mark.parametrize("where", ["view", "card", "prune"])
def test_s14_r31_sale_wins_among_rows_last_seen_together(where):
    """F2-1 (S-b): a sale 30 first seen 10 days ago and a list 55 in a NEWER row (the list amount changed
    during the sale), both last seen today: the view and the card serve the SALE and kb_prune_offers(1, 1)
    keeps it (the prune runs two days later). Among the rows last seen at the same instant the sale wins,
    then the newest capture."""
    order = _offer_orders()[where]
    sb = [
        _offer(1, "30.000", "sale", 10, 0),
        _offer(2, "50.000", "list", 10, 4),
        _offer(9, "55.000", "list", 4, 0),  # the larger id too, so an id fallback serves the list
    ]
    if where == "prune":
        kept = _pruned_offers(sb, order, 1, 1, T_DAY + timedelta(days=2))
        assert [r["amount"] for r in kept] == ["30.000"], [r["amount"] for r in kept]
        assert len(_pruned_offers(sb, order, 1, 1, T_DAY)) == 2, "today only the list 50 is old enough"
    else:
        assert [r["amount"] for r in _latest_offers(sb, order)] == ["30.000"], order
    # controls on the same key list (green on both byte sets)
    ended = [_offer(1, "30.000", "sale", 10, 1), _offer(2, "55.000", "list", 4, 0)]
    assert _sorted_offers(ended, order)[0]["amount"] == "55.000", "last_seen decides first: the sale ended"
    two_lists = [_offer(9, "40.000", "list", 5, 0), _offer(1, "45.000", "list", 1, 0)]
    assert _sorted_offers(two_lists, order)[0]["amount"] == "45.000", "then the newest capture"
    one_instant = [_offer(9, "50.000", "list", 1, 1), _offer(1, "30.000", "sale", 1, 1)]
    assert _sorted_offers(one_instant, order)[0]["amount"] == "30.000", "an exact tie serves the sale (S-a)"


# ---------------------------------------------------------------------------
# F2-4: one top-label belt on every host and URL column (SQL and the leaf)
# ---------------------------------------------------------------------------

TOP_LABEL_COLUMNS = [
    ("kb_merchants", "kb_merchants_host_top_label_letter", "host", "host", False),
    ("kb_offers", "kb_offers_url_top_label_letter", "canonical_url", "url", False),
    ("kb_images", "kb_images_url_top_label_letter", "url", "url", False),
    ("kb_images", "kb_images_provenance_top_label_letter", "provenance_host", "host", False),
    ("kb_specs", "kb_specs_source_top_label_letter", "source_url", "url", True),
    ("kb_reviews", "kb_reviews_source_top_label_letter", "source_url", "url", False),
    ("kb_gaps", "kb_gaps_hint_top_label_letter", "source_hint", "both", True),
]
NUMERIC_LAST_LABEL_HOSTS = ("127.0.0.0x1", "0x7f.0x0.0x0.0x1", "1.2.3.0x4", "10.0.0.1", "shop.123", "shop.0x")
LETTER_LAST_LABEL_HOSTS = ("shop.example", "4711.com", "163.com", "0xbeef.example", "shop.0xg", "a.b-c", "shop.1a")


@pytest.mark.parametrize("table,name,col,kind,nullable", TOP_LABEL_COLUMNS, ids=[c[1] for c in TOP_LABEL_COLUMNS])
def test_s14_r25e_top_label_belt_on_every_host_column(table, name, col, kind, nullable):
    """F2-4 (m3, m8): the SAME belt CHECK (the leaf's KB_HOST_TOP_LABEL_REGEX) on every host / URL column, so
    SQL refuses a last label that is all digits or 0x-hex (127.0.0.0x1, 0x7f.0x0.0x0.0x1, 1.2.3.0x4, 10.0.0.1)
    everywhere the leaf does; 4711.com and 163.com stay valid; the path never decides."""
    sql = _require(F045)
    cons = [c for c in _constraints(sql, table) if c.startswith("CONSTRAINT %s " % name)]
    lead = "%s IS NULL OR " % col if nullable else ""
    assert cons == ["CONSTRAINT %s CHECK (%s%s ~ '%s')" % (name, lead, col, TOP_LABEL_RE)], cons
    assert _attr(_kb(), "KB_HOST_TOP_LABEL_REGEX") == TOP_LABEL_RE
    rx = _py(TOP_LABEL_RE)
    forms = {"host": ("%s",), "url": ("https://%s/p",), "both": ("%s", "https://%s/p")}[kind]
    for form in forms:
        for h in NUMERIC_LAST_LABEL_HOSTS:
            assert not rx.search(form % h), form % h
        for h in LETTER_LAST_LABEL_HOSTS:
            assert rx.search(form % h), form % h
    if kind != "host":
        for url in ("https://10.0.0.1/x.abc", "http://127.0.0.0x1/a.b/c", "https://1.2.3.0x4/"):
            assert not rx.search(url), "a letter in the path must not rescue %s" % url


def test_s14_r25f_canonical_offer_url_refuses_numeric_last_labels():
    """F2-4: canonical_offer_url (and so every offer) refuses an all-digit or 0x-hex last label."""
    canon = _attr(_kb(), "canonical_offer_url")
    for h in NUMERIC_LAST_LABEL_HOSTS:
        for scheme in ("https", "http"):
            assert canon("%s://%s/p" % (scheme, h)) is None, h
    for h in LETTER_LAST_LABEL_HOSTS:
        assert canon("https://%s/p" % h) == "https://%s/p" % h, h
    assert canon("https://127.0.0.0X1/p") is None, "the host is lower-cased before the check"


# ---------------------------------------------------------------------------
# F2-5 (m4; R-A5): a placeholder BRAND mints no id either
# ---------------------------------------------------------------------------

PLACEHOLDER_BRANDS = [("Unknown", "Sauvage"), ("N/A", "Sauvage"), ("Unknown Brand", "Sauvage"), ("Product", "Sauvage")]


@pytest.mark.parametrize("gate", [None, "true"])
@pytest.mark.parametrize("brand,name", PLACEHOLDER_BRANDS, ids=["%s-%s" % p for p in PLACEHOLDER_BRANDS])
def test_s14_r22d_placeholder_brand_arm(prod_identity_env, monkeypatch, gate, brand, name):
    """F2-5: the house placeholder rule on the brand axis (the word "brand" dropped first), so 'brand
    unknown, name X' scans from different houses never share one juice id; the writers (S81-16 / S81-17)
    never pass a placeholder brand or name."""
    prod_identity_env(gate)
    kb = _kb()
    fn = _attr(kb, "kb_product_id")
    from app.services import result_gate, spec_spine_service

    calls = []
    real = spec_spine_service.spine_key
    monkeypatch.setattr(spec_spine_service, "spine_key", lambda *a, **k: calls.append(a) or real(*a, **k))
    assert fn(brand, name) is None, (brand, name)
    assert calls == [], "a placeholder brand must not reach spine_key"
    assert fn("Dior", name) == "fragrances|christian+dior|sauvage|-", "positive control"
    for real_brand in ("Brand Collection", "Generic", "No Brand"):
        assert fn(real_brand, name) is not None, "only a placeholder brand is refused: %s" % real_brand
    seen = []
    monkeypatch.setattr(result_gate, "is_placeholder_identity",
                        lambda text, site_title=None: seen.append(text) or False)
    assert fn(brand, name) is not None, "read result_gate.is_placeholder_identity at CALL time"
    assert brand in seen, seen
