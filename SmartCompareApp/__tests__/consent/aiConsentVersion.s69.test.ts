/**
 * S69 U3 — the disclosure copy is fenced to AI_CONSENT_VERSION.
 *
 * A stored AI-processing consent counts only when its `version` equals
 * AI_CONSENT_VERSION (src/services/aiConsent.ts). The version is what ties a
 * user's "Agree" to the text they agreed to, so the text must not move under
 * it silently.
 *
 * RULE — when this test goes red:
 *   - A MATERIAL change to aiConsent.title or aiConsent.body (EN or AR) — what
 *     is sent, to whom, or what is not sent — must bump AI_CONSENT_VERSION
 *     (which re-asks every user who already consented) AND re-record
 *     PINNED.sha256 below, in the same change.
 *   - A typo / punctuation fix that changes no meaning may re-record
 *     PINNED.sha256 alone, keeping the version.
 *   Re-record with:
 *     node -e "const c=require('crypto'),E=require('./src/i18n/en.json'),A=require('./src/i18n/ar.json');console.log(c.createHash('sha256').update([E['aiConsent.title'],E['aiConsent.body'],A['aiConsent.title'],A['aiConsent.body']].join('\n'),'utf8').digest('hex'))"
 *   (run from SmartCompareApp/).
 *
 * The hashed string is [EN title, EN body, AR title, AR body] joined with '\n'.
 */

import { createHash } from 'crypto';

// __tests__/setup.ts maps the module to a "granted" stub; this fence needs the
// real constant. authService is stubbed so the real module loads without it.
jest.mock('../../src/services/authService', () => ({ getSavedUser: jest.fn() }));

const EN: Record<string, string> = require('../../src/i18n/en.json');
const AR: Record<string, string> = require('../../src/i18n/ar.json');

// S75 U3b (decision D3 = C): the body gained the OpenAI data-use sentence in
// EN and AR (a MATERIAL change), so the version became 2.
// S81-12 (consent v3, a MATERIAL change): the body names both AI providers,
// Anthropic and OpenAI, says that until the move to Anthropic is complete some
// or all requests, including photos, are processed by OpenAI, so the version
// is 3 and the digest is re-recorded in the same edit. The training sentence
// stays (S81-12 V3C, PATH C of item 26: OpenAI's data-sharing programme is
// still disclosed), directly after the transition sentence.
// S81-12 ARFIX (2026-11-12): the AR body's tense fix ('we are currently working
// on moving') changes no meaning, and v3 reached no phone: digest alone, version 3.
// S81-12 V3C (2026-11-12): main's training sentence returns beside the transition
// sentence; v3 reached no phone, so the digest is re-recorded with version 3.
const PINNED = {
  version: 3,
  sha256: '040af0c5904061a42e2750537fd0f4b305763e33e632ff890c9e5a1064a9886a',
};

function consentCopyDigest(): string {
  const parts = [EN['aiConsent.title'], EN['aiConsent.body'], AR['aiConsent.title'], AR['aiConsent.body']];
  for (const p of parts) {
    expect(typeof p === 'string' && p.length > 0).toBe(true);
  }
  return createHash('sha256').update(parts.join('\n'), 'utf8').digest('hex');
}

describe('S69 U3 — aiConsent copy <-> AI_CONSENT_VERSION fence', () => {
  it('the real AI_CONSENT_VERSION and the sha256 of aiConsent.title + aiConsent.body (EN then AR) match the pinned pair', () => {
    const { AI_CONSENT_VERSION } = jest.requireActual('../../src/services/aiConsent');
    expect({ version: AI_CONSENT_VERSION, sha256: consentCopyDigest() }).toEqual(PINNED);
  });
});
