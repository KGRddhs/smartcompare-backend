"""Issue #52 — iHerb must branch on a REAL page currency signal, not a tautology.

THE DEFECT. ``fetch_iherb_price`` computed ``_origin = currency`` and then asked
``str(_origin).upper() == str(currency).upper()`` — a variable compared to
itself, always True — and stamped ``local_bhd`` on that answer. So EVERY iHerb
price was stamped a genuine region-currency shelf price regardless of what the
page actually priced in, earning the 7-day genuine TTL, the genuine authority
tier in ``_select_best`` and a slot in the genuine-BH-share KPI. The function
read no currency field at all: neither the GA-card loop nor the F2.2 microdata
fallback ever touched ``meta[itemprop="priceCurrency"]``.

THE FIX (behind ``ENABLE_IHERB_PAGE_CURRENCY``, default OFF). Read the signal the
page actually publishes — the chosen card's own ``priceCurrency`` first, then the
document's — and stamp truthfully:

  * signal == the asked currency          -> ``local_bhd`` (genuine)
  * a different, convertible currency     -> convert, ``converted_usd``,
                                             ``original_currency`` = the signal
  * a token that is present but unusable  -> ``None`` (pend), never relabelled
  * NO signal at all                      -> today's documented regional-
                                             storefront assumption, stated once

Both directions are pinned: flag ON does the new thing, flag OFF is identical to
the pre-fix behaviour on every one of the same inputs.

Free tier — ``curl_cffi.requests.get`` is mocked with recorded fixtures.
"""

import ast
import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import price_service
from app.services.exchange_rate_service import FALLBACK_RATES

FIXTURES = Path(__file__).parent / "fixtures"
PRICE_SERVICE_SRC = Path(price_service.__file__)

FLAG = "ENABLE_IHERB_PAGE_CURRENCY"

# The two products the fixtures carry, so the expectations below are readable.
NOW_TITLE = "NOW Foods Vitamin D-3 5000 IU 120 Softgels"
NOW_PRICE = 3.852


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class _FakeResp:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _patch_curl(html: str, status_code: int = 200):
    """Patch the curl_cffi.requests.get used inside fetch_iherb_price."""
    import curl_cffi

    return patch.object(curl_cffi.requests, "get", return_value=_FakeResp(html, status_code))


def _fetch(html: str, *, currency: str = "BHD", region_code: str = "bh",
           brand: str = "NOW Foods", full_name: str = NOW_TITLE):
    with _patch_curl(html):
        return _run(price_service.fetch_iherb_price(
            "NOW Vitamin D3 5000", brand, full_name, region_code, currency,
        ))


# ---------------------------------------------------------------------------
# The flag itself — default OFF, read PER CALL (never cached at import)
# ---------------------------------------------------------------------------

