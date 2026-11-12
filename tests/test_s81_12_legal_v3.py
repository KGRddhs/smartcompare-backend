"""S81-12 LEGAL-V3: RED rows for the legal update that names Anthropic (session 81).

Spec: sc-s81-s12/.qa-s80/S81-12_UNIT_SPEC.md section 5, as amended by its adversarial
review (S81-12_SPEC_REVIEW.md) and by RULINGS_S81_12.md R-S12-1..R-S12-18 including the
Amendments section (R-S12-10 as amended by RULINGS_S81_08 R-S08-3; R-S12-18 added by
RULINGS_S81_14 R-S14-4). Precedence: the rulings, then the review corrections, then the spec.

Every text change reaches the documents only through the U8 machinery (pre-fill snapshot ->
scripts/legal_variants_u8.json + tests/fixtures/legal_fill_in_u8.json -> restore ->
scripts/fill_in_legal.py -> scripts/render_legal_landing.py --check). These rows read the
filled sources, the landing regions, the variants, the fill-in data, the manifest and the
client sources as text; the dormant-text rows run the fill-in on TEMP COPIES with synthetic
values built at run time. Hermetic: no network, no .env, no app import except
tests that do not need one (none here imports app.main).

Row map (RED = fails at base 98d85433 on an AssertionError only; PIN = green at base):

  R1   privacy s4: both AI processors, the Anthropic no-training and retention facts
       ("up to" periods, R-S12-13), the conditional web-search sentence, the photo
       guidance once (EN / AR)                                         RED
  R1b  the R-S12-1 dual-provider sentence verbatim in privacy s2 and Terms s8 (EN);
       both names in privacy s2 / s5 and Terms s8 (AR)                  RED
  R2   (V3C EK7) the present-tense programme sentence once in privacy s2, s4 (scoped)
       and Terms s8; no ended story in any source or region (PATH C)   RED
  R3   (V3C EK8) the not-sold promise in main's carve-out form only   RED
  R4   privacy s5: one Anthropic and one OpenAI bullet, main's undated carve-out
       (V3C EK9), the email-delivery fragment (D9)                      RED
  R6   privacy s6: the catalogue crawler named by its published user-agent page
       (R-S12-2), operator entry, licensed data, Sponsored               RED
  R7   privacy s12: the AI-disclosure sentence after the minors text      RED
  R8   Terms s7 Sponsored + catalogue; Terms s8 no "Our AI provider is OpenAI" RED
  R9   processors.json: the anthropic row public and named (R-S12-11);
       PUBLIC_NAME_IDS in both test files; the openai row unchanged     RED
  R10  fill-in data and variants shape (V3C EK10: d3 'C', main's forks back, dormant forks and
       clauses, the new placeholder keys)                               RED
  R11  the device-rule texts are dormant until DEVICE_QUOTA_RESET is recorded (temp copy) RED
  R12  the compare-run and auth-throttle bullets are dormant until recorded; the
       compare-run bullet stays linked to the account (R-S12-9) (temp copy) RED
  R13  AI_SWITCH_DATE (EN, AR) == the effective date == TERMS_VERSION; it dates the notice
       only (V3C EK11)                                                  RED
  R14  consent v3 sources: AI_CONSENT_VERSION 3, setup mirror 3, the copy names both
       providers and carries main's training sentence after the transition sentence
       (V3C EK12), the fence pins version 3 and the recomputed digest   RED
  R15  onboarding Step 5 copy names the AI providers; Step05Trust defaults == en.json RED
  R16  OpenAI census (R-S12-7; V3C EK13): OpenAI only in privacy s2/s3.6 bullet/s4/s5 and Terms s8/s13, only
       inside the allowed sentence classes; regions carry the source counts RED
  R17  privacy s14 (R-S12-10 as amended by R-S08-3)                      RED
  R18  kb_feedback pseudonymous device key disclosure dormant (R-S12-18) (temp copy) RED
  R19  COMPARE_RUN_RETENTION / AUTH_THROTTLE_RETENTION join RETENTION_KEYS (R-S12-9) RED
  H1   HOLD (red by design until the window commit): tests/fixtures/legal_v3_window.json
       records the window date == TERMS_VERSION == AI_SWITCH_DATE (R-S12-6; V3C EK14) RED
  H1b  the H1 comparison proven on a temp copy (equal -> clean; each side mutated -> red;
       a missing file is a problem, never an exception)                 PIN
  P1   fill-in dry run idempotent, landing regions current               PIN
  P3   EN and AR key sets equal and unchanged against the recorded base set (R-S12-8) PIN
  P4   no QarenBot / old crawler token anywhere in the legal texts (R-S12-2) PIN
  P5   privacy s7 and TRANSFER_BASIS unchanged: no stronger basis (R-S12-3, LR3) PIN
  P6   DELETION_SECTION 043 and privacy s3.5 not edited here (R-S12-9)   PIN
  P7   the OpenAI 30-day sentence and its only evidence, the U3c store=False pin (R-S12-17) PIN

Pure ASCII: every Arabic string below is a unicode escape. The Arabic literals are BASE
texts (measured at 98d85433) used for absence checks, or synthetic test-only values; none is a
draft of the new copy (the AR drafts are GREEN's, [NATIVE READ]).
"""
from __future__ import annotations

import ast
import copy
import datetime
import hashlib
import html
import importlib.util
import json
import re
import shutil
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
LEGAL_MD = (PRIVACY_EN, TERMS_EN, PRIVACY_AR, TERMS_AR)
PAGES = (
    "landing/privacy.html", "landing/terms.html", "landing/support.html",
    "landing/ar/privacy.html", "landing/ar/terms.html", "landing/ar/support.html",
)
PAGE_OF = {
    PRIVACY_EN: "landing/privacy.html", TERMS_EN: "landing/terms.html",
    PRIVACY_AR: "landing/ar/privacy.html", TERMS_AR: "landing/ar/terms.html",
}
PREFILL = "tests/fixtures/legal_prefill_u8"
FILL_SCRIPT = "scripts/fill_in_legal.py"
RENDERER = "scripts/render_legal_landing.py"
VARIANTS = "scripts/legal_variants_u8.json"
FILL_IN = "tests/fixtures/legal_fill_in_u8.json"
WINDOW = "tests/fixtures/legal_v3_window.json"
MANIFEST = "app/legal/processors.json"
CONSENT_SERVICE = "app/services/consent_service.py"
EN_CATALOG = "SmartCompareApp/src/i18n/en.json"
AR_CATALOG = "SmartCompareApp/src/i18n/ar.json"
AI_CONSENT_TS = "SmartCompareApp/src/services/aiConsent.ts"
JEST_SETUP = "SmartCompareApp/__tests__/setup.ts"
FENCE_TEST = "SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts"
STEP05 = "SmartCompareApp/src/screens/onboarding/Step05Trust.tsx"
U8_TESTS = "tests/test_legal_docs_u8.py"
S78_TESTS = "tests/test_legal_s78.py"
U3C_PIN = "tests/test_u3c_store_false_pin.py"
STORE_PIN_SOURCE = "app/services/api_budget_service.py"

REGION_BEGIN = "<!-- legal:begin -->"
REGION_END = "<!-- legal:end -->"
AR_LETTER = "[\u0600-\u06ff]"

# --- R-S12-1: the dual-provider sentence (verbatim EN, ruling text) ----------------------
DUAL_EN = (
    "MYEZ uses AI providers to process your requests: Anthropic, PBC and OpenAI, L.L.C. "
    "We are moving this processing to Anthropic; until the move is complete, some or all "
    "requests, including photos, are processed by OpenAI."
)
# --- R-S12-2: the crawler sentence (verbatim EN core, ruling text) -----------------------
CRAWLER_EN = (
    "our catalogue crawler, identified by the user-agent string published at "
    "https://getmyez.com/bot/, reads merchant pages whose robots.txt permits it"
)
BOT_URL = "https://getmyez.com/bot/"
BOT_URL_AR = BOT_URL.rstrip("/")  # EK6 (RULINGS_ARFIX_S81_12 AF-5 (b)): the Arabic names the canonical address
# --- R-S12-10 (amended): privacy s14 -------------------------------------------------------
S14_EN_REQUIRED = {
    "AI permission record removed with the account": r"(?i)\bdeleting your account (?:also )?removes the AI permission record\b",
    "random install identifier": r"(?i)\brandom install identifier\b",
    "stored securely on the device": r"(?i)\bstored securely\b",
    "a second random identifier (F1-2)": r"(?i)\bsecond random identifier\b",
    "the older form of the install identifier (F1-2)": r"(?i)\bolder form of the install identifier\b",
}
S14_EN_FORBIDDEN = {
    "device-level copy (R-S08-3: no device consent mirror)": r"(?i)\bdevice-level copy\b",
    "two random device identifiers (base text)": r"(?i)\btwo random device identifiers\b",
    "device properties (a fingerprinting description, F1-2)": r"(?i)\bdevice properties\b",
}

