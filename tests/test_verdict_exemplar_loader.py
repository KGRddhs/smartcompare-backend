"""Tests for verdict_exemplar_loader (S2 I2.1).

Mirrors the test posture of test_pain_workflow_loader_edges.py: the loader
must degrade gracefully (return "" / empty) when the data file is missing,
malformed, or a category is absent — never raise into the verdict prompt
builder. The @lru_cache + reset_cache() pair is exercised so a test that
swaps the data file sees the swap.
"""

import json
from pathlib import Path

import pytest

from app.services import verdict_exemplar_loader as vel


@pytest.fixture(autouse=True)
def _reset_loader_cache():
    """Clear the loader lru_cache before every test (F2.5 lesson)."""
    vel.reset_cache()
    yield
    vel.reset_cache()


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

def test_missing_file_returns_empty_block(monkeypatch, tmp_path):
    """File absent → build_exemplar_block returns "" for any category."""
    monkeypatch.setattr(vel, "_EXEMPLAR_FILE", tmp_path / "does_not_exist.json")
    vel.reset_cache()
    assert vel.build_exemplar_block("electronics") == ""
    assert vel.build_exemplar_block("other") == ""


def test_malformed_json_returns_empty_block(monkeypatch, tmp_path):
    """Corrupt JSON → loader logs + returns "", never raises."""
    bad = tmp_path / "verdict_exemplars.json"
    bad.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(vel, "_EXEMPLAR_FILE", bad)
    vel.reset_cache()
    assert vel.build_exemplar_block("makeup") == ""


def test_unknown_category_returns_empty_block(monkeypatch, tmp_path):
    """A category not present in the file → "" (no KeyError)."""
    f = tmp_path / "verdict_exemplars.json"
    f.write_text(json.dumps({"electronics": {"exemplars": [], "anti_patterns": []}}),
                 encoding="utf-8")
    monkeypatch.setattr(vel, "_EXEMPLAR_FILE", f)
    vel.reset_cache()
    assert vel.build_exemplar_block("fragrances") == ""


def test_empty_arrays_return_empty_block(monkeypatch, tmp_path):
    """Category present but both arrays empty (the G2 skeleton state) → ""."""
    f = tmp_path / "verdict_exemplars.json"
    f.write_text(json.dumps({"makeup": {"exemplars": [], "anti_patterns": []}}),
                 encoding="utf-8")
    monkeypatch.setattr(vel, "_EXEMPLAR_FILE", f)
    vel.reset_cache()
    assert vel.build_exemplar_block("makeup") == ""


def test_missing_inner_keys_treated_as_empty(monkeypatch, tmp_path):
    """Category value missing 'exemplars'/'anti_patterns' keys → treated as []."""
    f = tmp_path / "verdict_exemplars.json"
    f.write_text(json.dumps({"makeup": {}}), encoding="utf-8")
    monkeypatch.setattr(vel, "_EXEMPLAR_FILE", f)
    vel.reset_cache()
    assert vel.build_exemplar_block("makeup") == ""


# ---------------------------------------------------------------------------
# Rendering — exemplars
# ---------------------------------------------------------------------------

def _write(tmp_path, monkeypatch, data):
    f = tmp_path / "verdict_exemplars.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(vel, "_EXEMPLAR_FILE", f)
    vel.reset_cache()
    return f


def test_exemplar_renders_into_block(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, {
        "skincare": {
            "exemplars": [
                {
                    "title": "EXAMPLE — do not copy",
                    "setup": "Budget retinol serum vs prestige retinol serum",
                    "verdict_json": {
                        "winner_index": 0,
                        "winner_declaration": "Budget Retinol Serum",
                        "winner_reason": "Same 0.3% encapsulated retinol at 60% lower price.",
                    },
                    "teaches": "H1",
                    "_provenance": "skin-018",
                }
            ],
            "anti_patterns": [],
        }
    })
    block = vel.build_exemplar_block("skincare")
    assert block != ""
    # Label present (JSON-mode safety — must signal "don't copy")
    assert "EXAMPLE" in block
    assert "do not copy" in block.lower()
    # Setup + a verdict field surface
    assert "Budget retinol serum" in block
    assert "0.3%" in block
    # Provenance is internal-only — must NOT leak into the rendered prompt
    assert "skin-018" not in block
    assert "_provenance" not in block


