/**
 * Physical textAlign fence — M21 W4 rtl-i18n (MB-i18n-rtl-05).
 *
 * RN's `textAlign: 'left' | 'right'` is PHYSICAL — it does not follow
 * I18nManager.isRTL. Five style sites hard-coded a physical side, so under
 * RTL (where the surrounding flex rows DO mirror) the text aligned away
 * from its anchor:
 *
 *   - ResultsAccordion.specsCellValueLeft / specsCellValueRight — the two
 *     spec-value columns hug the centered label; physical align pushes
 *     them off the label under RTL.
 *   - DimensionBars.legendNameRight — product-B legend name.
 *   - ContactUsScreen.charCount — char counter should sit at the logical
 *     END of the textarea.
 *   - ProfileEditorialSections.prioritiesPercent — percent column at the
 *     logical end of the priorities bar row.
 *
 * Contract: each site derives its side from I18nManager.isRTL. (isRTL is
 * fixed for the app lifetime — a direction change forces an app restart —
 * so StyleSheet.create-time evaluation is correct.)
 */
import * as fs from 'fs';
import * as path from 'path';

const ROOT = path.resolve(__dirname, '../../src');

function read(rel: string): string {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8');
}

/** Extract the object body of `styleName: { ... }` from a StyleSheet.create block. */
function styleBody(src: string, styleName: string): string {
  const m = src.match(new RegExp(`${styleName}:\\s*\\{[\\s\\S]*?\\n  \\}`));
  if (!m) throw new Error(`style ${styleName} not found`);
  return m[0];
}

const SITES: Array<[file: string, style: string]> = [
  ['components/results/ResultsAccordion.tsx', 'specsCellValueLeft'],
  ['components/results/ResultsAccordion.tsx', 'specsCellValueRight'],
  ['components/results/DimensionBars.tsx', 'legendNameRight'],
  ['screens/ContactUsScreen.tsx', 'charCount'],
  ['components/ProfileEditorialSections.tsx', 'prioritiesPercent'],
];

describe('textAlign left/right sites are I18nManager-conditional (MB-i18n-rtl-05)', () => {
  for (const [file, style] of SITES) {
    it(`${file} :: ${style}`, () => {
      const body = styleBody(read(file), style);
      // The physical literal may only appear as a branch of an
      // I18nManager.isRTL conditional, never bare.
      expect(body).toMatch(/textAlign:\s*I18nManager\.isRTL\s*\?/);
      expect(body).not.toMatch(/textAlign:\s*'(left|right)'/);
    });
  }
});
