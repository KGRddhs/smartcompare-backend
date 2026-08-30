"""M10 UNIT A3 — THE SIZE/VARIANT DISCRIMINATOR POLICY FOR MULTI-OFFER PDPs.

THIS UNIT SHIPS NO BEHAVIOUR CHANGE AND ADDS NO FLAG. Read that first, because
the brief that opened it asked for a new `ENABLE_SIZE_DISCRIMINATOR` gate and
that flag would be actively harmful. Measured on 2026-08-31 against the
committed fixtures in ``tests/fixtures/shapes/``:

  * The policy the brief describes — "a size parsed FROM THE QUERY selects the
    matching variant, else the size the compare request carried, else pend;
    never smallest-wins, never first-wins" — is ALREADY what
    ``_adjudicate_jsonld_multiplicity`` does, rung for rung.
  * The compare-request size ALREADY reaches it:
    ``structured_comparison_service._get_price`` folds the parser's
    ``variant`` into ``full_name`` (:5185-5188) and that string IS the
    ``query_name`` the adjudicator reads.
  * The brief's identity-axis requirement — "an EDP/EDT mismatch still pends
    regardless of size match" — ALREADY HOLDS IN PRODUCTION, but not in the
    adjudicator: the exact gate rejects the cross-concentration candidate
    before the adjudicator ever sees it. Block H measures both halves of that
    and pins WHERE the axis lives, because a future wave that moves the size
    rung above the gate would silently serve an Eau de Parfum price for an
    Eau de Toilette query. Gate OFF it already would (127.5, measured).

A new default-OFF flag over an existing default-ON rung has only two possible
readings and both are wrong: OFF-means-nothing (a dead flag), or OFF disables
today's rung 2 — which is a behaviour REGRESSION in the flag's own default
state and breaks the house rule that flag-OFF is byte-identical to main. So
this unit pins the policy instead, and the only code it changes is prose:
``_MULTIPLICITY_POLICY`` (the numbered contract, quotable from here) plus the
docstring that carries it, and one comment at the compare-request site.

TWO CORRECTIONS TO THE BRIEF, both re-measured here, neither inherited:

  1. **There is no "flaconi 50/100/150ml class".** Both flaconi.de rows in the
     global corpus are HTTP 403 Magento SPA-404 bodies with no price at all.
     The real multi-size class with committed fixtures is marionnaud.fr /
     marionnaud.ch (3 sizes), matas.dk (2), kicks.se (size in the NAME) and
     spacenk.com (size in a ``size`` FIELD). Those are what block A uses.
  2. **One fixture's markup CAN be misread as declaring a default variant, and
     it is the worst possible page to trust.** lookfantastic's
     ``ProductGroup.productGroupID`` is ``"10021723"``, which is also
     ``hasVariant[1].sku`` — and that page's four variants are byte-identically
     named "...75ml" at 80 / 59.2 / 20 / 55 GBP. See block F.

SAY WHICH EXACT-GATE MODE EVERY ASSERTION IS IN. ``ENABLE_EXACT_PRICE_GATE``
ships ON; ``false`` isolates extraction from the gate and is the mode CLAUDE.md
documents for that. A pin that only asserted the shipped default would lose the
extraction behaviour; one that only asserted gate-off would claim a behaviour
production does not have. Every test below names its mode in its docstring.

Run per-file (the full suite makes live network calls and hangs):

    pytest tests/test_multiplicity_discriminator_policy.py \
        -m "not (live_unit or live_db or integration)" --timeout=120 \
        -p no:cacheprovider
"""

import json
from pathlib import Path

import pytest

from app.services import price_service as ps
from app.services.price_service import (
    _adjudicate_jsonld_multiplicity,
    extract_jsonld_price,
    extract_sizes_ml,
)

FIXTURES = Path(__file__).parent / "fixtures" / "shapes"

MARIONNAUD_FR = "fr_hybris_marionnaud_fr_graph_productgroup_3_sizes.html"
MATAS = "dk_matas_dk_productgroup_two_sizes.html"
KICKS = "se_kicks_se_productgroup_size_in_name.html"
SPACENK = "gb_spacenk_com_productgroup_size_field.html"
SEPHORA = "us_sephora_com_productgroup_sizeless_variants.html"
LOOKFANTASTIC = "gb_thg_lookfantastic_com_productgroup_duplicate_names.html"
NOTINO = "gb_notino_co_uk_offers_array_four_prices.html"
DECANTS = "us_shopify_scentsplit_com_productgroup_decants_and_bottle.html"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _ladder_on(monkeypatch):
    """The shape ladder is the shipped default; a test that needs it OFF says
    so. With it off the adjudicator never runs and ``pending_out`` is never
    written, so every assertion here would be vacuous."""
    monkeypatch.delenv("ENABLE_JSONLD_SHAPE_LADDER", raising=False)
    yield


