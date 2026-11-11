"""D11 PDP-DISCOVERY RED rows (spec S81-G2 section 5 of D11, as amended by
RULINGS_S81_G2): 16 RED rows + 4 PIN rows.

Hermetic: ``_mod`` asserts the module spec (AssertionError at base, never an
ImportError); robots bodies, sitemap XML and CDX lines come from
``tests/fixtures/s81_d11_sitemaps.json`` (synthetic hosts only); the client,
fetch, validator, sleep and clock are recorders.
"""
import hashlib
import importlib
import importlib.util
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "s81_d11_sitemaps.json"
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
OFF_SPELLINGS = [None, "", "false", "0", "no", " OFF ", "garbage"]
G2_LOGGERS = ("cron_pdp_discovery", "kb_seed_common")
#: sha256 of the 71 JSON-LD hosts in walk order (the spec's D11 1.3 list), one per line.
JSONLD_HOSTS_SHA256 = "b0da63d96079a13087725db9e0cd58d4a48f36155c04d79a6f83c317a0879961"
HOST = "store-d.example.com"
INDEX = "CC-MAIN-2026-40"


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

    for name in ("ENABLE_PDP_DISCOVERY", "ENABLE_CC_CDX", "KB_CC_INDEX", "PDP_DISCOVERY_MAX_HOSTS",
                 "PDP_DISCOVERY_MAX_JUICES", "PDP_DISCOVERY_MAX_CHILDREN", "ENABLE_SITEMAP_PDP_MARKERS_V2",
                 "ENABLE_SITEMAP_MATCH_V2"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://" + "pdpdisc-test" + ".invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc" + "-" + "z" * 10)
    yield


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _fx():
    return json.loads(FIXTURE.read_text(encoding="ascii"))


def _sub(text, host):
    return text.replace("{host}", host)


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
        self.client.executed.append(self)
        kind = self.kind()
        if kind == "select" and self.table == "kb_merchants":
            (a, _), = self.arg("range")
            return _Resp(self.client.merchants[a[0]:a[1] + 1])
        if kind == "select" and self.table == "kb_offers":
            (a, _), = self.arg("range")
            return _Resp(self.client.offers[a[0]:a[1] + 1])
        if kind == "select" and self.table == "kb_products":
            ids = self.arg("in_")[0][0][1]
            return _Resp([p for p in self.client.products if p["id"] in ids])
        if kind == "upsert":
            (a, _), = self.arg("upsert")
            rows = list(a[0])
            return _Resp(rows if self.client.returned is None else self.client.returned(self, rows))
        return _Resp([])


class FakeClient:
    def __init__(self, merchants=(), offers=(), products=(), returned=None):
        self.merchants, self.offers, self.products = list(merchants), list(offers), list(products)
        self.returned = returned
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


def _robots(origin, body="User-agent: *\nAllow: /\n", at=NOW):
    from app.services import robots_registry as rr

    return rr.robots_record(rr.decide_robots(200, {}, body, [origin + "/"]), at, origin, "datacenter")


def _merchant(host, tier="gcc", rank=5, robots=None, origin="catalog", mechanism="", render_only=False, status="live"):
    from app.services import kb_service as kb

    entry = {"origin": origin, "order": 1000, "domain": host, "tier": tier, "categories": ["fragrances"],
             "weight": 1.0, "mechanism": mechanism, "currency": "AED", "priority_rank": rank,
             "is_render_only": render_only}
    row = kb.build_merchant_row(host=host, updated_at=NOW, country="AE", currency_hint="AED", registry=[entry],
                                robots=_robots("https://" + host) if robots is None else robots, status=status)
    assert row is not None
    return row


def _juices(*specs):
    """specs: (brand, name, merchant count) -> (offers, products)."""
    from app.services import kb_service as kb

    offers, products = [], []
    for brand, name, n in specs:
        pid = kb.kb_product_id(brand, name)
        products.append({"id": pid, "brand": brand, "name": name})
        for i in range(n):
            offers.append({"variant_id": pid + "|100", "merchant_id": "m%d.example.com" % i})
    return offers, products


class Rig:
    def __init__(self, monkeypatch, common, merchants=(), routes=None, offers=(), products=(), returned=None):
        self.client = FakeClient(merchants, offers, products, returned=returned)
        self.fetches, self.validates, self.sleeps = [], [], []
        self.routes = routes or {}
        self.in_flight = self.max_in_flight = 0
        self.client_factory_calls = []
        rig = self

        def factory():
            rig.client_factory_calls.append(1)
            return rig.client
        monkeypatch.setattr(common, "_admin_client", factory)
        monkeypatch.setattr(common, "_now", lambda: NOW)
        orig = common.PoliteFetcher

        def _pf(*a, **k):
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
        for prefix, resp in sorted(self.routes.items(), key=lambda kv: -len(kv[0])):
            if url.startswith(prefix):
                resp = resp(url) if callable(resp) else resp
                if isinstance(resp, Exception):
                    raise resp
                return resp
        return 404, {}, ""

    async def validate(self, url):
        self.validates.append(url)
        return "ok"

    async def sleep(self, seconds):
        self.sleeps.append(seconds)

    def urls(self):
        return [f["url"] for f in self.fetches]


def _ok(body, ctype="application/xml"):
    return 200, {"content-type": ctype}, body


def _std_routes(host=HOST, urls=None):
    fx = _fx()
    origin = "https://" + host
    urlset = fx["urlset"].replace("{locs}", "".join("<url><loc>%s</loc></url>" % u for u in (urls or [
        origin + "/products/maison-example-night-oud-eau-de-parfum-100ml"])))
    return {origin + "/robots.txt": _ok(_sub(fx["robots_one"], host), "text/plain"),
            origin + "/sitemap_products.xml": _ok(urlset)}


def _run(mod, mode, monkeypatch, argv=None):
    monkeypatch.setenv("ENABLE_PDP_DISCOVERY", mode)
    return _attr(mod, "main")(argv or [])


def _report(path):
    return json.loads(Path(path).read_text(encoding="ascii"))


def _host_report(path, host=HOST):
    (h,) = [h for h in _report(path)["hosts"] if h["host"] == host]
    return h


def _mods():
    return _mod("kb_seed_common"), _mod("cron_pdp_discovery")


NIGHT = ("Maison Example", "Night Oud Eau de Parfum 100ml")


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

MODE_TABLE = [(None, "off", False), ("", "off", False), ("false", "off", False), ("0", "off", False),
              ("no", "off", False), (" OFF ", "off", False), ("garbage", "off", False), ("true", "dry", True),
              ("1", "dry", True), ("yes", "dry", True), ("on", "dry", True), (" ON ", "dry", True),
              ("apply", "apply", False), (" APPLY ", "apply", False), ("dry", "off", False)]


@pytest.mark.parametrize("value,mode,cdx", MODE_TABLE)
def test_d11_r01_mode_and_subflag(monkeypatch, value, mode, cdx):
    common, pd = _mods()
    _set(monkeypatch, "ENABLE_PDP_DISCOVERY", value)
    _set(monkeypatch, "ENABLE_CC_CDX", value)
    assert _attr(pd, "pdp_discovery_mode")() == mode
    assert _attr(pd, "cc_cdx_enabled")() is cdx
    monkeypatch.setenv("ENABLE_CC_CDX", "true")
    assert pd.cc_cdx_enabled() is True
    monkeypatch.setenv("ENABLE_CC_CDX", "off")
    assert pd.cc_cdx_enabled() is False


@pytest.mark.parametrize("value", OFF_SPELLINGS)
def test_d11_r02_off_inert_full_config(monkeypatch, caplog, value):
    common, pd = _mods()
    monkeypatch.setenv("ENABLE_CC_CDX", "true")
    monkeypatch.setenv("KB_CC_INDEX", INDEX)
    for k, v in (("PDP_DISCOVERY_MAX_HOSTS", "3"), ("PDP_DISCOVERY_MAX_JUICES", "4"),
                 ("PDP_DISCOVERY_MAX_CHILDREN", "5")):
        monkeypatch.setenv(k, v)
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes())
    _set(monkeypatch, "ENABLE_PDP_DISCOVERY", value)
    caplog.set_level(logging.INFO)
    assert _attr(pd, "main")([]) == 0
    recs = [r for r in caplog.records if r.name in G2_LOGGERS]
    assert len(recs) == 1 and recs[0].levelno == logging.INFO and "ENABLE_PDP_DISCOVERY" in recs[0].getMessage()
    assert rig.client_factory_calls == [] and rig.client.executed == [] and rig.fetches == [] and rig.sleeps == []


