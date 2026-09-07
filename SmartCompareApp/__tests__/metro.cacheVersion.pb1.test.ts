/**
 * P-B1-CACHE — Metro's transform cache must be keyed on babel.config.js.
 *
 * Metro's transform-cache key is built by
 * `metro/src/DeltaBundler/getTransformCacheKey.js` from the metro version,
 * `config.cacheVersion`, the transformer module files and the transformer
 * config — and nothing else. `@expo/metro-config`'s babel transformer
 * implements no `getCacheKey`, so **babel.config.js is not in the key**, while
 * the cache itself is a FileStore rooted at `os.tmpdir()/metro-cache`:
 * machine-global and shared by every project and worktree on the box.
 *
 * That made B1's saving invisible to the ship path. Measured in this worktree
 * before metro.config.js existed: replacing babel.config.js with its pre-B1
 * content (no lucide splitter) and running `expo export --platform ios`
 * WITHOUT `-c` still emitted `2196 modules` / 6,518,432 B — byte-identical to
 * the plugin-ON build, from cache. `eas update` has no cache clear either, and
 * CI never bundles, so nothing anywhere would have noticed a box whose
 * %TEMP%\metro-cache predated the babel change shipping the OLD bundle.
 *
 * metro.config.js now folds a content hash of the transform inputs Metro
 * ignores into `cacheVersion`. Re-measured with the fix, same warm cache, no
 * `-c`: pre-B1 babel.config.js -> `3836 modules` / 8,267,689 B, HEAD
 * babel.config.js -> `2196 modules` / 6,518,433 B, and a no-change re-run is a
 * 6.5s cache hit vs a 14.2s cold transform.
 *
 * What this suite pins:
 *   1. metro.config.js actually wires the computed version into
 *      `config.cacheVersion` (deleting that line turns the key back into the
 *      stock "1.0" and this goes red).
 *   2. The key MOVES for any content edit to babel.config.js — down to one
 *      space — and is otherwise deterministic.
 *   3. The lucide ESM barrel (the icon map the B1 plugin parses at transform
 *      time) is folded in too.
 *   4. A comment-stripped source fence, with a positive control, that the
 *      wiring is real code and not commentary.
 */

import * as crypto from 'crypto';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

const {
  qarenCacheVersion,
  transformInputsFingerprint,
  TRANSFORM_INPUTS,
} = require('../metro.cacheVersion.js') as {
  qarenCacheVersion: (projectRoot: string, baseVersion?: string) => string;
  transformInputsFingerprint: (projectRoot: string) => string;
  TRANSFORM_INPUTS: Array<{ label: string; locate: (root: string) => string | null }>;
};

const APP_ROOT = path.resolve(__dirname, '..');

/** Metro's own default, `metro-config/src/defaults/index.js`. */
const STOCK_CACHE_VERSION = '1.0';

const LUCIDE_BARREL_REL = path.join(
  'node_modules',
  'lucide-react-native',
  'dist',
  'esm',
  'lucide-react-native.mjs'
);

const fixtures: string[] = [];

function makeFixture(): string {
  // A plain temp directory containing only regular files we create here — no
  // symlinks or junctions, so the recursive cleanup below can never follow one
  // out of the fixture.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'qaren-pb1-'));
  fixtures.push(dir);
  return dir;
}

function writeFixtureFile(dir: string, relPath: string, contents: string): void {
  const abs = path.join(dir, relPath);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, contents, 'utf8');
}

afterAll(() => {
  for (const dir of fixtures) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

/**
 * Comment-aware source stripper for the static fence at the bottom: a fence
 * that matched commentary would keep passing after the code was deleted.
 * String literals are preserved; `//` and block-comment runs are dropped.
 */
function stripComments(src: string): string {
  let out = '';
  let quote: string | null = null;
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    const next = src[i + 1];
    if (quote) {
      out += c;
      if (c === '\\') {
        out += next ?? '';
        i += 2;
        continue;
      }
      if (c === quote) quote = null;
      i += 1;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') {
      quote = c;
      out += c;
      i += 1;
      continue;
    }
    if (c === '/' && next === '/') {
      while (i < src.length && src[i] !== '\n') i += 1;
      continue;
    }
    if (c === '/' && next === '*') {
      i += 2;
      while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) i += 1;
      i += 2;
      continue;
    }
    out += c;
    i += 1;
  }
  return out;
}

