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


# ===========================================================================
# Fix round 2 (RULINGS_FIX2_B4): F2-1 a query-routed PDP is not the homepage,
# F2-2 the linear challenge-title scan, F2-4 contract pins, F2-5 no placeholder
# product name. RED rows fail at 96676f1f on an AssertionError only; PIN rows
# are green there and are proven by the mutant named in their docstring.
# ===========================================================================
_OC_PDP = "https://www.b4opencart.example.test/index.php?route=product/product&product_id=1262"
_OC_ROOT_PDP = "https://www.b4opencart2.example.test/?route=product/product&product_id=4154"
_PS_PDP = "https://www.b4presta.example.test/index.php?id_product=12&controller=product"
_WC_PDP = "https://www.b4woo.example.test/?product=b4-probe-oud-edp"
_QR_NAMES = {
    _OC_PDP: "B4 Probe Oud 100ml",
    _OC_ROOT_PDP: "B4 Probe Amber 50ml",
    _PS_PDP: "B4 Probe Musk 75ml",
    _WC_PDP: "B4 Probe Oud EDP 90ml",
}
_QR_PAGES = {url: ok(_page(name + " - Store", [_product(name, price="12.5")]))
             for url, name in _QR_NAMES.items()}

F2_1_PRODUCT_ROUTE_ROWS = [
    "/index.php?route=product/product&product_id=1262",
    "/?route=product/product&product_id=4154",
    "/index.php?route=product/product&path=20&product_id=5313",
    "/index.php?route=product/product",
    "/index.php?product_id=2058",
    "/index.php?id_product=12&controller=product",
    "/?product=b4-probe-oud-edp",
    "/index.html?product=b4-probe-oud-edp",
    "/en/?product=b4-probe-oud-edp",
    "/index.php?PRODUCT_ID=7",
    "/index.php?Id_Product=12",
    "/?ROUTE=product/product",
    "/?gclid=x&product_id=9",
]

F2_1_STILL_HOMEPAGE_ROWS = [
    "/?gclid=x", "/?gbraid=x", "/?utm_source=x", "/?fbclid=x", "/index.php", "/index.php?",
    "/?p=123",  # stated limit F2-6d: a bare WordPress `p` id is not in the allow-list
    "/index.php?route=common/home", "/?routes=product/x", "/?product_ids=1",
    "/?utm_content=product_id", "/?ref=product",
]


@pytest.mark.parametrize("path", F2_1_PRODUCT_ROUTE_ROWS)
def test_classify_url_path_product_route_query_is_not_homepage(path):
    """RED (F2-1, adversary M1): a root or /index.* path whose QUERY names a
    product route (OpenCart route=product/... or product_id, PrestaShop
    id_product, WooCommerce product; keys case-insensitive) is not the
    homepage. At 96676f1f the path alone decides: 'homepage'."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) is None, path


@pytest.mark.parametrize("path", F2_1_STILL_HOMEPAGE_ROWS)
def test_classify_url_path_tracking_query_stays_homepage(path):
    """PIN (F2-1 guard; kills a blanket 'any non-empty query is not the
    homepage' exemption and a substring match on 'product' anywhere in the
    query): tracking-only and non-product queries keep the homepage class."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) == "homepage", path


@pytest.mark.parametrize("pair", [(_OC_PDP, _OC_ROOT_PDP), (_PS_PDP, _OC_PDP), (_WC_PDP, _OC_PDP)],
                         ids=["opencart-opencart", "prestashop-opencart", "woocommerce-opencart"])
@pytest.mark.parametrize("verb", VERBS)
def test_query_routed_pdp_pair_delivers_flag_on(monkeypatch, client, verb, pair):
    """RED (F2-1, adversary M1, the pre-gate site): two query-routed product
    pages (OpenCart / PrestaShop / WooCommerce shapes on a root or /index.php
    path) pass the pre-gate, are fetched and DELIVER (flag ON, full config).
    At 96676f1f: 400 NOT_PRODUCT_PAGE homepage before any fetch."""
    h = _full(monkeypatch, H(), pages=_QR_PAGES)
    r = _call(client, verb, *pair)
    assert r.status_code == 200, (r.status_code, r.json())
    body = r.json()
    assert body.get("success") is True, body
    assert [p["name"] for p in body["products"]] == [_QR_NAMES[pair[0]], _QR_NAMES[pair[1]]], body
    assert sorted(h.pages.fetched) == sorted(pair), h.pages.fetched
    assert h.events[:3] == ["ssrf", "ssrf", "pregate"], h.events
    uid = h.user["id"]
    assert h.ledger.consumes == [uid] and h.ledger.refunds == [], (h.ledger.consumes, h.ledger.refunds)
    assert h.ledger.lifetime == [uid] and h.ledger.history == ["url"], (h.ledger.lifetime,
                                                                          h.ledger.history)


_OC_START = "https://www.b4opencart.example.test/b4-probe-oud-100ml"


@pytest.mark.parametrize("verb", VERBS)
def test_redirect_to_query_routed_pdp_is_not_refused_post_fetch(monkeypatch, client, verb):
    """RED (F2-1, the post-fetch site, the GC-2 reuse): a link redirecting to an
    OpenCart query-routed PDP at /index.php is not refused on its FINAL url; the
    pair delivers. At 96676f1f: 400 NOT_PRODUCT_PAGE homepage after the fetch."""
    pages = dict(_QR_PAGES)
    pages[_OC_START] = redirect(_OC_PDP, 301)
    pages[FX_PDP] = ok(PDP)
    h = _full(monkeypatch, H(), pages=pages)
    r = _call(client, verb, _OC_START, FX_PDP)
    assert r.status_code == 200, (r.status_code, r.json())
    body = r.json()
    assert body.get("success") is True, body
    assert body["products"][0]["name"] == _QR_NAMES[_OC_PDP], body
    assert sorted(h.pages.fetched) == sorted([_OC_START, _OC_PDP, FX_PDP]), h.pages.fetched


@pytest.mark.parametrize("verb", VERBS)
def test_redirect_to_tracking_root_is_still_homepage_post_fetch(monkeypatch, client, verb):
    """PIN (F2-1 guard at the post-fetch site; kills the blanket-query
    exemption): a redirect ending on the storefront root with a tracking-only
    query is still NOT_PRODUCT_PAGE / homepage, refunded once."""
    root = "https://www.fragrancex.com/?utm_source=b4"
    h = _full(monkeypatch, H(), pages={FX_PDP2: redirect(root), root: ok(STOREFRONT), FX_PDP: ok(PDP)})
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 400, r.json()
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "url1", "homepage")
    _assert_non_delivery(h)


# F2-2: about 66 KB of '<title ' openers with no close tag (the engineering
# adversary's probe-1 page): the regex retried the lazy group from every opener.
_TITLE_FLOOD_NO_GT = "<html><head><title " + "<title " * 9400 + "></head><body>b4</body></html>"
_TITLE_FLOOD_GT_NO_CLOSE = "<html><head><title " + "<title " * 9000 + "></head><body>b4</body></html>"


@pytest.mark.parametrize("page", [_TITLE_FLOOD_NO_GT, _TITLE_FLOOD_GT_NO_CLOSE],
                         ids=["no-gt-in-window", "gt-no-close"])
def test_challenge_title_scan_is_linear(page):
    """RED (F2-2, adversary E1): the challenge check over a crafted title flood
    returns the right verdict (not a challenge) within a LENIENT 500 ms (the
    linear scan is about 1 ms; the quadratic regex at 96676f1f took about
    2.5 s on this box, on the event loop)."""
    is_challenge = _fn(ues, "_is_challenge_page")
    assert 60000 < len(page) < 70000, len(page)
    started = time.perf_counter()
    verdict = is_challenge(page)
    elapsed = time.perf_counter() - started
    assert verdict is False, verdict
    assert elapsed < 0.5, f"_is_challenge_page took {elapsed * 1000:.0f} ms on {len(page)} bytes"


_CHALLENGE_TITLE_CASES = [
    ("<html><head><title>Just a moment...</title></head><body></body></html>", True),
    ("<HTML><HEAD><TITLE>Attention Required! | Cloudflare</TITLE></HEAD></HTML>", True),
    ('<html><head><title data-rh="true" lang="en">Access denied</title></head></html>', True),
    ("<html><head><title>   Checking your browser before accessing the site   </title ></head></html>",
     True),
    ("<html><head><Title>Please verify you are a human</Title></head></html>", True),
    ("<html><head><title>Dior Sauvage EDT 100ml</title></head><body>Just a moment...</body></html>",
     False),
    ("<html><head><title>B4 Shop</title></head><body><svg><title>Just a moment</title></svg></body>"
     "</html>", False),
    ("<html><head><titles>Just a moment</titles></head></html>", False),
    ("<html><head></head><body><h1>Access denied</h1></body></html>", False),
    ("", False),
]


