"""D16 OPERATOR-INGEST RED rows (spec S81-G4, unit D16 section 5, as amended by
RULINGS_S81_G4: R-G4-7 the licence fields (kb_serve.LICENCE_FIELDS) accepted in
``specs`` only from source ``partner``, 400 KB_LICENCE_FIELD with zero writes from
source ``operator`` (the NEW row R11); R-G4-11 include_in_schema=False on both
routes and the OpenAPI path-set sha pinned).

``app.main`` is imported FIRST (the dotenv guard strips CREDENTIALS_UNSET at
import); the admin key is built at run time (secrets.token_hex(32)) and set after.
Every RED row fails at base on an AssertionError only: ``app.services.kb_operator``
is reached through ``_op()`` (find_spec + an assertion); the route rows assert the
status the route must answer (404 at base). The PIN rows P1-P3 are green at base:
P1 sends the FULL configuration (the knob set, a valid key, a valid body) over the
flag-OFF spellings and compares each answer with the never-registered sibling
``/api/v1/admin/kb/__absent__`` in the same run, with ``verify_admin_key``
overridden by a recorder and the service-role clients replaced by raising
recorders; P2 pins the sorted OpenAPI path set (sha256 recorded at base 0b19de5b).

Hygiene: pure ASCII, LF; bounded runner only; netguard on; synthetic hosts and
identities only; no key-shaped literal.
"""
from __future__ import annotations

import app.main as app_main  # noqa: I001  (FIRST: the dotenv guard)

import copy
import hashlib
import importlib
import importlib.util
import json
import logging
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import admin_routes
from app.services import database_service

APP = app_main.app
ROOT = Path(__file__).resolve().parents[1]
OP = "app.services.kb_operator"
SERVE = "app.services.kb_serve"
FLAG = "ENABLE_OPERATOR_INGEST"
KNOB = "KB_OPERATOR_PAGE_MAX"
VIEW = "/api/v1/admin/kb/operator"
INGEST = "/api/v1/admin/kb/ingest"
ABSENT = "/api/v1/admin/kb/__absent__"
RUNBOOK = ROOT / "docs" / "runbooks" / "2026-11-kb-operator-ingest.md"
SCHEMA_PATHSET_SHA256 = "9dbdb7aab61e628c52b3cf3260cdbe968a827754d26bd1366aa6dafc642a9809"  # 76 paths at 0b19de5b
NOW = datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc)
HOST_A = "store-a.example.com"
HOST_B = "store-b.example.com"
HOST_C = "store-c.example.com"
PDP_A = "https://" + HOST_A + "/products/nimbus-noir"
PDP_B = "https://" + HOST_B + "/products/nimbus-noir"
IMG_A = "https://" + HOST_A + "/img/nimbus-noir.jpg"
BRAND, NAME = "Acme", "Nimbus Noir Eau de Parfum"
OFF_SPELLINGS = [None, "false", " 0 ", "OFF"]
LOG_RE = re.compile(r"^\[KB_OPERATOR\] ingest source=(operator|partner) host=[a-z0-9.-]+ products=\d+ "
                    r"variants=\d+ offers=\d+ images=\d+ specs=\d+ gaps_closed=\d+ not_built=\d+$")


def _present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _op():
    assert _present(OP), "app/services/kb_operator.py does not exist (D16 not implemented)"
    return importlib.import_module(OP)


def _attr(mod, name):
    assert hasattr(mod, name), "%s.%s is missing (D16 not implemented)" % (mod.__name__, name)
    return getattr(mod, name)


def _kb():
    from app.services import kb_service as kb
    return kb


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data
        self.count = None


