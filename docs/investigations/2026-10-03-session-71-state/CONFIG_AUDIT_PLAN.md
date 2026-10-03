# Claude Code configuration audit: plan (proposal only)

Date 2026-10-03. This plan merges five read-only surface audits: CLAUDE.md [MD], skills [SK], MCP [MCP], plugins [PL], and agents/hooks/settings [S5]. It adds four checks made during synthesis [SYN]. Nothing has been edited. Every item is a proposal for Ahmed to review.

Path legend:
- `~` = C:/Users/SynAckITPC
- `SC` = C:/Users/SynAckITPC/Documents/AI/smartcompare
- `DESK` = ~/AppData/Roaming/Claude/local-agent-mode-sessions/e4438e93-.../fdc6094b-.../ (the desktop account layer)

Layers:
- global: ~/.claude/*, ~/.claude.json, the desktop app and the claude.ai account
- project: SC/.claude/*, SC/CLAUDE.md, SC/.mcp.json, SC/.githooks
- parent-dir: Documents/AI and Documents

---

## Part 1: Reliability issues

### Healthy (keep as is)
- There is no global ~/.claude/CLAUDE.md and no Documents/AI/CLAUDE.md. Documents/AGENTS.md and Documents/CLAW.md are 0 B. SC/CLAUDE.md has no @imports. [MD]
- 79 of 83 path references in SC/CLAUDE.md resolve. The spot-checked facts are correct: 14 routers, the 46-line main baseline, the 11-row pre-impl baseline, canary 100 and the PHANTOM flags. The load-bearing rules are concrete: principle 10, the two app/ dirs, the generated requirements lock, the IMMUTABLE index predicate and the :799-849 zero-regression gate. [MD]
- CLAUDE.md delegates to the .claude/skills/qaren-* skills correctly. qaren-cohort and qaren-scoring frontmatter parses (re-checked). [MD][SK][SYN]
- 20 Matt Pocock skills and 27 of 30 Sentry skills set disable-model-invocation, so they cost nothing in the listing. There are no legacy commands dirs. 277 of 280 frontmatters parse. [SK]
- No MCP or settings file holds a literal secret: only env-var names appear, and the two values inside allow entries are short dummies. [MCP][PL][S5]
- Tool deferral is on. Subagents share the parent's MCP connections. There is no per-project mcpServers sprawl. [MCP]
- Only two marketplaces are registered, both first-party (anthropics/claude-plugins-official and openai/codex-plugin-cc). installed_plugins.json matches enabledPlugins. [PL]
- The Codex Stop review gate is off (stopReviewGate=false). No user or project agent, command or hook collides with a built-in. [PL][S5]
- .githooks/pre-commit is wired: core.hooksPath is shared by all worktrees and the tool versions match the pins. Nothing in it is weakened, and it runs only at commit. [S5]
- Keep these: the railway and context7 MCPs (heavily used), typescript-lsp, claude-md-management and frontend-design. [MCP][PL]

### Issues
Ranked by impact. The ranking weighs blast radius, how often the issue fires and how likely harm is, with security first. Each item gives its location, the problem in one sentence, the proposed fix and the config layer.

**R1 [high] The prod-secret dump path is open at three layers.** Layer: global + project. Sources: [MCP][S5][MD]
- Where:
  - ~/.claude/settings.json runs bypass mode with skipDangerousModePermissionPrompt:true and has no permissions.deny.
  - SC/.claude/settings.local.json allows `Bash(railway variables *)`, `Bash(env)`, `Bash(railway run *)`, `Bash(git checkout *)`, `Bash(git stash *)`, `Bash(git reset *)`, `Bash(shutdown /s /t 5)` and `PowerShell(Stop-Computer -Force)`.
  - Both Railway MCPs expose `list_variables`.
  - SC/CLAUDE.md:337 recommends `railway variables --service <svc> --kv`, which prints values, and :418 says to query env vars through `mcp__railway__*`. Both contradict principle 10 (:30).
- Problem: The rules learned from real incidents exist only as prose: the 2026-09-07 secret dump, `git checkout --` wiping agent work, stash in the shared clone, and recursive deletes through junctions. The config grants these actions, and CLAUDE.md itself recommends two value-printing recipes.
- Fix:
  1. Add `permissions.deny` to ~/.claude/settings.json. Put it in the global file so it also covers the Documents/AI orchestrator root. Deny: `Bash(railway variables*)`, `mcp__railway__list_variables`, `mcp__plugin_railway_railway__list_variables`, `Bash(env)`, `Bash(printenv*)`, `Read(**/.env)`, `Read(**/.env.*)`, `Bash(git checkout -- *)`, `Bash(git stash*)`, `Bash(git reset --hard*)`, `Bash(git clean*)`, `Bash(git push --force*)`, `Bash(shutdown*)`, `PowerShell(Stop-Computer*)`, `PowerShell(Remove-Item*-Recurse*)`.
  2. Delete the matching allow entries.
  3. Rewrite :337 in a names-only form (for example `... --kv | cut -d= -f1`) and delete :418.
  4. **Before relying on step 1, test that deny is enforced under bypassPermissions.** If it is not, enforce the same list with one PreToolUse guard hook. That hook replaces the Railway hook from R5, so per-Bash latency still drops.

**R2 [high] CLAUDE.md carries volatile prod state that contradicts itself.** Layer: project. Source: [MD]
- Where: SC/CLAUDE.md
  - Bright Data gate: :336 says UNSET, :565 says =true.
  - Migration 038: :438 says UNAPPLIED, :86 says applied.
  - Deploys: :443 says there has been no live deploy, :565 says RESTORED.
  - Phones: :296 and :505 say 97b5f15, while :577, :625 and :645 say 561d2cba.
  - Serper: :350, :637, :661 and :720 say dead, :850 says paid and live.
  - Migration 042 is still marked unapplied although session 70 applied it.
- Problem: An agent cannot tell which production statement is current, so it can act on a stale one.
- Fix: Remove volatile status from CLAUDE.md and keep one "Current state" pointer to the latest `docs/investigations/<date>-session-NN-state/NEXT_SESSION_PROMPT.md`. Record prod state only in the flag index, one as-of date per flag, edited in place.

**R3 [high] Corrections are appended next to the text they correct.** Layer: project. Source: [MD]
- Where: SC/CLAUDE.md :13/:17, :248/:250, :352/:353, :590/:591 and :850/:851. The :539 "corrections owed by #223" bullet is stale, since those corrections were already applied at :176 and :612.
- Problem: Both versions load, so an agent can follow the superseded one. Examples: :352 says "all four AsyncOpenAI constructions" but :353 says "only four of the five"; :850 says "un-degraded" but :851 says "degraded again".
- Fix: Fold each correction into its original sentence, delete the superseded text and delete :539. Add a rule to principle 5: edit in place, never append a correction.

**R4 [high] The orchestration rules contradict the harness, and nothing enforces Opus subagents.** Layer: project + global. Sources: [MD][S5]
- Where:
  - SC/CLAUDE.md:24 (principle 4, "parallel 4-Opus TeamCreate") and :283 ("mode: bypassPermissions REQUIRED") conflict with :285 ("Workflow tool, NOT TeamCreate") and :526 (a cap of 2 gate-heavy workflows).
  - ~/.claude/settings.json sets `"model": "fable[1m]"` and has no `CLAUDE_CODE_SUBAGENT_MODEL`.
  - Plugin agents pick their own model: superpowers:code-reviewer is `inherit` (so Fable), and feature-dev/* and codex:codex-rescue are `sonnet`.
- Problem: The always-loaded principle prescribes the four-parallel pattern that caused the session-68 slow-spawn stall. The user's rule (Opus agents, Fable orchestrator) holds only where a workflow script passes the model explicitly.
- Fix:
  - Rewrite principle 4 to the current harness: the Workflow tool, Opus agents, a Fable orchestrator, at most 2 gate-heavy workflows, pyt.py wall-clock bounds and the stall monitor. Delete :283.
  - Add env `CLAUDE_CODE_SUBAGENT_MODEL=<Opus model id>` to ~/.claude/settings.json. Verify the name and its precedence over agent frontmatter on this build.
  - Keep passing model explicitly in workflow scripts.
  - Optionally add `~/.claude/agents/opus-worker.md` with `model: opus`.

**R5 [high] The Railway plugin hook fires on every Bash call, and the Railway MCP loads twice.** Layer: global + project. Sources: [PL][S5][MCP]
- Where:
  - ~/.claude/settings.json enables `railway@claude-plugins-official`, which brings `~/.claude/plugins/cache/claude-plugins-official/railway/1.2.1/hooks/hooks.json` (PreToolUse on Bash, running auto-approve-api.sh:6-7, 14, 28-29).
  - `SC/.mcp.json` defines `mcpServers.railway` (`cmd /c railway mcp`), and `SC/.claude/settings.local.json` enables it through `enabledMcpjsonServers ["railway"]`.
- Problem: The hook needs jq, which is not installed, so it does nothing yet costs about 0.6-1.3 s per Bash call in every session and agent (measured). If jq were ever installed, the hook would auto-approve any `railway ...` command, including `railway variables`. On top of that, smartcompare-rooted sessions load 32+32 duplicate Railway tools and two railway processes (seen in 8 of 8 transcripts).
- Fix:
  - Disable the plugin.
  - Add one user-scope server so the Documents/AI orchestrator root keeps Railway: `claude mcp add railway -s user -- cmd /c railway mcp`.
  - Remove the railway entry from SC/.mcp.json and from enabledMcpjsonServers, in a repo PR.
  - Do not install jq.
  - Tool names change to `mcp__railway__*`, so update the briefs, scripts and the R1 deny list.
  - If the use-railway skill is wanted (2 uses), copy it to ~/.claude/skills.
  - The MCP audit proposed the opposite choice; see assumption A1.

**R6 [high] Ten unused Cowork plugins inject about 92 MCP entries and 99 skills into every Code session and agent.** Layer: global (desktop account). Sources: [MCP][PL][SK][SYN]
- Where: DESK/rpm/plugin_* (sales, marketing, legal, operations, data, design, product-management, productivity, cowork-plugin-management, pdf-viewer). ~/.claude.json pluginUsage for *@inline shows usageCount 0 for all of them.
- Problem: Every start probes about 40 servers that need auth and hits a 5 s salesforce timeout. The skill listing also overflows its budget, so about 109 skills show their name only. That includes Ahmed's own synack-prd-builder, synack-service-scoper, synack-sme-finder-bahrain and qaren-brand-voice, and the project's qaren-cohort, so they cannot be selected from their descriptions. All of these symptoms were re-verified in this agent's own context.
- Fix:
  - In the Claude Desktop plugin settings, disable or uninstall all ten for this account. Keep legal only if it is needed for the MYEZ privacy policy, and pdf-viewer only if it is used.
  - If a Code-only exclusion exists, use it instead.
  - Test whether `"<name>@inline": false` in SC/.claude/settings.json is honoured before relying on it.
  - Afterwards, check that the listing shows the synack-* and qaren-* descriptions again. If synack-* must trigger in Code, copy those skills into ~/.claude/skills.

**R7 [high] superpowers pushes agents into skill detours that compete with the harness.** Layer: global. Sources: [SK][PL][S5]
- Where: ~/.claude/settings.json enables `superpowers@claude-plugins-official` 4.3.1. Its hooks/hooks.json SessionStart hook (startup|resume|clear|compact) injects skills/using-superpowers/SKILL.md. The relevant skills are brainstorming, test-driven-development and finishing-a-development-branch.
- Problem: The injected "1% chance ... YOU MUST invoke" rule and the "MUST use before any creative work" skills make agents load skills from the roughly 237 that are invocable. finishing-a-development-branch also offers a local merge, which bypasses the adversary-before-merge rule.
- Fix: Disable superpowers globally. The user-scope tdd, diagnosing-bugs and code-review skills and the harness already cover its useful parts. If one of its skills is wanted, copy it into ~/.claude/skills with a neutral description.

**R8 [high] The binding rules in CLAUDE.md did not reach this workflow agent.** Layer: project (how the harness delivers rules). Source: [SYN]
- Where: sc-docs-70/CLAUDE.md is 331,767 B. This synthesis agent's cwd is sc-docs-70, and its context held ~/.claude/projects/C--Users-SynAckITPC-Documents/memory/MEMORY.md but no CLAUDE.md text.
- Problem: If workflow agents never load CLAUDE.md, whether by harness design or a size cap, then principle 10, the junction rule and the gate rules protect them only when the brief repeats them.
- Fix: Spawn one probe agent per root (Documents/AI and one worktree) that reports whether CLAUDE.md text is present. If it is absent, put the slim "Harness & gate rules" section (T1) into a shared brief preamble used by every workflow script, and rely on the R1 deny list for the secret rule.

**R9 [high] Two project skills never trigger because their YAML is invalid.** Layer: project. Sources: [SK][SYN]
- Where: SC/.claude/skills/qaren-eas-deploy/SKILL.md:4 and qaren-referrals/SKILL.md:4. The `last_verified` value has an unquoted ": " (from commit bda8aa43). Re-checked with yaml.safe_load in both SC and sc-docs-70: "mapping values are not allowed here".
- Problem: The listing shows only the H1 ("Qaren EAS Update Infrastructure") or nothing, so OTA and referral work does not pick up these procedures, including "run npm ls before any eas update".
- Fix: Quote the value, or change "2026-09-29:" to "2026-09-29 -". Add a yaml.safe_load check over `.claude/skills/*/SKILL.md` to .githooks/pre-commit and CI.

**R10 [high] The orchestrator root Documents/AI gets no project layer, and the empty Documents/.git sets the auto-memory path and gitStatus.** Layer: parent-dir. Sources: [S5][MD]
- Where:
  - cwd C:/Users/SynAckITPC/Documents/AI has no .claude/ and no CLAUDE.md (17 sessions ran there).
  - C:/Users/SynAckITPC/Documents/.git is an empty repo on master with no commits.
  - SC/CLAUDE.md :268, :280, :285 and :327 link to memory/... and [[feedback-*]] files.
- Problem: Project deny rules, hooks and .mcp.json never apply to the orchestrator. Auto-memory resolves to the C--Users-SynAckITPC-Documents memory dir, so CLAUDE.md's memory links dangle there. gitStatus also shows about 22 misleading untracked lines.
- Fix:
  - Put orchestrator-wide config in ~/.claude/settings.json (R1, R4) or in a new Documents/AI/.claude/settings.json.
  - Cite memory facts by absolute path, or copy them into docs/.
  - Add a Documents/.gitignore containing `*`.
  - **Do NOT delete Documents/.git before relocating the memory dir.** The memory key would change and MEMORY.md would look lost.

**R11 [high] The pre-commit secret guard catches only one of the repo's 11 secrets, and CI has no secret scan.** Layer: project. Source: [S5]
- Where: SC/.githooks/pre-commit:57-63, SC/.github/workflows/ci.yml and live-suite.yml. The gap is an open P2 in docs/investigations/2026-08-31-m13-review/security.verified.json.
- Problem: Of the 11 secret values in the repo's .env, only the OpenAI sk- key matches the regex. The Supabase service-role and anon JWTs, the Nasser JWT and the Upstash, Serper, Firecrawl, Scrape.do, YouTube and Zyte keys would all commit cleanly, even though gitleaks 8.30.1 is on PATH.
- Fix (additive):
  - Run `gitleaks git --pre-commit --staged --redact --no-banner`. Fail closed when gitleaks is present and warn when it is absent. Confirm the flags with `--help` first.
  - Add regex branches for JWTs and credentialed URLs.
  - Add a fixed-string pass that compares staged added lines against .env values of 16 or more chars and never prints a match.
  - Add a gitleaks job to CI.

**R12 [medium] The MEMORY.md index holds 13 "RESUME HERE" pointers and one garbled line.** Layer: global (auto-memory). Source: [SYN]
- Where: ~/.claude/projects/C--Users-SynAckITPC-Documents/memory/MEMORY.md is 20,386 B and 41 lines, with 13 "RESUME HERE" entries. The session-65b line has a second entry spliced into it ("...gate lessons.(project-myez-session65b-...md) — resume both via...").
- Problem: Every agent loads this file (observed here) and sees thirteen competing resume points for sessions 64-70, so it is unclear which is current.
- Fix: Keep one "RESUME HERE", for the latest session. Collapse the superseded session entries into one "History" line that points at the repo's docs/investigations/*-state folders. Keep the feedback-* lines and repair the spliced line. Do the same for the smartcompare-keyed index (17,629 B).

**R13 [medium] The CLAUDE.md update rule makes the file grow every session.** Layer: project. Source: [MD]
- Where: SC/CLAUDE.md:28 (principle 5).
- Problem: The rule "After major features: update CLAUDE.md, MEMORY.md, CONTEXT_SESSION_LOG.md" grew the file from 74,734 B in July to 327,795 B (52 commits since 09-01). Open docs PR #277 adds yet another block and a second "Phones today" line. "MEMORY.md" is also ambiguous, because there are two memory dirs.
- Fix: Session narrative goes only to the session log and the state doc. CLAUDE.md changes only for durable rules and the flag index, edited in place. Name the exact memory path. Amend PR #277 this way before merging it.

**R14 [medium] Overlapping skill triggers make skill selection unpredictable.** Layer: global. Source: [SK]

| Cluster | Candidates | Fix |
|---|---|---|
| Code review | ~/.claude/skills/code-review, review (gstack), the code-review plugin, superpowers:requesting-code-review, synack-build-orchestrator, gstack codex / codex:rescue | Keep ~/.claude/skills/code-review as the canonical one. Disable the code-review plugin and delete ~/.claude/skills/review. |
| Debugging | diagnosing-bugs, prove-it-works, investigate, superpowers:systematic-debugging | Keep diagnosing-bugs and prove-it-works. Delete investigate; superpowers goes with R7. |
| Ship/deploy | ship, land-and-deploy, setup-deploy, canary, document-release | "Ship it" can run a foreign VERSION/CHANGELOG/merge/deploy flow that skips the PR, adversary and EAS/Railway procedure. Delete land-and-deploy and setup-deploy, and set disable-model-invocation on ship. |
| iOS | ios-clean, ios-design-review, ios-fix, ios-qa, ios-sync | These are SwiftUI/SPM tools that can be picked for an Expo bug. Delete them or set disable-model-invocation. |
| Memory writers | sync-gbrain and setup-gbrain (gbrain is not installed), context-save/restore, learn, productivity:* | Delete the gbrain pair. productivity goes with R6. |
| Too-generic triggers | ~/.claude/skills/synack-build-orchestrator claims "/plan", "run the code review" and "audit the config" | Tighten the description to about 320 chars, scoped to a named Synack idea's PRD, and drop "/plan". |

Check first whether gstack-upgrade recreates deleted dirs. If it does, use disable-model-invocation instead of deleting.

**R15 [medium] Sentry is configured three ways and none of them is authenticated.** Layer: global + project + claude.ai. Sources: [MCP][PL]
- Where:
  - ~/.claude.json `mcpServers.sentry` has been needs-auth since 2026-08-16.
  - SC/.claude/settings.json enables `sentry@claude-plugins-official`, but its MCP never surfaces, and installed_plugins.json records the projectPath in lowercase as `Documents\ai\smartcompare`.
  - The claude.ai Sentry connector has been absent from recent sessions.
- Problem: The owed react-native Sentry re-check has no working route, and it is ambiguous which route would be used.
- Fix: Keep the user-scope entry, because it works from every root. Set the sentry plugin to false in SC/.claude/settings.json and authenticate once via /mcp.

**R16 [medium] The GitHub plugin MCP fails in every session.** Layer: global. Sources: [MCP][PL][SYN]
- Where: ~/.claude/settings.json enables `github@claude-plugins-official`. Its .mcp.json sends `Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}`, and that variable is unset in the process, User and Machine environments.
- Problem: It returns a 400 "Authorization header is badly formatted" at every start (seen in this agent's context too) and has 0 uses ever. Workflows already use gh, state/pr_rest.py and ccd_pr.
- Fix: Set it to false. If it is wanted later, put a fine-grained PAT in a User env var (never in settings env) and restart.

**R17 [medium] The Supabase MCP is often unauthenticated, while its prod-write tools are pre-allowed.** Layer: global + project. Sources: [MCP][PL][MD]
- Where: ~/.claude/settings.json enables `supabase@...`. SC/.claude/settings.local.json allows `mcp__plugin_supabase_supabase__execute_sql` and `apply_migration`. SC/CLAUDE.md:84 names the MCP as the preferred migration path.
- Problem: Agents planning DB steps find the tools missing: the server was needs-auth in all recent Documents/AI sessions, and the last real use was 2026-08-08. When it is connected, prod SQL writes run without a prompt.
- Fix:
  - Keep it global and deferred, since the orchestrator root needs it.
  - Re-authenticate via /mcp before any DB lane, and have the orchestrator check needs-auth before assigning DB work.
  - Remove the two allow entries.
  - Make the SQL-editor one-paste pattern (precheck, apply, postcheck) the primary path at :84.

**R18 [medium] The personal settings.local.json is committed to git.** Layer: project. Source: [S5]
- Where: SC/.claude/settings.local.json is tracked. It has 192 entries (11,046 chars), including 3 multi-line one-off commit commands, a hard-coded PID kill and 40 git entries already covered by `Bash(git *)`.
- Problem: Its approvals (git push, prod SQL, shutdown) ship to every clone and to all 28 worktrees, and every new "always allow" dirties a tracked file inside PR worktrees.
- Fix: Run `git rm --cached` on it and add it to .gitignore. Move the shared durable settings to the tracked SC/.claude/settings.json. Prune the local copy to a few wildcard entries.

**R19 [medium] 26 stale worktrees carry old CLAUDE.md files and broken skill copies.** Layer: project. Sources: [MD][SK]
- Where: Documents/AI/sc-*/, smartcompare-*/ and SC/.claude/worktrees/angry-wescoff-fc8992/. Their CLAUDE.md copies range from 74 to 332 KB (the nested copy is 85,806 B), and each has its own .claude/skills.
- Problem: Orchestrator sessions rooted at Documents/AI pick up CLAUDE.md and the qaren-* skills from whichever tree they touch. This session lists the sc-docs-70 copies, so superseded rules and broken skills load.
- Fix: Remove merged and abandoned worktrees. Unlink each node_modules junction first, using the single tested command from R20.