@pytest.mark.parametrize("html,expected", _CHALLENGE_TITLE_CASES)
def test_challenge_title_verdicts_preserved(html, expected):
    """PIN (F2-2, behaviour preserved; kills a case-sensitive opener, an opener
    that refuses attributes and a scan of a later title): the FIRST <title> of
    the page decides, case-insensitive, attributes allowed, the close tag may
    carry whitespace; a body text or a later <svg><title> never decides."""
    is_challenge = _fn(ues, "_is_challenge_page")
    assert is_challenge(html) is expected, html
    assert is_challenge(None) is False


def test_challenge_title_without_a_close_tag_is_read_to_a_bound():
    """RED (F2-2, the ruled shape): with no close tag the first title's text is
    read up to a fixed bound, so an unclosed challenge title is still a
    challenge and an unclosed product title is not. At 96676f1f the regex read
    an unclosed title as no title at all (never a challenge)."""
    is_challenge = _fn(ues, "_is_challenge_page")
    assert is_challenge("<html><head><title>Just a moment...") is True
    assert is_challenge("<html><head><title>Dior Sauvage EDT 100ml") is False


# F2-4a: a pasted link carrying userinfo, a path token and a query token (all
# built at run time, no credential literal), driven through every unreadable
# outcome of the v2 fetch.
_HYG_SECRET = "pw" + "b4q7x"
_HYG_USER = "ub4" + "tok"
_HYG_PATHTOK = "pathtok" + "b4p"
_HYG_QTOK = "qtok" + "b4q"
_HYG_HOST = "www.b4hyg.example.test"
_HYG_TOKENS = (_HYG_SECRET, _HYG_USER, _HYG_PATHTOK, _HYG_QTOK)
_HYG_CASES = {"blocked_initial": "blocked", "blocked_hop": "blocked", "redirect_cap": "redirect_cap",
              "non_2xx": "http_403", "challenge": "challenge", "transport": "fetch_error"}


def _hyg_link(host=_HYG_HOST):
    return ("https://" + _HYG_USER + ":" + _HYG_SECRET + "@" + host + ":8443/products/"
            + _HYG_PATHTOK + "?ref=" + _HYG_QTOK)


def _install_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)

    def factory(*a, **kw):
        if kw.get("transport") is None:
            kw["transport"] = transport
        return _REAL_ASYNC_CLIENT(*a, **kw)

    monkeypatch.setattr(ues.httpx, "AsyncClient", factory)
    monkeypatch.setattr(ues, "_TRANSPORT", transport, raising=False)


def _hyg_handler(kind):
    def handler(request):
        if kind == "transport":
            raise httpx.ConnectError("b4 probe " + str(request.url), request=request)
        if kind == "blocked_hop":
            return httpx.Response(302, headers={
                "location": "http://169.254.169.254/latest/" + _HYG_PATHTOK + "?x=" + _HYG_QTOK})
        if kind == "redirect_cap":
            return httpx.Response(302, headers={"location": str(request.url) + "x"})
        if kind == "non_2xx":
            return httpx.Response(403, text=FORBIDDEN)
        if kind == "challenge":
            return httpx.Response(200, text=CHALLENGE)
        return httpx.Response(200, text=PDP2)
    return handler


@pytest.mark.parametrize("case", sorted(_HYG_CASES))
def test_v2_fetch_log_records_carry_the_host_only(monkeypatch, caplog, case):
    """PIN (F2-4a; kills P2 the blocked-redirect line printing the target, S3
    _log_fetch_failed printing the url, S5 _host_only returning the netloc, S8
    the blocked-initial line printing the url, S9 the redirect-cap line printing
    the url): every record of every logger (root at DEBUG) over the blocked
    initial url, the blocked hop, the redirect cap, a non-2xx, a challenge page
    and a transport error carries no userinfo, path token or query token, and
    the ONE '[URL-V2] fetch failed' record names the host only."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    _install_transport(monkeypatch, _hyg_handler(case))
    _ssrf(monkeypatch, h, deny=(("b4hyg",) if case == "blocked_initial" else ("169.254",)))
    _llm(monkeypatch, h, boom=True)
    caplog.set_level(logging.DEBUG)
    link = _hyg_link()
    result = _run(ues.extract_from_url(link, url_mode_v2=True))
    reason = _HYG_CASES[case]
    assert result == {"success": False, "code": "STORE_UNREADABLE", "reason": reason, "url": link,
                      "error": SU_MSG}, result
    messages = [rec.getMessage() for rec in caplog.records]
    leaks = [m for m in messages if any(tok in m for tok in _HYG_TOKENS)]
    assert leaks == [], leaks
    failed = [m for m in messages if m.startswith("[URL-V2] fetch failed ")]
    want_type = "ConnectError" if case == "transport" else "None"
    assert failed == [f"[URL-V2] fetch failed host={_HYG_HOST} reason={reason} type={want_type}"], failed
    assert h.llm_calls == []


def test_webpage_name_is_not_a_site_name(monkeypatch):
    """PIN (F2-4b, D2; kills P1 WebPage counted among the site names): a WebPage
    node names the page, not the site; a page whose only structured node is a
    WebPage named like its <title> is a valid PDP (the LLM fills the price) and
    is delivered with name == the title."""
    site_names_of = _fn(ues, "_v2_site_names")
    title = "B4 Probe Amber Oud 50ml"
    webpage = {"@context": "https://schema.org", "@type": "WebPage", "name": title}
    assert site_names_of([webpage], {}) == set()
    graph = {"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "name": "B4 Probe Store"},
        {"@type": ["WebPage", "ItemPage"], "name": title}]}
    assert site_names_of([graph], {}) == {"b4 probe store"}
    url = "https://www.b4amber.example.test/amber-oud-50ml"
    h = H()
    _serve(monkeypatch, h, {url: ok(_page(title, [webpage]))})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content=json.dumps({"is_product_page": True, "price": 12.5,
                                             "currency": "BHD"}))
    result = _run(ues.extract_from_url(url, url_mode_v2=True))
    assert result.get("success") is True, result
    assert result["product"]["name"] == title, result
    assert len(h.llm_calls) == 1, h.llm_calls


@pytest.mark.parametrize("v2", [False, True], ids=["base-path", "v2-path"])
def test_detected_retailer_label_is_a_supported_name_or_unknown(monkeypatch, caplog, v2):
    """PIN (F2-4c, D4; kills P3 the label taken from the raw netloc): the
    'Detected retailer' INFO label is a SUPPORTED_RETAILERS display name or
    'unknown', never the netloc (a pasted link with userinfo and a port), on
    the base path and on the v2 path; the host is the hostname only."""
    unknown = "https://" + _HYG_USER + ":" + _HYG_SECRET + "@www.b4label.example.test:8443/products/b4"
    known = "https://www.amazon.ae/b4-probe-parfum/dp/B0B4PROBE2"
    h = H()
    _serve(monkeypatch, h, default=ok(PDP2))
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h)
    caplog.set_level(logging.INFO)
    for url in (unknown, known):
        _run(ues.extract_from_url(url, url_mode_v2=True) if v2 else ues.extract_from_url(url))
    lines = [m for m in _messages(caplog, "app.services.url_extraction_service", logging.INFO)
             if m.startswith("Detected retailer")]
    assert lines == ["Detected retailer: unknown for host www.b4label.example.test",
                     "Detected retailer: Amazon UAE for host www.amazon.ae"], lines


def test_fetch_page_v2_redirect_bound_is_five_requests(monkeypatch):
    """PIN (F2-4d; kills S01 range(6) and its range(4) twin): the v2 fetch makes
    at most FIVE requests, as fetch_page does: four redirect hops are followed
    to a page served on the fifth request; a fifth redirect is refused as
    redirect_cap after exactly five requests (the sixth url never requested)."""
    fetch_v2 = _fn(ues, "_fetch_page_v2")
    chain = [f"https://x.example.test/hop/{i}" for i in range(8)]
    h = H()
    pages = {chain[i]: redirect(chain[i + 1]) for i in range(4)}
    pages[chain[4]] = ok("<html>fifth</html>")
    _serve(monkeypatch, h, pages)
    _ssrf(monkeypatch, h)
    res = _run(fetch_v2(chain[0]))
    assert (res["outcome"], res["status"], res["final_url"]) == ("ok", 200, chain[4]), res
    assert h.pages.fetched == chain[:5], h.pages.fetched
    h = H()
    _serve(monkeypatch, h, {chain[i]: redirect(chain[i + 1]) for i in range(7)},
           default=ok("<html>never</html>"))
    _ssrf(monkeypatch, h)
    res = _run(fetch_v2(chain[0]))
    assert (res["outcome"], res["text"], res["final_url"]) == ("redirect_cap", None, chain[5]), res
    assert h.pages.fetched == chain[:5], h.pages.fetched


@pytest.mark.parametrize("target,reason", [
    ("https://www.b4gc2.example.test/search?q=oud", "search"),
    ("https://www.b4gc2.example.test/cart", "cart"),
    ("https://www.b4gc2.example.test/checkout", "cart"),
    ("https://www.b4gc2.example.test/account/login", "account"),
    ("https://www.b4gc2.example.test/collections/oud", "category"),
], ids=["search", "cart", "checkout", "account", "category"])
def test_post_fetch_final_url_in_any_pregate_class_is_not_product_page(monkeypatch, target, reason):
    """PIN (F2-4e, GC-2; kills S02 the post-fetch check refusing 'homepage'
    only): a redirect ending on a search / cart / checkout / account / category
    route is NOT_PRODUCT_PAGE with that class as the reason (checkout is the
    cart class), with no LLM call."""
    start = "https://www.b4gc2.example.test/b4-probe-oud-100ml"
    h = H()
    _serve(monkeypatch, h, {start: redirect(target), target: ok(STOREFRONT)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h)
    result = _run(ues.extract_from_url(start, url_mode_v2=True))
    assert result == {"success": False, "code": "NOT_PRODUCT_PAGE", "reason": reason, "url": start,
                      "error": NPP_MSG}, result
    assert h.pages.fetched == [start, target], h.pages.fetched
    assert h.llm_calls == []


@pytest.mark.parametrize("statuses,reason", [((403, 404), "http_403"), ((404, 403), "http_4xx")],
                         ids=["403-then-404", "404-then-403"])
@pytest.mark.parametrize("verb", VERBS)
def test_pair_reason_is_the_first_failing_links(monkeypatch, client, verb, statuses, reason):
    """PIN (F2-4f, S03): both links fail with the SAME code and different
    reasons: field both, the reason of url1 (the first failing link carrying the
    chosen code), whichever order."""
    _full(monkeypatch, H(), pages={FX_PDP2: status(statuses[0]), FX_PDP: status(statuses[1])})
    r = _call(client, verb, FX_PDP2, FX_PDP)
    assert r.status_code == 400, r.json()
    assert _strip_rid(r.json()) == _refusal("STORE_UNREADABLE", SU_MSG, "both", reason)


_FIRST = _product("B4 First Oud", image=_IMG + "first.jpg", price="11")
_SECOND = _product("B4 Second Oud", image=_IMG + "second.jpg", price="22")


@pytest.mark.parametrize("blocks", [
    [_FIRST, _SECOND],
    [{"@context": "https://schema.org", "@graph": [_FIRST, _SECOND]}],
], ids=["two-blocks", "graph"])
def test_first_product_node_in_document_order_wins(monkeypatch, blocks):
    """PIN (F2-4f, S10): with two Product nodes the FIRST in document order
    gives the name, the price and the image."""
    url = "https://shop.example.test/p/two-nodes"
    h = H()
    _serve(monkeypatch, h, {url: ok(_page("B4 Oud Pair - Shop", blocks))})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h)
    result = _run(ues.extract_from_url(url, url_mode_v2=True))
    assert result.get("success") is True, result
    product = result["product"]
    assert (product["name"], product["price"]["amount"], product["image_url"]) == (
        "B4 First Oud", "11", _IMG + "first.jpg"), product
    assert h.llm_calls == []


# F2-5: no placeholder product name under ON (is_usable_title on the merged name).
_HAWAS_TITLE = "Rasasi Hawas Ice"


def test_nameless_node_without_price_falls_back_to_the_title(monkeypatch):
    """RED (F2-5, adversary minor 3): a Product node with no name and no price,
    a usable <title> / og:title, and an LLM answer whose name is null: the
    meta-title fallback is decided on the unusable node name (not on key
    presence) and the product is delivered with name == the title. At
    96676f1f: UNRESOLVED_PRODUCT null_name."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    page = _page(_HAWAS_TITLE, [_product(name=None, price=None)], og={"title": _HAWAS_TITLE})
    _serve(monkeypatch, h, {_HAWAS: ok(page)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content=json.dumps({"is_product_page": True, "name": None, "price": 10.5,
                                             "currency": "SAR"}))
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert result.get("success") is True, result
    assert (result["product"]["name"], result["product"]["full_name"]) == (_HAWAS_TITLE,
                                                                           _HAWAS_TITLE), result
    assert len(h.llm_calls) == 1, h.llm_calls


@pytest.mark.parametrize("llm_name", ["Unknown Product", "Unknown", "N/A", "Product", "Rasasi"])
def test_placeholder_llm_name_never_ships_flag_on(monkeypatch, llm_name):
    """RED (F2-5, adversary minor 4): a page with a usable title, no Product
    node and no price, whose LLM answer carries a placeholder name (or the
    site's own name, og:site_name): the usable title wins; the delivered name is
    never the placeholder. At 96676f1f: delivered with the placeholder name."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    page = _page(_HAWAS_TITLE, og={"title": _HAWAS_TITLE, "site_name": "Rasasi"})
    _serve(monkeypatch, h, {_HAWAS: ok(page)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content=json.dumps({"is_product_page": True, "name": llm_name,
                                             "price": 10.5, "currency": "SAR"}))
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert result.get("success") is True, result
    assert result["product"]["name"] == _HAWAS_TITLE, (llm_name, result["product"]["name"])
    assert result["product"]["full_name"] == _HAWAS_TITLE, result


def test_placeholder_llm_name_with_a_usable_llm_full_title(monkeypatch):
    """RED (F2-5): an empty <title>, a nameless priceless Product node and an LLM
    answer with name 'N/A' and a usable full_title: the delivered name is the
    full title, never 'N/A'. At 96676f1f: delivered with name 'N/A'."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    _serve(monkeypatch, h, {_HAWAS: ok(_page("", [_product(name=None, price=None)]))})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content=json.dumps({"is_product_page": True, "name": "N/A",
                                             "full_title": _HAWAS_TITLE, "price": 10.5}))
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert result.get("success") is True, result
    assert result["product"]["name"] == _HAWAS_TITLE, result


