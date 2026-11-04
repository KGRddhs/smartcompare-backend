"""S81-16b KB-BRANDS RED rows (spec S81-16b_UNIT_SPEC.md section 5 as amended by
the adversarial review and RULINGS_S81_16B R-S16B-1..R-S16B-16).

  B01-B12  migration 052 kb_brands + its rollback (R-S16B-1: 052, never 051)
  K01-K06  the kb_service census entry + build_brand_row
  S01-S12  scripts/seed_kb_brands_wikidata.py under its OWN flag ENABLE_KB_BRANDS
           (unset / false / dry -> OFF; true -> DRY; the exact word apply -> WRITE)
           and the knob KB_BRANDS_MAX (300, 1..5000)
  PIN-1..6 green at base, run with the FULL configuration present

Hermetic: the G2 harness (Rig / FakeClient / _merchant / _mod) is reused by
import of tests.test_s81_s16_kb_seed (module object only, so none of its rows is
collected twice); app.main is imported FIRST (the dotenv hazard); the
zero-network guard is installed per test; missing files and symbols are read
through _require / _attr / s16._mod so a base run fails on an AssertionError
only; synthetic brands and hosts; Arabic labels built from code points; no
key-shaped literal.
"""
import ast
import hashlib
import importlib
import importlib.util
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests import _retro_r_mig_sql as _sql
from tests import test_migration_043_delete_user_cascade as t043
from tests import test_migration_index_predicate_immutability as timm
from tests import test_s81_s16_kb_seed as s16

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / "migrations"
RB = MIG / "rollback"
F052 = MIG / "052_kb_brands.sql"
R052 = RB / "052_kb_brands.sql"
LEAF_MOD = "app.services.kb_service"
NOW = s16.NOW
T0 = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
IRI = "http://www.wikidata.org/entity/"
ROBOTS_OK = "User-agent: *\nAllow: /\n"

UNIT_ENV = ("ENABLE_KB_BRANDS", "KB_BRANDS_MAX", "ENABLE_KB_SEED", "ENABLE_LLM_SPEND_BREAKER",
            "ANTHROPIC_API_KEY") + s16.KNOBS

TEN_045 = ("kb_merchants", "kb_products", "kb_variants", "kb_offers", "kb_images",
           "kb_specs", "kb_reviews", "kb_gaps", "kb_feedback", "kb_coverage_daily")
BRAND_COLUMNS = ("qid", "label_en", "label_ar", "official_host", "source", "created_at", "updated_at")
BRAND_KEYS = ("qid", "label_en", "label_ar", "official_host", "source", "updated_at")
UPSERT_SET = ("label_en", "label_ar", "official_host", "updated_at")
QID_RE = "^Q[1-9][0-9]{0,11}$"
HOST_RE = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
TOP_RE = "^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)"
DENY_RE = "(^|[.])(basenotes|fimgs|fragrantica|parfumo)[.]"

#: The 052 column and constraint items, compact (spec 2.6 step 3 + R-S16B-6 btrim clauses).
EXPECTED_ITEMS = [
    "qid text PRIMARY KEY CHECK (qid ~ '" + QID_RE + "')",
    "label_en text NOT NULL CHECK (char_length(label_en) BETWEEN 1 AND 128 AND label_en = btrim(label_en))",
    "label_ar text CHECK (label_ar IS NULL OR (char_length(label_ar) BETWEEN 1 AND 128"
    " AND label_ar = btrim(label_ar)))",
    "official_host text CHECK (official_host IS NULL OR (char_length(official_host) BETWEEN 1 AND 253"
    " AND official_host ~ '" + HOST_RE + "' AND official_host !~ '" + DENY_RE + "'))",
    "source text NOT NULL DEFAULT 'wikidata' CHECK (source IN ('wikidata', 'operator'))",
    "created_at timestamptz NOT NULL DEFAULT now()",
    "updated_at timestamptz NOT NULL DEFAULT now()",
    "CONSTRAINT kb_brands_host_top_label_letter CHECK (official_host IS NULL OR official_host ~ '"
    + TOP_RE + "')",
]

#: The 045 census at base 0b19de5b (PIN-3).
COLUMNS_045 = {
    "kb_merchants": (
        "host", "country", "currency_hint", "platform", "platform_confidence", "adapter",
        "search_template", "registry", "robots", "politeness", "health", "challenge", "tos",
        "deny", "status", "blocked_reason", "partner", "created_at", "updated_at",
    ),
    "kb_products": (
        "id", "brand", "line", "name", "concentration", "audience", "identity_confidence",
        "created_at", "updated_at",
    ),
    "kb_variants": (
        "id", "product_id", "concentration", "size_ml", "gtin", "sku", "created_at", "updated_at",
    ),
    "kb_offers": (
        "id", "variant_id", "merchant_id", "market", "amount", "observed_currency",
        "evidence_rung", "size_ml", "list_vs_sale", "in_stock", "first_seen", "last_seen",
        "captured_at", "canonical_url",
    ),
    "kb_images": (
        "id", "product_id", "variant_id", "url", "provenance_host", "source", "captured_at",
    ),
    "kb_specs": (
        "id", "product_id", "field", "lang", "value", "source_url", "extractor", "model",
        "cited", "captured_at",
    ),
    "kb_reviews": (
        "id", "product_id", "source", "aggregate_rating", "review_count", "source_url",
        "captured_at",
    ),
    "kb_gaps": (
        "id", "product_key", "field", "demand_count", "first_seen", "last_seen", "state",
        "source_hint",
    ),
    "kb_feedback": (
        "id", "compare_request_id", "product_id", "field", "verdict", "device_key", "created_at",
    ),
    "kb_coverage_daily": ("day", "metric", "value", "n"),
}

#: LF sha256 of the 045 texts at base (spec 1.4).
SHA_045 = {
    "migrations/045_kb_core.sql": "ba853c75a98953e5ca40ba06ffd92fe3acf4a7f6ceb9c19ea5ffd7339f867075",
    "migrations/rollback/045_kb_core.sql": "4a7fcbabc946e5dfbea8e2180dfe8e7ceaa91a8afc439f803dac050eae9043ba",
}


