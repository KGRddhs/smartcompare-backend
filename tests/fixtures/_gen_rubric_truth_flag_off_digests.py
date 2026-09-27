"""Auditable generator for tests/fixtures/rubric_truth_flag_off_digests.json (W4-6a, gate E2).

What it captures: for each of the 164 records below (14 named scenarios + the
144-row `grid()` + the 6 recorded `comparison_baseline_d2*.json` payloads) and
each of 3 flag states (all scoring flags unset; ENABLE_MISSING_DIM_RENORM on;
ENABLE_SPEC_FIELD_NORM on) -- with the two W4-6a flags
(ENABLE_VALUE_DIM_PARTIAL_SIGNAL, ENABLE_TIE_IS_NOT_MISSING) UNSET -- the
sha256 of the canonical JSON (sort_keys=True, ensure_ascii=True) of

    {"result": compute_scores(...), "v2": build_dimensions_v2(...),
     "cells": count_missing_dim_cells(...), "summary": build_scores_summary(...)}

`tradeoffs` / `key_tradeoff` are deliberately EXCLUDED (the ruled PO-RUBRIC-08
guard changes them, gate E5).

DEPENDENCY (ruling R10 / C7): `grid()` derives its spec dicts from
`app.services.extraction_service.CATEGORY_SPEC_SCHEMAS` (and
`scoring_service.CATEGORY_DIMENSIONS` / `NON_SCORING_SPEC_KEYS`). A schema edit
there changes the grid records and therefore the digests WITHOUT any scoring
change -- regenerate deliberately in that case and say so in the PR.

This module is also the single source of the W4-6a test builders
(`tests/test_scoring_rubric_truth.py` loads it by path). Every `app.*` import is
LAZY (inside a function) so importing the module never touches app code before
tests/conftest.py has neutralised credentials.

Regenerate ONLY through pytest (so tests/conftest.py and the network guard load
first), e.g. a throwaway probe file:

    def test_regen(monkeypatch):
        import importlib.util, os
        spec = importlib.util.spec_from_file_location(
            "gen", os.path.join("tests", "fixtures", "_gen_rubric_truth_flag_off_digests.py"))
        gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
        from app.services import scoring_service
        monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
        gen.write_digests(os.path.join("tests", "fixtures", "rubric_truth_flag_off_digests.json"))

run with `python -m pytest -p qaren_netguard -p no:randomly <probe file>`.
Never run this file as a bare script.
"""
import copy
import glob
import hashlib
import json
import os

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))
DIGESTS_PATH = os.path.join(FIXTURES_DIR, "rubric_truth_flag_off_digests.json")

NEW_FLAGS = ("ENABLE_VALUE_DIM_PARTIAL_SIGNAL", "ENABLE_TIE_IS_NOT_MISSING")
OTHER_SCORING_FLAGS = (
    "ENABLE_BUNDLE_C_SCORING", "ENABLE_SPEC_FIELD_NORM", "ENABLE_MISSING_DIM_RENORM",
    "ENABLE_CATEGORY_VALUE_BADGE", "ENABLE_BEHAVIORAL_DIM_TRANSLATION",
    "DISABLE_DIM_NORM_DAMPENING", "WINNER_DIM_GAP_TOLERANCE",
    "WINNER_PRICE_AUTHORITY_POINTS", "WINNER_VALUE_WEIGHT_SCALE",
    "ENABLE_WINNER_PROSE_RECONCILE",
)
ALL_FLAGS = NEW_FLAGS + OTHER_SCORING_FLAGS

DIGEST_STATES = {
    "OFF": {},
    "R": {"ENABLE_MISSING_DIM_RENORM": "true"},
    "S": {"ENABLE_SPEC_FIELD_NORM": "true"},
}

FULL_FC = {"specs_verified": 11, "specs_likely": 0, "specs_flagged": 0,
           "specs_unverified": 0, "price_verified": True,
           "review_sentiment_consistent": True}

ELEC_SPECS = {
    "display": "6.1 inch OLED", "processor": "A17 Pro", "ram": "8 GB",
    "storage": "256 GB", "battery": "4000 mAh", "rear_camera": "48 MP",
    "front_camera": "12 MP", "os": "iOS 18", "connectivity": "5G, Wi-Fi 7",
    "weight": "171 g", "water_resistance": "IP68",
}