class _Query:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.op, self.payload, self.kwargs = None, None, {}
        self.filters, self.orders, self.columns, self.lim = [], [], None, None

    def select(self, columns="*", **kwargs):
        if self.op is None:
            self.op = "select"
        self.columns = columns
        return self

    def upsert(self, rows, **kwargs):
        self.op, self.payload, self.kwargs = "upsert", copy.deepcopy(rows), dict(kwargs)
        return self

    def insert(self, rows, **kwargs):
        self.op, self.payload, self.kwargs = "insert", copy.deepcopy(rows), dict(kwargs)
        return self

    def update(self, payload, **kwargs):
        self.op, self.payload, self.kwargs = "update", copy.deepcopy(payload), dict(kwargs)
        return self

    def order(self, column, desc=False, **kwargs):
        self.orders.append((column, bool(desc)))
        return self

    def limit(self, n, **kwargs):
        self.lim = n
        return self

    def range(self, start, end, **kwargs):
        self.lim = end - start + 1
        return self

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _filter(*args, **kwargs):
            self.filters.append((name, list(args)))
            return self
        return _filter

    def execute(self):
        return self.client._execute(self)


def _match(row, name, args):
    if len(args) < 2:
        return True
    col, val = args[0], args[1]
    if name == "eq":
        return str(row.get(col)) == str(val)
    if name == "in_":
        return row.get(col) in list(val)
    return True


class _Client:
    def __init__(self, tables, *, raise_on_write=False):
        self.tables = copy.deepcopy(tables)
        self.raise_on_write = raise_on_write
        self.ops = []
        self.lock = threading.Lock()

    def table(self, name):
        return _Query(self, name)

    def _execute(self, q):
        with self.lock:
            self.ops.append({"table": q.table, "op": q.op, "payload": q.payload, "kwargs": q.kwargs,
                             "filters": q.filters, "columns": q.columns})
            rows = self.tables.setdefault(q.table, [])
            if q.op == "select":
                out = [dict(r) for r in rows if all(_match(r, n, a) for n, a in q.filters)]
                for col, desc in reversed(q.orders):
                    out.sort(key=lambda r: str(r.get(col)), reverse=desc)
                if q.lim is not None:
                    out = out[:q.lim]
                return _Resp(out)
            if self.raise_on_write:
                raise RuntimeError("d16 probe: write failed")
            if q.op in ("upsert", "insert"):
                payload = q.payload if isinstance(q.payload, list) else [q.payload]
                rows.extend(dict(r) for r in payload)
                return _Resp([dict(r) for r in payload])
            if q.op == "update":
                hit = [r for r in rows if all(_match(r, n, a) for n, a in q.filters)]
                for r in hit:
                    r.update(q.payload or {})
                return _Resp([dict(r) for r in hit])
            return _Resp([])

    def writes(self):
        return [o for o in self.ops if o["op"] in ("upsert", "insert", "update", "delete")]

    def sent(self, table):
        out = []
        for o in self.ops:
            if o["table"] == table and o["op"] in ("upsert", "insert"):
                out.extend(o["payload"] if isinstance(o["payload"], list) else [o["payload"]])
        return out


def _robots(host):
    return {"state": "allow", "origin": "https://" + host, "fetched_at": "2026-11-01T05:00:00Z",
            "next_reread": "2026-11-03T05:00:00Z"}


def _merchant(host, status="live", *, reviewed=True, verdict="allowed"):
    tos = {"verdict": verdict, "terms_url": "https://" + host + "/terms",
           "reviewed_at": "2026-10-30T00:00:00Z" if reviewed else None}
    return {"host": host, "status": status, "deny": False, "tos": tos, "robots": _robots(host),
            "blocked_reason": "challenge" if status == "blocked" else None, "country": "BH",
            "currency_hint": "BHD", "registry": [], "challenge": None, "platform": None}


def _pid():
    return _kb().kb_product_id(BRAND, NAME)


def _gap(field, state="open", demand=1, last="2026-11-01T10:00:00+00:00"):
    return {"product_key": _pid(), "field": field, "state": state, "demand_count": demand,
            "first_seen": last, "last_seen": last, "source_hint": HOST_A}


