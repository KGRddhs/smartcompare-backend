/**
 * Tests for `PaywallBanner` — renders in TwoInputShell's slot when
 * `canCompare === false`. Spec ref § 6.2 layout, § 8 analytics.
 * Plan ref: docs/superpowers/plans/2026-05-17-bundle-b-two-input-ux.md § 3.5.
 *
 * Coverage target: 80% on `SmartCompareApp/src/components/PaywallBanner.tsx`.
 *
 * THIS FILE LANDS IN PHASES:
 *   Phase 1 (NOW): import-contract stub. Fails with module-not-found until
 *     Frontend Opus commits the PaywallBanner.tsx skeleton.
 *   Phase 3 (LATER): behavioral assertions per plan § 3.5 (10 tests — render,
 *     tap analytics, RTL alignment, AR copy policy, no-close-affordance).
 */

describe('PaywallBanner — Phase 3 behavioral tests (RED until Frontend skeleton lands)', () => {
  it('imports the PaywallBanner module without throwing (skeleton must exist)', () => {
    expect(() => {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      require('../PaywallBanner');
    }).not.toThrow();
  });

  it.todo('renders title + body + CTA in English (Phase 3)');
  it.todo('renders the emerald-tinted icon (Phase 3)');
  it.todo('CTA tap fires onSeeOptions callback (Phase 3)');
  it.todo('CTA tap fires compare_entry_paywall_banner_tap analytics with mode payload (Phase 3)');
  it.todo('CTA tap fires compare_entry_paywall_banner_tap analytics with url mode payload (Phase 3)');
  it.todo('mount fires compare_entry_paywall_banner_view analytics once (Phase 3)');
  it.todo('does NOT double-fire view analytics on re-render (Phase 3)');
  it.todo('renders Arabic strings + RTL alignment in AR locale (Phase 3)');
  it.todo('AR copy passes .copy-policy.json (no تعذر / فشل) (Phase 3)');
  it.todo('renders NO close/dismiss affordance (spec § 6.2 — no escape hatch) (Phase 3)');
});
