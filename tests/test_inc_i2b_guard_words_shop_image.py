"""INC-I2b GUARD-WORDS + SHOP-IMAGE-TIER RED rows (three dark flags, default OFF).

Spec: s96/i2b/spec/INC_I2B_UNIT_SPEC_V2.md section 5, as ruled by RULINGS_INC_I2B.md
(I-1..I-19).

* W = ENABLE_IMAGE_GUARD_WORDS: under the relevance guard, a candidate whose title
  names another FORM (body care, a set, a refill, a miniature) or a concentration the
  user did not ask for is refused (reasons form, concentration).
* A = ENABLE_SHOP_PAGE_IMAGE: the WooCommerce adapter stamps the winning listing's own
  photo on the price dict (guarded, words-tested).
* B = ENABLE_SHOPPING_THUMB_IMAGE (owner policy): a guarded Google Shopping thumbnail
  is the last-resort picture.

RED rows E1..E19 fail at base on an AssertionError only: every missing symbol is read
through ``_need`` (hasattr + an assertion). PIN rows P1..P5 are green at base. P1 runs
with the FULL unit configuration (B1): the three flags unset and "false", every image
knob set to a synthetic value; it compares observations with
tests/fixtures/inc_i2b_flag_off_golden.json (recorded at base 5cd93c6a).

Hermetic: the Serper / credit / LLM leaves of image_service, the unified search, the
specs / price / reviews legs and the image cache are faked; no network, no Redis, no
LLM. Synthetic identities and example hosts only (well-known brand names appear as
corpus words only). Pure ASCII, LF.
"""

from __future__ import annotations

import asyncio
import collections
import copy
import hashlib
import inspect
import json
import logging
import os
import re
import time
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "inc_i2b_guard_words_corpus.json"
GOLDEN = ROOT / "tests" / "fixtures" / "inc_i2b_flag_off_golden.json"

G_FLAG = "ENABLE_IMAGE_RELEVANCE_GUARD"
S_FLAG = "ENABLE_IMAGE_GUARD_SHORT_LINE"
W_FLAG = "ENABLE_IMAGE_GUARD_WORDS"
A_FLAG = "ENABLE_SHOP_PAGE_IMAGE"
B_FLAG = "ENABLE_SHOPPING_THUMB_IMAGE"
L_FLAG = "ENABLE_IMAGE_LATE_BIND"
R_FLAG = "ENABLE_PRODUCT_RESOLVER"
UNIT_FLAGS = (W_FLAG, A_FLAG, B_FLAG)
SYNTH_KNOBS = {
    "IMAGE_LATE_BIND_MAX_WAIT_SECONDS": "7",
    "IMAGE_LATE_BIND_RESERVE_SECONDS": "9",
    "IMAGE_LATE_MAX_SECONDS": "11",
    "IMAGE_PICK_CACHE_TTL_SECONDS": "13",
    "IMAGE_RELEVANCE_CANDIDATES": "5",
}
CLEARED_ENV = (
    (G_FLAG, S_FLAG, W_FLAG, A_FLAG, B_FLAG, L_FLAG, R_FLAG)
    + tuple(SYNTH_KNOBS)
    + (
        "ENABLE_KB_FIRST_SERVE",
        "ENABLE_KB_INGEST",
        "ENABLE_IMAGE_PIPELINE_V2",
        "ENABLE_DATA_GUARDS_V2",
        "ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT",
        "ENABLE_EARLY_SPECS_STASH",
        "ENABLE_FACTCHECK_SHOPPING_KEY",
        "ENABLE_ADAPTER_SELECTION_PRIMARY",
        "ENABLE_VARIANT_MIN_PRICE_GUARD",
        "DEBUG_STAGE_TIMINGS",
    )
)

REL_LINE = re.compile(
    r"^\[IMG_RELEVANCE\] product=(0|1|-) tier=(none|piggyback|search_payload|"
    r"serper_images|llm_pick) outcome=(accepted|rejected|none) candidates=(\d+) "
    r"reason=(none|scheme|brand|name|fragrance_word|denied|form|concentration)$"
)
PAGE_LINE = re.compile(
    r"^IMG_SHOP page platform=woo outcome=(stamped|no_image|refused|skipped|error) "
    r"reason=(none|form|concentration) shape=(list|dict|str|none|other|-) "
    r"keys=(-|[A-Za-z][A-Za-z0-9_]{0,31}(?:,[A-Za-z][A-Za-z0-9_]{0,31}){0,11}) "
    r"other=(\d+)$"
)
KEYS_LINE = re.compile(
    r"^IMG_SHOP keys product=(0|1|-) "
    r"names=(-|[A-Za-z][A-Za-z0-9_]{0,31}(?:,[A-Za-z][A-Za-z0-9_]{0,31}){0,23}) "
    r"other=(\d+) with_url=(\d+) https=(\d+) gstatic=(\d+)$"
)
THUMB_LINE = re.compile(
    r"^IMG_SHOP thumb product=(0|1|-) outcome=(accepted|rejected|none|skipped|error) "
    r"candidates=(\d+) "
    r"reason=(none|scheme|brand|name|fragrance_word|denied|form|concentration)$"
)
BIND = re.compile(
    r"^IMG_LATE bind product=(0|1) outcome=(attached|cached|override|fallback|shopping|"
    r"none|missed_at_deadline) wait_ms=(\d+)$"
)

SHOP = "shop.example.com"
IMG_HOST = "img.example.com"
GSTATIC_HOST = "encrypted-tbn0." + "gstatic" + ".com"
URL_EDP = "https://" + IMG_HOST + "/p/sauvage-edp.jpg"
URL_EDT = "https://" + IMG_HOST + "/p/sauvage-edt.jpg"
URL_DEO = "https://" + IMG_HOST + "/p/sauvage-deo.jpg"
URL_SET = "https://" + IMG_HOST + "/p/sauvage-set.jpg"
URL_RIGHT = "https://" + IMG_HOST + "/p/sauvage-right.jpg"
URL_S0 = "https://" + IMG_HOST + "/p/nimbus-noir-1.jpg"
WOO_A = "https://" + SHOP + "/wp-content/uploads/khamrah-a.jpg"
WOO_B = "https://" + SHOP + "/wp-content/uploads/khamrah-b.jpg"
THUMB_SET = "https://" + GSTATIC_HOST + "/images/set-1.jpg"
THUMB_RIGHT = "https://" + IMG_HOST + "/t/nimbus-right.jpg"

P0 = ("Acme", "Nimbus Noir")
PINFO0 = {
    "brand": P0[0],
    "name": P0[1],
    "variant": "EDP 100ml",
    "category": "fragrances",
    "search_query": "Acme Nimbus Noir EDP 100ml",
}
PRICE_URL = "https://" + SHOP + "/products/nimbus-noir"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _ir():
    from app.services import image_relevance

    return image_relevance


def _img():
    from app.services import image_service

    return image_service


def _scs():
    import app.services.structured_comparison_service as scs

    return scs


def _woo():
    from app.services import woocommerce_service

    return woocommerce_service


def _need(obj, name):
    assert hasattr(obj, name), "%s.%s is missing (INC-I2b not implemented)" % (
        getattr(obj, "__name__", type(obj).__name__),
        name,
    )
    return getattr(obj, name)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    yield


