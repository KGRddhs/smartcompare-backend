"""Process-wide network guard for the default test tier (netguard 04c, issue #184).

Installed by ``tests/conftest.py`` at import time -- before any ``app.*`` import and
right after the credential neutralisation -- and registered there as a pytest plugin
(``pytest_plugins``). It imports no app code.

WHAT IT BLOCKS. Every non-loopback attempt raises :class:`NetworkBlocked` (an
``OSError`` subclass, so fail-open code takes its offline branch) and is recorded:

  * ``socket.socket.connect`` / ``connect_ex`` and ``socket.create_connection``;
  * on Windows, ``asyncio.windows_events.IocpProactor.connect`` -- the default
    proactor loop connects through ``ConnectEx`` and never calls ``socket.connect``
    (recorded as ``socket.connect`` so a Windows report matches CI's selector loop);
  * ``socket.getaddrinfo`` for a NAME. An IP literal (``ipaddress.ip_address``
    parses it) needs no DNS, so its lookup is allowed; connecting to a non-loopback
    literal is still blocked;
  * curl_cffi, whose native libcurl never touches the Python socket module:
    ``curl_cffi.requests.Session.request``, ``AsyncSession.request``,
    ``curl_cffi.Curl.perform`` and ``curl_cffi.AsyncCurl.add_handle``. A loopback URL
    passed to ``Session.request`` / ``AsyncSession.request`` is let through -- unless
    the call's ``proxy`` / ``proxies`` or the session's ``proxies`` name a
    non-loopback proxy -- and its ``perform`` / ``add_handle`` is allowed for that
    call (a ContextVar). Proxies libcurl reads from the environment are not seen. A bare
    ``Curl.perform`` is also allowed when the handle's own URL (curl
    ``EFFECTIVE_URL``) is loopback -- the ``stream=True`` path performs on an
    executor thread the ContextVar does not reach.

Loopback = ``localhost``, ``127.0.0.0/8`` (numeric forms only -- a NAME such as
``127.0.0.1.nip.io`` goes through real DNS and is blocked), ``::1``, ``::``,
``0.0.0.0``, ``''``, ``None``, ``testserver`` and AF_UNIX paths;
``QAREN_NETGUARD_ALLOW`` may name extra hosts (comma separated).

OPT-OUTS. The ``allow_network`` marker (and the live-tier markers ``live_unit``,
``live_db``, ``integration``, ``bench``, ``live_prod``) lifts the guard for that one
test. Under ``LIVE=1`` (``tests._env_safety.live_mode_enabled``) the guard is not
installed at all -- the live tiers are the point of that run -- and the terminal
summary says so.

REPORT. Each attempt is attributed to the test whose runtest protocol was active
(``<collection>`` for import/collection/session time) and classified by its host:
``sentinel`` (``*.invalid`` / ``neutralized.*`` -- the conftest credential
placeholders), ``ip_literal`` or ``egress``. Attribution is by the process-wide
"current test", not by thread: an attempt from a thread that outlives the test which
started it lands on whichever test is running when it fires (a known limit; the
ratchet names that later test). The terminal summary prints
``[netguard] blocked N attempt(s) from M node(s)``; ``QAREN_NETGUARD_REPORT=<path>``
writes ``{"blocked": n, "nodes": {nodeid: [targets]}, "classes": {nodeid: [classes]}}``
for ``scripts/netguard_ratchet.py``. Attempts are counted, not failed: making them a
failure is the follow-up campaign over the measured offender list.
"""
import contextvars
import json
import os
import socket
import threading
from ipaddress import ip_address as _ip_address  # a private reference: tests patch ipaddress.ip_address
from urllib.parse import urlsplit

import pytest

COLLECTION_NODE = "<collection>"
LIFT_MARKERS = ("allow_network", "live_unit", "live_db", "integration", "bench", "live_prod")
_LOOPBACK_NAMES = frozenset({"", "localhost", "0.0.0.0", "::1", "::", "testserver"})
_ALLOW_EXTRA = frozenset(
    h.strip().lower()
    for h in (os.environ.get("QAREN_NETGUARD_ALLOW") or "").split(",")
    if h.strip()
)

