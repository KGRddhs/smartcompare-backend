"""U8 polish round (rulings UP4 + UP8, 2026-10-08): the minors and notes of adversaries A and B and
of the final adversary, each pinned here. A NEW file so tests/test_legal_docs_u8.py stays append-only
(rule 3); it reads the same documents and scripts and holds before and after the fill-in commit.

Pure ASCII: Arabic markers are \\u escapes (native review, D11); failure messages escape Arabic.

What is pinned (node -> item):
  text (EN + AR):  A5 prices/pending, A6 specifications, A7 country, A8 notification records,
                   A9 Google picture, A13 AR request bodies, A14 invite-link display name,
                   F3 App performance traces, F5 search-engine pictures, A16 d3 B 30-day sentence,
                   A17 support identity fork, fix Q5 processors.json comment, F2 the AR twin of fix A3
  renderer:        B3 link safety + marker pairs + write_regions round trip, B6 one node per refusal
                   class + the BOM, B7 --check on a missing page
  fill-in script:  B4 end to end on a temp copy (all-null rc 2, complete rc 0, idempotent, markup rc 3,
                   d3 flip, B1 rc 3), F1 ('' after a fill), B2 (a page without its end marker), B5 + A10
                   (unused / Arabic counsel values), A11 retention, A12 controller country / Cloudflare /
                   DPO, A15 referral sentence
  route:           B8 the '_' subtag (ar_SA)

The answers the polish round adds live under "placeholders" (the data file's top level is frozen by
the schema of tests/test_legal_docs_u8.py): CONTROLLER_COUNTRY, RETENTION_CLEANUP_LIVE,
REFERRAL_PUSH_DISPLAY_NAME_ONLY, DPO_CONTACT_DETAILS and _AR; null is each one's documented default.
"""
import asyncio
import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PRIVACY_EN = "app/legal/privacy_policy.md"
PRIVACY_AR = "app/legal/privacy_policy_ar.md"
TERMS_EN = "app/legal/terms_of_service.md"
TERMS_AR = "app/legal/terms_of_service_ar.md"
SUPPORT_EN = "app/legal/support_contact.md"
SUPPORT_AR = "app/legal/support_contact_ar.md"
SOURCES = (PRIVACY_EN, TERMS_EN, SUPPORT_EN, PRIVACY_AR, TERMS_AR, SUPPORT_AR)
PAGES = (
    "landing/privacy.html", "landing/terms.html", "landing/support.html",
    "landing/ar/privacy.html", "landing/ar/terms.html", "landing/ar/support.html",
)
RENDERER = "scripts/render_legal_landing.py"
FILL_SCRIPT = "scripts/fill_in_legal.py"
VARIANTS = "scripts/legal_variants_u8.json"
FILL_IN = "tests/fixtures/legal_fill_in_u8.json"
MANIFEST = "app/legal/processors.json"
REFILL_HINT = "restore the pre-fill markdown"
# The six sources BEFORE the fill-in (a committed snapshot). The temp-copy fill-in nodes fill it, not the
# live sources, so they hold after the fill-in commit too (the live sources then carry no token);
# test_polish_prefill_snapshot_tracks_the_documents ties it to the live sources.
PREFILL = "tests/fixtures/legal_prefill_u8"

# Arabic markers (native review, D11).
AR = {
    "A5_OLD": "\u0627\u0633\u062a\u0631\u0634\u0627\u062f\u064a\u0629",
    "A5_PENDING": "\u0642\u064a\u062f \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631",
    "A6_KNOWLEDGE": "\u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u0627\u0644\u0639\u0627\u0645\u0629 \u0644\u0646\u0645\u0648\u0630\u062c \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a",
    "A7_ONBOARDING": "\u0623\u0633\u0626\u0644\u0629 \u0627\u0644\u0628\u062f\u0627\u064a\u0629",
    "A7_NETWORK": "\u0645\u0648\u0642\u0639 \u0634\u0628\u0643\u062a\u0643",
    "A8_LABEL": "\u0633\u062c\u0644\u0627\u062a \u0627\u0644\u0625\u0634\u0639\u0627\u0631\u0627\u062a",
    "A9_PICTURE": "\u0635\u0648\u0631\u0629 \u0645\u0644\u0641\u0643 \u0627\u0644\u0634\u062e\u0635\u064a",
    "A13_OLD": "\u0648\u0644\u0627 \u0645\u062d\u062a\u0648\u0649 \u0627\u0644\u0637\u0644\u0628\u0627\u062a",
    "A13_NEW": "\u0648\u0644\u0627 \u0645\u062a\u0648\u0646 \u0627\u0644\u0637\u0644\u0628\u0627\u062a",
    "A14_INVITE": "\u064a\u0641\u062a\u062d\u0648\u0646 \u0631\u0627\u0628\u0637 \u062f\u0639\u0648\u0629 \u062a\u0634\u0627\u0631\u0643\u0647 \u0631\u0624\u064a\u0629 \u0627\u0633\u0645\u0643 \u0627\u0644\u0645\u0639\u0631\u0648\u0636",
    "A14_OLD_PRIVACY": "\u0648\u0631\u0624\u064a\u0629 \u0627\u0633\u0645\u0643 \u0627\u0644\u0645\u0639\u0631\u0648\u0636",
    "A14_OLD_TERMS": "\u0648\u064a\u0631\u0648\u0646 \u0627\u0633\u0645\u0643 \u0627\u0644\u0645\u0639\u0631\u0648\u0636",
    "A15_FALSE": "\u0627\u0644\u062c\u0632\u0621 \u0627\u0644\u0623\u0648\u0644 \u0645\u0646 \u0639\u0646\u0648\u0627\u0646 \u0628\u0631\u064a\u062f\u0643 \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a",
    "A16_LIMIT": "\u062d\u062f\u0651 \u0627\u0644\u062b\u0644\u0627\u062b\u064a\u0646 \u064a\u0648\u0645\u064b\u0627",
    "A16_SENTENCE": "\u0648\u062a\u062e\u0636\u0639 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u062a\u064a \u062a\u0634\u0627\u0631\u0643\u0647\u0627 \u0628\u0647\u0630\u0647 \u0627\u0644\u0637\u0631\u064a\u0642\u0629 \u0644\u0634\u0631\u0648\u0637 OpenAI \u0628\u062f\u0644\u064b\u0627 \u0645\u0646 \u062d\u062f\u0651 \u0627\u0644\u062b\u0644\u0627\u062b\u064a\u0646 \u064a\u0648\u0645\u064b\u0627 \u0627\u0644\u0645\u0630\u0643\u0648\u0631 \u0623\u062f\u0646\u0627\u0647.",
    "DPO": "\u0645\u0633\u0624\u0648\u0644 \u062d\u0645\u0627\u064a\u0629 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0644\u062f\u064a\u0646\u0627",
    "F2_LINKED": "\u0645\u0627 \u062f\u0627\u0645 \u062d\u0633\u0627\u0628\u0643 \u0645\u0648\u062c\u0648\u062f\u064b\u0627",
    "F3_APP_TRACES": "\u062a\u062a\u0628\u0639\u0627\u062a \u0627\u0644\u0623\u062f\u0627\u0621 \u0627\u0644\u0648\u0627\u0631\u062f\u0629 \u0645\u0646 \u0627\u0644\u062a\u0637\u0628\u064a\u0642 \u0639\u0646\u0627\u0648\u064a\u0646 \u0627\u0644\u0637\u0644\u0628\u0627\u062a \u0646\u0641\u0633\u0647\u0627",
    "F5_SEARCH": "\u0645\u062d\u0631\u0643\u0627\u062a \u0627\u0644\u0628\u062d\u062b",
    "IP": "\u0639\u0646\u0627\u0648\u064a\u0646 IP",
    "LINKED": "\u0627\u0644\u0645\u0631\u062a\u0628\u0637\u0629 \u0628\u062d\u0633\u0627\u0628\u0643",
    "UNLINKED": "\u063a\u064a\u0631 \u0627\u0644\u0645\u0631\u062a\u0628\u0637\u0629 \u0628\u0623\u064a \u062d\u0633\u0627\u0628",
    "DATE_LINE": "*\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0633\u0631\u064a\u0627\u0646: 11 \u0623\u0643\u062a\u0648\u0628\u0631 2026*",
}

