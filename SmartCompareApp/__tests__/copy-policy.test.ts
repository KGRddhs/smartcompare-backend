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
import policy from '../src/i18n/.copy-policy.json';

// Bundle B follow-up — DRY up against .copy-policy.json so the JSON is
// the single source of truth and adding a banned pattern in policy
// automatically flows into this guard (previously the EN/AR lists were
// hardcoded duplicates of policy.banned_en / policy.banned_ar). Schema
// has been stable since Bundle E shipped; if the shape ever changes
// (e.g. `banned.en` nested), update both this loader + the policy file
// in the same commit.
//
// Notes preserved from the original hardcoded comments:
// - `Winner` matches across all namespaces (was Results-scoped intent
//   but the original code never actually filtered; policy now governs).
// - "Best for" stays a literal word-boundary match — i18n KEY names like
//   `results.bestForYou` are camelCase and never surface visibly.
type BannedEntry = { pattern: RegExp; label: string };

const policyDoc = policy as {
  banned_en?: { pattern: string; label: string }[];
  banned_ar?: { pattern: string; label: string }[];
  scary_vocab_en?: string[];
  scary_vocab_ar?: string[];
};

function compileBannedList(
  raw: { pattern: string; label: string }[] | undefined,
  flags: string
): BannedEntry[] {
  return (raw ?? []).map((entry) => ({
    pattern: new RegExp(entry.pattern, flags),
    label: entry.label,
  }));
}

// EN is case-insensitive; AR is case-sensitive (Arabic letters have no
// case distinction, and Latin substrings inside AR strings are rare
// enough that case-sensitivity is safer + matches existing behavior).
const BANNED_EN: BannedEntry[] = compileBannedList(policyDoc.banned_en, 'i');
const BANNED_AR: BannedEntry[] = compileBannedList(policyDoc.banned_ar, '');

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
 * Bundle B Build Principle #4 — "never frame the app as scary".
 *
 * Spec: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md
 *   § 7.4 Copy tone audit.
 *
 * Source of truth is `.copy-policy.json` — `scary_vocab_en` and
 * `scary_vocab_ar` arrays. This guard loads them directly so any future
 * additions to the policy file are picked up without touching the test.
 *
 * AR scope notes:
 *   - `تقدير` / `مُقدَّر` are blocked here because Bundle B's
 *     `feedback_no_estimated_word_in_ui.md` rule says user-facing AR copy
 *     must never expose the backend `source_method="estimated"` enum
 *     literally — UI must substitute "indicative" / "reference" phrasing.
 *
 * EN scope notes:
 *   - The bare word `error` is intentionally NOT in scary_vocab_en. It
 *     appears in many legitimate i18n KEY namespaces (e.g.
 *     `home.errors.camera`, `common.error`) whose user-visible VALUES use
 *     neutral copy ("Hold on — give it another tap."). Blocking the bare
 *     word would surface unrelated pre-existing strings as false
 *     positives. The other 3 EN patterns (`couldn't`, `try again`,
 *     `Failed to`) plus all 4 AR patterns are unambiguous and load-bearing.
 *
 * This complements the Bundle E describe-block above with a second layer
 * (scary copy vs. evaluative copy) so QA-5 (copy audit) is automated end
 * to end — Build Principle #4 is now a build-time fence, not a manual
 * checklist item.
 */
describe('Copy policy — Bundle B Build Principle #4 scary vocabulary audit', () => {
  const enScary: string[] = policyDoc.scary_vocab_en ?? [];
  const arScary: string[] = policyDoc.scary_vocab_ar ?? [];

  it('policy file loads banned + scary vocabulary arrays', () => {
    // Sanity check — guards against an empty policy silently passing
    // every assertion above + below. Also guards against the DRY refactor
    // (Bundle B) regressing the Bundle E lists to empty.
    expect(BANNED_EN.length).toBeGreaterThan(0);
    expect(BANNED_AR.length).toBeGreaterThan(0);
    expect(enScary.length).toBeGreaterThan(0);
    expect(arScary.length).toBeGreaterThan(0);
  });

  it('en.json values contain no scary vocabulary from .copy-policy.json scary_vocab_en', () => {
    const offenders: { key: string; banned: string; value: string }[] = [];
    for (const [key, value] of Object.entries(enRecord)) {
      if (typeof value !== 'string') continue;
      const visible = visibleCopy(value);
      const lower = visible.toLowerCase();
      for (const term of enScary) {
        if (lower.includes(term.toLowerCase())) {
          offenders.push({ key, banned: term, value });
        }
      }
    }
    expect(offenders).toEqual([]);
  });

  it('ar.json values contain no scary vocabulary from .copy-policy.json scary_vocab_ar', () => {
    const offenders: { key: string; banned: string; value: string }[] = [];
    for (const [key, value] of Object.entries(arRecord)) {
      if (typeof value !== 'string') continue;
      const visible = visibleCopy(value);
      for (const term of arScary) {
        if (visible.includes(term)) {
          offenders.push({ key, banned: term, value });
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
