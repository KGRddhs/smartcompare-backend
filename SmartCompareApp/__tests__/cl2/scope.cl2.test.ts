/**
 * S81-G6 CL2 CLIENT-SPEED -- rows P14-P18 (spec section 5, RULINGS_S81_G6
 * R-G6-3 / R-G6-12): the scope fences. No new flag, no package change, the
 * Geist runtime load kept, no copy in any new module, Home not throttled.
 * Static rows, CRLF normalised; P17 is vacuous at base (no new module yet).
 */

import * as fs from 'fs';
import * as path from 'path';

const ROOT = path.resolve(__dirname, '../..');

function readSrc(rel: string): string {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');
}

/** The export names of features.ts at base ec747b49, recorded as a literal. */
const FEATURES_EXPORTS_AT_BASE = [
  'CANARY_NEW_ONBOARDING_PERCENT',
  'ENABLE_EXPO_FETCH_SSE_DEFAULT',
  '_resetFlagStableIdForTests',
  '_setExpoFetchSseForTests',
  'FeatureFlag',
  'features',
  'setFlagStableId',
];

const NEW_MODULES = [
  'src/utils/clientSpeed.ts',
  'src/services/swrCache.ts',
  'src/services/imagePrefetch.ts',
  'src/navigation/lazyScreen.tsx',
];

function stripComments(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"])\/\/.*$/gm, '$1');
}

describe('CL2 scope fences', () => {
  it('P14 features.ts: the SSE default stays false and no export name is added', () => {
    const src = readSrc('src/config/features.ts');
    expect(src).toMatch(/^export const ENABLE_EXPO_FETCH_SSE_DEFAULT = false;$/m);
    const names = Array.from(
      src.matchAll(/^export\s+(?:const|function|type|let|class|interface|enum)\s+([A-Za-z_$][\w$]*)/gm)
    ).map((m) => m[1]);
    expect(names.sort()).toEqual([...FEATURES_EXPORTS_AT_BASE].sort());
    expect(src).not.toMatch(/^export\s*\{/m);
  });

  it('P15 package.json: @sentry/react-native ~7.2.0, no expo-image, no expo-atlas', () => {
    const pkg = JSON.parse(readSrc('package.json'));
    const all = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
    expect(all['@sentry/react-native']).toBe('~7.2.0');
    expect(Object.prototype.hasOwnProperty.call(all, 'expo-image')).toBe(false);
    expect(Object.prototype.hasOwnProperty.call(all, 'expo-atlas')).toBe(false);
  });

  it('P16 fonts.ts still loads the three Geist TTFs at runtime', () => {
    const src = readSrc('src/theme/fonts.ts');
    for (const w of ['Regular', 'SemiBold', 'Bold']) {
      expect(src).toContain("require('../../assets/fonts/Geist-" + w + ".ttf')");
    }
    expect(src).toMatch(/useExpoFonts\(/);
  });

  it('P17 no copy in a new module: no t(, no useTranslation, no <Text, no JSX text', () => {
    const offenders: string[] = [];
    for (const rel of NEW_MODULES) {
      const p = path.join(ROOT, rel);
      if (!fs.existsSync(p)) continue;
      const src = stripComments(readSrc(rel));
      if (/(^|[^\w.$])t\(/.test(src)) offenders.push(rel + ': t(');
      if (/useTranslation/.test(src)) offenders.push(rel + ': useTranslation');
      if (/<Text\b/.test(src)) offenders.push(rel + ': <Text');
      if (/i18n/.test(src)) offenders.push(rel + ': i18n');
      // JSX text: literal text, or a string-literal child, right before a closing tag.
      if (/>\s*[A-Za-z][^<>{}]*<\//.test(src)) offenders.push(rel + ': JSX text');
      if (/>\s*\{\s*['"`][^'"`]*['"`]\s*\}\s*<\//.test(src)) offenders.push(rel + ': JSX string child');
    }
    expect(offenders).toEqual([]);
  });

  it('P18 Home is not throttled: no SWR reads, the referral focus refetch kept', () => {
    const home = readSrc('src/screens/HomeScreen.tsx');
    expect(home).not.toMatch(/shouldRefetchOnFocus/);
    expect(home).not.toMatch(/swrRead/);
    expect(home).not.toMatch(/swrCache/);
    expect(home).toMatch(
      /useFocusEffect\(\s*useCallback\(\(\) => \{\s*let cancelled = false;\s*\(async \(\) => \{\s*try \{\s*const status: any = await getReferralStatus\(\);/
    );
  });
});
