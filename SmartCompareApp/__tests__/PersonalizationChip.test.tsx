// Bundle C — PersonalizationChip RED tests (Section C plan C.8.3 / C.8.4 / C.8.5).
//
// Spec §7a + 7b + 7c: compact qualitative chip below verdict. Arrows only,
// never magnitudes/percentages. Hidden when no shifts. i18n EN + AR.
//
// RED until B.7/B.8 land the PersonalizationChip component at
// src/components/results/PersonalizationChip.tsx.

import React from 'react';
import { render } from '@testing-library/react-native';
import { expectNoForbiddenStrings, expectNoMagnitudeStrings } from './_bundle_c_helpers';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, vars?: Record<string, string>) => {
      // Identity mock with template interpolation for chip_template
      if (vars && typeof vars === 'object') {
        let out = key;
        for (const [k, v] of Object.entries(vars)) {
          out = out.replace(`{{${k}}}`, String(v));
        }
        return out;
      }
      return key;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

// Lazy-import so file collects pre-impl.
function importComponent() {
  try {
    return require('../src/components/results/PersonalizationChip').default;
  } catch {
    return null;
  }
}

describe('PersonalizationChip (Bundle C §7)', () => {
  it('hidden when appliedShifts is empty array', () => {
    const PersonalizationChip = importComponent();
    if (!PersonalizationChip) {
      throw new Error(
        'RED: PersonalizationChip not yet implemented at src/components/results/PersonalizationChip.tsx (B.7/B.8 pending)',
      );
    }
    const { toJSON } = render(<PersonalizationChip appliedShifts={[]} />);
    // Empty render — either null or container with no children
    const tree = toJSON();
    if (tree && typeof tree === 'object' && !Array.isArray(tree)) {
      expect(tree.children == null || tree.children.length === 0).toBe(true);
    }
  });

  it('hidden when appliedShifts is null or undefined', () => {
    const PersonalizationChip = importComponent();
    if (!PersonalizationChip) {
      throw new Error('RED: PersonalizationChip not yet implemented');
    }
    const { toJSON: t1 } = render(
      <PersonalizationChip appliedShifts={null as any} />,
    );
    const tree1 = t1();
    if (tree1 && typeof tree1 === 'object' && !Array.isArray(tree1)) {
      expect(tree1.children == null || tree1.children.length === 0).toBe(true);
    }
  });

  it('renders arrows for each shift — direction only, no percentages', () => {
    const PersonalizationChip = importComponent();
    if (!PersonalizationChip) {
      throw new Error('RED: PersonalizationChip not yet implemented');
    }
    const shifts = [
      { dim_display: 'performance_score', direction: 'up' },
      { dim_display: 'build_quality_score', direction: 'up' },
      { dim_display: 'brand_recognition', direction: 'down' },
    ];
    const { toJSON } = render(<PersonalizationChip appliedShifts={shifts} />);
    const tree = toJSON();
    const serialised = JSON.stringify(tree);
    // ↑ for up + ↓ for down — at least one of each present
    expect(serialised).toMatch(/↑/);
    expect(serialised).toMatch(/↓/);
    // NO percentages or magnitudes (project rule)
    expect(serialised).not.toMatch(/\d+%/);
    expectNoMagnitudeStrings(tree);
    expectNoForbiddenStrings(tree);
  });

  it('limits to 3 arrows max even with longer input', () => {
    const PersonalizationChip = importComponent();
    if (!PersonalizationChip) {
      throw new Error('RED: PersonalizationChip not yet implemented');
    }
    const shifts = [
      { dim_display: 'a', direction: 'up' },
      { dim_display: 'b', direction: 'up' },
      { dim_display: 'c', direction: 'up' },
      { dim_display: 'd', direction: 'up' },
      { dim_display: 'e', direction: 'up' },
    ];
    const { toJSON } = render(<PersonalizationChip appliedShifts={shifts} />);
    const serialised = JSON.stringify(toJSON());
    // Count up-arrows — should be ≤ 3
    const upArrows = (serialised.match(/↑/g) || []).length;
    expect(upArrows).toBeLessThanOrEqual(3);
  });

  it('snapshot — 1 arrow', () => {
    const PersonalizationChip = importComponent();
    if (!PersonalizationChip) {
      throw new Error('RED: PersonalizationChip not yet implemented');
    }
    const tree = render(
      <PersonalizationChip
        appliedShifts={[{ dim_display: 'performance_score', direction: 'up' }]}
      />,
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('snapshot — 3 arrows mixed direction', () => {
    const PersonalizationChip = importComponent();
    if (!PersonalizationChip) {
      throw new Error('RED: PersonalizationChip not yet implemented');
    }
    const tree = render(
      <PersonalizationChip
        appliedShifts={[
          { dim_display: 'performance_score', direction: 'up' },
          { dim_display: 'build_quality_score', direction: 'up' },
          { dim_display: 'brand_recognition', direction: 'down' },
        ]}
      />,
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });
});
