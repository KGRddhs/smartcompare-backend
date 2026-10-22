"""D03 DENY-AND-GUARDS - the frozen RED file (ENABLE_DATA_GUARDS_V2, default OFF).

Unit D03 (PLAN_S81 M1, lane B). Spec: .qa-s80/D03_UNIT_SPEC.md (sha 3460ffab...),
its adversarial review .qa-s80/D03_SPEC_REVIEW.md and the orchestrator rulings
specs/RULINGS_D03.md (session-81 state folder). Precedence: rulings, then the
review corrections, then the spec. Base 95cf6f864b4e70980ca191daa064c0118e223c13.

Row kinds:
  * R rows fail at base on an AssertionError ONLY. A missing module or name is
    read through the _mod / _attr helpers and asserted, never raised.
  * P rows are green at base and pin the flag-OFF behaviour with the FULL unit
    configuration present (the synthetic registry carries a denied row of every
    selector shape, ENABLE_LONGEST_HOST_MATCH in both states, every falsy flag
    spelling) so a consumer that filters without reading the flag is killed
    (ruling B1, session 79). The behavioural OFF outputs are the recorders.
  * G rows are green at base AND must stay green with the flag ON: they guard
    against a downgrade the "as if absent" design could create (ruling B2).

Scope (ruling R-D03-1): the URL-mode half (pre-gate refusal, hop deny,
normalize_image_url skip, the V2-OFF base-path deny) is carved out to D03b; this
file asserts only that D03 does not touch the url_* files (P14). Prompt-input
filtering is D03c (R-D03-2); the omega / tiffany tokens are D03d (R-D03-3).

Hermetic: no network (the conftest netguard is on), no Supabase / OpenAI /
Serper (every seam is patched with a recorder), no .env, no credential. Host
names are public site names or synthetic .test hosts. Pure ASCII.
"""

from __future__ import annotations

import ast
import asyncio
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

FLAG = "ENABLE_DATA_GUARDS_V2"
ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
DENY_PATH = APP_DIR / "services" / "deny_hosts.py"
OUDWOOD_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "serper_oudwood_organic.json"
)

FALSY = ["", "false", "0", "off", "no", "garbage", "FALSE "]
TRUTHY = ["TRUE", " on ", "1", "Yes"]

FIMGS_IMG = "https://fimgs.net/mdimg/perfume/375x500.1826.jpg"
FRAG_PDP = "https://www.fragrantica.com/perfume/Tom-Ford/Oud-Wood-1826.html"
FRAG_BH_PDP = "https://www.fragrantica.com/bh-en/perfume/Tom-Ford/Oud-Wood-1826.html"
CDN_IMG = "https://cdn.perfume-shop.test/a.jpg"
OUNASS_PDP = "https://bahrain.ounass.com/shop-maison-margiela-replica-jazz-club-edt-100ml-0001.html"
REAL_GLOBAL_QUERY_OFF = (
    "Dior Sauvage site:amazon.com OR site:sephora.com OR site:walmart.com "
    "OR site:fragrantica.com"
)
REAL_GLOBAL_QUERY_ON = (
    "Dior Sauvage site:amazon.com OR site:sephora.com OR site:walmart.com"
)

THE_26_HOSTS = sorted(
    [
        "fragrantica.com",
        "fragrantica.asia",
        "fragrantica.co.il",
        "fragrantica.com.br",
        "fragrantica.cz",
        "fragrantica.de",
        "fragrantica.es",
        "fragrantica.fr",
        "fragrantica.gr",
        "fragrantica.hu",
        "fragrantica.it",
        "fragrantica.jp",
        "fragrantica.kr",
        "fragrantica.mn",
        "fragrantica.nl",
        "fragrantica.pl",
        "fragrantica.ro",
        "fragrantica.ru",
        "fragrantica.se",
        "fragrantica.tr",
        "fragrantica.ua",
        "parfumo.com",
        "parfumo.de",
        "basenotes.com",
        "basenotes.net",
        "fimgs.net",
    ]
)


# ---------------------------------------------------------------------------
# helpers: a missing symbol is an assertion, never an ImportError
# ---------------------------------------------------------------------------


def _mod(name):
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return None
    if spec is None:
        return None
    try:
        return importlib.import_module(name)
    except Exception:  # noqa: BLE001 - a broken new module reads as missing
        return None


def _attr(obj, name):
    return getattr(obj, name, None) if obj is not None else None


def _dh():
    m = _mod("app.services.deny_hosts")
    assert m is not None, "app.services.deny_hosts is missing (D03 change 1)"
    return m


def _dh_fn(name):
    f = _attr(_dh(), name)
    assert callable(f), "deny_hosts.%s is missing or not callable" % name
    return f


def _sr():
    return importlib.import_module("app.services.source_router")


def _sds():
    return importlib.import_module("app.services.search_descriptor_service")


def _ps():
    return importlib.import_module("app.services.price_service")


def _rs():
    return importlib.import_module("app.services.rating_service")


def _img():
    return importlib.import_module("app.services.image_service")


def _rv():
    return importlib.import_module("app.services.review_service")


def _on(mp):
    mp.setenv(FLAG, "true")


def _off(mp, value=None):
    if value is None:
        mp.delenv(FLAG, raising=False)
    else:
        mp.setenv(FLAG, value)


@pytest.fixture(autouse=True)
def _d03_clean_env(monkeypatch):
    """Every row sets its own flag state; nothing ambient leaks in."""
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv("BH_GCC_FANOUT_K", raising=False)
    monkeypatch.delenv("ENABLE_LONGEST_HOST_MATCH", raising=False)
    # Full unit configuration (2.7): the URL-mode flag of the sister unit is
    # present too, so a D03 consumer keyed on it is visible in the OFF pins.
    monkeypatch.setenv("ENABLE_URL_MODE_V2", "true")
    sr = _sr()
    # The filtered-registry memo seam (spec 2.8); absent at base (raising=False).
    monkeypatch.setattr(sr, "_ROUTABLE_MEMO", None, raising=False)
    yield


# ---------------------------------------------------------------------------
# the synthetic registry: one denied row of every selector shape + 4 allowed
# ---------------------------------------------------------------------------

N_DENIED = 8


def _descriptor():
    sds = _sds()
    return sds.SearchDescriptor(
        kind="platform_api",
        url_template="https://media.parfumo.com/search?q={q}",
        robots_allowed=True,
        discovered_via="manual",
        resolved_at="2026-10-22T00:00:00Z",
    )


def _reg():
    S = _sr().Source
    return [
        # denied rows (D1-D8): one per selector shape
        S("fragrantica.com", "global", ("fragrances",), 1.0),
        S(
            "www.parfumo.de",
            "gcc",
            ("fragrances",),
            1.5,
            usage="both",
            mechanism="woo_store_json",
            status="live",
            is_render_only=True,
        ),
        S(
            "media.parfumo.com",
            "bahrain",
            ("fragrances",),
            3.0,
            is_shopify=True,
            search_descriptor=_descriptor(),
        ),
        S("fimgs.net", "bahrain", ("fragrances",), 3.0, is_algolia=True),
        S("basenotes.com", "bahrain", ("fragrances",), 3.0, mechanism="json_api"),
        S(
            "forum.basenotes.net",
            "bahrain",
            ("fragrances",),
            3.0,
            usage="review",
            mechanism="sitemap",
        ),
        S("fragrantica.ru", "bahrain", ("fragrances",), 3.0),
        S(
            "fragrantica.asia",
            "gcc",
            ("fragrances",),
            1.5,
            sample_url="https://fragrantica.asia/products.json",
        ),
        # allowed rows (A1-A4)
        S("amazon.com", "global", (), 1.0),
        S("sephora.com", "global", ("fragrances",), 1.0, usage="both"),
        S("bh.perfume-shop.test", "bahrain", ("fragrances",), 3.0, is_shopify=True),
        S("notfragrantica.com", "gcc", ("fragrances",), 1.5),
    ]


def _doms(rows):
    return [s.domain for s in rows]


def _row_dom(row):
    return None if row is None else row.domain


R3A_CASES = {
    "sources_all": lambda sr, sds: _doms(sr.get_sources_for_category("fragrances")),
    "sources_price": lambda sr, sds: _doms(
        sr.get_sources_for_category("fragrances", usage="price")
    ),
    "sources_review": lambda sr, sds: _doms(
        sr.get_sources_for_category("fragrances", usage="review")
    ),
    "query_bahrain": lambda sr, sds: sr.build_site_discovery_query(
        "Q", "fragrances", tier="bahrain", limit=8
    ),
    "query_gcc": lambda sr, sds: sr.build_site_discovery_query(
        "Q", "fragrances", tier="gcc", limit=8
    ),
    "query_global": lambda sr, sds: sr.build_site_discovery_query(
        "Q", "fragrances", tier="global", limit=8
    ),
    "shopify": lambda sr, sds: _doms(sr.get_shopify_sources_for_category("fragrances")),
    "algolia": lambda sr, sds: _doms(sr.get_algolia_sources_for_category("fragrances")),
    "jsonapi": lambda sr, sds: _doms(sr.get_jsonapi_sources_for_category("fragrances")),
    "curl_pagescrape": lambda sr, sds: _doms(
        sr.get_curl_pagescrape_sources_for_category("fragrances")
    ),
    "sitemap": lambda sr, sds: _doms(sr.get_sitemap_sources_for_category("fragrances")),
    "woo": lambda sr, sds: _doms(sr.get_woo_sources_for_category("fragrances")),
    "gcc_shopify_pagescrape": lambda sr, sds: _doms(
        sr.get_gcc_shopify_pagescrape_sources_for_category("fragrances")
    ),
    "score_source": lambda sr, sds: sr.score_source(
        "https://www.fragrantica.com/perfume/x-1.html", "fragrances"
    ),
    "source_usage": lambda sr, sds: sr.source_usage(
        "https://forum.basenotes.net/t/x-1", "fragrances"
    ),
    "registry_tier": lambda sr, sds: sr.registry_tier("www.fragrantica.com"),
    "match_registry_apex": lambda sr, sds: sr.match_registry_apex("fr.fragrantica.com"),
    "is_render_only_domain": lambda sr, sds: sr.is_render_only_domain("www.parfumo.de"),
    "registry_row_for_host": lambda sr, sds: _row_dom(
        sr._registry_row_for_host("media.parfumo.com")
    ),
    "descriptor_for_host": lambda sr, sds: (
        None
        if sds.descriptor_for_host("media.parfumo.com") is None
        else sds.descriptor_for_host("media.parfumo.com").url_template
    ),
}

