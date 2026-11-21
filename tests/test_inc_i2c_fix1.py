"""INC-I2c GUARD-RECALL FIX-1 rows (ENABLE_IMAGE_GUARD_RECALL, default OFF).

The fix round of FIX1_RULINGS_INC_I2C (S98 orchestrator, 2026-11-21; F1-1..F1-10) and
the relay ruling ORCH-I2C-FIX1, on the reports of adversary 1 (recall and precision)
and adversary 2 (production and identity). The RED file
tests/test_inc_i2c_guard_recall.py stays frozen apart from ONE E1 case: the standalone
Arabic toilette word became the eau-de-toilette phrase, and the standalone word is a row
of E03 here that must NOT be rescued. Under the relevance guard, with the short-line
flag and the switch ON, for an empty-brand (typed-pair) identity:

* F1-1: ``_perfume_domains`` tests a row's categories BEFORE ``_host``, so only the
  fragrance-only rows are parsed.
* F1-2: R1 reads the TITLE (the first text) and the knowledge-graph types only, never
  the Serper source text (a site name) or a later text.
* F1-3: the Arabic toilette word counts for R1 only right after U+062F 0648 or U+062F
  064A (the eau-de-toilette phrase); alone it also means toilet.
* F1-4: in the second look the R1 words are not significant line words: with none
  left, the line's one-character tokens must be in the candidate, and they never count
  toward the R3 floor.
* F1-5: no second look when every remaining significant line word is men, women, man,
  woman, unisex, homme, femme, him, her, boys, girls or intense.
* F1-6: home spray, car freshener, fabric spray, wax melt(s) and the two Arabic gram
  units after a number refuse a rescue ``form`` (a typed word never counts; a pair only
  when both of its words are typed).
* F1-7: ``RelevanceCall.__new__(cls, *args, **kwargs)``: every argument goes on to
  ``__init__`` (a subclass may take more).

Rows test_e* fail at 4ab14157 (the unit head before the fix) on an AssertionError only
(the head's TypeError in E08 is caught and asserted) and pass after the fix; X3 (R1
never from the source text) is E07. Rows test_p* are green at both: the gaps X1, X2, X4
and X5 of adversary 1, the RC-unset verdict of every new scenario, and ruling (d): the
image layer (the image_service cascade and the image_relevance verdict path) reads none
of ENABLE_SHOP_PAGE_IMAGE, ENABLE_SHOPPING_THUMB_IMAGE, ENABLE_PRODUCT_RESOLVER and
ENABLE_IMAGE_LATE_BIND (widened by the re-verification finding RV-1).

Hermetic: the registry is a patched SOURCE_REGISTRY of SimpleNamespace rows on neutral
.test hosts built by concatenation (the one listing photo of P05 sits on the reserved
example.com name: the image policy refuses a .test host); the Serper / credit / LLM
leaves and the image cache of image_service are faked; no network, no Redis, no LLM,
no sleep. Arabic is built with chr(). Pure ASCII, LF.
"""

from __future__ import annotations

import ast
import asyncio
import copy
import inspect
import logging
import os
import sys
import textwrap
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

LOGGER = "app.services.image_service"
G_FLAG = "ENABLE_IMAGE_RELEVANCE_GUARD"
S_FLAG = "ENABLE_IMAGE_GUARD_SHORT_LINE"
W_FLAG = "ENABLE_IMAGE_GUARD_WORDS"
RC_FLAG = "ENABLE_IMAGE_GUARD_RECALL"
A_FLAG = "ENABLE_SHOP_PAGE_IMAGE"
B_FLAG = "ENABLE_SHOPPING_THUMB_IMAGE"
R_FLAG = "ENABLE_PRODUCT_RESOLVER"
L_FLAG = "ENABLE_IMAGE_LATE_BIND"
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
MULTI = "multi" + "store" + ".test"
VAN = "vanilla" + ".test"
BLOG = "blog" + ".test"
GEAR = "gear" + "works" + ".test"
#: X1: a look-alike host that ends with a perfume shop's name but is no subdomain.
LOOK = "x" + SHOP
IMG_URL = "https://cdn." + "example" + ".test/a.jpg"
FRAG = ("fragrances",)
#: The synthetic code registry (the RED file's): three fragrance-only rows, one
#: multi-category row.
ROWS = (
    SimpleNamespace(domain=SHOP, categories=FRAG),
    SimpleNamespace(domain=SUBROW, categories=FRAG),
    SimpleNamespace(domain=VAN, categories=FRAG),
    SimpleNamespace(domain=MULTI, categories=("fragrances", "makeup")),
)


def _cps(*code_points):
    return "".join(chr(cp) for cp in code_points)


