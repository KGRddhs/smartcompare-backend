"""B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- the RED file (session 80).

Spec: .qa-s80/B4_UNIT_SPEC.md of worktree sc-s80-b4 (sha256 fbb3cb8f...), its
adversarial review B4_SPEC_REVIEW.md (sha256 c454ad16...) and the orchestrator
rulings RULINGS_BATCH1.md section "B4 URL-MODE-V2" (B4-R1..R11) + "Common"
(G-1..G-4). Where they disagree the rulings win, then the review corrections,
then the spec. Base: 81df2b641454e0301cca51a3ba01bf8ef3d7e649.

What the unit does, behind ENABLE_URL_MODE_V2 (default OFF, read per call):
POST/GET /api/v1/url/compare refuse a storefront root / search / cart /
account / category link, and a pair equal after normalisation, BEFORE the
credit reserve (400 NOT_PRODUCT_PAGE + additive field/reason); after the fetch
every outcome carries a code (STORE_UNREADABLE, NOT_PRODUCT_PAGE post-fetch,
UNRESOLVED_PRODUCT, TIMEOUT through a 25 s wait_for); the extractor
normalises image_url to one https string; recommendation/key_differences are
filled from the verdict prose; the extraction LLM is asked for
is_product_page through URL_EXTRACTION_PROMPT_V2. Unflagged: the INFO lines
print the host only.

Node classes (each docstring opens with its class):
RED  fails at base 81df2b64 on an AssertionError ONLY (every symbol the unit
     adds is read with getattr / inspect.signature and asserted, never
     imported or called blind).
PIN  green at base and at head (flag-OFF identity, the codeless arm, the
     exception arm). Every flag-OFF PIN runs with the FULL configuration
     (metering ON, search-log truth ON, an authed user, the fetch transport,
     the LLM fake, the verdict fake) plus the ledger recorder (ruling B1), so a
     "not gated" mutant is killed.

Hermetic: no network (the httpx transport is a MockTransport installed on
url_extraction_service._TRANSPORT AND injected into every httpx.AsyncClient the
module builds; the SSRF validator is a recording fake), no .env reads beyond the
app's own import, no credential literal (ids built at run time).
"""
from __future__ import annotations

import app.main  # noqa: F401  -- FIRST: the dotenv hazard (s80-common.txt)

import asyncio
import copy
import hashlib
import inspect
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import url_routes
from app.api.auth_routes import get_optional_user
from app.main import app
from app.middleware import error_handler
from app.services import extraction_service, response_builder, text_sanitize
from app.services import structured_comparison_service as scs
from app.services import url_extraction_service as ues

FLAG = "ENABLE_URL_MODE_V2"
METER = "ENABLE_PAID_ROUTE_METERING"
TRUTH = "ENABLE_SEARCH_LOG_TRUTH"
PARSE = "ENABLE_PRICE_PARSE_OFFLOAD"
UNIT_ENV = (
    FLAG, METER, TRUTH, "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER", "SEARCH_LOG_SYNTHETIC_TOKEN",
    "ENABLE_COMPARE_AUTH_REQUIRED", "ENABLE_STRICT_OPTIONAL_AUTH",
    "ENABLE_OFFLOOP_DNS_RESOLVE", PARSE, "ENABLE_JSONLD_SHAPE_LADDER",
    "ENABLE_CAMERA_FAILURE_ENVELOPE", "ENABLE_LLM_PREFLIGHT_BREAKER",
    "ENABLE_SYNC_DB_OFFLOAD", "ENABLE_ANON_USAGE_GATE",
)
ON_VALUES = ["true", "TRUE", " true ", "1", "yes", "ON", "on"]
OFF_VALUES = [None, "", "false", "0", "no", "off", "garbage"]
VERBS = ["POST", "GET"]
RID = "b4-fixed-request-id"

# The unit's three copy constants (spec 2.1), pinned verbatim.
NPP_MSG = "That link opens a store page, not a product page. Paste the product's own page link."
SU_MSG = ("That store does not let us read its pages. Paste a link from another store, "
          "or type the product name.")
UP_MSG = "We did not find a product on that page. Paste the product's own page link."
FORBIDDEN_COPY = ("couldn't", "try again", "failed to")

BASE_PROMPT_SHA = "411169d46826f09e5e27c76e9d7905864a6e91681ab5bb7f5ee609f176b508a9"
BASE_FETCH_PAGE_SHA = "34dd74c618058409719313c2a859de0a69281c15c9c86d4faa3b41b42f7b8655"
# The flag-OFF extract_with_ai user message for the W4-11 recorder's inputs,
# measured at base 81df2b64 (the fixture key holds the PRE-fence render).
BASE_URL_EXTRACT_USER_SHA = "65edcacae42a8287a66e784f3d963eb41fba80b0219caae25fe10bef2c853a66"

FX_HOME = "https://www.fragrancex.com/"
FX_PDP = "https://www.fragrancex.com/products/christian-dior/sauvage-cologne"
FX_PDP2 = "https://www.fragrancex.com/products/calvin-klein/obsession-perfume"
RS_HOME = "https://store.rasasi.com.sa/"
RS_PAGE = "https://store.rasasi.com.sa/en/pages/about-us"
RS_PAGE2 = "https://store.rasasi.com.sa/en/pages/contact"
METADATA_URL = "http://169.254.169.254/latest/meta-data/"

_FIX = Path(__file__).resolve().parent / "fixtures"
STOREFRONT = (_FIX / "not_a_pdp" / "kw_abdulsamadalqurashi_com_homepage_collapse.html").read_bytes()
PDP = (_FIX / "spec_spine_d2" / "us_fragrancex_com_dior_sauvage_cologne.html").read_bytes()
STOREFRONT_TITLE = "Abdul Samad AlQurashi Online Store - KW"
PDP_IMAGE = "https://img.fragrancex.com/images/products/sku/large/saucm278d.jpg"

BASE_FEW = {"success": False, "error": "Could not extract both products", "code": "BAD_REQUEST"}
BASE_SSRF = {"success": False, "error": "URL blocked by security policy", "code": "BAD_REQUEST"}

VERDICT_OK = {
    "winner_index": 1, "winner_declaration": "B",
    "winner_reason": "B lasts longer on skin through the day.",
    "key_tradeoff": "A opens brighter.",
    "specs_comparison": {"product_0_advantages": ["brighter opening"],
                         "product_1_advantages": ["longer wear", "larger bottle"],
                         "similar": ["EDP"]},
}
VERDICT_LEAK = dict(copy.deepcopy(VERDICT_OK), winner_reason="B scores 84/100 overall.")
DELIVERY_KEYS = {"success", "products", "comparison", "winner_index", "recommendation",
                 "key_differences", "category_used", "source_urls"}

_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _page(title, jsonld=None, og=None, body=""):
    head = "" if title is None else f"<title>{title}</title>"
    for key, value in (og or {}).items():
        head += f'<meta property="og:{key}" content="{value}">'
    for block in (jsonld or []):
        head += '<script type="application/ld+json">' + json.dumps(block) + "</script>"
    return f"<html><head>{head}</head><body>{body}</body></html>"


def _product(name="Obsession Perfume", image=None, price="24.99", **extra):
    node = {"@context": "https://schema.org", "@type": "Product"}
    if name is not None:
        node["name"] = name
    if image is not None:
        node["image"] = image
    if price is not None:
        node["offers"] = {"@type": "Offer", "price": price, "priceCurrency": "USD"}
    node.update(extra)
    return node


PDP2 = _page("Calvin Klein Obsession Perfume - FragranceX",
             [_product(brand={"@type": "Brand", "name": "Calvin Klein"},
                       image="https://img.fragrancex.com/images/products/sku/large/obs.jpg")])
CHALLENGE = _page("Just a moment...", body="Checking your browser before accessing the site.")
FORBIDDEN = "<html><body>Forbidden</body></html>"


# ---------------------------------------------------------------------------
# helpers: missing symbols are ASSERTED (AssertionError), never raised blind
# ---------------------------------------------------------------------------
def _fn(module, name):
    value = getattr(module, name, None)
    assert callable(value), f"B4: {module.__name__}.{name} is missing or not callable"
    return value


def _const(module, name):
    value = getattr(module, name, None)
    assert value is not None, f"B4: {module.__name__}.{name} is missing"
    return value


def _assert_kwarg(fn, name):
    params = inspect.signature(fn).parameters
    assert name in params, f"B4: {fn.__qualname__} has no {name!r} parameter: {list(params)}"


def _strip_rid(body):
    if isinstance(body, dict):
        return {k: v for k, v in body.items() if k != "request_id"}
    return body


def _done(value=None):
    async def _r():
        return value
    return _r()


def _set_flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


def _messages(caplog, logger_name, level=None):
    out = []
    for rec in caplog.records:
        if rec.name != logger_name:
            continue
        if level is not None and rec.levelno != level:
            continue
        out.append(rec.getMessage())
    return out


# ---------------------------------------------------------------------------
# the harness
# ---------------------------------------------------------------------------
class Pages:
    """Serves pages by exact request url (str(request.url)); records every url.
    A value is (status, headers, body) or an httpx exception class."""

    def __init__(self, pages=None, default=None):
        self.pages = dict(pages or {})
        self.default = default
        self.fetched: list = []

    def handler(self, request):
        url = str(request.url)
        self.fetched.append(url)
        spec = self.pages.get(url, self.default)
        if spec is None:
            return httpx.Response(404, text="<html>not found</html>")
        if isinstance(spec, type) and issubclass(spec, Exception):
            raise spec("b4 probe", request=request)
        status, headers, body = spec
        content = body if isinstance(body, bytes) else body.encode("utf-8")
        return httpx.Response(status, headers=headers or {}, content=content)


def ok(body):
    return (200, {"content-type": "text/html; charset=utf-8"}, body)