# Flag-OFF base values over the synthetic registry (measured at 95cf6f86 by
# the RED author's probe; identical with ENABLE_LONGEST_HOST_MATCH OFF and ON).
P1_BASE = {
    "algolia": ["fimgs.net"],
    "curl_pagescrape": ["fragrantica.ru"],
    "descriptor_for_host": "https://media.parfumo.com/search?q={q}",
    "gcc_shopify_pagescrape": ["fragrantica.asia"],
    "is_render_only_domain": True,
    "jsonapi": ["basenotes.com"],
    "match_registry_apex": "fragrantica.com",
    "query_bahrain": "Q site:media.parfumo.com OR site:fimgs.net OR site:basenotes.com OR site:fragrantica.ru OR site:bh.perfume-shop.test",
    "query_gcc": "Q site:www.parfumo.de OR site:fragrantica.asia OR site:notfragrantica.com",
    "query_global": "Q site:fragrantica.com OR site:amazon.com OR site:sephora.com",
    "registry_row_for_host": "media.parfumo.com",
    "registry_tier": "global",
    "score_source": 1.0,
    "shopify": ["media.parfumo.com", "bh.perfume-shop.test"],
    "sitemap": ["forum.basenotes.net"],
    "source_usage": "review",
    "sources_all": [
        "media.parfumo.com",
        "fimgs.net",
        "basenotes.com",
        "forum.basenotes.net",
        "fragrantica.ru",
        "bh.perfume-shop.test",
        "www.parfumo.de",
        "fragrantica.asia",
        "notfragrantica.com",
        "fragrantica.com",
        "amazon.com",
        "sephora.com",
    ],
    "sources_price": [
        "media.parfumo.com",
        "fimgs.net",
        "basenotes.com",
        "fragrantica.ru",
        "bh.perfume-shop.test",
        "www.parfumo.de",
        "fragrantica.asia",
        "notfragrantica.com",
        "fragrantica.com",
        "amazon.com",
        "sephora.com",
    ],
    "sources_review": ["forum.basenotes.net", "www.parfumo.de", "sephora.com"],
    "woo": ["www.parfumo.de"],
}


# ---------------------------------------------------------------------------
# R1 - the deny_hosts leaf
# ---------------------------------------------------------------------------


def test_r1a_module_exists():
    m = _mod("app.services.deny_hosts")
    assert m is not None, "app.services.deny_hosts is missing"
    for name in (
        "DENY_HOSTS",
        "DENY_LABELS",
        "LEGACY_DESCRIPTOR_DENY_HOSTS",
        "data_guards_v2_enabled",
        "normalize_host",
        "is_denied_host",
        "is_denied_url",
        "is_denied_source",
        "DeniedSourceError",
        "kb_source_allowed",
        "assert_kb_source_allowed",
    ):
        assert _attr(m, name) is not None, "deny_hosts.%s missing" % name


def _imports_of(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend((a.name, 0) for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.append((node.module or "", node.level))
    return out


def test_r1b_module_is_stdlib_only():
    assert DENY_PATH.is_file(), "app/services/deny_hosts.py does not exist"
    for name, level in _imports_of(DENY_PATH):
        assert level == 0, "relative import in deny_hosts.py"
        root = name.split(".")[0]
        assert root == "__future__" or root in sys.stdlib_module_names, (
            "deny_hosts.py imports a non-stdlib module: %s" % name
        )


def _docstring_nodes(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], "value", None), ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def test_r1c_no_http_literal_t7b_safe():
    assert DENY_PATH.is_file(), "app/services/deny_hosts.py does not exist"
    tree = ast.parse(DENY_PATH.read_text(encoding="utf-8"))
    docs = _docstring_nodes(tree)
    bad = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and id(n) not in docs
        and ("http://" in n.value or "https://" in n.value)
    ]
    assert bad == [], "scheme literal in deny_hosts.py (T7b): %r" % bad


def test_r1d_deny_hosts_content():
    m = _dh()
    hosts = _attr(m, "DENY_HOSTS")
    assert isinstance(hosts, tuple), "DENY_HOSTS must be a tuple"
    assert sorted(hosts) == THE_26_HOSTS
    for h in hosts:
        assert (
            h == h.lower()
            and "://" not in h
            and not h.startswith("www.")
            and ":" not in h
        )
    assert _attr(m, "LEGACY_DESCRIPTOR_DENY_HOSTS") == (
        "fragrantica.com",
        "parfumo.com",
    )
    assert set(_attr(m, "DENY_LABELS") or ()) == {
        "fragrantica",
        "parfumo",
        "basenotes",
        "fimgs",
    }


R1E_TRUE = [
    "fragrantica.com",
    "www.fragrantica.com",
    "FRAGRANTICA.COM.",
    " fr.fragrantica.com ",
    "fragrantica.com:443",
    "fragrantica.ru",
    "www.fragrantica.com.br",
    "www.parfumo.de",
    "media.parfumo.com",
    "basenotes.com",
    "basenotes.net",
    "fimgs.net",
    "rwebsocket.fimgs.net",
    # ruling C10: deny by registrable LABEL with any public suffix
    "fragrantica.cn",
    "www.parfumo.it",
    # a port on a two-level public suffix (the port is dropped before matching)
    "fragrantica.com.br:8443",
]
R1E_FALSE = [
    "notfragrantica.com",
    "fragrantica.com.evil.test",
    "fragranticacom.net",
    "parfumoshop.com",
    "myfimgs.net",
    "bahrain.ounass.com",
    "",
    # ruling C10
    "notfragrantica.cn",
]


@pytest.mark.parametrize("host", R1E_TRUE)
def test_r1e_is_denied_host_true(host):
    assert _dh_fn("is_denied_host")(host) is True


@pytest.mark.parametrize("host", R1E_FALSE)
def test_r1e_is_denied_host_false(host):
    assert _dh_fn("is_denied_host")(host) is False


def test_r1e_is_denied_host_non_str_never_raises():
    fn = _dh_fn("is_denied_host")
    for value in (None, 123, b"fimgs.net", {}, ["fimgs.net"]):
        assert fn(value) is False


def _userinfo_url():
    # built at run time: no userinfo-shaped literal in the file
    return "https://" + "u" + "@" + "www.parfumo.de/x"


def test_r1f_is_denied_url():
    fn = _dh_fn("is_denied_url")
    for url in (
        FIMGS_IMG,
        "http://www.fragrantica.com/perfume/Tom-Ford/Oud-Wood-1826.html",
        "//media.parfumo.com/x.jpg",
        "fimgs.net/x.jpg",
        _userinfo_url(),
        "https://fimgs.net:8443/x",
        "https://fragrantica.cn/perfume/x-1.html",
    ):
        assert fn(url) is True, url
    for url in (
        "https://bahrain.ounass.com/x",
        "https://notfragrantica.com/x",
        "http://[bad",
        None,
        7,
        "",
    ):
        assert fn(url) is False, url


def test_r1g_is_denied_source():
    fn = _dh_fn("is_denied_source")
    for value in (
        "Fragrantica",
        "fragrantica.ru",
        "Parfumo",
        "Basenotes",
        "https://fimgs.net/a.jpg",
        "Parfumo.de",
    ):
        assert fn(value) is True, value
    for value in ("Notfragrantica", "Boots", "Sally Beauty", "", None, 5):
        assert fn(value) is False, value


@pytest.mark.parametrize("value", TRUTHY)
def test_r1h_reader_truthy(value, monkeypatch):
    monkeypatch.setenv(FLAG, value)
    assert _dh_fn("data_guards_v2_enabled")() is True


@pytest.mark.parametrize("value", FALSY + [None])
def test_r1h_reader_falsy(value, monkeypatch):
    _off(monkeypatch, value)
    assert _dh_fn("data_guards_v2_enabled")() is False


_BANNED_LITERAL_HOSTS = {"fragrantica.com", "parfumo.com", "basenotes.com", "fimgs.net"}


def _container_strs(node):
    """String constants directly inside a tuple / list / set literal (or a
    set() / frozenset() / tuple() / list() call over one), recursively through
    nested containers. A Source(...) call is NOT descended into: the documented
    exemption of the literal row source_router.py:347 (ruling C11) - and the
    rating name sets carry bare names, never a host."""
    out = []
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for e in node.elts:
            if isinstance(e, ast.Constant) and isinstance(e.value, str):
                out.append(e.value)
            else:
                out.extend(_container_strs(e))
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in ("set", "frozenset", "tuple", "list")
    ):
        for a in node.args:
            out.extend(_container_strs(a))
    return out


def test_r1i_single_deny_literal_list():
    offenders = []
    for path in sorted(APP_DIR.rglob("*.py")):
        if path.resolve() == DENY_PATH.resolve():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            value = None
            if isinstance(node, ast.Assign):
                value = node.value
            elif isinstance(node, ast.AnnAssign):
                value = node.value
            if value is None:
                continue
            hits = [
                s for s in _container_strs(value) if s.lower() in _BANNED_LITERAL_HOSTS
            ]
            if hits:
                offenders.append(
                    "%s:%d %r" % (path.relative_to(ROOT).as_posix(), node.lineno, hits)
                )
    assert offenders == [], "a second banned-host literal list: %s" % offenders
    m = _dh()
    assert _sds().DENY_HOSTS is _attr(m, "LEGACY_DESCRIPTOR_DENY_HOSTS")


