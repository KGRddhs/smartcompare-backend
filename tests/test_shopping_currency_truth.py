"""W4-1 — the shopping rung stamps the currency it parsed, and ``local_bhd``
needs a host (``ENABLE_SHOPPING_CURRENCY_TRUTH``, default OFF, read per call).

Findings PO-PRICE-TRUTH-01 / PO-PRICE-TRUTH-02 / PO-RECORDED-MEASURED-02.
Spec: ``.qa-w4/W4_1_UNIT_SPEC.md`` (measured at ``ed75dc70``; every number in
this file was re-measured through the real functions before it was written).

Runs against ``price_service.extract_price_from_shopping`` (the front door) and
``structured_comparison_service._seed_shortcircuit_candidates`` (the M13-10
re-selection stash — the back door that MUST agree) with
``ENABLE_EXACT_PRICE_GATE=false`` to isolate extraction, exactly as
``tests/test_m13_shopping_strict_currency.py`` does. No network, no LIVE. A
single-item result of ``None`` means the candidate PENDED.

RULING 2 (FABLE REVIEW), measured at ``ed75dc70`` (RED phase, 2026-09-11):
``source_router.registry_tier("noon.com")`` is ``'gcc'`` (first row wins:
``SOURCE_REGISTRY[23]`` = ``noon.com``/``gcc``), but
``_registry_row_for_host("noon.com", where=lambda s: s.tier == "bahrain")``
returns the SECOND literal ``noon.com`` row, ``SOURCE_REGISTRY[24]`` =
``tier='bahrain'``/``currency='BHD'``; ``alosraonline.com`` is a single
``bahrain`` row (``SOURCE_REGISTRY[8]``). Both hold with
``ENABLE_BH_GCC_CATALOG_SOURCES`` unset (44 literal rows, 24 bahrain-tier —
the CI/test state) AND with it ON (319 rows, 117 bahrain-tier — the prod
state), because both rows are LITERAL rows ahead of the catalog. So the
registry last resort finds both, and ``noon.com/p`` / ``alosraonline.com``
stay ``local_bhd`` under the flag — the table row stands and is pinned in
test 10 below; the four Preserve pin files (flag-OFF ``noon.com/p``) are
unaffected either way.

Flag-gate note (measured): ``is_price_showable``'s ``non_pdp_url`` backstop is
``if enforce_correctness and exact_gate_enabled()``, so test 12 sets
``ENABLE_EXACT_PRICE_GATE=true`` (the prod default) for its showable call —
with the file-wide ``false`` isolation the pend can never fire.
"""
import pytest

from app.services import price_service as ps
from app.services.structured_comparison_service import get_comparison_service

NAME = "Acme Widget Deluxe"
BH_LINK = "https://bahrain.sharafdg.com/product/x"
GOOGLE_LINK = "https://www.google.com/search?ibp=oshop&q=acme+widget+deluxe"

TRUTH = "ENABLE_SHOPPING_CURRENCY_TRUTH"
STRICT = "ENABLE_SHOPPING_STRICT_CURRENCY"
EXTENDED = "ENABLE_EXTENDED_FALLBACK_RATES"

EXTENDED_CODES = ("TRY", "PLN", "CAD", "JOD", "SEK", "DKK", "CHF", "EGP", "NOK", "AUD")

# Arabic display glyphs as UNICODE LITERALS (never escaped) so the residue
# transform sees exactly what Serper returns.
AED_GLYPH_1399 = "1,399 د.إ"
SAR_GLYPH_250 = "250 ر.س"
SAR_GLYPH_ARABIC_INDIC_123 = "١٢٣ ر.س"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Extraction-only isolation + every currency flag UNSET so each test states
    the flag state it asserts (a stray ``.env`` value must never leak in)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    for name in (TRUTH, STRICT, EXTENDED, "ENABLE_LONGEST_HOST_MATCH"):
        monkeypatch.delenv(name, raising=False)


def _flags(monkeypatch, *, truth=None, strict=None, extended=None):
    for name, val in ((TRUTH, truth), (STRICT, strict), (EXTENDED, extended)):
        if val is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, val)


def _item(price_str, *, link=BH_LINK, source="Sharaf DG", title=NAME):
    item = {"title": title, "price": price_str, "source": source}
    if link is not None:
        item["link"] = link
    return item


def _run_full(price_str, *, ask="BHD", region="bahrain", link=BH_LINK, source="Sharaf DG"):
    return ps.extract_price_from_shopping(
        NAME, [_item(price_str, link=link, source=source)], ask, shopping_region=region,
    )


def _run(price_str, *, ask="BHD", region="bahrain", link=BH_LINK, source="Sharaf DG"):
    r = _run_full(price_str, ask=ask, region=region, link=link, source=source)
    return None if r is None else (r["amount"], r["currency"], r["source_method"])


def _seed(price_str, *, link=BH_LINK, source="Sharaf DG", currency="BHD", region="bahrain"):
    """Run the tier1_shopping stash over ONE item (the ``_seed`` harness of
    ``tests/test_m21_currency_parity.py``); return the seeded candidates."""
    svc = get_comparison_service()
    svc._shopping_items_cache[NAME] = [_item(price_str, link=link, source=source)]
    svc._seed_shortcircuit_candidates(
        NAME, kind="tier1_shopping", currency=currency, shopping_region=region,
    )
    return svc._price_candidates.get(NAME, [])


# ---------------------------------------------------------------------------
# 1 / 2 — GCC display tokens: the parse receives the currency the string names
# ---------------------------------------------------------------------------
GCC_TOKEN_CASES = [
    # (price_str, flag-ON expected, flag-OFF (today) expected)
    ("22.500 BD", (22.5, "BHD", "local_bhd"), (22500.0, "BHD", "local_bhd")),
    ("8.750 KD", (10.76, "BHD", "converted_usd"), (8750.0, "BHD", "local_bhd")),
    ("250 SR", (25.07, "BHD", "converted_usd"), (250.0, "BHD", "local_bhd")),
    ("32,000 QR", (3305.6, "BHD", "converted_usd"), (32000.0, "BHD", "local_bhd")),
]


@pytest.mark.parametrize(
    "price_str,want_on,_want_off", GCC_TOKEN_CASES, ids=[c[0] for c in GCC_TOKEN_CASES],
)
def test_1_gcc_display_token_resolves_before_parse_flag_on(monkeypatch, price_str, want_on, _want_off):
    """RED — ``22.500 BD`` is 22.5 BHD (minor unit 3), not 22,500; ``8.750 KD``
    is 8.75 KWD converted (``round(8.75*1.23, 2) == 10.76``) and labelled
    ``converted_usd``; ``250 SR`` -> 25.07; ``32,000 QR`` -> 3305.6."""
    _flags(monkeypatch, truth="true")
    assert _run(price_str) == want_on


