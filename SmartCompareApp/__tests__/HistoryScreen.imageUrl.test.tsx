/**
 * Bundle E S3 A4 Wave 2 — HistoryScreen image_url integration.
 *
 * A2 left placeholder Views at four testIDs (2 hero marquee tiles + 2
 * per-row VS tiles per row). A4 swaps them for <ProductImage> consuming:
 *   - per-row tiles: from item.full_response.products[i].image_url (saved
 *     by A3's deploy on fresh comparisons)
 *   - hero marquee: from RecentDecisionItem if backend surfaces images
 *     (placeholder otherwise — no backend extension required since this
 *     test pins forward-compatibility, not data plumbing)
 *
 * SOURCE-GREP CONTRACT TEST. HistoryScreen depends on React Navigation +
 * authService + 5+ api modules — render-tree integration tests on it tend
 * to be brittle (same pattern A1 hit). Per `memory/feedback_snapshots_as_
 * staleness_liability.md` source-grep contract tests encode INTENT
 * robustly for these screen-shaped tests.
 *
 * The renderable proof is covered by the ProductImage primitive's own 17
 * tests (commit 0b4f463) — this suite just pins the wiring.
 */

import * as fs from 'fs';
import * as path from 'path';

const HISTORY_PATH = path.resolve(__dirname, '../src/screens/HistoryScreen.tsx');

let historySrc: string;

beforeAll(() => {
  historySrc = fs.readFileSync(HISTORY_PATH, 'utf8');
});

describe('HistoryScreen — image_url wired via ProductImage primitive', () => {
  it('imports ProductImage primitive', () => {
    expect(historySrc).toMatch(
      /from\s+['"](?:\.\.\/)+components\/primitives\/ProductImage['"]/
    );
  });

  it('renders ProductImage at history-row-{id}-block-a-image-slot', () => {
    // ProductImage testID prop + the row-block-a testID base
    expect(historySrc).toMatch(
      /<ProductImage[\s\S]*?testID=\{`history-row-\$\{item\.id\}-block-a-image-slot`\}/
    );
  });

  it('renders ProductImage at history-row-{id}-block-b-image-slot', () => {
    expect(historySrc).toMatch(
      /<ProductImage[\s\S]*?testID=\{`history-row-\$\{item\.id\}-block-b-image-slot`\}/
    );
  });

  it('renders ProductImage at history-hero-card-image-slot-a', () => {
    expect(historySrc).toMatch(
      /<ProductImage[\s\S]*?testID="history-hero-card-image-slot-a"/
    );
  });

  it('renders ProductImage at history-hero-card-image-slot-b', () => {
    expect(historySrc).toMatch(
      /<ProductImage[\s\S]*?testID="history-hero-card-image-slot-b"/
    );
  });

  it('passes per-product image_url from full_response.products[i].image_url', () => {
    // The row consumer pulls image_url from item.full_response.products[i].image_url
    // via a helper or inline access. The contract is: SOME read from products
    // index 0/1's image_url makes it onto the ProductImage prop.
    expect(historySrc).toMatch(/full_response[\s\S]{0,200}?image_url/);
  });

  it('forwards tone color to ProductImage placeholderTone for row tiles', () => {
    // Per JSX HistoryScreen.jsx:226-233 placeholder tone matches per-row
    // tone palette (toneA / toneB derived from product name).
    expect(historySrc).toMatch(/placeholderTone=\{toneA\}/);
    expect(historySrc).toMatch(/placeholderTone=\{toneB\}/);
  });

  it('uses aspectRatio 1 (square tile) for ProductImage', () => {
    // Both row + hero ProductImage instances should pass aspectRatio={1}
    const matches = historySrc.match(/<ProductImage[\s\S]*?aspectRatio=\{1\}/g);
    expect(matches).toBeTruthy();
    expect(matches!.length).toBeGreaterThanOrEqual(4); // 2 row + 2 hero
  });

  it('does NOT introduce raw <Image source= for product slots (single-source-of-truth)', () => {
    // ProductImage is the only image rendering — no raw <Image source={{uri ...}}/>
    // inside the row or hero blocks. (Avatar/logo Image elsewhere is fine.)
    const rowSection = historySrc
      .split(/history-row-.*?-block-a-image-slot/)[1]
      ?.split(/history-row-.*?-block-b-image-slot/)[0] ?? '';
    expect(rowSection).not.toMatch(/<Image\s+source/);
  });
});
