"""INC-X10 LISTING-MATCH-GUARD (G-INC-1, the S92-FIX incident lane) RED rows.

Spec: .qa-s80/G-INC-1_UNIT_SPEC.md section "Unit INC-X10" (X10.5), as amended by the batch
rulings R-G1-8 (the four-line table: Versace Eros, Versace Dylan Blue and Creed Aventus
default to the men's side, Dolce & Gabbana Light Blue to the women's side; each line has an
opposite-side REJECT row, a same-side ACCEPT row and an inert gendered-query row) and
R-G1-9 (the backstop hook H2 stays).

Flag ENABLE_LISTING_MATCH_GUARD (default OFF, read per call as the FIRST statement of
`price_service._vd_gender_line_flip`). Every row sets ENABLE_EXACT_PRICE_GATE=true and
ENABLE_VARIANT_DESCRIPTOR_AXES=true (production: ON / ON) and deletes
ENABLE_GENUINE_PRICE_PRIORITY (production: OFF); the unit flag is set or deleted explicitly
in every row. RED rows fail at base on an AssertionError only; PIN rows are green at base.

Hermetic: pure functions over synthetic titles and a synthetic host; no network. The
incident title is the one quoted in the incident report. Pure ASCII, LF.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

from app.services import price_service as ps  # noqa: E402
from app.services import structured_comparison_service as scs  # noqa: E402

FLAG = "ENABLE_LISTING_MATCH_GUARD"
FRAG = "fragrances"
HOST = "https://" + "shop.example" + "/p/"
INCIDENT_Q = "Versace Eros EDP"
INCIDENT_T = "Versace Eros for Women EDP 100ml"

# (id, query, title, category, candidate_brand, required verdict under flag ON)
REJECT_ROWS = {
    "T1": (INCIDENT_Q, INCIDENT_T, FRAG, "Versace"),
    "T2": (INCIDENT_Q, "Versace Eros Pour Femme EDP 100ml", FRAG, "Versace"),
    "T12": ("Creed Aventus", "Creed Aventus for Her EDP 75ml", FRAG, "Creed"),
    "T13": ("Dolce & Gabbana Light Blue EDT", "Dolce & Gabbana Light Blue Pour Homme EDT 125ml", FRAG,
            "Dolce & Gabbana"),
    "T17": ("Versace Dylan Blue", "Versace Dylan Blue Pour Femme Eau de Parfum 100ml", FRAG, "Versace"),
}
KEEP_ROWS = {
    "T3": ("Bleu de Chanel", "Bleu de Chanel Pour Homme EDP 100ml", FRAG, "Chanel"),
    "T4": ("Dior Sauvage EDP", "Sauvage Eau de Parfum for Men 100ml", FRAG, "Dior"),
    "T5": ("Lancome La Vie Est Belle EDP", "La Vie Est Belle Eau de Parfum for Women 100ml", FRAG, "Lancome"),
    "T6": ("YSL Libre EDP", "Libre Eau de Parfum Women 90ml", FRAG, "YSL"),
    "T7": ("Creed Aventus", "Creed Aventus for Men 100ml", FRAG, "Creed"),
    "T8": ("Creed Aventus for Her", "Creed Aventus for Her Eau de Parfum 75ml", FRAG, "Creed"),
    "T9": (INCIDENT_Q, "Versace Eros Pour Homme EDP 100ml", FRAG, "Versace"),
    "T10": (INCIDENT_Q, "Versace Eros EDP 100ml", FRAG, "Versace"),
    "T11": (INCIDENT_Q, "Versace Eros EDP for Men and Women 100ml", FRAG, "Versace"),
    "T14": ("Dolce & Gabbana Light Blue EDT", "Dolce & Gabbana Light Blue Eau de Toilette for Women 100ml",
            FRAG, "Dolce & Gabbana"),
    "T15": ("Versace Eros Pour Femme EDP", "Versace Eros Pour Femme EDP 100ml for Women", FRAG, "Versace"),
    "T16": (INCIDENT_Q, INCIDENT_T, None, "Versace"),
    "T18": ("Dolce & Gabbana Light Blue EDT", "Dolce & Gabbana Light Blue EDT for Men and Women 100ml", FRAG,
            "Dolce & Gabbana"),
}
ALL_ROWS = dict(REJECT_ROWS, **KEEP_ROWS)
OFF_SPELLINGS = [None, "false", " FALSE ", "0", "garbage"]
OFF_IDS = ["unset", "false", "padFALSE", "zero", "garbage"]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    monkeypatch.delenv("ENABLE_GENUINE_PRICE_PRIORITY", raising=False)
    monkeypatch.delenv(FLAG, raising=False)
    yield


def _flag(mp, value):
    if value is None:
        mp.delenv(FLAG, raising=False)
    else:
        mp.setenv(FLAG, value)


def _sel(row):
    q, t, cat, brand = row
    return ps._selection_match(q, t, cat, candidate_brand=brand)


def _cand(n, title, amount):
    return {"amount": amount, "currency": "BHD", "title": title, "url": HOST + str(n),
            "retailer": "Shop Example", "in_stock": True, "source_method": "page_scrape",
            "estimated": False, "brand": "Versace"}


def _incident_set():
    return [_cand(1, INCIDENT_T, 25.0), _cand(2, "Versace Eros EDP 100ml", 28.0),
            _cand(3, "Versace Eros Pour Homme EDP 100ml", 33.0)]


class _RecordingLines:
    """Stands in for ps._GENDER_FLIP_LINES and counts every iteration."""

    def __init__(self, real):
        self.real = tuple(real or ())
        self.iterations = 0

    def __iter__(self):
        for item in self.real:
            self.iterations += 1
            yield item
        self.iterations += 1  # an exhausted pass still counts as a read

    def __len__(self):
        return len(self.real)


def _install_recorder(mp):
    rec = _RecordingLines(getattr(ps, "_GENDER_FLIP_LINES", ()))
    mp.setattr(ps, "_GENDER_FLIP_LINES", rec, raising=False)
    return rec


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r10_1_eros_for_women_rejected(monkeypatch):
    """R10-1: T1 (the incident title) is rejected by the selection gate, flag ON."""
    _flag(monkeypatch, "true")
    assert _sel(REJECT_ROWS["T1"]) is False


def test_r10_2_eros_pour_femme_rejected(monkeypatch):
    _flag(monkeypatch, "true")
    assert _sel(REJECT_ROWS["T2"]) is False


def test_r10_3_aventus_for_her_pronoun_rejected(monkeypatch):
    _flag(monkeypatch, "true")
    assert _sel(REJECT_ROWS["T12"]) is False


def test_r10_4_light_blue_pour_homme_rejected(monkeypatch):
    _flag(monkeypatch, "true")
    assert _sel(REJECT_ROWS["T13"]) is False


def test_r10_5_dylan_blue_pour_femme_rejected(monkeypatch):
    _flag(monkeypatch, "true")
    assert _sel(REJECT_ROWS["T17"]) is False


def test_r10_6_select_best_skips_the_womens_listing(monkeypatch):
    """R10-6: three in-stock candidates on ONE host (authority ties): the 28.0 unmarked
    listing wins, not the cheaper 25.0 women's listing."""
    _flag(monkeypatch, "true")
    best = ps.select_best(_incident_set(), INCIDENT_Q, FRAG, drop_out_of_stock=False)
    assert best is not None and best["amount"] == 28.0, best


