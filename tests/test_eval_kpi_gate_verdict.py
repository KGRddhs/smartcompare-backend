"""Wave-1 — the machine-readable warmer-activation gate verdict.

`kpi_gate_verdict` turns the KPI's per-category dict into a structured
`{threshold, pass, failing, measured_categories}` so a runbook / CI can decide
warmer activation without re-deriving the >=0.85 rule. Critically it FAILS on
zero data (the old inline `failing` dict was empty for an empty per_category
and thus PASSED on nothing measured).
"""
from __future__ import annotations

from scripts.eval_runner import kpi_gate_verdict, USABLE_EXACT_GENUINE_GATE


def _cat(share, requested=6):
    return {"usable": round(share * requested), "requested": requested, "share": share}


def test_all_categories_above_gate_pass():
    pc = {"electronics": _cat(0.9), "fragrances": _cat(0.86), "fashion": _cat(1.0)}
    v = kpi_gate_verdict(pc)
    assert v["pass"] is True
    assert v["failing"] == {}
    assert v["measured_categories"] == ["electronics", "fashion", "fragrances"]


def test_one_category_below_gate_fails_and_names_it():
    pc = {"electronics": _cat(0.9), "fragrances": _cat(0.5)}
    v = kpi_gate_verdict(pc)
    assert v["pass"] is False
    assert "fragrances" in v["failing"]
    assert "electronics" not in v["failing"]


def test_empty_per_category_does_not_pass():
    # Zero measured data must NEVER auto-unlock the warmer.
    v = kpi_gate_verdict({})
    assert v["pass"] is False
    assert v["measured_categories"] == []


def test_zero_requested_category_is_not_measured():
    pc = {"electronics": _cat(0.9), "grocery": {"usable": 0, "requested": 0, "share": 0.0}}
    v = kpi_gate_verdict(pc)
    assert v["measured_categories"] == ["electronics"]
    assert v["pass"] is True  # grocery had nothing measured -> ignored, not a fail


def test_threshold_is_inclusive():
    pc = {"electronics": _cat(USABLE_EXACT_GENUINE_GATE)}
    v = kpi_gate_verdict(pc)
    assert v["pass"] is True


def test_default_threshold_is_085():
    assert USABLE_EXACT_GENUINE_GATE == 0.85
