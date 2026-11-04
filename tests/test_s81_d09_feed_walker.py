"""D09 FEED-WALKER RED rows (spec S81-G2 section 5 of D09, as amended by
RULINGS_S81_G2): 21 RED rows + 4 PIN rows.

Hermetic: ``_mod`` asserts the module spec (AssertionError at base, never an
ImportError); the service-role client, the fetch, the SSRF validator, the sleep
and the clock are recorders; feed pages come from
``tests/fixtures/s81_d09_feeds.json`` (synthetic hosts only).
"""
import copy
import hashlib
import importlib
import importlib.util
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "s81_d09_feeds.json"
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
OFF_SPELLINGS = [None, "", "false", "0", "no", " OFF ", "garbage"]
G2_LOGGERS = ("cron_feed_walker", "kb_seed_common")
#: sha256 of the 24 feed hosts in walk order, one per line (recorded from the
#: spec's D09 1.3 list over the S81-15 seed rows; pinned by count and hash).
FEED_HOSTS_SHA256 = "89e900fc981880b2a25bcd4792caf5685dd44faa7451596301260b8b14c5bcb6"
SHOP = "store-s.example.com"
WOO = "store-w.example.com"


def _mod(name):
    spec = importlib.util.find_spec("scripts." + name)
    assert spec is not None, "scripts/%s.py does not exist (S81-G2 not implemented)" % name
    return importlib.import_module("scripts." + name)


