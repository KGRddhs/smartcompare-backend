/**
 * S81-12 LEGAL-V3 - client rows (consent v3 and the onboarding Step 5 copy).
 *
 * Spec: sc-s81-s12/.qa-s80/S81-12_UNIT_SPEC.md section 5 (client rows C1-C5), as amended by
 * RULINGS_S81_12.md: R-S12-1 (the consent v3 sheet names BOTH AI processors, Anthropic and
 * OpenAI; until the move is complete "some or all requests, including photos" go to OpenAI),
 * R-S12-4 (OpenAI's data-sharing programme ended: no training claim remains in the copy),
 * R-S12-8 (no catalog key added or removed), R-S08-3 (consent stays per account).
 *
 * NOT MEASURED in the RED run: sc-s81-s12 has no SmartCompareApp/node_modules (R-S12-12);
 * the orchestrator creates the junction before GREEN and these rows run there by path.
 *
 * Rows (all RED at base 98d85433, where AI_CONSENT_VERSION is 2 and the copy names OpenAI only):
 *   C1  the real AI_CONSENT_VERSION is 3 and the fence file pins version 3 with the digest of the
 *       current copy (sha256 of EN title + EN body + AR title + AR body joined by newlines)
 *   C2  a stored v2 record no longer counts; the next Agree writes a v3 record (distinct userId per
 *       case, the UB-R11 isolation: the AsyncStorage mock store is emptied before every case)
 *   C3  the v3 EN / AR body: four sentences, names Anthropic and OpenAI, the OpenAI transition
 *       sentence precedes the final not-sent sentence, no training claim, no opt-out wording, no
 *       Arabic diacritics except inside the brand token
 *   C4  the rendered consent sheet names Anthropic (and OpenAI)
 *   C5  Step05Trust renders the new "what reaches our AI providers" heading (fallback, EN, AR)
 *
 * Pure ASCII: the only Arabic below are regex escapes (the brand token and the diacritics range).
 */

import * as fs from 'fs';
import * as path from 'path';
import { createHash } from 'crypto';
import React from 'react';
import { render } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// __tests__/setup.ts maps aiConsent to a "granted" stub; these rows need the REAL module.
// Never { virtual: true }: the module exists.
jest.mock('../../src/services/aiConsent', () => jest.requireActual('../../src/services/aiConsent'));

const mockGetSavedUser = jest.fn();
jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

let mockMode: 'default' | 'en' | 'ar' = 'en';
jest.mock('react-i18next', () => {
  const catalogs: Record<string, Record<string, string>> = {
    en: require('../../src/i18n/en.json'),
    ar: require('../../src/i18n/ar.json'),
  };
  const t = (key: string, opts?: any) => {
    const fallback = typeof opts === 'string' ? opts : opts?.defaultValue;
    if (mockMode === 'default') return fallback ?? key;
    return catalogs[mockMode][key] ?? fallback ?? key;
  };
  return { useTranslation: () => ({ t, i18n: { language: mockMode === 'ar' ? 'ar' : 'en' } }) };
});

// eslint-disable-next-line @typescript-eslint/no-require-imports
const aiConsent = require('../../src/services/aiConsent');
const EN: Record<string, string> = require('../../src/i18n/en.json');
const AR: Record<string, string> = require('../../src/i18n/ar.json');
const STORE: Record<string, string> = (AsyncStorage as any)._store;

const ROOT = path.resolve(__dirname, '..', '..');
const FENCE = path.join(ROOT, '__tests__', 'consent', 'aiConsentVersion.s69.test.ts');

