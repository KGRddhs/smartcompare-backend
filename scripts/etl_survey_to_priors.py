#!/usr/bin/env python3
"""ETL — Survey CSV → pain_workflow_priors.json + decision_style_priors.json.

Sprint (A) Lane 4 task L4.1. Source:
    C:/Users/SynAckITPC/Downloads/SURVEY RESPONSES/Fillout ENG results (2).csv
    C:/Users/SynAckITPC/Downloads/SURVEY RESPONSES/Fillout arab results (9).csv

Output (relative to repo root):
    data/pain_workflow_priors.json   — 8 ranked workflows + per-cohort weights + prompt instructions
    data/decision_style_priors.json  — per-cohort decision-style distribution + _global fallback

The script reads BOTH the English and Arabic surveys, normalises responses
to the canonical workflow names + canonical cohort keys, then aggregates
counts into the two JSON output files.

Run:
    python scripts/etl_survey_to_priors.py
        [--eng PATH] [--arab PATH] [--out-dir PATH] [--quiet]

If the survey CSVs are missing (e.g. CI), the script will refuse to
overwrite existing JSON files — pass --allow-missing to regenerate from
empty input (useful only for shape-test bootstrap).
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants & canonical mappings
# ---------------------------------------------------------------------------

DEFAULT_ENG_CSV = Path(
    r"C:/Users/SynAckITPC/Downloads/SURVEY RESPONSES/Fillout ENG results (2).csv"
)
DEFAULT_ARAB_CSV = Path(
    r"C:/Users/SynAckITPC/Downloads/SURVEY RESPONSES/Fillout arab results (9).csv"
)

# 8 canonical pain workflows — order = baseline rank (overridden by survey
# aggregate). Each carries the design § 6 prompt instruction verbatim.
PAIN_WORKFLOWS: List[Dict[str, str]] = [
    {
        "name": "close_option_paralysis",
        "description": (
            "User stalls when comparing 2-3 close options that look equally good."
        ),
        "prompt_instruction": (
            "If product scores are within 10 points of each other, do NOT say "
            "'both are good.' Provide an EXPLICIT tie-break: 'If budget matters most, "
            "pick A; if X matters most, pick B.' Always pivot the choice on a single "
            "concrete attribute the buyer can self-check."
        ),
    },
    {
        "name": "too_many_specs",
        "description": "User overwhelmed by long spec lists or option counts.",
        "prompt_instruction": (
            "Surface a MAXIMUM of 3 differences in key_tradeoff. Never list 6+ specs "
            "in the verdict text. Compress to the smallest set the buyer actually "
            "decides on. Long specs belong in the spec table, not the verdict prose."
        ),
    },
    {
        "name": "value_budget_uncertainty",
        "description": (
            "Buyer unsure whether the price-per-feature ratio justifies the spend."
        ),
        "prompt_instruction": (
            "Open the verdict with the value-per-BHD comparison and budget alignment. "
            "Cite price first, scores second. State which product gives more capability "
            "per dinar at this budget tier."
        ),
    },
    {
        "name": "trust_paralysis",
        "description": "Buyer doubts whether claims are supported by enough sources.",
        "prompt_instruction": (
            "Cite source counts inline: 'Confirmed by 3 retailers + 2 reviewer "
            "publications.' Never make a bare claim. If only one source supports a "
            "spec, mark it tentative and continue."
        ),
    },
    {
        "name": "post_decision_regret",
        "description": "Buyer regrets the trade-off they made after committing.",
        "prompt_instruction": (
            "Explicitly name the trade-off the buyer is accepting. Use the form "
            "'Choosing A means you give up Y.' Frame it as a conscious choice, not "
            "a downside discovered later."
        ),
    },
    {
        "name": "brand_loyalty_vs_evidence",
        "description": (
            "Buyer favours a known brand but evidence points to the alternative."
        ),
        "prompt_instruction": (
            "If the user's preferred brand loses on the data, acknowledge it: "
            "'Brand X is well-known for Y, but on the specific attributes that match "
            "your priorities here, Z is the better fit.' Respect brand affinity; "
            "do not dismiss it."
        ),
    },
    {
        "name": "warranty_aftersales_missing",
        "description": (
            "Buyer cares about warranty + after-sales coverage but it's not surfaced."
        ),
        "prompt_instruction": (
            "Surface warranty and return-policy information when available. If one "
            "product lacks a stated warranty in Bahrain, flag that as a deciding "
            "factor rather than a footnote."
        ),
    },
    {
        "name": "decision_speed",
        "description": "Buyer wants the answer in seconds, not minutes.",
        "prompt_instruction": (
            "Lead with a TL;DR one-sentence winner declaration that names the product "
            "and the single most important reason. Detail follows for tap-to-expand "
            "readers — never bury the winner past the first sentence."
        ),
    },
]


# Survey Q7 response → canonical workflow name. Buckets multiple verbatim
# answers under one workflow because the survey wording is narrower than
# the 8-workflow taxonomy.
Q7_TO_WORKFLOW: Dict[str, str] = {
    # English Q7
    "When I was comparing 2 or 3 close options": "close_option_paralysis",
    "When I found too many options": "too_many_specs",
    "At the beginning, when I did not know where to start": "decision_speed",
    "Just before paying / buying": "post_decision_regret",
    "It did not feel hard": "_no_pain",
    # Arabic Q7
    "لما كنت أقارن بين خيارين أو ثلاثة قريبين من بعض": "close_option_paralysis",
    "لما لقيت خيارات كثيرة": "too_many_specs",
    "من البداية، لما ما كنت عارف من وين أبدأ": "decision_speed",
    "قبل الدفع أو الشراء مباشرة": "post_decision_regret",
    "ما حسّيت إنه صعب": "_no_pain",
}

# Difficulties question — multi-select, comma-separated. Each token maps to
# 0..1 workflows. Tokens that don't map are ignored.
DIFFICULTY_TOKEN_TO_WORKFLOW: Dict[str, str] = {
    # English
    "Too many options": "too_many_specs",
    "Price": "value_budget_uncertainty",
    "Value for money": "value_budget_uncertainty",
    "Quality - Reliability": "trust_paralysis",
    "I was not sure what suited me": "close_option_paralysis",
    "Warranty or After-sales support": "warranty_aftersales_missing",
    "Brand preference": "brand_loyalty_vs_evidence",
    "Brand reputation": "brand_loyalty_vs_evidence",
    "Nothing made it hard": "_no_pain",
    # Arabic
    "الخيارات كانت كثيرة": "too_many_specs",
    "السعر": "value_budget_uncertainty",
    "القيمة مقابل السعر": "value_budget_uncertainty",
    "الجودة - الاعتمادية": "trust_paralysis",
    "ما كنت أعرف شنو يناسبني": "close_option_paralysis",
    "الضمان أو الدعم بعد البيع": "warranty_aftersales_missing",
    "تفضيل العلامة التجارية": "brand_loyalty_vs_evidence",
    "ما كان فيه شي صعب": "_no_pain",
}


# Decision-style question → canonical style name (4 styles).
STYLE_TO_CANONICAL: Dict[str, str] = {
    # English
    "Show me all details": "show_all_details",
    "Show me only the main differences": "show_only_main_differences",
    "Show me 2 or 3 suitable options": "show_2_or_3_options",
    "Suggest one best option with a reason": "suggest_one_best",
    # Arabic
    "أشوف كل التفاصيل بنفسي": "show_all_details",
    "أشوف أهم الفروقات بس": "show_only_main_differences",
    "أشوف شرح بسيط يوضح لي الخيارات": "show_2_or_3_options",
    "تقترح لي أفضل خيار مع توضيح السبب": "suggest_one_best",
}


# Demographics canonical mapping. Keys mirror cohort_priors.json exactly.
DESCRIBES_TO_NATIONALITY: Dict[str, str] = {
    # English
    "Bahraini": "Bahraini",
    "Non-Bahraini resident in Bahrain": "Non-Bahraini",
    "Prefer not to say": "_unknown",
    # Arabic
    "بحريني - بحرينية": "Bahraini",
    "مقيم/مقيمة غير بحريني - ة في البحرين": "Non-Bahraini",
    "أفضل عدم الإجابة": "_unknown",
}

AGE_CANONICAL: Dict[str, str] = {
    "18-24": "18-24",
    "25-34": "25-34",
    "35-44": "35-44",
    "45+": "45+",
}

GENDER_CANONICAL: Dict[str, str] = {
    # English
    "Female": "Female",
    "Male": "Male",
    "Prefer not to say": "_unknown",
    "Prefer to self-describe": "_unknown",
    # Arabic
    "أنثى": "Female",
    "ذكر": "Male",
    "أفضل عدم الإجابة": "_unknown",
}


# Canonical column names — English headers + Arabic headers grouped.
COL_GROUPS: Dict[str, List[str]] = {
    "q7": [
        "Q7 At what point did the choice feel hardest?",
        "في أي مرحلة حسّيت إن الاختيار كان أصعب شي؟",
    ],
    "difficulties": [
        "What were the top 2 difficulties you faced when trying to choose the right option?",
        "شنو أكثر صعوبتين واجهتهم؟ اختر حتى 2",
    ],
    "style": [
        "Which style of assistance or advice would you prefer to make choosing the right option more clear?",
        "لما تقارن بين خيارات متشابهة، شنو نوع المساعدة اللي تفضل تنعرض لك؟",
    ],
    "describes": [
        "Which of the following best describes you?",
        "أي وحدة تصفك أكثر؟",
    ],
    "age": [
        "What is your age group?",
        "ما هي فئتك العمرية؟",
    ],
    "gender": [
        "What is your gender?",
        "ما هو جنسك؟",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_get(row: Dict[str, str], group: str) -> str:
    """Return the first non-empty value across the column synonyms for group."""
    for col in COL_GROUPS[group]:
        v = row.get(col, "")
        if v is not None and v.strip():
            return v.strip()
    return ""


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _cohort_key(nationality: str, age: str, gender: str) -> Optional[str]:
    if not (nationality and age and gender):
        return None
    if "_unknown" in {nationality, gender}:
        return None
    return f"{age}_{gender.lower()}_{nationality.lower().replace('-', '_')}"


def _normalise_describe(raw: str) -> str:
    return DESCRIBES_TO_NATIONALITY.get(raw, "_unknown")


def _normalise_age(raw: str) -> str:
    return AGE_CANONICAL.get(raw, "")


def _normalise_gender(raw: str) -> str:
    return GENDER_CANONICAL.get(raw, "_unknown")


def _split_multi(raw: str) -> List[str]:
    """Split a multi-select cell value. The survey uses comma separators
    inside a single quoted field; some Arabic entries use a Latin comma too."""
    if not raw:
        return []
    return [tok.strip() for tok in raw.split(",") if tok.strip()]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    """Walk every row, accumulate workflow + style + cohort counts."""
    # Initialise counters
    workflow_counts: Counter[str] = Counter()
    workflow_per_cohort: Dict[str, Counter[str]] = defaultdict(Counter)
    style_per_cohort: Dict[str, Counter[str]] = defaultdict(Counter)
    style_global: Counter[str] = Counter()
    total_with_pain_signal = 0
    total_responses = 0

    for row in rows:
        total_responses += 1

        # Demographics → cohort key
        nationality = _normalise_describe(_row_get(row, "describes"))
        age = _normalise_age(_row_get(row, "age"))
        gender = _normalise_gender(_row_get(row, "gender"))
        cohort = _cohort_key(nationality, age, gender)

        # Pain workflow signal — count Q7 + difficulties tokens
        q7_raw = _row_get(row, "q7")
        q7_workflow = Q7_TO_WORKFLOW.get(q7_raw, "")

        difficulty_tokens = _split_multi(_row_get(row, "difficulties"))
        diff_workflows: List[str] = []
        for tok in difficulty_tokens:
            wf = DIFFICULTY_TOKEN_TO_WORKFLOW.get(tok, "")
            if wf and wf != "_no_pain":
                diff_workflows.append(wf)

        # Union of Q7 + difficulty workflows (dedup per respondent so
        # multi-select doesn't double-count the same pain).
        respondent_workflows: List[str] = []
        if q7_workflow and q7_workflow != "_no_pain":
            respondent_workflows.append(q7_workflow)
        for wf in diff_workflows:
            if wf not in respondent_workflows:
                respondent_workflows.append(wf)

        if respondent_workflows:
            total_with_pain_signal += 1
        for wf in respondent_workflows:
            workflow_counts[wf] += 1
            if cohort:
                workflow_per_cohort[cohort][wf] += 1

        # Decision style
        style_raw = _row_get(row, "style")
        style_canonical = STYLE_TO_CANONICAL.get(style_raw, "")
        if style_canonical:
            style_global[style_canonical] += 1
            if cohort:
                style_per_cohort[cohort][style_canonical] += 1

    return {
        "total_responses": total_responses,
        "total_with_pain_signal": total_with_pain_signal,
        "workflow_counts": dict(workflow_counts),
        "workflow_per_cohort": {k: dict(v) for k, v in workflow_per_cohort.items()},
        "style_per_cohort": {k: dict(v) for k, v in style_per_cohort.items()},
        "style_global": dict(style_global),
    }


# ---------------------------------------------------------------------------
# Emit pain_workflow_priors.json
# ---------------------------------------------------------------------------

def build_pain_workflow_priors(agg: Dict[str, Any], sources: List[str]) -> Dict[str, Any]:
    total_signal = max(agg["total_with_pain_signal"], 1)

    # Compute survey weight per workflow.
    weighted_workflows: List[Tuple[str, float]] = []
    for spec in PAIN_WORKFLOWS:
        name = spec["name"]
        count = agg["workflow_counts"].get(name, 0)
        weight = count / total_signal
        weighted_workflows.append((name, weight))

    # Survey-derived rank: descending by weight, ties broken by baseline rank
    # in PAIN_WORKFLOWS list.
    baseline_rank: Dict[str, int] = {spec["name"]: i for i, spec in enumerate(PAIN_WORKFLOWS)}
    weighted_workflows.sort(key=lambda kv: (-kv[1], baseline_rank[kv[0]]))

    # Per-cohort sorted top-3 (used at prompt time as cohort-targeted picks).
    per_cohort_top: Dict[str, Dict[str, float]] = {}
    for cohort, wf_counts in agg["workflow_per_cohort"].items():
        total = sum(wf_counts.values()) or 1
        per_cohort_top[cohort] = {
            wf: round(c / total, 4) for wf, c in wf_counts.items()
        }

    workflows_out: List[Dict[str, Any]] = []
    for rank_idx, (name, weight) in enumerate(weighted_workflows, start=1):
        spec = next(w for w in PAIN_WORKFLOWS if w["name"] == name)
        per_cohort_for_wf: Dict[str, float] = {}
        for cohort, wf_weights in per_cohort_top.items():
            if name in wf_weights:
                per_cohort_for_wf[cohort] = wf_weights[name]
        workflows_out.append({
            "rank": rank_idx,
            "name": name,
            "description": spec["description"],
            "prompt_instruction": spec["prompt_instruction"],
            "survey_weight": round(weight, 4),
            "per_cohort_weight": per_cohort_for_wf,
        })

    return {
        "metadata": {
            "source": sources,
            "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_responses": agg["total_responses"],
            "total_with_pain_signal": agg["total_with_pain_signal"],
            "schema_version": 1,
            "note": (
                "Ranks derived from survey aggregate of Q7 + Difficulties columns; "
                "prompt_instruction text matches design § 6 verbatim; per_cohort_weight "
                "is share of the cohort's signals attributable to this workflow."
            ),
        },
        "workflows": workflows_out,
    }


# ---------------------------------------------------------------------------
# Emit decision_style_priors.json
# ---------------------------------------------------------------------------

CANONICAL_STYLES = [
    "show_all_details",
    "show_only_main_differences",
    "show_2_or_3_options",
    "suggest_one_best",
]

# Smoothing — every style gets at least this share before normalisation so
# that small cohorts cannot zero out a style. Set deliberately small.
_LAPLACE_PRIOR = 0.01

# Minimum responses per cohort before we emit it (else fall back to _global).
_MIN_COHORT_N = 8


def _normalise_styles(raw_counts: Dict[str, int]) -> Dict[str, float]:
    """Apply Laplace smoothing + normalise so sum == 1.0 across all 4 styles."""
    smoothed: Dict[str, float] = {
        style: raw_counts.get(style, 0) + _LAPLACE_PRIOR for style in CANONICAL_STYLES
    }
    total = sum(smoothed.values())
    return {style: round(v / total, 4) for style, v in smoothed.items()}


def _fix_rounding(d: Dict[str, float]) -> Dict[str, float]:
    """Patch the last bucket so the four rounded values sum to exactly 1.0
    even after individual round() truncation."""
    keys = list(d.keys())
    if not keys:
        return d
    remainder = round(1.0 - sum(d[k] for k in keys[:-1]), 4)
    d[keys[-1]] = remainder
    return d


def build_decision_style_priors(agg: Dict[str, Any], sources: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "metadata": {
            "source": sources,
            "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_responses": agg["total_responses"],
            "min_cohort_n": _MIN_COHORT_N,
            "laplace_prior": _LAPLACE_PRIOR,
            "schema_version": 1,
            "note": (
                "Per-cohort style preference distributions. Cohort emitted only "
                "when >= min_cohort_n raw responses are available; smaller cohorts "
                "fall back to _global at call time. Laplace prior keeps zero-bucket "
                "styles ranked rather than silently dropping them."
            ),
        },
        "_global": _fix_rounding(_normalise_styles(agg["style_global"])),
    }

    for cohort, style_counts in agg["style_per_cohort"].items():
        n = sum(style_counts.values())
        if n < _MIN_COHORT_N:
            continue
        out[cohort] = _fix_rounding(_normalise_styles(style_counts))
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eng", default=str(DEFAULT_ENG_CSV), help="English survey CSV path")
    parser.add_argument("--arab", default=str(DEFAULT_ARAB_CSV), help="Arabic survey CSV path")
    parser.add_argument("--out-dir", default=None, help="Output dir (default: <repo>/data)")
    parser.add_argument("--allow-missing", action="store_true", help="Allow regen even if CSVs missing")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    eng_path = Path(args.eng)
    arab_path = Path(args.arab)

    if not args.allow_missing:
        missing = [p for p in (eng_path, arab_path) if not p.exists()]
        if missing:
            print(f"ERROR: survey CSVs missing: {missing}", file=sys.stderr)
            return 1

    repo_root = Path(__file__).resolve().parent.parent
    out_dir = Path(args.out_dir) if args.out_dir else repo_root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, str]] = []
    sources: List[str] = []
    for path in (eng_path, arab_path):
        new_rows = _read_csv(path)
        rows.extend(new_rows)
        if new_rows:
            sources.append(path.name)

    if not args.quiet:
        print(f"Loaded {len(rows)} survey rows from {len(sources)} files ({sources})")

    agg = aggregate(rows)
    if not args.quiet:
        print(
            f"  total_responses={agg['total_responses']} "
            f"with_pain_signal={agg['total_with_pain_signal']} "
            f"workflow_counts={agg['workflow_counts']}"
        )

    pain_out = build_pain_workflow_priors(agg, sources)
    style_out = build_decision_style_priors(agg, sources)

    pain_file = out_dir / "pain_workflow_priors.json"
    style_file = out_dir / "decision_style_priors.json"
    pain_file.write_text(json.dumps(pain_out, indent=2, ensure_ascii=False), encoding="utf-8")
    style_file.write_text(json.dumps(style_out, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.quiet:
        print(f"Wrote {pain_file} ({len(pain_out['workflows'])} workflows)")
        print(f"Wrote {style_file} ({len([k for k in style_out if k not in ('_global','metadata')])} cohorts + _global)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
