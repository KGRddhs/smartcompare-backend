"""F1.3 — Registry-first gate with legacy whitelist fallback.

The Tier 1.5 candidate gate (authorized + gcc tiers, inside
`_harvest_candidate_urls`) admits a link via, in order:

  1. REGISTRY     — `score_source(link, category) >= 1.5`
  2. LEGACY       — domain in `AUTHORIZED_LUXURY_RETAILERS` /
                    `OFFICIAL_BRAND_DOMAINS` (authorized) or
                    `GCC_LUXURY_RETAILERS` (gcc)

A counterfeit/unknown domain (score 0.5, absent from every legacy set) is
admitted by NEITHER path and is rejected — Dispatcher invariant #1.

These assertions are the explicit contract for the registry-first migration:
the registry is the new primary; the legacy sets remain only as fallback so
we can watch the registry win in `source_trace` before deleting them.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.structured_comparison_service import (
    _harvest_candidate_urls,
    AUTHORIZED_LUXURY_RETAILERS,
    OFFICIAL_BRAND_DOMAINS,
    GCC_LUXURY_RETAILERS,
)
from app.services.source_router import SOURCE_REGISTRY, score_source


def _organic(*links):
    return {"organic": [{"link": l} for l in links]}


_REGISTRY_DOMAINS = {s.domain for s in SOURCE_REGISTRY}


# ---------- Path 1: registry pass ----------

def test_registry_pass_route_recorded():
    """ounass.com (gcc fashion, registry weight 1.5) is admitted via the
    registry path with route='registry'."""
    harvested = _harvest_candidate_urls(
        {"authorized": _organic("https://www.ounass.com/p/123")},
        official_domain=None,
        category="fashion",
    )
    assert len(harvested) == 1
    link, domain, route, weight = harvested[0]
    assert route == "registry"
    assert weight >= 1.5
    # Sanity: the gate decision matches score_source.
    assert score_source(link, "fashion") >= 1.5


def test_registry_pass_gcc_noon_any_category():
    """noon.com is gcc-tier all-category (weight 1.5) → registry pass for
    electronics.

    Uses the BH-locale form `noon.com/bahrain-en/`. WS3/D8 (genuine-bh latency
    bundle) added a BH-locale discovery filter that DROPS noon's wrong-GCC
    locales (`/uae-en/`=AED, `/saudi-en/`=SAR, `/egypt-en/`=EGP) for a Bahrain
    query — see _BH_LOCALE_MARKERS @ source_router.py. The registry-pass path
    this test exercises is unchanged; only the fixture URL was realigned to the
    KEPT BH locale (the pre-D8 `/uae-en/` fixture is now correctly filtered).
    Merge-base f961e32 verified: this test passed pre-bundle; the WS3/D8 filter
    is the intended cause (not a regression in the gate itself).
    """
    harvested = _harvest_candidate_urls(
        {"gcc": _organic("https://www.noon.com/bahrain-en/laptop")},
        official_domain=None,
        category="electronics",
    )
    assert len(harvested) == 1
    assert harvested[0][2] == "registry"


# ---------- Path 2: legacy fallback ----------

def test_legacy_fallback_pass_authorized():
    """A domain in AUTHORIZED_LUXURY_RETAILERS but NOT in the registry is
    admitted via the legacy fallback path with route='legacy_fallback'."""
    legacy_only = next(
        (d for d in AUTHORIZED_LUXURY_RETAILERS if d not in _REGISTRY_DOMAINS), None
    )
    assert legacy_only, "test requires a legacy-only authorized retailer"
    # It must genuinely fail the registry gate (score < 1.5) to prove the
    # fallback path — not the registry path — admitted it.
    assert score_source(f"https://www.{legacy_only}/p/x", "fashion") < 1.5

    harvested = _harvest_candidate_urls(
        {"authorized": _organic(f"https://www.{legacy_only}/p/x")},
        official_domain=None,
        category="fashion",
    )
    assert len(harvested) == 1
    assert harvested[0][2] == "legacy_fallback"


def test_legacy_fallback_pass_gcc():
    """A GCC_LUXURY_RETAILERS-only domain is admitted on the gcc tier via
    the legacy fallback path."""
    legacy_only = next(
        (d for d in GCC_LUXURY_RETAILERS if d not in _REGISTRY_DOMAINS), None
    )
    if not legacy_only:
        pytest.skip("no gcc legacy-only domain to exercise the fallback")
    assert score_source(f"https://www.{legacy_only}/p/x", "fashion") < 1.5

    harvested = _harvest_candidate_urls(
        {"gcc": _organic(f"https://www.{legacy_only}/p/x")},
        official_domain=None,
        category="fashion",
    )
    assert len(harvested) == 1
    assert harvested[0][2] == "legacy_fallback"


# ---------- Neither path: counterfeit / unknown reject ----------

@pytest.mark.parametrize("bad_domain", ["dhgate.com", "aliexpress.com", "temu.com", "wish.com"])
def test_counterfeit_domain_rejected_both_gates(bad_domain):
    """Counterfeit domains score 0.5 AND are absent from every legacy set →
    rejected from both authorized and gcc harvest tiers."""
    # Contract precondition: they're not in any whitelist.
    assert bad_domain not in _REGISTRY_DOMAINS
    assert bad_domain not in AUTHORIZED_LUXURY_RETAILERS
    assert bad_domain not in OFFICIAL_BRAND_DOMAINS
    assert bad_domain not in GCC_LUXURY_RETAILERS

    harvested = _harvest_candidate_urls(
        {
            "authorized": _organic(f"https://www.{bad_domain}/fake"),
            "gcc": _organic(f"https://www.{bad_domain}/fake"),
        },
        official_domain=None,
        category="fashion",
    )
    assert harvested == []


def test_unknown_blog_domain_rejected():
    """A random unknown domain (score 0.5, no legacy membership) is rejected."""
    harvested = _harvest_candidate_urls(
        {"authorized": _organic("https://random-deals-blog.example/iphone")},
        official_domain=None,
        category="electronics",
    )
    assert harvested == []


# ---------- Registry-first precedence ----------

def test_registry_takes_precedence_over_legacy_label():
    """A domain in BOTH the registry (>=1.5) and a legacy set is recorded as
    route='registry' (registry-first), not legacy_fallback.

    ounass.com is the canonical overlap: gcc-tier fashion in SOURCE_REGISTRY
    (weight 1.5) AND a member of the legacy GCC_LUXURY_RETAILERS set.
    """
    # Find a registry domain that ALSO lives in a legacy set and scores >=1.5
    # for one of its own categories (so the registry path is genuinely taken).
    overlap_src = None
    overlap_cat = None
    for s in SOURCE_REGISTRY:
        if (
            s.domain in AUTHORIZED_LUXURY_RETAILERS
            or s.domain in OFFICIAL_BRAND_DOMAINS
            or s.domain in GCC_LUXURY_RETAILERS
        ):
            cat = s.categories[0] if s.categories else "fashion"
            if score_source(f"https://www.{s.domain}/p", cat) >= 1.5:
                overlap_src, overlap_cat = s, cat
                break

    assert overlap_src is not None, (
        "expected a registry/legacy overlap domain scoring >=1.5 (e.g. ounass.com)"
    )

    # Harvest via whichever tier the legacy membership corresponds to; the gate
    # logic is identical across authorized/gcc, so gcc exercises the ounass case.
    tier = "gcc" if overlap_src.domain in GCC_LUXURY_RETAILERS else "authorized"
    harvested = _harvest_candidate_urls(
        {tier: _organic(f"https://www.{overlap_src.domain}/p")},
        official_domain=None,
        category=overlap_cat,
    )
    assert len(harvested) == 1
    assert harvested[0][2] == "registry", (
        f"{overlap_src.domain} scores >=1.5 — registry path must win over "
        f"legacy_fallback"
    )
