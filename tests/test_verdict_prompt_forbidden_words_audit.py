"""S2 I2.6 — forbidden-words audit over the WHOLE verdict-prompt assembly path.

The pre-S2 audit (test_comparison_quality_detector.py:180) only checked the
'other' category with no exemplars. S2 adds per-category exemplar + anti-pattern
injection — this audit walks ALL 9 categories AND the exemplar/AP rendering
path itself so no injected text smuggles in 'estimated', 'reference price', or
scary copy (EN forbidden vocab). Mirrors the i18n copy contract.
"""

import json

import pytest

from app.services import extraction_service
from app.services import verdict_exemplar_loader as vel

# EN forbidden vocab (Qaren copy contract + Bundle C "estimated" rule).
FORBIDDEN = [
    "estimated",
    "reference price",
    "couldn't",
    "try again",
    "failed to",
    "we couldn't",
    "unable to",
]

ALL_CATEGORIES = [
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
]


@pytest.fixture(autouse=True)
def _reset_loader_cache():
    vel.reset_cache()
    yield
    vel.reset_cache()


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_verdict_prompt_clean_every_category_empty_exemplars(category):
    """With the shipped (empty) exemplar file, every category's verdict prompt
    — base + personality + global APs + pain-workflow — is forbidden-word
    clean."""
    prompt = extraction_service.build_verdict_prompt(
        products=[{"name": "X", "category_used": category}],
        user_cohort={"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"},
    ).lower()
    for bad in FORBIDDEN:
        assert bad not in prompt, f"[{category}] forbidden {bad!r} in verdict prompt"


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_exemplar_ap_assembly_path_clean(category, tmp_path, monkeypatch):
    """Seed every category with an exemplar + anti-pattern, then audit the
    assembled block. This exercises the rendering path I1's content will flow
    through — the audit catches forbidden vocab regardless of who authored it."""
    data = {
        cat: {
            "exemplars": [
                {
                    "title": "EXAMPLE -- do not copy",
                    "setup": f"A {cat} value pick vs a {cat} premium pick",
                    "verdict_json": {
                        "winner_index": 0,
                        "winner_reason": "Matches the rival at 40% lower price.",
                    },
                    "teaches": "H1",
                    "_provenance": "synthetic",
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
        for cat in ALL_CATEGORIES
    }
    f = tmp_path / "verdict_exemplars.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(vel, "_EXEMPLAR_FILE", f)
    vel.reset_cache()

    block = vel.build_exemplar_block(category).lower()
    assert block != ""
    for bad in FORBIDDEN:
        assert bad not in block, f"[{category}] forbidden {bad!r} in exemplar block"

    # And the full assembled prompt with content present stays clean too.
    full = extraction_service.build_verdict_prompt(
        products=[{"name": "X", "category_used": category}],
    ).lower()
    for bad in FORBIDDEN:
        assert bad not in full, f"[{category}] forbidden {bad!r} in full prompt w/ exemplars"


def test_no_ui_banner_directive_any_category(tmp_path, monkeypatch):
    """Critical rule #1 holds across the exemplar path: never instruct a UI
    banner."""
    for category in ALL_CATEGORIES:
        prompt = extraction_service.build_verdict_prompt(
            products=[{"name": "X", "category_used": category}],
            comparison_quality="weird",
        ).lower()
        assert "show banner" not in prompt
        assert "info banner" not in prompt
        assert "display warning" not in prompt
