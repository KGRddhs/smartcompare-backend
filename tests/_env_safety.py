"""Credential neutralisation for the default (non-LIVE) test tier — issue #48.

WHY THIS EXISTS
---------------
`tests/conftest.py` loads the developer's real `.env` over the top of the
process environment (`load_dotenv(override=True)`), so a local
`pytest tests/` ran the DEFAULT suite with production credentials. Two
reach-through vectors fire at IMPORT time, before any fixture can intervene:

  * `app/main.py:42` calls `init_sentry()` at module scope and
    `app/services/sentry_service.py:199-202` initialises the real SDK for any
    non-empty `SENTRY_DSN` — test exceptions report into production Sentry.
  * `app/services/cache_service.py:15-28` builds the Upstash client at module
    scope — any unmocked cache call READS AND WRITES the shared production
    cache that the warmer and live users read.

`load_dotenv` is left in place (feature flags and tuning knobs are still
expected to come from `.env`); only the credential-bearing and
production-endpoint names are neutralised, and only when the caller has not
opted in with `LIVE=1`.

WHY A GUARD ON `load_dotenv` TOO
-------------------------------
Sanitising once in `conftest.py` is necessary but not sufficient:
`app/main.py:11`, `app/services/extraction_service.py:5` and
`app/services/url_extraction_service.py:6` each call
`load_dotenv(override=True)` themselves at import. Importing any of them
re-injects the real `.env` on top of the sanitized environment — and if that
happens before `cache_service` is imported, the module-level Upstash client
points at production again. `install_dotenv_guard()` wraps the real
`load_dotenv` so the non-credential half of `.env` keeps flowing while the
credentials are re-cleared on every reload.

POP OR SENTINEL — THE RULE
--------------------------
A var is CLEARED when absence is the state its consumer already documents as
"disabled": `cache_service` falls to `redis_client = None`, `init_sentry()`
returns early, the vendor clients all check `if not KEY`. Absence there
reproduces exactly the credential-free environment CI runs, so nothing new is
invented and an unmocked call cannot go anywhere.

A var gets an unusable SENTINEL when absence would break a legitimately
OFFLINE test instead of disabling anything — `openai_service.py:20` builds
`AsyncOpenAI(...)` at import, `create_client()` is a pure constructor that
dozens of fully-mocked tests reach through a service `__init__`, and
`youtube_service.py:47` caches its key in a module-level global whose value
depends on import order. Each sentinel reuses the exact literal the test suite
already `os.environ.setdefault(...)`s for itself, and every sentinel host sits
under RFC 2606's reserved `.invalid` TLD, so a call that slips past its mock
fails locally and instantly rather than reaching production.

Measured: popping the `SUPABASE_*` trio instead fails ~80 offline tests, and
popping `YOUTUBE_API_KEY` fails 9 more in-suite-only. Both were passing on
main by talking to the real production project.

WHAT PROTECTS THE LIVE TIERS
----------------------------
`test_demographics_rls.py`, `test_migration_023.py`,
`test_migration_028_pain_workflow_events.py` and
`test_migration_032_b1_pre_hardening.py` gate on `os.getenv("SUPABASE_URL")`
and `pytest.skip(...)` when it is missing — a guard the sentinel would defeat
on its own. They are protected instead by :data:`LIVE_TIER_MARKERS` and the
`pytest_collection_modifyitems` hook in `conftest.py`, which skips every
live-tier item before its body runs unless `LIVE=1` is set. Under `LIVE=1`
both the hook and this sanitizer stand down and the guards see real values
again.
"""
from __future__ import annotations

import os
from typing import Dict, MutableMapping, Optional

#: Opt-in switch. `LIVE=1` restores the real `.env` for the live tiers.
LIVE_OPT_IN_ENV = "LIVE"

#: Accepted truthy spellings of the opt-in. `0` / `false` / `` are NOT
#: opt-ins — a half-set variable must never re-enable production credentials.
_TRUTHY = frozenset({"1", "true", "yes", "on"})

