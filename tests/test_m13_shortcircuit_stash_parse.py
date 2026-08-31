"""M13-10 — the re-selection stash must parse a Serper price string the SAME way
the main path does.

The main path calls ``parse_price_string(price_str, detected_cur, display_text=
True)``; the short-circuit stash called ``parse_price_string(price_str)`` bare,
so 'BHD 12,500' was 12.5 on the main path and 12500.0 in the stash — a 1000x
divergence the fairness re-select (is_price_showable-gated, no upper-magnitude
guard) could then serve. Pure defect fix, unflagged: same string -> same amount.

Runs against ``_seed_shortcircuit_candidates`` and ``extract_price_from_shopping``
with ENABLE_EXACT_PRICE_GATE=false to isolate extraction (no network).
"""
from app.services import price_service as ps
from app.services.structured_comparison_service import get_comparison_service


def _stash_value(name, item, region="bahrain"):
    svc = get_comparison_service()
    svc._shopping_items_cache[name] = [item]
    svc._seed_shortcircuit_candidates(
        name, kind="tier1_shopping", currency="BHD", shopping_region=region,
    )
    cands = svc._price_candidates.get(name, [])
    return cands[0]["value"] if cands else None


def test_m13_10_stash_and_main_agree_on_bhd_12500(monkeypatch):
    """Pin: 'BHD 12,500' produces the SAME amount (12.5) in the stash and the
    main path — never the bare-parse 12500.0."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    name = "Acme Widget Deluxe"
    item = {
        "title": name, "price": "BHD 12,500",
        "source": "noon.com", "link": "https://noon.com/p",
    }
    main = ps.extract_price_from_shopping(name, [item], "BHD", shopping_region="bahrain")
    stash = _stash_value(name, item)
    assert main is not None and main["amount"] == 12.5, main
    assert stash == 12.5, stash
    assert stash == main["amount"]
    # Never the 1000x bare-parse divergence.
    assert stash != 12500.0


def test_m13_10_stash_honest_label_on_us_fallback(monkeypatch):
    """A gl=us fallback region makes even a bare price string converted_usd in
    the stash, matching the main path's honest-label rule."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    svc = get_comparison_service()
    name = "Acme Widget Deluxe"
    item = {
        "title": name, "price": "45.00",  # bare, no currency token
        "source": "amazon.com", "link": "https://amazon.com/p",
    }
    svc._shopping_items_cache[name] = [item]
    svc._seed_shortcircuit_candidates(
        name, kind="tier1_shopping", currency="BHD", shopping_region="us_fallback",
    )
    cands = svc._price_candidates.get(name, [])
    assert cands, "expected a seeded candidate"
    assert cands[0]["source_method"] == "converted_usd", cands[0]
