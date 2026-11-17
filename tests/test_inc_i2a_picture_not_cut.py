"""INC-I2a PICTURE-NOT-CUT (ENABLE_IMAGE_LATE_BIND, default OFF) RED rows.

Spec: s96/i2a/spec/INC_I2A_UNIT_SPEC_V2.md section 5, as ruled by RULINGS_INC_I2A.md
(R-1..R-19). The flag moves the product picture out of the 5 s Phase-1 wait: the
image job starts with the product, runs in the background (bounded), is bound at the
tail (after the verdict, before the build) or drained at a hard cap, and caches every
guard-accepted late pick in Upstash under ``imgpick:v1:<guard version>:``.

RED rows E1..E28 fail at base on an AssertionError only: every missing symbol is read
through ``_need`` (hasattr + an assertion). PIN rows P1..P5 (and E23, a parity pin)
are green at base. P1 runs with the FULL unit configuration (B1): the flag unset and
"false", every IMAGE_LATE_* / IMAGE_PICK_* knob set to a synthetic value, a getenv
recorder, the cache fakes and the pool watched; it compares a sync and a stream
compare with tests/fixtures/inc_i2a_flag_off_golden.json (recorded at base fd983471).

Hermetic: the Serper / credit / LLM leaves of image_service, the unified search, the
specs / price / reviews legs and the verdict are faked; the image cache is an
in-memory get_cached / set_cached pair on image_service; no network, no Redis, no
LLM. Synthetic identities and example.com hosts only. Pure ASCII, LF.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import inspect
import json
import logging
import os
import re
import threading
import time
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "inc_i2a_flag_off_golden.json"

FLAG = "ENABLE_IMAGE_LATE_BIND"
G_FLAG = "ENABLE_IMAGE_RELEVANCE_GUARD"
S_FLAG = "ENABLE_IMAGE_GUARD_SHORT_LINE"
R_FLAG = "ENABLE_PRODUCT_RESOLVER"
KNOBS = (
    "IMAGE_LATE_BIND_MAX_WAIT_SECONDS",
    "IMAGE_LATE_BIND_RESERVE_SECONDS",
    "IMAGE_LATE_MAX_SECONDS",
    "IMAGE_PICK_CACHE_TTL_SECONDS",
)
SYNTH_KNOBS = {
    "IMAGE_LATE_BIND_MAX_WAIT_SECONDS": "7",
    "IMAGE_LATE_BIND_RESERVE_SECONDS": "9",
    "IMAGE_LATE_MAX_SECONDS": "11",
    "IMAGE_PICK_CACHE_TTL_SECONDS": "13",
}
CLEARED_ENV = (
    (FLAG, G_FLAG, S_FLAG, R_FLAG)
    + KNOBS
    + (
        "ENABLE_KB_FIRST_SERVE",
        "ENABLE_VERDICT_CACHE_LOG",
        "ENABLE_KB_INGEST",
        "ENABLE_SYNC_DB_OFFLOAD",
        "ENABLE_UNIFIED_SEARCH_BOUND",
        "UNIFIED_SEARCH_TIMEOUT_SECONDS",
        "ENABLE_PHASE2_RESIDUAL_GUARD",
        "DEBUG_STAGE_TIMINGS",
        "ENABLE_FULL_STREAM_DEADLINE",
        "ENABLE_RESULT_STATUS_METADATA",
        "ENABLE_LLM_LEDGER_V2",
        "ENABLE_LLM_SPEND_BREAKER",
        "ENABLE_ANTHROPIC_TEXT",
        "ENABLE_ANTHROPIC_VISION",
        "ENABLE_ANTHROPIC_VERDICT",
        "ENABLE_ANTHROPIC_CRITIC",
        "ENABLE_ANTHROPIC_MODERATION",
        "ENABLE_SONNET_ESCALATION",
        "ENABLE_OPENAI_PRE_V3",
        "ENABLE_FRAGRANCE_ONLY_GATE",
        "ENABLE_IMAGE_PIPELINE_V2",
        "ENABLE_DATA_GUARDS_V2",
        "ENABLE_TIER_FILL_RESIDUAL_GUARD",
        "ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT",
        "ENABLE_RESULT_GATE",
        "ENABLE_EARLY_SPECS_STASH",
        "ENABLE_PREVERDICT_DISCONNECT_ABORT",
        "ENABLE_ARABIC_VERDICT_OUTPUT",
        "IMAGE_RELEVANCE_CANDIDATES",
    )
)

BIND = re.compile(
    r"^IMG_LATE bind product=(0|1) outcome=(attached|cached|override|fallback|shopping|"
    r"missed_at_deadline|none) wait_ms=(\d+)$"
)
JOB = re.compile(
    r"^IMG_LATE job product=(0|1) outcome=(accepted|none|cancelled|timeout|error) "
    r"ms=(\d+) stored=(0|1)$"
)
PAGE = re.compile(
    r"^IMG_LATE page_override outcome=(hit|skipped|fallback) product=(0|1)$"
)
CACHE = re.compile(
    r"^IMG_LATE cache outcome=(hit|miss|skipped|error|stored|store_failed) ms=(\d+)$"
)
SAWAIT = re.compile(r"^IMG_LATE serper_await ms=(\d+) cancelling=(0|1)$")
TIER = re.compile(
    r"^\[IMG_TIER\] tier=(piggyback|search_payload|serper_budget|serper_images|llm_pick) "
    r"outcome=(hit|miss|skipped|error:[A-Za-z_][A-Za-z0-9_]*) ms=\d+$"
)
CANCEL = re.compile(
    r"^\[IMG_TIER\] cancelled tier=(serper_images|llm_pick) tier_ms=(\d+) total_ms=(\d+)$"
)

P0 = ("Acme", "Nimbus Noir Eau de Parfum")
P1 = ("Zephyra", "Velvet Dusk Eau de Toilette")
QUERY = "Acme Nimbus Noir Eau de Parfum vs Zephyra Velvet Dusk Eau de Toilette"
LLM_PARSED = {
    "products": [
        {
            "brand": P0[0],
            "name": P0[1],
            "variant": None,
            "category": "fragrances",
            "search_query": " ".join(P0),
        },
        {
            "brand": P1[0],
            "name": P1[1],
            "variant": None,
            "category": "fragrances",
            "search_query": " ".join(P1),
        },
    ],
    "comparison_type": "value",
}
PINFO0 = {
    "brand": P0[0],
    "name": P0[1],
    "variant": "EDP 100ml",
    "category": "fragrances",
    "search_query": "Acme Nimbus Noir Eau de Parfum 100ml",
}
SHOP = "shop.example.com"
STORE_A = "store-a.example.com"
URL_S0 = "https://" + "img.example.com" + "/p/nimbus-noir-1.jpg"
URL_S1 = "https://" + "img.example.com" + "/p/velvet-dusk-1.jpg"
URL_KG = "https://" + "kg.example.com" + "/img/nimbus-hero.jpg"
URL_GPT = "https://" + SHOP + "/media/nimbus-noir-pick.jpg"
PAGE_A = "https://" + STORE_A + "/img/nimbus-a.jpg"
PAGE_B = "https://" + STORE_A + "/img/nimbus-b.jpg"
CARD = "https://" + "card.example.com" + "/img/nimbus-card.jpg"
PRICE_URL = "https://" + STORE_A + "/products/nimbus-noir"
TITLE0 = "Acme Nimbus Noir Eau de Parfum perfume"
TITLE1 = "Zephyra Velvet Dusk Eau de Toilette perfume"
USAGE = {"prompt_tokens": 7, "completion_tokens": 3}
SENTINEL_NAME = "Nimbus Noir"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _img():
    from app.services import image_service

    return image_service


def _scs():
    import app.services.structured_comparison_service as scs

    return scs


def _need(obj, name):
    assert hasattr(obj, name), "%s.%s is missing (INC-I2a not implemented)" % (
        getattr(obj, "__name__", type(obj).__name__),
        name,
    )
    return getattr(obj, name)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    yield


def _flags(mp, *, late=True, g=True, s=True, extra=None):
    for name, on in ((FLAG, late), (G_FLAG, g), (S_FLAG, s)):
        if on is None:
            mp.delenv(name, raising=False)
        elif on is True:
            mp.setenv(name, "true")
        elif on is False:
            mp.delenv(name, raising=False)
        else:
            mp.setenv(name, on)
    for k, v in (extra or {}).items():
        mp.setenv(k, v)


def _lines(caplog, prefix):
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith(prefix)]


def _late(caplog, kind):
    return _lines(caplog, "IMG_LATE " + kind + " ")


def _parse(regex, lines):
    out = []
    for ln in lines:
        m = regex.match(ln)
        assert m, "a line does not match its grammar: %r" % ln
        out.append(m.groups())
    return out


async def _drain_bg(limit=15.0):
    from app.utils import async_utils as au

    loop = asyncio.get_running_loop()
    end = time.monotonic() + limit
    while time.monotonic() < end:
        pending = [
            t
            for t in list(au._BACKGROUND_TASKS)
            if not t.done() and t.get_loop() is loop
        ]
        if not pending:
            return
        await asyncio.wait(pending, timeout=max(0.01, end - time.monotonic()))


def _item(url, title, slug):
    return {
        "imageUrl": url,
        "title": title,
        "source": "Example Shop",
        "link": "https://" + SHOP + "/p/" + slug,
        "domain": SHOP,
    }


def _images_for(query):
    q = (query or "").lower()
    if "nimbus" in q:
        return [_item(URL_S0, TITLE0, "nimbus-noir")]
    if "velvet" in q:
        return [_item(URL_S1, TITLE1, "velvet-dusk")]
    return []


class _T:
    """Recorders for the image leaves and the image cache."""

    def __init__(self):
        self.credit = []
        self.search = []
        self.gpt = []
        self.get = []
        self.set = []
        self.store = {}
        self.search_started = 0


def _install_tiers(
    mp,
    t,
    *,
    granted=True,
    images=_images_for,
    search_delay=0.0,
    search_event=None,
    search_hang=False,
    gpt_url=None,
    gpt_hang=False,
    get_delay=0.0,
    get_raises=None,
    set_ret=True,
    set_raises=None,
    credit_delay=0.0,
):
    img = _img()

    def _credit(n):
        t.credit.append(
            {"n": n, "thread": threading.current_thread().name, "at": time.monotonic()}
        )
        if credit_delay:
            time.sleep(credit_delay)
        return granted

    async def _search(name, **kwargs):
        t.search_started += 1
        t.search.append({"q": name, "kw": dict(kwargs), "at": time.monotonic()})
        if search_event is not None:
            await search_event.wait()
        if search_delay:
            await asyncio.sleep(search_delay)
        if search_hang:
            await asyncio.Event().wait()
        return {"images": list(images(name) if callable(images) else (images or []))}

    async def _gpt(name, organic):
        t.gpt.append(name)
        if gpt_hang:
            await asyncio.Event().wait()
        return gpt_url

    def _get(key):
        t.get.append({"key": key, "thread": threading.current_thread().name})
        if get_delay:
            time.sleep(get_delay)
        if get_raises is not None:
            raise get_raises
        return copy.deepcopy(t.store.get(key))

    def _set(key, value, ttl=None, *a, **k):
        t.set.append(
            {
                "key": key,
                "value": copy.deepcopy(value),
                "ttl": ttl if ttl is not None else k.get("ttl"),
                "thread": threading.current_thread().name,
            }
        )
        if set_raises is not None:
            raise set_raises
        if set_ret is True:
            t.store[key] = copy.deepcopy(value)
        return set_ret

    mp.setattr(img, "try_consume_serper_image_credit", _credit)
    mp.setattr(img, "search_images", _search)
    mp.setattr(img, "extract_image_via_gpt", _gpt)
    mp.setattr(img, "get_cached", _get, raising=False)
    mp.setattr(img, "set_cached", _set, raising=False)


def _price(brand, *, image=None, url=PRICE_URL, amount=55.0):
    p = {
        "amount": amount,
        "currency": "BHD",
        "estimated": False,
        "source_method": "local_bhd",
        "retailer": "Live Store " + brand,
        "url": url,
        "title": "x",
        "in_stock": True,
    }
    if image is not None:
        p["image_url"] = image
    return p


def _payload_plain(query):
    return {
        "organic": [
            {
                "title": "T " + query[:20],
                "link": "https://" + "example.com/a",
                "snippet": "eau de parfum woody longevity 8 hours",
            }
        ]
    }


# --- the direct _fetch_product_data harness -------------------------------------------


def _fetch_setup(
    mp,
    svc,
    *,
    unified_delay=0.0,
    unified_event=None,
    payload=_payload_plain,
    price=None,
    price_delay=0.0,
    stamps=None,
    kb_card=None,
):
    scs = _scs()
    stamps = stamps if stamps is not None else {}

    async def _specs(*a, **_k):
        return {"concentration": "Eau de Parfum", "scent_family": "amber"}

    async def _price_leg(*a, **_k):
        if price_delay:
            await asyncio.sleep(price_delay)
        return copy.deepcopy(price) if price is not None else _price(str(a[0]))

    async def _reviews(*a, **_k):
        return {"highlights": ["good"], "summary": "ok"}

    async def _search_web(query, num_results=10, **kwargs):
        stamps.setdefault("search_web_start", time.monotonic())
        if unified_event is not None:
            await unified_event.wait()
        if unified_delay:
            await asyncio.sleep(unified_delay)
        stamps.setdefault("search_web_return", time.monotonic())
        return payload(query) if callable(payload) else payload

    async def _rating(*a, **_k):
        return {
            "rating": 4.5,
            "review_count": 10,
            "rating_verified": True,
            "rating_source": {"name": "example", "url": "https://" + "example.com/r"},
        }

    async def _empty(*a, **_k):
        return {}

    svc._get_specs = _specs
    svc._get_price = _price_leg
    svc._get_reviews = _reviews
    svc._get_verified_rating = _rating
    svc._smart_fallback_extract = _empty
    mp.setattr(svc, "_track_serper_cost", lambda *a, **k: None)
    mp.setattr(svc, "_track_gpt_cost", lambda *a, **k: None)
    mp.setattr(scs, "search_web", _search_web)
    mp.setattr(scs, "tier2_fill_non_negotiables", _empty)
    mp.setattr(scs, "tier3_synthesize_non_negotiables", _empty)
    mp.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    svc._compare_deadline = time.monotonic() + 30.0
    if kb_card is not None:
        from app.services import kb_serve

        def _classify(card, **_k):
            return {
                "hit": "partial",
                "price": None,
                "specs": None,
                "specs_complete": False,
                "candidates": [],
                "image_url": kb_card,
                "reviews": None,
            }

        mp.setattr(kb_serve, "classify", _classify)
    return stamps


async def _kb_task_done():
    fut = asyncio.get_running_loop().create_future()
    fut.set_result([{}, {}])
    return fut


async def _fetch(svc, pinfo=None, slot=0):
    return await svc._fetch_product_data(
        dict(pinfo or PINFO0), "bahrain", True, True, True, partial_slot=slot
    )


def _entry(svc, slot=0):
    entries = _need(svc, "_late_images")
    assert isinstance(entries, dict) and slot in entries, (
        "no late-image entry for slot %r" % slot
    )
    return entries[slot]


# --- the full compare driver (the FY25 driver of test_s81_s18_kb_first_serve.py, copied) --


def _install_compare(mp, svc, st):
    scs = _scs()
    from app.services import audit_service as _audit
    from app.services import content_safety_service as _cs
    from app.services import scoring_service as _ss

    async def _parse_q(query):
        return json.loads(json.dumps(LLM_PARSED)), dict(USAGE)

    async def _gen(*_a, **_k):
        if st.get("gen_hang"):
            await asyncio.sleep(60)
        if st.get("gen_delay"):
            await asyncio.sleep(st["gen_delay"])
        ev = st.get("gen_event")
        if ev is not None:
            ev.set()
        st["gen_done_at"] = time.monotonic()
        return (
            {
                "winner_index": 0,
                "winner_declaration": "Acme wins",
                "winner_reason": "longevity",
                "verdict": "v",
                "pros": {},
                "cons": {},
            },
            dict(USAGE),
        )

    async def _cat_llm(*_a, **_k):
        return "fragrances"

    async def _search(query, num_results=10, **kwargs):
        if st.get("unified_delay"):
            await asyncio.sleep(st["unified_delay"])
        st.setdefault("unified_returns", []).append(time.monotonic())
        return _payload_plain(query)

    async def _specs(*a, **_k):
        return {
            "concentration": "Eau de Parfum",
            "scent_family": "amber",
            "longevity": "8 hours",
        }

    async def _price_leg(*a, **_k):
        if st.get("price_delay"):
            await asyncio.sleep(st["price_delay"])
        if st.get("price_hang"):
            await asyncio.sleep(60)
        prices = st.get("prices") or {}
        return copy.deepcopy(prices.get(str(a[0]), _price(str(a[0]))))

    async def _reviews(*a, **_k):
        return {"highlights": ["good"], "summary": "ok"}

    async def _rating(*a, **_k):
        return {
            "rating": 4.5,
            "review_count": 10,
            "rating_verified": True,
            "rating_source": {"name": "example", "url": "https://" + "example.com/r"},
        }

    async def _fallback(*a, **_k):
        return {}

    async def _tier(*a, **k):
        return {}

    async def _moderate(_self, _text):
        return _cs.SafetyResult(allowed=True)

    def _reconcile(product_data, query, category, candidates_by_name=None, **kw):
        fn = st.get("reconcile")
        if fn is not None:
            fn(product_data)
        return None

    async def _none(*_a, **_k):
        return None

    mp.setattr(_audit, "log_content_blocked", _none)
    mp.setattr(_cs.ContentSafetyService, "moderate_output", _moderate)
    mp.setattr(scs, "parse_product_query", _parse_q)
    mp.setattr(scs, "generate_comparison", _gen)
    mp.setattr(scs, "reconcile_pair_fairness", _reconcile)
    mp.setattr(scs, "classify_category_llm", _cat_llm)
    mp.setattr(scs, "get_scoring_service", lambda: _ss.ScoringService())
    mp.setattr(scs, "search_web", _search)
    mp.setattr(scs, "tier2_fill_non_negotiables", _tier)
    mp.setattr(scs, "tier3_synthesize_non_negotiables", _tier)
    mp.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    mp.setattr(scs, "get_user_demographics", _none)
    svc._get_specs = _specs
    svc._get_price = _price_leg
    svc._get_reviews = _reviews
    svc._get_verified_rating = _rating
    svc._smart_fallback_extract = _fallback
    svc._fetch_behavior_profile = _none


async def _compare(mp, kind, st, *, cap=30.0):
    scs = _scs()
    mp.setattr(scs, "STREAM_HARD_CAP_SECONDS", cap)
    svc = st.get("svc") or scs.StructuredComparisonService()
    st["svc"] = svc
    _install_compare(mp, svc, st)
    st["entry_at"] = time.monotonic()
    if kind == "rest":
        out = await asyncio.wait_for(
            svc.compare_from_text(QUERY, region="bahrain", nocache=True), 60
        )
    else:
        out = []

        async def _go():
            async for event in svc.compare_from_text_streaming(
                QUERY, region="bahrain", nocache=True
            ):
                out.append(list(event))

        await asyncio.wait_for(_go(), 60)
    st["returned_at"] = time.monotonic()
    if st.get("after") is not None:
        await st["after"]()
    await _drain_bg()
    return out


def _complete(events):
    for kind, body in events:
        if kind == "complete":
            return body
    raise AssertionError("no complete event: %r" % ([e[0] for e in events],))


def _pics(body):
    return [p.get("image_url") for p in body["overview"]["products"]]


# ===========================================================================
# RED rows
# ===========================================================================


def test_e01_job_starts_before_the_unified_search_returns(monkeypatch):
    """E1: L ON, the unified search sleeps 0.3 s: the credit (and Serper) fake is stamped
    BEFORE the unified search returns."""
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t)

    async def go():
        svc = _scs().StructuredComparisonService()
        stamps = _fetch_setup(monkeypatch, svc, unified_delay=0.3)
        await _fetch(svc)
        await _drain_bg()
        return stamps

    stamps = _run(go())
    assert t.credit, "the credit fake was never called"
    assert (
        t.credit[0]["at"] < stamps["search_web_return"]
    ), "credit stamped after the unified search"
    assert t.search and t.search[0]["at"] < stamps["search_web_return"]


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_e02_e03_slow_serper_picture_not_cut(monkeypatch, caplog, kind):
    """E2 (sync) / E3 (stream): Serper 5.6 s, price 6.0 s, verdict fast: product 0 keeps the
    picture; no [L2.6] image race timeout and no X2a cancel line."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t, search_delay=5.6)
    st = {"price_delay": 6.0}
    out = _run(_compare(monkeypatch, kind, st))
    body = out if kind == "rest" else _complete(out)
    assert body.get("success") is True, body.get("code")
    assert _pics(body)[0] == URL_S0
    assert not _lines(caplog, "[L2.6] Phase 1 race timeout for image_url")
    assert not _lines(caplog, "[IMG_TIER] cancelled")


