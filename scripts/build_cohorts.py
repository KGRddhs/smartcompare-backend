"""Build data/cohort_priors.json from Fillout survey CSVs.

One-shot ETL: reads English + Arabic CSV exports, normalizes Arabic values to
English, groups by cohort key (age|gender|governorate|language), and writes
per-cohort modal answers + distributions plus fallback aggregates.

Run: python -m scripts.build_cohorts
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
ENG_CSV_PATH = ROOT / "data" / "surveys" / "Fillout_ENG_results.csv"
ARABIC_CSV_PATH = ROOT / "data" / "surveys" / "Fillout_arab_results.csv"
OUTPUT_PATH = ROOT / "data" / "cohort_priors.json"

VERSION = "1.0"

# ============================================================
# Arabic ↔ English value normalization
# ============================================================
#
# Maps the categorical Arabic responses observed in Fillout_arab_results.csv
# to their canonical English form so we can group bilingual cohorts together.
# Build script FAILS LOUDLY (raises ValueError) on any unmapped Arabic value;
# extending this table is intentional — adding silently would mask data drift.

ARABIC_TO_ENGLISH: dict[str, str] = {
    # ---- Categories purchased / category-of-recent-product ----
    "إلكترونيات": "Electronics",
    "الكترونيات": "Electronics",
    "جهاز منزلي": "Home appliance",
    "اشتراك أو خدمة": "Subscription or Service",
    "منتج أزياء - تجميل": "Fashion or Beauty item",
    "عطور": "Fragrance",
    "منتج صحي": "Health product",
    "مركبة": "Vehicle",
    "دراجة نارية": "Motorcycle",
    "ديكور": "Decor",
    # ---- Deciding factors (single + multi-select) ----
    "الجودة": "Quality",
    "الجودة - الاعتمادية": "Quality - Reliability",
    "الجودة أو الاعتمادية": "Quality - Reliability",
    "السعر": "Price",
    "العلامة التجارية": "Brand",
    "القيمة مقابل السعر": "Value for money",
    "الضمان أو خدمة ما بعد البيع": "Warranty or After-sales support",
    "الضمان - خدمة ما بعد البيع": "Warranty or After-sales support",
    "الشكل او التصميم": "Design",
    "سهولة الاستخدام": "Ease of use",
    "سهولة فهم المنتج": "Easy information",
    "آراء موثوقة": "Trusted opinions",
    "توصية من شخص أثق به": "Recommendation from someone I trust",
    "اقتراح من الذكاء الاصطناعي": "AI suggestion",
    # ---- Gender ----
    "أنثى": "Female",
    "ذكر": "Male",
    "أفضل عدم الإجابة": "Prefer not to say",
    "أفضل عدم الإجابة\u00a0": "Prefer not to say",  # trailing nbsp variant
    # ---- Governorate ----
    "محافظة العاصمة": "Capital",
    "المحافظة الشمالية": "Northern",
    "محافظة المحرق": "Muharraq",
    "المحافظة الجنوبية": "Southern",
    # ---- Identity ----
    "بحريني - بحرينية": "Bahraini",
    "مقيم/مقيمة غير بحريني - ة في البحرين": "Non-Bahraini resident in Bahrain",
    # ---- Spend brackets ----
    "أقل من 25 دينار بحريني": "<25 BHD",
    "من 25 إلى أقل من 50 دينار بحريني": "25-50 BHD",
    "من 50 إلى أقل من 100 دينار بحريني": "50-100 BHD",
    "من 100 إلى أقل من 250 دينار بحريني": "100-250 BHD",
    "250 دينار بحريني أو أكثر": "250+ BHD",
    # ---- Language ----
    "العربية": "Arabic",
    "الإنجليزية": "English",
    "كلتاهما بالتساوي": "Both equally",
    # ---- Trust source ----
    "شخص أعرفه": "Someone I know",
    "خبرتي السابقة": "My past experience",
    "وسائل التواصل": "Social media",
    "ما وثقت كثير بأي مصدر": "I did not strongly trust any source",
    "أداة ذكاء اصطناعي": "AI tool",
    "متجر": "Store",
    "قوقل": "Google",
    # ---- Assistance style ----
    "أشوف كل التفاصيل بنفسي": "Show me all details",
    "تقترح لي أفضل خيار مع توضيح السبب": "Suggest one best option with a reason",
    "أشوف أهم الفروقات بس": "Show me only the main differences",
    "أشوف شرح بسيط يوضح لي الخيارات": "Show me 2 or 3 suitable options",
    # ---- If info incomplete ----
    "أدور معلومات أكثر": "Look for more information",
    "أسأل شخص أثق فيه": "Ask someone I trust",
    "أسأل شخص": "Ask someone I trust",  # short fixture variant
    "أأجل الشراء": "Delay the purchase",
    "أختار الماركة اللي أعرفها": "Choose the brand I know",
    "أختار الماركة": "Choose the brand I know",
    "أسأل أداة ذكاء اصطناعي": "Ask an AI tool",
    "أروح متجر": "Go to a store",
    "من البداية": "From the beginning",
    "ما حسّيت": "Did not feel hard",
    # ---- Open-text primary_category responses (long-tail Arabic free-text) ----
    "Tool box للسيارة": "Other",
    "تعليقه سيارة": "Vehicle",
    "خلاط كهربائي": "Home appliance",
    "سيارة": "Vehicle",
    "قطع غيار": "Vehicle parts",
    "قهوة": "Grocery",
    "كتاب": "Book",
    "منتجات الغذاء/ الطعام": "Grocery",
    # ---- Difficulties ----
    "الخيارات كانت كثيرة": "Too many options",
    "ما كنت أعرف شنو يناسبني": "I was not sure what suited me",
    "ما كان فيه شي صعب": "Nothing made it hard",
    "الفروقات مو واضحة": "The differences were not clear",
    # ---- Post-purchase pattern ----
    "حسيت إني اخترت صح": "I felt I made the right choice",
    "كنت راضي إلى حد كبير بس بعد في شك": "I was mostly satisfied but still unsure",
    "بعدين حسيت كان المفروض أختار غير": "Later I felt I should have chosen differently",
    "استمريت أبحث وأقارن حتى بعد الشراء": "I kept looking even after buying",
    "رجعته أو بدلته": "Returned or exchanged",
    "رجعته": "Returned or exchanged",
    # ---- What helps most ----
    "معلومات أوضح": "Clearer information",
    "شرح أبسط للفروقات": "Simpler differences between options",
    "وضوح أفضل للأسعار": "Better price visibility",
    "خيارات أقل أراجعها": "Fewer options to go through",
    "مساعدة من أداة ذكاء اصطناعي": "AI help that explains clearly",
    "أهم الفروقات": "Simpler differences between options",
    "الخيار اللي يناسب": "Show main differences",
    "الخيار اللي يناسب ميزانيت": "Show main differences",
    "وضوح أفضل": "Clearer information",
}


def _has_arabic(value: str) -> bool:
    """True if value contains any character in the Arabic Unicode block (U+0600..U+06FF)."""
    return any(0x0600 <= ord(c) <= 0x06FF for c in value)


def normalize_value(value: str, field: str) -> str:
    """Map Arabic value to English; pass English through; FAIL on unknown Arabic.

    Empty strings pass through (caller decides whether empty is meaningful).
    Any value containing Arabic-script characters that's not in the mapping table
    raises ValueError so the build is loud about data drift. Latin-1 punctuation
    like NBSP (U+00A0) is tolerated because it occurs in Fillout's English exports.
    """
    if value is None:
        return ""
    value = value.strip()
    if value == "":
        return ""
    if value in ARABIC_TO_ENGLISH:
        return ARABIC_TO_ENGLISH[value]
    if _has_arabic(value):
        raise ValueError(
            f"unknown {field} value: {value!r} — add to ARABIC_TO_ENGLISH"
        )
    return value


# ============================================================
# Row dropping rules (consent + finished + multi-skip)
# ============================================================

CONSENT_FIELDS = (
    " I agree and want to continue",  # English (note leading space in CSV header)
    "I agree and want to continue",
    "أوافق وأرغب في المتابعة",
)

COHORT_KEY_FIELDS_EN = (
    "What is your age group?",
    "What is your gender?",
    "Which governorate do you mainly live in?",
    "Which language do you usually use when searching for products or services?",
)
COHORT_KEY_FIELDS_AR = (
    "ما هي فئتك العمرية؟",
    "ما هو جنسك؟",
    "في أي محافظة تعيش بشكل رئيسي؟",
    "ما اللغة التي تستخدمها غالباً عند البحث عن المنتجات أو الخدمات؟",
)

SKIP_PHRASES = {
    "",
    "Prefer not to say",
    "أفضل عدم الإجابة",
    "أفضل عدم الإجابة\u00a0",
}


def _get_first_match(row: dict, candidates: Iterable[str]) -> str:
    for key in candidates:
        v = row.get(key)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def _get_cohort_field(row: dict, idx: int) -> str:
    """Return the value for the given cohort field index, EN or AR."""
    en_val = (row.get(COHORT_KEY_FIELDS_EN[idx]) or "").strip()
    ar_val = (row.get(COHORT_KEY_FIELDS_AR[idx]) or "").strip()
    return en_val or ar_val


def should_drop_row(row: dict) -> bool:
    """Drop rows that violate consent, are unfinished, or have all cohort keys empty."""
    consent = _get_first_match(row, CONSENT_FIELDS).lower()
    if consent != "true":
        return True
    status = (row.get("Status") or "").strip().lower()
    if status != "finished":
        return True
    cohort_values = [_get_cohort_field(row, i) for i in range(4)]
    if all(v in SKIP_PHRASES for v in cohort_values):
        return True
    return False


# ============================================================
# Multi-select splitting
# ============================================================


def split_multi(value: str | None) -> list[str]:
    """Split a comma-separated multi-select value, strip whitespace, drop empties."""
    if value is None:
        return []
    if not isinstance(value, str):
        return []
    parts = [p.strip() for p in value.split(",")]
    return [p for p in parts if p]


# ============================================================
# Cohort key construction
# ============================================================

GOVERNORATE_SHORT_FORM = {
    "Northern Governorate": "Northern",
    "Capital Governorate": "Capital",
    "Muharraq Governorate": "Muharraq",
    "Southern Governorate": "Southern",
}


def build_cohort_key(
    age_group: str, gender: str, governorate: str, language: str
) -> str:
    """Build the canonical cohort key from 4 normalized fields."""
    gov = GOVERNORATE_SHORT_FORM.get(governorate, governorate)
    return f"{age_group}|{gender}|{gov}|{language}"


# ============================================================
# Confidence flag thresholds (per design 2.3)
# ============================================================


def _confidence_for(n: int) -> str | None:
    if n >= 20:
        return "high"
    if n >= 10:
        return "medium"
    if n >= 5:
        return "low"
    return None  # < 5 → omit cohort entirely


# ============================================================
# Modal computation + cohort stats
# ============================================================

# These are the MODAL fields tracked per cohort. The values come from the
# normalized rows produced by the ETL.
SCALAR_MODAL_FIELDS = (
    "spend_bracket",
    "assistance_style",
    "post_purchase_pattern",
    "if_info_incomplete",
)
MULTI_MODAL_FIELDS = (
    "deciding_factor",
    "trust_sources",
    "top_difficulties",
    "what_helps_most",
    "primary_categories",
)


def _modal_value(values: list) -> Any:
    """Return the most-common value from a list of values (None if empty)."""
    counts = Counter(v for v in values if v not in (None, ""))
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _distribution(values: list) -> dict[str, float]:
    """Return value → ratio (sums to ~1.0). Empties dropped."""
    counts = Counter(v for v in values if v not in (None, ""))
    total = sum(counts.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in counts.items()}


def _aggregate_rows(rows: list[dict], demographics: dict) -> dict:
    """Compute modal + distribution + persona for a group of normalized rows."""
    # Single-value fields → direct mode
    scalar_modal = {
        f: _modal_value([r.get(f) for r in rows]) for f in SCALAR_MODAL_FIELDS
    }
    # Multi-select fields → flatten then mode for "top X"
    multi_flat: dict[str, list] = {f: [] for f in MULTI_MODAL_FIELDS}
    for r in rows:
        for f in MULTI_MODAL_FIELDS:
            multi_flat[f].extend(r.get(f) or [])

    # Single most-common item per multi field
    multi_modal_top = {f: _modal_value(multi_flat[f]) for f in MULTI_MODAL_FIELDS}

    # For deciding_factor, also surface the second-most-common
    deciding_counts = Counter(multi_flat["deciding_factor"])
    deciding_ranked = [k for k, _ in deciding_counts.most_common(5)]

    modal: dict[str, Any] = {
        "top_deciding_factor": deciding_ranked[0] if deciding_ranked else None,
        "second_deciding_factor": deciding_ranked[1] if len(deciding_ranked) > 1 else None,
        "preferred_assistance_style": scalar_modal.get("assistance_style"),
        "spend_bracket": scalar_modal.get("spend_bracket"),
        "trust_sources": [k for k, _ in Counter(multi_flat["trust_sources"]).most_common(3)],
        "top_difficulties": [k for k, _ in Counter(multi_flat["top_difficulties"]).most_common(3)],
        "post_purchase_pattern": scalar_modal.get("post_purchase_pattern"),
        "what_helps_most": [k for k, _ in Counter(multi_flat["what_helps_most"]).most_common(3)],
        "primary_categories": [k for k, _ in Counter(multi_flat["primary_categories"]).most_common(3)],
        "if_info_incomplete": scalar_modal.get("if_info_incomplete"),
    }

    distribution = {
        "deciding_factor": _distribution(multi_flat["deciding_factor"]),
        "assistance_style": _distribution([r.get("assistance_style") for r in rows]),
        "spend_bracket": _distribution([r.get("spend_bracket") for r in rows]),
    }

    persona = generate_persona_label(modal)

    return {
        "n": len(rows),
        "demographics": demographics,
        "modal": modal,
        "distribution": distribution,
        "persona_label": persona,
    }


def _derive_demographics_from_key(key: str) -> dict[str, str]:
    """Parse 'age|gender|governorate|language' back to a demographics dict."""
    parts = key.split("|")
    return {
        "age_group": parts[0] if len(parts) > 0 else "",
        "gender": parts[1] if len(parts) > 1 else "",
        "governorate": parts[2] if len(parts) > 2 else "",
        "language": parts[3] if len(parts) > 3 else "",
    }


def _row_demographics(row: dict) -> dict[str, str]:
    """Get demographics from a normalized row, preferring per-row fields, falling back to cohort_key."""
    if any(row.get(k) for k in ("age_group", "gender", "governorate", "language")):
        return {
            "age_group": row.get("age_group", ""),
            "gender": row.get("gender", ""),
            "governorate": row.get("governorate", ""),
            "language": row.get("language", ""),
        }
    return _derive_demographics_from_key(row.get("cohort_key", ""))


def build_cohort_stats(rows: list[dict]) -> dict:
    """Group normalized rows by cohort_key + compute per-cohort stats + fallbacks."""
    by_key: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        key = r.get("cohort_key")
        if key:
            by_key[key].append(r)

    cohorts: dict[str, dict] = {}
    for key, group in by_key.items():
        # Skip keys where any of the 4 parts is empty (e.g. user skipped
        # governorate). match() can never hit these — broader fallback
        # aggregates already cover the broadened-key path.
        parts = key.split("|")
        if len(parts) != 4 or any(p == "" for p in parts):
            continue
        n = len(group)
        confidence = _confidence_for(n)
        if confidence is None:
            continue  # n<5 → omit
        demographics = _row_demographics(group[0])
        agg = _aggregate_rows(group, demographics)
        agg["confidence"] = confidence
        cohorts[key] = agg

    # Fallback aggregates: shorter prefixes + special "all"
    fallback = _build_fallback_aggregates(rows)

    return {
        "version": VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "total_responses": len(rows),
        "cohorts": cohorts,
        "fallback_aggregates": fallback,
    }


def _build_fallback_aggregates(rows: list[dict]) -> dict[str, dict]:
    """Build aggregates for shorter prefixes + the population-wide 'all' bucket."""
    fallback: dict[str, dict] = {}

    # Group by various prefix combinations
    by_age_gender_lang: dict[str, list[dict]] = defaultdict(list)
    by_age_gender: dict[str, list[dict]] = defaultdict(list)
    by_age: dict[str, list[dict]] = defaultdict(list)
    by_gender: dict[str, list[dict]] = defaultdict(list)

    for r in rows:
        demo = _row_demographics(r)
        age = demo.get("age_group", "")
        gender = demo.get("gender", "")
        lang = demo.get("language", "")
        if age and gender and lang:
            by_age_gender_lang[f"{age}|{gender}|{lang}"].append(r)
        if age and gender:
            by_age_gender[f"{age}|{gender}"].append(r)
        if age:
            by_age[age].append(r)
        if gender:
            by_gender[gender].append(r)

    def _add_aggregate(key: str, group: list[dict], demo_keys: list[str]):
        if not group:
            return
        n = len(group)
        if n < 5:
            return  # don't expose small fallbacks
        demographics = {k: _row_demographics(group[0]).get(k) for k in demo_keys}
        agg = _aggregate_rows(group, demographics)
        agg["confidence"] = _confidence_for(n) or "low"
        fallback[key] = agg

    for key, group in by_age_gender_lang.items():
        _add_aggregate(key, group, ["age_group", "gender", "language"])
    for key, group in by_age_gender.items():
        _add_aggregate(key, group, ["age_group", "gender"])
    for key, group in by_age.items():
        _add_aggregate(key, group, ["age_group"])
    for key, group in by_gender.items():
        _add_aggregate(key, group, ["gender"])

    # Population-wide aggregate
    all_agg = _aggregate_rows(rows, {})
    all_agg["confidence"] = _confidence_for(len(rows)) or "low"
    fallback["all"] = all_agg

    return fallback


# ============================================================
# Persona label generation (per design 2.5)
# ============================================================


def generate_persona_label(modal: dict) -> str:
    """Map modal answers to a one-line human-readable persona label."""
    factor = (modal.get("top_deciding_factor") or "").lower()
    spend = (modal.get("spend_bracket") or "").lower()
    style = (modal.get("preferred_assistance_style") or "").lower()

    # Quality + low/mid spend + 2-3 options → quality-first focused
    if "quality" in factor:
        if "100-250" in spend or "250+" in spend:
            return "Premium quality-conscious buyer"
        if "show me 2 or 3" in style or "main differences" in style:
            return "Quality-first focused buyer"
        return "Quality-first buyer"

    # Price + sub-25 → budget-conscious value seeker
    if "price" in factor:
        if "<25" in spend or "less than 25" in spend:
            return "Budget-conscious value seeker"
        return "Price-sensitive shopper"

    if "value" in factor:
        return "Value-driven buyer"

    if "brand" in factor:
        if "100-250" in spend or "250+" in spend:
            return "Premium brand-loyal buyer"
        return "Brand-conscious buyer"

    if "warranty" in factor or "after" in factor:
        return "Reliability-first buyer"

    if "design" in factor:
        return "Design-driven buyer"

    if "recommendation" in factor:
        return "Trust-network buyer"

    return "Balanced shopper"


# ============================================================
# Atomic write (per design 6.3 — never partial files)
# ============================================================


def write_atomic(target: Path, payload: dict) -> None:
    """Write JSON atomically: serialize to .tmp then os.replace to target."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp.write_text(serialized, encoding="utf-8")
    try:
        os.replace(tmp, target)
    except Exception:
        # Cleanup the tmp file so no partial artifact lingers
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


