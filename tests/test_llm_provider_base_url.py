"""OPENAI_BASE_URL: the provider indirection in app/services/llm_provider.py.

Contract pinned here:
  * unset / blank / whitespace-only -> the explicit stock URL, and a real
    request is addressed to api.openai.com.
  * a valid http(s) URL with a host (scheme matched case-insensitively,
    surrounding whitespace stripped) -> requests are addressed to THAT host.
  * any other non-blank value -> FAIL CLOSED: a real request raises
    openai.APIConnectionError and nothing reaches api.openai.com or the
    intended gateway, and one ERROR line names OPENAI_BASE_URL with the value
    redacted to its length and first 8 characters. With no http(s) scheme the
    failure comes before any DNS lookup; with an http(s) scheme but no host
    (``https://``, ``https:/gw.test/v1``) httpx resolves an EMPTY host once and
    fails there (EMPTY_HOST below pins exactly that).
  * describe_provider() never echoes credentials or a malformed value.

The DESTINATION tests drive a real openai.AsyncOpenAI request while the autouse
``net`` guard blocks every non-loopback getaddrinfo/connect, then read which
host the SDK tried to resolve. Any blocked attempt a test does not explicitly
take fails that test at teardown, so nothing in this file can reach the network.

Names that do not exist on the pre-fix module (STOCK_OPENAI_BASE_URL,
is_custom_provider) are resolved with getattr fallbacks, so this file also runs
against origin/main's llm_provider.py and fails there on the bug, not on
ImportError.
"""
import asyncio
import errno
import ipaddress
import logging
import socket

import pytest

from app.services import llm_provider as llm

ENV = "OPENAI_BASE_URL"
STOCK = getattr(llm, "STOCK_OPENAI_BASE_URL", "https://api.openai.com/v1")
STOCK_HOST = "api.openai.com"

# Non-blank values that are not http(s) URLs. The last one is the most likely
# real typo: a gateway URL with its scheme left off.
MALFORMED = [
    "not-a-url",
    "//proto",
    "junk value",
    "ftp://x",
    "api.gateway.test/v1",
    "  api.gateway.test/v1  ",
]

# Non-blank values that carry an http(s) scheme but no host: bare schemes and
# scheme typos with one slash, none, or backslashes. httpx parses these as
# http(s) with an EMPTY host, so the request dies on a resolution attempt for
# "" rather than on UnsupportedProtocol. They are still malformed: no host,
# ERROR line, never stock OpenAI.
EMPTY_HOST = [
    "https://",
    "http://",
    "https:/gw.test/v1",
    "HTTPS:/gw.test/v1",
    "http:gw.test/v1",
    "https:\\\\gw.test\\v1",
]


def _is_custom_provider():
    fn = getattr(llm, "is_custom_provider", None)
    if fn is not None:
        return fn()
    # Pre-fix module: "custom" meant "provider_base_url() returned a value".
    return llm.provider_base_url() is not None


# ------------------------------------------------------------ network guard

_PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
               "http_proxy", "https_proxy", "all_proxy")


def _norm_host(host):
    if isinstance(host, (bytes, bytearray)):
        host = bytes(host).decode("ascii", "replace")
    return str(host or "").strip("[]").lower()


def _is_loopback(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class _NetGuard:
    """Every blocked network attempt, as (call, host)."""

    def __init__(self):
        self.attempts = []

    def take_hosts(self):
        """The hosts attempted so far, clearing the record."""
        taken, self.attempts = self.attempts, []
        return [host for _, host in taken]


@pytest.fixture(autouse=True)
def net(monkeypatch):
    """Block every non-loopback getaddrinfo/connect (loopback stays open: the
    Windows event loop builds its self-pipe from a loopback socket pair).
    Proxies are disabled so an attempt names the real destination."""
    guard = _NetGuard()
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guarded_getaddrinfo(host, *args, **kwargs):
        name = _norm_host(host)
        if _is_loopback(name):
            return real_getaddrinfo(host, *args, **kwargs)
        guard.attempts.append(("getaddrinfo", name))
        raise socket.gaierror(socket.EAI_NONAME, "network blocked by the test guard")

    def _blocked(address):
        if not isinstance(address, tuple) or not address:
            return False  # an AF_UNIX path is local by definition
        name = _norm_host(address[0])
        if _is_loopback(name):
            return False
        guard.attempts.append(("connect", name))
        return True

    def guarded_connect(self, address):
        if _blocked(address):
            raise ConnectionRefusedError(errno.ECONNREFUSED, "network blocked by the test guard")
        return real_connect(self, address)

    def guarded_connect_ex(self, address):
        if _blocked(address):
            return errno.ECONNREFUSED
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    for var in _PROXY_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "*")
    yield guard
    assert guard.attempts == [], f"unexpected network attempts: {guard.attempts}"


