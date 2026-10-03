"""`.claude/` hygiene pins (T0b Phase A, tests T1 and T4).

T1: every `.claude/skills/*/SKILL.md` opens with a YAML frontmatter block that
`yaml.safe_load` parses into a mapping with a non-empty `name` and
`description`. A bare `: ` inside an unquoted value (for example a
`last_verified` date followed by "(partial re-check 2026-09-29: ...)") makes
the block unparseable, and a skill whose frontmatter does not parse is not
discovered by its trigger description. The pre-commit hook runs the same check
on staged SKILL.md files; this pytest is the CI half.

T4: `.claude/settings.local.json` is a personal, machine-local settings file
(every "always allow" rewrites it). It must not be tracked, and `.gitignore`
must list it so it is not re-added by a `git add .`. A global excludes file on
one machine is not enough: the `.gitignore` line is what other contributors
get.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
SKILL_FILES = sorted(SKILLS_DIR.glob("*/SKILL.md"))
SETTINGS_LOCAL = ".claude/settings.local.json"

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def test_the_repo_carries_skills():
    assert SKILL_FILES, "no .claude/skills/*/SKILL.md found; the pin checks nothing"


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
def test_skill_frontmatter_parses_and_has_name_and_description(path: Path):
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    m = FRONTMATTER.match(text)
    assert m, "%s does not open with a '---' frontmatter block" % _rel(path)
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        reason = str(exc).replace("\n", " ")
        pytest.fail("%s frontmatter does not parse: %s" % (_rel(path), reason))
    assert isinstance(data, dict), "%s frontmatter is not a mapping" % _rel(path)
    for key in ("name", "description"):
        value = data.get(key)
        ok = isinstance(value, str) and value.strip()
        assert ok, "%s frontmatter has no non-empty %r" % (_rel(path), key)


def _git(*args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def test_settings_local_json_is_not_tracked():
    listed = _git("ls-files", "--", SETTINGS_LOCAL)
    if listed.returncode != 0:
        pytest.skip("git not available: %s" % listed.stderr.strip()[:200])
    tracked = listed.stdout.strip()
    assert tracked == "", "%s is tracked (git rm --cached owed)" % SETTINGS_LOCAL


def test_gitignore_lists_settings_local_json():
    text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    lines = {ln.strip() for ln in text.splitlines()}
    listed = SETTINGS_LOCAL in lines or "/" + SETTINGS_LOCAL in lines
    assert listed, ".gitignore does not list %s" % SETTINGS_LOCAL
