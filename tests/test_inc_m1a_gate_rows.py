"""INC-M1a fix round 1 gate rows (FIX1_RULINGS_INC_M1a FX2): the short-token (SR) and the
model-guard (MG) pins of the resolver fold.

SR (adversary M1, mutant X1): the one-character exact rule of the lexicon arm's D5 line
search keeps every short typed token off the seeded line Y, and the exact Y spellings still
resolve to it. Golden: INC-M1a_green/probe_short_after.txt.

MG (adversary B1): the INC-R1 model-arm guard (d) `_line_within_typed` keeps the base D5 rule
(a one-character line token of a MODEL answer still matches within one edit), so the base
accepts stay accepted (Chanel N-degree-5, Terre d'Hermes, Bois d'Argent, L'Homme, L'Eau
d'Issey) and the base refusals stay refused. Inputs from INC-M1a_adv/probe_guard.txt and
probe_accept.txt; the end-to-end rows use the r21 seam of tests/test_inc_r1_resolver.py
(resolve_pair with the model arm reachable: the flag ON, ENABLE_ANTHROPIC_TEXT ON, consent 3,
a synthetic key, the fake SDK of tests/test_inc_r1_seam.py).

Hermetic: no network (the conftest netguard and the fake anthropic module / OpenAI client),
no .env, no real credential (the synthetic key is built at run time in the seam module).
Flags set explicitly in every row. Pure ASCII, LF: every non-ASCII character is built with
chr() at run time.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest

import app.main  # noqa: F401  (FIRST: the dotenv guard)
from app.services import api_budget_service as abs_
from app.services import category_gate as cg
from app.services import llm_router as lr
from app.services import openai_service as osvc
from app.services import product_resolver as pr
from app.utils import request_context as rc
from tests import test_inc_r1_seam as r1s

FLAG = "ENABLE_PRODUCT_RESOLVER"
YSL = "Yves Saint Laurent"
DEG = chr(0xB0)
E_GRAVE = chr(0xE8)
AR_YA = chr(0x064A)
AR_WAW = chr(0x0648)
PARTNER = "Dior Sauvage EDP"
EXTRA_CLEAR = ("ENABLE_URL_LINK_RESULT", "ENABLE_MATCH_FOLD")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in tuple(r1s.CLEAR) + EXTRA_CLEAR:
        monkeypatch.delenv(name, raising=False)
    for name in list(os.environ):
        if name.startswith("ANTHROPIC_") or name.startswith("PRODUCT_RESOLVER_"):
            monkeypatch.delenv(name, raising=False)
    r1s.ANTH.__init__()
    del r1s.OAI_CALLS[:]
    r1s.CONSENT["value"] = None
    monkeypatch.setitem(sys.modules, "anthropic", r1s._fake_anthropic_module())
    monkeypatch.setattr(
        lr, "_anthropic_client_factory", lambda **kw: r1s._FakeAnthropicClient(**kw)
    )
    monkeypatch.setattr(osvc, "get_client", lambda: r1s._OaiClient())
    monkeypatch.setattr(
        rc, "consent_version", lambda: r1s.CONSENT["value"], raising=False
    )
    monkeypatch.setattr(
        rc,
        "header_state",
        lambda name: "ok" if isinstance(r1s.CONSENT["value"], int) else "absent",
        raising=False,
    )
    for name in ("_redis_get", "_redis_set", "_redis_incr", "_redis_expire"):
        monkeypatch.setattr(abs_, name, lambda *a, **k: None, raising=False)
    monkeypatch.setattr(abs_, "is_circuit_closed", lambda *a, **k: True, raising=False)
    lr._reset_router_state()
    pr._reset_resolver_state()
    cg._reset_lexicon_cache()
    try:
        yield
    finally:
        lr._reset_router_state()
        pr._reset_resolver_state()
        cg._reset_lexicon_cache()


def _model_on(monkeypatch):
    """The r21 seam: the flag ON with the model arm reachable (TEXT ON, consent 3)."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(r1s.TIMEOUT, "5.0")
    monkeypatch.setenv(r1s.ASK, "1")
    monkeypatch.setenv(r1s.TEXT, "true")
    monkeypatch.setenv(r1s.PRE, "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", r1s.SYN_KEY)
    monkeypatch.setenv("ENABLE_REQUEST_CONTEXT_HEADERS", "true")
    r1s.CONSENT["value"] = 3


def _set_flag(monkeypatch, flag):
    if flag is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag)


def _side_tuple(side):
    return (
        side.resolved,
        side.brand,
        side.line,
        side.concentration,
        side.confidence,
        side.source,
        side.flanker,
    )


# ======================================================================= SR the short tokens

UNRESOLVED = (False, None, None, None, "medium", "none", None)

