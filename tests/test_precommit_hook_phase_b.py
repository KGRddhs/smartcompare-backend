"""Functional tests of `.githooks/pre-commit`, T0b Phase B.

Spec set: T0B_REPO_TOOLING_SPEC.md (corrections 1-17, rulings TR/TG/TF), the
Phase B addendum (section 3.3), the Phase B review (corrections 1-13) and the
orchestrator rulings TB1-TB14. One test node per scenario and per shell (sh,
and dash when it is a different binary), through the harness of the Phase A
file (tests/test_precommit_hook.py) and the shim helper of the round-2 file:
a tmp git repo per scenario, the LF copy of the hook, every GIT_* variable
dropped, GIT_CONFIG_NOSYSTEM=1, a tmp HOME, XDG_CONFIG_HOME and TMPDIR, and
the leftover checks after every run.

What is pinned here:
- the single staged diff read ONCE into the hook's temp dir, raw view and
  textconv view, with one status check (TB2, review correction 1, #316, TF7);
- the binary refusal of issue #315 with the TB3 allowlist and magic bytes;
- the gitleaks pass (R1.2, correction 1) through a PATH shim that records its
  argv and environment (flags, the HEAD config copy of TB6, the blanked
  GITLEAKS_CONFIG variables, color forced off), the two refusal wordings of
  review correction 7, the absent-gitleaks WARNING, the .gitleaksignore
  refusal (TB6), and the real gitleaks where it is installed (skips otherwise);
- the step order of TB7: every secret check before the Python checks, so no
  Python tool echoes a staged line first (M2);
- the ESLint step of R2.4 / correction 9 through a node shim and a fake
  SmartCompareApp/node_modules/eslint/bin/eslint.js (review correction 5);
- nodes 7 and 7b of review correction 9 (shims under sh -a);
- the optional nodes of review correction 10 (g): real `git commit -- path`
  and a commit from a linked worktree.

Security: every credential-shaped sentinel and every FAKE .env value is built
at runtime by concatenation; gitleaks runs with --redact (the hook's own
flags); no 12-character piece of a sentinel may appear in the hook output.
No real .env is ever opened: the hermetic environment keeps the hook inside
the tmp repo.

Every new hook message is a constant below; the GREEN hook prints each one
after the "pre-commit: " prefix of the existing fail helper.
"""

from __future__ import annotations

import codecs
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.test_precommit_hook import (
    MSG_CREDENTIAL,
    MSG_ENV_VALUE,
    MSG_NEW_SHAPES,
    MSG_PY_SYNTAX,
    PREFIX,
    REPO_ROOT,
    SH,
    SHELLS,
    V_EXPORT_QUOTED,
    HookRepo,
    HookRun,
    _akia,
    _assert_names_variable,
    _assert_passed,
    _assert_refused,
    _fake,
    _jwt,
    _shell_ids,
)
from tests.test_precommit_hook_round2 import (
    _assert_no_piece,
    _run_with_flags,
    _shim,
    _write_env,
)

# ---------------------------------------------------------------------------
# Phase B messages (binding for GREEN; each printed as "pre-commit: <text>")
# ---------------------------------------------------------------------------

MSG_DIFF_FAILED = "could not read the staged diff (git diff failed)"
MSG_BINARY = "staged file is binary to git and not a known asset path:"
MSG_BINARY_REMEDY = (
    "convert it to text, or add the path to the allowlist in "
    ".githooks/pre-commit in its own commit"
)
MSG_BINARY_LIST_FAILED = "could not list the staged files for the binary check"
MSG_GITLEAKS = "gitleaks refused the staged changes"
MSG_GITLEAKS_REPORT = MSG_GITLEAKS + " (rule id and place above)"
MSG_GITLEAKS_NO_REPORT = (
    MSG_GITLEAKS + " (it exited non-zero with no finding report: a broken "
    ".gitleaks.toml, or a gitleaks other than 8.30.1)"
)
MSG_GITLEAKS_ABSENT = (
    "WARNING gitleaks not installed - secret scan skipped (CI runs it)"
)
MSG_GITLEAKS_TEMPLATE = "could not write the gitleaks report template"
MSG_GITLEAKSIGNORE = "a .gitleaksignore would silence gitleaks; remove it"
MSG_GITLEAKS_HEAD_CONFIG = "could not read .gitleaks.toml from HEAD for gitleaks"
MSG_ESLINT = "eslint found errors in staged client files"
MSG_ESLINT_STAGED = "eslint found errors in the staged content of"
MSG_ESLINT_DIRTY_FAILED = "could not list the unstaged client files for eslint"
MSG_ESLINT_CAP = (
    "NOTE more than 10 partially staged client files - eslint read their working copies"
)
MSG_ESLINT_ABSENT = (
    "NOTE eslint not available (no node or no SmartCompareApp/node_modules)"
    " - staged client files not linted"
)
# Existing Phase A message, reused by the ESLint step (review correction 5).
MSG_STAGED_READ = "could not read the staged content of"

GITLEAKS = shutil.which("gitleaks")

# ---------------------------------------------------------------------------
# Runtime-built sentinels (never literals) and binary fixtures
# ---------------------------------------------------------------------------


def _ghp() -> str:
    """A GitHub personal-token shape (only gitleaks recognises it)."""
    return "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0" + "K1l2M3n4O5p6Q7r8"


def _rot13(text: str) -> str:
    return codecs.encode(text, "rot13")


PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600"
    "00001f15c4890000000d4944415478da63f8ffff3f0005fe02fea7"
    "d6a4b30000000049454e44ae426082"
)
PNG_MAGIC = PNG[:8]
JPEG = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")
GIF = b"GIF89a" + bytes.fromhex("010001000000002c00000000010001000002024401003b")
WEBP = (
    b"RIFF"
    + bytes.fromhex("1a000000")
    + b"WEBPVP8L"
    + bytes.fromhex("0d0000002f0000000007d0ff0f0000")
)
OTF = b"OTTO" + bytes.fromhex("000a00800003002043464620")
PDF = b"%PDF-1.4\n" + bytes(range(256)) + b"\n%%EOF\n"
SESSION_DIR = "docs/investigations/2026-10-05-session-72-state"

