/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R34, P13 (spec section 5, RULINGS_S81_G6
 * R-G6-8): freezeOnBlur: true in the MainTabs Tab.Navigator screenOptions
 * ONLY; no enableFreeze(); the AuthStack and root Stack screenOptions stay
 * { headerShown: false }. Static rows over App.tsx, CRLF normalised.
 */

import * as fs from 'fs';
import * as path from 'path';

const ROOT = path.resolve(__dirname, '../..');
const APP = fs.readFileSync(path.join(ROOT, 'App.tsx'), 'utf8').replace(/\r\n/g, '\n');
const INDEX = fs.readFileSync(path.join(ROOT, 'index.ts'), 'utf8').replace(/\r\n/g, '\n');

/** The text of the <Tab.Navigator ...> opening tag (up to its closing '>'). */
function tabNavigatorOpening(): string {
  const start = APP.indexOf('<Tab.Navigator');
  expect(start).toBeGreaterThan(-1);
  const end = APP.indexOf('<Tab.Screen', start);
  expect(end).toBeGreaterThan(start);
  return APP.slice(start, end);
}

describe('CL2 freezeOnBlur (C8)', () => {
  it('R34 the MainTabs Tab.Navigator screenOptions carry freezeOnBlur: true', () => {
    const opening = tabNavigatorOpening();
    expect(opening).toMatch(/screenOptions=\{\{[\s\S]*\bfreezeOnBlur:\s*true,?[\s\S]*\}\}/);
    expect(APP.split('freezeOnBlur').length - 1).toBe(1);
  });

  it('P13 no enableFreeze; AuthStack and root Stack screenOptions are exactly { headerShown: false }', () => {
    expect(APP).not.toMatch(/enableFreeze\(/);
    expect(INDEX).not.toMatch(/enableFreeze\(/);
    expect(APP).toContain('<AuthStack.Navigator screenOptions={{ headerShown: false }}>');
    expect(APP).toContain('<Stack.Navigator screenOptions={{ headerShown: false }}>');
    expect(APP.split('<AuthStack.Navigator').length - 1).toBe(1);
    expect(APP.split('<Stack.Navigator').length - 1).toBe(1);
  });
});
