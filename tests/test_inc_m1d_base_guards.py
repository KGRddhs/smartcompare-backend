"""INC-M1d BASE MATCHER GUARDS (ENABLE_MATCH_BASE_GUARDS, default OFF, read per call): the RED file.

Three pre-existing wrong-accept defects of the BASE matcher path, in production today
(ENABLE_MATCH_FOLD off, ENABLE_LISTING_MATCH_GUARD ON on web); the unit spec INC_M1d_SPEC.md,
sections 0, 1 and 3 (relay ruling ORCH-M1D-A: D1, D2 and D3 in one unit, one new switch):
  D1  the brand-field alias strip. When the listing's brand field holds one member word of a
      house alias group (price_service._BRAND_ALIAS_GROUPS), _identity_tokens_ps strips that
      whole group from both identity cores, so another house that shares a word passes the
      identity test ("Christian Lacroix" for Dior, "Paris Corner" for Lancome, "Giorgio
      Beverly Hills" for Armani, "Yves Rocher" for Yves Saint Laurent).
  D2  the same-spelling gender twin, the pronoun half. A query holding a women's pronoun
      ("her", "ladies") is accepted against the gender-free title of the men's twin in the same
      house spelling (the base femme asymmetry reads the strict women words only).
  D3  the same-spelling concentration-phrase flanker. A base query is accepted against its
      Le Parfum / Eau Fraiche / Eau de Cologne flanker title, and the flanker query against the
      base title: every concentration phrase is stripped from identity and
      extract_concentration keeps the first label.

Row classes (the gate reads them by name):
  test_red_*       RED: the switch ON ("true"), the wanted REFUSAL. The base ignores the
                   switch and accepts, so each row fails at d062bad1 on an AssertionError only.
  test_pin_*       PIN: green at the base, and must stay green. P-D1 / P-D2 / P-D3: the right
                   pairs stay accepted with the switch ON. P-OFF: every RED pair keeps today's
                   verdict (accepted) with the switch unset, "false" and " Off ".
  test_limit_l1_*  the stated limit L-1 (xfail, strict): D2's men's direction (a men's query
                   against the women's gender-free title) stays accepted with the switch ON; it
                   needs INC-M1c's line-gender data.
Every RED and PIN row runs in both ENABLE_LISTING_MATCH_GUARD cells (unset and "true": it is
ON in production). An autouse fixture deletes every ENABLE_* name and WARMER_CONTEXT first, so
ENABLE_MATCH_FOLD is unset and the exact gate keeps its default (ENABLE_EXACT_PRICE_GATE unset).

Sources: the read-only measured sets of the INC-M1b re-verifiers, adapted here (never imported):
  probeset2 (the flag-mix re-verifier of INC-M1b FIX1): class brand_a3 for D1 and P-D1, class
  rtwin_hl for D2, its checks (checks.py, checks2.py: the end-to-end check below) and its saved
  verdicts base_p2.json (fold off, production mix, exact gate default; index i of its pairs);
  concflank (the round-3 correctness re-verifier, newsets.concflank with the strict re-label of
  concflank_relabel.py, saved sets_main.json): the Scandal and Le Male Le Parfum pairs;
  ef (the round-3 flag-mix re-verifier, efmod.py, saved base_ef.json): the Eau Fraiche and
  Eau de Cologne pairs; the Y Eau Fraiche control (efprobe.py, the round-3 flag-mix report);
  p03_twin_reverse.py (the round-2 correctness re-verifier): the L-1 pair. Pairs no saved set
  holds were measured at d062bad1 by the RED author's small probes (named "RED probe").

Hermetic: no network, no .env, no credential; only existing functions and env vars, so the file
collects at the base. Pure ASCII, LF. A hermetic count is not the production proof: merged, NOT
yet proven until the owner's phone shows it.
"""

from __future__ import annotations

import os

import pytest

from app.services import price_service as ps

SWITCH = "ENABLE_MATCH_BASE_GUARDS"
LMG = "ENABLE_LISTING_MATCH_GUARD"
FOLD = "ENABLE_MATCH_FOLD"
EXACT_GATE = "ENABLE_EXACT_PRICE_GATE"
SWITCH_ON = "true"
SWITCH_OFF_SPELLINGS = (None, "false", " Off ")
LMG_CELLS = (None, "true")
LMG_IDS = ("lmg_unset", "lmg_true")
CAT = "fragrances"
PDP = "https://shop.example.bh/products/item-1"
PARK_URL = "https://gcc-shop.example.ae/products/item-9"
MFK_Q = "Maison Francis Kurkdjian Baccarat Rouge 540 EDP"
# checks.py LINE_NAME / AMOUNT (the walk's per-line values) for the lines these rows use.
LINE_NAME = {
    "sauvage": "Sauvage", "libre": "Libre", "br540": "Baccarat Rouge 540", "aventus": "Aventus",
    "khamrah": "Khamrah", "hawas": "Hawas", "layton": "Layton", "lveb": "La Vie Est Belle",
    "adgp": "Acqua di Gio Profumo", "swy": "Stronger With You",
}
AMOUNT = {
    "sauvage": 55.0, "libre": 50.0, "br540": 120.0, "aventus": 140.0, "khamrah": 12.0,
    "hawas": 15.0, "layton": 80.0, "lveb": 50.0, "adgp": 45.0, "swy": 40.0,
}
# The end-to-end verdicts a D1 end-to-end row reads (see _e2e).
E2E_KEYS = ("end_to_end", "should_cache_price", "select_best", "park_conv")
CONSUMER_KEYS = ("should_cache_price", "select_best", "park_conv")


# ---------------------------------------------------------------- environment and seams


def _clear_memo():
    """The descriptor memo (price_service._extract_variant_descriptor_cached) is cleared at every
    environment change, so no verdict computed in another cell is reused."""
    memo = getattr(ps, "_extract_variant_descriptor_cached", None)
    clear = getattr(memo, "cache_clear", None)
    if callable(clear):
        clear()


