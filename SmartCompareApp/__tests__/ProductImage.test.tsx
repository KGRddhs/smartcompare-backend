/**
 * ProductImage — Bundle E S3 A4 image-rendering primitive.
 *
 * Contract from A3 backend lane (per plan § A3.3 + A4 contract sync):
 *   - `products[*].image_url: string | null`
 *   - Consumer renders <Image source={{uri}} /> when truthy
 *   - Consumer renders placeholder when null, undefined, or onError fires
 *
 * Visual spec from ResultsScreen.jsx:39-66 and HomeScreen.jsx:503-525 — square
 * tile, aspectRatio 1/1, radius 12 (SmartPick) or 14 (Results ProductCard);
 * placeholder is solid `tone` background with a dimmed phone-shaped SVG icon.
 *
 * Per plan § A4 — no new native deps; uses RN <Image>. Placeholder is owned
 * by THIS component (no separate primitive); covers the 4 rendering states
 * listed in the dispatcher brief.
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import { ProductImage } from '../src/components/primitives/ProductImage';

describe('ProductImage — 4-state rendering contract', () => {
  describe('state 1: imageUrl is a non-empty string', () => {
    it('renders <Image> with source.uri = imageUrl', () => {
      const { getByTestId, queryByTestId } = render(
        <ProductImage testID="pi" imageUrl="https://cdn.example.com/iphone15.jpg" />
      );
      const img = getByTestId('pi-img');
      expect(img).toBeTruthy();
      expect(img.props.source).toEqual({ uri: 'https://cdn.example.com/iphone15.jpg' });
      expect(queryByTestId('pi-placeholder')).toBeNull();
    });

    it('forwards aspectRatio + borderRadius into Image style', () => {
      const { getByTestId } = render(
        <ProductImage
          testID="pi"
          imageUrl="https://cdn.example.com/x.jpg"
          aspectRatio={1}
          borderRadius={14}
        />
      );
      const img = getByTestId('pi-img');
      const styleArr = Array.isArray(img.props.style) ? img.props.style : [img.props.style];
      const flat = Object.assign({}, ...styleArr.filter(Boolean));
      expect(flat.aspectRatio).toBe(1);
      expect(flat.borderRadius).toBe(14);
    });
  });

  describe('state 2: imageUrl is null', () => {
    it('renders placeholder (NO <Image>)', () => {
      const { getByTestId, queryByTestId } = render(
        <ProductImage testID="pi" imageUrl={null} />
      );
      expect(getByTestId('pi-placeholder')).toBeTruthy();
      expect(queryByTestId('pi-img')).toBeNull();
    });

    it('applies placeholderTone as background color', () => {
      const { getByTestId } = render(
        <ProductImage testID="pi" imageUrl={null} placeholderTone="#FBE6E6" />
      );
      const ph = getByTestId('pi-placeholder');
      const styleArr = Array.isArray(ph.props.style) ? ph.props.style : [ph.props.style];
      const flat = Object.assign({}, ...styleArr.filter(Boolean));
      expect(flat.backgroundColor).toBe('#FBE6E6');
    });

    it('falls back to a neutral tone when placeholderTone is omitted', () => {
      const { getByTestId } = render(<ProductImage testID="pi" imageUrl={null} />);
      const ph = getByTestId('pi-placeholder');
      const styleArr = Array.isArray(ph.props.style) ? ph.props.style : [ph.props.style];
      const flat = Object.assign({}, ...styleArr.filter(Boolean));
      expect(flat.backgroundColor).toBeTruthy(); // neutral fallback applied
    });
  });

  describe('state 3: imageUrl is undefined', () => {
    it('renders placeholder (NO <Image>)', () => {
      const { getByTestId, queryByTestId } = render(<ProductImage testID="pi" />);
      expect(getByTestId('pi-placeholder')).toBeTruthy();
      expect(queryByTestId('pi-img')).toBeNull();
    });
  });

  describe('state 4: onError fires (broken URL)', () => {
    it('swaps to placeholder after onError', () => {
      const { getByTestId, queryByTestId } = render(
        <ProductImage testID="pi" imageUrl="https://cdn.example.com/404.jpg" placeholderTone="#E8E9ED" />
      );
      expect(getByTestId('pi-img')).toBeTruthy();
      fireEvent(getByTestId('pi-img'), 'error');
      expect(queryByTestId('pi-img')).toBeNull();
      expect(getByTestId('pi-placeholder')).toBeTruthy();
    });

    it('preserves placeholderTone on error fallback', () => {
      const { getByTestId } = render(
        <ProductImage testID="pi" imageUrl="https://cdn.example.com/404.jpg" placeholderTone="#FFEAD4" />
      );
      fireEvent(getByTestId('pi-img'), 'error');
      const ph = getByTestId('pi-placeholder');
      const styleArr = Array.isArray(ph.props.style) ? ph.props.style : [ph.props.style];
      const flat = Object.assign({}, ...styleArr.filter(Boolean));
      expect(flat.backgroundColor).toBe('#FFEAD4');
    });
  });

  describe('edge cases', () => {
    it('treats empty-string imageUrl as falsy → placeholder', () => {
      const { getByTestId, queryByTestId } = render(
        <ProductImage testID="pi" imageUrl="" />
      );
      expect(getByTestId('pi-placeholder')).toBeTruthy();
      expect(queryByTestId('pi-img')).toBeNull();
    });

    it('treats whitespace-only imageUrl as falsy → placeholder', () => {
      const { getByTestId, queryByTestId } = render(
        <ProductImage testID="pi" imageUrl="   " />
      );
      expect(getByTestId('pi-placeholder')).toBeTruthy();
      expect(queryByTestId('pi-img')).toBeNull();
    });

    it('honors custom aspectRatio (e.g. 4:3)', () => {
      const { getByTestId } = render(
        <ProductImage testID="pi" imageUrl={null} aspectRatio={4 / 3} />
      );
      const ph = getByTestId('pi-placeholder');
      const styleArr = Array.isArray(ph.props.style) ? ph.props.style : [ph.props.style];
      const flat = Object.assign({}, ...styleArr.filter(Boolean));
      expect(flat.aspectRatio).toBeCloseTo(4 / 3);
    });

    it('honors custom borderRadius', () => {
      const { getByTestId } = render(
        <ProductImage testID="pi" imageUrl={null} borderRadius={20} />
      );
      const ph = getByTestId('pi-placeholder');
      const styleArr = Array.isArray(ph.props.style) ? ph.props.style : [ph.props.style];
      const flat = Object.assign({}, ...styleArr.filter(Boolean));
      expect(flat.borderRadius).toBe(20);
    });

    it('renders an icon node inside placeholder for non-empty visual fill', () => {
      const { getByTestId } = render(<ProductImage testID="pi" imageUrl={null} />);
      expect(getByTestId('pi-placeholder-icon')).toBeTruthy();
    });

    it('accessibilityRole is "image" in both states', () => {
      const { getByTestId, rerender } = render(
        <ProductImage testID="pi" imageUrl="https://x/y.jpg" />
      );
      expect(getByTestId('pi-img').props.accessibilityRole).toBe('image');
      rerender(<ProductImage testID="pi" imageUrl={null} />);
      expect(getByTestId('pi-placeholder').props.accessibilityRole).toBe('image');
    });

    it('omits testID suffixes when no testID is passed', () => {
      const { queryByTestId } = render(<ProductImage imageUrl={null} />);
      expect(queryByTestId('pi-placeholder')).toBeNull();
      // No throw is the success condition; placeholder still renders, just untagged.
    });
  });

  describe('race condition: imageUrl prop changes after error', () => {
    it('re-renders Image when imageUrl prop changes to a new URL', () => {
      const { getByTestId, queryByTestId, rerender } = render(
        <ProductImage testID="pi" imageUrl="https://cdn.example.com/a.jpg" />
      );
      fireEvent(getByTestId('pi-img'), 'error');
      expect(queryByTestId('pi-img')).toBeNull();
      rerender(<ProductImage testID="pi" imageUrl="https://cdn.example.com/b.jpg" />);
      // After URL change, the component should attempt to load the new URL again.
      expect(getByTestId('pi-img')).toBeTruthy();
      expect(getByTestId('pi-img').props.source).toEqual({ uri: 'https://cdn.example.com/b.jpg' });
    });

    it('keeps placeholder when imageUrl prop changes from one falsy to another', () => {
      const { getByTestId, queryByTestId, rerender } = render(
        <ProductImage testID="pi" imageUrl={null} />
      );
      expect(getByTestId('pi-placeholder')).toBeTruthy();
      rerender(<ProductImage testID="pi" imageUrl={undefined} />);
      expect(getByTestId('pi-placeholder')).toBeTruthy();
      expect(queryByTestId('pi-img')).toBeNull();
    });
  });
});
