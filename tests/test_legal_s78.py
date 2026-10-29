"""S78-LEGAL: personal data out of the served legal surfaces, recipients by category, ToS v2 (RED file).

Spec: sc-s78-legal/.qa-s78/S78_LEGAL_UNIT_SPEC.md section 5 (R1-R26), as amended by the binding rulings
RULINGS_S78_LEGAL.md (LR1-LR11) and RULINGS_S78_LEGAL_SPEC_REVIEW.md (LT1-LT11, M1-M10, M2 / M6 / Q2 / Q9).

LR8: this file is pure ASCII and pattern based. It never embeds the controller's home address, a house / block /
road number, a phone number or a personal email; the town check compares sha256 digests of normalised
1- to 3-word windows with a GENERIC list of Bahraini town names (fixture bahrain_towns_latin). The
controller name is read from the fill-in data file. Arabic markers live in the fixture (read as UTF-8); failure
messages escape non-ASCII. Hermetic: file reads, temp copies for fill-ins, the legal route handlers called
directly, no network.

Nodes (PIN = green at base by design; every other node is RED at base for the reason in its docstring):
  R1   no street-component + digit pattern in any served surface (EN + AR)
  R2   no Bahraini town name (generic list) in any served surface
  R3   no personal email / +973 / Bahrain 8-digit shape in surfaces and the two crawler User-Agents
  R4   both User-Agents equal the LR7 value; landing/bot names the same contact
  R5   no '@gmail.com' string constant in app/ or scripts/
  Q9   (LR7b) package authors carry the role address; the abuse test carries no personal-looking address
  R6   identification lines: name, field of activity, trade name, postal line; the name nowhere else
  R7   the postal values are the interim line (LR1) or a bare P.O. Box; PRIVACY_EMAIL inside the interim line (M10)
  R8   PIN: OpenAI, Apple, Google stay named
  R9   privacy s5 lists recipients by category; manifest categories appear in the policy
  R10  no infrastructure vendor name in the legal surfaces; no Google in privacy s7
  R11  the on-request sentence (LR3 verbatim); the s5 carve-out names the mailbox provider (LT10)
  R12  transfers name countries only (M4 role words); the TRANSFER_BASIS sentence; no stronger basis
  R13  ToS s16 carries the Exhibit B items (LT2, LT3, LT8, LT9); no licence-grant wording
  R14  ToS s12 opens with the carve-outs (LT6 in Arabic); applicable-law qualifiers; no money cap
  R15  the under-18 guardian sentence in ToS s3 and privacy s12
  R16  ToS v2: 19 headings and the per-section markers (M3 case, LT1, LT5, LT11)
  R17  EN/AR structural parity (privacy, terms, support; filled and snapshot)
  R18  the twelve anchors are one date, later than 2026-10-11; legal_routes derives it
  R19  PIN: render --check clean and the fill-in idempotent
  R20  the P.O. Box swap is a data-only re-fill; the address-count delta (M2)
  R21  no security internals in the privacy policy
  R22  manifest category keys; hosts / modules unchanged
  R23  privacy s11 direct-marketing sentence (LT4) and s15 material-change sentence (LT5)
  R24  PIN: privacy keeps the required elements (LR6)
  R25  the new ToS sentences exist and pass the d3c claim scan, the S77 not-sold rule and the copy policy
  R26  the retired sentences are gone everywhere
  M1   every {value} clause's longest literal is absent when its value is empty; empty regions still fill
"""
import ast
import asyncio
import functools
import hashlib
import html
import importlib.util
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

FIXTURE = "tests/fixtures/legal_s78.json"
FILL_IN = "tests/fixtures/legal_fill_in_u8.json"
VARIANTS = "scripts/legal_variants_u8.json"
MANIFEST = "app/legal/processors.json"
PREFILL = "tests/fixtures/legal_prefill_u8"
FILL_SCRIPT = "scripts/fill_in_legal.py"
RENDERER = "scripts/render_legal_landing.py"
LEGAL_ROUTES = "app/api/legal_routes.py"
COPY_POLICY = "SmartCompareApp/src/i18n/.copy-policy.json"
U8_TESTS = "tests/test_legal_docs_u8.py"
D3C_TESTS = "tests/test_legal_docs_u8_d3c.py"
S77_TESTS = "tests/test_legal_disclosure_s77.py"
UA_FILES = (
    ("app/services/robots_eval.py", "QARENBOT_UA"),  # S81-15 R-S15-6: the ONE live UA definition moved here
    ("scripts/resolve_search_descriptors.py", "USER_AGENT"),
)
LANGS = ("en", "ar")
DOCS = ("privacy", "terms", "support")
MD = {
    ("en", "privacy"): "app/legal/privacy_policy.md",
    ("en", "terms"): "app/legal/terms_of_service.md",
    ("en", "support"): "app/legal/support_contact.md",
    ("ar", "privacy"): "app/legal/privacy_policy_ar.md",
    ("ar", "terms"): "app/legal/terms_of_service_ar.md",
    ("ar", "support"): "app/legal/support_contact_ar.md",
}
PAGES = {
    ("en", "privacy"): "landing/privacy.html",
    ("en", "terms"): "landing/terms.html",
    ("en", "support"): "landing/support.html",
    ("ar", "privacy"): "landing/ar/privacy.html",
    ("ar", "terms"): "landing/ar/terms.html",
    ("ar", "support"): "landing/ar/support.html",
}
REGION_BEGIN = "<!-- legal:begin -->"
REGION_END = "<!-- legal:end -->"
ROLE_EMAILS = ("privacy@getmyez.com", "support@getmyez.com")
LR7_UA = "QarenBot/1.0 (+https://getmyez.com/bot; contact: support@getmyez.com)"
ACTIVITY_EN = "an individual app developer in the Kingdom of Bahrain"
TRADE_EN = "trading as MYEZ"
TOKEN = re.compile(r"<PLACEHOLDER:([A-Z][A-Z0-9_]*)>")
SITE_ADDRESS = re.compile(r"qaren\.app|getmyez\.com")


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------


def _read(rel, root=REPO):
    p = Path(root) / rel
    return p.read_text(encoding="utf-8").replace("\r\n", "\n") if p.is_file() else None


def _json(rel, root=REPO):
    return json.loads(_read(rel, root))


@functools.lru_cache(maxsize=None)
def _fx():
    return _json(FIXTURE)


def _data():
    return _json(FILL_IN)


def _esc(text):
    return str(text).encode("unicode_escape").decode("ascii")


def _report(title, problems):
    return title + "\n  - " + "\n  - ".join(_esc(p) for p in problems)


def _load(rel, name, root=REPO):
    spec = importlib.util.spec_from_file_location(name, Path(root) / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def _section(text, number):
    m = re.search(r"(?ms)^## " + re.escape(str(number)) + r"\.[^\n]*\n(.*?)(?=^## |\Z)", text or "")
    return m.group(1) if m else ""


def _region(page_text):
    if not page_text or page_text.count(REGION_BEGIN) != 1 or page_text.count(REGION_END) != 1:
        return ""
    return page_text.split(REGION_BEGIN, 1)[1].split(REGION_END, 1)[0]


def _plain(text):
    """HTML reduced to its words: tags dropped, entities unescaped, runs of spaces collapsed."""
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or "")))


def _regions():
    """{(lang, doc): plain text of the legal region of the page}."""
    return {key: _plain(_region(_read(rel))) for key, rel in PAGES.items()}


def _payloads():
    """{(doc, lang): content} from the legal route handlers, called directly."""
    from app.api import legal_routes

    out = {}
    for doc, handler in (("privacy", legal_routes.get_privacy_policy), ("terms", legal_routes.get_terms_of_service)):
        for lang in LANGS:
            body = asyncio.run(handler(lang=lang))
            out[(doc, lang)] = body
    return out


def _landing_pages():
    return sorted(p.relative_to(REPO).as_posix() for p in (REPO / "landing").rglob("*.html"))


def _surfaces():
    """(label, text) for every served legal surface (spec section 5 SURFACES)."""
    out = [(rel, _read(rel) or "") for rel in MD.values()]
    out += [(f"region {PAGES[k]}", t) for k, t in _regions().items()]
    out += [(f"API {d} {l}", body["content"]) for (d, l), body in _payloads().items()]
    out += [(rel, html.unescape(_read(rel) or "")) for rel in _landing_pages()]
    return out