**R20 [medium] Four gate and procedure rules are stated inconsistently in CLAUDE.md.** Layer: project. Source: [MD]

| Rule | Conflict | Fix |
|---|---|---|
| Eval baseline | :486 uses `--baseline-run-id 4aee8e88-...`, but :487 says gates "MUST pass ... 54b603e8-..." | Keep one UUID. |
| CI wording | :488 says "green with 11 known nodes deselected", but :641 says "9 ... not 11"; the file has 11 rows | Prune the 2 stale rows and state one number. |
| Type check | :60-62 and :651 say "Trust ONLY npx tsc --noEmit", but :322 says npx can fall through to a global TS 6.0.2 | Use `node node_modules/typescript/bin/tsc --noEmit` everywhere. |
| Junction unlink | :322 uses PowerShell Directory.Delete and says `cmd //c rmdir` fails; :519 and :547 say `cmd /c rmdir`; the memory index and :322 disagree on whether Remove-Item -Recurse follows the junction | State the rule once, in the "Harness & gate rules" section, with one tested command. |

**R21 [medium] The flag registry is incomplete and contradicts itself.** Layer: project. Source: [MD]
- Where: SC/CLAUDE.md:278 claims every flag is listed. :336 says "All flags default OFF" right next to default-ON flags. The rows live at :338-456, :528-545 and :611-614.
- Problem: 24 ENABLE_* names that code in app/ or scripts/ reads are missing (for example ENABLE_GENUINE_PRICE_PRIORITY, ENABLE_NASSER_ADAPTER, ENABLE_STRICT_CURRENCY_LABEL, ENABLE_GPT_WINNER and ENABLE_YOUTUBE_SOURCE). Another 18 rows sit inside Active-runtime blocks and would be lost if those blocks were archived naively.
- Fix: Generate docs/FLAGS.md from code, using the U15 generator noted at :640. Keep a one-line-per-flag index in CLAUDE.md. Move the block-resident rows before archiving (see T1).

