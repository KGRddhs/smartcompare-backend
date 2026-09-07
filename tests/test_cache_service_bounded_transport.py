"""W0-3 red tests - Upstash bounded transport + no sleep-retry.

Finding: LS-REQUEST-PATH-BLOCKING-03 == LS-CACHE-REDIS-01 == LS-CONCURRENCY-LIMITS-04.

Today ``app/services/cache_service.py:27-40`` builds ``upstash_redis.Redis(url=..., token=...)``
at import time with library defaults. Verified against the PINNED wheel
``upstash-redis==1.7.0`` (downloaded to ``.qa-w0/wheels`` and read; the locally installed
1.6.0 is OFF-LOCK but byte-identical in the two shapes these tests touch):

  * ``upstash_redis/http.py`` ``SyncHttpClient.__init__`` -> ``self._client = httpx.Client(timeout=None)``
  * ``upstash_redis/client.py`` ``Redis.__init__`` -> ``rest_retries: int = 1``,
    ``rest_retry_interval: float = 3``, and the retry loop calls ``time.sleep(self._retry_interval)``.

So a stalled Upstash REST endpoint parks a request-path thread with NO ceiling, and a failed
attempt costs an extra 3 s of ``time.sleep`` before the second attempt.

The flag ``ENABLE_UPSTASH_BOUNDED_TRANSPORT`` (default OFF) is expected to bound both.
The client is constructed by module-level init code, so the *existing* init path is
"import the module with this environment" - these tests drive it via ``importlib.reload``,
which re-runs exactly the code a fresh worker process runs at boot.
"""

import importlib
import os
import time

import httpx
import pytest

CACHE_MODULE = "app.services.cache_service"
FLAG = "ENABLE_UPSTASH_BOUNDED_TRANSPORT"

STUB_REST_URL = "https://stub-upstash.invalid"
STUB_REDIS_URL = "redis://127.0.0.1:6379"
STUB_TOKEN = "stub-token-not-a-credential"

_ENV_KEYS = (
    FLAG,
    "UPSTASH_REDIS_URL",
    "UPSTASH_REDIS_TOKEN",
    "UPSTASH_TIMEOUT_SECONDS",
    "UPSTASH_CONNECT_TIMEOUT_SECONDS",
)

# Bounds the unit is specified to enforce when the flag is ON.
EXPECTED_READ_BOUND = 2.0
EXPECTED_CONNECT_BOUND = 1.0


@pytest.fixture(autouse=True)
def _cache_service_env_sandbox():
    """Save/restore the env keys this file drives, and restore the module afterwards.

    ``cache_service`` builds its client at import time, so every test here reloads the
    module. The teardown reloads it once more under the ORIGINAL environment so no other
    test file inherits a stubbed ``redis_client``.
    """
    saved = {key: os.environ.get(key) for key in _ENV_KEYS}
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        importlib.reload(importlib.import_module(CACHE_MODULE))


def _reload_cache_service(**env):
    """Re-run cache_service's own init path under ``env``. Returns the reloaded module."""
    for key in _ENV_KEYS:
        os.environ.pop(key, None)
    for key, value in env.items():
        os.environ[key] = value
    return importlib.reload(importlib.import_module(CACHE_MODULE))


def _http_layer(module):
    """The upstash SyncHttpClient behind the module's client (pinned-wheel attribute names)."""
    client = module.redis_client
    assert client is not None, (
        "cache_service.redis_client is None - the stub URL/token did not build a client, "
        "so this test never reached the behaviour under test."
    )
    http = getattr(client, "_http", None)
    assert http is not None, (
        "upstash Redis client has no ._http - the pinned upstash-redis==1.7.0 shape changed; "
        "re-read the wheel before trusting this suite."
    )
    return http


class _StallTransport(httpx.BaseTransport):
    """A transport that stalls like a black-holed Upstash endpoint.

    It honours the per-request read timeout the way ``httpx.HTTPTransport`` does: it sleeps at
    most the read budget and then raises ``ReadTimeout``. With ``timeout=None`` (today's client)
    there is no budget, so it sleeps the full stall and only then raises - which is exactly the
    unbounded park this unit exists to remove.
    """

    def __init__(self, stall_seconds: float):
        self.stall_seconds = stall_seconds
        self.attempts = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.attempts += 1
        budget = (request.extensions.get("timeout") or {}).get("read")
        slept = self.stall_seconds if budget is None else min(float(budget), self.stall_seconds)
        time.sleep(slept)
        raise httpx.ReadTimeout("stalled upstash endpoint", request=request)


