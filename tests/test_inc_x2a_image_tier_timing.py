"""INC-X2a IMAGE-TIER-TIMING (G-INC-1, the S92-FIX incident lane) RED rows.

Spec: .qa-s80/G-INC-1_UNIT_SPEC.md section "Unit INC-X2a" (X2a.5), as amended by the
batch rulings R-G1-12 (the handler has no await and re-raises with a bare raise; no line
carries a product name, a URL or query text).

The unit is UNFLAGGED and log-only (R-A1): `get_product_image_url` logs one INFO
`[IMG_TIER] tier=<name> outcome=<outcome> ms=<int>` per tier it reaches and one INFO
`[IMG_TIER] cancelled tier=<name> tier_ms=<int> total_ms=<int>` when the 5 s Phase-1
race cancels it. RED rows (R2-*) fail at base on an AssertionError only (no such line
exists at base). PIN rows (P2-*) are green at base and pin the unchanged calls, order,
arguments, returns and exceptions with call recorders on every tier.

Hermetic: the three tier callables are patched on the module (the same seams the existing
image tests use); no network, no Redis, no LLM. The product name is a sentinel built at run
time. Pure ASCII, LF.
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import logging
import os
import re

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

from app.services import image_service as img  # noqa: E402

LOGGER = "app.services.image_service"
TIER = re.compile(
    r"^\[IMG_TIER\] tier=(piggyback|search_payload|serper_budget|serper_images|llm_pick) "
    r"outcome=(hit|miss|skipped|error:[A-Za-z_][A-Za-z0-9_]*) ms=\d+$"
)
CANCEL = re.compile(r"^\[IMG_TIER\] cancelled tier=(serper_images|llm_pick) tier_ms=(\d+) total_ms=(\d+)$")
NAME = "Zq" + "xprobe " + "Nimbus" + "Noir " + "Parfum"
KG_URL = "https://" + "kg.example.com" + "/img/kg-hero.jpg"
SERPER_URL = "https://" + "images.example.com" + "/p/serper-1.jpg"
PAYLOAD_TEXT = "payload" + "-marker-" + "x7"


def _tier_records(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == LOGGER and r.getMessage().startswith("[IMG_TIER]")]


def _pairs(lines):
    out = []
    for ln in lines:
        m = TIER.match(ln)
        assert m, "an [IMG_TIER] line does not match the closed tier grammar: %r" % ln
        out.append((m.group(1), m.group(2)))
    return out


class _Rec:
    def __init__(self):
        self.order = []
        self.budget = []
        self.search = []
        self.gpt = []
        self.cancelled = []


def _install(monkeypatch, rec, *, granted=True, images=None, search_raises=None, gpt_url=None,
             gpt_raises=None, search_hang=False):
    def _budget(n):
        rec.order.append("budget")
        rec.budget.append((n,))
        return granted

    async def _search(name, **kwargs):
        rec.order.append("search")
        rec.search.append(((name,), dict(kwargs)))
        if search_hang:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                rec.cancelled.append("search")
                raise
        if search_raises is not None:
            raise search_raises
        return {"images": list(images or [])}

    async def _gpt(name, organic):
        rec.order.append("gpt")
        rec.gpt.append((name, organic))
        if gpt_raises is not None:
            raise gpt_raises
        return gpt_url

    monkeypatch.setattr(img, "try_consume_serper_image_credit", _budget)
    monkeypatch.setattr(img, "search_images", _search)
    monkeypatch.setattr(img, "extract_image_via_gpt", _gpt)
    monkeypatch.delenv("ENABLE_DATA_GUARDS_V2", raising=False)


def _kg_payload():
    return {"knowledgeGraph": {"imageUrl": KG_URL, "description": PAYLOAD_TEXT}}


def _organic():
    return [{"title": "t " + PAYLOAD_TEXT, "link": "https://" + "shop.example.com/p/1",
             "snippet": PAYLOAD_TEXT}]


def _run(coro):
    return asyncio.run(coro)


def _call(**kw):
    return img.get_product_image_url(NAME, region="bahrain", page_scrape_image=None, **kw)


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r2_1_search_payload_hit_lines(monkeypatch, caplog):
    """R2-1: a knowledgeGraph image: [piggyback skipped, search_payload hit], in order."""
    rec = _Rec()
    _install(monkeypatch, rec)
    caplog.set_level(logging.INFO, logger=LOGGER)
    _run(_call(organic_results=_organic(), search_payload=_kg_payload()))
    assert _pairs(_tier_records(caplog)) == [("piggyback", "skipped"), ("search_payload", "hit")]


def test_r2_2_serper_hit_lines(monkeypatch, caplog):
    """R2-2: payload None, budget granted, one Serper image: four lines."""
    rec = _Rec()
    _install(monkeypatch, rec, images=[{"imageUrl": SERPER_URL}])
    caplog.set_level(logging.INFO, logger=LOGGER)
    _run(_call(organic_results=_organic(), search_payload=None))
    assert _pairs(_tier_records(caplog)) == [
        ("piggyback", "skipped"), ("search_payload", "skipped"),
        ("serper_budget", "hit"), ("serper_images", "hit")]


def test_r2_3_all_miss_lines(monkeypatch, caplog):
    """R2-3: payload without an image, budget granted, no images, GPT None: five lines."""
    rec = _Rec()
    _install(monkeypatch, rec, images=[], gpt_url=None)
    caplog.set_level(logging.INFO, logger=LOGGER)
    _run(_call(organic_results=_organic(), search_payload={"organic": []}))
    assert _pairs(_tier_records(caplog)) == [
        ("piggyback", "skipped"), ("search_payload", "miss"), ("serper_budget", "hit"),
        ("serper_images", "miss"), ("llm_pick", "miss")]


def test_r2_4_error_and_denied_outcomes(monkeypatch, caplog):
    """R2-4: (a) search_images raises RuntimeError -> serper_images error:RuntimeError;
    (b) budget denied -> serper_budget miss then serper_images skipped."""
    rec = _Rec()
    _install(monkeypatch, rec, search_raises=RuntimeError("probe"), gpt_url=None)
    caplog.set_level(logging.INFO, logger=LOGGER)
    _run(_call(organic_results=_organic(), search_payload=None))
    pairs_a = _pairs(_tier_records(caplog))
    assert ("serper_images", "error:RuntimeError") in pairs_a, pairs_a
    caplog.clear()
    rec_b = _Rec()
    _install(monkeypatch, rec_b, granted=False, gpt_url=None)
    _run(_call(organic_results=_organic(), search_payload=None))
    pairs_b = _pairs(_tier_records(caplog))
    assert ("serper_budget", "miss") in pairs_b, pairs_b
    assert ("serper_images", "skipped") in pairs_b, pairs_b
    assert pairs_b.index(("serper_budget", "miss")) < pairs_b.index(("serper_images", "skipped"))


def _cancel_path(monkeypatch, caplog):
    rec = _Rec()
    _install(monkeypatch, rec, search_hang=True)
    caplog.set_level(logging.INFO, logger=LOGGER)
    outcome = {}

    async def _go():
        try:
            await asyncio.wait_for(_call(organic_results=_organic(), search_payload=None), 0.2)
            outcome["result"] = "returned"
        except asyncio.TimeoutError:
            outcome["result"] = "timeout"
    _run(_go())
    return rec, outcome


def test_r2_5_cancel_line_names_the_tier_in_flight(monkeypatch, caplog):
    """R2-5: the Serper Images call hangs; the 0.2 s race cancels it: exactly one CANCEL
    record, tier serper_images, tier_ms <= total_ms."""
    _cancel_path(monkeypatch, caplog)
    lines = [ln for ln in _tier_records(caplog) if ln.startswith("[IMG_TIER] cancelled")]
    assert len(lines) == 1, lines
    m = CANCEL.match(lines[0])
    assert m, lines[0]
    assert m.group(1) == "serper_images", lines[0]
    assert int(m.group(2)) <= int(m.group(3)), lines[0]


def test_r2_6_lines_carry_no_name_or_url(monkeypatch, caplog):
    """R2-6: over the R2-1..R2-5 paths at least one [IMG_TIER] record exists, every one
    matches TIER or CANCEL and none carries the sentinel name, 'http' or payload text."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    rec = _Rec()
    _install(monkeypatch, rec)
    _run(_call(organic_results=_organic(), search_payload=_kg_payload()))
    _install(monkeypatch, _Rec(), images=[{"imageUrl": SERPER_URL}])
    _run(_call(organic_results=_organic(), search_payload=None))
    _install(monkeypatch, _Rec(), images=[], gpt_url=None)
    _run(_call(organic_results=_organic(), search_payload={"organic": []}))
    _install(monkeypatch, _Rec(), search_raises=RuntimeError("probe"), gpt_url=None)
    _run(_call(organic_results=_organic(), search_payload=None))
    _cancel_path(monkeypatch, caplog)
    lines = _tier_records(caplog)
    assert lines, "no [IMG_TIER] record on any image path"
    for ln in lines:
        assert TIER.match(ln) or CANCEL.match(ln), ln
        assert NAME not in ln and NAME[:10] not in ln, ln
        assert "http" not in ln, ln
        assert PAYLOAD_TEXT not in ln, ln


