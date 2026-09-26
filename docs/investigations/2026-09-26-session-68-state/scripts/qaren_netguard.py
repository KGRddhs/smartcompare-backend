"""qaren_netguard -- process-wide network guard, a pytest -p plugin (session 68).

Load it BEFORE tests/conftest.py runs:

    PYTHONPATH=<this dir> python -m pytest -p qaren_netguard ...

It imports NO app code, so conftest's credential neutralisation still runs
before any `app.*` import.

What it blocks (every attempt raises NetworkBlocked, an OSError subclass, and
is counted):
  * socket.socket.connect / connect_ex and socket.create_connection to any
    non-loopback address;
  * socket.getaddrinfo for any non-loopback host;
  * curl_cffi (native libcurl never touches the Python socket module):
    curl_cffi.requests.Session.request, AsyncSession.request, Curl.perform
    and AsyncCurl.add_handle.  A loopback URL passed to Session.request /
    AsyncSession.request is allowed through (its perform/add_handle is then
    allowed for that call only); a bare Curl.perform / AsyncCurl.add_handle
    outside such a call is blocked.

Loopback = localhost, 127.0.0.0/8, ::1, 0.0.0.0, '', None and AF_UNIX paths.
QAREN_NETGUARD_ALLOW may name extra hosts (comma separated).

Report: the terminal summary prints the blocked-attempt count and the first
40 distinct targets; if QAREN_NETGUARD_REPORT names a file, a JSON report
{"blocked": n, "targets": [...]} is written there at session end.
"""
import contextvars
import json
import os
import socket
import threading

_BLOCKED = []
_BLOCKED_LOCK = threading.Lock()
_ALLOW_EXTRA = {
    h.strip().lower()
    for h in (os.environ.get("QAREN_NETGUARD_ALLOW") or "").split(",")
    if h.strip()
}
_CURL_LOOPBACK_OK = contextvars.ContextVar("qaren_netguard_curl_loopback_ok", default=False)
_INSTALLED = False


class NetworkBlocked(OSError):
    """Raised for every non-loopback network attempt under the guard."""


def _is_loopback_host(host):
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if not isinstance(host, str):
        return False
    h = host.strip().lower().strip("[]")
    if h in ("", "localhost", "0.0.0.0", "::1", "::", "testserver"):
        return True
    if h.startswith("127."):
        return True
    if h in _ALLOW_EXTRA:
        return True
    return False


def _record(kind, target):
    with _BLOCKED_LOCK:
        _BLOCKED.append((kind, str(target)))


def _host_of_address(address):
    # AF_UNIX: a str/bytes path -> loopback-equivalent.
    if isinstance(address, (str, bytes)):
        return None
    if isinstance(address, tuple) and address:
        return address[0]
    return None


def _host_of_url(url):
    try:
        from urllib.parse import urlsplit
        return urlsplit(str(url)).hostname
    except Exception:  # noqa: BLE001
        return str(url)


