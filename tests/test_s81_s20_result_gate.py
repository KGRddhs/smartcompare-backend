"""S81-20 B2-RESULT-GATE-V2 (ENABLE_RESULT_GATE) -- RED and PIN rows.

Spec .qa-s80/S81-20_UNIT_SPEC.md section 5 as amended by RULINGS_S81_20 (R-S20-23..46; the
brief's R-S20-1..22 beneath). Base 6869a3e6. Every RED row fails at base on an AssertionError
only: the unit's symbols are resolved with getattr inside the test body and ASSERTED, never
imported at module top. Every PIN row is green at base and runs with the FULL companion
configuration (metering, envelope, auth required + an authed override, B1 ON, V2 ON, echo ON,
W4-13 by param) plus the three decision recorders on result_gate.gate_reason /
url_gate_reason / camera_gate_reason (installed with raising=False, so they exist at base as
plain attributes and a not-gated mutant is killed).

Rulings applied beyond the spec rows: R-S20-31 (R61, M39), R-S20-32 (the GET / STREAM / URL /
no-fingerprint STREAM device-quota rows through the S81-09 FakeRedis), R-S20-33 (R62), R-S20-35
(R32 over POST / GET / URL), R-S20-36 (the Arabic-Indic digit price in R11), R-S20-38 (the
refusal-budget rows: counted / spent / gate OFF per route; R31 / R60 are re-cut from
"record_refusal_async 0 calls" to the counted form), R-S20-39 (the camera conflict only from two
V2 _category values; a stub-derived conflict under V1 is DELIVERED), R-S20-30 (the camera call
goes through the module attribute, so the recorder on result_gate.camera_gate_reason sees it),
R-S20-11 (anonymous rows with ENABLE_COMPARE_AUTH_REQUIRED OFF explicitly).

Hermetic: no network, no .env, no credential; synthetic ids (s20-<node>); the 64-hex device
fingerprint is built at run time. Pure ASCII, LF; the H6 em dash is chr(0x2014).
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.main as app_main  # FIRST: the dotenv guard (load_dotenv at import)
from app.api import image_routes, text_routes, url_routes
from app.api.auth_routes import get_current_user, get_optional_user
from app.main import app
from app.middleware import error_handler as eh
from app.services import category_gate as cg
from app.services import feedback_service, kb_ingest, usage_service
from app.services import response_builder as rb
from app.services import result_gate as rgm
import app.services.structured_comparison_service as scs
from tests import test_s75_fanout_identity as fy
from tests import test_retro_w2_1 as rw

FLAG = "ENABLE_RESULT_GATE"
B1 = "ENABLE_RESULT_STATUS_METADATA"
V2 = "ENABLE_VISION_IDENTITY_V2"
URLV2 = "ENABLE_URL_MODE_V2"
FRAG = "ENABLE_FRAGRANCE_ONLY_GATE"
QUOTA = "ENABLE_DEVICE_DAILY_QUOTA"
KBI = "ENABLE_KB_INGEST"
FSM = "ENABLE_FIELD_STATUS_METADATA"
KBF = "ENABLE_KB_FIRST_SERVE"
TRUTH = "ENABLE_SEARCH_LOG_TRUTH"
SYNM = "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER"
ECHO = "ENABLE_COMPARISON_ID_ECHO"
ANON = "ENABLE_ANON_USAGE_GATE"
AUTHREQ = "ENABLE_COMPARE_AUTH_REQUIRED"
METER = "ENABLE_PAID_ROUTE_METERING"
ENVELOPE = "ENABLE_CAMERA_FAILURE_ENVELOPE"

CLEAR = tuple(sorted(set((
    FLAG, B1, V2, URLV2, FRAG, QUOTA, KBI, FSM, KBF, TRUTH, SYNM, ECHO, ANON, AUTHREQ, METER,
    ENVELOPE, "ENABLE_STRICT_OPTIONAL_AUTH", "ENABLE_PREVERDICT_DISCONNECT_ABORT",
    "ENABLE_FULL_STREAM_DEADLINE", "DEBUG_STAGE_TIMINGS", "ENABLE_RIYADH_RESET",
    "ENABLE_REQUEST_CONTEXT_HEADERS", "DEVICE_KEY_PEPPER", "DEVICE_QUOTA_EXEMPT_USER_IDS",
    "DEVICE_DAILY_QUOTA_CAP", "ENABLE_ASYNC_REDIS_OFFLOAD", "ENABLE_USAGE_PATH_OFFLOOP",
    "ENABLE_SYNC_DB_OFFLOAD", "ENABLE_LLM_PREFLIGHT_BREAKER", "REFUSAL_DAILY_BUDGET",
    "ENABLE_JSONLD_RATING", "ENABLE_HONEST_PARTIAL_SCORING",
) + fy.UNIT_ENV)))

FIX = Path(__file__).resolve().parent / "fixtures"
LANE1 = ("fashion", "grocery", "haircare", "iphone15_vs_galaxys24", "makeup", "now_vs_solgar",
         "other", "skincare", "tomford_vs_creed")
EM = chr(0x2014)
H6_MESSAGE = "Comparison data was incomplete " + EM + " choose different products."
GATE_REASONS = ("placeholder_identity", "same_identity", "category_conflict", "no_evidence")
CAMERA_REASONS = ("placeholder_identity", "low_confidence", "same_identity", "category_conflict")
CAMERA_MESSAGE = "Photograph each product in its own photo so we can tell them apart."
ENVELOPE_KEYS = {"success", "error", "code", "request_id"}
JPEG = bytes([255, 216]) + bytes(64)
QUERY = "Alpha One vs Beta Two"
FRAG_QUERY = "Lattafa Asad vs Lattafa Khamrah"
URL1 = "https://example.test/alpha"
URL2 = "https://example.test/beta"
CONFLICT_PAIR = ("Samsung Galaxy S24 phone", "Dior Sauvage eau de parfum")
FY_V10_PAIR = ("Hyper X MIC", "Hyper X2 MIC")
FY_V10_FRAG_PAIR = ("Lattafa Asad eau de parfum", "Lattafa Khamrah eau de parfum")
TRUTHY_TABLE = [(None, False), ("", False), ("false", False), ("0", False), ("off", False),
                ("no", False), ("garbage", False), (" TRUE ", True), ("true", True), ("1", True),
                ("yes", True), ("On", True)]


def _fp():
    return "".join("abcdef0123456789"[(i * 7) % 16] for i in range(64))


# ---------------------------------------------------------------- symbol helpers (RED rule)

def _sym(name):
    value = getattr(rgm, name, None)
    assert value is not None, "result_gate.%s is absent (RED at base)" % name
    return value


def _fn(name):
    f = getattr(rgm, name, None)
    assert callable(f), "result_gate.%s is not callable (RED at base)" % name
    return f


def _call_total(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        return "raised " + type(exc).__name__


# ---------------------------------------------------------------- bodies

def _lane1(name):
    return json.loads((FIX / "lane1" / (name + "_response.json")).read_text(encoding="utf-8"))


def body_sup():
    return _lane1("tomford_vs_creed")


def _set_identity(body, i, brand, name):
    for prods in (body.get("products"), (body.get("overview") or {}).get("products")):
        if isinstance(prods, list) and len(prods) > i and isinstance(prods[i], dict):
            prods[i]["brand"] = brand
            prods[i]["name"] = name
            if "full_name" in prods[i]:
                prods[i]["full_name"] = (brand + " " + name).strip()


def body_v09():
    b = body_sup()
    for i in (0, 1):
        _set_identity(b, i, "", "Unknown Product")
    return b


def body_v07():
    b = body_sup()
    _set_identity(b, 0, "GUESS", "GUESS")
    _set_identity(b, 1, "GUESS", "GUESS!")
    return b


def _strip_evidence(b, keep_price0=False, keep_rating1=False):
    for i, p in enumerate(b["products"]):
        if not (keep_price0 and i == 0):
            p["price"] = {"amount": None, "currency": "BHD", "unavailable": True}
        if not (keep_rating1 and i == 1):
            p["rating"] = None
            p["rating_derived"] = True
        p["specs"] = {}
    for i, p in enumerate((b.get("overview") or {}).get("products") or []):
        if not (keep_price0 and i == 0):
            p["price"] = {"amount": None, "currency": "BHD", "unavailable": True}
        if not (keep_rating1 and i == 1):
            p["rating"] = None
            p["rating_derived"] = True
    for sp in ((b.get("specs") or {}).get("products") or []):
        if isinstance(sp, dict):
            sp["specs"] = {}
    sc = b.get("specs") or {}
    if isinstance(sc.get("specs_comparison"), (list, dict)):
        sc["specs_comparison"] = [] if isinstance(sc["specs_comparison"], list) else {}
    if isinstance(b.get("scoring_v2"), dict):
        b["scoring_v2"]["dimensions"] = []
    return b


def body_v10():
    return _strip_evidence(body_sup())


def body_v10_one():
    return _strip_evidence(body_sup(), keep_price0=True, keep_rating1=True)


def body_cat():
    b = body_sup()
    b["metadata"]["product_categories"] = ["electronics", "fragrances"]
    return b


def _url_env(p0, p1):
    return {"success": True, "products": [p0, p1], "comparison": {"winner_index": 0},
            "winner_index": 0, "category": "fragrances", "source": "url"}


def _up(brand, name, price=None, rating=None, specs=None, variant=None):
    return {"brand": brand, "name": name, "variant": variant, "category": "fragrances",
            "price": {"amount": price, "currency": "BHD"}, "reviews": {"rating": rating},
            "specs": specs or {}}


def url_v09():
    return _url_env(_up("", "Unknown Product", 10.0), _up("", "Unknown Product", 12.0))


def url_same():
    return _url_env(_up("Lattafa", "Asad", 10.0), _up("Lattafa", "Asad", 12.0))


def url_noev():
    return _url_env(_up("Lattafa", "Asad"), _up("Lattafa", "Khamrah"))


def url_v03():
    return _url_env(_up("Lattafa", "Asad", 10.5), _up("Lattafa", "Khamrah", 12.25))


def url_real(name):
    """The measured JSON-LD string shapes of spec 1.9 (bheshop '490.00' / godukkan '4099'
    + rating '5'; lulu '175.000' / samawa '271.0'), each read from the real fixture."""
    if name == "bh":
        a = _jsonld_offer(FIX / "bh_gcc" / "curl_bh_bheshop.html")
        b = _jsonld_offer(FIX / "bh_gcc" / "curl_bh_godukkan.html")
    else:
        a = _jsonld_offer(FIX / "jsonld_first" / "ae_lulu_lowercase_jsonld_pricecurrency.html")
        b = _jsonld_offer(FIX / "jsonld_first" / "ae_samawa_ae_og_no_currency_jsonld_aed.html")
    return _url_env(_up("StoreA", "Item A", a[0], a[1]), _up("StoreB", "Item B", b[0], b[1]))


def _jsonld_offer(path):
    """The first Product node with offers in document walk order (the spec's probe_jsonld)."""
    import re

    def walk(node, out):
        if isinstance(node, dict):
            t = node.get("@type")
            if "Product" in (t if isinstance(t, list) else [t]):
                out.append(node)
            for v in node.values():
                walk(v, out)
        elif isinstance(node, list):
            for v in node:
                walk(v, out)

    html = path.read_text(encoding="utf-8", errors="replace")
    prods = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html,
                            re.S | re.I):
        try:
            walk(json.loads(block.strip()), prods)
        except ValueError:
            continue
    assert prods, "no JSON-LD Product node in %s" % path.name
    price, rating = None, None
    for node in prods:
        offers = node.get("offers")
        offer = offers[0] if isinstance(offers, list) and offers else offers
        if price is None and isinstance(offer, dict) and offer.get("price") is not None:
            price = offer.get("price")
        agg = node.get("aggregateRating")
        if rating is None and isinstance(agg, dict):
            rating = agg.get("ratingValue")
    return price, rating