@pytest.mark.parametrize(
    "price_str,_want_on,want_off", GCC_TOKEN_CASES, ids=[c[0] for c in GCC_TOKEN_CASES],
)
def test_2_gcc_display_token_flag_off_is_todays_value(monkeypatch, price_str, _want_on, want_off):
    """PIN — flag OFF (STRICT and EXTENDED unset) is byte-for-byte today's
    (wrong) parse: the rung's flag-OFF identity for the parse half."""
    _flags(monkeypatch)  # everything unset
    assert _run(price_str) == want_off


# ---------------------------------------------------------------------------
# 3 / 4 — a known, non-target ISO code the effective table cannot convert
# ---------------------------------------------------------------------------
UNCONVERTIBLE_ISO = [f"{code} 1,299.00" for code in EXTENDED_CODES] + ["TRY 1.299,00"]


@pytest.mark.parametrize("strict", ["false", "true"], ids=["strict-off", "strict-on"])
@pytest.mark.parametrize("price_str", UNCONVERTIBLE_ISO)
def test_3_known_foreign_iso_unconvertible_pends_flag_on(monkeypatch, price_str, strict):
    """RED — a well-formed non-target ISO code we KNOW (a key of
    FALLBACK_RATES_EXTENDED) but cannot convert (EXTENDED OFF) is FOREIGN and
    pends. Today every one ships 1299.0 BHD ``local_bhd``."""
    _flags(monkeypatch, truth="true", strict=strict, extended="false")
    assert _run(price_str) is None


@pytest.mark.parametrize("strict", ["false", "true"], ids=["strict-off", "strict-on"])
def test_4_known_foreign_iso_converts_with_extended_on(monkeypatch, strict):
    """RED — with EXTENDED ON step 1 resolves TRY, so it CONVERTS
    (``round(1299*0.0094, 2) == 12.21``) and is labelled honestly. Today:
    STRICT OFF ships 1299 ``local_bhd``; STRICT+EXTENDED pends."""
    _flags(monkeypatch, truth="true", strict=strict, extended="true")
    assert _run("TRY 1.299,00") == (12.21, "BHD", "converted_usd")


# ---------------------------------------------------------------------------
# 5 — a google.com link is never local_bhd
# ---------------------------------------------------------------------------
def test_5_google_search_link_is_never_local_bhd_flag_on(monkeypatch):
    """RED — ``local_bhd`` requires host evidence; a ``google.com/search`` link
    is a listing url with NO host evidence, so the row is relabelled
    ``converted_usd`` with amount and url UNCHANGED."""
    _flags(monkeypatch, truth="true")
    r = _run_full("259.44", link=GOOGLE_LINK, source="Best Buy")
    assert r is not None
    assert r["source_method"] == "converted_usd", r
    assert r["amount"] == 259.44, r
    assert r["url"] == GOOGLE_LINK, r
    assert r["currency"] == "BHD", r


def test_5b_gcc_token_on_google_link_amount_fixed_and_label_honest(monkeypatch):
    """RED — ``22.500 BD`` on the google link: amount fixed (22.5) AND label
    honest (``converted_usd``) — both defects of case A+F closed together."""
    _flags(monkeypatch, truth="true")
    assert _run("22.500 BD", link=GOOGLE_LINK, source="Best Buy") == (22.5, "BHD", "converted_usd")


# ---------------------------------------------------------------------------
# 6 — the TARGET-currency Arabic glyph ships on all four TRUTH x STRICT states
# ---------------------------------------------------------------------------
TARGET_GLYPH_CASES = [
    (SAR_GLYPH_250, "SAR", "saudi_arabia", (250.0, "SAR", "local_bhd")),
    (SAR_GLYPH_ARABIC_INDIC_123, "SAR", "saudi_arabia", (123.0, "SAR", "local_bhd")),
    (AED_GLYPH_1399, "AED", "uae", (1399.0, "AED", "local_bhd")),
]


@pytest.mark.parametrize("strict", ["false", "true"], ids=["strict-off", "strict-on"])
@pytest.mark.parametrize("truth", ["false", "true"], ids=["truth-off", "truth-on"])
@pytest.mark.parametrize(
    "price_str,ask,region,want", TARGET_GLYPH_CASES,
    ids=["sar-glyph-ascii", "sar-glyph-arabic-indic", "aed-glyph"],
)
def test_6_target_currency_glyph_ships_on_every_state(monkeypatch, price_str, ask, region, want, truth, strict):
    """PIN — the M13-09 over-rejection fix must not regress: a price in the
    TARGET currency's own glyph is GENUINE on every flag combination."""
    _flags(monkeypatch, truth=truth, strict=strict)
    assert _run(price_str, ask=ask, region=region) == want


# ---------------------------------------------------------------------------
# 7 — composition with STRICT (Fable ruling 1): TRUTH resolves the glyph FIRST
# ---------------------------------------------------------------------------
def test_7_foreign_glyph_truth_off_strict_on_still_pends(monkeypatch):
    """PIN (unchanged M13-09 contract) — TRUTH OFF + STRICT ON: the AED glyph
    on a BHD ask pends."""
    _flags(monkeypatch, truth="false", strict="true")
    assert _run(AED_GLYPH_1399) is None


@pytest.mark.parametrize("strict", ["false", "true"], ids=["strict-off", "strict-on"])
def test_7_foreign_glyph_truth_on_converts_like_the_iso_form(monkeypatch, strict):
    """RED — TRUTH ON (STRICT OFF or ON): the resolvable AED glyph on a BHD ask
    CONVERTS to ``round(1399*0.1024, 2) == 143.26`` ``converted_usd``, exactly
    as ``AED 1,399`` already does (test_m13_09_iso_aed_never_ships_target_raw).
    STRICT's clause (b) no longer fires because ``detected_cur`` is now
    ``'AED'``, not None."""
    _flags(monkeypatch, truth="true", strict=strict)
    assert _run(AED_GLYPH_1399) == (143.26, "BHD", "converted_usd")


# ---------------------------------------------------------------------------
# 8 — STRICT's letter-dollar rule survives; the R$ collision is STRICT's, not ours
# ---------------------------------------------------------------------------
def test_8_letter_dollar_collision_stays_strict_s_job(monkeypatch):
    """PIN — ``R$ 1.399``: TRUTH ON + STRICT ON pends; TRUTH ON + STRICT OFF is
    today's 526.02 (1399 wrongly converted as USD) — TRUTH leaves a
    ``detect_currency`` hit alone."""
    _flags(monkeypatch, truth="true", strict="true")
    assert _run("R$ 1.399") is None
    _flags(monkeypatch, truth="true", strict="false")
    r = _run("R$ 1.399")
    assert r is not None and r[0] == 526.02, r


