/**
 * U8 T10 - LegalScreen serves the legal documents in the UI language.
 *
 * Spec: U8_LEGAL_REDRAFT_SPEC.md 4.8 (client files) and 4.10 T10; review C13
 * (the backend `lang` query parameter) and Q5; orchestrator rulings UL5 (no
 * bundled copy: the error state links to the landing page of the same
 * document and language, the URL constant lives beside the API base, and the
 * cache key becomes `legal_cache_{doc}_{lang}` so a cached DRAFT is never
 * shown offline after the deploy), UL13 (the server normalises `lang`) and
 * UL17 (what RED writes).
 *
 * Contract pinned here (GREEN implements it in src/screens/LegalScreen.tsx
 * and src/services/api.ts):
 *  - lang is 'ar' when the i18next UI language starts with 'ar', else 'en'
 *    (an undefined language gives 'en'). The language may be read from the
 *    react-i18next hook (`useTranslation().i18n.language`) or from the
 *    i18next singleton (`i18next.language`); both are driven from ONE value
 *    here, so either source passes.
 *  - The request is GET /api/v1/legal/{privacy_policy|terms_of_service} with
 *    exactly one query parameter, lang. Both call shapes pass:
 *    `api.get(path, { params: { lang } })` and `api.get(path + '?lang=..')`.
 *  - The cache key is `legal_cache_{doc}_{lang}`. The other language's key
 *    and the pre-U8 key `legal_cache_{doc}` are never read.
 *  - Error state (fetch failed, no cache for this language): exactly one
 *    element with the accessibility role "link"; pressing it calls
 *    Linking.openURL(`${LANDING_BASE_URL}/privacy.html` | `/terms.html`) for
 *    'en' and `${LANDING_BASE_URL}/ar/privacy.html` | `/ar/terms.html` for
 *    'ar'. `export const LANDING_BASE_URL = '<Railway landing host>';` sits
 *    beside `API_BASE_URL` in src/services/api.ts, and LegalScreen imports it
 *    from '../services/api' (no URL string literal in the screen).
 *
 * The twelve version/date anchors (spec 4.6) are not read or touched here.
 *
 * At base 1156f03c every node is RED except the one marked PIN.
 */
import * as fs from 'fs';
import * as path from 'path';
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Linking } from 'react-native';
// jest.mock calls below are hoisted above this import; every factory reads its
// mock* variable lazily, so the screen may be imported here.
import LegalScreen from '../../src/screens/LegalScreen';

/** The Railway landing host (getmyez.com does not serve the legal pages yet; UL5). */
const LANDING = 'https://qaren-landing-production.up.railway.app';

/** One UI language drives both possible sources (hook and singleton). */
let mockLanguage: string | undefined = 'en';

jest.mock('react-i18next', () => {
  // Stable objects, like the real hook; `language` reads the per-test value.
  const i18n = {
    get language() {
      return mockLanguage;
    },
  };
  const result = { t: (k: string) => k, i18n };
  return { useTranslation: () => result };
});

jest.mock('i18next', () => ({
  __esModule: true,
  default: {
    get language() {
      return mockLanguage;
    },
  },
}));

const mockGet = jest.fn();
jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: { get: (...args: unknown[]) => mockGet(...args) },
  API_BASE_URL: 'https://web-production-58776.up.railway.app',
  LANDING_BASE_URL: 'https://qaren-landing-production.up.railway.app',
}));

jest.mock('lucide-react-native', () => ({
  ChevronLeft: 'ChevronLeft',
}));