def _ua_values():
    from app.services import robots_eval

    out = {}
    for rel, name in UA_FILES:
        m = re.search(name + r'\s*=\s*"([^"]*)"\s*%', _read(rel) or "")
        out[rel] = (m.group(1) % (robots_eval.NAMED_AGENT,)) if m else None
    return out


def _name_in(name, text):
    """Whole-word match; an Arabic proclitic b/l/w may be attached (test_legal_docs_u8 idiom)."""
    return re.search("(?<!\\w)[\u0628\u0644\u0648]?" + re.escape(name) + "(?!\\w)", text or "") is not None


# ---------------------------------------------------------------------------
# Personal-data patterns (LR8)
# ---------------------------------------------------------------------------

_DIGIT = "[0-9\u0660-\u0669\u06f0-\u06f9]"
STREET_EN = re.compile(
    r"(?i)\b(?:block|blk|road|rd|street|str|st|avenue|ave|building|bldg|flat|apartment|apt|house|home|villa|lane"
    r"|way|office|unit|floor)\b\.?\s*(?:no\.?|number|#)?\s*" + _DIGIT
)
_AR_STREET_WORDS = (
    "\u0645\u062c\u0645\u0639", "\u0637\u0631\u064a\u0642", "\u0634\u0627\u0631\u0639", "\u0645\u0646\u0632\u0644",
    "\u0628\u064a\u062a", "\u0645\u0628\u0646\u0649", "\u0639\u0645\u0627\u0631\u0629", "\u0628\u0646\u0627\u064a\u0629",
    "\u0634\u0642\u0629", "\u0641\u064a\u0644\u0627", "\u062c\u0627\u062f\u0629", "\u0645\u0643\u062a\u0628",
    "\u0637\u0627\u0628\u0642",
)
STREET_AR = re.compile("(?:" + "|".join(_AR_STREET_WORDS) + ")\\s*(?:\u0631\u0642\u0645\\s*)?" + _DIGIT)
GMAIL = re.compile(r"(?i)@gmail\.com")
PLUS_973 = re.compile(r"(?:\+|00)\s*973")
BH_NUMBER = re.compile(r"(?<![\d.,])(?:3\d|6[69]|1[37])\d{2}[\s-]?\d{4}(?![\d.,])")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
PO_BOX_EN = re.compile(r"(?i)\bP\.?\s?O\.?\s?Box\s+\d{1,6}\b")
PO_BOX_AR = re.compile("\u0635\\.?\\s?\u0628\\.?\\s*\\d{1,6}")


def _street_hits(text):
    return [m.group(0) for rx in (STREET_EN, STREET_AR) for m in rx.finditer(text or "")]


def normalise(text):
    """NFKC, casefold, Arabic diacritics / dagger alef / tatweel dropped, non-letters to spaces, spaces collapsed."""
    t = unicodedata.normalize("NFKC", text or "").casefold()
    t = re.sub("[\u064b-\u065f\u0670\u0640]", "", t)
    t = "".join(c if c.isalpha() else " " for c in t)
    return " ".join(t.split())


def _town_hits(text, digests):
    words = normalise(text).split()
    hits = 0
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            if hashlib.sha256(" ".join(words[i:i + n]).encode("utf-8")).hexdigest() in digests:
                hits += 1
    return hits


def _town_digests(fx):
    """sha256 of every normalised town in the generic Bahraini town list (fixture bahrain_towns_latin)."""
    return {hashlib.sha256(normalise(name).encode("utf-8")).hexdigest() for name in fx["bahrain_towns_latin"]}


def _contact_problems(text):
    """R3 over one text: no Gmail, no +973, no Bahrain-shaped number, only the two role addresses."""
    problems = []
    if GMAIL.search(text):
        problems.append("an @gmail.com address")
    if PLUS_973.search(text):
        problems.append("a +973 / 00973 phone shape")
    if BH_NUMBER.search(text):
        problems.append("a Bahrain-shaped 8-digit number")
    others = sorted({m.group(0).lower() for m in EMAIL.finditer(text)} - set(ROLE_EMAILS))
    problems += [f"email other than the role addresses ({len(others)})"] if others else []
    return problems


# ---------------------------------------------------------------------------
# R1-R5, Q9: personal data
# ---------------------------------------------------------------------------


def test_s78_r1_no_street_number_pattern_in_served_surfaces():
    """R1 (LR1, LR8): no street-component word followed by a digit (EN + AR, Western and Arabic-Indic digits) on any
    served surface. Positive control first. RED at base: the residential address on every privacy / terms /
    support surface."""
    for sample in ("Block 12", "Rd. 5", "house no. 7", "Road #3", "\u0645\u062c\u0645\u0639 12",
                   "\u0645\u062c\u0645\u0639 \u0661\u0662", "\u0637\u0631\u064a\u0642 \u0631\u0642\u0645 4"):
        assert _street_hits(sample), "control: the pattern must flag " + _esc(sample)
    assert not _street_hits("section 4, 13 years, 3 a day, 1st, 3rd, 2026"), "control: no false positive"
    problems = [f"{label}: {len(_street_hits(text))} street-number hit(s)" for label, text in _surfaces() if _street_hits(text)]
    assert not problems, _report("R1: street-number pattern in served surfaces:", problems)


def test_s78_r2_no_home_town_token_in_served_surfaces():
    """R2 (LR8, gate): no 1-3 word window of a normalised surface is a Bahraini town name. Control: a synthetic
    digest added to a copy of the list is found in a synthetic text. RED at base: the town is inside the address."""
    digests = _town_digests(_fx())
    assert digests and all(re.fullmatch(r"[0-9a-f]{64}", d) for d in digests)
    synthetic = hashlib.sha256(normalise("Synthetic Town").encode("utf-8")).hexdigest()
    assert _town_hits("Lorem SYNTHETIC-town 1234 ipsum", digests | {synthetic}) == 1, "control"
    assert _town_hits("Lorem ipsum", digests | {synthetic}) == 0, "control"
    problems = [f"{label}: {n} window(s)" for label, text in _surfaces() if (n := _town_hits(text, digests))]
    assert not problems, _report("R2: a Bahraini town name on a served surface:", problems)


def test_s78_r3_no_personal_email_or_phone_in_served_text_and_user_agents():
    """R3 (LR2, LR7, LR8): over every surface and both formatted crawler User-Agents: no @gmail.com, no +973, no
    Bahrain-shaped number, and every email address is privacy@ or support@getmyez.com. Positive control first.
    RED at base: both User-Agents carry a personal Gmail address."""
    assert _contact_problems("x@gmail.com +973 3000 0000 a@b.example.org"), "control"
    assert len(_contact_problems("call 00973 66000000")) == 2, "control: both phone shapes"
    assert not _contact_problems("privacy@getmyez.com, 3 a day, 2026-10-14, 1300px"), "control: clean text passes"
    texts = list(_surfaces()) + [(f"User-Agent {rel}", ua or "") for rel, ua in _ua_values().items()]
    problems = [f"{label}: {p}" for label, text in texts for p in _contact_problems(text)]
    assert not problems, _report("R3: personal contact data:", problems)


def test_s78_r4_user_agent_is_the_lr7_value():
    """R4 (LR7): both formatted User-Agents equal the LR7 value and landing/bot names the same contact. RED at base:
    the contact is a personal address."""
    uas = _ua_values()
    problems = [f"{rel}: User-Agent differs from the LR7 value" for rel, ua in uas.items() if ua != LR7_UA]
    if "mailto:support@getmyez.com" not in (_read("landing/bot/index.html") or ""):
        problems.append("landing/bot/index.html: no mailto:support@getmyez.com")
    assert not problems, _report("R4:", problems)


def _string_constants(rel):
    tree = ast.parse(_read(rel) or "", filename=rel)
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def test_s78_r5_no_gmail_literal_in_app_or_scripts():
    """R5 (LR7): no string constant (AST) in app/**/*.py or scripts/**/*.py contains '@gmail.com'. RED at base: the
    two User-Agent literals."""
    files = sorted(p.relative_to(REPO).as_posix() for d in ("app", "scripts") for p in (REPO / d).rglob("*.py"))
    assert len(files) > 50, "control: the walk found the source trees"
    problems = [rel for rel in files if any(GMAIL.search(s) for s in _string_constants(rel))]
    assert not problems, _report("R5: '@gmail.com' string constants:", problems)


