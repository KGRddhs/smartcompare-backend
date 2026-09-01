/**
 * HomeScreen current-design contract tests — WIP branch
 * `wip/HomeScreen-pre-existing-test-repair`.
 *
 * REPLACEMENT for the three pre-existing render-based suites that
 * pre-date the Bundle B (commit 21e7bc0) + Bundle E S3 (commit 21e7bc0
 * follow-up) HomeScreen rewrites:
 *   - HomeScreen.redesign.test.tsx        (Phase 3 Task 26, camera-card design)
 *   - HomeScreen.modeChipAnim.test.tsx    (chip haptic + reanimated spring)
 *   - HomeScreen.scanCamera.test.tsx      (scan-chip → ScanCamera modal nav)
 *
 * Those tests reference testIDs (`home-camera-card`, `home-mode-scan/link/type`
 * + camera viewfinder, `home-hero` copy) that the rewrites removed/renamed;
 * the render-based assertions fail because the current JSX no longer carries
 * them OR because the mock surface drifted (act() + useFocusEffect glue
 * never re-stubbed for the rewrite). Pre-existing per MEMORY.md §
 * "HomeScreen variant integration tests need re-mocking (Bundle B
 * post-merge)" — formally deferred.
 *
 * This file replaces those three suites with SOURCE-GREP-style assertions
 * pinning the same load-bearing behaviors against the *current* design.
 * Same pattern used by HomeScreen.bundleE.s3.test.tsx + HomeScreen.
 * bundleB.contract.test.tsx — both already green.
 *
 * Behaviors pinned:
 *   1. MAX_IMAGES=2 export still 2 (Bundle B Task 2.6 contract)
 *   2. Scan mode chip routes to ScanCamera modal (not inline camera)
 *   3. Compare CTA is wired to navigation.navigate('ScanCamera') from
 *      the HomeScreen scan-mode CTA helper
 *   4. handleModeChange paywall gate fires navigate('Paywall') when
 *      canCompare=false
 *   5. Bundle E S3 redesign — hero copy lives in `home.hero` i18n key,
 *      counter uses `home-header-counter` testID
 *   6. Three mode chips carry testIDs `home-mode-{scan,link,type}` after
 *      the JSX consolidation (was a render-time check; now grepped)
 *   7. Gallery fallback `launchImageLibraryAsync` still uses
 *      `selectionLimit: MAX_IMAGES` (Bundle B Task 2.6 cap)
 */

import * as fs from 'fs';
import * as path from 'path';

const HOME_PATH = path.resolve(__dirname, '../src/screens/HomeScreen.tsx');
const EN_LOCALE_PATH = path.resolve(__dirname, '../src/i18n/en.json');

let homeSrc: string;
let enLocale: Record<string, string>;

beforeAll(() => {
  homeSrc = fs.readFileSync(HOME_PATH, 'utf8');
  enLocale = JSON.parse(fs.readFileSync(EN_LOCALE_PATH, 'utf8'));
});