#: Marker tiers that genuinely need real credentials. Without the opt-in they
#: are skipped rather than allowed to fail confusingly or pass vacuously.
#: `bench` is deliberately NOT here: it carries its own independent `BENCH=1`
#: gate and targets a hardcoded prod URL rather than credentials.
LIVE_TIER_MARKERS = ("live_unit", "live_db", "integration")

#: Credential and production-endpoint variables whose SAFE state is "absent".
#: Sourced from a grep of `os.getenv("...")` across `app/` and `scripts/`;
#: re-run that grep when adding an integration.
CREDENTIALS_UNSET = (
    # Observability — init_sentry() no-ops on an empty DSN.
    "SENTRY_DSN",
    # Shared production cache — cache_service falls to `redis_client = None`.
    "UPSTASH_REDIS_URL",
    "UPSTASH_REDIS_TOKEN",
    # LLM — the PDPL opt-out key falls back to the shared client when absent.
    "OPENAI_API_KEY_PRIVATE",
    # LLM endpoint — absent means stock OpenAI, the flag-OFF default.
    "OPENAI_BASE_URL",
    # Paid search / scraping vendors.
    "SERPER_API_KEY",
    "SERPER_API_KEYS",
    "FIRECRAWL_API_KEY",
    "SCRAPEDO_API_TOKEN",
    "BRIGHTDATA_API_KEY",
    "BRIGHTDATA_ZONE",
    "ZYTE_API_KEY",
    # Privileged app surfaces.
    "ADMIN_API_KEY",
    "NASSER_GUEST_TOKEN",
    # Deployed API the eval/bench runners point at.
    "TARGET_BASE_URL",
)

#: Variables that must stay PRESENT but must never be real. Both entries here
#: are cases where ABSENCE breaks a legitimately offline test rather than
#: disabling anything, so the safe state is an unusable value, not no value.
#: Every host below is under RFC 2606's reserved `.invalid` TLD, which can
#: never resolve — an unmocked call fails locally and instantly.
CREDENTIAL_PLACEHOLDERS: Dict[str, str] = {
    # openai_service.py:20 constructs AsyncOpenAI at module import and raises
    # OpenAIError on a missing key. Same literal ~120 test modules already
    # `os.environ.setdefault(...)` for themselves, so nothing new is invented.
    "OPENAI_API_KEY": "sk-test-dummy",
    # database_service/auth_service pass these straight to `create_client()`,
    # which is a PURE CONSTRUCTOR — no I/O. Dozens of offline tests build a
    # service whose __init__ calls `get_admin_supabase_client()` (e.g.
    # AbuseDetectionService.__init__) and then mock every query. Popping the
    # vars turns that pure constructor into a ValueError and fails ~80 tests
    # that never touch the network; a non-resolvable host keeps them offline
    # AND makes any genuinely unmocked query fail loudly instead of reaching
    # production. The live_db tiers are protected by the marker hook, not by
    # the absence of these vars — see LIVE_TIER_MARKERS.
    "SUPABASE_URL": "https://neutralized.supabase.invalid",
    "SUPABASE_ANON_KEY": "test-anon-key-neutralized",
    "SUPABASE_SERVICE_KEY": "test-service-key-neutralized",
    # youtube_service.py:47 reads YOUTUBE_API_KEY into a MODULE-LEVEL global,
    # so whether it is set depends on which test file imported the service
    # first. The five test_youtube_* modules each `os.environ.setdefault(
    # "YOUTUBE_API_KEY", "test-yt-key")`, which only wins if none of them was
    # beaten to the import — popping the var makes 9 of their tests fail in
    # suite while passing alone. Same literal they use, so the setdefaults
    # become no-ops and the global is deterministic either way. The absent
    # branch stays covered: test_youtube_service.py:186 monkeypatches the
    # module global to None directly.
    "YOUTUBE_API_KEY": "test-yt-key",
}

