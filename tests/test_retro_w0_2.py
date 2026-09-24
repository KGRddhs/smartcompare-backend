"""R-W0 / W0-2b -- RED tests for the shared Supabase transport under
``ENABLE_SUPABASE_CLIENT_REUSE``, plus the flag-OFF construction pins the
retroactive reviewer found missing (mutations M13 / M14 survived the whole
W0-2 unit file).

Spec: the retroactive adversary report on W0-1/W0-2 (PR #135, merge 67f716f2),
defect 1 and defect 5, under the orchestrator's binding ruling for W0-2b:

  the shared transport uses ``http2=False`` -- an HTTP/1.1 keep-alive pool,
  one request per connection -- so a hung PostgREST call cannot
  head-of-line-block unrelated requests, and the read timeout bounds EACH
  call. Pin it with a local fake server that hangs one request while another
  completes. Also pin the flag-OFF construction of the anon and user clients.

Why a REAL TLS + ALPN server on loopback, not a plain-HTTP one: over plain
``http://`` httpx negotiates HTTP/1.1 even when ``http2=True`` (h2c needs prior
knowledge, which ``get_shared_httpx_client`` does not ask for), so a plain
server would pass today and prove nothing. Supabase negotiates ``h2`` over
TLS/ALPN, so the server here offers ``["h2", "http/1.1"]`` over TLS with a
throwaway self-signed certificate generated per test (``cryptography`` is in
the pinned lock). The shared client is the one ``database_service`` builds;
the ONLY test-side change is the trust anchor, supplied through
``SSL_CERT_FILE``, which httpx 0.28.1 honours for ``verify=True``
(``httpx/_config.py:34``) whether the implementation passes ``http2=False``
to ``httpx.Client`` or builds its own ``HTTPTransport``.

The reviewer's repro used a hand-built ``http1=False`` h2c client
(``scratchpad/repro/h2_shared_timeout.py``); these tests drive the PRODUCTION
factory instead, so they turn green only when the factory itself changes.

Offline: the server binds 127.0.0.1 only, and the autouse ``_zero_network``
fixture blocks any non-loopback ``getaddrinfo`` / ``connect`` and fails the
test on any attempt.
"""
from __future__ import annotations

import asyncio
import datetime
import ipaddress
import os
import socket
import ssl
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import httpx
import pytest

from app.services import auth_service, database_service

FLAG = "ENABLE_SUPABASE_CLIENT_REUSE"
TIMEOUT_ENV = "SUPABASE_POSTGREST_TIMEOUT_SECONDS"

FAKE_URL = "https://rw02-probe.supabase.co"
FAKE_ANON = "rw02-anon-key"
FAKE_SERVICE = "rw02-service-key"

# postgrest/constants.py DEFAULT_POSTGREST_CLIENT_TIMEOUT, and httpx's own
# default Timeout -- what a bare create_client(url, key) builds at base
# (measured on the pinned supabase 2.31.0 / httpx 0.28.1).
LIBRARY_DEFAULT_POSTGREST_TIMEOUT = 120
HTTPX_DEFAULT_TIMEOUT = 5.0

# The run_db executor width (ADAPTER_EXECUTOR_MAX_WORKERS default, M13-34).
RUN_DB_EXECUTOR_WIDTH = 40

_PROXY_ENVS = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
)


# ---------------------------------------------------------------------------
# zero-network guard (autouse)
# ---------------------------------------------------------------------------

_REAL_GETADDRINFO = socket.getaddrinfo
_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex


