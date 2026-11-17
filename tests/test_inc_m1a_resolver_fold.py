"""INC-M1a RESOLVER FOLD (rides ENABLE_PRODUCT_RESOLVER; no new flag): RED and PIN rows.

Arabic typed names fold to their Latin identity inside the resolver hook (the one home for the
Arabic brand and line spellings is data/fragrance_lines.json, written as JSON escapes), the
Arabic concentration phrases of data/fragrance_lexicon.json are read by the resolver's typed
concentration, the seed rows (YSL Y, Rasasi Hawas, the flankers, Libre += EDT, the optional
single_concentration field) and a typed flanker word matched before the generic / qualifier
drop. Spec INC_M1_SPEC.md section 1 (1.3 the rows, 1.7 the mutants) as amended by
RULINGS_INC_M1 (M1R-1..M1R-6); the facts report INC_M1_FACTS.md stands in for the review
(Q4 LATIN column = the frozen price golden; Q5 = the picture parity). Base 7f672cfe.

RED = fails at the base on an AssertionError only. PIN = green at the base; every seam PIN
runs with the FULL configuration (ENABLE_ANTHROPIC_TEXT and ENABLE_OPENAI_PRE_V3 ON, consent
3, both resolver knobs, a synthetic Anthropic key, the fake SDK and OpenAI client, the picture
guard flags ON) plus the call recorders of tests/test_inc_r1_seam.py (route sites, getenv
names, lines-file opens), so a not-gated mutant is killable (ruling B1). The flag-OFF digests
were RECORDED AT THE BASE by the RED author.

Hermetic: every network leaf faked through the FY25 harness (tests/test_s75_fanout_identity.py)
and the INC-R1 seam fakes; no .env, no real credential (the synthetic key is built at run
time). Pure ASCII, LF: every Arabic string is built from chr() code points at run time (M1R-6).
"""

from __future__ import annotations

import ast
import asyncio
import copy
import dataclasses
import json
import os
import pathlib
import sys
from datetime import datetime

import pytest

import app.main  # noqa: F401  (FIRST: the dotenv guard)
from app.middleware import error_handler as eh
from app.services import api_budget_service as abs_
from app.services import category_gate as cg
from app.services import image_relevance as ir
from app.services import llm_router as lr
from app.services import openai_service as osvc
from app.services import price_service as ps
from app.services import product_resolver as pr
from app.services import url_extraction_service as ues
import app.services.structured_comparison_service as scs
from app.utils import request_context as rc
from tests import test_inc_r1_seam as r1s
from tests import test_s75_fanout_identity as fy

ROOT = pathlib.Path(__file__).resolve().parents[1]
LINES_FILE = ROOT / "data" / "fragrance_lines.json"
LEXICON_FILE = ROOT / "data" / "fragrance_lexicon.json"
FLAG = "ENABLE_PRODUCT_RESOLVER"
GUARD = "ENABLE_IMAGE_RELEVANCE_GUARD"
WORDS = "ENABLE_IMAGE_GUARD_WORDS"
SHORT = "ENABLE_IMAGE_GUARD_SHORT_LINE"
EXTRA_CLEAR = (
    GUARD,
    WORDS,
    SHORT,
    "ENABLE_IMAGE_LATE_BIND",
    "ENABLE_SHOP_PAGE_IMAGE",
    "ENABLE_LISTING_MATCH_GUARD",
    "ENABLE_VARIANT_DESCRIPTOR_AXES",
    "ENABLE_DATA_GUARDS_V2",
    "ENABLE_EXACT_PRICE_GATE",
    "ENABLE_PRICE_NOT_LOST",
    "ENABLE_MATCH_FOLD",
    "ENABLE_URL_LINK_RESULT",
    "ENABLE_GENUINE_PRICE_PRIORITY",
    "ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX",
)
CAT = "fragrances"


# ---------------------------------------------------------------- Arabic, built at run time


def _cp(*points):
    return "".join(chr(p) for p in points)


DIOR = _cp(0x062F, 0x064A, 0x0648, 0x0631)
SAUVAGE = _cp(0x0633, 0x0648, 0x0641, 0x0627, 0x062C)
BLEU = _cp(0x0628, 0x0644, 0x0648)
DE_WAW = _cp(0x062F, 0x0648)
DE_YA = _cp(0x062F, 0x064A)
CHANEL = _cp(0x0634, 0x0627, 0x0646, 0x064A, 0x0644)
RASASI = _cp(0x0627, 0x0644, 0x0631, 0x0635, 0x0627, 0x0635, 0x064A)
EAU_HAMZA = _cp(0x0623, 0x0648)
EAU = _cp(0x0627, 0x0648)
PARFAN = _cp(0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646)
TOILET = _cp(0x062A, 0x0648, 0x0627, 0x0644, 0x064A, 0x062A)
ML = _cp(0x0645, 0x0644)
BLEU_WAW = " ".join((BLEU, DE_WAW, CHANEL))
BLEU_YA = " ".join((BLEU, DE_YA, CHANEL))
# the three lexicon concentration phrases (data/fragrance_lexicon.json, the WAW particle)
LEX_EDP = " ".join((EAU_HAMZA, DE_WAW, PARFAN))
LEX_EDT = " ".join((EAU_HAMZA, DE_WAW, TOILET))
LEX_PARFUM = PARFAN

AR_A = DIOR + " " + SAUVAGE + " EDP"
AR_B = BLEU_WAW + " EDP"
AR_B_YA = BLEU_YA + " EDP"
LAT_A = "Dior Sauvage EDP"
LAT_B = "Bleu de Chanel EDP"
TWIN = {AR_A: LAT_A, AR_B: LAT_B, AR_B_YA: LAT_B, LAT_A: LAT_A, LAT_B: LAT_B}
KEYS5 = ("brand", "name", "variant", "search_query", "category")

# ---------------------------------------------------------------- the R4 corpus rows of the two lines
AMOUNT = {"sauvage": 55.0, "bleu": 60.0}


def _ar_titles():
    atr = _cp(0x0639, 0x0637, 0x0631)
    min_ = _cp(0x0645, 0x0646)
    men = _cp(0x0644, 0x0644, 0x0631, 0x062C, 0x0627, 0x0644)
    elixir = _cp(0x0625, 0x0644, 0x0643, 0x0633, 0x064A, 0x0631)
    tester = _cp(0x062A, 0x0633, 0x062A, 0x0631)
    taqm = _cp(0x0637, 0x0642, 0x0645)
    hadaya = _cp(0x0647, 0x062F, 0x0627, 0x064A, 0x0627)
    ma = _cp(0x0645, 0x0639)
    gel = _cp(0x062C, 0x0644)
    bath = _cp(0x0627, 0x0633, 0x062A, 0x062D, 0x0645, 0x0627, 0x0645)
    muzil = _cp(0x0645, 0x0632, 0x064A, 0x0644)
    araq = _cp(0x0639, 0x0631, 0x0642)
    stick = _cp(0x0633, 0x062A, 0x064A, 0x0643)
    edp = " ".join((EAU, DE_WAW, PARFAN))
    j = " ".join
    sauvage = [
        j((DIOR, SAUVAGE, edp, "100", ML)),
        j((atr, SAUVAGE, min_, DIOR, men, EAU, DE_YA, TOILET, "100", ML)),
        j((DIOR, SAUVAGE, elixir, "60", ML)),
        j((tester, DIOR, SAUVAGE, edp, "100", ML)),
        j((taqm, hadaya, DIOR, SAUVAGE, edp, "100", ML, ma, gel, bath)),
    ]
    bleu = [
        j((BLEU_YA, edp, "100", ML)),
        j((CHANEL, BLEU_YA, PARFAN, "150", ML)),
        j((muzil, araq, BLEU_YA, stick, "75", ML)),
        j((tester, BLEU_YA, edp, "100", ML)),
    ]
    return sauvage, bleu