# --- base literals (measured at 98d85433; used only for absence / presence checks) --------
PHOTO_EN = (
    "Please photograph products only, and do not include people, documents, payment cards or "
    "other personal or health details in your photos or searches."
)
PHOTO_AR = (
    "\u0648\u0646\u0631\u062c\u0648 \u0623\u0646 \u062a\u0635\u0648\u0651\u0631 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a "
    "\u0641\u0642\u0637\u060c \u0648\u0623\u0644\u0627 \u062a\u064f\u062f\u0631\u062c \u0641\u064a \u0635\u0648\u0631\u0643 "
    "\u0623\u0648 \u0639\u0645\u0644\u064a\u0627\u062a \u0628\u062d\u062b\u0643 \u0623\u0634\u062e\u0627\u0635\u064b\u0627 "
    "\u0623\u0648 \u0645\u0633\u062a\u0646\u062f\u0627\u062a \u0623\u0648 \u0628\u0637\u0627\u0642\u0627\u062a \u062f\u0641\u0639 "
    "\u0623\u0648 \u0623\u064a \u062a\u0641\u0627\u0635\u064a\u0644 \u0634\u062e\u0635\u064a\u0629 \u0623\u0648 "
    "\u0635\u062d\u064a\u0629 \u0623\u062e\u0631\u0649."
)
# present tense "(and) we take part in the data-sharing programme" (not after "kunna", the past form)
PRESENT_SHARING_EN = re.compile(r"(?i)\bwe take part in OpenAI'?s data[- ]sharing programme\b")
PRESENT_SHARING_AR = re.compile(
    "(?<!\u0643\u0646\u0627 )(?<!" + AR_LETTER + ")\u0648?\u0646\u0634\u0627\u0631\u0643 "
    "\u0641\u064a \u0628\u0631\u0646\u0627\u0645\u062c \u0645\u0634\u0627\u0631\u0643\u0629 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a"
)
APART_EN = "Apart from OpenAI's data-sharing programme"
APART_AR = "\u0628\u0627\u0633\u062a\u062b\u0646\u0627\u0621 \u0628\u0631\u0646\u0627\u0645\u062c OpenAI"
NOT_SOLD_EN = "We do not sell or otherwise exchange your personal data for anything of value"
NOT_SOLD_AR = "\u0644\u0627 \u0646\u0628\u064a\u0639 \u0628\u064a\u0627\u0646\u0627\u062a\u0643 \u0627\u0644\u0634\u062e\u0635\u064a\u0629"
TERMS_OPENAI_PROVIDER_EN = "Our AI provider is OpenAI"
TERMS_OPENAI_PROVIDER_AR = (
    "\u0648\u0645\u0632\u0648\u0651\u062f \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a "
    "\u0644\u062f\u064a\u0646\u0627 \u0647\u0648 OpenAI"
)
SPONSORED_AR = "\u0645\u0645\u0648\u0651\u0644"
AI_WORD_AR = "\u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a"
S14_TWO_IDS_AR = "\u0645\u0639\u0631\u0651\u0641\u064e\u064a\u0646 \u0639\u0634\u0648\u0627\u0626\u064a\u064a\u0646"
S14_AI_RECORD_AR = (
    "\u0625\u0632\u0627\u0644\u0629 \u0633\u062c\u0644 \u0625\u0630\u0646 \u0627\u0644\u0645\u0639\u0627\u0644\u062c\u0629 "
    "\u0628\u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a"
)
DEVICE_AR = "\u062c\u0647\u0627\u0632"
BASE_TERMS_S4_EN = (
    "Each account can run a limited number of comparisons (currently up to 3 a day and up to 10 a "
    "month; your first 3 comparisons count toward these limits, and the referral rewards described "
    "in section 9 add to the monthly limit)."
)
TRAINING_CLAIM_EN = re.compile(r"(?i)\binform the evaluation and training of its models\b")
# --- V3C (PATH C of item 26, RULINGS_V3C_S81_12 V3C-6): the restored present-tense programme sentence --------
SCOPED_EN = re.compile(r"(?i)\bwe take part in OpenAI'?s data[- ]sharing programme for the requests OpenAI processes:")
SCOPED_AR = re.compile(
    "(?<!" + AR_LETTER + ")\u0648?\u0646\u0634\u0627\u0631\u0643 \u0641\u064a \u0628\u0631\u0646\u0627\u0645\u062c "
    "\u0645\u0634\u0627\u0631\u0643\u0629 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0644\u062f\u0649 OpenAI "
    "\u0641\u064a \u0627\u0644\u0637\u0644\u0628\u0627\u062a \u0627\u0644\u062a\u064a \u062a\u0639\u0627\u0644\u062c\u0647\u0627 OpenAI:"
)  # ... the data-sharing programme at OpenAI in the requests that OpenAI processes:
ENDED_EN = (
    r"(?i)\bprogramme ended\b",
    r"(?i)\bour part in (?:it|the programme) (?:has )?ended\b",
    r"Since then, OpenAI does not use",
)
ENDED_AR = {
    "our part ended": "\u0627\u0646\u062a\u0647\u062a \u0645\u0634\u0627\u0631\u0643\u062a\u0646\u0627",
    "and since that date OpenAI does not use": (
        "\u0648\u0645\u0646\u0630 \u0630\u0644\u0643 \u0627\u0644\u062a\u0627\u0631\u064a\u062e \u0644\u0627 "
        "\u062a\u0633\u062a\u062e\u062f\u0645 OpenAI"
    ),
    "and we used to take part": "\u0648\u0643\u0646\u0627 \u0646\u0634\u0627\u0631\u0643",
}
MARKS_AR = re.compile("[\u064b-\u0652\u0670\u0640]")  # harakat, tanween, shadda, sukun, dagger alif, tatweel
V3C_FIXTURE = "tests/fixtures/legal_v3c_live_sentences.json"
# main 6b909e0a's forks (V3C EK10, OPTION F), by digest (_jsha): d3_training en / ar A + B, and openai_retention.
MAIN_D3_AB_SHA256 = "1a96f76c08107b07fdb693fa7acfb685" "2471a1e0294dabce233eedba6919402e"
MAIN_RETENTION_FORK_SHA256 = "9df7d8b9357b742878fd9ca686807a95" "5b7d04b7f69edfdf36889a60fe3fc0f5"

# Synthetic dormant values (test-only, never a real fact; Arabic: Western digits).
SYN_RESET_EN = "midnight test time (UTC+3)"
SYN_RESET_AR = "\u0645\u0646\u062a\u0635\u0641 \u0627\u0644\u0644\u064a\u0644 \u0628\u062a\u0648\u0642\u064a\u062a \u0627\u0644\u0627\u062e\u062a\u0628\u0627\u0631 (UTC+3)"
SYN_RUNS_EN = "90 days"
SYN_RUNS_AR = "90 \u064a\u0648\u0645\u064b\u0627"
SYN_THROTTLE_EN = "24 hours"
SYN_THROTTLE_AR = "24 \u0633\u0627\u0639\u0629"
SYN_FEEDBACK_EN = "12 months"
SYN_FEEDBACK_AR = "12 \u0634\u0647\u0631\u064b\u0627"
NEW_RETENTION_KEYS = (
    "COMPARE_RUN_RETENTION", "COMPARE_RUN_RETENTION_AR", "AUTH_THROTTLE_RETENTION", "AUTH_THROTTLE_RETENTION_AR",
)
BASE_RETENTION_KEYS = (
    "SECURITY_LOG_RETENTION", "SECURITY_LOG_RETENTION_AR", "ANON_LOG_RETENTION", "ANON_LOG_RETENTION_AR",
)
DORMANT_NULL_KEYS = (
    "DEVICE_QUOTA_RESET", "DEVICE_QUOTA_RESET_AR", "COMPARE_RUN_RETENTION", "COMPARE_RUN_RETENTION_AR",
    "AUTH_THROTTLE_RETENTION", "AUTH_THROTTLE_RETENTION_AR", "COMPARE_RUNS_CLAUSE", "AUTH_THROTTLE_CLAUSE",
)
NEW_FORKS = {"free_limits": "terms", "referral_rewards": "terms", "usage_counters": "privacy"}
NEW_CLAUSES = {"COMPARE_RUNS_CLAUSE": "COMPARE_RUN_RETENTION", "AUTH_THROTTLE_CLAUSE": "AUTH_THROTTLE_RETENTION"}

# Recorded base values (98d85433). Re-record ONLY with a ruling (see each row's docstring).
BASE_I18N_KEY_COUNT = 1011
BASE_I18N_NAMESET_SHA256 = "2d351a2c1fb2c25109ff3363d2ccd6bb24" "e114762d07f5a9acced9d4d9a1f543"
BASE_S7_SHA256 = {
    "en": "b7563dae1cfba69a0fa5b9da7ee7cdd207b166ccc8d818537" "813f7751a9e303c",
    "ar": "96e3a8db7853e618147" "aae0c5cc112cc9ac14508cf967c2e771b7a39e2f35f0b",
}
BASE_S3_5_SHA256 = {
    "en": "78cae5287cede0e0127d95feef8f1a7ae3ce6c34cad0ba77c25272b5cd5776b5",
    "ar": "dbdef2d47a1cb2fc99b815a005d4fa173985" "e7b84c5daa8ceb42a870fad0f10d",
}
BASE_TRANSFER_BASIS_SHA256 = "130653" "784154" "e079034" "2c7ce8b5fd203eaf3747d08aad912ea7ff0d16db74237"
BASE_DELETION_SECTION_SHA256 = "be880578" "c8729f6bf2c1d2f908c7298a29d5ce85535cd7646c56e8912c5d52c2"
BASE_OPENAI_ROW_SHA256 = "c67cb8088079" "d6afe8f" "1146530b41f6801d618cd7d6d79798b72b9762caa0320"
BASE_AR_CONSENT_BODY_SHA256 = "161e8427c78d34c0dcc094494" "95b45bc14a5a8e9137ee43ed309900" "a9bb521c4"
BASE_AR_ONB_HEAD_SHA256 = "83b9943c5799ed77aa2e45f86984a696093" "9684c29286b34e41043cabf6b29ea"

EN_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
GULF_MONTHS_AR = (  # the pinned table of tests/test_legal_docs_u8.py (T6)
    "\u064a\u0646\u0627\u064a\u0631", "\u0641\u0628\u0631\u0627\u064a\u0631", "\u0645\u0627\u0631\u0633",
    "\u0623\u0628\u0631\u064a\u0644", "\u0645\u0627\u064a\u0648", "\u064a\u0648\u0646\u064a\u0648",
    "\u064a\u0648\u0644\u064a\u0648", "\u0623\u063a\u0633\u0637\u0633", "\u0633\u0628\u062a\u0645\u0628\u0631",
    "\u0623\u0643\u062a\u0648\u0628\u0631", "\u0646\u0648\u0641\u0645\u0628\u0631", "\u062f\u064a\u0633\u0645\u0628\u0631",
)
EN_DATE = re.compile(r"\b(" + "|".join(EN_MONTHS) + r")\s+([0-9]{1,2}),\s*([0-9]{4})\b")
AR_DATE = re.compile(r"(?<![0-9])([0-9]{1,2})\s+(" + "|".join(GULF_MONTHS_AR) + r")\s+([0-9]{4})(?![0-9])")
ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
TERMS_VERSION_PY = re.compile(r"(?m)^TERMS_VERSION\s*=\s*['\"]([^'\"]+)['\"]")
SENTENCE_SPLIT = re.compile("(?<=[.!?\u061f])\\s+|\\n+")

NOT_SENT_EN = {
    "negation": r"\b(?:not|never)\b|n't\b",
    "send": r"\b(?:send|sent|share|shared)\b",
    "name": r"\bname\b",
    "email": r"\bemail\b",
    "account": r"\baccount\b",
}


# ---------------------------------------------------------------------------------------------
# helpers (no helper raises: a missing file or key is reported as a problem / None)
# ---------------------------------------------------------------------------------------------

def _read(rel, root=REPO):
    path = Path(root) / rel
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _visible(rel, root=REPO):
    text = _read(rel, root)
    if text is None:
        return None
    return html.unescape(text) if rel.endswith(".html") else text


def _json(rel, root=REPO):
    text = _read(rel, root)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def _esc(text):
    return str(text).encode("unicode_escape").decode("ascii")


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _jsha(value):
    return _sha(json.dumps(value, sort_keys=True, ensure_ascii=True))


def _report(title, problems):
    return title + "\n  - " + "\n  - ".join(_esc(p) for p in problems)


def _section_no(title):
    m = re.match(r"^([0-9]+(?:\.[0-9]+)*)\.?(?=\s|$)", title.strip())
    return m.group(1) if m else None