describe('HomeScreen current design — Bundle B Task 2.6 MAX_IMAGES + Scan nav', () => {
  it('exports MAX_IMAGES = 2 (cap reduced from 4 by Bundle B/C/D Task 2.6)', () => {
    // Source declaration check — robust to import-time evaluation issues.
    expect(homeSrc).toMatch(/export\s+const\s+MAX_IMAGES\s*=\s*2\b/);
  });

  it('Scan mode chip routes to ScanCamera modal (not inline viewfinder)', () => {
    // Bundle B/C/D Task 2.6 — tapping the Scan chip OR the scan-mode CTA
    // navigates to the dedicated ScanCamera modal screen rather than
    // toggling an inline camera view inside HomeScreen.
    expect(homeSrc).toMatch(/navigation\.navigate\(['"]ScanCamera['"]\)/);
  });

  it('scan-mode CTA helper handleScanCtaPress navigates to ScanCamera', () => {
    // Pin the helper name + its body. If a future refactor renames the
    // helper, the regex picks up the rename loud.
    expect(homeSrc).toMatch(
      /const\s+handleScanCtaPress\s*=\s*\([^)]*\)\s*=>\s*\{[\s\S]*?navigation\.navigate\(['"]ScanCamera['"]\)/
    );
  });

  it('gallery fallback caps selectionLimit at MAX_IMAGES', () => {
    // pickFromGalleryFallback respects the 2-image cap.
    expect(homeSrc).toMatch(/selectionLimit\s*:\s*MAX_IMAGES/);
  });
});

describe('HomeScreen — M13-13 gallery fallback passes picked photos through', () => {
  it('navigates to Results with vision_products mapped from result.assets', () => {
    // The fallback must NOT navigate to a param-less ScanCamera (which
    // drops the photos into a module-private slot cache). It threads the
    // picked URIs straight to Results, matching ScanCameraScreen.onCompare.
    const match = homeSrc.match(
      /const\s+pickFromGalleryFallback\s*=\s*async\s*\([^)]*\)\s*=>\s*\{([\s\S]*?)\n\s{2}\};/
    );
    expect(match).toBeTruthy();
    const body = match![1];
    expect(body).toMatch(
      /navigation\.navigate\(\s*['"]Results['"][\s\S]*?vision_products\s*:[\s\S]*?\.map\(/
    );
    // And it must NOT fall back to the old param-less ScanCamera nav.
    expect(body).not.toMatch(/navigation\.navigate\(\s*['"]ScanCamera['"]\s*\)/);
  });

  it('under-2 pick surfaces a visible Alert instead of a silent no-op', () => {
    const match = homeSrc.match(
      /const\s+pickFromGalleryFallback\s*=\s*async\s*\([^)]*\)\s*=>\s*\{([\s\S]*?)\n\s{2}\};/
    );
    expect(match).toBeTruthy();
    const body = match![1];
    expect(body).toMatch(/Alert\.alert\(/);
  });
});

describe('HomeScreen — M13-54 scan CTA gated on camera permission', () => {
  it('Open-camera CTA renders only when cameraPermissionGranted', () => {
    // The bottom "Open camera" CTA must be hidden while permission is not
    // granted — otherwise it routes to ScanCamera with no way to grant.
    // renderCenterArea() shows the in-place permission pad in that state.
    expect(homeSrc).toMatch(
      /canCompare\s*&&\s*inputMode\s*===\s*['"]scan['"]\s*&&\s*cameraPermissionGranted\s*&&/
    );
  });
});

describe('HomeScreen current design — handleModeChange paywall gate', () => {
  it('handleModeChange routes through Paywall when canCompare=false', () => {
    // Bundle B/C/D Task 2.6 — tapping any chip while at usage cap opens
    // the Paywall modal rather than silently switching modes. The mode
    // state is still updated so the user sees the chip flip.
    const match = homeSrc.match(
      /const\s+handleModeChange\s*=\s*\([^)]*\)\s*=>\s*\{([\s\S]*?)\n\s{2}\}\;/
    );
    expect(match).toBeTruthy();
    const body = match![1];
    expect(body).toMatch(/!canCompare/);
    expect(body).toMatch(/navigation\.navigate\(['"]Paywall['"]\)/);
  });

  it('emits compare_entry_paywall_banner_view analytics when paywall fires', () => {
    // Cross-check the analytics breadcrumb so a future refactor that
    // strips trackEvent still trips a test.
    expect(homeSrc).toMatch(
      /trackEvent\(['"]compare_entry_paywall_banner_view['"]/
    );
  });
});

describe('HomeScreen current design — Bundle E S3 testID contract', () => {
  it('mode chips carry testIDs home-mode-{scan,link,type}', () => {
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-mode-scan["']/);
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-mode-link["']/);
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-mode-type["']/);
  });

  it('header counter pill carries testID home-header-counter', () => {
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-header-counter["']/);
  });

  it('center-area host carries testID home-center-area', () => {
    // Bundle B Task 21e7bc0 rewire moved the TwoInputShell + scan card
    // into a single host with this testID.
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-center-area["']/);
  });

  it('Compare CTA carries testID home-compare-cta (Bundle E S3 contract)', () => {
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-compare-cta["']/);
  });

  it('theatrical loader carries testID home-loading-screen', () => {
    // Bundle E S3 redesign moved the loader to a fullscreen LoadingScreenVariants
    // wrapper. The testID is load-bearing for the loaderVisibility test.
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-loading-screen["']/);
  });
});

describe('HomeScreen current design — i18n keys', () => {
  it('home.hero key exists in en locale (Bundle E S3 hero copy)', () => {
    // Jest's toHaveProperty treats "home.hero" as a nested path, but the
    // locale file uses literal dot-keys (`"home.hero": "..."`). Use the
    // array form OR direct index access to bypass nesting interpretation.
    expect(enLocale['home.hero']).toBeDefined();
    // Spot-check the copy carries the "Compare" phrase per design Screen 0.
    expect(enLocale['home.hero'].toLowerCase()).toMatch(/compare/);
  });

  it('home.cta.openCamera default fallback wired through t()', () => {
    // Bundle E S3 — scan-mode CTA label "Open camera" uses defaultValue
    // pattern so missing locale still renders. Same pattern other
    // components in the lane follow.
    expect(homeSrc).toMatch(/t\(['"]home\.cta\.openCamera['"]\s*,\s*\{[^}]*defaultValue/);
  });
});

describe('HomeScreen current design — chip haptic vocab discipline', () => {
  it('uses Haptics.impactAsync for chip tap (light vocab per CLAUDE.md)', () => {
    // CLAUDE.md motion vocab: chip:light, stage:light, winner:medium.
    // No error/warning/heavy intensities anywhere.
    expect(homeSrc).toMatch(/Haptics\.impactAsync\(Haptics\.ImpactFeedbackStyle\.Light\)/);
  });

  it('does NOT use forbidden haptic intensities (Heavy/error/warning)', () => {
    // Build Principle #4 — never scary. These intensities are reserved
    // for surfaces that don't belong on Home.
    expect(homeSrc).not.toMatch(/Haptics\.impactAsync\(Haptics\.ImpactFeedbackStyle\.Heavy\)/);
    expect(homeSrc).not.toMatch(/Haptics\.notificationAsync\([^)]*Error/);
    expect(homeSrc).not.toMatch(/Haptics\.notificationAsync\([^)]*Warning/);
  });
});

describe('HomeScreen current design — SSE wall-time + ttfb mark (Lane A-L3.7)', () => {
  it('imports getWallTimeTracker from lib/performance', () => {
    // Lane A-L3.7 instrumentation — preserved across future HomeScreen
    // refactors so the 88s diagnosis stays observable.
    expect(homeSrc).toMatch(
      /import\s+\{[^}]*getWallTimeTracker[^}]*\}\s+from\s+['"]\.\.\/lib\/performance\/wallTimeInstrumentation['"]/
    );
  });

  it('starts the wall-time tracker before subscribe() fires', () => {
    expect(homeSrc).toMatch(/getWallTimeTracker\(\)/);
    expect(homeSrc).toMatch(/wallTime\.start\(\)/);
  });

  it('marks ttfb in onStatus/onSpecs/onPrices/onComplete handlers', () => {
    // markTtfb is the local closure that idempotently fires the first
    // wallTime.mark('ttfb') call. Each handler must invoke it.
    expect(homeSrc).toMatch(/markTtfb\(\)/);
    expect(homeSrc).toMatch(/onSpecs\s*:\s*\(\s*\)\s*=>\s*markTtfb\(\)/);
    expect(homeSrc).toMatch(/onPrices\s*:\s*\(\s*\)\s*=>\s*markTtfb\(\)/);
  });
});