# Synthetic answers for the temp-copy fill-in (ASCII or escaped; never a real fact).
COMPLETE_ANSWERS = {
    "deletion_variant": "043",
    "territories": "gcc",
    "counsel_review": False,
    "d3": "A",
    "d5": "A",
    "trade_name": "",
    "minors_clause": True,
    "openai_store_pinned": True,
    "inapp_notif_clause": False,
}
COMPLETE_VALUES = {
    "CONTROLLER_NAME": "Sample Publisher",
    "POSTAL_ADDRESS": "Building 1, Road 2, Block 3, Manama, Bahrain",
    "PRIVACY_EMAIL": "privacy@qaren.app",
    "SUPPORT_EMAIL": "support@qaren.app",
    "IP_OWNER": "the publisher",
    "IP_OWNER_AR": "\u0627\u0644\u0646\u0627\u0634\u0631",
    "GOVERNING_LAW": "the Kingdom of Bahrain",
    "GOVERNING_LAW_AR": "\u0645\u0645\u0644\u0643\u0629 \u0627\u0644\u0628\u062d\u0631\u064a\u0646",
    "WITHDRAW_PATH": "Profile, then Privacy",
    "WITHDRAW_PATH_AR": "\u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0634\u062e\u0635\u064a\u060c \u062b\u0645 \u0627\u0644\u062e\u0635\u0648\u0635\u064a\u0629",
    "SECURITY_LOG_RETENTION": "no fixed period",
    "SECURITY_LOG_RETENTION_AR": "\u062f\u0648\u0646 \u0645\u062f\u0629 \u0645\u062d\u062f\u062f\u0629",
    "ANON_LOG_RETENTION": "no fixed period",
    "ANON_LOG_RETENTION_AR": "\u062f\u0648\u0646 \u0645\u062f\u0629 \u0645\u062d\u062f\u062f\u0629",
    "HOSTING_REGIONS": "Ireland",
    "HOSTING_REGIONS_AR": "\u0623\u064a\u0631\u0644\u0646\u062f\u0627",
    "CONTROLLER_COUNTRY": "Bahrain",
    "RETENTION_CLEANUP_LIVE": "false",
    "REFERRAL_PUSH_DISPLAY_NAME_ONLY": "true",
}
AR_DPO_VALUE = "\u062c\u064a\u0646 \u062f\u0648\u060c dpo@example.com"
AR_COUNSEL_VALUE = "- **\u0639\u0642\u062f:** \u062d\u0633\u0627\u0628\u0643."
AR_TRANSFER_VALUE = "\u0646\u0646\u0642\u0644 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0628\u0645\u0648\u062c\u0628 \u0639\u0642\u0648\u062f."
AR_TWELVE_MONTHS = "12 \u0634\u0647\u0631\u064b\u0627"


def _read(rel, root=REPO):
    return (Path(root) / rel).read_text(encoding="utf-8")


def _esc(text):
    return text.encode("unicode_escape").decode("ascii")


def _section(text, number):
    match = re.search(r"(?ms)^## " + re.escape(str(number)) + r"\.[^\n]*\n(.*?)(?=^## |\Z)", text)
    return match.group(1) if match else ""


def _subsection(text, number):
    match = re.search(r"(?ms)^### " + re.escape(str(number)) + r"[^\n]*\n(.*?)(?=^##|\Z)", text)
    return match.group(1) if match else ""


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def _renderer():
    return _load(RENDERER, "_u8_polish_renderer")


def _fill():
    return _load(FILL_SCRIPT, "_u8_polish_fill_in")