# ---------------------------------------------------------------------------
# 9 — the stash back door agrees with the front door
# ---------------------------------------------------------------------------
def test_9a_stash_gcc_token_resolves_flag_on(monkeypatch):
    """RED — the stash seeds ``22.500 BD`` as 22.5, not 22500."""
    _flags(monkeypatch, truth="true")
    cands = _seed("22.500 BD")
    assert [c["value"] for c in cands] == [22.5], cands


def test_9b_stash_google_link_is_converted_usd_flag_on(monkeypatch):
    """RED — the stash never seeds a google-linked row as ``local_bhd``."""
    _flags(monkeypatch, truth="true")
    cands = _seed("259.44", link=GOOGLE_LINK, source="Best Buy")
    assert len(cands) == 1, cands
    assert cands[0]["source_method"] == "converted_usd", cands
    assert cands[0]["value"] == 259.44, cands


def test_9c_stash_unconvertible_foreign_iso_seeds_nothing_flag_on(monkeypatch):
    """RED — ``TRY 1.299,00`` with EXTENDED OFF seeds nothing (pend parity)."""
    _flags(monkeypatch, truth="true", extended="false")
    assert _seed("TRY 1.299,00") == []


def test_9d_stash_flag_off_is_todays_values(monkeypatch):
    """PIN — flag OFF the stash seeds exactly what it seeds today."""
    _flags(monkeypatch)
    assert [(c["value"], c["source_method"]) for c in _seed("22.500 BD")] == [(22500.0, "local_bhd")]
    assert [(c["value"], c["source_method"]) for c in _seed("259.44", link=GOOGLE_LINK, source="Best Buy")] == [(259.44, "local_bhd")]
    assert [(c["value"], c["source_method"]) for c in _seed("TRY 1.299,00")] == [(1299.0, "local_bhd")]


# ---------------------------------------------------------------------------
# 10 / 11 — host-evidence table (23 dry-run URL shapes, every row pinned)
# ---------------------------------------------------------------------------
HOST_TABLE = [
    # (link, expected flag-ON label)
    ("https://bolo.bh/product/x", "local_bhd"),                        # .bh
    ("https://bahrain.sharafdg.com/product/x", "local_bhd"),           # bahrain. subdomain
    ("https://gcc.luluhypermarket.com/en-bh/p/x", "local_bhd"),        # /en-bh/
    ("https://www.luluhypermarket.com/en-bh/p/x", "local_bhd"),        # /en-bh/ (tier None)
    ("https://www.extra.com/en-bh/p/x", "local_bhd"),                  # /en-bh/
    ("https://www.sephora.me/bh-en/p/x", "local_bhd"),                 # /bh-en/
    ("https://www.noon.com/bahrain-en/p/x", "local_bhd"),              # /bahrain-en/
    ("https://www.talabat.com/bahrain/x", "local_bhd"),                # /bahrain/
    ("https://alosraonline.com/x", "local_bhd"),                       # registry bahrain row
    ("https://noon.com/p", "local_bhd"),                               # registry SECOND (bahrain) noon row — ruling 2
    (GOOGLE_LINK, "converted_usd"),                                    # listing url
    ("https://www.google.com/shopping/product/123", "converted_usd"),  # any google.com host -> listing_url (polish round)
    ("https://www.noon.com/uae-en/p/x", "converted_usd"),              # other-country locale
    ("https://www.extra.com/en-sa/p/x", "converted_usd"),              # other-country locale (registry bahrain!)
    ("https://uae.sharafdg.com/product/x", "converted_usd"),           # other-country subdomain
    ("https://www.sharafdg.com/product/x", "converted_usd"),           # gcc tier, no bahrain row
    ("https://www.amazon.ae/dp/x", "converted_usd"),                   # gcc tier, no bahrain row
    ("https://www.amazon.com/dp/x", "converted_usd"),                  # global tier
    ("https://www.bestbuy.com/site/x", "converted_usd"),               # off-registry, no marker
    ("https://bh.iherb.com/pr/x", "converted_usd"),                    # global tier beats the bh. label (#52 product call)
    ("https://www.talabat.com/uae/x", "converted_usd"),                # other-country segment (registry bahrain!)
    ("https://ksa.swissarabian.com/products/x", "converted_usd"),      # other-country subdomain
    (None, "converted_usd"),                                           # MISSING link -> build_retailer_url search url (a listing url)
]
HOST_IDS = [("missing-link" if u is None else u.split("://", 1)[1].rstrip("/")) for u, _ in HOST_TABLE]


@pytest.mark.parametrize("link,want", HOST_TABLE, ids=HOST_IDS)
def test_10_local_bhd_requires_host_evidence_flag_on(monkeypatch, link, want):
    """RED on every ``converted_usd`` row — ``BHD 12.500`` parses to 12.5 on
    every link (unchanged); only the LABEL follows the host evidence. Amount,
    currency and url are untouched by the relabel."""
    _flags(monkeypatch, truth="true")
    r = _run_full("BHD 12.500", link=link, source="Best Buy")
    assert r is not None, link
    assert r["amount"] == 12.5, r
    assert r["currency"] == "BHD", r
    assert r["source_method"] == want, (link, r["source_method"])
    if link is None:
        # today's build_retailer_url fallback — a retailer SEARCH url, itself a listing url
        assert r["url"] and ps._is_listing_url(r["url"]), r["url"]
    else:
        assert r["url"] == link, r


@pytest.mark.parametrize("link,_want", HOST_TABLE, ids=HOST_IDS)
def test_11_host_table_flag_off_is_local_bhd_everywhere(monkeypatch, link, _want):
    """PIN — flag OFF every row carries today's ``local_bhd`` stamp (the host
    contributes nothing to the label at HEAD)."""
    _flags(monkeypatch)
    r = _run_full("BHD 12.500", link=link, source="Best Buy")
    assert r is not None, link
    assert (r["amount"], r["currency"], r["source_method"]) == (12.5, "BHD", "local_bhd"), r


# ---------------------------------------------------------------------------
# 12 — the relabel un-pends NOTHING (W4-2 ordering)
# ---------------------------------------------------------------------------
def test_12_showable_chokepoint_still_pends_google_row_non_pdp_url(monkeypatch):
    """PIN — ``is_price_showable(..., enforce_correctness=True)`` on the flag-ON
    google row still pends ``non_pdp_url``: the relabel does not un-pend
    anything (that is W4-2's job and the reason for the merge/flip ordering).

    The chokepoint backstop is gated on ``exact_gate_enabled()`` as well as
    ``enforce_correctness`` (measured), so the showable call runs with
    ``ENABLE_EXACT_PRICE_GATE=true`` — the prod default."""
    _flags(monkeypatch, truth="true")
    r = _run_full("259.44", link=GOOGLE_LINK, source="Best Buy")
    assert r is not None
    assert r["url"] == GOOGLE_LINK
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    assert ps.is_price_showable(NAME, r, enforce_correctness=True) is False
    assert r.get("guard_rejected") == "non_pdp_url", r