def _attr(mod, name):
    assert hasattr(mod, name), "%s.%s is missing" % (mod.__name__, name)
    return getattr(mod, name)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in ("ENABLE_FEED_WALKER", "FEED_WALKER_MAX_PAGES", "FEED_WALKER_CURRENCY_PROBES",
                 "ENABLE_DATA_GUARDS_V2"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://" + "feedwalker-test" + ".invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc" + "-" + "y" * 10)
    yield


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _fx():
    return json.loads(FIXTURE.read_text(encoding="ascii"))


class _Resp:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    OPS = ("select", "eq", "in_", "order", "range", "upsert", "insert", "update", "delete", "limit")

    def __init__(self, client, table):
        self.client, self.table, self.ops = client, table, []

    def __getattr__(self, name):
        if name not in FakeQuery.OPS:
            raise AttributeError(name)

        def op(*a, **k):
            self.ops.append((name, a, k))
            return self
        return op

    def kind(self):
        for name, _, _ in self.ops:
            if name in ("select", "upsert", "insert", "update", "delete"):
                return name
        return "?"

    def arg(self, name):
        return [(a, k) for n, a, k in self.ops if n == name]

    def execute(self):
        self.client.events.append(("db", self.table, self.kind()))
        self.client.executed.append(self)
        if self.client.fail is not None and self.client.fail(self):
            raise RuntimeError("fake-db-failure")
        kind = self.kind()
        if kind == "select" and self.table == "kb_merchants":
            (a, _), = self.arg("range")
            return _Resp(self.client.merchants[a[0]:a[1] + 1])
        if kind == "upsert":
            (a, _), = self.arg("upsert")
            rows = list(a[0])
            return _Resp(rows if self.client.returned is None else self.client.returned(self, rows))
        return _Resp([])


class FakeClient:
    def __init__(self, events, merchants=(), returned=None, fail=None):
        self.events, self.merchants, self.returned, self.fail = events, list(merchants), returned, fail
        self.executed = []

    def table(self, name):
        return FakeQuery(self, name)

    def rows(self, table, kind="upsert"):
        out = []
        for q in self.executed:
            if q.table == table and q.kind() == kind:
                (a, _), = q.arg(kind)
                out.extend(a[0] if isinstance(a[0], list) else [a[0]])
        return out


def _robots(origin, body="User-agent: *\nAllow: /\n", at=NOW, crawl_delay="keep"):
    from app.services import robots_registry as rr

    rec = rr.robots_record(rr.decide_robots(200, {}, body, [origin + "/"]), at, origin, "datacenter")
    if crawl_delay != "keep":
        rec["crawl_delay"] = crawl_delay
    return rec


def _entry(host, mechanism, tier="bahrain", currency="BHD", rank=5):
    return {"origin": "catalog", "order": 1000, "domain": host, "tier": tier, "categories": ["fragrances"],
            "weight": 1.0, "mechanism": mechanism, "currency": currency, "priority_rank": rank}


def _merchant(host, mechanism="shopify", tos="allowed", robots=None, currency_hint="BHD", entry_currency="BHD",
              country="BH", tier="bahrain", rank=5, origin=None):
    from app.services import kb_service as kb

    origin = origin or ("https://" + host)
    row = kb.build_merchant_row(host=host, updated_at=NOW, country=country, currency_hint=currency_hint,
                                registry=[_entry(host, mechanism, tier=tier, currency=entry_currency, rank=rank)],
                                robots=_robots(origin) if robots is None else robots,
                                tos={} if tos is None else ({"verdict": tos} if isinstance(tos, str) else tos),
                                status="live")
    assert row is not None
    return row


def _shop_product(i=0, **kw):
    p = copy.deepcopy(_fx()["shopify_product"])
    p["id"] = 1000 + i
    p["handle"] = "%s-%d" % (p["handle"], i)
    word = chr(97 + i % 26) * 2 + chr(97 + (i // 26) % 26) * 2
    p["title"] = p["title"].replace("Night Oud", "Night Oud " + word)
    for k, v in kw.items():
        p[k] = v
    return p


def _woo_product(**kw):
    p = copy.deepcopy(_fx()["woo_product"])
    for k, v in kw.items():
        if k == "prices":
            p["prices"].update(v)
        else:
            p[k] = v
    return p


class Rig:
    def __init__(self, monkeypatch, common, merchants=(), routes=None, clock=None, returned=None, fail=None):
        self.events = []
        self.client = FakeClient(self.events, merchants, returned=returned, fail=fail)
        self.fetches, self.validates, self.sleeps = [], [], []
        self.routes = routes or {}
        self.in_flight = 0
        self.max_in_flight = 0
        self.client_factory_calls = []
        self.pf_kwargs = []
        rig = self

        def factory():
            rig.client_factory_calls.append(1)
            return rig.client
        monkeypatch.setattr(common, "_admin_client", factory)
        monkeypatch.setattr(common, "_now", clock or (lambda: NOW))
        orig = common.PoliteFetcher

        def _pf(*a, **k):
            rig.pf_kwargs.append(dict(k))
            k.setdefault("fetch", rig.fetch)
            k.setdefault("validate", rig.validate)
            k.setdefault("sleep", rig.sleep)
            return orig(*a, **k)
        monkeypatch.setattr(common, "PoliteFetcher", _pf)

    async def fetch(self, url, headers=None, timeout=None, allow_redirects=None):
        import asyncio

        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0)
        self.in_flight -= 1
        self.fetches.append({"url": url, "headers": headers, "allow_redirects": allow_redirects})
        self.events.append(("fetch", url))
        for prefix, resp in self.routes.items():
            if url.startswith(prefix):
                return resp(url) if callable(resp) else resp
        return 404, {}, ""

    async def validate(self, url):
        self.validates.append(url)
        return "ok"

    async def sleep(self, seconds):
        self.sleeps.append(seconds)

    def urls(self):
        return [f["url"] for f in self.fetches]


def _shop_page(products):
    return 200, {"content-type": "application/json"}, json.dumps({"products": products})


def _woo_page(products):
    return 200, {"content-type": "application/json"}, json.dumps(products)


def _run(mod, mode, monkeypatch, argv=None):
    monkeypatch.setenv("ENABLE_FEED_WALKER", mode)
    return _attr(mod, "main")(argv or [])


def _report(path):
    return json.loads(Path(path).read_text(encoding="ascii"))


def _host_report(path, host):
    (h,) = [h for h in _report(path)["hosts"] if h["host"] == host]
    return h


def _mods():
    return _mod("kb_seed_common"), _mod("cron_feed_walker")


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

MODE_TABLE = [(None, "off"), ("", "off"), ("false", "off"), ("0", "off"), ("no", "off"), (" OFF ", "off"),
              ("garbage", "off"), ("true", "dry"), ("1", "dry"), ("yes", "dry"), ("on", "dry"),
              (" TRUE ", "dry"), ("apply", "apply"), (" APPLY ", "apply"), ("dry", "off")]


@pytest.mark.parametrize("value,expected", MODE_TABLE)
def test_d09_r01_mode_table(monkeypatch, value, expected):
    common, fw = _mods()
    _set(monkeypatch, "ENABLE_FEED_WALKER", value)
    assert _attr(fw, "feed_walker_mode")() == expected
    monkeypatch.setenv("ENABLE_FEED_WALKER", "apply")
    assert fw.feed_walker_mode() == "apply"


@pytest.mark.parametrize("value", OFF_SPELLINGS)
def test_d09_r02_off_inert_full_config(monkeypatch, caplog, value):
    common, fw = _mods()
    monkeypatch.setenv("FEED_WALKER_MAX_PAGES", "3")
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "2")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP)], routes={"https://": _shop_page([])})
    _set(monkeypatch, "ENABLE_FEED_WALKER", value)
    caplog.set_level(logging.INFO)
    assert _attr(fw, "main")(["--report", "unused.json"]) == 0
    recs = [r for r in caplog.records if r.name in G2_LOGGERS]
    assert len(recs) == 1 and recs[0].levelno == logging.INFO and "ENABLE_FEED_WALKER" in recs[0].getMessage()
    assert rig.client_factory_calls == [] and rig.events == [] and rig.fetches == [] and rig.sleeps == []