_AR_SAUVAGE, _AR_BLEU = _ar_titles()
CORPUS = {
    "sauvage": [
        "DIOR Sauvage Eau de Parfum Spray",
        "Dior Sauvage Parfum",
        "Sauvage EDP 100ml",
        "SAUVAGE 100ML",
        "Sauvage 3.4 oz",
        "Dior Sauvage Edt M 100Ml",
        "Dior Sauvage Eau de Parfum 100 ml for Men",
        "Christian Dior Sauvage EDP 60ml",
        "Dior Sauvage Eau de Parfum 200ml",
        "Dior Sauvage Elixir 100ml",
        "Dior Sauvage Eau de Parfum Refill 300ml",
        "Dior Sauvage EDP 100ml Tester (No Box)",
        "Dior Sauvage EDP 100ml + 10ml Travel Spray Gift Set",
        "Dior Sauvage Eau de Parfum 10ml Travel Spray",
        "Dior Sauvage Deodorant Stick 75g",
        "Dior Sauvage Shower Gel 250ml",
        "Inspired by Sauvage EDP 100ml Men Perfume",
    ]
    + _AR_SAUVAGE,
    "bleu": [
        "Chanel Bleu de Chanel Eau de Parfum 100ml",
        "BLEU DE CHANEL EAU DE PARFUM POUR HOMME SPRAY 3.4 FL OZ",
        "Bleu de Chanel EDP 50ml",
        "Bleu De Chanel Eau De Parfum 150ml",
        "Chanel Bleu de Chanel Eau de Toilette 100ml",
        "Chanel Bleu de Chanel Parfum 100ml",
        "Bleu de Chanel Eau de Parfum Twist and Spray 3 x 20ml Refill",
        "Chanel Bleu de Chanel EDP Tester 100ml",
        "Bleu de Chanel Deodorant Stick 75ml",
        "Bleu de Chanel After Shave Lotion 100ml",
        "Bleu de Chanel EDP 100ml Gift Set with Shower Gel",
        "Blue Chanel Inspired Perfume EDP 100ml",
    ]
    + _AR_BLEU,
}
LINE_OF = {AR_A: "sauvage", LAT_A: "sauvage", AR_B: "bleu", AR_B_YA: "bleu", LAT_B: "bleu"}
# facts Q4: the LATIN _selection_match accept sets (the frozen golden)
SEL_GOLDEN = {
    "sauvage": [
        "DIOR Sauvage Eau de Parfum Spray",
        "Dior Sauvage Eau de Parfum 100 ml for Men",
        "Dior Sauvage Eau de Parfum 200ml",
        "Dior Sauvage Eau de Parfum 10ml Travel Spray",
    ],
    "bleu": [
        "Chanel Bleu de Chanel Eau de Parfum 100ml",
        "BLEU DE CHANEL EAU DE PARFUM POUR HOMME SPRAY 3.4 FL OZ",
        "Bleu de Chanel EDP 50ml",
        "Bleu De Chanel Eau De Parfum 150ml",
    ],
}
# facts Q4: the LATIN is_price_showable accept sets (15 and 13 titles; measured at the base)
SHOW_GOLDEN = {
    "sauvage": [
        "DIOR Sauvage Eau de Parfum Spray",
        "Sauvage EDP 100ml",
        "SAUVAGE 100ML",
        "Sauvage 3.4 oz",
        "Dior Sauvage Eau de Parfum 100 ml for Men",
        "Christian Dior Sauvage EDP 60ml",
        "Dior Sauvage Eau de Parfum 200ml",
        "Dior Sauvage Elixir 100ml",
        "Dior Sauvage Deodorant Stick 75g",
        "Inspired by Sauvage EDP 100ml Men Perfume",
    ]
    + _AR_SAUVAGE,
    "bleu": [
        "Chanel Bleu de Chanel Eau de Parfum 100ml",
        "BLEU DE CHANEL EAU DE PARFUM POUR HOMME SPRAY 3.4 FL OZ",
        "Bleu de Chanel EDP 50ml",
        "Bleu De Chanel Eau De Parfum 150ml",
        "Bleu de Chanel Eau de Parfum Twist and Spray 3 x 20ml Refill",
        "Bleu de Chanel Deodorant Stick 75ml",
        "Bleu de Chanel After Shave Lotion 100ml",
        "Bleu de Chanel EDP 100ml Gift Set with Shower Gel",
        "Blue Chanel Inspired Perfume EDP 100ml",
    ]
    + _AR_BLEU,
}

# ---------------------------------------------------------------- the base data file (12 lines)
BASE_LINES = [
    {"house": "Dior", "house_aliases": ["dior", "christian dior"], "line": "Sauvage", "aliases": ["sauvage"], "concentrations": ["EDT", "EDP", "Parfum", "Elixir"], "base": "EDT", "flankers": []},
    {"house": "Chanel", "house_aliases": ["chanel"], "line": "Bleu de Chanel", "aliases": ["bleu de chanel"], "concentrations": ["EDT", "EDP", "Parfum"], "base": "EDT", "flankers": []},
    {"house": "Creed", "house_aliases": ["creed"], "line": "Aventus", "aliases": ["aventus"], "concentrations": ["EDP"], "base": "EDP", "flankers": []},
    {"house": "Parfums de Marly", "house_aliases": ["parfums de marly"], "line": "Layton", "aliases": ["layton"], "concentrations": ["EDP"], "base": "EDP", "flankers": []},
    {"house": "Lancome", "house_aliases": ["lancome"], "line": "La Vie Est Belle", "aliases": ["la vie est belle"], "concentrations": ["EDP"], "base": "EDP", "flankers": []},
    {"house": "Yves Saint Laurent", "house_aliases": ["yves saint laurent", "ysl", "saint laurent"], "line": "Libre", "aliases": ["libre"], "concentrations": ["EDP"], "base": "EDP", "flankers": []},
    {"house": "Giorgio Armani", "house_aliases": ["giorgio armani", "armani"], "line": "Acqua di Gio Profumo", "aliases": ["acqua di gio profumo"], "concentrations": [], "base": None, "flankers": []},
    {"house": "Versace", "house_aliases": ["versace"], "line": "Eros", "aliases": ["eros"], "concentrations": ["EDT", "EDP"], "base": "EDT", "flankers": []},
    {"house": "Maison Francis Kurkdjian", "house_aliases": ["maison francis kurkdjian", "mfk"], "line": "Baccarat Rouge 540", "aliases": ["baccarat rouge 540"], "concentrations": ["EDP", "Extrait"], "base": "EDP", "flankers": []},
    {"house": "Lattafa", "house_aliases": ["lattafa"], "line": "Khamrah", "aliases": ["khamrah"], "concentrations": ["EDP"], "base": "EDP", "flankers": []},
    {"house": "Emporio Armani", "house_aliases": ["emporio armani", "armani", "emporio"], "line": "Stronger With You", "aliases": ["stronger with you"], "concentrations": ["EDT"], "base": "EDT", "flankers": ["Intensely", "Absolutely", "Leather", "Parfum", "Oud"]},
    {"house": "Bvlgari", "house_aliases": ["bvlgari", "bulgari"], "line": "Tygar", "aliases": ["tygar", "le gemme tygar"], "concentrations": ["EDP"], "base": "EDP", "flankers": []},
]
SINGLE_CONCENTRATION_LINES = {"Aventus", "Layton", "Khamrah", "Hawas"}


