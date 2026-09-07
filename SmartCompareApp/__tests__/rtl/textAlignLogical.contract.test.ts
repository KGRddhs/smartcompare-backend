/**
 * Physical textAlign fence — W3-11a, the revert of the M21 W4 double-flip
 * (finding MB-I18N-RTL-03).
 *
 * ---------------------------------------------------------------------------
 * THE PREMISE THE M21 W4 FIX WAS BUILT ON IS FALSE.
 * ---------------------------------------------------------------------------
 * The previous version of this file asserted, in prose and in its assertions,
 * that "RN's `textAlign: 'left' | 'right'` is PHYSICAL — it does not follow
 * I18nManager.isRTL". That is wrong, and it is what produced the wrong fix.
 *
 * MEASURED against the pinned `react-native@0.81.5` source in node_modules.
 * All four platform paths already mirror `left`/`right` under RTL:
 *
 *  1. iOS (classic + Fabric) —
 *     `Libraries/Text/RCTTextAttributes.mm:107-115` (`effectiveParagraphStyle`):
 *     under `UIUserInterfaceLayoutDirectionRightToLeft`, `NSTextAlignmentRight`
 *     becomes `Left` and `NSTextAlignmentLeft` becomes `Right`. This is the one
 *     shared implementation — `effectiveParagraphStyle` is reached only via
 *     `effectiveTextAttributes`, which every Text/TextInput shadow view uses.
 *
 *  2. Android (classic) —
 *     `ReactAndroid/src/main/java/com/facebook/react/views/text/TextAttributeProps.java:294-297`:
 *       "left"  -> isRTL ? Gravity.RIGHT : Gravity.LEFT
 *       "right" -> isRTL ? Gravity.LEFT  : Gravity.RIGHT
 *
 *  3. Android (Fabric) —
 *     `ReactAndroid/src/main/java/com/facebook/react/views/text/TextLayoutManager.kt:169-198`.
 *     Reaches the same outcome by a different route, and the route matters
 *     because it LOOKS content-dependent and is not. Android resolves
 *     `ALIGN_NORMAL` against the SCRIPT direction, so RN computes
 *     `swapNormalAndOpposite = (isParagraphRTL != isScriptRTL)` (`:180`) to
 *     re-anchor alignment to the PARAGRAPH direction. Working the cases
 *     through, `'right'` lands on physical right in an LTR paragraph and
 *     physical left in an RTL paragraph — for Arabic AND Latin content alike.
 *     The compensation exists precisely to make the outcome script-independent.
 *
 * CONSEQUENCE: `textAlign: I18nManager.isRTL ? 'left' : 'right'` applies a
 * SECOND flip on top of RN's own, landing back on the physical side it started
 * from. Under RTL every site below aligns to the WRONG edge — the exact defect
 * M21 W4 set out to fix. The LTR branch of each ternary is a no-op; the RTL
 * branch is pure regression.
 *
 * Corroborated in-repo: `src/components/TwoInputShell.tsx` already learned
 * this same lesson for `flexDirection` ("RN mirrors it natively under
 * forceRTL; an explicit reverse cancelled that mirroring"). The app calls
 * `allowRTL(true)` + `forceRTL(...)` and never `swapLeftAndRightInRTL(false)`,
 * so RN's default mirroring is fully active.
 *
 * ---------------------------------------------------------------------------
 * CONTRACT (inverted vs the M21 W4 version of this file)
 * ---------------------------------------------------------------------------
 * Each style in SITES carries the BARE physical literal. For the five M21 W4
 * sites that is exactly what stood at `593ec1e`; the sixth
 * (`InviteeQuizScreen.charCount`) predates `593ec1e` and pins its own
 * pre-`acca7434` value — see the note on that row. The `I18nManager.isRTL`
 * ternary is FORBIDDEN on these styles: RN already mirrors them, so
 * re-introducing it re-introduces the bug.
 *
 * If you are here because you think one of these sites aligns to the wrong
 * edge under RTL, read the three source locations above FIRST — they take
 * about a minute to check — and do not re-apply the ternary.
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

/**
 * Return the bare physical literal a style assigns to `textAlign`, or — when
 * the value is not a bare literal — the raw expression, so a failure reads
 * `Expected: "right" / Received: "I18nManager.isRTL ? 'left' : 'right'"`.
 */
function textAlignValue(body: string): string {
  const bare = body.match(/textAlign:\s*'([a-z]+)'\s*,/);
  if (bare) return bare[1];
  const raw = body.match(/textAlign:\s*([^\n]+?),?\s*$/m);
  return raw ? raw[1].trim() : '<no textAlign in style body>';
}

