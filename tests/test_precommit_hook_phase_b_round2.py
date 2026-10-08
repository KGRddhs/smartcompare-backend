"""Round-2 pins of T0b Phase B: the fix round after the two adversaries.

One new file; the five frozen Phase A / Phase B test files do not change.
Each scenario names the adversary finding it pins:

- A1 (additivity): a user's external diff (diff.external, or a diff driver
  with a command) that prints decoded content as + lines was read by the old
  four-branch line (`git diff --cached -U0`); the staged-diff file now also
  carries that porcelain view, so the four-branch check sees it again.
- B3: with awk dead or missing and no .env, steps 4 and 4a still refuse
  (the old grep selection reads the staged-diff file).
- A3: an image whose extension is upper case (IMG_0001.PNG) is an image.
- A4: a typechange (a symlink replaced by a binary blob) reaches the binary
  refusal.
- B5: a TMPDIR that does not exist no longer refuses a clean commit.
- B7: pins for hook mutants the frozen nodes did not kill (magic bytes, the
  .ts ESLint pathspec, an empty gitleaks report, a failing raw view, a staged
  .gitleaks.toml edit).
- B6: four allowlist widenings of .gitleaks.toml (real gitleaks; skips
  without it, as in CI).
- B2 / A2: the ci.yml secret-scan step, executed under sh (and dash) with a
  gitleaks shim: the event ranges, the config read from the range base (the
  default rules written out when the base has none), the .gitleaksignore
  guard, a range end missing from the clone, an ERR line, the rotate-first
  message, and no `||` after the install checks.

Round 3 (rulings TBF1-TBF9, after the fix round):
- TBF1 (B1): gitleaks that logs an ERR line and exits 0 refuses; INF and WRN
  lines with exit 0 pass (a shim, and the real tool where installed).
- TBF2 (A2, hook half): the hook always passes --config; the two Phase B
  nodes that pinned "no --config when HEAD has none" were amended in place.
- TBF5 (a): docs/x.ttf is outside the binary allowlist (a static sample).
- TBF5 (c): the by-path ESLint call takes at most 64 paths.

Round 4 (the final adversary, findings F1 to F4):
- F1: steps 4 and 4a keep the old grep-only refusals whatever awk does: a
  dead awk with an allowlisted image or font staged (a NUL in the --text
  views hid every later line from grep), and an awk that works on stdin but
  fails on a file (with and without a .env); a dead awk under a UTF-8 locale
  with an invalid UTF-8 byte on a line before the key (a pin: grep drops
  only the line that holds such a byte).
- F2: the ci.yml scan runs gitleaks with --no-color, so its ERR test can
  match the real tool's log (a shim, and the real tool where installed).
  The CI shim writes its ERR level ANSI-coloured, as 8.30.1 does, unless
  its argv carries --no-color (TBF11).
- F3: a PR base missing from the clone fails the job before gitleaks runs.
- F4: every upper-case image and font extension row has a pass node.

Round 5 (ruling TBF21, after the round-5 adversary, findings R5-1 to R5-3):
- R5-1: with a dead awk the backstop still refuses an sk- key and an xoxb-
  token (both base refusals) and a credentialed URL.
- R5-2: a dead awk under a UTF-8 locale with an invalid UTF-8 byte on the
  SAME line as the key (TBF14 m4: the backstop's LC_ALL=C); the same line
  decoded by a diff driver command (the backstop's own reader of the
  external-diff view, under LC_ALL=C); a textconv driver that hides the key
  (the backstop's reader of the staged-diff file).
- R5-3: a commit that removes a committed key line passes (with and without
  a dead awk), and so does a new file whose path holds an sk- word.

Security: every credential-shaped sentinel is built at runtime; no real .env
is opened (the hermetic environment of the Phase A harness keeps every hook
run inside its tmp repo); gitleaks runs with --redact.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.test_gitleaks_config import GITLEAKS as GL_REAL
from tests.test_gitleaks_config import GlRepo, _config_path, _no_piece
from tests.test_precommit_hook import (
    MSG_CREDENTIAL,
    MSG_NEW_SHAPES,
    REPO_ROOT,
    SH,
    SHELLS,
    HookRepo,
    HookRun,
    _akia,
    _assert_passed,
    _assert_refused,
    _cred_url,
    _hermetic_env,
    _jwt,
    _private_key_header,
    _shell_ids,
    _sk,
    _slack,
)
from tests.test_precommit_hook_phase_b import (
    GIF,
    GL_SHIM,
    JPEG,
    MSG_DIFF_FAILED,
    MSG_ESLINT,
    MSG_GITLEAKS_NO_REPORT,
    OTF,
    PNG,
    WEBP,
    GlLog,
    _assert_binary_refused,
    _eslint_setup,
    _ghp,
    _gitleaks_shim,
    _node_calls,
    _posix,
    _rot13,
    _without_gitleaks,
)
from tests.test_precommit_hook_round2 import _assert_no_piece, _shim
from tests.test_secret_scan_static import _admitted, _binary_allowlist

CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"

# git calls an external diff as: path old-file old-hex old-mode new-file
# new-hex new-mode. This one prints the NEW file decoded (rot13), each line
# with a leading +, like a decrypting diff tool would.
EXT_SH = "#!/bin/sh\nsed 's/^/+/' \"$5\" | tr 'A-Za-z' 'N-ZA-Mn-za-m'\n"
FAIL_SH = "#!/bin/sh\nexit 3\n"


def _utf16_dump(text: str) -> bytes:
    return text.encode("utf-16")


# ---------------------------------------------------------------------------
# A1: the external-diff view (additivity)
# ---------------------------------------------------------------------------


def a1_ext_diff_reveal_four_branch(r: HookRepo, shell: str) -> None:
    r.write("ext.sh", EXT_SH)
    r.git("config", "diff.external", "sh " + _posix(r.root / "ext.sh"))
    key = _akia()
    r.stage("conf/a.cfg", "aws_id = " + _rot13(key) + "\n")
    run = r.run_hook(shell)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the decoded key")


def a1_driver_command_reveal_four_branch(r: HookRepo, shell: str) -> None:
    r.write("ext.sh", EXT_SH)
    r.write(".git/info/attributes", "*.cfg diff=dec\n")
    r.git("config", "diff.dec.command", "sh " + _posix(r.root / "ext.sh"))
    key = _akia()
    r.stage("conf/b.cfg", "aws_id = " + _rot13(key) + "\n")
    run = r.run_hook(shell)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the decoded key")


def a1_ext_diff_after_a_header_only_file(r: HookRepo, shell: str) -> None:
    # An empty new file has a header and no hunk; the external tool's lines
    # that follow it in the porcelain view must still be read (the old line
    # had no header state).
    r.write("ext.sh", EXT_SH)
    r.write(".git/info/attributes", "*.cfg diff=dec\n")
    r.git("config", "diff.dec.command", "sh " + _posix(r.root / "ext.sh"))
    r.stage("a_empty.txt", "")
    r.stage("b.cfg", "aws_id = " + _rot13(_akia()) + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def a1_ext_diff_after_a_trailing_header_only_file(r: HookRepo, shell: str) -> None:
    # The empty file sorts LAST, so the views before the external-diff lines
    # end inside its header block: the appended lines must still be read.
    r.write("ext.sh", EXT_SH)
    r.write(".git/info/attributes", "*.cfg diff=dec\n")
    r.git("config", "diff.dec.command", "sh " + _posix(r.root / "ext.sh"))
    r.stage("b.cfg", "aws_id = " + _rot13(_akia()) + "\n")
    r.stage("z_empty.txt", "")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def a1_failing_external_diff_refuses(r: HookRepo, shell: str) -> None:
    # The TB2 consequence, extended to the third view: a failing external
    # diff is a failed git diff (like a failing textconv).
    r.write("fail.sh", FAIL_SH)
    r.git("config", "diff.external", "sh " + _posix(r.root / "fail.sh"))
    r.stage("k.txt", "plain text\n")
    _assert_refused(r.run_hook(shell), MSG_DIFF_FAILED)


def pin_a1_trivial_external_diff_passes(r: HookRepo, shell: str) -> None:
    r.git("config", "diff.external", "true")
    r.stage("k.txt", "plain text\n")
    _assert_passed(r.run_hook(shell))


# ---------------------------------------------------------------------------
# B3: a dead or missing awk with no .env
# ---------------------------------------------------------------------------


def _broken_awk(r: HookRepo, rc: int) -> dict:
    env = _shim(r, "awk", "exit %d\n" % rc)
    env["PATH"] = _without_gitleaks(env["PATH"])
    return env


def b3_dead_awk_without_env_four_branch_refuses(r: HookRepo, shell: str) -> None:
    env = _broken_awk(r, 2)
    key = _akia()
    r.stage("k.txt", "id = " + key + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the staged key")


def b3_missing_awk_without_env_new_shapes_refuses(r: HookRepo, shell: str) -> None:
    env = _broken_awk(r, 127)
    jwt = _jwt()
    r.stage("t.txt", "token = " + jwt + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_NEW_SHAPES)
    _assert_no_piece(run, jwt, "the JWT")


def pin_b3_dead_awk_clean_commit_passes(r: HookRepo, shell: str) -> None:
    env = _broken_awk(r, 2)
    r.stage("k.txt", "plain text\n")
    _assert_passed(r.run_hook(shell, env=env))


# ---------------------------------------------------------------------------
# A3: upper-case image extensions; A4: typechange; B5: missing TMPDIR
# ---------------------------------------------------------------------------


def a3_png_upper_case_extension_passes(r: HookRepo, shell: str) -> None:
    r.stage("docs/investigations/s73/screens/IMG_0001.PNG", PNG)
    _assert_passed(r.run_hook(shell))


def a3_jpg_upper_case_extension_passes(r: HookRepo, shell: str) -> None:
    r.stage("SmartCompareApp/assets/images/IMG_0002.JPG", JPEG)
    _assert_passed(r.run_hook(shell))


def pin_a3_upper_case_png_dump_refused(r: HookRepo, shell: str) -> None:
    r.stage("docs/x/DUMP.PNG", _utf16_dump("id = " + _akia() + "\n"))
    _assert_binary_refused(r.run_hook(shell), "docs/x/DUMP.PNG")


def a4_typechange_to_utf16_blob_refused(r: HookRepo, shell: str) -> None:
    target = r.base / "target.txt"
    target.write_bytes(b"base.txt")
    sym = r.git("hash-object", "-w", str(target)).strip()
    r.git("update-index", "--add", "--cacheinfo", "120000," + sym + ",link")
    r.commit("symlink")
    blob = r.base / "dump.bin"
    blob.write_bytes(_utf16_dump("id = " + _akia() + "\n"))
    sha = r.git("hash-object", "-w", str(blob)).strip()
    r.git("update-index", "--cacheinfo", "100644," + sha + ",link")
    status = r.git("diff", "--cached", "--name-status")
    assert status.startswith("T"), "harness: no typechange staged: %r" % status
    _assert_binary_refused(r.run_hook(shell), "link")


def b5_missing_tmpdir_clean_commit_passes(r: HookRepo, shell: str) -> None:
    env = dict(r.env)
    env["TMPDIR"] = str(r.base / "no_such_tmpdir")
    r.stage("k.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    _assert_passed(run)
    gitdir = r.root / ".git"
    left = sorted(x.name for x in gitdir.iterdir() if "qaren-precommit" in x.name)
    assert not left, "the fallback temp dir was left in .git: %s" % left


# ---------------------------------------------------------------------------
# B7: mutants the frozen nodes did not kill
# ---------------------------------------------------------------------------


def b7_gif_dump_refused(r: HookRepo, shell: str) -> None:
    r.stage("docs/x/d.gif", _utf16_dump("id = " + _akia() + "\n"))
    _assert_binary_refused(r.run_hook(shell), "docs/x/d.gif")


def b7_webp_dump_refused(r: HookRepo, shell: str) -> None:
    r.stage("docs/x/d.webp", _utf16_dump("id = " + _akia() + "\n"))
    _assert_binary_refused(r.run_hook(shell), "docs/x/d.webp")


def b7_png_with_only_four_magic_bytes_refused(r: HookRepo, shell: str) -> None:
    data = PNG[:4] + b"\x00\x00\x00\x00" + _utf16_dump("id = " + _akia() + "\n")
    r.stage("docs/x/p.png", data)
    _assert_binary_refused(r.run_hook(shell), "docs/x/p.png")


def b7_eslint_lints_a_staged_ts_file(r: HookRepo, shell: str) -> None:
    env, log = _eslint_setup(r, rc=0)
    rel = "SmartCompareApp/src/services/S1.ts"
    r.stage(rel, "export const s1 = 1;\n")
    run = r.run_hook(shell, env=env)
    _assert_passed(run)
    calls = _node_calls(log)
    assert len(calls) == 1, "expected one eslint call; %r; %s" % (calls, run.explain())
    argv, pwd, stdin = calls[0]
    assert "src/services/S1.ts" in argv and stdin is None, calls
    assert pwd == "SmartCompareApp", calls


def b7_gitleaks_empty_report_gets_the_no_report_wording(
    r: HookRepo, shell: str
) -> None:
    log = r.base / "gitleaks_shim.log"
    body = (
        GL_SHIM.replace("@LOG@", '"' + _posix(log) + '"')
        .replace("@MARKCHECK@", "")
        .replace("@REPORT@", 'if [ -n "$rep" ]; then : > "$rep"; fi')
        .replace("@RC@", "1")
    )
    env = _shim(r, "gitleaks", body)
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    assert GlLog(log).calls >= 1, run.explain()
    _assert_refused(run, MSG_GITLEAKS_NO_REPORT)


def b7_failing_raw_view_refuses(r: HookRepo, shell: str) -> None:
    env = _shim(
        r,
        "git",
        'case " $* " in\n'
        '  *" -U0 --text --no-textconv "*) echo "git shim: raw view failed" >&2;'
        " exit 128 ;;\n"
        "esac\n"
        'exec git "$@"\n',
    )
    r.stage("k.txt", "plain text\n")
    _assert_refused(r.run_hook(shell, env=env), MSG_DIFF_FAILED)


def b7_staged_config_edit_does_not_judge_itself(r: HookRepo, shell: str) -> None:
    r.stage(".gitleaks.toml", "# head-marker-R2Q\n[extend]\nuseDefault = true\n")
    r.commit("cfg")
    r.stage(".gitleaks.toml", "# index-marker-R2Q\n[extend]\nuseDefault = true\n")
    env, log = _gitleaks_shim(r, rc=0)
    run = r.run_hook(shell, env=env)
    gl = GlLog(log)
    assert gl.calls >= 1, run.explain()
    _assert_passed(run)
    text = gl.config_text()
    assert "head-marker-R2Q" in text and "index-marker-R2Q" not in text, text[:200]


# ---------------------------------------------------------------------------
# TBF1 (B1): gitleaks that logs an error and exits 0
# ---------------------------------------------------------------------------

MSG_GITLEAKS_ERR_LOGGED = (
    "gitleaks refused the staged changes (it logged an error and exited 0, so it"
    " may have scanned nothing: run gitleaks git --pre-commit --staged by hand)"
)

# A textconv driver that writes a notice to stderr and exits 0: gitleaks
# 8.30.1 then logs ERR, exits 0 and reports nothing for the WHOLE commit
# (measured, adversary B H3b and fix round 2).
NOISY_SH = '#!/bin/sh\necho "driver notice" >&2\ncat "$1"\n'


def _gitleaks_stderr_shim(r: HookRepo, stderr_lines: list, rc: int = 0) -> tuple:
    """The Phase B gitleaks shim, writing ``stderr_lines`` to its stderr."""
    log = r.base / "gitleaks_shim.log"
    say = "\n".join("echo '%s' >&2" % ln for ln in stderr_lines)
    body = (
        GL_SHIM.replace("@LOG@", '"' + _posix(log) + '"')
        .replace("@MARKCHECK@", say)
        .replace("@REPORT@", "")
        .replace("@RC@", str(rc))
    )
    return _shim(r, "gitleaks", body), log


def tbf1_gitleaks_err_line_with_rc0_refuses(r: HookRepo, shell: str) -> None:
    env, log = _gitleaks_stderr_shim(
        r, ["9:00PM INF 0 commits scanned.", "9:00PM ERR [git] notice-T0BF1"]
    )
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    gl = GlLog(log)
    assert gl.calls >= 1, run.explain()
    _assert_refused(run, MSG_GITLEAKS_ERR_LOGGED)
    # An ERR line can quote git's own stderr: the hook never prints it.
    assert "notice-T0BF1" not in run.out, "the hook printed gitleaks' stderr"
    # Measured on 8.30.1: without --no-color the level is written as an
    # ANSI-coloured ERR even into a file, so a ' ERR ' test never matches.
    assert "--no-color" in gl.args(), "gitleaks runs with colour: %r" % gl.args()


def pin_tbf1_gitleaks_inf_and_wrn_lines_with_rc0_pass(r: HookRepo, shell: str) -> None:
    # At the default log level 8.30.1 writes INF lines on every run and a WRN
    # line with a finding (measured): only an ERR line refuses, never a
    # stderr that is merely not empty.
    env, log = _gitleaks_stderr_shim(
        r,
        [
            "9:00PM INF 0 commits scanned.",
            "9:00PM INF scanned ~12 bytes (12 bytes) in 357ms",
            "9:00PM INF no leaks found",
            "9:00PM WRN leaks found: 1",
        ],
    )
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    assert GlLog(log).calls >= 1, run.explain()
    _assert_passed(run)


def tbf1_real_gitleaks_error_with_rc0_refuses(r: HookRepo, shell: str) -> None:
    # The real tool (skips without it, as in CI): a noisy textconv driver on
    # one file blinds gitleaks for the commit, so a GitHub-token shape in
    # another file (only gitleaks knows the shape) passed with rc 0.
    if GL_REAL is None:
        pytest.skip("gitleaks not on PATH")
    r.write("noisy.sh", NOISY_SH)
    r.write(".git/info/attributes", "*.dat diff=noisy\n")
    r.git("config", "diff.noisy.textconv", "sh " + _posix(r.root / "noisy.sh"))
    r.stage("a.dat", "data\n")
    tok = _ghp()
    r.stage("g.txt", "gh_token = " + tok + "\n")
    run = r.run_hook(shell)
    _assert_refused(run, MSG_GITLEAKS_ERR_LOGGED)
    _assert_no_piece(run, tok, "the staged token")


# ---------------------------------------------------------------------------
# TBF5 (c): the by-path ESLint call is batched at 64 paths
# ---------------------------------------------------------------------------


def eslint_by_path_call_is_batched_at_64(r: HookRepo, shell: str) -> None:
    # The batching idiom of the Python steps: a Windows command line tops out
    # near 32k characters. 129 fully staged client files: the first call
    # takes B000-B063 and passes, the second takes B064-B127 and reports an
    # error (the shim fails on B064), which refuses before a third call.
    env, log = _eslint_setup(
        r, rc=0, say='case " $* " in *"/B064.tsx "*) exit 1 ;; esac'
    )
    rels = ["SmartCompareApp/src/screens/B%03d.tsx" % i for i in range(129)]
    for i, rel in enumerate(rels):
        r.write(rel, "export const b%d = 1;\n" % i)
    r.git("add", "--", "SmartCompareApp/src")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_ESLINT)
    calls = _node_calls(log)
    paths = [[a for a in argv if a.endswith(".tsx")] for argv, _, _ in calls]
    assert [len(p) for p in paths] == [64, 64], (
        "expected by-path calls of 64 then 64 paths: %r; %s"
        % ([len(p) for p in paths], run.explain())
    )
    want = [rel[len("SmartCompareApp/") :] for rel in rels]
    assert paths == [want[:64], want[64:128]], (paths[0][:2], paths[-1][:2])
    assert all(stdin is None and pwd == "SmartCompareApp" for _, pwd, stdin in calls)


SCENARIOS = {
    fn.__name__: fn
    for fn in (
        a1_ext_diff_reveal_four_branch,
        a1_driver_command_reveal_four_branch,
        a1_ext_diff_after_a_header_only_file,
        a1_ext_diff_after_a_trailing_header_only_file,
        a1_failing_external_diff_refuses,
        pin_a1_trivial_external_diff_passes,
        b3_dead_awk_without_env_four_branch_refuses,
        b3_missing_awk_without_env_new_shapes_refuses,
        pin_b3_dead_awk_clean_commit_passes,
        a3_png_upper_case_extension_passes,
        a3_jpg_upper_case_extension_passes,
        pin_a3_upper_case_png_dump_refused,
        a4_typechange_to_utf16_blob_refused,
        b5_missing_tmpdir_clean_commit_passes,
        b7_gif_dump_refused,
        b7_webp_dump_refused,
        b7_png_with_only_four_magic_bytes_refused,
        b7_eslint_lints_a_staged_ts_file,
        b7_gitleaks_empty_report_gets_the_no_report_wording,
        b7_failing_raw_view_refuses,
        b7_staged_config_edit_does_not_judge_itself,
        tbf1_gitleaks_err_line_with_rc0_refuses,
        pin_tbf1_gitleaks_inf_and_wrn_lines_with_rc0_pass,
        tbf1_real_gitleaks_error_with_rc0_refuses,
        eslint_by_path_call_is_batched_at_64,
    )
}


@pytest.mark.skipif(SH is None, reason="no POSIX sh on PATH")
class TestPreCommitHookPhaseBRound2:
    @pytest.fixture(scope="class")
    def template(self, tmp_path_factory) -> Path:
        return HookRepo(tmp_path_factory.mktemp("t0b_phase_b_r2_template")).root

    @pytest.fixture(params=_shell_ids())
    def shell(self, request) -> str:
        return request.param

    @pytest.mark.parametrize("scenario", list(SCENARIOS))
    def test_scenario(
        self, shell: str, scenario: str, template: Path, tmp_path: Path
    ) -> None:
        SCENARIOS[scenario](HookRepo(tmp_path, template), shell)


def test_binary_allowlist_refuses_a_font_under_docs():
    # TBF5 (a): the fonts row under docs/ is docs/claude-design-handoff/fonts
    # only (TBG1); a docs/*.ttf row survived every earlier node.
    assert not _admitted("docs/x.ttf", _binary_allowlist()), "docs/x.ttf is admitted"


# ---------------------------------------------------------------------------
# B6: allowlist widenings of .gitleaks.toml (real gitleaks, skip without it)
# ---------------------------------------------------------------------------


def _openai_text_key() -> str:
    return "s" + "k-" + "pRj4Kx9WqT2mZ7vL" + "0sYbN5hD3gF8cA1eU6iO"


def _opaque40() -> str:
    return "Zq8Lm3Tv7Xc1Bn5Hk9Wd" + "2Rf6Yp4Gs0Ju8Ea3Qo7N"


def _alnum32() -> str:
    return "Kd7Pq2Xw9Lm4Tz6B" + "v1Nc8Hr3Jf5Gy0Sa"


def _contains_test_marker() -> str:
    return "Xq9Fw2Lp7Rk4" + "test_" + "Mz8Vb3Nc6Hj1"


WIDENING_CASES = {
    "openai_text_with_a_real_length_key": (
        "notes.md",
        lambda: "Incorrect API key provided: " + _openai_text_key() + "\n",
        _openai_text_key,
    ),
    "access_token_40_char_opaque": (
        "resp.json",
        lambda: '{"access_token":"' + _opaque40() + '"}\n',
        _opaque40,
    ),
    "workflow_key_32_chars": (
        "wf.js",
        lambda: "{ key: '" + _alnum32() + "' }\n",
        _alnum32,
    ),
    "token_containing_test_underscore": (
        "cfg.txt",
        lambda: 'token = "' + _contains_test_marker() + '"\n',
        _contains_test_marker,
    ),
}


@pytest.mark.skipif(GL_REAL is None, reason="gitleaks not on PATH")
@pytest.mark.parametrize("case", sorted(WIDENING_CASES))
def test_repo_config_reports_beyond_each_narrow_allowlist(
    case: str, tmp_path: Path
) -> None:
    rel, body, secret = WIDENING_CASES[case]
    r = GlRepo(tmp_path)
    r.stage(rel, body())
    rc, rules, out = r.scan(_config_path())
    assert rc == 1 and rules, "the repo config hides %s: rc=%s rules=%s" % (
        case,
        rc,
        rules,
    )
    _no_piece(out, secret())


# ---------------------------------------------------------------------------
# B2 / A2: the ci.yml secret-scan step, executed with a gitleaks shim
# ---------------------------------------------------------------------------

ZERO_SHA = "0" * 40
DEFAULT_ONLY = "[extend]\nuseDefault = true"

CI_GL_SHIM = """#!/bin/sh
log=@LOG@
printf 'CALL\\n' >> "$log"
prev=""
colour=1
for a in "$@"; do
  printf 'ARG %s\\n' "$a" >> "$log"
  if [ "$prev" = "--config" ]; then
    printf 'CONFIG-BEGIN\\n' >> "$log"
    cat "$a" >> "$log"
    printf '\\nCONFIG-END\\n' >> "$log"
  fi
  if [ "$a" = "--no-color" ]; then colour=""; fi
  prev=$a
