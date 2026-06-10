"""Schema validation for data/validation_gold_truth.json (Bundle B F5.3).

Validates the full 200-query gold set against a pydantic model that mirrors
the verified per-entry schema, plus structural invariants:

- every entry validates against GoldQuery (types + ranges + price bands)
- all ids unique
- per-category counts match data/gold_truth_taxonomy_manifest.json
- every NEW entry (the 150 beyond the original 50) carries a provenance note
- original 50 keep max_wall_seconds == 25.0; new 150 use 30.0
- expected_winner_index is 0 or 1; price min <= max; currency == "BHD"

Pure data test — no network, no live services — runs in the free tier.

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md § Lane F5 (F5.3)
Taxonomy: docs/plans/2026-06-10-B-gold-200-taxonomy.md
"""

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from pydantic import BaseModel, ConfigDict, field_validator

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = REPO_ROOT / "data" / "validation_gold_truth.json"
MANIFEST_PATH = REPO_ROOT / "data" / "gold_truth_taxonomy_manifest.json"

ORIGINAL_COUNT = 50
TOTAL_EXPECTED = 200
ORIGINAL_WALL = 25.0
NEW_WALL = 30.0


# ---------------------------------------------------------------------------
# Pydantic model mirroring the verified gold-truth entry schema
# ---------------------------------------------------------------------------

class PriceBand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: float
    max: float
    currency: str
    note: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def _currency_is_bhd(cls, v: str) -> str:
        if v != "BHD":
            raise ValueError(f"currency must be 'BHD', got {v!r}")
        return v

    @field_validator("min", "max")
    @classmethod
    def _non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"price must be >= 0, got {v}")
        return v


class GoldQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    query: str
    category: str
    region: str
    expected_prices: Dict[str, PriceBand]
    expected_specs: Dict[str, Dict[str, str]]
    expected_winner_index: int
    expected_winner_rationale: str
    forbidden_facts: List[str]
    max_wall_seconds: float

    @field_validator("expected_winner_index")
    @classmethod
    def _winner_binary(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError(f"expected_winner_index must be 0 or 1, got {v}")
        return v

    @field_validator("expected_prices")
    @classmethod
    def _has_two_products(cls, v: Dict[str, PriceBand]) -> Dict[str, PriceBand]:
        for key in ("product_0", "product_1"):
            if key not in v:
                raise ValueError(f"expected_prices missing {key}")
        for key, band in v.items():
            if band.min > band.max:
                raise ValueError(f"{key} price min {band.min} > max {band.max}")
        return v

    @field_validator("expected_specs")
    @classmethod
    def _specs_two_products(cls, v: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        for key in ("product_0", "product_1"):
            if key not in v:
                raise ValueError(f"expected_specs missing {key}")
        return v


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def queries(gold) -> List[dict]:
    return gold["queries"]


# ---------------------------------------------------------------------------
# File-level structure
# ---------------------------------------------------------------------------

def test_gold_file_loads(gold):
    assert "queries" in gold
    assert "_metadata" in gold


def test_total_count_is_200(queries):
    assert len(queries) == TOTAL_EXPECTED


def test_metadata_count_matches_actual(gold, queries):
    assert gold["_metadata"]["queries"] == len(queries)


# ---------------------------------------------------------------------------
# Per-entry schema validation
# ---------------------------------------------------------------------------

def test_every_entry_validates(queries):
    errors = []
    for entry in queries:
        try:
            GoldQuery.model_validate(entry)
        except Exception as exc:  # noqa: BLE001 - aggregate report
            errors.append(f"{entry.get('id', '<no-id>')}: {exc}")
    assert not errors, "Schema validation failures:\n" + "\n".join(errors)


def test_all_ids_unique(queries):
    ids = [q["id"] for q in queries]
    dupes = [i for i, c in Counter(ids).items() if c > 1]
    assert not dupes, f"Duplicate ids: {dupes}"


def test_all_regions_bahrain(queries):
    bad = [q["id"] for q in queries if q["region"] != "bahrain"]
    assert not bad, f"Non-bahrain region entries: {bad}"


def test_every_winner_index_binary(queries):
    bad = [q["id"] for q in queries if q["expected_winner_index"] not in (0, 1)]
    assert not bad, f"Bad winner index: {bad}"


def test_forbidden_facts_present(queries):
    """Every entry should have at least one forbidden fact (the trap axis)."""
    bad = [q["id"] for q in queries if len(q.get("forbidden_facts", [])) < 1]
    assert not bad, f"Entries with no forbidden_facts: {bad}"


def test_new_entries_have_three_plus_forbidden_facts(queries):
    """Authoring rule: new entries (51+) carry 3+ forbidden facts."""
    new = queries[ORIGINAL_COUNT:]
    bad = [q["id"] for q in new if len(q.get("forbidden_facts", [])) < 3]
    assert not bad, f"New entries with <3 forbidden_facts: {bad}"


# ---------------------------------------------------------------------------
# Provenance + wall-time invariants (original vs new split)
# ---------------------------------------------------------------------------

def test_original_50_untouched_wall(queries):
    """The first 50 entries keep their 25.0s cap (frozen by F5)."""
    original = queries[:ORIGINAL_COUNT]
    bad = [q["id"] for q in original if q["max_wall_seconds"] != ORIGINAL_WALL]
    assert not bad, f"Original entries with wrong wall: {bad}"


def test_new_150_use_30s_wall(queries):
    new = queries[ORIGINAL_COUNT:]
    bad = [q["id"] for q in new if q["max_wall_seconds"] != NEW_WALL]
    assert not bad, f"New entries with wrong wall: {bad}"


def test_every_new_entry_has_provenance_note(queries):
    """F5.3 requirement: every entry id>=51 has a provenance note on at
    least one product price band."""
    new = queries[ORIGINAL_COUNT:]
    missing = [
        q["id"]
        for q in new
        if not any(band.get("note") for band in q["expected_prices"].values())
    ]
    assert not missing, f"New entries missing provenance note: {missing}"


# ---------------------------------------------------------------------------
# Per-category counts match the taxonomy manifest
# ---------------------------------------------------------------------------

def test_category_counts_match_manifest(queries, manifest):
    actual = Counter(q["category"] for q in queries)
    expected = manifest["category_totals"]
    mismatches = {
        cat: (actual.get(cat, 0), expected[cat])
        for cat in expected
        if actual.get(cat, 0) != expected[cat]
    }
    assert not mismatches, f"Category count mismatch (actual, expected): {mismatches}"


def test_no_unexpected_categories(queries, manifest):
    valid = set(manifest["valid_categories"])
    seen = {q["category"] for q in queries}
    extra = seen - valid
    assert not extra, f"Unexpected categories present: {extra}"


def test_manifest_totals_sum_to_200(manifest):
    assert sum(manifest["category_totals"].values()) == TOTAL_EXPECTED


# ---------------------------------------------------------------------------
# ID prefix consistency
# ---------------------------------------------------------------------------

def test_ids_use_manifest_prefixes(queries, manifest):
    prefixes = manifest["id_prefixes"]  # category -> prefix
    bad = []
    for q in queries:
        expected_prefix = prefixes.get(q["category"])
        if expected_prefix and not q["id"].startswith(expected_prefix + "-"):
            bad.append((q["id"], q["category"], expected_prefix))
    assert not bad, f"IDs with wrong prefix for category: {bad}"
