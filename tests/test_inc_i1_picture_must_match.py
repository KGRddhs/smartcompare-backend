"""INC-I1 PICTURE-MUST-MATCH (the S95-FIX incident lane) RED file A: the leaf
app/services/image_relevance.py and the guarded picture cascade
app/services/image_service.get_product_image_url.

Spec: .qa-s80/INC-I1_UNIT_SPEC.md (sha256 5539e844...) sections 2.1-2.3, 2.6, 2.8 and
5.2, as amended by the batch rulings RULINGS_INC_I1.md (I1-R1..I1-R21) and the review
.qa-s80/INC-I1_SPEC_REVIEW.md (the rulings win, then the review corrections, then the
spec): I1-R1 the deny list inside the guard on every tier (reason "denied"); I1-R2 the
fragrance word only for the categories fragrances and other (T20 -> None, T21); I1-R3
every significant line token when the brand is empty; I1-R4 registrable host labels,
the alias subset rule and no number-plus-unit line token; I1-R5 the knowledge-graph type
for the fragrance-word test only; I1-R7 the knob clamp 1..10; I1-R10 a Tier-3 pick needs
a raster path and is never an organic page link; I1-R12 the plurals; I1-R20 organic[:10]
for Tier 3, the review rows X9-X11 and the C-2 rows.

Flag ENABLE_IMAGE_RELEVANCE_GUARD (new, default OFF, read per call); knob
IMAGE_RELEVANCE_CANDIDATES. RED rows (test_r*) fail at base on an AssertionError only:
the leaf is reached through importlib.util.find_spec and the `relevance` keyword through
inspect.signature, never imported or passed at base. PIN rows (test_p*) are green at base
and run with the full configuration (the knob set, recorders on every tier) so a gated
mutant is killable (ruling B1). Every flag a row depends on is set or deleted by the row.

Hermetic: the three tier callables are patched on the module (the INC-X2a seams); no
network, no Redis, no LLM. Sentinels are built at run time; the banned-host sentinels are
concatenated so no banned host literal sits in this file; Arabic text is built with chr().
Pure ASCII, LF.
"""

from __future__ import annotations

import ast
import asyncio
import importlib
import importlib.util
import inspect
import logging
import os
import re
import sys

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

from app.services import image_service as img  # noqa: E402
from app.services import (
    price_service as _ps,
)  # noqa: E402  (I1-R20 / C-8: loaded first)

LOGGER = "app.services.image_service"
LEAF = "app.services.image_relevance"
FLAG = "ENABLE_IMAGE_RELEVANCE_GUARD"
KNOB = "IMAGE_RELEVANCE_CANDIDATES"
DG = "ENABLE_DATA_GUARDS_V2"
V2 = "ENABLE_IMAGE_PIPELINE_V2"

# The INC-X2a grammar (tests/test_inc_x2a_image_tier_timing.py:32-36), unchanged.
TIER = re.compile(
    r"^\[IMG_TIER\] tier=(piggyback|search_payload|serper_budget|serper_images|llm_pick) "
    r"outcome=(hit|miss|skipped|error:[A-Za-z_][A-Za-z0-9_]*) ms=\d+$"
)
CANCEL = re.compile(
    r"^\[IMG_TIER\] cancelled tier=(serper_images|llm_pick) tier_ms=(\d+) total_ms=(\d+)$"
)
# Spec 2.6, with the reason word "denied" of I1-R1.
REL_LINE = re.compile(
    r"^\[IMG_RELEVANCE\] product=(0|1|-) "
    r"tier=(none|piggyback|search_payload|serper_images|llm_pick) "
    r"outcome=(accepted|rejected|none) candidates=(\d+) "
    r"reason=(none|scheme|brand|name|fragrance_word|denied)$"
)


def _https(host, path):
    return "https://" + host + path


NAME = "Ty" + "ger"
POEM = _https("poem.example.com", "/tyger.jpg")
POEM_PAGE = _https("poems.example.org", "/poem/the-tyger")
BOTTLE = _https("img.example.com", "/tygar-1.jpg")
BOTTLE_A = _https("img.example.com", "/tygar-a.jpg")
BOTTLE_B = _https("img.example.com", "/tygar-b.jpg")
HTTP_BOTTLE = "http://" + "img.example.com" + "/tygar-h.jpg"
KG_IMG = _https("kg.example.com", "/hero.jpg")
ORG_IMG = _https("shop.example.com", "/aventus.jpg")
SHOP_PAGE = _https("shop.example.com", "/aventus")
PICK = _https("img.shop.example.com", "/aventus.jpg")
DIOR_IMG = _https("img.example.com", "/sauvage.jpg")
_BANNED = "fragr" + "antica"
FRAG_SOURCE = "Fragr" + "antica"
FRAG_PAGE = _https("www." + _BANNED + ".com", "/perfume/Bvlgari/Tygar-77.html")
FRAG_DOMAIN = "www." + _BANNED + ".com"
FIMGS_IMG = _https("fim" + "gs.net", "/mdimg/perfume/375x500.77.jpg")
SAFE_IMG = _https("img.example.com", "/tygar-safe.jpg")
AR_PERFUME = chr(0x0639) + chr(0x0637) + chr(0x0631)
AR_PERFUMES = chr(0x0639) + chr(0x0637) + chr(0x0648) + chr(0x0631)
LANCOME_ACC = "Lanc" + chr(0xF4) + "me"
IDOLE_ACC = "Id" + chr(0xF4) + "le"

POEM_ITEM = {
    "title": "The Tyger by William Blake",
    "source": "Poetry",
    "link": POEM_PAGE,
    "imageUrl": POEM,
}
POEM_ORGANIC = {
    "title": "The Tyger by William Blake",
    "link": POEM_PAGE,
    "snippet": "x",
}
BASE_PAIRS = [
    ("piggyback", "skipped"),
    ("search_payload", "skipped"),
    ("serper_budget", "hit"),
    ("serper_images", "hit"),
]


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    """conftest loads the developer .env with override: every flag a row reads is
    deleted here and set by the row itself."""
    for name in (FLAG, KNOB, DG, V2):
        monkeypatch.delenv(name, raising=False)


def _leaf():
    spec = importlib.util.find_spec(LEAF)
    assert (
        spec is not None
    ), "INC-I1 not built: app/services/image_relevance.py is missing"
    return importlib.import_module(LEAF)


def _assert_kw():
    params = inspect.signature(img.get_product_image_url).parameters
    assert (
        "relevance" in params
    ), "INC-I1 not built: get_product_image_url has no `relevance` keyword"


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _rel(brand, line, category="fragrances", slot=0):
    return {"brand": brand, "line": line, "category": category, "slot": slot}


