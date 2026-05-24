# Bundle D — App Store Screenshot Capture Runbook

**Task:** 2.N.1c — for Ahmed to run after Task 2.N.1 EAS preview build is installed
**Author:** native-ops
**Date drafted:** 2026-05-23
**Prerequisites:**
- Task 2.N.1 EAS preview build complete (an `.ipa` installable via TestFlight OR an iOS Simulator build)
- Xcode installed (Xcode 15+ recommended) — comes with iOS Simulator + the simulator device shapes Apple's App Store Connect expects
- Optionally `xcrun simctl` CLI (ships with Xcode Command Line Tools)

## Why this exists

App Store Connect requires uploaded screenshots in **specific Apple-defined display sizes** before TestFlight external testing OR App Store submission. Apple will reject the binary if the screenshot set is incomplete or wrong-sized.

Since Qaren has `ios.supportsTablet: true` (`SmartCompareApp/app.json:18`), **iPad Pro 12.9" screenshots are MANDATORY** alongside the iPhone set.

This runbook gives Ahmed step-by-step capture for the 2 required device sizes + the 6 recommended app moments.

## Required device sizes (Apple App Store Connect, 2026)

| Display class | Resolution (portrait, px) | Apple simulator device | Required? |
|---|---|---|---|
| 6.7" iPhone | **1290 × 2796** | iPhone 15 Pro Max / 16 Pro Max | ✅ MANDATORY |
| iPad Pro 12.9" (6th gen) | **2048 × 2732** | iPad Pro 12.9-inch (6th generation) | ✅ MANDATORY (because `ios.supportsTablet: true`) |
| 6.5" iPhone (legacy fallback) | 1242 × 2688 | iPhone 11 Pro Max | Optional — Apple accepts 6.7" alone |
| 5.5" iPhone (legacy) | 1242 × 2208 | iPhone 8 Plus | DROPPED 2024 — skip |

Minimum 1 screenshot per required size, maximum 10. **Recommend exactly 6** for both sizes per the ASC submission checklist (`docs/plans/bundle-d-asc-submission-checklist.md`).

## The 6 recommended captures (in order)

These mirror the user journey from first-open → core flow:

| # | Screen | Purpose | What to do |
|---|---|---|---|
| 1 | **Onboarding Step 1** (Cal-AI-Lite intro hero) | "What is Qaren?" — sets the emerald/black brand tone | Fresh install or after `expo-secure-store` wipe; first onboarding screen renders |
| 2 | **Onboarding Step 14** (theatrical loading) | Shows the cohort-personalization moment (3.2s minimum per design § 4) | Step through onboarding to Step 14; capture during the 3.2s window |
| 3 | **HomeScreen with TwoInputShell** (Bundle B redesign) | Core landing screen — paste-anywhere comparison input | Land on HomeScreen post-onboarding; show TwoInputShell empty + the 2-numeral-circle "vs" pill |
| 4 | **Results / Winner Reveal** | The decision moment — Qaren's verdict on a real comparison | Run a comparison (e.g. "iPhone 15 vs Galaxy S24"), wait for the stream-complete event, capture the verdict + winner badge |
| 5 | **Cohort badge moment** (below verdict) | Differentiator vs ChatGPT — "personalized to people like you" | Same screen as #4, scroll to expose the CohortBadge inline; OR scroll further to show cohort-personalization breakdown |
| 6 | **History tab populated** | Shows persistence + multi-comparison value | After running 3-5 comparisons, navigate to History tab; capture the date-grouped FlatList |

### Optional 7th — if Ahmed wants more

- **Profile tab with toggles** — surfaces the "no scary copy" toggles + premium upgrade path
- **Camera capture in action** — shows the camera-first input modality

## Capture step-by-step (per device size)

### Setup (one-time)