def _seed_rows():
    import app.services.source_router as sr
    from app.services import merchant_registry as mr

    json_rows = json.loads((ROOT / "data" / "bh_gcc_sources.json").read_text(encoding="utf-8"))
    rows = mr.build_seed_rows(list(sr._LITERAL_ROWS), json_rows, NOW)
    out = []
    for row in rows:
        row = dict(row)
        if row.get("status") == "live":
            row["tos"] = {"verdict": "allowed"}
            row["robots"] = _robots("https://" + row["host"])
        out.append(row)
    return out


def test_d09_r03_host_selection_and_order(monkeypatch, tmp_path):
    common, fw = _mods()
    rows = _seed_rows()
    picked = _attr(fw, "select_hosts")(rows)
    hosts = [r["host"] for r, _ in picked]
    mechs = [e["mechanism"] for _, e in picked]
    assert len(hosts) == 24 and len(set(hosts)) == 24
    assert mechs.count("shopify") == 9 and mechs.count("woo_store_json") == 10
    assert len([m for m in mechs if m not in ("shopify", "woo_store_json")]) == 5
    assert hashlib.sha256("\n".join(hosts).encode("ascii")).hexdigest() == FEED_HOSTS_SHA256
    assert picked[0][1]["tier"] == "bahrain"
    rig = Rig(monkeypatch, common, merchants=rows)
    rep = tmp_path / "r.json"
    assert _run(fw, "true", monkeypatch, ["--report", str(rep)]) == 0
    no_reader = [h for h in _report(rep)["hosts"] if h["reason"] == "no_reader"]
    assert len(no_reader) == 5
    for h in no_reader:
        assert not [u for u in rig.urls() if h["host"] in u]


@pytest.mark.parametrize("tos,walked,currency", [({}, False, "BHD"), ({"verdict": "pending"}, False, "BHD"),
                                                 ({"verdict": "pending"}, False, None),
                                                 ({"verdict": "allowed"}, True, "BHD")])
def test_d09_r04_tos_gate(monkeypatch, tmp_path, tos, walked, currency):
    common, fw = _mods()
    # spec 2.2 order: no_reader, then tos, then currency_unknown (a ToS-less host with no currency reads tos)
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP, tos=tos, currency_hint=currency,
                                                        entry_currency=currency or "")],
              routes={"https://" + SHOP + "/products.json": _shop_page([_shop_product()])})
    rep = tmp_path / "r.json"
    assert _run(fw, "true", monkeypatch, ["--report", str(rep)]) == 0
    h = _host_report(rep, SHOP)
    if walked:
        assert h["reason"] == "ok" and rig.fetches
    else:
        assert h["reason"] == "tos" and rig.fetches == []
    # the per-URL gate also requires the ToS verdict (spec 2.2: url_gate(..., require_tos=True))
    assert rig.pf_kwargs and all(k.get("require_tos") is True for k in rig.pf_kwargs)


@pytest.mark.parametrize("case", ["qarenbot_disallow", "star_disallow", "hop_disallowed", "stale", "www_origin"])
def test_d09_r05_robots_gate_per_url(monkeypatch, tmp_path, case):
    common, fw = _mods()
    origin = "https://" + SHOP
    robots, routes = None, {origin + "/products.json": _shop_page([_shop_product()])}
    if case == "qarenbot_disallow":
        robots = _robots(origin, "User-agent: " + "Qaren" + "Bot" + "\nDisallow: /products.json\n")
    elif case == "star_disallow":
        robots = _robots(origin, "User-agent: *\nDisallow: /products.json\n")
    elif case == "hop_disallowed":
        robots = _robots(origin, "User-agent: *\nDisallow: /blocked\n")
        routes = {origin + "/products.json": (302, {"location": origin + "/blocked/feed"}, "")}
    elif case == "stale":
        robots = _robots(origin, at=NOW - timedelta(hours=72))
    elif case == "www_origin":
        origin = "https://www." + SHOP
        robots = _robots(origin)
        routes = {origin + "/products.json": _shop_page([_shop_product()]),
                  origin + "/products/": (404, {}, "")}
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP, robots=robots)], routes=routes)
    rep = tmp_path / "r.json"
    assert _run(fw, "true", monkeypatch, ["--report", str(rep)]) == 0
    h = _host_report(rep, SHOP)
    if case == "hop_disallowed":
        assert len(rig.fetches) == 1 and h["reason"] != "ok"
    elif case == "www_origin":
        assert rig.fetches and all(u.startswith(origin + "/") for u in rig.urls())
        assert h["reason"] == "ok" and h["kept"] == 1
    else:
        assert rig.fetches == [] and h["reason"] == "robots"


