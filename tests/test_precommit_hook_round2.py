"""Round-2 pins for `.githooks/pre-commit` (T0b Phase A, ruling TF2).

The Phase A adversaries found five defects that the first fix rounds closed;
each scenario below pins one of them so that reverting the fix turns it red:

- D1 (ruling TF1): the .env value pass used a `case` pattern over the whole
  staged diff held in a shell variable, and dash overflows its stack on such a
  pattern at about 1 MB, killing the hook with no message. The pass now feeds
  the counted entries and the diff through ONE pipe into awk. Pinned with
  about 1.2 MB of staged added text, with the .env value absent (the hook
  passes and prints nothing) and present (the NAMES-only refusal).
- M1: the skill frontmatter step ran BEFORE the secret checks, and PyYAML's
  error message quotes the offending line, so a credential on a frontmatter
  line was echoed before any secret check could refuse it.
- M3: the new-shapes branch dropped every diff line starting with "+++", so an
  added line whose content starts with "++" was never scanned.
- M4: a TAB between "=" and the value, or before an inline "# comment", hid
  the value from the .env parse.
- M6: on a case-insensitive file system a staged ".Env" is the .env file, and
  the refusal pattern was case-sensitive.

The round-2 adversary then found three more, pinned by the r3_ scenarios:

- MINOR-1: the pipeline's status was awk's alone, so a crash of the .env
  parse (dash segfaults on a .env line of about 1 MB) or a failed git diff
  left awk with a partial stream, no hit and exit 0: the commit passed with
  no message. The stream now ends with a Z line written only after a
  successful git diff, and awk exits 2 without it. Pinned with a grep shim
  that kills the parse mid-file and a git shim whose diff fails.
- MINOR-2: under allexport (sh -a) the parse variables were exported, so a
  .env value reached the ENVIRONMENT of the git and grep processes. Pinned
  with a git shim that reports whether its environment carries the value.
- MINOR-3: an entry with no NAME (=<credentialed URL>) was refused with an
  empty name list. It is named (unnamed). The new-shapes branch refuses such
  a staged line first (TG3), so the pin blinds that branch with a grep shim.

The harness (tmp repo per scenario, hermetic environment, the LF copy of the
hook, the sh and dash columns, the leftover checks after every run) is the
one of tests/test_precommit_hook.py, imported. Every credential-shaped
sentinel and every FAKE .env value is built at runtime; no 12-character piece
of any of them may appear in the hook's output.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.test_precommit_hook import (
    MSG_ENV_FILE,
    MSG_ENV_VALUE,
    MSG_NEW_SHAPES,
    MSG_SKILL,
    PREFIX,
    SH,
    SHELLS,
    URL_VALUE,
    HookRepo,
    HookRun,
    _assert_refused,
    _fake,
    _jwt,
    _shell_ids,
)

MSG_ENV_CHECK_FAILED = "could not run the .env value check"

TAB = "\t"

# FAKE .env values (runtime-built; each 16 or more characters).
V_BULK = _fake("bk", 24)  # FAKE_BULK_KEY, the D1 value
V_OTHER = _fake("ot", 28)  # FAKE_OTHER_SECRET, never staged
V_TAB_LEAD = _fake("tl", 22)  # FAKE_TABLEAD_KEY=<TAB>value
V_TAB_COMMENT = _fake("tc", 21)  # FAKE_TABCOMMENT_TOKEN=value<TAB># comment
V_GLOB = "ab" + "\\" + "cd%s*[x]?" + "$" + "(nope)" + _fake("gl", 8)
V_TAG = "E" + _fake("tg", 20)  # starts with the stream's end-tag letter
# The allexport value carries a marker the git shim looks for in its own
# environment, so the shim never prints an environment value.
AX_MARKER = "Alx" + "PrtMk"
V_ALLEXPORT = _fake("ax", 9) + AX_MARKER + _fake("ay", 9)

# The exact argv of the staged-diff call of the new-shapes branch and of the
# .env value pass (the four-branch line runs git diff --cached -U0 only).
DIFF_ARGS = "diff --cached --no-color --no-ext-diff -U0"

# About 1.2 MB of plain added text: no credential shape, no .env value.
BULK_LINE = "bulk line %07d lorem ipsum dolor sit amet consectetur adipiscing elit\n"
BULK_BYTES = 1_200_000


def _bulk_text(tail: str = "") -> str:
    n = BULK_BYTES // len(BULK_LINE % 0) + 1
    return "".join(BULK_LINE % i for i in range(n)) + tail


def _env_bytes(lines: list) -> bytes:
    body = ["# FAKE .env written by tests/test_precommit_hook_round2.py"] + lines
    return ("\r\n".join(body) + "\r\n").encode("ascii")


def _write_env(r: HookRepo, lines: list) -> None:
    (r.root / ".env").write_bytes(_env_bytes(lines))


def _assert_no_piece(run: HookRun, secret: str, what: str) -> None:
    for i in range(len(secret) - 11):
        assert secret[i : i + 12] not in run.out, (
            "the hook output carries a 12-character piece of %s" % what
        )


def _shim(r: HookRepo, tool: str, body: str, env: dict | None = None) -> dict:
    """Put an sh script named ``tool`` first on PATH and return the env. The
    script drops its own directory from PATH (the first entry), so ``exec
    tool`` inside ``body`` reaches the real one."""
    d = r.base / ("t0bshim_" + tool)
    d.mkdir()
    head = "#!/bin/sh\nPATH=${PATH#*t0bshim_%s:}\n" % tool
    (d / tool).write_bytes((head + body).encode("ascii"))
    os.chmod(d / tool, 0o755)
    env = dict(env or r.env)
    env["PATH"] = str(d) + os.pathsep + env["PATH"]
    return env


def _run_with_flags(r: HookRepo, shell: str, flags: list, env: dict) -> HookRun:
    """HookRepo.run_hook with extra shell flags (``-a``), same leftover checks."""
    argv = [SHELLS[shell]] + flags + [".githooks/pre-commit"]
    p = subprocess.run(argv, cwd=str(r.root), env=env, capture_output=True, timeout=90)
    run = HookRun(p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace"))
    left = sorted(x.name for x in r.root.iterdir() if x.name.startswith(".merge_file_"))
    assert not left, "hook left %s in the checkout root; %s" % (left, run.explain())
    stray = sorted(x.name for x in r.hooktmp.iterdir())
    assert not stray, "hook left %s in its TMPDIR; %s" % (stray, run.explain())
    return run


def _assert_names_only(run: HookRun, names: list, values: list) -> None:
    line = _assert_refused(run, MSG_ENV_VALUE)
    printed = line[len(PREFIX + MSG_ENV_VALUE) :].split()
    assert printed == names, "expected the NAMES %r only, got %d word(s): %r" % (
        names,
        len(printed),
        [w if w in names else "<not a name>" for w in printed],
    )
    for value in values:
        _assert_no_piece(run, value, "a .env value")


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def d1_bulk_text_without_the_value_passes_with_no_message(
    r: HookRepo, shell: str
) -> None:
    _write_env(r, ["FAKE_BULK_KEY=" + V_BULK, "FAKE_OTHER_SECRET=" + V_OTHER])
    r.stage("docs/bulk.txt", _bulk_text())
    run = r.run_hook(shell)
    assert run.rc == 0 and run.hook_messages() == [], (
        "expected rc 0 and no hook message on ~1.2 MB of staged text; %s"
        % run.explain()
    )
    for value in (V_BULK, V_OTHER):
        _assert_no_piece(run, value, "a .env value")


def d1_bulk_text_with_the_value_is_refused_by_name_only(
    r: HookRepo, shell: str
) -> None:
    _write_env(r, ["FAKE_BULK_KEY=" + V_BULK, "FAKE_OTHER_SECRET=" + V_OTHER])
    r.stage("docs/bulk.txt", _bulk_text("tail = " + V_BULK + "\n"))
    _assert_names_only(r.run_hook(shell), ["FAKE_BULK_KEY"], [V_BULK, V_OTHER])


def d1_plusplus_line_with_the_value_is_refused(r: HookRepo, shell: str) -> None:
    # The value pass takes the added lines the way the new-shapes branch does:
    # a line whose CONTENT starts with "++" is a "+++" line in the diff body.
    _write_env(r, ["FAKE_BULK_KEY=" + V_BULK])
    r.stage("cfg.txt", "++" + V_BULK + "\n")
    _assert_names_only(r.run_hook(shell), ["FAKE_BULK_KEY"], [V_BULK])


def d1_special_characters_literal_and_prefix_is_not_a_hit(
    r: HookRepo, shell: str
) -> None:
    # Backslash, %, glob characters and $( in a value are matched literally;
    # a value that starts with the end-tag letter is still a value; a longer
    # value of which only a prefix is staged is NOT named.
    _write_env(
        r,
        [
            "FAKE_GLOB_TOKEN=" + V_GLOB,
            'FAKE_LONGER_SECRET="' + V_GLOB + 'Xtail"',
            "FAKE_TAG_KEY=" + V_TAG,
        ],
    )
    r.stage("cfg.txt", "g = " + V_GLOB + "\nt = " + V_TAG + "\n")
    _assert_names_only(
        r.run_hook(shell), ["FAKE_GLOB_TOKEN", "FAKE_TAG_KEY"], [V_GLOB, V_TAG]
    )


def d1_failed_awk_refuses_the_commit(r: HookRepo, shell: str) -> None:
    # A value check that cannot run must not pass silently.
    shim = r.base / "awkshim"
    shim.mkdir()
    (shim / "awk").write_bytes(b"#!/bin/sh\ncat >/dev/null\nexit 2\n")
    os.chmod(shim / "awk", 0o755)
    env = dict(r.env)
    env["PATH"] = str(shim) + os.pathsep + env["PATH"]
    _write_env(r, ["FAKE_BULK_KEY=" + V_BULK])
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_ENV_CHECK_FAILED)
    _assert_no_piece(run, V_BULK, "a .env value")


def m1_skill_frontmatter_jwt_is_refused_by_the_secret_check(
    r: HookRepo, shell: str
) -> None:
    jwt = _jwt()
    rel = ".claude/skills/demo/SKILL.md"
    r.stage(
        rel,
        "---\nname: demo\ndescription: use token: " + jwt + " here\n---\n\nbody\n",
    )
    run = r.run_hook(shell)
    _assert_refused(run, MSG_NEW_SHAPES)
    assert run.first_message(PREFIX + MSG_SKILL) is None, run.explain()
    _assert_no_piece(run, jwt, "the JWT")


def m1_skill_parse_error_does_not_quote_the_line(r: HookRepo, shell: str) -> None:
    marker = "Zq" + "marker" + "Wordq" + "Zq"
    rel = ".claude/skills/demo/SKILL.md"
    r.stage(
        rel,
        "---\nname: demo\ndescription: a demo skill\n"
        "last_verified: 2026-07-04 (" + marker + ": channels)\n---\n\nbody\n",
    )
    run = r.run_hook(shell)
    line = _assert_refused(run, MSG_SKILL)
    assert rel in line, run.explain()
    assert marker not in run.out, "the parse error quotes the frontmatter line"


def m3_plusplus_jwt_line_is_refused_by_the_new_shapes_branch(
    r: HookRepo, shell: str
) -> None:
    jwt = _jwt()
    r.stage("cfg.txt", "++" + jwt + "\n")
    run = r.run_hook(shell)
    _assert_refused(run, MSG_NEW_SHAPES)
    _assert_no_piece(run, jwt, "the JWT")


def m4_tab_after_equals_value_is_refused(r: HookRepo, shell: str) -> None:
    _write_env(r, ["FAKE_TABLEAD_KEY=" + TAB + V_TAB_LEAD])
    r.stage("cfg.txt", "a = " + V_TAB_LEAD + "\n")
    _assert_names_only(r.run_hook(shell), ["FAKE_TABLEAD_KEY"], [V_TAB_LEAD])


def m4_tab_before_inline_comment_value_is_refused(r: HookRepo, shell: str) -> None:
    _write_env(r, ["FAKE_TABCOMMENT_TOKEN=" + V_TAB_COMMENT + TAB + "# a comment"])
    r.stage("cfg.txt", "a = " + V_TAB_COMMENT + "\n")
    _assert_names_only(r.run_hook(shell), ["FAKE_TABCOMMENT_TOKEN"], [V_TAB_COMMENT])


def m6_git_mv_to_upper_case_env_is_refused(r: HookRepo, shell: str) -> None:
    r.git("mv", "base.txt", ".Env")
    _assert_refused(r.run_hook(shell), MSG_ENV_FILE)


def r3_parse_crash_refuses_the_commit(r: HookRepo, shell: str) -> None:
    # The credentialed-URL test is the only external call inside the .env
    # parse; the shim kills the shell that runs the parse there, after the
    # FAKE_BULK_KEY entry went into the pipe (what a dash segfault on a huge
    # .env line does). The staged line carries that value.
    env = _shim(
        r,
        "grep",
        'if [ "$1" = "-qE" ]; then\n'
        "  case $2 in\n"
        '    "[A-Za-z][A-Za-z0-9+.-]*://"*) kill -9 "$PPID"; exit 1 ;;\n'
        "  esac\n"
        "fi\n"
        'exec grep "$@"\n',
    )
    _write_env(r, ["FAKE_BULK_KEY=" + V_BULK, "UPSTREAM_URL=" + URL_VALUE])
    r.stage("cfg.txt", "a = " + V_BULK + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_ENV_CHECK_FAILED)
    _assert_no_piece(run, V_BULK, "a .env value")


def r3_failed_git_diff_refuses_the_commit(r: HookRepo, shell: str) -> None:
    env = _shim(
        r,
        "git",
        'case " $* " in\n'
        '  *" ' + DIFF_ARGS + ' "*) echo "git shim: diff failed" >&2; exit 128 ;;\n'
        "esac\n"
        'exec git "$@"\n',
    )
    _write_env(r, ["FAKE_BULK_KEY=" + V_BULK])
    r.stage("cfg.txt", "a = " + V_BULK + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_ENV_CHECK_FAILED)
    _assert_no_piece(run, V_BULK, "a .env value")


def r3_allexport_keeps_values_out_of_child_environments(
    r: HookRepo, shell: str
) -> None:
    # Under sh -a the git diff on the left of the value pipe would inherit
    # the last parsed value; the shim reports only whether the marker is in
    # its environment, never the environment itself.
    env = _shim(
        r,
        "git",
        'case " $* " in\n'
        '  *" ' + DIFF_ARGS + ' "*)\n'
        '    echo "T0B-SHIM-RAN" >&2\n'
        '    if env | grep -q "' + AX_MARKER + '"; then echo "T0B-ENV-LEAK" >&2; fi ;;\n'
        "esac\n"
        'exec git "$@"\n',
    )
    _write_env(r, ["FAKE_ALLEXPORT_KEY=" + V_ALLEXPORT])
    r.stage("cfg.txt", "plain text\n")
    run = _run_with_flags(r, shell, ["-a"], env)
    assert run.rc == 0 and run.refusals() == [], run.explain()
    assert run.out.count("T0B-SHIM-RAN") == 2, (
        "the shim did not see both staged-diff calls; %s" % run.explain()
    )
    assert "T0B-ENV-LEAK" not in run.out, (
        "a .env value is in the environment of git diff under sh -a"
    )
    _assert_no_piece(run, V_ALLEXPORT, "a .env value")


def r3_unnamed_credurl_entry_is_named_unnamed(r: HookRepo, shell: str) -> None:
    # The new-shapes branch (grep -qE -e JWT -e URL) would refuse the staged
    # URL first; the shim blinds that one call so the value pass is reached.
    env = _shim(
        r,
        "grep",
        'if [ "$1" = "-qE" ] && [ "$2" = "-e" ]; then cat >/dev/null; exit 1; fi\n'
        'exec grep "$@"\n',
    )
    _write_env(r, ["=" + URL_VALUE])
    r.stage("cfg.txt", "u = " + URL_VALUE + "\n")
    _assert_names_only(r.run_hook(shell, env=env), ["(unnamed)"], [URL_VALUE])


SCENARIOS = {
    fn.__name__: fn
    for fn in (
        d1_bulk_text_without_the_value_passes_with_no_message,
        d1_bulk_text_with_the_value_is_refused_by_name_only,
        d1_plusplus_line_with_the_value_is_refused,
        d1_special_characters_literal_and_prefix_is_not_a_hit,
        d1_failed_awk_refuses_the_commit,
        m1_skill_frontmatter_jwt_is_refused_by_the_secret_check,
        m1_skill_parse_error_does_not_quote_the_line,
        m3_plusplus_jwt_line_is_refused_by_the_new_shapes_branch,
        m4_tab_after_equals_value_is_refused,
        m4_tab_before_inline_comment_value_is_refused,
        m6_git_mv_to_upper_case_env_is_refused,
        r3_parse_crash_refuses_the_commit,
        r3_failed_git_diff_refuses_the_commit,
        r3_allexport_keeps_values_out_of_child_environments,
        r3_unnamed_credurl_entry_is_named_unnamed,
    )
}


@pytest.mark.skipif(SH is None, reason="no POSIX sh on PATH")
class TestPreCommitHookRound2:
    @pytest.fixture(scope="class")
    def template(self, tmp_path_factory) -> Path:
        return HookRepo(tmp_path_factory.mktemp("t0b_round2_template")).root

    @pytest.fixture(params=_shell_ids())
    def shell(self, request) -> str:
        return request.param

    @pytest.mark.parametrize("scenario", list(SCENARIOS))
    def test_scenario(
        self, shell: str, scenario: str, template: Path, tmp_path: Path
    ) -> None:
        SCENARIOS[scenario](HookRepo(tmp_path, template), shell)