def test_compact_option_a_full_block(tmp_path, monkeypatch):
    """COMPACT Option A (dispatcher ruling 2026-06-11): exemplars render the
    four teaching fields as a labeled abridged block — winner as 'Product N'
    (1-based), Why/Tradeoff/Value lines — NOT a raw verdict_json dump."""
    _write(tmp_path, monkeypatch, {
        "makeup": {
            "exemplars": [
                {
                    "title": "EXAMPLE -- do not copy",
                    "setup": "Affordable glow serum vs prestige glow serum",
                    "verdict_json": {
                        "winner_index": 0,
                        "winner_reason": "Same lit-from-within glow at 70% lower price.",
                        "key_tradeoff": "The prestige pick has a richer applicator and packaging.",
                        "value_context": {
                            "product_0": "Outstanding value-per-dinar for the same finish.",
                            "product_1": "A luxury splurge — pay for the brand experience.",
                        },
                    },
                    "teaches": "H1",
                    "_provenance": "make-016",
                }
            ],
            "anti_patterns": [],
        }
    })
    block = vel.build_exemplar_block("makeup")
    # Winner rendered 1-based as "Product 1" (winner_index 0)
    assert "Product 1" in block
    # The four teaching labels surface
    assert "Why:" in block
    assert "Tradeoff:" in block
    assert "Value:" in block
    # value_context per-product dict rendered readably
    assert "value-per-dinar" in block
    assert "luxury splurge" in block
    # NOT a raw JSON dump — no JSON braces from the verdict object
    assert '"winner_index"' not in block
    assert '{"' not in block


def test_compact_fields_at_top_level_also_render(tmp_path, monkeypatch):
    """Robustness: if I1 ships the compact fields at the exemplar top level
    (no nested verdict block), they still render."""
    _write(tmp_path, monkeypatch, {
        "grocery": {
            "exemplars": [
                {
                    "title": "EXAMPLE -- do not copy",
                    "setup": "Regional staple vs imported brand",
                    "winner_index": 1,
                    "winner_reason": "The import wins on a 30% longer shelf life.",
                    "key_tradeoff": "The local staple is cheaper and more widely stocked.",
                    "value_context": {
                        "product_0": "Everyday-value staple.",
                        "product_1": "Premium import for a specific need.",
                    },
                    "teaches": "H2",
                }
            ],
            "anti_patterns": [],
        }
    })
    block = vel.build_exemplar_block("grocery")
    assert "Product 2" in block  # winner_index 1 -> Product 2
    assert "30% longer shelf life" in block
    assert "Everyday-value staple" in block


def test_field_name_aliases_tolerated(tmp_path, monkeypatch):
    """Loader is consumer of canonical content: accept common field-name
    variants ('context' for setup, 'reason'/'tradeoff'/'value') so it renders
    whatever shape the ratified exemplar content ships."""
    _write(tmp_path, monkeypatch, {
        "fashion": {
            "exemplars": [
                {
                    "title": "EXAMPLE -- do not copy",
                    "context": "Heritage leather bag vs trend-driven tote",
                    "verdict_json": {
                        "winner_index": 0,
                        "reason": "Full-grain leather lasts 5x longer than coated canvas.",
                        "tradeoff": "The trend tote is half the price.",
                        "value": {"product_0": "A buy-it-for-life investment.",
                                  "product_1": "Fashion-forward but disposable."},
                    },
                    "teaches": "H6",
                }
            ],
            "anti_patterns": [],
        }
    })
    block = vel.build_exemplar_block("fashion")
    assert "Heritage leather bag" in block      # context -> Setup
    assert "Product 1" in block                  # winner_index 0
    assert "5x longer" in block                  # reason -> Why
    assert "half the price" in block             # tradeoff -> Tradeoff
    assert "buy-it-for-life" in block            # value -> Value


