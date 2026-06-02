/**
 * Bundle E S3 hotfix L1 — dedupe/loading/MonthStrip red-green tests.
 *
 * Three contracts:
 *   1. HomeScreen.tsx renders the scan-mode CTA (home-compare-cta) ONLY
 *      when inputMode==='scan'. In link/type modes the CTA is owned by
 *      TwoInputShell — HomeScreen must not double-render a sibling CTA.
 *   2. LoadingScreenVariants is the loading-state surface on HomeScreen.
 *      The prior toast/loadingOverlay pattern is gone (the scary "Finding
 *      products..." mid-Home was replaced with the theatrical loader).
 *   3. ProfileScreen renders MonthStrip in the JSX-canonical slot per
 *      docs/claude-design-handoff/ui_kits/mobile/ProfileScreen.jsx (Recent
 *      Decisions → Priorities → MonthStrip → FlatSettings).
 */

import * as fs from 'fs';
import * as path from 'path';

const HOME_SRC = fs.readFileSync(
  path.resolve(__dirname, '../src/screens/HomeScreen.tsx'),
  'utf8',
);
const PROFILE_SRC = fs.readFileSync(
  path.resolve(__dirname, '../src/screens/ProfileScreen.tsx'),
  'utf8',
);
const TWOINPUT_SRC = fs.readFileSync(
  path.resolve(__dirname, '../src/components/TwoInputShell.tsx'),
  'utf8',
);
const PROFILE_JSX_SRC = fs.readFileSync(
  path.resolve(
    __dirname,
    '../../docs/claude-design-handoff/ui_kits/mobile/ProfileScreen.jsx',
  ),
  'utf8',
);

describe('HomeScreen — Compare CTA is scan-mode-only (no double button)', () => {
  it('home-compare-cta is gated on inputMode === scan', () => {
    // Source-level: the only TouchableOpacity using home-compare-cta sits
    // inside a conditional that checks inputMode === 'scan'.
    expect(HOME_SRC).toMatch(
      /inputMode\s*===\s*['"]scan['"][^}]*&&[\s\S]{0,400}?testID\s*=\s*["']home-compare-cta["']/,
    );
  });

  it('there is exactly ONE testID="home-compare-cta" declaration in HomeScreen.tsx', () => {
    const matches = HOME_SRC.match(/testID\s*=\s*["']home-compare-cta["']/g);
    expect(matches).not.toBeNull();
    expect(matches!.length).toBe(1);
  });

  it('the prior loadingOverlay/loadingText toast styles are gone', () => {
    expect(HOME_SRC).not.toMatch(/loadingOverlay\s*:\s*\{/);
    expect(HOME_SRC).not.toMatch(/loadingText\s*:\s*\{/);
  });

  it('TwoInputShell still ships its own internal CTA (single source of truth in non-scan modes)', () => {
    expect(TWOINPUT_SRC).toMatch(/testID=\{`\$\{testID\}-cta`\}/);
  });

  it('HomeScreen does NOT render a CTA outside the scan branch (no orphan home-compare-cta sibling)', () => {
    // Defense in depth: the legacy wide-mode `ctaEnabled` predicate is
    // gone AND no per-render flag (e.g. scanCtaEnabled) recreates the
    // dead-code surface. The single source of truth for whether the
    // scan CTA renders is the JSX gate `inputMode === 'scan' &&`.
    expect(HOME_SRC).not.toMatch(/const\s+ctaEnabled\s*=\s*\(/);
    expect(HOME_SRC).not.toMatch(/\bscanCtaEnabled\b/);
  });
});

describe('HomeScreen — LoadingScreenVariants replaces the scary mini-toast', () => {
  it('imports LoadingScreenVariants from the screen-level loader file', () => {
    expect(HOME_SRC).toMatch(
      /import\s*\{\s*LoadingScreenVariants\s*\}\s*from\s*['"]\.\/LoadingScreenVariants['"]/,
    );
  });

  it('renders LoadingScreenVariants with mode="comparison" when loading', () => {
    // Mode "comparison" is the right semantic — no theatrical 3.2s floor,
    // since HomeScreen already enforces 1.2s via navigateToResultsWithFloor.
    expect(HOME_SRC).toMatch(/<LoadingScreenVariants[\s\S]*?mode=["']comparison["']/);
  });

  it('full-screen container uses absoluteFillObject + high zIndex', () => {
    expect(HOME_SRC).toMatch(/loadingFullscreen\s*:\s*\{[\s\S]*?StyleSheet\.absoluteFillObject/);
    expect(HOME_SRC).toMatch(/loadingFullscreen\s*:\s*\{[\s\S]*?zIndex\s*:\s*100/);
  });

  it('navigateToResultsWithFloor still gates the navigation (1.2s min-display floor preserved)', () => {
    expect(HOME_SRC).toMatch(/navigateToResultsWithFloor/);
    expect(HOME_SRC).toMatch(/MIN_LOADING_MS\s*=\s*1200/);
  });

  it('contains no scary "Finding products..." raw string at the toast position', () => {
    // The string still appears via i18n key results.loading.finding but
    // there must be NO `<ActivityIndicator>` overlay in the source.
    expect(HOME_SRC).not.toMatch(/ActivityIndicator/);
  });
});

describe('ProfileScreen — MonthStrip JSX parity', () => {
  it('JSX spec declares a MonthStrip section (3 tiles)', () => {
    // The Claude-Design JSX file describes the section layout — pin it
    // so future JSX edits surface here.
    expect(PROFILE_JSX_SRC).toMatch(/function MonthStrip\(/);
    expect(PROFILE_JSX_SRC).toMatch(/Decisions this month/);
    expect(PROFILE_JSX_SRC).toMatch(/BHD shopped smarter/);
    expect(PROFILE_JSX_SRC).toMatch(/Bonus credits/);
  });

  it('ProfileScreen.tsx imports MonthStrip from ProfileEditorialSections', () => {
    expect(PROFILE_SRC).toMatch(
      /import\s*\{[^}]*MonthStrip[^}]*\}\s*from\s*['"]\.\.\/components\/ProfileEditorialSections['"]/,
    );
  });

  it('ProfileScreen renders MonthStrip in the JSX-canonical slot', () => {
    // Order: RecentDecisionsRow → PrioritiesInline → MonthStrip → FlatSettings.
    const recentIdx = PROFILE_SRC.indexOf('<RecentDecisionsRow');
    const prioritiesIdx = PROFILE_SRC.indexOf('<PrioritiesInline');
    const monthIdx = PROFILE_SRC.indexOf('<MonthStrip');
    const flatIdx = PROFILE_SRC.indexOf('styles.flatCard');
    expect(recentIdx).toBeGreaterThan(0);
    expect(prioritiesIdx).toBeGreaterThan(recentIdx);
    expect(monthIdx).toBeGreaterThan(prioritiesIdx);
    expect(flatIdx).toBeGreaterThan(monthIdx);
  });
});
