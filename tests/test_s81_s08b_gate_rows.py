"""S81-08b LEGACY-FINGERPRINT-READER: the rebase-round gate rows (RULINGS_REBASE_S81_08B RB8-2 ..
RB8-7), kept in their own file so the frozen RED file (tests/test_s81_s08b_legacy_fingerprint.py,
BLOB sha256 2f4f8237904ce960e7f8de67db4fbda38e765477d78a13b21753b508da2f6a92) keeps its sha256.

Every row reuses the RED file's hermetic harness (the evaluating FakeDB, the FULL unit
configuration fixture `full`, the register / social drivers, the autouse limiter and flag
fixtures), imported exactly as tests/test_s81_s06_router_gate_rows.py reaches its RED file.
Synthetic values only (the RED file's sha256-of-a-fixed-string fingerprints and nil-shaped
uuids, built at run time); every row sets the unit flag itself.

Row map (node prefix -> ruling; the mutants each row must kill):
  test_rb8_2_  RB8-2  drop-path app.* log identity + no value logged   N3, N3b, N3c
  test_rb8_3_  RB8-3  failure table: site x op x exception type        N1, N2
  test_rb8_4_  RB8-4  OTA-precondition wording of the CLAUDE.md row     E12
  test_rb8_5a_ RB8-5a row placement after S81-14 and S81-06             E15
  test_rb8_5b_ RB8-5b the Auth + security hardening bullet              E14
  test_rb8_6_  RB8-6  widened header-name count in auth_routes          E3b
  test_rb8_7_  RB8-7  the legacy accessor reads through .get only       E9

RB8-2 literals: RB8_2_RECORDS below was RECORDED at the rebase main a8f01379 (origin/main =
#374 S81-06) in a DETACHED scratch worktree of that sha, with this file and the RED file
copied in untracked for that one run and removed afterwards, by
    S08B_GATE_ROWS_RECORD=<out.jsonl> <.venv-qaren python> harness/pyt.py --bound 600
        --tag s08b-rb-rb82-record --log <notes>/rb82_record_base.log
        --cwd <scratch worktree of a8f01379> -- tests/test_s81_s08b_gate_rows.py -k rb8_2
and confirmed equal at the rebased HEAD. Recorded: no app.* record at all in the five drop-path
scenarios at either site (the literal is the empty list), and the base rejection INFO line in
the capture-liveness control (RB8_2_LIVENESS: an upper-case primary, so an empty literal can
never pass because the capture saw nothing). A record is (logger name, levelno, getMessage()) for
every record whose logger is `app` or under `app.`; a message carrying a per-call variable is
NORMALISED, never dropped: every uuid (8-4-4-4-12 hex) becomes <uuid> and every duration
(digits with an optional fraction followed by ms or s) becomes <dur> (the regexes _UUID_RE and
_DURATION_RE below). The record hook writes only when S08B_GATE_ROWS_RECORD is set.
"""

import collections.abc
import json
import logging
import os
import re

import httpx
import pytest
from postgrest.exceptions import APIError

from tests.test_s81_s08b_legacy_fingerprint import (  # noqa: F401  (the autouse fixtures + helpers)
    AUTH_LOGGER,
    AUTH_ROUTES_PATH,
    CLAUDE_MD,
    FLAG,
    LEG,
    LEGACY,
    NEW,
    NL,
    PRIMARY,
    REG_BASE,
    REG_BODY,
    ROW_CAP,
    ROW_HEAD,
    SOCIAL_BASE_NULL,
    SOCIAL_BODY,
    FakeDB,
    _debug,
    _no_limiter,
    _Query,
    _reg_seed,
    _register,
    _set_flag,
    _social,
    _social_seed,
    _unit_flag_unset,
    auth_routes,
    full,
)

RECORD_ENV = "S08B_GATE_ROWS_RECORD"
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_DURATION_RE = re.compile(r"\b\d+(?:\.\d+)?(?:ms|s)\b")


def _norm(message):
    return _DURATION_RE.sub("<dur>", _UUID_RE.sub("<uuid>", message))


def _app_records(caplog):
    return [
        [r.name, r.levelno, _norm(r.getMessage())]
        for r in caplog.records
        if r.name == "app" or r.name.startswith("app.")
    ]


