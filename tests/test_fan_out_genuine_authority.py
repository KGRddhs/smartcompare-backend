"""S3 electronics-authority (prong b/c — fan_out layer) — a genuine BH price
must out-rank a converted_usd INSIDE the fan_out's _select_best, regardless of
price.

PROD-VERIFY Phase-4 iteration: after the backfill got sharafdg's genuine 244.99
PDP into the pool, iPhone 15 STILL returned apple.com 198.9 converted_usd —
because in the fan_out, apple.com's downgraded converted_usd (rank 85, value
198.9) and sharafdg's genuine page_scrape (rank 85, value 244.99) tie on rank,
and _select_best's tie-break (rank, -value) picked the CHEAPER apple.com.

Fix: _select_best ranks a genuine source-method ABOVE a converted_usd/estimated
one before the value tie-break. Authority over price (CLAUDE.md MOST-AUTHORITATIVE).
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")


_GENUINE = {"value": 244.99, "source_method": "page_scrape_jsonld", "rank": 85,
            "raw_data": {"amount": 244.99, "retailer": "bahrain.sharafdg.com",
                         "source_method": "page_scrape"}}
_CONVERTED = {"value": 198.9, "source_method": "converted_usd", "rank": 85,
              "raw_data": {"amount": 198.9, "retailer": "apple.com",
                           "source_method": "converted_usd"}}


class TestSelectBestGenuineAuthority:
    def test_genuine_pagescrape_beats_cheaper_converted(self):
        from app.services.price_service import _select_best
        best = _select_best([_CONVERTED, _GENUINE])
        assert best["raw_data"]["retailer"] == "bahrain.sharafdg.com", (
            f"converted_usd {best['value']} won over genuine page_scrape — "
            f"authority must beat price"
        )
        assert abs(best["value"] - 244.99) < 0.01

    def test_order_independent(self):
        """Genuine wins regardless of list order."""
        from app.services.price_service import _select_best
        best = _select_best([_GENUINE, _CONVERTED])
        assert best["raw_data"]["retailer"] == "bahrain.sharafdg.com"

    def test_two_genuine_lowest_price_wins(self):
        """Among TWO genuine prices, the existing (rank, -value) tie-break still
        picks the lower — authority tier is equal, so price decides."""
        from app.services.price_service import _select_best
        g1 = {"value": 244.99, "source_method": "page_scrape_jsonld", "rank": 85,
              "raw_data": {"amount": 244.99, "retailer": "bahrain.sharafdg.com",
                           "source_method": "page_scrape"}}
        g2 = {"value": 239.0, "source_method": "page_scrape_jsonld", "rank": 85,
              "raw_data": {"amount": 239.0, "retailer": "bahrain.microless.com",
                           "source_method": "page_scrape"}}
        best = _select_best([g1, g2])
        assert abs(best["value"] - 239.0) < 0.01

    def test_higher_rank_still_wins_over_authority_tier(self):
        """A rank-90 converted (firecrawl_brand_domain) still beats a rank-85
        genuine? NO — authority tier dominates rank for the genuine-vs-converted
        decision. A genuine BH price is the answer even at lower rank."""
        from app.services.price_service import _select_best
        conv90 = {"value": 198.9, "source_method": "converted_usd", "rank": 90,
                  "raw_data": {"amount": 198.9, "retailer": "apple.com",
                               "source_method": "converted_usd"}}
        best = _select_best([conv90, _GENUINE])
        assert best["raw_data"]["retailer"] == "bahrain.sharafdg.com", (
            "a genuine BH page_scrape must beat a converted_usd even at lower rank"
        )

    def test_no_genuine_falls_back_to_rank_then_price(self):
        """When NO genuine exists, the existing rank/price ordering is unchanged."""
        from app.services.price_service import _select_best
        c1 = {"value": 198.9, "source_method": "converted_usd", "rank": 85,
              "raw_data": {"amount": 198.9, "retailer": "apple.com"}}
        c2 = {"value": 169.0, "source_method": "converted_usd", "rank": 85,
              "raw_data": {"amount": 169.0, "retailer": "bestbuy.com"}}
        best = _select_best([c1, c2])
        assert abs(best["value"] - 169.0) < 0.01  # cheaper converted wins (tier equal)


class TestConfirmedExcludesConverted:
    """Prod-verify Phase-4 deepest cause: apple.com's converted_usd curl (rank
    85) triggered the fan_out's rank>=85 early-exit and CANCELLED sharafdg's
    pending genuine curl before it finished. _confirmed must NOT confirm on a
    converted_usd/estimated candidate's rank — only a genuine one ends the race."""

    def test_converted_rank85_does_not_confirm(self):
        from app.services.price_service import _confirmed
        # apple.com converted_usd at rank 85 — must NOT confirm (genuine pending).
        cands = [{"value": 198.9, "source_method": "converted_usd", "rank": 85,
                  "raw_data": {"source_method": "converted_usd"}}]
        assert _confirmed(cands) is False, (
            "a converted_usd rank-85 candidate confirmed the race + would cancel "
            "pending genuine curls"
        )

    def test_genuine_rank85_does_confirm(self):
        from app.services.price_service import _confirmed
        cands = [{"value": 244.99, "source_method": "page_scrape_jsonld", "rank": 85,
                  "raw_data": {"source_method": "page_scrape"}}]
        assert _confirmed(cands) is True

    def test_two_converted_agree_still_does_not_confirm_early_cancel(self):
        """Two converted prices agreeing should NOT confirm-and-cancel either —
        a pending genuine BH curl deserves to finish. (Agreement confirm is
        gated to genuine, same as rank.)"""
        from app.services.price_service import _confirmed
        cands = [
            {"value": 198.9, "source_method": "converted_usd", "rank": 85,
             "raw_data": {"source_method": "converted_usd"}},
            {"value": 200.0, "source_method": "converted_usd", "rank": 70,
             "raw_data": {"source_method": "converted_usd"}},
        ]
        assert _confirmed(cands) is False

    def test_genuine_pair_agreement_confirms(self):
        from app.services.price_service import _confirmed
        cands = [
            {"value": 244.99, "source_method": "page_scrape", "rank": 70,
             "raw_data": {"source_method": "page_scrape"}},
            {"value": 245.0, "source_method": "page_scrape", "rank": 70,
             "raw_data": {"source_method": "page_scrape"}},
        ]
        assert _confirmed(cands) is True
