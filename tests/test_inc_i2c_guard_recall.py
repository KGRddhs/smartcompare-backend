"""INC-I2c GUARD-RECALL RED rows (ENABLE_IMAGE_GUARD_RECALL, default OFF).

Spec: INC_I2C_UNIT_SPEC_V2.md (S98 main lane, 2026-11-21) section 5, as ruled by
RULINGS_INC_I2C.md (R-0..R-16). Under the relevance guard with the short-line flag ON,
an empty-brand (typed-pair) candidate refused with ``fragrance_word`` gets a second look
in the recall subclass ``image_relevance._RecallCall`` (built by
``RelevanceCall.__new__``): R1 rescues it on edc or an Arabic spelling of perfume,
parfum, toilette or cologne in its text or knowledge-graph type; R3 rescues it when the
typed text has two significant words or more and a candidate host is a perfume shop of
the code registry (``source_router.SOURCE_REGISTRY`` rows whose categories are exactly
fragrances). A rescued candidate is refused ``form`` when its title names a home-scent
good (R-4), then takes the words test whatever ENABLE_IMAGE_GUARD_WORDS reads (R-1).
Every other reason stands. ON, the pick-cache axis gains ``r`` + PICK_RECALL_RULES.

RED rows (test_e*) fail at base on an AssertionError only: every new symbol is read
with getattr and a default and asserted present before use. PIN rows (test_p*) are
green at base; P1 also compares the OFF state with BASE reasons recorded as literals
(measured at aa35e959).

Hermetic: the registry is a patched SOURCE_REGISTRY of SimpleNamespace rows on neutral
.test hosts built by concatenation; the Serper / credit / LLM leaves and the image
cache of image_service are faked; no network, no Redis, no LLM, no sleep. Arabic is
built with chr(). Pure ASCII, LF.
"""

from __future__ import annotations

import ast
import asyncio
import copy
import hashlib
import inspect
import logging
import os
import re
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

LOGGER = "app.services.image_service"
G_FLAG = "ENABLE_IMAGE_RELEVANCE_GUARD"
S_FLAG = "ENABLE_IMAGE_GUARD_SHORT_LINE"
W_FLAG = "ENABLE_IMAGE_GUARD_WORDS"
RC_FLAG = "ENABLE_IMAGE_GUARD_RECALL"
DB_FLAG = "ENABLE_MERCHANT_REGISTRY_DB"
KNOBS = (
    "IMAGE_RELEVANCE_CANDIDATES",
    "IMAGE_LATE_BIND_MAX_WAIT_SECONDS",
    "IMAGE_LATE_BIND_RESERVE_SECONDS",
    "IMAGE_LATE_MAX_SECONDS",
    "IMAGE_PICK_CACHE_TTL_SECONDS",
)
FW = "fragrance_word"

# Neutral hosts (no real shop), built by concatenation.
SHOP = "shop." + "nimbus" + ".test"
SUBROW = "bh." + "cedar" + ".test"
PARENT = "cedar" + ".test"
MULTI = "multi" + "store" + ".test"
VAN = "vanilla" + ".test"
BLOG = "blog" + ".test"
# A banned site name (the pattern of tests/test_inc_i1_picture_must_match.py:90).
BAN = "Fragr" + "antica"
IMG_URL = "https://cdn." + "example" + ".test/a.jpg"
FRAG = ("fragrances",)
#: The synthetic code registry: three fragrance-only rows and one multi-category row.
ROWS = (
    SimpleNamespace(domain=SHOP, categories=FRAG),
    SimpleNamespace(domain=SUBROW, categories=FRAG),
    SimpleNamespace(domain=VAN, categories=FRAG),
    SimpleNamespace(domain=MULTI, categories=("fragrances", "makeup")),
)
EDC_TITLE = "Nimbus Velvet for Women, edC 100ml"


def _cps(*code_points):
    return "".join(chr(cp) for cp in code_points)


def _u(path):
    return "https://" + SHOP + path


#: R1: the eight Arabic spellings (parfum, toilette, perfume x4, cologne x2).
AR_R1 = (
    _cps(0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646),
    _cps(0x062A, 0x0648, 0x0627, 0x0644, 0x064A, 0x062A),
    _cps(0x0628, 0x064A, 0x0631, 0x0641, 0x064A, 0x0648, 0x0645),
    _cps(0x0628, 0x0631, 0x0641, 0x064A, 0x0648, 0x0645),
    _cps(0x0628, 0x0627, 0x0631, 0x0641, 0x064A, 0x0648, 0x0645),
    _cps(0x0628, 0x0627, 0x0631, 0x0641, 0x0648, 0x0645),
    _cps(0x0643, 0x0648, 0x0644, 0x0648, 0x0646),
    _cps(0x0643, 0x0648, 0x0644, 0x0648, 0x0646, 0x064A, 0x0627),
)
#: R-4: the 17 kept single home-scent words (spec V2 section 2.4).
HOME_LATIN = (
    "bakhoor",
    "bakhour",
    "bukhoor",
    "bukhour",
    "bakhur",
    "bukhur",
    "incense",
    "burner",
    "burners",
    "charcoal",
    "chips",
)
HOME_ARABIC = (
    _cps(0x0628, 0x062E, 0x0648, 0x0631),
    _cps(0x0645, 0x0628, 0x062E, 0x0631),
    _cps(0x0645, 0x0628, 0x062E, 0x0631, 0x0629),
    _cps(0x0641, 0x062D, 0x0645),
    _cps(0x062F, 0x062E, 0x0648, 0x0646),
    _cps(0x0645, 0x0639, 0x0645, 0x0648, 0x0644),
)
HOME_WORDS = HOME_LATIN + HOME_ARABIC
HOME_IDS = HOME_LATIN + tuple("ar%d" % i for i in range(len(HOME_ARABIC)))
#: R-4: the Arabic air freshener pair.
AR_AIR = _cps(0x0645, 0x0639, 0x0637, 0x0631) + " " + _cps(0x062C, 0x0648)
HOME_JOINS = ("ROOM SPRAY", "LINEN SPRAY", "AIR FRESHENER", AR_AIR)
HOME_WEIGHTS = ("(36g)", "12 GRAMS", "500GR", "20 gm", "3 g", "100 Gram", "40gms")

