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
document's — and stamp truthfully. The ladder, as it stands after the follow-up
that closed the contradiction and scope defects:

  * the page CONTRADICTS itself (>=2 document codes) -> ``None`` (pend). A third
                                             state, told apart from silence by a
                                             module-level sentinel
  * NO signal at all                      -> today's documented regional-
                                             storefront assumption, stated once
  * signal == the asked currency          -> ``local_bhd`` (genuine), either scope
  * a DOCUMENT-level code that disagrees  -> ``None`` (pend). NEVER a conversion:
                                             that code is not scoped to the card
                                             whose number is being shipped
  * a CARD-level foreign, convertible code-> convert, ``converted_usd``,
                                             ``original_currency`` = the signal
  * a CARD-level token present but unusable-> ``None`` (pend), never relabelled

Both directions are pinned: flag ON does the new thing, flag OFF is identical to
the pre-fix behaviour on every one of the same inputs.

STRIP-CHECK, MEASURED (the original #52 fix removed, this file kept, ``pytest``
re-run): **7 of 14 fail on base** — ``test_flag_defaults_off``,
``test_flag_is_read_per_call_not_cached``,
``test_on_foreign_card_currency_converts_and_stamps_converted_usd``,
``test_on_unreadable_card_currency_pends``, the page-level node (then
``test_on_page_level_currency_used_when_the_card_is_silent``, now
``test_on_page_level_foreign_currency_pends_and_never_converts``),
``test_on_foreign_signal_with_non_bhd_ask_pends`` and the AST tautology pin
``test_no_variable_is_compared_against_its_own_alias``.

STRIP-CHECK OF THE FOLLOW-UP, MEASURED (``price_service.py`` reverted to the
pre-follow-up commit, this file kept): **4 of 26 fail** —
``test_on_page_level_foreign_currency_pends_and_never_converts``,
``test_page_rung_reports_contradiction_as_its_own_state`` and both parameters of
``test_on_a_self_contradicting_page_pends``. Three targeted MUTATIONS of the
follow-up were measured separately, each failing a different node and no other:
neutering the F2.2 per-card read -> the two ``test_on_f22_*`` nodes (0 before);
deleting the ``len(tokens) == 1`` guard -> the contradiction unit pin on every
run; narrowing the equality arm to card scope ->
``test_on_page_level_matching_currency_confirms_local_bhd``; replacing rung 2
with ``return None`` -> the page-level pend node.

