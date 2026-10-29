"""S81-12 LEGAL-V3: the gate rows of fix round 1 (RULINGS_FIX1_S81_12 F1-3 (a)-(h)), kept in their own
file so the frozen RED file (tests/test_s81_12_legal_v3.py) keeps its sha256 (the S81-06 gate-rows
pattern). They reuse the RED file's hermetic helpers and read the RENDERED app/legal sources (EN + AR);
row (b) and row (h) also read the landing regions.

They pin the facts both adversaries showed unpinned (S81_12_ADV1_correctness M-2, m4, m5, m6 and
S81_12_ADV1_legal MAJ-L4; the surviving mutants X1 X2 X4 X8 X9 X10 X12, M6s, L10m) and the dated
publication notice of F1-5:

  (a) privacy s4: OpenAI's no-training sentence since the switch, EN verbatim + its AR twin   (X1, L10m)
  (b) no 'OpenAI may use ... to train' (EN, AR) in the sources or the landing regions outside the ONE
      dated history sentence of privacy s4                                                        (X10)
  (c) privacy s4: the pre-switch carve-out sentence, EN verbatim + its AR twin                    (X4)
  (d) privacy s4: the Anthropic no-training sentence UNQUALIFIED (EN) and its AR twin        (X12, X9)
  (e) privacy s4: 'up to 30 days' inside the Anthropic retention sentence, EN + AR               (X8)
  (f) privacy s2: the dual-provider sentence carries 'including photos', EN + AR                 (X2)
  (g) Terms s7: the 'such a link is marked "Sponsored".' clause, EN + AR                        (M6s)
  (h) the dated 'Changes on <AI_SWITCH_DATE>' notice at the top of the privacy policy and of the
      Terms (F1-5), EN verbatim + AR by its elements, dated from the fill-in data (the window commit's
      re-date moves it with AI_SWITCH_DATE / _AR), present in the landing regions too

Each row fails on its mutant (applied through the U8 machinery on byte copies: snapshot edit ->
restore -> scripts/fill_in_legal.py) with an AssertionError; the mutation table is in the fix-round
report. Every row reports a missing file, section or value as a problem, never an exception.
Pure ASCII: every Arabic string is a unicode escape (the AR literals are the texts the machinery
renders; the drafts are [NATIVE READ]).
"""
from __future__ import annotations

import re

import pytest

from tests.test_legal_docs_u8 import D3_HISTORY_AR, D3_HISTORY_EN
from tests.test_s81_12_legal_v3 import (
    AR_LETTER,
    PAGE_OF,
    PRIVACY_AR,
    PRIVACY_EN,
    TERMS_AR,
    TERMS_EN,
    _placeholders,
    _read,
    _region,
    _report,
    _section,
    _sentences,
)

LANGS = ("en", "ar")

