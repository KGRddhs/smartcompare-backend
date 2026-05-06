import React from 'react';

const Animated = {
  View: ({ children, style, ...props }: any) =>
    React.createElement('mock-Animated-View', { ...props, style }, children),
  Text: ({ children, style, ...props }: any) =>
    React.createElement('mock-Animated-Text', { ...props, style }, children),
};

export function useSharedValue(init: number) {
  return { value: init };
}

export function useAnimatedStyle(updater: () => any) {
  return updater();
}

export function withRepeat(animation: any, _count?: number, _reverse?: boolean) {
  return animation;
}

export function withTiming(toValue: number, _config?: any) {
  return toValue;
}

export function withDelay(_delay: number, animation: any) {
  return animation;
}

export function withSequence(...animations: any[]) {
  return animations[animations.length - 1];
}

export function runOnJS(fn: any) {
  return fn;
}

export const Easing = {
  inOut: (_easing: any) => (_t: number) => _t,
  out: (_easing: any) => (_t: number) => _t,
  ease: (_t: number) => _t,
  cubic: (_t: number) => _t,
  bezier: (_x1: number, _y1: number, _x2: number, _y2: number) => (_t: number) => _t,
};

export default Animated;