def _is_loopback_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    h = str(host).strip("[]").lower()
    if h == "localhost":
        return True
    try:
        return ipaddress.ip_address(h.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Block every non-loopback resolve and connect; fail at teardown on any
    attempt, including one the code under test swallowed."""
    attempts: List[tuple] = []

    def _guarded_getaddrinfo(host, *args, **kwargs):
        if not _is_loopback_host(host):
            attempts.append(("getaddrinfo", host))
            raise OSError(f"zero-network guard: getaddrinfo({host!r}) blocked")
        return _REAL_GETADDRINFO(host, *args, **kwargs)

    def _check(sock, address, op):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            host = address[0] if isinstance(address, tuple) else address
            if not _is_loopback_host(host):
                attempts.append((op, address))
                raise OSError(f"zero-network guard: {op}({address!r}) blocked")

    def _guarded_connect(self, address):
        _check(self, address, "connect")
        return _REAL_CONNECT(self, address)

    def _guarded_connect_ex(self, address):
        _check(self, address, "connect_ex")
        return _REAL_CONNECT_EX(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", _guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)
    yield attempts
    assert attempts == [], f"zero-network guard: network attempted: {attempts!r}"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Fresh module state per test: no memoised admin client, no shared
    transport, no fail-open latch, fake credentials, flag and knob unset."""
    database_service._reset_client_cache_for_tests()
    auth_service._reset_client_cache_for_tests()
    for mod in (auth_service, database_service):
        monkeypatch.setattr(mod, "SUPABASE_URL", FAKE_URL, raising=False)
        monkeypatch.setattr(mod, "SUPABASE_ANON_KEY", FAKE_ANON, raising=False)
        monkeypatch.setattr(mod, "SUPABASE_SERVICE_KEY", FAKE_SERVICE, raising=False)
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(TIMEOUT_ENV, raising=False)
    yield
    database_service._reset_client_cache_for_tests()
    auth_service._reset_client_cache_for_tests()


# ---------------------------------------------------------------------------
# a loopback TLS server offering h2 AND http/1.1 over ALPN
# ---------------------------------------------------------------------------


def _write_self_signed(tmp_path) -> Tuple[str, str]:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "rw02 loopback")])
    now = datetime.datetime.now(datetime.timezone.utc)
    ski = x509.SubjectKeyIdentifier.from_public_key(key.public_key())
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(ski, critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(ski),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "rw02_cert.pem"
    key_path = tmp_path / "rw02_key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return str(cert_path), str(key_path)


_OK_BODY = b"ok"


class _LoopbackTLSServer:
    """Answers ``/fast`` at once, ``/slow?ms=N`` after N ms, and NEVER answers
    ``/hang`` (a hung PostgREST call) -- over HTTP/2 or HTTP/1.1, whichever
    ALPN selects.

    It runs on its OWN asyncio loop in a daemon thread, so every read and
    write of a TLS connection happens on that one thread (an OpenSSL SSL object
    must not be used from two threads at once) and a delayed HTTP/2 response is
    a ``call_later`` on the same loop. A server fault is RECORDED in
    ``self.errors`` so a test can tell a server bug from client behaviour; a
    CLIENT protocol violation is answered as RFC 9113 requires (GOAWAY
    PROTOCOL_ERROR, close) and recorded in ``self.protocol_violations``."""

    def __init__(self, cert_path: str, key_path: str) -> None:
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(cert_path, key_path)
        self.ctx.set_alpn_protocols(["h2", "http/1.1"])
        self.protocols: List[str] = []
        self.errors: List[str] = []
        self.protocol_violations: List[str] = []
        self.port = 0
        self._server = None
        self._ready = threading.Event()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="rw02-tls-server", daemon=True)
        self._thread.start()
        if not self._ready.wait(30.0):
            raise RuntimeError("loopback TLS server did not start")

    @property
    def base(self) -> str:
        return f"https://127.0.0.1:{self.port}"

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)

        async def _start() -> None:
            self._server = await asyncio.start_server(
                self._client, "127.0.0.1", 0, ssl=self.ctx, backlog=128
            )
            self.port = self._server.sockets[0].getsockname()[1]
            self._ready.set()

        self._loop.run_until_complete(_start())
        self._loop.run_forever()
        pending = asyncio.all_tasks(self._loop)
        for task in pending:
            task.cancel()
        if pending:
            self._loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
        self._loop.close()

    def close(self) -> None:
        def _stop() -> None:
            if self._server is not None:
                self._server.close()
            self._loop.stop()

        if self._loop.is_running():
            self._loop.call_soon_threadsafe(_stop)
        self._thread.join(timeout=10.0)

    @staticmethod
    def _delay_for(path: str) -> Optional[float]:
        """None = never answer; else seconds to wait before answering."""
        if path.startswith("/hang"):
            return None
        if path.startswith("/slow"):
            try:
                return int(path.split("ms=", 1)[1]) / 1000.0
            except (IndexError, ValueError):
                return 0.0
        return 0.0

    async def _client(self, reader, writer) -> None:
        sslobj = writer.get_extra_info("ssl_object")
        proto = (sslobj.selected_alpn_protocol() if sslobj is not None else None) or "http/1.1"
        self.protocols.append(proto)
        try:
            if proto == "h2":
                await self._serve_h2(reader, writer)
            else:
                await self._serve_h1(reader, writer)
        except (asyncio.CancelledError, asyncio.IncompleteReadError, ConnectionError):
            pass
        except Exception as exc:  # noqa: BLE001 - recorded, asserted on by tests
            self.errors.append(repr(exc))
        finally:
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass

    async def _serve_h1(self, reader, writer) -> None:
        while True:
            head = await reader.readuntil(b"\r\n\r\n")
            path = head.split(b"\r\n", 1)[0].split(b" ")[1].decode("ascii", "replace")
            delay = self._delay_for(path)
            if delay is None:
                await asyncio.Event().wait()  # hold the connection, never answer
            if delay:
                await asyncio.sleep(delay)
            writer.write(
                b"HTTP/1.1 200 OK\r\ncontent-type: text/plain\r\ncontent-length: "
                + str(len(_OK_BODY)).encode()
                + b"\r\n\r\n"
                + _OK_BODY
            )
            await writer.drain()

    async def _serve_h2(self, reader, writer) -> None:
        import h2.config
        import h2.connection
        import h2.errors
        import h2.events
        import h2.exceptions

        conn = h2.connection.H2Connection(h2.config.H2Configuration(client_side=False))
        conn.initiate_connection()
        writer.write(conn.data_to_send())
        loop = asyncio.get_running_loop()

        def _respond(stream_id: int) -> None:
            try:
                conn.send_headers(
                    stream_id,
                    [(":status", "200"), ("content-length", str(len(_OK_BODY)))],
                )
                conn.send_data(stream_id, _OK_BODY, end_stream=True)
            except h2.exceptions.H2Error:
                return  # the client reset the stream (e.g. its own timeout)
            out = conn.data_to_send()
            if out and not writer.is_closing():
                writer.write(out)

        while True:
            await writer.drain()
            data = await reader.read(65536)
            if not data:
                return
            try:
                events = conn.receive_data(data)
            except h2.exceptions.ProtocolError as exc:
                # A CLIENT protocol violation (e.g. a new stream id lower than
                # one already opened, RFC 9113 5.1.1). A compliant server MUST
                # answer with a connection error: GOAWAY(PROTOCOL_ERROR), then
                # close -- which fails every stream in flight on it.
                self.protocol_violations.append(repr(exc))
                conn.close_connection(error_code=h2.errors.ErrorCodes.PROTOCOL_ERROR)
                writer.write(conn.data_to_send())
                await writer.drain()
                return
            for ev in events:
                if isinstance(ev, h2.events.RequestReceived):
                    headers = {
                        (k.decode() if isinstance(k, bytes) else k): (
                            v.decode() if isinstance(v, bytes) else v
                        )
                        for k, v in ev.headers
                    }
                    delay = self._delay_for(headers.get(":path", "/"))
                    if delay is None:
                        continue  # never answer this stream
                    if delay:
                        loop.call_later(delay, _respond, ev.stream_id)
                    else:
                        _respond(ev.stream_id)
            out = conn.data_to_send()
            if out:
                writer.write(out)


