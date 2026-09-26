"""Auditable generator for tests/fixtures/w4_13_flag_off_ledger.json (W4-13,
Fable ruling R10: the C7 call ledger becomes a COMMITTED pin).

What it records: the 45 flag-OFF scenarios of the W4-13 call-ledger equality
gate (spec gate 5 as amended by ruling C7), driven through the real routes with
the stub orchestrators of tests/test_w4_13_measurement_truth.py:

  * POST and GET /api/v1/text/compare x {INSUFFICIENT_DATA, TIMEOUT, PARTIAL,
    delivered} x {anonymous, authed}                                   16
  * GET /api/v1/text/compare/stream x {delivered, PARTIAL, STREAM_TIMEOUT
    terminal, INSUFFICIENT_DATA terminal, moderation refusal, error event
    anon / authed-consumed (R14c), pre-verdict disconnect anon /
    authed-consumed, mid-stream raise}                                  10
  * POST /api/v1/image/identify x {delivered, INSUFFICIENT_DATA} x metering
    {off, on}, plus a compare raise, plus INSUFFICIENT_DATA and the compare
    raise AUTHED under metering (R14a/b: the reserved-credit refund fires) 7
  * /api/v1/url/compare x {success, <2 products, LLM_UNAVAILABLE, raise,
    SSRF-blocked}                                                        5
  * POST /api/v1/text/quick x {success, failure, raise}                  3
  * the four admin readers over the fixed 12-row dataset + its failing
    variant                                                              2
  * log_search insert records for four direct calls through the REAL
    database_service.log_search (4 records, asserted non-vacuous)        1
  * scripts/eval_runner.run_eval request headers (MockTransport)         1
                                                                        --
                                                                        45
Each record carries every log_search call's kwargs in call order (duration_ms
replaced by "<int>" after asserting it is an int), the fire_and_forget labels
IN CALL ORDER (log_search is itself fire_and_forget'd, so its label sits in the
same list as the refund's: the list is the side-effect sequence), and the
client-visible status + JSON body (the SSE chunks for the stream).

R14 (the three refund-firing scenarios): ruling R2 says flag OFF keeps HEAD's
log -> refund order at the five sites flag 1 reorders. The POST/GET failure
sites (T1) already fire a refund in the authed scenarios; camera.unsuccessful
(T6), the camera exception (T7) and the stream error event (T4) fired none in
any earlier scenario (all anonymous), so a refund moved before the flag-OFF log
there changed no record. The three R14 records fire it; the generator asserts
the log label and the refund label each fired exactly once (non-vacuity), the
ORDER is recorded in the labels list (a refund moved before the log is a moved
record), and the fixture-header test pins log-before-refund on the committed
records.

R15 (label pile-up): tests/test_retro_w2_1.py::_install wraps whatever
image_routes.fire_and_forget currently is, so under one monkeypatch each camera
scenario's wrapper chained over the previous ones and appended to every earlier
scenario's live label list. The generator now re-binds the REAL
image_routes.fire_and_forget before every camera scenario (the wrapper chain is
unwound) and stores a copy of each scenario's label list, so every record
carries exactly its own labels.
Every TestClient request sends the fixed X-Request-ID, so the error envelopes'
request_id is deterministic. Canonical form: json.dumps(records,
sort_keys=True, ensure_ascii=True, default=str).

THE RULE IT PINS: flag OFF is byte-identical to the pre-unit kwargs at every
log_search site. It is recorded with ENABLE_SEARCH_LOG_TRUTH,
ENABLE_SEARCH_LOG_SYNTHETIC_MARKER and SEARCH_LOG_SYNTHETIC_TOKEN all unset, at
the PRE-UNIT base (a detached scratch worktree at ac887e2d = 61585c58 + the
auth-only #202, with this generator and the helper test module copied in), and
tests/test_w4_13_flag_off_ledger.py re-drives it at HEAD and asserts RECORD BY
RECORD equality. The ON ledger changes by design and is never committed.

Every `app.*` / helper import is LAZY (inside `build_ledger`), so importing this
module never touches app code before tests/conftest.py has neutralised
credentials. Regenerate ONLY through pytest (tests/conftest.py and the network
guard load first), e.g. a throwaway probe file in the repo root's tests/ dir:

    import importlib.util, os
    from tests.test_w4_13_measurement_truth import (  # noqa: F401 (autouse)
        _zero_network, _clean_flags, _limiter_off, _restore_overrides)

    def test_regen(monkeypatch):
        spec = importlib.util.spec_from_file_location(
            "gen", os.path.join("tests", "fixtures", "_gen_w4_13_flag_off_ledger.py"))
        gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
        gen.write_ledger(gen.LEDGER_PATH, gen.build_ledger(monkeypatch),
                         recorded_at="<sha> (how)")

run with `python -m pytest -p qaren_netguard -p no:randomly <probe file>`.
Never run this file as a bare script. A deliberate regeneration is a reviewed
change: say in the PR which scenario moved and why.

Regeneration log:
  * 2026-09-26 first recording at ac887e2d (fix round 3, ruling R10).
  * 2026-09-27 re-recorded at ac887e2d (fix round 4, adversary r3 finding):
    the "inserts" scenario had recorded [] because the url scenarios' _Rec
    patch on database_service.log_search was still active; the generator now
    re-binds the real writer first, so the record holds the 4 insert records.
    The other 41 records are unchanged.
  * 2026-09-27 re-recorded at ac887e2d (fix round 5, Fable rulings R14/R15):
    three scenarios ADDED (stream.error_event.authed_consumed,
    camera.insufficient.meter_True.authed, camera.raise.meter_True.authed:
    42 -> 45), each firing its refund after its flag-OFF log; and four camera
    records' labels MOVED because the wrapper chain is unwound (R15), each now
    exactly its own scenario's single label:
      camera.delivered.meter_False     5 labels -> ['log_search.camera.success']
      camera.insufficient.meter_False  4 labels -> ['log_search.camera.success']
      camera.delivered.meter_True      3 labels -> ['log_search.camera.success']
      camera.insufficient.meter_True   2 labels -> ['log_search.camera.unsuccessful']
    camera.raise (1 label) and the other 37 records are unchanged.
"""
import asyncio
import hashlib
import json
import os

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(FIXTURES_DIR, "w4_13_flag_off_ledger.json")
GENERATOR = "tests/fixtures/_gen_w4_13_flag_off_ledger.py"
RULE = ("flag OFF is byte-identical to the pre-unit kwargs at every log_search site "
        "(ENABLE_SEARCH_LOG_TRUTH, ENABLE_SEARCH_LOG_SYNTHETIC_MARKER and "
        "SEARCH_LOG_SYNTHETIC_TOKEN unset)")
