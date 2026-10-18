/**
 * S79 B3-A item 3 -- the onboarding language step survives its own RTL
 * reload (spec C3, rows R12-R25; rulings A1 (the isolateModulesAsync
 * recipe), A5 (the RTL flag before the reload, per-key order), A6, A12
 * (MR1 = R20b, MR6 = R13b)).
 *
 * A1 recipe for every row that needs a fresh resume memo: inside
 * jest.isolateModulesAsync require the async-storage mock (a fresh, empty
 * store per isolate), plant the record with its setItem, then require react,
 * '@testing-library/react-native/pure' and the host INSIDE the isolate;
 * never render an isolated component with the outer RNTL; assert storage
 * through the isolate's AsyncStorage.
 *
 * onboardingResume does not exist at base: it is loaded through
 * loadResumeModule(), which turns a missing module into an assertion.
 */
/* eslint-disable @typescript-eslint/no-require-imports */

import React from 'react';
import { render, renderHook, fireEvent, act, waitFor } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = '@qaren_onboarding_resume_v1';
const RTL_KEY = '@qaren_rtl_bootstrapped';
const TTL = 10 * 60 * 1000;

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      language: mockI18nLang.value,
      changeLanguage: jest.fn(async (l: string) => {
        mockI18nLang.value = l;
      }),
    },
  }),
}));
const mockI18nLang = { value: 'en' };

jest.mock('../../src/i18n', () => ({
  saveLanguage: (lang: string) =>
    require('@react-native-async-storage/async-storage').default.setItem('@qaren_language', lang),
}));

const mockReloadAsync = jest.fn();
jest.mock('expo-updates', () => ({ reloadAsync: (...a: unknown[]) => mockReloadAsync(...a), isEnabled: true }));

const mockPutDemographics = jest.fn();
const mockSavePreferences = jest.fn();
const mockSaveAttribution = jest.fn();
jest.mock('../../src/services/api', () => ({
  putDemographics: (...a: unknown[]) => mockPutDemographics(...a),
  savePreferences: (...a: unknown[]) => mockSavePreferences(...a),
  saveAttribution: (...a: unknown[]) => mockSaveAttribution(...a),
  trackEvents: jest.fn().mockResolvedValue(undefined),
}));

const RN = require('react-native');

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function loadResumeModule(): any {
  try {
    return require('../../src/services/onboardingResume');
  } catch {
    return null;
  }
}

function record(over: Record<string, unknown> = {}): string {
  return JSON.stringify({ v: 1, step: 3, data: { language: 'ar' }, saved_at: Date.now(), ...over });
}

async function tick(n = 5) {
  for (let i = 0; i < n; i += 1) await new Promise((r) => setTimeout(r, 0));
}

interface Isolated {
  AS: any;
  React: any;
  TL: any;
  host: any;
}

/** A1 recipe: fresh registry, plant, then require react + RNTL pure + host. */
async function inIsolate(
  plant: (AS: any) => Promise<void> | void,
  body: (iso: Isolated) => Promise<void>,
  opts: { language?: 'en' | 'ar' } = {},
) {
  let thrown: unknown = null;
  await jest.isolateModulesAsync(async () => {
    const AS = require('@react-native-async-storage/async-storage').default;
    await AS.clear();
    await plant(AS);
    mockI18nLang.value = opts.language ?? 'en';
    jest.doMock('../../src/hooks/useLanguage', () => ({
      useLanguage: () => ({
        language: mockI18nLang.value,
        isRTL: mockI18nLang.value === 'ar',
        switchLanguage: jest.fn(),
      }),
    }));
    const ReactIso = require('react');
    const TL = require('@testing-library/react-native/pure');
    const host = require('../../src/screens/onboarding/NewOnboardingHost');
    await tick();
    try {
      await body({ AS, React: ReactIso, TL, host });
    } catch (e) {
      thrown = e;
    } finally {
      TL.cleanup();
    }
  });
  if (thrown) throw thrown;
}

const currentStep = (r: any) => r.getByTestId('onboarding-progress').props['data-current-step'];