def _seed_rows():
    import app.services.source_router as sr
    from app.services import merchant_registry as mr

    json_rows = json.loads((ROOT / "data" / "bh_gcc_sources.json").read_text(encoding="utf-8"))
    rows = mr.build_seed_rows(list(sr._LITERAL_ROWS), json_rows, NOW)
    for row in rows:
        if row.get("status") == "live":
            row["robots"] = _robots("https://" + row["host"])
    return rows


def test_d11_r03_host_selection(monkeypatch):
    common, pd = _mods()
    rows = _seed_rows()
    picked = _attr(pd, "select_hosts")(rows)
    hosts = [r["host"] for r in picked]
    assert len(hosts) == 71 and len(set(hosts)) == 71
    tiers = [common.registry_entries(r)[0]["tier"] for r in picked]
    assert tiers[:6] == ["bahrain"] * 6 and "bahrain" not in tiers[6:]
    for r in picked:
        (e,) = [e for e in common.registry_entries(r) if e.get("origin") == "catalog"][:1]
        assert e["mechanism"] == "" and not e.get("is_render_only")
    literal = {r["host"] for r in rows if any(e.get("origin") == "literal" for e in common.registry_entries(r))}
    assert not literal & set(hosts)
    assert hashlib.sha256("\n".join(hosts).encode("ascii")).hexdigest() == JSONLD_HOSTS_SHA256