**R22 [medium] Architecture facts are stale and some references are dead.** Layer: project. Source: [MD]
- Where:
  - :112 says the orchestrator is ~1,500 lines; it measures 9,148.
  - :95-107 lists 12 of 14 routers; home_routes.py and profile_routes.py are missing.
  - :199 says migrations 010-026; they now run to 042.
  - :483 says ~557 test files; there are 661.
  - :223 says ~98 tests; there are 104.
  - :249 points to `docs/plans/2026-05-06-qaren-ux-redesign{,.design}.md`; the real file is `-design.md`.
  - :853 points to `docs/investigations/2026-05-16-scrapedo-timeout-analysis.md`, which does not exist.
- Fix: Correct the numbers and paths, or move the detail to docs/CONTEXT_ARCHITECTURE.md and keep only the invariants in CLAUDE.md.

**R23 [medium] Account skills still enforce the old brand, and one has invalid YAML.** Layer: global (claude.ai account skills). Source: [SK]
- Where:
  - anthropic-skills:qaren-brand-voice enforces "Qaren (قارن)".
  - qaren-meta-campaign-setup-bahrain has invalid YAML in its description ("via Meta Ads MCP: 1 campaign").
  - qaren-meta-daily-check is pinned to the campaign BH_LeadGen_V1_2026-05.