def status(code, body=FORBIDDEN, headers=None):
    return (code, dict({"content-type": "text/html"}, **(headers or {})), body)


def redirect(location, code=302):
    return (code, {"location": location}, b"")


class Ledger:
    def __init__(self):
        self.consumes: list = []
        self.refunds: list = []
        self.lifetime: list = []
        self.history: list = []
        self.rows: list = []
        self.labels: list = []

    def consume(self, user_id, access_token="", *_a, **_kw):
        self.consumes.append(user_id)
        return _done({"allowed": True, "reason": None, "tier": "free", "consumed": True,
                      "consumed_keys": {"daily": "d", "monthly": "m"},
                      "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2}})

    def refund(self, user_id, *_a, **_kw):
        self.refunds.append(user_id)
        return _done()

    def record_lifetime(self, user_id, *_a, **_kw):
        self.lifetime.append(user_id)
        return _done()

    def save(self, *_a, **kw):
        self.history.append(kw.get("input_type"))
        return _done()

    def log_search(self, *a, **kw):
        assert not a, f"log_search must be keyword-only, got {a!r}"
        self.rows.append(dict(kw))
        return _done()

    def ff(self, coro, label=None):
        self.labels.append(label)
        try:
            coro.close()
        except Exception:  # noqa: BLE001
            pass


class _FC:
    def __init__(self, store, content):
        self.store, self.content = store, content

    async def create(self, **kw):
        self.store.append(kw)
        msg = type("M", (), {"content": self.content})()
        choice = type("C", (), {"message": msg})()
        return type("R", (), {"choices": [choice], "usage": None})()


def _fake_client(store, content="{}"):
    completions = _FC(store, content)
    chat = type("Chat", (), {"completions": completions})()
    ns = type("Client", (), {})()
    ns.chat = chat
    ns.with_options = lambda **kw: ns
    return ns


class H:
    """Per-test state: the page server, the ledger, the events, the LLM calls."""

    def __init__(self):
        self.pages = Pages()
        self.ledger = Ledger()
        self.events: list = []
        self.ssrf_calls: list = []
        self.llm_calls: list = []
        self.gen_calls: list = []
        self.cfu_calls: list = []
        self.pregate_raised: list = []
        self.user = None


@pytest.fixture(autouse=True)
def _unit_env(monkeypatch):
    for name in UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    for key in list(os.environ):
        if key.startswith("OPENAI_MODEL_"):
            monkeypatch.delenv(key, raising=False)
    from app.middleware.rate_limiter import limiter
    prior = limiter.enabled
    limiter.enabled = False
    saved = dict(app.dependency_overrides)
    try:
        yield
    finally:
        limiter.enabled = prior
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _serve(monkeypatch, h, pages=None, default=None):
    h.pages = Pages(pages, default)
    transport = httpx.MockTransport(h.pages.handler)

    def factory(*a, **kw):
        if kw.get("transport") is None:
            kw["transport"] = transport
        return _REAL_ASYNC_CLIENT(*a, **kw)

    monkeypatch.setattr(ues.httpx, "AsyncClient", factory)
    monkeypatch.setattr(ues, "_TRANSPORT", transport, raising=False)
    return transport


def _ssrf(monkeypatch, h, deny=(), deny_all=False):
    def validate(url):
        h.ssrf_calls.append(url)
        h.events.append("ssrf")
        if deny_all:
            return False
        return not any(d in str(url) for d in deny)
    monkeypatch.setattr("app.utils.url_validator.validate_external_url", validate)


def _llm(monkeypatch, h, content="{}", boom=False):
    if boom:
        def _boom(*_a, **_k):
            h.llm_calls.append("boom")
            raise RuntimeError("b4 offline")
        monkeypatch.setattr(ues, "get_client", _boom)
    else:
        monkeypatch.setattr(ues, "get_client", lambda *a, **k: _fake_client(h.llm_calls, content))


def _verdict(monkeypatch, h, verdict=None):
    async def gen(*a, **kw):
        h.gen_calls.append((a, kw))
        return copy.deepcopy(verdict if verdict is not None else VERDICT_OK), {
            "prompt_tokens": 0, "completion_tokens": 0}
    monkeypatch.setattr(extraction_service, "generate_comparison", gen)

    async def resolve(products, selected_category, parser_path=False):
        return "fragrances", False, None
    monkeypatch.setattr(scs, "_resolve_pair_category", resolve)


def _spy_pregate(monkeypatch, h):
    real = getattr(url_routes, "_url_pre_gate", None)

    def spy(*a, **kw):
        h.events.append("pregate")
        return real(*a, **kw) if callable(real) else None
    monkeypatch.setattr(url_routes, "_url_pre_gate", spy, raising=False)


def _raising_pregate(monkeypatch, h):
    def stand_in(*a, **kw):
        h.pregate_raised.append(a)
        raise AssertionError("B4: the flag-OFF path ran the pre-gate")
    monkeypatch.setattr(url_routes, "_url_pre_gate", stand_in, raising=False)


def _record_cfu(monkeypatch, h):
    real = url_routes.compare_from_urls

    async def rec(*a, **kw):
        h.cfu_calls.append((a, dict(kw)))
        return await real(*a, **kw)
    monkeypatch.setattr(url_routes, "compare_from_urls", rec)


def _full(monkeypatch, h, *, flag="true", meter=True, truth=True, authed=True,
          pages=None, default=None, llm_content="{}", llm_boom=False, verdict=None,
          deny=(), spy=True):
    """The FULL configuration (ruling B1): metering + truth ON, an authed user,
    the transport, the LLM fake, the verdict fake, the ledger, the SSRF fake."""
    _set_flag(monkeypatch, flag)
    if meter:
        monkeypatch.setenv(METER, "true")
    if truth:
        monkeypatch.setenv(TRUTH, "true")
    h.user = {"id": str(uuid.uuid4()), "access_token": "t-" + uuid.uuid4().hex} if authed else None
    user = h.user
    app.dependency_overrides[get_optional_user] = lambda: user
    _serve(monkeypatch, h, pages, default)
    _ssrf(monkeypatch, h, deny=deny)
    _llm(monkeypatch, h, content=llm_content, boom=llm_boom)
    _verdict(monkeypatch, h, verdict)
    led = h.ledger
    monkeypatch.setattr(url_routes, "consume_comparison_credit", led.consume)
    monkeypatch.setattr(url_routes, "refund_comparison_credit", led.refund)
    monkeypatch.setattr(url_routes, "record_lifetime_comparison", led.record_lifetime)
    monkeypatch.setattr(url_routes, "save_comparison_and_track_cohort", led.save)
    monkeypatch.setattr(url_routes, "log_search", led.log_search)
    monkeypatch.setattr(url_routes, "fire_and_forget", led.ff)
    if spy:
        _spy_pregate(monkeypatch, h)
    return h


def _call(client, verb, url1, url2):
    headers = {"X-Request-ID": RID}
    if verb == "GET":
        return client.get("/api/v1/url/compare", params={"url1": url1, "url2": url2},
                          headers=headers)
    return client.post("/api/v1/url/compare", json={"url1": url1, "url2": url2},
                       headers=headers)


def _refusal(code, msg, field, reason):
    return {"success": False, "error": msg, "code": code, "field": field, "reason": reason}


def _assert_non_delivery(h, *, refunded=True):
    led = h.ledger
    uid = h.user["id"]
    assert led.consumes == [uid], led.consumes
    assert led.refunds == ([uid] if refunded else []), led.refunds
    assert led.lifetime == [], led.lifetime
    assert led.history == [], led.history
    assert "save_comparison.url" not in led.labels, led.labels
    assert "record_lifetime.url" not in led.labels, led.labels


def _failure_row(h, message):
    rows = [r for r in h.ledger.rows if r.get("success") is False]
    assert len(rows) == 1, h.ledger.rows
    row = rows[0]
    assert row.get("input_type") == "url", row
    assert row.get("error_message") == message, row
    assert "log_search.url.failure" in h.ledger.labels, h.ledger.labels
    return row


def _run(coro):
    return asyncio.run(coro)


# ===========================================================================
# copy constants, seams, readers
# ===========================================================================
def test_copy_constants_verbatim_and_policy_clean():
    """RED: the three copy constants exist with the spec 2.1 text and carry none
    of the forbidden scary words."""
    for name, want in (("NOT_PRODUCT_PAGE_MESSAGE", NPP_MSG),
                       ("STORE_UNREADABLE_MESSAGE", SU_MSG),
                       ("UNRESOLVED_PRODUCT_MESSAGE", UP_MSG)):
        assert _const(ues, name) == want, name
        assert not any(w in want.lower() for w in FORBIDDEN_COPY), want


def test_test_seams_have_production_values():
    """RED: url_extraction_service._TRANSPORT is None (the default transport)
    and url_routes._URL_COMPARE_DEADLINE_SECONDS is the module constant 25.0."""
    assert hasattr(ues, "_TRANSPORT"), "B4: url_extraction_service._TRANSPORT missing"
    assert ues._TRANSPORT is None
    assert _const(url_routes, "_URL_COMPARE_DEADLINE_SECONDS") == 25.0


@pytest.mark.parametrize("value", ON_VALUES + OFF_VALUES)
def test_service_flag_reader_table(monkeypatch, value):
    """RED: url_mode_v2_enabled() is the house idiom (.strip().lower() in the set)."""
    reader = _fn(ues, "url_mode_v2_enabled")
    _set_flag(monkeypatch, value)
    assert reader() is (value in ON_VALUES), (value, reader())


@pytest.mark.parametrize("value", ON_VALUES + OFF_VALUES)
def test_error_handler_reader_table(monkeypatch, value):
    """RED (R33): the middleware's local one-liner reads the SAME name."""
    reader = _fn(error_handler, "_url_mode_v2_keys_enabled")
    _set_flag(monkeypatch, value)
    assert reader() is (value in ON_VALUES), (value, reader())


# ===========================================================================
# R1-R3, P4, P5, P6, R7, R37: the pre-gate
# ===========================================================================
@pytest.mark.parametrize("variant", [
    FX_HOME, "https://www.fragrancex.com", FX_HOME + "?gclid=abc123",
    FX_HOME + "?gbraid=xyz&gad_source=1", "https://www.fragrancex.com/en/",
    "https://www.fragrancex.com/index.html"])
@pytest.mark.parametrize("verb", VERBS)
def test_pregate_homepage_pair_refused_before_reserve(monkeypatch, client, caplog, verb, variant):
    """RED (R1): a storefront-root pair is refused for $0 BEFORE the reserve,
    after the SSRF checks, with field both / reason homepage. Base: the
    storefront is fetched and delivered as two store-named products (200)."""
    h = _full(monkeypatch, H(), default=ok(STOREFRONT))
    caplog.set_level(logging.INFO)
    r = _call(client, verb, variant, variant)
    assert r.status_code == 400, (r.status_code, r.json())
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "both", "homepage")
    led = h.ledger
    assert (led.consumes, led.refunds, led.lifetime, led.history, led.rows) == ([], [], [], [], [])
    assert h.pages.fetched == []
    assert h.events == ["ssrf", "ssrf", "pregate"], h.events
    lines = _messages(caplog, "app.api.url_routes", logging.INFO)
    assert lines.count("[URL-V2] refused code=NOT_PRODUCT_PAGE field=both reason=homepage") == 1, lines


@pytest.mark.parametrize("pair,field,reason", [
    ((FX_PDP, FX_HOME), "url2", "homepage"),
    (("https://www.fragrancex.com/search?q=sauvage", FX_PDP), "url1", "search"),
    (("https://www.fragrancex.com/cart", FX_PDP), "url1", "cart"),
    (("https://www.fragrancex.com/en-bh/checkout", FX_PDP), "url1", "cart"),
    (("https://www.fragrancex.com/account/login", FX_PDP), "url1", "account"),
    (("https://www.fragrancex.com/collections/men", FX_PDP), "url1", "category"),
    ((FX_HOME, "https://www.fragrancex.com/search"), "both", "homepage"),
], ids=["url2-home", "url1-search", "url1-cart", "url1-checkout", "url1-account",
        "url1-category", "both-home-search"])
@pytest.mark.parametrize("verb", VERBS)
def test_pregate_field_and_reason(monkeypatch, client, verb, pair, field, reason):
    """RED (R2): field names the refused url(s); url1's reason wins when both
    fail. Base: never refuses (both urls served a PDP and delivered)."""
    h = _full(monkeypatch, H(), default=ok(PDP))
    r = _call(client, verb, *pair)
    assert r.status_code == 400, (r.status_code, r.json())
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, field, reason)
    assert h.ledger.consumes == [] and h.pages.fetched == [], (h.ledger.consumes, h.pages.fetched)


