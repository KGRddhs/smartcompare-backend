"""Apply config-audit batch A to ~/.claude/settings.json (session 71, 2026-10-03).

Ahmed approved batch A of CONFIG_AUDIT_PLAN.md. Permission rules are his
security settings, so this script is for HIM to run; no agent runs it with
--apply.

What it changes (and nothing else; every other key is kept as it is):

  1. permissions.deny  += the R1 list (prod-secret dump paths, destructive git,
     shutdown, recursive deletes). Existing deny entries are kept.
  2. enabledPlugins    -> false for the plugins the audit found unused or
     duplicated: superpowers, railway, github, figma, code-review, feature-dev,
     code-simplifier (all @claude-plugins-official). codex@openai-codex is
     touched only with --with-codex.
  3. env               += CLAUDE_CODE_SUBAGENT_MODEL=opus and
     CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1 (rule: Fable orchestrates, every agent
     is Opus).

One deliberate refinement of the R1 list: plain `git push --force` / `-f` is
denied, `git push --force-with-lease` is NOT. The unit flow rebases a branch
onto a moved main and needs the lease form; the lease form cannot overwrite
work it has not seen.

Usage (from any directory):

    python apply_audit_batch_a.py              # dry run: prints the plan only
    python apply_audit_batch_a.py --apply      # backup, then write
    python apply_audit_batch_a.py --restore    # put the newest backup back

After --apply (each in an interactive `claude` terminal, they cannot be
scripted):

    claude mcp add railway --scope user -- railway mcp
    /plugin update context7
    /mcp          (authenticate sentry and supabase)

Then start a NEW session; plugin and env changes are read at session start.

What changes for the agent afterwards (so it is not a surprise):
  - `railway variables ...` is blocked in Bash. Variable NAMES are checked with
    `railway run -s <svc> python -c "import os; print('NAME' in os.environ)"`;
    a variable is set through the Railway MCP `set_variables` tool or by you.
  - `.env` files cannot be read with the Read tool. A Bash `cat .env` is not
    reliably covered by Read rules; the repo rule (never print secrets) still
    carries that case.

Pure stdlib. Prints key names and rule strings only, never a whole settings
file.
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

SETTINGS = Path.home() / ".claude" / "settings.json"

DENY = [
    # production-secret dump paths (repo principle 10; the 2026-09-07 incident)
    "Bash(railway variables*)",
    "mcp__railway__list_variables",
    "mcp__plugin_railway_railway__list_variables",
    "Bash(env)",
    "Bash(printenv*)",
    "Read(**/.env)",
    "Read(**/.env.*)",
    "Read(//**/.env)",
    "Read(//**/.env.*)",
    # destructive git (the W1-9 wipe; never stash or reset in the shared clone)
    "Bash(git checkout -- *)",
    "Bash(git stash*)",
    "Bash(git reset --hard*)",
    "Bash(git clean*)",
    "Bash(git push --force)",
    "Bash(git push --force *)",
    "Bash(git push -f)",
    "Bash(git push -f *)",
    # machine
    "Bash(shutdown*)",
    "PowerShell(Stop-Computer*)",
    # the junction hazard: recursive deletes can follow a node_modules junction
    "PowerShell(Remove-Item*-Recurse*)",
]

PLUGINS_OFF = [
    "superpowers@claude-plugins-official",
    "railway@claude-plugins-official",
    "github@claude-plugins-official",
    "figma@claude-plugins-official",
    "code-review@claude-plugins-official",
    "feature-dev@claude-plugins-official",
    "code-simplifier@claude-plugins-official",
]
CODEX = "codex@openai-codex"

ENV = {
    "CLAUDE_CODE_SUBAGENT_MODEL": "opus",
    "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
}


def plan(settings: dict, with_codex: bool, skip_deny: bool = False) -> tuple[dict, list[str]]:
    """The merged settings and a human-readable list of what moves.

    ``skip_deny`` leaves the ``permissions`` block untouched (not even created):
    the agent may run the plugin and env part on the owner's request, while the
    permission rules stay the owner's to apply.
    """
    out = json.loads(json.dumps(settings))  # deep copy, order kept
    lines: list[str] = []

    if not skip_deny:
        permissions = out.setdefault("permissions", {})
        if not isinstance(permissions, dict):
            raise SystemExit("settings.permissions is not an object; edit it by hand")
        deny = permissions.setdefault("deny", [])
        if not isinstance(deny, list):
            raise SystemExit("settings.permissions.deny is not a list; edit it by hand")
        for rule in DENY:
            if rule not in deny:
                deny.append(rule)
                lines.append(f"deny      + {rule}")

    plugins = out.setdefault("enabledPlugins", {})
    if not isinstance(plugins, dict):
        raise SystemExit("settings.enabledPlugins is not an object; edit it by hand")
    for name in PLUGINS_OFF + ([CODEX] if with_codex else []):
        before = plugins.get(name, "<absent>")
        if before is not False:
            plugins[name] = False
            lines.append(f"plugin    {name}: {before} -> False")

    env = out.setdefault("env", {})
    if not isinstance(env, dict):
        raise SystemExit("settings.env is not an object; edit it by hand")
    for key, value in ENV.items():
        if env.get(key) != value:
            state = "set" if key in env else "<absent>"
            env[key] = value
            lines.append(f"env       {key}: {state} -> {value}")

    return out, lines


def newest_backup() -> Path | None:
    backups = sorted(SETTINGS.parent.glob("settings.json.bak-batchA-*"))
    return backups[-1] if backups else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply config-audit batch A")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="backup, then write")
    mode.add_argument("--restore", action="store_true", help="restore the newest backup")
    parser.add_argument("--with-codex", action="store_true", help="also disable the codex plugin")
    parser.add_argument(
        "--skip-deny",
        action="store_true",
        help="plugins and env only; leave the permissions block untouched",
    )
    args = parser.parse_args(argv)

    if args.restore:
        backup = newest_backup()
        if backup is None:
            print("no batch-A backup found next to settings.json", file=sys.stderr)
            return 1
        shutil.copy2(backup, SETTINGS)
        print(f"restored {SETTINGS} from {backup.name}")
        return 0

    if not SETTINGS.is_file():
        print(f"{SETTINGS} not found", file=sys.stderr)
        return 1
    raw = SETTINGS.read_text(encoding="utf-8")
    try:
        settings = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"{SETTINGS} is not valid JSON ({exc}); nothing changed", file=sys.stderr)
        return 1
    if not isinstance(settings, dict):
        print("settings.json is not an object; nothing changed", file=sys.stderr)
        return 1

    merged, lines = plan(settings, args.with_codex, args.skip_deny)
    if not lines:
        print("batch A is already applied; nothing to change")
        return 0
    print(f"{len(lines)} change(s) to {SETTINGS}:")
    for line in lines:
        print("  " + line)

    if not args.apply:
        print("\ndry run: nothing written. Re-run with --apply to write.")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = SETTINGS.with_name(f"settings.json.bak-batchA-{stamp}")
    shutil.copy2(SETTINGS, backup)
    newline = "\r\n" if "\r\n" in raw else "\n"
    text = json.dumps(merged, indent=2, ensure_ascii=False) + "\n"
    with open(SETTINGS, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(text)
    json.loads(SETTINGS.read_text(encoding="utf-8"))  # must still parse
    print(f"\nwritten. backup: {backup.name}")
    print("start a NEW Claude Code session for the plugin and env changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