SERPER_ITEM = {
    "imageUrl": _u("/a.jpg"),
    "title": "VELVET RAIN",
    "source": "Nimbus Shop",
    "link": _u("/p/1"),
    "domain": SHOP,
}
PAYLOAD_ORGANIC = {
    "organic": [{"title": "VELVET RAIN", "link": _u("/p/1"), "imageUrl": _u("/o.jpg")}]
}
PAYLOAD_KG_EDC = {
    "knowledgeGraph": {"title": "Velvet Rain", "type": "EDC", "imageUrl": _u("/k.jpg")}
}
PAYLOAD_KG_BARE = {"knowledgeGraph": {"title": "Velvet Rain", "imageUrl": _u("/k.jpg")}}
ORGANIC = [{"title": "VELVET RAIN", "link": _u("/p/1")}]

#: E12 / P1 / P3: (row, product, texts, host, RC ON reason, BASE reason). The RC ON
#: column is the second look (spec V2 sections 2.2-2.4; rows of E1-E4, E10, E11 and a
#: brand-known control); the BASE column was recorded at aa35e959 (no second look).
E12_ROWS = (
    ("E1a", "Nimbus Velvet", (EDC_TITLE,), BLOG, None, FW),
    ("E1b", "Nimbus Velvet", ("NIMBUS VELVET " + AR_R1[2],), BLOG, None, FW),
    ("E1c", "Nimbus Velvet", ("NIMBUS VELVET",), BLOG, FW, FW),
    ("E2a", "Velvet Rain", ("VELVET RAIN",), SHOP, None, FW),
    ("E2b", "Velvet Rain", ("VELVET RAIN",), "bh." + SHOP, None, FW),
    ("E2c", "Velvet Rain", ("VELVET RAIN",), MULTI, FW, FW),
    ("E2d", "Velvet Rain", ("VELVET RAIN",), BLOG, FW, FW),
    ("E2e", "Velvet Rain", ("VELVET RAIN",), PARENT, FW, FW),
    ("E2f", "Velvet", ("VELVET",), SHOP, FW, FW),
    ("E3a", "Vanilla Musk", ("WHITE MUSK",), VAN, "name", "name"),
    ("E3b", "Nimbus Velvet Rain", ("VELVET RAIN",), SHOP, "name", "name"),
    ("E4a", "Velvet Rain", ("VELVET RAIN BODY MIST",), SHOP, "form", FW),
    ("E4b", "Velvet Rain Body Mist", ("VELVET RAIN BODY MIST",), SHOP, None, FW),
    ("E4c", "Velvet Rain", ("VELVET RAIN INTENSE",), SHOP, "concentration", FW),
    ("E10a", "Nimbus Velvet", (EDC_TITLE,), BLOG, None, FW),
    ("E10b", "Velvet Rain", ("VELVET RAIN",), SHOP, FW, FW),
    ("E10c", "Velvet Rain", ("VELVET RAIN",), SHOP, None, FW),
    ("E11a", "Velvet Rain", ("VELVET RAIN INCENSE",), SHOP, "form", FW),
    ("E11b", "Velvet Rain", ("VELVET RAIN ROOM SPRAY",), SHOP, "form", FW),
    ("E11c", "Velvet Rain", ("VELVET RAIN (36g)",), SHOP, "form", FW),
    ("E11d", "Velvet Rain Incense", ("VELVET RAIN INCENSE",), SHOP, None, FW),
    ("E11e", "Velvet Rain", ("VELVET RAIN (1 TOLA)",), SHOP, None, FW),
    ("E11f", "Velvet Rain", ("VELVET RAIN", "Incense House"), SHOP, None, FW),
    ("KB", "Nimbus Eau de Parfum", ("NIMBUS EDC",), BLOG, FW, FW),
)
#: The rows read with another registry (E10) and the brand-known control.
E12_REGISTRY = {"E10a": "raising", "E10b": "raising", "E10c": "odd"}
E12_BRAND = {"KB": "Nimbus"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _ir():
    from app.services import image_relevance

    return image_relevance


def _img():
    from app.services import image_service

    return image_service


def _sr():
    from app.services import source_router

    return source_router


def _scs():
    import app.services.structured_comparison_service as scs

    return scs


def _sym(obj, name):
    value = getattr(obj, name, None)
    assert value is not None, "INC-I2c not built: %s.%s is missing" % (
        getattr(obj, "__name__", type(obj).__name__),
        name,
    )
    return value


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """conftest loads the developer .env with override: every ENABLE_* flag and the
    image knobs are deleted here and each row sets its own; the code registry is the
    synthetic ROWS."""
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in list(os.environ):
        if name.startswith("ENABLE_") or name in KNOBS:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(_sr(), "SOURCE_REGISTRY", list(ROWS))
    yield


def _set(mp, name, value):
    if value is None or value is False:
        mp.delenv(name, raising=False)
    elif value is True:
        mp.setenv(name, "true")
    else:
        mp.setenv(name, value)


def _flags(mp, *, g=True, s=True, rc=True, w=None):
    """G and S ON, the switch ON, W unset unless stated (None / False = unset)."""
    for name, value in ((G_FLAG, g), (S_FLAG, s), (RC_FLAG, rc), (W_FLAG, w)):
        _set(mp, name, value)


def _rel(line, typed=None, brand=""):
    rel = {"brand": brand, "line": line, "category": "fragrances", "slot": 0}
    if typed is not None:
        rel["typed"] = typed
    return rel


def _hosts(host):
    return ("https://" + host + "/p/1",) if host else ()


def _accept(q, title, host=None, *, texts=None, brand="", typed=None):
    """One Serper Images candidate through RelevanceCall.accept: (accepted, call)."""
    call = _ir().RelevanceCall(q, _rel(q, typed, brand))
    ok = call.accept(
        "serper_images",
        IMG_URL,
        texts=(title,) if texts is None else tuple(texts),
        hosts=_hosts(host),
    )
    return ok, call


def _v(q, title, host=None, **kw):
    """None when the candidate is accepted, else the call's reason."""
    ok, call = _accept(q, title, host, **kw)
    return None if ok else call.last_reason


def _vw(mp, w, q, title, host=None, **kw):
    """_v with the words flag set to ``w`` (None = unset); with W ON the typed text is
    the product name (relevance_kwargs adds it only with W ON, IR:886-888)."""
    _set(mp, W_FLAG, w)
    return _v(q, title, host, typed=q if w else None, **kw)


class _RaisingRows(list):
    """A registry whose iteration raises (E10)."""

    def __iter__(self):
        raise RuntimeError("registry iteration failed")


def _registry(kind):
    if kind == "rows":
        return list(ROWS)
    if kind == "raising":
        return _RaisingRows(ROWS)
    if kind == "none":
        return None
    assert kind == "odd", kind
    return [
        SimpleNamespace(domain=None, categories=None),
        SimpleNamespace(domain=SHOP, categories=None),
        SimpleNamespace(categories=FRAG),
        SimpleNamespace(domain=SHOP, categories=FRAG),
    ]


def _e12_run(mp, w):
    """(reason, summary) of every E12 row with the words flag set to ``w``."""
    sr = _sr()
    out = []
    for rid, q, texts, host, _on, _base in E12_ROWS:
        mp.setattr(sr, "SOURCE_REGISTRY", _registry(E12_REGISTRY.get(rid, "rows")))
        _set(mp, W_FLAG, w)
        ok, call = _accept(
            q,
            None,
            host,
            texts=texts,
            brand=E12_BRAND.get(rid, ""),
            typed=q if w else None,
        )
        out.append((None if ok else call.last_reason, list(call.summary())))
    mp.setattr(sr, "SOURCE_REGISTRY", list(ROWS))
    return out


def _summary_of(reason):
    """The summary of ONE serper_images candidate with this verdict (n == 1)."""
    if reason is None:
        return ["0", "serper_images", "accepted", 1, "none"]
    return ["0", "serper_images", "rejected", 1, reason]


def _getenv_recorder(mp):
    real = os.getenv
    seen = []

    def _rec(key, default=None):
        seen.append(key)
        return real(key, default)

    mp.setattr(os, "getenv", _rec)
    return seen


def _msgs(caplog, prefix):
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == LOGGER and r.getMessage().startswith(prefix)
    ]