def _section(text, number, with_heading=False):
    """The level-2 section `number` (## N.) up to the next level-2 heading, or None."""
    if text is None:
        return None
    lines, start, head = text.split("\n"), None, None
    for i, line in enumerate(lines):
        m = re.match(r"^##(?!#)[ \t]+(.+)$", line)
        if not m:
            continue
        if start is not None:
            body = lines[start:i]
            return "\n".join(([head] if with_heading else []) + body)
        if _section_no(m.group(1)) == number:
            start, head = i + 1, line
    if start is None:
        return None
    return "\n".join(([head] if with_heading else []) + lines[start:])


def _heading(text, number):
    section = _section(text, number, with_heading=True)
    return section.split("\n", 1)[0] if section else None


def _subsection(text, number):
    """A ### N.M subsection body up to the next heading of level 2 or 3, or None."""
    if text is None:
        return None
    lines, start = text.split("\n"), None
    for i, line in enumerate(lines):
        m = re.match(r"^(#{2,3})[ \t]+(.+)$", line)
        if not m:
            continue
        if start is not None:
            return "\n".join(lines[start:i])
        if m.group(1) == "###" and _section_no(m.group(2)) == number:
            start = i + 1
    return "\n".join(lines[start:]) if start is not None else None


def _region(text):
    if text is None:
        return None
    i, j = text.find(REGION_BEGIN), text.find(REGION_END)
    if i < 0 or j < i:
        return None
    return html.unescape(re.sub(r"<[^>]+>", " ", text[i + len(REGION_BEGIN):j]))


def _sentences(text):
    return [s for s in SENTENCE_SPLIT.split(text or "") if s.strip()]


def _iso(year, month, day):
    try:
        return datetime.date(int(year), month, int(day)).isoformat()
    except ValueError:
        return None


def _en_date(text):
    m = EN_DATE.search(text or "")
    return _iso(m.group(3), EN_MONTHS.index(m.group(1)) + 1, m.group(2)) if m else None


def _ar_date(text):
    m = AR_DATE.search(text or "")
    return _iso(m.group(3), GULF_MONTHS_AR.index(m.group(2)) + 1, m.group(1)) if m else None


def _terms_version(root=REPO):
    m = TERMS_VERSION_PY.search(_read(CONSENT_SERVICE, root) or "")
    return m.group(1) if m and ISO_DATE.match(m.group(1)) else None


def _data(root=REPO):
    data = _json(FILL_IN, root)
    return data if isinstance(data, dict) else {}


def _placeholders(root=REPO):
    value = _data(root).get("placeholders")
    return value if isinstance(value, dict) else {}


def _variants():
    value = _json(VARIANTS)
    return value if isinstance(value, dict) else {}


def _catalog(rel):
    value = _json(rel)
    return value if isinstance(value, dict) else {}


def _v3c_text(rid, lang, block="live"):
    """The text of a V3C fixture entry (tests/fixtures/legal_v3c_live_sentences.json), or None (never raises)."""
    data = _json(V3C_FIXTURE)
    for entry in (data.get(block) if isinstance(data, dict) else None) or []:
        if isinstance(entry, dict) and entry.get("id") == rid and entry.get("lang") == lang:
            text = entry.get("text")
            return text if isinstance(text, str) and text.strip() else None
    return None


def _load(rel, name):
    """A repo script loaded by path (fill_in_legal / the renderer import nothing outside the stdlib)."""
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def _copy_tree(root):
    """Pages and renderer from the checkout, the six sources from the pre-fill snapshot (d3c pattern)."""
    for rel in SOURCES + PAGES + (RENDERER,):
        src = f"{PREFILL}/{Path(rel).name}" if rel in SOURCES else rel
        dest = Path(root) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / src, dest)


def _plan(root, data):
    """(outputs {rel: filled text} or None, problem or None): fill_in_legal.plan on a temp tree."""
    fill = _load(FILL_SCRIPT, "_s81_12_fill_in_plan")
    try:
        missing, outputs = fill.plan(Path(root), data, _variants())
    except Exception as exc:  # noqa: BLE001 -- reported as a problem (AssertionError in the row)
        return None, f"fill_in_legal.plan refused the data: {type(exc).__name__}: {_esc(exc)[:400]}"
    if missing:
        return None, f"fill_in_legal.plan reports missing values {missing}"
    return {rel: new.decode("utf-8").replace("\r\n", "\n") for rel, (new, _old) in outputs.items()}, None


def _dry_run_rc(root, data_path, data, capsys):
    fill = _load(FILL_SCRIPT, "_s81_12_fill_in_dry")
    Path(data_path).write_text(json.dumps(data), encoding="utf-8")
    rc = fill.main(["--repo-root", str(root), "--data", str(data_path), "--variants", str(REPO / VARIANTS), "--dry-run"])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def _recorded(data, *, device=False, runs=False, throttle=False, feedback=False):
    """A copy of the committed data with synthetic dormant values recorded (test-only)."""
    data = copy.deepcopy(data)
    ph = data.setdefault("placeholders", {})
    if device:
        ph["DEVICE_QUOTA_RESET"], ph["DEVICE_QUOTA_RESET_AR"] = SYN_RESET_EN, SYN_RESET_AR
    if runs:
        ph["COMPARE_RUN_RETENTION"], ph["COMPARE_RUN_RETENTION_AR"] = SYN_RUNS_EN, SYN_RUNS_AR
    if throttle:
        ph["AUTH_THROTTLE_RETENTION"], ph["AUTH_THROTTLE_RETENTION_AR"] = SYN_THROTTLE_EN, SYN_THROTTLE_AR
    if feedback:
        for key in [k for k, v in ph.items() if v is None and "FEEDBACK" in k and not k.endswith("_CLAUSE")]:
            ph[key] = SYN_FEEDBACK_AR if key.endswith("_AR") else SYN_FEEDBACK_EN
    if runs or throttle or feedback:
        ph["RETENTION_CLEANUP_LIVE"] = "true"  # UL8: a fixed period needs the cleanup live
    return data


def _lines_with(text, needle):
    return [line for line in (text or "").split("\n") if needle in line]


# =============================================================================================
# R1 / R1b -- both AI processors named; the Anthropic facts (R-S12-1, R-S12-13)
# =============================================================================================

@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r1_privacy_s4_names_both_processors_and_the_anthropic_facts(lang):
    """RED: privacy s4 names Anthropic (heading too) and OpenAI, states Anthropic's no-training
    and retention facts with "up to" periods (R-S12-13: 30 days API, 29 days batch, the
    usage-policy exception), carries the conditional web-search sentence (D7) and the photo
    guidance exactly once."""
    rel = PRIVACY_EN if lang == "en" else PRIVACY_AR
    text = _read(rel)
    s4 = _section(text, "4") or ""
    head = _heading(text, "4") or ""
    problems = []
    if "Anthropic" not in head:
        problems.append(f"{rel}: the section 4 heading does not name Anthropic: {head[:80]!r}")
    if lang == "en":
        if s4.count(DUAL_EN) != 1:
            problems.append(f"s4 carries the R-S12-1 dual-provider sentence {s4.count(DUAL_EN)} times (want 1)")
        if not any("Anthropic" in s and re.search(r"\b(?:not|never)\b", s) and re.search(r"\btrain", s) for s in _sentences(s4)):
            problems.append("no s4 sentence says Anthropic does not use the data to train its models")
        if len(re.findall(r"\bup to 30 days\b", s4)) < 2:
            problems.append("s4 lacks 'up to 30 days' for Anthropic's API retention beside OpenAI's (R-S12-13)")
        for label, pattern in (
            ("up to 29 days", r"\bup to 29 days\b"),
            ("batch requests", r"\bbatch(?:es|ed)?\b"),
            ("the usage-policy exception", r"\busage polic(?:y|ies)\b"),
            ("a conditional web-search sentence (If we use ... web search)", r"\bIf we use [^.]*\bweb search\b"),
            ("never your identity", r"\bnever your identity\b"),
        ):
            if not re.search(pattern, s4):
                problems.append(f"s4 lacks {label}")
        if s4.count(PHOTO_EN) != 1:
            problems.append(f"s4 carries the photo guidance {s4.count(PHOTO_EN)} times (want 1)")
    else:
        for label, pattern in (
            ("Anthropic, PBC", r"Anthropic[,\u060c]?\s*PBC"),
            ("OpenAI, L.L.C", r"OpenAI[,\u060c]?\s*L\.L\.C"),
            ("30 (days)", r"(?<![0-9])30(?![0-9])"),
            ("29 (days, batch)", r"(?<![0-9])29(?![0-9])"),
        ):
            if not re.search(pattern, s4):
                problems.append(f"AR s4 lacks {label}")
        if s4.count(PHOTO_AR) != 1:
            problems.append(f"AR s4 carries the base photo guidance {s4.count(PHOTO_AR)} times (want 1)")
    assert not problems, _report(f"R1 ({lang}): privacy section 4 names both AI processors:", problems)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r1b_dual_provider_sentence_in_privacy_s2_s5_and_terms_s8(lang):
    """RED: R-S12-1 -- privacy s2 and Terms s8 carry the dual-provider sentence (EN verbatim);
    privacy s2, s5 and Terms s8 name both Anthropic and OpenAI (EN and AR)."""
    priv = _read(PRIVACY_EN if lang == "en" else PRIVACY_AR)
    terms = _read(TERMS_EN if lang == "en" else TERMS_AR)
    problems = []
    places = {"privacy s2": _section(priv, "2") or "", "privacy s5": _section(priv, "5") or "",
              "terms s8": _section(terms, "8") or ""}
    for where, body in places.items():
        for name in ("Anthropic", "OpenAI"):
            if name not in body:
                problems.append(f"{where} does not name {name}")
        if lang == "en" and where != "privacy s5" and body.count(DUAL_EN) != 1:
            problems.append(f"{where} carries the dual-provider sentence {body.count(DUAL_EN)} times (want 1)")
    assert not problems, _report(f"R1b ({lang}): the R-S12-1 dual-provider wording:", problems)


# =============================================================================================
# R2 / R3 -- the data-sharing programme ended (R-S12-4); the bare not-sold promise
# =============================================================================================