# --- (a) OpenAI's no-training sentence since the switch (privacy s4) -------------------------------
SINCE_EN = "Since then, OpenAI does not use the data we send it to train its models"
SINCE_AR = (
    "\u0648\u0645\u0646\u0630 \u0630\u0644\u0643 \u0627\u0644\u062a\u0627\u0631\u064a\u062e \u0644\u0627 "
    "\u062a\u0633\u062a\u062e\u062f\u0645 OpenAI \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a "
    "\u0627\u0644\u062a\u064a \u0646\u0631\u0633\u0644\u0647\u0627 \u0625\u0644\u064a\u0647\u0627 "
    "\u0644\u062a\u062f\u0631\u064a\u0628 \u0646\u0645\u0627\u0630\u062c\u0647\u0627"
)
# --- (b) a present or future permission to use the data for training ------------------------------
TRAIN_EN = re.compile(r"(?i)\btrain")
PERMIT_EN = re.compile(
    r"(?i)\b(?:may|can|might|will|shall|could\s+now)\s+(?:also\s+|still\s+|now\s+)?use\b"
    r"|\bOpenAI\s+(?:also\s+|still\s+|now\s+)?uses\b"
    r"|\b(?:is|are)\s+(?:allowed|permitted|free)\s+to\s+use\b"
)
TRAIN_AR = "\u062a\u062f\u0631\u064a\u0628"  # training (in li-tadrib, wa-tadribiha)
USE_AR = "\u062a\u0633\u062a\u062e\u062f\u0645"  # (she) uses
USE_NEGATIONS_AR = ("\u0644\u0627 ", "\u0644\u0645 ")  # la, lam + space: does not / did not use
PERMIT_AR = re.compile(
    "(?<!" + AR_LETTER + ")(?:\u064a\u062c\u0648\u0632|\u064a\u0645\u0643\u0646|\u062a\u0633\u062a\u0637\u064a\u0639"
    "|\u0633\u062a\u0633\u062a\u062e\u062f\u0645)"  # it is permitted, it can, it is able, it will use
)
# --- (c) the pre-switch carve-out (privacy s4) -------------------------------------------------------
CARVE_EN = "Data shared with OpenAI under the programme before that date remains governed by OpenAI's terms."
CARVE_AR = (
    "\u0648\u062a\u0638\u0644 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u062a\u064a "
    "\u0634\u0648\u0631\u0643\u062a \u0645\u0639 OpenAI \u0636\u0645\u0646 \u0647\u0630\u0627 "
    "\u0627\u0644\u0628\u0631\u0646\u0627\u0645\u062c \u0642\u0628\u0644 \u0630\u0644\u0643 "
    "\u0627\u0644\u062a\u0627\u0631\u064a\u062e \u062e\u0627\u0636\u0639\u0629 \u0644\u0634\u0631\u0648\u0637 OpenAI."
)
# --- (d) the Anthropic no-training sentence (privacy s4) --------------------------------------------
ANTH_NO_TRAIN_EN = re.compile(r"\bdoes not use that information to train its models\b")
QUALIFIERS_EN = re.compile(
    r"(?i)\b(?:unless|except|excepting|other than|provided that|providing that|save that|subject to|but may)\b"
)
ANTH_NO_TRAIN_AR = (
    "\u0648\u0644\u0627 \u062a\u0633\u062a\u062e\u062f\u0645 \u0647\u0630\u0647 \u0627\u0644\u0645\u0639\u0644\u0648\u0645\u0627\u062a "
    "\u0644\u062a\u062f\u0631\u064a\u0628 \u0646\u0645\u0627\u0630\u062c\u0647\u0627"
)
QUALIFIERS_AR = re.compile(
    "(?<!" + AR_LETTER + ")(?:\u0645\u0627 \u0644\u0645|\u0625\u0644\u0627|\u0628\u0627\u0633\u062a\u062b\u0646\u0627\u0621"
    "|\u0634\u0631\u064a\u0637\u0629|\u0628\u0634\u0631\u0637|\u0639\u062f\u0627|\u0645\u0627 \u0639\u062f\u0627)(?!" + AR_LETTER + ")"
)  # unless, except, except for, provided that, on condition, apart from
# --- (e) the Anthropic retention sentence (privacy s4) ----------------------------------------------
KEEPS_EN = re.compile(r"(?i)\bkeeps?\b|\bretains?\b")
KEEPS_AR = "\u062a\u062d\u062a\u0641\u0638"  # (she) keeps
UP_TO_30_AR = re.compile("\u062a\u0635\u0644 \u0625\u0644\u0649 30(?![0-9])")  # up to 30
UP_TO_29_AR = re.compile("\u062a\u0635\u0644 \u0625\u0644\u0649 29(?![0-9])")  # up to 29
# --- (f) 'including photos' in the dual-provider sentence (privacy s2) ------------------------------
SOME_OR_ALL_EN = "some or all requests"
PHOTOS_EN = "including photos"
SOME_OR_ALL_AR = "\u0628\u0639\u0636 \u0627\u0644\u0637\u0644\u0628\u0627\u062a \u0623\u0648 \u062c\u0645\u064a\u0639\u0647\u0627"
PHOTOS_AR = "\u0628\u0645\u0627 \u0641\u064a\u0647\u0627 \u0627\u0644\u0635\u0648\u0631"
# --- (g) the Sponsored labelling clause (Terms s7) --------------------------------------------------
SPONSORED_CLAUSE_EN = 'such a link is marked "Sponsored".'
SPONSORED_CLAUSE_AR = (
    "\u0648\u064a\u062d\u0645\u0644 \u0647\u0630\u0627 \u0627\u0644\u0631\u0627\u0628\u0637 \u0639\u0644\u0627\u0645\u0629 "
    "\u00ab\u0645\u0645\u0648\u0651\u0644\u00bb."
)
# --- (h) the dated publication notice (F1-5; privacy s15 / Terms s14 'tell you ... when we publish it') --
NOTICE_EN = {
    PRIVACY_EN: (
        "**Changes on {date}:** we added Anthropic as one of our AI providers (section 4), our part in "
        "OpenAI's data-sharing programme ended on that date (section 4), and the App will ask again for your "
        "permission to send your requests to our AI providers."
    ),
    TERMS_EN: (
        "**Changes on {date}:** we added Anthropic as one of our AI providers (section 8), our part in "
        "OpenAI's data-sharing programme ended on that date (section 4 of our Privacy Policy), and the App "
        "will ask again for your permission to send your requests to our AI providers."
    ),
}
NOTICE_HEAD_AR = "**\u0627\u0644\u062a\u063a\u064a\u064a\u0631\u0627\u062a \u0641\u064a {date}:**"  # Changes on <date>:
NOTICE_ELEMENTS_AR = {
    "Anthropic": "Anthropic",
    "OpenAI": "OpenAI",
    "the data-sharing programme": "\u0628\u0631\u0646\u0627\u0645\u062c \u0645\u0634\u0627\u0631\u0643\u0629 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a",
    "our part ended": "\u0627\u0646\u062a\u0647\u062a \u0645\u0634\u0627\u0631\u0643\u062a\u0646\u0627",
    "on that date": "\u0641\u064a \u0630\u0644\u0643 \u0627\u0644\u062a\u0627\u0631\u064a\u062e",
    "your permission again": "\u0625\u0630\u0646\u0643 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649",
}


