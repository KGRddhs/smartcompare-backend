/**
 * Bundle E S3 Hot-Fix Wave 2 — L2 lane.
 *
 * Device-walk image #15 (Profile RecentDecisions tiles): placeholder
 * rectangles, no product images for NEW comparisons. Root cause: the
 * `MiniVsCard` inside `ProfileEditorialSections.RecentDecisionsRow`
 * renders solid tone-color tiles via `deriveTone(item.{winner,runner_up}_name)`
 * — it never consumes the `winner_image_url + runner_up_image_url`
 * fields that the API already types on `RecentDecisionItem`
 * (`api.ts:812-822` since A4 Wave 2).
 *
 * Fix: wire `<ProductImage>` inside each MiniProduct tile, falling back
 * to the existing tone color when the URL is missing (4-state primitive
 * contract — string→Image, null/undefined/onError→placeholder).
 *
 * Tests written RED first (TDD red-green-refactor):
 *   - Each tile renders a ProductImage primitive with the matching URL
 *   - Tone is forwarded as `placeholderTone` so legacy + null rows still
 *     show the per-brand color background
 *   - 4-state contract intact (string URL → -img suffix testID; null
 *     URL → -placeholder suffix testID)
 *   - Winner check overlay still renders (regression net for the
 *     existing emerald-check adornment)
 */

import React from 'react';
import { render, waitFor } from '@testing-library/react-native';

// Pass-through useFocusEffect → useEffect (sync-render pattern, per memory
// :feedback_sync_render_waitfor_for_focus_effect_screens). RecentDecisionsRow
// uses useEffect directly, but the same pattern keeps fetch->setState clean
// across renderers.
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
        return opts.defaultValue;
      }
      return key;
    },
  }),
}));

const mockGetProfileRecentDecisions = jest.fn();
const mockGetProfileMonthlyStats = jest.fn();
const mockGetProfilePrioritiesWeighted = jest.fn();

jest.mock('../src/services/api', () => ({
  getProfileRecentDecisions: (...args: any[]) =>
    mockGetProfileRecentDecisions(...args),
  getProfileMonthlyStats: (...args: any[]) =>
    mockGetProfileMonthlyStats(...args),
  getProfilePrioritiesWeighted: (...args: any[]) =>
    mockGetProfilePrioritiesWeighted(...args),
}));

import { RecentDecisionsRow } from '../src/components/ProfileEditorialSections';

function fixtureRecent(overrides: any = {}) {
  return {
    comparison_id: 'cmp-1',
    winner_name: 'iPhone 15',
    runner_up_name: 'Galaxy S24',
    created_at: '2026-06-02T12:00:00Z',
    winner_image_url: 'https://cdn.example.com/iphone-15.jpg',
    runner_up_image_url: 'https://cdn.example.com/galaxy-s24.jpg',
    ...overrides,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetProfileMonthlyStats.mockResolvedValue({
    decisions_count: 0,
    savings_bhd: 0,
    bonus_credits_this_month: 0,
  });
  mockGetProfilePrioritiesWeighted.mockResolvedValue({
    priorities: [],
    empty_state: true,
  });
});

describe('ProfileEditorialSections.RecentDecisionsRow — image_url wiring (Wave 2)', () => {
  it('renders ProductImage for the winner tile when winner_image_url present', async () => {
    mockGetProfileRecentDecisions.mockResolvedValue({
      recent: [fixtureRecent()],
      empty_state: false,
    });
    const { findByTestId } = render(<RecentDecisionsRow />);
    const winnerImg = await findByTestId('profile-recent-card-winner-image-slot-img');
    expect(winnerImg.props.source).toEqual({
      uri: 'https://cdn.example.com/iphone-15.jpg',
    });
  });

  it('renders ProductImage for the runner-up tile when runner_up_image_url present', async () => {
    mockGetProfileRecentDecisions.mockResolvedValue({
      recent: [fixtureRecent()],
      empty_state: false,
    });
    const { findByTestId } = render(<RecentDecisionsRow />);
    const runnerImg = await findByTestId(
      'profile-recent-card-runner-up-image-slot-img'
    );
    expect(runnerImg.props.source).toEqual({
      uri: 'https://cdn.example.com/galaxy-s24.jpg',
    });
  });

  it('renders placeholder when winner_image_url is null', async () => {
    mockGetProfileRecentDecisions.mockResolvedValue({
      recent: [fixtureRecent({ winner_image_url: null })],
      empty_state: false,
    });
    const { findByTestId, queryByTestId } = render(<RecentDecisionsRow />);
    await findByTestId('profile-recent-card-winner-image-slot-placeholder');
    expect(
      queryByTestId('profile-recent-card-winner-image-slot-img')
    ).toBeNull();
  });

  it('renders placeholder when runner_up_image_url is undefined', async () => {
    const item = fixtureRecent();
    delete item.runner_up_image_url;
    mockGetProfileRecentDecisions.mockResolvedValue({
      recent: [item],
      empty_state: false,
    });
    const { findByTestId, queryByTestId } = render(<RecentDecisionsRow />);
    await findByTestId('profile-recent-card-runner-up-image-slot-placeholder');
    expect(
      queryByTestId('profile-recent-card-runner-up-image-slot-img')
    ).toBeNull();
  });

  it('forwards deriveTone as placeholderTone so legacy rows keep the per-brand color', async () => {
    mockGetProfileRecentDecisions.mockResolvedValue({
      recent: [
        fixtureRecent({
          winner_image_url: null,
          runner_up_image_url: null,
        }),
      ],
      empty_state: false,
    });
    const { findByTestId } = render(<RecentDecisionsRow />);
    const winnerPh = await findByTestId(
      'profile-recent-card-winner-image-slot-placeholder'
    );
    const runnerPh = await findByTestId(
      'profile-recent-card-runner-up-image-slot-placeholder'
    );
    // backgroundColor on the placeholder is the per-brand tone — not
    // the neutral default — so the empty-image state still feels like
    // a real product card, not a blank rectangle.
    const flatten = (n: any) => {
      const styles = Array.isArray(n.props.style) ? n.props.style : [n.props.style];
      return Object.assign({}, ...styles.filter(Boolean));
    };
    const winnerStyle = flatten(winnerPh);
    const runnerStyle = flatten(runnerPh);
    expect(winnerStyle.backgroundColor).toBeTruthy();
    expect(runnerStyle.backgroundColor).toBeTruthy();
    // Winner and runner have different brand names so their tones MUST
    // differ — guards against accidentally hard-coding one color.
    expect(winnerStyle.backgroundColor).not.toBe(runnerStyle.backgroundColor);
  });

  it('keeps the winner check overlay rendered over the image', async () => {
    mockGetProfileRecentDecisions.mockResolvedValue({
      recent: [fixtureRecent()],
      empty_state: false,
    });
    const { findByTestId } = render(<RecentDecisionsRow />);
    // The card is rendered (image wiring landed) AND the existing
    // winner-check overlay must still render — regression guard for
    // the emerald check that signals "this is the winner".
    await findByTestId('profile-recent-card-winner-image-slot-img');
    await findByTestId('profile-recent-card-winner-check');
  });

  it('does not render product images on the empty-state card', async () => {
    mockGetProfileRecentDecisions.mockResolvedValue({
      recent: [],
      empty_state: true,
    });
    const { findByTestId, queryByTestId } = render(<RecentDecisionsRow />);
    await findByTestId('profile-recent-empty-card');
    expect(queryByTestId('profile-recent-card-winner-image-slot-img')).toBeNull();
    expect(
      queryByTestId('profile-recent-card-runner-up-image-slot-img')
    ).toBeNull();
  });
});
