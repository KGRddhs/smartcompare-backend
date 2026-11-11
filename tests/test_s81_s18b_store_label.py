"""S81-G8 S81-18b STORE-LABEL (ENABLE_STORE_LABEL) -- RED and PIN rows.

Spec .qa-s80/S81-G8_UNIT_SPEC.md (unit S81-18b, section 5) as amended by RULINGS_S81_G8
(R-G8-6: the builder kwarg output_lang + the conditional ctx entry in the two
_partial_build_ctx literals, one label in the request's language, EN without the kwarg;
R-G8-7: the url-host second lookup, the retailer string as the fallback; R-G8-8: the 33-host
BH seed, AR = EN in every row, the data file ASCII with \\u escapes, sorted, no URL).
Base daf86d32.

Every RED row fails at base on an AssertionError only (the new leaf is read through
importlib.util.find_spec and asserted; R4 asserts the output_lang keyword in
inspect.signature BEFORE any call carrying it). Every PIN row is green at base and runs with
the FULL companion configuration (ENABLE_KB_FIRST_SERVE ON with both cards, B1 ON,
ENABLE_RESULT_GATE ON, both W4-13 states) plus raising recorders on the leaf (installed
getattr-safely). The flag-OFF golden is the shared tests/fixtures/s81_g8_flag_off_golden.json
(recorded at the base by tests/test_s81_s11b_result_aggregates.py).

Hermetic: app.main imported FIRST; a synthetic label table written to tmp_path and installed
through store_labels.LABELS_PATH + _reset_label_cache(); the Arabic test labels are built with
chr() from code points (no diacritics); synthetic hosts store-a / store-b.example.com.
Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import copy
import importlib
import importlib.util
import inspect
import json
import logging
import os
from pathlib import Path

import pytest

import app.main  # noqa: F401  FIRST: the dotenv guard
from app.services import kb_serve
from app.services import response_builder as rb
import app.services.structured_comparison_service as scs
from tests import test_s81_s18_kb_first_serve as s18

FLAG = "ENABLE_STORE_LABEL"
AGG_FLAG = "ENABLE_RESULT_AGGREGATES"
B1 = "ENABLE_RESULT_STATUS_METADATA"
GATE = "ENABLE_RESULT_GATE"
TRUTH = "ENABLE_SEARCH_LOG_TRUTH"
EXACT = "ENABLE_EXACT_PRICE_GATE"
LEAF = "app.services.store_labels"
ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data" / "merchant_labels.json"
GOLDEN = ROOT / "tests" / "fixtures" / "s81_g8_flag_off_golden.json"
OFF_SPELLINGS = s18.OFF_SPELLINGS
TRUTH_STATES = (None, "true")
CLEARED = tuple(sorted(set(s18.CLEARED_ENV + (FLAG, AGG_FLAG, B1, GATE, TRUTH, EXACT,
                                              "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER"))))
HOST_A, HOST_B = s18.HOST_A, s18.HOST_B
# "<Arabic store word> A" / "... B": the letters meem, teh, jeem, reh (no harakat, no shadda)
AR_WORD = "".join(chr(c) for c in (0x0645, 0x062A, 0x062C, 0x0631))
SYN_ROWS = {
    HOST_A: {"en": "Store A", "ar": AR_WORD + " A"},
    HOST_B: {"en": "Store B", "ar": AR_WORD + " B"},
    "iherb.com": {"en": "iHerb", "ar": AR_WORD + " iHerb"},
}
SEED_HOSTS = (
    "nasserpharmacy.com", "boutiqaat.com", "sephora.me", "bh.asgharali.com", "en-bh.ajmal.com",
    "alhajisbahrain.com", "jalilaperfumes.com", "bahrain.ounass.com", "noon.com",
    "gcc.luluhypermarket.com", "bn.boots.com", "bolo.bh", "bh.jashanmal.com", "klinq.com",
    "bahrain.naseem.com", "bh.mubkhar.com", "bh.taifalemarat.com", "bh.afnan.com",
    "perfumistaaloud.com", "goldencollections.net", "bh-en.smellsoreal.com", "fragrancebh.com",
    "alibaksh.com", "theperfumesclub.com", "bh.arabianoud.com", "ashrafsbahrain.com",
    "bh.oudelite.com", "bdutyfree.com", "reefperfumes.com", "goldenscent.com",
    "bh.azhaperfumes.com", "beautyandblends.com", "en-bh.rituals.com",
)
DIACRITICS = set(range(0x064B, 0x0653)) | {0x0670}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in CLEARED:
        monkeypatch.delenv(name, raising=False)
    seen = getattr(kb_serve, "_SEEN", None)
    if hasattr(seen, "clear"):
        seen.clear()
    yield
    leaf = _leaf_or_none()
    if leaf is not None and callable(getattr(leaf, "_reset_label_cache", None)):
        leaf._reset_label_cache()


def _set(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


def _leaf_or_none():
    try:
        if importlib.util.find_spec(LEAF) is None:
            return None
    except (ImportError, ValueError):
        return None
    return importlib.import_module(LEAF)


def _leaf():
    leaf = _leaf_or_none()
    assert leaf is not None, "app/services/store_labels.py does not exist (S81-18b not implemented)"
    return leaf


def _fn(name):
    f = getattr(_leaf(), name, None)
    assert callable(f), "store_labels.%s is missing" % name
    return f


def _need_kwarg(name):
    params = inspect.signature(rb.build_comparison_response).parameters
    assert name in params, "build_comparison_response has no %s keyword (not implemented)" % name


def _install_table(mp, tmp_path, rows=None, raw=None):
    leaf = _leaf()
    path = tmp_path / "merchant_labels.json"
    if raw is not None:
        path.write_bytes(raw)
    elif rows is not None:
        path.write_text(json.dumps({"version": 1, "labels": rows}, ensure_ascii=True, sort_keys=True),
                        encoding="ascii")
    mp.setattr(leaf, "LABELS_PATH", path)
    _fn("_reset_label_cache")()
    return path


def _fp(name, host):
    return {"brand": "", "name": name, "full_name": name, "category": "fragrances",
            "specs": {"concentration": "EDP", "volume_ml": 100},
            "price": {"amount": 80.0, "currency": "BHD", "retailer": host,
                      "source_method": "page_scrape_jsonld", "url": "https://" + host + "/x"}}


def _pair():
    return [_fp("Item A", HOST_A), _fp("Item B", HOST_B)]


def _build(product_data, **extra):
    params = inspect.signature(rb.build_comparison_response).parameters
    values = {"product_data": product_data, "products": product_data,
              "comparison": {"winner_index": 0, "winner_declaration": "x", "winner_reason": "y",
                             "verdict": "v", "pros": {}, "cons": {}},
              "query": "Item A vs Item B", "region": "bahrain", "total_cost": 0.01, "api_calls": 3}
    kwargs = {n: values[n] for n in params if n in values}
    kwargs.update(extra)
    return rb.build_comparison_response(**kwargs)


def _labels(body):
    prods = [p.get("price") for p in body.get("products") or []]
    over = [p.get("price") for p in (body.get("overview") or {}).get("products") or []]
    return ([p.get("store_label") if isinstance(p, dict) else "<none>" for p in prods],
            [p.get("store_label") if isinstance(p, dict) else "<none>" for p in over])


def _warn(caplog, prefix):
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith(prefix)]


class _BoomPath:
    """A LABELS_PATH whose every access raises (the flag-OFF row: never touched)."""

    def __getattr__(self, name):
        raise RuntimeError("g8 probe: LABELS_PATH touched (%s)" % name)

    def __fspath__(self):
        raise RuntimeError("g8 probe: LABELS_PATH touched (fspath)")

    def __str__(self):
        raise RuntimeError("g8 probe: LABELS_PATH touched (str)")


# ---------------------------------------------------------------- the faked compare (S18 driver)

LIVE_B = {"amount": 55.0, "currency": "BHD", "retailer": HOST_B, "url": "https://" + HOST_B + "/p/1",
          "source_method": "local_bhd", "estimated": False, "title": "x", "in_stock": True}


async def _compare_live_b(mp, kind, *, vision=None, **kw):
    """S18's _compare with slot 1 served live: a store-b price from the faked _get_price."""
    mp.setattr(scs, "STREAM_HARD_CAP_SECONDS", 30.0)
    svc = scs.StructuredComparisonService()
    state = {}
    s18._install(mp, svc, state)

    async def _price(*a, **_k):
        return dict(LIVE_B)
    svc._get_price = _price
    kwargs = dict(kw)
    if vision:
        kwargs["vision_products"] = copy.deepcopy(vision)
    if kind == "rest":
        return await asyncio.wait_for(svc.compare_from_text(s18.QUERY, region="bahrain", nocache=True,
                                                            **kwargs), 60)
    events = []
    async for event in svc.compare_from_text_streaming(s18.QUERY, region="bahrain", nocache=True, **kwargs):
        events.append(list(event))
    return s18._complete(events)