# ===========================================================================
# FABLE REWORK RULING (2026-09-11, after the adversary's DEFECTIVE verdict)
# R1..R5 pins. Each row below reddens EXACTLY when its rung is deleted; the
# mutation for each is named in its docstring and was run from byte snapshots.
# ===========================================================================
import logging  # noqa: E402 — grouped with the rework pins it serves

KSA_LINK = "https://ksa.swissarabian.com/products/x"
PS_LOGGER = "app.services.price_service"
SCS_LOGGER = "app.services.structured_comparison_service"
NON_BHD_ASKS = ["SAR", "AED", "KWD", "QAR", "OMR", "sar"]


def _truth_lines(caplog):
    return [r.getMessage() for r in caplog.records if "[SHOPPING_CURRENCY_TRUTH]" in r.getMessage()]


def _capture(caplog):
    caplog.set_level(logging.INFO, logger=PS_LOGGER)
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)


# ---------------------------------------------------------------------------
# R1 (MAJOR) — step 3 is a BAHRAIN-shelf rule: its host vocabulary applies ONLY
# when the ask currency is BHD; the no_link / listing_url pair is region-agnostic
# ---------------------------------------------------------------------------
def test_r1a_non_bhd_ask_keeps_native_label_front_door(monkeypatch):
    """R1a — SAR ask, region saudi_arabia, ``250 SR`` on a KSA store keeps
    ``(250.0, 'SAR', 'local_bhd')`` with the flag ON, unchanged from HEAD. The
    first green applied the Bahrain vocabulary to every ask and measured
    ``converted_usd`` (reason other_country) here — and at
    structured_comparison_service ~:6662 a converted_usd Tier-1 price is PARKED,
    so every non-Bahrain region lost its native shopping short-circuit.
    MUTATION: drop the BHD scoping (apply the vocabulary to every ask) -> red."""
    _flags(monkeypatch, truth="true")
    assert _run("250 SR", ask="SAR", region="saudi_arabia", link=KSA_LINK) == (250.0, "SAR", "local_bhd")


def test_r1a_non_bhd_ask_keeps_native_label_stash(monkeypatch):
    """R1a, back door — the stash seeds the same KSA row ``local_bhd`` on a SAR ask."""
    _flags(monkeypatch, truth="true")
    cands = _seed("250 SR", link=KSA_LINK, currency="SAR", region="saudi_arabia")
    assert [(c["value"], c["source_method"]) for c in cands] == [(250.0, "local_bhd")], cands


def test_r1b_non_bhd_ask_listing_url_relabels_front_and_stash(monkeypatch, caplog):
    """R1b — SAR ask, the google search link: ``converted_usd`` with
    ``reason=listing_url`` on BOTH doors (a listing URL is not a shelf for ANY
    region). GREEN against the first green, which ran every rung on every ask;
    MUTATION: stop running the agnostic pair for non-BHD asks -> red."""
    _flags(monkeypatch, truth="true")
    _capture(caplog)
    r = _run_full("259.44", ask="SAR", region="saudi_arabia", link=GOOGLE_LINK, source="Best Buy")
    assert r is not None and (r["amount"], r["currency"], r["source_method"]) == (259.44, "SAR", "converted_usd"), r
    cands = _seed("259.44", link=GOOGLE_LINK, source="Best Buy", currency="SAR", region="saudi_arabia")
    assert [(c["value"], c["source_method"]) for c in cands] == [(259.44, "converted_usd")], cands
    lines = _truth_lines(caplog)
    assert sum("relabel local_bhd->converted_usd host=google.com reason=listing_url" in ln for ln in lines) == 2, lines


def test_r1c_non_bhd_ask_no_link_relabels_front_and_stash(monkeypatch, caplog):
    """R1c — SAR ask, link None (today's ``build_retailer_url`` search fallback):
    ``converted_usd`` with ``reason=no_link`` on BOTH doors. Same mutation as R1b."""
    _flags(monkeypatch, truth="true")
    _capture(caplog)
    r = _run_full("259.44", ask="SAR", region="saudi_arabia", link=None, source="Best Buy")
    assert r is not None and (r["amount"], r["currency"], r["source_method"]) == (259.44, "SAR", "converted_usd"), r
    cands = _seed("259.44", link=None, source="Best Buy", currency="SAR", region="saudi_arabia")
    assert [(c["value"], c["source_method"]) for c in cands] == [(259.44, "converted_usd")], cands
    lines = _truth_lines(caplog)
    assert sum("relabel local_bhd->converted_usd host= reason=no_link" in ln for ln in lines) == 2, lines


@pytest.mark.parametrize("ask", NON_BHD_ASKS)
def test_r1_helper_non_bhd_ask_past_the_agnostic_pair_is_true_with_no_reason(ask):
    """R1, the predicate itself — for every non-BHD ask (case-insensitive) the
    Bahrain vocabulary is skipped: a KSA store returns True with NO reason
    appended, while the agnostic pair still fires with its reason."""
    reasons = []
    assert ps._shopping_bh_host_evidence(KSA_LINK, ask_currency=ask, reason_out=reasons) is True
    assert reasons == []
    reasons = []
    assert ps._shopping_bh_host_evidence(GOOGLE_LINK, ask_currency=ask, reason_out=reasons) is False
    assert reasons == ["listing_url"]
    reasons = []
    assert ps._shopping_bh_host_evidence(None, ask_currency=ask, reason_out=reasons) is False
    assert reasons == ["no_link"]


def test_r1d_bhd_ask_on_ksa_host_stays_converted_usd_other_country(monkeypatch):
    """R1d — the BHD ask on the same KSA host stays ``converted_usd`` (test 10
    row kept); here with the reason the predicate reports."""
    _flags(monkeypatch, truth="true")
    assert _run("BHD 12.500", link=KSA_LINK, source="Best Buy") == (12.5, "BHD", "converted_usd")
    reasons = []
    assert ps._shopping_bh_host_evidence(KSA_LINK, ask_currency="BHD", reason_out=reasons) is False
    assert reasons == ["other_country"]


# ---------------------------------------------------------------------------
# R2 — conflicting markers resolve toward NO evidence (other_country first)
# ---------------------------------------------------------------------------
CONFLICT_LINKS = [
    "https://uae.sharafdg.com/en-bh/product/x",      # other-country subdomain + BH path segment
    "https://bahrain.sharafdg.com/en-sa/product/x",  # BH subdomain + other-country path segment
]


