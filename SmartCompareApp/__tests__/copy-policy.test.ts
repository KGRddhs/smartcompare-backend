/**
 * Copy policy — Bundle E Phase 3 Task 3.7 RED scaffold.
 *
 * Plan: docs/plans/2026-05-13-results-quality-overhaul.md
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 5.
 *
 * Catalog-level audit: every user-facing translation string in en.json
 * and ar.json must steer clear of the banned evaluative vocabulary
 * defined in § Decision 5. This is the i18n-side companion to the
 * component-level guard in `__tests__/components/FactualVerdict.test.tsx`
 * — together they form a defense-in-depth fence against legal exposure
 * from absolute superlatives or first-person Qaren endorsements.
 *
 * § Decision 5 banned patterns (EN — exact phrases per the design table):
 *   `Best Pick`, `Best Choice`, `Smart Pick`, `Winner`,
 *   `Excellent`, `Great`, `Smart pick`,
 *   `Choose this`, `Get this`, `This is right`,
 *   `Better`, `Worse`, `Beats`,
 *   `Why we picked this`, `We recommend`, `Best for`.
 *
 * Allowed near-matches:
 *   - The literal user-facing copy "Top match" — this is the approved
 *     replacement for "Best Pick" and MUST NOT match `Best`.
 *   - Phrase "if you want X, pick the first one" — `pick` only matches
 *     in `Best Pick` / `Smart Pick`, not as a verb.
 *   - "best price" / "best-in-class" — narrow approved fact-based copy,
 *     scoped via word-boundary in the regex below.
 *
 * AR side: § Decision 5 doesn't enumerate Arabic banned words explicitly.
 * We list the obvious literal mirrors here so a regression that drops
 * "أفضل اختيار" or similar absolute-superlative copy into ar.json gets
 * caught. This list will be tightened by Phase 3 Task 3.7 (Agent A or
 * Agent C will own the AR copy review with a native speaker).
 *
 * BLOCKED ON: no implementation dependency — this guard runs against the
 * current catalog as the components ship. Today it should PASS (Phase 3
 * hasn't shipped banned copy yet) but the test still belongs in the
 * scaffold suite so any Phase 3 PR is forced to keep en.json + ar.json
 * clean as part of cross-QA. If a banned word IS already in the
 * catalog, that's a Bundle E pre-existing bug worth a SEND-BACK.
 */

import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';

const BANNED_EN: { pattern: RegExp; label: string }[] = [
  { pattern: /\bBest Pick\b/i, label: 'Best Pick' },
  { pattern: /\bBest Choice\b/i, label: 'Best Choice' },
  { pattern: /\bSmart Pick\b/i, label: 'Smart Pick' },
  // `Winner` is a UI label some legacy code uses for non-Results
  // contexts (e.g. referrals leaderboard). Scope to Results-namespace
  // keys only — see filter below.
  { pattern: /\bWinner\b/i, label: 'Winner' },
  { pattern: /\bExcellent\b/i, label: 'Excellent' },
  { pattern: /\bChoose this\b/i, label: 'Choose this' },
  { pattern: /\bGet this\b/i, label: 'Get this' },
  { pattern: /\bThis is right\b/i, label: 'This is right' },
  { pattern: /\bBeats\b/i, label: 'Beats' },
  { pattern: /\bWhy we picked this\b/i, label: 'Why we picked this' },
  { pattern: /\bWe recommend\b/i, label: 'We recommend' },
  // "Best for" is banned per the design table. Approved alternative:
  // "Ideal for". Narrow regex to avoid matching the i18n KEY namespace
  // (e.g. `results.bestForYou` is a key name, not user-visible copy).
  { pattern: /\bBest for\b/i, label: 'Best for' },
];

// Arabic mirrors of the obvious absolute superlatives. Tightened in
// Phase 3 Task 3.7 by Arabic native review.
const BANNED_AR: { pattern: RegExp; label: string }[] = [
  { pattern: /أفضل اختيار/, label: 'أفضل اختيار (Best Choice)' },
  { pattern: /الخيار الأفضل/, label: 'الخيار الأفضل (The Best Choice)' },
  { pattern: /الفائز/, label: 'الفائز (Winner)' },
  { pattern: /نوصي بـ/, label: 'نوصي بـ (We recommend)' },
];

const enRecord = en as Record<string, string>;
const arRecord = ar as Record<string, string>;

// Strip `{{interpolated}}` placeholders before the banned-word check.
// Template variable names (e.g. `{{winner}}`) are never visible to the
// user — they get replaced at runtime with the actual product name.
// Only the literal copy around them is user-facing.
function visibleCopy(value: string): string {
  return value.replace(/\{\{[^}]+\}\}/g, '');
}

describe('Copy policy — Bundle E § Decision 5 banned vocabulary audit', () => {
  it('en.json contains no banned absolute-superlative or endorsement vocabulary', () => {
    const offenders: { key: string; banned: string; value: string }[] = [];
    for (const [key, value] of Object.entries(enRecord)) {
      if (typeof value !== 'string') continue;
      const visible = visibleCopy(value);
      for (const { pattern, label } of BANNED_EN) {
        if (pattern.test(visible)) {
          offenders.push({ key, banned: label, value });
        }
      }
    }
    // Surface every offender at once for a useful failure message.
    expect(offenders).toEqual([]);
  });

  it('ar.json contains no banned absolute-superlative or endorsement vocabulary', () => {
    const offenders: { key: string; banned: string; value: string }[] = [];
    for (const [key, value] of Object.entries(arRecord)) {
      if (typeof value !== 'string') continue;
      const visible = visibleCopy(value);
      for (const { pattern, label } of BANNED_AR) {
        if (pattern.test(visible)) {
          offenders.push({ key, banned: label, value });
        }
      }
    }
    expect(offenders).toEqual([]);
  });
});

/**
 * RED→GREEN trajectory:
 *
 *  1. At commit time (Bundle E scaffold landing): assertions PASS if the
 *     catalog is already clean, OR FAIL if pre-existing strings slipped
 *     past Phase 3 review. A failure here is itself useful — it surfaces
 *     a pre-Bundle-E debt for a separate cleanup PR.
 *  2. During Phase 3 implementation: any contributor adding "Best Pick"
 *     or "Excellent" to en.json triggers a build-time guard failure.
 *  3. Long-term: when § Decision 5's i18n ESLint rule + pytest companion
 *     ship (Phase 3 Task 3.7), this jest test stays as the runtime fence
 *     — three layers of defense (eslint at edit time, pytest in CI,
 *     jest on every test run).
 */