SCENARIOS = 45
UNIT_FLAGS = ("ENABLE_SEARCH_LOG_TRUTH", "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
              "SEARCH_LOG_SYNTHETIC_TOKEN")
# R14: scenario -> (the flag-OFF log label, the refund label that must follow it).
REFUND_ORDER = {
    "stream.error_event.authed_consumed": ("log_search.text_stream.failure",
                                           "usage_refund.text_stream"),
    "camera.insufficient.meter_True.authed": ("log_search.camera.unsuccessful",
                                              "usage_refund.image.comparison_unsuccessful"),
    "camera.raise.meter_True.authed": ("log_search.camera.failure",
                                       "usage_refund.image.comparison_failed"),
}


def _assert_refund_fired(name, labels):
    """R14 non-vacuity: the flag-OFF log AND the refund each fired exactly once.
    Their ORDER is deliberately not asserted here: it is recorded, so a refund
    moved before the log shows up as a moved record in the ledger test (and the
    fixture-header test pins log-before-refund on the committed records)."""
    log_label, refund_label = REFUND_ORDER[name]
    assert labels.count(log_label) == 1 and labels.count(refund_label) == 1, (name, labels)


def _body(r):
    try:
        return r.json()
    except Exception:  # noqa: BLE001 - a non-JSON body is recorded as text
        return r.text