def _env(monkeypatch, **flags):
    """Delete every ENABLE_* name and WARMER_CONTEXT, then set the given flags (None = unset)."""
    for name in list(os.environ):
        if name.startswith("ENABLE_") or name == "WARMER_CONTEXT":
            monkeypatch.delenv(name, raising=False)
    for name, value in flags.items():
        if value is not None:
            monkeypatch.setenv(name, value)
    _clear_memo()


@pytest.fixture(autouse=True)
def _every_enable_name_deleted(monkeypatch):
    """Every row starts with every ENABLE_* name and WARMER_CONTEXT deleted."""
    _env(monkeypatch)
    yield
    _clear_memo()


def _cell(monkeypatch, lmg, switch):
    """One cell: ENABLE_LISTING_MATCH_GUARD and the switch as given; ENABLE_MATCH_FOLD unset and
    the exact gate default (ENABLE_EXACT_PRICE_GATE unset); every other ENABLE_* deleted."""
    _env(monkeypatch, **{LMG: lmg, SWITCH: switch})
    assert os.environ.get(FOLD) is None and os.environ.get(EXACT_GATE) is None


def _cell_id(lmg, switch):
    return "%s=%r %s=%r" % (LMG, lmg, SWITCH, switch)


def _sel(query, title, brand=""):
    """_selection_match with the listing's brand passed as the candidate brand, as probeset2's
    checks2.vector does (brand "" is the walk's brand-less call)."""
    return bool(ps._selection_match(query, title, CAT, candidate_brand=brand))


def _price(line, title, brand=""):
    """checks2.price: the walk's local BHD price; the listing's brand rides price["brand"]."""
    price = {"amount": AMOUNT.get(line, 50.0), "currency": "BHD", "source_method": "local_bhd",
             "title": title, "url": PDP, "retailer": "shop.example.bh"}
    if brand:
        price["brand"] = brand
    return price


def _pair_size_ok(query, line, title, qsize, brand=""):
    """checks2.pair_size_ok: the real reconcile_pair_sizes with a partner product."""
    partner = "Creed Aventus EDP" if line != "aventus" else "Dior Sauvage EDP"
    sz = " %dml" % qsize if qsize else ""
    p0 = {"full_name": query, "name": LINE_NAME.get(line, line), "price": _price(line, title, brand)}
    p1 = {"full_name": partner + sz, "name": partner,
          "price": {"amount": 50.0, "currency": "BHD", "source_method": "local_bhd",
                    "title": partner + " " + (str(qsize) if qsize else "100") + "ml", "url": PDP}}
    ps.reconcile_pair_sizes([p0, p1], user_query=query + " vs " + partner + sz, candidates_by_name={})
    amount = p0["price"].get("amount")
    return isinstance(amount, (int, float)) and amount > 0


def _park_conv(query, title, brand=""):
    """checks2.park_conv: the converted terminal park, select_best over
    p2_filter_marketplace_rows of ONE converted row (the listing's brand rides row["brand"])."""
    row = {"amount": 30.0, "currency": "BHD", "source_method": "converted_usd", "title": title,
           "url": PARK_URL, "retailer": "gcc-shop.example.ae", "in_stock": True}
    if brand:
        row["brand"] = brand
    return ps.select_best(ps.p2_filter_marketplace_rows([row]), query, CAT) is not None


def _e2e(query, line, title, qsize, brand):
    """probeset2's end-to-end check (checks2.vector with a listing brand): end_to_end is the
    Shopping chain (shopping_listing_matches, _selection_match and _brand_evidence_ok, both with
    the listing's brand) and is_price_showable and reconcile_pair_sizes (both over the price
    dict that carries the brand); beside it the three consumers that read the brand from the
    price dict or the row: should_cache_price, select_best and the converted park."""
    listing = bool(ps.shopping_listing_matches(query, title))
    select = _sel(query, title, brand)
    chain = bool(listing and select and ps._brand_evidence_ok(
        query, title, candidate_brand=brand, category=CAT))
    showable = bool(ps.is_price_showable(query, _price(line, title, brand), CAT, enforce_correctness=True))
    pair = bool(_pair_size_ok(query, line, title, qsize, brand))
    return {
        "end_to_end": bool(chain and showable and pair),
        "should_cache_price": bool(ps.should_cache_price(query, _price(line, title, brand), CAT)),
        "select_best": ps.select_best([_price(line, title, brand)], query, CAT) is not None,
        "park_conv": _park_conv(query, title, brand),
    }


