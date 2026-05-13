/**
 * HeroRings — Bundle E Phase 3 Task 3.1 RED scaffold.
 *
 * Plan: docs/plans/2026-05-13-results-quality-overhaul.md
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 3.
 *
 * Two SVG radial rings side by side that show each product's calibrated
 * overall score (70-95 range per Decision 4). Top-match ring fills
 * emerald (`colors.accent`), runner-up fills neutral gray
 * (`colors.text.secondary`). **Never orange or red on a score** — the
 * design doc § 3 calls orange/red on a score "psychological poison."
 *
 * Visual contract per Decision 3:
 *   - Diameter 88px, stroke 8px (phone width).
 *   - Animated fill 0 → score (Reanimated worklet, 600ms ease-out).
 *   - Center label: integer, then "/100" smaller weight below.
 *   - No adjective labels ("Great" / "Excellent").
 *
 * BLOCKED ON: backend Task 1.6 — scoring_v2 SSE shape with
 * `overall_score.product_a/b` calibrated 70-95. Component path is
 * `src/components/results/HeroRings.tsx` (to be created). These tests
 * fail with `Cannot find module ...` until that file lands — that is the
 * intended RED signal for the GREEN-cycle harness.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

// HeroRings is the unit under test. Import will fail at RED time — the
// component doesn't exist yet. When Phase 3 Task 3.1 lands, the module
// resolves, `@ts-expect-error` flips to an error of its own (no
// unused-suppression), and the next contributor is forced to remove it
// — a self-disarming TDD breadcrumb that also keeps the baseline tsc
// exit code at 0 while other agents work in parallel.
/* eslint-disable import/no-unresolved -- RED scaffold: Phase 3 Task 3.1 creates src/components/results/HeroRings.tsx; remove this directive when the module lands. */
// @ts-expect-error Phase 3 Task 3.1 will create src/components/results/HeroRings.tsx
import { HeroRings } from '../../src/components/results/HeroRings';
/* eslint-enable import/no-unresolved */

import { colors } from '../../src/theme';

describe('HeroRings — Bundle E Phase 3 § Decision 3', () => {
  it('renders two SVG rings with 88px diameter and 8px stroke', () => {
    const { UNSAFE_getAllByType } = render(
      <HeroRings
        scoreA={87}
        scoreB={82}
        labelA="Glorious Model O"
        labelB="Ducky One 2 Mini"
        winnerIndex={0}
        testID="hero-rings"
      />,
    );
    // Each ring uses two <Circle> primitives — a track + a foreground
    // arc. Two rings × 2 circles = 4 total. Lower bound only because
    // implementation may add a center gradient or hairline.
    const circles = UNSAFE_getAllByType('Circle' as any);
    expect(circles.length).toBeGreaterThanOrEqual(4);
    // Every visible circle must declare diameter 88 (radius 44) and
    // stroke 8. SVG primitives accept r as a string or number — coerce
    // before comparing.
    for (const c of circles) {
      const r = Number(c.props.r);
      const sw = Number(c.props.strokeWidth);
      expect(r).toBe(44);
      expect(sw).toBe(8);
    }
  });

  it('paints the winner ring emerald and the runner-up ring neutral gray (no orange or red)', () => {
    const { UNSAFE_getAllByType } = render(
      <HeroRings
        scoreA={87}
        scoreB={82}
        labelA="Glorious Model O"
        labelB="Ducky One 2 Mini"
        winnerIndex={0}
        testID="hero-rings"
      />,
    );
    const circles = UNSAFE_getAllByType('Circle' as any);
    // Sweep every stroke prop on every circle. The only allowed colors
    // on a score ring are emerald (`colors.accent`) for the winner and
    // neutral gray (`colors.text.secondary`) for the runner-up, plus
    // the always-permitted border track color (`colors.border.light`).
    // Orange (`colors.warning` = #F59E0B) and red (`colors.destructive`
    // = #EF4444) are banned anywhere on the ring per design § 3.
    const bannedColors = [
      colors.warning, // #F59E0B
      colors.destructive, // #EF4444
      '#F59E0B',
      '#EF4444',
      '#F59',
      '#dc2',
      '#FB923C',
      '#FCA5A5',
    ];
    for (const c of circles) {
      const stroke = String(c.props.stroke ?? '').toLowerCase();
      for (const banned of bannedColors) {
        expect(stroke).not.toContain(banned.toLowerCase());
      }
    }
    // Positive: at least one circle uses emerald `colors.accent`.
    const strokes = circles.map((c) => String(c.props.stroke ?? ''));
    expect(strokes.some((s) => s.toLowerCase().includes(colors.accent.toLowerCase()))).toBe(true);
    // Positive: at least one circle uses the neutral gray for the runner-up.
    expect(
      strokes.some(
        (s) =>
          s.toLowerCase().includes(colors.text.secondary.toLowerCase()) ||
          s.toLowerCase().includes(colors.border.medium.toLowerCase()),
      ),
    ).toBe(true);
  });

  it('exposes the calibrated scores and winner index via host node props', () => {
    // The Reanimated worklet animates `progress` shared values on the
    // UI thread; we don't try to time-travel through frames in jest.
    // Instead we assert the host node exposes the *target* values via
    // data-* props so the parent can verify the worklet got the right
    // input. Implementation pattern: pass `progress.value` through to
    // a host node's `data-progress-a/b` so a snapshot/runtime probe
    // (or a worklet-thread crash regression) can be caught by tests.
    const { getByTestId } = render(
      <HeroRings
        scoreA={87}
        scoreB={82}
        labelA="Glorious Model O"
        labelB="Ducky One 2 Mini"
        winnerIndex={0}
        testID="hero-rings"
      />,
    );
    const root = getByTestId('hero-rings');
    expect(root.props['data-score-a']).toBe(87);
    expect(root.props['data-score-b']).toBe(82);
    expect(root.props['data-winner-index']).toBe(0);
  });
});

/**
 * RED→GREEN trajectory:
 *
 *  1. Pre-Phase-3 (backend Task 1.6 not yet landed): module
 *     `src/components/results/HeroRings.tsx` does not exist. All 3
 *     assertions error out at import — `Cannot find module ...`.
 *  2. Phase 3 Task 3.1 lands the component reading `scoreA`/`scoreB`
 *     from `scoring.overall_score` in the new contract. All 3 pass.
 *  3. Implementation must use ONLY emerald + neutral gray on the rings.
 *     Any later refactor that introduces destructive red or warning
 *     orange on the score ring trips assertion (2) — the banned-color
 *     sweep is broad enough to catch hex literals, theme aliases, and
 *     opacity-stripped variants.
 */
