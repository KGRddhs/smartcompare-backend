## Context
U4b (PR #279) sets the four launcher files `app.json` points at. Ruling RQ5 left the optional native icon fields unset. None is a launch blocker.

## Items
- `ios.icon` dark and tinted variants (iOS 18). Today iOS derives them from the single light icon.
- The `expo-notifications` plugin `icon` (Android notification glyph). Today Android uses the default.
- `android.adaptiveIcon.monochromeImage` (Android 13 themed icons).
- Android legacy splash sizing: with the root `splash` key the prebuild scales `splash-icon.png` with `resizeMode: contain`; on a 411x891 dp phone the mark is wider than on iOS (measured by the U4b App Review adversary, spec correction 6). Decide whether to add the `expo-splash-screen` plugin with an explicit `imageWidth`.

## Notes
- Every item is a NATIVE change and needs a new build.
- Any new art must come from `scripts/render_myez_icons.py` so the manifest stays the single record.

Severity: low. Source: U4b spec ruling RQ5.