def _u(path):
    return "https://" + SHOP + path


#: Arabic words by code point: eau, de (waw and yeh spellings, and the alef maqsura that
#: folds to yeh), toilette, the article + toilette, paper, cleaner, parfum (whole and
#: split in two), perfume, cologne, and the two gram units.
AR_EAU = _cps(0x0627, 0x0648)
AR_DE = _cps(0x062F, 0x0648)
AR_DE_I = _cps(0x062F, 0x064A)
AR_DE_MAQSURA = _cps(0x062F, 0x0649)
AR_TOILETTE = _cps(0x062A, 0x0648, 0x0627, 0x0644, 0x064A, 0x062A)
AR_THE_TOILETTE = _cps(0x0627, 0x0644) + AR_TOILETTE
AR_PAPER = _cps(0x0648, 0x0631, 0x0642)
AR_CLEANER = _cps(0x0645, 0x0646, 0x0638, 0x0641)
AR_PAR = _cps(0x0628, 0x0627, 0x0631)
AR_FAN = _cps(0x0641, 0x0627, 0x0646)
AR_PARFUM = AR_PAR + AR_FAN
AR_PERFUME = _cps(0x0628, 0x064A, 0x0631, 0x0641, 0x064A, 0x0648, 0x0645)
AR_COLOGNE = _cps(0x0643, 0x0648, 0x0644, 0x0648, 0x0646)
AR_GRAM = _cps(0x062C, 0x0631, 0x0627, 0x0645)
AR_GRAM_GH = _cps(0x063A, 0x0631, 0x0627, 0x0645)

SERPER_ITEM = {
    "imageUrl": _u("/a.jpg"),
    "title": "VELVET RAIN",
    "source": "Nimbus Shop",
    "link": _u("/p/1"),
    "domain": SHOP,
}
#: F1-2: a Serper Images item whose only edc is its source (a gear-shop site name).
EDC_SOURCE_ITEM = {
    "imageUrl": "https://" + BLOG + "/a.jpg",
    "title": "VELVET RAIN",
    "source": "EDC Store",
    "link": "https://" + BLOG + "/p/1",
    "domain": BLOG,
}
PAYLOAD_ORGANIC = {
    "organic": [{"title": "VELVET RAIN", "link": _u("/p/1"), "imageUrl": _u("/o.jpg")}]
}
PAYLOAD_KG_EDC = {
    "knowledgeGraph": {"title": "Velvet Rain", "type": "EDC", "imageUrl": _u("/k.jpg")}
}
ORGANIC = [{"title": "VELVET RAIN", "link": _u("/p/1")}]

#: F1-2: (typed, texts, host): everyday-carry gear titles typed with one word (and one
#: two-word line), edc only in the source, on a host outside the registry.
F12_SOURCE_ROWS = (
    ("Black", ("Black Folding Pocket Knife", "EDC Store"), GEAR),
    ("Titanium", ("Titanium Keychain Multitool", "The EDC Shop"), GEAR),
    ("Black Phantom", ("Black Phantom Tactical Flashlight", "EDC Supply Co"), GEAR),
    ("Velvet Rain", ("VELVET RAIN", "EDC Store"), BLOG),
)
#: F1-3: the toilette word outside the phrase: the old RED E1 case first, then the
#: article form and toilet goods.
F13_TOILET_ROWS = (
    ("Nimbus Velvet", ("NIMBUS VELVET " + AR_TOILETTE,), BLOG),
    ("Nimbus Velvet", ("NIMBUS VELVET " + AR_THE_TOILETTE,), BLOG),
    ("Velvet Rain", ("VELVET RAIN TOILET ROLL " + AR_PAPER + " " + AR_TOILETTE,), BLOG),
    (
        "Velvet Rain",
        ("VELVET RAIN " + AR_CLEANER + " " + AR_TOILETTE + " 500ml",),
        BLOG,
    ),
    ("Velvet Rain", (AR_TOILETTE + " VELVET RAIN",), BLOG),
)
#: F1-3: the eau-de-toilette phrase in its spellings (the run-together one included).
F13_PHRASES = (
    AR_EAU + " " + AR_DE + " " + AR_TOILETTE,
    AR_DE + " " + AR_TOILETTE,
    AR_EAU + " " + AR_DE_I + " " + AR_TOILETTE,
    AR_DE_MAQSURA + " " + AR_TOILETTE,
    AR_DE + AR_TOILETTE,
)
#: F1-4: (typed, texts, host, verdict after the fix).
F14_ROWS = (
    (AR_PERFUME + " V", ("CEDAR " + AR_PERFUME + " 2022",), MULTI, FW),
    (AR_PERFUME + " V", ("V " + AR_PERFUME + " 2022",), MULTI, None),
    (AR_PERFUME, ("CEDAR MOSS " + AR_PERFUME,), SHOP, FW),
    (
        AR_PERFUME + " " + AR_COLOGNE,
        ("CEDAR MOSS " + AR_PERFUME + " " + AR_COLOGNE,),
        SHOP,
        FW,
    ),
    ("Velvet " + AR_PERFUME, ("VELVET", AR_PERFUME + " House"), SHOP, FW),
    ("Velvet Rain " + AR_PERFUME, ("VELVET RAIN", AR_PERFUME + " House"), SHOP, None),
)
#: F1-5: the audience words and intense (ruling ORCH-I2C-FIX1 (a)).
AUDIENCE = (
    "men",
    "women",
    "man",
    "woman",
    "unisex",
    "homme",
    "femme",
    "him",
    "her",
    "boys",
    "girls",
    "intense",
)
#: F1-6: the kept home-scent pairs and the Arabic gram units after a number.
HOME_TAILS = (
    "HOME SPRAY",
    "CAR FRESHENER",
    "FABRIC SPRAY",
    "WAX MELT",
    "WAX MELTS",
    "50 " + AR_GRAM,
    "50 " + AR_GRAM_GH,
)
HOME_IDS = (
    "home_spray",
    "car_freshener",
    "fabric_spray",
    "wax_melt",
    "wax_melts",
    "ar_gram",
    "ar_gram_gh",
)
#: X3 (E07): (texts) whose only R1 word is in the source or a later text.
X3_TEXTS = (
    ("NIMBUS VELVET", "Nimbus " + AR_PERFUME),
    ("NIMBUS VELVET", "Nimbus Shop", "EDC"),
    ("NIMBUS VELVET", AR_PARFUM + " " + AR_COLOGNE),
)


