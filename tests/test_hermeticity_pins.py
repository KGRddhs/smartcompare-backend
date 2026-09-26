"""TEST-HERMETICITY pins -- issues #183, #184 (netguard 04c, curl_cffi), #185, #186.

Spec: .qa-s68/HERMETICITY_SPEC.md section F as amended by the Fable red-gate rulings
(RULINGS_HERMETICITY.md R1-R21). Written RED at 61585c58: every pin first asserts the
unit's modules (``tests._netguard``, ``tests._hermeticity``, ``scripts.netguard_ratchet``)
exist, so at base every node failed with "HERMETICITY RED: <module> does not exist yet".

Contract (names these pins rely on):

* ``tests._netguard``: ``NetworkBlocked`` (an ``OSError`` subclass) raised for every
  non-loopback attempt through ``socket.getaddrinfo`` (a NAME -- an IP literal needs no
  DNS and is allowed, R6) / ``socket.socket.connect`` / ``connect_ex`` /
  ``socket.create_connection`` and the four curl_cffi points
  (``curl_cffi.requests.Session.request``, ``AsyncSession.request``,
  ``curl_cffi.Curl.perform``, ``curl_cffi.AsyncCurl.add_handle``); each attempt is
  recorded as ``(nodeid, kind, target, class)`` (``blocked_records()``) and the real
  functions sit in ``_REAL``; installed by ``tests/conftest.py``; loopback allowed
  (socketpair, 127.0.0.1 listen+connect, a loopback ``Session.request`` reaching
  ``perform``, a loopback ``stream=True`` request whose ``perform`` runs on an executor
  thread -- R10(6)); marker ``allow_network`` lifts it for one test;
  ``QAREN_NETGUARD_REPORT`` writes ``{"blocked": n, "nodes": {nodeid: [targets...]},
  "classes": {nodeid: [classes]}}``; under ``LIVE=1`` the guard is not installed and
  the terminal summary says so.
* ``scripts/netguard_ratchet.py <report.json> <baseline>``: exit 0 on a subset (prints
  the shrink) or when every new node is sentinel/ip-literal only (WARNING, R7), 1 on a
  new node id attempting ``egress`` (prints it), 2 on a missing report; ``--write``
  regenerates the baseline as sorted ``<nodeid> <classes>`` lines; the
  ``<collection>`` pseudo-node never fails it.
* ``tests._hermeticity``: ``snapshot(modules=None)`` / ``compare(before, after)`` ->
  leak strings (item 3 also flags an instance-level ``compute_scores`` on a lazy
  scoring singleton CREATED during the test, R15); the conftest-armed autouse
  sentinel fails a leaking test at TEARDOWN with ``hermeticity: <test> leaked ...``;
  loadable as a pytest plugin.

Network: none, even with the guard broken. A public NAME is only ever looked up with
``AI_NUMERICHOST`` (the real resolver refuses a non-numeric host locally, so a broken
guard shows up as ``gaierror``, never a DNS query); the TEST-NET-1 literal
``192.0.2.1`` is only ever a connect / curl target the guard must refuse.

Subprocess pins over REAL test files are capped at four (R9): #183 hotfix -> w49, #185
platform_router -> l13 -> w49, #186 in both orders. Everything else is in-process;
the sentinel armed in conftest is the permanent pin over the fixed files -- and that
arming is itself pinned: ``test_conftest_arms_the_hermeticity_sentinel`` in-process,
and every CI-order run asserts the ``[hermeticity] sentinel checked N test(s)``
summary line, so "no hermeticity: error" can never be the silence of an unarmed run.
"""
import ast
import asyncio
import importlib
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import textwrap
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from tests._env_safety import live_mode_enabled

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_IP = "192.0.2.1"  # RFC 5737 TEST-NET-1: never routed; a connect/curl target only
PUBLIC_URL = "https://192.0.2.1/"
PUBLIC_NAME = "example.com"  # only ever looked up with AI_NUMERICHOST (no DNS query)
_RED = "HERMETICITY RED: %s does not exist yet"


# ---------------------------------------------------------------------------
# presence helpers -- the FIRST thing every pin does
# ---------------------------------------------------------------------------
def _require(modname):
    spec = importlib.util.find_spec(modname)
    assert spec is not None, _RED % modname
    return importlib.import_module(modname)


def _netguard():
    ng = _require("tests._netguard")
    if live_mode_enabled():
        pytest.skip("LIVE=1 leaves the netguard uninstalled by design")
    assert ng._STATE["installed"], "tests/conftest.py did not install the netguard"
    return ng


def _hermeticity():
    return _require("tests._hermeticity")


def _ratchet_script():
    _require("scripts.netguard_ratchet")
    path = REPO_ROOT / "scripts" / "netguard_ratchet.py"
    assert path.is_file(), _RED % "scripts/netguard_ratchet.py"
    return path


def _last_kind(ng):
    records = ng.blocked_records()
    assert records, "the guard recorded nothing"
    return records[-1][1]


def _subprocess_env(**extra):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO_ROOT), env.get("PYTHONPATH", "")) if p
    )
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("QAREN_NETGUARD_REPORT", None)
    env.pop("LIVE", None)
    env.update(extra)
    return env


def _run_pytest(args, cwd, **env_extra):
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-p", "no:randomly", *args],
        cwd=str(cwd), env=_subprocess_env(**env_extra), capture_output=True,
        encoding="utf-8", errors="replace", timeout=600,
    )


# ===========================================================================
# A. the guard (#184)
# ===========================================================================
def test_guard_blocks_getaddrinfo_for_a_public_host():
    ng = _netguard()
    with pytest.raises(ng.NetworkBlocked):
        socket.getaddrinfo(PUBLIC_NAME, 443, flags=socket.AI_NUMERICHOST)
    assert _last_kind(ng) == "socket.getaddrinfo"


def test_guard_decodes_a_bytes_host_in_the_record():
    ng = _netguard()
    with pytest.raises(ng.NetworkBlocked):
        socket.getaddrinfo(PUBLIC_NAME.encode(), 443, flags=socket.AI_NUMERICHOST)
    _node, kind, target, cls = ng.blocked_records()[-1]
    assert (kind, target, cls) == ("socket.getaddrinfo", "example.com:443", "egress")


