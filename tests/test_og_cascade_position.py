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
from app.services.exchange_rate_service import FALLBACK_RATES
from app.services.price_service import extract_price_from_html

#: The rate the flag-OFF microdata branch applies to its hardcoded "USD"
#: default -- used by the faces.ae selection pin to undo the conversion and
#: compare the two flag states on the page's OWN number.
_USD_TO_BHD = FALLBACK_RATES["USD"]

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

    @staticmethod
    def _record_call_order(monkeypatch):
        """Replace the three cascade branches with recording no-ops. Each
        returns None so the cascade runs to the bottom and every branch that
        WOULD be reached is observed, in the order the function reaches it."""
        seen = []
        for attr, label in (
            ("_extract_og_price", "og"),
            ("_extract_microdata_price", "microdata"),
            ("_extract_woocommerce_price", "woocommerce"),
        ):
            def _spy(*_args, _label=label, **_kwargs):
                seen.append(_label)
                return None
            monkeypatch.setattr(price_service, attr, _spy)
        return seen

    def test_og_is_called_before_microdata_and_woocommerce(self, monkeypatch):
        """OG at Priority 2, above microdata (3) and the Woo span (4) -- the
        exact cascade position it occupies on 8adaefb.

        ADJUDICATED IN UNIT F3 -- STALE PIN, and the assertion MECHANISM was
        replaced at this commit. Until now this test read the SOURCE TEXT of
        `extract_price_from_html` and asserted
        `src.index("_extract_og_price(") < src.index("_extract_microdata_price(")`.
        That comparison now fails UNCONDITIONALLY -- in both
        ENABLE_OG_BRANCH_FIXES states and regardless of behaviour -- because
        ENABLE_JSONLD_FIRST added a SECOND, flag-gated `_extract_microdata_price`
        call site physically ABOVE the OG branch, and `str.index` returns the
        FIRST occurrence. A source-position assertion cannot express "OG runs
        first under one flag and second under another"; a call-order one can,
        so the position assertion is REPLACED by a CALL-ORDER assertion here.

        The revert story it guards is unchanged. The "(c)" reorder that moved OG
        below microdata and the Woo span on ENABLE_OG_BRANCH_FIXES was reverted
        at d2a8900 for the four measured regressions in this module's docstring,
        and it stays reverted: with ENABLE_JSONLD_FIRST OFF the cascade is the
        8adaefb one, byte-identically (gate 1 re-proves that against a pristine
        8adaefb worktree). What the promotion under ENABLE_JSONLD_FIRST does NOT
        do is resurrect (c): (c) was gated on an OG-TAG flag and shipped with no
        guard, while the promoted microdata branch carries the OG-agreement
        guard (`_microdata_og_agreement_ok`) that stops it outbidding a
        disagreeing OpenGraph price -- which is why `TestOgOutranksTheLowerBranches`
        below still measures 99.000 in every flag state.
        """
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", "false")
        seen = self._record_call_order(monkeypatch)
        assert extract_price_from_html(
            _OG_PLUS_MICRODATA, QUERY, "BHD", DOMAIN, URL,
        ) is None, "the recording no-ops must let the cascade run to the bottom"
        assert seen == ["og", "microdata", "woocommerce"], (
            "OG must run BEFORE microdata and BEFORE the WooCommerce span"
        )

    def test_jsonld_first_calls_microdata_before_og(self, monkeypatch):
        """The other half of the same pin, added in UNIT F3: under
        ENABLE_JSONLD_FIRST (default ON) microdata IS promoted above OG -- by
        design and measured, with the OG-agreement guard attached. Pinning both
        orders is what makes the flag-OFF pin above a rollback surface rather
        than a statement about the source file's layout."""
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
        seen = self._record_call_order(monkeypatch)
        assert extract_price_from_html(
            _OG_PLUS_MICRODATA, QUERY, "BHD", DOMAIN, URL,
        ) is None
        assert seen == ["microdata", "og", "woocommerce"]

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
    @pytest.mark.parametrize(
        "jsonld_first,confidence",
        [("false", 0.9), ("true", 0.675)],
        ids=["jsonld_first_off", "jsonld_first_on"],
    )
    @BOTH_FLAG_STATES
    def test_og_beats_microdata(self, monkeypatch, og_flag, jsonld_first, confidence):
        """ADJUDICATED IN UNIT F3 -- STALE PIN on the confidence key only.

        The AMOUNT is intact at 99.000 in all four flag combinations, so OG
        still outranks the microdata 12.500 even where ENABLE_JSONLD_FIRST runs
        microdata FIRST -- the OG-agreement guard declines the disagreeing
        microdata candidate and the cascade falls through to OG, which is the
        whole point of that guard. What moved is `confidence`: this fixture's
        <body> never prints 99, so `_cross_check_price` marks the price
        unconfirmed and scales 0.9 down. Both values are pinned, and the
        original comment's real content -- "OG's confidence, not microdata's
        0.8" -- is asserted directly below so it cannot be read off a number.
        """
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", jsonld_first)
        res = extract_price_from_html(_OG_PLUS_MICRODATA, QUERY, "BHD", DOMAIN, URL)
        assert res is not None
        assert res["amount"] == pytest.approx(99.000)
        assert res["confidence"] != 0.8, "this is microdata's confidence, not OG's"
        assert res["confidence"] == confidence

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

