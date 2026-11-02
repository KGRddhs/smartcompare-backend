"""S81-G1 PRICE-PIPELINE: the GREEN-owned gate rows (GATE_S81_G1).

  test_g1_gc3_*   GC-3: a DB NULL ``challenge`` (None) counts as "no challenge
                  parked", so the channel-1 host rule ALLOWS the entry (the RED
                  rows pin an absent key and {} only).
  test_g1_gr1_*   a robots-record reader (the D14 seam) that raises yields no
                  channel-1 rating (fail-closed), never an exception.
  test_g1_gr2_*   an all-zero GTIN (a placeholder, never an allocated GTIN)
                  carries no ``gtin`` fact although its check digit is 0.

Hermetic: pure functions of ``app/services/jsonld_widen.py``; synthetic hosts
only; no network, no .env, no flag set outside a row's own monkeypatch.
"""
from __future__ import annotations

from datetime import datetime, timezone

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