def _line(tier, outcome, n, reason):
    return "[IMG_RELEVANCE] product=0 tier=%s outcome=%s candidates=%d reason=%s" % (
        tier,
        outcome,
        n,
        reason,
    )


NONE_LINE = "[IMG_RELEVANCE] product=0 tier=none outcome=none candidates=0 reason=none"
THUMB_LINE = "IMG_SHOP thumb product=0 outcome=%s candidates=1 reason=%s"
_MS = re.compile(r"(ms|wait_ms|tier_ms|total_ms)=\d+")


def _image_lines(caplog):
    """Every [IMG_* / IMG_* line of image_service, the timings stripped."""
    return [
        _MS.sub(lambda m: m.group(1) + "=N", msg)
        for msg in _msgs(caplog, "")
        if msg.startswith(("[IMG_", "IMG_"))
    ]


class _T:
    """Recorders of the image leaves and the image cache."""

    def __init__(self):
        self.credit = []
        self.search = []
        self.gpt = []
        self.get = []
        self.set = []
        self.store = {}


def _install_tiers(mp, t, *, images=(), gpt_url=None, granted=True):
    img = _img()

    def _credit(n):
        t.credit.append(n)
        return granted

    async def _search(name, **kwargs):
        t.search.append({"q": name, "kw": dict(kwargs)})
        return {"images": [dict(item) for item in images]}

    async def _gpt(name, organic):
        t.gpt.append(name)
        return gpt_url

    def _get(key):
        t.get.append(key)
        return copy.deepcopy(t.store.get(key))

    def _set_cached(key, value, ttl=None, *a, **k):
        t.set.append(key)
        t.store[key] = copy.deepcopy(value)
        return True

    mp.setattr(img, "try_consume_serper_image_credit", _credit)
    mp.setattr(img, "search_images", _search)
    mp.setattr(img, "extract_image_via_gpt", _gpt)
    mp.setattr(img, "get_cached", _get, raising=False)
    mp.setattr(img, "set_cached", _set_cached, raising=False)


def _gpu(mp, caplog, *, images=(), payload=None, organic=None):
    """One guarded get_product_image_url call for the typed pair "Velvet Rain" (brand
    ""): (url, its [IMG_RELEVANCE] lines, the recorders)."""
    t = _T()
    _install_tiers(mp, t, images=images, gpt_url=_u("/pick.jpg"))
    caplog.clear()
    url = _run(
        _img().get_product_image_url(
            "Velvet Rain",
            search_payload=copy.deepcopy(payload),
            organic_results=copy.deepcopy(organic),
            relevance=_rel("Velvet Rain"),
        )
    )
    return url, _msgs(caplog, "[IMG_RELEVANCE]"), t


def _late_run(rel):
    """One get_product_image_url_late call (payload done with None): (url, state)."""

    async def go():
        fut = asyncio.get_running_loop().create_future()
        fut.set_result(None)
        state = {"open": True, "until": None, "cached": False, "stored": False}
        url = await _img().get_product_image_url_late(
            "Velvet Rain", payload=fut, variant=None, state=state, relevance=rel
        )
        return url, state

    return _run(go())


def _thumb(title):
    return [
        {
            "thumbnail": _u("/t.jpg"),
            "title": title,
            "source": "Nimbus Shop",
            "link": _u("/p/1"),
        }
    ]


def _expected_name(rel, variant, axis):
    """The pick-cache name for ``axis`` (tests/test_inc_i2b_guard_words_shop_image.py
    :921-933)."""
    img = _img()
    parts = [
        img._name_part(rel.get("category")),
        img._name_part(rel.get("brand")),
        img._name_part(rel.get("line")),
        img._name_part(variant),
        axis,
    ]
    return (
        img.PICK_CACHE_PREFIX
        + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]
    )


# ---------------------------------------------------------------------------
# E1-E5: the rules and the switch
# ---------------------------------------------------------------------------


def test_e01_r1_vocabulary_rescues_on_any_host(monkeypatch):
    """E1 (R-3): edc and the eight Arabic words rescue a typed pair on a host outside
    the registry (BLOG), in the title or a knowledge-graph type; a bare title stays
    fragrance_word; RC unset: fragrance_word."""
    _flags(monkeypatch)
    assert _v("Nimbus Velvet", EDC_TITLE, BLOG) is None
    for word in ("EDC",) + AR_R1:
        got = _v("Nimbus Velvet", "NIMBUS VELVET " + word, BLOG)
        assert got is None, (ascii(word), got)
    assert _v("Nimbus Velvet", "NIMBUS VELVET", BLOG) == FW
    call = _ir().RelevanceCall("Nimbus Velvet", _rel("Nimbus Velvet"))
    assert call.accept(
        "search_payload",
        IMG_URL,
        texts=("Nimbus Velvet",),
        fragrance_texts=("EDC",),
    )
    _flags(monkeypatch, rc=None)
    assert _v("Nimbus Velvet", EDC_TITLE, BLOG) == FW