SCENARIOS = {
    "rest_full": ("rest", {}),
    "stream_full": ("stream", {}),
    "camera_full": ("rest", {"vision": s18.VISION}),
    "rest_ar": ("rest", {"output_lang": "ar"}),
}


def _raising_g8_recorders(mp, fired):
    def _boom(name):
        def _f(*a, **k):
            fired.append(name)
            raise AssertionError("G8 OFF: %s called" % name)
        return _f
    mp.setattr(kb_serve, "result_aggregates", _boom("result_aggregates"), raising=False)
    leaf = _leaf_or_none()
    if leaf is not None:
        for name in ("label_prices", "label_for", "load_labels"):
            mp.setattr(leaf, name, _boom(name), raising=False)


def _g8_snapshot(mp, truth):
    s18._full_config(mp, flag="true")
    mp.setenv(B1, "true")
    mp.setenv(GATE, "true")
    _set(mp, TRUTH, truth)
    s18._install_kb(mp, s18._CardClient({s18._pid(s18.P0): s18._card(s18.P0),
                                         s18._pid(s18.P1): s18._card_b()}))
    out = {}
    for name, (kind, kw) in SCENARIOS.items():
        state = {}
        payload = asyncio.run(s18._compare(mp, kind, state=state, **copy.deepcopy(kw)))
        out[name] = s18._normalize({"payload": payload,
                                    "calls": {k: len(v) for k, v in state["calls"].items()}})
    return json.loads(json.dumps(out))


