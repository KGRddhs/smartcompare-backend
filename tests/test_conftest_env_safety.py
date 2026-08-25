"""Issue #48 — the default test tier must never carry production credentials.

`tests/conftest.py` calls `load_dotenv(override=True)`, so a local
`pytest tests/` used to inherit the developer's REAL Sentry DSN, Upstash
token, Supabase service key, OpenAI key and Serper key. Two of those reach
production at IMPORT time, before any fixture can intervene:

  * `app/main.py` calls `init_sentry()` at module scope, and
    `sentry_service.init_sentry()` initialises the real SDK whenever
    `SENTRY_DSN` is non-empty -> test exceptions land in the production
    Sentry stream.
  * `app/services/cache_service.py` builds the Upstash client at module
    scope from `UPSTASH_REDIS_URL` / `UPSTASH_REDIS_TOKEN` -> a test that
    forgets to mock READS AND WRITES the shared production cache that the
    warmer and live users read. `tests/test_algolia_catalog_stores.py:38-48`
    already documents a suite going RED because of exactly this.

Clearing the vars in `conftest.py` is necessary but NOT sufficient:
`app/main.py:11`, `app/services/extraction_service.py:5` and
`app/services/url_extraction_service.py:6` each call
`load_dotenv(override=True)` themselves at import, which would re-inject
the real values on top of the sanitized ones. Hence the dotenv guard.

The contract list below is deliberately duplicated from
`tests/_env_safety.py` rather than imported: it states what the suite
PROMISES, independent of how the sanitizer happens to be implemented.
`test_helper_covers_the_whole_contract` catches drift.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Every credential / production-endpoint variable that must NOT be visible to
# a default (non-LIVE) test process. Absence is the safe state for all of
# these: every consumer reads them via `os.getenv(...)` and falls to a
# documented disabled branch, and the live_db suites skip on their absence.
_CONTRACT_UNSET = (
    "SENTRY_DSN",
    "UPSTASH_REDIS_URL",
    "UPSTASH_REDIS_TOKEN",
    "OPENAI_API_KEY_PRIVATE",
    "OPENAI_BASE_URL",
    "SERPER_API_KEY",
    "SERPER_API_KEYS",
    "FIRECRAWL_API_KEY",
    "SCRAPEDO_API_TOKEN",
    "BRIGHTDATA_API_KEY",
    "BRIGHTDATA_ZONE",
    "ZYTE_API_KEY",
    "ADMIN_API_KEY",
    "NASSER_GUEST_TOKEN",
    "TARGET_BASE_URL",
)

# Variables that must stay PRESENT but unusable, because absence would break a
# legitimately offline test rather than disable anything. Every host is under
# RFC 2606's reserved `.invalid` TLD and can never resolve.
_CONTRACT_SENTINEL = (
    "OPENAI_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY",
    "YOUTUBE_API_KEY",
)


def test_production_credentials_are_absent_by_default():
    """No credential-bearing env var survives collection without LIVE=1.

    Asserted against the snapshot the sanitizer took at conftest import, which
    is the moment that matters: `app.main` (init_sentry) and `cache_service`
    (module-level Upstash client) are imported during collection. Live
    `os.environ` is the wrong oracle here -- individual tests legitimately
    install fakes of their own (e.g. `test_analytics.py:245` assigns
    `ADMIN_API_KEY = "test-admin-key-123"` with no teardown), which would make
    this assertion order-dependent.

    Fails loudly on a developer machine with a populated `.env` until the
    conftest sanitizer lands. Names only in the message -- never values.
    """
    from tests._env_safety import COLLECTION_SNAPSHOT

    assert os.getenv("LIVE") is None, (
        "This test asserts the DEFAULT tier; re-run without LIVE set."
    )
    assert COLLECTION_SNAPSHOT, "sanitizer never ran against the real environment"
    leaked = [name for name in _CONTRACT_UNSET if COLLECTION_SNAPSHOT.get(name)]
    assert not leaked, (
        "production credentials leaked into the test process: "
        + ", ".join(leaked)
    )


def test_no_dotenv_value_is_live_in_the_process():
    """Sharper oracle: no var still holds the literal value from the real `.env`.

    Order-independent in the other direction -- a test that installs its own
    obvious fake does not trip this, but a real credential does. Compares
    against `.env` without ever putting a value in an assertion message.
    """
    from dotenv import dotenv_values

    env_file = _REPO_ROOT / ".env"
    if not env_file.is_file():
        pytest.skip("no .env on this machine (CI) -- nothing could leak")

    real = dotenv_values(env_file)
    watched = (*_CONTRACT_UNSET, *_CONTRACT_SENTINEL)
    leaked = [
        name
        for name in watched
        if real.get(name) and os.getenv(name) == real[name]
    ]
    assert not leaked, (
        "the real .env value is live in this process for: " + ", ".join(leaked)
    )


@pytest.mark.parametrize("name", _CONTRACT_SENTINEL)
def test_present_but_unusable_vars_hold_the_sentinel(name):
    """The vars that must stay PRESENT resolve to the fake, not the real value.

    `OPENAI_API_KEY`: `app/services/openai_service.py:20` builds
    `AsyncOpenAI(...)` at module import and raises `OpenAIError` on a missing
    key, so popping it would break `import app.main` for the whole suite.
    `SUPABASE_*`: `create_client()` is a pure constructor, and dozens of
    offline tests build a service whose `__init__` calls
    `get_admin_supabase_client()` (e.g. `AbuseDetectionService.__init__`)
    before mocking every query -- popping those three fails ~80 tests that
    never touch the network.
    """
    from tests._env_safety import CREDENTIAL_PLACEHOLDERS

    value = os.getenv(name)
    assert value, f"{name} must stay non-empty"
    assert value == CREDENTIAL_PLACEHOLDERS[name], (
        f"{name} is not the test sentinel -- the real value is live in this "
        "process"
    )


def test_sentinel_hosts_can_never_resolve():
    """Any unmocked call against a sentinel fails locally, never in production.

    `.invalid` is reserved by RFC 2606 and is guaranteed not to resolve, so a
    query that slips past its mock errors instantly instead of reaching a real
    Supabase project.
    """
    from tests._env_safety import CREDENTIAL_PLACEHOLDERS

    for name, value in CREDENTIAL_PLACEHOLDERS.items():
        if "://" in value:
            assert value.split("://", 1)[1].split("/")[0].endswith(".invalid"), (
                f"{name} sentinel must point at a reserved .invalid host"
            )


def test_later_load_dotenv_cannot_reinject_credentials():
    """`load_dotenv(override=True)` from app modules must not undo the fix.

    Three app modules call it at import time. Without the guard, importing
    `app.services.extraction_service` restores every real credential before
    `cache_service` reads `UPSTASH_REDIS_URL` at ITS import -- and the
    module-level Upstash client points at production again.
    """
    import dotenv

    dotenv.load_dotenv(override=True)

    leaked = [name for name in _CONTRACT_UNSET if os.getenv(name)]
    assert not leaked, (
        "load_dotenv re-injected production credentials: " + ", ".join(leaked)
    )


def test_helper_covers_the_whole_contract():
    """The sanitizer's own list must not drift below the promised contract."""
    from tests._env_safety import CREDENTIALS_UNSET

    missing = sorted(set(_CONTRACT_UNSET) - set(CREDENTIALS_UNSET))
    assert not missing, f"sanitizer no longer clears: {missing}"


