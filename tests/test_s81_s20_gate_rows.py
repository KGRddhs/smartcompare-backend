"""S81-20 B2-RESULT-GATE-V2 (ENABLE_RESULT_GATE) -- the GREEN-owned gate rows (GATE_S81_20).

G20-GR1 (GC-6): a refusal at an ALREADY-SPENT refusal budget keeps the credit: no refund AND
no record_refusal_async call, on text POST / GET, the stream, URL and the camera.
G20-GR2 (GC-7): the stream settles a refusal in ONE fire-and-forget coroutine scheduled from
the event generator's finally: no Await node inside that finally (base had none), the single
settle label, and the read -> decide -> refund-or-keep -> record -> row sequence.
G20-GR3 (L21): a client that leaves BEFORE the refusal terminal takes the base incomplete arm:
keyless refund, no budget read at the exit, no record, the T5 row, no settle scheduled.
G20-GR4 (RB-S20-3): the stream refusal row carries input_type text_stream under the settle
label usage_refund.text_stream.result_gate (kills the adversary's A8).

The harness (fixtures, ledgers, bodies) is the frozen RED file's, imported by module. Hermetic:
no network, no .env, no credential; synthetic ids. Pure ASCII, LF.
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import textwrap
from types import SimpleNamespace

import pytest

import app.main as app_main  # noqa: F401  FIRST: the dotenv guard (load_dotenv at import)
from app.api import text_routes, url_routes
from app.services import category_gate as cg
from tests import test_s81_s20_result_gate as red

# the RED harness fixtures, re-exported so pytest resolves them in this module
client = red.client
authed = red.authed

SETTLE_LABEL = "usage_refund.text_stream.result_gate"
SPENT = (3600, "2026-11-06T00:00:00+03:00")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in red.CLEAR:
        monkeypatch.delenv(name, raising=False)
    red.scs._DEBUG_STAGE_TIMINGS = None
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    saved = dict(red.app.dependency_overrides)
    try:
        yield
    finally:
        limiter.enabled = prior
        red.scs._DEBUG_STAGE_TIMINGS = None
        red.app.dependency_overrides.clear()
        red.app.dependency_overrides.update(saved)


# =============================================================== G20-GR1 (GC-6)

@pytest.mark.parametrize("site", ["text_post", "text_get", "stream", "url", "camera"])
def test_g20_gr1_spent_budget_no_refund_no_record(monkeypatch, client, authed, site):
    red._prod_on(monkeypatch, red.FLAG)
    # the route's own pre-consume read sees an open budget; the refusal exit sees it spent
    spent = SPENT if site == "url" else [None, SPENT]
    led, resp = red._budget_route(monkeypatch, client, site, spent)
    assert resp.status_code in (200, 400), resp.text[:200]
    reason = "same_identity" if site == "camera" else "no_evidence"
    red._assert_refused_ledger(led, authed["id"], reason, refund=False)
    assert led.refunds == [] and led.anon_refunds == [], (led.refunds, led.anon_refunds)
    assert led.budget_records == [], (site, led.budget_records)
    assert led.budget_reads, (site, led.budget_reads)
    assert not [x for x in led.labels if x.startswith("usage_refund.")
                and x != SETTLE_LABEL], led.labels
    assert led.consumes == [authed["id"]]


# =============================================================== G20-GR2 (GC-7)

def _event_generator_finally():
    src = textwrap.dedent(inspect.getsource(text_routes.text_compare_stream))
    tree = ast.parse(src)
    gens = [n for n in ast.walk(tree)
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "event_generator"]
    assert len(gens) == 1, len(gens)
    tries = [n for n in ast.walk(gens[0]) if isinstance(n, ast.Try) and n.finalbody]
    assert len(tries) == 1, len(tries)
    return tries[0].finalbody


def test_g20_gr2_no_await_in_stream_finally():
    body = _event_generator_finally()
    awaits = [n for stmt in body for n in ast.walk(stmt)
              if isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith))]
    assert awaits == [], [ast.dump(a)[:120] for a in awaits]


def test_g20_gr2_single_settle_label_scheduled_from_finally():
    body = _event_generator_finally()
    calls = [n for stmt in body for n in ast.walk(stmt)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "fire_and_forget" and n.args
             and isinstance(n.args[0], ast.Call) and isinstance(n.args[0].func, ast.Name)
             and n.args[0].func.id == "_s20_stream_settle"]
    assert len(calls) == 1, len(calls)
    labels = [k.value.value for k in calls[0].keywords
              if k.arg == "label" and isinstance(k.value, ast.Constant)]
    assert labels == [SETTLE_LABEL], labels
    src = inspect.getsource(text_routes)
    assert src.count('"' + SETTLE_LABEL + '"') == 1
    assert inspect.iscoroutinefunction(getattr(text_routes, "_s20_stream_settle", None))


def _settle_recorders(monkeypatch, order, *, spent):
    async def _state(subject):
        order.append(("read", subject))
        return SPENT if spent else None

    async def _record(subject):
        order.append(("record", subject))

    async def _refund(user_id, consumed_keys=None):
        order.append(("refund", user_id, consumed_keys))

    async def _row(**kw):
        order.append(("row", kw.get("error_message"), kw.get("success")))

    monkeypatch.setattr(cg, "budget_state_async", _state)
    monkeypatch.setattr(cg, "record_refusal_async", _record)
    monkeypatch.setattr(text_routes, "refund_comparison_credit", _refund)
    monkeypatch.setattr(text_routes, "log_search", _row)


def _settle(frag_on, *, consumed=True):
    user = {"id": "s20-gr2", "access_token": "s20-synthetic"}
    request = SimpleNamespace(state=SimpleNamespace())
    refusal = {"success": False, "code": "INSUFFICIENT_DATA", "reason": "no_evidence",
               "total_cost": 0.0}
    keys = {"daily": "d:s20-gr2", "device_daily": "dv:s20-gr2"}
    asyncio.run(text_routes._s20_stream_settle(
        refusal, request=request, user=user, query="q", usage_consumed=consumed,
        consumed_keys=keys, duration_ms=1, syn={}))
    return user, keys


@pytest.mark.parametrize("case", ["open", "spent", "gate_off"])
def test_g20_gr2_settle_sequence(monkeypatch, case):
    order = []
    if case != "gate_off":
        monkeypatch.setenv("ENABLE_FRAGRANCE_ONLY_GATE", "true")
    _settle_recorders(monkeypatch, order, spent=(case == "spent"))
    user, keys = _settle(case != "gate_off")
    subject = cg.budget_subject(user)
    row = ("row", "result_gate:no_evidence", False)
    if case == "open":
        assert order == [("read", subject), ("refund", user["id"], keys),
                         ("record", subject), row], order
    elif case == "spent":
        assert order == [("read", subject), row], order
    else:
        assert order == [("refund", user["id"], keys), row], order


# =============================================================== G20-GR3 (L21)

def test_g20_gr3_client_gone_before_refusal_terminal(monkeypatch):
    red._prod_on(monkeypatch, red.FLAG, red.TRUTH, red.FRAG)
    led = red._ledger(monkeypatch, text_routes)
    v09 = red.body_v09()
    red._text_svc(monkeypatch, events=[("status", {"progress": 10}), ("settle_complete", v09),
                                       ("complete", v09)])
    user = {"id": "s20-gr3", "access_token": "s20-synthetic"}
    req = red._FakeReq(0)
    req.state = SimpleNamespace()

    async def run():
        resp = await text_routes.text_compare_stream(
            request=req, q=red.FRAG_QUERY, product_a=None, product_b=None, region="bahrain",
            specs=True, reviews=True, pros_cons=True, nocache=True, selected_category=None,
            lang=None, user=user)
        reads_before = len(led.budget_reads)
        async for _c in resp.body_iterator:
            pass
        await asyncio.sleep(0)
        return reads_before

    reads_before = asyncio.run(run())
    assert "usage_refund.text_stream.incomplete" in led.labels, led.labels
    assert SETTLE_LABEL not in led.labels, led.labels
    assert led.refunds == [user["id"]] and led.refund_keys == [None], led.refund_keys
    assert len(led.budget_reads) == reads_before, led.budget_reads
    assert led.budget_records == [], led.budget_records
    assert led.history == [] and led.persist == [] and led.lifetime == []
    assert red._gate_rows(led) == []
    assert [r.get("error_message") for r in led.rows] == ["client_gone_before_complete"], led.rows


# =============================================================== G20-GR4 (RB-S20-3, A8)

def test_g20_gr4_stream_refusal_row_is_text_stream_under_the_settle_label(
        monkeypatch, client, authed):
    """RB-S20-3 (kills A8): the stream refusal's ONE search_logs row carries input_type
    text_stream (never text) and is written by the task scheduled under the settle label."""
    red._prod_on(monkeypatch, red.FLAG)
    led, resp = red._budget_route(monkeypatch, client, "stream", None)
    assert resp.status_code == 200, resp.text[:200]
    rows = red._gate_rows(led)
    assert [r.get("input_type") for r in rows] == ["text_stream"], rows
    assert rows[0].get("error_message") == "result_gate:no_evidence", rows
    assert rows[0].get("success") is False, rows
    assert [x for x in led.labels if x.startswith("usage_refund.")] == [SETTLE_LABEL], led.labels
    assert led.refunds == [authed["id"]] and len(led.budget_records) == 1, led.refunds


def test_g20_gr_url_module_reaches_the_gate_by_attribute():
    """R-S20-30: the URL route reaches result_gate through the module attribute."""
    assert getattr(url_routes, "_rg", None) is red.rgm
