/**
 * DirectionalIcon — M21 W4 rtl-i18n (MB-i18n-rtl-03).
 *
 * The repo shipped TWO flip helpers (utils/rtl.rtlFlip + icons/flipForRTL)
 * with exactly ONE consumer between them (OnboardingFlow), while ~11 screens
 * rendered back-chevrons / directional arrows unmirrored under RTL. This
 * wrapper is the single wiring point: it applies rtlFlip() (which reads
 * I18nManager.isRTL live at render time) around any direction-bearing icon.
 *
 * Contract:
 *   - LTR  (isRTL=false): transform [{ scaleX: 1 }]  — visual no-op.
 *   - RTL  (isRTL=true):  transform [{ scaleX: -1 }] — horizontal mirror.
 *   - Children render unchanged; wrapper adds no layout of its own.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { I18nManager, StyleSheet } from 'react-native';
import { ArrowLeft } from 'lucide-react-native';
import { DirectionalIcon } from '../../src/components/primitives/DirectionalIcon';

afterEach(() => {
  (I18nManager as any).isRTL = false;
});

function rootStyle(tree: any): Record<string, any> {
  return StyleSheet.flatten(tree.props.style);
}

describe('DirectionalIcon — RTL icon mirroring wrapper', () => {
  it('LTR: renders child icon with identity scaleX (no visual flip)', () => {
    (I18nManager as any).isRTL = false;
    const { toJSON } = render(
      <DirectionalIcon>
        <ArrowLeft size={24} color="#000" />
      </DirectionalIcon>
    );
    const tree = toJSON() as any;
    expect(rootStyle(tree).transform).toEqual([{ scaleX: 1 }]);
  });

  it('RTL: mirrors the child icon horizontally (scaleX -1)', () => {
    (I18nManager as any).isRTL = true;
    const { toJSON } = render(
      <DirectionalIcon>
        <ArrowLeft size={24} color="#000" />
      </DirectionalIcon>
    );
    const tree = toJSON() as any;
    expect(rootStyle(tree).transform).toEqual([{ scaleX: -1 }]);
  });

  it('renders its child icon unchanged', () => {
    const { toJSON } = render(
      <DirectionalIcon>
        <ArrowLeft size={24} color="#000" />
      </DirectionalIcon>
    );
    const tree = toJSON() as any;
    const child = tree.children?.[0];
    expect(child?.type).toBe('mock-icon-ArrowLeft');
    expect(child?.props?.size).toBe(24);
  });

  it('merges a caller style without dropping the flip transform', () => {
    (I18nManager as any).isRTL = true;
    const { toJSON } = render(
      <DirectionalIcon style={{ marginLeft: 4 }}>
        <ArrowLeft size={24} color="#000" />
      </DirectionalIcon>
    );
    const flat = rootStyle(toJSON() as any);
    expect(flat.transform).toEqual([{ scaleX: -1 }]);
    expect(flat.marginLeft).toBe(4);
  });

  it('matches snapshot in LTR', () => {
    (I18nManager as any).isRTL = false;
    const { toJSON } = render(
      <DirectionalIcon>
        <ArrowLeft size={24} color="#000" />
      </DirectionalIcon>
    );
    expect(toJSON()).toMatchSnapshot();
  });

  it('matches snapshot in RTL', () => {
    (I18nManager as any).isRTL = true;
    const { toJSON } = render(
      <DirectionalIcon>
        <ArrowLeft size={24} color="#000" />
      </DirectionalIcon>
    );
    expect(toJSON()).toMatchSnapshot();
  });
});