def _gate_off(monkeypatch):
    """Extraction isolated from the exact gate."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")


def _gate_shipped(monkeypatch):
    """The production configuration."""
    monkeypatch.delenv("ENABLE_EXACT_PRICE_GATE", raising=False)
    assert ps.exact_gate_enabled() is True, "this asserts the SHIPPED default"


def resolve(fixture, brand, currency, query, category="fragrances"):
    """Returns ``(amount, name, sorted distinct pended amounts)``."""
    pending = []
    got = extract_jsonld_price(
        load(fixture), brand, currency, query,
        category=category, pending_out=pending,
    )
    pended = sorted({c["amount"] for c in pending[0]}) if pending else []
    return (
        None if got is None else got.get("amount"),
        None if got is None else got.get("name"),
        pended,
    )


# ===========================================================================
# A — RUNG 2: THE SIZE THE QUERY NAMES SELECTS THE VARIANT
#
# Four real pages carrying the size in three different places: marionnaud in a
# JSON-LD `size` field AND the name, matas in the name, kicks in the name, and
# spacenk in a `size` field only. `_shape_ladder_candidate_size_text` reads all
# of them, which is why one rung covers all four shapes.
# ===========================================================================
def test_a_a_a_sizeless_query_pends_every_marionnaud_size(monkeypatch):
    """GATE OFF. Nothing on the page says which of 30/50/75ML the query means,
    so the page pends all three rather than picking. This is rung 4."""
    _gate_off(monkeypatch)
    amount, _, pended = resolve(
        MARIONNAUD_FR, "Chloe", "EUR", "Chloe Nomade Eau de Parfum",
    )
    assert amount is None
    assert pended == [49.0, 127.5, 152.0]


@pytest.mark.parametrize(
    "size,expected",
    [("30ml", 49.0), ("50ml", 127.5), ("75ml", 152.0)],
)
def test_a_b_each_stocked_size_resolves_to_its_own_amount(
    monkeypatch, size, expected,
):
    """GATE OFF. The size on the query IS the discriminator. Same page, same
    three candidates, three different served prices."""
    _gate_off(monkeypatch)
    amount, name, pended = resolve(
        MARIONNAUD_FR, "Chloe", "EUR", f"Chloe Nomade Eau de Parfum {size}",
    )
    assert amount == expected
    assert pended == []
    assert size.replace("ml", "").lower() in (name or "").lower()


def test_a_c_an_unstocked_size_pends_and_never_substitutes(monkeypatch):
    """GATE OFF. Rung 2 fails CLOSED. marionnaud stocks 30/50/75ML; a 20ml
    query narrows to NOTHING and pends. It must not answer with the nearest
    size (49.0, the 30ML) — that is a different product, not a near miss."""
    _gate_off(monkeypatch)
    amount, _, pended = resolve(
        MARIONNAUD_FR, "Chloe", "EUR", "Chloe Nomade Eau de Parfum 20ml",
    )
    assert amount is None
    assert amount not in (49.0, 127.5, 152.0)
    assert pended == [49.0, 127.5, 152.0]


@pytest.mark.parametrize(
    "size,expected", [("50 ml", 759.95), ("100 ml", 1059.0)],
)
def test_a_d_matas_two_sizes(monkeypatch, size, expected):
    """GATE OFF. A second host, a second size spelling ("50 ml", spaced), the
    size carried in the variant NAME rather than a `size` field."""
    _gate_off(monkeypatch)
    amount, _, _ = resolve(
        MATAS, "Burberry", "DKK", f"Burberry Hero Eau de Parfum {size}",
    )
    assert amount == expected


def test_a_d_matas_sizeless_pends_both(monkeypatch):
    """GATE OFF. The same page with no size on the query pends both."""
    _gate_off(monkeypatch)
    amount, _, pended = resolve(
        MATAS, "Burberry", "DKK", "Burberry Hero Eau de Parfum",
    )
    assert amount is None
    assert pended == [759.95, 1059.0]


@pytest.mark.parametrize(
    "size,expected", [("30 ml", 769.0), ("90 ml", 1509.0)],
)
def test_a_e_kicks_size_in_the_variant_name(monkeypatch, size, expected):
    """SHIPPED DEFAULT. kicks.se carries the size in the name; the rung reads
    it there. Pinned in the production configuration on purpose — this is the
    shape that survives the exact gate intact."""
    _gate_shipped(monkeypatch)
    amount, _, _ = resolve(
        KICKS, "Armani", "SEK", f"Armani My Way Eau de Parfum {size}",
    )
    assert amount == expected


@pytest.mark.parametrize(
    "size,expected", [("50ml", 155.0), ("100ml", 225.0)],
)
def test_a_f_spacenk_size_in_a_size_field(monkeypatch, size, expected):
    """SHIPPED DEFAULT. spacenk declares "50ML"/"100ML" in a JSON-LD `size`
    FIELD. `_shape_ladder_candidate_size_text` joins size+name+title, so the
    field and the name are the same rung, not two."""
    _gate_shipped(monkeypatch)
    amount, _, _ = resolve(
        SPACENK, "Byredo", "GBP", f"Byredo Young Rose Eau de Parfum {size}",
    )
    assert amount == expected


def test_a_g_spacenk_sizeless_pends_both(monkeypatch):
    """SHIPPED DEFAULT. Without a size the same page pends 155 and 225."""
    _gate_shipped(monkeypatch)
    amount, _, pended = resolve(
        SPACENK, "Byredo", "GBP", "Byredo Young Rose Eau de Parfum",
    )
    assert amount is None
    assert pended == [155.0, 225.0]


# ===========================================================================
# B — RUNG 2'S SECOND SOURCE: THE SIZE THE COMPARE REQUEST CARRIED
#
# There is no third source and no separate code path. `_get_price`
# (structured_comparison_service.py:5185-5188) folds the parser's `variant`
# (its `size_or_count`) into `full_name`, and `full_name` IS the `query_name`
# the adjudicator reads, via fetch_page_price -> extract_price_from_html ->
# extract_jsonld_price. These two tests reproduce that assembly literally, so
# a refactor at :5188 that drops `variant` goes RED here instead of silently
# deleting the compare-request discriminator.
# ===========================================================================
def _full_name(brand: str, name: str, variant: str) -> str:
    """VERBATIM the assembly at structured_comparison_service.py:5185-5188."""
    if variant and variant.lower() in name.lower():
        return f"{brand} {name}".strip()
    return f"{brand} {name} {variant or ''}".strip()


def test_b_a_the_compare_request_variant_reaches_the_adjudicator(monkeypatch):
    """GATE OFF. The caller's size identity, threaded exactly as production
    threads it, resolves marionnaud's 50ML. If :5188 ever stops folding
    `variant` into `full_name`, `extract_sizes_ml` sees nothing and this page
    pends instead — which is what this test exists to make visible."""
    _gate_off(monkeypatch)
    query = _full_name("Chloe", "Nomade Eau de Parfum", "50ml")
    assert extract_sizes_ml(query) == {"50"}
    amount, _, _ = resolve(MARIONNAUD_FR, "Chloe", "EUR", query)
    assert amount == 127.5


def test_b_b_the_variant_already_in_name_shortcut_keeps_the_size(monkeypatch):
    """GATE OFF. The OTHER branch of :5185 — when the variant is already inside
    the name, the assembly does NOT append it again. The size must survive that
    branch too, or every already-sized product silently loses its
    discriminator."""
    _gate_off(monkeypatch)
    query = _full_name("Chloe", "Nomade Eau de Parfum 50ml", "50ml")
    assert query == "Chloe Nomade Eau de Parfum 50ml"
    assert extract_sizes_ml(query) == {"50"}
    amount, _, _ = resolve(MARIONNAUD_FR, "Chloe", "EUR", query)
    assert amount == 127.5


def test_b_c_a_sizeless_compare_request_pends_exactly_as_today(monkeypatch):
    """GATE OFF. No size anywhere in the compare request -> the third limb of
    the policy: pend. Not the smallest, not the first, not a guess."""
    _gate_off(monkeypatch)
    query = _full_name("Chloe", "Nomade Eau de Parfum", "")
    assert extract_sizes_ml(query) == set()
    amount, _, pended = resolve(MARIONNAUD_FR, "Chloe", "EUR", query)
    assert amount is None
    assert pended == [49.0, 127.5, 152.0]


# ===========================================================================
# C — RUNG 5: THE THREE PROHIBITIONS. THE ANTI-REGRESSION CORE.
#
# NEVER smallest. NEVER first-in-document. NEVER nearest-size. Every case below
# is a real committed fixture, not a synthetic — and each was chosen because
# its cheapest and its first are DIFFERENT numbers, so a test that passes here
# cannot be passing by coincidence.
# ===========================================================================
def test_c_a_never_smallest_notino(monkeypatch):
    """SHIPPED DEFAULT. notino.co.uk offers 74.88 / 51.42 / 88.1 / 60.5 in that
    document order. The cheapest is 51.42 and that is precisely what the
    pre-ladder code returned; the page's own survey recorded 74.88. The page
    pends. 51.42 must never be the answer."""
    _gate_shipped(monkeypatch)
    amount, _, pended = resolve(
        NOTINO, "Acqua dell' Elba", "GBP", "Acqua dell' Elba Arcipelago Women",
    )
    assert amount is None
    assert pended == [51.42, 60.5, 74.88, 88.1]
    assert amount != min(pended)


def test_c_b_never_first_in_document_lookfantastic(monkeypatch):
    """SHIPPED DEFAULT. lookfantastic's four variants are BYTE-IDENTICALLY
    named "Jean Paul Gaultier Le Male Eau de Toilette 75ml" at 80 / 59.2 / 20 /
    55 GBP in that order. First (80) and cheapest (20) are different numbers,
    so this single page falsifies both shortcuts at once. A size on the query
    cannot help: every candidate carries the SAME size."""
    _gate_shipped(monkeypatch)
    for query in (
        "Jean Paul Gaultier Le Male Eau de Toilette",
        "Jean Paul Gaultier Le Male Eau de Toilette 75ml",
    ):
        amount, _, pended = resolve(LOOKFANTASTIC, "Jean Paul Gaultier",
                                    "GBP", query)
        assert amount is None, f"{query!r} newly returns {amount}"
        assert pended == [20.0, 55.0, 59.2, 80.0]
        assert amount != 80.0 and amount != 20.0


def test_c_c_never_first_in_document_sephora(monkeypatch):
    """SHIPPED DEFAULT. sephora's first variant is the 199.0 — the number the
    adjudicator's own docstring names as the reason document order asserts
    nothing. Here first AND cheapest are both 199.0, which is exactly why it
    needs its own pin beside lookfantastic: a first-wins bug hides behind a
    never-smallest test on this page."""
    _gate_shipped(monkeypatch)
    amount, _, pended = resolve(SEPHORA, "Dior", "USD", "Dior Sauvage Elixir")
    assert amount is None
    assert pended == [199.0, 265.0, 330.0]
    assert amount != 199.0


def test_c_d_never_nearest_size(monkeypatch):
    """GATE OFF. marionnaud stocks 30/50/75ML. A 20ml query is closest to the
    30ML at 49.0. The answer is None. "Nearest" is a guess wearing arithmetic:
    a 20ml and a 30ml are different SKUs at different prices."""
    _gate_off(monkeypatch)
    amount, _, _ = resolve(
        MARIONNAUD_FR, "Chloe", "EUR", "Chloe Nomade Eau de Parfum 20ml",
    )
    assert amount is None


def test_c_e_a_narrow_spread_is_still_two_skus(monkeypatch):
    """The adjudicator called DIRECTLY, so no gate and no page are involved.
    amouage.com in the corpus pends [429.0, 429.14] — a 0.03% spread. There is
    no tolerance band below which a pick becomes safe, because the spread
    measures nothing about whether the two rows are the same product."""
    candidates = [
        {"amount": 429.0, "name": "Interlude Man", "in_stock": True},
        {"amount": 429.14, "name": "Interlude Man Extrait", "in_stock": True},
    ]
    assert _adjudicate_jsonld_multiplicity(candidates, "Amouage Interlude") is None


def test_c_f_the_adjudicator_returns_none_it_does_not_pick(monkeypatch):
    """The adjudicator called DIRECTLY with a spread the cheapest-pick bug used
    to eat: perfume.com's 2.81 out of {2.81 ... 24.91}, an 8.9x spread on one
    page. A sizeless query resolves nothing, so the contract is None."""
    amounts = [2.81, 6.99, 13.5, 24.91]
    candidates = [
        {"amount": a, "name": "Pink Sugar", "in_stock": True} for a in amounts
    ]
    assert _adjudicate_jsonld_multiplicity(candidates, "Aquolina Pink Sugar") is None


# ===========================================================================
# D — THE DECANTS RULING IS A SPECIAL CASE OF RUNG 2, NOT AN EXCEPTION TO
#     RUNG 5.
#
#     Ahmed, 2026-08-30:  "decant price for decants queries"
#
# The full behavioural pin for this page lives in
# tests/test_jsonld_shape_ladder.py block H (:733-892) and is NOT duplicated
# here. What this block adds is the POLICY reading: the word "decants" in the
# query is acting as the size/variant discriminator — rung 2 doing its job —
# and NOT a standing "decants win" rule, which rung 5 forbids. The two
# directions in one test is the whole point.
# ===========================================================================
def test_d_the_ruling_is_query_conditional_not_decants_always_win(monkeypatch):
    """GATE OFF (block H measures the shipped default, which pends both ways).

    Same page, same three variants, two queries, two different answers:
      "xerjoff ilm sample decants" -> 8.99, the 1ml Sample
      "Xerjoff 'Ilm 50ml"          -> 250.0, the manufacturer's bottle
    and the bare "xerjoff ilm", which names neither, pends both. If a future
    wave turns the ruling into "the decant always wins", the middle assertion
    goes red — which is the point of writing it this way rather than as three
    separate tests."""
    _gate_off(monkeypatch)
    decant, decant_name, _ = resolve(
        DECANTS, "Xerjoff", "USD", "xerjoff ilm sample decants",
    )
    assert decant == 8.99
    assert decant_name == "'Ilm - 1ml Sample"

    bottle, bottle_name, _ = resolve(
        DECANTS, "Xerjoff", "USD", "Xerjoff 'Ilm 50ml",
    )
    assert bottle == 250.0
    assert bottle_name == "'Ilm - 50ml in Manufacturer's bottle"

    bare, _, pended = resolve(DECANTS, "Xerjoff", "USD", "xerjoff ilm")
    assert bare is None, "a bare query must not inherit the decant ruling"
    assert pended == [8.99, 250.0]


def test_d_the_glass_spray_is_unreachable_until_the_m6_flag_flips(monkeypatch):
    """SHIPPED DEFAULT for ENABLE_FRAGRANCE_GLASS_EXEMPTION (unset = OFF).

    The third variant, "'Ilm - 2ml Glass Spray" at 16.99, is not a candidate
    for ANY query because "glass" is in ACCESSORY_KEYWORDS. That is a real
    over-rejection on a decants page — a 2ml glass-spray decant is the product,
    not an accessory to it — and the M6 flag ENABLE_FRAGRANCE_GLASS_EXEMPTION
    (default OFF, price_service.py:936-1020) lifts it.

    IF M10 FLIPS THAT FLAG, THIS TEST GOES RED AND 16.99 BECOMES REACHABLE.
    That is the intended signal, not a breakage: record the new expected value
    here and in tests/test_jsonld_shape_ladder.py::test_h_e."""
    monkeypatch.delenv("ENABLE_FRAGRANCE_GLASS_EXEMPTION", raising=False)
    assert ps.is_accessory_for_category("'Ilm - 2ml Glass Spray",
                                        "fragrances") is True
    assert ps.is_accessory_for_category("'Ilm - 1ml Sample",
                                        "fragrances") is False


# ===========================================================================
# E — THE SIZELESS-VARIANT RESIDUAL. FAIL-CLOSED, AND CORRECT.
# ===========================================================================
def test_e_sephora_sizeless_variants_pend_even_for_a_sized_query(monkeypatch):
    """GATE OFF. THIS IS CORRECT BEHAVIOUR AND MUST STAY CORRECT — it is not a
    bug to be fixed later.

    sephora's three hasVariant members are all named bare "Sauvage Elixir" and
    carry no size text in any field. Rung 2 narrows to the candidates whose
    size text intersects the query's, so a "60ml" query narrows to NOTHING and
    the page fail-closes. The alternative — picking a variant whose size is
    UNKNOWN against a query that explicitly named one — is a wrong price
    served as a genuine one.

    Do NOT "fix" this by matching on price rank, position or count."""
    _gate_off(monkeypatch)
    for query in ("Dior Sauvage Elixir", "Dior Sauvage Elixir 60ml"):
        amount, _, pended = resolve(SEPHORA, "Dior", "USD", query)
        assert amount is None, f"{query!r} newly returns {amount}"
        assert pended == [199.0, 265.0, 330.0]


# ===========================================================================
# F — RUNG 0 ("the page declares a default") IS UNIMPLEMENTED BECAUSE NOTHING
#     MEASURED NEEDS IT — AND THE ONE PAGE THAT LOOKS LIKE IT DOES, DOESN'T.
# ===========================================================================
def _jsonld_nodes(fixture: str):
    """Every JSON-LD object in a fixture, flattened, with its ProductGroup
    membership recorded."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(load(fixture), "html.parser")
    groups, members = [], []

    def walk(node, inside_variant=False):
        if isinstance(node, list):
            for item in node:
                walk(item, inside_variant)
            return
        if not isinstance(node, dict):
            return
        raw_type = node.get("@type")
        types = raw_type if isinstance(raw_type, list) else [raw_type]
        if any(t == "ProductGroup" for t in types if isinstance(t, str)):
            groups.append(node)
        if inside_variant:
            members.append(node)
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                walk(value, inside_variant or key == "hasVariant")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            walk(json.loads(script.string or script.get_text() or ""))
        except (ValueError, TypeError):
            continue
    return groups, members


