import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';

describe('i18n translation files', () => {
  const enKeys = Object.keys(en).sort();
  const arKeys = Object.keys(ar).sort();

  it('English and Arabic have the same keys', () => {
    expect(enKeys).toEqual(arKeys);
  });

  it('no empty English values (except explicitly allowed)', () => {
    const allowedEmpty = ['onboarding.language.subtitle'];
    for (const [key, value] of Object.entries(en)) {
      if (allowedEmpty.includes(key)) continue;
      expect(value).not.toBe('');
    }
  });

  it('no empty Arabic values (except explicitly allowed)', () => {
    const allowedEmpty = ['onboarding.language.subtitle'];
    for (const [key, value] of Object.entries(ar)) {
      if (allowedEmpty.includes(key)) continue;
      expect(value).not.toBe('');
    }
  });

  it('interpolation variables match between EN and AR', () => {
    const interpolationRegex = /\{\{(\w+)\}\}/g;
    for (const key of enKeys) {
      const enMatches = [...(en as Record<string, string>)[key].matchAll(interpolationRegex)].map(m => m[1]).sort();
      const arMatches = [...(ar as Record<string, string>)[key].matchAll(interpolationRegex)].map(m => m[1]).sort();
      expect(arMatches).toEqual(enMatches);
    }
  });

  it('has app name in both languages', () => {
    expect((en as Record<string, string>)['app.name']).toBe('Qaren');
    expect((ar as Record<string, string>)['app.name']).toBe('قارن');
  });

  it('has all 9 category keys', () => {
    const categories = ['electronics', 'grocery', 'supplements', 'makeup', 'skincare', 'haircare', 'fragrances', 'fashion', 'other'];
    for (const cat of categories) {
      expect((en as Record<string, string>)[`home.categories.${cat}`]).toBeDefined();
      expect((ar as Record<string, string>)[`home.categories.${cat}`]).toBeDefined();
    }
  });

  it('has all 6 GCC region keys', () => {
    const regions = ['bahrain', 'saudi_arabia', 'uae', 'kuwait', 'qatar', 'oman'];
    for (const region of regions) {
      expect((en as Record<string, string>)[`onboarding.region.${region}`]).toBeDefined();
      expect((ar as Record<string, string>)[`onboarding.region.${region}`]).toBeDefined();
    }
  });
});
