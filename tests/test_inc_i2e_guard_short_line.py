"""INC-I2e GUARD-SHORT-LINE (S96 main lane) RED file: the short-line rules of the
picture relevance guard app/services/image_relevance.check.

Spec: INC_I2E_UNIT_SPEC.md (S96, 2026-11-16) sections 2 (the contract), 4 (the flag
mixes) and 5 (the rows). New dark flag ENABLE_IMAGE_GUARD_SHORT_LINE (default OFF, read
PER CALL inside ``check``; it has an effect only where ``check`` runs, i.e. under
ENABLE_IMAGE_RELEVANCE_GUARD). With it ON a line with no significant token once the
brand is known (``Y``, ``M``, ``L'Eau d'Issey``, the numbered ``N5`` forms) is matched
by the numero fold, its short tokens and its adjacent-pair joins; OFF is the base
behaviour byte for byte.

RED rows (test_e*) fail at base on an AssertionError only: the new symbols are read
through getattr helpers. PIN rows (test_p*) are green at base: P1 records the BASE
reasons as literals (measured at b0ad2603) and runs them with the full configuration
(the guard ON, the knob set, the new flag OFF in several spellings); P2 documents the
hazard; P3 proves the new flag is never read with the guard OFF (a getenv recorder);
P4 pins the leaf's module-level imports.

Hermetic: the three tier callables of image_service are patched on the module (the
INC-I1 seams); no network, no Redis, no LLM. Non-ASCII characters are built with chr().
Pure ASCII, LF.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import os

import pytest

from app.services import image_relevance as leaf
from app.services import image_service as img

LOGGER = "app.services.image_service"
G = "ENABLE_IMAGE_RELEVANCE_GUARD"
S = "ENABLE_IMAGE_GUARD_SHORT_LINE"
R = "ENABLE_PRODUCT_RESOLVER"
KNOB = "IMAGE_RELEVANCE_CANDIDATES"
DG = "ENABLE_DATA_GUARDS_V2"
V2 = "ENABLE_IMAGE_PIPELINE_V2"

DEG = chr(0xB0)  # the degree sign of "N<deg>5"
ORD = chr(0xBA)  # the masculine ordinal of "N<ord>5"
N5_DEG = "N" + DEG + "5"
N5_ORD = "N" + ORD + "5"


def _https(host, path):
    return "https://" + host + path


M_IMG = _https("img.example.com", "/ted-baker-m.jpg")
WOMAN_IMG = _https("img.example.com", "/ted-baker-woman.jpg")

# (row, brand, line, category, texts, expected with the new flag ON, BASE reason)
# The BASE column was recorded by running check(identity(brand + " " + line, rel),
# texts, ()) at b0ad2603 (the flag does not exist there).
CASES = [
    # E1 YSL Y
    (
        "E1",
        "Yves Saint Laurent",
        "Y",
        "fragrances",
        ("Yves Saint Laurent Y Eau de Parfum 100ml",),
        None,
        "name",
    ),
    ("E1", "Yves Saint Laurent", "Y", "fragrances", ("YSL Y EDP",), None, "name"),
    (
        "E1",
        "Yves Saint Laurent",
        "Y",
        "fragrances",
        ("Yves Saint Laurent Libre Eau de Parfum",),
        "name",
        "name",
    ),
    # E1 (rule 1b: EVERY short token, not any): a two-short-token line.
    (
        "E1",
        "Yves Saint Laurent",
        "Y 2",
        "fragrances",
        ("Yves Saint Laurent Y 2 Eau de Parfum",),
        None,
        "name",
    ),
    (
        "E1",
        "Yves Saint Laurent",
        "Y 2",
        "fragrances",
        ("Yves Saint Laurent Y Eau de Parfum",),
        "name",
        "name",
    ),
    # E2 Ted Baker M
    (
        "E2",
        "Ted Baker",
        "M",
        "fragrances",
        ("Ted Baker M Eau de Toilette 100 ml",),
        None,
        "name",
    ),
    (
        "E2",
        "Ted Baker",
        "M",
        "fragrances",
        ("Ted Baker Woman Eau de Toilette",),
        "name",
        "name",
    ),
    # E3 L'Eau d'Issey (the elision letters are not short tokens; the joins decide)
    (
        "E3",
        "Issey Miyake",
        "L'Eau d'Issey",
        "fragrances",
        ("Issey Miyake L'Eau d'Issey Eau de Toilette",),
        None,
        "name",
    ),
    (
        "E3",
        "Issey Miyake",
        "L'Eau d'Issey",
        "fragrances",
        ("Issey Miyake Nuit d'Issey Eau de Parfum",),
        "name",
        "name",
    ),
    (
        "E3",
        "Issey Miyake",
        "L'Eau d'Issey",
        "fragrances",
        ("Issey Miyake Nuit d'Issey L'Homme Eau de Parfum",),
        "name",
        "name",
    ),
]

# E4 Chanel N5: three spellings of the line against four titles.
_E4_TITLES = (
    ("CHANEL " + N5_DEG + " Eau de Parfum", None),
    ("Chanel No.5 EDP", None),
    ("Chanel N5 Parfum", None),
    ("Chanel No 19 Eau de Parfum", "name"),
)
_E4_BASE = {
    N5_DEG: ("name", "name", "name", "name"),
    "No 5": ("name", None, "name", None),
    N5_ORD: ("name", "name", "name", "name"),
}
for _line in (N5_DEG, "No 5", N5_ORD):
    for (_title, _on), _base in zip(_E4_TITLES, _E4_BASE[_line], strict=True):
        CASES.append(("E4", "Chanel", _line, "fragrances", (_title,), _on, _base))

CASES += [
    # E5 joined spellings, both ways
    (
        "E5",
        "Dior",
        "J'adore",
        "fragrances",
        ("Dior Jadore Eau de Parfum",),
        None,
        "name",
    ),
    (
        "E5",
        "Dolce & Gabbana",
        "Light Blue",
        "fragrances",
        ("Dolce Gabbana Lightblue EDT",),
        None,
        "name",
    ),
    (
        "E5",
        "Dolce & Gabbana",
        "Lightblue",
        "fragrances",
        ("Dolce & Gabbana Light Blue Eau de Toilette",),
        None,
        "name",
    ),
    # E5: a candidate pair never joins across two texts (title, source).
    (
        "E5",
        "Dolce & Gabbana",
        "Lightblue",
        "fragrances",
        ("Dolce & Gabbana Light", "Blue Perfume Shop"),
        "name",
        "name",
    ),
    # E6 nothing of the line to match
    (
        "E6",
        "Chanel",
        "Eau de Parfum",
        "fragrances",
        ("Chanel Eau de Parfum 100ml",),
        None,
        "name",
    ),
    (
        "E6",
        "Chanel",
        "Eau de Parfum",
        "fragrances",
        ("Chanel Coco handbag",),
        "fragrance_word",
        "name",
    ),
    (
        "E6",
        "Chanel",
        "Eau de Parfum",
        "electronics",
        ("Chanel Eau de Parfum 100ml",),
        "name",
        "name",
    ),
    # E7 empty brand (the typed path)
    (
        "E7",
        "",
        "Chanel " + N5_DEG,
        "fragrances",
        ("CHANEL " + N5_DEG + " Eau de Parfum",),
        None,
        None,
    ),
    (
        "E7",
        "",
        "Chanel " + N5_DEG,
        "fragrances",
        ("Chanel No 19 Eau de Parfum",),
        "name",
        None,
    ),
    (
        "E7",
        "",
        "Dior Jadore",
        "fragrances",
        ("Dior J'adore Eau de Parfum",),
        None,
        "name",
    ),
]

# P2: the resolver-shaped identities (brand = the house, line = the line) and every
# title E1-E4 lists for them; G ON and S OFF refuse each one with "name".
HAZARD = [
    (
        "Yves Saint Laurent",
        "Y",
        (
            "Yves Saint Laurent Y Eau de Parfum 100ml",
            "YSL Y EDP",
            "Yves Saint Laurent Libre Eau de Parfum",
        ),
    ),
    (
        "Ted Baker",
        "M",
        ("Ted Baker M Eau de Toilette 100 ml", "Ted Baker Woman Eau de Toilette"),
    ),
    (
        "Issey Miyake",
        "L'Eau d'Issey",
        (
            "Issey Miyake L'Eau d'Issey Eau de Toilette",
            "Issey Miyake Nuit d'Issey Eau de Parfum",
        ),
    ),
    ("Chanel", N5_DEG, tuple(t for t, _ in _E4_TITLES)),
    ("Chanel", N5_ORD, tuple(t for t, _ in _E4_TITLES)),
]


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    """conftest loads the developer .env with override: every flag a row reads is
    deleted here and set by the row itself."""
    for name in (G, S, R, KNOB, DG, V2):
        monkeypatch.delenv(name, raising=False)


def _sym(name):
    value = getattr(leaf, name, None)
    assert value is not None, "INC-I2e not built: image_relevance.%s is missing" % name
    return value


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _rel(brand, line, category="fragrances", slot=0):
    return {"brand": brand, "line": line, "category": category, "slot": slot}


def _reason(brand, line, category, texts):
    ident = leaf.identity((brand + " " + line).strip(), _rel(brand, line, category))
    return leaf.check(ident, texts, ())


def _rows(row):
    out = [case for case in CASES if case[0] == row]
    assert out, row
    return out


def _assert_on(monkeypatch, row):
    monkeypatch.setenv(S, "true")
    for _row, brand, line, category, texts, on, _base in _rows(row):
        got = _reason(brand, line, category, texts)
        assert got == on, (row, brand, ascii(line), category, ascii(texts), got)


class _Rec:
    def __init__(self):
        self.budget = []
        self.search = []
        self.gpt = []


def _install(monkeypatch, rec, *, images):
    def _budget(n):
        rec.budget.append((n,))
        return True

    async def _search(query, **kwargs):
        rec.search.append(((query,), dict(kwargs)))
        return {"images": [dict(item) for item in images]}

    async def _gpt(name, organic):
        rec.gpt.append((name, organic))
        return None

    monkeypatch.setattr(img, "try_consume_serper_image_credit", _budget)
    monkeypatch.setattr(img, "search_images", _search)
    monkeypatch.setattr(img, "extract_image_via_gpt", _gpt)


def _relevance_lines(caplog):
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == LOGGER and r.getMessage().startswith("[IMG_RELEVANCE]")
    ]


def _line(slot, tier, outcome, n, reason):
    return "[IMG_RELEVANCE] product=%s tier=%s outcome=%s candidates=%d reason=%s" % (
        slot,
        tier,
        outcome,
        n,
        reason,
    )


def _getenv_recorder(monkeypatch):
    real = os.getenv
    seen = []

    def _rec(key, default=None):
        seen.append(key)
        return real(key, default)

    monkeypatch.setattr(os, "getenv", _rec)
    return seen


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------


def test_e1_ysl_y_one_letter_line(monkeypatch):
    """E1: brand Yves Saint Laurent, line Y: the letter matches as a standalone token
    (the alias YSL proves the brand); another line of the house is refused; a line of
    two short tokens needs EVERY one (rule 1b)."""
    _assert_on(monkeypatch, "E1")


def test_e2_ted_baker_m_elision_letter_whole_line(monkeypatch):
    """E2: line M (an elision letter kept because it is the whole line)."""
    _assert_on(monkeypatch, "E2")


def test_e3_l_eau_d_issey_joins(monkeypatch):
    """E3: L'Eau d'Issey: no significant token, no short token (l and d are elision
    letters), the joins leau / eaud decide; dissey is never a join (issey is a brand
    form), so Nuit d'Issey is refused even when it carries a standalone l and d."""
    _assert_on(monkeypatch, "E3")