def test_f_a_no_fixture_declares_a_default_variant(monkeypatch):
    """No page in the committed corpus carries `hasDefaultVariant` or a
    canonical-offer flag, in any casing, anywhere in its bytes.

    Rung 0 ("if the page declares a DEFAULT variant, take it") therefore sits
    above rung 2 in the written policy and is DELIBERATELY unimplemented:
    adding it speculatively would be code with no measured consumer, and it
    would need its own flag (`ENABLE_DECLARED_DEFAULT_VARIANT`, default OFF)
    the day one appears.

    WHEN THIS TEST GOES RED, a page has started declaring one — that is the
    signal to implement rung 0, not to relax the assertion."""
    declared = ("hasdefaultvariant", "defaultvariant", "iscanonical",
                "canonicaloffer", "isdefault")
    offenders = {}
    for path in sorted(FIXTURES.glob("*.html")):
        raw = path.read_text(encoding="utf-8").lower()
        hits = [token for token in declared if token in raw]
        if hits:
            offenders[path.name] = hits
    assert offenders == {}, f"a page now declares a default: {offenders}"


def test_f_b_productgroupid_is_a_group_id_not_a_default_pointer(monkeypatch):
    """THE TRAP, PINNED. `productGroupID` is present on 8 of the 14 fixtures,
    and on lookfantastic it EQUALS a member's sku ("10021723" ==
    hasVariant[1].sku). A rung 0 that read `productGroupID` as "the group names
    its default member" would resolve that page to hasVariant[1] — the 59.2,
    the second of four BYTE-IDENTICALLY named "...75ml" variants at
    80 / 59.2 / 20 / 55. The one page in the set whose markup could be read as
    declaring a default is the canonical unresolvable-ambiguity page.

    schema.org's `productGroupID` is the GROUP's own identifier. THG simply
    reuses its lead SKU as the group id. That collision is a naming
    coincidence, not a declaration, and this test records it so a future rung 0
    cannot be built on it."""
    groups, members = _jsonld_nodes(LOOKFANTASTIC)
    group_ids = {g.get("productGroupID") for g in groups
                 if isinstance(g.get("productGroupID"), str)}
    assert group_ids == {"10021723"}
    member_skus = {m.get("sku") for m in members if isinstance(m.get("sku"), str)}
    assert "10021723" in member_skus, (
        "the collision this test documents has disappeared — re-check whether "
        "rung 0 is now buildable"
    )
    # And the page still pends, which is the behaviour that matters.
    _gate_shipped(monkeypatch)
    amount, _, pended = resolve(
        LOOKFANTASTIC, "Jean Paul Gaultier", "GBP",
        "Jean Paul Gaultier Le Male Eau de Toilette 75ml",
    )
    assert amount is None
    assert pended == [20.0, 55.0, 59.2, 80.0]