def _flags(mp, **kw):
    names = {
        "g": G_FLAG,
        "s": S_FLAG,
        "w": W_FLAG,
        "a": A_FLAG,
        "b": B_FLAG,
        "late": L_FLAG,
        "r": R_FLAG,
    }
    state = {"g": True, "s": True}
    state.update(kw)
    for key, value in state.items():
        name = names[key]
        if value is None or value is False:
            mp.delenv(name, raising=False)
        elif value is True:
            mp.setenv(name, "true")
        else:
            mp.setenv(name, value)


def _msgs(caplog, prefix):
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith(prefix)]


def _rel(brand, line, typed=None, slot=0):
    rel = {"brand": brand, "line": line, "category": "fragrances", "slot": slot}
    if typed is not None:
        rel["typed"] = typed
    return rel


def _verdict(product, brand, line, title, typed=True, texts=None):
    """check() of one title for one query; typed=True -> the product name is typed."""
    ir = _ir()
    t = product if typed is True else typed
    ident = ir.identity(product, _rel(brand, line, t if t else None))
    return ir.check(ident, list(texts) if texts else [title])


async def _drain_bg(limit=15.0):
    from app.utils import async_utils as au

    loop = asyncio.get_running_loop()
    end = time.monotonic() + limit
    while time.monotonic() < end:
        pending = [
            t
            for t in list(au._BACKGROUND_TASKS)
            if not t.done() and t.get_loop() is loop
        ]
        if not pending:
            return
        await asyncio.wait(pending, timeout=max(0.01, end - time.monotonic()))


class _T:
    def __init__(self):
        self.credit = []
        self.search = []
        self.gpt = []
        self.get = []
        self.set = []
        self.store = {}


def _item(url, title, slug="p"):
    return {
        "imageUrl": url,
        "title": title,
        "source": "Example Shop",
        "link": "https://" + SHOP + "/p/" + slug,
        "domain": SHOP,
    }


def _install_tiers(mp, t, *, images=(), gpt_url=None, granted=True):
    img = _img()

    def _credit(n):
        t.credit.append(n)
        return granted

    async def _search(name, **kwargs):
        t.search.append({"q": name, "kw": dict(kwargs)})
        return {"images": list(images(name) if callable(images) else images)}

    async def _gpt(name, organic):
        t.gpt.append(name)
        return gpt_url

    def _get(key):
        t.get.append(key)
        return copy.deepcopy(t.store.get(key))

    def _set(key, value, ttl=None, *a, **k):
        t.set.append(key)
        t.store[key] = copy.deepcopy(value)
        return True

    mp.setattr(img, "try_consume_serper_image_credit", _credit)
    mp.setattr(img, "search_images", _search)
    mp.setattr(img, "extract_image_via_gpt", _gpt)
    mp.setattr(img, "get_cached", _get, raising=False)
    mp.setattr(img, "set_cached", _set, raising=False)


def _price(*, image=None, url=PRICE_URL, amount=55.0):
    p = {
        "amount": amount,
        "currency": "BHD",
        "estimated": False,
        "source_method": "local_bhd",
        "retailer": "Live Store",
        "url": url,
        "title": "x",
        "in_stock": True,
    }
    if image is not None:
        p["image_url"] = image
    return p


def _payload_plain(query):
    return {
        "organic": [
            {
                "title": "T " + query[:20],
                "link": "https://" + "example.com/a",
                "snippet": "eau de parfum woody longevity 8 hours",
            }
        ]
    }


def _fetch_setup(mp, svc, *, price=None, kb_card=None, shopping=None):
    scs = _scs()

    async def _specs(*a, **_k):
        return {"concentration": "Eau de Parfum", "scent_family": "amber"}

    async def _price_leg(brand, name, variant, *a, **_k):
        if shopping is not None:
            key = scs._shopping_cache_key(brand, name, variant)
            svc._shopping_items_cache[key] = copy.deepcopy(shopping)
        return copy.deepcopy(price) if price is not None else _price()

    async def _reviews(*a, **_k):
        return {"highlights": ["good"], "summary": "ok"}

    async def _search_web(query, num_results=10, **kwargs):
        return _payload_plain(query)

    async def _rating(*a, **_k):
        return {
            "rating": 4.5,
            "review_count": 10,
            "rating_verified": True,
            "rating_source": {"name": "example", "url": "https://" + "example.com/r"},
        }

    async def _empty(*a, **_k):
        return {}

    svc._get_specs = _specs
    svc._get_price = _price_leg
    svc._get_reviews = _reviews
    svc._get_verified_rating = _rating
    svc._smart_fallback_extract = _empty
    mp.setattr(svc, "_track_serper_cost", lambda *a, **k: None)
    mp.setattr(svc, "_track_gpt_cost", lambda *a, **k: None)
    mp.setattr(scs, "search_web", _search_web)
    mp.setattr(scs, "tier2_fill_non_negotiables", _empty)
    mp.setattr(scs, "tier3_synthesize_non_negotiables", _empty)
    mp.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    svc._compare_deadline = time.monotonic() + 30.0
    if kb_card is not None:
        from app.services import kb_serve

        def _classify(card, **_k):
            return {
                "hit": "partial",
                "price": None,
                "specs": None,
                "specs_complete": False,
                "candidates": [],
                "image_url": kb_card,
                "reviews": None,
            }

        mp.setattr(kb_serve, "classify", _classify)


async def _kb_task_done():
    fut = asyncio.get_running_loop().create_future()
    fut.set_result([{}, {}])
    return fut


def _fetch_run(mp, pinfo=None, *, price=None, kb_card=None, shopping=None, bind=False):
    async def go():
        svc = _scs().StructuredComparisonService()
        _fetch_setup(mp, svc, price=price, kb_card=kb_card, shopping=shopping)
        if kb_card is not None:
            svc._kb_cards_task = await _kb_task_done()
            svc._kb_hit_marks = ["miss", "miss"]
            svc._kb_views = [None, None]
        result = await svc._fetch_product_data(
            dict(pinfo or PINFO0), "bahrain", True, True, True, partial_slot=0
        )
        if bind:
            await asyncio.sleep(0.02)
            await svc._late_image_bind()
        await _drain_bg()
        return result

    return _run(go())


# --- the corpus -------------------------------------------------------------------


def _corpus():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def _truth(q, row):
    cls, conc = row[4], row[2]
    if q[5] is None:
        return cls in ("base", "size", "tester", "conc") and conc in (
            "EDT",
            "EDP",
            "Parfum",
        )
    return cls in ("base", "size", "tester") and conc == q[5]


def _key(acc, truth):
    return ("A" if acc else "R") + ("R" if acc == truth else "W")


def _corpus_run(mp, s_on, which, typed):
    """(base, on) verdict tables of the corpus: W unset vs W ON, both under G."""
    c = _corpus()
    ir = _ir()
    _flags(mp, s=s_on)
    out = {
        "base": collections.Counter(),
        "on": collections.Counter(),
        "aw_on": collections.Counter(),
        "reasons": collections.Counter(),
        "right_refused": 0,
        "aw_left": [],
    }
    for q in c[which]:
        rel = _rel(q[3], q[4], q[2] if typed else None)
        for row in c["rows"]:
            if row[0] != q[1]:
                continue
            truth = _truth(q, row)
            mp.delenv(W_FLAG, raising=False)
            v0 = ir.check(ir.identity(q[2], rel), [row[1]])
            mp.setenv(W_FLAG, "true")
            v1 = ir.check(ir.identity(q[2], rel), [row[1]])
            mp.delenv(W_FLAG, raising=False)
            out["base"][_key(v0 is None, truth)] += 1
            out["on"][_key(v1 is None, truth)] += 1
            if v1 is None and not truth:
                out["aw_on"][row[4]] += 1
                out["aw_left"].append((q[0], row[4]))
            if v0 is None and v1 is not None:
                out["reasons"][v1] += 1
                if truth:
                    out["right_refused"] += 1
    for k in ("base", "on"):
        out[k] = dict(sorted(out[k].items()))
    return out


