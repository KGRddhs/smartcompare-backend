"""INC-I2b GUARD-WORDS + SHOP-IMAGE-TIER: the GREEN addenda rows AX-1..AX-7.

Gate: s96/i2b/GATE_INC_I2B.md (GB-4, GB-6, GB-7, GB-8). The frozen RED file
tests/test_inc_i2b_guard_words_shop_image.py stays frozen; these rows add:

* AX-1..AX-3 (GB-8, the Arabic probe ARABIC_PROBE.md): the unit changes nothing for an
  Arabic-script typed name. Pass at base and at the head.
* AX-4 (GB-4): the ``_typed_name`` carrier (G, W and R ON) never reaches a response body,
  a stream event, the verdict call, a model prompt or a log line; no IMG_ line carries
  the typed text. May pass at base trivially.
* AX-5 (GB-6): the A reader is read exactly once per WooCommerce match call that has a
  winner, and never for a call without one. Fails at base (0 != 1).
* AX-6 (GB-7, E13): the caps. L OFF: a Phase-1 cap before the B block leaves no
  thumbnail; L ON: the hard-cap drain keeps the base outcome. Each half opens with its
  positive control (the thumbnail when no cap fires), which fails at base.
* AX-7 (GB-7, E8): L ON + W ON: the late get_cached name carries the w axis; a pick
  stored under s1w0 is never read with W ON. Fails at base.

Arabic text is built from code points (chr of hex ints) so this file stays ASCII. Every
symbol absent at base is read through getattr / hasattr so a base failure is an
AssertionError only. Hermetic: the RED file's fakes (Serper / credit / LLM leaves, the
image cache, the fetch legs) and the INC-R1 seam's FY25 harness; no network. Pure ASCII.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

from tests import test_inc_i2b_guard_words_shop_image as red  # noqa: E402

W_FLAG = red.W_FLAG
A_FLAG = red.A_FLAG


def _ar(*code_points):
    return "".join(chr(c) for c in code_points)


# ---- the Arabic words of ARABIC_PROBE.md (code points only) -----------------------
AR_DIOR = _ar(0x062F, 0x064A, 0x0648, 0x0631)
AR_SAUVAGE = _ar(0x0633, 0x0648, 0x0641, 0x0627, 0x062C)
AR_BLEU = _ar(0x0628, 0x0644, 0x0648)
AR_DO = _ar(0x062F, 0x0648)
AR_DI = _ar(0x062F, 0x064A)
AR_CHANEL = _ar(0x0634, 0x0627, 0x0646, 0x064A, 0x0644)
AR_PERFUME = _ar(0x0639, 0x0637, 0x0631)
AR_EAU = _ar(0x0627, 0x0648)
AR_PARFUM = _ar(0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646)
AR_ML = _ar(0x0645, 0x0644)
AR_MEN = _ar(0x0644, 0x0644, 0x0631, 0x062C, 0x0627, 0x0644)
AR_GIFT = _ar(0x0647, 0x062F, 0x064A, 0x0629)
AR_GIFTS = _ar(0x0647, 0x062F, 0x0627, 0x064A, 0x0627)

#: The two placeholders (ar.json home.compare.box_a_text / box_b_text).
PH_A = " ".join((AR_DIOR, AR_SAUVAGE, "EDP"))
PH_B = " ".join((AR_BLEU, AR_DO, AR_CHANEL, "EDP"))

TITLES = {
    "dior": [
        "Dior Sauvage Eau de Parfum 100ml",
        "Sauvage Dior cologne - a fragrance for men 2015",
        " ".join(
            (AR_PERFUME, AR_DIOR, AR_SAUVAGE, AR_EAU, AR_DO, AR_PARFUM, "100", AR_ML)
        ),
        "Dior Sauvage EDP Spray for Men",
    ],
    "chanel": [
        "Bleu de Chanel Eau de Parfum Spray 100ml",
        "CHANEL BLEU DE CHANEL EDP",
        " ".join((AR_PERFUME, AR_BLEU, AR_DI, AR_CHANEL, AR_EAU, AR_DO, AR_PARFUM)),
        " ".join((AR_BLEU, AR_DO, AR_CHANEL, "-", AR_CHANEL, "-", AR_PERFUME, AR_MEN)),
    ],
}

#: (label, brand, line, title key, the base check() reasons per title) as measured by
#: the orchestrator's probe at 5cd93c6a (arprobe/out_on.txt; S OFF identical).
AR_ROWS = (
    ("A brand=latin", "Dior", PH_A, "dior", ["name", "name", "brand", "name"]),
    ("A brand=arabic", AR_DIOR, PH_A, "dior", ["brand", "brand", None, "brand"]),
    ("A brand=empty", "", PH_A, "dior", ["name", "name", None, "name"]),
    ("B brand=latin", "Chanel", PH_B, "chanel", ["name", "name", "brand", "brand"]),
    ("B brand=arabic", AR_CHANEL, PH_B, "chanel", ["brand", "brand", None, None]),
    ("B brand=empty", "", PH_B, "chanel", ["name", "name", None, None]),
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in red.CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    yield


def _ascii_file():
    with open(__file__, "rb") as fh:
        return all(b < 128 for b in fh.read())


# ---------------------------------------------------------------------------
# AX-1..AX-3: Arabic-script typed names (GB-8)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("s_on", [True, False])
def test_ax1_arabic_placeholders_same_reason_w_unset_and_on(monkeypatch, s_on):
    """AX-1: both placeholders typed, R OFF: per candidate the check() reason is the base
    probe's reason with W unset AND with W ON (brands Latin, Arabic, empty)."""
    assert _ascii_file()
    ir = red._ir()
    for label, brand, line, key, want in AR_ROWS:
        rel = red._rel(brand, line, line)
        got = {}
        for w in (None, True):
            red._flags(monkeypatch, s=s_on, w=w)
            ident = ir.identity(line, rel)
            got[w] = [ir.check(ident, [t]) for t in TITLES[key]]
        assert got[None] == want, (label, got[None])
        assert got[True] == got[None], (label, got)