GENERIC_LOCAL_PARTS = {"user", "real", "test", "example", "someone", "name"}


def test_s78_q9_no_personal_email_in_package_authors_or_test_values():
    """Q9 / LR7b (spec-review ruling): pyproject.toml and backend/pyproject.toml carry support@getmyez.com as the
    authors email and no Gmail address; tests/test_abuse_detection.py carries no personal-looking Gmail address
    (every Gmail local part is a generic word) and keeps a legitimate-domain example.com value. RED at base: both
    authors entries and one test value."""
    problems = []
    for rel in ("pyproject.toml", "backend/pyproject.toml"):
        text = _read(rel) or ""
        authors = re.search(r"(?ms)^authors\s*=\s*\[(.*?)\]", text)
        emails = re.findall(r'email\s*=\s*"([^"]*)"', authors.group(1)) if authors else []
        if emails != ["support@getmyez.com"]:
            problems.append(f"{rel}: authors email is not support@getmyez.com ({len(emails)} email(s))")
        if GMAIL.search(text):
            problems.append(f"{rel}: an @gmail.com address")
    text = _read("tests/test_abuse_detection.py") or ""
    locals_ = re.findall(r"([A-Za-z0-9._%+-]+)@gmail\.com", text)
    odd = [p for p in locals_ if p.lower() not in GENERIC_LOCAL_PARTS]
    if odd:
        problems.append(f"tests/test_abuse_detection.py: {len(odd)} personal-looking Gmail value(s)")
    if not re.search(r'"[A-Za-z0-9._%+-]+@example\.com"', text):
        problems.append("tests/test_abuse_detection.py: no example.com legitimate-domain value")
    assert not problems, _report("Q9:", problems)


# ---------------------------------------------------------------------------
# R6-R7: identity and postal line
# ---------------------------------------------------------------------------


def test_s78_r6_controller_line_is_name_activity_and_postal_line():
    """R6 (LR2): privacy s1, ToS s1 and the support line (EN / AR) each have one line with the controller name, the
    field of activity, the trade name (EN 'trading as MYEZ', AR per LT7) and that language's postal value; privacy
    s16 and ToS s19 hold the postal value; the name occurs exactly once in each markdown file and each legal region.
    RED at base: no activity phrase, no trade name, no POSTAL_ADDRESS_AR."""
    fx, ph = _fx(), _data()["placeholders"]
    name = ph.get("CONTROLLER_NAME") or ""
    assert name.strip(), "CONTROLLER_NAME is empty"
    postal = {"en": ph.get("POSTAL_ADDRESS") or "", "ar": ph.get("POSTAL_ADDRESS_AR") or ""}
    activity = {"en": ACTIVITY_EN, "ar": fx["activity_ar"]}
    trade = {"en": TRADE_EN, "ar": fx["trade_clause_ar"] + "MYEZ"}
    problems = []
    for lang in LANGS:
        if not postal[lang]:
            problems.append(f"{lang}: no postal value in the fill-in data")
            continue
        for doc in DOCS:
            text = _read(MD[(lang, doc)]) or ""
            scope = text if doc == "support" else _section(text, 1)
            lines = [l for l in scope.split("\n") if name in l and activity[lang] in l and trade[lang] in l and postal[lang] in l]
            if len(lines) != 1:
                problems.append(f"{MD[(lang, doc)]}: {len(lines)} identification line(s) with name, activity, trade name and postal value")
        for doc, n in (("privacy", 16), ("terms", 19)):
            if postal[lang] not in _section(_read(MD[(lang, doc)]), n):
                problems.append(f"{MD[(lang, doc)]} s{n}: no postal value")
    for key, rel in MD.items():
        if (_read(rel) or "").count(name) != 1:
            problems.append(f"{rel}: the name occurs {(_read(rel) or '').count(name)} times, not once")
    for key, text in _regions().items():
        if text.count(name) != 1:
            problems.append(f"region {PAGES[key]}: the name occurs {text.count(name)} times, not once")
    assert not problems, _report("R6:", problems)


def _postal_problems(value, lang, privacy_email, fx):
    if not isinstance(value, str) or not value.strip():
        return ["empty or missing"]
    problems = []
    if _street_hits(value):
        problems.append("matches R1")
    if _town_hits(value, _town_digests(fx)):
        problems.append("matches R2")
    country = "Kingdom of Bahrain" if lang == "en" else fx["postal_ar_markers"][0]
    po = (PO_BOX_EN if lang == "en" else PO_BOX_AR).search(value)
    if country in value and "@" in value:
        if privacy_email not in value:
            problems.append("interim form without PRIVACY_EMAIL (M10)")
        if lang == "ar" and value != fx["postal_address_ar_interim"]:
            problems.append("AR interim value differs from the fixture's (M6)")
        if lang == "en" and "available on request" not in value:
            problems.append("interim form without 'available on request' (LR1)")
    elif po:
        rest = value[:po.start()] + value[po.end():]
        if re.search(r"[0-9\u0660-\u0669\u06f0-\u06f9]", rest):
            problems.append("a digit run besides the P.O. Box number")
    else:
        problems.append("neither the LR1 interim line nor a P.O. Box")
    return problems


def test_s78_r7_postal_values_are_interim_or_po_box():
    """R7 (LR1, M6, M10): POSTAL_ADDRESS and POSTAL_ADDRESS_AR exist; neither matches R1 / R2; each is the interim
    line (country + PRIVACY_EMAIL; the AR value equals the fixture's) or a bare P.O. Box with no other digit run.
    Control: the synthetic P.O. Box values pass, a street value fails. RED at base: a residence, no AR key."""
    fx, ph = _fx(), _data()["placeholders"]
    email = ph.get("PRIVACY_EMAIL") or ""
    assert not _postal_problems("P.O. Box 0000, Kingdom of Bahrain", "en", email, fx), "control"
    assert not _postal_problems("\u0635.\u0628 0000\u060c \u0645\u0645\u0644\u0643\u0629 \u0627\u0644\u0628\u062d\u0631\u064a\u0646", "ar", email, fx), "control"
    assert _postal_problems("Flat 1, Road 2, Kingdom of Bahrain", "en", email, fx), "control"
    problems = [f"{key}: {p}" for key, lang in (("POSTAL_ADDRESS", "en"), ("POSTAL_ADDRESS_AR", "ar"))
                for p in _postal_problems(ph.get(key), lang, email, fx)]
    assert not problems, _report("R7:", problems)


# ---------------------------------------------------------------------------
# R8-R12: privacy recipients and transfers
# ---------------------------------------------------------------------------


def test_s78_r8_openai_apple_google_stay_named():
    """R8 PIN (green at base by design; LR3 allow-list guard): OpenAI in privacy s4 and s5 and ToS s8; Apple and
    Google in privacy s5; Apple in ToS s16 (EN and AR)."""
    problems = []
    for lang in LANGS:
        p, t = _read(MD[(lang, "privacy")]), _read(MD[(lang, "terms")])
        for where, text, name in (("privacy s4", _section(p, 4), "OpenAI"), ("privacy s5", _section(p, 5), "OpenAI"),
                                  ("terms s8", _section(t, 8), "OpenAI"), ("privacy s5", _section(p, 5), "Apple"),
                                  ("privacy s5", _section(p, 5), "Google"), ("terms s16", _section(t, 16), "Apple")):
            if not _name_in(name, text):
                problems.append(f"{lang} {where}: {name} not named")
    assert not problems, _report("R8:", problems)


S5_LABELS_EN = (
    "Our database and sign-in provider", "Our hosting provider", "Our temporary-storage provider",
    "Our error-reporting provider", "Our notification and update provider", "Web search and page-retrieval providers",
    "Our email providers", "The retailer websites and store search services we query",
)


