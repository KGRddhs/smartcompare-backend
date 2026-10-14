"""S77 LEGAL-DISCLOSURE: the candid OpenAI-exchange disclosure, the Gmail mailbox, the landing claims and the /bot page.

Spec: .qa-s77/LEGAL_DISCLOSURE_SPEC.md (sections 1, 5, 6), as amended by the BINDING rulings
.qa-s77/RULINGS_S77_LEGAL.md, which supersede it where they differ:
  RL2   privacy s5 own-terms sentence names Google as our mailbox provider (EN + the reviewer's AR twin).
  RL3   privacy s7 "(OpenAI)" -> "(OpenAI and Google)" (EN; the AR twin is pinned by structure).
  RL10  privacy s2 and terms s8 use the GENERAL not-sold promise with the OpenAI programme exception, followed by
        the spec's disclosure sentence; the spec's Option-B narrowing ("to data brokers or advertisers") and the bare
        old sentences are gone. The AR general promise is the GREEN's text: it is pinned by structure (the AR "we do
        not sell your personal data" head, never followed by the narrowing qualifier, in a sentence that names
        OpenAI, data brokers and advertisers).
  RL11  privacy s8 gains the email retention line; privacy s3.2 "Feedback and messages" covers email sent to our
        addresses (EN exact for s8; s3.2 and every AR twin pinned by structure).
  RL13  every node below is RED at base 10135306 because the new text is absent or the old text is present, or is
        a PIN that passes at base (marked PIN in its docstring).

NODE MAP (spec section 6 + rulings):
  D1  privacy s2 discloses the exchange (RL10)            D2  privacy s4 exchange + photo guidance (fork C)
  D3  terms s8 discloses the exchange (RL10)              D4  no bare / narrowed not-sold sentence anywhere (RL10)
  D5  rendered pages + API serve the new text             D5a PIN: the six legal regions equal a fresh render
  D6  privacy s5 names Google (Gmail)                     D7  processors.json Gmail row
  D8  landing index: no "authorized" / Google Play        D9  /bot page claim matches the runtime
  D10 fill-in of the snapshot reproduces the sources      D11 terms s4 states the coded limits
  D12 PIN: the new sentences pass the (k) scan            D13 RL2 own-terms sentence
  D14 RL3 s7 names Google                                 D15 RL11 email retention + s3.2
  D16 landing/README.md doc lines
  D17 RF1 privacy s7 transfer sentence (mailbox)      D18 RF2 privacy s9: email survives deletion

Pure ASCII: every Arabic expectation lives in tests/fixtures/legal_disclosure_s77.json (raw UTF-8); Arabic letter
ranges are built with chr(); failure messages escape non-ASCII. Hermetic: file reads, a temp copy for the fill-in,
the legal route handlers called directly (the test_legal_docs_u8_polish.py idiom), no network.
"""
import ast
import asyncio
import functools
import html
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FIXTURE = "tests/fixtures/legal_disclosure_s77.json"
D3C_FIXTURE = "tests/fixtures/legal_d3c_u8.json"
D3C_TESTS = "tests/test_legal_docs_u8_d3c.py"
RENDERER = "scripts/render_legal_landing.py"
FILL_SCRIPT = "scripts/fill_in_legal.py"
VARIANTS = "scripts/legal_variants_u8.json"
FILL_IN = "tests/fixtures/legal_fill_in_u8.json"
PREFILL = "tests/fixtures/legal_prefill_u8"
MANIFEST = "app/legal/processors.json"
USAGE_SERVICE = "app/services/usage_service.py"
ROBOTS_EVAL = "app/services/robots_eval.py"
BOT = "landing/bot/index.html"
README = "landing/README.md"

PRIVACY = {"en": "app/legal/privacy_policy.md", "ar": "app/legal/privacy_policy_ar.md"}
TERMS = {"en": "app/legal/terms_of_service.md", "ar": "app/legal/terms_of_service_ar.md"}
SUPPORT = {"en": "app/legal/support_contact.md", "ar": "app/legal/support_contact_ar.md"}
PAGE_PRIVACY = {"en": "landing/privacy.html", "ar": "landing/ar/privacy.html"}
PAGE_TERMS = {"en": "landing/terms.html", "ar": "landing/ar/terms.html"}
INDEX = {"en": "landing/index.html", "ar": "landing/ar/index.html"}
LEGAL_SOURCES = (PRIVACY["en"], TERMS["en"], PRIVACY["ar"], TERMS["ar"])
SIX_SOURCES = (PRIVACY["en"], TERMS["en"], SUPPORT["en"], PRIVACY["ar"], TERMS["ar"], SUPPORT["ar"])
LANGS = ("en", "ar")

AR_SEMI = chr(0x061B)
AR_LETTER = "[" + chr(0x0600) + "-" + chr(0x06FF) + "]"
EM_DASH = chr(0x2014)

# ---------------------------------------------------------------------------
# EN expectations (spec section 1 New EN texts, as amended by RL2, RL3, RL10, RL11)
# ---------------------------------------------------------------------------

# RL10: the general promise, then the spec's disclosure sentence(s).
GENERAL_EN = (
    "Apart from OpenAI's data-sharing programme described below, we do not sell or otherwise exchange your personal "
    "data for anything of value, and we do not share it with data brokers or advertisers."
)
P2_DISCLOSURE_EN = (
    "We take part in OpenAI's data-sharing programme (section 4): OpenAI may use the inputs we send it and the outputs "
    "it generates from them to evaluate and train its models, and in return OpenAI gives us some free use of its "
    "service."
)
P2_NEW_EN = GENERAL_EN + " " + P2_DISCLOSURE_EN
P2_OLD_EN = (
    "We do not sell your personal data, and we do not share it with data brokers or advertisers; section 4 describes "
    "what OpenAI may do with the inputs and outputs of your comparisons."
)
# The spec's Option-B narrowing, superseded by RL10 (never in a document).
NARROW_EN = "We do not sell your personal data to data brokers or advertisers, and we do not share it with them."
S2_KEYWORDS_EN = (r"data-sharing programme", r"evaluate and train its models", r"in return", r"free use of its service")

P4_ANCHOR_EN = "This applies to every comparison, and the App has no separate setting for it."
EXCHANGE_EN = "In return for this sharing, OpenAI gives us some free use of its service."
PHOTOS_EN = (
    "Please photograph products only, and do not include people, documents, payment cards or other personal or "
    "health details in your photos or searches."
)

# S78 (LR3, P14-P16): recipients by category. The Google line is sign-in only; the email-routing service and the
# mailbox provider are one category line; the own-terms sentence names "our mailbox provider" without a vendor.
P5G_NEW_EN = (
    "- **Google:** if you use Google Sign-In, Google shares your name, email address and profile picture with us "
    "through its sign-in token."
)
P5C_NEW_EN = (
    "- **Our email providers:** an email-routing service receives the email you send to our addresses and forwards "
    "it to our mailbox provider, which stores it under its own terms."
)
P5C_LABEL_EN = "Our email providers"
# S78 fix F3 (legal A3): the web-font service the website uses is named among the own-terms recipients.
OWN_TERMS_EN = (
    "Retailer websites (section 6), the sign-in providers Apple and Google, our mailbox provider and the web-font "
    "service our website uses act under their own terms."
)
# The S77 sentences S78 retires (P23).
P5G_S77_EN = (
    "- **Google:** if you use Google Sign-In, Google shares your name, email address and profile picture with us "
    "through its sign-in token. Google also receives the email you send to our addresses (see Cloudflare below)."
)
P5C_S77_EN = (
    "- **Cloudflare:** receives the email you send to our addresses and forwards it to our mailbox provider, Google "
    "(Gmail), which stores it under Google's own terms."
)
OWN_TERMS_S77_EN = (
    "Retailer websites (section 6), the sign-in providers Apple and Google, and Google as our mailbox provider act "
    "under their own terms."
)
OWN_TERMS_OLD_EN = "Retailer websites (section 6) and the sign-in providers Apple and Google act under their own terms."

