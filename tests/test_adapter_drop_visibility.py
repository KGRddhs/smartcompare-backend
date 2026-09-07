"""W1-8 RED — give the silent adapter drop a name (LS-CONCURRENCY-LIMITS-03).

`structured_comparison_service._timeout_none` is the per-source wrap every price
fan-out adapter runs inside:

    try:
        return await asyncio.wait_for(make_coro(), timeout)
    except Exception:  # noqa: BLE001 — TimeoutError + any adapter error → drop
        return None

Every adapter failure therefore returns `None` and emits NOTHING, so "the fan-out
saturated and 12 adapters timed out" and "no Bahraini store carries this product"
produce byte-identical telemetry: a short result list and silence. Until that is
fixed no W5 STEP 0 canary can be READ — a flag flip that made things worse looks
exactly like a flip that changed nothing.

`fan_out_price_lookup` has the same gap at the aggregate level: it returns
`cancelled_count` but no `failed_count`, so a caller can tell "deliberately
cancelled" from "completed" but not from "failed".

Contract pinned here (NO flag — additive observability only):
  1. `_timeout_none` takes a `label: str` and, on an adapter EXCEPTION, emits
     exactly one INFO record naming the label AND `type(exc).__name__`.
  2. On a TIMEOUT it emits exactly one INFO record that identifies the drop as a
     TIMEOUT (a distinct classification from the error case) and names the label.
  3. The SUCCESS path returns the value and logs NOTHING — this unit adds zero
     noise to the healthy case.
  4. `asyncio.CancelledError` still propagates out of `_timeout_none` and is
     never logged as a drop. See that test's docstring — it is green today and
     must STAY green; it is not trivial.
  5. `fan_out_price_lookup` returns `failed_count`, counting a raising scraper
     and NOT counting a cancelled one.
  6. Every `_timeout_none(` call site passes a non-default `label=`.

No network. Run:
  PYTHONIOENCODING=utf-8 python -m pytest tests/test_adapter_drop_visibility.py -x -q
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import ast
import asyncio
import logging
from pathlib import Path

import pytest

import app.services.structured_comparison_service as scs
from app.services.structured_comparison_service import _timeout_none
from app.services.price_service import fan_out_price_lookup


_SCS_LOGGER_NAME = scs.logger.name  # "app.services.structured_comparison_service"

# The module the call-site census reads. Resolved from the test file's own
# location so the census never depends on importing the (very heavy) module.
_SCS_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "app" / "services" / "structured_comparison_service.py"
)


def _scs_records(caplog) -> list[logging.LogRecord]:
    """Only records emitted by structured_comparison_service's own logger."""
    return [r for r in caplog.records if r.name == _SCS_LOGGER_NAME]


def _raising_factory(exc: BaseException):
    """A zero-arg factory (the real call-site shape) whose coro raises `exc`."""

    async def _coro():
        raise exc

    return lambda: _coro()


def _sleeping_factory(delay: float, value="never"):
    def _coro():
        async def _inner():
            await asyncio.sleep(delay)
            return value

        return _inner()

    return _coro


# ---------------------------------------------------------------------------
# 1 — an adapter EXCEPTION is named
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_adapter_exception_logs_one_info_record_with_label_and_type(caplog):
    """An adapter that RAISES must emit exactly one INFO record naming both the
    adapter-family label and the exception type.

    `make_coro` is a zero-arg lambda factory, so `make_coro.__name__` is
    '<lambda>' and carries nothing — the label has to be passed in explicitly.

    RED at HEAD: `_timeout_none` has no `label` parameter and logs nothing.
    """
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER_NAME)

    result = await _timeout_none(
        _raising_factory(RuntimeError("adapter blew up")),
        5.0,
        label="bolo_sitemap",
    )

    assert result is None, "a raising adapter must still resolve to None"

    records = _scs_records(caplog)
    assert len(records) == 1, (
        f"expected exactly 1 INFO record for the dropped adapter, got "
        f"{len(records)}: {[r.getMessage() for r in records]}"
    )
    rec = records[0]
    assert rec.levelno == logging.INFO, (
        f"the drop must be INFO, not {rec.levelname} — a cold Bahraini source "
        f"with no listing is not a warning"
    )
    msg = rec.getMessage()
    assert "bolo_sitemap" in msg, f"record does not name the label: {msg!r}"
    assert "RuntimeError" in msg, (
        f"record does not name type(exc).__name__ — an adapter exception is a "
        f"bug and must be identifiable: {msg!r}"
    )
    # Discriminate on the PREFIX, never on the substring "TIMEOUT" (Fable
    # review): since CPython 3.11 `asyncio.TimeoutError IS TimeoutError`, so
    # `type(exc).__name__` in this branch can legitimately BE "TimeoutError"
    # and a substring check would then fail for a correct message.
    assert ": ERROR " in msg, (
        f"an adapter exception must carry the ERROR prefix: {msg!r}"
    )
    assert ": TIMEOUT after" not in msg, (
        f"an adapter ERROR must not be classified as a TIMEOUT: {msg!r}"
    )