# ---------------------------------------------------------------------------
# helpers (the RED file's house style)
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


def _v(q, title, host=None, *, texts=None, brand="", typed=None):
    """One Serper Images candidate through RelevanceCall.accept: None when accepted,
    else the call's reason."""
    call = _ir().RelevanceCall(q, _rel(q, typed, brand))
    ok = call.accept(
        "serper_images",
        IMG_URL,
        texts=(title,) if texts is None else tuple(texts),
        hosts=_hosts(host),
    )
    return None if ok else call.last_reason


def _vw(mp, w, q, title, host=None, **kw):
    """_v with the words flag set to ``w`` (None = unset); with W ON the typed text is
    the product name (relevance_kwargs adds it only with W ON)."""
    _set(mp, W_FLAG, w)
    return _v(q, title, host, typed=q if w else None, **kw)


def _kg(q, kg_type):
    """A knowledge-graph candidate (no host) whose type is ``kg_type``: accepted?"""
    call = _ir().RelevanceCall(q, _rel(q))
    return call.accept(
        "search_payload", IMG_URL, texts=(q,), fragrance_texts=(kg_type,)
    )


def _env_reads(mp):
    """RV-1: an env-read recorder: (how, name, module) of every os.getenv call and of
    every os.environ lookup (the os._Environ methods __getitem__, __contains__ and get,
    so os.environ[...], ``in`` and .get are seen too); module is the innermost app.*
    frame of the read, else the direct caller. monkeypatch restores all four."""
    seen = []
    env_class = type(os.environ)
    real_getenv = os.getenv
    real = {
        how: getattr(env_class, how) for how in ("__getitem__", "__contains__", "get")
    }

    def _module():
        frame = sys._getframe(2)
        first = frame.f_globals.get("__name__")
        while frame is not None:
            name = frame.f_globals.get("__name__") or ""
            if name.startswith("app."):
                return name
            frame = frame.f_back
        return first

    def _getenv(key, default=None):
        seen.append(("getenv", key, _module()))
        return real_getenv(key, default)

    def _getitem(self, key):
        seen.append(("getitem", key, _module()))
        return real["__getitem__"](self, key)

    def _contains(self, key):
        seen.append(("contains", key, _module()))
        return real["__contains__"](self, key)

    def _get(self, key, default=None):
        seen.append(("get", key, _module()))
        return real["get"](self, key, default)

    mp.setattr(os, "getenv", _getenv)
    mp.setattr(env_class, "__getitem__", _getitem)
    mp.setattr(env_class, "__contains__", _contains)
    mp.setattr(env_class, "get", _get)
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


def _gpu(mp, caplog, *, images=(), payload=None, organic=None, rel=None):
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
            relevance=_rel("Velvet Rain") if rel is None else rel,
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