def _tables(**over):
    pid = _pid()
    t = {
        "kb_merchants": [_merchant(HOST_A), _merchant(HOST_B, "blocked", reviewed=False),
                         _merchant(HOST_C, "candidate")],
        "kb_gaps": [_gap("price"), _gap("image", "needs_operator"), _gap("specs", "licence"), _gap("rating"),
                    _gap("pdp_" + "a" * 16, "queued", demand=0)],
        "kb_coverage_daily": [
            {"day": "2026-11-01", "metric": "kb.products.total", "value": "4", "n": 4},
            {"day": "2026-11-01", "metric": "kb.field.offer_share", "value": "0.5", "n": 4},
            {"day": "2026-10-31", "metric": "kb.products.total", "value": "3", "n": 3},
        ],
        "kb_products": [], "kb_variants": [], "kb_offers": [], "kb_images": [], "kb_specs": [],
    }
    assert pid
    t.update(over)
    return t


def _body(**over):
    body = {"source": "operator", "page_url": PDP_A + "?utm_source=x",
            "jsonld": [{"@context": "https://schema.org", "@type": "Product", "brand": {"name": BRAND},
                        "name": NAME}],
            "og_image": IMG_A, "price": {"amount": 42.5, "currency": "BHD"}, "market": "BH", "size_ml": 100,
            "in_stock": True, "specs": {"scent_family": "woody", "season": "winter"}}
    body.update(over)
    return body


class H:
    """The route harness: the real app, the flag and knob per row, the key built at
    run time, the service-role client through kb_operator._admin_client."""

    def __init__(self, mp, *, flag="true", tables=None, key=True, raise_on_write=False):
        self.mp = mp
        self.key = secrets.token_hex(32)
        mp.setenv("ADMIN_API_KEY", self.key)
        mp.setenv(KNOB, "7")
        mp.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
        if flag is None:
            mp.delenv(FLAG, raising=False)
        else:
            mp.setenv(FLAG, flag)
        self.send_key = key
        self.client = _Client(tables if tables is not None else _tables(), raise_on_write=raise_on_write)
        self.legacy = []

        def _legacy(*_a, **_k):
            self.legacy.append("get_admin_supabase_client")
            return self.client
        mp.setattr(database_service, "get_admin_supabase_client", _legacy)
        if _present(OP):
            mod = importlib.import_module(OP)
            mp.setattr(mod, "_admin_client", lambda: self.client, raising=False)
            mp.setattr(mod, "_now", lambda: NOW, raising=False)
        self.http = TestClient(APP, raise_server_exceptions=False)

    def headers(self, key=None):
        out = {"X-Request-ID": "d16-rid"}
        if self.send_key or key:
            out["X-Admin-Key"] = key or self.key
        return out

    def _reset(self):
        from app.middleware.rate_limiter import limiter
        limiter.reset()

    def get(self, path, params=None, **kw):
        self._reset()
        return self.http.get(path, params=params, headers=self.headers(**kw))

    def post(self, path, body, **kw):
        self._reset()
        return self.http.post(path, json=body, headers=self.headers(**kw))


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in (FLAG, KNOB):
        monkeypatch.delenv(name, raising=False)
    yield


def _j(resp):
    try:
        return json.loads(resp.text)
    except ValueError as exc:
        raise AssertionError("not JSON (%s): %s %r" % (type(exc).__name__, resp.status_code, resp.text[:200]))


def _ok(resp):
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    body = _j(resp)
    assert body.get("success") is True, body
    return body


def _refused(resp, code):
    assert resp.status_code == 400, (code, resp.status_code, resp.text[:300])
    body = _j(resp)
    assert body.get("success") is False and body.get("code") == code, body
    return body


# ---------------------------------------------------------------------------
# rows
# ---------------------------------------------------------------------------