@pytest.mark.parametrize("meta", ["title_tag", "og_title"])
def test_nameless_node_with_price_uses_the_meta_title_without_the_llm(monkeypatch, meta):
    """RED (F2-5, adversary minor 3): a Product node with a price and no name and
    a usable <title> (or og:title alone), the LLM offline: the meta title is
    the name, delivered at $0 (no LLM call). At 96676f1f: the node's missing
    name skipped the meta fallback on key presence, the LLM was consulted and
    the page resolved to UNRESOLVED_PRODUCT null_name."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    node = _product(name=None, price="10.5")
    if meta == "title_tag":
        page = _page(_HAWAS_TITLE, [node])
    else:
        page = _page("", [node], og={"title": _HAWAS_TITLE})
    _serve(monkeypatch, h, {_HAWAS: ok(page)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, boom=True)
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert result.get("success") is True, result
    assert result["product"]["name"] == _HAWAS_TITLE, result
    assert h.llm_calls == [], h.llm_calls


@pytest.mark.parametrize("answer", [
    {"name": "Unknown Product"}, {"name": "Product"}, {"name": "N/A", "full_title": "Unknown"},
    {"name": "Rasasi", "full_title": "Rasasi"},
], ids=["unknown-product", "product", "na-unknown", "site-name"])
def test_no_usable_title_and_placeholder_name_is_unresolved(monkeypatch, answer):
    """PIN (F2-5 guard; kills a fix that delivers the merged name when no usable
    title exists, e.g. the null_name refusal dropped): an empty <title>, a
    nameless priceless Product node and an LLM answer whose name (and full
    title) is a placeholder or the site's own name: UNRESOLVED_PRODUCT /
    null_name, never a delivered placeholder."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    page = _page("", [_product(name=None, price=None)], og={"site_name": "Rasasi"})
    _serve(monkeypatch, h, {_HAWAS: ok(page)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content=json.dumps(dict(answer, is_product_page=True, price=10.5)))
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert result == _unresolved(_HAWAS, "null_name"), result
    assert "Unknown Product" not in json.dumps(result)


# ===========================================================================
# Fix round 3 (RULINGS_FIX3_B4): F3-1 the product-route-aware same-url key,
# F3-2 the OpenCart route marker is exactly product/product, F3-3 the first
# USABLE of title / full_title, F3-4 an allow-listed key needs a non-empty
# value, F3-5 pins for the round-2 re-verifier's surviving mutants (E1b, F5e,
# X1, X5). RED rows fail at 83daa8cb on an AssertionError only; PIN rows are
# green there and are proven by the mutant named in their docstring.
# ===========================================================================
_F3_OC = "https://www.b4oc3.example.test/index.php?route=product/product&product_id="
_F3_OC_ROOT = "https://www.b4oc3.example.test/?route=product/product&product_id="
_F3_PS = "https://www.b4ps3.example.test/index.php?controller=product&id_product="
_F3_WC = "https://www.b4wc3.example.test/?product="
_F3_OSC = "https://www.b4osc3.example.test/product_info.php?products_id="

F3_1_SAME_STORE_PAIRS = {
    "opencart-index": (_F3_OC + "1262", _F3_OC + "1263"),
    "opencart-root": (_F3_OC_ROOT + "1262", _F3_OC_ROOT + "1263"),
    "prestashop": (_F3_PS + "1", _F3_PS + "2"),
    "woocommerce": (_F3_WC + "b4-oud-a", _F3_WC + "b4-oud-b"),
    "oscommerce": (_F3_OSC + "1", _F3_OSC + "2"),
}


def _f3_pages(pair_id, url1, url2):
    names = {url1: "B4 Same Store One " + pair_id, url2: "B4 Same Store Two " + pair_id}
    pages = {u: ok(_page(n + " - Store", [_product(n, price="12.5")])) for u, n in names.items()}
    return names, pages


@pytest.mark.parametrize("pair_id", sorted(F3_1_SAME_STORE_PAIRS))
@pytest.mark.parametrize("verb", VERBS)
def test_same_store_query_routed_pair_is_not_same_url_flag_on(monkeypatch, client, verb, pair_id):
    """RED (F3-1, re-verifier MAJOR-R1): two DIFFERENT products of ONE
    query-routed store (OpenCart product_id on index.php and on the root
    ?route= form, PrestaShop id_product, WooCommerce ?product=, osCommerce
    products_id) are not the same url: the pre-gate lets them through, both are
    fetched and the pair DELIVERS (flag ON, full config, POST and GET). At
    83daa8cb the same-url key dropped the whole query: 400 NOT_PRODUCT_PAGE
    both / same_url with 0 fetches."""
    url1, url2 = F3_1_SAME_STORE_PAIRS[pair_id]
    names, pages = _f3_pages(pair_id, url1, url2)
    h = _full(monkeypatch, H(), pages=pages)
    r = _call(client, verb, url1, url2)
    assert r.status_code == 200, (r.status_code, r.json())
    body = r.json()
    assert body.get("success") is True, body
    assert [p["name"] for p in body["products"]] == [names[url1], names[url2]], body
    assert sorted(h.pages.fetched) == sorted([url1, url2]), h.pages.fetched
    assert h.events[:3] == ["ssrf", "ssrf", "pregate"], h.events
    uid = h.user["id"]
    assert h.ledger.consumes == [uid] and h.ledger.refunds == [], (h.ledger.consumes, h.ledger.refunds)


F3_1_STILL_SAME_URL = {
    "same-id-tracking": ("https://www.b4oc3.example.test/index.php?product_id=1&gclid=x",
                         "https://www.b4oc3.example.test/index.php?product_id=1&utm_source=y"),
    "aspnet-pid": ("https://www.b4asp3.example.test/ProductDetails.aspx?pid=1",
                   "https://www.b4asp3.example.test/ProductDetails.aspx?pid=2"),
    "identical": (_F3_OC + "1262", _F3_OC + "1262"),
}


@pytest.mark.parametrize("pair_id", sorted(F3_1_STILL_SAME_URL))
@pytest.mark.parametrize("verb", VERBS)
def test_same_url_still_refused_for_tracking_pid_and_identical_pairs(monkeypatch, client, verb,
                                                                     pair_id):
    """PIN (F3-1 guard; kills a key that keeps the WHOLE query, and an ASP.NET
    `pid` added to the allow-list): the same product_id with different tracking
    keys, an ASP.NET ?pid= pair (the stated limit: `pid` is generic) and two
    identical urls are still refused for $0 as NOT_PRODUCT_PAGE both / same_url,
    nothing reserved or fetched."""
    url1, url2 = F3_1_STILL_SAME_URL[pair_id]
    h = _full(monkeypatch, H(), default=ok(PDP))
    r = _call(client, verb, url1, url2)
    assert r.status_code == 400, (r.status_code, r.json())
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "both", "same_url")
    assert h.ledger.consumes == [] and h.pages.fetched == [], (h.ledger.consumes, h.pages.fetched)