# ---------------------------------------------------------------- D1: the brand-field alias strip
# (rid, line, query, title, the listing's brand field, typed size, source): the 20 brand_a3 pairs
# with truth WRONG hold 16 that the base production mix accepts through _selection_match (base_p2
# fold0_pnl0_vda0_lmg0_dg20_fsr0_gpp0_exgdef, the lmg1 cell identical). The brand field names
# another house (a dupe or another house, never the query's).
D1_ROWS = (
    ("d1_s01_christian_lacroix_sauvage_100", "sauvage", "Dior Sauvage EDP 100ml", "Sauvage EDP 100ml", "Christian Lacroix", 100, "probeset2 brand_a3 i=435"),
    ("d1_s02_christian_siriano_sauvage_100", "sauvage", "Dior Sauvage EDP 100ml", "Sauvage EDP 100ml", "Christian Siriano", 100, "probeset2 brand_a3 i=436"),
    ("d1_s03_christian_louboutin_sauvage", "sauvage", "Dior Sauvage EDP", "Sauvage EDP 100ml", "Christian Louboutin", None, "probeset2 brand_a3 i=437"),
    ("d1_s04_christian_lacroix_christian_title", "sauvage", "Dior Sauvage EDP", "Christian Sauvage EDP 100ml", "Christian Lacroix", None, "probeset2 brand_a3 i=441"),
    ("d1_s05_paris_corner_la_vie_est_belle", "lveb", "Lancome La Vie Est Belle EDP", "La Vie Est Belle EDP 100ml", "Paris Corner", None, "probeset2 brand_a3 i=442"),
    ("d1_s06_paris_bleu_la_vie_est_belle", "lveb", "Lancome La Vie Est Belle EDP", "La Vie Est Belle EDP 100ml", "Paris Bleu", None, "probeset2 brand_a3 i=443"),
    ("d1_s07_paris_hilton_la_vie_est_belle", "lveb", "Lancome La Vie Est Belle EDP", "La Vie Est Belle EDP 100ml", "Paris Hilton", None, "probeset2 brand_a3 i=444"),
    ("d1_s08_fragrance_world_paris_la_vie_est_belle_100", "lveb", "Lancome La Vie Est Belle EDP 100ml", "La Vie Est Belle EDP 100ml", "Fragrance World Paris", 100, "probeset2 brand_a3 i=445"),
    ("d1_s09_paris_corner_paris_title", "lveb", "Lancome La Vie Est Belle EDP", "Paris La Vie Est Belle EDP 100ml", "Paris Corner", None, "probeset2 brand_a3 i=449"),
    ("d1_s10_giorgio_beverly_hills_acqua_di_gio_profumo", "adgp", "Giorgio Armani Acqua di Gio Profumo", "Acqua di Gio Profumo 75ml", "Giorgio Beverly Hills", None, "probeset2 brand_a3 i=450"),
    ("d1_s11_giorgio_valenti_acqua_di_gio_profumo", "adgp", "Giorgio Armani Acqua di Gio Profumo", "Acqua di Gio Profumo 75ml", "Giorgio Valenti", None, "probeset2 brand_a3 i=451"),
    ("d1_s12_giorgio_beverly_hills_stronger_with_you", "swy", "Emporio Armani Stronger With You EDT", "Stronger With You EDT 100ml", "Giorgio Beverly Hills", None, "probeset2 brand_a3 i=455"),
    ("d1_s13_christian_lacroix_christian_dior_title", "sauvage", "Dior Sauvage EDP", "Christian Dior Sauvage EDP 100ml", "Christian Lacroix", None, "probeset2 brand_a3 i=471"),
    ("d1_s14_yves_rocher_ysl_title", "libre", "Yves Saint Laurent Libre EDP", "YSL Libre EDP 90ml", "Yves Rocher", None, "probeset2 brand_a3 i=472"),
    ("d1_s15_yves_rocher_houseless_title", "libre", "Yves Saint Laurent Libre EDP", "Libre EDP 90ml", "Yves Rocher", None, "probeset2 brand_a3 i=473"),
    ("d1_s16_laurent_mazzone_saint_laurent_title", "libre", "YSL Libre EDP", "Saint Laurent Libre EDP 90ml", "Laurent Mazzone", None, "probeset2 brand_a3 i=474"),
)
# d1_s13 (i=471): the base also strips the brand field's own words ("christian") from the title,
# so its title core equals the query core without the alias-group strip; a RED probe with the
# groups emptied in memory still accepts it (reported to the gate), the other 15 are refused.
# The 11 of the 16 that the base takes end to end (checks2 end_to_end 11 of 20, both cells).
D1_E2E_SOURCES = frozenset("probeset2 brand_a3 i=%d" % i for i in (435, 436, 437, 441, 442, 443, 444, 445, 449, 455, 471))


def _e2e_id(n, rid):
    return "d1_e%02d_%s" % (n, rid.split("_", 2)[2])


D1_E2E_ROWS = tuple(
    (_e2e_id(n, r[0]),) + r[1:]
    for n, r in enumerate((r for r in D1_ROWS if r[6] in D1_E2E_SOURCES), start=1))


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D1_ROWS, ids=[r[0] for r in D1_ROWS])
def test_red_d1_brand_field_alias_strip(monkeypatch, row, lmg):
    """Spec id D1 (RED, _selection_match). Source: probeset2 class brand_a3, truth WRONG, the
    listing brand passed as the matcher's candidate brand (checks2.vector); saved verdicts
    base_p2.json. Wanted with the switch ON: refused (spec section 2, G1: the brand field holds
    none of the query house's alias forms whole). Expected at base d062bad1: accepted in both
    cells (the switch is ignored), so the row fails on an AssertionError."""
    rid, _line, query, title, brand, _qsize, src = row
    _cell(monkeypatch, lmg, SWITCH_ON)
    assert _sel(query, title, brand) is False, (
        "%s (%s) [%s]: %s | %s | brand %r accepted by _selection_match; wanted: refused" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title, brand))


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D1_E2E_ROWS, ids=[r[0] for r in D1_E2E_ROWS])
def test_red_d1_brand_field_alias_strip_end_to_end(monkeypatch, row, lmg):
    """Spec id D1 end to end (RED). Source: the 11 probeset2 brand_a3 pairs (truth WRONG) that
    the base takes end to end through probeset2's own check (checks2.vector: the Shopping chain,
    is_price_showable and reconcile_pair_sizes with the brand in the price dict), read with the
    three brand-reading consumers (should_cache_price, select_best, the converted park); saved
    verdicts base_p2.json (every check accepts, both cells). Wanted with the switch ON: every one
    of the four refuses. Expected at base d062bad1: all four accept, so the row fails on an
    AssertionError."""
    rid, line, query, title, brand, qsize, src = row
    _cell(monkeypatch, lmg, SWITCH_ON)
    got = _e2e(query, line, title, qsize, brand)
    assert got == dict.fromkeys(E2E_KEYS, False), (
        "%s (%s) [%s]: %s | %s | brand %r taken end to end %r; wanted: all refused" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title, brand, got))


# ---------------------------------------------------------------- D2: the women-pronoun twin
# (rid, query, title, source): the three same-spelling pairs base_p2 holds (all end to end).
D2_ROWS = (
    ("d2_01_aventus_her_edp_men_edp_title", "Creed Aventus Her EDP", "Creed Aventus EDP 100ml", "probeset2 rtwin_hl i=419"),
    ("d2_02_aventus_her_men_title", "Creed Aventus Her", "Creed Aventus 100ml", "probeset2 rtwin_hl i=416"),
    ("d2_03_hawas_her_edp_men_edp_title", "Rasasi Hawas Her EDP", "Rasasi Hawas EDP 100ml", "probeset2 rtwin_hl i=422"),
)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    "D2 moved whole to INC-M1c with L-1 and its line-gender data (ruling ORCH-M1D-B, 22 Nov): a "
    "pronoun-only guard lost 381 right pairs on the women-default lines; a stated limit here"))
