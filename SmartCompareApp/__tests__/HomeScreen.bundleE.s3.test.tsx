/**
 * HomeScreen Bundle E S3 — REWRITE element-order + DELETE-list contract.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/HomeScreen.jsx
 * (1-717). Element-order checklist: docs/plans/_s3-a1-element-order.md.
 *
 * This is a SOURCE-GREP contract test (same pattern as
 * HomeScreen.bundleE.contract.test.tsx). The HomeScreen file has 25+ mock
 * dependencies, so we lean on structural assertions over the file content
 * rather than full-tree render. Mirrors how Bundle B + Bundle E S1 stayed
 * green through the integration-mock churn.
 *
 * Tests pin the load-bearing checklist rows from A1.1:
 *   - JSX:111-160  ModeSegment pill-container collapse
 *   - JSX:199-217  Compare CTA (primary black button INSIDE CompareCard,
 *                  label flips on inputMode)
 *   - JSX:438-501  SmartPickCard renders below CompareCard
 *   - JSX:534-570  QuickCategories renders below SmartPickCard
 *   - JSX:573-605  SavingsBanner renders below QuickCategories
 *   - JSX:608-651  TrendingNearYou renders below SavingsBanner
 *   - DELETE list  no `home-editorial-stub`, no `void serverOnline`
 */

import * as fs from 'fs';
import * as path from 'path';

const HOME_PATH = path.resolve(__dirname, '../src/screens/HomeScreen.tsx');
const HOME_ED_PATH = path.resolve(__dirname, '../src/components/HomeEditorialSections.tsx');
const EN_LOCALE_PATH = path.resolve(__dirname, '../src/i18n/en.json');

let homeSrc: string;
let homeEdSrc: string;
let enLocale: Record<string, string>;

beforeAll(() => {
  homeSrc = fs.readFileSync(HOME_PATH, 'utf8');
  homeEdSrc = fs.readFileSync(HOME_ED_PATH, 'utf8');
  enLocale = JSON.parse(fs.readFileSync(EN_LOCALE_PATH, 'utf8'));
});

describe('HomeScreen S3 — JSX:111-160 ModeSegment pill-container', () => {
  it('mode chips live INSIDE a pill-container, not on a bare flex-row rail', () => {
    // JSX wraps the 3 ModeTabs in ONE outer container with borderRadius
    // 999 + 1px border + padding 4. Test for the container border style
    // applied to the rail/segment.
    // Acceptance: the styles object (or inline style) for the mode segment
    // wrapper carries borderRadius: 999 + borderWidth: 1.
    const m = homeSrc.match(/modeSegment\s*:\s*\{[^}]+\}/);
    expect(m).toBeTruthy();
    const body = m![0];
    expect(body).toMatch(/borderRadius\s*:\s*999/);
    expect(body).toMatch(/borderWidth\s*:\s*1/);
    // Padding 4 per JSX:124 (`padding: 4`).
    expect(body).toMatch(/padding\s*:\s*4/);
  });

  it('individual mode tabs DO NOT carry their own border/borderColor', () => {
    // The pill-container owns the border; inner tabs are borderless
    // when inactive and emerald-fill when active. Tab style should NOT
    // include borderWidth.
    const m = homeSrc.match(/modeTab\s*:\s*\{[^}]+\}/);
    expect(m).toBeTruthy();
    const body = m![0];
    expect(body).not.toMatch(/borderWidth\s*:\s*1/);
    // Tab has its own radius (999) for the active fill pill.
    expect(body).toMatch(/borderRadius\s*:\s*999/);
  });
});

describe('HomeScreen S3 — JSX:199-217 Compare CTA inside CompareCard', () => {
  it('renders a Compare CTA button INSIDE CompareCard with testID home-compare-cta', () => {
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-compare-cta["']/);
  });

  it('Compare CTA label uses i18n home.compare.cta and home.cta.openCamera', () => {
    // HomeScreen owns the scan-mode CTA ("Open camera"); in link/type
    // modes the Compare CTA is consolidated inside TwoInputShell (which
    // references home.compare.cta). Both i18n keys must still exist.
    expect(enLocale['home.compare.cta']).toBeDefined();
    expect(enLocale['home.cta.openCamera']).toBeDefined();
    // HomeScreen.tsx references home.cta.openCamera (scan label).
    expect(homeSrc).toMatch(/home\.cta\.openCamera/);
    // home.compare.cta lives in TwoInputShell now — verify it's referenced
    // there so the canonical Compare label still routes through i18n.
    const twoInputSrc = fs.readFileSync(
      path.resolve(__dirname, '../src/components/TwoInputShell.tsx'),
      'utf8'
    );
    expect(twoInputSrc).toMatch(/home\.compare\.cta/);
  });

  it('Compare CTA style is full-width 48px-tall with cta.primary background', () => {
    const m = homeSrc.match(/compareCta\s*:\s*\{[^}]+\}/);
    expect(m).toBeTruthy();
    const body = m![0];
    // Height 48 per JSX:204 (`height: 48`).
    expect(body).toMatch(/(height|minHeight)\s*:\s*48/);
    // bg color points at cta.primary (not accent — JSX is black-CTA).
    expect(body).toMatch(/cta\.primary/);
  });
});

