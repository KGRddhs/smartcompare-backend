"""Tests for the A4 --read-cache eval mode (Faithful-Results, Phase 7.2).

Plan: docs/plans/2026-06-17-faithful-results-genuine-bh-freetier-plan.md Task 7.2.

The default eval path hits /api/v1/text/compare with ?nocache=true, which
measures COLD scraping — it can NEVER reflect the price-cache warmer's
genuine-share, because every query force-misses the cache. The A4 variant
adds a `--read-cache` mode that does NOT pass nocache=true, so a run reads
whatever the warmer has populated. Measurement is meaningful only AFTER the
warmer cron is activated (ENABLE_PRICE_CACHE_WARMER); the runner says so.

ALL tests here use a mocked httpx transport (httpx.MockTransport) — no live
network, no Serper/OpenAI cost. They assert the flag threads end to end
(main -> run_eval -> run_query) and that the cold-vs-cache request shapes
differ on exactly the nocache param.
"""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from scripts import eval_runner


REPO_ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = REPO_ROOT / "data" / "validation_gold_truth.json"


# ---------------------------------------------------------------------------
# Minimal response body + capturing transport
# ---------------------------------------------------------------------------

def _ok_body() -> dict:
    """A minimal 200 body the grader can parse without crashing."""
    return {
        "success": True,
        "overview": {
            "winner": {"product_index": 0, "declaration": "x"},
            "products": [
                {"name": "A", "price": {"amount": 100.0, "currency": "BHD",
                                        "source_method": "local_bhd"}},
                {"name": "B", "price": {"amount": 90.0, "currency": "BHD",
                                        "source_method": "local_bhd"}},
            ],
        },
        "specs": {"products": [{"specs": {}}, {"specs": {}}]},
        "reviews": {"products": [{"review_summary": {}}, {"review_summary": {}}]},
        "scoring_v2": {"overall_score": {"winner_idx": 0}},
    }


def _capturing_transport(captured: list[dict]) -> httpx.MockTransport:
    """A transport that records each request's params, returns a fixed 200."""

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(dict(request.url.params))
        return httpx.Response(200, json=_ok_body())

    return httpx.MockTransport(handler)


def _record(qid: str = "elec-001", query: str = "iPhone 15 vs Galaxy S24") -> dict:
    return {"id": qid, "query": query, "category": "electronics",
            "region": "bahrain", "expected_prices": {}, "expected_specs": {},
            "expected_winner_index": None, "forbidden_facts": [],
            "max_wall_seconds": 25.0}


# ---------------------------------------------------------------------------
# run_query — the nocache param is the cold-vs-cache lever
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_query_default_still_sends_nocache():
    """REGRESSION GUARD: the default (cold) path MUST keep nocache=true — the
    baseline/regression gates measure cold scraping and rely on this."""
    captured: list[dict] = []
    transport = _capturing_transport(captured)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await eval_runner.run_query(client, _record())
    assert captured[0].get("nocache") == "true"


@pytest.mark.asyncio
async def test_run_query_read_cache_omits_nocache():
    """read_cache=True must NOT send nocache=true, so the engine serves from
    its L1/L2 price cache (what the warmer populated)."""
    captured: list[dict] = []
    transport = _capturing_transport(captured)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await eval_runner.run_query(client, _record(), read_cache=True)
    params = captured[0]
    # nocache must be entirely absent (not "false", not "true") so the backend
    # takes its normal cached path.
    assert "nocache" not in params
    # The real query is still sent (only the cache lever changed).
    assert params.get("q") == "iPhone 15 vs Galaxy S24"
    assert params.get("region") == "bahrain"


@pytest.mark.asyncio
async def test_run_query_read_cache_false_is_cold():
    """Explicit read_cache=False behaves exactly like the default (cold)."""
    captured: list[dict] = []
    transport = _capturing_transport(captured)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await eval_runner.run_query(client, _record(), read_cache=False)
    assert captured[0].get("nocache") == "true"


# ---------------------------------------------------------------------------
# run_eval — threads read_cache to every run_query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_eval_read_cache_threads_to_all_queries():
    captured: list[dict] = []
    transport = _capturing_transport(captured)
    queries = [_record(qid=f"q-{i}", query=f"q{i}") for i in range(3)]
    report = await eval_runner.run_eval(
        queries, base_url="http://test", transport=transport,
        concurrency=2, read_cache=True,
    )
    assert report.queries_total == 3
    assert len(captured) == 3
    # NONE of the three requests carried nocache.
    assert all("nocache" not in p for p in captured)


@pytest.mark.asyncio
async def test_run_eval_default_is_cold():
    captured: list[dict] = []
    transport = _capturing_transport(captured)
    queries = [_record(qid=f"q-{i}", query=f"q{i}") for i in range(3)]
    await eval_runner.run_eval(
        queries, base_url="http://test", transport=transport, concurrency=2,
    )
    assert all(p.get("nocache") == "true" for p in captured)


# ---------------------------------------------------------------------------
# The "measurement meaningful only post-warmer" caveat
# ---------------------------------------------------------------------------

def test_read_cache_note_states_warmer_caveat():
    """The runner exposes a caveat string saying a cache-read measurement is
    only meaningful after the warmer cron is activated."""
    note = eval_runner.read_cache_note()
    low = note.lower()
    assert "warmer" in low
    # It must point at the activation lever so the operator can act.
    assert "enable_price_cache_warmer" in low or "cron" in low


def test_read_cache_note_is_ascii():
    """Captured/redirected eval logs mojibake non-ASCII under the Windows
    cp1252 console codec (CLAUDE.md trap) — keep the note ASCII-only."""
    note = eval_runner.read_cache_note()
    assert note.encode("ascii")  # raises UnicodeEncodeError if non-ASCII


# ---------------------------------------------------------------------------
# main() — the --read-cache CLI flag (mocked run_eval, no network)
# ---------------------------------------------------------------------------

def test_main_read_cache_flag_passes_through(monkeypatch, capsys):
    """--read-cache on smoke20 sets read_cache=True on the run_eval call and
    prints the warmer caveat. run_eval stubbed so no live traffic."""
    seen = {}

    async def _fake_run_eval(queries, **kwargs):
        seen["read_cache"] = kwargs.get("read_cache")
        return eval_runner.aggregate([])

    monkeypatch.setattr(eval_runner, "run_eval", _fake_run_eval)
    rc = eval_runner.main([
        "--gold", str(GOLD_PATH), "--subset", "smoke20", "--read-cache",
        "--mode", "absolute", "--threshold", "0.0",
    ])
    assert seen.get("read_cache") is True
    assert rc in (0, 1)  # reached the gate, not a cost-guard refusal
    out = capsys.readouterr().out.lower()
    assert "warmer" in out  # the caveat is surfaced to the operator


def test_main_default_is_cold(monkeypatch):
    """Without --read-cache, run_eval is called with read_cache False (cold)."""
    seen = {}

    async def _fake_run_eval(queries, **kwargs):
        seen["read_cache"] = kwargs.get("read_cache")
        return eval_runner.aggregate([])

    monkeypatch.setattr(eval_runner, "run_eval", _fake_run_eval)
    rc = eval_runner.main([
        "--gold", str(GOLD_PATH), "--subset", "smoke20",
        "--mode", "absolute", "--threshold", "0.0",
    ])
    # Default must be falsy (None or False) — NOT True.
    assert not seen.get("read_cache")
    assert rc in (0, 1)