# ===========================================================================
# G — THE POLICY IS WRITTEN DOWN, NUMBERED, AND QUOTABLE.
#
# The rung numbering is restated in prose in three places (the adjudicator's
# docstring, extract_jsonld_price's `pending_out` paragraph, and
# CAPTURE_AMBIGUOUS_PRICE's comment block). `_MULTIPLICITY_POLICY` is the one
# copy those defer to, so a future edit changes the contract in one place
# instead of drifting three.
# ===========================================================================
def test_g_a_the_policy_constant_states_every_rung_in_order():
    """The contract exists as a module-level constant and numbers rungs 0-5."""
    policy = ps._MULTIPLICITY_POLICY
    assert isinstance(policy, str)
    for rung in ("0.", "1.", "2.", "3.", "4.", "5."):
        assert rung in policy, f"rung {rung} missing from the written policy"


def test_g_b_the_policy_names_all_three_prohibitions():
    """Rung 5 is the reason this unit exists. All three prohibited shortcuts
    must be named in the text, so nobody has to reconstruct them from the
    code."""
    policy = ps._MULTIPLICITY_POLICY.lower()
    for prohibition in ("smallest", "first", "nearest"):
        assert prohibition in policy, f"{prohibition}-wins is not prohibited in writing"


def test_g_c_the_policy_points_at_the_compare_request_size_source():
    """Rung 2's second source is a fact about a call chain in ANOTHER module,
    and a refactor there deletes it silently. The policy must name the site."""
    policy = ps._MULTIPLICITY_POLICY
    assert "structured_comparison_service" in policy
    assert "5185" in policy


