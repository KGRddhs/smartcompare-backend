/**
 * F-S1.5i regression — ProfileScreen toggles muted + tap-route to
 * EditPreferences when preferences.priorities is empty.
 *
 * Contract:
 * - hasPriorities = (preferences?.priorities?.length ?? 0) > 0
 * - togglesGated = preferences === null || !hasPriorities
 * - When togglesGated: the 2 toggle hosts (AI sharing master +
 *   Notifications master) are wrapped in a TouchableOpacity whose
 *   onPress routes to EditPreferences (via handleEditStyleProfile)
 * - The ToggleRow components have `disabled={... || togglesGated}` so
 *   the inner Switch can't flip while the user has no priorities
 * - Sub-toggles (decision_insight / cohort_curiosity / decision_retrospective)
 *   only render when notificationsEnabled AND !togglesGated — they were
 *   silently 422'ing previously for no-priorities users
 *
 * Same source-grep approach used by ProfileScreen.bundleA.test.tsx — full
 * render pulls in 20+ services. Structural contract captured via source
 * matching.
 */

import * as fs from 'fs';
import * as path from 'path';

const PROFILE_PATH = path.resolve(__dirname, '../src/screens/ProfileScreen.tsx');
const SOURCE = fs.readFileSync(PROFILE_PATH, 'utf8');

describe('F-S1.5i — ProfileScreen toggle gating on empty priorities', () => {
  it('derives hasPriorities from preferences.priorities.length', () => {
    expect(SOURCE).toMatch(
      /hasPriorities\s*=\s*\(\s*preferences\?\.priorities\?\.length\s*\?\?\s*0\s*\)\s*>\s*0/,
    );
  });

  it('derives togglesGated from null preferences OR no priorities', () => {
    expect(SOURCE).toMatch(/togglesGated\s*=\s*preferences\s*===\s*null\s*\|\|\s*!hasPriorities/);
  });

  it('AI sharing ToggleRow disabled prop includes togglesGated', () => {
    // The AI sharing ToggleRow must propagate togglesGated into its
    // own `disabled` so the Switch can't flip while gated. Previously
    // it only checked `aiSharingSaving || preferences === null` which
    // ignored the empty-priorities case.
    expect(SOURCE).toMatch(
      /label=\{t\(['"]profile\.aiSharing\.title['"]\)\}[\s\S]{0,400}disabled=\{[^}]*togglesGated[^}]*\}/,
    );
  });

  it('Notifications master ToggleRow disabled prop includes togglesGated', () => {
    expect(SOURCE).toMatch(
      /label=\{t\(['"]profile\.notifs\.master\.title['"]\)\}[\s\S]{0,400}disabled=\{[^}]*togglesGated[^}]*\}/,
    );
  });

  it('sub-toggles hidden when togglesGated', () => {
    // The notifications sub-toggles block must check `!togglesGated`
    // in its render guard so it doesn't render dead sub-rows for
    // users with no priorities.
    expect(SOURCE).toMatch(/notificationsEnabled\s*&&\s*!togglesGated/);
  });

  it('toggle host taps route to handleEditStyleProfile when gated', () => {
    // Outer TouchableOpacity wrappers must call handleEditStyleProfile
    // on press when togglesGated is true (and undefined / no-op
    // otherwise so the inner ToggleRow handles its own tap when
    // ungated).
    expect(SOURCE).toMatch(/onPress=\{\s*togglesGated\s*\?\s*handleEditStyleProfile\s*:\s*undefined\s*\}/);
  });

  it('renders disabledReason caption when togglesGated', () => {
    // The captionr surfaces the gating reason in the rhythm of other
    // settings text (no banner, no modal).
    expect(SOURCE).toMatch(/togglesGated\s*\?\s*\([\s\S]{0,200}profile\.toggle\.disabledReason/);
  });

  it('muted opacity style is applied to toggle host when gated', () => {
    expect(SOURCE).toMatch(/togglesGated\s*&&\s*styles\.flatRowToggleHostMuted/);
  });
});