def test_e02_r3_perfume_shop_and_the_floor(monkeypatch):
    """E2 (R-3, R-9): a fragrance-only registry host or its subdomain rescues a
    two-word typed pair; a multi-category row, a host outside the registry and the
    parent of a row do not; a one-word line stays fragrance_word (the floor)."""
    _flags(monkeypatch)
    assert _v("Velvet Rain", "VELVET RAIN", SHOP) is None
    assert _v("Velvet Rain", "VELVET RAIN", "bh." + SHOP) is None
    assert _v("Velvet Rain", "VELVET RAIN", SUBROW) is None
    for host in (MULTI, BLOG, PARENT):
        assert _v("Velvet Rain", "VELVET RAIN", host) == FW, host
    assert _v("Velvet", "VELVET", SHOP) == FW
    _flags(monkeypatch, rc=None)
    assert _v("Velvet Rain", "VELVET RAIN", SHOP) == FW


def test_e03_a_name_refusal_stands(monkeypatch):
    """E3 (R-2): the recall class is built, and a typed word the title lacks stays
    name, even on a fragrance-only host whose label is a typed word; W unset and ON."""
    _flags(monkeypatch)
    call = _ir().RelevanceCall("Vanilla Musk", _rel("Vanilla Musk"))
    assert type(call).__name__ == "_RecallCall", type(call).__name__
    for w in (None, "true"):
        assert _vw(monkeypatch, w, "Vanilla Musk", "WHITE MUSK", VAN) == "name", w
        got = _vw(monkeypatch, w, "Nimbus Velvet Rain", "VELVET RAIN", SHOP)
        assert got == "name", (w, got)


def test_e04_a_rescue_takes_the_words_test(monkeypatch):
    """E4 (R-1): a rescued BODY MIST is refused form and a rescued free intense
    concentration, W unset and ON; the typed form words are exempt."""
    _flags(monkeypatch)
    for w in (None, "true"):
        got = _vw(monkeypatch, w, "Velvet Rain", "VELVET RAIN BODY MIST", SHOP)
        assert got == "form", (w, got)
        got = _vw(
            monkeypatch, w, "Velvet Rain Body Mist", "VELVET RAIN BODY MIST", SHOP
        )
        assert got is None, (w, got)
        got = _vw(monkeypatch, w, "Velvet Rain", "VELVET RAIN INTENSE", SHOP)
        assert got == "concentration", (w, got)


def test_e05_the_switch_spellings_and_reads(monkeypatch):
    """E5 (R-6): under G a truthy switch builds _RecallCall, any other value (unset,
    false, 0, garbage, "") the base class, and G unset never; the reader is the house
    idiom; one read per construction and one per pick_cache_name."""
    ir = _ir()

    def built(rc, g=True):
        _flags(monkeypatch, g=g, rc=rc)
        return type(ir.RelevanceCall("Velvet Rain", _rel("Velvet Rain"))).__name__

    for raw in ("true", "1", "yes", "on", " TRUE "):
        assert built(raw) == "_RecallCall", raw
    for raw in (None, "false", "0", "garbage", ""):
        assert built(raw) == "RelevanceCall", raw
    assert built("true", g=None) == "RelevanceCall"
    assert _sym(ir, "RECALL_FLAG_ENV") == RC_FLAG
    reader = _sym(ir, "recall_enabled")
    for raw in ("true", " TRUE ", "1", "yes", "On"):
        monkeypatch.setenv(RC_FLAG, raw)
        assert reader() is True, raw
    monkeypatch.delenv(RC_FLAG, raising=False)
    assert reader() is False
    for raw in ("", "false", "0", "no", "off", "garbage", "tru e"):
        monkeypatch.setenv(RC_FLAG, raw)
        assert reader() is False, raw
    _flags(monkeypatch)
    seen = _getenv_recorder(monkeypatch)
    ir.RelevanceCall("Velvet Rain", _rel("Velvet Rain"))
    assert seen.count(RC_FLAG) == 1, seen
    del seen[:]
    _img().pick_cache_name(_rel("Velvet Rain"), None)
    assert seen.count(RC_FLAG) == 1, seen


# ---------------------------------------------------------------------------
# E6-E9: the cascade, the thumbnail, the cache axis, the version
# ---------------------------------------------------------------------------


def test_e06_the_cascade_tiers(monkeypatch, caplog):
    """E6 (R-13): RC ON, the typed pair "Velvet Rain" on SHOP: (a) Serper Images, (b)
    the payload organic item, (d) a knowledge graph whose type is EDC (no host: R1 by
    the type), (e) the llm_pick precondition and pick (one GPT call); RC unset: the
    base refusals and no GPT call."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    got = {}
    for rc in (True, None):
        _flags(monkeypatch, rc=rc)
        got[rc] = {
            "a": _gpu(monkeypatch, caplog, images=[SERPER_ITEM]),
            "b": _gpu(monkeypatch, caplog, payload=PAYLOAD_ORGANIC),
            "d": _gpu(monkeypatch, caplog, payload=PAYLOAD_KG_EDC),
            "e": _gpu(monkeypatch, caplog, organic=ORGANIC),
        }
    on, off = got[True], got[None]
    url, lines, _t = on["a"]
    assert url == _u("/a.jpg"), url
    assert lines == [_line("serper_images", "accepted", 1, "none")], lines
    for key, image in (("b", "/o.jpg"), ("d", "/k.jpg")):
        url, lines, _t = on[key]
        assert url == _u(image), (key, url)
        assert lines == [_line("search_payload", "accepted", 1, "none")], (key, lines)
    url, lines, t = on["e"]
    assert url == _u("/pick.jpg") and len(t.gpt) == 1, (url, t.gpt)
    assert lines == [_line("llm_pick", "accepted", 1, "none")], lines
    url, lines, _t = off["a"]
    assert url is None and lines == [_line("serper_images", "rejected", 1, FW)]
    for key in ("b", "d"):
        url, lines, _t = off[key]
        assert url is None, (key, url)
        assert lines == [_line("search_payload", "rejected", 1, FW)], (key, lines)
    url, lines, t = off["e"]
    assert url is None and t.gpt == [] and lines == [NONE_LINE], (url, t.gpt, lines)


def test_e07_the_shopping_thumbnail(monkeypatch, caplog):
    """E7 (walk 8): B's thumbnail, W unset: a rescued bare title is accepted; a
    rescued GIFT SET is refused form by the words test; RC unset: fragrance_word."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    img = _img()
    got = {}
    for rc in (True, None):
        _flags(monkeypatch, rc=rc)
        caplog.clear()
        urls = [
            img.shopping_thumbnail(_thumb(title), "Velvet Rain", 0, _rel("Velvet Rain"))
            for title in ("VELVET RAIN", "VELVET RAIN GIFT SET")
        ]
        got[rc] = (urls, _msgs(caplog, "IMG_SHOP thumb"))
    assert got[True] == (
        [_u("/t.jpg"), None],
        [THUMB_LINE % ("accepted", "none"), THUMB_LINE % ("rejected", "form")],
    ), got[True]
    assert got[None] == ([None, None], [THUMB_LINE % ("rejected", FW)] * 2), got[None]