def test_s78_r9_privacy_s5_lists_recipients_by_category():
    """R9 (LR3): privacy s5 carries the category list items (EN labels, AR fixture labels); every personal manifest
    row with an open gate has its category_en / category_ar in privacy EN / AR. RED at base: vendor rows, no
    category keys."""
    fx, data = _fx(), _data()
    problems = []
    for lang, labels in (("en", S5_LABELS_EN), ("ar", fx["categories_s5_ar"])):
        s5 = _section(_read(MD[(lang, "privacy")]), 5)
        problems += [f"{lang} s5: no list item labelled {label!r}" for label in labels if f"- **{label}:**" not in s5]
    flags = data.get("flags") or {}
    for row in _json(MANIFEST)["rows"]:
        if not row.get("personal_data") or (row.get("gate_flag") and flags.get(row["gate_flag"]) != "on"):
            continue
        for lang, key in (("en", "category_en"), ("ar", "category_ar")):
            cat = row.get(key)
            if not isinstance(cat, str) or not _name_in(cat, _read(MD[(lang, "privacy")])):
                problems.append(f"row {row['id']}: {key} missing or not in the {lang} privacy policy")
    assert not problems, _report("R9:", problems)


VENDORS = (
    "Supabase", "Railway", "Upstash", "Sentry", "Expo", "Serper", "Bright Data", "BrightData", "Firecrawl", "Scrape.do",
    "Scrapedo", "Cloudflare", "Gmail", "Google Fonts", "YouTube", "Zyte", "Frankfurter", "PostHog", "Railway.app",
)


def _vendor_hits(text):
    return [v for v in VENDORS if re.search("(?i)(?<!\\w)[\u0628\u0644\u0648]?" + re.escape(v) + "(?!\\w)", text or "")]


def test_s78_r10_no_infrastructure_vendor_name_in_legal_surfaces():
    """R10 (LR3): no infrastructure vendor name (whole word, case-insensitive, AR proclitic allowed) in the six
    markdown files, the six regions or the four payloads; privacy s7 does not name Google. Control first. RED at
    base: 13 vendor names in privacy EN / AR."""
    assert _vendor_hits("via \u0648Sentry and google fonts") == ["Sentry", "Google Fonts"], "control"
    assert not _vendor_hits("Expose, Sentryish, Railways"), "control: whole words only"
    texts = [(rel, _read(rel) or "") for rel in MD.values()]
    texts += [(f"region {PAGES[k]}", t) for k, t in _regions().items()]
    texts += [(f"API {d} {l}", b["content"]) for (d, l), b in _payloads().items()]
    problems = [f"{label}: {', '.join(hits)}" for label, text in texts if (hits := _vendor_hits(text))]
    for lang in LANGS:
        if _name_in("Google", _section(_read(MD[(lang, "privacy")]), 7)):
            problems.append(f"{lang} privacy s7 names Google")
    assert not problems, _report("R10:", problems)


ON_REQUEST_EN = "We will tell you the names of our service providers on request at privacy@getmyez.com."
ON_REQUEST_EN_TEMPLATE = "We will tell you the names of our service providers on request at <PLACEHOLDER:PRIVACY_EMAIL>."
# S81-12 (R-S12-4, a deliberate pin change of R11): the carve-out names the data shared with OpenAI before the AI
# switch date (the fill-in data's AI_SWITCH_DATE / _AR), so R11 formats the committed date into it (EN here, AR in
# the fixture's s5_carveout_ar); the mailbox-provider clause it pins (LT10) is unchanged.
CARVEOUT_EN = (
    "Except as section 4 describes for data shared with OpenAI before {date} and as this section describes for our "
    "mailbox provider, each"
)


def test_s78_r11_providers_on_request_sentence():
    """R11 (LR3; LT10): filled privacy s5 carries the on-request sentence exactly once (EN verbatim, AR fixture); the
    snapshot carries the token form; the s5 carve-out sentence names the mailbox provider (LT10). RED at base:
    absent."""
    fx, ph = _fx(), _data()["placeholders"]
    problems = []
    carve_en = CARVEOUT_EN.format(date=ph.get("AI_SWITCH_DATE"))
    carve_ar = fx["s5_carveout_ar"].format(date=ph.get("AI_SWITCH_DATE_AR"))
    for lang, sentence, template, carve in (("en", ON_REQUEST_EN, ON_REQUEST_EN_TEMPLATE, carve_en),
                                            ("ar", fx["on_request_ar"], fx["on_request_ar_template"], carve_ar)):
        s5 = _section(_read(MD[(lang, "privacy")]), 5)
        if s5.count(sentence) != 1:
            problems.append(f"{lang} privacy s5: the on-request sentence occurs {s5.count(sentence)} times")
        snap = _section(_read(f"{PREFILL}/{Path(MD[(lang, 'privacy')]).name}"), 5)
        if snap.count(template) != 1:
            problems.append(f"{lang} snapshot s5: the token-form sentence occurs {snap.count(template)} times")
        if carve not in s5:
            problems.append(f"{lang} privacy s5: the carve-out does not name the mailbox provider (LT10)")
    assert not problems, _report("R11:", problems)


TRANSFER_EN = (
    "We transfer data to our service providers, which are required by contract to protect it, and to our mailbox "
    "provider, which handles email under its own terms (section 5)."
)
ROLE_WORDS_EN = re.compile(r"(?i)\b(?:database|hosting|temporary(?:-storage)?)\b")


def test_s78_r12_transfers_name_countries_without_vendor_mapping():
    """R12 (LR3, M4): privacy s7 names the United States, Germany (European Union) and the HOSTING_REGIONS value
    (AR twins), no vendor or role word (database / hosting / temporary), no parenthesis except (European Union) and
    (section 5), the TRANSFER_BASIS false sentence once, and no stronger basis. RED at base: s7 maps vendors."""
    fx, ph = _fx(), _data()["placeholders"]
    problems = []
    cases = (
        ("en", ["United States", "Germany (European Union)", ph.get("HOSTING_REGIONS") or "?"], TRANSFER_EN,
         {"European Union", "section 5"}, lambda s: ROLE_WORDS_EN.findall(s)),
        ("ar", list(fx["countries_ar"]) + [ph.get("HOSTING_REGIONS_AR") or "?"], fx["transfer_ar"],
         set(fx["s7_parentheticals_ar"]), lambda s: [w for w in fx["s7_role_words_ar"] if w in s]),
    )
    for lang, countries, transfer, parens, roles in cases:
        s7 = _section(_read(MD[(lang, "privacy")]), 7)
        problems += [f"{lang} s7: lacks {_esc(c)}" for c in countries if c not in s7]
        problems += [f"{lang} s7: vendor {v}" for v in _vendor_hits(s7) + [n for n in ("OpenAI", "Google", "Apple") if _name_in(n, s7)]]
        problems += [f"{lang} s7: role word {_esc(w)}" for w in roles(s7)]
        problems += [f"{lang} s7: parenthesis ({_esc(p)})" for p in re.findall(r"\(([^)]*)\)", s7) if p not in parens]
        if s7.count(transfer) != 1:
            problems.append(f"{lang} s7: the TRANSFER_BASIS sentence occurs {s7.count(transfer)} times")
        problems += [f"{lang} s7: basis claim {w!r}" for w in ("adequa", "Article 12", "Article 13", "consent and contract") if w.lower() in s7.lower()]
    assert not problems, _report("R12:", problems)


# ---------------------------------------------------------------------------
# R13-R17: Terms of Service v2
# ---------------------------------------------------------------------------

APPLE_EN = {
    "item1": ["between you and us only, not with Apple"],
    "item3": ["solely responsible for providing any maintenance and support", "no obligation to provide any maintenance or support"],
    "item4": ["will refund", "refund the purchase price", "no other warranty obligation"],
    "item5": ["product liability claims", "consumer protection"],
    "item6": ["intellectual property rights", "investigating, defending, settling and discharging"],
    "item7": ["represent and warrant", "embargo", "terrorist supporting", "prohibited or restricted parties"],
    "item9": ["third-party terms", "mobile carrier"],
    "item10": ["third-party beneficiar"],
    "precedence": ["Standard EULA", "If they conflict"],
}
LICENCE_GRANT = (
    re.compile(r"(?i)\bwe\s+(?:hereby\s+)?grant\s+you\b"),
    re.compile(r"(?i)\bis\s+licensed\s+to\s+you\b"),
    re.compile(r"(?i)\byou\s+(?:are|will\s+be)\s+granted\b"),
)


