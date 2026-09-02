import React from 'react';
import { View as RNView, Text as RNText, Image as RNImage } from 'react-native';

// Forward Animated.* to React Native's host components so that
// @testing-library/react-native helpers (getByText, getByRole) treat
// them as first-class hosts. A custom mock-prefixed element type makes
// getByText fail because it traverses Text-typed nodes only.
const Animated = {
  View: RNView,
  Text: RNText,
  Image: RNImage,
  ScrollView: RNView,
  createAnimatedComponent: <P,>(Component: React.ComponentType<P>) => Component,
};

export function useSharedValue(init: number) {
  return { value: init };
}

export function useAnimatedStyle(updater: () => any) {
  return updater();
}

// Bundle E HeroRings + DimensionBars use animatedProps for stroke-fill +
// width animations. Mock simply evaluates the updater once so the host
// node receives the *final* prop values — enough for source-prop
// assertions; we don't time-travel through frames in jest.
export function useAnimatedProps(updater: () => any) {
  return updater();
}

export function withRepeat(animation: any, _count?: number, _reverse?: boolean) {
  return animation;
}

export function withTiming(toValue: number, _config?: any) {
  return toValue;
}

export function withSpring(toValue: number, _config?: any) {
  return toValue;
}

export function withDelay(_delay: number, animation: any) {
  return animation;
}

export function useAnimatedReaction(_prepare: any, _react: any, _deps?: any) {
  return undefined;
}

export function useDerivedValue(updater: () => any) {
  return { value: updater() };
}

export function interpolate(value: number, _input: number[], output: number[]) {
  return output[0] ?? value;
}

export function withSequence(...animations: any[]) {
  return animations[animations.length - 1];
}

export function runOnJS(fn: any) {
  return fn;
}

// M21 mobile-jank — chainable entering-animation builders. `delay` is a
// jest.fn so tests can assert the per-row stagger values HistoryScreen
// passes (MB-perf-07 caps them). Each method returns the same builder so
// arbitrary chains (`FadeInDown.delay(50).duration(300)`) resolve.
function makeEnteringBuilder() {
  const builder: any = {};
  builder.delay = jest.fn((_ms: number) => builder);
  builder.duration = jest.fn((_ms: number) => builder);
  builder.springify = jest.fn(() => builder);
  builder.damping = jest.fn(() => builder);
  builder.easing = jest.fn(() => builder);
  return builder;
}
export const FadeInDown = makeEnteringBuilder();
export const FadeIn = makeEnteringBuilder();
export const FadeInUp = makeEnteringBuilder();
export const FadeOut = makeEnteringBuilder();

export const Easing = {
  inOut: (_easing: any) => (_t: number) => _t,
  out: (_easing: any) => (_t: number) => _t,
  ease: (_t: number) => _t,
  cubic: (_t: number) => _t,
  bezier: (_x1: number, _y1: number, _x2: number, _y2: number) => (_t: number) => _t,
  // Bundle E shimmer token uses Easing.linear (1.4s linear loop on skeletons).
  // Real Reanimated exposes linear as a callable identity easing function.
  linear: (_t: number) => _t,
};

export default Animated;
