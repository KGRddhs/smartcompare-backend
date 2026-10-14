# Session 79 resume prompt (MYEZ: App Review resubmission, the compare-quality units, PostHog B)

Run this session under /synack-build-orchestrator. The orchestrator plans and gates, and every workflow agent runs on Opus. Before the first launch, grep `CLAUDE_CODE_SUBAGENT_MODEL` in `~/.claude/settings.json`, then confirm `claude-opus-5-5` in the first agent transcript of each launch.

**Ledger:** `docs/investigations/2026-10-14-session-78-state/ledger.md`. It is the authoritative per-step record; read its tail first.

## State at the close of session 78 (2026-10-14)

### App Store: 1.0.0 (2) REJECTED, information only

Apple's message of 2026-10-13 is Guideline 2.1, "Information Needed - New App Submission". Submission id: cfef7ea0-131b-45d3-9a7e-1a2928b32752. The owner DEFERRED the reply ("another time"). Ready package, in the session-78 state folder:

- `REPLY_DRAFT.txt`: answers items 1-6, signed "The MYEZ team", 3,868 chars (the limit is 4,000).
- `NOTES_DRAFT.txt`: replaces the App Review Notes, 3,867 chars.
- `RECORDING_SCRIPT.md`: dry run, shot list, export.
- `DEMO_ACCOUNTS_SQL.md`: review accounts appreview1/2@getmyez.com, read-only checks, and the raise-the-limit UPDATE (finding F06).

**Steps when the owner is ready:**

1. **Owner** creates the 2 accounts and sends the emails (never the passwords). Claude runs SQL checks A and B; the owner runs C.
2. **Owner** dry run on an iPhone running the latest iOS, with 1.0.0 (2) from TestFlight. Test "Continue with Google": if it fails, drop it from reply item 4 and from the Notes SERVICES line. Test the photo compare: if it fails, item 1 says Link mode instead.
3. **Owner** records and trims the video.
4. **Claude, with the owner's yes:**
   - In ASC, tick "Sign-in required" (the owner types account 1's email and password) and paste the Notes.
   - Re-run `scripts/review_warmup.py --send-admin-key --pairs "iPhone 15 vs Samsung Galaxy S24" "Tom Ford Tobacco Vanille vs Creed Aventus" --runs 2`. Both pairs must PASS: the price cache lasts 24 h.
   - The owner attaches the video to the reply, the reply is sent, then "Resubmit to App Review".
5. **Read first:** the ASC reply box takes 4,000 chars plus Attach File. Release is manual. No OTA to the production EAS branch before approval and the owner's manual release.

### Legal (PR #353 MERGED, main e0f3e475, LIVE on the API and getmyez.com)

- **Identity:** the home address is removed. The controller line reads "Husain Aseeri, an individual app developer in the Kingdom of Bahrain, trading as MYEZ". The postal line reads "Kingdom of Bahrain (our postal address is available on request at privacy@getmyez.com)".
- **Recipients:** listed by category. OpenAI, Apple and Google sign-in, and the retailer websites stay named.
- **Terms v2:** 19 sections, with the Apple Exhibit B items, the liability carve-outs, a narrow indemnity and the minors rule.
- **Date:** 2026-10-14 in all twelve anchors. `consent.ts` reaches phones only with the first post-approval OTA.
- **P.O. Box swap:** a data change plus a re-measure of two count pins; the recipe is in the `_placeholders_comment` of `tests/fixtures/legal_fill_in_u8.json`.
- **Rulings:** LR1-LR11, LT/M, G1-G12 and F1-F6, in `specs/`.
- **Follow-up chip:** task_ac685e4d (self-host the web fonts; the FA1 AR pin).

### Production

- **Knob:** `PHASE2_MIN_RESIDUAL_SECONDS=12` on web since about 08:00. Canary before and after: ready 1/4 to 1/4; the iPhone pair 28.9 s to 23.4 s; loop lag max 7.0 s to 4.5 s. Kept.
- **Unchanged:** every other flag as in the session-77 state.

### Compare quality (`COMPARE_QUALITY_PLAN_S78.md`, diagnosis wf_31229115-6cb)

- **Root cause:** a serial per-product path adds up past the 30 s cap. The pros come only from the verdict. Partial results write no cache.
- **S78-TG** (worktree `sc-s78-tierguard`, branch `feature/s78-tier-fill-residual-guard`): a dark flag `ENABLE_TIER_FILL_RESIDUAL_GUARD` plus the knob `TAIL_RESERVE_SECONDS` 6.5. It skips the Tier-2 (4 s) and Tier-3 (3 s) fills when the residual is short.
- **S78-SM** (worktree `sc-s78-serpermemo`, branch `feature/s78-serper-key-memo`): a dark flag `ENABLE_SERPER_KEY_STATE_MEMO` plus the knob `SERPER_KEY_STATE_MEMO_TTL` 60. It memoises the exhausted-key Redis check, which removes about 2/3 of the blocking GETs.
- **Unit rulings:** `specs/RULINGS_S78_TG_SM*.md`. The ledger records which phase each unit reached (spec, RED, GREEN, PR).
- **Flips:** the owner's yes is needed for each, after its canary. The plan names the canary pairs, and every pair must be one never compared before.
- **Later candidates:** fix 6 (reserve the verdict tail at the pair barrier), fix 7 (the subtype router: Bose QuietComfort is detected as a phone, creams as sunscreen), fix 8 (report an all-timeout cap as TIMEOUT instead of 400), and S78-SM-b (the `api_budget_service._serper_key_prefix` memo).

### Not done this session (carried over)

- **PostHog unit B fix round 1:** rulings PF1-PF11 in the session-77 state folder; WIP d3a7dc9e on `feature/s77-posthog-server`. Never rewrite the pushed branch.
- **PostHog A, PostHog L, and the post-approval OTA:** see `NEXT_SESSION_PROMPT_S78.md` sections 3-6.

## Owner actions

See `OWNER_ACTIONS_S78.md`. The most urgent:

1. Make the GitHub repo private. The home address, a phone number and personal emails sit in its history and in older state folders.
2. Get a P.O. Box.
3. Read the exact name spelling on the Apple membership.
4. Set the EU DSA status (not set up), or limit availability to the GCC.
5. Check WHOIS and the Google OAuth support email.
6. File the PDPA Art. 14 notification.
7. Move to a business mailbox.

## Standing rules learned in session 78

- **Read tool in a worktree:** it injects that worktree's CLAUDE.md (about 86 K tokens). Read worktree files with bash, and write them with Python.
- **No personal values in the public repo:** tests are pattern-based; use a generic town list, never a digest of the owner's town, because a digest is reversible. Raw agent run JSONs (`runs/`) stay local: they can quote the address or test controls.
- **Workflow scripts:** a schema field the agent may fill with "completed: ..." must not gate an early return; check for `/^completed/`.
- **`railway variables`:** refused by the deny rule even for `--help`. A flip runs in the owner's Terminal panel with the owner's yes. Do not read that tab; verify through `/health` and log lines.