def test_r1_module_flag_knob(monkeypatch):
    """R1: the module exists; the house boolean read per call; page_max defensive
    (unset / blank / garbage / inf / nan / <= 0 -> 50, clamped 1..200)."""
    mod = _op()
    fn = _attr(mod, "operator_ingest_enabled")
    for v in (None, "", "false", "0", " OFF ", "garbage", "apply"):
        if v is None:
            monkeypatch.delenv(FLAG, raising=False)
        else:
            monkeypatch.setenv(FLAG, v)
        assert fn() is False, v
    for v in ("true", " TRUE ", "1", "yes", "On"):
        monkeypatch.setenv(FLAG, v)
        assert fn() is True, v
    pm = _attr(mod, "page_max")
    for v, want in ((None, 50), ("", 50), ("abc", 50), ("inf", 50), ("nan", 50), ("-3", 50), ("0", 50),
                    ("7", 7), ("999", 200), ("1", 1), (" 25 ", 25)):
        if v is None:
            monkeypatch.delenv(KNOB, raising=False)
        else:
            monkeypatch.setenv(KNOB, v)
        assert pm() == want, (v, pm())


def test_r2_view_requires_key_when_on(monkeypatch):
    """R2: ON: no key -> 403 (the existing dependency); a valid key -> 200 with the four
    blocks."""
    h = H(monkeypatch, key=False)
    resp = h.get(VIEW)
    assert resp.status_code == 403, (resp.status_code, resp.text[:200])
    assert _j(resp).get("error") == "Invalid admin key"
    body = _ok(h.get(VIEW, key=h.key))
    for k in ("blocked", "needs_operator", "coverage", "limit"):
        assert k in body, (k, sorted(body))


def test_r3_view_content_and_bounds(monkeypatch):
    """R3: the blocked projection keys exactly; needs_operator ordered by demand then
    last_seen; ?limit=999 clamped to the knob; the latest coverage day only; no
    personal field anywhere."""
    pid = _pid()
    gaps = [_gap("price", "needs_operator", 2, "2026-11-01T10:00:00+00:00"),
            _gap("image", "needs_operator", 5, "2026-10-30T10:00:00+00:00"),
            _gap("size", "needs_operator", 2, "2026-11-01T12:00:00+00:00"),
            _gap("rating", "open", 9)]
    h = H(monkeypatch, tables=_tables(kb_gaps=gaps))
    body = _ok(h.get(VIEW, params={"limit": "999"}))
    assert body["limit"] == 7, body["limit"]
    assert [b["host"] for b in body["blocked"]] == [HOST_B], body["blocked"]
    assert set(body["blocked"][0]) == {"host", "status", "blocked_reason", "robots_state", "robots_fetched_at",
                                       "tos_verdict", "tos_reviewed_at"}, body["blocked"][0]
    assert body["blocked"][0]["robots_state"] == "allow" and body["blocked"][0]["tos_reviewed_at"] is None
    assert [(g["field"], g["demand_count"]) for g in body["needs_operator"]] == [
        ("image", 5), ("size", 2), ("price", 2)], body["needs_operator"]
    assert all(g["product_key"] == pid for g in body["needs_operator"])
    assert body["coverage"]["day"] == "2026-11-01", body["coverage"]
    assert sorted(m["metric"] for m in body["coverage"]["metrics"]) == ["kb.field.offer_share", "kb.products.total"]
    text = json.dumps(body)
    for word in ("user_id", "email", "device", "query"):
        assert word not in text, word
    selects = [o for o in h.client.ops if o["op"] == "select" and o["table"] in ("kb_merchants", "kb_gaps")]
    assert selects and all(o["kwargs"] == {} for o in selects)
    body = _ok(h.get(VIEW, params={"limit": "abc"}))
    assert body["limit"] == 7


