/**
 * S75 U3b - AI consent v2 under decision D3 = C (2026-10-08): the organisation
 * shares the compare inputs and outputs with OpenAI, the sheet discloses it in
 * one sentence, and there is NO per-user opt-out (the Profile "Help improve AI
 * quality" toggle is gone). Spec: scratchpad/specs/U3B_CONSENT_V2_SPEC.md
 * section 3 (V1-V8) as amended by FABLE_RULINGS_U3B.md UB-R11 / UB-R12 / UB-R19.
 *
 * Contract pinned here (what the green must provide):
 *   - src/services/aiConsent.ts AI_CONSENT_VERSION === 2 (V1). A stored v1
 *     record no longer counts and the next Agree writes a v2 record over the
 *     same key - no migration (V2).
 *   - aiConsent.body (EN + AR) carries ONE new disclosure sentence placed
 *     immediately before the final "not sent" sentence: 4 sentences, the
 *     reassurance stays last (V3 / V4). The AR value is section 2 of
 *     U3B_AR_COPY.txt verbatim.
 *   - No opt-out wording anywhere in aiConsent.* (V5, pin: the T1.23 regexes).
 *   - __tests__/setup.ts mirrors the real constant (V6, pin).
 *   - profile.aiSharing.* is gone from both catalogs; key sets and counts stay
 *     equal (V7). No file under src/ names ai_sharing_enabled / aiSharing (V8).
 *
 * Isolation rule (UB-R11): every V2 case uses a DISTINCT userId AND the
 * AsyncStorage mock store (__mocks__/async-storage.ts, one module-global
 * `_store`) is emptied in beforeEach, so no case can pass on a record another
 * case persisted.
 *
 * Pure ASCII (UB-R19): the Arabic strings below are unicode escapes produced
 * by Python encode('ascii', 'backslashreplace') from U3B_AR_COPY.txt (sections
 * 1 and 2) and from the T1.23 OPT_OUT_AR regex; this file was written by
 * Python open().write and byte-checked (0 bytes > 127).
 */

import * as fs from 'fs';
import * as path from 'path';
import AsyncStorage from '@react-native-async-storage/async-storage';
import enCatalog from '../../src/i18n/en.json';
import arCatalog from '../../src/i18n/ar.json';
import {
  AI_CONSENT_VERSION,
  aiConsentStorageKey,
  ensureAiConsent,
  hasCurrentAiConsent,
} from '../../src/services/aiConsent';

// __tests__/setup.ts maps aiConsent to a "granted" stub; this file needs the
// REAL gate (jest.mock is hoisted above the imports by ts-jest). Never
// `{ virtual: true }`: the module exists (see the note in
// aiProcessingConsent.s69.test.tsx).
jest.mock('../../src/services/aiConsent', () => jest.requireActual('../../src/services/aiConsent'));

// The factory reads mockGetSavedUser lazily (inside the arrow), so the hoisted
// mock never touches the const before its initialisation.
const mockGetSavedUser = jest.fn();
jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

const EN = enCatalog as Record<string, string>;
const AR = arCatalog as Record<string, string>;
const STORE: Record<string, string> = (AsyncStorage as any)._store;

// The ONE new sentence (EN twin = U3B_AR_COPY.txt section 4; spec T-A) and the
// final sentence of the body at main 4c0f3c99 (en.json:705).
const EN_SENTENCE =
  'OpenAI may use these inputs and the outputs it generates from them to identify usage patterns, measure model quality and inform the evaluation and training of its models.';
const EN_FINAL = 'Your name, email and account details are not sent.';

