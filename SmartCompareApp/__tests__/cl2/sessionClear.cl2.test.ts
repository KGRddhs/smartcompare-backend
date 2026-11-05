/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R25, R26, P7 (spec section 5, RULINGS_S81_G6
 * R-G6-2): the cache is per user and cleared by ONE App.tsx effect keyed on
 * user?.id (every sign-out path ends in setUser(null)); every Results mount
 * invalidates history:*; authService.ts is untouched. Static rows over the
 * source, CRLF normalised.
 */

import * as fs from 'fs';
import * as path from 'path';

const ROOT = path.resolve(__dirname, '../..');

function readSrc(rel: string): string {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');
}

function count(hay: string, needle: string): number {
  return hay.split(needle).length - 1;
}

describe('CL2 session clear (C4)', () => {
  it('R25 App.tsx has exactly one setSwrUser call, in the user?.id effect', () => {
    const app = readSrc('App.tsx');
    expect(count(app, 'setSwrUser(')).toBe(1);
    expect(app).toMatch(
      /useEffect\(\(\) => \{\s*setSwrUser\(user\?\.id \?\? null\);\s*\}, \[user\?\.id\]\);/
    );
    expect(app).toMatch(/import \{[^}]*\bsetSwrUser\b[^}]*\} from '\.\/src\/services\/swrCache';/);
  });

  it('R26 ResultsScreen invalidates history:* inside a mount ([]) effect', () => {
    const results = readSrc('src/screens/ResultsScreen.tsx');
    expect(results).toMatch(
      /useEffect\(\(\) => \{\s*invalidateSwrPrefix\('history:'\);\s*\}, \[\]\);/
    );
    expect(results).toMatch(/import \{[^}]*\binvalidateSwrPrefix\b[^}]*\} from '\.\.\/services\/swrCache';/);
  });

  it('P7 authService.ts is untouched: no swrCache, clearSession body as at base', () => {
    const auth = readSrc('src/services/authService.ts');
    expect(auth).not.toMatch(/swrCache/);
    expect(auth).not.toMatch(/setSwrUser/);
    const start = auth.indexOf('export async function clearSession(): Promise<void> {');
    expect(start).toBeGreaterThan(-1);
    const end = auth.indexOf('\n}\n', start);
    const body = auth.slice(start, end + 2);
    const code = body
      .split('\n')
      .map((line) => line.replace(/\/\/.*$/, '').trim())
      .filter((line) => line.length > 0);
    expect(code).toEqual([
      'export async function clearSession(): Promise<void> {',
      'sessionEpoch += 1;',
      'try {',
      'await SecureStore.deleteItemAsync(TOKEN_STORAGE_KEY);',
      'await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);',
      'await AsyncStorage.removeItem(USER_STORAGE_KEY);',
      '} catch (error) {',
      "if (__DEV__) console.error('Error clearing session:', error);",
      '}',
      '}',
    ]);
  });
});
