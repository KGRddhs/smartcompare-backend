"""Audit single-word content-blocklist entries for product-name collisions.

F2.3 (Bundle B S1). The B0-E "opium" incident (commit 9f6e498) showed that a
single bare token in `app/data/content_blocklist.json` can collide with a
legitimate product/brand name ("YSL Black Opium" — a fragrance) and get the
whole query rejected at the L1 prefilter. This script generalises that audit:
for every SINGLE-WORD English blocklist entry it checks, using the EXACT
production matcher (`ContentSafetyService`), whether the term word-boundary-
matches inside any string in a legitimate product-name corpus.

Corpus sources:
  - gold-truth queries          (data/validation_gold_truth.json `queries[].query`)
  - brand / keyword constants   (app/services/price_service.py)
  - a curated catalogue of real product/brand names that historically collide
    with safety vocabulary (fragrances especially — the opium class), so the
    audit catches collisions even when the name is not yet in a static list.

Flagged single-word entries should be converted to multi-word phrases that
preserve the harmful intent without colliding (the opium pattern), each with a
regression test (legitimate-passes + harmful-phrase-still-blocks).

Usage:
    python scripts/audit_blocklist_collisions.py          # human report
    python scripts/audit_blocklist_collisions.py --json   # machine-readable
Exit code 1 when any collision is found (so CI / a test can assert clean).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# The matcher constructs an OpenAI client lazily only on the L3 path; importing
# the service is safe, but set a noop key so any eager construction elsewhere
# in the import graph does not raise in a bare CI environment.
os.environ.setdefault("OPENAI_API_KEY", "noop-audit-blocklist")

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.services.content_safety_service import ContentSafetyService  # noqa: E402


def _single_word_en_entries() -> dict[str, list[str]]:
    """Return {category: [single-word en terms]} from the live blocklist.

    "Single-word" = no internal whitespace. Hyphenated tokens (ar-15) count as
    single tokens but are excluded — they cannot collide with multi-word names
    and are model-number-shaped, not English words.
    """
    blocklist_path = _REPO / "app" / "data" / "content_blocklist.json"
    doc = json.loads(blocklist_path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for cat, lists in doc.get("categories", {}).items():
        singles = [
            t for t in lists.get("en", [])
            if " " not in t and "-" not in t
        ]
        if singles:
            out[cat] = singles
    return out


def _gold_truth_queries() -> list[str]:
    path = _REPO / "data" / "validation_gold_truth.json"
    if not path.exists():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [q.get("query", "") for q in doc.get("queries", []) if q.get("query")]


def _price_service_brand_corpus() -> list[str]:
    """Pull the legitimate brand / product keyword constants from price_service."""
    from app.services import price_service as ps

    corpus: list[str] = []
    for const_name in (
        "LUXURY_BRAND_KEYWORDS",
        "HIGH_VALUE_KEYWORDS",
        "SUPPLEMENT_KEYWORDS",
        "ACCESSORY_KEYWORDS",
    ):
        corpus.extend(getattr(ps, const_name, set()))
    return corpus


# Mainstream, high-volume legitimate products a real GCC user WOULD compare and
# whose NAME shares a token with safety vocabulary — the exact class the opium
# incident proved we must guard (a name need not be in a brand constant to
# reach the L1 prefilter). Every entry MUST pass L1; a hit here is a real
# false-positive (the bug). Curated, fact-anchored (each is a shipping product
# as of 2026). The genuinely-unsafe forms (switchblade, cocaine the drug, etc.)
# are intentionally absent — those SHOULD block, and converting them would
# weaken safety (F2.3 invariant).
_PRODUCT_NAME_CATALOGUE = [
    # Fragrances — historically the highest-collision category
    "YSL Black Opium Eau de Parfum",
    "Yves Saint Laurent Opium Vintage",
    "Dior Poison",
    "Dior Hypnotic Poison",
    "Dior Pure Poison",
    "Calvin Klein Obsession",
    "Calvin Klein Euphoria",
    "Maison Margiela Replica Jazz Club",   # "Replica" is a fragrance LINE name
    "Maison Margiela Replica Beach Walk",
    "Viktor & Rolf Spicebomb",
    # Makeup / skincare with edgy-but-mainstream names
    "NARS Orgasm Blush",
    "Charlotte Tilbury Pillow Talk",
    "Urban Decay Naked Heat Palette",
    "MAC Russian Red Lipstick",
]


def run_audit() -> dict:
    svc = ContentSafetyService()
    singles = _single_word_en_entries()

    corpus = (
        _gold_truth_queries()
        + _price_service_brand_corpus()
        + _PRODUCT_NAME_CATALOGUE
    )

    # Map term -> compiled single-term pattern reusing the SERVICE's boundary
    # semantics, so the audit matches production exactly.
    import re

    collisions: list[dict] = []
    for cat, terms in singles.items():
        for term in terms:
            pat = re.compile(
                r"(?:^|[\s\W])(" + re.escape(term.lower()) + r")(?=$|[\s\W])",
                flags=re.IGNORECASE | re.UNICODE,
            )
            hits = [name for name in corpus if pat.search(name.lower())]
            if hits:
                collisions.append({
                    "category": cat,
                    "term": term,
                    "collides_with": sorted(set(hits)),
                })

    # Cross-check via the actual L1 entry point for each collision (defensive:
    # confirms check_query_intent rejects, not just the local regex).
    for c in collisions:
        sample = c["collides_with"][0]
        res = svc.check_query_intent(sample)
        c["l1_blocks_sample"] = (not res.allowed)
        c["l1_reason"] = res.reason

    return {
        "single_word_entry_count": sum(len(v) for v in singles.values()),
        "collision_count": len(collisions),
        "collisions": collisions,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    report = run_audit()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Single-word EN blocklist entries audited: {report['single_word_entry_count']}")
        print(f"Collisions found: {report['collision_count']}\n")
        for c in report["collisions"]:
            flag = "L1 REJECTS" if c["l1_blocks_sample"] else "no-L1-hit"
            print(f"  [{c['category']}] '{c['term']}' [{flag}] collides with:")
            for name in c["collides_with"]:
                print(f"        - {name}")
        if not report["collisions"]:
            print("  (clean — no single-word entry collides with the corpus)")

    return 1 if report["collision_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