def _handler_nodes():
    tree = ast.parse(inspect.getsource(img))
    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_product_image_url":
            fn = node
    assert fn is not None, "get_product_image_url not found"
    handlers = []
    for node in ast.walk(fn):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            if ast.unparse(node.type) in ("asyncio.CancelledError", "CancelledError"):
                handlers.append(node)
    return handlers


def test_r2_7_handler_has_no_await_and_reraises():
    """R2-7: get_product_image_url has an `except asyncio.CancelledError` handler whose body
    contains no Await node and whose last statement is a bare Raise."""
    handlers = _handler_nodes()
    assert handlers, "get_product_image_url has no `except asyncio.CancelledError` handler"
    for h in handlers:
        awaits = [n for n in ast.walk(h) if isinstance(n, ast.Await)]
        assert awaits == [], "the CancelledError handler awaits: %s" % ast.unparse(h)
        last = h.body[-1]
        assert isinstance(last, ast.Raise) and last.exc is None, (
            "the CancelledError handler does not end with a bare raise: %s" % ast.unparse(h))


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------

def test_p2_1_kg_hit_calls_nothing_paid(monkeypatch):
    """P2-1: a knowledgeGraph hit calls no paid tier and returns the KG URL."""
    rec = _Rec()
    _install(monkeypatch, rec)
    out = _run(_call(organic_results=_organic(), search_payload=_kg_payload()))
    assert out == KG_URL
    assert rec.budget == [] and rec.search == [] and rec.gpt == []


