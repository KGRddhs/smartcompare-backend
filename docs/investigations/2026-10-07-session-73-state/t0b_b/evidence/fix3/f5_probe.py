"""F5 probe (TBF17): ONE measurement with the real gitleaks 8.30.1.

A scratch repo (the Phase A harness: GIT_* dropped, GIT_CONFIG_NOSYSTEM=1, tmp
HOME / XDG_CONFIG_HOME / TMPDIR) whose core.hooksPath is .githooks with the
current hook (LF). A runtime-built GitHub-token shape (only gitleaks knows the
shape; no regex branch of the hook matches it) is staged, then a REAL
`git commit` runs the hook: control = plain `git commit`; probe =
`git -c color.ui=always commit` (git exports GIT_CONFIG_PARAMETERS to the hook,
which reaches gitleaks' own git call). Prints rc, the class of the first hook
message and whether the commit landed; never the token (a 12-char piece check
on the output).
"""
import os
import pathlib
import subprocess
import sys
import time

WT = "C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b"
sys.path.insert(0, WT)
from tests.test_precommit_hook import HookRepo  # noqa: E402
from tests.test_precommit_hook_phase_b import _ghp  # noqa: E402

HERE = pathlib.Path(__file__).parent
SCR = HERE / ("f5probe_%d" % int(time.time()))
SCR.mkdir()


def classify(out: str) -> str:
    for line in out.splitlines():
        if "pre-commit: " in line and "WARNING" not in line and "NOTE" not in line:
            return line[line.index("pre-commit: "):][:110]
    return "-"


def attempt(label: str, extra: list) -> None:
    r = HookRepo(SCR / label)
    r.git("config", "core.hooksPath", ".githooks")
    tok = _ghp()
    r.stage("g.txt", "gh_token = " + tok + "\n")
    head0 = r.git("rev-parse", "HEAD").strip()
    t0 = time.time()
    p = subprocess.run(
        ["git", *extra, "-c", "user.email=t0b@example.invalid", "-c", "user.name=t0b",
         "-c", "commit.gpgsign=false", "commit", "-q", "-m", "probe"],
        cwd=str(r.root), env=r.env, capture_output=True, timeout=300,
    )
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    assert not any(tok[i:i + 12] in out for i in range(len(tok) - 11)), "token piece in output"
    head1 = r.git("rev-parse", "HEAD").strip()
    print("%-26s rc=%d committed=%s %.1fs first_msg=%s" % (
        label, p.returncode, head1 != head0, time.time() - t0, classify(out)), flush=True)


attempt("control_plain_commit", [])
attempt("probe_c_color_ui_always", ["-c", "color.ui=always"])
