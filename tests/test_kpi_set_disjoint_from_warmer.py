"""Wave D — the usable_exact_genuine KPI truth set must be NON-CIRCULAR for the
STRUCTURAL warmer catalog, AND fully COVERED by the intentional KPI seed.

Original intent (gap #51): Phase 2 warms data/warmer_catalog.json; if the KPI
truth set shared the STRUCTURAL warmer products, a --read-cache KPI run could
measure an incidental warm rather than correctness. That non-circularity is
still pinned for the structural section (ids warm-frag/hair/gadget/grocery-*).

Warmer-effectiveness update (2026-07-04): the --read-cache KPI is a WARMED-
correctness gate — it must read a cache the recurring cron actually warmed, so
the catalog now carries a deliberate KPI-SEED section (ids warm-kpi-*) that is
byte-identical to the 18 truth queries. This is NOT circular presence-measurement:
usable_exact_genuine_for_product independently re-validates the resolved SKU
against the truth entry (exact-SKU + per-axis), so a warmed WRONG-SKU is still
not counted. The KPI seed is therefore EXEMPT from the disjointness assertion,
and a coverage assertion pins that the seed covers all 18 truth queries.
"""
import io
import json

from app.services.price_service import normalize_words

_TRUTH = "data/usable_exact_genuine_truth.json"
_WARMER = "data/warmer_catalog.json"

# The intentional KPI seed (byte-identical to the truth queries) — exempt from the
# structural disjointness check; pinned instead by test_kpi_seed_covers_truth.
_KPI_SEED_PREFIX = "warm-kpi-"


def _load(path):
    return json.load(io.open(path, encoding="utf-8"))


def _structural_warmer_products():
    """The STRUCTURAL warmer products only (KPI-seed section excluded). Each
    structural query is an 'A vs B' PAIR — split into individual products."""
    out = []
    for e in _load(_WARMER)["queries"]:
        if str(e.get("id", "")).startswith(_KPI_SEED_PREFIX):
            continue  # intentional KPI seed — see test_kpi_seed_covers_truth
        for part in (e.get("query") or "").split(" vs "):
            p = part.strip()
            if p:
                out.append(p)
    return out


def test_kpi_truth_products_disjoint_from_structural_warmer():
    """The STRUCTURAL catalog must not incidentally overlap the KPI truth set."""
    truth = _load(_TRUTH)["products"]
    warmer = [(p, normalize_words(p)) for p in _structural_warmer_products()]
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
        "KPI truth products overlap STRUCTURAL warmer products (circular-test risk): "
        f"{overlaps}"
    )


def test_kpi_seed_covers_truth():
    """The KPI-seed section must warm EXACTLY the 18 truth queries (so the
    --read-cache WARMED gate reads a cache the cron actually warmed). Byte-match
    the query strings — the price cache key is size-aware."""
    truth_queries = {t["query"].strip() for t in _load(_TRUTH)["products"]}
    seed_queries = {
        (e.get("query") or "").strip()
        for e in _load(_WARMER)["queries"]
        if str(e.get("id", "")).startswith(_KPI_SEED_PREFIX)
    }
    missing = truth_queries - seed_queries
    assert not missing, f"KPI seed missing truth queries (warmed gate would cold-miss): {missing}"


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