ROT_SH = "#!/bin/sh\ntr 'A-Za-z' 'N-ZA-Mn-za-m' < \"$1\"\n"


def _posix(p: Path) -> str:
    return str(p).replace("\\", "/")


def _without_gitleaks(path: str) -> str:
    keep = [
        d
        for d in path.split(os.pathsep)
        if d
        and not (
            os.path.exists(os.path.join(d, "gitleaks"))
            or os.path.exists(os.path.join(d, "gitleaks.exe"))
        )
    ]
    return os.pathsep.join(keep)


def _first_refusal(run: HookRun) -> str:
    refusals = run.refusals()
    assert refusals, "expected a refusal; %s" % run.explain()
    return refusals[0]


def _assert_first_refusal(run: HookRun, msg: str) -> str:
    line = _first_refusal(run)
    assert run.rc != 0 and line.startswith(
        PREFIX + msg
    ), "expected the FIRST refusal to be %r; %s" % (PREFIX + msg, run.explain())
    return line


def _assert_binary_refused(run: HookRun, rel: str) -> None:
    line = _assert_refused(run, MSG_BINARY + " " + rel)
    assert MSG_BINARY_REMEDY in line, "the binary refusal lacks the remedy: %r" % line


def _hook_text_messages(run: HookRun, needle: str) -> list:
    return [m for m in run.hook_messages() if needle in m]


# ---------------------------------------------------------------------------
# Shims
# ---------------------------------------------------------------------------

GL_SHIM = r"""log=@LOG@
printf 'CALL\n' >> "$log"
prev=""
rep=""
for a in "$@"; do
  printf 'ARG %s\n' "$a" >> "$log"
  if [ "$prev" = "--config" ]; then
    printf 'CONFIG-BEGIN\n' >> "$log"
    if [ -f "$a" ]; then cat "$a" >> "$log"; else printf 'CONFIG-MISSING\n' >> "$log"; fi
    printf '\nCONFIG-END\n' >> "$log"
  fi
  if [ "$prev" = "--report-path" ]; then rep=$a; fi
  prev=$a
done
if [ -n "${GITLEAKS_CONFIG:-}" ]; then printf 'GLC SET\n' >> "$log"; else printf 'GLC EMPTY\n' >> "$log"; fi
if [ -n "${GITLEAKS_CONFIG_TOML:-}" ]; then printf 'GLCT SET\n' >> "$log"; else printf 'GLCT EMPTY\n' >> "$log"; fi
printf 'COLOR_UI %s\n' "$(git config --get color.ui)" >> "$log"
printf 'COLOR_DIFF %s\n' "$(git config --get color.diff)" >> "$log"
@MARKCHECK@
@REPORT@
exit @RC@
"""


def _gitleaks_shim(
    r: HookRepo,
    rc: int = 0,
    report: str | None = None,
    marker: str | None = None,
    env: dict | None = None,
) -> tuple:
    """A `gitleaks` first on PATH that records its argv, the content of the
    file after --config, whether GITLEAKS_CONFIG(_TOML) is empty, the color
    config its git sees, and (with ``marker``) whether the marker is in its
    environment. With ``report`` it writes that line to --report-path."""
    log = r.base / "gitleaks_shim.log"
    mark = ""
    if marker:
        mark = 'if env | grep -q "%s"; then printf "ENV-LEAK\\n" >> "$log"; fi' % marker
    rep = ""
    if report:
        rep = "if [ -n \"$rep\" ]; then printf '%%s\\n' '%s' > \"$rep\"; fi" % report
    body = (
        GL_SHIM.replace("@LOG@", '"' + _posix(log) + '"')
        .replace("@MARKCHECK@", mark)
        .replace("@REPORT@", rep)
        .replace("@RC@", str(rc))
    )
    return _shim(r, "gitleaks", body, env=env), log


class GlLog:
    def __init__(self, log: Path):
        self.text = log.read_text(encoding="utf-8") if log.exists() else ""
        self.lines = self.text.splitlines()

    @property
    def calls(self) -> int:
        return self.lines.count("CALL")

    def args(self) -> list:
        out = []
        for ln in self.lines:
            if ln == "CALL" and out:
                break
            if ln.startswith("ARG "):
                out.append(ln[4:])
        return out

    def config_text(self) -> str:
        m = re.search(r"CONFIG-BEGIN\n(.*?)\nCONFIG-END", self.text, re.S)
        return m.group(1) if m else ""

    def has(self, line: str) -> bool:
        return line in self.lines


def _assert_gl_ran(gl: GlLog, run: HookRun) -> None:
    assert gl.calls >= 1, "the gitleaks shim never ran; %s" % run.explain()


NODE_SHIM = r"""log=@LOG@
printf 'ARGV' >> "$log"
for a in "$@"; do printf ' [%s]' "$a" >> "$log"; done
printf '\n' >> "$log"
printf 'PWD %s\n' "${PWD##*/}" >> "$log"
case " $* " in
  *" --stdin "*) printf 'STDIN<<\n' >> "$log"; cat >> "$log"; printf '\n>>STDIN\n' >> "$log" ;;
esac
case " $* " in
  *"--max-warnings"*) echo "node shim: --max-warnings turns warnings into errors" >&2; exit 1 ;;
esac
@SAY@
exit @RC@
"""


def _eslint_setup(r: HookRepo, rc: int = 0, say: str = "") -> tuple:
    """A fake project eslint (the file the hook tests for) and a `node` shim
    that logs every call: argv, the basename of its cwd and its stdin."""
    r.write("SmartCompareApp/node_modules/eslint/bin/eslint.js", "// fake eslint\n")
    log = r.base / "node_shim.log"
    body = (
        NODE_SHIM.replace("@LOG@", '"' + _posix(log) + '"')
        .replace("@SAY@", say)
        .replace("@RC@", str(rc))
    )
    return _shim(r, "node", body), log


