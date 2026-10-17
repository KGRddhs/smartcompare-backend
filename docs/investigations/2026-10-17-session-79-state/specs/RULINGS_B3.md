# Fable rulings for build 3 (B3-A client, B3-B Apple token revocation), 2026-10-17 ~08:10 AST

Binding. They win over the specs and the reviews where they differ. Specs: `sc-s79-b3client/.qa-s79/B3A_CLIENT_UNIT_SPEC.md` (sha256 ef9f86ce...) with `B3A_SPEC_REVIEW.md`; `sc-s79-b3revoke/.qa-s79/B3B_APPLE_REVOKE_UNIT_SPEC.md` (sha256 9a49e17c...) with `B3B_SPEC_REVIEW.md`. Both reviews: APPROVE_WITH_RULINGS. Every proposed ruling below is adopted as written in its review unless amended here.

## Scope corrections (both specs relayed owner words that belong to the App Store screenshots, not the app)

- B3A-Q1 "improve the design, look at Cal AI": the owner meant the App Store screenshot set, which is done outside the app (set v5 uploaded). No design unit, no addendum. R-SCOPE-1.
- B3A-Q2 "a more attractive font for Arabic": also the screenshots (Microsoft Dubai on the marketing frames). No in-app font change in B3-A (RV4 adopted in its "do not fold" half; the B3-T typography unit is NOT opened unless the owner asks for an in-app font later). R-SCOPE-2.
- B3A-Q3 "do the 5 steps too": the owner's approval of the five build-3 items (1-4 client, 5 = Apple revocation). Nothing to map in the spec. R-SCOPE-3.
- RV5 (ask which screen): resolved by R-SCOPE-1; no restyle beyond C6's re-layout of Login and Register.

## B3-A (client) rulings