def test_guard_still_records_when_a_test_patches_ipaddress(monkeypatch):
    """Measured in the green full tier: test_security_hardening's
    test_exception_during_validation_blocked patches ipaddress.ip_address to raise; the
    guard's own host classifier must not depend on that global."""
    ng = _netguard()
    import ipaddress

    def _boom(*a, **k):
        raise RuntimeError("patched by a test")

    monkeypatch.setattr(ipaddress, "ip_address", _boom)
    with pytest.raises(ng.NetworkBlocked):
        socket.getaddrinfo(PUBLIC_NAME, 443, flags=socket.AI_NUMERICHOST)
    assert _last_kind(ng) == "socket.getaddrinfo"


def test_guard_allows_getaddrinfo_for_ip_literals_but_not_a_connect():
    """R6: a literal needs no DNS, so its lookup is allowed; connecting is not."""
    ng = _netguard()
    assert socket.getaddrinfo("10.0.0.1", 80)
    assert socket.getaddrinfo(PUBLIC_IP, 443)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(ng.NetworkBlocked):
            s.connect((PUBLIC_IP, 443))
    finally:
        s.close()
    with pytest.raises(ng.NetworkBlocked):
        socket.getaddrinfo(PUBLIC_NAME, 443, flags=socket.AI_NUMERICHOST)


def test_guard_blocks_socket_connect_to_a_public_address():
    ng = _netguard()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(ng.NetworkBlocked):
            s.connect((PUBLIC_IP, 443))
    finally:
        s.close()
    assert _last_kind(ng) == "socket.connect"


def test_guard_blocks_socket_connect_ex_to_a_public_address():
    ng = _netguard()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(ng.NetworkBlocked):
            s.connect_ex((PUBLIC_IP, 443))
    finally:
        s.close()
    assert _last_kind(ng) == "socket.connect_ex"


def test_guard_blocks_create_connection_to_a_public_address():
    ng = _netguard()
    with pytest.raises(ng.NetworkBlocked):
        socket.create_connection((PUBLIC_IP, 443), timeout=1)
    assert _last_kind(ng) == "socket.create_connection"


def test_network_blocked_is_an_oserror():
    ng = _netguard()
    assert issubclass(ng.NetworkBlocked, OSError)


def test_guard_blocks_curl_cffi_session_request():
    ng = _netguard()
    from curl_cffi import requests as curl_requests

    with curl_requests.Session() as s, pytest.raises(ng.NetworkBlocked):
        s.request("GET", PUBLIC_URL, timeout=2)
    assert _last_kind(ng) == "curl_cffi.Session.request"


def test_guard_blocks_curl_cffi_requests_get_helper():
    ng = _netguard()
    from curl_cffi import requests as curl_requests

    with pytest.raises(ng.NetworkBlocked):
        curl_requests.get(PUBLIC_URL, timeout=2)
    assert _last_kind(ng) == "curl_cffi.Session.request"


def test_guard_blocks_curl_cffi_async_session_request():
    ng = _netguard()
    from curl_cffi import requests as curl_requests

    async def _go():
        async with curl_requests.AsyncSession() as s:
            await s.request("GET", PUBLIC_URL, timeout=2)

    with pytest.raises(ng.NetworkBlocked):
        asyncio.run(_go())
    assert _last_kind(ng) == "curl_cffi.AsyncSession.request"


def test_guard_blocks_a_public_streamed_curl_request():
    ng = _netguard()
    from curl_cffi import requests as curl_requests

    with curl_requests.Session() as s, pytest.raises(ng.NetworkBlocked):
        s.request("GET", PUBLIC_URL, stream=True, timeout=2)


def test_guard_blocks_a_bare_curl_perform():
    ng = _netguard()
    from curl_cffi import Curl, CurlOpt

    c = Curl()
    try:
        c.setopt(CurlOpt.URL, PUBLIC_URL.encode())
        with pytest.raises(ng.NetworkBlocked):
            c.perform()
    finally:
        c.close()
    assert _last_kind(ng) == "curl_cffi.Curl.perform"


def test_guard_blocks_a_bare_async_curl_add_handle():
    ng = _netguard()
    from curl_cffi import AsyncCurl, Curl, CurlOpt

    async def _go():
        acurl = AsyncCurl(loop=asyncio.get_running_loop())
        c = Curl()
        try:
            c.setopt(CurlOpt.URL, PUBLIC_URL.encode())
            with pytest.raises(ng.NetworkBlocked):
                acurl.add_handle(c)
        finally:
            c.close()
            await acurl.close()

    asyncio.run(_go())
    assert _last_kind(ng) == "curl_cffi.AsyncCurl.add_handle"


@pytest.mark.allow_network
def test_allow_network_marker_lifts_a_bare_async_curl_add_handle(monkeypatch):
    """The marker lift reaches the add_handle point too (the ContextVar is unset for a
    bare AsyncCurl). The real add_handle is stubbed, so no transfer ever starts."""
    ng = _netguard()
    from curl_cffi import AsyncCurl, Curl, CurlOpt

    added = []
    monkeypatch.setitem(ng._REAL, "add_handle", lambda self, curl: added.append(curl))

    async def _go():
        acurl = AsyncCurl(loop=asyncio.get_running_loop())
        c = Curl()
        try:
            c.setopt(CurlOpt.URL, PUBLIC_URL.encode())
            try:
                acurl.add_handle(c)
            except ng.NetworkBlocked as exc:  # the RED case
                pytest.fail("allow_network did not lift the add_handle guard: %s" % exc)
            assert added == [c]
        finally:
            c.close()
            await acurl.close()

    asyncio.run(_go())


def test_guard_allows_socketpair():
    _netguard()
    a, b = socket.socketpair()
    try:
        a.sendall(b"x")
        assert b.recv(1) == b"x"
    finally:
        a.close()
        b.close()


def test_guard_allows_a_loopback_listen_and_connect():
    _netguard()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        cli = socket.create_connection(srv.getsockname(), timeout=5)
        conn, _ = srv.accept()
        try:
            cli.sendall(b"ok")
            assert conn.recv(2) == b"ok"
        finally:
            conn.close()
            cli.close()
    finally:
        srv.close()