# ============================================================
# CSV → normalized row pipeline
# ============================================================

# Maps from CSV column header → normalized output field
EN_COLUMN_MAP = {
    "What is your age group?": "age_group",
    "What is your gender?": "gender",
    "Which governorate do you mainly live in?": "governorate",
    "Which language do you usually use when searching for products or services?": "language",
    "About how much did you spend?": "spend_bracket_raw",
    "In the end, what was the most important factor that helped you make the final choice?": "top_factor_single",
    "When choosing between similar options, what matters most to you? Choose up to 2.": "deciding_factor_multi",
    "Which style of assistance or advice would you prefer to make choosing the right option more clear?": "assistance_style",
    "If the information is incomplete or unclear, what do you usually do first?": "if_info_incomplete",
    "What were the top 2 difficulties you faced when trying to choose the right option?": "top_difficulties_multi",
    "Among these sources, which one did you trust the most while choosing?": "trust_sources_single",
    "After buying, how did you usually feel?": "post_purchase_pattern",
    "What would have made that decision easier for you? Choose up to 2.": "what_helps_most_multi",
    "Which one was the most recent ?": "primary_category_single",
    "Which of the following best describes you?": "identity",
}

AR_COLUMN_MAP = {
    "ما هي فئتك العمرية؟": "age_group",
    "ما هو جنسك؟": "gender",
    "في أي محافظة تعيش بشكل رئيسي؟": "governorate",
    "ما اللغة التي تستخدمها غالباً عند البحث عن المنتجات أو الخدمات؟": "language",
    "تقريباً، جم دفعت؟": "spend_bracket_raw",
    "في النهاية، شنو كان العامل الأهم اللي خلاك تحسم قرارك؟": "top_factor_single",
    "لما تختار بين خيارات متشابهة، شنو أكثر شي يهمك؟ اختر حتى 2.": "deciding_factor_multi",
    "لما تقارن بين خيارات متشابهة، شنو نوع المساعدة اللي تفضل تنعرض لك؟": "assistance_style",
    "إذا كانت المعلومات ناقصة أو مو واضحة، شتسوي أول شي عادة؟": "if_info_incomplete",
    "شنو أكثر صعوبتين واجهتهم؟ اختر حتى 2": "top_difficulties_multi",
    "من بين هالمصادر، شنو أكثر مصدر وثقت فيه وقت الاختيار؟": "trust_sources_single",
    "بعد ما اشتريت، شلون كان شعورك وقتها؟": "post_purchase_pattern",
    "شنو كان بيسهّل عليك هالقرار أكثر؟ اختر حتى 2.": "what_helps_most_multi",
    "شنو كان آخر واحد منهم؟": "primary_category_single",
    "أي وحدة تصفك أكثر؟": "identity",
}


