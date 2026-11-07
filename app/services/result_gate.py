"""B1 RESULT-STATUS (S80, ENABLE_RESULT_STATUS_METADATA): the pure predicates behind the
honest status of a built comparison body.

Rules implemented here: R-A4 (the status vocabulary, identity_confidence, data_coverage and
overview.winner.supported; the minimum evidence to crown), R-A5 (placeholder identity and
same identity, with the brand condition of R0-5) and R0-5 (the AUDITABLE reading of
data_coverage: both prices showable and not estimated, both ratings real, a real two-sided
spec row that is not model knowledge (a tier-3 synthesis or a training_data field), a
non-sentinel non-low dimension with a margin of at least DIM_MARGIN; the LITERAL reading
rides beside it so production sizes the gap).

Every function is total: a malformed input yields the conservative answer and never
raises. Pure by contract: the standard library plus text_sanitize.dedup_brand_name,
nothing that does I/O, nothing that reads a flag except result_status_metadata_enabled,
stamp_camera_stage_timings, result_gate_enabled and result_gate_refusal (each reads its flag
per call, first). B2 (ENABLE_RESULT_GATE) enforces exactly what assess_result measures here.
B1b (S81-G8): assess_result(url_mode=True) reads the price / rating facts and the per-side
corroboration through the URL readers (_url_price / _url_rating); the default False keeps
every existing caller byte-identical.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.services.text_sanitize import dedup_brand_name

# ----------------------------------------------------------------- vocabulary (R-A4)
STATUS_SUPPORTED = "supported_result"
STATUS_PARTIAL = "partial_no_winner"
STATUS_NEEDS_ID = "needs_identification"
STATUS_UNSUPPORTED = "unsupported_category"
STATUS_FAILED = "failed"
STATUSES = (STATUS_SUPPORTED, STATUS_PARTIAL, STATUS_NEEDS_ID, STATUS_UNSUPPORTED, STATUS_FAILED)
CONFIDENCE_LEVELS = ("high", "medium", "low", "unresolved")
# Emission order; the status is decided by the FIRST applicable reason.
REASONS = (
    "not_success",
    "placeholder_identity",
    "same_identity",
    "unsupported_category",
    "category_conflict",
    "no_evidence",
)
_STATUS_BY_REASON = {
    "not_success": STATUS_FAILED,
    "placeholder_identity": STATUS_NEEDS_ID,
    "same_identity": STATUS_NEEDS_ID,
    "unsupported_category": STATUS_UNSUPPORTED,
    "category_conflict": STATUS_UNSUPPORTED,
    "no_evidence": STATUS_PARTIAL,
}
# A literal copy of the nine schema keys (pinned equal to the source by the unit's P10 row,
# so this module never imports the schema table).
CANONICAL_CATEGORIES = frozenset({
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
})
# R-A5: compared after norm() on both sides.
PLACEHOLDERS = frozenset({"", "unknown", "unknown product", "n/a", "product", "this product"})
# A superset of the builder's spec NA tokens; matched with value.strip().lower() (B1-R2).
NA_VALUES = frozenset({"", "n/a", "na", "none", "unknown", "-"})
DIM_FLAGGED = frozenset({"missing", "limited_data", "tier3"})
DIM_MARGIN = 3.0
SENTINEL_SCORE = 50  # the scoring MISSING_SCORE sentinel (P10 pins the equality)
SECTION_KEYS = ("specs", "reviews", "pros_cons", "price")
SECTION_STATES = ("available", "partial", "unavailable")
TIER3_MARKER = "tier3_synthesis"
# R-A4 (fix round F1-3): model knowledge is never evidence -- a tier-3 synthesis and a field the
# specs prompt filled from training data; retrieved markers (snippet, db, smart_fallback,
# tier2_fallback) keep counting.
MODEL_KNOWLEDGE_MARKERS = frozenset({TIER3_MARKER, "training_data"})
# F1-6: the stages the server stamps on metadata.partial_stage (the return values of
# StructuredComparisonService._partial_stage, pinned equal to the source by the unit's F1-6 row).
PARTIAL_STAGES = frozenset({"gather", "post_gather", "scoring", "verdict"})
JACCARD_THRESHOLD = 0.9
VISION_BUCKET_MS = 1000
COMPARE_BUCKET_MS = 5000

_TRUTHY = ("true", "1", "yes", "on")
# The Arabic block is built at run time so this file stays pure ASCII.
_NORM_RE = re.compile("[^0-9a-z" + chr(0x0600) + "-" + chr(0x06FF) + "]+")


def result_status_metadata_enabled() -> bool:
    """ENABLE_RESULT_STATUS_METADATA, default OFF, read per call (the house idiom)."""
    return os.getenv("ENABLE_RESULT_STATUS_METADATA", "false").strip().lower() in _TRUTHY


# ----------------------------------------------------------------- text helpers

def norm(text: Any) -> str:
    """casefold; every run outside [0-9a-z Arabic] becomes one space; collapsed; stripped."""
    if not isinstance(text, str):
        return ""
    return _NORM_RE.sub(" ", text.casefold()).strip()


_PLACEHOLDERS_NORM = frozenset(norm(p) for p in PLACEHOLDERS)


def _str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _num(value: Any) -> bool:
    """A real number, never a bool (True would otherwise read as 1)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