# =============================================================== RED rows

def test_r1_leaf_and_reader(monkeypatch):
    reader = _fn("store_label_enabled")
    for value in (None, "", "false", "0", "garbage", " OFF "):
        _set(monkeypatch, FLAG, value)
        assert reader() is False, value
    for value in (" TRUE ", "1", "yes", "On"):
        monkeypatch.setenv(FLAG, value)
        assert reader() is True, value


def test_r2_table_shape():
    from app.services.deny_hosts import normalize_host
    from app.services.kb_service import KB_HOST_REGEX

    assert TABLE.exists(), "data/merchant_labels.json is missing"
    raw = TABLE.read_bytes()
    assert all(b < 128 for b in raw) and b"\r" not in raw
    data = json.loads(raw.decode("ascii"))
    assert data.get("version") == 1 and isinstance(data.get("labels"), dict)
    labels = data["labels"]
    keys = list(labels)
    assert keys == sorted(keys)
    rx = KB_HOST_REGEX if hasattr(KB_HOST_REGEX, "match") else __import__("re").compile(KB_HOST_REGEX)
    for host, row in labels.items():
        assert host == normalize_host(host) and rx.match(host), host
        assert isinstance(row, dict) and set(row) == {"en", "ar"}, host
        for lang in ("en", "ar"):
            value = row[lang]
            assert isinstance(value, str) and value.strip(), (host, lang)
            assert "/" not in value and ":" not in value and "http" not in value.lower(), (host, lang)
        assert not any(ord(ch) in DIACRITICS for ch in row["ar"]), host
    assert set(SEED_HOSTS) <= set(keys), sorted(set(SEED_HOSTS) - set(keys))
    assert len(SEED_HOSTS) == 33


def test_r3_label_for_lookup_and_lang(monkeypatch, tmp_path):
    _install_table(monkeypatch, tmp_path, SYN_ROWS)
    label_for = _fn("label_for")
    a = {"retailer": HOST_A, "url": "https://" + HOST_A + "/p"}
    assert label_for(a, "en") == "Store A"
    assert label_for(a, None) == "Store A"
    assert label_for(a, "ar") == AR_WORD + " A"
    assert label_for({"retailer": "www.Store-A.example.com:443", "url": None}, "en") == "Store A"
    assert label_for({"retailer": "iHerb", "url": "https://iherb.com/pr/x"}, "en") == "iHerb"
    assert label_for({"retailer": "iHerb", "url": "https://iherb.com/pr/x"}, "ar") == AR_WORD + " iHerb"
    assert label_for({"retailer": "Unknown Shop", "url": "https://unknown.example.org/p"}, "en") == "Unknown Shop"
    assert label_for({"retailer": None, "url": None}, "ar") is None
    assert label_for({"retailer": "", "url": None}, "en") is None


