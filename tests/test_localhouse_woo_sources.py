"""Round-5 local-house genuine-BHD WooCommerce sources (alibaksh.com /
fragrancebh.com).

These two NON-walled Bahrain WooCommerce perfumeries are the durable genuine-BHD
source for the local Arabic houses (Lattafa/Rasasi/Armaf/Swiss Arabian/Al
Haramain) the prior catalog only reached via GCC-converted or Cloudflare-walled
stores. This pins them live + wired so a future `build_source_registry_data`
regeneration (or a liveness re-probe) can't silently drop or mis-map them.
"""
import json
from pathlib import Path

import pytest

_DATA = Path(__file__).resolve().parent.parent / "data" / "bh_gcc_sources.json"
_TARGETS = ("alibaksh.com", "fragrancebh.com")


def _by_domain():
    return {r["domain"]: r for r in json.loads(_DATA.read_text(encoding="utf-8"))}


@pytest.mark.parametrize("domain", _TARGETS)
def test_localhouse_woo_row_live_and_wired(domain):
    row = _by_domain().get(domain)
    assert row is not None, f"{domain} missing from bh_gcc_sources.json (round5 dropped?)"
    assert row["status"] == "live", f"{domain} not live"
    assert row["tier"] == "bahrain", f"{domain} must be bahrain-tier (BHD -> genuine)"
    assert row["currency"] == "BHD"
    assert row["mechanism"] == "woo_store_json"
    assert row["genuine_method"] == "woo_store_api"
    assert "fragrances" in row["categories"]


def test_localhouse_woo_rows_loaded_by_catalog_loader(monkeypatch):
    """The real _load_catalog_rows (flag ON) admits both rows with the woo
    mechanism — exercises the actual runtime loader, not just the data file."""
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    import app.services.source_router as sr

    loaded = {s.domain: s for s in sr._load_catalog_rows()}
    for domain in _TARGETS:
        assert domain in loaded, f"{domain} not admitted by _load_catalog_rows"
        assert loaded[domain].mechanism == "woo_store_json"
        assert loaded[domain].tier == "bahrain"


def test_localhouse_woo_rows_absent_when_flag_off(monkeypatch):
    """Flag OFF -> catalog dormant -> the rows do NOT load (ships inert)."""
    monkeypatch.delenv("ENABLE_BH_GCC_CATALOG_SOURCES", raising=False)
    import app.services.source_router as sr

    assert sr._load_catalog_rows() == []