// U3B_AR_COPY.txt section 1 (the sentence), the AR final sentence of the body
// at main (ar.json:702, last sentence) and section 2 (the whole target value).
const AR_SENTENCE = '\u0648\u0642\u062f \u062a\u0633\u062a\u062e\u062f\u0645 OpenAI \u0647\u0630\u0647 \u0627\u0644\u0645\u062f\u062e\u0644\u0627\u062a \u0648\u0627\u0644\u0645\u062e\u0631\u062c\u0627\u062a \u0627\u0644\u062a\u064a \u062a\u0646\u062a\u062c\u0647\u0627 \u0645\u0646\u0647\u0627 \u0644\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0623\u0646\u0645\u0627\u0637 \u0627\u0644\u0627\u0633\u062a\u062e\u062f\u0627\u0645 \u0648\u0642\u064a\u0627\u0633 \u062c\u0648\u062f\u0629 \u0627\u0644\u0646\u0645\u0627\u0630\u062c \u0648\u0627\u0644\u0627\u0633\u062a\u0639\u0627\u0646\u0629 \u0628\u0647\u0627 \u0641\u064a \u062a\u0642\u064a\u064a\u0645 \u0646\u0645\u0627\u0630\u062c\u0647\u0627 \u0648\u062a\u062f\u0631\u064a\u0628\u0647\u0627.';
const AR_FINAL = '\u0644\u0627 \u064a\u0631\u0633\u0644 \u0627\u0633\u0645\u0643 \u0623\u0648 \u0628\u0631\u064a\u062f\u0643 \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a \u0623\u0648 \u0628\u064a\u0627\u0646\u0627\u062a \u062d\u0633\u0627\u0628\u0643.';
const AR_SECTION2 = '\u0644\u062a\u062d\u062f\u064a\u062f \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a \u0648\u0643\u062a\u0627\u0628\u0629 \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629\u060c \u064a\u0631\u0633\u0644 \u0645\u064a\u0651\u0632 \u0625\u0644\u0649 OpenAI \u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a \u0623\u0648 \u0627\u0644\u0631\u0648\u0627\u0628\u0637 (\u0645\u0639 \u0646\u0635 \u0635\u0641\u062d\u0627\u062a\u0647\u0627) \u0623\u0648 \u0627\u0644\u0635\u0648\u0631 \u0627\u0644\u062a\u064a \u062a\u0644\u062a\u0642\u0637\u0647\u0627 \u0623\u0648 \u062a\u062e\u062a\u0627\u0631\u0647\u0627. \u0648\u0642\u062f \u064a\u0631\u0633\u0644 \u0623\u064a\u0636\u0627 \u0627\u0644\u062a\u0641\u0636\u064a\u0644\u0627\u062a \u0627\u0644\u0645\u062d\u0641\u0648\u0638\u0629 \u0641\u064a \u0645\u0644\u0641\u0643 \u0627\u0644\u0634\u062e\u0635\u064a (\u0648\u0645\u0646\u0647\u0627 \u062a\u0641\u0636\u064a\u0644\u0627\u062a \u0645\u0642\u062a\u0631\u062d\u0629 \u0628\u0646\u0627\u0621 \u0639\u0644\u0649 \u0625\u062c\u0627\u0628\u0627\u062a\u0643 \u0641\u064a \u0623\u0633\u0626\u0644\u0629 \u0627\u0644\u0628\u062f\u0627\u064a\u0629)\u060c \u0645\u062b\u0644 \u0627\u0644\u0623\u0648\u0644\u0648\u064a\u0627\u062a \u0648\u0641\u0626\u0629 \u0627\u0644\u0645\u064a\u0632\u0627\u0646\u064a\u0629\u060c \u0648\u0628\u0644\u062f\u0643 \u0648\u0644\u063a\u062a\u0643 \u0648\u0645\u0646\u0637\u0642\u062a\u0643. \u0648\u0642\u062f \u062a\u0633\u062a\u062e\u062f\u0645 OpenAI \u0647\u0630\u0647 \u0627\u0644\u0645\u062f\u062e\u0644\u0627\u062a \u0648\u0627\u0644\u0645\u062e\u0631\u062c\u0627\u062a \u0627\u0644\u062a\u064a \u062a\u0646\u062a\u062c\u0647\u0627 \u0645\u0646\u0647\u0627 \u0644\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0623\u0646\u0645\u0627\u0637 \u0627\u0644\u0627\u0633\u062a\u062e\u062f\u0627\u0645 \u0648\u0642\u064a\u0627\u0633 \u062c\u0648\u062f\u0629 \u0627\u0644\u0646\u0645\u0627\u0630\u062c \u0648\u0627\u0644\u0627\u0633\u062a\u0639\u0627\u0646\u0629 \u0628\u0647\u0627 \u0641\u064a \u062a\u0642\u064a\u064a\u0645 \u0646\u0645\u0627\u0630\u062c\u0647\u0627 \u0648\u062a\u062f\u0631\u064a\u0628\u0647\u0627. \u0644\u0627 \u064a\u0631\u0633\u0644 \u0627\u0633\u0645\u0643 \u0623\u0648 \u0628\u0631\u064a\u062f\u0643 \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a \u0623\u0648 \u0628\u064a\u0627\u0646\u0627\u062a \u062d\u0633\u0627\u0628\u0643.';

