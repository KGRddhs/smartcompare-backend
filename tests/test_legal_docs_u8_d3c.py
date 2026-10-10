"""U8 fill-in prep (session 76): the third d3 fork, decision D3 = C (ruling OA2, 2026-10-08).

The owner kept OpenAI organisation data sharing ON for all comparisons, disclosed, with no
per-user switch (DECISIONS_ACCEPTED_2026-10-08: "D3=C"). The consent sheet on main already
says so (SmartCompareApp/src/i18n/en.json aiConsent.body and its AR twin, consent v2, U3b).
Ruling OA2 requires a third value of the fill-in's d3 answer whose privacy section 4
paragraph names OpenAI's data-sharing programme, says inputs AND outputs may be used to
identify usage patterns, measure model quality and inform the evaluation and training of its
models, says data shared this way is governed by OpenAI's terms rather than the 30-day
abuse-monitoring limit, and promises no opt-out.

RED at feature/s73-u8-legal 3533e860 (PR #330 merged with main a8f4552b): every node fails
because the C fork or the C enum value is missing; nothing here fails on an import or a
missing fixture (tests/fixtures/legal_d3c_u8.json is committed with this file). GREEN (session 76)
applied the fork (UG1) and appended (f)-(h); every node is green on the committed tree.

NODE MAP
  (a) test_d3c_a_variants_carry_en_and_ar_c                   forks.d3_training.en.C / ar.C exist
      test_d3c_a_c_text_restates_the_consent_sheet_sentence   EN + AR restate aiConsent.body verbatim
      test_d3c_a_c_text_is_locatable_by_the_fork_machinery    no substring collision with A, B, retention
  (b) test_d3c_b_fill_in_enum_accepts_c                       fill_in_legal.ENUM_ANSWERS + its schema
  (c) test_d3c_c_test_schema_accepts_c                        tests/test_legal_docs_u8.py data schema
      test_d3c_c_existing_t8_routes_c_to_its_own_rule         _d3 / D3_FORBIDDEN_* know "C"
  (d) test_d3c_d_dry_run_selects_the_c_paragraph              --dry-run on a complete temp copy, d3 C
  (e) test_d3c_e_t8_rule_en / test_d3c_e_t8_rule_ar          the T8 keyword rule for d3 = C
GREEN additions (session 76, rulings UG2, UG5, UG6; green after GREEN):
  (f) test_d3c_f_store_pin_guard_refuses_b_and_c_without_the_pin   d3 B / C need openai_store_pinned
  (g) test_d3c_g_withdraw_path_never_follows_a_sentence_preposition no ' in by ' / AR twin, s4 + s10
  (h) test_d3c_h_no_per_user_sharing_setting_is_claimed            s3.3 names notification settings only
FIX additions (session 76, ruling UG12; the owner: "comparison data and preference data, never personal";
FIX round 2 rulings UF3-UF8 after the final adversary):
  (i) test_d3c_i_terms_grant_the_licence_and_own_only_derived_data      terms s8 history + licence + derived data (UF6)
  (j) test_d3c_j_privacy_keeps_not_sold_and_adds_the_aggregated_sentence privacy s2 (UF7) + aggregated, s3.6, s9 (UF6)
  (k) test_d3c_k_personal_data_claim_scan_positive_control             the scan's EN + AR controls (P2b, P7: UF8)
      test_d3c_k_no_sentence_claims_ownership_or_sale_of_personal_data six sources, live and filled
  (l) test_d3c_l_deletion_path_names_the_controls_the_app_shows         UF8 path + the labels check
  (m) test_d3c_m_hosting_regions_clause_names_only_the_measured_roles    UF3 privacy s7 roles
  (n) test_d3c_n_providers_sentence_carves_out_openai[C|A]               UF4 + UF10 privacy s5 carve-out
FIX round 3 rulings UF10-UF13 after the final adversary 2: (j) gains the s3.6 OpenAI-programme purpose
(UF11); (k) gains the share verb for advertisers / data brokers / partners and "data ... about you" (UF13,
the adversary's probes X1 and X2); (n) matches the UF10 service-providers sentence and pins the sentence that
retailer websites and the sign-in providers Apple and Google act under their own terms (UF10).

THE T8 RULE FOR d3 = C (replaces, for C only, the D3 = A rule "none of opt out / Help improve
AI quality / Data Sharing Program"): privacy section 4 matches every pattern of
T8_C_REQUIRED_EN (case-insensitive) and none of T8_C_FORBIDDEN_EN; the AR half lives in the
fixture (t8_c_ar). Each rule node first proves the rule rejects the A and B texts.

Pure ASCII: Arabic lives in tests/fixtures/legal_d3c_u8.json (the GREEN additions use escapes); failure
messages escape it.
Hermetic: temp copies only; the dry-run writes nothing and never touches the checkout.
"""
import copy
import html
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VARIANTS = "scripts/legal_variants_u8.json"
FILL_SCRIPT = "scripts/fill_in_legal.py"
RENDERER = "scripts/render_legal_landing.py"
FILL_IN = "tests/fixtures/legal_fill_in_u8.json"
D3C_FIXTURE = "tests/fixtures/legal_d3c_u8.json"
# The six sources before the fill-in (pinned by test_polish_prefill_snapshot_tracks_the_documents).
PREFILL = "tests/fixtures/legal_prefill_u8"
U8_TESTS = "tests/test_legal_docs_u8.py"
EN_CATALOG = "SmartCompareApp/src/i18n/en.json"
AR_CATALOG = "SmartCompareApp/src/i18n/ar.json"
PRIVACY_EN = "app/legal/privacy_policy.md"
PRIVACY_AR = "app/legal/privacy_policy_ar.md"
SOURCES = (
    "app/legal/privacy_policy.md", "app/legal/terms_of_service.md", "app/legal/support_contact.md",
    "app/legal/privacy_policy_ar.md", "app/legal/terms_of_service_ar.md", "app/legal/support_contact_ar.md",
)
PAGES = (
    "landing/privacy.html", "landing/terms.html", "landing/support.html",
    "landing/ar/privacy.html", "landing/ar/terms.html", "landing/ar/support.html",
)

T8_C_REQUIRED_EN = {
    "names the programme": r"\bdata[- ]sharing program(?:me)?\b",
    "inputs": r"\binputs\b",
    "outputs": r"\boutputs\b",
    "usage patterns": r"\bidentify usage patterns\b",
    "model quality": r"\bmeasure model quality\b",
    "evaluation and training": r"\binform the evaluation and training of its models\b",
    "governed by OpenAI's terms": r"\bgoverned by OpenAI's terms\b",
    "not the 30-day abuse-monitoring limit": r"\brather than the 30-day abuse-monitoring limit\b",
}
T8_C_FORBIDDEN_EN = {
    "opt out": r"\bopt(?:s|ed|ing)?[\s-]+out\b",
    "Help improve AI quality": r"Help improve AI quality",
    "turn on": r"\bturn(?:s|ed|ing)?\s+(?:it\s+|this\s+|sharing\s+)?on\b",
    "turn off": r"\bturn(?:s|ed|ing)?\s+(?:it\s+|this\s+|sharing\s+)?off\b",
    "stop sharing": r"\bstop(?:s|ped|ping)?\s+(?:future\s+)?sharing\b",
}
# Sample phrases the existing T8 node's C entry must catch (EN, case-insensitive regex search).
FORBIDDEN_SAMPLES_EN = ("opt out", "Help improve AI quality", "turn on", "turn off")
# The EN consent-sheet clause the C paragraph restates verbatim.
CONSENT_TAIL_EN = re.compile(r"the outputs .*?of its models")
# Section 4 of a rendered page: from its h2 to the next h2.
RENDERED_SECTION_4 = re.compile(r"(?s)<h2\b[^>]*>\s*4\.(.*?)(?=<h2\b|\Z)")

