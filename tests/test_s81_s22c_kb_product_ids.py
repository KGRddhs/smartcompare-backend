"""S81-G10 / S81-22c KB-PRODUCT-IDS (with D-S22-K1) -- RED and PIN rows.

Spec .qa-s80/S81-G10_UNIT_SPEC.md section 22c.5 as amended by RULINGS_S81_G10 (R-G10-5:
D-S22-K1 inside S81-22c with its own RED row; R-G10-7: the key is metadata.kb_product_ids,
written only when at least one slot is a full or partial hit; kb_hit never reshaped; a
both-miss compare carries no key). Base 90d4ed74.

Under ENABLE_KB_FIRST_SERVE the compare body gains the additive sibling key
metadata.kb_product_ids = [slot 0's KB card product id or null, slot 1's or null]; under
ENABLE_COMPARE_RUN_LEDGER compare_runs.build_run_row writes kb_product_ids from it (NULL when
absent or malformed; no kb_service / kb_serve import, the S81-22 P01 fence) and
sources_used.kb_hit accepts the producer vocabulary full / partial / miss (D-S22-K1: the run
row dropped every real hit; 'hit' stays accepted for the frozen synthetic rows).

Every RED row fails at base on an AssertionError only. The seams are the house harnesses,
imported as test-support modules: the S81-18 orchestrator driver (tests/test_s81_s18_kb_first_serve.py:
_compare, _on, _card, _full_config, _golden_snapshot, _raising_recorders) and the S81-22 row
builder / route harness (tests/test_s81_s22_compare_runs.py: _row, body_frag, Rec, _route_world,
_hit, _full; through it tests/test_s81_s20_result_gate.py). Hermetic: no network, no .env, no
credential; synthetic ids. Pure ASCII, LF.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import importlib
import json
from pathlib import Path

import pytest

import app.main  # noqa: F401  FIRST: the dotenv guard (load_dotenv at import)
from tests import test_s81_s18_kb_first_serve as s18
from tests import test_s81_s22_compare_runs as s22

s20 = s22.s20
ROOT = Path(__file__).resolve().parents[1]
CR_PATH = ROOT / "app" / "services" / "compare_runs.py"
KEY = "kb_product_ids"
LEDGER = "ENABLE_COMPARE_RUN_LEDGER"
COMPANIONS = (LEDGER, "ENABLE_RESULT_AGGREGATES", "ENABLE_STORE_LABEL")
OFF_SPELLINGS = [None, "", "false", "0", "off", " FALSE "]
OFF_IDS = ["unset", "empty", "false", "zero", "off", "padded-FALSE"]
GHOST_PID = "fragrance|ghost|miss view|edp"
CLEAR = tuple(sorted(set(s18.CLEARED_ENV + s22.CLEAR + COMPANIONS)))


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in CLEAR:
        monkeypatch.delenv(name, raising=False)
    kbs = importlib.import_module(s18.SERVE)
    seen = getattr(kbs, "_SEEN", None)
    if hasattr(seen, "clear"):
        seen.clear()
    yield
    if hasattr(seen, "clear"):
        seen.clear()


@pytest.fixture
def route_client(request):
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    saved = dict(s20.app.dependency_overrides)
    user = {"id": ("g10c-" + request.node.name)[:120], "email": "g10c@example.test",
            "access_token": "g10c-" + "synthetic"}
    s20.app.dependency_overrides[s20.get_optional_user] = lambda: user
    s20.app.dependency_overrides[s20.get_current_user] = lambda: user
    s20.scs._DEBUG_STAGE_TIMINGS = None
    try:
        yield s20.TestClient(s20.app, raise_server_exceptions=False)
    finally:
        limiter.enabled = prior
        s20.scs._DEBUG_STAGE_TIMINGS = None
        s20.app.dependency_overrides.clear()
        s20.app.dependency_overrides.update(saved)


def _ids():
    return s18._pid(s18.P0), s18._pid(s18.P1)


def _full_full(mp):
    pid0, pid1 = _ids()
    return s18._on(mp, {pid0: s18._card(s18.P0), pid1: s18._card_b()})


def _meta(body):
    return body.get("metadata") or {}


def _walk_has_key(obj, key):
    if isinstance(obj, dict):
        return key in obj or any(_walk_has_key(v, key) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_walk_has_key(v, key) for v in obj)
    return False


def _row_ids(ids):
    body = s22.body_frag()
    body.setdefault("metadata", {})
    if ids is not _ABSENT:
        body["metadata"][KEY] = copy.deepcopy(ids)
    return s22._row(body, "text")[KEY]


def _row_marks(marks):
    body = s22.body_frag()
    body.setdefault("metadata", {})["kb_hit"] = list(marks)
    return s22._row(body, "text")["sources_used"]["kb_hit"]


_ABSENT = object()


# =============================================================== RED rows (R1-R7)

def test_r1_rest_full_full(monkeypatch):
    """R1: KB ON, both cards full (REST): metadata.kb_product_ids == [P0 id, P1 id] (the cards'
    product.id) and metadata.kb_hit == ["full", "full"] unchanged."""
    s18._serve()
    _full_full(monkeypatch)
    body = asyncio.run(s18._compare(monkeypatch, "rest"))
    assert _meta(body).get("kb_hit") == ["full", "full"], _meta(body).get("kb_hit")
    assert _meta(body).get(KEY) == list(_ids()), _meta(body).get(KEY)


def test_r2_stream_full_full(monkeypatch):
    """R2: the stream path: the complete payload carries the same list."""
    s18._serve()
    _full_full(monkeypatch)
    events = asyncio.run(s18._compare(monkeypatch, "stream"))
    complete = s18._complete(events)
    assert _meta(complete).get("kb_hit") == ["full", "full"], _meta(complete).get("kb_hit")
    assert _meta(complete).get(KEY) == list(_ids()), _meta(complete).get(KEY)


def test_r3_partial_miss_and_a_miss_view_id_is_never_served(monkeypatch):
    """R3: slot 0 a partial card, slot 1 no card: [P0 id, None] with kb_hit ["partial", "miss"];
    a MISS view that carries a product id (built here by wrapping classify) still yields None
    (only a full or partial view's pid is an id)."""
    s18._serve()
    pid0, _pid1 = _ids()
    s18._on(monkeypatch, {pid0: s18._card(s18.P0, specs={}, images=[], rating=False)})
    kbs = importlib.import_module(s18.SERVE)
    real = kbs.classify

    def _classify(card, **kw):
        out = real(card, **kw)
        if isinstance(out, dict) and out.get("hit") == "miss":
            out = dict(out, pid=GHOST_PID)
        return out

    monkeypatch.setattr(kbs, "classify", _classify)
    body = asyncio.run(s18._compare(monkeypatch, "rest"))
    assert _meta(body).get("kb_hit") == ["partial", "miss"], _meta(body).get("kb_hit")
    assert _meta(body).get(KEY) == [pid0, None], _meta(body).get(KEY)


def test_r4_camera_path(monkeypatch):
    """R4: the camera compare (vision products) carries the key like kb_hit."""
    s18._serve()
    _full_full(monkeypatch)
    body = asyncio.run(s18._compare(monkeypatch, "rest", vision=s18.VISION))
    assert _meta(body).get("kb_hit") == ["full", "full"], _meta(body).get("kb_hit")
    assert _meta(body).get(KEY) == list(_ids()), _meta(body).get(KEY)


def test_r5_row_from_the_key():
    """R5: build_run_row writes kb_product_ids from metadata.kb_product_ids (two elements);
    an element that is not a str of length 1..256 is nulled while its sibling survives."""
    pid0, pid1 = _ids()
    assert _row_ids([pid0, None]) == [pid0, None]
    assert _row_ids([None, pid1]) == [None, pid1]
    assert _row_ids([pid0, pid1]) == [pid0, pid1]
    assert _row_ids(["x" * 257, pid1]) == [None, pid1]
    assert _row_ids(["", pid1]) == [None, pid1]
    assert _row_ids([1, pid1]) == [None, pid1]
    assert _row_ids(["y" * 256, None]) == ["y" * 256, None]


def test_r6_d_s22_k1_producer_vocabulary():
    """R6 (D-S22-K1): sources_used.kb_hit keeps the producer marks full / partial / miss
    (and the frozen synthetic 'hit'); any other mark, a non-str or a wrong length -> None."""
    assert _row_marks(["full", "miss"]) == ["full", "miss"]
    assert _row_marks(["partial", "partial"]) == ["partial", "partial"]
    assert _row_marks(["full", "full"]) == ["full", "full"]
    assert _row_marks(["miss", "miss"]) == ["miss", "miss"]
    assert _row_marks(["hit", "miss"]) == ["hit", "miss"]
    assert _row_marks(["bogus", "miss"]) is None
    assert _row_marks(["FULL", "miss"]) is None
    assert _row_marks(["full"]) is None
    assert _row_marks(["full", "miss", "miss"]) is None


def test_r7_end_to_end_text_post(monkeypatch, route_client):
    """R7: ENABLE_KB_FIRST_SERVE + ENABLE_COMPARE_RUN_LEDGER ON: the orchestrator's full/miss body
    (the S81-18 driver) through text POST (the S81-22 route harness): the insert recorder's row
    carries kb_product_ids [P0 id, None] and sources_used.kb_hit ["full", "miss"]."""
    s18._serve()
    pid0, _pid1 = _ids()
    s18._on(monkeypatch, {pid0: s18._card(s18.P0)})
    body = asyncio.run(s18._compare(monkeypatch, "rest"))
    assert _meta(body).get("kb_hit") == ["full", "miss"], _meta(body).get("kb_hit")
    s22._full(monkeypatch)
    monkeypatch.setenv(LEDGER, "true")
    rec = s22.Rec(monkeypatch)
    s22._route_world(monkeypatch, "post", body=body)
    resp = s22._hit(route_client, "post")
    assert resp.status_code == 200, resp.text[:300]
    assert rec.labels == ["compare_runs.insert.text"], rec.labels
    row = rec.rows[0]
    assert row["sources_used"]["kb_hit"] == ["full", "miss"], row["sources_used"]
    assert row[KEY] == [pid0, None], row[KEY]


# =============================================================== PIN rows (P1-P5)

@pytest.mark.parametrize("companions", [True, False], ids=["companions-on", "companions-off"])
@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=OFF_IDS)
def test_p1_kb_off_identity(monkeypatch, value, companions):
    """P1 (PIN, the FULL configuration): ENABLE_KB_FIRST_SERVE unset / blank / false / 0 / off /
    padded FALSE with ENABLE_COMPARE_RUN_LEDGER, ENABLE_RESULT_AGGREGATES and ENABLE_STORE_LABEL
    both ON and OFF: no kb_product_ids key anywhere in the REST, stream and camera payloads and
    no KB entry point reached (the S81-18 raising recorders); companions OFF: the payloads equal
    the S81-18 flag-OFF golden (through its own snapshot helper); companions ON (the G8 flags
    stamp their own additive keys, so that golden does not apply, measured at base): every OFF
    spelling yields the payloads of the unset spelling under the same configuration."""
    for name in COMPANIONS:
        if companions:
            monkeypatch.setenv(name, "true")
        else:
            monkeypatch.delenv(name, raising=False)
    fired = []
    s18._raising_recorders(monkeypatch, fired)
    if companions:
        s18._full_config(monkeypatch, flag=None, log_flag=None)
        want = json.loads(json.dumps(s18._golden_snapshot(monkeypatch)))
        assert not _walk_has_key(want, KEY)
    else:
        want = s18._golden()["scenarios"]
    s18._full_config(monkeypatch, flag=value, log_flag=None)
    got = json.loads(json.dumps(s18._golden_snapshot(monkeypatch)))
    moved = sorted(name for name in s18.SCENARIOS if got.get(name) != want.get(name))
    assert moved == [], moved
    assert not _walk_has_key(got, KEY)
    assert fired == [], fired


