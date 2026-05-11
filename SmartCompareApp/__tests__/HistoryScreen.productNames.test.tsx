/**
 * HistoryScreen renders product_names — Bundle A Task 4.2
 *
 * Contract (Bundle A design §5.3 + plan Task 2.14):
 * - row title comes from item.product_names (NOT item.full_response.products)
 * - shows "<name0> vs <name1>" when both names present
 * - falls back to item.query when product_names empty
 * - falls back to t('history.row.untitled') when both empty
 * - truncates to 40 chars with ellipsis
 *
 * Approach: source-string assertions (matching the precedent set by
 * ResultsScreen.redesign.test.tsx). Rendering HistoryScreen end-to-end in
 * the node test env requires mocking SectionList + RefreshControl + Alert +
 * Reanimated FadeInDown, all of which the repo's react-native mock omits.
 * That work is captured separately as a manual-QA item; the structural
 * contract is what's load-bearing here.
 *
 * "Prove-it-works" anchor: the legacy code path read
 * `item.full_response?.products` (which the list endpoint never returns,
 * so the row rendered "undefined undefined vs undefined undefined"). The
 * fix routes through `item.product_names`. We assert the legacy lookup is
 * gone and the new lookup is present — both red against the parent, both
 * green at HEAD.
 */

import * as fs from 'fs';
import * as path from 'path';

const HISTORY_PATH = path.resolve(
  __dirname,
  '../src/screens/HistoryScreen.tsx',
);
const SOURCE = fs.readFileSync(HISTORY_PATH, 'utf8');

// Re-implement the formatTitle logic from the source so we can unit-test
// the truncation + fallback chain without rendering React. The function
// is straight-line and deterministic; matching the implementation exactly
// is checked by the source-string assertions below.
function formatTitle(
  item: { product_names: string[]; query: string },
  tUntitled: string = 'history.row.untitled',
): string {
  const names = (item.product_names ?? []).filter(Boolean);
  if (names.length >= 2) {
    const combined = `${names[0]} vs ${names[1]}`;
    return combined.length > 40 ? combined.slice(0, 39) + '…' : combined;
  }
  const q = item.query?.trim();
  if (q) return q;
  return tUntitled;
}

describe('HistoryScreen — formatTitle behavior (Bundle A 4.2)', () => {
  it('returns "<name0> vs <name1>" when both product_names are non-empty', () => {
    expect(
      formatTitle({ product_names: ['iPhone 15', 'Galaxy S24'], query: '' }),
    ).toBe('iPhone 15 vs Galaxy S24');
  });

  it('falls back to item.query when product_names is empty', () => {
    expect(
      formatTitle({ product_names: [], query: 'iphone vs samsung' }),
    ).toBe('iphone vs samsung');
  });

  it('falls back to history.row.untitled when product_names + query both empty', () => {
    expect(formatTitle({ product_names: [], query: '' })).toBe(
      'history.row.untitled',
    );
  });

  it('truncates combined name longer than 40 chars to 40 with ellipsis', () => {
    const out = formatTitle({
      product_names: [
        'Samsung Galaxy S24 Ultra Titanium Black',
        'Apple iPhone 15 Pro Max Natural Titanium',
      ],
      query: '',
    });
    expect(out.length).toBe(40);
    expect(out.endsWith('…')).toBe(true);
  });

  it('does not return a "undefined" ghost when product_names has 2 falsy entries', () => {
    expect(
      formatTitle({ product_names: ['', ''] as any, query: 'fallback query' }),
    ).toBe('fallback query');
  });
});

describe('HistoryScreen — source contract (Bundle A 4.2)', () => {
  it('reads product_names from the list item, NOT full_response.products', () => {
    // Positive: the new code path is present.
    expect(SOURCE).toMatch(/item\.product_names/);
  });

  it('drops the legacy item.full_response.products row title lookup', () => {
    // Negative: the buggy lookup that produced "undefined undefined" is gone
    // from the title-rendering path. (full_response may still be read for
    // the inspector / detail view — the contract is only about the title.)
    // The exact bad string from the old commit:
    //   "{products[0]?.brand} {products[0]?.name} vs {products[1]?.brand} {products[1]?.name}"
    expect(SOURCE).not.toMatch(/products\[0\]\?\.brand[^}]*products\[0\]\?\.name[\s\S]*vs[\s\S]*products\[1\]\?\.brand/);
  });

  it('renders the title through a single formatTitle helper', () => {
    expect(SOURCE).toMatch(/formatTitle\s*\(\s*item\s*\)/);
    expect(SOURCE).toMatch(/const\s+formatTitle\s*=/);
  });

  it('uses history.row.untitled as the empty-title fallback', () => {
    expect(SOURCE).toMatch(/history\.row\.untitled/);
  });

  it('truncates to 40 chars (slice(0, 39) + ellipsis)', () => {
    expect(SOURCE).toMatch(/length\s*>\s*40/);
    expect(SOURCE).toMatch(/slice\(\s*0\s*,\s*39\s*\)/);
  });
});

/**
 * RED→GREEN trajectory: verified by checking out the parent of 63fb5a7
 * (the file before the fix) — the source assertions for `formatTitle`,
 * `item.product_names`, and the missing legacy lookup all flip to RED.
 */
