"""W4-14 Part C -- the cross-language catalog fence (runs in the BACKEND CI job).

Once the client catalogs carry `results.dimension.<public_key>` for every backend
dimension, the CATALOG (not the backend label) is what renders for a known key. This
fence keeps the two sources equal: every public dimension key the backend can name
has a key in BOTH `SmartCompareApp/src/i18n/en.json` and `ar.json`, and the EN value
equals the backend's English label byte-for-byte. Precedent for a backend test that
reads the client tree: tests/test_events_allowlist_superset.py.

RED = fails at the unit base 3985eaac (the family has 0 keys); PIN = green there.
Pure file + in-process reads: no network, no env.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
I18N = REPO / "SmartCompareApp" / "src" / "i18n"

# The 45 public keys build_dimensions_v2 can emit at HEAD (9 categories, every dim
# scored) - spec 1a, W4_14_probes/probe_out/dims_reach.json `reach_keys`.
REACHABLE_45 = sorted([
    "actives", "availability", "build", "build_quality", "character", "craft", "dietary",
    "dosage", "durability", "ecosystem", "efficacy", "evidence", "feature", "feature_match",
    "finish", "fit", "form", "formulation", "function", "futureproof", "hair_match",
    "heritage", "ingredient", "ingredient_safety", "longevity", "nutrition", "performance",
    "presentation", "price", "projection", "reliability", "results", "review", "reviews",
    "safety", "scalp", "scent", "sensory", "shade", "skin_compat", "style", "taste",
    "trust", "value", "versatility",
])


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Zero-network guard: this fence reads two JSON files and calls pure scoring
    helpers; any resolution/connection or a curl_cffi GET fails the node."""
    import socket

    attempts = []

    def _gai(host, *a, **k):
        attempts.append(("getaddrinfo", host))
        raise OSError("W4-14 fence: network blocked")

    def _curl_get(*a, **k):
        attempts.append(("curl_cffi.requests.get", a[:1]))
        raise OSError("W4-14 fence: network blocked")

    monkeypatch.setattr(socket, "getaddrinfo", _gai)
    try:
        import curl_cffi.requests as _cr
        monkeypatch.setattr(_cr, "get", _curl_get)
    except Exception:  # pragma: no cover
        pass
    yield
    assert attempts == [], attempts


def _catalog(lang):
    return json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))


def _public_key(dim_key: str) -> str:
    return dim_key[:-6] if dim_key.endswith("_score") else dim_key


def _two_products():
    return [
        {"name": "A", "price": {"amount": 10.0, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.5, "review_count": 100},
        {"name": "B", "price": {"amount": 12.0, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.0, "review_count": 50},
    ]


def _backend_labels():
    """public key -> the English label the backend renders: `_DIMENSION_LABELS` for
    the category dimensions, and the `label` the three core builders ACTUALLY return
    (called, not literals) for price / reviews / value."""
    from app.services import scoring_service as ss

    labels = {}
    for keys in ss.CATEGORY_DIMENSIONS.values():
        for k in keys:
            pk = _public_key(k)
            labels[pk] = ss._DIMENSION_LABELS[k] if k in ss._DIMENSION_LABELS \
                else ss._DIMENSION_LABELS[pk]
    prods = _two_products()
    for builder in (ss._dim_price, ss._dim_reviews, ss._dim_value):
        d = builder(prods)
        labels[d["key"]] = d["label"]
    return labels


def test_24_pin_backend_vocabulary_is_51_public_keys():
    """PIN (green at HEAD). The backend vocabulary the fence keys on: 49 category
    dimension keys + price/reviews/value = 51 distinct public keys (value is shared)."""
    labels = _backend_labels()
    assert len(labels) == 51, len(labels)
    assert {"price", "reviews", "value"} <= set(labels)


def test_22_red_every_public_dimension_key_is_in_both_catalogs():
    """RED. Every public dimension key (CATEGORY_DIMENSIONS minus `_score`, plus
    price/reviews/value) has results.dimension.<key> in en.json AND ar.json. HEAD:
    0 of 51. Kills M17 (one backend dim label key deleted from ar.json only)."""
    labels = _backend_labels()
    en, ar = _catalog("en"), _catalog("ar")
    missing_en = sorted(k for k in labels if f"results.dimension.{k}" not in en)
    missing_ar = sorted(k for k in labels if f"results.dimension.{k}" not in ar)
    assert not missing_en and not missing_ar, (
        f"results.dimension.* missing: en {len(missing_en)}/51 {missing_en[:6]}..., "
        f"ar {len(missing_ar)}/51 {missing_ar[:6]}..."
    )


def test_23_red_en_catalog_value_equals_the_backend_label():
    """RED. en.json results.dimension.<key> equals the backend English label
    byte-for-byte (so every EN render is unchanged once the catalog renders it, and
    a renamed backend label cannot be silently shadowed). HEAD: the keys are absent."""
    labels = _backend_labels()
    en = _catalog("en")
    diffs = {k: (en.get(f"results.dimension.{k}"), v) for k, v in labels.items()
             if en.get(f"results.dimension.{k}") != v}
    assert not diffs, f"{len(diffs)} EN catalog labels differ from the backend: " \
                      f"{dict(list(sorted(diffs.items()))[:6])}"


def test_24b_pin_build_dimensions_v2_emits_exactly_the_45_recorded_keys():
    """PIN (green at HEAD). build_dimensions_v2 over the 9 categories with every dim
    scored emits exactly the 45 recorded public keys (cpw is cut by the contextual
    cap; the 5 value proxies are skipped). If a change makes one reachable, this list
    moves deliberately."""
    from app.services import scoring_service as ss

    reach = set()
    for cat, keys in ss.CATEGORY_DIMENSIONS.items():
        sr = {"scores": {"product_0": {"breakdown": {k: 80.0 for k in keys}, "missing_data": []},
                         "product_1": {"breakdown": {k: 60.0 for k in keys}, "missing_data": []}}}
        prods = [dict(p, category=cat) for p in _two_products()]
        for d in ss.build_dimensions_v2(prods, sr, cat):
            reach.add(d.get("key"))
    assert sorted(reach) == REACHABLE_45
