"""M13-02 — proxy-aware rate-limit key + audit ip_address, behind the
default-OFF ENABLE_PROXY_AWARE_RATELIMIT flag.

Baseline: get_remote_address returns the Railway edge-proxy TCP peer, so every
caller hashes to one limiter key and every audit row records the proxy IP. This
adds a leftmost-X-Forwarded-For key_func (validated) shared with the audit
ip_address helper. Flag-OFF must be byte-identical to today.
"""
import os

import pytest
from starlette.requests import Request


def _req(xff=None, client_host="10.0.0.1"):
    headers = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/text/compare",
        "headers": headers,
        "query_string": b"",
        "client": (client_host, 55555) if client_host else None,
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def _clear_flag(monkeypatch):
    monkeypatch.delenv("ENABLE_PROXY_AWARE_RATELIMIT", raising=False)
    yield


def test_flag_off_is_todays_remote_address(monkeypatch):
    """Flag OFF: the key is the TCP peer, exactly as get_remote_address returns
    today — two different XFF values but the same peer collapse to one key."""
    from slowapi.util import get_remote_address
    from app.middleware.rate_limiter import _rate_limit_key

    a = _req(xff="1.1.1.1", client_host="10.0.0.9")
    b = _req(xff="2.2.2.2", client_host="10.0.0.9")
    assert _rate_limit_key(a) == get_remote_address(a) == "10.0.0.9"
    assert _rate_limit_key(a) == _rate_limit_key(b)  # one shared key today


def test_flag_on_two_xff_two_keys(monkeypatch):
    """Flag ON: two different leftmost X-Forwarded-For values → two keys."""
    monkeypatch.setenv("ENABLE_PROXY_AWARE_RATELIMIT", "true")
    from app.middleware.rate_limiter import _rate_limit_key

    a = _req(xff="1.1.1.1, 172.16.0.1", client_host="10.0.0.9")
    b = _req(xff="2.2.2.2, 172.16.0.1", client_host="10.0.0.9")
    assert _rate_limit_key(a) == "1.1.1.1"
    assert _rate_limit_key(b) == "2.2.2.2"
    assert _rate_limit_key(a) != _rate_limit_key(b)


def test_flag_on_invalid_xff_falls_back(monkeypatch):
    """Flag ON but a garbage / missing XFF → fall back to the TCP peer."""
    monkeypatch.setenv("ENABLE_PROXY_AWARE_RATELIMIT", "true")
    from app.middleware.rate_limiter import _rate_limit_key

    assert _rate_limit_key(_req(xff="not-an-ip", client_host="10.0.0.9")) == "10.0.0.9"
    assert _rate_limit_key(_req(xff=None, client_host="10.0.0.9")) == "10.0.0.9"


def test_audit_ip_flag_off_matches_today(monkeypatch):
    """audit_client_ip flag OFF == `request.client.host if request.client else None`."""
    from app.middleware.rate_limiter import audit_client_ip

    assert audit_client_ip(_req(xff="9.9.9.9", client_host="10.0.0.9")) == "10.0.0.9"
    assert audit_client_ip(_req(xff="9.9.9.9", client_host=None)) is None


def test_audit_ip_flag_on_reads_xff(monkeypatch):
    """audit_client_ip flag ON reads the same validated leftmost XFF the
    limiter key uses (shared helper)."""
    monkeypatch.setenv("ENABLE_PROXY_AWARE_RATELIMIT", "true")
    from app.middleware.rate_limiter import audit_client_ip, _rate_limit_key

    r = _req(xff="203.0.113.7, 172.16.0.1", client_host="10.0.0.9")
    assert audit_client_ip(r) == "203.0.113.7"
    assert audit_client_ip(r) == _rate_limit_key(r)  # one shared helper


def test_limiter_uses_proxy_aware_key_func():
    """The Limiter is wired to the proxy-aware key_func, not raw
    get_remote_address."""
    from app.middleware.rate_limiter import limiter, _rate_limit_key

    assert limiter._key_func is _rate_limit_key
