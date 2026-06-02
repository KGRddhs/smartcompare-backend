/**
 * Bundle E S3 hotfix — ProductImage resizeMode prop.
 *
 * Device walk (image #6) showed the hero ProductImage cards rendering
 * with the product photo cropped/overflowing the placeholder square —
 * <Image> defaulted to `resizeMode='cover'` so any photo whose aspect
 * ratio differed from 1:1 cropped its main subject out of view.
 *
 * Fix: extend ProductImage with a `resizeMode` prop (default 'cover' to
 * preserve previous behavior across SmartPick + History tiles); pass
 * 'contain' from ResultsContent so the full product fits inside the
 * neutral placeholder-tone host.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import { ProductImage } from '../src/components/primitives/ProductImage';

describe('ProductImage — resizeMode prop wiring', () => {
  it('defaults to resizeMode="cover" (backwards-compat)', () => {
    const { getByTestId } = render(
      <ProductImage testID="pi" imageUrl="https://cdn.example.com/iphone15.jpg" />
    );
    const img = getByTestId('pi-img');
    expect(img.props.resizeMode).toBe('cover');
  });

  it('forwards resizeMode="contain" to <Image> (Results hero card)', () => {
    const { getByTestId } = render(
      <ProductImage
        testID="pi"
        imageUrl="https://cdn.example.com/iphone15.jpg"
        resizeMode="contain"
      />
    );
    const img = getByTestId('pi-img');
    expect(img.props.resizeMode).toBe('contain');
  });

  it('host wrapper carries the placeholderTone background when image is rendered', () => {
    // Lets a non-square photo letterbox with the neutral tone visible
    // around the edges instead of cropping the main subject.
    const { getByTestId } = render(
      <ProductImage
        testID="pi"
        imageUrl="https://cdn.example.com/iphone15.jpg"
        placeholderTone="#EEEFF4"
      />
    );
    const host = getByTestId('pi');
    const styleArr = Array.isArray(host.props.style) ? host.props.style : [host.props.style];
    const flat = Object.assign({}, ...styleArr.filter(Boolean));
    expect(flat.backgroundColor).toBe('#EEEFF4');
    expect(flat.aspectRatio).toBe(1);
  });
});
