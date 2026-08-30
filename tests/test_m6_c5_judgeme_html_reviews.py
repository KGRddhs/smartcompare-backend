"""UNIT C5 — judge.me server-HTML opportunistic enrichment
(ENABLE_JUDGEME_HTML_REVIEWS, default OFF).

MEASURED (M5 measure-judgeme/VERDICT.md, zero-network over the 92 cached Gulf PDPs
in _proof/html): judge.me's API is contractually closed, but the merchant's OWN
PDP HTML — which the crawler already holds — exposes, for a MINORITY of Gulf
judge.me hosts, an AGGREGATE RATING (9/24 via the badge data-average-rating /
data-number-of-reviews or JSON-LD AggregateRating) and some REVIEW TEXT (6/24, one
substantially: myperfumes.ae 28 bodies + JSON-LD Review[]). 18/24 are pure shells.
So this is a small enrichment, NOT a reviews spine: RATING PRIMARY, bodies
secondary, piggybacking HTML already in hand. Reads the merchant HTML ONLY — never
judge.me's API — so there is NO network call and this test is fully offline.

Pins:
  (a) STRICT multi-marker install detector (cdn.judge.me loader / jdgm.*= config /
      jdgm- node class / id=judgeme_product_reviews); the bare 'judge' substring is
      NEVER an install (M5: 6/6 false positives);
  (b) flag-OFF: the enrichment returns None and parses nothing (byte-identical);
  (c) myperfumes.ae FULL: JSON-LD AggregateRating 4.79/115 + review bodies, JSON-LD
      preferred over the DOM badge; the CSS 0.00 decoy selector is ignored;
  (d) swissarabian.com THIN: DOM badge 5.00/3 + 3 review bodies (author/title/body),
      a multi-line body collapses its <br>;
  (e) parfum.ae SHELL: DOM badge 4.15/169 (the main product, never a related badge),
      zero bodies -> rating only;
  (f) albayan junk: 5.00/1 from the widget-root badge, the lone U+0660 1-char body
      is dropped -> rating only;
  (g) a 0.00/0 badge is ABSENT (not a real zero) -> a pure-placeholder shell yields
      nothing usable -> None.
"""

import os

import pytest

import app.services.judgeme_service as judgeme

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "judgeme_c5")


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


MYPERFUMES = _read("myperfumes_full_jsonld.html")
SWISS = _read("swissarabian_thin_dom.html")
PARFUM = _read("parfum_ae_shell_badge_only.html")
ALBAYAN = _read("albayan_junk_body_1char.html")
SHELL = _read("shell_placeholder_zero_badge.html")
FALSE_POSITIVE = _read("false_positive_webpixel.html")
CONTROL = _read("no_judgeme_control.html")


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    # Default: flag OFF (each test opts in).
    monkeypatch.delenv("ENABLE_JUDGEME_HTML_REVIEWS", raising=False)


# ---------------------------------------------------------------------------
# (a) STRICT multi-marker install detector — never the bare 'judge' substring
# ---------------------------------------------------------------------------

def test_strict_detector_fires_on_real_installs():
    assert judgeme.has_judgeme_install(MYPERFUMES) is True
    assert judgeme.has_judgeme_install(SWISS) is True
    assert judgeme.has_judgeme_install(PARFUM) is True
    assert judgeme.has_judgeme_install(ALBAYAN) is True
    assert judgeme.has_judgeme_install(SHELL) is True


def test_strict_detector_rejects_bare_substring_false_positives():
    # The web-pixel page carries 'judge'/'Judge.me' + judgeme-reviews.css but NO
    # strict install marker — M5 proved this is a false positive.
    assert "judge" in FALSE_POSITIVE.lower()
    assert judgeme.has_judgeme_install(FALSE_POSITIVE) is False
    assert judgeme.has_judgeme_install(CONTROL) is False


def test_strict_detector_marker_kinds():
    # id=judgeme_product_reviews alone is a valid install (swiss-style capture).
    assert judgeme.has_judgeme_install(
        "<div id=\"judgeme_product_reviews\"></div>") is True
    # a jdgm- node class alone is valid.
    assert judgeme.has_judgeme_install("<div class='jdgm-widget'></div>") is True
    # cdn.judge.me loader alone is valid.
    assert judgeme.has_judgeme_install(
        "<script src='https://cdn.judge.me/loader.js'></script>") is True
    # a jdgm.*= config assignment alone is valid.
    assert judgeme.has_judgeme_install("<script>jdgm.CDN_HOST='x';</script>") is True
    # the bare substring is NOT enough.
    assert judgeme.has_judgeme_install("please do not judge my code") is False
    assert judgeme.has_judgeme_install('{"webPixelName":"Judge.me"}') is False


# ---------------------------------------------------------------------------
# (b) flag gate — OFF by default, read per call, parses nothing when OFF
# ---------------------------------------------------------------------------

def test_enabled_helper_reads_env_per_call(monkeypatch):
    monkeypatch.delenv("ENABLE_JUDGEME_HTML_REVIEWS", raising=False)
    assert judgeme.judgeme_reviews_enabled() is False
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "true")
    assert judgeme.judgeme_reviews_enabled() is True
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "off")
    assert judgeme.judgeme_reviews_enabled() is False


def test_flag_off_returns_none_even_for_a_full_page(monkeypatch):
    # Even the richest page yields nothing when the flag is OFF.
    assert judgeme.extract_judgeme_from_html(
        MYPERFUMES, url="https://myperfumes.ae/products/marwa") is None


