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

from tests._env_safety import live_mode_enabled

# --- run-mode guards -------------------------------------------------------
#
# Most of this file asserts what a DEFAULT (non-LIVE) test process sees. That
# contract deliberately does not hold under the LIVE=1 opt-in, so those tests
# SKIP there rather than fail — otherwise the whole-suite command this very
# commit documents (`LIVE=1 python -m pytest tests/`) could never pass, and a
# doc that prescribes an impossible command is worse than no doc.
_DEFAULT_TIER_ONLY = pytest.mark.skipif(
    live_mode_enabled(),
    reason="asserts the default (non-LIVE) credential contract; LIVE=1 opts out of it",
)

# The two marker probes below exist only to be collected by a subprocess in
# this file. They must never execute in an ordinary run: one raises by design,
# and the other asserts an environment only its own subprocess arranges. The
# subprocesses set this variable; nothing else does.
_PROBE_ENV = "QAREN_ENV_SAFETY_PROBE"
_PROBE_ONLY = pytest.mark.skipif(
    os.getenv(_PROBE_ENV) != "1",
    reason="probe fixture — only meaningful inside its own subprocess",
)

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


@_DEFAULT_TIER_ONLY
def test_production_credentials_are_absent_by_default():
    """No credential-bearing env var still holds its production value.

    The oracle is a COMPARISON between two things, and both halves are load
    bearing:

      * LIVE `os.environ` -- what a test would actually read right now.
      * the fingerprint the sanitizer took of that same name BEFORE it acted
        (`tests/_env_safety.PRE_SANITIZE_FINGERPRINTS`), i.e. the real `.env`
        value as it stood at conftest import.

    Neither alone works. A plain "must be falsy" assertion on `os.environ` is
    order-dependent: tests legitimately install fakes with no teardown (e.g.
    `test_analytics.py:245` assigns `ADMIN_API_KEY = "test-admin-key-123"`).
    The pre-sanitize record alone is worse than useless -- an earlier revision
    of this test read a record captured AFTER the pop loop, so every watched
    name was `None` by construction and the test could not fail even with a
    real credential re-injected into the running process.

    Comparing them is red exactly when it should be: the name is set AND holds
    the production value the sanitizer saw. A test's own fake fingerprints
    differently and does not trip it.

    Names only in the message -- never values, and never digests.
    """
    from tests._env_safety import PRE_SANITIZE_FINGERPRINTS, fingerprint

    assert os.getenv("LIVE") is None, (
        "This test asserts the DEFAULT tier; re-run without LIVE set."
    )
    assert PRE_SANITIZE_FINGERPRINTS, (
        "sanitizer never ran against the real environment"
    )
    leaked = [
        name
        for name in _CONTRACT_UNSET
        if PRE_SANITIZE_FINGERPRINTS.get(name)
        and fingerprint(os.getenv(name)) == PRE_SANITIZE_FINGERPRINTS[name]
    ]
    assert not leaked, (
        "production credentials leaked into the test process: "
        + ", ".join(leaked)
    )


@_DEFAULT_TIER_ONLY
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


@_DEFAULT_TIER_ONLY
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


def _sentinel_hosts():
    """(name, host) for every placeholder that is a URL."""
    from tests._env_safety import CREDENTIAL_PLACEHOLDERS

    return [
        (name, value.split("://", 1)[1].split("/")[0])
        for name, value in CREDENTIAL_PLACEHOLDERS.items()
        if "://" in value
    ]


def test_sentinel_hosts_are_reserved_names():
    """Any unmocked call against a sentinel fails locally, never in production.

    `.invalid` is reserved by RFC 2606 and is guaranteed not to resolve, so a
    query that slips past its mock errors instead of reaching a real Supabase
    project. Measured on Windows: a `supabase-py` query against the sentinel
    fails in 0.002-0.20s.
    """
    hosts = _sentinel_hosts()
    assert hosts, "no URL sentinel to check -- did the placeholder list change?"
    for name, host in hosts:
        assert host.split(":")[0].endswith(".invalid"), (
            f"{name} sentinel must point at a reserved .invalid host"
        )


def test_sentinel_hosts_really_do_not_resolve_here():
    """The reserved name must also be un-resolvable ON THIS MACHINE.

    The suffix check above is a statement about the RFC; this one is a
    statement about the resolver actually in front of the developer. Resolvers
    that hijack NXDOMAIN (some consumer ISPs, some corporate DNS) answer with
    an A record for a name that does not exist -- and then a query that slips
    past its mock does not fail fast, it hangs to timeout, in a repo whose
    stated problem is a suite that hangs on network calls.

    A machine with no DNS at all raises `gaierror` too and passes, which is
    correct: nothing can be reached from there either.
    """
    import socket

    resolvable = []
    for name, host in _sentinel_hosts():
        hostname = host.split(":")[0]
        try:
            socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            continue
        except OSError:
            continue
        resolvable.append(f"{name} ({hostname})")

    assert not resolvable, (
        "this machine's resolver ANSWERS for a reserved .invalid name, which "
        "defeats the fail-fast property of the credential sentinel -- an "
        "unmocked query will hang to timeout instead of erroring. Point the "
        "resolver at one that returns NXDOMAIN (e.g. 1.1.1.1 / 8.8.8.8) or "
        "disable NXDOMAIN redirection. Affected: " + ", ".join(resolvable)
    )