# ---------------------------------------------------------------------------
# 2 — a TIMEOUT is classified distinctly
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_adapter_timeout_logs_one_info_record_identified_as_timeout(caplog):
    """A timed-out adapter emits one INFO record identified as a TIMEOUT and
    naming the label.

    A timeout is the LOAD signal this unit exists to expose; an adapter
    exception is a bug. They must be distinguishable in the stream.

    An explicit short `timeout=` is used (never `_ADAPTER_TIMEOUT`, which is
    10.0s) so this test runs in milliseconds.

    RED at HEAD: no `label` parameter, and the bare `except Exception` swallows
    the TimeoutError silently.
    """
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER_NAME)

    result = await _timeout_none(
        _sleeping_factory(5.0),
        0.02,
        label="nasser_jsonapi",
    )

    assert result is None, "a timed-out adapter must still resolve to None"

    records = _scs_records(caplog)
    assert len(records) == 1, (
        f"expected exactly 1 INFO record for the timed-out adapter, got "
        f"{len(records)}: {[r.getMessage() for r in records]}"
    )
    rec = records[0]
    assert rec.levelno == logging.INFO, (
        f"the drop must be INFO, not {rec.levelname}"
    )
    msg = rec.getMessage()
    assert "nasser_jsonapi" in msg, f"record does not name the label: {msg!r}"
    # MUST discriminate on the prefix (Fable review, from an adversarial
    # finding). The previous assertion was `"TIMEOUT" in msg.upper()`, which
    # PROVED NOTHING: `asyncio.TimeoutError is TimeoutError` on this
    # interpreter, so the generic error line "[ADAPTER DROP] <label>: ERROR
    # TimeoutError: " already upper-cases to a string containing "TIMEOUT".
    # Deleting the entire timeout branch left that assertion green.
    assert ": TIMEOUT after" in msg, (
        f"a timeout drop must carry the TIMEOUT prefix, distinct from the "
        f"adapter-error case: {msg!r}"
    )
    assert ": ERROR " not in msg, (
        f"a timeout must not fall through to the ERROR branch: {msg!r}"
    )


# ---------------------------------------------------------------------------
# 3 — the healthy path stays silent
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_success_returns_value_and_logs_nothing(caplog):
    """A successful adapter returns its value and emits NO log record.

    Pins that this unit adds no noise to the healthy case: a normal fan-out is
    ~18 adapters across two products, so a per-call success line would be pure
    volume with zero signal.
    """
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER_NAME)

    async def _ok():
        return {"amount": 12.5, "currency": "BHD"}

    result = await _timeout_none(lambda: _ok(), 5.0, label="bolo_sitemap")

    assert result == {"amount": 12.5, "currency": "BHD"}
    records = _scs_records(caplog)
    assert records == [], (
        f"the success path must log nothing, got: "
        f"{[r.getMessage() for r in records]}"
    )


