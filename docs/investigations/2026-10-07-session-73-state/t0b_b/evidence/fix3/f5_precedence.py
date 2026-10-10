"""F5 companion (no gitleaks, no secret): does `git -c color.ui=always commit`
reach the hook, and which value does a git child of the hook see with and
without the hook's GIT_CONFIG_COUNT override? Hermetic env of the Phase A
harness; a throwaway hook that prints config values only.
"""
import pathlib
import subprocess
import sys
import time

WT = "C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b"
sys.path.insert(0, WT)
from tests.test_precommit_hook import HookRepo  # noqa: E402

HERE = pathlib.Path(__file__).parent
r = HookRepo(HERE / ("f5prec_%d" % int(time.time())))
r.write(".githooks/pre-commit", (
    "#!/bin/sh\n"
    'if [ -n "${GIT_CONFIG_PARAMETERS:-}" ]; then echo "PARAMS=set"; else echo "PARAMS=unset"; fi\n'
    'echo "plain=$(git config --get color.ui)"\n'
    'echo "override=$(GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=color.ui GIT_CONFIG_VALUE_0=never '
    'GIT_CONFIG_KEY_1=color.diff GIT_CONFIG_VALUE_1=never git config --get color.ui)"\n'
    "exit 1\n"
))
r.git("config", "core.hooksPath", ".githooks")
r.stage("k.txt", "plain text\n")
for extra in ([], ["-c", "color.ui=always"]):
    p = subprocess.run(["git", *extra, "-c", "user.email=t0b@example.invalid", "-c", "user.name=t0b",
                        "commit", "-q", "-m", "x"], cwd=str(r.root), env=r.env, capture_output=True, timeout=120)
    print(extra or ["(plain)"], (p.stdout + p.stderr).decode("utf-8", "replace").split())
