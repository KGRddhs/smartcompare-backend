"""Fact Check Service — all fact-checking functions extracted from structured_comparison_service.

Zero-cost cross-validation: spec citations, shopping cross-check, review sentiment, price deviation.
"""
import os
import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Fields where numeric values must match exactly during citation verification
NUMERIC_SPEC_FIELDS = {
    "ram", "storage", "battery", "weight", "display", "count", "dosage",
    "nutrition_calories", "nutrition_protein", "nutrition_fat", "nutrition_carbs",
}


def citation_rubric_v2_enabled() -> bool:
    """True iff the unit-aware citation rubric with a reachable "flagged"
    outcome is active (issue #108, default OFF).

    The v1 rubric compares bare digit substrings, so a unit swap (128 TB vs a
    128 GB snippet) verifies and a contradiction (5000 mAh vs a 3582 mAh
    snippet) earns "likely" (weight 0.7) — while an honest "training" answer
    earns 0.3: the reliability dimension pays the model to invent a citation.
    v2 pairs each number with a bounded unit vocabulary, emits "flagged" on a
    same-unit contradiction, and demotes a numeric field citing a
    number-free snippet to "unverified". Read PER CALL from os.getenv (the
    price_service.exact_gate_enabled idiom) so a Railway flip needs no
    restart; flag OFF both rubric functions take the v1 code path unchanged.
    Dark because this is the first change that can make ``specs_flagged``
    non-zero (weight 0.0 in ScoringService._score_reliability) — it needs its
    own canary window and a specs_flagged rate to watch.
    """
    return os.getenv("ENABLE_CITATION_RUBRIC_V2", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


# Thousands separators stripped from BOTH sides before v2 number matching:
# ASCII comma and the Arabic thousands separator U+066C. '.' is kept as a
# decimal point.
_THOUSANDS_SEPARATORS_RE = re.compile("[,٬]")

# Bounded unit vocabulary for the v2 number+unit extractor. Base set copied
# from price_service._SPACED_UNIT_RE (gb|tb|ml|oz|mm|hz|mah|inch(es)?),
# extended with the units NUMERIC_SPEC_FIELDS actually carry (mb, kg, g, mg,
# mcg, iu, l, w, in, "). Longest alternatives first so 'inches' never matches
# as 'in'. Bounded on purpose: an open-ended letter capture would treat prose
# after a number ("128 different") as a unit and manufacture false "flagged"
# verdicts.
_CITATION_UNIT_VOCAB = (
    "inches", "inch", "mah", "mcg", "gb", "tb", "mb", "ml", "mm", "hz",
    "kg", "mg", "oz", "iu", "in", "g", "l", "w", '"',
)
_CITATION_NUM_UNIT_RE = re.compile(
    r"(?<![a-z0-9.])(\d+(?:\.\d+)?)[ \t]*("
    + "|".join(re.escape(u) for u in _CITATION_UNIT_VOCAB)
    + r")?(?![a-z0-9])"
)


def _extract_number_units(text: str) -> List[tuple]:
    """Extract (number, unit) pairs from lowercase separator-stripped text.

    The spaced and glued spellings are equal by construction ("128 GB" and
    "128GB" both yield ("128", "gb") — the [ \\t]* mirrors
    price_service._fold_spaced_units). A number followed by a word outside
    the vocabulary yields unit "" (a bare number). A number glued to unknown
    trailing letters ("16gbps") yields nothing.
    """
    return [
        (m.group(1), (m.group(2) or ""))
        for m in _CITATION_NUM_UNIT_RE.finditer(text)
    ]


def _grade_numeric_citation_v2(value_str: str, snippet_text: str) -> Optional[str]:
    """v2 verdict for a NUMERIC_SPEC_FIELDS value against its cited snippet.

    Both inputs must already be lowercased and separator-stripped. Returns:
      'verified'   — every significant cited (number, unit) pair matches the
                     snippet (same unit adjacent to the same number; bare
                     cited numbers match by substring as in v1);
      'flagged'    — a unit-bearing cited pair is unmatched while the snippet
                     carries a same-unit number of a DIFFERENT magnitude (the
                     snippet contradicts its own citation);
      'unverified' — otherwise: the snippet carries no comparable same-unit
                     number, so the citation is not evidence and must not
                     outscore an honest 'training' answer (both land on 0.3
                     in ScoringService._score_reliability);
      None         — no significant cited number (caller falls through to the
                     v1 term-overlap branch, mirroring the v1 sig-empty path).
    """
    cited = _extract_number_units(value_str)
    sig = [(n, u) for n, u in cited if len(n.replace(".", "")) >= 2]
    if not sig:
        return None

    snippet_pairs = _extract_number_units(snippet_text)

    def _matched(n: str, u: str) -> bool:
        if u:
            return any(sn == n and su == u for sn, su in snippet_pairs)
        return n in snippet_text

    if all(_matched(n, u) for n, u in sig):
        return "verified"
    for n, u in sig:
        if not u or _matched(n, u):
            continue
        if any(su == u and sn != n for sn, su in snippet_pairs):
            return "flagged"
    return "unverified"


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

                    rubric_v2 = citation_rubric_v2_enabled()
                    if rubric_v2:
                        # Issue #108 fix (d): separator spellings ("5,000" vs
                        # "5000") must match on BOTH sides; done once here so
                        # the term-overlap branches below benefit too.
                        snippet_text = _THOUSANDS_SEPARATORS_RE.sub("", snippet_text)
                        value_str = _THOUSANDS_SEPARATORS_RE.sub("", value_str)

                    spec_numbers = re.findall(r'\d+', value_str)

                    if key in NUMERIC_SPEC_FIELDS and spec_numbers:
                        v2_verdict = (
                            _grade_numeric_citation_v2(value_str, snippet_text)
                            if rubric_v2 else None
                        )
                        sig_numbers = [n for n in spec_numbers if len(n) >= 2]
                        if v2_verdict is not None:
                            confidence[key] = v2_verdict
                        elif sig_numbers and not rubric_v2:
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


def cross_validate_specs_with_shopping(
    specs: Dict, shopping_items: List[Dict], product_name: str = "",
) -> Dict[str, str]:
    """Cross-check spec values against Serper Shopping product titles/descriptions.

    Upgrades 'likely' to 'verified' if shopping data confirms.

    ``product_name`` (issue #108, optional so existing callers stay valid) is
    the product's own display name; with ENABLE_CITATION_RUBRIC_V2 on it feeds
    the identity fence that stops a digit belonging to the product's own
    name/brand/model ("iPhone 16") from verifying a spec value ("16 GB").
    Flag OFF the parameter is ignored entirely.
    """
    if not shopping_items:
        return {}

    rubric_v2 = citation_rubric_v2_enabled()

    shopping_text = " ".join(
        f"{item.get('title', '')} {item.get('description', '')}"
        for item in shopping_items
    ).lower()

    identity_numbers: set = set()
    shopping_pairs: set = set()
    if rubric_v2:
        shopping_text = _THOUSANDS_SEPARATORS_RE.sub("", shopping_text)
        # Unit-adjacent (number, unit) pairs actually present in the shopping
        # text — the only evidence strong enough to verify a digit that also
        # belongs to the product's own identity ("iPhone 16" vs "16GB RAM").
        shopping_pairs = {
            (n, u) for n, u in _extract_number_units(shopping_text) if u
        }
        identity_text = " ".join(
            str(t) for t in (product_name, specs.get("brand"), specs.get("model")) if t
        ).lower()
        identity_numbers = set(re.findall(r'\d+', identity_text))

    flags = {}
    checkable = ["storage", "ram", "display", "processor", "count", "dosage", "form"]
    for key in checkable:
        value = specs.get(key)
        if not value or value == "N/A":
            continue
        value_str = str(value).lower()
        if rubric_v2:
            value_str = _THOUSANDS_SEPARATORS_RE.sub("", value_str)
        spec_numbers = [n for n in re.findall(r'\d+', value_str) if len(n) >= 2]
        if spec_numbers:
            if rubric_v2:
                # Issue #108 fix (c): a candidate digit that is part of the
                # product's own name/brand/model tokens cannot verify on a
                # bare substring hit — it must appear unit-adjacent in the
                # shopping text with the SAME unit the spec value carries.
                value_units = dict(_extract_number_units(value_str))

                def _found(n: str) -> bool:
                    if n in identity_numbers:
                        u = value_units.get(n, "")
                        return bool(u) and (n, u) in shopping_pairs
                    return n in shopping_text

                all_found = all(_found(n) for n in spec_numbers)
            else:
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


def factcheck_currency_normalization_enabled() -> bool:
    """True iff verify_price converts shopping rows into the final price's own
    currency before taking the median (issue #106, default OFF).

    The currency-blind check VERIFIES the wrong-currency error class the W2
    currency wave exists to kill: a raw AED amount stamped BHD matches AED
    shopping numerals at 0.0% deviation (endorsed), while the correct BHD
    conversion of the same rows deviates ~89.8% (flagged). Read PER CALL from
    os.getenv (the response_builder._gpt_winner_lever_enabled idiom) so a
    Railway flip needs no restart; flag OFF the returned dict is byte-identical
    to the pre-#106 code for every input.
    """
    return os.getenv("ENABLE_FACTCHECK_CURRENCY_NORMALIZATION", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _normalized_shopping_prices(
    shopping_items: List[Dict], target_currency: str,
) -> tuple[List[float], int]:
    """Convert shopping-row prices into ``target_currency`` (issue #106).

    Returns ``(resolved_prices, unresolved_count)``:
      resolved_prices  — amounts expressed in the target currency: numeric rows
                         (no string to inspect — kept as-is, as today), bare
                         numeral strings (no currency residue — assumed target,
                         preserving today's behaviour for "1,299.99" rows), and
                         detected-currency strings converted via the fallback
                         rate table (the extract_price_from_shopping pattern,
                         price_service.py:9535-9550, mirrored row-for-row).
      unresolved_count — rows carrying a currency-like residue that neither
                         detect_currency nor the rate table can resolve. They
                         are DROPPED from the median rather than assumed to be
                         the target currency; the caller returns a None verdict
                         when only such rows survive.

    Imports are lazy on purpose: fact_check_service is dependency-light (re/
    logging/typing/os only) and a module-level price_service import would pull
    the whole pricing stack into every importer.
    """
    from app.services.price_service import (
        detect_currency, parse_price_string, _convert_to_bhd,
    )
    from app.services.exchange_rate_service import effective_fallback_rates

    resolved: List[float] = []
    unresolved = 0
    for item in shopping_items:
        p = item.get("price")
        if isinstance(p, (int, float)) and p > 0:
            resolved.append(float(p))
            continue
        if not isinstance(p, str):
            continue
        detected = detect_currency(p)
        amount = parse_price_string(p, detected, display_text=True)
        if amount is None or amount <= 0:
            continue
        if detected is None:
            # No detectable currency. A bare numeral ("1,299.99") is assumed
            # target-currency (today's behaviour); a non-numeric residue
            # ("ab 12") is an unresolvable currency token — drop, never assume.
            residue = re.sub(r"[0-9.,%\s/\-]", "", p).strip()
            if residue:
                unresolved += 1
                continue
            resolved.append(float(amount))
            continue
        if detected == target_currency:
            resolved.append(float(amount))
            continue
        if detected not in effective_fallback_rates():
            # _convert_to_bhd returns the amount UNCHANGED for an unresolvable
            # currency (documented contract, price_service.py:722-724) — never
            # treat its return as proof of conversion; branch on the table.
            unresolved += 1
            continue
        amount = _convert_to_bhd(amount, detected)
        if target_currency != "BHD":
            bhd_rate = _convert_to_bhd(1.0, target_currency)
            if bhd_rate > 0:
                amount = amount / bhd_rate
        resolved.append(float(amount))
    return resolved, unresolved


def verify_price(price: Dict, shopping_items: List[Dict]) -> Dict:
    """Cross-check final price against Serper Shopping prices.

    With ENABLE_FACTCHECK_CURRENCY_NORMALIZATION on (default OFF), every
    shopping row is converted into the final price's own currency before the
    median is taken; rows whose currency cannot be resolved are dropped, and
    when ONLY such rows survive the verdict is None (no verdict) rather than a
    confident wrong one. build_fact_check, ScoringService._score_reliability
    and is_data_freshness_shaky all handle a None verdict safely (audited at
    593ec1e — see issue #106).
    """
    if not price or not shopping_items:
        return {
            "price_verified": price is not None and not (price or {}).get("estimated", False),
            "deviation_pct": None,
            "source_count": 0,
        }

    final_amount = price.get("amount")
    if not final_amount:
        return {"price_verified": False, "deviation_pct": None, "source_count": 0}

    if factcheck_currency_normalization_enabled():
        target_currency = (price.get("currency") or "BHD").upper()
        resolved, unresolved = _normalized_shopping_prices(shopping_items, target_currency)
        if not resolved:
            if unresolved:
                # Rows survive but from unresolvable currencies: NO verdict.
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
        # Exact median expression as the legacy path (upper-median indexing) so
        # a single-currency corpus produces the identical number flag-ON/OFF.
        median = sorted(resolved)[len(resolved) // 2]
        deviation_pct = abs(final_amount - median) / median * 100 if median > 0 else None
        return {
            "price_verified": deviation_pct is not None and deviation_pct <= 30 and not price.get("estimated", False),
            "deviation_pct": round(deviation_pct, 1) if deviation_pct is not None else None,
            "source_count": len(resolved),
        }

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
