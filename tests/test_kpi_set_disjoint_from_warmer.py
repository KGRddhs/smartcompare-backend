"""Wave D — the usable_exact_genuine KPI truth set must be NON-CIRCULAR.

Phase 2 warms data/warmer_catalog.json; if the KPI truth set shared those products,
a --read-cache KPI run would measure the WARM, not correctness. This pins the
disjointness (gap #51) + the seed's shape.
"""
import io
import json

from app.services.price_service import normalize_words

_TRUTH = "data/usable_exact_genuine_truth.json"
_WARMER = "data/warmer_catalog.json"


def _load(path):
    return json.load(io.open(path, encoding="utf-8"))


def _warmer_products():
    """Each warmer query is a 'A vs B' PAIR — split into individual products."""
    out = []
    for e in _load(_WARMER)["queries"]:
        for part in (e.get("query") or "").split(" vs "):
            p = part.strip()
            if p:
                out.append(p)
    return out


def test_kpi_truth_products_disjoint_from_warmer():
    truth = _load(_TRUTH)["products"]
    warmer = [(p, normalize_words(p)) for p in _warmer_products()]
    overlaps = []
    for t in truth:
        t_tokens = normalize_words(t["query"])
        for wp, w_tokens in warmer:
            if not w_tokens:
                continue
            inter = t_tokens & w_tokens
            jacc = len(inter) / max(1, min(len(t_tokens), len(w_tokens)))
            if jacc >= 0.6:
                overlaps.append((t["id"], t["query"], wp))
    assert not overlaps, (
        "KPI truth products overlap warmer products (circular-test risk): " f"{overlaps}"
    )


def test_kpi_ids_disjoint_and_prefixed():
    truth_ids = {t["id"] for t in _load(_TRUTH)["products"]}
    warmer_ids = {e["id"] for e in _load(_WARMER)["queries"]}
    assert truth_ids.isdisjoint(warmer_ids)
    assert all(i.startswith("kpi-") for i in truth_ids), "KPI truth ids must use the kpi- prefix"


def test_kpi_truth_covers_three_target_categories():
    cats = {t["category"] for t in _load(_TRUTH)["products"]}
    for c in ("electronics", "fragrances", "fashion"):
        assert c in cats, f"KPI truth set missing target category {c}"


def test_kpi_truth_entries_have_expected_identity():
    for t in _load(_TRUTH)["products"]:
        assert t.get("query") and t.get("category") and isinstance(t.get("expected"), dict), (
            f"malformed KPI truth entry: {t.get('id')}"
        )
