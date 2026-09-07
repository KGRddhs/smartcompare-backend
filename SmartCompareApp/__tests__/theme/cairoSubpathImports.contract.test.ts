/**
 * Cairo barrel-import fence — B4 (shipped asset payload).
 *
 * `@expo-google-fonts/cairo`'s index.js top-level `require()`s ALL EIGHT
 * TTF weights, and Metro does no tree-shaking in this app (no metro.config.js,
 * and the experimental tree-shaker is not present in this @expo/metro-config).
 * So one barrel import — `import { Cairo_400Regular } from '@expo-google-fonts/cairo'`
 * — puts every weight into the asset graph, including the five the app never
 * loads (200ExtraLight / 300Light / 500Medium / 800ExtraBold / 900Black =
 * 469,608 bytes, measured on disk).
 *
 * Contract: src/theme/fonts.ts imports each Cairo weight from its own
 * per-weight subpath and never from the package root, and takes `useFonts`
 * from expo-font (the cairo package's own useFonts re-enters the barrel).
 *
 * This is a source-level fence because the defect is a bundler-graph
 * property: at runtime the app behaves identically either way, so only the
 * import shape can be asserted.
 */
import * as fs from 'fs';
import * as path from 'path';

const FONTS_TS = path.resolve(__dirname, '../../src/theme/fonts.ts');
const SRC_ROOT = path.resolve(__dirname, '../../src');

/** Strip block + line comments so the doc block above the imports never matches. */
function code(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

function allSourceFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === '__tests__' || entry.name === '__snapshots__') continue;
      allSourceFiles(full, acc);
    } else if (/\.tsx?$/.test(entry.name)) {
      acc.push(full);
    }
  }
  return acc;
}

const USED_WEIGHTS = ['400Regular', '600SemiBold', '700Bold'] as const;

describe('Cairo font weights are imported per-weight, not through the barrel', () => {
  const source = code(fs.readFileSync(FONTS_TS, 'utf8'));

  it.each(USED_WEIGHTS)('imports Cairo_%s from its own subpath', (weight) => {
    expect(source).toContain(
      `import { Cairo_${weight} } from '@expo-google-fonts/cairo/${weight}';`
    );
  });

  it('never imports from the @expo-google-fonts/cairo package root', () => {
    // Any specifier that is exactly the package root drags all eight weights in.
    expect(source).not.toMatch(/from\s+'@expo-google-fonts\/cairo'/);
    expect(source).not.toMatch(/require\(\s*'@expo-google-fonts\/cairo'\s*\)/);
  });

  it('takes useFonts from expo-font, not from the cairo package', () => {
    expect(source).toMatch(/from\s+'expo-font'/);
    // `@expo-google-fonts/cairo/useFonts` re-exports through the barrel.
    expect(source).not.toMatch(/'@expo-google-fonts\/cairo\/useFonts'/);
  });

  it('does not reach for a Cairo weight the app never loads', () => {
    for (const dead of ['200ExtraLight', '300Light', '500Medium', '800ExtraBold', '900Black']) {
      expect(source).not.toContain(`Cairo_${dead}`);
    }
  });

  it('is the only module in src/ that touches @expo-google-fonts', () => {
    const offenders = allSourceFiles(SRC_ROOT)
      .filter((f) => path.resolve(f) !== FONTS_TS)
      .filter((f) => code(fs.readFileSync(f, 'utf8')).includes('@expo-google-fonts'));
    expect(offenders).toEqual([]);
  });
});

describe('useAppFonts loads every family the theme names', () => {
  it('passes all three Geist weights and all three Cairo weights in one map', () => {
    jest.isolateModules(() => {
      const loaded: Record<string, unknown>[] = [];
      jest.doMock('expo-font', () => ({
        useFonts: (map: Record<string, unknown>) => {
          loaded.push(map);
          return [true, null];
        },
      }));

      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const fonts = require('../../src/theme/fonts');
      expect(fonts.useAppFonts()).toBe(true);

      expect(loaded).toHaveLength(1);
      expect(Object.keys(loaded[0]).sort()).toEqual([
        'Cairo_400Regular',
        'Cairo_600SemiBold',
        'Cairo_700Bold',
        'Geist-Bold',
        'Geist-Regular',
        'Geist-SemiBold',
      ]);

      // Every family named by the theme must be a key of the loaded map.
      const named = [
        ...Object.values(fonts.fontFamily.en),
        ...Object.values(fonts.fontFamily.ar),
      ];
      for (const family of named) {
        expect(Object.keys(loaded[0])).toContain(family);
      }
    });
  });
});