# ---------------------------------------------------------------------------
# 4 — cancellation still propagates (green today; MUST STAY GREEN)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cancellation_propagates_and_is_not_logged_as_a_drop(caplog):
    """DO NOT DELETE THIS TEST AS TRIVIAL. It is green today and its whole job
    is to STAY green.

    `asyncio.CancelledError` derives from BaseException, NOT Exception, so the
    existing `except Exception` deliberately lets cancellation propagate — that
    is what makes `_cancel_prefetched_direct` (the genuine-Tier-1 short-circuit
    that kills the ~18 speculative prefetch tasks) actually work. A future
    `except BaseException` here — an easy "let's catch everything" edit while
    adding logging — would silently convert every cancellation into a `None`
    return, so the speculative adapters would run to completion in the
    background and the prefetch cancel would become a no-op.

    Measured on the pinned interpreter (CPython 3.12.9, see the class-hierarchy
    assertion below): CancelledError.__mro__ is (CancelledError, BaseException,
    object) and issubclass(CancelledError, Exception) is False.

    Both cancellation shapes are pinned:
      (a) the adapter coro itself raises CancelledError;
      (b) the task awaiting `_timeout_none` is cancelled from outside — the
          `_cancel_prefetched_direct` case.
    """
    # Interpreter pin — the reason the narrow catch is load-bearing.
    assert not issubclass(asyncio.CancelledError, Exception), (
        "asyncio.CancelledError must NOT be an Exception subclass on this "
        "interpreter; if it were, `except Exception` would already be "
        "swallowing prefetch cancellation"
    )
    assert issubclass(asyncio.CancelledError, BaseException)

    caplog.set_level(logging.INFO, logger=_SCS_LOGGER_NAME)

    # (a) the adapter coro raises CancelledError itself.
    with pytest.raises(asyncio.CancelledError):
        await _timeout_none(
            _raising_factory(asyncio.CancelledError()),
            5.0,
            label="bolo_sitemap",
        )

    # (b) the awaiting task is cancelled from outside (prefetch cancel).
    task = asyncio.ensure_future(
        _timeout_none(_sleeping_factory(5.0), 5.0, label="nasser_jsonapi")
    )
    await asyncio.sleep(0)  # let the task body start
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled(), (
        "an outer cancel must leave the task CANCELLED, not completed with "
        "None — a None return means the cancel was swallowed"
    )

    assert _scs_records(caplog) == [], (
        "cancellation is not an adapter drop and must not be logged as one: "
        f"{[r.getMessage() for r in _scs_records(caplog)]}"
    )


# ---------------------------------------------------------------------------
# 5 — fan_out_price_lookup reports failed_count
# ---------------------------------------------------------------------------
def _confirming_scraper(delay: float):
    """A GENUINE BH candidate at rank >= HIGH_RANK_THRESHOLD (85), which is what
    `_confirmed` requires to end the race and cancel the pending scrapers."""

    async def _scraper(_product: dict) -> dict:
        await asyncio.sleep(delay)
        return {
            "value": 22.5,
            "source_method": "page_scrape_jsonld",
            "rank": 90,
            "retailer": "bolo.bh",
            "raw_data": {
                "source_method": "page_scrape_jsonld",
                "retailer": "bolo.bh",
            },
        }

    return _scraper


def _raising_scraper(delay: float):
    async def _scraper(_product: dict):
        await asyncio.sleep(delay)
        raise RuntimeError("adapter blew up")

    return _scraper


def _hanging_scraper(delay: float, cancel_marker: list[str]):
    async def _scraper(_product: dict):
        try:
            await asyncio.sleep(delay)
            return None
        except asyncio.CancelledError:
            cancel_marker.append("hanging")
            raise

    return _scraper