def test_r4_ingest_happy_path_operator(monkeypatch):
    """R4: a live host: product (identity high) / variant / offer (rung operator) / image
    (source operator) / specs (cited to the canonical page) are the builders' rows sent
    insert-ignore; the matching open + needs_operator gaps CAS-closed in ONE update;
    a licence gap, the rating gap and the pdp_ hint are untouched."""
    kb = _kb()
    pid = _pid()
    conc = pid.split("|")[3]
    vid = kb.kb_variant_key(pid, conc, 100)
    h = H(monkeypatch)
    body = _ok(h.post(INGEST, _body()))
    assert isinstance(body.get("written"), dict), body
    want = {
        "kb_products": kb.build_product_row(id=pid, brand=BRAND, name=NAME, identity_confidence="high",
                                            updated_at=NOW, concentration=conc),
        "kb_variants": kb.build_variant_row(id=vid, product_id=pid, updated_at=NOW, concentration=conc,
                                            size_ml=100),
        "kb_offers": kb.build_offer_row(variant_id=vid, merchant_id=HOST_A, market="BH", amount=42.5,
                                        observed_currency="BHD", evidence_rung="operator", canonical_url=PDP_A,
                                        captured_at=NOW, size_ml=100, in_stock=True),
        "kb_images": kb.build_image_row(product_id=pid, url=IMG_A, provenance_host=HOST_A, source="operator",
                                        captured_at=NOW),
    }
    for table, row in want.items():
        assert row is not None, table
        assert row in h.client.sent(table), (table, h.client.sent(table))
    for field, value in (("scent_family", "woody"), ("season", "winter")):
        row = kb.build_spec_row(product_id=pid, field=field, value=value, extractor="operator", captured_at=NOW,
                                lang="en", source_url=PDP_A, cited=True)
        assert row is not None and row in h.client.sent("kb_specs"), (field, h.client.sent("kb_specs"))
    for o in h.client.ops:
        if o["op"] in ("upsert", "insert"):
            assert o["op"] == "upsert" and o["kwargs"].get("ignore_duplicates") is True, o
    assert not [o for o in h.client.writes() if o["table"] in ("kb_reviews", "kb_feedback", "kb_merchants")]
    ups = [o for o in h.client.writes() if o["table"] == "kb_gaps"]
    assert len(ups) == 1 and ups[0]["op"] == "update" and ups[0]["payload"] == {"state": "closed"}, ups
    states = {r["field"]: r["state"] for r in h.client.tables["kb_gaps"]}
    assert states == {"price": "closed", "image": "closed", "specs": "licence", "rating": "open",
                      "pdp_" + "a" * 16: "queued"}, states


def test_r5_blocked_host_needs_review(monkeypatch):
    """R5: a blocked host without tos.reviewed_at -> 400 KB_HOST_NOT_REVIEWED, zero
    writes; with it -> accepted."""
    h = H(monkeypatch)
    _refused(h.post(INGEST, _body(page_url=PDP_B, og_image=None)), "KB_HOST_NOT_REVIEWED")
    assert h.client.writes() == []
    t = _tables()
    t["kb_merchants"][1] = _merchant(HOST_B, "blocked", reviewed=True)
    h = H(monkeypatch, tables=t)
    _ok(h.post(INGEST, _body(page_url=PDP_B, og_image=None)))
    assert h.client.sent("kb_offers"), h.client.ops


def test_r6_refusal_codes(monkeypatch):
    """R6: candidate / unknown / denied / placeholder identity / oversize -> the 2.6
    codes, zero writes; a raising write -> 400 KB_STORE_UNAVAILABLE (never a 503)."""
    from app.services import deny_hosts
    cases = [
        (_body(page_url="https://" + HOST_C + "/products/x", og_image=None), "KB_HOST_CANDIDATE"),
        (_body(page_url="https://unknown-host.example.com/products/x", og_image=None), "KB_HOST_UNKNOWN"),
        (_body(page_url="https://" + deny_hosts.DENY_HOSTS[0] + "/perfume/x", og_image=None), "KB_URL_REFUSED"),
        (_body(jsonld=[], brand="Unknown", name="Unknown"), "KB_IDENTITY_UNRESOLVED"),
        (_body(jsonld=[{"@type": "Product", "name": NAME, "description": "x" * 270000}]), "KB_PAYLOAD_TOO_LARGE"),
    ]
    for body, code in cases:
        h = H(monkeypatch)
        _refused(h.post(INGEST, body), code)
        assert h.client.writes() == [], (code, h.client.writes())
    h = H(monkeypatch, raise_on_write=True)
    resp = h.post(INGEST, _body())
    _refused(resp, "KB_STORE_UNAVAILABLE")


