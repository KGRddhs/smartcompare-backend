"""INC-H2 STORED-ROW GUARDS (S96-FIX incident lane): the Home smart pick never shows a
cross-size pair or a non-BHD pair.

- Part A (UNFLAGGED, ruled like INC-P2 F4): `home_routes._select_smart_pick` skips a stored
  row whose `metadata.pair_price_sizes.mode` is present and is not `same_size` (the F4 reader
  `_pair_price_sizes_differ`), right after the B1 `_result_status_supported` skip.
- Part B (ENABLE_SMART_PICK_BHD_ONLY, default OFF, read per call by
  `smart_pick_bhd_only_enabled` with the caption reader's env parsing, the FIRST statement of
  its predicate): flag ON skips a row unless BOTH `products[w].price.currency` and
  `products[l].price.currency` == "BHD" exactly (the savings reader's rule, no normalisation).
  Flag OFF is byte-identical to the base and reads no currency.

RED rows fail at the base 8bb97fe0 on an AssertionError only (the part-B reader is read with
getattr); PIN rows are green there. Every row sets or deletes each flag it depends on.
Hermetic: the `comparisons` rows are built here; the route rows drive GET
/api/v1/home/smart-pick through TestClient with the auth dependency overridden and the DB
client factories and the Redis helpers patched on the module. Pure ASCII, LF.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app  # noqa: E402  (first: the dotenv guard)
from app.api import home_routes as hr  # noqa: E402
from app.api.auth_routes import get_current_user  # noqa: E402

client = TestClient(app)

FLAG = "ENABLE_SMART_PICK_BHD_ONLY"
PNL = "ENABLE_PRICE_NOT_LOST"
READER = "smart_pick_bhd_only_enabled"
AMBIENT = (
    "ENABLE_SMART_PICK_VERDICT_CAPTION",
    "ENABLE_FRAGRANCE_ONLY_GATE",
    "ENABLE_ASYNC_REDIS_OFFLOAD",
    "ENABLE_HOME_SAVINGS_AGGREGATE",
)
RECENT = "home.smart_pick.reason.recent_winner"
PRIO = "home.smart_pick.reason.priority_match"
OLD = "2020-01-01T00:00:00Z"
OLDER = "2019-06-01T00:00:00Z"
_MISSING = object()

ON_VALUES = ["true", " TRUE ", "1", "yes", "On"]
OFF_VALUES = [None, "false", " Off "]
# (winner currency, loser currency): every cell is NOT a BHD/BHD pair.
CELLS = [
    pytest.param("USD", "BHD", id="usd-bhd"),
    pytest.param("BHD", "USD", id="bhd-usd"),
    pytest.param(_MISSING, "BHD", id="missing-bhd"),
    pytest.param("bhd", "BHD", id="lower-bhd"),
    pytest.param(" BHD ", "BHD", id="padded-bhd"),
    pytest.param("BHD", None, id="bhd-none"),
]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in (FLAG, PNL) + AMBIENT:
        monkeypatch.delenv(name, raising=False)
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


class _Rec(dict):
    """A price dict that records every key read (the flag-OFF 'reads no currency' recorder)."""

    def __init__(self, data, log):
        super().__init__(data)
        self.log = log

    def get(self, key, default=None):
        self.log.append(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self.log.append(key)
        return super().__getitem__(key)

    def __contains__(self, key):
        self.log.append(key)
        return super().__contains__(key)


def _price(amount, cur, log=None):
    data = {"amount": amount}
    if cur is not _MISSING:
        data["currency"] = cur
    return _Rec(data, log) if log is not None else data


def _row(id_, *, c0="BHD", c1="BHD", metadata=_MISSING, created_at=OLD, prio=False, log=None):
    """A plain v2 row: winner index 0 = Maison A Rose Eau 50 ml (30.5), loser = Maison B
    Oud Noir 50 ml (24.0). prio=True makes the winner the longevity dimension winner."""
    full = {
        "winner_index": 0,
        "products": [
            {"brand": "Maison A", "name": "Rose Eau 50 ml", "price": _price(30.5, c0, log)},
            {"brand": "Maison B", "name": "Oud Noir 50 ml", "price": _price(24.0, c1, log)},
        ],
        "scoring": {"dimension_winners": (
            {"longevity_score": "Maison A Rose Eau 50 ml"} if prio else {}
        )},
    }
    if metadata is not _MISSING:
        full["metadata"] = metadata
    return {"id": id_, "created_at": created_at, "full_response": full}


def _rich_row(id_, *, c0="BHD", c1="BHD", log=None):
    """A row exercising every extension field (winner index 1)."""
    full = {
        "winner_index": 1,
        "category": " fragrance ",
        "products": [
            {"brand": "Maison B", "name": "Oud Noir 50 ml", "price": _price(24.0, c0, log),
             "image_url": "https://img.example.com/oud.jpg"},
            {"brand": "Maison A", "name": "Rose Eau 50 ml", "price": _price(30.5, c1, log),
             "image_url": " https://img.example.com/rose.jpg "},
        ],
        "scoring": {"dimension_winners": {"longevity_score": "Maison A Rose Eau 50 ml"}},
        "overview": {"winner": {"declaration": "Rose Eau lasts longer on skin"}},
        "specs": {"products": [
            {"brand": "Maison B", "name": "Oud Noir 50 ml", "specs": {"volume": "50ml"}},
            {"brand": "Maison A", "name": "Rose Eau 50 ml", "specs": {"size": "50 ml"}},
        ]},
    }
    return {"id": id_, "created_at": OLD, "full_response": full}


# ---- frozen flag-OFF goldens (recorded from the base 8bb97fe0 code, in the payload's key order)
def _plain_golden(cid, reason=RECENT):
    return {
        "comparison_id": cid,
        "winner_name": "Maison A Rose Eau 50 ml",
        "runner_up_name": "Maison B Oud Noir 50 ml",
        "winner_price_bhd": 30.5,
        "runner_up_price_bhd": 24.0,
        "reason_key": reason,
        "reason_params": {"priority": "longevity"} if reason == PRIO else {},
        "category": None,
        "updated_at": "Older",
        "winner_sub": None,
        "runner_up_sub": None,
        "verdict_short": None,
        "winner_image_url": None,
        "runner_up_image_url": None,
    }


def _rich_golden(cid):
    return {
        "comparison_id": cid,
        "winner_name": "Maison A Rose Eau 50 ml",
        "runner_up_name": "Maison B Oud Noir 50 ml",
        "winner_price_bhd": 30.5,
        "runner_up_price_bhd": 24.0,
        "reason_key": PRIO,
        "reason_params": {"priority": "longevity"},
        "category": "fragrance",
        "updated_at": "Older",
        "winner_sub": "50 ml",
        "runner_up_sub": "50ml",
        "verdict_short": "Rose Eau lasts longer on skin",
        "winner_image_url": "https://img.example.com/rose.jpg",
        "runner_up_image_url": "https://img.example.com/oud.jpg",
    }


def _same(got, want):
    """Byte identity of the serialised payload (key order included)."""
    return json.dumps(got) == json.dumps(want)


def _reader():
    fn = getattr(hr, READER, None)
    assert callable(fn), "B0: home_routes.%s (the ENABLE_SMART_PICK_BHD_ONLY reader) is missing" % READER
    return fn


def _route(rows, prefs=None):
    """GET /api/v1/home/smart-pick with the DB reader returning `rows`; returns the JSON body
    and the recorded Redis writes."""
    supa = MagicMock()
    user_resp = MagicMock()
    user_resp.data = {"preferences": prefs or {}}
    comp_resp = MagicMock()
    comp_resp.data = rows

    def _table(name):
        m = MagicMock()
        if name == "users":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        else:
            (m.select.return_value.eq.return_value.eq.return_value
             .order.return_value.limit.return_value.execute.return_value) = comp_resp
        return m

    supa.table.side_effect = _table
    writes = []

    def _rset(key, value, ex=None):
        writes.append((key, value, ex))
        return True

    async def _user():
        return {"id": "h2-user"}

    app.dependency_overrides[get_current_user] = _user
    with patch.object(hr, "get_user_supabase_client", return_value=supa), \
            patch.object(hr, "get_admin_supabase_client", return_value=supa), \
            patch.object(hr, "_redis_get", return_value=None), \
            patch.object(hr, "_redis_set", side_effect=_rset):
        resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer synthetic"})
    assert resp.status_code == 200, resp.text
    return resp.json(), writes


EMPTY = {"smart_pick": None, "empty_state": True, "cta_text_key": "home.smart_pick.empty_cta"}


# =============================================================================
# Part A: the marker skip (unflagged)
# =============================================================================


@pytest.mark.parametrize("mode", ["different_sizes", "unknown"])
def test_a1_stamped_row_alone_is_no_pick(mode):
    """RED: a row stamped different_sizes / unknown is the only candidate -> None."""
    rows = [_row("h2-a1", metadata={"pair_price_sizes": {"mode": mode}})]
    assert hr._select_smart_pick([], rows) is None, "A1: a %s pair is never the smart pick" % mode


@pytest.mark.parametrize("stamped_prio", [True, False], ids=["stamped-prio", "stamped-recent"])
def test_a2_older_unstamped_row_is_picked(stamped_prio):
    """RED: the stamped row is newest; the older unstamped row is picked with its own reason."""
    rows = [
        _row("h2-a2-new", metadata={"pair_price_sizes": {"mode": "different_sizes"}},
             prio=stamped_prio),
        _row("h2-a2-old", created_at=OLDER),
    ]
    pick = hr._select_smart_pick(["longevity"], rows)
    assert pick is not None and pick["comparison_id"] == "h2-a2-old", "A2: the clean older row wins"
    assert pick["reason_key"] == RECENT and pick["reason_params"] == {}, "A2: reason of the older row"


@pytest.mark.parametrize("flag", [None, "true"])
def test_a3_same_size_stamp_picked_as_today(monkeypatch, flag):
    """PIN: a same_size stamp is picked exactly as today (flag OFF and ON)."""
    _set(monkeypatch, FLAG, flag)
    rows = [_row("h2-a3", metadata={"pair_price_sizes": {"mode": "same_size", "w_ml": 50}})]
    assert _same(hr._select_smart_pick([], rows), _plain_golden("h2-a3"))


@pytest.mark.parametrize("metadata", [
    pytest.param({"pair_price_sizes": {"sizes": [50, 100]}}, id="marker-without-mode"),
    pytest.param({"pair_price_sizes": "different_sizes"}, id="marker-str"),
    pytest.param({"pair_price_sizes": ["different_sizes"]}, id="marker-list"),
    pytest.param({"pair_price_sizes": None}, id="marker-none"),
    pytest.param("different_sizes", id="metadata-str"),
    pytest.param(["pair_price_sizes"], id="metadata-list"),
])
def test_a4_malformed_marker_picked_as_today(metadata):
    """PIN: a marker without mode, a non-dict marker or a non-dict metadata is picked as today."""
    rows = [_row("h2-a4", metadata=metadata)]
    assert _same(hr._select_smart_pick([], rows), _plain_golden("h2-a4"))


@pytest.mark.parametrize("pnl", [None, "true"], ids=["pnl-unset", "pnl-on"])
@pytest.mark.parametrize("flag", [None, "false", "true"], ids=["bhd-unset", "bhd-off", "bhd-on"])
def test_a5_marker_skip_holds_under_every_flag(monkeypatch, flag, pnl):
    """RED: the marker skip is unflagged: it holds with ENABLE_SMART_PICK_BHD_ONLY OFF and ON
    and with ENABLE_PRICE_NOT_LOST unset (and set)."""
    _set(monkeypatch, FLAG, flag)
    _set(monkeypatch, PNL, pnl)
    stamped = _row("h2-a5-new", metadata={"pair_price_sizes": {"mode": "different_sizes"}}, prio=True)
    assert hr._select_smart_pick(["longevity"], [stamped]) is None, "A5: stamped alone -> None"
    clean = _row("h2-a5-old", created_at=OLDER)
    pick = hr._select_smart_pick(["longevity"], [stamped, clean])
    assert pick is not None and _same(pick, _plain_golden("h2-a5-old")), "A5: the clean row wins"


def test_a6_marker_read_right_after_the_status_skip(monkeypatch):
    """RED: the marker reader runs after the B1 status test and never for a row the status
    test already skipped (the spec's placement: right after the status skip)."""
    seq = []
    orig_status, orig_marker = hr._result_status_supported, hr._pair_price_sizes_differ

    def _status(full):
        seq.append(("status", id(full)))
        return orig_status(full)

    def _marker(full):
        seq.append(("marker", id(full)))
        return orig_marker(full)

    monkeypatch.setattr(hr, "_result_status_supported", _status)
    monkeypatch.setattr(hr, "_pair_price_sizes_differ", _marker)
    bad = _row("h2-a6-bad", metadata={"result_status": "insufficient_evidence",
                                      "pair_price_sizes": {"mode": "different_sizes"}})
    good = _row("h2-a6-good", created_at=OLDER)
    pick = hr._select_smart_pick([], [bad, good])
    fb, fg = id(bad["full_response"]), id(good["full_response"])
    assert ("marker", fb) not in seq, "A6: a status-skipped row never reaches the marker reader"
    assert ("marker", fg) in seq, "A6: the marker reader is consulted for a supported row"
    assert seq.index(("status", fg)) < seq.index(("marker", fg)), "A6: status first, then marker"
    assert pick is not None and pick["comparison_id"] == "h2-a6-good"


# =============================================================================
# Part B: the currency skip (ENABLE_SMART_PICK_BHD_ONLY)
# =============================================================================


@pytest.mark.parametrize("value,expected", [
    (None, False), ("", False), ("false", False), ("0", False), ("no", False), ("off", False),
    ("garbage", False), ("true", True), (" TRUE ", True), ("1", True), ("yes", True),
    ("on", True), ("On ", True),
])
def test_b0_reader_exists_and_parses_like_the_caption_reader(monkeypatch, value, expected):
    """RED: the reader exists, defaults OFF and parses exactly like
    smart_pick_verdict_caption_enabled (strip, lower, 1/true/yes/on)."""
    fn = _reader()
    _set(monkeypatch, FLAG, value)
    assert fn() is expected
    _set(monkeypatch, "ENABLE_SMART_PICK_VERDICT_CAPTION", value)
    assert hr.smart_pick_verdict_caption_enabled() is expected  # the same parse table


@pytest.mark.parametrize("on", ON_VALUES)
@pytest.mark.parametrize("c0,c1", CELLS)
def test_b1_flag_on_skips_a_non_bhd_pair(monkeypatch, on, c0, c1):
    """RED: flag ON, a pair that is not exactly BHD/BHD is skipped (no normalisation)."""
    _set(monkeypatch, FLAG, on)
    rows = [_row("h2-b1", c0=c0, c1=c1)]
    assert hr._select_smart_pick([], rows) is None, "B1: a non-BHD pair is never the smart pick"


@pytest.mark.parametrize("off", OFF_VALUES, ids=["unset", "false", "padded-off"])
@pytest.mark.parametrize("c0,c1", CELLS)
def test_b2_flag_off_picked_as_today(monkeypatch, off, c0, c1):
    """PIN: flag OFF (unset, false, padded) the same cells are picked byte-identically to the
    frozen base golden, and no currency is read (the predicate reads the flag first)."""
    _set(monkeypatch, FLAG, off)
    _set(monkeypatch, PNL, "true")  # full configuration: the sibling flag present
    log = []
    rows = [_row("h2-b2", c0=c0, c1=c1, log=log)]
    assert _same(hr._select_smart_pick([], rows), _plain_golden("h2-b2"))
    assert "currency" not in log, "B2: flag OFF reads no currency"


@pytest.mark.parametrize("on", ON_VALUES)
def test_b3_flag_on_bhd_pair_picked_as_today(monkeypatch, on):
    """PIN: flag ON with BHD/BHD is picked exactly as today (plain and rich rows)."""
    _set(monkeypatch, FLAG, on)
    assert _same(hr._select_smart_pick([], [_row("h2-b3")]), _plain_golden("h2-b3"))
    assert _same(hr._select_smart_pick(["longevity"], [_rich_row("h2-b3r")]), _rich_golden("h2-b3r"))


@pytest.mark.parametrize("c0,c1", CELLS)
def test_b4_flag_on_older_bhd_row_is_picked(monkeypatch, c0, c1):
    """RED: flag ON, the newest row is non-BHD (and a priority match), an older row is BHD/BHD:
    the older row is picked with its own reason."""
    _set(monkeypatch, FLAG, "true")
    rows = [_row("h2-b4-new", c0=c0, c1=c1, prio=True), _row("h2-b4-old", created_at=OLDER)]
    pick = hr._select_smart_pick(["longevity"], rows)
    assert pick is not None and _same(pick, _plain_golden("h2-b4-old")), "B4: the BHD row wins"


def test_b5_flag_read_per_call(monkeypatch):
    """RED: the flag is read on every call (a flip takes effect without a restart) through the
    module reader."""
    fn = _reader()
    calls = []

    def _spy():
        calls.append(1)
        return fn()

    monkeypatch.setattr(hr, READER, _spy)
    rows = [_row("h2-b5", c0="USD")]
    monkeypatch.setenv(FLAG, "true")
    assert hr._select_smart_pick([], rows) is None, "B5: flag ON skips the USD row"
    first = len(calls)
    assert first >= 1, "B5: the reader is called while selecting"
    monkeypatch.delenv(FLAG)
    assert _same(hr._select_smart_pick([], rows), _plain_golden("h2-b5")), "B5: flag OFF picks it"
    assert len(calls) > first, "B5: read again on the next call"


def test_b6_flag_on_reads_both_currencies(monkeypatch):
    """RED: flag ON, the predicate reads the currency of both prices of a BHD/BHD pair."""
    _set(monkeypatch, FLAG, "true")
    w_log, l_log = [], []
    row = _row("h2-b6")
    products = row["full_response"]["products"]
    products[0]["price"] = _price(30.5, "BHD", w_log)
    products[1]["price"] = _price(24.0, "BHD", l_log)
    assert _same(hr._select_smart_pick([], [row]), _plain_golden("h2-b6"))
    assert "currency" in w_log and "currency" in l_log, "B6: both currencies are read under ON"


# =============================================================================
# Route rows (GET /api/v1/home/smart-pick, DB reader patched)
# =============================================================================


@pytest.mark.parametrize("flag", [None, "true"], ids=["bhd-unset", "bhd-on"])
def test_r1_route_skips_the_stamped_row(monkeypatch, flag):
    """RED: the reader returns [stamped different_sizes row, clean row]; the payload names the
    clean row (part A is unflagged)."""
    _set(monkeypatch, FLAG, flag)
    rows = [
        _row("h2-r1-stamped", metadata={"pair_price_sizes": {"mode": "different_sizes"}}, prio=True),
        _row("h2-r1-clean", created_at=OLDER),
    ]
    body, writes = _route(rows, {"priorities": ["longevity"]})
    assert body["empty_state"] is False
    assert body["smart_pick"]["comparison_id"] == "h2-r1-clean", "R1: the clean row is the pick"
    assert _same(body, {"smart_pick": _plain_golden("h2-r1-clean"), "empty_state": False})


def test_r1b_route_stamped_only_is_empty_state():
    """RED: a stamped row alone yields the empty-state payload."""
    rows = [_row("h2-r1b", metadata={"pair_price_sizes": {"mode": "unknown"}})]
    body, writes = _route(rows)
    assert _same(body, EMPTY), "R1b: no pick from a cross-size pair"


def test_r1c_route_flag_on_skips_the_usd_row(monkeypatch):
    """RED: flag ON, the reader returns [USD row, BHD row]; the payload names the BHD row."""
    _set(monkeypatch, FLAG, "true")
    rows = [_row("h2-r1c-usd", c0="USD", prio=True), _row("h2-r1c-bhd", created_at=OLDER)]
    body, writes = _route(rows, {"priorities": ["longevity"]})
    assert body["smart_pick"] is not None and body["smart_pick"]["comparison_id"] == "h2-r1c-bhd"


@pytest.mark.parametrize("pnl", [None, "true"], ids=["pnl-unset", "pnl-on"])
@pytest.mark.parametrize("off", [None, "false"], ids=["bhd-unset", "bhd-off"])
def test_r2_route_flag_off_byte_identical(monkeypatch, off, pnl):
    """PIN: flag OFF, no stamp: the payload and the cached bytes equal the frozen golden, and
    no currency is read (a USD row stays the pick as today)."""
    _set(monkeypatch, FLAG, off)
    _set(monkeypatch, PNL, pnl)
    log = []
    rows = [_rich_row("h2-r2-rich", c0="USD", log=log), _row("h2-r2-plain", created_at=OLDER, log=log)]
    body, writes = _route(rows, {"priorities": ["longevity"]})
    want = {"smart_pick": _rich_golden("h2-r2-rich"), "empty_state": False}
    assert _same(body, want)
    assert len(writes) == 1
    assert writes[0][0] == "home:smart_pick:h2-user"
    assert writes[0][1] == json.dumps(want), "R2: the cached bytes are the golden's"
    assert writes[0][2] == 300
    assert "currency" not in log, "R2: flag OFF reads no currency"