@pytest.mark.parametrize("delay,wait", [(5, 5.0), (0.5, 2.0), (90, 60.0), (None, 2.0)])
def test_d09_r06_politeness_and_concurrency(monkeypatch, tmp_path, delay, wait):
    common, fw = _mods()
    origin = "https://" + SHOP
    products = [_shop_product(i) for i in range(3)]
    routes = {origin + "/products.json": _shop_page(products),
              origin + "/products/": (200, {}, json.dumps({"product": {"variants": [{"price_currency": "BHD"}]}}))}
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP, robots=_robots(origin, crawl_delay=delay))],
              routes=routes)
    assert _run(fw, "true", monkeypatch) == 0
    assert len(rig.fetches) == 4
    assert rig.sleeps == [wait] * 3
    assert rig.max_in_flight == 1


def test_d09_r07_named_ua_no_redirect_ssrf(monkeypatch, tmp_path):
    common, fw = _mods()
    from app.services import robots_registry as rr

    origin = "https://" + SHOP
    routes = {origin + "/products.json?limit=250&page=1": (301, {"location": origin + "/feed/products.json"}, ""),
              origin + "/feed/products.json": _shop_page([_shop_product()])}
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP)], routes=routes)
    assert _run(fw, "true", monkeypatch) == 0
    assert len(rig.fetches) == 2
    assert all(f["headers"] == rr._REQUEST_HEADERS and f["allow_redirects"] is False for f in rig.fetches)
    assert rig.validates == rig.urls()


@pytest.mark.parametrize("sizes,cap,expected", [((250, 250, 3), None, 3), ((250, 250, 250), "2", 2), ((0,), None, 1)])
def test_d09_r08_shopify_pagination(monkeypatch, sizes, cap, expected):
    common, fw = _mods()
    origin = "https://" + SHOP
    pages = {n + 1: [_shop_product(i) for i in range(s)] for n, s in enumerate(sizes)}

    def route(url):
        n = int(url.rsplit("page=", 1)[1])
        return _shop_page(pages.get(n, []))
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    _set(monkeypatch, "FEED_WALKER_MAX_PAGES", cap)
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP)], routes={origin + "/products.json": route})
    assert _run(fw, "true", monkeypatch) == 0
    assert rig.urls() == ["%s/products.json?limit=250&page=%d" % (origin, n) for n in range(1, expected + 1)]


def test_d09_r09_currency_blind_rule(monkeypatch, tmp_path):
    common, fw = _mods()
    other = "store-x.example.com"
    rows = [_merchant(SHOP, currency_hint="QAR", entry_currency="QAR", country="QA"),
            _merchant(other, currency_hint=None, entry_currency="")]
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=rows,
              routes={"https://" + SHOP + "/products.json": _shop_page([_shop_product()]),
                      "https://" + other: _shop_page([_shop_product()])})
    rep = tmp_path / "r.json"
    assert _run(fw, "apply", monkeypatch, ["--report", str(rep)]) == 0
    offers = rig.client.rows("kb_offers")
    assert offers and {o["observed_currency"] for o in offers} == {"QAR"}
    assert {o["evidence_rung"] for o in offers} == {"expected_missing"}
    assert _host_report(rep, other)["reason"] == "currency_unknown"
    assert not [u for u in rig.urls() if other in u]
    assert _attr(common, "row_currency")(rows[1]) is None


@pytest.mark.parametrize("case", ["agree", "disagree", "probe404", "probes0"])
def test_d09_r10_currency_probe(monkeypatch, tmp_path, case):
    common, fw = _mods()
    origin = "https://" + SHOP
    probe = {"agree": (200, {}, json.dumps({"product": {"variants": [{"price_currency": "BHD"}]}})),
             "disagree": (200, {}, json.dumps({"product": {"variants": [{"price_currency": "AED"}]}})),
             "probe404": (404, {}, ""), "probes0": (404, {}, "")}[case]
    if case == "probes0":
        monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP)],
              routes={origin + "/products.json": _shop_page([_shop_product(0), _shop_product(1)]),
                      origin + "/products/": probe})
    rep = tmp_path / "r.json"
    assert _run(fw, "apply", monkeypatch, ["--report", str(rep)]) == 0
    h = _host_report(rep, SHOP)
    probes = [u for u in rig.urls() if "/products/" in u and u.endswith(".json")]
    if case == "disagree":
        assert h["reason"] == "currency_disagrees"
        assert not [q for q in rig.client.executed if q.table.startswith("kb_") and q.table != "kb_merchants"]
        return
    assert h["reason"] == "ok" and rig.client.rows("kb_offers")
    assert len(probes) == (0 if case == "probes0" else 2)
    assert ("currency_unprobed" in h["notes"]) == (case == "probe404")