def test_live_opt_in_preserves_real_values():
    """LIVE=1 is the opt-in the live_unit / live_db / integration tiers need.

    Exercised against a throwaway mapping so the real process environment is
    never mutated (re-importing conftest mid-session is not possible).
    """
    from tests._env_safety import neutralize_credentials

    env = {
        "LIVE": "1",
        "SUPABASE_URL": "https://real.supabase.co",
        "UPSTASH_REDIS_TOKEN": "real-token",
        "OPENAI_API_KEY": "sk-real-key",
    }
    before = dict(env)

    changed = neutralize_credentials(env)

    assert changed == {}, "sanitizer must be a no-op under the LIVE opt-in"
    assert env == before, "LIVE=1 must leave the real .env values untouched"


@pytest.mark.parametrize("live_value", ["0", "false", "", "no"])
def test_non_truthy_live_values_do_not_opt_in(live_value):
    """A half-set LIVE must not be read as an opt-in."""
    from tests._env_safety import neutralize_credentials

    env = {"LIVE": live_value, "UPSTASH_REDIS_URL": "https://real.upstash.io"}

    neutralize_credentials(env)

    assert "UPSTASH_REDIS_URL" not in env


def test_sanitizer_clears_credentials_and_places_the_sentinels():
    """The default path: secrets popped, the two present-but-fake vars replaced."""
    from tests._env_safety import CREDENTIAL_PLACEHOLDERS, neutralize_credentials

    env = {
        "SENTRY_DSN": "https://real@sentry.io/1",
        "UPSTASH_REDIS_URL": "https://real.upstash.io",
        "SUPABASE_URL": "https://real.supabase.co",
        "OPENAI_API_KEY": "sk-real-key",
        "ENABLE_COHORT_PERSONALIZATION": "true",
    }

    changed = neutralize_credentials(env)

    assert "SENTRY_DSN" not in env
    assert "UPSTASH_REDIS_URL" not in env
    assert changed["UPSTASH_REDIS_URL"] is None
    for name, placeholder in CREDENTIAL_PLACEHOLDERS.items():
        assert env[name] == placeholder
        assert changed[name] == placeholder
    assert env["ENABLE_COHORT_PERSONALIZATION"] == "true"


