"""Regression: VALID_MATTERED_MOST must be a superset of the FE feedback chips.

W3-1 / MB-NETWORK-CONTRACT-01. The mobile app's FeedbackCard renders a row of
pill chips and sends the tapped chip's key to POST /api/v1/feedback as
`mattered_most: [chipKey]`. The route validates every item against
feedback_routes.VALID_MATTERED_MOST and 422-rejects the WHOLE request on any
unknown value — and FeedbackCard swallows that error (`catch {}`,
fire-and-forget), so the tap silently records nothing server-side.

Measured at eecd8bf9: the two sets have ZERO overlap. The client can send only
`accurate` / `detailed` / `fast`; the allowlist holds only `price`, `specs`,
`reviews`, `brand`, `value`, `warranty`, `ratings`. Every in-app feedback tap on
the current build has been dropped. The fix is on the SERVER side (widen the
allowlist), so it reaches users without an OTA.

This mirrors tests/test_events_allowlist_superset.py, with ONE deliberate
difference in what is grepped. The client sends `mattered_most: [chipKey]`
DYNAMICALLY, so grepping for `mattered_most: [` finds no literal values and
would pass vacuously. The literals that define the contract are the chip
definitions themselves — the `{ key: '<x>' }` entries in the chip array in
FeedbackCard.tsx — so those are what this test greps.

This is a BACKEND test that scans SmartCompareApp/: per the gate rule in
CLAUDE.md it belongs in the mobile comm set even when no client file changes
(`grep -rl "SmartCompareApp" tests/` must find it).
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
FEEDBACK_CARD = REPO_ROOT / "SmartCompareApp" / "src" / "components" / "FeedbackCard.tsx"

# The chip array entries, e.g. `{ key: 'accurate', i18nKey: '...' },`. These are
# the ONLY literal mattered_most values in the client tree — the send site
# (`mattered_most: [chipKey]`) is dynamic.
# One brace-bounded object literal per match, DOTALL so a prettier-wrapped
# multi-line chip and a reordered `{ i18nKey: ..., key: ... }` chip are BOTH
# seen (adversary finding: the earlier same-line/key-first regex missed both,
# so an unallowlisted chip in either shape shipped green).
_CHIP_KEY_PATTERN = re.compile(
    r"\{[^{}]*?\bkey:\s*['\"]([A-Za-z0-9_]+)['\"][^{}]*?\}", re.DOTALL
)

# The chips shipped on phones today (FeedbackCard.tsx:19-21). Pinned explicitly
# so the contract survives a refactor that renames or moves the array.
_SHIPPED_CHIP_KEYS = ("accurate", "detailed", "fast")


def _collect_chip_keys() -> dict[str, list[str]]:
    """Map chip key -> ["file:line"] for every literal chip definition."""
    found: dict[str, list[str]] = {}
    text = FEEDBACK_CARD.read_text(encoding="utf-8")
    for m in _CHIP_KEY_PATTERN.finditer(text):
        key = m.group(1)
        lineno = text.count("\n", 0, m.start(1)) + 1
        found.setdefault(key, []).append(
            f"{FEEDBACK_CARD.relative_to(REPO_ROOT)}:{lineno}"
        )
    return found


# ---- Static superset contract ----------------------------------------------

def test_feedback_card_exists():
    """Guard against a vacuous pass if the component moves or is renamed."""
    assert FEEDBACK_CARD.is_file(), f"FeedbackCard not found at {FEEDBACK_CARD}"


def test_chip_keys_are_the_values_sent_as_mattered_most():
    """Anchor the grep target: the chip key IS what lands in mattered_most.

    If this send site ever stops being `mattered_most: [chipKey]`, the chip
    literals are no longer the contract and this whole file must be re-aimed.
    """
    text = FEEDBACK_CARD.read_text(encoding="utf-8")
    assert "mattered_most: [chipKey]" in text, (
        "FeedbackCard no longer sends the chip key as mattered_most — the grep "
        "target of this test is stale"
    )


def test_some_chip_keys_discovered():
    """The grep must actually find chip definitions — a regex that matched
    nothing would make the superset assertion vacuously true."""
    found = _collect_chip_keys()
    assert len(found) >= 3, (
        f"expected to discover the FeedbackCard chips, found {len(found)}: "
        f"{sorted(found)} — the grep pattern may have drifted from the code"
    )


def test_valid_mattered_most_is_superset_of_feedback_chips():
    """Every chip the client can send must be allowlisted server-side."""
    from app.api.feedback_routes import VALID_MATTERED_MOST

    allow = set(VALID_MATTERED_MOST)
    found = _collect_chip_keys()
    missing = {k: sites for k, sites in found.items() if k not in allow}
    assert not missing, (
        "VALID_MATTERED_MOST is missing FeedbackCard chip keys (a tap on these "
        "422s and is silently dropped server-side):\n"
        + "\n".join(f"  {k}  defined at {sites}" for k, sites in sorted(missing.items()))
    )


@pytest.mark.parametrize("chip", _SHIPPED_CHIP_KEYS)
def test_shipped_chip_keys_are_allowlisted(chip):
    """Explicit pins for the three chips on phones today — they must stay
    allowlisted even if a future refactor removes their client definition
    (builds already in the field keep sending them)."""
    from app.api.feedback_routes import VALID_MATTERED_MOST

    assert chip in set(VALID_MATTERED_MOST), (
        f"{chip} must be allowlisted — the shipped client sends it and the "
        f"route 422s the whole submission otherwise"
    )


def test_existing_seven_values_are_not_removed():
    """This unit WIDENS the allowlist. Removing an accepted value is a breaking
    change for any historical client or other caller that still sends it."""
    from app.api.feedback_routes import VALID_MATTERED_MOST

    allow = set(VALID_MATTERED_MOST)
    for value in ("price", "specs", "reviews", "brand", "value", "warranty", "ratings"):
        assert value in allow, f"{value} was dropped from VALID_MATTERED_MOST"


# ---- Route-level contract ---------------------------------------------------

@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def test_route_accepts_a_shipped_chip_key(client):
    """POST /feedback with the client's own chip value must not 422.

    RED at eecd8bf9: 422 "Invalid mattered_most item: accurate."
    """
    with patch("app.services.feedback_service.get_supabase_client"):
        resp = client.post(
            "/api/v1/feedback",
            json={"useful": True, "mattered_most": ["accurate"]},
        )
    assert resp.status_code == 200, (
        f"expected the shipped chip to be accepted, got {resp.status_code}: "
        f"{resp.text}"
    )


def test_route_still_accepts_an_existing_allowlisted_value(client):
    """Pin: the seven pre-existing values keep working after the widening."""
    with patch("app.services.feedback_service.get_supabase_client"):
        resp = client.post(
            "/api/v1/feedback",
            json={"useful": True, "mattered_most": ["price"]},
        )
    assert resp.status_code == 200, resp.text


def test_route_still_rejects_an_unknown_value(client):
    """Pin: this widens the allowlist, it does NOT remove validation.

    The 422 fires in the pydantic validator before the handler runs, but the
    patch is still here so that under a validator mutation this test cannot
    reach a real Supabase client (adversary finding: without it, M3 produced a
    live `getaddrinfo` attempt from feedback_service).
    """
    with patch("app.services.feedback_service.get_supabase_client"):
        resp = client.post(
            "/api/v1/feedback",
            json={"useful": True, "mattered_most": ["bogus"]},
        )
    assert resp.status_code == 422, resp.text
