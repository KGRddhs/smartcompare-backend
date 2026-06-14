"""S3-genuine (PDP curl Decision-F, 2026-06-14) — add bahrain.microless.com.

Re-curled SEQUENTIALLY (the first parallel attempt 403'd on a write-race, not a
real block): the live MacBook-Air-M4 PDP returns HTTP 200 and the production
extractor pulls a clean genuine BHD price from JSON-LD:
  offer price=439.062 priceCurrency=BHD availability=InStock

So microless is a CURL source (NOT render-only) — a bahrain-tier electronics
retailer (laptops/computing). Added at weight 3.0, curl-tier (is_render_only
False) so the direct-curl injector + fan_out curl it.
"""

import pytest

from app.services.source_router import SOURCE_REGISTRY, score_source


def _by_domain():
    return {s.domain: s for s in SOURCE_REGISTRY}


class TestMicrolessRegistered:
    def test_microless_in_registry(self):
        assert "bahrain.microless.com" in _by_domain()

    def test_microless_is_bahrain_electronics_curl(self):
        s = _by_domain()["bahrain.microless.com"]
        assert s.tier == "bahrain"
        assert s.weight == 3.0
        assert "electronics" in s.categories
        # Curl-scrapeable (JSON-LD) — must NOT be render-only.
        assert s.is_render_only is False
        # Not Shopify (Magento-ish) — no /products.json path.
        assert s.is_shopify is False

    def test_microless_scores_bahrain_weight_for_electronics(self):
        assert score_source(
            "https://bahrain.microless.com/product/apple-macbook-air-2025/",
            "electronics",
        ) == 3.0

    def test_microless_in_direct_curl_candidates(self):
        """As a curl bahrain electronics source, microless must be emitted by the
        Serper-independent direct-curl injector."""
        from app.services.price_service import build_direct_bh_candidates
        cands = build_direct_bh_candidates("Apple MacBook Air M4", "electronics")
        urls = " ".join(u for u, _ in cands)
        assert "microless" in urls


class TestMicrolessLivePdp:
    def test_live_microless_pdp_extracts_bhd(self):
        from pathlib import Path
        from app.services.price_service import extract_price_from_html
        fix = Path(__file__).parent.parent / ".l1_pdp_probe" / "microless_macbook.html"
        if not fix.exists():
            pytest.skip("live PDP capture not present (probe dir is gitignored)")
        html = fix.read_text(encoding="utf-8", errors="replace")
        res = extract_price_from_html(
            html, "Apple MacBook Air 2025 M4 16GB 256GB", "BHD",
            "bahrain.microless.com",
            "https://bahrain.microless.com/product/apple-macbook-air-2025-m4/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(439.062, abs=0.01)
        assert res["currency"].upper() == "BHD"
        assert res.get("original_currency", "BHD").upper() == "BHD"