# ---------------------------------------------------------------- vision shapes

def _v1(brand, name, conf="medium", size=None):
    return {"brand": brand, "name": name, "size_or_count": size, "visible_price": None,
            "confidence": conf}


def _v2(brand, name, conf="high", size=None, cat=None, feats=None, idx=0):
    return {"brand": brand, "name": name, "size_or_count": size, "visible_price": None,
            "confidence": conf, "_image_index": idx, "_category": cat,
            "_product_type": "perfume", "_distinguishing_features": list(feats or []),
            "_is_product": True}


VISION = {
    "V07": lambda: [_v1("GUESS", "GUESS"), _v1("GUESS", "GUESS!")],
    "V04": lambda: [_v2("Sefiki", "Oud", "low"), _v2("Violin", "Musk", "low", idx=1)],
    "LOW1": lambda: [_v2("Lattafa", "Asad", "high"), _v2("Rasasi", "Hawas", "LOW ", idx=1)],
    "V1_LOW": lambda: [_v1("Lattafa", "Asad", "low"), _v1("Rasasi", "Hawas", "low")],
    "PH0": lambda: [_v1("Unknown", "Unknown Product", "medium"), _v1("Lattafa", "Asad", "high")],
    "PH1": lambda: [_v1("Lattafa", "Asad", "high"), _v1("Unknown", "Unknown Product", "medium")],
    "ENRICH": lambda: [_v1("Unknown", "Unknown Product", "medium", "100ml"),
                       _v1("Lattafa", "Asad", "high")],
    "ENRICH_BRAND": lambda: [_v1("Lattafa", "Unknown Product", "medium", "100 ml"),
                             _v1("Rasasi", "Hawas", "high")],
    "CAT_V2": lambda: [_v2("Samsung", "Galaxy S24", cat="electronics"),
                       _v2("Dior", "Sauvage", cat="fragrances", idx=1)],
    "CAT_V1": lambda: [_v1("Samsung", "Galaxy S24 phone"), _v1("Dior", "Sauvage eau de parfum")],
    "FEAT": lambda: [_v2("GUESS", "GUESS", feats=["polyurethane"]),
                     _v2("GUESS", "GUESS!", feats=["cotton"], idx=1)],
    "SIZES": lambda: [_v1("Dior", "Sauvage", size="60ml"), _v1("Dior", "Sauvage", size="100ml")],
    "FRAG_SAME": lambda: [_v1("Lattafa", "Asad eau de parfum"), _v1("Lattafa", "Asad eau de parfum")],
    "DISTINCT": lambda: [_v1("Lattafa", "Asad"), _v1("Rasasi", "Hawas")],
}


# ---------------------------------------------------------------- harness

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in CLEAR:
        monkeypatch.delenv(name, raising=False)
    scs._DEBUG_STAGE_TIMINGS = None
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    saved = dict(app.dependency_overrides)
    try:
        yield
    finally:
        limiter.enabled = prior
        scs._DEBUG_STAGE_TIMINGS = None
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authed(request):
    user = {"id": ("s20-" + request.node.name)[:120], "email": "s20@example.test",
            "access_token": "s20-synthetic"}
    app.dependency_overrides[get_optional_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    return user


@pytest.fixture
def anonymous():
    app.dependency_overrides[get_optional_user] = lambda: None
    return None


class Rec:
    """The three decision recorders (installed with raising=False: plain attributes at base)."""

    def __init__(self, monkeypatch):
        self.calls = {"gate_reason": 0, "url_gate_reason": 0, "camera_gate_reason": 0}
        for name in self.calls:
            real = getattr(rgm, name, None)
            monkeypatch.setattr(rgm, name, self._wrap(name, real), raising=False)

    def _wrap(self, name, real):
        def _w(*a, **k):
            self.calls[name] += 1
            return real(*a, **k) if callable(real) else None
        return _w

    def total(self):
        return sum(self.calls.values())


class L(rw.Ledger):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.persist = []
        self.budget_reads = []
        self.budget_records = []

    def log_search(self, **kw):
        self.rows.append(dict(kw))
        return super().log_search(**kw)


def _ledger(monkeypatch, module, *, spent=None):
    led = L()
    rw._install(monkeypatch, led, module)
    monkeypatch.setattr(module, "log_search", led.log_search, raising=False)

    async def _prefs(_uid):
        return {"success": False}

    monkeypatch.setattr(text_routes, "get_user_preferences", _prefs)

    async def _persist(**kw):
        led.persist.append(kw.get("input_type"))
        return "s20-row-id"

    monkeypatch.setattr(text_routes, "_persist_comparison_bounded", _persist)

    def _track(*_a, **_k):
        return rw._done()

    monkeypatch.setattr(text_routes, "track_after_persist", _track)

    async def _state(subject):
        led.budget_reads.append(subject)
        if spent is None:
            return None
        return spent.pop(0) if isinstance(spent, list) and spent else spent

    async def _record(subject):
        led.budget_records.append(subject)

    monkeypatch.setattr(cg, "budget_state_async", _state)
    monkeypatch.setattr(cg, "record_refusal_async", _record)
    return led


class _Svc:
    def __init__(self, result=None, events=None):
        self.result = result
        self.events = events
        self.calls = 0

    async def compare_from_text(self, *_a, **_kw):
        self.calls += 1
        return copy.deepcopy(self.result)

    async def compare_from_text_streaming(self, *_a, **_kw):
        self.calls += 1
        for ev in self.events:
            yield ev


def _text_svc(monkeypatch, result=None, events=None):
    svc = _Svc(result, events)
    monkeypatch.setattr(text_routes, "get_comparison_service", lambda: svc)
    return svc


def _prod_on(monkeypatch, *extra):
    monkeypatch.setenv(METER, "true")
    monkeypatch.setenv(ENVELOPE, "true")
    monkeypatch.setenv(AUTHREQ, "true")
    for name in extra:
        monkeypatch.setenv(name, "true")


def _full_config(monkeypatch, truth=False):
    _prod_on(monkeypatch, B1, V2, ECHO, URLV2, KBI, FSM)
    if truth:
        monkeypatch.setenv(TRUTH, "true")


def _post(client, query=QUERY):
    return client.post("/api/v1/text/compare", json={"query": query})


def _get(client, query=QUERY):
    return client.get("/api/v1/text/compare", params={"q": query})


def _stream(client, query=QUERY, headers=None):
    return client.get("/api/v1/text/compare/stream", params={"q": query}, headers=headers or {})


def _frames(text):
    out = []
    for block in text.split("\n\n"):
        lines = [ln for ln in block.split("\n") if ln]
        if not lines:
            continue
        ev = next((ln[len("event: "):] for ln in lines if ln.startswith("event: ")), None)
        data = [ln[len("data: "):] for ln in lines if ln.startswith("data: ")]
        out.append((ev, json.loads(data[-1]) if data else None))
    return out


def _gate_rows(led):
    return [r for r in led.rows if isinstance(r.get("error_message"), str)
            and r["error_message"].startswith("result_gate:")]


def _assert_refused_ledger(led, uid, reason, *, refund=True, keys=None, label_prefix=None):
    if refund:
        assert led.refunds == [uid], led.refunds
        if keys is not None:
            assert led.refund_keys == [keys], led.refund_keys
    else:
        assert led.refunds == [], led.refunds
    assert led.history == [], led.history
    assert led.persist == [], led.persist
    assert led.lifetime == [], led.lifetime
    rows = _gate_rows(led)
    assert len(rows) == 1, led.rows
    assert rows[0]["error_message"] == "result_gate:" + reason, rows
    assert rows[0].get("success") is False, rows
    assert len(led.rows) == 1, led.rows
    if label_prefix and refund:
        ref = [i for i, x in enumerate(led.labels) if x.startswith("usage_refund.")]
        log = [i for i, x in enumerate(led.labels) if x.startswith("log_search.")]
        assert ref and log and ref[0] < log[0], led.labels


# ---------------------------------------------------------------- camera harness

class _Cam:
    def __init__(self, result=None):
        self.calls = []
        self.result = result if result is not None else copy.deepcopy(rw.DELIVERED)

    def factory(self):
        cam = self

        class _Service:
            async def compare_from_text(self, *a, **kw):
                cam.calls.append({"query": kw.get("query", a[0] if a else None),
                                  "vision_products": copy.deepcopy(kw.get("vision_products"))})
                return copy.deepcopy(cam.result)

        return _Service


def _camera(monkeypatch, vision, *, result=None, spent=None):
    led = _ledger(monkeypatch, image_routes, spent=spent)

    async def _identify(_images):
        return {"products": copy.deepcopy(vision), "cost": 0.003}

    monkeypatch.setattr(image_routes, "identify_products", _identify)
    from app.services import content_safety_service

    monkeypatch.setattr(content_safety_service, "get_content_safety_service",
                        lambda: rw._Safety(True, False))
    from app.services import audit_service

    monkeypatch.setattr(audit_service, "log_content_blocked", lambda **_kw: rw._done())

    async def _cprefs(_uid):
        return None

    monkeypatch.setattr(image_routes, "_camera_user_preferences", _cprefs)
    cam = _Cam(result)
    monkeypatch.setattr(image_routes, "StructuredComparisonService", cam.factory())
    return led, cam


def _post_image(client, fp=None):
    files = [("images", ("p%d.jpg" % i, JPEG, "image/jpeg")) for i in range(2)]
    headers = {"X-Device-Fingerprint": fp} if fp else {}
    return client.post("/api/v1/image/identify", files=files, headers=headers)


# ---------------------------------------------------------------- URL harness

def _url(monkeypatch, envelope, spent=None):
    led = _ledger(monkeypatch, url_routes, spent=spent)

    async def _allow(_url):
        return True

    monkeypatch.setattr(url_routes, "_validate_url_offloop_or_sync", _allow)
    calls = []

    async def _cmp(*a, **kw):
        calls.append(kw)
        return copy.deepcopy(envelope)

    monkeypatch.setattr(url_routes, "compare_from_urls", _cmp)
    return led, calls


def _post_url(client):
    return client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})