# ---------------------------------------------------------------------------
# Text items (EN + AR)
# ---------------------------------------------------------------------------


def test_polish_a5_no_estimated_price_marking_and_pending_disclosed():
    """A5: no price is ever marked 'estimated' in the App; the ToS says unconfirmed prices show as pending."""
    en, ar = _read(TERMS_EN), _read(TERMS_AR)
    problems = []
    if re.search(r"(?i)\bestimated\b", en):
        problems.append(f"{TERMS_EN}: still says 'estimated'")
    if "shows it as pending instead of a number" not in _section(en, 11):
        problems.append(f"{TERMS_EN} s11: the pending sentence is missing")
    if AR["A5_OLD"] in ar:
        problems.append(f"{TERMS_AR}: still carries the 'indicative' price wording")
    if AR["A5_PENDING"] not in _section(ar, 11):
        problems.append(f"{TERMS_AR} s11: the pending sentence is missing")
    assert not problems, problems


def test_polish_a6_specification_source_is_ai_compiled():
    """A6: s2 and s11 say specifications are AI-compiled from search results and the model's knowledge."""
    problems = []
    for rel, marker in ((TERMS_EN, "the AI model's general knowledge"), (TERMS_AR, AR["A6_KNOWLEDGE"])):
        text = _read(rel)
        for number in (2, 11):
            if marker not in _section(text, number):
                problems.append(f"{rel} s{number}: no AI-compiled specification wording")
    en = _read(TERMS_EN)
    if "cross-checked" in en or "gathers specifications" in en:
        problems.append(f"{TERMS_EN}: the old 'gathered and cross-checked' wording is back")
    if "we compare them with the search results where we can" not in _section(en, 11):
        problems.append(f"{TERMS_EN} s11: the 'compare where we can' clause is missing")
    assert not problems, problems


def test_polish_a7_country_source_is_onboarding_or_network_location():
    """A7: country comes from onboarding, or from the device language and the network location."""
    en, ar = _subsection(_read(PRIVACY_EN), "3.3"), _subsection(_read(PRIVACY_AR), "3.3")
    assert "which you choose during onboarding" in en and "your network location" in en, en
    assert "device's settings" not in en
    assert AR["A7_ONBOARDING"] in ar and AR["A7_NETWORK"] in ar, _esc(ar)


def test_polish_a8_notification_records_listed():
    """A8: s3.4 lists the reminder notification records (re_engagement_events)."""
    en, ar = _subsection(_read(PRIVACY_EN), "3.4"), _subsection(_read(PRIVACY_AR), "3.4")
    assert "- **Notification records:** which reminders we sent you, when, and their text." in en, en
    assert "- **" + AR["A8_LABEL"] + ":**" in ar, _esc(ar)


def test_polish_a9_google_shares_profile_picture():
    """A9: the Google sign-in line names the profile picture."""
    en = [line for line in _section(_read(PRIVACY_EN), 5).splitlines() if line.startswith("- **Google:**")]
    ar = [line for line in _section(_read(PRIVACY_AR), 5).splitlines() if line.startswith("- **Google:**")]
    assert len(en) == 1 and "name, email address and profile picture" in en[0], en
    assert len(ar) == 1 and AR["A9_PICTURE"] in ar[0], [_esc(x) for x in ar]


def test_polish_a13_ar_request_bodies_wording():
    """A13: the AR s13 renders 'request bodies' as bodies, not 'the content of requests'."""
    body = _section(_read(PRIVACY_AR), 13)
    assert AR["A13_NEW"] in body and AR["A13_OLD"] not in body, _esc(body)


def test_polish_a14_display_name_scoped_to_invite_links():
    """A14: only invite links show the sharer's display name; plain comparison links do not."""
    problems = []
    for rel, number in ((PRIVACY_EN, 5), (TERMS_EN, 9)):
        body = _section(_read(rel), number)
        if "People who open an invite link you share can also see your display name." not in body:
            problems.append(f"{rel} s{number}: no invite-link display-name sentence")
        if "without the parts personalised for you, and your display name" in body:
            problems.append(f"{rel} s{number}: comparison links still promise the display name")
    for rel, number, old in ((PRIVACY_AR, 5, AR["A14_OLD_PRIVACY"]), (TERMS_AR, 9, AR["A14_OLD_TERMS"])):
        body = _section(_read(rel), number)
        if AR["A14_INVITE"] not in body or old in body:
            problems.append(f"{rel} s{number}: the AR invite-link sentence is not the scoped one")
    assert not problems, problems


def test_polish_f3_app_performance_traces_disclosed():
    """F3: s13 says App performance traces record the same request addresses, after the App sentence."""
    en, ar = _section(_read(PRIVACY_EN), 13), _section(_read(PRIVACY_AR), 13)
    sentence = "Performance traces from the App record the same request addresses."
    assert sentence in en and en.index("Reports from the App can include") < en.index(sentence), en
    assert AR["F3_APP_TRACES"] in ar, _esc(ar)


def test_polish_f5_pictures_may_come_from_a_search_engine():
    """F5: the s6 picture sentence covers images served by a search engine too."""
    for rel, picture, engine in (
        (PRIVACY_EN, "Product pictures in the App", "search engine"),
        (PRIVACY_AR, "\u0635\u0648\u0631 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a \u0641\u064a \u0627\u0644\u062a\u0637\u0628\u064a\u0642", AR["F5_SEARCH"]),
    ):
        sentences = [s for s in re.split(r"(?<=\.)\s+", _section(_read(rel), 6)) if picture in s]
        assert len(sentences) == 1 and engine in sentences[0] and "IP" in sentences[0], (rel, [_esc(s) for s in sentences])


def test_polish_a16_d3_b_names_openai_terms_for_shared_data():
    """A16: the d3 = B variant says shared data follows OpenAI's terms, not the 30-day limit."""
    fork = json.loads(_read(VARIANTS))["forks"]["d3_training"]
    assert "Data you share this way is governed by OpenAI's terms rather than the 30-day limit below." in fork["en"]["B"]
    assert fork["ar"]["B"].endswith(" " + AR["A16_SENTENCE"]), _esc(fork["ar"]["B"])
    assert "30-day" not in fork["en"]["A"] and AR["A16_LIMIT"] not in fork["ar"]["A"]