def _docs(lang):
    return (PRIVACY_EN, TERMS_EN) if lang == "en" else (PRIVACY_AR, TERMS_AR)


def _switch_date(lang):
    value = _placeholders().get("AI_SWITCH_DATE_AR" if lang == "ar" else "AI_SWITCH_DATE")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _history_sentence(lang):
    date = _switch_date(lang)
    if date is None:
        return None
    return (D3_HISTORY_AR if lang == "ar" else D3_HISTORY_EN).format(date=date)


def _front_matter(text):
    """The lines before the first level-2 heading (title, brand, effective date, the notice), or None."""
    if text is None:
        return None
    lines = []
    for line in text.split("\n"):
        if re.match(r"^##(?!#)[ \t]", line):
            return "\n".join(lines)
        lines.append(line)
    return None


def _s4(lang):
    return _section(_read(PRIVACY_EN if lang == "en" else PRIVACY_AR), "4")


# =============================================================================================
# (a) -- OpenAI does not use the data to train its models since the switch (X1, L10m)
# =============================================================================================

@pytest.mark.parametrize("lang", LANGS)
def test_g_a_openai_no_training_since_the_switch(lang):
    """PIN: privacy s4 states, exactly once, that since the switch OpenAI does not use the data we send it
    to train its models (EN verbatim; the AR twin as the machinery renders it). This is the sentence that
    makes 'the programme ended' true for users (P7 / R-S12-17 lean on it)."""
    s4 = _s4(lang)
    want = SINCE_EN if lang == "en" else SINCE_AR
    problems = []
    if s4 is None:
        problems.append("privacy s4 missing")
    elif s4.count(want) != 1:
        problems.append(f"privacy s4 carries the OpenAI no-training sentence {s4.count(want)} times (want 1)")
    assert not problems, _report(f"G-a ({lang}): OpenAI's no-training sentence:", problems)