def test_e4_chanel_numero_fold(monkeypatch):
    """E4: N<deg>5, No 5 and N<ord>5 all fold to no5 on both sides; No 19 is
    refused. Then the fold itself (spec section 2 NUMERO FOLD)."""
    _assert_on(monkeypatch, "E4")
    fold = _sym("fold_numero")
    table = (
        (["n", "5"], ["no5"]),
        (["no", "5"], ["no5"]),
        (["nr", "5"], ["no5"]),
        (["no5"], ["no5"]),
        (["n5"], ["no5"]),
        (["nr5"], ["no5"]),
        (["no", "19"], ["no19"]),
        (["chanel", "n", "5", "eau"], ["chanel", "no5", "eau"]),
        (["n", "5", "5"], ["no5", "5"]),
        (["n"], ["n"]),
        (["no"], ["no"]),
        (["n", "x"], ["n", "x"]),
        (["5"], ["5"]),
        (["nob5"], ["nob5"]),
        ([], []),
    )
    for tokens, want in table:
        assert list(fold(list(tokens))) == want, (tokens, want)
    for text in (N5_DEG, N5_ORD, "No.5", "No 5", "No5", "N5"):
        assert list(fold(leaf._cg.normalize(text))) == ["no5"], ascii(text)


def test_e5_joined_spellings_both_ways(monkeypatch):
    """E5: J'adore vs Jadore, Light Blue vs Lightblue and the reverse; a pair never
    joins across two texts."""
    _assert_on(monkeypatch, "E5")


