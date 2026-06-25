"""Pure-function unit test for the OUT-OF-BAND sephora.me provider-test harness
classify/harvest helpers (.qa-bias-rerun/_sephora_provider_test.py).

NO network — operates on saved-HTML fixtures. Importing the harness module
triggers its env-guard (blanks UPSTASH creds + sets SCRAPEDO_SUPER in THIS
process's env only — never Railway), which is harmless under pytest. The harness
is NOT prod code and NOT wired into the cascade; this test only pins the pure
classifier so a GO verdict can never be manufactured by a misclassified wall.
"""
import importlib.util
import os

import pytest

# Load the .qa-bias-rerun harness module by path (it lives outside the package).
_HARNESS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".qa-bias-rerun", "_sephora_provider_test.py",
)
_spec = importlib.util.spec_from_file_location("_sephora_provider_test", _HARNESS_PATH)
_h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_h)


# --- Saved-HTML fixtures (no network) --------------------------------------
AKAMAI_403_BODY = (
    "<HTML><HEAD><TITLE>Access Denied</TITLE></HEAD><BODY>"
    "<H1>Access Denied</H1> You don't have permission to access "
    '"http://www.sephora.me/bh-en/makeup" on this server.<P>'
    "Reference #18.abcd1234.1700000000.0a0b0c0d</P></BODY></HTML>"
)

CATEGORY_WITH_PDPS = (
    "<html><body>"
    '<a href="https://www.sephora.me/bh-en/p/size-up-mascara/713779">Size Up</a>'
    '<a href="/bh-en/p/another-product/998877">Another</a>'
    '<a href="/bh-en/p/size-up-mascara/713779">dup</a>'  # duplicate collapses
    '<a href="/bh-en/makeup">category link, not a PDP</a>'
    "</body></html>"
)

BRANDS_CONTROL_NO_PDPS = (
    "<html><body><h1>Brands</h1>"
    '<a href="/bh-en/brand/dior">Dior</a>'
    '<a href="/bh-en/brand/chanel">Chanel</a>'
    "</body></html>"
)


class TestLooksAkamaiBlocked:
    def test_403_status_is_blocked_regardless_of_body(self):
        assert _h.looks_akamai_blocked("<html>anything</html>", 403) is True

    def test_akamai_body_marker_blocks_even_on_200(self):
        # A 200 challenge page that carries an Akamai marker is still a wall.
        assert _h.looks_akamai_blocked(AKAMAI_403_BODY, 200) is True

    def test_reference_hash_marker_detected(self):
        assert _h.looks_akamai_blocked("server error Reference #99.deadbeef", 200) is True

    def test_clean_200_not_blocked(self):
        assert _h.looks_akamai_blocked(CATEGORY_WITH_PDPS, 200) is False

    def test_empty_body_non_403_not_blocked_on_body_axis(self):
        assert _h.looks_akamai_blocked(None, 0) is False
        assert _h.looks_akamai_blocked("", 0) is False


class TestHarvestPdpLinks:
    def test_extracts_distinct_pdps(self):
        links = _h.harvest_pdp_links(CATEGORY_WITH_PDPS)
        # 2 distinct PDPs (the dup collapses; the /makeup category link is excluded).
        assert len(links) == 2
        assert any("713779" in l for l in links)
        assert any("998877" in l for l in links)

    def test_control_page_yields_zero_pdps(self):
        assert _h.harvest_pdp_links(BRANDS_CONTROL_NO_PDPS) == []

    def test_empty_html_yields_zero(self):
        assert _h.harvest_pdp_links(None) == []
        assert _h.harvest_pdp_links("") == []


class TestClassifyOutcome:
    def test_403_classifies_akamai_block(self):
        assert _h.classify_outcome(AKAMAI_403_BODY, 403, None, []) == "akamai_block"

    def test_200_akamai_marker_body_classifies_block(self):
        assert _h.classify_outcome(AKAMAI_403_BODY, 200, None, []) == "akamai_block"

    def test_pass_price_when_bhd_price_extracted(self):
        out = _h.classify_outcome("<html>ok</html>", 200, {"amount": 12.5}, [])
        assert out == "pass_price"

    def test_pass_harvest_when_pdps_found(self):
        out = _h.classify_outcome(CATEGORY_WITH_PDPS, 200, None,
                                  _h.harvest_pdp_links(CATEGORY_WITH_PDPS))
        assert out == "pass_harvest"

    def test_no_price_on_clean_control(self):
        # 200, not blocked, no price, no harvestable links (the /bh-en/brands case).
        out = _h.classify_outcome(BRANDS_CONTROL_NO_PDPS, 200, None, [])
        assert out == "no_price"

    def test_empty_body_non_403_classifies_empty(self):
        assert _h.classify_outcome("", 0, None, []) == "empty"
        assert _h.classify_outcome(None, 0, None, []) == "empty"


class TestVerdict:
    def _rec(self, outcome):
        return {"outcome": outcome}

    def test_go_scrapedo_when_super_passes(self):
        scr = [self._rec("akamai_block"), self._rec("pass_price")]
        assert _h._decide_verdict(scr, []) == "GO_SCRAPEDO"

    def test_go_zyte_when_only_zyte_passes(self):
        scr = [self._rec("akamai_block"), self._rec("akamai_block")]
        zyte = [self._rec("pass_harvest")]
        assert _h._decide_verdict(scr, zyte) == "GO_ZYTE"

    def test_no_go_when_both_block(self):
        scr = [self._rec("akamai_block"), self._rec("empty")]
        zyte = [self._rec("akamai_block")]
        assert _h._decide_verdict(scr, zyte) == "NO_GO"

    def test_no_go_when_only_no_price_or_control(self):
        # 200 but no price + no harvest (e.g. the brands control) is NOT a pass.
        scr = [self._rec("no_price"), self._rec("akamai_block")]
        assert _h._decide_verdict(scr, []) == "NO_GO"


def test_harness_does_not_import_source_router():
    """Belt-and-braces: the harness must NOT touch the prod routing chokepoint —
    importing _sephora_provider_test must not pull in app.services.source_router
    (it would, if the harness called get_sources_for_category / flipped routing).
    The harness only forces SCRAPEDO_SUPER in its OWN process env (never Railway)
    and drives scrapedo_service.render_page_with_status directly, out-of-band.

    NOTE: we deliberately do NOT assert UPSTASH_REDIS_URL=='' here — conftest.py
    re-loads .env at collection, repopulating it AFTER the harness blanked it.
    The real no-prod-write guard is the harness blanking the creds BEFORE its own
    cache_service import at RUN time (so redis_client is None then); that ordering
    is not reproducible under pytest's collect-then-run lifecycle, so asserting it
    here would be a false signal."""
    # The harness module never binds source_router (it would, if it called
    # get_sources_for_category / flipped routing). Inspect the module's OWN
    # namespace + source text rather than global sys.modules (which other test
    # files in a full-suite run could have polluted) so this stays order-robust.
    assert not hasattr(_h, "source_router"), (
        "harness binds source_router — it must not touch prod routing"
    )
    with open(_HARNESS_PATH, "r", encoding="utf-8") as f:
        src = f.read()
    assert "import source_router" not in src and "get_sources_for_category" not in src
    # The harness DID force the super flag in this process's env (import side effect).
    assert os.environ.get("SCRAPEDO_SUPER") == "true"
