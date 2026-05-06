import { motion } from '../../src/theme/motion';

describe('motion tokens — Phase 1', () => {
  it('exposes screenTransition with 320ms duration and bezier easing', () => {
    expect(motion.screenTransition.duration).toBe(320);
    expect(typeof motion.screenTransition.easing).toBe('function');
  });

  it('springConfig has chip / progress / tab presets', () => {
    expect(motion.springConfig.chip).toEqual({ damping: 14, stiffness: 200 });
    expect(motion.springConfig.progress).toEqual({ damping: 18, stiffness: 120 });
    expect(motion.springConfig.tab).toEqual({ damping: 12, stiffness: 180 });
  });

  it('variableEasing has fast / slow / snap segments', () => {
    expect(typeof motion.variableEasing.fast).toBe('function');
    expect(typeof motion.variableEasing.slow).toBe('function');
    expect(typeof motion.variableEasing.snap).toBe('function');
  });

  it('haptic uses confidence-only intensities (no scary error path)', () => {
    expect(motion.haptic.chip).toBe('light');
    expect(motion.haptic.stage).toBe('light');
    expect(motion.haptic.winner).toBe('medium');
    // explicit guard: nothing in haptic ever maps to a "warning"/"error"
    // intensity. The redesign principle (Section "Build Principles" #4)
    // forbids framing the app as scary, including via haptic feedback.
    expect(Object.values(motion.haptic)).not.toContain('warning');
    expect(Object.values(motion.haptic)).not.toContain('error');
    expect(Object.values(motion.haptic)).not.toContain('heavy');
  });
});
