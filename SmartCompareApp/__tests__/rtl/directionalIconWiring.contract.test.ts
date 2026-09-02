/**
 * Directional-icon wiring fence — M21 W4 rtl-i18n (MB-i18n-rtl-03).
 *
 * Source-grep contract: every horizontal direction-bearing lucide icon
 * (ArrowLeft / ChevronLeft / ChevronRight — back affordances and nav-row
 * disclosure chevrons) in the files below must render INSIDE the
 * DirectionalIcon wrapper so it mirrors under RTL.
 *
 * Vertical chevrons (ChevronDown/Up) and semantic non-directional icons
 * (TrendingUp = data direction, Share2 = node graph) are deliberately
 * NOT in scope — mirroring those is wrong per src/utils/rtl.ts guidance.
 */
import * as fs from 'fs';
import * as path from 'path';

const ROOT = path.resolve(__dirname, '../../src');

/** file (relative to src/) -> expected count of directional icon sites */
const WIRED_FILES: Record<string, number> = {
  'screens/ResultsScreen.tsx': 3,
  'components/results/ResultsContent.tsx': 1,
  'screens/EditProfileScreen.tsx': 2,
  'screens/EditPreferencesFlow.tsx': 1,
  'screens/LegalScreen.tsx': 1,
  'screens/ContactUsScreen.tsx': 1,
  'screens/InviteeQuizScreen.tsx': 1,
  'screens/ReferralLandingScreen.tsx': 1,
  'screens/HistoryScreen.tsx': 1,
  'screens/ProfileScreen.tsx': 1,
  'screens/LoginScreen.tsx': 1,
};

const DIRECTIONAL_JSX = /<(ArrowLeft|ChevronLeft|ChevronRight)\b/g;
const WRAPPED_JSX = /<DirectionalIcon[^>]*>\s*<(ArrowLeft|ChevronLeft|ChevronRight)\b/g;

function read(rel: string): string {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8');
}

describe('directional icons are wrapped in DirectionalIcon (RTL mirroring)', () => {
  for (const [rel, expectedSites] of Object.entries(WIRED_FILES)) {
    it(`${rel}: all ${expectedSites} directional icon site(s) wrapped`, () => {
      const src = read(rel);
      const directional = src.match(DIRECTIONAL_JSX) ?? [];
      const wrapped = src.match(WRAPPED_JSX) ?? [];
      // Site count drifting means an icon was added/removed — update the
      // table above AND wrap the new site.
      expect(directional.length).toBe(expectedSites);
      expect(wrapped.length).toBe(expectedSites);
      expect(src).toMatch(/import\s*\{\s*DirectionalIcon\s*\}\s*from/);
    });
  }

  it('fence is not a silent no-op (regexes still match real JSX)', () => {
    const total = Object.keys(WIRED_FILES)
      .map((rel) => (read(rel).match(DIRECTIONAL_JSX) ?? []).length)
      .reduce((a, b) => a + b, 0);
    expect(total).toBeGreaterThanOrEqual(13);
  });
});