def test_e6_nothing_of_the_line_to_match(monkeypatch):
    """E6: line Eau de Parfum: the fragrance word decides for fragrances; any other
    category -> name."""
    _assert_on(monkeypatch, "E6")


def test_e7_empty_brand_numero_and_joins(monkeypatch):
    """E7: the typed path (brand empty): Chanel N<deg>5 needs no5 (No 19 is now
    refused: the stated stricter change); Dior Jadore is covered by the join."""
    _assert_on(monkeypatch, "E7")


def test_e8_end_to_end_ted_baker_m(monkeypatch, caplog):
    """E8: through relevance_kwargs, RelevanceCall and get_product_image_url with a fake
    Serper Images payload: S ON returns the matching picture (accepted / serper_images),
    S OFF returns None with reason name."""
    monkeypatch.setenv(G, "true")
    monkeypatch.setenv(KNOB, "5")
    images = [
        {"title": "Ted Baker Woman Eau de Toilette", "imageUrl": WOMAN_IMG},
        {"title": "Ted Baker M Eau de Toilette 100 ml", "imageUrl": M_IMG},
    ]
    results = {}
    for s_value in ("true", None):
        _set(monkeypatch, S, s_value)
        kw = leaf.relevance_kwargs("Ted Baker", "M", "fragrances", 0, False)
        assert set(kw) == {"relevance"}, kw
        rec = _Rec()
        _install(monkeypatch, rec, images=images)
        caplog.set_level(logging.INFO, logger=LOGGER)
        caplog.clear()
        out = asyncio.run(
            img.get_product_image_url(
                "Ted Baker M",
                region="bahrain",
                page_scrape_image=None,
                organic_results=None,
                search_payload=None,
                **kw,
            )
        )
        results[s_value] = (out, _relevance_lines(caplog), rec)
    out, lines, rec = results["true"]
    assert out == M_IMG, out
    assert lines == [_line(0, "serper_images", "accepted", 2, "none")], lines
    assert rec.search == [(("Ted Baker M perfume",), {"num_results": 5})], rec.search
    assert rec.gpt == []
    out, lines, rec = results[None]
    assert out is None, out
    assert lines == [_line(0, "serper_images", "rejected", 2, "name")], lines
    assert rec.gpt == []


