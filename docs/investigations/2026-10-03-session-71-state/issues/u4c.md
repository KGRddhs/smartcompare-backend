## Context
U4b (PR #279) ships the native launcher art from the MYEZ master. The in-app glyph is still the old Qaren Q-ring drawn by `SmartCompareApp/src/components/QarenLogo.tsx` (react-native-svg). It renders on the JS splash, Home, Profile, History, onboarding Step 1 and inside `LoadingRings`. A reviewer sees the new icon on the home screen and the old mark the moment the app opens.

## Scope (unit U4c, OTA-capable, before the review build)
- Replace the Q-ring with the MYEZ mark at every render site. Keep the `QarenLogo` identifier and file path.
- Source the mark from the U4b renderer (`scripts/render_myez_icons.py`): add `@1x/@2x/@3x` outputs and extend the manifest.
- Approved design calls (Ahmed, 2026-10-03): drop the app-name text beside the mark; the JS splash mark starts at the launch-screen position and at full opacity (animate only the text); ONE `jest -u` on the `LoadingRings` snapshot file, with the diff reviewed.

## Acceptance
- No render site draws the Q-ring; the mark matches the launcher art over a white background.
- FULL jest green; the only `.snap` change is the authorised `LoadingRings` file.
- No `app.json`, `eas.json` or dependency change (the unit must stay OTA-capable).

Severity: medium (launch polish, App Review consistency). Source: U4b spec ruling RQ4.
