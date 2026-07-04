"""Wave B review MED (scripts/probe_truth_freshness.py _loose_match) —
SUCCESSOR-GENERATION guard on the freshness probe.

The probe's loose >=60% token overlap false-certified the exact staleness class
it exists to catch: a "Samsung Galaxy S26 5G 256GB" title shares enough
marketing tokens with the S25 entry (0.75 overlap, "s26" is not a flanker
tell) to read the retired SKU as FRESH — so the next S25->S26 / M3->M4 retail
transition would blame the RED KPI gate on matcher code again (the 2026-06-27
4/6-dead incident the script was added for).

Fix under pin: every DIGIT-BEARING query token (s25 / m3 / 128gb / 11) must
appear in the title BEFORE the 0.6 overlap test. Title-side digit ADDS (the
"(2025)" model-year) stay loose — only the QUERY's digits are hard.

Pure-function pins, no network (curl_cffi imports at module level but nothing
fires). Run: python -m pytest tests/test_probe_truth_freshness_match.py -q
"""
from scripts.probe_truth_freshness import _loose_match


# ------------------------------------------- successor generations REJECT ---

def test_s26_title_must_not_certify_s25_entry():
    # kpi-elec-002 query vs a successor-generation title: 3/4 token overlap
    # cleared the old 0.6 bar; the missing "s25" digit token must now reject.
    assert _loose_match(
        "Samsung Galaxy S25 256GB", "Samsung Galaxy S26 5G 256GB",
    ) is False


def test_m4_title_must_not_certify_m3_entry():
    # kpi-elec-004 query vs the M4 successor (chip generation flip)
    assert _loose_match(
        "Apple iPad Air 11-inch M3 128GB",
        "iPad Air 11-inch M4 Wi-Fi 128GB Space Grey",
    ) is False


# ---------------------------------------------------- live titles ACCEPT ---

def test_real_sharafdg_s25_title_accepts():
    # the live sharafdg title (recon 2026-07-02, 359.99 BHD in_stock=1):
    # digit tokens {s25, 256gb} both present; descriptive adds stay loose.
    assert _loose_match(
        "Samsung Galaxy S25 256GB",
        "Samsung Galaxy S25 5G 256GB 12GB RAM Icyblue AI Smartphone"
        " Middle East Version",
    ) is True


def test_ipad_2025_m3_title_accepts():
    # live sharafdg iPad title (240.99 BHD in_stock=1): the "(2025)" model-year
    # is a TITLE-side digit add — the guard requires QUERY digit tokens
    # ({11, m3, 128gb}, all present) in the title, never the reverse.
    assert _loose_match(
        "Apple iPad Air 11-inch M3 128GB",
        "iPad Air 11-inch M3 (2025) Wi-Fi 128GB - Space Grey"
        " Middle East Version with FaceTime",
    ) is True


# ------------------------------------- existing tell-guards stay in force ---

def test_accessory_and_flanker_tells_still_reject():
    # the digit guard is ADDITIVE — the two recon-proven tell-sets keep firing.
    assert _loose_match(
        "Nintendo Switch 2", "Nintendo Switch 2 Mario Kart World Bundle",
    ) is False
    assert _loose_match(
        "Samsung Galaxy S25 256GB", "Samsung Galaxy S25 Ultra 256GB",
    ) is False