def test_e08_the_pick_cache_axis(monkeypatch):
    """E8 (design B): PICK_RECALL_RULES first; the axis gains r + it only with RC and
    S ON (W both); every OFF name is the base name; the late call reads and stores
    exactly the ON name and reads the switch twice (name + construction)."""
    img = _img()
    rules = getattr(img, "PICK_RECALL_RULES", None)
    assert isinstance(rules, str) and re.fullmatch(r"[0-9a-f]{8}", rules), rules
    rel = _rel("Velvet Rain")
    typed = _rel("Velvet Rain", "Velvet Rain EDP")
    _flags(monkeypatch)
    on = img.pick_cache_name(rel, None)
    assert on == _expected_name(rel, None, "s1w0r" + rules)
    _flags(monkeypatch, rc=None)
    off = img.pick_cache_name(rel, None)
    assert off == _expected_name(rel, None, "s1w0")
    _flags(monkeypatch, s=None)
    assert img.pick_cache_name(rel, None) == _expected_name(rel, None, "s0w0")
    _flags(monkeypatch, w=True)
    got = img.pick_cache_name(typed, None)
    assert got == _expected_name(typed, None, "s1w1:EDPr" + rules)
    assert on != off
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t, images=[SERPER_ITEM], gpt_url=_u("/pick.jpg"))
    seen = _getenv_recorder(monkeypatch)
    url, state = _late_run(rel)
    assert url == _u("/a.jpg"), url
    assert t.get == [on] and t.set == [on], (t.get, t.set)
    assert state["stored"] is True
    assert seen.count(RC_FLAG) == 2, seen.count(RC_FLAG)


RECALL_SET = (
    "recall_enabled",
    "RelevanceCall.__new__",
    "_host",
    "_perfume_domains",
    "_perfume_shop",
    "_recall_reason",
    "_home_reason",
    "_RecallCall",
)
RECALL_SORTED_TABLES = (
    "RECALL_FRAGRANCE_WORDS",
    "RECALL_HOME_WORDS",
    "RECALL_HOME_JOINS",
    "RECALL_GRAM_UNITS",
)
RECALL_PATTERNS = ("RECALL_WEIGHT",)
RECALL_REPR = (
    "RECALL_SHOP_CATEGORIES",
    "RECALL_SHOP_MIN_WORDS",
    "RECALL_REASONS",
    "RECALL_FLAG_ENV",
)


def _recall_text():
    """The RECALL_SET text of spec V2 section 2.6 (presence asserted first)."""
    ir = _ir()
    missing = [
        name
        for name in RECALL_SET + RECALL_SORTED_TABLES + RECALL_PATTERNS + RECALL_REPR
        if "." not in name and not hasattr(ir, name)
    ]
    if "__new__" not in vars(ir.RelevanceCall):
        missing.append("RelevanceCall.__new__")
    assert not missing, "INC-I2c not built: image_relevance lacks %s" % missing
    parts = []
    for dotted in RECALL_SET:
        obj = ir
        for part in dotted.split("."):
            obj = getattr(obj, part)
        parts.append(inspect.getsource(obj))
    for name in RECALL_SORTED_TABLES:
        parts.append(name + "=" + repr(sorted(getattr(ir, name))))
    for name in RECALL_PATTERNS:
        parts.append(name + "=" + getattr(ir, name).pattern)
    for name in RECALL_REPR:
        parts.append(name + "=" + repr(getattr(ir, name)))
    return "\n".join(parts)


def test_e09_the_recall_version_is_pinned():
    """E9 (R-7): every RECALL_SET member and table present; the digest of the RECALL_SET
    text == PICK_RECALL_RULES != 00000000 (a unit that edits the recall code or tables
    bumps it)."""
    text = _recall_text()
    rules = getattr(_img(), "PICK_RECALL_RULES", None)
    assert isinstance(rules, str) and re.fullmatch(r"[0-9a-f]{8}", rules), rules
    assert rules != "00000000"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    assert digest == rules, "the recall code or tables changed: bump PICK_RECALL_RULES"


# ---------------------------------------------------------------------------
# E10-E13: the registry faults, home scent, the words flag, the pre-split shape
# ---------------------------------------------------------------------------


def test_e10_the_registry_read_is_total(monkeypatch):
    """E10 (R-5): a registry whose iteration raises, None, and rows with a missing or
    odd domain / categories: R1 still rescues, R3 sees no shop, nothing raises; a
    well-formed row among odd ones still counts."""
    _flags(monkeypatch)
    sr = _sr()
    assert _v("Nimbus Velvet", EDC_TITLE, BLOG) is None
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", _registry("raising"))
    assert _v("Nimbus Velvet", EDC_TITLE, BLOG) is None
    assert _v("Velvet Rain", "VELVET RAIN", SHOP) == FW
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", _registry("none"))
    assert _v("Velvet Rain", "VELVET RAIN", SHOP) == FW
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", _registry("odd"))
    assert _v("Velvet Rain", "VELVET RAIN", SHOP) is None


@pytest.mark.parametrize("word", HOME_WORDS, ids=HOME_IDS)
def test_e11_a_home_scent_word_refuses_a_rescue(monkeypatch, word):
    """E11 (R-4): each of the 17 kept single words refuses a rescued title form, W
    unset and ON; RC unset: fragrance_word."""
    _flags(monkeypatch)
    title = "VELVET RAIN " + word.upper()
    for w in (None, "true"):
        got = _vw(monkeypatch, w, "Velvet Rain", title, SHOP)
        assert got == "form", (ascii(word), w, got)
    _flags(monkeypatch, rc=None)
    assert _v("Velvet Rain", title, SHOP) == FW, ascii(word)