def _e04_run(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    holder = {}
    ev_box = {}

    async def _search(name, **kwargs):
        t.search.append({"q": name})
        await ev_box["ev"].wait()
        await asyncio.sleep(0.4)
        return {"images": _images_for(name)}

    _install_tiers(monkeypatch, t)
    monkeypatch.setattr(_img(), "search_images", _search)

    async def go():
        ev_box["ev"] = asyncio.Event()
        st = {"gen_event": ev_box["ev"]}
        holder["st"] = st
        return await _compare(monkeypatch, "rest", st)

    body = _run(go())
    return body, holder["st"], t


def test_e04_bind_waits_for_a_late_serper(monkeypatch, caplog):
    """E4: Serper resolves 0.4 s after the verdict, no override, residual large: the
    bind attaches with wait_ms >= 300."""
    body, st, t = _e04_run(monkeypatch, caplog)
    binds = _parse(BIND, _late(caplog, "bind"))
    mine = [b for b in binds if b[0] == "0"]
    assert mine, "no IMG_LATE bind line for product 0"
    assert mine[0][1] == "attached" and int(mine[0][2]) >= 300, mine
    assert _pics(body)[0] == URL_S0


def test_e05_bind_respects_the_deadline_and_never_cancels(monkeypatch, caplog):
    """E5: _compare_deadline = now + 1.0, reserve 2.0: the bind returns at once with
    missed_at_deadline and the job is not cancelled. E6 then follows in the same run."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    box = {}

    async def go():
        box["ev"] = asyncio.Event()
        _install_tiers(monkeypatch, t, search_event=box["ev"])
        svc = _scs().StructuredComparisonService()
        _fetch_setup(monkeypatch, svc)
        result = await _fetch(svc)
        entry = _entry(svc)
        svc._compare_deadline = time.monotonic() + 1.0
        t0 = time.monotonic()
        await _need(svc, "_late_image_bind")()
        took = time.monotonic() - t0
        box.update(
            took=took,
            cancelled=entry["task"].cancelled(),
            done=entry["task"].done(),
            image=result.get("image_url"),
        )
        box["ev"].set()
        await _drain_bg()
        box["final"] = (
            entry["task"].result() if not entry["task"].cancelled() else "CANCELLED"
        )

    _run(go())
    assert box["took"] < 0.2, box
    assert box["cancelled"] is False and box["done"] is False, box
    assert box["image"] is None
    binds = _parse(BIND, _late(caplog, "bind"))
    assert ("0", "missed_at_deadline", "0") in binds, binds
    # E6 (the task completes after the bind): ONE store, the prefix, u, the TTL.
    img = _img()
    prefix = _need(img, "PICK_CACHE_PREFIX")
    assert box["final"] == URL_S0
    assert len(t.set) == 1, t.set
    assert t.set[0]["key"].startswith(prefix)
    assert t.set[0]["value"]["u"] == URL_S0 and t.set[0]["ttl"] == 604800
    assert [g[0] for g in _parse(CACHE, _late(caplog, "cache"))].count("stored") == 1
    jobs = _parse(JOB, _late(caplog, "job"))
    assert jobs and jobs[0][1] == "accepted" and jobs[0][3] == "1", jobs


def test_e06_store_failed_keeps_the_picture(monkeypatch, caplog):
    """E6: set_cached returns False: cache store_failed, job stored=0, the picture is
    still bound when the job lands in time."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t, set_ret=False)

    async def go():
        svc = _scs().StructuredComparisonService()
        _fetch_setup(monkeypatch, svc)
        result = await _fetch(svc)
        await asyncio.sleep(0.05)
        await _need(svc, "_late_image_bind")()
        await _drain_bg()
        return result

    result = _run(go())
    assert result.get("image_url") == URL_S0
    assert "store_failed" in [g[0] for g in _parse(CACHE, _late(caplog, "cache"))]
    jobs = _parse(JOB, _late(caplog, "job"))
    assert jobs and jobs[0][3] == "0", jobs
    assert ("0", "attached") in [
        (b[0], b[1]) for b in _parse(BIND, _late(caplog, "bind"))
    ]


def _relevance0():
    """The identity scs hands the late call for PINFO0 (image_relevance.relevance_kwargs
    under the guard, built here flag-free)."""
    return {
        "brand": PINFO0["brand"],
        "line": PINFO0["name"],
        "category": "fragrances",
        "slot": 0,
    }


def test_e07_cache_hit_pays_nothing(monkeypatch, caplog):
    """E7: a cached {"u": URL}: credit and Serper 0 calls, cache hit, no [IMG_RELEVANCE];
    through _fetch_product_data the bind says cached."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    img = _img()
    t = _T()
    _install_tiers(monkeypatch, t)
    name = _need(img, "pick_cache_name")(_relevance0(), PINFO0["variant"])
    t.store[name] = {"u": URL_S1, "t": "serper_images"}

    async def go():
        svc = _scs().StructuredComparisonService()
        _fetch_setup(monkeypatch, svc)
        result = await _fetch(svc)
        await asyncio.sleep(0.05)
        await _need(svc, "_late_image_bind")()
        await _drain_bg()
        return result

    result = _run(go())
    assert t.credit == [] and t.search == []
    assert result.get("image_url") == URL_S1
    assert "hit" in [g[0] for g in _parse(CACHE, _late(caplog, "cache"))]
    assert not _lines(caplog, "[IMG_RELEVANCE]")
    assert ("0", "cached") in [
        (b[0], b[1]) for b in _parse(BIND, _late(caplog, "bind"))
    ]
    assert t.set == []


def _late_call(**kw):
    img = _img()
    fn = _need(img, "get_product_image_url_late")
    kw.setdefault("region", "bahrain")
    return fn(" ".join(P0), **kw)


async def _done_fut(value):
    fut = asyncio.get_running_loop().create_future()
    fut.set_result(value)
    return fut


def test_e08_misses_and_cuts_are_never_stored(monkeypatch, caplog):
    """E8: refused Serper items + gpt None: no set_cached, cache miss; a cut job (bound
    0.2 s, Serper hangs): job timeout, nothing written."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    bad = [_item(URL_S1, "Other House Something Else", "other")]
    _install_tiers(monkeypatch, t, images=bad, gpt_url=None)

    async def go():
        state = {"open": True, "until": None, "cached": False, "stored": False}
        out = await _late_call(
            payload=await _done_fut({"organic": []}),
            variant="EDP 100ml",
            state=state,
            relevance=_relevance0(),
        )
        return out

    assert _run(go()) is None
    assert t.set == []
    assert [g[0] for g in _parse(CACHE, _late(caplog, "cache"))] == ["miss"]
    caplog.clear()
    t2 = _T()
    _install_tiers(monkeypatch, t2, search_hang=True)
    scs = _scs()

    async def go2():
        state = {"open": True, "until": None, "cached": False, "stored": False}
        fut = asyncio.get_running_loop().create_future()
        coro = _late_call(
            payload=fut, variant="EDP 100ml", state=state, relevance=_relevance0()
        )
        return await _need(scs, "_late_image_job")(coro, 0.2, 0, state)

    assert _run(go2()) is None
    assert t2.set == []
    jobs = _parse(JOB, _late(caplog, "job"))
    assert jobs == [("0", "timeout", jobs[0][2], "0")], jobs


@pytest.mark.parametrize(
    "case", ["g_unset_no_relevance", "g_unset_with_relevance", "camera_g_on"]
)
def test_e09_no_cache_without_the_guard(monkeypatch, caplog, case):
    """E9 (R-6): G unset or a camera product (no relevance): the cache fakes are never
    called and the cache line says skipped."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, g=(case == "camera_g_on"))
    t = _T()
    _install_tiers(monkeypatch, t)
    rel = _relevance0() if case == "g_unset_with_relevance" else None

    async def go():
        state = {"open": True, "until": None, "cached": False, "stored": False}
        return await _late_call(
            payload=await _done_fut(None),
            variant="EDP 100ml",
            state=state,
            relevance=rel,
        )

    out = _run(go())
    assert out == URL_S0
    assert t.get == [] and t.set == []
    assert [g[0] for g in _parse(CACHE, _late(caplog, "cache"))] == ["skipped"]


def test_e10_credit_runs_on_the_offloop_pool(monkeypatch):
    """E10: L ON: the credit fake runs on a redis-offloop thread."""
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t)

    async def go():
        svc = _scs().StructuredComparisonService()
        _fetch_setup(monkeypatch, svc)
        await _fetch(svc)
        await _drain_bg()

    _run(go())
    assert t.credit and t.credit[0]["thread"].startswith("redis-offloop"), t.credit


def test_e11_line_grammar(monkeypatch, caplog):
    """E11 (a): every IMG_LATE line matches its grammar and carries no http, name or
    query; one serper_await cancelling=0 per Serper call; [IMG_TIER] lines keep X2a."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t)

    async def go():
        svc = _scs().StructuredComparisonService()
        _fetch_setup(monkeypatch, svc)
        await _fetch(svc)
        await asyncio.sleep(0.05)
        await _need(svc, "_late_image_bind")()
        await _drain_bg()

    _run(go())
    late = _lines(caplog, "IMG_LATE")
    assert late, "no IMG_LATE line"
    for ln in late:
        assert any(rx.match(ln) for rx in (BIND, JOB, PAGE, CACHE, SAWAIT)), ln
        assert (
            "http" not in ln and SENTINEL_NAME not in ln and "nimbus" not in ln.lower()
        ), ln
    aw = _parse(SAWAIT, _late(caplog, "serper_await"))
    assert len(aw) == len(t.search) == 1 and aw[0][1] == "0", aw
    for ln in _lines(caplog, "[IMG_TIER]"):
        assert TIER.match(ln) or CANCEL.match(ln), ln


@pytest.mark.parametrize(
    "point", ["cache", "serper_budget", "serper_images", "search_payload", "llm_pick"]
)
def test_e11_cancel_at_each_await(monkeypatch, caplog, point):
    """E11 (b): cancelling the job at each await point: job cancelled, the X2a cancel line
    only for serper_images / llm_pick, the CancelledError propagates."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    organic = [
        {"title": TITLE0, "link": "https://" + SHOP + "/p/nimbus-noir", "snippet": "s"}
    ]
    kw = {}
    if point == "cache":
        kw["get_delay"] = 0.6
    elif point == "serper_budget":
        kw["credit_delay"] = 0.6
    elif point == "serper_images":
        kw["search_hang"] = True
    elif point == "search_payload":
        kw["images"] = []
    else:
        kw.update(images=[], gpt_hang=True)
    _install_tiers(monkeypatch, t, **kw)
    scs = _scs()
    box = {}

    async def go():
        state = {"open": True, "until": None, "cached": False, "stored": False}
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        if point == "llm_pick":
            fut.set_result({"organic": organic})
        coro = _late_call(
            payload=fut, variant="EDP 100ml", state=state, relevance=_relevance0()
        )
        task = asyncio.ensure_future(
            _need(scs, "_late_image_job")(coro, 20.0, 0, state)
        )

        def reached():
            return {
                "cache": bool(t.get),
                "serper_budget": bool(t.credit),
                "serper_images": bool(t.search),
                "search_payload": bool(t.search),
                "llm_pick": bool(t.gpt),
            }[point]

        for _ in range(200):
            if reached():
                break
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
            box["r"] = "returned"
        except asyncio.CancelledError:
            box["r"] = "cancelled"
        await asyncio.sleep(0.7)

    _run(go())
    assert box["r"] == "cancelled"
    jobs = _parse(JOB, _late(caplog, "job"))
    assert [j[1] for j in jobs] == ["cancelled"], jobs
    cancels = [
        m.group(1)
        for m in (CANCEL.match(x) for x in _lines(caplog, "[IMG_TIER] cancelled"))
        if m
    ]
    if point in ("serper_images", "llm_pick"):
        assert cancels == [point], cancels
    else:
        assert cancels == [], cancels


def _swap_to(image):
    def fn(product_data):
        product_data[0]["price"] = _price(P0[0], image=image, amount=49.0)

    return fn


def _pend(product_data):
    product_data[0]["price"] = {
        "amount": None,
        "currency": "BHD",
        "pending": True,
        "reason": "size_mismatch",
        "estimated": False,
    }


@pytest.mark.parametrize("v2", [False, True])
@pytest.mark.parametrize("case", ["swap", "pend", "pend_cascade_none"])
def test_e12_override_reads_the_post_swap_price(monkeypatch, caplog, v2, case):
    """E12 (R-2, V2 missed point 8): Phase 1 had page image A, the cascade C; a fairness
    swap to page image B -> B (override, hit); swapped to pending -> C (attached,
    skipped); pending and cascade None -> A (fallback)."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, extra={"ENABLE_IMAGE_PIPELINE_V2": "true"} if v2 else None)
    t = _T()
    if case == "pend_cascade_none":
        _install_tiers(monkeypatch, t, images=[], gpt_url=None)
    else:
        _install_tiers(monkeypatch, t)
    st = {
        "prices": {P0[0]: _price(P0[0], image=PAGE_A)},
        "reconcile": _swap_to(PAGE_B) if case == "swap" else _pend,
    }
    body = _run(_compare(monkeypatch, "rest", st))
    want = {"swap": PAGE_B, "pend": URL_S0, "pend_cascade_none": PAGE_A}[case]
    assert _pics(body)[0] == want, (_pics(body), case)
    binds = [(b[0], b[1]) for b in _parse(BIND, _late(caplog, "bind"))]
    pages = [(p[1], p[0]) for p in _parse(PAGE, _late(caplog, "page_override"))]
    exp_bind = {
        "swap": "override",
        "pend": "attached",
        "pend_cascade_none": "fallback",
    }[case]
    exp_page = {"swap": "hit", "pend": "skipped", "pend_cascade_none": "fallback"}[case]
    assert ("0", exp_bind) in binds, binds
    assert ("0", exp_page) in pages, pages


@pytest.mark.parametrize("kind", ["rest", "stream"])
@pytest.mark.parametrize("image_state", ["done", "pending"])
def test_e13_hard_cap_during_phase1_drains(monkeypatch, caplog, kind, image_state):
    """E13: a 0.6 s cap DURING Phase 1 (price hangs, specs land, stash ON): image done at
    0.1 s -> the partial carries it, the bind line from the drain; image pending -> None,
    missed_at_deadline, and the job later stores."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, extra={"ENABLE_EARLY_SPECS_STASH": "true"})
    t = _T()
    box = {}

    async def go():
        if image_state == "pending":
            box["ev"] = asyncio.Event()
            _install_tiers(monkeypatch, t, search_event=box["ev"])
        else:
            _install_tiers(monkeypatch, t, search_delay=0.1)
        st = {"price_hang": True}

        async def after():
            if image_state == "pending":
                box["ev"].set()

        st["after"] = after
        return await _compare(monkeypatch, kind, st, cap=0.6)

    out = _run(go())
    body = out if kind == "rest" else _complete(out)
    assert (
        body.get("success") is True
        and (body.get("metadata") or {}).get("partial") is True
    ), body.get("code")
    binds = [(b[0], b[1]) for b in _parse(BIND, _late(caplog, "bind"))]
    if image_state == "done":
        assert _pics(body)[0] == URL_S0
        assert ("0", "attached") in binds, binds
    else:
        assert _pics(body)[0] is None
        assert ("0", "missed_at_deadline") in binds, binds
        assert any(s["value"]["u"] == URL_S0 for s in t.set), t.set


def test_e14_cancelled_fetch_leaves_the_job_running(monkeypatch):
    """E14: _fetch_product_data cancelled during the unified search: the job stays in
    _BACKGROUND_TASKS, is not cancelled, completes and stores; fut resolved None; the
    life is closed."""
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t, search_delay=0.2)
    box = {}

    async def go():
        from app.utils import async_utils as au

        svc = _scs().StructuredComparisonService()
        stamps = _fetch_setup(monkeypatch, svc, unified_event=asyncio.Event())
        task = asyncio.ensure_future(_fetch(svc))
        for _ in range(200):
            if "search_web_start" in stamps:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        entry = _entry(svc)
        box["in_bg"] = entry["task"] in au._BACKGROUND_TASKS
        box["fut_done"] = entry["fut"].done() and not entry["fut"].cancelled()
        box["fut_value"] = entry["fut"].result() if box["fut_done"] else "X"
        box["open"] = entry["state"]["open"]
        await _drain_bg()
        box["cancelled"] = entry["task"].cancelled()
        box["result"] = None if box["cancelled"] else entry["task"].result()

    _run(go())
    assert box["in_bg"] is True and box["cancelled"] is False, box
    assert box["fut_done"] is True and box["fut_value"] is None, box
    assert box["open"] is False, box
    assert box["result"] == URL_S0 and len(t.set) == 1, (box, t.set)


def test_e15_flag_read_per_call(monkeypatch):
    """E15: two instances, the flag flipped between them: the base order (credit after the
    unified search), then the late order (credit before it)."""
    _flags(monkeypatch, late=False)
    t = _T()
    _install_tiers(monkeypatch, t)
    seen = []

    async def go(on):
        if on:
            monkeypatch.setenv(FLAG, "true")
        svc = _scs().StructuredComparisonService()
        stamps = _fetch_setup(monkeypatch, svc, unified_delay=0.2)
        n = len(t.credit)
        await _fetch(svc)
        await _drain_bg()
        seen.append(t.credit[n]["at"] < stamps["search_web_return"])

    _run(go(False))
    _run(go(True))
    assert seen == [False, True], seen


def test_e16_kb_card_image_pays_nothing(monkeypatch, caplog):
    """E16: a KB card image: image_url == the card URL, bound as attached; credit, Serper,
    get_cached and set_cached 0 calls."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t)

    async def go():
        svc = _scs().StructuredComparisonService()
        _fetch_setup(monkeypatch, svc, kb_card=CARD)
        svc._kb_cards_task = await _kb_task_done()
        svc._kb_hit_marks = ["miss", "miss"]
        svc._kb_views = [None, None]
        result = await _fetch(svc)
        await asyncio.sleep(0.02)
        await _need(svc, "_late_image_bind")()
        await _drain_bg()
        return result

    result = _run(go())
    assert result.get("image_url") == CARD
    assert ("0", "attached") in [
        (b[0], b[1]) for b in _parse(BIND, _late(caplog, "bind"))
    ]
    assert t.credit == [] and t.search == [] and t.get == [] and t.set == []


KNOB_READERS = {
    "IMAGE_LATE_BIND_MAX_WAIT_SECONDS": ("image_late_bind_max_wait_seconds", 3.0),
    "IMAGE_LATE_BIND_RESERVE_SECONDS": ("image_late_bind_reserve_seconds", 2.0),
    "IMAGE_LATE_MAX_SECONDS": ("image_late_max_seconds", 20.0),
    "IMAGE_PICK_CACHE_TTL_SECONDS": ("image_pick_cache_ttl_seconds", 604800),
}


@pytest.mark.parametrize("env", sorted(KNOB_READERS))
def test_e17_knob_parsing(monkeypatch, env):
    """E17 (R-4): unset, "", "abc", "inf", "nan", "0", "-1" -> the default; "1.5" read
    (the TTL "3600"); IMAGE_LATE_MAX_SECONDS "45" -> 30.0."""
    reader_name, default = KNOB_READERS[env]
    reader = _need(_img(), reader_name)
    for raw in (None, "", "abc", "inf", "nan", "0", "-1", " -2 "):
        if raw is None:
            monkeypatch.delenv(env, raising=False)
        else:
            monkeypatch.setenv(env, raw)
        assert reader() == default, (env, raw, reader())
    good = "3600" if env == "IMAGE_PICK_CACHE_TTL_SECONDS" else "1.5"
    monkeypatch.setenv(env, good)
    assert reader() == (3600 if env == "IMAGE_PICK_CACHE_TTL_SECONDS" else 1.5)
    if env == "IMAGE_LATE_MAX_SECONDS":
        monkeypatch.setenv(env, "45")
        assert reader() == 30.0


def test_e18_payload_tier_after_serper_and_llm_pick(monkeypatch, caplog):
    """E18: Serper miss and a passing KG payload: the KG URL; tiers piggyback skipped,
    serper_budget hit, serper_images miss, search_payload hit; stored with t
    search_payload. No images + a passing organic item (life open): llm_pick runs and
    stores."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t, images=[])
    kg = {
        "knowledgeGraph": {"imageUrl": URL_KG, "title": TITLE0, "type": "Perfume"},
        "organic": [],
    }

    async def go(payload):
        state = {"open": True, "until": None, "cached": False, "stored": False}
        return await _late_call(
            payload=await _done_fut(payload),
            variant="EDP 100ml",
            state=state,
            relevance=_relevance0(),
        )

    assert _run(go(kg)) == URL_KG
    pairs = [TIER.match(x).groups() for x in _lines(caplog, "[IMG_TIER] tier=")]
    assert pairs == [
        ("piggyback", "skipped"),
        ("serper_budget", "hit"),
        ("serper_images", "miss"),
        ("search_payload", "hit"),
    ], pairs
    assert len(t.set) == 1 and t.set[0]["value"] == {
        "u": URL_KG,
        "t": "search_payload",
    }, t.set
    caplog.clear()
    t2 = _T()
    _install_tiers(monkeypatch, t2, images=[], gpt_url=URL_GPT)
    organic = {
        "organic": [
            {
                "title": TITLE0,
                "link": "https://" + SHOP + "/p/nimbus-noir",
                "snippet": "s",
            }
        ]
    }
    assert _run(go(organic)) == URL_GPT
    assert len(t2.gpt) == 1
    assert len(t2.set) == 1 and t2.set[0]["value"] == {
        "u": URL_GPT,
        "t": "llm_pick",
    }, t2.set


def _name(rel, variant):
    return _need(_img(), "pick_cache_name")(rel, variant)


def _rel(brand, line, category="fragrances", slot=0):
    return {"brand": brand, "line": line, "category": category, "slot": slot}


def test_e19_cache_name(monkeypatch):
    """E19 (R-12): EDT != EDP; EDP 100ml == EDP 50ml; a typed line with sizes folds;
    Sauvage != Sauvage Elixir; s0 != s1; category differs; slot 0 == slot 1; case and
    accents fold; no raw text; R OFF identity != R ON identity (stated)."""
    monkeypatch.setenv(S_FLAG, "true")
    a = _name(_rel("Dior", "Sauvage"), "EDP 100ml")
    assert a != _name(_rel("Dior", "Sauvage"), "EDT 100ml")
    assert a == _name(_rel("Dior", "Sauvage"), "EDP 50ml")
    assert a == _name(_rel("Dior", "Sauvage"), "EDP 100 ml")
    assert _name(_rel("", "Sauvage EDP 100 ml"), None) == _name(
        _rel("", "Sauvage EDP 50ml"), None
    )
    assert a != _name(_rel("Dior", "Sauvage Elixir"), "EDP 100ml")
    assert a != _name(_rel("Dior", "Sauvage", category="other"), "EDP 100ml")
    assert a == _name(_rel("Dior", "Sauvage", slot=1), "EDP 100ml")
    assert a == _name(_rel("DIOR", "  sauvage "), "edp 100ML")
    assert _name(_rel("Acme", "Cafe Noir"), None) == _name(
        _rel("ACME", "Caf" + chr(0xE9) + " Noir"), None
    )
    low = a.lower()
    assert "dior" not in low and "sauvage" not in low and "edp" not in low
    assert re.fullmatch(
        re.escape(_need(_img(), "PICK_CACHE_PREFIX")) + r"[0-9a-f]{32}", a
    ), a
    r_off = _name(_rel("", "Dior Sauvage EDP"), "EDP 100ml")
    assert r_off != a
    monkeypatch.delenv(S_FLAG, raising=False)
    assert _name(_rel("Dior", "Sauvage"), "EDP 100ml") != a


def test_e20_short_bound_never_breaks_the_set_sites(monkeypatch, caplog):
    """E20 (R-10): bound 0.2 s, unified 0.5 s, Serper miss: the compare succeeds with specs
    and prices, no InvalidStateError, no ERROR record, every fut done (not cancelled).
    """
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, extra={"IMAGE_LATE_MAX_SECONDS": "0.2"})
    t = _T()
    _install_tiers(monkeypatch, t, images=[], gpt_url=None)
    st = {"unified_delay": 0.5}
    body = _run(_compare(monkeypatch, "rest", st))
    assert body.get("success") is True, body.get("code")
    assert all(p.get("specs") for p in body["specs"]["products"])
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR], [
        r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR
    ]
    assert not [r for r in caplog.records if "InvalidStateError" in r.getMessage()]
    entries = _need(st["svc"], "_late_images")
    assert sorted(entries) == [0, 1], entries
    for e in entries.values():
        assert e["fut"].done() and not e["fut"].cancelled()
    assert [j[1] for j in _parse(JOB, _late(caplog, "job"))] == ["timeout", "timeout"]


@pytest.mark.parametrize("value", ["denied", "http", "str", "list", "no_u"])
def test_e21_read_check(monkeypatch, caplog, value):
    """E21 (R-13): DATA_GUARDS_V2 OFF: a cached denied-host URL, an http URL and a non-dict
    value are each a miss, and the cascade runs."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    monkeypatch.delenv("ENABLE_DATA_GUARDS_V2", raising=False)
    t = _T()
    _install_tiers(monkeypatch, t)
    name = _name(_relevance0(), "EDP 100ml")
    t.store[name] = {
        "denied": {"u": "https://" + "fimgs" + ".net/m/x.jpg", "t": "serper_images"},
        "http": {"u": "http://" + SHOP + "/x.jpg", "t": "serper_images"},
        "str": "https://" + SHOP + "/x.jpg",
        "list": ["https://" + SHOP + "/x.jpg"],
        "no_u": {"url": "https://" + SHOP + "/x.jpg"},
    }[value]

    async def go():
        state = {"open": True, "until": None, "cached": False, "stored": False}
        return await _late_call(
            payload=await _done_fut(None),
            variant="EDP 100ml",
            state=state,
            relevance=_relevance0(),
        )

    assert _run(go()) == URL_S0
    assert [g[0] for g in _parse(CACHE, _late(caplog, "cache"))][0] == "miss"
    assert len(t.credit) == 1


GUARD_SET = (
    "check",
    "_check_base",
    "_check_short_line",
    "_words_reason",
    "_conc_scan",
    "_conc_labels",
    "words_reason_for",
    "guard_words_enabled",
    "short_line_enabled",
    "_seq",
    "_text_tokens",
    "_host_tokens",
    "_candidate_keys",
    "fold_numero",
    "identity",
    "RelevanceCall._record",
    "RelevanceCall.accept",
    "RelevanceCall.accept_scheme",
    "RelevanceCall._organic_reason",
    "RelevanceCall.organic_passes",
    "RelevanceCall.accept_pick",
    "RelevanceCall.accept_thumb",
)
#: INC-I2b (I-2): every word table check() reads, as a deterministic text.
GUARD_SORTED_TABLES = (
    "NAME_EXCLUDE",
    "CONCENTRATION_WORDS",
    "STOP_WORDS",
    "FRAGRANCE_WORDS",
    "BRAND_NOISE",
    "PLACEHOLDER_BRANDS",
    "UNIT_WORDS",
    "ELISION",
    "BRAND_EXCLUDE",
    "_NUMERO_PREFIX",
    "_WHOLE_LINE_DROP",
    "FORM_WORDS",
    "FORM_JOINS",
    "INTENSE_WORDS",
    "INTENSE_GENERIC_NEXT",
)
GUARD_PATTERNS = ("SIZE_TOKEN", "_NUMBER", "_NUMERO")


def _guard_text():
    from app.services import image_relevance as ir

    objs = []
    for dotted in GUARD_SET:
        obj = ir
        for part in dotted.split("."):
            obj = getattr(obj, part)
        objs.append(obj)
    parts = [inspect.getsource(o) for o in objs]
    for name in GUARD_SORTED_TABLES:
        parts.append(name + "=" + repr(sorted(getattr(ir, name))))
    for name in GUARD_PATTERNS:
        parts.append(name + "=" + getattr(ir, name).pattern)
    parts.append("CONC_PHRASES=" + repr(ir.CONC_PHRASES))
    parts.append(
        "EXTRA_ALIAS_GROUPS=" + repr(sorted(sorted(g) for g in ir.EXTRA_ALIAS_GROUPS))
    )
    parts.append("CONC_CLASS=" + repr(sorted(ir.CONC_CLASS.items())))
    parts.append("TEXT_MAX_CHARS=" + repr(ir.TEXT_MAX_CHARS))
    return "\n".join(parts)


def _guard_digest():
    return hashlib.sha256(_guard_text().encode("utf-8")).hexdigest()[:8]


def test_e22_guard_version_in_the_name(monkeypatch):
    """E22 (R-13, R-19): the GUARD_SET digest[:8] == PICK_GUARD_RULES (a guard edit bumps
    it); the prefix == "imgpick:v1:" + it + ":"; every name starts with it."""
    img = _img()
    rules = _need(img, "PICK_GUARD_RULES")
    assert re.fullmatch(r"[0-9a-f]{8}", rules), rules
    assert (
        _guard_digest() == rules
    ), "image_relevance guard source changed: bump PICK_GUARD_RULES"
    assert _need(img, "PICK_CACHE_PREFIX") == "imgpick:v1:" + rules + ":"
    assert _name(_rel("Acme", "Nimbus"), None).startswith("imgpick:v1:" + rules + ":")


@pytest.mark.parametrize("kind", ["rest", "stream"])
@pytest.mark.parametrize("late", [False, True])
def test_e23_drain_parity_cap_during_the_verdict(monkeypatch, caplog, kind, late):
    """E23 (R-11) parity pin: a page image, the job pending, a cap during the verdict: the
    sync partial and _emit_stream_deadline_partial (FULL deadline ON, stash ON) carry it,
    ON exactly as OFF. The job is held pending by a slow cache read (ON only), so the
    OFF run (and the base) finish Phase 1 at once and cap during the verdict too."""
    caplog.set_level(logging.INFO)
    _flags(
        monkeypatch,
        late=late,
        extra={
            "ENABLE_FULL_STREAM_DEADLINE": "true",
            "ENABLE_EARLY_SPECS_STASH": "true",
        },
    )
    t = _T()
    _install_tiers(monkeypatch, t, get_delay=1.5)
    st = {"gen_hang": True, "prices": {P0[0]: _price(P0[0], image=PAGE_A)}}
    out = _run(_compare(monkeypatch, kind, st, cap=1.0))
    body = out if kind == "rest" else _complete(out)
    assert (
        body.get("success") is True
        and (body.get("metadata") or {}).get("partial") is True
    )
    assert _pics(body)[0] == PAGE_A


def test_e24_no_llm_pick_after_the_life_closes(monkeypatch, caplog):
    """E24 (R-18): the life closed (the bind ran, or the deadline minus reserve passed):
    a passing organic item, extract_image_via_gpt 0 calls, tier llm_pick skipped."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    organic = {
        "organic": [
            {
                "title": TITLE0,
                "link": "https://" + SHOP + "/p/nimbus-noir",
                "snippet": "s",
            }
        ]
    }
    for state in (
        {"open": False, "until": None, "cached": False, "stored": False},
        {
            "open": True,
            "until": time.monotonic() - 1.0,
            "cached": False,
            "stored": False,
        },
    ):
        caplog.clear()
        t = _T()
        _install_tiers(monkeypatch, t, images=[], gpt_url=URL_GPT)

        async def go(st=state):
            return await _late_call(
                payload=await _done_fut(organic),
                variant="EDP 100ml",
                state=st,
                relevance=_relevance0(),
            )

        assert _run(go()) is None
        assert t.gpt == []
        pairs = [TIER.match(x).groups() for x in _lines(caplog, "[IMG_TIER] tier=")]
        assert ("llm_pick", "skipped") in pairs, pairs


@pytest.mark.parametrize("cap", [25.0, 30.0])
def test_e25_residual_from_the_run_deadline(monkeypatch, cap):
    """E25 (R-5): w = max(0, min(deadline - now - reserve, max_wait)), None -> 0, for a 25 s
    and a 30 s cap; a sync compare's bind reads _compare_deadline == entry + cap."""
    scs = _scs()
    fn = _need(scs, "_late_bind_wait_seconds")
    t0 = 1000.0
    assert fn(t0 + cap, t0 + cap - 4) == pytest.approx(2.0)
    assert fn(t0 + cap, t0 + cap - 1.5) == 0
    assert fn(t0 + cap, t0 + 5) == pytest.approx(3.0)
    assert fn(None, t0) == 0
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t)
    seen = []
    st = {}

    async def go():
        svc = scs.StructuredComparisonService()
        st["svc"] = svc
        orig = _need(svc, "_late_image_bind")

        async def spy():
            seen.append(svc._compare_deadline)
            return await orig()

        monkeypatch.setattr(svc, "_late_image_bind", spy)
        return await _compare(monkeypatch, "rest", st, cap=cap)

    _run(go())
    assert len(seen) == 1, seen
    assert abs(seen[0] - (st["entry_at"] + cap)) < 0.5, (seen, st["entry_at"])