@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D2_ROWS, ids=[r[0] for r in D2_ROWS])
def test_red_d2_women_pronoun_same_spelling_twin(monkeypatch, row, lmg):
    """Spec id D2 (RED, _selection_match). Source: probeset2 class rtwin_hl, the three
    same-spelling pairs with truth WRONG (a women's pronoun query, the men's gender-free title);
    saved verdicts base_p2.json. Wanted with the switch ON: refused (spec section 2, G2: the FX3-1
    PRONW rule on the base path, a women's pronoun query needs a women's word in the candidate).
    Expected at base d062bad1: accepted in both cells, so the row fails on an AssertionError."""
    rid, query, title, src = row
    _cell(monkeypatch, lmg, SWITCH_ON)
    assert _sel(query, title) is False, (
        "%s (%s) [%s]: %s | %s accepted by _selection_match; wanted: refused" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title))


# ---------------------------------------------------------------- D3: the concentration-phrase flanker
# (rid, query, title, source). concflank: the base accepts 90 WRONG pairs (strict re-label), 45 of
# Scandal and 45 of Le Male, in the same house spelling; samples of both lines, both directions.
D3_CONCFLANK_ROWS = (
    ("d3_c01_scandal_edp_le_parfum_edp_title", "Jean Paul Gaultier Scandal EDP", "Jean Paul Gaultier Scandal Le Parfum EDP 100ml", "concflank i=656"),
    ("d3_c02_scandal_edp_100_le_parfum_eau_de_parfum_title", "Jean Paul Gaultier Scandal EDP 100ml", "Jean Paul Gaultier Scandal Le Parfum Eau de Parfum 100ml", "concflank i=704"),
    ("d3_c03_scandal_noconc_edp_le_parfum_title", "Jean Paul Gaultier Scandal", "Jean Paul Gaultier Scandal EDP Le Parfum 100ml", "concflank i=738"),
    ("d3_c04_scandal_le_parfum_query_base_title", "Jean Paul Gaultier Scandal Le Parfum EDP", "Jean Paul Gaultier Scandal EDP 100ml", "concflank i=802"),
    ("d3_c05_le_male_edt_le_parfum_edt_title", "Jean Paul Gaultier Le Male EDT", "Jean Paul Gaultier Le Male Le Parfum EDT 100ml", "concflank i=1620"),
    ("d3_c06_le_male_edt_100_le_parfum_eau_de_toilette_title", "Jean Paul Gaultier Le Male EDT 100ml", "Jean Paul Gaultier Le Male Le Parfum Eau de Toilette 100ml", "concflank i=1668"),
    ("d3_c07_le_male_noconc_le_parfum_edp_title", "Jean Paul Gaultier Le Male", "Jean Paul Gaultier Le Male Le Parfum EDP 100ml", "concflank i=1696"),
    ("d3_c08_le_male_le_parfum_query_base_title", "Jean Paul Gaultier Le Male Le Parfum EDT", "Jean Paul Gaultier Le Male EDT 100ml", "concflank i=1764"),
)
# ef: the base accepts 34 WRONG pairs end to end, all in the same house spelling ("Dolce
# Gabbana" / "Dolce & Gabbana", "Viktor Rolf" / "Viktor & Rolf"): 32 Eau Fraiche and 2 Eau de
# Cologne controls (one of Spicebomb, one of Light Blue).
D3_EF_ROWS = (
    ("d3_f01_light_blue_edt_eau_fraiche_edt_title", "Dolce Gabbana Light Blue EDT", "Dolce & Gabbana Light Blue Eau Fraiche EDT 100ml", "ef i=401"),
    ("d3_f02_light_blue_noconc_eau_fraiche_only_title", "Dolce Gabbana Light Blue", "Dolce & Gabbana Light Blue Eau Fraiche 100ml", "ef i=412"),
    ("d3_f03_light_blue_edp_eau_fraiche_eau_de_parfum_title", "Dolce Gabbana Light Blue EDP", "Dolce & Gabbana Light Blue Eau Fraiche Eau de Parfum 100ml", "ef i=443"),
    ("d3_f04_spicebomb_edt_eau_fraiche_eau_de_toilette_title", "Viktor Rolf Spicebomb EDT", "Viktor & Rolf Spicebomb Eau Fraiche Eau de Toilette 100ml", "ef i=750"),
    ("d3_f05_spicebomb_edt_100_edt_eau_fraiche_title", "Viktor Rolf Spicebomb EDT 100ml", "Viktor & Rolf Spicebomb EDT Eau Fraiche 100ml", "ef i=774"),
)
D3_EDC_ROWS = (
    ("d3_k01_spicebomb_eau_de_cologne_title", "Viktor Rolf Spicebomb", "Viktor & Rolf Spicebomb Eau de Cologne 100ml", "ef i=766"),
    ("d3_k02_light_blue_eau_de_cologne_title", "Dolce Gabbana Light Blue", "Dolce & Gabbana Light Blue Eau de Cologne 100ml", "ef i=416"),
)
# The real control of the flag-mix re-verifier: accepted with the fold OFF (production and all four
# matcher flags ON alike); YSL Y Eau Fraiche is a real flanker sold as an Eau de Toilette.
D3_Y_CONTROL_ROWS = (
    ("d3_y01_y_edt_eau_fraiche_eau_de_toilette_title", "Yves Saint Laurent Y EDT", "Yves Saint Laurent Y Eau Fraiche Eau de Toilette 100ml", "efprobe control"),
)
D3_ROWS = D3_CONCFLANK_ROWS + D3_EF_ROWS + D3_EDC_ROWS + D3_Y_CONTROL_ROWS