def test_polish_a17_support_region_carries_the_identity_fork():
    """A17: the support sources (before the fill-in) carry the d5 identity variant, so d5 = B reaches the
    support page."""
    fork = json.loads(_read(VARIANTS))["forks"]["d5_identity"]
    assert "support" in fork["docs"], fork["docs"]
    for rel, lang in ((SUPPORT_EN, "en"), (SUPPORT_AR, "ar")):
        assert _read(_prefill(rel)).count(fork[lang][fork["inline"]]) == 1, rel


def test_polish_q5_manifest_comment_names_the_app_module():
    """Fix Q5: the processors.json comment says the retailer row lists the App's ProductImage module."""
    data = json.loads(_read(MANIFEST))
    assert "SmartCompareApp/src/components/primitives/ProductImage.tsx" in data["_comment"]
    assert "retailer row" in data["_comment"]


BULLET = re.compile(r"(?m)^- \*\*(.+?):\*\*(.*)$")


def test_polish_f2_security_retention_scope_en_and_ar():
    """F2 (the AR twin of fix A3): the linked security line is kept as long as the account exists and
    never carries the retention value; the unlinked line carries it (the token before the fill-in,
    the recorded value after)."""
    data = json.loads(_read(FILL_IN))["placeholders"]
    problems = []
    for rel, key, ip, linked, unlinked, forever in (
        (PRIVACY_EN, "SECURITY_LOG_RETENTION", "IP address", "linked to your account", "not linked to an account",
         "as long as your account exists"),
        (PRIVACY_AR, "SECURITY_LOG_RETENTION_AR", AR["IP"], AR["LINKED"], AR["UNLINKED"], AR["F2_LINKED"]),
    ):
        # The token until the fill-in runs, the recorded value after (UG11 records the values first).
        retention = [f"<PLACEHOLDER:{key}>"] + ([data[key]] if data.get(key) else [])
        bullets = [(label, value) for label, value in BULLET.findall(_section(_read(rel), 8)) if ip in label]
        linked_rows = [v for label, v in bullets if linked in label and unlinked not in label]
        unlinked_rows = [v for label, v in bullets if unlinked in label]
        if len(linked_rows) != 1 or forever not in linked_rows[0] or "<PLACEHOLDER:SECURITY_LOG_RETENTION" in linked_rows[0]:
            problems.append(f"{rel} s8: the linked line must say {_esc(forever)!r} and carry no retention token")
        if len(unlinked_rows) != 1 or not any(r in unlinked_rows[0] for r in retention):
            problems.append(f"{rel} s8: the unlinked line must carry one of {[_esc(r) for r in retention]!r}")
    assert not problems, problems


# ---------------------------------------------------------------------------
# Renderer (B3, B6, B7)
# ---------------------------------------------------------------------------


def _copy_tree(root, rels):
    for rel in rels:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes((REPO / rel).read_bytes())


def _prefill(rel):
    """The snapshot path of a source (the six sources before the fill-in)."""
    return f"{PREFILL}/{Path(rel).name}"


def _copy_prefill(root):
    for rel in SOURCES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes((REPO / _prefill(rel)).read_bytes())


def _null_data():
    """The fill-in data file's shape with every answer, flag and value null (the recorded values are not used)."""
    data = json.loads(_read(FILL_IN))
    for key in data:
        if not key.startswith("_") and key not in ("flags", "placeholders"):
            data[key] = None
    data["flags"] = dict.fromkeys(data["flags"])
    data["placeholders"] = dict.fromkeys(data["placeholders"])
    return data


def test_polish_b3_renderer_link_safety_marker_pairs_and_write_round_trip(tmp_path):
    """B3 (PIN): unsafe hrefs stay text, safe hrefs are escaped; two marker pairs are refused;
    write_regions rewrites only the region, keeps CRLF and is idempotent."""
    r = _renderer()
    out = r.render_markdown("[x](javascript:alert(1)) [y](https://a.example/?a=1&b=2) [m](mailto:a@b.example)")
    assert 'href="javascript' not in out and "[x](javascript:alert(1))" in out, out
    assert 'href="https://a.example/?a=1&amp;b=2"' in out and 'href="mailto:a@b.example"' in out, out
    page = "<main>\n<!-- legal:begin -->\nA\n<!-- legal:end -->\n<!-- legal:begin --><!-- legal:end -->\n</main>\n"
    with pytest.raises(r.LegalRenderError):
        r._page_with_region(page.encode("utf-8"), "\nB\n", "landing/privacy.html")
    _copy_tree(tmp_path, SOURCES + PAGES)
    before = {p: (tmp_path / p).read_bytes() for p in PAGES}
    source = tmp_path / PRIVACY_EN
    src_nl = b"\r\n" if b"\r\n" in source.read_bytes() else b"\n"
    source.write_bytes(source.read_bytes() + src_nl + b"Appended paragraph for the round trip." + src_nl)
    assert r.write_regions(tmp_path) == ["landing/privacy.html"]
    assert r.write_regions(tmp_path) == []
    after = (tmp_path / "landing/privacy.html").read_bytes()
    head, _, tail = r._split_page(before["landing/privacy.html"].decode("utf-8"), "p")
    new_head, region, new_tail = r._split_page(after.decode("utf-8"), "p")
    assert (new_head, new_tail) == (head, tail) and "Appended paragraph for the round trip." in region
    # the page keeps its own line endings: CRLF on a Windows checkout (core.autocrlf), LF on the Linux CI
    if b"\r\n" in before["landing/privacy.html"]:
        assert after.count(b"\n") == after.count(b"\r\n"), "bare LF in a CRLF page"
    else:
        assert b"\r" not in after, "CR in an LF page"
    assert all((tmp_path / p).read_bytes() == before[p] for p in PAGES if p != "landing/privacy.html")