def test_e26_override_first_and_empty_registry(monkeypatch, caplog):
    """E26 (R-14): the override hits, the job pending 5 s: the bind returns in < 0.2 s with
    wait_ms=0; an empty registry returns before any await."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch)
    t = _T()
    _install_tiers(monkeypatch, t, search_delay=5.0)
    box = {}

    async def go():
        svc = _scs().StructuredComparisonService()
        _fetch_setup(monkeypatch, svc, price=_price(P0[0], image=PAGE_A))
        result = await _fetch(svc)
        t0 = time.monotonic()
        await _need(svc, "_late_image_bind")()
        box["took"] = time.monotonic() - t0
        box["image"] = result.get("image_url")
        _entry(svc)["task"].cancel()
        await _drain_bg()
        fresh = _scs().StructuredComparisonService()
        coro = _need(fresh, "_late_image_bind")()
        try:
            coro.send(None)
            box["stop"] = False
        except StopIteration:
            box["stop"] = True
        finally:
            coro.close()

    _run(go())
    assert box["took"] < 0.2 and box["image"] == PAGE_A, box
    assert ("0", "override", "0") in _parse(BIND, _late(caplog, "bind"))
    assert box["stop"] is True


def test_e27_elapsed_includes_the_wait(monkeypatch, caplog):
    """E27 (R-15): the E4 setup: metadata.elapsed_seconds >= the bind wait."""
    body, st, t = _e04_run(monkeypatch, caplog)
    binds = [b for b in _parse(BIND, _late(caplog, "bind")) if b[0] == "0"]
    assert binds and binds[0][1] == "attached", binds
    wait = int(binds[0][2]) / 1000.0
    assert wait >= 0.3
    # metadata.elapsed_seconds is round(elapsed, 2) (response_builder.py, the
    # elapsed_seconds stamp), so it can sit up to 0.005 s BELOW the true time,
    # while the bind wait is whole milliseconds: allow half a centisecond of
    # rounding plus one millisecond (seen: 0.42 vs a wait of 0.421).
    assert body["metadata"]["elapsed_seconds"] >= wait - 0.006, (
        body["metadata"]["elapsed_seconds"],
        wait,
    )


PAGE_IMAGES = {
    "https": PAGE_A,
    "http": "http://" + STORE_A + "/img/nimbus-a.jpg",
    "none": None,
    "denied": "https://" + "fimgs" + ".net/mdimg/x.jpg",
}


def test_e28_chooser_parity_matrix(monkeypatch):
    """E28: over page image (https / http / None / denied) x V2 x DG2 x G x vision, the
    chooser == what the OFF _fetch_product_data writes with the cascade None."""
    scs = _scs()
    t = _T()
    _install_tiers(monkeypatch, t, images=[], gpt_url=None)
    combos = []
    for pk in sorted(PAGE_IMAGES):
        for v2 in (False, True):
            for dg2 in (False, True):
                for g in (False, True):
                    for vision in (False, True):
                        combos.append((pk, v2, dg2, g, vision))

    async def go():
        out = []
        for pk, v2, dg2, g, vision in combos:
            for env, on in (
                (FLAG, False),
                ("ENABLE_IMAGE_PIPELINE_V2", v2),
                ("ENABLE_DATA_GUARDS_V2", dg2),
                (G_FLAG, g),
            ):
                if on:
                    monkeypatch.setenv(env, "true")
                else:
                    monkeypatch.delenv(env, raising=False)
            price = _price(P0[0], image=PAGE_IMAGES[pk])
            svc = scs.StructuredComparisonService()
            _fetch_setup(monkeypatch, svc, price=price, payload={"organic": []})
            pinfo = dict(PINFO0, _vision=vision)
            result = await _fetch(svc, pinfo)
            out.append(((pk, v2, dg2, g, vision), result.get("image_url"), price))
        return out

    rows = _run(go())
    chooser = _need(scs, "_late_page_image_choice")
    for key, want, price in rows:
        _, v2, dg2, g, vision = key
        for env, on in (
            ("ENABLE_IMAGE_PIPELINE_V2", v2),
            ("ENABLE_DATA_GUARDS_V2", dg2),
            (G_FLAG, g),
        ):
            if on:
                monkeypatch.setenv(env, "true")
            else:
                monkeypatch.delenv(env, raising=False)
        assert chooser(copy.deepcopy(price), vision) == want, key


# ===========================================================================
# PIN rows (green at base)
# ===========================================================================


def _golden_case(mp, caplog, kind, *, late_value, resolver):
    caplog.clear()
    caplog.set_level(logging.INFO)
    _flags(mp, late=late_value, extra=dict(SYNTH_KNOBS))
    if resolver:
        mp.setenv(R_FLAG, "true")
    else:
        mp.delenv(R_FLAG, raising=False)
    t = _T()
    _install_tiers(mp, t)
    real_getenv = os.getenv
    seen = []

    def _rec(name, *a, **k):
        seen.append(name)
        return real_getenv(name, *a, **k)

    mp.setattr(os, "getenv", _rec)
    st = {"prices": {P0[0]: _price(P0[0], image=PAGE_A)}}
    try:
        out = _run(_compare(mp, kind, st))
    finally:
        mp.setattr(os, "getenv", real_getenv)
    body = out if kind == "rest" else _complete(out)
    snap = {
        "events": [e[0] for e in out] if kind == "stream" else None,
        "image_url": _pics(body),
        "tier": sorted(
            re.sub(r" ms=\d+$", "", x) for x in _lines(caplog, "[IMG_TIER]")
        ),
        "relevance": sorted(_lines(caplog, "[IMG_RELEVANCE]")),
        "l26": sorted(_lines(caplog, "[L2.6]")),
        "credit": len(t.credit),
        "search": len(t.search),
        "gpt": len(t.gpt),
    }
    checks = {
        "knob_reads": sorted(
            n
            for n in seen
            if isinstance(n, str) and n.startswith(("IMAGE_LATE", "IMAGE_PICK"))
        ),
        "cache_calls": len(t.get) + len(t.set),
        "credit_threads": sorted({c["thread"] for c in t.credit}),
        "late_lines": _lines(caplog, "IMG_LATE"),
        "registry": bool(getattr(st["svc"], "_late_images", None)),
    }
    return snap, checks


@pytest.mark.parametrize("resolver", [False, True])
@pytest.mark.parametrize("late_value", [None, "false"])
@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_p1_flag_off_golden(monkeypatch, caplog, kind, late_value, resolver):
    """P1 (B1): the flag unset and "false", the knobs synthetic, G and S ON, R OFF and ON:
    one sync and one stream compare == the base golden; no knob read; the cache fakes
    and the pool unused; no IMG_LATE line; no late registry."""
    snap, checks = _golden_case(
        monkeypatch, caplog, kind, late_value=late_value, resolver=resolver
    )
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert snap == golden[kind], (snap, golden[kind])
    assert checks["knob_reads"] == []
    assert checks["cache_calls"] == 0
    assert checks["credit_threads"] == ["MainThread"], checks["credit_threads"]
    assert checks["late_lines"] == []
    assert checks["registry"] is False


def test_p2_flag_off_keeps_the_5s_cut(monkeypatch, caplog):
    """P2: L OFF, Serper 5.6 s: None and the [L2.6] image race timeout line."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, late=False)
    t = _T()
    _install_tiers(monkeypatch, t, search_delay=5.6)

    async def go():
        svc = _scs().StructuredComparisonService()
        _fetch_setup(monkeypatch, svc)
        return await _fetch(svc)

    result = _run(go())
    assert result.get("image_url") is None
    assert "[L2.6] Phase 1 race timeout for image_url (limit 5.0s)" in _lines(
        caplog, "[L2.6]"
    )