@pytest.fixture
def llm_log():
    """Every record the provider module's logger emits during the test."""
    records = []

    class _Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _Capture(level=logging.DEBUG)
    logger = logging.getLogger(llm.__name__)
    saved = (logger.level, logger.disabled)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.disabled = False  # a dictConfig elsewhere in the suite may disable it
    try:
        yield records
    finally:
        logger.removeHandler(handler)
        logger.level, logger.disabled = saved


def _new_client():
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key="sk-test-dummy", base_url=llm.provider_base_url(),
                       max_retries=0, timeout=5.0)


def _send_one_request(client):
    """Make ONE real request with ``client`` and return what it raised."""
    async def go():
        try:
            await client.models.list()
        except Exception as exc:  # the exception IS the result here
            return exc
        finally:
            await client.close()
        return None
    return asyncio.run(go())


def _chain(exc):
    names = []
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        names.append(type(exc).__name__)
        exc = exc.__cause__ or exc.__context__
    return names


# --------------------------------------------------- destination: unset/blank

@pytest.mark.parametrize("value", [None, "", "   ", "\t", "\n"])
def test_unset_or_blank_requests_go_to_stock_openai(monkeypatch, net, value):
    if value is None:
        monkeypatch.delenv(ENV, raising=False)
    else:
        monkeypatch.setenv(ENV, value)
    client = _new_client()
    assert str(client.base_url) == "https://api.openai.com/v1/"
    _send_one_request(client)
    assert set(net.take_hosts()) == {STOCK_HOST}


# ------------------------------------------------ destination: valid custom

@pytest.mark.parametrize("url, host", [
    ("https://gateway.test/v1", "gateway.test"),
    ("  https://gateway.test/v1  ", "gateway.test"),
    ("http://gateway.test:4000/v1", "gateway.test"),
    ("HTTPS://UPPER.test/v1", "upper.test"),
    ("Https://mixed.test/v1", "mixed.test"),
])
def test_valid_url_is_the_request_destination(monkeypatch, net, url, host):
    import openai
    monkeypatch.setenv(ENV, url)
    exc = _send_one_request(_new_client())
    assert isinstance(exc, openai.APIConnectionError), repr(exc)  # the guard refused DNS
    assert set(net.take_hosts()) == {host}


def test_scheme_is_lower_cased_host_and_path_kept(monkeypatch):
    monkeypatch.setenv(ENV, "HTTPS://UPPER.test/V1")
    assert llm.provider_base_url() == "https://UPPER.test/V1"


# ------------------------------------------ destination: malformed = CLOSED

@pytest.mark.parametrize("bad", MALFORMED)
def test_malformed_value_fails_closed_at_request_time(monkeypatch, net, bad):
    """The request fails before any DNS lookup: it reaches neither the bogus
    value nor api.openai.com (the fail-OPEN this PR's first cut had)."""
    import openai
    monkeypatch.setenv(ENV, bad)
    exc = _send_one_request(_new_client())
    assert isinstance(exc, openai.APIConnectionError), repr(exc)
    assert "UnsupportedProtocol" in _chain(exc), _chain(exc)
    assert net.take_hosts() == []


@pytest.mark.parametrize("bad", ["api.gateway.test/v1", "not-a-url"])
def test_real_factories_fail_closed_on_a_malformed_value(monkeypatch, net, bad):
    """Every AsyncOpenAI factory the app uses, not just a hand-built client."""
    import openai
    import app.services.extraction_service as esvc
    import app.services.openai_service as osvc
    import app.services.url_extraction_service as usvc

    monkeypatch.setenv(ENV, bad)
    monkeypatch.setattr(osvc, "_client_cache", {}, raising=False)
    monkeypatch.setattr(esvc, "_client", None, raising=False)
    monkeypatch.setattr(usvc, "_client", None, raising=False)
    clients = [osvc.get_client(use_shared_project=True)]
    monkeypatch.setattr(osvc, "_client_cache", {}, raising=False)
    clients += [osvc.get_client(use_shared_project=False), esvc.get_client(), usvc.get_client()]

    for client in clients:
        exc = _send_one_request(client.with_options(max_retries=0, timeout=5.0))
        assert isinstance(exc, openai.APIConnectionError), repr(exc)
    assert net.take_hosts() == []


@pytest.mark.parametrize("bad", MALFORMED)
def test_malformed_value_is_returned_unchanged(monkeypatch, bad):
    monkeypatch.setenv(ENV, bad)
    assert llm.provider_base_url() == bad.strip()


