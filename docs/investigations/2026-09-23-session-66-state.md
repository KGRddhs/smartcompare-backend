# Session 66 — one Fable session takes over both lanes (2026-09-23)

## What happened

- The two prior sessions (the W3-remainder lane and the W4 lane) could not be resumed by id, because workflow resume ids do not work across sessions. Their state was recovered from their workflow journals instead.
- Both idle lane sessions were archived. Session 66 now owns all of W3 and W4.
- The skill is `synack-build-orchestrator`. Fable orchestrates, and Opus 5.5 agents do the work.
- Step 1 was a read-only config audit. It produced a 13-finding plan, which is attached to the chat and has **not been applied yet**.
- Work is test-driven, with a Fable red gate before every green: no green starts until Fable has reviewed its red tests.

## Merged this session so far

#163 (redaction of a committed admin key, `64afd23b`), #164 W3-9 test-only lucide fence (`2ec8131e`), #165 W3-4 branch-root exit (`b6f94052`), #166 W3-3 device fingerprint on social sign-in behind `ENABLE_SOCIAL_DEVICE_FINGERPRINT` (`b203cfcc`). W4-1's re-adversary returned SOUND (four reproduced minors closed in a pre-commit polish); its PR follows this one. This docs PR also salvages, from two superseded July/August PRs, the 2026-07-04 EAS lessons in `.claude/skills/qaren-eas-deploy/SKILL.md` (#11) and the three `docs/investigations/2026-08-17-*.md` measurements (#45), then those PRs and #25/#35/#38 are closed as superseded per the 2026-09-23 audit.

## Reconciliation ledger (critic-verified)

1. **BLOCKING: a production admin key is in the PUBLIC repo's history.** It was committed on 2026-06-08 at `docs/plans/2026-06-08-backend-comparison-overhaul-plan.md:23`. #163 redacted it on main, but git history still has it. **The key must be rotated.**
2. **MAJOR: production secrets were copied into local transcripts.** On 2026-09-07 a review subagent called Railway `list_variables`. That put eight raw production secrets into the local transcripts of six sessions, across both project dirs:
   - `ADMIN_API_KEY`
   - `BRIGHTDATA_API_KEY`
   - `CLOUDFLARE_API_TOKEN`
   - `FIRECRAWL_API_KEY`
   - `OPENAI_API_KEY`
   - `SENTRY_DSN`
   - `SERPER_API_KEY`
   - `SERPER_API_KEYS`

   Six other variables were already masked by the MCP. All eight were redacted in place on 2026-09-23: 245 files, 1,933 occurrences, 0 left. **These eight keys must be rotated.**
3. **MAJOR: the M13-29 RLS migration was never merged, and its number now collides.** It exists only on the local branch `claude/strange-volhard-157220`, in the nested worktree `smartcompare/.claude/worktrees/angry-wescoff-fc8992`. It is numbered 036, which main already uses. It must be renumbered to 039, because 038 is W3-16's, and then reviewed as its own unit.
4. **The unit specs existed only in gitignored folders.** This PR archives them in `docs/investigations/specs/2026-09-23/`.
5. **A killed mutation runner leaves its mutation on disk.** This is why the 2026-09-11 W4-1 rework was misread as "R2 unimplemented". Rule: after any kill, compare each mutation target's sha with the pre-mutation sha in the runner's log.
6. **Hygiene work done:**
   - Retired 28 finished worktrees without touching the shared junction. The shared `node_modules` was checked throughout and stayed at 696 entries.
   - Deleted 17 merged remote branches.
   - Removed stray probe files.
   - Built a pinned venv, `.venv-qaren`, from the lockfiles. The global Python has drifted from CI (for example fastapi 0.115 locally vs 0.141.1 in CI).

## Unit status at time of writing

| Unit | Status |
|---|---|
| W3-3, W3-4, W3-9 | SOUND and committed (W3-9 merged as #164; W3-4 in flight as #165) |
| W3-6, W3-13, W3-15 | SOUND; in a pre-merge polish round for minor issues the reviewer reproduced |
| W3-7 | SOUND; fix round pending |
| W3-14, W3-16 | DEFECTIVE at round 0; now in fix rounds |
| W3-11bcd | SOUND; in a fix round for test rows that prove nothing |
| W4-1 | Fix round done; the adversarial re-review is running |
| W4-2 | Spec reviewed and binding rulings appended; waits for W4-1 to merge |
| W4-3, W4-4, W4-9, W4-10 | Specs reviewed and binding rulings appended; red tests running |
| W4-6a, W4-7, W4-8, W4-11, W4-12, W4-13, W4-14 | No spec yet |
| W4-6b | No spec yet; blocked on the #101 product call |

## Ahmed's list

1. **Rotate the eight keys in ledger item 2.** Do the admin key first, because it is in public history (ledger item 1).
2. Set `ENABLE_BRIGHTDATA_BUDGET_GATE=true`.
3. Run the OTA: `eas update --branch preview --clear-cache`.
4. Apply migrations 035, then 036, then 037. Then check that calling the `delete_user_cascade` RPC as anon returns 42501.
5. Add the `EXPO_TOKEN` repo secret.
6. Run `railway login`.
7. Supply the W3-7 icon artwork.
8. Supply the W3-16 age-gate copy.
9. Make the #101 product call, which unblocks W4-6b.
10. Make the product call on the "(converted from USD)" caption for W4-1 and W4-2.
11. Once the audit reports, decide whether to close or rebase the nine open PRs from before this session (#11…#45).