@pytest.mark.parametrize("case", ["no-cards", "raising-rpc"])
def test_p2_both_miss_no_key(monkeypatch, case):
    """P2 (PIN): KB ON, both slots miss (no card; a raising RPC): no kb_product_ids key (REST
    and stream); kb_hit ["miss", "miss"]."""
    s18._serve()
    if case == "no-cards":
        s18._on(monkeypatch, {})
    else:
        s18._on(monkeypatch, {}, raising=RuntimeError("g10c probe"))
    rest = asyncio.run(s18._compare(monkeypatch, "rest"))
    complete = s18._complete(asyncio.run(s18._compare(monkeypatch, "stream")))
    for body in (rest, complete):
        assert _meta(body).get("kb_hit") == ["miss", "miss"], _meta(body).get("kb_hit")
        assert KEY not in _meta(body), _meta(body).get(KEY)


def test_p3_shapes_never_raise():
    """P3 (PIN): build_run_row on an absent key / a non-list / a wrong length / no surviving
    element writes NULL and never raises."""
    pid0, _pid1 = _ids()
    for ids in (_ABSENT, None, pid0, {"0": pid0}, [pid0], [pid0, None, None], [None, None], ["", None],
                [1, None], ["x" * 257, None], [True, False], [[pid0], None]):
        assert _row_ids(ids) is None, ids