- Problem: Brand copy would come out as Qaren after the rename to MYEZ (ميّز), and the skill will not trigger on "MYEZ".
- Fix: Update the brand-voice skill to MYEZ, keeping "Qaren" as a legacy alias. Quote the campaign-setup description. Archive the Meta skills if that campaign has ended.

**R24 [medium] Local stdio MCP servers add about 450 MB and 10 processes per Code session on a box with slow process spawning.** Layer: global. Sources: [MCP][PL]
- Where:
  - context7 at version 2cd88e7947b7 runs `npx -y @upstash/context7-mcp` (about 5 processes and 210 MB).
  - The Cowork pdf-viewer runs `npx -y @modelcontextprotocol/server-pdf` (about 5 processes and 240 MB, 0 uses).
  - `DISABLE_AUTOUPDATER=1` keeps every plugin pinned at the Feb-2026 marketplace commit.
- Fix: Run `/plugin update context7@claude-plugins-official`; the cached version c447c3207a42 uses the hosted HTTP server. pdf-viewer goes with R6. Together these save about 1.1 GB and 20 processes across the two live sessions and the desktop app.

**R25 [low] Figma and Canva are each configured several ways.** Layer: global + claude.ai. Sources: [MCP][PL]
- The figma plugin is needs-auth with 0 uses, while the claude.ai Figma connector is connected (41 tools). Canva appears as both a claude.ai connector and `plugin:marketing:canva`.
- Fix: Disable the figma plugin. The Canva duplicate goes away with R6. The connectors are covered in T5.