R11 = [
    ("bhd3", {"price": "12500", "regular_price": "12500", "sale_price": "12500", "currency_code": "BHD",
              "currency_minor_unit": 3}, "BHD", ("12.5", "BHD", "platform_api")),
    ("aed0", {"price": "199", "regular_price": "199", "sale_price": "199", "currency_code": "AED",
              "currency_minor_unit": 0}, "BHD", ("199", "AED", "platform_api")),
    ("code_missing", {"price": "1500", "regular_price": "1500", "sale_price": "1500", "currency_code": "",
                      "currency_minor_unit": 2}, "OMR", ("15", "OMR", "expected_missing")),
    ("all_missing", {"price": "1500", "regular_price": "1500", "sale_price": "1500", "currency_code": "",
                     "currency_minor_unit": 2}, None, None),
    ("spread", {"price": None, "regular_price": None, "sale_price": None,
                "price_range": {"min_amount": "5000", "max_amount": "30000"}, "currency_code": "BHD",
                "currency_minor_unit": 3}, "BHD", "variable_spread"),
]


@pytest.mark.parametrize("case,prices,row_cur,want", R11)
def test_d09_r11_woo_amount_currency(monkeypatch, tmp_path, case, prices, row_cur, want):
    common, fw = _mods()
    row = _merchant(WOO, mechanism="woo_store_json", currency_hint=row_cur, entry_currency=row_cur or "")
    rig = Rig(monkeypatch, common, merchants=[row],
              routes={"https://" + WOO + "/wp-json/wc/store/products": _woo_page([_woo_product(prices=prices)])})
    rep = tmp_path / "r.json"
    assert _run(fw, "apply", monkeypatch, ["--report", str(rep)]) == 0
    offers = rig.client.rows("kb_offers")
    h = _host_report(rep, WOO)
    if want is None:
        assert offers == [] and h["reason"] == "currency_unknown"
    elif want == "variable_spread":
        assert offers == [] and h["counts"].get("variable_spread") == 1
    else:
        (o,) = offers
        assert Decimal(o["amount"]) == Decimal(want[0])
        assert (o["observed_currency"], o["evidence_rung"]) == want[1:]


def test_d09_r12_list_and_sale_pair(monkeypatch, tmp_path):
    common, fw = _mods()
    sale_shop = _shop_product(0)
    sale_shop["variants"][0]["compare_at_price"] = "60.000"
    plain_shop = _shop_product(1)
    woo_sale = _woo_product(prices={"price": "10000", "regular_price": "12500", "sale_price": "10000",
                                    "currency_code": "BHD", "currency_minor_unit": 3})
    ticks = [0]

    def clock():
        ticks[0] += 1
        return NOW + timedelta(seconds=ticks[0])
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP), _merchant(WOO, mechanism="woo_store_json")],
              routes={"https://" + SHOP + "/products.json": _shop_page([sale_shop, plain_shop]),
                      "https://" + WOO + "/wp-json": _woo_page([woo_sale])}, clock=clock)
    assert _run(fw, "apply", monkeypatch) == 0
    offers = rig.client.rows("kb_offers")
    shop = [o for o in offers if o["merchant_id"] == SHOP]
    by_variant = {}
    for o in shop:
        by_variant.setdefault(o["variant_id"], []).append(o)
    kinds = sorted(sorted(o["list_vs_sale"] for o in v) for v in by_variant.values())
    assert kinds == [["list", "sale"], ["unknown"]]
    pair = [v for v in by_variant.values() if len(v) == 2][0]
    assert {Decimal(o["amount"]) for o in pair} == {Decimal("45"), Decimal("60")}
    assert len({o["last_seen"] for o in pair}) == 1
    woo = sorted((o for o in offers if o["merchant_id"] == WOO), key=lambda o: o["list_vs_sale"])
    assert [(o["list_vs_sale"], Decimal(o["amount"])) for o in woo] == [("list", Decimal("12.5")), ("sale", Decimal("10"))]
    assert len({o["last_seen"] for o in woo}) == 1


def test_d09_r13_fragrance_and_guards(monkeypatch, tmp_path):
    common, fw = _mods()
    products = [_shop_product(0, title="Leather Wallet", product_type="Accessories", tags=[]),
                _shop_product(1, title="Perfume Atomizer Travel Case"),
                _shop_product(2, title="Replica Night Oud Eau de Parfum 100ml")]
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP)],
              routes={"https://" + SHOP + "/products.json": _shop_page(products)})
    rep = tmp_path / "r.json"
    assert _run(fw, "apply", monkeypatch, ["--report", str(rep)]) == 0
    assert not [q for q in rig.client.executed if q.kind() == "upsert"]
    c = _host_report(rep, SHOP)["counts"]
    assert c.get("non_fragrance") == 1 and c.get("accessory") == 1 and c.get("counterfeit") == 1


