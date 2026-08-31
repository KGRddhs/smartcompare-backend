"""M13-12 — LONGEST-domain-wins registry host resolution (ENABLE_LONGEST_HOST_MATCH).

Every ``for s in SOURCE_REGISTRY`` suffix scan was first-match-wins, so an apex
row (swissarabian.com, USD) shadowed its own country subdomains
(ksa.swissarabian.com SAR, om.swissarabian.com OMR). ONE shared resolver
(``_registry_row_for_host``) fixes all of them, longest-match behind a default-OFF
flag; flag OFF = first-match-wins (byte-identical).

Two kinds of pin:
  * SYNTHETIC unit tests of the resolver's flag ON/OFF semantics (deterministic,
    registry passed in).
  * SELF-CONSISTENCY sweeps over the REAL catalog registry: every registry row's
    currency lookup returns its own currency, and every descriptor row resolves
    to its own host — currently 2 of 319 / 2 of 95 fail (named below).
"""
from dataclasses import dataclass

import pytest

from app.services import source_router as sr
from app.services.search_descriptor_service import descriptor_for_host


@dataclass(frozen=True)
class _Row:
    domain: str
    tier: str = "gcc"
    currency: str = ""


# Apex FIRST, then the two country subdomains — exactly the file order that lets
# the apex shadow them under first-match-wins.
_SYNTH = [
    _Row("swissarabian.com", "gcc", "USD"),
    _Row("ksa.swissarabian.com", "gcc", "SAR"),
    _Row("om.swissarabian.com", "gcc", "OMR"),
]


def test_m13_12_flag_off_first_match_wins(monkeypatch):
    """Flag OFF: the apex shadows the subdomain (byte-identical legacy scan)."""
    monkeypatch.setenv("ENABLE_LONGEST_HOST_MATCH", "false")
    row = sr._registry_row_for_host("ksa.swissarabian.com", registry=_SYNTH)
    assert row is not None and row.domain == "swissarabian.com"


def test_m13_12_flag_on_longest_match_wins(monkeypatch):
    """Flag ON: the subdomain resolves to its OWN row."""
    monkeypatch.setenv("ENABLE_LONGEST_HOST_MATCH", "true")
    assert sr._registry_row_for_host("ksa.swissarabian.com", registry=_SYNTH).domain == "ksa.swissarabian.com"
    assert sr._registry_row_for_host("om.swissarabian.com", registry=_SYNTH).domain == "om.swissarabian.com"
    # The apex host still resolves to the apex (exact match).
    assert sr._registry_row_for_host("swissarabian.com", registry=_SYNTH).domain == "swissarabian.com"


def _full_registry(monkeypatch):
    """The literals + the catalog rows, assembled with the catalog flag ON so the
    swissarabian subdomains are present. _load_catalog_rows reads the flag per
    call, so no module reload is needed."""
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    return list(sr._LITERAL_ROWS) + sr._load_catalog_rows()


def _currency_mismatches(registry):
    wrong = []
    for s in registry:
        own = (getattr(s, "currency", "") or "").strip().upper()
        if not own:
            continue
        row = sr._registry_row_for_host(
            s.domain,
            where=lambda x: bool((getattr(x, "currency", "") or "").strip()),
            registry=registry,
        )
        got = (getattr(row, "currency", "") or "").strip().upper() if row else None
        if got != own:
            wrong.append((s.domain, own, got))
    return wrong


def test_m13_12_currency_self_consistency_on(monkeypatch):
    """Flag ON: EVERY registry row's currency lookup returns its own currency."""
    registry = _full_registry(monkeypatch)
    if not any(s.domain == "ksa.swissarabian.com" for s in registry):
        pytest.skip("catalog rows unavailable")
    monkeypatch.setenv("ENABLE_LONGEST_HOST_MATCH", "true")
    assert _currency_mismatches(registry) == []


def test_m13_12_currency_self_consistency_off_names_the_two(monkeypatch):
    """Flag OFF: exactly the two shadowed rows are wrong (ksa->USD, om->USD)."""
    registry = _full_registry(monkeypatch)
    if not any(s.domain == "ksa.swissarabian.com" for s in registry):
        pytest.skip("catalog rows unavailable")
    monkeypatch.setenv("ENABLE_LONGEST_HOST_MATCH", "false")
    wrong = {d: (own, got) for d, own, got in _currency_mismatches(registry)}
    assert wrong.get("ksa.swissarabian.com") == ("SAR", "USD")
    assert wrong.get("om.swissarabian.com") == ("OMR", "USD")


def test_m13_12_descriptor_self_consistency_on(monkeypatch):
    """Flag ON: every {q} descriptor row resolves to its OWN descriptor."""
    registry = _full_registry(monkeypatch)
    if not any(getattr(s, "search_descriptor", None) is not None for s in registry):
        pytest.skip("no descriptors folded onto the registry")
    monkeypatch.setenv("ENABLE_LONGEST_HOST_MATCH", "true")
    # descriptor_for_host reads the real SOURCE_REGISTRY; rebuild it so the
    # catalog rows are present for this lookup path too.
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", registry, raising=True)
    wrong = []
    for s in registry:
        d = getattr(s, "search_descriptor", None)
        if d is None:
            continue
        if descriptor_for_host(s.domain) is not d:
            wrong.append(s.domain)
    assert wrong == []