# ENABLE_JSONLD_FIRST overrides for the table above -- ADJUDICATED IN UNIT F3.
#
# faces.ae is a currency-SILENT page: 252 visible "AED" strings and ZERO
# `itemprop=priceCurrency` nodes, on a brand LISTING URL (/en/brands/tom-ford)
# rather than a PDP. Measured across all four flag combinations, the microdata
# branch selects the SAME node and the SAME raw number, 1515, in every one of
# them -- the AMOUNT did not move, so this is not the (c) reorder returning and
# not an OG-flag leak. What moved is the LABEL, and with it whether a
# conversion happens at all:
#
#   ENABLE_JSONLD_FIRST off -> the branch's legacy hardcoded `"USD"` default
#                              (price_service.py, the `if not _first` arm), so
#                              1515 * 0.376 = 569.64 "converted out of USD".
#   ENABLE_JSONLD_FIRST on  -> `_currency_label_for` rung 3, the sharafdg rule:
#                              token missing AND no page evidence -> the ASK,
#                              so 1515 is read as already-BHD and not converted.
#
# Neither number is the truth (1515 AED is 155.14 BHD; the old "USD" was an
# arbitrary default, not a measurement), and this file is not the place to fix
# that -- its subject is ENABLE_OG_BRANCH_FIXES invariance, which HOLDS in all
# four combinations. Both measured values are pinned so the page cannot drift
# again unnoticed, and the residual -- rung 3 assuming the ask currency on a
# page that prints a foreign code only in VISIBLE TEXT -- is recorded here
# deliberately rather than blessed silently. `_page_currency_evidence` reads
# metas and JSON-LD offers only; teaching it visible text is its own change,
# measured on its own, against the whole corpus.
_JSONLD_FIRST_OVERRIDES = {
    "faces.ae": (1515.0, "BHD", "page_scrape"),
}


@requires_corpus
class TestCorpusPagesTheReorderDamaged:
    @pytest.mark.parametrize("jsonld_first", ["true", "false"])
    @BOTH_FLAG_STATES
    @pytest.mark.parametrize(
        "domain,amount,orig_currency,method", _DAMAGED_PAGES,
        ids=[d for d, _a, _c, _m in _DAMAGED_PAGES],
    )
    def test_amount_and_provenance_are_flag_invariant(
        self, monkeypatch, jsonld_first, og_flag,
        domain, amount, orig_currency, method,
    ):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", jsonld_first)
        if jsonld_first == "true" and domain in _JSONLD_FIRST_OVERRIDES:
            amount, orig_currency, method = _JSONLD_FIRST_OVERRIDES[domain]
        res = _extract_row(_corpus_row(domain))
        assert res is not None, "%s must still produce a price" % domain
        assert res["amount"] == pytest.approx(amount, rel=1e-3)
        assert res["original_currency"] == orig_currency
        assert res["source_method"] == method

    @pytest.mark.parametrize("jsonld_first", ["true", "false"])
    @BOTH_FLAG_STATES
    def test_faces_ae_selects_the_same_node_in_every_flag_state(
        self, monkeypatch, jsonld_first, og_flag,
    ):
        """The claim the override table above rests on, asserted rather than
        asserted-about: faces.ae's SELECTED raw number is 1515 in all four flag
        combinations. Under ENABLE_JSONLD_FIRST it ships as-is (labelled BHD);
        without it, it is converted out of the legacy "USD" default. If the
        SELECTION ever moves, this fails first and the override table is not
        the thing to edit."""
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", og_flag)
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", jsonld_first)
        res = _extract_row(_corpus_row("faces.ae"))
        assert res is not None
        native = (
            res["amount"] if res["original_currency"] == "BHD"
            else res["amount"] / _USD_TO_BHD
        )
        assert native == pytest.approx(1515.0, rel=1e-3)

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