interface Site {
  file: string;
  style: string;
  /**
   * The bare literal to restore. For the five M21 W4 sites this is the value
   * at `593ec1e` — what every build users have ever run shipped. For the
   * sixth (InviteeQuizScreen) it is the pre-`acca7434` value, since the
   * double-flip there predates `593ec1e`.
   */
  expected: 'left' | 'right';
}

const SITES: Site[] = [
  {
    file: 'components/results/ResultsAccordion.tsx',
    style: 'specsCellValueLeft',
    expected: 'right',
  },
  {
    file: 'components/results/ResultsAccordion.tsx',
    style: 'specsCellValueRight',
    expected: 'left',
  },
  {
    file: 'components/results/DimensionBars.tsx',
    style: 'legendNameRight',
    expected: 'right',
  },
  { file: 'screens/ContactUsScreen.tsx', style: 'charCount', expected: 'right' },
  {
    file: 'components/ProfileEditorialSections.tsx',
    style: 'prioritiesPercent',
    expected: 'right',
  },
  // SIXTH SITE — not in the W3-11a spec's five-row table, and NOT an M21 W4
  // site. The double-flip here predates `593ec1e`: it was introduced by
  // `acca7434` (2026-05-07, "use logical properties ... for direction-aware
  // spacing"), so `593ec1e` already carries the ternary. Its pre-`acca7434`
  // value was the bare `'right'` this pins, so restoring it is still a revert
  // — just to an older baseline. It is the identical twin of the
  // `ContactUsScreen.charCount` row above: same style name, same widget (a
  // `{n}/{max}` counter under a textarea), same intended trailing edge.
  //
  // RISK-CLASS DIFFERENCE, deliberately recorded: `acca7434` IS an ancestor of
  // `97b5f15`, the `preview` build on phones, so unlike the five rows above
  // this one is a LIVE Arabic misalignment today rather than a main-only
  // regression. The "restores exactly the bytes users have already run"
  // safety argument therefore does NOT cover this row — it wants the
  // on-device Arabic check, and it is one line for a reviewer to drop.
  {
    file: 'screens/InviteeQuizScreen.tsx',
    style: 'charCount',
    expected: 'right',
  },
];

describe('textAlign sites carry the bare physical literal — RN mirrors it (MB-I18N-RTL-03)', () => {
  for (const { file, style } of SITES) {
    it(`${file} :: ${style} has no I18nManager.isRTL ternary`, () => {
      const body = styleBody(read(file), style);
      // RN already flips left/right under RTL on all four platform paths, so a
      // second flip here lands back on the wrong edge. Bare literal only.
      expect(body).toMatch(/textAlign:\s*'(left|right)'/);
      expect(body).not.toMatch(/textAlign:\s*I18nManager\.isRTL\s*\?/);
    });
  }
});

describe('the restored literal is a REVERT, not a new opinion', () => {
  for (const { file, style, expected } of SITES) {
    it(`${file} :: ${style} is '${expected}' as at its pre-flip baseline`, () => {
      // Pins the exact pre-M21-W4 value. Under LTR the M21 W4 ternary already
      // evaluated to this same literal, so this is also the proof that the
      // revert is a no-op for every LTR user.
      expect(textAlignValue(styleBody(read(file), style))).toBe(expected);
    });
  }
});

describe('no textAlign anywhere in src/ is written as an I18nManager.isRTL ternary', () => {
  const TERNARY = /textAlign:\s*I18nManager\.isRTL\s*\?/;

  function walk(dir: string, out: string[] = []): string[] {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full, out);
      else if (/\.tsx?$/.test(entry.name)) out.push(full);
    }
    return out;
  }

  it('catches a re-application in any file, including ones SITES does not name', () => {
    // Scanned over the WHOLE FILE TEXT, not line by line (Fable review, W3-11a).
    // A line-scoped version of this pin was blind to a WRAPPED re-application:
    //     textAlign: I18nManager.isRTL
    //       ? 'left'
    //       : 'right',
    // The pattern's whitespace class spans newlines, but testing each line in
    // isolation means the '?' on the next line is never seen. Prettier produces
    // exactly that wrap once the expression grows. This is the ONLY fence
    // covering files SITES does not name, and it is the fence that caught the
    // sixth site - a gap here is the difference between a real guard and a
    // decorative one.
    const hits: string[] = [];
    for (const file of walk(ROOT)) {
      const text = fs.readFileSync(file, 'utf8');
      const rx = new RegExp(TERNARY.source, 'g');
      for (const m of text.matchAll(rx)) {
        const rel = path.relative(ROOT, file).split(path.sep).join('/');
        const line = (text.slice(0, m.index).match(/\n/g) || []).length + 1;
        hits.push('src/' + rel + ':' + line);
      }
    }
    expect(hits).toEqual([]);
  });
});