def test_e9_flag_read_per_call(monkeypatch):
    """E9: the flag is read inside check on every call: one identity, both answers in
    both build orders; then the reader is the house idiom."""
    title = ("Ted Baker M Eau de Toilette 100 ml",)
    monkeypatch.delenv(S, raising=False)
    ident = leaf.identity("Ted Baker M", _rel("Ted Baker", "M"))
    monkeypatch.setenv(S, "true")
    assert leaf.check(ident, title, ()) is None
    monkeypatch.delenv(S, raising=False)
    assert leaf.check(ident, title, ()) == "name"
    monkeypatch.setenv(S, " On ")
    assert leaf.check(ident, title, ()) is None
    monkeypatch.setenv(S, "false")
    assert leaf.check(ident, title, ()) == "name"
    monkeypatch.setenv(S, "TRUE")
    built_on = leaf.identity("Ted Baker M", _rel("Ted Baker", "M"))
    assert leaf.check(built_on, title, ()) is None
    monkeypatch.delenv(S, raising=False)
    assert leaf.check(built_on, title, ()) == "name"
    assert _sym("SHORT_LINE_FLAG_ENV") == S
    reader = _sym("short_line_enabled")
    for raw in ("true", " TRUE ", "1", "yes", "On"):
        monkeypatch.setenv(S, raw)
        assert reader() is True, raw
    monkeypatch.delenv(S, raising=False)
    assert reader() is False
    for raw in ("", "false", "0", "no", "off", "garbage", "tru e"):
        monkeypatch.setenv(S, raw)
        assert reader() is False, raw


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("s_value", [None, "false", " FALSE ", "0", "garbage"])
def test_p1_flag_off_golden_is_the_base(monkeypatch, s_value):
    """P1: with the new flag OFF (unset or any falsy spelling) every E1-E7 case returns
    the BASE reason recorded at b0ad2603; full configuration present (the guard ON, the
    knob set, the resolver flag ON)."""
    monkeypatch.setenv(G, "true")
    monkeypatch.setenv(KNOB, "5")
    monkeypatch.setenv(R, "true")
    _set(monkeypatch, S, s_value)
    for row, brand, line, category, texts, _on, base in CASES:
        got = _reason(brand, line, category, texts)
        assert got == base, (row, brand, ascii(line), category, ascii(texts), got)


