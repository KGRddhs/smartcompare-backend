/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R9-R15 (spec section 5, RULINGS_S81_G6
 * R-G6-9): src/services/imagePrefetch.ts, at most two https product images,
 * fire-and-forget with the catch, the FIFO dedupe of 32, the guard for the
 * jest react-native mock that has no Image.prefetch.
 *
 * Every behaviour row loads a FRESH copy of the module (and of the mapped
 * react-native mock) inside jest.isolateModules, so the module-level seen-set
 * never leaks between rows. The module does not exist at base: it is read
 * through loadOptional and asserted. Synthetic URLs only.
 */

import * as fs from 'fs';
import * as path from 'path';

function loadOptional(rel: string): any {
  try {
    return require(rel);
  } catch {
    return null;
  }
}

const MOD = '../../src/services/imagePrefetch';
const ROOT = path.resolve(__dirname, '../..');

function readSrc(rel: string): string {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');
}

type Fresh = { mod: any; RN: any };

/** A fresh module + the react-native mock instance it sees. */
function fresh(prefetchImpl?: ((url: string) => any) | null): Fresh {
  let out: Fresh = { mod: null, RN: null };
  jest.isolateModules(() => {
    const RN = require('react-native');
    if (prefetchImpl === null) {
      delete RN.Image.prefetch;
    } else {
      RN.Image.prefetch = jest.fn(prefetchImpl || (() => Promise.resolve(true)));
    }
    out = { mod: loadOptional(MOD), RN };
  });
  return out;
}

const u = (name: string) => 'https://img.example.test/' + name + '.jpg';

function resultWith(urls: any[]): any {
  return { success: true, overview: { products: urls.map((x) => ({ image_url: x })) } };
}

const settleMacro = () => new Promise<void>((resolve) => setImmediate(resolve));

