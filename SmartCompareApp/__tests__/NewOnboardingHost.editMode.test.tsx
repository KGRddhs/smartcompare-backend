/**
 * Bundle D Task 1.F.3 — NewOnboardingHost edit-mode branch coverage.
 *
 * Idle-time coverage top-up per OP #4. Pins the contract that the
 * edit-mode branch:
 *   1. Defaults initialStep to 8 (priorities) when omitted
 *   2. Forwards lastStep=10 (brand_attitude) to OnboardingFlow
 *   3. Calls `onEditDone` (NOT `onComplete`) on completion
 *   4. Still runs the three persistence buckets (demographics /
 *      preferences / attribution) before firing the close hook
 *
 * Mocks OnboardingFlow to capture the props the host forwards into it.
 * React 19's TestRenderer renders concurrently, so all render calls
 * MUST be wrapped in `act(...)` for the mock to fire before the next
 * line of test code.
 */

const mockPut = jest.fn().mockResolvedValue({});
const mockSavePrefs = jest.fn().mockResolvedValue({});
const mockSaveAttr = jest.fn().mockResolvedValue({});

jest.mock('../src/services/api', () => ({
  putDemographics: (...args: any[]) => mockPut(...args),
  savePreferences: (...args: any[]) => mockSavePrefs(...args),
  saveAttribution: (...args: any[]) => mockSaveAttr(...args),
}));

jest.mock('../src/screens/onboarding/OnboardingFlow', () => ({
  OnboardingFlow: (props: any) => {
    (globalThis as any).__flowProps = props;
    return null;
  },
}));

import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { NewOnboardingHost } from '../src/screens/onboarding/NewOnboardingHost';

function renderHost(node: React.ReactElement): void {
  act(() => {
    TestRenderer.create(node);
  });
}

const FULL_DATA: any = {
  country: 'BH',
  governorate: 'Capital',
  age_group: '25-34',
  gender: 'Male',
  language: 'en',
  priorities: ['durability', 'value'],
  budget: 'mid',
  brand_attitude: 'best_of_both',
  attribution_source: 'friend',
};

describe('NewOnboardingHost — edit-mode branch (Bundle D 1.F.3)', () => {
  beforeEach(() => {
    (globalThis as any).__flowProps = null;
    mockPut.mockClear();
    mockSavePrefs.mockClear();
    mockSaveAttr.mockClear();
  });

  it('mode=edit forwards lastStep=10 to OnboardingFlow', () => {
    renderHost(
      <NewOnboardingHost
        mode="edit"
        onComplete={jest.fn()}
        onEditDone={jest.fn()}
      />
    );
    expect((globalThis as any).__flowProps).not.toBeNull();
    expect((globalThis as any).__flowProps.lastStep).toBe(10);
  });

  it('mode=edit defaults initialStep to 8 (priorities)', () => {
    renderHost(
      <NewOnboardingHost
        mode="edit"
        onComplete={jest.fn()}
        onEditDone={jest.fn()}
      />
    );
    expect((globalThis as any).__flowProps.initialStep).toBe(8);
  });

  it('mode=edit explicit initialStep override wins over the default', () => {
    renderHost(
      <NewOnboardingHost
        mode="edit"
        initialStep={9}
        onComplete={jest.fn()}
        onEditDone={jest.fn()}
      />
    );
    expect((globalThis as any).__flowProps.initialStep).toBe(9);
  });

  it('mode=full (default) does NOT forward lastStep — legacy 17-step flow preserved', () => {
    renderHost(<NewOnboardingHost onComplete={jest.fn()} />);
    expect((globalThis as any).__flowProps.lastStep).toBeUndefined();
  });

  it('edit-mode completion fires onEditDone, NOT onComplete', () => {
    const onComplete = jest.fn();
    const onEditDone = jest.fn();
    renderHost(
      <NewOnboardingHost
        mode="edit"
        onComplete={onComplete}
        onEditDone={onEditDone}
      />
    );
    act(() => {
      (globalThis as any).__flowProps.onComplete(FULL_DATA);
    });
    expect(onEditDone).toHaveBeenCalledTimes(1);
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('edit-mode completion still runs the 3 persistence buckets', () => {
    renderHost(
      <NewOnboardingHost
        mode="edit"
        onComplete={jest.fn()}
        onEditDone={jest.fn()}
      />
    );
    act(() => {
      (globalThis as any).__flowProps.onComplete(FULL_DATA);
    });
    expect(mockPut).toHaveBeenCalledTimes(1);
    expect(mockSavePrefs).toHaveBeenCalledTimes(1);
    expect(mockSaveAttr).toHaveBeenCalledTimes(1);
  });

  it('full-mode completion fires onComplete, NOT onEditDone', () => {
    const onComplete = jest.fn();
    const onEditDone = jest.fn();
    renderHost(
      <NewOnboardingHost
        onComplete={onComplete}
        onEditDone={onEditDone}
      />
    );
    act(() => {
      (globalThis as any).__flowProps.onComplete(FULL_DATA);
    });
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onEditDone).not.toHaveBeenCalled();
  });
});