def _red_d3(monkeypatch, row, lmg):
    rid, query, title, src = row
    _cell(monkeypatch, lmg, SWITCH_ON)
    assert _sel(query, title) is False, (
        "%s (%s) [%s]: %s | %s accepted by _selection_match; wanted: refused" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title))


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D3_CONCFLANK_ROWS, ids=[r[0] for r in D3_CONCFLANK_ROWS])
def test_red_d3_le_parfum_flanker(monkeypatch, row, lmg):
    """Spec id D3, the Scandal and Le Male Le Parfum samples (RED, _selection_match). Source: the
    concflank set (strict re-label, truth WRONG, saved sets_main.json sel|prod|OFF = 1). Wanted
    with the switch ON: refused (spec section 2, G3: the FX4-1 CONCPH rule on the base path,
    symmetric, a concentration-phrase flanker named on one side only). Expected at base
    d062bad1: accepted, so the row fails on an AssertionError."""
    _red_d3(monkeypatch, row, lmg)


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D3_EF_ROWS, ids=[r[0] for r in D3_EF_ROWS])
def test_red_d3_eau_fraiche_flanker(monkeypatch, row, lmg):
    """Spec id D3, the Eau Fraiche samples (RED, _selection_match). Source: the ef set (efmod.py
    class ef_syn, truth WRONG, saved base_ef.json: every check accepts, both cells). Wanted with the switch
    ON: refused (FX4-1 CONCPH (i) on the base path). Expected at base d062bad1: accepted, so the
    row fails on an AssertionError."""
    _red_d3(monkeypatch, row, lmg)


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D3_EDC_ROWS, ids=[r[0] for r in D3_EDC_ROWS])
def test_red_d3_eau_de_cologne_control(monkeypatch, row, lmg):
    """Spec id D3, the two Eau de Cologne controls (RED, _selection_match). Source: the ef set
    (efmod.py class ef_ctrl, truth WRONG, saved base_ef.json: every check accepts, both cells): it holds one
    accepted Spicebomb Eau de Cologne pair and one of Light Blue. Wanted with the switch ON:
    refused (FX4-1 CONCPH (iv) on the base path). Expected at base d062bad1: accepted, so the row
    fails on an AssertionError."""
    _red_d3(monkeypatch, row, lmg)


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D3_Y_CONTROL_ROWS, ids=[r[0] for r in D3_Y_CONTROL_ROWS])
def test_red_d3_y_eau_fraiche_control(monkeypatch, row, lmg):
    """Spec id D3, the YSL Y Eau Fraiche control (RED, _selection_match). Source: efprobe.py and
    the round-3 flag-mix report (the base accepts it with the fold OFF; RED probe at d062bad1:
    accepted in both cells). Wanted with the switch ON: refused. Expected at base d062bad1:
    accepted, so the row fails on an AssertionError."""
    _red_d3(monkeypatch, row, lmg)


# ---------------------------------------------------------------- P-D1: the same-house brands
# (rid, line, query, title, brand, typed size, what is read, source). Read: "all" = the four
# end-to-end verdicts of _e2e accept; "consumers" = should_cache_price, select_best and the park
# accept (reconcile_pair_sizes refuses the pair at the base for its 100ml size partner, so the
# composite end_to_end is not read); "sel" = _selection_match only. Three class pairs are refused
# at the base already (Francis Kurkdjian i=458: no MFK alias group, "maison" stays in the query
# core; Creed i=460 and Lattafa Perfumes i=463: the title states no concentration), so those pins
# keep the class brand and query with a title the base accepts.
PD1_ROWS = (
    ("pd1_christian_dior", "sauvage", "Dior Sauvage EDP 100ml", "Sauvage EDP 100ml", "Christian Dior", 100, "all", "probeset2 brand_a3 i=439"),
    ("pd1_dior_paris", "sauvage", "Dior Sauvage EDP 100ml", "Sauvage EDP 100ml", "Dior Paris", 100, "all", "probeset2 brand_a3 i=440"),
    ("pd1_lancome", "lveb", "Lancome La Vie Est Belle EDP", "La Vie Est Belle EDP 100ml", "Lancome", None, "all", "probeset2 brand_a3 i=447"),
    ("pd1_lancome_paris", "lveb", "Lancome La Vie Est Belle EDP", "La Vie Est Belle EDP 100ml", "Lancome Paris", None, "all", "probeset2 brand_a3 i=448"),
    ("pd1_giorgio_armani", "adgp", "Giorgio Armani Acqua di Gio Profumo", "Acqua di Gio Profumo 75ml", "Giorgio Armani", None, "consumers", "probeset2 brand_a3 i=453"),
    ("pd1_emporio_armani", "swy", "Emporio Armani Stronger With You EDT", "Stronger With You EDT 100ml", "Emporio Armani", None, "all", "probeset2 brand_a3 i=456"),
    ("pd1_francis_kurkdjian", "br540", MFK_Q, "Maison Francis Kurkdjian Baccarat Rouge 540 EDP 70ml", "Francis Kurkdjian", None, "consumers", "probeset2 brand_a3 i=458 adapted (house title), RED probe"),
    ("pd1_maison_francis_kurkdjian_paris", "br540", MFK_Q, "Baccarat Rouge 540 EDP 70ml", "Maison Francis Kurkdjian Paris", None, "consumers", "probeset2 brand_a3 i=459"),
    ("pd1_creed", "aventus", "Creed Aventus EDP", "Aventus EDP 100ml", "Creed", None, "all", "probeset2 brand_a3 i=460 adapted (EDP houseless title), RED probe"),
    ("pd1_lattafa_perfumes", "khamrah", "Lattafa Khamrah EDP", "Khamrah EDP 100ml", "Lattafa Perfumes", None, "all", "probeset2 brand_a3 i=463 adapted (EDP title), RED probe"),
    ("pd1_parfums_de_marly", "layton", "Parfums de Marly Layton EDP", "Layton EDP 125ml", "Parfums de Marly", None, "consumers", "probeset2 brand_a3 i=466"),
    # Two additions (RED author, for the gate): a same-house brand field whose title spells the
    # house with ANOTHER member of its alias group. The base accepts them only through the
    # alias-group strip (a RED probe with the groups emptied in memory refuses both), so they pin
    # that the strip stays for a brand field that names the query's house.
    ("pd1_dior_brand_christian_dior_title", "sauvage", "Dior Sauvage EDP", "Christian Dior Sauvage EDP 60ml", "Dior", None, "sel", "INC-M1b same_dior_christian_title, RED probe"),
    ("pd1_ysl_brand_yves_saint_laurent_query", "libre", "Yves Saint Laurent Libre EDP", "YSL Libre EDP 90ml", "YSL", None, "sel", "INC-M1b same_ysl_libre, RED probe"),
)


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", PD1_ROWS, ids=[r[0] for r in PD1_ROWS])
def test_pin_d1_same_house_brand(monkeypatch, row, lmg):
    """Spec id P-D1 (PIN). Source: probeset2 class brand_a3, truth RIGHT (the same-house brand
    fields of the class; three adapted, two added, see the table). Wanted with the switch ON:
    still accepted by _selection_match and by the end-to-end verdicts the row reads. Expected at
    base d062bad1: accepted (passes)."""
    rid, line, query, title, brand, qsize, read, src = row
    _cell(monkeypatch, lmg, SWITCH_ON)
    assert _sel(query, title, brand) is True, (
        "%s (%s) [%s]: %s | %s | brand %r refused by _selection_match; wanted: accepted" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title, brand))
    if read == "sel":
        return
    keys = E2E_KEYS if read == "all" else CONSUMER_KEYS
    got = _e2e(query, line, title, qsize, brand)
    assert {k: got[k] for k in keys} == dict.fromkeys(keys, True), (
        "%s (%s) [%s]: %s | %s | brand %r end to end %r; wanted: accepted" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title, brand, got))


