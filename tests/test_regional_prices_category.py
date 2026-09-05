# -*- coding: utf-8 -*-
"""#56 — `get_regional_prices` must resolve under the query's REAL category.

`get_regional_prices` is the resolver behind the public
`GET /api/v1/text/prices/{product}`. On main it fans out six `_get_price`
calls with NO `category` argument, so all six resolve under that parameter's
`"other"` default, while the compare path resolves the very same product under
its inferred category. That default drives three things inside `_get_price`:

  * `set_resolved_price_category(category)` — the per-task ContextVar every
    downstream extractor reads,
  * `build_size_aware_price_cache_key(..., category=category)` — the WRITE key,
  * every `should_cache_price(..., category)` write gate, whose electronics
    accessory veto only fires when the category literally says "electronics".

So a charger/case listing resolved under a phone query passes a veto that was
supposed to stop it, and lands in the same keyspace the compare path reads.

The route ALREADY computes the right category — but after the gather, and only
for the DISPLAY gate. This pins the hoist + the thread-through behind
ENABLE_REGIONAL_PRICES_CATEGORY (default OFF), in BOTH directions:

  ON  — all six calls carry the inferred category, coerced to `_get_price`'s own
        `"other"` default when the inference returns None.
  OFF — the call is byte-identical to main: `category` is not passed AT ALL,
        not even as the string "other" (a monkeypatched `_get_price` must see
        the exact same argument tuple it sees today).

And in both directions the DISPLAY gate keeps receiving the RAW Optional[str]
inference (None included) that it receives today — this issue must not move the
display gate, only the write path.
"""
import asyncio

import pytest

import app.services.structured_comparison_service as scs
import app.services.price_service as ps


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def _run(monkeypatch, search_query, flag_value):
    """Drive get_regional_prices with _get_price / is_price_showable recorded.

    Returns (price_calls, showable_categories, infer_call_count) where
    price_calls is a list of (positional_args_after_self, kwargs) per region.
    """
    price_calls = []
    showable_categories = []
    infer_calls = []

    async def _fake_get_price(self, *args, **kwargs):
        price_calls.append((args, dict(kwargs)))
        # No "amount" key -> the display gate below still runs (unavailable is
        # not True) but _convert_to_bhd is never reached.
        return {"currency": "BHD", "size": None}

    def _fake_showable(query, price, category, enforce_correctness=False):
        showable_categories.append(category)
        return True

    _real_infer = ps._infer_category_from_query

    def _counting_infer(q):
        infer_calls.append(q)
        return _real_infer(q)

    if flag_value is None:
        monkeypatch.delenv("ENABLE_REGIONAL_PRICES_CATEGORY", raising=False)
    else:
        monkeypatch.setenv("ENABLE_REGIONAL_PRICES_CATEGORY", flag_value)

    monkeypatch.setattr(
        scs.StructuredComparisonService, "_get_price", _fake_get_price, raising=True
    )
    monkeypatch.setattr(scs, "is_price_showable", _fake_showable, raising=True)
    monkeypatch.setattr(scs, "_infer_category_from_query", _counting_infer, raising=True)

    result = asyncio.run(
        scs.get_regional_prices("Apple", "iPhone 15 Pro", "256GB", search_query)
    )
    assert set(result["regional_prices"].keys()) == set(scs.GCC_REGIONS.keys())
    return price_calls, showable_categories, infer_calls


_ELECTRONICS_Q = "apple iphone 15 pro 256gb"
# `_infer_category_from_query` returns None for this one (no detector matches);
# verified against the real function in test_uncategorised_query_infers_none.
_UNCATEGORISED_Q = "Acme Widget"


def test_uncategorised_query_infers_none():
    """Guard the fixture itself: the 'no category' query must really infer None,
    and the electronics query must really infer 'electronics'. If a detector
    ever starts matching these strings, the coercion tests below would silently
    stop testing coercion."""
    assert ps._infer_category_from_query(_UNCATEGORISED_Q) is None
    assert ps._infer_category_from_query(_ELECTRONICS_Q) == "electronics"


# ---------------------------------------------------------------------------
# FLAG ON — the fix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flag", ["true", "1", "yes", "on", "TRUE", " True "])
def test_flag_on_threads_electronics_into_all_six_calls(monkeypatch, flag):
    calls, _showable, _infer = _run(monkeypatch, _ELECTRONICS_Q, flag)
    assert len(calls) == 6, "one _get_price per GCC region"
    for args, kwargs in calls:
        assert kwargs.get("category") == "electronics", (args, kwargs)