# ---------------------------------------------------------------------------
# R2 / P4 - the search descriptor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "host",
    [
        "basenotes.com",
        "www.parfumo.de",
        "fimgs.net",
        "fragrantica.ru",
        "www.fragrantica.com.br",
    ],
)
def test_r2a_descriptor_deny_on(host, monkeypatch):
    _on(monkeypatch)
    assert _sds()._deny(host) is True


@pytest.mark.parametrize("host", ["notfragrantica.com", "fragrancebh.com", ""])
def test_g2a_descriptor_on_keeps_allowed(host, monkeypatch):
    _on(monkeypatch)
    assert _sds()._deny(host) is False


def _probe(host):
    calls = []

    def fetch(url, *a, **k):
        calls.append(url)
        return (404, "")

    raised = other = False
    try:
        _sds().probe_search_descriptor(host, fetch)
    except ValueError:
        raised = True
    except Exception:  # noqa: BLE001
        other = True
    return raised, other, calls


@pytest.mark.parametrize("host", ["basenotes.com", "fimgs.net", "www.parfumo.de"])
def test_r2b_probe_refuses_new_hosts_without_fetch(host, monkeypatch):
    _on(monkeypatch)
    raised, other, calls = _probe(host)
    assert (raised, other, calls) == (True, False, [])


@pytest.mark.parametrize("flag", FALSY + [None])
def test_p4_descriptor_off_equals_base(flag, monkeypatch):
    _off(monkeypatch, flag)
    sds = _sds()
    assert sds.DENY_HOSTS == ("fragrantica.com", "parfumo.com")
    for h in ("basenotes.com", "fimgs.net", "www.parfumo.de", "fragrantica.ru"):
        assert sds._deny(h) is False, h
    for h in ("www.fragrantica.com", "parfumo.com"):
        assert sds._deny(h) is True, h
    raised, other, calls = _probe("basenotes.com")
    assert raised is False and other is False
    assert calls and calls[0] == "https://basenotes.com/robots.txt"
    # the legacy two hosts are refused before a fetch in BOTH states
    raised, other, calls = _probe("www.parfumo.com")
    assert (raised, calls) == (True, [])


def test_p4b_descriptor_tuple_on_unchanged(monkeypatch):
    _on(monkeypatch)
    assert _sds().DENY_HOSTS == ("fragrantica.com", "parfumo.com")
    raised, other, calls = _probe("fragrantica.com")
    assert (raised, calls) == (True, [])


# ---------------------------------------------------------------------------
# R3 / P1 / P2 - source_router consumers ("as if absent", flag read per call)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("longest", ["false", "true"])
@pytest.mark.parametrize("case", sorted(R3A_CASES))
def test_r3a_as_if_absent(case, longest, monkeypatch):
    sr, sds = _sr(), _sds()
    monkeypatch.setenv("ENABLE_LONGEST_HOST_MATCH", longest)
    reg = _reg()
    fn = R3A_CASES[case]
    # oracle: flag OFF over the registry minus the denied rows
    _off(monkeypatch)
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", reg[N_DENIED:])
    expected = fn(sr, sds)
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", reg)
    _on(monkeypatch)
    got = fn(sr, sds)
    assert got == expected


def test_r3b_real_registry_global_query(monkeypatch):
    sr = _sr()
    _on(monkeypatch)
    assert (
        sr.build_site_discovery_query(
            "Dior Sauvage", "fragrances", tier="global", limit=8
        )
        == REAL_GLOBAL_QUERY_ON
    )
    assert (
        sr.score_source("https://www.fragrantica.com/perfume/x-1.html", "fragrances")
        == 0.5
    )
    assert sr.registry_tier("www.fragrantica.com") is None


def test_r3c_per_call_flip(monkeypatch):
    sr = _sr()
    q = lambda: sr.build_site_discovery_query(
        "Dior Sauvage", "fragrances", tier="global", limit=8
    )  # noqa: E731
    _on(monkeypatch)
    assert "site:fragrantica.com" not in q()
    _off(monkeypatch)
    assert q() == REAL_GLOBAL_QUERY_OFF
    _on(monkeypatch)
    assert "site:fragrantica.com" not in q()
    _off(monkeypatch, "off")
    assert q() == REAL_GLOBAL_QUERY_OFF


def test_r3d_routable_registry_identity(monkeypatch):
    """Ruling B4: flag OFF returns SOURCE_REGISTRY itself; ON a NEW list of the
    same row objects minus the denied rows; the registry is never edited."""
    sr = _sr()
    fn = _attr(sr, "_routable_registry")
    assert callable(fn), "source_router._routable_registry is missing"
    reg = _reg()
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", reg)
    _off(monkeypatch)
    assert fn() is reg
    _on(monkeypatch)
    got = fn()
    assert got is not reg
    assert len(got) == len(reg) - N_DENIED
    assert all(a is b for a, b in zip(got, reg[N_DENIED:]))
    assert len(reg) == 12 and _doms(reg[:N_DENIED])[0] == "fragrantica.com"
    _off(monkeypatch)
    assert fn() is reg


def _alt_rows():
    S = _sr().Source
    rows = _reg()[:N_DENIED]
    return rows + [
        S("alt-a.perfume-b.test", "bahrain", ("fragrances",), 3.0),
        S("alt-b.perfume-b.test", "gcc", ("fragrances",), 1.5),
        S("alt-c.perfume-b.test", "global", ("fragrances",), 1.0),
        S("alt-d.perfume-b.test", "global", (), 1.0),
    ]


def test_r3e_memo_never_serves_a_replaced_registry(monkeypatch):
    """Ruling B4 (review RC7): free one registry, install a same-length
    different one (CPython recycles the freed list id), and the ON read must
    reflect the NEW rows every time. Direct module assignment on purpose:
    monkeypatch.setattr would keep every old list alive."""
    sr = _sr()
    rows_a = tuple(_reg())
    rows_b = tuple(_alt_rows())
    assert len(rows_a) == len(rows_b)
    expect_a = [
        "bh.perfume-shop.test",
        "notfragrantica.com",
        "amazon.com",
        "sephora.com",
    ]
    expect_b = [
        "alt-a.perfume-b.test",
        "alt-b.perfume-b.test",
        "alt-c.perfume-b.test",
        "alt-d.perfume-b.test",
    ]
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", sr.SOURCE_REGISTRY)  # restore point
    _on(monkeypatch)
    for _ in range(25):
        sr.SOURCE_REGISTRY = list(rows_a)
        assert _doms(sr.get_sources_for_category("fragrances")) == expect_a
        sr.SOURCE_REGISTRY = None
        sr.SOURCE_REGISTRY = list(rows_b)
        assert _doms(sr.get_sources_for_category("fragrances")) == expect_b
        sr.SOURCE_REGISTRY = None


@pytest.mark.parametrize("flag", FALSY + [None])
@pytest.mark.parametrize("longest", ["false", "true"])
def test_p1_off_consumers_equal_base(flag, longest, monkeypatch):
    sr, sds = _sr(), _sds()
    monkeypatch.setenv("ENABLE_LONGEST_HOST_MATCH", longest)
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", _reg())
    _off(monkeypatch, flag)
    assert P1_BASE is not None
    got = {name: R3A_CASES[name](sr, sds) for name in sorted(R3A_CASES)}
    assert got == P1_BASE


def test_p1b_explicit_registry_argument_kept_unfiltered(monkeypatch):
    """Spec C2: an explicit registry= argument is a test-only path, unfiltered."""
    sr = _sr()
    reg = _reg()
    for state in (None, "true"):
        if state:
            _on(monkeypatch)
        else:
            _off(monkeypatch)
        row = sr._registry_row_for_host("media.parfumo.com", registry=reg)
        assert row is reg[2]


def test_p2_registry_never_mutated(monkeypatch):
    sr = _sr()
    S = sr.Source
    assert sr._LITERAL_ROWS[38] == S("fragrantica.com", "global", ("fragrances",), 1.0)
    assert len(sr._LITERAL_ROWS) == 44
    before_obj = sr.SOURCE_REGISTRY
    before_rows = list(sr.SOURCE_REGISTRY)
    literal_before = list(sr._LITERAL_ROWS)
    for state in ("true", None, "1", "off"):
        if state in (None, "off"):
            _off(monkeypatch, state)
        else:
            monkeypatch.setenv(FLAG, state)
        sr.build_site_discovery_query(
            "Dior Sauvage", "fragrances", tier="global", limit=8
        )
        sr.score_source(FRAG_PDP, "fragrances")
        sr.registry_tier("www.fragrantica.com")
        sr.get_sources_for_category("fragrances")
    assert sr.SOURCE_REGISTRY is before_obj
    assert len(sr.SOURCE_REGISTRY) == len(before_rows)
    assert all(a is b for a, b in zip(sr.SOURCE_REGISTRY, before_rows))
    assert all(a is b for a, b in zip(sr._LITERAL_ROWS, literal_before))
    _off(monkeypatch)
    assert (
        sr.build_site_discovery_query(
            "Dior Sauvage", "fragrances", tier="global", limit=8
        )
        == REAL_GLOBAL_QUERY_OFF
    )
    assert sr.score_source(FRAG_PDP, "fragrances") == 1.0
    assert sr.registry_tier("www.fragrantica.com") == "global"
    assert sr.match_registry_apex("fr.fragrantica.com") == "fragrantica.com"


# ---------------------------------------------------------------------------
# R4 / P3 - rating selection
# ---------------------------------------------------------------------------

NAME = "Tom Ford Oud Wood"


def _frag_item():
    return {
        "title": NAME,
        "source": "Fragrantica",
        "rating": 4.3,
        "ratingCount": 17104,
        "link": FRAG_PDP,
    }