def test_s78_r13_tos_apple_section_carries_the_exhibit_b_items():
    """R13 (LR5.2; LT2, LT3, LT8, LT9): ToS s16 carries the markers of Exhibit B items 1, 3, 4, 5, 6, 7, 9, 10 and
    the precedence sentence (EN + AR fixture); no phone shape in s16; no licence-grant wording in the ToS. RED at
    base: s16 is one sentence."""
    fx = _fx()
    problems = []
    for lang, markers in (("en", APPLE_EN), ("ar", fx["apple_ar"])):
        s16 = _section(_read(MD[(lang, "terms")]), 16)
        problems += [f"{lang} s16 {item}: lacks {_esc(m)}" for item, ms in markers.items() for m in ms if m not in s16]
        if PLUS_973.search(s16) or BH_NUMBER.search(s16):
            problems.append(f"{lang} s16: a phone shape")
    tos = _read(MD[("en", "terms")]) or ""
    problems += [f"en terms: licence-grant wording {rx.pattern}" for rx in LICENCE_GRANT if rx.search(tos)]
    assert not problems, _report("R13:", problems)


CARVEOUTS_EN = ("fraud", "gross negligence", "wilful misconduct", "death or personal injury", "does not allow us to exclude or limit")
APPLICABLE_LAW_EN = "to the extent permitted by applicable law"


def _first_sentence(section):
    body = section.strip()
    return body.split(". ", 1)[0] if body else ""


def test_s78_r14_tos_liability_opens_with_the_carve_outs():
    """R14 (LR5.10; LT6): the first sentence of ToS s12 carries the carve-outs (AR: the Civil Code vocabulary of
    the fixture); 'to the extent permitted by applicable law' precedes the first s12 bullet; s11 opens with it; no
    currency amount in s11-s12. RED at base: no carve-out."""
    fx = _fx()
    problems = []
    en = _read(MD[("en", "terms")])
    s11, s12 = _section(en, 11), _section(en, 12)
    first = _first_sentence(s12)
    problems += [f"en s12 first sentence lacks {m!r}" for m in CARVEOUTS_EN if m not in first]
    bullet = s12.find("\n- ")
    if bullet < 0 or APPLICABLE_LAW_EN not in s12[:bullet]:
        problems.append("en s12: the applicable-law qualifier does not precede the first bullet")
    if not s11.strip().startswith("To the extent permitted by applicable law"):
        problems.append("en s11 does not open with the applicable-law qualifier")
    if re.search(r"\$|\bUSD\b|\bBHD\b|\bdollars\b", s11 + s12):
        problems.append("en s11-s12: a currency amount")
    ar = _read(MD[("ar", "terms")])
    ar_first = _section(ar, 12).strip().split(".", 1)[0]
    problems += [f"ar s12 first sentence lacks {_esc(m)}" for m in fx["carveouts_ar"] if m not in ar_first]
    if not _section(ar, 11).strip().startswith(fx["applicable_law_ar"]):
        problems.append("ar s11 does not open with the applicable-law qualifier")
    assert not problems, _report("R14:", problems)


def test_s78_r15_minors_guardian_sentence():
    """R15 (LR5.3): ToS s3 and privacy s12 carry 'under 18', 'age of majority', 'parent or guardian'; ToS s3 also
    'permission' (AR fixture markers). RED at base: no '18'."""
    fx = _fx()
    problems = []
    for lang, markers, permission in (("en", ("under 18", "age of majority", "parent or guardian"), "permission"),
                                      ("ar", fx["minors_ar"], fx["minors_permission_ar"])):
        t3 = _section(_read(MD[(lang, "terms")]), 3)
        p12 = _section(_read(MD[(lang, "privacy")]), 12)
        problems += [f"{lang} terms s3 lacks {_esc(m)}" for m in markers if m not in t3]
        problems += [f"{lang} privacy s12 lacks {_esc(m)}" for m in markers if m not in p12]
        if permission not in t3:
            problems.append(f"{lang} terms s3 lacks the permission word")
    assert not problems, _report("R15:", problems)


# S81-12 fix round 1 (RULINGS_FIX1_S81_12 F1-6, a deliberate pin change, E-row EF6b): the Terms s8 heading names 'our AI providers'.
TOS_HEADINGS_EN = (
    "1. Agreement and who we are", "2. The service", "3. Eligibility and your account", "4. Free use and limits",
    "5. Acceptable use", "6. AI-generated content and accuracy", "7. Retailers, brands and links",
    "8. Intellectual property, your content and our AI providers", "9. Smart Decision Referrals", "10. Notifications",
    "11. Disclaimer of warranties", "12. Limitation of liability", "13. Suspension, termination and deletion",
    "14. Changes to these Terms", "15. Governing law and disputes", "16. Apple",
    "17. Your responsibility for unlawful use", "18. General", "19. Contact",
)
TOS_MARKERS_EN = {
    3: ["13 years"],
    5: ["automated means", "several accounts", "interfere", "statement by MYEZ"],
    6: ["Check them with the retailer", "supplements", "skincare", "doctor or pharmacist", "not for emergencies"],
    7: ["not a party to any purchase", "do not control"],
    8: ["OpenAI", "section 4 of our Privacy Policy", "belong to their owners", "only to identify"],
    13: ["review the decision", "Delete account", "Section 9 of our Privacy Policy"],
    14: ["material", "when we publish it"],
    15: ["mandatory laws of the country where you live"],
    17: ["To the extent the law allows", "unlawful use", "section 5"],
    18: ["Entire agreement", "Severability", "No waiver", "Assignment", "successor"],
}
TOS_FORBIDDEN_EN = {
    6: ["specifications and ratings come from"],
    13: ["erases your account data"],
    14: ["before it takes effect"],
}


def test_s78_r16_tos_v2_sections_and_lr5_items():
    """R16 (LR5; M3 case as written, LT1, LT5, LT11): the EN ToS headings are exactly the 19 of spec 3.3 in order;
    the per-section markers (EN + AR fixture) are present and the retired wordings absent; s19 holds both role
    addresses and the postal value; no 'opt out' and no 'estimated'. RED at base: 17 sections, no markers."""
    fx, ph = _fx(), _data()["placeholders"]
    problems = []
    en = _read(MD[("en", "terms")]) or ""
    headings = tuple(re.findall(r"(?m)^## (.+?)\s*$", en))
    if headings != TOS_HEADINGS_EN:
        problems.append(f"en headings: {len(headings)} found, not the 19 of spec 3.3 in order")
    for lang, markers, forbidden, postal in (
        ("en", TOS_MARKERS_EN, TOS_FORBIDDEN_EN, ph.get("POSTAL_ADDRESS")),
        ("ar", {int(k): v for k, v in fx["tos_markers_ar"].items()}, {int(k): v for k, v in fx["tos_forbidden_ar"].items()},
         ph.get("POSTAL_ADDRESS_AR")),
    ):
        text = _read(MD[(lang, "terms")]) or ""
        for n, ms in sorted(markers.items()):
            problems += [f"{lang} s{n}: lacks {_esc(m)}" for m in ms if m not in _section(text, n)]
        for n, ms in sorted(forbidden.items()):
            problems += [f"{lang} s{n}: retired wording {_esc(m)}" for m in ms if m in _section(text, n)]
        s19 = _section(text, 19)
        problems += [f"{lang} s19: lacks {m}" for m in ROLE_EMAILS if m not in s19]
        if not postal or postal not in s19:
            problems.append(f"{lang} s19: no postal value")
        if re.search(r"(?i)\bopt[\s-]?out\b|\bestimated\b", text):
            problems.append(f"{lang} terms: 'opt out' or 'estimated'")
    assert not problems, _report("R16:", problems)


def _shape(text):
    """[(heading number, list items in the section, sorted tokens with _AR stripped)] by '##' / '###' heading."""
    parts = re.split(r"(?m)^(#{2,3}[ \t]+.*)$", text or "")
    shape = [("", sum(1 for line in parts[0].split("\n") if line.startswith("- ")),
              sorted(t.removesuffix("_AR") for t in TOKEN.findall(parts[0])))]
    for i in range(1, len(parts), 2):
        title = re.sub(r"^#{2,3}[ \t]+", "", parts[i])
        number = re.match(r"([0-9]+(?:\.[0-9]+)*)", title)
        body = parts[i + 1]
        items = sum(1 for line in body.split("\n") if line.startswith("- "))
        shape.append((number.group(1) if number else "?", items, sorted(t.removesuffix("_AR") for t in TOKEN.findall(body))))
    return shape