BETTER_ELEC_SPECS = dict(ELEC_SPECS, ram="12 GB", storage="512 GB",
                         battery="5000 mAh", rear_camera="200 MP")

SPARSE_ELEC_SPECS = {"display": "6.1 inch", "os": "Android"}

OXFORD_SPECS = {
    "material": "Full-grain Italian calfskin leather", "style": "Oxford shoe",
    "closure_type": "Lace-up", "size_options": "39-46",
    "care_instructions": "Polish with wax", "craftsmanship": "Hand-welted Goodyear construction",
    "collection_season": "Permanent collection", "origin": "Made in Italy",
    "color": "Black", "design_details": "Brogue toe cap",
}
PU_SPECS = {
    "material": "PU synthetic leather", "style": "Oxford shoe",
    "closure_type": "Lace-up", "size_options": "39-46",
    "care_instructions": "Wipe clean", "craftsmanship": "Glued sole, machine-made",
    "collection_season": "Spring/Summer 2025", "origin": "Made in China",
    "color": "Black", "design_details": "Plain toe",
}
ALU_SPECS = {"dimensions": "30 x 20 x 10 cm", "weight": "1.2 kg", "material": "Anodised aluminium",
             "color": "Silver", "features": "TSA lock, 4 spinner wheels", "origin": "Made in Germany",
             "warranty": "Lifetime"}
ABS_SPECS = {"dimensions": "30 x 20 x 10 cm", "weight": "2.9 kg", "material": "ABS plastic",
             "color": "Silver", "features": "Zip closure, 2 wheels", "origin": "Made in China",
             "warranty": "1 year"}


def prod(brand, name, category, specs=None, rating=None, review_count=None,
         fact_check=None, price=None, source_method="local_bhd", sources=0):
    """A fresh product dict (BHD price, optional source_ratings)."""
    p = {"brand": brand, "name": name, "category": category}
    if specs is not None:
        p["specs"] = dict(specs)
    if rating is not None:
        p["rating"] = rating
    if review_count is not None:
        p["review_count"] = review_count
    if fact_check is not None:
        p["fact_check"] = dict(fact_check)
    if price is not None:
        p["price"] = {"amount": price, "currency": "BHD", "source_method": source_method}
    if sources:
        p["reviews"] = {"source_ratings": [{"source": "s%d" % i, "rating": 4.0} for i in range(sources)]}
    return p