def _boots_item():
    return {
        "title": NAME,
        "source": "Boots",
        "rating": 4.6,
        "ratingCount": 20,
        "link": "https://bn.boots.com/tom-ford-oud-wood-1001",
    }


def _neutral_denied_link_item():
    return {
        "title": NAME,
        "source": "somestore.com",
        "rating": 4.1,
        "ratingCount": 900,
        "link": FIMGS_IMG,
    }


def _consensus_items():
    return [
        {
            "title": NAME,
            "source": src,
            "rating": 4.0,
            "ratingCount": 5000,
            "link": "https://www.%s/perfume/x-1.html" % host,
        }
        for src, host in (
            ("Parfumo", "parfumo.com"),
            ("Basenotes", "basenotes.com"),
            ("Parfumo.de", "parfumo.de"),
        )
    ]


def _src_name(out):
    return ((out or {}).get("rating_source") or {}).get("name") or ""


def _src_url(out):
    return ((out or {}).get("rating_source") or {}).get("url")


def test_r4a_rating_tier_denied_on(monkeypatch):
    _on(monkeypatch)
    t = _rs().get_rating_tier
    got = {
        s: t(s)
        for s in (
            "Fragrantica",
            "fragrantica.com",
            "Fragrantica.ru",
            "Parfumo",
            "Sally Beauty",
            "boots",
            "Sephora",
        )
    }
    assert got == {
        "Fragrantica": 3,
        "fragrantica.com": 3,
        "Fragrantica.ru": 3,
        "Parfumo": 3,
        "Sally Beauty": 2,
        "boots": 2,
        "Sephora": 1,
    }


def test_r4b_only_denied_candidate_no_rating(monkeypatch):
    _on(monkeypatch)
    out = _rs().extract_rating_from_shopping(NAME, [_frag_item()])
    assert out["rating"] is None and out["rating_source"] is None


def test_r4c_denied_loses_to_allowed(monkeypatch):
    _on(monkeypatch)
    out = _rs().extract_rating_from_shopping(NAME, [_frag_item(), _boots_item()])
    assert out["rating"] == 4.6
    assert _src_name(out).startswith("Boots")


def test_r4d_denied_link_with_neutral_source(monkeypatch):
    _on(monkeypatch)
    rs = _rs()
    assert (
        rs.extract_rating_from_shopping(NAME, [_neutral_denied_link_item()])["rating"]
        is None
    )
    out = rs.extract_rating_from_shopping(
        NAME, [_neutral_denied_link_item(), _boots_item()]
    )
    assert _src_name(out).startswith("Boots")
    frag_link = dict(_neutral_denied_link_item(), link=FRAG_PDP)
    assert rs.extract_rating_from_shopping(NAME, [frag_link])["rating"] is None


def test_r4e_consensus_ignores_denied(monkeypatch):
    _on(monkeypatch)
    out = _rs().extract_rating_from_shopping(NAME, _consensus_items())
    assert out["rating"] is None


def test_r4f_collect_retailer_ratings_drops_denied(monkeypatch):
    _on(monkeypatch)
    items = [_frag_item(), _boots_item(), _neutral_denied_link_item()]
    out = _rs().collect_retailer_ratings(NAME, {NAME: items})
    assert [r["source"] for r in out] == ["Boots"]


RATING_TIER_2_LITERAL = {
    "costco",
    "carrefour",
    "sharaf dg",
    "virgin megastore",
    "currys",
    "john lewis",
    "adorama",
    "micro center",
    "google store",
    "microsoft",
    "dell",
    "hp store",
    "lenovo",
    "fnac",
    "fragrantica",
    "sally beauty",
    "lookfantastic",
    "beautybay",
    "nykaa",
    "bath & body",
    "boots",
}
LUXURY_FASHION_RETAILERS_LITERAL = {
    "fragrantica",
    "sally beauty",
    "lookfantastic",
    "beautybay",
    "nykaa",
    "bath & body",
    "boots",
}


@pytest.mark.parametrize("flag", FALSY + [None])
def test_p3_rating_off_equals_base(flag, monkeypatch):
    _off(monkeypatch, flag)
    rs = _rs()
    assert rs.RATING_TIER_2 == RATING_TIER_2_LITERAL and len(rs.RATING_TIER_2) == 21
    assert rs.LUXURY_FASHION_RETAILERS == LUXURY_FASHION_RETAILERS_LITERAL
    assert rs.get_rating_tier("Fragrantica") == 2
    assert rs.get_rating_tier("Parfumo") == 3
    out = rs.extract_rating_from_shopping(NAME, [_frag_item()])
    assert (out["rating"], out["review_count"], _src_name(out)) == (
        4.3,
        17104,
        "Fragrantica via Google Shopping",
    )
    out = rs.extract_rating_from_shopping(NAME, [_frag_item(), _boots_item()])
    assert _src_name(out) == "Fragrantica via Google Shopping"
    out = rs.extract_rating_from_shopping(
        NAME, [_neutral_denied_link_item(), _boots_item()]
    )
    assert _src_name(out) == "somestore.com via Google Shopping"
    assert _src_url(out) == FIMGS_IMG
    out = rs.extract_rating_from_shopping(NAME, _consensus_items())
    assert (out["rating"], out["review_count"], _src_name(out)) == (
        4.0,
        5000,
        "Google Shopping (product aggregate)",
    )
    listed = rs.collect_retailer_ratings(
        NAME, {NAME: [_frag_item(), _boots_item(), _neutral_denied_link_item()]}
    )
    assert [r["source"] for r in listed] == ["Fragrantica", "Boots", "somestore.com"]


def test_p3b_rating_sets_unchanged_after_on_calls(monkeypatch):
    rs = _rs()
    _on(monkeypatch)
    rs.get_rating_tier("Fragrantica")
    rs.extract_rating_from_shopping(NAME, [_frag_item(), _boots_item()])
    rs.collect_retailer_ratings(NAME, {NAME: [_frag_item()]})
    assert rs.RATING_TIER_2 == RATING_TIER_2_LITERAL
    assert rs.LUXURY_FASHION_RETAILERS == LUXURY_FASHION_RETAILERS_LITERAL
    scs = importlib.import_module("app.services.structured_comparison_service")
    assert scs.StructuredComparisonService.RATING_TIER_2 is rs.RATING_TIER_2


# ---------------------------------------------------------------------------
# R5 / R6 / P5-P8 - the counterfeit and luxury guards
# ---------------------------------------------------------------------------

MARGIELA_TITLES = [
    "Maison Margiela Replica Jazz Club Eau de Toilette 100ml",
    "MAISON MARGIELA 'REPLICA' By the Fireplace EDT 100 ml",
]
SUBSTRING_FALSE_POSITIVES = [
    "Lattafa Oud Infused Eau de Parfum 100ml",
    "Rose Infused Body Oil",
    "Focused Serum 30ml",
    "Unused tester 100ml",
    "Copyright free",
]
LV_FALSE_POSITIVES = [
    "Centrum Silver",
    "Calvin Klein boxer briefs",
    "L'Oreal Elvive shampoo",
    "Creed Silver Mountain Water 100ml",
    "Velvet Matte Lipstick",
    "Salvatore Ferragamo Uomo",
    "Volvo key fob",
    "LVMH annual report",
]
LV_ALIASES = ["L.V. Neverfull", "l.v monogram"]
CK_NAME = "Calvin Klein Eternity Eau de Parfum 100ml"

COUNTERFEIT_KEPT_ON = [
    "Used tester 100ml",
    "Creed Aventus replicas set",
    "Aventus dupes 3 pack",
    "Replica of Maison Margiela Jazz Club dupe",
    "Inspired by Maison Margiela Replica Jazz Club",
    "REPLICA Jazz Club EDT 100ml",
    "Pre-owned bag",
    "Second hand watch",
    # ruling C2: copycat stays counterfeit ON (_CF_V2_EXTRA_TOKENS)
    "Copycat scent",
    # ruling C1: letters-only lookarounds keep the digit-glued cases
    "1:1replica Creed Aventus 100ml",
    "Creed Aventus Replica1",
]
LUXURY_KEPT_ON = [
    "LV Neverfull MM",
    "LV-Monogram scarf",
    "Louis Vuitton Ombre Nomade",
    "Tom Ford Velvet Orchid",
]


@pytest.mark.parametrize("title", MARGIELA_TITLES)
def test_r5a_frag018_replica_survives_on(title, monkeypatch):
    _on(monkeypatch)
    assert _ps().is_counterfeit_listing(title) is False


@pytest.mark.parametrize("title", SUBSTRING_FALSE_POSITIVES)
def test_r5b_substring_false_positives_gone_on(title, monkeypatch):
    _on(monkeypatch)
    assert _ps().is_counterfeit_listing(title) is False


def _frag018_items():
    return [
        {
            "title": "Maison Margiela Replica Jazz Club Eau de Toilette 100ml",
            "price": "BHD 45.000",
            "source": "Ounass",
            "link": OUNASS_PDP,
        }
    ]


def test_r5c_frag018_shopping_price_on(monkeypatch):
    _on(monkeypatch)
    out = _ps().extract_price_from_shopping(
        "Maison Margiela Replica Jazz Club",
        _frag018_items(),
        "BHD",
        category="fragrances",
    )
    assert out is not None and out.get("amount") == 45.0


def test_r5d_reader_per_call(monkeypatch):
    ps = _ps()
    title = SUBSTRING_FALSE_POSITIVES[0]
    _on(monkeypatch)
    assert ps.is_counterfeit_listing(title) is False
    _off(monkeypatch)
    assert ps.is_counterfeit_listing(title) is True
    _on(monkeypatch)
    assert ps.is_counterfeit_listing(title) is False


