"""Phase 3.1 — orchestrator gate for `cohort_summary`.

`StructuredComparisonService._build_cohort_summary(demographics_profile)` decides
WHEN to emit the cohort proof line and sources its two fields:

- peer_count  = demographics_profile["cohort_match"]["n"]  (the REAL survey
  sample size N persisted at demographics-submission time — see
  auth_routes.save_demographics; NOT an invented number);
- governorate = demographics_profile["governorate"]        (the user's typed
  governorate from onboarding Step 04).

Gating mirrors extraction_service.was_cohort_block_active (ENABLE_COHORT_
PERSONALIZATION flag + match_quality in the inject set + a confidence + a
cohort_key) AND additionally requires peer_count > 0 and a non-sentinel
governorate so the FE CohortBadge never renders an empty/zero line.

Returns None (→ key omitted upstream) on any failure (fail-soft — a cohort line
must never break a comparison).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.structured_comparison_service import StructuredComparisonService

_build = StructuredComparisonService._build_cohort_summary


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch):
    """Cohort personalization is ON in prod; default the env on for these tests
    (the flag-gating itself is asserted in the dedicated flag test)."""
    monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "true")


def _demographics(*, n=19, governorate="Capital", quality="exact",
                  confidence="medium", cohort_key="25-34|Female|Capital|English"):
    return {
        "governorate": governorate,
        "country": "Bahrain",
        "language": "English",
        "cohort_match": {
            "cohort_key": cohort_key,
            "match_quality": quality,
            "confidence": confidence,
            "n": n,
            "persona_label": "Quality-first focused buyer",
        },
    }


# ---------- happy path ----------

def test_returns_peer_count_and_governorate_when_resolved():
    out = _build(_demographics(n=19, governorate="Capital"))
    assert out == {"peer_count": 19, "governorate": "Capital"}


def test_peer_count_sourced_from_cohort_match_n():
    """peer_count must be the cohort prior's real sample size `n`, verbatim."""
    out = _build(_demographics(n=27, governorate="Northern"))
    assert out["peer_count"] == 27


def test_broadened_governorate_quality_still_emits():
    """broadened_governorate is in the inject set → still a valid cohort line."""
    out = _build(_demographics(quality="broadened_governorate"))
    assert out is not None
    assert out["governorate"] == "Capital"


# ---------- graceful absence ----------

def test_none_demographics_returns_none():
    assert _build(None) is None
    assert _build({}) is None


def test_no_cohort_match_returns_none():
    demo = _demographics()
    demo.pop("cohort_match")
    assert _build(demo) is None


def test_zero_n_returns_none():
    """peer_count 0 → omit (CohortBadge hides on <= 0)."""
    assert _build(_demographics(n=0)) is None


def test_blank_governorate_returns_none():
    assert _build(_demographics(governorate="")) is None


def test_none_governorate_returns_none():
    assert _build(_demographics(governorate=None)) is None


def test_prefer_not_to_say_governorate_returns_none():
    """'Prefer not to say' is a skip-sentinel — no region line."""
    assert _build(_demographics(governorate="Prefer not to say")) is None


def test_population_quality_returns_none():
    """match_quality='population' is NOT in the inject set → no cohort line
    (mirrors was_cohort_block_active / _build_cohort_priors_block)."""
    assert _build(_demographics(quality="population")) is None


def test_broadened_age_quality_returns_none():
    """broadened_age (gender-only) is below the inject threshold → no line."""
    assert _build(_demographics(quality="broadened_age")) is None


def test_missing_cohort_key_returns_none():
    assert _build(_demographics(cohort_key="")) is None


def test_invalid_confidence_returns_none():
    assert _build(_demographics(confidence="garbage")) is None


# ---------- flag gating ----------

def test_flag_off_returns_none(monkeypatch):
    """When ENABLE_COHORT_PERSONALIZATION is off, no cohort match ran upstream,
    so no cohort line is emitted (mirror of was_cohort_block_active)."""
    monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "false")
    assert _build(_demographics()) is None


# ---------- fail-soft ----------

def test_non_int_n_does_not_crash():
    """Defensive: a malformed n that can't coerce → None, never an exception."""
    demo = _demographics()
    demo["cohort_match"]["n"] = "lots"
    assert _build(demo) is None


# ---------- wiring guard (sync + streaming + partial share the chokepoint) ----------

def test_all_three_build_sites_pass_cohort_summary():
    """All three build_comparison_response call sites (sync compare_from_text,
    streaming, and the hard-cap partial) must thread cohort_summary so the proof
    line reaches the FE on every response path. One static guard covers the
    shared chokepoint — the builder attachment + helper gate are unit-tested
    above; this pins that the orchestrator actually passes the kwarg through and
    nobody silently drops it in a future refactor."""
    import inspect

    from app.services import structured_comparison_service as svc

    source = inspect.getsource(svc)
    # sync + streaming both pass demographics_profile; partial reads it from ctx
    assert source.count(
        "cohort_summary=self._build_cohort_summary(demographics_profile)"
    ) == 2, "sync + streaming build sites must each pass cohort_summary"
    assert (
        "cohort_summary=self._build_cohort_summary(ctx.get(\"demographics_profile\"))"
        in source
    ), "partial build site must pass cohort_summary from ctx"
