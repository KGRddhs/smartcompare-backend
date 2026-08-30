"""M7b — the no-key guard of ``scripts/seed_zyte_luxury.py`` must reflect the
PROCESS ENVIRONMENT AT STARTUP, not a live ``os.getenv``.

THE DEFECT THESE PIN. The script guards its run with
``if not os.getenv("ZYTE_API_KEY")`` (``seed_zyte_luxury.py``), but its OWN
module-top ``load_dotenv(override=False)`` runs first and REFILLS
``ZYTE_API_KEY`` from the repo ``.env`` -- ``override=False`` still SETS a name
that is ABSENT from the process env. So an operator who never exported the key
still triggered live calls to Zyte, a PAID vendor. Reproduced before the fix
with the key popped from the process env at startup: 5 outbound attempts, 2 of
them to ``api.zyte.com``.

Same fix pattern as ``scripts/seed_spec_spine.py`` (commit 991b357): a
module-top ``_STARTUP_ZYTE_KEY`` snapshot captured BEFORE ``load_dotenv`` runs,
with the guard reading the snapshot.

House rule 6: every test here installs a HARD non-loopback socket guard, so
nothing can leave the machine even if the guard regresses -- the outbound
attempt is trapped and COUNTED instead.
"""
from __future__ import annotations

import asyncio
import os
import socket

import pytest

# Environment names ``scripts.seed_zyte_luxury`` writes at IMPORT time. The
# import is a module-level side effect we cannot undo, so we snapshot and
# restore them around every test rather than leak them into the session.
_IMPORT_TIME_ENV = (
    "ENABLE_ZYTE_RENDER", "PRICE_RACE_TIMEOUT", "ZYTE_TIMEOUT", "WARMER_CONTEXT",
)

_LOOPBACK = {
    "127.0.0.1", "::1", "localhost", "0.0.0.0",
    b"127.0.0.1", b"::1", b"localhost",
}


@pytest.fixture(autouse=True)
def _restore_import_time_env():
    saved = {name: os.environ.get(name) for name in _IMPORT_TIME_ENV}
    yield
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@pytest.fixture
def blocked_sockets(monkeypatch):
    """Hard no-outbound-network guard. Returns the list of trapped attempts;
    every non-loopback name resolution / connect RAISES instead of leaving the
    machine."""
    attempts: list = []
    orig_gai = socket.getaddrinfo
    orig_connect = socket.socket.connect
    orig_create = socket.create_connection

    def _boom_gai(host, *a, **k):
        if host not in _LOOPBACK:
            attempts.append(("getaddrinfo", str(host)))
            raise RuntimeError("no-network guard: getaddrinfo(%r)" % (host,))
        return orig_gai(host, *a, **k)

    def _boom_connect(self, address, *a, **k):
        host = address[0] if isinstance(address, (tuple, list)) else address
        if host not in _LOOPBACK:
            attempts.append(("connect", str(host)))
            raise RuntimeError("no-network guard: connect(%r)" % (address,))
        return orig_connect(self, address, *a, **k)

    def _boom_create(address, *a, **k):
        host = address[0] if isinstance(address, (tuple, list)) else address
        if host not in _LOOPBACK:
            attempts.append(("create_connection", str(host)))
            raise RuntimeError("no-network guard: create_connection(%r)" % (address,))
        return orig_create(address, *a, **k)

    monkeypatch.setattr(socket, "getaddrinfo", _boom_gai)
    monkeypatch.setattr(socket.socket, "connect", _boom_connect)
    monkeypatch.setattr(socket, "create_connection", _boom_create)
    return attempts