@pytest.mark.parametrize("name", LV_FALSE_POSITIVES)
def test_r6a_lv_false_positives_gone_on(name, monkeypatch):
    _on(monkeypatch)
    assert _ps().is_luxury_brand(name) is False


@pytest.mark.parametrize("name", LV_ALIASES)
def test_r6b_lv_whole_token_aliases_on(name, monkeypatch):
    _on(monkeypatch)
    assert _ps().is_luxury_brand(name) is True


def test_r6c_calvin_klein_floor_on(monkeypatch):
    _on(monkeypatch)
    ps = _ps()
    assert ps.is_implausible_low_fragrance_price(CK_NAME, 18.0) is False
    assert ps._is_designer_fragrance_name(CK_NAME) is False


P5_COUNTERFEIT_BASE = {
    t: True for t in (MARGIELA_TITLES + SUBSTRING_FALSE_POSITIVES + COUNTERFEIT_KEPT_ON)
}
P5_LUXURY_BASE = dict(
    {n: True for n in LV_FALSE_POSITIVES + LUXURY_KEPT_ON},
    **{n: False for n in LV_ALIASES},
)


@pytest.mark.parametrize("flag", FALSY + [None])
def test_p5_guards_off_equal_base(flag, monkeypatch):
    _off(monkeypatch, flag)
    ps = _ps()
    assert {
        t: ps.is_counterfeit_listing(t) for t in P5_COUNTERFEIT_BASE
    } == P5_COUNTERFEIT_BASE
    assert {n: ps.is_luxury_brand(n) for n in P5_LUXURY_BASE} == P5_LUXURY_BASE
    assert ps.is_implausible_low_fragrance_price(CK_NAME, 18.0) is True
    assert ps._is_designer_fragrance_name(CK_NAME) is True
    assert (
        ps.extract_price_from_shopping(
            "Maison Margiela Replica Jazz Club",
            _frag018_items(),
            "BHD",
            category="fragrances",
        )
        is None
    )
    # BLOCKER 5 shapes: a non-str title never raises
    for bad in (None, 7, True, ["replica"], {"a": 1}):
        assert isinstance(ps.is_counterfeit_listing(bad), bool)


@pytest.mark.parametrize("title", COUNTERFEIT_KEPT_ON)
def test_p6_counterfeit_on_keeps_whole_word_hits(title, monkeypatch):
    _on(monkeypatch)
    assert _ps().is_counterfeit_listing(title) is True


@pytest.mark.parametrize("name", LUXURY_KEPT_ON)
def test_p6_luxury_on_keeps_hits(name, monkeypatch):
    _on(monkeypatch)
    assert _ps().is_luxury_brand(name) is True


def test_p6b_non_str_titles_on_never_raise(monkeypatch):
    _on(monkeypatch)
    ps = _ps()
    for bad in (None, 7, True, ["replica"], {"a": 1}):
        assert isinstance(ps.is_counterfeit_listing(bad), bool)


def _hermes_accent():
    return "Herm" + chr(0xE8) + "s bag"


# Copied literal rows of tests/test_counterfeit_filter.py and
# tests/test_luxury_brands.py (the existing pin corpus, unedited).
P7_COUNTERFEIT_ROWS = [
    ("Replica Hermes Birkin Bag", True),
    ("Fake Louis Vuitton Wallet", True),
    ("Designer Inspired Handbag", True),
    ("Pre-Owned Chanel Classic Flap", True),
    ("Used Rolex Submariner Date", True),
    ("Vintage Gucci Belt", True),
    ("Dupe Charlotte Tilbury Lipstick", True),
    ("Knockoff Ray-Ban Sunglasses", True),
    ("Generic Vitamin D3 5000IU", True),
    ("Unbranded Wireless Earbuds", True),
    ("Secondhand Prada Bag", True),
    ("Hermes Nevada H'Cheval Cap", False),
    ("Louis Vuitton Neverfull MM", False),
    ("Samsung Galaxy S24 Ultra 256GB", False),
    ("Apple iPhone 16 Pro Max", False),
    ("Nike Air Max 90", False),
    ("NOW Foods Vitamin D3 5000IU 360 Softgels", False),
    ("REPLICA Watch", True),
    ("replica watch", True),
    ("Replica Watch", True),
    ("Hermes Birkin Replica Bag", True),
    ("Fake Gucci Belt Buckle", True),
    ("Vintage Louis Vuitton Speedy 30", True),
    ("Replica Hermes Cap", True),
    ("Fake Designer Watch Replica", True),
    ("Knockoff Luxury Watch Dupe", True),
    ("Pre-Owned Nike Air Jordan 1 Used", True),
    ("Nike Air Jordan 1 Retro High", False),
]
P7_LUXURY_ROWS = [
    ("Louis Vuitton LV Vers Mesh Cap", True),
    ("Hermes Nevada H'Cheval cap", True),
    ("Hermes Birkin Bag", True),
    ("Chanel No. 5 Eau de Parfum", True),
    ("Gucci Ace Sneakers", True),
    ("Rolex Submariner", True),
    ("Prada Re-Nylon Backpack", True),
    ("Nike Air Max 90", False),
    ("Samsung Galaxy S24", False),
    ("NOW Vitamin D3", False),
    ("Adidas Ultraboost", False),
    ("Generic Cotton Hat", False),
    ("LOUIS VUITTON cap", True),
    ("hermes scarf", True),
    ("Louis Vuitton Vers Mesh Cap", True),
    ("Hermes Nevada Cap", True),
    ("Nike Air Max", False),
]


@pytest.mark.parametrize("flag", ["true", None])
def test_p7_guards_parity_existing_pin_corpus(flag, monkeypatch):
    if flag:
        _on(monkeypatch)
    else:
        _off(monkeypatch)
    ps = _ps()
    assert [
        (t, ps.is_counterfeit_listing(t)) for t, _ in P7_COUNTERFEIT_ROWS
    ] == P7_COUNTERFEIT_ROWS
    rows = P7_LUXURY_ROWS + [(_hermes_accent(), True)]
    assert [(n, ps.is_luxury_brand(n)) for n, _ in rows] == rows


def test_p8_importers_bind_the_same_function(monkeypatch):
    ps = _ps()
    for name in (
        "algolia_service",
        "woocommerce_service",
        "salla_service",
        "occ_service",
        "unbxd_service",
        "noon_service",
        "magento_graphql_service",
        "zyte_service",
    ):
        mod = importlib.import_module("app.services." + name)
        assert mod.is_counterfeit_listing is ps.is_counterfeit_listing, name
    scs = importlib.import_module("app.services.structured_comparison_service")
    assert scs.validate_scrape_url is ps.validate_scrape_url
    kw_c, kw_l = set(ps.COUNTERFEIT_KEYWORDS), set(ps.LUXURY_BRAND_KEYWORDS)
    assert len(kw_c) == 21 and len(kw_l) == 29 and "lv" in kw_l and "replica" in kw_c
    _on(monkeypatch)
    ps.is_counterfeit_listing("Copycat scent")
    ps.is_luxury_brand("Centrum Silver")
    assert (
        set(ps.COUNTERFEIT_KEYWORDS) == kw_c and set(ps.LUXURY_BRAND_KEYWORDS) == kw_l
    )


def test_r5e_scs_static_wrappers_inherit_on(monkeypatch):
    """The scs class wrappers (_is_counterfeit_listing / _is_luxury_brand, the
    pin files' entry points) delegate to the edited bodies."""
    _on(monkeypatch)
    svc = importlib.import_module(
        "app.services.structured_comparison_service"
    ).StructuredComparisonService
    assert svc._is_counterfeit_listing("Rose Infused Body Oil") is False
    assert svc._is_luxury_brand("Centrum Silver") is False


# ---------------------------------------------------------------------------
# R7 / P9 - images (every tier; the scs piggyback runs for real)
# ---------------------------------------------------------------------------

R7A_DENIED = [
    FIMGS_IMG,
    "https://rwebsocket.fimgs.net/a.png",
    "https://www.fragrantica.com/x.jpg",
    "http://media.parfumo.com/x.jpg",
]


@pytest.mark.parametrize("url", R7A_DENIED)
def test_r7a_image_validator_denies_on(url, monkeypatch):
    _on(monkeypatch)
    assert _img()._is_valid_image_url(url) is False


def test_g7a_image_validator_on_keeps_allowed(monkeypatch):
    _on(monkeypatch)
    v = _img()._is_valid_image_url
    assert v(CDN_IMG) is True and v("  " + CDN_IMG + " ") is True
    assert v("ftp://cdn.perfume-shop.test/a.jpg") is False and v(None) is False


def _search_payload():
    return {
        "knowledgeGraph": {"imageUrl": FIMGS_IMG},
        "organic": [{"imageUrl": CDN_IMG}],
    }


def test_r7b_search_payload_skips_denied_on(monkeypatch):
    _on(monkeypatch)
    assert _img().extract_image_from_search(_search_payload()) == CDN_IMG


def _patch_image_paid_tiers(monkeypatch, img):
    calls = {"search_images": 0, "llm": 0}

    async def fake_search_images(*a, **k):
        calls["search_images"] += 1
        return {"images": [{"imageUrl": FIMGS_IMG}]}

    monkeypatch.setattr(img, "try_consume_serper_image_credit", lambda *a, **k: False)
    monkeypatch.setattr(img, "search_images", fake_search_images)
    return calls


def test_r7c_cascade_never_returns_denied_on(monkeypatch):
    _on(monkeypatch)
    img = _img()
    calls = _patch_image_paid_tiers(monkeypatch, img)
    out = asyncio.run(img.get_product_image_url(NAME, page_scrape_image=FIMGS_IMG))
    assert out is None and calls["search_images"] == 0
    out = asyncio.run(
        img.get_product_image_url(
            NAME, page_scrape_image=FIMGS_IMG, search_payload=_search_payload()
        )
    )
    assert out == CDN_IMG