// Markdown stub: a host element carrying the raw markdown as its children.
jest.mock('react-native-markdown-display', () => {
  const MockReact = jest.requireActual<typeof import('react')>('react');
  return function Markdown({ children }: { children: string }) {
    return MockReact.createElement('mock-Markdown', { testID: 'md-content' }, children);
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

type Doc = 'privacy' | 'terms';

const ENDPOINT: Record<Doc, string> = {
  privacy: '/api/v1/legal/privacy_policy',
  terms: '/api/v1/legal/terms_of_service',
};

const APP_ROOT = path.resolve(__dirname, '..', '..');
const readApp = (rel: string) => fs.readFileSync(path.join(APP_ROOT, rel), 'utf8');

function renderScreen(doc: Doc) {
  return render(
    <LegalScreen
      navigation={{ goBack: jest.fn() } as any}
      route={{ params: { doc }, key: 'k', name: 'Legal' } as any}
    />,
  );
}

/** The request one api.get call made: its path and every query parameter, from either call shape. */
function requested(call: unknown[] | undefined): { path: string; params: Record<string, string> } | null {
  if (!call) return null;
  const [url, config] = call as [string, { params?: Record<string, unknown> } | undefined];
  const [p, qs = ''] = String(url).split('?');
  const params: Record<string, string> = {};
  new URLSearchParams(qs).forEach((v, k) => {
    params[k] = v;
  });
  for (const [k, v] of Object.entries(config?.params ?? {})) {
    if (v === undefined) continue;
    params[k] = k in params ? `${params[k]}|${String(v)}` : String(v);
  }
  return { path: p, params };
}

/** Waits until the load finished (fetch issued, loading state gone). */
async function settled(q: ReturnType<typeof renderScreen>) {
  await waitFor(() => expect(mockGet).toHaveBeenCalled());
  await waitFor(() => expect(q.queryByText('legal.loading')).toBeNull());
}

function shownState(q: ReturnType<typeof renderScreen>) {
  return {
    shown: q.queryByTestId('md-content')?.props.children ?? null,
    error: q.queryByText('legal.error.title') !== null,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  // Drop any queued once-value a failed test left behind, so nodes stay independent.
  mockGet.mockReset();
  mockLanguage = 'en';
  Object.keys(mockStore).forEach((k) => delete mockStore[k]);
});

describe('U8 T10 - LegalScreen requests the document in the UI language', () => {
  const LANG_CASES: [string | undefined, 'ar' | 'en'][] = [
    ['ar', 'ar'],
    ['ar-BH', 'ar'],
    ['en', 'en'],
    ['en-US', 'en'],
    ['fr', 'en'],
    [undefined, 'en'],
  ];

  describe.each(['privacy', 'terms'] as Doc[])('doc=%s', (doc) => {
    it.each(LANG_CASES)('UI language %p -> requests the endpoint with lang=%s', async (uiLang, lang) => {
      mockLanguage = uiLang;
      mockGet.mockResolvedValueOnce({ data: { content: '# Doc' } });
      renderScreen(doc);
      await waitFor(() => expect(mockGet).toHaveBeenCalled());
      expect(requested(mockGet.mock.calls[0])).toEqual({ path: ENDPOINT[doc], params: { lang } });
    });
  });
});

describe('U8 T10 - the offline cache is kept per document and language (UL5)', () => {
  it.each([
    ['privacy', 'ar'],
    ['terms', 'en'],
  ] as [Doc, string][])('a fetched %s copy under UI language %s is cached under legal_cache_{doc}_{lang} only', async (doc, uiLang) => {
    mockLanguage = uiLang;
    const md = `# ${doc} ${uiLang}`;
    mockGet.mockResolvedValueOnce({ data: { content: md } });
    const q = renderScreen(doc);
    await q.findByTestId('md-content');
    await waitFor(() => expect(mockStore).toEqual({ [`legal_cache_${doc}_${uiLang}`]: md }));
  });

  it('offline under Arabic: the Arabic cached copy is shown with the offline banner', async () => {
    mockLanguage = 'ar';
    mockStore['legal_cache_privacy_ar'] = '# AR cached';
    mockGet.mockRejectedValueOnce(new Error('network'));
    const q = renderScreen('privacy');
    await settled(q);
    expect(shownState(q)).toEqual({ shown: '# AR cached', error: false });
    expect(q.queryByText('legal.offline.banner')).not.toBeNull();
  });

  it('offline under Arabic: neither the English cache nor the pre-U8 key is shown (error state)', async () => {
    mockLanguage = 'ar';
    mockStore['legal_cache_privacy_en'] = '# EN cached';
    mockStore['legal_cache_privacy'] = '# pre-U8 cached DRAFT';
    mockGet.mockRejectedValueOnce(new Error('network'));
    const q = renderScreen('privacy');
    await settled(q);
    expect(shownState(q)).toEqual({ shown: null, error: true });
  });

  it('offline under English: the pre-U8 key legal_cache_terms is never read (error state)', async () => {
    mockLanguage = 'en';
    mockStore['legal_cache_terms'] = '# pre-U8 cached DRAFT';
    mockGet.mockRejectedValueOnce(new Error('network'));
    const q = renderScreen('terms');
    await settled(q);
    expect(shownState(q)).toEqual({ shown: null, error: true });
  });
});

describe('U8 T10 - the error state links to the landing page of the same document and language (UL5)', () => {
  it.each([
    ['privacy', 'en', 'privacy.html'],
    ['terms', 'en', 'terms.html'],
    ['privacy', 'ar', 'ar/privacy.html'],
    ['terms', 'ar', 'ar/terms.html'],
  ] as [Doc, string, string][])('doc=%s, UI language %s -> one link opening <landing>/%s', async (doc, uiLang, page) => {
    mockLanguage = uiLang;
    mockGet.mockRejectedValueOnce(new Error('network'));
    const q = renderScreen(doc);
    await q.findByText('legal.error.title');
    expect(q.queryByText('legal.error.retry')).not.toBeNull();
    const links = q.queryAllByRole('link');
    expect(links).toHaveLength(1);
    fireEvent.press(links[0]);
    await waitFor(() => expect(Linking.openURL).toHaveBeenCalledTimes(1));
    expect(Linking.openURL).toHaveBeenCalledWith(`${LANDING}/${page}`);
  });
});

describe('U8 T10 - the landing URL constant lives beside the API base (UL5)', () => {
  it('src/services/api.ts exports LANDING_BASE_URL (the Railway landing host) within 6 lines of API_BASE_URL', () => {
    const lines = readApp('src/services/api.ts').split(/\r?\n/);
    const apiAt = lines.findIndex((l) => /^export const API_BASE_URL = '/.test(l));
    const landingAt = lines.findIndex((l) => /^export const LANDING_BASE_URL = '/.test(l));
    const value = landingAt < 0 ? null : ((lines[landingAt].match(/= '([^']*)';/) ?? [])[1] ?? null);
    const beside = apiAt >= 0 && landingAt >= 0 && Math.abs(landingAt - apiAt) <= 6;
    expect({ value, beside }).toEqual({ value: LANDING, beside: true });
  });

  it('LegalScreen imports LANDING_BASE_URL from ../services/api and carries no URL string literal', () => {
    const src = readApp('src/screens/LegalScreen.tsx');
    const imports = /import[^;]*\bLANDING_BASE_URL\b[^;]*from '\.\.\/services\/api';/.test(src);
    const urlLiterals = src.match(/['"`]https?:\/\/[^'"`]*/g) ?? [];
    expect({ imports, urlLiterals }).toEqual({ imports: true, urlLiterals: [] });
  });

  it('PIN: the four landing pages the error-state link targets exist in landing/', () => {
    for (const page of ['privacy.html', 'terms.html', 'ar/privacy.html', 'ar/terms.html']) {
      const exists = fs.existsSync(path.resolve(APP_ROOT, '..', 'landing', page));
      expect({ page, exists }).toEqual({ page, exists: true });
    }
  });
});

// Polish round (UP4 B9, B10): appended cases; the cases above are unchanged.
describe('U8 polish - the error-state link and a language change', () => {
  it('B9: a rejecting Linking.openURL leaves no unhandled rejection', async () => {
    mockGet.mockRejectedValueOnce(new Error('network'));
    (Linking.openURL as jest.Mock).mockRejectedValueOnce(new Error('no handler for the URL'));
    const unhandled = jest.fn();
    process.on('unhandledRejection', unhandled);
    try {
      const q = renderScreen('privacy');
      await q.findByText('legal.error.title');
      fireEvent.press(q.getByRole('link'));
      await waitFor(() => expect(Linking.openURL).toHaveBeenCalledTimes(1));
      await new Promise((resolve) => setTimeout(resolve, 0));
      await new Promise((resolve) => setImmediate(resolve));
      expect(unhandled).not.toHaveBeenCalled();
    } finally {
      process.removeListener('unhandledRejection', unhandled);
    }
  });

  it('B10: after a language change whose fetch fails with no cache, the other language is not shown', async () => {
    mockGet.mockResolvedValueOnce({ data: { content: '# EN document' } });
    const q = renderScreen('privacy');
    await q.findByTestId('md-content');
    expect(shownState(q)).toEqual({ shown: '# EN document', error: false });
    mockLanguage = 'ar';
    mockGet.mockRejectedValueOnce(new Error('network'));
    q.rerender(
      <LegalScreen
        navigation={{ goBack: jest.fn() } as any}
        route={{ params: { doc: 'privacy' }, key: 'k', name: 'Legal' } as any}
      />,
    );
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(q.queryByText('legal.loading')).toBeNull());
    expect(requested(mockGet.mock.calls[1])).toEqual({ path: ENDPOINT.privacy, params: { lang: 'ar' } });
    expect(shownState(q)).toEqual({ shown: null, error: true });
  });

  it('B10: a language change that fetches the new document shows it', async () => {
    mockGet.mockResolvedValueOnce({ data: { content: '# EN document' } });
    const q = renderScreen('terms');
    await q.findByTestId('md-content');
    mockLanguage = 'ar';
    mockGet.mockResolvedValueOnce({ data: { content: '# AR document' } });
    q.rerender(
      <LegalScreen
        navigation={{ goBack: jest.fn() } as any}
        route={{ params: { doc: 'terms' }, key: 'k', name: 'Legal' } as any}
      />,
    );
    await waitFor(() => expect(shownState(q)).toEqual({ shown: '# AR document', error: false }));
  });
});
