/**
 * CohortBarChart tests — Phase 2 Task 16.
 * Hero illustration #2 used on Onboarding screen 12 ("388 GCC shoppers
 * helped train this") per design Section 5b.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { CohortBarChart } from '../../../src/components/illustrations/CohortBarChart';

describe('CohortBarChart', () => {
  it('renders an Svg root with default props', () => {
    const { UNSAFE_root } = render(<CohortBarChart />);
    const svg = UNSAFE_root.findByType('Svg' as any);
    expect(svg).toBeTruthy();
  });

  it('renders 4 bars when default bars are used', () => {
    const { UNSAFE_root } = render(<CohortBarChart />);
    // Bars are Rect elements tagged with testID="cohort-bar-{i}".
    const bars = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('cohort-bar-')
    );
    expect(bars.length).toBe(4);
  });

  it('renders the user-provided number of total dots (default 388)', () => {
    const { UNSAFE_root } = render(<CohortBarChart />);
    const dots = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('cohort-dot-')
    );
    expect(dots.length).toBe(388);
  });

  it('respects custom total prop', () => {
    const { UNSAFE_root } = render(<CohortBarChart total={100} />);
    const dots = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('cohort-dot-')
    );
    expect(dots.length).toBe(100);
  });

  it('highlights exactly userCohortSize dots in emerald', () => {
    const { UNSAFE_root } = render(<CohortBarChart userCohortSize={12} />);
    const emeraldDots = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('cohort-dot-') &&
        n.props.fill === '#10B981'
    );
    expect(emeraldDots.length).toBe(12);
  });

  it('respects custom userCohortSize', () => {
    const { UNSAFE_root } = render(<CohortBarChart userCohortSize={5} />);
    const emeraldDots = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('cohort-dot-') &&
        n.props.fill === '#10B981'
    );
    expect(emeraldDots.length).toBe(5);
  });

  it('clamps userCohortSize to total when oversized', () => {
    const { UNSAFE_root } = render(<CohortBarChart total={10} userCohortSize={50} />);
    const emeraldDots = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('cohort-dot-') &&
        n.props.fill === '#10B981'
    );
    expect(emeraldDots.length).toBe(10);
  });

  it('the highlighted bar uses emerald fill', () => {
    const bars = [
      { label: 'Quality', value: 0.45, highlighted: true },
      { label: 'Price', value: 0.30 },
      { label: 'Brand', value: 0.15 },
      { label: 'Design', value: 0.10 },
    ];
    const { UNSAFE_root } = render(<CohortBarChart bars={bars} />);
    const bar0 = UNSAFE_root.findByProps({ testID: 'cohort-bar-0' });
    expect(bar0.props.fill).toBe('#10B981');
    const bar1 = UNSAFE_root.findByProps({ testID: 'cohort-bar-1' });
    expect(bar1.props.fill).not.toBe('#10B981');
  });

  it('non-highlighted bars use a neutral gray', () => {
    const bars = [
      { label: 'A', value: 0.5, highlighted: true },
      { label: 'B', value: 0.5 },
      { label: 'C', value: 0.5 },
      { label: 'D', value: 0.5 },
    ];
    const { UNSAFE_root } = render(<CohortBarChart bars={bars} />);
    const bar1 = UNSAFE_root.findByProps({ testID: 'cohort-bar-1' });
    // Should be the design's border.medium #D1D5DB (or similar gray family).
    expect(bar1.props.fill).toBe('#D1D5DB');
  });

  it('bar height is proportional to value', () => {
    const bars = [
      { label: 'A', value: 1.0 },
      { label: 'B', value: 0.5 },
      { label: 'C', value: 0.25 },
      { label: 'D', value: 0.1 },
    ];
    const { UNSAFE_root } = render(<CohortBarChart bars={bars} />);
    const bar0 = UNSAFE_root.findByProps({ testID: 'cohort-bar-0' });
    const bar1 = UNSAFE_root.findByProps({ testID: 'cohort-bar-1' });
    const bar3 = UNSAFE_root.findByProps({ testID: 'cohort-bar-3' });
    // Heights are numeric props on Rect.
    const h0 = Number(bar0.props.height);
    const h1 = Number(bar1.props.height);
    const h3 = Number(bar3.props.height);
    expect(h1).toBeCloseTo(h0 * 0.5, 0);
    expect(h3).toBeCloseTo(h0 * 0.1, 0);
  });

  it('caption shows {total} GCC shoppers', () => {
    const { getByText } = render(<CohortBarChart total={388} />);
    expect(getByText(/388/)).toBeTruthy();
    expect(getByText(/GCC/)).toBeTruthy();
  });

  it('clamps bars to first 4 when more than 4 provided', () => {
    const bars = [
      { label: 'A', value: 0.4 },
      { label: 'B', value: 0.3 },
      { label: 'C', value: 0.15 },
      { label: 'D', value: 0.1 },
      { label: 'E', value: 0.05 },
    ];
    const { UNSAFE_root } = render(<CohortBarChart bars={bars} />);
    const all = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('cohort-bar-')
    );
    expect(all.length).toBe(4);
  });

  it('pads to 4 bars when fewer than 4 provided', () => {
    const bars = [
      { label: 'A', value: 0.5 },
      { label: 'B', value: 0.3 },
    ];
    const { UNSAFE_root } = render(<CohortBarChart bars={bars} />);
    const all = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('cohort-bar-')
    );
    expect(all.length).toBe(4);
  });
});