# =============================================================================================
# (b) -- no present or future permission for OpenAI to train on the data (X10)
# =============================================================================================

def _ar_affirmative_use(sentence):
    """True when the sentence carries an un-negated 'tastakhdim' (uses) or a permission verb."""
    if PERMIT_AR.search(sentence):
        return True
    start = 0
    while True:
        i = sentence.find(USE_AR, start)
        if i < 0:
            return False
        before = sentence[max(0, i - 3):i]
        prev_char = sentence[i - 1] if i > 0 else ""
        is_word_start = not re.match(AR_LETTER, prev_char) if prev_char else True
        if is_word_start and before not in USE_NEGATIONS_AR:
            return True
        start = i + len(USE_AR)


@pytest.mark.parametrize("lang", LANGS)
def test_g_b_no_openai_training_permission_outside_the_history_sentence(lang):
    """PIN: no sentence of the privacy policy or the Terms (sources and landing regions) that names OpenAI
    and training grants OpenAI a present or future use of the data ('OpenAI may use ... to train', EN; the
    AR 'qad tastakhdim' / an un-negated 'tastakhdim' / a permission verb), except the ONE dated history
    sentence of privacy s4 (allow-listed by its exact text, dated from the fill-in data)."""
    history = _history_sentence(lang)
    problems = [] if history else ["AI_SWITCH_DATE(_AR) is not recorded in the fill-in data"]
    for rel in _docs(lang):
        for where, text in ((rel, _read(rel)), (PAGE_OF[rel], _region(_read(PAGE_OF[rel])))):
            if text is None:
                problems.append(f"{where}: missing or no legal region")
                continue
            for sentence in _sentences(text):
                s = " ".join(sentence.split())
                if "OpenAI" not in s or (history and s == " ".join(history.split())):
                    continue
                if lang == "en" and TRAIN_EN.search(s) and PERMIT_EN.search(s):
                    problems.append(f"{where}: OpenAI may use the data to train: {s[:120]!r}")
                if lang == "ar" and TRAIN_AR in s and _ar_affirmative_use(s):
                    problems.append(f"{where}: an AR sentence lets OpenAI use the data for training: {s[:120]!r}")
    assert not problems, _report(f"G-b ({lang}): no OpenAI training permission:", problems)


# =============================================================================================
# (c) -- the pre-switch carve-out (X4)
# =============================================================================================

@pytest.mark.parametrize("lang", LANGS)
def test_g_c_pre_switch_carve_out_sentence(lang):
    """PIN: privacy s4 keeps, exactly once, the sentence that data shared with OpenAI under the programme
    before the switch date remains governed by OpenAI's terms (the s5 carve-out points at it)."""
    s4 = _s4(lang)
    want = CARVE_EN if lang == "en" else CARVE_AR
    problems = []
    if s4 is None:
        problems.append("privacy s4 missing")
    elif s4.count(want) != 1:
        problems.append(f"privacy s4 carries the pre-switch carve-out sentence {s4.count(want)} times (want 1)")
    assert not problems, _report(f"G-c ({lang}): the pre-switch carve-out:", problems)


# =============================================================================================
# (d) -- the Anthropic no-training sentence, unqualified (X12, X9)
# =============================================================================================

