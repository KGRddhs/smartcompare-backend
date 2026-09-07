"""W1-7 (SESSION 65) RED tests -- both start commands declare
``--limit-concurrency``, and cannot drift apart.

Finding ``LS-CONCURRENCY-LIMITS-10``. Today ``railway.json``'s
``deploy.startCommand`` and ``Procfile``'s ``web:`` command carry the SAME
string with no concurrency bound::

    uvicorn app.main:app --host 0.0.0.0 --port $PORT

With no limit the single uvicorn worker accepts connections without bound, so a
pile-up becomes a 120 s spinner for every caller instead of a fast failure for
the overflow. A 503 at the door is a better answer than a timeout, and it breaks
stage 4 of the modelled cascade.

The second half of the finding is that the two files can DRIFT SILENTLY: Railway
uses ``railway.json``'s ``startCommand``, so a Procfile-only edit would look
applied and do nothing. The equality pin below is the durable half.

-------------------------------------------------------------------------------
SHELL EXPANSION -- MEASURED, NOT ASSUMED (this is a BOOT-CRITICAL string; a
literal ``${...}`` reaching uvicorn is a crash loop, not a degraded mode)
-------------------------------------------------------------------------------
``$PORT`` in the existing string proves the command is shell-expanded, but
``${VAR:-default}`` is a DIFFERENT expansion form. It was proven before being
adopted, by running the exact command string through ``sh -c`` against an
argv-printing stub on PATH and reading the argument uvicorn actually receives::

    CMD='uvicorn app.main:app --host 0.0.0.0 --port $PORT \
         --limit-concurrency "${UVICORN_LIMIT_CONCURRENCY:-512}"'

    # UVICORN_LIMIT_CONCURRENCY unset, PORT=8080
    ARGV: [app.main:app] [--host] [0.0.0.0] [--port] [8080] \
          [--limit-concurrency] [512]
    # UVICORN_LIMIT_CONCURRENCY=250
    ARGV: ... [--limit-concurrency] [250]
    # UVICORN_LIMIT_CONCURRENCY=   (set but empty -- the ``:-`` form)
    ARGV: ... [--limit-concurrency] [512]

Negative control, against the REAL uvicorn, confirming the failure mode this
proof exists to rule out::

    $ python -m uvicorn app.main:app ... \
          --limit-concurrency '${UVICORN_LIMIT_CONCURRENCY:-100}'
    Error: Invalid value for '--limit-concurrency':
      '${UVICORN_LIMIT_CONCURRENCY:-100}' is not a valid integer.

So the expansion HOLDS and the retunable form is adopted; ops can change the
ceiling without a code deploy. These tests therefore pin the expansion form
itself, not a bare literal.

100 is chosen against measured traffic, not from a template: normal load is 5-8
compares/min with a fan-out of ~18 internal tasks each, so 100 concurrent
REQUESTS sits far above any healthy minute and only engages in a genuine
pile-up.

-------------------------------------------------------------------------------
Expected state at RED
-------------------------------------------------------------------------------
  * ``test_railway_start_command_declares_limit_concurrency``  -- RED (absent)
  * ``test_procfile_start_command_declares_limit_concurrency`` -- RED (absent)
  * ``test_limit_concurrency_value_is_the_retunable_form``     -- RED (absent)
  * ``test_start_commands_are_byte_identical``   -- GREEN today, REGRESSION PIN
  * ``test_neither_command_declares_proxy_headers`` -- GREEN today, EXCLUSION PIN
"""
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RAILWAY_JSON = _REPO_ROOT / "railway.json"
_PROCFILE = _REPO_ROOT / "Procfile"

_PROCFILE_WEB_PREFIX = "web: "

# The exact value adopted for --limit-concurrency, proven expandable above.
_EXPECTED_LIMIT_VALUE = '"${UVICORN_LIMIT_CONCURRENCY:-512}"'