def test_ax2_post_m1_identity_accepts_latin_titles(monkeypatch):
    """AX-2: the post-INC-M1 identity (Latin brand and line, the Arabic typed product
    name) accepts the Latin titles with W ON; the Arabic titles stay refused at brand
    (L15)."""
    ir = red._ir()
    rows = (
        ("Dior", "Sauvage EDP", PH_A, "dior", [None, None, "brand", None]),
        (
            "Chanel",
            "Bleu de Chanel EDP",
            PH_B,
            "chanel",
            [None, None, "brand", "brand"],
        ),
    )
    for brand, line, typed, key, want in rows:
        for w in (None, True):
            red._flags(monkeypatch, w=w)
            ident = ir.identity(typed, red._rel(brand, line, typed))
            got = [ir.check(ident, [t]) for t in TITLES[key]]
            assert got == want, (brand, w, got)


def test_ax3_arabic_gift_word_alone_never_refuses(monkeypatch):
    """AX-3 (I-10): an Arabic title carrying an Arabic gift word alone is not refused by
    W (an Arabic-script identity that accepts the title at base)."""
    ir = red._ir()
    base_title = TITLES["dior"][2]
    for gift in (AR_GIFT, AR_GIFTS):
        for title in (base_title + " " + gift, gift + " " + base_title):
            for w in (None, True):
                red._flags(monkeypatch, w=w)
                ident = ir.identity(PH_A, red._rel(AR_DIOR, PH_A, PH_A))
                assert ir.check(ident, [title]) is None, (w, title.encode("utf-8"))
                ident = ir.identity(PH_A, red._rel("", PH_A, PH_A))
                assert ir.check(ident, [title]) is None, (w, title.encode("utf-8"))


# ---------------------------------------------------------------------------
# AX-4: the carrier never leaks (GB-4)
# ---------------------------------------------------------------------------