def test_p2_2_serper_hit_call_order(monkeypatch):
    """P2-2: budget once with (1,), search once with (name,) / {num_results: 1}, gpt 0;
    the return is the image URL stripped."""
    rec = _Rec()
    _install(monkeypatch, rec, images=[{"imageUrl": "  " + SERPER_URL + " "}])
    out = _run(_call(organic_results=_organic(), search_payload=None))
    assert out == SERPER_URL
    assert rec.budget == [(1,)]
    assert rec.search == [((NAME,), {"num_results": 1})]
    assert rec.gpt == []
    assert rec.order == ["budget", "search"]


def test_p2_3_all_miss_call_order(monkeypatch, caplog):
    """P2-3: budget, search, gpt each once in that order; None; the existing final line."""
    rec = _Rec()
    _install(monkeypatch, rec, images=[], gpt_url=None)
    caplog.set_level(logging.INFO, logger=LOGGER)
    out = _run(_call(organic_results=_organic(), search_payload={"organic": []}))
    assert out is None
    assert rec.order == ["budget", "search", "gpt"]
    assert len(rec.gpt) == 1 and rec.gpt[0][0] == NAME
    assert any(r.getMessage().startswith("[image] All tiers exhausted") for r in caplog.records)


def test_p2_4_budget_denied(monkeypatch):
    """P2-4: budget denied: search 0 calls, gpt 1 call."""
    rec = _Rec()
    _install(monkeypatch, rec, granted=False, gpt_url=None)
    out = _run(_call(organic_results=_organic(), search_payload=None))
    assert out is None
    assert rec.search == [] and len(rec.gpt) == 1 and rec.budget == [(1,)]


def test_p2_5_search_raises_still_tries_gpt(monkeypatch, caplog):
    """P2-5: search raises: the existing WARNING is present and gpt is called once."""
    rec = _Rec()
    _install(monkeypatch, rec, search_raises=RuntimeError("probe"), gpt_url=None)
    caplog.set_level(logging.INFO, logger=LOGGER)
    _run(_call(organic_results=_organic(), search_payload=None))
    assert any(r.levelno == logging.WARNING
               and r.getMessage().startswith("[image] Tier 1 Serper Images raised")
               for r in caplog.records)
    assert len(rec.gpt) == 1


def test_p2_6_cancel_propagates(monkeypatch, caplog):
    """P2-6: the race path: the caller gets asyncio.TimeoutError, the stub saw a
    CancelledError, gpt is never called."""
    rec, outcome = _cancel_path(monkeypatch, caplog)
    assert outcome.get("result") == "timeout", outcome
    assert rec.cancelled == ["search"]
    assert rec.gpt == []


def test_p2_7_empty_name(monkeypatch, caplog):
    """P2-7: a blank name returns None, calls nothing and logs no [IMG_TIER] record."""
    rec = _Rec()
    _install(monkeypatch, rec)
    caplog.set_level(logging.INFO, logger=LOGGER)
    out = _run(img.get_product_image_url("  ", search_payload=_kg_payload(), organic_results=_organic()))
    assert out is None
    assert rec.order == []
    assert _tier_records(caplog) == []
