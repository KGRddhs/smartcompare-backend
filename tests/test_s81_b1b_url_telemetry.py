"""S81-G8 B1b URL-TELEMETRY (rides ENABLE_RESULT_STATUS_METADATA) -- RED and PIN rows.

Spec .qa-s80/S81-G8_UNIT_SPEC.md (unit B1b, section 5) as amended by RULINGS_S81_G8
(R-G8-2: price_showable_a/b stay STRICT on the URL input; R-G8-3: the compare_runs
build_run_row call gains the same conditional url_mode kwarg, row R7). Base daf86d32.

Every RED row fails at base on an AssertionError only: the new keyword is read through
inspect.signature and asserted BEFORE any call carrying it; every other RED row drives the
EXISTING capture_result_status / build_run_row. Every PIN row is green at base and runs with
B1 ON (or every OFF spelling) plus the capture_message recorder and, where a call must not
happen, a raising recorder on sentry_service.assess_result.

Hermetic: app.main imported FIRST (the dotenv guard); no network, no .env, no credential;
the JSON-LD readers are COPIED from tests/test_s81_s20_result_gate.py (_url_env, _up,
_jsonld_offer over the four real fixtures); synthetic identities StoreA Item A / StoreB
Item B. Pure ASCII, LF.
"""
from __future__ import annotations

import ast
import copy
import inspect
import json
import re
from pathlib import Path

import pytest
import sentry_sdk
from fastapi.testclient import TestClient

import app.main as app_main  # noqa: F401  FIRST: the dotenv guard (load_dotenv at import)
from app.main import app
from app.services import compare_runs
from app.services import result_gate as rg
from app.services import sentry_service
from tests import test_s80_b1 as b1

B1 = "ENABLE_RESULT_STATUS_METADATA"
GATE = "ENABLE_RESULT_GATE"
LEDGER = "ENABLE_COMPARE_RUN_LEDGER"
ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
RG_PATH = ROOT / "app" / "services" / "result_gate.py"
OFF_SPELLINGS = [None, "false", " 0 ", "OFF"]
OFF_IDS = ["unset", "false", "pad0", "OFF"]
CLEAR = tuple(sorted(set(b1.CLEAR + (B1, GATE, LEDGER, "ENABLE_URL_MODE_V2"))))
LANE1 = ("fashion", "grocery", "haircare", "iphone15_vs_galaxys24", "makeup", "now_vs_solgar",
         "other", "skincare", "tomford_vs_creed")


# ---------------------------------------------------------------- the URL readers (copied, S20 :195-266)

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


def url_ratings_only():
    return _url_env(_up("StoreA", "Item A", None, "4.5"), _up("StoreB", "Item B", None, "4"))


def url_real(name):
    if name == "bh":
        a = _jsonld_offer(FIX / "bh_gcc" / "curl_bh_bheshop.html")
        b = _jsonld_offer(FIX / "bh_gcc" / "curl_bh_godukkan.html")
    else:
        a = _jsonld_offer(FIX / "jsonld_first" / "ae_lulu_lowercase_jsonld_pricecurrency.html")
        b = _jsonld_offer(FIX / "jsonld_first" / "ae_samawa_ae_og_no_currency_jsonld_aed.html")
    return _url_env(_up("StoreA", "Item A", a[0], a[1]), _up("StoreB", "Item B", b[0], b[1]))


def _jsonld_offer(path):
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


# ---------------------------------------------------------------- harness

class _Rec:
    def __init__(self):
        self.calls = []

    def __call__(self, message, level=None, **kw):
        self.calls.append((message, level, dict(kw.get("tags") or {}), dict(kw.get("extras") or {})))


