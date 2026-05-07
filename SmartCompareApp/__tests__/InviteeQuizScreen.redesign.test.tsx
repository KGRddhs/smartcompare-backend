/**
 * InviteeQuizScreen reveal redesign — Phase 4 Task 39.
 *
 * Verifies the reveal-screen contract per design § 4e:
 * - Winner card with emerald glow ring
 * - Match score animating 0 → N via CounterTicker
 * - "How your answers shaped this" section echoes the user's quiz inputs
 * - Soft signup CTA: "Try Qaren free — 5 comparisons"
 *
 * Uses source-string assertions on InviteeQuizScreen.tsx + i18n catalog
 * because driving the 4Q wizard end-to-end in unit-test land would
 * require pretending to be a series of quiz answers + the submitQuiz
 * promise + Reanimated entering builders. The wizard flow itself is
 * covered by the existing InviteeQuizScreen.test.tsx behavior suite;
 * full visual verification happens at Phase 4 QA gate (#42) on-device.
 */

import * as fs from 'fs';
import * as path from 'path';

const SCREEN_PATH = path.resolve(
  __dirname,
  '../src/screens/InviteeQuizScreen.tsx'
);
const SOURCE = fs.readFileSync(SCREEN_PATH, 'utf8');

describe('InviteeQuizScreen reveal — Phase 4 Task 39 (source assertions)', () => {
  it('imports CounterTicker for the match-score animation', () => {
    expect(SOURCE).toMatch(
      /import\s*\{\s*CounterTicker\s*\}\s*from\s*['"]\.\.\/components\/CounterTicker['"]/
    );
  });

  it('renders the winner card slot (testID quiz-winner-card)', () => {
    expect(SOURCE).toMatch(/testID=['"]quiz-winner-card['"]/);
  });

  it('renders the emerald glow ring slot (testID quiz-winner-glow)', () => {
    expect(SOURCE).toMatch(/testID=['"]quiz-winner-glow['"]/);
  });

  it('renders the match-score CounterTicker slot (testID quiz-match-score)', () => {
    expect(SOURCE).toMatch(/testID=['"]quiz-match-score['"]/);
  });

  it('renders the "How your answers shaped this" section (testID quiz-shaped-by)', () => {
    expect(SOURCE).toMatch(/testID=['"]quiz-shaped-by['"]/);
  });

  it('renders the signup CTA (testID quiz-signup-cta)', () => {
    expect(SOURCE).toMatch(/testID=['"]quiz-signup-cta['"]/);
  });

  it('uses Button variant="primary" for the soft signup CTA (black)', () => {
    // The CTA should use the design Button component with primary
    // variant per § 4e ("Soft signup CTA at bottom (black, ...)").
    expect(SOURCE).toMatch(
      /testID=['"]quiz-signup-cta['"][\s\S]{0,400}variant=['"]primary['"]/
    );
  });
});

describe('InviteeQuizScreen reveal — i18n catalog', () => {
  const en = fs.readFileSync(
    path.resolve(__dirname, '../src/i18n/en.json'),
    'utf8'
  );
  const ar = fs.readFileSync(
    path.resolve(__dirname, '../src/i18n/ar.json'),
    'utf8'
  );

  it('adds the new reveal copy keys EN + AR', () => {
    for (const key of [
      'referrals.quiz.matchScoreLabel',
      'referrals.quiz.shapedByTitle',
      'referrals.quiz.signupCtaSoft',
    ]) {
      expect(en).toContain(`"${key}"`);
      expect(ar).toContain(`"${key}"`);
    }
  });

  it('uses confident copy "Try Qaren free — 5 comparisons" per § 4e', () => {
    // The exact phrasing is the design contract.
    expect(en).toMatch(/"Try Qaren free.*5 comparisons"/);
  });
});