def _patch_tier3(monkeypatch, img, picked):
    rec = {"n": 0}
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps({"image_url": picked}))
            )
        ]
    )

    async def fake_create(client, **kwargs):
        rec["n"] += 1
        return completion

    monkeypatch.setattr(img, "get_client", lambda *a, **k: object())
    monkeypatch.setattr(img._llm_breaker, "guarded_llm_create", fake_create)
    return rec


def test_r7d_tier3_denied_pick_refused_on(monkeypatch):
    _on(monkeypatch)
    img = _img()
    rec = _patch_tier3(monkeypatch, img, FIMGS_IMG)
    out = asyncio.run(
        img.extract_image_via_gpt(NAME, [{"link": FRAG_PDP, "snippet": "Oud Wood"}])
    )
    assert out is None and rec["n"] == 1


def _scs_product_info():
    return {
        "brand": "Apple",
        "name": "iPhone 15",
        "variant": None,
        "category": "electronics",
        "search_query": "Apple iPhone 15",
    }


async def _scs_fetch(page_img, cascade_img):
    from app.services.structured_comparison_service import get_comparison_service

    service = get_comparison_service()
    with (
        patch.object(service, "_get_specs", AsyncMock(return_value={"display": "6.1"})),
        patch.object(
            service,
            "_get_price",
            AsyncMock(
                return_value={
                    "amount": 350,
                    "currency": "BHD",
                    "retailer": "Apple Store",
                    "image_url": page_img,
                }
            ),
        ),
        patch.object(
            service, "_get_reviews", AsyncMock(return_value={"review_summary": {}})
        ),
        patch.object(
            service,
            "_get_verified_rating",
            AsyncMock(
                return_value={
                    "rating": 4.6,
                    "review_count": 100,
                    "rating_verified": True,
                    "rating_source": {"name": "test", "url": None},
                }
            ),
        ),
        patch(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={"organic": []}),
        ),
        patch(
            "app.services.structured_comparison_service.get_product_image_url",
            AsyncMock(return_value=cascade_img),
        ),
        patch(
            "app.services.structured_comparison_service.tier2_fill_non_negotiables",
            AsyncMock(return_value={}),
        ),
        patch(
            "app.services.structured_comparison_service.tier3_synthesize_non_negotiables",
            AsyncMock(return_value={}),
        ),
    ):
        return await service._fetch_product_data(
            _scs_product_info(),
            region="bahrain",
            include_specs=True,
            include_reviews=True,
            nocache=True,
        )


@pytest.mark.asyncio
async def test_r7e_scs_piggyback_skips_denied_on(monkeypatch):
    """Ruling B2 / C4: the Tier 1.5 piggyback override in
    structured_comparison_service runs for real; ON a denied page image never
    overrides the cascade result."""
    _on(monkeypatch)
    result = await _scs_fetch(FIMGS_IMG, CDN_IMG)
    assert result["image_url"] == CDN_IMG


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", [None, "false", "off"])
async def test_p9b_scs_piggyback_off_equals_base(flag, monkeypatch):
    _off(monkeypatch, flag)
    result = await _scs_fetch(FIMGS_IMG, CDN_IMG)
    assert result["image_url"] == FIMGS_IMG


@pytest.mark.asyncio
async def test_p9c_scs_piggyback_off_keeps_base_prefix_rule(monkeypatch):
    """Flag OFF the piggyback keeps its own inline test (no strip before the
    scheme check): a padded page image is NOT taken, exactly as at base."""
    _off(monkeypatch)
    result = await _scs_fetch(" https://store.perfume-shop.test/hero.jpg", CDN_IMG)
    assert result["image_url"] == CDN_IMG


@pytest.mark.asyncio
async def test_g9c_scs_piggyback_on_keeps_allowed(monkeypatch):
    _on(monkeypatch)
    page = "https://store.perfume-shop.test/hero.jpg"
    result = await _scs_fetch(page, CDN_IMG)
    assert result["image_url"] == page


@pytest.mark.parametrize("flag", FALSY + [None])
def test_p9_image_off_equals_base(flag, monkeypatch):
    _off(monkeypatch, flag)
    img = _img()
    for url in R7A_DENIED:
        assert img._is_valid_image_url(url) is True
    assert img.extract_image_from_search(_search_payload()) == FIMGS_IMG
    calls = _patch_image_paid_tiers(monkeypatch, img)
    assert (
        asyncio.run(img.get_product_image_url(NAME, page_scrape_image=FIMGS_IMG))
        == FIMGS_IMG
    )
    assert calls["search_images"] == 0
    rec = _patch_tier3(monkeypatch, img, FIMGS_IMG)
    out = asyncio.run(
        img.extract_image_via_gpt(NAME, [{"link": FRAG_PDP, "snippet": "Oud Wood"}])
    )
    assert out == FIMGS_IMG and rec["n"] == 1


# ---------------------------------------------------------------------------
# R10 / P12 - review display surfaces (ruling B1; post-LLM, no digest moves)
# ---------------------------------------------------------------------------


def _oudwood_organic():
    data = json.loads(OUDWOOD_FIXTURE.read_text(encoding="utf-8"))
    return data["organic"]


def _quote_reviews():
    return {
        "review_summary": {
            "highlights": [
                {"point": "[snippet_4] Smoky oud and sandalwood with a soft dry down."},
                {
                    "point": "[snippet_7] A composition of exotic smoky woods that lasts."
                },
            ]
        }
    }


def _citation_reviews():
    return {
        "review_summary": {
            "consensus": "[snippet_4] Rich smoky oud that projects well for hours.",
            "highlights": [
                {"point": "[snippet_4] Long lasting smooth oud sillage."},
                {"point": "[snippet_7] Creamy woods with a warm finish."},
            ],
        }
    }


def test_r10a_retailer_quotes_skip_denied_on(monkeypatch):
    _on(monkeypatch)
    organic = _oudwood_organic()
    assert "fragrantica.com" in organic[3]["link"]
    quotes = _rv().build_retailer_quotes_from_reviews(_quote_reviews(), organic)
    assert [q["retailer"] for q in quotes] == ["sephora.com"]
    assert quotes[0]["rating"] == 4.5


def test_r10b_citation_attribution_blank_for_denied_on(monkeypatch):
    _on(monkeypatch)
    out = _rv().clean_review_citations(_citation_reviews(), _oudwood_organic())
    rs_ = out["review_summary"]
    assert rs_["consensus"] == "Rich smoky oud that projects well for hours."
    assert [h["point"] for h in rs_["highlights"]] == [
        "Long lasting smooth oud sillage.",
        "Per sephora.com: Creamy woods with a warm finish.",
    ]


@pytest.mark.parametrize("flag", FALSY + [None])
def test_p12_review_display_off_equals_base(flag, monkeypatch):
    _off(monkeypatch, flag)
    organic = _oudwood_organic()
    quotes = _rv().build_retailer_quotes_from_reviews(_quote_reviews(), organic)
    assert [(q["retailer"], q.get("rating")) for q in quotes] == [
        ("fragrantica.com", 4.3),
        ("sephora.com", 4.5),
    ]
    assert quotes[0]["text"] == organic[3]["snippet"].strip()
    out = _rv().clean_review_citations(_citation_reviews(), organic)
    rs_ = out["review_summary"]
    assert (
        rs_["consensus"]
        == "Per fragrantica.com: Rich smoky oud that projects well for hours."
    )
    assert [h["point"] for h in rs_["highlights"]] == [
        "Per fragrantica.com: Long lasting smooth oud sillage.",
        "Per sephora.com: Creamy woods with a warm finish.",
    ]


# ---------------------------------------------------------------------------
# R11 / P13 / G11 - the never-fetched chokepoint (ruling B2)
# ---------------------------------------------------------------------------


def test_r11a_validate_scrape_url_denies_on(monkeypatch):
    _on(monkeypatch)
    v = _ps().validate_scrape_url
    assert v(FRAG_PDP) is False
    assert v(FRAG_BH_PDP) is False
    assert v("https://www.parfumo.de/Parfums/Tom_Ford/Oud_Wood") is False
    assert v(OUNASS_PDP) is True


@pytest.mark.parametrize("flag", FALSY + [None])
def test_p13_validate_scrape_url_off_equals_base(flag, monkeypatch):
    _off(monkeypatch, flag)
    v = _ps().validate_scrape_url
    assert v(FRAG_PDP) is True and v(FRAG_BH_PDP) is True and v(OUNASS_PDP) is True
    assert v("https://www.fragrantica.com/search/?q=x") is False


def _harvest(results_by_tier):
    scs = importlib.import_module("app.services.structured_comparison_service")
    return scs._harvest_organic_pdp_candidates(
        results_by_tier, "fragrances", query_name="Tom Ford Oud Wood"
    )


@pytest.mark.parametrize("flag", ["true", None])
def test_g11b_denied_bh_locale_link_never_harvested(flag, monkeypatch):
    """Review RC1: with the global-tier refusal gone ("as if absent"), a
    /bh-en/ Fragrantica path would fall to the BH-locale rung. The harvest
    must stay [] in BOTH states (real registry)."""
    monkeypatch.setenv("ENABLE_ORGANIC_PDP_HARVEST", "true")
    if flag:
        _on(monkeypatch)
    else:
        _off(monkeypatch)
    results = {
        "global": {
            "organic": [
                {
                    "link": FRAG_BH_PDP,
                    "title": "Tom Ford Oud Wood",
                    "snippet": "Oud Wood",
                }
            ]
        }
    }
    assert _harvest(results) == []


# ---------------------------------------------------------------------------
# R9 - the flag-free KB-writer guard
# ---------------------------------------------------------------------------


