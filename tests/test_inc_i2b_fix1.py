"""INC-I2b FIX-1 rows (ADV-1 F-A1-1 and F-A1-2), with ENABLE_IMAGE_GUARD_WORDS ON.

* FX-1 (F-A1-1): a free-standing "intense" refuses only in a POSITIONAL slot, i.e.
  when it is the flanker word of the name: the next token is the end, the first token
  of a concentration phrase, a size, or one of spray / for / pour / men / women /
  homme / femme / edition / by. A marketing "Intense Scent", "Intense and Long
  Lasting" or "Intense Woody" is generic.
* FX-2 (F-A1-2): when the user typed an intense together with a concentration, rule
  2(b) strips a trailing " Intense" from every label on both sides, so "Intense EDP"
  and "Eau de Parfum Intense" match. Without a typed intense 2(b) is unchanged (I-9).

X1..X11 fail at aec760b5 on an AssertionError (the GREEN head refuses them with
``concentration``); X12 and X13 are controls that stay refused at both heads.

The query shapes follow the ADV-1 probe (adv_a1/probes/words.py, mode roff): the
explicit R OFF path, brand "", the line and the typed text both equal to the typed
name. Hermetic: check() only, no network, no Redis, no LLM. Pure ASCII, LF.
"""

from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

G_FLAG = "ENABLE_IMAGE_RELEVANCE_GUARD"
S_FLAG = "ENABLE_IMAGE_GUARD_SHORT_LINE"
W_FLAG = "ENABLE_IMAGE_GUARD_WORDS"
A_FLAG = "ENABLE_SHOP_PAGE_IMAGE"
B_FLAG = "ENABLE_SHOPPING_THUMB_IMAGE"
L_FLAG = "ENABLE_IMAGE_LATE_BIND"
R_FLAG = "ENABLE_PRODUCT_RESOLVER"
CLEARED_ENV = (G_FLAG, S_FLAG, W_FLAG, A_FLAG, B_FLAG, L_FLAG, R_FLAG)


# ---------------------------------------------------------------------------
# helpers (copied from tests/test_inc_i2b_guard_words_shop_image.py)
# ---------------------------------------------------------------------------


def _ir():
    from app.services import image_relevance

    return image_relevance


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    yield


def _flags(mp, **kw):
    names = {"g": G_FLAG, "s": S_FLAG, "w": W_FLAG, "r": R_FLAG}
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


def _rel(brand, line, typed=None, slot=0):
    rel = {"brand": brand, "line": line, "category": "fragrances", "slot": slot}
    if typed is not None:
        rel["typed"] = typed
    return rel


def _verdict(product, brand, line, title, typed=True):
    """check() of one title for one query; typed=True -> the product name is typed."""
    ir = _ir()
    t = product if typed is True else typed
    ident = ir.identity(product, _rel(brand, line, t if t else None))
    return ir.check(ident, [title])


def _roff(typed_name, title):
    """The explicit R OFF path (ADV-1 mode roff): brand "", line = typed = the name."""
    return _verdict(typed_name, "", typed_name, title)


def _both(mp, typed_name, title):
    """(W unset, W ON) verdicts of one roff query, both under G and S ON."""
    _flags(mp, w=False)
    off = _roff(typed_name, title)
    _flags(mp, w=True)
    return off, _roff(typed_name, title)


# ---------------------------------------------------------------------------
# X1..X5 (FX-1): a marketing intense is generic
# ---------------------------------------------------------------------------

FX1_ROWS = [
    (
        "X1",
        "Dior Sauvage EDP",
        "Dior Sauvage Eau De Parfum 100ml - Long Lasting, Intense Scent",
    ),
    (
        "X2",
        "Dior Sauvage EDP",
        "Dior Sauvage EDP 100ml, Intense Long Lasting Fragrance for Men",
    ),
    (
        "X3",
        "Dior Sauvage EDP",
        "Dior Sauvage Eau de Parfum 100ml Intense and Long Lasting",
    ),
    (
        "X4",
        "Lattafa Khamrah",
        "Lattafa Khamrah Eau De Parfum 100ml - Sweet, Intense & Long Lasting",
    ),
    ("X5", "Dior Sauvage", "Dior Sauvage EDT 100ml, Intense Woody Scent"),
]