def test_g_d_the_adjudicator_docstring_carries_the_policy():
    """The constant is not a detached comment: the function that implements
    the policy documents itself with it."""
    assert ps._MULTIPLICITY_POLICY in (
        _adjudicate_jsonld_multiplicity.__doc__ or ""
    )


# ===========================================================================
# H — THE IDENTITY AXES. A SIZE MATCH IS NOT AN IDENTITY MATCH.
#
# THE BRIEF'S REQUIREMENT, MEASURED IN BOTH MODES: "an EDP/EDT mismatch still
# pends regardless of size match." It HOLDS in production — and the tests below
# pin WHERE it holds, which is not where you would guess.
#
# The adjudicator has no concentration axis. It narrows on SIZE and then counts
# distinct amounts. What keeps an Eau de Toilette query off marionnaud's Eau de
# Parfum 50mL is the EXACT GATE, upstream: `_selection_match` never admits the
# candidate, so the adjudicator is handed a smaller list.
#
# That is a real and load-bearing ordering. Anything that moves the size rung
# above the identity gate, or that "helpfully" resolves a pend by size when the
# gate has already rejected the candidates, re-opens the leak measured in
# test_h_a. Both tests are needed: one shows the leak exists when the gate is
# out of the way, the other shows the gate closing it.
# ===========================================================================
@pytest.mark.parametrize(
    "query,expected",
    [
        ("Chloe Nomade Eau de Toilette 50ml", 127.5),
        ("Chloe Nomade EDT 50ml", 127.5),
        ("Chloe Nomade Eau de Toilette 30ml", 49.0),
    ],
)
def test_h_a_gate_off_a_size_match_crosses_the_concentration_axis(
    monkeypatch, query, expected,
):
    """GATE OFF — EXTRACTION ISOLATED, NOT A SERVED BEHAVIOUR.

    With the exact gate out of the way, an Eau de TOILETTE query resolves
    marionnaud's Eau de PARFUM at the matching size. The adjudicator's rung 2
    is a SIZE rung; it has no opinion about concentration. This is measured and
    recorded, NOT endorsed — it is the leak the exact gate exists to close, and
    the reason the size rung must never be lifted above it."""
    _gate_off(monkeypatch)
    amount, name, _ = resolve(MARIONNAUD_FR, "Chloe", "EUR", query)
    assert amount == expected
    assert "Eau de Parfum" in (name or ""), (
        "the served candidate is the EDP — that is the point of this pin"
    )


