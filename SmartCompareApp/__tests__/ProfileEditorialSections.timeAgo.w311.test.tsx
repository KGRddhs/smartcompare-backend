/**
 * W3-11bcd — MB-I18N-RTL-08 (c): the Profile "recent decisions" row stops
 * rendering English relative time to Arabic users.
 *
 * Measured at base b63a8368: `ProfileEditorialSections.tsx:63-78` has its
 * own `timeAgo()` with no language branch — `${hrs}h` (:70), `${days}d`
 * (:73) and a bare `toLocaleDateString()` (:74) reach Arabic users through
 * `MiniVsCard` (:142). The fix (spec R6) deletes it: RecentDecisionsRow
 * reads `{ t, i18n }` from ONE useTranslation() and passes `language` +
 * `t` into MiniVsCard, which calls the shared
 * `formatTimeAgo(created_at, language, t)`.
 *
 * `t` here is a REAL i18next instance over the real catalogs (so plural
 * families resolve), exposed through the react-i18next mock together with
 * `i18n.language = 'ar'`.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import i18next from 'i18next';
import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';
import { formatDate } from '../src/utils/formatDate';

const AR = ar as Record<string, string>;

const mockI18n = i18next.createInstance();

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => mockI18n.t(key, opts),
    i18n: { language: 'ar' },
  }),
}));

const mockGetProfileRecentDecisions = jest.fn();

jest.mock('../src/services/api', () => ({
  getProfileRecentDecisions: (...args: any[]) => mockGetProfileRecentDecisions(...args),
  getProfileMonthlyStats: jest.fn(),
  getProfilePrioritiesWeighted: jest.fn(),
}));

import { RecentDecisionsRow } from '../src/components/ProfileEditorialSections';

const NOW = Date.UTC(2026, 8, 11, 12);

beforeAll(async () => {
  await mockI18n.init({
    lng: 'ar',
    fallbackLng: 'en',
    resources: { en: { translation: en }, ar: { translation: ar } },
    interpolation: { escapeValue: false },
  });
});

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(Date, 'now').mockReturnValue(NOW);
});

afterEach(() => {
  jest.restoreAllMocks();
});

function recent(createdAtMs: number) {
  return {
    comparison_id: 'cmp-1',
    winner_name: 'Dior Sauvage',
    runner_up_name: 'Bleu de Chanel',
    created_at: new Date(createdAtMs).toISOString(),
    winner_image_url: null,
    runner_up_image_url: null,
  };
}

/** Every rendered string inside the recent-decision card, joined. */
function cardText(json: any): string {
  const out: string[] = [];
  const walk = (n: any) => {
    if (n == null) return;
    if (typeof n === 'string') {
      out.push(n);
      return;
    }
    if (Array.isArray(n)) {
      n.forEach(walk);
      return;
    }
    if (n.children) n.children.forEach(walk);
  };
  walk(json);
  return out.join('');
}

describe('W3-11 RTL-08 (c) — Profile recent-decisions relative time under ar', () => {
  it('3 hours ago renders the Arabic "few" form, never an English "3h"', async () => {
    mockGetProfileRecentDecisions.mockResolvedValue({ recent: [recent(NOW - 3 * 3_600_000)], empty_state: false });
    const { findByTestId } = render(<RecentDecisionsRow />);
    const card = await findByTestId('profile-recent-card');
    const text = cardText(card.children);

    expect(text).not.toMatch(/\b\d+[hd]\b/);
    const few = AR['time.hoursAgo_few'];
    expect(few).toEqual(expect.any(String));
    expect(text).toContain(few.replace('{{count}}', '3'));
  });

  it('20 days ago renders the policy-mapped Arabic date, with no Arabic-Indic digit', async () => {
    const created = NOW - 20 * 86_400_000;
    mockGetProfileRecentDecisions.mockResolvedValue({ recent: [recent(created)], empty_state: false });
    const { findByTestId } = render(<RecentDecisionsRow />);
    const card = await findByTestId('profile-recent-card');
    const text = cardText(card.children);

    expect(text).not.toMatch(/[٠-٩۰-۹]/);
    // The shared formatter's >= 7-day fallback — not the device-locale
    // `toLocaleDateString()` the local helper used (:74).
    expect(text).toContain(formatDate(new Date(created), 'ar'));
  });
});