def _gtin(stem):
    total = sum(int(d) * (3 if (len(stem) + 1 - i) % 2 == 1 else 1) for i, d in enumerate(stem, start=1))
    return stem + str((10 - total % 10) % 10)


def test_d09_r14_identity(monkeypatch, tmp_path):
    common, fw = _mods()
    from app.services import kb_service as kb

    good = _gtin("6291" + "1" + "0" * 6 + "2")
    bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    p_good = _shop_product(0)
    p_good["variants"][0]["barcode"] = good
    p_bad = _shop_product(1)
    p_bad["variants"][0]["barcode"] = bad
    p_nobrand = _shop_product(2, vendor="")
    p_unknown = _shop_product(3, vendor="Unknown")
    woo = _woo_product()
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP), _merchant(WOO, mechanism="woo_store_json")],
              routes={"https://" + SHOP + "/products.json": _shop_page([p_good, p_bad, p_nobrand, p_unknown]),
                      "https://" + WOO + "/wp-json": _woo_page([woo])})
    rep = tmp_path / "r.json"
    assert _run(fw, "apply", monkeypatch, ["--report", str(rep)]) == 0
    c = _host_report(rep, SHOP)["counts"]
    assert c.get("no_brand") == 1 and c.get("no_identity") == 1
    prods = {p["id"]: p for p in rig.client.rows("kb_products")}
    pid_good = kb.kb_product_id(p_good["vendor"], p_good["title"])
    pid_bad = kb.kb_product_id(p_bad["vendor"], p_bad["title"])
    pid_woo = kb.kb_product_id("Brand Bee", woo["name"])
    assert prods[pid_good]["identity_confidence"] == "high" and prods[pid_bad]["identity_confidence"] == "medium"
    assert pid_woo in prods and prods[pid_woo]["brand"] == "Brand Bee"
    variants = {v["id"]: v for v in rig.client.rows("kb_variants")}
    vid_good = kb.kb_variant_key(pid_good, "EDP", 100)
    assert variants[vid_good]["gtin"] == good and variants[vid_good]["size_ml"] == 100
    assert variants[kb.kb_variant_key(pid_bad, "EDP", 100)]["gtin"] is None


def test_d09_r15_offer_row_fields(monkeypatch, tmp_path):
    common, fw = _mods()
    from app.services import kb_service as kb

    origin = "https://www." + SHOP
    ticks = [0]

    def clock():
        ticks[0] += 1
        return NOW + timedelta(seconds=ticks[0])
    page1 = [_shop_product(i) for i in range(250)]
    page2 = [_shop_product(250)]
    page2[0]["variants"][0]["available"] = False

    def route(url):
        return _shop_page(page1 if url.endswith("page=1") else page2)
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP, robots=_robots(origin), country="BH")],
              routes={origin + "/products.json": route}, clock=clock)
    assert _run(fw, "apply", monkeypatch) == 0
    offers = rig.client.rows("kb_offers")
    assert len(offers) == 251
    o0 = [o for o in offers if o["canonical_url"].endswith("/" + page1[0]["handle"])][0]
    assert o0["market"] == "BH" and o0["merchant_id"] == SHOP
    assert o0["canonical_url"] == kb.canonical_offer_url(origin + "/products/" + page1[0]["handle"])
    assert o0["in_stock"] is True
    for o in offers:
        assert o["captured_at"] == o["first_seen"] == o["last_seen"]
    times = {o["captured_at"] for o in offers}
    assert len(times) == 2
    last = [o for o in offers if o["canonical_url"].endswith("/" + page2[0]["handle"])][0]
    assert last["in_stock"] is False


def test_d09_r16_dry_writes_nothing_apply_order(monkeypatch, tmp_path):
    common, fw = _mods()
    from app.services import kb_service as kb

    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    routes = {"https://" + SHOP + "/products.json": _shop_page([_shop_product(0), _shop_product(1)])}
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP)], routes=routes)
    assert _run(fw, "true", monkeypatch) == 0
    assert {(q.table, q.kind()) for q in rig.client.executed} == {("kb_merchants", "select")}

    def returned(q, rows):
        return [] if q.table == "kb_offers" else rows
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP)], routes=routes, returned=returned)
    assert _run(fw, "apply", monkeypatch) == 0
    seq = [(q.table, q.kind()) for q in rig.client.executed if q.table != "kb_merchants"]
    n = len(rig.client.rows("kb_offers"))
    assert n == 2
    assert seq == [("kb_products", "upsert"), ("kb_variants", "upsert"), ("kb_offers", "upsert")] + \
        [("kb_offers", "update")] * n
    (up,) = [q for q in rig.client.executed if q.table == "kb_offers" and q.kind() == "upsert"]
    assert up.arg("upsert")[0][1] == {"on_conflict": ",".join(kb.KB_OFFER_OBSERVATION_KEY), "ignore_duplicates": True}
    for q in rig.client.executed:
        if q.kind() == "update":
            (a, _), = q.arg("update")
            assert set(a[0]) == set(kb.KB_OFFER_UPSERT_SET)
            assert sorted(x[0][0] for x in q.arg("eq")) == sorted(kb.KB_OFFER_OBSERVATION_KEY)