# ---------------------------------------------------------------------------
# E rows: one per fix F1-1..F1-7, and the gap X3
# ---------------------------------------------------------------------------


def test_e01_f1_1_the_registry_read_parses_only_fragrance_only_rows(monkeypatch):
    """F1-1 (A2-D1): _perfume_domains tests a row's categories before ``_host``, so only
    the fragrance-only rows are parsed (the head parsed every row: 319 a call with the
    catalog ON, flushing the process-wide URL-split cache); the domains are unchanged,
    a list of categories included."""
    _flags(monkeypatch)
    ir = _ir()
    domains_of = _sym(ir, "_perfume_domains")
    rows = [
        SimpleNamespace(domain=SHOP, categories=FRAG),
        SimpleNamespace(domain=MULTI, categories=("fragrances", "makeup")),
        SimpleNamespace(domain=BLOG, categories=None),
        SimpleNamespace(domain=GEAR, categories=("electronics",)),
        SimpleNamespace(domain=VAN, categories=list(FRAG)),
    ]
    monkeypatch.setattr(_sr(), "SOURCE_REGISTRY", rows)
    real = ir._host
    seen = []

    def _rec(value):
        seen.append(value)
        return real(value)

    monkeypatch.setattr(ir, "_host", _rec)
    assert domains_of() == frozenset({SHOP, VAN})
    assert seen == [SHOP, VAN], seen