_INF = float("inf")


def _finite(value: Any) -> bool:
    """F1-5: a real number that int() accepts (not inf, -inf or nan); the stdlib-free form of
    math.isfinite, so this module keeps its pinned import set (P11)."""
    return _num(value) and value == value and value not in (_INF, -_INF)


def identity_text(brand: Any, name: Any) -> str:
    """The display identity (R0-5: the brand alone is never the identity)."""
    try:
        return dedup_brand_name(_str(brand), _str(name))
    except Exception:  # noqa: BLE001 -- total
        return (_str(brand) + " " + _str(name)).strip()


# ----------------------------------------------------------------- identity (R-A5)

def is_placeholder_identity(text: Any, site_title: Any = None) -> bool:
    n = norm(text)
    if n in _PLACEHOLDERS_NORM:
        return True
    title = norm(site_title)
    return bool(title) and n == title


def product_is_placeholder(product: Any) -> bool:
    """True when the identity (brand + name deduplicated) or the name alone is a placeholder."""
    if not isinstance(product, dict):
        return True
    brand, name = product.get("brand"), product.get("name")
    return is_placeholder_identity(identity_text(brand, name)) or is_placeholder_identity(name)


def token_jaccard(a: Any, b: Any) -> float:
    sa, sb = set(norm(a).split()), set(norm(b).split())
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / float(len(sa | sb))


def _variant_axis(product: Dict[str, Any]) -> str:
    return norm(product.get("variant") or product.get("size_or_count") or "")


def _features_axis(product: Dict[str, Any]) -> str:
    feats = product.get("distinguishing_features")
    if not isinstance(feats, (list, tuple)):
        return ""
    return norm(" ".join(str(f) for f in feats if f))


def _axes_differ(p0: Dict[str, Any], p1: Dict[str, Any]) -> bool:
    """An axis both products carry with different values (one-sided values never veto)."""
    for axis in (_variant_axis, _features_axis):
        a, b = axis(p0), axis(p1)
        if a and b and a != b:
            return True
    return False


def same_identity(p0: Any, p1: Any) -> bool:
    """R-A5 with the brand condition (R0-5): the normalised identities are equal, or the
    brands are equal and the name tokens overlap at Jaccard >= 0.9. A size / variant /
    distinguishing_features axis read on BOTH sides with different values is never the same
    identity (the same perfume at two sizes stays a valid pair) -- on either arm."""
    p0 = p0 if isinstance(p0, dict) else {}
    p1 = p1 if isinstance(p1, dict) else {}
    b0, n0 = p0.get("brand"), p0.get("name")
    b1, n1 = p1.get("brand"), p1.get("name")
    same = norm(identity_text(b0, n0)) == norm(identity_text(b1, n1))
    if not same:
        same = norm(b0) == norm(b1) and token_jaccard(n0, n1) >= JACCARD_THRESHOLD
    return bool(same) and not _axes_differ(p0, p1)


