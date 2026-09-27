"""Auditable generator for tests/fixtures/rubric_truth_flag_on_golden.json (W4-6a, gate E3).

The flag-ON arm of the byte-identity gate: the full `compute_scores` output of the
two flag-SENSITIVE golden builders --
  * `golden_fixture_products` of tests/test_scoring_missing_dim_renormalize.py ("renorm")
  * `golden_fixture_products` of tests/test_scoring_spec_field_normalization.py ("specnorm")
-- for all 9 categories, in the three W4-6a states:
  V  = ENABLE_VALUE_DIM_PARTIAL_SIGNAL on
  T  = ENABLE_TIE_IS_NOT_MISSING on
  VT = both on
(every other scoring flag unset). `build_golden(states=("OFF",))` reproduces the
two existing *_flag_off_golden.json files for those builders, which is how
test 26 proves the generator's shape (E3).

The golden is generated from the GREEN head (never from the red tree, where the
flags are inert). Every `app.*` / `tests.*` import is LAZY. Regenerate ONLY
through pytest so tests/conftest.py and the network guard load first:

    def test_regen(monkeypatch):
        import importlib.util, os
        spec = importlib.util.spec_from_file_location(
            "gen_on", os.path.join("tests", "fixtures", "_gen_rubric_truth_flag_on_golden.py"))
        gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
        from app.services import scoring_service
        monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
        gen.write_golden()

Never run this file as a bare script.
"""
import json
import os

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))
GOLDEN_PATH = os.path.join(FIXTURES_DIR, "rubric_truth_flag_on_golden.json")

NEW_FLAGS = ("ENABLE_VALUE_DIM_PARTIAL_SIGNAL", "ENABLE_TIE_IS_NOT_MISSING")
OTHER_SCORING_FLAGS = (
    "ENABLE_BUNDLE_C_SCORING", "ENABLE_SPEC_FIELD_NORM", "ENABLE_MISSING_DIM_RENORM",
    "ENABLE_CATEGORY_VALUE_BADGE", "ENABLE_BEHAVIORAL_DIM_TRANSLATION",
    "DISABLE_DIM_NORM_DAMPENING", "WINNER_DIM_GAP_TOLERANCE",
    "WINNER_PRICE_AUTHORITY_POINTS", "WINNER_VALUE_WEIGHT_SCALE",
    "ENABLE_WINNER_PROSE_RECONCILE",
)
ALL_FLAGS = NEW_FLAGS + OTHER_SCORING_FLAGS

STATES = {
    "OFF": {},
    "V": {"ENABLE_VALUE_DIM_PARTIAL_SIGNAL": "true"},
    "T": {"ENABLE_TIE_IS_NOT_MISSING": "true"},
    "VT": {"ENABLE_VALUE_DIM_PARTIAL_SIGNAL": "true", "ENABLE_TIE_IS_NOT_MISSING": "true"},
}
ON_STATES = ("V", "T", "VT")


def _builders():
    from tests import test_scoring_missing_dim_renormalize as renorm_mod
    from tests import test_scoring_spec_field_normalization as specnorm_mod
    return {
        "renorm": renorm_mod.golden_fixture_products,
        "specnorm": specnorm_mod.golden_fixture_products,
    }


def build_golden(states=ON_STATES):
    """{state: {builder: {category: compute_scores result}}}.

    Sets/unsets os.environ itself and restores every touched name afterwards."""
    from app.services.scoring_service import CATEGORY_DIMENSIONS, ScoringService
    saved = {k: os.environ.get(k) for k in ALL_FLAGS}
    out = {}
    try:
        builders = _builders()
        for state in states:
            for k in ALL_FLAGS:
                os.environ.pop(k, None)
            os.environ.update(STATES[state])
            svc = ScoringService()
            out[state] = {
                bname: {
                    cat: json.loads(json.dumps(svc.compute_scores(build(cat))))
                    for cat in sorted(CATEGORY_DIMENSIONS)
                }
                for bname, build in builders.items()
            }
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return out


def write_golden(path=GOLDEN_PATH, generated_from="unknown"):
    golden = build_golden(ON_STATES)
    golden["_meta"] = {
        "unit": "W4-6a gate E3",
        "generated_from": generated_from,
        "generator": "tests/fixtures/_gen_rubric_truth_flag_on_golden.py",
        "states": {k: sorted(STATES[k]) for k in ON_STATES},
        "builders": "golden_fixture_products of tests/test_scoring_missing_dim_renormalize.py (renorm) "
                    "and tests/test_scoring_spec_field_normalization.py (specnorm), all 9 categories",
        "payload": "the full compute_scores result per category (tradeoffs are computed outside "
                   "compute_scores, so the tradeoff guard never moves this file)",
        "dependency": "both builders derive their spec dicts from extraction_service.CATEGORY_SPEC_SCHEMAS "
                      "(like the E2 digests' grid()) and iterate scoring_service.CATEGORY_DIMENSIONS: a schema "
                      "edit moves this golden without any scoring change - regenerate deliberately",
    }
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(golden, fh, indent=2, sort_keys=True, ensure_ascii=True)
        fh.write("\n")
    return golden
