/**
 * ShareBottomSheet redesign — Phase 4 Task 40.
 *
 * Verifies the new "You'll unlock" gamified reward block per design
 * § 4e. The pre-existing privacy-toggle + live-preview behavior stays
 * covered by the inviting screen's integration tests; this suite asserts
 * the reward block is present + uses the right copy keys.
 */

import * as fs from 'fs';
import * as path from 'path';

const SOURCE = fs.readFileSync(
  path.resolve(
    __dirname,
    '../src/components/ShareBottomSheet.tsx'
  ),
  'utf8'
);

describe('ShareBottomSheet redesign — Phase 4 Task 40 (source assertions)', () => {
  it('renders the reward block (testID share-reward-block)', () => {
    expect(SOURCE).toMatch(/testID=['"]share-reward-block['"]/);
  });

  it('uses the new reward i18n keys', () => {
    for (const key of [
      'referrals.share.reward.title',
      'referrals.share.reward.now',
      'referrals.share.reward.later',
    ]) {
      expect(SOURCE).toContain(key);
    }
  });

  it('places the reward block ABOVE the privacy-toggle section', () => {
    // The reward block carries the lift before the user thinks about
    // privacy, so it must appear earlier in the JSX.
    const rewardIdx = SOURCE.indexOf('share-reward-block');
    const privacyTogglesIdx = SOURCE.indexOf("Privacy toggles");
    expect(rewardIdx).toBeGreaterThan(0);
    expect(privacyTogglesIdx).toBeGreaterThan(rewardIdx);
  });
});

describe('ShareBottomSheet — i18n catalog', () => {
  const en = fs.readFileSync(
    path.resolve(__dirname, '../src/i18n/en.json'),
    'utf8'
  );
  const ar = fs.readFileSync(
    path.resolve(__dirname, '../src/i18n/ar.json'),
    'utf8'
  );

  it('adds reward + toast keys EN + AR', () => {
    for (const key of [
      'referrals.share.reward.title',
      'referrals.share.reward.now',
      'referrals.share.reward.later',
      'referrals.share.toast.confirm',
    ]) {
      expect(en).toContain(`"${key}"`);
      expect(ar).toContain(`"${key}"`);
    }
  });

  it('uses the design § 4e toast copy "Sent to {{name}}. We\'ll add 5 more if they sign up."', () => {
    // Per § 4g audit the confirm-toast copy is the brand contract.
    expect(en).toMatch(/"✦ Sent to \{\{name\}\}\. We'll add 5 more if they sign up\."/);
  });
});