def _r1_env(mp, r1):
    """The INC-R1 seam's autouse setup (its fakes), applied for this row only."""
    for name in r1.CLEAR:
        mp.delenv(name, raising=False)
    for name in list(os.environ):
        if name.startswith("ANTHROPIC_") or name.startswith("PRODUCT_RESOLVER_"):
            mp.delenv(name, raising=False)
    r1.ANTH.__init__()
    del r1.OAI_CALLS[:]
    r1.CONSENT["value"] = None
    r1.scs._DEBUG_STAGE_TIMINGS = None
    mp.setitem(sys.modules, "anthropic", r1._fake_anthropic_module())
    mp.setattr(
        r1.lr, "_anthropic_client_factory", lambda **kw: r1._FakeAnthropicClient(**kw)
    )
    mp.setattr(r1.osvc, "get_client", lambda: r1._OaiClient())
    mp.setattr(r1.rc, "consent_version", lambda: r1.CONSENT["value"], raising=False)
    mp.setattr(
        r1.rc,
        "header_state",
        lambda name: "ok" if isinstance(r1.CONSENT["value"], int) else "absent",
        raising=False,
    )
    for name in ("_redis_get", "_redis_set", "_redis_incr", "_redis_expire"):
        mp.setattr(r1.abs_, name, lambda *a, **k: None, raising=False)
    mp.setattr(r1.abs_, "is_circuit_closed", lambda *a, **k: True, raising=False)
    r1.lr._reset_router_state()
    mod = sys.modules.get(r1.PR_NAME)
    if mod is not None and hasattr(mod, "_reset_resolver_state"):
        mod._reset_resolver_state()


def _r1_reset(r1):
    r1.scs._DEBUG_STAGE_TIMINGS = None
    r1.lr._reset_router_state()
    mod = sys.modules.get(r1.PR_NAME)
    if mod is not None and hasattr(mod, "_reset_resolver_state"):
        mod._reset_resolver_state()


def _ax4_images(query):
    q = str(query).lower()
    if "chanel" in q or "bleu" in q:
        return [
            red._item(
                "https://" + red.IMG_HOST + "/p/bleu-edp.jpg",
                "Chanel Bleu de Chanel Eau de Parfum 100ml",
                "bleu",
            )
        ]
    return [red._item(red.URL_EDP, "Dior Sauvage Eau de Parfum 100ml", "edp")]


def _ax4_compare(mp, r1, kind, w):
    """One compare of the GOLD4 pair (R, G, S ON; W as given) through the FY25 harness
    with the real image cascade on the RED file's tier fakes."""
    r1._full(mp)
    red._flags(mp, w=w)
    t = red._T()
    red._install_tiers(mp, t, images=_ax4_images)
    seen = {"relevance": [], "verdict": []}
    img = red._img()
    real_gpu = img.get_product_image_url

    def extra(p, svc, state):
        async def _gpu(*a, **k):
            seen["relevance"].append(copy.deepcopy(k.get("relevance")))
            return await real_gpu(*a, **k)

        p.setattr(r1.scs, "get_product_image_url", _gpu)
        fy_gen = r1.scs.generate_comparison

        async def _gen(*a, **k):
            seen["verdict"].append(repr((a, k)))
            return await fy_gen(*a, **k)

        p.setattr(r1.scs, "generate_comparison", _gen)

    payload, state, _svc = r1._run(kind, r1.GOLD4, chip="fragrances", extra=extra)
    return payload, state, seen


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_ax4_carrier_never_leaks(monkeypatch, caplog, kind):
    """AX-4 (GB-4): G, W and R ON, one sync and one stream compare: no ``_typed_name`` in
    the response / the events, the verdict call, a model prompt or any log line; the
    payload's underscore keys equal the W OFF run's; no IMG_ line holds the typed
    text."""
    from tests import test_inc_r1_seam as r1

    _r1_env(monkeypatch, r1)
    try:
        off_payload, _s, _seen = _ax4_compare(monkeypatch, r1, kind, None)
        caplog.clear()
        with caplog.at_level(logging.INFO):
            payload, state, seen = _ax4_compare(monkeypatch, r1, kind, True)
        body = r1._success_body(kind, payload)
        assert body.get("success") is True, body.get("error")
        dumped = json.dumps(payload, default=str)
        assert "_typed_name" not in dumped
        assert sorted(r1._underscore_keys(payload, [])) == sorted(
            r1._underscore_keys(off_payload, [])
        )
        for call in seen["verdict"]:
            assert "_typed_name" not in call
        assert "_typed_name" not in json.dumps(r1.ANTH.calls, default=str)
        assert "_typed_name" not in json.dumps(r1.OAI_CALLS, default=str)
        msgs = [r.getMessage() for r in caplog.records]
        assert not [m for m in msgs if "_typed_name" in m]
        img_lines = [m for m in msgs if m.startswith(("[IMG_", "IMG_"))]
        for m in img_lines:
            low = m.lower()
            for word in ("sauvage", "chanel", "bleu", "dior", "edp"):
                assert word not in low, m
        if hasattr(r1.scs, "_typed_image_text"):
            # Non-vacuous at the head: the carrier exists on the fetch input and the
            # typed text reaches the guard's relevance (and nothing further).
            typed = [
                p.get("_typed_name")
                for p in state["fetch_products"]
                if p.get("name") == "Sauvage"
            ]
            assert typed == ["Dior Sauvage EDP"], state["fetch_products"]
            rels = [r for r in seen["relevance"] if r and r.get("line") == "Sauvage"]
            assert rels and rels[0].get("typed") == "Dior Sauvage EDP", rels
            assert [m for m in img_lines if m.startswith("[IMG_RELEVANCE]")]
    finally:
        _r1_reset(r1)