def test_e02_f1_2_r1_reads_the_title_and_the_kg_types_only(monkeypatch, caplog):
    """F1-2 (A1-D2, C13): edc only in the Serper source text (a site name: everyday-
    carry gear titles typed with one word, a gear-shop source) no longer rescues on a
    host outside the registry, W unset and ON, and the cascade logs the base refusal;
    edc in the title or a knowledge-graph type still rescues."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    _flags(monkeypatch)
    for w in (None, "true"):
        for q, texts, host in F12_SOURCE_ROWS:
            got = _vw(monkeypatch, w, q, None, host, texts=texts)
            assert got == FW, (q, texts, w, got)
        texts = ("VELVET RAIN EDC", "Nimbus Shop")
        got = _vw(monkeypatch, w, "Velvet Rain", None, BLOG, texts=texts)
        assert got is None, (w, got)
    _set(monkeypatch, W_FLAG, None)
    url, lines, _t = _gpu(monkeypatch, caplog, images=[EDC_SOURCE_ITEM])
    assert url is None, url
    assert lines == [_line("serper_images", "rejected", 1, FW)], lines
    assert _kg("Velvet Rain", "EDC") is True


def test_e03_f1_3_the_arabic_toilette_counts_only_in_the_phrase(monkeypatch):
    """F1-3 (A1-D3, C9b; ruling ORCH-I2C-FIX1 (b)): the Arabic toilette word alone (the
    old RED E1 case), with the article, or among toilet goods (toilet paper, a toilet
    cleaner) no longer rescues on a host outside the registry, nor as a knowledge-graph
    type; the eau-de-toilette phrase (the word right after U+062F 0648 or U+062F 064A,
    the alef maqsura folded, the run-together spelling too) still rescues, in a title
    or a knowledge-graph type; W unset and ON."""
    _flags(monkeypatch)
    for w in (None, "true"):
        for q, texts, host in F13_TOILET_ROWS:
            got = _vw(monkeypatch, w, q, None, host, texts=texts)
            assert got == FW, (ascii(texts), w, got)
        for phrase in F13_PHRASES:
            title = "NIMBUS VELVET " + phrase
            got = _vw(monkeypatch, w, "Nimbus Velvet", title, BLOG)
            assert got is None, (ascii(phrase), w, got)
    _set(monkeypatch, W_FLAG, None)
    assert _kg("Nimbus Velvet", AR_TOILETTE) is False
    assert _kg("Nimbus Velvet", AR_DE + " " + AR_TOILETTE) is True


def test_e04_f1_4_r1_words_are_no_line_words(monkeypatch):
    """F1-4 (A1-D1, F2): in the second look the R1 words are not significant line
    words. A typed Arabic perfume word plus a one-character token no longer accepts
    another product's title holding the word but not the token, at a shop R3 cannot
    prove (the multi-category row); its own title still passes; a line of R1 words only
    stays refused; and an R1 word never counts toward the R3 floor (the second row on
    SHOP, its R1 word only in the source); W unset and ON."""
    _flags(monkeypatch)
    for w in (None, "true"):
        for q, texts, host, want in F14_ROWS:
            got = _vw(monkeypatch, w, q, None, host, texts=texts)
            assert got == want, (ascii(q), ascii(texts), w, got)


@pytest.mark.parametrize("word", AUDIENCE)
def test_e05_f1_5_an_audience_line_gets_no_second_look(monkeypatch, word):
    """F1-5 (ruling ORCH-I2C-FIX1 (a)): a typed line whose significant words are all
    audience words or intense gets no second look: alone with edc in the title on a
    host outside the registry, and two of them on a registry perfume shop; a line with
    one other word is still rescued there, and a title the base accepts stays accepted;
    W unset and ON."""
    _flags(monkeypatch)
    cap = word.capitalize()
    pair = cap + (" Men" if word == "women" else " Women")
    for w in (None, "true"):
        got = _vw(monkeypatch, w, cap, word.upper() + " EDC 100ML", BLOG)
        assert got == FW, (word, w, got)
        got = _vw(monkeypatch, w, pair, pair.upper(), SHOP)
        assert got == FW, (pair, w, got)
        got = _vw(monkeypatch, w, "Velvet " + cap, "VELVET " + word.upper(), SHOP)
        assert got is None, (word, w, got)
        got = _vw(monkeypatch, w, cap, word.upper() + " EDP 100ML", BLOG)
        assert got is None, (word, w, got)


@pytest.mark.parametrize("tail", HOME_TAILS, ids=HOME_IDS)
def test_e06_f1_6_home_pairs_and_arabic_grams_refuse_a_rescue(monkeypatch, tail):
    """F1-6 (A1-M2): each kept home-scent pair and each Arabic gram unit after a number
    refuses a rescued title form, W unset and ON; the typed exemption stands: typed
    whole, the title passes; with only its first word typed, it is refused."""
    _flags(monkeypatch)
    first = tail.split()[0]
    for w in (None, "true"):
        got = _vw(monkeypatch, w, "Velvet Rain", "VELVET RAIN " + tail, SHOP)
        assert got == "form", (ascii(tail), w, got)
        got = _vw(monkeypatch, w, "Velvet Rain " + tail, "VELVET RAIN " + tail, SHOP)
        assert got is None, (ascii(tail), w, got)
        got = _vw(monkeypatch, w, "Velvet Rain " + first, "VELVET RAIN " + tail, SHOP)
        assert got == "form", (ascii(tail), w, got)


def test_e07_x3_r1_never_reads_the_source_or_a_later_text(monkeypatch):
    """X3 (A1 M-1; F1-2): an R1 word only in the Serper source text or in a later text
    (an Arabic perfume word, edc, the Arabic parfum and cologne) never rescues on a host
    outside the registry; in the title, or as a knowledge-graph type, it does; W unset
    and ON."""
    _flags(monkeypatch)
    for w in (None, "true"):
        for texts in X3_TEXTS:
            got = _vw(monkeypatch, w, "Nimbus Velvet", None, BLOG, texts=texts)
            assert got == FW, (ascii(texts), w, got)
        texts = ("NIMBUS VELVET " + AR_PERFUME, "Nimbus Shop")
        got = _vw(monkeypatch, w, "Nimbus Velvet", None, BLOG, texts=texts)
        assert got is None, (w, got)
    _set(monkeypatch, W_FLAG, None)
    assert _kg("Nimbus Velvet", AR_PERFUME) is True


def test_e08_f1_7_the_constructor_protocol_is_kept(monkeypatch):
    """F1-7 (A2-D3): RelevanceCall.__new__ takes *args and **kwargs and passes them on:
    the positional and keyword forms build the recall class with the switch ON and the
    base class with it unset, and a subclass whose __init__ takes one more argument
    builds, positional or keyword, either way (the head's __new__ took at most two
    arguments and raised TypeError)."""
    ir = _ir()
    for rc, want in ((True, "_RecallCall"), (None, "RelevanceCall")):
        _flags(monkeypatch, rc=rc)
        for call in (
            ir.RelevanceCall("a", None),
            ir.RelevanceCall(product_name="a", relevance=None),
        ):
            assert type(call).__name__ == want, (rc, type(call).__name__)
            assert call.product_name == "a" and call.n == 0

    class _Tagged(ir.RelevanceCall):
        def __init__(self, product_name, relevance, tag=None):
            super().__init__(product_name, relevance)
            self.tag = tag

    for rc in (True, None):
        _flags(monkeypatch, rc=rc)
        for args, kwargs in ((("a", None, "x"), {}), (("a", None), {"tag": "x"})):
            try:
                built = _Tagged(*args, **kwargs)
            except TypeError as exc:
                built = exc
            assert isinstance(built, _Tagged) and built.tag == "x", (rc, built)


# ---------------------------------------------------------------------------
# P rows (green at the head and after the fix)
# ---------------------------------------------------------------------------


def test_p01_x1_a_look_alike_host_is_no_perfume_shop(monkeypatch):
    """X1 (A1 M-1): a host that only ends with a perfume shop's name ("x" + SHOP) is no
    perfume shop: the subdomain test keeps its dot; a real subdomain is one; W unset
    and ON."""
    _flags(monkeypatch)
    for w in (None, "true"):
        for host in (LOOK, "x" + VAN):
            got = _vw(monkeypatch, w, "Velvet Rain", "VELVET RAIN", host)
            assert got == FW, (host, w, got)
        got = _vw(monkeypatch, w, "Velvet Rain", "VELVET RAIN", "bh." + SHOP)
        assert got is None, (w, got)
    shop_of = _sym(_ir(), "_perfume_shop")
    assert shop_of(("https://" + LOOK + "/p/1", LOOK)) is False


def test_p02_x2_r1_reads_the_adjacent_pair_joins_of_the_title(monkeypatch):
    """X2 (A1 M-1): R1 reads the title's adjacent-pair joins: the Arabic parfum split in
    two rescues on a host outside the registry; split across the title and the source
    it does not (a join never crosses two texts); W unset and ON."""
    _flags(monkeypatch)
    for w in (None, "true"):
        title = "NIMBUS VELVET " + AR_PAR + " " + AR_FAN
        got = _vw(monkeypatch, w, "Nimbus Velvet", title, BLOG)
        assert got is None, (w, got)
        texts = ("NIMBUS VELVET " + AR_PAR, AR_FAN + " House")
        got = _vw(monkeypatch, w, "Nimbus Velvet", None, BLOG, texts=texts)
        assert got == FW, (w, got)


def test_p03_x4_r3_reads_every_candidate_host(monkeypatch, caplog):
    """X4 (A1 M-1): R3 reads every candidate host, not only the first: a link outside the
    registry with the Serper domain on the shop is rescued, in both orders, and through
    the cascade."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    _flags(monkeypatch)
    for hosts in (("https://" + BLOG + "/p/1", SHOP), (_u("/p/1"), BLOG)):
        call = _ir().RelevanceCall("Velvet Rain", _rel("Velvet Rain"))
        ok = call.accept("serper_images", IMG_URL, texts=("VELVET RAIN",), hosts=hosts)
        assert ok is True, (hosts, call.last_reason)
    item = dict(SERPER_ITEM, link="https://" + BLOG + "/p/1")
    url, lines, _t = _gpu(monkeypatch, caplog, images=[item])
    assert url == item["imageUrl"], url
    assert lines == [_line("serper_images", "accepted", 1, "none")], lines