OUTSIDE_SUBSET_CASES = {
    "numbered": "Intro\n\n1. first\n2. second\n",
    "star_bullet": "Intro\n\n* first\n",
    "plus_bullet": "Intro\n\n+ first\n",
    "indented_item": "- a\n  - b\n",
    "quote": "> quoted\n",
    "table_row": "| a | b |\n",
    "four_hashes": "#### Deep heading\n",
    "horizontal_rule": "Intro\n\n---\n",
    "line_after_item": "- a\ncontinued line\n",
}


@pytest.mark.parametrize("case", sorted(OUTSIDE_SUBSET_CASES))
def test_polish_b6_renderer_refuses_markdown_outside_the_subset(case):
    """B6: each construct the landing renderer cannot render like the App is refused, not mis-rendered."""
    r = _renderer()
    with pytest.raises(r.LegalRenderError):
        r.render_markdown(OUTSIDE_SUBSET_CASES[case])


def test_polish_b6_renderer_subset_positive_control_and_bom(tmp_path):
    """B6 (PIN): the subset still renders; a source with a UTF-8 BOM keeps its h1."""
    r = _renderer()
    out = r.render_markdown("# T\n\n**MYEZ**\n\n## 1. A\n\nText *em* **b**.\n\n- **x:** y\n- z\n\n### 1.1 B\n\nMore.\n")
    assert "<h1>T</h1>" in out and "<li><strong>x:</strong> y</li>" in out and "<em>em</em>" in out
    _copy_tree(tmp_path, SOURCES + PAGES)
    (tmp_path / SUPPORT_EN).write_bytes(b"\xef\xbb\xbf# Support\n\nText.\n")
    assert "<h1>Support</h1>" in r.render_regions(tmp_path)["landing/support.html"]


@pytest.mark.parametrize("case", sorted(OUTSIDE_SUBSET_CASES))
def test_polish_b6_counsel_values_outside_the_subset_are_refused(case):
    """B6: a counsel value (EN or AR key) with markdown the renderer refuses is refused by the fill-in."""
    fill = _fill()
    for key in ("LEGAL_BASIS_COUNSEL", "LEGAL_BASIS_COUNSEL_AR"):
        with pytest.raises(fill.FillInError):
            fill._check_value(key, OUTSIDE_SUBSET_CASES[case])


def test_polish_b7_check_reports_a_missing_page(tmp_path, capsys):
    """B7: --check on a missing page exits 2 with a message, not a traceback."""
    r = _renderer()
    _copy_tree(tmp_path, SOURCES + PAGES)
    (tmp_path / "landing/support.html").unlink()
    with pytest.raises(r.LegalRenderError):
        r.stale_regions(tmp_path)
    assert r.main(["--check", "--repo-root", str(tmp_path)]) == 2
    assert "landing/support.html" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Fill-in script end to end on a temp copy (B4, B2, B5, A10, A11, A12, A15, F1)
# ---------------------------------------------------------------------------


class Copy:
    """A temp copy of the pre-fill sources (the snapshot), the pages and the renderer, and an all-null data
    file the node edits (so the node holds before and after the fill-in commit)."""

    def __init__(self, tmp_path):
        self.root = tmp_path / "repo"
        _copy_tree(self.root, PAGES + (RENDERER,))
        _copy_prefill(self.root)
        self.data = _null_data()
        self.data_path = tmp_path / "data.json"
        self.fill = _fill()

    def complete(self, **values):
        self.data.update(copy.deepcopy(COMPLETE_ANSWERS))
        self.data["flags"] = dict.fromkeys(self.data["flags"], "off")
        self.data["placeholders"].update(COMPLETE_VALUES)
        self.data["placeholders"].update(values)
        return self

    def run(self, capsys=None):
        self.data_path.write_text(json.dumps(self.data), encoding="utf-8")
        rc = self.fill.main(["--repo-root", str(self.root), "--data", str(self.data_path), "--variants", str(REPO / VARIANTS)])
        err = capsys.readouterr().err if capsys else ""
        return rc, err

    def snapshot(self):
        return {rel: (self.root / rel).read_bytes() for rel in SOURCES + PAGES}

    def text(self, rel):
        return _read(rel, self.root)


def test_polish_b4_fill_in_end_to_end(tmp_path, capsys):
    """B4: all-null rc 2 and nothing written; complete synthetic answers rc 0, no placeholder anywhere,
    the effective-date lines unchanged, and a second run changes nothing; markup rc 3; a d3 flip
    re-selects the fork; a value changed after the fill rc 3."""
    c = Copy(tmp_path)
    start = c.snapshot()
    assert c.run(capsys)[0] == 2 and c.snapshot() == start
    c.complete()
    assert c.run(capsys)[0] == 0
    filled = c.snapshot()
    assert not [rel for rel, b in filled.items() if b"PLACEHOLDER" in b]
    for rel in (PRIVACY_EN, TERMS_EN, PRIVACY_AR, TERMS_AR):
        assert c.text(rel).splitlines()[4] == _read(rel).splitlines()[4]
    assert c.text(PRIVACY_EN).splitlines()[4] == "*Effective date: October 11, 2026*"
    assert c.text(PRIVACY_AR).splitlines()[4] == AR["DATE_LINE"]
    assert c.run(capsys)[0] == 0 and c.snapshot() == filled
    bad = Copy(tmp_path / "markup").complete(SUPPORT_EMAIL="support@qaren.app <b>")
    bad_start = bad.snapshot()
    assert bad.run(capsys)[0] == 3 and bad.snapshot() == bad_start
    b_text = json.loads(_read(VARIANTS))["forks"]["d3_training"]["en"]["B"]
    c.data["d3"] = "B"
    assert c.run(capsys)[0] == 0 and b_text in c.text(PRIVACY_EN)
    flipped = c.snapshot()
    c.data["placeholders"]["WITHDRAW_PATH"] = "Profile, then Settings"
    rc, err = c.run(capsys)
    assert rc == 3 and "WITHDRAW_PATH" in err and REFILL_HINT in err and c.snapshot() == flipped


