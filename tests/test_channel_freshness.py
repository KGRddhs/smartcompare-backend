"""Unit tests for `scripts/check_channel_freshness.py` — W3-13 (MB-RECONCILE-06).

The `preview` channel runs whatever `eas update` last published; merging to
main ships NOTHING to a phone (CLAUDE.md "Two-lever launch model"). Measured
2026-09-11 at ed75dc70 the channel ran 97b5f15, 33 first-parent commits behind
main, and CI was green. The script under test is the decision half of the CI
guard: it reads the two eas-cli JSON documents (`update:list --json` and
`update:view <group> --json`), resolves the published commit, and exits
0 fresh / 1 stale / 2 unresolvable / 3 not-on-main / 4 roll-back-to-embedded.

Everything here is offline. The fixtures are inline dicts shaped exactly as
eas-cli 18.8.1 emits them (read from the installed source, not from a live
call — `update:list --json` carries NO `gitCommitHash`, only `update:view`
does, and eas-cli's JSON sanitizer DROPS null-valued keys, so an unhashed
publish has no key at all). Git ancestry is injected through `FakeAncestry`;
the real `GitAncestry` is exercised only against a monkeypatched
`subprocess.run`. No test asserts a real distance — the live number moves with
every merge (ruling 1c).
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_channel_freshness import (
    FRESH,
    NOT_ON_MAIN,
    ROLLBACK,
    STALE,
    UNRESOLVABLE,
    ChannelError,
    GitAncestry,
    GroupRef,
    evaluate,
    load_json_document,
    main,
    parse_list,
    parse_view,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_channel_freshness.py"

# The hash recorded for the 2026-09-02 publish (docs/CONTEXT_SESSION_LOG.md:131).
PHONES = "97b5f1501a1242c405fd3cf12bee9ab419db2bdd"

# `eas update:list --branch preview --limit 1 --json --non-interactive` at
# eas-cli 18.8.1: build/update/queries.js renderUpdateGroupsOnBranch prints
# `{...branch, currentPage: [getUpdateGroupDescriptionsWithBranch(...)]}`. Two
# entries so "index 0 is the newest group" is a real choice, not a tautology.
FAKE_LIST = {
    "name": "preview",
    "id": "branch-0000-1111",
    "currentPage": [
        {
            "branch": "preview",
            "message": "[Sep 02 01:34 by ahmed, runtimeVersion: 1.0.0] M18/M20 set",
            "runtimeVersion": "1.0.0",
            "isRollBackToEmbedded": False,
            "rolloutPercentage": 100,
            "group": "g-newest",
            "platforms": "android, ios",
        },
        {
            "branch": "preview",
            "message": "[Aug 20 22:10 by ahmed, runtimeVersion: 1.0.0] Bundle E",
            "runtimeVersion": "1.0.0",
            "isRollBackToEmbedded": False,
            "rolloutPercentage": 100,
            "group": "g-older",
            "platforms": "android, ios",
        },
    ],
}


def _view(hash_android, hash_ios=None, *, drop_hash=False):
    """`eas update:view <group> --json`: one entry per platform
    (build/update/utils.js getUpdateJsonInfosForUpdates). `drop_hash=True`
    reproduces eas-cli's sanitizeValue, which deletes the key when the server
    sent null."""
    if hash_ios is None:
        hash_ios = hash_android
    entries = []
    for platform, sha in (("android", hash_android), ("ios", hash_ios)):
        entry = {
            "id": f"update-{platform}",
            "createdAt": "2026-09-01T22:34:56.000Z",
            "group": "g-newest",
            "branch": "preview",
            "message": "M18/M20 set",
            "runtimeVersion": "1.0.0",
            "platform": platform,
            "manifestPermalink": f"https://u.expo.dev/update/update-{platform}",
            "isRollBackToEmbedded": False,
            "gitCommitHash": sha,
        }
        if drop_hash:
            del entry["gitCommitHash"]
        entries.append(entry)
    return entries


class FakeAncestry:
    """Injected ancestry: a first-parent main chain m0..m5 (m5 = head) with the
    phones' hash at index 2, plus one commit reachable from the checkout but
    NOT on main. `first_parent_distance` is the index distance to head."""

    main = ["m0", "m1", PHONES, "m3", "m4", "m5"]
    side = {"sidesha"}

    def contains(self, sha: str) -> bool:
        return sha in self.main or sha in self.side

    def is_ancestor_of_main(self, sha: str) -> bool:
        return sha in self.main

    def first_parent_distance(self, sha: str) -> int:
        return len(self.main) - 1 - self.main.index(sha)


# ---------------------------------------------------------------------------
# 1 / 1b / 2 — parse_list + load_json_document
# ---------------------------------------------------------------------------


def test_parse_list_takes_the_first_group():
    """eas-cli itself treats `updates[0]` as the latest group
    (build/update/utils.js:170, build/project/publish.js:433), which is what
    `--limit 1` + index 0 rests on. Mutation that reddens this:
    `currentPage[-1]`."""
    ref = parse_list(FAKE_LIST)
    assert isinstance(ref, GroupRef)
    assert ref.group == "g-newest"
    assert ref.runtime_version == "1.0.0"
    assert ref.is_rollback_to_embedded is False


def test_load_json_document_skips_a_chatter_preface():
    """`update:list` resolves its context (login + `npx expo config --json`)
    BEFORE `enableJsonOutput()` redirects stdout (list.js:41-50), so anything
    eas-cli logs during context resolution lands in the redirected file ahead
    of the JSON. Both loaders must decode from the first line that starts with
    `{` or `[`. Mutation that reddens this: plain `json.loads`."""
    preface = "Some chatter from context resolution\nAnother line without JSON\n"
    assert load_json_document(preface + json.dumps(FAKE_LIST)) == FAKE_LIST
    view = _view(PHONES)
    assert load_json_document(preface + json.dumps(view)) == view
    with pytest.raises(ChannelError):
        load_json_document("garbage only\nno document here\n")


def test_parse_list_empty_page_is_a_channel_error():
    """A branch with no update groups is UNRESOLVABLE, surfaced as the one
    exception type `main()` maps to exit 2. Mutation that reddens this:
    returning None instead of raising."""
    with pytest.raises(ChannelError):
        parse_list({"name": "preview", "id": "b", "currentPage": []})


# ---------------------------------------------------------------------------
# 3 — parse_view
# ---------------------------------------------------------------------------


def test_parse_view_absent_hash_is_not_a_hash():
    """eas-cli's `sanitizeValue` (build/utils/json.js:26-42) drops every key
    whose value is null, so a group published without a git hash has NO
    `gitCommitHash` key — not `None`. Absent must mean "not counted", never
    KeyError. Mutation that reddens the first case: `u["gitCommitHash"]`."""
    assert parse_view(_view(PHONES, drop_hash=True)) == set()
    assert parse_view(_view(PHONES)) == {PHONES}
    assert parse_view(_view(PHONES, "m4")) == {PHONES, "m4"}


# ---------------------------------------------------------------------------
# 3b — the exit-code contract itself (ruling 19)
# ---------------------------------------------------------------------------


def test_exit_codes_are_the_documented_contract():
    """FOUR documents quote "0 fresh / 1 stale / 2 unresolvable / 3 not-on-main
    / 4 roll-back-to-embedded" as a promise to a reader who cannot import this
    module: the script's own module docstring, the `channel-freshness` comment
    in `.github/workflows/ci.yml`, the unit spec's section 4.3 exit-code
    contract, and the PR body. Every other test here compares against the
    imported constants, so renumbering them keeps the suite green while all
    four documents become wrong. This is the only assertion that pins the
    numbers. Mutation that reddens it: any renumbering."""
    assert (FRESH, STALE, UNRESOLVABLE, NOT_ON_MAIN, ROLLBACK) == (0, 1, 2, 3, 4)


# ---------------------------------------------------------------------------
# 4 — evaluate: the verdict table over injected ancestry
# ---------------------------------------------------------------------------


def _group(**overrides) -> GroupRef:
    fields = {
        "group": "g-newest",
        "runtime_version": "1.0.0",
        "is_rollback_to_embedded": False,
        "message": "M18/M20 set",
    }
    fields.update(overrides)
    return GroupRef(**fields)


@pytest.mark.parametrize(
    "hashes, group_overrides, max_behind, expected_code, expected_substring",
    [
        pytest.param({"m5"}, {}, 1, FRESH, None, id="at-head-fresh"),
        pytest.param({"m4"}, {}, 1, FRESH, None, id="one-behind-still-fresh"),
        pytest.param(
            {PHONES},
            {},
            1,
            STALE,
            "first-parent commits behind main (max 1)",
            id="phones-three-behind-stale",
        ),
        pytest.param(set(), {}, 1, UNRESOLVABLE, None, id="no-hash-unresolvable"),
        pytest.param(
            {"deadbeef"}, {}, 1, UNRESOLVABLE, None, id="unknown-sha-unresolvable"
        ),
        pytest.param(
            {"m5", "m4"}, {}, 1, UNRESOLVABLE, None, id="two-hashes-unresolvable"
        ),
        pytest.param(
            {"sidesha"}, {}, 1, NOT_ON_MAIN, None, id="side-branch-not-on-main"
        ),
        pytest.param(
            {"m5"},
            {"is_rollback_to_embedded": True},
            1,
            ROLLBACK,
            None,
            id="rollback-to-embedded",
        ),
        pytest.param(
            {PHONES}, {}, 3, FRESH, None, id="max-behind-3-makes-phones-fresh"
        ),
    ],
)
def test_evaluate_verdicts(
    hashes, group_overrides, max_behind, expected_code, expected_substring
):
    """Exit-code contract: 0 fresh, 1 stale, 2 unresolvable (no hash / >1 hash /
    hash unknown to the checkout), 3 published from a commit not on main,
    4 roll-back-to-embedded. `--max-behind 1` means a publish from HEAD followed
    by ONE more first-parent commit is still fresh; the second is stale.

    Mutations that redden this: `d >= max_behind` (the one-behind case);
    dropping the `contains` check (deadbeef would fall through to
    `is_ancestor_of_main` and answer 3, not 2); dropping the rollback branch.
    Ruling 12: assert the code, then only the STALE substring — never prose.
    """
    code, message = evaluate(
        _group(**group_overrides), set(hashes), FakeAncestry(), max_behind
    )
    assert code == expected_code
    assert (
        isinstance(message, str) and message.strip()
    ), "verdict message must be non-empty"
    if expected_substring is not None:
        assert expected_substring in message
    if hashes == {"deadbeef"}:
        # Ruling 2(c): eas.json sets no cli.requireCommit, so eas-cli publishes
        # a dirty tree under HEAD's hash — an unknown hash is NOT a dirty-tree
        # signal and the message must not claim it is.
        assert "dirty" not in message.lower()


# ---------------------------------------------------------------------------
# 5 — GitAncestry: exact argv, first-parent, cwd
# ---------------------------------------------------------------------------


def _record_git(monkeypatch, returncode=0, stdout="33\n"):
    calls = []

    def fake_run(argv, *args, **kwargs):
        calls.append((list(argv), kwargs))
        return subprocess.CompletedProcess(
            list(argv), returncode, stdout=stdout, stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_git_ancestry_uses_first_parent_and_merge_base(monkeypatch, tmp_path):
    """The distance is FIRST-PARENT commits, not all commits: on the measured
    history the plain count was 141 where the first-parent count was 33, and
    a direct push to main must count the same as a merge (section 3.1).
    Mutation that reddens this: dropping `--first-parent`."""
    calls = _record_git(monkeypatch)
    ancestry = GitAncestry(tmp_path, "origin/main")

    assert ancestry.first_parent_distance("abc") == 33
    assert ancestry.is_ancestor_of_main("abc") is True
    assert ancestry.contains("abc") is True

    assert [c[0] for c in calls] == [
        ["git", "rev-list", "--count", "--first-parent", "abc..origin/main"],
        ["git", "merge-base", "--is-ancestor", "abc", "origin/main"],
        ["git", "cat-file", "-e", "abc^{commit}"],
    ]

    # every call runs in the repo the caller named (str or Path accepted)
    for _argv, kwargs in calls:
        assert "cwd" in kwargs, "git must be run with cwd=<repo>"
        assert Path(kwargs["cwd"]) == tmp_path


def test_git_ancestry_nonzero_exit_is_false_or_a_channel_error(monkeypatch, tmp_path):
    """Ruling 6: `cat-file -e` and `merge-base --is-ancestor` use the return
    code as the boolean; a non-zero `rev-list --count` (unknown ref) is a
    ChannelError, which `main()` maps to exit 2."""
    _record_git(monkeypatch, returncode=1, stdout="")
    ancestry = GitAncestry(tmp_path, "origin/main")
    assert ancestry.contains("abc") is False
    assert ancestry.is_ancestor_of_main("abc") is False
    with pytest.raises(ChannelError):
        ancestry.first_parent_distance("abc")


# ---------------------------------------------------------------------------
# 6 — the script is stdlib-only (the CI job runs no `pip install`)
# ---------------------------------------------------------------------------


def test_script_is_stdlib_only():
    """The channel-freshness CI job installs nothing with pip: it checks out,
    runs eas-cli under node, and calls this script with the runner's bare
    python. Every import root must therefore be in `sys.stdlib_module_names`
    (Python 3.10+; measured on 3.12.9: 301 names, `json` and `__future__` in,
    `yaml` NOT in). Mutation that reddens this: `import yaml`."""
    assert SCRIPT.exists(), f"script absent: {SCRIPT}"
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                roots.add("<relative import>")
            else:
                roots.add(node.module.split(".")[0])
    assert roots, "no imports found — the AST walk is broken"
    non_stdlib = sorted(r for r in roots if r not in sys.stdlib_module_names)
    assert not non_stdlib, f"non-stdlib imports in the CI script: {non_stdlib}"


# ---------------------------------------------------------------------------
# 7 — main(): exit codes, ::error:: / ::warning:: annotations, step summary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "list_payload, view_payload, expected_code, expected_prefix",
    [
        pytest.param(
            FAKE_LIST, _view(PHONES), STALE, "::error::", id="stale-is-an-error"
        ),
        pytest.param(
            {"name": "preview", "id": "b", "currentPage": []},
            _view(PHONES),
            UNRESOLVABLE,
            "::warning::",
            id="empty-page-is-a-warning",
        ),
        pytest.param(
            FAKE_LIST,
            _view(PHONES, drop_hash=True),
            UNRESOLVABLE,
            "::warning::",
            id="no-hash-is-a-warning",
        ),
        pytest.param(FAKE_LIST, _view("m5"), FRESH, None, id="fresh-has-no-annotation"),
    ],
)
def test_main_exit_codes_and_annotations(
    tmp_path,
    monkeypatch,
    capsys,
    list_payload,
    view_payload,
    expected_code,
    expected_prefix,
):
    """The CI step treats every non-zero exit as a failure; STALE / NOT_ON_MAIN /
    ROLLBACK annotate with `::error::`, UNRESOLVABLE with `::warning::` (it
    usually means the fetch side, not the phones, is wrong), FRESH prints no
    `::` annotation at all. The same summary line is appended to
    `$GITHUB_STEP_SUMMARY` when that variable is set. Ancestry is injected via
    the `ancestry_factory` hook (ruling 5) — no class-attribute patching.
    Mutation that reddens this: swapping the error/warning prefixes."""
    list_path = tmp_path / "preview-list.json"
    view_path = tmp_path / "preview-group.json"
    list_path.write_text(json.dumps(list_payload), encoding="utf-8")
    view_path.write_text(json.dumps(view_payload), encoding="utf-8")
    summary_path = tmp_path / "step-summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))

    seen = {}

    def factory(repo, main_ref):
        seen["repo"] = Path(repo)
        seen["main_ref"] = main_ref
        return FakeAncestry()

    rc = main(
        [
            "--list-json",
            str(list_path),
            "--view-json",
            str(view_path),
            "--main",
            "origin/main",
            "--max-behind",
            "1",
            "--repo",
            str(tmp_path),
        ],
        ancestry_factory=factory,
    )
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.strip()]

    assert rc == expected_code
    assert lines, "main() printed nothing"
    annotated = [ln for ln in lines if ln.startswith("::")]
    if expected_prefix is None:
        assert annotated == [], f"FRESH must not annotate, got {annotated}"
        summary_line = lines[-1]
    else:
        assert (
            len(annotated) == 1
        ), f"expected exactly one annotation line, got {annotated}"
        assert annotated[0].startswith(expected_prefix), annotated[0]
        summary_line = annotated[0][len(expected_prefix) :]
        wrong = "::warning::" if expected_prefix == "::error::" else "::error::"
        assert not any(ln.startswith(wrong) for ln in lines)

    assert summary_path.exists(), "GITHUB_STEP_SUMMARY was set but nothing was appended"
    assert summary_line.strip() in summary_path.read_text(encoding="utf-8")

    if expected_code in (FRESH, STALE):
        assert seen["main_ref"] == "origin/main"
        assert seen["repo"] == tmp_path
