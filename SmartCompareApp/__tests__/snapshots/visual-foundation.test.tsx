/**
 * Visual foundation snapshots — Phase 1 Task 6.
 *
 * Captures the rendered output of every component that defines the new
 * visual identity. If any future change accidentally walks back the
 * black/emerald hybrid, Geist typography, or icon shape contract, the
 * snapshot diff catches it loudly.
 *
 * Why component-level instead of screen-level:
 *   The redesign's identity lives in the design tokens, the Button, and
 *   the icons — not in screen layout (yet; Phase 3 redesigns Home and
 *   Results). Snapshotting screens before the Phase 3 layout overhaul
 *   would lock in the OLD layout. Phase 5 adds full-screen snapshots
 *   after the new layouts ship.
 *
 *   Manual visual on-device checks for the existing 12 screens are
 *   covered by the test-qa Phase 1 gate (Task 7) — Geist renders, all
 *   buttons pick up the black bg, RTL still works.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { Button } from '../../src/components/Button';
import {
  QaranIcon,
  BackIcon,
  CloseIcon,
  SearchIcon,
  BellIcon,
  SettingsIcon,
  PlusIcon,
} from '../../src/icons';
import { colors, typography, radii, spacing } from '../../src/theme';
import { motion } from '../../src/theme/motion';

describe('Theme tokens snapshot', () => {
  it('colors structure stable', () => {
    expect(colors).toMatchSnapshot();
  });

  it('typography presets stable', () => {
    expect(typography).toMatchSnapshot();
  });

  it('radii + spacing stable', () => {
    expect({ radii, spacing }).toMatchSnapshot();
  });
});

describe('Motion tokens snapshot', () => {
  it('springConfig + haptic stable (function-typed easings serialise as undefined which is fine)', () => {
    // Easing functions don't snapshot well — capture the structure
    // and the serialisable parts only.
    expect({
      screenTransitionDuration: motion.screenTransition.duration,
      springConfig: motion.springConfig,
      haptic: motion.haptic,
    }).toMatchSnapshot();
  });
});

describe('Button variants snapshot', () => {
  it('primary variant', () => {
    const tree = render(<Button title="Continue" onPress={() => {}} />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('signature variant', () => {
    const tree = render(
      <Button title="Reveal" variant="signature" onPress={() => {}} />
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('secondary variant', () => {
    const tree = render(
      <Button title="Skip" variant="secondary" onPress={() => {}} />
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('disabled primary variant', () => {
    const tree = render(
      <Button title="Submit" disabled onPress={() => {}} />
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });
});

describe('Icon snapshots — default 24px black', () => {
  it('QaranIcon default', () => {
    expect(render(<QaranIcon />).toJSON()).toMatchSnapshot();
  });

  it('BackIcon default', () => {
    expect(render(<BackIcon />).toJSON()).toMatchSnapshot();
  });

  it('CloseIcon default', () => {
    expect(render(<CloseIcon />).toJSON()).toMatchSnapshot();
  });

  it('SearchIcon default', () => {
    expect(render(<SearchIcon />).toJSON()).toMatchSnapshot();
  });

  it('BellIcon default', () => {
    expect(render(<BellIcon />).toJSON()).toMatchSnapshot();
  });

  it('SettingsIcon default', () => {
    expect(render(<SettingsIcon />).toJSON()).toMatchSnapshot();
  });

  it('PlusIcon default', () => {
    expect(render(<PlusIcon />).toJSON()).toMatchSnapshot();
  });
});

describe('Icon snapshots — emerald accent at 32px', () => {
  it('QaranIcon emerald 32', () => {
    expect(
      render(<QaranIcon size={32} color="#10B981" />).toJSON()
    ).toMatchSnapshot();
  });

  it('PlusIcon emerald 32', () => {
    expect(
      render(<PlusIcon size={32} color="#10B981" />).toJSON()
    ).toMatchSnapshot();
  });
});