@pytest.mark.parametrize("link", CONFLICT_LINKS, ids=["uae-sub+en-bh-path", "bahrain-sub+en-sa-path"])
def test_r2_conflicting_markers_resolve_to_no_evidence(monkeypatch, link):
    """R2 — a URL naming another country ANYWHERE (subdomain label OR first
    path segment) is contradictory evidence; a contradiction must not mint a
    genuine, 7-day-cached, KPI-counted label. RED against the first green
    (both earned ``local_bhd``). MUTATION: evaluate the BH-marker rung before
    the other-country rung (the first green's order) -> both rows red."""
    _flags(monkeypatch, truth="true")
    assert _run("BHD 12.500", link=link, source="Best Buy") == (12.5, "BHD", "converted_usd")
    reasons = []
    assert ps._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=reasons) is False
    assert reasons == ["other_country"]


# ---------------------------------------------------------------------------
# R3 — compound price strings are a STATED LIMIT (pin of the limit, not a fix)
# ---------------------------------------------------------------------------
def test_r3_compound_price_string_is_a_stated_limit(monkeypatch):
    """PIN OF A LIMIT (R3, follow-up PO-PRICE-TRUTH-01c) — ``From 22.500 BD``:
    the residue is ``FromBD`` (the M13-09 transform, deliberately unchanged), so
    step 1 resolves nothing and the string still parses as 22,500 ``local_bhd``
    with the flag ON, exactly as at HEAD. This asserts TODAY'S outcome so the
    canary reader is not surprised; it is not the desired value."""
    _flags(monkeypatch, truth="true")
    assert _run("From 22.500 BD") == (22500.0, "BHD", "local_bhd")


# ---------------------------------------------------------------------------
# R5 — pins for the rungs the adversary showed unproven
# ---------------------------------------------------------------------------
RUNG_PINS = [
    # (link, flag-ON label, reasons the predicate reports)
    ("https://example-store.bh/p/x", "local_bhd", []),                # R5.1 the .bh TLD rung — OFF-registry host
    ("https://bh.example-store.com/p/x", "local_bhd", []),            # R5.2 the BH subdomain-label rung — OFF-registry host
    ("https://bolo.bh/search?q=x", "converted_usd", ["listing_url"]),  # R5.3 the listing-url rung on a BH-evidenced REGISTRY host
    ("https://bh.iherb.com/pr/x", "converted_usd", ["global_tier"]),   # R5.4 the global-tier rung (beats the bh. label)
]


@pytest.mark.parametrize(
    "link,want,want_reasons", RUNG_PINS,
    ids=["r5.1-bh-tld-off-registry", "r5.2-bh-label-off-registry", "r5.3-listing-on-bh-host", "r5.4-global-tier"],
)
def test_r5_rung_pins_each_reddens_only_when_its_rung_is_deleted(monkeypatch, link, want, want_reasons):
    """R5.1-R5.4 — one row per rung, chosen so NO other rung can carry it:
    ``example-store.bh`` / ``bh.example-store.com`` are off-registry (tier None,
    no bahrain row — measured), so only the TLD / subdomain-label rung earns
    them ``local_bhd`` (bolo.bh and bahrain.sharafdg.com are registry rows and
    prove nothing for those rungs); ``bolo.bh/search?q=x`` is a listing URL on
    a BH-evidenced registry host, so only the listing rung can relabel it;
    ``bh.iherb.com`` pins the global-tier rung. NOTE (R5.4): ``www.amazon.com``
    in test 10 is a TABLE row, not a rung pin — with the global rung deleted it
    still relabels via the ``no_bh_evidence`` fallthrough.
    MUTATIONS: ``.bh`` endswith -> False (X4) reds r5.1; the subdomain-label
    check -> False (X5) reds r5.2; delete the listing rung (X7) reds r5.3;
    delete the global rung (X8) reds r5.4."""
    _flags(monkeypatch, truth="true")
    r = _run_full("BHD 12.500", link=link, source="Best Buy")
    assert r is not None and (r["amount"], r["currency"], r["source_method"]) == (12.5, "BHD", want), r
    reasons = []
    assert ps._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=reasons) is (want == "local_bhd")
    assert reasons == want_reasons


@pytest.mark.parametrize("extended", ["false", "true"], ids=["extended-off", "extended-on"])
def test_r5_5_three_decimal_only_iso_pends_on_both_extended_states(monkeypatch, extended):
    """R5.5 — ``IQD 1,299``: IQD is three-decimal and in NO rate table (base 13
    codes; extended adds AUD/CAD/CHF/DKK/EGP/JOD/NOK/PLN/SEK/TRY — measured), so
    it is known ONLY through the ``_THREE_DECIMAL_CURRENCIES |
    _ZERO_DECIMAL_CURRENCIES`` half of ``_shopping_known_currency_codes`` and
    pends on both doors, EXTENDED off AND on. Flag OFF ships 1299 ``local_bhd``.
    MUTATION: drop that half of the vocabulary (X16b) -> both rows red."""
    _flags(monkeypatch, truth="true", extended=extended)
    assert _run("IQD 1,299") is None
    assert _seed("IQD 1,299") == []
    _flags(monkeypatch, extended=extended)
    assert _run("IQD 1,299") == (1299.0, "BHD", "local_bhd")


# ---------------------------------------------------------------------------
# R5.6 — the canary log lines are ASSERTED (the vocabulary the PR advertises)
# ---------------------------------------------------------------------------
def test_r5_6_canary_relabel_line_carries_reason_listing_url(monkeypatch, caplog):
    """R5.6 — the google row emits the relabel line with ``reason=listing_url``.
    MUTATION: delete the front-door logger.info -> red."""
    _flags(monkeypatch, truth="true")
    _capture(caplog)
    _run_full("259.44", link=GOOGLE_LINK, source="Best Buy")
    lines = _truth_lines(caplog)
    assert any(
        "relabel local_bhd->converted_usd host=google.com reason=listing_url for " + NAME in ln for ln in lines
    ), lines


def test_r5_6_canary_relabel_line_carries_reason_no_host(monkeypatch, caplog):
    """R4 + R5.6 — ``'not a url'`` relabels via ``no_host`` (as do ``'https://'``
    and ``'javascript:alert(1)'``, measured) and the line says so; ``no_host``
    is part of the advertised ``reason=`` vocabulary."""
    _flags(monkeypatch, truth="true")
    _capture(caplog)
    r = _run_full("BHD 12.500", link="not a url", source="Best Buy")
    assert r is not None and r["source_method"] == "converted_usd", r
    lines = _truth_lines(caplog)
    assert any("relabel local_bhd->converted_usd host= reason=no_host for " + NAME in ln for ln in lines), lines