SR_NOT = [
    ("lhomme", "YSL L'Homme"),
    ("yves_lhomme", "Yves Saint Laurent L'Homme"),
    ("b", "YSL B"),
    ("by", "YSL by"),
    ("x", "YSL X"),
    ("one", "YSL 1"),
    ("ya", "YSL Ya"),
    ("yo", "YSL Yo"),
    ("ar_ya", "YSL " + AR_YA),
    ("ar_waw", "YSL " + AR_WAW),
]

SR_MUST = [
    ("y", "Y", "EDT", None),
    ("y_edp", "Y EDP", "EDP", None),
    ("ysl_y", "YSL Y", "EDT", None),
    ("saint_laurent_y", "Saint Laurent Y", "EDT", None),
    ("ysl_y_edp", "YSL Y EDP", "EDP", None),
    ("ysl_y_elixir", "YSL Y Elixir", "Elixir", "Elixir"),
]


@pytest.mark.parametrize("flag", ["true", "false"], ids=["on", "off"])
@pytest.mark.parametrize("name", [c[1] for c in SR_NOT], ids=[c[0] for c in SR_NOT])
def test_sr1_short_token_never_resolves_to_line_y(monkeypatch, name, flag):
    """SR (M1R-11 (d)): a short typed token next to the YSL house never resolves high to
    (Yves Saint Laurent, Y); the side stays medium / source none (the green golden)."""
    _set_flag(monkeypatch, flag)
    side = pr.resolve_lexicon(name)
    assert (side.brand, side.line) != (YSL, "Y"), side
    assert _side_tuple(side) == UNRESOLVED, side


@pytest.mark.parametrize("flag", ["true", "false"], ids=["on", "off"])
@pytest.mark.parametrize(
    "name,conc,flanker", [c[1:] for c in SR_MUST], ids=[c[0] for c in SR_MUST]
)
def test_sr2_exact_y_resolves_to_line_y(monkeypatch, name, conc, flanker, flag):
    """SR: the exact Y spellings resolve high/lexicon to (Yves Saint Laurent, Y)."""
    _set_flag(monkeypatch, flag)
    side = pr.resolve_lexicon(name)
    assert _side_tuple(side) == (True, YSL, "Y", conc, "high", "lexicon", flanker), side
    assert side.is_fragrance is True, side


# ======================================================================= MG the model-arm guard

# (id, typed, model brand, model line, guard at base, accepted concentration at base)
MG_ACCEPT = [
    ("no5", "Chanel No 5", "Chanel", "N" + DEG + "5", None),
    ("no5_edp", "Chanel No 5 Eau de Parfum", "Chanel", "N" + DEG + "5", "EDP"),
    ("no5_space", "Chanel No 5", "Chanel", "N" + DEG + " 5", None),
    ("no5_dot", "Chanel No. 5", "Chanel", "N" + DEG + "5", None),
    ("no5_leau", "Chanel No 5 L'Eau", "Chanel", "N" + DEG + "5 L'Eau", None),
    ("terre", "Hermes Terre de Hermes", "Hermes", "Terre d'Herm" + E_GRAVE + "s", None),
    ("bois", "Dior Bois de Argent", "Dior", "Bois d'Argent", None),
    ("lhomme", "Prada Le Homme", "Prada", "L'Homme", None),
    ("leau_issey", "Issey Miyake L Eau De Issey", "Issey Miyake", "L'Eau d'Issey", None),
]

# accepted at base AND at the GREEN head (pins of the rule's untouched part)
MG_ACCEPT_BOTH = [
    ("no_5", "Chanel No 5", "Chanel", "No 5"),
    ("terre_d", "Hermes Terre d Hermes", "Hermes", "Terre d'Herm" + E_GRAVE + "s"),
    ("l_homme", "Prada L Homme", "Prada", "L'Homme"),
    ("a_men", "Mugler A Men", "Mugler", "A*Men"),
    ("million", "Paco Rabanne 1 Million", "Paco Rabanne", "1 Million"),
    ("ysl_y", "YSL Y", YSL, "Y"),
]

# refused by the guard at base (a model line not within the typed text)
MG_REFUSE = [
    ("n5", "Chanel N5", "Chanel", "N" + DEG + "5"),
    ("number5", "Chanel Number 5", "Chanel", "N" + DEG + "5"),
    ("no5_leau_joined", "Chanel No 5 Leau", "Chanel", "N" + DEG + "5 L'Eau"),
    ("coco", "Chanel No 5", "Chanel", "Coco Mademoiselle"),
    ("luna", "Prada Luna Rossa", "Prada", "L'Homme"),
]


def _guard(typed, brand, line):
    pr._reset_resolver_state()
    return pr._line_within_typed(brand, line, pr._core(typed), pr._index())


def _answer_side(brand, line):
    return {
        "brand": brand,
        "line": line,
        "is_fragrance": True,
        "confidence": "high",
        "candidates": [],
        "concentration": "none",
    }


