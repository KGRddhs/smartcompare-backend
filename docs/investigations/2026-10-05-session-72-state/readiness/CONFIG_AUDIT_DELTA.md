# Configuration audit DELTA (session 72, 2026-10-05; proposal only, nothing changed)

Finder CONFIG under `/synack-build-orchestrator` Step 1. Base: main `845ece15` (read-only checkout `sc-s71-u13`; `sc-docs-70` is the same commit and its CLAUDE.md is byte-identical, sha256 prefix `d488eb33244fc804`). Delta against `sc-docs-70/docs/investigations/2026-10-03-session-71-state/CONFIG_AUDIT_PLAN.md` (R1-R32, T1-T17, batches A-D). Measured 13:48-14:05 AST with read-only scripts `m1.py`-`m6.py` in this folder (outputs `m*_out.txt`). No env value was printed except `CLAUDE_CODE_SUBAGENT_MODEL(_FORCE)`; `~/.claude.json` was not opened.

## 1. Size figures

| Surface | Now | 2026-10-03 audit | Note |
|---|---|---|---|
| CLAUDE.md @845ece15 | 346,920 B / **344,314 chars / ~86.1K tok** / 879 lines | 324,462 chars (~81K) | +19,852 chars (+6.1 %) since the audit, after T0c |
| - Active-runtime blocks L508-L764 (17 blocks) | 157,889 chars (~39.5K tok, 45.9 %) | 143,811 | T1 not done; 15 of 17 blocks marked "superseded" but still load |
| - Environment Variables L335-L460 | 100,631 chars (~25.2K tok, 29.2 %) | 92,404 (flag rows) | T2 not done |
| - Core (everything else) | 85,794 chars (~21.4K tok) | - | Important Patterns 30,382; Architecture 17,716; fragrance findings 11,927 |
| MEMORY.md index (Documents key) | 20,891 B / 20,692 chars (~5.2K tok), 13 "RESUME HERE" | 20,386 B, 13 | grew; spliced 65b line still present |
| MEMORY.md index (smartcompare key) | 17,629 B (~4.3K tok) | 17,629 B | unchanged |
| ~/.claude/skills | 93 dirs, 73 model-invocable, 20 disable-model-invocation, 8,212 description chars | - | 0 YAML errors; `_gstack-command` == `gstack` byte-identical |
| Repo skills | 4, all parse with `yaml.safe_load` | 2 of 4 broken | fixed by #312 |
| Global enabledPlugins | 13 entries: 6 true, 7 false | 13 true | batch A plugin half applied 2026-10-03 10:25 |
| Project tracked enabledPlugins | 1 (`sentry@claude-plugins-official` true) | same | R15 open |
| Cowork/account plugins (not in settings.json) | 10, still loaded (pdf-viewer, product-management, legal, cowork-plugin-management, operations, marketing, sales, data, design, productivity) | 10 | R6 open |
| Worktrees of the clone | 29 (23 branches merged into 845ece15), 29 CLAUDE.md copies = 5.9 MB, 29 skill dirs, 10 junctioned `node_modules` | 26 + 1 nested | R19 worse |

## 2. Delta status of every 2026-10-03 finding

CLOSED = proven in code, config or a merged PR. PARTLY / OPEN = what is still true, with the evidence.