# ---------------------------------------------------------------------------
# E1-E4d: the words
# ---------------------------------------------------------------------------


def test_e01_corpus_s_on_typed_and_untyped(monkeypatch):
    """E1: S ON, typed: W unset 42/65/40/22 -> W ON 42/7/98/22; untyped (the R ON default
    case) 42/27/78/22; no right picture newly refused in either run."""
    t = _corpus_run(monkeypatch, True, "queries", True)
    assert t["base"] == {"AR": 42, "AW": 65, "RR": 40, "RW": 22}, t["base"]
    assert t["on"] == {"AR": 42, "AW": 7, "RR": 98, "RW": 22}, t["on"]
    assert t["right_refused"] == 0
    u = _corpus_run(monkeypatch, True, "queries", False)
    assert u["on"] == {"AR": 42, "AW": 27, "RR": 78, "RW": 22}, u["on"]
    assert u["right_refused"] == 0


def test_e02_corpus_s_off_and_no_concentration_queries(monkeypatch):
    """E2: S OFF 39/59/46/25 -> 39/7/98/25; untyped 39/23/82/25; the no-concentration
    queries, S ON and OFF: 14/10/5/9 -> 14/1/14/9."""
    t = _corpus_run(monkeypatch, False, "queries", True)
    assert t["base"] == {"AR": 39, "AW": 59, "RR": 46, "RW": 25}, t["base"]
    assert t["on"] == {"AR": 39, "AW": 7, "RR": 98, "RW": 25}, t["on"]
    u = _corpus_run(monkeypatch, False, "queries", False)
    assert u["on"] == {"AR": 39, "AW": 23, "RR": 82, "RW": 25}, u["on"]
    for s_on in (True, False):
        n = _corpus_run(monkeypatch, s_on, "noconc_queries", True)
        assert n["base"] == {"AR": 14, "AW": 10, "RR": 5, "RW": 9}, (s_on, n["base"])
        assert n["on"] == {"AR": 14, "AW": 1, "RR": 14, "RW": 9}, (s_on, n["on"])
        assert n["right_refused"] == 0


def test_e03_corpus_per_class(monkeypatch):
    """E3: typed, S ON: body / conc / gift / refill / mini accepted-wrong -> 0; reasons
    form 37 / concentration 21; left 5 flankers and 2 twins; untyped: the 20 conc rows
    stay accepted, concentration 1; "YSL Libre Intense EDP 90ml" refused (free intense).
    """
    t = _corpus_run(monkeypatch, True, "queries", True)
    for cls in ("body", "conc", "gift", "refill", "mini"):
        assert t["aw_on"][cls] == 0, (cls, dict(t["aw_on"]))
    assert dict(t["reasons"]) == {"form": 37, "concentration": 21}, dict(t["reasons"])
    left = collections.Counter(cls for _q, cls in t["aw_left"])
    assert dict(left) == {"flanker": 5, "twin": 2}, dict(left)
    u = _corpus_run(monkeypatch, True, "queries", False)
    assert u["aw_on"]["conc"] == 20, dict(u["aw_on"])
    assert u["reasons"]["concentration"] == 1, dict(u["reasons"])
    _flags(monkeypatch, w=True)
    assert (
        _verdict("YSL Libre EDP", "YSL", "Libre", "YSL Libre Intense EDP 90ml")
        == "concentration"
    )


SAUV = ("Dior Sauvage EDP 100ml", "Dior", "Sauvage")


def test_e04_kept_and_refused(monkeypatch):
    """E4: KEPT rows; REFUSED form and concentration rows; the source text never read."""
    _flags(monkeypatch, w=True)
    kept = [
        SAUV + ("Dior Sauvage EDP 100ml Refillable Bottle",),
        SAUV + ("Dior Sauvage Eau de Parfum Spray for Men 100ml",),
        SAUV + ("Dior Sauvage Eau de Parfum - Parfum Homme 100ml",),
        SAUV + ("Dior Sauvage Eau de Parfum Vaporisateur 100 ml",),
        ("Burberry Body EDP", "Burberry", "Body", "Burberry Body Eau de Parfum 85ml"),
        (
            "Dior Homme Intense EDP",
            "Dior",
            "Homme Intense",
            "Dior Homme Intense Eau de Parfum 100ml",
        ),
        (
            "Dior Sauvage Elixir",
            "Dior",
            "Sauvage Elixir",
            "Dior Sauvage Elixir Parfum 60ml",
        ),
        (
            "Yves Saint Laurent Y Le Parfum",
            "Yves Saint Laurent",
            "Y Le Parfum",
            "Yves Saint Laurent Y Le Parfum 100ml",
        ),
        ("Chanel No 5 EDP", "Chanel", "No 5", "Chanel N 5 Eau de Parfum 100ml"),
        (
            "Creed Aventus Cologne",
            "Creed",
            "Aventus Cologne",
            "Creed Aventus Cologne 100ml",
        ),
        SAUV + ("Dior Sauvage EDP 100ml Gift",),
        SAUV + ("Dior Sauvage Eau de Parfum 100ml - Gifts for Men",),
    ]
    for p, b, line, title in kept:
        assert _verdict(p, b, line, title) is None, (p, title)
    form = [
        "Dior Sauvage Body Lotion 200ml",
        "Dior Sauvage EDP Set 100ml",
        "Dior Sauvage After Shave Balm 100ml",
        "Dior Sauvage Perfume Oil 30ml",
        "Dior Sauvage EDP Sample Vial 1ml",
        "Dior Sauvage Fragrance Mist 100ml",
        "Dior Sauvage EDP Refill 300ml",
    ]
    for title in form:
        assert _verdict(*SAUV, title) == "form", title
    assert (
        _verdict(
            "Dior Sauvage Parfum 100ml",
            "Dior",
            "Sauvage",
            "Dior Sauvage Eau de Parfum 100ml",
        )
        == "concentration"
    )
    # M6: a parfum after an Elixir phrase adds nothing (a typed Parfum refuses it).
    elixir = "Dior Sauvage Elixir Parfum 60ml"
    assert _verdict("Dior Sauvage Parfum", "Dior", "Sauvage", elixir) == "concentration"
    ok = "Dior Sauvage Eau de Parfum 100ml"
    assert _verdict(*SAUV, ok, texts=[ok, "The Body Shop"]) is None