def test_r9a_kb_guard(monkeypatch):
    _on(monkeypatch)
    allowed = _dh_fn("kb_source_allowed")
    for v in (OUNASS_PDP, "Boots", None, ""):
        assert allowed(v) is True, v
    for v in ("https://www.parfumo.de/x", "Fragrantica", "fimgs.net"):
        assert allowed(v) is False, v
    err = _attr(_dh(), "DeniedSourceError")
    assert isinstance(err, type) and issubclass(err, ValueError)
    with pytest.raises(ValueError) as exc:
        _dh_fn("assert_kb_source_allowed")("fimgs.net")
    assert isinstance(exc.value, err) and str(exc.value) == "denied source"
    assert _dh_fn("assert_kb_source_allowed")("Boots") is None


@pytest.mark.parametrize("flag", FALSY + [None])
def test_r9b_kb_guard_is_flag_free(flag, monkeypatch):
    _off(monkeypatch, flag)
    assert _dh_fn("kb_source_allowed")("fimgs.net") is False
    assert _dh_fn("kb_source_allowed")("https://bahrain.ounass.com/x") is True


# ---------------------------------------------------------------------------
# P11 / P14 - falsy flag spellings; the D03b scope fence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", FALSY + [None])
def test_p11_reader_falsy_consumers_as_base(flag, monkeypatch):
    _off(monkeypatch, flag)
    sr, ps, img, rs = _sr(), _ps(), _img(), _rs()
    assert ps.is_counterfeit_listing(SUBSTRING_FALSE_POSITIVES[0]) is True
    assert ps.is_luxury_brand("Centrum Silver") is True
    assert (
        sr.build_site_discovery_query(
            "Dior Sauvage", "fragrances", tier="global", limit=8
        )
        == REAL_GLOBAL_QUERY_OFF
    )
    assert img._is_valid_image_url(FIMGS_IMG) is True
    assert ps.validate_scrape_url(FRAG_PDP) is True
    assert rs.get_rating_tier("Fragrantica") == 2


