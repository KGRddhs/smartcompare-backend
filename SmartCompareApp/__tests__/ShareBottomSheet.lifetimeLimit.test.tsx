/**
 * ShareBottomSheet — Bundle B/C/D Task 2.14 lifetime gating.
 *
 * Verifies the share-target buttons disable when the user hits the
 * lifetime cap (3), the Copy button stays active (§ 4.9 Path D — they
 * can re-share an existing link), and the gift-thanks banner appears.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  notificationAsync: jest.fn(),
  impactAsync: jest.fn(),
  NotificationFeedbackType: { Success: 'Success' },
  ImpactFeedbackStyle: { Light: 'Light' },
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      let str = key;
      if (opts) {
        for (const [k, v] of Object.entries(opts)) {
          if (k === 'defaultValue') continue;
          str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
        }
      }
      return str;
    },
  }),
}));

jest.mock('../src/services/referralService', () => ({
  createShare: jest.fn(),
  ReferralError: class FakeReferralError extends Error {
    code = 'UNKNOWN';
    status = null;
  },
}));

import ShareBottomSheet from '../src/components/ShareBottomSheet';

const COMPARISON = {
  id: 'cmp-123',
  productA: 'iPhone 15',
  productB: 'Galaxy S24',
  winnerName: 'iPhone 15',
};

describe('ShareBottomSheet — Bundle B/C/D lifetime gating', () => {
  it('does NOT show the gift-thanks banner when lifetimeRemaining is undefined', () => {
    const { queryByTestId } = render(
      <ShareBottomSheet
        visible
        comparison={COMPARISON}
        onClose={jest.fn()}
        onShared={jest.fn()}
      />
    );
    expect(queryByTestId('share-max-reached-banner')).toBeNull();
  });

  it('does NOT show the banner when remaining > 0', () => {
    const { queryByTestId } = render(
      <ShareBottomSheet
        visible
        comparison={COMPARISON}
        onClose={jest.fn()}
        onShared={jest.fn()}
        lifetimeRemaining={1}
      />
    );
    expect(queryByTestId('share-max-reached-banner')).toBeNull();
  });

  it('shows the gift-thanks banner when lifetimeRemaining === 0', () => {
    const { getByTestId } = render(
      <ShareBottomSheet
        visible
        comparison={COMPARISON}
        onClose={jest.fn()}
        onShared={jest.fn()}
        lifetimeRemaining={0}
      />
    );
    expect(getByTestId('share-max-reached-banner')).toBeTruthy();
  });

  it('keeps the Copy target enabled when at the limit', () => {
    const { getByTestId } = render(
      <ShareBottomSheet
        visible
        comparison={COMPARISON}
        onClose={jest.fn()}
        onShared={jest.fn()}
        lifetimeRemaining={0}
      />
    );
    const copyBtn = getByTestId('share-target-copy');
    expect(copyBtn.props.accessibilityState?.disabled).toBe(false);
    expect(copyBtn.props.disabled).toBe(false);
  });

  it('disables non-copy targets (WhatsApp, X, Telegram, Snapchat) when at the limit', () => {
    const { getByTestId } = render(
      <ShareBottomSheet
        visible
        comparison={COMPARISON}
        onClose={jest.fn()}
        onShared={jest.fn()}
        lifetimeRemaining={0}
      />
    );
    for (const t of ['whatsapp', 'x', 'telegram', 'snapchat']) {
      const btn = getByTestId(`share-target-${t}`);
      expect(btn.props.accessibilityState?.disabled).toBe(true);
      expect(btn.props.disabled).toBe(true);
    }
  });

  it('non-copy targets are NOT disabled when remaining > 0', () => {
    const { getByTestId } = render(
      <ShareBottomSheet
        visible
        comparison={COMPARISON}
        onClose={jest.fn()}
        onShared={jest.fn()}
        lifetimeRemaining={2}
      />
    );
    for (const t of ['whatsapp', 'x', 'telegram', 'snapchat']) {
      const btn = getByTestId(`share-target-${t}`);
      expect(btn.props.accessibilityState?.disabled).toBe(false);
    }
  });
});