#: What the credential vars actually resolved to the first time the sanitizer
#: ran against the real process environment (i.e. at conftest import, before
#: any test could touch them). Tests assert the SESSION-START guarantee against
#: this rather than against live `os.environ`, which individual tests are free
#: to mutate with fakes of their own.
COLLECTION_SNAPSHOT: Dict[str, Optional[str]] = {}


def live_mode_enabled(environ: Optional[MutableMapping[str, str]] = None) -> bool:
    """True when the caller explicitly opted into real credentials."""
    env = os.environ if environ is None else environ
    return (env.get(LIVE_OPT_IN_ENV) or "").strip().lower() in _TRUTHY


def neutralize_credentials(
    environ: Optional[MutableMapping[str, str]] = None,
) -> Dict[str, Optional[str]]:
    """Strip production credentials from ``environ`` unless ``LIVE`` is set.

    Returns a map of the names acted on to their resulting value (``None``
    for the ones removed), so a caller can log what changed without ever
    handling the secret it replaced. A no-op returning ``{}`` under the
    ``LIVE`` opt-in.

    Feature flags are explicitly out of scope: nothing in
    :data:`CREDENTIALS_UNSET` or :data:`CREDENTIAL_PLACEHOLDERS` starts with
    ``ENABLE_``, so the ``setdefault`` semantics in ``conftest.py`` — which
    encode flag-OFF-in-production — are untouched.
    """
    env = os.environ if environ is None else environ
    if live_mode_enabled(env):
        return {}

    changed: Dict[str, Optional[str]] = {}
    for name in CREDENTIALS_UNSET:
        if env.pop(name, None) is not None:
            changed[name] = None
    for name, placeholder in CREDENTIAL_PLACEHOLDERS.items():
        if env.get(name) != placeholder:
            env[name] = placeholder
            changed[name] = placeholder

    if env is os.environ and not COLLECTION_SNAPSHOT:
        COLLECTION_SNAPSHOT.update(
            (name, env.get(name))
            for name in (*CREDENTIALS_UNSET, *CREDENTIAL_PLACEHOLDERS)
        )
    return changed


def install_dotenv_guard() -> bool:
    """Re-run :func:`neutralize_credentials` after every ``load_dotenv`` call.

    ``app/main.py``, ``app/services/extraction_service.py`` and
    ``app/services/url_extraction_service.py`` call ``load_dotenv(override=True)``
    at import time, which would otherwise re-inject the real ``.env`` over the
    sanitized environment. Wrapping (rather than disabling) keeps the
    non-credential half of ``.env`` — feature flags, tuning knobs — working
    exactly as before.

    Idempotent. Returns False when it was already installed or the opt-in is
    active, True when a guard was installed.
    """
    if live_mode_enabled():
        return False

    import dotenv
    import dotenv.main

    real_load_dotenv = dotenv.main.load_dotenv
    if getattr(real_load_dotenv, "_qaren_env_guard", False):
        return False

    def guarded_load_dotenv(*args, **kwargs):
        result = real_load_dotenv(*args, **kwargs)
        neutralize_credentials()
        return result

    guarded_load_dotenv._qaren_env_guard = True  # type: ignore[attr-defined]
    guarded_load_dotenv.__doc__ = real_load_dotenv.__doc__
    guarded_load_dotenv.__name__ = real_load_dotenv.__name__

    # Patch BOTH bindings: modules do `from dotenv import load_dotenv` and the
    # `dotenv` package re-exports the `dotenv.main` symbol.
    dotenv.main.load_dotenv = guarded_load_dotenv
    dotenv.load_dotenv = guarded_load_dotenv
    return True


def live_tier_skip_reason() -> str:
    """Message shown when a live-tier test is skipped for lack of the opt-in."""
    # ASCII only: this string is printed by `pytest -rs` into consoles whose
    # encoding (Windows cp1252) mangles anything else.
    return (
        "live-tier test needs real credentials: re-run with LIVE=1 "
        "(default runs are credential-free - see tests/_env_safety.py)"
    )