def _expected_existing():
    """The 12 base lines with exactly the spec 1.2 edits (M1R-4), lists as sets."""
    out = {}
    for item in copy.deepcopy(BASE_LINES):
        if item["line"] == "Sauvage":
            item["house_aliases"].append(DIOR)
            item["aliases"].append(SAUVAGE)
        elif item["line"] == "Bleu de Chanel":
            item["house_aliases"].append(CHANEL)
            item["aliases"].extend([BLEU_WAW, BLEU_YA])
        elif item["line"] == "Libre":
            item["concentrations"] = ["EDT", "EDP"]
            item["flankers"] = ["Intense", "Le Parfum"]
        elif item["line"] == "Khamrah":
            item["flankers"] = ["Qahwa", "Dukhan"]
        elif item["line"] == "Aventus":
            item["flankers"] = ["for Her", "Absolu", "Cologne"]
        if item["line"] in SINGLE_CONCENTRATION_LINES:
            item["single_concentration"] = True
        out[(item["house"], item["line"])] = _setify(item)
    return out


def _setify(item):
    return {
        k: (sorted(v) if isinstance(v, list) else v)
        for k, v in item.items()
        if not (k == "single_concentration" and v is False)
    }


# ---------------------------------------------------------------- fixtures


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in tuple(r1s.CLEAR) + EXTRA_CLEAR:
        monkeypatch.delenv(name, raising=False)
    for name in list(os.environ):
        if name.startswith("ANTHROPIC_") or name.startswith("PRODUCT_RESOLVER_"):
            monkeypatch.delenv(name, raising=False)
    r1s.ANTH.__init__()
    del r1s.OAI_CALLS[:]
    r1s.CONSENT["value"] = None
    scs._DEBUG_STAGE_TIMINGS = None
    monkeypatch.setitem(sys.modules, "anthropic", r1s._fake_anthropic_module())
    monkeypatch.setattr(
        lr, "_anthropic_client_factory", lambda **kw: r1s._FakeAnthropicClient(**kw)
    )
    monkeypatch.setattr(osvc, "get_client", lambda: r1s._OaiClient())
    monkeypatch.setattr(
        rc, "consent_version", lambda: r1s.CONSENT["value"], raising=False
    )
    monkeypatch.setattr(
        rc,
        "header_state",
        lambda name: "ok" if isinstance(r1s.CONSENT["value"], int) else "absent",
        raising=False,
    )
    for name in ("_redis_get", "_redis_set", "_redis_incr", "_redis_expire"):
        monkeypatch.setattr(abs_, name, lambda *a, **k: None, raising=False)
    monkeypatch.setattr(abs_, "is_circuit_closed", lambda *a, **k: True, raising=False)
    lr._reset_router_state()
    pr._reset_resolver_state()
    cg._reset_lexicon_cache()
    try:
        yield
    finally:
        scs._DEBUG_STAGE_TIMINGS = None
        lr._reset_router_state()
        pr._reset_resolver_state()
        cg._reset_lexicon_cache()


def _unit_flags(monkeypatch):
    """The unit rows: the resolver flag ON, the model arm OFF (no TEXT), no consent."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.delenv("ENABLE_ANTHROPIC_TEXT", raising=False)


def _image_flags(monkeypatch, *, words):
    monkeypatch.setenv(GUARD, "true")
    monkeypatch.setenv(SHORT, "true")
    if words:
        monkeypatch.setenv(WORDS, "true")
    else:
        monkeypatch.delenv(WORDS, raising=False)
    monkeypatch.delenv("ENABLE_IMAGE_LATE_BIND", raising=False)


def _step1(name):
    return {
        "brand": "",
        "name": name,
        "variant": None,
        "category": scs.classify_category_from_text(name),
        "search_query": name,
        "_explicit": True,
    }


def _resolve(pair):
    pr._reset_resolver_state()
    return asyncio.run(pr.resolve_pair(list(pair), selected_category=None))


def _applied(pair):
    r = _resolve(pair)
    products = [_step1(pair[0]), _step1(pair[1])]
    both = pr.apply_resolution(products, r)
    return r, products, both


def _sides(r):
    return [(s.brand, s.line, s.concentration, s.source, s.confidence) for s in r.sides]


def _full_name(product):
    return scs._product_display_identity(
        product["brand"], product["name"], product["variant"], product["search_query"], False
    )[0]


# ======================================================================= AR-0 the one home (data rows)


def test_ar0_arabic_aliases_in_the_lines_file():
    """AR-0 (spec 1.2.1, M1R-2, M1R-3): the Arabic house and line aliases live in
    data/fragrance_lines.json, the YA spelling of the Bleu particle an EXPLICIT alias row."""
    data = json.loads(LINES_FILE.read_bytes().decode("ascii"))
    by_line = {x["line"]: x for x in data["lines"]}
    assert DIOR in by_line["Sauvage"]["house_aliases"], "Arabic Dior house alias missing"
    assert SAUVAGE in by_line["Sauvage"]["aliases"], "Arabic Sauvage line alias missing"
    assert CHANEL in by_line["Bleu de Chanel"]["house_aliases"], "Arabic Chanel missing"
    assert BLEU_WAW in by_line["Bleu de Chanel"]["aliases"], "WAW Bleu alias missing"
    assert BLEU_YA in by_line["Bleu de Chanel"]["aliases"], "YA Bleu alias missing (M1R-3)"


def test_ar0b_lines_file_ascii_and_loads():
    """AR-0b / MA7 (PIN): the file stays pure ASCII (the loader refuses any byte > 127)."""
    raw = LINES_FILE.read_bytes()
    assert sum(1 for b in raw if b > 127) == 0
    json.loads(raw.decode("ascii"))


def test_ar0c_loader_reads_fourteen_lines():
    """AR-0c / MA7: the real file loads through the resolver's loader: 12 + Y + Hawas."""
    _state, lines = pr._load_lines()
    assert len(lines) == 14, [x["line"] for x in lines]


# ======================================================================= AR-1 resolve and rewrite

AR1_PAIRS = [
    ((AR_A, AR_B), (LAT_A, LAT_B)),
    ((AR_A, AR_B_YA), (LAT_A, LAT_B)),
    ((AR_A, LAT_B), (LAT_A, LAT_B)),
    ((AR_B, LAT_A), (LAT_B, LAT_A)),
    ((AR_B_YA, LAT_A), (LAT_B, LAT_A)),
]
AR1_IDS = ["arA_arB", "arA_arBya", "arA_latB", "arB_latA", "arBya_latA"]