describe('HomeScreen S3 — JSX:438-651 editorial sections render flat-sibling order', () => {
  it('HomeEditorialSections wrapper drops its internal home-editorial-scroll ScrollView', () => {
    // Per JSX the 4 sections (SmartPick/QuickCats/Savings/Trending) live
    // as flat siblings inside HomeScreen's main ScrollView. The wrapper
    // should NOT render its own home-editorial-scroll ScrollView.
    expect(homeEdSrc).not.toMatch(/testID\s*=\s*["']home-editorial-scroll["']/);
  });

  it('SmartPickCard renders below Compare CTA (top-down order)', () => {
    // We assert order by index-of: testID home-compare-cta must appear
    // before the JSX render of <HomeEditorialSections in the source.
    // Use the JSX-tag pattern to skip past the import-line match.
    const ctaIdx = homeSrc.indexOf('home-compare-cta');
    const editorialRenderIdx = homeSrc.indexOf('<HomeEditorialSections');
    expect(ctaIdx).toBeGreaterThan(0);
    expect(editorialRenderIdx).toBeGreaterThan(0);
    expect(editorialRenderIdx).toBeGreaterThan(ctaIdx);
  });

  it('the 4 editorial sections render in the JSX order Smart→Quick→Savings→Trending', () => {
    // Source-of-truth file is HomeEditorialSections.tsx wrapper. The render
    // body of HomeEditorialSections must call the 4 sections in this order.
    // Anchor on the default-export function declaration (S3 keeps default
    // export but renamed internal — match either).
    const wrapper = homeEdSrc.match(/export\s+(?:default\s+)?function\s+HomeEditorialSections[\s\S]*?^}/m);
    expect(wrapper).toBeTruthy();
    const body = wrapper![0];
    const smartIdx = body.indexOf('SmartPickCard');
    const quickIdx = body.indexOf('QuickCategories');
    const savingsIdx = body.indexOf('SavingsBanner');
    const trendingIdx = body.indexOf('TrendingNearYou');
    expect(smartIdx).toBeGreaterThan(0);
    expect(quickIdx).toBeGreaterThan(smartIdx);
    expect(savingsIdx).toBeGreaterThan(quickIdx);
    expect(trendingIdx).toBeGreaterThan(savingsIdx);
  });
});

describe('HomeScreen S3 — DELETE list (TSX pieces not in JSX)', () => {
  // Strip comments first — the file header documents what was deleted in
  // a comment block. We only care about runtime code references.
  const codeOnly = () =>
    homeSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');

  it('drops the home-editorial-stub 0-height marker (not in JSX)', () => {
    expect(codeOnly()).not.toMatch(/home-editorial-stub/);
  });

  it('drops the void serverOnline plumbing (no health-state UI in JSX)', () => {
    expect(codeOnly()).not.toMatch(/void serverOnline/);
  });
});

describe('HomeScreen S3 — testID surface stability (no regression)', () => {
  // The Bundle E contract test pins these; we re-pin here so the S3
  // REWRITE doesn't accidentally rename them.
  it('keeps home-header-counter pill', () => {
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-header-counter["']/);
  });

  it('keeps home-center-area wrapper', () => {
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-center-area["']/);
  });

  it('keeps home-mode-{scan,link,type} chip testIDs', () => {
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-mode-scan["']/);
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-mode-link["']/);
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-mode-type["']/);
  });
});

describe('HomeScreen S3 — Build Principle #4 (no scary copy / motion)', () => {
  it('contains no shake / wobble / jitter / bounce in source', () => {
    // Strip comments first — "tree-shaken" + "b-o-u-n-c-e" mentions in
    // documentation comments are not user-visible motion. Same pattern
    // as HomeScreen.bundleE.contract.test.tsx.
    const stripped = homeSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    const banned = ['shake', 'wobble', 'jitter', 'bounce'];
    for (const w of banned) {
      expect(stripped.toLowerCase()).not.toContain(w);
    }
  });

  it('contains no scary copy strings (Failed to / couldnt / try again)', () => {
    const lower = homeSrc.toLowerCase();
    // Allow "failed" inside i18n keys (e.g. error.saveFailed) but not as
    // a user-visible English string. Test for the literal forbidden phrases.
    expect(lower).not.toMatch(/'failed to/);
    expect(lower).not.toMatch(/'try again/);
    expect(lower).not.toMatch(/"failed to/);
    expect(lower).not.toMatch(/"try again/);
  });
});

describe('HomeScreen S3 — i18n vocabulary present in both locales', () => {
  it('home.cta.openCamera key exists in en.json', () => {
    expect(enLocale['home.cta.openCamera']).toBeDefined();
    expect(typeof enLocale['home.cta.openCamera']).toBe('string');
    expect(enLocale['home.cta.openCamera'].length).toBeGreaterThan(0);
  });

  it('home.cta.openCamera key exists in ar.json (RTL parity)', () => {
    const arPath = path.resolve(__dirname, '../src/i18n/ar.json');
    const ar = JSON.parse(fs.readFileSync(arPath, 'utf8'));
    expect(ar['home.cta.openCamera']).toBeDefined();
    expect(typeof ar['home.cta.openCamera']).toBe('string');
    expect(ar['home.cta.openCamera'].length).toBeGreaterThan(0);
  });
});
