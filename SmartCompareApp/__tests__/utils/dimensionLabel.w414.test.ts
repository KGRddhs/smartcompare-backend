/**
 * W4-14 Part A1 — `localizedDimensionLabel(key, label, t)` (src/utils/dimensionLabel.ts).
 *
 * The `localizedCurrency` echo guard applied to dimension labels: the catalog value
 * when `results.dimension.<key>` resolves, otherwise the backend label — under ALL
 * the t() shapes the suite uses (the real i18next, a key-echo t that ignores
 * defaultValue = the global __mocks__/react-i18next and the per-file `(key) => key`
 * mocks, and a defaultValue-returning t).
 *
 * RED 4 = fails at the unit base 3985eaac: the module does not exist. The module is
 * required INSIDE the test body so its absence is an assertion, not a suite-level
 * import error.
 */
import i18next from 'i18next';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';

type TFn = (key: string, options?: Record<string, unknown>) => string;

function loadHelper(): (key: string | null | undefined, label: string, t: TFn) => string {
  let mod: any = null;
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    mod = require('../../src/utils/dimensionLabel');
  } catch (e) {
    mod = null;
  }
  expect(mod && typeof mod.localizedDimensionLabel).toBe('function');
  return mod.localizedDimensionLabel;
}

function arInstance() {
  const inst = i18next.createInstance();
  inst.init({
    lng: 'ar',
    fallbackLng: 'en',
    resources: { en: { translation: en }, ar: { translation: ar } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  } as any);
  return inst;
}

describe('W4-14 localizedDimensionLabel — echo-guard semantics', () => {
  it('RED 4: (a) real ar -> catalog value; (b) key-echo t -> label; (c) defaultValue t -> label; (d) empty key -> label; (e) uncatalogued key -> label', () => {
    const fn = loadHelper();
    const inst = arInstance();
    const tAr: TFn = inst.t.bind(inst) as any;
    const arCat = ar as Record<string, string>;

    // (a) the real Arabic catalog value, never the English label.
    const a = fn('longevity', 'Longevity', tAr);
    expect(arCat['results.dimension.longevity']).toBeDefined();
    expect(a).toBe(arCat['results.dimension.longevity']);
    expect(a).not.toBe('Longevity');

    // (b) a t that echoes the key and ignores defaultValue (the global mock shape).
    const echo: TFn = (key) => key;
    expect(fn('longevity', 'Longevity', echo)).toBe('Longevity');

    // (c) a t that returns defaultValue (the per-file mock shape).
    const dflt: TFn = (key, opts) => ((opts?.defaultValue as string) ?? key);
    expect(fn('longevity', 'Longevity', dflt)).toBe('Longevity');

    // (d) empty / undefined / null key -> the backend label, t never consulted.
    const never = jest.fn(() => 'SHOULD-NOT-BE-USED');
    expect(fn('', 'Longevity', never as any)).toBe('Longevity');
    expect(fn(undefined, 'Longevity', never as any)).toBe('Longevity');
    expect(fn(null, 'Longevity', never as any)).toBe('Longevity');

    // (e) an uncatalogued key under the real Arabic instance -> the backend label.
    expect(fn('popularity', 'Popularity', tAr)).toBe('Popularity');
  });

  it('RED 4b: (f) a t that returns an empty string -> label; (g) a t that returns a non-string (undefined, an object) -> label', () => {
    const fn = loadHelper();
    // (f) the `out.length === 0` branch: an empty catalog value never blanks a row.
    const empty: TFn = () => '';
    expect(fn('longevity', 'Longevity', empty)).toBe('Longevity');
    // (g) the `typeof out !== 'string'` branch: a t that yields undefined or an
    // object (i18next returnObjects / a nested key) never reaches the <Text>.
    const undef = (() => undefined) as unknown as TFn;
    expect(fn('longevity', 'Longevity', undef)).toBe('Longevity');
    const obj = (() => ({ length: 3 })) as unknown as TFn;
    expect(fn('longevity', 'Longevity', obj)).toBe('Longevity');
  });
});
