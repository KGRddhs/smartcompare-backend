# MYEZ App Store launch — implementation plan (session 71, 2026-10-03)

Produced under `/synack-build-orchestrator` Step 4 by the Fable orchestrator. PRD (Ahmed, 2026-10-03): `docs/investigations/2026-09-29-session-69-state/APP_STORE_LAUNCH_RUNBOOK.md` + `docs/investigations/2026-09-29-session-69-state.md`. Inputs: `CONFIG_AUDIT_PLAN.md` (Step 1) and `RESEARCH_DIGEST.md` (Step 3) in this folder. Base: main `4bd5a09f` (#278 locks + #277 docs merged today).

**Roles.** Fable (main session) plans, rules, reviews specs/tests/diffs. Every agent is Opus (`model: 'opus'`), in workflows. Max two gate-heavy workflows at once; bounded pytest runner; stall monitor.

**Per-unit loop (Step 5).** Opus writes the tests (RED, each failing for the stated reason) → **Fable gate on spec + tests** (blocking issues become GitHub issues through the REST helper) → Opus implements to GREEN → two Opus adversaries (distinct lenses, mutation checks) → Opus fix round → **Fable reviews the diff** → gates (unit tests, comm gate / full jest, lint, static analysis, pre-commit hook) → commit → PR → the five required CI checks → merge. RED and GREEN are separate workflow launches so the gate sits between them.

**Out of scope (binding, from the PRD):** switching LLM provider; StoreKit/IAP; iPad support; scraper flag flips before App Store approval; any dark flag activation; the fourteen session-68b flags.

---

## Milestone 0 — configuration and tooling (needs Ahmed's approval per audit batch)

| Unit | What | Files | Tests / check |
|---|---|---|---|
| **T0a** global settings (audit batch A) | `permissions.deny` list (R1), disable unused plugins (R5, R7, R16, R25–R27), Opus subagent default (R4), one user-scope `railway mcp`, context7 update | `~/.claude/settings.json`, `~/.claude.json` | Probe first: is `deny` enforced under bypass mode, and is the subagent-model env name honoured. If deny is not enforced, one PreToolUse guard hook instead. Read-back of each key; a probe command that must be refused. |
| **T0b** repo tooling PR (audit batch C, Step 2) | Pre-commit additions, all ADDITIVE (no safety check weakened): gitleaks staged scan (fail closed when present) + JWT/credentialed-URL regex branches (R11); lint staged blobs not the working tree, widen the `.env` refusal, warn when black is missing (R28); eslint on staged `SmartCompareApp/src` files; a `yaml.safe_load` frontmatter check over `.claude/skills/*/SKILL.md`. CI: a gitleaks job. Fix the two broken skill frontmatters (R9). Untrack `.claude/settings.local.json` (R18). Remove the duplicate `railway` server from `.mcp.json` (R5) only after T0a adds the user-scope one. | `.githooks/pre-commit`, `.github/workflows/ci.yml`, `.claude/skills/qaren-eas-deploy/SKILL.md`, `.claude/skills/qaren-referrals/SKILL.md`, `.gitignore`, `.mcp.json`, `tests/test_ci_gates.py` (pins) | RED: a test that every `SKILL.md` frontmatter parses (red on the two files); `test_ci_gates` pins for the new hook lines and the CI job (red at base); a fixture-driven hook test (a staged JWT-shaped and URL-credential sentinel is refused; an `sk-` shape still refused). GREEN gates: `tests/test_ci_gates.py`, `test_channel_freshness.py`, `test_hermeticity_pins.py` through the bounded runner; the hook run on a scratch commit. |
| **T0c** CLAUDE.md contradiction fixes (docs) | Fold the six appended corrections into their sentences (R3), remove contradictory prod-state lines in favour of one pointer (R2), rewrite principle 4 to the current harness and delete the TeamCreate/bypass line (R4), names-only Railway recipe (R1), the four inconsistent gate rules (R20) | `CLAUDE.md` | Docs PR; CI green; a grep proof for each removed contradiction. The large restructure (T1–T3, ~56K tokens saved) runs AFTER Milestone 1 so it cannot conflict with the OAI merge-time CLAUDE.md edits. |

Assumption: **no Prettier.** The repo has no Prettier config; introducing it would reformat every client file and collide with the CRLF/Edit-tool rule. ESLint 9 (flat config) + `tsc --noEmit` are the TypeScript static analysis; ruff tier + black allowlist + `py_compile` for Python; sqlfluff for migrations (all already wired). This follows the skill's "existing established patterns" rule.

---

## Milestone 1 — units that need none of Ahmed's inputs

### U4b — launcher art + Expo SDK 54 patch bumps + gesture-handler removal + CI ratchet (NATIVE)
- **Spec:** `docs/investigations/2026-09-30-session-70-state/U4B_ICONS_DEPS_SPEC.md` (R1–R12, P0–P8, G1–G11, 14 binding corrections, rulings RQ1–RQ12). Worktree `sc-s70-u4b` (own `node_modules`).
- **State:** RED complete and Fable-reviewed PASS (`FABLE_REVIEW_RED_U4B.md`): 19 red / 39 green / 58. Next = rebase onto `4bd5a09f`, then GREEN.
- **Session-71 addendum to the rulings (from the research digest):** (RQ13) every orchestrator/manual `expo install --check` runs as `CI=1 … --check` (an interactive TTY prompts "Fix dependencies?" default Yes and rewrites `package.json`); the rewritten CI comment must not say "never writes". (RQ14) the report-only online step counts as online-verified only if its log lacks the offline-fallback warnings. (RQ15) the offline gate cannot see `expo` itself or `babel-preset-expo`; k1/k2 and correction 11's P8 check are the guards — state it in the CI comment. (RQ16) `package.json` is rewritten by `npx expo install` (LF, re-sorted): R12/G10 are judged on parsed JSON + content-line diff, not raw bytes. (RQ17) P3 runs with `EXPO_NO_NEW_ARCH_COMPAT_CHECK=1`. (RQ18) PR body wording: the store icon is pixel-equivalent, not byte-identical; the favicon is web-only and not a launch item. (RQ19) trim the stale "(AHMED: supply art …)" suffix from b1/b2 names.
- **Edge cases:** a newer SDK-54 patch appearing mid-run (STOP, RQ8); `babel-preset-expo` nesting (correction 11); `@expo/prebuild-config` moving to 54.0.9 (correction 5 grep); the known `HistoryScreen.mobileJank.m21` flake (re-run once).
- **Orchestrator-only steps after GREEN:** `CI=1 npx expo install --check` online, `npx expo-doctor`, optional `@expo/fingerprint` before/after diff for the PR body.

### OAI/obs — #265 retry ceiling, #268 cap-downgrade visibility, 8 empty-message log sites, never-retrieved gather future (backend, unflagged)
- **Spec:** `…/2026-09-30-session-70-state/OAI_OBS_SPEC.md` (R1.1–R4.3, C1–C11, rulings OQ1–OQ7, OR1–OR5). Worktree `sc-s70-oai`.
- **State:** RED incomplete (four untracked files, unverified). Next = rebase onto `4bd5a09f`, Opus RED (finish/rewrite), Fable gate, GREEN.
- **Session-71 addendum:** (OR6) SDK-path tests mock at `guarded_llm_create` / `chat.completions.create` (openai 3.3.1 runs on httpx2; respx and `httpx.MockTransport` do not intercept it). (OR7) item-4 tests assert only on `context['message']` (the attached `CancelledError` can be traceback-less). (OR8) the "contextvar would not work" rationale is wrong on 3.12.9 (`wait_for(timeout>0)` runs in the same task): the return-value carrier stays, the rationale stays out of code comments and the PR body. (OR9) no `exc_info=True` at the eight sites (it would regroup Sentry events by stack). (OR10) the `_retrieve_prefetch_outcome` docstring states its precondition (every entry is a gather with `return_exceptions=True`). (OR11) C9's post-deploy check = `<prefix><TypeName>` on one accumulating issue (the title follows the latest event). (OR12) runbook §6 states the complimentary-token allowance is tier-dependent (250K/day Tier 1–2, 1M Tier 3–5) and that tier + enrolment are Ahmed's to read. (OR13) §7 limits gain the pre-existing `'rate'` substring over-match in the 429-fallback trigger. (OR14) the comm gate's BASE is the rebased base `4bd5a09f` (fresh run on the current venv), not `94c097cd` — like is compared with like after the lock bump.
- **Edge cases:** `DAILY_4O_CAP` garbage/inf/nan/<1; Redis down (counts 0, verdict stays on the verdict model); self-critique regen served vs rejected; streaming with `ENABLE_FULL_STREAM_DEADLINE` on and off; a prefetch child that raised inside a cancelled gather.

### U4c — the in-app MYEZ mark (JS + bundled PNG; OTA-capable; must be in the store binary)
- **Depends on:** U4b merged (it extends `scripts/render_myez_icons.py`). Spec to be written by an Opus spec agent from this description, adversarially reviewed, then ruled by Fable before RED.
- **Files:** `SmartCompareApp/src/components/QarenLogo.tsx` (module path, default export and testIDs kept — 11 suites mock this path); new `SmartCompareApp/assets/brand/myez-mark.png` + `@2x` + `@3x` (128/256/384 px RGBA, transparent, rendered deterministically from the committed master via the U4b renderer with manifest entries and `--check`); `scripts/render_myez_icons.py`; `docs/brand/myez-icons.manifest.json`; the two `LoadingRings` snapshots; tests.
- **Contract:** `QarenLogo({ size })` renders React Native `<Image source={require(...)} style={{width: size, height: size}} resizeMode="contain">`, hidden from accessibility exactly as today; the `color` prop is dropped (tintColor would recolour the emerald dot; no `src` caller passes it). No `expo-image` (native → would break OTA under RQ2). No RTL flip.
- **Edge cases:** sizes 24–128 pt at six sites (`LoadingRings` uses `round(size*0.22)`); the cut-out is exact only over white/near-white backgrounds (measure each site's background); the launch-screen → JS-splash hand-off; the brand text next to the mark; jest's PNG stub (`require` returns the stub — compare with `toBe(require(samePath))`).
- **Test list:** the component renders the host `Image` with width/height = size, `resizeMode contain`, the a11y-hidden props, and the required source; no site renders the Q-ring SVG; the three PNGs exist with the manifest's sha256/dimensions/mode (reusing the U4b decoder); the renderer `--check` passes; `LoadingRings` snapshots updated by ONE authorised `jest -u` on that file with the diff reviewed (Svg subtree → Image) — needs a ruling; FULL jest, tsc, eslint.
- **Design calls (Ahmed, see "Decisions"):** keep or drop the app-name text beside the mark; start the splash mark at the launch position and full opacity.

---

## Milestone 2 — units gated on Ahmed's inputs

### U3b — AI data-sharing toggle and policy §11 (after D3)
- **Spec:** `…/2026-09-29-session-69-state/U3_AI_CONSENT_SPEC.md` R4. **D3 = A (recommended; research: option B collides with Apple 5.1.2, KSA IR Art 11(1)(e) and Bahrain PDPL Art 3(2)):** remove the Profile "Help improve AI quality" toggle and its keys, delete `select_client_for_user` and the `OPENAI_API_KEY_PRIVATE` branch (closes #266). **D3 = B:** route all 17 call sites through `select_client_for_user` (unset = OFF), separate opt-in, `AI_CONSENT_VERSION = 2`.
- **Files (A):** `SmartCompareApp/src/screens/ProfileScreen.tsx`, `src/i18n/{en,ar}.json`, `app/services/openai_service.py` (+ callers), tests; `BRAND_KEYS`/copy fences as needed.
- **Tests:** no caller of `select_client_for_user` remains (AST scan); the toggle keys are gone from both catalogs (the no-deleted-keys fence updated by ruling); explicit `store=False` decision pinned if adopted; consent sheet copy hash ↔ version fence.
- **New scope candidates found by research (NOT added without Ahmed's call):** an in-app consent **withdrawal** control (Apple 5.1.1(ii), Bahrain Order 48/2022 Art 6, KSA IR Art 12(2)); a **server-side consent record** (KSA IR Art 11(1)(d)).

### U8 — privacy policy and terms redraft (LAUNCH BLOCKER; after the 8 legal inputs + D3 + D5)
- **Files:** `app/legal/privacy_policy.md`, `app/legal/terms_of_service.md`, `app/api/legal_routes.py` (`last_updated`), `SmartCompareApp/src/services/consent.ts` + `app/services/consent_service.py` (`TERMS_VERSION`), `tests/test_consent_capture_w3_16.py` pin, `landing/{privacy,terms}.html`, `landing/ar/{privacy,terms}.html`, `SmartCompareApp/src/screens/LegalScreen.tsx` (language parameter, M16).
- **Contract:** the MUST list M1–M17 of the research digest, each traced to its source; no legal fact invented — every `<PLACEHOLDER>` comes from Ahmed's inputs.
- **Edge cases / pitfalls to resolve with Ahmed:** a 30-day response time breaks Bahrain's 10/15-working-day deadlines; a "Beta" label conflicts with App Review 2.2; today's deletion promises are untrue (`delete_user_cascade` keeps `admin_audit_log` and the users row and does not null demographics/display_name/email) — describe truthfully or fix in a small backend unit; AR pages need native review (garbled line at `landing/ar/privacy.html:273`).
- **Tests:** `grep -ri draft app/legal landing` = 0; version pins move together; the brand fence over the legal pages; the legal route returns the new `last_updated`; an AR/EN parity check of section headings.

### U10 — `eas.json` `submit.production` (after the ASC app id)
- **Files:** `SmartCompareApp/eas.json`. **Contract (option A, key stored on EAS):** `{"submit":{"production":{"ios":{"ascAppId":"<digits, QUOTED string>","appleTeamId":"8K562M549D"}}}}`.
- **Test:** validate with the RESOLVED submit schema (`EasJsonUtils.getSubmitProfileAsync`), not JSON parse (a placeholder passes every cheap check); a jest pin that `ascAppId` matches `/^\d+$/` and `appleTeamId` `/^[\dA-Z]{10}$/`.

### U11 (optional) — Sign in with Apple token revocation
Needs a product/legal call first (store the refresh token at sign-in vs re-authenticate at deletion) and a SIWA key from the Apple session. Not planned for 1.0.0 unless Ahmed says so.

---

## Milestone 3 — release (Ahmed's actions, Claude verifies)
1. **OpenAI live:** after Ahmed's top-up + new key → `verify_after_credits.py` + the app-shaped REST compare (pass = real verdict, specs, a price, pros/cons, no 429).
2. **Step 6 structured code review** (security, performance, complexity, dead code) over everything merged since `94c097cd`, by Opus reviewers in a workflow, findings ranked into one action plan; accepted findings become issues and new units. Run at the end of Milestone 1 and again pre-handoff (before the production build).
3. **Build path (Ahmed, real terminal):** `eas credentials` → preview build → smoke on two iPhones (sign-in, camera, compare, push, Arabic walkthrough, fresh-install splash hand-off, a Sentry react-native event) → `eas build --profile production` → `eas submit --id <build>` → internal TestFlight smoke → listing fields, App Privacy from the inventory, 13+ override, review notes, demo account, warm-up pairs → Submit for Review.
4. **After approval:** `APP_STORE_URL`, the Worker's `idTBD`, production-branch OTAs with `--environment production`.

---

## Sequencing (two gate-heavy workflows at a time)
- **Wave 1 (now):** U4b GREEN ‖ OAI RED. Then the OAI Fable gate → OAI GREEN ‖ U4c spec + review.
- **Wave 2:** U4c RED → gate → GREEN (after U4b merges) ‖ T0b tooling PR (if batch C is approved).
- **Wave 3:** Step 6 review of Milestone 1 ‖ T0c docs.
- **On Ahmed's inputs:** U3b, U8, U10 as each unblocks; then Milestone 3.

## Assumptions (and why each beats the alternative)
1. **Keep U4b's existing RED** (confirmed by Ahmed): it is complete, proven red for the right reasons and passed the Fable gate; rewriting it under Opus would repeat finished work.
2. **Rebase units onto `4bd5a09f` before building; comm-gate BASE = the rebased base.** The lock changed (pyjwt, urllib3); a BASE at `94c097cd` on today's venv would not be the code CI compares against.
3. **U4c keeps the `QarenLogo.tsx` path and renders a PNG via RN `Image`.** Renaming breaks 11 suites at load; a vector needs a source file the repo does not have; `expo-image` is native and would break OTA compatibility.
4. **D3 = A is assumed for planning only.** Lowest legal and review risk; nothing is built on it until Ahmed rules.
5. **No Prettier** (see Milestone 0).
6. **The large CLAUDE.md restructure waits until Milestone 1 merges.** The OAI unit edits CLAUDE.md at merge; restructuring first would make every later doc edit conflict.
7. **Adversaries are Opus; the orchestrator's diff review is the Fable gate.** Matches "Opus agents, Fable orchestrates and reviews".

## Decisions needed from Ahmed (beyond D3, D5–D14 and the 8 legal inputs)
- **Audit batches:** A (global settings), B (desktop/claude.ai — yours), C (repo tooling + CLAUDE.md fixes), D (housekeeping).
- **U4c design:** (1) drop the app-name text next to the mark on Home/Splash (the mark already spells MYEZ) or keep both; (2) start the JS splash mark at the launch position and full opacity, animating only the text; (3) authorise one `jest -u` on the `LoadingRings` snapshot file with a reviewed diff.
- **U8/I5:** response times of 10 working days (rectification, erasure, objection) and 15 working days (access) instead of a flat 30 days.
- **U8/I8:** no "Beta" label in the store listing.
- **Consent:** add an in-app withdrawal control (recommended for launch, small) and a server-side consent record (recommended as a follow-up unless counsel requires it for launch).
- **Deletion truthfulness:** fix `delete_user_cascade` to null demographics/display_name/email (a small backend unit + migration you apply) or describe the retained fields in the policy.
- **OpenAI dashboard reads:** usage tier, data-sharing enrolment and scope, Chat Completions storage default.

## Ahmed's answers (2026-10-03 ~07:20 AST) — recorded verbatim from the approval form
- **Plan:** approved; start Wave 1 (U4b GREEN and OAI RED in parallel, Opus, each stopping at the Fable gate).
- **Audit batches approved:** A (global settings), C (repo tooling + CLAUDE.md fixes), D (housekeeping, after the launch lane). Batch B is Ahmed's own.
- **U4c design:** drop the app-name text beside the mark; the JS splash mark starts at the launch position and full opacity (animate only the text); ONE `jest -u` on the `LoadingRings` snapshot file is authorised, diff reviewed by the orchestrator.
- **Legal/consent:** response times 10 working days (rectification, erasure, objection) and 15 working days (access); no Beta label in the listing; an in-app consent withdrawal control ships in U3b (the server-side consent record stays a follow-up); **account deletion is fixed in code** — a new backend unit **U8b** (`delete_user_cascade` also nulls demographics, display name and email; a migration Ahmed applies), specified in Wave 2.
- **Earlier today:** PRD = the launch runbook + the session-69 audit; GitHub issues through the REST helper; keep U4b's completed RED tests; PR #278 merged on green.