class _Hello(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 -- http.server API
        body = b"loopback-ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # silence
        pass


@pytest.fixture()
def loopback_http_server():
    srv = HTTPServer(("127.0.0.1", 0), _Hello)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield "http://127.0.0.1:%d/" % srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()


def test_guard_allows_a_loopback_curl_session_request_through_perform(loopback_http_server):
    _netguard()
    from curl_cffi import requests as curl_requests

    with curl_requests.Session() as s:
        r = s.request("GET", loopback_http_server, timeout=10)
    assert r.status_code == 200
    assert r.content == b"loopback-ok"


def test_guard_allows_a_loopback_curl_async_session_request(loopback_http_server):
    _netguard()
    from curl_cffi import requests as curl_requests

    async def _go():
        async with curl_requests.AsyncSession() as s:
            return await s.request("GET", loopback_http_server, timeout=10)

    r = asyncio.run(_go())
    assert r.status_code == 200


def test_guard_allows_a_loopback_streamed_curl_request(loopback_http_server):
    """R10(6): stream=True performs on an executor thread the loopback ContextVar does
    not reach; the handle's own loopback URL (curl EFFECTIVE_URL) lets it through."""
    _netguard()
    from curl_cffi import requests as curl_requests

    with curl_requests.Session() as s:
        r = s.request("GET", loopback_http_server, stream=True, timeout=10)
        try:
            body = b"".join(r.iter_content())
        finally:
            r.close()
    assert r.status_code == 200
    assert body == b"loopback-ok"


def test_guard_blocks_a_name_that_only_starts_with_127():
    """127.0.0.1.nip.io is a NAME (real DNS, a common SSRF/rebinding fixture), not a
    loopback address; only numeric 127.x forms are loopback."""
    ng = _netguard()
    with pytest.raises(ng.NetworkBlocked):
        socket.getaddrinfo("127.0.0.1.nip.io", 443, flags=socket.AI_NUMERICHOST)
    _node, kind, target, cls = ng.blocked_records()[-1]
    assert (kind, target, cls) == ("socket.getaddrinfo", "127.0.0.1.nip.io:443", "egress")
    assert not ng._is_loopback("127.evil-example.com")
    assert ng._is_loopback("127.0.0.1") and ng._is_loopback("127.1")


@pytest.mark.parametrize("host,cls", [
    ("x.supabase.invalid", "sentinel"),
    (b"x.supabase.invalid", "sentinel"),
    ("neutralized.example", "sentinel"),     # the neutralized.* rule on its own (R7)
    ("NEUTRALIZED.Example", "sentinel"),
    ("10.0.0.1", "ip_literal"),
    ("[fd00::1]", "ip_literal"),
    ("example.com", "egress"),
    ("api.openai.com", "egress"),
    ("127.0.0.1.nip.io", "egress"),
])
def test_report_classifies_every_host(host, cls):
    ng = _netguard()
    assert ng.classify_host(host) == cls


def _loop_params():
    proactor = getattr(asyncio, "ProactorEventLoop", None)
    return [
        pytest.param(asyncio.SelectorEventLoop, id="selector"),
        pytest.param(proactor, id="proactor",
                     marks=pytest.mark.skipif(proactor is None, reason="Windows-only loop")),
    ]


@pytest.mark.parametrize("loop_factory", _loop_params())
def test_guard_blocks_an_asyncio_connect_to_a_public_literal(loop_factory):
    """Windows' default proactor loop connects through ConnectEx, never through
    socket.socket.connect; CI's selector loop does. Both must be refused."""
    ng = _netguard()
    loop = loop_factory()
    try:
        with pytest.raises(ng.NetworkBlocked):
            loop.run_until_complete(asyncio.wait_for(asyncio.open_connection(PUBLIC_IP, 443), 3))
    finally:
        loop.close()
    _node, kind, target, cls = ng.blocked_records()[-1]
    assert (kind, target, cls) == ("socket.connect", "%s:443" % PUBLIC_IP, "ip_literal")


@pytest.mark.parametrize("loop_factory", _loop_params())
def test_guard_allows_an_asyncio_loopback_connect(loop_factory):
    _netguard()

    async def _go():
        async def _handle(reader, writer):
            writer.write(b"ok")
            await writer.drain()
            writer.close()

        srv = await asyncio.start_server(_handle, "127.0.0.1", 0)
        try:
            reader, writer = await asyncio.open_connection(
                "127.0.0.1", srv.sockets[0].getsockname()[1])
            data = await reader.read(2)
            writer.close()
            return data
        finally:
            srv.close()

    loop = loop_factory()
    try:
        assert loop.run_until_complete(asyncio.wait_for(_go(), 10)) == b"ok"
    finally:
        loop.close()


_PUBLIC_PROXY = "http://%s:8080" % PUBLIC_IP


@pytest.mark.parametrize("how", ["call_proxy", "call_proxies", "session_proxies", "async_call_proxy"])
def test_guard_blocks_a_loopback_curl_url_through_a_public_proxy(how, loopback_http_server):
    """libcurl connects to the PROXY, not to the loopback host in the URL."""
    ng = _netguard()
    from curl_cffi import requests as curl_requests

    url = loopback_http_server
    with pytest.raises(ng.NetworkBlocked):
        if how == "call_proxy":
            with curl_requests.Session() as s:
                s.request("GET", url, proxy=_PUBLIC_PROXY, timeout=2)
        elif how == "call_proxies":
            with curl_requests.Session() as s:
                s.request("GET", url, proxies={"all": _PUBLIC_PROXY}, timeout=2)
        elif how == "session_proxies":
            with curl_requests.Session(proxies={"http": _PUBLIC_PROXY}) as s:
                s.request("GET", url, timeout=2)
        else:
            async def _go():
                async with curl_requests.AsyncSession() as s:
                    await s.request("GET", url, proxy=_PUBLIC_PROXY, timeout=2)

            asyncio.run(_go())
    _node, kind, target, cls = ng.blocked_records()[-1]
    assert kind in ("curl_cffi.Session.request", "curl_cffi.AsyncSession.request"), kind
    assert cls == "ip_literal" and target.startswith(_PUBLIC_PROXY), target


def test_guard_allows_a_loopback_curl_url_through_a_loopback_proxy(loopback_http_server):
    _netguard()
    from curl_cffi import requests as curl_requests

    with curl_requests.Session() as s:
        r = s.request("GET", loopback_http_server,
                      proxy=loopback_http_server.rstrip("/"), timeout=10)
    assert r.status_code == 200
    assert r.content == b"loopback-ok"


def _stub_real_getaddrinfo(ng, monkeypatch):
    calls = []

    def _fake(host, port, *a, **k):
        calls.append(host)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 0))]

    monkeypatch.setitem(ng._REAL, "getaddrinfo", _fake)
    return calls