class _Rec:
    def __init__(self):
        self.order = []
        self.budget = []
        self.search = []
        self.gpt = []
        self.cancelled = []


def _install(monkeypatch, rec, *, granted=True, images=None, gpt_url=None, hang=False):
    def _budget(n):
        rec.order.append("budget")
        rec.budget.append((n,))
        return granted

    async def _search(query, **kwargs):
        rec.order.append("search")
        rec.search.append(((query,), dict(kwargs)))
        if hang:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                rec.cancelled.append("search")
                raise
        return {"images": [dict(item) for item in (images or [])]}

    async def _gpt(name, organic):
        rec.order.append("gpt")
        rec.gpt.append((name, organic))
        return gpt_url

    monkeypatch.setattr(img, "try_consume_serper_image_credit", _budget)
    monkeypatch.setattr(img, "search_images", _search)
    monkeypatch.setattr(img, "extract_image_via_gpt", _gpt)


def _messages(caplog, prefix):
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == LOGGER and r.getMessage().startswith(prefix)
    ]


def _pairs(caplog):
    out = []
    for line in _messages(caplog, "[IMG_TIER]"):
        if line.startswith("[IMG_TIER] cancelled"):
            assert CANCEL.match(line), line
            continue
        m = TIER.match(line)
        assert m, "an [IMG_TIER] line left the INC-X2a grammar: %r" % line
        out.append((m.group(1), m.group(2)))
    return out


def _run_case(
    monkeypatch,
    caplog,
    *,
    name=NAME,
    rel=None,
    flag="true",
    knob=None,
    dg=None,
    granted=True,
    images=None,
    gpt_url=None,
    payload=None,
    organic=None,
    piggy=None,
):
    """One cascade call: returns (result, recorder, [IMG_TIER] pairs, [IMG_RELEVANCE] lines)."""
    _set(monkeypatch, FLAG, flag)
    _set(monkeypatch, KNOB, knob)
    _set(monkeypatch, DG, dg)
    rec = _Rec()
    _install(monkeypatch, rec, granted=granted, images=images, gpt_url=gpt_url)
    caplog.set_level(logging.INFO, logger=LOGGER)
    caplog.clear()
    kwargs = {
        "region": "bahrain",
        "page_scrape_image": piggy,
        "organic_results": organic,
        "search_payload": payload,
    }
    if rel is not None:
        _assert_kw()
        kwargs["relevance"] = rel
    out = asyncio.run(img.get_product_image_url(name, **kwargs))
    return out, rec, _pairs(caplog), _messages(caplog, "[IMG_RELEVANCE]")


def _line(slot, tier, outcome, n, reason):
    return "[IMG_RELEVANCE] product=%s tier=%s outcome=%s candidates=%d reason=%s" % (
        slot,
        tier,
        outcome,
        n,
        reason,
    )


# ---------------------------------------------------------------------------
# RED rows: the leaf
# ---------------------------------------------------------------------------


def test_r01_flag_reader_table(monkeypatch):
    """A-R01: guard_enabled() is the house idiom, read per call."""
    leaf = _leaf()
    for raw in ("true", " TRUE ", "1", "yes", "On"):
        monkeypatch.setenv(FLAG, raw)
        assert leaf.guard_enabled() is True, raw
    monkeypatch.delenv(FLAG, raising=False)
    assert leaf.guard_enabled() is False
    for raw in ("", "false", "0", "no", "off", "garbage", "tru e"):
        monkeypatch.setenv(FLAG, raw)
        assert leaf.guard_enabled() is False, raw


def test_r02_knob_table(monkeypatch):
    """A-R02 as amended by I1-R7: finite values clamp to 1..10 (truncated, spec 2.1);
    blank, garbage, inf and nan fall back to 5."""
    leaf = _leaf()
    monkeypatch.delenv(KNOB, raising=False)
    assert leaf.candidates_knob() == 5
    table = (
        ("", 5),
        ("abc", 5),
        ("inf", 5),
        ("-inf", 5),
        ("nan", 5),
        ("0", 1),
        ("-3", 1),
        ("0.5", 1),
        ("1", 1),
        (" 7 ", 7),
        ("7.9", 7),
        ("10", 10),
        ("11", 10),
        ("15", 10),
    )
    for raw, want in table:
        monkeypatch.setenv(KNOB, raw)
        assert leaf.candidates_knob() == want, (raw, want)