@pytest.mark.parametrize("other", [
    FX_PDP, FX_PDP + "/", "HTTPS://WWW.FragranceX.com/products/christian-dior/sauvage-cologne",
    "https://fragrancex.com/products/christian-dior/sauvage-cologne", FX_PDP + "?utm=1#top"],
    ids=["identical", "slash", "case-host", "no-www", "query-fragment"])
@pytest.mark.parametrize("verb", VERBS)
def test_pregate_same_url_after_normalisation(monkeypatch, client, verb, other):
    """RED (R3): a pair equal after normalisation is refused with field both /
    reason same_url, nothing reserved or fetched. Base: fetches both, delivers."""
    h = _full(monkeypatch, H(), default=ok(PDP))
    r = _call(client, verb, FX_PDP, other)
    assert r.status_code == 400, (r.status_code, r.json())
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "both", "same_url")
    assert h.ledger.consumes == [] and h.pages.fetched == []


@pytest.mark.parametrize("verb", VERBS)
def test_pregate_lets_distinct_pdps_through(monkeypatch, client, verb):
    """PIN (P4): two distinct PDPs pass the gate (flag ON, full config)."""
    h = _full(monkeypatch, H(), pages={FX_PDP: ok(PDP), FX_PDP2: ok(PDP2)})
    r = _call(client, verb, FX_PDP, FX_PDP2)
    assert r.status_code == 200, r.json()
    assert r.json().get("success") is True
    assert sorted(h.pages.fetched) == sorted([FX_PDP, FX_PDP2]), h.pages.fetched
    assert h.ledger.consumes == [h.user["id"]] and h.ledger.refunds == []


@pytest.mark.parametrize("flag", [None, "true"], ids=["off", "on"])
@pytest.mark.parametrize("verb", VERBS)
def test_ssrf_refusal_byte_identical_in_both_states(monkeypatch, client, verb, flag):
    """PIN (P5, review C10): the HOMEPAGE pair with the validator refusing url1:
    the SSRF 400 first in both states, the pre-gate never runs (kills M3)."""
    h = _full(monkeypatch, H(), flag=flag, default=ok(STOREFRONT))
    _ssrf(monkeypatch, h, deny_all=True)
    r = _call(client, verb, FX_HOME, FX_HOME)
    assert r.status_code == 400
    assert _strip_rid(r.json()) == BASE_SSRF
    assert h.events == ["ssrf"], h.events
    assert h.ledger.consumes == [] and h.ledger.rows == [] and h.pages.fetched == []


@pytest.mark.parametrize("value", OFF_VALUES)
@pytest.mark.parametrize("verb", VERBS)
def test_flag_off_homepage_pair_is_base_behaviour(monkeypatch, client, verb, value):
    """PIN (P6): flag OFF (every OFF spelling) with the FULL configuration and a
    RAISING pre-gate stand-in: the base storefront delivery (the V09 shape), the
    base positional compare_from_urls call, the base billing."""
    h = _full(monkeypatch, H(), flag=value, default=ok(STOREFRONT), llm_boom=True, spy=False)
    _raising_pregate(monkeypatch, h)
    _record_cfu(monkeypatch, h)
    r = _call(client, verb, RS_HOME, RS_HOME)
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body.get("success") is True
    assert body["products"][0]["name"] == STOREFRONT_TITLE
    assert body["recommendation"] == "" and body["key_differences"] == []
    assert h.pages.fetched == [RS_HOME, RS_HOME], h.pages.fetched
    uid = h.user["id"]
    assert h.ledger.consumes == [uid] and h.ledger.refunds == []
    assert h.ledger.lifetime == [uid] and h.ledger.history == ["url"]
    assert h.pregate_raised == []
    assert len(h.cfu_calls) == 1
    args, kwargs = h.cfu_calls[0]
    assert kwargs == {} and len(args) == 4, h.cfu_calls


@pytest.mark.parametrize("value", ON_VALUES)
@pytest.mark.parametrize("verb", VERBS)
def test_flag_reader_table_on(monkeypatch, client, verb, value):
    """RED (R7): every ON spelling enables the pre-gate (the R1 pair)."""
    _full(monkeypatch, H(), flag=value, default=ok(STOREFRONT))
    r = _call(client, verb, FX_HOME, FX_HOME)
    assert r.status_code == 400, r.json()
    assert r.json().get("code") == "NOT_PRODUCT_PAGE"


@pytest.mark.parametrize("verb", VERBS)
def test_pregate_writes_no_search_log_row(monkeypatch, client, verb):
    """RED (R37): a pre-gate refusal is the SSRF-400 class: no row, no label.
    Base: a success row for the storefront delivery."""
    h = _full(monkeypatch, H(), default=ok(STOREFRONT))
    r = _call(client, verb, FX_HOME, FX_HOME)
    assert r.status_code == 400
    assert h.ledger.rows == [] and h.ledger.labels == [], (h.ledger.rows, h.ledger.labels)


# ===========================================================================
# R8-R14: post-fetch coded outcomes through the route
# ===========================================================================
@pytest.mark.parametrize("verb", VERBS)
def test_v09_storefront_pages_unresolved(monkeypatch, client, verb):
    """RED (R8, V09): two non-root storefront pages (no Product node, the title
    equals the Organization name) are UNRESOLVED_PRODUCT / no_product_node, with
    NO LLM call, refunded once, one failure row. Base: 200 with two store-named
    products, billed."""
    h = _full(monkeypatch, H(), pages={RS_PAGE: ok(STOREFRONT), RS_PAGE2: ok(STOREFRONT)})
    r = _call(client, verb, RS_PAGE, RS_PAGE2)
    assert r.status_code == 400, (r.status_code, r.json())
    assert _strip_rid(r.json()) == _refusal("UNRESOLVED_PRODUCT", UP_MSG, "both", "no_product_node")
    assert h.llm_calls == [], h.llm_calls
    assert h.gen_calls == []
    _assert_non_delivery(h)
    assert "usage_refund.url.compare.failure" in h.ledger.labels
    row = _failure_row(h, UP_MSG)
    assert row.get("query") == f"{RS_PAGE} vs {RS_PAGE2}", row


@pytest.mark.parametrize("verb", VERBS)
def test_v02_fragrancex_403_is_store_unreadable(monkeypatch, client, caplog, verb):
    """RED (R9, V02): a 403 is STORE_UNREADABLE http_403 on url1, refunded once.
    Base: the codeless 'Could not extract both products' 400."""
    h = _full(monkeypatch, H(), pages={FX_PDP2: status(403), FX_PDP: ok(PDP)})
    caplog.set_level(logging.INFO)
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 400, r.json()
    assert _strip_rid(r.json()) == _refusal("STORE_UNREADABLE", SU_MSG, "url1", "http_403")
    _assert_non_delivery(h)
    _failure_row(h, SU_MSG)
    lines = _messages(caplog, "app.services.url_extraction_service", logging.INFO)
    assert "[URL-V2] outcome=http_error reason=http_403 status=403" in lines, lines


