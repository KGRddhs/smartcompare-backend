"""M10 UNIT A2 — WALL-SIGNATURE ANCHORING in ``classify_capture``.

THE DEFECT THIS PINS, measured 2026-08-31 over all 414 cached pages of the two
read-only corpora (92 Gulf rows from ``_proof/sweep2_curl_cffi.jsonl`` +
``_proof/html/``, 322 global rows from ``_proof/global/corpus.json`` +
``_proof/global/html|_dach_html/``), zero network:

    classify_capture(html, None, status) over 414
      -> no_structured_price 353, walled 44, empty_shell 17
    of the 44 walled: 37 are STATUS-driven (status in _WALL_HTTP_STATUS)
                       7 are SIGNATURE-driven, and FOUR OF THE SEVEN ARE WRONG.

``_WALL_SIGNATURES`` was an UNANCHORED substring alternation over the first
200,000 chars of the body, and its first alternative was the bare phrase
``access denied``. Adjudicated against the corpora's OWN recorded
``blocked`` / ``block_kind`` / ``has_price`` flags, the seven fires are:

  | host                | status | bytes   | phrase        | offset  | verdict |
  |---------------------|--------|---------|---------------|---------|---------|
  | om.swissarabian.com | 200    | 611,667 | access denied | 102,029 | FALSE + |
  | www.walmart.com x2  | 200    | ~480KB  | perimeterx    | ~4,600  | FALSE + |
  | www.macys.com       | 404    | 16,098  | access denied | 8,722   | FALSE + |
  | www.boots.com       | 200    | 6,183   | _Incapsula_   | 4,996   | TRUE    |
  | www.sallybeauty.com | 200    | 6,608   | px-captcha    | 369     | TRUE    |
  | www.dillards.com    | 200    | 378     | Access Denied | 24      | TRUE    |

and the four false positives fire on text that is verbatim NOT a wall:

  * ``om.swissarabian.com`` — a COMMENTED-OUT ``console.log('Service access
    denied based on billing status')`` inside a Shopify popup app's inline JS,
    on a 611KB page whose ``<title>`` is the product and whose Gulf corpus row
    records ``verdict CAPTURED, structurally_blocked false``;
  * ``www.walmart.com`` x2 — ``*.perimeterx.net`` inside a Content-Security-
    Policy HOST ALLOWLIST, on two real PDPs the corpus records as
    ``blocked false, usable_pdp true, has_price true``. This is the SAME
    failure mode the table's own comment already documented for
    ``/cdn-cgi/challenge``: a bot-vendor string that ships on served pages;
  * ``www.macys.com`` — ``// ... so we got an access denied.`` in a JS comment
    on a genuine 404 whose ``<title>`` is "Not Found - Macy's".

WHY IT HAD NOT SHIPPED A VISIBLE BUG, and why that is not a defence:
``classify_capture`` returns ``CAPTURE_OK`` BEFORE any wall test whenever
``price`` carries a positive finite amount, and three of the four false
positives are pages that do carry a price. The false positive materialises the
moment the extractor returns None for one of them — an identity pend, a
currency mismatch, a multiplicity pend, a query the page does not carry. Then a
real 611KB served page is labelled ``walled``, and ``CAPTURE_WALLED``'s
documented meaning ("There is no page behind this response") issues the most
expensive instruction in the outcome vocabulary — BUY A DIFFERENT FETCH CHANNEL
— about a page free curl already holds in full.

THE FIX, behind ``ENABLE_WALL_SIGNATURE_ANCHOR`` (default OFF): split the table
in two. The ambiguous PHRASES (``access denied`` and friends) move to
``_WALL_TITLE_SIGNATURES``, matched against the ``<title>`` and the ``<h1>``/
``<h2>`` text ONLY — a wall says what it is immediately. The unambiguous VENDOR
tokens stay unanchored, with bare ``perimeterx`` narrowed to
``perimeterx-container`` (the class PerimeterX puts on the interstitial itself).
The precedent is in this same file: ``_NOT_A_PDP_ERROR_TITLE_RE`` is anchored at
the start of the ``<title>`` and its comment names this exact swissarabian page
as the reason. A2 applies that decision to the wall table, which was written
first and never got it.

MEASURED ACCEPTANCE over the same 414 pages (``scripts/measure_wall_anchoring.py``):
flag OFF walled = 44, flag ON walled = 40; DROPPED is exactly the four false
positives above; ADDED is EMPTY; the three retained signature-driven walls are
exactly boots, sallybeauty and dillards. Class B below is that no-false-negative
bar expressed as tests.

Fixtures: ``tests/fixtures/wall_anchoring/`` — cut from the real cached bytes
(the three true walls are whole, byte for byte; the false positives keep their
own ``<title>``, ``<h1>`` and the exact ``<script>``/CSP tag carrying the
phrase). Provenance and per-file padding in that directory's ``SOURCES.json``.
"""
import inspect
import os