def test_r5_6_canary_pend_line_carries_the_code(monkeypatch, caplog):
    """R5.6 — the pend line carries the ISO code (``IQD``) on BOTH doors, each
    asserted on its OWN module logger (fix round: the stash line was unpinned —
    replacing its code argument with a literal left the file green, Y1).
    MUTATIONS: the front-door or the stash pend line's code argument -> red."""
    _flags(monkeypatch, truth="true", extended="false")
    _capture(caplog)
    assert _run("IQD 1,299") is None
    assert _seed("IQD 1,299") == []
    want = "[SHOPPING_CURRENCY_TRUTH] pend unconvertible IQD for " + NAME
    for logger_name in (PS_LOGGER, SCS_LOGGER):
        lines = [r.getMessage() for r in caplog.records if r.name == logger_name]
        assert want in lines, (logger_name, lines)


# ===========================================================================
# FIX ROUND (post-rework adversary, 2026-09-23) — each pin below reddens under
# the named mutation, run from a byte snapshot with a sha-verified restore.
# ===========================================================================
def test_fx_bhd_scope_is_case_insensitive():
    """The BHD scope reads ``(ask_currency or '').upper()``: a lowercase ``bhd``
    ask must still run the Bahrain vocabulary (a KSA store -> other_country; an
    off-registry ``.bh`` store -> evidence). ``test_r1_helper[sar]`` cannot
    prove this ('sar' is non-BHD either way).
    MUTATION Y4: drop ``.upper()`` from the scope check -> red."""
    reasons = []
    assert ps._shopping_bh_host_evidence(KSA_LINK, ask_currency="bhd", reason_out=reasons) is False
    assert reasons == ["other_country"]
    reasons = []
    assert ps._shopping_bh_host_evidence("https://www.bestbuy.com/site/x", ask_currency="bhd", reason_out=reasons) is False
    assert reasons == ["no_bh_evidence"]


INVALID_LINK = "http://[invalid"


def test_fx_host_classifier_error_fails_closed_on_both_doors(monkeypatch, caplog):
    """The fail-closed rung: ``urlparse('http://[invalid')`` raises inside the
    BHD branch, so the row relabels ``converted_usd`` with
    ``reason=host_classifier_error`` on BOTH doors, and the canary line says so.
    MUTATION Y3: ``return _no('host_classifier_error')`` -> ``return True``
    (fail OPEN, mints a genuine label) -> red."""
    _flags(monkeypatch, truth="true")
    _capture(caplog)
    reasons = []
    assert ps._shopping_bh_host_evidence(INVALID_LINK, ask_currency="BHD", reason_out=reasons) is False
    assert reasons == ["host_classifier_error"]
    assert _run("BHD 12.500", link=INVALID_LINK, source="Best Buy") == (12.5, "BHD", "converted_usd")
    cands = _seed("BHD 12.500", link=INVALID_LINK, source="Best Buy")
    assert [(c["value"], c["source_method"]) for c in cands] == [(12.5, "converted_usd")], cands
    for logger_name in (PS_LOGGER, SCS_LOGGER):
        lines = [r.getMessage() for r in caplog.records if r.name == logger_name]
        assert any("relabel local_bhd->converted_usd" in ln and "reason=host_classifier_error for " + NAME in ln for ln in lines), (logger_name, lines)
    # flag OFF: today's label, untouched
    _flags(monkeypatch)
    assert _run("BHD 12.500", link=INVALID_LINK, source="Best Buy") == (12.5, "BHD", "local_bhd")


def test_fx_host_classifier_error_on_a_registry_failure(monkeypatch):
    """The same rung for a REGISTRY error: ``bolo.bh`` (a .bh host AND a
    bahrain registry row, local_bhd in test 10) relabels ``converted_usd``
    reason ``host_classifier_error`` when the registry lookup raises — a
    classifier crash never mints a genuine label. MUTATION Y3 -> red."""
    from app.services import source_router

    def _boom(*_a, **_k):
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(source_router, "registry_tier", _boom)
    _flags(monkeypatch, truth="true")
    reasons = []
    assert ps._shopping_bh_host_evidence("https://bolo.bh/product/x", ask_currency="BHD", reason_out=reasons) is False
    assert reasons == ["host_classifier_error"]
    assert _run("BHD 12.500", link="https://bolo.bh/product/x", source="Best Buy") == (12.5, "BHD", "converted_usd")


MULTI_COUNTRY_ROWS = [
    # (link, reasons) — bahrain-tier registry hosts that trade in other countries
    ("https://www.talabat.com/iraq/p/x", ["other_country"]),     # new token: iraq
    ("https://www.talabat.com/lebanon/p/x", ["other_country"]),  # new token: lebanon
    ("https://www.talabat.com/eg/p/x", ["other_country"]),       # new token: eg
    ("https://www.talabat.com/en-jo/p/x", ["other_country"]),    # new token: jo (locale form)
    ("https://www.talabat.com/iq/p/x", ["other_country"]),       # new token: iq
    ("https://www.sephora.me/lb-en/p/x", ["other_country"]),     # new token: lb (locale form)
    ("https://www.talabat.com/en_sa/p/x", ["other_country"]),    # underscore fold
    ("https://www.talabat.com/sa_en/p/x", ["other_country"]),    # underscore fold
    ("https://www.sephora.me/p/x", ["no_bh_evidence"]),          # row locale_paths ('/bh-en',), path under none
    ("https://www.boutiqaat.com/p/x", ["no_bh_evidence"]),       # row locale_paths ('/en-bh',)
    ("https://www.nasserpharmacy.com/p/x", ["no_bh_evidence"]),  # row locale_paths ('/bh-en',)
]


@pytest.mark.parametrize("link,want_reasons", MULTI_COUNTRY_ROWS, ids=[u.split("://", 1)[1] for u, _ in MULTI_COUNTRY_ROWS])
def test_fx_multi_country_registry_host_needs_a_bahrain_path(monkeypatch, link, want_reasons):
    """A bahrain-tier registry row is not a Bahrain shelf when the URL names
    another country (the vocabulary now covers the measured Iraq / Lebanon /
    ISO-egypt/jordan shapes and the underscore locale spelling), or when the
    row declares its Bahrain ``locale_paths`` and the path is under none of
    them. RED at the rework green (every row earned local_bhd).
    MUTATIONS: drop the new tokens (iraq/lebanon/eg/jo/iq/lb rows red); drop
    the underscore fold (en_sa/sa_en rows red); drop the locale_paths check
    (sephora/boutiqaat/nasserpharmacy rows red). Flag OFF: local_bhd."""
    _flags(monkeypatch, truth="true")
    reasons = []
    assert ps._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=reasons) is False
    assert reasons == want_reasons
    assert _run("BHD 12.500", link=link, source="Best Buy") == (12.5, "BHD", "converted_usd")
    cands = _seed("BHD 12.500", link=link, source="Best Buy")
    assert [(c["value"], c["source_method"]) for c in cands] == [(12.5, "converted_usd")], cands
    _flags(monkeypatch)
    assert _run("BHD 12.500", link=link, source="Best Buy") == (12.5, "BHD", "local_bhd")