// Verbatim copies of __tests__/consent/aiProcessingConsent.s69.test.tsx T1.23
// (:755 OPT_OUT_EN incl. "you can stop", :757 OPT_OUT_AR) per UB-R12: the two
// pins must agree. The AR words: turn off / cancel / settings / disable.
const OPT_OUT_EN = /opt[\s-]?out|turn (it )?off|switch (it )?off|toggle|disable|settings|you can stop/i;
const OPT_OUT_AR = /\u0625\u064a\u0642\u0627\u0641|\u0625\u0644\u063a\u0627\u0621|\u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a|\u062a\u0639\u0637\u064a\u0644/;
const AR_OPT_OUT_WORDS = ['\u0625\u064a\u0642\u0627\u0641', '\u0625\u0644\u063a\u0627\u0621', '\u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a', '\u062a\u0639\u0637\u064a\u0644'];

const CONSENT_KEYS = ['aiConsent.title', 'aiConsent.body', 'aiConsent.link', 'aiConsent.agree', 'aiConsent.notNow'];

const SRC_DIR = path.resolve(__dirname, '../../src');

function walkSrc(dir: string, out: string[]): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkSrc(full, out);
    } else if (/\.(ts|tsx|json)$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

function countOf(haystack: string, needle: string): number {
  return haystack.split(needle).length - 1;
}

beforeEach(() => {
  jest.clearAllMocks();
  for (const key of Object.keys(STORE)) delete STORE[key];
});

describe('S75 U3b V1 - the consent version', () => {
  it('V1 AI_CONSENT_VERSION is 2 (the disclosure changed materially: D3 = C)', () => {
    expect(AI_CONSENT_VERSION).toBe(2);
  });
});

describe('S75 U3b V2 - a v1 record no longer counts; the next Agree writes v2 (distinct userId per case)', () => {
  it('V2a a stored {version: 1} record is NOT current consent', async () => {
    const userId = 'u3b-v2-a';
    STORE[aiConsentStorageKey(userId)] = JSON.stringify({ version: 1, at: '2026-09-29T12:00:00.000Z' });
    expect(await hasCurrentAiConsent(userId)).toBe(false);
  });

  it('V2b a stored {version: 1} record: ensureAiConsent asks once and the stored record becomes version 2', async () => {
    const userId = 'u3b-v2-b';
    const key = aiConsentStorageKey(userId);
    STORE[key] = JSON.stringify({ version: 1, at: '2026-09-29T12:00:00.000Z' });
    mockGetSavedUser.mockResolvedValue({ id: userId, display_name: 'K', email: 'k@example.com' });
    const ask = jest.fn(async () => true);

    expect(await ensureAiConsent(ask)).toBe(true);
    expect(ask).toHaveBeenCalledTimes(1);
    const stored = JSON.parse(STORE[key]);
    expect(stored.version).toBe(2);
    expect(typeof stored.at).toBe('string');
  });

  it('V2c a stored {version: 2} record skips the sheet (ask is not called) and is left as it is', async () => {
    const userId = 'u3b-v2-c';
    const key = aiConsentStorageKey(userId);
    const raw = JSON.stringify({ version: 2, at: '2026-10-09T12:00:00.000Z' });
    STORE[key] = raw;
    mockGetSavedUser.mockResolvedValue({ id: userId, display_name: 'K', email: 'k@example.com' });
    const ask = jest.fn(async () => true);

    expect(await ensureAiConsent(ask)).toBe(true);
    expect(ask).not.toHaveBeenCalled();
    expect(STORE[key]).toBe(raw);
  });
});

describe('S75 U3b V3 / V4 - the disclosure sentence sits before the final sentence (EN + AR)', () => {
  it('V3 EN body: the sentence appears exactly once, immediately precedes the final sentence, the body still ends with it, 4 sentences', () => {
    const body = EN['aiConsent.body'] ?? '';
    expect({ occurrences: countOf(body, EN_SENTENCE) }).toEqual({ occurrences: 1 });
    expect({ precedesFinal: body.endsWith(`${EN_SENTENCE} ${EN_FINAL}`) }).toEqual({ precedesFinal: true });
    expect({ endsWithFinal: body.endsWith(EN_FINAL) }).toEqual({ endsWithFinal: true });
    expect({ separators: countOf(body, '. ') }).toEqual({ separators: 3 });
  });

  it('V4 AR body: the same three checks with the AR sentence and AR final sentence, and the value is U3B_AR_COPY.txt section 2', () => {
    const body = AR['aiConsent.body'] ?? '';
    expect({ occurrences: countOf(body, AR_SENTENCE) }).toEqual({ occurrences: 1 });
    expect({ precedesFinal: body.endsWith(`${AR_SENTENCE} ${AR_FINAL}`) }).toEqual({ precedesFinal: true });
    expect({ endsWithFinal: body.endsWith(AR_FINAL) }).toEqual({ endsWithFinal: true });
    expect({ separators: countOf(body, '. ') }).toEqual({ separators: 3 });
    expect(body).toBe(AR_SECTION2);
  });
});

describe('S75 U3b V5 (pin) - no opt-out is promised anywhere in the sheet copy', () => {
  it('V5 every EN aiConsent.* value fails OPT_OUT_EN and every AR value carries none of the AR opt-out words', () => {
    for (const k of CONSENT_KEYS) {
      expect({ k, en: OPT_OUT_EN.test(EN[k] ?? 'MISSING opt-out') }).toEqual({ k, en: false });
      expect({ k, ar: OPT_OUT_AR.test(AR[k] ?? AR_OPT_OUT_WORDS[0]) }).toEqual({ k, ar: false });
      for (const w of AR_OPT_OUT_WORDS) {
        expect({ k, w, hit: (AR[k] ?? w).includes(w) }).toEqual({ k, w, hit: false });
      }
    }
  });
});

describe('S75 U3b V6 (pin) - __tests__/setup.ts mirrors the real constant', () => {
  it('V6 the AI_CONSENT_VERSION in the global granted mock equals the real AI_CONSENT_VERSION', () => {
    const setupSrc = fs.readFileSync(path.resolve(__dirname, '../setup.ts'), 'utf8');
    const m = setupSrc.match(/AI_CONSENT_VERSION:\s*(\d+)/);
    expect(m).not.toBeNull();
    expect({ setup: Number(m![1]), real: AI_CONSENT_VERSION }).toEqual({
      setup: AI_CONSENT_VERSION,
      real: AI_CONSENT_VERSION,
    });
  });
});

describe('S75 U3b V7 / V8 - the toggle is gone from the catalogs and from src/', () => {
  it('V7 no key starts with profile.aiSharing in EN or AR; key sets equal; counts equal', () => {
    const stray = [...Object.keys(EN), ...Object.keys(AR)].filter((k) => k.startsWith('profile.aiSharing'));
    expect(stray).toEqual([]);
    expect(Object.keys(AR).sort()).toEqual(Object.keys(EN).sort());
    expect(Object.keys(AR).length).toBe(Object.keys(EN).length);
  });

  it('V8 no file under src/ (.ts / .tsx / .json) contains ai_sharing_enabled or aiSharing', () => {
    const hits: string[] = [];
    for (const file of walkSrc(SRC_DIR, [])) {
      const text = fs.readFileSync(file, 'utf8');
      if (text.includes('ai_sharing_enabled') || text.includes('aiSharing')) {
        hits.push(path.relative(SRC_DIR, file).split(path.sep).join('/'));
      }
    }
    expect(hits.sort()).toEqual([]);
  });
});
