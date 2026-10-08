/**
 * S74 CLIENT-TRUTH - share sheet truth (AR-1, decision SHARE=A).
 *
 * Spec CLIENT_TRUTH_SPEC.md section 2 (C1, C2, C4) + section 8 rows CT-S1..CT-S4,
 * amended by FABLE_RULINGS_CLIENT_TRUTH.md CT1 (pin the rewritten reward line),
 * CT2 (hide the reward block at the cap; the copy carries LIFETIME_CAP) and
 * CT7 (the share error path always shows the generic catalog copy).
 *
 * At main dfbda511 the sheet renders "+1 Deep Review credit now" (a credit
 * nothing consumes), a placeholder link "https://qaren.app/r/QR-XXXXXX", the
 * reward line "+5 comparisons if they sign up" (wrong trigger: Loop 2 fires on
 * the invitee's first comparison; wrong tier: premium gets 10; no 7-day
 * expiry), shows the reward block even at the device lifetime cap, and puts
 * raw axios / backend English text on the error line.
 *
 * Catalog-backed t: a local react-i18next mock resolving from the REAL
 * src/i18n/{en,ar}.json (pattern honestCounts.s69.test.tsx:41-55), language
 * switched per test through mockLang. Backend constants are read
 * cross-package from app/services/referral_service.py (the CT-Y3 pattern).
 * Pure ASCII: Arabic is written as \u escapes.
 */
import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';

let mockLang: 'en' | 'ar' = 'en';

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  notificationAsync: jest.fn(),
  impactAsync: jest.fn(),
  NotificationFeedbackType: { Success: 'Success', Error: 'Error' },
  ImpactFeedbackStyle: { Light: 'Light' },
}));

jest.mock('react-i18next', () => {
  const cats: Record<string, Record<string, string>> = {
    en: require('../../src/i18n/en.json'),
    ar: require('../../src/i18n/ar.json'),
  };
  const t = (key: string, opts?: Record<string, unknown>) => {
    const cat = cats[mockLang];
    let str: string =
      cat[key] ?? cats.en[key] ?? (opts?.defaultValue as string | undefined) ?? key;
    if (opts && typeof opts === 'object') {
      for (const [k, v] of Object.entries(opts)) {
        if (k === 'defaultValue') continue;
        str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
      }
    }
    return str;
  };
  return { useTranslation: () => ({ t, i18n: { language: mockLang } }) };
});

const mockCreateShare = jest.fn();
jest.mock('../../src/services/referralService', () => {
  class FakeReferralError extends Error {
    code: string;
    status: number | null;
    constructor(message: string, code = 'UNKNOWN', status: number | null = null) {
      super(message);
      this.code = code;
      this.status = status;
    }
  }
  return {
    createShare: (...args: unknown[]) => mockCreateShare(...args),
    ReferralError: FakeReferralError,
  };
});

jest.mock('../../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: jest.fn(async () => 'fp-test'),
}));

import ShareBottomSheet from '../../src/components/ShareBottomSheet';

const EN = en as unknown as Record<string, string>;
const AR = ar as unknown as Record<string, string>;

const REPO = path.resolve(__dirname, '../../..');
const SHEET_SOURCE = fs.readFileSync(
  path.resolve(__dirname, '../../src/components/ShareBottomSheet.tsx'),
  'utf8',
);
const REFERRAL_SERVICE_PY = fs.readFileSync(
  path.join(REPO, 'app/services/referral_service.py'),
  'utf8',
);

function pyIntConstant(name: string): number {
  const m = REFERRAL_SERVICE_PY.match(new RegExp(`^${name}\\s*=\\s*(\\d+)\\s*$`, 'm'));
  if (!m) throw new Error(`${name} not found in app/services/referral_service.py`);
  return Number(m[1]);
}

/** Integers written in a catalog value (ASCII, Arabic-Indic and extended Arabic-Indic digits). */
function integersIn(value: string): number[] {
  const western = value
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
    .replace(/[\u06f0-\u06f9]/g, (d) => String(d.charCodeAt(0) - 0x06f0));
  return (western.match(/[0-9]+/g) ?? []).map(Number);
}