describe('CL2 imagePrefetch leaf (C3)', () => {
  it('R9 two https URLs -> one prefetch each; returns undefined synchronously', () => {
    const { mod, RN } = fresh();
    expect(mod).not.toBeNull();
    const ret = mod.prefetchProductImages(resultWith([u('r9-a'), u('r9-b')]));
    expect(ret).toBeUndefined();
    expect(RN.Image.prefetch.mock.calls).toEqual([[u('r9-a')], [u('r9-b')]]);
  });

  it('R9 also reads the legacy top-level products array', () => {
    const { mod, RN } = fresh();
    expect(mod).not.toBeNull();
    mod.prefetchProductImages({ products: [{ image_url: u('r9-c') }, { image_url: u('r9-d') }] });
    expect(RN.Image.prefetch.mock.calls).toEqual([[u('r9-c')], [u('r9-d')]]);
  });

  it('R10 non-https, empty, non-string and over-long URLs are never prefetched', () => {
    const { mod, RN } = fresh();
    expect(mod).not.toBeNull();
    const longUrl = 'https://img.example.test/' + 'a'.repeat(2049 - 'https://img.example.test/'.length);
    expect(longUrl.length).toBe(2049);
    const bad: any[] = [
      'http://img.example.test/x.jpg',
      'data:image/png;base64,AAAA',
      '',
      null,
      undefined,
      42,
      longUrl,
    ];
    for (let i = 0; i < bad.length; i += 2) {
      mod.prefetchProductImages(resultWith(bad.slice(i, i + 2)));
    }
    mod.prefetchProductImages(null);
    mod.prefetchProductImages(undefined);
    mod.prefetchProductImages({});
    mod.prefetchProductImages({ overview: { products: 'not-an-array' } });
    expect(RN.Image.prefetch).not.toHaveBeenCalled();
  });

  it('R11 three products -> only the first two are prefetched', () => {
    const { mod, RN } = fresh();
    expect(mod).not.toBeNull();
    mod.prefetchProductImages(resultWith([u('r11-a'), u('r11-b'), u('r11-c')]));
    expect(RN.Image.prefetch.mock.calls).toEqual([[u('r11-a')], [u('r11-b')]]);
  });

  it('R12 a rejecting prefetch gets a catch handler attached', () => {
    const catchSpy = jest.fn();
    const thenable = { then: jest.fn(), catch: catchSpy };
    const { mod } = fresh(() => thenable);
    expect(mod).not.toBeNull();
    mod.prefetchProductImages(resultWith([u('r12-a')]));
    expect(catchSpy).toHaveBeenCalledTimes(1);
    expect(typeof (catchSpy.mock.calls as any[])[0][0]).toBe('function');
  });

  it('R12 a rejecting prefetch raises no unhandledRejection; a throwing one does not throw', async () => {
    const seen: unknown[] = [];
    const onUnhandled = (reason: unknown) => {
      seen.push(reason);
    };
    process.on('unhandledRejection', onUnhandled);
    try {
      const { mod } = fresh(() => Promise.reject(new Error('synthetic prefetch failure')));
      expect(mod).not.toBeNull();
      mod.prefetchProductImages(resultWith([u('r12-b')]));
      await settleMacro();
      await settleMacro();
      expect(seen).toEqual([]);
      const thrower = fresh(() => {
        throw new Error('synthetic sync failure');
      });
      expect(thrower.mod).not.toBeNull();
      expect(() => thrower.mod.prefetchProductImages(resultWith([u('r12-c')]))).not.toThrow();
    } finally {
      process.removeListener('unhandledRejection', onUnhandled);
    }
  });

  it('R13 an absent Image.prefetch (the jest mock shape) is a silent no-op', () => {
    const { mod, RN } = fresh(null);
    expect(mod).not.toBeNull();
    expect(RN.Image.prefetch).toBeUndefined();
    expect(() => mod.prefetchProductImages(resultWith([u('r13-a'), u('r13-b')]))).not.toThrow();
  });

  it('R14 the same URL across two calls is prefetched once; FIFO 32 evicts the oldest', () => {
    const { mod, RN } = fresh();
    expect(mod).not.toBeNull();
    mod.prefetchProductImages(resultWith([u('r14-0')]));
    mod.prefetchProductImages(resultWith([u('r14-0')]));
    expect(RN.Image.prefetch).toHaveBeenCalledTimes(1);
    // 32 more distinct URLs push r14-0 out of the 32-entry seen-set.
    for (let i = 1; i <= 32; i += 1) {
      mod.prefetchProductImages(resultWith([u('r14-' + i)]));
    }
    expect(RN.Image.prefetch).toHaveBeenCalledTimes(33);
    mod.prefetchProductImages(resultWith([u('r14-0')]));
    expect(RN.Image.prefetch).toHaveBeenCalledTimes(34);
    expect((RN.Image.prefetch.mock.calls as any[])[33][0]).toBe(u('r14-0'));
    // r14-32 is still remembered.
    mod.prefetchProductImages(resultWith([u('r14-32')]));
    expect(RN.Image.prefetch).toHaveBeenCalledTimes(34);
  });

  it('R15 wiring: Home floor starts with the prefetch; Results prefetches on [result]', () => {
    const home = readSrc('src/screens/HomeScreen.tsx');
    expect(home).toMatch(
      /const navigateToResultsWithFloor = useCallback\(\s*\(result: any\) => \{\s*prefetchProductImages\(result\);/
    );
    expect(home).toMatch(/import \{[^}]*\bprefetchProductImages\b[^}]*\} from '\.\.\/services\/imagePrefetch';/);
    const results = readSrc('src/screens/ResultsScreen.tsx');
    expect(results).toMatch(
      /useEffect\(\(\) => \{\s*prefetchProductImages\(result\);\s*\}, \[result\]\);/
    );
    expect(results).toMatch(/import \{[^}]*\bprefetchProductImages\b[^}]*\} from '\.\.\/services\/imagePrefetch';/);
  });
});
