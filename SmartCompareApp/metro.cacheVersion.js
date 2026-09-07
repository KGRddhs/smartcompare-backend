const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

/**
 * Transform-cache key inputs Metro does NOT key on itself (P-B1-CACHE).
 *
 * Metro's transform cache key is
 * `sha1("metro-cache", metroVersion, config.cacheVersion, <hash of the
 * transformer module files>, transformerKey, globalPrefix)`
 * (metro/src/DeltaBundler/getTransformCacheKey.js) and the cache itself is a
 * FileStore rooted at `os.tmpdir()/metro-cache` — machine-global, shared by
 * every project and every worktree on the box.
 *
 * Nothing in that key covers `babel.config.js`, and `@expo/metro-config`'s
 * babel transformer implements no `getCacheKey`. So a change to our babel
 * config — the two local plugins in babel.config.js are what strip production
 * `console.*` (M13-55) and split the lucide barrel import (B1, -1,749,282 B) —
 * is invisible to the cache: a machine whose %TEMP%\metro-cache predates the
 * change keeps serving the pre-change transform output, and `eas update` /
 * `expo export` silently ship the OLD bundle. Measured in this worktree before
 * this file existed: replacing babel.config.js with its pre-B1 content and
 * exporting without `-c` still produced a byte-identical 2196-module bundle.
 *
 * Folding a content hash of those inputs into `cacheVersion` makes ANY change
 * to them invalidate the transform cache on EVERY machine, so the ship path
 * can no longer disagree with the source tree.
 *
 * Inputs:
 *  - `babel.config.js` — the transform itself.
 *  - lucide's ESM barrel — babel.config.js's `buildLucideIconMap()` parses
 *    `dist/esm/lucide-react-native.mjs` at transform time to build the
 *    icon-name -> icon-file map it rewrites imports to. The barrel's content
 *    hash subsumes the package version (and also catches a patched install,
 *    which a version string would not).
 */

const LUCIDE_PACKAGE = 'lucide-react-native';

/**
 * Mirrors `lucideEsmDir()` in babel.config.js so we hash exactly the file the
 * plugin reads: in-project node_modules first, Node resolution as the fallback
 * for hoisted installs. Returns null when lucide is not installed.
 */
function lucideBarrelPath(projectRoot) {
  const local = path.join(
    projectRoot,
    'node_modules',
    LUCIDE_PACKAGE,
    'dist',
    'esm',
    'lucide-react-native.mjs'
  );
  if (fs.existsSync(local)) return local;
  try {
    // "." resolves to dist/cjs/lucide-react-native.js via the exports map.
    const main = require.resolve(LUCIDE_PACKAGE, { paths: [projectRoot] });
    return path.join(path.dirname(main), '..', 'esm', 'lucide-react-native.mjs');
  } catch {
    return null;
  }
}

const TRANSFORM_INPUTS = [
  {
    label: 'babel.config.js',
    locate: (projectRoot) => path.join(projectRoot, 'babel.config.js'),
  },
  {
    label: 'lucide-esm-barrel',
    locate: lucideBarrelPath,
  },
];

/**
 * Content hash of one input. Both inputs are JS source, so we read them as text
 * and normalize CRLF -> LF first: `core.autocrlf=true` checkouts differ from LF
 * checkouts in every line ending, and that difference cannot change what babel
 * emits — normalizing keeps the key stable across checkout styles instead of
 * forcing a cold rebuild on every Windows clone. Any other edit (a space, a
 * character, a reordered plugin) still moves the hash.
 */
function hashFile(absPath) {
  if (!absPath) return 'unresolved';
  try {
    return crypto
      .createHash('sha256')
      .update(fs.readFileSync(absPath, 'utf8').replace(/\r\n/g, '\n'))
      .digest('hex');
  } catch {
    // A missing input must still produce a stable key, not a crash: metro.config.js
    // is loaded by every expo command, including ones that never bundle.
    return 'absent';
  }
}

/**
 * The exact string the key is a hash of. JSON so the label/hash boundary is
 * unambiguous and the value is reproducible by hand from the files on disk.
 *
 * @param {string} projectRoot absolute path to SmartCompareApp/
 * @returns {string}
 */
function transformInputsFingerprint(projectRoot) {
  return JSON.stringify(
    TRANSFORM_INPUTS.map((input) => [input.label, hashFile(input.locate(projectRoot))])
  );
}

/**
 * @param {string} projectRoot absolute path to SmartCompareApp/
 * @param {string} [baseVersion] the `cacheVersion` we are extending (metro's default is "1.0")
 * @returns {string} `<base>-qaren1-<16 hex>`
 */
function qarenCacheVersion(projectRoot, baseVersion) {
  const fingerprint = crypto
    .createHash('sha256')
    .update(transformInputsFingerprint(projectRoot))
    .digest('hex')
    .slice(0, 16);
  const base = baseVersion == null || baseVersion === '' ? '1.0' : String(baseVersion);
  return `${base}-qaren1-${fingerprint}`;
}

module.exports = {
  qarenCacheVersion,
  transformInputsFingerprint,
  TRANSFORM_INPUTS,
  lucideBarrelPath,
};