# ---------------------------------------------------------------------------
# AX-5: the A reader, exactly once per match call with a winner (GB-6)
# ---------------------------------------------------------------------------


def test_ax5_shop_reader_once_per_winner_call(monkeypatch):
    """AX-5 (GB-6, P5 strict): ENABLE_SHOP_PAGE_IMAGE is read exactly once per
    WooCommerce match call that has a winner (A unset and A ON) and 0 times for a call
    without one."""
    woo = red._woo()
    real = os.getenv
    seen = []

    def rec(name, *a):
        seen.append(name)
        return real(name, *a)

    win = [red._woo_prod("Lattafa Khamrah Eau de Parfum", red.WOO_A)]
    lose = [red._woo_prod("Acme Other Thing", red.WOO_A)]
    for a in (None, True):
        red._flags(monkeypatch, a=a)
        monkeypatch.setattr(os, "getenv", rec)
        del seen[:]
        best = woo._match_woo_product(win, "Lattafa Khamrah", "BHD", "fragrances")
        assert best is not None
        assert seen.count(A_FLAG) == 1, (a, seen.count(A_FLAG))
        del seen[:]
        assert woo._match_woo_product(win, "Lattafa Khamrah", "BHD", "fragrances")
        assert woo._match_woo_product(win, "Lattafa Khamrah", "BHD", "fragrances")
        assert seen.count(A_FLAG) == 2, (a, seen.count(A_FLAG))
        del seen[:]
        none = woo._match_woo_product(lose, "Lattafa Khamrah", "BHD", "fragrances")
        assert none is None
        assert seen.count(A_FLAG) == 0, (a, seen.count(A_FLAG))
        monkeypatch.setattr(os, "getenv", real)


# ---------------------------------------------------------------------------
# AX-6: the caps (GB-7, E13)
# ---------------------------------------------------------------------------


def _thumb_recorder(mp):
    img = red._img()
    real = getattr(img, "shopping_thumbnail", None)
    calls = []

    def rec(*a, **k):
        calls.append(1)
        return real(*a, **k) if real is not None else None

    mp.setattr(img, "shopping_thumbnail", rec, raising=False)
    return calls


def _capped_fetch(mp, *, late):
    """A _fetch_product_data cut by an outer cap while the price leg hangs (the Shopping
    items are already cached, so only the cap keeps the B block from running). L ON: the
    hard-cap drain runs after the cut. Returns (service, the slot-0 late entry)."""
    scs = red._scs()

    async def go():
        svc = scs.StructuredComparisonService()
        red._fetch_setup(mp, svc, shopping=red._shop_items())

        async def _hang(brand, name, variant, *a, **_k):
            key = scs._shopping_cache_key(brand, name, variant)
            svc._shopping_items_cache[key] = copy.deepcopy(red._shop_items())
            await asyncio.sleep(30)

        svc._get_price = _hang
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                svc._fetch_product_data(
                    dict(red.PINFO0), "bahrain", True, True, True, partial_slot=0
                ),
                0.8,
            )
        if late:
            svc._late_image_drain_now()
        entry = (getattr(svc, "_late_images", None) or {}).get(0)
        await red._drain_bg(limit=6.0)
        return svc, entry

    return red._run(go())