const SENTENCE_SPLIT = /(?<=[.!?\u061f])\s+/;
const NOT_SENT_EN = [/\b(?:not|never)\b|n't\b/i, /\b(?:send|sent|share|shared)\b/i, /\bname\b/i, /\bemail\b/i, /\baccount\b/i];
const TRAINING_CLAIM_EN = /\binform the evaluation and training of its models\b/i;
const OPT_OUT_EN = /\bopt(?:s|ed|ing)?[\s-]+out\b|\bturn(?:s|ed|ing)?\s+(?:it\s+|this\s+|sharing\s+)?off\b/i;
const BRAND_AR = '\u0645\u064a\u0651\u0632';
const DIACRITICS_AR = /[\u064b-\u0652]/;

function copyDigest(): string {
  const parts = [EN['aiConsent.title'], EN['aiConsent.body'], AR['aiConsent.title'], AR['aiConsent.body']];
  return createHash('sha256').update(parts.join('\n'), 'utf8').digest('hex');
}

beforeEach(() => {
  for (const k of Object.keys(STORE)) delete STORE[k];
  mockGetSavedUser.mockReset();
  mockMode = 'en';
});

describe('S81-12 C1 - consent version 3 and the re-pinned fence', () => {
  it('AI_CONSENT_VERSION is 3 and the fence pins {version: 3, sha256: digest of the current copy}', () => {
    expect(aiConsent.AI_CONSENT_VERSION).toBe(3);
    const fence = fs.readFileSync(FENCE, 'utf8');
    const version = /PINNED\s*=\s*\{\s*version:\s*([0-9]+)/.exec(fence);
    const sha = /sha256:\s*'([0-9a-f]{64})'/.exec(fence);
    expect(version && version[1]).toBe('3');
    expect(sha && sha[1]).toBe(copyDigest());
  });
});

describe('S81-12 C2 - a stored v2 record no longer counts', () => {
  // S81-12 F1-11 (RULINGS_FIX1_S81_12, E-row ECF1): consent is per account (R-S08-3), so the record
  // API takes the synthetic user id explicitly; the API itself is unchanged.
  it('v2 record -> not current; after Agree the stored record is version 3', async () => {
    const userId = 's81-12-c2-user-a';
    mockGetSavedUser.mockResolvedValue({ id: userId });
    STORE[aiConsent.aiConsentStorageKey(userId)] = JSON.stringify({ version: 2, at: '2026-10-01T00:00:00.000Z' });
    expect(await aiConsent.hasCurrentAiConsent(userId)).toBe(false);
    await aiConsent.recordAiConsent(userId);
    const stored = JSON.parse(STORE[aiConsent.aiConsentStorageKey(userId)] || '{}');
    expect(stored.version).toBe(3);
    expect(await aiConsent.hasCurrentAiConsent(userId)).toBe(true);
  });

  it('a v3 record (another user) counts', async () => {
    const userId = 's81-12-c2-user-b';
    mockGetSavedUser.mockResolvedValue({ id: userId });
    STORE[aiConsent.aiConsentStorageKey(userId)] = JSON.stringify({ version: 3, at: '2026-10-24T00:00:00.000Z' });
    expect(await aiConsent.hasCurrentAiConsent(userId)).toBe(true);
  });
});

describe('S81-12 C3 - the v3 consent body (EN and AR)', () => {
  it('EN: four sentences, both providers, transition before the final not-sent sentence, no training or opt-out claim', () => {
    const body = EN['aiConsent.body'];
    const sentences = body.split(SENTENCE_SPLIT).filter((s) => s.trim());
    expect(sentences.length).toBe(4);
    expect(body).toMatch(/\bAnthropic\b/);
    expect(body).toMatch(/\bOpenAI\b/);
    expect(sentences[2]).toMatch(/\bOpenAI\b/);
    expect(sentences[2]).toMatch(/\bsome or all\b/);
    for (const rx of NOT_SENT_EN) expect(sentences[3]).toMatch(rx);
    expect(body).not.toMatch(TRAINING_CLAIM_EN);
    expect(body).not.toMatch(OPT_OUT_EN);
  });

  it('AR: four sentences, both providers named, no diacritics outside the brand token', () => {
    const body = AR['aiConsent.body'];
    const sentences = body.split(SENTENCE_SPLIT).filter((s) => s.trim());
    expect(sentences.length).toBe(4);
    expect(body).toContain('Anthropic');
    expect(body).toContain('OpenAI');
    expect(sentences[2]).toContain('OpenAI');
    expect(DIACRITICS_AR.test(body.split(BRAND_AR).join(''))).toBe(false);
  });
});

describe('S81-12 C4 - the rendered sheet names Anthropic', () => {
  it('AiConsentSheet (EN) renders the body that names Anthropic and OpenAI', () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require('../../src/components/AiConsentSheet');
    const Sheet = mod.AiConsentSheet || mod.default;
    const screen = render(React.createElement(Sheet, { visible: true, onAgree: jest.fn(), onDecline: jest.fn(), onOpenPolicy: jest.fn() }));
    const text = JSON.stringify(screen.toJSON());
    expect(text).toContain('Anthropic');
    expect(text).toContain('OpenAI');
  });
});

describe('S81-12 C5 - Step05Trust names the AI providers', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { Step05Trust } = require('../../src/screens/onboarding/Step05Trust');
  const renderStep = () => JSON.stringify(render(React.createElement(Step05Trust, { onNext: jest.fn(), onBack: jest.fn() })).toJSON());

  it.each(['default', 'en', 'ar'] as const)('%s: the heading is not "What reaches OpenAI" and the body names Anthropic', (mode) => {
    mockMode = mode;
    const text = renderStep();
    expect(text).not.toContain('What reaches OpenAI');
    expect(text).toContain('Anthropic');
    if (mode !== 'ar') expect(text).toMatch(/AI providers?/);
  });
});
