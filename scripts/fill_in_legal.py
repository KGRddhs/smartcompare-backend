"""Apply the owner's answers to the legal documents (unit U8, rulings UL3, UL9, UG3).

Reads ``tests/fixtures/legal_fill_in_u8.json`` (the answers, the seven flag
states and the placeholder values) and ``scripts/legal_variants_u8.json`` (the
variant texts), then:

1. selects every fork: the committed markdown carries the recommended variant
   inline; the variant found in the document (exactly once, as raw text or as
   already filled in) is replaced by the variant the answers select;
2. expands every derived clause token (``TRADE_NAME_CLAUSE``,
   ``DELETION_SECTION`` ...) from its answer;
3. substitutes every remaining ``<PLACEHOLDER:ID>`` token from the data file;
4. writes the six markdown sources (the two documents and the support contact
   block, English and Arabic) and re-renders the six landing regions through
   ``scripts/render_legal_landing.py``.

It writes NOTHING while any answer, flag or required placeholder is null (the
missing keys are printed, exit code 2) or while any document or variant is
inconsistent (exit code 3; so is d3 "B" or "C" with openai_store_pinned
false, UG5). It is also inconsistent when the filled documents
do not carry a recorded value or a selected clause text: after a first fill no
token is left to replace, so a value or answer changed since then would
otherwise be dropped silently; restore the pre-fill markdown from git and run
again. Every landing page's region markers and every filled source's markdown
are checked through the renderer BEFORE the first write, so a page that cannot
be rendered also writes nothing (exit code 3). The result is deterministic,
and running it again with the same data changes nothing. The effective dates
are not placeholders: the orchestrator moves the twelve date anchors in the
fill-in commit (UL3).

Answers that live under "placeholders" (the data file's top level is frozen by
its schema): CONTROLLER_COUNTRY (null, or "Bahrain": sections 7 and 10 name
Bahrain, any other country is refused until they are re-drafted),
RETENTION_CLEANUP_LIVE ("true" | "false" | null = not live: a fixed retention
period is refused until the cleanup is live, UL8), REFERRAL_PUSH_DISPLAY_NAME_ONLY
("true" | "false" | null = "false": the referral-notification sentence),
DPO_CONTACT_DETAILS / _AR (null = no DPO_CONTACT clause). Null is their
documented default, so they are never reported missing.

Usage, from the repo root:

    python scripts/fill_in_legal.py [--dry-run] [--data PATH] [--variants PATH]

Standard library only. Importing this module has no side effect.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = "tests/fixtures/legal_fill_in_u8.json"
VARIANTS_FILE = "scripts/legal_variants_u8.json"
RENDERER_FILE = "scripts/render_legal_landing.py"

# (language, document) -> markdown source
DOCUMENTS = {
    ("en", "privacy"): "app/legal/privacy_policy.md",
    ("en", "terms"): "app/legal/terms_of_service.md",
    ("en", "support"): "app/legal/support_contact.md",
    ("ar", "privacy"): "app/legal/privacy_policy_ar.md",
    ("ar", "terms"): "app/legal/terms_of_service_ar.md",
    ("ar", "support"): "app/legal/support_contact_ar.md",
}

SEVEN_FLAGS = (
    "ENABLE_YOUTUBE_SOURCE",
    "ENABLE_REENGAGEMENT_PUSHES",
    "ENABLE_BONUS_EXPIRY_PUSHES",
    "ENABLE_FEWSHOT_ROTATION",
    "ENABLE_FIRECRAWL",
    "ENABLE_SCRAPEDO",
    "ENABLE_BRIGHTDATA_FALLBACK",
)
ENUM_ANSWERS = {
    "deletion_variant": ("043", "old"),
    "territories": ("bahrain", "gcc"),
    "d3": ("A", "B", "C"),
    "d5": ("A", "B"),
}
BOOL_ANSWERS = ("counsel_review", "minors_clause", "openai_store_pinned", "inapp_notif_clause")
STR_ANSWERS = ("trade_name",)
ANSWER_KEYS = (*ENUM_ANSWERS, *BOOL_ANSWERS, *STR_ANSWERS)

TOKEN = re.compile(r"<PLACEHOLDER:([A-Z][A-Z0-9_]*)>")
PLACEHOLDER_ID = re.compile(r"^[A-Z][A-Z0-9_]*$")
# A value is text inside a sentence: no markup, no line breaks. Counsel's
# wording (keys ending in _COUNSEL or _COUNSEL_AR) may span lines and use
# markdown emphasis and top-level "- " items, nothing outside the renderer's subset.
_FORBIDDEN_IN_VALUE = re.compile(r"[<>\[\]`*\r\n]")
_FORBIDDEN_IN_COUNSEL_VALUE = re.compile(r"[<>`\r]")
COUNSEL_SUFFIXES = ("_COUNSEL", "_COUNSEL_AR")
# The renderer's refusals (scripts/render_legal_landing.py OUTSIDE_SUBSET), per counsel line.
_COUNSEL_OUTSIDE_SUBSET = (
    re.compile(r"^[ \t]*(?:[-*_][ \t]*){3,}$"),
    re.compile(r"^[ \t]*[0-9]+[.)][ \t]"),
    re.compile(r"^[ \t]*[*+][ \t]"),
    re.compile(r"^[ \t]+-[ \t]"),
    re.compile(r"^[ \t]*>"),
    re.compile(r"^[ \t]*\|"),
    re.compile(r"^[ \t]*#{4,}"),
)
_COUNSEL_ITEM = re.compile(r"^-[ \t]")
_MAX_CLAUSE_DEPTH = 5
REFILL_HINT = "already filled? restore the pre-fill markdown from git and run again"

# Answers kept under "placeholders" (strings; null is the documented default, never missing).
CONTROLLER_COUNTRY = "CONTROLLER_COUNTRY"
RETENTION_CLEANUP_LIVE = "RETENTION_CLEANUP_LIVE"
REFERRAL_PUSH_DISPLAY_NAME_ONLY = "REFERRAL_PUSH_DISPLAY_NAME_ONLY"
ANSWER_PLACEHOLDERS = (CONTROLLER_COUNTRY, RETENTION_CLEANUP_LIVE, REFERRAL_PUSH_DISPLAY_NAME_ONLY)
BOOL_STRING_PLACEHOLDERS = (RETENTION_CLEANUP_LIVE, REFERRAL_PUSH_DISPLAY_NAME_ONLY)
DOCUMENTED_COUNTRY = "Bahrain"
RETENTION_KEYS = (
    "SECURITY_LOG_RETENTION", "SECURITY_LOG_RETENTION_AR", "ANON_LOG_RETENTION", "ANON_LOG_RETENTION_AR",
)
# A fixed retention period names a number or a duration (UL8: only once the cleanup is live).
_FIXED_PERIOD = re.compile(
    r"[0-9\u0660-\u0669\u06f0-\u06f9]|\b(?:hours?|days?|weeks?|months?|years?)\b"
    "|\u0633\u0627\u0639\u0629|\u0633\u0627\u0639\u0627\u062a|\u064a\u0648\u0645|\u0623\u064a\u0627\u0645"
    "|\u0623\u0633\u0628\u0648\u0639|\u0623\u0633\u0627\u0628\u064a\u0639|\u0634\u0647\u0631|\u0623\u0634\u0647\u0631"
    "|\u0634\u0647\u0648\u0631|\u0633\u0646\u0629|\u0633\u0646\u0648\u0627\u062a|\u0633\u0646\u064a\u0646"
    "|\u0639\u0627\u0645|\u0623\u0639\u0648\u0627\u0645",
    re.IGNORECASE,
)
# The only placeholder values that may be an empty string (an unknown region; F1).
EMPTY_ALLOWED = ("HOSTING_REGIONS", "HOSTING_REGIONS_AR")
# d3 values whose text says shared data follows OpenAI's terms "rather than the 30-day ... limit
# below": that limit is the openai_retention sentence only openai_store_pinned true publishes (UG5).
STORE_PIN_D3 = ("B", "C")


class FillInError(Exception):
    """The data, the variants or a document is inconsistent; nothing was written."""


class RenderAfterWriteError(Exception):
    """The landing renderer failed after the markdown sources were written (pages are stale)."""


def _schema_problems(data) -> list:
    """The same rules as the fill-in data schema of tests/test_legal_docs_u8.py."""
    if not isinstance(data, dict):
        return ["the data file must be a JSON object"]
    problems = []
    expected = {*ANSWER_KEYS, "flags", "placeholders"}
    problems += [f"unknown key {k!r}" for k in sorted(data) if not k.startswith("_") and k not in expected]
    problems += [f"missing key {k!r}" for k in sorted(expected - set(data))]
    for key, allowed in ENUM_ANSWERS.items():
        value = data.get(key)
        if value is not None and value not in allowed:
            problems.append(f"{key} must be one of {allowed} or null")
    for key in BOOL_ANSWERS:
        value = data.get(key)
        if value is not None and not isinstance(value, bool):
            problems.append(f"{key} must be true, false or null")
    for key in STR_ANSWERS:
        value = data.get(key)
        if value is not None and not isinstance(value, str):
            problems.append(f"{key} must be a string or null")
    flags = data.get("flags")
    if not isinstance(flags, dict) or set(flags) != set(SEVEN_FLAGS):
        problems.append(f"flags must name exactly {SEVEN_FLAGS}")
    else:
        problems += [f"flags.{n} must be on, off or null" for n, v in sorted(flags.items()) if v not in ("on", "off", None)]
    placeholders = data.get("placeholders")
    if not isinstance(placeholders, dict):
        problems.append("placeholders must be an object")
    else:
        for pid, value in sorted(placeholders.items()):
            if not PLACEHOLDER_ID.match(str(pid)):
                problems.append(f"placeholder id {pid!r} is not [A-Z][A-Z0-9_]*")
            elif value is not None and not isinstance(value, str):
                problems.append(f"placeholders.{pid} must be a string or null")
        problems += _answer_placeholder_problems(placeholders)
    return problems


def _answer_placeholder_problems(placeholders: dict) -> list:
    """The answers kept under "placeholders" (UP4 A11, A12a, A15)."""
    problems = []
    for key in BOOL_STRING_PLACEHOLDERS:
        if placeholders.get(key) not in (None, "true", "false"):
            problems.append(f'placeholders.{key} must be "true", "false" or null')
    country = placeholders.get(CONTROLLER_COUNTRY)
    if isinstance(country, str) and country.strip().casefold() != DOCUMENTED_COUNTRY.casefold():
        problems.append(
            f"placeholders.{CONTROLLER_COUNTRY} is {country!r}: the documents name {DOCUMENTED_COUNTRY} as the "
            "controller's country (privacy section 7 'Transfers outside Bahrain' and the section 10 complaint "
            "authority); re-draft sections 7 and 10 before recording another country"
        )
    if placeholders.get(RETENTION_CLEANUP_LIVE) != "true":
        for key in RETENTION_KEYS:
            value = placeholders.get(key)
            if isinstance(value, str) and _FIXED_PERIOD.search(value):
                problems.append(
                    f"placeholders.{key} names a fixed period, which needs the DEL-FOLLOWUPS cleanup "
                    "(migration 044) merged and its Railway cron registered first (UL8); record "
                    f'placeholders.{RETENTION_CLEANUP_LIVE} "true" once it is, else use no-fixed-period wording'
                )
    return problems


def _store_pin_problem(data: dict):
    """One line when the selected d3 text would point at a retention sentence that is not published (UG5)."""
    if data.get("d3") in STORE_PIN_D3 and data.get("openai_store_pinned") is False:
        return (
            f"d3 {data['d3']!r} refers to the 30-day limit 'below', which is published only with "
            "openai_store_pinned true; record true once store=False is pinned on main (U3c) or choose d3 'A' (UG5)"
        )
    return None


def _lookup(data, path: str):
    """(known, value) for an answer path: 'd3', 'flags.X' or 'placeholders.X'."""
    if path.startswith("flags."):
        flags = data.get("flags") or {}
        return path[len("flags."):] in flags, flags.get(path[len("flags."):])
    if path.startswith("placeholders."):
        placeholders = data.get("placeholders") or {}
        return path[len("placeholders."):] in placeholders, placeholders.get(path[len("placeholders."):])
    return path in data, data.get(path)


def _value_key(value, table: dict) -> str:
    """The key of a variant table that an answer value selects."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str) and ("nonempty" in table or "empty" in table):
        return "nonempty" if value.strip() else "empty"
    return str(value)