beforeEach(async () => {
  jest.clearAllMocks();
  await AsyncStorage.clear();
  mockI18nLang.value = 'en';
  RN.I18nManager.isRTL = false;
  mockPutDemographics.mockResolvedValue({ success: true, cohort_match: null });
  mockSavePreferences.mockResolvedValue({ success: true });
  mockSaveAttribution.mockResolvedValue({ success: true });
});

// ---------------------------------------------------------------------------
// the service
// ---------------------------------------------------------------------------

describe('B3-A onboardingResume service (C3)', () => {
  it('r12 save then load returns the record once', async () => {
    let raw: string | null = null;
    await jest.isolateModulesAsync(async () => {
      const AS = require('@react-native-async-storage/async-storage').default;
      await AS.clear();
      const mod = loadResumeModule();
      expect(mod).not.toBeNull();
      expect(mod.ONBOARDING_RESUME_KEY).toBe(KEY);
      await mod.saveOnboardingResume({ step: 3, data: { language: 'ar' } });
      raw = await AS.getItem(KEY);
      const stored = JSON.parse(String(raw));
      expect(stored.v).toBe(1);
      expect(stored.step).toBe(3);
      expect(stored.data.language).toBe('ar');
      expect(typeof stored.saved_at).toBe('number');
    });
    await jest.isolateModulesAsync(async () => {
      const AS = require('@react-native-async-storage/async-storage').default;
      await AS.clear();
      await AS.setItem(KEY, String(raw));
      const mod = loadResumeModule();
      expect(mod).not.toBeNull();
      await expect(mod.loadOnboardingResume()).resolves.toEqual({ step: 3, data: { language: 'ar' } });
      expect(await AS.getItem(KEY)).toBeNull();
      expect(mod.peekOnboardingResume()).toEqual({ settled: true, value: { step: 3, data: { language: 'ar' } } });
    });
    await jest.isolateModulesAsync(async () => {
      const AS = require('@react-native-async-storage/async-storage').default;
      await AS.clear();
      const mod = loadResumeModule();
      expect(mod).not.toBeNull();
      await expect(mod.loadOnboardingResume()).resolves.toBeNull();
    });
  });

  const INVALID: [string, (now: number) => string][] = [
    ['older than the TTL', (now) => record({ saved_at: now - TTL - 1 })],
    ['61 s in the future', (now) => record({ saved_at: now + 61000 })],
    ['v 2', () => record({ v: 2 })],
    ['step 1', () => record({ step: 1 })],
    ['step 2', () => record({ step: 2 })],
    ['step 16', () => record({ step: 16 })],
    ['step 18', () => record({ step: 18 })],
    ['step 3.5', () => record({ step: 3.5 })],
    ['language fr', () => record({ data: { language: 'fr' } })],
    ['malformed JSON', () => '{"v":1,"step":3,'],
  ];

  it.each(INVALID)('r13 an invalid record (%s) loads as null and is removed', async (_label, make) => {
    await jest.isolateModulesAsync(async () => {
      const AS = require('@react-native-async-storage/async-storage').default;
      await AS.clear();
      const mod = loadResumeModule();
      expect(mod).not.toBeNull();
      expect(mod.RESUME_TTL_MS).toBe(TTL);
      await AS.setItem(KEY, make(Date.now()));
      await expect(mod.loadOnboardingResume()).resolves.toBeNull();
      expect(await AS.getItem(KEY)).toBeNull();
    });
  });

  it('r13 unknown data keys are dropped from a valid record', async () => {
    await jest.isolateModulesAsync(async () => {
      const AS = require('@react-native-async-storage/async-storage').default;
      await AS.clear();
      const mod = loadResumeModule();
      expect(mod).not.toBeNull();
      await AS.setItem(KEY, record({ step: 4, data: { language: 'en', evil: 'x', __proto__x: 1 } }));
      await expect(mod.loadOnboardingResume()).resolves.toEqual({ step: 4, data: { language: 'en' } });
    });
  });

  it('r13b (MR6) the TTL boundary: exactly TTL old is valid, TTL + 1 ms is not', async () => {
    const NOW = 1_800_000_000_000;
    const spy = jest.spyOn(Date, 'now').mockReturnValue(NOW);
    try {
      for (const [age, valid] of [
        [TTL, true],
        [TTL + 1, false],
      ] as [number, boolean][]) {
        await jest.isolateModulesAsync(async () => {
          const AS = require('@react-native-async-storage/async-storage').default;
          await AS.clear();
          const mod = loadResumeModule();
          expect(mod).not.toBeNull();
          await AS.setItem(KEY, record({ saved_at: NOW - age, step: 17 }));
          const got = await mod.loadOnboardingResume();
          expect({ age, got }).toEqual({ age, got: valid ? { step: 17, data: { language: 'ar' } } : null });
        });
      }
    } finally {
      spy.mockRestore();
    }
  });
});

