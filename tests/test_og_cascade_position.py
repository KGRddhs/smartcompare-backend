"""The OpenGraph branch's POSITION in `extract_price_from_html` is FROZEN.

Wave-2 blocker 1. The `ENABLE_OG_BRANCH_FIXES` commit (45b2313) shipped three
changes; two were correctness fixes and the third, "(c)", moved the OpenGraph
branch from Priority 2 down to LAST, below the microdata and WooCommerce-span
branches. (c) is REVERTED. This file exists so nobody re-lands it.

Measured over the 92 cached fragrance PDPs in ``_proof/html/`` with
``ENABLE_EXACT_PRICE_GATE=false`` (extraction-isolation mode -- with the gate ON
the identity gate rejects most cached pages and everything returns None, which
masks extraction behaviour entirely), the reorder produced ZERO improvements and
these regressions:

    oudworlds.com       19.54 BHD (OMR, converted_usd)  ->  3.00 (page_scrape)
                        a 6.5x UNDER-price. The Woo "first span not in <del>"
                        rule picks a different product on a page whose spans are
                        4.000 / 3.000 / 2.500 / 4.000 / 20.000 -- the real one
                        being 20.000 -- AND it relabels an honest converted_usd
                        as a fake-genuine page_scrape.
    perfumeskuwait.com  10.95 BHD (KWD, converted_usd)  ->  8.90 ("KD",
                        page_scrape)
    faces.ae           569.64 BHD (AED, page_scrape)    -> 238.76 (converted_usd)
    perfumeqatar.com    same amount, provenance relabelled to a fake-genuine
                        page_scrape

perfumeqatar is the general shape of the damage: the branches below OG emit
``page_scrape`` off whatever currency string the page wrote -- an Arabic-script
symbol or a local abbreviation like "KD" -- which no rate table maps, so the
conversion silently no-ops and an unconverted foreign amount ships labelled as a
genuine local shelf price. The OG branch converts and labels honestly.

What SURVIVES under `ENABLE_OG_BRANCH_FIXES` is (a) the tri-state `in_stock` and
(b) the comma-decimal OG parse; both are pinned in
``tests/test_og_branch_fixes.py``. This file pins only the ORDER.

No network. The synthetic and structural assertions run everywhere; the
corpus-anchored ones skip when ``_proof/`` is absent (it is git-excluded).
"""

import hashlib
import inspect
import json
import os
import re

import pytest

from app.services import price_service
from app.services.price_service import extract_price_from_html

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_HTML = os.path.join(REPO_ROOT, "_proof", "html")
CORPUS_SWEEP = os.path.join(REPO_ROOT, "_proof", "sweep2_curl_cffi.jsonl")

BOTH_FLAG_STATES = pytest.mark.parametrize("og_flag", ["true", "false"])


@pytest.fixture(autouse=True)
def _isolate_extraction(monkeypatch):
    """Every assertion here is about EXTRACTION, so the exact-identity gate is
    OFF -- with it ON the gate rejects most real pages and everything returns
    None, which would make these tests pass vacuously."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")


def _strip_comments(src):
    return "\n".join(
        line for line in src.splitlines() if not line.strip().startswith("#")
    )


# ---------------------------------------------------------------------------
# STRUCTURAL -- the call site itself, so a reorder fails even when no fixture
# happens to cover the page shape that would regress.
# ---------------------------------------------------------------------------


class TestOgCallSitePosition:
    @staticmethod
    def _cascade_source():
        return inspect.getsource(price_service.extract_price_from_html)

    def test_exactly_one_og_call_site(self):
        """(c) shipped TWO `_extract_og_price` call sites -- one at Priority 2
        for flag-OFF and one at the bottom for flag-ON -- and chose between them
        on the flag. One call site means the position cannot be flag-dependent.
        """
        src = _strip_comments(self._cascade_source())
        assert src.count("_extract_og_price(") == 1, (
            "extract_price_from_html must call _extract_og_price exactly once; "
            "a second call site is how the (c) reorder was smuggled in"
        )

    def test_og_is_called_before_microdata_and_woocommerce(self):
        """OG at Priority 2, above microdata (3) and the Woo span (4) -- the
        exact cascade position it occupies on 8adaefb."""
        src = _strip_comments(self._cascade_source())
        og_at = src.index("_extract_og_price(")
        micro_at = src.index("_extract_microdata_price(")
        woo_at = src.index("_extract_woocommerce_price(")
        assert og_at < micro_at, "OG must run BEFORE microdata"
        assert og_at < woo_at, "OG must run BEFORE the WooCommerce span"

    def test_the_og_call_is_not_flag_gated(self):
        """The OG branch's position must not depend on the flag. If a future
        edit re-gates it, this catches it before any fixture does."""
        src = _strip_comments(self._cascade_source())
        head = src[: src.index("_extract_og_price(")]
        assert "og_branch_fixes_enabled()" not in head, (
            "the OG branch position must not depend on ENABLE_OG_BRANCH_FIXES"
        )


# ---------------------------------------------------------------------------
# SYNTHETIC -- OG outranks microdata and the Woo span in BOTH flag states.
# ---------------------------------------------------------------------------

QUERY = "Oud Elite So Black Eau de Parfum 100ml"
DOMAIN = "bh.oudelite.com"
URL = "https://bh.oudelite.com/product/so-black"

_OG_PLUS_MICRODATA = """<html><head>
  <meta property="og:price:amount" content="99.000">
  <meta property="og:price:currency" content="BHD">