# Synthetic complete answers for the temp-copy dry-run (never a real fact).
COMPLETE_ANSWERS = {
    "deletion_variant": "043",
    "territories": "gcc",
    "counsel_review": False,
    "d3": "C",
    "d5": "A",
    "trade_name": "",
    "minors_clause": True,
    "openai_store_pinned": True,
    "inapp_notif_clause": False,
}
COMPLETE_VALUES_EN = {
    "CONTROLLER_NAME": "Sample Publisher",
    "POSTAL_ADDRESS": "Building 1, Road 2, Block 3, Manama, Bahrain",
    "PRIVACY_EMAIL": "privacy@qaren.app",
    "SUPPORT_EMAIL": "support@qaren.app",
    "IP_OWNER": "the publisher",
    "GOVERNING_LAW": "the Kingdom of Bahrain",
    "WITHDRAW_PATH": "Profile, then Privacy",
    "SECURITY_LOG_RETENTION": "no fixed period",
    "ANON_LOG_RETENTION": "no fixed period",
    "HOSTING_REGIONS": "Ireland",
    "CONTROLLER_COUNTRY": "Bahrain",
    "RETENTION_CLEANUP_LIVE": "false",
    "REFERRAL_PUSH_DISPLAY_NAME_ONLY": "true",
}


def _read(rel, root=REPO):
    return (Path(root) / rel).read_text(encoding="utf-8")


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


def _fixture():
    return _json(D3C_FIXTURE)


def _d3_fork():
    return _json(VARIANTS)["forks"]["d3_training"]


def _c_text(lang):
    """The C variant text of the d3 fork, or pytest.fail naming the missing fork value."""
    table = _d3_fork().get(lang) or {}
    text = table.get("C")
    if not (isinstance(text, str) and text.strip()):
        pytest.fail(
            f"{VARIANTS}: forks.d3_training.{lang} has no non-empty 'C' variant "
            f"(keys {sorted(table)}); decision D3 = C / ruling OA2 needs the third fork value"
        )
    return text


def _section(text, number):
    match = re.search(r"(?ms)^## " + re.escape(str(number)) + r"\.[^\n]*\n(.*?)(?=^## |\Z)", text)
    return match.group(1) if match else None


def _rule_problems(text, required, forbidden, flags):
    problems = [f"lacks {name!r}" for name, pattern in required.items() if not re.search(pattern, text, flags)]
    problems += [f"contains {name!r}" for name, pattern in forbidden.items() if re.search(pattern, text, flags)]
    return problems


def _ar_rule():
    rule = _fixture()["t8_c_ar"]
    return rule["required"], rule["forbidden"]


def _complete_data():
    data = _json(FILL_IN)
    data["placeholders"] = dict.fromkeys(data["placeholders"])  # synthetic values only, never the recorded ones
    data.update(copy.deepcopy(COMPLETE_ANSWERS))
    data["flags"] = dict.fromkeys(data["flags"], "off")
    data["placeholders"].update(COMPLETE_VALUES_EN)
    data["placeholders"].update(_fixture()["ar_values"])
    return data


# ---------------------------------------------------------------------------
# (a) the variants file carries the C fork value, EN and AR
# ---------------------------------------------------------------------------


def test_d3c_a_variants_carry_en_and_ar_c():
    """(a) forks.d3_training carries a non-empty en.C and ar.C next to A and B (OA2)."""
    fork = _d3_fork()
    assert fork.get("answer") == "d3" and "privacy" in fork.get("docs", ()), fork.get("docs")
    assert {"A", "B"} <= set(fork["en"]) and {"A", "B"} <= set(fork["ar"])
    missing = [lang for lang in ("en", "ar") if not (isinstance(fork[lang].get("C"), str) and fork[lang]["C"].strip())]
    assert not missing, f"{VARIANTS}: forks.d3_training has no non-empty 'C' variant for {missing} (D3 = C, OA2)"


def test_d3c_a_c_text_restates_the_consent_sheet_sentence():
    """(a) The C paragraph restates the consent-sheet purpose clause verbatim, EN and AR (OA2: the
    policy must match the sheet the user agreed to, AI_CONSENT_VERSION 2)."""
    en_body = json.loads(_read(EN_CATALOG))["aiConsent.body"]
    ar_body = json.loads(_read(AR_CATALOG))["aiConsent.body"]
    en_tail = CONSENT_TAIL_EN.search(en_body)
    assert en_tail, "aiConsent.body (en) no longer carries the OA2 sentence 'the outputs ... of its models'"
    tail = _fixture()["consent_tail_ar"]
    start = ar_body.find(tail["start"])
    end = ar_body.find(tail["end"], start)
    assert start >= 0 and end >= 0, "aiConsent.body (ar) no longer carries the OA2 clause (fixture anchors)"
    ar_tail = ar_body[start:end + len(tail["end"])]
    en_c, ar_c = _c_text("en"), _c_text("ar")
    assert en_tail.group(0) in en_c, f"en.C does not restate {en_tail.group(0)!r}"
    assert ar_tail in ar_c, f"ar.C does not restate {_esc(ar_tail)}"


def test_d3c_a_c_text_is_locatable_by_the_fork_machinery():
    """(a) fill_in_legal locates a fork by its variant text (exactly once): C may not contain, or be
    contained in, the A or B text or either openai_retention text."""
    variants = _json(VARIANTS)
    problems = []
    for lang in ("en", "ar"):
        c_text = _c_text(lang)
        others = {f"d3 {k}": variants["forks"]["d3_training"][lang][k] for k in ("A", "B")}
        others.update({f"retention {k}": t for k, t in variants["forks"]["openai_retention"][lang].items()})
        problems += [f"{lang}: C collides with {name}" for name, text in others.items() if text in c_text or c_text in text]
    assert not problems, problems


# ---------------------------------------------------------------------------
# (b) the fill-in script accepts d3 = "C"
# ---------------------------------------------------------------------------


def test_d3c_b_fill_in_enum_accepts_c():
    """(b) scripts/fill_in_legal.py: ENUM_ANSWERS['d3'] contains 'C' and its schema accepts d3 'C'."""
    fill = _load(FILL_SCRIPT, "_u8_d3c_fill_in_b")
    data = _json(FILL_IN)
    data["d3"] = "C"
    assert "C" in fill.ENUM_ANSWERS["d3"], f"fill_in_legal.ENUM_ANSWERS['d3'] = {fill.ENUM_ANSWERS['d3']!r} lacks 'C'"
    assert fill._schema_problems(data) == []


# ---------------------------------------------------------------------------
# (c) the data schema and the T8 routing in tests/test_legal_docs_u8.py know "C"
# ---------------------------------------------------------------------------


def test_d3c_c_test_schema_accepts_c():
    """(c) the fill-in data schema of tests/test_legal_docs_u8.py accepts d3 'C' (the fill-in commit's data)."""
    u8 = _load(U8_TESTS, "_u8_d3c_u8_tests_c1")
    data = _json(FILL_IN)
    data["d3"] = "C"
    assert "C" in u8._ENUM_ANSWERS["d3"], f"_ENUM_ANSWERS['d3'] = {u8._ENUM_ANSWERS['d3']!r} lacks 'C'"
    assert u8._fill_in_schema_problems(data) == []


def test_d3c_c_existing_t8_routes_c_to_its_own_rule():
    """(c) the existing T8 nodes must not judge a C fill-in by the A rule: today _d3() maps 'C' to 'A',
    and D3_FORBIDDEN_AR['A'] forbids the AR name of the programme the C text must name."""
    u8 = _load(U8_TESTS, "_u8_d3c_u8_tests_c2")
    assert u8._d3({"d3": "C"}) == "C", f"_d3({{'d3': 'C'}}) returns {u8._d3({'d3': 'C'})!r}"
    assert "C" in u8.D3_FORBIDDEN_EN and "C" in u8.D3_FORBIDDEN_AR
    uncaught = [s for s in FORBIDDEN_SAMPLES_EN if not any(re.search(p, s, re.I) for p in u8.D3_FORBIDDEN_EN["C"])]
    assert not uncaught, f"D3_FORBIDDEN_EN['C'] does not catch {uncaught}"
    name = _fixture()["ar_programme_name"]
    assert not [p for p in u8.D3_FORBIDDEN_AR["C"] if p in name or name in p], "D3_FORBIDDEN_AR['C'] forbids the programme name"
    assert not [p for p in u8.D3_FORBIDDEN_EN["C"] if re.search(p, _c_text("en"), re.I)]