def _railway_start_command() -> str:
    assert _RAILWAY_JSON.is_file(), f"missing {_RAILWAY_JSON}"
    config = json.loads(_RAILWAY_JSON.read_text(encoding="utf-8"))
    deploy = config.get("deploy")
    assert isinstance(deploy, dict), "railway.json has no 'deploy' object"
    command = deploy.get("startCommand")
    assert isinstance(command, str) and command.strip(), (
        "railway.json deploy.startCommand is missing or not a string -- Railway "
        "boots from this string, so it is the one that must carry the limit"
    )
    return command.strip()


def _procfile_web_command() -> str:
    assert _PROCFILE.is_file(), f"missing {_PROCFILE}"
    for raw_line in _PROCFILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith(_PROCFILE_WEB_PREFIX.strip()):
            # Strip the process-type prefix ("web:") and any following space.
            return line.split(":", 1)[1].strip()
    pytest.fail("Procfile declares no 'web:' process type")


def _tokens(command: str) -> list:
    """Whitespace tokens of a start command.

    Neither command contains quoting today, and neither should: a quoted
    ``"${VAR:-default}"`` would still expand, but an unquoted one keeps the
    string diffable against railway.json character-for-character.
    """
    return command.split()


def _flag_value(command: str, flag: str):
    """Return the token following ``flag``, or None when the flag is absent."""
    tokens = _tokens(command)
    for index, token in enumerate(tokens):
        if token == flag:
            if index + 1 >= len(tokens):
                pytest.fail(f"{flag} present in {command!r} with no value after it")
            return tokens[index + 1]
        if token.startswith(f"{flag}="):
            return token.split("=", 1)[1]
    return None


# ---------------------------------------------------------------------------
# 1 + 2 -- the limit is declared in BOTH files (RED: absent from both today)
# ---------------------------------------------------------------------------


def test_railway_start_command_declares_limit_concurrency():
    """Railway boots from railway.json -- the bound must be in THIS string.

    RED today: the shipped startCommand is
    ``uvicorn app.main:app --host 0.0.0.0 --port $PORT`` with no bound, so the
    worker accepts connections without limit and a pile-up degrades into a
    120 s spinner for everyone instead of a 503 for the overflow.
    """
    command = _railway_start_command()
    assert "--limit-concurrency" in command, (
        "railway.json deploy.startCommand declares no --limit-concurrency; "
        f"got {command!r}"
    )


def test_procfile_start_command_declares_limit_concurrency():
    """The Procfile must carry the bound too, so the two cannot diverge.

    RED today: same unbounded string as railway.json.
    """
    command = _procfile_web_command()
    assert "--limit-concurrency" in command, (
        f"Procfile web: command declares no --limit-concurrency; got {command!r}"
    )


# ---------------------------------------------------------------------------
# The value is the retunable, PROVEN-EXPANDABLE form (RED: no value at all)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source, reader",
    [
        ("railway.json", _railway_start_command),
        ("Procfile", _procfile_web_command),
    ],
)
def test_limit_concurrency_value_is_the_retunable_form(source, reader):
    """Ops must be able to retune the ceiling without a code deploy.

    The value is pinned to the QUOTED form ``"${UVICORN_LIMIT_CONCURRENCY:-512}"``,
    whose shell expansion was MEASURED through ``sh -c`` with an argv-printing
    stub (unset -> ``512``, set -> the override) before adoption.

    THE QUOTES ARE LOAD-BEARING (Fable review). Unquoted, the substitution
    WORD-SPLITS: with ``UVICORN_LIMIT_CONCURRENCY='1 --workers 4'`` the measured
    argv gained two extra flags, i.e. an env var that only sets a ceiling could
    inject arbitrary uvicorn arguments. Quoted, the same value arrives as the
    single argument ``[1 --workers 4]``, which uvicorn rejects as a bad int -- a
    clean boot failure instead of a silently reconfigured server.

    512, NOT 100 (Fable review). uvicorn's gate is not on requests: it is
    ``len(self.connections) >= limit_concurrency or len(self.tasks) >= ...``
    (verified in the installed uvicorn's ``protocols/http/h11_impl.py`` and
    ``httptools_impl.py``). Idle HTTP keep-alive connections therefore COUNT, so
    a request-shaped estimate of 100 would have started shedding real users at a
    connection population this service can plausibly reach. 512 still bounds an
    unbounded pile-up while sitting far above any plausible keep-alive
    population at current traffic, and the ceiling is env-tunable so it can be
    lowered under observation rather than guessed at now.
    """
    value = _flag_value(reader(), "--limit-concurrency")
    assert value is not None, (
        f"{source} start command carries no --limit-concurrency value"
    )
    assert value == _EXPECTED_LIMIT_VALUE, (
        f"{source} --limit-concurrency is {value!r}, expected "
        f"{_EXPECTED_LIMIT_VALUE!r} so ops can retune without a code deploy"
    )