def test_e04b_intense_after_a_phrase_is_its_label(monkeypatch):
    """E4b (I-9): intense after a concentration phrase is part of its label."""
    _need(_ir(), "_conc_scan")
    _flags(monkeypatch, w=True)
    jpg = "Jean Paul Gaultier"
    kept = [
        (
            jpg + " Ultra Male",
            jpg,
            "Ultra Male",
            jpg + " Ultra Male Eau de Toilette Intense 125ml",
        ),
        (
            jpg + " Le Male Le Parfum",
            jpg,
            "Le Male Le Parfum",
            jpg + " Le Male Le Parfum Eau de Parfum Intense 125ml",
        ),
        (
            jpg + " Scandal Pour Homme Le Parfum",
            jpg,
            "Scandal Pour Homme Le Parfum",
            jpg + " Scandal Pour Homme Le Parfum Eau de Toilette Intense 100ml",
        ),
        SAUV
        + (
            "Dior Sauvage Eau de Parfum 100ml - Long Lasting Intense Fragrance for Men",
        ),
        ("YSL Y", "YSL", "Y", "Yves Saint Laurent Y Eau de Parfum Intense 100ml"),
    ]
    for p, b, line, title in kept:
        assert _verdict(p, b, line, title) is None, (p, title)
    refused = [
        ("YSL Y EDP", "YSL", "Y", "Yves Saint Laurent Y Eau de Parfum Intense 100ml"),
        (
            "Kayali Vanilla 28 EDP",
            "Kayali",
            "Vanilla 28",
            "KAYALI Vanilla 28 Eau de Parfum Intense 50ml",
        ),
        (
            jpg + " Ultra Male EDT 125ml",
            jpg,
            "Ultra Male",
            jpg + " Ultra Male Eau de Toilette Intense 125ml",
        ),
    ]
    for p, b, line, title in refused:
        assert _verdict(p, b, line, title) == "concentration", (p, title)


def test_e04c_bare_gift_and_travel_never_refuse(monkeypatch):
    """E4c (I-10): bare gift / travel words keep; the joins and set words refuse."""
    _need(_ir(), "FORM_JOINS")
    _flags(monkeypatch, w=True)
    kept = [
        (
            "Lattafa Khamrah EDP 100ml",
            "Lattafa",
            "Khamrah",
            "Lattafa Khamrah Eau de Parfum 100ml Unisex - Perfect Gift for Him and Her",
        ),
        (
            "Paco Rabanne 1 Million EDT",
            "Paco Rabanne",
            "1 Million",
            "Paco Rabanne 1 Million Eau de Toilette Spray 100ml with Gift Bag",
        ),
        (
            "Hugo Boss Bottled EDT",
            "Hugo Boss",
            "Bottled",
            "Hugo Boss Boss Bottled Eau de Toilette 100ml Travel Exclusive",
        ),
    ]
    for p, b, line, title in kept:
        assert _verdict(p, b, line, title) is None, (p, title)
    for tail in (
        "Gift Set",
        "Gift Box",
        "Gift Pack",
        "Giftset",
        "Coffret",
        "Travel Size 10ml",
        "Travel Spray 10ml",
    ):
        title = "Dior Sauvage Eau de Parfum " + tail
        assert _verdict(*SAUV, title) == "form", title
    # OQ-A (stated): "Set of 1" counts under the listed words.
    assert (
        _verdict(
            "Versace Eros EDT",
            "Versace",
            "Eros",
            "Versace Eros Eau de Toilette Natural Spray 100ml for Men Set of 1",
        )
        == "form"
    )


def test_e04d_extrait_folds_and_brand_forms_exempt(monkeypatch):
    """E4d (I-13, I-14): Extrait == Parfum for 2(b); brand-form tokens never refuse."""
    _need(_ir(), "CONC_CLASS")
    _flags(monkeypatch, w=True)
    assert (
        _verdict(
            "Chanel No 5 Parfum", "Chanel", "No 5", "Chanel N 5 Extrait de Parfum 15ml"
        )
        is None
    )
    assert (
        _verdict("Chanel No 5 Extrait", "Chanel", "No 5", "Chanel No 5 Parfum 15ml")
        is None
    )
    assert (
        _verdict(
            "Japanese Cherry Blossom",
            "Bath & Body Works",
            "Japanese Cherry Blossom",
            "Bath and Body Works Japanese Cherry Blossom Eau de Parfum 75ml",
        )
        is None
    )


# ---------------------------------------------------------------------------
# E5: the typed concentration (I-8)
# ---------------------------------------------------------------------------


def _sauvage_images(first, second):
    titles = {
        "EDP": ("Dior Sauvage Eau de Parfum 100ml", URL_EDP, "edp"),
        "EDT": ("Dior Sauvage Eau de Toilette 100ml", URL_EDT, "edt"),
    }
    return [_item(titles[k][1], titles[k][0], titles[k][2]) for k in (first, second)]


def _resolved(variant, typed_name):
    p = {
        "brand": "Dior",
        "name": "Sauvage",
        "variant": variant,
        "category": "fragrances",
        "search_query": "Dior Sauvage " + variant,
        "_explicit": True,
    }
    if typed_name is not None:
        p["_typed_name"] = typed_name
    return p


def test_e05_typed_concentration_seam(monkeypatch, caplog):
    """E5 (I-8): query_conc from the typed text only; the resolver carrier; the ruled
    row (bare Dior Sauvage, R ON default EDT) keeps the EDP picture; a typed EDP refuses
    the EDT picture with W ON and not with W OFF."""
    caplog.set_level(logging.INFO)
    ir, scs = _ir(), _scs()
    ident = ir.identity(
        "Dior Sauvage", _rel("Dior", "Sauvage", "Dior Sauvage EDT 100ml")
    )
    assert getattr(ident, "query_conc", None) == frozenset({"EDT"})
    assert (
        getattr(
            ir.identity("Dior Sauvage EDT", _rel("Dior", "Sauvage EDT")),
            "query_conc",
            None,
        )
        == frozenset()
    )
    tit = _need(scs, "_typed_image_text")
    assert tit({"_typed_name": "Dior Sauvage EDP 100ml", "brand": "Dior"}, "x") == (
        "Dior Sauvage EDP 100ml"
    )
    assert (
        tit({"_explicit": True, "brand": "Dior", "name": "Sauvage"}, "Dior Sauvage EDT")
        == ""
    )
    assert (
        tit(
            {"_explicit": True, "brand": "", "name": "Dior Sauvage EDP"},
            "Dior Sauvage EDP",
        )
        == "Dior Sauvage EDP"
    )
    assert (
        tit({"brand": "Dior", "name": "Sauvage"}, "Dior Sauvage EDP")
        == "Dior Sauvage EDP"
    )

    def run(images, pinfo, w):
        _flags(monkeypatch, w=w)
        t = _T()
        _install_tiers(monkeypatch, t, images=images)
        return _fetch_run(monkeypatch, pinfo, price=_price())

    # THE RULED ROW: bare typed name, the resolver default EDT, [EDP first].
    r = run(_sauvage_images("EDP", "EDT"), _resolved("EDT", "Dior Sauvage"), True)
    assert r.get("image_url") == URL_EDP
    typed = _resolved("EDP 100ml", "Dior Sauvage EDP 100ml")
    on = run(_sauvage_images("EDT", "EDP"), typed, True)
    assert on.get("image_url") == URL_EDP, on.get("image_url")
    off = run(_sauvage_images("EDT", "EDP"), typed, None)
    assert off.get("image_url") == URL_EDT
    assert sorted(k for k in on if k.startswith("_")) == sorted(
        k for k in off if k.startswith("_")
    )
    for m in _msgs(caplog, "[IMG_RELEVANCE]") + _msgs(caplog, "IMG_SHOP"):
        assert "Sauvage" not in m and "EDP 100ml" not in m, m


class _Res:
    usage = None
    outcome = "resolved"