R04 = ["two", "404", "403", "timeout", "offsite", "disallowed", "seven"]


@pytest.mark.parametrize("case", R04)
def test_d11_r04_robots_and_declared_sitemaps(monkeypatch, tmp_path, case):
    common, pd = _mods()
    fx = _fx()
    origin = "https://" + HOST
    record_body = "User-agent: *\nAllow: /\n"
    routes = {}
    empty = _ok(fx["urlset"].replace("{locs}", ""))
    if case == "two":
        routes[origin + "/robots.txt"] = _ok(_sub(fx["robots_two"], HOST), "text/plain")
    elif case == "404":
        routes[origin + "/robots.txt"] = (404, {}, "")
    elif case == "403":
        routes[origin + "/robots.txt"] = (403, {}, "no")
    elif case == "timeout":
        routes[origin + "/robots.txt"] = TimeoutError("t")
    elif case == "offsite":
        routes[origin + "/robots.txt"] = _ok("User-agent: *\nAllow: /\nSitemap: https://evil.example.net/sitemap.xml\n",
                                             "text/plain")
    elif case == "disallowed":
        record_body = "User-agent: *\nDisallow: /private\n"
        routes[origin + "/robots.txt"] = _ok(record_body + "Sitemap: %s/private/sitemap.xml\n" % origin, "text/plain")
    elif case == "seven":
        routes[origin + "/robots.txt"] = _ok("User-agent: *\n" + "".join(
            "Sitemap: %s/sitemap-%d.xml\n" % (origin, i) for i in range(7)), "text/plain")
    routes[origin + "/sitemap"] = empty
    routes[origin + "/private"] = empty
    routes["https://evil.example.net"] = empty
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST, robots=_robots(origin, record_body))], routes=routes)
    rep = tmp_path / "r.json"
    assert _run(pd, "true", monkeypatch, ["--report", str(rep)]) == 0
    sitemap_fetches = [u for u in rig.urls() if not u.endswith("/robots.txt")]
    h = _host_report(rep)
    assert not [u for u in rig.urls() if "evil.example.net" in u]
    if case == "two":
        assert len(sitemap_fetches) == 2 and h["sitemaps"] == 2
    elif case == "404":
        assert sitemap_fetches == [] and h["reason"] == "no_sitemap"
    elif case in ("403", "timeout"):
        assert sitemap_fetches == [] and h["reason"] == "robots_unreadable"
    elif case in ("offsite", "disallowed"):
        assert sitemap_fetches == [] and h["sitemaps"] == 0
    else:
        assert len(sitemap_fetches) == 5 and h["sitemaps"] == 5


