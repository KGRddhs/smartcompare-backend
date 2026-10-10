"""m4 probe (TBF14): hook variants x locale scenarios x {sh, dash}, dead awk,
gitleaks stripped. The Phase A harness keeps every run hermetic (GIT_* dropped,
GIT_CONFIG_NOSYSTEM=1, tmp HOME / XDG_CONFIG_HOME / TMPDIR). The 0xFF byte is
built in Python. Prints rc + the class of the first hook message only, and
asserts no 12-character piece of the key reaches the output.
"""
import hashlib
import os
import pathlib
import subprocess
import sys
import time

WT = "C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b"
sys.path.insert(0, WT)
from tests.test_precommit_hook import HookRepo, SHELLS, _akia  # noqa: E402
from tests.test_precommit_hook_phase_b import _without_gitleaks  # noqa: E402

HERE = pathlib.Path(__file__).parent
SCR = HERE / ("m1probe_%d" % int(time.time()))
SCR.mkdir()
sys.path.insert(0, str(HERE))
import mut  # noqa: E402

CUR = (pathlib.Path(WT) / ".githooks/pre-commit").read_bytes()
M4 = CUR
for old, new, count in mut.MUTANTS["m1_ext_reader_dropped"][1]:
    assert M4.count(old) == count
    M4 = M4.replace(old, new)
BASE = subprocess.run(
    ["git", "-C", WT, "show", "845ece15:.githooks/pre-commit"], capture_output=True, check=True
).stdout
VARIANTS = {
    "cur": CUR.replace(b"\r\n", b"\n"),
    "m1": M4.replace(b"\r\n", b"\n"),
    "base": BASE.replace(b"\r\n", b"\n"),
}


def classify(out: str) -> str:
    for line in out.splitlines():
        if "pre-commit: " in line and "WARNING" not in line and "NOTE" not in line:
            msg = line[line.index("pre-commit: "):]
            if msg.startswith("pre-commit: staged diff contains what looks like a credential"):
                return "FOUR"
            return "OTHER:" + msg[:50]
    return "-"


def run(variant: str, scen: str, shell: str, n: int) -> str:
    r = HookRepo(SCR / ("%s_%s_%s_%d" % (variant, scen, shell, n)))
    (r.root / ".githooks/pre-commit").write_bytes(VARIANTS[variant])
    env = dict(r.env)
    env["PATH"] = _without_gitleaks(env["PATH"])
    d = r.base / "t0bshim_awk"
    d.mkdir()
    (d / "awk").write_bytes(b"#!/bin/sh\nexit 1\n")
    os.chmod(d / "awk", 0o755)
    env["PATH"] = str(d) + os.pathsep + env["PATH"]
    key = _akia()
    ext = r.root / "ext.sh"
    ext.write_bytes(b"#!/bin/sh\nsed 's/^/+/' \"$5\" | tr 'A-Za-z' 'N-ZA-Mn-za-m'\n")
    r.git("config", "diff.external", "sh " + ext.as_posix())
    rot = key.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                                      "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"))
    r.stage("conf/a.cfg", ("vq = " + rot + " pns").encode() + bytes([0xFF]) + b"\n")
    if scen.endswith("_utf8"):
        env["LC_ALL"] = "C.UTF-8"
    p = subprocess.run([SHELLS[shell], ".githooks/pre-commit"], cwd=str(r.root), env=env,
                       capture_output=True, timeout=120)
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    assert not any(key[i:i + 12] in out for i in range(len(key) - 11)), "key piece in output"
    return "rc=%d %s" % (p.returncode, classify(out))


n = 0
for scen in ("extdiff_sameline_utf8", "extdiff_sameline_default"):
    for variant in ("base", "cur", "m1"):
        for shell in ("sh", "dash"):
            n += 1
            print("%-17s %-5s %-5s %s" % (scen, variant, shell, run(variant, scen, shell, n)), flush=True)
print("variants sha:", {k: hashlib.sha256(v).hexdigest()[:12] for k, v in VARIANTS.items()})