# ---------------------------------------------------------------- P-D2: the right twins
# (rid, query, title, source). The women's pronoun query against a title holding a women's word;
# the men's query against the men's title. The rtwin_hl truth-RIGHT titles state no concentration
# (the base refuses them under an EDP query), so these pins add the EDP label (RED probe).
PD2_ROWS = (
    ("pd2_aventus_her_edp_for_her_edp_title", "Creed Aventus Her EDP", "Creed Aventus for Her EDP 75ml", "probeset2 rtwin_hl i=423 with EDP, RED probe"),
    ("pd2_aventus_her_for_her_title", "Creed Aventus Her", "Creed Aventus for Her 75ml", "probeset2 rtwin_hl i=423 without EDP, RED probe"),
    ("pd2_hawas_her_edp_for_her_edp_title", "Rasasi Hawas Her EDP", "Rasasi Hawas for Her EDP 100ml", "probeset2 rtwin_hl i=424 with EDP, RED probe"),
    ("pd2_aventus_ladies_edp_for_her_edp_title", "Creed Aventus Ladies EDP", "Creed Aventus for Her EDP 75ml", "RED probe"),
    ("pd2_aventus_her_edp_women_edp_title", "Creed Aventus Her EDP", "Creed Aventus Women EDP 75ml", "RED probe"),
    ("pd2_aventus_men_edp_base_edp_title", "Creed Aventus Men EDP", "Creed Aventus EDP 100ml", "probeset2 rtwin_hl i=428 with EDP, RED probe"),
    ("pd2_aventus_men_edp_for_men_edp_title", "Creed Aventus Men EDP", "Creed Aventus for Men EDP 100ml", "RED probe"),
    ("pd2_hawas_men_edp_base_edp_title", "Rasasi Hawas Men EDP", "Rasasi Hawas EDP 100ml", "probeset2 rtwin_hl i=429 with EDP, RED probe"),
    ("pd2_hawas_him_edp_base_edp_title", "Rasasi Hawas Him EDP", "Rasasi Hawas EDP 100ml", "probeset2 rtwin_hl i=426 with EDP, RED probe"),
    ("pd2_light_blue_pour_homme_both_sides", "Dolce Gabbana Light Blue Pour Homme EDT", "Dolce & Gabbana Light Blue Pour Homme EDT 125ml", "probeset2 rtwin i=387 in the same spelling, RED probe"),
)


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", PD2_ROWS, ids=[r[0] for r in PD2_ROWS])
def test_pin_d2_right_twin(monkeypatch, row, lmg):
    """Spec id P-D2 (PIN). Source: probeset2 classes rtwin_hl / rtwin (truth RIGHT) and the RED
    probes at d062bad1. Wanted with the switch ON: still accepted by _selection_match. Expected at
    base d062bad1: accepted (passes)."""
    rid, query, title, src = row
    _cell(monkeypatch, lmg, SWITCH_ON)
    assert _sel(query, title) is True, (
        "%s (%s) [%s]: %s | %s refused by _selection_match; wanted: accepted" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title))