@pytest.mark.parametrize("pair,twin", AR1_PAIRS, ids=AR1_IDS)
def test_ar1_arabic_pair_resolves_and_rewrites_as_latin(monkeypatch, pair, twin):
    """AR-1: resolve_pair of the Arabic names is `resolved` with the Latin sides, and
    apply_resolution writes exactly the dicts the Latin twin pair produces."""
    _unit_flags(monkeypatch)
    r_lat, p_lat, both_lat = _applied(twin)
    assert r_lat.outcome == "resolved" and both_lat is True
    r_ar, p_ar, both_ar = _applied(pair)
    assert r_ar.outcome == "resolved", (r_ar.outcome, _sides(r_ar))
    assert _sides(r_ar) == _sides(r_lat), (_sides(r_ar), _sides(r_lat))
    want = {
        LAT_A: ("Dior", "Sauvage", "EDP", "lexicon", "high"),
        LAT_B: ("Chanel", "Bleu de Chanel", "EDP", "lexicon", "high"),
    }
    assert _sides(r_ar) == [want[twin[0]], want[twin[1]]], _sides(r_ar)
    assert both_ar is True
    got = [{k: p[k] for k in KEYS5} for p in p_ar]
    exp = [{k: p[k] for k in KEYS5} for p in p_lat]
    assert got == exp, (got, exp)
    assert r_ar.usage is None


# ======================================================================= AR-2 the compare seam

MIXES = {
    "text_off": {"text": False, "consent": 3, "words": False},
    "text_on_c3": {"text": True, "consent": 3, "words": False},
    "text_on_c2": {"text": True, "consent": 2, "words": False},
    "text_on_c3_words": {"text": True, "consent": 3, "words": True},
}
AR2_PAIRS = {"waw": (AR_A, AR_B), "ya": (AR_A, AR_B_YA)}
LAT_PAIR = (LAT_A, LAT_B)


def _recorders(rec):
    def _extra(p, svc, state):
        async def _price(brand, name, variant, region, search_query, nocache=False,
                         category="other"):
            rec["price"].append(
                {
                    "brand": brand,
                    "name": name,
                    "variant": variant,
                    "region": region,
                    "category": category,
                    "serper_query": search_query,
                    "cache_key": scs.build_size_aware_price_cache_key(
                        brand, name, variant, region, search_query, category=category
                    ),
                }
            )
            return {"amount": 120.0, "currency": "BHD", "estimated": False,
                    "source_method": "local_bhd", "retailer": "Best Buy",
                    "url": "https://www.bestbuy.com/site/x/1.p", "title": "x",
                    "in_stock": True}

        async def _image(full_name, *args, **kwargs):
            relevance = dict(kwargs.get("relevance") or {})
            rec["image"].append(
                {
                    "query": "%s perfume" % full_name,
                    "relevance": {k: v for k, v in relevance.items() if k != "typed"},
                    "typed": relevance.get("typed"),
                }
            )
            return None

        svc._get_price = _price
        p.setattr(scs, "get_product_image_url", _image)

    return _extra


def _seam(monkeypatch, kind, pair, mix_name, flag="true"):
    mix = MIXES[mix_name]
    r1s._full(monkeypatch, flag, consent=mix["consent"], text=mix["text"])
    if not mix["text"]:
        monkeypatch.delenv("ENABLE_ANTHROPIC_TEXT", raising=False)
    _image_flags(monkeypatch, words=mix["words"])
    r1s.ANTH.__init__()
    pr._reset_resolver_state()
    lr._reset_router_state()
    rec = {"price": [], "image": []}
    payload, state, svc = r1s._run(kind, pair, extra=_recorders(rec))
    return payload, state, svc, rec, list(r1s.ANTH.calls)


def _key(d):
    return json.dumps(d, sort_keys=True, ensure_ascii=True, default=repr)


def _no_typed(products):
    return [{k: v for k, v in p.items() if k != "_typed_name"} for p in products]


_LATIN_SEAM = {}


def _latin_seam(monkeypatch, kind, mix_name):
    key = (kind, mix_name)
    if key not in _LATIN_SEAM:
        payload, state, _svc, rec, calls = _seam(monkeypatch, kind, LAT_PAIR, mix_name)
        body = r1s._success_body(kind, payload)
        _LATIN_SEAM[key] = {
            "fetch": copy.deepcopy(state["fetch_products"]),
            "searches": sorted(s[0] for s in state["searches"]),
            "price": sorted(_key(x) for x in rec["price"]),
            "image": sorted(_key({k: x[k] for k in ("query", "relevance")}) for x in rec["image"]),
            "products": [(p.get("brand"), p.get("name")) for p in body["overview"]["products"]],
            "calls": calls,
        }
    return _LATIN_SEAM[key]


@pytest.mark.parametrize("mix_name", sorted(MIXES))
@pytest.mark.parametrize("pair_name", sorted(AR2_PAIRS))
@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_ar2_seam_queries_equal_the_latin_twin(monkeypatch, kind, pair_name, mix_name):
    """AR-2: through the compare entry (sync and the stream twin) with the flag ON, the
    serper-shopping query, the unified-search query, the price cache key and the image query
    (full_name + " perfume") of the Arabic pair are byte-equal to the Latin pair's; no model
    call is made for the Arabic pair in any mix (the fold needs no model arm)."""
    lat = _latin_seam(monkeypatch, kind, mix_name)
    assert lat["calls"] == [], "the Latin twin made a model call"
    pair = AR2_PAIRS[pair_name]
    payload, state, _svc, rec, calls = _seam(monkeypatch, kind, pair, mix_name)
    assert calls == [], "the Arabic pair reached the model arm (%d calls)" % len(calls)
    assert _no_typed(state["fetch_products"]) == _no_typed(lat["fetch"]), (
        state["fetch_products"],
        lat["fetch"],
    )
    assert sorted(s[0] for s in state["searches"]) == lat["searches"]
    assert sorted(_key(x) for x in rec["price"]) == lat["price"]
    image = sorted(_key({k: x[k] for k in ("query", "relevance")}) for x in rec["image"])
    assert image == lat["image"], (image, lat["image"])
    body = r1s._success_body(kind, payload)
    got = [(p.get("brand"), p.get("name")) for p in body["overview"]["products"]]
    assert got == lat["products"], (got, lat["products"])
    if MIXES[mix_name]["words"]:
        typed = [p.get("_typed_name") for p in state["fetch_products"]]
        assert typed == list(pair), typed


# ======================================================================= AR-3 the price filters


def _accepts(query, line):
    sel, show = [], []
    for title in CORPUS[line]:
        if ps._selection_match(query, title, CAT):
            sel.append(title)
        price = {
            "amount": AMOUNT[line],
            "currency": "BHD",
            "source_method": "local_bhd",
            "title": title,
            "url": "https://shop.example.bh/products/item-1",
            "retailer": "shop.example.bh",
        }
        if ps.is_price_showable(query, price, CAT, enforce_correctness=True):
            show.append(title)
    return sel, show


def _resolved_full_name(typed):
    partner = LAT_B if LINE_OF[typed] == "sauvage" else LAT_A
    _r, products, _both = _applied((typed, partner))
    return _full_name(products[0])


@pytest.mark.parametrize("typed", [LAT_A, LAT_B], ids=["latA", "latB"])
def test_ar3_pin_latin_accept_sets_equal_the_golden(monkeypatch, typed):
    """AR-3 PIN: the Latin twin's resolved full_name accepts exactly the facts Q4 golden."""
    _unit_flags(monkeypatch)
    line = LINE_OF[typed]
    sel, show = _accepts(_resolved_full_name(typed), line)
    assert sel == SEL_GOLDEN[line], sel
    assert show == SHOW_GOLDEN[line], show


