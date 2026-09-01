"""Fact Check Service — all fact-checking functions extracted from structured_comparison_service.

Zero-cost cross-validation: spec citations, shopping cross-check, review sentiment, price deviation.
"""
import os
import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def factcheck_currency_normalization_enabled() -> bool:
    """True iff ``verify_price`` normalizes every shopping row into the final
    price's own currency BEFORE taking the median (issue #106, default OFF).

    Without it the price cross-check is currency-blind: it strips shopping
    price strings to bare numerals and compares them to the final BHD amount,
    so a raw AED/USD amount stamped BHD passes at ~0% deviation while the
    CORRECT conversion of the same rows is flagged unverified — the verdict is
    systematically inverted, not noisy. Read PER CALL from os.getenv (the
    price_service.shopping_strict_currency_enabled idiom) so Railway can flip
    it without a restart; default OFF is byte-identical to f2481b9.
    """
    return os.getenv("ENABLE_FACTCHECK_CURRENCY_NORMALIZATION", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


#: A shopping price string that is ONLY digits/separators/whitespace carries no
#: currency signal at all — the legacy assumption (same currency as the final
#: price) is the only available reading, exactly like a numeric row. Anything
#: else that detect_currency cannot resolve (junk letters, an unknown glyph) is
#: an UNRESOLVED basis and must be dropped from the median, never assumed.
_PURE_NUMERAL_RE = re.compile(r"[\d.,\s]+\Z")

# Fields where numeric values must match exactly during citation verification
NUMERIC_SPEC_FIELDS = {
    "ram", "storage", "battery", "weight", "display", "count", "dosage",
    "nutrition_calories", "nutrition_protein", "nutrition_fat", "nutrition_carbs",
}


def verify_spec_citations(specs: Dict, search_snippets: List[str]) -> Dict[str, str]:
    """Verify GPT spec citations against actual search snippets.

    Returns dict mapping spec_field -> confidence:
      'verified': citation matches snippet text
      'likely': citation provided but can't fully cross-check
      'unverified': no citation or citation doesn't match
    """
    confidence = {}
    for key, value in specs.items():
        if key.endswith("_source") or key.startswith("_") or key in ("brand", "model", "variant", "category"):
            continue
        source_key = f"{key}_source"
        source = specs.get(source_key)

        if not source or source == "training":
            confidence[key] = "unverified"
        elif source.startswith("snippet_"):
            try:
                idx = int(source.split("_")[1]) - 1
                if 0 <= idx < len(search_snippets):
                    snippet_text = search_snippets[idx].lower()
                    value_str = str(value).lower()

                    spec_numbers = re.findall(r'\d+', value_str)

                    if key in NUMERIC_SPEC_FIELDS and spec_numbers:
                        sig_numbers = [n for n in spec_numbers if len(n) >= 2]
                        if sig_numbers:
                            matches = sum(1 for n in sig_numbers if n in snippet_text)
                            confidence[key] = "verified" if matches == len(sig_numbers) else "likely"
                        else:
                            terms = [t for t in value_str.split() if len(t) > 2]
                            if not terms:
                                confidence[key] = "likely"
                            else:
                                matches = sum(1 for t in terms if t in snippet_text)
                                confidence[key] = "verified" if matches >= len(terms) * 0.5 else "likely"
                    else:
                        terms = [t for t in value_str.split() if len(t) > 2]
                        if not terms:
                            confidence[key] = "likely"
                        else:
                            matches = sum(1 for t in terms if t in snippet_text)
                            confidence[key] = "verified" if matches >= len(terms) * 0.5 else "likely"
                else:
                    confidence[key] = "unverified"
            except (ValueError, IndexError):
                confidence[key] = "unverified"
        else:
            confidence[key] = "unverified"

    return confidence


def cross_validate_specs_with_shopping(specs: Dict, shopping_items: List[Dict]) -> Dict[str, str]:
    """Cross-check spec values against Serper Shopping product titles/descriptions.

    Upgrades 'likely' to 'verified' if shopping data confirms.
    """
    if not shopping_items:
        return {}

    shopping_text = " ".join(
        f"{item.get('title', '')} {item.get('description', '')}"
        for item in shopping_items
    ).lower()

    flags = {}
    checkable = ["storage", "ram", "display", "processor", "count", "dosage", "form"]
    for key in checkable:
        value = specs.get(key)
        if not value or value == "N/A":
            continue
        value_str = str(value).lower()
        spec_numbers = [n for n in re.findall(r'\d+', value_str) if len(n) >= 2]
        if spec_numbers:
            all_found = all(n in shopping_text for n in spec_numbers)
            if all_found:
                flags[key] = "verified"
        else:
            terms = [t for t in value_str.split() if len(t) > 2]
            found = sum(1 for t in terms if t in shopping_text)
            if terms and found >= len(terms) * 0.5:
                flags[key] = "verified"

    return flags


def verify_review_sentiment(reviews: Dict, source_ratings: List[Dict]) -> Dict:
    """Cross-check GPT review sentiment against real Serper ratings."""
    gpt_rating = reviews.get("average_rating")
    if not source_ratings or gpt_rating is None:
        return {"sentiment_consistent": None, "gpt_rating": gpt_rating, "serper_avg_rating": None, "deviation": None}

    total_weight = 0
    weighted_sum = 0
    for sr in source_ratings:
        rating = sr.get("rating")
        count = sr.get("review_count", 1) or 1
        if rating and isinstance(rating, (int, float)):
            weighted_sum += rating * count
            total_weight += count

    if total_weight == 0:
        return {"sentiment_consistent": None, "gpt_rating": gpt_rating, "serper_avg_rating": None, "deviation": None}

    serper_avg = round(weighted_sum / total_weight, 2)
    deviation = abs(gpt_rating - serper_avg)
    consistent = deviation <= 0.8

    return {
        "sentiment_consistent": consistent,
        "gpt_rating": gpt_rating,
        "serper_avg_rating": serper_avg,
        "deviation": round(deviation, 2),
    }


def verify_price(price: Dict, shopping_items: List[Dict]) -> Dict:
    """Cross-check final price against Serper Shopping prices."""
    if not price or not shopping_items:
        return {
            "price_verified": price is not None and not (price or {}).get("estimated", False),
            "deviation_pct": None,
            "source_count": 0,
        }

    final_amount = price.get("amount")
    if not final_amount:
        return {"price_verified": False, "deviation_pct": None, "source_count": 0}

    # Issue #106 — normalize every shopping row into the final price's own
    # currency before the median (flag ON). Flag OFF: the legacy currency-blind
    # path below runs untouched, byte-identical to f2481b9.
    if factcheck_currency_normalization_enabled():
        return _verify_price_currency_normalized(price, final_amount, shopping_items)

    shopping_prices = []
    for item in shopping_items:
        p = item.get("price")
        if isinstance(p, (int, float)) and p > 0:
            shopping_prices.append(p)
        elif isinstance(p, str):
            nums = re.findall(r'[\d.]+', p.replace(',', ''))
            if nums:
                try:
                    shopping_prices.append(float(nums[0]))
                except ValueError:
                    pass

    if not shopping_prices:
        return {
            "price_verified": not price.get("estimated", False),
            "deviation_pct": None,
            "source_count": 0,
        }

    median = sorted(shopping_prices)[len(shopping_prices) // 2]
    deviation_pct = abs(final_amount - median) / median * 100 if median > 0 else None

    return {
        "price_verified": deviation_pct is not None and deviation_pct <= 30 and not price.get("estimated", False),
        "deviation_pct": round(deviation_pct, 1) if deviation_pct is not None else None,
        "source_count": len(shopping_prices),
    }


def _verify_price_currency_normalized(
    price: Dict, final_amount: float, shopping_items: List[Dict]
) -> Dict:
    """Issue #106 flag-ON body — currency-aware price cross-check.

    Mirrors ``price_service.extract_price_from_shopping``'s row handling:
    ``detect_currency`` -> ``parse_price_string(..., display_text=True)`` ->
    ``_convert_to_bhd`` when the detected currency differs from the target
    (with the same target!=BHD re-basing). Contract:

      * numeric ``item["price"]`` — no string to inspect, treated as already
        in the target currency (as today);
      * string row with a resolvable currency — parsed under that currency and
        converted into the target before the median;
      * string row with digits but NO resolvable currency signal beyond a bare
        numeral — DROPPED from the median (counted as unresolved), never
        assumed to be the target currency;
      * a resolved code the rate table cannot convert (``_convert_to_bhd``
        returns the amount UNCHANGED for an unresolvable currency — that
        return contract is deliberate, so we probe the 1.0 rate instead of
        trusting the return) — also dropped as unresolved;
      * zero usable rows but >=1 unresolved row — NO verdict:
        ``price_verified: None`` (cross-cutting rule: a check that cannot be
        computed degrades to ABSENT, never to a default that reads as
        verified);
      * zero rows of any kind — the existing no-usable-rows shape.

    Lazy import on purpose: fact_check_service is deliberately dependency-light
    and a module-level import of price_service would pull the whole pricing
    stack into every importer.
    """
    from app.services.price_service import (
        detect_currency, parse_price_string, _convert_to_bhd,
    )

    target = price.get("currency") or "BHD"
    usable: List[float] = []
    unresolved = 0

    for item in shopping_items:
        p = item.get("price")
        if isinstance(p, (int, float)) and p > 0:
            usable.append(float(p))
            continue
        if not isinstance(p, str):
            continue
        raw = p.strip()
        if not raw or not re.search(r"\d", raw):
            continue  # no numeral at all — contributes nothing (as today)
        detected = detect_currency(raw)
        if detected is None and not _PURE_NUMERAL_RE.fullmatch(raw):
            # digits + junk the currency detector cannot resolve: basis unknown
            unresolved += 1
            continue
        amount = parse_price_string(raw, detected, display_text=True)
        if amount is None or amount <= 0:
            continue
        if detected and detected != target:
            if detected.upper() != "BHD" and _convert_to_bhd(1.0, detected) == 1.0:
                # detect_currency resolved a code the effective rate table
                # cannot convert — never treat the unchanged return as a
                # conversion (documented _convert_to_bhd contract).
                unresolved += 1
                continue
            amount = _convert_to_bhd(amount, detected)
            if target != "BHD":
                bhd_rate = _convert_to_bhd(1.0, target)
                if bhd_rate > 0:
                    amount = amount / bhd_rate
        usable.append(amount)

    if not usable:
        if unresolved > 0:
            # Rows exist but none has a resolvable currency basis: no verdict.
            return {
                "price_verified": None,
                "deviation_pct": None,
                "source_count": unresolved,
            }
        return {
            "price_verified": not price.get("estimated", False),
            "deviation_pct": None,
            "source_count": 0,
        }

    # Same upper-median indexing as the legacy path so a single-currency corpus
    # produces the identical number flag-ON and flag-OFF.
    median = sorted(usable)[len(usable) // 2]
    deviation_pct = abs(final_amount - median) / median * 100 if median > 0 else None

    return {
        "price_verified": deviation_pct is not None and deviation_pct <= 30 and not price.get("estimated", False),
        "deviation_pct": round(deviation_pct, 1) if deviation_pct is not None else None,
        "source_count": len(usable),
    }


def build_fact_check(product: Dict) -> Dict:
    """Assemble fact_check object from per-field verification results.

    Pops internal _spec_confidence, _review_verification, _price_verification
    keys from the product dict and returns a clean fact_check summary.
    """
    spec_confidence = product.pop("_spec_confidence", {})
    review_verification = product.pop("_review_verification", {})
    price_verification = product.pop("_price_verification", {})

    specs_verified = sum(1 for v in spec_confidence.values() if v == "verified")
    specs_likely = sum(1 for v in spec_confidence.values() if v == "likely")
    specs_flagged = sum(1 for v in spec_confidence.values() if v == "flagged")
    specs_unverified = sum(1 for v in spec_confidence.values() if v == "unverified")

    price_verified = price_verification.get("price_verified", False)
    sentiment_consistent = review_verification.get("sentiment_consistent")

    # Bundle E § Decision 7: overall_confidence pill dropped; per-dimension
    # confidence rendered via bar opacity instead. Use is_data_freshness_shaky
    # for the rare "all-bad-signals" inline notice.
    return {
        "specs_verified": specs_verified,
        "specs_likely": specs_likely,
        "specs_flagged": specs_flagged,
        "specs_unverified": specs_unverified,
        "price_verified": price_verified,
        "price_deviation_pct": price_verification.get("deviation_pct"),
        "review_sentiment_consistent": sentiment_consistent,
        "review_rating_deviation": review_verification.get("deviation"),
    }


def is_data_freshness_shaky(fact_check_results: list[Dict]) -> bool:
    """Bundle E § Decision 7 — return True only when ≥2 of these
    BOTH-product conditions hold:
      (i)   both price_verified == False
      (ii)  both review_sentiment_consistent is None
      (iii) both specs_verified + specs_likely == 0
    Otherwise False (default — no apologetic banner). Defensive on empty
    or single-item input."""
    if len(fact_check_results) < 2:
        return False
    a, b = fact_check_results[0], fact_check_results[1]
    conditions = 0
    if a.get("price_verified") is False and b.get("price_verified") is False:
        conditions += 1
    if a.get("review_sentiment_consistent") is None and b.get("review_sentiment_consistent") is None:
        conditions += 1
    a_specs = a.get("specs_verified", 0) + a.get("specs_likely", 0)
    b_specs = b.get("specs_verified", 0) + b.get("specs_likely", 0)
    if a_specs == 0 and b_specs == 0:
        conditions += 1
    return conditions >= 2