@_DEFAULT_TIER_ONLY
def test_later_load_dotenv_cannot_reinject_credentials():
    """`load_dotenv(override=True)` from app modules must not undo the fix.

    Three app modules call it at import time. Without the guard, importing
    `app.services.extraction_service` restores every real credential before
    `cache_service` reads `UPSTASH_REDIS_URL` at ITS import -- and the
    module-level Upstash client points at production again.

    This has to run against the REAL process environment (that is the thing
    under test), so it restores `os.environ` exactly afterwards: `override=True`
    also re-applies the NON-credential half of `.env` -- ENVIRONMENT, DEBUG,
    LOG_LEVEL, FREE_TIER_DAILY_LIMIT, MAX_MONTHLY_COST, CACHE_DURATION -- over
    whatever the suite currently holds, which would be an order-dependent flake
    for any later test that set one of those at module scope.
    """
    import dotenv

    before = dict(os.environ)
    try:
        dotenv.load_dotenv(override=True)

        leaked = [name for name in _CONTRACT_UNSET if os.getenv(name)]
        assert not leaked, (
            "load_dotenv re-injected production credentials: "
            + ", ".join(leaked)
        )
    finally:
        for name in [n for n in os.environ if n not in before]:
            del os.environ[name]
        os.environ.update(before)


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


# The five modules whose own `os.getenv("SUPABASE_URL") -> pytest.skip(...)`
# guard the SUPABASE_* sentinel defeats: with a sentinel present that guard
# sees a truthy value and lets the body run, so what actually keeps them off a
# real project is the live-tier marker plus the collection hook. Listed as
# exact node ids and asserted against a REAL pytest collection rather than a
# substring scan of the file text -- `pytest.mark.live_db` appears in the
# DOCSTRING of four of these modules, so a text scan stays green even when the
# decorator itself is deleted.
_SUPABASE_GUARDED_FILES = (
    "tests/test_demographics_rls.py",
    "tests/test_migration_023.py",
    "tests/test_migration_028_pain_workflow_events.py",
    "tests/test_migration_032_b1_pre_hardening.py",
    "tests/test_drug_database_service.py",
)

_SUPABASE_GUARDED_NODEIDS = frozenset({
    "tests/test_demographics_rls.py::test_demographics_profile_column_exists",
    "tests/test_demographics_rls.py::test_user_b_cannot_read_user_a_demographics_via_rls",
    "tests/test_demographics_rls.py::test_demographics_dismissed_columns_exist",
    "tests/test_migration_023.py::TestMigration023LiveSchema::test_lifetime_invites_consumed_column_exists",
    "tests/test_migration_023.py::TestMigration023LiveSchema::test_weekly_invites_used_column_dropped",
    "tests/test_migration_028_pain_workflow_events.py::TestMigration028LiveSchema::test_pain_workflow_events_table_selectable",
    "tests/test_migration_028_pain_workflow_events.py::TestMigration028LiveSchema::test_workflow_name_check_rejects_unknown_value",
    "tests/test_migration_032_b1_pre_hardening.py::TestMigration032LiveSchema::test_comparisons_cache_dropped",
    "tests/test_migration_032_b1_pre_hardening.py::TestMigration032LiveSchema::test_products_still_writable_via_service_role",
    "tests/test_drug_database_service.py::TestFindMatchingDrugs::test_exact_trade_name_match",
    "tests/test_drug_database_service.py::TestFindMatchingDrugs::test_partial_ingredient_match",
    "tests/test_drug_database_service.py::TestFindMatchingDrugs::test_vitamin_d_search",
    "tests/test_drug_database_service.py::TestFindMatchingDrugs::test_no_match_returns_empty",
    "tests/test_drug_database_service.py::TestFindMatchingDrugs::test_limit_parameter",
    "tests/test_drug_database_service.py::TestFindMatchingDrugs::test_result_fields",
})

_LIVE_TIER_SELECTION = "live_unit or live_db or integration"


def _collect_nodeids(marker_expression):
    """Node ids pytest really selects for `-m <marker_expression>`.

    Runs `--collect-only` in a subprocess so the assertion goes through the
    same collection path `pytest_collection_modifyitems` runs in -- the honest
    oracle for "is this item in the live tier?", and one that a docstring
    mentioning a marker name cannot satisfy.
    """
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            *_SUPABASE_GUARDED_FILES,
            "--collect-only", "-q",
            "-m", marker_expression,
            "-p", "no:cacheprovider",
            "--timeout=45",
        ],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        "collection failed for -m %r\n%s\n%s"
        % (marker_expression, result.stdout[-3000:], result.stderr[-2000:])
    )
    collected = {
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if "::" in line and line.strip().startswith("tests")
    }
    assert collected, (
        "collected nothing for -m %r -- the oracle is not looking at anything"
        % (marker_expression,)
    )
    return collected


