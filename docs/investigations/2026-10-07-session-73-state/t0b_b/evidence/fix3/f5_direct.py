"""F5 diagnosis (same measurement window): the real gitleaks 8.30.1 run
DIRECTLY in a scratch repo with a staged GitHub-token shape, with and without
GIT_CONFIG_PARAMETERS='color.ui'='always', and with the hook's GIT_CONFIG_COUNT
override on top. --redact, a rule-id + path template report; prints rc and the
rule ids only.
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
r = HookRepo(HERE / ("f5direct_%d" % int(time.time())))
tok = _ghp()
r.stage("g.txt", "gh_token = " + tok + "\n")
tmpl = r.base / "t.tmpl"
tmpl.write_text("{{ range . }}{{ .RuleID }} {{ .File }}:{{ .StartLine }}\n{{ end }}", encoding="ascii")
OVR = {"GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "color.ui", "GIT_CONFIG_VALUE_0": "never",
       "GIT_CONFIG_KEY_1": "color.diff", "GIT_CONFIG_VALUE_1": "never"}
CASES = {
    "no_params": {},
    "params_always": {"GIT_CONFIG_PARAMETERS": "'color.ui'='always'"},
    "params_always_plus_override": dict(OVR, GIT_CONFIG_PARAMETERS="'color.ui'='always'"),
    "repo_config_always_plus_override": dict(OVR),
}
for name, extra in CASES.items():
    if name.startswith("repo_config"):
        r.git("config", "color.ui", "always")
    env = dict(r.env)
    env.update(extra)
    rep = r.base / (name + ".txt")
    p = subprocess.run(["gitleaks", "git", "--pre-commit", "--staged", "--redact", "--no-banner", "--no-color",
                        "--log-level", "error", "--report-format", "template", "--report-template", str(tmpl),
                        "--report-path", str(rep), str(r.root)], cwd=str(r.root), env=env,
                       capture_output=True, timeout=120)
    out = (p.stdout + p.stderr).decode("utf-8", "replace") + (rep.read_text() if rep.exists() else "")
    assert not any(tok[i:i + 12] in out for i in range(len(tok) - 11)), "token piece in output"
    rules = [ln.split()[0] for ln in (rep.read_text().splitlines() if rep.exists() else []) if ln.strip()]
    print("%-34s rc=%d rules=%s" % (name, p.returncode, rules), flush=True)
