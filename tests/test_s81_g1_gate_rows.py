"""S81-G1 PRICE-PIPELINE: the GREEN-owned gate rows (GATE_S81_G1).

  test_g1_gc3_*   GC-3: a DB NULL ``challenge`` (None) counts as "no challenge
                  parked", so the channel-1 host rule ALLOWS the entry (the RED
                  rows pin an absent key and {} only).
  test_g1_gr1_*   a robots-record reader (the D14 seam) that raises yields no
                  channel-1 rating (fail-closed), never an exception.
  test_g1_gr2_*   an all-zero GTIN (a placeholder, never an allocated GTIN)
                  carries no ``gtin`` fact although its check digit is 0.
  test_g1_am*     the rebase round's four rows (RULINGS_FIX1_S81_G1 F1-G1-4:
                  the adversary's surviving mutants A-M18 / A-M27 / A-M29 /
                  A-M30): the first-party '.' label boundary, the FIRST allowed
                  image, a rescaled rating below 1.0, and channel1_rating's own
                  1..5 range check (also through the real rating block).

Hermetic: pure functions of ``app/services/jsonld_widen.py`` and, for the
A-M30 slot row, the real ``StructuredComparisonService._fetch_product_data``
with every I/O leg mocked (the scs harness COPIED from
tests/test_s81_d08_jsonld_widen.py, never imported); synthetic hosts only; no
network, no .env, no flag set outside a row's own monkeypatch.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services import jsonld_widen

FIXED_NOW = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)
PAGE_URL = "https://store-a.example.com/products/oud-noir-100ml"


def _entry(**over):
    entry = {
        "status": "live",
        "deny": False,
        "robots": {
            "state": "allow",
            "status": 200,
            "body_sha": "synthetic-sha",
            "fetched_at": "2026-10-29T00:00:00Z",
            "next_reread": "2026-10-30T00:00:00Z",
            "crawl_delay": None,
            "origin": "https://store-a.example.com",
            "source": "datacenter",
            "rules": {"qarenbot": [["disallow", "/admin"]],
                      "star": [["disallow", "/cart"], ["allow", "/"]]},
            "probed": {"/": "allow"},
        },
        "challenge": {},
    }
    entry.update(over)
    return entry


def _price(url=PAGE_URL):
    return {"amount": 45.5, "currency": "BHD", "url": url,
            "_jsonld_facts": {"rating": {"value": 4.4, "count": 120}}}


def test_g1_gc3_challenge_null_is_allowed(monkeypatch):
    """GC-3: challenge None (a DB NULL) = no challenge parked = allowed, both in
    the pure rule and through channel1_rating with a seam answering that row."""
    assert jsonld_widen.rating_host_allowed(_entry(challenge=None), PAGE_URL, FIXED_NOW) is True
    calls = []

    def _seam(host):
        calls.append(host)
        return _entry(challenge=None)

    monkeypatch.setattr(jsonld_widen, "ROBOTS_ENTRY_LOOKUP", _seam)
    out = jsonld_widen.channel1_rating(_price(), FIXED_NOW)
    assert out == {"value": 4.4, "count": 120, "source": "store-a.example.com",
                   "url": PAGE_URL, "extract_method": "jsonld_aggregate_rating"}
    assert calls == ["store-a.example.com"]


def test_g1_gr1_seam_raise_fails_closed(monkeypatch):
    """A reader that raises is no entry: channel1_rating answers None."""
    def _boom(host):
        raise RuntimeError("synthetic reader failure")

    monkeypatch.setattr(jsonld_widen, "ROBOTS_ENTRY_LOOKUP", _boom)
    assert jsonld_widen.channel1_rating(_price(), FIXED_NOW) is None


@pytest.mark.parametrize("raw", ["0" * 8, "0" * 12, "0" * 13, "0000 0000 0000 00"],
                         ids=["zero8", "zero12", "zero13", "zero14-spaced"])
def test_g1_gr2_all_zero_gtin_refused(raw):
    """An all-zero GTIN passes the mod-10 check (0) but is a placeholder."""
    assert jsonld_widen.valid_gtin(raw) is None


_BACKSLASH = chr(92)


@pytest.mark.parametrize("url", [
    "https://store-a.example.com/img/a b.jpg",
    "https://store-a.example.com" + _BACKSLASH + "@evil-b.example.net/img/a.jpg",
    "https://store-a.example.com/img/a.jpg" + chr(9),
    "https://1.2.3/img/a.jpg",
], ids=["inner-space", "backslash-authority", "trailing-tab-stripped", "numeric-last-label"])
def test_g1_gr3_image_url_shape_refusals(url):
    """GREEN's extra image-policy refusals: whitespace / control characters or a
    backslash inside the URL (a WHATWG parser reads the backslash as a path
    separator, so the authority would differ), and an IP-like numeric host."""
    page = "https://store-a.example.com/p/x"
    if url.endswith(chr(9)):
        # a TRAILING tab is stripped like any outer whitespace and the URL passes
        assert jsonld_widen.allowed_image_url(url, page, ()) == url.strip()
    else:
        assert jsonld_widen.allowed_image_url(url, page, ()) is None


# ---------------------------------------------------------------------------
# F1-G1-4 (the rebase round): the adversary's four surviving mutants as rows
# ---------------------------------------------------------------------------
AM18_PAGE = "https://store-a.example.com/p/x"
AM18_SUFFIX_ONLY = "https://evilstore-a.example.com/img/a.jpg"
AM18_SUBDOMAIN = "https://img.store-a.example.com/img/a.jpg"
AM18_PAGE_HOST = "https://store-a.example.com/img/a.jpg"


def test_g1_am18_first_party_label_boundary():
    """A-M18 (F1-G1-4, the security-relevant gap): first-party = the page host
    or a subdomain of it at a '.' label boundary. A host that merely ENDS with
    the page host's text (evilstore-a.example.com for a page on
    store-a.example.com) is refused; no brand domain and no platform CDN apply.
    A subdomain of the page host and the page host itself are accepted."""
    assert jsonld_widen.allowed_image_url(AM18_SUFFIX_ONLY, AM18_PAGE, ()) is None
    assert jsonld_widen.allowed_image_url(AM18_SUBDOMAIN, AM18_PAGE, ()) == AM18_SUBDOMAIN
    assert jsonld_widen.allowed_image_url(AM18_PAGE_HOST, AM18_PAGE, ()) == AM18_PAGE_HOST


AM27_REFUSED = "http://store-a.example.com/img/lead-http.jpg"
AM27_FIRST = "https://store-a.example.com/img/first.jpg"
AM27_SECOND = "https://img.store-a.example.com/img/second.jpg"


def test_g1_am27_first_allowed_image_wins(monkeypatch):
    """A-M27: a Product node offering two policy-passing images stamps the
    FIRST allowed one as image_url; the leading refused (http) URL is skipped
    and the later allowed one never overwrites it."""
    monkeypatch.setenv("ENABLE_IMAGE_PIPELINE_V2", "true")
    monkeypatch.delenv("ENABLE_JSONLD_RATING", raising=False)
    # each candidate on its own: the lead is refused, the other two pass
    assert jsonld_widen.allowed_image_url(AM27_REFUSED, PAGE_URL, ()) is None
    assert jsonld_widen.allowed_image_url(AM27_FIRST, PAGE_URL, ()) == AM27_FIRST
    assert jsonld_widen.allowed_image_url(AM27_SECOND, PAGE_URL, ()) == AM27_SECOND
    result = {"amount": 45.5, "currency": "BHD"}
    node = {"image": [AM27_REFUSED, AM27_FIRST, AM27_SECOND]}
    out = jsonld_widen.stamp_jsonld_facts(result, node, PAGE_URL, ())
    assert out is result
    assert result == {"amount": 45.5, "currency": "BHD", "image_url": AM27_FIRST}


def test_g1_am29_rating_fact_lower_bound():
    """A-M29: rating_fact keeps a rescaled rating only inside 1.0..5.0:
    ratingValue 0.5 of bestRating 10 rescales to 0.25 (0.2 after the one-decimal
    round) and carries no fact; 2 of 10 rescales to exactly 1.0 and is kept."""
    assert jsonld_widen.rating_fact({"rating_value": 0.5, "best_rating": 10}) is None
    kept = jsonld_widen.rating_fact({"rating_value": 2, "best_rating": 10, "review_count": 7})
    assert kept == {"value": 1.0, "count": 7}


AM30_MALFORMED = (6.0, 0.0, "4.5")


def _am30_price(value, url=PAGE_URL):
    return {"amount": 45.5, "currency": "BHD", "url": url,
            "_jsonld_facts": {"rating": {"value": value, "count": 120}}}


# scs harness: COPIED from tests/test_s81_d08_jsonld_widen.py (_scs_fetch /
# _scs_product_info, itself copied from tests/test_s81_d03_deny_and_guards.py),
# never imported from it; with the same per-row flag hygiene as that file.
SCS_PRICE_URL = "https://store-a.example.com/products/iphone-15"
CASCADE_IMG = "https://cdn-a.example.com/cascade.jpg"
NO_PROVIDER = {"rating": None, "review_count": None, "rating_verified": False,
               "rating_source": None}
EXTRACT_PATH_FLAGS = (
    "ENABLE_JSONLD_FIRST", "ENABLE_JSONLD_SHAPE_LADDER", "ENABLE_NOT_A_PDP_FILTER",
    "ENABLE_PRICE_PARSE_OFFLOAD", "ENABLE_STRICT_CURRENCY_LABEL", "ENABLE_SALE_PRICE_FIRST",
    "ENABLE_OG_BRANCH_FIXES", "ENABLE_EXTRACTOR_FIXES_2608", "ENABLE_VISIBLE_TEXT_CURRENCY",
    "ENABLE_WALL_SIGNATURE_ANCHOR", "ENABLE_MONEY_PARSER_V2", "ENABLE_HOSTILE_NUMERIC_GUARD",
    "ENABLE_WIDE_SIGNAL_TEXT", "ENABLE_SHOWABLE_NAME_IDENTITY", "ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX",
    "ENABLE_FRAGRANCE_GLASS_EXEMPTION", "ENABLE_RSC_FLIGHT_PRICE", "ENABLE_NORMALIZE_WORDS_EMPTY_FIX",
    "ENABLE_DATA_GUARDS_V2", "ENABLE_MERCHANT_REGISTRY_DB", "ENABLE_LONGEST_HOST_MATCH",
)


def _scs_product_info():
    return {
        "brand": "Apple",
        "name": "iPhone 15",
        "variant": None,
        "category": "electronics",
        "search_query": "Apple iPhone 15",
    }


async def _scs_fetch(facts):
    from app.services.structured_comparison_service import get_comparison_service

    price = {"amount": 350, "currency": "BHD", "retailer": "Store A", "image_url": None,
             "url": SCS_PRICE_URL, "_jsonld_facts": json.loads(json.dumps(facts))}
    service = get_comparison_service()
    with (
        patch.object(service, "_get_specs", AsyncMock(return_value={"display": "6.1"})),
        patch.object(service, "_get_price", AsyncMock(return_value=price)),
        patch.object(service, "_get_reviews", AsyncMock(
            return_value={"review_summary": {}, "average_rating": 4.2})),
        patch.object(service, "_get_verified_rating", AsyncMock(
            return_value=dict(NO_PROVIDER))),
        patch("app.services.structured_comparison_service.search_web",
              AsyncMock(return_value={"organic": []})),
        patch("app.services.structured_comparison_service.get_product_image_url",
              AsyncMock(return_value=CASCADE_IMG)),
        patch("app.services.structured_comparison_service.tier2_fill_non_negotiables",
              AsyncMock(return_value={})),
        patch("app.services.structured_comparison_service.tier3_synthesize_non_negotiables",
              AsyncMock(return_value={})),
    ):
        return await service._fetch_product_data(
            _scs_product_info(),
            region="bahrain",
            include_specs=True,
            include_reviews=True,
            nocache=True,
        )


@pytest.mark.asyncio
async def test_g1_am30_channel1_range_check(monkeypatch):
    """A-M30: channel1_rating checks the stamped value itself (a real number
    inside 1..5) even where the host rule allows the page: 6.0, 0.0 and a
    string each give None (the in-range control proves the seam allows the
    page), and through the real rating block of _fetch_product_data (the rating
    flag ON, the allowing seam, the clock seam fixed, the facts stamped, no
    provider rating) each adds no jsonld_rating and leaves the EMPTY rating
    slot untouched (R14 of the RED file is the in-range twin)."""
    monkeypatch.delenv("ENABLE_IMAGE_PIPELINE_V2", raising=False)
    for name in EXTRACT_PATH_FLAGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "true")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_JSONLD_RATING", "true")
    monkeypatch.setattr(jsonld_widen, "ROBOTS_ENTRY_LOOKUP", lambda host: _entry())
    monkeypatch.setattr(jsonld_widen, "_now", lambda: FIXED_NOW)
    control = jsonld_widen.channel1_rating(_am30_price(4.4), FIXED_NOW)
    assert control is not None and control["value"] == 4.4
    for value in AM30_MALFORMED:
        assert jsonld_widen.channel1_rating(_am30_price(value), FIXED_NOW) is None, value
        result = await _scs_fetch({"rating": {"value": value, "count": 120}})
        assert "jsonld_rating" not in result, value
        assert result.get("rating") is None, value
        assert result.get("review_count") is None, value
        assert result.get("rating_verified") is False, value
        assert result.get("rating_source") is None, value
        assert "rating_derived" not in result, value