def test_supabase_live_db_guards_are_superseded_by_the_marker_hook():
    """The sentinel is safe only because the marker hook fires first.

    Those modules gate on `os.getenv("SUPABASE_URL") and ...` then
    `pytest.skip(...)` when it is absent. The sentinel makes that guard see a
    truthy value, so a clean skip would become a live connection attempt --
    unless the item carries a live-tier marker and the collection hook skips it
    before the body runs. Under LIVE=1 both stand down and the guards see the
    real values again.

    Asserted by COLLECTING the five files under the live-tier marker expression
    and checking every Supabase-touching node id is in that selection. `-m X`
    and `-m "not X"` partition the same collection, so membership here is also
    proof of absence from the default tier.
    """
    live_tier = _collect_nodeids(_LIVE_TIER_SELECTION)

    unprotected = sorted(_SUPABASE_GUARDED_NODEIDS - live_tier)
    assert not unprotected, (
        "these Supabase-touching tests are NOT in the live tier, so the "
        "collection hook cannot protect them from the sentinel and a default "
        "`pytest tests/` would run them against a real project: "
        + ", ".join(unprotected)
    )


def test_no_supabase_guarded_test_is_reachable_from_the_default_tier():
    """The same claim from the other side, and it catches new-test drift.

    `tests/test_demographics_rls.py` marks the WHOLE module
    (`pytestmark = pytest.mark.live_db`), so a test added there without a
    marker cannot exist: assert the default tier collects nothing at all from
    it. For the mixed modules, assert none of the known Supabase node ids has
    slipped into the default selection.
    """
    default_tier = _collect_nodeids("not (%s)" % _LIVE_TIER_SELECTION)

    leaked = sorted(_SUPABASE_GUARDED_NODEIDS & default_tier)
    assert not leaked, (
        "Supabase-touching tests are selected by the DEFAULT tier: "
        + ", ".join(leaked)
    )

    escaped = sorted(
        node
        for node in default_tier
        if node.startswith("tests/test_demographics_rls.py::")
    )
    assert not escaped, (
        "tests/test_demographics_rls.py is live_db at module scope; these "
        "items escaped that marker: " + ", ".join(escaped)
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
        # The probe is _PROBE_ONLY-gated so it can never fire in an ordinary
        # run; this subprocess is the one caller allowed to reach it. LIVE is
        # cleared explicitly so the assertion holds even when the PARENT run
        # was invoked with LIVE=1.
        env={**os.environ, _PROBE_ENV: "1", "LIVE": ""},
    )
    assert "1 skipped" in result.stdout, result.stdout[-3000:]
    assert "LIVE=1" in result.stdout, result.stdout[-3000:]


@_PROBE_ONLY
@pytest.mark.live_db
def test_marker_tier_probe():
    """Probe used by `test_live_tier_markers_are_skipped_without_the_opt_in`.

    Deselected by the default `-m "not (live_unit or live_db or integration)"`
    selection; only ever reached by the subprocess above, where the collection
    hook must skip it before the body can run.
    """
    raise AssertionError("must never execute without the LIVE opt-in")


def test_live_opt_in_restores_the_environment_end_to_end(tmp_path):
    """LIVE=1 through the REAL conftest: the tier runs and the value survives.

    The pure-function test above covers the predicate; this one covers the
    wiring, which is where a sanitizer usually breaks a marker tier. Probes
    `SENTRY_DSN` because it is the cheapest var to prove: stripped by default,
    and never touched by any network call in the probe body.

    Deliberately HERMETIC. `LIVE=1` means "give this process real credentials",
    and this test is part of the DEFAULT suite -- spawning a fully credentialled
    child from a plain `pytest tests/` would mean any future import side effect
    in `conftest.py` runs against production. So the child runs with `cwd` on a
    scratch dir (no `.env` for `load_dotenv` to find), inherits only this
    process's already-sanitized environment, and gets one injected sentinel DSN.
    That is also the sharper assertion: the DSN it sees can only have survived
    because `LIVE=1` stood the sanitizer down.
    """
    probe_dsn = "https://opt-in-probe@example.invalid/1"
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(Path(__file__).resolve()) + "::test_live_opt_in_probe",
            "-m", "live_unit",
            "-p", "no:cacheprovider",
            "--timeout=45",
            "-rs", "-q",
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=300,
        env={
            **os.environ,
            _PROBE_ENV: "1",
            "LIVE": "1",
            "SENTRY_DSN": probe_dsn,
            "PYTHONPATH": str(_REPO_ROOT),
        },
    )
    assert "1 passed" in result.stdout, result.stdout[-3000:]


@_PROBE_ONLY
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