@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r2_no_present_tense_sharing_and_one_history_sentence(lang):
    """RED, amended V3C (EK7, PATH C of item 26; node id kept): the present-tense programme sentence, scoped.
    The present-tense "we take part in OpenAI's data-sharing programme" (EN; the AR twin) occurs exactly once
    in privacy s2, exactly once in privacy s4 (there followed by the scope 'for the requests OpenAI
    processes:'; AR the scope twin) and exactly once in Terms s8, and each landing region carries the same
    count as its source; no source or region tells the programme as ended (EN 'programme ended', 'our part in
    it / the programme (has) ended', 'Since then, OpenAI does not use'; AR marks-insensitive 'our part ended',
    'and since that date OpenAI does not use', 'and we used to take part')."""
    docs = (PRIVACY_EN, TERMS_EN) if lang == "en" else (PRIVACY_AR, TERMS_AR)
    rx = PRESENT_SHARING_EN if lang == "en" else PRESENT_SHARING_AR
    problems = []
    for rel, number in ((docs[0], "2"), (docs[0], "4"), (docs[1], "8")):
        body = _section(_read(rel), number) or ""
        n = len(rx.findall(body))
        if n != 1:
            problems.append(f"{rel} s{number} carries the present-tense programme sentence {n} times (want 1)")
    s4 = _section(_read(docs[0]), "4") or ""
    scoped = SCOPED_EN if lang == "en" else SCOPED_AR
    if len(scoped.findall(s4)) != 1:
        problems.append("privacy s4: the programme sentence does not carry the scope 'for the requests OpenAI processes'")
    for rel in docs:
        text = _read(rel)
        for where, body in ((rel, text), (PAGE_OF[rel], _region(_read(PAGE_OF[rel])))):
            if body is None:
                problems.append(f"{where}: missing or no legal region")
                continue
            if where != rel and len(rx.findall(" ".join(body.split()))) != len(rx.findall(" ".join((text or "").split()))):
                problems.append(f"{where}: the region carries a different count of the programme sentence than its source")
            if lang == "en":
                for pattern in ENDED_EN:
                    if re.search(pattern, body):
                        problems.append(f"{where}: carries the ended story {pattern!r}")
            else:
                flat = MARKS_AR.sub("", body)
                for label, needle in ENDED_AR.items():
                    if needle in flat:
                        problems.append(f"{where}: carries the AR ended story '{label}'")
    assert not problems, _report(f"R2 ({lang}): the present-tense programme sentence, scoped:", problems)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r3_bare_not_sold_promise(lang):
    """RED, amended V3C (EK8 + C6; node id kept): privacy s2 and Terms s8 each state the not-sold promise
    exactly once in main's carve-out form ("Apart from OpenAI's data-sharing programme described below, we
    do not sell or otherwise exchange your personal data for anything of value"; AR: the carve-out opening of
    main's sentence from the V3C fixture followed by the promise); the bare sentence-initial promise ("We do
    not sell or otherwise exchange", capital W) is absent from the four sources and their regions; AR: in every
    section of both documents and in both regions the promise occurs only directly after the carve-out
    opening (the counts are equal)."""
    priv, terms = (PRIVACY_EN, TERMS_EN) if lang == "en" else (PRIVACY_AR, TERMS_AR)
    problems = []
    if lang == "en":
        carve, promise = APART_EN + " described below, we do not sell or otherwise exchange your personal data for anything of value", NOT_SOLD_EN
    else:
        s1 = _v3c_text("S1", "ar") or ""
        i = s1.find(NOT_SOLD_AR)
        carve, promise = (s1[:i + len(NOT_SOLD_AR)] if i > 0 else None), NOT_SOLD_AR
        if carve is None:
            problems.append("the V3C fixture S1 (ar) does not carry the carve-out form")
            carve = APART_AR + " " + NOT_SOLD_AR
    for where, body in (("privacy s2", _section(_read(priv), "2")), ("terms s8", _section(_read(terms), "8"))):
        if (body or "").count(carve) != 1:
            problems.append(f"{where} does not carry the carve-out form of the not-sold promise once")
    for rel in (priv, terms):
        text = _read(rel) or ""
        places = [(f"{rel} s{n}", body) for n, body in _sections_of(text).items()]
        places.append((PAGE_OF[rel], " ".join((_region(_read(PAGE_OF[rel])) or "").split())))
        for where, body in places:
            if lang == "en":
                if promise in body:
                    problems.append(f"{where} carries the bare sentence-initial not-sold promise")
            elif body.count(promise) != body.count(carve):
                problems.append(f"{where}: the AR not-sold promise occurs outside the carve-out form")
    assert not problems, _report(f"R3 ({lang}): the not-sold promise in main's carve-out form:", problems)


# =============================================================================================
# R4 -- privacy s5 recipients
# =============================================================================================

@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r4_privacy_s5_two_ai_bullets_and_dated_carveout(lang):
    """RED, amended V3C (EK9; node id kept): privacy s5 has exactly one Anthropic and one OpenAI bullet; the
    carve-out is main's undated line ('Except as section 4 describes for OpenAI and as this section describes
    for our mailbox provider, ...'; the AR twin from the V3C fixture) exactly once, and s5 carries NO date;
    EN also carries the email-delivery fragment (D9)."""
    s5 = _section(_read(PRIVACY_EN if lang == "en" else PRIVACY_AR), "5") or ""
    problems = []
    for name in ("Anthropic", "OpenAI"):
        n = len(re.findall(r"(?m)^- \*\*" + name + r":\*\*", s5))
        if n != 1:
            problems.append(f"s5 has {n} '- **{name}:**' bullets (want 1)")
    line = _v3c_text("C5", lang)
    if line is None or s5.split("\n").count(line) != 1:
        problems.append("s5 does not carry main's undated carve-out line once")
    if (EN_DATE if lang == "en" else AR_DATE).findall(s5):
        problems.append("s5 carries a date")
    if lang == "en" and "directly or through an email-delivery provider" not in s5:
        problems.append("the sign-in-provider bullet lacks ', directly or through an email-delivery provider' (D9)")
    assert not problems, _report(f"R4 ({lang}): privacy section 5:", problems)


# =============================================================================================
# R6 / R7 / R8 -- catalogue, crawler, Sponsored, AI disclosure, Terms
# =============================================================================================

@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r6_privacy_s6_catalogue_crawler_and_sponsored(lang):
    """RED: privacy s6 describes the owned catalogue: the crawler identified by the user-agent string
    published at getmyez.com/bot (R-S12-2, never the old brand token: P4), operator entry by hand,
    licensed data, and store links marked Sponsored that never change the ranking."""
    s6 = _section(_read(PRIVACY_EN if lang == "en" else PRIVACY_AR), "6") or ""
    problems = []
    if lang == "en":
        if not re.search(re.escape(CRAWLER_EN), s6, re.I):
            problems.append("s6 lacks the R-S12-2 crawler sentence")
        for label, pattern in (
            ("operator entry (by hand)", r"\bby hand\b"),
            ("licensed data", r"\blicens"),
            ("Sponsored", r"\bSponsored\b"),
            ("never changes the comparison/score/rank", r"\bnever changes how products are compared, scored or ranked\b"),
        ):
            if not re.search(pattern, s6):
                problems.append(f"s6 lacks {label}")
    else:
        for label, needle in (("the bot page address", BOT_URL_AR), ("robots.txt", "robots.txt"), ("Sponsored", SPONSORED_AR)):
            if needle not in s6:
                problems.append(f"AR s6 lacks {label}")
        if BOT_URL in s6:
            problems.append("AR s6 names the bot page address with the trailing slash")
    assert not problems, _report(f"R6 ({lang}): privacy section 6:", problems)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r7_privacy_s12_ai_disclosure(lang):
    """RED: privacy s12 (children and young people) tells that comparisons are written by AI, that the
    App asks permission first and that requests and results are checked for unsafe content."""
    s12 = _section(_read(PRIVACY_EN if lang == "en" else PRIVACY_AR), "12") or ""
    problems = []
    if lang == "en":
        for label, pattern in (("written by AI", r"\bwritten by AI\b"), ("permission", r"\bpermission\b"),
                               ("unsafe content", r"\bunsafe content\b")):
            if not re.search(pattern, s12):
                problems.append(f"s12 lacks {label}")
    elif AI_WORD_AR not in s12:
        problems.append("AR s12 does not mention AI")
    assert not problems, _report(f"R7 ({lang}): privacy section 12:", problems)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r8_terms_s7_sponsored_and_s8_provider(lang):
    """RED: Terms s7 discloses Sponsored links (never a recommendation) and the own catalogue; Terms s8 no
    longer says the AI provider is OpenAI alone."""
    terms = _read(TERMS_EN if lang == "en" else TERMS_AR)
    s7, s8 = _section(terms, "7") or "", _section(terms, "8") or ""
    problems = []
    if lang == "en":
        for label, pattern in (("Sponsored", r"\bSponsored\b"), ("not a recommendation", r"\bnot a recommendation\b"),
                               ("the own catalogue", r"\bcatalogue\b")):
            if not re.search(pattern, s7):
                problems.append(f"terms s7 lacks {label}")
        if TERMS_OPENAI_PROVIDER_EN in s8:
            problems.append("terms s8 still says 'Our AI provider is OpenAI'")
    else:
        if SPONSORED_AR not in s7:
            problems.append("AR terms s7 lacks Sponsored")
        if TERMS_OPENAI_PROVIDER_AR in s8:
            problems.append("AR terms s8 still says the AI provider is OpenAI")
    assert not problems, _report(f"R8 ({lang}): Terms sections 7 and 8:", problems)


# =============================================================================================
# R9 -- the processor manifest (R-S12-11)
# =============================================================================================

def _public_name_ids(rel):
    """The literal ids of the module-level PUBLIC_NAME_IDS = frozenset({...}) in a test file, or None."""
    source = _read(rel)
    if source is None:
        return None
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "PUBLIC_NAME_IDS" for t in node.targets):
            value = node.value
            if isinstance(value, ast.Call) and value.args:
                value = value.args[0]
            try:
                return set(ast.literal_eval(value))
            except ValueError:
                return None
    return None


def test_r9_manifest_anthropic_row_public_and_named():
    """RED: R-S12-11 -- the anthropic processors row (S81-06 adds it gated; this unit makes it public) is a
    personal-data row with public_name true and api.anthropic.com, its name and category appear in both
    privacy policies, PUBLIC_NAME_IDS names it in both test files, and the openai row is unchanged."""
    manifest = _json(MANIFEST) or {}
    rows = [r for r in manifest.get("rows", []) if isinstance(r, dict)]
    by_id = {r.get("id"): r for r in rows}
    row = by_id.get("anthropic")
    problems = []
    en, ar = _read(PRIVACY_EN) or "", _read(PRIVACY_AR) or ""
    if row is None:
        problems.append(f"{MANIFEST} has no 'anthropic' row")
    else:
        if row.get("personal_data") is not True:
            problems.append("anthropic: personal_data must be true")
        if row.get("public_name") is not True:
            problems.append("anthropic: public_name must be true (R-S12-11: this unit names Anthropic)")
        if "api.anthropic.com" not in (row.get("hosts") or []):
            problems.append("anthropic: hosts must list api.anthropic.com")
        if row.get("gate_flag") not in (None, "ENABLE_ANTHROPIC_TEXT"):
            problems.append(f"anthropic: unexpected gate_flag {row.get('gate_flag')!r}")
        for key, text, label in (("name_en", en, "privacy EN"), ("name_ar", ar, "privacy AR"),
                                 ("category_en", en, "privacy EN"), ("category_ar", ar, "privacy AR")):
            value = row.get(key) or ""
            if not value or not re.search("(?<!\\w)[\u0628\u0644\u0648]?" + re.escape(value) + "(?!\\w)", text):
                problems.append(f"anthropic: {key} {value!r} is not in {label}")
    openai_row = by_id.get("openai")
    if openai_row is None or _jsha(openai_row) != BASE_OPENAI_ROW_SHA256:
        problems.append("the openai row changed (OpenAI stays a transition processor, R-S12-1)")
    for rel in (U8_TESTS, S78_TESTS):
        ids = _public_name_ids(rel)
        if ids is None or "anthropic" not in ids:
            problems.append(f"{rel}: PUBLIC_NAME_IDS {sorted(ids) if ids else ids} lacks 'anthropic'")
    assert not problems, _report("R9: the anthropic processors row:", problems)