@pytest.mark.parametrize(
    "query",
    [
        "Chloe Nomade Eau de Toilette 50ml",
        "Chloe Nomade EDT 50ml",
        "Chloe Nomade Eau de Toilette 30ml",
        "Chloe Nomade Eau de Toilette",
    ],
)
def test_h_b_shipped_an_edt_query_pends_however_well_the_size_matches(
    monkeypatch, query,
):
    """SHIPPED DEFAULT — THE PRODUCTION BEHAVIOUR, AND THE BRIEF'S RULE.

    Every one of these queries names a size marionnaud actually stocks, and
    every one of them yields NO price, because the concentration axis is
    contradicted. Size agreement does not buy an identity match."""
    _gate_shipped(monkeypatch)
    amount, _, _ = resolve(MARIONNAUD_FR, "Chloe", "EUR", query)
    assert amount is None, f"{query!r} newly serves {amount} across EDP/EDT"


def test_h_c_shipped_the_matching_concentration_still_resolves(monkeypatch):
    """SHIPPED DEFAULT. The control for test_h_b: pinning the EDT rejection
    costs the EDP nothing. Without this, an over-rejection that killed the page
    outright would pass test_h_b silently."""
    _gate_shipped(monkeypatch)
    amount, _, _ = resolve(
        MARIONNAUD_FR, "Chloe", "EUR", "Chloe Nomade Eau de Parfum 50ml",
    )
    assert amount == 127.5