class TestNoKeyGuard:
    def test_no_key_at_startup_makes_zero_outbound_socket_attempts(
        self, monkeypatch, blocked_sockets, caplog
    ):
        """THE REGRESSION TEST. The key was absent from the process env when the
        operator launched the script, but ``load_dotenv(override=False)`` has
        since refilled ``os.environ`` from the repo .env. The run must still be
        a clean no-op that touches NOTHING outbound.

        Pre-fix (live ``os.getenv`` guard) this records ``api.zyte.com``
        attempts and fails."""
        import scripts.seed_zyte_luxury as seeder

        monkeypatch.setattr(seeder, "_STARTUP_ZYTE_KEY", "")
        # Exactly what the module's own load_dotenv did to the process env.
        monkeypatch.setenv("ZYTE_API_KEY", "refilled-by-load-dotenv")
        monkeypatch.setattr("sys.argv", ["seed_zyte_luxury"])

        with caplog.at_level("WARNING"):
            totals = asyncio.run(seeder.main())

        assert blocked_sockets == [], (
            "the no-key seed attempted an outbound call: %r" % (blocked_sockets,)
        )
        assert totals == {"genuine": 0, "pending": 0}
        assert any("ZYTE_API_KEY not set" in r.getMessage() for r in caplog.records)

    def test_whitespace_only_startup_key_is_treated_as_absent(
        self, monkeypatch, blocked_sockets
    ):
        """A key that is only whitespace is not a key. Same clean no-op."""
        import scripts.seed_zyte_luxury as seeder

        monkeypatch.setattr(seeder, "_STARTUP_ZYTE_KEY", "")
        monkeypatch.setenv("ZYTE_API_KEY", "   ")
        monkeypatch.setattr("sys.argv", ["seed_zyte_luxury"])

        assert asyncio.run(seeder.main()) == {"genuine": 0, "pending": 0}
        assert blocked_sockets == []

    @pytest.mark.parametrize("script", ["seed_zyte_luxury.py", "diag_zyte_match.py"])
    def test_snapshot_is_taken_above_the_module_top_load_dotenv(self, script):
        """The snapshot only tells the truth if it is captured BEFORE the
        module's own ``load_dotenv`` call -- reading it afterwards would record
        the refilled value and reproduce the defect. Pinned on source order
        because that ordering IS the fix. ``diag_zyte_match.py`` carries the
        identical defect (module-top ``load_dotenv(override=False)`` +
        ``os.getenv`` guard) and takes the identical one-line fix; it burns ~16
        paid productList extracts when its guard fails to fire."""
        from pathlib import Path

        src = Path(__file__).resolve().parents[1] / "scripts" / script
        text = src.read_text(encoding="utf-8")
        snap = text.index("_STARTUP_ZYTE_KEY =")
        dotenv = text.index("load_dotenv(override=False)")
        assert snap < dotenv, (
            "%s: _STARTUP_ZYTE_KEY must be snapshotted ABOVE the module-top "
            "load_dotenv() call, or it records the refilled key" % script
        )

    def test_diag_script_no_key_at_startup_makes_zero_outbound_attempts(
        self, monkeypatch, blocked_sockets, capsys
    ):
        """The sibling recon script gets the same guarantee: key absent at
        startup, ``os.environ`` refilled by its own load_dotenv -> abort with
        zero outbound attempts, no Zyte credits burned."""
        import scripts.diag_zyte_match as diag

        monkeypatch.setattr(diag, "_STARTUP_ZYTE_KEY", "")
        monkeypatch.setenv("ZYTE_API_KEY", "refilled-by-load-dotenv")
        monkeypatch.setattr("sys.argv", ["diag_zyte_match"])

        asyncio.run(diag.main())

        assert blocked_sockets == [], (
            "the no-key recon script attempted an outbound call: %r"
            % (blocked_sockets,)
        )
        assert "ZYTE_API_KEY not set" in capsys.readouterr().out


class TestKeyPresentStillSeeds:
    def test_a_key_present_at_startup_still_runs_the_seed(
        self, monkeypatch, blocked_sockets
    ):
        """The other half of the contract -- the guard must not become a
        blanket off switch. With a key exported at startup the run proceeds
        past the guard and reaches the Zyte fetch; the socket guard traps that
        attempt (nothing leaves the machine) and the entry pends honestly."""
        import scripts.seed_zyte_luxury as seeder

        monkeypatch.setattr(seeder, "_STARTUP_ZYTE_KEY", "exported-at-startup")
        monkeypatch.setenv("ZYTE_API_KEY", "exported-at-startup")
        monkeypatch.setenv("ZYTE_RETRIES", "1")
        monkeypatch.setenv("ZYTE_RETRY_BACKOFF", "0")
        # What the script itself sets at import; re-asserted here because the
        # autouse fixture restores the pre-import value between tests.
        monkeypatch.setenv("ENABLE_ZYTE_RENDER", "true")
        # Only the pinned truth-critical PDP entry: one Zyte call, no GPT parse.
        monkeypatch.setattr(
            "sys.argv", ["seed_zyte_luxury", "--only", "luna rossa carbon"]
        )

        totals = asyncio.run(seeder.main())

        assert any("zyte" in host.lower() for _kind, host in blocked_sockets), (
            "a key exported at startup must still reach the Zyte fetch; "
            "trapped attempts were %r" % (blocked_sockets,)
        )
        assert totals == {"genuine": 0, "pending": 1}