@pytest.mark.parametrize("typed", [AR_A, AR_B, AR_B_YA], ids=["arA", "arB", "arBya"])
def test_ar3_arabic_accept_sets_equal_the_golden(monkeypatch, typed):
    """AR-3: the three Arabic strings reach _selection_match and is_price_showable with the
    Latin identity: the accepted-candidate sets equal the frozen LATIN golden."""
    _unit_flags(monkeypatch)
    line = LINE_OF[typed]
    query = _resolved_full_name(typed)
    sel, show = _accepts(query, line)
    assert sel == SEL_GOLDEN[line], (ascii(query), sel)
    assert show == SHOW_GOLDEN[line], (ascii(query), show)


# ======================================================================= AR-4 the picture identity


def _picture(pair, slot_titles=True):
    svc = scs.StructuredComparisonService()
    products = [_step1(pair[0]), _step1(pair[1])]
    pr._reset_resolver_state()
    refusal, _both = asyncio.run(
        svc._resolve_explicit_pair(products, None, datetime.now())
    )
    assert refusal is None, refusal
    out = []
    for slot, product in enumerate(products):
        full = _full_name(product)
        category = scs.canonicalize_category(product.get("category"))
        typed = scs._typed_image_text(product, full)
        kw = ir.relevance_kwargs(
            product["brand"], product["name"], category, slot, False, typed=typed
        )
        ident = ir.identity(full, kw.get("relevance"))
        line = LINE_OF[pair[slot]]
        verdicts = [ir.check(ident, [title]) for title in CORPUS[line]]
        out.append(
            {
                "kw": kw,
                "ident": ident,
                "query": ir.image_query(full, ident),
                "verdicts": verdicts,
            }
        )
    return out


AR4_PAIRS = {"waw": (AR_A, AR_B), "ya": (AR_A, AR_B_YA)}
# facts Q5: the Latin accepted counts per line (SHORT_LINE ON; + WORDS ON)
AR4_LATIN_ACCEPTED = {False: (13, 11), True: (5, 5)}


@pytest.mark.parametrize("words", [False, True], ids=["words_off", "words_on"])
def test_ar4_pin_latin_picture_counts(monkeypatch, words):
    """AR-4 PIN: the Latin pair's picture verdicts accept the facts Q5 counts."""
    _unit_flags(monkeypatch)
    _image_flags(monkeypatch, words=words)
    lat = _picture(LAT_PAIR)
    got = tuple(sum(1 for v in x["verdicts"] if v is None) for x in lat)
    assert got == AR4_LATIN_ACCEPTED[words], got


@pytest.mark.parametrize("words", [False, True], ids=["words_off", "words_on"])
@pytest.mark.parametrize("pair_name", sorted(AR4_PAIRS))
def test_ar4_picture_identity_equals_the_latin_twin(monkeypatch, pair_name, words):
    """AR-4: relevance_kwargs, the identity, the image query and the verdict per corpus title
    of the Arabic pair equal the Latin pair's (ENABLE_IMAGE_GUARD_SHORT_LINE ON; WORDS off and
    on: with WORDS ON only the typed carrier and the words it adds to query_words differ)."""
    _unit_flags(monkeypatch)
    _image_flags(monkeypatch, words=words)
    lat = _picture(LAT_PAIR)
    ar = _picture(AR4_PAIRS[pair_name])
    for slot in (0, 1):
        a, b = ar[slot], lat[slot]
        kw_a = copy.deepcopy(a["kw"])
        kw_b = copy.deepcopy(b["kw"])
        typed_a = kw_a.get("relevance", {}).pop("typed", None)
        kw_b.get("relevance", {}).pop("typed", None)
        assert kw_a == kw_b, (slot, ascii(kw_a), kw_b)
        if words:
            assert typed_a == AR4_PAIRS[pair_name][slot], ascii(typed_a)
            ia = dataclasses.replace(a["ident"], query_words=frozenset())
            ib = dataclasses.replace(b["ident"], query_words=frozenset())
        else:
            ia, ib = a["ident"], b["ident"]
        assert ia == ib, (slot, ascii(ia), ib)
        assert a["query"] == b["query"], (slot, ascii(a["query"]), b["query"])
        assert a["verdicts"] == b["verdicts"], (slot, a["verdicts"], b["verdicts"])


# ======================================================================= AR-5 Arabic concentration phrases

AR5_CASES = [
    ("edp_waw_lexicon", DIOR + " " + SAUVAGE + " " + LEX_EDP, ("Dior", "Sauvage", "EDP")),
    ("edp_ya", " ".join((DIOR, SAUVAGE, EAU_HAMZA, DE_YA, PARFAN)), ("Dior", "Sauvage", "EDP")),
    ("edp_waw_plain_alef", " ".join((DIOR, SAUVAGE, EAU, DE_WAW, PARFAN)), ("Dior", "Sauvage", "EDP")),
    ("edp_ya_plain_alef", " ".join((DIOR, SAUVAGE, EAU, DE_YA, PARFAN)), ("Dior", "Sauvage", "EDP")),
    ("edt_waw_lexicon", DIOR + " " + SAUVAGE + " " + LEX_EDT, ("Dior", "Sauvage", "EDT")),
    ("edt_ya", " ".join((DIOR, SAUVAGE, EAU_HAMZA, DE_YA, TOILET)), ("Dior", "Sauvage", "EDT")),
    ("parfum", DIOR + " " + SAUVAGE + " " + LEX_PARFUM, ("Dior", "Sauvage", "Parfum")),
    ("bleu_waw_edp", BLEU_WAW + " " + LEX_EDP, ("Chanel", "Bleu de Chanel", "EDP")),
    ("bleu_ya_edp_ya", " ".join((BLEU_YA, EAU, DE_YA, PARFAN)), ("Chanel", "Bleu de Chanel", "EDP")),
]


@pytest.mark.parametrize("name,want", [c[1:] for c in AR5_CASES], ids=[c[0] for c in AR5_CASES])
def test_ar5_arabic_concentration_phrase_resolves(monkeypatch, name, want):
    """AR-5: an all-Arabic name with the lexicon's Arabic concentration phrase (the WAW and
    the YA particle) resolves high/lexicon to the Latin concentration token."""
    _unit_flags(monkeypatch)
    side = pr.resolve_lexicon(name)
    got = (side.brand, side.line, side.concentration)
    assert got == want, (got, side.confidence, side.source)
    assert side.resolved is True and side.source == "lexicon", side


def test_ar5b_pin_lexicon_holds_the_three_arabic_phrases():
    """AR-5b PIN: the lexicon (the one home of concentration words) holds the 3 WAW phrases
    and the Arabic Rasasi house the Hawas row reuses."""
    data = json.loads(LEXICON_FILE.read_bytes().decode("ascii"))
    conc = data["fragrance"]["concentrations"]
    for phrase in (LEX_EDP, LEX_EDT, LEX_PARFUM):
        assert phrase in conc, ascii(phrase)
    assert RASASI in data["fragrance"]["houses"]


