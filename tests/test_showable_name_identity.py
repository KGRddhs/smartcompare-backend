"""W4-5 (PO-PRICE-TRUTH-04) -- the sample/decant guard must read the identity the
page-scrape branches actually stamp.

``is_price_showable`` feeds ``_is_sample_or_decant_listing`` the ``title`` key ONLY.
Every ``extract_price_from_html`` rung (JSON-LD / OG / microdata / WooCommerce / RSC)
stamps the listing identity under ``name`` and never writes ``title``, so a decant
listing that reaches the display chokepoint through the page-scrape family is
invisible to the guard and ships as the full-bottle price.

The fix is ONE argument at the guard call, behind ``ENABLE_SHOWABLE_NAME_IDENTITY``
(default OFF, read per call):

    _is_sample_or_decant_listing(
        product_name,
        (title or price.get("name")) if showable_name_identity_enabled() else title,
        amount,
    )

``title or name`` -- never ``name or title``, never ``name`` alone -- and the fallback
is an ARGUMENT, never a write into ``price["title"]``.

Tests 1-4 are RED at ed75dc70 (the guard genuinely ignores ``name``); tests 5-9 pin
the rollback, the over-rejection boundary, the precedence, the no-dict-mutation
contract and the flag reader. ``ENABLE_EXACT_PRICE_GATE`` is left at its code
default (ON) throughout -- the ``name`` stamps in the page-scrape family are gated
by it, so that is the state in which the defect is reachable in prod.
"""

import pytest

import app.services.price_service as ps
from app.services.price_service import is_price_showable

FLAG = "ENABLE_SHOWABLE_NAME_IDENTITY"

# The review's exact reproduction (measured at ed75dc70, see .qa-w4/W4_5_UNIT_SPEC.md).
Q = "Xerjoff Ilm Eau de Parfum"
SAMPLE = "'Ilm Sample & Decants by Xerjoff"
TINY = "'Ilm 2ml Glass Spray by Xerjoff"
GENUINE = "Xerjoff 'Ilm Eau de Parfum 50ml"

# 94 BHD, not a low amount: at 40 the low-fragrance FLOOR already returns False for a
# name-only listing (the size falls to the 100 ml basis), so a low amount would make
# every red test pass vacuously through the floor instead of through the guard.
AMOUNT = 94


@pytest.fixture(autouse=True)
def _flag_env_default(monkeypatch):
    """Start every test with the unit's flag UNSET and the exact gate at its code
    default (ON). Toggled per test with monkeypatch.setenv/delenv, the
    tests/test_price_parse_offload.py idiom."""
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv("ENABLE_EXACT_PRICE_GATE", raising=False)
    yield


def _review_price(**overrides):
    """The review's price dict: {amount: 94, source_method: converted_usd, ...}."""
    price = {"amount": AMOUNT, "source_method": "converted_usd"}
    price.update(overrides)
    return price


def _showable(price, q=Q, category=None, *, enforce=True):
    return is_price_showable(q, price, category, enforce_correctness=enforce)


# ------------------------------------------------------------------ RED 1 ---


def test_1_review_call_name_keyed_sample_listing_not_showable_when_flag_on(monkeypatch):
    """RED test 1 -- the review's exact call with the flag ON returns False.

    RED at ed75dc70: True (the guard is fed ``title`` only, and there is none)."""
    monkeypatch.setenv(FLAG, "true")
    price = _review_price(name=SAMPLE)
    assert _showable(price) is False


# ------------------------------------------------------------------ RED 2 ---


def test_2_tiny_size_half_under_name_not_showable_when_flag_on(monkeypatch):
    """RED test 2 -- the tiny-size heuristic (<= 10 ml at >= 30 BHD) is ALSO blind
    to ``name``: a 2 ml glass spray at 94 BHD is a decant priced like a bottle.

    RED at ed75dc70: True."""
    monkeypatch.setenv(FLAG, "true")
    price = _review_price(name=TINY)
    assert _showable(price) is False


# ------------------------------------------------------------------ RED 3 ---