**R26 [low] The Codex Stop gate has no loop guard, and the plugin spawns node three times per session.** Layer: global. Sources: [S5][PL]
- Where: `~/.claude/plugins/cache/openai-codex/codex/1.0.4/scripts/stop-review-gate-hook.mjs:142-176` has no stop_hook_active check and a 15-min timeout.
- Problem: The gate is off today. If it were enabled while OpenAI credits are out, each Stop could block for up to 15 minutes. The node hooks run regardless, and the plugin was last used 2026-06-23.
- Fix: Keep the gate off. Disable `codex@openai-codex` unless the lane uses it; the gstack codex skill covers the CLI.

**R27 [low] Plugin agents collide.** Layer: global. Sources: [S5]
- superpowers:code-reviewer and feature-dev:code-reviewer share a name. feature-dev:code-explorer duplicates the built-in Explore. codex-rescue invites proactive hand-off of work to an external runtime.
- Fix: Disable feature-dev; superpowers goes with R7. Name one reviewer agent in workflow briefs.

**R28 [low] The pre-commit hook has weak mechanics.** Layer: project. Source: [S5]
- Where: SC/.githooks/pre-commit:11-45 and :61.
- Problem: py_compile, ruff and black read working-tree files instead of the staged blobs. The .env check matches only the root .env. black is skipped silently when missing. Nothing checks TS/JS. core.hooksPath is local-only config, so fresh clones are unprotected (CLAUDE.md:738).
- Fix (additive): Lint the staged blobs via `git checkout-index --temp` (not stash). Widen the .env check to `(^|/)\.env(\..*)?$`. Warn when black is missing. Optionally run eslint on staged SmartCompareApp files. Have a setup script set core.hooksPath.