@pytest.mark.parametrize("row", FX1_ROWS, ids=[r[0] for r in FX1_ROWS])
def test_x01_x05_marketing_intense_is_generic(monkeypatch, row):
    """X1..X5 (F-A1-1): base None and W ON None (aec760b5: concentration)."""
    _rid, typed_name, title = row
    off, on = _both(monkeypatch, typed_name, title)
    assert off is None, (typed_name, title, off)
    assert on is None, (typed_name, title, on)


# ---------------------------------------------------------------------------
# X6..X11 (FX-2): a typed intense matches either word order
# ---------------------------------------------------------------------------

FX2_ROWS = [
    (
        "X6",
        "Valentino Born in Roma Intense EDP",
        "Valentino Donna Born In Roma Eau de Parfum Intense 100ml",
    ),
    (
        "X7",
        "Coco Mademoiselle Eau de Parfum Intense",
        "Chanel Coco Mademoiselle Intense EDP 100ml",
    ),
    (
        "X8",
        "Coco Mademoiselle Intense EDP",
        "Chanel Coco Mademoiselle Eau de Parfum Intense Spray 100ml",
    ),
    (
        "X9",
        "Dior Homme Intense EDP",
        "Dior Homme Eau de Parfum Intense 100ml",
    ),
    (
        "X10",
        "Boss Bottled Intense EDP",
        "Hugo Boss Boss Bottled Eau de Parfum Intense 100ml",
    ),
    (
        "X11",
        "Le Male Le Parfum EDP Intense",
        "Jean Paul Gaultier Le Male Le Parfum Intense Eau de Parfum",
    ),
]


@pytest.mark.parametrize("row", FX2_ROWS, ids=[r[0] for r in FX2_ROWS])
def test_x06_x11_typed_intense_either_order(monkeypatch, row):
    """X6..X11 (F-A1-2): base None and W ON None (aec760b5: concentration)."""
    _rid, typed_name, title = row
    off, on = _both(monkeypatch, typed_name, title)
    assert off is None, (typed_name, title, off)
    assert on is None, (typed_name, title, on)


# ---------------------------------------------------------------------------
# X12, X13: the controls (refused at aec760b5 and after the fix)
# ---------------------------------------------------------------------------


def test_x12_flanker_intense_without_a_typed_intense_stays_refused(monkeypatch):
    """X12: a positional intense (before a phrase, before a size) and an "EDP Intense"
    label, with no typed intense: concentration (no stripping). The bare row carries
    the brand ("Dior" / "Homme"): on the roff shape its title has no fragrance word,
    so the base already refuses it (fragrance_word)."""
    rows = [
        (
            "Dior Homme EDP",
            "",
            "Dior Homme EDP",
            "Dior Homme Intense Eau de Parfum 100ml",
        ),
        ("Dior Homme", "Dior", "Homme", "Dior Homme Intense 100ml"),
        (
            "Dior Homme EDP",
            "",
            "Dior Homme EDP",
            "Dior Homme Eau de Parfum Intense 100ml",
        ),
    ]
    for product, brand, line, title in rows:
        _flags(monkeypatch, w=False)
        off = _verdict(product, brand, line, title)
        _flags(monkeypatch, w=True)
        on = _verdict(product, brand, line, title)
        assert off is None, (product, title, off)
        assert on == "concentration", (product, title, on)


def test_x13_typed_intense_other_concentration_stays_refused(monkeypatch):
    """X13: typed "Born in Roma Intense EDP" vs an EDT title: refused (EDT vs EDP after
    the stripping). With the brand known the base passes and the words refuse with
    concentration; on the roff shape the base already refuses."""
    typed_name = "Born in Roma Intense EDP"
    title = "Valentino Born in Roma EDT 100ml"
    _flags(monkeypatch, w=False)
    assert _verdict(typed_name, "Valentino", "Born in Roma Intense", title) is None
    _flags(monkeypatch, w=True)
    assert (
        _verdict(typed_name, "Valentino", "Born in Roma Intense", title)
        == "concentration"
    )
    assert _roff(typed_name, title) is not None
