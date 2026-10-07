"""Functional tests of the repo's .gitleaks.toml with the real gitleaks
(T0b Phase B: spec R1.4, review corrections 2 and 3 of the spec, addendum
section 3.5, review corrections 2, 3 and 4 of Phase B, rulings TB4 and TB5).

Every node skips with "gitleaks not on PATH" where gitleaks is not installed
(CI's backend-tests job); CI's secret-scan job runs the real scan. Where it is
installed, every node first asserts that the repo carries .gitleaks.toml, so
at the base (no config) each node fails by an assertion.

Each staged case runs gitleaks the way the hook does (git mode, --pre-commit
--staged, --redact) in a tmp repo, with --config naming the repo's file and
GITLEAKS_CONFIG(_TOML) removed from the environment, and reads a template
report that carries the rule id and the path only. Every sentinel is built at
runtime; no 12-character piece of one may appear in gitleaks' output.

The PR-range node replays the nine merged PR ranges that carried findings
under the default rules (addendum 2h) and expects 0 findings with the repo
config; it skips when a merge commit is not in the clone (CI depth 1).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / ".gitleaks.toml"
GITLEAKS = shutil.which("gitleaks")

pytestmark = pytest.mark.skipif(GITLEAKS is None, reason="gitleaks not on PATH")

TEMPLATE = "{{ range . }}{{ .RuleID }} {{ .File }}\n{{ end }}"


# ---------------------------------------------------------------------------
# Runtime-built sentinels (never literals)
# ---------------------------------------------------------------------------


def _jwt() -> str:
    head = "ey" + "J" + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    body = "ey" + "J" + "zdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkZha2UifQ"
    sig = "Zm9vYmFy" + "QmF6cXV4" + "WFlaMTIzNDU2Nzg5MA"
    return head + "." + body + "." + sig


def _aws() -> str:
    return "AK" + "IA" + "Z7QW2RTY" + "UI3OPLKJ"


def _sk() -> str:
    return "sk" + "-" + "proj-" + "T3Blbk" + "FJ" + "Qx7Lm2Np9Rt4Vw" * 3


def _ghp() -> str:
    return "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0" + "K1l2M3n4O5p6Q7r8"


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode("ascii")).hexdigest()


def _mixed17() -> str:
    return "Xq7" + "Lm2Np9" + "Rt4Vw8Zb"


def _public_client_key() -> str:
    # A 32-character key of the kind third-party pages embed (generic-api-key).
    return "a7f3c9e1" + "b5d2f8a4" + "c6e0b9d3" + "f1a7c5e2"


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _env(base: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.pop("GITLEAKS_CONFIG", None)
    env.pop("GITLEAKS_CONFIG_TOML", None)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    for key, sub in (("HOME", "home"), ("XDG_CONFIG_HOME", "xdg"), ("TMPDIR", "tmp")):
        d = base / sub
        d.mkdir(parents=True, exist_ok=True)
        env[key] = str(d)
    return env


class GlRepo:
    def __init__(self, base: Path):
        self.base = base
        self.root = base / "repo"
        self.root.mkdir()
        self.env = _env(base)
        self.git("init", "-q")
        self.stage("base.txt", "base\n")
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
            "init",
        )

    def git(self, *args: str) -> None:
        p = subprocess.run(
            ["git", *args],
            cwd=str(self.root),
            env=self.env,
            capture_output=True,
            timeout=60,
        )
        assert p.returncode == 0, "harness: git %s failed: %r" % (args, p.stderr[-300:])

    def stage(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        self.git("add", "--", rel)

    def scan(self, config: Path) -> tuple:
        tmpl = self.base / "ids.tmpl"
        tmpl.write_text(TEMPLATE, encoding="ascii")
        report = self.base / "report.txt"
        p = subprocess.run(
            [
                GITLEAKS,
                "git",
                "--pre-commit",
                "--staged",
                "--redact",
                "--no-banner",
                "--log-level",
                "error",
                "--ignore-gitleaks-allow",
                "--config",
                str(config),
                "--report-format",
                "template",
                "--report-template",
                str(tmpl),
                "--report-path",
                str(report),
                str(self.root),
            ],
            cwd=str(self.root),
            env=self.env,
            capture_output=True,
            timeout=120,
        )
        out = (p.stdout + p.stderr).decode("utf-8", "replace")
        rows = report.read_text(encoding="utf-8").split() if report.exists() else []
        return p.returncode, rows[0::2], out


def _config_path() -> Path:
    assert CONFIG.is_file(), "the repo has no .gitleaks.toml (R1.4)"
    return CONFIG


def _no_piece(out: str, secret: str) -> None:
    for i in range(len(secret) - 11):
        assert secret[i : i + 12] not in out, "gitleaks printed a piece of a sentinel"


# Staged cases that the repo config must still REPORT (rc 1).
REPORTED = {
    "jwt": ("cfg.txt", lambda: "token = " + _jwt() + "\n", _jwt),
    "aws_key": ("cfg.txt", lambda: "id = " + _aws() + "\n", _aws),
    "sk_key": ("cfg.txt", lambda: "key = " + _sk() + "\n", _sk),
    "github_token": ("cfg.txt", lambda: "gh_token = " + _ghp() + "\n", _ghp),
    "admin_api_key_hex64": (
        "cfg.py",
        lambda: 'ADMIN_API_KEY = "' + _hex64("adm") + '"\n',
        lambda: _hex64("adm"),
    ),
    # Review correction 2: the three shapes the draft digest allowlist hid.
    "attr_token_hex64": (
        "svc.py",
        lambda: 'self.token = "' + _hex64("tok") + '"\n',
        lambda: _hex64("tok"),
    ),
    "attr_key_hex64": (
        "svc.py",
        lambda: 'settings.key = "' + _hex64("key") + '"\n',
        lambda: _hex64("key"),
    ),
    "yaml_auth_key_hex64": (
        "cfg.yml",
        lambda: "auth.key: " + _hex64("yml") + "\n",
        lambda: _hex64("yml"),
    ),
    # Review correction 3: a password outside the one fixture file.
    "password_outside_fixture_file": (
        "tests/test_x.py",
        lambda: '{"password": "' + _mixed17() + '"}\n',
        _mixed17,
    ),
    # TB5: the jwt rule stays active under tests/fixtures/.
    "jwt_in_fixtures": (
        "tests/fixtures/page.html",
        lambda: "<meta data-t='" + _jwt() + "'>\n",
        _jwt,
    ),
}

# Benign shapes the repo config must CLEAR (rc 0).
CLEARED = {
    "file_digest": ("report.md", lambda: "api.ts: " + _hex64("digest") + "\n"),
    "workflow_row_id": (
        "wf.js",
        lambda: "{ key: '" + "expo-sdk54-u4b" + "', prompt: 'x' }\n",
    ),
    "pytest_name": (
        "notes.md",
        lambda: "api_key=test_" + "reviewer_sentinel_is_not_logged" + "\n",
    ),
    "password_fixture_file": (
        "tests/test_retro_w1_9_429.py",
        lambda: '{"new_password": "' + _mixed17() + '"}\n',
    ),
    "public_client_key_in_fixtures": (
        "tests/fixtures/captured.json",
        lambda: '{"apiKey": "' + _public_client_key() + '"}\n',
    ),
}


@pytest.mark.parametrize("case", sorted(REPORTED))
def test_repo_config_still_reports(case: str, tmp_path: Path) -> None:
    config = _config_path()
    rel, body, secret = REPORTED[case]
    r = GlRepo(tmp_path)
    r.stage(rel, body())
    rc, rules, out = r.scan(config)
    assert rc == 1 and rules, "the repo config hides %s: rc=%s rules=%s" % (
        case,
        rc,
        rules,
    )
    _no_piece(out, secret())


@pytest.mark.parametrize("case", sorted(CLEARED))
def test_repo_config_clears_benign_shapes(case: str, tmp_path: Path) -> None:
    config = _config_path()
    rel, body = CLEARED[case]
    r = GlRepo(tmp_path)
    r.stage(rel, body())
    rc, rules, out = r.scan(config)
    assert rc == 0 and not rules, "the repo config reports %s: rc=%s rules=%s" % (
        case,
        rc,
        rules,
    )


def test_a_config_without_extend_would_report_nothing(tmp_path: Path) -> None:
    # The mutant of spec correction 2, measured inside the test so the test
    # proves it can see it: drop [extend] and the default rules are gone.
    # targetRules lines go too: gitleaks 8.30.1 refuses to load an allowlist
    # whose targetRules name a rule that does not exist (measured: rc 1,
    # "target rule ID 'generic-api-key' does not exist"), which would fail
    # closed rather than show the fail-open state this mutant is about.
    config = _config_path()
    text = config.read_text(encoding="utf-8")
    assert "[extend]" in text and "useDefault = true" in text
    kept = [
        ln
        for ln in text.splitlines()
        if ln.strip() not in ("[extend]", "useDefault = true")
        and not ln.strip().startswith("targetRules")
    ]
    stripped = tmp_path / "no_extend.toml"
    stripped.write_text("\n".join(kept) + "\n", encoding="utf-8")
    r = GlRepo(tmp_path)
    r.stage("cfg.txt", "token = " + _jwt() + "\n")
    rc_real, _, _ = r.scan(config)
    rc_mutant, _, _ = r.scan(stripped)
    assert rc_real == 1, "the repo config does not report a staged JWT"
    assert rc_mutant == 0, "without [extend] the default rules should be gone"


# The nine merged PRs whose ranges carried findings under the default rules
# (addendum 2h): with the repo config each range reports 0.
PR_NUMBERS = [297, 289, 256, 214, 209, 208, 197, 195, 194]


def _merge_sha(number: int) -> str | None:
    p = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "log",
            "--first-parent",
            "--merges",
            "--format=%H %s",
            "-n",
            "400",
            "HEAD",
        ],
        capture_output=True,
        timeout=60,
    )
    if p.returncode != 0:
        return None
    needle = "Merge pull request #%d " % number
    for line in p.stdout.decode("utf-8", "replace").splitlines():
        sha, _, subject = line.partition(" ")
        if subject.startswith(needle):
            return sha
    return None


@pytest.mark.parametrize("number", PR_NUMBERS)
def test_repo_config_clears_the_merged_pr_ranges(number: int, tmp_path: Path) -> None:
    config = _config_path()
    sha = _merge_sha(number)
    if sha is None:
        pytest.skip("merge of PR #%d is not in this clone" % number)
    tmpl = tmp_path / "ids.tmpl"
    tmpl.write_text(
        "{{ range . }}{{ .RuleID }} {{ .File }}\n{{ end }}", encoding="ascii"
    )
    report = tmp_path / "report.txt"
    p = subprocess.run(
        [
            GITLEAKS,
            "git",
            "--log-opts=%s^1..%s^2" % (sha, sha),
            "--redact",
            "--no-banner",
            "--log-level",
            "error",
            "--ignore-gitleaks-allow",
            "--config",
            str(config),
            "--report-format",
            "template",
            "--report-template",
            str(tmpl),
            "--report-path",
            str(report),
            str(REPO_ROOT),
        ],
        cwd=str(REPO_ROOT),
        env=_env(tmp_path),
        capture_output=True,
        timeout=300,
    )
    rows = report.read_text(encoding="utf-8").split() if report.exists() else []
    assert p.returncode == 0 and not rows, "PR #%d range: rc=%s findings %s" % (
        number,
        p.returncode,
        list(zip(rows[0::2], rows[1::2])),
    )