def test_r4_builder_pass_both_surfaces(monkeypatch, tmp_path):
    _need_kwarg("output_lang")
    _install_table(monkeypatch, tmp_path, SYN_ROWS)
    for exact in ("false", "true"):
        monkeypatch.setenv(EXACT, exact)
        monkeypatch.delenv(FLAG, raising=False)
        off = _build(_pair(), output_lang="ar")
        monkeypatch.setenv(FLAG, "true")
        pd = _pair()
        originals = [p["price"] for p in pd]
        on = _build(pd, output_lang="ar")
        want = [AR_WORD + " A", AR_WORD + " B"]
        assert _labels(on) == (want, want), (exact, _labels(on))
        for surface in ("products", "overview"):
            on_p = on["products"] if surface == "products" else on["overview"]["products"]
            off_p = off["products"] if surface == "products" else off["overview"]["products"]
            for i in (0, 1):
                rest = {k: v for k, v in on_p[i]["price"].items() if k != "store_label"}
                assert json.dumps(rest, sort_keys=True) == json.dumps(off_p[i]["price"], sort_keys=True)
        assert all("store_label" not in price for price in originals), exact
        en = _build(_pair(), output_lang="en")
        assert _labels(en) == (["Store A", "Store B"], ["Store A", "Store B"])
        none = _build(_pair())
        assert _labels(none) == (["Store A", "Store B"], ["Store A", "Store B"])


def _orch_setup(mp, tmp_path):
    _install_table(mp, tmp_path, SYN_ROWS)
    s18._full_config(mp, flag="true")
    s18._install_kb(mp, s18._CardClient({s18._pid(s18.P0): s18._card(s18.P0)}))
    mp.setenv(FLAG, "true")


def test_r5_orchestrator_kb_and_live(monkeypatch, tmp_path):
    _orch_setup(monkeypatch, tmp_path)
    en, ar = ["Store A", "Store B"], [AR_WORD + " A", AR_WORD + " B"]
    rest = asyncio.run(_compare_live_b(monkeypatch, "rest"))
    assert rest.get("success") is True, str(rest)[:300]
    assert [p["price"].get("retailer") for p in rest["products"]] == [HOST_A, HOST_B],         [p.get("price") for p in rest["products"]]
    assert _labels(rest) == (en, en), _labels(rest)
    rest_ar = asyncio.run(_compare_live_b(monkeypatch, "rest", output_lang="ar"))
    assert _labels(rest_ar) == (ar, ar), _labels(rest_ar)
    stream_ar = asyncio.run(_compare_live_b(monkeypatch, "stream", output_lang="ar"))
    assert _labels(stream_ar) == (ar, ar), _labels(stream_ar)
    camera = asyncio.run(_compare_live_b(monkeypatch, "rest", vision=s18.VISION))
    assert _labels(camera) == (en, en), _labels(camera)


def _partial_svc(lang):
    svc = scs.StructuredComparisonService()
    ctx = {"query": "Item A vs Item B", "region": "bahrain", "from_cache": False,
           "user_preferences": None, "category_used": "fragrances", "category_switched": False,
           "original_category": None}
    if lang:
        ctx["output_lang"] = lang
    svc._partial_build_ctx = ctx
    svc._partial_product_data = _pair()
    svc._partial_scoring_result = None
    svc._partial_product_names = None
    svc._partial_comparison = None
    return svc


def test_r6_partial_builder_lang_from_ctx(monkeypatch, tmp_path):
    _install_table(monkeypatch, tmp_path, SYN_ROWS)
    monkeypatch.setenv(FLAG, "true")
    ar = _partial_svc("ar")._build_partial_response(elapsed_seconds=1.0)
    assert _labels(ar) == ([AR_WORD + " A", AR_WORD + " B"],) * 2, _labels(ar)
    en = _partial_svc(None)._build_partial_response(elapsed_seconds=1.0)
    assert _labels(en) == (["Store A", "Store B"],) * 2, _labels(en)


def test_r7_fail_safe_table(monkeypatch, tmp_path, caplog):
    _need_kwarg("output_lang")
    leaf = _leaf()
    monkeypatch.setenv(FLAG, "true")
    bad_row = dict(SYN_ROWS)
    bad_row[HOST_A] = {"en": "Store A", "ar": AR_WORD + chr(0x064E) + " A"}
    states = {
        "missing": lambda d: d / "absent.json",
        "invalid": lambda d: _write(d / "invalid.json", b"{not json"),
        "diacritic": lambda d: _write(d / "diacritic.json", json.dumps(
            {"version": 1, "labels": bad_row}, ensure_ascii=True, sort_keys=True).encode("ascii")),
    }
    for name, make in states.items():
        sub = tmp_path / name
        sub.mkdir()
        monkeypatch.setattr(leaf, "LABELS_PATH", make(sub))
        _fn("_reset_label_cache")()
        caplog.clear()
        caplog.set_level(logging.WARNING)
        for _ in range(2):
            body = _build(_pair(), output_lang="en")
            assert _labels(body) == ([HOST_A, HOST_B],) * 2, (name, _labels(body))
        lines = _warn(caplog, "[STORE_LABEL] table unavailable type=")
        assert len(lines) == 1, (name, lines)


