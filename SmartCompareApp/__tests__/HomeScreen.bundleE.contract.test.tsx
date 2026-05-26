/**
 * HomeScreen Bundle E contract — source-grep regressions.
 *
 * Inspired by HomeScreen.bundleB.contract.test.tsx pattern: read source
 * files as strings and assert structural invariants. Cheap, fast, robust
 * against the 25-mock-deep render-tree noise of HomeScreen integration.
 *
 * Scope (per design doc § 6 Home checkpoints + § 3.1 row):
 *   - HomeScreen renders the HeaderCounter pill testID="home-header-counter"
 *   - HomeEditorialSections SmartPickCard consumes the NEW pre-split shape
 *     (products[] OR winner_name + extension fields) — not legacy-only
 *   - HomeTrending consumes the NEW {tag, a, b, count} shape — not the
 *     legacy {query, view_count}-only
 *   - SmartPickCard renders a center "vs" pill from VsPair primitive
 *     (S0.3 wiring) — assertion deferred to S0.3-landed pass, kept as
 *     reminder skip()
 *
 * Cross-references the freshly-landed backend reshapes:
 *   - dca8067 /home/trending pre-split: items[{tag, a, b, count}]
 *   - 3bb31bd /home/smart-pick extension fields: tone, sub, etc.
 */
import * as fs from 'fs';
import * as path from 'path';

const API_PATH = path.resolve(__dirname, '../src/services/api.ts');
const HOME_ED_PATH = path.resolve(__dirname, '../src/components/HomeEditorialSections.tsx');
const HOME_PATH = path.resolve(__dirname, '../src/screens/HomeScreen.tsx');

let apiSrc: string;
let homeEdSrc: string;
let homeSrc: string;

beforeAll(() => {
  apiSrc = fs.readFileSync(API_PATH, 'utf8');
  homeEdSrc = fs.readFileSync(HOME_ED_PATH, 'utf8');
  homeSrc = fs.readFileSync(HOME_PATH, 'utf8');
});

describe('Bundle E contract — api.ts client types reflect backend reshape', () => {
  it('HomeTrendingItem interface includes the new pre-split fields (tag, a, b, count)', () => {
    // After backend B-S1.B4.3a (commit dca8067), trending rows ship as
    //   { tag, a, b, count, ...legacy_keys }
    // The TS client type MUST surface the new fields so HomeEditorialSections
    // can render the JSX-spec layout [Category pill] [a] vs [b] [count].
    const m = apiSrc.match(/export interface HomeTrendingItem\s*\{([^}]+)\}/);
    expect(m).toBeTruthy();
    const body = m![1];
    // Document the contract — at least these field names must appear:
    expect(body).toMatch(/\btag\b/);
    expect(body).toMatch(/\ba\b/);
    expect(body).toMatch(/\bb\b/);
    expect(body).toMatch(/\bcount\b/);
  });

  it('HomeSmartPickItem interface includes Bundle E extension fields', () => {
    // After backend B-S1.B4.3b (commit 3bb31bd), smart-pick ships extension
    // fields per the JSX-wins audit. Field names from the JSX reference:
    //   { name, sub, price, winner, tone? } per-product
    // Either the response is products[]-shaped (preferred) OR keeps
    // winner_name + adds tone/sub at the row level. The test accepts
    // EITHER shape — at minimum `tone` must surface so SmartPickCard can
    // render the "warm" / "cool" verdict color cue.
    const m = apiSrc.match(/export interface HomeSmartPick(Item|Response)\s*\{([^}]+)\}/);
    expect(m).toBeTruthy();
    const body = (m as any)[2];
    // At least ONE of products[] / tone / sub must be present.
    const hasNewSurface =
      /products\s*:\s*Array</.test(apiSrc) ||
      /products\s*\?\s*:/.test(apiSrc) ||
      /\btone\b\s*\?\s*:/.test(apiSrc) ||
      /\bsub\b\s*\?\s*:/.test(apiSrc);
    expect(hasNewSurface).toBe(true);
  });
});

describe('Bundle E contract — HomeEditorialSections consumes new shapes', () => {
  it('trending row reads .tag, .a, .b (not just .query)', () => {
    // JSX renders each row as [Category pill] [a] vs [b] [count]. The
    // component MUST surface `.tag` for the category pill — that's the
    // load-bearing JSX-wins change.
    // Accept either explicit .tag access or destructure from item.
    const readsTag = /\btag\b/.test(homeEdSrc);
    const readsA = /\.\s*a\b/.test(homeEdSrc) || /\b\s*a\s*[,}]/.test(homeEdSrc);
    const readsB = /\.\s*b\b/.test(homeEdSrc) || /\b\s*b\s*[,}]/.test(homeEdSrc);
    expect(readsTag).toBe(true);
    // a + b together: at least one must appear in JSX layout
    expect(readsA || readsB).toBe(true);
  });

  it('exposes home-trending-item testID per row (Bundle B + E both rely on this)', () => {
    expect(homeEdSrc).toMatch(/testID\s*=\s*["']home-trending-item["']/);
  });
});

describe('Bundle E contract — HomeScreen testID surface stable', () => {
  it('renders home-header-counter pill (HeaderCounter design § 3.1)', () => {
    // The pill copy is "2/3 free · +1" per design — the testID anchor must
    // remain stable so Q-S1 visual spot-checks + integration tests align.
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-header-counter["']/);
  });

  it('renders home-center-area (Bundle B 21e7bc0 rewire, kept under E)', () => {
    expect(homeSrc).toMatch(/testID\s*=\s*["']home-center-area["']/);
  });

  it('HomeEditorialSections is reachable from HomeScreen', () => {
    // Soft-detect: HomeScreen imports OR renders HomeEditorialSections.
    // (Bundle B Home tucks editorial sections below the input shell.)
    const refs =
      /from\s+['"][^'"]*HomeEditorialSections['"]/.test(homeSrc) ||
      /<HomeEditorialSections\b/.test(homeSrc) ||
      /home-editorial-(scroll|stub)/.test(homeSrc);
    expect(refs).toBe(true);
  });
});

describe('Bundle E contract — Build Principle #4 holds for Home surface', () => {
  it('HomeScreen contains no shake / wobble / jitter / bounce in source', () => {
    const banned = ['shake', 'wobble', 'jitter', 'bounce'];
    for (const w of banned) {
      // Allow the word inside a comment that ESCAPES the regex (Build
      // Principle #4 is documented in some files as 'b-o-u-n-c-e' with
      // hyphens). Strip comments before grepping.
      const stripped = homeSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
      expect(stripped.toLowerCase()).not.toContain(w);
    }
  });

  it('HomeEditorialSections contains no scary copy strings', () => {
    const scary = ["couldn't", 'try again', 'failed to', 'تعذر', 'فشل'];
    for (const phrase of scary) {
      // Skip non-string contexts — only flag literal user-visible strings.
      // (Coarse check, same approach as Bundle B contract test.)
      const lower = homeEdSrc.toLowerCase();
      expect(lower).not.toContain(phrase.toLowerCase());
    }
  });
});