@pytest.mark.parametrize("lang", LANGS)
def test_g_d_anthropic_no_training_sentence_unqualified(lang):
    """PIN: privacy s4 has exactly one sentence naming Anthropic and training; it says Anthropic does not use
    that information to train its models (EN; the AR twin verbatim) and carries no qualifier (EN 'unless',
    'except', 'other than', 'provided that' ...; AR 'ma lam', 'illa', 'bi-stithna', 'sharitat' ...)."""
    s4 = _s4(lang)
    problems = []
    if s4 is None:
        problems.append("privacy s4 missing")
        s4 = ""
    if lang == "en":
        hits = [s for s in _sentences(s4) if "Anthropic" in s and TRAIN_EN.search(s)]
        qualifiers, ok = QUALIFIERS_EN, (lambda s: bool(ANTH_NO_TRAIN_EN.search(s)))
    else:
        hits = [s for s in _sentences(s4) if "Anthropic" in s and TRAIN_AR in s]
        qualifiers, ok = QUALIFIERS_AR, (lambda s: ANTH_NO_TRAIN_AR in s)
    if len(hits) != 1:
        problems.append(f"privacy s4 has {len(hits)} sentences naming Anthropic and training (want 1)")
    for sentence in hits:
        if not ok(sentence):
            problems.append(f"the Anthropic sentence does not say it does not use the data to train: {sentence[:120]!r}")
        found = qualifiers.search(sentence)
        if found:
            problems.append(f"the Anthropic no-training sentence is qualified by {found.group(0)!r}")
    assert not problems, _report(f"G-d ({lang}): Anthropic's no-training sentence:", problems)


# =============================================================================================
# (e) -- 'up to 30 days' in the Anthropic retention sentence (X8)
# =============================================================================================

@pytest.mark.parametrize("lang", LANGS)
def test_g_e_anthropic_retention_up_to_30_days(lang):
    """PIN: privacy s4 has exactly one sentence naming Anthropic and its retention ('keeps' / AR 'tahtafiz');
    that sentence carries 'up to 30 days' (API) and 'up to 29 days' (batches), EN and AR, so the AR '30'
    sits in the Anthropic sentence and not merely somewhere in s4 (OpenAI's 30 days is another sentence)."""
    s4 = _s4(lang)
    problems = []
    if s4 is None:
        problems.append("privacy s4 missing")
        s4 = ""
    if lang == "en":
        hits = [s for s in _sentences(s4) if "Anthropic" in s and KEEPS_EN.search(s)]
        checks = (("up to 30 days", lambda s: "up to 30 days" in s), ("up to 29 days", lambda s: "up to 29 days" in s))
    else:
        hits = [s for s in _sentences(s4) if "Anthropic" in s and KEEPS_AR in s]
        checks = (("up to 30 (days)", lambda s: bool(UP_TO_30_AR.search(s))), ("up to 29 (days)", lambda s: bool(UP_TO_29_AR.search(s))))
    if len(hits) != 1:
        problems.append(f"privacy s4 has {len(hits)} Anthropic retention sentences (want 1)")
    for sentence in hits:
        for label, check in checks:
            if not check(sentence):
                problems.append(f"the Anthropic retention sentence lacks {label}: {sentence[:120]!r}")
    assert not problems, _report(f"G-e ({lang}): Anthropic's retention period:", problems)


# =============================================================================================
# (f) -- 'including photos' in the privacy s2 dual-provider sentence (X2)
# =============================================================================================

@pytest.mark.parametrize("lang", LANGS)
def test_g_f_dual_provider_sentence_carries_including_photos(lang):
    """PIN: in privacy s2 the sentence that puts some or all requests on OpenAI until the move is complete
    names OpenAI and says 'including photos' (EN) / its AR twin; exactly one such sentence."""
    s2 = _section(_read(PRIVACY_EN if lang == "en" else PRIVACY_AR), "2")
    some, photos = (SOME_OR_ALL_EN, PHOTOS_EN) if lang == "en" else (SOME_OR_ALL_AR, PHOTOS_AR)
    problems = []
    if s2 is None:
        problems.append("privacy s2 missing")
        s2 = ""
    hits = [s for s in _sentences(s2) if some in s]
    if len(hits) != 1:
        problems.append(f"privacy s2 has {len(hits)} 'some or all requests' sentences (want 1)")
    for sentence in hits:
        if "OpenAI" not in sentence:
            problems.append("the 'some or all requests' sentence does not name OpenAI")
        if photos not in sentence:
            problems.append(f"the dual-provider sentence of privacy s2 lacks 'including photos': {sentence[:120]!r}")
    assert not problems, _report(f"G-f ({lang}): the dual-provider sentence of privacy s2:", problems)


