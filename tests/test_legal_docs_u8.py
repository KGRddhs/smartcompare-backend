"""U8 -- privacy policy and terms of service redraft (App Store launch blocker): backend tests.

Authority (the later wins): ``U8_LEGAL_REDRAFT_SPEC.md`` section 4.10 (T1-T11) <
``U8_LEGAL_REDRAFT_REVIEW.md`` (C1-C28) < ``FABLE_RULINGS_U8.md`` (UL1-UL20; UL17
says what RED writes). T10 is the client suite ``__tests__/legal/legalScreenLang.u8.test.tsx``.
Written RED at main ``1156f03c`` (#325). This file reads the network, a real ``.env``,
Railway, Supabase and the OpenAI dashboard NEVER: flag states come from the fill-in data
file only. Failure messages print Arabic as ``\\u`` escapes (ASCII console).

NODE MAP (state at base 1156f03c)
---------------------------------
RED (fail at base, green after GREEN; T2 stays red until the fill-in commit, UL3):
  T1   test_t1_no_draft_text
  T2   test_t2_no_unresolved_placeholder            (base: the fill-in data file is absent)
  T3   test_t3_no_old_brand_in_legal_text
  T4   test_t4_en_ar_heading_parity_markdown         (base: the AR markdown does not exist)
  T5   test_t5_landing_regions_match_markdown_render
  T6   test_t6_version_anchors_move_together         (base: the two AR markdown anchors)
  T7   test_t7_processor_manifest_schema             (base: manifest absent, UL17 allows)
  T7a  test_t7a_policy_names_every_processor          (base: manifest absent, UL17 allows)
  T7b  test_t7b_external_hosts_and_clients_map_to_manifest
  T7c  test_t7c_client_side_recipients_have_rows      (base: manifest absent, UL17 allows)
  T8   test_t8_policy_ai_section_agrees_with_consent_copy_en
  T8   test_t8_policy_ai_section_agrees_with_consent_copy_ar
  T9   test_t9_lang_ar_serves_arabic_documents
  T11  test_t11_deletion_text_matches_043_state_en    (base: data file absent, UL17 allows)
  T11  test_t11_deletion_text_matches_043_state_ar    (base: data file absent, UL17 allows)
  UL12 test_ar_legal_text_follows_copy_policy
PIN (green at base and after): the positive controls of T1/T2/T3/T6/T7/T8, the T4 page
parity, the four T9 route pins (UL13), no tables in the legal markdown (C22), the
landing chrome (UL1/UL11).

DOCUMENTS
---------
Markdown: app/legal/{privacy_policy,terms_of_service}.md and their NEW ``_ar.md`` twins.
Pages: landing/{privacy,terms}.html, landing/ar/{privacy,terms}.html (rendered from the
markdown, UL1) and landing/support.html + landing/ar/support.html (their own region, UL11).
HTML is entity-decoded (``html.unescape``) before every content scan, so an escaped
``&lt;PLACEHOLDER:X&gt;`` counts exactly like the raw token.

FILL-IN DATA FILE (UL9) -- tests/fixtures/legal_fill_in_u8.json (GREEN writes it)
---------------------------------------------------------------------------------
One JSON object. Every key below is REQUIRED; a value of ``null`` means "not answered /
not recorded yet" and is reported by T2 (the fill-in commit leaves no null).
  "deletion_variant":    "043" | "old" | null     (UL9; T11 marker iff "043")
  "territories":         "bahrain" | "gcc" | null
  "counsel_review":      true | false | null
  "d3":                  "A" | "B" | null           (T8 treats null as the drafting default A)
  "d5":                  "A" | "B" | null
  "trade_name":          string (may be "") | null
  "minors_clause":       true | false | null
  "openai_store_pinned": true | false | null        (UL2)
  "inapp_notif_clause":  true | false | null        (UL2/C24: false until #264)
  "flags":       {exactly the seven names of review Q10 -> "on" | "off" | null}:
                 ENABLE_YOUTUBE_SOURCE, ENABLE_REENGAGEMENT_PUSHES, ENABLE_BONUS_EXPIRY_PUSHES,
                 ENABLE_FEWSHOT_ROTATION, ENABLE_FIRECRAWL, ENABLE_SCRAPEDO,
                 ENABLE_BRIGHTDATA_FALLBACK (recorded by the orchestrator from a names-only
                 read; never by an agent; null until recorded)
  "placeholders": {"<ID>": string | null}  one key per ``<PLACEHOLDER:ID>`` token used in
                 the four markdown files, the support region source or
                 scripts/legal_variants_u8.json; ID matches ``[A-Z][A-Z0-9_]*``.
Keys starting with "_" are comments and are ignored; any other extra key is an error.

PROCESSOR MANIFEST (UL14, C14) -- app/legal/processors.json (GREEN writes it)
------------------------------------------------------------------------------
``{"rows": [row, ...]}`` (keys starting with "_" are comments). Each row:
  "id":            non-empty string, unique
  "name_en":       non-empty string that must appear in privacy_policy.md (T7a)
  "name_ar":       non-empty string that must appear in privacy_policy_ar.md (T7a; may be Latin)
  "kind":          non-empty string; EXACTLY ONE row has "retailer" (P15: every retailer
                   host is one class; its modules are excluded from the host check of T7b)
  "personal_data": bool
  "module":        list of repo-relative FILE paths that exist (a single string is read as a
                   one-element list): backend modules (app/services/...py) and/or client files
                   (SmartCompareApp/...); empty only for a recipient with no code site
                   (Railway hosting, Cloudflare email routing)
  "hosts":         list of strings: the hosts this row covers (exact or parent domain,
                   e.g. "api.openai.com"); for client rows also the npm package or API
                   identifier a grep finds in the row's client files (T7c)
  "gate_flag":     null, or one of the seven Q10 flag names. Set it ONLY when the policy
                   names the recipient conditionally on that flag (today: the YouTube clause,
                   ENABLE_YOUTUBE_SOURCE); T7a then applies only when the data file records
                   that flag "on". A recipient the policy names unconditionally carries null.
T7a also needs a personal-data row (name_en) for each recipient spec 4.2 s5 names
unconditionally (``SPEC_RECIPIENTS_EN``: Supabase, Railway, Upstash, Sentry, OpenAI, Expo,
Apple, Google, Serper, Bright Data, Firecrawl, Scrape.do, Cloudflare). T7c needs, for each
``CLIENT_PROBES`` entry, a row whose ``hosts`` lists the probe's needle and whose
SmartCompareApp/ module files contain it.
T7b scan (a strict superset of spec 4.10's module-level ``*_URL`` constants): every
app/services/**/*.py string literal that is not a docstring and holds an http(s) URL with a
valid external host (first party ``qaren.app`` and loopback excluded), plus every
construction of ``AsyncOpenAI(`` / ``OpenAI(`` / ``create_client(`` / ``Redis(`` /
``StrictRedis(`` / ``<redis>.from_url(`` / ``sentry_sdk.init(``. A scanned module must be
in ``NOT_PERSONAL`` (below, reason >= 40 chars) or in the ``module`` list of a row; unless
that row is the retailer row, every host found in the module must be covered by the
``hosts`` of its rows. schema.org (named by UL14) occurs only in comments and docstrings,
which are not scanned.

RENDERER CONTRACT (UL1, UL11) -- scripts/render_legal_landing.py (GREEN writes it)
----------------------------------------------------------------------------------
Stdlib-only (every top-level import is in ``sys.stdlib_module_names``); importing it has
no side effect (writing pages only under ``if __name__ == "__main__"``). It exposes
  render_markdown(text: str) -> str         the markdown subset -> HTML; HTML-escapes ALL text
  render_regions(repo_root: pathlib.Path) -> dict[str, str]
      {posix page path relative to repo_root: the exact text between the end of
       "<!-- legal:begin -->" and the start of "<!-- legal:end -->"} for exactly the six pages
       above; pure (reads the sources, writes nothing).
T5 compares each committed region with its render after the checkout's line-ending
translation (both read as text; "\\r\\n" == "\\n"); every other byte must match.

ROUTES (UL13)
-------------
GET /api/v1/legal/{privacy,privacy_policy,terms,terms_of_service}?lang=...: the handler takes
``lang: str = "en"`` (no ``Query()``); strip, lower, primary subtag (split on "-"), cap 8,
"ar" -> the ``_ar.md`` file, anything else -> the English file; ``last_updated`` is
``consent_service.TERMS_VERSION`` for both languages; the legacy short paths answer exactly
like the long ones; ``get_terms_of_service()`` with no argument keeps working
(tests/test_consent_capture_w3_16.py::test_b12, line 535).

TEXT RULES THE TESTS PIN
------------------------
* T6 anchors: the FIRST "<Month> <D>, <YYYY>" in an English file and the FIRST
  "<D> <Gulf month> <YYYY>" (Western digits, ``GULF_MONTHS_AR``) in an Arabic file is that
  file's date anchor; the two route ``last_updated`` values and both ``TERMS_VERSION``
  literals complete the twelve. Keep the date line first; it stays 2026-03-26 until the
  fill-in commit (UL3), so it is never a placeholder.
* T1: "message templates" (the UF7 Sentry sentence) is the one allowed use of "template";
  an Arabic rendering of it must use the plural (which does not contain the token).
* T3: addresses (the landing.brand.s69 ADDRESS_RE) and identifiers (``@qaren_*``,
  ``qaren_*`` / ``qaren.*`` keys, ``qaren-rr``, ``QarenLogo``) are stripped first; then any
  "qaren" (any case) and the standalone old Arabic brand word fail.
* T8 / T11 Arabic: ``AI_SECTION_KEYWORDS_AR``, ``AI_SECTION_NOT_SENT_AR`` and
  ``DELETION_DNEW_MARKER_AR`` are filled by GREEN (native-reviewed) - the only edits GREEN
  makes to this file.

MUTATION MATRIX (GREEN runs it; each mutant must redden the node named)
-----------------------------------------------------------------------
DRAFT line back in a markdown file -> T1 (and T5); ``.draft-notice`` rule back in a page
<style> -> T1; one placeholder left after the fill-in -> T2; "Qaren" in a body paragraph ->
T3; one AR heading dropped -> T4 (and T5); one landing paragraph hand-edited -> T5;
``html.escape`` removed from the renderer -> T5; a non-stdlib import in the renderer -> T5;
one anchor date changed -> T6; "Bright Data" removed from the policy -> T7a; a module with
``FOO_API_URL = "https://api.example.net"`` added to app/services -> T7b; the EAS Update row
removed -> T7c; "opt out" added to section 4 -> T8 en; "similar" removed from section 4 -> T8
en; lang=ar ignored -> T9 (and T10); ``startswith("ar")`` normalisation -> the unknown-lang
pin ("arabic"); ``lang: str = Query("en")`` -> the no-argument pin; deletion_variant flipped
without the text -> T11; a copy-policy term in an AR document -> the UL12 node.
"""
import ast
import asyncio
import datetime
import html
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