def test_h_d_the_axis_is_enforced_by_the_gate_not_the_adjudicator(monkeypatch):
    """SHIPPED DEFAULT. Names the mechanism, so the ordering above is a pinned
    fact rather than an inference from two black-box results.

    `_selection_match` — the runtime selector the orchestrator calls — rejects
    the EDP candidate for an EDT query and admits it for an EDP query. The
    adjudicator is downstream of that."""
    _gate_shipped(monkeypatch)
    candidate = "CHLOE CHLOÉ NOMADE Eau de Parfum 50mL"
    assert ps._selection_match(
        "Chloe Nomade Eau de Parfum 50ml", candidate, "fragrances") is True
    assert ps._selection_match(
        "Chloe Nomade Eau de Toilette 50ml", candidate, "fragrances") is False
    assert ps._selection_match(
        "Chloe Nomade EDT 50ml", candidate, "fragrances") is False


def test_h_e_matas_confirms_the_axis_on_a_second_host(monkeypatch):
    """SHIPPED DEFAULT. Not a marionnaud artifact: matas.dk behaves the same,
    serving the 50 ml EDP and pending the 50 ml EDT."""
    _gate_shipped(monkeypatch)
    served, _, _ = resolve(
        MATAS, "Burberry", "DKK", "Burberry Hero Eau de Parfum 50 ml")
    assert served == 759.95
    for query in ("Burberry Hero Eau de Toilette 50 ml",
                  "Burberry Hero EDT 50 ml"):
        amount, _, _ = resolve(MATAS, "Burberry", "DKK", query)
        assert amount is None, f"{query!r} newly serves {amount}"


