# The third over-the-air update (runtime 1.0.0): the bundle rule and the proven publish steps (S95, 2026-11-14)

Written by the S95 main lane for the relay, modelled on S93_AFTER_MERGE_RECIPES.md and after-merge-378/SECOND_OTA_PUBLISH.md. The merge sha `<M>` (the full sha) comes by message when the merge exists; it is the sha to publish from. The unit is PR #405 (https://github.com/KGRddhs/smartcompare-backend/pull/405), head 82172383d8c68563ee5bbb9997d61168a27b93bc, a draft until the merge word. Nothing here has been run by this lane.

## The bundle rule

- The bundle = the client of the second update (group d84dac11, main ea47cbfb) PLUS the two client files of S95-LOGO:
  1. `SmartCompareApp/src/components/results/ResultsContent.tsx` (the RevealBurst mount, its import and its slot style removed; comments)
  2. `SmartCompareApp/src/screens/ResultsScreen.tsx` (one unused import removed)
- Measure it: `git diff --name-only ea47cbfb <M> -- SmartCompareApp`, with the paths under `SmartCompareApp/__tests__/` removed, must list EXACTLY those two files. (Between ea47cbfb and 731bcddf it lists nothing: no client file changed after the second update.) If it lists any other file, for example a client change merged by the S95-FIX lane before this publish, STOP: that file would ride the update too; ask the lane that owns it.
- `git diff --stat ea47cbfb <M> -- SmartCompareApp/package.json SmartCompareApp/package-lock.json SmartCompareApp/app.json` must print nothing (no dependency or native change, so the 1.0.0 binary runs the bundle).
- `git show <M>:SmartCompareApp/app.json | grep -n '"version"'` must print `"version": "1.0.0"`. eas update takes the runtime from the checkout's app.json (runtimeVersion policy appVersion); once main says 1.0.1, a 1.0.0 update is published only from a release/1.0.x checkout.
- What the update changes on a phone: the result page no longer draws the winner-reveal celebration, so no MYEZ badge sits over the score bars. Nothing else: no copy, no consent, no request, no server change. The App Privacy label is untouched (no data flow changes).

## The publish steps (the proven form of the second update; eas-cli 18.8.1, not upgraded)

Worktree: `C:/Users/SynAckITPC/Documents/AI/sc-ota-main/SmartCompareApp` (its node_modules is a real install, `npm ls` clean on this lock; no other lane's junction points at it: the S95 worktree's junction points at the clone).

Preflight, in order:
1. `railway deployment list -s web -e production --json` (names-only filter): the top row SUCCESS at commit `<M>` (the merge redeploys the backend; this unit changes no backend byte). `curl -s https://web-production-58776.up.railway.app/health`: `"status":"healthy"`.
2. `git -C C:/Users/SynAckITPC/Documents/AI/smartcompare fetch origin` and `git -C C:/Users/SynAckITPC/Documents/AI/smartcompare rev-parse origin/main` = `<M>`.
3. The three bundle-rule checks above.
4. In sc-ota-main: `git status --porcelain` shows only untracked dist folders (no tracked change); `mv dist dist-ota2-d84dac11` (keeps the second update's maps beside `dist-ota1-08de6433`); `git switch --detach <M>`; `git rev-parse HEAD` = `<M>`.
5. `git show HEAD:SmartCompareApp/app.json | grep -n '"version"'` prints `5:    "version": "1.0.0",`.
6. `npm ls --depth=0`: exit 0, no invalid / missing / extraneous / UNMET line (expo 54.0.37, expo-updates 29.0.20, react-native 0.81.5). `npx expo config --type public --json`: version 1.0.0, runtimeVersion {policy: appVersion}, updates.url https://u.expo.dev/387a4fcb-76f6-4857-a2fb-39482ca4bd40.
7. `CI=1 npx eas update:list --branch production --non-interactive --json` (before): the newest group is d84dac11-bc20-4cd2-a89e-1cd723f2c514, runtime 1.0.0, "main ea47cbfb".

Publish, once, in the foreground:
`cd C:/Users/SynAckITPC/Documents/AI/sc-ota-main/SmartCompareApp && CI=1 npx eas update --channel production --message "main <first 8 of M>" --non-interactive`
(The second update took 123 s: iOS and Android bundled, 2 bundles uploaded, "Uploading assets skipped - no new assets found".)

Confirm:
- `CI=1 npx eas update:list --branch production --non-interactive --json`: the new group is the newest, runtime 1.0.0, android + ios, message "main <first 8 of M>", isRollBackToEmbedded false.
- `CI=1 npx eas update:view <new group id> --json`: gitCommitHash `<M>` on both platforms.
- `CI=1 npx eas channel:view production --non-interactive`: the latest group is the new one, runtime 1.0.0.
- Keep a masked log (progress lines and the account name removed; zero token or secret matches), as eas_update_2026-11-12.log.

## The owner's proof on his phone

1. Open MYEZ, swipe it away, open it again. The first open only DOWNLOADS the update; the second cold start runs it (expo-updates defaults: app.json sets only updates.url).
2. Compare a pair with a clear winner and scroll the result page past the score bars: no MYEZ badge over them. Once in English and once in Arabic if he can.
3. In the same sitting, the consent proof of S95_FIRST_REPORT.md: sign in to the OLD account, one compare: the version 3 sheet naming Anthropic and OpenAI must appear; Agree; the result carries AI text.
For the relay, read-only: Sentry `comparison_wall_time` events from his phone after step 1 carry the new iOS update id in `contexts.ota_updates.update_id`.

## Rollback (read from eas-cli 18.8.1 `update:republish`; never run)

`CI=1 npx eas update:republish --group d84dac11-bc20-4cd2-a89e-1cd723f2c514 --message "rollback to main ea47cbfb" --non-interactive` republishes the second update as the newest on its branch, production (phones take it from their second cold start). NEVER `eas update:roll-back-to-embedded` for this fleet: the embedded 1.0.0 (3) bundle predates the request-context headers and consent version 3, so every phone would get a result without AI text.

## What the main lane does not do

No flag, no variable, no deploy, no update, no store label: those are the relay's and the owner's.