def _record_texts(caplog):
    """Every captured record (any logger): getMessage(), msg, repr(args) and exc_text."""
    out = []
    for r in caplog.records:
        out.append(r.getMessage())
        out.append(str(r.msg))
        out.append(repr(r.args))
        if r.exc_text:
            out.append(r.exc_text)
    return out


def _maybe_record(payload):
    path = os.environ.get(RECORD_ENV)
    if path:
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")


# =============================================================================================
# RB8-2 (corr m1): the drop-path app.* log identity at register and at the social apply.
# Five scenarios: flag unset with a valid primary and (i) no legacy header, (ii) a valid
# distinct legacy header; flag ON with (iii) no legacy header, (iv) a 63-char legacy header,
# (v) a legacy header equal to the primary. (a) the ordered app.* record list equals ONE
# literal per site (recorded at a8f01379, see the module docstring); (b) no record carries the
# primary or the legacy value.

RB8_2_RECORDS = {
    "register": [],
    "social": [],
}

RB8_2_SCENARIOS = [
    ("unset-no-legacy", None, None),
    ("unset-valid-legacy", None, "leg"),
    ("on-no-legacy", "true", None),
    ("on-legacy-63", "true", "leg63"),
    ("on-legacy-equal", "true", "equal"),
]


def _legacy_value(kind):
    return {None: None, "leg": LEG, "leg63": LEG[:63], "equal": NEW}[kind]


@pytest.mark.parametrize(
    "scenario,flag,legacy_kind", RB8_2_SCENARIOS, ids=[s[0] for s in RB8_2_SCENARIOS]
)
@pytest.mark.parametrize("site", ["register", "social"])
def test_rb8_2_drop_path_log_identity(full, caplog, site, scenario, flag, legacy_kind):
    _debug(caplog)
    _set_flag(full, flag)
    headers = {PRIMARY: NEW}
    legacy = _legacy_value(legacy_kind)
    if legacy is not None:
        headers[LEGACY] = legacy
    if site == "register":
        db = FakeDB(_reg_seed())
        resp, factory = _register(db, headers)
        body, calls = REG_BODY, REG_BASE
    else:
        db = FakeDB(_social_seed())
        resp, factory = _social(db, headers)
        body, calls = SOCIAL_BODY, SOCIAL_BASE_NULL
    records = _app_records(caplog)
    _maybe_record({"site": site, "scenario": scenario, "records": records})
    assert resp.status_code == 200, resp.text
    assert resp.json() == body
    assert db.calls == calls, db.calls
    assert factory.call_count == 1
    # (b) no record (any logger) carries the primary or the legacy value (checked first, so a
    # value leak reports as (b) even where (a) would also fail)
    values = [NEW, LEG[:63]] + ([legacy] if legacy else [])
    for text in _record_texts(caplog):
        for value in values:
            assert value not in text, (site, scenario, "a log record carries a fingerprint value")
    # (a) the ordered app.* record list equals the site's base-recorded literal
    assert records == RB8_2_RECORDS[site], (site, scenario, records)


# The capture-liveness control of RB8-2 (so an empty literal can never pass vacuously): the same
# harness with an INVALID primary (upper case) logs the base rejection line at both sites
# (recorded at a8f01379 with the rows above).
RB8_2_LIVENESS = [
    [AUTH_LOGGER, logging.INFO, "device-fp header rejected: invalid format (expected 64-char hex), len=64"]
]


@pytest.mark.parametrize("site", ["register", "social"])
def test_rb8_2_capture_liveness(full, caplog, site):
    _debug(caplog)
    _set_flag(full, None)
    headers = {PRIMARY: NEW.upper(), LEGACY: LEG}
    if site == "register":
        resp, factory = _register(FakeDB(_reg_seed()), headers)
    else:
        resp, factory = _social(FakeDB(_social_seed()), headers)
    records = _app_records(caplog)
    _maybe_record({"site": site, "scenario": "liveness-invalid-primary", "records": records})
    assert resp.status_code == 200, resp.text
    assert factory.call_count == 0
    assert records == RB8_2_LIVENESS, (site, records)


# =============================================================================================
# RB8-3 (corr m2): the failure table. Flag ON, a valid primary and a valid distinct legacy
# header; the dual read (op in_) or the dual update (op update) raises one of three exception
# types. The response is the no-failure response; exactly ONE new app.* record, the typed
# WARNING; a read failure writes nothing; an update failure is not retried; the exception
# text (which carries both values) reaches no record.