# (id, brand, line, category, texts, hosts, expected reason or None)
TRUTH = [
    (
        "T1",
        "",
        "Tyger",
        "fragrances",
        ("The Tyger by William Blake", "Poetry Foundation"),
        (POEM_PAGE,),
        "fragrance_word",
    ),
    ("T2", "", "Tyger", "fragrances", ("The Tyger",), (), "fragrance_word"),
    (
        "T3",
        "Bvlgari",
        "Tygar",
        "fragrances",
        ("Bulgari Le Gemme Tygar Eau de Parfum 125ml",),
        (),
        None,
    ),
    ("T4", "Bvlgari", "Tygar", "fragrances", ("BVLGARI TYGAR",), (), None),
    (
        "T5",
        "Dior",
        "Sauvage EDP",
        "fragrances",
        ("Sauvage Eau de Parfum",),
        ("https://www.dior.com/en_us/p/x",),
        None,
    ),
    (
        "T6",
        "Dior",
        "Sauvage",
        "fragrances",
        ("Sauvage Eau de Toilette", "Dior"),
        (),
        None,
    ),
    ("T7", "Dior", "Sauvage", "fragrances", ("Zara Sauvage Spray",), (), "brand"),
    (
        "T8",
        "Chanel",
        "Bleu de Chanel EDP",
        "fragrances",
        ("Chanel No 5 Eau de Parfum",),
        (),
        "name",
    ),
    ("T9", "", "Aventus", "fragrances", ("Creed Viking Eau de Parfum",), (), "name"),
    (
        "T10",
        LANCOME_ACC,
        IDOLE_ACC,
        "fragrances",
        ("Lancome Idole Eau de Parfum",),
        (),
        None,
    ),
    (
        "T10r",
        "Lancome",
        "Idole",
        "fragrances",
        (LANCOME_ACC + " " + IDOLE_ACC + " Eau de Parfum",),
        (),
        None,
    ),
    ("T11", "", "Tyger", "fragrances", ("Tyger " + AR_PERFUME,), (), None),
    (
        "T12",
        "Sefiki",
        "Limited Edition",
        "fragrances",
        ("Sefiki men watch",),
        (),
        "name",
    ),
    ("T13", "", "Shahrazad L'Intense", "fragrances", ("Violin",), (), "name"),
    ("T14", "", "Sauvage EDP", "fragrances", ("Bleu de Chanel EDP",), (), "name"),
    (
        "T15",
        "Chanel",
        "Bleu de Chanel",
        "fragrances",
        ("Chanel Coco Mademoiselle parfum",),
        (),
        "name",
    ),
    (
        "T16",
        "Parfums de Marly",
        "Layton",
        "fragrances",
        ("Layton parfums review",),
        (),
        "brand",
    ),
    ("T17", "Unknown", "Tyger", "fragrances", ("The Tyger",), (), "fragrance_word"),
    (
        "T18",
        "Dior",
        "Sauvage",
        "fragrances",
        ("Dior official site",),
        ("https://sauvage.dior.com/",),
        "name",
    ),
    # Spec 2.2 item 5: a host such as sauvage.example never proves the line (both arms).
    (
        "T18b",
        "Dior",
        "Sauvage",
        "fragrances",
        ("Dior official site",),
        ("https://sauvage.example/",),
        "name",
    ),
    (
        "T18c",
        "",
        "Sauvage",
        "fragrances",
        ("Eau de Parfum",),
        ("https://sauvage.example/",),
        "name",
    ),
    (
        "T19",
        "Tom Ford",
        "Ombre Leather",
        "fragrances",
        ("Ombre Leather Eau de Parfum",),
        ("https://www.tomford.com/x",),
        None,
    ),
    # I1-R2: no fragrance word for a non-fragrance category; still for "other".
    ("T20", "", "iPhone 15", "electronics", ("Apple iPhone 15 128GB",), (), None),
    (
        "T21",
        "",
        "Tyger",
        "other",
        ("The Tyger by William Blake",),
        (),
        "fragrance_word",
    ),
    # I1-R3: every significant line token when the brand is empty (review X1-X4).
    (
        "X1",
        "",
        "Bleu de Chanel EDP",
        "fragrances",
        ("Chanel No 5 Eau de Parfum",),
        (),
        "name",
    ),
    (
        "X1t",
        "",
        "Bleu de Chanel EDP",
        "fragrances",
        ("Chanel Bleu de Chanel Eau de Parfum",),
        (),
        None,
    ),
    (
        "X2",
        "",
        "stronger with you",
        "fragrances",
        ("Emporio Armani Because It's You Eau de Parfum",),
        (),
        "name",
    ),
    (
        "X2t",
        "",
        "stronger with you",
        "fragrances",
        ("Emporio Armani Stronger With You Eau de Toilette",),
        (),
        None,
    ),
    (
        "X3",
        "",
        "Dior Sauvage",
        "fragrances",
        ("Dior Homme Eau de Toilette",),
        (),
        "name",
    ),
    (
        "X4",
        "",
        "Aventus 100 ml",
        "fragrances",
        ("Creed Viking Eau de Parfum 100 ml",),
        (),
        "name",
    ),
    # I1-R4 (c): a number followed by a unit is no line token (spaced and attached).
    (
        "X4t",
        "",
        "Aventus 100 ml",
        "fragrances",
        ("Creed Aventus Eau de Parfum",),
        (),
        None,
    ),
    (
        "X11",
        "",
        "Aventus 100ml",
        "fragrances",
        ("Bleu de Chanel 100ml EDP",),
        (),
        "name",
    ),
    (
        "X11t",
        "",
        "Aventus 100ml",
        "fragrances",
        ("Creed Aventus Eau de Parfum",),
        (),
        None,
    ),
    # I1-R4 (a): host tokens are the registrable label only (no TLD, no www).
    (
        "X6",
        "Carolina Herrera",
        "Good Girl",
        "fragrances",
        ("Good Girl Gone Bad Eau de Parfum",),
        ("https://www.manor.ch/x",),
        "brand",
    ),
    # I1-R4 (b): a group expands only when the brand's kept tokens are its subset.
    (
        "X7",
        "Paris Hilton",
        "Heiress",
        "fragrances",
        ("Lancome Heiress Eau de Parfum",),
        (),
        "brand",
    ),
    (
        "X8",
        "Christian Louboutin",
        "Loubirouge",
        "fragrances",
        ("Dior Loubirouge Eau de Parfum",),
        (),
        "brand",
    ),
    # The review's X9 / X10 (I1-R20): STOP_WORDS and BRAND_NOISE are load-bearing.
    (
        "X9",
        "Armani",
        "Stronger With You",
        "fragrances",
        ("Armani perfume with vanilla notes",),
        (),
        "name",
    ),
    (
        "X10",
        "Maison Margiela",
        "Replica Jazz Club",
        "fragrances",
        ("Maison Francis Kurkdjian Baccarat Rouge 540",),
        (),
        "brand",
    ),
    ("X12", "", "Sauvage EDP", "fragrances", ("Sauvage",), (), "fragrance_word"),
    # A line with no significant token never passes (I1-3 (b) at least one token).
    (
        "E1",
        "",
        "Eau de Parfum",
        "fragrances",
        ("Creed Aventus Eau de Parfum",),
        (),
        "name",
    ),
]
# I1-R12: the plurals are fragrance words.
TRUTH += [
    ("P-" + str(i), "", "Tyger", "fragrances", ("Tyger " + word,), (), None)
    for i, word in enumerate(
        ("perfumes", "parfums", "fragrances", "colognes", AR_PERFUMES)
    )
]
# I1-R4 (c) with a known brand: the number before ml / oz / fl / g / gm is no line token.
TRUTH += [
    (
        "U-sp-" + unit,
        "Creed",
        "Aventus 50 " + unit,
        "fragrances",
        ("Creed Viking 50",),
        (),
        "name",
    )
    for unit in ("ml", "oz", "fl", "g", "gm")
]
TRUTH += [
    (
        "U-at-" + unit,
        "Creed",
        "Aventus 50" + unit,
        "fragrances",
        ("Creed Viking 50" + unit,),
        (),
        "name",
    )
    for unit in ("ml", "oz", "fl", "g", "gm")
]


@pytest.mark.parametrize(
    "brand,line,category,texts,hosts,expected",
    [row[1:] for row in TRUTH],
    ids=[row[0] for row in TRUTH],
)
def test_r03_relevance_truth_table(brand, line, category, texts, hosts, expected):
    """A-R03: check(identity(name, relevance), texts, hosts) per the amended table."""
    leaf = _leaf()
    rel = _rel(brand, line, category, 0)
    ident = leaf.identity((brand + " " + line).strip(), rel)
    assert leaf.check(ident, texts, hosts) == expected