def build_ledger(monkeypatch):
    """The 45 records, in scenario order, as canonical JSON-round-tripped data.

    Deletes the two unit flags + the token itself (the caller's autouse
    `_clean_flags` does too); every other env change goes through
    `monkeypatch`, so nothing leaks out of the calling test."""
    import inspect

    import tests.test_w4_13_measurement_truth as T
    from app.api import image_routes
    from app.services import database_service

    # The REAL writer, captured before any scenario patches it: the url
    # scenarios (T._url) monkeypatch database_service.log_search with a _Rec
    # stub, and that patch is still active when the "inserts" scenario runs.
    real_log_search = database_service.log_search
    assert inspect.iscoroutinefunction(real_log_search), real_log_search
    assert real_log_search.__module__ == "app.services.database_service", real_log_search
    # R15: the REAL camera fire_and_forget, re-bound before every camera
    # scenario so test_retro_w2_1._install wraps it (and only it) each time.
    real_cam_ff = image_routes.fire_and_forget
    assert real_cam_ff.__module__ == "app.utils.async_utils", real_cam_ff

    def _camera(**kw):
        monkeypatch.setattr(image_routes, "fire_and_forget", real_cam_ff)
        r, calls, labels = T._camera(monkeypatch, client, **kw)
        return r, calls, list(labels)

    for name in UNIT_FLAGS:
        monkeypatch.delenv(name, raising=False)
    records = []

    def _rec(name, **kw):
        # R15: every list (labels, calls, chunks) is snapshotted as this
        # record's OWN copy, so a later scenario can never append to it.
        records.append({"scenario": name,
                        **{k: (list(v) if isinstance(v, list) else v) for k, v in kw.items()}})

    client = T.TestClient(T.app, raise_server_exceptions=False)
    for verb in ("post", "get"):
        for name, res in (("insufficient", T.FAIL_ID), ("timeout", T.FAIL_TO),
                          ("partial", T.PARTIAL), ("delivered", T.DELIVERED)):
            r, calls, labels = T._sync(monkeypatch, client, verb, res)
            _rec(f"{verb}.{name}", status=r.status_code, body=_body(r),
                 calls=[T._norm(c) for c in calls], labels=labels)
            r, calls, labels = T._sync(monkeypatch, client, verb, res, user=T.AUTHED)
            _rec(f"{verb}.{name}.authed", status=r.status_code, body=_body(r),
                 calls=[T._norm(c) for c in calls], labels=labels)
    streams = {
        "delivered": dict(events=T._term(T.DELIVERED)),
        "partial": dict(events=T._term(T.PARTIAL)),
        "stream_timeout": dict(events=T._term(T.ST_TERMINAL)),
        "insufficient_terminal": dict(events=T._term(T.ID_TERMINAL)),
        "moderation_refusal": dict(events=T._term(T.MOD_TERMINAL)),
        "error_event": dict(events=[("status", {}), ("error", dict(T.ERR_EVENT))]),
        # R14(c): authed + CONSUMED, so the T4 site's refund fires.
        "error_event.authed_consumed": dict(events=[("status", {}), ("error", dict(T.ERR_EVENT))],
                                            user=T.AUTHED, consumed=True),
        "preverdict_anon": dict(events=T.SIX, disconnect_after=0),
        "preverdict_authed_consumed": dict(events=T.SIX, disconnect_after=0, user=T.AUTHED),
        "midstream_raise": dict(events=T._term(T.DELIVERED), raise_after=1),
    }
    for name, kw in streams.items():
        out = asyncio.run(T._stream(monkeypatch, **kw))
        if f"stream.{name}" in REFUND_ORDER:
            _assert_refund_fired(f"stream.{name}", out["labels"])
        _rec(f"stream.{name}", calls=[T._norm(c) for c in out["calls"]], labels=out["labels"],
             raised=out["raised"], sse=out["chunks"])
    for meter in (False, True):
        for name, kw in (("delivered", dict(result=T.DELIVERED)),
                         ("insufficient", dict(result=T.FAIL_ID))):
            monkeypatch.delenv(T.METER, raising=False)
            r, calls, labels = _camera(meter=meter, **kw)
            _rec(f"camera.{name}.meter_{meter}", status=r.status_code, body=_body(r),
                 calls=[T._norm(c) for c in calls], labels=labels)
    monkeypatch.delenv(T.METER, raising=False)
    r, calls, labels = _camera(raises=True)
    _rec("camera.raise", status=r.status_code, body=_body(r),
         calls=[T._norm(c) for c in calls], labels=labels)
    # R14(a)/(b): authed + metering ON, so `_refund_reserved_credit` fires at
    # the camera.unsuccessful (T6) and camera-exception (T7) sites.
    for name, kw in (("camera.insufficient.meter_True.authed", dict(result=T.FAIL_ID)),
                     ("camera.raise.meter_True.authed", dict(raises=True))):
        monkeypatch.delenv(T.METER, raising=False)
        r, calls, labels = _camera(meter=True, user=T.AUTHED, **kw)
        _assert_refund_fired(name, labels)
        _rec(name, status=r.status_code, body=_body(r),
             calls=[T._norm(c) for c in calls], labels=labels)
    monkeypatch.delenv(T.METER, raising=False)
    # Unwind the last camera wrapper too (R15), before the url scenarios.
    monkeypatch.setattr(image_routes, "fire_and_forget", real_cam_ff)
    for name, kw in (("success", dict(result=T.URL_OK)), ("few", dict(result=T.URL_FEW)),
                     ("llm", dict(result=T.URL_LLM)), ("raise", dict(raises=True)),
                     ("ssrf", dict(result=T.URL_OK, valid=False))):
        r, calls, labels = T._url(monkeypatch, client, **kw)
        _rec(f"url.{name}", status=r.status_code, body=_body(r),
             calls=[T._norm(c) for c in calls], labels=labels)
    for name, kw in (("success", dict(result=T.DELIVERED)), ("failure", dict(result=T.FAIL_ID)),
                     ("raise", dict(raises=True))):
        r, calls, labels = T._quick(monkeypatch, client, **kw)
        _rec(f"quick.{name}", status=r.status_code, body=_body(r),
             calls=[T._norm(c) for c in calls], labels=labels)
    _rec("readers", out=asyncio.run(T._readers(monkeypatch, T._PROBE + T._ORGANIC)))
    _rec("readers.failing", out=asyncio.run(T._readers(monkeypatch, T._PROBE_FAILING + T._ORGANIC)))
    # Re-bind the real writer (adversary r3: without this the four calls below
    # hit the url scenarios' _Rec stub and the scenario recorded []), then
    # capture the insert records its fake Supabase client receives.
    monkeypatch.setattr(database_service, "log_search", real_log_search)
    inserted = T._insert_capture(monkeypatch)

    async def _ins():
        await database_service.log_search(query="q", success=False, error_message="x", duration_ms=5)
        await database_service.log_search(query="q2", user_id="u1", success=True, cost=0.01,
                                          duration_ms=7)
        await database_service.log_search(query="q3", input_type="camera", products_found=["a"])
        await database_service.log_search(query="q4", input_type="text_stream", cost=0.02,
                                          duration_ms=9)
    asyncio.run(_ins())
    assert len(inserted) == 4, f"the inserts scenario must record 4 insert records, got {inserted!r}"
    _rec("inserts", records=inserted)
    _rec("eval_headers", headers=asyncio.run(T._eval_headers()))
    return json.loads(canonical(records))


def canonical(records):
    """The ledger's canonical text (the form the scratch gate hashed)."""
    return json.dumps(records, sort_keys=True, ensure_ascii=True, default=str)


def ledger_sha256(records):
    return hashlib.sha256(canonical(records).encode("ascii")).hexdigest()


def write_ledger(path, records, recorded_at):
    doc = {
        "_meta": {
            "unit": "W4-13 flag-OFF call ledger (spec gate 5 / ruling C7; committed by ruling R10)",
            "generator": GENERATOR,
            "rule": RULE,
            "recorded_at": recorded_at,
            "scenarios": len(records),
            "records_sha256": ledger_sha256(records),
            "canonical_form": "json.dumps(records, sort_keys=True, ensure_ascii=True, default=str); "
                              "duration_ms -> '<int>'; fixed X-Request-ID",
            "compare": "record by record (tests/test_w4_13_flag_off_ledger.py); the sha is a "
                       "secondary integrity check, never the assertion",
        },
        "records": records,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, ensure_ascii=True)
        fh.write("\n")
    return doc