_F3_KEY_BASE = "https://www.b4key3.example.test/index.php"

F3_1_KEY_DIFFERS = [
    ("?route=product/product&product_id=1262", "?route=product/product&product_id=1263"),
    ("?product=b4-oud-a", "?product=b4-oud-b"),
    ("?products_id=1", "?products_id=2"),
    ("?id_product=1&controller=product", "?id_product=2&controller=product"),
]

F3_1_KEY_EQUAL = [
    ("?product_id=1&gclid=x", "?product_id=1&utm_source=y"),
    ("?PRODUCT_ID=1", "?product_id=1"),
    ("?route=PRODUCT/PRODUCT&product_id=1", "?route=product/product&product_id=1"),
    ("?product_id=%31", "?product_id=1"),
    ("?product_id=1%20", "?product_id=1"),
    ("?product_id=1&route=product/product", "?route=product/product&product_id=1"),
    ("?product_id=&utm_source=x", ""),
    ("?pid=1", "?pid=2"),
    ("?route=product/category&product_id=5", "?product_id=5"),
]


@pytest.mark.parametrize("q1,q2", F3_1_KEY_DIFFERS,
                         ids=["opencart", "woocommerce", "oscommerce", "prestashop"])
def test_same_url_key_keeps_product_route_values(q1, q2):
    """RED (F3-1): the same-url key keeps the allow-listed product-route keys
    and their values (route=product/product, product_id, id_product, product,
    products_id), so two products of one store at one path have different
    keys. At 83daa8cb the whole query was dropped: equal keys."""
    norm = _fn(ues, "normalize_url_for_same_check")
    k1, k2 = norm(_F3_KEY_BASE + q1), norm(_F3_KEY_BASE + q2)
    assert k1 and k2, (k1, k2)
    assert k1 != k2, (q1, q2, k1)


@pytest.mark.parametrize("q1,q2", F3_1_KEY_EQUAL,
                         ids=["tracking-dropped", "key-case", "route-value-case", "percent-decoded",
                              "value-stripped", "order", "empty-value-dropped", "pid-not-a-key",
                              "listing-route-not-a-key"])
def test_same_url_key_equal_when_only_dropped_keys_differ(q1, q2):
    """PIN (F3-1 / F3-2 / F3-4 in the key; kills a whole-query key, case-
    sensitive keys or route value, undecoded or unstripped values, an order-
    sensitive key, an empty value kept, `pid` in the allow-list and a listing
    route kept in the key): two urls that differ only in dropped keys, in key
    case, in the route value's case, in percent-encoding, in surrounding
    whitespace or in key order have EQUAL keys."""
    norm = _fn(ues, "normalize_url_for_same_check")
    k1, k2 = norm(_F3_KEY_BASE + q1), norm(_F3_KEY_BASE + q2)
    assert k1, k1
    assert k1 == k2, (q1, q2, k1, k2)


_F3_LISTING_ROUTES = ["product/category&path=20", "product/search&search=oud", "product/compare",
                      "product/special", "product/manufacturer"]
F3_2_LISTING_ROWS = [p + "?route=" + r for p in ("/index.php", "/") for r in _F3_LISTING_ROUTES]


@pytest.mark.parametrize("path", F3_2_LISTING_ROWS)
def test_classify_url_path_listing_route_is_homepage(path):
    """RED (F3-2, re-verifier m2): an OpenCart LISTING route (product/category,
    product/search, product/compare, product/special, product/manufacturer) on
    a root or /index.php path is a homepage again (as at 96676f1f): only the
    exact product/product route is a product route. At 83daa8cb any route value
    starting product/ was exempt (None)."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) == "homepage", path


F3_2_EXEMPT_RED_ROWS = ["/index.php?route=PRODUCT/PRODUCT", "/?route=Product/Product"]
F3_2_EXEMPT_PIN_ROWS = ["/index.php?route=product/product&product_id=7",
                        "/index.php?route=PRODUCT/PRODUCT&product_id=7"]


@pytest.mark.parametrize("path", F3_2_EXEMPT_RED_ROWS)
def test_classify_url_path_product_product_route_is_case_insensitive(path):
    """RED (F3-2): the route VALUE product/product is matched case-insensitively
    (the key already was), so an upper-case product/product route alone is not
    the homepage. At 83daa8cb the value check was case-sensitive: 'homepage'."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) is None, path


@pytest.mark.parametrize("path", F3_2_EXEMPT_PIN_ROWS)
def test_classify_url_path_product_product_route_stays_exempt(path):
    """PIN (F3-2 guard, the ruling's two exempt rows; kills a route VETO, i.e. a
    route value overriding the product_id marker: the exact product/product
    value vetoing, or a value compared case-sensitively vetoing the upper-case
    row): route=product/product with a product_id, lower or upper case, stays
    exempt."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) is None, path


@pytest.mark.parametrize("route", _F3_LISTING_ROUTES)
@pytest.mark.parametrize("verb", VERBS)
def test_listing_route_link_refused_before_reserve(monkeypatch, client, verb, route):
    """RED (F3-2, the pre-gate site): an OpenCart listing-route link on
    /index.php is refused for $0 as NOT_PRODUCT_PAGE url1 / homepage, nothing
    reserved or fetched. At 83daa8cb it passed the pre-gate and was fetched."""
    url1 = "https://www.b4oc3.example.test/index.php?route=" + route
    h = _full(monkeypatch, H(), pages={FX_PDP: ok(PDP)}, default=ok(STOREFRONT))
    r = _call(client, verb, url1, FX_PDP)
    assert r.status_code == 400, (r.status_code, r.json())
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "url1", "homepage")
    assert h.ledger.consumes == [] and h.pages.fetched == [], (h.ledger.consumes, h.pages.fetched)


@pytest.mark.parametrize("route", _F3_LISTING_ROUTES)
def test_redirect_to_listing_route_is_homepage_post_fetch(monkeypatch, route):
    """RED (F3-2, the post-fetch site): a link redirecting to an OpenCart
    listing route on /index.php is NOT_PRODUCT_PAGE / homepage on its FINAL url,
    with no LLM call. At 83daa8cb the final url was exempt and the listing page
    was extracted."""
    start = "https://www.b4oc3.example.test/b4-probe-oud-100ml"
    target = "https://www.b4oc3.example.test/index.php?route=" + route
    h = H()
    _serve(monkeypatch, h, {start: redirect(target), target: ok(STOREFRONT)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h)
    result = _run(ues.extract_from_url(start, url_mode_v2=True))
    assert result == {"success": False, "code": "NOT_PRODUCT_PAGE", "reason": "homepage",
                      "url": start, "error": NPP_MSG}, result
    assert h.pages.fetched == [start, target], h.pages.fetched
    assert h.llm_calls == []


F3_4_EMPTY_VALUE_ROWS = ["/index.php?product_id=", "/?product=", "/index.php?id_product=",
                         "/?product=%20", "/?gclid=x&product_id="]


@pytest.mark.parametrize("path", F3_4_EMPTY_VALUE_ROWS)
def test_classify_url_path_empty_product_key_is_homepage(path):
    """RED (F3-4, re-verifier m6 / X4): an allow-listed key with an EMPTY (or
    whitespace-only) value is not a product-route marker: presence AND a
    non-empty value are required, so the link stays a homepage. At 83daa8cb key
    presence alone exempted it (None)."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) == "homepage", path