@pytest.mark.parametrize("verb", VERBS)
def test_both_urls_403_field_both(monkeypatch, client, verb):
    """RED (R10): both urls 403 -> field both, reason http_403."""
    _full(monkeypatch, H(), pages={FX_PDP2: status(403), FX_PDP: status(403)})
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 400
    assert _strip_rid(r.json()) == _refusal("STORE_UNREADABLE", SU_MSG, "both", "http_403")


@pytest.mark.parametrize("verb", VERBS)
def test_challenge_page_is_store_unreadable(monkeypatch, client, verb):
    """RED (R11): a 2xx title-anchored challenge page is STORE_UNREADABLE /
    challenge. Base: the title is 'usable' -> delivery or BAD_REQUEST."""
    _full(monkeypatch, H(), pages={FX_PDP2: ok(CHALLENGE), FX_PDP: ok(PDP)})
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 400, r.json()
    assert _strip_rid(r.json()) == _refusal("STORE_UNREADABLE", SU_MSG, "url1", "challenge")


@pytest.mark.parametrize("verb", VERBS)
def test_body_text_access_denied_is_not_a_challenge(monkeypatch, client, verb):
    """PIN (R11b, kills M15): 'Access denied' in the BODY of a real PDP (title
    not a challenge title) still delivers, in both states."""
    page = _page("Calvin Klein Obsession Perfume - FragranceX",
                 [_product(brand="Calvin Klein")],
                 body="<p>Access denied for the reviews widget. Just a moment...</p>")
    _full(monkeypatch, H(), pages={FX_PDP2: ok(page), FX_PDP: ok(PDP)})
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 200, r.json()
    assert r.json().get("success") is True


@pytest.mark.parametrize("verb", VERBS)
def test_transport_error_is_store_unreadable(monkeypatch, client, caplog, verb):
    """RED (R12): a transport exception is STORE_UNREADABLE / fetch_error with
    ONE ERROR line carrying the host and the exception type only (inside the
    except arm). The exact template is deliberately not pinned here: the spec's
    reuse of the base 'Failed to fetch URL host %s: %s' text collides with
    tests/test_sentry_channels_u8d_unit.py R8 (exactly ONE ERROR call with that
    prefix in url_extraction_service.py), an open question for the gate."""
    _full(monkeypatch, H(), pages={FX_PDP2: httpx.ConnectTimeout, FX_PDP: ok(PDP)})
    caplog.set_level(logging.INFO)
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 400, r.json()
    assert _strip_rid(r.json()) == _refusal("STORE_UNREADABLE", SU_MSG, "url1", "fetch_error")
    errors = [m for m in _messages(caplog, "app.services.url_extraction_service", logging.ERROR)
              if "ConnectTimeout" in m]
    assert len(errors) == 1, errors
    assert "www.fragrancex.com" in errors[0] and "/products/" not in errors[0], errors


@pytest.mark.parametrize("verb", VERBS)
def test_redirect_to_homepage_is_not_product_page_post_fetch(monkeypatch, client, verb):
    """RED (R13): a redirect ending on the storefront root is NOT_PRODUCT_PAGE
    (post-fetch, field url1, reason homepage). Base: followed, final url
    discarded, delivered."""
    h = _full(monkeypatch, H(), pages={FX_PDP2: redirect(FX_HOME), FX_HOME: ok(STOREFRONT),
                                       FX_PDP: ok(PDP)})
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 400, r.json()
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "url1", "homepage")
    assert sorted(h.pages.fetched) == sorted([FX_PDP2, FX_HOME, FX_PDP]), h.pages.fetched
    _assert_non_delivery(h)
    _failure_row(h, NPP_MSG)


@pytest.mark.parametrize("verb", VERBS)
def test_mixed_codes_precedence(monkeypatch, client, verb):
    """RED (R14): url1 unresolved + url2 403 -> STORE_UNREADABLE wins, field
    both, reason http_403 (the reason of the url carrying the chosen code)."""
    _full(monkeypatch, H(), pages={RS_PAGE: ok(STOREFRONT), FX_PDP2: status(403)})
    r = _call(client, verb, RS_PAGE, FX_PDP2)
    assert r.status_code == 400
    assert _strip_rid(r.json()) == _refusal("STORE_UNREADABLE", SU_MSG, "both", "http_403")


@pytest.mark.parametrize("verb", VERBS)
def test_mixed_codes_precedence_not_product_page_over_unresolved(monkeypatch, client, verb):
    """RED (R14b): url1 redirected to a storefront root (NOT_PRODUCT_PAGE) +
    url2 unresolved -> NOT_PRODUCT_PAGE, field both, reason homepage."""
    _full(monkeypatch, H(), pages={FX_PDP2: redirect(FX_HOME), FX_HOME: ok(STOREFRONT),
                                   RS_PAGE: ok(STOREFRONT)})
    r = _call(client, verb, FX_PDP2, RS_PAGE)
    assert r.status_code == 400
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "both", "homepage")


@pytest.mark.parametrize("case,reason", [("blocked_hop", "blocked"), ("redirect_cap", "redirect_cap")])
@pytest.mark.parametrize("verb", VERBS)
def test_route_fetch_blocked_or_capped_is_store_unreadable(monkeypatch, client, verb, case, reason):
    """RED (B4-R3 route rows): an SSRF-blocked hop / a redirect cap inside the
    v2 fetch is a 400 STORE_UNREADABLE (reason blocked / redirect_cap), refunded
    once; the internal target is never requested."""
    if case == "blocked_hop":
        pages = {FX_PDP2: redirect(METADATA_URL), FX_PDP: ok(PDP)}
    else:
        pages = {FX_PDP: ok(PDP), FX_PDP2: redirect("https://www.fragrancex.com/loop/0")}
        for i in range(12):
            pages[f"https://www.fragrancex.com/loop/{i}"] = redirect(
                f"https://www.fragrancex.com/loop/{i + 1}")
    h = _full(monkeypatch, H(), pages=pages, deny=("169.254",))
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 400, r.json()
    assert _strip_rid(r.json()) == _refusal("STORE_UNREADABLE", SU_MSG, "url1", reason)
    assert METADATA_URL not in h.pages.fetched
    _assert_non_delivery(h)


# ===========================================================================
# P15, R16, P17, P18: the codeless arm, the deadline, the exception arm
# ===========================================================================
@pytest.mark.parametrize("verb", VERBS)
def test_codeless_failure_keeps_base_body_flag_on(monkeypatch, client, verb):
    """PIN (P15): an exception inside extract_from_url for url1 (flag ON) keeps
    the base codeless 400 and the verbatim row."""
    h = _full(monkeypatch, H(), pages={FX_PDP: ok(PDP)})
    real = ues.extract_from_url

    async def ext(url, *a, **kw):
        if url == FX_PDP2:
            raise RuntimeError("b4 probe")
        return await real(url, *a, **kw)
    monkeypatch.setattr(ues, "extract_from_url", ext)
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 400
    assert _strip_rid(r.json()) == BASE_FEW
    _assert_non_delivery(h)
    _failure_row(h, "Could not extract both products")


def _slow_compare(monkeypatch, seconds=0.6):
    delivered = {"success": True, "products": [{"brand": "A", "name": "one"},
                                               {"brand": "B", "name": "two"}],
                 "comparison": {}, "winner_index": 0, "recommendation": "",
                 "key_differences": [], "category_used": "other",
                 "source_urls": [FX_PDP, FX_PDP2]}

    async def slow(*a, **kw):
        await asyncio.sleep(seconds)
        return copy.deepcopy(delivered)
    monkeypatch.setattr(url_routes, "compare_from_urls", slow)


@pytest.mark.parametrize("verb", VERBS)
def test_deadline_yields_timeout_503(monkeypatch, client, caplog, verb):
    """RED (R16): a compare past the deadline is the structured 503 TIMEOUT,
    refunded once, one failure row, one WARNING, well before the hang ends."""
    _const(url_routes, "_URL_COMPARE_DEADLINE_SECONDS")
    h = _full(monkeypatch, H())
    monkeypatch.setattr(url_routes, "_URL_COMPARE_DEADLINE_SECONDS", 0.2)
    _slow_compare(monkeypatch)
    caplog.set_level(logging.INFO)
    t0 = time.monotonic()
    r = _call(client, verb, FX_PDP, FX_PDP2)
    wall = time.monotonic() - t0
    assert r.status_code == 503, r.json()
    body = r.json()
    assert body.get("code") == "TIMEOUT"
    assert body.get("error") == scs.TIMEOUT_FRIENDLY_MESSAGE
    assert set(body) == {"success", "error", "code", "request_id"}, body
    _assert_non_delivery(h)
    assert "usage_refund.url.compare.failure" in h.ledger.labels
    _failure_row(h, scs.TIMEOUT_FRIENDLY_MESSAGE)
    warns = [m for m in _messages(caplog, "app.api.url_routes", logging.WARNING)
             if m.startswith("[URL-V2] deadline")]
    assert len(warns) == 1 and re.fullmatch(r"\[URL-V2\] deadline 0\.2s hit", warns[0]), warns
    assert wall < 0.6, wall


@pytest.mark.parametrize("verb", VERBS)
def test_flag_off_no_deadline(monkeypatch, client, caplog, verb):
    """PIN (P17): flag OFF makes the base call with no deadline (full config)."""
    h = _full(monkeypatch, H(), flag=None)
    monkeypatch.setattr(url_routes, "_URL_COMPARE_DEADLINE_SECONDS", 0.2, raising=False)
    _slow_compare(monkeypatch)
    caplog.set_level(logging.INFO)
    t0 = time.monotonic()
    r = _call(client, verb, FX_PDP, FX_PDP2)
    assert r.status_code == 200, r.json()
    assert time.monotonic() - t0 >= 0.5
    assert not [m for m in _messages(caplog, "app.api.url_routes") if "deadline" in m]
    assert h.ledger.refunds == [] and h.ledger.lifetime == [h.user["id"]]


