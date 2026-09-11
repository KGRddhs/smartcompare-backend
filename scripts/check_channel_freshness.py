"""Fail CI when the `preview` EAS channel is more than one first-parent commit
behind `origin/main` (W3-13, MB-RECONCILE-06).

Phones run whatever `eas update` last published to the `preview` channel.
Merging to main ships NOTHING to a device (CLAUDE.md "Two-lever launch model"),
and until this guard existed nothing anywhere reported the gap. Measured
2026-09-11 at ed75dc70: the channel ran 97b5f15, **33 first-parent commits
(28 merges + 5 direct pushes) / 141 commits / 311 files** behind main, and CI
was green the whole time. That figure is a dated measurement, not a live
claim — it moves with every merge, and no test in this repo asserts it.

INPUT. Two JSON documents produced by eas-cli (read from the installed 18.8.1
source, not guessed):

  * ``eas update:list --branch preview --limit 1 --json --non-interactive``
    prints ``{...branch, "currentPage": [group, ...]}`` where each group carries
    ``branch, message, runtimeVersion, isRollBackToEmbedded, rolloutPercentage,
    codeSigningKey, group, platforms`` — **no git commit hash**
    (build/update/utils.js getUpdateGroupDescriptionsWithBranch).
  * ``eas update:view <group> --json`` prints a LIST, one entry per platform,
    carrying ``id, createdAt, group, branch, message, runtimeVersion, platform,
    manifestPermalink, isRollBackToEmbedded, gitCommitHash``
    (build/update/utils.js getUpdateJsonInfosForUpdates). eas-cli's
    ``sanitizeValue`` (build/utils/json.js) DROPS keys whose value is null, so a
    publish with no recorded hash has no ``gitCommitHash`` key at all — absent
    means unresolvable, never a KeyError.

Both documents may carry a non-JSON preface: eas-cli resolves its context
(login, and ``npx expo config --json`` for the project id) BEFORE
``enableJsonOutput()`` redirects stdout, so anything logged during context
resolution lands in the redirected file ahead of the JSON. ``load_json_document``
decodes from the first line that starts with ``{`` or ``[``.

EXIT CODES — the contract four documents quote (this docstring, the
``channel-freshness`` comment in .github/workflows/ci.yml, the unit spec and the
PR body), pinned by
``tests/test_channel_freshness.py::test_exit_codes_are_the_documented_contract``:

    0  FRESH         the channel is at most ``--max-behind`` first-parent commits behind
    1  STALE         it is further behind than that
    2  UNRESOLVABLE  empty page / no hash / more than one hash / hash unknown here
    3  NOT_ON_MAIN   published from a commit that is not an ancestor of main
    4  ROLLBACK      the group is a roll-back-to-embedded publish

The CI step treats every non-zero exit as a failure (non-blocking for now).
2 is annotated ``::warning::`` because it usually means the fetch side, not the
phones, is wrong; 1/3/4 are annotated ``::error::``.

STDLIB ONLY. The CI job checks out, runs eas-cli under node and calls this file
with the runner's bare python — there is no ``pip install`` step, and
``tests/test_channel_freshness.py::test_script_is_stdlib_only`` keeps it that
way.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Protocol

FRESH = 0
STALE = 1
UNRESOLVABLE = 2
NOT_ON_MAIN = 3
ROLLBACK = 4

DEFAULT_MAIN_REF = "origin/main"
DEFAULT_MAX_BEHIND = 1
REPO_ROOT = Path(__file__).resolve().parent.parent


class ChannelError(Exception):
    """Anything that makes the channel's commit unresolvable — an empty page, a
    document that is not JSON, an unreadable file, or a git call that failed.
    ``main()`` maps it to UNRESOLVABLE."""


@dataclass(frozen=True)
class GroupRef:
    """One update group as ``eas update:list --json`` describes it."""

    group: str
    runtime_version: str | None
    is_rollback_to_embedded: bool
    message: str | None


class Ancestry(Protocol):
    """The three git questions the verdict needs, injected so the decision logic
    is testable without a repository."""

    def contains(self, sha: str) -> bool: ...

    def is_ancestor_of_main(self, sha: str) -> bool: ...

    def first_parent_distance(self, sha: str) -> int: ...


def load_json_document(text: str) -> object:
    """Decode the JSON document from ``text``, skipping any non-JSON preface."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            body = "\n".join(lines[index:])
            try:
                return json.loads(body)
            except ValueError as exc:
                raise ChannelError(f"eas-cli output is not valid JSON: {exc}") from exc
    raise ChannelError("no JSON document found in the eas-cli output")


def parse_list(payload: object) -> GroupRef:
    """The newest group from ``eas update:list --json``.

    Index 0 is eas-cli's own convention for "latest": it fetches the latest
    group per platform with ``limit: 1, offset: 0`` through the same query
    (build/update/queries.js), reads ``branch.updates[0]`` as the latest
    (build/update/utils.js:170) and labels ``updates[0]`` the "current update"
    (build/project/publish.js:433). The job passes ``--limit 1`` as well. The
    list JSON carries no ``createdAt``, so the first armed run confirms it — the
    view JSON's ``createdAt`` is printed for exactly that reason.
    """
    if not isinstance(payload, dict):
        raise ChannelError(
            f"update:list JSON is not an object (got {type(payload).__name__})"
        )
    page = payload.get("currentPage")
    if not isinstance(page, list) or not page:
        raise ChannelError("no update groups on the branch")
    first = page[0]
    if not isinstance(first, dict) or not first.get("group"):
        raise ChannelError("the first update group carries no group id")
    return GroupRef(
        group=str(first["group"]),
        runtime_version=first.get("runtimeVersion"),
        is_rollback_to_embedded=bool(first.get("isRollBackToEmbedded", False)),
        message=first.get("message"),
    )