The remaining nodes pass on base ON PURPOSE and must not be mistaken for defect
pins: the ``test_off_*`` cases are FLAG-OFF byte-identity pins (passing on base is
literally what they assert — and since the corpus byte-identity gate never calls
``fetch_iherb_price``, they are #52's ONLY byte-identity evidence), and
``test_on_matching_card_currency_stays_local_bhd`` +
``test_on_no_signal_keeps_the_regional_storefront_assumption`` are
ARM-PRESERVATION pins — the fix must NOT start pending an unlabelled page or
relabelling a page that already agrees, which is the acceptance criterion that
keeps ``tests/test_iherb_native_bhd_label.py`` green.

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


def test_on_page_level_foreign_currency_pends_and_never_converts(monkeypatch):
    """A DOCUMENT-level code that disagrees with the storefront PENDS.

    UPDATED PIN (was ``test_on_page_level_currency_used_when_the_card_is_silent``,
    which asserted this fixture converts 3.852 to 0.376x and stamps
    ``converted_usd``). The rationale for the change, in full:

    ``_page_currency_evidence`` returns the FIRST ``og:price:currency`` /
    ``product:price:currency`` meta, else the FIRST ``priceCurrency`` reachable
    in ANY JSON-LD blob on the document. Its measured justification is
    single-product PDPs (niche-beauty.com, samawa.ae, faces.ae) where og:price
    describes THE product on the page. ``fetch_iherb_price`` parses a
    MULTI-PRODUCT search-results page, so nothing ties that document-level code
    to the card whose number is being shipped. Converting on it means: if
    bh.iherb.com's template ever emits a canonical document-level USD while its
    cards price in BHD — the normal shape for a US-origin multi-storefront site
    — flag ON multiplies every genuine BHD supplement price by 0.376, a 62%-low
    number. That is strictly worse than the mislabel #52 exists to fix.

    So the document rung keeps exactly two powers: CONFIRM (see
    ``test_on_page_level_matching_currency_confirms_local_bhd``) or PEND (here).
    The per-CARD rung keeps convert-on-foreign, because it IS scoped to the card
    whose amount it moves — see
    ``test_on_foreign_card_currency_converts_and_stamps_converted_usd``.
    """
    monkeypatch.setenv(FLAG, "true")
    assert _fetch(_load("iherb_ga_cards_og_currency.html")) is None


def test_on_page_level_matching_currency_confirms_local_bhd(monkeypatch):
    """A DOCUMENT-level code that AGREES with the storefront confirms: genuine.

    The guard against OVER-correcting. Confirming cannot move a number — it only
    ratifies the assumption already in force — so it needs no scoping argument,
    and a rule that read "document evidence always pends" would be a silent
    capture loss on every page whose template happens to tag itself correctly.
    MEASURED: narrowing the equality arm to card scope only (``elif _ccy_signal
    == _ask_ccy and _ccy_scope == _CCY_SCOPE_CARD``) fails THIS node and no
    other. Honest limit: this node does NOT catch deleting rung 2 outright —
    that collapses to the storefront-assumption arm, which ships the same
    ``local_bhd`` 3.852; the node above is what catches that (measured: rung 2
    replaced by ``return None`` fails it alone).
    """
    monkeypatch.setenv(FLAG, "true")
    res = _fetch(_load("iherb_ga_cards_og_bhd.html"))

    assert res is not None
    assert res["source_method"] == "local_bhd"
    assert res["amount"] == NOW_PRICE
    assert res["original_currency"] == "BHD"


# ---------------------------------------------------------------------------
# Flag ON — a page that CONTRADICTS ITSELF is a THIRD state, not silence
# ---------------------------------------------------------------------------

def test_page_rung_reports_contradiction_as_its_own_state():
    """Direct pin on the abstain-on-multiplicity rule, which was prose-only.

    MEASURED by the reviewer on the previous HEAD: deleting the ``len(tokens) ==
    1`` guard in ``_iherb_page_currency_token`` left all 14 nodes of this file
    green, because no fixture carried two DISTINCT document-level codes. This
    node kills that mutation DETERMINISTICALLY: without the guard the helper
    returns an arbitrary element of a ``set`` of ISO strings, which is never the
    sentinel. (The end-to-end contradiction nodes below would only catch it on
    the ~50% of runs where PYTHONHASHSEED ordering hands back the code that is
    not the storefront's — which is exactly why the rule cannot be pinned end to
    end alone.)

    It also pins the shape of the answer: a contradiction must be tellable APART
    from silence by the caller, so it is a sentinel object compared with ``is``,
    never None and never a string that could collide with an ISO code.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(_load("iherb_ga_cards_contradiction.html"), "html.parser")
    assert (
        price_service._iherb_page_currency_token(soup)
        is price_service._CURRENCY_CONTRADICTION
    )
    assert price_service._CURRENCY_CONTRADICTION is not None
    assert price_service._CURRENCY_CONTRADICTION != "BHD"
    assert price_service._CURRENCY_CONTRADICTION != "USD"


def test_page_rung_still_answers_a_single_document_code():
    """The negative control for the node above: one distinct code is evidence.

    Without this, "return the sentinel on multiplicity" could be satisfied by
    returning the sentinel on EVERY microdata page, which would silently kill the
    rung instead of narrowing it.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(_load("iherb_microdata_only.html"), "html.parser")
    assert price_service._iherb_page_currency_token(soup) == "BHD"


@pytest.mark.parametrize("fixture", [
    "iherb_ga_cards_contradiction.html",   # GA-card path
    "iherb_microdata_contradiction.html",  # F2.2 microdata path
])
def test_on_a_self_contradicting_page_pends(monkeypatch, fixture):
    """A silent chosen card on a page declaring TWO different currencies pends.

    THE DEFECT THIS CLOSES. ``_iherb_page_currency_token`` used to return None on
    multiplicity, and None is what the caller reads as "this page never says" —
    THE ASSUMPTION ARM. So a self-contradicting page kept ``_genuine_bh = True``,
    kept the amount untouched and stamped ``local_bhd``: the 7-day genuine TTL,
    the genuine authority tier in ``_select_best`` and a genuine-BH-share KPI
    slot, all bought by a page that cannot agree with itself. That is the exact
    conflation #52 removes at the card rung, reintroduced one rung down.

    Both fixtures use the DANGEROUS pair (BHD beside USD), so an implementation
    that picks an arbitrary token cannot be right by luck about which of the two
    it grabbed. Both paths are covered because the GA loop and the F2.2 microdata
    loop reach the caller through different code.
    """
    monkeypatch.setenv(FLAG, "true")
    assert _fetch(_load(fixture)) is None


# ---------------------------------------------------------------------------
# Flag ON — the F2.2 microdata fallback's own per-card read
# ---------------------------------------------------------------------------
#
# MEASURED by the reviewer on the previous HEAD: neutering the per-card currency
# read inside the F2.2 `div.product-inner` loop (`"currency_token":
# _iherb_card_currency_token(card) if _currency_signal_gate else None`) left all
# 14 nodes of this file green, while the same mutation on the GA-card line was
# caught. Every fixture the file used reached either the GA loop or a microdata
# page whose EVERY card declared BHD, so the document rung always produced the
# answer the card rung would have. The two nodes below are the arm's own pins.

def test_on_f22_foreign_card_currency_converts_and_stamps_converted_usd(monkeypatch):
    """F2.2 path: the chosen card says USD, its siblings say BHD -> convert.

    The document rung is useless here by construction (two distinct codes is a
    contradiction), so only the per-card read can see the truth — and only the
    per-card read is scoped narrowly enough to license moving this card's amount.
    Without the F2.2 read this page shipped 3.852 USD as 3.852 "BHD" with the
    genuine stamp.
    """
    monkeypatch.setenv(FLAG, "true")
    res = _fetch(_load("iherb_microdata_foreign_card.html"))

    assert res is not None, "a convertible foreign currency must still yield a price"
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "USD"
    assert res["currency"] == "BHD"
    assert res["amount"] == round(NOW_PRICE * FALLBACK_RATES["USD"], 3)
    assert res["amount"] != NOW_PRICE, "the raw foreign figure must never ship"


def test_on_f22_unreadable_card_currency_pends(monkeypatch):
    """F2.2 path: the chosen card says "XYZ", its siblings say BHD -> pend.

    The trap: "XYZ" does not resolve, so the DOCUMENT rung sees only the
    siblings' BHD — one distinct code, a clean-looking agreement with the
    storefront — and would confirm the genuine stamp on a number denominated in
    something nothing can read. Only the per-card read pends it.
    """
    monkeypatch.setenv(FLAG, "true")
    assert _fetch(_load("iherb_microdata_unreadable_card.html")) is None


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


@pytest.mark.parametrize("fixture", [
    "iherb_ga_cards_contradiction.html",
    "iherb_microdata_contradiction.html",
    "iherb_microdata_foreign_card.html",
    "iherb_microdata_unreadable_card.html",
    "iherb_ga_cards_og_bhd.html",
])
def test_off_new_fixtures_behave_exactly_as_before(monkeypatch, fixture):
    """FLAG-OFF BYTE-IDENTITY over every fixture this follow-up added.

    These five inputs are new, so nothing else in the repo pins what base does
    with them — and the corpus byte-identity gate
    (``scripts/verify_flag_byte_identity.py``) exercises only
    ``extract_price_from_html`` and never calls ``fetch_iherb_price`` at all, so
    THESE EXPLICIT PINS ARE #52'S ONLY BYTE-IDENTITY EVIDENCE. Every one of the
    five pages ships the pre-#52 answer with the flag off: the storefront
    assumption, the untouched amount, the ``local_bhd`` stamp — including the
    two that pend and the one that converts with the flag on.
    """
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

    POSITIVE CONTROL (test-quality review #52/P3). Every assertion in this test
    lives inside ``for alias, source, alias_line in pairs``, so an EMPTY
    ``pairs`` — or zero ``Compare`` nodes, or a rename of ``fetch_iherb_price``
    that made this an all-``continue`` loop — passes it VACUOUSLY, which is the
    same failure mode the sibling pins were repaired for
    (``tests/test_flush_live_price_key.py`` ``assert holder``,
    ``tests/test_genuine_price_clobber_guard.py``). MEASURED at aaaaa76: 4 alias
    pairs (``_origin = currency`` at line 15883 among them) and 20 ``Compare``
    nodes. The three assertions below pin that the detector had real material,
    and ``inspected`` pins that its comparison body actually RAN.
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

    compares = [n for n in ast.walk(func) if isinstance(n, ast.Compare)]
    # --- positive control: the detector must have had something to detect.
    assert pairs, (
        "no `alias = source` assignment found in fetch_iherb_price — the loop "
        "below would pass vacuously, exactly as it did at merge-base where the "
        "tautology this file exists to pin had not been written yet"
    )
    assert compares, "no Compare node in fetch_iherb_price — nothing to inspect"
    assert any(alias == "_origin" for alias, _s, _l in pairs), (
        "the `_origin = <name>` alias is gone; if that is deliberate, retarget "
        f"this control at the alias that replaced it (found: {pairs})"
    )

    inspected = 0
    for cmp_node in compares:
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
                    inspected += 1
                    assert not (
                        (alias in left and source in right)
                        or (alias in right and source in left)
                    ), (
                        f"line {cmp_node.lineno}: '{alias}' is just '{source}', so this "
                        f"comparison is always True — read a real page signal instead"
                    )

    # ...and the loop body really executed: every `continue` above firing on
    # every pass would leave this at 0 and the test would prove nothing.
    assert inspected, (
        "no (comparison, alias) combination was ever inspected — the guards "
        "skipped every pass, so this pin is asserting nothing"
    )


# ---------------------------------------------------------------------------
# The contradiction arm is DEFENCE IN DEPTH — and must stay tellable apart
# ---------------------------------------------------------------------------
#
# MEASURED at aaaaa76 (test-quality review #52/P3): deleting the
# `if _ccy_signal is _CURRENCY_CONTRADICTION:` arm from `fetch_iherb_price`
# left every node of this file green. It is behaviourally redundant given the
# arm two rungs down — `_CURRENCY_CONTRADICTION` can only ever come from
# `_iherb_page_currency_token`, which `_iherb_currency_signal` reaches only on
# the `_CCY_SCOPE_PAGE` branch, so `_ccy_scope != _CCY_SCOPE_CARD` pends the
# same page. Redundancy is fine here (the sentinel is the whole point of #52's
# third state, and a future CARD-scoped contradiction must not be allowed to
# fall through to conversion), so the arm STAYS — but a pin has to make its
# deletion visible, and the canary has to be able to tell the two pends apart.
_CONTRADICTION_LOG_PREFIX = "[PRICE] iHerb pend: page declares two or more currencies"


def _fetch_iherb_func():
    tree = ast.parse(PRICE_SERVICE_SRC.read_text(encoding="utf-8"))
    return next(
        n for n in ast.walk(tree)
        if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
        and n.name == "fetch_iherb_price"
    )


def _ifs_testing_on(func, symbol):
    """Every ``ast.If`` in ``func`` whose TEST mentions the name ``symbol``."""
    return [
        n for n in ast.walk(func)
        if isinstance(n, ast.If)
        and symbol in {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)}
    ]


def _pend_log_messages(if_node):
    """Every ``logger.*("...")`` format string in this arm's OWN body.

    ``if_node.body`` only — an ``elif`` chain hangs the remaining arms off
    ``orelse``, so walking the node whole would attribute the ``else`` arm's
    message to the ``elif`` above it.
    """
    msgs = []
    for stmt in if_node.body:
        for node in ast.walk(stmt):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "logger"
                    and node.args and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                msgs.append(node.args[0].value)
    return msgs


def test_the_contradiction_arm_is_tested_before_the_document_scope_arm():
    """Structural pin — the arm exists, and it is reached FIRST.

    Order is the whole of its value: the scope arm below it pends the same page
    with a different message, so a contradiction that fell through would be
    indistinguishable from an ordinary document/card disagreement. Parsed with
    ``ast`` so a comment cannot satisfy it, and both lookups are asserted to
    find EXACTLY ONE branch (the positive control) so a rename cannot make this
    pass by finding nothing.
    """
    func = _fetch_iherb_func()
    contradiction = _ifs_testing_on(func, "_CURRENCY_CONTRADICTION")
    scope = _ifs_testing_on(func, "_CCY_SCOPE_CARD")

    assert len(contradiction) == 1, (
        "expected exactly one `is _CURRENCY_CONTRADICTION` branch in "
        f"fetch_iherb_price, found {len(contradiction)}"
    )
    assert len(scope) == 1, (
        "expected exactly one `_ccy_scope != _CCY_SCOPE_CARD` branch in "
        f"fetch_iherb_price, found {len(scope)}"
    )
    assert contradiction[0].lineno < scope[0].lineno, (
        "the contradiction arm no longer precedes the document-scope arm, so a "
        "self-contradicting page now pends with the scope arm's message"
    )


def test_the_two_pend_arms_log_distinguishable_lines():
    """A canary must be able to count contradictions separately from scope pends.

    The merge note cites the contradiction prefix verbatim, so it is pinned
    verbatim; the scope arm must not share it.
    """
    func = _fetch_iherb_func()
    contradiction_msgs = _pend_log_messages(
        _ifs_testing_on(func, "_CURRENCY_CONTRADICTION")[0])
    scope_msgs = _pend_log_messages(_ifs_testing_on(func, "_CCY_SCOPE_CARD")[0])

    assert len(contradiction_msgs) == 1, contradiction_msgs
    assert len(scope_msgs) == 1, scope_msgs
    assert contradiction_msgs[0].startswith(_CONTRADICTION_LOG_PREFIX), (
        "the merge note cites this exact prefix and the canary greps for it: "
        f"{contradiction_msgs[0]!r}"
    )
    assert not scope_msgs[0].startswith(_CONTRADICTION_LOG_PREFIX), (
        "the scope pend is now indistinguishable from a contradiction pend"
    )
    assert contradiction_msgs[0] != scope_msgs[0]

    # ...and no OTHER pend in this function reuses the prefix either (there is a
    # third one, the non-convertible arm), so a grep for the merge note's string
    # counts contradictions and nothing else.
    all_pends = [
        node.args[0].value
        for node in ast.walk(func)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "logger"
            and node.args and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.startswith("[PRICE] iHerb pend:"))
    ]
    assert len(all_pends) >= 3, f"pend arms disappeared: {all_pends}"
    assert len(set(all_pends)) == len(all_pends), (
        f"two pend arms log the SAME line: {all_pends}"
    )
    assert [m for m in all_pends if m.startswith(_CONTRADICTION_LOG_PREFIX)] == [
        contradiction_msgs[0]
    ]


def test_a_contradicting_page_logs_the_contradiction_line_not_the_scope_line(
        monkeypatch, caplog):
    """...and the arm is really REACHED, not merely present.

    Deleting the arm leaves the page pending anyway (the scope arm catches it),
    so only the LOG can tell the difference — which is why this node reads the
    log and not the return value.
    """
    import logging

    monkeypatch.setenv(FLAG, "true")
    with caplog.at_level(logging.INFO, logger="app.services.price_service"):
        assert _fetch(_load("iherb_ga_cards_contradiction.html")) is None

    lines = [r.getMessage() for r in caplog.records]
    assert any(m.startswith(_CONTRADICTION_LOG_PREFIX) for m in lines), (
        "the contradiction arm did not run — this page pended through some "
        f"other arm: {[m for m in lines if 'iHerb pend' in m]}"
    )
    assert not any("document-level currency" in m for m in lines), (
        "the document-scope arm handled a contradiction; the two pends are no "
        "longer distinguishable in the logs"
    )
