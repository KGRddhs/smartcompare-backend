# Qaren Claude.ai Web Skills

This directory holds `SKILL.md` files that Ahmed uploads to **claude.ai → Settings → Skills**. These are NOT Claude Code skills (those live under `~/.claude/`); these run in claude.ai web alongside the Meta Ads MCP connector.

## Why claude.ai web, not Claude Code

The official Meta Ads MCP at `https://mcp.facebook.com/ads` works in claude.ai web (Pro/Max/Team) and Claude Desktop, but **fails OAuth in Claude Code CLI** because Meta hasn't whitelisted Claude Code's dynamic-port redirect URIs. Tracked in Anthropic GitHub issues #55002, #55556, #57191. Until that's resolved, all Qaren ad-ops happens in claude.ai web.

## Skills in this bundle

| # | File | Purpose |
|---|---|---|
| 1 | `qaren-meta-campaign-setup-bahrain.md` | One-shot creation of campaign + ad set + 2 ads + 2 Instant Forms (all paused) |
| 2 | `qaren-meta-daily-check.md` | Daily insights pull + decision-rule recommendation |
| 3 | `qaren-fillout-meta-reconcile.md` | Match Fillout completers to Meta ads via UTM tags |
| 4 | `qaren-brand-voice.md` | Copy contract enforcement (no scary words, AR-first, emerald = signal only) |

## How to upload

1. Open https://claude.ai → click your profile → **Settings** → **Skills** tab
2. Click **Create skill** (or **Upload skill**)
3. Paste the entire `SKILL.md` file content into the editor (including YAML frontmatter at top)
4. Save
5. Repeat for each file

Once uploaded, Skills auto-trigger when the user's prompt matches their `description` field. No further setup needed.

## Design + decisions

Full design rationale: `docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md`

Updating these skills:
- Change CLAUDE.md copy contract → update `qaren-brand-voice.md` in the same commit
- Change campaign decision rules → update `qaren-meta-daily-check.md`
- New campaign version (V2, V3, ...) → fork the setup skill, don't edit V1 in place