**R29 [low] Some skills are dead weight or collide by name.** Layer: global. Source: [SK]
- ~/.claude/skills/_gstack-command is a byte-identical copy of the gstack router, so the router is listed twice.
- pov-reels-montage: set disable-model-invocation.
- scaffold-exercises, migrate-to-shoehorn and setup-pre-commit (which installs Husky; the repo uses .githooks + ruff): remove.
- git-guardrails-claude-code, benchmark-models and pair-agent: make them slash-only.
- The bare-name collisions (learn, schedule, brainstorm, pdf, risk-assessment, codex, competitive-brief) mostly disappear with R6 and R7. Otherwise remove gstack learn and gstack codex.
- The Cowork-only anthropic-skills (setup-cowork, built-in-browser, chrome-browser, computer-use) duplicate Claude_Browser and claude-in-chrome in Code.

**R30 [low] The update settings conflict, and there is a stray config file.** Layer: global. Source: [S5]
- `DISABLE_AUTOUPDATER=1` makes `autoUpdatesChannel: "stable"` a no-op. ~/.claude/.claude.json (569 B) duplicates migration keys from ~/.claude.json.
- Fix: Drop one of the two update settings. Confirm the stray file is unread before archiving it.

**R31 [low] Some CLAUDE.md directives are vague or stale.** Layer: project. Source: [MD]
- Principles 1, 3 and 5 (:21-28) have no concrete trigger. Give one (for example, any change touching 3+ files or a flag) or delete principle 1.
- :498 calls the age policy "locked" while decision D9 is still pending. Reword it.
- :854 still lists the Session-54 Google Sign-In bug, whose diagnostics remain in auth_service.py:801 and authService.ts:893. Re-verify it or move it to an issue.