# =============================================================================================
# (g) -- the Sponsored labelling clause of Terms s7 (M6s)
# =============================================================================================

@pytest.mark.parametrize("lang", LANGS)
def test_g_g_terms_s7_sponsored_label_clause(lang):
    """PIN: Terms s7 keeps, exactly once, the labelling commitment that a paid store link is marked
    'Sponsored' (EN 'such a link is marked "Sponsored".'; the AR twin), not only the word."""
    s7 = _section(_read(TERMS_EN if lang == "en" else TERMS_AR), "7")
    want = SPONSORED_CLAUSE_EN if lang == "en" else SPONSORED_CLAUSE_AR
    problems = []
    if s7 is None:
        problems.append("terms s7 missing")
    elif s7.count(want) != 1:
        problems.append(f"terms s7 carries the Sponsored labelling clause {s7.count(want)} times (want 1)")
    assert not problems, _report(f"G-g ({lang}): the Sponsored labelling clause:", problems)


# =============================================================================================
# (h) -- the dated publication notice at the top of both documents (F1-5)
# =============================================================================================

@pytest.mark.parametrize("lang", LANGS)
def test_g_h_dated_change_notice_at_the_top(lang):
    """RED until F1-5 lands: the privacy policy and the Terms carry, before section 1, ONE dated notice
    paragraph 'Changes on <AI_SWITCH_DATE>' (EN verbatim per document; AR: the dated head and its
    elements: Anthropic, OpenAI's data-sharing programme ended on that date, your permission again), dated
    from the fill-in data, and the landing regions carry it too (the 'on our website' notice of privacy
    s15 / Terms s14; the in-App notice is the consent v3 re-ask after the OTA)."""
    date = _switch_date(lang)
    problems = [] if date else ["AI_SWITCH_DATE(_AR) is not recorded in the fill-in data"]
    for rel in _docs(lang):
        front = _front_matter(_read(rel))
        if front is None:
            problems.append(f"{rel}: missing or no section heading")
            continue
        if lang == "en":
            want = NOTICE_EN[rel].format(date=date)
            lines = [line for line in front.split("\n") if line.startswith("**Changes on ")]
            if lines != [want]:
                problems.append(f"{rel}: the front matter carries {len(lines)} 'Changes on' notices, want exactly: {want[:90]!r}")
            visible = want.replace("**", "")
            region = _region(_read(PAGE_OF[rel]))
            if region is None or " ".join(visible.split()) not in " ".join(region.split()):
                problems.append(f"{PAGE_OF[rel]}: the landing region does not carry the dated notice")
        else:
            head = NOTICE_HEAD_AR.format(date=date)
            lines = [line for line in front.split("\n") if line.startswith(head)]
            if len(lines) != 1:
                problems.append(f"{rel}: the front matter carries {len(lines)} dated AR notices (want 1)")
            for line in lines:
                for label, needle in NOTICE_ELEMENTS_AR.items():
                    if needle not in line:
                        problems.append(f"{rel}: the AR notice lacks {label}")
            region = _region(_read(PAGE_OF[rel]))
            if region is None or head.replace("**", "") not in region:
                problems.append(f"{PAGE_OF[rel]}: the landing region does not carry the dated AR notice")
    assert not problems, _report(f"G-h ({lang}): the dated change notice:", problems)
