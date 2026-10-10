"""Session 69 — the landing site's universal-link hand-off page (audit RT-8 / EXPO-06).

The backend builds every referral link on ``https://getmyez.com/c/<share token>?ref=<code>``
(``app/services/referral_service.py`` ``APP_BASE_URL``; the share token is the comparison
row's, which is NULL unless ``POST /share/{id}`` created one — so the live shape is usually
``/c/?ref=QR-XXXXXX``), and the app registers ``/c/*``, ``/r/*`` and ``/q/*`` as universal
links (``landing/.well-known/apple-app-site-association``) and as ``qaren://`` deep links
(``SmartCompareApp/src/navigation/linking.ts``). Before this unit the landing nginx served a
404 for all three families. On 2026-10-10 ``getmyez.com`` still served an unrelated page, so the page is
reachable only on the Railway landing host until Ahmed attaches the domain (runbook row 12).

This file pins the STATIC contract (nginx, Dockerfile, the page's structure and safety). The
hand-off logic itself is executed and pinned by the jest suite
``SmartCompareApp/__tests__/landing.handoff.s69.test.ts``. No network, no env, no ``app`` import.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LANDING = REPO / "landing"
NGINX_RAW = (LANDING / "nginx.conf.template").read_text(encoding="utf-8")
# Comments never configure anything: strip them before matching so a commented-out block
# cannot satisfy a rule.
NGINX = "\n".join(line.split("#", 1)[0] for line in NGINX_RAW.splitlines())
DOCKERFILE = (LANDING / "Dockerfile").read_text(encoding="utf-8")
PAGE = (LANDING / "open.html").read_text(encoding="utf-8")
AASA = json.loads((LANDING / ".well-known" / "apple-app-site-association").read_text(encoding="utf-8"))

FAMILIES = ("c", "r", "q")


def _aasa_paths() -> list[str]:
    return [p for d in AASA["applinks"]["details"] for p in d["paths"]]


@pytest.mark.parametrize("family", FAMILIES)
def test_nginx_serves_the_handoff_page_for_each_link_family(family):
    # `location ^~ /c/ { try_files /open.html =404; }` — a prefix match that wins over the
    # catch-all `location /` and serves the page for the token path itself.
    pattern = re.compile(r"location\s+\^~\s+/" + family + r"/\s*\{[^}]*try_files\s+/open\.html\s+=404;", re.S)
    assert pattern.search(NGINX), f"nginx has no ^~ /{family}/ location serving /open.html (comments stripped)"


def test_every_aasa_path_family_has_a_handoff_location():
    for p in _aasa_paths():
        fam = p.strip("/").split("/")[0]
        assert fam in FAMILIES, f"AASA path {p} has no hand-off family in the test's list"
        assert re.search(r"location\s+\^~\s+/" + fam + r"/", NGINX), f"AASA path {p} not served by nginx"


def test_dockerfile_copies_the_page_into_the_web_root():
    assert re.search(r"^COPY\s+open\.html\s+/usr/share/nginx/html/\s*$", DOCKERFILE, re.M), (
        "Dockerfile must COPY open.html — nginx try_files would 404 otherwise"
    )


def test_page_is_branded_myez_only():
    assert "MYEZ" in PAGE and "ميّز" in PAGE
    assert "Qaren" not in PAGE
    # The standalone old brand word — including its proclitic forms بقارن / لقارن / وقارن —
    # is gone; the embedded forms (مقارنة "comparison") are ordinary Arabic and stay. The same
    # regex the U-R landing fence applies (landing.brand.s69.test.ts wordRe).
    assert not re.search(r"(?<![؀-ۿ])[بلو]?قارن(?![؀-ۿ])", PAGE)


def test_page_hands_off_to_the_app_scheme_for_the_three_families():
    # The scheme prefix the app's linking config registers, the family regex covering exactly
    # c / r / q, the token-less referral branch, and the query string riding along.
    assert "'qaren://'" in PAGE
    assert re.search(r"FAMILY_RE = /\^\\/\(c\|r\|q\)\\/", PAGE), "the hand-off regex must cover /c/, /r/ and /q/"
    assert re.search(r"EMPTY_C_RE = /\^\\/c\\/\?\$/", PAGE), "the token-less /c/?ref= branch is missing"
    assert "'qaren://r/' + code" in PAGE
    assert "window.location.search" in PAGE
    assert "window.__myezHandoff = handoffTarget" in PAGE


def test_both_language_buttons_are_rewritten_and_default_to_the_scheme():
    for id_ in ("open-en", "open-ar"):
        assert re.search(rf'id="{id_}" href="qaren://"', PAGE), f"{id_} must default to qaren:// without JS"
    assert "['open-en', 'open-ar'].forEach" in PAGE


def test_page_carries_both_languages_arabic_first_for_arabic_browsers_and_no_external_scripts():
    assert re.search(r'<section lang="en" dir="ltr"', PAGE)
    assert re.search(r'<section lang="ar" dir="rtl"', PAGE)
    assert "main.insertBefore(ar, en)" in PAGE
    assert not re.search(r"<script\b[^>]*\bsrc=", PAGE), "no external scripts on the hand-off page"
    assert 'name="robots" content="noindex' in PAGE


def test_page_never_writes_markup_from_the_url():
    for banned in ("innerHTML", "document.write(", "eval("):
        assert banned not in PAGE, f"{banned} must not appear — the path is untrusted input"


def test_store_link_stays_hidden_until_the_app_store_url_is_filled():
    assert "var APP_STORE_URL = '';" in PAGE
    assert re.search(r'id="store-en" href="#" hidden', PAGE)
    assert re.search(r'id="store-ar" href="#" hidden', PAGE)