def test_p14_url_files_untouched_scope_fence():
    """Ruling R-D03-1: D03 edits no url_* file (the URL half is D03b)."""
    for rel in ("app/api/url_routes.py", "app/services/url_extraction_service.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "deny_hosts" not in text and "denied_source" not in text, rel
        assert "ENABLE_DATA_GUARDS_V2" not in text, rel


# ---------------------------------------------------------------------------
# F1 - fix round 1 (specs/RULINGS_FIX1_D03.md, after the two NOT_READY
# adversaries on 5244f716). APPENDED rows only; every row above is unchanged.
#   * F1-1 (MAJ-1 = MAJ-E1, the Serper-Shopping door) and F1-4 (userinfo and
#     the backslash authority) R rows fail at 5244f716 on an AssertionError.
#   * F1-2 (two-level suffix), F1-3 (deny before dedup), F1-5 (piggyback
#     strip) are PIN rows green at 5244f716, each proven by its mutant (A9, D6,
#     G3). F1-6 (the patchable validator) fails at 5244f716 by construction
#     (the by-name import is the defect it pins).
# ---------------------------------------------------------------------------
import logging  # noqa: E402 - the fix-round rows read the price_service canary lines

W41 = "ENABLE_SHOPPING_CURRENCY_TRUTH"
SHOP_NAME = "Tom Ford Oud Wood Eau de Parfum 100ml"
ALLOWED_SHOP_LINK = "https://bh.perfume-shop.test/products/tom-ford-oud-wood-100ml"
NEUTRAL_SHOP_LINK = "https://store.perfume-shop.test/products/tom-ford-oud-wood-100ml"
# (denied by link, denied by source name, allowed): both denied rows are
# CHEAPER than the allowed one, so at 5244f716 a denied row wins the sort;
# every amount clears the premium 50 BHD / 100 ml floor, so the stash's
# is_price_showable gate admits all three.
SHOP_PRICES = {
    "BHD": ("BHD 55.000", "BHD 56.000", "BHD 60.000"),
    "AED": ("AED 550.00", "AED 560.00", "AED 600.00"),
}
SHOP_ALLOWED_AMOUNT = {"BHD": 60.0, "AED": 600.0}
BACKSLASH = chr(92)


def _w41(mp, state):
    if state == "on":
        mp.setenv(W41, "true")
    else:
        mp.delenv(W41, raising=False)


def _shop_row(price, source, link):
    return {"title": SHOP_NAME, "price": price, "source": source, "link": link}


def _shop_pool(ask):
    p_link, p_src, p_ok = SHOP_PRICES[ask]
    return [
        _shop_row(p_link, "Perfume Outlet", FRAG_BH_PDP),
        _shop_row(p_src, "Fragrantica", NEUTRAL_SHOP_LINK),
        _shop_row(p_ok, "Perfume Shop BH", ALLOWED_SHOP_LINK),
    ]


def _stash_seed(full_name, pool, ask):
    from app.services.structured_comparison_service import get_comparison_service

    service = get_comparison_service()
    service._shopping_items_cache[full_name] = pool
    service._seed_shortcircuit_candidates(
        full_name, kind="tier1_shopping", currency=ask
    )
    return [
        (c.get("retailer"), (c.get("raw_data") or {}).get("url"))
        for c in service._price_candidates.get(full_name, [])
    ]


def _evidence_recorder(monkeypatch, module):
    seen = []
    real = module._shopping_bh_host_evidence

    def recorder(link, **kwargs):
        seen.append(link)
        return real(link, **kwargs)

    monkeypatch.setattr(module, "_shopping_bh_host_evidence", recorder)
    return seen


@pytest.mark.parametrize("ask", ["BHD", "AED"])
@pytest.mark.parametrize("w41", ["off", "on"])
def test_f1_1a_shopping_door_drops_denied_rows_on(w41, ask, monkeypatch):
    """F1-1: ON, a Shopping row whose link host OR source name is banned is
    never priced: the next allowed row wins, a pool of only denied rows yields
    None (both W4-1 states, a BHD and an AED ask; the real function)."""
    _on(monkeypatch)
    _w41(monkeypatch, w41)
    ps = _ps()
    pool = _shop_pool(ask)
    out = ps.extract_price_from_shopping(SHOP_NAME, pool, ask, category="fragrances")
    assert out is not None
    assert (out.get("retailer"), out.get("url")) == (
        "Perfume Shop BH",
        ALLOWED_SHOP_LINK,
    )
    assert out.get("amount") == SHOP_ALLOWED_AMOUNT[ask]
    assert (
        ps.extract_price_from_shopping(SHOP_NAME, pool[:2], ask, category="fragrances")
        is None
    )


@pytest.mark.parametrize("ask", ["BHD", "AED"])
@pytest.mark.parametrize("link", [FRAG_BH_PDP, FRAG_PDP])
def test_f1_1b_evidence_helper_denies_on(link, ask, monkeypatch):
    """F1-1: the W4-1 host-evidence helper itself never reads a banned link as
    evidence (before every rung: the /bh-en/ shape is no BH marker)."""
    _on(monkeypatch)
    _w41(monkeypatch, "on")
    reasons = []
    assert (
        _ps()._shopping_bh_host_evidence(link, ask_currency=ask, reason_out=reasons)
        is False
    )
    assert reasons == ["denied_host"]


def test_f1_1c_denied_rows_reach_no_currency_or_evidence_logic_on(monkeypatch, caplog):
    """F1-1: a denied row is dropped BEFORE the currency and evidence logic of
    the front door: the evidence helper never sees its link and no W4-1 canary
    line (pend or relabel) is written for it (kills the check-after-evidence
    mutant)."""
    _on(monkeypatch)
    _w41(monkeypatch, "on")
    ps = _ps()
    seen = _evidence_recorder(monkeypatch, ps)
    pool = [_shop_row("TRY 1.299,00", "Perfume Outlet", FRAG_PDP)] + _shop_pool("BHD")
    with caplog.at_level(logging.INFO, logger="app.services.price_service"):
        out = ps.extract_price_from_shopping(
            SHOP_NAME, pool, "BHD", category="fragrances"
        )
    assert out is not None and out.get("url") == ALLOWED_SHOP_LINK
    assert seen == [ALLOWED_SHOP_LINK]
    truth = [
        r.getMessage()
        for r in caplog.records
        if "[SHOPPING_CURRENCY_TRUTH]" in r.getMessage()
    ]
    assert not any("pend unconvertible" in m for m in truth), truth
    assert not any(
        "fragrantica" in m or "store.perfume-shop.test" in m for m in truth
    ), truth
    # ONE D03 line per call, host only (never a title, a price or a URL path).
    d03 = [
        r.getMessage() for r in caplog.records if "[DATA_GUARDS_V2]" in r.getMessage()
    ]
    assert len(d03) == 1, d03
    assert (
        "count=3" in d03[0]
        and "by=link" in d03[0]
        and "host=www.fragrantica.com" in d03[0]
    ), d03
    assert SHOP_NAME not in d03[0] and "1826" not in d03[0] and "BHD" not in d03[0], d03


@pytest.mark.parametrize("ask", ["BHD", "AED"])
@pytest.mark.parametrize("w41", ["off", "on"])
def test_f1_1d_stash_never_seeds_denied_rows_on(w41, ask, monkeypatch):
    """F1-1: the scs re-selection stash (the M13-10 back door) seeds no denied
    Shopping row (both W4-1 states, both asks)."""
    _on(monkeypatch)
    _w41(monkeypatch, w41)
    assert _stash_seed(SHOP_NAME, _shop_pool(ask), ask) == [
        ("Perfume Shop BH", ALLOWED_SHOP_LINK)
    ]


def test_f1_1e_stash_denied_rows_reach_no_evidence_on(monkeypatch):
    """F1-1: the stash drops a denied row before its W4-1 evidence call."""
    _on(monkeypatch)
    _w41(monkeypatch, "on")
    scs = importlib.import_module("app.services.structured_comparison_service")
    seen = _evidence_recorder(monkeypatch, scs)
    _stash_seed(SHOP_NAME, _shop_pool("BHD"), "BHD")
    assert seen == [ALLOWED_SHOP_LINK]


@pytest.mark.parametrize("flag", FALSY + [None])
def test_f1_1p_shopping_door_off_equals_base(flag, monkeypatch, caplog):
    """F1-1 flag OFF = the 5244f716 door (the adversary probe3 shape pinned):
    W4-1 ON, BHD ask, a Fragrantica /bh-en/ row is priced converted_usd with
    the base reason global_tier (W4-1 OFF: local_bhd); in the mixed pool the
    cheapest denied row wins, the stash seeds every row, no D03 line."""
    _off(monkeypatch, flag)
    ps = _ps()
    probe = [_shop_row("BHD 45.000", "Fragrantica", FRAG_BH_PDP)]
    _w41(monkeypatch, "on")
    reasons = []
    assert (
        ps._shopping_bh_host_evidence(
            FRAG_BH_PDP, ask_currency="BHD", reason_out=reasons
        )
        is False
    )
    assert reasons == ["global_tier"]
    with caplog.at_level(logging.INFO, logger="app.services.price_service"):
        out = ps.extract_price_from_shopping(
            SHOP_NAME, probe, "BHD", category="fragrances"
        )
    assert (
        out is not None
    ), "flag OFF the denied Shopping row is priced exactly as at 5244f716"
    assert (out["retailer"], out["url"], out["amount"], out["source_method"]) == (
        "Fragrantica",
        FRAG_BH_PDP,
        45.0,
        "converted_usd",
    )
    msgs = [r.getMessage() for r in caplog.records]
    assert any("reason=global_tier" in m for m in msgs), msgs
    assert not any("[DATA_GUARDS_V2]" in m for m in msgs), msgs
    for w41 in ("off", "on"):
        _w41(monkeypatch, w41)
        for ask in ("BHD", "AED"):
            out = ps.extract_price_from_shopping(
                SHOP_NAME, _shop_pool(ask), ask, category="fragrances"
            )
            assert out is not None, (w41, ask)
            assert (out["retailer"], out["url"]) == ("Perfume Outlet", FRAG_BH_PDP), (
                w41,
                ask,
            )
            assert len(_stash_seed(SHOP_NAME, _shop_pool(ask), ask)) == 3, (w41, ask)
    _w41(monkeypatch, "off")
    out = ps.extract_price_from_shopping(SHOP_NAME, probe, "BHD", category="fragrances")
    assert out is not None and out["source_method"] == "local_bhd"


F1_2_TWO_LEVEL_TRUE = [
    "fragrantica.co.uk",
    "www.parfumo.com.au",
    "basenotes.co.nz",
    "fimgs.net:8443",
]
F1_2_TWO_LEVEL_FALSE = ["fragrantica.co.uk.evil.test", "co.uk", "notfragrantica.co.uk"]


def test_f1_2_two_level_public_suffix_labels():
    """F1-2 (MIN-1, mutant A9): an UNLISTED edition under a two-level public
    suffix is denied by the registrable label (labels[-3])."""
    host, url = _dh_fn("is_denied_host"), _dh_fn("is_denied_url")
    for h in F1_2_TWO_LEVEL_TRUE:
        assert host(h) is True, h
        assert url("https://" + h + "/x") is True, h
    for h in F1_2_TWO_LEVEL_FALSE:
        assert host(h) is False, h
        assert url("https://" + h + "/x") is False, h


def test_f1_3_collect_ratings_deny_skip_precedes_dedup(monkeypatch):
    """F1-3 (MIN-2, block-move D6): a link-denied item with a neutral source
    name does not consume the dedup key; the next allowed item with the same
    source name is listed."""
    _on(monkeypatch)
    same_source_allowed = dict(
        _neutral_denied_link_item(), rating=4.4, link="https://somestore.test/oud-wood"
    )
    out = _rs().collect_retailer_ratings(
        NAME, {NAME: [_neutral_denied_link_item(), same_source_allowed]}
    )
    assert [(r["source"], r["rating"]) for r in out] == [("somestore.com", 4.4)]


def _frag_userinfo_url():
    # built at run time: no userinfo-shaped literal in the file
    return "https://" + "u" + "@" + "www.fragrantica.com/perfume/x-1.html"


def _dotted_userinfo_url():
    return "https://" + "a.b" + "@" + "fragrantica.com/perfume/x-1.html"


def _backslash_url():
    # https://fragrantica.com<backslash>@evil.test/... : a WHATWG parser reads
    # the host fragrantica.com (the backslash ends the authority), urlsplit
    # reads evil.test.
    return "https://fragrantica.com" + BACKSLASH + "@evil.test/perfume/x-1.html"


def _f1_4_organic(link):
    return [
        {
            "link": link,
            "title": "Oud Wood",
            "snippet": "Smoky oud and sandalwood with a soft dry down that lasts.",
        },
        {
            "link": "https://www.sephora.com/product/oud-wood",
            "title": "Oud Wood",
            "snippet": "A composition of exotic smoky woods that lasts for hours.",
        },
    ]


def _f1_4_reviews():
    return {
        "review_summary": {
            "consensus": "[snippet_1] Rich smoky oud that projects well.",
            "highlights": [
                {"point": "[snippet_1] Long lasting smooth oud sillage."},
                {"point": "[snippet_2] Creamy woods with a warm finish."},
            ],
        }
    }


@pytest.mark.parametrize("kind", ["userinfo", "backslash"])
def test_f1_4a_review_display_reads_the_hostname_on(kind, monkeypatch):
    """F1-4 (MIN-3 + MIN-E7): the review display deny reads the parsed
    hostname (userinfo removed) and the conservative backslash rule, never
    the netloc: neither a quote nor a 'Per <domain>:' attribution."""
    _on(monkeypatch)
    link = _frag_userinfo_url() if kind == "userinfo" else _backslash_url()
    rv = _rv()
    quotes = rv.build_retailer_quotes_from_reviews(_f1_4_reviews(), _f1_4_organic(link))
    assert [q["retailer"] for q in quotes] == ["sephora.com"]
    rs_ = rv.clean_review_citations(_f1_4_reviews(), _f1_4_organic(link))[
        "review_summary"
    ]
    assert rs_["consensus"] == "Rich smoky oud that projects well."
    assert [h["point"] for h in rs_["highlights"]] == [
        "Long lasting smooth oud sillage.",
        "Per sephora.com: Creamy woods with a warm finish.",
    ]


def test_f1_4b_backslash_authority_denied_conservatively(monkeypatch):
    """F1-4 (MIN-E7): an authority carrying a backslash is denied when a banned
    label appears in it anywhere (is_denied_url, so every consumer)."""
    fn = _dh_fn("is_denied_url")
    assert fn(_backslash_url()) is True
    assert fn("https://www.parfumo.de" + BACKSLASH + "@evil.test/x") is True
    assert fn("fimgs.net" + BACKSLASH + "@cdn.evil.test/a.jpg") is True
    _on(monkeypatch)
    img = "https://fimgs.net" + BACKSLASH + "@cdn.evil.test/a.jpg"
    assert _img()._is_valid_image_url(img) is False


def test_f1_4p_hostname_rules_pinned():
    """F1-4 PIN: the hostname (never the netloc) decides; the conservative rule
    reads the AUTHORITY only (a label in the query or the path is not a host)."""
    fn = _dh_fn("is_denied_url")
    assert fn(_frag_userinfo_url()) is True
    assert fn(_dotted_userinfo_url()) is True
    assert fn("https://evil.test/?u=fragrantica.com") is False
    assert fn("https://evil.test/" + BACKSLASH + "fragrantica.com") is False
    assert fn("https://evil.test" + BACKSLASH + "?u=fragrantica.com") is False
    assert fn("https://" + "fragrantica.com" + "@" + "evil.test/x") is False
    assert fn("https://evil.test" + BACKSLASH + "@notfragrantica.com/x") is False


@pytest.mark.parametrize("flag", FALSY + [None])
def test_f1_4q_review_userinfo_off_equals_base(flag, monkeypatch):
    """F1-4 flag OFF: the userinfo link is quoted and attributed exactly as at
    5244f716 (the netloc-derived domain)."""
    _off(monkeypatch, flag)
    shown = "u" + "@" + "fragrantica.com"
    rv = _rv()
    quotes = rv.build_retailer_quotes_from_reviews(
        _f1_4_reviews(), _f1_4_organic(_frag_userinfo_url())
    )
    assert [q["retailer"] for q in quotes] == [shown, "sephora.com"]
    rs_ = rv.clean_review_citations(
        _f1_4_reviews(), _f1_4_organic(_frag_userinfo_url())
    )["review_summary"]
    assert rs_["consensus"] == "Per %s: Rich smoky oud that projects well." % shown


@pytest.mark.asyncio
async def test_f1_5_piggyback_on_stores_the_stripped_url(monkeypatch):
    """F1-5 (MIN-5, mutant G3): ON a padded JSON-LD page image is stored
    STRIPPED; a padded image on a banned host is still refused."""
    _on(monkeypatch)
    page = "https://cdn.store.test/x.jpg"
    result = await _scs_fetch("  " + page + " ", CDN_IMG)
    assert result["image_url"] == page
    result = await _scs_fetch("  " + FIMGS_IMG + " ", CDN_IMG)
    assert result["image_url"] == CDN_IMG


@pytest.mark.asyncio
async def test_f1_6_piggyback_validator_is_patchable_on(monkeypatch):
    """F1-6 (MIN-E9): scs reaches image_service._is_valid_image_url through the
    module attribute, so patching the attribute changes the piggyback verdict."""
    _on(monkeypatch)
    img = _img()
    seen = []

    def refuse(value):
        seen.append(value)
        return False

    monkeypatch.setattr(img, "_is_valid_image_url", refuse)
    page = "https://store.perfume-shop.test/hero.jpg"
    result = await _scs_fetch(page, CDN_IMG)
    assert result["image_url"] == CDN_IMG
    assert page in seen