T8_DISCLOSURE_EN = (
    "We take part in OpenAI's data-sharing programme, as section 4 of our Privacy Policy describes: OpenAI may use the "
    "inputs we send it and the outputs it generates from them to evaluate and train its models, and in return OpenAI "
    "gives us some free use of its service."
)
T8_TAIL_EN = "; none of it identifies you. " + GENERAL_EN + " " + T8_DISCLOSURE_EN
T8_OLD_TAIL_EN = "; none of it identifies you, and your personal data is never sold."

T4_NEW_EN = (
    "(currently up to 3 a day and up to 10 a month; your first 3 comparisons count toward these limits, and the "
    "referral rewards described in section 9 add to the monthly limit)"
)
T4_OLD_EN = "after 3 introductory comparisons"

# S78 (LR3, P19): s7 names countries only, no vendor mapping.
S7_EN = "including in the United States and Germany (European Union)"
S7_S77_EN = "United States (OpenAI and Google)"
S7_VENDORS = ("OpenAI", "Google", "Apple", "Sentry", "Supabase", "Railway", "Upstash", "Gmail", "Cloudflare", "Expo")
EMAIL_RETENTION_EN = "Email you send to our addresses: kept in our mailbox until we delete it; no fixed period."

RETIRED_EN = (
    P2_OLD_EN,
    "your personal data is never sold",
    "only if you use Google Sign-In",
    "delivers the email you send to our addresses",
    T4_OLD_EN,
    OWN_TERMS_OLD_EN,
    "We do not sell your personal data to data brokers or advertisers",
    # S78 (P23): the S77-era sentences this unit retires.
    P5G_S77_EN,
    P5C_S77_EN,
    OWN_TERMS_S77_EN,
    S7_S77_EN,
    "and to Google as our mailbox provider, which handles email under its own terms (section 5).",
)

# Landing (spec L1, L3, L4).
OG_EN = "Coming soon to the App Store."
LEDE_EN = (
    "Compare electronics, supplements, fragrances, fashion and more, with prices from online retailers across the "
    "region. Coming soon to the App Store."
)
LEDE_OLD_EN = (
    "Compare electronics, supplements, fragrances, fashion, and more " + EM_DASH + " sourced from authorized retailers "
    "across the region. Coming soon to the App Store and Google Play."
)
BOT_META_EN = "How MYEZ finds prices on store websites, and how its site-discovery crawler (QarenBot) follows robots.txt."
BOT_P_EN = (
    "MYEZ looks up public product pages and store search results to find prices for the products our users compare. "
    "Our site-discovery crawler (QarenBot) reads and follows robots.txt. If you run a store and want us to stop or "
    'slow down, email <a href="mailto:support@getmyez.com">support@getmyez.com</a>.'
)
BOT_ROBOTS_EN = "Our site-discovery crawler (QarenBot) reads and follows robots.txt."
README_BOT_NEW = (
    "how MYEZ looks up prices, the site-discovery crawler (QarenBot) follows robots.txt, support contact (reworded S77)"
)
README_BADGE_NEW = "**App Store badge:** present but"
README_BADGE_NOTE = "The Google Play badge was removed in S77: no Android app is planned."

# Spec section 1 M: the Gmail row of app/legal/processors.json.
ROW_M = {
    "id": "gmail",
    "name_en": "Google (Gmail)",
    "name_ar": "Google (Gmail)",
    "kind": "email_mailbox",
    "personal_data": True,
    "module": [],
    "hosts": [],
    "gate_flag": None,
    "category_en": "mailbox provider",
    "category_ar": "\u0645\u0632\u0648\u0651\u062f \u0635\u0646\u062f\u0648\u0642 \u0628\u0631\u064a\u062f\u0646\u0627",
    "public_name": False,
}

# The QarenBot emitters measured at 10135306 (spec L3); the price look-up modules never send the name.
QARENBOT_FILES = {
    "app/services/robots_eval.py",
    "app/services/search_descriptor_service.py",
    "app/services/sitemap_discovery_service.py",
    "scripts/resolve_search_descriptors.py",
}
PRICE_LOOKUP_FILES = (
    "app/services/price_service.py",
    "app/services/scrapedo_service.py",
    "app/services/brightdata_service.py",
    "app/services/firecrawl_service.py",
)