class _TypedFailQuery(_Query):
    def execute(self, *args, **kwargs):
        if self.db.fail_op in self.used:
            self._step("execute", args, kwargs)
            raise self.db.fail_exc
        return super().execute(*args, **kwargs)


class TypedFailDB(FakeDB):
    """The RED FakeDB whose query raises `fail_exc` (any type) when it used `fail_op`
    (in_ = the dual read, update = the dual write): the raise_on vocabulary gains `update`
    and a typed exception."""

    def __init__(self, tables, fail_op, fail_exc):
        super().__init__(tables)
        self.fail_op = fail_op
        self.fail_exc = fail_exc

    def table(self, *args, **kwargs):
        self.record("table", args, kwargs)
        return _TypedFailQuery(self, args[0])


RB8_3_SENTINEL = "s81-08b-rb8-3 boom"


def _rb8_3_exc(name):
    msg = RB8_3_SENTINEL + " " + LEG + " " + NEW
    if name == "RuntimeError":
        return RuntimeError(msg)
    if name == "APIError":
        return APIError({"message": msg, "code": "PGRST000", "hint": None, "details": msg})
    if name == "ConnectError":
        return httpx.ConnectError(msg)
    raise AssertionError(name)


@pytest.mark.parametrize("exc_name", ["RuntimeError", "APIError", "ConnectError"])
@pytest.mark.parametrize("op", ["in_", "update"])
@pytest.mark.parametrize("site", ["register", "social"])
def test_rb8_3_failure_table(full, caplog, site, op, exc_name):
    _debug(caplog)
    _set_flag(full, "true")
    exc = _rb8_3_exc(exc_name)
    assert type(exc).__name__ == exc_name
    headers = {PRIMARY: NEW, LEGACY: LEG}
    if site == "register":
        db = TypedFailDB(_reg_seed(), op, exc)
        resp, _ = _register(db, headers)
        body = REG_BODY
    else:
        db = TypedFailDB(_social_seed(), op, exc)
        resp, _ = _social(db, headers)
        body = SOCIAL_BODY
    assert resp.status_code == 200, resp.text
    assert resp.json() == body
    assert ["in_", ["device_fingerprint_hash", [NEW, LEG]]] in db.calls, "the dual read never ran"
    expected = RB8_2_RECORDS[site] + [
        [AUTH_LOGGER, logging.WARNING, "[LEGACY-FP] site=" + site + " inherit failed: " + exc_name]
    ]
    assert _app_records(caplog) == expected, _app_records(caplog)
    update_calls = [c for c in db.calls if c[0] == "update"]
    if op == "in_":
        assert update_calls == [], "a failed dual read writes nothing"
    else:
        assert len(update_calls) == 1, "an update failure is not followed by a second write"
    assert db.updates == []
    for text in _record_texts(caplog):
        for value in (RB8_3_SENTINEL, NEW, LEG):
            assert value not in text, (site, op, exc_name, "the exception text reached a record")


# =============================================================================================
# CLAUDE.md rows (eng m2, m3): the S81-08b row slice exactly as R11 bounds it.


def _claude_text():
    return CLAUDE_MD.read_text(encoding="utf-8")


def _row_slice(text):
    at = text.find(NL + ROW_HEAD)
    assert at != -1, "no column-0 SESSION 81 flag (S81-08b ...) paragraph in CLAUDE.md"
    start = at + 1
    ends = [
        i
        for i in (text.find(NL + "**SESSION", start), text.find(NL + "## ", start))
        if i != -1
    ]
    end = min(ends) if ends else len(text)
    row = text[start:end]
    assert len(row) <= ROW_CAP, ("the row slice is not bounded (R-S08B-9)", len(row))
    return row


RB8_4_REQUIRED = (
    "The OTA precondition is the DATED ledger line of this flip ON",
    "never the merge",
)
RB8_4_FORBIDDEN = (
    "precondition is the merge",
    "precondition is merging",
    "precondition is the merged",
)


def test_rb8_4_ota_precondition_wording():
    row = _row_slice(_claude_text())
    for fragment in RB8_4_REQUIRED:
        assert fragment in row, ("RB8-4 fragment", fragment)
    low = row.lower()
    for bad in RB8_4_FORBIDDEN:
        assert bad not in low, ("RB8-4 forbidden", bad)


