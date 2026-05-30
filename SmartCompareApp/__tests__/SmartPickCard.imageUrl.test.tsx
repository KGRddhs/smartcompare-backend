/**
 * Bundle E S3 A4 Wave 2 — SmartPickCard image_url integration.
 *
 * A3 ship `dbf3a5f` extended /home/smart-pick payload with:
 *   winner_image_url: string | null
 *   runner_up_image_url: string | null
 *
 * A4 wires <ProductImage> into both winner + runner-up tiles of the
 * SmartPickCard. The tone background stays (it's the placeholder color
 * when image_url is null) but the tile no longer renders just bare bg —
 * it now hosts a square image when image_url is present.
 *
 * Contract: same 4-state primitive (URL / null / undefined / onError) ×
 * 2 tiles (winner + runner-up).
 *
 * JSX ref: docs/claude-design-handoff/ui_kits/mobile/HomeScreen.jsx:503-525
 * (PickTile) — aspectRatio 1, borderRadius 12, tone background.
 */

import React from 'react';
import { fireEvent, render, waitFor } from '@testing-library/react-native';

jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  return {
    __esModule: true,
    ...real,
    default: real.default ?? real,
  };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      let str = (opts?.defaultValue as string) ?? key;
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

// Mock the api modules SmartPickCard imports via HomeEditorialSections —
// each getter resolves with a deterministic payload so render is sync-ish.
const mockSmartPick = jest.fn();
jest.mock('../src/services/api', () => ({
  getHomeSmartPick: () => mockSmartPick(),
  getHomeQuickCategories: () => Promise.resolve({ categories: [] }),
  getHomeSavings: () => Promise.resolve({ savings: null }),
  getHomeTrending: () => Promise.resolve({ items: [] }),
}));

import { SmartPickCard } from '../src/components/HomeEditorialSections';

function basePick(overrides: Record<string, any> = {}) {
  return {
    comparison_id: 'cmp_1',
    winner_name: 'Galaxy S24',
    runner_up_name: 'iPhone 15',
    winner_price_bhd: 299,
    runner_up_price_bhd: 329,
    reason_key: 'home.smart_pick.reason.fallback',
    reason_params: {},
    category: 'Electronics',
    updated_at: 'Updated today',
    winner_sub: '128GB',
    runner_up_sub: '128GB',
    verdict_short: 'Galaxy edged out iPhone on camera + battery.',
    winner_image_url: null,
    runner_up_image_url: null,
    ...overrides,
  };
}

describe('SmartPickCard — image_url wires to <ProductImage> per tile', () => {
  beforeEach(() => {
    mockSmartPick.mockReset();
  });

  it('renders <Image> on both tiles when both image_urls present', async () => {
    mockSmartPick.mockResolvedValue({
      smart_pick: basePick({
        winner_image_url: 'https://cdn.example.com/galaxy.jpg',
        runner_up_image_url: 'https://cdn.example.com/iphone.jpg',
      }),
      empty_state: false,
    });
    const { findByTestId, queryByTestId } = render(<SmartPickCard />);
    const winnerImg = await findByTestId('home-smart-pick-winner-image-img');
    const runnerImg = await findByTestId('home-smart-pick-runner-up-image-img');
    expect(winnerImg.props.source).toEqual({ uri: 'https://cdn.example.com/galaxy.jpg' });
    expect(runnerImg.props.source).toEqual({ uri: 'https://cdn.example.com/iphone.jpg' });
    expect(queryByTestId('home-smart-pick-winner-image-placeholder')).toBeNull();
    expect(queryByTestId('home-smart-pick-runner-up-image-placeholder')).toBeNull();
  });

  it('renders placeholder on both tiles when both image_urls are null', async () => {
    mockSmartPick.mockResolvedValue({
      smart_pick: basePick({ winner_image_url: null, runner_up_image_url: null }),
      empty_state: false,
    });
    const { findByTestId, queryByTestId } = render(<SmartPickCard />);
    expect(await findByTestId('home-smart-pick-winner-image-placeholder')).toBeTruthy();
    expect(await findByTestId('home-smart-pick-runner-up-image-placeholder')).toBeTruthy();
    expect(queryByTestId('home-smart-pick-winner-image-img')).toBeNull();
    expect(queryByTestId('home-smart-pick-runner-up-image-img')).toBeNull();
  });

  it('renders placeholder when image_url fields are undefined (legacy payload)', async () => {
    const pick = basePick();
    delete (pick as any).winner_image_url;
    delete (pick as any).runner_up_image_url;
    mockSmartPick.mockResolvedValue({ smart_pick: pick, empty_state: false });
    const { findByTestId, queryByTestId } = render(<SmartPickCard />);
    expect(await findByTestId('home-smart-pick-winner-image-placeholder')).toBeTruthy();
    expect(await findByTestId('home-smart-pick-runner-up-image-placeholder')).toBeTruthy();
    expect(queryByTestId('home-smart-pick-winner-image-img')).toBeNull();
  });

  it('mixed state — winner has URL, runner-up null', async () => {
    mockSmartPick.mockResolvedValue({
      smart_pick: basePick({
        winner_image_url: 'https://cdn.example.com/galaxy.jpg',
        runner_up_image_url: null,
      }),
      empty_state: false,
    });
    const { findByTestId, queryByTestId } = render(<SmartPickCard />);
    expect(await findByTestId('home-smart-pick-winner-image-img')).toBeTruthy();
    expect(await findByTestId('home-smart-pick-runner-up-image-placeholder')).toBeTruthy();
    expect(queryByTestId('home-smart-pick-winner-image-placeholder')).toBeNull();
    expect(queryByTestId('home-smart-pick-runner-up-image-img')).toBeNull();
  });

  it('swaps winner image to placeholder when onError fires', async () => {
    mockSmartPick.mockResolvedValue({
      smart_pick: basePick({
        winner_image_url: 'https://cdn.example.com/404.jpg',
        runner_up_image_url: null,
      }),
      empty_state: false,
    });
    const { findByTestId, queryByTestId } = render(<SmartPickCard />);
    const img = await findByTestId('home-smart-pick-winner-image-img');
    fireEvent(img, 'error');
    await waitFor(() => {
      expect(queryByTestId('home-smart-pick-winner-image-img')).toBeNull();
    });
    expect(await findByTestId('home-smart-pick-winner-image-placeholder')).toBeTruthy();
  });

  it('hides card entirely when empty_state is true (no image rendering)', async () => {
    mockSmartPick.mockResolvedValue({ smart_pick: null, empty_state: true });
    const { queryByTestId } = render(<SmartPickCard />);
    // Allow microtask flush so the promise resolves
    await waitFor(() => {
      expect(queryByTestId('home-smart-pick-winner-image-img')).toBeNull();
      expect(queryByTestId('home-smart-pick-winner-image-placeholder')).toBeNull();
    });
  });
});
