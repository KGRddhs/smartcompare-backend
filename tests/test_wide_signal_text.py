"""Step 6 — WIDEN THE SHOPIFY SIGNAL TEXT (ENABLE_WIDE_SIGNAL_TEXT, default OFF).

`_match_shopify_product` builds

    _signal_text = f"{title} {_variant_title}".strip()

and derives BOTH the ranking (`variant_precision_rank` + `flagship_basis_bonus`)
AND the captured annotations (`extract_sizes_ml` / `extract_concentration`) from
it. The SAME `/products.json` row already carries `product_type`, `tags` and
`body_html`; folding them in lifts size capture 25.6% -> 62.7% and concentration
7.6% -> 24.1% over 999 live Shopify fragrance products.

THE CORRECTNESS CONSTRAINT this file exists to pin:

  (a) SELECTION MUST NOT MOVE. The widened text is used for the size /
      concentration EXTRACTION ONLY; the NARROW text keeps feeding
      `variant_precision_rank` and `flagship_basis_bonus`. Two variables, by
      deliberate design — see `test_ranking_still_reads_the_narrow_text` and
      `test_wide_ranking_would_have_flipped_the_winner`, which construct the
      catalog where a wide-ranking implementation ships a DIFFERENT (dearer)
      product and prove this implementation does not.

  (b) NO CROSS-CONTAMINATION. `body_html` is marketing copy: it names other
      products, flankers and bundle contents. `om.swissarabian.com`'s real
      "MUSK 07 EDP + BODY LOTION GIFT SET" body lists TWO sizes — the 50ml
      perfume and the 300ml BODY LOTION. A naive union takes
      `sorted({"50", "300"})[0]` == "300" (STRING sort!) and would ship the body
      lotion's size as the fragrance size. Pinned in
      `test_adversarial_gift_set_body_mentions_two_sizes`.

Every catalog here is offline: `tests/fixtures/shopify_products/*.json`, each
lifted from the embedded ProductJson blob of a CACHED PDP under `_proof/html/`
(see that directory's SOURCES.json). No network.
"""

import json
import time
from pathlib import Path

import pytest

import app.services.price_service as ps


FIXDIR = Path(__file__).parent / "fixtures" / "shopify_products"

# The flags whose rollback must NOT drag this one with it.
_SIBLING_FLAGS = (
    "ENABLE_EXACT_PRICE_GATE",
    "ENABLE_SALE_PRICE_FIRST",
    "ENABLE_OG_BRANCH_FIXES",
    "ENABLE_WIDE_CANDIDATE",
    "ENABLE_SHOPIFY_PDP_JSON",
)