def test_r7_validation(monkeypatch):
    """R7: an extra key, a bad currency, 21 JSON-LD items -> 422 (never a 500); a 20-item
    body is accepted."""
    h = H(monkeypatch)
    for body in (_body(extra_key=1), _body(price={"amount": 1.0, "currency": "bhd"}),
                 _body(jsonld=[{"@type": "Thing"}] * 21), _body(price={"amount": -1, "currency": "BHD"})):
        resp = h.post(INGEST, body)
        assert resp.status_code == 422, (resp.status_code, resp.text[:200])
    assert h.client.writes() == []
    _ok(h.post(INGEST, _body(jsonld=_body()["jsonld"] + [{"@type": "Thing"}] * 19)))


def test_r8_partner_source(monkeypatch, caplog):
    """R8: source partner writes the same rows and logs source=partner."""
    kb = _kb()
    caplog.set_level(logging.INFO)
    h = H(monkeypatch)
    _ok(h.post(INGEST, _body(source="partner")))
    pid = _pid()
    vid = kb.kb_variant_key(pid, pid.split("|")[3], 100)
    offer = kb.build_offer_row(variant_id=vid, merchant_id=HOST_A, market="BH", amount=42.5,
                               observed_currency="BHD", evidence_rung="operator", canonical_url=PDP_A,
                               captured_at=NOW, size_ml=100, in_stock=True)
    assert offer in h.client.sent("kb_offers")
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[KB_OPERATOR]")]
    assert lines and "source=partner" in lines[-1], lines


def test_r9_log_line_constants(monkeypatch, caplog):
    """R9: ONE `[KB_OPERATOR] ingest` line per ingest: the host and ints only."""
    caplog.set_level(logging.INFO)
    h = H(monkeypatch)
    _ok(h.post(INGEST, _body()))
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[KB_OPERATOR]")]
    assert len(lines) == 1 and LOG_RE.match(lines[0]), lines
    assert "host=" + HOST_A + " " in lines[0]
    assert "/products" not in lines[0] and "Nimbus" not in lines[0] and "Acme" not in lines[0]
    assert " offers=1 " in lines[0] and " specs=2 " in lines[0], lines[0]


def test_r10_runbook_names_only():
    """R10: the runbook exists; the bookmarklet copies to the clipboard and never posts;
    the curl template names the variable only; no 64-hex run, no email shape."""
    assert RUNBOOK.is_file(), "docs/runbooks/2026-11-kb-operator-ingest.md does not exist (D16 not implemented)"
    text = RUNBOOK.read_text(encoding="ascii")
    for needle in ("javascript:", "navigator.clipboard", "X-Admin-Key", "ADMIN_API_KEY", "/api/v1/admin/kb/ingest"):
        assert needle in text, needle
    snippet = text[text.index("javascript:"):]
    snippet = snippet[:snippet.find("```")] if "```" in snippet else snippet
    assert "fetch(" not in snippet and "XMLHttpRequest" not in snippet and "sendBeacon" not in snippet
    assert not re.search(r"[0-9a-fA-F]{64}", text)
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    assert all(b < 128 for b in RUNBOOK.read_bytes()) and b"\r" not in RUNBOOK.read_bytes()


