import { fontFamily } from '../../src/theme/fonts';

describe('fonts module', () => {
  it('exposes Geist family for EN', () => {
    expect(fontFamily.en.regular).toBe('Geist-Regular');
    expect(fontFamily.en.semiBold).toBe('Geist-SemiBold');
    expect(fontFamily.en.bold).toBe('Geist-Bold');
  });

  it('keeps Cairo family for AR', () => {
    expect(fontFamily.ar.regular).toMatch(/Cairo/);
    expect(fontFamily.ar.semiBold).toMatch(/Cairo/);
    expect(fontFamily.ar.bold).toMatch(/Cairo/);
  });
});