@pytest.fixture(autouse=True)
def rec(monkeypatch):
    for name in CLEAR:
        monkeypatch.delenv(name, raising=False)
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    recorder = _Rec()
    monkeypatch.setattr(sentry_sdk, "capture_message", recorder)
    saved = dict(app.dependency_overrides)
    try:
        yield recorder
    finally:
        limiter.enabled = prior
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _has_url_mode():
    params = inspect.signature(rg.assess_result).parameters
    return "url_mode" in params


def _need_url_mode():
    assert _has_url_mode(), "result_gate.assess_result has no url_mode keyword (B1b not implemented)"


def _url_assess(body):
    _need_url_mode()
    return rg.assess_result(body, product_categories=rg.stamped_product_categories(body), url_mode=True)


def _one(rec):
    assert len(rec.calls) == 1, rec.calls
    message, level, tags, _extras = rec.calls[0]
    assert message == "comparison_result_status" and level == "info"
    return tags


def _lane1_body(name):
    return b1._build_row(b1._lane1(name), product_categories=[None, None])


def _text_body_readings_differ():
    """The lane1 tomford_vs_creed body with each price.source_method removed and every
    rating derived: the strict reading loses price / ratings while a URL reading counts them."""
    body = copy.deepcopy(b1._lane1("tomford_vs_creed"))
    for prods in (body.get("products"), (body.get("overview") or {}).get("products")):
        for p in prods or []:
            if isinstance(p, dict):
                if isinstance(p.get("price"), dict):
                    p["price"].pop("source_method", None)
                p["rating_derived"] = True
    return body


# =============================================================== RED rows

def test_r1_assess_result_url_mode_keyword():
    params = inspect.signature(rg.assess_result).parameters
    assert "url_mode" in params, sorted(params)
    assert params["url_mode"].default is False
    assert params["url_mode"].kind is inspect.Parameter.KEYWORD_ONLY


def _jsonld_pair_tags(monkeypatch, rec, name):
    """R2 (bh) / R3 (ae): the JSON-LD string price pair through the EXISTING capture."""
    monkeypatch.setenv(B1, "true")
    sentry_service.capture_result_status(url_real(name), "url", compare_ms=1234)
    tags = _one(rec)
    got = {k: tags.get(k) for k in ("result_status", "reasons", "winner_emitted", "data_coverage",
                                     "data_coverage_literal", "identity_confidence", "price_showable_a",
                                     "price_showable_b", "input_type", "compare_ms")}
    assert got == {"result_status": "supported_result", "reasons": "none", "winner_emitted": "true",
                   "data_coverage": "1", "data_coverage_literal": "1", "identity_confidence": "high",
                   "price_showable_a": "false", "price_showable_b": "false", "input_type": "url",
                   "compare_ms": "0"}, got


def test_r2_bh_jsonld_pair_tags(monkeypatch, rec):
    _jsonld_pair_tags(monkeypatch, rec, "bh")


def test_r3_ae_jsonld_pair_tags(monkeypatch, rec):
    _jsonld_pair_tags(monkeypatch, rec, "ae")


def test_r4_string_ratings_only(monkeypatch, rec):
    monkeypatch.setenv(B1, "true")
    sentry_service.capture_result_status(url_ratings_only(), "url", compare_ms=10)
    tags = _one(rec)
    assert (tags.get("data_coverage"), tags.get("result_status")) == ("1", "supported_result"), tags


def test_r5_same_identity_keeps_needs_identification(monkeypatch, rec):
    monkeypatch.setenv(B1, "true")
    sentry_service.capture_result_status(url_same(), "url", compare_ms=10)
    tags = _one(rec)
    assert (tags.get("result_status"), tags.get("reasons")) == ("needs_identification", "same_identity"), tags


def test_r6_url_route_tags_follow_the_url_reading(monkeypatch, client, rec):
    monkeypatch.setenv(B1, "true")
    r = b1._url(monkeypatch, client)
    assert r.status_code == 200, r.text[:300]
    tags = _one(rec)
    assert tags.get("input_type") == "url"
    assert int(tags.get("data_coverage", "0")) >= 1, tags
    body = r.json()
    want = rg.telemetry_tags(body, "url", assessment=_url_assess(body), compare_ms=0)
    got = {k: v for k, v in tags.items() if k != "compare_ms"}
    assert got == {k: v for k, v in want.items() if k != "compare_ms"}, (got, want)