// ---------------------------------------------------------------------------
// the hook (useLanguage)
// ---------------------------------------------------------------------------

describe('B3-A useLanguage beforeReload (C3, A5)', () => {
  const { useLanguage } = jest.requireActual('../../src/hooks/useLanguage');

  function wire(events: string[]) {
    (AsyncStorage.setItem as jest.Mock).mockImplementation(async (k: string, v: string) => {
      events.push(`setItem:${k}=${v}`);
      (AsyncStorage as any)._store[k] = v;
    });
    RN.I18nManager.forceRTL.mockImplementation((v: boolean) => events.push(`forceRTL:${v}`));
    mockReloadAsync.mockImplementation(async () => {
      events.push('reloadAsync');
    });
  }

  async function run(target: 'en' | 'ar', opts?: any) {
    const { result } = renderHook(() => useLanguage());
    await act(async () => {
      await result.current.switchLanguage(target, opts);
    });
  }

  const pos = (events: string[], e: string) => events.indexOf(e);
  const count = (events: string[], prefix: string) => events.filter((x) => x.startsWith(prefix)).length;

  it('r14 EN to AR: language saved < forceRTL(true) < beforeReload < RTL flag < reloadAsync, each once', async () => {
    const events: string[] = [];
    wire(events);
    mockI18nLang.value = 'en';
    RN.I18nManager.isRTL = false;
    const beforeReload = jest.fn(async () => {
      events.push('beforeReload');
    });
    await run('ar', { beforeReload });
    expect(beforeReload).toHaveBeenCalledTimes(1);
    expect(count(events, 'setItem:@qaren_language=')).toBe(1);
    expect(count(events, 'forceRTL:')).toBe(1);
    expect(count(events, `setItem:${RTL_KEY}=`)).toBe(1);
    expect(count(events, 'reloadAsync')).toBe(1);
    const a = pos(events, 'setItem:@qaren_language=ar');
    const b = pos(events, 'forceRTL:true');
    const c = pos(events, 'beforeReload');
    const d = pos(events, `setItem:${RTL_KEY}=rtl`);
    const e = pos(events, 'reloadAsync');
    expect([a >= 0, a < b, b < c, b < d, c < e, d < e]).toEqual([true, true, true, true, true, true]);
  });

  it('r15 AR to EN: the same order with forceRTL(false) and the ltr flag', async () => {
    const events: string[] = [];
    wire(events);
    mockI18nLang.value = 'ar';
    RN.I18nManager.isRTL = true;
    const beforeReload = jest.fn(async () => {
      events.push('beforeReload');
    });
    await run('en', { beforeReload });
    expect(beforeReload).toHaveBeenCalledTimes(1);
    const a = pos(events, 'setItem:@qaren_language=en');
    const b = pos(events, 'forceRTL:false');
    const c = pos(events, 'beforeReload');
    const d = pos(events, `setItem:${RTL_KEY}=ltr`);
    const e = pos(events, 'reloadAsync');
    expect([a >= 0, a < b, b < c, b < d, c < e, d < e]).toEqual([true, true, true, true, true, true]);
    expect(count(events, 'reloadAsync')).toBe(1);
  });

  it('r16 [PIN] no-reload paths call neither beforeReload nor reloadAsync; no opts keeps today', async () => {
    const events: string[] = [];
    wire(events);
    const beforeReload = jest.fn();
    // (a) same language
    mockI18nLang.value = 'ar';
    RN.I18nManager.isRTL = true;
    await run('ar', { beforeReload });
    // (b) language differs but the direction already matches
    mockI18nLang.value = 'en';
    RN.I18nManager.isRTL = true;
    await run('ar', { beforeReload });
    expect(beforeReload).not.toHaveBeenCalled();
    expect(mockReloadAsync).not.toHaveBeenCalled();
    expect(count(events, `setItem:${RTL_KEY}=`)).toBe(0);
    // (c) opts omitted on a reload path
    mockI18nLang.value = 'en';
    RN.I18nManager.isRTL = false;
    await run('ar');
    expect(mockReloadAsync).toHaveBeenCalledTimes(1);
  });

  it('r17 a rejecting beforeReload never blocks the reload', async () => {
    const events: string[] = [];
    wire(events);
    mockI18nLang.value = 'en';
    RN.I18nManager.isRTL = false;
    const beforeReload = jest.fn(() => Promise.reject(new Error('disk')));
    await run('ar', { beforeReload });
    expect(beforeReload).toHaveBeenCalledTimes(1);
    expect(mockReloadAsync).toHaveBeenCalledTimes(1);
  });

  it('r17 a never-settling beforeReload is bounded at 1500 ms', async () => {
    const events: string[] = [];
    wire(events);
    mockI18nLang.value = 'en';
    RN.I18nManager.isRTL = false;
    const beforeReload = jest.fn(() => new Promise<void>(() => undefined));
    jest.useFakeTimers();
    try {
      const { result } = renderHook(() => useLanguage());
      let p: Promise<void> | null = null;
      await act(async () => {
        p = result.current.switchLanguage('ar', { beforeReload });
        await jest.advanceTimersByTimeAsync(1500);
      });
      await act(async () => {
        await p;
      });
      expect(beforeReload).toHaveBeenCalledTimes(1);
      expect(mockReloadAsync).toHaveBeenCalledTimes(1);
    } finally {
      jest.useRealTimers();
    }
  });
});