def test_p4_compare_runs_imports_no_kb_module():
    """P4 (PIN): compare_runs.py imports neither kb_service nor kb_serve (top level, lazy or by
    an importlib string): the S81-22 P01 fence."""
    tree = ast.parse(CR_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names = [node.module or ""] + [a.name for a in node.names]
            assert not any(n.endswith(("kb_service", "kb_serve")) for n in names), ast.dump(node)
        elif isinstance(node, ast.Import):
            assert not any(a.name.endswith(("kb_service", "kb_serve")) for a in node.names), ast.dump(node)
        elif isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in ("import_module", "__import__"):
                args = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                assert not any(a.endswith(("kb_service", "kb_serve")) for a in args), ast.dump(node)


def test_p5_ledger_off_no_insert_no_build(monkeypatch, route_client):
    """P5 (PIN): ENABLE_COMPARE_RUN_LEDGER OFF with KB ON: the full/full body through text POST
    schedules no insert and never reaches build_run_row / _insert / _query_hmac (raising stubs)."""
    s18._serve()
    _full_full(monkeypatch)
    body = asyncio.run(s18._compare(monkeypatch, "rest"))
    s22._full(monkeypatch)
    monkeypatch.delenv(LEDGER, raising=False)
    rec = s22.Rec(monkeypatch, raising=True)
    s22._route_world(monkeypatch, "post", body=body)
    resp = s22._hit(route_client, "post")
    assert resp.status_code == 200, resp.text[:300]
    assert rec.labels == [] and rec.rows == [] and rec.db == 0, (rec.labels, rec.db)