def test_s78_r17_en_ar_structural_parity():
    """R17 (LR8 parity): for privacy, terms and support, the EN and AR markdown (filled and snapshot) have the same
    heading numbers, the same list-item count per section and (snapshot) the same tokens per section, _AR stripped;
    the ToS has 19 '##' sections and the privacy policy 16. RED at base: the ToS has 17 sections."""
    problems = []
    for doc in DOCS:
        en_rel, ar_rel = MD[("en", doc)], MD[("ar", doc)]
        for label, root_rel in (("filled", lambda r: r), ("snapshot", lambda r: f"{PREFILL}/{Path(r).name}")):
            en, ar = _shape(_read(root_rel(en_rel))), _shape(_read(root_rel(ar_rel)))
            if [(n, i) for n, i, _ in en] != [(n, i) for n, i, _ in ar]:
                problems.append(f"{doc} {label}: heading numbers or list items differ between EN and AR")
            if label == "snapshot" and [t for _, _, t in en] != [t for _, _, t in ar]:
                problems.append(f"{doc} snapshot: tokens per section differ between EN and AR")
    for doc, count in (("terms", 19), ("privacy", 16)):
        for lang in LANGS:
            n = len(re.findall(r"(?m)^## ", _read(MD[(lang, doc)]) or ""))
            if n != count:
                problems.append(f"{lang} {doc}: {n} '##' sections, not {count}")
    assert not problems, _report("R17:", problems)


# ---------------------------------------------------------------------------
# R18-R20: date, machinery, the P.O. Box swap
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=None)
def _u8():
    return _load(U8_TESTS, "_s78_u8_module")


def test_s78_r18_twelve_anchors_equal_and_moved():
    """R18 (LR4): the twelve anchors (T6 parsers, by content) all equal consent_service.TERMS_VERSION, later than
    2026-10-11; the four snapshot date lines carry the same date; legal_routes imports TERMS_VERSION from
    consent_service and has no ISO date literal. RED at base: every anchor is 2026-10-11 and the routes carry
    literals."""
    from app.services import consent_service

    version = consent_service.TERMS_VERSION
    u8 = _u8()
    problems = [] if version > "2026-10-11" else [f"TERMS_VERSION {version} is not later than 2026-10-11"]
    anchors = u8._anchors()
    assert len(anchors) == 12
    problems += [f"{label}: {value or reason}" for label, (value, reason) in anchors.items() if value != version]
    for rel, parse in (("privacy_policy.md", u8._en_anchor), ("terms_of_service.md", u8._en_anchor),
                       ("privacy_policy_ar.md", u8._ar_anchor), ("terms_of_service_ar.md", u8._ar_anchor)):
        if parse(_read(f"{PREFILL}/{rel}") or "") != version:
            problems.append(f"snapshot {rel}: date line is not {version}")
    tree = ast.parse(_read(LEGAL_ROUTES) or "")
    imports = any(isinstance(n, ast.ImportFrom) and n.module == "app.services.consent_service"
                  and any(a.name == "TERMS_VERSION" for a in n.names) for n in ast.walk(tree))
    if not imports:
        problems.append("legal_routes does not import TERMS_VERSION from app.services.consent_service")
    literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", n.value)]
    if literals:
        problems.append(f"legal_routes carries {len(literals)} ISO date literal(s)")
    assert not problems, _report("R18:", problems)


def _fill_module():
    return _load(FILL_SCRIPT, "_s78_fill_in_legal")


def test_s78_r19_render_check_clean_and_fill_idempotent():
    """R19 PIN (green at base by design; the merge gate): render_legal_landing.stale_regions(REPO) is empty and
    fill_in_legal.plan(REPO, data, variants) reports no missing key and reproduces every source byte for byte."""
    renderer = _load(RENDERER, "_s78_renderer")
    assert renderer.stale_regions(REPO) == []
    missing, outputs = _fill_module().plan(REPO, _data(), _json(VARIANTS))
    assert missing == []
    assert len(outputs) == 6
    changed = [rel for rel, (new, old) in outputs.items() if new != old]
    assert not changed, _report("R19: a fill-in would change:", changed)


def _temp_repo(tmp_path):
    """A temp repo: the six pre-fill snapshots as the sources, the six pages and the renderer."""
    root = tmp_path / "repo"
    for rel in MD.values():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / PREFILL / Path(rel).name, root / rel)
    for rel in PAGES.values():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, root / rel)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / RENDERER, root / RENDERER)
    return root


def _run_fill(root, data, tmp_path, capsys):
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    rc = _fill_module().main(["--repo-root", str(root), "--data", str(data_path), "--variants", str(REPO / VARIANTS)])
    out = capsys.readouterr()
    return rc, out.out + out.err


PO_BOX_EN_VALUE = "P.O. Box 0000, Kingdom of Bahrain"
PO_BOX_AR_VALUE = "\u0635.\u0628 0000\u060c \u0645\u0645\u0644\u0643\u0629 \u0627\u0644\u0628\u062d\u0631\u064a\u0646"
# The postal-line mentions of the site address per page; R20 expects this drop only while the committed postal
# value is the interim line (S78 fix F1), and 0 once a P.O. Box is committed.
ADDRESS_DELTA = {"privacy": 2, "terms": 2, "support": 1}


def test_s78_r20_po_box_swap_needs_no_code_change(tmp_path, capsys):
    """R20 (LR1, M2, Q2): on a temp copy of the snapshot, pages and renderer, the committed data with only the two
    postal values replaced by synthetic P.O. Box values fills with rc 0; the values reach privacy s1 / s16, ToS
    s1 / s19 and support in each language; R1, R2, R3 and R7 hold on the result; while the COMMITTED postal value
    of a language is the interim line (it contains PRIVACY_EMAIL), the site-address count of each page of that
    language drops by exactly the postal-line count (privacy 2, terms 2, support 1; the two literal count pins are
    re-measured at swap time, M2), and once a P.O. Box is committed the expected drop is 0, so a real swap keeps
    R20 green without an edit (S78 fix F1). RED at base: the AR documents use POSTAL_ADDRESS, so
    POSTAL_ADDRESS_AR is refused as unused."""
    fx = _fx()
    data = _data()
    data["placeholders"]["POSTAL_ADDRESS"] = PO_BOX_EN_VALUE
    data["placeholders"]["POSTAL_ADDRESS_AR"] = PO_BOX_AR_VALUE
    root = _temp_repo(tmp_path)
    rc, out = _run_fill(root, data, tmp_path, capsys)
    assert rc == 0, "R20: the P.O. Box re-fill is refused: " + _esc(out[-400:])
    problems = []
    values = {"en": PO_BOX_EN_VALUE, "ar": PO_BOX_AR_VALUE}
    for lang in LANGS:
        for doc, sections in (("privacy", (1, 16)), ("terms", (1, 19)), ("support", (None,))):
            text = _read(MD[(lang, doc)], root) or ""
            for n in sections:
                scope = text if n is None else _section(text, n)
                if values[lang] not in scope:
                    problems.append(f"{lang} {doc} s{n}: the P.O. Box value is missing")
    texts = [(rel, _read(rel, root) or "") for rel in MD.values()]
    texts += [(rel, html.unescape(_read(rel, root) or "")) for rel in PAGES.values()]
    for label, text in texts:
        if _street_hits(text):
            problems.append(f"{label}: R1")
        if _town_hits(text, _town_digests(fx)):
            problems.append(f"{label}: R2")
        problems += [f"{label}: R3 {p}" for p in _contact_problems(text)]
    email = data["placeholders"].get("PRIVACY_EMAIL") or ""
    problems += [f"R7 {lang}: {p}" for lang in LANGS for p in _postal_problems(values[lang], lang, email, fx)]
    committed = _data()["placeholders"]
    interim = {lang: bool(email) and email in (committed.get(key) or "")
               for lang, key in (("en", "POSTAL_ADDRESS"), ("ar", "POSTAL_ADDRESS_AR"))}
    for (lang, doc), rel in PAGES.items():
        expected = ADDRESS_DELTA[doc] if interim[lang] else 0
        before = len(SITE_ADDRESS.findall(_read(rel) or ""))
        after = len(SITE_ADDRESS.findall(_read(rel, root) or ""))
        if before - after != expected:
            problems.append(f"{rel}: site-address count {before} -> {after}, expected a drop of {expected}")
    assert not problems, _report("R20:", problems)


