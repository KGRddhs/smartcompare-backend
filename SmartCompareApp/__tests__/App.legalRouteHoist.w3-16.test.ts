/**
 * W3-16 (absorbs the Legal-hoist half of MB-FLOWS-STATE-08) — spec §5-A.11.
 *
 * The consent row's Terms / Privacy spans live on Register / Login, i.e.
 * while the user is NOT authenticated. Today `Legal` is registered INSIDE the
 * authenticated branch of App.tsx, so from Register/Login the route does not
 * exist and `navigate('Legal')` is silently dropped. The fix registers it at
 * navigator level, after the ReferralLanding / InviteeQuiz pair that is
 * already root-level for the same reason.
 *
 * POSITION ONLY. "Exactly one Legal" is NOT re-asserted: the existing
 * __tests__/App.distinctRouteNames.test.ts already reds on any duplicate
 * Stack.Screen name. Same static-scan approach and the same regex as that
 * file — rendering App.tsx is not feasible under this jest env
 * (App.navigation.test.tsx:36-39).
 */

import * as fs from 'fs';
import * as path from 'path';

const SOURCE = fs.readFileSync(path.resolve(__dirname, '../App.tsx'), 'utf8');

/** Source index of every `<Stack.Screen … name="X"` registration of `name`. */
function registrationIndexes(name: string): number[] {
  const re = /<Stack\.Screen[\s\S]{0,200}?name=["']([A-Za-z][A-Za-z0-9]*)["']/g;
  const out: number[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(SOURCE)) !== null) {
    if (m[1] === name) out.push(m.index + m[0].lastIndexOf('name='));
  }
  return out;
}

describe('W3-16 — the Legal route is registered at root-navigator level', () => {
  it('11. every Legal registration sits after InviteeQuiz and before </Stack.Navigator>', () => {
    const legal = registrationIndexes('Legal');
    const inviteeQuiz = registrationIndexes('InviteeQuiz');
    const navigatorClose = SOURCE.lastIndexOf('</Stack.Navigator>');

    // Positive controls — the anchors this pin is measured against exist.
    expect(legal.length).toBeGreaterThan(0);
    expect(inviteeQuiz).toHaveLength(1);
    expect(navigatorClose).toBeGreaterThan(inviteeQuiz[0]);

    for (const idx of legal) {
      expect(idx).toBeGreaterThan(inviteeQuiz[0]);
      expect(idx).toBeLessThan(navigatorClose);
    }
  });
});