# ---------------------------------------------------------------------------
# (d) a dry-run on a complete synthetic data file selects the C paragraph
# ---------------------------------------------------------------------------


def _copy_tree(root):
    """Pages and renderer from the checkout; the six sources from the pre-fill snapshot (so the
    temp-copy nodes hold after the fill-in commit too)."""
    for rel in SOURCES + PAGES + (RENDERER,):
        src = f"{PREFILL}/{Path(rel).name}" if rel in SOURCES else rel
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes((REPO / src).read_bytes())


def _snapshot(root):
    return {rel: (root / rel).read_bytes() for rel in SOURCES + PAGES}


def _dry_run(fill, root, data_path, data, capsys):
    data_path.write_text(json.dumps(data), encoding="utf-8")
    rc = fill.main(["--repo-root", str(root), "--data", str(data_path), "--variants", str(REPO / VARIANTS), "--dry-run"])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def test_d3c_d_dry_run_selects_the_c_paragraph(tmp_path, capsys):
    """(d) --dry-run on a temp copy with complete synthetic answers and d3 'C': rc 0, nothing written,
    privacy section 4 (EN and AR, markdown and rendered) carries the C paragraph instead of A, and no
    forbidden opt-out phrase. Control first: the same data with d3 'A' dry-runs rc 0, so only the C
    value can fail this node."""
    fill = _load(FILL_SCRIPT, "_u8_d3c_fill_in_d")
    root = tmp_path / "repo"
    _copy_tree(root)
    start = _snapshot(root)
    data = _complete_data()
    control = copy.deepcopy(data)
    control["d3"] = "A"
    rc, out, err = _dry_run(fill, root, tmp_path / "control.json", control, capsys)
    assert rc == 0 and "would write: app/legal/privacy_policy.md" in out, f"control (d3 A) rc {rc}: {err}"
    rc, out, err = _dry_run(fill, root, tmp_path / "data.json", data, capsys)
    assert rc == 0, f"dry-run with d3 'C' exits {rc}: {err.strip()}"
    assert _snapshot(root) == start, "the dry-run wrote to the temp copy"
    missing, outputs = fill.plan(root, data, _json(VARIANTS))
    assert missing == []
    renderer = _load(RENDERER, "_u8_d3c_renderer_d")
    a_texts = {lang: _d3_fork()[lang]["A"] for lang in ("en", "ar")}
    ar_required, ar_forbidden = _ar_rule()
    problems = []
    for lang, rel, required, forbidden, flags in (
        ("en", PRIVACY_EN, T8_C_REQUIRED_EN, T8_C_FORBIDDEN_EN, re.I),
        ("ar", PRIVACY_AR, ar_required, ar_forbidden, 0),
    ):
        text = outputs[rel][0].decode("utf-8").replace("\r\n", "\n")
        section = _section(text, 4) or ""
        rendered = html.unescape(renderer.render_markdown(text))
        match = RENDERED_SECTION_4.search(rendered)
        rendered_s4 = match.group(1) if match else ""
        c_text = _c_text(lang)
        if c_text not in section:
            problems.append(f"{rel} s4: the C paragraph is not selected")
        if a_texts[lang] in text:
            problems.append(f"{rel}: the A sentence is still present")
        if c_text not in rendered_s4:
            problems.append(f"{rel}: the rendered section 4 lacks the C paragraph")
        problems += [f"{rel} s4 {p}" for p in _rule_problems(section, required, forbidden, flags)]
        problems += [f"{rel} rendered s4 {p}" for p in _rule_problems(rendered_s4, {}, forbidden, flags)]
        # The opt-out families (not the turn on / turn off words, which the notification
        # sentences of section 11 may use) are absent from the whole rendered document.
        whole = {k: p for k, p in forbidden.items() if not k.startswith("turn")}
        problems += [f"{rel} rendered document {p}" for p in _rule_problems(rendered, {}, whole, flags)]
    assert not problems, [_esc(p) for p in problems]


# ---------------------------------------------------------------------------
# (e) the T8 keyword rule for d3 = C
# ---------------------------------------------------------------------------


def test_d3c_e_t8_rule_en():
    """(e) EN: the C rule rejects the A and B texts (control), then the C text satisfies it."""
    fork = _d3_fork()["en"]
    assert _rule_problems(fork["A"], T8_C_REQUIRED_EN, T8_C_FORBIDDEN_EN, re.I), "rule accepts the A text"
    b_problems = _rule_problems(fork["B"], T8_C_REQUIRED_EN, T8_C_FORBIDDEN_EN, re.I)
    assert any(p.startswith("contains") for p in b_problems), "rule does not catch the B opt-out promise"
    problems = _rule_problems(_c_text("en"), T8_C_REQUIRED_EN, T8_C_FORBIDDEN_EN, re.I)
    assert not problems, problems


def test_d3c_e_t8_rule_ar():
    """(e) AR: the C rule rejects the A and B texts (control), then the C text satisfies it."""
    required, forbidden = _ar_rule()
    fork = _d3_fork()["ar"]
    assert _rule_problems(fork["A"], required, forbidden, 0), "rule accepts the AR A text"
    b_problems = _rule_problems(fork["B"], required, forbidden, 0)
    assert any(p.startswith("contains") for p in b_problems), "rule does not catch the AR B opt-out promise"
    problems = _rule_problems(_c_text("ar"), required, forbidden, 0)
    assert not problems, problems


# ---------------------------------------------------------------------------
# GREEN additions (session 76): (f) UG5 store-pin guard, (g) UG2 withdrawal
# sentences, (h) UG6 no sharing setting
# ---------------------------------------------------------------------------

# UG5: the d3 values whose text points at "the 30-day ... limit below".
STORE_PIN_D3 = ("B", "C")
# UG2: a sentence preposition stranded in front of the WITHDRAW_PATH value's own one.
STRANDED_EN = (" in by ", " at by ", " in the App at by ", " from by ")
# AR: min (from), fi (in), ala (on), abr (through), each put in front of the AR value's first word.
AR_PREPOSITIONS = ("\u0645\u0646", "\u0641\u064a", "\u0639\u0644\u0649", "\u0639\u0628\u0631")
# The pre-UG2 sentence heads: followed by the committed value, the scan must catch them (control).
OLD_HEADS_EN = ("You can withdraw it at any time in ", "withdraw your permission for AI processing in the App at ")
OLD_HEADS_AR = (
    "\u0641\u064a \u0623\u064a \u0648\u0642\u062a \u0645\u0646 ",  # at any time from
    "\u0641\u064a \u0627\u0644\u062a\u0637\u0628\u064a\u0642 \u0645\u0646 ",  # in the App from
)
# UG6: privacy s3.3 names only the notification settings; the AR "your notification settings".
S33_EN = "your notification settings"
S33_AR = "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0625\u0634\u0639\u0627\u0631\u0627\u062a \u0644\u062f\u064a\u0643"
SHARING_SETTING_EN = r"(?i)\bsharing settings?\b|\bsettings? for sharing\b"
# AR "notifications and sharing" (the pre-UG6 s3.3 wording).
SHARING_SETTING_AR = "\u0627\u0644\u0625\u0634\u0639\u0627\u0631\u0627\u062a \u0648\u0627\u0644\u0645\u0634\u0627\u0631\u0643\u0629"


