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


def test_g2_state_ap_only_no_examples_preamble_no_reinforcement():
    """F1 (G2 ultracode): the SHIPPED file has exemplars[] EMPTY + per-category
    anti_patterns POPULATED. An AP-only category must render the AP block ONLY —
    NO 'examples below' preamble (incoherent with zero examples) and NO
    'examples above are abridged' reinforcement. Reads the REAL shipped file."""
    data = _load()
    # Every populated category in the shipped file is AP-only at G2.
    ap_only = [
        c for c, e in data.items()
        if not c.startswith("_") and (e.get("anti_patterns") and not e.get("exemplars"))
    ]
    assert ap_only, "expected AP-only categories in the shipped G2 file"
    for cat in ap_only:
        block = vel.build_exemplar_block(cat)
        assert block != ""
        assert "ANTI-PATTERN" in block.upper()           # APs render
        assert "examples below" not in block.lower()       # NO examples preamble
        assert "examples above are abridged" not in block.lower()  # NO reinforcement
        assert "Avoid these failure modes:" in block


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