@pytest.mark.parametrize("path,expected", [("/index.php?product_id=5", None), ("/?pid=1", "homepage")],
                         ids=["product-id-5-exempt", "pid-root-homepage"])
def test_classify_url_path_non_empty_value_and_pid_limit(path, expected):
    """PIN (F3-4 / F3-1 guards; kills a fix that refuses a non-empty product_id
    and `pid` added to the allow-list): /index.php?product_id=5 stays exempt;
    a single ?pid= link on a root path stays a homepage (the stated limit)."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) == expected, path


@pytest.mark.parametrize("node_name", ["Unknown", "Product", "Unknown Product", "Rasasi"])
def test_placeholder_node_name_gives_way_to_a_usable_llm_full_title(monkeypatch, node_name):
    """RED (F3-3, re-verifier m3): a Product node NAMED with a placeholder (or
    the site's own name), an empty <title>, no price, and an LLM answer with a
    placeholder name and a usable full_title: the first USABLE of title /
    full_title is the title, so the product is delivered with name == full_name
    == the full title (never the placeholder). At 83daa8cb the first TRUTHY
    title (the placeholder) shadowed it: UNRESOLVED_PRODUCT null_name after
    the paid LLM call."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    page = _page("", [_product(name=node_name, price=None)], og={"site_name": "Rasasi"})
    _serve(monkeypatch, h, {_HAWAS: ok(page)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content=json.dumps({"is_product_page": True, "name": "N/A",
                                             "full_title": _HAWAS_TITLE, "price": 10.5}))
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert result.get("success") is True, result
    assert (result["product"]["name"], result["product"]["full_name"]) == (_HAWAS_TITLE,
                                                                           _HAWAS_TITLE), result
    assert len(h.llm_calls) == 1, h.llm_calls


def test_challenge_title_past_the_scan_window_is_not_read(monkeypatch):
    """PIN (F3-5, kills E1b the unbounded title window): the challenge check
    reads the first 64 KiB only. A challenge <title> that starts past byte
    65,536 (after a long HTML comment) is not a challenge page: the predicate
    says False and a page carrying a priced Product node is delivered; the same
    title placed just inside the window is a challenge (STORE_UNREADABLE)."""
    is_challenge = _fn(ues, "_is_challenge_page")
    title = "<title>Just a moment...</title>"
    node = '<script type="application/ld+json">' + json.dumps(
        _product("B4 Window Oud", price="10.5")) + "</script>"

    def page(pad):
        return "<html><head><!--" + "b" * pad + "-->" + title + node + "</head><body></body></html>"

    inside, outside = page(65000), page(65600)
    assert inside.find("</title>") + len("</title>") < 65536, inside.find("</title>")
    assert outside.find("<title>") > 65536, outside.find("<title>")
    assert is_challenge(inside) is True
    assert is_challenge(outside) is False
    h = H()
    _serve(monkeypatch, h, {FX_PDP2: ok(outside), FX_PDP: ok(inside)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, boom=True)
    delivered = _run(ues.extract_from_url(FX_PDP2, url_mode_v2=True))
    assert delivered.get("success") is True, delivered
    assert delivered["product"]["name"] == "B4 Window Oud", delivered
    refused = _run(ues.extract_from_url(FX_PDP, url_mode_v2=True))
    assert refused == {"success": False, "code": "STORE_UNREADABLE", "reason": "challenge",
                       "url": FX_PDP, "error": SU_MSG}, refused
    assert h.llm_calls == []


def test_node_named_like_the_site_takes_the_usable_meta_title(monkeypatch):
    """PIN (F3-5, kills F5e the node-name usability check ignoring the site
    names in extract_generic_data_v2): a priced Product node named exactly like
    og:site_name takes the usable <title>; delivered at $0 with no LLM call."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    page = _page(_HAWAS_TITLE, [_product(name="Rasasi", price="10.5")], og={"site_name": "Rasasi"})
    _serve(monkeypatch, h, {_HAWAS: ok(page)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, boom=True)
    result = _run(ues.extract_from_url(_HAWAS, url_mode_v2=True))
    assert result.get("success") is True, result
    assert (result["product"]["name"], result["product"]["full_name"]) == (_HAWAS_TITLE,
                                                                           _HAWAS_TITLE), result
    assert h.llm_calls == [], h.llm_calls


def test_transport_error_line_carries_no_exception_info(monkeypatch, caplog):
    """PIN (F3-5, kills X1 the transport ERROR line gaining exc_info=True): the
    ONE '[URL-V2] fetch failed' record of a transport error is at ERROR with the
    exact host-only message, and it (like every other record of the run) carries
    no exception info and no stack info (a traceback could carry the pasted
    url)."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    _serve(monkeypatch, h, {FX_PDP2: httpx.ConnectTimeout})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, boom=True)
    caplog.set_level(logging.DEBUG)
    result = _run(ues.extract_from_url(FX_PDP2, url_mode_v2=True))
    assert result == {"success": False, "code": "STORE_UNREADABLE", "reason": "fetch_error",
                      "url": FX_PDP2, "error": SU_MSG}, result
    failed = [rec for rec in caplog.records if rec.getMessage().startswith("[URL-V2] fetch failed ")]
    assert [(rec.levelno, rec.getMessage()) for rec in failed] == [
        (logging.ERROR, "[URL-V2] fetch failed host=www.fragrancex.com reason=fetch_error "
                        "type=ConnectTimeout")], [(r.levelno, r.getMessage()) for r in failed]
    assert failed[0].exc_info is None and failed[0].exc_text is None, failed[0].exc_info
    assert failed[0].stack_info is None
    assert [rec.getMessage() for rec in caplog.records if rec.exc_info] == []


def test_non_2xx_401_is_the_4xx_class(monkeypatch):
    """PIN (F3-5, kills X5 a 401 reported as http_403): an upstream 401 is
    STORE_UNREADABLE with the 4xx-class reason http_4xx (only a 403 is
    http_403; the reason vocabulary has no per-status 401 word), no LLM call."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    h = H()
    _serve(monkeypatch, h, {FX_PDP2: status(401)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h)
    result = _run(ues.extract_from_url(FX_PDP2, url_mode_v2=True))
    assert result == {"success": False, "code": "STORE_UNREADABLE", "reason": "http_4xx",
                      "url": FX_PDP2, "error": SU_MSG}, result
    assert h.llm_calls == []


# ===========================================================================
# Fix round 4 (RULINGS_FIX4_B4): F4-1 the bounded pre-gate (a link over 2,048
# characters is refused url_too_long BEFORE any parse; each link's query is
# parsed ONCE per request), F4-3 products_id joins the homepage-class
# allow-list (osCommerce / Zen Cart), F4-4 the meta title is the first USABLE
# of og:title and the <title> tag, F4-5 the extract_with_ai ERROR line carries
# the exception TYPE only. RED rows fail at 0aac07f1 on an AssertionError only;
# PIN rows are green there and are proven by the mutant named in their
# docstring. No assertion message ever carries a multi-megabyte link.
# ===========================================================================
_F4_HOST = "https://www.b4long4.example.test"


def _f4_link(n, prefix="/products/b4-long-"):
    """A path-routed product link of exactly n characters (url-safe characters
    only, so the transport sees it byte for byte)."""
    head = _F4_HOST + prefix
    assert n > len(head) + 1, n
    return head + "a" * (n - len(head))


def _f4_big_query_link(product_id, size=5 * 1024 * 1024):
    """A ~5 MB /index.php link: a product-route marker, then ~1.3 M query pairs
    (the engineering adversary's MAJOR-E2 probe shape)."""
    head = _F4_HOST + "/index.php?product_id=" + str(product_id) + "&"
    return head + "a=b&" * ((size - len(head)) // 4)


def _record_parse(monkeypatch):
    """Records the query string of every parse_qs call the service makes (the
    one query parse of the pre-gate helpers)."""
    calls = []
    real = ues.parse_qs

    def rec(query, *a, **kw):
        calls.append(query)
        return real(query, *a, **kw)
    monkeypatch.setattr(ues, "parse_qs", rec)
    return calls


F4_1_LONG_CASES = {
    "url1": ((2049, "/products/b4-one-"), None, "url1"),
    "url2": (None, (2049, "/products/b4-two-"), "url2"),
    "both": ((2049, "/products/b4-one-"), (2050, "/products/b4-two-"), "both"),
    "homepage-and-long": ("home", (2049, "/products/b4-two-"), "url2"),
}


@pytest.mark.parametrize("case", sorted(F4_1_LONG_CASES))
@pytest.mark.parametrize("verb", VERBS)
def test_link_over_2048_chars_refused_before_any_parse(monkeypatch, client, verb, case):
    """RED (F4-1, engineering MAJOR-E2): a pasted link longer than 2,048
    characters (the client's validateUrl bound) is refused for $0 as
    NOT_PRODUCT_PAGE <field> / url_too_long BEFORE any query parse (it wins over
    the other link's homepage class): nothing reserved, nothing fetched, no
    parse_qs call, no row. At 0aac07f1 there was no bound: the long links were
    parsed, fetched and delivered (and the homepage case refused url1)."""
    spec1, spec2, field = F4_1_LONG_CASES[case]
    url1 = FX_HOME if spec1 == "home" else (_f4_link(*spec1) if spec1 else FX_PDP)
    url2 = _f4_link(*spec2) if spec2 else FX_PDP2
    pages = {FX_PDP: ok(PDP), FX_PDP2: ok(PDP2), FX_HOME: ok(STOREFRONT)}
    for i, u in enumerate((url1, url2)):
        if len(u) > 2048:
            pages[u] = ok(_page("B4 Long Oud - Store", [_product("B4 Long Oud " + str(i), price="9.5")]))
    h = _full(monkeypatch, H(), pages=pages)
    parses = _record_parse(monkeypatch)
    r = _call(client, verb, url1, url2)
    assert r.status_code == 400, (r.status_code, r.json())
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, field, "url_too_long")
    assert h.events == ["ssrf", "ssrf", "pregate"], h.events
    assert h.ledger.consumes == [] and h.pages.fetched == [], (h.ledger.consumes, len(h.pages.fetched))
    n_parses = len(parses)
    assert n_parses == 0, n_parses
    assert h.ledger.rows == [] and h.ledger.labels == [], (h.ledger.rows, h.ledger.labels)


@pytest.mark.parametrize("side", ["url1", "url2", "both"])
@pytest.mark.parametrize("verb", VERBS)
def test_link_of_exactly_2048_chars_proceeds(monkeypatch, client, verb, side):
    """PIN (F4-1 boundary; kills a bound at 2,047 or a '>=' comparison): a
    link of exactly 2,048 characters (the client's own maximum) passes the
    pre-gate, is fetched and the pair delivers (flag ON, full config)."""
    one, two = _f4_link(2048, "/products/b4-one-"), _f4_link(2048, "/products/b4-two-")
    assert len(one) == len(two) == 2048
    url1 = one if side in ("url1", "both") else FX_PDP
    url2 = two if side in ("url2", "both") else FX_PDP2
    names = {one: "B4 Boundary Oud One", two: "B4 Boundary Oud Two",
             FX_PDP: None, FX_PDP2: "Obsession Perfume"}
    pages = {FX_PDP: ok(PDP), FX_PDP2: ok(PDP2)}
    for u in (one, two):
        pages[u] = ok(_page(names[u] + " - Store", [_product(names[u], price="9.5")]))
    h = _full(monkeypatch, H(), pages=pages)
    r = _call(client, verb, url1, url2)
    assert r.status_code == 200, (r.status_code, r.json())
    body = r.json()
    assert body.get("success") is True, body
    for i, u in enumerate((url1, url2)):
        if names[u] is not None:
            assert body["products"][i]["name"] == names[u], body["products"][i].get("name")
    assert sorted(h.pages.fetched) == sorted([url1, url2]), [len(u) for u in h.pages.fetched]
    assert h.ledger.consumes == [h.user["id"]] and h.ledger.refunds == []


def test_two_5mb_links_refused_fast_with_no_parse(monkeypatch, client):
    """RED (F4-1, engineering MAJOR-E2: 3.55 s on the event loop at 0aac07f1):
    two ~5 MB /index.php links, each with a product-route marker and ~1.3 M
    query pairs, are refused for $0 as NOT_PRODUCT_PAGE both / url_too_long; the
    pre-gate decides in under 50 ms of wall time with NO parse_qs call; nothing
    reserved or fetched; the whole request stays under a lenient 1 s (POST only:
    a GET cannot carry 5 MB). At 0aac07f1 each query was parsed twice, then
    the links reached the fetch (400 STORE_UNREADABLE after ~3.5 s)."""
    url1, url2 = _f4_big_query_link(1), _f4_big_query_link(2)
    h = _full(monkeypatch, H(), default=ok(PDP), spy=False)
    timings = []
    real_gate = url_routes._url_pre_gate

    def timed(*a, **kw):
        h.events.append("pregate")
        t0 = time.perf_counter()
        try:
            return real_gate(*a, **kw)
        finally:
            timings.append(time.perf_counter() - t0)
    monkeypatch.setattr(url_routes, "_url_pre_gate", timed)
    parses = _record_parse(monkeypatch)
    t0 = time.perf_counter()
    r = _call(client, "POST", url1, url2)
    wall = time.perf_counter() - t0
    body = _strip_rid(r.json())
    assert (r.status_code, body) == (400, _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "both",
                                                     "url_too_long")), (r.status_code, body)
    n_parses, n_fetched = len(parses), len(h.pages.fetched)
    assert n_parses == 0, n_parses
    assert len(timings) == 1 and timings[0] < 0.05, timings
    assert h.ledger.consumes == [] and n_fetched == 0, (h.ledger.consumes, n_fetched)
    assert wall < 1.0, wall


F4_1_SAME_ID_TRACKING = ("https://www.b4parse4.example.test/index.php?product_id=7&gclid=b4",
                         "https://www.b4parse4.example.test/index.php?product_id=7&utm_source=b4")


@pytest.mark.parametrize("verb", VERBS)
def test_pregate_parses_each_query_once_per_request(monkeypatch, client, verb):
    """RED (F4-1): the pre-gate parses each link's query ONCE per request and
    reuses the parsed pairs for the homepage class and the same-url key: a
    same-store /index.php pair with one product_id and different tracking keys
    (refused same_url at $0) costs exactly two parse_qs calls, one per link.
    At 0aac07f1 each query was parsed twice (classify_url_path, then the
    same-url key): four calls."""
    h = _full(monkeypatch, H(), default=ok(PDP))
    parses = _record_parse(monkeypatch)
    r = _call(client, verb, *F4_1_SAME_ID_TRACKING)
    assert r.status_code == 400, (r.status_code, r.json())
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "both", "same_url")
    assert sorted(parses) == ["product_id=7&gclid=b4", "product_id=7&utm_source=b4"], parses
    assert h.ledger.consumes == [] and h.pages.fetched == []


def test_pregate_pass_path_parses_each_query_once(monkeypatch):
    """RED (F4-1, the pass path): for a same-store OpenCart pair the pre-gate
    lets through (product_id 1262 vs 1263 on /index.php), _url_pre_gate makes
    exactly one parse_qs call per link. At 0aac07f1: two per link."""
    pre_gate = _fn(url_routes, "_url_pre_gate")
    parses = _record_parse(monkeypatch)
    assert pre_gate(_F3_OC + "1262", _F3_OC + "1263") is None
    assert sorted(parses) == ["route=product/product&product_id=1262",
                              "route=product/product&product_id=1263"], parses


@pytest.mark.parametrize("value", [None, "false"], ids=["unset", "false"])
def test_flag_off_5mb_links_are_base_behaviour(monkeypatch, client, value):
    """PIN (F4-1 flag-OFF identity, full configuration, a RAISING pre-gate
    stand-in; kills a length bound or a parse outside the flag): two ~5 MB
    links with the flag OFF take the base path exactly as at 0aac07f1: no
    pre-gate, no parse_qs call, the credit reserved then refunded once, nothing
    fetched (httpx refuses a url over 65,536 characters), the base codeless 400
    'Could not extract both products' and its one failure row."""
    url1, url2 = _f4_big_query_link(1), _f4_big_query_link(2)
    h = _full(monkeypatch, H(), flag=value, default=ok(PDP), spy=False)
    _raising_pregate(monkeypatch, h)
    parses = _record_parse(monkeypatch)
    r = _call(client, "POST", url1, url2)
    body = _strip_rid(r.json())
    assert (r.status_code, body) == (400, BASE_FEW), (r.status_code, body)
    n_parses, n_fetched = len(parses), len(h.pages.fetched)
    assert n_parses == 0 and n_fetched == 0, (n_parses, n_fetched)
    assert h.pregate_raised == []
    _assert_non_delivery(h)
    _failure_row(h, "Could not extract both products")


_F4_OSC_ROOT = "https://www.b4osc4.example.test/?products_id="
_F4_OSC_INDEX = "https://www.b4osc4.example.test/index.php?products_id="
_F4_ZEN = "https://www.b4zen4.example.test/index.php?main_page=product_info&products_id="

F4_3_PRODUCTS_ID_ROWS = ["/?products_id=12", "/index.php?products_id=12",
                         "/index.php?main_page=product_info&products_id=12",
                         "/index.php?PRODUCTS_ID=12"]


@pytest.mark.parametrize("path", F4_3_PRODUCTS_ID_ROWS)
def test_classify_url_path_products_id_is_a_product_route(path):
    """RED (F4-3, engineering e-m5 / addendum A3-1): a non-empty products_id
    (osCommerce, and Zen Cart's default main_page=product_info&products_id=N
    PDP url; key case-insensitive) on a root or /index.* path is a product-route
    marker, so the link is not the homepage. At 0aac07f1 products_id sat in the
    same-url key only: 'homepage'."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) is None, path


@pytest.mark.parametrize("path", ["/?products_id=", "/index.php?products_id=%20",
                                  "/index.php?main_page=product_info&products_id="])
def test_classify_url_path_empty_products_id_is_homepage(path):
    """PIN (F4-3 with F3-4; kills an empty products_id counted as a marker): an
    EMPTY (or whitespace-only) products_id is not a product route, so the link
    stays a homepage (as at 0aac07f1)."""
    classify = _fn(ues, "classify_url_path")
    assert classify("https://shop.example.test" + path) == "homepage", path


F4_3_PAIRS = {
    "oscommerce-root": (_F4_OSC_ROOT + "12", _F4_OSC_ROOT + "13"),
    "oscommerce-index": (_F4_OSC_INDEX + "12", _F4_OSC_INDEX + "13"),
    "zencart": (_F4_ZEN + "12", _F4_ZEN + "13"),
}


@pytest.mark.parametrize("pair_id", sorted(F4_3_PAIRS))
@pytest.mark.parametrize("verb", VERBS)
def test_products_id_pair_delivers_flag_on(monkeypatch, client, verb, pair_id):
    """RED (F4-3, the pre-gate site; the correctness adversary's Zen Cart
    extension): two products of one osCommerce (root or /index.php) or Zen Cart
    store addressed by products_id pass the pre-gate, are fetched and DELIVER
    (flag ON, full config, POST and GET). At 0aac07f1: 400 NOT_PRODUCT_PAGE
    both / homepage with 0 fetches."""
    url1, url2 = F4_3_PAIRS[pair_id]
    names, pages = _f3_pages(pair_id, url1, url2)
    h = _full(monkeypatch, H(), pages=pages)
    r = _call(client, verb, url1, url2)
    assert r.status_code == 200, (r.status_code, r.json())
    body = r.json()
    assert body.get("success") is True, body
    assert [p["name"] for p in body["products"]] == [names[url1], names[url2]], body
    assert sorted(h.pages.fetched) == sorted([url1, url2]), h.pages.fetched
    uid = h.user["id"]
    assert h.ledger.consumes == [uid] and h.ledger.refunds == [], (h.ledger.consumes, h.ledger.refunds)


@pytest.mark.parametrize("verb", VERBS)
def test_redirect_to_zen_cart_pdp_is_not_refused_post_fetch(monkeypatch, client, verb):
    """RED (F4-3, the post-fetch site): a link redirecting to a Zen Cart PDP
    (/index.php?main_page=product_info&products_id=12) is not refused on its
    FINAL url; the pair delivers. At 0aac07f1: 400 NOT_PRODUCT_PAGE url1 /
    homepage after the fetch."""
    start = "https://www.b4zen4.example.test/b4-zen-oud-100ml"
    target = _F4_ZEN + "12"
    name = "B4 Zen Oud 100ml"
    pages = {start: redirect(target, 301), target: ok(_page(name + " - Store", [_product(name, price="12.5")])),
             FX_PDP: ok(PDP)}
    h = _full(monkeypatch, H(), pages=pages)
    r = _call(client, verb, start, FX_PDP)
    assert r.status_code == 200, (r.status_code, r.json())
    body = r.json()
    assert body.get("success") is True, body
    assert body["products"][0]["name"] == name, body
    assert sorted(h.pages.fetched) == sorted([start, target, FX_PDP]), h.pages.fetched


_F4_TITLE = "Rasasi Hawas Ice 100ml | Rasasi Store"
_F4_SITE = "Rasasi Store"
_F4_NODELESS = "https://store.b4rasasi4.example.test/en/hawas-ice-100ml"
_F4_NODE = "https://store.b4rasasi4.example.test/en/hawas-ice-100ml-node"


@pytest.mark.parametrize("og_title", [_F4_SITE, "Product"],
                         ids=["og-title-is-site-name", "og-title-placeholder"])
@pytest.mark.parametrize("verb", VERBS)
def test_nodeless_page_takes_a_usable_title_tag_over_an_unusable_og_title(monkeypatch, client,
                                                                          verb, og_title):
    """RED (F4-4, correctness c-m1): a node-less page whose og:title is
    unusable (equal to og:site_name, or a placeholder) and whose <title> tag is
    usable: the meta title is the first USABLE of og:title, <title>, so the page
    is not refused no_product_node; the price comes from the paid LLM rung (one
    call) and the pair DELIVERS with that <title> as the product name (real
    route, flag ON, full config). At 0aac07f1: 400 UNRESOLVED_PRODUCT url1 /
    no_product_node with 0 LLM calls."""
    page = _page(_F4_TITLE, og={"title": og_title, "site_name": _F4_SITE})
    h = _full(monkeypatch, H(), pages={_F4_NODELESS: ok(page), FX_PDP2: ok(PDP2)},
              llm_content=json.dumps({"is_product_page": True, "price": 10.5}))
    r = _call(client, verb, _F4_NODELESS, FX_PDP2)
    assert r.status_code == 200, (r.status_code, r.json())
    body = r.json()
    assert body.get("success") is True, body
    assert (body["products"][0]["name"], body["products"][0]["full_name"]) == (_F4_TITLE,
                                                                               _F4_TITLE), body
    assert len(h.llm_calls) == 1, h.llm_calls


@pytest.mark.parametrize("verb", VERBS)
def test_site_named_priced_node_takes_the_usable_title_tag(monkeypatch, client, verb):
    """RED (F4-4, correctness c-m1 case 3): a PRICED Product node named like the
    site, og:title equal to og:site_name and a usable <title> tag: the F2-5
    fallback reads the first USABLE meta title (the <title>), so the product is
    delivered under that name with no LLM call (real route, flag ON, full
    config). At 0aac07f1 the unusable og:title shadowed it: 400
    UNRESOLVED_PRODUCT url1 / null_name."""
    page = _page(_F4_TITLE, [_product(name=_F4_SITE, price="10.5")],
                 og={"title": _F4_SITE, "site_name": _F4_SITE})
    h = _full(monkeypatch, H(), pages={_F4_NODE: ok(page), FX_PDP2: ok(PDP2)}, llm_boom=True)
    r = _call(client, verb, _F4_NODE, FX_PDP2)
    assert r.status_code == 200, (r.status_code, r.json())
    body = r.json()
    assert body.get("success") is True, body
    assert (body["products"][0]["name"], body["products"][0]["full_name"]) == (_F4_TITLE,
                                                                               _F4_TITLE), body
    assert h.llm_calls == [], h.llm_calls


def test_usable_og_title_keeps_precedence_over_the_title_tag(monkeypatch):
    """PIN (F4-4 guard; kills the <title> tag read BEFORE og:title): when both
    are usable, og:title stays the meta title (first in order, as at 0aac07f1),
    so a node-less page is delivered under its og:title."""
    _assert_kwarg(ues.extract_from_url, "url_mode_v2")
    og_name = "B4 OG Oud 50ml"
    h = H()
    page = _page("B4 Title Tag Oud 50ml - Store", og={"title": og_name, "site_name": _F4_SITE})
    _serve(monkeypatch, h, {_F4_NODELESS: ok(page)})
    _ssrf(monkeypatch, h)
    _llm(monkeypatch, h, content=json.dumps({"is_product_page": True, "price": 10.5}))
    result = _run(ues.extract_from_url(_F4_NODELESS, url_mode_v2=True))
    assert result.get("success") is True, result
    assert (result["product"]["name"], result["product"]["full_name"]) == (og_name, og_name), result


@pytest.mark.parametrize("v2", [False, True], ids=["base", "v2"])
def test_extract_with_ai_error_line_carries_the_type_only(monkeypatch, caplog, v2):
    """RED (F4-5, engineering e-m6; unflagged, log-only, R-A1 b; the ruling
    calls it a pin, but at 0aac07f1 the f-string logged the exception text, so
    it fails there): when the extraction LLM call raises, the ONE 'AI extraction
    error' ERROR record carries the exception TYPE only, never its text (a
    run-time sentinel in the raised message reaches no record), on the base and
    the v2 path; the return value is unchanged ({"error": str(e)})."""
    sentinel = "b4sent" + uuid.uuid4().hex[:8]

    def boom(*_a, **_k):
        raise ValueError("upstream said " + sentinel)
    monkeypatch.setattr(ues, "get_client", boom)
    caplog.set_level(logging.DEBUG)
    result = _run(ues.extract_with_ai(FX_PDP, PDP2, {"key": "generic", "name": "Example"},
                                      url_mode_v2=v2))
    assert result == {"error": "upstream said " + sentinel}, result
    errors = [rec for rec in caplog.records
              if rec.name == "app.services.url_extraction_service" and rec.levelno == logging.ERROR]
    assert [rec.getMessage() for rec in errors] == ["AI extraction error: ValueError"], [
        rec.getMessage() for rec in errors]
    assert errors[0].exc_info is None, errors[0].exc_info
    assert [rec.name for rec in caplog.records if sentinel in rec.getMessage()] == []


# ===========================================================================
# Rebase round (after RULINGS_FIX4_B4; the both-lens re-verifier's minors m-1
# and m-2): test-only rows. m-1 pins the flag-OFF GET route for a link longer
# than the pre-gate's 2,048-character bound: the base path, never a length
# refusal (kills mutant B5, a length 400 in compare_urls_get that fires only
# with the flag OFF). m-2 pins "each link's query is parsed ONCE per request"
# for links whose product-route pairs are EMPTY (kills mutant V3,
# classify_url_path re-parsing the query when url_pre_gate_view passes []).
# ===========================================================================
_RB_LONG_HEAD = FX_PDP + "?b4ref=offlong&b4pad="
# The flag-OFF GET delivery of _rb_long_pdp() vs FX_PDP2, measured at origin/main
# 95cf6f86 (no B4) through the offline fetch stub with the full configuration
# (flag unset and 'false', two runs each, identical): status 200, these top-level
# keys, and the sha256 of the canonical body JSON (request_id stripped;
# sort_keys, ASCII, separators (",", ":")).
_RB_M1_BASE_KEYS = ["category_used", "comparison", "key_differences", "products",
                    "recommendation", "source_urls", "success", "winner_index"]
_RB_M1_BASE_BODY_SHA = "06bd08d895ee6bce653365cab11dbd23320336744437f4d5edcbb7cef1593b82"


def _rb_long_pdp(n=3000):
    """A valid https product path padded with a long query to exactly n characters."""
    assert n > len(_RB_LONG_HEAD), n
    return _RB_LONG_HEAD + "a" * (n - len(_RB_LONG_HEAD))


@pytest.mark.parametrize("value", [None, "false"], ids=["unset", "false"])
def test_flag_off_get_over_long_url1_is_base_behaviour(monkeypatch, client, value):
    """PIN (m-1 of the round-4 re-verifier; kills mutant B5, a length 400 in
    compare_urls_get that fires only when the flag is OFF; green at origin/main
    95cf6f86 and at the rebased HEAD): flag unset or 'false', the FULL
    configuration and a RAISING pre-gate stand-in; GET /api/v1/url/compare with
    a 3,000-character url1 (a product path padded with a long query, over the
    2,048 bound) takes the base path exactly as at origin/main: never refused on
    length, both links fetched, the base 200 delivery (its keys and canonical
    body digest recorded at base), one consume, no refund, the lifetime bump,
    the history row and the one success row."""
    url1 = _rb_long_pdp()
    assert len(url1) == 3000
    h = _full(monkeypatch, H(), flag=value, pages={url1: ok(PDP), FX_PDP2: ok(PDP2)}, spy=False)
    _raising_pregate(monkeypatch, h)
    r = _call(client, "GET", url1, FX_PDP2)
    body = _strip_rid(r.json())
    assert r.status_code == 200, (r.status_code, body.get("code"), body.get("reason"))
    assert body.get("success") is True and "code" not in body, sorted(body)
    assert sorted(body) == _RB_M1_BASE_KEYS, sorted(body)
    canon = json.dumps(body, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(canon.encode("ascii")).hexdigest()
    assert digest == _RB_M1_BASE_BODY_SHA, digest
    assert h.pregate_raised == []
    assert h.events == ["ssrf", "ssrf", "ssrf", "ssrf"], h.events
    n_fetched = len(h.pages.fetched)
    assert sorted(h.pages.fetched) == sorted([url1, FX_PDP2]), n_fetched
    led, uid = h.ledger, h.user["id"]
    assert (led.consumes, led.refunds, led.lifetime, led.history) == ([uid], [], [uid], ["url"])
    assert led.labels == ["save_comparison.url", "record_lifetime.url",
                          "log_search.url.success"], led.labels
    rows = [(row.get("success"), row.get("input_type"), row.get("products_found"))
            for row in led.rows]
    assert rows == [(True, "url", ["Christian Dior Sauvage Cologne",
                                   "Calvin Klein Obsession Perfume"])], rows
    assert (len(h.gen_calls), len(h.llm_calls)) == (1, 0)


_RB_TRK_HOST = "https://www.b4trk5.example.test"
_RB_TRK_ONE = _RB_TRK_HOST + "/products/b4-track-one?utm_source=x&gclid=y"
_RB_TRK_TWO = _RB_TRK_HOST + "/products/b4-track-two?gclid=y2&utm_source=x"
_RB_TRK_ROOT = _RB_TRK_HOST + "/?utm_source=x&gclid=y"
_RB_TRK_QUERIES = sorted(["utm_source=x&gclid=y", "gclid=y2&utm_source=x"])


def _record_route_pairs(monkeypatch):
    """Records the query of every _product_route_pairs call (the one query parse
    of the pre-gate helpers; _query_names_a_product_route goes through it too)."""
    real = _fn(ues, "_product_route_pairs")
    calls = []

    def rec(query, *a, **kw):
        calls.append(query)
        return real(query, *a, **kw)
    monkeypatch.setattr(ues, "_product_route_pairs", rec)
    return calls


def test_tracking_only_product_links_parse_once_and_reach_the_fetch(monkeypatch, client):
    """PIN (m-2, the gate's shape; green at the rebased HEAD; at origin/main
    95cf6f86, which has no B4, it fails on an AssertionError only:
    _product_route_pairs is missing): flag ON, full configuration, real POST
    route: two product-path links of one store whose queries carry ONLY
    tracking keys (no product-route key) cost exactly ONE _product_route_pairs
    call per link over the whole request (the view's parse; the same-url key
    reuses the EMPTY pairs; the post-fetch check reads the path only), pass the
    pre-gate, reach the fetch stub and deliver. A product path never reaches the
    homepage exemption's query read, so this row alone does not kill V3
    (measured in the rebase report); the root row below does."""
    names = {_RB_TRK_ONE: "B4 Track Oud One", _RB_TRK_TWO: "B4 Track Oud Two"}
    pages = {u: ok(_page(n + " - Store", [_product(n, price="9.5")])) for u, n in names.items()}
    h = _full(monkeypatch, H(), pages=pages)
    calls = _record_route_pairs(monkeypatch)
    r = _call(client, "POST", _RB_TRK_ONE, _RB_TRK_TWO)
    assert r.status_code == 200, (r.status_code, r.json())
    body = r.json()
    assert body.get("success") is True, body
    assert [p.get("name") for p in body["products"]] == [names[_RB_TRK_ONE], names[_RB_TRK_TWO]]
    assert sorted(calls) == _RB_TRK_QUERIES, calls
    assert h.events[:3] == ["ssrf", "ssrf", "pregate"], h.events
    assert sorted(h.pages.fetched) == sorted([_RB_TRK_ONE, _RB_TRK_TWO]), h.pages.fetched
    assert h.ledger.consumes == [h.user["id"]] and h.ledger.refunds == []


def test_tracking_only_root_link_parses_its_query_once(monkeypatch, client):
    """PIN (m-2; kills mutant V3; green at the rebased HEAD; at origin/main
    95cf6f86 it fails on an AssertionError only): flag ON, full configuration,
    real POST route: a storefront-root link whose query carries ONLY tracking
    keys, beside a tracking-only product link, is refused NOT_PRODUCT_PAGE url1
    / homepage at $0 (nothing reserved, fetched or logged) with exactly ONE
    _product_route_pairs call per link: the homepage exemption reuses the
    view's EMPTY pairs instead of re-parsing the query (V3 makes it three)."""
    h = _full(monkeypatch, H(), default=ok(PDP))
    calls = _record_route_pairs(monkeypatch)
    r = _call(client, "POST", _RB_TRK_ROOT, _RB_TRK_TWO)
    assert r.status_code == 400, (r.status_code, r.json())
    assert _strip_rid(r.json()) == _refusal("NOT_PRODUCT_PAGE", NPP_MSG, "url1", "homepage")
    assert sorted(calls) == _RB_TRK_QUERIES, calls
    assert h.events == ["ssrf", "ssrf", "pregate"], h.events
    assert (h.ledger.consumes, h.pages.fetched, h.ledger.rows) == ([], [], [])
