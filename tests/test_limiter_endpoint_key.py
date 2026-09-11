"""W1-5 red tests -- a rate limit that path parameters cannot walk around.

Finding ``LS-RATELIMIT-KEY-01``. Flag ``ENABLE_LIMITER_ENDPOINT_KEY``, default OFF.

THE MECHANISM, MEASURED ON THE INSTALLED slowapi
------------------------------------------------
Installed here: ``slowapi==0.1.9`` (``importlib.metadata.version('slowapi')``).
``requirements.txt`` pins ``slowapi==0.1.10``. Every line number below was read
off the INSTALLED 0.1.9 wheel; the unit spec quotes 0.1.10's numbers, which sit
one line earlier. The BEHAVIOUR is identical in the two shapes these tests
touch, and no assertion in this file depends on a line number.

  * ``slowapi/extension.py:147`` -- ``key_style: Literal["endpoint", "url"] = "url"``
    (spec quotes ``:146``).
  * ``slowapi/extension.py:185``  -- ``self._key_style = key_style``. Read ONCE,
    at construction.
  * ``slowapi/extension.py:565`` -- ``_endpoint_key = endpoint_url if
    self._key_style == "url" else endpoint_func_name`` (spec quotes ``:564``),
    where ``endpoint_url = request["path"]`` (``:559``).
  * ``slowapi/extension.py:630`` -- ``self.__evaluate_limits(request,
    _endpoint_key, all_limits)`` (``:629`` is the comment line above it; the
    ruling quoted ``:629``), and ``:488`` ``limit_scope = lim.scope or
    endpoint``. So a limit registered with a FALSY scope (every
    ``@limiter.limit(...)`` in this repo registers ``scope == ''``) buckets on
    ``_endpoint_key``.

``app/middleware/rate_limiter.py`` constructs ``Limiter(key_func=...,
storage_uri=..., default_limits=[ANON_LIMIT])`` and passes no ``key_style``, so
the bucket today is ``(client IP, RESOLVED URL)``. ``/api/v1/share/abc`` and
``/api/v1/share/xyz`` are different URLs, so the ``30/minute`` on
``share_routes.py:53`` is 30 per TOKEN, not 30 per caller.

WHY A PRIVATE MODULE INSTANCE
-----------------------------
``key_style`` is read once, at ``Limiter`` construction, which happens at IMPORT
of ``app.middleware.rate_limiter``. So "construct the limiter under the flag" is
"execute that module body under the flag". These tests do exactly that with
``importlib.util.spec_from_file_location`` + ``module_from_spec`` under the REAL
dotted name -- the W0-3 pattern settled in
``tests/test_cache_service_bounded_transport.py``. NEVER ``importlib.reload`` of
the real module (a reload rebinds every function object while ``from ... import
x`` importers keep the original, which reddened an unrelated test in full-suite
order last week) and NEVER ``sys.modules`` surgery.

To make the REAL share route run against that private limiter, the loader
patches the ATTRIBUTE ``app.middleware.rate_limiter.limiter`` (monkeypatch,
auto-restored) and then executes a private instance of ``app.api.share_routes``,
whose ``from app.middleware.rate_limiter import limiter`` therefore binds the
private object. ``sys.modules`` is never written to.
"""

import importlib
import importlib.util
import os
from importlib.metadata import version

import pytest
import slowapi
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from app.middleware.error_handler import rate_limit_handler

# Import the real application ONCE, at module import, BEFORE any attribute
# patching. Every router module then binds the REAL limiter and registers its
# @limiter.limit decorators there. Without this the first
# `_exec_private("app.api.share_routes")` would perform the FIRST real import of
# that module while `rate_limiter.limiter` was patched, permanently binding a
# private limiter into sys.modules and registering the share limits on it
# instead of the real one -- measured: the blast-radius test passed alone and
# failed in file order.
import app.main  # noqa: E402,F401  (import-for-side-effect, order matters)

RATE_LIMITER_MODULE = "app.middleware.rate_limiter"
SHARE_ROUTES_MODULE = "app.api.share_routes"

FLAG = "ENABLE_LIMITER_ENDPOINT_KEY"

# Env names this file drives. ENABLE_PROXY_AWARE_RATELIMIT and
# ENABLE_DEFAULT_RATE_LIMITS are read by the same module body, so they are
# pinned OFF for every construction: the unit must be measured against the
# SHIPPED default configuration, not against a stray local .env.
_ENV_KEYS = (FLAG, "ENABLE_PROXY_AWARE_RATELIMIT", "ENABLE_DEFAULT_RATE_LIMITS")