CASCADE_SRC_SHA_BASE = (
    "3f3b8ad50c077e5408270f85373d8fe0a88100a15cace2ca186612590a14ad8b"
)


def test_p3_cascade_source_unchanged():
    """P3: get_product_image_url is not edited (sha256 of its source at base)."""
    src = inspect.getsource(_img().get_product_image_url)
    assert hashlib.sha256(src.encode("utf-8")).hexdigest() == CASCADE_SRC_SHA_BASE


@pytest.mark.parametrize("late", [False, True])
def test_p4_specs_event_and_source_trace_keep_the_image(monkeypatch, caplog, late):
    """P4: the specs event and the payload keep image_url, L OFF and ON; ON, the
    source_trace keeps products[i].races.image."""
    caplog.set_level(logging.INFO)
    _flags(monkeypatch, late=late)
    t = _T()
    _install_tiers(monkeypatch, t)
    st = {}
    out = _run(_compare(monkeypatch, "stream", st))
    specs = [e[1] for e in out if e[0] == "specs"]
    assert specs and all("image_url" in p for p in specs[0]["products"])
    body = _complete(out)
    assert all("image_url" in p for p in body["overview"]["products"])
    trace = (body.get("metadata") or {}).get("source_trace") or {}
    prods = trace.get("products") or []
    assert len(prods) == 2, trace
    for prod in prods:
        assert "image" in prod.get("races", {}), prod


def test_p5_flag_off_credit_on_the_loop(monkeypatch):
    """P5: L OFF: the credit fake runs on the loop thread."""
    _flags(monkeypatch, late=False)
    t = _T()
    _install_tiers(monkeypatch, t)

    async def go():
        svc = _scs().StructuredComparisonService()
        _fetch_setup(monkeypatch, svc)
        await _fetch(svc)
        return threading.current_thread().name

    loop_thread = _run(go())
    assert t.credit and all(c["thread"] == loop_thread for c in t.credit), t.credit