@pytest.fixture
def tls_server(tmp_path, monkeypatch):
    cert_path, key_path = _write_self_signed(tmp_path)
    monkeypatch.setenv("SSL_CERT_FILE", cert_path)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    for name in _PROXY_ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    server = _LoopbackTLSServer(cert_path, key_path)
    try:
        yield server
    finally:
        server.close()
    assert server.errors == [], f"the loopback test server itself faulted: {server.errors!r}"


def _shared_client_on(monkeypatch, knob: str) -> httpx.Client:
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, knob)
    shared = database_service.get_shared_httpx_client()
    assert shared is not None, "precondition: the shared transport must build"
    return shared


def _timed_get(client: httpx.Client, url: str) -> Dict[str, Any]:
    t0 = time.monotonic()
    try:
        r = client.get(url)
        return {"status": r.status_code, "elapsed": time.monotonic() - t0,
                "http_version": r.http_version, "error": None}
    except Exception as exc:  # noqa: BLE001 - recorded and asserted on
        return {"status": None, "elapsed": time.monotonic() - t0,
                "http_version": None, "error": type(exc).__name__}


# ===========================================================================
# W0-2b: the shared transport is HTTP/1.1 (RED today)
# ===========================================================================


def test_red_shared_transport_is_built_http1_only(monkeypatch):
    """RED today: ``get_shared_httpx_client`` builds ``http2=True``, so every
    Supabase client in the process multiplexes onto ONE HTTP/2 connection per
    origin. Ruling: ``http2=False``."""
    shared = _shared_client_on(monkeypatch, "8")
    pool = shared._transport._pool

    assert pool._http1 is True, "the shared transport must speak HTTP/1.1"
    assert pool._http2 is False, (
        "the shared Supabase transport is built with http2=True: every "
        "user-scoped, anon and admin client shares one multiplexed connection, "
        "so one hung PostgREST call stalls or poisons unrelated requests "
        "(reviewer: a hung call ran 7.95 s against a 2 s read bound)"
    )