def _resolver_fakes(mp, rewrite_slot0=True):
    scs = _scs()
    pr = scs._product_resolver

    async def _resolve_pair(names, **_k):
        return _Res()

    def _apply(products, resolution):
        if rewrite_slot0:
            products[0].update({"brand": "Dior", "name": "Sauvage", "variant": "EDT"})
        return True

    mp.setattr(pr, "resolve_pair", _resolve_pair)
    mp.setattr(pr, "apply_resolution", _apply)


def test_e05b_carrier_only_with_w_on(monkeypatch):
    """E5 (I-8): _resolve_explicit_pair writes _typed_name on a REWRITTEN dict only,
    and only with G and W ON."""
    scs = _scs()
    from datetime import datetime

    def run():
        _resolver_fakes(monkeypatch)
        svc = scs.StructuredComparisonService()
        prods = [
            {
                "brand": "",
                "name": "Dior Sauvage EDP",
                "variant": None,
                "_explicit": True,
            },
            {"brand": "", "name": "Acme Nimbus", "variant": None, "_explicit": True},
        ]
        out = _run(svc._resolve_explicit_pair(prods, None, datetime.now()))
        return out, prods

    _flags(monkeypatch, w=True)
    out, prods = run()
    assert out == (None, True)
    assert prods[0].get("_typed_name") == "Dior Sauvage EDP", prods[0]
    assert "_typed_name" not in prods[1]
    _flags(monkeypatch, w=None)
    out, prods = run()
    assert "_typed_name" not in prods[0] and "_typed_name" not in prods[1]


# ---------------------------------------------------------------------------
# E6-E8: the cascade, the reader, the cache axis
# ---------------------------------------------------------------------------


def _gpu(mp, caplog, images, *, rel=None, payload=None, organic=None, gpt_url=None):
    t = _T()
    _install_tiers(mp, t, images=images, gpt_url=gpt_url)
    caplog.clear()
    url = _run(
        _img().get_product_image_url(
            "Dior Sauvage EDP 100ml",
            search_payload=payload,
            organic_results=organic,
            relevance=rel or _rel("Dior", "Sauvage", "Dior Sauvage EDP 100ml"),
        )
    )
    lines = _msgs(caplog, "[IMG_RELEVANCE]")
    assert len(lines) == 1, lines
    return url, REL_LINE.match(lines[0]).groups(), t


def test_e06_cascade_words(monkeypatch, caplog):
    """E6: W ON: [deodorant, gift set, right] -> right, accepted candidates=3; all wrong ->
    rejected reason=form; a KG EDT title under a typed EDP -> 1.5b miss, reason
    concentration; a body-only organic -> the llm pick is skipped."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, w=True)
    deo = _item(URL_DEO, "Dior Sauvage Deodorant Stick 75g", "deo")
    gset = _item(URL_SET, "Dior Sauvage Eau de Parfum Gift Set", "set")
    right = _item(URL_RIGHT, "Dior Sauvage Eau de Parfum 100ml", "right")
    url, g, _t = _gpu(monkeypatch, caplog, [deo, gset, right])
    assert url == URL_RIGHT and g[1:4] == ("serper_images", "accepted", "3"), (url, g)
    url, g, _t = _gpu(monkeypatch, caplog, [deo, gset])
    assert url is None and g[2] == "rejected" and g[4] == "form", (url, g)
    kg = {
        "knowledgeGraph": {
            "title": "Dior Sauvage Eau de Toilette",
            "imageUrl": URL_EDT,
            "type": "Perfume",
        }
    }
    url, g, _t = _gpu(monkeypatch, caplog, [], payload=kg)
    assert url is None and g[1] == "search_payload" and g[4] == "concentration", (
        url,
        g,
    )
    organic = [
        {"title": "Dior Sauvage Body Lotion 200ml", "link": "https://" + SHOP + "/b"}
    ]
    url, g, t = _gpu(monkeypatch, caplog, [], organic=organic, gpt_url=URL_RIGHT)
    assert t.gpt == [] and url is None, (t.gpt, url)


def test_e07_words_flag_read_once_after_a_pass(monkeypatch):
    """E7 (I-15): a passing check reads WORDS_FLAG_ENV exactly once; a brand refusal
    reads it 0 times."""
    ir = _ir()
    _flags(monkeypatch)
    real = os.getenv
    seen = []

    def rec(name, *a):
        seen.append(name)
        return real(name, *a)

    ident = ir.identity(*("Dior Sauvage EDP", _rel("Dior", "Sauvage")))
    monkeypatch.setattr(os, "getenv", rec)
    assert ir.check(ident, ["Dior Sauvage Eau de Parfum 100ml"]) is None
    assert seen.count(W_FLAG) == 1, seen
    del seen[:]
    assert ir.check(ident, ["Acme Nimbus Eau de Parfum"]) == "brand"
    assert seen.count(W_FLAG) == 0, seen


def _expected_name(rel, variant, axis):
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


def test_e08_cache_axis(monkeypatch):
    """E8 (I-19, OQ-B): the axis s1w0 / s1w1: / s1w1:EDP / s0w1:, all distinct."""
    img = _img()
    plain = _rel("Dior", "Sauvage")
    typed = _rel("Dior", "Sauvage", "Dior Sauvage EDP 100ml")
    _flags(monkeypatch)
    a = img.pick_cache_name(plain, "EDP 100ml")
    assert a == _expected_name(plain, "EDP 100ml", "s1w0")
    _flags(monkeypatch, w=True)
    b = img.pick_cache_name(plain, "EDP 100ml")
    c = img.pick_cache_name(typed, "EDP 100ml")
    assert b == _expected_name(plain, "EDP 100ml", "s1w1:")
    assert c == _expected_name(typed, "EDP 100ml", "s1w1:EDP")
    _flags(monkeypatch, s=None, w=True)
    d = img.pick_cache_name(plain, "EDP 100ml")
    assert d == _expected_name(plain, "EDP 100ml", "s0w1:")
    assert len({a, b, c, d}) == 4


# ---------------------------------------------------------------------------
# E9-E11, E14: A, the WooCommerce stamp
# ---------------------------------------------------------------------------


def _woo_prod(name, image=None, images=None, permalink="khamrah"):
    p = {
        "name": name,
        "prices": {"currency_code": "BHD", "currency_minor_unit": 3, "price": "20000"},
        "permalink": "https://" + SHOP + "/product/" + permalink,
        "is_in_stock": True,
    }
    if images is not None:
        p["images"] = images
    elif image is not None:
        p["images"] = [
            {"id": 7, "src": image, "thumbnail": image, "name": "k", "alt": ""}
        ]
    return p


def _woo_match(mp, prods, name="Lattafa Khamrah"):
    woo = _woo()
    seen = []
    real = woo.select_best

    def spy(cands, *a, **k):
        seen.append(cands)
        return real(cands, *a, **k)

    mp.setattr(woo, "select_best", spy)
    best = woo._match_woo_product(prods, name, "BHD", "fragrances")
    return best, (seen[0] if seen else [])


def test_e09_woo_stamp_on_the_winner(monkeypatch, caplog):
    """E9 (I-16): A ON, L OFF: the winner carries image_url, the other candidate none;
    ONE stamped page line per match call; through _fetch_product_data (cascade None)
    the payload image == the stamp."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, a=True)
    prods = [
        _woo_prod("Lattafa Khamrah Eau de Parfum", WOO_A, permalink="a"),
        _woo_prod("Lattafa Khamrah Eau de Parfum 100ml", WOO_B, permalink="b"),
    ]
    best, cands = _woo_match(monkeypatch, prods)
    assert best is not None and len(cands) == 2
    want = WOO_A if best["url"].endswith("/a") else WOO_B
    assert best.get("image_url") == want, best
    assert [c.get("image_url") for c in cands if c is not best] == [None]
    lines = _msgs(caplog, "IMG_SHOP page")
    assert len(lines) == 1 and PAGE_LINE.match(lines[0]), lines
    assert PAGE_LINE.match(lines[0]).groups()[:3] == ("stamped", "none", "list")
    t = _T()
    _install_tiers(monkeypatch, t, images=[])
    r = _fetch_run(monkeypatch, price=best)
    assert r.get("image_url") == want


