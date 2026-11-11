"""D16b OPERATOR-INGEST-DATES RED rows (spec S81-G7, unit D16b section 5, as amended by
RULINGS_S81_G7: R-G7-4 the 300 s skew allowance kb_serve.FUTURE_SKEW_SECONDS confirmed;
a captured_at later than now + 300 s is refused with the existing 422 VALIDATION_ERROR;
classify and the coverage readings treat a timestamp beyond the skew as unknown).

No new flag: the rows ride ENABLE_OPERATOR_INGEST (the ingest route), classify (reached
only under ENABLE_KB_FIRST_SERVE in production, called directly here) and
ENABLE_KB_COVERAGE_ROLLUP (the coverage job). The route harness is the frozen D16 RED
file's ``H`` (reached through ``tests.test_s81_d16_operator_ingest``): the real app, the
admin key built at run time, the knob set, a fake service-role client, ``kb_operator._now``
patched to NOW. The classify rows reuse the frozen S18 card builders; the coverage row
reuses the frozen D17 fakes.

Every RED row fails at base on an AssertionError only (a missing constant is read with
getattr and asserted). The PIN rows are green at base and run with the FULL configuration.

Hygiene: pure ASCII, LF; bounded runner only; netguard on; synthetic hosts and identities
only; no key-shaped literal.
"""
from __future__ import annotations

import app.main as app_main  # noqa: I001  (FIRST: the dotenv guard)

import importlib
import json
import logging
from datetime import datetime, timedelta, timezone

import pytest

APP = app_main.app
D16 = "tests.test_s81_d16_operator_ingest"
S18 = "tests.test_s81_s18_kb_first_serve"
D17 = "tests.test_s81_d17_coverage"
FLAG = "ENABLE_OPERATOR_INGEST"
KNOB = "KB_OPERATOR_PAGE_MAX"
COVERAGE_FLAG = "ENABLE_KB_COVERAGE_ROLLUP"
OFF_SPELLINGS = [None, "false", " 0 ", "OFF"]
NOW = datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc)


def _d16():
    return importlib.import_module(D16)


def _s18():
    return importlib.import_module(S18)


def _d17():
    return importlib.import_module(D17)


def _serve():
    return importlib.import_module("app.services.kb_serve")


def _kb():
    from app.services import kb_service as kb
    return kb