def test_flag_defaults_off(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    assert price_service.iherb_page_currency_enabled() is False


def test_flag_is_read_per_call_not_cached(monkeypatch):
    """Railway must be able to flip it without a restart (the exact_gate idiom)."""
    monkeypatch.setenv(FLAG, "true")
    assert price_service.iherb_page_currency_enabled() is True
    monkeypatch.setenv(FLAG, "false")
    assert price_service.iherb_page_currency_enabled() is False


# ---------------------------------------------------------------------------
# Flag ON — the four arms of the signal ladder
# ---------------------------------------------------------------------------

def test_on_foreign_card_currency_converts_and_stamps_converted_usd(monkeypatch):
    """A card that declares USD on a BHD ask converts and is NOT genuine.

    This is the whole bug: today 3.852 USD ships as 3.852 "BHD" (a 2.66x
    over-price) wearing the genuine local_bhd stamp.
    """
    monkeypatch.setenv(FLAG, "true")
    res = _fetch(_load("iherb_ga_cards_usd.html"))

    assert res is not None, "a convertible foreign currency must still yield a price"
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "USD"
    assert res["currency"] == "BHD"
    assert res["amount"] == round(NOW_PRICE * FALLBACK_RATES["USD"], 3)
    assert res["amount"] != NOW_PRICE, "the raw foreign figure must never ship"


def test_on_matching_card_currency_stays_local_bhd(monkeypatch):
    """A card that declares BHD on a BHD ask is genuine — unchanged amount."""
    monkeypatch.setenv(FLAG, "true")
    res = _fetch(_load("iherb_microdata_only.html"))

    assert res is not None
    assert res["source_method"] == "local_bhd"
    assert res["amount"] == NOW_PRICE
    assert res["original_currency"].upper() == "BHD"


def test_on_unreadable_card_currency_pends(monkeypatch):
    """A present-but-unresolvable token pends. It must NOT be read as silence.

    "This page says nothing" and "this page says something I cannot read" are
    different states (BLOCKER 4). Collapsing them ships a foreign figure under
    the region-currency label.
    """
    monkeypatch.setenv(FLAG, "true")
    assert _fetch(_load("iherb_ga_cards_unreadable_currency.html")) is None


def test_on_no_signal_keeps_the_regional_storefront_assumption(monkeypatch):
    """A genuinely unlabelled page keeps today's documented assumption.

    ``iherb_ga_cards.html`` carries no currency marker at all, which is exactly
    this arm. Deliberate: the fix removes a GUESS dressed as a check, it does not
    start pending every page iHerb serves without microdata.
    """
    monkeypatch.setenv(FLAG, "true")
    res = _fetch(_load("iherb_ga_cards.html"))

    assert res is not None
    assert res["source_method"] == "local_bhd"
    assert res["amount"] == NOW_PRICE
    assert res["original_currency"] == "BHD"


def test_on_page_level_currency_used_when_the_card_is_silent(monkeypatch):
    """Card carries no currency, the document's OG meta does -> that is a signal."""
    monkeypatch.setenv(FLAG, "true")
    res = _fetch(_load("iherb_ga_cards_og_currency.html"))

    assert res is not None
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "USD"
    assert res["amount"] == round(NOW_PRICE * FALLBACK_RATES["USD"], 3)


def test_on_foreign_signal_with_non_bhd_ask_pends(monkeypatch):
    """The conversion rung targets BHD only, so a SAR ask on a USD page pends.

    ``_convert_to_bhd`` converts to BHD and nothing else; stamping a
    BHD-converted number with "SAR" would be the same relabelling defect one
    currency over. Abstaining is the honest answer.
    """
    monkeypatch.setenv(FLAG, "true")
    assert _fetch(_load("iherb_ga_cards_usd.html"),
                  currency="SAR", region_code="sa") is None


# ---------------------------------------------------------------------------
# Flag OFF — identical to the pre-fix behaviour on the SAME inputs
# ---------------------------------------------------------------------------

def test_off_foreign_card_currency_behaves_exactly_as_before(monkeypatch):
    """Flag OFF must not read the signal at all: today's stamp, today's amount."""
    monkeypatch.delenv(FLAG, raising=False)
    res = _fetch(_load("iherb_ga_cards_usd.html"))

    assert res is not None
    assert res["source_method"] == "local_bhd"
    assert res["original_currency"] == "BHD"
    assert res["amount"] == NOW_PRICE


def test_off_unreadable_card_currency_behaves_exactly_as_before(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    res = _fetch(_load("iherb_ga_cards_unreadable_currency.html"))

    assert res is not None
    assert res["source_method"] == "local_bhd"
    assert res["amount"] == NOW_PRICE


def test_off_page_level_currency_behaves_exactly_as_before(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    res = _fetch(_load("iherb_ga_cards_og_currency.html"))

    assert res is not None
    assert res["source_method"] == "local_bhd"
    assert res["amount"] == NOW_PRICE


@pytest.mark.parametrize("fixture", [
    "iherb_ga_cards.html",
    "iherb_microdata_only.html",
])
def test_off_unsignalled_and_matching_pages_are_untouched(monkeypatch, fixture):
    monkeypatch.delenv(FLAG, raising=False)
    res = _fetch(_load(fixture))

    assert res is not None
    assert res["source_method"] == "local_bhd"
    assert res["amount"] == NOW_PRICE
    assert res["original_currency"] == "BHD"


# ---------------------------------------------------------------------------
# The tautology itself — a structural pin, comment-free by construction
# ---------------------------------------------------------------------------

def test_no_variable_is_compared_against_its_own_alias():
    """``fetch_iherb_price`` must not decide anything by comparing X to X.

    Parsed with ``ast``, so COMMENTS AND DOCSTRINGS CANNOT SATISFY THIS TEST —
    this repo has shipped a pin that passed because the asserted string lived in
    a comment, and a docstring carries no ``Assign``/``Compare`` nodes at all.

    The detector: find a name bound straight to another name (``_origin =
    currency``), then flag any LATER comparison built out of that alias on one
    side and its source on the other — unless one of the two was rebound in
    between, which is what makes an ordinary accumulator (``best_score =
    overlap`` then ``overlap > best_score`` on the next pass) not a tautology.
    """
    tree = ast.parse(PRICE_SERVICE_SRC.read_text(encoding="utf-8"))
    func = next(
        n for n in ast.walk(tree)
        if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
        and n.name == "fetch_iherb_price"
    )

    # Every line on which a bare name is (re)bound, and every `alias = source`
    # pair with the line it happened on.
    bound_at: dict[str, list[int]] = {}
    pairs: list[tuple[str, str, int]] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
            bound_at.setdefault(target, []).append(node.lineno)
            if isinstance(node.value, ast.Name):
                pairs.append((target, node.value.id, node.lineno))

    def names(node):
        return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}

    def rebound_between(name, lo, hi):
        return any(lo < line <= hi for line in bound_at.get(name, ()))

    for cmp_node in (n for n in ast.walk(func) if isinstance(n, ast.Compare)):
        sides = [names(cmp_node.left)] + [names(c) for c in cmp_node.comparators]
        for alias, source, alias_line in pairs:
            if cmp_node.lineno <= alias_line:
                continue  # the alias did not exist yet
            if rebound_between(alias, alias_line, cmp_node.lineno):
                continue
            if rebound_between(source, alias_line, cmp_node.lineno):
                continue
            for i, left in enumerate(sides):
                for right in sides[i + 1:]:
                    assert not (
                        (alias in left and source in right)
                        or (alias in right and source in left)
                    ), (
                        f"line {cmp_node.lineno}: '{alias}' is just '{source}', so this "
                        f"comparison is always True — read a real page signal instead"
                    )