def test_p04_x5_a_gram_unit_counts_only_after_a_number(monkeypatch):
    """X5 (A1 M-1): a gram unit with no number before it (Latin or Arabic) never refuses
    a rescue; after a number it does; W unset and ON."""
    _flags(monkeypatch)
    for w in (None, "true"):
        for tail in ("GRAM", "G", "GRAMS", "GR", AR_GRAM, AR_GRAM_GH):
            got = _vw(monkeypatch, w, "Velvet Rain", "VELVET RAIN " + tail, SHOP)
            assert got is None, (ascii(tail), w, got)
        got = _vw(monkeypatch, w, "Velvet Rain", "VELVET RAIN 50 GRAM", SHOP)
        assert got == "form", (w, got)


#: Ruling (d): the four flags, their readers (A's in image_relevance, called by the
#: WooCommerce adapter; B's and L's in image_service, called by SCS; R's in
#: product_resolver) and the constants that hold the names.
ABRL = (A_FLAG, B_FLAG, R_FLAG, L_FLAG)
ABRL_READERS = (
    "shop_page_image_enabled",
    "shopping_thumb_enabled",
    "product_resolver_enabled",
    "late_bind_enabled",
)
ABRL_CONSTANTS = (
    "SHOP_PAGE_IMAGE_FLAG_ENV",
    "SHOPPING_THUMB_FLAG_ENV",
    "LATE_BIND_FLAG_ENV",
)
#: The roots of the RelevanceCall verdict path (ruling (d)(i)).
VERDICT_ROOTS = (
    "check",
    "_check_base",
    "_check_short_line",
    "_words_reason",
    "identity",
    "RelevanceCall",
    "_RecallCall",
    "_recall_reason",
    "_home_reason",
    "_perfume_domains",
    "_perfume_shop",
)
#: Members the closure must hold (so the scan is not vacuous).
VERDICT_MUST = VERDICT_ROOTS + (
    "_conc_scan",
    "_candidate_keys",
    "_text_tokens",
    "_host",
    "_denied",
    "guard_enabled",
    "recall_enabled",
    "short_line_enabled",
    "guard_words_enabled",
)
#: RV-1: the roots of the image_service cascade (the rest of the image layer).
CASCADE_ROOTS = (
    "get_product_image_url",
    "get_product_image_url_late",
    "shopping_thumbnail",
    "stamp_shop_image",
    "pick_cache_name",
)
#: Members the cascade closure must hold, and image_relevance names it must reach.
CASCADE_MUST = CASCADE_ROOTS + (
    "_relevant_serper_image",
    "_extract_relevant_image_from_search",
    "_read_cached_pick",
    "_store_pick",
    "_name_part",
)
CASCADE_USES = (
    "RelevanceCall",
    "guard_enabled",
    "first_https_raster",
    "words_reason_for",
)
#: RV-1: the listing photo of the stamp_shop_image scenario.
PAGE_IMG = "https://shop." + "example" + ".com/wp/s.jpg"