def test_r04_image_query():
    """A-R04: the word perfume only for the fragrance category (spec 2.2 item 6)."""
    leaf = _leaf()
    cases = (
        ("Tyger", _rel("", "Tyger", "fragrances"), "Tyger perfume"),
        (
            "Dior Sauvage EDP",
            _rel("Dior", "Sauvage", "fragrances"),
            "Dior Sauvage EDP perfume",
        ),
        ("iPhone 15", _rel("", "iPhone 15", "electronics"), "iPhone 15"),
        ("X", _rel("", "X", "other"), "X"),
    )
    for product_name, rel, want in cases:
        ident = leaf.identity(product_name, rel)
        assert leaf.image_query(product_name, ident) == want, product_name


def test_r05_first_https_raster():
    """A-R05: the noon seam keeps the first https raster URL on a public, allowed host."""
    leaf = _leaf()
    n1 = _https("f.nooncdn.com", "/p/pzsku/ZT1/45/_/x1/a1.jpg?width=1200")
    n2 = _https("f.nooncdn.com", "/p/pzsku/ZT1/45/_/x2/a2.jpg?width=1200")
    n3 = _https("f.nooncdn.com", "/p/pzsku/ZT1/45/_/x3/a3.jpg?width=1200")
    assert leaf.first_https_raster([n1, n2, n3]) == n1
    b = _https("h.example.com", "/b.png")
    assert leaf.first_https_raster(["http://" + "h.example.com" + "/a.jpg", b]) == b
    c = _https("h.example.com", "/c.webp")
    assert leaf.first_https_raster([{"@type": "ImageObject", "url": c}]) == c
    d = _https("h.example.com", "/d.jpg")
    assert leaf.first_https_raster({"contentUrl": d}) == d
    assert leaf.first_https_raster([_https("h.example.com", "/e.svg")]) is None
    assert leaf.first_https_raster([_https("10.0.0.1", "/f.jpg")]) is None
    assert leaf.first_https_raster([FIMGS_IMG]) is None
    assert leaf.first_https_raster([_https("img.example.test", "/g.jpg")]) is None
    for junk in (None, 42, {}):
        assert leaf.first_https_raster(junk) is None, junk


def _module_level_nodes(tree):
    """Every node outside a function body (the module and class bodies)."""
    out = []
    stack = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        out.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return out