**R32 [low] A stale Codex fork of the instructions remains.** Layer: project. Source: [MD]
- SC/AGENTS.md is untracked, 67,332 B, and still says "app brand: Qaren". codex:rescue delegations read it.
- Fix: Replace it with a 3-line pointer to CLAUDE.md, or delete it.

### Suggested change batches (in review order)
- **A. ~/.claude/settings.json, one edit:**
  - the R1 deny list
  - enabledPlugins false for superpowers, railway, github, figma, code-review, feature-dev and code-simplifier (plus codex if unused)
  - CLAUDE_CODE_SUBAGENT_MODEL

  Then add the user-scope railway server, run /plugin update context7, and authenticate sentry and supabase via /mcp.
- **B. Claude Desktop and claude.ai settings:** the Cowork plugins (R6), the connectors (T5) and the account skills (R23).
- **C. One SC repo PR:** the skill YAML fix and frontmatter check (R9), the .mcp.json railway removal (R5), untracking settings.local.json (R18), turning off the sentry plugin (R15), gitleaks (R11), and the CLAUDE.md fixes and restructure (R2-R4, R13, R20-R22, T1-T3). Amend docs PR #277 first.
- **D. Housekeeping:** the MEMORY.md trim (R12), the worktree prune with junction unlink (R19), the ~/.claude/skills prune (R14, R29) and the Documents/.gitignore (R10).

---

## Part 2: Token efficiency

### What consumes always-on context (largest first; tokens are about chars / 4)

| Consumer | Size now | Who pays |
|---|---|---|
| SC/CLAUDE.md | 324,462 chars, about 81K (worktree copies are 74-332 KB) | Main sessions rooted in SC, or lazily when a Documents/AI session reads into a tree. It was not present in this workflow agent (R8). |
| Skill listing | about 6.0K as rendered (about 16.6K if every description showed) | Every session and agent |
| MEMORY.md index | 20,386 B, about 5.1K (the smartcompare-keyed one is 17,629 B, about 4.4K) | Every session and agent (observed) |
| claude.ai connectors (Canva, Miro, Figma) | about 2.6K of deferred names and server instructions (UUID names likely cost 1.5-2x more) | Every agent |
| All MCP server instructions | 6,164 chars, about 1.5K | Every agent |
| superpowers SessionStart injection | about 1.1K per start, resume, /clear or compaction | Main sessions |
| Needs-auth and failed-server notices | about 0.5K | Every agent (observed) |
| gitStatus from the empty Documents repo | about 0.2K | Documents/AI-rooted sessions |
| Host-injected schemas (Claude_Browser with 19 full schemas, ccd_*, visualize, terminal) | Not measured, and not user-configurable | Every session |

### Proposals

| # | Item | Layer | Action | Estimated saving |
|---|---|---|---|---|
| T1 | CLAUDE.md :504-741, the Active-runtime blocks (143,811 chars, about 36K) | project | Move them verbatim to docs/SESSION_BUNDLES.md, following the 2026-08-30 trim precedent. First hoist the 18 flag rows into docs/FLAGS.md, and the binding text (:519, :526, :528, :549, :570, :588, :593, :602) into a new ~2.5K "Harness & gate rules" section. Leave a pointer of 15 lines or fewer to the latest NEXT_SESSION_PROMPT.md. | about 33K per load |
| T2 | CLAUDE.md :338-456, the flag registry (92,404 chars, about 23K) | project | Put the full rows in a generated docs/FLAGS.md. Keep about 130 index lines: name, code default, prod state with as-of date, precondition and anchor. | about 20K per load |
| T3 | Narrative inside the CLAUDE.md core (:176, :193, :270-277, :296, the :322 incident story, :327; about 3K) | project | Move it to docs and keep the one-line rule each passage implies. | about 3K per load |
| | **CLAUDE.md after T1-T3** | project | 81K becomes about 20-25K, or about 15K if the fragrance findings and architecture detail also move to docs | **about 56-61K per load (about 66K for the aggressive option)** |
| T4 | MEMORY.md indexes (R12) | global | One resume pointer, history collapsed, at most about 8K chars | about 3-3.5K per agent |
| T5 | claude.ai connectors Canva and Miro, plus Figma unless design work runs from Code | claude.ai | Disable them for Code, in connector settings or per session with set_session_connector_enabled | about 2.6K per agent (3-4K real) |
| T6 | The ten Cowork plugins (R6) | desktop | Disable | about 2.4K per agent today (about 8K at full descriptions), plus 40 auth probes and a 5 s timeout per start |
| T7 | superpowers (R7) | global | Disable | about 1.6-2.3K per session plus 1.1K per compaction; about 0.6-0.9K per agent |
| T8 | Unused global plugins: the github failure notice, feature-dev, code-review, code-simplifier, codex | global | Disable | about 0.35K, plus 0.3K for codex and 3-4 node spawns |
| T9 | ~/.claude/skills prune (R14, R29) | global | Delete, or set disable-model-invocation | about 0.65K |
| T10 | Railway duplicate (R5) | project | Keep one server | about 0.23-0.35K per SC-rooted session |
| T11 | synack-* descriptions (account skills and ~/.claude/skills/synack-build-orchestrator) | global | Trim each to about 300-350 chars | about 0.28K once descriptions render again |
| T12 | gitStatus noise (R10) | parent-dir | Add Documents/.gitignore with `*` | about 0.2K |
| T13 | sentry plugin skills (R15) | project | Disable the plugin | about 0.15K, since 27 of 30 skills are not listed (see A7) |
| T14 | anthropic-skills account layer: built-in-browser, chrome-browser, computer-use, google-workspace, learn, rubric-driven-paper, morning, explain-usage, import-memory, setup-claude | claude.ai | Turn off whichever are unused. Keep docx, pptx, xlsx, pdf, deep-research, synack-* and brand-voice. | about 0.06K now (about 1.5K potential); mainly frees listing budget |
| T15 | figma plugin | global | Disable | about 0.05K now (about 0.8K potential) |
| T16 | `effortLevel: "xhigh"` as the global default | global | Use a lower default and raise it per session or per workflow agent | Unquantified (thinking tokens) |
| T17 | settings.local.json (192 entries) | project | Hygiene only (R18) | 0; permission rules are not injected into context |