def test_e10_stamp_through_the_late_chooser(monkeypatch, caplog):
    """E10: A ON, L ON: bind override with the stamp; a pending current price ->
    fallback with the Phase-1 stamp."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, a=True, late=True)
    best, _c = _woo_match(
        monkeypatch, [_woo_prod("Lattafa Khamrah Eau de Parfum", WOO_A)]
    )
    assert best is not None

    async def go(current, phase1):
        async def none():
            return None

        task = asyncio.ensure_future(none())
        await task
        entry = {
            "result": {"price": current},
            "task": task,
            "is_vision": False,
            "price_phase1": phase1,
            "state": {"open": True, "cached": False},
            "closed": False,
        }
        _scs().StructuredComparisonService()._late_image_choose(0, entry, 0)
        return entry["result"].get("image_url")

    assert _run(go(best, best)) == WOO_A
    pend = {"amount": None, "currency": "BHD", "pending": True, "estimated": False}
    assert _run(go(pend, best)) == WOO_A
    binds = [BIND.match(m).groups()[1] for m in _msgs(caplog, "IMG_LATE bind")]
    assert binds == ["override", "fallback"], binds


def _stamp(
    price, product, name="Dior Sauvage EDP", title="Dior Sauvage Eau de Parfum 100ml"
):
    _need(_img(), "stamp_shop_image")(price, "woo", product, None, name, title)
    return price


def test_e11_stamp_refusals(monkeypatch, caplog):
    """E11: no_image (http, denied host, non-raster); refused form / concentration (a
    free intense); an EDT title under an EDP name stamps (no 2(b) at A); G OFF skipped;
    IMAGE_PIPELINE_V2: the shop's own host passes the override, a third-party CDN not.
    """
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, a=True)
    one = lambda u: {"images": [{"src": u}]}  # noqa: E731
    for src in (
        "http://" + SHOP + "/a.jpg",
        "https://" + "fimgs" + ".net/a.jpg",
        "https://" + SHOP + "/a.html",
    ):
        p = _stamp({}, one(src))
        assert "image_url" not in p, src
    caplog.clear()
    assert "image_url" not in _stamp(
        {}, one(WOO_A), title="Dior Sauvage EDP Gift Set 100ml"
    )
    assert "image_url" not in _stamp(
        {}, one(WOO_A), title="Dior Sauvage Intense Eau de Parfum 100ml"
    )
    got = [PAGE_LINE.match(m).groups()[:2] for m in _msgs(caplog, "IMG_SHOP page")]
    assert got == [("refused", "form"), ("refused", "concentration")], got
    assert _stamp({}, one(WOO_A), title="Dior Sauvage Eau de Toilette 100ml") == {
        "image_url": WOO_A
    }
    _flags(monkeypatch, g=None, a=True)
    caplog.clear()
    assert _stamp({}, one(WOO_A)) == {}
    assert PAGE_LINE.match(_msgs(caplog, "IMG_SHOP page")[0]).groups()[0] == "skipped"
    _flags(monkeypatch, a=True)
    monkeypatch.setenv("ENABLE_IMAGE_PIPELINE_V2", "true")
    choice = _scs()._late_page_image_choice
    assert (
        choice(_price(image=WOO_A, url="https://" + SHOP + "/product/a"), False)
        == WOO_A
    )
    cdn = "https://" + "cdn.thirdparty.example.net" + "/a.jpg"
    assert (
        choice(_price(image=cdn, url="https://" + SHOP + "/product/a"), False) is None
    )


def test_e14_shapes_and_failures(monkeypatch, caplog):
    """E14: images "x" / 5 / [5] -> no_image (str / other / list), dict untouched; a raising
    first_https_raster -> error, dict untouched; a raising thumb -> image None, thumb
    error, no raise."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, a=True)
    for images, shape in (("x", "str"), (5, "other"), ([5], "list")):
        caplog.clear()
        assert _stamp({"amount": 1}, {"images": images}) == {"amount": 1}
        g = PAGE_LINE.match(_msgs(caplog, "IMG_SHOP page")[0]).groups()
        assert g[0] == "no_image" and g[2] == shape, g

    def boom(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr(_ir(), "first_https_raster", boom)
    caplog.clear()
    assert _stamp({"amount": 1}, {"images": [{"src": WOO_A}]}) == {"amount": 1}
    g = PAGE_LINE.match(_msgs(caplog, "IMG_SHOP page")[0]).groups()
    assert g == ("error", "none", "-", "-", "0"), g
    _flags(monkeypatch, b=True)
    monkeypatch.setattr(_img(), "shopping_thumbnail", boom, raising=False)
    t = _T()
    _install_tiers(monkeypatch, t, images=[])
    caplog.clear()
    r = _fetch_run(monkeypatch, shopping=[{"title": "x", "imageUrl": THUMB_RIGHT}])
    assert r.get("image_url") is None
    g = [THUMB_LINE.match(m).groups()[1] for m in _msgs(caplog, "IMG_SHOP thumb")]
    assert g == ["error"], g


# ---------------------------------------------------------------------------
# E12, E15-E18: B, the Shopping thumbnail
# ---------------------------------------------------------------------------


def _shop_items():
    return [
        {
            "title": "Acme Nimbus Noir Eau de Parfum Gift Set",
            "source": "Store A",
            "link": "https://" + SHOP + "/s",
            "imageUrl": THUMB_SET,
        },
        {
            "title": "Acme Nimbus Noir Eau de Parfum 100ml",
            "source": "Store B",
            "link": "https://" + SHOP + "/r",
            "imageUrl": THUMB_RIGHT,
        },
        {
            "title": "Acme Nimbus Noir Eau de Parfum",
            "source": "Store C",
            "link": "https://" + SHOP + "/n",
        },
    ]


def test_e12_thumb_last_resort(monkeypatch, caplog):
    """E12 (I-12): B ON, W UNSET: [gift-set thumb, right thumb, no-image] -> the right
    thumb, accepted candidates=2; keys with_url=2 https=2 gstatic=1; L OFF: the thumb only
    when the cascade gave None; L ON: bind shopping only after override, job, fallback.
    """
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, b=True)
    thumb = _need(_img(), "shopping_thumbnail")
    kw = _ir().relevance_kwargs("Acme", "Nimbus Noir", "fragrances", 0, False)
    assert thumb(_shop_items(), "Acme Nimbus Noir EDP 100ml", 0, **kw) == THUMB_RIGHT
    g = THUMB_LINE.match(_msgs(caplog, "IMG_SHOP thumb")[0]).groups()
    assert g == ("0", "accepted", "2", "none"), g
    k = KEYS_LINE.match(_msgs(caplog, "IMG_SHOP keys")[0]).groups()
    assert k[3:] == ("2", "2", "1"), k
    # M15: the thumb takes the guard first (a wrong-brand item is never a thumb).
    caplog.clear()
    other = [
        {"title": "Zephyra Velvet Dusk Eau de Parfum 100ml", "imageUrl": THUMB_RIGHT}
    ]
    assert thumb(other, "Acme Nimbus Noir EDP 100ml", 0, **kw) is None
    g = THUMB_LINE.match(_msgs(caplog, "IMG_SHOP thumb")[0]).groups()
    assert g == ("0", "rejected", "1", "brand"), g
    t = _T()
    _install_tiers(monkeypatch, t, images=[])
    r = _fetch_run(monkeypatch, shopping=_shop_items())
    assert r.get("image_url") == THUMB_RIGHT
    t = _T()
    _install_tiers(
        monkeypatch, t, images=[_item(URL_S0, "Acme Nimbus Noir Eau de Parfum")]
    )
    r = _fetch_run(monkeypatch, shopping=_shop_items())
    assert r.get("image_url") == URL_S0
    r = _fetch_run(
        monkeypatch,
        price=_price(image="https://" + SHOP + "/i/page.jpg"),
        shopping=_shop_items(),
    )
    assert r.get("image_url") == "https://" + SHOP + "/i/page.jpg"

    async def go(job_url, phase1):
        async def job():
            return job_url

        task = asyncio.ensure_future(job())
        await task
        entry = {
            "result": {"price": None},
            "task": task,
            "is_vision": False,
            "price_phase1": phase1,
            "state": {"open": True, "cached": False},
            "closed": False,
            "shop_thumb": THUMB_RIGHT,
        }
        _scs().StructuredComparisonService()._late_image_choose(0, entry, 0)
        return entry["result"].get("image_url")

    caplog.clear()
    assert _run(go(None, None)) == THUMB_RIGHT
    assert _run(go(URL_S0, None)) == URL_S0
    assert _run(go(None, _price(image=WOO_A))) == WOO_A
    binds = [BIND.match(m).groups()[1] for m in _msgs(caplog, "IMG_LATE bind")]
    assert binds == ["shopping", "attached", "fallback"], binds