def test_r06_leaf_import_shape():
    """A-R06 as widened by I1-R1: module-level imports are __future__, the stdlib,
    category_gate, jsonld_widen and deny_hosts only; price_service only inside function
    bodies; no module-level logger; no string literal holding a host URL; pure ASCII."""
    leaf = _leaf()
    path = leaf.__file__
    with open(path, "rb") as fh:
        raw = fh.read()
    assert all(b < 128 for b in raw), "the leaf is not pure ASCII"
    tree = ast.parse(raw.decode("ascii"))
    allowed_app = {
        "app.services.category_gate",
        "app.services.jsonld_widen",
        "app.services.deny_hosts",
    }
    allowed_leaves = {"category_gate", "jsonld_widen", "deny_hosts"}
    stdlib = set(sys.stdlib_module_names)
    for node in _module_level_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert alias.name in allowed_app or root in stdlib, alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "__future__":
                continue
            if mod == "app.services":
                names = {a.name for a in node.names}
                assert names <= allowed_leaves, names
                continue
            assert mod in allowed_app or mod.split(".")[0] in stdlib, mod
        elif isinstance(node, ast.Call):
            func = node.func
            fname = getattr(func, "attr", None) or getattr(func, "id", None)
            assert fname != "getLogger", "a module-level logger in the leaf"
    inner_ps = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.ImportFrom) and (sub.module or "").endswith(
                    "price_service"
                ):
                    inner_ps = True
                if isinstance(sub, ast.ImportFrom) and sub.module == "app.services":
                    if any(a.name == "price_service" for a in sub.names):
                        inner_ps = True
                if isinstance(sub, ast.Import):
                    if any(a.name.endswith("price_service") for a in sub.names):
                        inner_ps = True
    assert inner_ps, "price_service is not imported inside a function body"
    host_url = re.compile(r"https?://[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not host_url.search(node.value), node.value


def test_r07_alias_reuse():
    """A-R07: the repository's alias groups plus the local {bvlgari, bulgari} (I1-R18)."""
    leaf = _leaf()
    assert leaf.EXTRA_ALIAS_GROUPS == (frozenset({"bvlgari", "bulgari"}),)
    assert (
        leaf.alias_groups() == tuple(_ps._BRAND_ALIAS_GROUPS) + leaf.EXTRA_ALIAS_GROUPS
    )


# ---------------------------------------------------------------------------
# RED rows: the cascade (each scenario is reused by the grammar row A-R14)
# ---------------------------------------------------------------------------


def _case_r08():
    return dict(
        name=NAME,
        rel=_rel("", "Tyger", "fragrances", 0),
        images=[POEM_ITEM],
        organic=[dict(POEM_ORGANIC)],
    )


def test_r08_tyger_poem_rejected_at_tier1(monkeypatch, caplog):
    """A-R08: the bare poem title fails the fragrance-word test; the query carries the
    word perfume and the knob default 5; no organic result passes, so no LLM call."""
    out, rec, pairs, lines = _run_case(monkeypatch, caplog, **_case_r08())
    assert out is None
    assert rec.search == [(("Tyger perfume",), {"num_results": 5})]
    assert rec.budget == [(1,)]
    assert rec.gpt == []
    assert ("serper_images", "miss") in pairs, pairs
    assert ("llm_pick", "skipped") in pairs, pairs
    assert lines == [_line(0, "serper_images", "rejected", 1, "fragrance_word")]


def _case_r09():
    return dict(
        name="Bvlgari Tygar",
        rel=_rel("Bvlgari", "Tygar", "fragrances", 1),
        payload={"knowledgeGraph": {"title": "The Tyger", "imageUrl": POEM}},
        images=[{"title": "Bulgari Tygar Eau de Parfum", "imageUrl": BOTTLE}],
    )


def test_r09_kg_poem_rejected_tier1_bottle_accepted(monkeypatch, caplog):
    """A-R09: the KG poem fails the brand test; the Bulgari-titled bottle passes."""
    out, rec, pairs, lines = _run_case(monkeypatch, caplog, **_case_r09())
    assert out == BOTTLE
    assert rec.search == [(("Bvlgari Tygar perfume",), {"num_results": 5})]
    assert ("search_payload", "miss") in pairs, pairs
    assert ("serper_images", "hit") in pairs, pairs
    assert lines == [_line(1, "serper_images", "accepted", 2, "none")]


def _walk_images():
    return [
        {"title": "The Tyger by William Blake", "imageUrl": POEM},
        {"title": "Bvlgari Tygar Eau de Parfum", "imageUrl": HTTP_BOTTLE},
        {"title": "Bvlgari Tygar Eau de Parfum", "imageUrl": BOTTLE_A},
        {"title": "Bvlgari Tygar Parfum", "imageUrl": BOTTLE_B},
    ]


def _case_r10(knob):
    return dict(
        name="Bvlgari Tygar",
        rel=_rel("Bvlgari", "Tygar", "fragrances", 0),
        knob=knob,
        images=_walk_images(),
    )


def test_r10_walk_order_and_knob(monkeypatch, caplog):
    """A-R10: the walk is in order, an http item is rejected for its scheme, and the
    knob sets both the request size and the walk cap."""
    out, rec, pairs, lines = _run_case(monkeypatch, caplog, **_case_r10("3"))
    assert out == BOTTLE_A
    assert rec.search[0][1] == {"num_results": 3}
    assert lines == [_line(0, "serper_images", "accepted", 3, "none")]
    out, rec, pairs, lines = _run_case(monkeypatch, caplog, **_case_r10("2"))
    assert out is None
    assert rec.search[0][1] == {"num_results": 2}
    assert lines == [_line(0, "serper_images", "rejected", 2, "scheme")]


def _case_r11a():
    return dict(
        name="Bvlgari Tygar",
        rel=_rel("Bvlgari", "Tygar", "fragrances", 0),
        piggy="http://" + "shop.example.com" + "/tygar.jpg",
        payload={
            "knowledgeGraph": {
                "title": "Bvlgari Tygar Eau de Parfum",
                "imageUrl": KG_IMG,
            }
        },
    )


def _case_r11b():
    return dict(
        name="Bvlgari Tygar",
        rel=_rel("Bvlgari", "Tygar", "fragrances", 0),
        payload={
            "knowledgeGraph": {
                "title": "Bvlgari Tygar Eau de Parfum",
                "imageUrl": "http://" + "kg.example.com" + "/t.jpg",
            }
        },
        images=[],
    )


def _case_r11c():
    return dict(
        name="Bvlgari Tygar",
        rel=_rel("Bvlgari", "Tygar", "fragrances", 0),
        granted=False,
        organic=[
            {
                "title": "Bvlgari Tygar Eau de Parfum",
                "link": _https("shop.example.com", "/tygar"),
                "snippet": "x",
            }
        ],
        gpt_url="http://" + "shop.example.com" + "/t.jpg",
    )


def test_r11_https_on_every_tier(monkeypatch, caplog):
    """A-R11: an http candidate is rejected on the piggyback, search-payload and Tier-3
    tiers (I1-5)."""
    out, rec, pairs, lines = _run_case(monkeypatch, caplog, **_case_r11a())
    assert out == KG_IMG
    assert pairs[:2] == [("piggyback", "miss"), ("search_payload", "hit")], pairs
    assert lines == [_line(0, "search_payload", "accepted", 2, "none")]
    out, rec, pairs, lines = _run_case(monkeypatch, caplog, **_case_r11b())
    assert out is None
    assert ("search_payload", "miss") in pairs, pairs
    assert lines == [_line(0, "search_payload", "rejected", 1, "scheme")]
    out, rec, pairs, lines = _run_case(monkeypatch, caplog, **_case_r11c())
    assert out is None
    assert len(rec.gpt) == 1
    assert ("llm_pick", "miss") in pairs, pairs
    assert lines == [_line(0, "llm_pick", "rejected", 1, "scheme")]


def _case_r12():
    organic = [
        {
            "title": "Creed Viking",
            "link": _https("shop.example.com", "/viking"),
            "imageUrl": _https("shop.example.com", "/viking.jpg"),
        },
        {
            "title": "Creed Aventus 100ml EDP",
            "link": SHOP_PAGE,
            "imageUrl": ORG_IMG,
        },
    ]
    return dict(
        name="Creed Aventus",
        rel=_rel("Creed", "Aventus", "fragrances", 0),
        payload={
            "knowledgeGraph": {"title": "Viking", "imageUrl": KG_IMG},
            "organic": organic,
        },
        organic=[dict(item) for item in organic],
    )


def test_r12_search_payload_each_item_tested(monkeypatch, caplog):
    """A-R12: the KG item (brand), the first organic item (name) and the second organic
    item (passes) are each tested in the base precedence; no paid tier runs."""
    out, rec, pairs, lines = _run_case(monkeypatch, caplog, **_case_r12())
    assert out == ORG_IMG
    assert rec.budget == [] and rec.search == [] and rec.gpt == []
    assert lines == [_line(0, "search_payload", "accepted", 3, "none")]


def _creed_tier3(organic, pick):
    return dict(
        name="Creed Aventus",
        rel=_rel("Creed", "Aventus", "fragrances", 0),
        granted=False,
        organic=organic,
        gpt_url=pick,
    )


AVENTUS_ORGANIC = {
    "title": "Creed Aventus Eau de Parfum",
    "link": SHOP_PAGE,
    "snippet": "x",
}


def test_r13_tier3_precondition_and_pick(monkeypatch, caplog):
    """A-R13: (a) no passing organic result = no LLM call; (b) a pick on a passing
    result's host is accepted and the call is unchanged; (c) a pick on an unrelated host
    is rejected (no related item: reason brand)."""
    viking = [{"title": "Creed Viking", "link": _https("shop.example.com", "/viking")}]
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_creed_tier3(viking, PICK)
    )
    assert out is None
    assert rec.gpt == []
    assert ("llm_pick", "skipped") in pairs, pairs
    assert lines == [_line(0, "none", "none", 0, "none")]
    organic = [dict(AVENTUS_ORGANIC)]
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_creed_tier3(organic, PICK)
    )
    assert out == PICK
    assert ("llm_pick", "hit") in pairs, pairs
    assert rec.gpt[0] == ("Creed Aventus", organic)
    assert lines == [_line(0, "llm_pick", "accepted", 1, "none")]
    other = _https("cdn.other.example.org", "/x.jpg")
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_creed_tier3([dict(AVENTUS_ORGANIC)], other)
    )
    assert out is None
    assert ("llm_pick", "miss") in pairs, pairs
    assert lines == [_line(0, "llm_pick", "rejected", 1, "brand")]