import pytest

from app.services import price_service as ps

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "wall_anchoring")

SWISS = "om_swissarabian_com_js_comment_access_denied.html"
WALMART = "www_walmart_com_csp_allowlist_perimeterx_mon_paris.html"
MACYS = "www_macys_com_404_js_comment_access_denied.html"
DILLARDS = "www_dillards_com_title_access_denied_wall.html"
BOOTS = "www_boots_com_incapsula_interstitial_wall.html"
SALLY = "www_sallybeauty_com_px_captcha_wall.html"


def load(name):
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as fh:
        return fh.read()


def _anchor(monkeypatch, value):
    monkeypatch.setenv("ENABLE_WALL_SIGNATURE_ANCHOR", value)


BOTH_MODES = pytest.mark.parametrize("flag", ["false", "true"])


# ===========================================================================
# A — THE FOUR MEASURED FALSE POSITIVES
#
# Each asserts BOTH modes: flag OFF reproduces today's wrong answer (so the
# rollback is pinned and the defect stays documented), flag ON is the repair.
# ===========================================================================
def test_a_a_js_comment_access_denied_is_not_a_wall(monkeypatch):
    """om.swissarabian.com: 611KB served product page, HTTP 200, Gulf corpus
    verdict CAPTURED. Its only ``access denied`` is inside a commented-out
    ``console.log`` at offset 102,029 — 100KB into the body, in a Shopify popup
    app's inline JS. The cut keeps the page's own <title>, its first <h1> and
    that whole <script> block."""
    html = load(SWISS)
    assert len(html) > ps._EMPTY_SHELL_MAX_BYTES, (
        "the cut must clear the shell threshold or the signature rung is "
        "never reached and this test proves nothing")
    _anchor(monkeypatch, "false")
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_WALLED
    _anchor(monkeypatch, "true")
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_NO_STRUCTURED_PRICE


def test_a_b_a_csp_allowlist_perimeterx_is_not_a_wall(monkeypatch):
    """www.walmart.com Mon Paris PDP: HTTP 200, corpus ``blocked false,
    usable_pdp true, has_price true, jsonld_price "Now $85.50"``. Its only
    ``perimeterx`` is ``*.perimeterx.net`` inside a Content-Security-Policy
    host allowlist. Bare ``perimeterx`` must narrow to the interstitial's own
    ``perimeterx-container``."""
    html = load(WALMART)
    assert "perimeterx.net" in html and "perimeterx-container" not in html
    _anchor(monkeypatch, "false")
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_WALLED
    _anchor(monkeypatch, "true")
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_NO_STRUCTURED_PRICE


def test_a_c_a_404_with_access_denied_in_a_js_comment_is_not_a_wall(monkeypatch):
    """www.macys.com: a genuine 404 (<title>Not Found - Macy's</title>) whose
    ``access denied`` is a JS comment about IE's document.domain. 404 is not in
    ``_WALL_HTTP_STATUS``, and 16KB of 404 is an empty shell — never a wall,
    because "buy a different fetch channel" is the wrong instruction for a page
    that does not exist."""
    html = load(MACYS)
    assert len(html) < ps._EMPTY_SHELL_MAX_BYTES
    _anchor(monkeypatch, "false")
    assert ps.classify_capture(html, None, 404) == ps.CAPTURE_WALLED
    _anchor(monkeypatch, "true")
    assert ps.classify_capture(html, None, 404) == ps.CAPTURE_EMPTY_SHELL


def test_a_d_the_phrase_stays_inert_wherever_the_body_puts_it(monkeypatch):
    """The class, not the four instances: an ambiguous phrase in ordinary body
    prose is not a wall either. This is what stops the next reader "fixing" the
    anchoring by re-widening it to <p> text."""
    _anchor(monkeypatch, "true")
    html = ("<html><head><title>Sauvage Eau de Toilette 100ml</title></head>"
            "<body><h1>Sauvage Eau de Toilette</h1>"
            "<p>If your card issuer returns access denied, try another card.</p>"
            + "<p>filler</p>" * 4000 + "</body></html>")
    assert len(html) > ps._EMPTY_SHELL_MAX_BYTES
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_NO_STRUCTURED_PRICE