@pytest.mark.parametrize(
    "typed,brand,line",
    [c[1:4] for c in MG_ACCEPT] + [c[1:] for c in MG_ACCEPT_BOTH],
    ids=[c[0] for c in MG_ACCEPT] + [c[0] for c in MG_ACCEPT_BOTH],
)
def test_mg1_guard_accepts_as_at_base(monkeypatch, typed, brand, line):
    """MG (B1): guard (d) finds the model line within the typed text under the BASE D5
    rule (a one-character line token within one edit), as at base 9bc13109."""
    _set_flag(monkeypatch, "true")
    assert _guard(typed, brand, line) is True, (typed, line)


@pytest.mark.parametrize(
    "typed,brand,line", [c[1:] for c in MG_REFUSE], ids=[c[0] for c in MG_REFUSE]
)
def test_mg2_guard_refuses_as_at_base(monkeypatch, typed, brand, line):
    """MG: the guard still refuses a model line that is not within the typed text."""
    _set_flag(monkeypatch, "true")
    assert _guard(typed, brand, line) is False, (typed, line)


@pytest.mark.parametrize(
    "typed,brand,line,conc", [c[1:] for c in MG_ACCEPT], ids=[c[0] for c in MG_ACCEPT]
)
def test_mg3_accept_model_side_as_at_base(monkeypatch, typed, brand, line, conc):
    """MG: accept_model_side accepts the high-confidence fragrance answer (source llm)."""
    _set_flag(monkeypatch, "true")
    det = pr.resolve_lexicon(typed)
    assert det.resolved is False, det
    got = pr.accept_model_side(typed, _answer_side(brand, line), det)
    assert (got.resolved, got.source, got.confidence) == (True, "llm", "high"), got
    assert (got.brand, got.line, got.concentration) == (brand, line, conc), got
    assert got.is_fragrance is True, got


@pytest.mark.parametrize(
    "typed,brand,line", [c[1:] for c in MG_REFUSE], ids=[c[0] for c in MG_REFUSE]
)
def test_mg4_accept_model_side_refuses_as_at_base(monkeypatch, typed, brand, line):
    """MG: accept_model_side refuses the answer whose line is not within the typed text."""
    _set_flag(monkeypatch, "true")
    det = pr.resolve_lexicon(typed)
    got = pr.accept_model_side(typed, _answer_side(brand, line), det)
    assert (got.resolved, got.source, got.brand, got.line) == (False, "none", None, None), got


def _resolve_model(monkeypatch, typed, brand, line):
    _model_on(monkeypatch)
    junk = r1s._side("false", "Acme", "Nothing", "none", "low")
    r1s.ANTH.default = r1s.c_msg(
        r1s._answer(r1s._side("true", brand, line, "none", "high"), junk)
    )
    pr._reset_resolver_state()
    r = asyncio.run(pr.resolve_pair([typed, PARTNER], selected_category=None))
    assert len(r1s.ANTH.calls) == 1, r1s.ANTH.calls
    b = r.sides[1]
    assert (b.resolved, b.brand, b.line, b.concentration, b.source) == (
        True,
        "Dior",
        "Sauvage",
        "EDP",
        "lexicon",
    ), b
    assert r1s.OAI_CALLS == [], r1s.OAI_CALLS
    return r


@pytest.mark.parametrize(
    "typed,brand,line,conc", [c[1:] for c in MG_ACCEPT], ids=[c[0] for c in MG_ACCEPT]
)
def test_mg5_model_arm_pair_resolves_as_at_base(monkeypatch, typed, brand, line, conc):
    """MG end to end (the r21 seam): with the model arm reachable the model-answered side
    is accepted (source llm, high) and the pair outcome is resolved, never ask."""
    r = _resolve_model(monkeypatch, typed, brand, line)
    got = r.sides[0]
    assert (got.resolved, got.source, got.confidence) == (True, "llm", "high"), got
    assert (got.brand, got.line, got.concentration) == (brand, line, conc), got
    assert r.outcome == "resolved", r.outcome


@pytest.mark.parametrize(
    "typed,brand,line",
    [c[1:] for c in MG_REFUSE if c[0] in ("coco", "luna")],
    ids=["coco", "luna"],
)
def test_mg6_model_arm_pair_refused_as_at_base(monkeypatch, typed, brand, line):
    """MG end to end: a model line outside the typed text is refused by the guard, so the
    side stays unresolved and the fragrance-intended pair asks (PRODUCT_RESOLVER_ASK=1)."""
    r = _resolve_model(monkeypatch, typed, brand, line)
    got = r.sides[0]
    assert (got.resolved, got.source, got.brand, got.line) == (False, "none", None, None), got
    assert r.outcome == "ask", r.outcome


def test_mg7_answer_payload_is_ascii_json():
    """Hygiene: the fake answer the MG rows send is JSON text built at run time."""
    text = r1s._answer(r1s._side("true", "Chanel", "N" + DEG + "5"), r1s._side("false"))
    assert json.loads(text)["a"]["line"] == "N" + DEG + "5"