def test_r10_7_only_the_womens_listing_gives_no_price(monkeypatch):
    _flag(monkeypatch, "true")
    assert ps.select_best([_cand(1, INCIDENT_T, 25.0)], INCIDENT_Q, FRAG, drop_out_of_stock=False) is None


def test_r10_8_backstop_rejects_on_read_and_display(monkeypatch):
    _flag(monkeypatch, "true")
    assert ps.backstop_identity_verdict(INCIDENT_Q, INCIDENT_T, FRAG) == (False, "not_exact:gender")


def test_r10_9_poisoned_cache_entry_rejected(monkeypatch):
    _flag(monkeypatch, "true")
    entry = {"title": INCIDENT_T, "amount": 25.0, "currency": "BHD", "url": HOST + "1"}
    assert scs._cache_price_identity_ok(entry, "Versace", "Eros EDP", FRAG) is False


def test_r10_10_should_cache_refuses_the_womens_listing(monkeypatch):
    _flag(monkeypatch, "true")
    assert ps.should_cache_price(INCIDENT_Q, _cand(1, INCIDENT_T, 25.0), FRAG) is False


@pytest.mark.parametrize("raw, want", [
    ("true", True), (" TRUE ", True), ("1", True), ("yes", True), ("on", True),
    (None, False), ("", False), ("false", False), ("0", False), ("no", False), ("garbage", False),
], ids=["true", "padTRUE", "one", "yes", "on", "unset", "empty", "false", "zero", "no", "garbage"])
def test_p10_3_flag_reader_hygiene(monkeypatch, raw, want):
    """P10-3 (RED: the reader does not exist at base): listing_match_guard_enabled()."""
    reader = getattr(ps, "listing_match_guard_enabled", None)
    assert callable(reader), "price_service.listing_match_guard_enabled is missing (INC-X10)"
    _flag(monkeypatch, raw)
    assert reader() is want


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rid", sorted(KEEP_ROWS))
def test_p10_1_keep_rows_accept_flag_on(monkeypatch, rid):
    """P10-1: every KEEP row stays accepted with the flag ON (the table must not over-reject)."""
    _flag(monkeypatch, "true")
    assert _sel(KEEP_ROWS[rid]) is True, rid