def test_non_loopback_lookup_is_blocked_without_the_marker(monkeypatch):
    ng = _netguard()
    calls = _stub_real_getaddrinfo(ng, monkeypatch)
    with pytest.raises(ng.NetworkBlocked):
        socket.getaddrinfo(PUBLIC_NAME, 80, flags=socket.AI_NUMERICHOST)
    assert calls == []


@pytest.mark.allow_network
def test_allow_network_marker_lifts_the_guard_for_this_test(monkeypatch):
    """The lifted call reaches the (stubbed) real resolver: no NetworkBlocked, and no
    DNS query either -- the stub answers."""
    ng = _netguard()
    calls = _stub_real_getaddrinfo(ng, monkeypatch)
    try:
        socket.getaddrinfo(PUBLIC_NAME, 80, flags=socket.AI_NUMERICHOST)
    except ng.NetworkBlocked as exc:  # pragma: no cover -- the RED case
        pytest.fail("allow_network did not lift the guard: %s" % exc)
    except OSError:
        pass  # a broken guard falls through to the real resolver, which refuses a name
    assert calls == [PUBLIC_NAME]


def test_allow_network_marker_is_registered():
    _netguard()
    import tomllib

    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers = data["tool"]["pytest"]["ini_options"]["markers"]
    assert any(m.split(":", 1)[0].strip() == "allow_network" for m in markers), markers


_TINY_CONFTEST = textwrap.dedent(
    """
    import tests._netguard as _ng  # noqa: F401  -- the port must install on import/configure
    pytest_plugins = ["tests._netguard"]
    """
)

_TINY_TEST = textwrap.dedent(
    """
    import socket


    def test_one_lookup():
        try:
            socket.getaddrinfo("example.com", 443, flags=socket.AI_NUMERICHOST)
        except OSError:
            pass


    def test_quiet():
        assert True
    """
)


def test_report_file_has_the_expected_shape(tmp_path):
    _netguard()
    (tmp_path / "conftest.py").write_text(_TINY_CONFTEST, encoding="utf-8")
    (tmp_path / "test_tiny.py").write_text(_TINY_TEST, encoding="utf-8")
    report = tmp_path / "report.json"
    res = _run_pytest(["-q", "test_tiny.py"], tmp_path, QAREN_NETGUARD_REPORT=str(report))
    assert res.returncode == 0, res.stdout + res.stderr
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["blocked"] == 1, data
    assert list(data["nodes"]) == ["test_tiny.py::test_one_lookup"], data
    assert data["nodes"]["test_tiny.py::test_one_lookup"] == [
        "socket.getaddrinfo example.com:443"], data
    assert data["classes"] == {"test_tiny.py::test_one_lookup": ["egress"]}, data
    assert "[netguard] blocked 1 attempt(s) from 1 node(s)" in res.stdout, res.stdout


_SESSIONFINISH_CONFTEST = _TINY_CONFTEST + textwrap.dedent(
    """
    import socket


    def pytest_sessionfinish(session, exitstatus):
        # an attempt AFTER the last test's runtest protocol has ended
        try:
            socket.getaddrinfo("after-the-last-test.example.com", 443, flags=socket.AI_NUMERICHOST)
        except OSError:
            pass
    """
)


def test_an_attempt_after_the_last_test_is_charged_to_collection(tmp_path):
    """R16: pytest_runtest_protocol's finally resets the current node, so an attempt
    from a session-finish hook is reported under <collection> (which never fails the
    ratchet), never under the last test that ran."""
    _netguard()
    (tmp_path / "conftest.py").write_text(_SESSIONFINISH_CONFTEST, encoding="utf-8")
    (tmp_path / "test_tiny.py").write_text("def test_last():\n    assert True\n", encoding="utf-8")
    report = tmp_path / "report.json"
    res = _run_pytest(["-q", "test_tiny.py"], tmp_path, QAREN_NETGUARD_REPORT=str(report))
    assert res.returncode == 0, res.stdout + res.stderr
    data = json.loads(report.read_text(encoding="utf-8"))
    assert list(data["nodes"]) == ["<collection>"], data
    assert data["nodes"]["<collection>"] == [
        "socket.getaddrinfo after-the-last-test.example.com:443"], data
    assert "[netguard] blocked 1 attempt(s) from 0 node(s)" in res.stdout, res.stdout


_LIFTED_LAST_CONFTEST = _TINY_CONFTEST + textwrap.dedent(
    """
    import pathlib
    import socket


    def pytest_sessionfinish(session, exitstatus):
        # an attempt AFTER an allow_network LAST test; the exception type is written
        # to a file because the terminal capture state is not reliable this late
        try:
            socket.getaddrinfo("after-the-last-test.example.com", 443, flags=socket.AI_NUMERICHOST)
            outcome = "no exception"
        except OSError as exc:
            outcome = type(exc).__name__
        pathlib.Path("sessionfinish_outcome.txt").write_text(outcome, encoding="utf-8")
    """
)

_LIFTED_LAST_TEST = textwrap.dedent(
    """
    import pytest


    def test_first():
        assert True


    @pytest.mark.allow_network
    def test_last_is_lifted():
        assert True
    """
)


def test_an_attempt_after_a_lifted_last_test_is_still_blocked(tmp_path):
    """R18: pytest_runtest_protocol's finally also resets ``lifted``. After the LAST test
    no later protocol sets it again, so without that reset an attempt from a session-finish
    hook after an ``allow_network`` last test would go through UNBLOCKED and unrecorded.
    It must be blocked (NetworkBlocked) and charged to <collection>, never to that test.
    (AI_NUMERICHOST: even with the reset dropped the real resolver refuses the name
    locally with gaierror, so this pin makes no DNS query.)"""
    _netguard()
    (tmp_path / "conftest.py").write_text(_LIFTED_LAST_CONFTEST, encoding="utf-8")
    (tmp_path / "test_tiny.py").write_text(_LIFTED_LAST_TEST, encoding="utf-8")
    report = tmp_path / "report.json"
    res = _run_pytest(["-q", "test_tiny.py"], tmp_path, QAREN_NETGUARD_REPORT=str(report))
    assert res.returncode == 0, res.stdout + res.stderr
    assert "2 passed" in res.stdout, res.stdout
    outcome = (tmp_path / "sessionfinish_outcome.txt").read_text(encoding="utf-8")
    assert outcome == "NetworkBlocked", outcome
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["blocked"] == 1, data
    assert list(data["nodes"]) == ["<collection>"], data
    assert data["nodes"]["<collection>"] == [
        "socket.getaddrinfo after-the-last-test.example.com:443"], data
    assert "[netguard] blocked 1 attempt(s) from 0 node(s)" in res.stdout, res.stdout