def test_object_shaped_provenance_never_leaks(tmp_path, monkeypatch):
    """Dispatcher ruled I1's _provenance is OBJECT-shaped. The loader renders
    only title/setup + the 4 compact fields, so _provenance (string OR object)
    is stripped by omission — pin it never surfaces in the prompt."""
    _write(tmp_path, monkeypatch, {
        "supplements": {
            "exemplars": [
                {
                    "title": "EXAMPLE -- do not copy",
                    "setup": "Budget whey vs premium isolate",
                    "verdict_json": {
                        "winner_index": 0,
                        "winner_reason": "Same 24g protein per scoop at 35% lower cost.",
                        "key_tradeoff": "The isolate has less lactose.",
                        "value_context": {"product_0": "Best cost-per-gram protein.",
                                          "product_1": "Worth it for the lactose-sensitive."},
                    },
                    "teaches": "H1",
                    # Dispatcher-confirmed ratified shape: _provenance is an
                    # OBJECT {source_pattern_id, synthetic: true/false,
                    # rewrite_note}. Loader is type-agnostic (never reads it).
                    "_provenance": {
                        "source_pattern_id": "supp-013",
                        "synthetic": True,
                        "rewrite_note": "rewritten from Optimum Nutrition vs Dymatize ISO100; different brands",
                    },
                }
            ],
            "anti_patterns": [],
        }
    })
    block = vel.build_exemplar_block("supplements")
    assert block != ""
    # None of the object-shaped provenance keys/values may leak. (Note: the
    # word "synthetic" legitimately appears in the block HEADER — "synthetic
    # teaching cases" — so we assert the provenance KEY name + the rewrite_note
    # VALUE, not the bare word.)
    assert "supp-013" not in block
    assert "_provenance" not in block
    assert "source_pattern_id" not in block
    assert "rewrite_note" not in block
    assert "Optimum Nutrition vs Dymatize" not in block
    assert "different brands" not in block  # rewrite_note value content
    # The legitimate teaching content still renders.
    assert "24g protein" in block


def test_anti_pattern_renders_into_block(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, {
        "electronics": {
            "exemplars": [],
            "anti_patterns": [
                {
                    "name": "identical on paper = identical in Bahrain",
                    "rule": "A spec tie can break on local service/consumables availability.",
                    "teaches": "H4",
                }
            ],
        }
    })
    block = vel.build_exemplar_block("electronics")
    assert block != ""
    assert "ANTI-PATTERN" in block.upper()
    assert "identical on paper" in block
    assert "service" in block.lower()


def test_both_arrays_render_together(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, {
        "fragrances": {
            "exemplars": [
                {
                    "title": "EXAMPLE — do not copy",
                    "setup": "GCC staple oud vs imported designer scent",
                    "verdict_json": {"winner_index": 0, "winner_reason": "Wins on 8-hour longevity."},
                    "teaches": "H2",
                    "_provenance": "frag-016",
                }
            ],
            "anti_patterns": [
                {
                    "name": "global prestige outranks GCC market reality",
                    "rule": "A regional staple can outrank an import on local adoption.",
                    "teaches": "H2",
                }
            ],
        }
    })
    block = vel.build_exemplar_block("fragrances")
    assert "GCC staple oud" in block
    assert "global prestige" in block


# ---------------------------------------------------------------------------
# Cache behaviour
# ---------------------------------------------------------------------------