def test_e11b_home_joins_weights_typed_words_and_limits(monkeypatch):
    """E11 (R-4): the pairs and the weights refuse form; a typed word never counts (a
    pair only when both are typed); tola, a bare room / linen / wood, a ml size and a
    second text never refuse; W unset and ON; RC unset: fragrance_word."""
    _flags(monkeypatch)
    for w in (None, "true"):
        for tail in HOME_JOINS + HOME_WEIGHTS:
            got = _vw(monkeypatch, w, "Velvet Rain", "VELVET RAIN " + tail, SHOP)
            assert got == "form", (ascii(tail), w, got)
        typed = (
            ("Velvet Rain Incense", "VELVET RAIN INCENSE", None),
            ("Velvet Rain Room Spray", "VELVET RAIN ROOM SPRAY", None),
            ("Velvet Rain Room", "VELVET RAIN ROOM SPRAY", "form"),
            ("Velvet Rain 36g", "VELVET RAIN (36g)", None),
            ("Velvet Rain 12", "VELVET RAIN 12 GRAMS", "form"),
        )
        for q, title, want in typed:
            got = _vw(monkeypatch, w, q, title, SHOP)
            assert got == want, (q, title, w, got)
        for tail in ("(1 TOLA)", "ROOM", "LINEN", "WOOD", "100ML"):
            got = _vw(monkeypatch, w, "Velvet Rain", "VELVET RAIN " + tail, SHOP)
            assert got is None, (tail, w, got)
        texts = ("VELVET RAIN", "Incense House")
        got = _vw(monkeypatch, w, "Velvet Rain", None, SHOP, texts=texts)
        assert got is None, (w, got)
    _flags(monkeypatch, rc=None)
    for tail in HOME_JOINS + HOME_WEIGHTS:
        assert _v("Velvet Rain", "VELVET RAIN " + tail, SHOP) == FW, ascii(tail)


def test_e12_rc_on_reasons_are_one_table_for_both_words_states(monkeypatch):
    """E12 (R-1, walk 5): 24 synthetic rows (the classes of E1-E4, E10, E11 and a
    brand-known control): with RC ON the reasons are the second-look column and each
    summary counts the candidate once, W unset and W ON alike."""
    _flags(monkeypatch)
    want = [(row[4], _summary_of(row[4])) for row in E12_ROWS]
    for w in (None, "true"):
        got = _e12_run(monkeypatch, w)
        bad = [
            (row[0], g, x)
            for row, g, x in zip(E12_ROWS, got, want, strict=True)
            if g != x
        ]
        assert not bad, (w, bad)


def test_e13_a_presplit_typed_pair_gets_the_second_look(monkeypatch):
    """E13 (RC-3, walk 14): the q= " vs " pre-split / parse-fallback product shape has
    brand "" and its relevance identity is rescued on a registry perfume shop."""
    _flags(monkeypatch)
    scs, ir = _scs(), _ir()
    halves = scs._split_on_vs("Velvet Rain vs Cedar Moss")
    assert tuple(halves) == ("Velvet Rain", "Cedar Moss"), halves
    p = scs._explicit_pair_products(halves)[0]
    assert p["brand"] == "" and p["name"] == "Velvet Rain", p
    kw = ir.relevance_kwargs(p["brand"], p["name"], "fragrances", 0, False)
    call = ir.RelevanceCall(p["name"], kw["relevance"])
    ok = call.accept(
        "serper_images", IMG_URL, texts=("VELVET RAIN",), hosts=(_u("/p/1"),)
    )
    assert ok is True, call.last_reason


# ---------------------------------------------------------------------------
# P rows (green at base)
# ---------------------------------------------------------------------------


def _p1_observe(mp, caplog, rc):
    """The E12 reasons, the E6 / E7 / E8 URLs and lines and the pick-cache names with
    the switch set to ``rc``."""
    _flags(mp, rc=rc)
    img = _img()
    obs = {"e12": [_e12_run(mp, w) for w in (None, "true")]}
    _set(mp, W_FLAG, None)
    for key, kw in (
        ("a", {"images": [SERPER_ITEM]}),
        ("b", {"payload": PAYLOAD_ORGANIC}),
        ("d", {"payload": PAYLOAD_KG_EDC}),
        ("e", {"organic": ORGANIC}),
    ):
        url, _lines, t = _gpu(mp, caplog, **kw)
        obs["e6" + key] = [url, len(t.gpt), _image_lines(caplog)]
    caplog.clear()
    thumbs = [
        img.shopping_thumbnail(_thumb(title), "Velvet Rain", 0, _rel("Velvet Rain"))
        for title in ("VELVET RAIN", "VELVET RAIN GIFT SET")
    ]
    obs["e7"] = [thumbs, _image_lines(caplog)]
    rel = _rel("Velvet Rain")
    names = [img.pick_cache_name(rel, None)]
    _set(mp, W_FLAG, True)
    names.append(img.pick_cache_name(_rel("Velvet Rain", "Velvet Rain EDP"), None))
    _set(mp, W_FLAG, None)
    obs["names"] = names
    t = _T()
    _install_tiers(mp, t, images=[SERPER_ITEM], gpt_url=_u("/pick.jpg"))
    caplog.clear()
    url, state = _late_run(rel)
    obs["e8"] = [url, list(t.get), list(t.set), state["stored"], _image_lines(caplog)]
    return obs