@pytest.mark.parametrize("verb", VERBS)
def test_deadline_exception_arm_untouched(monkeypatch, client, verb):
    """PIN (P18): compare_from_urls raising (flag ON) still takes the base
    exception arm: 500, the exception refund label, the constant row."""
    h = _full(monkeypatch, H())

    async def boom(*a, **kw):
        raise RuntimeError("b4 probe: compare raised")
    monkeypatch.setattr(url_routes, "compare_from_urls", boom)
    r = _call(client, verb, FX_PDP, FX_PDP2)
    assert r.status_code == 500
    assert "usage_refund.url.compare.exception" in h.ledger.labels, h.ledger.labels
    assert [row.get("error_message") for row in h.ledger.rows] == ["url_compare_exception"]


# ===========================================================================
# R19, P20: images
# ===========================================================================
_IMG = "https://img.example.test/"
R19_CASES = {
    "pdp_fixture": ({FX_PDP: ok(PDP)}, FX_PDP, PDP_IMAGE),
    "graph": ({"https://shop.example.test/p/g": ok(_page("G", [{
        "@context": "https://schema.org", "@graph": [
            {"@type": "WebSite", "name": "Shop"},
            _product("G Product", image=_IMG + "g.jpg")]}]))},
        "https://shop.example.test/p/g", _IMG + "g.jpg"),
    "type_list": ({"https://shop.example.test/p/t": ok(_page("T", [
        dict(_product("T Product", image=_IMG + "t.jpg"), **{"@type": ["Product", "Thing"]})]))},
        "https://shop.example.test/p/t", _IMG + "t.jpg"),
    "has_variant": ({"https://shop.example.test/p/v": ok(_page("V", [{
        "@context": "https://schema.org", "@type": "ProductGroup", "name": "PG",
        "hasVariant": [_product("PG 50ml", image=_IMG + "v.jpg")]}]))},
        "https://shop.example.test/p/v", _IMG + "v.jpg"),
    "image_object": ({"https://shop.example.test/p/o": ok(_page("O", [
        _product("O Product", image={"@type": "ImageObject", "url": _IMG + "o.jpg"})]))},
        "https://shop.example.test/p/o", _IMG + "o.jpg"),
    "protocol_relative": ({"https://shop.example.test/p/a": ok(_page("A", [
        _product("A Product", image=["//img.example.test/a.jpg"])]))},
        "https://shop.example.test/p/a", "https://img.example.test/a.jpg"),
    "http_only": ({"https://shop.example.test/p/h": ok(_page("H", [
        _product("H Product", image=["http://img.example.test/a.jpg"])]))},
        "https://shop.example.test/p/h", None),
    "og_fallback_relative": ({"https://shop.example.test/p/1": ok(_page(
        "N", [_product("N Product", image=None)], og={"image": "/img/p.jpg"}))},
        "https://shop.example.test/p/1", "https://shop.example.test/img/p.jpg"),
    "og_joined_on_final_url": ({
        "https://shop.example.test/old/1": redirect("https://cdn-shop.example.test/p/1", 301),
        "https://cdn-shop.example.test/p/1": ok(_page(
            "F", [_product("F Product", image=None)], og={"image": "/img/p.jpg"}))},
        "https://shop.example.test/old/1", "https://cdn-shop.example.test/img/p.jpg"),
    "no_image": ({"https://shop.example.test/p/n": ok(_page("Z", [_product("Z Product")]))},
                 "https://shop.example.test/p/n", None),
}


