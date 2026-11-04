"""S81-10b LINKS-GATE: the RED + PIN rows (ENABLE_FRAGRANCE_ONLY_GATE, the S81-10 flag, default OFF).

Contract: the unit spec (.qa-s80/S81-10b_UNIT_SPEC.md of the unit worktree) as amended by its
adversarial review (C1-C15) and RULINGS_S81_10B (R-S10B-1..R-S10B-18; the rulings win, then the
review corrections, then the spec). Base c6fb6533. Every RED row fails at the base on an
AssertionError only (missing parameters are read through inspect.signature and asserted FIRST);
every PIN row is green at the base and runs with the FULL configuration (spec 2.10: the flag OFF
or the row's state, REFUSAL_DAILY_BUDGET set, a run-time lexicon, the device header bound with a
synthetic pepper, metering ON, the refusal counters seeded ABOVE the budget, the A2b armed to
answer a non-fragrance) plus call recorders and, where the row says so, RAISING recorders on every
public category_gate function but the flag reader (ruling B1).

Decision semantics pinned (rulings over spec):
  * the budget (pre-consume, url_routes): after the free SSRF / B4 pre-gate 400s and BEFORE the
    S81-06 consent 503 and the reserve; route labels url.post / url.get (R-S10B-7);
  * the post-extraction decision (compare_from_urls, between _resolve_pair_category and the pair
    write-back): rule 1 over the pair's "<brand> <name>" texts; then, for EACH product whose page
    category is 'other', rule 1 over that product's own "<brand> <name>" alone, a refusal making
    that product's category the lexicon group, computed on SHALLOW COPIES that also carry
    search_query = "<brand> <name>" (R-S10B-1, C12: the extracted dicts keep their categories);
    then post_resolve_refusal(resolver_classified=False) over the copies: a positive
    non-fragrance refuses; a form / concentration word is the form override (the pair is
    compared as fragrances, GC-1); with a REAL chip a blind pair takes the evidence-or-ONE-A2b
    arm; with NO chip or the chip 'other' ONE A2b decides whatever the evidence (R-S10B-2); an
    A2b answer 'fragrances' rewrites category_used to fragrances (R-S10B-3; the classify seam
    reads extraction_service.classify_category_llm at call time);
  * a refusal is counted ONCE (one EVAL on both keys), refunded ONCE by the route's failure arm
    and shipped as the coded 400 through _surface_comparison_failure;
  * url_routes.py and url_extraction_service.py import category_gate only as a module alias
    (R-S10B-10), so the raising recorders reach every call.

Golden: tests/fixtures/s81_s10b_flag_off_golden.json, recorded at the base with the flag unset and
the full configuration (19 scenarios UG01-UG19, UG19 = GET v2 FRAG, R-S10B-12). Re-record only
deliberately: S81_S10B_RECORD_GOLDEN=1 makes P01 (unset spelling) write the fixture and FAIL.

Harness: reused from the S81-10 RED module by import (R-S10B-10, the gate-rows precedent), with a
fixed X-Request-ID on every request and a usage_service._get_user_tier_info recorder. Hermetic: no
network, no .env read, every user id / fingerprint / pepper / admin credential synthetic and built
at run time; every URL a synthetic *.example.test host; pure ASCII.
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import json
import logging
import os
import re

import pytest
from fastapi.testclient import TestClient

import app.main as app_main  # noqa: F401  (first: the dotenv guard and setup_logging)
from app.api import url_routes
from app.api.auth_routes import get_current_user, get_optional_user
from app.services import (
    cache_service,
    category_gate as gate,
    extraction_service,
    llm_router,
    structured_comparison_service as scs,
    url_extraction_service as ues,
    usage_service,
)
from tests.test_s81_s10_fragrance_gate import (  # noqa: F401  (the autouse fixture + helpers)
    ADMIN_VALUE,
    APP,
    BUDGET_MESSAGE,
    CODE,
    DAY_TXT,
    FIXED_NEXT,
    FLAG,
    FP,
    OFF_IDS,
    OFF_SPELLINGS,
    REFUSAL_MESSAGE,
    ROOT,
    UID,
    USER,
    FakeRedis,
    _body,
    _coro,
    _dk,
    _evals,
    _expected_keys,
    _full_config,
    _gate_messages,
    _install_raising_gate_recorders,
    _jsonable,
    _redis_reads,
    _s10_clean,
    _set_flag,
    _window_1800,
    _window_fixed,
)

GOLDEN_PATH = ROOT / "tests" / "fixtures" / "s81_s10b_flag_off_golden.json"
RECORD_ENV = "S81_S10B_RECORD_GOLDEN"
RID = "s10b-rid"
GOLDEN_LOGGERS = (
    "app.api.url_routes", "app.services.url_extraction_service", "app.middleware.error_handler",
    "app.api.text_routes", "app.services.category_gate",
)
URL_FILES = ("app/api/url_routes.py", "app/services/url_extraction_service.py")
REFUSAL_KEYS = ["success", "error", "code", "request_id", "category", "categories_live"]
BUDGET_KEYS = ["success", "error", "code", "request_id", "categories_live", "scope", "resets_at",
               "retry_after_seconds"]
EXPIREAT = str(int(FIXED_NEXT.timestamp()) + 3600)

U1 = "https://shop-a.example.test/p/item-one"
U2 = "https://shop-b.example.test/p/item-two"
U_HOME = "https://shop-a.example.test/"
U_DENY = "https://blocked.example.test/p/item-three"
U_SLOW = "https://shop-c.example.test/p/item-slow"


def _long_url():
    base = "https://shop-a.example.test/p/"
    return base + "x" * (2049 - len(base))


def _pair(p1, p2):
    """Two pages (brand, name, raw category or None) keyed by the two synthetic URLs."""
    return {U1: p1, U2: p2}


FRAG_1 = ("Lattafa", "Khamrah Eau de Parfum 100ml", "fragrances")
FRAG_2 = ("Rasasi", "Hawas for Him Eau de Parfum 100ml", "fragrances")
FRAG = _pair(FRAG_1, FRAG_2)
PHONE_LLM_1 = ("Apple", "iPhone 15 Pro 256GB", "electronics")
PHONE_LLM_2 = ("Samsung", "Galaxy S24 Ultra 512GB", "electronics")
PHONES_LLM = _pair(PHONE_LLM_1, PHONE_LLM_2)
PHONES_JSONLD = _pair(("Apple", "iPhone 15 Pro 256GB", None), ("Samsung", "Galaxy S24 Ultra 512GB", None))
TV = _pair(("Samsung", "65 inch QLED Smart TV", None), ("LG", "65 inch OLED TV", None))
MAKEUP_LLM = _pair(("Fenty Beauty", "Pro Filtr Soft Matte Foundation", "makeup"),
                   ("Huda Beauty", "FauxFilter Foundation", "makeup"))
HAIR_MIST_1 = ("Chanel", "Coco Mademoiselle Hair Mist 35ml", "haircare")
EDT_LLM = ("Dior", "Sauvage Eau de Toilette 100ml", "fragrances")
HOUSES_BLIND = _pair(("Prada", "Paradoxe", None), ("Gucci", "Bloom", None))
LOTION = _pair(("Chanel", "Coco Mademoiselle Body Lotion 200ml", None), ("Dior", "Sauvage Body Lotion", None))
EDT_JSONLD = ("Dior", "Sauvage Eau de Toilette 100ml", None)
LAPTOP_JSONLD = ("Dell", "XPS 13 Laptop 16GB 512GB", None)
SHAMPOO_JSONLD = ("Pantene", "Pro-V Shampoo 400ml", None)


def _ordered(pages, order):
    first, second = pages
    return _pair(first, second) if order == "ab" else _pair(second, first)


# ---------------------------------------------------------------------------
# the harnesses
# ---------------------------------------------------------------------------
class UrlHarness:
    """Route level: the REAL app through TestClient and the REAL compare_from_urls (behind a
    recording spy on url_routes.compare_from_urls), the REAL normalizer and resolver (behind a
    spy); the page fetch, the verdict, the A2b, the usage leaves, the log rows, the tier read and
    Redis are recording fakes in ONE ordered list."""

    def __init__(self, monkeypatch, tmp_path, *, flag="true", pages=None, budget="10", user=USER,
                 header=FP, auth_required=False, metering=True, store=None, seed=False,
                 redis_raising=None, redis_none=False, window=_window_1800, a2b="electronics",
                 tier="free", v2=False, truth=False):
        self.mp = monkeypatch
        self.rec = []
        _full_config(monkeypatch, tmp_path, budget=budget, metering=metering)
        if seed:
            store = {**_url_seeded_store(), **dict(store or {})}
        _set_flag(monkeypatch, flag)
        if auth_required:
            monkeypatch.setenv("ENABLE_COMPARE_AUTH_REQUIRED", "true")
        if v2:
            monkeypatch.setenv("ENABLE_URL_MODE_V2", "true")
        if truth:
            monkeypatch.setenv("ENABLE_SEARCH_LOG_TRUTH", "true")
        self.user = user
        self.header = header
        self.admin = None
        self.plan = {
            "pages": dict(pages if pages is not None else FRAG),
            "deny": set(),
            "fail": set(),
            "coded": {},
            "slow": set(),
            "consume_allowed": True,
            "verdict_fail": False,
            "a2b": a2b,
            "tier": tier,
        }
        self.redis = None if redis_none else FakeRedis(self.rec, store=dict(store or {}), raising=redis_raising)
        monkeypatch.setattr(cache_service, "redis_client", self.redis)
        monkeypatch.setattr(gate, "reset_window", window)
        self._install()
        monkeypatch.setitem(APP.dependency_overrides, get_optional_user, lambda: self.user)
        monkeypatch.setitem(APP.dependency_overrides, get_current_user, lambda: self.user or USER)
        self.client = TestClient(APP, raise_server_exceptions=False)

    def _install(self):
        mp, rec, plan = self.mp, self.rec, self.plan

        async def _validate(url):
            rec.append(("ssrf", url))
            return url not in plan["deny"]

        mp.setattr(url_routes, "_validate_url_offloop_or_sync", _validate)

        def _consume(uid, access_token="", *a, **kw):
            rec.append(("consume", uid))
            if plan["consume_allowed"]:
                payload = {
                    "allowed": True, "reason": None, "tier": "free", "consumed": True,
                    "consumed_keys": {"daily": "usage:daily:" + uid, "monthly": "usage:monthly:" + uid},
                    "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
                }
            else:
                payload = {
                    "allowed": False, "reason": "daily_limit", "tier": "free", "consumed": False,
                    "remaining": {"daily": 0, "monthly": 0, "lifetime_free": 0},
                }
            return _coro(payload)

        def _refund(uid, consumed_keys=None, *a, **kw):
            rec.append(("refund", uid))
            return _coro(None)

        def _lifetime(uid, access_token="", *a, **kw):
            rec.append(("record_lifetime", uid))
            return _coro(None)

        def _log_search(**kw):
            rec.append(("log_search", kw.get("input_type"), kw.get("success"), kw.get("error_message")))
            return _coro(None)

        def _save(**kw):
            rec.append(("save", kw.get("input_type")))
            return _coro(None)

        def _capture(result, input_type, **kw):
            rec.append(("capture_result_status", input_type))

        def _ff(coro, label=None, **kw):
            rec.append(("ff", label))
            close = getattr(coro, "close", None)
            if callable(close):
                close()

        mp.setattr(url_routes, "consume_comparison_credit", _consume)
        mp.setattr(url_routes, "refund_comparison_credit", _refund)
        mp.setattr(url_routes, "record_lifetime_comparison", _lifetime)
        mp.setattr(url_routes, "log_search", _log_search)
        mp.setattr(url_routes, "save_comparison_and_track_cohort", _save)
        mp.setattr(url_routes, "capture_result_status", _capture)
        mp.setattr(url_routes, "fire_and_forget", _ff)

        async def _extract(url, url_mode_v2=False):
            rec.append(("extract", url, bool(url_mode_v2)))
            if url in plan["slow"]:
                await asyncio.sleep(0.5)
            if url in plan["coded"]:
                return ues._v2_refusal(url, "NOT_PRODUCT_PAGE", plan["coded"][url], "ok", 200)
            if url in plan["fail"] or url not in plan["pages"]:
                return {"success": False, "error": "Failed to fetch URL", "url": url}
            brand, name, category = plan["pages"][url]
            raw = {"brand": brand, "name": name, "title": f"{brand} {name}", "price": 10.5, "currency": "BHD"}
            if category:
                raw["category"] = category
            retailer = ues.detect_retailer(url)
            if url_mode_v2:
                product = ues.normalize_product_data(raw, retailer, url, url_mode_v2=True, final_url=url)
            else:
                product = ues.normalize_product_data(raw, retailer, url)
            return {"success": True, "product": product, "retailer": retailer, "source_url": url}

        mp.setattr(ues, "extract_from_url", _extract)
        mp.setattr(url_routes, "extract_from_url", _extract)

        real_compare = ues.compare_from_urls

        async def _compare_spy(*args, **kwargs):
            rec.append(("compare_from_urls", list(args), sorted(kwargs)))
            return await real_compare(*args, **kwargs)

        mp.setattr(url_routes, "compare_from_urls", _compare_spy)

        real_resolve = scs._resolve_pair_category

        async def _resolve(products, selected_category, parser_path=False):
            rec.append(("resolve", bool(parser_path), selected_category))
            return await real_resolve(products, selected_category, parser_path=parser_path)

        mp.setattr(scs, "_resolve_pair_category", _resolve)

        async def _generate(p0, p1, region, category=None, **kw):
            rec.append(("generate", category))
            if plan["verdict_fail"]:
                return {"winner_index": 0, "error": "s10b verdict failed"}, {}
            return ({"winner_index": 0, "winner_reason": "s10b reason",
                     "specs_comparison": {"product_0_advantages": ["a"], "product_1_advantages": ["b"]}},
                    {"total_tokens": 1})

        mp.setattr(extraction_service, "generate_comparison", _generate)

        async def _classify(names):
            rec.append(("a2b", tuple(names)))
            return plan["a2b"]

        mp.setattr(extraction_service, "classify_category_llm", _classify)
        mp.setattr(scs, "classify_category_llm", _classify)

        def _tier(uid, *a, **kw):
            rec.append(("tier_read", uid))
            return _coro({"subscription_tier": plan["tier"], "lifetime_comparisons_used": 5,
                          "referral_bonus_comparisons_this_month": 0})

        mp.setattr(usage_service, "_get_user_tier_info", _tier)

    def headers(self):
        out = {"X-Request-ID": RID}
        if self.header:
            out["X-Device-Fingerprint"] = self.header
        if self.admin:
            out["X-Admin-Key"] = self.admin
        return out

    def _reset_limiter(self):
        from app.middleware.rate_limiter import limiter
        limiter.reset()

    def post(self, chip=None, url1=U1, url2=U2):
        self._reset_limiter()
        body = {"url1": url1, "url2": url2, "region": "bahrain"}
        if chip is not None:
            body["selected_category"] = chip
        return self.client.post("/api/v1/url/compare", json=body, headers=self.headers())

    def get(self, chip=None, url1=U1, url2=U2):
        self._reset_limiter()
        params = {"url1": url1, "url2": url2}
        if chip is not None:
            params["selected_category"] = chip
        return self.client.get("/api/v1/url/compare", params=params, headers=self.headers())

    def call(self, verb, chip=None, url1=U1, url2=U2):
        return (self.post if verb == "post" else self.get)(chip=chip, url1=url1, url2=url2)

    def path(self, method, url, **kw):
        self._reset_limiter()
        return self.client.request(method, url, headers=self.headers(), **kw)

    def tags(self):
        return [e[0] for e in self.rec]

    def count(self, tag):
        return self.tags().count(tag)

    def entries(self, tag):
        return [e for e in self.rec if e[0] == tag]

    def mgets(self):
        return [e for e in self.rec if e[0] == "redis.mget"]

    def spy_kwargs(self):
        return [e[2] for e in self.entries("compare_from_urls")]


def _url_seeded_store(value=99):
    """Refusal counters ABOVE any budget for the synthetic account and device (B1)."""
    return {f"refusal:daily:acct:{UID}:{DAY_TXT}": value, f"refusal:daily:dev:{_dk()}:{DAY_TXT}": value}


class UrlSvcHarness:
    """Service level: the REAL compare_from_urls with the same recording leaves (no route)."""

    def __init__(self, monkeypatch, tmp_path, *, flag="true", pages=None, a2b="electronics", seed=True):
        self.rec = []
        _full_config(monkeypatch, tmp_path, budget="1")
        _set_flag(monkeypatch, flag)
        self.redis = FakeRedis(self.rec, store=_url_seeded_store() if seed else {})
        monkeypatch.setattr(cache_service, "redis_client", self.redis)
        monkeypatch.setattr(gate, "reset_window", _window_fixed)
        self.extracted = []
        rec = self.rec
        pages = dict(pages or FRAG)
        extracted = self.extracted

        async def _extract(url, url_mode_v2=False):
            rec.append(("extract", url, bool(url_mode_v2)))
            brand, name, category = pages[url]
            raw = {"brand": brand, "name": name, "title": f"{brand} {name}", "price": 10.5, "currency": "BHD"}
            if category:
                raw["category"] = category
            product = ues.normalize_product_data(raw, ues.detect_retailer(url), url)
            extracted.append(product)
            return {"success": True, "product": product}

        monkeypatch.setattr(ues, "extract_from_url", _extract)
        real_resolve = scs._resolve_pair_category

        async def _resolve(products, selected_category, parser_path=False):
            rec.append(("resolve", bool(parser_path), selected_category))
            return await real_resolve(products, selected_category, parser_path=parser_path)

        monkeypatch.setattr(scs, "_resolve_pair_category", _resolve)

        async def _generate(p0, p1, region, category=None, **kw):
            rec.append(("generate", category))
            return ({"winner_index": 0, "winner_reason": "s10b reason",
                     "specs_comparison": {"product_0_advantages": ["a"], "product_1_advantages": ["b"]}}, {})

        monkeypatch.setattr(extraction_service, "generate_comparison", _generate)

        async def _classify(names):
            rec.append(("a2b", tuple(names)))
            return a2b

        monkeypatch.setattr(extraction_service, "classify_category_llm", _classify)
        monkeypatch.setattr(scs, "classify_category_llm", _classify)

    def tags(self):
        return [e[0] for e in self.rec]


@pytest.fixture(autouse=True)
def _s10b_clean(monkeypatch):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    yield


def _fragrance_gate_param():
    return inspect.signature(ues.compare_from_urls).parameters.get("fragrance_gate")


def _resolver_classified_param():
    return inspect.signature(gate.post_resolve_refusal).parameters.get("resolver_classified")


def _assert_refusal_400(h, resp, category, *, refund=1):
    assert resp.status_code == 400, (resp.status_code, resp.text[:400])
    body = _body(resp)
    assert sorted(body) == sorted(REFUSAL_KEYS), body
    assert body["code"] == CODE and body["error"] == REFUSAL_MESSAGE, body
    assert body["category"] == category and body["categories_live"] == ["fragrances"], body
    assert body["success"] is False and body["request_id"] == RID, body
    assert h.count("generate") == 0, h.rec
    assert h.count("refund") == refund, h.rec
    for tag in ("save", "record_lifetime", "capture_result_status"):
        assert h.count(tag) == 0, (tag, h.rec)
    return body


def _assert_one_eval(h, dk=True):
    evals = _evals(h.rec)
    assert len(evals) == 1, evals
    assert list(evals[0][2]) == _expected_keys(dk=_dk() if dk else None), evals
    return evals[0]


# ===========================================================================
# R01-R05: the flag read and the pre-consume budget (url_routes)
# ===========================================================================
def test_r01_url_routes_read_the_shared_flag_reader(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    # (a) env unset, the shared reader patched ON: the link compare is gated.
    h = UrlHarness(monkeypatch, tmp_path, flag=None, pages=PHONES_JSONLD, a2b="electronics")
    monkeypatch.setattr(gate, "fragrance_only_gate_enabled", lambda: True)
    resp = h.post()
    # (the error handler reads the env itself, so the additive keys stay off: C15)
    assert resp.status_code == 400 and _body(resp)["code"] == CODE, (resp.status_code, resp.text[:300])
    assert h.count("generate") == 0 and h.count("refund") == 1 and h.count("a2b") == 1, h.rec
    # (b) env "true", the shared reader patched OFF: the base path (no read, no kwarg).
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=PHONES_JSONLD, a2b="electronics")
    monkeypatch.setattr(gate, "fragrance_only_gate_enabled", lambda: False)
    resp = h.post()
    assert resp.status_code == 200, resp.text[:300]
    assert h.mgets() == [] and h.count("a2b") == 0, h.rec
    assert all("fragrance_gate" not in kw for kw in h.spy_kwargs()), h.rec
    # (c) neither URL file parses the env or imports a category_gate function by name.
    for rel in URL_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert FLAG not in text, rel
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module != "app.services.category_gate", (rel, node.lineno)


@pytest.mark.parametrize("route,axis,spelling", [
    ("post", "acct", " TRUE "), ("post", "dev", "1"), ("get", "acct", "yes"), ("get", "dev", "On"),
], ids=["post-acct", "post-dev", "get-acct", "get-dev"])
def test_r02_budget_spent_never_billed(monkeypatch, tmp_path, caplog, route, axis, spelling):
    caplog.set_level(logging.INFO)
    h = UrlHarness(monkeypatch, tmp_path, flag=spelling, pages=PHONES_LLM, budget="1")
    h.redis.store[_expected_keys(dk=_dk())[0 if axis == "acct" else 1]] = 1
    caplog.clear()
    resp = h.call(route)
    assert resp.status_code == 429, (resp.status_code, resp.text[:300])
    body = _body(resp)
    assert sorted(body) == sorted(BUDGET_KEYS), body
    assert body["error"] == BUDGET_MESSAGE and body["code"] == CODE, body
    assert body["scope"] == "refusal_daily" and body["categories_live"] == ["fragrances"], body
    assert body["retry_after_seconds"] == 1800 and isinstance(body["retry_after_seconds"], int), body
    assert isinstance(body["resets_at"], str) and body["request_id"] == RID, body
    assert resp.headers.get("retry-after") == "1800", dict(resp.headers)
    for tag in ("consume", "extract", "compare_from_urls", "refund", "log_search", "a2b", "generate"):
        assert h.count(tag) == 0, (tag, h.rec)
    assert _evals(h.rec) == [], h.rec
    assert len(h.mgets()) == 1 and _redis_reads(h.rec) == _expected_keys(dk=_dk()), h.rec
    assert _gate_messages(caplog) == [f"[CATEGORY-GATE] budget spent stage=pre_consume route=url.{route}"]


def test_r03_budget_order_reserve_and_consent(monkeypatch, tmp_path):
    # (a) under the budget: the MGET precedes the consume, which precedes the extraction.
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, budget="2")
    for key in _expected_keys(dk=_dk()):
        h.redis.store[key] = 1
    resp = h.post()
    assert resp.status_code == 200, resp.text[:300]
    tags = h.tags()
    assert "redis.mget" in tags, h.rec
    assert tags.index("redis.mget") < tags.index("consume") < tags.index("extract"), h.rec
    # (b) consent refused AND the budget spent: the budget 429 wins, nothing consumed.
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, budget="1", seed=True)
    monkeypatch.setattr(llm_router, "compare_refuses_for_consent", lambda: True)
    resp = h.post()
    assert resp.status_code == 429 and _body(resp)["code"] == CODE, resp.text[:300]
    assert h.count("consume") == 0, h.rec
    # (c) consent refused, the budget unspent: the base 503, nothing consumed, one MGET first.
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, budget="10")
    monkeypatch.setattr(llm_router, "compare_refuses_for_consent", lambda: True)
    resp = h.post()
    assert resp.status_code == 503 and _body(resp)["code"] == "LLM_UNAVAILABLE", resp.text[:300]
    assert h.count("consume") == 0 and len(h.mgets()) == 1, h.rec


def test_r04_budget_subject_axes_and_anonymous(monkeypatch, tmp_path):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG)
    assert h.post().status_code == 200
    assert _redis_reads(h.rec) == _expected_keys(dk=_dk()), h.rec
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, header=None)
    assert h.post().status_code == 200
    assert _redis_reads(h.rec) == _expected_keys(), h.rec
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, user=None)
    assert h.post().status_code == 200
    assert _redis_reads(h.rec) == [f"refusal:daily:dev:{_dk()}:{DAY_TXT}"], h.rec
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=TV, user=None, header=None)
    resp = h.post()
    _assert_refusal_400(h, resp, "electronics", refund=0)
    assert h.mgets() == [] and _evals(h.rec) == [] and h.count("consume") == 0, h.rec


def test_r05_budget_fail_open_and_exemptions(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    # (a) the MGET raises: proceed, ONE fail-open WARNING.
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, redis_raising="get")
    caplog.clear()
    assert h.post().status_code == 200
    assert _gate_messages(caplog) == ["[CATEGORY-GATE] budget read fail-open type=RuntimeError"]
    # (b) the S81-09 allow-list (mixed case) exempts the budget, not the rules.
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, budget="1", seed=True)
    monkeypatch.setenv("DEVICE_QUOTA_EXEMPT_USER_IDS", UID.upper())
    assert h.post().status_code == 200
    assert len(h.mgets()) == 1, h.rec
    # (c) a premium account is exempt: ONE tier read.
    monkeypatch.delenv("DEVICE_QUOTA_EXEMPT_USER_IDS", raising=False)
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, budget="1", seed=True, tier="premium")
    assert h.post().status_code == 200
    assert h.count("tier_read") == 1 and len(h.mgets()) == 1, h.rec
    # (d) no Redis client: proceed silently.
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, redis_none=True)
    caplog.clear()
    assert h.post().status_code == 200
    assert _gate_messages(caplog) == [], caplog.records


# ===========================================================================
# R06-R13: the post-extraction decision (compare_from_urls)
# ===========================================================================
@pytest.mark.parametrize("verb,v2", [("post", False), ("get", False), ("post", True), ("get", True)],
                         ids=["post-v1", "get-v1", "post-v2", "get-v2"])
def test_r06_post_extract_refusal(monkeypatch, tmp_path, caplog, verb, v2):
    caplog.set_level(logging.INFO)
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=PHONES_LLM, v2=v2, window=_window_fixed)
    caplog.clear()
    resp = h.call(verb)
    _assert_refusal_400(h, resp, "electronics")
    assert h.count("consume") == 1 and h.count("a2b") == 0, h.rec
    assert ("ff", "usage_refund.url.compare.failure") in h.rec, h.rec
    ev = _assert_one_eval(h)
    assert ev[3] == (EXPIREAT,), ev
    assert _gate_messages(caplog) == ["[CATEGORY-GATE] refused stage=post_extract category=electronics"]


@pytest.mark.parametrize("order", ["ab", "ba"])
def test_r07_mixed_pair_refused_per_product(monkeypatch, tmp_path, order):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=_ordered((FRAG_1, PHONE_LLM_1), order))
    resp = h.post()
    _assert_refusal_400(h, resp, "electronics")
    _assert_one_eval(h)


@pytest.mark.parametrize("chip", [None, "other", "fragrances", "electronics"],
                         ids=["nochip", "other", "fragrances", "electronics"])
def test_r08_blind_pair_classified_chip_free(monkeypatch, tmp_path, chip):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=PHONES_JSONLD, a2b="electronics")
    resp = h.post(chip=chip)
    assert h.entries("a2b") == [("a2b", ("Apple iPhone 15 Pro 256GB", "Samsung Galaxy S24 Ultra 512GB"))], h.rec
    _assert_refusal_400(h, resp, "electronics")
    _assert_one_eval(h)


def test_r09_blind_houses_with_a_real_chip_proceed_without_a_classifier(monkeypatch, tmp_path):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=HOUSES_BLIND, a2b="fashion")
    resp = h.post(chip="fragrances")
    assert resp.status_code == 200, resp.text[:300]
    assert len(h.mgets()) == 1, h.rec
    assert h.count("a2b") == 0 and _evals(h.rec) == [] and h.count("refund") == 0, h.rec
    assert h.entries("generate") == [("generate", "fragrances")], h.rec


def test_r10_classifier_other_proceeds_uncounted(monkeypatch, tmp_path):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=PHONES_JSONLD, a2b="other")
    resp = h.post()
    assert resp.status_code == 200, resp.text[:300]
    assert h.count("a2b") == 1, h.rec
    assert _evals(h.rec) == [] and h.count("refund") == 0 and h.count("generate") == 1, h.rec


@pytest.mark.parametrize("order", ["ab", "ba"], ids=["mist-first", "mist-second"])
def test_r11_form_override_compares_as_fragrances(monkeypatch, tmp_path, order):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=_ordered((HAIR_MIST_1, EDT_LLM), order))
    resp = h.post()
    assert resp.status_code == 200, resp.text[:300]
    assert h.entries("generate") == [("generate", "fragrances")], h.rec
    body = _body(resp)
    assert body["category_used"] == "fragrances", body.get("category_used")
    assert [p["category"] for p in body["products"]] == ["fragrances", "fragrances"], body["products"]
    assert h.count("a2b") == 0 and _evals(h.rec) == [], h.rec
    assert len(h.mgets()) == 1, h.rec  # the gated request read the budget


@pytest.mark.parametrize("label", [None, "fragrances"], ids=["blind", "llm-fragrances"])
def test_r12_rule1_on_extracted_names(monkeypatch, tmp_path, caplog, label):
    """Rule 1 over the pair's names refuses at no A2b (Q1 / R-S10B-6), also when the extraction
    LLM labelled the pages 'fragrances' (the pair-level rule wins over the page category; the
    per-product pass of R-S10B-1 reads only 'other' pages, so this node pins the pair rule)."""
    caplog.set_level(logging.INFO)
    pages = {url: (brand, name, label) for url, (brand, name, _c) in TV.items()}
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=pages)
    caplog.clear()
    resp = h.post()
    _assert_refusal_400(h, resp, "electronics")
    assert h.count("a2b") == 0, h.rec
    _assert_one_eval(h)
    assert _gate_messages(caplog) == ["[CATEGORY-GATE] refused stage=post_extract category=electronics"]


def test_r13_house_beside_a_product_word_goes_to_the_classifier(monkeypatch, tmp_path):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=LOTION, a2b="skincare")
    resp = h.post()
    assert h.count("a2b") == 1, h.rec
    _assert_refusal_400(h, resp, "skincare")
    _assert_one_eval(h)


# ===========================================================================
# R14-R16: billing and logs on the link refusal
# ===========================================================================
class _QuotaRedis(FakeRedis):
    """FakeRedis plus S81-09's two quota scripts emulated in Python (keyed on usage_service's own
    script constants), recorded as 'quota.eval' (the gate-rows shape, copied, not imported)."""

    def _emulate(self, shape, script, keys, argv):
        if script == usage_service.DEVICE_CONSUME_SCRIPT:
            account = int(self.store.get(keys[0]) or 0)
            device = int(self.store.get(keys[1]) or 0) if len(keys) > 1 else 0
            reply = None
            if len(keys) > 1 and device >= int(argv[1]):
                reply = [2, account, device]
            if reply is None and account >= int(argv[0]):
                reply = [1, account, device]
            if reply is None:
                if len(keys) > 1:
                    device += 1
                    self.store[keys[1]] = device
                account += 1
                self.store[keys[0]] = account
                reply = [0, account, device]
            self.rec.append(("quota.eval", "consume", tuple(keys), tuple(reply)))
            return reply
        if script == usage_service.DEVICE_REFUND_SCRIPT:
            reply = []
            for key in keys:
                value = int(self.store.get(key) or 0)
                if value > 0:
                    self.store[key] = value - 1
                    reply.append(value - 1)
                else:
                    reply.append(-1)
            self.rec.append(("quota.eval", "refund", tuple(keys), tuple(reply)))
            return reply
        return super()._emulate(shape, script, keys, argv)


def test_r14_device_debit_refunded_on_the_link_refusal(monkeypatch, tmp_path):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=PHONES_LLM, window=_window_fixed)
    monkeypatch.setenv("ENABLE_DEVICE_DAILY_QUOTA", "true")
    fake = _QuotaRedis(h.rec, store={})
    h.redis = fake
    monkeypatch.setattr(cache_service, "redis_client", fake)
    monkeypatch.setattr(usage_service, "redis_client", fake)
    monkeypatch.setattr(usage_service, "_get_active_referral_bonus", lambda uid: _coro(0))
    rec = h.rec
    real_consume = usage_service.consume_comparison_credit
    real_refund = usage_service.refund_comparison_credit

    async def _consume(uid, access_token="", **kw):
        rec.append(("consume", uid))
        return await real_consume(uid, access_token, **kw)

    async def _refund(uid, consumed_keys=None):
        rec.append(("refund", uid))
        await real_refund(uid, consumed_keys)

    def _ff(coro, label=None, **kw):
        rec.append(("ff", label))
        if isinstance(label, str) and label.startswith("usage_refund"):
            try:
                coro.send(None)
            except StopIteration:
                return
            coro.close()
            raise AssertionError("the refund suspended: " + label)
        close = getattr(coro, "close", None)
        if callable(close):
            close()

    monkeypatch.setattr(url_routes, "consume_comparison_credit", _consume)
    monkeypatch.setattr(url_routes, "refund_comparison_credit", _refund)
    monkeypatch.setattr(url_routes, "fire_and_forget", _ff)
    resp = h.post()
    _assert_refusal_400(h, resp, "electronics")
    quota = [e for e in h.rec if e[0] == "quota.eval"]
    assert [e[1] for e in quota] == ["consume", "refund"], quota
    consume_keys = quota[0][2]
    assert len(consume_keys) == 2 and quota[1][2] == consume_keys, quota
    assert quota[0][3] == (0, 1, 1) and quota[1][3] == (0, 0), quota
    assert fake.store[consume_keys[0]] == 0 and fake.store[consume_keys[1]] == 0, fake.store
    assert h.count("consume") == 1 and h.count("refund") == 1, h.rec
    _assert_one_eval(h)


def test_r15_failure_row_and_no_delivery_side_effects(monkeypatch, tmp_path):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=PHONES_LLM, truth=True)
    resp = h.post()
    _assert_refusal_400(h, resp, "electronics")
    rows = h.entries("log_search")
    assert rows == [("log_search", "url", False, REFUSAL_MESSAGE)], rows
    labels = [e[1] for e in h.entries("ff")]
    assert labels.index("usage_refund.url.compare.failure") < labels.index("log_search.url.failure"), labels
    assert "log_search.url.success" not in labels, labels


_LINK_GRAMMAR = re.compile(
    r"^\[CATEGORY-GATE\] (refused stage=post_extract category="
    r"(electronics|grocery|supplements|makeup|skincare|haircare|fashion)"
    r"|budget spent stage=pre_consume route=url\.(post|get)"
    r"|(budget read fail-open|budget record failed|lexicon unavailable|kb lookup failed)"
    r" type=[A-Za-z_][A-Za-z0-9_]*)$")


def test_r16_log_hygiene_and_grammar(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=PHONES_LLM, budget="1",
                   store={_expected_keys()[0]: 1})
    h.post()
    for pages, chip in ((PHONES_LLM, None), (PHONES_JSONLD, None), (TV, None)):
        h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=pages, a2b="electronics")
        h.post(chip=chip)
    forbidden = [U1, U2, "shop-a.example.test", "shop-b.example.test", UID, FP, _dk(),
                 "iPhone", "Galaxy", "QLED", "OLED", "Samsung", "Apple"]
    gate_records = [r for r in caplog.records
                    if r.name == "app.services.category_gate" or r.getMessage().startswith("[CATEGORY-GATE]")]
    for record in gate_records:
        msg = record.getMessage()
        assert record.levelno < logging.ERROR, msg
        for needle in forbidden:
            assert needle not in msg, (needle, msg)
        if msg.startswith("[CATEGORY-GATE]"):
            assert _LINK_GRAMMAR.match(msg), msg
    lines = _gate_messages(caplog)
    assert len([m for m in lines if " refused " in m]) >= 3, lines
    assert len([m for m in lines if " budget spent " in m]) == 1, lines


# ===========================================================================
# R17-R18: the service and category_gate seams
# ===========================================================================
def test_r17_service_signature_and_order(monkeypatch, tmp_path):
    param = _fragrance_gate_param()
    assert param is not None, "S81-10b: compare_from_urls has no fragrance_gate parameter"
    assert param.kind is inspect.Parameter.KEYWORD_ONLY and param.default is None, param
    subject = gate.BudgetSubject(user_id=UID, device_key=None)
    decision = gate.GateDecision("proceed", None, False, subject)
    # (a) MIXED: refused per product, before the write-back; the extracted dicts keep their categories.
    h = UrlSvcHarness(monkeypatch, tmp_path, pages=_pair(FRAG_1, PHONE_LLM_1))
    out = asyncio.run(ues.compare_from_urls(U1, U2, "bahrain", None, fragrance_gate=decision))
    assert out == gate.refusal_result("electronics"), out
    assert h.tags() == ["extract", "extract", "resolve", "redis.eval"], h.rec
    assert h.rec[2] == ("resolve", True, None), h.rec
    assert [p["category"] for p in h.extracted] == ["fragrances", "electronics"], h.extracted
    # (b) R-S10B-1 on copies: the laptop page is refused by its own rule 1; the extracted dicts
    # keep 'other' and carry no search_query (the copies carry it).
    h = UrlSvcHarness(monkeypatch, tmp_path, pages=_pair(EDT_JSONLD, LAPTOP_JSONLD))
    out = asyncio.run(ues.compare_from_urls(U1, U2, "bahrain", None, fragrance_gate=decision))
    assert out == gate.refusal_result("electronics"), out
    assert "a2b" not in h.tags() and "generate" not in h.tags(), h.rec
    assert [p["category"] for p in h.extracted] == ["other", "other"], h.extracted
    assert all("search_query" not in p for p in h.extracted), h.extracted


def test_r18_category_gate_resolver_classified(monkeypatch, tmp_path):
    param = _resolver_classified_param()
    assert param is not None, "S81-10b: post_resolve_refusal has no resolver_classified parameter"
    assert param.kind is inspect.Parameter.KEYWORD_ONLY and param.default is True, param
    calls = []

    def _classify(answer):
        async def _c(names):
            calls.append(tuple(names))
            return answer
        return _c

    def _products():
        return [{"brand": "Acme", "name": "Widget One", "category": "other"},
                {"brand": "Acme", "name": "Widget Two", "category": "other"}]

    def _run(evidence, chip, answer, **kw):
        calls.clear()
        decision = gate.GateDecision("proceed", None, evidence, None)
        return asyncio.run(gate.post_resolve_refusal(
            decision, _products(), parser_path=False, selected_category=chip, category_used="other",
            classify=_classify(answer), **kw))

    # (b) resolver_classified=False: no chip / 'other' -> ONE classify whatever the evidence.
    for chip in (None, "other"):
        for evidence in (True, False):
            v = _run(evidence, chip, "electronics", resolver_classified=False)
            assert v.refused == "electronics" and len(calls) == 1, (chip, evidence, v, calls)
            v = _run(evidence, chip, "other", resolver_classified=False)
            assert v.refused is None and len(calls) == 1, (chip, evidence, v, calls)
    # a real chip: the evidence arm (0 classify) else ONE classify.
    v = _run(True, "fragrances", "electronics", resolver_classified=False)
    assert v.refused is None and calls == [], (v, calls)
    v = _run(False, "fragrances", "electronics", resolver_classified=False)
    assert v.refused == "electronics" and len(calls) == 1, (v, calls)
    v = _run(False, "fragrances", "other", resolver_classified=False)
    assert v.refused is None and len(calls) == 1, (v, calls)
    # (c) the default keeps C11: no chip reuses category_used, 0 classify.
    calls.clear()
    decision = gate.GateDecision("proceed", None, False, None)
    v = asyncio.run(gate.post_resolve_refusal(
        decision, _products(), parser_path=False, selected_category=None, category_used="electronics",
        classify=_classify("other")))
    assert v.refused == "electronics" and calls == [], (v, calls)


def test_r18d_route_labels(caplog):
    caplog.set_level(logging.INFO)
    caplog.clear()
    gate.log_budget_spent("url.post")
    gate.log_budget_spent("url.get")
    gate.log_budget_spent("bogus")
    gate.log_refused("post_extract", "electronics", "url.get")
    assert _gate_messages(caplog) == [
        "[CATEGORY-GATE] budget spent stage=pre_consume route=url.post",
        "[CATEGORY-GATE] budget spent stage=pre_consume route=url.get",
        "[CATEGORY-GATE] budget spent stage=pre_consume route=image",
        "[CATEGORY-GATE] refused stage=post_extract category=electronics route=url.get",
    ]


# ===========================================================================
# R19-R20: the rulings' rows (R-S10B-1, R-S10B-2, R-S10B-3)
# ===========================================================================
@pytest.mark.parametrize("case,order", [
    ("laptop", "ab"), ("laptop", "ba"), ("shampoo", "ab"), ("shampoo", "ba"),
], ids=["laptop-edt-first", "laptop-edt-second", "shampoo-edt-first", "shampoo-edt-second"])
def test_r19_mixed_jsonld_pair_refused_per_product(monkeypatch, tmp_path, caplog, case, order):
    caplog.set_level(logging.INFO)
    other, category = (LAPTOP_JSONLD, "electronics") if case == "laptop" else (SHAMPOO_JSONLD, "haircare")
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=_ordered((EDT_JSONLD, other), order))
    caplog.clear()
    resp = h.post()
    _assert_refusal_400(h, resp, category)
    assert h.count("a2b") == 0, h.rec
    _assert_one_eval(h)
    assert _gate_messages(caplog) == [f"[CATEGORY-GATE] refused stage=post_extract category={category}"]


@pytest.mark.parametrize("chip", [None, "other"], ids=["nochip", "other"])
@pytest.mark.parametrize("plan", ["fragrances", "fashion", "other"])
def test_r20_no_chip_blind_pair_one_a2b(monkeypatch, tmp_path, chip, plan):
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=HOUSES_BLIND, a2b=plan)
    resp = h.post(chip=chip)
    assert h.entries("a2b") == [("a2b", ("Prada Paradoxe", "Gucci Bloom"))], h.rec
    if plan == "fashion":
        _assert_refusal_400(h, resp, "fashion")
        _assert_one_eval(h)
        return
    assert resp.status_code == 200, resp.text[:300]
    assert _evals(h.rec) == [] and h.count("refund") == 0, h.rec
    assert h.entries("generate") == [("generate", plan)], h.rec
    assert _body(resp)["category_used"] == plan, _body(resp).get("category_used")


# ===========================================================================
# P01: the flag-OFF golden (the five OFF spellings, the full configuration, raising recorders)
# ===========================================================================
def _ug01(h):
    return h.post()


def _ug02(h):
    h.plan["pages"] = dict(PHONES_LLM)
    return h.post()


def _ug03(h):
    h.plan["pages"] = dict(PHONES_JSONLD)
    return h.get()


def _ug04(h):
    h.plan["pages"] = dict(PHONES_JSONLD)
    return h.post(chip="fragrances")


def _ug05(h):
    h.mp.setenv("ENABLE_URL_MODE_V2", "true")
    h.plan["pages"] = dict(MAKEUP_LLM)
    return h.post()


def _ug06(h):
    h.plan["pages"] = _pair(HAIR_MIST_1, EDT_LLM)
    return h.post()


def _ug07(h):
    h.plan["fail"] = {U2}
    return h.post()


def _ug08(h):
    h.mp.setenv("ENABLE_URL_MODE_V2", "true")
    h.plan["coded"] = {U1: "category"}
    return h.post()


def _ug09(h):
    h.plan["consume_allowed"] = False
    return h.post()


def _ug10(h):
    h.plan["verdict_fail"] = True
    return h.get()


def _ug11(h):
    h.user = None
    h.mp.setenv("ENABLE_COMPARE_AUTH_REQUIRED", "true")
    h.mp.setenv("ADMIN_API_KEY", ADMIN_VALUE)
    h.admin = ADMIN_VALUE
    h.plan["pages"] = dict(PHONES_LLM)
    return h.post()


def _ug12(h):
    h.mp.setenv("ENABLE_URL_MODE_V2", "true")
    return h.get(url1=U_HOME)


def _ug13(h):
    h.plan["deny"] = {U_DENY}
    return h.post(url1=U_DENY)


def _admin(h):
    h.user = None
    h.mp.setenv("ENABLE_COMPARE_AUTH_REQUIRED", "true")
    h.mp.setenv("ADMIN_API_KEY", ADMIN_VALUE)
    h.admin = ADMIN_VALUE


def _ug14(h):
    _admin(h)
    return h.path("POST", "/api/v1/url/detect", json={"url": U1})


def _ug15(h):
    return h.path("GET", "/api/v1/url/retailers")


def _ug16(h):
    _admin(h)
    return h.path("POST", "/api/v1/url/extract", json={"url": U1})


def _ug17(h):
    h.mp.setenv("ENABLE_SEARCH_LOG_TRUTH", "true")
    h.plan["pages"] = dict(PHONES_LLM)
    return h.post()


def _ug18(h):
    h.mp.setenv("ENABLE_SEARCH_LOG_TRUTH", "true")
    h.plan["fail"] = {U2}
    return h.post()


def _ug19(h):
    h.mp.setenv("ENABLE_URL_MODE_V2", "true")
    return h.get()


GOLDEN_SCENARIOS = [
    ("UG01", _ug01), ("UG02", _ug02), ("UG03", _ug03), ("UG04", _ug04), ("UG05", _ug05),
    ("UG06", _ug06), ("UG07", _ug07), ("UG08", _ug08), ("UG09", _ug09), ("UG10", _ug10),
    ("UG11", _ug11), ("UG12", _ug12), ("UG13", _ug13), ("UG14", _ug14), ("UG15", _ug15),
    ("UG16", _ug16), ("UG17", _ug17), ("UG18", _ug18), ("UG19", _ug19),
]


def _scenario_record(h, resp, records):
    headers = {"content-type": resp.headers.get("content-type")}
    if resp.headers.get("retry-after") is not None:
        headers["retry-after"] = resp.headers.get("retry-after")
    logs = [r.getMessage() for r in records if r.name in GOLDEN_LOGGERS and r.levelno >= logging.INFO]
    return {"calls": _jsonable(h.rec), "status": resp.status_code, "headers": headers,
            "body": resp.text, "logs": logs}


def _run_golden(monkeypatch, tmp_path, caplog, spelling):
    caplog.set_level(logging.INFO)
    called = []
    a2b_calls = []
    out = {}
    for name, run in GOLDEN_SCENARIOS:
        monkeypatch.delenv("ENABLE_URL_MODE_V2", raising=False)
        monkeypatch.delenv("ENABLE_SEARCH_LOG_TRUTH", raising=False)
        monkeypatch.delenv("ENABLE_COMPARE_AUTH_REQUIRED", raising=False)
        monkeypatch.delenv("ADMIN_API_KEY", raising=False)
        h = UrlHarness(monkeypatch, tmp_path, flag=spelling, budget="1", seed=True, a2b="electronics")
        _install_raising_gate_recorders(monkeypatch, called)
        caplog.clear()
        resp = run(h)
        out[name] = _scenario_record(h, resp, caplog.records)
        out[name]["gate_lines"] = _gate_messages(caplog)
        a2b_calls.extend(h.entries("a2b"))
    return out, called, a2b_calls


@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=OFF_IDS)
def test_p01_flag_off_golden(monkeypatch, tmp_path, caplog, spelling):
    out, called, a2b_calls = _run_golden(monkeypatch, tmp_path, caplog, spelling)
    if spelling is None and os.environ.get(RECORD_ENV) == "1":
        data = {
            "meta": {
                "unit": "S81-10b LINKS-GATE",
                "recorded_at_base": "c6fb65336deab4f48275b13d3847e0f42b298984",
                "recorded_with": "ENABLE_FRAGRANCE_ONLY_GATE unset; full configuration (REFUSAL_DAILY_BUDGET=1, "
                                 "a run-time lexicon, the device header bound with a synthetic pepper, "
                                 "ENABLE_PAID_ROUTE_METERING=true, refusal counters seeded above the budget, "
                                 "the A2b armed to answer electronics, a fixed X-Request-ID, the tier recorder)",
                "scenarios": len(out),
            },
            "scenarios": {k: {f: out[k][f] for f in ("calls", "status", "headers", "body", "logs")}
                          for k in sorted(out)},
        }
        GOLDEN_PATH.write_text(json.dumps(data, ensure_ascii=True, indent=1) + "\n", encoding="ascii", newline="\n")
        pytest.fail("S81_S10B_RECORD_GOLDEN=1: the golden was written; re-run without it")
    assert called == [], called
    assert a2b_calls == [], a2b_calls
    golden = json.loads(GOLDEN_PATH.read_text(encoding="ascii"))["scenarios"]
    assert sorted(golden) == sorted(out), (sorted(golden), sorted(out))
    for name in sorted(out):
        assert out[name]["gate_lines"] == [], (name, out[name]["gate_lines"])
        for field in ("calls", "status", "headers", "body", "logs"):
            assert out[name][field] == golden[name][field], (name, field, out[name][field], golden[name][field])


# ===========================================================================
# P02-P06: the other pins
# ===========================================================================
@pytest.mark.parametrize("spelling", OFF_SPELLINGS + ["true"], ids=OFF_IDS + ["true"])
def test_p02_service_without_the_kwarg_is_base(monkeypatch, tmp_path, spelling):
    for pages, category in ((PHONES_LLM, "electronics"), (PHONES_JSONLD, "other")):
        h = UrlSvcHarness(monkeypatch, tmp_path, flag=spelling, pages=pages)
        called = []
        _install_raising_gate_recorders(monkeypatch, called)
        out = asyncio.run(ues.compare_from_urls(U1, U2, "bahrain", None))
        assert out.get("success") is True and out.get("category_used") == category, out
        assert h.tags() == ["extract", "extract", "resolve", "generate"], h.rec
        assert h.rec[2] == ("resolve", True, None) and h.rec[3] == ("generate", category), h.rec
        assert called == [], called


_ADMIN_ROUTES = [
    ("POST", "/api/v1/url/extract", {"json": {"url": U1}}, True),
    ("GET", "/api/v1/url/extract", {"params": {"url": U1}}, True),
    ("POST", "/api/v1/url/detect", {"json": {"url": U1}}, True),
    ("GET", "/api/v1/url/detect", {"params": {"url": U1}}, True),
    ("GET", "/api/v1/url/retailers", {}, False),
]


def _admin_route_call(monkeypatch, tmp_path, flag, method, url, kw, admin):
    h = UrlHarness(monkeypatch, tmp_path, flag=flag, budget="1", seed=True)
    called = []
    _install_raising_gate_recorders(monkeypatch, called)
    reads = []
    monkeypatch.setattr(gate, "fragrance_only_gate_enabled", lambda: reads.append(1) or flag == "true")
    if admin:
        _admin(h)
    resp = h.path(method, url, **kw)
    return h, resp, called, reads


@pytest.mark.parametrize("flag", [None, "true"], ids=["off", "on"])
@pytest.mark.parametrize("idx", range(len(_ADMIN_ROUTES)),
                         ids=["post-extract", "get-extract", "post-detect", "get-detect", "retailers"])
def test_p03_admin_routes_untouched(monkeypatch, tmp_path, flag, idx):
    method, url, kw, admin = _ADMIN_ROUTES[idx]
    h0, base, _c0, _r0 = _admin_route_call(monkeypatch, tmp_path, None, method, url, kw, admin)
    h, resp, called, reads = _admin_route_call(monkeypatch, tmp_path, flag, method, url, kw, admin)
    assert resp.status_code == base.status_code == 200, (resp.status_code, base.status_code, resp.text[:300])
    assert resp.text == base.text, (resp.text[:300], base.text[:300])
    assert reads == [] and called == [] and h.mgets() == [], (reads, called, h.rec)


def _exit_v2_coded(h):
    h.mp.setenv("ENABLE_URL_MODE_V2", "true")
    h.plan["coded"] = {U1: "category"}
    return h.post()


def _exit_few(h):
    h.plan["fail"] = {U2}
    return h.post()


def _exit_verdict(h):
    h.plan["verdict_fail"] = True
    return h.post()


def _exit_deadline(h):
    h.mp.setenv("ENABLE_URL_MODE_V2", "true")
    h.mp.setattr(url_routes, "_URL_COMPARE_DEADLINE_SECONDS", 0.05)
    h.plan["pages"][U_SLOW] = FRAG_1
    h.plan["slow"] = {U_SLOW}
    return h.post(url1=U_SLOW)


def _exit_consume(h):
    h.plan["consume_allowed"] = False
    return h.post()


_EXITS = [("v2-coded", _exit_v2_coded, 400), ("few-products", _exit_few, 400),
          ("verdict-failed", _exit_verdict, 503), ("v2-deadline", _exit_deadline, 503),
          ("consume-refused", _exit_consume, 429)]


@pytest.mark.parametrize("idx", range(len(_EXITS)), ids=[e[0] for e in _EXITS])
def test_p04_other_url_exits_unchanged_under_the_flag(monkeypatch, tmp_path, idx):
    _name, run, status = _EXITS[idx]
    seen = {}
    for flag in ("true", None):
        monkeypatch.delenv("ENABLE_URL_MODE_V2", raising=False)
        h = UrlHarness(monkeypatch, tmp_path, flag=flag, pages=FRAG, budget="10")
        resp = run(h)
        body = _body(resp)
        body.pop("request_id", None)
        seen[flag] = (resp.status_code, body, h.count("consume"), h.count("refund"))
        assert _evals(h.rec) == [] and h.count("a2b") == 0, h.rec
    assert seen["true"] == seen[None], seen
    assert seen[None][0] == status, seen


@pytest.mark.parametrize("verb", ["post", "get"])
def test_p05_admin_key_bypass(monkeypatch, tmp_path, caplog, verb):
    caplog.set_level(logging.INFO)
    h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=PHONES_LLM, budget="1", seed=True)
    _admin(h)
    caplog.clear()
    resp = h.call(verb)
    assert resp.status_code == 200, resp.text[:300]
    assert h.mgets() == [] and _evals(h.rec) == [], h.rec
    assert h.spy_kwargs() and all("fragrance_gate" not in kw for kw in h.spy_kwargs()), h.rec
    assert _gate_messages(caplog) == [], _gate_messages(caplog)


@pytest.mark.parametrize("axis", ["acct", "dev"])
@pytest.mark.parametrize("case", ["ssrf", "homepage", "too-long"])
def test_p06_free_400s_precede_the_budget(monkeypatch, tmp_path, case, axis):
    if axis == "acct":
        h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, budget="1", header=None,
                       store={_expected_keys()[0]: 1})
    else:
        h = UrlHarness(monkeypatch, tmp_path, flag="true", pages=FRAG, budget="1")
        h.redis.store[_expected_keys(dk=_dk())[1]] = 1
    if case == "ssrf":
        h.plan["deny"] = {U_DENY}
        resp = h.post(url1=U_DENY)
        assert resp.status_code == 400 and _body(resp)["error"] == "URL blocked by security policy", resp.text
    else:
        monkeypatch.setenv("ENABLE_URL_MODE_V2", "true")
        resp = h.post(url1=U_HOME if case == "homepage" else _long_url())
        body = _body(resp)
        assert resp.status_code == 400 and body["code"] == "NOT_PRODUCT_PAGE", resp.text[:300]
        assert body["reason"] == ("url_too_long" if case == "too-long" else body["reason"]), body
    assert h.mgets() == [] and h.count("consume") == 0 and h.count("extract") == 0, h.rec