def scenarios():
    """The 14 named W4-6a scenarios (spec section 1)."""
    sc = {}
    sc["R01_identical_spec_50v52"] = [
        prod("Brand A", "Phone X", "electronics", ELEC_SPECS, 4.5, 900, FULL_FC, 50.0),
        prod("Brand B", "Phone Y", "electronics", ELEC_SPECS, 4.5, 900, FULL_FC, 52.0)]
    sc["R01b_nospec_50v52"] = [
        prod("Brand A", "Phone X", "electronics", None, 4.5, 900, FULL_FC, 50.0),
        prod("Brand B", "Phone Y", "electronics", None, 4.5, 900, FULL_FC, 52.0)]
    sc["R02_identical_verified_50v50"] = [
        prod("Brand A", "Phone X", "electronics", ELEC_SPECS, 4.5, 900, FULL_FC, 50.0),
        prod("Brand B", "Phone Y", "electronics", ELEC_SPECS, 4.5, 900, FULL_FC, 50.0)]
    near = dict(ELEC_SPECS, battery="4400 mAh")
    sc["R02b_near_tie_spec_50v50"] = [
        prod("Brand A", "Phone X", "electronics", ELEC_SPECS, 4.5, 900, FULL_FC, 50.0),
        prod("Brand B", "Phone Y", "electronics", near, 4.5, 900, FULL_FC, 50.0)]
    sc["R02c_sparse_identical"] = [
        prod("Brand A", "Phone X", "electronics", SPARSE_ELEC_SPECS, 4.0, None, {"specs_unverified": 1}, 50.0, sources=1),
        prod("Brand B", "Phone Y", "electronics", SPARSE_ELEC_SPECS, 4.0, None, {"specs_unverified": 1}, 50.0, sources=1)]
    sc["R03_fashion_oxford_v_pu_real"] = [
        prod("Maison A", "Oxford One", "fashion", OXFORD_SPECS, 4.6, 220,
             {"specs_verified": 8, "specs_likely": 2}, 180.0),
        prod("Brand B", "Oxford Two", "fashion", PU_SPECS, 3.9, 1500,
             {"specs_verified": 5, "specs_unverified": 5}, 25.0)]
    sc["R03b_fashion_equal_signals_equal_price"] = [
        prod("Maison A", "Oxford One", "fashion", OXFORD_SPECS, 4.5, 900, FULL_FC, 60.0),
        prod("Brand B", "Oxford Two", "fashion", PU_SPECS, 4.5, 900, FULL_FC, 60.0)]
    sc["R03c_other_alu_v_abs_real"] = [
        prod("Brand A", "Case Alu", "other", ALU_SPECS, 4.4, 300, {"specs_verified": 5, "specs_likely": 2}, 250.0),
        prod("Brand B", "Case ABS", "other", ABS_SPECS, 4.0, 800, {"specs_verified": 3, "specs_unverified": 4}, 30.0)]
    sc["R03d_other_equal_signals_equal_price"] = [
        prod("Brand A", "Case Alu", "other", ALU_SPECS, 4.5, 900, FULL_FC, 60.0),
        prod("Brand B", "Case ABS", "other", ABS_SPECS, 4.5, 900, FULL_FC, 60.0)]
    sc["R08_loser_best_is_sentinel"] = [
        prod("Brand A", "Phone X", "electronics", BETTER_ELEC_SPECS, 4.8, 5000, {"specs_flagged": 10}, 40.0),
        prod("Brand B", "Phone Y", "electronics", ELEC_SPECS, 1.0, 1, None, 60.0)]
    sc["R08b_loser_best_is_sentinel_fc_mix"] = [
        prod("Brand A", "Phone X", "electronics", BETTER_ELEC_SPECS, 4.8, 5000,
             {"specs_verified": 1, "specs_flagged": 9}, 40.0),
        prod("Brand B", "Phone Y", "electronics", ELEC_SPECS, 1.0, 1, None, 60.0)]
    sc["R08d_loser_sparse_best_is_sentinel"] = [
        prod("Brand A", "Phone X", "electronics", BETTER_ELEC_SPECS, 4.8, 5000, {"specs_flagged": 10}, 40.0),
        prod("Brand B", "Phone Y", "electronics", SPARSE_ELEC_SPECS, 1.0, 1, None, 60.0)]
    sc["R08e_loser_sparse_fc_mix"] = [
        prod("Brand A", "Phone X", "electronics", BETTER_ELEC_SPECS, 4.8, 5000,
             {"specs_verified": 1, "specs_flagged": 9}, 40.0),
        prod("Brand B", "Phone Y", "electronics", SPARSE_ELEC_SPECS, 1.0, 1, None, 60.0)]
    sc["R08c_loser_has_real_strength"] = [
        prod("Brand A", "Phone X", "electronics", BETTER_ELEC_SPECS, 4.8, 5000, FULL_FC, 40.0),
        prod("Brand B", "Phone Y", "electronics", ELEC_SPECS, 3.0, 50,
             {"specs_verified": 11, "price_verified": True}, 60.0)]
    return sc