def _check_value(key: str, value: str) -> None:
    counsel = key.endswith(COUNSEL_SUFFIXES)
    pattern = _FORBIDDEN_IN_COUNSEL_VALUE if counsel else _FORBIDDEN_IN_VALUE
    if pattern.search(value) or "PLACEHOLDER" in value:
        raise FillInError(f"{key}: value contains markup, a line break or a placeholder")
    if counsel:
        after_item = False
        for line in value.split("\n"):
            if not line.strip():
                after_item = False
                continue
            if any(rx.match(line) for rx in _COUNSEL_OUTSIDE_SUBSET) or (after_item and not _COUNSEL_ITEM.match(line)):
                raise FillInError(f"{key}: a line is outside the markdown subset the landing renderer supports")
            after_item = bool(_COUNSEL_ITEM.match(line))


class _Filler:
    def __init__(self, data: dict, variants: dict):
        self.data = data
        self.forks = variants.get("forks") or {}
        self.clauses = variants.get("clauses") or {}
        self.missing: set = set()
        placeholders = data.get("placeholders") or {}
        for token in sorted(self.clauses):
            if placeholders.get(token) is not None:
                raise FillInError(f"placeholders.{token} is derived from the answers and must stay null")

    # -- answers -----------------------------------------------------------
    def _answer(self, spec, lang: str, if_null=None):
        """The answer value; ``if_null`` (a value) stands for a null answer, which is then not missing.

        ``spec`` is a path, a {language: path} map, or {"all_end_with": [paths], "suffix": s}
        (true when every path's value ends with s, case-insensitively).
        """
        if isinstance(spec, dict) and "all_end_with" in spec:
            values = [self._answer(path, lang) for path in spec["all_end_with"]]
            if any(v is None for v in values):
                return None
            suffix = str(spec.get("suffix", "")).casefold()
            return all(str(v).strip().casefold().endswith(suffix) for v in values)
        path = spec.get(lang) if isinstance(spec, dict) else spec
        if not isinstance(path, str):
            raise FillInError(f"no answer path for language {lang!r}: {spec!r}")
        known, value = _lookup(self.data, path)
        if not known:
            raise FillInError(f"answer path {path!r} is not a key of the data file")
        if value is None and if_null is not None:
            return if_null
        if value is None:
            self.missing.add(path)
        return value

    # -- clauses -----------------------------------------------------------
    def _clause_text(self, token: str, lang: str, doc: str):
        clause = self.clauses[token]
        by_doc = clause.get(lang)
        if not isinstance(by_doc, dict):
            raise FillInError(f"clause {token} has no {lang!r} texts")
        table = by_doc.get(doc, by_doc.get("*"))
        if not isinstance(table, dict):
            raise FillInError(f"clause {token} has no {lang!r} text for document {doc!r}")
        value = self._answer(clause["answer"], lang, clause.get("if_null"))
        if value is None:
            return None
        key = _value_key(value, table)
        if key not in table:
            raise FillInError(f"clause {token} ({lang}, {doc}) has no variant {key!r}")
        text = table[key]
        if "{value}" in text:
            _check_value(token, value)
            text = text.replace("{value}", value.strip())
        return text

    def _expand_clauses(self, text: str, lang: str, doc: str):
        """(text, complete): derived tokens replaced where their answer is known."""
        complete = True
        pending: set = set()
        for _ in range(_MAX_CLAUSE_DEPTH):
            tokens = [
                t for t in dict.fromkeys(TOKEN.findall(text))
                if t in self.clauses and t not in pending
            ]
            if not tokens:
                return text, complete
            for token in tokens:
                clause = self._clause_text(token, lang, doc)
                if clause is None:
                    complete = False
                    pending.add(token)
                    continue
                text = text.replace(f"<PLACEHOLDER:{token}>", clause)
        raise FillInError(f"clause tokens nest deeper than {_MAX_CLAUSE_DEPTH} levels ({lang}, {doc})")

    def _substitute(self, text: str):
        """(text, complete): provided tokens replaced where the data file has a value."""
        placeholders = self.data.get("placeholders") or {}
        complete = True
        for token in sorted(set(TOKEN.findall(text))):
            if token in self.clauses:
                complete = False  # its answer is missing; recorded by _expand_clauses
                continue
            if token not in placeholders:
                raise FillInError(f"<PLACEHOLDER:{token}> has no key in {DATA_FILE}")
            value = placeholders[token]
            if value is None:
                self.missing.add(f"placeholders.{token}")
                complete = False
                continue
            _check_value(token, value)
            if not value.strip():
                raise FillInError(f"placeholders.{token} is empty but the documents use it")
            text = text.replace(f"<PLACEHOLDER:{token}>", value.strip())
        return text, complete

    def _filled(self, text: str, lang: str, doc: str):
        """A variant text with every token filled, or None if a value is unknown or cannot fill it.

        A variant whose values cannot be filled (for example an empty or formatted value of a
        token only an unselected variant uses) cannot be the one in the text; the selected
        variant is still validated by ``fill`` (adversary B5).
        """
        missing_before = set(self.missing)
        try:
            expanded, complete = self._expand_clauses(text, lang, doc)
            result, substituted = self._substitute(expanded)
        except FillInError:
            return None
        finally:
            self.missing = missing_before
        return result if complete and substituted else None

    # -- forks -------------------------------------------------------------
    def _apply_fork(self, name: str, fork: dict, text: str, lang: str, doc: str):
        """(text, selected): the selected variant in place of the one found."""
        table = fork.get(lang)
        if not isinstance(table, dict) or not table:
            raise FillInError(f"fork {name} has no {lang!r} variants")
        found = []
        for key in sorted(table):
            forms = [table[key]]
            filled = self._filled(table[key], lang, doc)
            if filled is not None and filled != table[key]:
                forms.append(filled)
            for form in forms:
                count = text.count(form) if form else 0
                if count > 1:
                    raise FillInError(f"fork {name} ({lang}, {doc}): variant {key!r} occurs {count} times")
                if count == 1:
                    found.append((key, form))
        empty = [k for k in sorted(table) if table[k] == ""]
        if not found and len(empty) == 1:
            # An empty variant is present wherever no other variant is; it cannot be located,
            # so only that same variant can be selected again.
            found.append((empty[0], ""))
        if len(found) != 1:
            keys = [k for k, _ in found] or "none"
            hint = "" if found else f" (a value it uses changed after a fill-in? {REFILL_HINT})"
            raise FillInError(f"fork {name} ({lang}, {doc}): expected exactly one variant in the text, found {keys}{hint}")
        value = self._answer(fork["answer"], lang, fork.get("if_null"))
        if value is None:
            return text, False
        key = _value_key(value, table)
        if key not in table:
            raise FillInError(f"fork {name} ({lang}) has no variant {key!r}")
        if found[0][1] == "":
            if table[key] != "":
                raise FillInError(
                    f"fork {name} ({lang}, {doc}): the answers select {key!r}, but the text was filled with the "
                    f"empty variant {found[0][0]!r} ({REFILL_HINT})"
                )
            return text, True
        return text.replace(found[0][1], table[key], 1), True

    # -- post-condition (a re-run after a fill) ---------------------------
    def clause_problems(self, filled: dict) -> list:
        """Derived clauses whose selected text the filled documents do not carry.

        ``filled`` maps (language, document) to the filled text. For every
        clause table without a ``{value}`` (those values are checked as
        placeholders or inside a fork), the selected non-empty variant must be
        in a document the table applies to, and no other non-empty variant may
        be. For a ``{value}`` table whose answer selects "empty", the literal
        text of its "nonempty" variant must be absent (F1: a value changed to ''
        after a fill). Fails on an answer changed after a fill, which no token
        reveals.
        """
        problems = []
        for token in sorted(self.clauses):
            clause = self.clauses[token]
            for lang in ("en", "ar"):
                by_doc = clause.get(lang)
                if not isinstance(by_doc, dict):
                    continue
                for doc_key, table in sorted(by_doc.items()):
                    if not isinstance(table, dict):
                        continue
                    texts = [t for (lng, d), t in sorted(filled.items()) if lng == lang and doc_key in (d, "*")]
                    if not texts:
                        continue
                    selected = _value_key(self._answer(clause["answer"], lang, clause.get("if_null")), table)
                    if any("{value}" in str(t) for t in table.values()):
                        literal = max((p.strip() for p in str(table.get("nonempty", "")).split("{value}")), key=len)
                        if selected == "empty" and literal and any(literal in t for t in texts):
                            problems.append(
                                f"clause {token} ({lang}, {doc_key}): the answer is empty but the documents carry "
                                f"the 'nonempty' text ({REFILL_HINT})"
                            )
                        continue
                    for key, variant in sorted(table.items()):
                        text = self._filled(variant, lang, doc_key)
                        if not text:
                            continue
                        present = any(text in t for t in texts)
                        if key == selected and not present:
                            problems.append(f"clause {token} ({lang}, {doc_key}): the selected {key!r} text is not in the documents ({REFILL_HINT})")
                        elif key != selected and present:
                            problems.append(f"clause {token} ({lang}, {doc_key}): the documents carry the {key!r} text, the answers select {selected!r} ({REFILL_HINT})")
        return problems

    # -- document ----------------------------------------------------------
    def fill(self, text: str, lang: str, doc: str):
        """The filled document, or None while an answer or value is missing."""
        complete = True
        for name in sorted(self.forks):
            fork = self.forks[name]
            if doc in fork.get("docs", ()):
                text, selected = self._apply_fork(name, fork, text, lang, doc)
                complete = complete and selected
        text, expanded = self._expand_clauses(text, lang, doc)
        text, substituted = self._substitute(text)
        return text if complete and expanded and substituted else None


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FillInError(f"{path}: cannot read JSON ({type(exc).__name__})") from None