def test_red_shared_transport_negotiates_http11_with_an_h2_capable_server(
    monkeypatch, tls_server
):
    """RED today: against a TLS server that OFFERS h2 over ALPN (as Supabase
    does), the shared client picks HTTP/2."""
    shared = _shared_client_on(monkeypatch, "8")
    r = shared.get(f"{tls_server.base}/fast")

    assert r.status_code == 200, "precondition: the loopback server must answer"
    assert r.http_version == "HTTP/1.1", (
        f"the shared transport negotiated {r.http_version} with an h2-capable "
        f"server (server saw ALPN {tls_server.protocols!r}); it must stay on "
        "HTTP/1.1 so each request gets its own connection"
    )


def test_red_hung_call_under_concurrent_traffic_fails_no_unrelated_request(
    monkeypatch, tls_server
):
    """RED today: while 4 threads keep unrelated requests in flight on the
    shared transport, one hung call's timeout tears down the ONE multiplexed
    HTTP/2 connection under them -- httpcore records the read failure for the
    whole connection and closes it, so every request in flight at that moment
    fails ``RemoteProtocolError('Server disconnected')``. Measured on this box
    through the production factory: ~200 of ~2,000 unrelated requests failed
    at t~1.06 s, the instant the 1.0 s hung call timed out.

    Contract (ruling W0-2b): with one request per connection the hung call
    times out on its OWN connection -- within knob + 0.5 s -- and no unrelated
    request fails. The bound on the hung call is asserted too, because the
    reviewer measured it running 7.95 s against a 2 s bound under traffic on
    an h2c connection (3.98 s re-measured here with the reviewer's script)."""
    knob = 1.0
    shared = _shared_client_on(monkeypatch, str(knob))
    warm = shared.get(f"{tls_server.base}/fast")
    assert warm.status_code == 200, "precondition: the loopback server must answer"

    hung: Dict[str, Any] = {}

    def _hang() -> None:
        hung.update(_timed_get(shared, f"{tls_server.base}/hang"))

    stop_at = time.monotonic() + 3.0
    worker_results: List[Dict[str, Any]] = []
    lock = threading.Lock()

    def _worker() -> None:
        while time.monotonic() < stop_at:
            res = _timed_get(shared, f"{tls_server.base}/fast")
            with lock:
                worker_results.append(res)

    hang_thread = threading.Thread(target=_hang)
    hang_thread.start()
    time.sleep(0.1)
    workers = [threading.Thread(target=_worker) for _ in range(4)]
    for w in workers:
        w.start()
    for w in workers:
        w.join(timeout=30)
    hang_thread.join(timeout=30)

    ok = sum(1 for r in worker_results if r["status"] == 200)
    failed = [r["error"] for r in worker_results if r["status"] != 200]
    assert ok > 0, "precondition: the concurrent traffic must have flowed"
    assert failed == [], (
        f"{len(failed)} of {len(worker_results)} UNRELATED requests failed "
        f"({sorted(set(failed))!r}) because one hung call shared their "
        f"connection (hung call: {hung!r}; client stream-id violations the "
        f"server had to reject: {tls_server.protocol_violations[:2]!r}). A write "
        "such as save_comparison or a usage increment can commit server-side "
        "while its caller sees this error"
    )
    assert hung.get("error") is not None and "Timeout" in hung["error"], (
        f"the hung call must end in its OWN timeout, got {hung!r}"
    )
    assert hung["elapsed"] <= knob + 0.5, (
        f"a hung PostgREST call ran {hung['elapsed']:.2f}s against a {knob}s "
        "read bound while unrelated traffic flowed"
    )