def test_reset_cache_picks_up_file_swap(tmp_path, monkeypatch):
    f = _write(tmp_path, monkeypatch, {"makeup": {"exemplars": [], "anti_patterns": []}})
    assert vel.build_exemplar_block("makeup") == ""
    # Swap the file content, WITHOUT reset → cached empty still returned
    f.write_text(json.dumps({
        "makeup": {
            "exemplars": [],
            "anti_patterns": [
                {"name": "climate-neutral verdicts in a 45 degree market",
                 "rule": "Grade heat/humidity wear for the Gulf.", "teaches": "H8"}
            ],
        }
    }), encoding="utf-8")
    assert vel.build_exemplar_block("makeup") == ""  # stale cache
    vel.reset_cache()
    assert "climate-neutral" in vel.build_exemplar_block("makeup")  # fresh


def test_block_is_stable_per_category_for_prompt_cache(tmp_path, monkeypatch):
    """The rendered block must be deterministic across calls (OpenAI
    prompt-cache discipline: same category → byte-identical prefix)."""
    _write(tmp_path, monkeypatch, {
        "haircare": {
            "exemplars": [
                {"title": "EXAMPLE — do not copy", "setup": "Drugstore vs salon shampoo",
                 "verdict_json": {"winner_index": 1, "winner_reason": "30% more actives per ml."},
                 "teaches": "H1", "_provenance": "x"}
            ],
            "anti_patterns": [],
        }
    })
    a = vel.build_exemplar_block("haircare")
    b = vel.build_exemplar_block("haircare")
    assert a == b
    assert a != ""


# ---------------------------------------------------------------------------
# ABRIDGED marker + COMPLETE-schema reinforcement (dispatcher order)
# ---------------------------------------------------------------------------

def test_abridged_marker_in_exemplar_label(tmp_path, monkeypatch):
    """The exemplar label must carry the ABRIDGED marker so the model never
    mistakes an abridged teaching case for the required output shape."""
    _write(tmp_path, monkeypatch, {
        "skincare": {
            "exemplars": [
                {"title": "EXAMPLE -- do not copy", "setup": "Budget vs prestige serum",
                 "verdict_json": {"winner_index": 0, "winner_reason": "Same 10% niacinamide at 50% less."},
                 "teaches": "H1", "_provenance": "x"}
            ],
            "anti_patterns": [],
        }
    })
    block = vel.build_exemplar_block("skincare")
    # Dispatcher-ratified verbatim marker (matches I1's exemplar setups).
    assert "abridged, do not copy structure or content" in block
    assert "abridged" in block.lower()


def test_complete_schema_reinforcement_after_exemplars(tmp_path, monkeypatch):
    """When exemplars are present, the reinforcement line renders AFTER them,
    verbatim, instructing the model to emit the full schema."""
    _write(tmp_path, monkeypatch, {
        "makeup": {
            "exemplars": [
                {"title": "EXAMPLE -- do not copy", "setup": "Drugstore vs luxury foundation",
                 "verdict_json": {"winner_index": 0, "winner_reason": "Matches 40-shade range at 70% less."},
                 "teaches": "H1", "_provenance": "x"}
            ],
            "anti_patterns": [],
        }
    })
    block = vel.build_exemplar_block("makeup")
    reinforcement = "The examples above are abridged. Always emit the COMPLETE verdict schema."
    assert reinforcement in block
    # It must come AFTER the exemplar content.
    assert block.index("abridged, do not copy structure or content") < block.index(reinforcement)


def test_no_reinforcement_when_only_anti_patterns(tmp_path, monkeypatch):
    """The reinforcement references 'the examples above' — it must NOT render
    when there are anti-patterns but zero exemplars (the G2 skeleton state)."""
    _write(tmp_path, monkeypatch, {
        "electronics": {
            "exemplars": [],
            "anti_patterns": [
                {"name": "identical on paper = identical in Bahrain",
                 "rule": "A spec tie can break on local service availability.", "teaches": "H4"}
            ],
        }
    })
    block = vel.build_exemplar_block("electronics")
    assert block != ""
    assert "The examples above are abridged" not in block
    assert "abridged, do not copy structure or content" not in block  # no exemplars rendered