def install():
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo
    real_create_connection = socket.create_connection

    def guarded_connect(self, address):
        host = _host_of_address(address)
        if not _is_loopback_host(host):
            _record("socket.connect", address)
            raise NetworkBlocked("[netguard] blocked socket.connect to %r" % (address,))
        return real_connect(self, address)

    def guarded_connect_ex(self, address):
        host = _host_of_address(address)
        if not _is_loopback_host(host):
            _record("socket.connect_ex", address)
            raise NetworkBlocked("[netguard] blocked socket.connect_ex to %r" % (address,))
        return real_connect_ex(self, address)

    def guarded_getaddrinfo(host, port, *args, **kwargs):
        if not _is_loopback_host(host):
            _record("socket.getaddrinfo", host)
            raise NetworkBlocked("[netguard] blocked getaddrinfo for %r" % (host,))
        return real_getaddrinfo(host, port, *args, **kwargs)

    def guarded_create_connection(address, *args, **kwargs):
        host = _host_of_address(address)
        if not _is_loopback_host(host):
            _record("socket.create_connection", address)
            raise NetworkBlocked("[netguard] blocked create_connection to %r" % (address,))
        return real_create_connection(address, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.getaddrinfo = guarded_getaddrinfo
    socket.create_connection = guarded_create_connection

    try:
        import curl_cffi
        from curl_cffi import requests as curl_requests
    except Exception:  # noqa: BLE001 -- curl_cffi absent: nothing to patch
        return

    def _url_from_call(args, kwargs):
        if "url" in kwargs:
            return kwargs["url"]
        # Session.request(self, method, url, ...): args here EXCLUDE self.
        if len(args) >= 2:
            return args[1]
        return None

    real_session_request = curl_requests.Session.request

    def guarded_session_request(self, *args, **kwargs):
        url = _url_from_call(args, kwargs)
        if not _is_loopback_host(_host_of_url(url)):
            _record("curl_cffi.Session.request", url)
            raise NetworkBlocked("[netguard] blocked curl_cffi Session.request to %r" % (url,))
        token = _CURL_LOOPBACK_OK.set(True)
        try:
            return real_session_request(self, *args, **kwargs)
        finally:
            _CURL_LOOPBACK_OK.reset(token)

    curl_requests.Session.request = guarded_session_request

    real_async_request = getattr(curl_requests.AsyncSession, "request", None)
    if real_async_request is not None:
        async def guarded_async_request(self, *args, **kwargs):
            url = _url_from_call(args, kwargs)
            if not _is_loopback_host(_host_of_url(url)):
                _record("curl_cffi.AsyncSession.request", url)
                raise NetworkBlocked("[netguard] blocked curl_cffi AsyncSession.request to %r" % (url,))
            token = _CURL_LOOPBACK_OK.set(True)
            try:
                return await real_async_request(self, *args, **kwargs)
            finally:
                _CURL_LOOPBACK_OK.reset(token)

        curl_requests.AsyncSession.request = guarded_async_request

    real_perform = curl_cffi.Curl.perform

    def guarded_perform(self, *args, **kwargs):
        if not _CURL_LOOPBACK_OK.get():
            _record("curl_cffi.Curl.perform", "<bare perform>")
            raise NetworkBlocked("[netguard] blocked bare curl_cffi Curl.perform")
        return real_perform(self, *args, **kwargs)

    curl_cffi.Curl.perform = guarded_perform

    async_curl = getattr(curl_cffi, "AsyncCurl", None)
    if async_curl is not None and hasattr(async_curl, "add_handle"):
        real_add_handle = async_curl.add_handle

        def guarded_add_handle(self, *args, **kwargs):
            if not _CURL_LOOPBACK_OK.get():
                _record("curl_cffi.AsyncCurl.add_handle", "<bare add_handle>")
                raise NetworkBlocked("[netguard] blocked bare curl_cffi AsyncCurl.add_handle")
            return real_add_handle(self, *args, **kwargs)

        async_curl.add_handle = guarded_add_handle


def blocked_count():
    with _BLOCKED_LOCK:
        return len(_BLOCKED)


def blocked_targets(limit=40):
    with _BLOCKED_LOCK:
        seen = []
        for kind, target in _BLOCKED:
            key = "%s %s" % (kind, target)
            if key not in seen:
                seen.append(key)
            if len(seen) >= limit:
                break
        return seen


# ---- pytest plugin hooks -------------------------------------------------

def pytest_configure(config):
    install()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    n = blocked_count()
    terminalreporter.write_line("[netguard] blocked %d network attempt(s)" % n)
    for t in blocked_targets():
        terminalreporter.write_line("[netguard]   %s" % t)
    report = os.environ.get("QAREN_NETGUARD_REPORT")
    if report:
        try:
            with open(report, "w", encoding="utf-8") as fh:
                json.dump({"blocked": n, "targets": blocked_targets(400)}, fh, indent=1)
        except Exception as e:  # noqa: BLE001
            terminalreporter.write_line("[netguard] report write failed: %s" % type(e).__name__)


install()