def _closure(module, roots):
    """(name -> source, used): every function and class of ``module`` the roots reach by
    name, transitively (a class brings all of its methods), the roots included; ``used``
    holds the image_relevance functions and classes those sources name as an attribute
    of an image_relevance alias (image_service's ``_relevance.<name>``)."""
    ir = _ir()

    def own(mod):
        return {
            name
            for name, obj in vars(mod).items()
            if (inspect.isfunction(obj) or inspect.isclass(obj))
            and obj.__module__ == mod.__name__
        }

    names, ir_names = own(module), own(ir)
    found, used = {}, set()
    todo = list(roots)
    while todo:
        name = todo.pop()
        if name in found:
            continue
        src = textwrap.dedent(inspect.getsource(getattr(module, name)))
        found[name] = src
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Name) and node.id in names:
                todo.append(node.id)
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and vars(module).get(node.value.id) is ir
                and node.attr in ir_names
            ):
                used.add(node.attr)
    return found, used


def test_p05_the_verdict_path_reads_no_a_b_r_or_l_flag(monkeypatch, caplog):
    """Ruling (d), widened by RV-1: the image layer reads none of ENABLE_SHOP_PAGE_IMAGE
    (A), ENABLE_SHOPPING_THUMB_IMAGE (B), ENABLE_PRODUCT_RESOLVER (R) and
    ENABLE_IMAGE_LATE_BIND (L). (i) Static: the source of every image_service function
    the cascade roots (get_product_image_url, get_product_image_url_late,
    shopping_thumbnail, stamp_shop_image, pick_cache_name) reach by name, and of every
    image_relevance function and class that the verdict roots (check, _check_base,
    _check_short_line, _words_reason, identity, RelevanceCall and _RecallCall with
    every method, _recall_reason, _home_reason, _perfume_domains, _perfume_shop) or
    those image_service functions (as _relevance.<name>) reach, transitively, names none
    of the four, their readers or the constants that hold them; A's reader
    shop_page_image_enabled is off the path. (ii) Runtime: with the four set "true" and
    G, S, W and the switch ON, a recorder of os.getenv and of every os.environ lookup
    (the os._Environ methods __getitem__, __contains__ and get; proven live first) over
    guarded calls of the five roots (Serper Images, the payload organic item and
    knowledge graph, llm_pick, the late call, the thumbnail, the shop-page stamp, the
    cache name) sees image_relevance read G, S, W and the switch, and 0 reads of the
    four by any module. Not covered: SCS (structured_comparison_service), not the image
    layer, calls B's and L's readers (both defined in image_service, where no function
    calls them) and R's (in product_resolver); the WooCommerce adapter calls A's (in
    image_relevance); the modules the two layers import (category_gate, deny_hosts,
    jsonld_widen, price_service, source_router and the rest) are not scanned, only
    recorded on the paths the scenarios run (the Serper, credit, LLM and cache leaves
    are fakes)."""
    cascade, used = _closure(_img(), CASCADE_ROOTS)
    path = _closure(_ir(), VERDICT_ROOTS + tuple(sorted(used)))[0]
    missing = [name for name in VERDICT_MUST if name not in path]
    missing += [name for name in CASCADE_MUST if name not in cascade]
    missing += [name for name in CASCADE_USES if name not in used]
    assert not missing, missing
    assert "shop_page_image_enabled" not in path
    scanned = [("image_relevance", name, src) for name, src in path.items()]
    scanned += [("image_service", name, src) for name, src in cascade.items()]
    hits = sorted(
        (module, name, word)
        for module, name, src in scanned
        for word in ABRL + ABRL_READERS + ABRL_CONSTANTS
        if word in src
    )
    assert hits == [], hits

    caplog.set_level(logging.INFO, logger=LOGGER)
    _flags(monkeypatch, w=True)
    for name in ABRL:
        monkeypatch.setenv(name, "true")
    ir, img = _ir(), _img()
    rel = _rel("Velvet Rain", "Velvet Rain")
    seen = _env_reads(monkeypatch)
    assert os.getenv(G_FLAG) == os.environ.get(G_FLAG) == os.environ[G_FLAG] == "true"
    assert G_FLAG in os.environ
    hows = {how for how, key, _m in seen if key == G_FLAG}
    assert hows == {"getenv", "get", "getitem", "contains"}, hows
    del seen[:]
    urls = [
        _gpu(monkeypatch, caplog, images=[SERPER_ITEM], rel=rel)[0],
        _gpu(monkeypatch, caplog, payload=PAYLOAD_ORGANIC, rel=rel)[0],
        _gpu(monkeypatch, caplog, payload=PAYLOAD_KG_EDC, rel=rel)[0],
        _gpu(monkeypatch, caplog, organic=ORGANIC, rel=rel)[0],
    ]
    assert urls == [_u("/a.jpg"), _u("/o.jpg"), _u("/k.jpg"), _u("/pick.jpg")], urls
    t = _T()
    _install_tiers(monkeypatch, t, images=[SERPER_ITEM], gpt_url=_u("/pick.jpg"))
    late_url, _state = _late_run(rel)
    assert late_url == _u("/a.jpg"), late_url
    thumb = img.shopping_thumbnail(_thumb("VELVET RAIN"), "Velvet Rain", 0, rel)
    assert thumb == _u("/t.jpg"), thumb
    price = {}
    listing = {"images": [{"src": PAGE_IMG}]}
    img.stamp_shop_image(price, "woo", listing, None, "Velvet Rain", "VELVET RAIN")
    assert price == {"image_url": PAGE_IMG}, price
    cache_name = img.pick_cache_name(rel, None)
    assert t.set == [cache_name], (t.set, cache_name)
    by_leaf = {key for _how, key, module in seen if module == ir.__name__}
    assert {G_FLAG, S_FLAG, RC_FLAG, W_FLAG} <= by_leaf, sorted(by_leaf)
    abrl = [(how, key, module) for how, key, module in seen if key in ABRL]
    assert abrl == [], abrl