def test_ax6_caps_l_off_cap_skips_the_thumb(monkeypatch, caplog):
    """AX-6 L OFF: positive control (no cap) -> the thumbnail; a Phase-1 cap before the
    B block -> shopping_thumbnail 0 calls, no IMG_SHOP thumb line."""
    caplog.set_level(logging.INFO)
    red._flags(monkeypatch, b=True)
    monkeypatch.setenv("IMAGE_LATE_MAX_SECONDS", "2")
    calls = _thumb_recorder(monkeypatch)
    t = red._T()
    red._install_tiers(monkeypatch, t, images=[])
    r = red._fetch_run(monkeypatch, shopping=red._shop_items())
    assert r.get("image_url") == red.THUMB_RIGHT, r.get("image_url")
    assert calls == [1], calls
    del calls[:]
    caplog.clear()
    _capped_fetch(monkeypatch, late=False)
    assert calls == [], calls
    assert red._msgs(caplog, "IMG_SHOP thumb") == []


def test_ax6_caps_l_on_drain_keeps_the_base_outcome(monkeypatch, caplog):
    """AX-6 L ON: positive control (no cap) -> bind shopping with the thumbnail; the
    hard-cap drain before the B block -> the base outcome (none / missed_at_deadline),
    never shopping, no thumbnail, shopping_thumbnail 0 calls."""
    caplog.set_level(logging.INFO)
    red._flags(monkeypatch, b=True, late=True)
    monkeypatch.setenv("IMAGE_LATE_MAX_SECONDS", "2")
    calls = _thumb_recorder(monkeypatch)
    t = red._T()
    red._install_tiers(monkeypatch, t, images=[], gpt_url=None)
    r = red._fetch_run(monkeypatch, shopping=red._shop_items(), bind=True)
    assert r.get("image_url") == red.THUMB_RIGHT, r.get("image_url")
    binds = [red.BIND.match(m).groups()[1] for m in red._msgs(caplog, "IMG_LATE bind")]
    assert binds == ["shopping"], binds
    del calls[:]
    caplog.clear()
    _svc, entry = _capped_fetch(monkeypatch, late=True)
    assert entry is not None and "shop_thumb" not in entry, entry
    assert entry["result"].get("image_url") != red.THUMB_RIGHT
    binds = [red.BIND.match(m).groups()[1] for m in red._msgs(caplog, "IMG_LATE bind")]
    assert len(binds) == 1 and binds[0] in ("none", "missed_at_deadline"), binds
    assert calls == [], calls


# ---------------------------------------------------------------------------
# AX-7: the late cache name carries the w axis (GB-7, E8)
# ---------------------------------------------------------------------------


def test_ax7_late_cache_name_carries_the_w_axis(monkeypatch):
    """AX-7 (E8 L ON half): L ON + W ON: the late get_cached name is the s1w1:EDP name
    (typed EDP); W unset: s1w0; a pick stored under s1w0 is never read with W ON."""
    rel = {"category": "fragrances", "brand": "Acme", "line": "Nimbus Noir"}
    variant = red.PINFO0["variant"]
    name_w0 = red._expected_name(rel, variant, "s1w0")
    name_w1 = red._expected_name(rel, variant, "s1w1:EDP")
    stale = "https://" + red.IMG_HOST + "/p/stale-w0.jpg"
    right = red._item(red.URL_S0, "Acme Nimbus Noir Eau de Parfum 100ml", "s0")

    red._flags(monkeypatch, late=True, w=True)
    t = red._T()
    red._install_tiers(monkeypatch, t, images=[right])
    t.store[name_w0] = {"u": stale}
    r = red._fetch_run(monkeypatch, bind=True)
    assert t.get == [name_w1], (t.get, name_w1)
    assert r.get("image_url") != stale
    assert r.get("image_url") == red.URL_S0, r.get("image_url")
    assert name_w1 in t.set, t.set

    red._flags(monkeypatch, late=True, w=None)
    t = red._T()
    red._install_tiers(monkeypatch, t, images=[right])
    red._fetch_run(monkeypatch, bind=True)
    assert t.get == [name_w0], (t.get, name_w0)