def test_d11_r05_reuses_the_collector(monkeypatch, tmp_path):
    common, pd = _mods()
    from app.services import cache_service
    from app.services import sitemap_discovery_service as sds

    calls, forbidden, robots_calls = [], [], []
    real = sds._collect_slugs_for_index

    async def spy(*a, **k):
        calls.append((a, k))
        return await real(*a, **k)
    monkeypatch.setattr(sds, "_collect_slugs_for_index", spy)
    for target, name in ((sds, "build_sitemap_index"), (sds, "get_cached"), (sds, "set_cached"),
                         (cache_service, "get_cached"), (cache_service, "set_cached")):
        monkeypatch.setattr(target, name, lambda *a, _n=name, **k: forbidden.append(_n))
    monkeypatch.setattr(pd, "_refuse_all", lambda url: robots_calls.append(url))
    offers, products = _juices(NIGHT + (2,))
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes(), offers=offers,
              products=products)
    rep = tmp_path / "r.json"
    assert _run(pd, "true", monkeypatch, ["--report", str(rep)]) == 0
    assert len(calls) == 1
    a, k = calls[0]
    assert k["robots_cache"] == {HOST: _sub(_fx()["robots_one"], HOST)}
    assert callable(k["fetch"]) and k["max_children"] == 32
    assert robots_calls == [] and forbidden == []
    assert "https://%s/sitemap_products.xml" % HOST in rig.urls()
    assert _host_report(rep)["pdp_urls"] == 1


@pytest.mark.parametrize("v2", [None, "true"])
def test_d11_r06_pdp_markers_follow_v2(monkeypatch, tmp_path, v2):
    common, pd = _mods()
    origin = "https://" + HOST
    woo = origin + "/product/amber-veil-eau-de-toilette/"
    shop = origin + "/products/night-oud-eau-de-parfum"
    _set(monkeypatch, "ENABLE_SITEMAP_PDP_MARKERS_V2", v2)
    Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes(urls=[woo, shop]))
    rep = tmp_path / "r.json"
    assert _run(pd, "true", monkeypatch, ["--report", str(rep)]) == 0
    urls = set(_host_report(rep)["urls"])
    assert shop in urls
    assert (woo in urls) == (v2 == "true")


def test_d11_r07_ranking(monkeypatch, tmp_path):
    common, pd = _mods()
    from app.services import kb_service as kb

    a = ("Maison Example", "Night Oud Eau de Parfum 100ml", 3)
    b = ("Brand Bee", "Amber Veil Eau de Toilette 75ml", 1)
    c = ("Brand Cee", "Cedar Mist Eau de Parfum 50ml", 0)
    offers, products = _juices(a, b, c)
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], offers=offers, products=products)
    got = _attr(pd, "ranked_juices")(rig.client)
    assert [g[0] for g in got] == [kb.kb_product_id(a[0], a[1]), kb.kb_product_id(b[0], b[1])]
    assert got[0][1:] == (a[0], a[1])
    monkeypatch.setenv("PDP_DISCOVERY_MAX_JUICES", "1")
    assert [g[0] for g in pd.ranked_juices(rig.client)] == [kb.kb_product_id(a[0], a[1])]
    monkeypatch.delenv("PDP_DISCOVERY_MAX_JUICES")
    Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes())
    rep = tmp_path / "r.json"
    assert _run(pd, "true", monkeypatch, ["--report", str(rep)]) == 0
    h = _host_report(rep)
    assert h["pdp_urls"] == 1 and h["matched"] == 0


def test_d11_r08_matching(monkeypatch, tmp_path):
    common, pd = _mods()
    from app.services import kb_service as kb

    origin = "https://" + HOST
    hit = origin + "/products/maison-example-night-oud-eau-de-parfum-100ml"
    other_size = "https://store-e.example.com/products/maison-example-night-oud-eau-de-parfum-50ml"
    unranked = origin + "/products/brand-zed-dune-eau-de-parfum-100ml"
    offers, products = _juices(NIGHT + (2,))
    host_e = "store-e.example.com"
    routes = _std_routes(urls=[hit, unranked])
    routes.update(_std_routes(host=host_e, urls=[other_size]))
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST, rank=1), _merchant(host_e, rank=2)], routes=routes,
              offers=offers, products=products)
    rep = tmp_path / "r.json"
    assert _run(pd, "apply", monkeypatch, ["--report", str(rep)]) == 0
    gaps = rig.client.rows("kb_gaps")
    pid = kb.kb_product_id(*NIGHT)
    assert [(g["product_key"], g["source_hint"]) for g in gaps] == [(pid, hit)]
    assert _host_report(rep, host_e)["matched"] == 0