def test_live_opt_in_leaves_the_guard_uninstalled(tmp_path):
    _netguard()
    (tmp_path / "conftest.py").write_text(_TINY_CONFTEST, encoding="utf-8")
    (tmp_path / "test_tiny.py").write_text(
        "import socket\n\n\ndef test_real_socket_module():\n"
        "    assert socket.getaddrinfo.__module__ == 'socket'\n",
        encoding="utf-8",
    )
    res = _run_pytest(["-q", "test_tiny.py"], tmp_path, LIVE="1")
    assert res.returncode == 0, res.stdout + res.stderr
    low = res.stdout.lower()
    assert "[netguard]" in low and "not installed" in low, res.stdout


def test_conftest_installs_the_guard_once():
    """A second install() (double import of the port) must not double-patch. This pins
    idempotence only; WHEN conftest installs is pinned by the next test."""
    ng = _netguard()
    before = (socket.getaddrinfo, socket.socket.connect, socket.create_connection)
    ng.install()
    assert (socket.getaddrinfo, socket.socket.connect, socket.create_connection) == before


def _is_call_to(node, owner, attr):
    return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == attr
            and isinstance(node.value.func.value, ast.Name) and node.value.func.value.id == owner)


def test_conftest_installs_the_guard_at_import_before_any_app_import():
    """Invariant 3: the guard is installed at conftest IMPORT time, after the credential
    neutralisation and before any module-level ``app`` import. The plugin's
    pytest_configure also installs it, so a runtime check cannot see a removed
    import-time call; this reads conftest's module-level statements in order."""
    _netguard()
    tree = ast.parse((REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"))
    neutralised = install = None
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
                and getattr(node.value.func, "id", None) == "neutralize_credentials":
            neutralised = i
        if _is_call_to(node, "_netguard", "install"):
            install = i
            break
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            assert not any(n == "app" or n.startswith("app.") for n in names), (
                "conftest imports %s before _netguard.install()" % names)
    assert install is not None, "tests/conftest.py no longer calls _netguard.install() at import"
    assert neutralised is not None and neutralised < install, (
        "the credential neutralisation must run before the guard is installed")


def test_conftest_arms_the_hermeticity_sentinel(request):
    """The sentinel is registered from tests/conftest.py and wraps THIS test; without
    it every "no hermeticity: error" assertion below would be vacuous."""
    _hermeticity()
    assert request.config.pluginmanager.get_plugin("tests._hermeticity") is not None, (
        "tests/conftest.py no longer registers tests._hermeticity")
    assert "_hermeticity_sentinel" in request.fixturenames


_LIFT_TESTS = textwrap.dedent(
    """
    import socket

    import pytest


    def _lookup():
        # AI_NUMERICHOST: an unguarded resolver refuses the name locally (gaierror),
        # so a lifted test never makes a DNS query; only NetworkBlocked propagates.
        try:
            socket.getaddrinfo("example.com", 443, flags=socket.AI_NUMERICHOST)
        except OSError as exc:
            if type(exc).__name__ == "NetworkBlocked":
                raise


    @pytest.mark.allow_network
    def test_allow_network():
        _lookup()


    @pytest.mark.live_unit
    def test_live_unit():
        _lookup()


    @pytest.mark.live_db
    def test_live_db():
        _lookup()


    @pytest.mark.integration
    def test_integration():
        _lookup()


    @pytest.mark.bench
    def test_bench():
        _lookup()


    @pytest.mark.live_prod
    def test_live_prod():
        _lookup()


    def test_unmarked_control():
        try:
            socket.getaddrinfo("example.com", 443, flags=socket.AI_NUMERICHOST)
        except OSError:
            pass
    """
)


def test_every_lift_marker_lifts_the_guard(tmp_path):
    """R8: allow_network AND the live-tier markers (live_unit, live_db, integration,
    bench, live_prod) each lift the guard for that one test; the unmarked control is
    still blocked and is the only node in the report."""
    _netguard()
    (tmp_path / "conftest.py").write_text(_TINY_CONFTEST, encoding="utf-8")
    (tmp_path / "test_lift.py").write_text(_LIFT_TESTS, encoding="utf-8")
    report = tmp_path / "report.json"
    res = _run_pytest(["-q", "-rfE", "test_lift.py"], tmp_path, QAREN_NETGUARD_REPORT=str(report))
    assert res.returncode == 0, res.stdout + res.stderr
    assert "7 passed" in res.stdout, res.stdout
    data = json.loads(report.read_text(encoding="utf-8"))
    assert list(data["nodes"]) == ["test_lift.py::test_unmarked_control"], data


# ===========================================================================
# ratchet
# ===========================================================================
def _write_report(path, nodes, classes=None):
    data = {"blocked": sum(len(v) for v in nodes.values()), "nodes": nodes}
    if classes is not None:
        data["classes"] = classes
    path.write_text(json.dumps(data), encoding="utf-8")


def _ratchet(*args):
    script = _ratchet_script()
    return subprocess.run([sys.executable, str(script), *map(str, args)], cwd=str(REPO_ROOT),
                          env=_subprocess_env(), capture_output=True, encoding="utf-8",
                          errors="replace", timeout=120)


def _baseline(path, ids):
    path.write_text("# generated\n" + "".join(i + "\n" for i in sorted(ids)), encoding="utf-8")


def _baseline_ids(path):
    return [ln.strip().rsplit(" ", 1)[0] for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def test_ratchet_same_set_exits_0(tmp_path):
    _ratchet_script()
    rep, base = tmp_path / "r.json", tmp_path / "b.txt"
    _write_report(rep, {"tests/test_a.py::t1": ["x"], "tests/test_b.py::t2": ["y"]})
    _baseline(base, ["tests/test_a.py::t1", "tests/test_b.py::t2"])
    res = _ratchet(rep, base)
    assert res.returncode == 0, res.stdout + res.stderr


def test_ratchet_fewer_exits_0_and_prints_the_shrink(tmp_path):
    _ratchet_script()
    rep, base = tmp_path / "r.json", tmp_path / "b.txt"
    _write_report(rep, {"tests/test_a.py::t1": ["x"]})
    _baseline(base, ["tests/test_a.py::t1", "tests/test_b.py::t2"])
    res = _ratchet(rep, base)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "tests/test_b.py::t2" in res.stdout, res.stdout


def test_ratchet_new_id_exits_1_and_prints_it(tmp_path):
    _ratchet_script()
    rep, base = tmp_path / "r.json", tmp_path / "b.txt"
    _write_report(rep, {"tests/test_a.py::t1": ["x"], "tests/test_new.py::t9": ["z"]})
    _baseline(base, ["tests/test_a.py::t1"])
    res = _ratchet(rep, base)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "tests/test_new.py::t9" in res.stdout + res.stderr


def test_ratchet_new_sentinel_only_node_warns_and_exits_0(tmp_path):
    """R7: a new node whose attempts are all credential placeholders is a WARNING."""
    _ratchet_script()
    rep, base = tmp_path / "r.json", tmp_path / "b.txt"
    _write_report(rep, {"tests/test_new.py::t9": ["socket.getaddrinfo x.supabase.invalid:443"]},
                  classes={"tests/test_new.py::t9": ["sentinel"]})
    _baseline(base, [])
    res = _ratchet(rep, base)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "WARNING" in res.stdout and "tests/test_new.py::t9" in res.stdout, res.stdout


def test_ratchet_new_node_mixing_sentinel_and_egress_exits_1(tmp_path):
    """R7: the rule is 'classes INCLUDE egress', not 'classes == {egress}' -- the
    commonest shape of a new offender (the baseline carries sentinel,egress nodes)."""
    _ratchet_script()
    rep, base = tmp_path / "r.json", tmp_path / "b.txt"
    _write_report(rep, {"tests/test_new.py::t9": ["socket.getaddrinfo x.supabase.invalid:443",
                                                  "socket.getaddrinfo api.openai.com:443"]},
                  classes={"tests/test_new.py::t9": ["egress", "sentinel"]})
    _baseline(base, [])
    res = _ratchet(rep, base)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "NEW: tests/test_new.py::t9" in res.stdout, res.stdout


def test_ratchet_classifies_targets_when_the_report_has_no_classes(tmp_path):
    """An ip-literal-only new node (classified from its target) is a WARNING; a named
    host in the same report is egress and fails."""
    _ratchet_script()
    rep, base = tmp_path / "r.json", tmp_path / "b.txt"
    _write_report(rep, {"tests/test_lit.py::t": ["socket.connect 192.0.2.1:443"]})
    _baseline(base, [])
    res = _ratchet(rep, base)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "WARNING" in res.stdout and "tests/test_lit.py::t" in res.stdout, res.stdout
    _write_report(rep, {"tests/test_lit.py::t": ["socket.connect 192.0.2.1:443"],
                        "tests/test_dns.py::t": ["socket.getaddrinfo example.com:443"]})
    res = _ratchet(rep, base)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "tests/test_dns.py::t" in res.stdout, res.stdout


def test_ratchet_warns_when_a_baseline_node_gains_a_class(tmp_path):
    """A sentinel-only baseline node that starts making a real call is not a NEW node,
    so R7 does not fail it -- but it must not pass silently either."""
    _ratchet_script()
    rep, base = tmp_path / "r.json", tmp_path / "b.txt"
    _write_report(rep, {"tests/test_a.py::t": ["socket.getaddrinfo api.openai.com:443"]},
                  classes={"tests/test_a.py::t": ["egress"]})
    base.write_text("# generated\ntests/test_a.py::t sentinel\n", encoding="utf-8")
    res = _ratchet(rep, base)
    assert res.returncode == 0, res.stdout + res.stderr
    warned = [ln for ln in res.stdout.splitlines()
              if "WARNING" in ln and "tests/test_a.py::t" in ln and "egress" in ln]
    assert warned, res.stdout


def test_ratchet_never_fails_on_the_collection_pseudo_node(tmp_path):
    _ratchet_script()
    rep, base = tmp_path / "r.json", tmp_path / "b.txt"
    _write_report(rep, {"<collection>": ["socket.create_connection example.com:443"]},
                  classes={"<collection>": ["egress"]})
    _baseline(base, [])
    res = _ratchet(rep, base)
    assert res.returncode == 0, res.stdout + res.stderr


def test_ratchet_missing_report_exits_2(tmp_path):
    _ratchet_script()
    base = tmp_path / "b.txt"
    _baseline(base, [])
    res = _ratchet(tmp_path / "absent.json", base)
    assert res.returncode == 2, res.stdout + res.stderr


def test_ratchet_write_regenerates_the_baseline_sorted(tmp_path):
    _ratchet_script()
    rep, base = tmp_path / "r.json", tmp_path / "b.txt"
    _write_report(rep, {"tests/test_z.py::t": ["x"], "tests/test_a.py::t": ["y"],
                        "<collection>": ["z"]},
                  classes={"tests/test_z.py::t": ["egress", "sentinel"]})
    res = _ratchet(rep, base, "--write")
    assert res.returncode == 0, res.stdout + res.stderr
    lines = [ln for ln in base.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    assert lines == ["tests/test_a.py::t egress", "tests/test_z.py::t sentinel,egress"]


def test_committed_baseline_is_sorted_and_unique():
    _ratchet_script()
    path = REPO_ROOT / "tests" / ".network_attempt_baseline.txt"
    assert path.is_file(), _RED % "tests/.network_attempt_baseline.txt"
    ids = _baseline_ids(path)
    assert ids == sorted(set(ids))


def test_ci_runs_the_network_attempt_ratchet():
    """R16: the "Run unit tests" step writes the report and the plain following
    "Network-attempt ratchet" step reads the SAME file -- a path mismatch between the
    two steps (file name OR directory) reddens here instead of only failing CI with the
    ratchet's exit 2. The ratchet step must also be able to fail the job: one command,
    exactly the script's argv (no ``|| true``, no second command), no
    ``continue-on-error`` on the step or the job, no ``if:``. R19: the ratchet step has
    no ``env:`` (a RUNNER_TEMP override) and no ``shell:`` (a shell that never runs the
    script), and its report path is not single-quoted (``'$RUNNER_TEMP/...'`` never
    expands). Anything else about the runner is left to CI's own exit 2."""
    _ratchet_script()
    import shlex

    import yaml

    ci = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    job = ci["jobs"]["backend-tests"]
    steps = job["steps"]
    names = [s.get("name") for s in steps]
    test_step = steps[names.index("Run unit tests")]
    ratchet = steps[names.index("Network-attempt ratchet")]

    def _runner_temp(path):
        # ${{ runner.temp }} (expression) and $RUNNER_TEMP / ${RUNNER_TEMP} (shell env)
        # are the same directory on a GitHub runner; anything else is a different one.
        return re.sub(r"\$\{\{\s*runner\.temp\s*\}\}|\$\{RUNNER_TEMP\}|\$RUNNER_TEMP(?![A-Za-z0-9_])",
                      "<runner.temp>", path)

    report_path = _runner_temp(test_step["env"]["QAREN_NETGUARD_REPORT"])
    assert report_path == "<runner.temp>/netguard_report.json", report_path
    run_lines = [ln for ln in ratchet["run"].splitlines() if ln.strip()]
    assert len(run_lines) == 1, ratchet["run"]  # one command: no `set +e`, no fallback line
    argv = shlex.split(run_lines[0])
    assert len(argv) == 4, argv  # no `|| true`, no `; exit 0`, no extra argument
    assert argv[:2] == ["python", "scripts/netguard_ratchet.py"], argv
    assert argv[3] == "tests/.network_attempt_baseline.txt", argv
    assert _runner_temp(argv[2]) == report_path, (argv[2], test_step["env"]["QAREN_NETGUARD_REPORT"])
    # R19 (AD1): the RAW report token (quotes kept) must not be single-quoted anywhere --
    # the shell does not expand $RUNNER_TEMP inside single quotes.
    raw_argv = shlex.split(run_lines[0], posix=False)
    assert len(raw_argv) == 4, raw_argv
    assert "'" not in raw_argv[2], raw_argv[2]
    assert names.index("Network-attempt ratchet") > names.index("Run unit tests")
    assert "if" not in ratchet, ratchet  # a plain following step, never `if: always()`
    assert "env" not in ratchet, ratchet  # R19 (AD2): no RUNNER_TEMP override for the step
    assert "shell" not in ratchet, ratchet  # R19 (AD5): the default shell runs the script
    assert not ratchet.get("continue-on-error"), ratchet
    assert not job.get("continue-on-error"), job.get("continue-on-error")


# ===========================================================================
# E. sentinels
# ===========================================================================
def _fake_modules(*, key=None, singleton=None):
    class _Scoring:
        def compute_scores(self, *a, **k):
            return {}

    pkg = types.ModuleType("app.services")
    ps = types.ModuleType("app.services.price_service")
    pkg.price_service = ps
    serper = types.ModuleType("app.services.serper_service")
    serper.SERPER_API_KEY = key
    scoring = types.ModuleType("app.services.scoring_service")
    scoring.ScoringService = _Scoring
    scoring._scoring_service = singleton if singleton is not None else _Scoring()
    return {
        "app": types.ModuleType("app"),
        "app.services": pkg,
        "app.services.price_service": ps,
        "app.services.serper_service": serper,
        "app.services.scoring_service": scoring,
    }


def _leaks(before_mods, mutate):
    h = _hermeticity()
    before = h.snapshot(before_mods)
    mutate(before_mods)
    return h.compare(before, h.snapshot(before_mods))


def test_sentinel_is_silent_when_nothing_changed():
    assert _leaks(_fake_modules(), lambda m: None) == []


def test_sentinel_flags_a_replaced_price_service_module():
    def _swap(m):
        new = types.ModuleType("app.services.price_service")
        m["app.services.price_service"] = new
        m["app.services"].price_service = new

    out = _leaks(_fake_modules(), _swap)
    assert out and any("sys.modules" in s and "price_service" in s for s in out), out


def test_sentinel_flags_a_rebound_price_service_package_attribute():
    def _rebind(m):
        m["app.services"].price_service = types.ModuleType("app.services.price_service")

    out = _leaks(_fake_modules(), _rebind)
    assert out and any("package attribute" in s for s in out), out


def test_sentinel_flags_a_deleted_price_service_module():
    out = _leaks(_fake_modules(), lambda m: m.pop("app.services.price_service"))
    assert out and any("sys.modules['app.services.price_service'] removed" in s for s in out), out


def test_sentinel_flags_a_changed_serper_key():
    def _set(m):
        m["app.services.serper_service"].SERPER_API_KEY = "test-key"

    out = _leaks(_fake_modules(), _set)
    assert out and any("SERPER_API_KEY" in s for s in out), out
    assert not any("test-key" in s for s in out), out  # values are never printed in clear


def test_sentinel_flags_a_replaced_scoring_singleton():
    def _swap(m):
        sc = m["app.services.scoring_service"]
        sc._scoring_service = sc.ScoringService()

    out = _leaks(_fake_modules(), _swap)
    assert out and any("_scoring_service" in s for s in out), out


def test_sentinel_flags_an_instance_level_compute_scores_shadow():
    """#186 measured: monkeypatch.setattr(<singleton>, "compute_scores", spy) undoes by
    SETTING the bound method it read, leaving vars(singleton)['compute_scores'] -- whose
    __func__ is the ORIGINAL function, so a __func__ identity check alone misses it."""
    def _shadow(m):
        single = m["app.services.scoring_service"]._scoring_service
        single.compute_scores = single.compute_scores  # what monkeypatch's undo leaves

    out = _leaks(_fake_modules(), _shadow)
    assert out and any("compute_scores" in s for s in out), out


def _lazy_scoring_modules():
    """_fake_modules with the scoring singleton not built yet: the real module holds
    ``_scoring_service = None`` until the first get_scoring_service() call."""
    mods = _fake_modules()
    mods["app.services.scoring_service"]._scoring_service = None
    return mods


def test_sentinel_flags_a_shadow_on_a_singleton_created_during_the_test():
    """R15: the leaker is the FIRST to build the lazy singleton and leaves the #186
    shadow on it. Without this item every later test snapshots the shadow as its
    baseline and the failure lands on a victim."""
    def _create_and_shadow(m):
        sc = m["app.services.scoring_service"]
        sc._scoring_service = single = sc.ScoringService()
        single.compute_scores = single.compute_scores  # what monkeypatch's undo leaves

    out = _leaks(_lazy_scoring_modules(), _create_and_shadow)
    assert out and any("compute_scores" in s and "created during the test" in s for s in out), out


def test_sentinel_is_silent_when_a_test_creates_the_singleton_without_a_shadow():
    """R15: building the lazy singleton is legitimate; only a shadow on it leaks."""
    def _create(m):
        sc = m["app.services.scoring_service"]
        sc._scoring_service = sc.ScoringService()

    assert _leaks(_lazy_scoring_modules(), _create) == []


def test_sentinel_flags_a_deleted_app_module():
    out = _leaks(_fake_modules(), lambda m: m.pop("app.services.serper_service"))
    assert out and any("app.services.serper_service" in s for s in out), out


_LEAK_CONFTEST = textwrap.dedent(
    """
    import sys
    import types

    # fake app modules only -- no real app code is imported in this subprocess
    for _name in ("app", "app.services", "app.services.serper_service"):
        sys.modules.setdefault(_name, types.ModuleType(_name))
    sys.modules["app.services.serper_service"].SERPER_API_KEY = None

    pytest_plugins = ["tests._hermeticity"]
    """
)

_LEAK_TESTS = textwrap.dedent(
    """
    import sys


    def test_leaks_the_key():
        sys.modules["app.services.serper_service"].SERPER_API_KEY = "leaked"


    def test_innocent_victim():
        assert True
    """
)


def test_sentinel_errors_the_leaking_test_at_teardown(tmp_path):
    _hermeticity()
    (tmp_path / "conftest.py").write_text(_LEAK_CONFTEST, encoding="utf-8")
    (tmp_path / "test_leak.py").write_text(_LEAK_TESTS, encoding="utf-8")
    res = _run_pytest(["-q", "-rE", "test_leak.py"], tmp_path)
    out = res.stdout + res.stderr
    assert res.returncode != 0, out
    assert "ERROR test_leak.py::test_leaks_the_key" in out, out
    assert "hermeticity:" in out and "SERPER_API_KEY" in out, out
    assert "test_innocent_victim" not in out.split("short test summary info")[-1], out
    assert "2 passed, 1 error" in out, out


# ===========================================================================
# #183 / #185 / #186 -- the fixed files: in-process pins, then the four CI-order
# subprocess pins (R9), each with the sentinel armed and silent
# ===========================================================================
_FREE_TIER = ["-m", "not (live_unit or live_db or integration)", "--timeout=120", "-q", "-rfE"]
# R20: each subprocess pin runs a whole pytest child over real files -- measured 38-56 s
# on a loaded box -- while CI runs the tree with --timeout=60; the per-test marker
# (pytest-timeout) overrides the CLI value for these four nodes only.
_SUBPROCESS_PIN_TIMEOUT = pytest.mark.timeout(300)


def _ci_order_run(*files):
    _hermeticity()
    _netguard()
    res = _run_pytest([*_FREE_TIER, *files], REPO_ROOT)
    out = res.stdout + res.stderr
    assert res.returncode == 0, out[-4000:]
    # The sentinel was ARMED in that run (so the silence below is meaningful) ...
    armed = re.search(r"\[hermeticity\] sentinel checked (\d+) test", out)
    assert armed and int(armed.group(1)) > 0, out[-4000:]
    # ... and nothing in the fixed files leaked.
    assert "hermeticity:" not in out, out[-4000:]
    return out


def test_183_hotfix_reload_tests_leave_the_serper_module_in_place():
    """In-process: the three TestSearchProductPricesIntegration bodies, each with its own
    MonkeyPatch undone, leave serper_service's module object and key exactly as found."""
    _hermeticity()
    import app.services.serper_service as serper_service

    from tests import test_hotfix_shopping_query_clean as hot

    module_before, key_before = sys.modules["app.services.serper_service"], serper_service.SERPER_API_KEY
    cls = hot.TestSearchProductPricesIntegration
    for name in ("test_cleaner_runs_before_serper_call",
                 "test_clean_query_passes_through_unchanged",
                 "test_us_fallback_uses_cleaned_query"):
        mp = pytest.MonkeyPatch()
        try:
            asyncio.run(getattr(cls(), name)(mp))
        finally:
            mp.undo()
    after = sys.modules["app.services.serper_service"]
    assert after is module_before
    key_after = after.SERPER_API_KEY
    assert key_after == key_before


@_SUBPROCESS_PIN_TIMEOUT
def test_183_hotfix_reload_tests_then_w49_in_ci_order():
    _ci_order_run("tests/test_hotfix_shopping_query_clean.py",
                  "tests/test_w49_extraction_catch_redaction.py")


def test_185_cycle_proof_leaves_price_service_in_place():
    _hermeticity()
    import app.services as pkg
    import app.services.price_service as ps_before

    from tests import test_platform_router as tpr

    tpr.test_does_not_import_price_service()
    assert sys.modules.get("app.services.price_service") is ps_before
    assert getattr(pkg, "price_service", None) is ps_before


@_SUBPROCESS_PIN_TIMEOUT
def test_185_platform_router_then_l13_then_w49_in_ci_order():
    _ci_order_run("tests/test_platform_router.py", "tests/test_shopify_discovery_l13.py",
                  "tests/test_w49_extraction_catch_redaction.py")


def test_186_w43_sync_pin_leaves_no_instance_compute_scores_on_the_singleton():
    """In-process: W4-3's `_run_sync` (the helper behind the four leaking nodes) with its
    MonkeyPatch undone leaves no instance-level compute_scores on the singleton."""
    _hermeticity()
    from app.services import scoring_service

    from tests import test_prescoring_showable_guard as w43

    single = scoring_service.get_scoring_service()
    assert "compute_scores" not in vars(single)
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv(w43.FLAG, "true")
        _resp, holder = w43._run_sync(mp, url=w43.GOOG0)
    finally:
        mp.undo()
    assert holder.get("scored_pd") is not None, "the sync path never reached compute_scores"
    assert scoring_service.get_scoring_service() is single
    assert "compute_scores" not in vars(single)


@_SUBPROCESS_PIN_TIMEOUT
@pytest.mark.parametrize("order", ["w43_first", "w44_first"])
def test_186_prescoring_and_partial_files_pass_in_both_orders(order):
    files = ["tests/test_prescoring_showable_guard.py",
             "tests/test_partial_response_no_fabricated_scores.py"]
    if order == "w44_first":
        files.reverse()
    _ci_order_run(*files)