# ---------------------------------------------------------------- FY harness

@pytest.fixture
def fy_text(monkeypatch):
    p = fy._Patcher()
    state = fy._new_state()
    state["leaves"] = None

    def _factory():
        svc = scs.StructuredComparisonService()
        fy._install(p, svc, state)
        if state["leaves"] == "v10":
            calls = {"n": 0}

            async def _specs(*_a, **_k):
                calls["n"] += 1
                return {} if calls["n"] % 2 else {"display": "-", "battery": "-"}

            async def _none(*_a, **_k):
                return None

            async def _empty(*_a, **_k):
                return {}

            async def _no_rating(*_a, **_k):
                return {"rating": None, "review_count": 0, "rating_verified": False}

            svc._get_specs = _specs
            svc._get_price = _none
            svc._get_verified_rating = _no_rating
            svc._get_reviews = _empty
        return svc

    monkeypatch.setattr(text_routes, "get_comparison_service", _factory)
    try:
        yield state
    finally:
        p.undo()


def _pair_post(client, pair):
    return client.post("/api/v1/text/compare", json={"product_a": pair[0], "product_b": pair[1]})


# =============================================================== PIN: fixture statuses at base

def test_p00_fixture_statuses_measured_at_base():
    """PIN (5.2): the synthetic bodies' base assessment (the real assess_result) is what the
    rows below assume; a row whose fixture does not measure as stated is not kept."""
    a = rgm.assess_result
    assert a(body_sup())["status"] == "supported_result"
    assert a(body_v09())["reasons"][:1] == ["placeholder_identity"]
    assert a(body_v07())["reasons"][:1] == ["same_identity"]
    v10 = a(body_v10())
    assert v10["reasons"] == ["no_evidence"] and v10["data_coverage"] == 0, v10["reasons"]
    assert v10["identity_confidence"] == "medium", v10["identity_confidence"]
    v10b = a(body_v10_one())
    assert v10b["reasons"] == ["no_evidence"] and v10b["identity_confidence"] == "high", v10b
    cat = a(body_cat(), product_categories=["electronics", "fragrances"])
    assert cat["reasons"] == ["category_conflict"], cat["reasons"]
    for name in LANE1:
        assert a(_lane1(name))["status"] == "supported_result", name
    bh, ae = url_real("bh"), url_real("ae")
    assert [p["price"]["amount"] for p in bh["products"]] == ["490.00", "4099"]
    assert bh["products"][1]["reviews"]["rating"] == "5"
    assert [p["price"]["amount"] for p in ae["products"]] == ["175.000", "271.0"]


# =============================================================== unit rows (result_gate)

@pytest.mark.parametrize("raw,want", TRUTHY_TABLE, ids=[repr(r[0]) for r in TRUTHY_TABLE])
def test_r01_flag_reader_table(monkeypatch, raw, want):
    if raw is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, raw)
    assert _fn("result_gate_enabled")() is want


def test_r02_constants():
    assert _sym("GATE_REASONS") == GATE_REASONS
    assert _sym("CAMERA_GATE_REASONS") == CAMERA_REASONS
    assert _sym("GATE_CODE") == "INSUFFICIENT_DATA"
    assert _sym("GATE_LOG_PREFIX") == "result_gate:"
    assert _sym("GATE_REFUSAL_MESSAGE") == H6_MESSAGE
    assert _sym("CAMERA_GATE_MESSAGE") == CAMERA_MESSAGE
    h6 = asyncio.run(fy._scenario("rest", "just one thing"))["payload"]
    if h6.get("code") == "INSUFFICIENT_DATA":
        assert h6.get("error") == _sym("GATE_REFUSAL_MESSAGE"), h6.get("error")


@pytest.mark.parametrize("name", LANE1)
def test_r03_gate_reason_lane1_supported(name):
    assert _fn("gate_reason")(_lane1(name)) is None


def test_r04_v09_placeholder():
    assert _fn("gate_reason")(body_v09()) == "placeholder_identity"


def test_r05_same_identity():
    gr = _fn("gate_reason")
    assert gr(body_v07()) == "same_identity"
    b = body_sup()
    _set_identity(b, 0, "GUESS", "Logo Tee")
    _set_identity(b, 1, "GUESS", "Denim Shirt")
    assert gr(b) is None


def test_r06_category():
    gr = _fn("gate_reason")
    assert gr(body_sup(), product_categories=["electronics", "fragrances"]) == "category_conflict"
    assert gr(body_sup(), product_categories=["other", "fragrances"]) is None
    b = body_sup()
    b["category_used"] = "toys"
    assert gr(b) == "category_conflict"


def _w412_rows():
    return json.loads((FIX / "w412_corpus_min.json").read_text(encoding="utf-8"))


def test_r07_corpus():
    """R7 (re-measured at 6869a3e6 through the real assess_result): every success:True corpus
    row maps to exactly the reason its first assessment reason maps to."""
    gr = _fn("gate_reason")
    mapping = {"placeholder_identity": "placeholder_identity", "same_identity": "same_identity",
               "unsupported_category": "category_conflict", "category_conflict": "category_conflict",
               "no_evidence": "no_evidence"}
    seen = 0
    for row in _w412_rows():
        body = row.get("full_response") if isinstance(row, dict) else None
        if not isinstance(body, dict):
            continue
        body = dict(body)
        body.setdefault("success", True)
        reasons = [r for r in rgm.assess_result(body)["reasons"] if r in mapping]
        want = mapping[reasons[0]] if reasons else None
        assert gr(body) == want, (row.get("row"), want)
        seen += 1
    assert seen >= 20, seen


def _r08_bodies():
    out = [(b, None) for b in (body_sup(), body_v09(), body_v07(), body_v10(), body_v10_one())]
    out.append((body_sup(), ["electronics", "fragrances"]))
    out.append((body_sup(), ["other", "fragrances"]))
    for name in LANE1:
        out.append((_lane1(name), None))
    for row in _w412_rows():
        body = row.get("full_response") if isinstance(row, dict) else None
        if isinstance(body, dict):
            body = dict(body)
            body.setdefault("success", True)
            out.append((body, None))
    return out


def test_r08_mapping_completeness():
    gr = _fn("gate_reason")
    for body, cats in _r08_bodies():
        supported = rgm.assess_result(body, product_categories=cats)["status"] == "supported_result"
        assert (gr(body, product_categories=cats) is None) == supported