# ===========================================================================
# B — NO FALSE NEGATIVES. THIS IS THE ACCEPTANCE BAR.
#
# The corpus gate (scripts/measure_wall_anchoring.py) proves DROPPED is exactly
# the four above and ADDED is empty over all 414 pages. These pin the three
# signature-driven walls that must survive, plus the 37 status-driven ones a
# regex change cannot reach.
# ===========================================================================
@BOTH_MODES
def test_b_a_dillards_title_access_denied_is_still_a_wall(monkeypatch, flag):
    """378 bytes, ``<TITLE>Access Denied</TITLE>`` + ``<H1>Access Denied</H1>``.
    The one true consumer of the phrase, and it has it exactly where a wall
    puts it. Corpus: blocked true, akamai_edge_denied."""
    _anchor(monkeypatch, flag)
    assert ps.classify_capture(load(DILLARDS), None, 200) == ps.CAPTURE_WALLED


@BOTH_MODES
def test_b_b_boots_incapsula_interstitial_is_still_a_wall(monkeypatch, flag):
    """``_Incapsula_Resource`` in the body AND ``<title>Pardon Our
    Interruption</title>`` — caught by the unanchored vendor token and,
    independently, by the anchored family. Corpus: blocked true,
    imperva_incapsula."""
    html = load(BOOTS)
    assert "_Incapsula_Resource" in html
    _anchor(monkeypatch, flag)
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_WALLED


@BOTH_MODES
def test_b_c_sallybeauty_px_captcha_is_still_a_wall(monkeypatch, flag):
    """``#px-captcha`` + ``.perimeterx-container`` in the interstitial's own
    stylesheet, ``<title>Access to this page has been denied.</title>``. Three
    independent catches; narrowing bare ``perimeterx`` costs none of them.
    Corpus: blocked true, perimeterx_human."""
    html = load(SALLY)
    assert "px-captcha" in html and "perimeterx-container" in html
    _anchor(monkeypatch, flag)
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_WALLED


@BOTH_MODES
@pytest.mark.parametrize("status", sorted(ps._WALL_HTTP_STATUS))
def test_b_d_every_status_driven_wall_is_untouched(monkeypatch, flag, status):
    """37 of the 44 walls in the corpus are named by status alone, on bodies
    carrying no wall phrase at all. A regex change cannot reach them and this
    says so for every member of ``_WALL_HTTP_STATUS``."""
    _anchor(monkeypatch, flag)
    assert ps.classify_capture("<html>ordinary page</html>", None, status) == (
        ps.CAPTURE_WALLED)


@BOTH_MODES
@pytest.mark.parametrize("body", [
    "<html><head><title>Just a moment...</title></head><body></body></html>",
    "<html><body><script>window.__CF$cv$params={};__cf_chl_opt={};</script></body></html>",
    "<html><body><div id=\"cf-browser-verification\"></div></body></html>",
    "<html><body>Please verify you are human to continue.</body></html>",
    "<html><body>Our systems have detected unusual traffic from your network.</body></html>",
    "<html><body>Request unsuccessful. Incapsula incident ID: 0-1</body></html>",
    "<html><body><script>_Incapsula_Resource?SWJIYLWA=5</script></body></html>",
    "<html><body>Enable JavaScript and cookies to continue</body></html>",
    "<html><body><div class=\"perimeterx-container\"></div></body></html>",
    "<html><body><div id=\"distil_r_captcha\"></div></body></html>",
    "<html><head><title>Attention Required! | Cloudflare</title></head><body></body></html>",
])
def test_b_e_every_unambiguous_vendor_token_still_fires(monkeypatch, flag, body):
    """One case per surviving alternative of the unanchored table. The
    narrowing removed exactly two things — bare ``access denied`` (which moved,
    see class C) and bare ``perimeterx`` (which narrowed) — and nothing else in
    the table may have moved with them."""
    _anchor(monkeypatch, flag)
    assert ps.classify_capture(body, None, 200) == ps.CAPTURE_WALLED