# (nodeid, kind, target, class) per blocked attempt, in order.
_RECORDS = []
_LOCK = threading.Lock()
_CURL_LOOPBACK_OK = contextvars.ContextVar("qaren_netguard_curl_loopback_ok", default=False)
# The real functions the guarded wrappers delegate to, looked up at CALL time.
_REAL = {}
_STATE = {"installed": False, "live_skip": False, "node": None, "lifted": False}


class NetworkBlocked(OSError):
    """Raised for every non-loopback network attempt under the guard."""


def _norm(host):
    if isinstance(host, (bytes, bytearray)):
        host = bytes(host).decode("ascii", "replace")
    if not isinstance(host, str):
        return host
    return host.strip().lower().strip("[]").split("%", 1)[0]


def _is_ip_literal(host):
    h = _norm(host)
    if not isinstance(h, str) or not h:
        return False
    try:
        _ip_address(h)
    except ValueError:
        return False
    return True


def _is_loopback(host):
    if host is None:
        return True
    h = _norm(host)
    if not isinstance(h, str):
        return False
    if h in _LOOPBACK_NAMES or h in _ALLOW_EXTRA:
        return True
    try:
        return _ip_address(h).is_loopback
    except ValueError:
        # A short NUMERIC form such as "127.1" (inet_aton reads it as 127.0.0.1) is
        # loopback; a NAME that merely starts with "127." (127.0.0.1.nip.io) is not --
        # it resolves through real DNS.
        return h.startswith("127.") and h.replace(".", "").isdigit()


def classify_host(host):
    """``sentinel`` | ``ip_literal`` | ``egress`` for one attempted host."""
    h = _norm(host)
    if isinstance(h, str) and (h.endswith(".invalid") or h.startswith("neutralized.")):
        return "sentinel"
    if _is_ip_literal(h):
        return "ip_literal"
    return "egress"


def _blocks(host):
    return not _STATE["lifted"] and not _is_loopback(host)


def _record(kind, host, target):
    with _LOCK:
        _RECORDS.append((_STATE["node"] or COLLECTION_NODE, kind, str(target), classify_host(host)))


def _host_of_address(address):
    if isinstance(address, tuple) and address:
        return address[0]
    return None  # AF_UNIX path (str/bytes): loopback-equivalent


def _fmt_address(address):
    return _fmt_hostport(address[0], address[1]) if isinstance(address, tuple) and len(address) >= 2 else repr(address)


def _fmt_hostport(host, port):
    h = _norm(host)
    return ("[%s]:%s" if isinstance(h, str) and ":" in h else "%s:%s") % (h, port)


def _url_text(url):
    if isinstance(url, (bytes, bytearray)):
        return bytes(url).decode("ascii", "replace")
    return "" if url is None else str(url)


def _host_of_url(url):
    text = _url_text(url)
    try:
        host = urlsplit(text).hostname
        if host is None and "://" not in text:
            host = urlsplit("//" + text).hostname
    except ValueError:
        host = None
    return host if host is not None else (text or "<no url>")


def _url_from_call(args, kwargs):
    if "url" in kwargs:
        return kwargs["url"]
    # Session.request(self, method, url, ...): args here EXCLUDE self.
    return args[1] if len(args) >= 2 else None


def _effective_url(curl):
    try:
        from curl_cffi import CurlInfo

        return _url_text(curl.getinfo(CurlInfo.EFFECTIVE_URL))
    except Exception:  # noqa: BLE001 -- unreadable handle: treat as unknown (blocked)
        return ""


def _blocked(kind, host, target):
    _record(kind, host, target)
    raise NetworkBlocked("[netguard] blocked %s to %s" % (kind, target))


def _guarded_connect(self, address):
    host = _host_of_address(address)
    if _blocks(host):
        _blocked("socket.connect", host, _fmt_address(address))
    return _REAL["connect"](self, address)