@pytest.mark.parametrize("d3", STORE_PIN_D3)
def test_d3c_f_store_pin_guard_refuses_b_and_c_without_the_pin(tmp_path, capsys, d3):
    """(f) UG5: d3 'B' or 'C' with openai_store_pinned false would publish "the 30-day ... limit below"
    with no 30-day sentence below it: the fill-in exits 3 with ONE line naming openai_store_pinned, in
    --dry-run and in a real run, and writes nothing. Control first: the same data with d3 'A' dry-runs
    rc 0 (the A text does not refer to the limit)."""
    fill = _load(FILL_SCRIPT, "_u8_d3c_fill_in_f")
    root = tmp_path / "repo"
    _copy_tree(root)
    start = _snapshot(root)
    data = _complete_data()
    data["openai_store_pinned"] = False
    control = copy.deepcopy(data)
    control["d3"] = "A"
    rc, _out, err = _dry_run(fill, root, tmp_path / "control.json", control, capsys)
    assert rc == 0, f"control (d3 A, store not pinned) rc {rc}: {err}"
    data["d3"] = d3
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    for extra in (["--dry-run"], []):
        rc = fill.main(["--repo-root", str(root), "--data", str(data_path), "--variants", str(REPO / VARIANTS), *extra])
        err = capsys.readouterr().err.strip()
        assert rc == 3, f"d3 {d3!r} without the store pin {extra}: rc {rc}: {err}"
        assert len(err.splitlines()) == 1 and "openai_store_pinned" in err and "nothing written" in err, err
    assert _snapshot(root) == start, "the refused run wrote to the temp copy"
    with pytest.raises(fill.FillInError):
        fill.plan(root, data, _json(VARIANTS))


def _withdraw_values():
    placeholders = _json(FILL_IN)["placeholders"]
    values = {lang: placeholders.get(key) for lang, key in (("en", "WITHDRAW_PATH"), ("ar", "WITHDRAW_PATH_AR"))}
    missing = [lang for lang, value in values.items() if not (isinstance(value, str) and value.strip())]
    assert not missing, f"{FILL_IN}: WITHDRAW_PATH not recorded for {missing} (UG2, UG11)"
    return values


def _stranded(text, values):
    """The stranded-preposition strings in `text`: the EN list, and each AR preposition + the AR value's first word."""
    needles = list(STRANDED_EN) + [f" {p} {values['ar'].split()[0]}" for p in AR_PREPOSITIONS]
    return [needle for needle in needles if needle in text]


def test_d3c_g_withdraw_path_never_follows_a_sentence_preposition(tmp_path):
    """(g) UG2: the committed WITHDRAW_PATH / _AR values carry their own preposition, so privacy s4 and
    s10 no longer carry one. On a synthetic complete fill-in with the committed values, the six filled
    sources and the six rendered landing regions never read " in by " / " at by " (or an AR preposition
    before the value's first word); the value fills s4 and s10 in both languages, and the s4 sentence
    also names the privacy address (the email route). Control first: the pre-UG2 heads are caught.
    FIX round 2 (UF8): the committed values name the path the App shows (PATH_EN and its AR twin; (l)
    pins the labels)."""
    values = _withdraw_values()
    assert f"({PATH_EN})" in values["en"] and f"({_fix2_ar()['path']})" in values["ar"], "WITHDRAW_PATH lacks the UF8 path"
    controls = [head + values["en"] for head in OLD_HEADS_EN] + [head + values["ar"] for head in OLD_HEADS_AR]
    uncaught = [_esc(c[:40]) for c in controls if not _stranded(" " + c, values)]
    assert not uncaught, f"the stranded-preposition scan misses the pre-UG2 sentences: {uncaught}"
    fill = _load(FILL_SCRIPT, "_u8_d3c_fill_in_g")
    root = tmp_path / "repo"
    _copy_tree(root)
    data = _complete_data()
    data["placeholders"]["WITHDRAW_PATH"] = values["en"]
    data["placeholders"]["WITHDRAW_PATH_AR"] = values["ar"]
    missing, outputs = fill.plan(root, data, _json(VARIANTS))
    assert missing == [] and set(outputs) == set(SOURCES), missing
    for rel, (new, _old) in outputs.items():
        (root / rel).write_bytes(new)
    regions = _load(RENDERER, "_u8_d3c_renderer_g").render_regions(root)
    texts = {rel: _read(rel, root).replace("\r\n", "\n") for rel in SOURCES}
    texts.update({page: html.unescape(region) for page, region in regions.items()})
    assert set(texts) == set(SOURCES) | set(PAGES), sorted(texts)
    problems = [f"{rel}: {_esc(n)!r}" for rel, text in sorted(texts.items()) for n in _stranded(text, values)]
    email = data["placeholders"]["PRIVACY_EMAIL"]
    for rel, lang in ((PRIVACY_EN, "en"), (PRIVACY_AR, "ar")):
        s4, s10 = _section(texts[rel], 4) or "", _section(texts[rel], 10) or ""
        if values[lang] not in s4 or values[lang] not in s10:
            problems.append(f"{rel}: the WITHDRAW_PATH value is not in both s4 and s10")
        if not any(values[lang] in line and email in line for line in s4.split("\n")):
            problems.append(f"{rel} s4: the withdrawal sentence does not name {email}")
    assert not problems, problems


def _subsection(text, number):
    match = re.search(r"(?ms)^### " + re.escape(str(number)) + r"[^\n]*\n(.*?)(?=^##|\Z)", text)
    return match.group(1) if match else ""


def test_d3c_h_no_per_user_sharing_setting_is_claimed():
    """(h) UG6: under D3 = C the App has no sharing setting (U3b removed the toggle), so privacy s3.3
    lists only the notification settings, and no legal source, EN or AR, claims a sharing setting."""
    problems = []
    if S33_EN not in _subsection(_read(PRIVACY_EN), "3.3"):
        problems.append(f"{PRIVACY_EN} s3.3: no {S33_EN!r}")
    if S33_AR not in _subsection(_read(PRIVACY_AR), "3.3"):
        problems.append(f"{PRIVACY_AR} s3.3: no AR 'your notification settings'")
    for rel in SOURCES:
        text = _read(rel)
        if re.search(SHARING_SETTING_EN, text) or SHARING_SETTING_AR in text:
            problems.append(f"{rel}: claims a per-user sharing setting")
    assert not problems, problems


# ---------------------------------------------------------------------------
# FIX additions (session 76, ruling UG12 + the owner's clarification "comparison data
# and preference data, never personal"; FIX round 2 rulings UF3-UF8): (i) the terms
# history, licence and derived-data sentences, (j) privacy s2, s3.6 and s9, (k) no sentence
# claims ownership or a sale of personal data or of a user's own items, (l) the deletion
# path names the App's real controls, (m) the hosting roles of privacy s7, (n) the s5
# carve-out for OpenAI
# ---------------------------------------------------------------------------

# Terms section 8 (EN binding wording; the AR twins live in the fixture's ug12_ar, [SPEC]).
TERMS_HISTORY_EN = (
    "Your account's comparison history is yours to view, share and delete, and is handled under our Privacy Policy."
)
TERMS_LICENCE_EN = (
    "You grant us a worldwide, royalty-free licence to use the content you submit to MYEZ (your queries, "
    "photos, links, feedback and preferences) to operate, secure and improve the service, to create "
    "de-identified comparison and preference datasets, and to obtain comparisons from our AI provider as our "
    "Privacy Policy describes."
)
TERMS_DERIVED_EN = (
    "We own MYEZ's comparison data (the search queries, the products compared, the verdicts and scores, and the "
    "prices gathered), which we de-identify before any such use, and the preference and usage statistics we "
    "derive in aggregated or anonymised form, and we may use, license or sell that comparison and preference "
    "data to third parties; none of it identifies you, and your personal data is never sold."
)
# Wording FIX round 2 retired (UF6 b, d); neither may come back.
TERMS_RETIRED_EN = ("Your comparison history is yours and", "stripped of anything that identifies you")
# Privacy section 2 (UF7: the "not sold" statement points at section 4 for OpenAI), 3.6 (UF6 c) and 9 (UF6 e).
PRIVACY_NOT_SOLD_EN = "We do not sell your personal data"
PRIVACY_S2_EN = (
    "We do not sell your personal data, and we do not share it with data brokers or advertisers; section 4 "
    "describes what OpenAI may do with the inputs and outputs of your comparisons."
)
PRIVACY_AGG_EN = (
    "We may share or sell aggregated or anonymised comparison and preference statistics (for example price "
    "trends or category popularity) that cannot identify you."
)
PRIVACY_PURPOSE_EN = (
    "- **In our legitimate interest in improving and funding the service:** producing de-identified statistics "
    "about comparisons and preferences."
)
PRIVACY_S9_EN = "De-identified statistics that cannot identify you may be kept after deletion."
# FIX round 3 (UF11): privacy s3.6 names OpenAI's use under its data-sharing programme with its legal basis.
PRIVACY_OPENAI_PURPOSE_EN = (
    "- Letting OpenAI use the inputs and outputs of your comparisons under its data-sharing programme, as section 4 "
    "describes (legal basis: the permission you give before your first comparison; withdrawal as section 10 "
    "describes)."
)
TERMS_EN = "app/legal/terms_of_service.md"
TERMS_AR = "app/legal/terms_of_service_ar.md"