def test_e15_camera_product(monkeypatch, caplog):
    """E15: a camera product: no relevance, thumb skipped; the stamp still works."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, w=True, a=True, b=True)
    thumb = _need(_img(), "shopping_thumbnail")
    assert (
        _ir().relevance_kwargs("Acme", "Nimbus", "fragrances", 0, True, typed="x") == {}
    )
    assert thumb(_shop_items(), "Acme Nimbus Noir", 0) is None
    assert THUMB_LINE.match(_msgs(caplog, "IMG_SHOP thumb")[0]).groups()[1] == "skipped"
    assert _msgs(caplog, "[IMG_RELEVANCE]") == []
    assert _stamp(
        {},
        {"images": [{"src": WOO_A}]},
        "Acme Nimbus Noir",
        "Acme Nimbus Noir Eau de Parfum",
    ) == {"image_url": WOO_A}


def test_e16_kb_card_skips_the_thumb(monkeypatch):
    """E16 (I-15): B ON, a KB card image: shopping_thumbnail 0 calls; a KB miss: 1."""
    _flags(monkeypatch, b=True)
    calls = []

    def rec(*a, **k):
        calls.append(1)
        return None

    monkeypatch.setattr(_img(), "shopping_thumbnail", rec, raising=False)
    t = _T()
    _install_tiers(monkeypatch, t, images=[])
    card = "https://" + "card.example.com" + "/img/c.jpg"
    r = _fetch_run(monkeypatch, kb_card=card, shopping=_shop_items())
    assert r.get("image_url") == card and calls == []
    _fetch_run(monkeypatch, shopping=_shop_items())
    assert calls == [1], calls


def test_e17_line_grammar(monkeypatch, caplog):
    """E17: every IMG_SHOP line fullmatches its grammar; none holds a URL, a title word
    or the query."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, a=True, b=True)
    _woo_match(monkeypatch, [_woo_prod("Lattafa Khamrah Eau de Parfum", WOO_A)])
    _stamp({}, {"images": {"src": WOO_A, "weird key!": 1}})
    _stamp({}, {"images": None})
    kw = _ir().relevance_kwargs("Acme", "Nimbus Noir", "fragrances", 1, False)
    _need(_img(), "shopping_thumbnail")(_shop_items(), "Acme Nimbus Noir", 1, **kw)
    lines = _msgs(caplog, "IMG_SHOP")
    assert len(lines) >= 5, lines
    for m in lines:
        assert PAGE_LINE.match(m) or KEYS_LINE.match(m) or THUMB_LINE.match(m), m
        low = m.lower()
        for word in ("://", "http:", "khamrah", "lattafa", "nimbus", "acme", "dior"):
            assert word not in low, m


