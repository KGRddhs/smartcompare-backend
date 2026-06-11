"""S2 I2.2 — global anti-patterns + Bahrain-buyer localization directive.

The H1/H3 disjoint-mirror bias (34/82 fails, dossier §2) means price-positioning
judgment is broken in BOTH directions. The COMPARISON_SYSTEM RULES block gets:
  - the H1/H3 discriminator anti-pattern (value-per-dinar at parity UNLESS a
    durability/service/update gap licenses the premium), and
  - the localization directive ("grade as a Bahrain buyer, not a global spec
    sheet") carrying Decision C's qualitative-only guardrail verbatim.

These live in COMPARISON_SYSTEM itself (the static base) so they apply to every
verdict regardless of category. Must obey the forbidden-words audit.
"""

from app.services.extraction_service import COMPARISON_SYSTEM, build_verdict_prompt


def test_h1_h3_discriminator_present():
    text = COMPARISON_SYSTEM.lower()
    # The discriminator names value-per-dinar AND the licensing exception.
    assert "value-per-dinar" in text or "value per dinar" in text
    assert "parity" in text
    # The premium is licensed only by a durability / service / update gap.
    assert "durability" in text
    assert "service" in text
    assert "update" in text or "guarantee" in text


def test_h1_h3_is_a_discriminator_not_a_direction():
    """Must NOT hard-code 'cheaper always wins' or 'premium always wins' — it
    teaches WHEN each applies (dossier §2: exemplars/APs teach the
    discriminator, never a direction)."""
    text = COMPARISON_SYSTEM.lower()
    assert "cheaper always" not in text
    assert "premium always" not in text
    # the conditional 'unless' is the discriminator hinge
    assert "unless" in text


def test_localization_directive_present():
    text = COMPARISON_SYSTEM.lower()
    assert "bahrain buyer" in text
    # the contrast with a global spec sheet
    assert "global spec sheet" in text or "spec sheet" in text


def test_decision_c_qualitative_guardrail_verbatim():
    """Decision C: qualitative claims allowed, but NO store counts / branch
    names / unsourced numbers. The guardrail sentence must be present so the
    model knows the boundary."""
    text = COMPARISON_SYSTEM.lower()
    # qualitative exemplar phrasings from Decision C
    assert "widely available in bahrain" in text or "gcc crowd-pleaser" in text
    # the explicit prohibition
    assert "store counts" in text or "store count" in text
    assert "branch names" in text or "branch name" in text


def test_global_aps_in_built_verdict_prompt():
    """The APs ship inside COMPARISON_SYSTEM, so they appear in every built
    verdict prompt (any category)."""
    prompt = build_verdict_prompt(products=[{"name": "X", "category_used": "electronics"}])
    lower = prompt.lower()
    assert "value-per-dinar" in lower or "value per dinar" in lower
    assert "bahrain buyer" in lower


def test_global_aps_pass_forbidden_words_audit():
    """No scary copy / 'estimated' / 'reference price' introduced by the APs."""
    text = COMPARISON_SYSTEM.lower()
    for forbidden in ["estimated", "reference price", "couldn't", "try again", "failed to"]:
        assert forbidden not in text, f"forbidden phrase {forbidden!r} in COMPARISON_SYSTEM"