def _canon(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    v = value.strip().casefold()
    return v or None


def identity_coherence(product_categories: Any, category_used: Any = None) -> bool:
    """False only when BOTH per-product categories are canonical, not 'other' and differ.
    category_used is accepted for the B2 signature and never makes a pair incoherent (R0-4)."""
    if not isinstance(product_categories, (list, tuple)) or len(product_categories) != 2:
        return True
    a, b = _canon(product_categories[0]), _canon(product_categories[1])
    if a is None or b is None:
        return True
    if a not in CANONICAL_CATEGORIES or b not in CANONICAL_CATEGORIES:
        return True
    if a == "other" or b == "other":
        return True
    return a == b


# ----------------------------------------------------------------- evidence facts (R0-5)

def price_is_showable(price: Any) -> bool:
    """The AUDITABLE price fact: a positive amount, not pended, not estimated, with a named
    source method that is not 'estimated' (equals the builder chokepoint's verdict by position)."""
    if not isinstance(price, dict):
        return False
    amount = price.get("amount")
    if not _num(amount) or amount <= 0:
        return False
    if price.get("unavailable") is True or price.get("estimated") is True:
        return False
    method = price.get("source_method")
    return isinstance(method, str) and bool(method.strip()) and method != "estimated"


def price_is_present_literal(price: Any) -> bool:
    """The LITERAL price fact (R0's price_task): a numeric amount, not pended, not estimated;
    an empty source method passes."""
    if not isinstance(price, dict):
        return False
    if not _num(price.get("amount")):
        return False
    if price.get("unavailable") is True or price.get("estimated") is True:
        return False
    return price.get("source_method") != "estimated"


def rating_is_real(product: Any) -> bool:
    if not isinstance(product, dict):
        return False
    return _num(product.get("rating")) and product.get("rating_derived") is not True


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in NA_VALUES
    return False


def _tier3_fields(specs: Dict[str, Any]) -> set:
    """The fields this side marks as model knowledge (MODEL_KNOWLEDGE_MARKERS)."""
    confidence = specs.get("_field_confidence")
    if not isinstance(confidence, dict):
        return set()
    return {field for field, marker in confidence.items() if marker in MODEL_KNOWLEDGE_MARKERS}


def real_spec_rows(specs0: Any, specs1: Any) -> int:
    """Fields both products populate with a real value, excluding private keys, NA tokens on
    either side and fields either side marks as model knowledge (a tier-3 synthesis or
    training data; R-A4: not evidence)."""
    if not isinstance(specs0, dict) or not isinstance(specs1, dict):
        return 0
    tier3 = _tier3_fields(specs0) | _tier3_fields(specs1)
    count = 0
    for field, value in specs0.items():
        if not isinstance(field, str) or field.startswith("_") or field not in specs1:
            continue
        if field in tier3 or _is_na(value) or _is_na(specs1.get(field)):
            continue
        count += 1
    return count


def real_spec_rows_one_side(specs: Any) -> int:
    if not isinstance(specs, dict):
        return 0
    return sum(
        1 for field, value in specs.items()
        if isinstance(field, str) and not field.startswith("_") and not _is_na(value)
    )


def literal_spec_items(specs_comparison: Any) -> int:
    """R0's literal fact (c): the GPT prose lists; the display rows are deliberately not counted."""
    if not isinstance(specs_comparison, dict):
        return 0
    total = 0
    for key in ("product_0_advantages", "product_1_advantages", "similar"):
        items = specs_comparison.get(key)
        if isinstance(items, list):
            total += len(items)
    return total


def dim_is_discriminating(dim: Any, missing_data_keys: Any, *, strict: bool) -> bool:
    """Both scores numeric, neither caption nor confidence flagged, margin >= DIM_MARGIN; the
    strict reading also refuses a low confidence, the MISSING_SCORE sentinel on either side and
    a key the scoring listed as missing data."""
    if not isinstance(dim, dict):
        return False
    a, b = dim.get("score_a"), dim.get("score_b")
    if not _num(a) or not _num(b):
        return False
    if dim.get("caption_key") in DIM_FLAGGED or dim.get("confidence") in DIM_FLAGGED:
        return False
    if abs(a - b) < DIM_MARGIN:
        return False
    if strict:
        if dim.get("confidence") == "low":
            return False
        if a == SENTINEL_SCORE or b == SENTINEL_SCORE:
            return False
        key = dim.get("key")
        keys = set(missing_data_keys or ())
        if isinstance(key, str) and (key in keys or key + "_score" in keys):
            return False
    return True


# ----------------------------------------------------------------- body readers (B1-R7)

def _raw_products(result: Dict[str, Any]) -> List[Any]:
    """The RAW products alias first (post-chokepoint dicts, present on every body and stored
    row); the overview mirror only when the alias is absent."""
    products = result.get("products")
    if isinstance(products, list) and len(products) >= 2:
        return products
    overview = result.get("overview")
    products = overview.get("products") if isinstance(overview, dict) else None
    return products if isinstance(products, list) else []


def _overview_products(result: Dict[str, Any]) -> List[Any]:
    overview = result.get("overview")
    products = overview.get("products") if isinstance(overview, dict) else None
    if isinstance(products, list) and len(products) >= 2:
        return products
    products = result.get("products")
    return products if isinstance(products, list) else []


def _product_at(products: List[Any], i: int) -> Dict[str, Any]:
    return products[i] if len(products) > i and isinstance(products[i], dict) else {}


def _specs_of(result: Dict[str, Any], i: int) -> Any:
    specs_block = result.get("specs")
    if isinstance(specs_block, dict):
        per_product = specs_block.get("products")
        if isinstance(per_product, list) and len(per_product) > i and isinstance(per_product[i], dict):
            return per_product[i].get("specs")
    return _product_at(_raw_products(result), i).get("specs")


def _dims(result: Dict[str, Any]) -> List[Any]:
    scoring_v2 = result.get("scoring_v2")
    if not isinstance(scoring_v2, dict):
        return []
    dims = scoring_v2.get("dimensions")
    return dims if isinstance(dims, list) else []


def _missing_keys(result: Dict[str, Any]) -> set:
    scoring = result.get("scoring")
    scores = scoring.get("scores") if isinstance(scoring, dict) else None
    keys: set = set()
    if isinstance(scores, dict):
        for entry in scores.values():
            missing = entry.get("missing_data") if isinstance(entry, dict) else None
            if isinstance(missing, list):
                keys.update(k for k in missing if isinstance(k, str))
    return keys


def _prose(result: Dict[str, Any]) -> Any:
    comparison = result.get("comparison")
    if isinstance(comparison, dict) and isinstance(comparison.get("specs_comparison"), dict):
        return comparison.get("specs_comparison")
    specs = result.get("specs")
    return specs.get("specs_comparison") if isinstance(specs, dict) else None


_NO_FACTS = {"price": False, "ratings": False, "specs": False, "dims": False}


def _facts(result: Any, *, strict: bool, url_mode: bool = False) -> Dict[str, bool]:
    if not isinstance(result, dict):
        return dict(_NO_FACTS)
    products = _raw_products(result)
    if len(products) < 2:
        return dict(_NO_FACTS)
    p0, p1 = _product_at(products, 0), _product_at(products, 1)
    if url_mode:
        # B1b: the URL reading (S81-20) in BOTH the strict and the literal reading.
        price = _url_price(p0) and _url_price(p1)
        ratings = _url_rating(p0) and _url_rating(p1)
    else:
        price_fact = price_is_showable if strict else price_is_present_literal
        price = price_fact(p0.get("price")) and price_fact(p1.get("price"))
        ratings = rating_is_real(p0) and rating_is_real(p1)
    if strict:
        specs = real_spec_rows(_specs_of(result, 0), _specs_of(result, 1)) >= 1
    else:
        specs = literal_spec_items(_prose(result)) >= 1
    missing = _missing_keys(result)
    dims = any(dim_is_discriminating(d, missing, strict=strict) for d in _dims(result))
    return {"price": bool(price), "ratings": bool(ratings), "specs": bool(specs), "dims": bool(dims)}


def evidence_facts(result: Any) -> Dict[str, bool]:
    """The AUDITABLE facts (R0-5 ruling): data_coverage counts these."""
    return _facts(result, strict=True)


def evidence_facts_literal(result: Any) -> Dict[str, bool]:
    """The LITERAL facts (R0's tally): data_coverage_literal counts these."""
    return _facts(result, strict=False)


def evidence_coverage(result: Any) -> Tuple[int, int]:
    return (sum(evidence_facts(result).values()), sum(evidence_facts_literal(result).values()))


# ----------------------------------------------------------------- section status (MYEZ-022)

def _reviews_present(product: Dict[str, Any]) -> bool:
    reviews = product.get("reviews")
    if isinstance(reviews, dict):
        summary = reviews.get("review_summary")
        if isinstance(summary, dict):
            consensus = summary.get("consensus")
            if isinstance(consensus, str) and consensus.strip():
                return True
        quotes = reviews.get("retailer_quotes")
        if isinstance(quotes, list) and quotes:
            return True
    praise = product.get("review_praise")
    if isinstance(praise, str) and praise.strip():
        return True
    count = product.get("review_count")
    return rating_is_real(product) and isinstance(count, int) and not isinstance(count, bool) and count > 0


def _section_state(flags: Sequence[bool]) -> str:
    present = sum(1 for f in flags if f)
    if present and present == len(flags):
        return "available"
    return "partial" if present else "unavailable"


def section_status(result: Any) -> Dict[str, str]:
    """Per section: available (both products), partial (one), unavailable (none)."""
    if not isinstance(result, dict):
        return dict.fromkeys(SECTION_KEYS, "unavailable")
    raw, overview = _raw_products(result), _overview_products(result)
    specs_f, reviews_f, pros_cons_f, price_f = [], [], [], []
    for i in range(2):
        p, o = _product_at(raw, i), _product_at(overview, i)
        specs_f.append(real_spec_rows_one_side(_specs_of(result, i)) >= 1)
        reviews_f.append(_reviews_present(p) or _reviews_present(o))
        pros, cons = o.get("pros"), o.get("cons")
        pros_cons_f.append(bool(isinstance(pros, list) and pros) or bool(isinstance(cons, list) and cons))
        price_f.append(price_is_showable(p.get("price")) or price_is_showable(o.get("price")))
    return {
        "specs": _section_state(specs_f),
        "reviews": _section_state(reviews_f),
        "pros_cons": _section_state(pros_cons_f),
        "price": _section_state(price_f),
    }


# ----------------------------------------------------------------- the assessment (R-A4)

def identity_confidence(products: Sequence[Any], *, same: bool, coherent: bool,
                        vision_confidences: Any = None,
                        facts_per_product: Sequence[bool]) -> str:
    """unresolved: a placeholder; low: same identity, a category conflict or a low vision
    read; medium: an empty brand, a medium vision read or a product with no corroboration;
    else high. vision_confidences is None until B3 threads it (L1)."""
    if len(products) < 2 or any(product_is_placeholder(p) for p in products):
        return "unresolved"
    vision = []
    if isinstance(vision_confidences, (list, tuple)):
        vision = [str(v).strip().casefold() for v in vision_confidences if v is not None]
    if same or not coherent or "low" in vision:
        return "low"
    if any(norm(p.get("brand")) == "" for p in products) or "medium" in vision \
            or not all(bool(f) for f in facts_per_product):
        return "medium"
    return "high"


def _corroborated(result: Dict[str, Any], i: int, url_mode: bool = False) -> bool:
    """One real signal on this product's own side: a showable price, a real rating or a real spec
    (under url_mode the price / rating through the URL readers, B1b)."""
    product = _product_at(_raw_products(result), i)
    if url_mode:
        return _url_price(product) or _url_rating(product) \
            or real_spec_rows_one_side(_specs_of(result, i)) >= 1
    return price_is_showable(product.get("price")) or rating_is_real(product) \
        or real_spec_rows_one_side(_specs_of(result, i)) >= 1


def _category_used(result: Dict[str, Any]) -> Optional[str]:
    for key in ("category_used", "category"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().casefold()
    return None


def assess_result(result: Any, *, product_categories: Any = None,
                  vision_confidences: Any = None, url_mode: bool = False) -> Dict[str, Any]:
    """The honest status of a built body: every applicable reason in REASONS order, the status
    of the first one (supported_result when none applies = R-A4's minimum evidence to crown:
    coverage >= 1, identity not unresolved, not the same identity, no category conflict).
    url_mode (B1b, default False): the price / rating facts and the per-side corroboration
    read the URL evidence; everything else is unchanged."""
    body = result if isinstance(result, dict) else {}
    products = _raw_products(body)
    p0 = products[0] if len(products) > 0 else None
    p1 = products[1] if len(products) > 1 else None
    reasons: List[str] = []
    if body.get("success") is not True:
        reasons.append("not_success")
    unknown = sum(1 for p in (p0, p1) if product_is_placeholder(p))
    if unknown:
        reasons.append("placeholder_identity")
    same = same_identity(p0, p1)
    if same:
        reasons.append("same_identity")
    category = _category_used(body)
    if category is not None and category not in CANONICAL_CATEGORIES:
        reasons.append("unsupported_category")
    coherent = identity_coherence(product_categories, category)
    if not coherent:
        reasons.append("category_conflict")
    facts = _facts(body, strict=True, url_mode=url_mode)
    facts_literal = _facts(body, strict=False, url_mode=url_mode)
    coverage, coverage_literal = sum(facts.values()), sum(facts_literal.values())
    if coverage == 0:
        reasons.append("no_evidence")
    status = _STATUS_BY_REASON[reasons[0]] if reasons else STATUS_SUPPORTED
    confidence = identity_confidence(
        [p0, p1], same=same, coherent=coherent, vision_confidences=vision_confidences,
        facts_per_product=[_corroborated(body, 0, url_mode), _corroborated(body, 1, url_mode)])
    return {
        "status": status,
        "reasons": reasons,
        "identity_confidence": confidence,
        "data_coverage": coverage,
        "data_coverage_literal": coverage_literal,
        "section_status": section_status(body),
        "unknown_product_count": unknown,
        "same_identity": same,
        "coherent": coherent,
        "facts": facts,
        "facts_literal": facts_literal,
    }


# ----------------------------------------------------------------- telemetry (2.5, B1-R10)

def stamped_product_categories(result: Any) -> Optional[List[Optional[str]]]:
    """F1-1: the ONE reader of the stamped `metadata.product_categories` (a two-element list,
    each element a str or None; anything else is None), so the telemetry assessment equals the
    stamp the builder wrote with the same categories. An unstamped body reads None (today)."""
    metadata = result.get("metadata") if isinstance(result, dict) else None
    cats = metadata.get("product_categories") if isinstance(metadata, dict) else None
    if not isinstance(cats, list) or len(cats) != 2:
        return None
    return [c if isinstance(c, str) else None for c in cats]


def _image_present(result: Dict[str, Any], i: int) -> bool:
    for products in (_overview_products(result), _raw_products(result)):
        url = _product_at(products, i).get("image_url")
        if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
            return True
    return False


def _bucket(ms: Any, step: int) -> Optional[str]:
    """The bucket's lower edge in ms as a digit string (GA-2); None when unknown (F1-5: a
    non-finite, bool or str wall is unknown)."""
    if not _finite(ms) or ms < 0:
        return None
    return str((int(ms) // step) * step)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def telemetry_tags(result: Any, input_type: str, *, assessment: Any = None,
                   vision_ms: Any = None, compare_ms: Any = None) -> Dict[str, str]:
    """The PII-free tag set: enums, small ints and bucketed walls only, every value a str
    matching ^[a-z0-9_,]+$; a wall tag is omitted when unknown, never 'None'. Without an
    assessment the body is assessed with its stamped product_categories (F1-1); the
    partial_stage tag carries a PARTIAL_STAGES value only, an unknown value omits it (F1-6)."""
    body = result if isinstance(result, dict) else {}
    a = assessment if isinstance(assessment, dict) else assess_result(
        body, product_categories=stamped_product_categories(body))
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    raw = _raw_products(body)
    partial_stage = metadata.get("partial_stage")
    stage_tag: Optional[str] = "none"
    if metadata.get("partial") is True and isinstance(partial_stage, str):
        stage_tag = partial_stage if partial_stage in PARTIAL_STAGES else None
    tags: Dict[str, str] = {
        "input_type": str(input_type),
        "result_status": str(a.get("status")),
        "identity_confidence": str(a.get("identity_confidence")),
        "reasons": ",".join(a.get("reasons") or []) or "none",
        "unknown_product_count": str(int(a.get("unknown_product_count") or 0)),
        "winner_emitted": _flag(a.get("status") == STATUS_SUPPORTED),
        "image_present_a": _flag(_image_present(body, 0)),
        "image_present_b": _flag(_image_present(body, 1)),
        "price_showable_a": _flag(price_is_showable(_product_at(raw, 0).get("price"))),
        "price_showable_b": _flag(price_is_showable(_product_at(raw, 1).get("price"))),
        "data_coverage": str(int(a.get("data_coverage") or 0)),
        "data_coverage_literal": str(int(a.get("data_coverage_literal") or 0)),
    }
    if stage_tag is not None:
        tags["partial_stage"] = stage_tag
    vision_bucket = _bucket(vision_ms, VISION_BUCKET_MS)
    compare_bucket = _bucket(compare_ms, COMPARE_BUCKET_MS)
    if vision_bucket is not None:
        tags["vision_ms"] = vision_bucket
    if compare_bucket is not None:
        tags["compare_ms"] = compare_bucket
    return tags


def telemetry_extras(*, vision_ms: Any = None, compare_ms: Any = None) -> Dict[str, int]:
    """The raw walls as ints (B1-R10 extras); an unknown wall (F1-5: non-finite, bool, str,
    negative) is omitted."""
    extras: Dict[str, int] = {}
    if _finite(vision_ms) and vision_ms >= 0:
        extras["vision_ms"] = int(vision_ms)
    if _finite(compare_ms) and compare_ms >= 0:
        extras["compare_ms"] = int(compare_ms)
    return extras


# ----------------------------------------------------------------- camera timings (B1-TIMINGS)

def stamp_camera_stage_timings(result: Any, *, vision_ms: Any, vision_moderation_ms: Any,
                               compare_ms: Any) -> bool:
    """Flag first; then ONLY into an EXISTING metadata.stage_timings_ms dict, as ints; a None
    (F1-5: or a non-finite, bool or str) wall is skipped. Never creates metadata or the dict
    (R0-6: production runs DEBUG_STAGE_TIMINGS=true, so a presence-only rule would move
    production bytes at merge)."""
    if not result_status_metadata_enabled():
        return False
    if not isinstance(result, dict):
        return False
    metadata = result.get("metadata")
    if not isinstance(metadata, dict):
        return False
    timings = metadata.get("stage_timings_ms")
    if not isinstance(timings, dict):
        return False
    wrote = False
    for key, value in (("vision_ms", vision_ms), ("vision_moderation_ms", vision_moderation_ms),
                       ("compare_ms", compare_ms)):
        if _finite(value):
            timings[key] = int(value)
            wrote = True
    return wrote


# ----------------------------------------------------------------- the gate (S81-20, B2)
# ENABLE_RESULT_GATE (default OFF, read per call): the route exits refuse a body the
# assessment above does not support, as a non-delivery (R-A3). Pure, total, ASCII; the
# decision functions read no flag; result_gate_refusal reads it FIRST.
GATE_REASONS = ("placeholder_identity", "same_identity", "category_conflict", "no_evidence")
CAMERA_GATE_REASONS = ("placeholder_identity", "low_confidence", "same_identity",
                       "category_conflict")
GATE_CODE = "INSUFFICIENT_DATA"
# Byte-equal to the orchestrator's H6 sentence (the em dash built from its code point).
GATE_REFUSAL_MESSAGE = "Comparison data was incomplete " + chr(0x2014) + " choose different products."
CAMERA_GATE_MESSAGE = "Photograph each product in its own photo so we can tell them apart."
GATE_LOG_PREFIX = "result_gate:"
# assess_result reason -> gate reason; not_success never maps.
_GATE_REASON_BY_ASSESS = {
    "placeholder_identity": "placeholder_identity",
    "same_identity": "same_identity",
    "unsupported_category": "category_conflict",
    "category_conflict": "category_conflict",
    "no_evidence": "no_evidence",
}
# R-S20-1 / R-S20-36: a JSON-LD price or rating string, ASCII digits only.
_URL_NUMBER_RE = re.compile(r"^\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^\d+(?:\.\d+)?$", re.ASCII)


def result_gate_enabled() -> bool:
    """ENABLE_RESULT_GATE, default OFF, read per call (the house idiom)."""
    return os.getenv("ENABLE_RESULT_GATE", "false").strip().lower() in _TRUTHY


def gate_reason(result: Any, *, product_categories: Any = None) -> Optional[str]:
    """The first assess_result reason that maps to a gate reason. None on a supported body
    and on anything that is not a success:True dict (a success body with no products maps
    to placeholder_identity through the assessment, GC-8). No flag read."""
    if not isinstance(result, dict) or result.get("success") is not True:
        return None
    assessment = assess_result(result, product_categories=product_categories)
    reasons = assessment.get("reasons") if isinstance(assessment, dict) else None
    for reason in reasons or ():
        mapped = _GATE_REASON_BY_ASSESS.get(reason) if isinstance(reason, str) else None
        if mapped is not None:
            return mapped
    return None


def _url_number(value: Any) -> Optional[float]:
    """A finite number from an int / float (never bool) or an ASCII numeric string."""
    if _num(value):
        return float(value) if _finite(value) else None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not _URL_NUMBER_RE.match(text):
        return None
    try:
        out = float(text.replace(",", ""))
    except (TypeError, ValueError, OverflowError):
        return None
    return out if _finite(out) else None


def _url_price(product: Dict[str, Any]) -> bool:
    price = product.get("price")
    if not isinstance(price, dict):
        return False
    if price.get("unavailable") is True or price.get("estimated") is True:
        return False
    amount = _url_number(price.get("amount"))
    return amount is not None and amount > 0


def _url_rating(product: Dict[str, Any]) -> bool:
    reviews = product.get("reviews")
    if isinstance(reviews, dict):
        value = _url_number(reviews.get("rating"))
        if value is not None and 0 < value <= 5:
            return True
    if rating_is_real(product):
        value = _url_number(product.get("rating"))
        return value is not None and 0 < value <= 5
    return False


def url_gate_reason(result: Any) -> Optional[str]:
    """The URL reading (R-S20-1 / R-S20-3): placeholder, then same identity, then the
    JSON-LD aware evidence count; never a category check. None under two products. No
    flag read."""
    if not isinstance(result, dict) or result.get("success") is not True:
        return None
    products = result.get("products")
    if not isinstance(products, list) or len(products) < 2:
        return None
    p0, p1 = products[0], products[1]
    if not isinstance(p0, dict) or not isinstance(p1, dict):
        return None
    if product_is_placeholder(p0) or product_is_placeholder(p1):
        return "placeholder_identity"
    if same_identity(p0, p1):
        return "same_identity"
    coverage = (int(_url_price(p0) and _url_price(p1))
                + int(_url_rating(p0) and _url_rating(p1))
                + int(real_spec_rows(p0.get("specs"), p1.get("specs")) >= 1))
    if coverage == 0:
        return "no_evidence"
    return None


def _camera_view(product: Any, identity: Any) -> Optional[Dict[str, Any]]:
    """The identity view of one camera side: the pre-enrichment (brand, name) when given,
    never the distinguishing features (R-S20-4); the size axis rides along."""
    if not isinstance(product, dict):
        return None
    if isinstance(identity, (list, tuple)) and len(identity) == 2:
        brand, name = identity[0], identity[1]
    else:
        brand, name = product.get("brand"), product.get("name")
    return {"brand": brand, "name": name, "size_or_count": product.get("size_or_count")}


def _camera_low(product: Any) -> bool:
    """A V2 product (the _is_product marker, R-S20-25) whose confidence reads low."""
    if not isinstance(product, dict) or product.get("_is_product") is not True:
        return False
    confidence = product.get("confidence")
    return isinstance(confidence, str) and confidence.strip().casefold() == "low"


def camera_gate_categories(p0: Any, p1: Any) -> List[Optional[str]]:
    """The camera category pair (R-S20-39): the V2 _category of an _is_product dict when it
    is one of the nine canonical keys, else None, so a V1 pair never carries a conflict."""
    out: List[Optional[str]] = []
    for product in (p0, p1):
        category = None
        if isinstance(product, dict) and product.get("_is_product") is True:
            value = product.get("_category")
            if isinstance(value, str) and value in CANONICAL_CATEGORIES:
                category = value
        out.append(category)
    return out


def camera_gate_reason(p0: Any, p1: Any, *, categories: Any = None,
                       identities: Any = None) -> Optional[str]:
    """The camera pre-compare reading (R-S20-2 / -4 / -5 / -39), on the pair the route
    would compare. No flag read."""
    ids: Tuple[Any, Any] = (None, None)
    if isinstance(identities, (list, tuple)) and len(identities) == 2:
        ids = (identities[0], identities[1])
    view0, view1 = _camera_view(p0, ids[0]), _camera_view(p1, ids[1])
    if (view0 is None or view1 is None
            or product_is_placeholder(view0) or product_is_placeholder(view1)):
        return "placeholder_identity"
    if _camera_low(p0) or _camera_low(p1):
        return "low_confidence"
    if same_identity(view0, view1):
        return "same_identity"
    if not identity_coherence(categories):
        return "category_conflict"
    return None


def _non_negative(value: Any) -> float:
    return value if _finite(value) and value >= 0 else 0.0


def gate_refusal_body(result: Any, reason: str) -> Dict[str, Any]:
    """The refusal in the H6 key order, the additive reason last."""
    metadata = result.get("metadata") if isinstance(result, dict) else None
    metadata = metadata if isinstance(metadata, dict) else {}
    calls = metadata.get("api_calls")
    if not (isinstance(calls, int) and not isinstance(calls, bool) and calls >= 0):
        calls = 0
    return {
        "success": False,
        "error": GATE_REFUSAL_MESSAGE,
        "code": GATE_CODE,
        "elapsed_seconds": _non_negative(metadata.get("elapsed_seconds")),
        "total_cost": _non_negative(metadata.get("total_cost")),
        "api_calls": calls,
        "reason": reason,
    }


def result_gate_refusal(result: Any, *, url_mode: bool = False) -> Optional[Dict[str, Any]]:
    """The flag FIRST; then the refusal body of a success:True result the gate does not
    support, else None. A raising reading delivers as OFF."""
    if not result_gate_enabled():
        return None
    if not isinstance(result, dict) or result.get("success") is not True:
        return None
    try:
        if url_mode:
            reason = url_gate_reason(result)
        else:
            reason = gate_reason(result, product_categories=stamped_product_categories(result))
    except Exception:  # noqa: BLE001 -- deliver as OFF
        return None
    if reason is None:
        return None
    return gate_refusal_body(result, reason)


def gate_log_message(reason: Any) -> str:
    """The search_logs error_message of a refusal: a closed set, never a value."""
    for known in GATE_REASONS + CAMERA_GATE_REASONS:
        if isinstance(reason, str) and reason == known:
            return GATE_LOG_PREFIX + reason
    return GATE_LOG_PREFIX + "unknown"