@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=OFF_IDS)
def test_p10_2_flag_off_identity_full_config(monkeypatch, value):
    """P10-2: flag OFF over five spellings with the FULL configuration and a recording table:
    every truth-table row keeps its base verdict (True), select_best returns the 25.0
    listing, the backstop and the cache read accept T1, and the table is never read."""
    _flag(monkeypatch, value)
    rec = _install_recorder(monkeypatch)
    for rid, row in sorted(ALL_ROWS.items()):
        assert _sel(row) is True, rid
    best = ps.select_best(_incident_set(), INCIDENT_Q, FRAG, drop_out_of_stock=False)
    assert best is not None and best["amount"] == 25.0, best
    assert ps.backstop_identity_verdict(INCIDENT_Q, INCIDENT_T, FRAG) == (True, None)
    entry = {"title": INCIDENT_T, "amount": 25.0, "currency": "BHD", "url": HOST + "1"}
    assert scs._cache_price_identity_ok(entry, "Versace", "Eros EDP", FRAG) is True
    assert ps.should_cache_price(INCIDENT_Q, _cand(1, INCIDENT_T, 25.0), FRAG) is True
    assert rec.iterations == 0, rec.iterations


@pytest.mark.parametrize("category", [None, "fashion"], ids=["none", "fashion"])
def test_p10_4_rule_is_fragrance_scoped(monkeypatch, category):
    """P10-4: outside fragrances the flag changes nothing (T1 query + title)."""
    row = (INCIDENT_Q, INCIDENT_T, category, "Versace")
    _flag(monkeypatch, None)
    off = _sel(row)
    _flag(monkeypatch, "true")
    on = _sel(row)
    assert off is True, off
    assert on == off, (on, off)


def test_p10_5_gendered_query_never_consults_the_table(monkeypatch):
    """P10-5: flag ON, a gendered query (T8, T15) is accepted and the table is never read."""
    _flag(monkeypatch, "true")
    rec = _install_recorder(monkeypatch)
    assert _sel(KEEP_ROWS["T8"]) is True
    assert _sel(KEEP_ROWS["T15"]) is True
    assert rec.iterations == 0, rec.iterations


def test_p10_6_no_new_key_on_the_winner(monkeypatch):
    """P10-6: flag ON, the winner is one of the input objects with its own key set."""
    _flag(monkeypatch, "true")
    cands = _incident_set()
    keys = [set(c) for c in cands]
    best = ps.select_best(cands, INCIDENT_Q, FRAG, drop_out_of_stock=False)
    assert best is not None
    idx = [i for i, c in enumerate(cands) if c is best]
    assert len(idx) == 1, "the winner is not one of the input candidate objects"
    assert set(best) == keys[idx[0]]