@pytest.mark.parametrize("bad", EMPTY_HOST)
def test_empty_host_value_never_reaches_a_real_host(monkeypatch, net, bad):
    """An http(s) scheme with no host fails at request time. At most the empty
    host is resolved (once, measured on httpx 0.28.1); api.openai.com and the
    gw.test the typo meant are never attempted."""
    import openai
    monkeypatch.setenv(ENV, bad)
    exc = _send_one_request(_new_client())
    assert isinstance(exc, openai.APIConnectionError), repr(exc)
    assert set(net.take_hosts()) <= {""}


def test_unparseable_authority_never_reaches_a_real_host(monkeypatch, net):
    """urlsplit cannot parse an unclosed IPv6 bracket; httpx percent-encodes it
    and resolves the mangled name '%5bgw.test' (measured on httpx 0.28.1)."""
    import openai
    monkeypatch.setenv(ENV, "https://[gw.test/v1")
    exc = _send_one_request(_new_client())
    assert isinstance(exc, openai.APIConnectionError), repr(exc)
    hosts = set(net.take_hosts())
    assert STOCK_HOST not in hosts and "gw.test" not in hosts, hosts


@pytest.mark.parametrize("bad", EMPTY_HOST + ["https://[gw.test/v1"])
def test_empty_host_value_is_treated_as_malformed(monkeypatch, llm_log, bad):
    """Also covers an http(s) value urlsplit cannot parse at all (an unclosed
    IPv6 bracket), which must not raise out of provider_base_url()."""
    monkeypatch.setenv(ENV, bad)
    assert llm.provider_base_url() == bad
    assert [r.levelno for r in llm_log] == [logging.ERROR]
    assert ENV in llm_log[0].getMessage()
    assert llm.describe_provider() == "misconfigured:OPENAI_BASE_URL"
    assert _is_custom_provider() is False


# ------------------------------------------------------------- error line

SECRET_BAD = "user:sk-SECRET-TAIL@gw.test/v1"  # no scheme, carries a credential


def test_malformed_value_logs_one_redacted_error(monkeypatch, llm_log):
    monkeypatch.setenv(ENV, SECRET_BAD)
    llm.provider_base_url()
    assert [r.levelno for r in llm_log] == [logging.ERROR]
    msg = llm_log[0].getMessage()
    assert ENV in msg
    assert f"len={len(SECRET_BAD)}" in msg
    assert repr(SECRET_BAD[:8]) in msg
    assert "SECRET-TAIL" not in msg


@pytest.mark.parametrize("call", ["provider_base_url", "describe_provider", "is_custom_provider"])
def test_one_error_line_per_call(monkeypatch, llm_log, call):
    monkeypatch.setenv(ENV, "not-a-url")
    fn = getattr(llm, call, None) or _is_custom_provider
    fn()
    assert [r.levelno for r in llm_log] == [logging.ERROR]


@pytest.mark.parametrize("value", [None, "", "https://gateway.test/v1", "HTTPS://UPPER.test/v1"])
def test_no_log_line_for_unset_or_valid(monkeypatch, llm_log, value):
    if value is None:
        monkeypatch.delenv(ENV, raising=False)
    else:
        monkeypatch.setenv(ENV, value)
    llm.provider_base_url()
    llm.describe_provider()
    assert llm_log == []


# ------------------------------------------------------------------ labels

