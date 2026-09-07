/**
 * A18 — Results-route param contract fence.
 *
 * THE BUG THIS EXISTS FOR
 * The Home Smart-pick "View verdict" CTA and the Profile recent-decisions
 * marquee both navigated to Results with `{ from_history: <id> }`. That key
 * is not declared on `RootStackParamList.Results` and ResultsScreen never
 * destructures it, so on both surfaces:
 *
 *   result        = undefined   (no route.params.result)
 *   loadingResult = false       (needs comparison_id OR vision_products)
 *   the fetch effect returns immediately (`if (!comparisonId ...) return`)
 *   loadError     = null
 *   -> falls through to `if (!result || loadError)` -> results-empty-state
 *
 * i.e. 100% of taps on the two surfaces that exist to re-engage returning
 * users dead-ended on "No comparison loaded". Two type escape hatches hid
 * it: HomeScreen double-cast (`'Results' as any`, `as any`) and
 * ProfileScreen's `navigation: any` prop, so `tsc` stayed green.
 *
 * WHY A SOURCE FENCE AND NOT A RENDER TEST
 * ResultsScreen is not rendered anywhere in this suite — it needs the whole
 * Reanimated entering-animation surface plus ~9 service mocks, so the
 * established convention (ResultsScreen.historyDetailFetch / .timeout /
 * .redesign) asserts its wiring at the source level. The BEHAVIOURAL half —
 * what the two entry points actually pass — is pinned by rendering the real
 * screens in HomeScreen.bundleE.s3.integration and
 * ProfileScreen.bundleE.s3.integration. This file closes the loop: every
 * Results navigate payload in the app must consist only of keys the route
 * declares AND ResultsScreen reads, so the next invented param fails here
 * rather than on a user's phone.
 */

import * as fs from 'fs';
import * as path from 'path';

const SRC_DIR = path.resolve(__dirname, '../src');
const RESULTS_SRC = fs.readFileSync(
  path.join(SRC_DIR, 'screens/ResultsScreen.tsx'),
  'utf8'
);
const TYPES_SRC = fs.readFileSync(path.join(SRC_DIR, 'types/types.ts'), 'utf8');

/**
 * Drop whole-line `//` comments so a guard greps CODE, not prose. Only
 * lines that are ENTIRELY a comment are removed, so a `//` inside a string
 * (a URL, say) can never truncate real code.
 */
function stripCommentLines(source: string): string {
  return source
    .split('\n')
    .filter((line) => !line.trim().startsWith('//'))
    .join('\n');
}

/** Every .ts/.tsx file under src/. */
function walk(dir: string, acc: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, acc);
    else if (/\.tsx?$/.test(entry.name)) acc.push(full);
  }
  return acc;
}

/** Top-level keys of an object literal body (shorthand + `key:` forms). */
function topLevelKeys(body: string): string[] {
  const segments: string[] = [];
  let depth = 0;
  let current = '';
  for (const ch of body) {
    if (ch === '{' || ch === '(' || ch === '[') depth++;
    else if (ch === '}' || ch === ')' || ch === ']') depth--;
    if (ch === ',' && depth === 0) {
      segments.push(current);
      current = '';
    } else {
      current += ch;
    }
  }
  segments.push(current);

  const keys: string[] = [];
  for (const seg of segments) {
    const trimmed = seg.replace(/\/\/[^\n]*/g, '').trim();
    if (!trimmed) continue;
    const m = trimmed.match(/^([A-Za-z_$][\w$]*)\s*(?::|$)/);
    if (m) keys.push(m[1]);
  }
  return keys;
}

type NavSite = { file: string; keys: string[] };