1. Install Xcode from the App Store (~10 GB download).
2. Open Xcode → Preferences → Components → ensure "iOS 17.0 Simulator" (or latest) is installed.
3. Open Simulator app: `open -a Simulator` from terminal, OR Xcode → Open Developer Tool → Simulator.
4. In Simulator menu bar: **File → New Simulator** if the device you need isn't already created. Pick "iPhone 16 Pro Max" (or 15 Pro Max) for 6.7" + "iPad Pro 12.9-inch (6th generation)" for iPad.
5. Install Qaren on the Simulator. Two options:
   - **Path A (EAS Simulator build):** if Ahmed ran `eas build --profile preview --platform ios --simulator` (note the `--simulator` flag), the resulting `.tar.gz` extracts to a `.app` bundle. Drag the `.app` onto the running Simulator window. Faster turnaround than TestFlight.
   - **Path B (TestFlight on physical device + screen mirroring):** TestFlight does NOT install on Simulator. If only the standard preview build (`.ipa`) is available, use a real device + screen-record + crop. NOT recommended — wrong pixel dimensions for App Store unless very carefully cropped.
   - **Recommended:** run Path A. Ask the EAS preview build to be rebuilt with `--simulator` if needed.

### Per-capture flow

For each of the 6 captures × 2 device sizes (= 12 screenshots total):