def test_ar5c_pin_price_service_concentration_unchanged():
    """AR-5c PIN (spec 1.2.2): price_service.extract_concentration is NOT changed: it still
    reads no Arabic phrase (the resolver writes the Latin token instead)."""
    for phrase in (LEX_EDP, LEX_EDT, LEX_PARFUM):
        assert ps.extract_concentration(DIOR + " " + SAUVAGE + " " + phrase) is None
    assert ps.extract_concentration(AR_A) == "EDP"


def test_ar5d_pin_phrases_come_from_the_lexicon(monkeypatch, tmp_path):
    """AR-5d PIN (M1R-2: no second table): with a FRAGRANCE_LEXICON_PATH seam lexicon that
    lacks the Arabic concentration phrases, the Arabic phrase is NOT read as EDP."""
    _unit_flags(monkeypatch)
    data = json.loads(LEXICON_FILE.read_bytes().decode("ascii"))
    data["fragrance"]["concentrations"] = [
        c for c in data["fragrance"]["concentrations"] if all(ord(ch) < 128 for ch in c)
    ]
    seam = tmp_path / "lexicon_no_arabic_conc.json"
    seam.write_text(json.dumps(data, ensure_ascii=True), encoding="ascii")
    monkeypatch.setenv("FRAGRANCE_LEXICON_PATH", str(seam))
    cg._reset_lexicon_cache()
    pr._reset_resolver_state()
    side = pr.resolve_lexicon(DIOR + " " + SAUVAGE + " " + LEX_EDP)
    assert not (side.resolved and side.concentration == "EDP"), side


# ======================================================================= SEED-1 the seed rows


def test_seed1_data_rows():
    """SEED-1 data (M1R-4): the 12 base lines carry exactly the spec's edits; YSL Y and Rasasi
    Hawas are added with the stated facts; single_concentration only on the four lines."""
    data = json.loads(LINES_FILE.read_bytes().decode("ascii"))
    lines = data["lines"]
    by_key = {(x["house"], x["line"]): x for x in lines}
    want = _expected_existing()
    for key, item in want.items():
        assert key in by_key, key
        assert _setify(by_key[key]) == item, (key, ascii(by_key[key]))
    y = by_key.get(("Yves Saint Laurent", "Y"))
    assert y is not None, "the YSL Y line is missing"
    assert sorted(y["concentrations"]) == ["EDP", "EDT"] and y["base"] == "EDT", y
    assert sorted(y["flankers"]) == ["Elixir", "Le Parfum"], y
    assert y.get("single_concentration", False) is False, y
    hawas = by_key.get(("Rasasi", "Hawas"))
    assert hawas is not None, "the Rasasi Hawas line is missing"
    assert sorted(hawas["house_aliases"]) == sorted(["rasasi", RASASI]), ascii(hawas)
    assert hawas["concentrations"] == ["EDP"] and hawas["base"] == "EDP", hawas
    assert sorted(hawas["flankers"]) == ["Ice", "for Her"], hawas
    assert hawas.get("single_concentration") is True, hawas
    assert len(lines) == 14, [x["line"] for x in lines]
    singles = {x["line"] for x in lines if x.get("single_concentration") is True}
    assert singles == SINGLE_CONCENTRATION_LINES, singles


SEED1_CASES = [
    ("YSL Y EDP", ("Yves Saint Laurent", "Y", "EDP", None)),
    ("YSL Y", ("Yves Saint Laurent", "Y", "EDT", None)),
    ("Yves Saint Laurent Y Eau de Parfum", ("Yves Saint Laurent", "Y", "EDP", None)),
    ("Rasasi Hawas", ("Rasasi", "Hawas", "EDP", None)),
    ("Creed Aventus Cologne", ("Creed", "Aventus Cologne", None, "Cologne")),
    ("Aventus Cologne", ("Creed", "Aventus Cologne", None, "Cologne")),
    ("Rasasi Hawas for Her", ("Rasasi", "Hawas for Her", None, "for Her")),
    ("Hawas for Her", ("Rasasi", "Hawas for Her", None, "for Her")),
    ("Hawas Ice", ("Rasasi", "Hawas Ice", None, "Ice")),
    ("Rasasi Hawas Ice", ("Rasasi", "Hawas Ice", None, "Ice")),
    ("Lattafa Khamrah Qahwa", ("Lattafa", "Khamrah Qahwa", None, "Qahwa")),
    ("Khamrah Qahwa", ("Lattafa", "Khamrah Qahwa", None, "Qahwa")),
    ("Lattafa Khamrah Dukhan", ("Lattafa", "Khamrah Dukhan", None, "Dukhan")),
    ("Creed Aventus for Her", ("Creed", "Aventus for Her", None, "for Her")),
    ("Creed Aventus Absolu", ("Creed", "Aventus Absolu", None, "Absolu")),
    ("YSL Libre Intense", ("Yves Saint Laurent", "Libre Intense", None, "Intense")),
    ("YSL Libre EDT", ("Yves Saint Laurent", "Libre", "EDT", None)),
]


@pytest.mark.parametrize("name,want", SEED1_CASES, ids=[c[0] for c in SEED1_CASES])
def test_seed1_typed_names_resolve(monkeypatch, name, want):
    """SEED-1: the seeded names resolve high/lexicon; a typed flanker word (cologne, for her,
    ice, qahwa ...) resolves to the line WITH that flanker (the Stronger With You
    representation), never to the base key at high."""
    _unit_flags(monkeypatch)
    side = pr.resolve_lexicon(name)
    got = (side.brand, side.line, side.concentration, side.flanker)
    assert got == want, (name, got, side.confidence, side.source)
    assert side.resolved is True and side.source == "lexicon", side


# ======================================================================= SEED-2 the validator


def _one_line(**extra):
    item = copy.deepcopy(BASE_LINES[2])
    item.update(extra)
    return {"version": 1, "note": "seam", "lines": [item]}


@pytest.mark.parametrize("value", [True, False], ids=["true", "false"])
def test_seed2_pin_validator_accepts_boolean(value):
    """SEED-2 PIN: single_concentration true / false (and absent) is accepted."""
    assert len(pr._validate_lines(_one_line(single_concentration=value))) == 1
    assert len(pr._validate_lines(_one_line())) == 1


@pytest.mark.parametrize("value", [1, 0, "true", "", None], ids=["1", "0", "str_true", "blank", "null"])
def test_seed2_validator_rejects_non_boolean(value):
    """SEED-2 / MA6: a non-boolean single_concentration is refused (ValueError)."""
    raised = None
    try:
        pr._validate_lines(_one_line(single_concentration=value))
    except ValueError as exc:
        raised = exc
    assert raised is not None, "single_concentration=%r was accepted" % (value,)


# ======================================================================= PIN-1 the existing lines


def _side_tuple(side):
    return (
        side.brand,
        side.line,
        side.concentration,
        side.size_ml,
        side.confidence,
        side.source,
        side.resolved,
        side.flanker,
    )


