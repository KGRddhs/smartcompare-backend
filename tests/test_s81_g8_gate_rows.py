"""S81-G8 GREEN-owned gate rows (RULINGS_REBASE_S81_G8 RB-G8-3; the adversary's MIN-2,
MIN-3 and MIN-4, survivors OWN-3 / OWN-4 / OWN-6 / OWN-8).

G8-GR1 test_g8_gr1_partial_ctx_output_lang_both_paths (MIN-2, kills OWN-3 / OWN-4): the
REAL ``StructuredComparisonService._partial_build_ctx`` literal, captured at the moment
the service assigns it while the REST path (``compare_from_text``) and the stream path
(``compare_from_text_streaming``) run as the service runs them (the S18 faked-compare
driver), carries ``output_lang`` when the request has a lang and NO such key without
one; the ctx without a lang is the base literal (key order and values), the ctx with a
lang is that literal plus the one entry.

G8-GR2 test_g8_gr2_aggregates_fold_host_case_and_space (MIN-3, kills OWN-6):
``kb_serve.result_aggregates`` counts 'Store-A.example.com ', 'store-a.example.com' and
'STORE-A.EXAMPLE.COM' as ONE host (the strip().lower() fold); a second host makes two.

G8-GR3 test_g8_gr3_label_value_url_guard (MIN-4, kills OWN-8): the store_labels table
validation refuses a value carrying '/', ':' or 'http' (any case): the WHOLE table is
unavailable, ONE WARNING per file state over two builds, and every price renders its
retailer string (the fallback); the valid table labels (the positive control).

OWN-9 (the lang strip / lower in label_for) is the stated limit L-S18b-6
(normalize_output_lang already folds upstream). Synthetic hosts and labels only; netguard
on; pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import logging

import pytest

import app.main  # noqa: F401  FIRST: the dotenv guard
import app.services.structured_comparison_service as scs
from app.services import kb_serve
from tests import test_s81_s18_kb_first_serve as s18
from tests import test_s81_s18b_store_label as s18b

REST_BASE_KEYS = ["query", "region", "from_cache", "user_preferences", "category_used",
                  "category_switched", "original_category"]
STREAM_BASE_HEAD = REST_BASE_KEYS + ["product_categories"]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in s18b.CLEARED:
        monkeypatch.delenv(name, raising=False)
    seen = getattr(kb_serve, "_SEEN", None)
    if hasattr(seen, "clear"):
        seen.clear()
    yield
    leaf = s18b._leaf_or_none()
    if leaf is not None and callable(getattr(leaf, "_reset_label_cache", None)):
        leaf._reset_label_cache()


# ---------------------------------------------------------------- G8-GR1

def _capturing_service(mp, captured):
    base_cls = scs.StructuredComparisonService

    class _Capture(base_cls):
        def __setattr__(self, name, value):
            if name == "_partial_build_ctx" and isinstance(value, dict):
                captured.append(list(value.items()))
            base_cls.__setattr__(self, name, value)

    mp.setattr(scs, "StructuredComparisonService", _Capture)


def _first_ctx(mp, kind, **kw):
    captured = []
    _capturing_service(mp, captured)
    payload = asyncio.run(s18._compare(mp, kind, **kw))
    if kind == "rest":
        assert isinstance(payload, dict) and payload.get("success") is True, str(payload)[:300]
    else:
        s18._complete(payload)
    assert captured, "the %s path never assigned _partial_build_ctx" % kind
    return captured[0]


def test_g8_gr1_partial_ctx_output_lang_both_paths(monkeypatch):
    for kind in ("rest", "stream"):
        plain = _first_ctx(monkeypatch, kind)
        plain_keys = [k for k, _v in plain]
        assert "output_lang" not in plain_keys, (kind, plain_keys)
        if kind == "rest":
            assert plain_keys == REST_BASE_KEYS, plain_keys
        else:
            assert plain_keys[:len(STREAM_BASE_HEAD)] == STREAM_BASE_HEAD, plain_keys
        for lang in ("ar", "en"):
            with_lang = _first_ctx(monkeypatch, kind, output_lang=lang)
            assert [k for k, _v in with_lang] == plain_keys + ["output_lang"], (kind, lang, with_lang)
            assert with_lang[-1] == ("output_lang", lang), (kind, lang)
            assert with_lang[:-1] == plain, (kind, lang)
        none = _first_ctx(monkeypatch, kind, output_lang=None)
        assert none == plain, (kind, none)


# ---------------------------------------------------------------- G8-GR2

def _view(retailers):
    return {"hit": "full",
            "candidates": [{"retailer": r, "as_of": "2026-11-0%dT10:00:00Z" % (i + 1)}
                           for i, r in enumerate(retailers)]}


def test_g8_gr2_aggregates_fold_host_case_and_space():
    folded = ["Store-A.example.com ", "store-a.example.com", "STORE-A.EXAMPLE.COM"]
    got = kb_serve.result_aggregates([_view(folded), _view(folded + ["store-b.example.com"])])
    assert [e["store_count"] for e in got] == [1, 2], got
    assert [list(e) for e in got] == [list(kb_serve.AGGREGATE_FIELDS)] * 2, got
    assert all(e["compare_count"] is None for e in got), got
    assert all(e["price_checked_at"] is not None for e in got), got


# ---------------------------------------------------------------- G8-GR3

def _rows_with(host, lang, value):
    rows = {h: dict(r) for h, r in s18b.SYN_ROWS.items()}
    rows[host][lang] = value
    return rows


def test_g8_gr3_label_value_url_guard(monkeypatch, tmp_path, caplog):
    s18b._need_kwarg("output_lang")
    monkeypatch.setenv(s18b.FLAG, "true")
    a, b = s18b.HOST_A, s18b.HOST_B
    # the positive control: the valid synthetic table labels both surfaces
    s18b._install_table(monkeypatch, tmp_path, s18b.SYN_ROWS)
    good = s18b._build(s18b._pair(), output_lang="en")
    assert s18b._labels(good) == (["Store A", "Store B"],) * 2, s18b._labels(good)
    bad = {
        "slash": (a, "en", "Store" + chr(47) + "A"),
        "colon": (b, "en", "Store" + chr(58) + " B"),
        "http_lower": (a, "ar", s18b.AR_WORD + " http A"),
        "http_upper": (b, "en", "Visit HTTP B"),
    }
    for name, (host, lang, value) in bad.items():
        sub = tmp_path / name
        sub.mkdir()
        s18b._install_table(monkeypatch, sub, _rows_with(host, lang, value))
        caplog.clear()
        caplog.set_level(logging.WARNING)
        for out_lang in ("en", "ar"):
            body = s18b._build(s18b._pair(), output_lang=out_lang)
            assert s18b._labels(body) == ([a, b],) * 2, (name, out_lang, s18b._labels(body))
        lines = s18b._warn(caplog, "[STORE_LABEL] table unavailable type=")
        assert len(lines) == 1, (name, lines)
