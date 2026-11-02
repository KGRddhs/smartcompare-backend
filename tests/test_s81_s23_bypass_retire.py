"""S81-G1 unit S81-23 BYPASS-RETIRE -- the frozen RED file.

Flag ``ENABLE_SCRAPEDO_SUPER`` (new name, read PER CALL by
``app.services.scrapedo_service.scrapedo_super_enabled``), with the TRI-STATE
transition of RULINGS_S81_G1 R-G1-6: the new name UNSET -> the legacy
``SCRAPEDO_SUPER`` read exactly as the base expression (``.lower() == "true"``,
no strip; "TRUE" ON, "1" / " true" OFF), now per call; the new name SET -> it
wins in both directions (``false`` is a kill switch even with the legacy on).
R-G1-7: ``scripts/seed_zyte_luxury.py`` keeps its scaffold with both seed lists
emptied (sephora.me retired). Spec: ``.qa-s80/S81-G1_UNIT_SPEC.md`` (unit S81-23,
sections 2, 5 and 6).

Row map: RED R1-R9 (``test_s23_rN_*``) fail at base on an AssertionError only;
PIN P1-P4 (``test_s23_pN_*``) are green at base and run with the FULL
configuration (a synthetic token built at run time, ``SCRAPEDO_GEOCODE=ae``
where stated, an httpx recorder on both render functions, the routing
registry pinned to the literal rows).

Hermetic: httpx is patched at ``app.services.scrapedo_service.httpx.AsyncClient``;
the seed run traps every non-loopback socket attempt (the
tests/test_seed_zyte_guard.py guard, copied) and patches the GPT parse.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest

NEW_FLAG = "ENABLE_SCRAPEDO_SUPER"
LEGACY = "SCRAPEDO_SUPER"
GEO = "SCRAPEDO_GEOCODE"
REPO = Path(__file__).resolve().parents[1]
RENDER_URL = "https://store-a.example.com/products/x"
SEPHORA = "sephora.me"
CATEGORIES = ("makeup", "skincare", "fragrances", "haircare")
_SEED_IMPORT_ENV = ("ENABLE_ZYTE_RENDER", "PRICE_RACE_TIMEOUT", "ZYTE_TIMEOUT", "WARMER_CONTEXT")
_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0", b"127.0.0.1", b"::1", b"localhost"}


def _vid(value):
    """A space-free test id for an env spelling (None = unset)."""
    if value is None:
        return "unset"
    if value == "":
        return "empty"
    core = value.strip().replace(" ", "_")
    return core + "_padded" if core != value else core


def _token():
    """A synthetic, low-entropy token word built at run time."""
    return "-".join(["synthetic", "render", "word"])


def _sd():
    return importlib.import_module("app.services.scrapedo_service")


def _sr():
    return importlib.import_module("app.services.source_router")


def _reader():
    fn = getattr(_sd(), "scrapedo_super_enabled", None)
    assert callable(fn), "S81-23: scrapedo_service.scrapedo_super_enabled is missing"
    return fn


def _set(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


@pytest.fixture(autouse=True)
def _s23_env(monkeypatch):
    """Every row sets its own state; the base process cache is reset before and
    after (the reset hook stays callable after S81-23); the seed module's
    import-time env writes are restored."""
    for name in (NEW_FLAG, LEGACY, GEO, "ENABLE_MERCHANT_REGISTRY_DB", "ENABLE_DATA_GUARDS_V2",
                 "ENABLE_LONGEST_HOST_MATCH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SCRAPEDO_API_TOKEN", _token())
    saved = {name: os.environ.get(name) for name in _SEED_IMPORT_ENV}
    sd = _sd()
    sd.reset_super_flags_cache()
    sr = _sr()
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", list(sr._LITERAL_ROWS))
    monkeypatch.setattr(sr, "_ROUTABLE_MEMO", None, raising=False)
    yield
    sd.reset_super_flags_cache()
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


class _Recorder:
    def __init__(self):
        self.calls = []

    def client_cls(self):
        rec = self

        class _Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url, params=None, **kwargs):
                rec.calls.append({"url": url, "params": dict(params or {})})
                return SimpleNamespace(status_code=200, text="<html>" + "x" * 600 + "</html>",
                                       headers={})

        return _Client


def _render_params(monkeypatch):
    """The GET params both render functions send, in order [render_page,
    render_page_with_status]."""
    sd = _sd()
    rec = _Recorder()
    monkeypatch.setattr(sd.httpx, "AsyncClient", rec.client_cls())
    html = asyncio.run(sd.render_page(RENDER_URL))
    out = asyncio.run(sd.render_page_with_status(RENDER_URL))
    assert html is not None and out[0] is not None and out[1] == 200
    assert len(rec.calls) == 2
    return [c["params"] for c in rec.calls]


def _base_params(super_on, geo="ae"):
    p = {"token": _token(), "url": RENDER_URL, "render": "true"}
    if super_on:
        p.update({"super": "true", "geoCode": geo})
    return p


def _routed_bahrain(category):
    return [s.domain for s in _sr().get_sources_for_category(category) if s.tier == "bahrain"]


# ===========================================================================
# RED rows
# ===========================================================================
@pytest.mark.parametrize("legacy", [None, "false"], ids=_vid)
@pytest.mark.parametrize("new", ["true", "1", "yes", " ON "], ids=_vid)
def test_s23_r1_reader_exists_and_wins(new, legacy, monkeypatch):
    """R1 (2.1): the new reader exists and a truthy ENABLE_SCRAPEDO_SUPER wins
    over an unset / false legacy SCRAPEDO_SUPER."""
    fn = _reader()
    _set(monkeypatch, NEW_FLAG, new)
    _set(monkeypatch, LEGACY, legacy)
    assert fn() is True


@pytest.mark.parametrize("new", ["false", "0", "off", ""], ids=_vid)
def test_s23_r2_new_false_kills_legacy(new, monkeypatch):
    """R2 (2.1): a set-but-falsy ENABLE_SCRAPEDO_SUPER is a kill switch even
    while the legacy SCRAPEDO_SUPER is true."""
    sd = _sd()
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.setenv(NEW_FLAG, new)
    assert sd._super_params() == {}
    assert sd._super_enabled() is False


def test_s23_r3_per_call_no_reset(monkeypatch):
    """R3 (2.1): read per call -- flipping the env takes effect on the NEXT call
    WITHOUT the reset hook (the base cached the first read for the process)."""
    sd = _sd()
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.setenv(GEO, "ae")
    assert sd._super_params() == {"super": "true", "geoCode": "ae"}
    monkeypatch.setenv(NEW_FLAG, "false")
    assert sd._super_params() == {}
    assert sd._super_enabled() is False
    monkeypatch.setenv(NEW_FLAG, "true")
    assert sd._super_params() == {"super": "true", "geoCode": "ae"}


def test_s23_r4_render_params_new_off(monkeypatch):
    """R4 (2.1/2.4): both render functions with the new flag false and the
    legacy true send exactly {token, url, render}."""
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.setenv(GEO, "ae")
    monkeypatch.setenv(NEW_FLAG, "false")
    assert _render_params(monkeypatch) == [_base_params(False), _base_params(False)]


def test_s23_r5_routing_new_off(monkeypatch):
    """R5 (2.4): new false + legacy true -> the requires_super row (sephora.me)
    is NOT routed; new true + legacy unset -> it is."""
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.setenv(NEW_FLAG, "false")
    for cat in ("makeup", "skincare", "fragrances"):
        assert SEPHORA not in _routed_bahrain(cat), cat
    monkeypatch.delenv(LEGACY, raising=False)
    monkeypatch.setenv(NEW_FLAG, "true")
    for cat in ("makeup", "skincare", "fragrances"):
        assert SEPHORA in _routed_bahrain(cat), cat


def _seeder():
    return importlib.import_module("scripts.seed_zyte_luxury")


def test_s23_r6_seed_lists_retired():
    """R6 (2.2, R-G1-7): the scaffold stays, both seed lists are empty and no
    seed string mentions sephora."""
    seeder = _seeder()
    assert seeder.LUXURY_PAIRS == []
    assert seeder.TRUTH_CRITICAL_SEEDS == []
    blob = repr(seeder.LUXURY_PAIRS) + repr(seeder.TRUTH_CRITICAL_SEEDS)
    assert "sephora" not in blob.lower()


@pytest.fixture
def blocked_sockets(monkeypatch):
    """Hard no-outbound-network guard (copied from tests/test_seed_zyte_guard.py):
    every non-loopback resolution / connect is trapped, counted and RAISES."""
    attempts: list = []
    orig_gai = socket.getaddrinfo
    orig_connect = socket.socket.connect
    orig_create = socket.create_connection

    def _boom_gai(host, *a, **k):
        if host not in _LOOPBACK:
            attempts.append(("getaddrinfo", str(host)))
            raise RuntimeError("no-network guard: getaddrinfo(%r)" % (host,))
        return orig_gai(host, *a, **k)

    def _boom_connect(self, address, *a, **k):
        host = address[0] if isinstance(address, (tuple, list)) else address
        if host not in _LOOPBACK:
            attempts.append(("connect", str(host)))
            raise RuntimeError("no-network guard: connect(%r)" % (address,))
        return orig_connect(self, address, *a, **k)

    def _boom_create(address, *a, **k):
        host = address[0] if isinstance(address, (tuple, list)) else address
        if host not in _LOOPBACK:
            attempts.append(("create_connection", str(host)))
            raise RuntimeError("no-network guard: create_connection(%r)" % (address,))
        return orig_create(address, *a, **k)

    monkeypatch.setattr(socket, "getaddrinfo", _boom_gai)
    monkeypatch.setattr(socket.socket, "connect", _boom_connect)
    monkeypatch.setattr(socket, "create_connection", _boom_create)
    return attempts


def test_s23_r7_main_makes_no_zyte_call(monkeypatch, blocked_sockets):
    """R7 (2.2): with a key exported at startup and no args, main() seeds
    nothing: {"genuine": 0, "pending": 0}, zero trapped socket attempts and no
    GPT parse (base: the pinned sephora.me PDP reaches the Zyte fetch)."""
    seeder = _seeder()
    parses = []

    async def _no_parse(pair):
        parses.append(pair)
        return {"products": []}, {}

    es = importlib.import_module("app.services.extraction_service")
    monkeypatch.setattr(es, "parse_product_query", _no_parse)
    key_word = "-".join(["exported", "at", "startup"])
    monkeypatch.setattr(seeder, "_STARTUP_ZYTE_KEY", key_word)
    monkeypatch.setenv("ZYTE_API_KEY", key_word)
    monkeypatch.setenv("ZYTE_RETRIES", "1")
    monkeypatch.setenv("ZYTE_RETRY_BACKOFF", "0")
    monkeypatch.setenv("ENABLE_ZYTE_RENDER", "true")
    monkeypatch.setattr("sys.argv", ["seed_zyte_luxury"])
    totals = asyncio.run(seeder.main())
    assert totals == {"genuine": 0, "pending": 0}
    assert blocked_sockets == []
    assert parses == []


_FORBIDDEN_CLAUDE_MD = (
    "defeats most Cloudflare",
    "cracks Akamai",
    "residential proxies, only when",
    "#93 specifies 20+ samples",
    "controls curl cracks",
)
_G1_HEADING = "**SESSION 81 flags (S81-G1 PRICE-PIPELINE"


def _g1_block(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(_G1_HEADING):
            block = [line]
            for nxt in lines[i + 1:]:
                if not nxt.strip() or nxt.startswith("**SESSION") or nxt.startswith("## "):
                    break
                block.append(nxt)
            return "\n".join(block)
    return None


def test_s23_r8_claude_md_neutral():
    """R8 (3.5): the wall-praising CLAUDE.md lines are rewritten neutrally and
    the S81-G1 block (column 0) names ENABLE_SCRAPEDO_SUPER and the robots policy."""
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    for phrase in _FORBIDDEN_CLAUDE_MD:
        assert phrase not in text, phrase
    block = _g1_block(text)
    assert block is not None, "the S81-G1 block heading is missing at column 0"
    assert NEW_FLAG in block
    assert "2026-08-31-robots-unreadable-ruling.md" in block


def test_s23_r9_docstring_neutral():
    """R9 (2.1): the module docstring no longer advertises an anti-bot bypass."""
    doc = _sd().__doc__ or ""
    assert "anti-bot bypass" not in doc


# ===========================================================================
# PIN rows (green at base; the new name UNSET = today's legacy behaviour)
# ===========================================================================
P1_CASES = [(None, False), ("false", False), ("true", True), ("TRUE", True), ("1", False),
            (" true", False)]


@pytest.mark.parametrize("legacy,super_on", P1_CASES, ids=[_vid(c[0]) for c in P1_CASES])
def test_s23_p1_unset_matches_base_params(legacy, super_on, monkeypatch):
    """P1 (2.3): new name unset -> the params of both render functions equal the
    base literal for every legacy value (super + geoCode exactly for
    "true"/"TRUE"; no strip, "1" stays OFF)."""
    _set(monkeypatch, LEGACY, legacy)
    monkeypatch.setenv(GEO, "ae")
    assert _render_params(monkeypatch) == [_base_params(super_on), _base_params(super_on)]


P2_ROUTED = {'off': {'fragrances': ['gcc.luluhypermarket.com',
                                    'nasserpharmacy.com',
                                    'boutiqaat.com',
                                    'bh.asgharali.com',
                                    'en-bh.ajmal.com',
                                    'alhajisbahrain.com',
                                    'jalilaperfumes.com',
                                    'bahrain.ounass.com',
                                    'noon.com'],
                     'haircare': ['gcc.luluhypermarket.com',
                                  'bn.boots.com',
                                  'nasserpharmacy.com',
                                  'bahrainpharmacy.com',
                                  'boutiqaat.com'],
                     'makeup': ['gcc.luluhypermarket.com',
                                'bn.boots.com',
                                'bolo.bh',
                                'nasserpharmacy.com',
                                'bahrainpharmacy.com',
                                'boutiqaat.com',
                                'bahrain.ounass.com'],
                     'skincare': ['gcc.luluhypermarket.com',
                                  'bn.boots.com',
                                  'bolo.bh',
                                  'nasserpharmacy.com',
                                  'bahrainpharmacy.com',
                                  'boutiqaat.com']},
             'on': {'fragrances': ['gcc.luluhypermarket.com',
                                   'nasserpharmacy.com',
                                   'sephora.me',
                                   'boutiqaat.com',
                                   'bh.asgharali.com',
                                   'en-bh.ajmal.com',
                                   'alhajisbahrain.com',
                                   'jalilaperfumes.com',
                                   'bahrain.ounass.com',
                                   'noon.com'],
                    'haircare': ['gcc.luluhypermarket.com',
                                 'bn.boots.com',
                                 'nasserpharmacy.com',
                                 'bahrainpharmacy.com',
                                 'boutiqaat.com'],
                    'makeup': ['gcc.luluhypermarket.com',
                               'bn.boots.com',
                               'bolo.bh',
                               'nasserpharmacy.com',
                               'bahrainpharmacy.com',
                               'sephora.me',
                               'boutiqaat.com',
                               'bahrain.ounass.com'],
                    'skincare': ['gcc.luluhypermarket.com',
                                 'bn.boots.com',
                                 'bolo.bh',
                                 'nasserpharmacy.com',
                                 'bahrainpharmacy.com',
                                 'sephora.me',
                                 'boutiqaat.com']}}


@pytest.mark.parametrize("legacy,super_on", P1_CASES, ids=[_vid(c[0]) for c in P1_CASES])
def test_s23_p2_unset_matches_base_routing(legacy, super_on, monkeypatch):
    """P2 (2.3): new name unset -> the bahrain-tier routed domains for the four
    beauty categories equal the base literal lists (sephora.me only when the
    legacy flag is exactly true after lower)."""
    _set(monkeypatch, LEGACY, legacy)
    monkeypatch.setenv(GEO, "ae")
    for cat in CATEGORIES:
        assert _routed_bahrain(cat) == P2_ROUTED["on" if super_on else "off"][cat], cat


def test_s23_p3_reset_hook_callable(monkeypatch):
    """P3 (2.1): reset_super_flags_cache() stays callable, returns None and
    changes no outcome."""
    sd = _sd()
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.setenv(GEO, "ae")
    before = sd._super_params()
    assert sd.reset_super_flags_cache() is None
    assert sd._super_params() == before == {"super": "true", "geoCode": "ae"}
    assert sd._super_enabled() is True


def test_s23_p4_geocode_default(monkeypatch):
    """P4 (2.1): legacy true with SCRAPEDO_GEOCODE unset -> geoCode "bh"."""
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.delenv(GEO, raising=False)
    assert _render_params(monkeypatch) == [_base_params(True, "bh"), _base_params(True, "bh")]