</head><body>
  <div itemscope itemtype="https://schema.org/Product">
    <span itemprop="name">Oud Elite So Black Eau de Parfum 100ml</span>
    <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
      <span itemprop="price" content="12.500">12.500</span>
      <meta itemprop="priceCurrency" content="BHD" />
    </div>
  </div>
</body></html>"""

_OG_PLUS_WOO = """<html><head>
  <meta property="og:price:amount" content="99.000">
  <meta property="og:price:currency" content="BHD">
</head><body>
  <p class="price"><span class="woocommerce-Price-amount amount"><bdi>2.110 <span class="woocommerce-Price-currencySymbol">BHD </span></bdi></span></p>
</body></html>"""


class TestOgOutranksTheLowerBranches:
    @BOTH_FLAG_STATES
    def test_og_beats_microdata(self, monkeypatch, og_flag):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        res = extract_price_from_html(_OG_PLUS_MICRODATA, QUERY, "BHD", DOMAIN, URL)
        assert res is not None
        assert res["amount"] == pytest.approx(99.000)
        assert res["confidence"] == 0.9  # OG's confidence, not microdata's 0.8

    @BOTH_FLAG_STATES
    def test_og_beats_the_woocommerce_span(self, monkeypatch, og_flag):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        res = extract_price_from_html(
            _OG_PLUS_WOO, QUERY, "BHD", "fragrancebh.com", URL,
        )
        assert res is not None
        assert res["amount"] == pytest.approx(99.000)

    @BOTH_FLAG_STATES
    def test_jsonld_still_outranks_og(self, monkeypatch, og_flag):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        html = """<html><head>
          <meta property="og:price:amount" content="99.000">
          <meta property="og:price:currency" content="BHD">
          <script type="application/ld+json">
            {"@type":"Product","name":"Oud Elite So Black Eau de Parfum 100ml",
             "offers":{"@type":"Offer","price":"41.000","priceCurrency":"BHD",
                       "availability":"https://schema.org/InStock"}}
          </script>
        </head><body></body></html>"""
        res = extract_price_from_html(html, QUERY, "BHD", DOMAIN, URL)
        assert res is not None
        assert res["amount"] == pytest.approx(41.000)

    @BOTH_FLAG_STATES
    def test_microdata_still_reached_when_og_is_silent(self, monkeypatch, og_flag):
        """Reverting (c) must not make the lower branches unreachable -- a page
        with NO OG price still falls through to microdata."""
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        no_og = "<html><head></head>" + _OG_PLUS_MICRODATA.split("</head>")[1]
        res = extract_price_from_html(no_og, QUERY, "BHD", DOMAIN, URL)
        assert res is not None
        assert res["amount"] == pytest.approx(12.500)

    @BOTH_FLAG_STATES
    def test_woocommerce_still_reached_when_og_is_silent(self, monkeypatch, og_flag):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        no_og = "<html><head></head>" + _OG_PLUS_WOO.split("</head>")[1]
        res = extract_price_from_html(no_og, QUERY, "BHD", "fragrancebh.com", URL)
        assert res is not None
        assert res["amount"] == pytest.approx(2.110)


# ---------------------------------------------------------------------------
# The DAMAGE SHAPE, synthetic -- an unmapped local currency abbreviation below
# the OG branch ships unconverted AND relabelled genuine. Reproduces the
# perfumeskuwait ("KD") failure without touching the corpus.
# ---------------------------------------------------------------------------


class TestUnmappedCurrencyBelowOgNeverOutranksOg:
    @BOTH_FLAG_STATES
    def test_woo_span_in_an_unmapped_currency_does_not_win(self, monkeypatch, og_flag):
        """perfumeskuwait shape: OG says 30 KWD, which converts to BHD honestly;
        the Woo span says "8.90 KD", which no rate table maps, so it would ship
        unconverted AND labelled page_scrape."""
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        html = """<html><head>
          <meta property="og:price:amount" content="30.000">
          <meta property="og:price:currency" content="KWD">
        </head><body>
          <p class="price"><span class="woocommerce-Price-amount amount"><bdi>8.90 <span class="woocommerce-Price-currencySymbol">KD</span></bdi></span></p>
        </body></html>"""
        res = extract_price_from_html(
            html, "Eternity for Men edT 100ml", "BHD",
            "perfumeskuwait.com", "https://www.perfumeskuwait.com/product/x/",
        )
        assert res is not None
        assert res["amount"] != pytest.approx(8.90), "the unmapped Woo span won"
        assert res["original_currency"] == "KWD"
        assert res["source_method"] == "converted_usd", (
            "a converted foreign price must never be labelled a genuine page_scrape"
        )


# ---------------------------------------------------------------------------
# CORPUS-ANCHORED -- the pages the reorder actually damaged, read straight off
# the cached HTML. Zero network. Skipped when _proof/ is absent.
# ---------------------------------------------------------------------------

_CORPUS_MISSING = not (
    os.path.isdir(CORPUS_HTML) and os.path.isfile(CORPUS_SWEEP)
)
requires_corpus = pytest.mark.skipif(
    _CORPUS_MISSING, reason="_proof/ cached corpus not present (git-excluded)",
)


def _corpus_rows():
    with open(CORPUS_SWEEP, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def _corpus_row(domain):
    for row in _corpus_rows():
        if row.get("domain") == domain:
            return row
    raise AssertionError("no cached sweep row for %s" % domain)


def _cached_html(url):
    h = hashlib.sha1(("curl_cffi|" + url).encode("utf-8")).hexdigest()
    with open(
        os.path.join(CORPUS_HTML, h + ".html"), encoding="utf-8", errors="replace"
    ) as fh:
        return fh.read()


def _extract_row(row, target_currency="BHD"):
    return extract_price_from_html(
        _cached_html(row["url"]),
        row.get("derived_query") or row.get("page_title") or "",
        target_currency,
        row.get("domain") or "",
        row["url"],
    )


# (domain, expected amount in BHD, expected original_currency, expected method)
# -- the 8adaefb values, re-measured on this tree with
# ENABLE_EXACT_PRICE_GATE=false and every wave flag at its default.
_DAMAGED_PAGES = [
    ("oudworlds.com", 19.54, "OMR", "converted_usd"),
    ("perfumeskuwait.com", 10.95, "KWD", "converted_usd"),
    # faces.ae is the one whose damage came from the microdata "reorder
    # preconditions" rather than the reorder itself: microdata ALREADY wins here
    # at Priority 3, and document-order-instead-of-max picked a different node
    # (569.64 -> 238.76) while the relabel made it converted_usd. Both went with
    # (c), so this page pins them too.
    ("faces.ae", 569.64, "USD", "page_scrape"),
]


@requires_corpus
class TestCorpusPagesTheReorderDamaged:
    @BOTH_FLAG_STATES
    @pytest.mark.parametrize(
        "domain,amount,orig_currency,method", _DAMAGED_PAGES,
        ids=[d for d, _a, _c, _m in _DAMAGED_PAGES],
    )
    def test_amount_and_provenance_are_flag_invariant(
        self, monkeypatch, og_flag, domain, amount, orig_currency, method,
    ):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        res = _extract_row(_corpus_row(domain))
        assert res is not None, "%s must still produce a price" % domain
        assert res["amount"] == pytest.approx(amount, rel=1e-3)
        assert res["original_currency"] == orig_currency
        assert res["source_method"] == method

    @BOTH_FLAG_STATES
    def test_perfumeqatar_provenance_is_not_relabelled_genuine(
        self, monkeypatch, og_flag,
    ):
        """Same amount either way -- the reorder's damage here was PURELY the
        provenance relabel, which the genuine-BH-share KPI would have counted."""
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        res = _extract_row(_corpus_row("perfumeqatar.com"))
        assert res is not None
        assert res["source_method"] == "converted_usd"
        assert res["original_currency"] == "QAR"


@requires_corpus
class TestWholeCorpusFlagDiffIsOnlyStockAndCommaDecimals:
    """The wave's acceptance bar, executable: flipping ENABLE_OG_BRANCH_FIXES
    over all 92 cached pages may change ONLY `in_stock` (defect (a)) and may
    only ADD results that previously threw on a comma decimal (defect (b)).
    Any amount, currency or provenance change on a page that already had a
    price is a re-landed reorder."""

    # 92 pages x 2 flag states x 3 tests is 550-odd BeautifulSoup parses of real
    # PDP HTML; memoize so the file stays under a few seconds.
    _MEMO = {}

    @classmethod
    def _sweep(cls, flag):
        if flag in cls._MEMO:
            return cls._MEMO[flag]
        os.environ["ENABLE_OG_BRANCH_FIXES"] = flag
        results = {}
        for row in _corpus_rows():
            url = row.get("url")
            if not url:
                continue
            h = hashlib.sha1(("curl_cffi|" + url).encode("utf-8")).hexdigest()
            if not os.path.exists(os.path.join(CORPUS_HTML, h + ".html")):
                continue
            try:
                results[url] = _extract_row(row)
            except Exception as exc:  # noqa: BLE001 - a throw IS defect (b)
                results[url] = {"__threw__": type(exc).__name__}
        cls._MEMO[flag] = results
        return results

    def _both_states(self, monkeypatch):
        # monkeypatch owns the restore; _sweep sets the value it needs because
        # the memo means the two sweeps do not both run on every test.
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", "false")
        off = self._sweep("false")
        on = self._sweep("true")
        assert off and len(off) == len(on)
        return off, on

    def test_only_permitted_differences(self, monkeypatch):
        off, on = self._both_states(monkeypatch)
        offences = []
        for url, before in off.items():
            after = on[url]
            if before == after:
                continue
            if before is None:
                # (b) -- a comma decimal that used to be unparseable may now
                # produce a price. Never the reverse.
                continue
            if after is None:
                offences.append("%s: lost its price entirely" % url)
                continue
            for field in set(before) | set(after):
                if field == "in_stock":
                    continue  # (a) -- the only permitted mutation
                if before.get(field) != after.get(field):
                    offences.append(
                        "%s: %s %r -> %r"
                        % (url, field, before.get(field), after.get(field))
                    )
        assert not offences, (
            "ENABLE_OG_BRANCH_FIXES changed something other than in_stock on a "
            "page that already had a price:\n  " + "\n  ".join(offences)
        )

    def test_the_in_stock_fix_is_actually_exercised(self, monkeypatch):
        """Guards against the diff test passing vacuously."""
        off, on = self._both_states(monkeypatch)
        flipped = [
            u for u, b in off.items()
            if isinstance(b, dict) and b.get("in_stock") is True
            and isinstance(on[u], dict) and on[u].get("in_stock") is not True
        ]
        assert flipped, "no cached page exercised the (a) in_stock fix"

    def test_the_comma_decimal_fix_is_actually_exercised(self, monkeypatch):
        """Same, for defect (b)."""
        off, on = self._both_states(monkeypatch)
        rescued = [
            u for u, b in off.items()
            if b is None and isinstance(on[u], dict) and on[u].get("amount")
        ]
        assert rescued, "no cached page exercised the (b) comma-decimal fix"


# ---------------------------------------------------------------------------
# The flag docstring must stop advertising a reorder that no longer exists.
# ---------------------------------------------------------------------------


def test_flag_docstring_no_longer_claims_a_reorder():
    doc = price_service.og_branch_fixes_enabled.__doc__ or ""
    assert "JSON-LD -> microdata -> WooCommerce -> OG" not in doc, (
        "the flag docstring still advertises the reverted (c) cascade order"
    )
    assert re.search(r"\brevert", doc, re.I), (
        "the flag docstring must record that (c) was reverted"
    )