# ===========================================================================
# I — THIS UNIT ADDED NO FLAG, AND THE LADDER FLAG STILL DISARMS EVERYTHING.
# ===========================================================================
def test_i_a_no_size_discriminator_flag_was_introduced():
    """The brief asked for ENABLE_SIZE_DISCRIMINATOR. It was NOT added, and
    this test says so out loud so the absence reads as a decision rather than
    an omission.

    A default-OFF flag over a default-ON rung that already implements the
    policy has two readings and both are wrong: OFF-means-nothing (dead flag,
    unfalsifiable), or OFF disables today's rung 2 — a behaviour regression in
    the flag's own default state, and a violation of flag-OFF-is-byte-identical.
    The policy is pinned by the tests above instead."""
    source = Path(ps.__file__).read_text(encoding="utf-8")
    assert "ENABLE_SIZE_DISCRIMINATOR" not in source
    # And the adjudicator reads no environment at all: it is pure over its two
    # arguments, so there is nothing for a flag to gate in the first place.
    assert "getenv" not in (_adjudicate_jsonld_multiplicity.__doc__ or "")
    marker = "def _adjudicate_jsonld_multiplicity("
    body = source[source.index(marker):]
    body = body[:body.index("\n# The contract above")]
    assert "os.getenv" not in body


def test_i_b_the_ladder_flag_off_disarms_the_adjudicator(monkeypatch):
    """LADDER OFF + GATE OFF. With ENABLE_JSONLD_SHAPE_LADDER off the
    adjudicator never runs, `pending_out` is never written, and the legacy
    pre-S4 path is restored. Pinned here so a reader of this file cannot
    mistake the pends above for unconditional behaviour."""
    monkeypatch.setenv("ENABLE_JSONLD_SHAPE_LADDER", "false")
    _gate_off(monkeypatch)
    pending = []
    extract_jsonld_price(
        load(MARIONNAUD_FR), "Chloe", "EUR", "Chloe Nomade Eau de Parfum",
        category="fragrances", pending_out=pending,
    )
    assert pending == [], "the ladder flag no longer disarms the pend channel"


def test_i_c_the_empty_query_legacy_contract_is_left_alone():
    """The adjudicator is deliberately NOT applied when `query_name` is empty:
    that is the documented pre-S4 caller contract, which has no identity to
    adjudicate against. Rung 5 does not reach it, and this unit did not change
    it. Its own pin lives at
    tests/test_jsonld_shape_ladder.py::test_c_f_the_no_query_legacy_path_is_left_alone.
    """
    assert extract_sizes_ml("") == set()
    doc = _adjudicate_jsonld_multiplicity.__doc__ or ""
    assert "query_name" in doc and "empty" in doc.lower()