def _guarded_connect_ex(self, address):
    host = _host_of_address(address)
    if _blocks(host):
        _blocked("socket.connect_ex", host, _fmt_address(address))
    return _REAL["connect_ex"](self, address)


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    if _blocks(host) and not _is_ip_literal(host):
        _blocked("socket.getaddrinfo", host, _fmt_hostport(host, port))
    return _REAL["getaddrinfo"](host, port, *args, **kwargs)


def _guarded_create_connection(address, *args, **kwargs):
    host = _host_of_address(address)
    if _blocks(host):
        _blocked("socket.create_connection", host, _fmt_address(address))
    return _REAL["create_connection"](address, *args, **kwargs)


def _guarded_proactor_connect(self, conn, address):
    # Windows' default asyncio loop connects through IocpProactor.connect
    # (_overlapped.ConnectEx / WSAConnect) and never calls socket.socket.connect.
    # Recorded under the same kind as a plain connect so a Windows report matches
    # the one CI's selector loop (which does go through socket.socket.connect) writes.
    host = _host_of_address(address)
    if _blocks(host):
        _blocked("socket.connect", host, _fmt_address(address))
    return _REAL["proactor_connect"](self, conn, address)


def _proxy_urls(session, kwargs):
    """Every proxy this curl_cffi request could go through: the call's ``proxy`` /
    ``proxies`` and the session's own ``proxies`` (curl_cffi picks one by scheme; the
    guard checks them all). Environment proxies libcurl reads by itself are NOT seen."""
    urls = [kwargs.get("proxy")]
    for mapping in (kwargs.get("proxies"), getattr(session, "proxies", None)):
        if isinstance(mapping, dict):
            urls.extend(mapping.values())
    return [_url_text(u) for u in urls if u]


def _check_curl_request(kind, session, url, kwargs):
    """Block a non-loopback URL, and a loopback URL routed through a non-loopback
    proxy (libcurl would connect to the proxy, not to the loopback host)."""
    host = _host_of_url(url)
    if _blocks(host):
        _blocked(kind, host, _url_text(url))
    for proxy in _proxy_urls(session, kwargs):
        phost = _host_of_url(proxy)
        if _blocks(phost):
            _blocked(kind, phost, "%s (proxy for %s)" % (proxy, _url_text(url)))


def _guarded_session_request(self, *args, **kwargs):
    _check_curl_request("curl_cffi.Session.request", self, _url_from_call(args, kwargs), kwargs)
    token = _CURL_LOOPBACK_OK.set(True)
    try:
        return _REAL["session_request"](self, *args, **kwargs)
    finally:
        _CURL_LOOPBACK_OK.reset(token)


async def _guarded_async_request(self, *args, **kwargs):
    _check_curl_request("curl_cffi.AsyncSession.request", self, _url_from_call(args, kwargs), kwargs)
    token = _CURL_LOOPBACK_OK.set(True)
    try:
        return await _REAL["async_request"](self, *args, **kwargs)
    finally:
        _CURL_LOOPBACK_OK.reset(token)


def _guarded_perform(self, *args, **kwargs):
    if not _CURL_LOOPBACK_OK.get():
        url = _effective_url(self)
        host = _host_of_url(url) if url else "<bare perform>"
        if _blocks(host):
            _blocked("curl_cffi.Curl.perform", host, url or "<bare perform>")
    return _REAL["perform"](self, *args, **kwargs)


def _guarded_add_handle(self, *args, **kwargs):
    if not _CURL_LOOPBACK_OK.get() and not _STATE["lifted"]:
        _blocked("curl_cffi.AsyncCurl.add_handle", "<bare add_handle>", "<bare add_handle>")
    return _REAL["add_handle"](self, *args, **kwargs)


