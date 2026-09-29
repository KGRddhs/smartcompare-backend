"""S69 U6 T6 (backend half) -- the register benefits copy mirrors the real free tier.

Spec: docs/investigations/2026-09-29-session-69-state/U6_SIGNIN_FIRST_RUN_SPEC.md R6(a),
with spec-review correction 24: the free tier is daily 3 / monthly 10 / lifetime_free 3
(``app/services/usage_service.py`` ``TIER_LIMITS``), so the client catalogs'
``register.benefits.*`` block must state BOTH the daily and the monthly number, in
English AND Arabic, and must never again promise the old "5 comparisons per day".

This is a BACKEND CI test that reads the client tree (precedent:
tests/test_events_allowlist_superset.py, tests/test_dimension_label_catalog_parity_w414.py),
so it belongs in the mobile gate set (``grep -rl SmartCompareApp tests/``).

Hermetic: ``TIER_LIMITS`` is read from the source with ``ast`` (no import of
``app.services.usage_service``, which would pull the Supabase / Redis clients), and the
catalogs are two JSON files. No network, no env.

RED at base e3f87b8b: both catalogs say 5 per day and name no monthly figure.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
USAGE_SERVICE = REPO / "app" / "services" / "usage_service.py"
I18N = REPO / "SmartCompareApp" / "src" / "i18n"

_ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _tier_limits() -> dict:
    """``TIER_LIMITS`` as a literal, read from the source (never imported)."""
    tree = ast.parse(USAGE_SERVICE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "TIER_LIMITS" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("TIER_LIMITS assignment not found in app/services/usage_service.py")


def _catalog(lang: str) -> dict:
    return json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))


def _integers(value: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", value.translate(_ARABIC_INDIC))]


FREE = _tier_limits()["free"]


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_register_benefits_daily_equals_tier_limits_free_daily(lang):
    # Guards the fence itself: if the tier changes, these assertions follow the
    # new numbers instead of silently pinning the old ones.
    assert isinstance(FREE["daily"], int) and FREE["daily"] > 0
    cat = _catalog(lang)
    value = cat.get("register.benefits.daily")
    assert isinstance(value, str), f"{lang}.json lacks register.benefits.daily"
    nums = _integers(value)
    assert FREE["daily"] in nums, (
        f"{lang} register.benefits.daily={value!r} does not state the free daily limit "
        f"{FREE['daily']} (TIER_LIMITS['free']['daily'])"
    )
    assert 5 not in nums or FREE["daily"] == 5, (
        f"{lang} register.benefits.daily={value!r} still promises 5 per day"
    )


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_register_benefits_state_the_monthly_limit(lang):
    cat = _catalog(lang)
    block = {k: v for k, v in cat.items() if k.startswith("register.benefits.")}
    nums = [n for v in block.values() for n in _integers(v)]
    assert FREE["monthly"] in nums, (
        f"{lang} register.benefits.* never states the free monthly limit "
        f"{FREE['monthly']} (TIER_LIMITS['free']['monthly']); '{FREE['daily']} per day' "
        "alone implies ~90 a month"
    )
