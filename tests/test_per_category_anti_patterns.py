"""S2 I2.3 — per-category anti-patterns in data/verdict_exemplars.json.

These are MY (Lane I2) content — named-failure-mode + one-line counter-rule,
sitting in the shared exemplar file beside I1's exemplars. Mapping per dossier
§3: H4 -> electronics, H2 -> grocery/fragrances/makeup, H8 -> skincare/makeup/
electronics(appliances), H6 -> electronics. The loader renders them; this test
reads the REAL shipped file (not a tmp fixture) so it pins the actual content.
"""

import json
from pathlib import Path

import pytest

from app.services import verdict_exemplar_loader as vel

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FILE = _REPO_ROOT / "data" / "verdict_exemplars.json"


@pytest.fixture(autouse=True)
def _reset_loader_cache():
    vel.reset_cache()
    yield
    vel.reset_cache()


def _load():
    return json.loads(_FILE.read_text(encoding="utf-8"))


def _ap_names(category_entry):
    return {ap.get("name", "").lower() for ap in category_entry.get("anti_patterns", [])}


# Expected named failure modes per category (dossier §2/§3 H-tag mapping).
EXPECTED = {
    "electronics": ["identical on paper", "newer spec sheet"],   # H4, H6
    "grocery":     ["global prestige"],                          # H2
    "fragrances":  ["global prestige"],                          # H2
    "makeup":      ["global prestige", "climate-neutral"],       # H2, H8
    "skincare":    ["climate-neutral"],                          # H8
}


@pytest.mark.parametrize("category,fragments", list(EXPECTED.items()))
def test_category_has_expected_anti_patterns(category, fragments):
    data = _load()
    assert category in data, f"{category} missing from exemplar file"
    names = " ".join(_ap_names(data[category]))
    for frag in fragments:
        assert frag in names, f"{category}: AP for {frag!r} missing"


def test_every_anti_pattern_has_name_and_rule():
    data = _load()
    for cat, entry in data.items():
        if cat.startswith("_"):  # skip _schema
            continue
        for ap in entry.get("anti_patterns", []):
            assert ap.get("name"), f"{cat}: anti_pattern missing name"
            assert ap.get("rule"), f"{cat}: anti_pattern {ap.get('name')!r} missing rule"


def test_anti_patterns_render_into_block():
    """Each category that has APs renders an ANTI-PATTERN line."""
    for cat in EXPECTED:
        block = vel.build_exemplar_block(cat)
        assert "ANTI-PATTERN" in block.upper(), f"{cat}: no AP rendered"


def test_ap_carrying_categories_render_their_aps_post_g3():
    """F1 (post-G3, was test_g2_state_ap_only): at G2 every populated category was
    AP-only; after the I1 G3 fill those same categories ALSO carry exemplars, so
    the AP block now renders ALONGSIDE the examples preamble + reinforcement. This
    pins the surviving real-file behaviour: every AP-carrying category still
    renders its anti-patterns (the I2.3 content is not dropped by the fill)."""
    data = _load()
    ap_cats = [
        c for c, e in data.items()
        if not c.startswith("_") and e.get("anti_patterns")
    ]
    assert ap_cats, "expected AP-carrying categories in the shipped file"
    for cat in ap_cats:
        block = vel.build_exemplar_block(cat)
        assert block != ""
        assert "ANTI-PATTERN" in block.upper()         # I2.3 APs still render
        assert "Avoid these failure modes:" in block


def test_ap_only_category_renders_aps_without_examples_scaffolding(tmp_path, monkeypatch):
    """The G2 behavioural invariant, preserved against render drift: when a
    category has anti_patterns but ZERO exemplars, the loader renders the AP
    block ONLY — NO 'examples below' preamble (incoherent with zero examples)
    and NO 'examples above are abridged' reinforcement. Pinned via a tmp fixture
    (the real file no longer has any AP-only category post-G3, so the behaviour
    must be exercised against a constructed file, not the shipped one)."""
    f = tmp_path / "verdict_exemplars.json"
    f.write_text(json.dumps({
        "electronics": {
            "exemplars": [],
            "anti_patterns": [
                {"name": "identical on paper = identical in Bahrain",
                 "rule": "A spec tie can break on local service/consumables.",
                 "teaches": "H4"}
            ],
        }
    }), encoding="utf-8")
    monkeypatch.setattr(vel, "_EXEMPLAR_FILE", f)
    vel.reset_cache()
    block = vel.build_exemplar_block("electronics")
    assert block != ""
    assert "ANTI-PATTERN" in block.upper()                       # APs render
    assert "Avoid these failure modes:" in block
    assert "examples below" not in block.lower()                  # NO examples preamble
    assert "examples above are abridged" not in block.lower()     # NO reinforcement


def test_anti_patterns_forbidden_words_clean():
    forbidden = ["estimated", "reference price", "couldn't", "try again", "failed to"]
    for cat in EXPECTED:
        block = vel.build_exemplar_block(cat).lower()
        for bad in forbidden:
            assert bad not in block, f"{cat}: forbidden {bad!r} in AP block"


def test_anti_patterns_carry_no_unsourced_numbers_or_store_counts():
    """Decision C guardrail: per-category APs must not introduce store counts /
    branch names / unsourced statistics either."""
    import re
    data = _load()
    for cat, entry in data.items():
        if cat.startswith("_"):
            continue
        for ap in entry.get("anti_patterns", []):
            rule = ap.get("rule", "")
            # No digit-led store/branch counts like "12 stores" / "5 branches".
            assert not re.search(r"\d+\s*(stores?|branches?|outlets?)", rule.lower()), (
                f"{cat}: AP rule names a store/branch count: {rule!r}"
            )
