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


def factcheck_honest_absence_enabled() -> bool:
    """True iff ``verify_price`` reports the ABSENCE of cross-check evidence
    honestly (M18 PO-fact-check-07, default OFF).

    Legacy (flag OFF): both empty-evidence branches return
    ``price_verified = not estimated`` — i.e. TRUE for any scraped/converted
    price with ZERO shopping rows to check it against (source_count=0), which
    then earns the +0.1 reliability bonus precisely when nothing checked it.
    Supplements ALWAYS hit this (their shopping cache is set to []).

    Flag ON: zero usable evidence degrades to ``price_verified: None``
    (unknown — the same cross-cutting rule as ``sentiment_consistent: None``
    and the #106 unresolved-rows verdict) for a NON-estimated price, and
    stays ``False`` for an estimate (an estimate is definitionally not a
    verified price — that negative is honest, not fabricated). Downstream is
    already None-safe from #109: ``_score_reliability`` truthy-tests (no
    bonus), ``_product_price_factcheck_contradicts`` identity-tests
    ``is False`` (no demotion), and ``is_data_freshness_shaky`` counts only
    ``is False``. Read PER CALL from os.getenv (the
    price_service.exact_gate_enabled idiom); default OFF is byte-identical.
    """
    return os.getenv("ENABLE_FACTCHECK_HONEST_ABSENCE", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _empty_evidence_verdict(price: Optional[Dict]) -> Optional[bool]:
    """The ``price_verified`` value for a source_count==0 return.

    Flag OFF: legacy ``not estimated`` fabrication (byte-identical).
    Flag ON: ``None`` (unknown) unless the price is missing or estimated,
    both of which keep their honest ``False``.
    """
    if price is None:
        return False
    estimated = bool(price.get("estimated", False))
    if factcheck_honest_absence_enabled():
        return False if estimated else None
    return not estimated


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


def citation_rubric_v2_enabled() -> bool:
    """True iff the citation rubric is unit-aware and can emit "flagged"
    (issue #108, default OFF).

    The v1 rubric compares bare digit substrings: a fabricated `128 TB` cited
    against a `128 GB` snippet earns "verified", a value that CONTRADICTS its
    own cited snippet earns "likely" (weight 0.7 — above an honest "training"
    at 0.3), and "flagged" is counted downstream but produced nowhere. Read
    PER CALL from os.getenv (the price_service.exact_gate_enabled idiom);
    default OFF is byte-identical to f2481b9.
    """
    return os.getenv("ENABLE_CITATION_RUBRIC_V2", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


#: Arabic thousands separator (U+066C) — stripped alongside "," before any
#: number matching so `5,000`/`5٬000`/`5000` compare equal on both sides.
_ARABIC_THOUSANDS_SEP = "٬"


def _strip_thousands_separators(text: str) -> str:
    return text.replace(",", "").replace(_ARABIC_THOUSANDS_SEP, "")


# Bounded unit vocabulary (issue #108). Copied from price_service's
# _SPACED_UNIT_RE (gb|tb|ml|oz|mm|hz|mah|inch(es)) and extended with the units
# NUMERIC_SPEC_FIELDS actually carry (mb, kg, g, mg, mcg, iu, l, w, in, ").
# Deliberately BOUNDED rather than any-trailing-letters: an open capture would
# read prose words after a number ("128 different") as units and manufacture
# false "flagged" disagreements. Alternation order matters — longer tokens
# before their prefixes (gb before g, mcg/mg before g, inch before in).
_UNIT_CORE = r"gb|tb|mb|ml|oz|mm|hz|mah|inch(?:es)?|kg|mcg|mg|g|iu|l|w"
# Value side accepts "in" and the double-quote inch spelling. Snippet side
# deliberately EXCLUDES bare "in": in prose it is a preposition ("128 in
# stock") far more often than a unit, and treating it as one would turn the
# contradiction rule into a false-"flagged" generator. A value spelled "in"
# still matches a snippet spelled "inch"/"inches" via aliasing; a snippet that
# only ever says "in" degrades that pair to "unverified" — absent, never a
# manufactured contradiction.
_VALUE_NUM_UNIT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(" + _UNIT_CORE + r"|in|\")(?![a-z0-9])", re.I
)
_SNIPPET_NUM_UNIT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(" + _UNIT_CORE + r"|\")(?![a-z0-9])", re.I
)
_UNIT_ALIASES = {"inches": "inch", "in": "inch", '"': "inch"}


def _extract_number_units(text: str, *, value_side: bool):
    """Extract ((number, unit) pairs, loose-number strings) from text.

    A number immediately followed (optionally spaced — "128 GB" == "128GB")
    by a bounded-vocabulary unit forms a pair; every other number is "loose".
    """
    rx = _VALUE_NUM_UNIT_RE if value_side else _SNIPPET_NUM_UNIT_RE
    pairs = []
    spans = []
    for m in rx.finditer(text):
        unit = _UNIT_ALIASES.get(m.group(2).lower(), m.group(2).lower())
        try:
            pairs.append((float(m.group(1)), unit))
        except ValueError:  # pragma: no cover — \d-only capture always floats
            continue
        spans.append(m.span(1))
    loose = []
    for m in re.finditer(r"\d+(?:\.\d+)?", text):
        if any(s <= m.start() < e for (s, e) in spans):
            continue
        loose.append(m.group(0))
    return pairs, loose


def _grade_citation_v2(key: str, value_str: str, snippet_text: str) -> str:
    """Issue #108 flag-ON grading of one cited field against its snippet.

    Numeric fields: a cited (number, unit) counts as matched only when the
    SAME unit appears adjacent to that number in the snippet.
      * every number matched            -> "verified"
      * same-unit number, wrong number  -> "flagged"   (contradicted)
      * no comparable same-unit number  -> "unverified" (absent — a snippet
        with nothing to compare is not evidence and must not outscore an
        honest "training", which also lands on "unverified")
    Non-numeric fields keep the term-overlap rubric (on separator-normalized
    text, so `5,000`-style spellings benefit there too).
    """
    value_norm = _strip_thousands_separators(value_str)
    snippet_norm = _strip_thousands_separators(snippet_text)

    v_pairs, v_loose = _extract_number_units(value_norm, value_side=True)
    v_loose_sig = [n for n in v_loose if len(n.replace(".", "")) >= 2]

    if key in NUMERIC_SPEC_FIELDS and (v_pairs or v_loose_sig):
        s_pairs, _ = _extract_number_units(snippet_norm, value_side=False)
        all_matched = True
        contradicted = False
        for num, unit in v_pairs:
            same_unit = [n for (n, u) in s_pairs if u == unit]
            if any(abs(n - num) <= 1e-9 * max(1.0, abs(num)) for n in same_unit):
                continue
            all_matched = False
            if same_unit:
                contradicted = True
        for n in v_loose_sig:
            if n not in snippet_norm:
                all_matched = False
        if all_matched:
            return "verified"
        if contradicted:
            return "flagged"
        return "unverified"

    terms = [t for t in value_norm.split() if len(t) > 2]
    if not terms:
        return "likely"
    matches = sum(1 for t in terms if t in snippet_norm)
    return "verified" if matches >= len(terms) * 0.5 else "likely"


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

                    # Issue #108 (flag ON): unit-aware rubric that can emit
                    # "flagged". Flag OFF: the legacy digit-substring rubric
                    # below runs untouched, byte-identical to f2481b9.
                    if citation_rubric_v2_enabled():
                        confidence[key] = _grade_citation_v2(key, value_str, snippet_text)
                        continue

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


def _shopping_number_confirmed(
    n: str, value_str: str, shopping_text: str, identity_numbers: set
) -> bool:
    """Issue #108 fix (c), flag-ON only — is spec number `n` genuinely
    confirmed by the shopping text?

    A digit that is part of the product's own name/brand/model (e.g. the "16"
    of "iPhone 16") is NOT evidence for a spec value: it only counts when it
    appears in the shopping text ADJACENT to the unit the spec value itself
    pairs it with ("16GB"/"16 GB" confirms ram="16 GB"; a bare model-number
    "16" does not). A colliding digit whose value carries no unit cannot be
    disambiguated and is dropped (degrades toward unverified, never upgrades).
    Non-colliding digits keep the legacy substring check.
    """
    if n not in identity_numbers:
        return n in shopping_text
    v_pairs, _ = _extract_number_units(
        _strip_thousands_separators(value_str), value_side=True
    )
    try:
        n_val = float(n)
    except ValueError:  # pragma: no cover — \d-only capture always floats
        return False
    for num, unit in v_pairs:
        if abs(num - n_val) > 1e-9:
            continue
        pat_unit = "inch(?:es)?" if unit == "inch" else re.escape(unit)
        if re.search(
            r"\b" + re.escape(n) + r"\s*" + pat_unit + r"(?![a-z0-9])",
            shopping_text,
        ):
            return True
    return False


def cross_validate_specs_with_shopping(
    specs: Dict, shopping_items: List[Dict], product_name: str = ""
) -> Dict[str, str]:
    """Cross-check spec values against Serper Shopping product titles/descriptions.

    Upgrades 'likely' to 'verified' if shopping data confirms.

    `product_name` (issue #108, optional so existing callers stay valid) feeds
    the flag-ON identity fence: a digit belonging to the product's own
    name/brand/model cannot upgrade a spec value. Flag OFF it is ignored.
    """
    if not shopping_items:
        return {}

    shopping_text = " ".join(
        f"{item.get('title', '')} {item.get('description', '')}"
        for item in shopping_items
    ).lower()

    rubric_v2 = citation_rubric_v2_enabled()
    identity_numbers: set = set()
    if rubric_v2:
        identity_text = " ".join(
            str(part or "")
            for part in (product_name, specs.get("brand"), specs.get("model"))
        ).lower()
        identity_numbers = set(re.findall(r"\d+", identity_text))

    flags = {}
    checkable = ["storage", "ram", "display", "processor", "count", "dosage", "form"]
    for key in checkable:
        value = specs.get(key)
        if not value or value == "N/A":
            continue
        value_str = str(value).lower()
        spec_numbers = [n for n in re.findall(r'\d+', value_str) if len(n) >= 2]
        if spec_numbers:
            if rubric_v2:
                all_found = all(
                    _shopping_number_confirmed(
                        n, value_str, shopping_text, identity_numbers
                    )
                    for n in spec_numbers
                )
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
    # M18 PO-fact-check-09 — a JSON-mode model can emit a QUOTED number and
    # cached reviews replay it for 7-14 days; `abs('4.5' - 4.3)` raised
    # TypeError at an unguarded call site OUTSIDE every try, losing the whole
    # compare. Coerce here (extract-time normalize also coerces, but cached
    # rows written before that fix still carry strings). Unparseable ->
    # None-shape, i.e. honest "could not check", never a crash.
    if gpt_rating is not None and not isinstance(gpt_rating, (int, float)):
        try:
            gpt_rating = float(str(gpt_rating).strip())
        except (ValueError, TypeError):
            gpt_rating = None
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
        # M18 PO-fact-check-07 — flag ON, zero evidence is UNKNOWN (None),
        # never a fabricated True; estimates keep their honest False.
        return {
            "price_verified": _empty_evidence_verdict(price),
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
        # M18 PO-fact-check-07 — same absence rule as the no-items branch.
        return {
            "price_verified": _empty_evidence_verdict(price),
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
        # A bare numeral carries no currency signal, so it is read as already
        # being in the TARGET currency (same rule the numeric-row branch above
        # applies). It must be PARSED under that currency too: BHD has three
        # decimals, so the ordinary Bahraini string "99.500" is 99.5 -- parsing
        # it with no currency reads 99500.0 and inverts the verdict on a
        # correct price. Same M13-10 canon as `BHD 12,500` -> 12.5.
        amount = parse_price_string(raw, detected or target, display_text=True)
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
            # M18 PO-fact-check-07 — same absence rule as the legacy branches.
            "price_verified": _empty_evidence_verdict(price),
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