# =============================================================================================
# R10 -- fill-in data and variants shape (D4, D5, D6, R-S12-4, R-S12-9, R-S12-16)
# =============================================================================================

def test_r10_fill_in_data_and_variants_shape():
    """RED, amended V3C (EK10, PATH C OPTION F): d3 'C' (main's answer); openai_store_pinned stays true
    (R-S12-17); the forks d3_training (answer 'd3', inline 'A', docs ['privacy'], en / ar A and B equal to
    main's by digest, C = the V3C scoped paragraph built from the fixture: the scoped programme sentence, the
    governed sentence, the adapted applies sentence, the in-return sentence) and openai_retention (main's
    block, by digest) are back; the dormant forks free_limits / referral_rewards / usage_counters and clauses
    COMPARE_RUNS_CLAUSE / AUTH_THROTTLE_CLAUSE exist (EN + AR, if_null ""); the ten new placeholder keys
    exist, the eight dormant ones null, AI_SWITCH_DATE / _AR recorded."""
    data, variants = _data(), _variants()
    forks, clauses, ph = variants.get("forks") or {}, variants.get("clauses") or {}, _placeholders()
    problems = []
    if data.get("d3") != "C":
        problems.append(f"d3 is {data.get('d3')!r} (want 'C': PATH C, main's answer)")
    if data.get("openai_store_pinned") is not True:
        problems.append("openai_store_pinned must stay true (R-S12-17)")
    d3f, ret = forks.get("d3_training"), forks.get("openai_retention")
    if not isinstance(d3f, dict):
        problems.append("fork d3_training is missing (V3C OPTION F returns it)")
    else:
        if d3f.get("answer") != "d3" or d3f.get("inline") != "A" or d3f.get("docs") != ["privacy"]:
            problems.append("fork d3_training: answer / inline / docs are not main's ('d3', 'A', ['privacy'])")
        ab = {lang: {k: (d3f.get(lang) or {}).get(k) for k in ("A", "B")} for lang in ("en", "ar")}
        if _jsha(ab) != MAIN_D3_AB_SHA256:
            problems.append("fork d3_training: the A / B variants differ from main's")
        for lang in ("en", "ar"):
            parts = [_v3c_text("P4s", lang, "ruled"), _v3c_text("P4g", lang), _v3c_text("C2", lang, "ruled"), _v3c_text("P4r", lang)]
            want = " ".join(parts) if all(parts) else None
            if want is None or (d3f.get(lang) or {}).get("C") != want:
                problems.append(f"fork d3_training: {lang}.C is not the V3C scoped paragraph")
    if not isinstance(ret, dict) or _jsha(ret) != MAIN_RETENTION_FORK_SHA256:
        problems.append("fork openai_retention is missing or differs from main's block")
    for name, doc in NEW_FORKS.items():
        fork = forks.get(name)
        if not isinstance(fork, dict):
            problems.append(f"fork {name} missing")
            continue
        if doc not in (fork.get("docs") or []):
            problems.append(f"fork {name}: docs must include {doc!r}")
        if fork.get("answer") != {"en": "placeholders.DEVICE_QUOTA_RESET", "ar": "placeholders.DEVICE_QUOTA_RESET_AR"}:
            problems.append(f"fork {name}: answer must be DEVICE_QUOTA_RESET(_AR)")
        if fork.get("if_null") != "":
            problems.append(f"fork {name}: if_null must be ''")
        for lang in ("en", "ar"):
            if not {"empty", "nonempty"} <= set((fork.get(lang) or {})):
                problems.append(f"fork {name}: {lang} must carry empty and nonempty")
    for name, key in NEW_CLAUSES.items():
        clause = clauses.get(name)
        if not isinstance(clause, dict):
            problems.append(f"clause {name} missing")
            continue
        if clause.get("answer") != {"en": f"placeholders.{key}", "ar": f"placeholders.{key}_AR"}:
            problems.append(f"clause {name}: answer must be {key}(_AR)")
        if clause.get("if_null") != "":
            problems.append(f"clause {name}: if_null must be ''")
        for lang in ("en", "ar"):
            table = (clause.get(lang) or {}).get("privacy") or {}
            if table.get("empty") != "" or "{value}" not in str(table.get("nonempty", "")):
                problems.append(f"clause {name}: {lang}.privacy must be {{empty: '', nonempty: '...{{value}}...'}}")
    for key in DORMANT_NULL_KEYS:
        if key not in ph:
            problems.append(f"placeholders.{key} missing")
        elif ph[key] is not None:
            problems.append(f"placeholders.{key} must be null (dormant)")
    for key in ("AI_SWITCH_DATE", "AI_SWITCH_DATE_AR"):
        if not (isinstance(ph.get(key), str) and ph[key].strip()):
            problems.append(f"placeholders.{key} must be recorded")
    assert not problems, _report("R10: fill-in data and variants:", problems)


# =============================================================================================
# R11 / R12 / R18 -- the dormant texts (temp copies, synthetic values)
# =============================================================================================

def _require_forks_and_clauses(names_forks=(), names_clauses=()):
    variants = _variants()
    problems = [f"fork {n} missing" for n in names_forks if n not in (variants.get("forks") or {})]
    problems += [f"clause {n} missing" for n in names_clauses if n not in (variants.get("clauses") or {})]
    return problems


def test_r11_device_rule_texts_dormant_until_recorded(tmp_path, capsys):
    """RED: with DEVICE_QUOTA_RESET null the filled Terms keep today's account limits (s4) and rewards
    (s9 'How rewards work'); with a synthetic reset recorded the fill selects the each-device limit,
    the paused rewards (R-S12-9 wording; '3 successful invites per device' and '7 days' kept for
    tests/test_legal_routes.py) and the privacy s8 device counters; dry run rc 0 both ways."""
    problems = _require_forks_and_clauses(tuple(NEW_FORKS))
    assert not problems, _report("R11: the dormant device-rule forks are missing:", problems)
    root = tmp_path / "repo"
    _copy_tree(root)
    committed = _data()
    dormant, problem = _plan(root, committed)
    assert dormant is not None, f"R11 dormant fill: {problem}"
    t4 = _section(dormant.get(TERMS_EN), "4") or ""
    t9 = _section(dormant.get(TERMS_EN), "9") or ""
    if BASE_TERMS_S4_EN not in t4:
        problems.append("dormant: terms s4 lost today's account-limit sentence")
    if "**How rewards work:**" not in t9:
        problems.append("dormant: terms s9 lost 'How rewards work'")
    recorded_data = _recorded(committed, device=True)
    recorded, problem = _plan(root, recorded_data)
    assert recorded is not None, f"R11 recorded fill: {problem}"
    r4 = _section(recorded.get(TERMS_EN), "4") or ""
    r9 = _section(recorded.get(TERMS_EN), "9") or ""
    rp8 = _section(recorded.get(PRIVACY_EN), "8") or ""
    if "Each device can run up to 3 comparisons a day" not in r4 or SYN_RESET_EN not in r4:
        problems.append("recorded: terms s4 lacks the each-device limit with the reset time")
    if BASE_TERMS_S4_EN in r4:
        problems.append("recorded: terms s4 still carries today's account-limit sentence")
    if not re.search(r"\bpaused\b", r9) or "**How rewards work:**" in r9:
        problems.append("recorded: terms s9 does not say the rewards are paused")
    if not re.search(r"remain usable until they expire or the daily device limit applies", r9):
        problems.append("recorded: terms s9 lacks the R-S12-9 wording for earlier bonus comparisons")
    whole = recorded.get(TERMS_EN) or ""
    for needle in ("3 successful invites per device", "7 days"):
        if needle not in whole:
            problems.append(f"recorded: terms lost {needle!r} (tests/test_legal_routes.py)")
    if not any(SYN_RESET_EN in line and re.search(r"\bdevice\b", line) for line in _lines_with(rp8, "Usage counters")):
        problems.append("recorded: privacy s8 'Usage counters' bullet lacks the device counter and reset time")
    for rel, where in ((TERMS_AR, "AR terms s4"), (PRIVACY_AR, "AR privacy s8")):
        number = "4" if rel == TERMS_AR else "8"
        if SYN_RESET_AR not in (_section(recorded.get(rel), number) or ""):
            problems.append(f"recorded: {where} lacks the AR reset value")
    if (_section(recorded.get(TERMS_AR), "9") or "") == (_section(dormant.get(TERMS_AR), "9") or ""):
        problems.append("recorded: AR terms s9 did not switch to the paused text")
    for label, data in (("dormant", committed), ("recorded", recorded_data)):
        rc, _out, err = _dry_run_rc(root, tmp_path / f"{label}.json", data, capsys)
        if rc != 0:
            problems.append(f"{label} dry run rc {rc}: {err.strip()[:300]}")
    assert not problems, _report("R11: the device-rule texts (DEVICE_QUOTA_RESET):", problems)


def _clause_literal(name, lang):
    table = (((_variants().get("clauses") or {}).get(name) or {}).get(lang) or {}).get("privacy") or {}
    parts = [p.strip() for p in str(table.get("nonempty", "")).split("{value}")]
    return max(parts, key=len) if parts else ""


