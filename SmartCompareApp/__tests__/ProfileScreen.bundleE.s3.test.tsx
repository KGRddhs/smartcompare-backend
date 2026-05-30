/**
 * ProfileScreen Bundle E S3 — REWRITE element-order + DELETE-list contract.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/ProfileScreen.jsx
 * (1-323). Element-order checklist: docs/plans/_s3-a1-element-order.md.
 *
 * Per the A1.1 audit, ProfileScreen.tsx was already REWRITTEN top-down
 * for JSX in F-S1.5c. S3 deltas are minor surgical tightening + pin the
 * load-bearing testID surface so the F-S1.5c structure stays intact
 * through any future refactor.
 *
 * Tests pin the JSX:
 *   - JSX:34-51   ProfileHeaderRow at TOP (Q logo + name + region + settings)
 *   - JSX:122-161 RecentDecisionsRow second
 *   - JSX:163-200 PrioritiesInline third
 *   - JSX:202-221 MonthStrip fourth
 *   - JSX:251-275 FlatSettings with 4 eyebrow groups
 *   - DELETE list: no brandTitleRow / screenTitle / StyleProfileCard /
 *     ReferralStatusCard / B6 Upgrade card at top-level
 */

import * as fs from 'fs';
import * as path from 'path';

const PROFILE_PATH = path.resolve(__dirname, '../src/screens/ProfileScreen.tsx');

let profileSrc: string;

beforeAll(() => {
  profileSrc = fs.readFileSync(PROFILE_PATH, 'utf8');
});

describe('ProfileScreen S3 — JSX:34-51 ProfileHeaderRow at top', () => {
  it('renders ProfileHeaderRow with testID profile-header-settings (icon button)', () => {
    expect(profileSrc).toMatch(/testID\s*=\s*["']profile-header-settings["']/);
  });

  it('ProfileHeaderRow renders BEFORE the FlatSettings card', () => {
    // JSX:310 / TSX:405 — header is the first element inside the scroll.
    // FlatSettings (the flatCard) comes much later. Index-of order pins that.
    const headerIdx = profileSrc.indexOf('<ProfileHeaderRow');
    const flatCardIdx = profileSrc.indexOf('styles.flatCard');
    expect(headerIdx).toBeGreaterThan(0);
    expect(flatCardIdx).toBeGreaterThan(0);
    expect(headerIdx).toBeLessThan(flatCardIdx);
  });
});

describe('ProfileScreen S3 — JSX:122-275 element-order top-down', () => {
  it('elements render in JSX order: header → recent → priorities → month → settings', () => {
    // Match the render() body — anchor on the SafeAreaView root and the
    // closing of ScrollView.
    const headerIdx = profileSrc.indexOf('<ProfileHeaderRow');
    const recentIdx = profileSrc.indexOf('<RecentDecisionsRow');
    const prioritiesIdx = profileSrc.indexOf('<PrioritiesInline');
    const monthIdx = profileSrc.indexOf('<MonthStrip');
    const flatIdx = profileSrc.indexOf('styles.flatCard');
    expect(headerIdx).toBeGreaterThan(0);
    expect(recentIdx).toBeGreaterThan(headerIdx);
    expect(prioritiesIdx).toBeGreaterThan(recentIdx);
    expect(monthIdx).toBeGreaterThan(prioritiesIdx);
    expect(flatIdx).toBeGreaterThan(monthIdx);
  });
});

describe('ProfileScreen S3 — FlatSettings 4 eyebrow groups (JSX:251-275)', () => {
  it('renders ACCOUNT eyebrow', () => {
    expect(profileSrc).toMatch(/profile\.section\.account/);
  });

  it('renders PRIVACY & NOTIFICATIONS eyebrow', () => {
    expect(profileSrc).toMatch(/profile\.section\.privacy_notifications/);
  });

  it('renders HELP eyebrow', () => {
    expect(profileSrc).toMatch(/profile\.section\.help/);
  });

  it('renders DANGER ZONE eyebrow', () => {
    expect(profileSrc).toMatch(/profile\.section\.danger/);
  });

  it('eyebrow groups render in JSX order: account → privacy → help → danger', () => {
    const accountIdx = profileSrc.indexOf('profile.section.account');
    const privacyIdx = profileSrc.indexOf('profile.section.privacy_notifications');
    const helpIdx = profileSrc.indexOf('profile.section.help');
    const dangerIdx = profileSrc.indexOf('profile.section.danger');
    expect(accountIdx).toBeGreaterThan(0);
    expect(privacyIdx).toBeGreaterThan(accountIdx);
    expect(helpIdx).toBeGreaterThan(privacyIdx);
    expect(dangerIdx).toBeGreaterThan(helpIdx);
  });
});

describe('ProfileScreen S3 — DELETE list (Bundle D editorial cards not in JSX)', () => {
  // Strip comments — the F-S1.5c file header documents what was deleted.
  const codeOnly = () =>
    profileSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');

  it('drops the brandTitleRow + "Profile" h1 (header is the brand moment)', () => {
    const stripped = codeOnly();
    // No top-level "Profile" h1 / brandTitle. Check there's no rendered
    // <Text> with the literal "Profile" string outside of i18n keys.
    expect(stripped).not.toMatch(/brandTitleRow/);
    expect(stripped).not.toMatch(/screenTitle/);
  });

  it('drops the standalone StyleProfileCard at top-level', () => {
    // The user info moved into ProfileHeaderRow. There should be no
    // import OR JSX render of <StyleProfileCard /> in ProfileScreen.tsx.
    expect(codeOnly()).not.toMatch(/<StyleProfileCard\b/);
  });

  it('drops the standalone ReferralStatusCard', () => {
    expect(codeOnly()).not.toMatch(/<ReferralStatusCard\b/);
  });

  it('drops the standalone B6 Upgrade card with Sparkles icon at top-level', () => {
    // The Upgrade is now a row inside the ACCOUNT eyebrow group, not a
    // standalone card. Sparkles icon should not be imported (Settings
    // icon and ChevronRight are still needed).
    expect(codeOnly()).not.toMatch(/\bSparkles\b/);
  });
});

describe('ProfileScreen S3 — testID surface stability (rows have testIDs)', () => {
  it('keeps profile-row-edit on the Edit profile row', () => {
    expect(profileSrc).toMatch(/testID\s*=\s*["']profile-row-edit["']/);
  });

  it('keeps profile-row-logout on the destructive logout row', () => {
    expect(profileSrc).toMatch(/testID\s*=\s*["']profile-row-logout["']/);
  });

  it('keeps profile-row-language with EN/AR toggle', () => {
    expect(profileSrc).toMatch(/testID\s*=\s*["']profile-row-language["']/);
  });
});

describe('ProfileScreen S3 — Build Principle #4 (no scary copy / motion)', () => {
  it('contains no shake / wobble / jitter / bounce in source', () => {
    const stripped = profileSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/\/\/.*$/gm, '');
    const banned = ['shake', 'wobble', 'jitter', 'bounce'];
    for (const w of banned) {
      expect(stripped.toLowerCase()).not.toContain(w);
    }
  });

  it('contains no scary copy strings (Failed to / couldnt / try again) as raw text', () => {
    const lower = profileSrc.toLowerCase();
    expect(lower).not.toMatch(/'failed to/);
    expect(lower).not.toMatch(/'try again/);
    expect(lower).not.toMatch(/"failed to/);
    expect(lower).not.toMatch(/"try again/);
  });
});