def test_d11_r09_gap_rows(monkeypatch, tmp_path):
    common, pd = _mods()
    from app.services import kb_service as kb

    origin = "https://" + HOST
    hit = origin + "/products/maison-example-night-oud-eau-de-parfum-100ml"
    long_url = origin + "/products/brand-bee-amber-veil-eau-de-toilette-75ml-" + "-".join(["extra"] * 50)
    offers, products = _juices(NIGHT + (2,), ("Brand Bee", "Amber Veil Eau de Toilette 75ml", 1))
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes(urls=[hit, long_url]),
              offers=offers, products=products)
    rep = tmp_path / "r.json"
    assert _run(pd, "apply", monkeypatch, ["--report", str(rep)]) == 0
    pid = kb.kb_product_id(*NIGHT)
    field = "pdp_" + hashlib.sha256(HOST.encode()).hexdigest()[:16]
    want = kb.build_gap_row(product_key=pid, field=field, first_seen=NOW, last_seen=NOW, demand_count=0,
                            state="queued", source_hint=kb.canonical_offer_url(hit))
    assert rig.client.rows("kb_gaps") == [want]
    assert _host_report(rep)["hint_refused"] == 1
    (up,) = [q for q in rig.client.executed if q.table == "kb_gaps" and q.kind() == "upsert"]
    assert up.arg("upsert")[0][1] == {"on_conflict": "product_key,field", "ignore_duplicates": True}
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes(urls=[hit]), offers=offers,
              products=products, returned=lambda q, rows: [])
    assert _run(pd, "apply", monkeypatch) == 0
    (upd,) = [q for q in rig.client.executed if q.table == "kb_gaps" and q.kind() == "update"]
    assert upd.arg("update")[0][0][0] == {"last_seen": want["last_seen"]}
    assert sorted(x[0] for x in upd.arg("eq")) == [("field", field), ("product_key", pid)]


@pytest.mark.parametrize("flag,index", [("true", None), ("true", "cc-main-2026-40"), ("true", "CC-MAIN-26-4"),
                                        ("false", INDEX)])
def test_d11_r10_cdx_inert(monkeypatch, flag, index):
    common, pd = _mods()
    monkeypatch.setenv("ENABLE_CC_CDX", flag)
    _set(monkeypatch, "KB_CC_INDEX", index)
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes())
    assert _run(pd, "true", monkeypatch) == 0
    assert rig.fetches and not [u for u in rig.urls() if "commoncrawl" in u]


def test_d11_r11_cdx_request_shape_and_stop(monkeypatch):
    common, pd = _mods()
    monkeypatch.setenv("ENABLE_CC_CDX", "true")
    monkeypatch.setenv("KB_CC_INDEX", INDEX)
    origin = "https://" + HOST
    cdx_line = json.dumps({"url": origin + "/products/cdx-only-eau-de-parfum", "status": "200", "mime": "text/html"})
    routes = _std_routes()
    routes["https://index.commoncrawl.org/"] = _ok(cdx_line + "\n", "text/plain")
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=routes)
    assert _run(pd, "true", monkeypatch) == 0
    cdx = [u for u in rig.urls() if u.startswith("https://index.commoncrawl.org/")]
    assert len(cdx) == 3
    first = urlsplit(cdx[0])
    assert first.path == "/%s-index" % INDEX
    assert sorted(parse_qsl(first.query)) == sorted([
        ("url", HOST + "/*"), ("output", "json"), ("fl", "url,status,mime"), ("filter", "status:200"),
        ("filter", "mime:text/html"), ("page", "0")])
    assert [dict(parse_qsl(urlsplit(u).query))["page"] for u in cdx] == ["0", "1", "2"]
    assert origin + "/products/cdx-only-eau-de-parfum" not in rig.urls()
    other = "store-e.example.com"
    routes = _std_routes()
    routes.update(_std_routes(host=other))
    routes["https://index.commoncrawl.org/"] = (503, {}, "")
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST, rank=1), _merchant(other, rank=2)], routes=routes)
    assert _run(pd, "true", monkeypatch) == 0
    assert len([u for u in rig.urls() if "commoncrawl" in u]) == 1