@pytest.mark.parametrize(
    "rc", ["false", "0", "garbage", ""], ids=["false", "0", "garbage", "empty"]
)
def test_p01_every_off_spelling_is_the_base(monkeypatch, caplog, rc):
    """P1 (RC-9): RC unset == "false" == "0" == "garbage" == "": the E12 reasons and
    summaries, the E6-E8 URLs and IMG_TIER / IMG_RELEVANCE / IMG_SHOP / IMG_LATE lines
    and the pick-cache names; RC unset gives the BASE reasons, summaries, lines and
    names (recorded at aa35e959)."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    unset = _p1_observe(monkeypatch, caplog, None)
    base = [(row[5], _summary_of(row[5])) for row in E12_ROWS]
    assert unset["e12"] == [base, base], unset["e12"]
    assert unset["e6a"][:2] == [None, 0], unset["e6a"]
    assert _line("serper_images", "rejected", 1, FW) in unset["e6a"][2]
    for key in ("e6b", "e6d"):
        assert unset[key][:2] == [None, 0], (key, unset[key])
        assert _line("search_payload", "rejected", 1, FW) in unset[key][2], key
    assert unset["e6e"][:2] == [None, 0] and NONE_LINE in unset["e6e"][2]
    assert unset["e7"][0] == [None, None], unset["e7"]
    assert [x for x in unset["e7"][1] if x.startswith("IMG_SHOP thumb")] == [
        THUMB_LINE % ("rejected", FW)
    ] * 2
    rel = _rel("Velvet Rain")
    typed = _rel("Velvet Rain", "Velvet Rain EDP")
    assert unset["names"] == [
        _expected_name(rel, None, "s1w0"),
        _expected_name(typed, None, "s1w1:EDP"),
    ]
    assert unset["e8"][:4] == [None, [unset["names"][0]], [], False], unset["e8"]
    assert _p1_observe(monkeypatch, caplog, rc) == unset


GUARD_SET = (
    "check",
    "_check_base",
    "_check_short_line",
    "_words_reason",
    "_conc_scan",
    "_conc_labels",
    "words_reason_for",
    "guard_words_enabled",
    "short_line_enabled",
    "_seq",
    "_text_tokens",
    "_host_tokens",
    "_candidate_keys",
    "fold_numero",
    "identity",
    "RelevanceCall._record",
    "RelevanceCall.accept",
    "RelevanceCall.accept_scheme",
    "RelevanceCall._organic_reason",
    "RelevanceCall.organic_passes",
    "RelevanceCall.accept_pick",
    "RelevanceCall.accept_thumb",
)
GUARD_SORTED_TABLES = (
    "NAME_EXCLUDE",
    "CONCENTRATION_WORDS",
    "STOP_WORDS",
    "FRAGRANCE_WORDS",
    "BRAND_NOISE",
    "PLACEHOLDER_BRANDS",
    "UNIT_WORDS",
    "ELISION",
    "BRAND_EXCLUDE",
    "_NUMERO_PREFIX",
    "_WHOLE_LINE_DROP",
    "FORM_WORDS",
    "FORM_JOINS",
    "INTENSE_WORDS",
    "INTENSE_GENERIC_NEXT",
)
GUARD_PATTERNS = ("SIZE_TOKEN", "_NUMBER", "_NUMERO")


def _guard_text():
    """The GUARD_SET text (tests/test_inc_i2a_picture_not_cut.py:1387-1452)."""
    ir = _ir()
    objs = []
    for dotted in GUARD_SET:
        obj = ir
        for part in dotted.split("."):
            obj = getattr(obj, part)
        objs.append(obj)
    parts = [inspect.getsource(o) for o in objs]
    for name in GUARD_SORTED_TABLES:
        parts.append(name + "=" + repr(sorted(getattr(ir, name))))
    for name in GUARD_PATTERNS:
        parts.append(name + "=" + getattr(ir, name).pattern)
    parts.append("CONC_PHRASES=" + repr(ir.CONC_PHRASES))
    parts.append(
        "EXTRA_ALIAS_GROUPS=" + repr(sorted(sorted(g) for g in ir.EXTRA_ALIAS_GROUPS))
    )
    parts.append("CONC_CLASS=" + repr(sorted(ir.CONC_CLASS.items())))
    parts.append("TEXT_MAX_CHARS=" + repr(ir.TEXT_MAX_CHARS))
    return "\n".join(parts)


def test_p02_the_guard_version_does_not_move():
    """P2 (R-6): the GUARD_SET digest == PICK_GUARD_RULES == 7f9e0f4f; the prefix and
    so every OFF name are unchanged."""
    img = _img()
    digest = hashlib.sha256(_guard_text().encode("utf-8")).hexdigest()[:8]
    assert digest == "7f9e0f4f", digest
    assert img.PICK_GUARD_RULES == "7f9e0f4f"
    assert img.PICK_CACHE_PREFIX == "imgpick:v1:7f9e0f4f:"


def test_p03_check_never_reads_the_switch(monkeypatch):
    """P3 (M24): check() over the E12 rows (W unset and ON, RC ON) reads
    ENABLE_IMAGE_GUARD_RECALL 0 times."""
    _flags(monkeypatch)
    ir = _ir()
    cases = []
    for w in (None, "true"):
        for rid, q, texts, host, _on, _base in E12_ROWS:
            rel = _rel(q, q if w else None, E12_BRAND.get(rid, ""))
            cases.append((w, ir.identity(q, rel), texts, _hosts(host)))
    seen = _getenv_recorder(monkeypatch)
    for w, ident, texts, hosts in cases:
        _set(monkeypatch, W_FLAG, w)
        ir.check(ident, texts, hosts)
    assert seen.count(RC_FLAG) == 0, seen.count(RC_FLAG)
    assert S_FLAG in seen


def test_p04_guard_off_never_reads_the_switch(monkeypatch, caplog):
    """P4 (walk 1, M20): G unset, RC and S ON: relevance_kwargs is {}; the cascade, the
    late call and shopping_thumbnail (with and without a relevance) read the switch 0
    times."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    _flags(monkeypatch, g=None)
    ir, img = _ir(), _img()
    assert ir.relevance_kwargs("", "Velvet Rain", "fragrances", 0, False) == {}
    t = _T()
    _install_tiers(monkeypatch, t, images=[SERPER_ITEM], gpt_url=_u("/pick.jpg"))
    seen = _getenv_recorder(monkeypatch)
    rel = _rel("Velvet Rain")
    url = _run(
        img.get_product_image_url(
            "Velvet Rain",
            search_payload=copy.deepcopy(PAYLOAD_ORGANIC),
            organic_results=copy.deepcopy(ORGANIC),
            relevance=rel,
        )
    )
    assert url == _u("/o.jpg"), url
    late_url, _state = _late_run(rel)
    assert late_url == _u("/a.jpg"), late_url
    assert img.shopping_thumbnail(_thumb("VELVET RAIN"), "Velvet Rain", 0) is None
    img.shopping_thumbnail(_thumb("VELVET RAIN"), "Velvet Rain", 0, rel)
    assert seen.count(RC_FLAG) == 0, seen.count(RC_FLAG)
    assert G_FLAG in seen
    assert _msgs(caplog, "[IMG_RELEVANCE]") == []