MD_EN = {"privacy": "app/legal/privacy_policy.md", "terms": "app/legal/terms_of_service.md"}
MD_AR = {"privacy": "app/legal/privacy_policy_ar.md", "terms": "app/legal/terms_of_service_ar.md"}
PAGES_EN = {"privacy": "landing/privacy.html", "terms": "landing/terms.html"}
PAGES_AR = {"privacy": "landing/ar/privacy.html", "terms": "landing/ar/terms.html"}
SUPPORT_PAGES = ("landing/support.html", "landing/ar/support.html")
LEGAL_MD = (*MD_EN.values(), *MD_AR.values())
LEGAL_PAGES = (*PAGES_EN.values(), *PAGES_AR.values())
RENDERED_PAGES = (*LEGAL_PAGES, *SUPPORT_PAGES)
ALL_DOCS = (*LEGAL_MD, *RENDERED_PAGES)
AR_DOCS = (*MD_AR.values(), *PAGES_AR.values(), "landing/ar/support.html")

FILL_IN = "tests/fixtures/legal_fill_in_u8.json"
MANIFEST = "app/legal/processors.json"
RENDERER = "scripts/render_legal_landing.py"
VARIANTS = "scripts/legal_variants_u8.json"
LEGAL_ROUTES = "app/api/legal_routes.py"
CONSENT_TS = "SmartCompareApp/src/services/consent.ts"
EN_CATALOG = "SmartCompareApp/src/i18n/en.json"
AR_CATALOG = "SmartCompareApp/src/i18n/ar.json"
COPY_POLICY = "SmartCompareApp/src/i18n/.copy-policy.json"

REGION_BEGIN = "<!-- legal:begin -->"
REGION_END = "<!-- legal:end -->"


def _read(rel):
    """Text of a repo file (universal newlines), or None when it does not exist."""
    p = REPO / rel
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8")


def _visible(rel):
    """The text the content fences scan: entity-decoded for .html files."""
    text = _read(rel)
    if text is None:
        return None
    return html.unescape(text) if rel.endswith(".html") else text


def _esc(text):
    """ASCII rendering for failure messages (no Arabic on the console)."""
    return text.encode("unicode_escape").decode("ascii")


def _report(title, problems):
    return title + "\n  - " + "\n  - ".join(problems)


def _absent(rel):
    return f"{rel}: file absent (UL18 creates it)"


# ---------------------------------------------------------------------------
# Fill-in data file (UL9)
# ---------------------------------------------------------------------------

SEVEN_FLAGS = (
    "ENABLE_YOUTUBE_SOURCE",
    "ENABLE_REENGAGEMENT_PUSHES",
    "ENABLE_BONUS_EXPIRY_PUSHES",
    "ENABLE_FEWSHOT_ROTATION",
    "ENABLE_FIRECRAWL",
    "ENABLE_SCRAPEDO",
    "ENABLE_BRIGHTDATA_FALLBACK",
)
_ENUM_ANSWERS = {
    "deletion_variant": ("043", "old"),
    "territories": ("bahrain", "gcc"),
    "d3": ("A", "B"),
    "d5": ("A", "B"),
}
_BOOL_ANSWERS = ("counsel_review", "minors_clause", "openai_store_pinned", "inapp_notif_clause")
_STR_ANSWERS = ("trade_name",)
FILL_IN_ANSWER_KEYS = (*_ENUM_ANSWERS, *_BOOL_ANSWERS, *_STR_ANSWERS)
_PLACEHOLDER_ID = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _fill_in_schema_problems(data):
    problems = []
    if not isinstance(data, dict):
        return [f"{FILL_IN}: top level must be a JSON object"]
    expected = {*FILL_IN_ANSWER_KEYS, "flags", "placeholders"}
    for key in sorted(k for k in data if not k.startswith("_") and k not in expected):
        problems.append(f"{FILL_IN}: unknown key {key!r}")
    for key in sorted(expected - set(data)):
        problems.append(f"{FILL_IN}: missing key {key!r}")
    for key, allowed in _ENUM_ANSWERS.items():
        value = data.get(key)
        if value is not None and not (isinstance(value, str) and value in allowed):
            problems.append(f"{FILL_IN}: {key} must be one of {allowed} or null, got {value!r}")
    for key in _BOOL_ANSWERS:
        value = data.get(key)
        if value is not None and not isinstance(value, bool):
            problems.append(f"{FILL_IN}: {key} must be true/false or null, got {value!r}")
    for key in _STR_ANSWERS:
        value = data.get(key)
        if value is not None and not isinstance(value, str):
            problems.append(f"{FILL_IN}: {key} must be a string or null, got {value!r}")
    flags = data.get("flags")
    if "flags" in data:
        if not isinstance(flags, dict) or set(flags) != set(SEVEN_FLAGS):
            problems.append(f"{FILL_IN}: flags must name exactly {SEVEN_FLAGS}")
        else:
            for name, value in flags.items():
                if value not in ("on", "off", None):
                    problems.append(f"{FILL_IN}: flags.{name} must be on/off/null, got {value!r}")
    placeholders = data.get("placeholders")
    if "placeholders" in data:
        if not isinstance(placeholders, dict):
            problems.append(f"{FILL_IN}: placeholders must be an object")
        else:
            for pid, value in placeholders.items():
                if not _PLACEHOLDER_ID.match(str(pid)):
                    problems.append(f"{FILL_IN}: placeholder id {pid!r} is not [A-Z][A-Z0-9_]*")
                if value is not None and not isinstance(value, str):
                    problems.append(f"{FILL_IN}: placeholders.{pid} must be a string or null")
    return problems


def _load_fill_in():
    """(data or None, problems). data is None when the file is absent or not JSON."""
    raw = _read(FILL_IN)
    if raw is None:
        return None, [
            f"fill-in data file {FILL_IN} absent (UL9): the owner's answers and the "
            "orchestrator's flag read have not been recorded"
        ]
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return None, [f"{FILL_IN}: not valid JSON ({type(exc).__name__})"]
    return data, _fill_in_schema_problems(data)


def _require_fill_in():
    data, problems = _load_fill_in()
    if data is None or problems:
        pytest.fail(_report("the fill-in data file is required here (UL9):", problems))
    return data


# ---------------------------------------------------------------------------
# T1 -- no draft / template / counsel-before-publication text (UL1, UL12/C11)
# ---------------------------------------------------------------------------

DRAFT_TOKENS = (
    ("'draft'", re.compile(r"(?i)\bdraft")),
    ("'template'", re.compile(r"(?i)\btemplate")),
    ("'legal counsel before publication'", re.compile(r"(?i)legal\s+counsel\s+before\s+publication")),
    ("AR 'draft' (musawwada)", re.compile("\u0645\u0633\u0648\u062f\u0629")),
    ("AR 'template' (qalib)", re.compile("\u0642\u0627\u0644\u0628")),
    ("AR 'legal counsel' (mustashar qanuni)", re.compile("\u0645\u0633\u062a\u0634\u0627\u0631\\s+\u0642\u0627\u0646\u0648\u0646\u064a")),
)
# UF7's Sentry sentence ("scrubbed message templates") is binding text (UL10 / C9).
T1_ALLOWED_PHRASES = (re.compile(r"(?i)\bmessage\s+templates?\b"),)


def _draft_hits(text):
    for rx in T1_ALLOWED_PHRASES:
        text = rx.sub(" ", text)
    return [(label, len(rx.findall(text))) for label, rx in DRAFT_TOKENS if rx.search(text)]


def test_t1_draft_scanner_positive_control():
    """PIN: the T1 scanner flags each token and spares only the UF7 phrase."""
    assert dict(_draft_hits("DRAFT - This document is a template.")) == {"'draft'": 1, "'template'": 1}
    assert _draft_hits("reviewed by legal counsel before publication") == [
        ("'legal counsel before publication'", 1)
    ]
    assert _draft_hits("Sentry receives scrubbed message templates and nothing else.") == []
    assert _draft_hits("p.draft-notice { color: red }") == [("'draft'", 1)]
    assert _draft_hits("@qaren_onboarding_draft_v1") == []
    assert [label for label, _ in _draft_hits("\u0645\u0633\u0648\u062f\u0629 \u0642\u0627\u0644\u0628")] == [
        "AR 'draft' (musawwada)",
        "AR 'template' (qalib)",
    ]


def test_t1_no_draft_text():
    """RED: no DRAFT / template / counsel notice in the eight legal documents or the support pages."""
    problems = []
    for rel in ALL_DOCS:
        text = _visible(rel)
        if text is None:
            problems.append(_absent(rel))
            continue
        for label, count in _draft_hits(text):
            problems.append(f"{rel}: {count} x {label}")
    assert not problems, _report("T1: draft/template text remains (UL1, UL12):", problems)


# ---------------------------------------------------------------------------
# T2 -- no unresolved placeholder (the LAST red; only the fill-in commit greens it)
# ---------------------------------------------------------------------------

PLACEHOLDER_TOKEN = re.compile(r"<PLACEHOLDER:([A-Z][A-Z0-9_]*)>")


def _placeholder_ids(text):
    """(token ids in order, count of PLACEHOLDER mentions that are not a well-formed token)."""
    ids = PLACEHOLDER_TOKEN.findall(text)
    return ids, text.count("PLACEHOLDER") - len(ids)


def test_t2_placeholder_scanner_reads_escaped_html():
    """PIN: a token escaped by the renderer is still found (the scan entity-decodes pages)."""
    page = "<p>Provided by &lt;PLACEHOLDER:CONTROLLER_NAME&gt;, PLACEHOLDER:BROKEN</p>"
    assert _placeholder_ids(html.unescape(page)) == (["CONTROLLER_NAME"], 1)
    assert _placeholder_ids("no tokens here") == ([], 0)