NOT_SELL_EN = re.compile(r"(?i)\bdo not sell your personal data\b")
NEVER_SOLD_EN = re.compile(r"(?i)personal data is never sold")
RENDERED_SECTION = r"(?s)<h2\b[^>]*>\s*{n}\.(.*?)(?=<h2\b|\Z)"
ADDRESS_RE = re.compile(
    r"qaren://[\w/.-]*|[\w.+-]*@qaren\.app|(?:https?://)?(?:[\w-]+\.)*qaren\.app(?:/[\w/.%-]*)?", re.I | re.A
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _read(rel, root=REPO):
    return (Path(root) / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")


def _json(rel, root=REPO):
    return json.loads(_read(rel, root))


def _esc(text):
    return str(text).encode("unicode_escape").decode("ascii")


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


@functools.lru_cache(maxsize=None)
def _d3c():
    """The d3c test module (its (k) scan and its pinned EN sentences), loaded by path."""
    return _load(D3C_TESTS, "_s77_d3c_module")


def _fx():
    return _json(FIXTURE)


def _d3c_fx():
    return _json(D3C_FIXTURE)


def _prefill(rel):
    return f"{PREFILL}/{Path(rel).name}"


def _section(text, number):
    match = re.search(r"(?ms)^## " + re.escape(str(number)) + r"\.[^\n]*\n(.*?)(?=^## |\Z)", text)
    return match.group(1) if match else ""


def _subsection(text, number):
    match = re.search(r"(?ms)^### " + re.escape(str(number)) + r"[^\n]*\n(.*?)(?=^##|\Z)", text)
    return match.group(1) if match else ""


def _rendered_section(page, number):
    match = re.search(RENDERED_SECTION.format(n=number), page)
    return match.group(1) if match else ""


def _plain(text):
    """Markdown or HTML reduced to its words: tags dropped, entities unescaped, bold markers dropped, runs of
    spaces collapsed (newlines kept)."""
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).replace("**", "")
    return re.sub(r"[ \t]+", " ", text)


def _item_plain(line):
    """A markdown list item as it reads once rendered (no '- ' bullet, no bold markers)."""
    return _plain(line[2:] if line.startswith("- ") else line)


def _api(doc, lang):
    from app.api import legal_routes

    handler = {"privacy": legal_routes.get_privacy_policy, "terms": legal_routes.get_terms_of_service}[doc]
    body = asyncio.run(handler(lang=lang)) if asyncio.iscoroutinefunction(handler) else handler(lang=lang)
    return body if isinstance(body, dict) else body.__dict__


def _line_with(text, needle):
    hits = [line for line in text.split("\n") if needle in line]
    return hits[0] if len(hits) == 1 else None


def _sentence_around(text, start, end):
    """The '.'-delimited sentence (or line) that holds text[start:end]."""
    a = max(text.rfind(".", 0, start), text.rfind("\n", 0, start)) + 1
    ends = [i for i in (text.find(".", end), text.find("\n", end)) if i >= 0]
    return text[a:min(ends) if ends else len(text)]


def _en_not_sold_problems(text):
    """RL10 (EN): every 'do not sell your personal data' sits inside the general promise; nothing says 'personal data
    is never sold'."""
    spans = [m.span() for m in re.finditer(re.escape(GENERAL_EN), text)]
    problems = []
    for m in NOT_SELL_EN.finditer(text):
        if not any(a <= m.start() and m.end() <= b for a, b in spans):
            problems.append("bare or narrowed 'do not sell your personal data': " + repr(text[m.start():m.end() + 60]))
    problems += ["'personal data is never sold'" for _m in NEVER_SOLD_EN.finditer(text)]
    return problems


def _ar_not_sold_problems(text, fx):
    """RL10 (AR, structure): every AR 'we do not sell your personal data' is not followed by the narrowing qualifier
    (to data brokers or advertisers) and sits in a sentence that names OpenAI (the programme exception)."""
    head, qualifier = fx["not_sold_head_ar"], fx["narrow_qualifier_ar"]
    problems = []
    for m in re.finditer(re.escape(head), text):
        if text[m.end():].startswith(qualifier):
            problems.append("AR not-sold head followed by the narrowing qualifier at %d" % m.start())
        if "OpenAI" not in _sentence_around(text, m.start(), m.end()):
            problems.append("AR not-sold head at %d is not in a sentence naming OpenAI (no programme exception)" % m.start())
    return problems


def _retired_problems(where, text, fx):
    out = [f"{where}: retired EN wording {r!r}" for r in RETIRED_EN if r in text]
    out += [f"{where}: retired AR wording {_esc(r[:60])!r}" for r in fx["retired_ar"] if r in text]
    return out


def _texts_with_snapshot(rel):
    """((label, markdown text)) for a live source and its pre-fill snapshot (plain-text lines are identical)."""
    return ((rel, _read(rel)), (_prefill(rel), _read(_prefill(rel))))


def _ar_general_problems(where, section, disclosure, fx, after=None):
    """RL10 AR structure inside one section: the disclosure sentence once; an AR not-sold head that names OpenAI,
    data brokers and advertisers, BEFORE the disclosure (and after `after` when given), never narrowed."""
    problems = []
    if section.count(disclosure) != 1:
        problems.append(f"{where}: the AR disclosure sentence is there {section.count(disclosure)} time(s), not once")
        return problems
    head = fx["not_sold_head_ar"]
    hits = [m for m in re.finditer(re.escape(head), section) if m.start() < section.index(disclosure)]
    if not hits:
        problems.append(f"{where}: no AR not-sold head before the disclosure sentence")
        return problems
    sentence = _sentence_around(section, hits[-1].start(), hits[-1].end())
    for name in ("brokers_ar", "advertisers_ar"):
        if fx[name] not in sentence:
            problems.append(f"{where}: the AR general promise lacks {name}")
    if "OpenAI" not in sentence:
        problems.append(f"{where}: the AR general promise does not name OpenAI (the programme exception)")
    if after is not None and not (after in section and section.index(after) < hits[-1].start()):
        problems.append(f"{where}: the AR general promise does not follow {_esc(after[:40])!r}")
    problems += _ar_not_sold_problems(section, fx)
    return problems


# ---------------------------------------------------------------------------
# D1 privacy s2 (RL10)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d1_privacy_s2_discloses_the_openai_exchange(lang):
    """D1 (RL10): privacy s2, live and snapshot. EN: the general promise followed by the disclosure sentence occurs
    exactly once, in the paragraph that holds the aggregated-statistics sentence and BEFORE it; s2 also matches
    'data-sharing programme', 'evaluate and train its models', 'in return', 'free use of its service'. AR: the
    spec's AR disclosure sentence occurs once in s2; the AR general promise (the not-sold head in a sentence naming
    OpenAI, data brokers and advertisers, never narrowed) precedes it; the aggregated sentence follows it in the same
    paragraph. RED at base: the sentences are absent."""
    fx, d3c = _fx(), _d3c()
    aggregated = d3c.PRIVACY_AGG_EN if lang == "en" else _d3c_fx()["ug12_ar"]["privacy_aggregated"]
    problems = []
    for where, text in _texts_with_snapshot(PRIVACY[lang]):
        s2 = _section(text, 2)
        if lang == "en":
            if text.count(P2_NEW_EN) != 1 or P2_NEW_EN not in s2:
                problems.append(f"{where}: s2 lacks the RL10 general promise + disclosure exactly once")
                continue
            problems += [f"{where}: s2 lacks {k!r}" for k in S2_KEYWORDS_EN if not re.search(k, s2, re.I)]
            anchor = P2_NEW_EN
        else:
            local = _ar_general_problems(where, s2, fx["privacy_s2_disclosure_ar"], fx)
            problems += local
            if local:
                continue
            anchor = fx["privacy_s2_disclosure_ar"]
        paragraph = _line_with(s2, anchor)
        if paragraph is None or aggregated not in paragraph or paragraph.index(anchor) > paragraph.index(aggregated):
            problems.append(f"{where}: the disclosure is not before the aggregated sentence in one paragraph")
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D2 privacy s4 (fork d3_training C)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d2_privacy_s4_states_the_exchange_and_the_photo_guidance(lang):
    """D2: the live privacy s4 holds the exchange sentence and the photo guidance exactly once each, after the 'no
    separate setting' sentence and before the openai_retention sentence (forks.openai_retention.<lang>.true);
    forks.d3_training.<lang>.C ends with ' ' + exchange + ' ' + photos; variants A and B carry neither. The snapshot
    keeps variant A (not checked). RED at base: absent."""
    fx = _fx()
    variants = _json(VARIANTS)
    if lang == "en":
        anchor, exchange, photos = P4_ANCHOR_EN, EXCHANGE_EN, PHOTOS_EN
    else:
        anchor, exchange, photos = fx["privacy_s4_anchor_ar"], fx["privacy_s4_exchange_ar"], fx["privacy_s4_photos_ar"]
    retention = variants["forks"]["openai_retention"][lang]["true"]
    text = _read(PRIVACY[lang])
    s4 = _section(text, 4)
    problems = []
    for name, sentence in (("exchange", exchange), ("photos", photos)):
        if text.count(sentence) != 1 or sentence not in s4:
            problems.append(f"{PRIVACY[lang]} s4: the {name} sentence is not there exactly once")
    if not problems:
        order = [s4.find(s) for s in (anchor, exchange, photos, retention)]
        if -1 in order or order != sorted(order):
            problems.append(f"{PRIVACY[lang]} s4: not anchor < exchange < photos < retention ({order})")
    fork = variants["forks"]["d3_training"][lang]
    if not fork.get("C", "").endswith(" " + exchange + " " + photos):
        problems.append(f"{VARIANTS}: forks.d3_training.{lang}.C does not end with the exchange + photo guidance")
    for variant in ("A", "B"):
        if exchange in fork.get(variant, "") or photos in fork.get(variant, ""):
            problems.append(f"{VARIANTS}: forks.d3_training.{lang}.{variant} carries the C-only exchange text")
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D3 terms s8 (RL10)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d3_terms_s8_discloses_the_openai_exchange(lang):
    """D3 (RL10): terms s8, live and snapshot. EN: the tail '; none of it identifies you. ' + general promise +
    ' ' + terms disclosure sentence occurs exactly once in s8, after the licence sentence. AR: the 'none of it
    identifies you.' sentence, then the AR general promise (structure as D1), then the spec's AR terms disclosure
    sentence, each after the licence sentence. RED at base."""
    fx, d3c = _fx(), _d3c()
    problems = []
    for where, text in _texts_with_snapshot(TERMS[lang]):
        s8 = _section(text, 8)
        if lang == "en":
            licence = d3c.TERMS_LICENCE_EN
            if text.count(T8_TAIL_EN) != 1 or T8_TAIL_EN not in s8:
                problems.append(f"{where}: s8 lacks the RL10 tail exactly once")
            elif licence not in s8 or s8.index(licence) > s8.index(T8_TAIL_EN):
                problems.append(f"{where}: the RL10 tail does not follow the licence sentence")
            continue
        licence = _d3c_fx()["ug12_ar"]["terms_licence"]
        identifies = fx["terms_s8_identifies_ar"]
        if s8.count(identifies) != 1 or licence not in s8 or s8.index(licence) > s8.index(identifies):
            problems.append(f"{where}: the AR 'none of it identifies you.' sentence is not once after the licence")
            continue
        problems += _ar_general_problems(where, s8, fx["terms_s8_disclosure_ar"], fx, after=identifies)
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D4 no bare or narrowed not-sold sentence (RL10)
# ---------------------------------------------------------------------------


def test_s77_d4_no_bare_not_sold_sentence():
    """D4 (RL10): over the four legal sources, their four pre-fill snapshots, the four rendered legal pages (tags
    dropped, entities unescaped) and the four legal route payloads: every EN 'do not sell your personal data' sits
    inside the general promise and nothing says 'personal data is never sold'; every AR not-sold head is never
    followed by the narrowing qualifier and names OpenAI in its sentence; no retired EN / AR wording occurs. Positive
    control: the check flags the base P2 sentence, the base T8 tail, the spec's Option-B narrowing (EN + AR) and a
    bare AR head. RED at base: the bare sentences are present."""
    fx = _fx()
    # Positive control first (it holds at base and after the change).
    assert _en_not_sold_problems(P2_OLD_EN), "control: the base P2 sentence must be flagged"
    assert _en_not_sold_problems(T8_OLD_TAIL_EN), "control: the base T8 tail must be flagged"
    assert _en_not_sold_problems(NARROW_EN), "control: the Option-B narrowing must be flagged"
    assert not _en_not_sold_problems(P2_NEW_EN) and not _en_not_sold_problems(T8_TAIL_EN), "control: RL10 text passes"
    assert _ar_not_sold_problems(fx["narrow_promise_ar"], fx), "control: the AR narrowing must be flagged"
    assert _ar_not_sold_problems(fx["not_sold_head_ar"] + ".", fx), "control: a bare AR head must be flagged"
    assert [r for r in fx["retired_ar"] if r], "control: the retired AR list is empty"
    texts = []
    for rel in LEGAL_SOURCES:
        texts += list(_texts_with_snapshot(rel))
    for lang in LANGS:
        texts += [(PAGE_PRIVACY[lang], _plain(_read(PAGE_PRIVACY[lang]))), (PAGE_TERMS[lang], _plain(_read(PAGE_TERMS[lang])))]
        texts += [(f"API {doc} {lang}", _api(doc, lang)["content"]) for doc in ("privacy", "terms")]
    problems = []
    for where, text in texts:
        problems += [f"{where}: {p}" for p in _en_not_sold_problems(text)]
        problems += [f"{where}: {p}" for p in _ar_not_sold_problems(text, fx)]
        problems += _retired_problems(where, text, fx)
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D5 rendered pages and API
# ---------------------------------------------------------------------------


def _privacy_expected(lang):
    fx = _fx()
    if lang == "en":
        return (P2_NEW_EN, EXCHANGE_EN, PHOTOS_EN, _item_plain(P5G_NEW_EN), _item_plain(P5C_NEW_EN), OWN_TERMS_EN, S7_EN,
                EMAIL_RETENTION_EN)
    return (fx["privacy_s2_disclosure_ar"], fx["privacy_s4_exchange_ar"], fx["privacy_s4_photos_ar"],
            _item_plain(fx["privacy_s5_google_ar"]), _item_plain(fx["privacy_s5_cloudflare_ar"]),
            fx["privacy_s5_own_terms_ar"])


def _terms_expected(lang):
    fx = _fx()
    if lang == "en":
        return (T8_TAIL_EN[2:], T4_NEW_EN)
    return (fx["terms_s8_identifies_ar"], fx["terms_s8_disclosure_ar"], fx["terms_s4_limits_ar"])


def test_s77_d5a_landing_legal_regions_match_a_fresh_render():
    """D5a PIN (the render --check contract, spec section 4 step 5 / RL5): the committed region of each of the six
    landing legal pages equals scripts/render_legal_landing.py's render of its markdown source (line endings
    ignored). Passes at base; guards a hand edit inside a region or a stale render after the source edits."""
    renderer = _load(RENDERER, "_s77_renderer_d5a")
    assert renderer.stale_regions(REPO) == []


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d5_rendered_pages_and_api_serve_the_new_text(lang):
    """D5: the rendered privacy and terms pages (tags dropped, entities unescaped, bold dropped) and the legal route
    payloads (get_privacy_policy / get_terms_of_service with lang) carry every new text of their language whose
    wording is fixed (EN: P2 = RL10, P4, P5G, P5C, RL2, RL3, RL11, T8 = RL10, T4; AR: the spec's disclosure, P4,
    P5G, P5C, RL2, T8 sentences, T4), and last_updated is consent_service.TERMS_VERSION, later than 2026-10-11 (S78
    LR4 supersedes RL1; P21). RED at base."""
    from app.services.consent_service import TERMS_VERSION

    problems = []
    for doc, page, expected in (
        ("privacy", PAGE_PRIVACY[lang], _privacy_expected(lang)),
        ("terms", PAGE_TERMS[lang], _terms_expected(lang)),
    ):
        rendered = _plain(_read(page))
        body = _api(doc, lang)
        served = _plain(body["content"])
        if body.get("last_updated") != TERMS_VERSION or not TERMS_VERSION > "2026-10-11":
            problems.append(f"API {doc} {lang}: last_updated {body.get('last_updated')!r} (LR4: TERMS_VERSION, after 2026-10-11)")
        for sentence in expected:
            if sentence not in rendered:
                problems.append(f"{page}: lacks {_esc(sentence[:70])!r}")
            if sentence not in served:
                problems.append(f"API {doc} {lang}: lacks {_esc(sentence[:70])!r}")
    assert not problems, problems


# ---------------------------------------------------------------------------
# D6 privacy s5 names Google (Gmail)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d6_privacy_s5_names_google_gmail(lang):
    """D6, amended S78 (LR3, P17; node name kept): privacy s5 (live and snapshot) carries the email-providers line
    (P5C) and the sign-in-only Google line (P5G) exactly once each; 'only if you use Google Sign-In' (AR twin) is
    gone; the rendered privacy s5 names neither 'Gmail' nor 'Cloudflare', and the page carries
    '<strong>Our email providers:</strong>' (AR label) exactly once. RED at base."""
    fx = _fx()
    if lang == "en":
        lines, retired = (P5C_NEW_EN, P5G_NEW_EN), "only if you use Google Sign-In"
    else:
        lines, retired = (fx["privacy_s5_cloudflare_ar"], fx["privacy_s5_google_ar"]), fx["retired_ar"][2]
    problems = []
    for where, text in _texts_with_snapshot(PRIVACY[lang]):
        s5 = _section(text, 5)
        for line in lines:
            if text.count(line) != 1 or line not in s5:
                problems.append(f"{where} s5: {_esc(line[:40])!r} is not there exactly once")
        if retired in text:
            problems.append(f"{where}: the retired 'only if you use Google Sign-In' wording is back")
    page = _read(PAGE_PRIVACY[lang])
    rendered_s5 = _rendered_section(page, 5)
    for name in ("Gmail", "Cloudflare"):
        if name in rendered_s5:
            problems.append(f"{PAGE_PRIVACY[lang]}: the rendered s5 names {name} (LR3: by category)")
    label = P5C_LABEL_EN if lang == "en" else lines[0][len("- **"):lines[0].index(":**")]
    if page.count(f"<strong>{label}:</strong>") != 1:
        problems.append(f"{PAGE_PRIVACY[lang]}: <strong>{_esc(label)}:</strong> is not there exactly once")
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D7 processors.json
# ---------------------------------------------------------------------------


def test_s77_d7_processors_manifest_names_gmail():
    """D7, amended S78 (LR3, P18): app/legal/processors.json has exactly one row with id 'gmail', equal to spec row M
    (eleven keys since S78, exact values), placed directly after the cloudflare row; its category_en / category_ar
    occur inside section 5 of the EN / AR policy and its name_en / name_ar in neither policy (stricter than T7a).
    RED at base: no row."""
    rows = _json(MANIFEST)["rows"]
    ids = [row.get("id") for row in rows]
    assert ids.count("gmail") == 1, f"{MANIFEST}: {ids.count('gmail')} gmail row(s)"
    row = rows[ids.index("gmail")]
    assert row == ROW_M, row
    assert ids.index("gmail") == ids.index("cloudflare") + 1, "the gmail row must follow the cloudflare row"
    for lang, cat, name in (("en", "category_en", "name_en"), ("ar", "category_ar", "name_ar")):
        text = _read(PRIVACY[lang])
        assert row[cat] in _section(text, 5), f"{PRIVACY[lang]} s5 does not describe {_esc(row[cat])!r}"
        assert row[name] not in text, f"{PRIVACY[lang]} names {row[name]!r} (LR3: by category)"


# ---------------------------------------------------------------------------
# D8 landing index pages
# ---------------------------------------------------------------------------


def _lede(page):
    match = re.search(r'(?s)<p class="lede">(.*?)</p>', page)
    return " ".join(_plain(match.group(1)).split()) if match else None


def _og(page):
    match = re.search(r'<meta property="og:description" content="([^"]*)">', page)
    return html.unescape(match.group(1)) if match else None


def _index_claim_problems(lang, page, fx):
    problems = []
    if lang == "en":
        for pattern in (r"(?i)\bauthori[sz]ed\b", r"(?i)google\s*play", r"(?i)play\s*store"):
            if re.search(pattern, page):
                problems.append(f"matches {pattern!r}")
    else:
        problems += [f"carries {_esc(w)!r}" for w in fx["landing_forbidden_ar"] if w in page]
        if re.search(r"(?i)google\s*play", page):
            problems.append("names Google Play")
    return problems


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d8_landing_index_makes_no_authorized_or_google_play_claim(lang):
    """D8 (M4): landing/index.html has no 'authorized' / 'Google Play' / 'Play Store'; landing/ar/index.html none of
    the AR forbidden words and no 'Google Play'; each index page has exactly one store badge, naming the App Store;
    og:description and the lede equal the spec's L1 / L2 texts. Mirrors of the jest fences that cannot run in this
    worktree: 8 qaren.app|getmyez.com mentions per index page; the AR page keeps exactly 3 standalone uses of the old
    AR word, each followed by the AR 'between' or 'smartly' (landing.brand.s69.test.ts word-boundary rule, addresses
    stripped). Positive control: the base lede strings are flagged. RED at base."""
    fx = _fx()
    page = _read(INDEX[lang])
    lede, og, store = (LEDE_EN, OG_EN, "App Store") if lang == "en" else (
        fx["landing_lede_ar"], fx["landing_og_ar"], fx["app_store_ar"])
    old_lede = LEDE_OLD_EN if lang == "en" else None
    if old_lede is not None:
        assert _index_claim_problems(lang, old_lede, fx), "control: the base EN lede must be flagged"
    else:
        assert _index_claim_problems(lang, " ".join(fx["landing_forbidden_ar"]), fx), "control: the AR words must be flagged"
    problems = [f"{INDEX[lang]}: {p}" for p in _index_claim_problems(lang, page, fx)]
    badges = re.findall(r'<span class="store-badge">(.*?)</span></span>', page)
    if page.count('class="store-badge"') != 1 or len(badges) != 1 or store not in badges[0]:
        problems.append(f"{INDEX[lang]}: not exactly one store badge naming the App Store ({len(badges)})")
    if _og(page) != og:
        problems.append(f"{INDEX[lang]}: og:description is {_esc(_og(page))!r}")
    if _lede(page) != lede:
        problems.append(f"{INDEX[lang]}: the lede is {_esc(_lede(page))!r}")
    count = len(re.findall(r"qaren\.app|getmyez\.com", page))
    if count != 8:
        problems.append(f"{INDEX[lang]}: {count} qaren.app|getmyez.com mentions, the jest fence pins 8")
    if lang == "ar":
        scoped = ADDRESS_RE.sub(" ", page)
        word = re.compile("(?<!" + AR_LETTER + ")[" + chr(0x0628) + chr(0x0644) + chr(0x0648) + "]?" + re.escape(fx["verb_ar"]) + "(?!" + AR_LETTER + ")")
        follow = re.compile(" (?:" + "|".join(re.escape(w) for w in fx["verb_followers_ar"]) + ")")
        uses = [scoped[m.end():m.end() + 7] for m in word.finditer(scoped)]
        verbs = [u for u in uses if follow.match(u)]
        if len(verbs) != 3 or len(uses) != 3:
            problems.append(f"{INDEX[lang]}: {len(uses)} standalone old-brand words, {len(verbs)} verb uses (jest pins 3/3)")
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D9 /bot page vs the runtime
# ---------------------------------------------------------------------------


def _bot_paragraph(page, lang):
    match = re.search(r'<p lang="%s" dir="%s">(.*?)</p>' % (lang, "ltr" if lang == "en" else "rtl"), page, re.S)
    return match.group(1) if match else ""


def test_s77_d9_bot_page_claim_matches_the_runtime():
    """D9 (AX-01): landing/bot/index.html is pure ASCII; its meta description and EN paragraph equal the spec's L3
    text; the decoded AR paragraph starts with the spec's AR text; no 'honour(s)' claim; both paragraphs carry the
    robots_eval NAMED_AGENT, 'robots.txt' and mailto:support@getmyez.com; the only EN robots sentence names the
    site-discovery crawler. RUNTIME PIN (passes at base): the .py files under app/ and scripts/ that mention
    QarenBot or NAMED_AGENT are exactly the four measured emitters, the three non-defining ones evaluate robots.txt
    (can_fetch) or import search_descriptor_service, and no price look-up module sends the name (so the page must not
    claim robots.txt governs price look-ups). RED at base: the meta, the paragraphs and the 'honours' word."""
    # Runtime pin first.
    found = set()
    for top in ("app", "scripts"):
        for path in sorted((REPO / top).rglob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "QarenBot" in text or "NAMED_AGENT" in text:
                found.add(path.relative_to(REPO).as_posix())
    assert found == QARENBOT_FILES, f"QarenBot emitters changed (review the /bot text): {sorted(found ^ QARENBOT_FILES)}"
    for rel in sorted(QARENBOT_FILES - {ROBOTS_EVAL}):
        text = _read(rel)
        assert "can_fetch" in text or "search_descriptor_service" in text, f"{rel}: QarenBot without a robots.txt check"
    for rel in PRICE_LOOKUP_FILES:
        text = _read(rel)
        assert "QarenBot" not in text and "NAMED_AGENT" not in text, f"{rel}: a price look-up sends the crawler name"
    agent = re.search(r'^NAMED_AGENT = "([^"]+)"', _read(ROBOTS_EVAL), re.M).group(1)
    raw = (REPO / BOT).read_bytes()
    page = raw.decode("ascii", errors="replace").replace("\r\n", "\n")
    problems = []
    if any(b > 127 for b in raw):
        problems.append(f"{BOT}: non-ASCII bytes")
    meta = re.search(r'<meta name="description" content="([^"]*)">', page)
    if not meta or html.unescape(meta.group(1)) != BOT_META_EN:
        problems.append(f"{BOT}: the meta description is not the L3 text")
    en = _bot_paragraph(page, "en")
    ar = re.sub(r"&#x([0-9A-Fa-f]+);", lambda m: chr(int(m.group(1), 16)), _bot_paragraph(page, "ar"))
    if en != BOT_P_EN:
        problems.append(f"{BOT}: the EN paragraph is not the L3 text")
    if not ar.startswith(_fx()["bot_ar"]):
        problems.append(f"{BOT}: the AR paragraph does not start with the L3 AR text")
    if re.search(r"(?i)\bhonou?r\w*", page):
        problems.append(f"{BOT}: still claims to honour robots.txt")
    for lang, text in (("en", en), ("ar", ar)):
        for needle in (agent, "robots.txt", "mailto:support@getmyez.com"):
            if needle not in text:
                problems.append(f"{BOT} {lang}: lacks {needle!r}")
    robots_sentences = [s for s in re.split(r"(?<=\.)\s+", _plain(en)) if "robots.txt" in s]
    if robots_sentences != [BOT_ROBOTS_EN]:
        problems.append(f"{BOT}: the EN robots sentences are {robots_sentences!r}")
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D10 fill-in of the snapshot
# ---------------------------------------------------------------------------


def test_s77_d10_fill_in_of_the_snapshot_reproduces_the_sources(tmp_path):
    """D10: on a temp copy of the six pre-fill snapshots, fill_in_legal.plan with the committed data and variants
    reports no missing key and reproduces the live sources (line endings aside), and the filled privacy / terms carry
    the new texts of their language (D5's lists). RED at base: the live sources lack the texts."""
    fill = _load(FILL_SCRIPT, "_s77_fill_in_d10")
    root = tmp_path / "repo"
    for rel in SIX_SOURCES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes((REPO / _prefill(rel)).read_bytes())
    missing, outputs = fill.plan(root, _json(FILL_IN), _json(VARIANTS))
    assert missing == [], missing
    filled = {
        rel: (outputs[rel][0] if rel in outputs else (root / rel).read_bytes()).decode("utf-8").replace("\r\n", "\n")
        for rel in SIX_SOURCES
    }
    stale = [rel for rel in SIX_SOURCES if filled[rel] != _read(rel)]
    assert not stale, f"the fill-in of {PREFILL}/ does not reproduce {stale}"
    problems = []
    for lang in LANGS:
        for rel, expected in ((PRIVACY[lang], _privacy_expected(lang)), (TERMS[lang], _terms_expected(lang))):
            plain = _plain(filled[rel])
            problems += [f"filled {rel}: lacks {_esc(s[:70])!r}" for s in expected if s not in plain]
    assert not problems, problems


# ---------------------------------------------------------------------------
# D11 terms s4 limits
# ---------------------------------------------------------------------------


def _tier_limits():
    tree = ast.parse(_read(USAGE_SERVICE))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "TIER_LIMITS" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{USAGE_SERVICE}: no TIER_LIMITS")


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d11_terms_s4_states_the_coded_limits(lang):
    """D11 (RL6 keeps T4): terms s4 (live and snapshot) carries the T4 parenthesis exactly once and not 'after 3
    introductory comparisons' (AR twin); the numbers it states (3 a day, 10 a month, the first 3) equal
    TIER_LIMITS['free'] daily / monthly / lifetime_free read from usage_service.py with ast. RED at base."""
    fx = _fx()
    free = _tier_limits()["free"]
    assert (free["daily"], free["monthly"], free["lifetime_free"]) == (3, 10, 3), free
    new, old = (T4_NEW_EN, T4_OLD_EN) if lang == "en" else (fx["terms_s4_limits_ar"], fx["retired_ar"][4])
    # The digits the parenthesis states, section 9 aside (the AR spells "the first three" as a word).
    numbers = [int(n) for n in re.findall(r"\d+", new) if n != "9"]
    expected = [free["daily"], free["monthly"], free["lifetime_free"]] if lang == "en" else [free["daily"], free["monthly"]]
    assert numbers == expected, numbers
    problems = []
    for where, text in _texts_with_snapshot(TERMS[lang]):
        if text.count(new) != 1 or new not in _section(text, 4):
            problems.append(f"{where} s4: the T4 parenthesis is not there exactly once")
        if old in text:
            problems.append(f"{where}: the retired 'after 3 introductory comparisons' wording is back")
    assert not problems, problems


# ---------------------------------------------------------------------------
# D12 PIN the (k) scan
# ---------------------------------------------------------------------------


def test_s77_d12_new_sentences_pass_the_personal_data_scan():
    """D12 PIN (RL10: the general promise must pass the d3c (k) scan): the d3c module's _personal_data_claims finds
    no claim in any new EN constant (P2 = RL10, P4, P5G, P5C, RL2, RL11, T8 = RL10, T4), in any new AR fixture
    string, or in the four live legal sources. Passes at base for the constants and the base sources; it is the
    regression guard for the GREEN's AR general promise and the edited sources."""
    fx, scan = _fx(), _d3c()._personal_data_claims
    sentences = (
        GENERAL_EN, P2_DISCLOSURE_EN, P2_NEW_EN, EXCHANGE_EN, PHOTOS_EN, P5G_NEW_EN, P5C_NEW_EN, OWN_TERMS_EN,
        EMAIL_RETENTION_EN, T8_TAIL_EN, T4_NEW_EN,
        fx["privacy_s2_disclosure_ar"], fx["privacy_s4_exchange_ar"], fx["privacy_s4_photos_ar"],
        fx["privacy_s5_google_ar"], fx["privacy_s5_cloudflare_ar"], fx["privacy_s5_own_terms_ar"],
        fx["terms_s8_identifies_ar"], fx["terms_s8_disclosure_ar"], fx["terms_s4_limits_ar"],
    )
    flagged = [_esc(s[:60]) for s in sentences if scan(s)]
    flagged += [f"{rel}: {_esc(c[:100])}" for rel in LEGAL_SOURCES for c in scan(_read(rel))]
    assert not flagged, flagged


# ---------------------------------------------------------------------------
# D13 RL2 own-terms sentence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d13_privacy_s5_own_terms_names_google_as_mailbox_provider(lang):
    """D13 (RL2): privacy s5 (live and snapshot) carries the RL2 own-terms sentence (EN; the reviewer's AR twin from
    the fixture) exactly once, after the service-providers carve-out; the old sentence is gone; the rendered s5
    carries it. RED at base."""
    fx, d3c = _fx(), _d3c()
    if lang == "en":
        new, old, carveout = OWN_TERMS_EN, OWN_TERMS_OLD_EN, d3c.S5_CARVEOUT_EN
    else:
        new, old, carveout = fx["privacy_s5_own_terms_ar"], fx["retired_ar"][5], _d3c_fx()["fix2_ar"]["s5_carveout"]
    problems = []
    for where, text in _texts_with_snapshot(PRIVACY[lang]):
        s5 = _section(text, 5)
        if text.count(new) != 1 or new not in s5:
            problems.append(f"{where} s5: the RL2 own-terms sentence is not there exactly once")
        elif carveout not in s5 or s5.index(carveout) > s5.index(new):
            problems.append(f"{where} s5: the RL2 sentence does not follow the carve-out")
        if old in text:
            problems.append(f"{where}: the old own-terms sentence is back")
    if new not in _plain(_rendered_section(_read(PAGE_PRIVACY[lang]), 5)):
        problems.append(f"{PAGE_PRIVACY[lang]}: the rendered s5 lacks the RL2 sentence")
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D14 RL3 transfers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d14_privacy_s7_names_openai_and_google(lang):
    """D14, amended S78 (LR3, P19; node name kept): privacy s7 (live, snapshot and rendered) names the destination
    countries without a vendor mapping. EN: S7_EN ('... the United States and Germany (European Union)') exactly
    once; AR: the AR 'United States' and the fixture's germany_eu_ar; no vendor name and no '(OpenAI' anywhere in
    s7. RED at base: s7 says '(OpenAI)'."""
    fx = _fx()
    texts = list(_texts_with_snapshot(PRIVACY[lang]))
    sections = [(where, _section(text, 7)) for where, text in texts]
    sections.append((PAGE_PRIVACY[lang], _plain(_rendered_section(_read(PAGE_PRIVACY[lang]), 7))))
    problems = []
    for where, s7 in sections:
        if not s7.strip():
            problems.append(f"{where}: no section 7")
            continue
        if "(OpenAI" in s7:
            problems.append(f"{where} s7: still maps OpenAI to a country")
        problems += [f"{where} s7: names {name!r} (LR3)" for name in S7_VENDORS if re.search(r"\b" + name + r"\b", s7)]
        if lang == "en":
            if s7.count(S7_EN) != 1:
                problems.append(f"{where} s7: {S7_EN!r} is not there exactly once")
            continue
        if fx["us_ar"] not in s7 or fx["germany_eu_ar"] not in s7:
            problems.append(f"{where} s7: the AR United States / Germany (European Union) are not named")
        if re.search(re.escape(fx["us_ar"]) + r"\s*\(", s7):
            problems.append(f"{where} s7: a parenthesis follows the AR United States")
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D15 RL11 email retention and s3.2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d15_privacy_covers_email_sent_to_our_addresses(lang):
    """D15 (RL11): privacy (live and snapshot). s8: EN carries 'Email you send to our addresses: kept in our mailbox
    until we delete it; no fixed period.' exactly once (bold label markers ignored); AR (structure) has one s8 line
    naming email (the AR 'email'), our addresses and the AR 'no fixed period'. s3.2: the 'Feedback and messages'
    item (EN label / the AR label from the fixture) also covers email sent to our addresses (EN 'email' + 'our
    addresses'; AR the two AR words). The rendered s8 carries it too. RED at base."""
    fx = _fx()
    problems = []
    for where, text in _texts_with_snapshot(PRIVACY[lang]):
        s8, s32 = _section(text, 8), _subsection(text, "3.2")
        if lang == "en":
            if _plain(s8).count(EMAIL_RETENTION_EN) != 1 or _plain(text).count(EMAIL_RETENTION_EN) != 1:
                problems.append(f"{where} s8: the email retention line is not there exactly once")
            item = _line_with(s32, "**Feedback and messages:**")
            if item is None or not (re.search(r"(?i)\bemails?\b", item) and "our addresses" in item):
                problems.append(f"{where} s3.2: 'Feedback and messages' does not cover email sent to our addresses")
            continue
        words = (fx["email_ar"], fx["our_addresses_ar"], fx["no_fixed_period_ar"])
        lines = [line for line in s8.split("\n") if all(w in line for w in words)]
        if len(lines) != 1:
            problems.append(f"{where} s8: {len(lines)} line(s) naming email, our addresses and no fixed period")
        item = _line_with(s32, "**" + fx["feedback_label_ar"] + ":**")
        if item is None or fx["email_ar"] not in item or fx["our_addresses_ar"] not in item:
            problems.append(f"{where} s3.2: the AR feedback item does not cover email sent to our addresses")
    rendered_s8 = _plain(_rendered_section(_read(PAGE_PRIVACY[lang]), 8))
    if lang == "en" and EMAIL_RETENTION_EN not in rendered_s8:
        problems.append(f"{PAGE_PRIVACY[lang]}: the rendered s8 lacks the email retention line")
    if lang == "ar" and not (fx["email_ar"] in rendered_s8 and fx["our_addresses_ar"] in rendered_s8):
        problems.append(f"{PAGE_PRIVACY[lang]}: the rendered s8 does not name email sent to our addresses")
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# D16 landing/README.md
# ---------------------------------------------------------------------------


def test_s77_d16_landing_readme_lines_updated():
    """D16 (spec L4 + RL4): landing/README.md describes the /bot page as the spec's L4 line-30 text; line 43's note
    (and every other line) no longer says the crawler honours robots.txt; the badge line reads '**App Store badge:**
    present but' and records that the Google Play badge was removed in S77; no 'App Store + Google Play badges'.
    RED at base."""
    text = _read(README)
    problems = []
    bot_line = _line_with(text, "bot/index.html ")
    if bot_line is None or README_BOT_NEW not in bot_line:
        problems.append("the bot/index.html tree line is not the L4 text")
    if re.search(r"(?i)\bhonou?r\w*", text):
        problems.append("still says the crawler honours robots.txt")
    badge = _line_with(text, README_BADGE_NEW)
    if badge is None or not badge.rstrip().endswith(README_BADGE_NOTE):
        problems.append("the badge line is not '**App Store badge:** present but ... " + README_BADGE_NOTE + "'")
    if "App Store + Google Play badges" in text:
        problems.append("still lists App Store + Google Play badges")
    assert not problems, problems


# ---------------------------------------------------------------------------
# D17 / D18 FIX round (rulings RF1, RF2; the final adversary's major and first minor finding)
# ---------------------------------------------------------------------------

# RF1: privacy s7, the TRANSFER_BASIS 'false' variant (the snapshot carries <PLACEHOLDER:TRANSFER_BASIS>).
# S78 (LR3, P20): the mailbox provider without a vendor name; the basis is no stronger than RF1's.
S7_TRANSFER_EN = (
    "We transfer data to our service providers, which are required by contract to protect it, and to our mailbox "
    "provider, which handles email under its own terms (section 5)."
)
S7_TRANSFER_OLD_EN = "We transfer data only to providers that are required by contract to protect it."
# RF2: privacy s9, plain text (live and snapshot; the snapshot carries the PRIVACY_EMAIL token).
S9_EMAIL_EN = (
    "Email you sent to our addresses stays in our mailbox until we delete it; ask us at privacy@getmyez.com if you "
    "want it deleted too."
)
PRIVACY_ADDRESS = "privacy@getmyez.com"
PRIVACY_EMAIL_TOKEN = "<PLACEHOLDER:PRIVACY_EMAIL>"
SITE_ADDRESS_RE = re.compile(r"qaren\.app|getmyez\.com")
# Mirror of SmartCompareApp/__tests__/landing.brand.s69.test.ts ADDRESS_COUNTS for privacy.html and ar/privacy.html,
# moved 10 -> 11 by the RF2 sentence (jest cannot run in this worktree), and 11 -> 14 by S78 (P22, re-measured
# 2026-10-14): the interim postal line names privacy@getmyez.com in s1 and s16 and s5 adds the on-request sentence.
# A later P.O. Box re-fill moves it 14 -> 12 (re-measure then).
PRIVACY_PAGE_ADDRESSES = 14


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d17_privacy_s7_transfer_sentence_covers_the_mailbox(lang):
    """D17 (RF1): privacy s7 no longer says that we transfer data ONLY to providers required by contract to protect
    it (the Gmail mailbox acts under Google's own terms, s5 and limit L4). The live s7, the TRANSFER_BASIS 'false'
    variant that the fill-in puts in place of the snapshot's token, the rendered s7 and the API payload carry the new
    sentence (EN exact; AR the fixture's privacy_s7_transfer_ar) exactly once; the old categorical sentence (EN and
    the fixture's privacy_s7_retired_ar) is in none of them, nor in the snapshot or the variants file. The new
    sentence passes the d3c (k) scan. RED against the GREEN bytes: the old sentence is there."""
    fx = _fx()
    new = {"en": S7_TRANSFER_EN, "ar": fx["privacy_s7_transfer_ar"]}[lang]
    old = {"en": S7_TRANSFER_OLD_EN, "ar": fx["privacy_s7_retired_ar"]}[lang]
    problems = []
    live = _read(PRIVACY[lang])
    if live.count(new) != 1 or new not in _section(live, 7):
        problems.append(f"{PRIVACY[lang]} s7: the new transfer sentence is not there exactly once")
    variant = _json(VARIANTS)["clauses"]["TRANSFER_BASIS"][lang]["privacy"]["false"]
    if variant != new:
        problems.append(f"{VARIANTS}: TRANSFER_BASIS {lang} 'false' is not the new transfer sentence")
    snapshot = _read(_prefill(PRIVACY[lang]))
    if "<PLACEHOLDER:TRANSFER_BASIS>" not in _section(snapshot, 7):
        problems.append(f"{_prefill(PRIVACY[lang])} s7: the TRANSFER_BASIS token is gone")
    page = _read(PAGE_PRIVACY[lang])
    rendered = _plain(page)
    if rendered.count(new) != 1 or new not in _plain(_rendered_section(page, 7)):
        problems.append(f"{PAGE_PRIVACY[lang]}: the rendered s7 does not carry the new transfer sentence once")
    served = _plain(_api("privacy", lang)["content"])
    if served.count(new) != 1:
        problems.append(f"API privacy {lang}: the new transfer sentence is not served exactly once")
    for where, text in (
        (PRIVACY[lang], live),
        (_prefill(PRIVACY[lang]), snapshot),
        (VARIANTS, _read(VARIANTS)),
        (PAGE_PRIVACY[lang], rendered),
        (f"API privacy {lang}", served),
    ):
        if old in text:
            problems.append(f"{where}: the old categorical transfer sentence is back")
    if _d3c()._personal_data_claims(new):
        problems.append("the new transfer sentence trips the d3c (k) scan")
    assert not problems, [_esc(p) for p in problems]


@pytest.mark.parametrize("lang", LANGS)
def test_s77_d18_privacy_s9_says_email_survives_account_deletion(lang):
    """D18 (RF2): privacy s9 says that email sent to our addresses stays in our mailbox until we delete it and how
    to ask for its deletion. The live s9, the rendered s9 and the API payload carry the sentence (EN exact; AR the
    fixture's privacy_s9_email_ar) exactly once; the snapshot s9 carries it once with <PLACEHOLDER:PRIVACY_EMAIL> in
    place of the address (the fill-in substitutes it). The sentence passes the d3c (k) scan. Both privacy pages now
    carry PRIVACY_PAGE_ADDRESSES site addresses (the pytest mirror of the jest ADDRESS_COUNTS pin; 14 since S78).
    RED against the GREEN bytes: the sentence is absent."""
    fx = _fx()
    new = {"en": S9_EMAIL_EN, "ar": fx["privacy_s9_email_ar"]}[lang]
    problems = []
    if new.count(PRIVACY_ADDRESS) != 1:
        problems.append("the expected s9 sentence does not name the privacy address once")
    live = _read(PRIVACY[lang])
    if live.count(new) != 1 or new not in _section(live, 9):
        problems.append(f"{PRIVACY[lang]} s9: the email sentence is not there exactly once")
    snapshot = _read(_prefill(PRIVACY[lang]))
    tokenised = new.replace(PRIVACY_ADDRESS, PRIVACY_EMAIL_TOKEN)
    if snapshot.count(tokenised) != 1 or tokenised not in _section(snapshot, 9):
        problems.append(f"{_prefill(PRIVACY[lang])} s9: the email sentence (with the PRIVACY_EMAIL token) is not there once")
    page = _read(PAGE_PRIVACY[lang])
    if _plain(page).count(new) != 1 or new not in _plain(_rendered_section(page, 9)):
        problems.append(f"{PAGE_PRIVACY[lang]}: the rendered s9 does not carry the email sentence once")
    if _plain(_api("privacy", lang)["content"]).count(new) != 1:
        problems.append(f"API privacy {lang}: the email sentence is not served exactly once")
    if _d3c()._personal_data_claims(new):
        problems.append("the s9 email sentence trips the d3c (k) scan")
    count = len(SITE_ADDRESS_RE.findall(page))
    if count != PRIVACY_PAGE_ADDRESSES:
        problems.append(f"{PAGE_PRIVACY[lang]}: {count} site addresses, the jest ADDRESS_COUNTS pin says {PRIVACY_PAGE_ADDRESSES}")
    assert not problems, [_esc(p) for p in problems]