/** Every string rendered anywhere in the tree. */
function allText(screen: any): string[] {
  const out: string[] = [];
  const walk = (node: any) => {
    if (node == null) return;
    if (typeof node === 'string' || typeof node === 'number') {
      out.push(String(node));
      return;
    }
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    walk(node.children);
  };
  walk(screen.toJSON());
  return out;
}

const COMPARISON = {
  id: 'cmp-123',
  productA: 'iPhone 15',
  productB: 'Galaxy S24',
  winnerName: 'iPhone 15',
};

function renderSheet(extra: Record<string, unknown> = {}) {
  return render(
    <ShareBottomSheet
      visible
      comparison={COMPARISON}
      onClose={jest.fn()}
      onShared={jest.fn()}
      {...extra}
    />,
  );
}

const FALSE_RENDERED = [/Deep Review/i, /QR-X{6}/, /qaren\.app\/r\//];

beforeEach(() => {
  mockLang = 'en';
  mockCreateShare.mockReset();
});

describe('S74 CLIENT-TRUTH share sheet (rendered)', () => {
  it('CT-S1 EN: no Deep Review claim, no placeholder link; the reward line is the catalog reward.later', () => {
    mockLang = 'en';
    const texts = allText(renderSheet());
    const hits = texts.filter((s) => FALSE_RENDERED.some((re) => re.test(s)));
    expect(hits).toEqual([]);
    expect(texts).toContain(EN['referrals.share.reward.later']);
  });

  it('CT-S2 AR: no Deep Review claim, no placeholder link; the reward line is the catalog reward.later', () => {
    mockLang = 'ar';
    const texts = allText(renderSheet());
    const hits = texts.filter((s) => FALSE_RENDERED.some((re) => re.test(s)));
    expect(hits).toEqual([]);
    expect(texts).toContain(AR['referrals.share.reward.later']);
  });

  it('CT2: the reward block is hidden at the device lifetime cap (lifetimeRemaining 0)', () => {
    const { queryByTestId } = renderSheet({ lifetimeRemaining: 0 });
    // The gift-thanks banner proves the at-cap branch rendered.
    expect(queryByTestId('share-max-reached-banner') !== null).toBe(true);
    expect({ rewardBlockRendered: queryByTestId('share-reward-block') !== null }).toEqual({
      rewardBlockRendered: false,
    });
  });

  it('CT2 GUARD: the reward block still renders below the cap and when the cap is unknown', () => {
    expect(renderSheet().queryByTestId('share-reward-block')).not.toBeNull();
    expect(renderSheet({ lifetimeRemaining: 2 }).queryByTestId('share-reward-block')).not.toBeNull();
  });

  it('CT7: a raw-message ReferralError renders the generic catalog copy, never the raw text', async () => {
    const { ReferralError } = jest.requireMock('../../src/services/referralService');
    const raw = 'Request failed with status code ' + '500';
    mockCreateShare.mockRejectedValueOnce(new ReferralError(raw, 'UNKNOWN', 500));
    const generic = EN['referrals.share.error.generic'];
    expect(typeof generic).toBe('string');
    const screen = renderSheet();
    fireEvent.press(screen.getByTestId('share-target-whatsapp'));
    await waitFor(() => expect(mockCreateShare).toHaveBeenCalledTimes(1));
    // Wait until the error line has rendered (whichever text it carries).
    await waitFor(() =>
      expect(allText(screen).some((s) => s === raw || s === generic)).toBe(true),
    );
    const texts = allText(screen);
    expect(texts.filter((s) => s.includes(raw))).toEqual([]);
    expect(texts).toContain(generic);
  });

  it('Y8: before any target tap no rendered text carries the head of the outgoing message (EN and AR)', () => {
    const hits: string[] = [];
    for (const [lang, cat] of [
      ['en', EN],
      ['ar', AR],
    ] as const) {
      const head = cat['referrals.share.messageWithLink'].split('{{link}}')[0].trim();
      expect(head.length).toBeGreaterThan(10);
      mockLang = lang;
      const texts = allText(renderSheet());
      hits.push(...texts.filter((s) => s.includes(head)).map((s) => `${lang}: ${s}`));
    }
    expect(mockCreateShare).not.toHaveBeenCalled();
    expect(hits).toEqual([]);
  });
});

describe('S74 CLIENT-TRUTH referral catalog values', () => {
  const EN_FALSE = /Deep Review|this week|weekly|2\s*\u00d7/i;
  // "Deep Review"; "this week" (\u0647\u0630\u0627 \u0627\u0644\u0623\u0633\u0628\u0648\u0639); "deeper" (\u0623\u0639\u0645\u0642).
  const AR_FALSE = /Deep Review|\u0647\u0630\u0627 \u0627\u0644\u0623\u0633\u0628\u0648\u0639|\u0623\u0639\u0645\u0642/;

  it('CT-S3: no referrals.* value claims a Deep Review credit, a weekly allowance or 2x deeper reviews (EN and AR)', () => {
    const enHits = Object.keys(EN).filter(
      (k) => k.startsWith('referrals.') && EN_FALSE.test(EN[k]),
    );
    const arHits = Object.keys(AR).filter(
      (k) => k.startsWith('referrals.') && AR_FALSE.test(AR[k]),
    );
    expect({ en: enHits, ar: arHits }).toEqual({ en: [], ar: [] });
  });

  it('CT1 + Y10: referrals.share.reward.later is true to Loop 2 (no +5 / +10 / "if they sign up"; BONUS_EXPIRY_DAYS days; signs up; first comparison)', () => {
    const days = pyIntConstant('BONUS_EXPIRY_DAYS');
    expect(days).toBeGreaterThan(0);
    const enLine = EN['referrals.share.reward.later'];
    const arLine = AR['referrals.share.reward.later'];
    const problems: string[] = [];
    for (const [lang, line] of [
      ['EN', enLine],
      ['AR', arLine],
    ] as const) {
      if (line.includes('+5')) problems.push(`${lang} carries +5`);
      if (line.includes('+10')) problems.push(`${lang} carries +10`);
    }
    if (/if they sign up/i.test(enLine)) problems.push('EN says "if they sign up"');
    if (!enLine.includes(`${days} days`)) problems.push(`EN lacks "${days} days"`);
    if (!/signs? up/i.test(enLine)) problems.push('EN lacks "signs up"');
    if (!/first comparison/i.test(enLine)) problems.push('EN lacks "first comparison"');
    expect(problems).toEqual([]);
  });

  it('CT2: the reward line carries the device lifetime cap read from referral_service.LIFETIME_CAP ("up to N friends")', () => {
    const cap = pyIntConstant('LIFETIME_CAP');
    const days = pyIntConstant('BONUS_EXPIRY_DAYS');
    expect(cap).toBeGreaterThan(0);
    const enLine = EN['referrals.share.reward.later'];
    const arLine = AR['referrals.share.reward.later'];
    const m = enLine.match(/up to ([0-9]+) friends?/i);
    // Exactly the cap and the expiry days are the numbers the line carries.
    const expected = Array.from(new Set([cap, days])).sort((a, b) => a - b);
    const numbers = (line: string) => Array.from(new Set(integersIn(line))).sort((a, b) => a - b);
    expect({
      enUpToFriends: m ? Number(m[1]) : null,
      enNumbers: numbers(enLine),
      arNumbers: numbers(arLine),
    }).toEqual({ enUpToFriends: cap, enNumbers: expected, arNumbers: expected });
  });
});

describe('S74 CLIENT-TRUTH ShareBottomSheet.tsx source', () => {
  it('CT-S4: no quoted QR-XXXXXX placeholder literal, no Deep Review, no WEEKLY_INVITE_CAP branch, no +5 literal', () => {
    const lineHits = (re: RegExp) =>
      SHEET_SOURCE.split(/\r?\n/)
        .map((l, i) => `${i + 1}: ${l.trim()}`)
        .filter((l) => re.test(l));
    expect({
      quotedPlaceholder: SHEET_SOURCE.match(/['"][^'"\n]*QR-X{6}['"]/g) ?? [],
      deepReview: lineHits(/Deep Review/),
      weeklyCap: lineHits(/WEEKLY_INVITE_CAP/),
      plusFive: lineHits(/\+5/),
    }).toEqual({ quotedPlaceholder: [], deepReview: [], weeklyCap: [], plusFive: [] });
  });
});