def test_r12_compare_run_and_throttle_bullets_dormant_until_recorded(tmp_path, capsys):
    """RED: with COMPARE_RUN_RETENTION / AUTH_THROTTLE_RETENTION null no bullet text is published; with
    synthetic periods recorded (and the cleanup recorded live, the UL8 rule R19 adds) each bullet appears
    once in privacy s8 as a list item with its value; the compare-run bullet says the record stays linked
    to the account until it is deleted (R-S12-9: compare_runs keep comparison_id)."""
    problems = _require_forks_and_clauses((), tuple(NEW_CLAUSES))
    assert not problems, _report("R12: the dormant clauses are missing:", problems)
    for name in NEW_CLAUSES:
        for lang, rel in (("en", PRIVACY_EN), ("ar", PRIVACY_AR)):
            literal = _clause_literal(name, lang)
            if not literal or literal in (_read(rel) or ""):
                problems.append(f"{rel}: the dormant {name} text is published (or empty) while its value is null")
    root = tmp_path / "repo"
    _copy_tree(root)
    data = _recorded(_data(), runs=True, throttle=True)
    recorded, problem = _plan(root, data)
    assert recorded is not None, f"R12 recorded fill: {problem}"
    s8 = _section(recorded.get(PRIVACY_EN), "8") or ""
    for value, label in ((SYN_RUNS_EN, "compare-run"), (SYN_THROTTLE_EN, "auth-throttle")):
        lines = [line for line in s8.split("\n") if value in line]
        if len(lines) != 1 or not lines[0].startswith("- "):
            problems.append(f"privacy s8: the {label} value is in {len(lines)} lines (want one list item)")
    runs = [line for line in s8.split("\n") if SYN_RUNS_EN in line]
    if runs and not (re.search(r"\baccount\b", runs[0]) and re.search(r"(?i)\bdelet", runs[0])
                     and not re.search(r"(?i)not linked to an account", runs[0])):
        problems.append("the compare-run bullet does not say it stays linked to the account until deletion (R-S12-9)")
    throttle = [line for line in s8.split("\n") if SYN_THROTTLE_EN in line]
    if throttle and not re.search(r"(?i)\battempt", throttle[0]):
        problems.append("the auth-throttle bullet does not name the attempt counters")
    s8_ar = _section(recorded.get(PRIVACY_AR), "8") or ""
    for value in (SYN_RUNS_AR, SYN_THROTTLE_AR):
        if s8_ar.count(value) != 1:
            problems.append(f"AR privacy s8 carries an AR synthetic value {s8_ar.count(value)} times (want 1)")
    renderer = _load(RENDERER, "_s81_12_renderer_r12")
    try:
        renderer.render_markdown(recorded.get(PRIVACY_EN) or "")
        renderer.render_markdown(recorded.get(PRIVACY_AR) or "")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"the renderer refuses the recorded privacy text: {type(exc).__name__}")
    rc, _out, err = _dry_run_rc(root, tmp_path / "recorded.json", data, capsys)
    if rc != 0:
        problems.append(f"recorded dry run rc {rc}: {err.strip()[:300]}")
    assert not problems, _report("R12: the compare-run and auth-throttle bullets:", problems)


_FEEDBACK_KEY_EN = re.compile(r"(?i)\b(?:HMAC|one-way code|keyed hash|pseudonymous)\b")


def _feedback_lines(s8):
    return [line for line in (s8 or "").split("\n")
            if re.search(r"(?i)\bfeedback\b", line) and _FEEDBACK_KEY_EN.search(line) and re.search(r"(?i)\bdevice\b", line)]


def test_r18_kb_feedback_device_key_disclosure_dormant(tmp_path):
    """RED: R-S12-18 -- privacy s8 discloses kb_feedback's pseudonymous device key (a one-way code of the
    device identifier, never the identifier itself), kept up to 12 months and deleted with the account's
    compare records (S81-22); dormant: absent from the committed policy, present once S81-22's values are
    recorded (every dormant selector recorded here: device reset, compare-run and throttle periods and any
    *FEEDBACK* placeholder)."""
    problems = []
    if _feedback_lines(_section(_read(PRIVACY_EN), "8")):
        problems.append("the committed privacy s8 already carries the kb_feedback disclosure (it must be dormant)")
    root = tmp_path / "repo"
    _copy_tree(root)
    dormant, problem = _plan(root, _data())
    recorded, problem2 = _plan(root, _recorded(_data(), device=True, runs=True, throttle=True, feedback=True))
    both_filled = dormant is not None and recorded is not None
    assert both_filled, f"R18 fill: dormant={problem} recorded={problem2}"
    lines = _feedback_lines(_section(recorded.get(PRIVACY_EN), "8"))
    if len(lines) != 1:
        problems.append(f"recorded: privacy s8 has {len(lines)} kb_feedback device-key bullets (want 1)")
    else:
        for label, pattern in (("12 months", r"(?i)\b(?:12 months|twelve months|365 days)\b"),
                               ("never the identifier itself", r"(?i)\bidentifier itself\b"),
                               ("deleted with the account's compare records", r"(?i)\bdelet")):
            if not re.search(pattern, lines[0]):
                problems.append(f"recorded: the kb_feedback bullet lacks {label}")
    ar_d, ar_r = _section(dormant.get(PRIVACY_AR), "8") or "", _section(recorded.get(PRIVACY_AR), "8") or ""
    new_ar = [line for line in ar_r.split("\n") if line not in ar_d.split("\n")]
    if not any(re.search(r"(?<![0-9])(?:12|365)(?![0-9])", line) and DEVICE_AR in line for line in new_ar):
        problems.append("recorded: AR privacy s8 gains no device-key bullet with its 12-month period")
    assert not problems, _report("R18: the kb_feedback device-key disclosure (dormant):", problems)


def test_r19_dormant_retention_keys_refuse_a_fixed_period_until_cleanup_live():
    """RED: R-S12-9 -- COMPARE_RUN_RETENTION and AUTH_THROTTLE_RETENTION (and their _AR twins) join
    fill_in_legal.RETENTION_KEYS: a fixed period is refused until RETENTION_CLEANUP_LIVE is "true"
    (UL8); the four base keys stay."""
    fill = _load(FILL_SCRIPT, "_s81_12_fill_in_r19")
    keys = set(getattr(fill, "RETENTION_KEYS", ()))
    problems = [f"RETENTION_KEYS lost {k}" for k in BASE_RETENTION_KEYS if k not in keys]
    check = getattr(fill, "_answer_placeholder_problems", None)
    assert callable(check), "fill_in_legal._answer_placeholder_problems is gone"
    for key in NEW_RETENTION_KEYS:
        if key not in keys:
            problems.append(f"RETENTION_KEYS lacks {key}")
        value = SYN_RUNS_AR if key.endswith("_AR") else SYN_RUNS_EN
        if not any(key in p for p in check({key: value})):
            problems.append(f"a fixed period in {key} is not refused while the cleanup is not live")
        if any(key in p for p in check({key: value, "RETENTION_CLEANUP_LIVE": "true"})):
            problems.append(f"{key} is refused although the cleanup is recorded live")
    assert not problems, _report("R19: the UL8 fixed-period rule covers the dormant retention keys:", problems)


# =============================================================================================
# R13 -- the switch date
# =============================================================================================

def test_r13_switch_date_equals_effective_date_and_terms_version():
    """RED, amended V3C (EK11; node id kept, V3C-2 OQ-5): AI_SWITCH_DATE (EN "<Month> <D>, <YYYY>") and
    AI_SWITCH_DATE_AR ("<D> <Gulf month> <YYYY>") parse to the same ISO date as the T6 effective-date anchors
    and consent_service.TERMS_VERSION; the placeholder now dates the NOTICE only: the notice line of the
    privacy policy and of the Terms (EN and AR) carries the value, privacy s4 and s5 carry no date at all,
    and the value occurs in each document only on its effective-date line and its notice line."""
    ph = _placeholders()
    tv = _terms_version()
    en_value, ar_value = ph.get("AI_SWITCH_DATE"), ph.get("AI_SWITCH_DATE_AR")
    problems = []
    if tv is None:
        problems.append("consent_service.TERMS_VERSION not readable")
    en_iso = _en_date(en_value) if isinstance(en_value, str) else None
    ar_iso = _ar_date(ar_value) if isinstance(ar_value, str) else None
    if en_iso is None or en_iso != tv:
        problems.append(f"AI_SWITCH_DATE {en_value!r} -> {en_iso} != TERMS_VERSION {tv}")
    if ar_iso is None or ar_iso != tv:
        problems.append(f"AI_SWITCH_DATE_AR -> {ar_iso} != TERMS_VERSION {tv}")
    for rel, parse in ((PRIVACY_EN, _en_date), (TERMS_EN, _en_date), (PRIVACY_AR, _ar_date), (TERMS_AR, _ar_date)):
        if parse(_read(rel)) != tv:
            problems.append(f"{rel}: the effective-date anchor differs from TERMS_VERSION")
    for rel, value, rx in ((PRIVACY_EN, en_value, EN_DATE), (TERMS_EN, en_value, EN_DATE),
                           (PRIVACY_AR, ar_value, AR_DATE), (TERMS_AR, ar_value, AR_DATE)):
        text = _read(rel) or ""
        dated = [line for line in text.split("\n") if isinstance(value, str) and value in line]
        notice = [line for line in dated if line.startswith("**")]
        if len(notice) != 1:
            problems.append(f"{rel}: the notice line does not carry the AI_SWITCH_DATE value once")
        if len(dated) != 2 or not isinstance(value, str) or text.count(value) != 2 or (notice and dated[1] != notice[0]):
            problems.append(f"{rel}: the date occurs on {len(dated)} lines (want the effective-date line, then the notice line)")
    for rel, rx in ((PRIVACY_EN, EN_DATE), (PRIVACY_AR, AR_DATE)):
        for number in ("4", "5"):
            if rx.findall(_section(_read(rel), number) or ""):
                problems.append(f"{rel} s{number} carries a date (nothing about OpenAI is dated, R-V3C-3)")
    assert not problems, _report("R13: AI_SWITCH_DATE dates the notice:", problems)


# =============================================================================================
# R14 / R15 -- consent v3 and onboarding copy (client sources read as text)
# =============================================================================================