def install():
    """Patch the socket and curl_cffi entry points once per process (idempotent).
    Under ``LIVE=1`` nothing is patched."""
    if _STATE["installed"] or _STATE["live_skip"]:
        return
    from tests._env_safety import live_mode_enabled

    if live_mode_enabled():
        _STATE["live_skip"] = True
        return
    _STATE["installed"] = True

    _REAL["connect"] = socket.socket.connect
    _REAL["connect_ex"] = socket.socket.connect_ex
    _REAL["getaddrinfo"] = socket.getaddrinfo
    _REAL["create_connection"] = socket.create_connection
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    socket.getaddrinfo = _guarded_getaddrinfo
    socket.create_connection = _guarded_create_connection
    try:
        from asyncio import windows_events
    except ImportError:  # not Windows: the selector loop goes through socket.socket.connect
        windows_events = None
    if windows_events is not None:
        _REAL["proactor_connect"] = windows_events.IocpProactor.connect
        windows_events.IocpProactor.connect = _guarded_proactor_connect

    try:
        import curl_cffi
        from curl_cffi import requests as curl_requests
    except Exception:  # noqa: BLE001 -- curl_cffi absent: nothing to patch
        return
    _REAL["session_request"] = curl_requests.Session.request
    curl_requests.Session.request = _guarded_session_request
    _REAL["async_request"] = curl_requests.AsyncSession.request
    curl_requests.AsyncSession.request = _guarded_async_request
    _REAL["perform"] = curl_cffi.Curl.perform
    curl_cffi.Curl.perform = _guarded_perform
    _REAL["add_handle"] = curl_cffi.AsyncCurl.add_handle
    curl_cffi.AsyncCurl.add_handle = _guarded_add_handle


def blocked_records():
    """A copy of every recorded attempt as ``(nodeid, kind, target, class)``."""
    with _LOCK:
        return list(_RECORDS)


def report():
    """``{"blocked": n, "nodes": {nodeid: [targets]}, "classes": {nodeid: [classes]}}``."""
    nodes, classes = {}, {}
    records = blocked_records()
    for nodeid, kind, target, cls in records:
        nodes.setdefault(nodeid, []).append("%s %s" % (kind, target))
        classes.setdefault(nodeid, set()).add(cls)
    return {"blocked": len(records), "nodes": nodes,
            "classes": {k: sorted(v) for k, v in classes.items()}}


# ---- pytest plugin hooks ----------------------------------------------------

def pytest_configure(config):
    install()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item, nextitem):
    _STATE["node"] = item.nodeid
    _STATE["lifted"] = any(item.get_closest_marker(m) for m in LIFT_MARKERS)
    try:
        return (yield)
    finally:
        # The node reset charges a post-last-test attempt (a session-finish hook) to
        # <collection>, never to the last test (pinned). The lifted reset is
        # pinned too (R18): nothing re-arms the guard after a lifted LAST test.
        _STATE["node"] = None
        _STATE["lifted"] = False


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _STATE["installed"]:
        terminalreporter.write_line(
            "[netguard] not installed (LIVE=1 opt-in: the live tiers need the network)")
        return
    data = report()
    nodes = {k: v for k, v in data["nodes"].items() if k != COLLECTION_NODE}
    terminalreporter.write_line(
        "[netguard] blocked %d attempt(s) from %d node(s)" % (data["blocked"], len(nodes)))
    if COLLECTION_NODE in data["nodes"]:
        terminalreporter.write_line("[netguard]   %s: %d attempt(s) outside any test, e.g. %s" % (
            COLLECTION_NODE, len(data["nodes"][COLLECTION_NODE]), data["nodes"][COLLECTION_NODE][0]))
    for nodeid, targets in list(nodes.items())[:40]:
        terminalreporter.write_line("[netguard]   %s [%s] %s" % (
            nodeid, ",".join(data["classes"][nodeid]), targets[0]))
    if len(nodes) > 40:
        terminalreporter.write_line("[netguard]   ... %d more node(s) in the report" % (len(nodes) - 40))
    path = os.environ.get("QAREN_NETGUARD_REPORT")
    if path:
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=1, sort_keys=True)
        except OSError as exc:
            terminalreporter.write_line("[netguard] report write failed: %s" % type(exc).__name__)