describe('P-B1-CACHE: metro.config.js keys the transform cache on babel.config.js', () => {
  it('wires the computed version into config.cacheVersion', () => {
    // Loading the real config also proves it is a valid Expo metro config: it
    // is what `expo export` / `eas update` will evaluate.
    const config = require('../metro.config.js');

    expect(typeof config.cacheVersion).toBe('string');
    expect(config.cacheVersion).not.toBe(STOCK_CACHE_VERSION);
    expect(config.cacheVersion).toMatch(/^1\.0-qaren1-[0-9a-f]{16}$/);
    // The exact value, recomputed here from the files on disk — so an edit to
    // babel.config.js that the config did not pick up fails this.
    expect(config.cacheVersion).toBe(qarenCacheVersion(APP_ROOT, STOCK_CACHE_VERSION));

    // Sanity: the stock Expo config really does leave cacheVersion at "1.0",
    // i.e. the assertion above is not vacuously true.
    const {
      getDefaultConfig,
    } = require('expo/metro-config') as { getDefaultConfig: (root: string) => any };
    expect(getDefaultConfig(APP_ROOT).cacheVersion).toBe(STOCK_CACHE_VERSION);
  }, 120000);

  it('names babel.config.js as a transform input', () => {
    const labels = TRANSFORM_INPUTS.map((input) => input.label);
    expect(labels).toContain('babel.config.js');
    expect(TRANSFORM_INPUTS.length).toBeGreaterThan(0);

    const located = TRANSFORM_INPUTS.find((i) => i.label === 'babel.config.js')!.locate(APP_ROOT);
    expect(located).toBe(path.join(APP_ROOT, 'babel.config.js'));
    expect(fs.existsSync(located as string)).toBe(true);
  });

  it('moves the key when babel.config.js content changes — down to one space', () => {
    const dir = makeFixture();
    const original = fs.readFileSync(path.join(APP_ROOT, 'babel.config.js'), 'utf8');
    writeFixtureFile(dir, 'babel.config.js', original);

    const before = qarenCacheVersion(dir, STOCK_CACHE_VERSION);

    // The real edit shape this defends against: the B1 plugin is removed.
    writeFixtureFile(dir, 'babel.config.js', original.replace(/lucideIconImportsPlugin/g, 'x'));
    const withoutPlugin = qarenCacheVersion(dir, STOCK_CACHE_VERSION);
    expect(withoutPlugin).not.toBe(before);

    // One extra space, nothing else.
    writeFixtureFile(dir, 'babel.config.js', original.replace('const fs =', 'const  fs ='));
    const oneSpace = qarenCacheVersion(dir, STOCK_CACHE_VERSION);
    expect(oneSpace).not.toBe(before);

    // ...and it comes back, so the key is content-derived, not time- or
    // run-derived (a key that churned would cold-rebuild on every export).
    writeFixtureFile(dir, 'babel.config.js', original);
    expect(qarenCacheVersion(dir, STOCK_CACHE_VERSION)).toBe(before);
  });

  it('treats a CRLF checkout of the same babel.config.js as unchanged', () => {
    const dir = makeFixture();
    const lf = "module.exports = function () {\n  return { presets: [] };\n};\n";
    writeFixtureFile(dir, 'babel.config.js', lf);
    const lfVersion = qarenCacheVersion(dir, STOCK_CACHE_VERSION);

    writeFixtureFile(dir, 'babel.config.js', lf.replace(/\n/g, '\r\n'));
    // core.autocrlf=true is set on this repo; a smudged checkout must not
    // invalidate every machine's cache for a difference babel cannot see.
    expect(qarenCacheVersion(dir, STOCK_CACHE_VERSION)).toBe(lfVersion);
  });

  it('folds in the lucide ESM barrel the B1 plugin parses', () => {
    const dir = makeFixture();
    writeFixtureFile(dir, 'babel.config.js', '// same in both\n');
    writeFixtureFile(
      dir,
      LUCIDE_BARREL_REL,
      "export { default as Camera } from './icons/camera.mjs';\n"
    );
    const before = qarenCacheVersion(dir, STOCK_CACHE_VERSION);

    writeFixtureFile(
      dir,
      LUCIDE_BARREL_REL,
      "export { default as Camera } from './icons/camera-renamed.mjs';\n"
    );
    expect(qarenCacheVersion(dir, STOCK_CACHE_VERSION)).not.toBe(before);
  });

  it('composes with the base version and never throws on a missing input', () => {
    const dir = makeFixture();
    // No babel.config.js at all: metro.config.js is loaded by every expo
    // command, including ones that never bundle, so this must not throw.
    const missing = qarenCacheVersion(dir, STOCK_CACHE_VERSION);
    expect(missing).toMatch(/^1\.0-qaren1-[0-9a-f]{16}$/);

    writeFixtureFile(dir, 'babel.config.js', '// present\n');
    const present = qarenCacheVersion(dir, STOCK_CACHE_VERSION);
    expect(present).not.toBe(missing);

    // A future metro/expo default other than "1.0" must survive into the key.
    expect(qarenCacheVersion(dir, '2.0')).toBe(present.replace(/^1\.0-/, '2.0-'));
    expect(qarenCacheVersion(dir, '2.0')).not.toBe(present);
  });

  it('hashes the same bytes babel reads (no accidental double-encoding)', () => {
    const dir = makeFixture();
    const babelBody = '// exactly these bytes\n';
    const barrelBody = "export { default as Camera } from './icons/camera.mjs';\n";
    writeFixtureFile(dir, 'babel.config.js', babelBody);
    // Written into the fixture so the in-project branch of lucideBarrelPath()
    // is taken and the expectation below is exact in any environment.
    writeFixtureFile(dir, LUCIDE_BARREL_REL, barrelBody);

    const sha = (s: string) => crypto.createHash('sha256').update(s).digest('hex');
    const fingerprint = JSON.stringify([
      ['babel.config.js', sha(babelBody)],
      ['lucide-esm-barrel', sha(barrelBody)],
    ]);
    expect(transformInputsFingerprint(dir)).toBe(fingerprint);

    const expected = crypto.createHash('sha256').update(fingerprint).digest('hex').slice(0, 16);
    expect(qarenCacheVersion(dir, STOCK_CACHE_VERSION)).toBe(`1.0-qaren1-${expected}`);
  });

  it('static fence: the cacheVersion assignment is real code, not a comment', () => {
    const raw = fs.readFileSync(path.join(APP_ROOT, 'metro.config.js'), 'utf8');
    const src = stripComments(raw);

    // Positive control: the file does carry commentary explaining the fix, and
    // the stripper removed it while keeping the code.
    expect(raw).toContain('P-B1-CACHE');
    expect(src).not.toContain('P-B1-CACHE');
    expect(src).toContain("require('expo/metro-config')");

    const assignments = src.match(/config\.cacheVersion\s*=\s*qarenCacheVersion\(/g) ?? [];
    expect(assignments.length).toBe(1);
    expect(src).toContain("require('./metro.cacheVersion')");
    expect(src).toContain('module.exports = config');
  });
});