- A1 (BLOCKING, = RV1): R12, R13, R20, R20b, R21, R22, R24 use the reviewer's recipe: `await jest.isolateModulesAsync(async () => { ... })` requiring the async-storage mock, planting the record with `await setItem` (R21: stub `getItem` with a deferred promise), requiring `react` and `@testing-library/react-native/pure` INSIDE the isolate, then the host; never render an isolated component with the outer RNTL. RED proves each row red at base for its stated reason and green on the prototype.
- A2 (= RV2 / MR4): R51 sets `globalThis.__DEV__ = true` for its call and restores it.
- A3 (= RV3, gate ruling): the backend comm gate is chunk A (the 23 non-hook SmartCompareApp-scanning files, bound 1200) + chunk B (the 8 CLAUDE.md source-scanning pins, bound 600), at base and head, `comm -13` of the FAILED ids empty. The pre-commit-hook pair is excluded with the measured reason (two TIMEOUTs, writes fixture paths into a temp repo, reads no real client file). Strike L8 and gate 7's single 25-file chunk.
- A4 (= RV6): keep dropping `offlineAccess`; restate C6: no effect on iOS (serverClientID is set from webClientId unconditionally), a serverAuthCode is still issued and the app never reads, sends or stores it; the limit is recorded.
- A5 (= RV7 / MR9): `useLanguage` writes `@qaren_rtl_bootstrapped` = the target direction before `Updates.reloadAsync`, inside the same try and bound as `beforeReload`; R14/R15 assert the setItem before the reload; every "once" assertion is filtered by key.
- A6 (= RV8): `logout()`'s finally also clears `@qaren_onboarding_resume_v1`, beside `clearOnboardingDraft`.
- A7 (= RV9 / MR7): Register mirrors Login (ConsentRow, Apple, Google, OR, form); a blocked Create Account brings the consent error into view (R42b).
- A8 (= RV10 / MR11): new or changed AR values carry no diacritics except in «ميّز»; the 7 fixture strings are re-spelled before RED and stay marked [NATIVE READ].
- A9 (RV11, the owner's call): NOT adopted. The pre-permission CTA stays "Turn on camera" (the Notes v3 and the recording script name it; it is a feature CTA, not a prompt that directs the user to allow). R9 unchanged.
- A10 (= RV12): the four comm constraints become GREEN rules in spec 2.8 (authService.ts console lines carry `__DEV__` on the same line; "Web Client ID:" banned; the file readable in the default encoding; the other three as the review lists them).
- A11 (= RV13): R37 and gate 9 use the repo-root `docs/privacy-data-inventory.md`.
- A12 (= RV14 + MR1): adopt MR1 (R20b, the AR->EN resume), MR2, MR3, MR5, MR6, MR8, MR10 as rows and mutants M41-M45.
- A13 (= RV17, answers Q4): extend item 4 to the learning claims: `onboarding.s13.subtitle` ("Trained by your peers."), `onboarding.s14.cohort_footer`, `loading.cohort.caption`, the en :631-633 / :637 / :665 / :751 set, and the other "credits" strings (:339, :680). Survey-backed cohort counts may stay ("Informed by a survey of GCC shoppers" is the allowed framing).
- A14 (= RV18, answers Q8): keep R11 (the ScanCamera denied pad) as cheap defence.
- A15 (= RV19): `ENABLE_COHORT_PERSONALIZATION` is ON in production (since 2026-05-05, CLAUDE.md), so `onboarding.s4.subtitle` keeps both sentences.
- A16 (= RV20): `SocialSignInButton` may move to `src/components/SocialSignInButton.tsx` (added to gate 9); testIDs and labels unchanged.
- A17 (Q5): no `reloadScreenOptions`; out of scope. (Q6): the Login title stays "Welcome back."; only the subtitle changes (the recording script names the title). (Q7): no user-id binding of the resume record (TTL 10 min + single use), plus A6.
- A18 (contract with B3-B, = Q10): the social-login body field is `authorization_code`, sent for Apple only, only as a non-empty string, never for Google.
- A19 (RED mechanics for a client unit): the RED agent writes the test files in the unit worktree, runs them at base one jest process at a time by path under `timeout -k 15`, and proves satisfiability with an in-place prototype: byte copies (shutil) of every file it edits first, the prototype applied, the RED files run, then every file restored from the copies and sha256-compared. No scratch worktree with a junction, no recursive delete, no npm. The full jest suite is the arbiter at GREEN, not at RED.

## B3-B (backend) rulings

- B1 (BLOCKING, = RV-1): R7, R8, R19, R20 run with all four `APPLE_SIWA_*` variables set (key generated at run time) and a base-safe `httpx.AsyncClient.send` recorder; each asserts zero sends, zero admin `table()` calls and zero `[SIWA]` records; the mutation table maps X17->R8, X18->R7, X33->R19 under this setup.
- B2 (BLOCKING, = RV-3): R4 verifies the signature with `options={'verify_exp': False}` and separately asserts `exp - iat == 300`; R3 uses the real clock.
- B3 (BLOCKING, = RV-2, answers Q7): the exchange stays inline, each Apple call wrapped in `asyncio.wait_for(..., 6.0)` with httpx `timeout=5.0` inside; a bound TimeoutError is logged by type and counts as retryable for the revoke; R5, R11, R14 restated, R27 added; L6 = at most about 12 s, the sign-in cost at most about 6 s.
- B4 (= RV-4, answers the activation order): before build 3 is submitted: the owner creates the key and keeps the .p8, 044 is applied with its postcheck, the four variables are set, the flag is flipped; then a canary on the TestFlight install of build 3 with a test Apple ID ("exchange status=200", no "store failed"; delete the account; "revoke status=200"). The spec's 8.2 is rewritten in that order. The flag is a no-op for build-2 clients.
- B5 (= RV-5): a positive INFO line `[SIWA] stored` (no ids) after a successful upsert, in the 2.7 templates and in R6/R18.
- B6 (= RV-6, orchestrator's choice taken): 044 carries an explicit `GRANT SELECT, INSERT, UPDATE ON public.apple_siwa_tokens TO service_role`; M4/M5 become "exactly one GRANT, to service_role"; the owner postcheck checks `has_table_privilege` for service_role (INSERT, SELECT true) and anon (SELECT false).
- B7 (= RV-7): `tests/test_behavior_dimension_translation.py` and a "reads CLAUDE.md" rule join comm_set.py; gate 3 names `tests/test_sqlfluff_config.py::test_sqlfluff_lints_the_migration_corpus_clean` and `tests/test_domain_s76.py`; new app/ code names the bundle id only as the exact `com.qaren.app`.
- B8 (= RV-8, answers Q8): no requirements edit in this unit; R29 (`jwt.algorithms.has_crypto` is True and both pins present) added; the `pyjwt[crypto]` declaration + recompiled lock is a follow-up unit. Q8b: add `APPLE_SIWA_PRIVATE_KEY` to `tests/_env_safety.CREDENTIALS_UNSET`.
- B9 (= RV-9, answers Q3): the key accepts a PEM with real newlines, a PEM with literal `\n`, or base64 of the .p8; the base64 branch strips all whitespace before `b64decode(validate=True)`; the owner step gives the PowerShell `[Convert]::ToBase64String([IO.File]::ReadAllBytes(...))` form.
- B10 (= RV-10): the test file assigns no literal to a name containing token, secret or key unless built at run time or a low-entropy word; RED reports a local gitleaks run or its absence.
- B11 (= RV-11): the three stated limits are added (the unflagged OpenAPI property; rollback to OFF while rows exist skips the revoke and the FK cascade drops the rows; dev clients with another bundle id get exchange status=400).
- B12 (= RV-12): the deletion-time re-authentication path (the audit's P1 design: a fresh authorization code in the DELETE body when no row exists) is follow-up B3-C after approval, not this unit. The texts never claim revocation until this ships and is flipped.
- B13 (answers Q1-Q12 as the review proposes): Q1 A (cascade untouched; FK to `auth.users` ON DELETE CASCADE; a KEEP entry in the 043 fence; the 12-table test renamed to 13); Q2 `auth.users`; Q4 `APPLE_SIWA_CLIENT_ID` required, no default; Q5 keep the sub check; Q6 read before the cascade, revoke after the cascade and before the auth delete, no sleep between the two attempts; Q9 amend the apple manifest row and the R22 fixture in this unit, no policy text here; Q11 the before-validator mapping any non-str `authorization_code` to None; Q12 drop the JWT `typ` header.
- B14 (= the review's MISSING rows): adopt R25, R26, R27, R28, the R6 and R18 amendments, R29, the R3 params, the R13 param, and the RED admin fake for R12-R17 (serves `data=[{'refresh_token': T}]` or `[]`, appends `read_token`).

## Standing for both RED agents

- The RED file(s) are the contract: every RED row fails at base on an AssertionError with the stated reason (never an import or setup error), every PIN row is green at base; a prototype makes all green; the mutation table is run on the prototype with byte copy / restore / sha check per mutant; every pytest run through the bounded runner, every jest run by path under `timeout -k 15`, one process at a time, chunks of 25.
- Report the counts (RED / PIN / mutants killed) with the `[pyt]` or `[jest]` lines, the sha256 of every file written, and `git status --short` of the worktree at the end (only the new test files, and for B3-B the new fixture, may be untracked; nothing else dirty).