# ---------------------------------------------------------------------------
# R21-R24: privacy internals, manifest, strength sentences, required elements
# ---------------------------------------------------------------------------


def test_s78_r21_privacy_has_no_security_internals():
    """R21 (LR6): privacy EN has no 'secret key', 'Administrative functions' or 'certificate pinning'; AR none of the
    fixture internals; s13 still says data is encrypted in transit and tokens are in secure storage. RED at base:
    the base s13 sentences."""
    fx = _fx()
    en = _read(MD[("en", "privacy")]) or ""
    ar = _read(MD[("ar", "privacy")]) or ""
    problems = [f"en: {w!r}" for w in ("secret key", "Administrative functions", "certificate pinning") if w.lower() in en.lower()]
    problems += [f"ar: {_esc(w)}" for w in fx["internals_ar"] if w in ar]
    problems += [f"en s13 lacks {w!r}" for w in ("encrypted in transit", "secure storage") if w not in _section(en, 13)]
    problems += [f"ar s13 lacks {_esc(w)}" for w in fx["security_ar"] if w not in _section(ar, 13)]
    assert not problems, _report("R21:", problems)


# S81-12 (R-S12-11, a deliberate pin change): the anthropic row is public (the policy names Anthropic).
PUBLIC_NAME_IDS = {"openai", "anthropic", "apple", "google_sign_in", "retailers"}


def test_s78_r22_manifest_categories():
    """R22 (LR3): every manifest row has non-empty category_en / category_ar and a bool public_name, true exactly
    for openai, apple, google_sign_in and retailers; ids, kinds, modules, hosts, gate flags and personal_data equal
    the frozen base values (T7b coverage unchanged). RED at base: no category keys."""
    base = _fx()["manifest_base"]
    rows = _json(MANIFEST)["rows"]
    problems = []
    if sorted(r.get("id") for r in rows) != sorted(base):
        problems.append("the row ids changed")
    for row in rows:
        rid = row.get("id")
        for key in ("category_en", "category_ar"):
            if not (isinstance(row.get(key), str) and row[key].strip()):
                problems.append(f"{rid}: {key} missing or empty")
        if not isinstance(row.get("public_name"), bool):
            problems.append(f"{rid}: public_name is not a bool")
        elif row["public_name"] != (rid in PUBLIC_NAME_IDS):
            problems.append(f"{rid}: public_name is {row['public_name']}")
        frozen = base.get(rid)
        if frozen and any(row.get(k) != v for k, v in frozen.items()):
            problems.append(f"{rid}: kind / module / hosts / gate_flag / personal_data changed")
    assert not problems, _report("R22:", problems)


MARKETING_EN = (
    "Apart from the reminders described above, we do not use your personal data for direct marketing, and we do not "
    "share it with others for their marketing."
)
CHANGES_EN = "If a change is material, we will also tell you about it in the App or on our website when we publish it."


def test_s78_r23_privacy_strength_sentences():
    """R23 (PDPL Art 17(1)(c)(4); LT4, LT5): privacy s11 carries the LT4 direct-marketing sentence and s15 the LT5
    material-change sentence (EN; AR fixture twins); s15 makes no 'before it takes effect' promise. RED at base:
    absent."""
    fx = _fx()
    problems = []
    for lang, marketing, changes, before in (("en", MARKETING_EN, CHANGES_EN, "before it takes effect"),
                                             ("ar", fx["marketing_ar"], fx["changes_ar"], fx["before_effect_ar"])):
        text = _read(MD[(lang, "privacy")])
        if marketing not in _section(text, 11):
            problems.append(f"{lang} s11: no direct-marketing sentence")
        if changes not in _section(text, 15):
            problems.append(f"{lang} s15: no material-change sentence")
        if before in _section(text, 15):
            problems.append(f"{lang} s15: a before-effect promise")
    assert not problems, _report("R23:", problems)


S10_LABELS_EN = ("Access and a copy", "Correction", "Deletion, objection and restriction", "Withdrawing consent")
S8_LABELS_EN = ("Usage counters", "Email you send to our addresses", "Backups and service logs")
CARVEOUT_CORE_EN = "processes data only to provide its service to us, and we require each of them to protect it at least as well as this policy does."


def test_s78_r24_privacy_keeps_the_required_elements():
    """R24 PIN (green at base by design; LR6 guard against over-trimming): privacy EN / AR keep the 16 base section
    titles, s3.6, the s5 equal-protection sentence, the s8 retention lines, the s9 in-app deletion path, the s10
    rights and the PDPA complaint, s12 13+, s13 encryption in transit and the s16 role addresses."""
    fx = _fx()
    problems = []
    for lang in LANGS:
        text = _read(MD[(lang, "privacy")]) or ""
        heads = re.findall(r"(?m)^## (.+?)\s*$", text)
        if heads != fx[f"privacy_headings_{lang}"]:
            problems.append(f"{lang}: the 16 section titles changed")
        if not re.search(r"(?m)^### 3\.6 ", text):
            problems.append(f"{lang}: no s3.6")
        problems += [f"{lang} s16 lacks {m}" for m in ROLE_EMAILS if m not in _section(text, 16)]
    en = _read(MD[("en", "privacy")])
    ar = _read(MD[("ar", "privacy")])
    if CARVEOUT_CORE_EN not in _section(en, 5):
        problems.append("en s5: the equal-protection sentence is gone")
    problems += [f"en s8 lacks {m!r}" for m in S8_LABELS_EN if f"**{m}:**" not in _section(en, 8)]
    problems += [f"ar s8 lacks {_esc(m)}" for m in fx["privacy_s8_labels_ar"] if f"**{m}:**" not in _section(ar, 8)]
    if "Delete account" not in _section(en, 9) or fx["privacy_s9_delete_ar"] not in _section(ar, 9):
        problems.append("s9: the in-app deletion path is gone")
    problems += [f"en s10 lacks {m!r}" for m in S10_LABELS_EN if f"**{m}:**" not in _section(en, 10)]
    problems += [f"ar s10 lacks {_esc(m)}" for m in fx["privacy_s10_labels_ar"] if f"**{m}:**" not in _section(ar, 10)]
    if "Personal Data Protection Authority" not in _section(en, 10):
        problems.append("en s10: no PDPA complaint")
    if "aged 13 and over" not in _section(en, 12) or fx["privacy_s12_age_ar"] not in _section(ar, 12):
        problems.append("s12: 13+ is gone")
    if "encrypted in transit" not in _section(en, 13) or fx["security_ar"][0] not in _section(ar, 13):
        problems.append("s13: encryption in transit is gone")
    assert not problems, _report("R24:", problems)


# ---------------------------------------------------------------------------
# R25-R26: the existing scans and the retired sentences
# ---------------------------------------------------------------------------

# S81-12 (R-S12-1, a deliberate pin change of R25): Terms s8 names both AI providers (the dual-provider
# sentence), then lists what we send them; the AR twin is the fixture's tos_s8_openai_ar.
TOS_S8_OPENAI_EN = (
    "MYEZ uses AI providers to process your requests: Anthropic, PBC and OpenAI, L.L.C. We are moving this "
    "processing to Anthropic; until the move is complete, some or all requests, including photos, are processed "
    "by OpenAI. Section 4 of our Privacy Policy lists what we send them, and the App asks your permission before "
    "your first comparison or scan."
)
TOS_S13_DELETION_EN = "Section 9 of our Privacy Policy describes what deleting your account removes and the records we keep."