@pytest.mark.parametrize("s_value", [None, "false"])
def test_p2_hazard_documented_guard_on_short_line_off(monkeypatch, s_value):
    """P2: G ON, S OFF: the resolver-shaped identities of E1-E4 (built through
    relevance_kwargs) refuse every listed title with name."""
    monkeypatch.setenv(G, "true")
    monkeypatch.setenv(R, "true")
    _set(monkeypatch, S, s_value)
    for brand, line, titles in HAZARD:
        kw = leaf.relevance_kwargs(brand, line, "fragrances", 0, False)
        ident = leaf.identity(brand + " " + line, kw["relevance"])
        for title in titles:
            got = leaf.check(ident, (title,), ())
            assert got == "name", (brand, ascii(line), ascii(title), got)


@pytest.mark.parametrize("g_value", [None, "false", " FALSE "])
def test_p3_guard_off_never_reads_the_short_line_flag(monkeypatch, caplog, g_value):
    """P3: guard OFF: relevance_kwargs returns {} and neither it nor the base call of
    get_product_image_url (with and without a relevance) reads the new flag; the new
    flag is set truthy and the knob set (ruling B1)."""
    _set(monkeypatch, G, g_value)
    monkeypatch.setenv(S, "true")
    monkeypatch.setenv(KNOB, "5")
    images = [{"title": "Ted Baker M Eau de Toilette 100 ml", "imageUrl": M_IMG}]
    seen = _getenv_recorder(monkeypatch)
    assert leaf.relevance_kwargs("Ted Baker", "M", "fragrances", 0, False) == {}
    assert leaf.relevance_kwargs("Ted Baker", "M", "fragrances", 0, True) == {}
    assert G in seen, seen
    for extra in ({}, {"relevance": _rel("Ted Baker", "M")}):
        rec = _Rec()
        _install(monkeypatch, rec, images=images)
        caplog.set_level(logging.INFO, logger=LOGGER)
        caplog.clear()
        out = asyncio.run(
            img.get_product_image_url(
                "Ted Baker M",
                region="bahrain",
                page_scrape_image=None,
                organic_results=None,
                search_payload=None,
                **extra,
            )
        )
        assert out == M_IMG, out
        assert _relevance_lines(caplog) == []
    assert S not in seen, seen


def _module_level_imports(tree):
    out = []
    stack = list(tree.body)
    while stack:
        node = stack.pop(0)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            out.append(node)
        elif isinstance(node, (ast.If, ast.Try)):
            for field in ("body", "orelse", "finalbody", "handlers"):
                stack.extend(getattr(node, field, []) or [])
        elif isinstance(node, ast.ExceptHandler):
            stack.extend(node.body)
    return out


# The module-level imports of image_relevance.py at b0ad2603 (typing names aside).
BASE_IMPORTS = {
    ("from", "__future__", "annotations", None),
    ("import", "math", None),
    ("import", "os", None),
    ("import", "re", None),
    ("from", "dataclasses", "dataclass", None),
    ("from", "urllib.parse", "urlsplit", None),
    ("from", "app.services", "category_gate", "_cg"),
    ("from", "app.services", "deny_hosts", "_dh"),
    ("from", "app.services", "jsonld_widen", "_jw"),
}
BASE_TYPING = {"Any", "Dict", "FrozenSet", "List", "Optional", "Set", "Tuple"}


def test_p4_leaf_module_level_imports_unchanged():
    """P4: image_relevance.py stays a leaf: its module-level imports are the base set
    (typing may only gain names from typing itself); no module-level logger."""
    with open(leaf.__file__, "rb") as fh:
        tree = ast.parse(fh.read().decode("utf-8"))
    got = set()
    typing_names = set()
    for node in _module_level_imports(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                got.add(("import", alias.name, alias.asname))
        elif node.module == "typing":
            typing_names.update(alias.name for alias in node.names)
        else:
            for alias in node.names:
                got.add(("from", node.module, alias.name, alias.asname))
    assert got == BASE_IMPORTS, got ^ BASE_IMPORTS
    assert typing_names >= BASE_TYPING, typing_names
    import typing

    assert all(hasattr(typing, name) for name in typing_names), typing_names
    defs = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    for node in tree.body:
        if isinstance(node, defs):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                fname = getattr(sub.func, "attr", None) or getattr(sub.func, "id", None)
                assert fname != "getLogger", "a module-level logger in the leaf"