def _grammar_cases():
    """The paths of A-R08..A-R13 and of the ruling rows below."""
    return [
        _case_r08(),
        _case_r09(),
        _case_r10("3"),
        _case_r10("2"),
        _case_r11a(),
        _case_r11b(),
        _case_r11c(),
        _case_r12(),
        _creed_tier3([{"title": "Creed Viking", "link": SHOP_PAGE}], PICK),
        _creed_tier3([dict(AVENTUS_ORGANIC)], PICK),
        _creed_tier3(
            [dict(AVENTUS_ORGANIC)], _https("cdn.other.example.org", "/x.jpg")
        ),
        _deny_case("serper_frag"),
        _deny_case("organic_link"),
        _kg_type_case("tyger_poem"),
    ]


def test_r14_one_line_closed_grammar(monkeypatch, caplog):
    """A-R14: exactly one [IMG_RELEVANCE] record per call, each in the closed grammar,
    never a name, a URL, the query or a title; every [IMG_TIER] record keeps the INC-X2a
    grammar (checked inside _pairs)."""
    for case in _grammar_cases():
        out, rec, pairs, lines = _run_case(monkeypatch, caplog, **case)
        assert len(lines) == 1, (case.get("name"), lines)
        line = lines[0]
        assert REL_LINE.match(line), line
        assert "http" not in line, line
        assert case["name"] not in line, line
        assert "perfume" not in line, line
        for item in case.get("images") or []:
            if item.get("title"):
                assert item["title"] not in line, line


def test_r15_cancel_under_the_flag(monkeypatch, caplog):
    """A-R15: the 5 s race cancels a hanging Serper call under the guard: the X2a cancel
    line and exactly one [IMG_RELEVANCE] line (the finally), the cancellation re-raised.
    """
    _assert_kw()
    monkeypatch.setenv(FLAG, "true")
    rec = _Rec()
    _install(monkeypatch, rec, hang=True)
    caplog.set_level(logging.INFO, logger=LOGGER)
    caplog.clear()
    outcome = {}

    async def _go():
        try:
            await asyncio.wait_for(
                img.get_product_image_url(
                    NAME,
                    region="bahrain",
                    page_scrape_image=None,
                    organic_results=None,
                    search_payload=None,
                    relevance=_rel("", "Tyger", "fragrances", 0),
                ),
                0.05,
            )
            outcome["r"] = "returned"
        except asyncio.TimeoutError:
            outcome["r"] = "timeout"

    asyncio.run(_go())
    assert outcome["r"] == "timeout"
    cancels = [
        ln
        for ln in _messages(caplog, "[IMG_TIER]")
        if ln.startswith("[IMG_TIER] cancelled")
    ]
    assert len(cancels) == 1, cancels
    assert (
        CANCEL.match(cancels[0])
        and CANCEL.match(cancels[0]).group(1) == "serper_images"
    )
    assert _messages(caplog, "[IMG_RELEVANCE]") == [_line(0, "none", "none", 0, "none")]
    assert rec.cancelled == ["search"]
    assert rec.gpt == []


@pytest.mark.parametrize("flag", [None, "false", "0", "garbage"])
def test_r16_flag_off_with_relevance_is_the_base_call(monkeypatch, caplog, flag):
    """A-R16 (F2): flag OFF with `relevance` GIVEN and the knob set is the base call:
    images[0], one credit, the bare name with num_results 1, no new line, no knob read.
    """
    _assert_kw()
    leaf = _leaf()
    knob_reads = []

    def _knob():
        knob_reads.append(1)
        raise RuntimeError("the knob was read with the flag OFF")

    monkeypatch.setattr(leaf, "candidates_knob", _knob)
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        flag=flag,
        knob="7",
        rel=_rel("", "Tyger", "fragrances", 0),
        images=[dict(POEM_ITEM)],
    )
    assert out == POEM
    assert rec.budget == [(1,)]
    assert rec.search == [((NAME,), {"num_results": 1})]
    assert rec.order == ["budget", "search"]
    assert pairs == BASE_PAIRS
    assert lines == []
    assert knob_reads == []


# ---------------------------------------------------------------------------
# RED rows added by the rulings
# ---------------------------------------------------------------------------

TYGAR_TITLE = "Tygar Bvlgari cologne for men"


def _deny_case(kind, dg=None):
    rel = _rel("", "Tygar", "fragrances", 0)
    base = dict(name="Tygar", rel=rel, dg=dg)
    if kind == "serper_frag":
        base["images"] = [
            {
                "title": TYGAR_TITLE,
                "source": FRAG_SOURCE,
                "link": FRAG_PAGE,
                "imageUrl": SAFE_IMG,
            }
        ]
    elif kind == "serper_image_url":
        base["images"] = [
            {
                "title": TYGAR_TITLE,
                "source": "Shop",
                "link": _https("shop.example.com", "/tygar"),
                "imageUrl": FIMGS_IMG,
            }
        ]
    elif kind == "serper_link":
        base["images"] = [
            {
                "title": TYGAR_TITLE,
                "source": "Shop",
                "link": FRAG_PAGE,
                "imageUrl": SAFE_IMG,
            }
        ]
    elif kind == "serper_source":
        base["images"] = [
            {
                "title": TYGAR_TITLE,
                "source": FRAG_SOURCE,
                "link": _https("shop.example.com", "/tygar"),
                "imageUrl": SAFE_IMG,
            }
        ]
    elif kind == "serper_domain":
        base["images"] = [
            {
                "title": TYGAR_TITLE,
                "source": "Shop",
                "domain": FRAG_DOMAIN,
                "imageUrl": SAFE_IMG,
            }
        ]
    elif kind == "kg_image_url":
        base.update(
            granted=False,
            payload={"knowledgeGraph": {"title": TYGAR_TITLE, "imageUrl": FIMGS_IMG}},
        )
    elif kind == "organic_link":
        base.update(
            granted=False,
            payload={
                "organic": [
                    {"title": TYGAR_TITLE, "link": FRAG_PAGE, "imageUrl": SAFE_IMG}
                ]
            },
        )
    elif kind == "images_source":
        base.update(
            granted=False,
            payload={
                "images": [
                    {"title": TYGAR_TITLE, "source": FRAG_SOURCE, "imageUrl": SAFE_IMG}
                ]
            },
        )
    elif kind == "piggyback":
        base.update(granted=False, piggy=FIMGS_IMG)
    else:
        raise AssertionError(kind)
    return base


