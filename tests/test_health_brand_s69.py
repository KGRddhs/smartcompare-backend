"""S69 U-R -- brand rename Qaren -> MYEZ: the /health message (T3).

Spec: docs/investigations/2026-09-29-session-69-state/UR_RENAME_MYEZ_SPEC.md
section 3 T3 / R3, as corrected by its spec review (C6, C7, Q3).

* ``GET /health`` must answer ``"MYEZ API is running"`` -- no ``Qaren``, no
  ``SmartCompare``. Hermetic: the real ASGI app through ``TestClient`` (the
  pattern of ``tests/test_health_loop_lag.py``), no network, no lifespan.
* ``scripts/bundle_d_prod_smoke.py`` probe 1 shape-checks the same message.
  At base its helper FAILS unless the message says ``Qaren``, so a deploy of
  the rename would turn the prod smoke red. The helper must accept MYEZ and
  refuse the old brands. It is loaded from its file path (``scripts`` is not a
  package); importing it opens no connection -- ``main()`` only runs under
  ``__main__``.
"""
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

_EXPECTED_MESSAGE = "MYEZ API is running"
_SMOKE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "bundle_d_prod_smoke.py"


def _health_payload() -> dict:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200, (
        f"/health returned {response.status_code}; it is Railway's deploy "
        "healthcheck and must never fail"
    )
    return response.json()


def _load_smoke():
    spec = importlib.util.spec_from_file_location("_s69_bundle_d_prod_smoke", _SMOKE_PATH)
    assert spec is not None and spec.loader is not None, f"cannot load {_SMOKE_PATH}"
    module = importlib.util.module_from_spec(spec)
    # The script defines @dataclass classes, and dataclasses resolves the
    # class's module through sys.modules while the module body runs. Register
    # it under a private name for the exec only, then remove it again so no
    # module identity leaks into other tests.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _health_shape_check(module):
    """The helper probe 1 uses; the rename may give it a MYEZ name."""
    for name in ("_health_body_myez_branded", "_health_body_branded", "_health_body_qaren_branded"):
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    pytest.fail(
        "scripts/bundle_d_prod_smoke.py has no /health brand shape check "
        "(_health_body_myez_branded / _health_body_branded / _health_body_qaren_branded)"
    )


def test_health_message_is_myez():
    payload = _health_payload()
    assert payload.get("status") == "healthy", payload
    assert payload.get("message") == _EXPECTED_MESSAGE, (
        f"/health 'message' must be {_EXPECTED_MESSAGE!r} after the MYEZ rename; "
        f"got {payload.get('message')!r}"
    )


def test_health_message_carries_no_old_brand():
    message = str(_health_payload().get("message", ""))
    assert "MYEZ" in message, f"/health message does not name MYEZ: {message!r}"
    for old in ("Qaren", "SmartCompare"):
        assert old not in message, f"/health message still carries {old!r}: {message!r}"


def test_prod_smoke_health_check_accepts_myez():
    check = _health_shape_check(_load_smoke())
    ok, why = check({"status": "healthy", "message": _EXPECTED_MESSAGE})
    assert ok, (
        "scripts/bundle_d_prod_smoke.py rejects the renamed /health message, so the "
        f"post-deploy smoke would go red: {why}"
    )


def test_prod_smoke_health_check_refuses_old_brands():
    check = _health_shape_check(_load_smoke())
    accepted = [
        old
        for old in ("Qaren API is running", "SmartCompare API is running")
        if check({"status": "healthy", "message": old})[0]
    ]
    assert accepted == [], (
        f"scripts/bundle_d_prod_smoke.py still accepts old /health messages: {accepted!r}"
    )