def _p06_rows():
    """(typed, texts, host, base verdict) of every verdict scenario of the E rows."""
    rows = [(q, texts, host, FW) for q, texts, host in F12_SOURCE_ROWS]
    rows.append(("Velvet Rain", ("VELVET RAIN EDC", "Nimbus Shop"), BLOG, FW))
    rows += [(q, texts, host, FW) for q, texts, host in F13_TOILET_ROWS]
    rows += [
        ("Nimbus Velvet", ("NIMBUS VELVET " + phrase,), BLOG, FW)
        for phrase in F13_PHRASES
    ]
    rows += [(q, texts, host, FW) for q, texts, host, _want in F14_ROWS]
    for word in AUDIENCE:
        cap = word.capitalize()
        pair = cap + (" Men" if word == "women" else " Women")
        rows.append((cap, (word.upper() + " EDC 100ML",), BLOG, FW))
        rows.append((pair, (pair.upper(),), SHOP, FW))
        rows.append(("Velvet " + cap, ("VELVET " + word.upper(),), SHOP, FW))
        rows.append((cap, (word.upper() + " EDP 100ML",), BLOG, None))
    for tail in HOME_TAILS:
        first = tail.split()[0]
        for q in ("Velvet Rain", "Velvet Rain " + tail, "Velvet Rain " + first):
            rows.append((q, ("VELVET RAIN " + tail,), SHOP, FW))
    rows += [("Nimbus Velvet", texts, BLOG, FW) for texts in X3_TEXTS]
    rows.append(
        ("Nimbus Velvet", ("NIMBUS VELVET " + AR_PERFUME, "Nimbus Shop"), BLOG, FW)
    )
    return rows


def test_p06_rc_unset_every_fix_scenario_is_the_base_verdict(monkeypatch):
    """RC unset (the merge state): every verdict scenario of the E rows gives the base
    verdict (fragrance_word, or None for a title the base accepts), W unset and ON, and
    the base class is built."""
    _flags(monkeypatch, rc=None)
    assert type(_ir().RelevanceCall("a", None)).__name__ == "RelevanceCall"
    for w in (None, "true"):
        for q, texts, host, want in _p06_rows():
            got = _vw(monkeypatch, w, q, None, host, texts=texts)
            assert got == want, (ascii(q), ascii(texts), w, got)