@pytest.mark.asyncio
async def test_failed_count_sees_a_raiser_done_but_never_yielded():
    """The case the incremental count could not see (Fable review, from an
    adversarial finding) — and it is an ORDERING case, not a timing race.

    The sibling test below gives the raiser the SHORTEST delay, so
    `as_completed` yields it and it is counted on the way past. That is the
    lucky ordering. Here the confirmer and the raiser complete in the SAME tick
    (both `sleep(0)`), and `as_completed` then yields them in CREATION order —
    measured, deterministic. So the confirmer is yielded first, `_confirmed()`
    ends the race, and the raiser is left `done()` but never yielded. Both
    drains skip it with `if t.cancelled() or t.done(): continue`, so its
    exception is never retrieved and the incremental count reported 0 for it.

    Counting once over `tasks` after the drain sees it regardless of yield
    order, which is the point: a saturation metric that depends on which task
    happened to be yielded first is not a metric.
    """
    cancelled: list[str] = []
    scrapers = [
        _confirming_scraper(0.0),   # created first -> yielded first -> break
        _raising_scraper(0.0),      # same tick, never yielded, left done()
        _hanging_scraper(5.0, cancelled),
    ]

    result = await fan_out_price_lookup(
        {"brand": "Glorious", "name": "Model O", "category": "electronics"},
        scrapers=scrapers,
        scraping_mode="hard",
    )

    assert result["failed_count"] == 1, (
        f"a raiser left done-but-unyielded by the confirmation break must still "
        f"be counted; got failed_count={result['failed_count']} "
        f"(cancelled_count={result['cancelled_count']})"
    )


@pytest.mark.asyncio
async def test_fan_out_reports_failed_count_separately_from_cancelled():
    """`fan_out_price_lookup` must return `failed_count` — a purely additive key
    (every existing caller reads by key, so it is inert for them).

    Without it the caller can distinguish "deliberately cancelled" from
    "completed" but NOT from "failed": twelve adapters raising and twelve
    adapters finding nothing return the identical dict.

    Three scrapers: one raises (failed), one confirms at rank 90 (which ends the
    race), one hangs and is cancelled. `failed_count` must count the raiser and
    must NOT count the cancelled one.

    RED at HEAD: KeyError — the returned dict has only best / alternates /
    cancelled_count / elapsed_seconds.
    """
    cancelled: list[str] = []
    scrapers = [
        _raising_scraper(0.01),      # completes first → failed
        _confirming_scraper(0.05),   # confirms → cancels the pending one
        _hanging_scraper(5.0, cancelled),
    ]

    result = await fan_out_price_lookup(
        {"brand": "Glorious", "name": "Model O", "category": "electronics"},
        scrapers=scrapers,
        scraping_mode="hard",
    )

    assert "failed_count" in result, (
        f"fan_out_price_lookup must report failed_count; got keys "
        f"{sorted(result)}"
    )
    assert result["failed_count"] == 1, (
        f"exactly one scraper raised; failed_count={result['failed_count']}"
    )
    # Exactly one scraper was cancelled (the hanging one). Pins the other half
    # of the distinction: the RAISING scraper must not be counted as cancelled.
    assert result["cancelled_count"] == 1, (
        f"only the hanging scraper should be cancelled; "
        f"cancelled_count={result['cancelled_count']}"
    )
    assert cancelled == ["hanging"], (
        f"expected the hanging scraper to observe its cancel, got {cancelled}"
    )
    assert result["best"] is not None, "the confirming scraper should have won"


# ---------------------------------------------------------------------------
# 6 — every call site names its adapter family
# ---------------------------------------------------------------------------
def test_every_timeout_none_call_site_passes_a_label():
    """Source-level census: zero `_timeout_none(` calls may omit `label=`.

    This is what stops the NEXT adapter added to the fan-out from being silent
    again — the default exists only so the signature change is non-breaking, not
    so call sites can rely on it.

    Parsed with `ast` (not a regex) so a multi-line call, a nested lambda
    default or a comment containing the name cannot skew the count.

    RED at HEAD: 6 unlabelled call sites.
    """
    source = _SCS_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    unlabelled: list[int] = []
    total = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "_timeout_none"):
            continue
        total += 1
        if not any(kw.arg == "label" for kw in node.keywords):
            unlabelled.append(node.lineno)

    assert total > 0, (
        "found no _timeout_none call sites — the census is looking at the "
        f"wrong file: {_SCS_SOURCE}"
    )
    assert unlabelled == [], (
        f"{len(unlabelled)} of {total} _timeout_none call sites pass no "
        f"label= and would drop adapters anonymously; lines: {unlabelled}"
    )