# ---------------------------------------------------------------------------
# (c) myperfumes.ae FULL — JSON-LD aggregate + bodies, JSON-LD preferred
# ---------------------------------------------------------------------------

def test_myperfumes_jsonld_aggregate_and_reviews(monkeypatch):
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "true")
    res = judgeme.extract_judgeme_from_html(
        MYPERFUMES, url="https://myperfumes.ae/products/marwa")
    assert res is not None
    assert res["source"] == "judgeme"
    assert res["retailer"] == "myperfumes.ae"
    # aggregate rating is the PRIMARY target — JSON-LD wins over the DOM badge.
    rating = res["rating"]
    assert rating is not None
    assert rating["source"] == "jsonld"
    assert rating["average_score"] == pytest.approx(4.79)
    assert rating["total_reviews"] == 115
    # review bodies recovered from JSON-LD Review[].
    assert len(res["reviews"]) == 3
    first = res["reviews"][0]
    assert "packaging" in first["body"]
    assert first["score"] == 5
    assert first["date"] == "2026-07-21T05:57:34Z"
    assert first["source"] == "jsonld"


def test_myperfumes_css_zero_decoy_is_ignored(monkeypatch):
    # The <style> block carries .jdgm-prev-badge[data-average-rating='0.00'] — a CSS
    # selector, not a real element. The aggregate must NOT collapse to 0.00.
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "true")
    agg = judgeme.extract_judgeme_aggregate(MYPERFUMES)
    assert agg is not None
    assert agg["average_score"] == pytest.approx(4.79)


# ---------------------------------------------------------------------------
# (d) swissarabian.com THIN — DOM badge + 3 review bodies
# ---------------------------------------------------------------------------

def test_swissarabian_dom_badge_and_three_bodies(monkeypatch):
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "true")
    res = judgeme.extract_judgeme_from_html(SWISS, url="https://swissarabian.com/p")
    assert res is not None
    assert res["rating"]["source"] == "dom_badge"
    assert res["rating"]["average_score"] == pytest.approx(5.0)
    assert res["rating"]["total_reviews"] == 3
    reviews = res["reviews"]
    assert len(reviews) == 3
    assert reviews[0]["author"] == "Debra Sullivan Reguiti"
    assert reviews[0]["title"] == "Nice"
    assert reviews[0]["body"] == "Love the scent."
    assert reviews[0]["score"] == 5
    assert reviews[0]["source"] == "dom"
    # a multi-line body collapses its <br> to a single space (no double spacing).
    assert "  " not in reviews[1]["body"]
    assert reviews[1]["body"].startswith("The rose hair mist scents are beautiful")
    assert reviews[1]["body"].endswith("Very happy with my purchase.")


# ---------------------------------------------------------------------------
# (e) parfum.ae SHELL — main-product badge only, zero bodies
# ---------------------------------------------------------------------------

def test_parfum_shell_rating_only_main_badge(monkeypatch):
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "true")
    res = judgeme.extract_judgeme_from_html(PARFUM, url="https://parfum.ae/p")
    assert res is not None
    assert res["rating"]["source"] == "dom_badge"
    # the FIRST nonzero badge is the MAIN product (4.15/169), never a related one.
    assert res["rating"]["average_score"] == pytest.approx(4.15)
    assert res["rating"]["total_reviews"] == 169
    # SHELL: zero review bodies server-side -> rating only.
    assert res["reviews"] == []


# ---------------------------------------------------------------------------
# (f) albayan — widget-root badge, lone U+0660 body dropped
# ---------------------------------------------------------------------------

def test_albayan_junk_body_dropped_rating_kept(monkeypatch):
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "true")
    res = judgeme.extract_judgeme_from_html(ALBAYAN, url="https://albayanperfumes.com/p")
    assert res is not None
    # aggregate read from the .jdgm-rev-widg root (there is no .jdgm-prev-badge).
    assert res["rating"]["average_score"] == pytest.approx(5.0)
    assert res["rating"]["total_reviews"] == 1
    # the single 1-char (U+0660) body is dropped by the >1-char floor.
    assert res["reviews"] == []


# ---------------------------------------------------------------------------
# (g) 0.00/0 badge is ABSENT — pure placeholder shell yields nothing
# ---------------------------------------------------------------------------

def test_zero_badge_is_absent_not_a_real_zero(monkeypatch):
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "true")
    # aggregate helper returns None for a 0.00/0-only page.
    assert judgeme.extract_judgeme_aggregate(SHELL) is None
    # and the whole enrichment yields nothing usable.
    assert judgeme.extract_judgeme_from_html(SHELL, url="https://shell.example/p") is None


def test_false_positive_page_yields_nothing(monkeypatch):
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "true")
    assert judgeme.extract_judgeme_from_html(
        FALSE_POSITIVE, url="https://houseofperfumes.com/p") is None
    assert judgeme.extract_judgeme_from_html(
        CONTROL, url="https://plain.example/p") is None


# ---------------------------------------------------------------------------
# hygiene — never raises on junk / empty input
# ---------------------------------------------------------------------------

def test_never_raises_on_bad_input(monkeypatch):
    monkeypatch.setenv("ENABLE_JUDGEME_HTML_REVIEWS", "true")
    assert judgeme.extract_judgeme_from_html(None) is None
    assert judgeme.extract_judgeme_from_html("") is None
    assert judgeme.extract_judgeme_from_html(12345) is None  # type: ignore[arg-type]
    assert judgeme.has_judgeme_install(None) is False
    assert judgeme.extract_judgeme_aggregate(None) is None