def _source_router_imports(tree):
    """The enclosing function name (None at module level) of every import that
    names source_router."""
    found = []

    def visit(node, func):
        for child in ast.iter_child_nodes(node):
            inner = func
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inner = child.name
            elif isinstance(child, ast.Import):
                if any(a.name.split(".")[-1] == "source_router" for a in child.names):
                    found.append(func)
            elif isinstance(child, ast.ImportFrom):
                module = (child.module or "").split(".")[-1]
                if module == "source_router" or any(
                    a.name == "source_router" for a in child.names
                ):
                    found.append(func)
            visit(child, inner)

    visit(tree, None)
    return found


def test_p05_the_leaf_reads_the_code_registry_only():
    """P5 (R-5, R-10): source_router is imported only inside _perfume_domains (never at
    module level: the leaf shape); the leaf names no refreshing registry reader."""
    src = inspect.getsource(_ir())
    found = _source_router_imports(ast.parse(src))
    assert all(func == "_perfume_domains" for func in found), found
    for word in ("registry_lookup_rows", "kb_merchants", "robots_registry"):
        assert word not in src, word


def test_p06_registry_db_on_schedules_nothing(monkeypatch):
    """P6 (R-5, walk 11): ENABLE_MERCHANT_REGISTRY_DB ON, an empty memo, a running
    loop: the E2 candidate creates no task, runs no refresh and reads no
    registry_lookup_rows; its verdict is the DB-OFF verdict."""
    from app.services import merchant_registry as mr

    _flags(monkeypatch)
    sr = _sr()
    runs = []
    reads = []

    def _refresh():
        runs.append(1)

        async def _noop():
            return None

        return _noop()

    real_lookup = sr.registry_lookup_rows

    def _lookup():
        reads.append(1)
        return real_lookup()

    monkeypatch.setattr(mr, "refresh_merchant_registry", _refresh)
    monkeypatch.setattr(sr, "registry_lookup_rows", _lookup)

    async def go():
        before = set(asyncio.all_tasks())
        off = _v("Velvet Rain", "VELVET RAIN", SHOP)
        monkeypatch.setenv(DB_FLAG, "true")
        on = _v("Velvet Rain", "VELVET RAIN", SHOP)
        return off, on, set(asyncio.all_tasks()) - before

    mr._reset_for_tests()
    try:
        off, on, new = _run(go())
    finally:
        mr._reset_for_tests()
    assert new == set(), new
    assert runs == [] and reads == [], (runs, reads)
    assert on == off, (on, off)


P7_IDENTITIES = (
    (
        "Nimbus Velvet Rain",
        (
            "NIMBUS VELVET RAIN",
            "VELVET RAIN",
            "ACME VELVET RAIN",
            "NIMBUS CEDAR",
            "VELVET RAIN BODY MIST",
        ),
    ),
    ("Nimbus Eau de Parfum", ("NIMBUS EDC", "NIMBUS " + AR_R1[0], "NIMBUS")),
)


def test_p07_brand_known_identities_are_untouched(monkeypatch):
    """P7 (walk 6 / 13, M1, M30): brand "Nimbus" (the resolved / LLM-parsed shape):
    every title x SHOP, BLOG, W unset and ON: RC ON == RC unset, a brand-known
    fragrance_word refusal (a line of concentration words) included."""
    grid = {}
    for rc in (None, True):
        _flags(monkeypatch, rc=rc)
        grid[rc] = [
            _vw(monkeypatch, w, q, title, host, brand="Nimbus")
            for w in (None, "true")
            for q, titles in P7_IDENTITIES
            for title in titles
            for host in (SHOP, BLOG)
        ]
    assert grid[True] == grid[None], (grid[True], grid[None])
    assert FW in grid[True] and "name" in grid[True], grid[True]


def test_p08_short_line_off_the_switch_is_inert(monkeypatch):
    """P8 (walk 4, M2): S unset: E1, E2 and E4 first and E11 INCENSE are
    fragrance_word with RC ON and RC unset."""
    cases = (
        ("Nimbus Velvet", EDC_TITLE, BLOG),
        ("Velvet Rain", "VELVET RAIN", SHOP),
        ("Velvet Rain", "VELVET RAIN BODY MIST", SHOP),
        ("Velvet Rain", "VELVET RAIN INCENSE", SHOP),
    )
    for rc in (True, None):
        _flags(monkeypatch, s=None, rc=rc)
        for q, title, host in cases:
            assert _v(q, title, host) == FW, (rc, title)


def test_p09_a_denied_candidate_is_never_rescued(monkeypatch, caplog):
    """P9 (walk 12, M16): RC ON on SHOP (a mutant running the second look on a denied
    or scheme refusal would rescue each): a Serper item whose source names a banned
    site -> denied; an http image -> scheme; an organic item whose title names the
    banned site -> denied, no GPT call; a knowledge graph without a host ->
    fragrance_word."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    _flags(monkeypatch)
    url, lines, _t = _gpu(monkeypatch, caplog, images=[dict(SERPER_ITEM, source=BAN)])
    assert url is None and lines == [_line("serper_images", "rejected", 1, "denied")]
    http_item = dict(SERPER_ITEM, imageUrl="http://" + SHOP + "/h.jpg")
    url, lines, _t = _gpu(monkeypatch, caplog, images=[http_item])
    assert url is None and lines == [_line("serper_images", "rejected", 1, "scheme")]
    organic = [{"title": "VELVET RAIN " + BAN, "link": _u("/p/1")}]
    call = _ir().RelevanceCall("Velvet Rain", _rel("Velvet Rain"))
    assert call._organic_reason(organic[0]) == "denied"
    url, lines, t = _gpu(monkeypatch, caplog, organic=organic)
    assert url is None and t.gpt == [] and lines == [NONE_LINE], (url, t.gpt, lines)
    url, lines, _t = _gpu(monkeypatch, caplog, payload=PAYLOAD_KG_BARE)
    assert url is None and lines == [_line("search_payload", "rejected", 1, FW)]


def test_p10_a_base_pass_is_never_re_read(monkeypatch):
    """P10 (R-4 acts on rescues only): a title the base accepts (it carries eau de
    parfum) passes with incense in it, RC unset and ON, W unset and ON."""
    for rc in (None, True):
        _flags(monkeypatch, rc=rc)
        for w in (None, "true"):
            title = "VELVET RAIN INCENSE EAU DE PARFUM"
            assert _vw(monkeypatch, w, "Velvet Rain", title, SHOP) is None, (rc, w)