def test_r14_consent_v3_version_copy_and_fence():
    """RED, amended V3C (EK12, PATH C): AI_CONSENT_VERSION 3 in aiConsent.ts and the jest setup mirror;
    aiConsent.body names both providers (EN: 'some or all' requests on OpenAI, R-S12-1); the EN body has five
    sentences and carries main's training sentence (TRAINING_CLAIM_EN) exactly once, directly after the
    transition sentence (it names OpenAI and 'some or all') and directly before the not-sent final sentence;
    the AR body carries main's AR sentence (the V3C fixture J8) once at the same index, is not the v2 text;
    the fence pins version 3 and the digest of the current copy."""
    problems = []
    ts = _read(AI_CONSENT_TS) or ""
    m = re.search(r"export\s+const\s+AI_CONSENT_VERSION\s*=\s*([0-9]+)\s*;", ts)
    if not m or m.group(1) != "3":
        problems.append(f"aiConsent.ts AI_CONSENT_VERSION is {m.group(1) if m else None} (want 3)")
    setup = _read(JEST_SETUP) or ""
    m = re.search(r"AI_CONSENT_VERSION:\s*([0-9]+)\s*,", setup)
    if not m or m.group(1) != "3":
        problems.append(f"the jest setup mirror is {m.group(1) if m else None} (want 3)")
    en, ar = _catalog(EN_CATALOG), _catalog(AR_CATALOG)
    body_en, body_ar = en.get("aiConsent.body") or "", ar.get("aiConsent.body") or ""
    for name in ("Anthropic", "OpenAI"):
        if name not in body_en:
            problems.append(f"EN consent body does not name {name}")
        if name not in body_ar:
            problems.append(f"AR consent body does not name {name}")
    if not re.search(r"\bsome or all\b", body_en):
        problems.append("EN consent body does not say 'some or all' requests may go to OpenAI (R-S12-1)")
    sentences = _sentences(body_en)
    if len(sentences) != 5:
        problems.append(f"EN consent body has {len(sentences)} sentences (want 5)")
    elif len(TRAINING_CLAIM_EN.findall(body_en)) != 1 or not TRAINING_CLAIM_EN.search(sentences[3]):
        problems.append("EN consent body does not carry main's training sentence once as sentence 4")
    elif not ("OpenAI" in sentences[2] and re.search(r"\bsome or all\b", sentences[2])):
        problems.append("the training sentence does not directly follow the transition sentence")
    if not sentences or not all(re.search(p, sentences[-1], re.I) for p in NOT_SENT_EN.values()):
        problems.append("EN consent body does not end with the not-sent sentence")
    j8 = _v3c_text("J8", "ar")
    ar_sentences = _sentences(body_ar)
    if j8 is None or body_ar.count(j8) != 1 or len(ar_sentences) != 5 or ar_sentences[3] != j8:
        problems.append("AR consent body does not carry main's AR training sentence once as sentence 4")
    if _sha(body_ar) == BASE_AR_CONSENT_BODY_SHA256:
        problems.append("AR consent body is the v2 text")
    fence = _read(FENCE_TEST) or ""
    v = re.search(r"PINNED\s*=\s*\{\s*version:\s*([0-9]+)", fence)
    s = re.search(r"sha256:\s*'([0-9a-f]{64})'", fence)
    parts = [en.get("aiConsent.title"), body_en, ar.get("aiConsent.title"), body_ar]
    digest = _sha("\n".join(p or "" for p in parts))
    if not v or v.group(1) != "3":
        problems.append(f"the fence pins version {v.group(1) if v else None} (want 3)")
    if not s or s.group(1) != digest:
        problems.append(f"the fence digest {s.group(1)[:8] if s else None} != the current copy {digest[:8]}")
    assert not problems, _report("R14: consent v3:", problems)


def _tsx_default(source, key):
    m = re.search(r"t\(\s*'" + re.escape(key) + r"'\s*,\s*\{\s*defaultValue:\s*(['\"])((?:\\.|(?!\1).)*)\1",
                  source or "", re.S)
    if not m:
        return None
    raw = m.group(2)
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda x: chr(int(x.group(1), 16)), raw).replace("\\'", "'").replace('\\"', '"')


def test_r15_onboarding_step5_names_the_ai_providers():
    """RED: onboarding Step 5 says what reaches the AI providers: EN heading names the AI providers (not
    'What reaches OpenAI'), the EN and AR bodies name Anthropic and OpenAI, the AR heading moved, and the
    Step05Trust.tsx defaultValues equal en.json."""
    en, ar = _catalog(EN_CATALOG), _catalog(AR_CATALOG)
    head_en, body_en = en.get("onboarding.s5.privacy_anon_head") or "", en.get("onboarding.s5.privacy_anon_body") or ""
    head_ar, body_ar = ar.get("onboarding.s5.privacy_anon_head") or "", ar.get("onboarding.s5.privacy_anon_body") or ""
    problems = []
    if head_en == "What reaches OpenAI" or not re.search(r"\bAI providers?\b", head_en):
        problems.append(f"EN heading {head_en!r} does not name the AI providers")
    if _sha(head_ar) == BASE_AR_ONB_HEAD_SHA256:
        problems.append("AR heading is the base 'What reaches OpenAI' text")
    for label, body in (("EN", body_en), ("AR", body_ar)):
        for name in ("Anthropic", "OpenAI"):
            if name not in body:
                problems.append(f"{label} body does not name {name}")
    src = _read(STEP05)
    for key, want in (("onboarding.s5.privacy_anon_head", head_en), ("onboarding.s5.privacy_anon_body", body_en)):
        got = _tsx_default(src, key)
        if got != want:
            problems.append(f"Step05Trust.tsx defaultValue for {key} is {got!r} (want en.json {want!r})")
    assert not problems, _report("R15: onboarding Step 5 copy:", problems)


# =============================================================================================
# R16 -- OpenAI census (R-S12-7)
# =============================================================================================

# V3C EK13: privacy s3 is admitted for main's restored s3.6 legal-basis bullet only (checked by exact text in R16).
OPENAI_SECTIONS = {PRIVACY_EN: {"2", "3", "4", "5"}, PRIVACY_AR: {"2", "3", "4", "5"}, TERMS_EN: {"8", "13"}, TERMS_AR: {"8", "13"}}
OPENAI_SENTENCE_CLASSES_EN = (
    ("dual-provider / transition (names Anthropic)", r"\bAnthropic\b"),
    ("the programme (present, scoped; V3C EK13)", r"(?i)\bdata[- ]sharing programme\b|\bthis sharing\b"),
    ("the carve-out (main's form; V3C EK13)", r"\bExcept as section 4 describes for OpenAI\b"),
    ("carve-out / deletion (data shared with OpenAI)", r"(?i)\bshared with OpenAI\b"),
    ("OpenAI's own retention and no-training facts", r"(?i)\babuse-monitoring\b|\bdoes not use\b|\bno longer\b"),
)


def _sections_of(text):
    out, cur, buf = {}, None, []
    for line in (text or "").split("\n"):
        m = re.match(r"^##(?!#)[ \t]+(.+)$", line)
        if m:
            if cur is not None:
                out[cur] = "\n".join(buf)
            cur, buf = _section_no(m.group(1)), [line]
            continue
        if cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf)
    return out


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r16_openai_census(lang):
    """RED, amended V3C (EK13, PATH C): R-S12-7 -- 'OpenAI' appears only in privacy s2 / s3 / s4 / s5 and Terms
    s8 / s13; in privacy s3 ONLY inside main's restored legal-basis bullet of s3.6 (the V3C fixture B1, once;
    never in s3.2, s3.3 or s8); EN sentences only of the allowed classes (dual-provider, transition, the
    programme in the present tense (scoped), main's carve-out, deletion, OpenAI's own retention, and the
    adapted applies sentence of s4 by its exact text), and every landing region names OpenAI exactly as often
    as its source."""
    docs = (PRIVACY_EN, TERMS_EN) if lang == "en" else (PRIVACY_AR, TERMS_AR)
    problems = []
    b1, applies = _v3c_text("B1", lang), _v3c_text("C2", lang, "ruled")
    if b1 is None or applies is None:
        problems.append("the V3C fixture lacks B1 / C2")
    for rel in docs:
        text = _read(rel) or ""
        for number, body in _sections_of(text).items():
            n = body.count("OpenAI")
            if n and number not in OPENAI_SECTIONS[rel]:
                problems.append(f"{rel} s{number} names OpenAI {n} times (allowed only in {sorted(OPENAI_SECTIONS[rel])})")
            if n and number == "3" and rel in (PRIVACY_EN, PRIVACY_AR):
                s36 = _subsection(text, "3.6") or ""
                if b1 is None or body.count(b1) != 1 or s36.count(b1) != 1 or n != b1.count("OpenAI"):
                    problems.append(f"{rel} s3 names OpenAI outside the restored s3.6 legal-basis bullet")
                continue
            if n and lang == "en" and number in OPENAI_SECTIONS[rel]:
                for sentence in _sentences(body):
                    if "OpenAI" not in sentence:
                        continue
                    if number == "4" and applies and " ".join(sentence.split()) == " ".join(applies.split()):
                        continue
                    if not any(re.search(p, sentence) for _, p in OPENAI_SENTENCE_CLASSES_EN):
                        problems.append(f"{rel} s{number}: OpenAI outside the allowed sentences: {sentence[:90]!r}")
        region = _region(_read(PAGE_OF[rel]))
        if region is None or region.count("OpenAI") != text.count("OpenAI"):
            problems.append(f"{PAGE_OF[rel]}: the region names OpenAI {None if region is None else region.count('OpenAI')} times, the source {text.count('OpenAI')}")
    assert not problems, _report(f"R16 ({lang}): the OpenAI census:", problems)


# =============================================================================================
# R17 -- privacy s14 (R-S12-10 as amended by R-S08-3)
# =============================================================================================

@pytest.mark.parametrize("lang", ["en", "ar"])
def test_r17_privacy_s14_ai_permission_and_device_identifiers(lang):
    """RED: privacy s14 keeps 'deleting your account removes the AI permission record', has NO
    device-level consent copy (R-S08-3), and describes the device identifiers as re-ruled on 2026-10-29
    (RULINGS_FIX1_S81_12 F1-2; this row amended as EK2 in fix round 2, F2-1): two random identifiers
    stored securely (a random install identifier and a second random identifier), and the older form of
    the install identifier sent only until 31 March 2027, after which only the random install identifier
    is used; 'device properties' (a fingerprinting description) is forbidden."""
    s14 = _section(_read(PRIVACY_EN if lang == "en" else PRIVACY_AR), "14") or ""
    problems = []
    if lang == "en":
        for label, pattern in S14_EN_REQUIRED.items():
            if not re.search(pattern, s14):
                problems.append(f"s14 lacks {label}")
        for label, pattern in S14_EN_FORBIDDEN.items():
            if re.search(pattern, s14):
                problems.append(f"s14 carries {label}")
        older = [s for s in _sentences(s14) if re.search(r"(?i)older form of the install identifier", s)]
        if not older or not all(re.search(p, older[0]) for p in (r"\bUntil 31 March 2027\b",
                                                                 r"\bafter that date only the random install identifier is used\b")):
            problems.append("the older-form sentence does not end with the 31 March 2027 cutoff (F1-2; R-S08-4)")
    else:
        if S14_TWO_IDS_AR in s14:
            problems.append("AR s14 still says two random device identifiers")
        if S14_AI_RECORD_AR not in s14:
            problems.append("AR s14 lost the AI permission record removal")
    assert not problems, _report(f"R17 ({lang}): privacy section 14:", problems)


# =============================================================================================
# H1 / H1b -- the hold (R-S12-6)
# =============================================================================================