@pytest.mark.parametrize("case,reason", [("429", "throttled"), ("503", "throttled"), ("challenge", "challenge"),
                                         ("html", "bad_feed")])
def test_d09_r17_throttle_challenge_badfeed(monkeypatch, tmp_path, case, reason):
    common, fw = _mods()
    first = {"429": (429, {}, ""), "503": (503, {}, ""),
             "challenge": (200, {"cf-mitigated": "challenge", "content-type": "text/html"}, "<html>wait</html>"),
             "html": (200, {"content-type": "text/html"}, "<html><body>store</body></html>")}[case]
    other = "store-t.example.com"
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP, rank=1), _merchant(other, rank=2)],
              routes={"https://" + SHOP + "/products.json": first,
                      "https://" + other + "/products.json": _shop_page([_shop_product()])})
    rep = tmp_path / "r.json"
    assert _run(fw, "true", monkeypatch, ["--report", str(rep)]) == 0
    assert _host_report(rep, SHOP)["reason"] == reason
    assert len([u for u in rig.urls() if SHOP in u and other not in u]) == 1
    assert _host_report(rep, other)["reason"] == "ok"


@pytest.mark.parametrize("mode", ["true", "apply"])
def test_d09_r18_tables_written(monkeypatch, mode):
    common, fw = _mods()
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP), _merchant(WOO, mechanism="woo_store_json")],
              routes={"https://" + SHOP + "/products.json": _shop_page([_shop_product()]),
                      "https://" + WOO + "/wp-json": _woo_page([_woo_product()])})
    assert _run(fw, mode, monkeypatch) == 0
    for q in rig.client.executed:
        assert q.table not in ("kb_images", "kb_specs", "kb_reviews", "kb_gaps")
        assert not (q.table == "kb_merchants" and q.kind() != "select")
    if mode == "apply":
        assert {q.table for q in rig.client.executed} >= {"kb_products", "kb_variants", "kb_offers"}


def test_d09_r19_report(monkeypatch, tmp_path, caplog):
    common, fw = _mods()
    from app.services import kb_service as kb

    word = "Zqxv" + "wort"
    price = "77.7" + "77"
    products = [_shop_product(i) for i in range(7)]
    products[0]["title"] = "Night Oud %s Eau de Parfum 100ml" % word
    products[0]["variants"][0]["price"] = price
    other = "store-t.example.com"
    shared = _shop_product(0)
    shared["title"] = products[0]["title"]
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "0")
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP, rank=1), _merchant(other, rank=2)],
              routes={"https://" + SHOP + "/products.json": _shop_page(products),
                      "https://" + other + "/products.json": _shop_page([shared])})
    caplog.set_level(logging.DEBUG)
    rep = tmp_path / "r.json"
    assert _run(fw, "true", monkeypatch, ["--report", str(rep)]) == 0
    r = _report(rep)
    h = _host_report(rep, SHOP)
    assert h["kept"] == 7 and len(h["samples"]) == 5 and h["offers"] == 7
    pid = kb.kb_product_id(products[0]["vendor"], products[0]["title"])
    ranking = r["ranking"]
    assert ranking[0] == {"pid": pid, "merchants": 2}
    assert [x["merchants"] for x in ranking] == sorted((x["merchants"] for x in ranking), reverse=True)
    ones = [x["pid"] for x in ranking if x["merchants"] == 1]
    assert ones == sorted(ones)
    for rec in caplog.records:
        msg = rec.getMessage()
        assert word not in msg and price not in msg
    assert rig.fetches


def test_d09_r20_railway_feedwalker():
    path = ROOT / "railway.feedwalker.json"
    assert path.is_file(), "railway.feedwalker.json is missing"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    assert cfg["deploy"]["startCommand"] == "python -m scripts.cron_feed_walker"
    assert cfg["deploy"]["restartPolicyType"] == "NEVER"
    assert {"scripts/cron_feed_walker.py", "scripts/kb_seed_common.py", "railway.feedwalker.json"} <= set(
        cfg["build"]["watchPatterns"])