def _ar(*codes):
    return "".join(chr(c) for c in codes)


AR1 = _ar(0x645, 0x64A, 0x632, 0x627, 0x646)
AR2 = _ar(0x639, 0x637, 0x631)
AR3 = _ar(0x645, 0x633, 0x643)


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://" + "kbbrands-test" + ".invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc" + "-" + "b" * 10)
    attempts = _sql.install_network_guard(monkeypatch)
    yield
    assert attempts == [], "S81-16b tests must not touch the network: %r" % attempts


def _lf(text):
    return text.replace("\r\n", "\n")


def _require(path):
    assert path.is_file(), "S81-16b: %s does not exist yet (RED until GREEN writes it)" % (
        path.relative_to(ROOT).as_posix())
    return _lf(path.read_text(encoding="utf-8"))


def _kb():
    spec = importlib.util.find_spec(LEAF_MOD)
    assert spec is not None, "app/services/kb_service.py missing"
    return importlib.import_module(LEAF_MOD)


def _attr(obj, name):
    assert hasattr(obj, name), "S81-16b: %s.%s is missing" % (getattr(obj, "__name__", obj), name)
    return getattr(obj, name)


def _brand_keys(kb):
    keys = _attr(kb, "KB_BUILDER_KEYS")
    assert "kb_brands" in keys, "KB_BUILDER_KEYS has no kb_brands entry"
    return keys["kb_brands"]


def _compact(text):
    s = " ".join(text.split())
    s = re.sub(r"\(\s+", "(", s)
    return re.sub(r"\s+\)", ")", s)


def _statements(sql):
    return [_compact(s) for s in _sql.code_only(sql).split(";") if s.strip()]