def _node_calls(log: Path) -> list:
    """[(argv list, pwd basename, stdin or None), ...] in call order."""
    if not log.exists():
        return []
    text = log.read_text(encoding="utf-8")
    calls = []
    for chunk in text.split("ARGV")[1:]:
        head, _, rest = chunk.partition("\n")
        argv = re.findall(r"\[([^\]]*)\]", head)
        pwd = re.search(r"^PWD (.*)$", rest, re.M)
        stdin = re.search(r"STDIN<<\n(.*?)\n>>STDIN", rest, re.S)
        calls.append(
            (argv, pwd.group(1) if pwd else None, stdin.group(1) if stdin else None)
        )
    return calls


def _stage_client(r: HookRepo, i: int, partial: bool) -> str:
    rel = "SmartCompareApp/src/screens/S%d.tsx" % i
    r.stage(rel, "// STAGED-%d\nexport const a%d = 1;\n" % (i, i))
    if partial:
        r.write(rel, "// WORKTREE-%d\nexport const a%d = 2;\n" % (i, i))
    return rel


# ---------------------------------------------------------------------------
# Scenarios: the gitleaks pass through the PATH shim (CI has no gitleaks)
# ---------------------------------------------------------------------------


def gl_shim_finding_with_report_refuses(r: HookRepo, shell: str) -> None:
    env, log = _gitleaks_shim(r, rc=1, report="shim-rule cfg.txt:1")
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    _assert_gl_ran(GlLog(log), run)
    _assert_refused(run, MSG_GITLEAKS_REPORT)
    assert "shim-rule cfg.txt:1" in run.out, (
        "the report is not printed; " + run.explain()
    )


def gl_shim_nonzero_without_report_refuses(r: HookRepo, shell: str) -> None:
    env, log = _gitleaks_shim(r, rc=1)
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    _assert_gl_ran(GlLog(log), run)
    _assert_refused(run, MSG_GITLEAKS_NO_REPORT)


def gl_shim_rc2_broken_config_refuses(r: HookRepo, shell: str) -> None:
    env, log = _gitleaks_shim(r, rc=2)
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    _assert_gl_ran(GlLog(log), run)
    _assert_refused(run, MSG_GITLEAKS)


def gl_shim_argv_flags_env_and_color(r: HookRepo, shell: str) -> None:
    # color.ui / color.diff = always blind gitleaks 8.30.1 (addendum 2a);
    # GITLEAKS_CONFIG(_TOML) outrank --config, so the hook blanks them.
    r.git("config", "color.ui", "always")
    r.git("config", "color.diff", "always")
    env, log = _gitleaks_shim(r, rc=0)
    rulesless = r.base / "rulesless.toml"
    rulesless.write_text('title = "no rules"\n', encoding="ascii")
    env["GITLEAKS_CONFIG"] = str(rulesless)
    env["GITLEAKS_CONFIG_TOML"] = 'title = "no rules"'
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    gl = GlLog(log)
    _assert_gl_ran(gl, run)
    _assert_passed(run)
    args = gl.args()
    assert args and args[0] == "git", "gitleaks must run its git mode: %r" % args
    for flag in (
        "--pre-commit",
        "--staged",
        "--redact",
        "--no-banner",
        "--ignore-gitleaks-allow",
    ):
        assert flag in args, "gitleaks argv lacks %s: %r" % (flag, args)
    assert "--report-format" in args, args
    assert args[args.index("--report-format") + 1] == "template", args
    for bad in ("-v", "--verbose"):
        assert bad not in args, "gitleaks argv carries %s (content echo): %r" % (
            bad,
            args,
        )
    # TBF2: always --config; HEAD has none here, so a default-only file.
    assert "--config" in args, "TBF2: the hook always passes --config: %r" % args
    assert gl.config_text().strip() == "[extend]\nuseDefault = true", gl.config_text()
    assert gl.has("GLC EMPTY"), "GITLEAKS_CONFIG reaches gitleaks: " + gl.text[-300:]
    assert gl.has("GLCT EMPTY"), "GITLEAKS_CONFIG_TOML reaches gitleaks"
    assert gl.has("COLOR_UI never"), "color.ui is not forced off for gitleaks"
    assert gl.has("COLOR_DIFF never"), "color.diff is not forced off for gitleaks"


def gl_shim_config_is_a_copy_of_head(r: HookRepo, shell: str) -> None:
    # TB6: --config names a copy of HEAD:.gitleaks.toml in the hook's temp
    # dir, never the working-tree file (a change cannot widen the allowlist
    # that judges it).
    head = "# head-marker-T0BQ\n[extend]\nuseDefault = true\n"
    r.stage(".gitleaks.toml", head)
    r.commit("cfg")
    r.write(".gitleaks.toml", "# worktree-marker-T0BQ\n[extend]\nuseDefault = true\n")
    env, log = _gitleaks_shim(r, rc=0)
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    gl = GlLog(log)
    _assert_gl_ran(gl, run)
    _assert_passed(run)
    args = gl.args()
    assert "--config" in args, "HEAD has a .gitleaks.toml: --config expected: %r" % args
    cfg = args[args.index("--config") + 1].replace("\\", "/")
    assert not cfg.endswith("/repo/.gitleaks.toml"), (
        "--config names the working-tree file: %r" % cfg
    )
    text = gl.config_text()
    assert "head-marker-T0BQ" in text and "worktree-marker-T0BQ" not in text, (
        "the config gitleaks read is not HEAD's: %r" % text[:200]
    )


