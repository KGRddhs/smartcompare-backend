/**
 * M21 mobile-jank — MB-perf-08: ProductImage must request Android
 * downsampled decoding.
 *
 * The backend image pipeline sources image_url primarily from og:image —
 * routinely 1000-2400px product shots — while ProductImage renders them
 * into 64-160px tiles. On Android, Fresco only downsamples when
 * `resizeMethod="resize"` is set; the default ('auto' → 'scale' for
 * remote URIs) decodes the FULL bitmap and lets the GPU scale it, so a
 * History screen can decode ~100 multi-megapixel bitmaps for
 * thumbnail-sized slots. iOS ignores the prop entirely (safe no-op).
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import { ProductImage } from '../src/components/primitives/ProductImage';

describe('ProductImage — Android decode downsampling (MB-perf-08)', () => {
  it('passes resizeMethod="resize" to the underlying <Image>', () => {
    const { getByTestId } = render(
      <ProductImage testID="pi" imageUrl="https://cdn.example.com/huge-og-image.jpg" />
    );
    expect(getByTestId('pi-img').props.resizeMethod).toBe('resize');
  });

  it('keeps resizeMethod="resize" alongside a custom resizeMode', () => {
    const { getByTestId } = render(
      <ProductImage
        testID="pi"
        imageUrl="https://cdn.example.com/huge-og-image.jpg"
        resizeMode="contain"
      />
    );
    const img = getByTestId('pi-img');
    expect(img.props.resizeMethod).toBe('resize');
    expect(img.props.resizeMode).toBe('contain');
  });
});