def test_red_concurrent_requests_on_the_shared_transport_never_fail(
    monkeypatch, tls_server
):
    """RED today -- measured here, NOT in the reviewer's report: with NO hung
    call at all, 4 threads looping plain 200-OK requests through the shared
    HTTP/2 client for 2 s lose ~4% of them (79-135 of ~2,000-2,500 in every
    run) to ``RemoteProtocolError('Server disconnected')``, and the client
    opens 20-40 connections instead of reusing one. The server side sees the
    CLIENT reset each connection; in some runs it also receives a new stream
    id lower than one already opened (``StreamIDTooLowError``), which RFC 9113
    5.1.1 requires a server to answer with a connection error. Mechanism:
    httpcore 1.0.9 allocates the stream id OUTSIDE its write lock
    (``httpcore/_sync/http2.py:134`` ``get_next_available_stream_id``, then
    ``:144`` ``_send_request_headers``), so concurrent ``run_db`` threads race
    on one connection. The same client with ``http2=False`` lost 0 of ~4,000
    with 8 threads. This is exactly the traffic shape of every request-path
    Supabase call under ``ENABLE_SUPABASE_CLIENT_REUSE``."""
    shared = _shared_client_on(monkeypatch, "1.0")
    warm = shared.get(f"{tls_server.base}/fast")
    assert warm.status_code == 200, "precondition: the loopback server must answer"

    stop_at = time.monotonic() + 2.0
    results: List[Dict[str, Any]] = []
    lock = threading.Lock()

    def _worker() -> None:
        while time.monotonic() < stop_at:
            res = _timed_get(shared, f"{tls_server.base}/fast")
            with lock:
                results.append(res)

    workers = [threading.Thread(target=_worker) for _ in range(4)]
    for w in workers:
        w.start()
    for w in workers:
        w.join(timeout=30)

    failed = [r["error"] for r in results if r["status"] != 200]
    assert len(results) > 100, "precondition: the concurrent traffic must have flowed"
    assert failed == [], (
        f"{len(failed)} of {len(results)} plain requests FAILED with no hung call "
        f"at all ({sorted(set(failed))!r}; {len(tls_server.protocols)} "
        f"connections opened over {sorted(set(tls_server.protocols))!r}; client "
        f"stream-id violations: {tls_server.protocol_violations[:2]!r}) -- "
        "concurrent threads cannot safely share one HTTP/2 connection"
    )


def test_red_fast_request_during_a_hung_call_succeeds(monkeypatch, tls_server):
    """RED today: a 300 ms request issued 0.8 s into a hung call on the shared
    HTTP/2 connection is starved by the hung stream's read and then killed by
    the connection-wide ReadTimeout (reviewer: failed after 0.2 s; succeeded in
    0.44 s on its own connection). It must succeed, well inside the knob."""
    knob = 1.0
    shared = _shared_client_on(monkeypatch, str(knob))
    warm = shared.get(f"{tls_server.base}/fast")
    assert warm.status_code == 200, "precondition: the loopback server must answer"

    hung: Dict[str, Any] = {}
    hang_thread = threading.Thread(
        target=lambda: hung.update(_timed_get(shared, f"{tls_server.base}/hang"))
    )
    hang_thread.start()
    time.sleep(0.8)
    victim = _timed_get(shared, f"{tls_server.base}/slow?ms=300")
    hang_thread.join(timeout=30)

    assert victim["status"] == 200, (
        f"an unrelated 300 ms request issued during a hung call FAILED on the "
        f"shared transport ({victim!r}; hung call: {hung!r}) -- a write such as "
        "save_comparison can commit server-side while the client sees this error"
    )
    assert victim["elapsed"] < knob - 0.1, (
        f"the unrelated request took {victim['elapsed']:.2f}s: it was "
        "head-of-line-blocked behind the hung call"
    )


# ===========================================================================
# PINS -- green today, must stay green
# ===========================================================================


def test_pin_hung_call_alone_is_bounded_by_the_knob(monkeypatch, tls_server):
    """PIN (green today): a hung call with NO other traffic ends at the knob
    (it is the only reader, so the per-read timeout IS the per-call timeout).
    Proves the loopback server and the knob work in both transports."""
    knob = 1.0
    shared = _shared_client_on(monkeypatch, str(knob))
    assert shared.get(f"{tls_server.base}/fast").status_code == 200
    res = _timed_get(shared, f"{tls_server.base}/hang")
    assert res["error"] is not None and "Timeout" in res["error"], res
    assert knob - 0.2 <= res["elapsed"] <= knob + 0.5, res