HEAD_S14 = "**SESSION 81 unit (S81-14 KB-SCHEMA"
HEAD_S06 = "**SESSION 81 flags (S81-06 ANTHROPIC-ROUTER"


def test_rb8_5a_row_placement():
    text = _claude_text()
    for head in (HEAD_S14, HEAD_S06, ROW_HEAD):
        assert text.count(NL + head) == 1, ("RB8-5a one column-0 head", head)
    i14 = text.find(NL + HEAD_S14)
    i06 = text.find(NL + HEAD_S06)
    i8b = text.find(NL + ROW_HEAD)
    assert i14 < i06 < i8b, ("RB8-5a order S81-14 < S81-06 < S81-08b", i14, i06, i8b)
    nxt = text.find(NL + "## ", i8b + 1)
    assert nxt != -1
    assert text[nxt + 1:].split(NL, 1)[0] == "## Tests", text[nxt + 1:nxt + 40]


AUTH_BULLET_START = "- **`X-Device-Fingerprint`** must match"


def test_rb8_5b_auth_bullet():
    lines = [ln for ln in _claude_text().split(NL) if ln.startswith(AUTH_BULLET_START)]
    assert len(lines) == 1, ("RB8-5b exactly one Auth bullet line", len(lines))
    line = lines[0]
    for fragment in ("`X-Device-Fingerprint-Legacy`", "S81-08b", "silently dropped when invalid or equal"):
        assert fragment in line, ("RB8-5b fragment", fragment)


# =============================================================================================
# RB8-6 (eng m4): the widened names rule over auth_routes (case-insensitive; the frozen P14 /
# S81-05 p07 exact-literal counts stay as they are).

_GET_PRIMARY_RE = re.compile(r"""request\.headers\.get\(\s*(["'])x-device-fingerprint\1""", re.IGNORECASE)
_GET_LEGACY_RE = re.compile(r"""request\.headers\.get\(\s*(["'])x-device-fingerprint-legacy\1""", re.IGNORECASE)
_SUBSCRIPT_RE = re.compile(r"""headers\s*\[\s*(["'])x-device-fingerprint(?:-legacy)?\1""", re.IGNORECASE)


def test_rb8_6_widened_header_names():
    text = AUTH_ROUTES_PATH.read_text(encoding="utf-8")
    assert len(_GET_PRIMARY_RE.findall(text)) == 1, "RB8-6: one primary header read"
    assert len(_GET_LEGACY_RE.findall(text)) == 1, "RB8-6: one legacy header read"
    assert _SUBSCRIPT_RE.findall(text) == [], "RB8-6: no headers[...] subscript of either name"


# =============================================================================================
# RB8-7 (eng m5): the legacy accessor reads through Mapping.get ONLY (GC-3).


class _RecordingMapping(collections.abc.Mapping):
    """A header mapping whose every accessor records; get returns WITHOUT __getitem__."""

    def __init__(self, values):
        self._values = dict(values)
        self.calls = []

    def get(self, key, default=None):
        self.calls.append(("get", key))
        return self._values.get(key, default)

    def __getitem__(self, key):
        self.calls.append(("__getitem__", key))
        return self._values[key]

    def __contains__(self, key):
        self.calls.append(("__contains__", key))
        return key in self._values

    def __iter__(self):
        self.calls.append(("__iter__", None))
        return iter(list(self._values))

    def __len__(self):
        self.calls.append(("__len__", None))
        return len(self._values)

    def keys(self):
        self.calls.append(("keys", None))
        return list(self._values)

    def items(self):
        self.calls.append(("items", None))
        return list(self._values.items())

    def values(self):
        self.calls.append(("values", None))
        return list(self._values.values())


class _MappingRequest:
    def __init__(self, mapping):
        self._mapping = mapping

    @property
    def headers(self):
        return self._mapping


def test_rb8_7_legacy_accessor_get_only(monkeypatch):
    _set_flag(monkeypatch, "true")
    mapping = _RecordingMapping({LEGACY: LEG, PRIMARY: NEW})
    got = auth_routes._read_valid_legacy_fingerprint(_MappingRequest(mapping), NEW)
    assert mapping.calls == [("get", LEGACY)], mapping.calls
    assert got == LEG
