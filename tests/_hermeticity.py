"""Hermeticity sentinel for the test suite (issues #183, #185, #186).

A test that changes process-wide state and does not put it back poisons whichever
test runs after it, and the failure then shows up on the VICTIM, often only in CI's
alphabetical order. This sentinel snapshots a SMALL set of known-fragile state before
each test and compares it after the test's own fixtures (and monkeypatch's undo)
have torn down, so a leak ERRORs the LEAKING test at teardown with
``hermeticity: <test> leaked <item>: <before> -> <after>``.

The four items (only read when the module is already loaded -- nothing is imported):

  1. ``app.services.price_service``: missing from ``sys.modules`` at teardown, or its
     ``sys.modules`` identity changed, or the ``app.services.price_service`` package
     attribute's identity changed (#185: deleting it orphaned every by-name binding);
  2. ``app.services.serper_service.SERPER_API_KEY`` value (#183: a reload left a fake
     key in the module global);
  3. ``app.services.scoring_service._scoring_service`` identity, and the presence /
     identity of an instance-level ``compute_scores`` in ``vars(singleton)`` (#186:
     ``monkeypatch.setattr(<instance>, name, spy)`` undoes by SETTING the bound method
     it read, which then shadows the class attribute -- its ``__func__`` is the
     original, so a ``__func__`` check alone cannot see it). The singleton is built
     lazily, so a singleton that was ``None`` at setup and EXISTS at teardown must
     carry no instance-level ``compute_scores`` either (the leaker created it);
  4. the set of ``sys.modules`` keys under ``app`` -- no deletions.

Contract: ``snapshot(modules=None)`` reads the items from ``modules`` (default
``sys.modules``); ``compare(before, after)`` returns human-readable leak strings (empty
when nothing leaked). Loadable as a pytest plugin: its autouse fixture is registered at
the session root, so it is set up before, and torn down after, every other
function-scoped fixture of the test. The terminal summary prints
``[hermeticity] sentinel checked N test(s)`` -- the proof a run had it armed.
"""
import hashlib
import sys

import pytest

_NOTSET = object()
_PS = "app.services.price_service"
_SERPER = "app.services.serper_service"
_SCORING = "app.services.scoring_service"


def snapshot(modules=None):
    """Strong references to the four sentinel items (so ``id`` reuse cannot hide a
    replacement)."""
    mods = sys.modules if modules is None else modules
    pkg = mods.get("app.services")
    serper = mods.get(_SERPER)
    scoring = mods.get(_SCORING)
    single = getattr(scoring, "_scoring_service", None) if scoring is not None else None
    shadow = _NOTSET
    if single is not None:
        try:
            shadow = vars(single).get("compute_scores", _NOTSET)
        except TypeError:  # no instance __dict__
            shadow = _NOTSET
    return {
        "price_service_module": mods.get(_PS, _NOTSET),
        "price_service_pkgattr": getattr(pkg, "price_service", _NOTSET) if pkg is not None else _NOTSET,
        "serper_key": getattr(serper, "SERPER_API_KEY", _NOTSET) if serper is not None else _NOTSET,
        "scoring_singleton": single,
        "scoring_shadow": shadow,
        "app_keys": frozenset(k for k in list(mods) if k == "app" or k.startswith("app.")),
    }


def _obj(value):
    if value is _NOTSET:
        return "<unset>"
    return "%s@%x" % (type(value).__name__, id(value))


def _value(value):
    """A key's value, never printed in clear: ``None`` / ``<unset>`` or a length and a
    short digest (the sentinel may run under LIVE=1 with real credentials)."""
    if value is _NOTSET:
        return "<unset>"
    if isinstance(value, str):
        return "<str len=%d sha256:%s>" % (
            len(value), hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:8])
    return repr(value) if value is None else "<%s>" % type(value).__name__


def compare(before, after):
    """Leak strings for every sentinel item that changed between two snapshots."""
    leaks = []
    b_mod, a_mod = before["price_service_module"], after["price_service_module"]
    if b_mod is not _NOTSET:
        if a_mod is _NOTSET:
            leaks.append("sys.modules[%r] removed: %s -> <unset>" % (_PS, _obj(b_mod)))
        elif a_mod is not b_mod:
            leaks.append("sys.modules[%r] replaced: %s -> %s" % (_PS, _obj(b_mod), _obj(a_mod)))
    b_attr, a_attr = before["price_service_pkgattr"], after["price_service_pkgattr"]
    if b_attr is not _NOTSET and a_attr is not b_attr:
        leaks.append("app.services.price_service package attribute replaced: %s -> %s"
                     % (_obj(b_attr), _obj(a_attr)))
    b_key, a_key = before["serper_key"], after["serper_key"]
    if b_key is not _NOTSET and a_key is not _NOTSET and a_key != b_key:
        leaks.append("serper_service.SERPER_API_KEY changed: %s -> %s" % (_value(b_key), _value(a_key)))
    b_single, a_single = before["scoring_singleton"], after["scoring_singleton"]
    if b_single is not None:
        if a_single is not b_single:
            leaks.append("scoring_service._scoring_service replaced: %s -> %s"
                         % (_obj(b_single), _obj(a_single)))
        elif after["scoring_shadow"] is not before["scoring_shadow"]:
            leaks.append("vars(scoring_service._scoring_service)['compute_scores'] changed: %s -> %s"
                         % (_obj(before["scoring_shadow"]), _obj(after["scoring_shadow"])))
    elif a_single is not None and after["scoring_shadow"] is not _NOTSET:
        # The lazy singleton was CREATED during this test and already carries an
        # instance-level compute_scores: the #186 shadow at its source. Without this
        # branch every later test would snapshot the shadow as its baseline.
        leaks.append("vars(scoring_service._scoring_service)['compute_scores'] set on a singleton "
                     "created during the test: <unset> -> %s" % _obj(after["scoring_shadow"]))
    gone = sorted(before["app_keys"] - after["app_keys"])
    if gone:
        leaks.append("app modules removed from sys.modules: %s -> <unset>" % ", ".join(gone[:10]))
    return leaks


_CHECKED = {"tests": 0}


@pytest.fixture(autouse=True)
def _hermeticity_sentinel(request):
    """Fail the LEAKING test at teardown (an ERROR on it, never on a later victim)."""
    _CHECKED["tests"] += 1
    before = snapshot()
    yield
    leaks = compare(before, snapshot())
    if leaks:
        pytest.fail("hermeticity: %s leaked %s" % (request.node.nodeid, "; ".join(leaks)),
                    pytrace=False)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # Proof the sentinel was ARMED in this run: a run where nothing leaked and a run
    # where the sentinel never loaded both print no "hermeticity:" error, so the pins
    # over real files assert this line instead of only the absence of an error.
    terminalreporter.write_line("[hermeticity] sentinel checked %d test(s)" % _CHECKED["tests"])