def test_r09_totality():
    gr, ugr, cgr = _fn("gate_reason"), _fn("url_gate_reason"), _fn("camera_gate_reason")
    for bad in (None, 1, "x", [], {"success": False, "products": []}):
        assert _call_total(gr, bad) is None, bad
        assert _call_total(ugr, bad) is None, bad
    # products missing: url_gate_reason answers None (it needs two dicts); gate_reason maps
    # the assessment, which reads a product-less success body as a placeholder (w412 row 6)
    assert _call_total(ugr, {"success": True}) is None
    assert _call_total(ugr, {"success": True, "products": [{"brand": "A", "name": "B"}]}) is None
    assert _call_total(cgr, None, None) == "placeholder_identity"
    assert _call_total(cgr, "x", _v1("Lattafa", "Asad")) == "placeholder_identity"


def test_r10_url_gate_synthetic():
    ugr = _fn("url_gate_reason")
    assert ugr(url_v09()) == "placeholder_identity"
    assert ugr(url_same()) == "same_identity"
    assert ugr(url_noev()) == "no_evidence"
    assert ugr(url_v03()) is None


@pytest.mark.parametrize("bad", ["0", "abc", "1e400", "1" * 400, "-5", "nan", True,
                                 chr(0x0661) + chr(0x0662) + chr(0x0663)],
                         ids=["zero", "abc", "1e400", "long", "neg", "nan", "bool", "arabic_indic"])
def test_r11_url_string_reading(bad):
    ugr = _fn("url_gate_reason")
    assert ugr(url_real("bh")) is None
    assert ugr(url_real("ae")) is None
    env = _url_env(_up("Lattafa", "Asad", bad), _up("Lattafa", "Khamrah", "12.5"))
    assert ugr(env) == "no_evidence", bad
    rated = _url_env(_up("Lattafa", "Asad", rating="5"), _up("Lattafa", "Khamrah", rating="4.5"))
    assert ugr(rated) is None
    for r in ("6", "0"):
        env = _url_env(_up("Lattafa", "Asad", rating=r), _up("Lattafa", "Khamrah", rating="4"))
        assert ugr(env) == "no_evidence", r


def test_r12_url_one_sided():
    ugr = _fn("url_gate_reason")
    assert ugr(_url_env(_up("Lattafa", "Asad", 10.0), _up("Lattafa", "Khamrah"))) == "no_evidence"
    assert ugr(_url_env(_up("Lattafa", "Asad", 10.0), _up("", "Unknown Product", 9.0))) \
        == "placeholder_identity"


def test_r13_camera_gate_table():
    cgr = _fn("camera_gate_reason")

    def run(key, cats=None):
        v = VISION[key]()
        return cgr(v[0], v[1], categories=cats)

    assert run("V07") == "same_identity"
    assert run("V04") == "low_confidence"
    assert run("LOW1") == "low_confidence"
    assert run("V1_LOW") is None
    assert run("PH0") == "placeholder_identity"
    assert run("PH1") == "placeholder_identity"
    assert run("DISTINCT", ["electronics", "fragrances"]) == "category_conflict"
    assert run("DISTINCT", ["other", "other"]) is None


def test_r14_camera_snapshot():
    cgr = _fn("camera_gate_reason")
    v = VISION["ENRICH"]()
    ids = [(p["brand"], p["name"]) for p in v]
    enriched = copy.deepcopy(v)
    enriched[0]["name"] = "Unknown Product 100ml"
    assert cgr(enriched[0], enriched[1], identities=ids) == "placeholder_identity"
    vb = VISION["ENRICH_BRAND"]()
    ids_b = [(p["brand"], p["name"]) for p in vb]
    eb = copy.deepcopy(vb)
    eb[0]["name"] = "Unknown Product 100 ml"
    assert cgr(eb[0], eb[1], identities=ids_b) == "placeholder_identity"
    assert cgr(enriched[0], enriched[1]) is None  # documents BL2: the enriched name escapes


def test_r15_camera_features_ignored():
    cgr = _fn("camera_gate_reason")
    v = VISION["FEAT"]()
    assert cgr(v[0], v[1]) == "same_identity"
    s = VISION["SIZES"]()
    assert cgr(s[0], s[1]) is None


def test_r16_refusal_body_shape():
    body_fn = _fn("gate_refusal_body")
    b = body_sup()
    out = body_fn(b, "no_evidence")
    assert list(out) == ["success", "error", "code", "elapsed_seconds", "total_cost",
                         "api_calls", "reason"]
    assert out["success"] is False and out["error"] == H6_MESSAGE
    assert out["code"] == "INSUFFICIENT_DATA" and out["reason"] == "no_evidence"
    assert out["elapsed_seconds"] == b["metadata"]["elapsed_seconds"]
    assert out["total_cost"] == b["metadata"]["total_cost"]
    assert out["api_calls"] == b["metadata"]["api_calls"]
    for bad in (float("inf"), float("nan"), True, -1):
        b2 = body_sup()
        b2["metadata"].update({"elapsed_seconds": bad, "total_cost": bad, "api_calls": bad})
        o2 = body_fn(b2, "no_evidence")
        assert o2["elapsed_seconds"] == 0 and o2["total_cost"] == 0 and o2["api_calls"] == 0, bad


def test_r17_refusal_flag_first(monkeypatch):
    refusal = _fn("result_gate_refusal")
    rec = Rec(monkeypatch)
    monkeypatch.delenv(FLAG, raising=False)
    assert refusal(body_v09()) is None
    assert rec.total() == 0, rec.calls
    monkeypatch.setenv(FLAG, "true")
    out = refusal(body_v09())
    assert isinstance(out, dict) and out.get("reason") == "placeholder_identity", out
    assert rec.calls["gate_reason"] == 1 and rec.calls["url_gate_reason"] == 0, rec.calls
    out2 = refusal(url_v09(), url_mode=True)
    assert isinstance(out2, dict) and out2.get("reason") == "placeholder_identity", out2
    assert rec.calls["url_gate_reason"] == 1, rec.calls


def test_r18_log_message():
    msg = _fn("gate_log_message")
    assert msg("no_evidence") == "result_gate:no_evidence"
    assert msg("low_confidence") == "result_gate:low_confidence"
    assert msg("x") == "result_gate:unknown"
    assert msg([]) == "result_gate:unknown"


# =============================================================== text POST / GET

def _text_refused(resp, reason):
    assert resp.status_code == 400, (resp.status_code, resp.text[:300])
    j = resp.json()
    assert set(j) == ENVELOPE_KEYS | {"reason"}, sorted(j)
    assert j["code"] == "INSUFFICIENT_DATA" and j["reason"] == reason, j
    assert j["error"] == H6_MESSAGE, j["error"]


@pytest.mark.parametrize("truth", [False, True], ids=["w413_off", "w413_on"])
def test_r20_text_post_v09_refused(monkeypatch, client, authed, truth):
    _prod_on(monkeypatch, FLAG)
    if truth:
        monkeypatch.setenv(TRUTH, "true")
    led = _ledger(monkeypatch, text_routes)
    _text_svc(monkeypatch, body_v09())
    resp = _post(client)
    _text_refused(resp, "placeholder_identity")
    _assert_refused_ledger(led, authed["id"], "placeholder_identity",
                           keys={"daily": "d:" + authed["id"], "monthly": "m:" + authed["id"]},
                           label_prefix=True)
    assert _gate_rows(led)[0].get("cost") == body_v09()["metadata"]["total_cost"]