def test_s78_r25_new_text_passes_the_existing_scans():
    """R25 (LR5.6; LT11): the new ToS s8 OpenAI sentence and s13 deletion sentence are present (EN + AR fixture);
    then the d3c personal-data claim scan (loaded by path) finds no claim in the six filled markdown files, the S77
    D4 not-sold rule holds over them, and the copy-policy AR lists find nothing in the AR documents. RED at base:
    the S78 sentences are absent."""
    fx = _fx()
    problems = []
    for lang, s8, s13 in (("en", TOS_S8_OPENAI_EN, TOS_S13_DELETION_EN), ("ar", fx["tos_s8_openai_ar"], fx["tos_s13_deletion_ar"])):
        tos = _read(MD[(lang, "terms")])
        if s8 not in _section(tos, 8):
            problems.append(f"{lang} terms s8: the OpenAI sentence is missing")
        if s13 not in _section(tos, 13):
            problems.append(f"{lang} terms s13: the deletion sentence is missing")
    assert not problems, _report("R25: the S78 sentences are not there:", problems)
    d3c = _load(D3C_TESTS, "_s78_d3c_module")
    s77 = _load(S77_TESTS, "_s78_s77_module")
    s77_fx = s77._fx()
    policy = _json(COPY_POLICY)
    banned = [(e["label"], re.compile(e["pattern"])) for e in policy.get("banned_ar", [])]
    scary = list(policy.get("scary_vocab_ar", []))
    assert banned and scary, "copy policy has no Arabic lists"
    for (lang, doc), rel in MD.items():
        text = _read(rel) or ""
        problems += [f"{rel}: claim {c[:80]}" for c in d3c._personal_data_claims(text)]
        problems += [f"{rel}: {p}" for p in s77._en_not_sold_problems(text)]
        problems += [f"{rel}: {p}" for p in s77._ar_not_sold_problems(text, s77_fx)]
        if lang == "ar":
            problems += [f"{rel}: banned_ar {label}" for label, rx in banned if rx.search(text)]
            problems += [f"{rel}: scary_vocab_ar {w}" for w in scary if w in text]
    assert not problems, _report("R25: the existing scans flag the new text:", problems)


RETIRED_EN = (
    "Google also receives the email you send to our addresses (see Cloudflare below).",
    "receives the email you send to our addresses and forwards it to our mailbox provider, Google (Gmail)",
    "and Google as our mailbox provider act under their own terms.",
    "United States (OpenAI and Google)",
    "and to Google as our mailbox provider, which handles email under its own terms (section 5).",
    "Apple's Licensed Application End User License Agreement also applies, and Apple is not responsible for the App or for support.",
    "Deleting your account erases your account data from our servers",
)


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def test_s78_r26_retired_sentences_are_gone():
    """R26 (LR3, LR5): no retired EN / AR sentence (the base Google mailbox sentence, the Cloudflare line, the RL2
    own-terms sentence, 'United States (OpenAI and Google)', the RF1 transfer sentence, the base ToS s16 sentence,
    the 'erases your account data' deletion sentence) in the six markdown files, the snapshot, the variants file,
    the six regions or the four payloads. RED at base: all present."""
    retired = list(RETIRED_EN) + list(_fx()["retired_ar"])
    assert len(retired) == 14
    texts = [(rel, _read(rel) or "") for rel in MD.values()]
    texts += [(f"snapshot {Path(rel).name}", _read(f"{PREFILL}/{Path(rel).name}") or "") for rel in MD.values()]
    texts += [(VARIANTS, "\n".join(_strings(_json(VARIANTS))))]
    texts += [(f"region {PAGES[k]}", t) for k, t in _regions().items()]
    texts += [(f"API {d} {l}", b["content"]) for (d, l), b in _payloads().items()]
    problems = [f"{label}: {r[:60]}" for label, text in texts for r in retired if r in text]
    assert not problems, _report("R26: retired wording still published:", problems)


# ---------------------------------------------------------------------------
# R27: the variants file names no vendor in any state (S78 fix F5)
# ---------------------------------------------------------------------------

YOUTUBE_AR = "\u064a\u0648\u062a\u064a\u0648\u0628"
R27_MUST_SCAN = (
    "clauses.YOUTUBE_CLAUSE.en.privacy.on", "clauses.YOUTUBE_CLAUSE.ar.privacy.on",
    "clauses.YOUTUBE_CLAUSE.en.privacy.off", "forks.d5_identity.en.B", "forks.d5_identity.ar.B",
)


def _variant_texts(variants):
    """(label, text) for every text of every fork and clause variant, in every state, EN and AR."""
    out = []
    for section in ("forks", "clauses"):
        for token, entry in sorted((variants.get(section) or {}).items()):
            for lang in LANGS:
                for key, value in sorted((entry.get(lang) or {}).items()):
                    if isinstance(value, str):
                        out.append((f"{section}.{token}.{lang}.{key}", value))
                    elif isinstance(value, dict):
                        out += [(f"{section}.{token}.{lang}.{key}.{state}", text)
                                for state, text in sorted(value.items()) if isinstance(text, str)]
    return out


def _variant_vendor_problems(variants):
    problems = []
    for label, text in _variant_texts(variants):
        hits = _vendor_hits(text) + (["YouTube (AR)"] if YOUTUBE_AR in text else [])
        if hits:
            problems.append(f"{label}: {', '.join(hits)}")
    return problems


def test_s78_r27_variants_never_name_a_vendor():
    """R27 (S78 fix F5; LR3, G8): every text of every fork and clause variant of the variants file, in every state
    (on and off, selected by the current answers or not), EN and AR, names no R10 infrastructure vendor (OpenAI,
    Apple and Google are not on the list: LR3 keeps them named) and never YouTube (G8; the AR spelling too). R10
    and R25 scan only the filled documents, so a variant the answers do not select (YOUTUBE_CLAUSE 'on', d5 'B')
    is guarded only here. Controls first: the unselected states are scanned, and planted names are caught."""
    variants = _json(VARIANTS)
    labels = {label for label, _ in _variant_texts(variants)}
    missing = [label for label in R27_MUST_SCAN if label not in labels]
    assert not missing, f"control: not scanned: {missing}"
    planted = json.loads(json.dumps(variants))
    planted["clauses"]["YOUTUBE_CLAUSE"]["en"]["privacy"]["on"] += " YouTube receives the search."
    planted["clauses"]["YOUTUBE_CLAUSE"]["ar"]["privacy"]["on"] += " " + YOUTUBE_AR
    planted["forks"]["d5_identity"]["en"]["B"] += " Hosted on Railway."
    caught = _variant_vendor_problems(planted)
    for label in ("clauses.YOUTUBE_CLAUSE.en.privacy.on", "clauses.YOUTUBE_CLAUSE.ar.privacy.on", "forks.d5_identity.en.B"):
        assert any(p.startswith(label + ":") for p in caught), f"control: a planted name in {label} is not caught"
    problems = _variant_vendor_problems(variants)
    assert not problems, _report("R27: a variant names a vendor:", problems)


# ---------------------------------------------------------------------------
# M1: {value} clause literals (spec-review ruling M1)
# ---------------------------------------------------------------------------


def test_s78_m1_value_clause_literals_absent_when_empty(tmp_path, capsys):
    """M1 (generic; may pass at base): for every {value} clause of the variants file, once its expanded text is
    removed from the filled documents of that language, the longest literal of its 'nonempty' text occurs nowhere
    in them (otherwise an empty value is refused as a changed value, rc 3); and a re-fill of the snapshot with
    HOSTING_REGIONS = HOSTING_REGIONS_AR = '' is accepted (rc 0, the polish F1 promise)."""
    data, variants = _data(), _json(VARIANTS)
    problems = []
    for token, clause in sorted(variants["clauses"].items()):
        for lang in LANGS:
            tables = clause.get(lang) or {}
            for doc_key, table in tables.items():
                if not isinstance(table, dict) or not any("{value}" in str(t) for t in table.values()):
                    continue
                spec = clause["answer"]
                path = spec.get(lang) if isinstance(spec, dict) else spec
                value = data
                for part in str(path).split("."):
                    value = value.get(part) if isinstance(value, dict) else None
                value = value if isinstance(value, str) else (clause.get("if_null") or "")
                nonempty = str(table.get("nonempty", ""))
                literal = max((p.strip() for p in nonempty.split("{value}")), key=len)
                docs = [d for d in DOCS if doc_key in (d, "*")]
                for doc in docs:
                    text = _read(MD[(lang, doc)]) or ""
                    if value.strip():
                        text = text.replace(nonempty.replace("{value}", value), "")
                    if literal and literal in text:
                        problems.append(f"{token} ({lang}, {doc}): the literal {_esc(literal)!s} occurs outside the clause")
    data["placeholders"]["HOSTING_REGIONS"] = ""
    data["placeholders"]["HOSTING_REGIONS_AR"] = ""
    rc, out = _run_fill(_temp_repo(tmp_path), data, tmp_path, capsys)
    if rc != 0:
        problems.append("an empty HOSTING_REGIONS re-fill is refused: " + out[-300:])
    assert not problems, _report("M1:", problems)