1. Switch Simulator to the target device (Simulator → File → Switch Device → pick iPhone 16 Pro Max OR iPad Pro 12.9").
2. Cold-start Qaren on the Simulator (close + reopen if mid-flow).
3. Navigate to the target screen (Onboarding Step 1, Step 14, HomeScreen, etc.).
4. Capture:
   - **Keyboard shortcut:** `Cmd + S` in Simulator. Or:
   - **CLI:** `xcrun simctl io booted screenshot ~/Desktop/qaren-1-onboarding.png`
5. Repeat for next capture.

### Naming convention

To keep ASC uploads tidy:

```
qaren-iphone67-1-onboarding.png
qaren-iphone67-2-loading.png
qaren-iphone67-3-homescreen.png
qaren-iphone67-4-winner.png
qaren-iphone67-5-cohort.png
qaren-iphone67-6-history.png
qaren-ipad-1-onboarding.png
... (same 6 names with ipad prefix)
```

### Validate dimensions before uploading

Apple rejects any screenshot that's not exactly the right pixel dimensions. Verify each file:

```bash
# macOS
sips -g pixelWidth -g pixelHeight ~/Desktop/qaren-iphone67-1-onboarding.png
# Expect: pixelWidth: 1290 / pixelHeight: 2796 for iPhone 6.7"

sips -g pixelWidth -g pixelHeight ~/Desktop/qaren-ipad-1-onboarding.png
# Expect: pixelWidth: 2048 / pixelHeight: 2732 for iPad Pro 12.9"
```

**If a capture is the wrong size** (common gotcha — Simulator's "View → Scale → Pixel-Accurate" must be ON or screenshots get downscaled):
1. In Simulator: View menu → Scale → Pixel-Accurate (Cmd-1 ≠ pixel-accurate; Cmd-= cycles)
2. Re-capture.

### Avoid the status bar gotcha

iOS Simulator screenshots include the simulator's status bar by default (signal bars, time, battery). Apple **rejects** screenshots with the simulator's status bar content because it's inauthentic.

Two fixes:
- **Best:** `xcrun simctl status_bar booted override --time "9:41" --batteryState charged --batteryLevel 100 --cellularBars 4 --wifiBars 3` BEFORE capturing. Restores the Apple-standard 9:41 demo state.
- **Acceptable:** capture as-is, then crop the status bar off using Preview.app. Don't change dimensions — just letterbox if needed.

## Upload to App Store Connect

1. ASC web → App → "App Store" tab → version "1.0.0" → **iOS app screenshots**.
2. Click "+ iPhone 6.7"" — drag your 6 `qaren-iphone67-*.png` files in order 1→6.
3. Click "+ iPad Pro 12.9"" — drag the 6 `qaren-ipad-*.png` files.
4. Save. ASC verifies dimensions immediately + flags any rejects.

**Editable post-submission:** screenshots can be swapped via ASC web UI any time without rebuilding the binary. So if Ahmed wants to iterate on shot quality post-launch, no problem.

## Recommended polish (optional, NOT blocking)

- **App Preview video** (15-30s, 1080×1920 portrait): adds 5-30% conversion lift per Apple internal data. Defer to v1.1.
- **Localized AR screenshots:** Apple supports per-locale screenshots. With AR app + RTL layout, capturing the AR variant in the AR simulator locale (`xcrun simctl device locale ar_AE`) would give us better representation in GCC App Store storefronts. Defer to v1.1 polish pass.

## Troubleshooting

- **Simulator shows "Untrusted Developer" banner:** for screenshots, dismiss via Settings → General → VPN & Device Management → trust the EAS preview profile. Then re-launch the app.
- **App crashes on first launch:** check `~/Library/Logs/CrashReporter/` or `xcrun simctl spawn booted log stream --predicate 'subsystem == "host.exp.exponent"'` — typical cause is a missing `expo-secure-store` migration or a Hermes init crash, both pre-Phase-2 issues that won't affect a Phase-2 EAS build.
- **Status bar override didn't apply:** restart Simulator after running the `xcrun simctl status_bar` command. Override is per-boot.
- **Wrong dimensions despite Pixel-Accurate ON:** older macOS may downscale screenshots if external display scaling is on. Run captures with Simulator on the laptop's built-in display only.

## When can Ahmed do this?

Trigger: after Task 2.N.1 EAS preview build is installed on a physical device OR Simulator. Estimated runtime: 30-45 min for the full 12-screenshot capture set if everything works first try; 1-2 hours including dimension fixes + status-bar overrides.

ASC upload itself: 5-10 min once files are correctly sized.

## Why this is in scope

Per ASC submission checklist (`docs/plans/bundle-d-asc-submission-checklist.md` § "Screenshots"), Apple's required screenshots are part of the metadata package alongside Privacy Nutrition Labels, App Name, Description, Keywords. Without complete screenshots in the right dimensions, the binary cannot move from "Processing" to "Ready to Submit" in TestFlight, and the App Store record cannot be created at all.

For TestFlight internal-only testing (Phase 3 Task 3.N.2), screenshots are NOT strictly required — internal testers redeem via the TestFlight app + don't see ASC store listings. But Apple does require screenshots before promoting from internal → external testing OR before App Store submission. So Ahmed can defer this to Phase 4 if internal-only testing is enough for v1; otherwise capture during Phase 3.

---

## Cheat sheet — fastest path

```bash
# Setup once
open -a Simulator
xcrun simctl boot "iPhone 16 Pro Max"
xcrun simctl status_bar booted override --time "9:41" --batteryState charged --batteryLevel 100 --cellularBars 4 --wifiBars 3

# Install Qaren (from EAS Simulator build .app bundle)
xcrun simctl install booted /path/to/Qaren.app

# Open app
xcrun simctl launch booted com.qaren.app

# Capture each scene (after navigating to the right screen)
xcrun simctl io booted screenshot ~/Desktop/qaren-iphone67-1-onboarding.png
xcrun simctl io booted screenshot ~/Desktop/qaren-iphone67-2-loading.png
xcrun simctl io booted screenshot ~/Desktop/qaren-iphone67-3-homescreen.png
xcrun simctl io booted screenshot ~/Desktop/qaren-iphone67-4-winner.png
xcrun simctl io booted screenshot ~/Desktop/qaren-iphone67-5-cohort.png
xcrun simctl io booted screenshot ~/Desktop/qaren-iphone67-6-history.png

# Switch device, repeat
xcrun simctl shutdown booted
xcrun simctl boot "iPad Pro (12.9-inch) (6th generation)"
# ... repeat status_bar override + install + capture for the 6 iPad shots
```

Validate every file:

```bash
for f in ~/Desktop/qaren-*.png; do
  sips -g pixelWidth -g pixelHeight "$f"
done
```

Done. Drag the 12 PNGs into ASC.