def _z(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in (FLAG, KNOB, COVERAGE_FLAG, "KB_FIRST_SERVE_MAX_ASOF_DAYS", "ENABLE_SYNC_DB_OFFLOAD",
                 "KB_COVERAGE_MAX_HOSTS", "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH"):
        monkeypatch.delenv(name, raising=False)
    yield


def _harness(monkeypatch, **kw):
    """The frozen D16 harness plus a counter on every client.table() call."""
    h = _d16().H(monkeypatch, **kw)
    calls = []
    orig = h.client.table

    def _table(name):
        calls.append(name)
        return orig(name)
    h.client.table = _table
    h.table_calls = calls
    return h


def _json(resp):
    try:
        return json.loads(resp.text)
    except ValueError as exc:
        raise AssertionError("not JSON (%s): %s %r" % (type(exc).__name__, resp.status_code, resp.text[:200]))


def _refused_422(resp):
    assert resp.status_code == 422, (resp.status_code, resp.text[:300])
    body = _json(resp)
    assert body.get("success") is False and body.get("code") == "VALIDATION_ERROR", body
    return body


def _accepted(resp):
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    body = _json(resp)
    assert body.get("success") is True, body
    return body


def _ids():
    kb = _kb()
    d16 = _d16()
    pid = d16._pid()
    conc = pid.split("|")[3]
    conc = conc if conc in kb.kb_concentrations() else None
    return pid, conc, kb.kb_variant_key(pid, conc, 100)


def _offer_row(captured):
    d16 = _d16()
    _pid, _conc, vid = _ids()
    return _kb().build_offer_row(variant_id=vid, merchant_id=d16.HOST_A, market="BH", amount=42.5,
                                 observed_currency="BHD", evidence_rung="operator", canonical_url=d16.PDP_A,
                                 captured_at=captured, size_ml=100, in_stock=True)


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r1_skew_constant():
    """R1: kb_serve.FUTURE_SKEW_SECONDS is the int 300 (R-G7-4)."""
    value = getattr(_serve(), "FUTURE_SKEW_SECONDS", None)
    assert isinstance(value, int) and not isinstance(value, bool), value
    assert value == 300, value


def test_r2_future_captured_at_refused(monkeypatch):
    """R2: flag ON, captured_at NOW + 1 d -> 422 VALIDATION_ERROR; the client saw no call."""
    h = _harness(monkeypatch)
    _refused_422(h.post(_d16().INGEST, _d16()._body(captured_at=_z(NOW + timedelta(days=1)))))
    assert h.table_calls == [], h.table_calls
    assert h.client.ops == [], h.client.ops


def test_r3_skew_boundary(monkeypatch):
    """R3: NOW + 301 s -> 422; NOW + 300 s -> 200 and the offer row is the builder's for that instant."""
    h = _harness(monkeypatch)
    _refused_422(h.post(_d16().INGEST, _d16()._body(captured_at=_z(NOW + timedelta(seconds=301)))))
    assert h.client.writes() == [], h.client.writes()
    edge = NOW + timedelta(seconds=300)
    h2 = _harness(monkeypatch)
    _accepted(h2.post(_d16().INGEST, _d16()._body(captured_at=_z(edge))))
    want = _offer_row(edge)
    assert want is not None
    assert want in h2.client.sent("kb_offers"), h2.client.sent("kb_offers")


def test_r4_naive_future_refused(monkeypatch):
    """R4: a naive captured_at one day ahead of the seam is read as UTC and refused."""
    h = _harness(monkeypatch)
    _refused_422(h.post(_d16().INGEST, _d16()._body(captured_at="2026-11-03T06:00:00")))
    assert h.table_calls == [], h.table_calls


def test_r5_reads_the_now_seam(monkeypatch):
    """R5: 2026-11-03T06:00Z is in the real past on any run day after 2026-11-03 but in the
    future of the patched seam (NOW): refused, so the validator reads kb_operator._now."""
    h = _harness(monkeypatch)
    _refused_422(h.post(_d16().INGEST, _d16()._body(captured_at="2026-11-03T06:00:00Z")))
    assert h.table_calls == [], h.table_calls


def _classify(card, *, accepts_asof=False):
    return _serve().classify(card, category="fragrances", region="bahrain", now=NOW, accepts_asof=accepts_asof)


def test_r6_classify_future_only_is_unknown():
    """R6: a card whose only BH / BHD offer was last seen NOW + 1 d serves no price."""
    s18 = _s18()
    pid = s18._pid(s18.P0)
    out = _classify(s18._card(s18.P0, offers=[s18._offer(pid, s18.PDP_A, s18.HOST_A, days=-1)]))
    assert out["price"] is None, out["price"]
    assert out["price_state"] == "none", out["price_state"]
    assert out["candidates"] == [], out["candidates"]


def test_r7_classify_future_never_shadows():
    """R7: a NOW + 2 d offer (99.0) beside a NOW - 1 d offer (42.5): the genuine one is served."""
    s18 = _s18()
    pid = s18._pid(s18.P0)
    future = s18._offer(pid, s18.PDP_A, s18.HOST_A, days=-2, amount=99.0)
    past = s18._offer(pid, s18.PDP_A, s18.HOST_A, days=1, amount=42.5)
    out = _classify(s18._card(s18.P0, offers=[future, past]))
    assert out["price"] is not None, out["price_state"]
    assert out["price"]["amount"] == 42.5, out["price"]
    assert out["price"]["as_of"] == _z(NOW - timedelta(days=1)), out["price"]
    assert len(out["candidates"]) == 1, out["candidates"]


def _coverage_world():
    d17 = _d17()
    t = d17._tables()
    pa, pb = d17.PA, d17.PB
    t["kb_products"] = [p for p in t["kb_products"] if p["id"] in (pa, pb)]
    t["kb_variants"] = [{"id": pa + "|100", "product_id": pa, "size_ml": 100},
                        {"id": pb + "|50", "product_id": pb, "size_ml": 50}]
    t["kb_offers_latest"] = [
        {"variant_id": pa + "|100", "last_seen": d17._iso(NOW + timedelta(days=3)),
         "captured_at": d17._iso(NOW + timedelta(days=3))},
        {"variant_id": pb + "|50", "last_seen": d17._iso(NOW - timedelta(days=1)),
         "captured_at": d17._iso(NOW - timedelta(days=1))},
    ]
    return t


def test_r8_coverage_future_not_fresh_not_aged(monkeypatch, caplog):
    """R8: one product whose only offer is 3 d in the future and one with a 1 d old offer:
    offer_fresh_share 0.5 over n 2; both age medians count only the past value (n 1)."""
    d17 = _d17()
    monkeypatch.setattr(d17._common(), "_now", lambda: NOW)
    _rc, _client, _r, lines = d17._run(monkeypatch, caplog, "true", tables=_coverage_world(), redis=None,
                                       argv=["--day", "2026-11-01"])
    got = d17._metrics(lines)
    assert float(got["kb.field.offer_fresh_share"][0]) == 0.5 and got["kb.field.offer_fresh_share"][1] == 2, got
    assert got["kb.price.age_median_hours"][1] == 1, got["kb.price.age_median_hours"]
    assert float(got["kb.price.age_median_hours"][0]) == 24.0, got["kb.price.age_median_hours"]
    assert got["kb.price.capture_age_median_hours"][1] == 1, got["kb.price.capture_age_median_hours"]


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=["unset", "false", "pad0", "OFF"])
def test_p1_flag_off_404_with_future_body(monkeypatch, value):
    """P1 (PIN): the FULL configuration (key, knob, seam) with the flag OFF: a future-dated
    body answers exactly the never-registered sibling (404 before body validation); without
    the key it is still 404 (never 403: the admin-key dependency is not reached); no client call."""
    d16 = _d16()
    h = _harness(monkeypatch, flag=value)
    body = d16._body(captured_at=_z(NOW + timedelta(days=1)))
    got, want = h.post(d16.INGEST, body), h.post(d16.ABSENT, body)
    assert want.status_code == 404 and _json(want) == {"detail": "Not Found"}, (want.status_code, want.text)
    assert got.status_code == want.status_code and _json(got) == _json(want), (got.status_code, got.text)
    h.send_key = False
    nokey = h.post(d16.INGEST, body)
    assert nokey.status_code == 404 and _json(nokey) == {"detail": "Not Found"}, (nokey.status_code, nokey.text)
    assert h.table_calls == [] and h.client.ops == [] and h.legacy == [], (h.table_calls, h.client.ops, h.legacy)


