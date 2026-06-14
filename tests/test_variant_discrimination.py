"""S3 #1 (discovery-match) — variant-discrimination guard.

Live repro (sharafdg/microless site: discovery for "iPhone 15"): the base-model
query strict-matches the HIGHER variants because "iPhone 15" is a prefix of
"iPhone 15 Pro Max" — strict_title_match=True, numbers_match=True, overlap=1.00.
So a "iPhone 15" query can attribute the Pro Max PDP's (higher) price, or the
fan_out picks the wrong-variant PDP. Same wrong-product class as iPhone16->14.

variant_mismatch(query, title) rejects a candidate that carries a model-
distinguishing qualifier (pro/max/plus/ultra/mini) the QUERY lacks (title is a
more-specific SKU), and vice-versa (query qualifier absent from title).
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")


class TestVariantMismatch:
    def test_base_query_rejects_pro_max_title(self):
        from app.services.price_service import variant_mismatch
        # "iPhone 15" must NOT match "iPhone 15 Pro Max" (different SKU).
        assert variant_mismatch("iPhone 15", "Apple iPhone 15 Pro Max 1TB Black") is True
        assert variant_mismatch("iPhone 15", "Apple iPhone 15 Pro 256GB Natural") is True
        assert variant_mismatch("iPhone 15", "Apple iPhone 15 Plus 128GB") is True

    def test_base_query_matches_base_title(self):
        from app.services.price_service import variant_mismatch
        # "iPhone 15" DOES match the genuine base "iPhone 15 128GB Black".
        assert variant_mismatch("iPhone 15", "Apple iPhone 15 128GB Black with FaceTime") is False
        assert variant_mismatch("iPhone 15", "Apple iPhone 15 128GB Pink") is False

    def test_pro_query_requires_pro_title(self):
        from app.services.price_service import variant_mismatch
        # "iPhone 15 Pro" must match a Pro title, NOT the base or Pro Max.
        assert variant_mismatch("iPhone 15 Pro", "Apple iPhone 15 Pro 256GB") is False
        assert variant_mismatch("iPhone 15 Pro", "Apple iPhone 15 128GB Black") is True  # base lacks "pro"
        assert variant_mismatch("iPhone 15 Pro", "Apple iPhone 15 Pro Max 1TB") is True  # max extra

    def test_pro_max_query_matches_pro_max(self):
        from app.services.price_service import variant_mismatch
        assert variant_mismatch("iPhone 15 Pro Max", "Apple iPhone 15 Pro Max 256GB") is False
        assert variant_mismatch("iPhone 15 Pro Max", "Apple iPhone 15 Pro 256GB") is True  # missing max

    def test_macbook_air_vs_no_qualifier(self):
        from app.services.price_service import variant_mismatch
        # MacBook Air M3 vs MacBook Pro — "air"/"pro" are the discriminators.
        assert variant_mismatch("MacBook Air M3", "Apple MacBook Pro M3 14-inch") is True
        assert variant_mismatch("MacBook Air M3", "Apple MacBook Air M3 13-inch 8GB") is False

    def test_no_qualifiers_either_side_is_match(self):
        from app.services.price_service import variant_mismatch
        # Neither has a variant qualifier → not a variant mismatch (other
        # matchers handle brand/number).
        assert variant_mismatch("Galaxy S24", "Samsung Galaxy S24 256GB") is False

    def test_size_qualifier_inch_discriminates(self):
        from app.services.price_service import variant_mismatch
        # 13-inch vs 15-inch MacBook Air M3 — a size qualifier in the QUERY must
        # be honored; but a size ONLY in the title (query unspecified) is allowed
        # (query didn't constrain size).
        assert variant_mismatch("MacBook Air 13 M3", "Apple MacBook Air 15-inch M3") is True
        assert variant_mismatch("MacBook Air M3", "Apple MacBook Air 15-inch M3") is False
