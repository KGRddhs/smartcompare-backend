"""S81-12d OPENAI-EGRESS-STOP: the gate rows of GATE_S81_12D (GC-5, GC-9).

Written by the GREEN round, never the frozen RED files. It imports helpers (not
tests, not fixtures) from frozen file A, as frozen file B does.

G1 (GC-5, RED question 1): the sixth OpenAI dispatch function at this base is
MON1's active check, llm_credential_probe._metadata_call (the models call of its
openai branch). Besides the in-use rule (ruling K-2 3.11), the function itself
gets its own guard H5: the FIRST statement of the openai branch raises
OpenAIEgressStoppedError(OPENAI_EGRESS_STOP_MESSAGE) while
api_budget_service.openai_egress_stop_enabled() is true, read by module attribute
through a function-local import, NOT through stop_openai_egress_if_enabled (the
frozen census S12D-20 keeps that helper to its four functions), with no log line.

- G1 (behaviour): a direct call of _metadata_call("openai") with the stop ON
  raises the stop class and the transport recorder sees ZERO requests; with the
  stop off it makes its one models request (401 from the recorder) as at base
  (the PIN half). Killed by mutant GM-1 (the guard removed).
- G1b (placement): the guard is the first statement of the openai branch, reads
  the predicate as a two-name attribute chain on a module alias, raises the stop
  class with the message constant and calls neither the stop helper nor a
  logger. Killed by mutants GM-2 (the guard moved after the client build) and
  GM-3 (the guard routed through the stop helper).

Hermetic: the pinned SDK talks only to file A's transport recorder; every
synthetic value is built at run time. Pure ASCII.
"""

import app.main  # noqa: F401  (first: the dotenv guard, tests/_env_safety)

import ast
import inspect
import os

import pytest

from app.services import api_budget_service as abs_
from app.services import llm_credential_probe as probe
from app.services import llm_router
from app.services import model_config
from tests.test_s81_s12d_openai_egress_stop import (
    SYN_OPENAI,
    _capture,
    _run,
    full_config,
    install_wire,
    new_symbol,
    reset_clients,
    stop_class,
    stop_message,
)


@pytest.fixture(autouse=True)
def _s12d_gate_env(monkeypatch):
    for k in list(os.environ):
        if (
            k.startswith("ENABLE_")
            or k.startswith("ANTHROPIC_")
            or k.startswith("LLM_SPEND_")
            or k.startswith("OPENAI_")
            or k.startswith("LLM_BREAKER_")
        ):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", SYN_OPENAI)
    reset = new_symbol("_reset_openai_egress_stop_state")
    if reset is not None:
        reset()
    if hasattr(llm_router, "_reset_router_state"):
        llm_router._reset_router_state()
    yield
    if reset is not None:
        reset()
    if hasattr(llm_router, "_reset_router_state"):
        llm_router._reset_router_state()


async def _direct_metadata_call():
    """Call _metadata_call('openai') and await what it returns; a raise at the
    call (H5) or at the await is captured by the caller."""
    call = probe._metadata_call("openai")
    if call is None:
        return None
    return await call


@pytest.mark.parametrize("stop", ("true", None), ids=("stop_on", "stop_off_pin_half"))
def test_g1_metadata_call_openai_leg_has_its_own_guard(monkeypatch, stop):
    """G1 (GC-5): stop ON, a direct _metadata_call('openai') raises the stop
    class with the message constant and ZERO requests leave; stop off (PIN
    half), its one models request goes out and the recorder's 401 surfaces."""
    full_config(monkeypatch, stop=stop)
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    st, out = _run(_capture(_direct_metadata_call()))
    if stop is None:
        std = model_config.standard_model()
        assert wire.paths() == ["/v1/models/" + std], wire.paths()
        assert st == "raised" and type(out).__name__ == "AuthenticationError", (st, out)
        return
    assert wire.requests == [], wire.paths()
    assert wire.other == [], wire.other
    cls = new_symbol("OpenAIEgressStoppedError")
    assert isinstance(cls, type), "OpenAIEgressStoppedError missing"
    assert st == "raised" and type(out) is stop_class(), (st, out)
    assert str(out) == stop_message(), str(out)


def _openai_branch():
    src = inspect.getsource(probe._metadata_call)
    fn = ast.parse(src).body[0]
    assert isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)), fn
    for node in fn.body:
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "provider"
            and isinstance(node.test.comparators[0], ast.Constant)
            and node.test.comparators[0].value == "openai"
        ):
            return node
    raise AssertionError("no `if provider == 'openai':` branch in _metadata_call")


def _chain(node):
    out = []
    while True:
        if isinstance(node, ast.Attribute):
            out.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Name):
            out.append(node.id)
            break
        else:
            break
    return list(reversed(out))


def test_g1b_h5_is_the_first_statement_of_the_openai_branch():
    """G1b (GC-5 placement): the openai branch's first statement is
    `if <alias>.openai_egress_stop_enabled(): raise
    <alias>.OpenAIEgressStoppedError(<alias>.OPENAI_EGRESS_STOP_MESSAGE)`, the
    predicate read as a two-name attribute chain (module attribute, never a
    copied name), no stop helper and no logger anywhere in the function, and no
    client is built before it."""
    branch = _openai_branch()
    first = branch.body[0]
    assert isinstance(first, ast.If), ast.dump(first)[:200]
    test = first.test
    assert isinstance(test, ast.Call) and not test.args, ast.dump(test)[:200]
    chain = _chain(test.func)
    assert len(chain) == 2 and chain[1] == "openai_egress_stop_enabled", chain
    assert len(first.body) == 1 and isinstance(first.body[0], ast.Raise), ast.dump(first)[:300]
    exc = first.body[0].exc
    assert isinstance(exc, ast.Call), ast.dump(first.body[0])[:200]
    assert _chain(exc.func)[-1:] == ["OpenAIEgressStoppedError"], _chain(exc.func)
    assert len(exc.args) == 1 and _chain(exc.args[0])[-1:] == ["OPENAI_EGRESS_STOP_MESSAGE"], ast.dump(exc)[:300]
    assert not first.orelse, "the guard has no else arm"
    src = inspect.getsource(probe._metadata_call)
    fn = ast.parse(src).body[0]
    callees = [_chain(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)]
    assert not any(c[-1:] == ["stop_openai_egress_if_enabled"] for c in callees), callees
    assert not any(c and c[0] in ("logger", "logging") for c in callees), callees
    # the alias the predicate is read through is api_budget_service, imported
    # inside the function (llm_credential_probe stays free of module-top imports
    # of provider modules: its own docstring rule)
    alias = chain[0]
    imported = [
        a
        for n in ast.walk(fn)
        if isinstance(n, ast.ImportFrom) and n.module == "app.services"
        for a in n.names
        if a.name == "api_budget_service"
    ]
    assert [((a.asname or a.name)) for a in imported] == [alias], (alias, imported)
    assert getattr(abs_, "openai_egress_stop_enabled", None) is not None