def test_sanitizer_never_touches_feature_flags():
    """`ENABLE_*` semantics are load-bearing (conftest.py:14 / :19).

    The two `os.environ.setdefault` lines encode flag-OFF-in-production; the
    sanitizer must not clear or invent any `ENABLE_*` variable.
    """
    from tests._env_safety import CREDENTIAL_PLACEHOLDERS, CREDENTIALS_UNSET

    touched = sorted(
        name
        for name in (*CREDENTIALS_UNSET, *CREDENTIAL_PLACEHOLDERS)
        if name.startswith("ENABLE_")
    )
    assert not touched, f"sanitizer must not manage feature flags: {touched}"


def test_conftest_feature_flag_defaults_still_resolve_true():
    """The setdefault lines survive the sanitizer running before them."""
    assert os.getenv("ENABLE_COHORT_PERSONALIZATION") == "true"
    assert os.getenv("ENABLE_REFERRAL_SYSTEM") == "true"


def test_the_two_lists_are_disjoint():
    """A var is either cleared or sentinelled -- never both, never neither."""
    from tests._env_safety import CREDENTIAL_PLACEHOLDERS, CREDENTIALS_UNSET

    overlap = sorted(set(CREDENTIALS_UNSET) & set(CREDENTIAL_PLACEHOLDERS))
    assert not overlap, f"var is in both lists: {overlap}"


def test_supabase_live_db_guards_are_superseded_by_the_marker_hook():
    """The sentinel is safe only because the marker hook fires first.

    `test_demographics_rls.py`, `test_migration_023.py`,
    `test_migration_028_pain_workflow_events.py` and
    `test_migration_032_b1_pre_hardening.py` gate on
    `os.getenv("SUPABASE_URL") and ...` then `pytest.skip(...)` when absent.
    A sentinel would defeat that guard on its own -- turning a clean skip into
    a connection error -- so those suites must all carry a live-tier marker,
    which the collection hook skips before their body can read the sentinel.
    Under LIVE=1 both the hook and the sanitizer stand down and the guards see
    the real values again.
    """
    from tests._env_safety import LIVE_TIER_MARKERS

    guarded = (
        "test_demographics_rls.py",
        "test_migration_023.py",
        "test_migration_028_pain_workflow_events.py",
        "test_migration_032_b1_pre_hardening.py",
        "test_drug_database_service.py",
    )
    marker_decorators = tuple(f"pytest.mark.{m}" for m in LIVE_TIER_MARKERS)
    for file_name in guarded:
        source = (_REPO_ROOT / "tests" / file_name).read_text(encoding="utf-8")
        assert any(dec in source for dec in marker_decorators), (
            f"{file_name} reads SUPABASE_* but carries no live-tier marker, so "
            "the collection hook cannot protect it from the sentinel"
        )