def test_d11_r12_dry_writes_nothing(monkeypatch, tmp_path):
    common, pd = _mods()
    offers, products = _juices(NIGHT + (2,))
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes(), offers=offers,
              products=products)
    rep = tmp_path / "r.json"
    assert _run(pd, "true", monkeypatch, ["--report", str(rep)]) == 0
    assert not [q for q in rig.client.executed if q.table == "kb_gaps"]
    h = _host_report(rep)
    assert h["matched"] == 1 and h["pdp_urls"] == 1 and h["sitemaps"] == 1


def test_d11_r13_politeness_named_ua_ssrf(monkeypatch):
    common, pd = _mods()
    from app.services import robots_registry as rr

    origin = "https://" + HOST
    routes = _std_routes()
    routes[origin + "/sitemap_products.xml"] = (301, {"location": origin + "/sitemap_products_2.xml"}, "")
    routes[origin + "/sitemap_products_2.xml"] = _ok(_fx()["urlset"].replace(
        "{locs}", "<url><loc>%s/products/x-eau-de-parfum</loc></url>" % origin))
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=routes)
    assert _run(pd, "true", monkeypatch) == 0
    assert len(rig.fetches) == 3 and rig.max_in_flight == 1
    assert rig.sleeps == [2.0, 2.0]
    assert all(f["headers"] == rr._REQUEST_HEADERS and f["allow_redirects"] is False for f in rig.fetches)
    assert rig.validates == rig.urls()


@pytest.mark.parametrize("mode", ["true", "apply"])
def test_d11_r14_tables_written(monkeypatch, mode):
    common, pd = _mods()
    offers, products = _juices(NIGHT + (2,))
    rig = Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes(), offers=offers,
              products=products)
    assert _run(pd, mode, monkeypatch) == 0
    for q in rig.client.executed:
        assert q.table not in ("kb_variants", "kb_specs", "kb_images")
        if q.table != "kb_gaps":
            assert q.kind() == "select"
    assert ("kb_gaps" in {q.table for q in rig.client.executed}) == (mode == "apply")


def test_d11_r15_railway_pdpdiscovery():
    path = ROOT / "railway.pdpdiscovery.json"
    assert path.is_file(), "railway.pdpdiscovery.json is missing"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    assert cfg["deploy"]["startCommand"] == "python -m scripts.cron_pdp_discovery"
    assert cfg["deploy"]["restartPolicyType"] == "NEVER"
    assert {"scripts/cron_pdp_discovery.py", "scripts/kb_seed_common.py", "railway.pdpdiscovery.json"} <= set(
        cfg["build"]["watchPatterns"])


R16 = [
    ("PDP_DISCOVERY_MAX_HOSTS", None, 100), ("PDP_DISCOVERY_MAX_HOSTS", "", 100),
    ("PDP_DISCOVERY_MAX_HOSTS", "garbage", 100), ("PDP_DISCOVERY_MAX_HOSTS", "inf", 100),
    ("PDP_DISCOVERY_MAX_HOSTS", "nan", 100), ("PDP_DISCOVERY_MAX_HOSTS", "-1", 100),
    ("PDP_DISCOVERY_MAX_HOSTS", "999", 500), ("PDP_DISCOVERY_MAX_HOSTS", "2", 2),
    ("PDP_DISCOVERY_MAX_JUICES", None, 2000), ("PDP_DISCOVERY_MAX_JUICES", "nan", 2000),
    ("PDP_DISCOVERY_MAX_JUICES", "99999", 20000),
    ("PDP_DISCOVERY_MAX_CHILDREN", None, 32), ("PDP_DISCOVERY_MAX_CHILDREN", "-4", 32),
    ("PDP_DISCOVERY_MAX_CHILDREN", "999", 200), ("PDP_DISCOVERY_MAX_CHILDREN", "3", 3),
]