def test_p2_past_and_absent_unchanged(monkeypatch):
    """P2 (PIN): flag ON: an absent captured_at writes NOW; NOW - 1 d writes the builders'
    offer / image / spec rows for that instant."""
    d16 = _d16()
    kb = _kb()
    pid, _conc, _vid = _ids()
    h = _harness(monkeypatch)
    _accepted(h.post(d16.INGEST, d16._body()))
    assert _offer_row(NOW) in h.client.sent("kb_offers"), h.client.sent("kb_offers")
    past = NOW - timedelta(days=1)
    h2 = _harness(monkeypatch)
    _accepted(h2.post(d16.INGEST, d16._body(captured_at=_z(past))))
    assert _offer_row(past) in h2.client.sent("kb_offers"), h2.client.sent("kb_offers")
    image = kb.build_image_row(product_id=pid, url=d16.IMG_A, provenance_host=d16.HOST_A, source="operator",
                               captured_at=past)
    assert image is not None and image in h2.client.sent("kb_images"), h2.client.sent("kb_images")
    for field, value in (("scent_family", "woody"), ("season", "winter")):
        row = kb.build_spec_row(product_id=pid, field=field, value=value, extractor="operator", captured_at=past,
                                lang="en", source_url=d16.PDP_A, cited=True)
        assert row is not None and row in h2.client.sent("kb_specs"), (field, h2.client.sent("kb_specs"))


def test_p3_within_skew_classify_unchanged():
    """P3 (PIN): last_seen NOW + 4 min -> fresh with that as_of; 6 d -> fresh; 8 d with
    as_of accepted -> asof."""
    s18 = _s18()
    pid = s18._pid(s18.P0)
    near = s18._offer(pid, s18.PDP_A, s18.HOST_A)
    near["last_seen"] = s18._iso(NOW + timedelta(minutes=4))
    out = _classify(s18._card(s18.P0, offers=[near]))
    assert out["price_state"] == "fresh", out["price_state"]
    assert out["price"]["as_of"] == _z(NOW + timedelta(minutes=4)), out["price"]
    out = _classify(s18._card(s18.P0, offers=[s18._offer(pid, s18.PDP_A, s18.HOST_A, days=6)]))
    assert out["price_state"] == "fresh" and out["price"]["amount"] == 42.5, out["price_state"]
    out = _classify(s18._card(s18.P0, offers=[s18._offer(pid, s18.PDP_A, s18.HOST_A, days=8)]), accepts_asof=True)
    assert out["price_state"] == "asof", out["price_state"]
    assert out["price"]["as_of"] == _z(NOW - timedelta(days=8)), out["price"]


def test_p4_coverage_past_world_identical(monkeypatch, caplog):
    """P4 (PIN): the frozen D17 world (no future value) yields the frozen EXPECTED triples."""
    d17 = _d17()
    monkeypatch.setattr(d17._common(), "_now", lambda: NOW)
    _rc, _client, _r, lines = d17._run(monkeypatch, caplog, "true")
    got = d17._metrics(lines)
    assert sorted(got) == sorted(d17.EXPECTED), sorted(set(got) ^ set(d17.EXPECTED))
    for name, (value, n) in d17.EXPECTED.items():
        assert float(got[name][0]) == float(value) and got[name][1] == n, (name, got[name], (value, n))
    caplog.set_level(logging.INFO)