def parse_view(payload: object) -> set[str]:
    """The set of commit hashes ``eas update:view --json`` recorded.

    One entry per platform; a key that eas-cli's sanitizer dropped is simply
    absent, which must read as "no hash", never KeyError. A healthy publish
    yields a one-element set; anything else is unresolvable.
    """
    if not isinstance(payload, list):
        raise ChannelError(
            f"update:view JSON is not a list (got {type(payload).__name__})"
        )
    hashes = set()
    for entry in payload:
        if isinstance(entry, dict) and entry.get("gitCommitHash"):
            hashes.add(str(entry["gitCommitHash"]))
    return hashes


def describe_view(payload: object) -> str:
    """A one-line, non-annotated context line for the run log: the platforms the
    group covers and when it was published. ``update:list --json`` has no
    ``createdAt``; this is where the date comes from."""
    entries: Iterable[object] = payload if isinstance(payload, list) else []
    platforms = []
    created = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("platform"):
            platforms.append(str(entry["platform"]))
        created = created or entry.get("createdAt")
    return "platforms={} createdAt={}".format(
        ",".join(platforms) or "unknown", created or "unknown"
    )


class GitAncestry:
    """Ancestry answered by git in ``repo``, comparing against ``main_ref``."""

    def __init__(self, repo: Path, main_ref: str) -> None:
        self.repo = Path(repo)
        self.main_ref = main_ref

    def _git(self, *argv: str) -> subprocess.CompletedProcess:
        # encoding is explicit: `text=True` alone decodes cp1252 on Windows and
        # manufactures mojibake from clean UTF-8 (CLAUDE.md "Windows codec trap").
        return subprocess.run(
            ["git", *argv],
            cwd=str(self.repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def contains(self, sha: str) -> bool:
        return self._git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0

    def is_ancestor_of_main(self, sha: str) -> bool:
        return (
            self._git("merge-base", "--is-ancestor", sha, self.main_ref).returncode == 0
        )

    def first_parent_distance(self, sha: str) -> int:
        proc = self._git(
            "rev-list", "--count", "--first-parent", f"{sha}..{self.main_ref}"
        )
        if proc.returncode != 0:
            raise ChannelError(
                f"git rev-list {sha}..{self.main_ref} failed "
                f"({proc.returncode}): {proc.stderr.strip()}"
            )
        try:
            return int(proc.stdout.strip())
        except ValueError as exc:
            raise ChannelError(
                f"git rev-list printed no count: {proc.stdout!r}"
            ) from exc


def evaluate(
    group: GroupRef,
    hashes: set[str],
    ancestry: Ancestry,
    max_behind: int = DEFAULT_MAX_BEHIND,
) -> tuple[int, str]:
    """The verdict. ``max_behind`` 1 means: a publish from HEAD followed by ONE
    more first-parent commit on main is still fresh; the second one without a
    republish is stale. Direct pushes count exactly like merges — five of the
    33 first-parent commits measured on 2026-09-11 were direct pushes, so a
    merge count would let a direct-push regression through."""
    if group.is_rollback_to_embedded:
        return (
            ROLLBACK,
            f"group {group.group} is a roll-back-to-embedded publish — phones run "
            "the binary's embedded bundle, not a commit",
        )
    if len(hashes) != 1:
        return (
            UNRESOLVABLE,
            f"gitCommitHash unresolvable from update:view (got {sorted(hashes)})",
        )
    sha = next(iter(hashes))
    if not ancestry.contains(sha):
        # NOT a dirty-tree signal: eas.json sets no `cli.requireCommit`, so
        # eas-cli publishes a dirty tree under HEAD's own hash and the JSON
        # carries no dirtiness flag at all.
        return (
            UNRESOLVABLE,
            f"{sha[:8]} is not in this checkout's history (published from an "
            "unpushed branch, a fork, or read from a shallow clone?)",
        )
    if not ancestry.is_ancestor_of_main(sha):
        return NOT_ON_MAIN, f"{sha[:8]} is not an ancestor of main"
    distance = ancestry.first_parent_distance(sha)
    if distance > max_behind:
        return (
            STALE,
            f"preview runs {sha[:8]}, {distance} first-parent commits behind main "
            f"(max {max_behind})",
        )
    return (
        FRESH,
        f"preview runs {sha[:8]}, {distance} first-parent commits behind main "
        f"(max {max_behind})",
    )


def _read(path: Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ChannelError(f"cannot read {path}: {exc}") from exc


def _annotation(code: int) -> str:
    if code == FRESH:
        return ""
    if code == UNRESOLVABLE:
        return "::warning::"
    return "::error::"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list-json", required=True, type=Path)
    parser.add_argument("--view-json", required=True, type=Path)
    parser.add_argument("--main", default=DEFAULT_MAIN_REF)
    parser.add_argument("--max-behind", type=int, default=DEFAULT_MAX_BEHIND)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    ancestry_factory: Callable[[Path, str], Ancestry] = GitAncestry,
) -> int:
    args = _build_parser().parse_args(argv)
    context = None
    try:
        group = parse_list(load_json_document(_read(args.list_json)))
        view_payload = load_json_document(_read(args.view_json))
        hashes = parse_view(view_payload)
        context = "channel group {} runtimeVersion {} {}".format(
            group.group, group.runtime_version or "unknown", describe_view(view_payload)
        )
        code, message = evaluate(
            group, hashes, ancestry_factory(Path(args.repo), args.main), args.max_behind
        )
    except ChannelError as exc:
        code, message = UNRESOLVABLE, str(exc)
    if context:
        print(context)
    print(f"{_annotation(code)}{message}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    return code


if __name__ == "__main__":  # pragma: no cover - exercised by the CI step
    sys.exit(main())