def gl_shim_no_config_when_head_has_none(r: HookRepo, shell: str) -> None:
    # TB6: no .gitleaks.toml at HEAD (a first commit) -> the default rules,
    # even when the working tree holds one. TBF2: passed as a default-only
    # --config file, so gitleaks never loads the working-tree file itself.
    r.write(".gitleaks.toml", "# worktree-only-T0BQ\n[extend]\nuseDefault = true\n")
    env, log = _gitleaks_shim(r, rc=0)
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    gl = GlLog(log)
    _assert_gl_ran(gl, run)
    _assert_passed(run)
    args = gl.args()
    assert "--config" in args, "TBF2: the hook always passes --config: %r" % args
    cfg = args[args.index("--config") + 1].replace("\\", "/")
    assert not cfg.endswith("/repo/.gitleaks.toml"), "--config names the work tree"
    text = gl.config_text()
    assert text.strip() == "[extend]\nuseDefault = true", "not default-only: %r" % text
    assert "worktree-only-T0BQ" not in text, "the working-tree config judged the commit"


def gl_absent_warns_and_passes(r: HookRepo, shell: str) -> None:
    env = dict(r.env)
    env["PATH"] = _without_gitleaks(env["PATH"])
    assert shutil.which("gitleaks", path=env["PATH"]) is None
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    _assert_passed(run)
    warn = [m for m in run.hook_messages() if m == PREFIX + MSG_GITLEAKS_ABSENT]
    assert len(warn) == 1, "expected ONE %r; %s" % (
        PREFIX + MSG_GITLEAKS_ABSENT,
        run.explain(),
    )


