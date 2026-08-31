"""The flag-OFF byte-identity harness (scripts/verify_flag_byte_identity.py).

M11 backlog item 2 (recorded M10 verify finding): the previous scratchpad-only
harness fed ONE fixed query to every corpus page, so 586/588 pages hashed the
literal ``None`` extraction — near-zero discrimination. These tests pin the
three properties the port exists for, on a tiny synthetic corpus (zero
network, zero real corpus dependency):

  * queries are derived PER PAGE, so extractors actually run (non-None
    extractions appear in the payload);
  * two different extractions hash to two different overall SHAs;
  * a rerun over the same corpus is deterministic (same SHA, twice).
"""

import json

import pytest

from scripts.verify_flag_byte_identity import (
    derive_page_query,
    load_manifest,
    run_harness,
)


def _pdp_html(title: str, price: str, currency: str = "BHD") -> str:
    """A minimal but realistic PDP: JSON-LD Product + matching <title>."""
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "brand": {"@type": "Brand", "name": title.split()[0]},
        "offers": {
            "@type": "Offer",
            "price": price,
            "priceCurrency": currency,
            "availability": "https://schema.org/InStock",
        },
    })
    body = "<p>" + ("filler " * 200) + "</p>"
    return (
        "<html><head><title>%s | Test Store</title>"
        '<script type="application/ld+json">%s</script>'
        "</head><body>%s</body></html>" % (title, ld, body)
    )


PAGES = [
    ("https://shop-a.example/products/atlas-oud-noir-50ml",
     "Atlas Oud Noir 50ml", "20.500"),
    ("https://shop-b.example/products/meridian-amber-veil-100ml",
     "Meridian Amber Veil 100ml", "34.900"),
    ("https://shop-c.example/products/cobalt-santal-drift-75ml",
     "Cobalt Santal Drift 75ml", "12.750"),
]


@pytest.fixture
def corpus(tmp_path):
    """(records, manifest_path, html_dir) for the 3-page fixture corpus."""
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    rows = []
    for i, (url, title, price) in enumerate(PAGES):
        p = html_dir / ("page%d.html" % i)
        p.write_text(_pdp_html(title, price), encoding="utf-8")
        rows.append({
            "url": url,
            "path": str(p),
            "domain": url.split("/")[2],
            "page_currency": "BHD",
        })
    manifest = tmp_path / "corpus.jsonl"
    manifest.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8",
    )
    records, skipped = load_manifest(str(manifest), str(html_dir))
    assert skipped == 0
    return records, manifest, html_dir


class TestQueryDerivation:
    def test_manifest_query_wins(self):
        assert derive_page_query(
            {"derived_query": "Hand Derived Name", "url": "https://x/p/slug"},
            "<title>Other</title>",
        ) == "Hand Derived Name"

    def test_page_title_is_used_when_manifest_has_none(self):
        q = derive_page_query(
            {"url": "https://x/products/foo", "brand": "Atlas"},
            "<html><head><title>Oud Noir 50ml | Store</title></head></html>",
        )
        assert "Oud Noir" in q and "Atlas" in q
        assert "Store" not in q  # the site-suffix segment is dropped

    def test_slug_is_the_last_resort(self):
        q = derive_page_query(
            {"url": "https://x/products/amber-veil-100ml"}, "",
        )
        assert q == "amber veil 100ml"

    def test_queries_are_per_page_never_a_fixed_constant(self, corpus):
        records, _, _ = corpus
        queries = {r["query"] for r in records}
        assert len(queries) == len(records) == 3


class TestHarnessRuns:
    def test_extractors_actually_run(self, corpus):
        """The de-degeneration property: with per-page queries the JSON-LD
        extraction engages, so non-None results appear — not 586/588 None."""
        records, _, _ = corpus
        payload, sha = run_harness(records, flags=[])
        assert payload["non_none_extractions"] > 0
        assert payload["distinct_queries"] == 3
        # 3 pages x 2 gate modes x 2 currency legs
        assert len(payload["results"]) == 12
        assert len(sha) == 64

    def test_a_rerun_is_deterministic(self, corpus):
        records, _, _ = corpus
        _, sha1 = run_harness(records, flags=["ENABLE_JSONLD_FIRST"])
        _, sha2 = run_harness(records, flags=["ENABLE_JSONLD_FIRST"])
        assert sha1 == sha2

    def test_two_different_extractions_hash_differently(self, corpus, tmp_path):
        """Change ONE page's price and the overall SHA must move — the exact
        discrimination the fixed-query harness lacked."""
        records, _, html_dir = corpus
        _, sha_before = run_harness(records, flags=[])
        # Rewrite page 1 with a different price; identical everything else.
        url, title, _ = PAGES[1]
        (html_dir / "page1.html").write_text(
            _pdp_html(title, "99.900"), encoding="utf-8",
        )
        _, sha_after = run_harness(records, flags=[])
        assert sha_before != sha_after

    def test_flag_env_is_restored_after_the_sweep(self, corpus, monkeypatch):
        records, _, _ = corpus
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
        monkeypatch.delenv("ENABLE_EXACT_PRICE_GATE", raising=False)
        run_harness(records, flags=["ENABLE_JSONLD_FIRST"])
        import os
        assert os.environ.get("ENABLE_JSONLD_FIRST") == "true"
        assert "ENABLE_EXACT_PRICE_GATE" not in os.environ