def test_r11_licence_fields_partner_only(monkeypatch):
    """R11 (R-G4-7): a specs field in kb_serve.LICENCE_FIELDS from source operator -> 400
    KB_LICENCE_FIELD with zero writes; from source partner -> accepted and the spec row
    written (cited to the page)."""
    kb = _kb()
    assert _present(SERVE), "app/services/kb_serve.py does not exist (S81-18 not implemented)"
    fields = _attr(importlib.import_module(SERVE), "LICENCE_FIELDS")
    assert tuple(fields) == ("notes_top", "notes_heart", "notes_base", "longevity", "sillage"), fields
    for field in fields:
        h = H(monkeypatch)
        _refused(h.post(INGEST, _body(specs={"scent_family": "woody", field: "x"})), "KB_LICENCE_FIELD")
        assert h.client.writes() == [], field
    h = H(monkeypatch)
    _ok(h.post(INGEST, _body(source="partner", specs={"notes_top": "bergamot"})))
    row = kb.build_spec_row(product_id=_pid(), field="notes_top", value="bergamot", extractor="operator",
                            captured_at=NOW, lang="en", source_url=PDP_A, cited=True)
    assert row in h.client.sent("kb_specs"), h.client.sent("kb_specs")


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

def _shape(resp):
    names = sorted(k.lower() for k in resp.headers.keys() if k.lower() not in ("x-request-id", "content-length"))
    return resp.status_code, _j(resp), names


@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=["unset", "false", "pad0", "OFF"])
def test_p1_flag_off_equals_unregistered_path(monkeypatch, value):
    """P1 (PIN): with the FULL configuration and the flag OFF, both D16 paths answer
    exactly what the never-registered sibling answers (status, JSON body, header names);
    no client is built; verify_admin_key (overridden by a recorder) never runs."""
    h = H(monkeypatch, flag=value)
    calls = []

    def _rec_admin():
        calls.append("verify_admin_key")
        return True
    monkeypatch.setitem(APP.dependency_overrides, admin_routes.verify_admin_key, _rec_admin)
    if _present(OP):
        mod = importlib.import_module(OP)

        def _boom():
            raise AssertionError("D16 OFF: the service-role client was built")
        monkeypatch.setattr(mod, "_admin_client", _boom, raising=False)
    got_view, want_view = _shape(h.get(VIEW, params={"limit": "3"})), _shape(h.get(ABSENT, params={"limit": "3"}))
    got_post, want_post = _shape(h.post(INGEST, _body())), _shape(h.post(ABSENT, _body()))
    assert want_view[0] == 404 and want_view[1] == {"detail": "Not Found"}, want_view
    assert got_view == want_view, (got_view, want_view)
    assert got_post == want_post, (got_post, want_post)
    assert calls == [] and h.legacy == [] and h.client.ops == [], (calls, h.legacy, h.client.ops)


def test_p2_openapi_unchanged(monkeypatch):
    """P2 (PIN): the sorted OpenAPI path set equals the one recorded at base (both D16
    routes include_in_schema=False), with the flag ON and OFF."""
    saved = APP.openapi_schema
    try:
        for value in (None, "true"):
            if value is None:
                monkeypatch.delenv(FLAG, raising=False)
            else:
                monkeypatch.setenv(FLAG, value)
            APP.openapi_schema = None
            paths = sorted(APP.openapi()["paths"])
            digest = hashlib.sha256("\n".join(paths).encode("ascii")).hexdigest()
            assert digest == SCHEMA_PATHSET_SHA256, (len(paths), digest)
            assert not any("/kb/" in p for p in paths)
    finally:
        APP.openapi_schema = saved


@pytest.mark.parametrize("value", [None, "true"])
def test_p3_existing_admin_routes_unchanged(monkeypatch, value):
    """P3 (PIN): /api/v1/admin/stats/daily without a key -> the 403 envelope, flag ON and
    OFF."""
    h = H(monkeypatch, flag=value, key=False)
    resp = h.get("/api/v1/admin/stats/daily")
    assert resp.status_code == 403
    body = _j(resp)
    assert (body.get("success"), body.get("error"), body.get("code")) == (False, "Invalid admin key", "FORBIDDEN"), body
    assert h.client.ops == []


_ = timedelta  # imported for symmetry with the sibling files