LOCALE_PATH_CONTROLS = [
    "https://www.sephora.me/bh-en/p/x",       # under the row's /bh-en
    "https://www.boutiqaat.com/en-bh/p/x",    # under the row's /en-bh
    "https://www.nasserpharmacy.com/bh-en",   # the locale path itself
    "https://www.talabat.com/bahrain/p/x",    # no locale_paths row, BH segment
    "https://alosraonline.com/x",             # no locale_paths row, host-only (ruling 2)
    "https://noon.com/p",                     # no locale_paths row, host-only (ruling 2)
]


@pytest.mark.parametrize("link", LOCALE_PATH_CONTROLS, ids=[u.split("://", 1)[1] for u in LOCALE_PATH_CONTROLS])
def test_fx_bahrain_path_and_locale_less_rows_keep_local_bhd(monkeypatch, link):
    """Over-rejection controls for the fix round: a path under the row's own
    Bahrain locale, and a bahrain row that declares NO locale_paths, keep
    ``local_bhd`` with the flag ON."""
    _flags(monkeypatch, truth="true")
    reasons = []
    assert ps._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=reasons) is True, reasons
    assert reasons == []
    assert _run("BHD 12.500", link=link, source="Best Buy") == (12.5, "BHD", "local_bhd")


OM_LINK = "https://om.swissarabian.com/products/x"


@pytest.mark.parametrize("price_str", ["RO 12.500", "12.500 RO", "R.O. 12.500"])
def test_fx_latin_omani_token_is_a_stated_limit(monkeypatch, price_str):
    """PIN OF A LIMIT (fix round) — ``RO`` / ``R.O.`` resolve nowhere:
    ``GCC_CURRENCY_SYMBOLS`` (must-NOT-touch) excludes "RO" by a documented
    ruling, and the proof corpus carries 0 price-adjacent "RO"/"R.O." against
    86 "OMR" (92 Gulf pages). So on an OMR ask these still parse 12,500 with the
    flag ON, exactly as at HEAD; the Arabic ``ر.ع.`` form is fixed (control).
    This asserts TODAY'S outcome; it is not the desired value."""
    _flags(monkeypatch, truth="true")
    assert _run(price_str, ask="OMR", region="oman", link=OM_LINK) == (12500.0, "OMR", "local_bhd")
    assert _run("12.500 ر.ع.", ask="OMR", region="oman", link=OM_LINK) == (12.5, "OMR", "local_bhd")


def test_fx_bare_three_decimal_numeral_is_a_stated_limit(monkeypatch):
    """PIN OF A LIMIT (fix round) — a BARE ``12.500`` has an empty residue, so
    step 1 has nothing to resolve and it still parses 12,500 ``local_bhd`` on a
    BHD ask with the flag ON, exactly as at HEAD. Parsing bare strings under the
    ask currency is NOT a safe fix: ``parse_price_string('1,299', 'BHD',
    display_text=True)`` is 1.299 (measured), the mirror 1000x error. This
    asserts TODAY'S outcome; it is not the desired value."""
    _flags(monkeypatch, truth="true")
    assert _run("12.500") == (12500.0, "BHD", "local_bhd")
    assert _run("1,299") == (1299.0, "BHD", "local_bhd")


# ===========================================================================
# POLISH ROUND (SOUND re-adversary, four minors ruled closed before the commit)
# — each pin below reddens under the named mutation, run from a byte snapshot
# with a sha-verified restore.
# ===========================================================================
def _both_doors(price_str, *, link, ask="BHD", region="bahrain"):
    """(front-door tuple, stash [(value, source_method)]) for one item."""
    front = _run(price_str, ask=ask, region=region, link=link, source="Best Buy")
    cands = _seed(price_str, link=link, source="Best Buy", currency=ask, region=region)
    return front, [(c["value"], c["source_method"]) for c in cands]


LANG_PREFIXED_OTHER_COUNTRY = [
    "https://www.talabat.com/ar/uae/x",
    "https://www.talabat.com/ar/kuwait/x",
    "https://www.talabat.com/ar/iraq/x",
    "https://www.talabat.com/en/uae/x",
    "https://www.talabat.com/grocery/uae/x",
]


@pytest.mark.parametrize(
    "link", LANG_PREFIXED_OTHER_COUNTRY, ids=[u.split("://", 1)[1] for u in LANG_PREFIXED_OTHER_COUNTRY],
)
def test_pol1_other_country_token_behind_a_language_segment(monkeypatch, link):
    """Polish (1) — the other-country vocabulary applies to EVERY path segment
    (R2's principle is "anywhere"), not only the first: talabat is a
    bahrain-tier registry row with no ``locale_paths``, so before the polish
    these five shapes earned ``local_bhd`` through the registry rung.
    MUTATION P1: read only the first path segment again -> all five red."""
    _flags(monkeypatch, truth="true")
    reasons = []
    assert ps._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=reasons) is False
    assert reasons == ["other_country"]
    assert _both_doors("BHD 12.500", link=link) == ((12.5, "BHD", "converted_usd"), [(12.5, "converted_usd")])
    _flags(monkeypatch)
    assert _run("BHD 12.500", link=link, source="Best Buy") == (12.5, "BHD", "local_bhd")


LANG_PREFIXED_BAHRAIN_CONTROLS = [
    "https://www.talabat.com/ar/bahrain/x",   # language segment + Bahrain segment, no other-country token
    "https://www.talabat.com/en/bahrain/x",
]


@pytest.mark.parametrize(
    "link", LANG_PREFIXED_BAHRAIN_CONTROLS, ids=[u.split("://", 1)[1] for u in LANG_PREFIXED_BAHRAIN_CONTROLS],
)
def test_pol1_language_segment_alone_is_not_other_country(monkeypatch, link):
    """Over-rejection control for polish (1): a language segment names no
    country, so a talabat Bahrain path behind it keeps ``local_bhd`` (via the
    registry rung — talabat declares no ``locale_paths``)."""
    _flags(monkeypatch, truth="true")
    reasons = []
    assert ps._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=reasons) is True, reasons
    assert _both_doors("BHD 12.500", link=link) == ((12.5, "BHD", "local_bhd"), [(12.5, "local_bhd")])