@pytest.mark.parametrize("name,value,expected", R16)
def test_d11_r16_int_knobs_and_max_hosts(monkeypatch, name, value, expected):
    common, pd = _mods()
    from app.services import sitemap_discovery_service as sds

    reader = {"PDP_DISCOVERY_MAX_HOSTS": "max_hosts", "PDP_DISCOVERY_MAX_JUICES": "max_juices",
              "PDP_DISCOVERY_MAX_CHILDREN": "max_children"}[name]
    _set(monkeypatch, name, value)
    assert _attr(pd, reader)() == expected
    if value == "2":
        hosts = ["store-%s.example.com" % c for c in "pqr"]
        routes = {}
        for h in hosts:
            routes.update(_std_routes(host=h))
        rows = [_merchant("store-r.example.com", rank=3), _merchant("store-p.example.com", rank=1),
                _merchant("store-q.example.com", rank=2)]
        rig = Rig(monkeypatch, common, merchants=rows, routes=routes)
        assert _run(pd, "true", monkeypatch) == 0
        seen = {urlsplit(u).hostname for u in rig.urls()}
        assert seen == {"store-p.example.com", "store-q.example.com"}
    if value == "3":
        seen = []
        real = sds._collect_slugs_for_index

        async def spy(*a, **k):
            seen.append(k.get("max_children"))
            return await real(*a, **k)
        monkeypatch.setattr(sds, "_collect_slugs_for_index", spy)
        Rig(monkeypatch, common, merchants=[_merchant(HOST)], routes=_std_routes())
        assert _run(pd, "true", monkeypatch) == 0
        assert seen == [3]


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------

def _full_config(monkeypatch):
    monkeypatch.delenv("ENABLE_PDP_DISCOVERY", raising=False)
    monkeypatch.setenv("ENABLE_CC_CDX", "true")
    monkeypatch.setenv("KB_CC_INDEX", INDEX)
    monkeypatch.setenv("PDP_DISCOVERY_MAX_HOSTS", "3")


def test_d11_p01_collector_failclosed(monkeypatch):
    _full_config(monkeypatch)
    import asyncio

    from app.services import sitemap_discovery_service as sds

    fetched, robots = [], []

    async def fetch(url):
        fetched.append(url)
        return "<urlset/>"

    async def robots_fetch(url):
        robots.append(url)
        return 200, ""
    out = asyncio.run(sds._collect_slugs_for_index(HOST, "https://%s/sitemap.xml" % HOST, fetch, 5, robots_fetch,
                                                   {HOST: None}))
    assert out == {} and fetched == [] and robots == []


def test_d11_p02_pdp_markers_v1(monkeypatch):
    _full_config(monkeypatch)
    monkeypatch.delenv("ENABLE_SITEMAP_PDP_MARKERS_V2", raising=False)
    from app.services import sitemap_discovery_service as sds

    assert sds._is_pdp_url("https://%s/products/x" % HOST) is True
    assert sds._is_pdp_url("https://%s/product/x" % HOST) is False
    assert sds._is_pdp_url("https://%s/collections/x" % HOST) is False


def test_d11_p03_robots_sitemaps(monkeypatch):
    _full_config(monkeypatch)
    from app.services import robots_eval

    body = ("# Sitemap: https://%s/commented.xml\nUser-agent: *\nSitemap: https://%s/a.xml\n"
            "Sitemap: https://%s/b.xml\nSitemap: https://%s/a.xml\n") % ((HOST,) * 4)
    assert robots_eval.sitemaps(body) == ["https://%s/a.xml" % HOST, "https://%s/b.xml" % HOST]


def test_d11_p04_gap_builder_hint(monkeypatch):
    _full_config(monkeypatch)
    from app.services import kb_service as kb

    head = "https://%s/products/" % HOST
    ok = head + "x" * (256 - len(head))
    base = dict(product_key="fragrances|maison+example|night+oud|EDP", field="pdp_" + "0" * 16, first_seen=NOW,
                demand_count=0, state="queued")
    assert kb.build_gap_row(**dict(base, source_hint=ok)) is not None
    assert kb.build_gap_row(**dict(base, source_hint=ok[:-2] + "?q")) is None
    assert kb.build_gap_row(**dict(base, source_hint=ok + "x")) is None