@pytest.mark.parametrize("key", ("HOSTING_REGIONS", "HOSTING_REGIONS_AR", "PRIVACY_EMAIL", "SUPPORT_EMAIL"))
def test_polish_f1_value_changed_to_empty_after_a_fill_is_refused(tmp_path, capsys, key):
    """F1: a value changed to '' after a fill exits 3 and writes nothing (the old text would stay)."""
    c = Copy(tmp_path).complete()
    assert c.run(capsys)[0] == 0
    filled = c.snapshot()
    c.data["placeholders"][key] = ""
    rc, err = c.run(capsys)
    assert rc == 3 and c.snapshot() == filled, err


def test_polish_f1_empty_hosting_regions_first_fill_is_accepted(tmp_path, capsys):
    """F1 (PIN): HOSTING_REGIONS '' (unknown) stays a legitimate first answer."""
    c = Copy(tmp_path).complete(HOSTING_REGIONS="", HOSTING_REGIONS_AR="")
    assert c.run(capsys)[0] == 0
    # FIX-2 UF3: the clause names only the database and hosting roles (the Upstash region is not measured).
    assert "(our database and hosting providers)" not in c.text(PRIVACY_EN)
    assert "temporary-storage" not in c.text(PRIVACY_EN)


def test_polish_b2_unrenderable_page_writes_nothing(tmp_path, capsys):
    """B2: a page without its end marker is found before the first write: rc 3, nothing written."""
    c = Copy(tmp_path).complete()
    page = c.root / "landing/support.html"
    page.write_bytes(page.read_bytes().replace(b"<!-- legal:end -->", b""))
    start = c.snapshot()
    rc, err = c.run(capsys)
    assert rc == 3 and "nothing written" in err and "landing/support.html" in err and c.snapshot() == start


def test_polish_b2_counsel_markdown_outside_the_subset_writes_nothing(tmp_path, capsys):
    """B2 + B6: counsel markdown outside the renderer subset is refused before any write."""
    c = Copy(tmp_path).complete()
    c.data["counsel_review"] = True
    c.data["placeholders"].update(
        LEGAL_BASIS_COUNSEL="Intro\n\n1. numbered", LEGAL_BASIS_COUNSEL_AR=AR_COUNSEL_VALUE,
        TRANSFER_BASIS_COUNSEL="We transfer data under contracts.", TRANSFER_BASIS_COUNSEL_AR=AR_TRANSFER_VALUE,
    )
    start = c.snapshot()
    rc, err = c.run(capsys)
    assert rc == 3 and "LEGAL_BASIS_COUNSEL" in err and c.snapshot() == start


def test_polish_a10_arabic_counsel_wording_is_accepted(tmp_path, capsys):
    """A10: an Arabic counsel value may use the same markdown as the English one."""
    c = Copy(tmp_path).complete()
    c.data["counsel_review"] = True
    c.data["placeholders"].update(
        LEGAL_BASIS_COUNSEL="- **Contract:** your account.", LEGAL_BASIS_COUNSEL_AR=AR_COUNSEL_VALUE,
        TRANSFER_BASIS_COUNSEL="We transfer data under contracts.", TRANSFER_BASIS_COUNSEL_AR=AR_TRANSFER_VALUE,
    )
    rc, err = c.run(capsys)
    assert rc == 0, err
    assert AR_COUNSEL_VALUE in c.text(PRIVACY_AR) and "- **Contract:** your account." in c.text(PRIVACY_EN)


@pytest.mark.parametrize("key,value,answers", (
    ("CR_NUMBER", "", {"d5": "A"}),
    ("CR_NUMBER", "CR 12345", {"d5": "A"}),
    ("LEGAL_BASIS_COUNSEL_AR", AR_COUNSEL_VALUE, {"counsel_review": False}),
))
def test_polish_b5_value_only_an_unselected_variant_uses(tmp_path, capsys, key, value, answers):
    """B5 + UP3 + F1: a value only an unselected variant uses is refused with 'set it null', never
    with the false 'the documents use it' or 'markup' message."""
    c = Copy(tmp_path).complete(**{key: value})
    c.data.update(answers)
    rc, err = c.run(capsys)
    assert rc == 3 and "set it null" in err, err
    assert "the documents use it" not in err and "markup" not in err, err


def test_polish_a11_fixed_retention_period_needs_the_live_cleanup(tmp_path, capsys):
    """A11 (UL8): a fixed retention period is refused until RETENTION_CLEANUP_LIVE is 'true'."""
    for key, value in (("SECURITY_LOG_RETENTION", "12 months"), ("ANON_LOG_RETENTION_AR", AR_TWELVE_MONTHS)):
        for live in ("false", None):
            c = Copy(tmp_path / f"{key}-{live}").complete(**{key: value, "RETENTION_CLEANUP_LIVE": live})
            start = c.snapshot()
            rc, err = c.run(capsys)
            assert rc == 3 and "UL8" in err and key in err and c.snapshot() == start, err
        c = Copy(tmp_path / f"{key}-live").complete(**{key: value, "RETENTION_CLEANUP_LIVE": "true"})
        assert c.run(capsys)[0] == 0
        assert value in c.text(PRIVACY_AR if key.endswith("_AR") else PRIVACY_EN)


@pytest.mark.parametrize("value,rc", (("Bahrain", 0), (" bahrain ", 0), (None, 0), ("Saudi Arabia", 3), ("", 3)))
def test_polish_a12a_controller_country_must_be_bahrain(tmp_path, capsys, value, rc):
    """A12(a): any controller country but Bahrain is refused until sections 7 and 10 are re-drafted."""
    c = Copy(tmp_path).complete(CONTROLLER_COUNTRY=value)
    got, err = c.run(capsys)
    assert got == rc, err
    if rc == 3:
        assert "re-draft sections 7 and 10" in err