def test_pin_shared_transport_config_is_otherwise_unchanged(monkeypatch):
    """PIN (green today): the knob is the read bound, connect stays 3.0 s,
    redirects are followed, the pool is at least the run_db executor width
    (reviewer: size max_connections >= 40 + headroom), and every Supabase
    client in the process -- anon, user-scoped, both admin -- still rides the
    ONE shared client (the CR-PERFORMANCE-03 win is the shared SSLContext)."""
    shared = _shared_client_on(monkeypatch, "8")
    assert shared.timeout.read == 8.0
    assert shared.timeout.connect == 3.0
    assert shared.follow_redirects is True
    assert shared._transport._pool._max_connections >= RUN_DB_EXECUTOR_WIDTH

    assert auth_service.get_auth_client().options.httpx_client is shared
    assert database_service.get_user_supabase_client("tok").options.httpx_client is shared
    assert auth_service.get_admin_client().options.httpx_client is shared
    assert database_service.get_admin_supabase_client().options.httpx_client is shared
    assert database_service.get_shared_httpx_client() is shared


def test_pin_shared_transport_pool_limits_are_the_base_values(monkeypatch):
    """PIN (fixer; surviving mutant N11 max_connections=40): W0-2b changes the
    protocol ONLY. The pool limits stay the base 100 / 20 the PR body states --
    40 would still clear the >= run_db-width floor above, so that floor alone
    cannot see a silent shrink to the executor width with no headroom."""
    shared = _shared_client_on(monkeypatch, "8")
    pool = shared._transport._pool
    assert pool._max_connections == 100
    assert pool._max_keepalive_connections == 20


def test_pin_shared_transport_keeps_http11_connections_alive(monkeypatch, tls_server):
    """PIN (fixer; surviving mutant N10 max_keepalive_connections=0): the
    HTTP/1.1 transport is a KEEP-ALIVE pool. Sequential calls reuse one TLS
    connection, so W0-2b pays one handshake per concurrently-busy connection,
    not one per request. With keep-alive disabled every call would open (and
    handshake) a fresh connection."""
    shared = _shared_client_on(monkeypatch, "8")
    for _ in range(5):
        res = _timed_get(shared, f"{tls_server.base}/fast")
        assert res["status"] == 200 and res["http_version"] == "HTTP/1.1", res
    assert tls_server.protocols == ["http/1.1"], (
        f"5 sequential requests opened {len(tls_server.protocols)} connections "
        f"({tls_server.protocols!r}); the shared transport must keep one alive"
    )


def test_pin_every_leg_adopts_the_one_shared_client(monkeypatch):
    """PIN (green today): the postgrest and gotrue legs adopt the SHARED client
    as-is (so whatever protocol it is built with is what every leg speaks)."""
    shared = _shared_client_on(monkeypatch, "8")
    client = database_service.get_user_supabase_client("tok")
    assert client.postgrest.session is shared
    assert client.auth._http_client is shared
    assert client.postgrest.headers["Authorization"] == "Bearer tok"
    assert "tok" not in shared.headers.get("authorization", "")


# ---------------------------------------------------------------------------
# flag-OFF construction pins (M13 / M14 -- unpinned before this file)
# ---------------------------------------------------------------------------


def _recording_create_client(calls: List[Tuple[tuple, dict]]):
    class _Stub:
        def __getattr__(self, name):
            return self

        def __call__(self, *a, **k):
            return self

    def _record(*args, **kwargs):
        calls.append((args, kwargs))
        return _Stub()

    return _record


def _assert_flag_off_anon_construction(calls: List[Tuple[tuple, dict]], n: int) -> None:
    """R-AUTH W1-4c (merged after this pin was written, unflagged by ruling) makes
    ``get_auth_client()`` ALWAYS pass ``options=ClientOptions(auto_refresh_token=False,
    persist_session=False)`` so a server client never auto-refreshes; with the reuse
    flag OFF that is now the base construction: positional (URL, ANON_KEY), the
    ``options`` keyword ONLY, no injected transport, both auth flags False."""
    assert len(calls) == n, calls
    for args, kwargs in calls:
        assert args == (FAKE_URL, FAKE_ANON), calls
        assert set(kwargs) == {"options"}, (
            f"flag-OFF get_auth_client() changed its construction: {calls!r}"
        )
        opts = kwargs["options"]
        assert getattr(opts, "httpx_client", None) is None, (
            f"flag-OFF anon client construction injects a transport: {calls!r}"
        )
        assert opts.auto_refresh_token is False and opts.persist_session is False, (
            f"flag-OFF anon client lost the W1-4c no-auto-refresh options: {calls!r}"
        )


