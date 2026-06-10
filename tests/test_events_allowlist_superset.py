"""Regression: VALID_EVENT_TYPES must be a superset of FE-fired event types.

Bundle B B.1 (item 4 — dispatcher-requested). The mobile app fires analytics
events to POST /api/v1/events via api.ts `trackEvent` / `trackEvents`. The
endpoint validates `event_type` against feedback_routes.VALID_EVENT_TYPES and
422-rejects the WHOLE batch on any unknown type — and api.ts swallows that
error (fire-and-forget). The result: an event the FE fires but the backend
doesn't allow is silently dropped server-side, with nothing in logs.

This is exactly how share_sheet_opened / share_completed / demographics_* /
the compare_entry_* funnel / onboarding_* went dark before this fix
(comparison_wall_time was Sprint A's 88s instrumentation; the onboarding_*
events are the Qaren funnel contract).

This test statically greps the FE `src/` tree for the literal event_type
strings passed to trackEvent / trackEvents (and the fireEvent / fireAnalytics
wrappers that forward into trackEvents) and asserts every one is present in
VALID_EVENT_TYPES. Dynamic (variable) event_type args can't be resolved
statically and are out of scope — only literals are checked.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FE_SRC = REPO_ROOT / "SmartCompareApp" / "src"

# Patterns that carry a literal event_type into the /events pipeline:
#   trackEvent('x', ...)          — single-event helper (api.ts)
#   fireEvent('x', ...)           — OnboardingFlow wrapper -> trackEvents
#   fireAnalytics('x', step)      — OnboardingScreen wrapper -> trackEvents
#   { event_type: 'x', ... }      — batch item passed to trackEvents
_LITERAL_PATTERNS = (
    re.compile(r"\btrackEvent\(\s*['\"]([a-z_]+)['\"]"),
    re.compile(r"\bfireEvent\(\s*['\"]([a-z_]+)['\"]"),
    re.compile(r"\bfireAnalytics\(\s*['\"]([a-z_]+)['\"]"),
    re.compile(r"\bevent_type:\s*['\"]([a-z_]+)['\"]"),
)

# event_type literals that intentionally do NOT go to /events (documented
# exclusions). comparison_wall_time is a Sentry captureMessage event.
_NON_EVENTS_LITERALS = {"comparison_wall_time"}


def _collect_fe_event_types() -> dict[str, list[str]]:
    """Map event_type -> list of "file:line" where it is fired, scanning the
    FE src tree (production code only — __tests__ excluded)."""
    found: dict[str, list[str]] = {}
    for path in FE_SRC.rglob("*.ts*"):
        # Skip test files — only production call sites define the contract.
        if "__tests__" in path.parts or path.name.endswith(".test.tsx") or path.name.endswith(".test.ts"):
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pat in _LITERAL_PATTERNS:
                for m in pat.finditer(line):
                    et = m.group(1)
                    if et in _NON_EVENTS_LITERALS:
                        continue
                    found.setdefault(et, []).append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    return found


def test_fe_src_tree_exists():
    """Guard against a vacuous pass if the FE path moves."""
    assert FE_SRC.is_dir(), f"FE src not found at {FE_SRC}"


def test_some_fe_event_types_discovered():
    """The grep must actually find call sites — a regex that matches nothing
    would make the superset assertion vacuously true."""
    found = _collect_fe_event_types()
    assert len(found) >= 10, (
        f"expected to discover many FE event types, found {len(found)}: "
        f"{sorted(found)} — the grep patterns may have drifted from the code"
    )


def test_valid_event_types_is_superset_of_fe_calls():
    """Every literal event_type the FE fires into /events must be allowlisted."""
    from app.api.feedback_routes import VALID_EVENT_TYPES

    allow = set(VALID_EVENT_TYPES)
    found = _collect_fe_event_types()
    missing = {et: sites for et, sites in found.items() if et not in allow}
    assert not missing, (
        "VALID_EVENT_TYPES is missing FE-fired event types (these would be "
        "silently 422-dropped server-side):\n"
        + "\n".join(f"  {et}  fired at {sites}" for et, sites in sorted(missing.items()))
    )


def test_known_previously_dark_events_now_allowlisted():
    """Explicit pins for the events the dispatcher called out as having been
    dark — they must be present even if a future refactor removes their FE
    call site (regression intent)."""
    from app.api.feedback_routes import VALID_EVENT_TYPES

    allow = set(VALID_EVENT_TYPES)
    for et in (
        "share_sheet_opened",
        "share_completed",
        "demographics_submitted",
        "demographics_dismissed",
        "onboarding_started",
        "onboarding_step_completed",
        "onboarding_completed",
    ):
        assert et in allow, f"{et} must be allowlisted (was silently dropped before B.1)"


def test_comparison_wall_time_is_not_an_events_type():
    """comparison_wall_time is a Sentry event, not an /events write — it must
    NOT be in the allowlist (documents the exclusion so nobody 're-adds' it)."""
    from app.api.feedback_routes import VALID_EVENT_TYPES

    assert "comparison_wall_time" not in set(VALID_EVENT_TYPES)