def test_polish_a12b_cloudflare_line_kept_whatever_the_mailboxes(tmp_path, capsys):
    """A12(b) as amended by fix P1 (2026-10-08): the Cloudflare line is plain text and stays whatever
    addresses are recorded (the landing chrome publishes support@qaren.app on every legal page); a
    changed address after a fill is still refused."""
    line = "- **Cloudflare:**"
    kept = Copy(tmp_path / "kept").complete()
    assert kept.run(capsys)[0] == 0
    assert line in kept.text(PRIVACY_EN) and line in kept.text(PRIVACY_AR)
    mixed = Copy(tmp_path / "mixed").complete(SUPPORT_EMAIL="help@example.com")
    assert mixed.run(capsys)[0] == 0
    assert line in mixed.text(PRIVACY_EN) and line in mixed.text(PRIVACY_AR)
    assert "- **Retailer websites:**" in mixed.text(PRIVACY_EN)
    filled = mixed.snapshot()
    assert mixed.run(capsys)[0] == 0 and mixed.snapshot() == filled
    plan = mixed.fill.plan
    data = copy.deepcopy(mixed.data)
    data["placeholders"]["SUPPORT_EMAIL"] = "support@qaren.app"
    with pytest.raises(mixed.fill.FillInError) as info:
        plan(mixed.root, data, json.loads(_read(VARIANTS)))
    assert "SUPPORT_EMAIL" in str(info.value) and REFILL_HINT in str(info.value)


def test_polish_a12c_dpo_contact_clause(tmp_path, capsys):
    """A12(c): DPO_CONTACT is empty by default and names the officer in s1 and s16 when recorded; a
    value removed after the fill exits 3."""
    none = Copy(tmp_path / "none").complete()
    assert none.run(capsys)[0] == 0
    assert "data protection officer" not in none.text(PRIVACY_EN) and AR["DPO"] not in none.text(PRIVACY_AR)
    c = Copy(tmp_path / "dpo").complete(DPO_CONTACT_DETAILS="Jane Doe, dpo@example.com", DPO_CONTACT_DETAILS_AR=AR_DPO_VALUE)
    assert c.run(capsys)[0] == 0
    en, ar = c.text(PRIVACY_EN), c.text(PRIVACY_AR)
    clause = ", or our data protection officer, Jane Doe, dpo@example.com"
    assert clause in _section(en, 1) and clause in _section(en, 16), en
    assert AR["DPO"] in _section(ar, 1) and AR["DPO"] in _section(ar, 16) and AR_DPO_VALUE in ar
    filled = c.snapshot()
    c.data["placeholders"]["DPO_CONTACT_DETAILS"] = None
    c.data["placeholders"]["DPO_CONTACT_DETAILS_AR"] = None
    rc, err = c.run(capsys)
    assert rc == 3 and "DPO_CONTACT" in err and c.snapshot() == filled, err


@pytest.mark.parametrize("value", ("true", "false", None))
def test_polish_a15_referral_notification_sentence(tmp_path, capsys, value):
    """A15: 'true' keeps the display-name sentence; 'false' and null publish the email-prefix wording."""
    fork = json.loads(_read(VARIANTS))["forks"]["referral_push_name"]
    for rel, lang in ((PRIVACY_EN, "en"), (TERMS_EN, "en"), (PRIVACY_AR, "ar"), (TERMS_AR, "ar")):
        assert _read(_prefill(rel)).count(fork[lang]["true"]) == 1, rel
    assert "first part of your email address" in fork["en"]["false"] and AR["A15_FALSE"] in fork["ar"]["false"]
    c = Copy(tmp_path).complete(REFERRAL_PUSH_DISPLAY_NAME_ONLY=value)
    assert c.run(capsys)[0] == 0
    key = "true" if value == "true" else "false"
    for rel, lang in ((PRIVACY_EN, "en"), (TERMS_EN, "en"), (PRIVACY_AR, "ar"), (TERMS_AR, "ar")):
        assert c.text(rel).count(fork[lang][key]) == 1, rel


def test_polish_a15_referral_answer_must_be_a_bool_string(tmp_path, capsys):
    """A15 / A11 (PIN): the two string-boolean answers accept only 'true', 'false' or null."""
    for key in ("REFERRAL_PUSH_DISPLAY_NAME_ONLY", "RETENTION_CLEANUP_LIVE"):
        c = Copy(tmp_path / key).complete(**{key: "yes"})
        rc, err = c.run(capsys)
        assert rc == 3 and key in err, err


def test_polish_new_answer_keys_are_recorded_null_in_the_fixture():
    """The polish answers exist in the fill-in data file (null is each one's documented default)."""
    data = json.loads(_read(FILL_IN))
    for key in ("CONTROLLER_COUNTRY", "RETENTION_CLEANUP_LIVE", "REFERRAL_PUSH_DISPLAY_NAME_ONLY",
                "DPO_CONTACT", "DPO_CONTACT_DETAILS", "DPO_CONTACT_DETAILS_AR"):
        assert key in data["placeholders"], key
    assert "DPO_CONTACT" in json.loads(_read(VARIANTS))["clauses"]


# ---------------------------------------------------------------------------
# Route (B8)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ("ar_SA", "AR_bh", " ar_SA "))
def test_polish_b8_underscore_subtag_serves_arabic(value):
    """B8 (UG11's waiver withdrawn): 'ar_SA' and friends serve the Arabic documents."""
    from app.api import legal_routes

    ar = _read(PRIVACY_AR)
    for handler in (legal_routes.get_privacy_policy, legal_routes.get_terms_of_service):
        body = asyncio.run(handler(lang=value)) if asyncio.iscoroutinefunction(handler) else handler(lang=value)
        content = body.get("content") if isinstance(body, dict) else getattr(body, "content", None)
        assert content and re.search("[\u0600-\u06ff]", content), (handler.__name__, value)
    assert ar.splitlines()[0].startswith("# ")