PORT_OR_DOT_GLOBAL = [
    "https://bh.iherb.com:443/pr/x",
    "https://bh.iherb.com./pr/x",
    "https://www.amazon.com:443/bahrain/x",
]


@pytest.mark.parametrize("link", PORT_OR_DOT_GLOBAL, ids=["iherb-port", "iherb-trailing-dot", "amazon-port-bahrain-path"])
def test_pol2_port_or_trailing_dot_cannot_bypass_the_global_rung(monkeypatch, link):
    """Polish (2) — the registry lookups receive the parsed hostname (port
    removed, lower-cased, trailing dot stripped), not the raw netloc, so an
    explicit ``:443`` or a trailing dot no longer misses the global row and
    falls through to the bh. label / Bahrain path. ``source_router`` is
    untouched. MUTATION P2: pass the raw link to ``registry_tier`` again ->
    all three red."""
    _flags(monkeypatch, truth="true")
    reasons = []
    assert ps._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=reasons) is False
    assert reasons == ["global_tier"]
    assert _both_doors("BHD 12.500", link=link) == ((12.5, "BHD", "converted_usd"), [(12.5, "converted_usd")])


def test_pol2_trailing_dot_is_the_same_host(monkeypatch):
    """Consequence of polish (2), pinned so it is visible: ``bolo.bh.`` is the
    fully-qualified spelling of ``bolo.bh`` and now earns the same ``local_bhd``
    as test 10's ``bolo.bh`` row (before the polish it fell through to
    ``no_bh_evidence``)."""
    _flags(monkeypatch, truth="true")
    link = "https://bolo.bh./product/x"
    reasons = []
    assert ps._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=reasons) is True, reasons
    assert _both_doors("BHD 12.500", link=link) == ((12.5, "BHD", "local_bhd"), [(12.5, "local_bhd")])


GOOGLE_PRODUCT_LINK = "https://www.google.com/shopping/product/123"


@pytest.mark.parametrize(
    "ask,region,price_str,want_front,want_stash",
    [
        ("SAR", "saudi_arabia", "250 SR", (250.0, "SAR", "converted_usd"), [(250.0, "converted_usd")]),
        ("BHD", "bahrain", "BHD 12.500", (12.5, "BHD", "converted_usd"), [(12.5, "converted_usd")]),
    ],
    ids=["sar-ask", "bhd-ask"],
)
def test_pol3_google_product_page_is_a_listing_on_every_ask(monkeypatch, caplog, ask, region, price_str, want_front, want_stash):
    """Polish (3) — ``google.com/shopping/product/<id>`` is a shelf for no
    region, so ANY google.com host joins the region-agnostic pair with reason
    ``listing_url`` on EVERY ask. Before the polish a SAR ask kept a genuine,
    showable ``(250.0, 'SAR', 'local_bhd')`` here (and a BHD ask reached
    ``no_bh_evidence``). ``_is_listing_url`` is untouched (W4-2 follow-up 03c).
    MUTATION P3: delete the google.com-host check -> both rows red."""
    _flags(monkeypatch, truth="true")
    _capture(caplog)
    reasons = []
    assert ps._shopping_bh_host_evidence(GOOGLE_PRODUCT_LINK, ask_currency=ask, reason_out=reasons) is False
    assert reasons == ["listing_url"]
    assert _both_doors(price_str, link=GOOGLE_PRODUCT_LINK, ask=ask, region=region) == (want_front, want_stash)
    lines = _truth_lines(caplog)
    assert sum("host=google.com reason=listing_url for " + NAME in ln for ln in lines) == 2, lines
    _flags(monkeypatch)
    assert _run(price_str, ask=ask, region=region, link=GOOGLE_PRODUCT_LINK, source="Best Buy")[2] == "local_bhd"


LOCALE_ROW_OUTSIDE_ITS_LOCALE = [
    "https://www.sephora.me/en-us/p/x",        # a locale outside both vocabularies
    "https://www.nasserpharmacy.com/bh-enx/p",  # a prefix of /bh-en that is NOT under it
    "https://www.boutiqaat.com/brands/x",      # a plain catalogue path
]


@pytest.mark.parametrize(
    "link", LOCALE_ROW_OUTSIDE_ITS_LOCALE, ids=[u.split("://", 1)[1] for u in LOCALE_ROW_OUTSIDE_ITS_LOCALE],
)
def test_pol4_locale_declaring_row_outside_its_locale_is_no_bh_evidence(monkeypatch, link):
    """Polish (4), the REJECT half of the registry rung: a bahrain-tier row
    that declares ``locale_paths`` earns nothing for a path outside them —
    ``no_bh_evidence`` on both doors. (The accept half was dead by
    construction and is gone; see the invariant pin below.)
    MUTATION P4: return True for any bahrain row again (drop the reject) ->
    all three red (plus the three locale rows of the multi-country test)."""
    _flags(monkeypatch, truth="true")
    reasons = []
    assert ps._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=reasons) is False
    assert reasons == ["no_bh_evidence"]
    assert _both_doors("BHD 12.500", link=link) == ((12.5, "BHD", "converted_usd"), [(12.5, "converted_usd")])


@pytest.mark.parametrize("catalog", ["", "true"], ids=["catalog-off", "catalog-on"])
def test_pol4_every_declared_bahrain_locale_starts_with_a_bh_path_segment(monkeypatch, catalog):
    """Invariant that makes polish (4) safe: every ``locale_paths`` entry on a
    bahrain-tier row, in BOTH registry states (literal rows only, and with the
    liveness-gated catalog loaded), has a first segment in
    ``_BH_HOST_PATH_SEGMENTS`` — so a path under a declared locale is always
    accepted by the BH path-segment rung before the registry rung is reached.
    If a future row declares a locale outside that vocabulary this reddens:
    add the segment to the vocabulary (with a measured URL) or accept that the
    row's locale resolves toward no evidence."""
    from app.services import source_router

    if catalog:
        monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", catalog)
    else:
        monkeypatch.delenv("ENABLE_BH_GCC_CATALOG_SOURCES", raising=False)
    rows = list(source_router._LITERAL_ROWS) + list(source_router._load_catalog_rows())
    declared = [
        (s.domain, lp) for s in rows if getattr(s, "tier", None) == "bahrain"
        for lp in (getattr(s, "locale_paths", ()) or ())
    ]
    assert declared, "no bahrain row declares locale_paths — the reject pin above would be vacuous"
    outside = [
        (dom, lp) for dom, lp in declared
        if ([seg for seg in lp.lower().split("/") if seg] or [""])[0] not in ps._BH_HOST_PATH_SEGMENTS
    ]
    assert outside == [], outside