# (k) THE SCAN. A clause is a run of text between . ; ! ? a newline or the AR semicolon / question mark.
# Two triggers. (1) A clause that mentions personal data (EN "personal data" / "personal information"; AR
# bayanat... + (al)shakhsi) may not carry a sale, licence, ownership, trade or rent word. (2) FIX round 2
# (UF8): a clause that names a user's own item (EN "your" + query, search, preference, comparison, history,
# photo, email, name, data, information, profile, account, identifier, answer, location, feedback or
# message; AR the same nouns with the second-person suffix -ka) may not carry a sale, trade, rent or
# verb-licence word: under the UG12 clarification a query or preference linked to an account is personal
# data (the licence the user grants us, "licence" the noun, is not a sale). Under either trigger a
# transfer word counts when the clause says the transfer is for value (EN "for value / money / payment",
# "in exchange for ..."; AR muqabil not after dun / bidun / bila). A word passes when one of the three
# words before it is a negator: "we do not sell your personal data" and "your personal data is never sold"
# pass; "we may sell your search queries" and "we may trade your personal data" (the final adversary's
# probes P2b and P7) do not.
# FIX round 3 (UF13): (3) a clause about "data / information / details ... about you" (AR bayanat / ma'lumat ...
# 'ank) is a user's own item too (the adversary's probe X2); and under any trigger the verb share (AR the
# root sh-r-k: nusharik, musharaka) is a claim word when the clause names advertisers, data brokers or
# partners as the recipient (probe X1). "We do not share it with data brokers or advertisers" passes (negated).
CLAUSE_SPLIT = re.compile("[.;!?\n\u061b\u061f]")
PERSONAL_DATA_EN = re.compile(r"(?i)\bpersonal\s+(?:data|information)\b")
USER_ITEM_EN = re.compile(
    r"(?i)\byour\s+(?:[\w-]+\s+){0,2}?(?:quer(?:y|ies)|search(?:es)?|preferences?|comparisons?|histor(?:y|ies)"
    r"|photos?|emails?|names?|data|information|profiles?|accounts?|identifiers?|answers?|locations?|feedback"
    r"|messages?)\b"
)
SALE_OR_OWN_EN = re.compile(
    r"(?i)^(?:re)?(?:sell|sells|selling|sold|sale|sales|licen[cs]e[sd]?|licensing|own|owns|owned|ownership"
    r"|belongs?|belonging|property|monetis\w*|monetiz\w*|trade[sd]?|trading|rent|rents|rented|renting|rental)$"
)
SALE_EN = re.compile(
    r"(?i)^(?:re)?(?:sell|sells|selling|sold|sale|sales|license[sd]?|licensing|monetis\w*|monetiz\w*"
    r"|trade[sd]?|trading|rent|rents|rented|renting|rental)$"
)
TRANSFER_EN = re.compile(r"(?i)^transfer(?:s|red|ring)?$")
FOR_VALUE_EN = re.compile(
    r"(?i)\b(?:for|in\s+exchange\s+for|in\s+return\s+for)\s+(?:value|money|payment|cash|a\s+fee|compensation"
    r"|consideration|profit)\b"
)
NEGATORS_EN = frozenset(("not", "never", "no", "none", "don't", "doesn't", "won't", "cannot"))
SHARE_EN = re.compile(r"(?i)^shar(?:e|es|ed|ing)$")
RECIPIENT_EN = re.compile(r"(?i)\b(?:advertisers?|data\s+brokers?|partners?)\b")
ABOUT_YOU_EN = re.compile(r"(?i)\b(?:data|information|details)\b(?:\s+[\w'-]+){0,4}?\s+about\s+you\b")
# AR (after dropping the harakat and the tatweel): bayanat<suffix> (al)shakhsi = personal data.
AR_MARKS = re.compile("[\u0640\u064b-\u065f\u0670]")
PERSONAL_DATA_AR = re.compile("\u0628\u064a\u0627\u0646\u0627\u062a\\S*\\s+(?:\u0627\u0644)?\u0634\u062e\u0635\u064a")
# A user's own item: bayanat, ma'lumat, tafdilat, muqaranat, muqaranat (sing.), bahth, suwar, barid, ism, malaff,
# hisab, ijabat, sijill, mulahazat, rasa'il, rawabit + the suffix -ka.
USER_ITEM_AR = re.compile(
    "(?:\u0628\u064a\u0627\u0646\u0627\u062a|\u0645\u0639\u0644\u0648\u0645\u0627\u062a|\u062a\u0641\u0636\u064a\u0644\u0627\u062a|\u0645\u0642\u0627\u0631\u0646\u0627\u062a|\u0645\u0642\u0627\u0631\u0646\u062a|\u0628\u062d\u062b|\u0635\u0648\u0631|\u0628\u0631\u064a\u062f|\u0627\u0633\u0645|\u0645\u0644\u0641|\u062d\u0633\u0627\u0628|\u0625\u062c\u0627\u0628\u0627\u062a|\u0633\u062c\u0644|\u0645\u0644\u0627\u062d\u0638\u0627\u062a|\u0631\u0633\u0627\u0626\u0644|\u0631\u0648\u0627\u0628\u0637)\u0643(?![\u0621-\u064a])"
)
# sell: bay' (not in tabi'a, rabi'), ba' (not in ittiba', tiba'a, ishba'); trade: yatajir / natajir / tatajir,
# ittijar, mutajara (not matajir, stores); rent: ta'jir, yu'ajjir, ijar, isti'jar.
SALE_AR = (
    "(?<![\u0637\u0631])\u0628\u064a\u0639|(?<!\u0627\u062a)(?<![\u0637\u0634])\u0628\u0627\u0639"
    "|\u064a\u062a\u0627\u062c\u0631|\u0646\u062a\u0627\u062c\u0631|\u062a\u062a\u0627\u062c\u0631|\u0627\u062a\u062c\u0627\u0631|\u0645\u062a\u0627\u062c\u0631\u0629"
    "|\u062a\u0623\u062c\u064a\u0631|\u0624\u062c\u0631|\u0625\u064a\u062c\u0627\u0631|\u0627\u0633\u062a\u0626\u062c\u0627\u0631"
)
SALE_ONLY_AR = re.compile(SALE_AR)
# + rakhs / rakhis (licence), mlk not in mamlaka (own), mamluk (owned).
SALE_OR_OWN_AR = re.compile(SALE_AR + "|\u0631\u062e\u064a?\u0635|(?<!\u0645)\u0645\u0644\u0643(?!\u0629)|\u0645\u0645\u0644\u0648\u0643")
# transfer: naql, tahwil; for value: muqabil, not after dun / bidun / bila (royalty-free, "without consideration").
TRANSFER_AR = re.compile("\u0646\u0642\u0644|\u062a\u062d\u0648\u064a\u0644|\u0646\u062d\u0648\u0644|\u064a\u062d\u0648\u0644")
FOR_VALUE_AR = re.compile("(?<!\u062f\u0648\u0646 )(?<!\u0628\u062f\u0648\u0646 )(?<!\u0628\u0644\u0627 )\u0645\u0642\u0627\u0628\u0644")
# la, lan, lam, laysa, laysat, abadan; a leading wa / fa conjunction is dropped first.
NEGATORS_AR = frozenset(("\u0644\u0627", "\u0644\u0646", "\u0644\u0645", "\u0644\u064a\u0633", "\u0644\u064a\u0633\u062a", "\u0623\u0628\u062f\u0627"))
# share: the root sh-r-k (nusharik, yusharik, musharaka); recipients: mu'lin (advertiser), wusata' al-bayanat
# (data brokers), shuraka' (partners); about you: bayanat / ma'lumat ... 'ank.
SHARE_AR = re.compile("\u0634\u0627\u0631\u0643")
RECIPIENT_AR = re.compile("\u0645\u0639\u0644\u0646|\u0648\u0633\u0637\u0627\u0621 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a|\u0634\u0631\u0643\u0627\u0621|\u0634\u0631\u0643\u0627\u0626")
ABOUT_YOU_AR = re.compile("(?:\u0628\u064a\u0627\u0646\u0627\u062a|\u0645\u0639\u0644\u0648\u0645\u0627\u062a)(?:\\s+\\S+){0,4}?\\s+\u0639\u0646\u0643(?![\u0621-\u064a])")
# Control sentences for the EN scan (the AR controls are the fixture's ug12_ar.flagged / accepted).
EN_FLAGGED = (
    "We may sell your personal data to third parties.",
    "MYEZ owns the personal data you submit.",
    "We do not show ads, but we may license your personal data to partners.",
    "Your personal data is sold to data brokers.",
    "Your personal information belongs to us.",
    # FIX round 2 (UF8): the final adversary's probes P2b and P7, then rent, transfer for value, a verb licence.
    "We may sell your search queries and preferences to data brokers.",
    "We may trade your personal data with partners.",
    "We may rent your personal data to advertisers.",
    "We may transfer your personal data to partners in exchange for payment.",
    "We may license your search history to partners.",
    # FIX round 3 (UF13): the final adversary 2's probes X1 and X2, then share with partners.
    "We may share your search history with advertisers.",
    "We may sell the data we collect about you to data brokers.",
    "We may share your personal data with partners.",
)
EN_ACCEPTED = (
    PRIVACY_NOT_SOLD_EN + ", we do not show third-party ads and we do not track you.",
    "None of it identifies you, and your personal data is never sold.",
    "We decide how and why your personal data is processed in the App.",
    PRIVACY_S2_EN,
    TERMS_HISTORY_EN,
    "We transfer your queries to our AI provider to produce the comparison.",
    "Rewards cannot be transferred, have no cash value and expire 7 days after they are granted.",
    # FIX round 3 (UF13): sharing with no advertiser, broker or partner recipient, or negated, passes.
    "Apple shares your email address, or a private relay address, with us.",
    "People who open an invite link you share can also see your display name.",
    "We never share your personal data with partners.",
)