def test_flag_on_coerces_none_inference_to_the_str_default(monkeypatch):
    """`_get_price` is typed `category: str = "other"`; the inference is
    Optional[str]. Passing None would publish None into the ContextVar and the
    cache key — the coercion must hand it the parameter's own default."""
    calls, _showable, _infer = _run(monkeypatch, _UNCATEGORISED_Q, "true")
    assert len(calls) == 6
    for args, kwargs in calls:
        assert "category" in kwargs
        assert kwargs["category"] == "other"
        assert kwargs["category"] is not None


def test_flag_on_leaves_the_positional_arguments_alone(monkeypatch):
    """The category must arrive BY KEYWORD — `_get_price`'s 6th positional is
    `nocache: bool`, so a positional thread-through would set nocache=True."""
    calls, _showable, _infer = _run(monkeypatch, _ELECTRONICS_Q, "true")
    for args, kwargs in calls:
        assert len(args) == 5, f"brand/name/variant/region/search_query only, got {args}"
        assert args[0] == "Apple"
        assert args[1] == "iPhone 15 Pro"
        assert args[2] == "256GB"
        assert args[4] == _ELECTRONICS_Q
        assert "nocache" not in kwargs
        assert set(kwargs) == {"category"}
    assert [a[3] for a, _k in calls] == list(scs.GCC_REGIONS.keys())


# ---------------------------------------------------------------------------
# FLAG OFF — byte-identical to main
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flag", [None, "false", "0", "off", "no", ""])
def test_flag_off_passes_no_category_at_all(monkeypatch, flag):
    """Not `category="other"` — NOTHING. Flag-OFF has to reproduce main's exact
    call, so a patched/wrapped `_get_price` sees the identical argument set."""
    calls, _showable, _infer = _run(monkeypatch, _ELECTRONICS_Q, flag)
    assert len(calls) == 6
    for args, kwargs in calls:
        assert kwargs == {}, f"flag OFF must not pass any kwarg, got {kwargs}"
        assert len(args) == 5


def test_flag_off_default_is_off(monkeypatch):
    monkeypatch.delenv("ENABLE_REGIONAL_PRICES_CATEGORY", raising=False)
    assert scs._regional_prices_category_enabled() is False


def test_flag_helper_reads_env_per_call(monkeypatch):
    """Never cached at import — Railway must be able to flip it live."""
    monkeypatch.delenv("ENABLE_REGIONAL_PRICES_CATEGORY", raising=False)
    assert scs._regional_prices_category_enabled() is False
    monkeypatch.setenv("ENABLE_REGIONAL_PRICES_CATEGORY", "true")
    assert scs._regional_prices_category_enabled() is True
    monkeypatch.setenv("ENABLE_REGIONAL_PRICES_CATEGORY", "false")
    assert scs._regional_prices_category_enabled() is False


# ---------------------------------------------------------------------------
# The DISPLAY gate must not move, in EITHER flag state
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flag", [None, "true"])
def test_display_gate_still_receives_the_raw_optional_inference(monkeypatch, flag):
    """`is_price_showable` gets the un-coerced value, None included — the
    coercion is for the RESOLVE path only. Loosening/altering the display gate
    here would be a critical regression, not a cleanup."""
    _calls, showable, _infer = _run(monkeypatch, _UNCATEGORISED_Q, flag)
    assert len(showable) == 6
    assert showable == [None] * 6

    _calls2, showable2, _infer2 = _run(monkeypatch, _ELECTRONICS_Q, flag)
    assert showable2 == ["electronics"] * 6


# ---------------------------------------------------------------------------
# One inference per call (the hoist replaces the post-gather call, not adds to it)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flag", [None, "true"])
def test_infer_category_called_exactly_once(monkeypatch, flag):
    _calls, _showable, infer = _run(monkeypatch, _ELECTRONICS_Q, flag)
    assert infer == [_ELECTRONICS_Q], f"expected 1 inference, got {infer}"


def test_inference_happens_before_the_fan_out(monkeypatch):
    """The hoist is the point: on main the inference runs AFTER the gather, so
    it cannot possibly feed the resolve. Pin the ORDER, not just the count."""
    order = []

    async def _fake_get_price(self, *args, **kwargs):
        order.append("resolve")
        return {"currency": "BHD"}

    _real_infer = ps._infer_category_from_query

    def _ordered_infer(q):
        order.append("infer")
        return _real_infer(q)

    monkeypatch.setenv("ENABLE_REGIONAL_PRICES_CATEGORY", "true")
    monkeypatch.setattr(
        scs.StructuredComparisonService, "_get_price", _fake_get_price, raising=True
    )
    monkeypatch.setattr(scs, "is_price_showable", lambda *a, **k: True, raising=True)
    monkeypatch.setattr(scs, "_infer_category_from_query", _ordered_infer, raising=True)

    asyncio.run(scs.get_regional_prices("Apple", "iPhone 15 Pro", "256GB", _ELECTRONICS_Q))
    assert order[0] == "infer", order
    assert order.count("infer") == 1
    assert order.count("resolve") == 6