def gl_gitleaksignore_is_refused(r: HookRepo, shell: str) -> None:
    # TB6: a .gitleaksignore in the work tree root silences gitleaks.
    env, log = _gitleaks_shim(r, rc=0)
    r.write(".gitleaksignore", "cfg.txt:generic-api-key:1\n")
    r.stage("cfg.txt", "plain text\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_GITLEAKSIGNORE)


def gl_shim_refusal_precedes_python(r: HookRepo, shell: str) -> None:
    # TB7: gitleaks (the last secret check) runs before py_compile.
    env, log = _gitleaks_shim(r, rc=1, report="shim-rule bad.py:1")
    r.stage("bad.py", "def f(:\n")
    run = r.run_hook(shell, env=env)
    _assert_first_refusal(run, MSG_GITLEAKS)


def gl_allexport_keeps_values_out_of_gitleaks_env(r: HookRepo, shell: str) -> None:
    # Review correction 9, node 7: under sh -a no .env value reaches the
    # environment of a process started after the .env parse (gitleaks).
    marker = "Glx" + "PrtMk"
    value = _fake("gx", 9) + marker + _fake("gy", 9)
    env, log = _gitleaks_shim(r, rc=0, marker=marker)
    _write_env(r, ["FAKE_ALLEXPORT_KEY=" + value])
    r.stage("cfg.txt", "plain text\n")
    run = _run_with_flags(r, shell, ["-a"], env)
    gl = GlLog(log)
    _assert_gl_ran(gl, run)
    assert run.rc == 0 and run.refusals() == [], run.explain()
    assert not gl.has("ENV-LEAK"), "a .env value is in the environment of gitleaks"
    _assert_no_piece(run, value, "a .env value")


def cat_allexport_keeps_values_out_of_the_value_pipe(r: HookRepo, shell: str) -> None:
    # Review correction 9, node 7b: the left side of the .env value pipe reads
    # the staged-diff file with cat AFTER the parse; under sh -a its
    # environment must not carry a .env value.
    marker = "Ctx" + "PrtMk"
    value = _fake("cx", 9) + marker + _fake("cy", 9)
    log = r.base / "cat_shim.log"
    body = (
        'printf "CAT\\n" >> "%s"\n'
        'if env | grep -q "%s"; then printf "CAT-ENV-LEAK\\n" >> "%s"; fi\n'
        'exec cat "$@"\n'
    ) % (_posix(log), marker, _posix(log))
    env = _shim(r, "cat", body)
    _write_env(r, ["FAKE_ALLEXPORT_KEY=" + value])
    r.stage("cfg.txt", "plain text\n")
    run = _run_with_flags(r, shell, ["-a"], env)
    text = log.read_text(encoding="utf-8") if log.exists() else ""
    assert "CAT" in text.splitlines(), (
        "cat never ran: the value pass does not read the staged-diff file; %s"
        % run.explain()
    )
    assert run.rc == 0 and run.refusals() == [], run.explain()
    assert "CAT-ENV-LEAK" not in text, "a .env value is in the environment of cat"
    _assert_no_piece(run, value, "a .env value")


# ---------------------------------------------------------------------------
# Scenarios: TB7 order (M2) and the staged diff (#316, TF7)
# ---------------------------------------------------------------------------


def m2_regex_refusal_precedes_python_no_echo(r: HookRepo, shell: str) -> None:
    key = _akia()
    r.stage("bad.py", 'def f(: k = "' + key + '"\n')
    run = r.run_hook(shell)
    _assert_first_refusal(run, MSG_CREDENTIAL)
    assert run.first_message(PREFIX + MSG_PY_SYNTAX) is None, run.explain()
    _assert_no_piece(run, key, "the staged key")


def i316_color_ui_always(r: HookRepo, shell: str) -> None:
    r.git("config", "color.ui", "always")
    r.stage("k.txt", "id = " + _akia() + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def i316_color_diff_always(r: HookRepo, shell: str) -> None:
    r.git("config", "color.diff", "always")
    r.stage("k.txt", "id = " + _akia() + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def i316_diff_external(r: HookRepo, shell: str) -> None:
    r.git("config", "diff.external", "true")
    r.stage("k.txt", "id = " + _akia() + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def i316_plusplus_line(r: HookRepo, shell: str) -> None:
    r.stage("k.txt", "++" + _akia() + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def tf7_failed_diff_refuses_without_env(r: HookRepo, shell: str) -> None:
    # A git diff of the staged patch that fails must refuse the commit for the
    # four-branch line and 4a too (TF7), not only for the .env value pass.
    env = _shim(
        r,
        "git",
        'case " $* " in\n'
        '  *" diff --cached"*" -U0 "*) echo "git shim: diff failed" >&2; exit 128 ;;\n'
        "esac\n"
        'exec git "$@"\n',
    )
    r.stage("k.txt", "id = " + _akia() + "\n")
    _assert_refused(r.run_hook(shell, env=env), MSG_DIFF_FAILED)


# ---------------------------------------------------------------------------
# Scenarios: textconv (review correction 1 PINs; #315 hide cases)
# ---------------------------------------------------------------------------


def _rot_driver(r: HookRepo) -> None:
    r.write("rot.sh", ROT_SH)
    r.write(".git/info/attributes", "*.cfg diff=rot\n")
    r.git("config", "diff.rot.textconv", "sh " + _posix(r.root / "rot.sh"))


def _hide_driver(r: HookRepo, pattern: str) -> None:
    r.write(".git/info/attributes", pattern + " diff=hide\n")
    r.git("config", "diff.hide.textconv", "true")


def pin_textconv_reveal_four_branch(r: HookRepo, shell: str) -> None:
    _rot_driver(r)
    r.stage("conf/a.cfg", "aws_id = " + _rot13(_akia()) + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


def pin_textconv_reveal_new_shapes(r: HookRepo, shell: str) -> None:
    _rot_driver(r)
    r.stage("conf/j.cfg", "token = " + _rot13(_jwt()) + "\n")
    run = r.run_hook(shell)
    _assert_refused(run, MSG_NEW_SHAPES)
    _assert_no_piece(run, _jwt(), "the JWT")


def pin_textconv_reveal_env_value(r: HookRepo, shell: str) -> None:
    _rot_driver(r)
    r.write_fake_env()
    r.stage("conf/b.cfg", "v = " + _rot13(V_EXPORT_QUOTED) + "\n")
    _assert_names_variable(r.run_hook(shell), "FAKE_SERVICE_KEY", V_EXPORT_QUOTED)


def i315_textconv_hides_env_value(r: HookRepo, shell: str) -> None:
    _hide_driver(r, "*.dat")
    r.write_fake_env()
    r.stage("conf/a.dat", "a = " + V_EXPORT_QUOTED + "\n")
    _assert_names_variable(r.run_hook(shell), "FAKE_SERVICE_KEY", V_EXPORT_QUOTED)


def i315_textconv_hides_aws_key(r: HookRepo, shell: str) -> None:
    _hide_driver(r, "*.dat")
    r.stage("conf/b.dat", "id = " + _akia() + "\n")
    _assert_refused(r.run_hook(shell), MSG_CREDENTIAL)


# ---------------------------------------------------------------------------
# Scenarios: binary content (#315, TB3)
# ---------------------------------------------------------------------------


def i315_nul_jwt_outside_allowlist(r: HookRepo, shell: str) -> None:
    jwt = _jwt()
    r.stage("data/blob.dat", b"\x00\x01binary\n" + ("token = " + jwt + "\n").encode())
    run = r.run_hook(shell)
    _assert_refused(run, MSG_NEW_SHAPES)
    _assert_no_piece(run, jwt, "the JWT")


def i315_nul_jwt_at_allowlisted_path(r: HookRepo, shell: str) -> None:
    # Review correction 10 (b): the mawk canary. A CI-only red here is a real
    # Linux gap in the NUL handling of the added-lines awk, not a test bug.
    jwt = _jwt()
    data = PNG_MAGIC + b"\x00\x00\n" + ("token = " + jwt + "\n").encode()
    r.stage("docs/img/n.png", data)
    run = r.run_hook(shell)
    _assert_refused(run, MSG_NEW_SHAPES)
    _assert_no_piece(run, jwt, "the JWT")


def i315_minus_diff_jwt_at_allowlisted_path(r: HookRepo, shell: str) -> None:
    # Review correction 10 (b): the --text killer that needs no NUL handling:
    # a text file made binary by a -diff attribute, at an allowlisted path,
    # with the PNG magic bytes.
    jwt = _jwt()
    r.write(".git/info/attributes", "*.png -diff\n")
    r.stage("docs/img/t.png", PNG_MAGIC + b"\n" + ("token = " + jwt + "\n").encode())
    run = r.run_hook(shell)
    _assert_refused(run, MSG_NEW_SHAPES)
    _assert_no_piece(run, jwt, "the JWT")


def i315_minus_diff_env_value(r: HookRepo, shell: str) -> None:
    r.write(".git/info/attributes", "*.json -diff\n")
    r.write_fake_env()
    r.stage("a.json", '{"v": "' + V_EXPORT_QUOTED + '"}\n')
    run = r.run_hook(shell)
    _assert_binary_refused(run, "a.json")
    _assert_no_piece(run, V_EXPORT_QUOTED, "a .env value")


def i315_utf16_aws_key(r: HookRepo, shell: str) -> None:
    key = _akia()
    r.stage("notes/u.txt", ("id = " + key + "\n").encode("utf-16"))
    run = r.run_hook(shell)
    _assert_binary_refused(run, "notes/u.txt")
    _assert_no_piece(run, key, "the staged key")


def i315_nul_env_value(r: HookRepo, shell: str) -> None:
    r.write_fake_env()
    r.stage("data/n.txt", b"\x00\n" + ("a = " + V_EXPORT_QUOTED + "\n").encode())
    run = r.run_hook(shell)
    _assert_binary_refused(run, "data/n.txt")
    _assert_no_piece(run, V_EXPORT_QUOTED, "a .env value")


def i315_png_outside_allowlist(r: HookRepo, shell: str) -> None:
    r.stage("misc/new.png", PNG)
    _assert_binary_refused(r.run_hook(shell), "misc/new.png")


def i315_rename_png_out_of_allowlist(r: HookRepo, shell: str) -> None:
    r.stage("SmartCompareApp/assets/a.png", PNG)
    r.commit("png")
    (r.root / "misc").mkdir()
    r.git("mv", "SmartCompareApp/assets/a.png", "misc/a.png")
    _assert_binary_refused(r.run_hook(shell), "misc/a.png")


def i315_pdf_under_docs_refused(r: HookRepo, shell: str) -> None:
    rel = SESSION_DIR + "/report.pdf"
    r.stage(rel, PDF)
    _assert_binary_refused(r.run_hook(shell), rel)


def i315_renamed_dump_without_magic_refused(r: HookRepo, shell: str) -> None:
    # TB3 (Q2b): an allowlisted path must carry the magic bytes of its
    # extension; a UTF-16 dump named .png does not.
    rel = SESSION_DIR + "/dump.png"
    r.stage(rel, ("id = " + _fake("dp", 30) + "\n").encode("utf-16"))
    _assert_binary_refused(r.run_hook(shell), rel)


def pin_315_repo_icon_passes(r: HookRepo, shell: str) -> None:
    rel = "SmartCompareApp/assets/icon.png"
    r.stage(rel, (REPO_ROOT / rel).read_bytes())
    _assert_passed(r.run_hook(shell))


def pin_315_docs_images_pass(r: HookRepo, shell: str) -> None:
    # TB3: new session screenshots and images under docs/ pass.
    r.stage(SESSION_DIR + "/screenshot.png", PNG)
    r.stage(SESSION_DIR + "/photo.jpg", JPEG)
    r.stage(SESSION_DIR + "/anim.gif", GIF)
    _assert_passed(r.run_hook(shell))


def pin_315_assets_webp_and_otf_pass(r: HookRepo, shell: str) -> None:
    r.stage("SmartCompareApp/assets/images/new.webp", WEBP)
    r.stage("SmartCompareApp/assets/fonts/New.otf", OTF)
    _assert_passed(r.run_hook(shell))


def pin_315_rename_within_allowlist_passes(r: HookRepo, shell: str) -> None:
    r.stage("SmartCompareApp/assets/a.png", PNG)
    r.commit("png")
    r.git("mv", "SmartCompareApp/assets/a.png", "SmartCompareApp/assets/b.png")
    _assert_passed(r.run_hook(shell))


def pin_315_deleted_binary_passes(r: HookRepo, shell: str) -> None:
    r.stage("misc/old.png", PNG)
    r.commit("png")
    r.git("rm", "-q", "misc/old.png")
    _assert_passed(r.run_hook(shell))


def pin_315_empty_file_passes(r: HookRepo, shell: str) -> None:
    r.stage("empty.txt", b"")
    _assert_passed(r.run_hook(shell))


# ---------------------------------------------------------------------------
# Scenarios: ESLint on staged client content (R2.4, corrections 9 and 5)
# ---------------------------------------------------------------------------


def eslint_full_error_blocks(r: HookRepo, shell: str) -> None:
    env, log = _eslint_setup(r, rc=1)
    _stage_client(r, 0, partial=False)
    run = r.run_hook(shell, env=env)
    calls = _node_calls(log)
    assert len(calls) == 1, "expected one eslint call; %r; %s" % (calls, run.explain())
    argv, pwd, stdin = calls[0]
    assert pwd == "SmartCompareApp", "eslint must run from SmartCompareApp: %r" % pwd
    assert argv and argv[0] == "node_modules/eslint/bin/eslint.js", argv
    assert "src/screens/S0.tsx" in argv and "--stdin" not in argv, argv
    assert not any(a.startswith("SmartCompareApp/") for a in argv), argv
    for bad in ("--fix", "--cache", "--max-warnings"):
        assert not any(a.startswith(bad) for a in argv), argv
    _assert_refused(run, MSG_ESLINT)


def eslint_crash_blocks(r: HookRepo, shell: str) -> None:
    env, log = _eslint_setup(r, rc=2)
    _stage_client(r, 0, partial=False)
    run = r.run_hook(shell, env=env)
    assert _node_calls(log), "eslint was never called; " + run.explain()
    _assert_refused(run, MSG_ESLINT)


def eslint_partial_reads_staged_content(r: HookRepo, shell: str) -> None:
    env, log = _eslint_setup(r, rc=0)
    _stage_client(r, 0, partial=True)
    run = r.run_hook(shell, env=env)
    calls = _node_calls(log)
    stdin_calls = [c for c in calls if "--stdin" in c[0]]
    assert len(stdin_calls) == 1, "expected one --stdin call: %r; %s" % (
        calls,
        run.explain(),
    )
    argv, pwd, stdin = stdin_calls[0]
    assert pwd == "SmartCompareApp", pwd
    assert "--stdin-filename" in argv, argv
    assert argv[argv.index("--stdin-filename") + 1] == "src/screens/S0.tsx", argv
    assert stdin is not None and "STAGED-0" in stdin and "WORKTREE-0" not in stdin, (
        "eslint read the working tree, not the staged content: %r" % stdin
    )
    _assert_passed(run)


def eslint_partial_error_blocks(r: HookRepo, shell: str) -> None:
    env, log = _eslint_setup(r, rc=1)
    rel = _stage_client(r, 0, partial=True)
    run = r.run_hook(shell, env=env)
    assert _node_calls(log), "eslint was never called; " + run.explain()
    _assert_refused(run, MSG_ESLINT_STAGED + " " + rel)


def eslint_partial_git_show_failure_refuses(r: HookRepo, shell: str) -> None:
    # Review correction 5: a failed read of the staged blob must refuse, not
    # lint an empty stdin.
    env, log = _eslint_setup(r, rc=0)
    env = _shim(
        r,
        "git",
        'case " $* " in\n'
        '  *" show :SmartCompareApp/"*|*" cat-file "*":SmartCompareApp/"*)'
        ' echo "git shim: show failed" >&2; exit 128 ;;\n'
        "esac\n"
        'exec git "$@"\n',
        env=env,
    )
    rel = _stage_client(r, 0, partial=True)
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_STAGED_READ + " " + rel)
    assert not [
        c for c in _node_calls(log) if "--stdin" in c[0]
    ], "eslint linted a stdin after the staged read failed"


def eslint_cap_over_10_partial(r: HookRepo, shell: str) -> None:
    env, log = _eslint_setup(r, rc=0)
    for i in range(11):
        _stage_client(r, i, partial=True)
    run = r.run_hook(shell, env=env)
    assert run.first_message(PREFIX + MSG_ESLINT_CAP), "expected the NOTE %r; %s" % (
        PREFIX + MSG_ESLINT_CAP,
        run.explain(),
    )
    calls = _node_calls(log)
    assert len(calls) == 1 and "--stdin" not in calls[0][0], calls
    paths = [a for a in calls[0][0] if a.startswith("src/screens/S")]
    assert len(paths) == 11, (
        "the by-path call must carry all 11 files: %r" % calls[0][0]
    )
    _assert_passed(run)


def eslint_absent_notes(r: HookRepo, shell: str) -> None:
    _stage_client(r, 0, partial=False)
    run = r.run_hook(shell)
    _assert_passed(run)
    assert run.first_message(PREFIX + MSG_ESLINT_ABSENT), "expected the NOTE %r; %s" % (
        PREFIX + MSG_ESLINT_ABSENT,
        run.explain(),
    )


def pin_eslint_warnings_pass(r: HookRepo, shell: str) -> None:
    env, log = _eslint_setup(r, rc=0, say='echo "src/screens/S0.tsx: 1 warning (shim)"')
    _stage_client(r, 0, partial=False)
    _assert_passed(r.run_hook(shell, env=env))


def pin_eslint_no_client_file_no_note(r: HookRepo, shell: str) -> None:
    env, log = _eslint_setup(r, rc=1)
    r.stage("app/x.py", "x = 1\n")
    run = r.run_hook(shell, env=env)
    _assert_passed(run)
    assert not _hook_text_messages(run, "eslint"), run.explain()
    assert not _node_calls(log), "eslint ran with no client file staged"


# ---------------------------------------------------------------------------
# Scenarios: the real gitleaks (skip where it is not installed, as in CI)
# ---------------------------------------------------------------------------


def _need_gitleaks() -> None:
    if GITLEAKS is None:
        pytest.skip("gitleaks not on PATH")


def gl_real_staged_only_secret_refused(r: HookRepo, shell: str) -> None:
    _need_gitleaks()
    tok = _ghp()
    r.stage("cfg.txt", "gh_token = " + tok + "\n")
    r.write("cfg.txt", "clean\n")
    run = r.run_hook(shell)
    _assert_refused(run, MSG_GITLEAKS_REPORT)
    _assert_no_piece(run, tok, "the staged token")


def pin_gl_real_unstaged_secret_passes(r: HookRepo, shell: str) -> None:
    _need_gitleaks()
    r.stage("cfg.txt", "clean\n")
    r.commit("cfg")
    r.write("cfg.txt", "gh_token = " + _ghp() + "\n")
    r.stage("ok.txt", "fine\n")
    _assert_passed(r.run_hook(shell))


def gl_real_color_always_refused(r: HookRepo, shell: str) -> None:
    _need_gitleaks()
    r.git("config", "color.ui", "always")
    r.git("config", "color.diff", "always")
    tok = _ghp()
    r.stage("cfg.txt", "gh_token = " + tok + "\n")
    run = r.run_hook(shell)
    _assert_refused(run, MSG_GITLEAKS)
    _assert_no_piece(run, tok, "the staged token")


def gl_real_allow_comment_refused(r: HookRepo, shell: str) -> None:
    _need_gitleaks()
    tok = _ghp()
    r.stage("cfg.txt", "gh_token = " + tok + "  # " + "gitleaks" + ":allow\n")
    run = r.run_hook(shell)
    _assert_refused(run, MSG_GITLEAKS)
    _assert_no_piece(run, tok, "the staged token")


def gl_real_env_config_override_refused(r: HookRepo, shell: str) -> None:
    _need_gitleaks()
    rulesless = r.base / "rulesless.toml"
    rulesless.write_text('title = "no rules"\n', encoding="ascii")
    env = dict(r.env)
    env["GITLEAKS_CONFIG"] = str(rulesless)
    tok = _ghp()
    r.stage("cfg.txt", "gh_token = " + tok + "\n")
    run = r.run_hook(shell, env=env)
    _assert_refused(run, MSG_GITLEAKS)
    _assert_no_piece(run, tok, "the staged token")


def gl_real_worktree_config_cannot_widen(r: HookRepo, shell: str) -> None:
    # TB6 with the real tool: HEAD's config judges the commit; a working-tree
    # edit that allowlists the token does not silence it.
    _need_gitleaks()
    r.stage(".gitleaks.toml", "[extend]\nuseDefault = true\n")
    r.commit("cfg")
    widened = (
        "[extend]\nuseDefault = true\n\n[[allowlists]]\n"
        'description = "local widening"\n'
        "regexes = ['''" + "gh" + "p_[A-Za-z0-9]+" + "''']\n"
    )
    r.write(".gitleaks.toml", widened)
    tok = _ghp()
    r.stage("cfg.txt", "gh_token = " + tok + "\n")
    run = r.run_hook(shell)
    _assert_refused(run, MSG_GITLEAKS)
    _assert_no_piece(run, tok, "the staged token")


def gl_real_m2_no_echo(r: HookRepo, shell: str) -> None:
    _need_gitleaks()
    tok = _ghp()
    r.stage("bad.py", 'def f(: t = "' + tok + '"\n')
    run = r.run_hook(shell)
    _assert_first_refusal(run, MSG_GITLEAKS)
    _assert_no_piece(run, tok, "the staged token")


# ---------------------------------------------------------------------------
# Scenarios: a real `git commit` runs the hook (review correction 10 g).
# git starts the hook with its own sh, so these run in the sh column only.
# ---------------------------------------------------------------------------


def _real_commit(r: HookRepo, *args: str, cwd: Path | None = None) -> HookRun:
    p = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=.githooks",
            "-c",
            "user.email=t0b@example.invalid",
            "-c",
            "user.name=t0b",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            "real",
            *args,
        ],
        cwd=str(cwd or r.root),
        env=r.env,
        capture_output=True,
        timeout=120,
    )
    run = HookRun(p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace"))
    stray = sorted(x.name for x in r.hooktmp.iterdir())
    assert not stray, "hook left %s in its TMPDIR; %s" % (stray, run.explain())
    return run


def _only_sh(shell: str) -> None:
    if shell != "sh":
        pytest.skip("git runs the hook with its own sh: one column is enough")


def pin_real_commit_of_a_path_with_a_jwt_refused(r: HookRepo, shell: str) -> None:
    _only_sh(shell)
    head = r.git("rev-parse", "HEAD").strip()
    r.stage("tok.txt", "token = " + _jwt() + "\n")
    run = _real_commit(r, "--", "tok.txt")
    _assert_refused(run, MSG_NEW_SHAPES)
    assert r.git("rev-parse", "HEAD").strip() == head, "the commit was created"


def pin_real_partial_commit_ignores_other_staged_path(r: HookRepo, shell: str) -> None:
    _only_sh(shell)
    head = r.git("rev-parse", "HEAD").strip()
    r.stage("other.txt", "token = " + _jwt() + "\n")
    r.stage("clean.txt", "hello\n")
    run = _real_commit(r, "--", "clean.txt")
    assert run.rc == 0 and not run.refusals(), run.explain()
    assert r.git("rev-parse", "HEAD").strip() != head, "the commit was not created"


def pin_real_commit_from_a_linked_worktree(r: HookRepo, shell: str) -> None:
    _only_sh(shell)
    wt = r.base / "linked"
    r.git("worktree", "add", "-q", "--detach", str(wt), "HEAD")
    r.stage("tok.txt", "token = " + _jwt() + "\n", root=wt)
    _assert_refused(_real_commit(r, cwd=wt), MSG_NEW_SHAPES)
    r.git("rm", "-q", "--cached", "tok.txt", cwd=wt)
    r.stage("ok.txt", "fine\n", root=wt)
    run = _real_commit(r, cwd=wt)
    assert run.rc == 0 and not run.refusals(), run.explain()


SCENARIOS = {
    fn.__name__: fn
    for fn in (
        gl_shim_finding_with_report_refuses,
        gl_shim_nonzero_without_report_refuses,
        gl_shim_rc2_broken_config_refuses,
        gl_shim_argv_flags_env_and_color,
        gl_shim_config_is_a_copy_of_head,
        gl_shim_no_config_when_head_has_none,
        gl_absent_warns_and_passes,
        gl_gitleaksignore_is_refused,
        gl_shim_refusal_precedes_python,
        gl_allexport_keeps_values_out_of_gitleaks_env,
        cat_allexport_keeps_values_out_of_the_value_pipe,
        m2_regex_refusal_precedes_python_no_echo,
        i316_color_ui_always,
        i316_color_diff_always,
        i316_diff_external,
        i316_plusplus_line,
        tf7_failed_diff_refuses_without_env,
        pin_textconv_reveal_four_branch,
        pin_textconv_reveal_new_shapes,
        pin_textconv_reveal_env_value,
        i315_textconv_hides_env_value,
        i315_textconv_hides_aws_key,
        i315_nul_jwt_outside_allowlist,
        i315_nul_jwt_at_allowlisted_path,
        i315_minus_diff_jwt_at_allowlisted_path,
        i315_minus_diff_env_value,
        i315_utf16_aws_key,
        i315_nul_env_value,
        i315_png_outside_allowlist,
        i315_rename_png_out_of_allowlist,
        i315_pdf_under_docs_refused,
        i315_renamed_dump_without_magic_refused,
        pin_315_repo_icon_passes,
        pin_315_docs_images_pass,
        pin_315_assets_webp_and_otf_pass,
        pin_315_rename_within_allowlist_passes,
        pin_315_deleted_binary_passes,
        pin_315_empty_file_passes,
        eslint_full_error_blocks,
        eslint_crash_blocks,
        eslint_partial_reads_staged_content,
        eslint_partial_error_blocks,
        eslint_partial_git_show_failure_refuses,
        eslint_cap_over_10_partial,
        eslint_absent_notes,
        pin_eslint_warnings_pass,
        pin_eslint_no_client_file_no_note,
        gl_real_staged_only_secret_refused,
        pin_gl_real_unstaged_secret_passes,
        gl_real_color_always_refused,
        gl_real_allow_comment_refused,
        gl_real_env_config_override_refused,
        gl_real_worktree_config_cannot_widen,
        gl_real_m2_no_echo,
        pin_real_commit_of_a_path_with_a_jwt_refused,
        pin_real_partial_commit_ignores_other_staged_path,
        pin_real_commit_from_a_linked_worktree,
    )
}


@pytest.mark.skipif(SH is None, reason="no POSIX sh on PATH")
class TestPreCommitHookPhaseB:
    @pytest.fixture(scope="class")
    def template(self, tmp_path_factory) -> Path:
        return HookRepo(tmp_path_factory.mktemp("t0b_phase_b_template")).root

    @pytest.fixture(params=_shell_ids())
    def shell(self, request) -> str:
        return request.param

    @pytest.mark.parametrize("scenario", list(SCENARIOS))
    def test_scenario(
        self, shell: str, scenario: str, template: Path, tmp_path: Path
    ) -> None:
        SCENARIOS[scenario](HookRepo(tmp_path, template), shell)