@BOTH_MODES
@pytest.mark.parametrize("zone", ["title", "h1", "h2"])
@pytest.mark.parametrize("phrase", [
    "Access Denied",
    "Access to this page has been denied.",
    "Pardon Our Interruption",
    "Attention Required!",
    "You have been blocked",
    "Are you a human?",
])
def test_b_f_an_ambiguous_phrase_in_the_anchor_zone_is_a_wall(
        monkeypatch, flag, zone, phrase):
    """The anchored family, positively: every phrase it owns is a wall when it
    is what the page SAYS IT IS. Both flag modes, because the two the legacy
    table already carried (``you have been blocked``, ``are you a human``) must
    not regress and the rest must not be reachable only by luck."""
    _anchor(monkeypatch, flag)
    if zone == "title":
        body = "<html><head><title>%s</title></head><body></body></html>" % phrase
    else:
        body = "<html><body><%s>%s</%s></body></html>" % (zone, phrase, zone)
    if flag == "false" and phrase not in (
            "Access Denied", "You have been blocked", "Are you a human?"):
        pytest.skip("not in the pre-A2 table; class C pins what OFF does")
    assert ps.classify_capture(body, None, 200) == ps.CAPTURE_WALLED


# ===========================================================================
# C — THE FLAG. OFF must be byte-identical to the pre-unit behaviour.
# ===========================================================================
def test_c_a_flag_off_is_the_legacy_table_verbatim():
    """The rollback contract: with the flag off ``classify_capture`` consults
    the LITERAL pre-A2 pattern. Pinned as source text so a later edit to the
    narrowed table cannot silently drift the rollback path with it."""
    assert ps._WALL_SIGNATURES.pattern == (
        r"access denied"
        r"|attention required!\s*\|\s*cloudflare"
        r"|cf-browser-verification|cf_chl_opt|__cf_chl_"
        r"|<title>\s*just a moment"
        r"|you (?:have been|are) blocked"
        r"|px-captcha|perimeterx|distil_r_captcha|_incapsula_|incap_ses"
        r"|are you a (?:human|robot)|unusual traffic (?:from|has)"
        r"|request unsuccessful\.?\s*incapsula"
        r"|verify you are (?:a )?human"
        r"|enable javascript and cookies to continue"
    )


def test_c_b_the_narrowed_table_differs_by_exactly_two_edits():
    """``access denied`` MOVED to the anchored family; bare ``perimeterx``
    NARROWED to ``perimeterx-container``. Nothing else."""
    legacy, narrowed = ps._WALL_SIGNATURES.pattern, ps._WALL_SIGNATURES_NARROWED.pattern
    assert narrowed == legacy.replace("access denied|", "", 1).replace(
        "|perimeterx|", "|perimeterx-container|", 1)


def test_c_c_the_flag_is_read_per_call_never_cached_at_import(monkeypatch):
    """CLAUDE.md house rule 1 — Railway flips flags without a restart."""
    html = load(SWISS)
    _anchor(monkeypatch, "false")
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_WALLED
    _anchor(monkeypatch, "true")
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_NO_STRUCTURED_PRICE
    _anchor(monkeypatch, "false")
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_WALLED


def test_c_d_the_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("ENABLE_WALL_SIGNATURE_ANCHOR", raising=False)
    assert ps.wall_anchor_enabled() is False
    assert ps.classify_capture(load(SWISS), None, 200) == ps.CAPTURE_WALLED


@pytest.mark.parametrize("off_value", ["false", "0", "no", "off", "FALSE", "Off", ""])
def test_c_e_the_off_spellings_match_the_other_flags(monkeypatch, off_value):
    monkeypatch.setenv("ENABLE_WALL_SIGNATURE_ANCHOR", off_value)
    assert ps.wall_anchor_enabled() is False


@pytest.mark.parametrize("on_value", ["true", "1", "yes", "on", "TRUE", "On", " true "])
def test_c_f_the_on_spellings_match_the_other_flags(monkeypatch, on_value):
    monkeypatch.setenv("ENABLE_WALL_SIGNATURE_ANCHOR", on_value)
    assert ps.wall_anchor_enabled() is True


