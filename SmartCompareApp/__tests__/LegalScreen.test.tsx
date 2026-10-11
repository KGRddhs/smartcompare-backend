/**
 * LegalScreen — Bundle A Task 4.6
 *
 * Contract (Bundle A design §6.2 + plan Task 2.8):
 * - fetches /api/v1/legal/privacy_policy for doc='privacy'
 * - fetches /api/v1/legal/terms_of_service for doc='terms'
 * - shows skeleton (ActivityIndicator) while loading
 * - renders markdown content on success
 * - on fetch fail with cached copy: renders cache + offline banner
 * - on fetch fail with NO cache: shows error + retry button
 * - "Try again" button triggers re-fetch
 *
 * Why these assertions: legal docs must work offline once seen at least
 * once (App Store reviewers must always be able to read them). The
 * offline-banner / retry distinction is the user-visible signal.
 *
 * U8 amendment (rulings UL5, UL17): the request now carries the UI language
 * as the `lang` query parameter (English here) and the offline cache key is
 * `legal_cache_{doc}_{lang}`. The language rules, the per-language cache and
 * the error-state landing link are pinned in
 * __tests__/legal/legalScreenLang.u8.test.tsx.
 */

import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';

const mockGet = jest.fn();
jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: { get: (...args: any[]) => mockGet(...args) },
}));

jest.mock('react-i18next', () => {
  // U8: LegalScreen reads the UI language; stable objects, like the real hook.
  const result = { t: (k: string) => k, i18n: { language: 'en' } };
  return { useTranslation: () => result };
});

jest.mock('lucide-react-native', () => ({
  ChevronLeft: 'ChevronLeft',
}));

// react-native-markdown-display renders to text — stub to a View with the
// raw markdown as children for easy assertion.
jest.mock('react-native-markdown-display', () => {
  const React = require('react');
  return function Markdown({ children }: { children: string }) {
    return React.createElement('mock-Markdown', { testID: 'md-content' }, children);
  };
});

const mockStore: Record<string, string> = {};
jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn((k: string) => Promise.resolve(mockStore[k] ?? null)),
    setItem: jest.fn((k: string, v: string) => {
      mockStore[k] = v;
      return Promise.resolve();
    }),
    removeItem: jest.fn((k: string) => {
      delete mockStore[k];
      return Promise.resolve();
    }),
  },
}));

import LegalScreen from '../src/screens/LegalScreen';

function renderScreen(doc: 'privacy' | 'terms' = 'privacy') {
  return render(
    <LegalScreen
      navigation={{ goBack: jest.fn() } as any}
      route={{ params: { doc }, key: 'k', name: 'Legal' } as any}
    />,
  );
}

/** U8: path + every query parameter of one api.get call, from either call shape. */
function requested(call: any[] | undefined): { path: string; params: Record<string, string> } | null {
  if (!call) return null;
  const [url, config] = call;
  const [p, qs = ''] = String(url).split('?');
  const params: Record<string, string> = {};
  new URLSearchParams(qs).forEach((v, k) => {
    params[k] = v;
  });
  for (const [k, v] of Object.entries((config?.params ?? {}) as Record<string, unknown>)) {
    if (v !== undefined) params[k] = String(v);
  }
  return { path: p, params };
}

describe('LegalScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.keys(mockStore).forEach((k) => delete mockStore[k]);
  });

  it('fetches the privacy endpoint for doc="privacy" (lang=en)', async () => {
    mockGet.mockResolvedValueOnce({ data: { content: '# Privacy' } });
    renderScreen('privacy');
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(requested(mockGet.mock.calls[0])).toEqual({
      path: '/api/v1/legal/privacy_policy',
      params: { lang: 'en' },
    });
  });

  it('fetches the terms endpoint for doc="terms" (lang=en)', async () => {
    mockGet.mockResolvedValueOnce({ data: { content: '# Terms' } });
    renderScreen('terms');
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    expect(requested(mockGet.mock.calls[0])).toEqual({
      path: '/api/v1/legal/terms_of_service',
      params: { lang: 'en' },
    });
  });

  it('renders the markdown content on success', async () => {
    mockGet.mockResolvedValueOnce({ data: { content: '# Hello world' } });
    const { findByTestId } = renderScreen('privacy');
    const md = await findByTestId('md-content');
    expect(md.props.children).toBe('# Hello world');
  });

  it('on fetch fail with cached copy: renders cache + offline banner', async () => {
    mockStore['legal_cache_privacy_en'] = '# Cached privacy';
    mockGet.mockRejectedValueOnce(new Error('network'));

    const { findByTestId, findByText } = renderScreen('privacy');

    const md = await findByTestId('md-content');
    expect(md.props.children).toBe('# Cached privacy');
    await findByText('legal.offline.banner');
  });

  it('on fetch fail with NO cache: shows error + retry button', async () => {
    mockGet.mockRejectedValueOnce(new Error('network'));
    const { findByText } = renderScreen('privacy');
    await findByText('legal.error.title');
    await findByText('legal.error.retry');
  });

  it('"Try again" button triggers a re-fetch', async () => {
    mockGet
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ data: { content: '# Recovered' } });

    const { findByText, findByTestId } = renderScreen('privacy');
    const retryBtn = await findByText('legal.error.retry');
    await act(async () => {
      fireEvent.press(retryBtn);
    });

    const md = await findByTestId('md-content');
    expect(md.props.children).toBe('# Recovered');
    expect(mockGet).toHaveBeenCalledTimes(2);
  });

  it('persists fetched content to AsyncStorage cache', async () => {
    mockGet.mockResolvedValueOnce({ data: { content: '# Stored' } });
    renderScreen('terms');
    await waitFor(() => expect(mockStore['legal_cache_terms_en']).toBe('# Stored'));
  });
});