/** Every `navigation.navigate('Results', { ... })` with an inline payload. */
function resultsNavSites(): NavSite[] {
  const sites: NavSite[] = [];
  for (const file of walk(SRC_DIR)) {
    const source = fs.readFileSync(file, 'utf8');
    const re = /navigation\.navigate\(\s*['"]Results['"](?:\s+as\s+any)?\s*,\s*/g;
    let match: RegExpExecArray | null;
    while ((match = re.exec(source)) !== null) {
      const start = match.index + match[0].length;
      if (source[start] !== '{') continue;
      let depth = 0;
      let end = start;
      for (; end < source.length; end++) {
        if (source[end] === '{') depth++;
        else if (source[end] === '}') {
          depth--;
          if (depth === 0) break;
        }
      }
      sites.push({
        file: path.relative(SRC_DIR, file).replace(/\\/g, '/'),
        keys: topLevelKeys(source.slice(start + 1, end)),
      });
    }
  }
  return sites;
}

/** Keys declared on RootStackParamList.Results. */
function declaredResultsParams(): string[] {
  const block = TYPES_SRC.match(/\n\s*Results:\s*\{([\s\S]*?)\n\s*\};/);
  if (!block) return [];
  return Array.from(block[1].matchAll(/^\s*([A-Za-z_$][\w$]*)\??\s*:/gm)).map(
    (m) => m[1]
  );
}

/** Keys ResultsScreen actually reads off route.params. */
function consumedResultsParams(): string[] {
  return Array.from(
    new Set(
      Array.from(
        RESULTS_SRC.matchAll(/route\??\.params\??\.([A-Za-z_$][\w$]*)/g)
      ).map((m) => m[1])
    )
  );
}

describe('Results route param contract (A18)', () => {
  const sites = resultsNavSites();
  const declared = declaredResultsParams();
  const consumed = consumedResultsParams();

  // Positive controls — without these, a regex that silently stops
  // matching would turn every assertion below into a vacuous pass.
  it('finds the Results navigate call sites and the route declaration', () => {
    expect(sites.length).toBeGreaterThanOrEqual(6);
    expect(sites.every((s) => s.keys.length > 0)).toBe(true);
    expect(declared.sort()).toEqual([
      'comparison_id',
      'result',
      'vision_products',
    ]);
    expect(consumed).toEqual(expect.arrayContaining(declared));
  });

  it('every Results navigate passes only DECLARED route params', () => {
    const offenders = sites.filter((s) =>
      s.keys.some((k) => !declared.includes(k))
    );
    expect(
      offenders.map((o) => `${o.file}: {${o.keys.join(', ')}}`)
    ).toEqual([]);
  });

  it('every Results navigate passes only params ResultsScreen READS', () => {
    // Declaring a key is not enough — an undeclared-but-read key would
    // still work, and a declared-but-unread key would still dead-end on
    // the empty state. This is the assertion A18 actually violated.
    const offenders = sites.filter((s) =>
      s.keys.some((k) => !consumed.includes(k))
    );
    expect(
      offenders.map((o) => `${o.file}: {${o.keys.join(', ')}}`)
    ).toEqual([]);
  });

  it('the two A18 re-open surfaces pass comparison_id', () => {
    const home = sites.filter((s) => s.file === 'screens/HomeScreen.tsx');
    const profile = sites.filter((s) => s.file === 'screens/ProfileScreen.tsx');
    expect(home.some((s) => s.keys.includes('comparison_id'))).toBe(true);
    expect(profile.some((s) => s.keys.includes('comparison_id'))).toBe(true);
  });

  it('the dead `from_history` param is gone from src/ code entirely', () => {
    const hits = walk(SRC_DIR)
      .filter((f) =>
        stripCommentLines(fs.readFileSync(f, 'utf8')).includes('from_history')
      )
      .map((f) => path.relative(SRC_DIR, f).replace(/\\/g, '/'));
    expect(hits).toEqual([]);
  });
});

describe('ResultsScreen — comparison_id takes the loading path, not the empty state (A18)', () => {
  it('seeds loadingResult from comparison_id (so it never falls straight through)', () => {
    // `loadingResult` true => the `results-loading-state` early return wins
    // over the `if (!result || loadError)` empty state below it.
    expect(RESULTS_SRC).toMatch(
      /setLoadingResult|useState<boolean>\(\s*\n?\s*!route\?\.params\?\.result\s*&&\s*\n?\s*!!\(route\?\.params\?\.comparison_id\s*\|\|\s*route\?\.params\?\.vision_products\)/
    );
    expect(RESULTS_SRC).toMatch(/route\?\.params\?\.comparison_id\s*\|\|\s*route\?\.params\?\.vision_products/);
  });

  it('fetches the payload with getComparison(comparison_id)', () => {
    expect(RESULTS_SRC).toMatch(
      /const comparisonId = route\?\.params\?\.comparison_id;[\s\S]{0,400}getComparison\(comparisonId\)/
    );
  });

  it('renders results-loading-state before the empty-state guard', () => {
    const loadingIdx = RESULTS_SRC.indexOf('testID="results-loading-state"');
    const emptyIdx = RESULTS_SRC.indexOf('testID="results-empty-state"');
    expect(loadingIdx).toBeGreaterThan(-1);
    expect(emptyIdx).toBeGreaterThan(-1);
    expect(loadingIdx).toBeLessThan(emptyIdx);
  });
});