def _catalog(name: str) -> dict:
    return json.loads((FIXDIR / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _clean_flag(monkeypatch):
    """Every test starts from an UNSET ENABLE_WIDE_SIGNAL_TEXT (the prod default)."""
    monkeypatch.delenv("ENABLE_WIDE_SIGNAL_TEXT", raising=False)
    yield


def _on(monkeypatch):
    monkeypatch.setenv("ENABLE_WIDE_SIGNAL_TEXT", "true")


# Real fixture -> (query, domain, store currency).
CASES = {
    "perfumistaaloud_com.json": ("Perfumusk", "perfumistaaloud.com", "BHD"),
    "armaf_ae.json": ("Odyssey Tyrant Special Edition", "armaf.ae", "AED"),
    "om_swissarabian_com.json": (
        "Musk 07 EDP + Body Lotion Gift Set", "om.swissarabian.com", "OMR",
    ),
}


def _match(name: str) -> dict:
    query, domain, currency = CASES[name]
    return ps._match_shopify_product(_catalog(name), query, currency, domain)


# ===========================================================================
# 1. THE FLAG
# ===========================================================================

def test_flag_defaults_off_when_unset():
    """Ships DORMANT — it can move a captured size, so it canaries first."""
    assert ps.wide_signal_text_enabled() is False


@pytest.mark.parametrize("val", ["true", "TRUE", " True ", "1", "yes", "on", "ON"])
def test_flag_on_for_the_allow_list(monkeypatch, val):
    monkeypatch.setenv("ENABLE_WIDE_SIGNAL_TEXT", val)
    assert ps.wide_signal_text_enabled() is True


@pytest.mark.parametrize(
    "val", ["", "  ", "false", "FALSE", "0", "no", "off", "maybe", "ture", "2"],
)
def test_flag_off_for_everything_else(monkeypatch, val):
    """Allow-list, not deny-list: an empty / misspelt value stays OFF."""
    monkeypatch.setenv("ENABLE_WIDE_SIGNAL_TEXT", val)
    assert ps.wide_signal_text_enabled() is False


def test_flag_is_read_per_call_not_cached_at_import(monkeypatch):
    assert ps.wide_signal_text_enabled() is False
    monkeypatch.setenv("ENABLE_WIDE_SIGNAL_TEXT", "true")
    assert ps.wide_signal_text_enabled() is True
    monkeypatch.setenv("ENABLE_WIDE_SIGNAL_TEXT", "false")
    assert ps.wide_signal_text_enabled() is False


@pytest.mark.parametrize("sibling", _SIBLING_FLAGS)
def test_flag_is_independent_of_the_sibling_flags(monkeypatch, sibling):
    """A master rollback of the exact-identity layer (or of any earlier step)
    must not silently change this one's state, in either direction."""
    monkeypatch.setenv(sibling, "false")
    assert ps.wide_signal_text_enabled() is False
    monkeypatch.setenv("ENABLE_WIDE_SIGNAL_TEXT", "true")
    assert ps.wide_signal_text_enabled() is True


def test_flag_is_not_registered_in_app_config():
    """House rule: app/config.py is a trap (ValidationError at import)."""
    cfg = (
        Path(__file__).parents[1] / "app" / "config.py"
    ).read_text(encoding="utf-8")
    assert "ENABLE_WIDE_SIGNAL_TEXT" not in cfg


# ===========================================================================
# 2. THE PURE TEXT BUILDER
# ===========================================================================

def test_builder_folds_type_tags_and_body_into_the_narrow_text():
    out = ps._wide_signal_capture_text(
        "Perfumusk Default Title",
        {
            "product_type": "Eau de Parfum",
            "tags": ["oud", "100ml"],
            "body_html": "<p>Musky &amp; woody</p><p>100 ml</p>",
        },
    )
    assert out.startswith("Perfumusk Default Title")
    for token in ("Eau de Parfum", "oud", "100ml", "Musky & woody", "100 ml"):
        assert token in out
    assert "<p>" not in out


def test_builder_strips_markup_unescapes_entities_and_collapses_whitespace():
    out = ps._wide_signal_capture_text(
        "T", {"body_html": "<div class='x'>a</div>\n\n<br/>   b &nbsp;&amp; 50&nbsp;ml</div>"},
    )
    assert "<" not in out and ">" not in out
    assert "&amp;" not in out and "&nbsp;" not in out
    assert "  " not in out  # runs collapsed to a single space
    assert "50" in out and "ml" in out


def test_builder_tolerates_missing_none_and_non_list_fields():
    assert ps._wide_signal_capture_text("T", {}) == "T"
    assert ps._wide_signal_capture_text(
        "T", {"product_type": None, "tags": None, "body_html": None},
    ) == "T"
    # Some payloads hand back tags as a comma string rather than a list.
    assert "oud" in ps._wide_signal_capture_text("T", {"tags": "oud, amber"})
    # The .js envelope's field names must work too (description / type).
    out = ps._wide_signal_capture_text(
        "T", {"type": "Perfume", "description": "<p>30ml</p>"},
    )
    assert "Perfume" in out and "30ml" in out


def test_builder_never_returns_none_or_drops_the_narrow_text():
    assert ps._wide_signal_capture_text("", {}) == ""
    assert ps._wide_signal_capture_text("Only Title", {"body_html": ""}) == "Only Title"


def test_body_cap_equals_the_repo_redos_bound():
    """The cap is not a fresh magic number: the body's plain-text budget IS the
    matchers' existing `_MATCH_INPUT_CAP` (512)."""
    assert ps._WIDE_SIGNAL_BODY_CAP == ps._MATCH_INPUT_CAP == 512


def test_each_segment_has_its_own_cap_so_one_long_field_cannot_starve_the_rest():
    out = ps._wide_signal_capture_text(
        "NARROW",
        {
            "product_type": "T" * 5000,
            "tags": ["G" * 5000],
            "body_html": "<p>" + ("B" * 50000) + "</p>",
        },
    )
    assert out.startswith("NARROW")
    assert out.count("T") <= ps._WIDE_SIGNAL_TYPE_CAP
    assert out.count("G") <= ps._WIDE_SIGNAL_TAGS_CAP
    assert out.count("B") <= ps._WIDE_SIGNAL_BODY_CAP
    # Total is bounded by narrow + the three segment budgets + separators.
    assert len(out) <= (
        len("NARROW") + ps._WIDE_SIGNAL_TYPE_CAP + ps._WIDE_SIGNAL_TAGS_CAP
        + ps._WIDE_SIGNAL_BODY_CAP + 8
    )


def test_a_tens_of_kb_body_is_bounded_and_fast():
    """A body_html can be tens of KB and this runs once per candidate product,
    999 of them on a real catalog. Bound the WORK, not just the output."""
    huge = ("<div style='%s'>lorem 100ml ipsum</div>" % ("x" * 400)) * 4000
    assert len(huge) > 1_500_000
    t0 = time.monotonic()
    out = ps._wide_signal_capture_text("T", {"body_html": huge})
    elapsed = time.monotonic() - t0
    assert len(out) <= ps._WIDE_SIGNAL_BODY_CAP + len("T") + 4
    assert elapsed < 0.25, "builder must not scan the whole body: %.3fs" % elapsed


def test_pathological_angle_brackets_do_not_blow_up():
    """`<[^<>]*>` (NOT `<[^>]*>`): every failed tag-open aborts at the next
    angle bracket, so a run of '<' cannot go quadratic."""
    for body in ("<" * 60000, "<a" * 40000, ">" * 60000, "<" + "z" * 60000):
        t0 = time.monotonic()
        ps._wide_signal_capture_text("T", {"body_html": body})
        assert time.monotonic() - t0 < 0.25


# ===========================================================================
# 3. FLAG OFF — the pre-change behaviour, pinned on the real fixtures
# ===========================================================================

FLAG_OFF_BASELINE = {
    "perfumistaaloud_com.json": {
        "amount": 2.5, "currency": "BHD", "original_currency": "BHD",
        "retailer": "perfumistaaloud.com",
        "url": "https://perfumistaaloud.com/products/perfumusk",
        "in_stock": True, "confidence": 1.0, "estimated": False,
        "source_method": "shopify_json", "concentration": None, "size": None,
        "title": "Perfumusk", "match_score": 1.0,
    },
    "armaf_ae.json": {
        "amount": 140.0, "currency": "AED", "original_currency": "AED",
        "retailer": "armaf.ae",
        "url": "https://armaf.ae/products/odyssey-tyrant-special-edition",
        "in_stock": True, "confidence": 1.0, "estimated": False,
        "source_method": "shopify_json", "concentration": None, "size": None,
        "title": "ODYSSEY TYRANT SPECIAL EDITION", "match_score": 1.0,
    },
    "om_swissarabian_com.json": {
        "amount": 3.0, "currency": "OMR", "original_currency": "OMR",
        "retailer": "om.swissarabian.com",
        "url": "https://om.swissarabian.com/products/musk-07-edp-body-lotion-gift-set",
        "in_stock": True, "confidence": 1.0, "estimated": False,
        "source_method": "shopify_json", "concentration": "EDP", "size": None,
        "title": "MUSK 07 EDP + BODY LOTION GIFT SET", "match_score": 1.0,
    },
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_flag_off_is_the_unchanged_8adaefb_dict(name):
    assert _match(name) == FLAG_OFF_BASELINE[name]


def test_flag_off_never_calls_the_builder(monkeypatch):
    """With the flag OFF nothing may even LOOK at body_html."""
    calls = []
    monkeypatch.setattr(
        ps, "_wide_signal_capture_text",
        lambda *a, **k: calls.append(a) or "",
    )
    for name in CASES:
        _match(name)
    assert calls == []


# ===========================================================================
# 4. FLAG ON — the measured capture lift, on the real fixtures
# ===========================================================================

def test_size_recovered_from_body_html(monkeypatch):
    """perfumistaaloud.com/products/perfumusk — the title is a bare 'Perfumusk'
    and the only variant is 'Default Title', so today the size is LOST. The real
    body_html carries '<p>100 ml</p>'."""
    assert _match("perfumistaaloud_com.json")["size"] is None
    _on(monkeypatch)
    got = _match("perfumistaaloud_com.json")
    assert got["size"] == "100ml"
    # No concentration is claimed: the copy says "Perfume", never "parfum"/EDP.
    assert got["concentration"] is None


def test_concentration_and_size_recovered_from_tags_and_body(monkeypatch):
    """armaf.ae — title carries neither axis; the real tags carry 'edp for her'
    and the real body_html opens 'Eau De Parfum 100ml'."""
    before = _match("armaf_ae.json")
    assert (before["concentration"], before["size"]) == (None, None)
    _on(monkeypatch)
    got = _match("armaf_ae.json")
    assert got["concentration"] == "EDP"
    assert got["size"] == "100ml"


@pytest.mark.parametrize("name", sorted(CASES))
def test_price_and_selection_are_byte_identical_with_the_flag_on(monkeypatch, name):
    off = _match(name)
    _on(monkeypatch)
    on = _match(name)
    assert set(off) == set(on)
    for key in off:
        if key in ("size", "concentration"):
            continue
        assert on[key] == off[key], "%s moved on %s" % (key, name)


@pytest.mark.parametrize("name", sorted(CASES))
def test_capture_is_additive_only_never_a_rewrite(monkeypatch, name):
    """Narrow-first: a value the narrow text ALREADY produced is authoritative.
    Flag ON may only fill a None — it may never change a non-None."""
    off = _match(name)
    _on(monkeypatch)
    on = _match(name)
    for key in ("size", "concentration"):
        if off[key] is not None:
            assert on[key] == off[key]


# ===========================================================================
# 5. ADVERSARIAL — body_html names OTHER products' sizes
# ===========================================================================

def test_adversarial_gift_set_body_mentions_two_sizes(monkeypatch):
    """om.swissarabian.com "MUSK 07 EDP + BODY LOTION GIFT SET" — the REAL
    body_html reads:

        Musk 07 Extrait de Parfum - 50ml
        Musk 07 Body Lotion - 300ml

    The 300ml is a BODY LOTION, not a fragrance size. A naive widened capture
    unions to {"50", "300"} and `sorted(...)[0]` is "300" (string sort), so it
    would ship the body lotion's size. Ambiguity -> abstain."""
    name = "om_swissarabian_com.json"
    assert _match(name)["size"] is None
    _on(monkeypatch)
    got = _match(name)
    assert got["size"] is None, "abstain, do not guess between 50ml and 300ml"
    assert got["concentration"] == "EDP"  # from the TITLE, narrow-first


def test_the_naive_union_really_would_have_shipped_the_body_lotion_size():
    """Guards the guard: if this ever stops holding, the abstention above has
    silently stopped testing anything."""
    prod = _catalog("om_swissarabian_com.json")["products"][0]
    wide = ps._wide_signal_capture_text(
        "%s %s" % (prod["title"], prod["variants"][0]["title"]), prod,
    )
    sizes = ps.extract_sizes_ml(wide)
    assert sizes == {"50", "300"}
    assert sorted(sizes)[0] == "300"  # the STRING sort the legacy line uses


def test_narrow_first_is_load_bearing_for_concentration(monkeypatch):
    """`extract_concentration` is FIRST-PATTERN-WINS and checks Extrait BEFORE
    EDP. So on an EDP whose copy mentions the Extrait flanker, a widened read
    would REWRITE the title's own EDP into "Extrait". Narrow-first forbids it —
    the widened text may only fill a None."""
    catalog = {
        "_store_currency": "BHD",
        "products": [{
            "title": "Musk 07 EDP", "handle": "musk-07", "vendor": "Swiss Arabian",
            "product_type": "Perfume", "tags": [],
            "body_html": "<p>Try the Musk 07 Extrait de Parfum as well.</p>",
            "variants": [{"title": "Default Title", "price": "3.000",
                          "available": True}],
        }],
    }
    prod = catalog["products"][0]
    wide = ps._wide_signal_capture_text("Musk 07 EDP Default Title", prod)
    assert ps.extract_concentration(wide) == "Extrait"  # what a rewrite would take
    _on(monkeypatch)
    assert ps._match_shopify_product(
        catalog, "Musk 07 EDP", "BHD", "x.com",
    )["concentration"] == "EDP"


def test_narrow_size_wins_over_a_different_body_size(monkeypatch):
    """The title is authoritative. A body that mentions a DIFFERENT size (a
    flanker, a related item, an "also available in" line) must not overwrite it.

    NOTE for a future editor: on the SIZE axis the two rules overlap. The
    widened text is a strict SUPERSET of the narrow text, so whenever the narrow
    text already carries a size and the body carries a different one the union
    holds >= 2 sizes and the ambiguity-abstention alone would already refuse.
    Narrow-first is kept as the explicit statement of intent (and it is the
    load-bearing rule on the CONCENTRATION axis, above)."""
    catalog = {
        "_store_currency": "BHD",
        "products": [{
            "title": "Perfumusk 50ml", "handle": "perfumusk-50",
            "vendor": "Perfumista Aloud", "product_type": "Perfume",
            "tags": ["100ml", "gift"],
            "body_html": "<p>Also available in 100 ml and 200 ml.</p>",
            "variants": [{"title": "Default Title", "price": "25.000",
                          "available": True}],
        }],
    }
    off = ps._match_shopify_product(catalog, "Perfumusk 50ml", "BHD", "x.com")
    assert off["size"] == "50ml"
    _on(monkeypatch)
    on = ps._match_shopify_product(catalog, "Perfumusk 50ml", "BHD", "x.com")
    assert on["size"] == "50ml"
    assert on["amount"] == off["amount"]


def test_single_unambiguous_body_size_is_taken(monkeypatch):
    """The counterpart: one distinct size in the widened text IS attributable."""
    catalog = {
        "_store_currency": "BHD",
        "products": [{
            "title": "Perfumusk", "handle": "perfumusk", "vendor": "Perfumista Aloud",
            "product_type": "Perfume", "tags": ["oud"],
            "body_html": "<p>100 ml</p><p>A 100ml bottle of musk.</p>",
            "variants": [{"title": "Default Title", "price": "25.000",
                          "available": True}],
        }],
    }
    _on(monkeypatch)
    assert ps._match_shopify_product(
        catalog, "Perfumusk", "BHD", "x.com",
    )["size"] == "100ml"


# ===========================================================================
# 6. (a) SELECTION CANNOT MOVE — the two-variable design, proved
# ===========================================================================

# An EDP whose copy mentions the Extrait flanker (everyday fragrance marketing).
# `extract_concentration` checks Extrait FIRST, so the WIDE text of product A
# reads "Extrait" while its TITLE reads EDP.
_FLIP_CATALOG = {
    "_store_currency": "BHD",
    "products": [
        {
            "title": "Musk 07 EDP", "handle": "musk-07-edp-cheap",
            "vendor": "Swiss Arabian", "product_type": "Perfume", "tags": [],
            "body_html": "<p>Discover the Musk 07 Extrait de Parfum too.</p>",
            "variants": [{"title": "Default Title", "price": "3.000",
                          "available": True}],
        },
        {
            "title": "Musk 07 EDP", "handle": "musk-07-edp-dear",
            "vendor": "Swiss Arabian", "product_type": "Perfume", "tags": [],
            "body_html": "<p>A deep sensual musk.</p>",
            "variants": [{"title": "Default Title", "price": "9.000",
                          "available": True}],
        },
    ],
}
_FLIP_QUERY = "Musk 07 EDP"


def test_wide_ranking_would_have_flipped_the_winner():
    """Proves the hazard is REAL, so the test below is not vacuous.

    Ranked on the NARROW text both products score conc_rank +1 -> the tie goes
    to the first (`_rank > best_rank` is strict) -> the 3.000 one.
    Ranked on the WIDE text product A scores -1 (Extrait vs the query's EDP) and
    loses to product B -> a 9.000 price, 3x dearer, for the same query."""
    prods = _FLIP_CATALOG["products"]
    narrow_a = "%s %s" % (prods[0]["title"], prods[0]["variants"][0]["title"])
    narrow_b = "%s %s" % (prods[1]["title"], prods[1]["variants"][0]["title"])
    wide_a = ps._wide_signal_capture_text(narrow_a, prods[0])
    wide_b = ps._wide_signal_capture_text(narrow_b, prods[1])

    assert ps.variant_precision_rank(_FLIP_QUERY, narrow_a)[0] == 1
    assert ps.variant_precision_rank(_FLIP_QUERY, narrow_b)[0] == 1
    assert ps.variant_precision_rank(_FLIP_QUERY, wide_a)[0] == -1
    assert ps.variant_precision_rank(_FLIP_QUERY, wide_b)[0] == 1


def test_the_winner_does_not_flip(monkeypatch):
    off = ps._match_shopify_product(_FLIP_CATALOG, _FLIP_QUERY, "BHD", "x.com")
    assert off["amount"] == 3.0
    _on(monkeypatch)
    on = ps._match_shopify_product(_FLIP_CATALOG, _FLIP_QUERY, "BHD", "x.com")
    assert on["amount"] == 3.0
    assert on["url"] == off["url"]
    assert on["title"] == off["title"]
    # narrow-first also protects the ANNOTATION: the title already said EDP.
    assert on["concentration"] == "EDP"


@pytest.mark.parametrize("name", sorted(CASES))
def test_ranking_still_reads_the_narrow_text(monkeypatch, name):
    """Direct proof of design (a): record what the two RANKING functions are
    fed, flag OFF vs flag ON, and require the arguments to be identical."""
    real_rank = ps.variant_precision_rank
    real_flagship = ps.flagship_basis_bonus

    def _run(flag_on):
        rank_args, flag_args = [], []

        def rank(*a, **k):
            rank_args.append(a)
            return real_rank(*a, **k)

        def flagship(*a, **k):
            flag_args.append(a)
            return real_flagship(*a, **k)

        ps.variant_precision_rank = rank
        ps.flagship_basis_bonus = flagship
        try:
            if flag_on:
                _on(monkeypatch)
            _match(name)
        finally:
            ps.variant_precision_rank = real_rank
            ps.flagship_basis_bonus = real_flagship
        return rank_args, flag_args

    seen = {"off": _run(False), "on": _run(True)}
    assert seen["on"] == seen["off"]
    # And the recorded text really is the narrow one — no body copy in it.
    for args in seen["on"][0]:
        assert len(args[1]) < 200
        assert "<" not in args[1]


def test_variant_selection_is_unchanged_on_a_multi_variant_product(monkeypatch):
    """A multi-variant product whose body_html names a size that matches NO
    variant. The chosen variant (and therefore the price) must not move."""
    catalog = {
        "_store_currency": "BHD",
        "products": [{
            "title": "Musk 07", "handle": "musk-07", "vendor": "Swiss Arabian",
            "product_type": "Perfume", "tags": ["30ml"],
            "body_html": "<p>Layer it with our 300ml Body Lotion.</p>",
            "variants": [
                {"title": "50 ml", "price": "5.000", "available": True},
                {"title": "100 ml", "price": "9.000", "available": True},
            ],
        }],
    }
    off = ps._match_shopify_product(catalog, "Musk 07", "BHD", "x.com")
    _on(monkeypatch)
    on = ps._match_shopify_product(catalog, "Musk 07", "BHD", "x.com")
    assert on["amount"] == off["amount"]
    assert on["size"] == off["size"]  # the VARIANT size is narrow, already set