_SAUV_C = [("Dior", "Sauvage", "EDP"), ("Dior", "Sauvage", "Parfum"), ("Dior", "Sauvage", "Elixir")]
_BLEU_C = [("Chanel", "Bleu de Chanel", "EDP"), ("Chanel", "Bleu de Chanel", "Parfum")]
_BR_C = [("Maison Francis Kurkdjian", "Baccarat Rouge 540", "Extrait")]
_SWY_C = [
    ("Emporio Armani", "Stronger With You Intensely", None),
    ("Emporio Armani", "Stronger With You Absolutely", None),
    ("Emporio Armani", "Stronger With You Leather", None),
    ("Emporio Armani", "Stronger With You", "Parfum"),
]
# (typed, (brand, line, conc, size, confidence, source, resolved, flanker), candidates) at 7f672cfe
PIN1_FULL = [
    ("Dior Sauvage", ("Dior", "Sauvage", "EDT", None, "high", "lexicon", True, None), _SAUV_C),
    ("Sauvage EDP", ("Dior", "Sauvage", "EDP", None, "high", "lexicon", True, None), []),
    ("Dior Sauvage 100 ML Edp", ("Dior", "Sauvage", "EDP", 100, "high", "lexicon", True, None), []),
    ("Sauvage Elixir", ("Dior", "Sauvage", "Elixir", None, "high", "lexicon", True, None), []),
    ("Dior Sauvage Parfum", ("Dior", "Sauvage", "Parfum", None, "high", "lexicon", True, None), []),
    ("Dior Sauvage Tester", ("Dior", "Sauvage", "EDT", None, "high", "lexicon", True, None), _SAUV_C),
    ("Bleu de Chanel", ("Chanel", "Bleu de Chanel", "EDT", None, "high", "lexicon", True, None), _BLEU_C),
    ("Bleu de chanel EDP", ("Chanel", "Bleu de Chanel", "EDP", None, "high", "lexicon", True, None), []),
    ("Bleu de Chanel Parfum", ("Chanel", "Bleu de Chanel", "Parfum", None, "high", "lexicon", True, None), []),
    ("Baccarat Rouge 540", ("Maison Francis Kurkdjian", "Baccarat Rouge 540", "EDP", None, "high", "lexicon", True, None), _BR_C),
    ("BR540", (None, None, None, None, "low", "none", False, None), []),
    ("Baccarat Rouge 540 Extrait", ("Maison Francis Kurkdjian", "Baccarat Rouge 540", "Extrait", None, "high", "lexicon", True, None), []),
    ("MFK Baccarat Rouge 540", ("Maison Francis Kurkdjian", "Baccarat Rouge 540", "EDP", None, "high", "lexicon", True, None), _BR_C),
    ("Stronger With You Intensely", ("Emporio Armani", "Stronger With You Intensely", None, None, "high", "lexicon", True, "Intensely"), []),
    ("Emporio Armani Stronger With You Parfum", ("Emporio Armani", "Stronger With You", "Parfum", None, "high", "lexicon", True, "Parfum"), []),
    ("stronger with you", ("Emporio Armani", "Stronger With You", "EDT", None, "high", "lexicon", True, None), _SWY_C),
    ("Layton", ("Parfums de Marly", "Layton", "EDP", None, "high", "lexicon", True, None), []),
    ("Parfums de Marly Layton", ("Parfums de Marly", "Layton", "EDP", None, "high", "lexicon", True, None), []),
    ("Lancome La Vie Est Belle", ("Lancome", "La Vie Est Belle", "EDP", None, "high", "lexicon", True, None), []),
    ("Versace Eros", ("Versace", "Eros", "EDT", None, "high", "lexicon", True, None), [("Versace", "Eros", "EDP")]),
    ("Versace Eros EDP", ("Versace", "Eros", "EDP", None, "high", "lexicon", True, None), []),
    ("Eros", ("Versace", "Eros", "EDT", None, "high", "lexicon", True, None), [("Versace", "Eros", "EDP")]),
    ("Acqua di Gio Profumo", ("Giorgio Armani", "Acqua di Gio Profumo", None, None, "high", "lexicon", True, None), []),
    ("Bvlgari Tygar", ("Bvlgari", "Tygar", "EDP", None, "high", "lexicon", True, None), []),
    ("Tyger", (None, None, None, None, "medium", "none", False, None), [("Bvlgari", "Tygar", "EDP")]),
]
# the lines whose candidates change ON PURPOSE (Libre's concentration set, the flanker rows):
# the side itself is pinned, the candidate list is listed as deliberate in the gate.
PIN1_SIDE_ONLY = [
    ("Creed Aventus", ("Creed", "Aventus", "EDP", None, "high", "lexicon", True, None)),
    ("Aventus", ("Creed", "Aventus", "EDP", None, "high", "lexicon", True, None)),
    ("YSL Libre", ("Yves Saint Laurent", "Libre", "EDP", None, "high", "lexicon", True, None)),
    ("Libre", ("Yves Saint Laurent", "Libre", "EDP", None, "high", "lexicon", True, None)),
    ("Lattafa Khamrah", ("Lattafa", "Khamrah", "EDP", None, "high", "lexicon", True, None)),
    ("Khamrah", ("Lattafa", "Khamrah", "EDP", None, "high", "lexicon", True, None)),
]


@pytest.mark.parametrize("name,want,cands", PIN1_FULL, ids=[c[0] for c in PIN1_FULL])
def test_pin1_existing_lines_unchanged(monkeypatch, name, want, cands):
    """PIN-1: the R4 typed set on the unchanged lines resolves exactly as at the base."""
    _unit_flags(monkeypatch)
    side = pr.resolve_lexicon(name)
    assert _side_tuple(side) == want, (name, _side_tuple(side))
    got = [(c["brand"], c["line"], c["concentration"]) for c in side.candidates]
    assert got == cands, (name, got)


@pytest.mark.parametrize("name,want", PIN1_SIDE_ONLY, ids=[c[0] for c in PIN1_SIDE_ONLY])
def test_pin1_changed_lines_keep_their_side(monkeypatch, name, want):
    """PIN-1: the base key of a line with new flankers / concentrations still resolves to the
    same side (only its candidates change, on purpose)."""
    _unit_flags(monkeypatch)
    assert _side_tuple(pr.resolve_lexicon(name)) == want, name


def test_pin1_arabic_outside_the_seed_unchanged(monkeypatch):
    """PIN-1 (stated limit 1.4): an Arabic name outside the two seeded lines (Khamrah Lattafa
    in Arabic) still does not resolve deterministically: it goes to the model arm."""
    _unit_flags(monkeypatch)
    khamrah = _cp(0x062E, 0x0645, 0x0631, 0x0629)
    lattafa = _cp(0x0644, 0x0637, 0x0627, 0x0641, 0x0629)
    side = pr.resolve_lexicon(khamrah + " " + lattafa)
    assert _side_tuple(side) == (None, None, None, None, "medium", "none", False, None), side


# ======================================================================= PIN-0 flag OFF and the non-hook readers

# base64 sha256 of fy._digest over {snapshot, recorders}, RECORDED at 7f672cfe
BASE_OFF_DIGEST = {
    ("rest", "ar"): "VFX94Py7V+ZR0qb7eQGGtUvODG481SB/j2Ze9MMiJBI=",
    ("stream", "ar"): "sDiiMZZm8DmAtLxk3QnXKxstVJ27q06MY//7TYHE2Ao=",
    ("rest", "lat"): "hbQ0ITS7SPAmWQhe0kUcHKsXyKwBixHSCdwMyd3w+aw=",
    ("stream", "lat"): "hOgLAoSI+bkzwFvN9RpUy6FE1YwfhNQ+X2eB/EB+yp0=",
}
OFF_PAIRS = {"ar": (AR_A, AR_B), "lat": (LAT_A, LAT_B)}


