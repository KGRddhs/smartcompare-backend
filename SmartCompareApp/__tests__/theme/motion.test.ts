import { motion } from '../../src/theme/motion';

/**
 * Banned motion primitives — Build Principle #4 (never frame the app as scary).
 * No motion token name OR token-string value may contain any of these substrings.
 * Spring physics (damping/stiffness) is allowed; the WORD "bounce" used as a
 * token name is not. See docs/plans/2026-05-26-bundle-e-visual-fidelity-design.md
 * § 3.3 Motion infrastructure.
 */
const BANNED_MOTION_PRIMITIVES = ['shake', 'wobble', 'jitter', 'bounce'] as const;

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

describe('motion tokens — Bundle E extensions', () => {
  // These tokens land in src/theme/motion.ts during S0.2 (frontend lane).
  // The block is RED until that extension lands. See plan § S0.2.

  it('screenTransition mirrors under RTL', () => {
    // S0.2: motion.screenTransition gains mirrorRTL: true so SlideTransition
    // wrapper knows to invert translateX direction when I18nManager.isRTL.
    const st = motion.screenTransition as { duration: number; easing: unknown; mirrorRTL?: boolean };
    expect(st.mirrorRTL).toBe(true);
  });

  it('exposes accordionChevron with 220ms ease (DetailsAccordion S0.3)', () => {
    expect((motion as any).accordionChevron).toBeDefined();
    expect((motion as any).accordionChevron.duration).toBe(220);
    expect(typeof (motion as any).accordionChevron.easing).toBe('function');
  });

  it('exposes ctaGlow with 240ms easing + emerald shadow color', () => {
    const t = (motion as any).ctaGlow;
    expect(t).toBeDefined();
    expect(t.duration).toBe(240);
    expect(typeof t.easing).toBe('function');
    expect(t.shadowColor).toBe('#10B981');
    expect(typeof t.shadowRadius).toBe('number');
    expect(t.shadowRadius).toBeGreaterThan(0);
  });

  it('exposes modeSegment with 180ms bezier (ModeSegment active-pill slide)', () => {
    const t = (motion as any).modeSegment;
    expect(t).toBeDefined();
    expect(t.duration).toBe(180);
    expect(typeof t.easing).toBe('function');
  });

  it('exposes shimmer with 1400ms linear loop (skeleton placeholders)', () => {
    const t = (motion as any).shimmer;
    expect(t).toBeDefined();
    expect(t.duration).toBe(1400);
    expect(typeof t.easing).toBe('function');
    expect(t.repeat).toBe(-1);
  });

  it('exposes counterTick with 2400ms ease-out-cubic (LoadingRings counter)', () => {
    const t = (motion as any).counterTick;
    expect(t).toBeDefined();
    expect(t.duration).toBe(2400);
    expect(typeof t.easing).toBe('function');
  });

  it('exposes revealBurst with particle + badge spring parameters', () => {
    const t = (motion as any).revealBurst;
    expect(t).toBeDefined();
    expect(t.particleEmit).toBe(600);
    expect(t.particleFall).toBe(800);
    expect(t.badgeSpring).toEqual({ damping: 8, stiffness: 100 });
  });
});

describe('motion tokens — Build Principle #4 banned-vocab guard', () => {
  // Walk every key + every string-valued leaf in the motion object.
  // No banned primitive (shake/wobble/jitter/bounce) may appear as a token
  // name OR as a string value. Spring physics damping/stiffness are numbers,
  // not strings, so springConfig is unaffected; this guard catches a future
  // commit that adds e.g. motion.cardBounce or { easing: 'shake' }.

  function walk(obj: unknown, path: string, hits: string[]): void {
    if (obj === null || obj === undefined) return;
    if (typeof obj === 'string') {
      for (const banned of BANNED_MOTION_PRIMITIVES) {
        if (obj.toLowerCase().includes(banned)) {
          hits.push(`${path} = "${obj}" contains banned primitive "${banned}"`);
        }
      }
      return;
    }
    if (typeof obj === 'function' || typeof obj === 'number' || typeof obj === 'boolean') {
      return;
    }
    if (typeof obj === 'object') {
      for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
        for (const banned of BANNED_MOTION_PRIMITIVES) {
          if (k.toLowerCase().includes(banned)) {
            hits.push(`${path}.${k} key contains banned primitive "${banned}"`);
          }
        }
        walk(v, path ? `${path}.${k}` : k, hits);
      }
    }
  }

  it('no token name uses shake/wobble/jitter/bounce', () => {
    const hits: string[] = [];
    walk(motion, 'motion', hits);
    expect(hits).toEqual([]);
  });

  it('no token string value uses shake/wobble/jitter/bounce', () => {
    // Redundant with above (walk covers both) — kept as an explicit anchor
    // for code reviewers. If a future commit adds e.g. { mode: 'wobble' },
    // this fails loudly.
    const serialized = JSON.stringify(motion, (_k, v) =>
      typeof v === 'function' ? '<easing-fn>' : v,
    ).toLowerCase();
    for (const banned of BANNED_MOTION_PRIMITIVES) {
      expect(serialized).not.toContain(banned);
    }
  });
});