# ---------------------------------------------------------------------------
# 3 -- the durable half of the finding: the two strings cannot drift
# ---------------------------------------------------------------------------


def test_start_commands_are_byte_identical():
    """REGRESSION PIN -- this is GREEN TODAY and must stay green.

    DO NOT DELETE THIS AS "trivially passing". It is the durable half of
    LS-CONCURRENCY-LIMITS-10: Railway boots from ``railway.json``'s
    ``startCommand``, so a Procfile-only edit looks applied and does nothing.
    The whole point of the pin is that it is green BEFORE the change (both
    files carry the same unbounded string) and green AFTER it (both files
    carry the same bounded string) -- and RED for exactly the window in which
    someone edits one file and not the other.
    """
    railway = _railway_start_command()
    procfile = _procfile_web_command()
    assert railway == procfile, (
        "railway.json deploy.startCommand and the Procfile web: command have "
        "DRIFTED. Railway boots from railway.json, so a Procfile-only edit is "
        f"a silent no-op.\n  railway.json: {railway!r}\n  Procfile:     {procfile!r}"
    )


# ---------------------------------------------------------------------------
# 4 -- the deliberate exclusion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source, reader",
    [
        ("railway.json", _railway_start_command),
        ("Procfile", _procfile_web_command),
    ],
)
def test_neither_command_declares_proxy_headers(source, reader):
    """EXCLUSION PIN -- GREEN TODAY and deliberately so.

    ``--proxy-headers`` is NOT part of this change. It changes the client IP the
    slowapi rate limiter keys on, and that limiter is currently the only thing
    bounding the loop (see ENABLE_PROXY_AWARE_RATELIMIT, still dark pending a
    live check of Railway's proxy hop count). Adding it here would silently
    couple a concurrency change to an auth/abuse change. It is its own unit with
    its own canary.
    """
    command = reader()
    assert "--proxy-headers" not in command, (
        f"{source} start command declares --proxy-headers. That is deliberately "
        "OUT OF SCOPE for W1-7: it re-keys the rate limiter, which is currently "
        "the only bound on the event loop. Ship it as its own unit with its own "
        f"canary.\n  {command!r}"
    )
    assert "--forwarded-allow-ips" not in command, (
        f"{source} start command declares --forwarded-allow-ips, which is only "
        "meaningful alongside --proxy-headers and is equally out of scope here"
    )


def test_limit_concurrency_is_a_real_uvicorn_option_on_this_build():
    """Fable review addition -- the start command is BOOT CRITICAL.

    ``requirements.txt`` pins ``uvicorn==0.52.4``, which is what CI and Railway
    install; only 0.30.0 is installed in these worktrees and installing is not
    permitted here. So the measurements behind this unit were taken on a build
    that is NOT the deployed one -- the same local-vs-lock drift that blinded
    three route tests in M13, and the same gap recorded for sentry-sdk in W1-1.

    If ``--limit-concurrency`` were ever removed or renamed, uvicorn would exit
    on an unrecognised argument and the container would CRASH-LOOP on deploy --
    a worse failure than the unbounded acceptance this unit exists to fix. This
    assertion runs on whatever uvicorn is present, so CI settles it on the
    pinned build instead of Railway discovering it at boot.
    """
    import inspect

    import uvicorn.config

    params = inspect.signature(uvicorn.config.Config.__init__).parameters
    assert "limit_concurrency" in params, (
        f"uvicorn {getattr(__import__('uvicorn'), '__version__', '?')} has no "
        f"limit_concurrency option, but both start commands pass "
        f"--limit-concurrency. The container would fail to boot."
    )