@pytest.mark.parametrize("off", [None, "false"], ids=["unset", "false"])
@pytest.mark.parametrize("pair_name", sorted(OFF_PAIRS))
@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_pin0_flag_off_identity(monkeypatch, kind, pair_name, off):
    """PIN-0: with ENABLE_PRODUCT_RESOLVER OFF (unset / "false") and the FULL configuration
    (TEXT ON, consent 3, both knobs, the picture guard and WORDS ON) the compare output for
    the Arabic pair and the Latin pair is byte-identical to the base; the resolver reads no
    lines file and makes no call."""
    pair = OFF_PAIRS[pair_name]
    r1s._full(monkeypatch, off, consent=3)
    _image_flags(monkeypatch, words=True)
    rec_calls = r1s.Recorders(monkeypatch)
    rec = {"price": [], "image": []}
    payload, state, svc = r1s._run(kind, pair, extra=_recorders(rec))
    monkeypatch.setattr(os, "getenv", os.environ.get)
    assert r1s.ANTH.calls == [] and r1s.OAI_CALLS == []
    assert rec_calls.lines_opens() == [], rec_calls.lines_opens()
    assert "resolve" not in rec_calls.sites, rec_calls.sites
    assert [p["brand"] for p in state["fetch_products"]] == ["", ""]
    assert [p["name"] for p in state["fetch_products"]] == list(pair)
    snap = r1s._snapshot(payload, state, svc)
    import base64
    import hashlib

    blob = fy._digest({"snap": snap, "rec": rec})
    got = base64.b64encode(hashlib.sha256(blob.encode("ascii")).digest()).decode("ascii")
    assert got == BASE_OFF_DIGEST[(kind, pair_name)], got


def test_pin0_constants_the_middleware_and_routes_read():
    """PIN-0: the names text_routes and error_handler read are unchanged (the data fold
    touches none of them)."""
    labels = ("EDT", "EDP", "Parfum", "Extrait", "EDC", "Elixir", "Eau Fraiche", "Parfum Intense")
    assert pr.CONCENTRATIONS == labels
    assert eh._RESOLVER_CONCENTRATIONS == labels
    assert pr.ASK_MESSAGE == r1s.ASK_MESSAGE
    assert (pr.REFUSAL_CODE, pr.REFUSAL_REASON) == ("INSUFFICIENT_DATA", "placeholder_identity")


def test_pin0_resolver_word_tables_unchanged():
    """PIN-0 (M1R-2): no second table in the resolver: the Latin phrase table, the generic and
    the qualifier words are the base ones (the Arabic phrases come from the lexicon)."""
    assert pr.CONCENTRATION_PHRASES == (
        (("extrait", "de", "parfum"), "Extrait"),
        (("parfum", "intense"), "Parfum Intense"),
        (("eau", "de", "parfum"), "EDP"),
        (("eau", "de", "toilette"), "EDT"),
        (("eau", "de", "cologne"), "EDC"),
        (("eau", "fraiche"), "Eau Fraiche"),
        (("edp",), "EDP"),
        (("edt",), "EDT"),
        (("edc",), "EDC"),
        (("extrait",), "Extrait"),
        (("elixir",), "Elixir"),
        (("parfum",), "Parfum"),
    )
    assert pr.GENERIC_WORDS == frozenset(
        {"perfume", "perfumes", "fragrance", "fragrances", "cologne", "colognes", "scent",
         "scents", "spray"}
    )
    assert pr.QUALIFIER_WORDS == frozenset(
        {"for", "men", "mens", "man", "male", "him", "his", "homme", "tester", "original",
         "authentic", "genuine", "new"}
    )


def _resolver_attrs(rel_path, alias):
    tree = ast.parse((ROOT / rel_path).read_text(encoding="utf-8"))
    return sorted(
        {
            n.attr
            for n in ast.walk(tree)
            if isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name)
            and n.value.id == alias
        }
    )


def test_pin0_non_hook_readers_unchanged():
    """PIN-0: the resolver names scs (outside the hook body: none), text_routes and the link
    key read are the base ones; error_handler imports no service."""
    assert _resolver_attrs("app/services/structured_comparison_service.py", "_product_resolver") == [
        "OUTCOME_ASK",
        "apply_resolution",
        "product_resolver_enabled",
        "refusal_result",
        "resolve_pair",
    ]
    assert _resolver_attrs("app/api/text_routes.py", "_product_resolver") == [
        "ASK_MESSAGE",
        "http_detail_extras",
        "is_ask_refusal",
    ]
    assert _resolver_attrs("app/services/url_extraction_service.py", "product_resolver") == [
        "_typed_concentration",
        "resolve_lexicon",
    ]
    src = (ROOT / "app/middleware/error_handler.py").read_text(encoding="utf-8")
    assert "import product_resolver" not in src and "product_resolver import" not in src


LINK_PAGES = [
    (("Dior", "Sauvage Eau de Parfum 100ml"), ("Dior", "Sauvage", "EDP", 100, True)),
    (("Chanel", "Bleu de Chanel Eau de Toilette 50ml"), ("Chanel", "Bleu de Chanel", "EDT", 50, True)),
    (("Creed", "Aventus 100ml"), ("Creed", "Aventus", None, 100, True)),
    (("Yves Saint Laurent", "Libre Eau de Parfum 90ml"), ("Yves Saint Laurent", "Libre", "EDP", 90, True)),
    (("Parfums de Marly", "Layton EDP 125ml"), ("Parfums de Marly", "Layton", "EDP", 125, True)),
    (("Lattafa", "Khamrah EDP 100ml"), ("Lattafa", "Khamrah", "EDP", 100, True)),
    (("Versace", "Eros EDT 100ml"), ("Versace", "Eros", "EDT", 100, True)),
    (("Maison Francis Kurkdjian", "Baccarat Rouge 540 Extrait de Parfum 70ml"), ("Maison Francis Kurkdjian", "Baccarat Rouge 540", "Extrait", 70, True)),
    (("Emporio Armani", "Stronger With You Intensely 100ml"), ("Emporio Armani", "Stronger With You Intensely", None, 100, True)),
    (("Bvlgari", "Tygar EDP 125ml"), ("Bvlgari", "Tygar", "EDP", 125, True)),
    (("Lancome", "La Vie Est Belle EDP 50ml"), ("Lancome", "La Vie Est Belle", "EDP", 50, True)),
    (("Giorgio Armani", "Acqua di Gio Profumo 75ml"), ("Giorgio Armani", "Acqua di Gio Profumo", None, 75, True)),
    (("Apple", "iPhone 15 128GB"), (None, None, None, None, False)),
]


@pytest.mark.parametrize("page,want", LINK_PAGES, ids=[p[0][1] for p in LINK_PAGES])
def test_pin0_link_key_unchanged_for_the_base_lines(monkeypatch, page, want):
    """PIN-0: url_extraction_service._link_key (the INC-U1 link key, no flag of its own; read
    only) gives the base key for the existing lines' page names. A page naming a NEW seed
    line, a flanker or an Arabic name moves with the data (deliberate; under
    ENABLE_URL_LINK_RESULT only)."""
    _unit_flags(monkeypatch)
    key = ues._link_key({"brand": page[0], "name": page[1]}, None)
    got = (key["brand"], key["line"], key["concentration"], key["size_ml"], key["resolved"])
    assert got == want, (page, got)