| ID | State | Evidence today |
|---|---|---|
| R1 deny list + value-printing recipes | PARTLY | Recipe half CLOSED by #306: CLAUDE.md L341 carries the names-only recipe, `mcp__railway` has 0 hits. Deny half OPEN: `~/.claude/settings.json` has NO `permissions` key at all; `apply_audit_batch_a.py:62-86` is ready, but SESSION_71_STATE says it is Ahmed's to run. `sc-s71-u13/.claude/settings.local.json` (192 allows) still allows `Bash(railway variables *)`, `Bash(railway run *)`, `Bash(env)`, `Bash(git checkout *)`, `Bash(git stash *)`, `Bash(git reset *)`, three `shutdown` forms, `PowerShell(Stop-Computer -Force)`, and supabase `execute_sql` / `apply_migration` |
| R2 volatile prod state in CLAUDE.md | PARTLY | L9 now points at SESSION_71_STATE.md. L21 (inside the "read EVERY session" block) still says "U4d in flight; the production binary must be built after it lands", but #307 merged (72b13bc5). The 17 Active-runtime blocks (157,889 chars) still load |
| R3 appended corrections | PARTLY | Still present: L361 vs L454 (ENABLE_DEFAULT_RATE_LIMITS row vs "CORRECTION to the ... row above"); L436 "INERT until the client sends it" + "CORRECTED ... NO LONGER INERT"; L642 "does not exist" + "CORRECTED ... it EXISTS LIVE"; L394 and L398 "CORRECTED 2026-09-01"; L433 "UPDATE ... precondition (1) IS NOW LIVE". **New pair written in session 71, the day principle 5 was added:** L513 says the "one deployment-wide bucket" sentence is wrong (#299), but L361 and L441 still say it |
| R4 orchestration rules / Opus subagents | CLOSED | L30 is principle 4 = the Workflow harness (#306); `bypassPermissions` has 0 hits; global `env` has `CLAUDE_CODE_SUBAGENT_MODEL=opus` + `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` |
| R5 Railway hook + duplicate MCP | PARTLY | `railway@claude-plugins-official` is false, so the per-Bash hook and the 32+32 duplicate are gone. `.mcp.json` still defines `railway` (stdio `cmd /c railway mcp`) and the local file enables it (`enabledMcpjsonServers ["railway"]`), which exposes `list_variables` to SC-rooted sessions with no deny rule. A user-scope server cannot be verified (`~/.claude.json` is off-limits); this Documents/AI-rooted agent has no `mcp__railway__*` tool |
| R6 ten Cowork plugins | OPEN | This agent's context lists about 40 `plugin:*` servers needing auth, plus `plugin:sales:salesforce` CONNECT_TIMEOUT 30000 ms. About 90 skills show their name only, including synack-*, qaren-brand-voice and, in the initial listing, sc-docs-70's qaren-cohort and qaren-referrals |
| R7 superpowers | CLOSED | Plugin false; no SessionStart injection in this agent's context |
| R8 do workflow agents get CLAUDE.md | CLOSED (answered) | This agent received the FULL sc-docs-70 CLAUDE.md (344,314 chars, ending at "## Detailed Context", so not truncated) right after its first `Read` of a file in that tree. The harness rules ride the brief preamble `s72-common.txt`, which is the fix R8 proposed. The cost consequence is under T1 |
| R9 broken skill YAML | CLOSED | #312: all 4 SKILL.md parse (m5); `tests/test_skill_frontmatter.py`; hook step 4c (`.githooks/pre-commit:333-378`); sc-s71-u13's qaren-eas-deploy and qaren-referrals now show their descriptions in this agent's listing |
| R10 parent-dir layer, empty Documents/.git, memory links | OPEN | No `Documents/.gitignore`; `Documents/.git` has no HEAD (rc 128); no `Documents/AI/.claude`. CLAUDE.md L273/L333 `memory/...` files exist only in the `C--Users-SynAckITPC-Documents-AI-smartcompare` auto-memory dir, not the repo `memory/` (8 other files) and not the Documents-key dir. The `[[feedback-*]]` links at L286/L290 use hyphens, the files use underscores, so they match no file anywhere |
| R11 secret guard / CI scan | PARTLY | Phase A (#312): JWT + credentialed-URL branch (pre-commit:169-173) and the `.env`-values pass (:185-327). OPEN: no gitleaks in the hook or CI, no `.gitleaks.toml`; #315 (no `--text`, so binary-looking blobs skip every scan) and #316 (L150 four-branch line without `--no-color --no-ext-diff`) |
| R12 MEMORY.md index | OPEN | 20,891 B, 13 "RESUME HERE", spliced session-65b line still present (m6) |
| R13 update rule grows CLAUDE.md | PARTLY | L31 adds "edit in place", but still orders "update CLAUDE.md, MEMORY.md" after major features (and "MEMORY.md" is still ambiguous). The file grew 19.9K chars in 2 days |
| R14 overlapping skill triggers | PARTLY | The code-review, superpowers and feature-dev plugins are off. Still in `~/.claude/skills` and model-invocable: `review`, `investigate`, `land-and-deploy`, `setup-deploy`, `ship`, `ios-*` x5, `setup-gbrain` / `sync-gbrain`. `synack-build-orchestrator` description is 512 chars and still claims "/plan" |
| R15 Sentry three ways | OPEN | Tracked `.claude/settings.json` still enables `sentry@claude-plugins-official`; installed_plugins projectPath is still lowercase `Documents\ai\smartcompare`. A working route exists: the claude.ai Sentry connector (deferred `mcp__25c88de3...` tools here, used for the 14-day react-native read) |
| R16 GitHub plugin | CLOSED | false |
| R17 Supabase MCP vs prod-write allows | OPEN | Plugin on (http). Local allows still pre-approve `execute_sql` / `apply_migration`. CLAUDE.md L90 still calls the MCP the preferred path, although 037/038/040/041/042 were all applied in the SQL editor |
| R18 settings.local.json tracked | CLOSED | `git ls-files .claude` = settings.json + 4 SKILL.md; `.gitignore` lists `.claude/settings.local.json`. The 192-entry prune moves to R1 |
| R19 stale worktrees | OPEN (worse) | 29 worktrees, 23 merged; 10 `sc-w3-*` hold junctions. During this run the listing gained 16 duplicate qaren-* entries from sc-s71-u13, sc-s71-t0b and sc-s71-u8b; this agent read no file in the last two |
| R20 four gate rules | CLOSED | One UUID (L487-488 = 54b603e8), "11" matches the 11 rows of `tests/.pre_impl_failures.txt`, tsc by path (L74, L327), one junction rule (L327) |
| R21 flag registry | OPEN | L341 "All flags default OFF in code" sits on the same line as three "(default ON" entries, plus default-ON rows at L346 and L371; no `docs/FLAGS.md` |
| R22 stale architecture facts | OPEN | L116 "~1,500 lines" vs 9,174 measured. 14 `*_routes.py`, 12 listed (`home_routes.py`, `profile_routes.py` missing). L204 "migrations/010-026" vs files up to 043. L485 "~557 test files" vs 677. L237 "~98 tests" vs 104 defs. L255 `{,.design}.md` vs the real `-design.md`. L875 cites a scrapedo doc that does not exist |
| R23 account skills brand | NOT VERIFIED | Account skills are not readable from disk here; they are listed name-only |
| R24 stdio MCP weight | OPEN | context7 installed version 2cd88e7947b7 = `npx -y @upstash/context7-mcp` (stdio); the hosted c447c3207a42 config sits in the cache but is not active. pdf-viewer tools are still present |
| R25 Figma | CLOSED (plugin) | The connector remains, see T5 |
| R26 Codex | OPEN | `codex@openai-codex` true; its hooks.json is active |
| R27 plugin agent collisions | CLOSED | feature-dev and superpowers off; codex-rescue stays (R26) |
| R28 hook mechanics | PARTLY | Staged blobs via `checkout-index --prefix` (:22-48), nested/case/renamed `.env` refused (:181), black-missing WARNING (:135), `scripts/setup_hooks.sh`, `core.hooksPath=.githooks`. ESLint on staged files is Phase B |
| R29 dead or colliding skills | OPEN | `_gstack-command` == `gstack` (sha 4669df05cb64); pov-reels-montage, scaffold-exercises, migrate-to-shoehorn, setup-pre-commit (Husky), git-guardrails, benchmark-models and pair-agent are all model-invocable |
| R30 update settings, stray file | OPEN | `DISABLE_AUTOUPDATER` and `autoUpdatesChannel: stable` are both set; `~/.claude/.claude.json` (569 B) still exists |
| R31 vague / stale directives | OPEN | L27/L29 principles 1 and 3; L35 principle 9 (inbox / ACK, a relic of the retired TeamCreate mode); L504 "Age policy (locked)" with D9 still pending; L876 the Session-54 Google Sign-In bug |
| R32 AGENTS.md fork | OPEN | `smartcompare/AGENTS.md` untracked, 67,332 B, "app brand: Qaren", no "MYEZ" |
| T1-T3 CLAUDE.md slimming | OPEN | See Part 4; T7, T10, T15 and T17 CLOSED with R7, R5, R25 and R18; T8 PARTLY (codex); T16 OPEN (`effortLevel: xhigh`) |

## 3. RELIABILITY ISSUES (open items only, highest impact first)

Layers: G = global (`~/.claude/*`, desktop, claude.ai), P = project (repo), PD = parent dir.

1. **CFG-01 [high] CLAUDE.md tells agents to copy `.env` into worktrees** (P).
   - Where: L286 (c) "copy `.env` into each pytest-running worktree"; L286 (g) "comm-gate harness ... + copy `.env` in"; L203 "sync LOCAL `.env` and worktree copies".
   - Problem: R8 is now proven: agents receive CLAUDE.md. These lines contradict three other rules:
     - the brief rule "Never copy .env anywhere";
     - principle 10;
     - #207/#48, whose conftest strips credentials, so the free tier needs no `.env`.
   - The session-67 lesson at L594 (5), "agents keep copying `.env` into scratch dirs", is this instruction at work.
   - Fix: delete (c) and the `.env` step of (g). In L203 keep "sync the clone's `.env`" (orchestrator only) and drop "worktree copies". Make principle 10 say "never copy `.env`".

2. **R1 + CFG-05 [high] deny rules unapplied, and the prepared list has holes** (G, Ahmed).
   - Where: `~/.claude/settings.json` has no `permissions` key; `apply_audit_batch_a.py:62-86`; the local allows listed in §2.
   - Problem: R1 itself still holds. Also, the 20 rules deny only the Read tool on `.env` and only the exact `Bash(env)`. Claude Code documents that Read rules do not cover Bash subprocesses; this was not probed here. So these stay open:
     - `cat` / `type` / `Get-Content` on `.env`
     - `Get-ChildItem env:`, `set`, `export -p`
     - `railway run ... -- env` (and `printenv`)
     - `git restore <file>` (the same erase as `git checkout --`)
     - Git-Bash `rm -rf` (the junction rule at L327 calls every recursive removal unsafe)
   - Fix: add those forms to DENY, keeping the `git worktree remove --force` scratch flow and `git restore --staged` allowed. Ahmed runs `--apply`. Then prune the local allows to wildcard read-only entries.

3. **R6 [high for agent spawn + listing] Cowork plugins** (G, Ahmed).
   - Every agent start probes about 40 needs-auth servers and waits on salesforce's 30,000 ms connect timeout (observed in this agent).
   - The listing overflow still hides about 90 descriptions.
   - Fix: as in the 10-03 audit: disable the ten plugins in Desktop, keeping legal only for U8 if wanted.

4. **R3 + R2 + CFG-03 [medium] contradictory statements in the always-loaded file** (P).
   - Where: the pairs in §2 R3; L21 "U4d in flight".
   - Fix: fold each pair into one dated sentence. L21 becomes "U4d merged (#307); the production binary must contain it". Fix L361/L441 per #299, or state the open question once.

5. **CFG-04 [medium] Ultracode rules fight principle 4 and the harness** (P).
   - Where: L290 (a) "NEVER run the full test/jest suite inside an IMPLEMENT task", (b) "<= 2-3 concurrent", (d) "batch <= 4 concurrent".
   - Problem: these sit against:
     - principle 4 (L30: at most 2 gate-heavy workflows);
     - the brief's full-suite jest command for green agents;
     - L576 ("the FULL jest suite is the arbiter");
     - the memory rule "after rebasing a client unit run the FULL jest suite before the PR".
   - Fix: delete (a), (b) and (d), or restate them inside principle 4 with the current bounds.

6. **CFG-02 [medium] runnable commands that the harness forbids** (P).
   - Where: L463-L474: bare `python -m pytest`, including three `LIVE=1` suites that spend money and hit Railway; L50-55 production curl; `npm install` / `npx expo install`.
   - Fix: put the bounded-runner recipe first, and label the LIVE / prod / install commands "owner or orchestrator only, never in an agent brief".

7. **R11 + R28 [medium] secret-scan gaps (T0b Phase B)** (P).
   - Phase B is still owed: gitleaks pass, `.gitleaks.toml`, CI job, ESLint on staged files, and fixes for #315 and #316.
   - Already the next planned unit (SESSION_71_STATE §0 item 2).

8. **R17 [medium] DB lane path** (P + G).
   - Where: L90 names the Supabase MCP as the preferred path, while every apply since session 67 used the SQL editor. The local allows pre-approve prod SQL writes.
   - Fix: L90 makes the one-paste PRECHECK/APPLY/POSTCHECK files primary (043 is next), and the two allows are removed.

9. **R19 [medium] 23 merged worktrees** (P / PD).
   - Problem: stale CLAUDE.md and skill copies, plus listing duplicates (16 observed in this run).
   - Fix: prune with the junction-safe order at L327, after Ahmed approves the list.

10. **R5 [low-medium]** (P): keep `.mcp.json` `railway` only after the deny rules land, or move it to user scope, as planned.
11. **R15 [low]** (P): set `sentry@claude-plugins-official` false in `.claude/settings.json`; the claude.ai Sentry connector is the working route.
12. **R10 [low]** (PD + P):
    - Add `Documents/.gitignore` with `*`.
    - Cite memory facts by absolute path, or move them into `docs/`.
    - Fix the hyphen-vs-underscore `[[feedback-*]]` names.
13. **R12 / R13 [low]** (G / P):
    - Trim MEMORY.md to one resume pointer and repair the spliced line.
    - Principle 5 should name the exact memory path and stop routing session narrative into CLAUDE.md.
14. **R21 / R22 / R31 / R32 [low]** (P): stale facts and vague directives (§2 rows); fold them into the T1-T3 restructure.
15. **R14 / R29 / R30 / R24 / R26 / CFG-06 [low]** (G):
    - Prune the skill clusters and duplicates.
    - Drop one of the two update settings and the stray file.
    - `/plugin update context7`.
    - Turn codex off unless the lane uses it.
    - CFG-06: `typescript-lsp` stays enabled although CLAUDE.md L74 and the M21 lesson record fabricated diagnostics (5 in one day). Disable it for agent work, or accept the noise.

Healthy (no change needed):
- Principle 4 + CLAUDE_CODE_SUBAGENT_MODEL / FORCE.
- Repo skill YAML and its two checks (hook + CI test).
- `core.hooksPath` wired.
- settings.local.json untracked.
- The names-only Railway recipe.
- The one-rule gates (R20).
- No user or project subagents, slash commands or settings hooks colliding with built-ins.
- No literal secret seen in any settings surface read (structure only).

## 4. TOKEN EFFICIENCY

| Consumer (largest first) | Size now | Who pays | Trim / lazy-load | Rough saving |
|---|---|---|---|---|
| CLAUDE.md | 344,314 chars, ~86K tok | **Every workflow agent that Reads any file in a worktree** (observed here), plus SC-rooted main sessions | T1: move the 17 Active-runtime blocks (157,889 chars) to `docs/SESSION_BUNDLES.md`. First hoist the binding rules (L594 lessons, flag rows inside blocks) into a short "Harness and gate rules" section and the flag index. Leave a pointer of 15 lines or fewer | ~37K tok per load |
| | | | T2: generate `docs/FLAGS.md`; keep about 130 index lines (100,631 chars today) | ~20K tok per load |
| | | | T3: narrative in the core (Important Patterns 30,382, fragrance findings 11,927) to docs, keeping the one-line rules | ~5-8K tok per load |
| | | | **Total: ~86K -> ~20-25K** | **~60-66K tok per agent that reads a repo file**; at a session-69 scale of about 265 agents, up to ~16M tokens per session |
| Skill listing | ~6K tok at start (estimate, about 217 entries) + ~1.3K tok of duplicates gained in this run (16 qaren-* entries); about 9.5K if all 29 worktrees surface | Every agent | R6 (Cowork 10), R14/R29 prune (73 invocable user skills, 8,212 desc chars), R19 worktree prune, T11 synack-build-orchestrator description 512 -> ~300 chars | ~2-4K tok per agent, plus the duplicate growth avoided |
| MEMORY.md index | 20,692 chars, ~5.2K tok | Every agent (observed) | R12: one resume pointer, history collapsed to a docs pointer, at most ~8K chars | ~3K tok per agent |
| claude.ai connectors: Canva, Figma, Miro, **Gamma (new since 10-03)**, Claude Docs | ~7K chars of deferred names + ~5K chars of server instructions, ~3K tok | Every agent | T5: disable the unused ones for Code (Ahmed, connector settings; per session via `set_session_connector_enabled` is untested for subagents) | ~2.5-3K tok per agent |
| Needs-auth / failed-server notices + Cowork deferred tools | ~0.5K tok + 30 s salesforce wait | Every agent | R6 | ~0.5K tok + spawn time |
| gitStatus from the empty Documents repo | ~0.25K tok (about 20 untracked lines) | Documents/AI-rooted sessions | R10 `Documents/.gitignore` | ~0.25K |
| `effortLevel: xhigh` global | thinking tokens, not measured | Main sessions | T16 | unquantified |

Capability kept: archived text stays in `docs/` and loads on demand. Every disabled plugin is unused or duplicated. Skills set to disable-model-invocation still run on an explicit /name.

## 5. Three highest-impact fixes for the remaining launch units (U3b, U8, U10, T0b Phase B, the production build)

1. **Close the secret and destructive paths at the config layer, not in prose.**
   - Ahmed runs the batch-A deny list once, extended with the CFG-05 forms.
   - Claude deletes the three "copy `.env`" instructions (CFG-01) in the next docs PR.
   - CLAUDE.md now provably reaches agents, so today it is both the rule and the hole.
2. **Slim CLAUDE.md (T1-T3) and fold the contradiction pairs (R3, CFG-03, CFG-04, CFG-02) in the same docs unit.**
   - This saves ~60K tokens for every agent that reads a repo file.
   - It removes the competing instructions that every Opus agent of the lane now receives.
3. **Disable the ten Cowork plugins (R6) and prune the 23 merged worktrees (R19).**
   - Per agent start this removes about 40 auth probes, a 30 s connect timeout and about 90 truncated skill descriptions, plus the growing duplicate skill entries and stale CLAUDE.md copies.

## 6. Not verified
- Whether the deny rules actually block when probed. Ledger:29 and SESSION_71_STATE:71 record a docs-based check, not a live probe. Whether Read deny rules also bind Bash/PowerShell readers: per the docs they do not; not probed.
- The user-scope MCP entries (railway, sentry) and Supabase auth state: `~/.claude.json` is off-limits. No `mcp__plugin_supabase_*` tool is in this agent's deferred list.
- Whether a second, identical CLAUDE.md (sc-s71-u13) would be injected again on a Read. Not tested, to protect this agent's context. A `Grep` on that tree surfaced its skills but no CLAUDE.md text.
- Why the sc-s71-t0b and sc-s71-u8b skill sets appeared in this agent's listing without a read in those trees.
- R23 account-skill contents; where bypass mode is set (no `defaultMode` in the global file); the host-injected schema cost; exact listing size (estimated).

## 7. Files written (sha256 in the final report)
`notes.md`, `m1.py`-`m6.py` and their outputs, `m2_lines.txt`, `m5_desc.txt`, `m5_skills.json`, `m6_worktrees.txt`, `m7_lines.txt`, this file.