def grid():
    """16 patterns x 9 categories = 144 rows (keys "<category>|<pattern>").

    Depends on extraction_service.CATEGORY_SPEC_SCHEMAS (see module docstring)."""
    from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS
    from app.services.scoring_service import CATEGORY_DIMENSIONS, NON_SCORING_SPEC_KEYS
    out = {}
    for cat in sorted(CATEGORY_DIMENSIONS):
        schema = [f for f in CATEGORY_SPEC_SCHEMAS.get(cat, CATEGORY_SPEC_SCHEMAS["other"])
                  if f not in NON_SCORING_SPEC_KEYS]
        full_a = {f: "%d units" % ((i + 2) * 3) for i, f in enumerate(schema)}
        full_b = {f: "%d units" % ((i + 3) * 2) for i, f in enumerate(schema)}
        sparse = {f: "%d units" % ((i + 1) * 5) for i, f in enumerate(schema[:2])}
        num_f = schema[0]
        tenx_a = dict(full_a)
        tenx_a[num_f] = "32 units"
        tenx_b = dict(full_a)
        tenx_b[num_f] = "1024 units"
        nota_a = dict(full_a)
        nota_a[num_f] = "5000 mAh"
        nota_b = dict(full_a)
        nota_b[num_f] = "5 Ah"
        fc_a = {"specs_verified": 6, "specs_likely": 2}
        fc_b = {"specs_verified": 4, "specs_flagged": 1}

        def P(nm, _cat=cat, **kw):
            return prod("Brand " + nm, _cat + " " + nm, _cat, **kw)

        pats = {
            "both_full": [P("A", specs=full_a, rating=4.4, review_count=500, fact_check=fc_a, price=40.0),
                          P("B", specs=full_b, rating=4.1, review_count=300, fact_check=fc_b, price=55.0)],
            "one_missing_all_specs": [P("A", specs=full_a, rating=4.4, review_count=500, fact_check=fc_a, price=40.0),
                                      P("B", rating=4.1, review_count=300, fact_check=fc_b, price=55.0)],
            "one_missing_price": [P("A", specs=full_a, rating=4.4, review_count=500, fact_check=fc_a, price=40.0),
                                  P("B", specs=full_b, rating=4.1, review_count=300, fact_check=fc_b)],
            "nodata_vs_measured_bad": [P("A", price=50.0),
                                       P("B", specs=sparse, rating=2.0, review_count=40,
                                         fact_check={"specs_flagged": 2}, price=50.0)],
            "nodata_vs_measured_good": [P("A", price=50.0),
                                        P("B", specs=full_b, rating=4.8, review_count=2000,
                                          fact_check=FULL_FC, price=50.0)],
            "genuine_vs_estimated": [P("A", specs=full_a, rating=4.4, review_count=500, fact_check=fc_a, price=40.0),
                                     P("B", specs=full_b, rating=4.1, review_count=300, fact_check=fc_b,
                                       price=40.0, source_method="estimated")],
            "localbhd_vs_convertedusd": [P("A", specs=full_a, rating=4.4, review_count=500, fact_check=fc_a, price=40.0),
                                         P("B", specs=full_b, rating=4.1, review_count=300, fact_check=fc_b,
                                           price=40.0, source_method="converted_usd")],
            "unrated_vs_2star": [P("A", specs=full_a, fact_check=fc_a, price=40.0),
                                 P("B", specs=full_a, rating=2.0, review_count=50, fact_check=fc_a, price=40.0)],
            "49star900_vs_unrated": [P("A", specs=full_a, rating=4.9, review_count=900, fact_check=fc_a, price=40.0),
                                     P("B", specs=full_a, fact_check=fc_a, price=40.0)],
            "identical": [P("A", specs=full_a, rating=4.5, review_count=900, fact_check=FULL_FC, price=40.0),
                          P("B", specs=full_a, rating=4.5, review_count=900, fact_check=FULL_FC, price=40.0)],
            "extreme_price_ratio": [P("A", specs=full_a, rating=4.4, review_count=500, fact_check=fc_a, price=5.0),
                                    P("B", specs=full_b, rating=4.1, review_count=300, fact_check=fc_b, price=5000.0)],
            "both_no_price": [P("A", specs=full_a, rating=4.4, review_count=500, fact_check=fc_a),
                              P("B", specs=full_b, rating=4.1, review_count=300, fact_check=fc_b)],
            "sparse_vs_sparse": [P("A", specs=sparse, fact_check={"specs_unverified": 1}, price=40.0),
                                 P("B", specs=sparse, fact_check={"specs_unverified": 1}, price=45.0)],
            "factcheck_only_gap": [P("A", specs=full_a, rating=4.4, review_count=500, fact_check=FULL_FC, price=40.0),
                                   P("B", specs=full_a, rating=4.4, review_count=500,
                                     fact_check={"specs_unverified": 8}, price=40.0)],
            "same_unit_10x_gap": [P("A", specs=tenx_a, rating=4.4, review_count=500, fact_check=fc_a, price=40.0),
                                  P("B", specs=tenx_b, rating=4.4, review_count=500, fact_check=fc_a, price=40.0)],
            "notation_gap": [P("A", specs=nota_a, rating=4.4, review_count=500, fact_check=fc_a, price=40.0),
                             P("B", specs=nota_b, rating=4.4, review_count=500, fact_check=fc_a, price=40.0)],
        }
        for pn, pr in pats.items():
            out["%s|%s" % (cat, pn)] = pr
    return out