R21 = [
    ("FEED_WALKER_MAX_PAGES", None, 40), ("FEED_WALKER_MAX_PAGES", "", 40), ("FEED_WALKER_MAX_PAGES", "garbage", 40),
    ("FEED_WALKER_MAX_PAGES", "inf", 40), ("FEED_WALKER_MAX_PAGES", "nan", 40), ("FEED_WALKER_MAX_PAGES", "-3", 40),
    ("FEED_WALKER_MAX_PAGES", "0", 40), ("FEED_WALKER_MAX_PAGES", "999", 200), ("FEED_WALKER_MAX_PAGES", "7", 7),
    ("FEED_WALKER_CURRENCY_PROBES", None, 3), ("FEED_WALKER_CURRENCY_PROBES", "garbage", 3),
    ("FEED_WALKER_CURRENCY_PROBES", "nan", 3), ("FEED_WALKER_CURRENCY_PROBES", "-1", 3),
    ("FEED_WALKER_CURRENCY_PROBES", "0", 0), ("FEED_WALKER_CURRENCY_PROBES", "50", 10),
    ("FEED_WALKER_CURRENCY_PROBES", "1", 1),
]


@pytest.mark.parametrize("name,value,expected", R21)
def test_d09_r21_int_knobs_table(monkeypatch, name, value, expected):
    common, fw = _mods()
    reader = {"FEED_WALKER_MAX_PAGES": "max_pages", "FEED_WALKER_CURRENCY_PROBES": "currency_probes"}[name]
    _set(monkeypatch, name, value)
    assert _attr(fw, reader)() == expected
    if name != "FEED_WALKER_CURRENCY_PROBES" or value != "1":
        return
    origin = "https://" + SHOP
    rig = Rig(monkeypatch, common, merchants=[_merchant(SHOP)],
              routes={origin + "/products.json": _shop_page([_shop_product(i) for i in range(3)]),
                      origin + "/products/": (200, {}, json.dumps({"product": {"variants": [{"price_currency": "BHD"}]}}))})
    assert _run(fw, "true", monkeypatch) == 0
    assert len([u for u in rig.urls() if "/products/" in u and u.endswith(".json")]) == 1


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------

def _full_config(monkeypatch):
    monkeypatch.setenv("FEED_WALKER_MAX_PAGES", "3")
    monkeypatch.setenv("FEED_WALKER_CURRENCY_PROBES", "2")
    monkeypatch.delenv("ENABLE_FEED_WALKER", raising=False)


def test_d09_p01_amount_from_prices_table(monkeypatch):
    _full_config(monkeypatch)
    from app.services import woocommerce_service as ws

    assert ws._amount_from_prices({"price": "12500", "currency_minor_unit": 3, "currency_code": "BHD"}) == 12.5
    assert ws._amount_from_prices({"price": "1999", "currency_minor_unit": 2, "currency_code": "AED"}) == 19.99
    assert ws._amount_from_prices({"price": "199", "currency_minor_unit": 0, "currency_code": "AED"}) == 199
    assert ws._amount_from_prices({"price": "12500", "currency_code": "BHD"}) == 12.5
    assert ws._amount_from_prices({"price": "1999", "currency_code": "AED"}) == 19.99
    assert ws._amount_from_prices({"price": None, "price_range": {"min_amount": "5000", "max_amount": "9000"},
                                   "currency_minor_unit": 3}) == 5.0


def test_d09_p02_politeness_delays(monkeypatch):
    _full_config(monkeypatch)
    import asyncio

    from app.services import robots_registry as rr

    slept = []

    async def sleep(s):
        slept.append(s)
    pol = rr.Politeness(sleep)

    async def go():
        for d in (None, None, 5, 90):
            await pol.before_request(d)
    asyncio.run(go())
    assert slept == [2.0, 5.0, 60.0]


def test_d09_p03_offer_builder_refusals(monkeypatch):
    _full_config(monkeypatch)
    from app.services import kb_service as kb

    base = dict(variant_id="fragrances|maison+example|night+oud|EDP|100", merchant_id=SHOP, market="BH",
                amount=45.0, observed_currency="BHD", evidence_rung="expected_missing",
                canonical_url="https://%s/products/night-oud" % SHOP, captured_at=NOW)
    assert kb.build_offer_row(**base) is not None
    assert kb.build_offer_row(**dict(base, canonical_url="https://store-z.example.com/products/x")) is None
    assert kb.build_offer_row(**dict(base, evidence_rung="guessed")) is None
    assert kb.build_offer_row(**dict(base, canonical_url="https://%s/products/x?variant=1" % SHOP)) is None


def test_d09_p04_adapter_paths(monkeypatch):
    _full_config(monkeypatch)
    from app.services import robots_registry as rr

    assert rr.ADAPTER_PATHS["shopify"] == "/products.json"
    assert rr.ADAPTER_PATHS["woo_store_json"] == "/wp-json/wc/store/products"