### Totals (rough)
- **Main session rooted in smartcompare:** about 56-61K from CLAUDE.md, about 3K from the memory index and about 9-10K from T5-T15. That is roughly 68-74K saved per session start, taking always-on context from about 98K to about 28-30K, before the unmeasured host schemas.
- **Workflow agent as observed here (no CLAUDE.md):** about 3K plus about 8-9K, so about 11-12K per agent. A session-69-sized run of about 265 agents would save about 3M tokens. The CLAUDE.md audit's "~15M per run" figure assumed agents load CLAUDE.md. This agent did not, so that figure is unconfirmed (R8).
- **Orchestrator sessions in Documents/AI that read several trees:** up to about 160K saved through T1-T3 and the worktree prune (R19). Each tree's CLAUDE.md copy loads lazily, and whether identical copies are deduplicated is unverified.
- **Capability kept:** archived text stays in docs/ and loads on demand. Every disabled plugin is either unused (0 recorded uses) or duplicated elsewhere. Slash-only skills still run on an explicit /name.

### Assumptions (both parts), and why each beats the alternative
- **A1. Railway:** turn the plugin off and keep one user-scope `railway mcp` server. Keeping the plugin costs 0.6-1.3 s per Bash call and leaves a latent auto-approver. Keeping only the project .mcp.json entry would leave the Documents/AI orchestrator root without Railway.
- **A2. Deny list in the global settings, not the project:** the orchestrator root never sees SC/.claude, and the global file covers both roots.
- **A3. Cowork plugins disabled at account level,** even if that removes them from Cowork too, unless a Code-only lever turns up. They have 0 recorded uses, they cost something on every Code session and agent, and the change is reversible.
- **A4. Sentry: keep the user-scope entry and drop the plugin.** The entry works from every root. The plugin is project-scoped, its MCP never surfaces, and its install path has the wrong case.
- **A5. Supabase stays global:** its deferred cost is small, and moving it to the project would hide it from the orchestrator.
- **A6. Archive CLAUDE.md history rather than delete it:** this keeps provenance and follows the 2026-08-30 precedent. Rewriting risks losing binding rules buried inside the blocks.
- **A7. Where surfaces disagreed on numbers, the more direct measurement wins.** For sentry, the frontmatter-based 0.15K beats the raw-description 2K, because skills with disable-model-invocation are not listed. Both hook-latency measurements (0.6 s and 1.1-1.3 s) are kept as a range.
- **A8. Tokens are estimated as chars / 4:** no tokenizer was run, and UUID-prefixed tool names are likely undercounted.

### Not verified
- Whether permissions.deny is enforced in bypassPermissions mode. This gates R1; the fallback is the guard hook.
- The exact name of CLAUDE_CODE_SUBAGENT_MODEL, and its precedence over agent frontmatter and Agent-tool model params.
- Whether workflow agents ever load CLAUDE.md (there is one negative observation here), and whether main sessions truncate a 324K-char CLAUDE.md.
- Whether a Code-only disable lever exists for the Cowork plugins and claude.ai connectors (`ENABLE_CLAUDEAI_MCP_SERVERS` is untested), and whether `"<name>@inline": false` is honoured.
- How Railway deduplicates between SC/.mcp.json and the plugin, why the sentry plugin's MCP is suppressed, and why Supabase auth is intermittent.
- Whether the superpowers SessionStart hook fires on this Windows box and whether it reaches subagents.
- The live prod state behind R2 (the Bright Data gate, Serper, migration 042, the OTA group), the status of issue #89, and the Google Sign-In bug.
- Whether gstack-upgrade recreates deleted skill dirs, and whether "/plan" is a built-in command.
- How the skill-listing budget works (inferred from about 109 name-only entries), and the cost of the host-injected schemas.
- The exact pre-commit flags for gitleaks 8.30.1.