def test_3_method_agnostic_page_scrape_jsonld_under_name_not_showable(monkeypatch):
    """RED test 3 -- the defect is not ``converted_usd``-specific: the genuine
    ``page_scrape_jsonld`` method reaches the chokepoint with the same ``name``-only
    shape and must be caught the same way.

    RED at ed75dc70: True."""
    monkeypatch.setenv(FLAG, "true")
    price = _review_price(source_method="page_scrape_jsonld", name=SAMPLE)
    assert _showable(price) is False


# ------------------------------------------------------------------ RED 4 ---

_TF_Q = "Tom Ford Ombré Leather"
_TF_SAMPLE_PRICE = {"amount": 60.0, "currency": "BHD", "source_method": "converted_usd"}
_TF_GENUINE_PRICE = {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd"}
_SONY_Q = "Sony WH-1000XM5"
_SONY_PRICE = {"amount": 120.0, "currency": "BHD", "source_method": "local_bhd"}

# (query, category, identity string, price base, expected verdict under EITHER key)
# The four token rows are tests/test_price_showable.py::TestSampleDecantListingNotShowable's
# title pins carried across the key; the two genuine rows pin that parity does not
# over-reject; the electronics row pins that the regex half is category-agnostic
# (measured: title -> False, name -> True today) and the flag must not change that.
_PARITY_ROWS = [
    pytest.param(_TF_Q, None, f"{_TF_Q} sample 5ml", _TF_SAMPLE_PRICE, False, id="sample"),
    pytest.param(_TF_Q, None, f"{_TF_Q} decant 5ml", _TF_SAMPLE_PRICE, False, id="decant"),
    pytest.param(_TF_Q, None, f"{_TF_Q} tester 5ml", _TF_SAMPLE_PRICE, False, id="tester"),
    pytest.param(_TF_Q, None, f"{_TF_Q} vial 5ml", _TF_SAMPLE_PRICE, False, id="vial"),
    pytest.param(_TF_Q, None, f"{_TF_Q} EDP 100ml", _TF_GENUINE_PRICE, True, id="genuine-tf-100ml"),
    pytest.param(Q, None, GENUINE, _review_price(), True, id="genuine-xerjoff-50ml"),
    pytest.param(
        _SONY_Q, "electronics", "Sony WH-1000XM5 Tester unit", _SONY_PRICE, False,
        id="electronics-tester-unit",
    ),
]


@pytest.mark.parametrize("enforce", [False, True], ids=["enforce=False", "enforce=True"])
@pytest.mark.parametrize("q,category,identity,price_base,expected", _PARITY_ROWS)
def test_4_key_parity_name_equals_title_when_flag_on(
    monkeypatch, q, category, identity, price_base, expected, enforce,
):
    """RED test 4 -- with the flag ON, ``showable({name: s})`` equals
    ``showable({title: s})`` for every ``s``, and the title-keyed side still gives
    the pinned verdict (so parity is never satisfied vacuously).

    RED at ed75dc70 on the four token rows and the electronics row (name -> True,
    title -> False); the two genuine rows are True under both keys today."""
    monkeypatch.setenv(FLAG, "true")
    by_title = _showable({**price_base, "title": identity}, q=q, category=category, enforce=enforce)
    by_name = _showable({**price_base, "name": identity}, q=q, category=category, enforce=enforce)
    assert by_title is expected
    assert by_name is by_title


# ------------------------------------------------------------------ PIN 5 ---


@pytest.mark.parametrize("flag_value", [None, "false"], ids=["unset", "false"])
def test_5_flag_off_review_call_stays_showable(monkeypatch, flag_value):
    """PIN test 5 -- flag OFF (unset, and the literal "false") is byte-identical at
    the function level: the review's exact call returns True, exactly as today.

    This is the rollback pin the corpus byte-identity harness cannot see
    (``extract_price_from_html`` never calls ``is_price_showable``)."""
    if flag_value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag_value)
    price = _review_price(name=SAMPLE)
    assert _showable(price) is True


# ------------------------------------------------------------------ PIN 6 ---


