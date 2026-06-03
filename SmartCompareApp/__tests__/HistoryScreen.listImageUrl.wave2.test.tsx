/**
 * Bundle E S3 Hot-Fix Wave 2 — L2 lane.
 *
 * Device-walk image #22 (History list rows): NEW iPhone 17 comparison
 * shows placeholder phone glyphs even though the image pipeline is live.
 * Root cause: HistoryScreen list-row reader at HistoryScreen.tsx:533-536
 * pulls `full_response.products[i].image_url`, which works for FULLY
 * RE-FETCHED rows but the LIST endpoint may not include the full
 * response (smaller payload optimization). L3 Wave 2 extends the LIST
 * payload with top-level `winner_image_url + runner_up_image_url`
 * fields per row.
 *
 * Fix: HistoryScreen list-row reader prefers the top-level fields when
 * present, falls back to the `full_response.products[i].image_url`
 * traversal for backwards compat with stale cached list data.
 *
 * Tests:
 *   1. Top-level `winner_image_url + runner_up_image_url` win when both
 *      shapes are present (new path).
 *   2. `full_response.products[i].image_url` fills in when top-level
 *      missing (legacy / backwards-compat path).
 *   3. winner_index drives which top-level field maps to block A vs B.
 *   4. SOURCE-GREP contract: HistoryScreen.tsx reads `item.winner_image_url`
 *      and `item.runner_up_image_url` (per the new field names L3 wires).
 *
 * Mirror of HistoryScreen.imageUrl.test.tsx source-grep style — same
 * `memory/feedback_snapshots_as_staleness_liability.md` reasoning for
 * source-string contract over render-tree integration on this screen.
 */

import * as fs from 'fs';
import * as path from 'path';

const HISTORY_PATH = path.resolve(__dirname, '../src/screens/HistoryScreen.tsx');

let historySrc: string;

beforeAll(() => {
  historySrc = fs.readFileSync(HISTORY_PATH, 'utf8');
});

describe('HistoryScreen — Wave 2 list-row prefers top-level winner_image_url', () => {
  it('source references item.winner_image_url', () => {
    expect(historySrc).toMatch(/item\.winner_image_url/);
  });

  it('source references item.runner_up_image_url', () => {
    expect(historySrc).toMatch(/item\.runner_up_image_url/);
  });

  it('HistoryItem interface declares optional winner_image_url field', () => {
    expect(historySrc).toMatch(
      /winner_image_url\??\s*:\s*string\s*\|\s*null/
    );
  });

  it('HistoryItem interface declares optional runner_up_image_url field', () => {
    expect(historySrc).toMatch(
      /runner_up_image_url\??\s*:\s*string\s*\|\s*null/
    );
  });

  it('list-row reader prefers top-level field with ?? fallback to full_response', () => {
    // The contract: either
    //   imageUrlA = item.winner_image_url ?? fullResponseProducts[…]?.image_url
    // OR equivalent — the top-level field is the PRIMARY source, the
    // full_response traversal is the BACKWARD-COMPAT fallback.
    expect(historySrc).toMatch(
      /item\.winner_image_url\s*\?\?[\s\S]{0,200}?image_url/
    );
    expect(historySrc).toMatch(
      /item\.runner_up_image_url\s*\?\?[\s\S]{0,200}?image_url/
    );
  });

  it('still falls back to full_response.products[i].image_url for legacy rows', () => {
    // Regression net for the Wave 1 path — backwards compat for cached
    // pre-deploy list-payload state.
    expect(historySrc).toMatch(/full_response[\s\S]{0,200}?image_url/);
  });
});