def _ug12_ar():
    return _fixture()["ug12_ar"]


def _fix2_ar():
    return _fixture()["fix2_ar"]


def _fix3_ar():
    return _fixture()["fix3_ar"]


def _negated_ar(token):
    token = token.strip("\u060c,()")
    if token[:1] in ("\u0648", "\u0641") and token[1:] in NEGATORS_AR:
        token = token[1:]
    return token in NEGATORS_AR


def _clause_claims(tokens, words, transfer, for_value, negated):
    """True when a token is a claim word (or a transfer word in a for-value clause) not negated by the three words before it."""
    for i, token in enumerate(tokens):
        if (words(token) or (for_value and transfer(token))) and not negated(tokens[max(0, i - 3):i]):
            return True
    return False


def _with_share(words, share, recipient):
    """UF13: the claim words, plus the share verb when the clause names an advertiser, broker or partner."""
    if not recipient:
        return words
    return lambda token: words(token) or share(token)


def _personal_data_claims(text):
    """The clauses of `text` that claim a sale, licence or ownership of personal data, or a sale, trade or rent
    of a user's own items (see THE SCAN)."""
    claims = []
    for clause in CLAUSE_SPLIT.split(AR_MARKS.sub("", text)):
        personal = PERSONAL_DATA_EN.search(clause)
        item = USER_ITEM_EN.search(clause) or ABOUT_YOU_EN.search(clause)
        if personal or item:
            tokens = [t.strip(",()*:\"").lower() for t in clause.split()]
            words = _with_share((SALE_OR_OWN_EN if personal else SALE_EN).match, SHARE_EN.match, RECIPIENT_EN.search(clause))
            if _clause_claims(tokens, words, TRANSFER_EN.match, FOR_VALUE_EN.search(clause), lambda w: NEGATORS_EN.intersection(w)):
                claims.append(clause.strip())
                continue
        personal = PERSONAL_DATA_AR.search(clause)
        item = USER_ITEM_AR.search(clause) or ABOUT_YOU_AR.search(clause)
        if personal or item:
            words = _with_share((SALE_OR_OWN_AR if personal else SALE_ONLY_AR).search, SHARE_AR.search, RECIPIENT_AR.search(clause))
            if _clause_claims(clause.split(), words, TRANSFER_AR.search, FOR_VALUE_AR.search(clause), lambda w: any(_negated_ar(t) for t in w)):
                claims.append(clause.strip())
    return claims


def _paragraph_with(text, needle):
    hits = [line for line in text.split("\n") if needle in line]
    return hits[0] if len(hits) == 1 else None


def test_d3c_i_terms_grant_the_licence_and_own_only_derived_data():
    """(i) UG12 + UF6: terms section 8, EN and AR, carries the history sentence (the account's comparison history
    is the user's to view, share and delete), the licence sentence (queries, photos, links, feedback and
    preferences, to operate, secure and improve the service, to create de-identified comparison and preference
    datasets and to obtain comparisons from our AI provider) and the derived-data sentence (the comparison data,
    which we de-identify before any such use, and the aggregated or anonymised preference and usage statistics are
    ours to use, license or sell; none of it identifies a user; personal data is never sold), each once and in
    that order; the retired wording is gone."""
    ar = _ug12_ar()
    problems = []
    for rel, history, licence, derived, retired in (
        (TERMS_EN, TERMS_HISTORY_EN, TERMS_LICENCE_EN, TERMS_DERIVED_EN, TERMS_RETIRED_EN),
        (TERMS_AR, ar["terms_history"], ar["terms_licence"], ar["terms_derived"], tuple(ar["terms_retired"])),
    ):
        text = _read(rel)
        section = _section(text, 8) or ""
        for name, sentence in (("history", history), ("licence", licence), ("derived-data", derived)):
            if text.count(sentence) != 1 or sentence not in section:
                problems.append(f"{rel}: the {name} sentence is not in section 8 exactly once")
        if all(s in section for s in (history, licence, derived)) and not (
            section.index(history) < section.index(licence) < section.index(derived)
        ):
            problems.append(f"{rel}: section 8 does not read history, licence, derived data in that order")
        problems += [f"{rel}: retired wording {_esc(r)!r} is back" for r in retired if r in text]
    assert not problems, problems