def _h1_problems(root):
    """Problems that keep the PR held: the window record vs TERMS_VERSION vs AI_SWITCH_DATE(_AR)."""
    problems = []
    raw = _read(WINDOW, root)
    if raw is None:
        return [f"{WINDOW} is missing (the window record: the window date, V3C EK14)"]
    try:
        record = json.loads(raw)
    except ValueError:
        return [f"{WINDOW} is not JSON"]
    value = record.get("window_date") if isinstance(record, dict) else None
    if not (isinstance(value, str) and ISO_DATE.match(value)):
        problems.append(f"{WINDOW}: window_date is {value!r} (the window date the owner approves, ISO)")
    tv = _terms_version(root)
    if tv is None:
        problems.append("TERMS_VERSION not readable")
    elif value != tv:
        problems.append(f"the window date {value!r} != TERMS_VERSION {tv!r}")
    ph = (_data(root).get("placeholders") or {})
    en_iso = _en_date(ph.get("AI_SWITCH_DATE")) if isinstance(ph.get("AI_SWITCH_DATE"), str) else None
    ar_iso = _ar_date(ph.get("AI_SWITCH_DATE_AR")) if isinstance(ph.get("AI_SWITCH_DATE_AR"), str) else None
    if en_iso != value or ar_iso != value:
        problems.append(f"AI_SWITCH_DATE {en_iso} / AI_SWITCH_DATE_AR {ar_iso} != the window date {value!r}")
    return problems


def test_h1_merge_window_recorded():
    """HOLD, RED BY DESIGN until the window commit records the WINDOW DATE (PATH C, RULINGS_ITEM26_S81_12
    IT26-9 (c); V3C EK14): the orchestrator records the window date the owner approves in
    tests/fixtures/legal_v3_window.json ({"window_date": "<YYYY-MM-DD>"}) equal to TERMS_VERSION and
    AI_SWITCH_DATE(_AR) (re-date recipe G). The PR does not merge while this row is red."""
    problems = _h1_problems(REPO)
    assert not problems, _report("H1 (hold): the window date is not recorded:", problems)


def _h1_tree(root, record, en, ar, tv):
    root = Path(root)
    (root / "tests/fixtures").mkdir(parents=True, exist_ok=True)
    (root / "app/services").mkdir(parents=True, exist_ok=True)
    (root / CONSENT_SERVICE).write_text(f'TERMS_VERSION = "{tv}"\n', encoding="utf-8")
    (root / FILL_IN).write_text(json.dumps({"placeholders": {"AI_SWITCH_DATE": en, "AI_SWITCH_DATE_AR": ar}}), encoding="utf-8")
    if record is not ...:
        (root / WINDOW).write_text(json.dumps({"_comment": "synthetic", "window_date": record}), encoding="utf-8")


def test_h1b_hold_logic_proven_on_temp_copies(tmp_path):
    """PIN: the H1 comparison on synthetic trees -- equal record / TERMS_VERSION / AI_SWITCH_DATE(_AR) is
    clean; the record, the EN date or the AR date mutated alone is a problem; a missing, non-JSON or null
    record is a problem (never an exception)."""
    ar_nov2 = "2 " + GULF_MONTHS_AR[10] + " 2026"
    cases = {
        "equal": ("2026-11-02", "November 2, 2026", ar_nov2, "2026-11-02", False),
        "record mutated": ("2026-11-03", "November 2, 2026", ar_nov2, "2026-11-02", True),
        "EN switch date mutated": ("2026-11-02", "November 3, 2026", ar_nov2, "2026-11-02", True),
        "AR switch date mutated": ("2026-11-02", "November 2, 2026", "3 " + GULF_MONTHS_AR[10] + " 2026", "2026-11-02", True),
        "TERMS_VERSION mutated": ("2026-11-02", "November 2, 2026", ar_nov2, "2026-11-04", True),
        "record null": (None, "November 2, 2026", ar_nov2, "2026-11-02", True),
        "record missing": (..., "November 2, 2026", ar_nov2, "2026-11-02", True),
    }
    wrong = []
    for label, (record, en, ar, tv, expect_problem) in cases.items():
        root = tmp_path / re.sub(r"\W+", "_", label)
        _h1_tree(root, record, en, ar, tv)
        got = _h1_problems(root)
        if bool(got) != expect_problem:
            wrong.append(f"{label}: problems={got}")
    root = tmp_path / "not_json"
    _h1_tree(root, ..., "November 2, 2026", ar_nov2, "2026-11-02")
    (root / WINDOW).write_text("{not json", encoding="utf-8")
    if not _h1_problems(root):
        wrong.append("non-JSON record: no problem")
    assert not wrong, _report("H1b: the hold comparison:", wrong)


# =============================================================================================
# PINs
# =============================================================================================

def test_p1_fill_in_idempotent_and_landing_regions_current(capsys):
    """PIN: the committed data re-fills to the committed sources (dry run rc 0, nothing to write) and the
    six landing regions are current (render_legal_landing.py --check rc 0)."""
    fill = _load(FILL_SCRIPT, "_s81_12_fill_in_p1")
    rc = fill.main(["--repo-root", str(REPO), "--dry-run"])
    out = capsys.readouterr()
    assert rc == 0 and "would write" not in out.out, f"fill_in_legal --dry-run rc {rc}: {_esc(out.out + out.err)[:400]}"
    renderer = _load(RENDERER, "_s81_12_renderer_p1")
    rc = renderer.main(["--check", "--repo-root", str(REPO)])
    out = capsys.readouterr()
    assert rc == 0, f"render_legal_landing --check rc {rc}: {_esc(out.out + out.err)[:400]}"


def test_p3_i18n_key_sets_equal_and_unchanged():
    """PIN: R-S12-8 -- the EN and AR catalogs have equal key sets and this unit adds or removes no key.
    The recorded set is the base (98d85433): after a rebase onto a main whose catalogs gained keys (S81-08,
    which merges first) re-record BASE_I18N_KEY_COUNT / BASE_I18N_NAMESET_SHA256 from that main with
    sha256('\\n'.join(sorted(keys))), never from this unit's own catalogs."""
    en, ar = _catalog(EN_CATALOG), _catalog(AR_CATALOG)
    assert set(en) == set(ar), f"EN-only {sorted(set(en) - set(ar))[:5]} AR-only {sorted(set(ar) - set(en))[:5]}"
    keys = sorted(en)
    assert (len(keys), _sha("\n".join(keys))) == (BASE_I18N_KEY_COUNT, BASE_I18N_NAMESET_SHA256), (
        f"the key set changed: {len(keys)} keys, sha {_sha(chr(10).join(keys))[:12]}"
    )
    for key in ("aiConsent.title", "aiConsent.body", "onboarding.s5.privacy_anon_head", "onboarding.s5.privacy_anon_body"):
        assert key in en and key in ar, f"{key} missing"


def test_p4_no_qarenbot_in_the_legal_texts():
    """PIN: R-S12-2 -- the crawler is never named with the old brand token: 'QarenBot' is absent from the six
    sources, the six pages, the pre-fill snapshot and the variants (T3 and landing.brand stay unedited)."""
    rels = SOURCES + PAGES + tuple(f"{PREFILL}/{Path(r).name}" for r in SOURCES) + (VARIANTS,)
    hits = [rel for rel in rels if re.search(r"(?i)qarenbot", _visible(rel) or "")]
    assert not hits, f"QarenBot named in {hits}"


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_p5_transfers_section_no_stronger_than_today(lang):
    """PIN: R-S12-3 / LR3 -- privacy s7 (countries + the TRANSFER_BASIS clause) is byte-identical to the base
    and the TRANSFER_BASIS variants are unchanged: no PDPL article sentence, no adequacy claim, no vendor
    name (Anthropic included) until counsel answers (a counsel re-fill re-pins this row)."""
    s7 = _section(_read(PRIVACY_EN if lang == "en" else PRIVACY_AR), "7") or ""
    problems = []
    if _sha(s7) != BASE_S7_SHA256[lang]:
        problems.append("privacy s7 changed")
    for name in ("Anthropic", "OpenAI", "Law No. 30", "adequa"):
        if name in s7:
            problems.append(f"privacy s7 names {name!r}")
    clause = ((_variants().get("clauses") or {}).get("TRANSFER_BASIS")) or {}
    if _jsha(clause) != BASE_TRANSFER_BASIS_SHA256:
        problems.append("the TRANSFER_BASIS variants changed")
    assert not problems, _report(f"P5 ({lang}): transfers no stronger than today:", problems)


def test_p6_deletion_section_and_privacy_s3_5_not_edited_here():
    """PIN: R-S12-9 -- the DELETION_SECTION variants (043 and old, privacy and Terms, EN and AR) and privacy
    s3.5 are not edited by this unit (S81-09 owns the device-counter wording there)."""
    clause = ((_variants().get("clauses") or {}).get("DELETION_SECTION")) or {}
    problems = []
    if _jsha(clause) != BASE_DELETION_SECTION_SHA256:
        problems.append("the DELETION_SECTION variants changed")
    for lang, rel in (("en", PRIVACY_EN), ("ar", PRIVACY_AR)):
        if _sha(_subsection(_read(rel), "3.5") or "") != BASE_S3_5_SHA256[lang]:
            problems.append(f"{rel} s3.5 changed")
    assert not problems, _report("P6: not edited here:", problems)


def test_p7_openai_30_day_sentence_rests_on_the_store_false_pin():
    """PIN: R-S12-17 -- privacy s4 keeps OpenAI's 'abuse-monitoring logs for up to 30 days' sentence (EN; AR
    names OpenAI and 30), and its only evidence is the U3c pin: guarded_llm_create sets kwargs['store'] =
    False and tests/test_u3c_store_false_pin.py exists."""
    problems = []
    s4 = _section(_read(PRIVACY_EN), "4") or ""
    if not any("OpenAI" in s and "abuse-monitoring logs for up to 30 days" in s for s in _sentences(s4)):
        problems.append("privacy s4 lost OpenAI's 'abuse-monitoring logs for up to 30 days' sentence")
    s4_ar = _section(_read(PRIVACY_AR), "4") or ""
    if "OpenAI" not in s4_ar or not re.search(r"(?<![0-9])30(?![0-9])", s4_ar):
        problems.append("AR privacy s4 lost OpenAI's 30-day sentence")
    tree = ast.parse(_read(STORE_PIN_SOURCE) or "")
    pinned = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "guarded_llm_create":
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Assign) and isinstance(sub.value, ast.Constant) and sub.value.value is False
                        and any(isinstance(t, ast.Subscript) and ast.unparse(t) == "kwargs['store']" for t in sub.targets)):
                    pinned = True
    if not pinned:
        problems.append(f"{STORE_PIN_SOURCE}: guarded_llm_create no longer sets kwargs['store'] = False")
    if not (REPO / U3C_PIN).is_file():
        problems.append(f"{U3C_PIN} is missing")
    assert not problems, _report("P7: the OpenAI 30-day sentence and its evidence:", problems)