@pytest.mark.parametrize("enforce", [True, False], ids=["enforce=True", "enforce=False"])
def test_6_genuine_name_keyed_listing_stays_showable_when_flag_on(monkeypatch, enforce):
    """PIN test 6 -- reading ``name`` must not over-reject: a genuine 50 ml listing
    whose identity sits under ``name`` stays showable with the flag ON (case C).

    No mutation target: it guards against over-rejection by construction."""
    monkeypatch.setenv(FLAG, "true")
    price = _review_price(name=GENUINE)
    assert _showable(price, enforce=enforce) is True


# ------------------------------------------------------------------ PIN 7 ---


@pytest.mark.parametrize("enforce", [True, False], ids=["enforce=True", "enforce=False"])
def test_7_precedence_title_wins_over_name(monkeypatch, enforce):
    """PIN test 7 -- ``title or name``, never ``name or title``: a present ``title``
    short-circuits the fallback, so the adapter rungs (which carry ``title``) are
    unchanged in both flag states. Reddens under ``name or title``."""
    monkeypatch.setenv(FLAG, "true")
    assert _showable(_review_price(title=GENUINE, name=SAMPLE), enforce=enforce) is True
    assert _showable(_review_price(title=SAMPLE, name=GENUINE), enforce=enforce) is False


# ------------------------------------------------------------------ PIN 8 ---


def test_8_list_typed_name_is_coerced_and_title_key_is_never_written(monkeypatch):
    """PIN test 8 -- a list-typed ``name`` is coerced INSIDE
    ``_is_sample_or_decant_listing`` (:1765-1767), so the raw value is safe to pass
    as an argument, and the price dict has NO ``title`` key afterwards: the
    fallback is an argument, not a dict mutation (design item 3 -- a mutated
    shape would leak the flag into cache rows and responses).

    ``enforce_correctness=False`` is deliberate: with it True and the exact gate
    ON, a list-typed ``name`` raises ``TypeError: unhashable type: 'list'`` today
    inside the backstop (Honest limit 3) -- pre-existing and outside this unit."""
    monkeypatch.setenv(FLAG, "true")
    price = _review_price(name=["'Ilm", "Sample & Decants"])
    result = _showable(price, enforce=False)
    assert "title" not in price
    assert result is False


# ------------------------------------------------------------------ PIN 9 ---

# Resolved lazily INSIDE each test (never at module import) so a missing reader
# reddens test 9 alone instead of erroring the whole file at collection -- tests
# 1-4 must fail because the guard ignores ``name``, not because of an ImportError.


def _reader():
    reader = getattr(ps, "showable_name_identity_enabled", None)
    assert reader is not None, "price_service.showable_name_identity_enabled is missing"
    return reader


def test_9a_reader_default_off_when_unset(monkeypatch):
    """PIN test 9 -- unset -> False (default OFF)."""
    monkeypatch.delenv(FLAG, raising=False)
    assert _reader()() is False


@pytest.mark.parametrize("value,expected", [
    ("true", True), ("1", True), ("yes", True), ("on", True),
    ("false", False), ("0", False),
    # Adversary (2026-09-11): the reader's ``.strip().lower()`` normalisation was
    # unpinned -- a reader without it survived every node. Operators type TRUE.
    ("TRUE", True), (" true ", True), ("ON", True), ("Yes", True),
    ("off", False), ("no", False), ("", False), ("  ", False),
])
def test_9b_reader_truthy_set_matches_price_parse_offload_idiom(monkeypatch, value, expected):
    """PIN test 9 -- the ``price_parse_offload_enabled`` truthy set
    ("true", "1", "yes", "on"); "false"/"0" -> False."""
    monkeypatch.setenv(FLAG, value)
    assert _reader()() is expected


def test_9c_reader_is_read_per_call_not_at_import(monkeypatch):
    """PIN test 9 -- setenv AFTER import flips the NEXT call: the module was
    imported at collection with the flag unset, so a reader that captured the
    env into a module constant at import would stay False here."""
    reader = _reader()
    monkeypatch.delenv(FLAG, raising=False)
    assert reader() is False
    monkeypatch.setenv(FLAG, "true")
    assert reader() is True
    monkeypatch.setenv(FLAG, "false")
    assert reader() is False
    monkeypatch.delenv(FLAG, raising=False)
    assert reader() is False