def test_pin_flag_off_anon_client_is_the_bare_base_construction():
    """PIN (green today) -- kills M13: with the flag OFF,
    ``auth_service.get_auth_client()`` is exactly base: ONE positional
    ``create_client(URL, ANON_KEY)`` with only the W1-4c ``options`` keyword
    (auto_refresh_token=False, persist_session=False, no httpx_client), a fresh
    client per call, and the shared transport is never built."""
    assert FLAG not in os.environ
    calls: List[Tuple[tuple, dict]] = []
    with patch("app.services.auth_service.create_client", new=_recording_create_client(calls)), \
         patch("app.services.database_service.create_client", new=_recording_create_client(calls)):
        auth_service.get_auth_client()
        auth_service.get_auth_client()
    _assert_flag_off_anon_construction(calls, 2)
    assert database_service._SHARED_HTTPX is None, (
        "flag OFF built the shared transport"
    )

    real = auth_service.get_auth_client()
    assert real.options.httpx_client is None, (
        "flag-OFF anon client is on an injected (shared) transport"
    )
    assert real.postgrest.session.timeout.read == LIBRARY_DEFAULT_POSTGREST_TIMEOUT
    assert real.postgrest.session.timeout.connect == LIBRARY_DEFAULT_POSTGREST_TIMEOUT
    assert real.auth._http_client.timeout.read == HTTPX_DEFAULT_TIMEOUT
    assert database_service._SHARED_HTTPX is None


def test_pin_flag_off_user_client_is_the_bare_base_construction():
    """PIN (green today) -- kills M14: with the flag OFF,
    ``database_service.get_user_supabase_client(token)`` is exactly base: ONE
    positional ``create_client(URL, ANON_KEY)``, the token on the client's own
    postgrest headers, the library's 120 s postgrest timeout, no shared
    transport."""
    assert FLAG not in os.environ
    calls: List[Tuple[tuple, dict]] = []
    with patch("app.services.database_service.create_client", new=_recording_create_client(calls)):
        database_service.get_user_supabase_client("tok-a")
    assert calls == [((FAKE_URL, FAKE_ANON), {})], (
        f"flag-OFF get_user_supabase_client() changed its construction: {calls!r}"
    )

    real = database_service.get_user_supabase_client("tok-b")
    assert real.options.httpx_client is None
    assert real.postgrest.headers["Authorization"] == "Bearer tok-b"
    assert real.postgrest.session.timeout.read == LIBRARY_DEFAULT_POSTGREST_TIMEOUT
    assert real.postgrest.session.timeout.connect == LIBRARY_DEFAULT_POSTGREST_TIMEOUT
    assert real.auth._http_client.timeout.read == HTTPX_DEFAULT_TIMEOUT
    assert database_service._SHARED_HTTPX is None


def test_pin_flag_off_after_on_rolls_anon_and_user_clients_back(monkeypatch):
    """PIN (green today): the Railway rollback. The shared transport was built
    while the flag was ON; with the flag flipped OFF (no restart) new anon and
    user-scoped clients must NOT ride it -- they are back on their own
    library-default transports, with the base construction call."""
    shared = _shared_client_on(monkeypatch, "8")
    monkeypatch.delenv(FLAG, raising=False)

    calls: List[Tuple[tuple, dict]] = []
    with patch("app.services.auth_service.create_client", new=_recording_create_client(calls)), \
         patch("app.services.database_service.create_client", new=_recording_create_client(calls)):
        auth_service.get_auth_client()
        database_service.get_user_supabase_client("tok")
    _assert_flag_off_anon_construction(calls[:1], 1)
    assert calls[1] == ((FAKE_URL, FAKE_ANON), {}), calls

    anon = auth_service.get_auth_client()
    user = database_service.get_user_supabase_client("tok")
    for client in (anon, user):
        assert client.options.httpx_client is None
        assert client.postgrest.session is not shared
        assert client.auth._http_client is not shared
        assert client.postgrest.session.timeout.read == LIBRARY_DEFAULT_POSTGREST_TIMEOUT