def d2_records():
    """The `products` blocks of the 6 recorded tests/fixtures/comparison_baseline_d2*.json."""
    out = {}
    for f in sorted(glob.glob(os.path.join(FIXTURES_DIR, "comparison_baseline_d2*.json"))):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        prods = []
        for p in d["products"]:
            q = {k: p.get(k) for k in ("brand", "name", "category", "specs", "rating",
                                       "review_count", "fact_check", "price", "reviews")}
            prods.append({k: v for k, v in q.items() if v is not None})
        out[os.path.basename(f)] = prods
    return out


def all_records():
    """{"S:<scenario>" | "G:<cat>|<pattern>" | "D:<file>": [product, product]} -- 164 records."""
    recs = {}
    recs.update({"S:" + k: v for k, v in scenarios().items()})
    recs.update({"G:" + k: v for k, v in grid().items()})
    recs.update({"D:" + k: v for k, v in d2_records().items()})
    return recs


def product_names(products):
    from app.services.text_sanitize import dedup_brand_name
    return [dedup_brand_name(str(p.get("brand") or ""), str(p.get("name") or "")) for p in products]


def record_payload(svc, products):
    """The E2 payload for one record in the CURRENT environment."""
    from app.services.scoring_service import build_dimensions_v2, count_missing_dim_cells
    p = copy.deepcopy(products)
    result = svc.compute_scores(p)
    cat = result.get("category", "other")
    return {
        "result": result,
        "v2": build_dimensions_v2(p, result, cat),
        "cells": count_missing_dim_cells(result, cat),
        "summary": svc.build_scores_summary(result, product_names(p)),
    }


def canonical_sha256(obj):
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def build_digests():
    """{"<state>|<record id>": sha256} over DIGEST_STATES x all_records().

    Sets/unsets os.environ itself and restores every touched name afterwards.
    The caller resets `scoring_service._BUNDLE_C_SCORING_FLAG` (process cache)."""
    from app.services.scoring_service import ScoringService
    saved = {k: os.environ.get(k) for k in ALL_FLAGS}
    out = {}
    try:
        recs = all_records()
        for state, env in DIGEST_STATES.items():
            for k in ALL_FLAGS:
                os.environ.pop(k, None)
            os.environ.update(env)
            svc = ScoringService()
            for rid, products in recs.items():
                out["%s|%s" % (state, rid)] = canonical_sha256(record_payload(svc, products))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return out


def write_digests(path=DIGESTS_PATH, captured_at="unknown"):
    digests = build_digests()
    doc = {
        "_meta": {
            "unit": "W4-6a gate E2",
            "captured_at": captured_at,
            "generator": "tests/fixtures/_gen_rubric_truth_flag_off_digests.py",
            "states": {k: sorted(v) for k, v in DIGEST_STATES.items()},
            "records": 164,
            "payload": "sha256(json.dumps({result, v2, cells, summary}, sort_keys=True, ensure_ascii=True)); "
                       "tradeoffs/key_tradeoff excluded",
            "dependency": "grid() derives its spec dicts from extraction_service.CATEGORY_SPEC_SCHEMAS "
                          "(+ scoring_service.CATEGORY_DIMENSIONS, NON_SCORING_SPEC_KEYS): a schema edit "
                          "moves these digests without any scoring change - regenerate deliberately",
        },
        "digests": digests,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, ensure_ascii=True)
        fh.write("\n")
    return doc