# ---------------------------------------------------------------------------
# Fix round 2 (finding P1 of the polish adversary, 2026-10-08; amends UP4 A12(b))
# ---------------------------------------------------------------------------

P1_LINE_EN = "- **Cloudflare:** delivers the email you send to our addresses."
P1_LINE_AR = (
    "- **Cloudflare:** \u062a\u0648\u0635\u0644 \u0631\u0633\u0627\u0626\u0644 \u0627\u0644\u0628\u0631\u064a\u062f "
    "\u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a \u0627\u0644\u062a\u064a \u062a\u0631\u0633\u0644\u0647\u0627 "
    "\u0625\u0644\u0649 \u0639\u0646\u0627\u0648\u064a\u0646\u0646\u0627."
)
P1_EMAIL_PAIRS = (
    ("privacy@qaren.app", "help@example.com"),
    ("privacy@example.com", "support@qaren.app"),
    ("privacy@mail.qaren.app", "support@qaren.app"),
    ("privacy@example.com", "help@example.com"),
    ("privacy@qaren.app", "support@qaren.app"),
)


def test_fix2_p1_cloudflare_line_is_plain_text_not_derived():
    """P1: the landing chrome outside the legal regions publishes support@qaren.app on every legal page,
    so mail to a qaren.app address passes through Cloudflare whatever addresses the fill-in records.
    The Cloudflare line of privacy s5 is therefore committed plain text (EN + AR, once each), no fork or
    clause carries it or derives anything from the e-mail addresses, and no comment documents the
    withdrawn 'both addresses end in @qaren.app' rule."""
    variants = json.loads(_read(VARIANTS))
    problems = []
    for kind in ("forks", "clauses"):
        for name, entry in sorted(variants.get(kind, {}).items()):
            if "Cloudflare" in json.dumps(entry, ensure_ascii=False):
                problems.append(f"{VARIANTS} {kind}.{name} carries the Cloudflare line")
            if "_EMAIL" in json.dumps(entry.get("answer")):
                problems.append(f"{VARIANTS} {kind}.{name} derives its text from an e-mail address")
    for rel, line in ((PRIVACY_EN, P1_LINE_EN), (PRIVACY_AR, P1_LINE_AR)):
        text = _read(rel)
        if text.count(line) != 1 or line not in _section(text, 5):
            problems.append(f"{rel}: the Cloudflare line is not in section 5 exactly once")
    fixture = json.loads(_read(FILL_IN))
    for where, comment in ((VARIANTS, variants.get("_comment", "")), (FILL_IN, fixture.get("_placeholder_answers_comment", ""))):
        if "cloudflare_clause" in comment or "both end in @qaren.app" in comment:
            problems.append(f"{where}: a comment still describes the conditional Cloudflare line")
    assert not problems, problems


@pytest.mark.parametrize("privacy_email,support_email", P1_EMAIL_PAIRS)
def test_fix2_p1_fill_in_keeps_cloudflare_for_every_address_pair(tmp_path, capsys, privacy_email, support_email):
    """P1: a fill-in with any address pair (one or both off qaren.app, a subdomain) exits 0, keeps the
    Cloudflare line in the EN and AR policy and on both privacy pages, so T7a's SPEC_RECIPIENTS_EN
    (Cloudflare unconditional, UG7) holds after the fill-in; a second run changes nothing."""
    c = Copy(tmp_path).complete(PRIVACY_EMAIL=privacy_email, SUPPORT_EMAIL=support_email)
    rc, err = c.run(capsys)
    assert rc == 0, err
    en, ar = c.text(PRIVACY_EN), c.text(PRIVACY_AR)
    assert en.count(P1_LINE_EN) == 1 and P1_LINE_EN in _section(en, 5), _section(en, 5)
    assert ar.count(P1_LINE_AR) == 1 and P1_LINE_AR in _section(ar, 5), _esc(_section(ar, 5))
    for page in ("landing/privacy.html", "landing/ar/privacy.html"):
        assert c.text(page).count("<strong>Cloudflare:</strong>") == 1, page
    filled = c.snapshot()
    assert c.run(capsys)[0] == 0 and c.snapshot() == filled


# ---------------------------------------------------------------------------
# Pre-fill snapshot (session 76, U8 fill-in GREEN): what the temp-copy nodes fill
# ---------------------------------------------------------------------------


def test_polish_prefill_snapshot_tracks_the_documents(tmp_path):
    """tests/fixtures/legal_prefill_u8 is the six sources before the fill-in. While the live sources still
    carry a token they equal it (an edit to a source is an edit to its snapshot); once the fill-in commit
    has filled them, the fill-in of the snapshot with the committed data reproduces them (line endings
    aside). So the temp-copy nodes, which fill the snapshot, test the real documents before and after
    the fill-in commit."""
    live = {rel: _read(rel).replace("\r\n", "\n") for rel in SOURCES}
    snap = {rel: _read(_prefill(rel)).replace("\r\n", "\n") for rel in SOURCES}
    assert all("<PLACEHOLDER:" in snap[rel] for rel in SOURCES), "the snapshot must be the token-bearing sources"
    if any("<PLACEHOLDER:" in text for text in live.values()):
        stale = [rel for rel in SOURCES if live[rel] != snap[rel]]
        assert not stale, f"pre-fill: {stale} differ from {PREFILL}/ (copy the edited source there too)"
        return
    root = tmp_path / "repo"
    _copy_prefill(root)
    missing, outputs = _fill().plan(root, json.loads(_read(FILL_IN)), json.loads(_read(VARIANTS)))
    assert not missing, missing
    filled = {
        rel: (outputs[rel][0] if rel in outputs else (root / rel).read_bytes()).decode("utf-8").replace("\r\n", "\n")
        for rel in SOURCES
    }
    stale = [rel for rel in SOURCES if filled[rel] != live[rel]]
    assert not stale, f"post-fill: the fill-in of {PREFILL}/ with {FILL_IN} does not reproduce {stale}"