def test_r7_compare_runs_row_follows_the_url_reading():
    """R-G8-3: compare_runs.build_run_row (pure, the function exists at base) over the bh
    JSON-LD URL envelope with input_type url reads the URL evidence."""
    row = compare_runs.build_run_row(url_real("bh"), "url")
    assert isinstance(row, dict), row
    got = (row.get("result_status"), row.get("data_coverage"), row.get("winner_supported"))
    assert got == ("supported_result", 1, True), got
    text_row = compare_runs.build_run_row(url_real("bh"), "text")
    assert (text_row.get("result_status"), text_row.get("data_coverage")) == ("partial_no_winner", 0)


# =============================================================== PIN rows

def test_p1_flag_off_no_message_any_input(monkeypatch, rec):
    for value in OFF_SPELLINGS:
        _p1_one(monkeypatch, rec, value)


def _p1_one(monkeypatch, rec, value):
    if value is None:
        monkeypatch.delenv(B1, raising=False)
    else:
        monkeypatch.setenv(B1, value)
    fired = []

    def _boom(*a, **k):
        fired.append(1)
        raise AssertionError("B1 OFF: assess_result called")

    monkeypatch.setattr(sentry_service, "assess_result", _boom)
    monkeypatch.setattr(rg, "assess_result", _boom)
    bodies = [url_real("bh"), url_real("ae"), _lane1_body("tomford_vs_creed"), _lane1_body("grocery")]
    for body in bodies:
        for input_type in ("url", "text", "text_stream", "camera"):
            sentry_service.capture_result_status(copy.deepcopy(body), input_type, compare_ms=10)
    assert rec.calls == [] and fired == [], value


def test_p2_text_camera_stream_tags_byte_equal(monkeypatch, rec):
    monkeypatch.setenv(B1, "true")
    calls = []
    real = rg.assess_result

    def _spy(*a, **k):
        calls.append(sorted(k))
        return real(*a, **k)

    monkeypatch.setattr(sentry_service, "assess_result", _spy)
    body = _text_body_readings_differ()
    for input_type in ("text", "text_stream", "camera"):
        rec.calls.clear()
        sentry_service.capture_result_status(copy.deepcopy(body), input_type, compare_ms=100)
        tags = _one(rec)
        want = rg.telemetry_tags(body, input_type, assessment=real(
            body, product_categories=rg.stamped_product_categories(body)), compare_ms=100)
        assert json.dumps(tags, sort_keys=True) == json.dumps(want, sort_keys=True), (input_type, tags, want)
    assert calls == [["product_categories"]] * 3, calls
    # the readings DIFFER on this body (so a url_mode leak into a non-URL input is visible)
    assert real(body)["facts"]["price"] is False
    assert rg._url_price(body["products"][0]) and rg._url_price(body["products"][1])