# SPEC CORRECTION (appended section, 2026-09-08): the finding's "35 GETs to
# distinct share tokens" targets GET /api/v1/share/{token}, which is
# @limiter.limit("30/minute") at share_routes.py:53 -- so the 429 lands on the
# 31st request, not the 11th.
SHARE_GET_LIMIT = 30
SHARE_GET_PROBES = 35

# The exact constructor call today. Flag OFF must reproduce it argument for
# argument (spec: "With the flag OFF the Limiter is constructed exactly as
# today -- byte-identical").
TODAYS_LIMITER_KWARG_NAMES = {"key_func", "storage_uri", "default_limits"}


@pytest.fixture(autouse=True)
def _env_sandbox():
    """Save/restore only the env names this file drives."""
    saved = {key: os.environ.get(key) for key in _ENV_KEYS}
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _apply_env(flag_on):
    for key in _ENV_KEYS:
        os.environ.pop(key, None)
    if flag_on:
        os.environ[FLAG] = "true"


def _exec_private(dotted_name):
    """Execute ``dotted_name``'s module body in a PRIVATE instance and return it.

    The spec is given the REAL dotted name so ``logging.getLogger(__name__)``
    inside the module still resolves to the real logger; ``module_from_spec``
    never touches ``sys.modules``.
    """
    real = importlib.import_module(dotted_name)
    spec = importlib.util.spec_from_file_location(dotted_name, real.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _private_rate_limiter(flag_on, monkeypatch=None, recorder=None):
    """Construct ``rate_limiter`` under the flag, in a private module instance.

    When ``recorder`` is given, ``slowapi.Limiter`` is temporarily swapped for a
    factory that records the constructor call, so the flag-OFF byte-identity of
    the construction itself is testable.
    """
    _apply_env(flag_on)
    if recorder is None:
        return _exec_private(RATE_LIMITER_MODULE)

    real_limiter_cls = slowapi.Limiter

    def _recording_limiter(*args, **kwargs):
        recorder.append({"args": args, "kwargs": dict(kwargs)})
        return real_limiter_cls(*args, **kwargs)

    # Targeted swap/restore, NOT ``monkeypatch.undo()``: ``undo`` would also
    # revert every patch the CALLING test set before this helper ran.
    slowapi.Limiter = _recording_limiter
    try:
        return _exec_private(RATE_LIMITER_MODULE)
    finally:
        slowapi.Limiter = real_limiter_cls


def _share_client(monkeypatch, limiter_module):
    """A TestClient over the REAL share routes bound to ``limiter_module``'s Limiter.

    Also mounts one FIXED-PATH control route on the same Limiter, so a test can
    compare a parameterised route against a non-parameterised one under the
    identical limiter instance.
    """
    real_rate_limiter = importlib.import_module(RATE_LIMITER_MODULE)
    private_limiter = limiter_module.limiter

    # Attribute patch (NOT sys.modules): the private share_routes body does
    # `from app.middleware.rate_limiter import limiter`, which reads this
    # attribute off the module object.
    monkeypatch.setattr(real_rate_limiter, "limiter", private_limiter)
    share_module = _exec_private(SHARE_ROUTES_MODULE)

    async def _stub_get_shared_comparison(token):
        return {
            "query": "w1-5 probe",
            "product_names": ["a", "b"],
            "input_type": "text",
            "full_response": {},
            "created_at": "2026-09-08T00:00:00Z",
        }

    monkeypatch.setattr(
        share_module, "get_shared_comparison", _stub_get_shared_comparison
    )

    app = FastAPI()
    app.state.limiter = private_limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.include_router(share_module.router)

    @app.get("/api/v1/w15-control/fixed")
    @private_limiter.limit(f"{SHARE_GET_LIMIT}/minute")
    async def _w15_control_fixed(request: Request):  # pragma: no cover - trivial
        return {"success": True}

    return TestClient(app)


def _key_style_of(limiter):
    """slowapi's stored key style, with a legible message on version drift.

    Read off the INSTALLED slowapi (0.1.9 here; requirements.txt pins 0.1.10).
    The attribute name is not asserted anywhere else, so a rename on the pinned
    build fails here with an explanation instead of a bare AttributeError.
    """
    assert hasattr(limiter, "_key_style"), (
        "the installed slowapi's Limiter has no `_key_style` attribute -- "
        f"installed version is {version('slowapi')}, requirements.txt pins "
        "0.1.10. Re-read the wheel before trusting this file."
    )
    return limiter._key_style


def _share_token(i):
    """A distinct token matching share_routes' Path pattern ^[A-Za-z0-9_-]{18,30}$."""
    return f"w15share{i:02d}aaaaaaaa"


def _get_distinct_share_tokens(client, count=SHARE_GET_PROBES):
    return [
        client.get(f"/api/v1/share/{_share_token(i)}").status_code
        for i in range(count)
    ]


def _get_fixed_path(client, count=SHARE_GET_LIMIT + 1):
    return [client.get("/api/v1/w15-control/fixed").status_code for _ in range(count)]


# ===========================================================================
# 1. FLAG ON -- distinct path parameters must share ONE bucket per caller
# ===========================================================================
def test_flag_on_distinct_share_tokens_share_one_bucket(monkeypatch):
    """RED today: 35 GETs to 35 DISTINCT share tokens from ONE client all 200.

    Under the flag the limiter must key on the view function, so the 30/minute
    on ``share_routes.py:53`` becomes 30 per CALLER and the 31st request is a
    429 (spec correction: the 31st, not the 11th -- the GET is 30/min).
    """
    limiter_module = _private_rate_limiter(flag_on=True, monkeypatch=monkeypatch)
    client = _share_client(monkeypatch, limiter_module)

    statuses = _get_distinct_share_tokens(client)

    assert statuses[:SHARE_GET_LIMIT] == [200] * SHARE_GET_LIMIT, (
        "flag ON: the first 30 GETs are inside the 30/minute ceiling and must "
        f"all be 200; got {statuses!r}"
    )
    assert statuses[SHARE_GET_LIMIT] == 429, (
        "flag ON: 35 GETs to 35 DISTINCT share tokens from one client must "
        "share ONE bucket, so request #31 must be 429. Got "
        f"{statuses[SHARE_GET_LIMIT]} -- statuses={statuses!r}. "
        "This is the path-parameter escape the unit removes."
    )


# ===========================================================================
# 2. FLAG OFF -- today's behaviour, pinned as the flag-OFF contract
# ===========================================================================
def test_flag_off_distinct_share_tokens_are_thirty_five_separate_buckets(monkeypatch):
    """PIN (green today AND after the fix): flag OFF is byte-identical behaviour.

    35 GETs to 35 distinct tokens = 35 distinct URL buckets = 35 x 200. This is
    what makes the byte-identity claim testable, and it is the mutation check
    for hard-coding ``key_style="endpoint"``.
    """
    limiter_module = _private_rate_limiter(flag_on=False, monkeypatch=monkeypatch)
    client = _share_client(monkeypatch, limiter_module)

    statuses = _get_distinct_share_tokens(client)

    assert statuses == [200] * SHARE_GET_PROBES, (
        "flag OFF must reproduce today's url-keyed bucketing exactly: 35 "
        f"distinct tokens -> 35 x 200. Got {statuses!r}"
    )


# ===========================================================================
# 3. FLAG ON -- a non-parameterised route's bucketing is unchanged
# ===========================================================================
@pytest.mark.parametrize("flag_on", [False, True], ids=["flag_off", "flag_on"])
def test_fixed_path_route_bucketing_is_unchanged_by_the_flag(monkeypatch, flag_on):
    """PIN: a route with no path parameter keeps ONE bucket per route per IP.

    For a fixed URL, ``request["path"]`` is constant, so url-keying and
    endpoint-keying agree. The flag must therefore move the 429 boundary by
    zero requests on such a route.
    """
    limiter_module = _private_rate_limiter(flag_on=flag_on, monkeypatch=monkeypatch)
    client = _share_client(monkeypatch, limiter_module)

    statuses = _get_fixed_path(client)

    assert statuses == [200] * SHARE_GET_LIMIT + [429], (
        f"flag {'ON' if flag_on else 'OFF'}: a fixed-path route must 429 on "
        f"request #{SHARE_GET_LIMIT + 1} and not before; got {statuses!r}"
    )


def test_fixed_path_route_is_status_for_status_identical_across_the_flag(monkeypatch):
    """PIN: the same non-parameterised route, both flag states, same status list."""
    off_module = _private_rate_limiter(flag_on=False, monkeypatch=monkeypatch)
    off_statuses = _get_fixed_path(_share_client(monkeypatch, off_module))

    on_module = _private_rate_limiter(flag_on=True, monkeypatch=monkeypatch)
    on_statuses = _get_fixed_path(_share_client(monkeypatch, on_module))

    assert off_statuses == on_statuses, (
        "the flag must not change bucketing on a route without a path "
        f"parameter; flag OFF={off_statuses!r} flag ON={on_statuses!r}"
    )


# ===========================================================================
# 4. key_style is read at CONSTRUCTION only -- a Railway flip needs a restart
# ===========================================================================
def test_env_flip_after_construction_cannot_loosen_the_key(monkeypatch):
    """PIN: built with the flag OFF, then the env goes ON -- nothing changes.

    Documents the restart requirement as a test rather than a sentence. This is
    the W0-3 Upstash class of flag, not the per-call ``os.getenv`` class.
    """
    limiter_module = _private_rate_limiter(flag_on=False, monkeypatch=monkeypatch)
    client = _share_client(monkeypatch, limiter_module)

    os.environ[FLAG] = "true"  # a Railway flip, AFTER construction

    assert _key_style_of(limiter_module.limiter) == "url", (
        "the limiter was constructed with the flag OFF; flipping the env "
        "afterwards must not change the already-read key_style, got "
        f"{_key_style_of(limiter_module.limiter)!r}"
    )
    statuses = _get_distinct_share_tokens(client)
    assert statuses == [200] * SHARE_GET_PROBES, (
        "a post-construction env flip must not start bucketing by endpoint; "
        f"got {statuses!r}"
    )


def test_env_flip_after_construction_cannot_loosen_an_endpoint_keyed_limiter(
    monkeypatch,
):
    """RED today: built with the flag ON, then the env goes OFF -- still endpoint-keyed.

    The mirror half of the restart requirement. It is red today only because
    the flag does not exist yet, so construction under it yields ``"url"``.
    """
    limiter_module = _private_rate_limiter(flag_on=True, monkeypatch=monkeypatch)
    client = _share_client(monkeypatch, limiter_module)

    os.environ.pop(FLAG, None)  # a Railway flip back, AFTER construction

    assert _key_style_of(limiter_module.limiter) == "endpoint", (
        "constructed with ENABLE_LIMITER_ENDPOINT_KEY ON, the Limiter must "
        "carry slowapi's endpoint key style; got "
        f"{_key_style_of(limiter_module.limiter)!r}"
    )
    statuses = _get_distinct_share_tokens(client)
    assert statuses[SHARE_GET_LIMIT] == 429, (
        "a post-construction env flip back to OFF must not loosen the already "
        f"constructed limiter; got statuses={statuses!r}"
    )


# ===========================================================================
# 5/6. The construction call itself
# ===========================================================================
def test_flag_off_constructs_the_limiter_with_exactly_todays_arguments(monkeypatch):
    """PIN: flag OFF passes NO ``key_style`` and nothing else new.

    Strict reading of the spec's "with the flag OFF the Limiter is constructed
    exactly as today -- byte-identical". Passing ``key_style="url"`` explicitly
    would be behaviourally equal but is NOT today's call, so it fails here on
    purpose; relax this pin only with the reviewer's agreement.
    """
    recorder = []
    limiter_module = _private_rate_limiter(
        flag_on=False, monkeypatch=monkeypatch, recorder=recorder
    )

    assert len(recorder) == 1, (
        f"expected exactly one Limiter construction, recorded {len(recorder)}"
    )
    call = recorder[0]
    assert call["args"] == (), (
        f"today's call is keyword-only; got positional args {call['args']!r}"
    )
    assert set(call["kwargs"]) == TODAYS_LIMITER_KWARG_NAMES, (
        "flag OFF must construct the Limiter with exactly today's arguments "
        f"{sorted(TODAYS_LIMITER_KWARG_NAMES)}; got {sorted(call['kwargs'])}"
    )
    assert _key_style_of(limiter_module.limiter) == "url", (
        "flag OFF must leave slowapi's default url key style in place; got "
        f"{_key_style_of(limiter_module.limiter)!r}"
    )
    # The VALUES, not just the kwarg names: a regression that keeps the three
    # names but changes what they carry must fail here, not in a sibling file.
    kwargs = call["kwargs"]
    assert kwargs["key_func"] is limiter_module._rate_limit_key, (
        "flag OFF must key on the module's own _rate_limit_key; got "
        f"{kwargs['key_func']!r}"
    )
    assert kwargs["storage_uri"] == limiter_module._get_storage_uri(), (
        "flag OFF must pass the storage URI that _get_storage_uri() resolves; got "
        f"{kwargs['storage_uri']!r}"
    )
    assert kwargs["default_limits"] == [limiter_module.ANON_LIMIT], (
        "flag OFF must pass today's single ANON_LIMIT default; got "
        f"{kwargs['default_limits']!r}"
    )


def test_flag_on_constructs_the_limiter_with_endpoint_key_style(monkeypatch):
    """RED today: the flag must reach slowapi as ``key_style="endpoint"``."""
    recorder = []
    limiter_module = _private_rate_limiter(
        flag_on=True, monkeypatch=monkeypatch, recorder=recorder
    )

    assert len(recorder) == 1, (
        f"expected exactly one Limiter construction, recorded {len(recorder)}"
    )
    assert recorder[0]["kwargs"].get("key_style") == "endpoint", (
        "flag ON must construct the Limiter with key_style='endpoint' -- "
        "slowapi already implements the bucketing, the unit only has to ask "
        f"for it; recorded kwargs={sorted(recorder[0]['kwargs'])}"
    )
    assert _key_style_of(limiter_module.limiter) == "endpoint"


# ===========================================================================
# 7. BLAST RADIUS -- the PR's statement, pinned in code
# ===========================================================================
# Every entry is a route whose registered limit has a FALSY scope, so slowapi
# buckets it on `_endpoint_key` and the flag re-buckets it. Values are
# `str(Limit.limit)` on the installed limits package.
_SPEC_TABLE_PATH_PARAM_ROUTES = {
    "app.api.history_routes.get_comparison": "20 per 1 minute",
    "app.api.history_routes.remove_comparison": "20 per 1 minute",
    "app.api.referral_routes.resolve_invite": "20 per 1 minute",
    "app.api.referral_routes.submit_invitee_quiz": "10 per 1 minute",
    "app.api.share_routes.share_comparison": "10 per 1 minute",
    "app.api.share_routes.view_shared_comparison": "30 per 1 minute",
}

# The SEVENTH path-parameter route. The spec's appended correction says it
# "carries only the (flag-gated, currently OFF) default" -- MEASURED FALSE, see
# the assertion below.
_SEVENTH_PATH_PARAM_ROUTE = "app.api.text_routes.get_gcc_prices"


def _real_route_limits():
    """The REAL limiter's registrations (app.main was imported at module load)."""
    return importlib.import_module(RATE_LIMITER_MODULE).limiter._route_limits


def test_blast_radius_table_matches_the_registered_limits(monkeypatch):
    """PIN: the six routes in the spec's corrected table exist with those limits,
    and each is registered with a falsy scope, i.e. bucketed on ``_endpoint_key``."""
    route_limits = _real_route_limits()

    for name, expected in _SPEC_TABLE_PATH_PARAM_ROUTES.items():
        assert name in route_limits, (
            f"{name} carries no registered @limiter.limit -- the blast-radius "
            "table is stale"
        )
        limits = route_limits[name]
        assert len(limits) == 1, (
            f"{name} is expected to carry exactly one limit; got "
            f"{[(str(lim.limit), lim.scope) for lim in limits]!r}"
        )
        assert str(limits[0].limit) == expected, (
            f"{name}: table says {expected!r}, code says {str(limits[0].limit)!r}"
        )
        assert not limits[0].scope, (
            f"{name} carries an explicit scope {limits[0].scope!r}, so the "
            "key_style flag would NOT re-bucket it and the table row is wrong"
        )


def test_seventh_path_param_route_is_also_in_the_blast_radius(monkeypatch):
    """SPEC DISAGREEMENT, pinned: GET /text/prices/{product} is NOT default-only.

    The spec's appended correction says this route "carries only the
    (flag-gated, currently OFF) default". Measured at HEAD it carries TWO
    explicit limits (``text_routes.py:820-826``), mutually exclusive via
    ``exempt_when``:

      * ``@limiter.shared_limit("20/minute", scope="text_prices_route",
        exempt_when=_paid_route_metering_disabled)`` -- live only when
        ENABLE_PAID_ROUTE_METERING is ON; explicit scope, so key_style cannot
        touch it.
      * ``@limiter.limit("20/minute", exempt_when=paid_route_metering_enabled)``
        -- live under the SHIPPED default (metering OFF); falsy scope, so it
        buckets on ``_endpoint_key`` and the flag DOES re-bucket it.

    So under the shipped configuration the blast radius is SEVEN routes, not
    six. The one-line key_style fix covers this route too; only the PR's
    blast-radius statement needs the extra row.
    """
    route_limits = _real_route_limits()

    assert _SEVENTH_PATH_PARAM_ROUTE in route_limits, (
        f"{_SEVENTH_PATH_PARAM_ROUTE} carries no registered limit at all"
    )
    limits = route_limits[_SEVENTH_PATH_PARAM_ROUTE]
    unscoped = [lim for lim in limits if not lim.scope]

    assert unscoped, (
        "GET /text/prices/{product} was expected to carry an explicit, "
        "UNSCOPED limit that the key_style flag re-buckets; got "
        f"{[(str(lim.limit), lim.scope) for lim in limits]!r}"
    )
    assert [str(lim.limit) for lim in unscoped] == ["20 per 1 minute"], (
        "the unscoped (metering-OFF) limit on GET /text/prices/{product} is "
        f"expected to be 20/minute; got {[str(lim.limit) for lim in unscoped]!r}"
    )


# ===========================================================================
# 8. THE FLAG PARSER'S VALUE VOCABULARY
# ===========================================================================
# ADDED IN THE GREEN PHASE, by a mutation check. Replacing the helper's
# ("1", "true", "yes", "on") membership test with a bare
# `bool(os.getenv(FLAG, "").strip())` left all 11 tests above GREEN: none of
# them ever sets the flag to anything but "true" or unsets it, so the value
# vocabulary was entirely unpinned.
#
# That is not academic. This project's documented kill switch is
# `railway variables set ENABLE_<X>=false` (docs/BUNDLE_C_PROD_STATE.md:49,65),
# i.e. flags are turned off by SETTING the string "false", not by removing the
# variable. Under the permissive parser `ENABLE_LIMITER_ENDPOINT_KEY=false`
# would silently switch endpoint keying ON across all seven path-parameter
# routes -- the exact opposite of the operator's intent, and un-revertable
# except by deleting the variable. These two tests pin the same vocabulary the
# file's two neighbouring flag helpers (_proxy_aware_enabled,
# _default_rate_limits_enabled) already use.
_FLAG_VALUES_MEANING_OFF = ["", "   ", "false", "False", "FALSE", "0", "no", "off", "2"]
_FLAG_VALUES_MEANING_ON = ["1", "true", "True", "TRUE", "  true  ", "yes", "on", "ON"]


def _rate_limiter_with_raw_flag(raw_value):
    """Construct the limiter with FLAG set to a literal string.

    Env is restored by the autouse ``_env_sandbox`` fixture.
    """
    for key in _ENV_KEYS:
        os.environ.pop(key, None)
    os.environ[FLAG] = raw_value
    return _exec_private(RATE_LIMITER_MODULE)


@pytest.mark.parametrize("raw", _FLAG_VALUES_MEANING_OFF)
def test_flag_values_that_do_not_mean_yes_leave_todays_key_style(raw):
    """A value that does not affirmatively mean yes must keep url keying."""
    module = _rate_limiter_with_raw_flag(raw)

    assert _key_style_of(module.limiter) == "url", (
        f"{FLAG}={raw!r} does not affirmatively enable the flag, so the "
        "Limiter must keep slowapi's url key style; got "
        f"{_key_style_of(module.limiter)!r}. Setting a flag to the string "
        "'false' is this repo's documented kill switch -- a parser that reads "
        "it as ON would enable endpoint keying on seven routes by accident."
    )


@pytest.mark.parametrize("raw", _FLAG_VALUES_MEANING_ON)
def test_flag_values_that_mean_yes_switch_to_endpoint_keying(raw):
    """The accepted vocabulary matches the file's two neighbouring flag helpers."""
    module = _rate_limiter_with_raw_flag(raw)

    assert _key_style_of(module.limiter) == "endpoint", (
        f"{FLAG}={raw!r} is in the accepted truthy vocabulary "
        '("1"/"true"/"yes"/"on", case- and whitespace-insensitive) used by '
        "_proxy_aware_enabled and _default_rate_limits_enabled, so it must "
        f"select endpoint keying; got {_key_style_of(module.limiter)!r}"
    )