def _spend_bracket_normalize(raw: str) -> str | None:
    """Map raw spend descriptions (English variations) to canonical bracket strings."""
    if not raw:
        return None
    s = raw.strip().lower()
    if "less than 25" in s or "<25" in s or "أقل من 25" in s:
        return "<25 BHD"
    if "25 to less than 50" in s or "25-50" in s or "25 إلى أقل من 50" in s:
        return "25-50 BHD"
    if "50 to less than 100" in s or "50-100" in s or "50 إلى أقل من 100" in s:
        return "50-100 BHD"
    if "100 to less than 250" in s or "100-250" in s or "100 إلى أقل من 250" in s:
        return "100-250 BHD"
    if "250 bhd or more" in s or "250+" in s or "250 دينار" in s:
        return "250+ BHD"
    return raw  # leave unchanged for downstream normalization


def parse_row(row: dict, column_map: dict) -> dict | None:
    """Convert a raw CSV row into a normalized cohort row (or None to drop)."""
    if should_drop_row(row):
        return None

    out: dict[str, Any] = {}
    for col, target in column_map.items():
        raw = row.get(col, "") or ""
        if target.endswith("_multi"):
            out[target.removesuffix("_multi")] = [
                normalize_value(v, field=target) for v in split_multi(raw)
            ]
        elif target.endswith("_single"):
            base = target.removesuffix("_single")
            out[base] = normalize_value(raw, field=base)
        else:
            out[target] = normalize_value(raw, field=target)

    # Cohort key: derive from age|gender|governorate|language
    age = out.get("age_group", "")
    gender = out.get("gender", "")
    gov = out.get("governorate", "")
    lang = out.get("language", "")
    out["governorate"] = GOVERNORATE_SHORT_FORM.get(gov, gov)
    if age in SKIP_PHRASES:
        age = ""
    if gender in SKIP_PHRASES:
        gender = ""
    if gov in SKIP_PHRASES:
        gov = ""
    if lang in SKIP_PHRASES:
        lang = ""
    out["age_group"] = age
    out["gender"] = gender
    out["language"] = lang
    out["cohort_key"] = build_cohort_key(age, gender, gov, lang)

    # Spend bracket canonicalization
    raw_spend = out.pop("spend_bracket_raw", "")
    out["spend_bracket"] = _spend_bracket_normalize(raw_spend)

    # Combine top_factor_single (last most-important factor) into deciding_factor list
    top_factor = out.pop("top_factor", None)
    if top_factor:
        deciding = out.get("deciding_factor") or []
        if top_factor not in deciding:
            deciding = [top_factor] + deciding
        out["deciding_factor"] = deciding
    out.setdefault("deciding_factor", [])

    # Trust sources from a single column (some rows have only one)
    trust_single = out.pop("trust_sources", None)
    if isinstance(trust_single, str):
        out["trust_sources"] = [trust_single] if trust_single else []
    else:
        out["trust_sources"] = trust_single or []

    # Primary categories from the single most-recent column
    primary = out.pop("primary_category", None)
    out["primary_categories"] = [primary] if primary else []

    # Multi-select fields default to []
    for f in ("top_difficulties", "what_helps_most"):
        if not isinstance(out.get(f), list):
            out[f] = []

    return out


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def main() -> None:
    """Entry point: read CSVs → normalize → group → atomic write JSON."""
    eng_rows = _read_csv(ENG_CSV_PATH)
    arab_rows = _read_csv(ARABIC_CSV_PATH)

    normalized: list[dict] = []
    for raw in eng_rows:
        parsed = parse_row(raw, EN_COLUMN_MAP)
        if parsed is not None:
            normalized.append(parsed)
    for raw in arab_rows:
        parsed = parse_row(raw, AR_COLUMN_MAP)
        if parsed is not None:
            normalized.append(parsed)

    stats = build_cohort_stats(normalized)
    write_atomic(OUTPUT_PATH, stats)

    # Friendly summary to stdout
    print(
        f"[build_cohorts] wrote {OUTPUT_PATH}\n"
        f"  total_responses: {stats['total_responses']}\n"
        f"  cohorts (n>=5): {len(stats['cohorts'])}\n"
        f"  fallback aggregates: {len(stats['fallback_aggregates'])}"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