def test_d3c_j_privacy_keeps_not_sold_and_adds_the_aggregated_sentence():
    """(j) UG12 + UF7 + UF6: privacy, EN and AR. Section 2 says personal data is not sold and not shared with data
    brokers or advertisers, pointing at section 4 for OpenAI, and the aggregated or anonymised statistics sentence
    follows it in the same paragraph, once; section 3.6 names the purpose of producing de-identified statistics
    with its legal basis and (UF11) the purpose of letting OpenAI use the inputs and outputs under its
    data-sharing programme with its legal basis; section 9 says de-identified statistics may be kept after
    deletion."""
    ar = _ug12_ar()
    ar_openai = _fix3_ar()["privacy_openai_purpose"]
    problems = []
    for rel, s2, not_sold, aggregated, purpose, s9, openai in (
        (PRIVACY_EN, PRIVACY_S2_EN, PRIVACY_NOT_SOLD_EN, PRIVACY_AGG_EN, PRIVACY_PURPOSE_EN, PRIVACY_S9_EN,
         PRIVACY_OPENAI_PURPOSE_EN),
        (PRIVACY_AR, ar["privacy_s2"], ar["privacy_not_sold"], ar["privacy_aggregated"], ar["privacy_purpose"], ar["privacy_s9"],
         ar_openai),
    ):
        text = _read(rel)
        paragraph = _paragraph_with(_section(text, 2) or "", not_sold)
        if paragraph is None:
            problems.append(f"{rel} s2: the 'personal data is not sold' statement is missing")
        elif text.count(s2) != 1 or s2 not in paragraph:
            problems.append(f"{rel} s2: the UF7 'not sold, not shared with brokers or advertisers' sentence is not there once")
        elif text.count(aggregated) != 1 or aggregated not in paragraph:
            problems.append(f"{rel} s2: the aggregated sentence is not in the 'not sold' paragraph exactly once")
        elif not paragraph.index(s2) < paragraph.index(aggregated):
            problems.append(f"{rel} s2: the aggregated sentence precedes the 'not sold' statement")
        if text.count(purpose) != 1 or purpose not in _subsection(text, "3.6"):
            problems.append(f"{rel} s3.6: the de-identified statistics purpose line is not there once")
        if text.count(openai) != 1 or openai not in _subsection(text, "3.6"):
            problems.append(f"{rel} s3.6: the OpenAI data-sharing programme purpose line (UF11) is not there once")
        if text.count(s9) != 1 or s9 not in (_section(text, 9) or ""):
            problems.append(f"{rel} s9: the de-identified statistics sentence is not there once")
    assert not problems, problems


def test_d3c_k_personal_data_claim_scan_positive_control():
    """(k) PIN: the scan flags every control claim (EN and AR, the final adversary's P2b and P7 among them) and
    spares the negated or neutral forms the documents use."""
    ar, fx3 = _ug12_ar(), _fix3_ar()
    missed = [_esc(s) for s in EN_FLAGGED + tuple(ar["flagged"]) + tuple(fx3["flagged"]) if not _personal_data_claims(s)]
    spurious = [_esc(s) for s in EN_ACCEPTED + tuple(ar["accepted"]) + tuple(fx3["accepted"]) if _personal_data_claims(s)]
    assert not missed, f"the scan misses: {missed}"
    assert not spurious, f"the scan flags a negated or neutral sentence: {spurious}"
    # The UG12 / UF6 / UF7 sentences themselves pass the scan.
    sentences = (
        TERMS_HISTORY_EN, TERMS_LICENCE_EN, TERMS_DERIVED_EN, PRIVACY_S2_EN, PRIVACY_AGG_EN, PRIVACY_PURPOSE_EN,
        PRIVACY_S9_EN, ar["terms_history"], ar["terms_licence"], ar["terms_derived"], ar["privacy_s2"],
        ar["privacy_aggregated"], ar["privacy_purpose"], ar["privacy_s9"],
        # FIX round 3: the UF10 s5 sentences and the UF11 purpose line, EN and AR.
        S5_CARVEOUT_EN, S5_OWN_TERMS_EN, PRIVACY_OPENAI_PURPOSE_EN, _fix2_ar()["s5_carveout"],
        fx3["s5_own_terms"], fx3["privacy_openai_purpose"],
    )
    assert not [_esc(s[:40]) for s in sentences if _personal_data_claims(s)]


def test_d3c_k_no_sentence_claims_ownership_or_sale_of_personal_data(tmp_path):
    """(k) UG12 + UF8: no clause of the six sources claims ownership of, a licence of or a sale of personal data,
    or a sale, trade or rent of a user's own items, in the checkout and after a synthetic complete fill-in of the
    pre-fill snapshot (so every selected variant text is scanned too)."""
    problems = [f"{rel}: {_esc(c[:120])}" for rel in SOURCES for c in _personal_data_claims(_read(rel))]
    fill = _load(FILL_SCRIPT, "_u8_d3c_fill_in_k")
    root = tmp_path / "repo"
    _copy_tree(root)
    missing, outputs = fill.plan(root, _complete_data(), _json(VARIANTS))
    assert missing == [], missing
    for rel in SOURCES:
        text = (outputs[rel][0] if rel in outputs else (root / rel).read_bytes()).decode("utf-8")
        assert "<PLACEHOLDER:" not in text, f"filled {rel}: a token is left"
        problems += [f"filled {rel}: {_esc(c[:120])}" for c in _personal_data_claims(text)]
    assert not problems, problems


# ---------------------------------------------------------------------------
# FIX round 2 additions: (l) UF8 the deletion path, (m) UF3 privacy s7, (n) UF4 privacy s5
# ---------------------------------------------------------------------------

# UF8: the Profile tab, the header settings icon (it opens the Edit Profile screen directly) and Delete account.
PATH_EN = "Profile, then the settings icon, then Delete account"
PATH_RETIRED_EN = "then Edit profile"
APP_ENTRY = "SmartCompareApp/App.tsx"
PROFILE_SCREEN = "SmartCompareApp/src/screens/ProfileScreen.tsx"
EDIT_PROFILE_SCREEN = "SmartCompareApp/src/screens/EditProfileScreen.tsx"
NAVIGATE = re.compile(r"navigation\.navigate\('(\w+)'\)")
# UF3: the roles privacy s7 names next to HOSTING_REGIONS (the Upstash region is not measured).
HOSTING_CLAUSE_EN = ", and in {value} (our database and hosting providers)"
TEMPORARY_STORAGE_EN = re.compile(r"(?i)temporary[- ]storage")
# UF4 + FIX round 3 (UF10): privacy s5's service-providers sentence carves out OpenAI's data-sharing programme
# (section 4); every "only to provide its service" claim in s5 must be that sentence, and the next sentence says
# retailer websites and the sign-in providers Apple and Google act under their own terms.
S5_CORE_EN = "only to provide its service"
S5_CARVEOUT_EN = (
    "Except as section 4 describes for OpenAI, each of our service providers processes data only to provide its "
    "service to us, and we require each of them to protect it at least as well as this policy does."
)
S5_OWN_TERMS_EN = "Retailer websites (section 6) and the sign-in providers Apple and Google act under their own terms."
RENDERED_SECTION = r"(?s)<h2\b[^>]*>\s*{n}\.(.*?)(?=<h2\b|\Z)"


def _filled(tmp_path, name, **answers):
    """A synthetic complete fill-in of the pre-fill snapshot with the committed WITHDRAW_PATH values: {rel: text}."""
    fill = _load(FILL_SCRIPT, f"_u8_d3c_fill_in_{name}")
    root = tmp_path / name
    _copy_tree(root)
    data = _complete_data()
    data.update(answers)
    values = _withdraw_values()
    data["placeholders"]["WITHDRAW_PATH"] = values["en"]
    data["placeholders"]["WITHDRAW_PATH_AR"] = values["ar"]
    missing, outputs = fill.plan(root, data, _json(VARIANTS))
    assert missing == [] and set(outputs) == set(SOURCES), missing
    return {rel: new.decode("utf-8").replace("\r\n", "\n") for rel, (new, _old) in outputs.items()}