// ---------------------------------------------------------------------------
// Step02Language and OnboardingFlow
// ---------------------------------------------------------------------------

describe('B3-A Step02 / OnboardingFlow wiring (C3)', () => {
  it('r18 Step02Language forwards beforeReload only when given onBeforeReload', async () => {
    const switchLanguage = jest.fn();
    await jest.isolateModulesAsync(async () => {
      jest.doMock('../../src/hooks/useLanguage', () => ({
        useLanguage: () => ({ language: 'en', isRTL: false, switchLanguage }),
      }));
      const ReactIso = require('react');
      const TL = require('@testing-library/react-native/pure');
      const { Step02Language } = require('../../src/screens/onboarding/Step02Language');
      try {
        const onBeforeReload = jest.fn(async () => undefined);
        const r = TL.render(ReactIso.createElement(Step02Language, { onChange: jest.fn(), onBeforeReload }));
        TL.fireEvent.press(r.getByTestId('lang-ar'));
        expect(switchLanguage).toHaveBeenCalledTimes(1);
        const call = switchLanguage.mock.calls[0];
        expect(call[0]).toBe('ar');
        expect(typeof call[1]?.beforeReload).toBe('function');
        await call[1].beforeReload();
        expect(onBeforeReload).toHaveBeenCalledWith('ar');

        switchLanguage.mockClear();
        r.rerender(ReactIso.createElement(Step02Language, { onChange: jest.fn() }));
        TL.fireEvent.press(r.getByTestId('lang-ar'));
        expect(switchLanguage.mock.calls[0]).toEqual(['ar']);
      } finally {
        TL.cleanup();
      }
    });
  });

  it.each([
    [true, 'lang-ar', 'ar'],
    [false, 'lang-ar', 'ar'],
    [true, 'lang-en', 'en'],
  ] as [boolean, string, 'en' | 'ar'][])(
    'r19 OnboardingFlow (isAuthenticated=%s) writes the step after the language step (%s)',
    async (isAuthenticated, testID, lang) => {
      const switchLanguage = jest.fn();
      await jest.isolateModulesAsync(async () => {
        const AS = require('@react-native-async-storage/async-storage').default;
        await AS.clear();
        jest.doMock('../../src/hooks/useLanguage', () => ({
          useLanguage: () => ({ language: lang === 'ar' ? 'en' : 'ar', isRTL: lang !== 'ar', switchLanguage }),
        }));
        const ReactIso = require('react');
        const TL = require('@testing-library/react-native/pure');
        const { OnboardingFlow } = require('../../src/screens/onboarding/OnboardingFlow');
        try {
          const r = TL.render(
            ReactIso.createElement(OnboardingFlow, { onComplete: jest.fn(), initialStep: 2, isAuthenticated }),
          );
          TL.fireEvent.press(r.getByTestId(testID));
          expect(switchLanguage).toHaveBeenCalledTimes(1);
          const opts = switchLanguage.mock.calls[0][1];
          expect(typeof opts?.beforeReload).toBe('function');
          await opts.beforeReload();
          const stored = JSON.parse(String(await AS.getItem(KEY)));
          expect(stored.v).toBe(1);
          expect(stored.step).toBe(3);
          expect(stored.data.language).toBe(lang);
        } finally {
          TL.cleanup();
        }
      });
    },
  );
});

