/**
 * Button variant tests — Phase 1.
 *
 * The redesign moves the primary CTA from emerald to black; emerald is
 * now reserved for the *signature* variant (see design Section 1
 * "Where each color earns its keep" + Section 4e — the one-time
 * invitee "Reveal my verdict" CTA).
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { StyleSheet } from 'react-native';
import { Button } from '../../src/components/Button';

function flatten(style: unknown): Record<string, unknown> {
  return StyleSheet.flatten(style as any) as Record<string, unknown>;
}

describe('Button', () => {
  it('primary variant uses black background by default', () => {
    const { getByTestId } = render(
      <Button title="Continue" testID="btn" onPress={() => {}} />
    );
    const node = getByTestId('btn');
    const style = flatten(node.props.style);
    expect(style.backgroundColor).toBe('#0A0A0B');
  });

  it('primary variant text is white', () => {
    const { getByText } = render(
      <Button title="Continue" onPress={() => {}} />
    );
    const text = getByText('Continue');
    const style = flatten(text.props.style);
    expect(style.color).toBe('#FFFFFF');
  });

  it('signature variant uses emerald — reserved for the one-time invitee CTA', () => {
    const { getByTestId } = render(
      <Button title="Reveal" variant="signature" testID="btn" onPress={() => {}} />
    );
    const node = getByTestId('btn');
    const style = flatten(node.props.style);
    expect(style.backgroundColor).toBe('#10B981');
  });

  it('secondary variant uses white bg + black border', () => {
    const { getByTestId } = render(
      <Button title="Skip" variant="secondary" testID="btn" onPress={() => {}} />
    );
    const node = getByTestId('btn');
    const style = flatten(node.props.style);
    expect(style.backgroundColor).toBe('#FFFFFF');
    expect(style.borderColor).toBe('#0A0A0B');
    expect(style.borderWidth).toBeGreaterThanOrEqual(1);
  });

  it('secondary variant text is black', () => {
    const { getByText } = render(
      <Button title="Skip" variant="secondary" onPress={() => {}} />
    );
    const text = getByText('Skip');
    const style = flatten(text.props.style);
    expect(style.color).toBe('#0A0A0B');
  });

  it('disabled prop reduces opacity and propagates disabled to host', () => {
    const onPress = jest.fn();
    const { getByTestId } = render(
      <Button title="Submit" testID="btn" disabled onPress={onPress} />
    );
    const node = getByTestId('btn');
    const style = flatten(node.props.style);
    expect(style.opacity).toBeLessThan(1);
    expect(node.props.disabled).toBe(true);
  });

  it('press fires onPress for primary variant', () => {
    const onPress = jest.fn();
    const { getByTestId } = render(
      <Button title="Continue" testID="btn" onPress={onPress} />
    );
    fireEvent.press(getByTestId('btn'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