def test_d3c_l_deletion_path_names_the_controls_the_app_shows(tmp_path):
    """(l) UF8: the deletion / withdrawal path is "Profile, then the settings icon, then Delete account" (AR twin)
    in WITHDRAW_PATH, every DELETION_SECTION variant and, after synthetic fill-ins (043 and old), privacy s4, s9,
    s10 and terms s13; "then Edit profile" (AR twin) is gone from the variants, the data file, the six sources and
    the six landing pages. THE LABELS CHECK: the path's words are the App's own labels (the Profile tab label
    profile.title, the settings icon's accessibility label profile.settings, editProfile.deleteAccount, EN and
    AR catalogs), and the settings icon opens the Edit Profile screen, which renders Delete account."""
    fx = _fix2_ar()
    paths = {"en": PATH_EN, "ar": fx["path"]}
    retired = {"en": PATH_RETIRED_EN, "ar": fx["path_retired"]}
    problems = []
    # The labels check.
    for lang, catalog in (("en", EN_CATALOG), ("ar", AR_CATALOG)):
        strings = json.loads(_read(catalog))
        title, settings, delete = (strings.get(k) for k in ("profile.title", "profile.settings", "editProfile.deleteAccount"))
        path = paths[lang]
        if not (title and path.startswith(title)):
            problems.append(f"{lang}: the path does not start with the Profile tab label {_esc(title)!r}")
        if not (settings and settings.casefold() in path.casefold()):
            problems.append(f"{lang}: the path does not name the settings icon's label {_esc(settings)!r}")
        if not (delete and path.rstrip("\u00bb").endswith(delete)):
            problems.append(f"{lang}: the path does not end with the Delete account label {_esc(delete)!r}")
    if "tabBarLabel: t('profile.title')" not in _read(APP_ENTRY):
        problems.append(f"{APP_ENTRY}: the Profile tab is no longer labelled profile.title")
    screen = _read(PROFILE_SCREEN)
    at = screen.find('testID="profile-header-settings"')
    targets = NAVIGATE.findall(screen[max(0, at - 400):at]) if at >= 0 else []
    if not targets or targets[-1] != "EditProfile":
        problems.append(f"{PROFILE_SCREEN}: the header settings icon does not open EditProfile ({targets})")
    if "t('editProfile.deleteAccount')" not in _read(EDIT_PROFILE_SCREEN):
        problems.append(f"{EDIT_PROFILE_SCREEN}: no Delete account row")
    # The committed texts.
    values = _withdraw_values()
    for lang in ("en", "ar"):
        if f"({paths[lang]})" not in values[lang]:
            problems.append(f"{FILL_IN}: WITHDRAW_PATH ({lang}) does not name the UF8 path")
        for doc, table in _json(VARIANTS)["clauses"]["DELETION_SECTION"][lang].items():
            for variant, text in table.items():
                if f"({paths[lang]})" not in text:
                    problems.append(f"{VARIANTS}: DELETION_SECTION {lang}.{doc}.{variant} does not name the UF8 path")
    for rel in (VARIANTS, FILL_IN) + SOURCES + PAGES:
        text = _read(rel)
        if rel == FILL_IN:
            text = json.dumps(json.loads(text), ensure_ascii=False)
        problems += [f"{rel}: the retired path {_esc(r)!r}" for r in retired.values() if r in text]
    # Synthetic fill-ins: the path reaches privacy s4, s9, s10 and terms s13, EN and AR.
    for variant in ("043", "old"):
        texts = _filled(tmp_path, f"l_{variant}", deletion_variant=variant)
        for lang, privacy, terms in (("en", PRIVACY_EN, TERMS_EN), ("ar", PRIVACY_AR, TERMS_AR)):
            for rel, number in ((privacy, 4), (privacy, 9), (privacy, 10), (terms, 13)):
                if paths[lang] not in (_section(texts[rel], number) or ""):
                    problems.append(f"{variant}: filled {rel} s{number} lacks the UF8 path")
            problems += [f"{variant}: filled {rel}: the retired path" for rel in SOURCES if retired[lang] in texts[rel]]
    assert not problems, problems


def test_d3c_m_hosting_regions_clause_names_only_the_measured_roles(tmp_path):
    """(m) UF3: privacy s7 names HOSTING_REGIONS for "our database and hosting providers" only (EN and AR):
    the Upstash (temporary-storage) region is not measured, so a filled s7 never says temporary storage."""
    fx = _fix2_ar()
    clause = _json(VARIANTS)["clauses"]["HOSTING_REGIONS_CLAUSE"]
    problems = []
    if clause["en"]["privacy"]["nonempty"] != HOSTING_CLAUSE_EN:
        problems.append(f"{VARIANTS}: HOSTING_REGIONS_CLAUSE en is {clause['en']['privacy']['nonempty']!r}")
    ar_clause = clause["ar"]["privacy"]["nonempty"]
    if fx["hosting_roles"] not in ar_clause or fx["temporary_storage"] in ar_clause:
        problems.append(f"{VARIANTS}: HOSTING_REGIONS_CLAUSE ar does not name only the database and hosting roles")
    texts = _filled(tmp_path, "m")
    regions = {"en": COMPLETE_VALUES_EN["HOSTING_REGIONS"], "ar": _fixture()["ar_values"]["HOSTING_REGIONS_AR"]}
    for lang, rel, roles, storage in (
        ("en", PRIVACY_EN, "(our database and hosting providers)", TEMPORARY_STORAGE_EN.pattern),
        ("ar", PRIVACY_AR, fx["hosting_roles"], re.escape(fx["temporary_storage"])),
    ):
        s7 = _section(texts[rel], 7) or ""
        if f"{regions[lang]} {roles}" not in s7:
            problems.append(f"filled {rel} s7: the regions are not followed by the database and hosting roles")
        if re.search(storage, s7):
            problems.append(f"filled {rel} s7: names a temporary-storage provider")
    assert not problems, [_esc(p) for p in problems]


def _carveout_problems(rel, text, core, carveout, flags):
    """s5 of `text` (markdown) carries the carve-out, and every providers-only claim in s5 is the carved-out one."""
    section = _section(text, 5) or ""
    claims = len(re.findall(re.escape(core), section, flags))
    carved = len(re.findall(re.escape(carveout), section, flags))
    if carved < 1 or claims != carved:
        return [f"{rel} s5: {claims} providers-only claim(s), {carved} carved out for OpenAI"]
    return []


@pytest.mark.parametrize("d3", ("C", "A"))
def test_d3c_n_providers_sentence_carves_out_openai(tmp_path, d3):
    """(n) UF4 + UF10: after a synthetic complete fill-in, privacy s5 says each of our service providers processes
    data only to provide its service "except as section 4 describes for OpenAI" (EN and AR, markdown and
    rendered), every "only to provide its service" claim in s5 is that sentence, and the next sentence says
    retailer websites (section 6) and the sign-in providers Apple and Google act under their own terms (once,
    after the carve-out). With d3 "C" section 4 carries the C paragraph (OpenAI's data-sharing programme), so the
    carve-out is what keeps s5 true; with d3 "A" it is present and harmless."""
    fx = _fix2_ar()
    own_terms = {"en": S5_OWN_TERMS_EN, "ar": _fix3_ar()["s5_own_terms"]}
    texts = _filled(tmp_path, f"n_{d3}", d3=d3)
    renderer = _load(RENDERER, f"_u8_d3c_renderer_n_{d3}")
    problems = []
    for lang, rel, core, carveout, flags in (
        ("en", PRIVACY_EN, S5_CORE_EN, S5_CARVEOUT_EN, re.I),
        ("ar", PRIVACY_AR, fx["s5_core"], fx["s5_carveout"], 0),
    ):
        text = texts[rel]
        problems += _carveout_problems(rel, text, core, carveout, flags)
        section = _section(text, 5) or ""
        if text.count(own_terms[lang]) != 1 or own_terms[lang] not in section:
            problems.append(f"{rel} s5: the retailer / Apple / Google own-terms sentence (UF10) is not there once")
        elif carveout not in section or section.index(carveout) > section.index(own_terms[lang]):
            problems.append(f"{rel} s5: the own-terms sentence does not follow the service-providers sentence")
        rendered = html.unescape(renderer.render_markdown(text))
        match = re.search(RENDERED_SECTION.format(n=5), rendered)
        rendered_s5 = match.group(1) if match else ""
        if own_terms[lang] not in rendered_s5:
            problems.append(f"{rel}: the rendered s5 lacks the own-terms sentence (UF10)")
        if len(re.findall(re.escape(core), rendered_s5, flags)) != len(re.findall(re.escape(carveout), rendered_s5, flags)) or carveout.split()[0] not in rendered_s5:
            problems.append(f"{rel}: the rendered s5 is not carved out")
        own = _d3_fork()[lang][d3]
        if own not in (_section(text, 4) or ""):
            problems.append(f"{rel} s4: the d3 {d3} paragraph is not selected")
    assert not problems, [_esc(p) for p in problems]