def _load_renderer(repo_root: Path):
    path = repo_root / RENDERER_FILE
    spec = importlib.util.spec_from_file_location("_u8_fill_in_renderer", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _unapplied_values(data: dict, filler: _Filler, filled: dict) -> list:
    """Recorded values and selected clause texts the filled documents do not carry.

    A placeholder value must be in a document of its language (keys ending in
    _AR: the Arabic documents; every other key: the English ones). A value no
    selected variant uses is refused as well: record it as null.
    """
    texts = {lang: [t for (lng, _), t in sorted(filled.items()) if lng == lang] for lang in ("en", "ar")}
    problems = []
    for key, value in sorted((data.get("placeholders") or {}).items()):
        if key in filler.clauses or key in ANSWER_PLACEHOLDERS or not isinstance(value, str):
            continue
        if not value.strip():
            if key not in EMPTY_ALLOWED:
                problems.append(
                    f"{key}: an empty string is accepted only for {' and '.join(EMPTY_ALLOWED)} "
                    f"(set it null if no selected variant uses it; {REFILL_HINT} if it was filled before)"
                )
            continue
        lang = "ar" if key.endswith("_AR") else "en"
        if not any(value.strip() in t for t in texts[lang]):
            problems.append(f"{key}: value not in the {lang} documents ({REFILL_HINT}; or set it null if no selected variant uses it)")
    return problems + filler.clause_problems(filled)


def plan(repo_root: Path, data: dict, variants: dict):
    """(missing keys, {source path: (new bytes, old bytes)}); writes nothing."""
    problems = _schema_problems(data)
    if problems:
        raise FillInError("; ".join(problems))
    store_problem = _store_pin_problem(data)
    if store_problem:
        raise FillInError(store_problem)
    missing = {k for k in ANSWER_KEYS if data.get(k) is None}
    missing |= {f"flags.{n}" for n in SEVEN_FLAGS if data["flags"].get(n) is None}
    filler = _Filler(data, variants)
    outputs = {}
    filled_texts = {}
    for (lang, doc), rel in sorted(DOCUMENTS.items()):
        path = repo_root / rel
        if not path.is_file():
            raise FillInError(f"document missing: {rel}")
        raw = path.read_bytes()
        source = raw.decode("utf-8")
        newline = "\r\n" if "\r\n" in source else "\n"
        text = source.replace("\r\n", "\n")
        filled = filler.fill(text, lang, doc)
        if filled is None:
            continue
        if "PLACEHOLDER" in filled:
            raise FillInError(f"{rel}: a malformed PLACEHOLDER mention survives the fill-in")
        filled_texts[(lang, doc)] = filled
        outputs[rel] = (filled.replace("\n", newline).encode("utf-8"), raw)
    missing |= filler.missing
    if not missing:
        problems = _unapplied_values(data, filler, filled_texts)
        if problems:
            raise FillInError("; ".join(problems))
    return sorted(missing), outputs


def _check_pages(renderer, repo_root: Path, outputs: dict) -> None:
    """Render every page's region from the filled sources and split every page, writing nothing.

    Raises FillInError when a page is missing, does not carry exactly one marker pair, or a
    filled source has markdown outside the renderer's subset (adversary B2).
    """
    try:
        for page, src in sorted(renderer.SOURCES.items()):
            text = outputs[src][0].decode("utf-8") if src in outputs else None
            if text is None:
                source = repo_root / src
                if not source.is_file():
                    raise renderer.LegalRenderError(f"source missing: {src}")
                text = source.read_text(encoding="utf-8-sig")
            renderer.render_markdown(text)
            path = repo_root / page
            if not path.is_file():
                raise renderer.LegalRenderError(f"page missing: {page}")
            renderer._split_page(path.read_bytes().decode("utf-8"), page)
    except renderer.LegalRenderError as exc:
        raise FillInError(f"landing renderer: {src}: {exc}") from None


def run(repo_root: Path, data_path: Path, variants_path: Path, dry_run: bool) -> int:
    data = _read_json(data_path)
    variants = _read_json(variants_path)
    missing, outputs = plan(repo_root, data, variants)
    if missing:
        print("missing (nothing written):")
        for key in missing:
            print(f"  {key}")
        return 2
    changed = [rel for rel, (new, old) in sorted(outputs.items()) if new != old]
    try:
        renderer = _load_renderer(repo_root)
    except (OSError, SyntaxError, ImportError) as exc:
        raise FillInError(f"cannot load {RENDERER_FILE} ({type(exc).__name__})") from None
    _check_pages(renderer, repo_root, outputs)
    if dry_run:
        for rel in changed:
            print(f"would write: {rel}")
        return 0
    for rel in changed:
        (repo_root / rel).write_bytes(outputs[rel][0])
        print(f"wrote: {rel}")
    try:
        rendered = renderer.write_regions(repo_root)
    except renderer.LegalRenderError as exc:
        raise RenderAfterWriteError(f"landing renderer after the markdown was written: {exc}") from None
    for page in rendered:
        print(f"rendered: {page}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data", default=None, help=f"default: {DATA_FILE}")
    parser.add_argument("--variants", default=None, help=f"default: {VARIANTS_FILE}")
    parser.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root)
    data_path = Path(args.data) if args.data else repo_root / DATA_FILE
    variants_path = Path(args.variants) if args.variants else repo_root / VARIANTS_FILE
    try:
        return run(repo_root, data_path, variants_path, args.dry_run)
    except FillInError as exc:
        print(f"error (nothing written): {exc}", file=sys.stderr)
        return 3
    except RenderAfterWriteError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