def test_live_tier_markers_are_skipped_without_the_opt_in():
    """A live_unit/live_db/integration test must never pass vacuously.

    Without LIVE=1 the credentials are gone, so a live-tier test would
    either fail with a confusing 401 or -- worse -- pass without touching
    anything live. The collection hook turns that into an explicit skip
    naming the opt-in, which is the same posture the live_db suites already
    take when the Supabase vars are missing.
    """
    from tests._env_safety import LIVE_TIER_MARKERS

    assert set(LIVE_TIER_MARKERS) == {"live_unit", "live_db", "integration"}

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/test_conftest_env_safety.py::test_marker_tier_probe",
            "-m", "live_db",
            "-p", "no:cacheprovider",
            "--timeout=45",
            "-rs", "-q",
        ],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert "1 skipped" in result.stdout, result.stdout[-3000:]
    assert "LIVE=1" in result.stdout, result.stdout[-3000:]


@pytest.mark.live_db
def test_marker_tier_probe():
    """Probe used by `test_live_tier_markers_are_skipped_without_the_opt_in`.

    Deselected by the default `-m "not (live_unit or live_db or integration)"`
    selection; only ever reached by the subprocess above, where the collection
    hook must skip it before the body can run.
    """
    raise AssertionError("must never execute without the LIVE opt-in")


def test_live_opt_in_restores_the_environment_end_to_end():
    """LIVE=1 through the REAL conftest: the tier runs and the values survive.

    The pure-function test above covers the predicate; this one covers the
    wiring, which is where a sanitizer usually breaks a marker tier. Probes
    `SENTRY_DSN` because it is the cheapest var to prove: stripped by default,
    and never touched by any network call in the probe body.
    """
    probe_dsn = "https://opt-in-probe@example.invalid/1"
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/test_conftest_env_safety.py::test_live_opt_in_probe",
            "-m", "live_unit",
            "-p", "no:cacheprovider",
            "--timeout=45",
            "-rs", "-q",
        ],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "LIVE": "1", "SENTRY_DSN": probe_dsn},
    )
    assert "1 passed" in result.stdout, result.stdout[-3000:]


@pytest.mark.live_unit
def test_live_opt_in_probe():
    """Probe for `test_live_opt_in_restores_the_environment_end_to_end`.

    Reached only from that subprocess, where LIVE=1 must have suppressed both
    the sanitizer and the collection-hook skip. Asserts truthiness rather than
    an exact value so it holds whether the DSN came from the injected sentinel
    or from a real `.env`.
    """
    assert os.getenv("SENTRY_DSN"), "LIVE=1 must leave the real environment intact"


def test_app_main_still_imports_under_the_sentinels(tmp_path):
    """`import app.main` must survive the neutralised environment.

    Run in a subprocess (importing app.main into the running suite has
    side effects other tests do not expect) whose cwd is a scratch dir, so
    `load_dotenv()` inside `app/main.py` finds no `.env` to fall back on --
    the sentinels from this process are all it gets.
    """
    result = subprocess.run(
        [sys.executable, "-c", "import app.main; print('IMPORT_OK')"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
    )
    assert "IMPORT_OK" in result.stdout, (
        f"app.main failed to import\nstdout:\n{result.stdout[-2000:]}"
        f"\nstderr:\n{result.stderr[-3000:]}"
    )
