"""Fixture-driven tests of `.githooks/pre-commit` (T0b Phase A, test T3).

Every scenario builds a throwaway git repo under ``tmp_path``, writes the hook
into it as LF bytes (the Windows working copy is CRLF and dash rejects it:
"set: Illegal option -"), stages content and runs the hook directly under a
POSIX shell. One test node per scenario and per shell: ``sh`` always, and
``dash`` as well when it exists and is a different binary (on Ubuntu ``sh`` IS
dash, so the second column would only repeat the first).

Hermeticity (spec correction 11): every subprocess runs with all ``GIT_*``
variables dropped, ``GIT_CONFIG_NOSYSTEM=1``, a tmp ``HOME`` and
``XDG_CONFIG_HOME`` and a tmp ``TMPDIR``. A hook launched from a git hook or a
``git rebase -x`` would otherwise read the REAL index through an inherited
``GIT_DIR``, and through the .env fallback of correction 10 the REAL ``.env``.
Here the fallback resolves inside the tmp repo, which holds a FAKE ``.env``
only when a scenario writes one.

Security: every credential-shaped sentinel and every fake ``.env`` value is
BUILT at runtime by concatenation, so this file holds no credential-shaped
literal (the hook that guards this repo would refuse to commit it).

Every assertion names the specific refusal line, or the absence of any
refusal, never the exit code alone (correction 11 b). After every run the
hook must leave nothing behind: no ``.merge_file_*`` in the checkout root and
an empty ``TMPDIR`` (correction 14 h).
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".githooks" / "pre-commit"

PREFIX = "pre-commit: "

# Refusals the hook prints today (ASCII prefixes of the existing fail() texts).
MSG_CREDENTIAL = "staged diff contains what looks like a credential"
MSG_ENV_FILE = ".env must never be committed"
MSG_PY_SYNTAX = "python syntax error in staged files"
MSG_RUFF = "ruff blocking tier failed"
MSG_BLACK = "black allowlist check failed"

# New Phase A messages (ruling TR4). The GREEN hook prints each one, right
# after the "pre-commit: " prefix, at the START of a single line:
#   pre-commit: staged diff contains a JWT or a credentialed URL ...
#   pre-commit: staged diff contains the value of .env variable(s): NAME [NAME ...]
#   pre-commit: skill frontmatter check failed: <repo-relative path> ...
#   pre-commit: WARNING black not installed ...
# tests/test_ci_gates.py pins the same strings in the hook text.
MSG_NEW_SHAPES = "staged diff contains a JWT or a credentialed URL"
MSG_ENV_VALUE = "staged diff contains the value of .env variable(s):"
MSG_SKILL = "skill frontmatter check failed:"
MSG_BLACK_MISSING = "WARNING black not installed"

SH = shutil.which("sh")
_DASH = shutil.which("dash")
if _DASH is None and os.path.exists("/usr/bin/dash"):
    _DASH = "/usr/bin/dash"


def _shell_ids() -> list:
    ids = ["sh"]
    if SH and _DASH and os.path.realpath(_DASH) != os.path.realpath(SH):
        ids.append("dash")
    return ids


SHELLS = {"sh": SH, "dash": _DASH}


# ---------------------------------------------------------------------------
# Runtime-built sentinels and FAKE .env values (never literals)
# ---------------------------------------------------------------------------


def _fake(seed: str, n: int) -> str:
    """A deterministic fake value of exactly ``n`` characters."""
    return (seed + "Q7x" * n)[:n]


def _sk() -> str:
    return "sk" + "-" + "proj" + "Ab3x" * 5


def _akia() -> str:
    return "AK" + "IA" + "IOSFODNN" + "7EXAMPLE"


def _slack() -> str:
    return "xo" + "xb" + "-" + "1234567890" + "-abcdef"


def _private_key_header() -> str:
    return "-" * 5 + "BEGIN " + "OPENSSH " + "PRIVATE KEY" + "-" * 5


def _jwt() -> str:
    return (
        "ey"
        + "J"
        + "hbGciOiJIUz"
        + "."
        + "eyJzdWIiOi"
        + "IxMjM0In0"
        + "."
        + "c2lnbmF0dXJl"
        + "X3Rlc3Q"
    )


def _cred_url(password_len: int, host: str) -> str:
    return (
        "https"
        + "://"
        + "deploy"
        + ":"
        + _fake("pw", password_len)
        + "@"
        + host
        + "/hook"
    )


V_EXPORT_QUOTED = _fake("fk", 24)  # export FAKE_SERVICE_KEY="..."
V_LOWER_16 = _fake("lw", 16)  # fake_api_token=...  (exactly the minimum)
V_SINGLE_QUOTED = _fake("sq", 20)  # DB_PASSWORD='...'
V_SHORT_15 = _fake("sh", 15)  # SHORT_SECRET=...   (one below the minimum)
URL_PASSWORD = _fake("up", 14)
URL_VALUE = (
    "postgres"
    + "ql"
    + "://"
    + "svc_user"
    + ":"
    + URL_PASSWORD
    + "@"
    + "db.internal.example"
    + "/app"
)


def _fake_env_bytes() -> bytes:
    """A FAKE .env with CRLF endings and the export / quoted / lower-case forms
    of correction 10, plus a credentialed URL under a neutral name (TR5)."""
    lines = [
        "# FAKE .env written by tests/test_precommit_hook.py",
        "",
        'export FAKE_SERVICE_KEY="' + V_EXPORT_QUOTED + '"',
        "fake_api_token=" + V_LOWER_16,
        "DB_PASSWORD='" + V_SINGLE_QUOTED + "'",
        "SHORT_SECRET=" + V_SHORT_15,
        "UPSTREAM_URL=" + URL_VALUE,
    ]
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


# ---------------------------------------------------------------------------
# The tmp repo and the hook run
# ---------------------------------------------------------------------------


def _hermetic_env(base: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    for key, sub in (
        ("HOME", "home"),
        ("XDG_CONFIG_HOME", "xdg"),
        ("TMPDIR", "t0bhooktmp"),
        ("BLACK_CACHE_DIR", "blackcache"),
    ):
        d = base / sub
        d.mkdir(parents=True, exist_ok=True)
        env[key] = str(d)
    # The hook's `python`, `ruff` and `black` are the ones of the interpreter
    # running this test (the pinned venv here, setup-python in CI).
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")
    return env


class HookRun:
    def __init__(self, rc: int, out: str):
        self.rc = rc
        self.out = out
        self.lines = [ln.rstrip("\r") for ln in out.splitlines()]

    def hook_messages(self) -> list:
        """Every "pre-commit: ..." message, cut from the prefix on. A tool that
        ends its output without a newline (py_compile's OSError text does) puts
        the hook's message mid-line, so the prefix is searched, not anchored."""
        return [ln[ln.index(PREFIX) :] for ln in self.lines if PREFIX in ln]

    def first_message(self, text: str):
        for msg in self.hook_messages():
            if msg.startswith(text):
                return msg
        return None

    def refusals(self) -> list:
        return [
            m
            for m in self.hook_messages()
            if not m.startswith(PREFIX + "WARNING")
            and not m.startswith(PREFIX + "NOTE")
        ]

    def explain(self) -> str:
        tail = [ln[:200] for ln in self.lines[-8:]]
        return "rc=%s; last output lines: %r" % (self.rc, tail)


class HookRepo:
    """A tmp repo whose first commit holds the hook (LF), a minimal
    pyproject.toml, a one-entry black allowlist, a .gitignore and base.txt.
    With ``template`` the repo is a byte copy of an already built one (the
    setup is the same for every scenario; copying saves three git spawns)."""

    def __init__(self, base: Path, template: Path | None = None):
        self.base = base
        self.root = base / "repo"
        self.env = _hermetic_env(base)
        self.hooktmp = Path(self.env["TMPDIR"])
        if template is not None:
            shutil.copytree(template, self.root)
            return
        self.root.mkdir()
        self.git("init", "-q")
        self.write(".githooks/pre-commit", HOOK.read_bytes().replace(b"\r\n", b"\n"))
        self.write("pyproject.toml", '[tool.ruff]\ntarget-version = "py312"\n')
        self.write(
            ".github/black-clean-paths.txt", "# allowlist of the tmp repo\nfmt.py\n"
        )
        self.write(".gitignore", ".env\n")
        self.write("base.txt", "base\n")
        self.git("add", ".")
        self.commit("init")

    def git(self, *args, cwd: Path | None = None) -> str:
        p = subprocess.run(
            ["git", *args],
            cwd=str(cwd or self.root),
            env=self.env,
            capture_output=True,
            timeout=60,
        )
        if p.returncode != 0:
            raise AssertionError(
                "harness: git %s failed rc=%s: %s"
                % (
                    " ".join(args),
                    p.returncode,
                    p.stderr.decode("utf-8", "replace")[-400:],
                )
            )
        return p.stdout.decode("utf-8", "replace")

    def commit(self, msg: str, cwd: Path | None = None) -> None:
        self.git(
            "-c",
            "user.email=t0b@example.invalid",
            "-c",
            "user.name=t0b",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--no-verify",
            "-m",
            msg,
            cwd=cwd,
        )

    def write(self, rel: str, data, root: Path | None = None) -> Path:
        path = (root or self.root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
        return path

    def stage(
        self, rel: str, data, force: bool = False, root: Path | None = None
    ) -> None:
        self.write(rel, data, root=root)
        self.git("add", *(["-f"] if force else []), "--", rel, cwd=root)

    def write_fake_env(self) -> None:
        (self.root / ".env").write_bytes(_fake_env_bytes())

    def run_hook(
        self,
        shell: str,
        cwd: Path | None = None,
        xtrace: bool = False,
        env: dict | None = None,
    ) -> HookRun:
        where = cwd or self.root
        argv = [SHELLS[shell]] + (["-x"] if xtrace else []) + [".githooks/pre-commit"]
        p = subprocess.run(
            argv, cwd=str(where), env=env or self.env, capture_output=True, timeout=90
        )
        run = HookRun(p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace"))
        leftovers = sorted(
            x.name for x in where.iterdir() if x.name.startswith(".merge_file_")
        )
        assert not leftovers, "hook left %s in the checkout root; %s" % (
            leftovers,
            run.explain(),
        )
        stray = sorted(x.name for x in self.hooktmp.iterdir())
        assert not stray, "hook left %s in its TMPDIR; %s" % (stray, run.explain())
        return run


def _assert_refused(run: HookRun, msg: str) -> str:
    line = run.first_message(PREFIX + msg)
    assert run.rc != 0 and line is not None, "expected the refusal %r; %s" % (
        PREFIX + msg,
        run.explain(),
    )
    return line


def _assert_passed(run: HookRun) -> None:
    assert run.rc == 0 and not run.refusals(), (
        "expected a pass with no refusal line; %s" % run.explain()
    )


def _assert_names_variable(run: HookRun, name: str, value: str) -> None:
    line = _assert_refused(run, MSG_ENV_VALUE)
    assert name.upper() in line.upper(), "the refusal does not name %s: %r" % (
        name,
        line,
    )
    for piece in (value, value[:12], value[-12:]):
        assert piece not in run.out, (
            "the hook output carries the value (or a 12-char piece) of %s" % name
        )


# ---------------------------------------------------------------------------
# Scenarios. "red_*" fail at base for the stated reason; "pin_*" pass at base
# and must keep passing.
# ---------------------------------------------------------------------------


def red_jwt_refused(r: HookRepo, shell: str) -> None:
    r.stage("cfg.txt", "token = " + _jwt() + "\n")
    _assert_refused(r.run_hook(shell), MSG_NEW_SHAPES)


def red_credurl_12_char_password_refused(r: HookRepo, shell: str) -> None:
    r.stage("cfg.txt", "url = " + _cred_url(12, "gw.test") + "\n")
    _assert_refused(r.run_hook(shell), MSG_NEW_SHAPES)


def red_nested_env_refused(r: HookRepo, shell: str) -> None:
    r.stage("sub/.env", "A=1\n", force=True)
    _assert_refused(r.run_hook(shell), MSG_ENV_FILE)


def red_git_mv_to_env_refused(r: HookRepo, shell: str) -> None:
    r.git("mv", "base.txt", ".env")
    _assert_refused(r.run_hook(shell), MSG_ENV_FILE)


def red_renamed_py_with_syntax_error_refused(r: HookRepo, shell: str) -> None:
    r.stage("m.py", "x = 1\n" * 20)
    r.commit("m")
    r.git("mv", "m.py", "n.py")
    r.stage("n.py", "x = 1\n" * 19 + "def f(:\n")
    _assert_refused(r.run_hook(shell), MSG_PY_SYNTAX)


def red_staged_syntax_error_with_fixed_working_copy_refused(
    r: HookRepo, shell: str
) -> None:
    r.stage("bad.py", "def f(:\n")
    r.write("bad.py", "def f():\n    pass\n")
    _assert_refused(r.run_hook(shell), MSG_PY_SYNTAX)


def red_staged_undefined_name_with_fixed_working_copy_refused(
    r: HookRepo, shell: str
) -> None:
    if shutil.which("ruff", path=r.env["PATH"]) is None:
        pytest.skip("ruff is not on the hook's PATH")
    r.stage("u.py", "print(undefined_name_q)\n")
    r.write("u.py", "undefined_name_q = 1\nprint(undefined_name_q)\n")
    _assert_refused(r.run_hook(shell), MSG_RUFF)


def red_staged_black_dirty_allowlisted_with_clean_working_copy_refused(
    r: HookRepo, shell: str
) -> None:
    if importlib.util.find_spec("black") is None:
        pytest.skip("black is not importable by the hook's python")
    r.stage("fmt.py", "x=1\n")
    r.write("fmt.py", "x = 1\n")
    _assert_refused(r.run_hook(shell), MSG_BLACK)


def red_env_value_export_quoted_refused(r: HookRepo, shell: str) -> None:
    r.write_fake_env()
    r.stage("cfg.txt", "a = '" + V_EXPORT_QUOTED + "'\n")
    _assert_names_variable(r.run_hook(shell), "FAKE_SERVICE_KEY", V_EXPORT_QUOTED)


def red_env_value_lower_case_name_16_chars_refused(r: HookRepo, shell: str) -> None:
    r.write_fake_env()
    r.stage("cfg.txt", "b = " + V_LOWER_16 + "\n")
    _assert_names_variable(r.run_hook(shell), "fake_api_token", V_LOWER_16)


def red_env_value_single_quoted_refused(r: HookRepo, shell: str) -> None:
    r.write_fake_env()
    r.stage("cfg.txt", 'c = "' + V_SINGLE_QUOTED + '"\n')
    _assert_names_variable(r.run_hook(shell), "DB_PASSWORD", V_SINGLE_QUOTED)


def red_env_value_under_xtrace_is_named_not_printed(r: HookRepo, shell: str) -> None:
    r.write_fake_env()
    r.stage("cfg.txt", "a = " + V_EXPORT_QUOTED + "\n")
    _assert_names_variable(
        r.run_hook(shell, xtrace=True), "FAKE_SERVICE_KEY", V_EXPORT_QUOTED
    )


def red_env_credurl_value_under_neutral_name_refused_without_echo(
    r: HookRepo, shell: str
) -> None:
    # TR5 puts a credentialed-URL .env value in the fixed-string pass whatever
    # its NAME. Under the TR4 order the correction-6 URL branch runs first and
    # matches every added line that carries such a value, so the refusal seen
    # here is the new-shapes one (recorded as a deviation in the RED report).
    r.write_fake_env()
    r.stage("cfg.txt", "dsn = " + URL_VALUE + "\n")
    run = r.run_hook(shell, xtrace=True)
    _assert_refused(run, MSG_NEW_SHAPES)
    assert URL_PASSWORD not in run.out, "the hook output carries the URL password"


def red_env_fallback_to_common_dir_from_linked_worktree(
    r: HookRepo, shell: str
) -> None:
    r.write_fake_env()
    wt = r.base / "linked"
    r.git("worktree", "add", "-q", "--detach", str(wt), "HEAD")
    assert not (wt / ".env").exists()
    r.stage("cfg.txt", "a = " + V_EXPORT_QUOTED + "\n", root=wt)
    _assert_names_variable(
        r.run_hook(shell, cwd=wt), "FAKE_SERVICE_KEY", V_EXPORT_QUOTED
    )


def red_black_absent_warns_and_passes(r: HookRepo, shell: str) -> None:
    shim = r.base / "shim"
    shim.mkdir()
    real_python = sys.executable.replace("\\", "/")
    (shim / "python").write_bytes(
        (
            "#!/bin/sh\n"
            'if [ "${1:-}" = "-m" ] && [ "${2:-}" = "black" ]; then\n'
            '  echo "No module named black" >&2\n'
            "  exit 1\n"
            "fi\n"
            'exec "' + real_python + '" "$@"\n'
        ).encode("utf-8")
    )
    os.chmod(shim / "python", 0o755)
    keep = [
        d
        for d in r.env["PATH"].split(os.pathsep)
        if d
        and not (
            os.path.exists(os.path.join(d, "black"))
            or os.path.exists(os.path.join(d, "black.exe"))
        )
    ]
    env = dict(r.env)
    env["PATH"] = os.pathsep.join([str(shim)] + keep)
    assert shutil.which("black", path=env["PATH"]) is None
    r.stage("fmt.py", "x = 1\n")
    run = r.run_hook(shell, env=env)
    _assert_passed(run)
    assert run.first_message(
        PREFIX + MSG_BLACK_MISSING
    ), "expected the warning %r; %s" % (
        PREFIX + MSG_BLACK_MISSING,
        run.explain(),
    )


def red_skill_md_bare_colon_value_refused(r: HookRepo, shell: str) -> None:
    # The working copy is fixed after staging: the step must read the STAGED
    # blob (spec correction 16), so a working-tree read cannot pass this.
    rel = ".claude/skills/demo/SKILL.md"
    head = "---\nname: demo\ndescription: a demo skill\n"
    value = "2026-07-04 (re-check 2026-09-29: channels)"
    r.stage(rel, head + "last_verified: " + value + "\n---\n\nbody\n")
    r.write(rel, head + 'last_verified: "' + value + '"\n---\n\nbody\n')
    line = _assert_refused(r.run_hook(shell), MSG_SKILL)
    assert rel in line, "the refusal does not name %s: %r" % (rel, line)


def red_skill_md_without_description_refused(r: HookRepo, shell: str) -> None:
    rel = ".claude/skills/nodesc/SKILL.md"
    r.stage(rel, "---\nname: nodesc\nlast_verified: 2026-10-03\n---\n\nbody\n")
    line = _assert_refused(r.run_hook(shell), MSG_SKILL)
    assert rel in line, "the refusal does not name %s: %r" % (rel, line)


def red_failing_run_on_nested_path_leaves_nothing_behind(
    r: HookRepo, shell: str
) -> None:
    # The leftover checks run inside run_hook after EVERY scenario; this one
    # makes the hook fail on a staged-only error two directories deep, after
    # the staged blobs have been materialised. (At base it is red because the
    # refusal is missing: base materialises nothing, so it cannot leave any.)
    r.stage("pkg/sub/bad.py", "def f(:\n")
    r.write("pkg/sub/bad.py", "def f():\n    pass\n")
    _assert_refused(r.run_hook(shell), MSG_PY_SYNTAX)


def red_staged_ok_with_broken_working_copy_passes(r: HookRepo, shell: str) -> None:
    r.stage("ok.py", "x = 1\n")
    r.write("ok.py", "def f(:\n")
    _assert_passed(r.run_hook(shell))


def red_path_with_space_passes(r: HookRepo, shell: str) -> None:
    r.stage("a b.py", "x = 1\n")
    _assert_passed(r.run_hook(shell))


def red_non_ascii_path_passes(r: HookRepo, shell: str) -> None:
    r.stage("caf" + chr(0xE9) + ".py", "x = 1\n")
    _assert_passed(r.run_hook(shell))


def pin_root_env_refused(r: HookRepo, shell: str) -> None:
    r.stage(".env", "A=1\n", force=True)
    _assert_refused(r.run_hook(shell), MSG_ENV_FILE)


def pin_sk_shape_refused(r: HookRepo, shell: str) -> None:
    r.stage("k.txt", "key = " + _sk() + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def pin_akia_shape_refused(r: HookRepo, shell: str) -> None:
    r.stage("k.txt", "id = " + _akia() + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def pin_slack_shape_refused(r: HookRepo, shell: str) -> None:
    r.stage("k.txt", "hook = " + _slack() + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def pin_private_key_header_refused(r: HookRepo, shell: str) -> None:
    r.stage("k.txt", _private_key_header() + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def pin_musk_slug_passes(r: HookRepo, shell: str) -> None:
    r.stage("u.txt", "om.swissarabian.com/products/musk-07-edp-body-lotion-gift-set\n")
    _assert_passed(r.run_hook(shell))


def pin_clean_change_passes(r: HookRepo, shell: str) -> None:
    r.stage("ok.py", "x = 1\n")
    _assert_passed(r.run_hook(shell))


def pin_credurl_11_char_password_on_test_host_passes(r: HookRepo, shell: str) -> None:
    r.stage("cfg.txt", "url = " + _cred_url(11, "gw.test") + "\n")
    _assert_passed(r.run_hook(shell))


def pin_env_value_15_chars_not_matched(r: HookRepo, shell: str) -> None:
    r.write_fake_env()
    r.stage("cfg.txt", "d = " + V_SHORT_15 + "\n")
    _assert_passed(r.run_hook(shell))


def pin_valid_skill_md_passes(r: HookRepo, shell: str) -> None:
    r.stage(
        ".claude/skills/fine/SKILL.md",
        '---\nname: fine\ndescription: a fine skill\nlast_verified: "2026-10-03 (x: y)"\n---\n\nbody\n',
    )
    _assert_passed(r.run_hook(shell))


SCENARIOS = {
    fn.__name__: fn
    for fn in (
        red_jwt_refused,
        red_credurl_12_char_password_refused,
        red_nested_env_refused,
        red_git_mv_to_env_refused,
        red_renamed_py_with_syntax_error_refused,
        red_staged_syntax_error_with_fixed_working_copy_refused,
        red_staged_undefined_name_with_fixed_working_copy_refused,
        red_staged_black_dirty_allowlisted_with_clean_working_copy_refused,
        red_env_value_export_quoted_refused,
        red_env_value_lower_case_name_16_chars_refused,
        red_env_value_single_quoted_refused,
        red_env_value_under_xtrace_is_named_not_printed,
        red_env_credurl_value_under_neutral_name_refused_without_echo,
        red_env_fallback_to_common_dir_from_linked_worktree,
        red_black_absent_warns_and_passes,
        red_skill_md_bare_colon_value_refused,
        red_skill_md_without_description_refused,
        red_failing_run_on_nested_path_leaves_nothing_behind,
        red_staged_ok_with_broken_working_copy_passes,
        red_path_with_space_passes,
        red_non_ascii_path_passes,
        pin_root_env_refused,
        pin_sk_shape_refused,
        pin_akia_shape_refused,
        pin_slack_shape_refused,
        pin_private_key_header_refused,
        pin_musk_slug_passes,
        pin_clean_change_passes,
        pin_credurl_11_char_password_on_test_host_passes,
        pin_env_value_15_chars_not_matched,
        pin_valid_skill_md_passes,
    )
}


@pytest.mark.skipif(SH is None, reason="no POSIX sh on PATH")
class TestPreCommitHook:
    @pytest.fixture(scope="class")
    def template(self, tmp_path_factory) -> Path:
        return HookRepo(tmp_path_factory.mktemp("t0b_hook_template")).root

    @pytest.fixture(params=_shell_ids())
    def shell(self, request) -> str:
        return request.param

    @pytest.mark.parametrize("scenario", list(SCENARIOS))
    def test_scenario(
        self, shell: str, scenario: str, template: Path, tmp_path: Path
    ) -> None:
        SCENARIOS[scenario](HookRepo(tmp_path, template), shell)