def test_r21_text_get_v07_refused(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    led = _ledger(monkeypatch, text_routes)
    _text_svc(monkeypatch, body_v07())
    _text_refused(_get(client), "same_identity")
    _assert_refused_ledger(led, authed["id"], "same_identity",
                           keys={"daily": "d:" + authed["id"], "monthly": "m:" + authed["id"]})


def test_r22_text_post_v10_no_evidence(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    led = _ledger(monkeypatch, text_routes)
    _text_svc(monkeypatch, body_v10())
    _text_refused(_post(client), "no_evidence")
    _assert_refused_ledger(led, authed["id"], "no_evidence")


def test_r23_real_orchestrator_v10(monkeypatch, client, authed, fy_text):
    _prod_on(monkeypatch, FLAG)
    led = _ledger(monkeypatch, text_routes)
    fy_text["leaves"] = "v10"
    resp = _pair_post(client, FY_V10_PAIR)
    _text_refused(resp, "no_evidence")
    _assert_refused_ledger(led, authed["id"], "no_evidence")


def test_r24_real_orchestrator_v10_both_flags(monkeypatch, client, authed, fy_text):
    _prod_on(monkeypatch, FLAG, B1)
    led = _ledger(monkeypatch, text_routes)
    fy_text["leaves"] = "v10"
    built = []
    real = rb.build_comparison_response

    def _rec(*a, **k):
        out = real(*a, **k)
        built.append(copy.deepcopy(out))
        return out

    monkeypatch.setattr(scs, "build_comparison_response", _rec)
    resp = _pair_post(client, FY_V10_PAIR)
    _text_refused(resp, "no_evidence")
    assert built and built[-1]["metadata"].get("result_status") == "partial_no_winner", \
        [b["metadata"].get("result_status") for b in built]
    _assert_refused_ledger(led, authed["id"], "no_evidence")


def test_r25_category_conflict_b2_alone(monkeypatch, client, authed, fy_text):
    _prod_on(monkeypatch, FLAG)
    led = _ledger(monkeypatch, text_routes)
    _text_refused(_pair_post(client, CONFLICT_PAIR), "category_conflict")
    _assert_refused_ledger(led, authed["id"], "category_conflict")


def test_r26_category_conflict_both_flags(monkeypatch, client, authed, fy_text):
    _prod_on(monkeypatch, FLAG, B1)
    _ledger(monkeypatch, text_routes)
    _text_refused(_pair_post(client, CONFLICT_PAIR), "category_conflict")


def test_r27_supported_real_orchestrator_stamp(monkeypatch, client, authed, fy_text):
    _prod_on(monkeypatch, FLAG)
    led = _ledger(monkeypatch, text_routes)
    resp = _post(client, fy.QUERY)
    assert resp.status_code == 200, resp.text[:300]
    md = resp.json().get("metadata") or {}
    assert md.get("product_categories") == ["electronics", "electronics"], md.get("product_categories")
    assert "result_status" not in md
    assert led.refunds == [] and led.history == ["text"] and led.lifetime == [authed["id"]]


def test_r28_anonymous_text_refusal(monkeypatch, client, anonymous):
    _prod_on(monkeypatch, FLAG)
    monkeypatch.setenv(AUTHREQ, "false")  # R-S20-11: explicit
    led = _ledger(monkeypatch, text_routes)
    _text_svc(monkeypatch, body_v09())
    _text_refused(_post(client), "placeholder_identity")
    assert led.refunds == [] and led.consumes == []
    rows = _gate_rows(led)
    assert len(rows) == 1 and rows[0].get("user_id") is None, led.rows


def test_r29_hard_cap_partials(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    _ledger(monkeypatch, text_routes)
    partial = asyncio.run(fy._scenario("rest", fy.QUERY, cap=0.5, slow=True))["payload"]
    assert partial.get("success") is True and (partial.get("metadata") or {}).get("partial") is True
    assert rgm.assess_result(partial)["data_coverage"] >= 1
    _text_svc(monkeypatch, partial)
    r1 = _post(client)
    assert r1.status_code == 200 and r1.json()["metadata"].get("partial") is True, r1.text[:200]
    p0 = body_v10()
    p0["metadata"]["partial"] = True
    _text_svc(monkeypatch, p0)
    _text_refused(_post(client), "no_evidence")


# ---------------------------------------------------------------- device quota (S81-09 FakeRedis)

def _s09():
    from tests import test_s81_s09_device_quota as s09
    return s09


def _quota_setup(monkeypatch, result=None, events=None, vision=None):
    s09 = _s09()
    s09._full_config(monkeypatch, quota="true")
    s09._freeze(monkeypatch, s09.T0)
    s09._tier(monkeypatch, "free", 5)
    red = s09._install_redis(monkeypatch, {s09._D(): 1, s09._DV(): 1})
    s09._stub_routes(monkeypatch, result=result, events=events, vision=vision)
    lifetime, history = [], []

    def _life(user_id, *_a, **_k):
        lifetime.append(user_id)
        return rw._done()

    def _save(**kw):
        history.append(kw.get("input_type"))
        return rw._done()

    for mod in (text_routes, url_routes, image_routes):
        monkeypatch.setattr(mod, "record_lifetime_comparison", _life, raising=False)
        monkeypatch.setattr(mod, "save_comparison_and_track_cohort", _save, raising=False)
    refund_args = []
    real_refund = usage_service.refund_comparison_credit

    def _refund(user_id, consumed_keys=None):
        refund_args.append(copy.deepcopy(consumed_keys))
        return real_refund(user_id, consumed_keys)

    for mod in (text_routes, url_routes, image_routes):
        monkeypatch.setattr(mod, "refund_comparison_credit", _refund, raising=False)
    return s09, red, lifetime, history, refund_args


@pytest.mark.parametrize("site", ["text_post", "text_get", "text_stream", "url_post", "image"])
def test_r30_device_quota_keys(monkeypatch, site):
    """R30 / R58 + R-S20-32: real consume under ENABLE_DEVICE_DAILY_QUOTA ON (one Lua EVAL);
    the refusal refunds with the consumed {daily, device_daily} keys through ONE
    DEVICE_REFUND_SCRIPT EVAL; lifetime 0; history 0."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(ENVELOPE, "true")
    v10 = body_v10()
    s09, red, lifetime, history, refund_args = _quota_setup(
        monkeypatch, result=v10, events=[("settle_complete", v10), ("complete", v10)],
        vision={"products": VISION["V07"](), "cost": 0.003})
    if site == "url_post":
        async def _cmp(*_a, **_k):
            return url_noev()

        monkeypatch.setattr(url_routes, "compare_from_urls", _cmp)
    with s09._as_user(s09.USER):
        with TestClient(app_main.app, raise_server_exceptions=False) as c:
            resp = s09._req(c, site)
    assert resp.status_code != 429, resp.text[:200]
    assert len(s09._evals(red, "consume")) == 1, red.calls
    assert refund_args == [{"daily": s09._D(), "device_daily": s09._DV()}], refund_args
    refunds = s09._evals(red, "refund")
    assert refunds == [["eval", "refund", [s09._D(), s09._DV()], []]], red.calls
    assert lifetime == [] and history == [], (lifetime, history)


def test_r30b_stream_no_fingerprint_stash(monkeypatch):
    """R-S20-32: the no-fingerprint STREAM variant: consumed_keys {daily} only; the keyed
    refund resolves through the request-scoped stash inside the generator's finally (or the
    keyed account window); the row PINS what the StreamingResponse task sees."""
    monkeypatch.setenv(FLAG, "true")
    v10 = body_v10()
    s09, red, lifetime, history, refund_args = _quota_setup(
        monkeypatch, events=[("settle_complete", v10), ("complete", v10)])
    with s09._as_user(s09.USER):
        with TestClient(app_main.app, raise_server_exceptions=False) as c:
            resp = s09._req(c, "text_stream", fp=None)
    assert resp.status_code == 200
    assert refund_args == [{"daily": s09._D()}], refund_args
    assert lifetime == [] and history == []
    # the account-only debit is refunded by ONE EVAL over [daily]: what the
    # StreamingResponse task's finally sees (the stash names this user, no device key)
    assert s09._evals(red, "refund") == [["eval", "refund", [s09._D()], []]], red.calls


# ---------------------------------------------------------------- refusal budget (R-S20-38)

def _budget_route(monkeypatch, client, site, spent):
    monkeypatch.setenv(FRAG, "true")
    if site in ("text_post", "text_get", "stream"):
        led = _ledger(monkeypatch, text_routes, spent=spent)
        frag = body_v10()
        if site == "stream":
            _text_svc(monkeypatch, events=[("settle_complete", frag), ("complete", frag)])
            return led, _stream(client, FRAG_QUERY)
        _text_svc(monkeypatch, frag)
        return led, (_post(client, FRAG_QUERY) if site == "text_post" else _get(client, FRAG_QUERY))
    if site == "url":
        env = url_noev()
        led, _calls = _url(monkeypatch, env, spent=spent)

        async def _budget(_user, _route):
            return None

        monkeypatch.setattr(url_routes, "_url_refusal_budget", _budget)
        return led, _post_url(client)
    led, _cam = _camera(monkeypatch, VISION["FRAG_SAME"](), spent=spent)
    return led, _post_image(client)


BUDGET_SITES = ["text_post", "text_get", "stream", "url", "camera"]


@pytest.mark.parametrize("site", BUDGET_SITES)
def test_r35_refusal_counted_on_budget(monkeypatch, client, authed, site):
    """R-S20-38 counted: FRAGRANCE gate ON, budget not spent: ONE record_refusal_async on the
    route's subject; the refund still made; one row; lifetime 0; history 0."""
    _prod_on(monkeypatch, FLAG)
    led, resp = _budget_route(monkeypatch, client, site, spent=None)
    assert resp.status_code in (200, 400), resp.text[:200]
    assert len(led.budget_records) == 1, (site, led.budget_records)
    reason = "same_identity" if site == "camera" else "no_evidence"
    _assert_refused_ledger(led, authed["id"], reason)


@pytest.mark.parametrize("site", BUDGET_SITES)
def test_r36_refusal_budget_spent_keeps_credit(monkeypatch, client, authed, site):
    """R-S20-38 spent: the budget is already spent at the refusal exit: NO refund (the credit
    is kept); still no lifetime, no history, one result_gate row."""
    _prod_on(monkeypatch, FLAG)
    # the route's own pre-consume budget read sees an open budget; the refusal exit sees it spent
    spent = [None, (3600, "2026-11-06T00:00:00+03:00")]
    if site == "url":
        spent = (3600, "2026-11-06T00:00:00+03:00")
    led, resp = _budget_route(monkeypatch, client, site, spent=spent)
    assert resp.status_code in (200, 400), resp.text[:200]
    reason = "same_identity" if site == "camera" else "no_evidence"
    _assert_refused_ledger(led, authed["id"], reason, refund=False)
    assert led.consumes == [authed["id"]]


@pytest.mark.parametrize("site", BUDGET_SITES)
def test_r37_refusal_gate_off_refunded_uncounted(monkeypatch, client, authed, site):
    """R-S20-38 gate OFF: refunded, never counted (no budget read, no record)."""
    _prod_on(monkeypatch, FLAG)
    led, resp = _budget_route(monkeypatch, client, site, spent=None)
    monkeypatch.delenv(FRAG, raising=False)
    led2, resp2 = _budget_route(monkeypatch, client, site, spent=None)
    monkeypatch.delenv(FRAG, raising=False)
    # the second harness replaced the first; rerun with the gate OFF on a fresh ledger
    monkeypatch.setenv(FRAG, "false")
    if site in ("text_post", "text_get", "stream"):
        led3 = _ledger(monkeypatch, text_routes)
        frag = body_v10()
        if site == "stream":
            _text_svc(monkeypatch, events=[("settle_complete", frag), ("complete", frag)])
            _stream(client, FRAG_QUERY)
        else:
            _text_svc(monkeypatch, frag)
            (_post if site == "text_post" else _get)(client, FRAG_QUERY)
    elif site == "url":
        led3, _c = _url(monkeypatch, url_noev())
        _post_url(client)
    else:
        led3, _cam = _camera(monkeypatch, VISION["FRAG_SAME"]())
        _post_image(client)
    reason = "same_identity" if site == "camera" else "no_evidence"
    _assert_refused_ledger(led3, authed["id"], reason)
    assert led3.budget_records == [] and led3.budget_reads == [], (led3.budget_records, led3.budget_reads)


def test_r31_fragrance_gate_counts_result_gate_refusal(monkeypatch, client, authed, fy_text):
    """R31 as re-cut by R-S20-38: FRAGRANCE gate ON, FY_V10_FRAG via POST: 400
    INSUFFICIENT_DATA reason no_evidence (not CATEGORY_NOT_LIVE); the refusal is COUNTED once."""
    _prod_on(monkeypatch, FLAG, FRAG)
    led = _ledger(monkeypatch, text_routes)
    fy_text["leaves"] = "v10"
    resp = _pair_post(client, FY_V10_FRAG_PAIR)
    _text_refused(resp, "no_evidence")
    assert len(led.budget_records) == 1, led.budget_records


@pytest.mark.parametrize("site", ["post", "get", "url"])
def test_r32_text_info_line(monkeypatch, client, authed, caplog, site):
    _prod_on(monkeypatch, FLAG)
    if site == "url":
        _url(monkeypatch, url_v09())
    else:
        _ledger(monkeypatch, text_routes)
        _text_svc(monkeypatch, body_v09())
    with caplog.at_level(logging.INFO):
        if site == "post":
            _post(client)
        elif site == "get":
            _get(client)
        else:
            _post_url(client)
    recs = [r for r in caplog.records if str(r.msg).startswith("[RESULT_GATE]")]
    assert len(recs) == 1, [r.getMessage() for r in caplog.records][-10:]
    assert recs[0].levelno == logging.INFO
    assert recs[0].msg == "[RESULT_GATE] refused input=%s reason=%s"
    assert recs[0].args == ("url" if site == "url" else "text", "placeholder_identity")
    for r in recs:
        assert QUERY not in r.getMessage() and URL1 not in r.getMessage()
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR
                and "RESULT_GATE" in r.getMessage()]


# ---------------------------------------------------------------- G3 tail (R-S20-18 / -23)

def _kb_recorders(monkeypatch):
    seen = {"snaps": [], "scheduled": []}
    real_build = kb_ingest.build_job

    def _build(*a, **k):
        snap = real_build(*a, **k)
        seen["snaps"].append(snap)
        return snap

    monkeypatch.setattr(kb_ingest, "build_job", _build)

    def _ff(coro, label=None, *_a, **_k):
        seen["scheduled"].append(label)
        try:
            coro.close()
        except Exception:  # noqa: BLE001
            pass

    monkeypatch.setattr(scs, "_fire_and_forget", _ff)
    return seen


def test_r33_g3_tail_no_evidence(monkeypatch, client, authed, fy_text):
    _prod_on(monkeypatch, FLAG, KBI)
    _ledger(monkeypatch, text_routes)
    seen = _kb_recorders(monkeypatch)
    fy_text["leaves"] = "v10"
    resp = _pair_post(client, FY_V10_FRAG_PAIR)
    _text_refused(resp, "no_evidence")
    assert len(seen["snaps"]) == 1, seen
    assert seen["scheduled"].count("kb_ingest") == 1, seen["scheduled"]
    snap = seen["snaps"][0]
    assert snap["identity_confidence"] == "medium", snap["identity_confidence"]
    fs = snap.get("field_status") or {}
    states = json.dumps(fs)
    assert "unknown" in states, fs


@pytest.mark.parametrize("pair,reason", [(CONFLICT_PAIR, "category_conflict"),
                                         (("Lattafa Asad", "Lattafa Asad"), "same_identity")],
                         ids=["conflict", "same"])
def test_r34_g3_tail_identity_classes(monkeypatch, client, authed, fy_text, pair, reason):
    _prod_on(monkeypatch, FLAG, KBI)
    _ledger(monkeypatch, text_routes)
    seen = _kb_recorders(monkeypatch)
    _text_refused(_pair_post(client, pair), reason)
    assert seen["scheduled"].count("kb_ingest") == 1, seen["scheduled"]
    assert seen["snaps"][0]["identity_confidence"] in ("low", "unresolved"), seen["snaps"][0]


# =============================================================== stream

@pytest.mark.parametrize("truth", [False, True], ids=["w413_off", "w413_on"])
def test_r40_stream_refusal_frames_and_accounting(monkeypatch, client, authed, caplog, truth):
    _prod_on(monkeypatch, FLAG)
    if truth:
        monkeypatch.setenv(TRUTH, "true")
    led = _ledger(monkeypatch, text_routes)
    v09 = body_v09()
    _text_svc(monkeypatch, events=[("status", {"progress": 10}), ("verdict", {"x": 1}),
                                   ("settle_complete", v09), ("complete", v09)])
    with caplog.at_level(logging.INFO):
        resp = _stream(client)
    frames = _frames(resp.text)
    terms = [d for e, d in frames if e in ("settle_complete", "complete")]
    assert len(terms) == 2, frames
    for d in terms:
        assert list(d) == ["success", "error", "code", "elapsed_seconds", "total_cost",
                           "api_calls", "reason"], d
        assert d["success"] is False and d["code"] == "INSUFFICIENT_DATA"
        assert d["reason"] == "placeholder_identity" and d["error"] == H6_MESSAGE
    _assert_refused_ledger(led, authed["id"], "placeholder_identity",
                           keys={"daily": "d:" + authed["id"], "monthly": "m:" + authed["id"]})
    assert not [x for x in led.labels if x.endswith("terminal_failure") or x.endswith(".success")]
    recs = [r for r in caplog.records if str(r.msg).startswith("[RESULT_GATE]")]
    assert [r.args for r in recs] == [("text_stream", "placeholder_identity")]


def test_r41_stream_refusal_not_persisted_under_echo(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG, ECHO)
    led = _ledger(monkeypatch, text_routes)
    v09 = body_v09()
    _text_svc(monkeypatch, events=[("settle_complete", v09), ("complete", v09)])
    frames = _frames(_stream(client).text)
    assert led.persist == [], led.persist
    for e, d in frames:
        if e in ("settle_complete", "complete"):
            assert "comparison_id" not in d, d


def test_r62_stream_error_then_refusal_terminal(monkeypatch, client, authed):
    """R-S20-33: an error event then complete(BODY_V09): the existing `elif had_error` arm
    wins (keyless label usage_refund.text_stream), no result_gate row."""
    _prod_on(monkeypatch, FLAG)
    led = _ledger(monkeypatch, text_routes)
    v09 = body_v09()
    _text_svc(monkeypatch, events=[("error", {"error": "Streaming comparison failed",
                                              "code": "TIMEOUT"}), ("complete", v09)])
    _stream(client)
    assert "usage_refund.text_stream" in led.labels, led.labels
    assert led.refund_keys == [None], led.refund_keys
    assert _gate_rows(led) == [], led.rows
    assert led.lifetime == [] and led.history == []
    # the RED half: the gate decided the terminal (the frame carries the reason)
    assert _sym("GATE_CODE") == "INSUFFICIENT_DATA"


# =============================================================== camera

def _camera_refused(resp, cam, reason, cost=0.003):
    assert resp.status_code == 200, resp.text[:300]
    j = resp.json()
    assert j == {"success": False, "action": "error", "error": CAMERA_MESSAGE,
                 "vision_cost": cost, "reason": reason}, j
    assert cam.calls == [], cam.calls


def test_r50_camera_same_identity(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    led, cam = _camera(monkeypatch, VISION["V07"]())
    rec = Rec(monkeypatch)
    _camera_refused(_post_image(client), cam, "same_identity")
    _assert_refused_ledger(led, authed["id"], "same_identity",
                           keys={"daily": "d:" + authed["id"], "monthly": "m:" + authed["id"]})
    assert _gate_rows(led)[0].get("cost") == 0.003
    assert rec.calls["camera_gate_reason"] == 1, rec.calls


@pytest.mark.parametrize("key", ["V04", "LOW1"])
def test_r51_camera_low_confidence(monkeypatch, client, authed, key):
    _prod_on(monkeypatch, FLAG, V2)
    led, cam = _camera(monkeypatch, VISION[key]())
    _camera_refused(_post_image(client), cam, "low_confidence")
    assert _gate_rows(led)[0]["error_message"] == "result_gate:low_confidence"


def test_r52_camera_two_placeholders(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    led, cam = _camera(monkeypatch, [_v1("Unknown", "Unknown Product"), _v1("", "Unknown")])
    _camera_refused(_post_image(client), cam, "placeholder_identity")


@pytest.mark.parametrize("key", ["PH0", "PH1"])
def test_r53_camera_one_placeholder_is_error(monkeypatch, client, authed, key):
    _prod_on(monkeypatch, FLAG)
    led, cam = _camera(monkeypatch, VISION[key]())
    _camera_refused(_post_image(client), cam, "placeholder_identity")
    assert led.refunds == [authed["id"]]


@pytest.mark.parametrize("key", ["ENRICH", "ENRICH_BRAND"])
def test_r54_camera_enrichment_evasion(monkeypatch, client, authed, key):
    _prod_on(monkeypatch, FLAG)
    led, cam = _camera(monkeypatch, VISION[key]())
    _camera_refused(_post_image(client), cam, "placeholder_identity")


def test_r55_camera_category_conflict_v2(monkeypatch, client, authed):
    """R-S20-39: a conflict between two V2 `_category` values is refused."""
    _prod_on(monkeypatch, FLAG, V2)
    led, cam = _camera(monkeypatch, VISION["CAT_V2"]())
    _camera_refused(_post_image(client), cam, "category_conflict")


def test_p19_camera_v1_stub_conflict_delivered(monkeypatch, client, authed):
    """PIN (R-S20-39, the re-cut R55 V1 half): under V1 a stub-derived conflict
    (Samsung phone vs Dior parfum) is DELIVERED, flag ON and OFF; compare once."""
    _prod_on(monkeypatch, FLAG)
    led, cam = _camera(monkeypatch, VISION["CAT_V1"]())
    resp = _post_image(client)
    assert resp.status_code == 200 and resp.json().get("action") == "comparison", resp.text[:200]
    assert len(cam.calls) == 1
    assert _gate_rows(led) == []


def test_r56_camera_v2_features_same_identity(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG, V2)
    led, cam = _camera(monkeypatch, VISION["FEAT"]())
    _camera_refused(_post_image(client), cam, "same_identity")


def test_r57_camera_anon_refund_keys(monkeypatch, client, anonymous):
    _prod_on(monkeypatch, FLAG, ANON)
    monkeypatch.setenv(AUTHREQ, "false")  # R-S20-11: explicit
    fp = _fp()
    led, cam = _camera(monkeypatch, VISION["V07"]())
    _camera_refused(_post_image(client, fp=fp), cam, "same_identity")
    assert led.anon_refunds == [fp], led.anon_refunds
    assert led.anon_refund_keys == [{"daily": "d:anon:" + fp, "monthly": "m:anon:" + fp}]


def test_r59_camera_info_line(monkeypatch, client, authed, caplog):
    _prod_on(monkeypatch, FLAG)
    _camera(monkeypatch, VISION["V07"]())
    with caplog.at_level(logging.INFO):
        _post_image(client)
    recs = [r for r in caplog.records if str(r.msg).startswith("[RESULT_GATE]")]
    assert [r.args for r in recs] == [("camera", "same_identity")]
    for r in recs:
        assert "GUESS" not in r.getMessage()


def test_r60_camera_fragrance_gate_order(monkeypatch, client, authed):
    """R60 as re-cut by R-S20-38: FRAGRANCE gate ON, a fragrance same-identity pair: the S81-10
    pair gate passes, the S81-20 refusal fires (same_identity) and is COUNTED once."""
    _prod_on(monkeypatch, FLAG, FRAG)
    led, cam = _camera(monkeypatch, VISION["FRAG_SAME"]())
    _camera_refused(_post_image(client), cam, "same_identity")
    assert len(led.budget_records) == 1, led.budget_records


def test_r61_camera_category_not_live_wins(monkeypatch, client, authed, caplog):
    """R-S20-31 (M39): FRAGRANCE gate ON + RESULT gate ON, a non-fragrance same-identity
    camera pair: the S81-10 camera_refusal_body wins (CATEGORY_NOT_LIVE, no reason key);
    record_refusal_async once; compare 0; one refund labelled
    usage_refund.image.category_not_live; no result_gate row; no [RESULT_GATE] line."""
    _prod_on(monkeypatch, FLAG, FRAG)
    led, cam = _camera(monkeypatch, [_v1("Samsung", "Galaxy S24 phone"),
                                     _v1("Samsung", "Galaxy S24 phone")])
    with caplog.at_level(logging.INFO):
        resp = _post_image(client)
    j = resp.json()
    assert j.get("code") == "CATEGORY_NOT_LIVE" and "reason" not in j, j
    assert len(led.budget_records) == 1 and cam.calls == []
    assert led.refunds == [authed["id"]]
    assert "usage_refund.image.category_not_live" in led.labels, led.labels
    assert _gate_rows(led) == []
    assert not [r for r in caplog.records if str(r.msg).startswith("[RESULT_GATE]")]
    assert callable(getattr(rgm, "camera_gate_reason", None)), "RED at base: the gate is absent"


# =============================================================== URL

@pytest.mark.parametrize("truth", [False, True], ids=["w413_off", "w413_on"])
def test_r70_url_v09_refused(monkeypatch, client, authed, truth):
    _prod_on(monkeypatch, FLAG)
    if truth:
        monkeypatch.setenv(TRUTH, "true")
    led, _c = _url(monkeypatch, url_v09())
    _text_refused(_post_url(client), "placeholder_identity")
    _assert_refused_ledger(led, authed["id"], "placeholder_identity",
                           keys={"daily": "d:" + authed["id"], "monthly": "m:" + authed["id"]})


def test_r71_url_no_evidence(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    _url(monkeypatch, url_noev())
    _text_refused(_post_url(client), "no_evidence")


def test_r72_url_same_identity(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    _url(monkeypatch, url_same())
    _text_refused(_post_url(client), "same_identity")


@pytest.mark.parametrize("v2", [False, True], ids=["url_v1", "url_v2"])
def test_r73_url_info_line_and_v2_arm(monkeypatch, client, authed, caplog, v2):
    _prod_on(monkeypatch, FLAG)
    if v2:
        monkeypatch.setenv(URLV2, "true")
    _url(monkeypatch, url_noev())
    with caplog.at_level(logging.INFO):
        resp = _post_url(client)
    _text_refused(resp, "no_evidence")
    recs = [r for r in caplog.records if str(r.msg).startswith("[RESULT_GATE]")]
    assert [r.args for r in recs] == [("url", "no_evidence")]


# =============================================================== envelope + surface

def _handle(detail, status=400):
    class _St:
        request_id = "s20-request"

    class _Req:
        state = _St()

    resp = asyncio.run(eh.http_exception_handler(_Req(), HTTPException(status_code=status, detail=detail)))
    return json.loads(resp.body)


def test_r80_envelope_passthrough(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    out = _handle({"code": "INSUFFICIENT_DATA", "error": "x", "reason": "no_evidence"})
    assert out.get("reason") == "no_evidence", out
    assert "reason" not in _handle({"code": "INSUFFICIENT_DATA", "error": "x", "reason": "hacked"})
    assert "reason" not in _handle({"code": "TIMEOUT", "error": "x", "reason": "no_evidence"}, 503)
    monkeypatch.setenv(FRAG, "true")
    assert "reason" not in _handle({"code": "CATEGORY_NOT_LIVE", "error": "x",
                                    "reason": "no_evidence"})


@pytest.mark.parametrize("raw,want", TRUTHY_TABLE, ids=[repr(r[0]) for r in TRUTHY_TABLE])
def test_r81_reader_and_vocab_parity(monkeypatch, raw, want):
    if raw is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, raw)
    local = getattr(eh, "_result_gate_keys_enabled", None)
    assert callable(local), "error_handler._result_gate_keys_enabled absent (RED at base)"
    assert local() is want and _fn("result_gate_enabled")() is want
    assert getattr(eh, "_RESULT_GATE_REASONS", None) == _sym("GATE_REASONS")


def test_r82_surface_reason_on(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    with pytest.raises(HTTPException) as ei:
        text_routes._surface_comparison_failure({"success": False, "code": "INSUFFICIENT_DATA",
                                                 "error": "x", "reason": "no_evidence"})
    assert ei.value.detail == {"code": "INSUFFICIENT_DATA", "error": "x", "reason": "no_evidence"}
    with pytest.raises(HTTPException) as e2:
        text_routes._surface_comparison_failure({"success": False, "code": "INSUFFICIENT_DATA",
                                                 "error": "x", "reason": "hacked"})
    assert e2.value.detail == {"code": "INSUFFICIENT_DATA", "error": "x"}


def _build(product_categories):
    resp = body_sup()
    pd = copy.deepcopy(resp["products"])
    comparison = {"winner_index": 0, "winner_declaration": "x", "winner_reason": "y",
                  "verdict": "v", "pros": {}, "cons": {}}
    try:
        return rb.build_comparison_response(pd, comparison, "Tom Ford vs Creed", "bahrain",
                                            0.01, 3, 1.0, product_categories=product_categories)
    except TypeError:
        return None


def _builder_body(monkeypatch, product_categories):
    import inspect

    params = inspect.signature(rb.build_comparison_response).parameters
    kwargs = {}
    names = list(params)
    body = body_sup()
    product_data = copy.deepcopy(body["products"])
    for p in product_data:
        p.setdefault("full_name", (p.get("brand", "") + " " + p.get("name", "")).strip())
    comparison = {"winner_index": 0, "winner_declaration": "x", "winner_reason": "y",
                  "verdict": "v", "pros": {}, "cons": {}}
    values = {"product_data": product_data, "products": product_data, "comparison": comparison,
              "query": "Tom Ford vs Creed", "region": "bahrain", "total_cost": 0.01,
              "api_calls": 3, "elapsed": 1.0, "start_time": 0.0}
    for n in names:
        if n in values:
            kwargs[n] = values[n]
    kwargs["product_categories"] = product_categories
    return rb.build_comparison_response(**kwargs)


def test_r90_builder_stamp_b2_alone(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    out = _builder_body(monkeypatch, ["electronics", "fragrances"])
    md = out.get("metadata") or {}
    assert md.get("product_categories") == ["electronics", "fragrances"], md.get("product_categories")
    assert "result_status" not in md


# =============================================================== PIN rows (flag OFF, full config)

def _assert_off_delivered(resp, led, rec, uid, body, *, input_type="text"):
    assert resp.status_code == 200, resp.text[:300]
    got = resp.json()
    want = json.loads(json.dumps(body))
    want["comparison_id"] = "s20-row-id"
    assert got == want
    assert "reason" not in got
    assert led.refunds == [] and led.lifetime == [uid] and led.persist == [input_type]
    assert _gate_rows(led) == []
    assert rec.total() == 0, rec.calls


@pytest.mark.parametrize("truth", [False, True], ids=["w413_off", "w413_on"])
@pytest.mark.parametrize("flag_value", [None, "false", "0", "off", "", "garbage"])
def test_p01_off_text_post_v09_delivered(monkeypatch, client, authed, truth, flag_value):
    _full_config(monkeypatch, truth=truth)
    if flag_value is not None:
        monkeypatch.setenv(FLAG, flag_value)
    led = _ledger(monkeypatch, text_routes)
    rec = Rec(monkeypatch)
    _text_svc(monkeypatch, body_v09())
    _assert_off_delivered(_post(client), led, rec, authed["id"], body_v09())
    assert led.labels == ["log_search.text.post.success", "save_comparison.text.post",
                          "record_lifetime.text.post"], led.labels


def test_p02_off_text_get_v07_delivered(monkeypatch, client, authed):
    _full_config(monkeypatch)
    led = _ledger(monkeypatch, text_routes)
    rec = Rec(monkeypatch)
    _text_svc(monkeypatch, body_v07())
    _assert_off_delivered(_get(client), led, rec, authed["id"], body_v07())


@pytest.mark.parametrize("truth", [False, True], ids=["w413_off", "w413_on"])
def test_p03_off_stream_v09_billed_as_base(monkeypatch, client, authed, truth):
    _full_config(monkeypatch, truth=truth)
    led = _ledger(monkeypatch, text_routes)
    rec = Rec(monkeypatch)
    v09 = body_v09()
    _text_svc(monkeypatch, events=[("settle_complete", v09), ("complete", v09)])
    frames = _frames(_stream(client).text)
    want = json.loads(json.dumps(body_v09()))
    want["comparison_id"] = "s20-row-id"
    terms = [d for e, d in frames if e in ("settle_complete", "complete")]
    assert terms == [want, want], [list(t)[:5] for t in terms]
    assert led.refunds == [] and led.lifetime == [authed["id"]] and led.persist == ["text_stream"]
    assert _gate_rows(led) == [] and rec.total() == 0


def test_p04_off_camera_v07_and_enrich_as_base(monkeypatch, client, authed):
    _full_config(monkeypatch)
    for key, want_name in (("V07", "GUESS"), ("ENRICH", "Unknown Product 100ml")):
        led, cam = _camera(monkeypatch, VISION[key]())
        rec = Rec(monkeypatch)
        resp = _post_image(client)
        assert resp.status_code == 200 and resp.json().get("action") == "comparison", resp.text[:200]
        assert len(cam.calls) == 1, cam.calls
        assert cam.calls[0]["vision_products"][0]["name"] == want_name, cam.calls[0]
        assert rec.total() == 0 and _gate_rows(led) == [] and "reason" not in resp.json()


def test_p05_off_url_v09_delivered(monkeypatch, client, authed):
    _full_config(monkeypatch)
    led, calls = _url(monkeypatch, url_v09())
    rec = Rec(monkeypatch)
    resp = _post_url(client)
    assert resp.status_code == 200, resp.text[:200]
    assert resp.json() == json.loads(json.dumps(url_v09()))
    assert led.consumes == [authed["id"]] and led.history == ["url"]
    assert led.lifetime == [authed["id"]] and led.refunds == [] and rec.total() == 0


@pytest.mark.parametrize("on", [False, True], ids=["off", "on"])
def test_p06_h6_envelope_four_keys(monkeypatch, client, authed, on):
    _full_config(monkeypatch)
    if on:
        monkeypatch.setenv(FLAG, "true")
    _ledger(monkeypatch, text_routes)
    _text_svc(monkeypatch, {"success": False, "code": "INSUFFICIENT_DATA", "error": H6_MESSAGE,
                            "elapsed_seconds": 1.0, "total_cost": 0.0, "api_calls": 3})
    resp = _post(client)
    assert resp.status_code == 400 and set(resp.json()) == ENVELOPE_KEYS, resp.text[:200]


def test_p07_off_handler_drops_reason(monkeypatch):
    out = _handle({"code": "INSUFFICIENT_DATA", "error": "x", "reason": "no_evidence"})
    assert set(out) == ENVELOPE_KEYS, out


def test_p08_off_builder_no_categories(monkeypatch):
    out = _builder_body(monkeypatch, ["electronics", "fragrances"])
    assert "product_categories" not in (out.get("metadata") or {})


def test_p09_off_surface_detail_two_keys(monkeypatch):
    with pytest.raises(HTTPException) as ei:
        text_routes._surface_comparison_failure({"success": False, "code": "INSUFFICIENT_DATA",
                                                 "error": "x", "reason": "no_evidence"})
    assert ei.value.detail == {"code": "INSUFFICIENT_DATA", "error": "x"}


def test_p10_on_supported_text_delivered(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    led = _ledger(monkeypatch, text_routes)
    _text_svc(monkeypatch, body_sup())
    resp = _post(client)
    assert resp.status_code == 200 and resp.json() == json.loads(json.dumps(body_sup()))
    assert led.refunds == [] and led.history == ["text"] and led.lifetime == [authed["id"]]
    assert _gate_rows(led) == []


@pytest.mark.parametrize("which", ["bh", "ae", "v03"])
def test_p11_on_url_priced_pairs_delivered(monkeypatch, client, authed, which):
    _prod_on(monkeypatch, FLAG)
    env = url_v03() if which == "v03" else url_real(which)
    led, _c = _url(monkeypatch, env)
    resp = _post_url(client)
    assert resp.status_code == 200, resp.text[:200]
    assert led.history == ["url"] and led.lifetime == [authed["id"]]


def test_p12_on_stream_supported_delivered(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    led = _ledger(monkeypatch, text_routes)
    sup = body_sup()
    _text_svc(monkeypatch, events=[("settle_complete", sup), ("complete", sup)])
    frames = _frames(_stream(client).text)
    for e, d in frames:
        if e in ("settle_complete", "complete"):
            assert "reason" not in d and d.get("success") is True
    assert led.refunds == [] and led.lifetime == [authed["id"]]


@pytest.mark.parametrize("name", LANE1)
def test_p13_on_lane1_all_delivered(monkeypatch, client, authed, name):
    _prod_on(monkeypatch, FLAG)
    _ledger(monkeypatch, text_routes)
    _text_svc(monkeypatch, _lane1(name))
    assert _post(client).status_code == 200


def test_p14_on_camera_v1_low_compares(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    led, cam = _camera(monkeypatch, VISION["V1_LOW"]())
    resp = _post_image(client)
    assert resp.json().get("action") == "comparison" and len(cam.calls) == 1, resp.text[:200]


def test_p15_on_camera_sizes_compare(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    led, cam = _camera(monkeypatch, VISION["SIZES"]())
    resp = _post_image(client)
    assert resp.json().get("action") == "comparison" and len(cam.calls) == 1, resp.text[:200]


class _FakeReq:
    def __init__(self, disconnect_after=10 ** 6):
        self.calls = 0
        self.disconnect_after = disconnect_after
        self.headers = {}

    async def is_disconnected(self):
        self.calls += 1
        return self.calls > self.disconnect_after


def test_p16_on_stream_client_gone_before_refusal(monkeypatch):
    _prod_on(monkeypatch, FLAG, TRUTH)
    led = _ledger(monkeypatch, text_routes)
    v09 = body_v09()
    _text_svc(monkeypatch, events=[("status", {"progress": 10}), ("settle_complete", v09),
                                   ("complete", v09)])
    user = {"id": "s20-p16", "access_token": "s20-synthetic"}

    async def run():
        resp = await text_routes.text_compare_stream(
            request=_FakeReq(0), q=QUERY, product_a=None, product_b=None, region="bahrain",
            specs=True, reviews=True, pros_cons=True, nocache=True, selected_category=None,
            lang=None, user=user)
        async for _c in resp.body_iterator:
            pass

    asyncio.run(run())
    assert "usage_refund.text_stream.incomplete" in led.labels, led.labels
    assert led.history == [] and led.persist == [] and _gate_rows(led) == []
    assert [r.get("error_message") for r in led.rows] == ["client_gone_before_complete"], led.rows


def test_p17_on_camera_single_product_exit_unchanged(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG)
    led, cam = _camera(monkeypatch, [_v1("Unknown", "Unknown Product")])
    resp = _post_image(client)
    assert resp.json().get("action") == "need_second_product", resp.text[:200]
    assert led.refunds == [authed["id"]] and cam.calls == []


def test_p18_on_category_not_live_keeps_its_envelope(monkeypatch, client, authed):
    _prod_on(monkeypatch, FLAG, FRAG)
    led = _ledger(monkeypatch, text_routes)
    _text_svc(monkeypatch, cg.refusal_result("electronics"))
    resp = _post(client, FRAG_QUERY)
    assert resp.status_code == 400 and resp.json().get("code") == "CATEGORY_NOT_LIVE", resp.text[:200]
    assert "reason" not in resp.json()
    assert _gate_rows(led) == []


def test_p20_off_feedback_composite_untouched():
    """PIN: the history composite the ledger replaces is the module attribute both route
    modules call (so a refusal's `history == []` is observed, not assumed)."""
    assert callable(feedback_service.save_comparison_and_track_cohort)
    assert callable(text_routes.save_comparison_and_track_cohort)