@pytest.mark.parametrize("parse_flag", [None, "true"], ids=["parse-off", "parse-on"])
@pytest.mark.parametrize("case", sorted(R19_CASES))
def test_pdp_image_is_first_https_string(monkeypatch, case, parse_flag):
    """RED (R19, run in both ENABLE_PRICE_PARSE_OFFLOAD states, B4-R10 Q7):
    extract_from_url(url, url_mode_v2=True) ships image_url as the first https
    url string or None (the @graph / @type list / hasVariant nodes found, the
    og:image key-presence bug fixed, urljoin against the FINAL url). No inline
    page carries an og:image except the og rows, and the LLM returns no
    image_url (review C20). Base: the LIST passes through; the ladder shapes
    find no Product."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    pages, url, want = R19_CASES[case]
    if parse_flag:
        monkeypatch.setenv(PARSE, parse_flag)
    h = H()
    _serve(monkeypatch, h, pages)
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content="{}")
    result = _run(ues.extract_from_url(url, url_mode_v2=True))
    assert result.get("success") is True, result
    product = result["product"]
    assert "image_url" in product
    value = product["image_url"]
    assert isinstance(value, (str, type(None))), value
    assert value == want, (case, value)


@pytest.mark.parametrize("env", [None, "true"], ids=["env-unset", "env-true"])
def test_flag_off_image_passes_through_raw(monkeypatch, env):
    """PIN (P20): extract_from_url(url) with no kwarg ships the RAW JSON-LD
    image (a LIST, the T07 base) whatever the env says (the route threads the
    bool; the service never reads the env)."""
    _set_flag(monkeypatch, env)
    h = H()
    _serve(monkeypatch, h, {FX_PDP: ok(PDP)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content="{}")
    result = _run(ues.extract_from_url(FX_PDP))
    assert result["success"] is True
    assert result["product"]["image_url"] == [PDP_IMAGE]


# ===========================================================================
# R21, R22, P23: recommendation / key_differences
# ===========================================================================
@pytest.mark.parametrize("verb", VERBS)
def test_recommendation_and_key_differences_filled(monkeypatch, client, verb):
    """RED (R21): the frozen keys are filled from the verdict prose; the key set
    is the base set (no metadata). Base: '' and []."""
    _full(monkeypatch, H(), pages={FX_PDP: ok(PDP), FX_PDP2: ok(PDP2)})
    r = _call(client, verb, FX_PDP, FX_PDP2)
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["recommendation"] == "B lasts longer on skin through the day."
    assert body["key_differences"] == ["brighter opening", "longer wear", "larger bottle"]
    assert set(body) == DELIVERY_KEYS, sorted(body)
    assert "metadata" not in body


@pytest.mark.parametrize("verb", VERBS)
def test_recommendation_fallback_when_reason_leaks_scores(monkeypatch, client, verb):
    """RED (R22): a score-leaking winner_reason is stripped and replaced by the
    qualitative fallback for the winner (index 1)."""
    _full(monkeypatch, H(), pages={FX_PDP: ok(PDP), FX_PDP2: ok(PDP2)}, verdict=VERDICT_LEAK)
    r = _call(client, verb, FX_PDP, FX_PDP2)
    assert r.status_code == 200, r.json()
    body = r.json()
    winner = body["products"][1]
    name = winner.get("full_name") or winner.get("name") or ""
    assert body["recommendation"] == response_builder._QUALITATIVE_WINNER_REASON(name)
    assert text_sanitize.has_score_internals(body["recommendation"]) is False


@pytest.mark.parametrize("verb", VERBS)
def test_flag_off_recommendation_empty(monkeypatch, client, verb):
    """PIN (P23): flag OFF (full config) keeps the base literals '' and []."""
    _full(monkeypatch, H(), flag=None, pages={FX_PDP: ok(PDP), FX_PDP2: ok(PDP2)})
    r = _call(client, verb, FX_PDP, FX_PDP2)
    assert r.status_code == 200
    assert r.json()["recommendation"] == "" and r.json()["key_differences"] == []


# ===========================================================================
# R24, P25, R26: the prompt
# ===========================================================================
_OPEN = re.compile(r"<SEARCH_RESULTS>")
_CLOSE = re.compile(r"</SEARCH_RESULTS>")
_RETAILER = {"key": "generic", "name": "Example"}
_PROMPT_URL = "https://www.example-retailer.com/p/iphone-17"


def test_prompt_v2_asks_is_product_page_and_keeps_shape(monkeypatch):
    """RED (R24): url_mode_v2=True renders V2: the is_product_page field, the
    guard, ONE region, the URL line before it, the base kwargs."""
    _assert_kwarg(ues.extract_with_ai, "url_mode_v2")
    from app.services.extraction_service import SEARCH_RESULTS_GUARD
    from tests.w4_11_prompt_digest_recorder import BENIGN_HTML
    h = H()
    _llm(monkeypatch, h, content='{"name": "iPhone 17"}')
    _run(ues.extract_with_ai(_PROMPT_URL, BENIGN_HTML, _RETAILER, url_mode_v2=True))
    assert len(h.llm_calls) == 1
    call = h.llm_calls[0]
    text = call["messages"][-1]["content"]
    assert '"is_product_page": true|false' in text
    assert text.startswith(SEARCH_RESULTS_GUARD + "\n\n")
    # The guard sentence itself names the tag, so the region is counted AFTER
    # it (the F13 reading, tests/test_prompt_fence.py: `opens[-1]`).
    body = text[len(SEARCH_RESULTS_GUARD):]
    opens = [m.start() for m in _OPEN.finditer(body)]
    closes = [m.start() for m in _CLOSE.finditer(body)]
    assert len(opens) == 1 and len(closes) == 1, (opens, closes)
    pos = body.find(f"URL: {_PROMPT_URL}\n")
    assert pos != -1 and pos < opens[0] < closes[0]
    assert {k: v for k, v in call.items() if k != "messages"} == {
        "model": "gpt-4o-mini", "max_tokens": 800, "temperature": 0.1, "store": False}


@pytest.mark.parametrize("env", [None, "true"], ids=["env-unset", "env-true"])
def test_prompt_off_render_equals_w411_digest(monkeypatch, env):
    """PIN (P25): no kwarg -> the base prompt (the service reads no env).

    DEVIATION from spec P25 (recorded in the RED report): the W4-11 fixture key
    `url_extract_user` is the PRE-fence render (recorded at 61585c58; the
    recorder's own comment says it MUST move when the fences land), so the
    base OFF render does NOT equal it. The row pins the OFF render against the
    digest MEASURED at base 81df2b64 through the recorder's exact url / html /
    retailer / answer, and the kwargs against the fixture's
    `url_extract_kwargs` (unchanged by the fence)."""
    from tests.w4_11_prompt_digest_recorder import BENIGN_HTML, FLAGS
    for name in FLAGS:
        monkeypatch.delenv(name, raising=False)
    _set_flag(monkeypatch, env)
    fixture = json.loads((_FIX / "w4_11_prompt_render_digests.json").read_text(encoding="utf-8"))
    h = H()
    _llm(monkeypatch, h, content='{"name": "iPhone 17"}')
    _run(ues.extract_with_ai(_PROMPT_URL, BENIGN_HTML, _RETAILER))
    assert len(h.llm_calls) == 1
    text = h.llm_calls[0]["messages"][-1]["content"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == BASE_URL_EXTRACT_USER_SHA
    assert {k: v for k, v in h.llm_calls[0].items() if k != "messages"} == fixture["url_extract_kwargs"]


def test_prompt_v2_is_derived_from_v1():
    """RED (R26): V2 differs from V1; V1 is byte-identical to base; removing the
    two added lines from V2 yields V1; the 9-key enumeration appears once in
    each; V2 carries no stale category token."""
    v1 = ues.URL_EXTRACTION_PROMPT
    v2 = _const(ues, "URL_EXTRACTION_PROMPT_V2")
    assert isinstance(v2, str) and v2 != v1
    assert hashlib.sha256(v1.replace("\r", "").encode("utf-8")).hexdigest() == BASE_PROMPT_SHA
    assert v2.count("is_product_page") == 2, v2.count("is_product_page")
    stripped = re.sub(r',\n[ \t]*"is_product_page": true\|false', "", v2, count=1)
    stripped = re.sub(r"\n- is_product_page[^\n]*", "", stripped, count=1)
    assert stripped == v1
    enum = "electronics|grocery|supplements|makeup|skincare|haircare|fragrances|fashion|other"
    assert v1.count(enum) == 1 and v2.count(enum) == 1
    for stale in ("beauty", "automotive", "sports", "|home|"):
        assert stale not in v2, stale


# ===========================================================================
# R27, R43, R44, R28: the UNRESOLVED rule (ruling B4-R1)
# ===========================================================================
_HAWAS = "https://store.rasasi.com.sa/en/hawas-ice"


def _unresolved(url, reason):
    return {"success": False, "code": "UNRESOLVED_PRODUCT", "reason": reason, "url": url,
            "error": UP_MSG}


@pytest.mark.parametrize("answer", ["not_product_page", "name_null", "empty", "offline"])
def test_llm_answers_on_a_usable_title_page(monkeypatch, answer):
    """RED (R27 as amended by B4-R1): a page with NO Product node and a usable
    title: the LLM's is_product_page false refuses (not_product_page); a null
    name, an empty answer or the offline {'error'} shape DELIVER with
    name == the title (the usable title keeps the page)."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    _serve(monkeypatch, h, {_HAWAS: ok(_page("Rasasi Hawas Ice"))})
    _ssrf(monkeypatch, h)
    content = {"not_product_page": '{"is_product_page": false, "name": "x"}',
               "name_null": '{"is_product_page": true, "name": null}',
               "empty": "{}"}.get(answer)
    _llm(monkeypatch, h, content=content or "{}", boom=(answer == "offline"))
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert len(h.llm_calls) == 1, h.llm_calls
    if answer == "not_product_page":
        assert result == _unresolved(_HAWAS, "not_product_page"), result
    else:
        assert result.get("success") is True, result
        assert result["product"]["name"] == "Rasasi Hawas Ice"
        assert "error" not in result["product"]


def test_node_bearing_page_with_llm_false_delivers(monkeypatch):
    """RED (R43, B4-R1): a page WITH a Product node (no price, so the LLM is
    consulted) and an LLM answer is_product_page false still DELIVERS."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    _serve(monkeypatch, h, {_HAWAS: ok(_page("Rasasi Hawas Ice | Rasasi",
                                             [_product("Rasasi Hawas Ice", price=None)]))})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content='{"is_product_page": false}')
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert len(h.llm_calls) == 1, h.llm_calls
    assert result.get("success") is True, result
    assert result["product"]["name"] == "Rasasi Hawas Ice"


def test_null_name_only_when_the_title_is_unusable(monkeypatch):
    """RED (R44, B4-R1): a Product node without a name, an empty <title> and an
    LLM answer with no name -> UNRESOLVED_PRODUCT / null_name (never
    'Unknown Product')."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    _serve(monkeypatch, h, {_HAWAS: ok(_page("", [_product(name=None, price="10")]))})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content='{"name": null}')
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert result == _unresolved(_HAWAS, "null_name"), result
    assert "Unknown Product" not in json.dumps(result)


@pytest.mark.parametrize("answer", ['{"name": null}', "{}", "offline"],
                         ids=["name_null", "empty", "offline"])
def test_never_unknown_product_flag_on(monkeypatch, answer):
    """RED (R28 as corrected by review C8): an empty-title page with no node is
    UNRESOLVED / no_product_node with NO LLM call; 'Unknown Product' nowhere."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    _serve(monkeypatch, h, {_HAWAS: ok(_page(""))})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content=answer if answer != "offline" else "{}", boom=(answer == "offline"))
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert result == _unresolved(_HAWAS, "no_product_node"), result
    assert h.llm_calls == []
    assert "Unknown Product" not in json.dumps(result)


@pytest.mark.parametrize("code,reason", [(403, "http_403"), (404, "http_4xx"), (500, "http_5xx"),
                                         (302, "http_3xx")])
def test_non_2xx_reason_table(monkeypatch, code, reason):
    """RED (review C19): the status reason table at the service level; a 3xx
    with NO Location ends the loop and is http_3xx."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    _serve(monkeypatch, h, {FX_PDP2: status(code)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h)
    result = _run(ues.extract_from_url(FX_PDP2, url_mode_v2=True))
    assert result == {"success": False, "code": "STORE_UNREADABLE", "reason": reason,
                      "url": FX_PDP2, "error": SU_MSG}, result
    assert h.llm_calls == []


# ===========================================================================
# R29, R30, R31: the pure tables
# ===========================================================================
PATH_TABLE = [
    ("/", "homepage"), ("", "homepage"), ("/en", "homepage"), ("/ar/", "homepage"),
    ("/en-bh/", "homepage"), ("/index.html", "homepage"), ("/index.php", "homepage"),
    ("/search", "search"), ("/search?q=x", "search"), ("/catalogsearch/result/", "search"),
    ("/cart", "cart"), ("/checkout", "cart"), ("/en/checkouts/abc", "cart"),
    ("/account", "account"), ("/en/account/login", "account"),
    ("/customer/account/login", "account"),
    ("/collections/men", "category"), ("/en/category/perfume", "category"),
    ("/c/fragrance", "category"), ("/brands/dior", "category"),
    ("/collections/men/products/sauvage", None), ("/products/christian-dior/sauvage-cologne", None),
    ("/en/-/p666775809", None), ("/dp/B0CHX1W1XY", None), ("/shop/sauvage-100ml/", None),
    ("/uae-en/samsung-galaxy-s24/N123456", None), ("/p/12345", None),
    # B4-R7: the measured misses, pinned as current behaviour (L3)
    ("/ar/search", None), ("/s", None), ("/uae-en/search/", None), ("/uae-en/", None),
    ("/uae-en", None), ("/eng/", None), ("/en/cart.html", None),
]


@pytest.mark.parametrize("path,expected", PATH_TABLE)
def test_classify_url_path_table(path, expected):
    """RED (R29): the path classifier table (query ignored, path-anchored)."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) == expected, path


def test_normalize_url_table():
    """RED (R30 + B4-R4): the same-url normaliser; malformed -> '' (never
    raises); two '' never make a same_url refusal."""
    norm = _fn(ues, "normalize_url_for_same_check")
    pre_gate = _fn(url_routes, "_url_pre_gate")
    base = norm(FX_PDP)
    assert base != ""
    for other in (FX_PDP + "/", "HTTPS://WWW.FragranceX.com/products/christian-dior/sauvage-cologne",
                  "https://fragrancex.com/products/christian-dior/sauvage-cologne",
                  FX_PDP + "?utm=1#top"):
        assert norm(other) == base, other
    assert norm("https://a.test/x") != norm("https://a.test/X")
    assert norm("https://a.test/x") != norm("https://a.test:8443/x")
    for bad in ("not a url", "also not", "http://[", "https://a.test:99999/x", None, 7):
        assert norm(bad) == "", bad
    assert pre_gate("not a url", "also not") is None


def test_is_usable_title_table():
    """RED (R31): placeholders and site names are not usable titles."""
    usable = _fn(ues, "is_usable_title")
    site_names_of = _fn(ues, "_v2_site_names")
    for bad in (None, "", "Unknown", "unknown product", "N/A", "Product", "This Product "):
        assert usable(bad, set()) is False, bad
    store_html = STOREFRONT.decode("utf-8")
    names = site_names_of(ues.extract_json_ld(store_html), ues.extract_meta_tags(store_html))
    assert usable(STOREFRONT_TITLE, names) is False
    og_names = site_names_of([], {"og_site_name": "FragranceX"})
    assert usable("FragranceX", og_names) is False
    assert usable("Christian Dior Sauvage Cologne - FragranceX", og_names) is True
    assert usable("Christian Dior Sauvage Cologne - FragranceX", set()) is True


# ===========================================================================
# R32: the scoped error-handler passthrough (B4-R5)
# ===========================================================================
def _mini_app(detail):
    mini = FastAPI()
    mini.add_exception_handler(HTTPException, error_handler.http_exception_handler)

    @mini.get("/x")
    def _x():
        raise HTTPException(status_code=400, detail=detail)
    return TestClient(mini, raise_server_exceptions=False)


@pytest.mark.parametrize("code", ["NOT_PRODUCT_PAGE", "STORE_UNREADABLE", "UNRESOLVED_PRODUCT"])
def test_error_handler_passthrough_on(monkeypatch, code):
    """RED (R32 ON half): the three B4 codes carry str field / reason to the wire;
    a non-str value is dropped."""
    _fn(error_handler, "_url_mode_v2_keys_enabled")
    _set_flag(monkeypatch, "true")
    body = _mini_app({"code": code, "error": "m", "field": "url1", "reason": "homepage"}).get("/x").json()
    assert _strip_rid(body) == {"success": False, "error": "m", "code": code,
                                "field": "url1", "reason": "homepage"}, body
    body = _mini_app({"code": code, "error": "m", "field": 7, "reason": "homepage"}).get("/x").json()
    assert _strip_rid(body) == {"success": False, "error": "m", "code": code,
                                "reason": "homepage"}, body


_B4_KEYS = {"code": "NOT_PRODUCT_PAGE", "error": "m", "field": "url1", "reason": "homepage"}
_B4_NO_KEYS = {"code": "NOT_PRODUCT_PAGE", "error": "m"}
_OTHER_KEYS = {"code": "INSUFFICIENT_DATA", "error": "m", "field": "url1", "reason": "homepage"}


@pytest.mark.parametrize("flag,detail", [
    (None, _B4_KEYS), (None, _B4_NO_KEYS), (None, _OTHER_KEYS),
    ("true", _B4_NO_KEYS), ("true", _OTHER_KEYS),
], ids=["off-b4-code-keys", "off-b4-code-no-keys", "off-other-code-keys",
        "on-b4-code-no-keys", "on-other-code-keys"])
def test_error_handler_four_key_body(monkeypatch, flag, detail):
    """PIN (R32 OFF half + scope, B4-R5): flag OFF -> the four-key body for every
    detail (kills M11); flag ON -> the four-key body for a B4 detail without the
    keys and for ANY other code carrying them (the passthrough is scoped to the
    three B4 codes, never a global two-key scan)."""
    _set_flag(monkeypatch, flag)
    body = _mini_app(detail).get("/x").json()
    assert set(body) == {"success", "error", "code", "request_id"}, body
    assert body["code"] == detail["code"] and body["error"] == "m"


# ===========================================================================
# R34: host-only INFO lines (UNFLAGGED)
# ===========================================================================
def test_info_lines_print_host_only(monkeypatch, client, caplog):
    """RED (R34, unflagged): the request line, the two Detected-retailer lines
    and the /extract line print the host only (no path, no query)."""
    h = _full(monkeypatch, H(), flag=None, pages={FX_PDP + "?gclid=abc": ok(PDP), FX_PDP2: ok(PDP2)})
    caplog.set_level(logging.INFO)
    r = _call(client, "POST", FX_PDP + "?gclid=abc", FX_PDP2)
    assert r.status_code == 200, r.json()
    req = [m for m in _messages(caplog, "app.api.url_routes") if m.startswith("URL comparison request")]
    assert len(req) == 1 and "www.fragrancex.com" in req[0], req
    assert "/products/" not in req[0] and "gclid" not in req[0], req
    det = [m for m in _messages(caplog, "app.services.url_extraction_service")
           if m.startswith("Detected retailer")]
    assert len(det) == 2, det
    for line in det:
        assert "www.fragrancex.com" in line and "/products/" not in line and "gclid" not in line, det
    caplog.clear()
    h.pages.pages[FX_PDP] = ok(PDP)
    r = client.post("/api/v1/url/extract", json={"url": FX_PDP + "?gclid=abc"},
                    headers={"X-Request-ID": RID})
    ext = [m for m in _messages(caplog, "app.api.url_routes") if m.startswith("URL extraction request")]
    assert len(ext) == 1, ext
    assert "host=" in ext[0] and "www.fragrancex.com" in ext[0], ext
    assert "/products/" not in ext[0] and "gclid" not in ext[0], ext


def test_info_line_survives_a_malformed_url(monkeypatch, client, caplog):
    """RED (R34 + B4-R4): a malformed pasted link never raises in the host-only
    line: the request is the SSRF 400, the INFO line is emitted, no path."""
    h = _full(monkeypatch, H(), flag=None)
    _ssrf(monkeypatch, h, deny_all=True)
    caplog.set_level(logging.INFO)
    r = _call(client, "POST", "http://[", "https://a.test:99999/x")
    assert r.status_code == 400 and _strip_rid(r.json()) == BASE_SSRF, r.json()
    req = [m for m in _messages(caplog, "app.api.url_routes") if m.startswith("URL comparison request")]
    assert len(req) == 1, req
    assert "/x" not in req[0] and "99999" not in req[0], req


# ===========================================================================
# R35: every new code is a non-delivery (R-A3)
# ===========================================================================
def _r35_pages(code):
    if code == "NOT_PRODUCT_PAGE":
        return {FX_PDP2: redirect(FX_HOME), FX_HOME: ok(STOREFRONT), FX_PDP: ok(PDP)}
    if code == "STORE_UNREADABLE":
        return {FX_PDP2: status(403), FX_PDP: ok(PDP)}
    return {FX_PDP2: ok(STOREFRONT), FX_PDP: ok(PDP)}


@pytest.mark.parametrize("meter", [True, False], ids=["meter-on", "meter-off"])
@pytest.mark.parametrize("code", ["NOT_PRODUCT_PAGE", "STORE_UNREADABLE", "UNRESOLVED_PRODUCT",
                                  "TIMEOUT"])
@pytest.mark.parametrize("verb", VERBS)
def test_non_delivery_per_r_a3_every_code(monkeypatch, client, verb, code, meter):
    """RED (R35): each new code is a non-delivery through the existing exit:
    metering ON -> consumed once, refunded once, no lifetime, no history;
    metering OFF -> nothing consumed or refunded; never the success labels."""
    if code == "TIMEOUT":
        _const(url_routes, "_URL_COMPARE_DEADLINE_SECONDS")
    h = _full(monkeypatch, H(), meter=meter, pages=_r35_pages(code))
    if code == "TIMEOUT":
        monkeypatch.setattr(url_routes, "_URL_COMPARE_DEADLINE_SECONDS", 0.2)
        _slow_compare(monkeypatch)
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.json().get("code") == code, r.json()
    assert r.status_code == (503 if code == "TIMEOUT" else 400)
    if meter:
        _assert_non_delivery(h)
    else:
        assert h.ledger.consumes == [] and h.ledger.refunds == []
        assert h.ledger.lifetime == [] and h.ledger.history == []
    assert "save_comparison.url" not in h.ledger.labels
    assert "record_lifetime.url" not in h.ledger.labels


# ===========================================================================
# P36: the W4-13 url rows unchanged with the flag OFF
# ===========================================================================
@pytest.mark.parametrize("value", [None, "false", "garbage"])
def test_w4_13_rows_unchanged_flag_off(monkeypatch, client, value):
    """PIN (P36): the five W4-13 url scenarios re-driven with the flag OFF equal
    the committed fixture records (status, body, calls, labels)."""
    import tests.test_w4_13_measurement_truth as T
    for name in ("ENABLE_SEARCH_LOG_TRUTH", "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
                 "SEARCH_LOG_SYNTHETIC_TOKEN", METER):
        monkeypatch.delenv(name, raising=False)
    _set_flag(monkeypatch, value)
    fixture = json.loads((_FIX / "w4_13_flag_off_ledger.json").read_text(encoding="utf-8"))
    want = {r["scenario"]: r for r in fixture["records"] if r["scenario"].startswith("url.")}
    scenarios = (("success", dict(result=T.URL_OK)), ("few", dict(result=T.URL_FEW)),
                 ("llm", dict(result=T.URL_LLM)), ("raise", dict(raises=True)),
                 ("ssrf", dict(result=T.URL_OK, valid=False)))
    for name, kw in scenarios:
        r, calls, labels = T._url(monkeypatch, client, **kw)
        try:
            body = r.json()
        except Exception:  # noqa: BLE001
            body = r.text
        got = json.loads(json.dumps({"body": body, "calls": [T._norm(c) for c in calls],
                                     "labels": labels, "scenario": f"url.{name}",
                                     "status": r.status_code}))
        assert got == want[f"url.{name}"], (name, got, want[f"url.{name}"])


def test_w4_13_rows_full_config_flag_off(monkeypatch, client):
    """PIN (P36, B1 rule): truth + metering ON, authed, flag 'off': the five url
    bodies equal the fixture bodies and the rows carry the base constants."""
    import tests.test_w4_13_measurement_truth as T
    _set_flag(monkeypatch, "off")
    monkeypatch.setenv(TRUTH, "true")
    fixture = json.loads((_FIX / "w4_13_flag_off_ledger.json").read_text(encoding="utf-8"))
    want = {r["scenario"]: r for r in fixture["records"] if r["scenario"].startswith("url.")}
    expect_rows = {"success": [None], "few": ["Could not extract both products"],
                   "llm": [scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE],
                   "raise": ["url_compare_exception"], "ssrf": []}
    for name, kw in (("success", dict(result=T.URL_OK)), ("few", dict(result=T.URL_FEW)),
                     ("llm", dict(result=T.URL_LLM)), ("raise", dict(raises=True)),
                     ("ssrf", dict(result=T.URL_OK, valid=False))):
        r, calls, _labels = T._url(monkeypatch, client, meter=True, user=T.AUTHED, **kw)
        assert r.status_code == want[f"url.{name}"]["status"], name
        assert r.json() == want[f"url.{name}"]["body"], name
        assert [c.get("error_message") for c in calls] == expect_rows[name], (name, calls)


# ===========================================================================
# R38, R39: the conditional kwarg; fetch_page byte-unchanged
# ===========================================================================
@pytest.mark.parametrize("flag", [None, "true"], ids=["off", "on"])
@pytest.mark.parametrize("verb", VERBS)
def test_v2_kwarg_is_conditional(monkeypatch, client, verb, flag):
    """PIN (off) / RED (on) (R38): the route passes url_mode_v2=True ONLY when
    the flag is ON; OFF it is the base positional 4-argument call."""
    h = _full(monkeypatch, H(), flag=flag)
    seen = []

    async def rec(*a, **kw):
        seen.append((a, dict(kw)))
        return {"success": True, "products": [{"brand": "A", "name": "one"},
                                              {"brand": "B", "name": "two"}],
                "comparison": {}, "winner_index": 0, "recommendation": "",
                "key_differences": [], "category_used": "other", "source_urls": []}
    monkeypatch.setattr(url_routes, "compare_from_urls", rec)
    r = _call(client, verb, FX_PDP, FX_PDP2)
    assert r.status_code == 200, r.json()
    assert len(seen) == 1
    args, kwargs = seen[0]
    assert len(args) == 4, seen
    assert kwargs == ({"url_mode_v2": True} if flag else {}), seen
    assert h.ledger.refunds == []


def test_fetch_page_untouched_pin(monkeypatch):
    """PIN (R39, review C18): fetch_page's source is byte-identical to base and
    it still blocks a redirect to the metadata address without requesting it."""
    src = inspect.getsource(ues.fetch_page).replace("\r", "")
    assert hashlib.sha256(src.encode("utf-8")).hexdigest() == BASE_FETCH_PAGE_SHA
    h = H()
    _serve(monkeypatch, h, {"https://attacker.example.test/p": redirect(METADATA_URL)})
    _ssrf(monkeypatch, h, deny=("169.254",))
    assert _run(ues.fetch_page("https://attacker.example.test/p")) is None
    assert h.pages.fetched == ["https://attacker.example.test/p"]


# ===========================================================================
# R40-R42: _fetch_page_v2 SSRF (ruling B4-R3, mandatory)
# ===========================================================================
_V2_KEYS = {"status", "final_url", "text", "outcome", "error_type"}


def test_fetch_page_v2_blocks_private_initial_url(monkeypatch, caplog):
    """RED (R40): a blocked initial url -> outcome blocked, zero requests."""
    fetch_v2 = _fn(ues, "_fetch_page_v2")
    h = H()
    _serve(monkeypatch, h, default=ok("<html>secret</html>"))
    _ssrf(monkeypatch, h, deny=("127.0.0.1", "169.254"))
    caplog.set_level(logging.INFO)
    res = _run(fetch_v2("http://127.0.0.1/admin"))
    assert set(res) == _V2_KEYS, res
    assert res["outcome"] == "blocked" and res["text"] is None, res
    assert h.pages.fetched == []
    warns = _messages(caplog, "app.services.url_extraction_service", logging.WARNING)
    assert any(w.startswith("[SSRF] Blocked initial URL") for w in warns), warns


def test_fetch_page_v2_blocks_redirect_to_metadata(monkeypatch, caplog):
    """RED (R41): a 302 to the cloud-metadata address -> outcome blocked, the
    internal target NEVER requested, the base WARNING line."""
    fetch_v2 = _fn(ues, "_fetch_page_v2")
    h = H()
    _serve(monkeypatch, h, {"https://attacker.example.test/p": redirect(METADATA_URL)},
           default=ok("<html>secret</html>"))
    _ssrf(monkeypatch, h, deny=("127.0.0.1", "169.254"))
    caplog.set_level(logging.INFO)
    res = _run(fetch_v2("https://attacker.example.test/p"))
    assert res["outcome"] == "blocked", res
    assert h.pages.fetched == ["https://attacker.example.test/p"], h.pages.fetched
    warns = _messages(caplog, "app.services.url_extraction_service", logging.WARNING)
    assert any(w.startswith("[SSRF] Blocked redirect") for w in warns), warns


def test_fetch_page_v2_caps_redirect_chain(monkeypatch):
    """RED (R42): a 10-hop public loop -> outcome redirect_cap after at most 6
    requests."""
    fetch_v2 = _fn(ues, "_fetch_page_v2")
    h = H()
    pages = {f"https://x.example.test/{i}": redirect(f"https://x.example.test/{i + 1}")
             for i in range(12)}
    _serve(monkeypatch, h, pages)
    _ssrf(monkeypatch, h)
    res = _run(fetch_v2("https://x.example.test/0"))
    assert res["outcome"] == "redirect_cap", res
    assert 1 <= len(h.pages.fetched) <= 6, h.pages.fetched


def test_fetch_page_v2_keeps_status_and_final_url(monkeypatch):
    """RED (R42b): a followed redirect ends 'ok' with the LAST status, the FINAL
    url and the text; a 403 keeps its status (no raise_for_status)."""
    fetch_v2 = _fn(ues, "_fetch_page_v2")
    h = H()
    _serve(monkeypatch, h, {"https://x.example.test/a": redirect("https://y.example.test/b"),
                            "https://y.example.test/b": ok("<html>ok</html>"),
                            "https://x.example.test/f": status(403)})
    _ssrf(monkeypatch, h)
    res = _run(fetch_v2("https://x.example.test/a"))
    assert res == {"status": 200, "final_url": "https://y.example.test/b", "text": "<html>ok</html>",
                   "outcome": "ok", "error_type": None}, res
    res = _run(fetch_v2("https://x.example.test/f"))
    assert res["status"] == 403 and res["outcome"] == "ok" and res["error_type"] is None, res


# ===========================================================================
# Fix round 1 (RULINGS_FIX1_B4 F4-2): the normaliser-stage image coercion
# ===========================================================================
_NOON_PDP = "https://www.noon.com/uae-en/b4-probe-oud/N4B4PROBEA/p/"
_AMAZON_PDP = "https://www.amazon.ae/b4-probe-parfum/dp/B0B4PROBE1"
_LLM_PDP = "https://shop.example.test/p/llm-merged"
_LLM_PAGE = _page("B4 Probe Musk - Shop", [_product("B4 Probe Musk", price=None)])
# case -> (url, page, LLM answer or None for "no LLM call", the image_url that ships)
_NORMALISER_IMAGE_CASES = {
    # noon: the base extractor hands the RAW JSON-LD image list to the normaliser
    "noon_jsonld_list": (
        _NOON_PDP,
        _page("B4 Probe Oud | noon", [_product(
            "B4 Probe Oud 100ml", price="30",
            image=["http://f.nooncdn.example.test/b4-http.jpg",
                   "https://f.nooncdn.example.test/b4.jpg"])]),
        None, "https://f.nooncdn.example.test/b4.jpg"),
    # amazon: the base extractor's raw landingImage src (protocol-relative)
    "amazon_raw_src": (
        _AMAZON_PDP,
        _page("Amazon.ae: B4 Probe Parfum", body=(
            '<span id="productTitle">B4 Probe Parfum 100ml</span>'
            '<span class="a-price-whole">12</span>'
            '<img id="landingImage" src="//m.media.example.test/images/b4.jpg">')),
        None, "https://m.media.example.test/images/b4.jpg"),
    # generic page, a node without an image or a price: the LLM's image LIST is
    # merged raw into raw_data (the v2 extractor found none)
    "llm_merged_list": (
        _LLM_PDP, _LLM_PAGE,
        {"is_product_page": True, "price": 9.5, "currency": "USD",
         "image_url": ["http://img.example.test/llm-http.jpg",
                       "https://img.example.test/llm.jpg"]},
        "https://img.example.test/llm.jpg"),
    # the same with no https member: null, never a list or an http url
    "llm_merged_http_only": (
        _LLM_PDP, _LLM_PAGE,
        {"is_product_page": True, "price": 9.5, "currency": "USD",
         "image_url": ["http://img.example.test/llm-http.jpg"]},
        None),
}


def test_normaliser_coerces_a_raw_image_list_flag_on(monkeypatch):
    """PIN (fix round 1, RULINGS_FIX1_B4 F4-2; kills the GREEN mutant G10, the
    normaliser-stage coercion removed): under url_mode_v2=True a product whose
    image reaches normalize_product_data RAW (the noon extractor's JSON-LD list,
    the amazon extractor's protocol-relative src, an LLM-merged list when the v2
    extractor found none) ships image_url as ONE absolute https url string (the
    first https member, joined against the final url), or None when no member is
    https; never a list. Run in both ENABLE_PRICE_PARSE_OFFLOAD states. Green on
    the GREEN bytes 9db99de9; at base 81df2b64 it fails on the _assert_kwarg
    AssertionError (the R19 class)."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    seen = {}
    for parse_flag in (None, "true"):
        if parse_flag:
            monkeypatch.setenv(PARSE, parse_flag)
        else:
            monkeypatch.delenv(PARSE, raising=False)
        for case in sorted(_NORMALISER_IMAGE_CASES):
            url, page, llm, want = _NORMALISER_IMAGE_CASES[case]
            h = H()
            _serve(monkeypatch, h, {url: ok(page)})
            _ssrf(monkeypatch, h)
            _llm(monkeypatch, h, content=json.dumps(llm) if llm is not None else "{}")
            result = _run(ues.extract_from_url(url, url_mode_v2=True))
            assert result.get("success") is True, (case, parse_flag, result)
            value = result["product"]["image_url"]
            assert isinstance(value, (str, type(None))), (case, parse_flag, value)
            assert value == want, (case, parse_flag, value)
            assert len(h.llm_calls) == (0 if llm is None else 1), (case, parse_flag, h.llm_calls)
            seen[(case, parse_flag)] = value
    assert len(seen) == 2 * len(_NORMALISER_IMAGE_CASES), seen