# ---------------------------------------------------------------- P-D3: the right flanker pairs
# (rid, query, title, source): the flanker query against the flanker title (both sides name the
# same phrase), and the base query against the base title (neither side names one).
PD3_ROWS = (
    ("pd3_scandal_le_parfum_both_sides", "Jean Paul Gaultier Scandal Le Parfum EDP", "Jean Paul Gaultier Scandal Le Parfum EDP 100ml", "concflank i=816"),
    ("pd3_scandal_le_parfum_edp_eau_de_parfum_title", "Jean Paul Gaultier Scandal Le Parfum EDP", "Jean Paul Gaultier Scandal Le Parfum Eau de Parfum 100ml", "concflank i=824"),
    ("pd3_le_male_le_parfum_both_sides", "Jean Paul Gaultier Le Male Le Parfum", "Jean Paul Gaultier Le Male Le Parfum 100ml", "concflank i=1854"),
    ("pd3_y_eau_fraiche_both_sides", "Yves Saint Laurent Y Eau Fraiche EDT", "Yves Saint Laurent Y Eau Fraiche Eau de Toilette 100ml", "RED probe"),
    ("pd3_scandal_edp_base_title", "Jean Paul Gaultier Scandal EDP", "Jean Paul Gaultier Scandal EDP 100ml", "concflank i=642"),
    ("pd3_scandal_edp_eau_de_parfum_base_title", "Jean Paul Gaultier Scandal EDP", "Jean Paul Gaultier Scandal Eau de Parfum 100ml", "concflank i=646"),
    ("pd3_le_male_edt_base_title", "Jean Paul Gaultier Le Male EDT", "Jean Paul Gaultier Le Male EDT 100ml", "concflank i=1604"),
    ("pd3_y_edt_eau_de_toilette_base_title", "Yves Saint Laurent Y EDT", "Yves Saint Laurent Y Eau de Toilette 100ml", "RED probe"),
    ("pd3_spicebomb_edt_base_title", "Viktor Rolf Spicebomb EDT", "Viktor & Rolf Spicebomb EDT 100ml", "ef i=757"),
    ("pd3_light_blue_edt_base_title", "Dolce Gabbana Light Blue EDT", "Dolce & Gabbana Light Blue EDT 100ml", "ef i=407"),
)


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", PD3_ROWS, ids=[r[0] for r in PD3_ROWS])
def test_pin_d3_right_flanker_pair(monkeypatch, row, lmg):
    """Spec id P-D3 (PIN). Source: the concflank set (strict re-label: the same product on both
    sides), the ef set (ef_ctrl, truth RIGHT) and the RED probes at d062bad1. Wanted with the
    switch ON: still accepted by _selection_match. Expected at base d062bad1: accepted (passes)."""
    rid, query, title, src = row
    _cell(monkeypatch, lmg, SWITCH_ON)
    assert _sel(query, title) is True, (
        "%s (%s) [%s]: %s | %s refused by _selection_match; wanted: accepted" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title))


# ---------------------------------------------------------------- P-OFF: switch-OFF identity
# Every RED pair keeps today's verdict (accepted) with the switch unset, "false" and " Off ":
# with the switch OFF every verdict is byte-identical to main (spec section 2).


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D1_ROWS, ids=[r[0] for r in D1_ROWS])
def test_pin_off_d1_selection(monkeypatch, row, lmg):
    """Spec id P-OFF over D1 (PIN). Source: the D1 rows (probeset2 brand_a3, base_p2.json).
    Wanted with the switch unset, "false" and " Off ": accepted by _selection_match, as today.
    Expected at base d062bad1: accepted (passes)."""
    rid, _line, query, title, brand, _qsize, src = row
    for switch in SWITCH_OFF_SPELLINGS:
        _cell(monkeypatch, lmg, switch)
        assert _sel(query, title, brand) is True, (
            "%s (%s) [%s]: %s | %s | brand %r refused with the switch OFF; wanted: today's accept" % (
                rid, src, _cell_id(lmg, switch), query, title, brand))


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D1_E2E_ROWS, ids=[r[0] for r in D1_E2E_ROWS])
def test_pin_off_d1_end_to_end(monkeypatch, row, lmg):
    """Spec id P-OFF over D1 end to end (PIN). Source: the 11 D1 end-to-end rows (probeset2
    brand_a3, checks2.vector, base_p2.json). Wanted with the switch unset, "false" and " Off ":
    the four end-to-end verdicts accept, as today. Expected at base d062bad1: accepted (passes)."""
    rid, line, query, title, brand, qsize, src = row
    for switch in SWITCH_OFF_SPELLINGS:
        _cell(monkeypatch, lmg, switch)
        got = _e2e(query, line, title, qsize, brand)
        assert got == dict.fromkeys(E2E_KEYS, True), (
            "%s (%s) [%s]: %s | %s | brand %r end to end %r with the switch OFF; wanted: today's accept" % (
                rid, src, _cell_id(lmg, switch), query, title, brand, got))


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D2_ROWS, ids=[r[0] for r in D2_ROWS])
def test_pin_off_d2(monkeypatch, row, lmg):
    """Spec id P-OFF over D2 (PIN). Source: the D2 rows (probeset2 rtwin_hl, base_p2.json).
    Wanted with the switch unset, "false" and " Off ": accepted by _selection_match, as today.
    Expected at base d062bad1: accepted (passes)."""
    rid, query, title, src = row
    for switch in SWITCH_OFF_SPELLINGS:
        _cell(monkeypatch, lmg, switch)
        assert _sel(query, title) is True, (
            "%s (%s) [%s]: %s | %s refused with the switch OFF; wanted: today's accept" % (
                rid, src, _cell_id(lmg, switch), query, title))


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", D3_ROWS, ids=[r[0] for r in D3_ROWS])
def test_pin_off_d3(monkeypatch, row, lmg):
    """Spec id P-OFF over D3 (PIN). Source: the D3 rows (concflank sets_main.json, ef
    base_ef.json, the efprobe control). Wanted with the switch unset, "false" and " Off ":
    accepted by _selection_match, as today. Expected at base d062bad1: accepted (passes)."""
    rid, query, title, src = row
    for switch in SWITCH_OFF_SPELLINGS:
        _cell(monkeypatch, lmg, switch)
        assert _sel(query, title) is True, (
            "%s (%s) [%s]: %s | %s refused with the switch OFF; wanted: today's accept" % (
                rid, src, _cell_id(lmg, switch), query, title))


# ---------------------------------------------------------------- L-1: the stated limit
L1_QUERY = "Dolce Gabbana Light Blue Pour Homme EDT"
L1_TITLE = "Dolce & Gabbana Light Blue EDT 100ml"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    "L-1 stated limit (spec section 0, D2): the men's direction of the same-spelling twin needs "
    "INC-M1c's line-gender data; the switch does not refuse it"))
@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
def test_limit_l1_light_blue_mens_direction(monkeypatch, lmg):
    """Spec id L-1 (xfail, strict). Source: p03_twin_reverse.py of the round-2 correctness
    re-verifier (OFF True) and the RED probe at d062bad1 (accepted in both cells): a men's query
    against the women's Light Blue gender-free title in the same spelling. The row asserts the
    wanted refusal with the switch ON; INC-M1d leaves it accepted, so it xfails at the base and
    after GREEN, and turns strict-red (XPASS) once a later unit refuses it."""
    _cell(monkeypatch, lmg, SWITCH_ON)
    assert _sel(L1_QUERY, L1_TITLE) is False, (
        "L-1 [%s]: %s | %s accepted (the stated limit)" % (_cell_id(lmg, SWITCH_ON), L1_QUERY, L1_TITLE))