BASE_ASSESS = {
    'lane1_fashion': ('supported_result', '', 3, 3, 'high'),
    'lane1_grocery': ('supported_result', '', 3, 3, 'high'),
    'lane1_haircare': ('supported_result', '', 3, 3, 'high'),
    'lane1_iphone15_vs_galaxys24': ('supported_result', '', 3, 3, 'high'),
    'lane1_makeup': ('supported_result', '', 3, 3, 'high'),
    'lane1_now_vs_solgar': ('supported_result', '', 3, 3, 'high'),
    'lane1_other': ('supported_result', '', 3, 3, 'high'),
    'lane1_skincare': ('supported_result', '', 3, 3, 'high'),
    'lane1_tomford_vs_creed': ('supported_result', '', 3, 3, 'high'),
    's20_cat': ('unsupported_category', 'category_conflict', 4, 4, 'low'),
    's20_v07': ('needs_identification', 'same_identity', 4, 4, 'low'),
    's20_v09': ('needs_identification', 'placeholder_identity,same_identity', 4, 4, 'unresolved'),
    's20_v10': ('partial_no_winner', 'no_evidence', 0, 1, 'medium'),
    's20_v10_one': ('partial_no_winner', 'no_evidence', 0, 1, 'high'),
    'url_ae': ('partial_no_winner', 'no_evidence', 0, 0, 'medium'),
    'url_bh': ('partial_no_winner', 'no_evidence', 0, 0, 'medium'),
    'url_noev': ('partial_no_winner', 'no_evidence', 0, 0, 'medium'),
    'url_same': ('needs_identification', 'same_identity,no_evidence', 0, 1, 'low'),
    'url_v03': ('partial_no_winner', 'no_evidence', 0, 1, 'medium'),
    'url_v09': ('needs_identification', 'placeholder_identity,same_identity,no_evidence', 0, 1, 'unresolved'),
}


def _p3_bodies():
    from tests import test_s81_s20_result_gate as s20
    out = {}
    for n in LANE1:
        out["lane1_" + n] = _lane1_body(n)
    for n in ("v09", "v07", "v10", "v10_one", "cat"):
        out["s20_" + n] = getattr(s20, "body_" + n)()
    out["url_bh"], out["url_ae"] = url_real("bh"), url_real("ae")
    for n, f in (("url_noev", url_noev), ("url_same", url_same), ("url_v09", url_v09), ("url_v03", url_v03)):
        out[n] = f()
    return out


def test_p3_assess_result_default_unchanged():
    got = {}
    for k, b in _p3_bodies().items():
        a = rg.assess_result(b, product_categories=rg.stamped_product_categories(b))
        got[k] = (a["status"], ",".join(a["reasons"]), a["data_coverage"], a["data_coverage_literal"],
                  a["identity_confidence"])
    assert got == BASE_ASSESS, {k: v for k, v in got.items() if BASE_ASSESS.get(k) != v}


def test_p4_url_gate_reading_unchanged(monkeypatch):
    monkeypatch.setenv(GATE, "true")
    cases = {"bh": (url_real("bh"), None), "ae": (url_real("ae"), None), "v03": (url_v03(), None),
             "noev": (url_noev(), "no_evidence"), "same": (url_same(), "same_identity"),
             "v09": (url_v09(), "placeholder_identity")}
    for name, (body, reason) in cases.items():
        assert rg.url_gate_reason(copy.deepcopy(body)) == reason, name
        refusal = rg.result_gate_refusal(copy.deepcopy(body), url_mode=True)
        assert (refusal is None) == (reason is None), (name, refusal)


def test_p5_url_body_never_stamped_and_strict_showable_tag(monkeypatch, client, rec):
    monkeypatch.setenv(B1, "true")
    r = b1._url(monkeypatch, client)
    assert r.status_code == 200, r.text[:300]
    assert "metadata" not in r.json()
    tags = _one(rec)
    assert (tags.get("price_showable_a"), tags.get("price_showable_b")) == ("false", "false"), tags


P11_ALLOWED = {"os", "re", "typing", "__future__", "app.services.text_sanitize"}
P11_BANNED = ("sentry_sdk", "structured_comparison_service", "response_builder", "price_service",
              "extraction_service", "httpx", "asyncio", "socket", "logging")


def test_p6_result_gate_purity_restated():
    raw = RG_PATH.read_bytes()
    assert all(b < 128 for b in raw)
    text = raw.decode("ascii")
    tree = ast.parse(text)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module)
        assert not isinstance(node, ast.AsyncFunctionDef)
    assert mods <= P11_ALLOWED, sorted(mods - P11_ALLOWED)
    assert [s for s in P11_BANNED if s in text] == []
