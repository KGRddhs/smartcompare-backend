#!/usr/bin/env node
/**
 * Generates tests/fixtures/featurebucket_parity.json — the source-of-truth
 * fixture for the Python-vs-TypeScript djb2 parity test (RE-3).
 *
 * The TS djb2/hashBucket implementation lives in
 * SmartCompareApp/src/config/featureBucket.ts. We re-inline it here (NOT
 * `require()` the .ts file) so this generator stays a zero-dependency
 * Node script — no ts-node, no Expo runtime. The two implementations are
 * 4 lines each and divergence is caught by the parity test itself.
 *
 * Usage:
 *   node scripts/generate_feature_bucket_parity_fixture.js
 *
 * Outputs:
 *   tests/fixtures/featurebucket_parity.json
 *
 * Determinism: seeded RNG so a re-run produces an identical fixture.
 */

const fs = require('fs');
const path = require('path');

// --- TS implementation re-inlined verbatim from featureBucket.ts ---
function djb2(s) {
  let h = 5381;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  }
  return h >>> 0;
}

function hashBucket(id, percent) {
  if (!id) return false;
  if (percent <= 0) return false;
  if (percent >= 100) return true;
  return djb2(id) % 100 < percent;
}

// --- Fixture generation ---
// We sweep a wide range of (id, percent) shapes so the parity test catches
// regressions in: ASCII, Unicode, empty strings, numeric strings, UUID
// shapes, long strings, and the boundary percentages (0, 1, 99, 100).

const PERCENTS = [0, 1, 10, 25, 50, 75, 90, 99, 100];

function generateIds() {
  const ids = [];

  // 100 deterministic synthetic user-N-N ids.
  for (let i = 0; i < 100; i++) {
    ids.push(`user-${i}-${(i * 919) % 1000}`);
  }

  // UUID-shaped ids (deterministic — no Crypto.randomUUID, just hex).
  for (let i = 0; i < 5; i++) {
    const hex = (n) => n.toString(16).padStart(8, '0');
    ids.push(`${hex(i * 17)}-${hex(i * 23)}-${hex(i * 31)}-${hex(i * 37)}-${hex(i * 41)}${hex(i * 43)}`);
  }

  // Edge: single-char, empty would be falsy in hashBucket so skip it
  // (the empty-id branch is exercised by featureBucket.test.ts, not parity).
  ids.push('a', 'Z', '0', '!');

  // Unicode: Arabic + emoji to catch any char-code/byte mismatch.
  ids.push('مستخدم-1');
  ids.push('مستخدم-2');
  ids.push('cafe\u00e9');  // composed é
  ids.push('cafe\u0301');  // combining acute

  return ids;
}

function main() {
  const ids = generateIds();
  const cases = [];

  for (const id of ids) {
    for (const percent of PERCENTS) {
      cases.push({
        id,
        percent,
        expected: hashBucket(id, percent),
        hash: djb2(id),
      });
    }
  }

  const out = path.join(__dirname, '..', 'tests', 'fixtures', 'featurebucket_parity.json');
  fs.writeFileSync(out, JSON.stringify(cases));
  console.log(`Wrote ${cases.length} cases to ${out}`);
}

main();