# ===========================================================================
# D — TOTALITY. ``classify_capture``'s standing contract, re-run with the new
# zone extraction in the path.
# ===========================================================================
@BOTH_MODES
@pytest.mark.parametrize("html", [
    pytest.param(None, id="none"),
    pytest.param("", id="empty"),
    pytest.param(b"bytes", id="bytes"),
    pytest.param(3, id="int"),
    pytest.param([], id="list"),
    pytest.param({}, id="dict"),
    pytest.param(object(), id="object"),
    pytest.param("<title>unclosed access denied", id="unclosed_title"),
    pytest.param("<title></title>" * 500, id="500_empty_titles"),
    pytest.param("<h1><h1><h1>access denied", id="nested_unclosed_h1"),
    pytest.param("<h1>" + "x" * 500000 + "</h1>", id="500kb_h1"),
    pytest.param("<html>" + "<h2>pad</h2>" * 5000 + "</html>", id="5000_h2"),
    pytest.param("<title\nfoo=bar>Access Denied</title>", id="newline_in_tag"),
])
def test_d_a_classify_capture_stays_total(monkeypatch, flag, html):
    _anchor(monkeypatch, flag)
    assert ps.classify_capture(html) in ps.CAPTURE_OUTCOMES


@BOTH_MODES
def test_d_b_a_4mb_body_is_still_bounded(monkeypatch, flag):
    """The scan cap is unchanged: both the vendor table and the anchor zone
    read ``text[:_WALL_SCAN_CHARS]`` and nothing else."""
    _anchor(monkeypatch, flag)
    html = "<html><body>" + ("filler " * 600000) + "</body></html>"
    assert len(html) > 4_000_000
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_NO_STRUCTURED_PRICE


@BOTH_MODES
def test_d_c_a_phrase_past_the_scan_cap_is_not_read(monkeypatch, flag):
    """Unchanged bound, stated: a <title> beyond 200,000 chars is out of scope
    for both families, exactly as it was before A2."""
    _anchor(monkeypatch, flag)
    html = ("<html><body>" + "x" * (ps._WALL_SCAN_CHARS + 10) +
            "<title>Access Denied</title></body></html>")
    assert ps.classify_capture(html, None, 200) == ps.CAPTURE_NO_STRUCTURED_PRICE


@BOTH_MODES
def test_d_d_a_price_still_beats_every_wall_signal(monkeypatch, flag):
    """The price-first rung at the top of ``classify_capture`` is untouched —
    it is why the four false positives never shipped a visible bug."""
    _anchor(monkeypatch, flag)
    for name in (SWISS, DILLARDS, BOOTS, SALLY):
        assert ps.classify_capture(
            load(name), {"amount": 12.5, "currency": "USD"}, 200) == ps.CAPTURE_OK


@BOTH_MODES
def test_d_e_the_outcome_vocabulary_is_unchanged(monkeypatch, flag):
    """A2 renames no outcome and adds none — it only stops one of them being
    issued wrongly."""
    _anchor(monkeypatch, flag)
    assert ps.CAPTURE_OUTCOMES == (
        ps.CAPTURE_OK, ps.CAPTURE_WALLED, ps.CAPTURE_EMPTY_SHELL,
        ps.CAPTURE_NO_STRUCTURED_PRICE, ps.CAPTURE_AMBIGUOUS_PRICE,
        ps.CAPTURE_NOT_A_PDP,
    )


# ===========================================================================
# E — THE M9 LOW: the docstring documented a parameter that does not exist.
# ===========================================================================
def test_e_a_the_docstring_documents_only_real_parameters():
    """``classify_capture``'s docstring carried a ``final_url`` paragraph
    inherited from UNIT F1, describing a parameter the function never accepted
    — and it directly contradicted the paragraph above it, which says the
    function is total over (html, price, status) "and nothing else". A
    docstring that names a parameter the signature does not have is a lie the
    next caller will act on."""
    names = set(inspect.signature(ps.classify_capture).parameters)
    assert names == {"html", "price", "http_status"}
    doc = inspect.getdoc(ps.classify_capture) or ""
    assert "final_url" not in doc
    for name in names:
        assert "``%s``" % name in doc, "%s is undocumented" % name


def test_e_b_the_docstring_still_names_the_not_a_pdp_boundary():
    """Deleting the stale paragraph must not delete the FACT it was carrying:
    NOT-A-PDP and AMBIGUOUS_PRICE are stamped elsewhere because they are not
    facts about the bytes this function is total over."""
    doc = inspect.getdoc(ps.classify_capture) or ""
    assert "CAPTURE_AMBIGUOUS_PRICE" in doc
    assert "extract_price_from_html" in doc