def test_t2_no_unresolved_placeholder():
    """RED until the fill-in commit: no placeholder in any served document, every answer recorded."""
    data, problems = _load_fill_in()
    placeholders = (data or {}).get("placeholders") if isinstance(data, dict) else None
    known = placeholders if isinstance(placeholders, dict) else {}
    for rel in ALL_DOCS:
        text = _visible(rel)
        if text is None:
            problems.append(_absent(rel))
            continue
        ids, stray = _placeholder_ids(text)
        for pid in sorted(set(ids)):
            if pid not in known:
                state = "id unknown to the fill-in data"
            elif known[pid] is None:
                state = "owner has not answered (null)"
            else:
                state = "value recorded but the fill-in script has not been applied"
            problems.append(f"{rel}: <PLACEHOLDER:{pid}> x{ids.count(pid)} -- {state}")
        if stray:
            problems.append(f"{rel}: {stray} malformed PLACEHOLDER mention(s)")
    variants = _read(VARIANTS)
    if variants is not None and data is not None:
        for pid in sorted(set(PLACEHOLDER_TOKEN.findall(variants)) - set(known)):
            problems.append(f"{VARIANTS}: <PLACEHOLDER:{pid}> has no key in the fill-in data")
    if isinstance(data, dict):
        for key in FILL_IN_ANSWER_KEYS:
            if key in data and data[key] is None:
                problems.append(f"{FILL_IN}: answer {key!r} is null")
        flags = data.get("flags")
        if isinstance(flags, dict):
            for name in SEVEN_FLAGS:
                if flags.get(name) is None:
                    problems.append(f"{FILL_IN}: flags.{name} not recorded (null)")
    assert not problems, _report("T2: unresolved fill-in (UL3, UL9):", problems)


# ---------------------------------------------------------------------------
# T3 -- no old brand in user-visible legal text (spec C1/C22; UL12 regex)
# ---------------------------------------------------------------------------

# Same address pattern as SmartCompareApp/__tests__/landing.brand.s69.test.ts.
ADDRESS_RE = re.compile(
    r"qaren://[\w/.-]*|[\w.+-]*@qaren\.app|(?:https?://)?(?:[\w-]+\.)*qaren\.app(?:/[\w/.%-]*)?",
    re.I,
)
IDENTIFIER_RE = re.compile(r"@qaren_\w+|\bqaren[_.][A-Za-z0-9_.]*[A-Za-z0-9_]|\bqaren-rr\b|\bQarenLogo\b")
LATIN_OLD_BRAND = re.compile(r"(?i)qaren")
AR_LETTER = "[\u0600-\u06ff]"
# landing.brand.s69 wordRe: optional proclitic b/l/w, Arabic-letter boundaries on both sides
# (the word for "comparison" contains the brand's letters and must never match).
OLD_AR_WORD = re.compile("(?<!" + AR_LETTER + ")[\u0628\u0644\u0648]?\u0642\u0627\u0631\u0646(?!" + AR_LETTER + ")")


def _old_brand_hits(text):
    stripped = IDENTIFIER_RE.sub(" ", ADDRESS_RE.sub(" ", text))
    return len(LATIN_OLD_BRAND.findall(stripped)), len(OLD_AR_WORD.findall(stripped))


def test_t3_old_brand_patterns_positive_control():
    """PIN: brand hits counted, addresses / identifiers / 'comparison' spared."""
    assert _old_brand_hits("Qaren operates the QAREN app") == (2, 0)
    assert _old_brand_hits("privacy@qaren.app https://qaren.app/ar/ qaren://profile @qaren_user qaren-rr") == (0, 0)
    assert _old_brand_hits("qaren_token qaren.demographicsPromptState.v1 QarenLogo com.qaren.app") == (0, 0)
    brand = "\u0642\u0627\u0631\u0646"
    comparison = "\u0645\u0642\u0627\u0631\u0646\u0629"
    assert _old_brand_hits(f"{brand} \u0648{brand} ({brand})") == (0, 3)
    assert _old_brand_hits(f"{comparison} \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0627\u062a") == (0, 0)


def test_t3_no_old_brand_in_legal_text():
    """RED: no 'Qaren' and no standalone old Arabic brand word in the legal documents."""
    problems = []
    for rel in ALL_DOCS:
        text = _visible(rel)
        if text is None:
            problems.append(_absent(rel))
            continue
        latin, arabic = _old_brand_hits(text)
        if latin:
            problems.append(f"{rel}: {latin} x 'Qaren' outside an address or identifier")
        if arabic:
            problems.append(f"{rel}: {arabic} x the old Arabic brand word")
    assert not problems, _report("T3: old brand in legal text (spec C1/C22, UL12):", problems)


# ---------------------------------------------------------------------------
# T4 -- EN/AR heading parity (count, level and section numbering)
# ---------------------------------------------------------------------------

MD_HEADING = re.compile(r"(?m)^(#{2,3})[ \t]+(.+?)[ \t]*$")
HTML_HEADING = re.compile(r"(?is)<h([23])\b[^>]*>(.*?)</h\1>")
SECTION_NO = re.compile(r"^([0-9]+(?:\.[0-9]+)*)\.?(?=\s|$)")
TAG = re.compile(r"<[^>]+>")


def _section_no(title):
    m = SECTION_NO.match(title.strip())
    return m.group(1) if m else ""


def _md_headings(text):
    return [(len(hashes), _section_no(title)) for hashes, title in MD_HEADING.findall(text)]


def _html_headings(text):
    return [(int(level), _section_no(html.unescape(TAG.sub("", inner)))) for level, inner in HTML_HEADING.findall(text)]


def _shape(headings):
    return " ".join(f"h{level}:{no or '-'}" for level, no in headings)


def _parity_problems(pairs, extract):
    problems = []
    for en_rel, ar_rel in pairs:
        en_text, ar_text = _read(en_rel), _read(ar_rel)
        if en_text is None:
            problems.append(_absent(en_rel))
            continue
        en = extract(en_text)
        ar = extract(ar_text) if ar_text is not None else []
        if not en:
            problems.append(f"{en_rel}: no headings found")
        if en != ar:
            note = " (file absent)" if ar_text is None else ""
            problems.append(
                f"{en_rel} vs {ar_rel}{note}: EN {len(en)} [{_shape(en)}] / AR {len(ar)} [{_shape(ar)}]"
            )
    return problems


def test_t4_en_ar_heading_parity_markdown():
    """RED: the AR markdown has the same headings, levels and numbering as the EN markdown."""
    problems = _parity_problems([(MD_EN[d], MD_AR[d]) for d in ("privacy", "terms")], _md_headings)
    assert not problems, _report("T4: EN/AR markdown heading parity:", problems)


def test_t4_en_ar_heading_parity_landing_pages():
    """PIN: the EN and AR landing pages keep identical h2/h3 numbering (15/15 and 14/14 at base)."""
    problems = _parity_problems([(PAGES_EN[d], PAGES_AR[d]) for d in ("privacy", "terms")], _html_headings)
    assert not problems, _report("T4: EN/AR landing heading parity:", problems)


# ---------------------------------------------------------------------------
# T5 -- the six landing regions are byte-equal to an in-memory render (UL1, UL11)
# ---------------------------------------------------------------------------


def _region(text):
    """(region text or None, problem or None) for one page."""
    if text.count(REGION_BEGIN) != 1 or text.count(REGION_END) != 1:
        return None, f"expected one {REGION_BEGIN} and one {REGION_END}, found {text.count(REGION_BEGIN)}/{text.count(REGION_END)}"
    start, end = text.index(REGION_BEGIN) + len(REGION_BEGIN), text.index(REGION_END)
    if end < start:
        return None, "legal:end precedes legal:begin"
    return text[start:end], None


def _non_stdlib_imports(source):
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    bad = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            bad += [a.name for a in node.names if a.name.split(".")[0] not in stdlib]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] not in stdlib:
                bad.append(node.module)
    return bad