def test_unset_is_labelled_openai(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    assert llm.provider_base_url() == STOCK
    assert _is_custom_provider() is False
    assert llm.describe_provider() == "openai"


@pytest.mark.parametrize("stock", [
    "https://api.openai.com/v1",
    "https://api.openai.com/v1/",
    "HTTPS://API.OPENAI.COM/v1",
    "  https://api.openai.com/v1  ",
])
def test_explicit_stock_url_is_labelled_openai(monkeypatch, stock):
    monkeypatch.setenv(ENV, stock)
    assert llm.describe_provider() == "openai"
    assert _is_custom_provider() is False


@pytest.mark.parametrize("url", [
    "https://api.openai.com/v1?x=1",
    "https://api.openai.com/v1#frag",
])
def test_stock_host_with_query_or_fragment_is_not_labelled_stock(monkeypatch, url):
    """A query string or fragment changes what the SDK sends, so it is not the
    stock endpoint even on api.openai.com/v1."""
    monkeypatch.setenv(ENV, url)
    assert llm.describe_provider() == "openai-compatible@https://api.openai.com/v1"
    assert _is_custom_provider() is True


@pytest.mark.parametrize("url", [
    "https://api.groq.com/openai/v1",
    "http://localhost:4000",
    "https://gateway.ai.cloudflare.com/v1/acct/app/openai",
])
def test_valid_url_passes_through(monkeypatch, url):
    """Regression guard: origin/main already passes this. It is not evidence
    for the fix; it stops the fix from breaking a valid custom URL."""
    monkeypatch.setenv(ENV, url)
    assert llm.provider_base_url() == url
    assert _is_custom_provider() is True
    assert llm.describe_provider() == f"openai-compatible@{url}"


def test_surrounding_whitespace_is_stripped(monkeypatch):
    monkeypatch.setenv(ENV, "  https://example.test/v1  ")
    assert llm.provider_base_url() == "https://example.test/v1"


@pytest.mark.parametrize("url", [
    "https://user:sk-pw@gw.test/v1",
    "https://gw.test/v1?api-key=sk-query-secret",
    "https://user:sk-pw@gw.test/v1?api-key=sk-query-secret#frag",
    "https://user:sk-p@ss@gw.test/v1",
])
def test_describe_never_includes_credentials(monkeypatch, url):
    monkeypatch.setenv(ENV, url)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-do-not-log")
    label = llm.describe_provider()
    assert label == "openai-compatible@https://gw.test/v1"
    assert "sk-" not in label


@pytest.mark.parametrize("url", [
    "https://user:sk-pa?ss@gw.test/v1",
    "https://user:sk-pa#ss@gw.test/v1",
    "https://user:sk-pa/ss@gw.test/v1",
])
def test_describe_redacts_a_password_the_parser_splits(monkeypatch, url):
    """An unencoded '?', '#' or '/' in the password makes urlsplit cut the
    authority early, so part of the password lands in the host and the rest in
    the query, fragment or path. The label must then show no location at all."""
    monkeypatch.setenv(ENV, url)
    assert llm.describe_provider() == "openai-compatible@https://<redacted>"


@pytest.mark.parametrize("bad", MALFORMED)
def test_malformed_value_is_labelled_misconfigured_not_openai(monkeypatch, bad):
    monkeypatch.setenv(ENV, bad)
    assert llm.describe_provider() == "misconfigured:OPENAI_BASE_URL"
    assert _is_custom_provider() is False


def test_read_fresh_every_call(monkeypatch):
    """No module-level cache: a Railway change takes effect on the next client
    construction, with no redeploy."""
    monkeypatch.delenv(ENV, raising=False)
    assert llm.provider_base_url() == STOCK
    monkeypatch.setenv(ENV, "https://a.test/v1")
    assert llm.provider_base_url() == "https://a.test/v1"
    monkeypatch.setenv(ENV, "https://b.test/v1")
    assert llm.provider_base_url() == "https://b.test/v1"


# ------------------------------------------- the factories actually use it

def test_all_client_factories_pass_base_url(monkeypatch):
    """Every AsyncOpenAI construction in the app must honour the setting:
    a factory that forgets it would silently stay on stock OpenAI.

    Regression guard: origin/main already passes this. It is not evidence for
    the fix."""
    import app.services.openai_service as osvc
    import app.services.extraction_service as esvc
    import app.services.url_extraction_service as usvc

    seen = []

    class _Spy:
        def __init__(self, *a, **kw):
            seen.append(kw.get("base_url", "MISSING"))

    monkeypatch.setenv(ENV, "https://spy.test/v1")
    for mod in (osvc, esvc, usvc):
        monkeypatch.setattr(mod, "AsyncOpenAI", _Spy)
    monkeypatch.setattr(osvc, "_client_cache", {}, raising=False)
    monkeypatch.setattr(esvc, "_client", None, raising=False)
    monkeypatch.setattr(usvc, "_client", None, raising=False)

    osvc.get_client(use_shared_project=True)
    monkeypatch.setattr(osvc, "_client_cache", {}, raising=False)
    osvc.get_client(use_shared_project=False)
    esvc.get_client()
    usvc.get_client()

    assert len(seen) == 4, seen
    assert all(v == "https://spy.test/v1" for v in seen), seen


def test_factories_pass_explicit_stock_url_when_unset(monkeypatch):
    """Unset hands the SDK an EXPLICIT stock url, never None: None would let
    the SDK re-read OPENAI_BASE_URL itself, behind this module's back."""
    import app.services.extraction_service as esvc
    seen = []

    class _Spy:
        def __init__(self, *a, **kw):
            seen.append(kw.get("base_url", "MISSING"))

    monkeypatch.delenv(ENV, raising=False)
    monkeypatch.setattr(esvc, "AsyncOpenAI", _Spy)
    monkeypatch.setattr(esvc, "_client", None, raising=False)
    esvc.get_client()
    assert seen == [STOCK]
