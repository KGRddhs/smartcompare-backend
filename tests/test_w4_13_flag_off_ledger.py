"""W4-13 flag-OFF call ledger -- the COMMITTED pin (Fable ruling R10).

The HARD rule of W4-13: with ENABLE_SEARCH_LOG_TRUTH, ENABLE_SEARCH_LOG_SYNTHETIC_MARKER
and SEARCH_LOG_SYNTHETIC_TOKEN unset, every log_search site passes EXACTLY the
pre-unit kwargs, fires the same labels and answers with the same bytes. Until
this file the rule was guarded at one site (the camera success-site cost
selector `_truth and comparison_unsuccessful`, adversary r2 mutant X20) only by
a scratch ledger outside the repo. The 45 scenarios are recorded in
tests/fixtures/w4_13_flag_off_ledger.json by
tests/fixtures/_gen_w4_13_flag_off_ledger.py at the PRE-UNIT base, and this test
re-drives them at HEAD and compares RECORD BY RECORD (never by the sha alone).

Fix round 5 (Fable rulings R14/R15): three refund-firing scenarios were added
(42 -> 45) so ruling R2's "flag OFF keeps HEAD's log -> refund order" is pinned
at ALL five reordered sites, not only T1: stream.error_event.authed_consumed
(T4), camera.insufficient.meter_True.authed (T6) and
camera.raise.meter_True.authed (T7). Each record's `labels` is the
fire_and_forget sequence (log_search is fire_and_forget'd too), so mutants N1
(camera.unsuccessful refunds moved before the flag-OFF log), N2 (camera-exception
refunds moved before the flag-OFF log) and N3 (the stream error-event refund
moved before the flag-OFF log) each move one record here. The camera records
also stopped accumulating labels across scenarios (R15).

Mutation X20 (drop `_truth and` at the camera success site) reddens
test_flag_off_ledger_equals_the_pre_unit_recording_record_by_record
(camera.insufficient.meter_False: cost 0 -> 0.02). Since fix round 4 the
"inserts" scenario drives the REAL database_service.log_search (it had recorded
[] under the url scenarios' _Rec patch), so the insert-record mutants INS1
(is_synthetic always written) and INS3 (error_message dropped) redden it too.
INS2 (the flag-2 check dropped, key written whenever is_synthetic is passed) is
NOT this test's to catch: the base writer rejects the is_synthetic kwarg, so no
recorded call passes it; test_log_search_record_flag_off_identical pins it.
"""
from __future__ import annotations

import importlib.util
import json
import os

# The unit test module's autouse guards apply here too: zero network (socket,
# DNS, curl_cffi), both unit flags + the token + the neighbouring route flags
# deleted, the limiter off, app.dependency_overrides restored.
from tests.test_w4_13_measurement_truth import (  # noqa: F401 - autouse fixtures
    _clean_flags,
    _limiter_off,
    _restore_overrides,
    _zero_network,
)

_FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
_LEDGER_JSON = os.path.join(_FIXTURES, "w4_13_flag_off_ledger.json")
_GEN_PATH = os.path.join(_FIXTURES, "_gen_w4_13_flag_off_ledger.py")


def _gen():
    spec = importlib.util.spec_from_file_location("_gen_w4_13_flag_off_ledger", _GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture():
    with open(_LEDGER_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def test_ledger_fixture_names_its_generator_rule_and_45_scenarios():
    """PIN (rulings R10, R14, R15): the fixture header names the generator, the
    recording commit and the rule it pins; it carries EXACTLY 45 uniquely named
    scenarios, and its recorded sha matches its own records (integrity only --
    the assertion that matters is the record-by-record test below).
    Mutations: drop or duplicate a scenario; edit a record without
    regenerating; drop the rule or the generator name."""
    gen = _gen()
    doc = _fixture()
    meta, records = doc["_meta"], doc["records"]
    assert meta["generator"] == "tests/fixtures/_gen_w4_13_flag_off_ledger.py" == gen.GENERATOR
    assert os.path.isfile(_GEN_PATH)
    assert meta["rule"] == gen.RULE
    assert "flag off is byte-identical to the pre-unit kwargs at every log_search site" in meta["rule"].lower()
    assert "ac887e2d" in meta["recorded_at"], meta["recorded_at"]
    assert gen.SCENARIOS == 45
    assert meta["scenarios"] == len(records) == 45, (meta["scenarios"], len(records))
    names = [r["scenario"] for r in records]
    assert len(set(names)) == 45, sorted(n for n in names if names.count(n) > 1)
    assert meta["records_sha256"] == gen.ledger_sha256(records)
    # The "inserts" scenario is not decoration (adversary r3): it holds the
    # four insert records the REAL log_search built, the flag-2 key's site.
    inserts = [r for r in records if r["scenario"] == "inserts"]
    assert len(inserts) == 1 and len(inserts[0]["records"]) == 4, inserts
    assert all("is_synthetic" not in rec for rec in inserts[0]["records"]), inserts
    # R14: the three refund-firing scenarios exist, and the PRE-UNIT recording
    # has the flag-OFF log label BEFORE the refund label in each (R2's order).
    by_name = {r["scenario"]: r for r in records}
    assert set(gen.REFUND_ORDER) == {"stream.error_event.authed_consumed",
                                     "camera.insufficient.meter_True.authed",
                                     "camera.raise.meter_True.authed"}
    for name, (log_label, refund_label) in gen.REFUND_ORDER.items():
        labels = by_name[name]["labels"]
        assert labels.count(log_label) == 1 and labels.count(refund_label) == 1, (name, labels)
        assert labels.index(log_label) < labels.index(refund_label), (name, labels)
        assert len(by_name[name]["calls"]) == 1, (name, by_name[name]["calls"])
    # R15: no camera record carries another scenario's labels -- each one has
    # exactly one log_search label per recorded log_search call.
    for r in records:
        if r["scenario"].startswith("camera."):
            logs = [lb for lb in r["labels"] if lb.startswith("log_search.")]
            assert len(logs) == len(r["calls"]) == 1, (r["scenario"], r["labels"])


def test_flag_off_ledger_equals_the_pre_unit_recording_record_by_record(monkeypatch):
    """PIN (rulings R10 + R14, the committed C7 gate): both unit flags and the
    token deleted, the 45 scenarios re-driven at HEAD equal the pre-unit
    recording record by record -- log_search kwargs in call order, labels (the
    fire_and_forget sequence), status, body and SSE chunks. Mutation X20 (the
    camera success-site `_truth and` guard dropped) reddens
    camera.insufficient.meter_False; N1 / N2 / N3 (a refund moved before the
    flag-OFF log) redden camera.insufficient.meter_True.authed /
    camera.raise.meter_True.authed / stream.error_event.authed_consumed."""
    for name in ("ENABLE_SEARCH_LOG_TRUTH", "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
                 "SEARCH_LOG_SYNTHETIC_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    gen = _gen()
    expected = _fixture()["records"]
    live = gen.build_ledger(monkeypatch)
    assert len(live) == len(expected) == 45, (len(live), len(expected))
    assert [r["scenario"] for r in live] == [r["scenario"] for r in expected]
    moved = []
    for got, want in zip(live, expected):
        if got != want:
            keys = sorted(k for k in set(got) | set(want) if got.get(k) != want.get(k))
            moved.append((want["scenario"], {k: (want.get(k), got.get(k)) for k in keys}))
    assert not moved, (
        f"{len(moved)} of 45 flag-OFF ledger records moved (flag OFF must be byte-identical "
        f"to the pre-unit kwargs at every log_search site): {moved!r}")
