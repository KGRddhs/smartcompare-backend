"""Quality ranker for parallel scraper price candidates — Bundle E § Decision 8."""
from __future__ import annotations

from typing import Any

PRICE_SOURCE_RANK: list[tuple[str, int]] = [
    ("confirmed_multi_source", 100),
    ("firecrawl_brand_domain", 90),
    ("page_scrape_jsonld", 85),
    ("serper_shopping", 75),
    ("scrapedo_rendered", 70),
    ("gpt_organic_extract", 60),
    ("gpt_training_estimate", 40),
]

_AGREEMENT_WINDOW = 0.05


def _within_agreement(a: float, b: float) -> bool:
    hi = max(abs(a), abs(b))
    if hi == 0:
        return True
    return abs(a - b) / hi <= _AGREEMENT_WINDOW


def select_best_price(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    ordered = sorted(candidates, key=lambda c: c.get("rank", 0), reverse=True)
    top = ordered[0]
    for other in ordered[1:]:
        if _within_agreement(top.get("value", 0), other.get("value", 0)):
            return {
                "value": top.get("value"),
                "source_method": "confirmed_multi_source",
                "rank": 100,
                "raw_data": top.get("raw_data", {}),
            }
    return {
        "value": top.get("value"),
        "source_method": top.get("source_method"),
        "rank": top.get("rank"),
        "raw_data": top.get("raw_data", {}),
    }
