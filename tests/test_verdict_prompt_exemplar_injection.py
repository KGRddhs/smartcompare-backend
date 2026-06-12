"""Tests for S2 I2.1 — verdict-prompt few-shot exemplar injection.

build_verdict_prompt() must inject build_exemplar_block(category) AFTER the
category personality and BEFORE the pain-workflow block, inside the
static-per-category prefix (OpenAI prompt-cache discipline). When a category
carries NEITHER exemplars nor anti-patterns the injection is a no-op. With
content present (APs at G2, +exemplars at G3) the rendered text must appear and
must obey the forbidden-words audit.

NOTE: the SHIPPED G2 file is NOT all-empty — it ships anti_patterns[] populated
(exemplars[] empty), so production renders the AP block at G2. The all-empty
cases here exercise the degenerate no-op path, not the G2 shipped state.
"""

import json

import pytest

from app.services import extraction_service
from app.services import verdict_exemplar_loader as vel


@pytest.fixture(autouse=True)
def _reset_loader_cache():
    vel.reset_cache()
    yield
    vel.reset_cache()


def _seed(tmp_path, monkeypatch, data):
    f = tmp_path / "verdict_exemplars.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(vel, "_EXEMPLAR_FILE", f)
    vel.reset_cache()


def test_empty_file_injection_is_noop(monkeypatch, tmp_path):
    """Degenerate case (NOT the G2 shipped state): a category with BOTH arrays
    empty → no exemplar section rendered, prompt identical to no-exemplar."""
    _seed(tmp_path, monkeypatch, {
        "electronics": {"exemplars": [], "anti_patterns": []},
    })
    with_block = extraction_service.build_verdict_prompt(
        products=[{"name": "X", "category_used": "electronics"}],
    )
    # No exemplar section header rendered
    assert "Verdict calibration" not in with_block


def test_exemplar_block_injected_for_category(monkeypatch, tmp_path):
    _seed(tmp_path, monkeypatch, {
        "skincare": {
            "exemplars": [
                {
                    "title": "EXAMPLE -- do not copy",
                    "setup": "Budget vitamin C serum vs prestige vitamin C serum",
                    "verdict_json": {
                        "winner_index": 0,
                        "winner_reason": "Same 15% L-ascorbic acid at 55% lower price.",
                    },
                    "teaches": "H1",
                    "_provenance": "skin-018",
                }
            ],
            "anti_patterns": [
                {
                    "name": "climate-neutral verdicts in a 45 degree market",
                    "rule": "Weigh heat/humidity stability for the Gulf climate.",
                    "teaches": "H8",
                }
            ],
        }
    })
    prompt = extraction_service.build_verdict_prompt(
        products=[{"name": "A serum", "category_used": "skincare"}],
    )
    assert "Verdict calibration" in prompt
    assert "Budget vitamin C serum" in prompt
    assert "15%" in prompt
    assert "climate-neutral verdicts" in prompt
    # Provenance never leaks
    assert "skin-018" not in prompt


def test_exemplar_injected_before_pain_workflow(monkeypatch, tmp_path):
    """Position invariant: exemplar block precedes the pain-workflow block so
    it sits in the static-per-category prefix (cohort-varying text comes
    after — prompt-cache discipline)."""
    _seed(tmp_path, monkeypatch, {
        "electronics": {
            "exemplars": [
                {"title": "EXAMPLE -- do not copy", "setup": "AC unit A vs AC unit B",
                 "verdict_json": {"winner_index": 1, "winner_reason": "20% higher SEER rating."},
                 "teaches": "H3", "_provenance": "elec-024"}
            ],
            "anti_patterns": [],
        }
    })
    prompt = extraction_service.build_verdict_prompt(
        products=[{"name": "AC", "category_used": "electronics"}],
        user_cohort={"age_group": "25-34", "gender": "Male", "nationality": "Bahraini"},
    )
    exemplar_pos = prompt.find("Verdict calibration")
    pain_pos = prompt.find("Buyer pain-workflow constraints")
    assert exemplar_pos != -1
    # pain-workflow block present for a known cohort
    assert pain_pos != -1
    assert exemplar_pos < pain_pos


def test_exemplar_injected_after_personality(monkeypatch, tmp_path):
    """The exemplar block must come AFTER the COMPARISON_SYSTEM base +
    personality (i.e. not at the very top)."""
    _seed(tmp_path, monkeypatch, {
        "makeup": {
            "exemplars": [
                {"title": "EXAMPLE -- do not copy", "setup": "Drugstore vs luxury foundation",
                 "verdict_json": {"winner_index": 0, "winner_reason": "Matches 40-shade range at 70% less."},
                 "teaches": "H1", "_provenance": "make-016"}
            ],
            "anti_patterns": [],
        }
    })
    prompt = extraction_service.build_verdict_prompt(
        products=[{"name": "Foundation", "category_used": "makeup"}],
    )
    base_pos = prompt.find("You are a product comparison expert")
    exemplar_pos = prompt.find("Verdict calibration")
    assert base_pos != -1 and exemplar_pos != -1
    assert base_pos < exemplar_pos


def test_injection_failure_never_raises(monkeypatch, tmp_path):
    """A broken loader must not break the verdict prompt (best-effort)."""
    def _boom(_category):
        raise RuntimeError("loader exploded")
    monkeypatch.setattr(
        "app.services.verdict_exemplar_loader.build_exemplar_block", _boom
    )
    # Should not raise — the try/except in build_verdict_prompt swallows it.
    prompt = extraction_service.build_verdict_prompt(
        products=[{"name": "X", "category_used": "electronics"}],
    )
    assert "You are a product comparison expert" in prompt