def test_e18_late_thumb_bound_never_stored(monkeypatch, caplog):
    """E18 (I-15): L ON + a B pick: the thumb IS bound (shopping); set_cached 0 calls; no
    cache stored line."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, b=True, late=True)
    t = _T()
    _install_tiers(monkeypatch, t, images=[], gpt_url=None)
    r = _fetch_run(monkeypatch, shopping=_shop_items(), bind=True)
    assert r.get("image_url") == THUMB_RIGHT
    binds = [BIND.match(m).groups()[1] for m in _msgs(caplog, "IMG_LATE bind")]
    assert binds == ["shopping"], binds
    assert t.set == []
    assert not [m for m in _msgs(caplog, "IMG_LATE cache") if "outcome=stored" in m]


# ---------------------------------------------------------------------------
# E19: the guard version (I-2)
# ---------------------------------------------------------------------------

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
    ir = _ir()
    objs = []
    for dotted in GUARD_SET:
        obj = ir
        for part in dotted.split("."):
            obj = _need(obj, part)
        objs.append(obj)
    parts = [inspect.getsource(o) for o in objs]
    for name in GUARD_SORTED_TABLES:
        parts.append(name + "=" + repr(sorted(_need(ir, name))))
    for name in GUARD_PATTERNS:
        parts.append(name + "=" + _need(ir, name).pattern)
    parts.append("CONC_PHRASES=" + repr(_need(ir, "CONC_PHRASES")))
    parts.append(
        "EXTRA_ALIAS_GROUPS=" + repr(sorted(sorted(g) for g in ir.EXTRA_ALIAS_GROUPS))
    )
    parts.append("CONC_CLASS=" + repr(sorted(_need(ir, "CONC_CLASS").items())))
    parts.append("TEXT_MAX_CHARS=" + repr(ir.TEXT_MAX_CHARS))
    return "\n".join(parts)


def _guard_digest():
    return hashlib.sha256(_guard_text().encode("utf-8")).hexdigest()[:8]


def test_e19_guard_version_bumped(monkeypatch):
    """E19 (I-2): PICK_GUARD_RULES != b39b9d79, == the widened GUARD_SET digest; the
    prefix carries it."""
    img = _img()
    assert img.PICK_GUARD_RULES != "b39b9d79"
    assert _guard_digest() == img.PICK_GUARD_RULES
    assert img.PICK_CACHE_PREFIX == "imgpick:v1:" + img.PICK_GUARD_RULES + ":"
    assert "{" not in _guard_text().split("FORM_WORDS=")[1].split("\n")[0][:1]


# ---------------------------------------------------------------------------
# P rows (green at base)
# ---------------------------------------------------------------------------

_MS = re.compile(r"(ms|wait_ms|tier_ms|total_ms)=\d+")


def _strip_ms(lines):
    return [_MS.sub(lambda m: m.group(1) + "=N", ln) for ln in lines]


def _p1_observe(mp, caplog, off_value):
    """Observations of the OFF state (the three flags unset or "false", knobs set)."""
    for name in UNIT_FLAGS:
        if off_value is None:
            mp.delenv(name, raising=False)
        else:
            mp.setenv(name, off_value)
    for k, v in SYNTH_KNOBS.items():
        mp.setenv(k, v)
    obs = {}
    ir = _ir()
    c = _corpus()
    for s_on in (True, False):
        _flags(mp, s=s_on)
        row = []
        for q in c["queries"] + c["noconc_queries"]:
            ident = ir.identity(q[2], _rel(q[3], q[4]))
            for r in c["rows"]:
                if r[0] == q[1]:
                    row.append(ir.check(ident, [r[1]]) or "ok")
        obs["corpus_s%d" % s_on] = row
    _flags(mp)
    deo = _item(URL_DEO, "Dior Sauvage Deodorant Stick 75g", "deo")
    right = _item(URL_RIGHT, "Dior Sauvage Eau de Parfum 100ml", "right")
    for name, imgs in (
        ("deo_right", [deo, right]),
        ("edt_edp", _sauvage_images("EDT", "EDP")),
    ):
        t = _T()
        _install_tiers(mp, t, images=imgs)
        caplog.clear()
        url = _run(
            _img().get_product_image_url(
                "Dior Sauvage EDP 100ml", relevance=_rel("Dior", "Sauvage")
            )
        )
        obs["gpu_" + name] = [url, _strip_ms(_msgs(caplog, "[IMG_"))]
    obs["relkw"] = [
        _ir().relevance_kwargs("Dior", "Sauvage", "fragrances", 0, False),
        _ir().relevance_kwargs("Dior", "Sauvage", "fragrances", 1, True),
    ]
    prods = [
        _woo_prod("Lattafa Khamrah Eau de Parfum", WOO_A, permalink="a"),
        _woo_prod("Lattafa Khamrah Eau de Parfum 100ml", WOO_B, permalink="b"),
    ]
    obs["woo"] = _woo()._match_woo_product(
        prods, "Lattafa Khamrah", "BHD", "fragrances"
    )
    for late in (False, True):
        _flags(mp, late=late)
        t = _T()
        _install_tiers(mp, t, images=_sauvage_images("EDT", "EDP"))
        caplog.clear()
        r = _fetch_run(
            mp, _resolved("EDP 100ml", None), shopping=_shop_items(), bind=late
        )
        lines = [m for m in _msgs(caplog, "") if m.startswith(("[IMG_", "IMG_"))]
        obs["fetch_l%d" % late] = [r.get("image_url"), sorted(r), _strip_ms(lines)]
    return json.loads(json.dumps(obs))


@pytest.mark.parametrize("off_value", [None, "false"])
def test_p1_flag_off_golden(monkeypatch, caplog, off_value):
    """P1 (B1): W A B unset and "false", knobs set: corpus verdicts, cascade results and
    lines, relevance dicts, the Woo dict and two fetches (L OFF / ON) == the golden; no
    IMG_SHOP line."""
    caplog.set_level(logging.INFO)
    obs = _p1_observe(monkeypatch, caplog, off_value)
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert set(obs) == set(golden)
    for k in sorted(golden):
        assert obs[k] == golden[k], k
    assert not [r for r in caplog.records if r.getMessage().startswith("IMG_SHOP")]


def test_p2_words_off_is_the_base_verdict(monkeypatch):
    """P2: W OFF: check on the corpus == the I-8-free base table (recorded in E1's
    W-unset half); the late cascade source sha unchanged (I2a P3 stands)."""
    _flags(monkeypatch, w="false")
    ir = _ir()
    c = _corpus()
    for q in c["queries"][:3]:
        ident = ir.identity(q[2], _rel(q[3], q[4], q[2]))
        for r in c["rows"]:
            if r[0] == q[1]:
                base = getattr(ir, "_check_base", None)
                if base is not None:
                    assert ir.check(ident, [r[1]]) == base(ident, [r[1]])
    src = inspect.getsource(_img().get_product_image_url_late)
    assert hashlib.sha256(src.encode("utf-8")).hexdigest() == P2_LATE_SHA


P2_LATE_SHA = "17b90f4f3031001e532e26f11b336e3049901f41740a19cb0354582953deb4f9"


def test_p3_guard_off_reads_no_unit_flag(monkeypatch):
    """P3: G OFF: a fetch reads WORDS_FLAG_ENV 0 times; relevance_kwargs {}."""
    _flags(monkeypatch, g=None, w=True)
    assert _ir().relevance_kwargs("Dior", "Sauvage", "fragrances", 0, False) == {}
    real = os.getenv
    seen = []

    def rec(name, *a):
        seen.append(name)
        return real(name, *a)

    t = _T()
    _install_tiers(monkeypatch, t, images=_sauvage_images("EDT", "EDP"))
    monkeypatch.setattr(os, "getenv", rec)
    _fetch_run(monkeypatch, _resolved("EDP 100ml", "Dior Sauvage EDP 100ml"))
    assert seen.count(W_FLAG) == 0


def test_p4_relevance_dict_and_identity_build(monkeypatch):
    """P4: relevance_kwargs with W OFF == the 4-key base dict (a typed text ignored);
    Identity with the base fields builds."""
    _flags(monkeypatch)
    ir = _ir()
    want = {
        "relevance": {
            "brand": "Dior",
            "line": "Sauvage",
            "category": "fragrances",
            "slot": 0,
        }
    }
    assert ir.relevance_kwargs("Dior", "Sauvage", "fragrances", 0, False) == want
    try:
        got = ir.relevance_kwargs("Dior", "Sauvage", "fragrances", 0, False, typed="x")
    except TypeError:
        got = want
    assert got == want
    ident = ir.Identity(
        brand_empty=False,
        brand_forms=frozenset({"dior"}),
        brand_joined="dior",
        name_tokens=frozenset({"sauvage"}),
        fragrance=True,
        needs_fragrance_word=True,
    )
    assert ident.brand_joined == "dior"


def test_p5_shop_flag_unset_is_the_base_adapter(monkeypatch):
    """P5 (I-11): A UNSET, images "x" and [{"src": 5}] -> the base dict, no raise, no
    stamp call; the A reader read once per match call with a winner."""
    _flags(monkeypatch)
    calls = []
    monkeypatch.setattr(
        _img(), "stamp_shop_image", lambda *a, **k: calls.append(a), raising=False
    )
    for images in ("x", [{"src": 5}]):
        best, _c = _woo_match(
            monkeypatch, [_woo_prod("Lattafa Khamrah Eau de Parfum", images=images)]
        )
        assert best is not None and "image_url" not in best
    assert calls == []
    real = os.getenv
    seen = []

    def rec(name, *a):
        seen.append(name)
        return real(name, *a)

    monkeypatch.setattr(os, "getenv", rec)
    _woo()._match_woo_product(
        [_woo_prod("Lattafa Khamrah Eau de Parfum", WOO_A)],
        "Lattafa Khamrah",
        "BHD",
        "fragrances",
    )
    _woo()._match_woo_product(
        [_woo_prod("Acme Other Thing", WOO_A)], "Lattafa Khamrah", "BHD", "fragrances"
    )
    assert seen.count(A_FLAG) in (0, 1)
