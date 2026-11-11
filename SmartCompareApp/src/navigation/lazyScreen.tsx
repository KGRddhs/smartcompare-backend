/**
 * S81-G6 CL2 CLIENT-SPEED -- defer a screen module's evaluation to its first
 * open (React.lazy + Suspense).
 *
 * On native the module stays in the one bundle (no chunk split); only its
 * evaluation moves out of boot. Until the import settles the screen shows
 * one full-screen View in the theme background colour (no text, no string;
 * RULINGS_S81_G6 R-G6-1). A failing import propagates to the nearest error
 * boundary, as a throwing module body does today.
 */
import React, { Suspense } from 'react';
import { View } from 'react-native';
import { colors } from '../theme';

const fallbackStyle = { flex: 1, backgroundColor: colors.bg.primary };

export function lazyScreen<P extends object>(
  load: () => Promise<{ default: React.ComponentType<P> }>
): React.ComponentType<P> {
  const LazyComponent = React.lazy(load);
  function LazyScreen(props: P) {
    return (
      <Suspense fallback={<View style={fallbackStyle} />}>
        <LazyComponent {...(props as React.JSX.IntrinsicAttributes & P)} />
      </Suspense>
    );
  }
  return LazyScreen;
}