DENY_TIER = {
    "serper_frag": "serper_images",
    "serper_image_url": "serper_images",
    "serper_link": "serper_images",
    "serper_source": "serper_images",
    "serper_domain": "serper_images",
    "kg_image_url": "search_payload",
    "organic_link": "search_payload",
    "images_source": "search_payload",
    "piggyback": "piggyback",
}


@pytest.mark.parametrize("kind", sorted(DENY_TIER))
def test_r17_denied_candidate_rejected_on_every_tier(monkeypatch, caplog, kind):
    """I1-R1 (DG OFF, the production mix): a candidate that passes the relevance test
    is rejected when its image URL, link host, domain or source is denied; reason denied.
    """
    out, rec, pairs, lines = _run_case(monkeypatch, caplog, **_deny_case(kind))
    assert out is None
    assert lines == [_line(0, DENY_TIER[kind], "rejected", 1, "denied")]


@pytest.mark.parametrize("dg", [None, "true"])
def test_r18_fragrantica_item_rejected_in_both_guard_states(monkeypatch, caplog, dg):
    """I1-R1: the review's X5 shape (it passes the relevance test) is rejected with
    ENABLE_DATA_GUARDS_V2 OFF and ON."""
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_deny_case("serper_frag", dg)
    )
    assert out is None
    assert ("serper_images", "miss") in pairs, pairs
    assert lines == [_line(0, "serper_images", "rejected", 1, "denied")]


@pytest.mark.parametrize("dg", [None, "true"])
def test_r19_denied_organic_never_opens_tier3(monkeypatch, caplog, dg):
    """I1-R1: a denied organic result that passes the relevance test does not satisfy
    the Tier-3 precondition (no LLM call), in both guard states."""
    organic = [{"title": TYGAR_TITLE, "link": FRAG_PAGE, "snippet": "x"}]
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        name="Tygar",
        rel=_rel("", "Tygar", "fragrances", 0),
        dg=dg,
        granted=False,
        organic=organic,
        gpt_url=_https("img.example.com", "/tygar.jpg"),
    )
    assert out is None
    assert rec.gpt == []
    assert ("llm_pick", "skipped") in pairs, pairs
    assert lines == [_line(0, "none", "none", 0, "none")]


def _kg_type_case(kind):
    if kind == "sauvage_perfume":
        rel = _rel("", "Sauvage EDP", "fragrances", 0)
        kg = {"title": "Sauvage", "type": "Perfume", "imageUrl": KG_IMG}
        name = "Sauvage EDP"
    elif kind == "tyger_poem":
        rel = _rel("", "Tyger", "fragrances", 0)
        kg = {"title": "The Tyger", "type": "Poem", "imageUrl": POEM}
        name = NAME
    elif kind == "type_never_the_line":
        rel = _rel("", "Sauvage", "fragrances", 0)
        kg = {
            "title": "Dior Eau de Parfum",
            "type": "Sauvage perfume",
            "imageUrl": KG_IMG,
        }
        name = "Sauvage"
    elif kind == "type_never_the_brand":
        rel = _rel("Dior", "Sauvage", "fragrances", 0)
        kg = {
            "title": "Sauvage Eau de Toilette",
            "type": "Dior perfume",
            "imageUrl": KG_IMG,
        }
        name = "Dior Sauvage"
    else:
        raise AssertionError(kind)
    return dict(name=name, rel=rel, granted=False, payload={"knowledgeGraph": kg})


def test_r20_kg_type_serves_the_fragrance_word_only(monkeypatch, caplog):
    """I1-R5: the knowledge graph's type text may satisfy the fragrance-word test only,
    never the brand or the line test."""
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_kg_type_case("sauvage_perfume")
    )
    assert out == KG_IMG
    assert lines == [_line(0, "search_payload", "accepted", 1, "none")]
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_kg_type_case("tyger_poem")
    )
    assert out is None
    assert lines == [_line(0, "search_payload", "rejected", 1, "fragrance_word")]
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_kg_type_case("type_never_the_line")
    )
    assert out is None
    assert lines == [_line(0, "search_payload", "rejected", 1, "name")]
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_kg_type_case("type_never_the_brand")
    )
    assert out is None
    assert lines == [_line(0, "search_payload", "rejected", 1, "brand")]


def test_r21_tier3_pick_needs_a_raster_path_and_is_no_page(monkeypatch, caplog):
    """I1-R10: a Tier-3 pick without a raster path (the repository's extension set,
    judged on the path) is rejected, a pick equal to an organic link is rejected, and a
    raster path with a query string is accepted."""
    organic = [dict(AVENTUS_ORGANIC)]
    for bad in (
        _https("img.shop.example.com", "/aventus.svg"),
        _https("img.shop.example.com", "/aventus"),
    ):
        out, rec, pairs, lines = _run_case(
            monkeypatch, caplog, **_creed_tier3([dict(item) for item in organic], bad)
        )
        assert out is None, bad
        assert ("llm_pick", "miss") in pairs, (bad, pairs)
        assert len(lines) == 1 and REL_LINE.match(lines[0]), lines
        assert " tier=llm_pick outcome=rejected candidates=1 " in lines[0], lines
    page_like = _https("shop.example.com", "/p/aventus.png")
    linked = [
        {"title": "Creed Aventus Eau de Parfum", "link": page_like, "snippet": "x"}
    ]
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_creed_tier3(linked, page_like)
    )
    assert out is None
    assert ("llm_pick", "miss") in pairs, pairs
    assert len(lines) == 1 and " outcome=rejected candidates=1 " in lines[0], lines
    query_pick = _https("img.shop.example.com", "/aventus.webp?w=600")
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        **_creed_tier3([dict(item) for item in organic], query_pick),
    )
    assert out == query_pick
    assert lines == [_line(0, "llm_pick", "accepted", 1, "none")]


def test_r22_tier3_reads_organic_first_ten(monkeypatch, caplog):
    """I1-R20: the Tier-3 precondition and the related-host test read organic[:10]
    (the model's view, img:173)."""
    fillers = [
        {
            "title": "Creed Viking",
            "link": _https("fill%d.example.org" % i, "/v"),
            "snippet": "x",
        }
        for i in range(10)
    ]
    late = {"title": "Creed Aventus Eau de Parfum", "link": SHOP_PAGE, "snippet": "x"}
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, **_creed_tier3([dict(f) for f in fillers] + [late], PICK)
    )
    assert rec.gpt == [], "an organic result past the first ten opened Tier 3"
    assert ("llm_pick", "skipped") in pairs, pairs
    assert out is None
    first = dict(AVENTUS_ORGANIC)
    late_related = {
        "title": "Creed Aventus EDP",
        "link": _https("other.example.net", "/aventus"),
        "snippet": "x",
    }
    organic = [first] + [dict(f) for f in fillers[:9]] + [late_related]
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        **_creed_tier3(organic, _https("cdn.other.example.net", "/x.jpg")),
    )
    assert len(rec.gpt) == 1
    assert (
        out is None
    ), "a pick related only to the eleventh organic result was accepted"
    assert lines == [_line(0, "llm_pick", "rejected", 1, "brand")]