// ---------------------------------------------------------------------------
// the host
// ---------------------------------------------------------------------------

describe('B3-A NewOnboardingHost resume (C3)', () => {
  it('r20 the host resumes at step 3 with Arabic kept (EN -> AR)', async () => {
    await inIsolate(
      (AS) => AS.setItem(KEY, record({ data: { language: 'ar' } })),
      async ({ AS, React: R, TL, host }) => {
        const r = TL.render(R.createElement(host.NewOnboardingHost, { onComplete: jest.fn() }));
        expect(currentStep(r)).toBe(3);
        TL.fireEvent.press(r.getByTestId('onboarding-back'));
        expect(currentStep(r)).toBe(2);
        expect(r.getByTestId('lang-ar').props.accessibilityState?.selected).toBe(true);
        expect(await AS.getItem(KEY)).toBeNull();
      },
      { language: 'ar' },
    );
  });

  it('r20b (MR1) the host resumes at step 3 with English kept (AR -> EN)', async () => {
    await inIsolate(
      (AS) => AS.setItem(KEY, record({ data: { language: 'en' } })),
      async ({ AS, React: R, TL, host }) => {
        const r = TL.render(R.createElement(host.NewOnboardingHost, { onComplete: jest.fn() }));
        expect(currentStep(r)).toBe(3);
        TL.fireEvent.press(r.getByTestId('onboarding-back'));
        expect(currentStep(r)).toBe(2);
        expect(r.getByTestId('lang-en').props.accessibilityState?.selected).toBe(true);
        expect(await AS.getItem(KEY)).toBeNull();
      },
      { language: 'en' },
    );
  });

  it('r21 a late-settling preload remounts at the resumed step', async () => {
    let release: (v: string) => void = () => undefined;
    const deferred = new Promise<string>((res) => {
      release = res;
    });
    await inIsolate(
      (AS) => {
        const orig = AS.getItem;
        AS.getItem = jest.fn((k: string) => (k === KEY ? deferred : orig(k)));
      },
      async ({ React: R, TL, host }) => {
        const r = TL.render(R.createElement(host.NewOnboardingHost, { onComplete: jest.fn() }));
        expect(r.getByTestId('onboarding-step-1')).toBeTruthy();
        await TL.act(async () => {
          release(record({ data: { language: 'ar' } }));
          await tick();
        });
        expect(currentStep(r)).toBe(3);
      },
      { language: 'ar' },
    );
  });

  it('r22 a stale record: step 1 synchronously and the key is removed', async () => {
    await inIsolate(
      (AS) => AS.setItem(KEY, record({ saved_at: Date.now() - TTL - 1 })),
      async ({ AS, React: R, TL, host }) => {
        const r = TL.render(R.createElement(host.NewOnboardingHost, { onComplete: jest.fn() }));
        expect(r.getByTestId('onboarding-step-1')).toBeTruthy();
        await TL.act(async () => {
          await tick();
        });
        expect(await AS.getItem(KEY)).toBeNull();
      },
    );
  });

  // Fix round FA1: the record is single use in memory too.
  it('r20c (FA1) a second full-mode mount in the same JS context starts at step 1; storage stays empty', async () => {
    await inIsolate(
      (AS) => AS.setItem(KEY, record({ data: { language: 'ar' } })),
      async ({ AS, React: R, TL, host }) => {
        const first = TL.render(R.createElement(host.NewOnboardingHost, { onComplete: jest.fn() }));
        expect(currentStep(first)).toBe(3);
        await TL.act(async () => {
          await tick();
        });
        first.unmount();
        const second = TL.render(R.createElement(host.NewOnboardingHost, { onComplete: jest.fn() }));
        await TL.act(async () => {
          await tick();
        });
        expect(second.queryByTestId('onboarding-step-1')).not.toBeNull();
        expect(await AS.getItem(KEY)).toBeNull();
      },
      { language: 'ar' },
    );
  });

  it('r20d (FA1) after clearOnboardingResume() the peek is settled-null and a mount renders step 1', async () => {
    await inIsolate(
      (AS) => AS.setItem(KEY, record({ data: { language: 'ar' } })),
      async ({ AS, React: R, TL, host }) => {
        const mod = require('../../src/services/onboardingResume');
        expect(mod.peekOnboardingResume()).toEqual({ settled: true, value: { step: 3, data: { language: 'ar' } } });
        await mod.clearOnboardingResume();
        expect(mod.peekOnboardingResume()).toEqual({ settled: true, value: null });
        const r = TL.render(R.createElement(host.NewOnboardingHost, { onComplete: jest.fn() }));
        await TL.act(async () => {
          await tick();
        });
        expect(r.queryByTestId('onboarding-step-1')).not.toBeNull();
        expect(await AS.getItem(KEY)).toBeNull();
      },
      { language: 'ar' },
    );
  });

  it('r22b (FA1) a record consumed by load but peeked 11 minutes later applies as null: step 1', async () => {
    const t0 = Date.now();
    const spy = jest.spyOn(Date, 'now').mockReturnValue(t0);
    try {
      await inIsolate(
        (AS) => AS.setItem(KEY, record({ saved_at: t0, data: { language: 'ar' } })),
        async ({ AS, React: R, TL, host }) => {
          const mod = require('../../src/services/onboardingResume');
          expect(mod.peekOnboardingResume()).toEqual({ settled: true, value: { step: 3, data: { language: 'ar' } } });
          expect(await AS.getItem(KEY)).toBeNull();
          spy.mockReturnValue(t0 + 11 * 60 * 1000);
          expect(mod.peekOnboardingResume()).toEqual({ settled: true, value: null });
          const r = TL.render(R.createElement(host.NewOnboardingHost, { onComplete: jest.fn() }));
          expect(r.queryByTestId('onboarding-step-1')).not.toBeNull();
        },
        { language: 'ar' },
      );
    } finally {
      spy.mockRestore();
    }
  });

  it('r23 [PIN] no record: step 1 renders synchronously', () => {
    const { NewOnboardingHost } = require('../../src/screens/onboarding/NewOnboardingHost');
    const r = render(<NewOnboardingHost onComplete={jest.fn()} />);
    expect(r.getByTestId('onboarding-step-1')).toBeTruthy();
  });

  it('r24 [PIN] edit mode ignores a settled record', async () => {
    await inIsolate(
      (AS) => AS.setItem(KEY, record({ data: { language: 'ar' } })),
      async ({ React: R, TL, host }) => {
        const r = TL.render(
          R.createElement(host.NewOnboardingHost, { onComplete: jest.fn(), mode: 'edit', onEditDone: jest.fn() }),
        );
        expect(currentStep(r)).toBe(8);
      },
    );
  });

  it('r25 completing the flow clears the record', async () => {
    jest.doMock('../../src/hooks/useLanguage', () => ({
      useLanguage: () => ({ language: 'en', isRTL: false, switchLanguage: jest.fn() }),
    }));
    const { NewOnboardingHost } = require('../../src/screens/onboarding/NewOnboardingHost');
    const r = render(
      <NewOnboardingHost
        onComplete={jest.fn()}
        initialStep={17}
        initialData={{ country: 'BH', age_group: '25-34', priorities: ['quality_reliability'], budget: 'mid', brand_attitude: 'best_of_both', attribution_source: 'instagram' } as any}
      />,
    );
    await AsyncStorage.setItem(KEY, record({ data: { language: 'en' } }));
    fireEvent.press(r.getByTestId('s17-not-now'));
    await waitFor(async () => {
      expect(await AsyncStorage.getItem(KEY)).toBeNull();
    });
  });
});