def _load_renderer(problems):
    source = _read(RENDERER)
    if source is None:
        problems.append(f"{RENDERER}: absent (UL1)")
        return None
    bad = _non_stdlib_imports(source)
    if bad:
        problems.append(f"{RENDERER}: non-stdlib imports {bad} (UL1: stdlib only)")
    name = "_u8_render_legal_landing"
    spec = importlib.util.spec_from_file_location(name, REPO / RENDERER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses / typing need the module registered while it executes
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 -- reported, not raised
        problems.append(f"{RENDERER}: import failed ({type(exc).__name__})")
        return None
    finally:
        sys.modules.pop(name, None)
    for name in ("render_markdown", "render_regions"):
        if not callable(getattr(module, name, None)):
            problems.append(f"{RENDERER}: no callable {name}()")
    return module


def test_t5_landing_regions_match_markdown_render():
    """RED: each page carries one legal region and it equals the renderer's output (UL1, UL11)."""
    problems = []
    committed = {}
    for rel in RENDERED_PAGES:
        text = _read(rel)
        if text is None:
            problems.append(_absent(rel))
            continue
        region, problem = _region(text)
        if problem:
            problems.append(f"{rel}: {problem}")
        else:
            committed[rel] = region
    module = _load_renderer(problems)
    if module is not None and callable(getattr(module, "render_markdown", None)):
        try:
            out = module.render_markdown("Tom & Jerry <script>x</script> <PLACEHOLDER:CONTROLLER_NAME>")
        except Exception as exc:  # noqa: BLE001
            out = None
            problems.append(f"{RENDERER}: render_markdown raised {type(exc).__name__}")
        if out is not None and not (
            "<script" not in out
            and "&lt;script&gt;" in out
            and "&amp;" in out
            and "&lt;PLACEHOLDER:CONTROLLER_NAME&gt;" in out
        ):
            problems.append(f"{RENDERER}: render_markdown does not HTML-escape text (UL1)")
    if module is not None and callable(getattr(module, "render_regions", None)):
        try:
            rendered = module.render_regions(REPO)
        except Exception as exc:  # noqa: BLE001
            rendered = None
            problems.append(f"{RENDERER}: render_regions raised {type(exc).__name__}")
        if rendered is not None:
            keys = set(rendered) if isinstance(rendered, dict) else set()
            if keys != set(RENDERED_PAGES):
                problems.append(f"{RENDERER}: render_regions keys {sorted(keys)} != {sorted(RENDERED_PAGES)}")
            for rel, region in committed.items():
                want = rendered.get(rel) if isinstance(rendered, dict) else None
                if not isinstance(want, str):
                    continue
                if region.replace("\r\n", "\n") != want.replace("\r\n", "\n"):
                    problems.append(f"{rel}: committed region differs from the render (hand edit or stale render)")
    assert not problems, _report("T5: landing regions vs markdown render (UL1, UL11):", problems)


# ---------------------------------------------------------------------------
# T6 -- the twelve version anchors and both TERMS_VERSION constants are one date
# ---------------------------------------------------------------------------

EN_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
# Pinned Gulf month-name table (C12 / UL12), January..December.
GULF_MONTHS_AR = (
    "\u064a\u0646\u0627\u064a\u0631",  # January
    "\u0641\u0628\u0631\u0627\u064a\u0631",  # February
    "\u0645\u0627\u0631\u0633",  # March
    "\u0623\u0628\u0631\u064a\u0644",  # April
    "\u0645\u0627\u064a\u0648",  # May
    "\u064a\u0648\u0646\u064a\u0648",  # June
    "\u064a\u0648\u0644\u064a\u0648",  # July
    "\u0623\u063a\u0633\u0637\u0633",  # August
    "\u0633\u0628\u062a\u0645\u0628\u0631",  # September
    "\u0623\u0643\u062a\u0648\u0628\u0631",  # October
    "\u0646\u0648\u0641\u0645\u0628\u0631",  # November
    "\u062f\u064a\u0633\u0645\u0628\u0631",  # December
)
EN_DATE = re.compile(r"\b(" + "|".join(EN_MONTHS) + r")\s+([0-9]{1,2}),\s*([0-9]{4})\b")
AR_DATE = re.compile(r"(?<![0-9])([0-9]{1,2})\s+(" + "|".join(GULF_MONTHS_AR) + r")\s+([0-9]{4})(?![0-9])")
ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
CLIENT_TERMS_VERSION = re.compile(r"export\s+const\s+TERMS_VERSION\s*=\s*['\"]([^'\"]+)['\"]")


def _iso(year, month, day):
    try:
        return datetime.date(int(year), month, int(day)).isoformat()
    except ValueError:
        return None


def _en_anchor(text):
    m = EN_DATE.search(text)
    return _iso(m.group(3), EN_MONTHS.index(m.group(1)) + 1, m.group(2)) if m else None


def _ar_anchor(text):
    m = AR_DATE.search(text)
    return _iso(m.group(3), GULF_MONTHS_AR.index(m.group(2)) + 1, m.group(1)) if m else None


def _doc_anchor(rel, parse):
    text = _visible(rel)
    if text is None:
        return None, "file absent"
    value = parse(text)
    return (value, None) if value else (None, "no date in the pinned format")


def _route_anchor(handler):
    try:
        from app.api import legal_routes

        value = asyncio.run(getattr(legal_routes, handler)())["last_updated"]
    except Exception as exc:  # noqa: BLE001 -- reported as a missing anchor
        return None, f"handler raised {type(exc).__name__}"
    return (value, None) if isinstance(value, str) and ISO_DATE.match(value) else (None, f"not ISO: {value!r}")


def _backend_terms_version():
    from app.services import consent_service

    value = consent_service.TERMS_VERSION
    return (value, None) if ISO_DATE.match(value) else (None, f"not ISO: {value!r}")


def _client_terms_version():
    src = _read(CONSENT_TS)
    m = CLIENT_TERMS_VERSION.search(src or "")
    if not m:
        return None, "TERMS_VERSION literal not found"
    return (m.group(1), None) if ISO_DATE.match(m.group(1)) else (None, f"not ISO: {m.group(1)!r}")


def _anchors():
    """{label: (iso date or None, reason)} for the twelve anchors of spec 4.6."""
    return {
        "app/api/legal_routes.py privacy last_updated": _route_anchor("get_privacy_policy"),
        "app/api/legal_routes.py terms last_updated": _route_anchor("get_terms_of_service"),
        MD_EN["terms"]: _doc_anchor(MD_EN["terms"], _en_anchor),
        MD_EN["privacy"]: _doc_anchor(MD_EN["privacy"], _en_anchor),
        PAGES_EN["terms"]: _doc_anchor(PAGES_EN["terms"], _en_anchor),
        PAGES_EN["privacy"]: _doc_anchor(PAGES_EN["privacy"], _en_anchor),
        "app/services/consent_service.py TERMS_VERSION": _backend_terms_version(),
        f"{CONSENT_TS} TERMS_VERSION": _client_terms_version(),
        PAGES_AR["privacy"]: _doc_anchor(PAGES_AR["privacy"], _ar_anchor),
        PAGES_AR["terms"]: _doc_anchor(PAGES_AR["terms"], _ar_anchor),
        MD_AR["privacy"]: _doc_anchor(MD_AR["privacy"], _ar_anchor),
        MD_AR["terms"]: _doc_anchor(MD_AR["terms"], _ar_anchor),
    }


def test_t6_anchor_parsers_read_the_existing_anchors():
    """PIN: the parsers read the ten anchors that exist at base, and the month table is pinned."""
    assert len(set(GULF_MONTHS_AR)) == 12
    march = GULF_MONTHS_AR[2]
    assert _ar_anchor(f"x: 26 {march} 2026") == "2026-03-26"
    assert _ar_anchor(f"x: 1 {GULF_MONTHS_AR[11]} 2027") == "2027-12-01"
    assert _ar_anchor("x: \u0662\u0666 " + march + " \u0662\u0660\u0662\u0666") is None  # Arabic-Indic digits
    assert _en_anchor("*Effective date: March 26, 2026*") == "2026-03-26"
    anchors = _anchors()
    assert len(anchors) == 12
    existing = {label: got for label, got in anchors.items() if label not in MD_AR.values()}
    unread = [f"{label}: {reason}" for label, (value, reason) in existing.items() if value is None]
    assert not unread, _report("T6 parsers cannot read an existing anchor:", unread)


def test_t6_version_anchors_move_together():
    """RED: all twelve anchors exist and carry ONE date, equal to both TERMS_VERSION constants."""
    anchors = _anchors()
    problems = [f"{label}: {reason}" for label, (value, reason) in anchors.items() if value is None]
    dates = sorted({value for value, _ in anchors.values() if value is not None})
    if len(dates) > 1:
        problems.append(
            "anchors disagree: " + "; ".join(f"{label}={value}" for label, (value, _) in anchors.items() if value)
        )
    assert not problems, _report("T6: version anchors (spec 4.6, UL3, UL12):", problems)


# ---------------------------------------------------------------------------
# T7 -- the processor manifest and the policy (UL14, C14)
# ---------------------------------------------------------------------------

FIRST_PARTY_HOST_SUFFIXES = ("qaren.app",)
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0"})
URL_HOST = re.compile(r"https?://([A-Za-z0-9.-]+)")
VALID_HOST = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$")
CLIENT_CONSTRUCTORS = frozenset({"AsyncOpenAI", "OpenAI", "create_client", "Redis", "StrictRedis"})

# Modules the scan finds that send no personal data (UL14; reason >= 40 characters).
NOT_PERSONAL = {
    "app/services/exchange_rate_service.py": (
        "Frankfurter (api.frankfurter.app) receives only ISO currency codes for the daily "
        "exchange-rate fetch; no query, identifier or user data is sent."
    ),
    "app/services/zyte_service.py": (
        "Zyte is used only by the off-clock luxury seed over a curated product list "
        "(ENABLE_ZYTE_RENDER is off on the live path, spec P17); no user query or identity reaches it."
    ),
}

# Client-side recipients a scan of app/services cannot see (UL14). Each needle must be
# found in its file today (positive control) and listed in the hosts of a client row.
CLIENT_PROBES = {
    "EAS Update": ("SmartCompareApp/app.json", "u.expo.dev"),
    "Sentry (app)": ("SmartCompareApp/src/services/sentry.ts", "@sentry/react-native"),
    "Sign in with Apple": ("SmartCompareApp/src/components/AppleSignInButton.tsx", "expo-apple-authentication"),
    "Google Sign-In": ("SmartCompareApp/src/services/authService.ts", "@react-native-google-signin/google-signin"),
    "Expo push token": ("SmartCompareApp/src/services/pushTokenService.ts", "getExpoPushTokenAsync"),
}

# The recipients spec 4.2 s5 names unconditionally (near-final text, UL10): each is the
# name_en of a personal-data row, so T7a keeps it in the policy.
SPEC_RECIPIENTS_EN = (
    "Supabase", "Railway", "Upstash", "Sentry", "OpenAI", "Expo", "Apple", "Google",
    "Serper", "Bright Data", "Firecrawl", "Scrape.do", "Cloudflare",
)

_ROW_KEYS = ("id", "name_en", "name_ar", "kind", "personal_data", "module", "hosts", "gate_flag")


def _docstring_ids(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    ids.add(id(body[0].value))
    return ids


def _external_host(raw):
    host = raw.lower().strip(".")
    if host in LOCAL_HOSTS or not VALID_HOST.match(host):
        return None
    if any(host == s or host.endswith("." + s) for s in FIRST_PARTY_HOST_SUFFIXES):
        return None
    return host


def _scan_source(source):
    """(external hosts in non-docstring literals, client construction call names)."""
    tree = ast.parse(source)
    skip = _docstring_ids(tree)
    hosts, calls = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            for raw in URL_HOST.findall(node.value):
                host = _external_host(raw)
                if host:
                    hosts.add(host)
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
            if name in CLIENT_CONSTRUCTORS:
                calls.append(name)
            elif name == "from_url" and isinstance(func, ast.Attribute) and "redis" in ast.unparse(func.value).lower():
                calls.append("redis.from_url")
            elif name == "init" and isinstance(func, ast.Attribute) and ast.unparse(func.value) == "sentry_sdk":
                calls.append("sentry_sdk.init")
    return hosts, calls


def _scan_services():
    found = {}
    for path in sorted((REPO / "app" / "services").rglob("*.py")):
        hosts, calls = _scan_source(path.read_text(encoding="utf-8"))
        if hosts or calls:
            found[path.relative_to(REPO).as_posix()] = (hosts, calls)
    return found


def _manifest_rows():
    """(rows or None, problem or None)."""
    raw = _read(MANIFEST)
    if raw is None:
        return None, f"processor manifest {MANIFEST} absent (UL9 d, UL14)"
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return None, f"{MANIFEST}: not valid JSON ({type(exc).__name__})"
    rows = data.get("rows") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None, f'{MANIFEST}: top level must be {{"rows": [...]}}'
    return rows, None


def _require_manifest():
    rows, problem = _manifest_rows()
    if rows is None:
        pytest.fail(problem)
    return rows


def _row_modules(row):
    module = row.get("module") if isinstance(row, dict) else None
    if isinstance(module, str):
        return [module]
    return [m for m in module if isinstance(m, str)] if isinstance(module, list) else []


def _row_hosts(row):
    hosts = row.get("hosts") if isinstance(row, dict) else None
    return [h for h in hosts if isinstance(h, str)] if isinstance(hosts, list) else []


def _covers(row_host, host):
    row_host = row_host.lower()
    return host == row_host or host.endswith("." + row_host)


def _name_in(name, text):
    """Whole-word match; an Arabic proclitic b/l/w may be attached (as in landing.brand.s69)."""
    return re.search("(?<!\\w)[\u0628\u0644\u0648]?" + re.escape(name) + "(?!\\w)", text) is not None


def _gate_open(row, data):
    flag = row.get("gate_flag")
    return flag is None or (data.get("flags") or {}).get(flag) == "on"


def test_t7_scanner_positive_controls():
    """PIN: the T7b scanner finds the known sites, skips docstrings and first-party hosts."""
    assert _scan_source('FOO_API_URL = "https://api.example.net/v1"\n') == ({"api.example.net"}, [])
    assert _scan_source('"""See https://docs.example.org for details."""\nX = 1\n') == (set(), [])
    assert _scan_source('APP_BASE_URL = "https://qaren.app"\nU = "https://...jpg"\n') == (set(), [])
    assert _scan_source("import sentry_sdk\nsentry_sdk.init(dsn=None)\n")[1] == ["sentry_sdk.init"]
    found = _scan_services()
    expected = {
        "app/services/openai_service.py": "AsyncOpenAI",
        "app/services/extraction_service.py": "AsyncOpenAI",
        "app/services/database_service.py": "create_client",
        "app/services/cache_service.py": "Redis",
        "app/services/sentry_service.py": "sentry_sdk.init",
        "app/services/push_service.py": "exp.host",
        "app/services/brightdata_service.py": "api.brightdata.com",
        "app/services/serper_service.py": "google.serper.dev",
        "app/services/youtube_service.py": "www.googleapis.com",
        "app/services/exchange_rate_service.py": "api.frankfurter.app",
    }
    misses = []
    for rel, needle in expected.items():
        hosts, calls = found.get(rel, (set(), []))
        if needle not in hosts and needle not in calls:
            misses.append(f"{rel}: {needle} not found")
    assert not misses, _report("T7 scanner misses a known site:", misses)
    assert "app/services/referral_service.py" not in found  # only the first-party qaren.app
    stale = [rel for rel in NOT_PERSONAL if rel not in found]
    short = [rel for rel, reason in NOT_PERSONAL.items() if len(reason) < 40]
    assert not stale and not short, f"NOT_PERSONAL stale={stale} short_reason={short}"


def test_t7_client_probes_find_their_needles():
    """PIN: every client-side recipient probe still finds its host/package in the client today."""
    misses = []
    for label, (rel, needle) in CLIENT_PROBES.items():
        text = _read(rel)
        if text is None or needle not in text:
            misses.append(f"{label}: {needle!r} not in {rel}")
    assert not misses, _report("client probes (UL14):", misses)


def test_t7_processor_manifest_schema():
    """RED: the manifest exists and every row has the UL14 shape."""
    rows = _require_manifest()
    problems = []
    if not rows:
        problems.append("rows is empty")
    ids = []
    for i, row in enumerate(rows):
        where = f"rows[{i}]"
        if not isinstance(row, dict):
            problems.append(f"{where}: not an object")
            continue
        where = f"rows[{i}] id={row.get('id')!r}"
        for key in _ROW_KEYS:
            if key not in row:
                problems.append(f"{where}: missing {key!r}")
        for key in ("id", "name_en", "name_ar", "kind"):
            if not (isinstance(row.get(key), str) and row.get(key).strip()):
                problems.append(f"{where}: {key} must be a non-empty string")
        if not isinstance(row.get("personal_data"), bool):
            problems.append(f"{where}: personal_data must be a bool")
        modules = _row_modules(row)
        raw_module = row.get("module")
        if not (isinstance(raw_module, str) or (isinstance(raw_module, list) and len(modules) == len(raw_module))):
            problems.append(f"{where}: module must be a path or a list of paths")
        for rel in modules:
            if not (REPO / rel).is_file():
                problems.append(f"{where}: module path {rel!r} is not a file in the repo")
        if not isinstance(row.get("hosts"), list) or any(not isinstance(h, str) for h in row.get("hosts") or []):
            problems.append(f"{where}: hosts must be a list of strings")
        if row.get("gate_flag") is not None and row.get("gate_flag") not in SEVEN_FLAGS:
            problems.append(f"{where}: gate_flag must be null or one of the seven Q10 flags")
        if row.get("personal_data") is True:
            for rel in modules:
                if rel in NOT_PERSONAL:
                    problems.append(f"{where}: {rel} is both NOT_PERSONAL and in a personal-data row")
        ids.append(row.get("id"))
    dupes = sorted({i for i in ids if ids.count(i) > 1 and i is not None})
    if dupes:
        problems.append(f"duplicate ids {dupes}")
    retailer_rows = [r for r in rows if isinstance(r, dict) and r.get("kind") == "retailer"]
    if len(retailer_rows) != 1:
        problems.append(f"exactly one row of kind 'retailer' required, found {len(retailer_rows)}")
    assert not problems, _report(f"T7: {MANIFEST} schema (UL14):", problems)


def test_t7a_policy_names_every_processor():
    """RED: every personal-data row (gate open in the data file) is named in both policies."""
    rows = _require_manifest()
    data = _require_fill_in()
    problems = []
    en, ar = _visible(MD_EN["privacy"]) or "", _visible(MD_AR["privacy"])
    if ar is None:
        problems.append(_absent(MD_AR["privacy"]))
        ar = ""
    personal = [r for r in rows if isinstance(r, dict) and r.get("personal_data") is True]
    for row in personal:
        if not _gate_open(row, data):
            continue
        name_en, name_ar = row.get("name_en") or "", row.get("name_ar") or ""
        if not name_en or not _name_in(name_en, en):
            problems.append(f"{MD_EN['privacy']}: does not name {name_en!r} (row {row.get('id')!r})")
        if not name_ar or not _name_in(name_ar, ar):
            problems.append(f"{MD_AR['privacy']}: does not name {_esc(name_ar)!r} (row {row.get('id')!r})")
    named = {r.get("name_en") for r in personal}
    for name in SPEC_RECIPIENTS_EN:
        if name not in named:
            problems.append(f"{MANIFEST}: no personal-data row named {name!r} (spec 4.2 s5)")
    assert not problems, _report("T7a: the policy names every processor (UL14):", problems)


def test_t7b_external_hosts_and_clients_map_to_manifest():
    """RED: every external host / client construction in app/services maps to a row or NOT_PERSONAL."""
    rows, manifest_problem = _manifest_rows()
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    problems = [manifest_problem] if manifest_problem else []
    for rel, (hosts, calls) in _scan_services().items():
        if rel in NOT_PERSONAL:
            continue
        mapped = [r for r in rows if rel in _row_modules(r)]
        found = sorted(hosts) + sorted(set(calls))
        if not mapped:
            problems.append(f"{rel}: unmapped ({', '.join(found)})")
            continue
        if any(r.get("kind") == "retailer" for r in mapped):
            continue
        row_hosts = [h for r in mapped for h in _row_hosts(r)]
        for host in sorted(hosts):
            if not any(_covers(h, host) for h in row_hosts):
                problems.append(f"{rel}: host {host} not covered by its rows {[r.get('id') for r in mapped]}")
    assert not problems, _report("T7b: app/services recipients vs the manifest (UL14):", problems)


def test_t7c_client_side_recipients_have_rows():
    """RED: each client-side recipient has a row whose client files contain its host/package."""
    rows = [r for r in _require_manifest() if isinstance(r, dict)]
    problems = []
    for label, (_, needle) in CLIENT_PROBES.items():
        owners = [
            r for r in rows
            if needle in _row_hosts(r)
            and any(m.startswith("SmartCompareApp/") and needle in (_read(m) or "") for m in _row_modules(r))
        ]
        if not owners:
            problems.append(f"{label}: no row lists {needle!r} with a SmartCompareApp/ file that contains it")
    assert not problems, _report("T7c: client-side recipients (UL14):", problems)


# ---------------------------------------------------------------------------
# T8 -- consent copy vs policy section 4 (C4, UL2, UL10, UL16)
# ---------------------------------------------------------------------------

# key: (pattern, also required in aiConsent.body). The consent copy is not edited by U8 (UL16).
AI_SECTION_KEYWORDS_EN = {
    "product names": (r"\bproduct names\b", True),
    "links": (r"\blinks?\b", True),
    "page text": (r"\btext of (?:those|these|the) (?:web )?pages\b", True),
    "photos": (r"\bphotos?\b", True),
    "preferences": (r"\bpreferences\b", True),
    "budget": (r"\bbudget\b", True),
    "country": (r"\bcountry\b", True),
    "language": (r"\blanguage\b", True),
    "area": (r"\barea\b", True),
    "OpenAI": (r"\bOpenAI\b", True),
    "similar": (r"\bsimilar\b", False),  # C4: cohort priors from people with similar answers
}
NOT_SENT_EN = {
    "negation": r"\b(?:not|never)\b|n't\b",
    "send": r"\b(?:send|sent|share|shared)\b",
    "name": r"\bname\b",
    "email": r"\bemail\b",
    "account": r"\baccount\b",
}
D3_FORBIDDEN_EN = {
    "A": (r"\bopt(?:s|ed|ing)?[\s-]+out\b", r"Help improve AI quality", r"Data Sharing Program"),
    "B": (r"\bopt(?:s|ed|ing)?[\s-]+out\b", r"Data Sharing Program"),
}
# GREEN fills these three (same keys as the EN maps; Arabic regex; native-reviewed, UL12).
AI_SECTION_KEYWORDS_AR = {
    "product names": ("\u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a", True),
    "links": ("\u0631\u0648\u0627\u0628\u0637", True),
    "page text": ("\u0646\u0635 (?:\u062a\u0644\u0643 )?(?:\u0627\u0644)?\u0635\u0641\u062d\u0627\u062a", True),
    "photos": ("(?<!" + AR_LETTER + ")[\u0648\u0628]?\u0627\u0644\u0635\u0648\u0631(?!" + AR_LETTER + ")", True),
    "preferences": ("\u0627\u0644\u062a\u0641\u0636\u064a\u0644\u0627\u062a", True),
    "budget": ("\u0627\u0644\u0645\u064a\u0632\u0627\u0646\u064a\u0629", True),
    "country": ("\u0628\u0644\u062f\u0643", True),
    "language": ("\u0644\u063a\u062a\u0643", True),
    "area": ("\u0645\u0646\u0637\u0642\u062a\u0643", True),
    "OpenAI": ("OpenAI", True),
    "similar": ("\u062a\u062a\u0634\u0627\u0628\u0647|\u0645\u0634\u0627\u0628\u0647", False),
}
AI_SECTION_NOT_SENT_AR = {
    "negation": "(?<!" + AR_LETTER + ")(?:\u0644\u0627|\u0644\u0646|\u0644\u0645)(?!" + AR_LETTER + ")",
    "send": "[\u0646\u064a\u062a]\u0631\u0633\u0644|\u0625\u0631\u0633\u0627\u0644",
    "name": "\u0627\u0633\u0645\u0643",
    "email": "\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a|\u0628\u0631\u064a\u062f\u0643 \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a",
    "account": "\u062d\u0633\u0627\u0628",
}
D3_FORBIDDEN_AR = {
    "A": (
        "\u0628\u0631\u0646\u0627\u0645\u062c \u0645\u0634\u0627\u0631\u0643\u0629 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a",  # Data Sharing Program
        "\u062a\u062d\u0633\u064a\u0646 \u062c\u0648\u062f\u0629 \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a",  # improve AI quality
        "\u0633\u0627\u0639\u062f \u0641\u064a \u062a\u062d\u0633\u064a\u0646 \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a",  # toggle title
    ),
    "B": (
        "\u0628\u0631\u0646\u0627\u0645\u062c \u0645\u0634\u0627\u0631\u0643\u0629 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a",
    ),
}
SENTENCE_SPLIT = re.compile("(?<=[.!?\u061f])\\s+|\\n+")  # U+061F = Arabic question mark


def _md_section(text, number):
    """Body of the level-2 section numbered `number`, up to the next level-2 heading."""
    lines, start = text.splitlines(), None
    for i, line in enumerate(lines):
        m = re.match(r"^##(?!#)[ \t]+(.+)$", line)
        if not m:
            continue
        if start is not None:
            return "\n".join(lines[start:i])
        if _section_no(m.group(1)) == number:
            start = i + 1
    return "\n".join(lines[start:]) if start is not None else None


def _not_sent_sentence(text, patterns):
    for sentence in SENTENCE_SPLIT.split(text):
        if all(re.search(p, sentence, re.I) for p in patterns.values()):
            return True
    return False


def _d3(data):
    value = data.get("d3") if isinstance(data, dict) else None
    return value if value in ("A", "B") else "A"


def _catalog_value(rel, key):
    return json.loads(_read(rel)).get(key)


def test_t8_consent_copy_carries_the_keyword_map():
    """PIN: the shipped EN consent copy (aiConsent.body) carries every consent-side keyword."""
    body = _catalog_value(EN_CATALOG, "aiConsent.body")
    assert isinstance(body, str) and body
    missing = [k for k, (p, in_consent) in AI_SECTION_KEYWORDS_EN.items() if in_consent and not re.search(p, body, re.I)]
    assert not missing, f"aiConsent.body lacks {missing}"
    assert _not_sent_sentence(body, NOT_SENT_EN), "aiConsent.body has no not-sent sentence"
    assert set(NOT_SENT_EN) == {"negation", "send", "name", "email", "account"}


def test_t8_policy_ai_section_agrees_with_consent_copy_en():
    """RED: policy section 4 names everything the consent sheet says is sent, and nothing else."""
    text = _read(MD_EN["privacy"])
    section = _md_section(text, "4") if text is not None else None
    problems = []
    if section is None:
        problems.append(f"{MD_EN['privacy']}: no '## 4.' section")
        section = ""
    for key, (pattern, _) in AI_SECTION_KEYWORDS_EN.items():
        if not re.search(pattern, section, re.I):
            problems.append(f"section 4 lacks {key!r}")
    if not _not_sent_sentence(section, NOT_SENT_EN):
        problems.append("section 4 has no sentence saying name, email and account are not sent")
    data, _ = _load_fill_in()
    variant = _d3(data)
    for pattern in D3_FORBIDDEN_EN[variant]:
        if re.search(pattern, section, re.I):
            problems.append(f"section 4 contains {pattern!r} (forbidden under D3 = {variant})")
    assert not problems, _report("T8 (en): policy section 4 vs the consent sheet (C4, UL2):", problems)


def _usable_ar_pattern(pattern, latin_ok=False):
    if not isinstance(pattern, str):
        return False
    try:
        if re.fullmatch(pattern, "") is not None:
            return False
    except re.error:
        return False
    return latin_ok or re.search(AR_LETTER, pattern) is not None


def _ar_map_problems():
    """The GREEN-filled Arabic maps mirror the EN maps (keys and consent flags) with usable regex."""
    problems = []
    if set(AI_SECTION_KEYWORDS_AR) != set(AI_SECTION_KEYWORDS_EN):
        problems.append(
            f"AI_SECTION_KEYWORDS_AR keys {sorted(AI_SECTION_KEYWORDS_AR)} != EN keys (GREEN fills it, UL12)"
        )
    if set(AI_SECTION_NOT_SENT_AR) != set(NOT_SENT_EN):
        problems.append(f"AI_SECTION_NOT_SENT_AR keys {sorted(AI_SECTION_NOT_SENT_AR)} != {sorted(NOT_SENT_EN)}")
    for key, entry in AI_SECTION_KEYWORDS_AR.items():
        en_flag = AI_SECTION_KEYWORDS_EN.get(key, (None, None))[1]
        if not (isinstance(entry, tuple) and len(entry) == 2 and entry[1] is en_flag):
            problems.append(f"AI_SECTION_KEYWORDS_AR[{key!r}] must be (pattern, {en_flag})")
        elif not _usable_ar_pattern(entry[0], latin_ok=key == "OpenAI"):
            problems.append(f"AI_SECTION_KEYWORDS_AR[{key!r}]: empty, invalid or not Arabic")
    for key, pattern in AI_SECTION_NOT_SENT_AR.items():
        if not _usable_ar_pattern(pattern):
            problems.append(f"AI_SECTION_NOT_SENT_AR[{key!r}]: empty, invalid or not Arabic")
    return problems


def test_t8_policy_ai_section_agrees_with_consent_copy_ar():
    """RED: the AR policy section 4 agrees with the AR consent copy (map filled by GREEN)."""
    problems = _ar_map_problems()
    text = _read(MD_AR["privacy"])
    section = _md_section(text, "4") if text is not None else None
    if text is None:
        problems.append(_absent(MD_AR["privacy"]))
    elif section is None:
        problems.append(f"{MD_AR['privacy']}: no '## 4.' section")
    consent = _catalog_value(AR_CATALOG, "aiConsent.body") or ""
    if not problems:
        for key, (pattern, in_consent) in AI_SECTION_KEYWORDS_AR.items():
            if in_consent and not re.search(pattern, consent):
                problems.append(f"AR consent copy does not match the AR pattern for {key!r}")
            if not re.search(pattern, section):
                problems.append(f"AR section 4 lacks {key!r}")
        if not _not_sent_sentence(section, AI_SECTION_NOT_SENT_AR):
            problems.append("AR section 4 has no not-sent sentence (name, email, account)")
        data, _ = _load_fill_in()
        for phrase in D3_FORBIDDEN_AR[_d3(data)]:
            if phrase in section:
                problems.append(f"AR section 4 contains forbidden phrase {_esc(phrase)}")
    assert not problems, _report("T8 (ar): AR policy section 4 vs the AR consent sheet:", problems)


# ---------------------------------------------------------------------------
# T9 -- the legal routes: date, language, legacy paths, no-argument call (UL13)
# ---------------------------------------------------------------------------

LEGAL_PATHS = {
    "/api/v1/legal/privacy_policy": "privacy",
    "/api/v1/legal/privacy": "privacy",
    "/api/v1/legal/terms_of_service": "terms",
    "/api/v1/legal/terms": "terms",
}
AR_LANG_VALUES = ("ar", "AR", " ar ", "ar-BH")
EN_LANG_VALUES = ("en", "EN", "en-US", "fr", "", "arabic", "zz-ZZ", "x" * 64)


def _client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def _terms_version():
    from app.services import consent_service

    return consent_service.TERMS_VERSION


def test_t9_lang_ar_serves_arabic_documents():
    """RED: ?lang=ar (any case, padded, with a region) serves the _ar.md file on every path."""
    client, version, problems = _client(), _terms_version(), []
    for path, doc in LEGAL_PATHS.items():
        en_text, ar_text = _read(MD_EN[doc]), _read(MD_AR[doc])
        for value in AR_LANG_VALUES:
            resp = client.get(path, params={"lang": value})
            where = f"GET {path}?lang={value!r}"
            if resp.status_code != 200:
                problems.append(f"{where}: status {resp.status_code}")
                continue
            body = resp.json()
            if body.get("content") == en_text:
                problems.append(f"{where}: served the English document")
            elif ar_text is None or body.get("content") != ar_text:
                problems.append(f"{where}: content is not {MD_AR[doc]}" + (" (file absent)" if ar_text is None else ""))
            if body.get("last_updated") != version:
                problems.append(f"{where}: last_updated {body.get('last_updated')!r} != TERMS_VERSION {version!r}")
    assert not problems, _report("T9: lang=ar (UL13):", problems)


def test_t9_default_lang_serves_english_and_terms_version():
    """PIN: no lang -> the English file, last_updated == TERMS_VERSION, on all four paths."""
    client, version, problems = _client(), _terms_version(), []
    for path, doc in LEGAL_PATHS.items():
        resp = client.get(path)
        body = resp.json() if resp.status_code == 200 else {}
        if resp.status_code != 200 or body.get("content") != _read(MD_EN[doc]):
            problems.append(f"GET {path}: status {resp.status_code} / not the English file")
        if body.get("last_updated") != version:
            problems.append(f"GET {path}: last_updated {body.get('last_updated')!r} != {version!r}")
    assert not problems, _report("T9 default:", problems)


def test_t9_unknown_or_english_lang_serves_english():
    """PIN: en, unknown and over-long lang values serve the English file with status 200."""
    client, version, problems = _client(), _terms_version(), []
    for path, doc in LEGAL_PATHS.items():
        for value in EN_LANG_VALUES:
            resp = client.get(path, params={"lang": value})
            body = resp.json() if resp.status_code == 200 else {}
            if resp.status_code != 200 or body.get("content") != _read(MD_EN[doc]):
                problems.append(f"GET {path}?lang={value[:12]!r}: status {resp.status_code} / not English")
            elif body.get("last_updated") != version:
                problems.append(f"GET {path}?lang={value[:12]!r}: last_updated != TERMS_VERSION")
    assert not problems, _report("T9 unknown lang -> en (UL13):", problems)


def test_t9_legacy_paths_match_new_paths():
    """PIN: /privacy == /privacy_policy and /terms == /terms_of_service, for every lang."""
    client, problems = _client(), []
    pairs = (("/api/v1/legal/privacy", "/api/v1/legal/privacy_policy"), ("/api/v1/legal/terms", "/api/v1/legal/terms_of_service"))
    for short, long_ in pairs:
        for params in (None, {"lang": "ar"}, {"lang": "en"}, {"lang": "fr"}):
            a, b = client.get(short, params=params), client.get(long_, params=params)
            if (a.status_code, a.json()) != (b.status_code, b.json()):
                problems.append(f"{short} != {long_} for params={params}")
    assert not problems, _report("T9 legacy paths:", problems)


def test_t9_handlers_callable_without_arguments():
    """PIN (UL13, B12 line 535): both handlers work with no argument and serve English; no Query()."""
    from app.api import legal_routes

    version = _terms_version()
    privacy = asyncio.run(legal_routes.get_privacy_policy())
    terms = asyncio.run(legal_routes.get_terms_of_service())
    assert privacy["content"] == _read(MD_EN["privacy"])
    assert terms["content"] == _read(MD_EN["terms"])
    assert privacy["last_updated"] == version == terms["last_updated"]
    tree = ast.parse(_read(LEGAL_ROUTES))
    queries = [
        n.lineno for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and ((isinstance(n.func, ast.Name) and n.func.id == "Query") or (isinstance(n.func, ast.Attribute) and n.func.attr == "Query"))
    ]
    assert not queries, f"{LEGAL_ROUTES}: Query() at lines {queries} (UL13: plain default)"


# ---------------------------------------------------------------------------
# T11 -- the D-NEW deletion text ships iff deletion_variant == "043" (UL9, C15)
# ---------------------------------------------------------------------------

# From the PR #290 "Policy statement U8 may use" paragraph (spec 4.2 s9, D-NEW).
DELETION_DNEW_MARKER_EN = "We keep only a de-identified record"
# GREEN fills the Arabic marker sentence of its D-NEW translation (native-reviewed).
DELETION_DNEW_MARKER_AR = "\u0644\u0627 \u0646\u062d\u062a\u0641\u0638 \u0625\u0644\u0627 \u0628\u0633\u062c\u0644 \u0645\u0646\u0632\u0648\u0639 \u0627\u0644\u0647\u0648\u064a\u0629"


def _norm(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def _t11_problems(rel, marker, data):
    text = _read(rel)
    if text is None:
        return [_absent(rel)]
    variant = data.get("deletion_variant")
    has = _norm(marker) in _norm(text)
    want = variant == "043"
    if has != want:
        state = "contains" if has else "lacks"
        return [f"{rel}: {state} the D-NEW marker while deletion_variant is {variant!r}"]
    return []


def test_t11_deletion_text_matches_043_state_en():
    """RED: privacy_policy.md carries the D-NEW marker sentence iff deletion_variant == '043'."""
    data = _require_fill_in()
    problems = _t11_problems(MD_EN["privacy"], DELETION_DNEW_MARKER_EN, data)
    assert not problems, _report("T11 (en): deletion text vs 043 (UL9, C15):", problems)


def test_t11_deletion_text_matches_043_state_ar():
    """RED: privacy_policy_ar.md carries the AR D-NEW marker iff deletion_variant == '043'."""
    data = _require_fill_in()
    problems = []
    if not (DELETION_DNEW_MARKER_AR.strip() and re.search(AR_LETTER, DELETION_DNEW_MARKER_AR)):
        problems.append("DELETION_DNEW_MARKER_AR is not filled (GREEN fills it, native-reviewed)")
    else:
        problems += _t11_problems(MD_AR["privacy"], DELETION_DNEW_MARKER_AR, data)
    assert not problems, _report("T11 (ar): deletion text vs 043 (UL9, C15):", problems)


# ---------------------------------------------------------------------------
# UL12 -- Arabic legal text follows SmartCompareApp/src/i18n/.copy-policy.json
# ---------------------------------------------------------------------------


def test_ar_legal_text_follows_copy_policy():
    """RED: no banned_ar pattern and no scary_vocab_ar term in the Arabic legal documents."""
    policy = json.loads(_read(COPY_POLICY))
    banned = [(e["label"], re.compile(e["pattern"])) for e in policy.get("banned_ar", [])]
    scary = list(policy.get("scary_vocab_ar", []))
    assert banned and scary, "copy policy has no Arabic lists"
    problems = []
    for rel in AR_DOCS:
        text = _visible(rel)
        if text is None:
            problems.append(_absent(rel))
            continue
        for label, rx in banned:
            if rx.search(text):
                problems.append(f"{rel}: banned_ar {_esc(label)}")
        for word in scary:
            if word in text:
                problems.append(f"{rel}: scary_vocab_ar {_esc(word)} x{text.count(word)}")
    assert not problems, _report("UL12: Arabic legal text vs the copy policy:", problems)


# ---------------------------------------------------------------------------
# PINs on the document shape (C22, UL1, UL11)
# ---------------------------------------------------------------------------

TABLE_ROW = re.compile(r"(?m)^[ \t]*\|.*\|[ \t]*$")


def test_legal_markdown_has_no_tables():
    """PIN (review C22): LegalScreen cannot render tables; no legal markdown file uses one."""
    offenders = [rel for rel in LEGAL_MD if _read(rel) is not None and TABLE_ROW.search(_read(rel))]
    assert not offenders, f"markdown tables in {offenders} (review C22: headings + bullet lists)"


def test_landing_legal_chrome_preserved():
    """PIN (UL1, UL11): the six rendered pages keep their language chrome."""
    problems = []
    for rel in RENDERED_PAGES:
        text = _read(rel)
        if text is None:
            problems.append(_absent(rel))
            continue
        is_ar = rel.startswith("landing/ar/")
        needles = ['<html lang="ar" dir="rtl">'] if is_ar else ['<html lang="en"']
        needles += ['hreflang="en"', 'hreflang="ar"', "<footer>", 'class="lang-switch"', "</html>"]
        for needle in needles:
            if needle not in text:
                problems.append(f"{rel}: lost {needle!r}")
    assert not problems, _report("landing chrome:", problems)


# ---------------------------------------------------------------------------
# FIX ROUND (adversaries A and B, 2026-10-08). Appended nodes; the nodes above
# are unchanged. A1-A4: the policy text against the code it describes (EN and
# AR). B1: scripts/fill_in_legal.py never exits 0 on a value or answer it did
# not apply. Every node holds before and after the fill-in commit.
# ---------------------------------------------------------------------------

BULLET = re.compile(r"(?m)^- \*\*(.+?):\*\*(.*)$")


def _fix_section(rel, number):
    """Body of '## <number>. ...' in a markdown file, up to the next level-2 heading ('' if absent)."""
    text = _read(rel) or ""
    match = re.search(r"(?ms)^## " + re.escape(str(number)) + r"\.[^\n]*\n(.*?)(?=^## |\Z)", text)
    return match.group(1) if match else ""


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=\.)\s+", text) if s.strip()]


SENTRY_TS = "SmartCompareApp/src/services/sentry.ts"
CLIENT_QUERY_RUNG = re.compile(r"\[\?&\]\(\?:([A-Za-z0-9_|]+)\)")
FIX_A1_EN = {
    "servers": "From our servers, Sentry receives exception types",
    "traces": "Performance traces from our servers",
    "app": "Reports from the App can include",
    "products": "product names",
}
# Arabic markers (native review, D11): the same four statements in privacy_policy_ar.md s13.
FIX_A1_AR = {
    "servers": "\u064a\u062a\u0644\u0642\u0649 Sentry \u0645\u0646 \u062e\u0648\u0627\u062f\u0645\u0646\u0627 \u0623\u0646\u0648\u0627\u0639 \u0627\u0644\u0627\u0633\u062a\u062b\u0646\u0627\u0621\u0627\u062a",
    "traces": "\u062a\u062a\u0628\u0639\u0627\u062a \u0627\u0644\u0623\u062f\u0627\u0621 \u0645\u0646 \u062e\u0648\u0627\u062f\u0645\u0646\u0627",
    "app": "\u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631 \u0627\u0644\u0648\u0627\u0631\u062f\u0629 \u0645\u0646 \u0627\u0644\u062a\u0637\u0628\u064a\u0642",
    "products": "\u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a",
}


def _client_scrubbed_query_params():
    match = CLIENT_QUERY_RUNG.search(_read(SENTRY_TS) or "")
    return set(match.group(1).split("|")) if match else set()


def test_fix_a1_client_query_rung_parser_positive_control():
    """PIN: the parser reads the client Sentry query rung (else A1's condition is unreadable)."""
    params = _client_scrubbed_query_params()
    assert {"q", "query"} <= params, f"{SENTRY_TS}: query-scrub rung not found ({sorted(params)})"


def test_fix_a1_sentry_sentence_scoped_to_servers_and_app_reports_disclosed():
    """FIX A1 (UF7): the UF7 sentence covers our servers only; the App's reports are disclosed.

    While the client query rung does not scrub product_a / product_b, the App sentence must say
    that request addresses can include the product names.
    """
    products_needed = not {"product_a", "product_b"} <= _client_scrubbed_query_params()
    problems = []
    for rel, markers in ((MD_EN["privacy"], FIX_A1_EN), (MD_AR["privacy"], FIX_A1_AR)):
        body = _fix_section(rel,13)
        if not body:
            problems.append(f"{rel}: no section 13")
            continue
        for key in ("servers", "traces"):
            if markers[key] not in body:
                problems.append(f"{rel} s13: missing {_esc(markers[key])!r}")
        app = [s for s in _sentences(body) if markers["app"] in s]
        if not app:
            problems.append(f"{rel} s13: no sentence on the App's error reports ({_esc(markers['app'])!r})")
        elif products_needed and not any(markers["products"] in s for s in app):
            problems.append(f"{rel} s13: the App sentence does not say its request addresses can include product names")
    assert not problems, _report("FIX A1: Sentry disclosure (UF7, sentry.ts):", problems)


PRODUCT_IMAGE_TSX = "SmartCompareApp/src/components/primitives/ProductImage.tsx"
DEVICE_IMAGE_LOAD = re.compile(r"source=\{\{\s*uri\s*:")
FIX_A2_EN = ("loaded directly from the retailer or image website", "IP address")
FIX_A2_AR = (
    "\u0635\u0648\u0631 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a \u0641\u064a \u0627\u0644\u062a\u0637\u0628\u064a\u0642",
    "\u0639\u0646\u0648\u0627\u0646 IP \u0627\u0644\u062e\u0627\u0635 \u0628\u062c\u0647\u0627\u0632\u0643",
)


def test_fix_a2_device_loaded_product_images_disclosed():
    """FIX A2: the App loads product pictures from third-party hosts; s6 and the manifest say so."""
    source = _read(PRODUCT_IMAGE_TSX)
    assert source is not None and DEVICE_IMAGE_LOAD.search(source), (
        f"{PRODUCT_IMAGE_TSX}: no remote <Image source={{{{ uri }}}}> found; if pictures are now proxied, "
        "update policy section 6 and this node"
    )
    problems = []
    for rel, (marker, ip) in ((MD_EN["privacy"], FIX_A2_EN), (MD_AR["privacy"], FIX_A2_AR)):
        if not any(marker in s and ip in s for s in _sentences(_fix_section(rel,6))):
            problems.append(f"{rel} s6: no sentence saying product pictures load from their website with the device IP")
    retailer = [r for r in _require_manifest() if isinstance(r, dict) and r.get("kind") == "retailer"]
    if not any(PRODUCT_IMAGE_TSX in _row_modules(r) for r in retailer):
        problems.append(f"{MANIFEST}: the retailer row does not list {PRODUCT_IMAGE_TSX}")
    assert not problems, _report("FIX A2: device-side product images:", problems)


FIX_A3_EN = ("IP address", "linked to your account", "not linked to an account")
FIX_A3_AR = (
    "\u0639\u0646\u0627\u0648\u064a\u0646 IP",
    "\u0627\u0644\u0645\u0631\u062a\u0628\u0637\u0629 \u0628\u062d\u0633\u0627\u0628\u0643",
    "\u063a\u064a\u0631 \u0627\u0644\u0645\u0631\u062a\u0628\u0637\u0629 \u0628\u0623\u064a \u062d\u0633\u0627\u0628",
)


def test_fix_a3_security_record_retention_is_scoped():
    """FIX A3 (UL8, form item 10): every s8 retention line on IP-bearing records says whether they
    are linked to the account; the cleanup period applies to the unlinked ones only."""
    problems = []
    for rel, (ip, linked, unlinked) in ((MD_EN["privacy"], FIX_A3_EN), (MD_AR["privacy"], FIX_A3_AR)):
        bullets = BULLET.findall(_fix_section(rel,8))
        ip_bullets = [(label, value) for label, value in bullets if ip in label]
        if not any(unlinked in label for label, _ in ip_bullets):
            problems.append(f"{rel} s8: no line for IP-bearing records not linked to an account")
        if not any(linked in label and unlinked not in label for label, _ in ip_bullets):
            problems.append(f"{rel} s8: no line for IP-bearing records linked to the account")
        for label, _ in ip_bullets:
            if linked not in label and unlinked not in label:
                problems.append(f"{rel} s8: {_esc(label)!r} does not say whether the records are linked to the account")
    en_linked = [v for label, v in BULLET.findall(_fix_section(MD_EN["privacy"], 8))
                 if FIX_A3_EN[0] in label and FIX_A3_EN[1] in label and FIX_A3_EN[2] not in label]
    if en_linked and not all("as long as your account exists" in v for v in en_linked):
        problems.append(f"{MD_EN['privacy']} s8: linked security records must be kept 'as long as your account exists'")
    assert not problems, _report("FIX A3: security-record retention scope:", problems)


FIX_A4_EN = ("your account", "section 9", "the record of reminders we sent you")
FIX_A4_AR = (
    "\u062d\u0633\u0627\u0628\u0643",
    "\u0627\u0644\u0642\u0633\u0645 9",
    "\u0627\u0644\u062a\u0630\u0643\u064a\u0631\u0627\u062a \u0627\u0644\u062a\u064a \u0623\u0631\u0633\u0644\u0646\u0627\u0647\u0627 \u0625\u0644\u064a\u0643",
)
MIGRATION_025 = "migrations/025_delete_user_cascade_completeness.sql"


def test_fix_a4_retention_lines_defer_to_the_deletion_section():
    """FIX A4: s8 lines kept 'with your account' point to section 9 (true under D-NEW and D-OLD), and
    D-OLD lists the reminder records 025 keeps."""
    problems = []
    for rel, (account, section9, _) in ((MD_EN["privacy"], FIX_A4_EN), (MD_AR["privacy"], FIX_A4_AR)):
        bullets = BULLET.findall(_fix_section(rel,8))
        if not bullets:
            problems.append(f"{rel}: section 8 has no retention lines")
        for label, value in bullets:
            if account in value and section9 not in value:
                problems.append(f"{rel} s8: {_esc(label)!r} is kept with the account but does not point to section 9")
    migration = _read(MIGRATION_025)
    assert migration is not None and "delete_user_cascade" in migration, f"{MIGRATION_025}: absent"
    if "re_engagement_events" not in migration:
        old = json.loads(_read(VARIANTS))["clauses"]["DELETION_SECTION"]
        for lang, marker in (("en", FIX_A4_EN[2]), ("ar", FIX_A4_AR[2])):
            if marker not in old[lang]["privacy"]["old"]:
                problems.append(f"{VARIANTS}: D-OLD ({lang}) does not list the reminder records 025 keeps")
    assert not problems, _report("FIX A4: retention vs deletion variants:", problems)


FILL_SCRIPT = "scripts/fill_in_legal.py"
FILL_SOURCES = (
    "app/legal/privacy_policy.md",
    "app/legal/terms_of_service.md",
    "app/legal/support_contact.md",
    "app/legal/privacy_policy_ar.md",
    "app/legal/terms_of_service_ar.md",
    "app/legal/support_contact_ar.md",
)
_SAMPLE_ANSWERS = {
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
REFILL_HINT = "restore the pre-fill markdown"


def _load_fill_script():
    name = "_u8_fill_in_legal_fix_round"
    spec = importlib.util.spec_from_file_location(name, REPO / FILL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def _filled_copy(tmp_path):
    """(module, root, data, variants): the six sources filled once in a temp copy of the repo.

    Recorded values of the data file are kept; every null the fill-in asks for gets a synthetic
    value (ASCII, '<key> sample value'), so the node holds before and after the fill-in commit.
    """
    fill = _load_fill_script()
    variants = json.loads(_read(VARIANTS))
    root = tmp_path / "repo"
    for rel in FILL_SOURCES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes((REPO / rel).read_bytes())
    data = json.loads(_read(FILL_IN))
    for _ in range(8):
        missing, outputs = fill.plan(root, data, variants)
        if not missing:
            break
        for key in missing:
            if key.startswith("flags."):
                data["flags"][key[len("flags."):]] = "off"
            elif key.startswith("placeholders."):
                pid = key[len("placeholders."):]
                data["placeholders"][pid] = pid.lower() + " sample value"
            else:
                data[key] = _SAMPLE_ANSWERS[key]
    else:
        pytest.fail(f"the fill-in still reports missing keys: {missing}")
    for rel, (new, _old) in outputs.items():
        (root / rel).write_bytes(new)
    return fill, root, data, variants


def _snapshot(root):
    return {rel: (root / rel).read_bytes() for rel in FILL_SOURCES}


def test_fix_b1_fill_in_rerun_with_the_same_data_changes_nothing(tmp_path):
    """PIN (B1): over filled documents the same data is accepted and changes no byte."""
    fill, root, data, variants = _filled_copy(tmp_path)
    assert not any("PLACEHOLDER" in (root / rel).read_text(encoding="utf-8") for rel in FILL_SOURCES)
    missing, outputs = fill.plan(root, data, variants)
    changed = sorted(rel for rel, (new, old) in outputs.items() if new != old)
    assert not missing and set(outputs) == set(FILL_SOURCES) and not changed, (missing, changed)


@pytest.mark.parametrize(
    "key",
    ("SUPPORT_EMAIL", "PRIVACY_EMAIL", "WITHDRAW_PATH", "WITHDRAW_PATH_AR", "GOVERNING_LAW_AR",
     "SECURITY_LOG_RETENTION_AR"),
)
def test_fix_b1_fill_in_refuses_a_value_changed_after_a_fill(tmp_path, capsys, key):
    """FIX B1: a value changed after a fill is reported (exit 3) and nothing is written."""
    fill, root, data, variants = _filled_copy(tmp_path)
    before = _snapshot(root)
    data["placeholders"][key] = data["placeholders"][key] + " revised"
    with pytest.raises(fill.FillInError) as info:
        fill.plan(root, data, variants)
    message = str(info.value)
    assert key in message and "not in the" in message and REFILL_HINT in message, message
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    rc = fill.main(["--repo-root", str(root), "--data", str(data_path), "--variants", str(REPO / VARIANTS)])
    assert rc == 3 and key in capsys.readouterr().err
    assert _snapshot(root) == before


def test_fix_b1_fill_in_names_the_remedy_when_a_fork_value_changed(tmp_path):
    """FIX B1: a value inside a fork variant changed after a fill is refused with the remedy."""
    fill, root, data, variants = _filled_copy(tmp_path)
    data["placeholders"]["CONTROLLER_NAME"] = data["placeholders"]["CONTROLLER_NAME"] + " revised"
    with pytest.raises(fill.FillInError) as info:
        fill.plan(root, data, variants)
    assert "found none" in str(info.value) and REFILL_HINT in str(info.value), str(info.value)


_FLIP = {
    "minors_clause": ("MINORS_CLAUSE", lambda v: not v),
    "inapp_notif_clause": ("INAPP_NOTIF_CLAUSE", lambda v: not v),
    "deletion_variant": ("DELETION_SECTION", lambda v: "old" if v == "043" else "043"),
    "flags.ENABLE_YOUTUBE_SOURCE": ("YOUTUBE_CLAUSE", lambda v: "off" if v == "on" else "on"),
}


@pytest.mark.parametrize("answer", sorted(_FLIP))
def test_fix_b1_fill_in_refuses_a_clause_answer_changed_after_a_fill(tmp_path, answer):
    """FIX B1: a derived-clause answer changed after a fill is refused, not silently ignored."""
    fill, root, data, variants = _filled_copy(tmp_path)
    token, flip = _FLIP[answer]
    holder, key = (data["flags"], answer[len("flags."):]) if answer.startswith("flags.") else (data, answer)
    holder[key] = flip(holder[key])
    with pytest.raises(fill.FillInError) as info:
        fill.plan(root, data, variants)
    assert token in str(info.value) and REFILL_HINT in str(info.value), str(info.value)