def test_upstash_client_has_bounded_timeout_and_no_sleep_retry():
    """RED today: httpx.Client(timeout=None) plus rest_retries=1 / rest_retry_interval=3."""
    module = _reload_cache_service(
        **{
            FLAG: "true",
            "UPSTASH_REDIS_URL": STUB_REST_URL,
            "UPSTASH_REDIS_TOKEN": STUB_TOKEN,
        }
    )
    http = _http_layer(module)
    timeout = http._client.timeout

    assert timeout.read is not None and timeout.read <= EXPECTED_READ_BOUND, (
        "Upstash REST read timeout is {!r}; expected a bound <= {}s under {}.".format(
            timeout.read, EXPECTED_READ_BOUND, FLAG
        )
    )
    assert timeout.connect is not None and timeout.connect <= EXPECTED_CONNECT_BOUND, (
        "Upstash REST connect timeout is {!r}; expected a bound <= {}s under {}.".format(
            timeout.connect, EXPECTED_CONNECT_BOUND, FLAG
        )
    )
    assert http._retries == 0, (
        "Upstash rest_retries is {!r}; expected 0 under {} so no time.sleep({!r}) can run "
        "on the request path.".format(http._retries, FLAG, http._retry_interval)
    )


def test_stalled_transport_returns_none_within_bound():
    """RED today: a stalled endpoint parks the caller for stall + retry_interval + stall."""
    module = _reload_cache_service(
        **{
            FLAG: "true",
            "UPSTASH_REDIS_URL": STUB_REST_URL,
            "UPSTASH_REDIS_TOKEN": STUB_TOKEN,
        }
    )
    http = _http_layer(module)

    transport = _StallTransport(stall_seconds=5.0)
    # Keep whatever timeout the init path chose; swap only the wire.
    http._client = httpx.Client(timeout=http._client.timeout, transport=transport)

    started = time.monotonic()
    result = module._redis_get("w0-3-probe-key")
    elapsed = time.monotonic() - started

    assert result is None, (
        "_redis_get must stay fail-open on a stalled endpoint; got {!r}.".format(result)
    )
    assert elapsed <= 2.5, (
        "_redis_get blocked {:.2f}s on a stalled Upstash endpoint ({} HTTP attempt(s)); "
        "expected <= 2.5s under {}.".format(elapsed, transport.attempts, FLAG)
    )


def test_redis_url_fallback_gets_socket_timeouts():
    """RED today: the redis:// branch passes no socket_timeout / socket_connect_timeout."""
    module = _reload_cache_service(
        **{
            FLAG: "true",
            "UPSTASH_REDIS_URL": STUB_REDIS_URL,
            "UPSTASH_REDIS_TOKEN": STUB_TOKEN,
        }
    )
    client = module.redis_client
    assert client is not None, "redis:// fallback did not build a client."

    kwargs = client.connection_pool.connection_kwargs
    socket_timeout = kwargs.get("socket_timeout")
    socket_connect_timeout = kwargs.get("socket_connect_timeout")

    assert socket_timeout is not None and socket_timeout <= EXPECTED_READ_BOUND, (
        "redis:// fallback socket_timeout is {!r}; expected a bound <= {}s under {}.".format(
            socket_timeout, EXPECTED_READ_BOUND, FLAG
        )
    )
    assert (
        socket_connect_timeout is not None
        and socket_connect_timeout <= EXPECTED_CONNECT_BOUND
    ), (
        "redis:// fallback socket_connect_timeout is {!r}; expected a bound <= {}s under "
        "{}.".format(socket_connect_timeout, EXPECTED_CONNECT_BOUND, FLAG)
    )


def test_flag_off_defaults_unchanged():
    """Flag-OFF pin (GREEN today by construction, and must stay green after the unit lands).

    This is the byte-identity half of the unit: with the flag unset the client must keep the
    pinned upstash-redis==1.7.0 defaults exactly.
    """
    module = _reload_cache_service(
        **{
            "UPSTASH_REDIS_URL": STUB_REST_URL,
            "UPSTASH_REDIS_TOKEN": STUB_TOKEN,
        }
    )
    assert os.environ.get(FLAG) is None, "the flag must be unset for the flag-OFF pin"

    http = _http_layer(module)
    assert http._client.timeout.read is None, (
        "flag OFF must keep httpx.Client(timeout=None); read timeout is {!r}.".format(
            http._client.timeout.read
        )
    )
    assert http._client.timeout.connect is None, (
        "flag OFF must keep httpx.Client(timeout=None); connect timeout is {!r}.".format(
            http._client.timeout.connect
        )
    )
    assert http._retries == 1, "flag OFF must keep rest_retries=1; got {!r}.".format(
        http._retries
    )
    assert http._retry_interval == 3, (
        "flag OFF must keep rest_retry_interval=3; got {!r}.".format(http._retry_interval)
    )
