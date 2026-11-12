"""G-INC-1 gate rows (fix round 1, rulings F1-3): two rows that pin what the adversary's
two surviving mutants showed unpinned.

GR1 (INC-X10, mutant A10-beautywide): the listing-match guard is FRAGRANCE-scoped. With
ENABLE_LISTING_MATCH_GUARD on, the incident query and title under makeup, skincare and
haircare keep the flag-OFF verdict (accepted) at the selection gate and at the backstop.
Widening the H1 scope from "fragrances" to the whole beauty set flips them to rejected.

GR2 (INC-X2a, mutant A2-llmerr): the image tier line reports `error:<class name>` for an
LLM pick that raises, never `miss`.

Every row states its whole environment (the RED files' rule). Hermetic: pure functions over
synthetic titles, and the image tier callables patched on the module; no network, no Redis,
no LLM. Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

from app.services import image_service as img  # noqa: E402
from app.services import price_service as ps  # noqa: E402

FLAG = "ENABLE_LISTING_MATCH_GUARD"
INCIDENT_Q = "Versace Eros EDP"
INCIDENT_T = "Versace Eros for Women EDP 100ml"
LOGGER = "app.services.image_service"
TIER = re.compile(
    r"^\[IMG_TIER\] tier=(piggyback|search_payload|serper_budget|serper_images|llm_pick) "
    r"outcome=(hit|miss|skipped|error:[A-Za-z_][A-Za-z0-9_]*) ms=\d+$"
)
NAME = "Zq" + "xprobe " + "Nimbus" + "Noir " + "Parfum"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    monkeypatch.delenv("ENABLE_GENUINE_PRICE_PRIORITY", raising=False)
    monkeypatch.delenv("WARMER_CONTEXT", raising=False)
    monkeypatch.delenv("ENABLE_DATA_GUARDS_V2", raising=False)
    monkeypatch.delenv(FLAG, raising=False)
    yield


def _flag(mp, value):
    if value is None:
        mp.delenv(FLAG, raising=False)
    else:
        mp.setenv(FLAG, value)


@pytest.mark.parametrize("category", ["makeup", "skincare", "haircare"])
def test_gr1_guard_is_fragrance_scoped_not_beauty_wide(monkeypatch, category):
    """GR1: outside fragrances (the other three beauty categories) the flag changes nothing."""
    _flag(monkeypatch, None)
    sel_off = ps._selection_match(INCIDENT_Q, INCIDENT_T, category, candidate_brand="Versace")
    back_off = ps.backstop_identity_verdict(INCIDENT_Q, INCIDENT_T, category)
    _flag(monkeypatch, "true")
    sel_on = ps._selection_match(INCIDENT_Q, INCIDENT_T, category, candidate_brand="Versace")
    back_on = ps.backstop_identity_verdict(INCIDENT_Q, INCIDENT_T, category)
    assert sel_off is True, (category, sel_off)
    assert sel_on is True, (category, sel_on)
    assert back_on == back_off, (category, back_on, back_off)
    # Control: the same pair under fragrances IS rejected with the flag on (the row is live).
    assert ps._selection_match(INCIDENT_Q, INCIDENT_T, "fragrances", candidate_brand="Versace") is False


def test_gr2_llm_pick_error_outcome_names_the_class(monkeypatch, caplog):
    """GR2: budget denied, the LLM pick raises RuntimeError: the llm_pick line says
    error:RuntimeError (not miss), and the call still returns None."""
    order = []

    def _budget(n):
        order.append("budget")
        return False

    async def _search(name, **kwargs):
        order.append("search")
        return {"images": []}

    async def _gpt(name, organic):
        order.append("gpt")
        raise RuntimeError("probe")

    monkeypatch.setattr(img, "try_consume_serper_image_credit", _budget)
    monkeypatch.setattr(img, "search_images", _search)
    monkeypatch.setattr(img, "extract_image_via_gpt", _gpt)
    caplog.set_level(logging.INFO, logger=LOGGER)
    organic = [{"title": "t", "link": "https://" + "shop.example.com/p/1", "snippet": "s"}]
    out = asyncio.run(img.get_product_image_url(
        NAME, region="bahrain", page_scrape_image=None, organic_results=organic,
        search_payload=None))
    assert out is None
    assert order == ["budget", "gpt"], order
    pairs = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if rec.name == LOGGER and msg.startswith("[IMG_TIER]"):
            m = TIER.match(msg)
            assert m, msg
            pairs.append((m.group(1), m.group(2)))
    llm = [p for p in pairs if p[0] == "llm_pick"]
    assert llm == [("llm_pick", "error:RuntimeError")], pairs