done
say() {
  :
  @SAY@
}
# TBF11: like 8.30.1 (measured), the log level is ANSI-coloured, even into
# a file, unless the call carries --no-color.
if [ -n "$colour" ]; then
  esc=$(printf '\\033')
  say "$@" 2>&1 | sed "s/ ERR / ${esc}[31mERR${esc}[0m /" >&2
else
  say "$@"
fi
exit @RC@
"""


def _scan_step() -> str:
    jobs = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))["jobs"]
    assert "secret-scan" in jobs, "ci.yml has no secret-scan job"
    runs = [
        str(s.get("run", ""))
        for s in jobs["secret-scan"]["steps"]
        if "--log-opts" in str(s.get("run", ""))
    ]
    assert len(runs) == 1, "expected one scan step, got %d" % len(runs)
    return runs[0]


def _install_step() -> str:
    jobs = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))["jobs"]
    runs = [
        str(s.get("run", ""))
        for s in jobs["secret-scan"]["steps"]
        if "sha256sum" in str(s.get("run", ""))
    ]
    assert len(runs) == 1, "expected one install step"
    return runs[0]


class CiRepo:
    def __init__(self, base: Path):
        self.base = base
        self.root = base / "repo"
        self.root.mkdir()
        self.env = _hermetic_env(base)
        self.runner_temp = base / "runner_temp"
        self.runner_temp.mkdir()
        self.log = base / "ci_gl.log"
        self.git("init", "-q")

    def git(self, *args: str) -> str:
        p = subprocess.run(
            ["git", *args],
            cwd=str(self.root),
            env=self.env,
            capture_output=True,
            timeout=60,
        )
        assert p.returncode == 0, "harness: git %s failed: %r" % (args, p.stderr[-300:])
        return p.stdout.decode("utf-8", "replace")

    def commit(self, files: dict, msg: str) -> str:
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
            self.git("add", "--", rel)
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
            "--allow-empty",
            "-m",
            msg,
        )
        return self.git("rev-parse", "HEAD").strip()

    def run_step(self, shell: str, event: dict, rc: int = 0, say: str = "") -> HookRun:
        shim = self.runner_temp / "gitleaks"
        shim.write_bytes(
            CI_GL_SHIM.replace("@LOG@", '"' + _posix(self.log) + '"')
            .replace("@SAY@", say)
            .replace("@RC@", str(rc))
            .encode("ascii")
        )
        os.chmod(shim, 0o755)
        script = self.base / "scan_step.sh"
        script.write_bytes(_scan_step().encode("utf-8"))
        env = dict(self.env)
        env.update(
            {
                "EVENT_NAME": "",
                "PR_BASE": "",
                "PR_HEAD": "",
                "PUSH_BEFORE": "",
                "PUSH_SHA": "",
            }
        )
        env.update(event)
        env["RUNNER_TEMP"] = _posix(self.runner_temp)
        p = subprocess.run(
            [SHELLS[shell], "-e", str(script)],
            cwd=str(self.root),
            env=env,
            capture_output=True,
            timeout=120,
        )
        return HookRun(p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace"))

    def gl(self) -> GlLog:
        return GlLog(self.log)


def _cfg(marker: str) -> str:
    return "# " + marker + "\n[extend]\nuseDefault = true\n"


def ci_pr_scans_base_to_head_with_the_base_config(c: CiRepo, shell: str) -> None:
    base = c.commit({".gitleaks.toml": _cfg("base-marker-CIQ")}, "base")
    head = c.commit({".gitleaks.toml": _cfg("head-marker-CIQ"), "a.txt": "a\n"}, "head")
    run = c.run_step(
        shell, {"EVENT_NAME": "pull_request", "PR_BASE": base, "PR_HEAD": head}
    )
    gl = c.gl()
    assert run.rc == 0 and gl.calls == 1, run.explain()
    args = gl.args()
    assert "--log-opts=" + base + ".." + head in args, args
    for flag in ("--redact", "--ignore-gitleaks-allow", "-v"):
        assert flag in args, args
    text = gl.config_text()
    assert "base-marker-CIQ" in text and "head-marker-CIQ" not in text, text[:200]


def ci_push_scans_before_to_sha(c: CiRepo, shell: str) -> None:
    before = c.commit({".gitleaks.toml": _cfg("before-marker-CIQ")}, "before")
    sha = c.commit({"a.txt": "a\n"}, "pushed")
    run = c.run_step(
        shell, {"EVENT_NAME": "push", "PUSH_BEFORE": before, "PUSH_SHA": sha}
    )
    gl = c.gl()
    assert run.rc == 0 and gl.calls == 1, run.explain()
    assert "--log-opts=" + before + ".." + sha in gl.args(), gl.args()
    assert "before-marker-CIQ" in gl.config_text()


def ci_new_branch_push_uses_the_default_rules(c: CiRepo, shell: str) -> None:
    # A2: with no config to read, gitleaks would load the SCANNED tree's own
    # .gitleaks.toml; the step must pass the default rules explicitly.
    sha = c.commit({".gitleaks.toml": _cfg("tree-marker-CIQ"), "a.txt": "a\n"}, "new")
    run = c.run_step(shell, {"EVENT_NAME": "push", "PUSH_BEFORE": ZERO_SHA, "PUSH_SHA": sha})
    gl = c.gl()
    assert run.rc == 0 and gl.calls == 1, run.explain()
    args = gl.args()
    assert "--log-opts=-1 " + sha in args, args
    assert "--config" in args, "no --config: gitleaks reads the scanned tree's file"
    assert gl.config_text().strip() == DEFAULT_ONLY, gl.config_text()[:200]


def ci_base_without_config_uses_the_default_rules(c: CiRepo, shell: str) -> None:
    before = c.commit({"base.txt": "b\n"}, "before")
    sha = c.commit({".gitleaks.toml": _cfg("tree-marker-CIQ")}, "adds config")
    run = c.run_step(
        shell, {"EVENT_NAME": "push", "PUSH_BEFORE": before, "PUSH_SHA": sha}
    )
    gl = c.gl()
    assert run.rc == 0 and gl.calls == 1, run.explain()
    assert "--config" in gl.args(), gl.args()
    assert gl.config_text().strip() == DEFAULT_ONLY, gl.config_text()[:200]


def ci_unreachable_range_end_fails_without_scanning(c: CiRepo, shell: str) -> None:
    sha = c.commit({"a.txt": "a\n"}, "pushed")
    gone = "1234567890abcdef" * 2 + "12345678"
    run = c.run_step(shell, {"EVENT_NAME": "push", "PUSH_BEFORE": gone, "PUSH_SHA": sha})
    assert run.rc != 0, "a range end missing from the clone must fail; " + run.explain()
    assert c.gl().calls == 0, "gitleaks scanned a range with a missing end"


def ci_tracked_gitleaksignore_fails(c: CiRepo, shell: str) -> None:
    base = c.commit({"a.txt": "a\n"}, "base")
    head = c.commit({".gitleaksignore": "a.txt:generic-api-key:1\n"}, "ignore")
    run = c.run_step(
        shell, {"EVENT_NAME": "pull_request", "PR_BASE": base, "PR_HEAD": head}
    )
    assert run.rc != 0 and c.gl().calls == 0, run.explain()


def ci_gitleaks_err_line_fails(c: CiRepo, shell: str) -> None:
    # B2: gitleaks 8.30.1 logs ERR and exits 0 when its git call fails.
    base = c.commit({"a.txt": "a\n"}, "base")
    head = c.commit({"b.txt": "b\n"}, "head")
    run = c.run_step(
        shell,
        {"EVENT_NAME": "pull_request", "PR_BASE": base, "PR_HEAD": head},
        rc=0,
        say='echo "1:00PM ERR [git] fatal: bad revision" >&2',
    )
    assert c.gl().calls == 1, run.explain()
    assert run.rc != 0, "an ERR line from gitleaks must fail the job; " + run.explain()


def ci_finding_says_rotate_first(c: CiRepo, shell: str) -> None:
    base = c.commit({"a.txt": "a\n"}, "base")
    head = c.commit({"b.txt": "b\n"}, "head")
    run = c.run_step(
        shell,
        {"EVENT_NAME": "pull_request", "PR_BASE": base, "PR_HEAD": head},
        rc=1,
    )
    assert run.rc != 0, run.explain()
    assert "ROTATE THE KEY FIRST" in run.out, run.explain()


CI_SCENARIOS = {
    fn.__name__: fn
    for fn in (
        ci_pr_scans_base_to_head_with_the_base_config,
        ci_push_scans_before_to_sha,
        ci_new_branch_push_uses_the_default_rules,
        ci_base_without_config_uses_the_default_rules,
        ci_unreachable_range_end_fails_without_scanning,
        ci_tracked_gitleaksignore_fails,
        ci_gitleaks_err_line_fails,
        ci_finding_says_rotate_first,
    )
}


@pytest.mark.skipif(SH is None, reason="no POSIX sh on PATH")
class TestSecretScanStep:
    @pytest.fixture(params=_shell_ids())
    def shell(self, request) -> str:
        return request.param

    @pytest.mark.parametrize("scenario", list(CI_SCENARIOS))
    def test_scenario(self, shell: str, scenario: str, tmp_path: Path) -> None:
        CI_SCENARIOS[scenario](CiRepo(tmp_path), shell)


def test_install_step_checks_are_not_softened():
    # B2 (C06, C07): `|| true` after the checksum or the version check would
    # let an unverified binary scan.
    for ln in _install_step().splitlines():
        if "sha256sum -c" in ln or "version" in ln:
            assert "||" not in ln, "an install check is softened: %r" % ln.strip()


def test_scan_step_messages_are_ascii():
    assert all(ord(ch) < 128 for ch in _scan_step()), "the scan step is not ASCII"


# ---------------------------------------------------------------------------
# Round 4, F1: the old grep-only refusals of step 4 hold whatever awk does
# ---------------------------------------------------------------------------

# A TrueType header (magic 00010000) padded with NUL bytes: git calls it
# binary, the --text views carry its NULs.
TTF = bytes.fromhex("00010000000a0080000300204f532f32") + bytes(32)


def _awk_failing_on_a_file(r: HookRepo) -> dict:
    # Passes a program over stdin (what a probe like printf '+x' | awk tests)
    # and exits 2 when it is given a file to read.
    env = _shim(r, "awk", 'case $# in 1) exec awk "$@" ;; esac\nexit 2\n')
    env["PATH"] = _without_gitleaks(env["PATH"])
    return env


def f1_dead_awk_after_an_allowlisted_png_akia_refused(r: HookRepo, shell: str) -> None:
    env = _broken_awk(r, 1)
    key = _akia()
    r.stage("docs/a.png", PNG)
    r.stage("z.txt", "id = " + key + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the staged key")


def f1_dead_awk_after_an_allowlisted_png_jwt_refused(r: HookRepo, shell: str) -> None:
    env = _broken_awk(r, 1)
    jwt = _jwt()
    r.stage("docs/a.png", PNG)
    r.stage("z.txt", "token = " + jwt + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_NEW_SHAPES)
    _assert_no_piece(run, jwt, "the JWT")


def f1_dead_awk_after_an_allowlisted_font_private_key_refused(
    r: HookRepo, shell: str
) -> None:
    env = _broken_awk(r, 1)
    r.stage("SmartCompareApp/assets/fonts/x.ttf", TTF)
    r.stage("z.txt", _private_key_header() + "\n")
    _assert_refused(r.run_hook(shell, env=env), MSG_CREDENTIAL)


def f1_awk_failing_on_a_file_akia_refused(r: HookRepo, shell: str) -> None:
    env = _awk_failing_on_a_file(r)
    key = _akia()
    r.stage("z.txt", "id = " + key + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the staged key")


def f1_awk_failing_on_a_file_with_env_akia_refused(r: HookRepo, shell: str) -> None:
    # With a .env the value pass reads stdin, runs and finds no value: the
    # key must still be refused by the four-branch check.
    env = _awk_failing_on_a_file(r)
    r.write_fake_env()
    key = _akia()
    r.stage("z.txt", "id = " + key + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the staged key")


def pin_f1_dead_awk_after_an_allowlisted_png_clean_commit_passes(
    r: HookRepo, shell: str
) -> None:
    env = _broken_awk(r, 1)
    r.stage("docs/a.png", PNG)
    r.stage("z.txt", "plain text\n")
    _assert_passed(r.run_hook(shell, env=env))


def f1_dead_awk_utf8_locale_invalid_byte_then_akia_refused(
    r: HookRepo, shell: str
) -> None:
    # TBF14 m4: the backstop runs under LC_ALL=C. Under a UTF-8 locale grep
    # treats an invalid UTF-8 byte as binary data; the byte (built here, never
    # in a shell string) sits on an earlier line of an earlier file, the key
    # in a later file.
    env = _broken_awk(r, 1)
    env["LC_ALL"] = "C.UTF-8"
    key = _akia()
    r.stage("a.txt", b"caf" + bytes([0xFF]) + b"\n")
    r.stage("z.txt", "id = " + key + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the staged key")


# ---------------------------------------------------------------------------
# Round 4, F4: an upper-case extension passes for every row of the hook's
# extension case (valid magic bytes, binary to git)
# ---------------------------------------------------------------------------


def f4_jpeg_upper_case_extension_passes(r: HookRepo, shell: str) -> None:
    r.stage("docs/x/IMG.JPEG", JPEG)
    _assert_passed(r.run_hook(shell))


def f4_ttf_upper_case_extension_passes(r: HookRepo, shell: str) -> None:
    r.stage("SmartCompareApp/assets/fonts/X.TTF", TTF)
    _assert_passed(r.run_hook(shell))


def f4_gif_upper_case_extension_passes(r: HookRepo, shell: str) -> None:
    r.stage("docs/x/X.GIF", GIF)
    _assert_passed(r.run_hook(shell))


def f4_webp_upper_case_extension_passes(r: HookRepo, shell: str) -> None:
    r.stage("SmartCompareApp/assets/images/X.WEBP", WEBP)
    _assert_passed(r.run_hook(shell))


def f4_otf_upper_case_extension_passes(r: HookRepo, shell: str) -> None:
    r.stage("SmartCompareApp/assets/fonts/X.OTF", OTF)
    _assert_passed(r.run_hook(shell))


ROUND4_SCENARIOS = {
    fn.__name__: fn
    for fn in (
        f1_dead_awk_after_an_allowlisted_png_akia_refused,
        f1_dead_awk_after_an_allowlisted_png_jwt_refused,
        f1_dead_awk_after_an_allowlisted_font_private_key_refused,
        f1_awk_failing_on_a_file_akia_refused,
        f1_awk_failing_on_a_file_with_env_akia_refused,
        pin_f1_dead_awk_after_an_allowlisted_png_clean_commit_passes,
        f1_dead_awk_utf8_locale_invalid_byte_then_akia_refused,
        f4_jpeg_upper_case_extension_passes,
        f4_ttf_upper_case_extension_passes,
        f4_gif_upper_case_extension_passes,
        f4_webp_upper_case_extension_passes,
        f4_otf_upper_case_extension_passes,
    )
}


@pytest.mark.skipif(SH is None, reason="no POSIX sh on PATH")
class TestPreCommitHookPhaseBRound4:
    @pytest.fixture(scope="class")
    def template(self, tmp_path_factory) -> Path:
        return HookRepo(tmp_path_factory.mktemp("t0b_phase_b_r4_template")).root

    @pytest.fixture(params=_shell_ids())
    def shell(self, request) -> str:
        return request.param

    @pytest.mark.parametrize("scenario", list(ROUND4_SCENARIOS))
    def test_scenario(
        self, shell: str, scenario: str, template: Path, tmp_path: Path
    ) -> None:
        ROUND4_SCENARIOS[scenario](HookRepo(tmp_path, template), shell)


# ---------------------------------------------------------------------------
# Round 4, F2: the ci.yml scan runs gitleaks with --no-color
# ---------------------------------------------------------------------------


def ci_gitleaks_call_runs_without_colour(c: CiRepo, shell: str) -> None:
    # 8.30.1 writes the log level as an ANSI-coloured ERR even into a file
    # (measured), so the step's ' ERR ' test needs --no-color to match.
    base = c.commit({"a.txt": "a\n"}, "base")
    head = c.commit({"b.txt": "b\n"}, "head")
    run = c.run_step(
        shell, {"EVENT_NAME": "pull_request", "PR_BASE": base, "PR_HEAD": head}
    )
    gl = c.gl()
    assert run.rc == 0 and gl.calls == 1, run.explain()
    assert "--no-color" in gl.args(), "the scan runs gitleaks with colour: %r" % (
        gl.args(),
    )


def ci_real_gitleaks_err_line_fails(c: CiRepo, shell: str) -> None:
    # The real tool (skips without it, as in CI's backend job): a noisy
    # textconv driver makes 8.30.1 log ERR, report nothing for the range and
    # exit 0, so a GitHub-token shape in the head commit passed the job.
    if GL_REAL is None:
        pytest.skip("gitleaks not on PATH")
    noisy = c.base / "noisy.sh"
    noisy.write_bytes(NOISY_SH.encode("ascii"))
    c.git("config", "diff.noisy.textconv", "sh " + _posix(noisy))
    info = c.root / ".git" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "attributes").write_bytes(b"*.dat diff=noisy\n")
    base = c.commit({"a.txt": "a\n"}, "base")
    tok = _ghp()
    head = c.commit({"a.dat": "data\n", "g.txt": "gh_token = " + tok + "\n"}, "head")
    run = c.run_step(
        shell,
        {"EVENT_NAME": "pull_request", "PR_BASE": base, "PR_HEAD": head},
        say='exec "' + _posix(Path(GL_REAL)) + '" "$@"',
    )
    assert c.gl().calls == 1, run.explain()
    assert run.rc != 0, "an ERR line from the real gitleaks must fail the job; " + (
        run.explain()
    )
    assert "gitleaks logged an error" in run.out, run.explain()
    _assert_no_piece(run, tok, "the head commit's token")


def ci_unreachable_pr_base_fails_without_scanning(c: CiRepo, shell: str) -> None:
    # F3: a PR base missing from the clone (a force push of the base branch)
    # fails before gitleaks runs, like a missing push end.
    head = c.commit({"a.txt": "a\n"}, "head")
    gone = "1234567890abcdef" * 2 + "12345678"
    run = c.run_step(
        shell, {"EVENT_NAME": "pull_request", "PR_BASE": gone, "PR_HEAD": head}
    )
    assert run.rc != 0, "a PR base missing from the clone must fail; " + run.explain()
    assert c.gl().calls == 0, "gitleaks scanned a range with a missing PR base"


ROUND4_CI_SCENARIOS = {
    fn.__name__: fn
    for fn in (
        ci_gitleaks_call_runs_without_colour,
        ci_real_gitleaks_err_line_fails,
        ci_unreachable_pr_base_fails_without_scanning,
    )
}


@pytest.mark.skipif(SH is None, reason="no POSIX sh on PATH")
class TestSecretScanStepRound4:
    @pytest.fixture(params=_shell_ids())
    def shell(self, request) -> str:
        return request.param

    @pytest.mark.parametrize("scenario", list(ROUND4_CI_SCENARIOS))
    def test_scenario(self, shell: str, scenario: str, tmp_path: Path) -> None:
        ROUND4_CI_SCENARIOS[scenario](CiRepo(tmp_path), shell)


# ---------------------------------------------------------------------------
# Round 5 (TBF21): the backstop's branches, readers and line selection that
# no earlier node pinned (the round-5 adversary's R5-1 to R5-3). Each node
# names the adversary scenario it reproduces.
# ---------------------------------------------------------------------------


def r5_dead_awk_sk_key_refused(r: HookRepo, shell: str) -> None:
    # R5-1, da_sk_only: the sk- branch of the backstop. Base refused this
    # with a dead awk, so losing the branch is an additivity regression.
    env = _broken_awk(r, 1)
    key = _sk()
    r.stage("a.txt", "t = " + key + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the staged key")


def r5_dead_awk_slack_token_refused(r: HookRepo, shell: str) -> None:
    # R5-1, da_xox_only: the xox branch (a base refusal as well).
    env = _broken_awk(r, 1)
    token = _slack()
    r.stage("a.txt", "t = " + token + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, token, "the staged token")


def r5_dead_awk_credentialed_url_refused(r: HookRepo, shell: str) -> None:
    # R5-1, da_credurl_only: the credentialed-URL branch of the second
    # backstop block (a 15-character password on a reserved host).
    env = _broken_awk(r, 1)
    url = _cred_url(15, "db.example.invalid")
    r.stage("a.txt", "db " + url + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_NEW_SHAPES)
    _assert_no_piece(run, url, "the credentialed URL")


def r5_dead_awk_utf8_locale_invalid_byte_same_line_akia_refused(
    r: HookRepo, shell: str
) -> None:
    # R5-2, da_utf8_ff_same_line_akia (TBF14 m4): the upstream stages of the
    # backstop run under LC_ALL=C. Under a UTF-8 locale grep drops the line
    # that holds an invalid UTF-8 byte (only that line, so the earlier-line
    # node of Round 4 stays a pin); here the byte and the key share the line.
    # The byte is built here, never in a shell string.
    env = _broken_awk(r, 1)
    env["LC_ALL"] = "C.UTF-8"
    key = _akia()
    r.stage("a.txt", b"caf" + bytes([0xFF]) + b" k " + key.encode("ascii") + b"\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the staged key")


def r5_dead_awk_utf8_locale_ext_diff_invalid_byte_line_refused(
    r: HookRepo, shell: str
) -> None:
    # R5-2, da_ext_reveal_ff_same_line_utf8: a diff driver command decodes a
    # line that holds 0xFF and the key. The grep that appends the
    # external-diff view to the staged-diff file (4-pre) runs in the user's
    # UTF-8 locale and drops that line, so only the backstop's own reader of
    # that view, under LC_ALL=C, sees it.
    env = _broken_awk(r, 1)
    env["LC_ALL"] = "C.UTF-8"
    r.write("ext.sh", EXT_SH)
    r.write(".git/info/attributes", "*.enc diff=dec\n")
    r.git("config", "diff.dec.command", "sh " + _posix(r.root / "ext.sh"))
    key = _akia()
    r.stage("s.enc", bytes([0xFF]) + b" k " + _rot13(key).encode("ascii") + b"\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the decoded key")


def r5_dead_awk_hiding_textconv_akia_refused(r: HookRepo, shell: str) -> None:
    # R5-2, da_textconv_hide_akia: a textconv driver that prints nothing
    # hides the key from the porcelain view, so the backstop's reader of the
    # staged-diff file (its --no-textconv view) is the one that refuses.
    env = _broken_awk(r, 1)
    r.write(".git/info/attributes", "*.txt diff=h\n")
    r.git("config", "diff.h.textconv", "true")
    key = _akia()
    r.stage("s.txt", "k = " + key + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_CREDENTIAL)
    _assert_no_piece(run, key, "the staged key")


def _commit_a_key_then_remove_it(r: HookRepo) -> str:
    # The key reaches HEAD past the hook (--no-verify), then the next commit
    # replaces its line with plain text: the post-leak remediation commit.
    key = _akia()
    r.stage("k.txt", "id = " + key + "\n")
    r.commit("a key, committed past the hook")
    r.stage("k.txt", "plain text\n")
    return key


def pin_r5_removing_a_committed_key_line_passes(r: HookRepo, shell: str) -> None:
    # R5-3 (a), deleted_line_only: the backstop reads + lines only, never -.
    key = _commit_a_key_then_remove_it(r)
    run = r.run_hook(shell)
    _assert_passed(run)
    _assert_no_piece(run, key, "the removed key")


def pin_r5_dead_awk_removing_a_committed_key_line_passes(
    r: HookRepo, shell: str
) -> None:
    # R5-3 (a), da_deleted_line_akia: the same with a dead awk.
    env = _broken_awk(r, 1)
    key = _commit_a_key_then_remove_it(r)
    run = r.run_hook(shell, env=env)
    _assert_passed(run)
    _assert_no_piece(run, key, "the removed key")


def pin_r5_sk_word_in_a_new_file_path_passes(r: HookRepo, shell: str) -> None:
    # R5-3 (b), wa_sk_learn_path_header: the backstop drops the +++ header
    # lines, so a new file whose path holds an sk- word of 20 or more
    # characters passes. The path is built here: as one literal in this file
    # it is an added line that the four-branch check would refuse.
    r.stage("docs/x/s" + "k-learn-integration-notes-2026.md", "plain notes\n")
    _assert_passed(r.run_hook(shell))


ROUND5_SCENARIOS = {
    fn.__name__: fn
    for fn in (
        r5_dead_awk_sk_key_refused,
        r5_dead_awk_slack_token_refused,
        r5_dead_awk_credentialed_url_refused,
        r5_dead_awk_utf8_locale_invalid_byte_same_line_akia_refused,
        r5_dead_awk_utf8_locale_ext_diff_invalid_byte_line_refused,
        r5_dead_awk_hiding_textconv_akia_refused,
        pin_r5_removing_a_committed_key_line_passes,
        pin_r5_dead_awk_removing_a_committed_key_line_passes,
        pin_r5_sk_word_in_a_new_file_path_passes,
    )
}


@pytest.mark.skipif(SH is None, reason="no POSIX sh on PATH")
class TestPreCommitHookPhaseBRound5:
    @pytest.fixture(scope="class")
    def template(self, tmp_path_factory) -> Path:
        return HookRepo(tmp_path_factory.mktemp("t0b_phase_b_r5_template")).root

    @pytest.fixture(params=_shell_ids())
    def shell(self, request) -> str:
        return request.param

    @pytest.mark.parametrize("scenario", list(ROUND5_SCENARIOS))
    def test_scenario(
        self, shell: str, scenario: str, template: Path, tmp_path: Path
    ) -> None:
        ROUND5_SCENARIOS[scenario](HookRepo(tmp_path, template), shell)
