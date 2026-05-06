/**
 * react-native-svg test mock.
 *
 * Renders each SVG primitive as a host component named after the
 * primitive so @testing-library/react-native queries (UNSAFE_root,
 * findByType) can match by name. Props pass through verbatim so style
 * + color assertions still work.
 */
import React from 'react';

function host(name: string) {
  const C = ({ children, ...props }: any) =>
    React.createElement(name, props, children);
  C.displayName = name;
  return C;
}

const Svg = host('Svg');
export default Svg;
export { Svg };

export const Circle = host('Circle');
export const Rect = host('Rect');
export const Line = host('Line');
export const Path = host('Path');
export const G = host('G');
export const Text = host('SvgText');
export const TSpan = host('TSpan');
export const Defs = host('Defs');
export const ClipPath = host('ClipPath');
export const Mask = host('Mask');
export const Use = host('Use');
export const Polygon = host('Polygon');
export const Polyline = host('Polyline');
export const Ellipse = host('Ellipse');
export const LinearGradient = host('LinearGradient');
export const RadialGradient = host('RadialGradient');
export const Stop = host('Stop');
export const Symbol = host('Symbol');