# ---------------------------------------------------------------- P-D1s / P-D1n: G1's two bounds
# Appended at GREEN, before G1 (the relay's GREEN word of 22 Nov 11:40): the two sides of
# spec section 2 / RED gate condition (b) G1 must never fire on. The 16th D1 pair (probeset2
# brand_a3 i=471) is RED already: d1_s13 and d1_e11.
#   P-D1s  a store-name brand field that shares no word with the query house, on a right
#          title (a G1 without the shared-word condition refuses it);
#   P-D1n  no brand field (empty, or null), on a right title.
# (rid, line, query, title, brand, typed size, what is read, source), read as in P-D1: "all" =
# the four end-to-end verdicts of _e2e accept; "consumers" = should_cache_price, select_best and
# the park accept (reconcile_pair_sizes refuses the 90 ml and 75 ml titles for their 100 ml
# partner at the base). Measured at the base d062bad1 by the GREEN author's small probe
# (accepted in both cells, the switch unset and "true" alike).
PD1S_ROWS = (
    ("pd1s_perfume_palace_dior_sauvage", "sauvage", "Dior Sauvage EDP 100ml", "Dior Sauvage EDP 100ml", "Perfume Palace", 100, "all", "GREEN probe"),
    ("pd1s_bahrain_fragrance_store_lancome", "lveb", "Lancome La Vie Est Belle EDP", "Lancome La Vie Est Belle EDP 100ml", "Bahrain Fragrance Store", None, "all", "GREEN probe"),
    ("pd1s_perfume_palace_ysl_libre", "libre", "Yves Saint Laurent Libre EDP", "Yves Saint Laurent Libre EDP 90ml", "Perfume Palace", None, "consumers", "GREEN probe"),
    ("pd1s_bahrain_fragrance_store_armani", "adgp", "Giorgio Armani Acqua di Gio Profumo", "Giorgio Armani Acqua di Gio Profumo 75ml", "Bahrain Fragrance Store", None, "consumers", "GREEN probe"),
    ("pd1s_perfume_palace_emporio_armani", "swy", "Emporio Armani Stronger With You EDT", "Emporio Armani Stronger With You EDT 100ml", "Perfume Palace", None, "all", "GREEN probe"),
)
PD1N_ROWS = (
    ("pd1n_dior_sauvage", "sauvage", "Dior Sauvage EDP 100ml", "Dior Sauvage EDP 100ml", "", 100, "all", "GREEN probe"),
    ("pd1n_lancome_la_vie_est_belle", "lveb", "Lancome La Vie Est Belle EDP", "Lancome La Vie Est Belle EDP 100ml", "", None, "all", "GREEN probe"),
    ("pd1n_ysl_libre", "libre", "Yves Saint Laurent Libre EDP", "Yves Saint Laurent Libre EDP 90ml", "", None, "consumers", "GREEN probe"),
    ("pd1n_armani_acqua_di_gio_profumo", "adgp", "Giorgio Armani Acqua di Gio Profumo", "Giorgio Armani Acqua di Gio Profumo 75ml", "", None, "consumers", "GREEN probe"),
    ("pd1n_emporio_armani", "swy", "Emporio Armani Stronger With You EDT", "Emporio Armani Stronger With You EDT 100ml", "", None, "all", "GREEN probe"),
    # a null brand field (a price dict holding brand None reaches the matcher as None)
    ("pd1n_null_brand_dior_sauvage", "sauvage", "Dior Sauvage EDP 100ml", "Dior Sauvage EDP 100ml", None, 100, "all", "GREEN probe"),
)


def _pin_accepted(monkeypatch, row, lmg):
    """The P-D1 read (test_pin_d1_same_house_brand) for the appended rows: _selection_match
    with the listing's brand, then the end-to-end verdicts the row reads, the switch ON."""
    rid, line, query, title, brand, qsize, read, src = row
    _cell(monkeypatch, lmg, SWITCH_ON)
    assert _sel(query, title, brand) is True, (
        "%s (%s) [%s]: %s | %s | brand %r refused by _selection_match; wanted: accepted" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title, brand))
    keys = E2E_KEYS if read == "all" else CONSUMER_KEYS
    got = _e2e(query, line, title, qsize, brand)
    assert {k: got[k] for k in keys} == dict.fromkeys(keys, True), (
        "%s (%s) [%s]: %s | %s | brand %r end to end %r; wanted: accepted" % (
            rid, src, _cell_id(lmg, SWITCH_ON), query, title, brand, got))


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", PD1S_ROWS, ids=[r[0] for r in PD1S_ROWS])
def test_pin_d1s_store_name_brand(monkeypatch, row, lmg):
    """Spec id P-D1s (PIN; the relay's GREEN word, 22 Nov 11:40). Source: the GREEN author's
    probe at d062bad1. A store-name brand field that shares no word with the query house
    ("Perfume Palace", "Bahrain Fragrance Store") on a right title of the D1 houses. Wanted
    with the switch ON: accepted by _selection_match and by the end-to-end verdicts the row
    reads (G1 never fires on a brand that shares no word with the house). Expected at base
    d062bad1: accepted (passes)."""
    _pin_accepted(monkeypatch, row, lmg)


@pytest.mark.parametrize("lmg", LMG_CELLS, ids=LMG_IDS)
@pytest.mark.parametrize("row", PD1N_ROWS, ids=[r[0] for r in PD1N_ROWS])
def test_pin_d1n_no_brand_field(monkeypatch, row, lmg):
    """Spec id P-D1n (PIN; the relay's GREEN word, 22 Nov 11:40). Source: the GREEN author's
    probe at d062bad1. No brand field, on a right title of the D1 houses. Wanted with the
    switch ON: accepted by _selection_match and by the end-to-end verdicts the row reads (G1
    never fires without a brand field). Expected at base d062bad1: accepted (passes)."""
    _pin_accepted(monkeypatch, row, lmg)