def _table_items(sql, table):
    clean = _sql.strip_line_comments(sql)
    m = re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+public\.%s\s*\(" % table, clean, re.I)
    assert m, "052 does not create public.%s" % table
    body = t043._balanced(clean, m.end() - 1)
    return [_compact(x) for x in t043._split_top(body)]


def _call(fn, argv, **kw):
    """main() with a SystemExit (argparse) turned into a value, so a base run
    fails on an AssertionError, never on the exit."""
    try:
        return fn(argv, **kw)
    except SystemExit as exc:
        return "SystemExit(%r)" % (exc.code,)


def _bind(qid, site=None, en=None, ar=None, mul=None, iri=True):
    b = {"brand": {"value": (IRI + qid) if iri else qid}}
    if site is not None:
        b["site"] = {"value": site}
    for key, value in (("label_en", en), ("label_ar", ar), ("label_mul", mul)):
        if value is not None:
            b[key] = {"value": value}
    return b


def _body(bindings):
    return json.dumps({"results": {"bindings": bindings}})


def _full(monkeypatch, mode, cap="50"):
    """The FULL unit configuration of a script row (B1)."""
    s16._set(monkeypatch, "ENABLE_KB_BRANDS", mode)
    monkeypatch.setenv("ENABLE_KB_SEED", "apply")
    s16._set(monkeypatch, "KB_BRANDS_MAX", cap)


def _run(monkeypatch, tmp_path, mode, bindings, cap="50", extra=(), returned=None, fail=None,
         name="brands.json"):
    common = s16._mod("kb_seed_common")
    brands = s16._mod("seed_kb_brands_wikidata")
    _full(monkeypatch, mode, cap)
    rig = s16.Rig(monkeypatch, common, merchants=[s16._merchant("store-a.example.com")], fail=fail)
    if returned is not None:
        rig.client.returned = returned
    rig.fetch_responses = [(200, {}, ROBOTS_OK), (200, {}, _body(bindings))]
    rep = tmp_path / name
    rc = _call(_attr(brands, "main"), ["--report", str(rep)] + list(extra), client=rig.client)
    report = s16._report(rep) if rep.is_file() else {}
    return rig, report, rc


def _get(report, key):
    assert key in report, "--report has no %r key (keys %r)" % (key, sorted(report))
    return report[key]


def _row(qid, en, ar=None, host=None):
    return {"qid": qid, "label_en": en, "label_ar": ar, "official_host": host, "source": "wikidata",
            "updated_at": NOW.isoformat()}


def _rep(qid, en, ar=None, host=None):
    return {"qid": qid, "label_en": en, "label_ar": ar, "official_host": host}


def _sparql_text(rig):
    from urllib.parse import parse_qs, urlsplit

    assert len(rig.fetches) == 2, "expected the robots GET and ONE SPARQL GET: %r" % (
        [f["url"] for f in rig.fetches])
    query = parse_qs(urlsplit(rig.fetches[1]["url"]).query).get("query", [""])[0]
    return query


# ===========================================================================
# B rows: migration 052 (R-S16B-1)
# ===========================================================================

def test_s16b_b01_files_exist_once():
    _require(F052)
    _require(R052)
    assert sorted(p.name for p in MIG.glob("052_*.sql")) == ["052_kb_brands.sql"]
    assert sorted(p.name for p in RB.glob("052_*.sql")) == ["052_kb_brands.sql"]
    assert not list(MIG.glob("051_*.sql")) and not list(RB.glob("051_*.sql")), "051 is S81-17b's (R-S16B-1)"


@pytest.mark.parametrize("path", [F052, R052], ids=["forward", "rollback"])
def test_s16b_b02_one_transaction(path):
    stmts = [s.lower() for s in _statements(_require(path))]
    assert stmts and stmts[0] == "begin" and stmts[-1] == "commit", (stmts[:1], stmts[-1:])
    assert stmts.count("begin") == 1 and stmts.count("commit") == 1
    assert "rollback" not in stmts


def test_s16b_b03_columns_match_the_leaf():
    items = _table_items(_require(F052), "kb_brands")
    assert items == EXPECTED_ITEMS, items
    names = [i.split()[0] for i in items if not i.upper().startswith("CONSTRAINT ")]
    kb = _kb()
    cols = _attr(kb, "KB_COLUMNS")
    assert "kb_brands" in cols, "KB_COLUMNS has no kb_brands entry"
    assert tuple(names) == tuple(cols["kb_brands"]) == BRAND_COLUMNS


def test_s16b_b04_regex_texts_equal_the_leaf():
    items = _table_items(_require(F052), "kb_brands")
    kb = _kb()
    by_name = {i.split()[0] if not i.upper().startswith("CONSTRAINT ") else i.split()[1]: i for i in items}
    assert set(by_name) >= {"qid", "official_host", "kb_brands_host_top_label_letter"}, sorted(by_name)
    qid_lits = re.findall(r"~\s*'((?:[^']|'')*)'", by_name["qid"])
    assert qid_lits == [_attr(kb, "KB_QID_REGEX")], qid_lits
    host = by_name["official_host"]
    assert re.findall(r"(?<!!)~\s*'((?:[^']|'')*)'", host) == [kb.KB_HOST_REGEX]
    assert re.findall(r"!~\s*'((?:[^']|'')*)'", host) == [kb.kb_host_deny_regex()]
    top = re.findall(r"~\s*'((?:[^']|'')*)'", by_name["kb_brands_host_top_label_letter"])
    assert top == [kb.KB_HOST_TOP_LABEL_REGEX], top
    assert "label_en = btrim(label_en)" in by_name["label_en"]
    assert "label_ar IS NULL OR" in by_name["label_ar"] and "label_ar = btrim(label_ar)" in by_name["label_ar"]


def test_s16b_b05_service_role_only():
    stmts = [s.lower() for s in _statements(_require(F052))]
    rls = "alter table public.kb_brands enable row level security"
    revoke = "revoke all on table public.kb_brands from public, anon, authenticated, service_role"
    grant = "grant select, insert, update, delete on table public.kb_brands to service_role"
    for want in (rls, revoke, grant):
        assert stmts.count(want) == 1, want
    assert stmts.index(revoke) < stmts.index(grant)
    grants = [s for s in stmts if s.startswith("grant ")]
    assert grants == [grant], grants
    joined = " ".join(stmts)
    assert "create policy" not in joined and "security definer" not in joined
    assert "create function" not in joined and "create or replace function" not in joined
    assert not re.search(r"\bto\s+(public|anon|authenticated)\b", joined)


def test_s16b_b06_trigger_and_045_guard():
    sql = _require(F052)
    stmts = _statements(sql)
    trig = ("CREATE OR REPLACE TRIGGER kb_brands_set_updated_at BEFORE UPDATE ON public.kb_brands "
            "FOR EACH ROW EXECUTE FUNCTION public.kb_set_updated_at()")
    assert stmts.count(trig) == 1, [s for s in stmts if "TRIGGER" in s.upper()]
    clean = _sql.strip_line_comments(sql)
    m = re.search(r"\bDO\s+\$\$(.*?)\$\$", clean, re.S)
    assert m, "052 has no DO $$ ... $$ guard"
    body = " ".join(m.group(1).split())
    assert "to_regprocedure('public.kb_set_updated_at()') IS NULL" in body
    assert "RAISE EXCEPTION '052 " in body, body
    ct = re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+public\.kb_brands", clean)
    assert ct and m.start() < ct.start(), "the 045 guard must run before the CREATE TABLE"


def test_s16b_b07_host_index_not_unique():
    sql = _require(F052)
    stmts = _statements(sql)
    idx = ("CREATE INDEX IF NOT EXISTS idx_kb_brands_official_host ON public.kb_brands (official_host) "
           "WHERE official_host IS NOT NULL")
    assert stmts.count(idx) == 1, [s for s in stmts if "INDEX" in s.upper()]
    code = " ".join(stmts).upper()
    assert "UNIQUE" not in code, "official_host is NOT unique (spec Q3)"
    preds = timm._index_predicates(sql)
    assert len(preds) == 1, preds
    assert [timm._volatile_hits(p) for _s, p in preds] == [[]]


def test_s16b_b08_no_personal_column_no_fk():
    sql = _require(F052)
    names = [i.split()[0] for i in _table_items(sql, "kb_brands") if not i.upper().startswith("CONSTRAINT ")]
    hits = [n for n in names if t043.PERSONAL_RX.search(n) or t043.USER_REF_ID_RX.search(n)]
    assert hits == [], hits
    assert "REFERENCES" not in _sql.code_only(sql).upper()
    files = t043.real_forward_files()
    assert "052_kb_brands.sql" in [n for n, _t in files], "the 043 fence must see 052"
    assert t043._all_gaps(t043.fence_report(files)) == set()
    assert set(t043.fence_user_tables(files)) == set(t043.KNOWN_USER_TABLES)


def test_s16b_b09_rollback_statements():
    sql = _require(R052)
    assert _statements(sql) == ["BEGIN", "DROP TABLE IF EXISTS public.kb_brands", "COMMIT"]
    assert "kb_set_updated_at" not in _sql.code_only(sql)


def test_s16b_b10_headers():
    fwd = _require(F052)
    rb = _require(R052)
    head = _sql.norm(_sql.header_of(fwd))
    for phrase in ("s81-16b", "rollback/052_kb_brands.sql", "service role", "cc0", "after 045",
                   "enable_kb_brands", "not unique", "(p31 q5)", "merging this changes nothing in production"):
        assert phrase in head, phrase
    rhead = _sql.norm(_sql.header_of(rb))
    for phrase in ("before any rollback of 045", "enable_kb_brands"):
        assert phrase in rhead, phrase
    assert "051" not in fwd and "051" not in rb, "a leftover 051 (R-S16B-1)"


@pytest.mark.parametrize("path", [F052, R052], ids=["forward", "rollback"])
def test_s16b_b11_ascii_and_sqlfluff_clean(path):
    _require(path)
    raw = path.read_bytes()
    assert all(b < 128 for b in raw), "non-ASCII byte"
    text = raw.decode("ascii").replace("\r\n", "\n")
    assert not re.search(r"\d{8}", text), "an 8-digit run"
    from sqlfluff.core import FluffConfig, Linter

    linter = Linter(config=FluffConfig.from_path(str(ROOT)))
    res = linter.lint_string(text, fname=path.relative_to(ROOT).as_posix())
    bad = [(v.rule_code(), v.line_no) for v in res.get_violations()]
    assert bad == [], bad


def test_s16b_b12_kb_brands_literal_census():
    allowed = 'KB_BRANDS_TABLE = "kb_brands"'
    offenders, common_hits = [], []
    for top in ("app", "scripts"):
        for path in sorted((ROOT / top).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value == "kb_brands":
                    if rel == "app/services/kb_service.py":
                        continue
                    line = lines[node.lineno - 1].strip()
                    if rel == "scripts/kb_seed_common.py" and line == allowed:
                        common_hits.append(node.lineno)
                        continue
                    offenders.append("%s:%d" % (rel, node.lineno))
    assert offenders == [], offenders
    assert len(common_hits) == 1, "scripts/kb_seed_common.py needs exactly one %r line" % allowed


# ===========================================================================
# K rows: the leaf
# ===========================================================================

def test_s16b_k01_census_constants():
    kb = _kb()
    tables = tuple(_attr(kb, "KB_TABLES"))
    assert tables[-1] == "kb_brands" and tables[:-1] == TEN_045, tables
    assert tuple(_attr(kb, "KB_COLUMNS").get("kb_brands", ())) == BRAND_COLUMNS
    assert tuple(_brand_keys(kb)) == BRAND_KEYS
    assert "kb_brands" not in kb.KB_UUID_ID_TABLES
    assert tuple(_attr(kb, "KB_BRAND_SOURCES")) == ("wikidata", "operator")
    assert tuple(_attr(kb, "KB_BRAND_UPSERT_SET")) == UPSERT_SET
    assert _attr(kb, "KB_QID_REGEX") == QID_RE


def _host_of(n):
    """A valid-shape host of exactly ``n`` chars (labels <= 63; built at run time)."""
    labels, left = [], n
    while left > 64:
        labels.append("a" * 63)
        left -= 64
    labels.append("d" * left)
    host = ".".join(labels)
    assert len(host) == n
    return host


K02_CASES = {
    "minimal": dict(qid="Q42", label_en="Maison Example"),
    "with_host": dict(qid="Q42", label_en="Maison Example", official_host="brand-b.example.com"),
    "arabic_label": dict(qid="Q7", label_en="Maison Example", label_ar=AR1),
    "label_128": dict(qid="Q42", label_en="L" * 128, label_ar="m" * 128),
    "qid_12_digits": dict(qid="Q" + "9" * 12, label_en="Maison Example"),
    "source_operator": dict(qid="Q42", label_en="Maison Example", source="operator"),
    "host_253": dict(qid="Q42", label_en="Maison Example", official_host="@253"),
}


@pytest.mark.parametrize("case", sorted(K02_CASES))
def test_s16b_k02_builder_accepts(case):
    kb = _kb()
    build = _attr(kb, "build_brand_row")
    kw = dict(K02_CASES[case])
    if kw.get("official_host") == "@253":
        kw["official_host"] = _host_of(253)
    row = build(updated_at=T0, **kw)
    assert isinstance(row, dict), row
    assert set(row) == set(_brand_keys(kb))
    assert row["updated_at"] == T0.isoformat()
    want = {"label_ar": None, "official_host": None, "source": "wikidata"}
    want.update(kw)
    for key, value in want.items():
        assert row[key] == value, key


def _deny_label():
    from app.services import deny_hosts as dh

    return sorted(dh.DENY_LABELS)[0]


def _deny_host():
    from app.services import deny_hosts as dh

    return dh.DENY_HOSTS[0]


K03_CASES = [
    ("qid-Q0", {"qid": "Q0"}), ("qid-Q01", {"qid": "Q01"}), ("qid-lower", {"qid": "q42"}),
    ("qid-bare-Q", {"qid": "Q"}), ("qid-13-digits", {"qid": "@q13"}), ("qid-trailing-space", {"qid": "Q42 "}),
    ("qid-trailing-newline", {"qid": "Q42\n"}), ("qid-int", {"qid": 42}),
    ("label_en-none", {"label_en": None}), ("label_en-empty", {"label_en": ""}),
    ("label_en-129", {"label_en": "x" * 129}), ("label_en-nul", {"label_en": "Mai\x00son"}),
    ("label_en-surrogate", {"label_en": "Mai\ud800son"}), ("label_en-lead-space", {"label_en": " Maison"}),
    ("label_en-trail-space", {"label_en": "Maison "}), ("label_en-blank", {"label_en": " "}),
    ("label_ar-empty", {"label_ar": ""}), ("label_ar-129", {"label_ar": "y" * 129}),
    ("label_ar-nul", {"label_ar": "a\x00b"}), ("label_ar-lead-space", {"label_ar": " Maison"}),
    ("label_ar-trail-space", {"label_ar": "Maison "}), ("label_ar-blank", {"label_ar": " "}),
    ("host-upper", {"official_host": "Brand.Example.com"}), ("host-single-label", {"official_host": "brand"}),
    ("host-ipv4", {"official_host": "192.0.2.10"}), ("host-hex-top", {"official_host": "127.0.0.0x1"}),
    ("host-www-deny", {"official_host": "@www-deny"}), ("host-deny", {"official_host": "@deny"}),
    ("host-rule-only", {"official_host": "@rule-only"}), ("host-path", {"official_host": "brand.example.com/x"}),
    ("host-254", {"official_host": "@254"}),
    ("source-manual", {"source": "manual"}), ("source-none", {"source": None}),
    ("updated_at-naive", {"updated_at": datetime(2026, 11, 4, 12, 0)}),
    ("updated_at-str", {"updated_at": "2026-11-04T12:00:00+00:00"}),
]


def _materialise(value):
    if value == "@q13":
        return "Q" + "1" * 13
    if value == "@www-deny":
        return "www." + _deny_host()
    if value == "@deny":
        return _deny_host()
    if value == "@rule-only":
        return _deny_label() + "-shop.example.com"
    if value == "@254":
        return _host_of(254)
    return value


@pytest.mark.parametrize("case,override", K03_CASES, ids=[c for c, _o in K03_CASES])
def test_s16b_k03_builder_refuses(case, override):
    kb = _kb()
    build = _attr(kb, "build_brand_row")
    kw = dict(qid="Q42", label_en="Maison Example", label_ar=AR1, official_host="brand-b.example.com",
              source="wikidata", updated_at=T0)
    assert build(**kw) is not None, "the base row of K03 must be accepted"
    kw.update({k: _materialise(v) for k, v in override.items()})
    assert build(**kw) is None, case


def test_s16b_k04_belt_holds_without_the_rule(monkeypatch):
    kb = _kb()
    build = _attr(kb, "build_brand_row")
    from app.services import deny_hosts as dh

    monkeypatch.setattr(dh, "kb_source_allowed", lambda v: True)
    base = dict(qid="Q42", label_en="Maison Example", updated_at=T0)
    assert build(official_host="www." + _deny_host(), **base) is None, "the 052 belt"
    row = build(official_host=_deny_label() + "-shop.example.com", **base)
    assert row is not None and row["official_host"] == _deny_label() + "-shop.example.com"


def test_s16b_k05_rule_read_at_call_time(monkeypatch):
    kb = _kb()
    build = _attr(kb, "build_brand_row")
    from app.services import deny_hosts as dh

    seen = []

    def rule(v):
        seen.append(v)
        return False
    monkeypatch.setattr(dh, "kb_source_allowed", rule)
    base = dict(qid="Q42", label_en="Maison Example", updated_at=T0)
    assert build(official_host="brand-b.example.com", **base) is None
    assert seen == ["brand-b.example.com"]
    del seen[:]
    assert build(**base) is not None
    assert seen == []


def test_s16b_k06_never_raises_on_junk():
    kb = _kb()
    build = _attr(kb, "build_brand_row")
    junk = object()
    assert build(qid=junk, label_en=junk, updated_at=junk, label_ar=junk, official_host=junk, source=junk) is None
    for bad in ({"a": 1}, ["Maison"], b"Maison", 7):
        assert build(qid="Q42", label_en=bad, updated_at=T0) is None
        assert build(qid="Q42", label_en="Maison", label_ar=bad, updated_at=T0) is None


# ===========================================================================
# S rows: the script (every row: the full configuration + the G2 Rig recorders)
# ===========================================================================

@pytest.mark.parametrize("value,expected", s16.MODE_TABLE)
def test_s16b_s01_flag_constant_and_table(monkeypatch, value, expected):
    common = s16._mod("kb_seed_common")
    brands = s16._mod("seed_kb_brands_wikidata")
    assert _attr(brands, "FLAG") == "ENABLE_KB_BRANDS"
    monkeypatch.setenv("ENABLE_KB_SEED", "apply")
    monkeypatch.setenv("KB_BRANDS_MAX", "5")
    s16._set(monkeypatch, "ENABLE_KB_BRANDS", value)
    assert common.run_mode(brands.FLAG) == expected


@pytest.mark.parametrize("kb_seed", ["apply", "true", None], ids=["seed-apply", "seed-true", "seed-unset"])
@pytest.mark.parametrize("value", s16.OFF_SPELLINGS + ["dry"])
def test_s16b_s02_off_is_inert(monkeypatch, tmp_path, caplog, value, kb_seed):
    common = s16._mod("kb_seed_common")
    brands = s16._mod("seed_kb_brands_wikidata")
    rig = s16.Rig(monkeypatch, common, merchants=[s16._merchant("store-a.example.com")])
    rig.fetch_responses = [(200, {}, ROBOTS_OK), (200, {}, _body([_bind("Q2", "https://x.example.com/", en="X")]))]
    s16._set(monkeypatch, "ENABLE_KB_BRANDS", value)
    s16._set(monkeypatch, "ENABLE_KB_SEED", kb_seed)
    monkeypatch.setenv("KB_BRANDS_MAX", "5")
    rep = tmp_path / "off.json"
    import builtins

    real_open = builtins.open

    def _open(file, *a, **k):
        if str(rep) in str(file):
            rig.opened.append(str(file))
        return real_open(file, *a, **k)
    monkeypatch.setattr(builtins, "open", _open)
    caplog.set_level(logging.INFO)
    rc = _call(_attr(brands, "main"), ["--corpus", str(tmp_path), "--report", str(rep)])
    assert rc == 0, rc
    recs = s16._records(caplog)
    assert len(recs) == 1 and recs[0].levelno == logging.INFO, [r.getMessage() for r in recs]
    msg = recs[0].getMessage()
    assert "ENABLE_KB_BRANDS" in msg and "ENABLE_KB_SEED" in msg, msg
    assert rig.client_factory_calls == [] and rig.fetches == [] and rig.validates == []
    assert rig.sleeps == [] and rig.opened == [] and rig.events == [] and rig.client.executed == []
    assert not rep.exists()


S03_BINDINGS = [
    _bind("Q2", "https://two-a.example.com/", en="Two Sites", ar=AR1),
    _bind("Q2", "https://two-b.example.com/", en="Two Sites", ar=AR1),
    _bind("Q3", "https://three.example.com/", en="No Arabic"),
    _bind("Q4", "https://four.example.com/", mul="Mul Only", ar=AR2),
    _bind("Q5", "https://five.example.com/"),
]


def test_s16b_s03_dry_counts_no_write(monkeypatch, tmp_path, caplog):
    from app.services import robots_registry as rr

    caplog.set_level(logging.INFO)
    rig, report, rc = _run(monkeypatch, tmp_path, "true", S03_BINDINGS)
    assert rc == 0, rc
    query = _sparql_text(rig)
    assert rig.fetches[0]["url"] == "https://query.wikidata.org/robots.txt"
    assert rig.fetches[1]["url"].startswith("https://query.wikidata.org/sparql?")
    assert rig.validates == [f["url"] for f in rig.fetches]
    assert all(f["headers"] == rr._REQUEST_HEADERS and f["allow_redirects"] is False for f in rig.fetches)
    for clause in ("?label_en", "?label_ar", "?label_mul",
                   'OPTIONAL { ?brand rdfs:label ?label_en . FILTER(LANG(?label_en) = "en") }',
                   'OPTIONAL { ?brand rdfs:label ?label_mul . FILTER(LANG(?label_mul) = "mul") }',
                   'OPTIONAL { ?brand rdfs:label ?label_ar . FILTER(LANG(?label_ar) = "ar") }',
                   "FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 . }",
                   'ORDER BY xsd:integer(STRAFTER(STR(?brand), "/entity/Q")) ?site',
                   "LIMIT 2000", "?brand wdt:P1056 wd:Q131746 .", "?brand wdt:P856 ?site ."):
        assert clause in query, clause
    assert rig.client.writes() == []
    assert _get(report, "brands") == [
        _rep("Q2", "Two Sites", AR1, "two-a.example.com"),
        _rep("Q3", "No Arabic", None, "three.example.com"),
        _rep("Q4", "Mul Only", AR2, "four.example.com"),
    ]
    assert _get(report, "hosts") == ["five.example.com", "four.example.com", "three.example.com",
                                     "two-a.example.com", "two-b.example.com"]
    assert _get(report, "counts") == {"bindings": 5, "with_site": 5, "new": 5, "with_label_en": 2,
                                      "with_label_ar": 2, "label_en_from_mul": 1, "no_label_en": 1,
                                      "brand_rows": 3}
    totals = [r for r in s16._records(caplog) if "totals" in r.getMessage()]
    assert len(totals) == 1 and totals[0].levelno == logging.INFO


def _s04_fixture():
    bindings = [
        _bind("Q9", "https://brand-b.example.com/", mul="Mul Brand", ar=AR2),
        _bind("Q3", "https://zeta.example.com/", en="Maison Alpha", ar=AR1),
        _bind("Q3", "https://alpha.example.com/x", en="Maison Alpha", ar=AR1),
        _bind("Q5", "https://store-a.example.com/", en="Store Brand"),
        _bind("Q7", "http://192.0.2.10/", en="Ip Brand"),
    ]
    expected = [
        _row("Q3", "Maison Alpha", AR1, "alpha.example.com"),
        _row("Q5", "Store Brand", None, "store-a.example.com"),
        _row("Q7", "Ip Brand", None, None),
        _row("Q9", "Mul Brand", AR2, "brand-b.example.com"),
    ]
    for n in range(1100, 999, -1):
        bindings.append(_bind("Q%d" % n, "https://filler-%d.example.net/" % n, en="Filler %d" % n))
    for n in range(1000, 1101):
        expected.append(_row("Q%d" % n, "Filler %d" % n, None, "filler-%d.example.net" % n))
    return bindings, expected


@pytest.mark.parametrize("dry_run", [False, True], ids=["apply", "apply-dry-run"])
def test_s16b_s04_apply_writes_kb_brands_only(monkeypatch, tmp_path, dry_run):
    bindings, expected = _s04_fixture()
    rig, report, rc = _run(monkeypatch, tmp_path, "apply", bindings, cap="500",
                           extra=["--dry-run"] if dry_run else [])
    assert rc == 0, rc
    want_report = [{k: r[k] for k in ("qid", "label_en", "label_ar", "official_host")} for r in expected]
    assert _get(report, "brands") == want_report
    writes = rig.client.writes()
    if dry_run:
        assert writes == []
        return
    assert [(w[0], w[1]) for w in writes] == [("kb_brands", "upsert"), ("kb_brands", "upsert")], [
        (w[0], w[1]) for w in writes]
    assert [len(w[2]) for w in writes] == [100, 5]
    assert all(w[3] == {"on_conflict": "qid", "ignore_duplicates": True} for w in writes), [w[3] for w in writes]
    sent = [row for w in writes for row in w[2]]
    assert sent == expected
    counts = _get(report, "counts")
    assert counts.get("kb_brands_sent") == 105 and counts.get("brand_rows") == 105
    assert "brand_updates" not in counts and "write_failed" not in counts


def _s05_bindings():
    return [_bind("Q6", "https://six.example.com/", en="Six"),
            _bind("Q2", "https://two.example.com/", en="Two", ar=AR3),
            _bind("Q4", "http://192.0.2.10/", en="Four")]


@pytest.mark.parametrize("case", ["none-returned", "two-returned"])
def test_s16b_s05_rerun_updates_wikidata_rows_only(monkeypatch, tmp_path, case):
    returned = (lambda q, rows: []) if case == "none-returned" else (lambda q, rows: rows[:2])
    rig, report, rc = _run(monkeypatch, tmp_path, "apply", _s05_bindings(), returned=returned)
    assert rc == 0, rc
    expected = [_row("Q2", "Two", AR3, "two.example.com"), _row("Q4", "Four", None, None),
                _row("Q6", "Six", None, "six.example.com")]
    upserts = [q for q in rig.client.executed if q.kind() == "upsert"]
    assert len(upserts) == 1 and upserts[0].table == "kb_brands"
    updates = [q for q in rig.client.executed if q.kind() == "update"]
    want = expected if case == "none-returned" else expected[2:]
    assert [q.table for q in updates] == ["kb_brands"] * len(want)
    for q, row in zip(updates, want):
        (args, kwargs), = q.arg("update")
        assert tuple(args[0]) == UPSERT_SET, tuple(args[0])
        assert args[0] == {k: row[k] for k in UPSERT_SET}
        assert [a for a, _k in q.arg("eq")] == [("qid", row["qid"]), ("source", "wikidata")]
    kinds = [q.kind() for q in rig.client.executed]
    assert "delete" not in kinds and "insert" not in kinds
    assert _get(report, "counts").get("brand_updates") == len(want)


def test_s16b_s06_dedupe_and_host_choice(monkeypatch, tmp_path):
    from app.services import deny_hosts as dh

    bindings = [
        _bind("Q7", "https://zeta.example.com/", en="Seven"),
        _bind("Q7", "https://alpha.example.com/", en="Seven"),
        _bind("Q8", "https://www.%s/" % dh.DENY_HOSTS[0], en="Eight"),
        _bind("Q8", "http://192.0.2.10/", en="Eight"),
        _bind("Q9", "https://nine.example.com/", ar=AR1),
        _bind("Q10", "https://ten.example.com/", en="Ten", ar=chr(0x627) * 129),
        _bind("Q11", "https://eleven.example.com/", en="  Maison Example  "),
        _bind("Q01", "https://zero.example.com/", en="Zero"),
        _bind("Q12", "https://store-a.example.com/", en="Twelve"),
        _bind("Q13", "https://thirteen.example.com/", mul="Mul Thirteen"),
        _bind("Q14", "https://fourteen.example.com/", en="x" * 129),
        _bind("Q15", "https://fifteen.example.com/", en="Fifteen", ar="  " + AR1 + "  "),
    ]
    rig, report, rc = _run(monkeypatch, tmp_path, "true", bindings)
    assert rc == 0, rc
    assert _get(report, "brands") == [
        _rep("Q7", "Seven", None, "alpha.example.com"),
        _rep("Q8", "Eight", None, None),
        _rep("Q10", "Ten", None, "ten.example.com"),
        _rep("Q11", "Maison Example", None, "eleven.example.com"),
        _rep("Q12", "Twelve", None, "store-a.example.com"),
        _rep("Q13", "Mul Thirteen", None, "thirteen.example.com"),
        _rep("Q15", "Fifteen", AR1, "fifteen.example.com"),
    ]
    counts = _get(report, "counts")
    got = {k: counts.get(k) for k in ("bad_qid", "no_label_en", "label_ar_dropped", "brand_host_null",
                                      "label_en_from_mul", "brand_rows", "existing")}
    assert got == {"bad_qid": 1, "no_label_en": 2, "label_ar_dropped": 1, "brand_host_null": 1,
                   "label_en_from_mul": 1, "brand_rows": 7, "existing": 1}, got
    assert rig.client.writes() == []


def test_s16b_s07_cap_and_order(monkeypatch, tmp_path):
    qids = [2, 10, 3, 100, 25, 4, 11, 9, 30, 1000, 5, 12]
    bindings = [_bind("Q%d" % n, "https://cap-%d.example.com/" % n, en="Cap %d" % n) for n in qids]
    rig, report, rc = _run(monkeypatch, tmp_path, "apply", bindings, cap="5")
    assert rc == 0, rc
    sent = [row["qid"] for w in rig.client.writes() for row in w[2]]
    assert sent == ["Q2", "Q3", "Q4", "Q5", "Q9"], sent
    counts = _get(report, "counts")
    assert counts.get("over_cap_brands") == 7 and counts.get("brand_rows") == 5, counts
    assert _get(report, "hosts") == sorted("cap-%d.example.com" % n for n in qids)
    assert [b["qid"] for b in _get(report, "brands")] == sent


@pytest.mark.parametrize("value,expected", [
    (None, 300), ("", 300), ("garbage", 300), ("inf", 300), ("nan", 300), ("-5", 300), ("0", 300),
    ("7", 7), ("7.9", 7), ("9000", 5000), (" 12 ", 12), ("1", 1)])
def test_s16b_s08_knob_table(monkeypatch, value, expected):
    brands = s16._mod("seed_kb_brands_wikidata")
    monkeypatch.setenv("ENABLE_KB_BRANDS", "apply")
    monkeypatch.setenv("ENABLE_KB_SEED", "apply")
    s16._set(monkeypatch, "KB_BRANDS_MAX", value)
    assert _attr(brands, "brands_max")() == expected
    assert _attr(brands, "MAX_KNOB") == "KB_BRANDS_MAX"


def test_s16b_s09_limit_hit_count(monkeypatch, tmp_path):
    def many(n):
        return [_bind("Q%d" % (i + 1), "https://b%d.example.com/" % i, en="B %d" % i) for i in range(n)]

    rig, report, rc = _run(monkeypatch, tmp_path, "true", many(2000), cap="5", name="a.json")
    assert rc == 0, rc
    counts = _get(report, "counts")
    assert counts.get("sparql_limit_hit") == 1 and counts.get("bindings") == 2000, counts
    assert _attr(s16._mod("seed_kb_brands_wikidata"), "SPARQL_LIMIT") == 2000
    rig2, report2, rc2 = _run(monkeypatch, tmp_path, "true", many(1999), cap="5", name="b.json")
    assert rc2 == 0
    counts2 = _get(report2, "counts")
    assert "sparql_limit_hit" not in counts2 and counts2.get("brand_rows") == 5, counts2


@pytest.mark.parametrize("where", ["upsert", "update"])
def test_s16b_s10_write_failure_is_quiet(monkeypatch, tmp_path, caplog, where):
    caplog.set_level(logging.INFO)
    returned = (lambda q, rows: []) if where == "update" else None
    rig, report, rc = _run(monkeypatch, tmp_path, "apply", _s05_bindings(), returned=returned,
                           fail=lambda q: q.kind() == where)
    assert rc == 0, rc
    recs = s16._records(caplog)
    warns = [r for r in recs if r.levelno == logging.WARNING]
    assert len(warns) == 1, [r.getMessage() for r in warns]
    msg = warns[0].getMessage()
    assert "kb_brands write failed" in msg and "RuntimeError" in msg, msg
    assert not [r for r in recs if "db-failure" in r.getMessage()]
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
    counts = _get(report, "counts")
    assert counts.get("write_failed") == 1, counts
    assert counts.get("kb_brands_sent", 0) == (3 if where == "update" else 0), counts
    assert counts.get("brand_updates", 0) == 0
    assert len(_get(report, "brands")) == 3
    assert [r for r in recs if r.levelno == logging.INFO and "totals" in r.getMessage()]


def test_s16b_s11_no_label_or_host_in_logs(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    labels = ["Sentinel" + "Zq" + str(i) for i in range(3)]
    arabic = _ar(0x633, 0x646, 0x62A) + "Zq"
    hosts = ["sentinel-%d-zq.example.com" % i for i in range(3)]
    bindings = [_bind("Q%d" % (i + 2), "https://%s/" % h, en=lab, ar=arabic if i == 0 else None)
                for i, (lab, h) in enumerate(zip(labels, hosts))]
    rig, report, rc = _run(monkeypatch, tmp_path, "apply", bindings)
    assert rc == 0, rc
    needles = labels + [arabic] + hosts + ["rdfs:label", "SELECT", "wikidata.org/entity"]
    for r in s16._records(caplog):
        blob = r.getMessage() + " " + repr(r.args)
        assert not [n for n in needles if n in blob], blob
    got = _get(report, "brands")
    assert [b["label_en"] for b in got] == labels and got[0]["label_ar"] == arabic
    raw = (tmp_path / "brands.json").read_bytes()
    assert all(b < 128 for b in raw)


def test_s16b_s12_script_hygiene():
    for name in ("seed_kb_brands_wikidata", "kb_seed_common"):
        path = ROOT / "scripts" / (name + ".py")
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        assert b"\r" not in raw and all(b < 128 for b in raw), name
        text = raw.decode("ascii")
        assert "impersonate" not in text
        assert ("Qaren" + "Bot") not in text and ("NAMED" + "_AGENT") not in text
        assert ("claude" + "-") not in text and ("/v1/" + "messages") not in text
        tree = ast.parse(text)
        in_except = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                in_except.update(id(n) for n in ast.walk(node))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "error"
                    and isinstance(node.func.value, ast.Name) and node.func.value.id in ("logger", "logging")):
                assert id(node) in in_except, "%s:%d logs ERROR outside an except arm" % (name, node.lineno)
        if name == "seed_kb_brands_wikidata":
            assert not re.search(r"\.table\(\s*[\"']", text)
            doc = ast.get_docstring(tree) or ""
            assert "DRY-ONLY" not in doc and "writes NOTHING" not in doc, "the docstring still says DRY-only"
            assert "ENABLE_KB_BRANDS" in doc


# ===========================================================================
# PIN rows (green at base; the full configuration present)
# ===========================================================================

def test_s16b_pin1_batch_seeder_flag_unchanged(monkeypatch, tmp_path, caplog):
    common = s16._mod("kb_seed_common")
    seed = s16._mod("seed_kb_batch")
    corpus = s16._std_corpus(tmp_path)
    s16._full_config(monkeypatch, corpus)
    monkeypatch.setenv("ENABLE_KB_BRANDS", "apply")
    monkeypatch.setenv("KB_BRANDS_MAX", "5")
    monkeypatch.delenv("ENABLE_KB_SEED", raising=False)
    rig = s16.Rig(monkeypatch, common, seed=seed, merchants=[s16._merchant("store-a.example.com")])
    assert _attr(seed, "FLAG") == "ENABLE_KB_SEED"
    caplog.set_level(logging.INFO)
    assert _attr(seed, "main")(["--corpus", str(corpus)]) == 0
    recs = s16._records(caplog)
    assert len(recs) == 1 and recs[0].levelno == logging.INFO and "ENABLE_KB_SEED" in recs[0].getMessage()
    assert rig.client_factory_calls == [] and rig.factory_calls == [] and rig.fetches == [] and rig.events == []


def test_s16b_pin2_host_derivation_literal(monkeypatch):
    brands = s16._mod("seed_kb_brands_wikidata")
    from app.services import deny_hosts as dh

    monkeypatch.setenv("ENABLE_KB_BRANDS", "apply")
    monkeypatch.setenv("ENABLE_KB_SEED", "apply")
    monkeypatch.setenv("KB_BRANDS_MAX", "1")
    sites = ["https://brand-b.example.com/", "https://store-a.example.com/", "https://www.%s/" % dh.DENY_HOSTS[0],
             "http://192.0.2.10/", "https://Brand-C.Example.org:443/x", "not a url"]
    bindings = [_bind("Q%d" % (i + 1), s, en="Brand %d" % i, ar=AR1) for i, s in enumerate(sites)]
    bindings.append(_bind("Q99", None, en="No Site"))
    counts = {}
    hosts = _attr(brands, "derive_hosts")(bindings, {"store-a.example.com"}, counts)
    assert hosts == ["brand-b.example.com", "brand-c.example.org"]
    assert counts == {"bindings": 7, "denied": 1, "existing": 1, "invalid": 2, "new": 2, "with_site": 6}
    assert _attr(brands, "MAX_BRAND_HOSTS") == 300


def test_s16b_pin3_the_045_census_unchanged():
    kb = _kb()
    assert tuple(_attr(kb, "KB_TABLES"))[:10] == TEN_045
    cols = _attr(kb, "KB_COLUMNS")
    for table in TEN_045:
        assert tuple(cols[table]) == COLUMNS_045[table], table


def test_s16b_pin4_app_names_nothing_new():
    offenders = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        for needle in ("ENABLE_KB_BRANDS", "KB_BRANDS_MAX", "seed_kb_brands_wikidata"):
            if needle in text:
                offenders.append((rel, needle))
        if "kb_brands" in text.replace("seed_kb_brands_wikidata", "") and rel != "app/services/kb_service.py":
            offenders.append((rel, "kb_brands"))
    assert offenders == [], offenders


def test_s16b_pin5_no_service_runs_the_brand_script():
    files = sorted(ROOT.glob("railway*.json"))
    assert files, "no railway*.json at the repo root"
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        start = str((data.get("deploy") or {}).get("startCommand") or "")
        assert "seed_kb_brands_wikidata" not in start, path.name


def test_s16b_pin6_045_untouched():
    for rel, want in SHA_045.items():
        got = hashlib.sha256(_lf((ROOT / rel).read_text(encoding="utf-8")).encode("utf-8")).hexdigest()
        assert got == want, rel
