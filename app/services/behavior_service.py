"""Behavioral learning service for user profile aggregation.

Computes behavioral profiles from comparison history, feedback, and events.
Profiles are stored as JSONB on the users table and updated after each comparison.
"""

from datetime import datetime
from typing import Any, Dict, List


# Tab-to-dimension mapping for sensitivity computation
TAB_DIMENSION_MAP = {
    "specs": "spec_score",
    "reviews": "review_score",
    "overview": "price_score",  # overview attention correlates with price focus
}

MIN_DWELL_MS = 2000  # Minimum dwell time to count


class BehaviorService:
    """Computes and manages user behavioral profiles."""

    def _decay_weight(self, event_time: datetime, now: datetime) -> float:
        """Exponential decay with 30-day half-life."""
        days_ago = (now - event_time).total_seconds() / 86400
        return 0.5 ** (days_ago / 30)

    def _compute_category_affinity(self, comparisons: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute category affinity from comparison history with decay weighting."""
        if not comparisons:
            return {}
        now = datetime.now()
        weighted_counts: Dict[str, float] = {}
        for c in comparisons:
            cat = c.get("category_used", "other")
            created = c.get("created_at", "")
            try:
                event_time = datetime.fromisoformat(
                    created.replace("Z", "+00:00").replace("+00:00", "")
                ) if created else now
            except (ValueError, AttributeError):
                event_time = now
            weight = self._decay_weight(event_time, now)
            weighted_counts[cat] = weighted_counts.get(cat, 0) + weight
        total = sum(weighted_counts.values())
        if total == 0:
            return {}
        return {cat: round(w / total, 3) for cat, w in weighted_counts.items()}

    def _compute_price_range(self, comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute price range preference from comparison prices."""
        prices = []
        for c in comparisons:
            for p in c.get("products", []):
                price = p.get("price", {})
                if isinstance(price, dict) and price.get("amount"):
                    prices.append(price["amount"])
                elif isinstance(price, (int, float)) and price > 0:
                    prices.append(price)
        if not prices:
            return {"avg_price_viewed": 0, "tier_distribution": {}}
        avg = sum(prices) / len(prices)
        # Compute tier distribution
        tiers = {"budget": 0, "mid": 0, "premium": 0, "luxury": 0}
        for p in prices:
            if p < 11:
                tiers["budget"] += 1
            elif p < 57:
                tiers["mid"] += 1
            elif p < 189:
                tiers["premium"] += 1
            else:
                tiers["luxury"] += 1
        total = len(prices)
        tier_dist = {t: round(c / total, 2) for t, c in tiers.items()}
        return {"avg_price_viewed": round(avg, 1), "tier_distribution": tier_dist}

    def _compute_winner_agreement(self, feedback: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute winner agreement from feedback."""
        agreed = sum(1 for f in feedback if f.get("useful") is True)
        disagreed = sum(1 for f in feedback if f.get("useful") is False)
        total = agreed + disagreed
        rate = round(agreed / total, 3) if total > 0 else 0.0
        return {"agreed": agreed, "disagreed": disagreed, "agreement_rate": rate}

    def _compute_dimension_sensitivity(self, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute dimension sensitivity from tab dwell patterns."""
        dwell_totals: Dict[str, float] = {}
        for e in events:
            if e.get("event_type") != "tab_switch":
                continue
            meta = e.get("metadata", {})
            tab = meta.get("to", "")
            dwell = meta.get("dwell_ms", 0)
            if dwell < MIN_DWELL_MS:
                continue
            dim = TAB_DIMENSION_MAP.get(tab)
            if dim:
                dwell_totals[dim] = dwell_totals.get(dim, 0) + dwell
        total_dwell = sum(dwell_totals.values())
        if total_dwell == 0:
            return {}
        return {dim: round(dwell / total_dwell, 3) for dim, dwell in dwell_totals.items()}

    def compute_session_signals(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute in-session signals from event list."""
        tab_switches = [e for e in events if e.get("event_type") == "tab_switch"]
        first_tab = tab_switches[0].get("metadata", {}).get("to") if tab_switches else None

        dwell_by_tab: Dict[str, int] = {}
        for e in tab_switches:
            meta = e.get("metadata", {})
            tab = meta.get("to", "")
            dwell = meta.get("dwell_ms", 0)
            dwell_by_tab[tab] = dwell_by_tab.get(tab, 0) + dwell

        return {
            "first_tab_viewed": first_tab,
            "tab_dwell_ms": dwell_by_tab,
            "price_checked_first": first_tab == "overview",
            "shared_result": any(e.get("event_type") == "share" for e in events),
            "feedback_given": next(
                (
                    "positive" if e.get("metadata", {}).get("useful") else "negative"
                    for e in events
                    if e.get("event_type") == "feedback"
                ),
                None,
            ),
        }

    async def build_behavior_profile(
        self,
        comparisons: List[Dict[str, Any]],
        feedback: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build complete behavioral profile from user data."""
        return {
            "category_affinity": self._compute_category_affinity(comparisons),
            "price_range_preference": self._compute_price_range(comparisons),
            "winner_agreement": self._compute_winner_agreement(feedback),
            "dimension_sensitivity": self._compute_dimension_sensitivity(events),
            "comparison_count": len(comparisons),
            "last_updated": datetime.now().isoformat(),
        }


def get_behavior_service() -> BehaviorService:
    """Singleton factory."""
    if not hasattr(get_behavior_service, "_instance"):
        get_behavior_service._instance = BehaviorService()
    return get_behavior_service._instance