def test_r23_tier3_related_but_failing_item_reason(monkeypatch, caplog):
    """Review C-2 (I1-R20): a pick whose related organic item fails logs that item's
    reason (here name), not the empty-text reason."""
    organic = [
        dict(AVENTUS_ORGANIC),
        {
            "title": "Creed Viking",
            "link": _https("other.example.org", "/viking"),
            "snippet": "x",
        },
    ]
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        **_creed_tier3(organic, _https("cdn.other.example.org", "/x.jpg")),
    )
    assert out is None
    assert lines == [_line(0, "llm_pick", "rejected", 1, "name")]


def test_r24_brand_from_source_link_or_domain(monkeypatch, caplog):
    """I1-3 / review C-2: the brand may come from the source text, the link host or the
    domain of a Serper item, and from the domain of an images-block item."""
    rel = _rel("Dior", "Sauvage", "fragrances", 0)
    title = "Sauvage Eau de Parfum"
    tier1_items = (
        {"title": title, "source": "Dior", "imageUrl": DIOR_IMG},
        {
            "title": title,
            "link": "https://www.dior.com/en_us/p/sauvage",
            "imageUrl": DIOR_IMG,
        },
        {"title": title, "domain": "www.dior.com", "imageUrl": DIOR_IMG},
    )
    for item in tier1_items:
        out, rec, pairs, lines = _run_case(
            monkeypatch, caplog, name="Dior Sauvage", rel=rel, images=[item]
        )
        assert out == DIOR_IMG, item
        assert lines == [_line(0, "serper_images", "accepted", 1, "none")], item
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        name="Dior Sauvage",
        rel=rel,
        images=[{"title": title, "imageUrl": DIOR_IMG}],
    )
    assert out is None
    assert lines == [_line(0, "serper_images", "rejected", 1, "brand")]
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        name="Dior Sauvage",
        rel=rel,
        granted=False,
        payload={
            "images": [{"title": title, "domain": "www.dior.com", "imageUrl": DIOR_IMG}]
        },
    )
    assert out == DIOR_IMG
    assert lines == [_line(0, "search_payload", "accepted", 1, "none")]


def test_r25_kg_https_preference_and_snake_key(monkeypatch, caplog):
    """Review C-2 (I1-R20): an item carrying an http and an https image key gives the
    https one; the snake_case knowledge_graph key is read too."""
    rel = _rel("Creed", "Aventus", "fragrances", 0)
    https_hero = _https("kg.example.com", "/a2.jpg")
    kg = {
        "title": "Creed Aventus Eau de Parfum",
        "imageUrl": "http://" + "kg.example.com" + "/a.jpg",
        "image": https_hero,
    }
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        name="Creed Aventus",
        rel=rel,
        granted=False,
        payload={"knowledgeGraph": kg},
    )
    assert out == https_hero
    assert lines == [_line(0, "search_payload", "accepted", 1, "none")]
    snake = {"title": "Creed Aventus Eau de Parfum", "imageUrl": KG_IMG}
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        name="Creed Aventus",
        rel=rel,
        granted=False,
        payload={"knowledge_graph": snake},
    )
    assert out == KG_IMG
    assert lines == [_line(0, "search_payload", "accepted", 1, "none")]
    thumb = _https("shop.example.com", "/aventus-t.jpg")
    organic_item = {
        "title": "Creed Aventus EDP",
        "link": SHOP_PAGE,
        "imageUrl": "http://" + "shop.example.com" + "/aventus.jpg",
        "thumbnailUrl": thumb,
    }
    out, rec, pairs, lines = _run_case(
        monkeypatch,
        caplog,
        name="Creed Aventus",
        rel=rel,
        granted=False,
        payload={"organic": [organic_item]},
    )
    assert out == thumb
    assert lines == [_line(0, "search_payload", "accepted", 1, "none")]


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------


def test_p01_base_call_full_config(monkeypatch, caplog):
    """A-P01: flag unset, knob set, no `relevance`: the base call, the X2a grammar."""
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, flag=None, knob="7", images=[dict(POEM_ITEM)]
    )
    assert out == POEM
    assert rec.budget == [(1,)]
    assert rec.search == [((NAME,), {"num_results": 1})]
    assert rec.order == ["budget", "search"]
    assert pairs == BASE_PAIRS
    assert lines == []


def test_p02_flag_on_without_identity_is_the_base_call(monkeypatch, caplog):
    """A-P02 (F3): flag ON, knob set, NO `relevance` (the camera / legacy caller)."""
    out, rec, pairs, lines = _run_case(
        monkeypatch, caplog, flag="true", knob="7", images=[dict(POEM_ITEM)]
    )
    assert out == POEM
    assert rec.budget == [(1,)]
    assert rec.search == [((NAME,), {"num_results": 1})]
    assert rec.order == ["budget", "search"]
    assert pairs == BASE_PAIRS
    assert lines == []


def test_p03_base_search_payload_function_untouched(monkeypatch):
    """A-P03 (F4): extract_image_from_search keeps the base rule (no title test, no deny
    with ENABLE_DATA_GUARDS_V2 OFF) with the guard flag ON."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(KNOB, "7")
    kg = {"knowledgeGraph": {"title": "The Tyger", "imageUrl": POEM}}
    assert img.extract_image_from_search(kg) == POEM
    organic = {"organic": [{"title": "x", "link": FRAG_PAGE, "imageUrl": SAFE_IMG}]}
    assert img.extract_image_from_search(organic) == SAFE_IMG


def test_p04_shared_validator_untouched(monkeypatch):
    """A-P04 (F4): _is_valid_image_url keeps http and, with ENABLE_DATA_GUARDS_V2 OFF, a
    banned image host (kb_serve.py:323 and the override depend on it); DG ON denies it.
    """
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(KNOB, "7")
    assert img._is_valid_image_url("http://" + "x.example.com" + "/a.jpg") is True
    assert img._is_valid_image_url(FIMGS_IMG) is True
    monkeypatch.setenv(DG, "true")
    assert img._is_valid_image_url(FIMGS_IMG) is False
