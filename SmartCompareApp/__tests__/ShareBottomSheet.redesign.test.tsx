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
      'referrals.share.reward.later',
      // S81-11 (E7, R-S11-33): referrals.share.toast.confirm deleted (no reader).
    ]) {
      expect(en).toContain(`"${key}"`);
      expect(ar).toContain(`"${key}"`);
    }
  });

  // S81-11 (E7, R-S11-33): the confirm-toast exact-copy row is deleted with
  // the key ("We'll add 5 more" had no reader; CL4 re-adds what its flow needs).
  it('the deleted confirm-toast key is absent from both catalogs (S81-11)', () => {
    expect(en).not.toContain('"referrals.share.toast.confirm"');
    expect(ar).not.toContain('"referrals.share.toast.confirm"');
  });
});