def _write(path, data):
    path.write_bytes(data)
    return path


def test_r8_flag_read_first(monkeypatch, caplog):
    _need_kwarg("output_lang")
    leaf = _leaf()
    caplog.set_level(logging.WARNING)
    monkeypatch.setattr(leaf, "LABELS_PATH", _BoomPath())
    _fn("_reset_label_cache")()
    for value in OFF_SPELLINGS:
        _set(monkeypatch, FLAG, value)
        body = _build(_pair(), output_lang="ar")
        assert _labels(body) == ([None, None],) * 2, value
    assert [r for r in caplog.records if "STORE_LABEL" in r.getMessage()] == []
    monkeypatch.setenv(FLAG, "true")

    def _raises(*a, **k):
        raise ValueError("g8 probe")
    monkeypatch.setattr(leaf, "label_prices", _raises)
    body = _build(_pair(), output_lang="ar")
    assert _labels(body) == ([None, None],) * 2
    assert "store_label" not in json.dumps(body)
    assert _warn(caplog, "[STORE_LABEL]") == ["[STORE_LABEL] pass skipped: ValueError"]


def _set_aside_kb_product_ids(got):
    """S81-22c (EC2, R-G10-6): metadata.kb_product_ids is the S81-22c additive key under
    ENABLE_KB_FIRST_SERVE (not a G8 flag). Pop it from every payload's metadata and assert
    its value (the card id of each full or partial slot, else null; absent when no slot
    holds one), so the shared G8 golden (not re-recorded) keeps pinning the G8 flags."""
    ids = [s18._pid(s18.P0), s18._pid(s18.P1)]
    seen = []

    def walk(obj):
        if isinstance(obj, dict):
            meta = obj.get("metadata")
            if isinstance(meta, dict) and isinstance(meta.get("kb_hit"), list):
                marks = meta["kb_hit"]
                want = [ids[i] if m in ("full", "partial") else None for i, m in enumerate(marks)]
                popped = meta.pop("kb_product_ids", None)
                assert popped == (want if any(want) else None), (marks, popped)
                seen.append(marks)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    walk(got)
    assert ["full", "full"] in seen, seen
    return got


# =============================================================== PIN rows

def test_p1_flag_off_golden_full_config(monkeypatch):
    assert GOLDEN.exists(), "the G8 golden is missing"
    want = json.loads(GOLDEN.read_text(encoding="ascii"))["scenarios"]
    for truth in TRUTH_STATES:
        for value in OFF_SPELLINGS:
            _set(monkeypatch, FLAG, value)
            _set(monkeypatch, AGG_FLAG, value)
            fired = []
            _raising_g8_recorders(monkeypatch, fired)
            got = _set_aside_kb_product_ids(_g8_snapshot(monkeypatch, truth))
            exp = want["truth_unset" if truth is None else "truth_" + truth]
            moved = sorted(n for n in SCENARIOS if got.get(n) != exp.get(n))
            assert moved == [], (truth, value, moved)
            assert '"store_label"' not in json.dumps(got) and '"aggregates"' not in json.dumps(got)
            assert fired == [], fired


def test_p2_classify_price_dict_untouched():
    price = s18._classify(s18._card(s18.P0))["price"]
    assert set(price) == {"amount", "currency", "retailer", "url", "source_method", "estimated", "title",
                          "size", "as_of", "_cached", "_cache_source", "in_stock"}, sorted(price)
    assert price["retailer"] == HOST_A


def _prices_frames(mp):
    s18._full_config(mp, flag="true")
    s18._install_kb(mp, s18._CardClient({s18._pid(s18.P0): s18._card(s18.P0),
                                         s18._pid(s18.P1): s18._card_b()}))
    events = asyncio.run(s18._compare(mp, "stream", output_lang="ar"))
    frames = [s18._normalize(p) for kind, p in events if kind == "prices"]
    return json.loads(json.dumps(frames)), s18._complete(events)


def test_p3_sse_prices_frame_unchanged(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    off, _ = _prices_frames(monkeypatch)
    monkeypatch.setenv(FLAG, "true")
    on, _complete_on = _prices_frames(monkeypatch)
    assert off and on == off
    assert "store_label" not in json.dumps(on)
